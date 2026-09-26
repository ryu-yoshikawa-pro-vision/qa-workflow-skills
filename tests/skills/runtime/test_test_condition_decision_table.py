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
SCRIPT = REPO_ROOT / "skills" / "test-condition-design" / "scripts" / "decision_table.py"
sys.path.insert(0, str(SCRIPT.parent))
SPEC = importlib.util.spec_from_file_location("runtime_test_decision_table_module", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
decision_table = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = decision_table
SPEC.loader.exec_module(decision_table)


def metadata() -> dict:
    return {
        "envelope_version": "1", "skill": "test-condition-design", "runtime_contract_version": "runtime-v1", "generator_contract_version": "decision-table-v1",
        "runtime_unit_key": "model:decision-001", "model_key": "decision-001", "model_type": "decision", "technique_slug": "decision", "selection_source": "condition_design", "selection_key": None,
        "scope_key": None, "input_mode": "direct", "upstream_entities": [], "upstream_runtime_units": [], "static_data_versions": {}, "authority_refs": [], "reference_refs": [],
    }


def run(value: dict) -> dict:
    result = subprocess.run([sys.executable, str(SCRIPT)], input=json.dumps({"metadata": metadata(), "input": value}, ensure_ascii=False).encode(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=REPO_ROOT, check=False)
    if result.stderr:
        raise AssertionError(result.stderr.decode())
    return json.loads(result.stdout)


def tv(kind: str, value) -> dict:
    return {"type": kind, "value": value}


def base_rules() -> dict:
    return {
        "conditions": [
            {"condition_key": "logged_in", "label": "Logged in", "values": [tv("boolean", False), tv("boolean", True)], "authority_refs": ["SPEC-001"]},
            {"condition_key": "active", "label": "Active", "values": [tv("boolean", False), tv("boolean", True)], "authority_refs": ["SPEC-001"]},
        ],
        "actions": [{"action_key": "allow", "label": "Allow", "values": [tv("boolean", False), tv("boolean", True)], "authority_refs": ["SPEC-001"]}],
        "known_rules": [
            {"rule_key": "R-1", "when": {"logged_in": tv("boolean", False), "active": tv("boolean", False)}, "then": {"allow": tv("boolean", False)}, "authority_refs": ["SPEC-001"]},
            {"rule_key": "R-2", "when": {"logged_in": tv("boolean", False), "active": tv("boolean", True)}, "then": {"allow": tv("boolean", False)}, "authority_refs": ["SPEC-001"]},
            {"rule_key": "R-3", "when": {"logged_in": tv("boolean", True), "active": tv("boolean", False)}, "then": {"allow": tv("boolean", False)}, "authority_refs": ["SPEC-001"]},
            {"rule_key": "R-4", "when": {"logged_in": tv("boolean", True), "active": tv("boolean", True)}, "then": {"allow": tv("boolean", True)}, "authority_refs": ["SPEC-001"]},
        ],
        "constraints": [],
        "accepted_merges": [],
    }


class DecisionTableRuntimeTests(unittest.TestCase):
    def test_cartesian_rules_are_stable_and_generate_non_destructive_dont_care_candidate(self) -> None:
        result = run(base_rules())
        self.assertEqual(result["runtime_status"], "ok")
        self.assertEqual(result["result_status"], "ready")
        self.assertEqual(result["payload"]["coverage_summary"], {"criterion": "decision-rules", "required": 4, "covered": 4, "complete": True})
        self.assertEqual(len(result["payload"]["targets"]), 4)
        candidates = result["payload"]["dont_care_candidates"]
        self.assertEqual(len(candidates), 2)
        self.assertEqual({row["condition_key"] for row in candidates}, {"active", "logged_in"})
        self.assertEqual(result["payload"]["dont_care_rules"], [])
        self.assertTrue(all(row["target_key"].startswith("dt:h") for row in result["payload"]["targets"]))

    def test_constraint_leaves_unspecified_assignment_unresolved_and_does_not_hide_target(self) -> None:
        value = base_rules()
        value["constraints"] = [{"constraint_key": "C-1", "assignment": {"logged_in": tv("boolean", False)}, "authority_refs": ["SPEC-002"]}]
        value["known_rules"] = value["known_rules"][2:]
        result = run(value)
        self.assertEqual(result["result_status"], "ready")
        self.assertEqual(result["payload"]["coverage_summary"]["required"], 2)
        self.assertEqual(result["payload"]["coverage_summary"]["covered"], 2)
        self.assertTrue(result["payload"]["coverage_summary"]["complete"])

    def test_accepted_merge_must_be_a_generated_candidate(self) -> None:
        value = base_rules()
        value["accepted_merges"] = ["dm:h" + "0" * 64]
        result = run(value)
        self.assertEqual(result["runtime_status"], "ok")
        self.assertEqual(result["result_status"], "unresolved")
        self.assertEqual(result["issues"][0]["issue_type"], "invalid_accepted_merge")

    def _run_with_rule_limit(self, value: dict, limit: int) -> tuple[int, dict]:
        request = json.dumps({"metadata": metadata(), "input": value}).encode()
        stdout = io.BytesIO()
        input_stream = type("InputStream", (), {"buffer": io.BytesIO(request)})()
        output_stream = type("OutputStream", (), {"buffer": stdout})()
        with patch.object(decision_table, "MAX_RULES", limit):
            old_stdin, old_stdout = sys.stdin, sys.stdout
            try:
                sys.stdin, sys.stdout = input_stream, output_stream
                code = decision_table.run_cli(decision_table.generate, skill="test-condition-design", generator="decision_table", generator_contract_version="decision-table-v1", generator_path=SCRIPT)
            finally:
                sys.stdin, sys.stdout = old_stdin, old_stdout
        return code, json.loads(stdout.getvalue())

    def test_rule_space_limit_boundary_and_structured_exit_status(self) -> None:
        value = base_rules()
        value["conditions"] = [
            {"condition_key": f"c{index:02d}", "label": f"Condition {index}", "values": [tv("boolean", False), tv("boolean", True)], "authority_refs": []}
            for index in range(2)
        ]
        value["known_rules"] = []
        code, exact = self._run_with_rule_limit(value, 4)
        self.assertEqual(code, 0)
        self.assertEqual(exact["runtime_status"], "ok")

        value["conditions"].append({"condition_key": "c02", "label": "Condition 2", "values": [tv("boolean", False), tv("boolean", True)], "authority_refs": []})
        code, exceeded = self._run_with_rule_limit(value, 4)
        self.assertEqual(code, 0)
        self.assertEqual(exceeded["runtime_status"], "limit_exceeded")
        self.assertEqual(exceeded["result_status"], "blocked")
        self.assertFalse(exceeded["deterministic_generated"])


if __name__ == "__main__":
    unittest.main()
