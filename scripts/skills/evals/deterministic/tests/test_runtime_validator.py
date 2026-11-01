from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from scripts.skills.evals.deterministic.result import EvalResult
from scripts.skills.evals.deterministic.runtime_validator import (
    _canonical_text,
    _digest,
    validate_runtime_evidence,
    validate_skill_local_runtime_evidence,
)

REPO_ROOT = Path(__file__).resolve().parents[5]


def _fixture_digest(value: object) -> str:
    raw = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode()
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _artifact(source_root: Path | None = None) -> str:
    source_root = source_root or REPO_ROOT
    metadata = {
        "envelope_version": "1",
        "skill": "test-condition-design",
        "runtime_contract_version": "runtime-v2",
        "generator_contract_version": "equivalence-partitions-v1",
        "runtime_unit_key": "model:ep-001",
        "model_key": "ep-001",
        "model_type": "ep",
        "technique_slug": "ep",
        "selection_source": "condition_design",
        "selection_key": None,
        "scope_key": None,
        "input_mode": "direct",
        "upstream_entities": [],
        "upstream_runtime_units": [],
        "static_data_versions": {},
        "authority_refs": [],
        "reference_refs": [],
    }
    request = {
        "metadata": metadata,
        "input": {"sets": []},
    }
    completed = subprocess.run(
        [
            sys.executable,
            str(
                source_root
                / "skills/test-condition-design/scripts/equivalence_partitions.py"
            ),
        ],
        input=json.dumps(request, ensure_ascii=False).encode("utf-8"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=source_root,
        check=False,
    )
    if completed.returncode != 0 or completed.stderr:
        raise AssertionError(completed.stderr.decode("utf-8", errors="replace"))
    result = json.loads(completed.stdout)
    entity_content = {"value": "stable"}
    entity = {
        "schema_version": "entity-state-v2",
        "skill": "test-condition-design",
        "entity_type": "model",
        "entity_ref": "ep-001",
        "model_key": "ep-001",
        "content": entity_content,
        "content_fingerprint": _fixture_digest(entity_content),
        "upstream_entity_dependencies": [],
        "runtime_dependencies": [],
    }

    def fence(value):
        return (
            "```json\n"
            + json.dumps(
                value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            )
            + "\n```"
        )

    return "\n".join(
        [
            "### Machine Runtime Input: test-condition-design::model:ep-001",
            "",
            fence({"metadata": metadata, "input": {"sets": []}}),
            "### Machine Runtime Result: test-condition-design::model:ep-001",
            "",
            fence(result),
            "### Machine Entities: test-condition-design",
            "",
            fence(
                {
                    "schema_version": "entity-state-v2",
                    "skill": "test-condition-design",
                    "entities": [entity],
                }
            ),
            "",
        ]
    )


class RuntimeValidatorTests(unittest.TestCase):
    def test_decimal_fingerprint_uses_exact_canonical_number(self) -> None:
        expected = "sha256:" + hashlib.sha256(b'{"n":1}').hexdigest()
        self.assertEqual(_digest({"n": Decimal("1.0")}), expected)
        self.assertEqual(_digest({"n": Decimal("1.00")}), expected)

    def _skill_runtime_artifact(self) -> str:
        identity = "example-skill::artifact:example:all"
        input_body = {
            "metadata": {
                "skill": "example-skill",
                "runtime_unit_key": "artifact:example:all",
            },
            "input": {"amount": Decimal("1.25")},
        }
        entities_body = {
            "schema_version": "entity-state-v2",
            "skill": "example-skill",
            "entities": [],
        }
        return "\n".join(
            [
                (
                    f"### Machine Runtime Input: {identity}\n\n"
                    f"```json\n{_canonical_text(input_body)}\n```"
                ),
                (
                    f"### Machine Runtime Result: {identity}\n\n"
                    "```json\n"
                    f"{_canonical_text({'runtime_status': 'blocked'})}\n```"
                ),
                (
                    "### Machine Entities: example-skill\n\n"
                    f"```json\n{_canonical_text(entities_body)}\n```"
                ),
            ]
        )

    def _write_fake_runtime_verifier(
        self, root: Path, *, valid: bool = True, exit_code: int = 0
    ) -> None:
        verifier = root / "skills/example-skill/scripts/runtime_contract.py"
        verifier.parent.mkdir(parents=True)
        verifier.write_text(
            "import json, sys\n"
            "request = json.load(sys.stdin)\n"
            "assert request['operation'] == 'verify_runtime_evidence'\n"
            "assert request['normalized_skill_input']['amount'] == 1.25\n"
            "assert request['partial_rerun'] is False\n"
            f"issues = [] if {valid!r} else [{{'issue_type': 'synthetic_invalid'}}]\n"
            f"sys.stdout.write(json.dumps({{'valid': {valid!r}, 'issues': issues}}))\n"
            f"sys.exit({exit_code})\n",
            encoding="utf-8",
        )

    def test_skill_runtime_gate_accepts_valid_blocked_result(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._write_fake_runtime_verifier(root)
            result = EvalResult("example-skill", "EXAMPLE-001")
            outcome = validate_skill_local_runtime_evidence(
                self._skill_runtime_artifact(),
                "example-skill",
                "EXAMPLE-001",
                {
                    "runtime_unit_key": "artifact:example:all",
                    "partial_rerun": False,
                },
                result,
                source_root=Path(os.path.relpath(root, Path.cwd())),
            )
        self.assertEqual(outcome["status"], "verified")
        self.assertTrue(outcome["valid"])
        self.assertEqual(result.status, "pass")

    def test_skill_runtime_gate_rejects_missing_and_malformed_evidence(self) -> None:
        policy = {"runtime_unit_key": "artifact:example:all", "partial_rerun": False}
        missing = EvalResult("example-skill", "EXAMPLE-002")
        missing_outcome = validate_skill_local_runtime_evidence(
            "# no machine evidence", "example-skill", "EXAMPLE-002", policy, missing
        )
        self.assertEqual(missing_outcome["status"], "missing_evidence")
        self.assertEqual(missing.status, "fail")

        malformed_text = self._skill_runtime_artifact().replace(
            "```json", "```text", 1
        )
        malformed = EvalResult("example-skill", "EXAMPLE-003")
        malformed_outcome = validate_skill_local_runtime_evidence(
            malformed_text,
            "example-skill",
            "EXAMPLE-003",
            policy,
            malformed,
        )
        self.assertEqual(malformed_outcome["status"], "invalid_evidence")
        self.assertEqual(malformed.status, "fail")

    def test_skill_runtime_gate_distinguishes_invalid_evidence_from_execution_error(
        self,
    ) -> None:
        policy = {"runtime_unit_key": "artifact:example:all", "partial_rerun": False}
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._write_fake_runtime_verifier(root, valid=False)
            invalid_result = EvalResult("example-skill", "EXAMPLE-004")
            invalid_outcome = validate_skill_local_runtime_evidence(
                self._skill_runtime_artifact(),
                "example-skill",
                "EXAMPLE-004",
                policy,
                invalid_result,
                source_root=root,
            )
            self.assertEqual(invalid_outcome["status"], "invalid_evidence")
            self.assertEqual(invalid_result.status, "fail")

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._write_fake_runtime_verifier(root, exit_code=7)
            execution_result = EvalResult("example-skill", "EXAMPLE-005")
            execution_outcome = validate_skill_local_runtime_evidence(
                self._skill_runtime_artifact(),
                "example-skill",
                "EXAMPLE-005",
                policy,
                execution_result,
                source_root=root,
            )
        self.assertEqual(execution_outcome["status"], "execution error")
        self.assertIsNone(execution_outcome["valid"])
        self.assertEqual(execution_result.status, "pass")

    def test_skill_runtime_verifier_source_change_is_execution_error(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._write_fake_runtime_verifier(root)
            verifier = root / "skills/example-skill/scripts/runtime_contract.py"
            original_run = subprocess.run

            def run_then_change_source(*args, **kwargs):
                completed = original_run(*args, **kwargs)
                verifier.write_text(
                    verifier.read_text(encoding="utf-8") + "# changed\n",
                    encoding="utf-8",
                )
                return completed

            result = EvalResult("example-skill", "EXAMPLE-006")
            with patch(
                "scripts.skills.evals.deterministic.runtime_validator.subprocess.run",
                side_effect=run_then_change_source,
            ):
                outcome = validate_skill_local_runtime_evidence(
                    self._skill_runtime_artifact(),
                    "example-skill",
                    "EXAMPLE-006",
                    {
                        "runtime_unit_key": "artifact:example:all",
                        "partial_rerun": False,
                    },
                    result,
                    source_root=root,
                )

        self.assertEqual(outcome["status"], "execution error")
        self.assertIsNone(outcome["valid"])
        self.assertEqual(
            outcome["reason"], "skill_local_runtime_verifier_changed_during_execution"
        )

    def test_skill_runtime_verifier_inconsistent_response_is_execution_error(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._write_fake_runtime_verifier(root)
            verifier = root / "skills/example-skill/scripts/runtime_contract.py"
            verifier.write_text(
                "import json, sys\n"
                "json.load(sys.stdin)\n"
                "sys.stdout.write(json.dumps({'valid': True, 'issues': "
                "[{'issue_type': 'impossible'}]}))\n",
                encoding="utf-8",
            )
            result = EvalResult("example-skill", "EXAMPLE-007")
            outcome = validate_skill_local_runtime_evidence(
                self._skill_runtime_artifact(),
                "example-skill",
                "EXAMPLE-007",
                {
                    "runtime_unit_key": "artifact:example:all",
                    "partial_rerun": False,
                },
                result,
                source_root=root,
            )

        self.assertEqual(outcome["status"], "execution error")
        self.assertIsNone(outcome["valid"])
        self.assertEqual(
            outcome["reason"], "skill_local_runtime_verifier_inconsistent_response"
        )

    def test_declared_runtime_and_entity_contract_passes(self) -> None:
        expected = {
            "runtime_contract": {
                "expected_runtime_units": [
                    {
                        "skill": "test-condition-design",
                        "runtime_unit_key": "model:ep-001",
                    }
                ],
                "expected_generators": {
                    "test-condition-design::model:ep-001": "equivalence_partitions"
                },
                "expected_targets": {"test-condition-design::model:ep-001": []},
            },
            "machine_entities": {
                "expected_entities": [
                    {
                        "skill": "test-condition-design",
                        "entity_type": "model",
                        "entity_ref": "ep-001",
                    }
                ]
            },
        }
        result = EvalResult("test-condition-design", "TCN-OUT-001")
        validate_runtime_evidence(_artifact(), expected, result)
        self.assertEqual(result.status, "pass")

    def test_missing_result_is_a_pair_failure(self) -> None:
        expected = {
            "expected_runtime_units": [
                {"skill": "test-condition-design", "runtime_unit_key": "model:ep-001"}
            ]
        }
        text = _artifact().replace(
            "### Machine Runtime Result: test-condition-design::model:ep-001\n\n", ""
        )
        result = EvalResult("test-condition-design", "TCN-OUT-002")
        validate_runtime_evidence(text, expected, result)
        self.assertEqual(result.status, "fail")

    def test_declared_runtime_unit_rejects_missing_runtime_evidence(self) -> None:
        expected = {
            "runtime_contract": {
                "expected_runtime_units": [
                    "coverage-analysis::artifact:traceability:all"
                ],
                "expected_generators": {
                    "coverage-analysis::artifact:traceability:all": "traceability"
                },
            }
        }
        result = EvalResult("coverage-analysis", "COV-OUT-002")
        validate_runtime_evidence("# output without runtime evidence", expected, result)
        failures = {
            assertion.id
            for assertion in result.assertions
            if assertion.status == "fail"
        }
        self.assertEqual(result.status, "fail")
        self.assertIn("RUNTIME-UNITS-EXACT", failures)

    def test_expected_runtime_status_is_checked(self) -> None:
        expected = {
            "runtime_contract": {
                "expected_runtime_units": ["test-condition-design::model:ep-001"],
                "expected_status": {
                    "test-condition-design::model:ep-001": {"runtime_status": "ready"}
                },
            }
        }
        result = EvalResult("test-condition-design", "TCN-OUT-001")
        validate_runtime_evidence(_artifact(), expected, result)
        failures = {a.id for a in result.assertions if a.status == "fail"}
        self.assertEqual(result.status, "fail")
        self.assertIn(
            "RUNTIME-PAIR-test-condition-design-model-ep-001-STATUS", failures
        )

    def test_fingerprint_tampering_is_detected_without_expected_hash_fixture(
        self,
    ) -> None:
        expected = {
            "runtime_contract": {
                "expected_runtime_units": [
                    {
                        "skill": "test-condition-design",
                        "runtime_unit_key": "model:ep-001",
                    }
                ],
            },
            "machine_entities": {
                "expected_entities": [
                    {
                        "skill": "test-condition-design",
                        "entity_type": "model",
                        "entity_ref": "ep-001",
                    }
                ]
            },
        }
        text = re.sub(
            r'("input_fingerprint":")[^"]+',
            r"\1sha256:" + "0" * 64,
            _artifact(),
            count=1,
        )
        result = EvalResult("test-condition-design", "TCN-OUT-003")
        validate_runtime_evidence(text, expected, result)
        self.assertEqual(result.status, "fail")

    def test_runtime_fingerprint_uses_trusted_candidate_source_root(self) -> None:
        expected = {
            "runtime_contract": {
                "expected_runtime_units": [
                    {
                        "skill": "test-condition-design",
                        "runtime_unit_key": "model:ep-001",
                    }
                ],
            },
            "machine_entities": {
                "expected_entities": [
                    {
                        "skill": "test-condition-design",
                        "entity_type": "model",
                        "entity_ref": "ep-001",
                    }
                ]
            },
        }
        with tempfile.TemporaryDirectory() as temporary:
            source_root = Path(temporary)
            script_root = source_root / "skills/test-condition-design/scripts"
            script_root.mkdir(parents=True)
            original_scripts = REPO_ROOT / "skills/test-condition-design/scripts"
            for name in ("runtime_contract.py", "equivalence_partitions.py"):
                shutil.copyfile(original_scripts / name, script_root / name)

            text = _artifact(source_root)
            result = EvalResult("test-condition-design", "TCN-OUT-CANDIDATE")
            validate_runtime_evidence(text, expected, result, source_root=source_root)
            self.assertEqual(result.status, "pass")

            runtime_path = script_root / "runtime_contract.py"
            runtime_path.write_text(
                runtime_path.read_text(encoding="utf-8") + "\n# candidate revision\n",
                encoding="utf-8",
            )
            candidate_result = EvalResult(
                "test-condition-design", "TCN-OUT-CANDIDATE-CHANGED"
            )
            validate_runtime_evidence(
                text, expected, candidate_result, source_root=source_root
            )
            self.assertEqual(candidate_result.status, "fail")

    def test_duplicate_machine_entity_block_is_detected(self) -> None:
        expected = {
            "runtime_contract": {
                "expected_runtime_units": [
                    {
                        "skill": "test-condition-design",
                        "runtime_unit_key": "model:ep-001",
                    }
                ],
            },
            "machine_entities": {
                "expected_entities": [
                    {
                        "skill": "test-condition-design",
                        "entity_type": "model",
                        "entity_ref": "ep-001",
                    }
                ]
            },
        }
        text = _artifact()
        entity_block = text.split("### Machine Entities: test-condition-design", 1)[1]
        text = text + "### Machine Entities: test-condition-design" + entity_block
        result = EvalResult("test-condition-design", "TCN-OUT-004")
        validate_runtime_evidence(text, expected, result)
        self.assertEqual(result.status, "fail")


if __name__ == "__main__":
    unittest.main()
