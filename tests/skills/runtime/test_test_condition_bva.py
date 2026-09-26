from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import unittest


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "skills" / "test-condition-design" / "scripts" / "bva.py"


def metadata() -> dict:
    return {
        "envelope_version": "1", "skill": "test-condition-design", "runtime_contract_version": "runtime-v1", "generator_contract_version": "bva-v1",
        "runtime_unit_key": "model:bva-001", "model_key": "bva-001", "model_type": "bva", "technique_slug": "bva", "selection_source": "condition_design", "selection_key": None,
        "scope_key": None, "input_mode": "direct", "upstream_entities": [], "upstream_runtime_units": [], "static_data_versions": {}, "authority_refs": [], "reference_refs": [],
    }


def run(value: dict) -> dict:
    result = subprocess.run([sys.executable, str(SCRIPT)], input=json.dumps({"metadata": metadata(), "input": value}, ensure_ascii=False).encode(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=REPO_ROOT, check=False)
    if result.stderr:
        raise AssertionError(result.stderr.decode())
    return json.loads(result.stdout)


class BvaRuntimeTests(unittest.TestCase):
    def test_empty_boundaries_are_invalid_instead_of_vacuous_complete(self) -> None:
        self.assertEqual(run({"boundaries": []})["runtime_status"], "invalid_input")

    def test_two_value_lower_inclusive_and_three_value_are_exact(self) -> None:
        result = run({"boundaries": [
            {"boundary_key": "amount", "label": "Amount", "side": "lower", "threshold": {"type": "integer", "value": 10}, "inclusive": True, "step": {"unit": "integer", "amount": 1}, "mode": "2-value", "coverage_selection_reason": "", "authority_refs": []},
            {"boundary_key": "ratio", "label": "Ratio", "side": "upper", "threshold": {"type": "decimal", "value": "1.25"}, "inclusive": False, "step": {"unit": "decimal", "amount": "0.1"}, "mode": "3-value", "coverage_selection_reason": "explicit risk", "authority_refs": []},
        ]})
        self.assertEqual(result["runtime_status"], "ok")
        values = {(row["boundary_key"], row["position"]): row["value"] for row in result["payload"]["targets"]}
        self.assertEqual(values[("amount", "AT")], {"type": "integer", "value": 10})
        self.assertEqual(values[("amount", "OTHER")], {"type": "integer", "value": 9})
        self.assertEqual(values[("ratio", "BELOW")], {"type": "decimal", "value": "1.15"})
        self.assertEqual(values[("ratio", "ABOVE")], {"type": "decimal", "value": "1.35"})
        self.assertTrue(all(row["target_ref"].startswith("sha256:") for row in result["payload"]["targets"]))

    def test_three_value_requires_reason_and_step_type_matches_threshold(self) -> None:
        base = {"boundary_key": "d", "label": "Date", "side": "lower", "threshold": {"type": "date", "value": "2026-01-01"}, "inclusive": True, "step": {"unit": "day", "amount": 1}, "mode": "3-value", "coverage_selection_reason": "", "authority_refs": []}
        self.assertEqual(run({"boundaries": [base]})["runtime_status"], "invalid_input")
        base["coverage_selection_reason"] = "incident"
        base["step"] = {"unit": "second", "amount": 1}
        self.assertEqual(run({"boundaries": [base]})["runtime_status"], "invalid_input")


if __name__ == "__main__":
    unittest.main()
