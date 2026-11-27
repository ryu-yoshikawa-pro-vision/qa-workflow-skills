"""Owner completion gates for context signal batches and synthesis runs."""

from __future__ import annotations

import copy
import hashlib
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tests" / "skills" / "runtime"))
sys.path.insert(0, str(ROOT / "skills" / "qa-workflow" / "scripts"))
sys.path.insert(0, str(ROOT / "scripts"))

import context_artifacts as contracts  # noqa: E402
import owner_verifiers  # noqa: E402
import test_context_artifacts as fixtures  # noqa: E402


def canonical_text(value: object) -> str:
    return contracts.canonical_bytes(value).decode("utf-8")


def provider_readback(kind: str, artifact: dict, revision: str) -> dict:
    content = canonical_text(artifact)
    return {
        "kind": kind,
        "root_binding": fixtures.ROOT_BINDING,
        "artifact_ref": artifact["artifact_ref"],
        "revision": revision,
        "sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
        "content": content,
    }


def ranged_batch(section: str) -> dict:
    batch = fixtures.build_batch()
    source_range = {"kind": "sections", "items": [section]}
    batch["source"]["requested_range"] = source_range
    batch["source"]["actual_inspected_range"] = source_range
    batch["batch_identity"] = contracts.batch_identity(
        batch["source"]["artifact_ref"],
        batch["source"]["source_content_hash"],
        source_range,
        batch["source"]["observation_condition"],
    )
    batch["artifact_ref"] = contracts.artifact_ref(
        "context-signal-batch",
        batch["batch_identity"],
    )
    signal = batch["signals"][0]
    signal["observation_locator"]["section_id"] = section
    signal["signal_identity"] = contracts.signal_identity(
        batch["source"]["artifact_ref"],
        signal["observation_locator"],
        batch["source"]["source_content_hash"],
    )
    signal["signal_content_hash"] = contracts.signal_content_hash(signal)
    contracts.validate_artifact(batch, "context-signal-batch")
    return batch


class ContextOwnerVerifierTests(unittest.TestCase):
    def test_signal_owner_reuses_a_broader_batch_for_the_requested_range(self) -> None:
        batch = ranged_batch("SEC-1")
        broad = {"kind": "sections", "items": ["SEC-1", "SEC-2"]}
        batch["source"]["requested_range"] = broad
        batch["source"]["actual_inspected_range"] = broad
        batch["batch_identity"] = contracts.batch_identity(
            fixtures.SOURCE_REF,
            fixtures.SOURCE_HASH,
            broad,
            batch["source"]["observation_condition"],
        )
        batch["artifact_ref"] = contracts.artifact_ref(
            "context-signal-batch", batch["batch_identity"]
        )
        contracts.validate_artifact(batch, "context-signal-batch")
        selected = provider_readback("context-signal-batch", batch, "file-v1-1-2")
        requested = {"kind": "sections", "items": ["SEC-1"]}
        evidence = {
            "stored_content": selected["content"],
            "readback": selected,
            "expected_revision": selected["revision"],
            "root_binding": fixtures.ROOT_BINDING,
            "requested_source_ref": fixtures.SOURCE_REF,
            "requested_source_content_hash": fixtures.SOURCE_HASH,
            "requested_range": requested,
            "observation_condition": {"locale": "ja"},
            "current_source": {
                "artifact_ref": fixtures.SOURCE_REF,
                "source_revision": "r3",
                "content_hash": fixtures.SOURCE_HASH,
            },
            "batch_readbacks": [selected],
        }
        scope = {
            "skill": "context-signal-audit",
            "target": batch["artifact_ref"],
            "execution_range": json.dumps(
                requested, sort_keys=True, separators=(",", ":")
            ),
            "normalized_input": {
                "owner_verification": evidence,
                "context_request": {
                    "workflow_ref": "workflow-test-2",
                    "source_artifact_ref": fixtures.SOURCE_REF,
                    "source_revision": "r3",
                    "source_content_hash": fixtures.SOURCE_HASH,
                    "requested_range": requested,
                    "assigned_range": requested,
                    "observation_condition": {"locale": "ja"},
                },
            },
        }

        verified = owner_verifiers.VERIFIERS["context-signal-audit"](scope)

        self.assertEqual(verified["artifact_ref"], batch["artifact_ref"])
        self.assertNotEqual(batch["source"]["actual_inspected_range"], requested)

    def test_signal_owner_accepts_two_readbacks_covering_one_requested_range(
        self,
    ) -> None:
        first = ranged_batch("SEC-1")
        second = ranged_batch("SEC-2")
        selected = provider_readback("context-signal-batch", first, "git:" + "1" * 40)
        other = provider_readback("context-signal-batch", second, "git:" + "2" * 40)
        evidence = {
            "stored_content": selected["content"],
            "readback": selected,
            "expected_revision": selected["revision"],
            "root_binding": fixtures.ROOT_BINDING,
            "requested_source_ref": fixtures.SOURCE_REF,
            "requested_source_content_hash": fixtures.SOURCE_HASH,
            "requested_range": {"kind": "sections", "items": ["SEC-1", "SEC-2"]},
            "observation_condition": {"locale": "ja"},
            "current_source": {
                "artifact_ref": fixtures.SOURCE_REF,
                "source_revision": "r3",
                "content_hash": fixtures.SOURCE_HASH,
            },
            "batch_readbacks": [selected, other],
        }
        scope = {
            "skill": "context-signal-audit",
            "target": first["artifact_ref"],
            "execution_range": json.dumps(
                {"kind": "sections", "items": ["SEC-1"]},
                sort_keys=True,
                separators=(",", ":"),
            ),
            "normalized_input": {
                "owner_verification": evidence,
                "context_request": {
                    "workflow_ref": "workflow-test-1",
                    "source_artifact_ref": fixtures.SOURCE_REF,
                    "source_revision": "r3",
                    "source_content_hash": fixtures.SOURCE_HASH,
                    "requested_range": {
                        "kind": "sections",
                        "items": ["SEC-1", "SEC-2"],
                    },
                    "assigned_range": {
                        "kind": "sections",
                        "items": ["SEC-1"],
                    },
                    "observation_condition": {"locale": "ja"},
                },
            },
        }

        verified = owner_verifiers.VERIFIERS["context-signal-audit"](scope)

        self.assertEqual(verified["artifact_ref"], first["artifact_ref"])
        self.assertEqual(verified["content_hash"], selected["sha256"])

    def test_signal_owner_rejects_missing_range_and_unread_correction_target(
        self,
    ) -> None:
        first = ranged_batch("SEC-1")
        selected = provider_readback("context-signal-batch", first, "git:" + "1" * 40)
        evidence = {
            "stored_content": selected["content"],
            "readback": selected,
            "expected_revision": selected["revision"],
            "root_binding": fixtures.ROOT_BINDING,
            "requested_source_ref": fixtures.SOURCE_REF,
            "requested_source_content_hash": fixtures.SOURCE_HASH,
            "requested_range": {"kind": "sections", "items": ["SEC-1", "SEC-2"]},
            "observation_condition": {"locale": "ja"},
            "current_source": {
                "artifact_ref": fixtures.SOURCE_REF,
                "source_revision": "r3",
                "content_hash": fixtures.SOURCE_HASH,
            },
            "batch_readbacks": [selected],
        }
        scope = {
            "skill": "context-signal-audit",
            "target": first["artifact_ref"],
            "execution_range": json.dumps(
                first["source"]["actual_inspected_range"],
                sort_keys=True,
                separators=(",", ":"),
            ),
            "normalized_input": {
                "owner_verification": evidence,
                "context_request": {
                    "workflow_ref": "workflow-test-1",
                    "source_artifact_ref": fixtures.SOURCE_REF,
                    "source_revision": "r3",
                    "source_content_hash": fixtures.SOURCE_HASH,
                    "requested_range": {
                        "kind": "sections",
                        "items": ["SEC-1", "SEC-2"],
                    },
                    "assigned_range": first["source"]["actual_inspected_range"],
                    "observation_condition": {"locale": "ja"},
                },
            },
        }
        with self.assertRaisesRegex(
            owner_verifiers.VerificationFailed, "batch_does_not_cover"
        ):
            owner_verifiers.VERIFIERS["context-signal-audit"](scope)

        corrected = copy.deepcopy(first)
        corrected["correction"] = {
            "original_batch_identity": first["batch_identity"],
            "corrected_batch_targets": [
                {
                    "batch_identity": first["batch_identity"],
                    "artifact_ref": first["artifact_ref"],
                    "revision": selected["revision"],
                    "content_hash": selected["sha256"],
                    "source_artifact_ref": fixtures.SOURCE_REF,
                    "source_content_hash": fixtures.SOURCE_HASH,
                    "actual_inspected_range": first["source"]["actual_inspected_range"],
                    "observation_condition": {"locale": "ja"},
                }
            ],
            "reason": "Confirmed extraction omission.",
            "source_evidence_refs": [fixtures.SOURCE_REF],
        }
        corrected["batch_identity"] = contracts.correction_batch_identity(
            first["batch_identity"],
            corrected["correction"]["corrected_batch_targets"],
            corrected["signals"],
        )
        corrected["artifact_ref"] = contracts.artifact_ref(
            "context-signal-batch",
            corrected["batch_identity"],
        )
        contracts.validate_artifact(corrected, "context-signal-batch")
        corrected_readback = provider_readback(
            "context-signal-batch", corrected, "git:" + "3" * 40
        )
        evidence.update(
            stored_content=corrected_readback["content"],
            readback=corrected_readback,
            expected_revision=corrected_readback["revision"],
            requested_range=first["source"]["actual_inspected_range"],
            batch_readbacks=[corrected_readback],
        )
        scope.update(
            target=corrected["artifact_ref"],
            normalized_input={
                "owner_verification": evidence,
                "context_request": {
                    "workflow_ref": "workflow-test-1",
                    "source_artifact_ref": fixtures.SOURCE_REF,
                    "source_revision": "r3",
                    "source_content_hash": fixtures.SOURCE_HASH,
                    "requested_range": first["source"]["actual_inspected_range"],
                    "assigned_range": first["source"]["actual_inspected_range"],
                    "observation_condition": {"locale": "ja"},
                },
            },
        )
        with self.assertRaisesRegex(
            owner_verifiers.VerificationFailed, "correction_target_readback"
        ):
            owner_verifiers.VERIFIERS["context-signal-audit"](scope)

    def test_synthesis_owner_requires_exact_run_and_provider_readbacks(self) -> None:
        run = fixtures.build_run()
        run_content = canonical_text(run)
        run_readback = provider_readback("context-synthesis-run", run, "sqlite:r1")
        source_readback = {
            "kind": "spec",
            "root_binding": fixtures.ROOT_BINDING,
            "artifact_ref": fixtures.SOURCE_REF,
            "revision": "r3",
            "sha256": fixtures.SOURCE_HASH,
            "content": fixtures.SOURCE_CONTENT,
        }
        evidence = {
            "stored_content": run_content,
            "readback": run_readback,
            "expected_revision": run_readback["revision"],
            "root_binding": fixtures.ROOT_BINDING,
            "provider_readbacks": [source_readback],
        }
        scope = {
            "skill": "context-rule-synthesis",
            "target": run["artifact_ref"],
            "execution_range": "run:" + run["run_identity"],
            "normalized_input": {
                "owner_verification": evidence,
                "context_request": {
                    "workflow_ref": run["workflow_ref"],
                    "operation_input": run["operation_input"],
                    "requested_scope": run["requested_scope"],
                    "target_batch_refs": run["triage_plan"]["target_batch_refs"],
                },
            },
        }

        verified = owner_verifiers.VERIFIERS["context-rule-synthesis"](scope)

        self.assertEqual(verified["artifact_ref"], run["artifact_ref"])
        self.assertEqual(verified["content_hash"], run_readback["sha256"])
        run_readback["sha256"] = "0" * 64
        with self.assertRaisesRegex(
            owner_verifiers.VerificationFailed, "stored_artifact_readback"
        ):
            owner_verifiers.VERIFIERS["context-rule-synthesis"](scope)


if __name__ == "__main__":
    unittest.main()
