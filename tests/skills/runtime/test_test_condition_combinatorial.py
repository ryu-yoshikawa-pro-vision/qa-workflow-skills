from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import unittest


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "skills" / "test-condition-design" / "scripts" / "combinatorial.py"


def metadata() -> dict:
    return {
        "envelope_version": "1", "skill": "test-condition-design", "runtime_contract_version": "runtime-v1", "generator_contract_version": "combinatorial-v1",
        "runtime_unit_key": "model:comb-001", "model_key": "comb-001", "model_type": "comb", "technique_slug": "comb", "selection_source": "condition_design", "selection_key": None,
        "scope_key": None, "input_mode": "direct", "upstream_entities": [], "upstream_runtime_units": [], "static_data_versions": {}, "authority_refs": [], "reference_refs": [],
    }


def run(value: dict) -> dict:
    result = subprocess.run([sys.executable, str(SCRIPT)], input=json.dumps({"metadata": metadata(), "input": value}, ensure_ascii=False).encode(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=REPO_ROOT, check=False)
    if result.stderr:
        raise AssertionError(result.stderr.decode())
    return json.loads(result.stdout)


def factors():
    return [
        {"factor_key": "role", "label": "Role", "values": [{"type": "enum", "value": "admin"}, {"type": "enum", "value": "user"}], "authority_refs": []},
        {"factor_key": "region", "label": "Region", "values": [{"type": "enum", "value": "jp"}, {"type": "enum", "value": "us"}], "authority_refs": []},
        {"factor_key": "plan", "label": "Plan", "values": [{"type": "enum", "value": "free"}, {"type": "enum", "value": "pro"}], "authority_refs": []},
    ]


class CombinatorialRuntimeTests(unittest.TestCase):
    def test_exhaustive_and_base_choice_have_constraint_aware_rows(self) -> None:
        value = {"mode": "exhaustive", "factors": factors()[:2], "constraints": [{"constraint_key": "C-1", "assignment": {"role": {"type": "enum", "value": "guest"}}, "authority_refs": ["SPEC-001"]}]}
        # Unknown constraint values are rejected instead of being treated as a
        # hidden complement.
        self.assertEqual(run(value)["runtime_status"], "invalid_input")
        value["constraints"] = []
        result = run(value)
        self.assertEqual(result["payload"]["coverage_summary"]["required"], 4)
        base = {"mode": "base-choice", "factors": factors()[:2], "constraints": [], "base_assignment": {"role": {"type": "enum", "value": "admin"}, "region": {"type": "enum", "value": "jp"}}}
        base_result = run(base)
        self.assertEqual(base_result["runtime_status"], "ok")
        self.assertEqual(len(base_result["payload"]["rows"]), 3)
        self.assertTrue(all(row["target_key"].startswith("comb:base-choice:h") for row in base_result["payload"]["targets"]))

    def test_pairwise_greedy_covers_sat_tuples_and_requires_reason_for_threewise(self) -> None:
        value = {"mode": "t-wise", "factors": factors(), "constraints": [], "strength": 2}
        result = run(value)
        self.assertEqual(result["runtime_status"], "ok")
        self.assertTrue(result["payload"]["coverage_summary"]["complete"])
        self.assertGreaterEqual(len(result["payload"]["targets"]), 12)
        no_reason = {**value, "strength": 3}
        self.assertEqual(run(no_reason)["runtime_status"], "invalid_input")
        with_reason = {**no_reason, "coverage_selection_reason": "risk-based 3-wise selection"}
        self.assertEqual(run(with_reason)["runtime_status"], "ok")

    def test_mixed_strength_deduplicates_global_and_subset_targets(self) -> None:
        value = {"mode": "mixed-strength", "factors": factors(), "constraints": [], "global_strength": 2, "subsets": [{"factor_keys": ["role", "region", "plan"], "strength": 3}], "coverage_selection_reason": "critical interaction"}
        result = run(value)
        self.assertEqual(result["runtime_status"], "ok")
        self.assertEqual(len(result["payload"]["targets"]), len({row["target_ref"] for row in result["payload"]["targets"]}))
        self.assertTrue(result["payload"]["coverage_summary"]["complete"])


if __name__ == "__main__":
    unittest.main()
