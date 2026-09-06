from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


REPO_ROOT = Path(__file__).resolve().parents[4]
SKILL = "test-case-design"
EVAL_ID = "TC-SEM-001"
CRITERIA = [
    "SEM-TC-001",
    "SEM-TC-002",
    "SEM-TC-003",
    "SEM-TC-004",
    "SEM-TC-005",
    "SEM-TC-006",
]


class SemanticRuntimePortabilityTests(unittest.TestCase):
    def test_single_skill_copy_runs_semantic_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            temp_root = Path(tmp)
            skill_target = temp_root / "skills" / SKILL
            runtime_target = temp_root / "scripts" / "skills" / "evals"
            skill_target.parent.mkdir(parents=True)
            runtime_target.parent.mkdir(parents=True)

            shutil.copytree(REPO_ROOT / "skills" / SKILL, skill_target)
            shutil.copytree(REPO_ROOT / "scripts" / "skills" / "evals", runtime_target)

            self.assertEqual(
                sorted(path.name for path in (temp_root / "skills").iterdir()),
                [SKILL],
            )
            self.assertFalse((temp_root / "scripts" / "__init__.py").exists())
            self.assertFalse((temp_root / "scripts" / "skills" / "__init__.py").exists())

            candidate = temp_root / "candidate.md"
            candidate.write_text("# Test Case\n保存操作と一覧反映を具体的に検証する。", encoding="utf-8")

            judge = temp_root / "fake_judge.py"
            response = {
                "criteria": [
                    {
                        "id": criterion_id,
                        "evaluable": True,
                        "rating": 4,
                        "reason": "fixtureの根拠とCandidate Outputを照合できる",
                        "evidence": ["Candidate Outputの具体的な検証記述"],
                    }
                    for criterion_id in CRITERIA
                ]
            }
            judge.write_text(
                "import json, sys\n"
                "prompt = sys.stdin.read()\n"
                "assert '# Evaluation Instructions' in prompt\n"
                "assert '# Candidate Output' in prompt\n"
                "assert '\"candidate_output\":' in prompt\n"
                "assert '<CANDIDATE_OUTPUT_UNTRUSTED>' not in prompt\n"
                f"print(json.dumps({response!r}, ensure_ascii=False))\n",
                encoding="utf-8",
            )

            completed = subprocess.run(
                [
                    sys.executable,
                    "scripts/skills/evals/semantic/run.py",
                    "--skill",
                    SKILL,
                    "--eval-id",
                    EVAL_ID,
                    "--output",
                    str(candidate),
                    "--judge-command",
                    sys.executable,
                    str(judge),
                ],
                cwd=temp_root,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            payload = json.loads(completed.stdout)
            self.assertEqual(payload["verdict"], "pass")


if __name__ == "__main__":
    unittest.main()
