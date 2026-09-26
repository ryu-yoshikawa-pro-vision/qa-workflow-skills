from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import unittest


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "skills" / "test-condition-design" / "scripts" / "metamorphic.py"


def metadata() -> dict:
    return {
        "envelope_version": "1", "skill": "test-condition-design", "runtime_contract_version": "runtime-v1", "generator_contract_version": "metamorphic-v1",
        "runtime_unit_key": "model:metamorphic-001", "model_key": "metamorphic-001", "model_type": "metamorphic", "technique_slug": "metamorphic", "selection_source": "condition_design", "selection_key": None,
        "scope_key": None, "input_mode": "direct", "upstream_entities": [], "upstream_runtime_units": [], "static_data_versions": {}, "authority_refs": [], "reference_refs": [],
    }


def run(value: dict) -> dict:
    result = subprocess.run([sys.executable, str(SCRIPT)], input=json.dumps({"metadata": metadata(), "input": value}, ensure_ascii=False).encode(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=REPO_ROOT, check=False)
    if result.stderr:
        raise AssertionError(result.stderr.decode())
    return json.loads(result.stdout)


class MetamorphicRuntimeTests(unittest.TestCase):
    def test_empty_relations_are_invalid_instead_of_vacuous_complete(self) -> None:
        self.assertEqual(run({"relations": []})["runtime_status"], "invalid_input")

    def test_decimal_transforms_are_applied_in_declared_order_and_counted_as_pairs(self) -> None:
        value = {"relations": [{"relation_key": "MR-001", "relation_label": "Total does not decrease", "source_inputs": [{"source_id": "SRC-001", "value": {"amount": {"type": "decimal", "value": "10"}, "items": ["b", "a"]}}], "follow_ups": [{"follow_up_key": "FU-001", "transforms": [{"op": "add_decimal", "path": "$.amount", "operand": "1"}, {"op": "multiply_decimal", "path": "$.amount", "operand": "2"}, {"op": "sort", "path": "$.items", "order": "asc"}]}], "expected_relation": {"op": "monotonic_non_decreasing", "output_path": "$.amount", "output_kind": "decimal"}, "authority_refs": ["SPEC-001"]}]}
        result = run(value)
        self.assertEqual(result["runtime_status"], "ok")
        self.assertEqual(result["payload"]["completion_summary"], {"required_pairs": 1, "generated_pairs": 1, "complete": True})
        execution = result["payload"]["targets"][0]["execution"]
        self.assertEqual(execution["follow_up_value"]["amount"], {"type": "decimal", "value": "22"})
        self.assertEqual(execution["follow_up_value"]["items"], ["a", "b"])

    def test_unsupported_path_is_explicit_and_not_silently_dropped(self) -> None:
        value = {"relations": [{"relation_key": "MR-001", "relation_label": "Relation", "source_inputs": [{"source_id": "SRC-001", "value": {"amount": {"type": "decimal", "value": "10"}}}], "follow_ups": [{"follow_up_key": "FU-001", "transforms": [{"op": "add_decimal", "path": "$.missing", "operand": "1"}]}], "expected_relation": {"op": "equal", "output_path": "$.result", "output_kind": "canonical_json"}, "authority_refs": []}]}
        result = run(value)
        self.assertEqual(result["support_status"], "unsupported")
        self.assertTrue(result["payload"]["unsupported_items"])
        self.assertFalse(result["payload"]["targets"][0]["materializable"])

    def test_relation_kind_compatibility_is_validated_without_product_oracle(self) -> None:
        value = {"relations": [{"relation_key": "MR-001", "relation_label": "Bad monotonic", "source_inputs": [{"source_id": "SRC-001", "value": 1}], "follow_ups": [{"follow_up_key": "FU-001", "transforms": [{"op": "set", "path": "$", "value": {"type": "integer", "value": 2}}]}], "expected_relation": {"op": "monotonic_non_decreasing", "output_path": "$", "output_kind": "string"}, "authority_refs": []}]}
        self.assertEqual(run(value)["runtime_status"], "invalid_input")


if __name__ == "__main__":
    unittest.main()
