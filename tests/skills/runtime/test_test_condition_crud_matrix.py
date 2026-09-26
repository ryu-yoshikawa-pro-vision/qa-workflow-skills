from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import unittest


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "skills" / "test-condition-design" / "scripts" / "crud_matrix.py"


def metadata() -> dict:
    return {
        "envelope_version": "1", "skill": "test-condition-design", "runtime_contract_version": "runtime-v1", "generator_contract_version": "crud-matrix-v1",
        "runtime_unit_key": "model:crud-001", "model_key": "crud-001", "model_type": "crud", "technique_slug": "crud", "selection_source": "condition_design", "selection_key": None,
        "scope_key": None, "input_mode": "direct", "upstream_entities": [], "upstream_runtime_units": [], "static_data_versions": {}, "authority_refs": [], "reference_refs": [],
    }


def run(value: dict) -> dict:
    result = subprocess.run([sys.executable, str(SCRIPT)], input=json.dumps({"metadata": metadata(), "input": value}, ensure_ascii=False).encode(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=REPO_ROOT, check=False)
    if result.stderr:
        raise AssertionError(result.stderr.decode())
    return json.loads(result.stdout)


def base() -> dict:
    return {
        "entities": [{"entity_key": "customer", "label": "Customer", "authority_refs": ["SPEC-001"]}],
        "functions": [{"function_key": "customer_lifecycle", "label": "Customer lifecycle", "authority_refs": ["SPEC-001"]}],
        "cells": [{"entity_key": "customer", "function_key": "customer_lifecycle", "operations": ["C", "R", "U", "D"], "authority_refs": []}],
        "consistency_sequences": [{"sequence_key": "SEQ-001", "entity_key": "customer", "kind": "lifecycle", "steps": [{"function_key": "customer_lifecycle", "operation": "C"}, {"function_key": "customer_lifecycle", "operation": "R"}, {"function_key": "customer_lifecycle", "operation": "U"}, {"function_key": "customer_lifecycle", "operation": "D"}], "authority_refs": ["SPEC-002"]}],
        "operation_dispositions": [],
    }


class CrudMatrixRuntimeTests(unittest.TestCase):
    def test_completeness_and_consistency_are_separate_and_labels_are_in_execution(self) -> None:
        result = run(base())
        self.assertEqual(result["runtime_status"], "ok")
        self.assertEqual(result["result_status"], "ready")
        summary = result["payload"]["coverage_summary"]
        self.assertTrue(summary["completeness"]["complete"])
        self.assertTrue(summary["consistency"]["complete"])
        operation = next(row for row in result["payload"]["targets"] if row["target_key"] == "crud:op:customer:customer_lifecycle:C")
        self.assertEqual(operation["execution"]["entity_label"], "Customer")
        sequence = next(row for row in result["payload"]["targets"] if row["target_key"] == "crud:seq:SEQ-001")
        self.assertEqual(sequence["execution"]["steps"][0]["function_label"], "Customer lifecycle")

    def test_missing_operation_requires_authority_backed_not_applicable(self) -> None:
        value = base()
        value["cells"][0]["operations"] = ["C", "R"]
        value["consistency_sequences"][0]["steps"] = [{"function_key": "customer_lifecycle", "operation": "C"}, {"function_key": "customer_lifecycle", "operation": "R"}]
        unresolved = run(value)
        self.assertEqual(unresolved["result_status"], "unresolved")
        self.assertFalse(unresolved["payload"]["coverage_summary"]["completeness"]["complete"])
        self.assertEqual(unresolved["issues"][0]["issue_type"], "missing_operation_disposition")
        value["operation_dispositions"] = [
            {"entity_key": "customer", "operation": "U", "handling": "not_applicable", "reason": "immutable by design", "authority_refs": ["SPEC-003"]},
            {"entity_key": "customer", "operation": "D", "handling": "not_applicable", "reason": "retention policy", "authority_refs": ["SPEC-004"]},
        ]
        resolved = run(value)
        self.assertEqual(resolved["result_status"], "ready")
        self.assertEqual(resolved["payload"]["coverage_summary"]["completeness"]["covered"], 4)

    def test_sequence_cannot_invent_operation(self) -> None:
        value = base()
        value["consistency_sequences"][0]["steps"][0]["operation"] = "U"
        value["cells"][0]["operations"] = ["C", "R"]
        self.assertEqual(run(value)["runtime_status"], "invalid_input")


if __name__ == "__main__":
    unittest.main()
