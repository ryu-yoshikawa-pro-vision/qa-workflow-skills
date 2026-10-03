from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]
SKILL_ROOT = REPO_ROOT / "skills" / "usability-evaluation"
VALIDATOR_PATH = SKILL_ROOT / "evals" / "deterministic" / "validator.py"
spec = importlib.util.spec_from_file_location("usability_evaluation_output_validator", VALIDATOR_PATH)
validator = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(validator)


def _case(case_name: str) -> tuple[str, dict]:
    root = SKILL_ROOT / "evals" / "output" / "cases" / case_name
    return (
        (root / "reference.md").read_text(encoding="utf-8"),
        json.loads((root / "expected.json").read_text(encoding="utf-8")),
    )


class UsabilityEvaluationOutputTests(unittest.TestCase):
    def test_saved_dialog_issue_and_no_issue_outputs_close_deterministically(self) -> None:
        for case_name in ("case-001", "case-002"):
            with self.subTest(case=case_name):
                text, expected = _case(case_name)
                result = validator.validate(text, expected, case_name)
                self.assertEqual(result.status, "pass", result.to_dict())

    def test_non_aspect_validation_error_does_not_fail_fixed_aspect_assertion(self) -> None:
        text, expected = _case("case-001")
        text = text.replace('["EV-001","EV-002","EV-003","EV-004"]', '["UNKNOWN-EVIDENCE"]', 1)
        result = validator.validate(text, expected, "UE-OUT-NEG-001")
        assertions = {row["id"]: row for row in result.to_dict()["assertions"]}
        self.assertEqual(assertions["UE-D003"]["status"], "pass")
        self.assertEqual(assertions["UE-D005"]["status"], "fail")

    def test_fixture_cannot_rewrite_saved_test_result_or_product_risk(self) -> None:
        text, expected = _case("case-001")
        result = validator.validate(text.replace("TC-001 remains PASS", "TC-001 remains FAIL"), expected, "UE-OUT-NEG-002")
        assertions = {row["id"]: row for row in result.to_dict()["assertions"]}
        self.assertEqual(assertions["UE-D007"]["status"], "fail")

    def test_eval_manifest_and_pr12_evidence_fixture_are_present(self) -> None:
        manifest = json.loads((SKILL_ROOT / "evals" / "output" / "evals.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["skill"], "usability-evaluation")
        self.assertEqual({case["id"] for case in manifest["cases"]}, {"UE-OUT-001", "UE-OUT-002"})
        input_text = (SKILL_ROOT / "evals" / "output" / "cases" / "case-001" / "input.md").read_text(encoding="utf-8")
        self.assertIn("assets/output-template.md", input_text)
        evidence = (SKILL_ROOT / "evals" / "output" / "cases" / "case-001" / "evidence" / "test-target-inspection-evidence.md").read_text(encoding="utf-8")
        self.assertIn("## 操作・ふるまい", evidence)
        self.assertIn("## 副作用・cleanup", evidence)
        self.assertIn("## 保存結果", evidence)


if __name__ == "__main__":
    unittest.main()
