from __future__ import annotations

import hashlib
import json
from decimal import Decimal
from pathlib import Path
import re
import subprocess
import sys
import unittest

from scripts.skills.evals.deterministic.result import EvalResult
from scripts.skills.evals.deterministic.runtime_validator import _digest, validate_runtime_evidence


REPO_ROOT = Path(__file__).resolve().parents[5]


def _fixture_digest(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _artifact() -> str:
    metadata = {
        "envelope_version": "1", "skill": "test-condition-design", "runtime_contract_version": "runtime-v1",
        "generator_contract_version": "equivalence-partitions-v1", "runtime_unit_key": "model:ep-001", "model_key": "ep-001",
        "model_type": "ep", "technique_slug": "ep", "selection_source": "condition_design", "selection_key": None,
        "scope_key": None, "input_mode": "direct", "upstream_entities": [], "upstream_runtime_units": [],
        "static_data_versions": {}, "authority_refs": [], "reference_refs": [],
    }
    request = {
        "metadata": metadata,
        "input": {"sets": []},
    }
    completed = subprocess.run(
        [sys.executable, str(REPO_ROOT / "skills/test-condition-design/scripts/equivalence_partitions.py")],
        input=json.dumps(request, ensure_ascii=False).encode("utf-8"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=REPO_ROOT,
        check=False,
    )
    if completed.returncode != 0 or completed.stderr:
        raise AssertionError(completed.stderr.decode("utf-8", errors="replace"))
    result = json.loads(completed.stdout)
    entity_content = {"value": "stable"}
    entity = {
        "schema_version": "entity-state-v1", "skill": "test-condition-design", "entity_type": "model", "entity_ref": "ep-001", "model_key": "ep-001",
        "content": entity_content, "content_fingerprint": _fixture_digest(entity_content), "upstream_entity_dependencies": [], "runtime_dependencies": [],
    }
    fence = lambda value: "```json\n" + json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n```"
    return "\n".join([
        "### Machine Runtime Input: test-condition-design::model:ep-001", "", fence({"metadata": metadata, "input": {"sets": []}}),
        "### Machine Runtime Result: test-condition-design::model:ep-001", "", fence(result),
        "### Machine Entities: test-condition-design", "", fence({"schema_version": "entity-state-v1", "skill": "test-condition-design", "entities": [entity]}), "",
    ])


class RuntimeValidatorTests(unittest.TestCase):
    def test_decimal_fingerprint_uses_exact_canonical_number(self) -> None:
        expected = "sha256:" + hashlib.sha256(b'{"n":1}').hexdigest()
        self.assertEqual(_digest({"n": Decimal("1.0")}), expected)
        self.assertEqual(_digest({"n": Decimal("1.00")}), expected)

    def test_declared_runtime_and_entity_contract_passes(self) -> None:
        expected = {
            "runtime_contract": {
                "expected_runtime_units": [{"skill": "test-condition-design", "runtime_unit_key": "model:ep-001"}],
                "expected_generators": {"test-condition-design::model:ep-001": "equivalence_partitions"},
                "expected_targets": {"test-condition-design::model:ep-001": []},
            },
            "machine_entities": {"expected_entities": [{"skill": "test-condition-design", "entity_type": "model", "entity_ref": "ep-001"}]},
        }
        result = EvalResult("test-condition-design", "TCN-OUT-001")
        validate_runtime_evidence(_artifact(), expected, result)
        self.assertEqual(result.status, "pass")

    def test_missing_result_is_a_pair_failure(self) -> None:
        expected = {"expected_runtime_units": [{"skill": "test-condition-design", "runtime_unit_key": "model:ep-001"}]}
        text = _artifact().replace("### Machine Runtime Result: test-condition-design::model:ep-001\n\n", "")
        result = EvalResult("test-condition-design", "TCN-OUT-002")
        validate_runtime_evidence(text, expected, result)
        self.assertEqual(result.status, "fail")

    def test_fingerprint_tampering_is_detected_without_expected_hash_fixture(self) -> None:
        expected = {
            "runtime_contract": {
                "expected_runtime_units": [{"skill": "test-condition-design", "runtime_unit_key": "model:ep-001"}],
            },
        }
        text = re.sub(r'("input_fingerprint":")[^"]+', r'\1sha256:' + "0" * 64, _artifact(), count=1)
        result = EvalResult("test-condition-design", "TCN-OUT-003")
        validate_runtime_evidence(text, expected, result)
        self.assertEqual(result.status, "fail")

    def test_duplicate_machine_entity_block_is_detected(self) -> None:
        expected = {
            "runtime_contract": {
                "expected_runtime_units": [{"skill": "test-condition-design", "runtime_unit_key": "model:ep-001"}],
            },
            "machine_entities": {"expected_entities": [{"skill": "test-condition-design", "entity_type": "model", "entity_ref": "ep-001"}]},
        }
        text = _artifact()
        entity_block = text.split("### Machine Entities: test-condition-design", 1)[1]
        text = text + "### Machine Entities: test-condition-design" + entity_block
        result = EvalResult("test-condition-design", "TCN-OUT-004")
        validate_runtime_evidence(text, expected, result)
        self.assertEqual(result.status, "fail")


if __name__ == "__main__":
    unittest.main()
