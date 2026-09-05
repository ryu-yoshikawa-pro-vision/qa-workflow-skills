from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from scripts.skills.evals.semantic.loader import SemanticDatasetError, load_semantic_skill


class SemanticLoaderTests(unittest.TestCase):
    def make_fixture(self, root: Path) -> Path:
        skills_root = root / "skills"
        semantic = skills_root / "example-skill" / "evals" / "semantic"
        case = semantic / "cases" / "case-001"
        case.mkdir(parents=True)
        (semantic / "rubric.json").write_text(
            json.dumps(
                {
                    "skill": "example-skill",
                    "criteria": [
                        {
                            "id": "SEM-EX-001",
                            "title": "意味品質",
                            "description": "根拠と整合するか。",
                            "critical": True,
                        }
                    ],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        (semantic / "evals.json").write_text(
            json.dumps(
                {
                    "skill": "example-skill",
                    "cases": [
                        {
                            "id": "EX-SEM-001",
                            "input": "cases/case-001/input.md",
                            "reference": "cases/case-001/reference.md",
                            "criteria": ["SEM-EX-001"],
                        }
                    ],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        (case / "input.md").write_text("# Input\n事実A", encoding="utf-8")
        (case / "reference.md").write_text("# Reference\n事実Aを基準とする", encoding="utf-8")
        return skills_root

    def set_case_path(self, skills_root: Path, field: str, value: str) -> None:
        path = skills_root / "example-skill/evals/semantic/evals.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["cases"][0][field] = value
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    def test_loads_temporary_semantic_fixture(self):
        with tempfile.TemporaryDirectory() as tmp:
            dataset = load_semantic_skill("example-skill", self.make_fixture(Path(tmp)))
            self.assertEqual(dataset["skill"], "example-skill")
            self.assertEqual(dataset["cases"][0]["id"], "EX-SEM-001")

    def test_missing_rubric_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            skills_root = self.make_fixture(Path(tmp))
            (skills_root / "example-skill/evals/semantic/rubric.json").unlink()
            with self.assertRaises(FileNotFoundError):
                load_semantic_skill("example-skill", skills_root)

    def test_missing_evals_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            skills_root = self.make_fixture(Path(tmp))
            (skills_root / "example-skill/evals/semantic/evals.json").unlink()
            with self.assertRaises(FileNotFoundError):
                load_semantic_skill("example-skill", skills_root)

    def test_duplicate_criterion_id_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            skills_root = self.make_fixture(Path(tmp))
            path = skills_root / "example-skill/evals/semantic/rubric.json"
            data = json.loads(path.read_text(encoding="utf-8"))
            data["criteria"].append(dict(data["criteria"][0]))
            path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            with self.assertRaises(SemanticDatasetError):
                load_semantic_skill("example-skill", skills_root)

    def test_unknown_case_criterion_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            skills_root = self.make_fixture(Path(tmp))
            path = skills_root / "example-skill/evals/semantic/evals.json"
            data = json.loads(path.read_text(encoding="utf-8"))
            data["cases"][0]["criteria"] = ["SEM-EX-999"]
            path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            with self.assertRaises(SemanticDatasetError):
                load_semantic_skill("example-skill", skills_root)

    def test_missing_input_or_reference_raises(self):
        for filename in ("input.md", "reference.md"):
            with self.subTest(filename=filename), tempfile.TemporaryDirectory() as tmp:
                skills_root = self.make_fixture(Path(tmp))
                (skills_root / f"example-skill/evals/semantic/cases/case-001/{filename}").unlink()
                with self.assertRaises(FileNotFoundError):
                    load_semantic_skill("example-skill", skills_root)

    def test_relative_traversal_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            skills_root = self.make_fixture(tmp_path)
            outside = skills_root / "example-skill/evals/outside.md"
            outside.write_text("outside", encoding="utf-8")
            self.set_case_path(skills_root, "input", "cases/../../outside.md")
            with self.assertRaises(SemanticDatasetError):
                load_semantic_skill("example-skill", skills_root)

    def test_absolute_case_path_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            skills_root = self.make_fixture(tmp_path)
            outside = tmp_path / "outside.md"
            outside.write_text("outside", encoding="utf-8")
            self.set_case_path(skills_root, "reference", str(outside.resolve()))
            with self.assertRaises(SemanticDatasetError):
                load_semantic_skill("example-skill", skills_root)

    def test_symlink_escape_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            skills_root = self.make_fixture(tmp_path)
            semantic = skills_root / "example-skill/evals/semantic"
            outside = tmp_path / "outside.md"
            outside.write_text("outside", encoding="utf-8")
            link = semantic / "cases" / "escape.md"
            try:
                link.symlink_to(outside)
            except (OSError, NotImplementedError) as exc:
                self.skipTest(f"symlink is not available: {exc}")
            self.set_case_path(skills_root, "input", "cases/escape.md")
            with self.assertRaises(SemanticDatasetError):
                load_semantic_skill("example-skill", skills_root)


if __name__ == "__main__":
    unittest.main()
