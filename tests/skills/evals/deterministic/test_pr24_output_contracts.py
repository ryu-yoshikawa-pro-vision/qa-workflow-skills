from __future__ import annotations

import json
import unittest
from pathlib import Path

from scripts.skills.evals.deterministic.loader import load_validator

ROOT = Path(__file__).resolve().parents[4] / "skills"


def sample(skill: str, case: str) -> tuple[str, dict]:
    folder = ROOT / skill / "evals" / "output" / "cases" / case
    return (
        (folder / "output.md").read_text(encoding="utf-8"),
        json.loads((folder / "expected.json").read_text(encoding="utf-8")),
    )


class PR24OutputContractTests(unittest.TestCase):
    def test_project_context_positive_and_false_saved_rejection(self) -> None:
        text, expected = sample("project-context", "pc-out-001")
        validator = load_validator("project-context")
        self.assertEqual(validator(text, expected, "PC-OUT-001").status, "pass")
        invalid = text.replace("未実施。保存先と権限未確認", "成功")
        result = validator(invalid, expected, "PC-OUT-001").to_dict()
        self.assertEqual(result["status"], "fail")
        self.assertIn(
            "PC-D008",
            [a["id"] for a in result["assertions"] if a["status"] == "fail"],
        )

    def test_feature_positive_and_missing_unknown_rejection(self) -> None:
        text, expected = sample("feature-analysis", "fa-out-001")
        validator = load_validator("feature-analysis")
        self.assertEqual(validator(text, expected, "FA-OUT-001").status, "pass")
        invalid = text.replace(
            "- 製品全機能の発見保証：未判定",
            "- 製品全機能の発見保証：100%",
        )
        result = validator(invalid, expected, "FA-OUT-001").to_dict()
        self.assertEqual(result["status"], "fail")
        self.assertIn(
            "FA-D005",
            [a["id"] for a in result["assertions"] if a["status"] == "fail"],
        )


if __name__ == "__main__":
    unittest.main()
