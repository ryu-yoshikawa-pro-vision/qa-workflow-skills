from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import unittest


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "skills" / "test-condition-design" / "scripts" / "domain_testing.py"


def metadata() -> dict:
    return {
        "envelope_version": "1", "skill": "test-condition-design", "runtime_contract_version": "runtime-v1", "generator_contract_version": "domain-testing-v1",
        "runtime_unit_key": "model:domain-001", "model_key": "domain-001", "model_type": "domain", "technique_slug": "domain", "selection_source": "condition_design", "selection_key": None,
        "scope_key": None, "input_mode": "direct", "upstream_entities": [], "upstream_runtime_units": [], "static_data_versions": {}, "authority_refs": [], "reference_refs": [],
    }


def run(value: dict) -> dict:
    result = subprocess.run([sys.executable, str(SCRIPT)], input=json.dumps({"metadata": metadata(), "input": value}, ensure_ascii=False).encode(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=REPO_ROOT, check=False)
    if result.stderr:
        raise AssertionError(result.stderr.decode())
    return json.loads(result.stdout)


class DomainTestingRuntimeTests(unittest.TestCase):
    def test_empty_domain_inputs_are_invalid_instead_of_vacuous_complete(self) -> None:
        self.assertEqual(run({"partitions": [], "borders": []})["runtime_status"], "invalid_input")

    def test_closed_border_reliable_domain_points_use_exact_values(self) -> None:
        value = {
            "partitions": [{"partition_key": "valid", "label": "Valid", "dimensions": [{"dimension_key": "x", "label": "X"}], "expression": {"op": "border_ref", "border_key": "b1"}, "authority_refs": []}],
            "borders": [{"border_key": "b1", "label": "x <= 10", "partition_key": "valid", "relation": "<=", "coefficients": {"x": "1"}, "constant": "-10", "pivot_key": "x", "anchor": {}, "pivot_step": "1", "authority_refs": []}],
        }
        result = run(value)
        self.assertEqual(result["runtime_status"], "ok")
        self.assertEqual(result["result_status"], "ready")
        values = {row["position"]: row["values"]["x"] for row in result["payload"]["targets"]}
        self.assertEqual(values["ON"], {"type": "integer", "value": 10})
        self.assertEqual(values["OFF"], {"type": "integer", "value": 11})
        self.assertEqual(values["IN"], {"type": "integer", "value": 9})
        self.assertEqual(values["OUT"], {"type": "integer", "value": 12})

    def test_expression_must_reference_known_border_and_nonzero_pivot(self) -> None:
        value = {"partitions": [{"partition_key": "p", "label": "P", "dimensions": [{"dimension_key": "x", "label": "X"}], "expression": {"op": "border_ref", "border_key": "missing"}, "authority_refs": []}], "borders": []}
        self.assertEqual(run(value)["runtime_status"], "invalid_input")
        value["partitions"][0]["expression"] = {"op": "border_ref", "border_key": "b"}
        value["borders"] = [{"border_key": "b", "label": "bad", "partition_key": "p", "relation": "<=", "coefficients": {"x": "0"}, "constant": "0", "pivot_key": "x", "anchor": {}, "pivot_step": "1", "authority_refs": []}]
        self.assertEqual(run(value)["runtime_status"], "invalid_input")


if __name__ == "__main__":
    unittest.main()
