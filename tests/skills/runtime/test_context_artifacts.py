from __future__ import annotations

import copy
import hashlib
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
COMMON_SCRIPTS = PROJECT_ROOT / "scripts"
QA_WORKFLOW_SCRIPTS = PROJECT_ROOT / "skills" / "qa-workflow" / "scripts"
sys.path.insert(0, str(COMMON_SCRIPTS))
sys.path.insert(0, str(QA_WORKFLOW_SCRIPTS))

from context_artifacts import (  # noqa: E402
    ContractError,
    artifact_ref,
    batch_covers_request,
    batch_identity,
    batch_union_covers_request,
    candidate_identity,
    canonical_bytes,
    completion_check,
    correction_batch_identity,
    impact,
    normalize_range,
    parse_canonical_json,
    project_artifact,
    range_contains,
    range_union,
    run_identity,
    select_batch_signals,
    semantic_handoff_key,
    signal_content_hash,
    signal_identity,
    snapshot_hash,
    transition_allowed,
    validate_artifact,
    validate_candidate_relations,
    workflow_operation_id,
)

ROOT_BINDING = "fixture-root:context-artifacts"
SOURCE_REF = "project/specifications/payment.md"
SOURCE_CONTENT = "Specification revision 3: eligible purchases can be refunded."
SOURCE_HASH = hashlib.sha256(SOURCE_CONTENT.encode("utf-8")).hexdigest()


def operation_input() -> dict:
    return {
        "operation_type": "synthesize_context",
        "input_sources": [
            {
                "artifact_ref": SOURCE_REF,
                "content_hash": SOURCE_HASH,
                "effective_authority_fingerprint": None,
                "source_revision": "r3",
            }
        ],
        "investigation_conditions": {"environment": "staging"},
    }


def requested_scope() -> dict:
    return {
        "scope_refs": ["feature:refund"],
        "analysis_aspect": "refund and cancellation behavior",
        "environment_and_versions": [
            {"environment": "staging", "version_constraint": "v1"}
        ],
    }


def build_batch() -> dict:
    actual_range = {"kind": "sections", "items": ["SEC-1"]}
    identity = batch_identity(SOURCE_REF, SOURCE_HASH, actual_range, {"locale": "ja"})
    signal = {
        "observation_locator": {"section_id": "SEC-1", "item": "refund-window"},
        "evidence_type": "spec",
        "fact_summary": "Refund requests are accepted for eligible purchases.",
        "independence_group": "spec:payment",
        "cross_cutting_attributes": {"operation": "refund", "channel": "web"},
        "environment_and_versions": [
            {"environment": "staging", "version_constraint": "v1"}
        ],
    }
    signal["signal_identity"] = signal_identity(
        SOURCE_REF, signal["observation_locator"], SOURCE_HASH
    )
    signal["signal_content_hash"] = signal_content_hash(signal)
    return {
        "schema_version": "1.0",
        "artifact_ref": artifact_ref("context-signal-batch", identity),
        "batch_identity": identity,
        "workflow_operation_id": workflow_operation_id(
            "workflow:ctx-001", operation_input(), requested_scope()
        ),
        "source": {
            "artifact_ref": SOURCE_REF,
            "source_revision": "r3",
            "source_content_hash": SOURCE_HASH,
            "requested_range": actual_range,
            "actual_inspected_range": actual_range,
            "observation_condition": {"locale": "ja"},
        },
        "scan_completeness": "complete",
        "candidate_check": {
            "status": "checked_no_conflict",
            "triggered_candidate_identities": [],
        },
        "signals": [signal],
    }


def build_candidate(
    rule_statement: str = "Eligible purchases can be refunded.",
    *,
    role: str = "customer",
) -> dict:
    identity_key = {
        "domain": "payments",
        "operation_axis": "refund",
        "rule_kind": "eligibility",
        "target_scope_kind": "feature",
        "governing_conditions": {"role": role},
        "assertion_polarity": "positive",
        "normalized_assertion": "eligible purchases are refundable",
    }
    identity = candidate_identity(identity_key)
    return {
        "schema_version": "1.0",
        "artifact_ref": artifact_ref("context-rule-candidate", identity),
        "candidate_identity": identity,
        "identity_key": identity_key,
        "rule_statement": rule_statement,
        "applicability": {
            "scope_summary": "Customer refunds for eligible purchases.",
            "cross_cutting_attributes": {"role": role},
            "invalidation_conditions": [],
        },
        "related_candidate_refs": [],
        "evidence_links": [],
        "unobserved_ranges": ["refund processing after settlement"],
        "currentness_dependencies": [],
        "evaluation_status": {
            "scan_completeness": "complete",
            "revalidation_required": False,
            "revalidation_reasons": [],
            "last_synthesis_run_ref": None,
        },
        "resolution_state": "uninvestigated",
        "resolution_links": [],
        "implementation_conformance_refs": [],
        "question_refs": [],
        "handoff_records": [],
        "rejection_or_deferral_detail": None,
        "investigation_history": [],
    }


def build_run() -> dict:
    operation = operation_input()
    op_id = workflow_operation_id("workflow:ctx-001", operation, requested_scope())
    identity = run_identity(op_id)
    snapshot = {
        "search_roots_and_scopes": ["designated context root"],
        "search_criteria": "payment refund rules, candidates and authority",
        "referenced_sources": [
            {
                "source_kind": "spec",
                "artifact_ref": SOURCE_REF,
                "source_revision": "r3",
                "content_hash": SOURCE_HASH,
                "effective_authority_fingerprint": None,
            }
        ],
        "unverifiable_sources": [],
        "excluded_scope_notes": "No excluded scope.",
    }
    snapshot["snapshot_hash"] = snapshot_hash(snapshot)
    return {
        "schema_version": "1.0",
        "artifact_ref": artifact_ref("context-synthesis-run", identity),
        "run_identity": identity,
        "workflow_ref": "workflow:ctx-001",
        "workflow_operation_id": op_id,
        "operation_input": operation,
        "requested_scope": requested_scope(),
        "inspected_scope": "feature:refund",
        "scan_completeness": "complete",
        "snapshot": snapshot,
        "triage_plan": {"target_batch_refs": [], "planned_candidate_ops": []},
        "result_summary": {
            "status": "completed_zero_changes",
            "zero_change_reason": "no_related_candidates",
            "unresolved_and_handoff_refs": [],
        },
    }


class ContextArtifactContractTests(unittest.TestCase):
    def test_canonical_bytes_and_root_relative_refs(self) -> None:
        batch = build_batch()
        raw = canonical_bytes(batch)
        self.assertEqual(parse_canonical_json(raw), batch)
        self.assertEqual(validate_artifact(batch, "context-signal-batch"), batch)
        self.assertEqual(
            batch["artifact_ref"],
            f"context-signal-batch/{batch['batch_identity']}.json",
        )
        self.assertNotIn("project_ref", batch)
        with self.assertRaises(ContractError):
            parse_canonical_json(b'{"a":1,"a":2}')
        with self.assertRaises(ContractError):
            parse_canonical_json(b'{"value":NaN}')

    def test_run_identity_binds_requested_scope_and_paired_input_sources(self) -> None:
        run = build_run()
        self.assertEqual(validate_artifact(run, "context-synthesis-run"), run)
        changed_scope = copy.deepcopy(run)
        changed_scope["requested_scope"]["analysis_aspect"] = "different question"
        with self.assertRaisesRegex(ContractError, "run_identity_mismatch"):
            validate_artifact(changed_scope, "context-synthesis-run")
        changed_source = operation_input()
        changed_source["input_sources"][0].pop("content_hash")
        with self.assertRaisesRegex(
            ContractError, "operation_input_source_schema_invalid"
        ):
            workflow_operation_id("workflow:ctx-001", changed_source, requested_scope())

    def test_identities_include_semantic_inputs_and_exclude_mutable_provenance(
        self,
    ) -> None:
        candidate = build_candidate()
        key = candidate["identity_key"]
        identity = candidate_identity(key)
        changed_tag_only = copy.deepcopy(candidate)
        changed_tag_only["search_tags"] = ["cancellation", "refund"]
        self.assertEqual(candidate_identity(changed_tag_only["identity_key"]), identity)
        self.assertEqual(
            validate_artifact(changed_tag_only, "context-rule-candidate")[
                "candidate_identity"
            ],
            identity,
        )
        changed_condition = copy.deepcopy(key)
        changed_condition["governing_conditions"]["role"] = "administrator"
        self.assertNotEqual(candidate_identity(changed_condition), identity)
        self.assertEqual(run_identity("a" * 64), run_identity("a" * 64))
        self.assertNotEqual(
            workflow_operation_id(
                "workflow:ctx-001", operation_input(), requested_scope()
            ),
            workflow_operation_id(
                "workflow:ctx-001",
                operation_input(),
                {**requested_scope(), "analysis_aspect": "different question"},
            ),
        )
        changed_authority = operation_input()
        changed_authority["input_sources"][0]["effective_authority_fingerprint"] = (
            "b" * 64
        )
        self.assertNotEqual(
            workflow_operation_id(
                "workflow:ctx-001", operation_input(), requested_scope()
            ),
            workflow_operation_id(
                "workflow:ctx-001", changed_authority, requested_scope()
            ),
        )
        changed_revision_only = operation_input()
        changed_revision_only["input_sources"][0]["source_revision"] = "r4"
        self.assertEqual(
            workflow_operation_id(
                "workflow:ctx-001", operation_input(), requested_scope()
            ),
            workflow_operation_id(
                "workflow:ctx-001", changed_revision_only, requested_scope()
            ),
        )

    def test_batch_identity_binds_source_range_and_observation_condition(self) -> None:
        base = batch_identity(
            SOURCE_REF,
            SOURCE_HASH,
            {"kind": "sections", "items": ["SEC-1"]},
            {"locale": "ja"},
        )
        self.assertEqual(
            batch_identity(
                SOURCE_REF,
                SOURCE_HASH,
                {"kind": "sections", "items": ["SEC-1"]},
                {"locale": "ja"},
            ),
            base,
        )
        self.assertNotEqual(
            batch_identity(
                SOURCE_REF,
                SOURCE_HASH,
                {"kind": "sections", "items": ["SEC-2"]},
                {"locale": "ja"},
            ),
            base,
        )
        self.assertNotEqual(
            batch_identity(
                SOURCE_REF,
                SOURCE_HASH,
                {"kind": "sections", "items": ["SEC-1"]},
                {"locale": "en"},
            ),
            base,
        )
        self.assertNotEqual(
            batch_identity(
                "project/specifications/refund.md",
                SOURCE_HASH,
                {"kind": "sections", "items": ["SEC-1"]},
                {"locale": "ja"},
            ),
            base,
        )

    def test_semantic_handoff_key_binds_owner_scope_and_intent_only(self) -> None:
        base = semantic_handoff_key(
            "question-analysis", "feature:refund", {"question": "refund window"}
        )
        self.assertEqual(
            semantic_handoff_key(
                "question-analysis", "feature:refund", {"question": "refund window"}
            ),
            base,
        )
        self.assertNotEqual(
            semantic_handoff_key(
                "spec-analysis", "feature:refund", {"question": "refund window"}
            ),
            base,
        )
        self.assertNotEqual(
            semantic_handoff_key(
                "question-analysis",
                "feature:cancellation",
                {"question": "refund window"},
            ),
            base,
        )
        self.assertNotEqual(
            semantic_handoff_key(
                "question-analysis",
                "feature:refund",
                {"question": "cancellation policy"},
            ),
            base,
        )

    def test_structured_range_normalization_union_and_coverage(self) -> None:
        self.assertEqual(
            normalize_range({"kind": "sections", "items": ["SEC-2", "SEC-1", "SEC-2"]}),
            {"kind": "sections", "items": ["SEC-1", "SEC-2"]},
        )
        self.assertTrue(
            range_contains(
                {"kind": "sections", "items": ["SEC-1", "SEC-2"]},
                {"kind": "sections", "items": ["SEC-1"]},
            )
        )
        self.assertFalse(
            range_contains(
                {"kind": "sections", "items": ["SEC-1"]},
                {"kind": "paths", "items": ["src/refund.py"]},
            )
        )

    def test_partial_batch_union_projection_and_selective_signal_read(self) -> None:
        request = {"kind": "sections", "items": ["SEC-1", "SEC-2"]}
        batches = []
        for section in ("SEC-1", "SEC-2"):
            batch = build_batch()
            signal = batch["signals"][0]
            signal["observation_locator"] = {
                "section_id": section,
                "item": "refund-window",
            }
            signal["signal_identity"] = signal_identity(
                SOURCE_REF, signal["observation_locator"], SOURCE_HASH
            )
            signal["signal_content_hash"] = signal_content_hash(signal)
            batch["source"]["actual_inspected_range"] = {
                "kind": "sections",
                "items": [section],
            }
            batch["source"]["requested_range"] = request
            batch["scan_completeness"] = "partial"
            identity = batch_identity(
                SOURCE_REF,
                SOURCE_HASH,
                batch["source"]["actual_inspected_range"],
                batch["source"]["observation_condition"],
            )
            batch["batch_identity"] = identity
            batch["artifact_ref"] = artifact_ref("context-signal-batch", identity)
            batches.append(validate_artifact(batch, "context-signal-batch"))
        self.assertTrue(
            batch_union_covers_request(
                batches,
                source_ref=SOURCE_REF,
                source_content_hash=SOURCE_HASH,
                requested_range=request,
                observation_condition={"locale": "ja"},
            )
        )
        self.assertFalse(
            batch_union_covers_request(
                batches[:1],
                source_ref=SOURCE_REF,
                source_content_hash=SOURCE_HASH,
                requested_range=request,
                observation_condition={"locale": "ja"},
            )
        )
        projection = project_artifact(
            batches[0], kind="context-signal-batch", item_limit=1
        )
        self.assertEqual(projection["signal_count"], 1)
        self.assertEqual(
            select_batch_signals(
                batches[0], [batches[0]["signals"][0]["signal_identity"]]
            ),
            batches[0]["signals"],
        )
        wrong_condition = copy.deepcopy(batches[1])
        wrong_condition["source"]["observation_condition"] = {"locale": "en"}
        self.assertFalse(
            batch_union_covers_request(
                [batches[0], wrong_condition],
                source_ref=SOURCE_REF,
                source_content_hash=SOURCE_HASH,
                requested_range=request,
                observation_condition={"locale": "ja"},
            )
        )

    def test_correction_batch_identity_is_immutable_and_conflicts_do_not_cover(
        self,
    ) -> None:
        original = build_batch()
        original_content_hash = hashlib.sha256(canonical_bytes(original)).hexdigest()
        target = {
            "batch_identity": original["batch_identity"],
            "artifact_ref": original["artifact_ref"],
            "revision": "r1",
            "content_hash": original_content_hash,
            "source_artifact_ref": SOURCE_REF,
            "source_content_hash": SOURCE_HASH,
            "actual_inspected_range": original["source"]["actual_inspected_range"],
            "observation_condition": original["source"]["observation_condition"],
        }

        def corrected(summary: str) -> dict:
            value = copy.deepcopy(original)
            signal = value["signals"][0]
            signal["fact_summary"] = summary
            signal["signal_content_hash"] = signal_content_hash(signal)
            value["correction"] = {
                "original_batch_identity": original["batch_identity"],
                "corrected_batch_targets": [target],
                "reason": "The source sentence was rechecked and the omitted condition was restored.",
                "source_evidence_refs": [SOURCE_REF],
            }
            identity = correction_batch_identity(
                original["batch_identity"],
                value["correction"]["corrected_batch_targets"],
                value["signals"],
            )
            value["batch_identity"] = identity
            value["artifact_ref"] = artifact_ref("context-signal-batch", identity)
            return value

        first = validate_artifact(
            corrected("Eligible purchases can be refunded within 30 days."),
            "context-signal-batch",
        )
        second = validate_artifact(
            corrected("Eligible purchases can be refunded within 14 days."),
            "context-signal-batch",
        )
        self.assertTrue(
            batch_union_covers_request(
                [original, first],
                source_ref=SOURCE_REF,
                source_content_hash=SOURCE_HASH,
                requested_range=original["source"]["actual_inspected_range"],
                observation_condition={"locale": "ja"},
            )
        )
        self.assertFalse(
            batch_union_covers_request(
                [original, first, second],
                source_ref=SOURCE_REF,
                source_content_hash=SOURCE_HASH,
                requested_range=original["source"]["actual_inspected_range"],
                observation_condition={"locale": "ja"},
            )
        )
        self.assertIsNone(
            range_union(
                [
                    {"kind": "sections", "items": ["SEC-1"]},
                    {"kind": "paths", "items": ["src/refund.py"]},
                ]
            )
        )
        batch = build_batch()
        self.assertTrue(
            batch_covers_request(
                batch,
                source_ref=SOURCE_REF,
                source_content_hash=SOURCE_HASH,
                requested_range={"kind": "sections", "items": ["SEC-1"]},
                observation_condition={"locale": "ja"},
            )
        )
        self.assertFalse(
            batch_covers_request(
                batch,
                source_ref=SOURCE_REF,
                source_content_hash="b" * 64,
                requested_range={"kind": "sections", "items": ["SEC-1"]},
                observation_condition={"locale": "ja"},
            )
        )

    def test_candidate_state_and_successor_cycle_rules(self) -> None:
        a, b = (
            build_candidate(),
            build_candidate("Administrator refunds are allowed.", role="administrator"),
        )
        a_id, b_id = a["candidate_identity"], b["candidate_identity"]
        self.assertTrue(
            transition_allowed(
                "investigating", "resolved", owner_readback_confirmed=True
            )
        )
        self.assertFalse(transition_allowed("investigating", "resolved"))
        self.assertFalse(
            transition_allowed("investigating", "rejected", authority_basis_ref="DEC-1")
        )
        self.assertTrue(
            transition_allowed(
                "investigating",
                "rejected",
                authority_basis_ref="DEC-1",
                owner_readback_confirmed=True,
            )
        )
        a["related_candidate_refs"] = [
            {"candidate_identity": b_id, "relation": "competing_hypothesis"}
        ]
        b["related_candidate_refs"] = [
            {"candidate_identity": a_id, "relation": "competing_hypothesis"}
        ]
        validate_candidate_relations([a, b])
        a["related_candidate_refs"] = [
            {"candidate_identity": b_id, "relation": "merged_into"}
        ]
        b["related_candidate_refs"] = [
            {"candidate_identity": a_id, "relation": "replaced_by"}
        ]
        with self.assertRaises(ContractError):
            validate_candidate_relations(iter([a, b]))

    def test_secret_like_candidate_text_is_rejected(self) -> None:
        candidate = build_candidate("api_key=abcdefgh12345678")
        with self.assertRaises(ContractError):
            validate_artifact(candidate, "context-rule-candidate")

    def test_impact_detects_addition_authority_change_and_missing_revision(
        self,
    ) -> None:
        saved = [
            {
                "source_kind": "spec",
                "artifact_ref": SOURCE_REF,
                "source_revision": "r1",
                "content_hash": SOURCE_HASH,
                "effective_authority_fingerprint": "c" * 64,
            }
        ]
        current = copy.deepcopy(saved)
        self.assertEqual(impact(current, saved)["status"], "current")
        current[0]["effective_authority_fingerprint"] = "d" * 64
        self.assertEqual(impact(current, saved)["status"], "changed")
        current = copy.deepcopy(saved)
        current[0]["source_revision"] = None
        self.assertEqual(impact(current, saved)["status"], "unverifiable")
        current.append({**saved[0], "artifact_ref": "project/decision/DEC-1"})
        self.assertEqual(impact(current, saved)["status"], "changed")

    def test_run_never_completes_from_self_declaration_without_provider_readback(
        self,
    ) -> None:
        run = build_run()
        self.assertTrue(validate_artifact(run, "context-synthesis-run"))
        self.assertEqual(
            completion_check(run, root_binding=ROOT_BINDING),
            {
                "complete": False,
                "status": "unverifiable",
                "reason": "provider_readbacks_required",
            },
        )

    def test_completed_run_requires_exact_candidate_and_run_readbacks(self) -> None:
        candidate = build_candidate()
        candidate_content = canonical_bytes(candidate).decode("utf-8")
        candidate_hash = hashlib.sha256(candidate_content.encode("utf-8")).hexdigest()
        updated_candidate = copy.deepcopy(candidate)
        updated_candidate["rule_statement"] = "Updated wording for the same hypothesis."
        updated_content = canonical_bytes(updated_candidate).decode("utf-8")
        updated_hash = hashlib.sha256(updated_content.encode("utf-8")).hexdigest()
        run = build_run()
        run["triage_plan"]["planned_candidate_ops"] = [
            {
                "candidate_identity": candidate["candidate_identity"],
                "candidate_ref": candidate["artifact_ref"],
                "action": "update",
                "base_content_hash": candidate_hash,
                "expected_revision": "r1",
                "related_preconditions": [],
                "operation_id": "provider-op-1",
                "planned_content_hash": updated_hash,
                "planned_payload": updated_candidate,
                "write_request_meta": {
                    "source_ref": SOURCE_REF,
                    "source_revision": "r3",
                    "approval_ref": "approval:qa-write",
                    "approval_revision": "r1",
                    "change_reason": "Reuse the current candidate after readback.",
                },
                "confirmed_result": {
                    "artifact_ref": candidate["artifact_ref"],
                    "storage_revision": "r2",
                    "content_hash": updated_hash,
                },
            }
        ]
        run["result_summary"]["status"] = "completed"
        run["result_summary"]["zero_change_reason"] = None
        self.assertTrue(validate_artifact(run, "context-synthesis-run"))
        run_content = canonical_bytes(run).decode("utf-8")
        run_hash = hashlib.sha256(run_content.encode("utf-8")).hexdigest()
        readbacks = [
            {
                "kind": "spec",
                "root_binding": ROOT_BINDING,
                "artifact_ref": SOURCE_REF,
                "revision": "r3",
                "sha256": SOURCE_HASH,
                "content": SOURCE_CONTENT,
            },
            {
                "kind": "context-rule-candidate",
                "root_binding": ROOT_BINDING,
                "artifact_ref": candidate["artifact_ref"],
                "revision": "r1",
                "sha256": candidate_hash,
                "content": candidate_content,
            },
            {
                "kind": "context-rule-candidate",
                "root_binding": ROOT_BINDING,
                "artifact_ref": candidate["artifact_ref"],
                "revision": "r2",
                "sha256": updated_hash,
                "content": updated_content,
            },
            {
                "kind": "context-synthesis-run",
                "root_binding": ROOT_BINDING,
                "artifact_ref": run["artifact_ref"],
                "revision": "r3",
                "sha256": run_hash,
                "content": run_content,
            },
        ]
        self.assertTrue(
            completion_check(
                run,
                root_binding=ROOT_BINDING,
                provider_readbacks=readbacks,
                run_readback_revision="r3",
            )["complete"]
        )
        self.assertFalse(
            completion_check(
                run,
                root_binding="another-root",
                provider_readbacks=readbacks,
                run_readback_revision="r3",
            )["complete"]
        )
        readbacks[2]["content"] = updated_content + " "
        self.assertFalse(
            completion_check(
                run,
                root_binding=ROOT_BINDING,
                provider_readbacks=readbacks,
                run_readback_revision="r3",
            )["complete"]
        )

    def test_target_batches_bind_start_input_snapshot_and_exact_readback(self) -> None:
        batch = build_batch()
        batch_content = canonical_bytes(batch).decode("utf-8")
        batch_hash = hashlib.sha256(batch_content.encode("utf-8")).hexdigest()
        batch_revision = "batch-r1"
        run = build_run()
        run["operation_input"]["input_sources"].append(
            {
                "artifact_ref": batch["artifact_ref"],
                "content_hash": batch_hash,
                "effective_authority_fingerprint": None,
                "source_revision": batch_revision,
            }
        )
        run["operation_input"]["input_sources"].sort(
            key=lambda item: item["artifact_ref"]
        )
        run["snapshot"]["referenced_sources"].append(
            {
                "source_kind": "signal_batch",
                "artifact_ref": batch["artifact_ref"],
                "source_revision": batch_revision,
                "content_hash": batch_hash,
                "effective_authority_fingerprint": None,
            }
        )
        run["snapshot"]["referenced_sources"].sort(
            key=lambda item: (item["artifact_ref"], item["source_revision"])
        )
        run["snapshot"]["snapshot_hash"] = snapshot_hash(run["snapshot"])
        run["triage_plan"]["target_batch_refs"] = [batch["artifact_ref"]]
        operation_id = workflow_operation_id(
            run["workflow_ref"], run["operation_input"], run["requested_scope"]
        )
        run["workflow_operation_id"] = operation_id
        run["run_identity"] = run_identity(operation_id)
        run["artifact_ref"] = artifact_ref("context-synthesis-run", run["run_identity"])
        run_content = canonical_bytes(run).decode("utf-8")
        run_hash = hashlib.sha256(run_content.encode("utf-8")).hexdigest()
        readbacks = [
            {
                "kind": "spec",
                "root_binding": ROOT_BINDING,
                "artifact_ref": SOURCE_REF,
                "revision": "r3",
                "sha256": SOURCE_HASH,
                "content": SOURCE_CONTENT,
            },
            {
                "kind": "context-signal-batch",
                "root_binding": ROOT_BINDING,
                "artifact_ref": batch["artifact_ref"],
                "revision": batch_revision,
                "sha256": batch_hash,
                "content": batch_content,
            },
            {
                "kind": "context-synthesis-run",
                "root_binding": ROOT_BINDING,
                "artifact_ref": run["artifact_ref"],
                "revision": "run-r1",
                "sha256": run_hash,
                "content": run_content,
            },
        ]

        self.assertTrue(validate_artifact(run, "context-synthesis-run"))
        self.assertTrue(
            completion_check(
                run,
                root_binding=ROOT_BINDING,
                provider_readbacks=readbacks,
                run_readback_revision="run-r1",
            )["complete"]
        )
        without_target = [readbacks[0], readbacks[2]]
        result = completion_check(
            run,
            root_binding=ROOT_BINDING,
            provider_readbacks=without_target,
            run_readback_revision="run-r1",
        )
        self.assertEqual(result["reason"], "target_batch_readback_missing")
