from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import unittest


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "skills" / "test-condition-design" / "scripts" / "equivalence_partitions.py"


def metadata() -> dict:
    return {
        "envelope_version": "1",
        "skill": "test-condition-design",
        "runtime_contract_version": "runtime-v1",
        "generator_contract_version": "equivalence-partitions-v1",
        "runtime_unit_key": "model:ep-001",
        "model_key": "ep-001",
        "model_type": "ep",
        "technique_slug": "ep",
        "selection_source": "analysis",
        "selection_key": "SEL-001",
        "scope_key": None,
        "input_mode": "direct",
        "upstream_entities": [],
        "upstream_runtime_units": [],
        "static_data_versions": {},
        "authority_refs": [],
        "reference_refs": [],
    }


def run(input_value: dict) -> dict:
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        input=json.dumps({"metadata": metadata(), "input": input_value}, ensure_ascii=False).encode("utf-8"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=REPO_ROOT,
        check=False,
    )
    if result.stderr:
        raise AssertionError(result.stderr.decode())
    return json.loads(result.stdout)


def enum_partition(key: str, values: list[dict], validity: str = "valid") -> dict:
    return {
        "partition_key": key,
        "label": key.title(),
        "validity": validity,
        "definition": {"type": "enum", "values": values},
        "representative": None,
        "authority_refs": [],
    }


class EquivalencePartitionRuntimeTests(unittest.TestCase):
    def test_each_choice_targets_have_self_contained_execution_and_stable_refs(self) -> None:
        value = {
            "sets": [
                {
                    "set_key": "role",
                    "label": "Role",
                    "partitions": [
                        enum_partition("admin", [{"type": "enum", "value": "admin"}]),
                        enum_partition("user", [{"type": "enum", "value": "user"}]),
                    ],
                }
            ]
        }
        result = run(value)
        self.assertEqual(result["runtime_status"], "ok")
        self.assertEqual(result["result_status"], "ready")
        self.assertEqual(result["payload"]["coverage_summary"], {"criterion": "each-choice", "required": 2, "covered": 2, "complete": True})
        self.assertEqual([row["target_key"] for row in result["payload"]["targets"]], ["ep:role:admin", "ep:role:user"])
        for target in result["payload"]["targets"]:
            self.assertTrue(target["materializable"])
            self.assertIsNotNone(target["execution_fingerprint"])
            self.assertEqual(target["execution"]["partition"]["key"], target["partition"]["key"])
            self.assertTrue(target["target_ref"].startswith("sha256:"))

    def test_partition_and_set_input_order_does_not_change_result_targets(self) -> None:
        first = {
            "sets": [
                {"set_key": "b", "label": "B", "partitions": [enum_partition("z", [{"type": "enum", "value": "z"}])]},
                {"set_key": "a", "label": "A", "partitions": [enum_partition("x", [{"type": "enum", "value": "x"}])]},
            ]
        }
        second = {"sets": list(reversed(first["sets"]))}
        left = run(first)
        right = run(second)
        self.assertEqual(left["input_fingerprint"], right["input_fingerprint"])
        self.assertEqual(left["payload"]["targets"], right["payload"]["targets"])

    def test_overlapping_partitions_are_rejected(self) -> None:
        value = {
            "sets": [
                {
                    "set_key": "x",
                    "label": "X",
                    "partitions": [
                        enum_partition("one", [{"type": "enum", "value": 1}]),
                        enum_partition("also-one", [{"type": "enum", "value": 1}], "invalid"),
                    ],
                }
            ]
        }
        result = run(value)
        self.assertEqual(result["runtime_status"], "invalid_input")
        self.assertEqual(result["result_status"], "blocked")

    def test_non_integer_range_without_representative_is_unresolved(self) -> None:
        value = {
            "sets": [
                {
                    "set_key": "amount",
                    "label": "Amount",
                    "partitions": [
                        {
                            "partition_key": "positive",
                            "label": "Positive",
                            "validity": "valid",
                            "definition": {
                                "type": "range",
                                "minimum": {"type": "decimal", "value": "0.1"},
                                "maximum": {"type": "decimal", "value": "1.0"},
                                "minimum_inclusive": True,
                                "maximum_inclusive": True,
                            },
                            "representative": None,
                            "authority_refs": [],
                        }
                    ],
                }
            ]
        }
        result = run(value)
        self.assertEqual(result["runtime_status"], "ok")
        self.assertEqual(result["result_status"], "unresolved")
        self.assertFalse(result["payload"]["coverage_summary"]["complete"])
        self.assertEqual(result["payload"]["targets"], [])
        self.assertEqual(result["issues"][0]["issue_type"], "unresolved_representative")


if __name__ == "__main__":
    unittest.main()
