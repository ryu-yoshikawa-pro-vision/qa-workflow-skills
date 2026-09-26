from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import unittest


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "skills" / "test-condition-design" / "scripts" / "classification_tree.py"


def metadata() -> dict:
    return {
        "envelope_version": "1", "skill": "test-condition-design", "runtime_contract_version": "runtime-v1", "generator_contract_version": "classification-tree-v1",
        "runtime_unit_key": "model:classification-001", "model_key": "classification-001", "model_type": "classification", "technique_slug": None, "selection_source": None, "selection_key": None,
        "scope_key": None, "input_mode": "direct", "upstream_entities": [], "upstream_runtime_units": [], "static_data_versions": {}, "authority_refs": [], "reference_refs": [],
    }


def run(value: dict) -> dict:
    result = subprocess.run([sys.executable, str(SCRIPT)], input=json.dumps({"metadata": metadata(), "input": value}, ensure_ascii=False).encode(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=REPO_ROOT, check=False)
    if result.stderr:
        raise AssertionError(result.stderr.decode())
    return json.loads(result.stdout)


def value(semantic=None):
    return {
        "classifications": [{"classification_key": "role", "label": "Role", "classes": [{"class_key": "admin", "value": {"type": "enum", "value": "admin"}, "authority_refs": []}, {"class_key": "user", "value": {"type": "enum", "value": "user"}, "authority_refs": []}], "authority_refs": ["SPEC-001"]}],
        "constraints": [],
        "child_models": [{"child_model_key": "comb-child", "model_type": "comb", "derived_from_model_key": "classification-001", "semantic_parameters": semantic}],
    }


class ClassificationTreeRuntimeTests(unittest.TestCase):
    def test_skeleton_requires_only_semantic_strategy_and_preserves_child_input(self) -> None:
        unresolved = run(value())
        self.assertEqual(unresolved["result_status"], "unresolved")
        self.assertEqual(unresolved["payload"]["derived_child_inputs"], [])
        self.assertTrue(unresolved["payload"]["semantic_parameter_requests"])
        ready = run(value({"mode": "exhaustive"}))
        self.assertEqual(ready["result_status"], "ready")
        child_input = ready["payload"]["derived_child_inputs"][0]["input"]
        self.assertEqual(child_input["factors"], ready["payload"]["factors"])
        self.assertEqual(child_input["constraints"], [])

    def test_strategy_unknown_fields_and_duplicate_class_values_are_not_silently_dropped(self) -> None:
        self.assertEqual(run(value({"mode": "exhaustive", "unexpected": True}))["runtime_status"], "invalid_input")
        duplicate = value()
        duplicate["classifications"][0]["classes"][1]["value"] = duplicate["classifications"][0]["classes"][0]["value"]
        self.assertEqual(run(duplicate)["runtime_status"], "invalid_input")


if __name__ == "__main__":
    unittest.main()
