from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


REPO_ROOT = Path(__file__).resolve().parents[5]
RUNNER = REPO_ROOT / "scripts" / "skills" / "evals" / "semantic" / "run.py"


class SemanticCliTests(unittest.TestCase):
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
                            "title": "整合性",
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
        (case / "input.md").write_text("仕様A", encoding="utf-8")
        (case / "reference.md").write_text("仕様Aが正本", encoding="utf-8")
        return skills_root

    def write_judge(self, path: Path, rating: int) -> None:
        path.write_text(
            "import json, sys\n"
            "prompt = sys.stdin.read()\n"
            "assert '# Evaluation Instructions' in prompt\n"
            f"print(json.dumps({{'criteria':[{{'id':'SEM-EX-001','evaluable':True,'rating':{rating},'reason':'根拠と一致','evidence':['候補の記述']}}]}}, ensure_ascii=False))\n",
            encoding="utf-8",
        )

    def run_cli(self, skills_root: Path, candidate: Path, judge: Path):
        return subprocess.run(
            [
                sys.executable,
                str(RUNNER),
                "--skill",
                "example-skill",
                "--eval-id",
                "EX-SEM-001",
                "--output",
                str(candidate),
                "--skills-root",
                str(skills_root),
                "--judge-command",
                sys.executable,
                str(judge),
            ],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_pass_verdict_returns_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            skills_root = self.make_fixture(tmp_path)
            candidate = tmp_path / "candidate.md"
            candidate.write_text("仕様Aに従う", encoding="utf-8")
            judge = tmp_path / "judge.py"
            self.write_judge(judge, 4)
            completed = self.run_cli(skills_root, candidate, judge)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(json.loads(completed.stdout)["verdict"], "pass")

    def test_needs_review_returns_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            skills_root = self.make_fixture(tmp_path)
            candidate = tmp_path / "candidate.md"
            candidate.write_text("仕様Aに従う", encoding="utf-8")
            judge = tmp_path / "judge.py"
            self.write_judge(judge, 2)
            completed = self.run_cli(skills_root, candidate, judge)
            self.assertEqual(completed.returncode, 1, completed.stderr)
            self.assertEqual(json.loads(completed.stdout)["verdict"], "needs_review")

    def test_invalid_judge_response_returns_two(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            skills_root = self.make_fixture(tmp_path)
            candidate = tmp_path / "candidate.md"
            candidate.write_text("仕様Aに従う", encoding="utf-8")
            judge = tmp_path / "judge.py"
            judge.write_text("import sys\nsys.stdin.read()\nprint('not-json')\n", encoding="utf-8")
            completed = self.run_cli(skills_root, candidate, judge)
            self.assertEqual(completed.returncode, 2)
            self.assertEqual(completed.stdout, "")

    def test_utf8_judge_protocol_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            skills_root = self.make_fixture(tmp_path)
            candidate_text = "名称「日本語テスト✅」を保存する → 完了"
            candidate = tmp_path / "candidate.md"
            candidate.write_text(candidate_text, encoding="utf-8")
            judge = tmp_path / "judge.py"
            judge.write_text(
                "import json, sys\n"
                "prompt = sys.stdin.buffer.read().decode('utf-8')\n"
                f"assert {candidate_text!r} in prompt\n"
                "response = {'criteria':[{'id':'SEM-EX-001','evaluable':True,'rating':4,'reason':'日本語理由✅','evidence':['記号「→」を確認']}] }\n"
                "sys.stdout.buffer.write(json.dumps(response, ensure_ascii=False).encode('utf-8'))\n",
                encoding="utf-8",
            )
            completed = self.run_cli(skills_root, candidate, judge)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            payload = json.loads(completed.stdout)
            self.assertEqual(payload["verdict"], "pass")
            self.assertEqual(payload["criteria"][0]["reason"], "日本語理由✅")
            self.assertEqual(payload["criteria"][0]["evidence"], ["記号「→」を確認"])


if __name__ == "__main__":
    unittest.main()
