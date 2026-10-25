"""質問JSONとHTML生成の回帰テスト。"""

import importlib.util
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "build_form", ROOT / "scripts/build_form.py"
)
assert SPEC and SPEC.loader
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


def sample():
    return json.loads(
        (ROOT / "assets/questionnaire_template.json").read_text(encoding="utf-8")
    )


class FormBuilderTests(unittest.TestCase):
    def test_sample_is_dummy_and_offline(self):
        form = sample()
        self.assertIn("サンプル", form["title"])
        self.assertTrue(all("ダミー質問" in q["title"] for q in form["questions"]))
        html = mod.build(mod.validate(form))
        self.assertEqual(html.count("<script"), 2)
        self.assertNotIn('src="http', html)
        self.assertNotIn('href="http', html)

    def test_choice_and_free_text(self):
        form = sample()
        self.assertTrue(form["questions"][0]["choices"])
        self.assertEqual(form["questions"][1]["choices"], [])
        html = mod.build(mod.validate(form))
        self.assertNotIn("__FORM_APP_JS__", html)
        self.assertNotIn("__QUESTIONNAIRE_JSON__", html)

    def test_missing_choices_normalized(self):
        form = sample()
        form["questions"][1].pop("choices")
        self.assertEqual(mod.validate(form)["questions"][1]["choices"], [])

    def test_duplicate_question_id(self):
        form = sample()
        form["questions"][1]["id"] = form["questions"][0]["id"]
        with self.assertRaises(mod.FormError):
            mod.validate(form)

    def test_duplicate_choice_id(self):
        form = sample()
        form["questions"][0]["choices"][1]["id"] = "A"
        with self.assertRaises(mod.FormError):
            mod.validate(form)

    def test_unsafe_filename(self):
        for name in ("../answers.md", "file.txt", r"folder\answers.md"):
            with self.subTest(name=name):
                form = sample()
                form["output"]["filename"] = name
                with self.assertRaises(mod.FormError):
                    mod.validate(form)

    def test_multiple_type(self):
        form = sample()
        form["questions"][0]["defaultMultiple"] = "false"
        with self.assertRaises(mod.FormError):
            mod.validate(form)

    def test_html_escape(self):
        form = sample()
        form["questions"][0]["title"] = "</script><img src=x>&\u2028"
        html = mod.build(mod.validate(form))
        self.assertEqual(html.lower().count("</script>"), 2)
        self.assertNotIn("<img src=x", html)
        self.assertIn(r"\u003c/script\u003e", html)
        self.assertIn(r"\u0026", html)
        self.assertIn(r"\u2028", html)

    def test_marker_in_user_content(self):
        form = sample()
        form["questions"][0]["context"] = "__FORM_APP_JS__"
        html = mod.build(mod.validate(form))
        self.assertIn('"context":"__FORM_APP_JS__"', html)

    def test_preserve_qa_question_id(self):
        form = sample()
        form["questions"][0]["id"] = "Q-001"
        html = mod.build(mod.validate(form))
        self.assertIn('"id":"Q-001"', html)

    def test_reject_duplicate_json_object_keys_at_cli(self):
        form = sample()
        raw = json.dumps(form, ensure_ascii=False)
        raw = raw.replace('"formId":', '"formId": "duplicate", "formId":', 1)
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "duplicate.json"
            path.write_text(raw, encoding="utf-8")
            proc = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts/build_form.py"),
                    "--input",
                    str(path),
                    "--validate-only",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("JSONキーが重複", proc.stderr)

    def test_per_question_fingerprint_not_changed_by_number(self):
        form = sample()
        form["questions"][0]["id"] = "Q-017"
        base = mod._question_hash(form["questions"][0])
        form["questions"][0]["number"] = "No.99"
        self.assertEqual(base, mod._question_hash(form["questions"][0]))
        form["questions"][0]["choices"][0]["label"] = "意味が変わった選択肢"
        self.assertNotEqual(base, mod._question_hash(form["questions"][0]))

    def test_generated_html_embeds_question_definition_hash(self):
        html = mod.build(mod.validate(sample()))
        match = re.search(
            r'<script id="questions-json" type="application/json">(.*?)</script>',
            html,
            re.DOTALL,
        )
        self.assertIsNotNone(match)
        embedded = json.loads(match.group(1))
        for question in embedded["questions"]:
            self.assertEqual(len(question["_definitionHash"]), 64)
            self.assertEqual(question["_definitionHash"], mod._question_hash(question))

    def test_write_output_outside_skill(self):
        with tempfile.TemporaryDirectory() as root:
            target = Path(root) / "form.html"
            target.write_text(mod.build(mod.validate(sample())), encoding="utf-8")
            self.assertIn("questions-json", target.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
