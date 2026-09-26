from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import unittest


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "skills" / "test-condition-design" / "scripts" / "cause_effect.py"


def metadata() -> dict:
    return {
        "envelope_version": "1", "skill": "test-condition-design", "runtime_contract_version": "runtime-v1", "generator_contract_version": "cause-effect-v1",
        "runtime_unit_key": "model:cause-effect-001", "model_key": "cause-effect-001", "model_type": "cause-effect", "technique_slug": None, "selection_source": None, "selection_key": None,
        "scope_key": None, "input_mode": "direct", "upstream_entities": [], "upstream_runtime_units": [], "static_data_versions": {}, "authority_refs": [], "reference_refs": [],
    }


def run(value: dict) -> dict:
    result = subprocess.run([sys.executable, str(SCRIPT)], input=json.dumps({"metadata": metadata(), "input": value}, ensure_ascii=False).encode(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=REPO_ROOT, check=False)
    if result.stderr:
        raise AssertionError(result.stderr.decode())
    return json.loads(result.stdout)


class CauseEffectRuntimeTests(unittest.TestCase):
    def test_boolean_graph_is_directly_compatible_with_decision_child(self) -> None:
        value = {
            "causes": [
                {"cause_key": "C1", "label": "Payment valid", "authority_refs": ["SPEC-001"]},
                {"cause_key": "C2", "label": "Account active", "authority_refs": ["SPEC-001"]},
            ],
            "effects": [{"effect_key": "E1", "label": "Accept", "expression": {"op": "and", "args": [{"op": "ref", "key": "C1"}, {"op": "ref", "key": "C2"}]}, "true_value": {"type": "enum", "value": "allow"}, "false_value": {"type": "enum", "value": "deny"}, "authority_refs": ["SPEC-002"]}],
            "constraints": [],
            "child_models": [{"child_model_key": "decision-child", "model_type": "decision", "derived_from_model_key": "cause-effect-001", "semantic_parameters": None}],
        }
        result = run(value)
        self.assertEqual(result["runtime_status"], "ok")
        self.assertEqual(result["result_status"], "ready")
        self.assertEqual(len(result["payload"]["targets"]), 4)
        child = result["payload"]["derived_child_inputs"][0]
        self.assertEqual(child["model_type"], "decision")
        self.assertEqual(child["input"]["accepted_merges"], [])
        self.assertEqual(len(child["input"]["known_rules"]), 4)
        self.assertEqual(child["input"]["conditions"][0]["values"], [{"type": "boolean", "value": False}, {"type": "boolean", "value": True}])

    def test_constraint_excludes_assignment_and_invalid_effect_ref_is_rejected(self) -> None:
        value = {
            "causes": [{"cause_key": "C1", "label": "Flag", "authority_refs": []}],
            "effects": [{"effect_key": "E1", "label": "Outcome", "expression": {"op": "ref", "key": "C1"}, "true_value": {"type": "boolean", "value": True}, "false_value": {"type": "boolean", "value": False}, "authority_refs": []}],
            "constraints": [{"constraint_key": "C-1", "assignment": {"C1": {"type": "boolean", "value": False}}, "authority_refs": ["SPEC-003"]}],
            "child_models": [{"child_model_key": "decision-child", "model_type": "decision", "derived_from_model_key": "cause-effect-001", "semantic_parameters": None}],
        }
        result = run(value)
        self.assertEqual(result["runtime_status"], "ok")
        self.assertEqual(len(result["payload"]["targets"]), 1)
        value["effects"][0]["expression"] = {"op": "ref", "key": "E1"}
        self.assertEqual(run(value)["runtime_status"], "invalid_input")


if __name__ == "__main__":
    unittest.main()
