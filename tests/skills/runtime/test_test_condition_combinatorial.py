from __future__ import annotations

import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "skills" / "test-condition-design" / "scripts" / "combinatorial.py"
sys.path.insert(0, str(SCRIPT.parent))
SPEC = importlib.util.spec_from_file_location("runtime_test_combinatorial_module", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
combinatorial = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = combinatorial
SPEC.loader.exec_module(combinatorial)


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

    def _run_with_budget(self, value: dict, budget: int) -> tuple[int, dict]:
        request = json.dumps({"metadata": metadata(), "input": value}).encode()
        stdout = io.BytesIO()
        input_stream = type("InputStream", (), {"buffer": io.BytesIO(request)})()
        output_stream = type("OutputStream", (), {"buffer": stdout})()
        with patch.object(combinatorial, "MAX_EXPLORATION_NODES", budget), patch.object(combinatorial, "MAX_FULL_ASSIGNMENTS", 1):
            old_stdin, old_stdout = sys.stdin, sys.stdout
            try:
                sys.stdin, sys.stdout = input_stream, output_stream
                code = combinatorial.run_cli(combinatorial.generate, skill="test-condition-design", generator="combinatorial", generator_contract_version="combinatorial-v1", generator_path=SCRIPT)
            finally:
                sys.stdin, sys.stdout = old_stdin, old_stdout
        return code, json.loads(stdout.getvalue())

    def test_exploration_budget_accumulates_across_tuple_and_greedy_searches(self) -> None:
        value = {"mode": "t-wise", "factors": factors()[:2], "constraints": [], "strength": 2}
        code, exact = self._run_with_budget(value, 24)
        self.assertEqual(code, 0)
        self.assertEqual(exact["runtime_status"], "ok")
        self.assertTrue(exact["payload"]["coverage_summary"]["complete"])

        code, exceeded = self._run_with_budget(value, 23)
        self.assertEqual(code, 0)
        self.assertEqual(exceeded["runtime_status"], "limit_exceeded")
        self.assertEqual(exceeded["result_status"], "blocked")
        self.assertFalse(exceeded["deterministic_generated"])

        # Twelve tuple-feasibility nodes plus the next tuple crosses this
        # invocation-wide budget; it must not reset for each tuple.
        code, cumulative = self._run_with_budget(value, 11)
        self.assertEqual(code, 0)
        self.assertEqual(cumulative["runtime_status"], "limit_exceeded")


if __name__ == "__main__":
    unittest.main()
