from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
ITEM_SCRIPTS = ROOT / "skills" / "test-item-analysis" / "scripts"
CONDITION_SCRIPTS = ROOT / "skills" / "test-condition-analysis" / "scripts"
QA_WORKFLOW_SCRIPTS = ROOT / "skills" / "qa-workflow" / "scripts"
sys.path.insert(0, str(ITEM_SCRIPTS))
sys.path.insert(0, str(CONDITION_SCRIPTS))
sys.path.insert(0, str(QA_WORKFLOW_SCRIPTS))

from artifact_graph import _validate_claim_details  # noqa: E402
from candidate_support import (  # noqa: E402
    MAX_INPUT_BYTES,
    ContractError,
    canonical_bytes,
    fingerprint,
    strict_loads,
)
from condition_candidates import run as run_conditions  # noqa: E402
from item_artifact_contract import (  # noqa: E402
    validate_item_artifact as validate_crosscheck_item_artifact,
)
from item_candidates import (  # noqa: E402
    run as run_items,
)
from item_candidates import (  # noqa: E402
    validate_artifact as validate_item_artifact,
)


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _refresh_artifact_fingerprint(artifact):
    artifact["content_fingerprint"] = fingerprint(
        {key: value for key, value in artifact.items() if key != "content_fingerprint"}
    )
    return artifact


def _stored_readback(artifact, *, owner, artifact_ref, revision=None):
    """Simulate a provider that stores bytes and reports the hash of what it reads back.

    Mirrors A's local baseline: content_hash is the SHA-256 of the stored bytes and
    the provider revision is a separate "sha256:"-prefixed provider-owned value.
    """
    stored = json.dumps(
        artifact, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "artifact.json"
        path.write_bytes(stored)
        read_back = path.read_bytes()
    digest = hashlib.sha256(read_back).hexdigest()
    return {
        "owner": owner,
        "scope": artifact["scope"],
        "artifact_ref": artifact_ref,
        "revision": revision or f"sha256:{digest}",
        "content_hash": digest,
    }


def _feature_analysis(snapshot, status):
    sources = sorted(snapshot["sources"], key=lambda row: row["id"])
    features = sorted(snapshot["features"], key=lambda row: row["id"])
    source_boundary = (
        bool(snapshot["expected_source_ids"])
        and not snapshot["unknown_areas"]
        and all(
            any(
                source["id"] == source_id and source["status"] == "complete"
                for source in sources
            )
            for source_id in snapshot["expected_source_ids"]
        )
    )
    source_ids = {row["id"]: row for row in snapshot["sources"]}
    reasons = []
    if not snapshot["expected_source_ids"]:
        reasons.append("source_boundary_unconfirmed")
    for source_id in snapshot["expected_source_ids"]:
        source = source_ids.get(source_id)
        if source is None:
            reasons.append(f"source_missing:{source_id}")
        elif source["status"] != "complete":
            reasons.append(f"source_incomplete:{source_id}")
    if snapshot["unknown_areas"]:
        reasons.append("unknown_areas_present")
    if not snapshot["changes"]:
        reasons.append("change_denominator_zero")
    if not snapshot["candidates"]:
        reasons.append("candidate_denominator_zero")
    reasons = sorted(set(reasons))
    if status == "complete" and reasons:
        raise AssertionError(
            "fixture cannot report a complete B analysis with unresolved reasons"
        )
    if status == "incomplete" and not reasons:
        reasons = ["fixture_incomplete"]
    snapshot_sha256 = _sha(
        json.dumps(snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    )
    handoff = {
        "snapshot_sha256": snapshot_sha256,
        "source_inventory": [
            {
                "id": row["id"],
                "ref": row["ref"],
                "status": row["status"],
                "revision": row.get("revision"),
                "unretrieved": row["unretrieved"],
            }
            for row in sources
        ],
        "artifact_ref": snapshot["artifact_ref"],
        "artifact_revision": snapshot["artifact_revision"],
        "source_revision": snapshot["source_revision"],
        "feature_ids": [row["id"] for row in features],
        "feature_refs": [
            {
                "id": row["id"],
                "kind": row["kind"],
                "status": row["status"],
                "parent_id": row["parent_id"],
                "source_ids": row["source_ids"],
                "implementation_refs": row["implementation_refs"],
                "spec_refs": row["spec_refs"],
                "qa_refs": row["qa_refs"],
            }
            for row in features
        ],
        "impacted_feature_ids": sorted(
            {
                feature_id
                for row in snapshot["changes"]
                if row["classification"] == "impact"
                for feature_id in row["feature_ids"]
            }
        ),
        "approval_required_change_ids": sorted(
            row["id"]
            for row in snapshot["changes"]
            if row["classification"] in {"no_impact", "out_of_scope"}
        ),
        "unknown_areas": snapshot["unknown_areas"],
        "unclassified_change_ids": sorted(
            row["id"]
            for row in snapshot["changes"]
            if row["classification"] not in {"impact", "no_impact", "out_of_scope"}
        ),
        "expected_source_ids": snapshot["expected_source_ids"],
    }
    return {
        "status": status,
        "reasons": reasons,
        "metrics": {
            "change_classification": {
                "numerator_ids": sorted(
                    row["id"]
                    for row in snapshot["changes"]
                    if row["classification"] in {"impact", "no_impact", "out_of_scope"}
                ),
                "denominator_ids": sorted(row["id"] for row in snapshot["changes"]),
                "rate": (
                    sum(
                        row["classification"] in {"impact", "no_impact", "out_of_scope"}
                        for row in snapshot["changes"]
                    )
                    / len(snapshot["changes"])
                    if snapshot["changes"]
                    else None
                ),
            },
            "observed_candidate_mapping": {
                "numerator_ids": sorted(
                    row["id"]
                    for row in snapshot["candidates"]
                    if row["status"] == "mapped"
                ),
                "denominator_ids": sorted(row["id"] for row in snapshot["candidates"]),
                "rate": (
                    sum(row["status"] == "mapped" for row in snapshot["candidates"])
                    / len(snapshot["candidates"])
                    if snapshot["candidates"]
                    else None
                ),
            },
            "source_boundary_complete": source_boundary,
            "unknown_areas": snapshot["unknown_areas"],
            "excluded_candidate_ids": sorted(
                row["id"]
                for row in snapshot["candidates"]
                if row["status"] == "excluded"
            ),
            "all_product_features_discovered": None,
        },
        "handoff": handoff,
    }


def feature_inventory(*, features=None, status="complete", source_status="complete"):
    rows = (
        features
        if features is not None
        else [
            {"id": "FEAT-001", "status": "implemented"},
            {"id": "FEAT-002", "status": "planned"},
        ]
    )
    feature_rows = []
    for index, row in enumerate(rows, start=1):
        feature_id = row["id"]
        feature_rows.append(
            {
                "id": feature_id,
                "identity": f"fixture identity {feature_id}",
                "name": f"Fixture {feature_id}",
                "kind": "api",
                "status": row["status"],
                "parent_id": None,
                "source_ids": ["SRC-001"],
                "implementation_refs": [f"src/feature-{index}.py"],
                "spec_refs": [],
                "qa_refs": [],
            }
        )
    complete_source = source_status == "complete"
    effective_status = (
        "incomplete" if status == "complete" and not feature_rows else status
    )
    snapshot = {
        "schema_version": "feature-inventory-v1",
        "project_ref": "project:shop",
        "artifact_ref": "feature-inventory:shop",
        "artifact_revision": "feature-r1",
        "previous_artifact_revision": None,
        "source_revision": "commit:abc123",
        "operation_id": "fixture:feature-1",
        "event": "initial",
        "expected_source_ids": ["SRC-001"],
        "sources": [
            {
                "id": "SRC-001",
                "kind": "code",
                "ref": "product/repo",
                "scope": "src",
                "status": source_status,
                "revision": "commit:abc123" if complete_source else None,
                "evidence_ref": "evidence/sources" if complete_source else None,
                "enumeration_complete": complete_source,
                "unretrieved": [],
                **({} if complete_source else {"reason": "source access denied"}),
            }
        ],
        "features": feature_rows,
        "candidates": [
            {
                "id": "CAND-001",
                "source_ids": ["SRC-001"],
                "evidence_ref": "evidence/candidate",
                "status": "mapped",
                "feature_id": "FEAT-001",
            }
        ],
        "changes": [
            {
                "id": "DIF-001",
                "source_id": "SRC-001",
                "before_revision": "commit:old",
                "after_revision": "commit:abc123",
                "locator": "src/auth.py",
                "evidence_ref": "evidence/diff",
                "classification": "impact",
                "feature_ids": ["FEAT-001"],
                "reason": "Authorization behavior changed",
            }
        ],
        "history": [
            {
                "event_id": "feature-event-001",
                "kind": "added",
                "revision": "commit:abc123",
                "evidence_ref": "evidence/created",
                "from_ids": [],
                "to_ids": ["FEAT-001"],
            }
        ],
        "unknown_areas": [],
    }
    if not feature_rows:
        snapshot["candidates"] = []
        snapshot["changes"] = []
        snapshot["history"] = []
    elif effective_status == "incomplete" and complete_source:
        snapshot["changes"] = []
        snapshot["candidates"] = []
    return {
        "snapshot": snapshot,
        "analysis": _feature_analysis(snapshot, effective_status),
    }


def unresolved_feature_inventory(*, unknown_areas=None, unretrieved=None):
    value = feature_inventory(
        status="incomplete", source_status="denied" if unretrieved else "complete"
    )
    snapshot = value["snapshot"]
    if unknown_areas:
        snapshot["unknown_areas"] = list(unknown_areas)
    if unretrieved:
        snapshot["sources"][0]["unretrieved"] = list(unretrieved)
    return {
        "snapshot": snapshot,
        "analysis": _feature_analysis(snapshot, "incomplete"),
    }


def feature_ref(revision=None, content_hash=None):
    if revision is None or content_hash is None:
        snapshot = feature_inventory()
        revision = snapshot["snapshot"]["artifact_revision"]
        content_hash = snapshot["analysis"]["handoff"]["snapshot_sha256"]
    return {
        "owner": "feature-analysis",
        "scope": "project:shop",
        "artifact_ref": "feature-inventory:shop",
        "revision": revision,
        "content_hash": content_hash,
    }


def _feature_ref_for(snapshot):
    b_snapshot = snapshot["snapshot"]
    handoff = snapshot["analysis"]["handoff"]
    return feature_ref(
        revision=b_snapshot["artifact_revision"],
        content_hash=handoff["snapshot_sha256"],
    )


def spec_ref(revision="spec-r1", content_hash="b" * 64):
    return {
        "owner": "spec-analysis",
        "scope": "project:shop",
        "artifact_ref": "authority:shop",
        "revision": revision,
        "content_hash": content_hash,
    }


def item_candidate(
    key,
    *,
    name=None,
    feature_refs=None,
    evidence_refs=None,
    parent_refs=None,
    action="new",
    item_id=None,
    related=None,
    status="implemented",
    reason="fixture candidate identity review",
    kind="api",
    description="candidate product test target",
):
    return {
        "candidate_key": key,
        "identity_action": action,
        "item_id": item_id,
        "related_item_ids": related or [],
        "reason": reason,
        "name": name or key,
        "description": description,
        "kind": kind,
        "status": status,
        "parent_item_refs": parent_refs or [],
        "feature_refs": feature_refs or ["FEAT-001"],
        "evidence_refs": [feature_ref()] if evidence_refs is None else evidence_refs,
    }


def item_request(
    *,
    candidates=None,
    feature_snapshot=None,
    sources=None,
    previous=None,
    expected=None,
    current=None,
    retirements=None,
    artifact_ref="item-candidates:shop",
):
    snapshot = feature_snapshot or feature_inventory()
    source_rows = sources or [_feature_ref_for(snapshot), spec_ref()]
    if not any(row["owner"] == "feature-analysis" for row in source_rows):
        source_rows = [*source_rows, feature_ref()]
    return {
        "operation": "materialize",
        "scope": "project:shop",
        "artifact_ref": artifact_ref,
        "feature_inventory": snapshot,
        "source_refs": source_rows,
        "expected_revision": expected,
        "current_revision": current,
        "approval_ref": None,
        "required_permission": "owner_artifact_write",
        "previous_artifact": previous,
        "candidates": candidates or [],
        "retirements": retirements or [],
    }


def condition_candidate(
    key,
    *,
    name=None,
    feature_refs=None,
    item_refs=None,
    evidence_refs=None,
    authorities=None,
    action="new",
    condition_id=None,
    related=None,
    state="candidate",
    unknowns=None,
    reason="fixture candidate identity review",
    item_kinds=None,
    kind="authorization",
    intent="verify a source-backed authorization condition",
):
    evidence = [feature_ref(), spec_ref()] if evidence_refs is None else evidence_refs
    auth_rows = (
        authorities
        if authorities is not None
        else [{"source_ref": spec_ref(), "entity_ref": "AUTH-001"}]
    )
    return {
        "candidate_key": key,
        "identity_action": action,
        "condition_id": condition_id,
        "related_condition_ids": related or [],
        "reason": reason,
        "name": name or key,
        "intent": intent,
        "kind": kind,
        "applicable_item_kinds": item_kinds or ["api", "ui"],
        "feature_refs": feature_refs or ["FEAT-001"],
        "item_refs": item_refs or [],
        "authority_refs": auth_rows,
        "evidence_refs": evidence,
        "candidate_state": state,
        "unknowns": unknowns or [],
    }


def condition_request(
    *,
    candidates=None,
    feature_snapshot=None,
    sources=None,
    previous=None,
    expected=None,
    current=None,
    retirements=None,
    artifact_ref="condition-candidates:shop",
):
    snapshot = feature_snapshot or feature_inventory()
    source_rows = sources or [_feature_ref_for(snapshot), spec_ref()]
    if not any(row["owner"] == "feature-analysis" for row in source_rows):
        source_rows = [*source_rows, feature_ref()]
    return {
        "operation": "materialize",
        "scope": "project:shop",
        "artifact_ref": artifact_ref,
        "feature_inventory": snapshot,
        "source_refs": source_rows,
        "expected_revision": expected,
        "current_revision": current,
        "approval_ref": None,
        "required_permission": "owner_artifact_write",
        "previous_artifact": previous,
        "candidates": candidates or [],
        "retirements": retirements or [],
    }


def _materialize_item(request):
    result = run_items(request)
    if not result["valid"]:
        raise AssertionError(result)
    return result


def _materialize_condition(request):
    result = run_conditions(request)
    if not result["valid"]:
        raise AssertionError(result)
    return result


def _assert_contract_code(test_case, expected_code, operation):
    with test_case.assertRaises(ContractError) as caught:
        operation()
    test_case.assertEqual(caught.exception.code, expected_code)


class TestItemAnalysisContract(unittest.TestCase):
    def test_stable_ids_parent_children_many_to_many_and_same_name_remain_distinct(
        self,
    ):
        result = _materialize_item(
            item_request(
                candidates=[
                    item_candidate(
                        "parent", name="Checkout", kind="api", feature_refs=["FEAT-001"]
                    ),
                    item_candidate(
                        "z_child",
                        name="Checkout",
                        kind="batch",
                        feature_refs=["FEAT-001", "FEAT-002"],
                        parent_refs=["@draft:parent"],
                    ),
                ]
            )
        )
        artifact = result["candidate"]
        rows = {row["item_id"]: row for row in artifact["items"]}
        self.assertEqual(
            result["candidate_item_ids"], {"parent": "ITEM-001", "z_child": "ITEM-002"}
        )
        self.assertEqual(rows["ITEM-002"]["parent_item_ids"], ["ITEM-001"])
        self.assertEqual(rows["ITEM-002"]["feature_refs"], ["FEAT-001", "FEAT-002"])
        self.assertEqual(rows["ITEM-001"]["name"], rows["ITEM-002"]["name"])
        self.assertEqual(len(artifact["id_history"]), 2)
        self.assertEqual(result["status"], "candidate_ready_unpersisted")
        self.assertFalse(result["write_precondition"]["performed"])
        self.assertTrue(result["write_precondition"]["requires_provider_native_cas"])

    def test_cycle_unknown_parent_missing_source_and_manual_id_are_rejected(self):
        cyclic = item_request(
            candidates=[
                item_candidate("left", parent_refs=["@draft:right"]),
                item_candidate("right", parent_refs=["@draft:left"]),
            ]
        )
        _assert_contract_code(self, "item_parent_cycle", lambda: run_items(cyclic))
        missing_parent = item_request(
            candidates=[item_candidate("child", parent_refs=["ITEM-999"])]
        )
        _assert_contract_code(
            self, "item_parent_missing", lambda: run_items(missing_parent)
        )
        missing_source = item_request(
            candidates=[item_candidate("item", evidence_refs=[])]
        )
        _assert_contract_code(
            self, "missing_source_ref", lambda: run_items(missing_source)
        )
        manual_id = item_request(
            candidates=[item_candidate("item", item_id="ITEM-777")]
        )
        _assert_contract_code(
            self, "manual_item_id_forbidden", lambda: run_items(manual_id)
        )

    def test_partial_and_zero_population_never_report_a_rate(self):
        partial = feature_inventory(status="incomplete", source_status="denied")
        result = _materialize_item(
            item_request(feature_snapshot=partial, candidates=[])
        )
        self.assertEqual(result["status"], "incomplete")
        self.assertIsNone(result["item_candidate_coverage"]["rate"])
        self.assertIsNone(result["item_candidate_coverage"]["denominator"])
        empty = feature_inventory(features=[])
        zero = _materialize_item(item_request(feature_snapshot=empty, candidates=[]))
        self.assertIsNone(zero["item_candidate_coverage"]["rate"])
        self.assertIsNone(zero["item_candidate_coverage"]["denominator"])
        blocked = feature_inventory(status="blocked")
        _assert_contract_code(
            self,
            "feature_inventory_not_current",
            lambda: run_items(item_request(feature_snapshot=blocked, candidates=[])),
        )

    def test_no_change_replay_preserves_unresolved_analysis_state(self):
        incomplete = feature_inventory(status="incomplete")
        item_first = _materialize_item(
            item_request(
                feature_snapshot=incomplete,
                candidates=[
                    item_candidate(
                        "partial-item",
                        evidence_refs=[_feature_ref_for(incomplete)],
                    )
                ],
            )
        )
        self.assertEqual(item_first["analysis_status"], "incomplete")
        self.assertEqual(item_first["status"], "incomplete")
        self.assertTrue(item_first["issues"])
        item_replay = run_items(
            item_request(
                feature_snapshot=incomplete,
                candidates=[
                    item_candidate(
                        "partial-item",
                        action="reuse",
                        item_id="ITEM-001",
                        evidence_refs=[_feature_ref_for(incomplete)],
                    )
                ],
                previous=item_first["candidate"],
                expected="provider-r1",
                current="provider-r1",
            )
        )
        self.assertEqual(item_replay["status"], "no_change")
        self.assertEqual(item_replay["analysis_status"], "incomplete")
        self.assertEqual(item_replay["issues"], item_first["issues"])
        self.assertEqual(
            item_replay["item_candidate_coverage"],
            item_first["item_candidate_coverage"],
        )
        self.assertEqual(
            item_replay["unrepresented_feature_ids"],
            item_first["unrepresented_feature_ids"],
        )
        self.assertEqual(item_replay["unrepresented_feature_ids"], ["FEAT-002"])
        self.assertIn(
            "unrepresented_feature_candidates",
            {row["code"] for row in item_replay["issues"]},
        )
        self.assertEqual(
            item_replay["item_candidate_coverage"]["status"],
            "not_measurable_incomplete_population",
        )
        self.assertIsNone(item_replay["item_candidate_coverage"]["rate"])
        self.assertEqual(
            item_replay["write_precondition"],
            {"performed": False, "provider_selected": False},
        )
        self.assertEqual(item_replay["candidate"], item_first["candidate"])

        condition_first = _materialize_condition(
            condition_request(
                feature_snapshot=incomplete,
                candidates=[
                    condition_candidate(
                        "partial-condition",
                        evidence_refs=[_feature_ref_for(incomplete), spec_ref()],
                        authorities=[
                            {
                                "source_ref": spec_ref(),
                                "entity_ref": "AUTH-001",
                            }
                        ],
                    )
                ],
            )
        )
        self.assertEqual(condition_first["analysis_status"], "incomplete")
        self.assertEqual(condition_first["status"], "incomplete")
        self.assertTrue(condition_first["issues"])
        condition_replay = run_conditions(
            condition_request(
                feature_snapshot=incomplete,
                candidates=[
                    condition_candidate(
                        "partial-condition",
                        action="reuse",
                        condition_id="COND-001",
                        evidence_refs=[_feature_ref_for(incomplete), spec_ref()],
                        authorities=[
                            {
                                "source_ref": spec_ref(),
                                "entity_ref": "AUTH-001",
                            }
                        ],
                    )
                ],
                previous=condition_first["candidate"],
                expected="provider-r1",
                current="provider-r1",
            )
        )
        self.assertEqual(condition_replay["status"], "no_change")
        self.assertEqual(condition_replay["analysis_status"], "incomplete")
        self.assertEqual(condition_replay["issues"], condition_first["issues"])
        self.assertEqual(
            condition_replay["write_precondition"],
            {"performed": False, "provider_selected": False},
        )
        self.assertEqual(condition_replay["candidate"], condition_first["candidate"])

        crosscheck_first = run_conditions(
            {
                "operation": "crosscheck",
                "item_artifact": item_first["candidate"],
                "condition_artifact": condition_first["candidate"],
                "candidate_pairs": [],
            }
        )
        crosscheck_replay = run_conditions(
            {
                "operation": "crosscheck",
                "item_artifact": item_replay["candidate"],
                "condition_artifact": condition_replay["candidate"],
                "candidate_pairs": [],
            }
        )
        self.assertEqual(crosscheck_replay, crosscheck_first)
        self.assertEqual(crosscheck_replay["status"], "incomplete")
        self.assertTrue(crosscheck_replay["issues"])

    def test_no_change_replay_preserves_unknown_area_and_unretrieved_source(self):
        cases = [
            (
                "unknown_area",
                unresolved_feature_inventory(unknown_areas=["external auth flow"]),
                "feature_population_incomplete",
            ),
            (
                "unretrieved_source",
                unresolved_feature_inventory(unretrieved=["src/auth/**"]),
                "feature_population_incomplete",
            ),
        ]
        for name, snapshot, issue_code in cases:
            with self.subTest(state=name):
                item_ref = _feature_ref_for(snapshot)
                item_first = _materialize_item(
                    item_request(
                        feature_snapshot=snapshot,
                        candidates=[
                            item_candidate("partial", evidence_refs=[item_ref])
                        ],
                    )
                )
                item_replay = run_items(
                    item_request(
                        feature_snapshot=snapshot,
                        candidates=[
                            item_candidate(
                                "partial",
                                action="reuse",
                                item_id="ITEM-001",
                                evidence_refs=[item_ref],
                            )
                        ],
                        previous=item_first["candidate"],
                        expected="provider-r1",
                        current="provider-r1",
                    )
                )
                self.assertEqual(item_replay["status"], "no_change")
                self.assertEqual(item_replay["analysis_status"], "incomplete")
                self.assertIn(
                    issue_code, {row["code"] for row in item_replay["issues"]}
                )
                self.assertEqual(item_replay["candidate"], item_first["candidate"])

                condition_first = _materialize_condition(
                    condition_request(
                        feature_snapshot=snapshot,
                        candidates=[
                            condition_candidate(
                                "partial",
                                evidence_refs=[item_ref, spec_ref()],
                            )
                        ],
                    )
                )
                condition_replay = run_conditions(
                    condition_request(
                        feature_snapshot=snapshot,
                        candidates=[
                            condition_candidate(
                                "partial",
                                action="reuse",
                                condition_id="COND-001",
                                evidence_refs=[item_ref, spec_ref()],
                            )
                        ],
                        previous=condition_first["candidate"],
                        expected="provider-r1",
                        current="provider-r1",
                    )
                )
                self.assertEqual(condition_replay["status"], "no_change")
                self.assertEqual(condition_replay["analysis_status"], "incomplete")
                self.assertIn(
                    issue_code,
                    {row["code"] for row in condition_replay["issues"]},
                )
                self.assertEqual(
                    condition_replay["candidate"], condition_first["candidate"]
                )

    def test_complete_no_change_is_deterministic_and_requests_no_write(self):
        item = _materialize_item(
            item_request(
                candidates=[
                    item_candidate("stable", feature_refs=["FEAT-001", "FEAT-002"])
                ]
            )
        )
        item_request_again = item_request(
            candidates=[
                item_candidate(
                    "stable",
                    action="reuse",
                    item_id="ITEM-001",
                    feature_refs=["FEAT-001", "FEAT-002"],
                )
            ],
            previous=item["candidate"],
            expected="provider-r1",
            current="provider-r1",
        )
        item_replay = run_items(item_request_again)
        item_second_replay = run_items(
            item_request(
                candidates=[
                    item_candidate(
                        "stable",
                        action="reuse",
                        item_id="ITEM-001",
                        feature_refs=["FEAT-001", "FEAT-002"],
                    )
                ],
                previous=item_replay["candidate"],
                expected="provider-r2",
                current="provider-r2",
            )
        )
        self.assertEqual(item_replay["status"], "no_change")
        self.assertEqual(item_replay["analysis_status"], "complete")
        self.assertTrue(item_replay["valid"])
        self.assertEqual(item_replay["issues"], [])
        self.assertEqual(item_replay["candidate_item_ids"], {"stable": "ITEM-001"})
        self.assertEqual(
            item_replay["candidate"]["content_fingerprint"],
            item["candidate"]["content_fingerprint"],
        )
        self.assertEqual(
            item_replay["candidate"]["history"], item["candidate"]["history"]
        )
        self.assertEqual(item_replay, item_second_replay)
        self.assertEqual(
            item_replay["write_precondition"],
            {"performed": False, "provider_selected": False},
        )

        condition = _materialize_condition(
            condition_request(candidates=[condition_candidate("stable")])
        )
        condition_replay = run_conditions(
            condition_request(
                candidates=[
                    condition_candidate(
                        "stable", action="reuse", condition_id="COND-001"
                    )
                ],
                previous=condition["candidate"],
                expected="provider-r1",
                current="provider-r1",
            )
        )
        self.assertEqual(condition_replay["status"], "no_change")
        self.assertEqual(condition_replay["analysis_status"], "complete")
        self.assertTrue(condition_replay["valid"])
        self.assertEqual(condition_replay["issues"], [])
        self.assertEqual(
            condition_replay["candidate_condition_ids"], {"stable": "COND-001"}
        )
        self.assertEqual(
            condition_replay["candidate"]["content_fingerprint"],
            condition["candidate"]["content_fingerprint"],
        )
        self.assertEqual(
            condition_replay["candidate"]["history"], condition["candidate"]["history"]
        )
        condition_second_replay = run_conditions(
            condition_request(
                candidates=[
                    condition_candidate(
                        "stable", action="reuse", condition_id="COND-001"
                    )
                ],
                previous=condition_replay["candidate"],
                expected="provider-r2",
                current="provider-r2",
            )
        )
        self.assertEqual(condition_replay, condition_second_replay)
        self.assertEqual(
            condition_replay["write_precondition"],
            {"performed": False, "provider_selected": False},
        )

    def test_no_change_keeps_unconfirmed_and_blocked_conditions_unresolved(self):
        candidates = [
            condition_candidate(
                "blocked",
                state="blocked",
                authorities=[],
                unknowns=["waiting for security evidence"],
            ),
            condition_candidate(
                "unconfirmed",
                state="unconfirmed",
                authorities=[],
                unknowns=["authority is not confirmed"],
            ),
        ]
        first = _materialize_condition(condition_request(candidates=candidates))
        ids = first["candidate_condition_ids"]
        replay = run_conditions(
            condition_request(
                candidates=[
                    condition_candidate(
                        row["candidate_key"],
                        action="reuse",
                        condition_id=ids[row["candidate_key"]],
                        state=row["candidate_state"],
                        authorities=[],
                        unknowns=row["unknowns"],
                    )
                    for row in candidates
                ],
                previous=first["candidate"],
                expected="provider-r1",
                current="provider-r1",
            )
        )
        self.assertEqual(first["status"], "incomplete")
        self.assertEqual(replay["status"], "no_change")
        self.assertEqual(replay["analysis_status"], "incomplete")
        self.assertEqual(replay["unconfirmed_condition_ids"], [ids["unconfirmed"]])
        self.assertEqual(replay["blocked_condition_ids"], [ids["blocked"]])
        self.assertEqual(replay["recheck_condition_ids"], sorted(ids.values()))
        self.assertEqual(
            {row["code"] for row in replay["issues"]},
            {"unconfirmed_conditions", "blocked_conditions"},
        )
        self.assertEqual(replay["candidate"], first["candidate"])

    def test_invalid_previous_artifacts_are_rejected_before_no_change(self):
        item = _materialize_item(
            item_request(candidates=[item_candidate("valid-item")])
        )["candidate"]
        invalid_item = copy.deepcopy(item)
        invalid_item["items"][0]["name"] = ""
        _refresh_artifact_fingerprint(invalid_item)
        _assert_contract_code(
            self,
            "invalid_field",
            lambda: run_items(
                item_request(
                    candidates=[],
                    previous=invalid_item,
                    expected="provider-r1",
                    current="provider-r1",
                )
            ),
        )

        condition = _materialize_condition(
            condition_request(candidates=[condition_candidate("valid-condition")])
        )["candidate"]
        invalid_condition = copy.deepcopy(condition)
        invalid_condition["conditions"][0]["name"] = ""
        _refresh_artifact_fingerprint(invalid_condition)
        _assert_contract_code(
            self,
            "invalid_field",
            lambda: run_conditions(
                condition_request(
                    candidates=[],
                    previous=invalid_condition,
                    expected="provider-r1",
                    current="provider-r1",
                )
            ),
        )

    def test_revision_conflict_blocks_without_allocating_ids(self):
        request = item_request(
            candidates=[item_candidate("new")], expected="rev-a", current="rev-b"
        )
        result = run_items(request)
        self.assertEqual(result["status"], "blocked")
        self.assertIsNone(result["candidate"])
        self.assertEqual(result["issues"][0]["code"], "cas_conflict")

    def test_reuse_split_retirement_and_nonreuse_history(self):
        first = _materialize_item(
            item_request(candidates=[item_candidate("original")])
        )["candidate"]
        reused = _materialize_item(
            item_request(
                candidates=[
                    item_candidate(
                        "same",
                        action="reuse",
                        item_id="ITEM-001",
                        description="updated description",
                    )
                ],
                previous=first,
                expected="storage-r1",
                current="storage-r1",
            )
        )["candidate"]
        self.assertEqual(reused["items"][0]["item_id"], "ITEM-001")
        self.assertIn("updated", [event["action"] for event in reused["history"]])
        split = _materialize_item(
            item_request(
                candidates=[
                    item_candidate("split", action="split", related=["ITEM-001"])
                ],
                previous=reused,
                expected="storage-r2",
                current="storage-r2",
            )
        )["candidate"]
        self.assertEqual(split["id_history"], ["ITEM-001", "ITEM-002"])
        self.assertIn("split", [event["action"] for event in split["history"]])
        retired = _materialize_item(
            item_request(
                candidates=[],
                retirements=[
                    {
                        "item_id": "ITEM-001",
                        "reason": "source confirms removal",
                        "evidence_refs": [feature_ref()],
                    }
                ],
                previous=split,
                expected="storage-r3",
                current="storage-r3",
            )
        )["candidate"]
        retired_row = next(
            row for row in retired["items"] if row["item_id"] == "ITEM-001"
        )
        self.assertEqual(retired_row["status"], "retired")
        self.assertEqual(retired["id_history"], ["ITEM-001", "ITEM-002"])
        _assert_contract_code(
            self,
            "item_reuse_invalid",
            lambda: run_items(
                item_request(
                    candidates=[
                        item_candidate("bad-reuse", action="reuse", item_id="ITEM-001")
                    ],
                    previous=retired,
                    expected="storage-r4",
                    current="storage-r4",
                )
            ),
        )
        next_item = _materialize_item(
            item_request(
                candidates=[item_candidate("after-retire")],
                previous=retired,
                expected="storage-r4",
                current="storage-r4",
            )
        )["candidate"]
        self.assertIn("ITEM-003", next_item["id_history"])

    def test_merge_requires_explicit_retirement_and_keeps_history(self):
        first = _materialize_item(
            item_request(
                candidates=[
                    item_candidate("one"),
                    item_candidate("two"),
                ]
            )
        )["candidate"]
        bad_identity = item_request(
            candidates=[
                item_candidate("merge-one", action="merge", related=["ITEM-001"])
            ],
            previous=first,
            expected="storage-r1",
            current="storage-r1",
        )
        _assert_contract_code(
            self, "merge_source_invalid", lambda: run_items(bad_identity)
        )
        invalid = item_request(
            candidates=[
                item_candidate(
                    "merge", action="merge", related=["ITEM-001", "ITEM-002"]
                )
            ],
            previous=first,
            expected="storage-r1",
            current="storage-r1",
        )
        _assert_contract_code(
            self, "merge_sources_not_retired", lambda: run_items(invalid)
        )
        merged = _materialize_item(
            item_request(
                candidates=[
                    item_candidate(
                        "merge", action="merge", related=["ITEM-001", "ITEM-002"]
                    )
                ],
                retirements=[
                    {
                        "item_id": "ITEM-001",
                        "reason": "same behavior consolidated",
                        "evidence_refs": [feature_ref()],
                    },
                    {
                        "item_id": "ITEM-002",
                        "reason": "same behavior consolidated",
                        "evidence_refs": [feature_ref()],
                    },
                ],
                previous=first,
                expected="storage-r1",
                current="storage-r1",
            )
        )["candidate"]
        self.assertEqual(merged["id_history"], ["ITEM-001", "ITEM-002", "ITEM-003"])
        self.assertEqual(
            {row["item_id"]: row["status"] for row in merged["items"]},
            {
                "ITEM-001": "retired",
                "ITEM-002": "retired",
                "ITEM-003": "implemented",
            },
        )
        merge_event = next(
            row for row in merged["history"] if row["action"] == "merged"
        )
        self.assertEqual(merge_event["related_item_ids"], ["ITEM-001", "ITEM-002"])

    def test_source_change_impacts_only_linked_item(self):
        result = _materialize_item(
            item_request(
                candidates=[
                    item_candidate("feature-backed", evidence_refs=[feature_ref()]),
                    item_candidate("authority-backed", evidence_refs=[spec_ref()]),
                ]
            )
        )
        current_sources = [
            feature_ref(),
            spec_ref(revision="spec-r2", content_hash="c" * 64),
        ]
        impact = run_items(
            {
                "operation": "impact",
                "artifact": result["candidate"],
                "current_source_refs": current_sources,
            }
        )
        self.assertEqual(
            impact["impacted_item_ids"],
            [result["candidate_item_ids"]["authority-backed"]],
        )
        self.assertEqual(
            impact["unaffected_item_ids"],
            [result["candidate_item_ids"]["feature-backed"]],
        )

    def test_retired_item_source_change_needs_no_revalidation(self):
        first = _materialize_item(
            item_request(
                candidates=[
                    item_candidate(
                        "active",
                        feature_refs=["FEAT-001", "FEAT-002"],
                        evidence_refs=[feature_ref()],
                    ),
                    item_candidate("legacy", evidence_refs=[spec_ref()]),
                ]
            )
        )
        legacy_id = first["candidate_item_ids"]["legacy"]
        retired = _materialize_item(
            item_request(
                candidates=[
                    item_candidate(
                        "active",
                        action="reuse",
                        item_id=first["candidate_item_ids"]["active"],
                        feature_refs=["FEAT-001", "FEAT-002"],
                        evidence_refs=[feature_ref()],
                    )
                ],
                retirements=[
                    {
                        "item_id": legacy_id,
                        "reason": "source confirms removal",
                        "evidence_refs": [feature_ref()],
                    }
                ],
                previous=first["candidate"],
                expected="provider-r1",
                current="provider-r1",
            )
        )["candidate"]
        changed_sources = [
            feature_ref(),
            spec_ref(revision="spec-r2", content_hash="c" * 64),
        ]

        impact = run_items(
            {
                "operation": "impact",
                "artifact": retired,
                "current_source_refs": changed_sources,
            }
        )
        self.assertEqual(impact["status"], "current")
        self.assertEqual(impact["issues"], [])
        self.assertEqual(impact["impacted_item_ids"], [])
        self.assertEqual(impact["source_unknown_item_ids"], [])
        self.assertEqual(impact["retired_item_ids"], [legacy_id])
        self.assertEqual(impact["unaffected_item_ids"], ["ITEM-001"])

        events_before = len(retired["history"])
        updated = _materialize_item(
            item_request(
                sources=changed_sources,
                candidates=[
                    item_candidate(
                        "active",
                        action="reuse",
                        item_id="ITEM-001",
                        feature_refs=["FEAT-001", "FEAT-002"],
                        evidence_refs=[feature_ref()],
                    )
                ],
                previous=retired,
                expected="provider-r2",
                current="provider-r2",
            )
        )
        self.assertEqual(updated["status"], "candidate_ready_unpersisted")
        self.assertEqual(updated["analysis_status"], "complete")
        self.assertEqual(updated["issues"], [])
        self.assertEqual(updated["stale_item_ids"], [])
        self.assertEqual(updated["unknown_item_ids"], [])
        self.assertEqual(updated["recheck_item_ids"], [])
        self.assertEqual(updated["impacted_item_ids"], [])
        self.assertEqual(len(updated["candidate"]["history"]), events_before)
        self.assertNotIn(
            "source_changed",
            [event["action"] for event in updated["candidate"]["history"]],
        )
        retired_row = next(
            row for row in updated["candidate"]["items"] if row["item_id"] == legacy_id
        )
        self.assertEqual(retired_row["status"], "retired")
        validate_item_artifact(updated["candidate"])

        # The same changed evidence on a live (not retired) item still needs revalidation.
        live = _materialize_item(
            item_request(
                sources=changed_sources,
                candidates=[],
                previous=first["candidate"],
                expected="provider-r2",
                current="provider-r2",
            )
        )
        self.assertEqual(live["status"], "incomplete")
        self.assertEqual(live["stale_item_ids"], [legacy_id])
        self.assertEqual(live["recheck_item_ids"], [legacy_id])
        self.assertIn(
            "source_changed",
            [event["action"] for event in live["candidate"]["history"]],
        )

    def test_unknown_feature_status_is_not_a_confirmed_active_denominator(self):
        snapshot = feature_inventory(
            features=[
                {"id": "FEAT-001", "status": "implemented"},
                {"id": "FEAT-002", "status": "unknown"},
            ]
        )
        request = item_request(
            feature_snapshot=snapshot,
            candidates=[
                item_candidate(
                    "covers-all",
                    feature_refs=["FEAT-001", "FEAT-002"],
                    evidence_refs=[_feature_ref_for(snapshot)],
                )
            ],
        )
        first = _materialize_item(request)
        self.assertEqual(first["status"], "incomplete")
        self.assertEqual(first["analysis_status"], "incomplete")
        self.assertEqual(first["unknown_feature_ids"], ["FEAT-002"])
        self.assertEqual(first["unrepresented_feature_ids"], [])
        self.assertIn(
            "unknown_feature_status", {row["code"] for row in first["issues"]}
        )
        coverage = first["item_candidate_coverage"]
        self.assertEqual(coverage["status"], "not_measurable_unknown_feature_status")
        self.assertIsNone(coverage["rate"])
        self.assertIsNone(coverage["denominator"])
        # Non-measurable: the unknown feature must not leak into the numerator either.
        self.assertIsNone(coverage["numerator"])

        replay = _materialize_item(
            item_request(
                feature_snapshot=snapshot,
                candidates=[
                    item_candidate(
                        "covers-all",
                        action="reuse",
                        item_id="ITEM-001",
                        feature_refs=["FEAT-001", "FEAT-002"],
                        evidence_refs=[_feature_ref_for(snapshot)],
                    )
                ],
                previous=first["candidate"],
                expected="provider-r1",
                current="provider-r1",
            )
        )
        self.assertEqual(replay["status"], "no_change")
        self.assertEqual(replay["analysis_status"], "incomplete")
        self.assertEqual(replay["unknown_feature_ids"], ["FEAT-002"])
        self.assertEqual(
            replay["item_candidate_coverage"]["status"],
            "not_measurable_unknown_feature_status",
        )

        confirmed = _materialize_item(
            item_request(
                candidates=[
                    item_candidate(
                        "covers-all",
                        feature_refs=["FEAT-001", "FEAT-002"],
                    )
                ]
            )
        )
        self.assertEqual(confirmed["unknown_feature_ids"], [])
        self.assertEqual(confirmed["item_candidate_coverage"]["status"], "measured")
        self.assertEqual(confirmed["item_candidate_coverage"]["rate"], 1.0)
        self.assertEqual(confirmed["item_candidate_coverage"]["numerator"], 2)
        self.assertEqual(confirmed["item_candidate_coverage"]["denominator"], 2)

    def test_readback_accepts_hash_of_stored_content_not_candidate_fingerprint(self):
        result = _materialize_item(item_request(candidates=[item_candidate("item")]))
        candidate = result["candidate"]
        readback = _stored_readback(
            candidate, owner="test-item-analysis", artifact_ref="item-candidates:shop"
        )
        # The provider hash covers the whole stored artifact, so it can never equal
        # the fingerprint that excludes content_fingerprint, nor the provider revision.
        self.assertNotEqual(readback["content_hash"], candidate["content_fingerprint"])
        self.assertNotEqual(readback["revision"], candidate["content_fingerprint"])
        self.assertEqual(
            readback["content_hash"],
            result["write_precondition"]["storage_content_sha256"],
        )
        self.assertEqual(
            result["write_precondition"]["storage_content_encoding"],
            "canonical-json-utf8",
        )
        good = run_items(
            {
                "operation": "validate_readback",
                "candidate_artifact": candidate,
                "readback": readback,
                "expected_revision": readback["revision"],
            }
        )
        self.assertTrue(good["valid"])
        self.assertEqual(good["issues"], [])
        self.assertEqual(
            good["candidate_fingerprint"], candidate["content_fingerprint"]
        )
        self.assertEqual(good["storage_content_sha256"], readback["content_hash"])
        self.assertEqual(
            good["provider_authenticity"], "not_established_by_this_validator"
        )
        self.assertEqual(good["provider_cas"], "not_established_by_this_validator")

    def test_readback_rejects_fingerprint_tamper_and_revision_mismatch(self):
        candidate = _materialize_item(
            item_request(candidates=[item_candidate("item")])
        )["candidate"]
        readback = _stored_readback(
            candidate, owner="test-item-analysis", artifact_ref="item-candidates:shop"
        )

        def check(rb, **extra):
            return run_items(
                {
                    "operation": "validate_readback",
                    "candidate_artifact": candidate,
                    "readback": rb,
                    **extra,
                }
            )

        # Reporting the candidate fingerprint as the stored hash is the old confusion.
        confused = check({**readback, "content_hash": candidate["content_fingerprint"]})
        self.assertFalse(confused["valid"])
        self.assertEqual(confused["issues"][0]["code"], "readback_hash_mismatch")

        tampered = copy.deepcopy(candidate)
        tampered["items"][0]["description"] = "tampered after save"
        tampered_rb = _stored_readback(
            tampered, owner="test-item-analysis", artifact_ref="item-candidates:shop"
        )
        self.assertEqual(
            check(tampered_rb)["issues"][0]["code"], "readback_hash_mismatch"
        )
        _assert_contract_code(
            self,
            "item_fingerprint_mismatch",
            lambda: run_items(
                {
                    "operation": "validate_readback",
                    "candidate_artifact": tampered,
                    "readback": tampered_rb,
                }
            ),
        )

        wrong_revision = check(readback, expected_revision="sha256:" + "0" * 64)
        self.assertFalse(wrong_revision["valid"])
        self.assertEqual(
            [row["code"] for row in wrong_revision["issues"]],
            ["readback_revision_mismatch"],
        )
        # Without an expected revision the provider revision stays opaque.
        self.assertTrue(check({**readback, "revision": "provider-r9"})["valid"])
        _assert_contract_code(
            self,
            "readback_identity_mismatch",
            lambda: check({**readback, "scope": "project:other"}),
        )
        _assert_contract_code(
            self,
            "readback_hash_invalid",
            lambda: check({**readback, "content_hash": "ABC"}),
        )
        _assert_contract_code(
            self, "request_schema", lambda: check(readback, unexpected=True)
        )


class TestConditionAnalysisContract(unittest.TestCase):
    def test_independent_stable_condition_id_and_name_collision(self):
        result = _materialize_condition(
            condition_request(
                candidates=[
                    condition_candidate("first", name="Login lockout"),
                    condition_candidate("second", name="Login lockout", item_refs=[]),
                ]
            )
        )
        artifact = result["candidate"]
        self.assertEqual(
            result["candidate_condition_ids"],
            {"first": "COND-001", "second": "COND-002"},
        )
        self.assertEqual(
            [row["name"] for row in artifact["conditions"]],
            ["Login lockout", "Login lockout"],
        )
        self.assertEqual(artifact["conditions"][0]["candidate_state"], "candidate")
        self.assertTrue(artifact["conditions"][0]["authority_refs"])

    def test_authority_missing_means_unconfirmed_and_no_manual_id(self):
        unconfirmed = condition_candidate(
            "unconfirmed",
            authorities=[],
            state="unconfirmed",
            unknowns=["Authority not yet confirmed"],
        )
        result = _materialize_condition(condition_request(candidates=[unconfirmed]))
        self.assertEqual(
            result["candidate"]["conditions"][0]["candidate_state"], "unconfirmed"
        )
        invalid = condition_candidate("invalid", authorities=[], state="candidate")
        _assert_contract_code(
            self,
            "condition_authority_required",
            lambda: run_conditions(condition_request(candidates=[invalid])),
        )
        manual = condition_candidate("manual", condition_id="COND-900")
        _assert_contract_code(
            self,
            "manual_condition_id_forbidden",
            lambda: run_conditions(condition_request(candidates=[manual])),
        )

    def test_condition_source_impact_and_cas_conflict(self):
        result = _materialize_condition(
            condition_request(
                candidates=[
                    condition_candidate(
                        "source-a",
                        evidence_refs=[feature_ref()],
                        authorities=[],
                        state="unconfirmed",
                        unknowns=["Authority evidence pending"],
                    ),
                    condition_candidate("source-b", evidence_refs=[spec_ref()]),
                ]
            )
        )
        impact = run_conditions(
            {
                "operation": "impact",
                "artifact": result["candidate"],
                "current_source_refs": [
                    feature_ref(),
                    spec_ref(revision="spec-r2", content_hash="c" * 64),
                ],
            }
        )
        self.assertEqual(impact["impacted_condition_ids"], ["COND-002"])
        conflict = run_conditions(
            condition_request(
                candidates=[condition_candidate("new")],
                expected="rev-1",
                current="rev-2",
            )
        )
        self.assertEqual(conflict["status"], "blocked")
        self.assertIsNone(conflict["candidate"])

    def test_split_merge_retirement_preserve_ids(self):
        first = _materialize_condition(
            condition_request(candidates=[condition_candidate("base")])
        )["candidate"]
        split = _materialize_condition(
            condition_request(
                candidates=[
                    condition_candidate("split", action="split", related=["COND-001"])
                ],
                previous=first,
                expected="store-r1",
                current="store-r1",
            )
        )["candidate"]
        self.assertEqual(split["id_history"], ["COND-001", "COND-002"])
        self.assertIn("split", [event["action"] for event in split["history"]])
        retired = _materialize_condition(
            condition_request(
                candidates=[],
                retirements=[
                    {
                        "condition_id": "COND-001",
                        "reason": "meaning superseded",
                        "evidence_refs": [spec_ref()],
                    }
                ],
                previous=split,
                expected="store-r2",
                current="store-r2",
            )
        )["candidate"]
        self.assertEqual(retired["id_history"], ["COND-001", "COND-002"])
        _assert_contract_code(
            self,
            "condition_reuse_invalid",
            lambda: run_conditions(
                condition_request(
                    candidates=[
                        condition_candidate(
                            "reuse", action="reuse", condition_id="COND-001"
                        )
                    ],
                    previous=retired,
                    expected="store-r3",
                    current="store-r3",
                )
            ),
        )

    def test_merge_requires_explicit_retirement_and_keeps_history(self):
        first = _materialize_condition(
            condition_request(
                candidates=[
                    condition_candidate("one"),
                    condition_candidate("two"),
                ]
            )
        )["candidate"]
        bad_identity = condition_request(
            candidates=[
                condition_candidate("merge-one", action="merge", related=["COND-001"])
            ],
            previous=first,
            expected="store-r1",
            current="store-r1",
        )
        _assert_contract_code(
            self, "merge_source_invalid", lambda: run_conditions(bad_identity)
        )
        invalid = condition_request(
            candidates=[
                condition_candidate(
                    "merge", action="merge", related=["COND-001", "COND-002"]
                )
            ],
            previous=first,
            expected="store-r1",
            current="store-r1",
        )
        _assert_contract_code(
            self, "merge_sources_not_retired", lambda: run_conditions(invalid)
        )
        merged = _materialize_condition(
            condition_request(
                candidates=[
                    condition_candidate(
                        "merge", action="merge", related=["COND-001", "COND-002"]
                    )
                ],
                retirements=[
                    {
                        "condition_id": "COND-001",
                        "reason": "same condition consolidated",
                        "evidence_refs": [spec_ref()],
                    },
                    {
                        "condition_id": "COND-002",
                        "reason": "same condition consolidated",
                        "evidence_refs": [spec_ref()],
                    },
                ],
                previous=first,
                expected="store-r1",
                current="store-r1",
            )
        )["candidate"]
        self.assertEqual(merged["id_history"], ["COND-001", "COND-002", "COND-003"])
        self.assertEqual(
            [row["condition_id"] for row in merged["conditions"]], ["COND-003"]
        )
        self.assertEqual(
            {
                row["condition_id"]
                for row in merged["history"]
                if row["action"] == "retired"
            },
            {"COND-001", "COND-002"},
        )
        merge_event = next(
            row for row in merged["history"] if row["action"] == "merged"
        )
        self.assertEqual(merge_event["related_condition_ids"], ["COND-001", "COND-002"])

    def test_crosscheck_only_explicit_pairs_and_keeps_metrics_separate(self):
        item_result = _materialize_item(
            item_request(
                candidates=[
                    item_candidate("one", feature_refs=["FEAT-001"]),
                ]
            )
        )
        condition_result = _materialize_condition(
            condition_request(
                candidates=[
                    condition_candidate("one", feature_refs=["FEAT-001"]),
                    condition_candidate("two", feature_refs=["FEAT-002"]),
                ]
            )
        )
        result = run_conditions(
            {
                "operation": "crosscheck",
                "item_artifact": item_result["candidate"],
                "condition_artifact": condition_result["candidate"],
                "candidate_pairs": [
                    {
                        "item_id": "ITEM-001",
                        "condition_id": "COND-001",
                        "status": "proposed",
                        "rationale": "shared source scope",
                        "evidence_refs": [spec_ref()],
                    }
                ],
            }
        )
        self.assertTrue(result["valid"])
        self.assertEqual(result["unrepresented_feature_refs"], ["FEAT-002"])
        self.assertEqual(
            result["candidate_pairs"],
            [
                {
                    "item_id": "ITEM-001",
                    "condition_id": "COND-001",
                    "status": "proposed",
                    "rationale": "shared source scope",
                    "evidence_refs": [spec_ref()],
                    "machine_check_issues": [],
                }
            ],
        )
        self.assertFalse(result["cartesian_product_generated"])
        self.assertEqual(result["metrics"]["candidate_pair_count"], 1)
        self.assertIsNone(result["metrics"]["formal_tcn_ci_design"]["count"])
        self.assertEqual(result["candidate_identification_coverage"]["rate"], 0.5)

    def test_partial_and_zero_denominator_metrics_are_null(self):
        partial = feature_inventory(status="incomplete", source_status="denied")
        item_result = _materialize_item(
            item_request(feature_snapshot=partial, candidates=[])
        )
        condition_result = _materialize_condition(
            condition_request(
                feature_snapshot=partial,
                candidates=[
                    condition_candidate(
                        "one",
                        feature_refs=["FEAT-001"],
                        evidence_refs=[_feature_ref_for(partial), spec_ref()],
                    ),
                ],
            )
        )
        result = run_conditions(
            {
                "operation": "crosscheck",
                "item_artifact": item_result["candidate"],
                "condition_artifact": condition_result["candidate"],
                "candidate_pairs": [],
            }
        )
        self.assertIsNone(result["candidate_identification_coverage"]["rate"])
        self.assertIsNone(result["candidate_identification_coverage"]["denominator"])
        empty = feature_inventory(features=[])
        empty_items = _materialize_item(
            item_request(feature_snapshot=empty, candidates=[])
        )["candidate"]
        empty_conditions = _materialize_condition(
            condition_request(feature_snapshot=empty, candidates=[])
        )["candidate"]
        zero = run_conditions(
            {
                "operation": "crosscheck",
                "item_artifact": empty_items,
                "condition_artifact": empty_conditions,
                "candidate_pairs": [],
            }
        )
        self.assertIsNone(zero["candidate_identification_coverage"]["rate"])
        self.assertEqual(
            zero["candidate_identification_coverage"]["status"],
            "not_measurable_zero_denominator",
        )

    def test_formal_disposition_and_revision_mismatch_are_rejected(self):
        item_artifact = _materialize_item(
            item_request(candidates=[item_candidate("one")])
        )["candidate"]
        condition_artifact = _materialize_condition(
            condition_request(candidates=[condition_candidate("one")])
        )["candidate"]
        _assert_contract_code(
            self,
            "formal_disposition_forbidden",
            lambda: run_conditions(
                {
                    "operation": "crosscheck",
                    "item_artifact": item_artifact,
                    "condition_artifact": condition_artifact,
                    "candidate_pairs": [
                        {
                            "item_id": "ITEM-001",
                            "condition_id": "COND-001",
                            "status": "adopted",
                            "rationale": "incorrect formal decision",
                            "evidence_refs": [spec_ref()],
                        }
                    ],
                }
            ),
        )
        changed_feature = feature_inventory()
        changed_feature["snapshot"]["artifact_revision"] = "feature-r2"
        changed_feature["analysis"] = _feature_analysis(
            changed_feature["snapshot"], "complete"
        )
        changed_feature_ref = _feature_ref_for(changed_feature)
        stale_condition = _materialize_condition(
            condition_request(
                feature_snapshot=changed_feature,
                candidates=[
                    condition_candidate(
                        "one",
                        feature_refs=["FEAT-001"],
                        evidence_refs=[changed_feature_ref, spec_ref()],
                    )
                ],
            )
        )["candidate"]
        _assert_contract_code(
            self,
            "feature_revision_mismatch",
            lambda: run_conditions(
                {
                    "operation": "crosscheck",
                    "item_artifact": item_artifact,
                    "condition_artifact": stale_condition,
                    "candidate_pairs": [],
                }
            ),
        )

    def test_blocked_condition_pair_cannot_be_promoted_to_a_proposed_pair(self):
        item_artifact = _materialize_item(
            item_request(candidates=[item_candidate("one")])
        )["candidate"]
        blocked_condition = _materialize_condition(
            condition_request(
                candidates=[
                    condition_candidate(
                        "blocked",
                        authorities=[],
                        state="blocked",
                        unknowns=["Authority evidence is unavailable"],
                    ),
                ]
            )
        )["candidate"]
        proposed = {
            "operation": "crosscheck",
            "item_artifact": item_artifact,
            "condition_artifact": blocked_condition,
            "candidate_pairs": [
                {
                    "item_id": "ITEM-001",
                    "condition_id": "COND-001",
                    "status": "proposed",
                    "rationale": "must not promote a blocked condition",
                    "evidence_refs": [spec_ref()],
                }
            ],
        }
        _assert_contract_code(
            self, "candidate_pair_unconfirmed", lambda: run_conditions(proposed)
        )
        proposed["candidate_pairs"][0]["status"] = "blocked"
        result = run_conditions(proposed)
        self.assertEqual(result["candidate_pairs"][0]["status"], "blocked")
        self.assertIsNone(result["metrics"]["formal_applicability_decisions"]["count"])
        self.assertIsNone(result["metrics"]["formal_tcn_ci_design"]["count"])
        self.assertIsNone(result["metrics"]["execution"]["count"])

    def test_provider_readback_uses_stored_content_hash_not_fingerprint(self):
        result = _materialize_condition(
            condition_request(candidates=[condition_candidate("one")])
        )
        candidate = result["candidate"]
        readback = _stored_readback(
            candidate,
            owner="test-condition-analysis",
            artifact_ref="condition-candidates:shop",
        )
        self.assertNotEqual(readback["content_hash"], candidate["content_fingerprint"])
        self.assertEqual(
            readback["content_hash"],
            result["write_precondition"]["storage_content_sha256"],
        )

        def check(rb, **extra):
            return run_conditions(
                {
                    "operation": "validate_readback",
                    "candidate_artifact": candidate,
                    "readback": rb,
                    **extra,
                }
            )

        good = check(readback, expected_revision=readback["revision"])
        self.assertTrue(good["valid"])
        self.assertEqual(
            good["candidate_fingerprint"], candidate["content_fingerprint"]
        )
        self.assertEqual(good["provider_cas"], "not_established_by_this_validator")
        confused = check({**readback, "content_hash": candidate["content_fingerprint"]})
        self.assertEqual(confused["issues"][0]["code"], "readback_hash_mismatch")
        tampered = copy.deepcopy(candidate)
        tampered["conditions"][0]["intent"] = "tampered after save"
        tampered_rb = _stored_readback(
            tampered,
            owner="test-condition-analysis",
            artifact_ref="condition-candidates:shop",
        )
        self.assertEqual(
            check(tampered_rb)["issues"][0]["code"], "readback_hash_mismatch"
        )
        self.assertEqual(
            [
                row["code"]
                for row in check(readback, expected_revision="provider-r9")["issues"]
            ],
            ["readback_revision_mismatch"],
        )

    def test_unknown_feature_status_keeps_condition_materialize_incomplete(self):
        unknown_snapshot = feature_inventory(
            features=[
                {"id": "FEAT-001", "status": "implemented"},
                {"id": "FEAT-002", "status": "unknown"},
            ]
        )

        def request_for(snapshot, **extra):
            return condition_request(
                feature_snapshot=snapshot,
                candidates=[
                    condition_candidate(
                        "covers",
                        feature_refs=["FEAT-001"],
                        evidence_refs=[_feature_ref_for(snapshot), spec_ref()],
                    )
                ],
                **extra,
            )

        first = _materialize_condition(request_for(unknown_snapshot))
        self.assertTrue(first["valid"])
        self.assertEqual(first["status"], "incomplete")
        self.assertEqual(first["analysis_status"], "incomplete")
        self.assertEqual(first["unknown_feature_ids"], ["FEAT-002"])
        issues = {row["code"]: row for row in first["issues"]}
        self.assertIn("unknown_feature_status", issues)
        self.assertFalse(issues["unknown_feature_status"]["blocking"])
        # The unknown feature does not change the candidate artifact or its history.
        self.assertEqual(
            first["candidate"]["conditions"][0]["condition_id"], "COND-001"
        )

        replay = _materialize_condition(
            condition_request(
                feature_snapshot=unknown_snapshot,
                candidates=[
                    condition_candidate(
                        "covers",
                        action="reuse",
                        condition_id="COND-001",
                        feature_refs=["FEAT-001"],
                        evidence_refs=[_feature_ref_for(unknown_snapshot), spec_ref()],
                    )
                ],
                previous=first["candidate"],
                expected="provider-r1",
                current="provider-r1",
            )
        )
        self.assertEqual(replay["status"], "no_change")
        self.assertEqual(replay["analysis_status"], "incomplete")
        self.assertEqual(replay["unknown_feature_ids"], ["FEAT-002"])
        self.assertIn(
            "unknown_feature_status", {row["code"] for row in replay["issues"]}
        )

        # Confirmed (and retired) features alone keep the normal path.
        for features in (
            None,
            [
                {"id": "FEAT-001", "status": "implemented"},
                {"id": "FEAT-002", "status": "retired"},
            ],
        ):
            confirmed_snapshot = feature_inventory(features=features)
            confirmed = _materialize_condition(request_for(confirmed_snapshot))
            self.assertEqual(confirmed["status"], "candidate_ready_unpersisted")
            self.assertEqual(confirmed["analysis_status"], "complete")
            self.assertEqual(confirmed["unknown_feature_ids"], [])
            self.assertNotIn(
                "unknown_feature_status", {row["code"] for row in confirmed["issues"]}
            )

        # A partial population stays incomplete without being reported as unknown.
        partial = _materialize_condition(
            request_for(feature_inventory(status="incomplete", source_status="denied"))
        )
        self.assertEqual(partial["analysis_status"], "incomplete")
        self.assertEqual(partial["unknown_feature_ids"], [])

        # Item, condition and crosscheck agree on the unknown-feature population.
        item_result = _materialize_item(
            item_request(
                feature_snapshot=unknown_snapshot,
                candidates=[
                    item_candidate(
                        "covers",
                        feature_refs=["FEAT-001"],
                        evidence_refs=[_feature_ref_for(unknown_snapshot)],
                    )
                ],
            )
        )
        self.assertEqual(item_result["unknown_feature_ids"], ["FEAT-002"])
        self.assertEqual(item_result["analysis_status"], first["analysis_status"])
        crosscheck = run_conditions(
            {
                "operation": "crosscheck",
                "item_artifact": item_result["candidate"],
                "condition_artifact": first["candidate"],
                "candidate_pairs": [],
            }
        )
        self.assertEqual(crosscheck["status"], "incomplete")
        self.assertEqual(
            crosscheck["candidate_identification_coverage"]["status"],
            "not_measurable_unknown_feature_status",
        )
        self.assertIsNone(crosscheck["candidate_identification_coverage"]["numerator"])

    def test_cli_is_self_contained_for_isolated_skill_package(self):
        item_request_json = item_request(candidates=[item_candidate("cli-item")])
        item_completed = subprocess.run(
            [sys.executable, str(ITEM_SCRIPTS / "item_candidates.py")],
            input=json.dumps(item_request_json).encode("utf-8"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        item_result = json.loads(item_completed.stdout)
        self.assertTrue(item_result["valid"])
        self.assertEqual(item_result["candidate_item_ids"]["cli-item"], "ITEM-001")

        request = condition_request(candidates=[condition_candidate("cli")])
        completed = subprocess.run(
            [sys.executable, str(CONDITION_SCRIPTS / "condition_candidates.py")],
            input=json.dumps(request).encode("utf-8"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        result = json.loads(completed.stdout)
        self.assertTrue(result["valid"])
        self.assertEqual(result["candidate_condition_ids"]["cli"], "COND-001")


class TestInputSecurityContracts(unittest.TestCase):
    def test_strict_json_rejects_malformed_and_duplicate_input(self):
        cases = [
            (b"{", "invalid_json"),
            (
                b'{"operation":"validate","operation":"materialize"}',
                "duplicate_json_key",
            ),
            (b'{"value":"\xff"}', "invalid_json"),
        ]
        for raw, expected_code in cases:
            with self.subTest(expected_code=expected_code, size=len(raw)):
                with self.assertRaises(ContractError) as caught:
                    strict_loads(raw)
                self.assertEqual(caught.exception.code, expected_code)

    def test_deep_json_cannot_become_a_valid_artifact(self):
        nested_artifact = b"[" * 2500 + b"0" + b"]" * 2500
        raw = b'{"operation":"validate","artifact":' + nested_artifact + b"}"
        for script in (
            ITEM_SCRIPTS / "item_candidates.py",
            CONDITION_SCRIPTS / "condition_candidates.py",
        ):
            with self.subTest(script=script.name):
                completed = subprocess.run(
                    [sys.executable, str(script)],
                    input=raw,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=True,
                )
                result = json.loads(completed.stdout)
                self.assertFalse(result["valid"])
                self.assertEqual(result["status"], "blocked")

    def test_non_finite_constants_and_values_are_rejected(self):
        for constant in (b"NaN", b"Infinity", b"-Infinity"):
            with self.subTest(constant=constant):
                with self.assertRaises(ContractError) as caught:
                    strict_loads(b'{"value":' + constant + b"}")
                self.assertEqual(caught.exception.code, "invalid_json_constant")

        for value in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(value=value):
                with self.assertRaises(ContractError) as caught:
                    canonical_bytes({"value": value})
                self.assertEqual(caught.exception.code, "invalid_json_value")

    def test_input_size_limit_fails_closed_in_both_isolated_clis(self):
        oversized = b" " * (MAX_INPUT_BYTES + 1)
        for script in (
            ITEM_SCRIPTS / "item_candidates.py",
            CONDITION_SCRIPTS / "condition_candidates.py",
        ):
            with self.subTest(script=script.name):
                completed = subprocess.run(
                    [sys.executable, str(script)],
                    input=oversized,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=True,
                )
                result = json.loads(completed.stdout)
                self.assertFalse(result["valid"])
                self.assertEqual(result["status"], "blocked")
                self.assertIn(
                    "limit_exceeded", {issue["code"] for issue in result["issues"]}
                )

    def test_json_parse_failures_are_consistent_across_isolated_clis(self):
        inputs = (
            (
                b'{"operation":"validate","operation":"materialize"}',
                "duplicate_json_key",
            ),
            (b'{"operation":"validate","value":NaN}', "invalid_json_constant"),
        )
        for script in (
            ITEM_SCRIPTS / "item_candidates.py",
            CONDITION_SCRIPTS / "condition_candidates.py",
        ):
            for raw, expected_code in inputs:
                with self.subTest(script=script.name, expected_code=expected_code):
                    completed = subprocess.run(
                        [sys.executable, str(script)],
                        input=raw,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        check=True,
                    )
                    result = json.loads(completed.stdout)
                    self.assertFalse(result["valid"])
                    self.assertIn(
                        expected_code,
                        {issue["code"] for issue in result["issues"]},
                    )


class TestReviewRegressionFindings(unittest.TestCase):
    @staticmethod
    def crosscheck(item_artifact, condition_artifact, candidate_pairs=None):
        return run_conditions(
            {
                "operation": "crosscheck",
                "item_artifact": item_artifact,
                "condition_artifact": condition_artifact,
                "candidate_pairs": candidate_pairs or [],
            }
        )

    def test_crosscheck_reports_stale_or_unknown_condition_in_proposed_pair(self):
        initial_item = _materialize_item(
            item_request(
                candidates=[
                    item_candidate(
                        "current-item", evidence_refs=[feature_ref(), spec_ref()]
                    )
                ]
            )
        )["candidate"]
        changed_spec = spec_ref(revision="spec-r2", content_hash="c" * 64)
        current_item = _materialize_item(
            item_request(
                candidates=[
                    item_candidate(
                        "current-item",
                        action="reuse",
                        item_id="ITEM-001",
                        evidence_refs=[feature_ref(), changed_spec],
                    )
                ],
                sources=[feature_ref(), changed_spec],
                previous=initial_item,
                expected="storage-r1",
                current="storage-r1",
            )
        )["candidate"]
        self.assertEqual(current_item["items"][0]["currentness"], "current")

        def lagging_condition(initial, sources):
            return _materialize_condition(
                condition_request(
                    candidates=[],
                    sources=sources,
                    previous=initial,
                    expected="storage-r1",
                    current="storage-r1",
                )
            )["candidate"]

        initial_condition = _materialize_condition(
            condition_request(candidates=[condition_candidate("lagging-condition")])
        )["candidate"]
        stale_condition = lagging_condition(
            initial_condition, [feature_ref(), changed_spec]
        )
        unknown_condition = lagging_condition(initial_condition, [feature_ref()])

        def pair(status):
            return {
                "item_id": "ITEM-001",
                "condition_id": "COND-001",
                "status": status,
                "rationale": "pair against a condition whose evidence moved",
                "evidence_refs": [spec_ref()],
            }

        for artifact, reason, listed in (
            (stale_condition, "condition_stale", "stale_condition_ids"),
            (
                unknown_condition,
                "condition_currentness_unknown",
                "unknown_condition_ids",
            ),
        ):
            self.assertEqual(artifact["conditions"][0]["candidate_state"], "candidate")
            for status in ("proposed", "unconfirmed"):
                with self.subTest(reason=reason, status=status):
                    result = self.crosscheck(current_item, artifact, [pair(status)])
                    self.assertTrue(result["valid"])
                    self.assertEqual(result["status"], "incomplete")
                    # Never accepted as a confirmed pair, and no formal decision is made.
                    self.assertEqual(result["candidate_pairs"], [])
                    self.assertEqual(
                        result["items_without_pair_proposal"], ["ITEM-001"]
                    )
                    self.assertEqual(len(result["unresolved_condition_references"]), 1)
                    reference = result["unresolved_condition_references"][0]
                    self.assertEqual(reference["reason"], reason)
                    self.assertEqual(reference["condition_id"], "COND-001")
                    self.assertEqual(reference["item_id"], "ITEM-001")
                    self.assertEqual(reference["state"], "unconfirmed")
                    self.assertEqual(reference["candidate_pair"]["status"], status)
                    self.assertEqual(result["recheck_condition_ids"], ["COND-001"])
                    self.assertEqual(result["recheck_item_ids"], ["ITEM-001"])
                    # Other diagnostics are kept alongside the unresolved reference.
                    self.assertEqual(result[listed], ["COND-001"])
                    self.assertEqual(result["unresolved_item_references"], [])
                    codes = {row["code"] for row in result["issues"]}
                    self.assertIn("unresolved_candidate_references", codes)
                    self.assertFalse(result["cartesian_product_generated"])
                    self.assertIsNone(
                        result["metrics"]["formal_applicability_decisions"]["count"]
                    )

        # A condition that is still unconfirmed/blocked must not be promoted, even when
        # its evidence is also stale or unknown.
        for state, unknowns, authorities in (
            ("unconfirmed", ["owner decision pending"], None),
            ("blocked", ["Authority evidence is unavailable"], []),
        ):
            initial = _materialize_condition(
                condition_request(
                    candidates=[
                        condition_candidate(
                            "not-a-candidate",
                            state=state,
                            unknowns=unknowns,
                            authorities=authorities,
                        )
                    ]
                )
            )["candidate"]
            for sources in ([feature_ref(), changed_spec], [feature_ref()]):
                with self.subTest(state=state, sources=len(sources)):
                    lagging = lagging_condition(initial, sources)
                    self.assertEqual(lagging["conditions"][0]["candidate_state"], state)
                    self.assertNotEqual(
                        lagging["conditions"][0]["currentness"], "current"
                    )
                    _assert_contract_code(
                        self,
                        "candidate_pair_unconfirmed",
                        lambda lagging=lagging: self.crosscheck(
                            current_item, lagging, [pair("proposed")]
                        ),
                    )

    def test_identification_metric_uses_confirmed_active_features_in_item_and_condition(
        self,
    ):
        def scenario(snapshot, covered):
            item_result = _materialize_item(
                item_request(
                    feature_snapshot=snapshot,
                    candidates=[
                        item_candidate(
                            "covers",
                            feature_refs=covered,
                            evidence_refs=[_feature_ref_for(snapshot)],
                        )
                    ]
                    if covered
                    else [],
                )
            )
            condition_artifact = _materialize_condition(
                condition_request(feature_snapshot=snapshot, candidates=[])
            )["candidate"]
            crosscheck = self.crosscheck(item_result["candidate"], condition_artifact)
            item_metric = item_result["item_candidate_coverage"]
            # One shared rule: item and condition report the identical metric.
            self.assertEqual(
                item_metric, crosscheck["candidate_identification_coverage"]
            )
            return item_metric

        impl = {"id": "FEAT-001", "status": "implemented"}
        planned = {"id": "FEAT-002", "status": "planned"}

        measured = scenario(feature_inventory(features=[impl, planned]), ["FEAT-001"])
        self.assertEqual(measured["status"], "measured")
        self.assertEqual(
            (measured["numerator"], measured["denominator"], measured["rate"]),
            (1, 2, 0.5),
        )

        # A retired feature is outside the population, not an unrepresented gap.
        retired = scenario(
            feature_inventory(features=[impl, {"id": "FEAT-002", "status": "retired"}]),
            ["FEAT-001"],
        )
        self.assertEqual(
            (retired["status"], retired["numerator"], retired["denominator"]),
            ("measured", 1, 1),
        )

        # An unknown-status feature is not confirmed active: even when an item
        # represents it, it is in neither numerator nor denominator, and the metric
        # is not presented as measured or 100%.
        unknown = scenario(
            feature_inventory(features=[impl, {"id": "FEAT-002", "status": "unknown"}]),
            ["FEAT-001", "FEAT-002"],
        )
        self.assertEqual(unknown["status"], "not_measurable_unknown_feature_status")
        self.assertEqual(
            (unknown["numerator"], unknown["denominator"], unknown["rate"]),
            (None, None, None),
        )
        self.assertFalse(unknown["zero_denominator"])
        only_unknown = scenario(
            feature_inventory(features=[{"id": "FEAT-001", "status": "unknown"}]),
            ["FEAT-001"],
        )
        self.assertEqual(
            only_unknown["status"], "not_measurable_unknown_feature_status"
        )
        self.assertIsNone(only_unknown["numerator"])
        self.assertTrue(only_unknown["zero_denominator"])

        partial = scenario(
            unresolved_feature_inventory(unknown_areas=["payments"]), ["FEAT-001"]
        )
        self.assertEqual(partial["status"], "not_measurable_incomplete_population")
        self.assertEqual(
            (partial["numerator"], partial["denominator"], partial["rate"]),
            (None, None, None),
        )

        empty = scenario(feature_inventory(features=[]), [])
        self.assertEqual(empty["status"], "not_measurable_zero_denominator")
        self.assertEqual(
            (empty["numerator"], empty["denominator"], empty["rate"]),
            (None, None, None),
        )
        self.assertTrue(empty["zero_denominator"])

    def test_b_snapshot_and_analysis_are_separate_and_bound(self):
        source = feature_inventory()
        candidate = _materialize_item(
            item_request(feature_snapshot=source, candidates=[])
        )["candidate"]
        context = candidate["feature_inventory_context"]
        self.assertEqual(context["project_ref"], source["snapshot"]["project_ref"])
        self.assertEqual(context["artifact_ref"], source["snapshot"]["artifact_ref"])
        self.assertEqual(
            context["artifact_revision"], source["snapshot"]["artifact_revision"]
        )
        self.assertEqual(
            context["source_revision"], source["snapshot"]["source_revision"]
        )
        self.assertEqual(
            context["snapshot_sha256"], source["analysis"]["handoff"]["snapshot_sha256"]
        )
        self.assertEqual(
            context["source_inventory"],
            source["analysis"]["handoff"]["source_inventory"],
        )
        self.assertEqual(
            context["feature_ids"], source["analysis"]["handoff"]["feature_ids"]
        )

        partial = feature_inventory(status="incomplete")
        partial["snapshot"]["unknown_areas"] = ["product routes not enumerated"]
        partial["analysis"] = _feature_analysis(partial["snapshot"], "incomplete")
        partial_result = _materialize_item(
            item_request(feature_snapshot=partial, candidates=[])
        )
        self.assertEqual(partial_result["status"], "incomplete")
        self.assertFalse(partial_result["candidate"]["source_boundary_complete"])
        self.assertEqual(
            partial_result["candidate"]["feature_inventory_context"]["unknown_areas"],
            ["product routes not enumerated"],
        )

        mutations = [
            (
                "feature_snapshot_hash_mismatch",
                lambda value: value["analysis"]["handoff"].update(
                    snapshot_sha256="f" * 64
                ),
            ),
            (
                "feature_inventory_revision_mismatch",
                lambda value: value["analysis"]["handoff"].update(
                    source_revision="commit:other"
                ),
            ),
            (
                "feature_snapshot_hash_mismatch",
                lambda value: value["snapshot"].update(artifact_revision="feature-r2"),
            ),
            (
                "feature_inventory_revision_mismatch",
                lambda value: value["analysis"]["handoff"].update(
                    artifact_revision="feature-r2"
                ),
            ),
            (
                "feature_inventory_not_current",
                lambda value: value["analysis"].update(status="stale"),
            ),
            (
                "feature_inventory_contract_changed",
                lambda value: value["analysis"].update(unpublished_output=True),
            ),
            (
                "feature_inventory_handoff_mismatch",
                lambda value: value["analysis"]["handoff"].update(
                    feature_ids=["FEAT-999"]
                ),
            ),
            (
                "feature_inventory_analysis_mismatch",
                lambda value: value["analysis"]["metrics"].update(
                    source_boundary_complete=False
                ),
            ),
            (
                "feature_inventory_snapshot_incomplete",
                lambda value: value["snapshot"].pop("source_revision"),
            ),
            (
                "feature_inventory_analysis_mismatch",
                lambda value: value["snapshot"]["changes"][0].update(classification=[]),
            ),
            (
                "feature_inventory_analysis_mismatch",
                lambda value: (
                    value["snapshot"]["candidates"][0].update(
                        status="mapped", feature_id="FEAT-999"
                    )
                    or value["analysis"]["handoff"].update(
                        snapshot_sha256=fingerprint(value["snapshot"])
                    )
                ),
            ),
        ]
        for expected_code, mutate in mutations:
            with self.subTest(expected_code=expected_code, mutate=mutate):
                invalid = copy.deepcopy(source)
                mutate(invalid)
                _assert_contract_code(
                    self,
                    expected_code,
                    lambda invalid=invalid: run_items(
                        item_request(feature_snapshot=invalid, candidates=[])
                    ),
                )

    def test_item_owner_and_crosscheck_validators_match_semantically(self):
        valid = _materialize_item(
            item_request(candidates=[item_candidate("validator-parity")])
        )["candidate"]
        self.assertIsNotNone(validate_item_artifact(copy.deepcopy(valid)))
        self.assertIsNotNone(validate_crosscheck_item_artifact(copy.deepcopy(valid)))

        mutations = [
            lambda value: value["items"][0].update(kind="unsupported"),
            lambda value: value["items"][0].update(kind=[]),
            lambda value: value["items"][0].update(status="unsupported"),
            lambda value: value["items"][0].update(status=[]),
            lambda value: value["items"][0].pop("description"),
            lambda value: value["items"][0].update(parent_item_ids=["ITEM-999"]),
            lambda value: value["items"][0].update(parent_item_ids=["ITEM-001"]),
            lambda value: value["items"][0].update(feature_refs=["FEAT-999"]),
            lambda value: value["history"][0].update(action="unsupported"),
            lambda value: value["history"][0].update(action=[]),
            lambda value: value["items"][0].update(
                evidence_refs=[spec_ref(revision="spec-r9", content_hash="c" * 64)]
            ),
            lambda value: value["items"][0].update(name=""),
            lambda value: value["history"][0].update(
                reason="history altered after creation"
            ),
            lambda value: value.update(owner="test-condition-analysis"),
        ]
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                invalid = copy.deepcopy(valid)
                mutate(invalid)
                _refresh_artifact_fingerprint(invalid)
                owner_error = None
                crosscheck_error = None
                with self.assertRaises(ContractError) as owner_caught:
                    validate_item_artifact(copy.deepcopy(invalid))
                owner_error = owner_caught.exception.code
                with self.assertRaises(ContractError) as consumer_caught:
                    validate_crosscheck_item_artifact(copy.deepcopy(invalid))
                crosscheck_error = consumer_caught.exception.code
                self.assertEqual(owner_error, crosscheck_error)

        invalid = copy.deepcopy(valid)
        invalid["items"][0]["name"] = ""
        _refresh_artifact_fingerprint(invalid)
        condition = _materialize_condition(
            condition_request(candidates=[condition_candidate("validator-consumer")])
        )["candidate"]
        _assert_contract_code(
            self,
            "invalid_field",
            lambda: self.crosscheck(invalid, condition),
        )

    def test_history_ids_are_unique_idempotent_and_legacy_compatible(self):
        first_item = _materialize_item(
            item_request(candidates=[item_candidate("seed", reason="same reason")])
        )["candidate"]
        second_item = _materialize_item(
            item_request(
                candidates=[
                    item_candidate(
                        "revision-two",
                        action="reuse",
                        item_id="ITEM-001",
                        name="revision two",
                        reason="same reason",
                    )
                ],
                previous=first_item,
                expected="storage-r1",
                current="storage-r1",
            )
        )["candidate"]
        third_item = _materialize_item(
            item_request(
                candidates=[
                    item_candidate(
                        "revision-three",
                        action="reuse",
                        item_id="ITEM-001",
                        name="revision three",
                        reason="same reason",
                    )
                ],
                previous=second_item,
                expected="storage-r2",
                current="storage-r2",
            )
        )["candidate"]
        item_event_ids = [row["event_id"] for row in third_item["history"]]
        self.assertEqual(len(item_event_ids), len(set(item_event_ids)))
        self.assertNotEqual(item_event_ids[-2], item_event_ids[-1])
        item_replay = run_items(
            item_request(
                candidates=[
                    item_candidate(
                        "revision-three",
                        action="reuse",
                        item_id="ITEM-001",
                        name="revision three",
                        reason="same reason",
                    )
                ],
                previous=third_item,
                expected="storage-r3",
                current="storage-r3",
            )
        )
        self.assertEqual(item_replay["status"], "no_change")
        self.assertEqual(item_replay["candidate"]["history"], third_item["history"])

        first_condition = _materialize_condition(
            condition_request(
                candidates=[condition_candidate("seed", reason="same reason")]
            )
        )["candidate"]
        second_condition = _materialize_condition(
            condition_request(
                candidates=[
                    condition_candidate(
                        "revision-two",
                        action="reuse",
                        condition_id="COND-001",
                        name="revision two",
                        reason="same reason",
                    )
                ],
                previous=first_condition,
                expected="storage-r1",
                current="storage-r1",
            )
        )["candidate"]
        third_condition = _materialize_condition(
            condition_request(
                candidates=[
                    condition_candidate(
                        "revision-three",
                        action="reuse",
                        condition_id="COND-001",
                        name="revision three",
                        reason="same reason",
                    )
                ],
                previous=second_condition,
                expected="storage-r2",
                current="storage-r2",
            )
        )["candidate"]
        condition_event_ids = [row["event_id"] for row in third_condition["history"]]
        self.assertEqual(len(condition_event_ids), len(set(condition_event_ids)))
        self.assertNotEqual(condition_event_ids[-2], condition_event_ids[-1])
        condition_replay = run_conditions(
            condition_request(
                candidates=[
                    condition_candidate(
                        "revision-three",
                        action="reuse",
                        condition_id="COND-001",
                        name="revision three",
                        reason="same reason",
                    )
                ],
                previous=third_condition,
                expected="storage-r3",
                current="storage-r3",
            )
        )
        self.assertEqual(condition_replay["status"], "no_change")
        self.assertEqual(
            condition_replay["candidate"]["history"], third_condition["history"]
        )

        legacy_item = copy.deepcopy(first_item)
        for event in legacy_item["history"]:
            event["event_id"] = fingerprint(
                {key: value for key, value in event.items() if key != "event_id"}
            )
        _refresh_artifact_fingerprint(legacy_item)
        validate_item_artifact(legacy_item)
        migrated_item = _materialize_item(
            item_request(
                candidates=[
                    item_candidate(
                        "legacy-next",
                        action="reuse",
                        item_id="ITEM-001",
                        name="migrated without rewriting history",
                    )
                ],
                previous=legacy_item,
                expected="legacy-r1",
                current="legacy-r1",
            )
        )["candidate"]
        self.assertEqual(
            migrated_item["history"][0]["event_id"],
            legacy_item["history"][0]["event_id"],
        )
        self.assertNotEqual(
            migrated_item["history"][1]["event_id"],
            migrated_item["history"][0]["event_id"],
        )

        legacy_condition = copy.deepcopy(first_condition)
        for event in legacy_condition["history"]:
            event["event_id"] = fingerprint(
                {key: value for key, value in event.items() if key != "event_id"}
            )
        _refresh_artifact_fingerprint(legacy_condition)
        validate_crosscheck_item_artifact(legacy_item)
        validate_condition_artifact = run_conditions(
            {"operation": "validate", "artifact": legacy_condition}
        )
        self.assertTrue(validate_condition_artifact["valid"])
        migrated_condition = _materialize_condition(
            condition_request(
                candidates=[
                    condition_candidate(
                        "legacy-next",
                        action="reuse",
                        condition_id="COND-001",
                        name="migrated without rewriting history",
                    )
                ],
                previous=legacy_condition,
                expected="legacy-r1",
                current="legacy-r1",
            )
        )["candidate"]
        self.assertEqual(
            migrated_condition["history"][0]["event_id"],
            legacy_condition["history"][0]["event_id"],
        )

        altered = copy.deepcopy(third_item)
        altered["history"][0]["reason"] = (
            "altered with a recomputed artifact fingerprint"
        )
        _refresh_artifact_fingerprint(altered)
        _assert_contract_code(
            self,
            "history_event_integrity",
            lambda: validate_item_artifact(altered),
        )
        duplicate_item_event = copy.deepcopy(third_item)
        duplicate_item_event["history"][-1]["event_id"] = duplicate_item_event[
            "history"
        ][-2]["event_id"]
        _refresh_artifact_fingerprint(duplicate_item_event)
        _assert_contract_code(
            self,
            "item_history_invalid",
            lambda: validate_item_artifact(duplicate_item_event),
        )
        truncated = copy.deepcopy(third_condition)
        truncated["history"].pop(0)
        _refresh_artifact_fingerprint(truncated)
        _assert_contract_code(
            self,
            "history_event_integrity",
            lambda: run_conditions({"operation": "validate", "artifact": truncated}),
        )
        duplicate_condition_event = copy.deepcopy(third_condition)
        duplicate_condition_event["history"][-1]["event_id"] = (
            duplicate_condition_event["history"][-2]["event_id"]
        )
        _refresh_artifact_fingerprint(duplicate_condition_event)
        _assert_contract_code(
            self,
            "condition_history_invalid",
            lambda: run_conditions(
                {"operation": "validate", "artifact": duplicate_condition_event}
            ),
        )

    def test_current_sources_reject_competing_revisions_but_retain_history(self):
        snapshot = feature_inventory()
        source_rows = [_feature_ref_for(snapshot), spec_ref()]
        first = _materialize_item(
            item_request(candidates=[item_candidate("ordered")], sources=source_rows)
        )["candidate"]
        reversed_result = _materialize_item(
            item_request(
                candidates=[item_candidate("ordered")],
                sources=list(reversed(source_rows)),
            )
        )["candidate"]
        self.assertEqual(
            first["content_fingerprint"], reversed_result["content_fingerprint"]
        )

        for conflict, code in (
            ([source_rows[0], source_rows[1], source_rows[1]], "duplicate_source_ref"),
            (
                [
                    source_rows[0],
                    source_rows[1],
                    spec_ref(revision="spec-r2", content_hash="c" * 64),
                ],
                "conflicting_source_revision",
            ),
            (
                [
                    source_rows[0],
                    source_rows[1],
                    spec_ref(revision="spec-r1", content_hash="c" * 64),
                ],
                "conflicting_source_revision",
            ),
        ):
            _assert_contract_code(
                self,
                code,
                lambda conflict=conflict: run_items(
                    item_request(candidates=[], sources=conflict)
                ),
            )

        initial_item = _materialize_item(
            item_request(
                candidates=[
                    item_candidate(
                        "source-linked",
                        evidence_refs=[feature_ref(), spec_ref()],
                    )
                ]
            )
        )["candidate"]
        initial_condition = _materialize_condition(
            condition_request(candidates=[condition_candidate("source-linked")])
        )["candidate"]
        revisions = [
            spec_ref(revision="spec-r2", content_hash="c" * 64),
            spec_ref(revision="spec-r3", content_hash="d" * 64),
        ]
        item_previous = initial_item
        condition_previous = initial_condition
        for index, revision in enumerate(revisions, start=1):
            current_sources = [feature_ref(), revision]
            impact_item = run_items(
                {
                    "operation": "impact",
                    "artifact": item_previous,
                    "current_source_refs": current_sources,
                }
            )
            impact_condition = run_conditions(
                {
                    "operation": "impact",
                    "artifact": condition_previous,
                    "current_source_refs": current_sources,
                }
            )
            self.assertEqual(impact_item["impacted_item_ids"], ["ITEM-001"])
            self.assertEqual(impact_condition["impacted_condition_ids"], ["COND-001"])
            item_update = _materialize_item(
                item_request(
                    candidates=[],
                    sources=current_sources,
                    previous=item_previous,
                    expected=f"storage-r{index}",
                    current=f"storage-r{index}",
                )
            )
            condition_update = _materialize_condition(
                condition_request(
                    candidates=[],
                    sources=current_sources,
                    previous=condition_previous,
                    expected=f"storage-r{index}",
                    current=f"storage-r{index}",
                )
            )
            item_previous = item_update["candidate"]
            condition_previous = condition_update["candidate"]
            self.assertEqual(
                [row["action"] for row in item_previous["history"]].count(
                    "source_changed"
                ),
                index,
            )
            self.assertEqual(
                [row["action"] for row in condition_previous["history"]].count(
                    "source_changed"
                ),
                index,
            )
        self.assertEqual(
            sorted(
                ref["revision"]
                for ref in item_previous["source_refs"]
                if ref["owner"] == "spec-analysis"
            ),
            ["spec-r1", "spec-r2", "spec-r3"],
        )
        item_replay = run_items(
            item_request(
                candidates=[],
                sources=[feature_ref(), revisions[-1]],
                previous=item_previous,
                expected="storage-r2",
                current="storage-r2",
            )
        )
        condition_replay = run_conditions(
            condition_request(
                candidates=[],
                sources=[feature_ref(), revisions[-1]],
                previous=condition_previous,
                expected="storage-r2",
                current="storage-r2",
            )
        )
        self.assertEqual(item_replay["status"], "no_change")
        self.assertEqual(condition_replay["status"], "no_change")
        self.assertEqual(item_replay["analysis_status"], "incomplete")
        self.assertEqual(condition_replay["analysis_status"], "incomplete")
        self.assertEqual(item_replay["stale_item_ids"], ["ITEM-001"])
        self.assertEqual(condition_replay["stale_condition_ids"], ["COND-001"])
        self.assertIn("source_stale", {row["code"] for row in item_replay["issues"]})
        self.assertIn(
            "source_stale", {row["code"] for row in condition_replay["issues"]}
        )
        self.assertEqual(item_replay["recheck_item_ids"], ["ITEM-001"])
        self.assertEqual(condition_replay["recheck_condition_ids"], ["COND-001"])
        self.assertEqual(
            len(item_replay["candidate"]["history"]), len(item_previous["history"])
        )
        self.assertEqual(
            len(condition_replay["candidate"]["history"]),
            len(condition_previous["history"]),
        )

    def test_no_change_replay_preserves_unknown_currentness(self):
        snapshot = feature_inventory()
        current_feature_ref = _feature_ref_for(snapshot)
        initial_item = _materialize_item(
            item_request(
                candidates=[
                    item_candidate(
                        "unknown-after-source-omission",
                        evidence_refs=[current_feature_ref, spec_ref()],
                    )
                ],
                feature_snapshot=snapshot,
            )
        )["candidate"]
        initial_condition = _materialize_condition(
            condition_request(
                candidates=[condition_candidate("unknown-after-source-omission")],
                feature_snapshot=snapshot,
            )
        )["candidate"]
        available_sources = [current_feature_ref]
        item_unknown = _materialize_item(
            item_request(
                candidates=[],
                feature_snapshot=snapshot,
                sources=available_sources,
                previous=initial_item,
                expected="provider-r1",
                current="provider-r1",
            )
        )
        condition_unknown = _materialize_condition(
            condition_request(
                candidates=[],
                feature_snapshot=snapshot,
                sources=available_sources,
                previous=initial_condition,
                expected="provider-r1",
                current="provider-r1",
            )
        )
        self.assertEqual(item_unknown["unknown_item_ids"], ["ITEM-001"])
        self.assertEqual(condition_unknown["unknown_condition_ids"], ["COND-001"])

        item_replay = run_items(
            item_request(
                candidates=[],
                feature_snapshot=snapshot,
                sources=available_sources,
                previous=item_unknown["candidate"],
                expected="provider-r2",
                current="provider-r2",
            )
        )
        condition_replay = run_conditions(
            condition_request(
                candidates=[],
                feature_snapshot=snapshot,
                sources=available_sources,
                previous=condition_unknown["candidate"],
                expected="provider-r2",
                current="provider-r2",
            )
        )
        self.assertEqual(item_replay["status"], "no_change")
        self.assertEqual(condition_replay["status"], "no_change")
        self.assertEqual(item_replay["analysis_status"], "incomplete")
        self.assertEqual(condition_replay["analysis_status"], "incomplete")
        self.assertEqual(item_replay["issues"], item_unknown["issues"])
        self.assertEqual(condition_replay["issues"], condition_unknown["issues"])
        self.assertEqual(item_replay["unknown_item_ids"], ["ITEM-001"])
        self.assertEqual(condition_replay["unknown_condition_ids"], ["COND-001"])
        self.assertEqual(item_replay["recheck_item_ids"], ["ITEM-001"])
        self.assertEqual(condition_replay["recheck_condition_ids"], ["COND-001"])
        self.assertEqual(item_replay["candidate"], item_unknown["candidate"])
        self.assertEqual(condition_replay["candidate"], condition_unknown["candidate"])

    def test_unfound_item_references_are_unconfirmed_and_can_resolve_later(self):
        empty_items = _materialize_item(item_request(candidates=[]))["candidate"]
        condition = _materialize_condition(
            condition_request(
                candidates=[condition_candidate("await-item", item_refs=["ITEM-001"])]
            )
        )["candidate"]
        unresolved = self.crosscheck(empty_items, condition)
        unresolved_replay = self.crosscheck(empty_items, condition)
        self.assertEqual(unresolved_replay, unresolved)
        self.assertEqual(unresolved["status"], "incomplete")
        self.assertEqual(
            unresolved["unresolved_item_references"][0]["reason"], "item_not_found"
        )
        self.assertEqual(
            unresolved["unresolved_item_references"][0]["state"], "unconfirmed"
        )
        self.assertEqual(unresolved["recheck_item_ids"], ["ITEM-001"])
        self.assertEqual(unresolved["recheck_condition_ids"], ["COND-001"])
        self.assertEqual(condition["conditions"][0]["condition_id"], "COND-001")
        self.assertEqual(empty_items["items"], [])

        registered = _materialize_item(
            item_request(candidates=[item_candidate("arrived")])
        )["candidate"]
        resolved = self.crosscheck(registered, condition)
        self.assertEqual(resolved["unresolved_item_references"], [])
        self.assertEqual(resolved["status"], "candidate_crosscheck_complete")
        self.assertEqual(condition["conditions"][0]["condition_id"], "COND-001")

        malformed = condition_request(
            candidates=[condition_candidate("malformed", item_refs=["bad-id"])]
        )
        _assert_contract_code(
            self,
            "candidate_item_ref_invalid",
            lambda: run_conditions(malformed),
        )

        unknown_item = _materialize_item(
            item_request(candidates=[item_candidate("unknown", status="unknown")])
        )["candidate"]
        unknown_condition = _materialize_condition(
            condition_request(
                candidates=[condition_candidate("unknown-item", item_refs=["ITEM-001"])]
            )
        )["candidate"]
        unknown_result = self.crosscheck(unknown_item, unknown_condition)
        self.assertEqual(
            unknown_result["unresolved_item_references"][0]["reason"],
            "item_unconfirmed",
        )
        self.assertEqual(unknown_result["status"], "incomplete")

        active_item = _materialize_item(
            item_request(candidates=[item_candidate("to-retire")])
        )["candidate"]
        retired_item = _materialize_item(
            item_request(
                candidates=[],
                previous=active_item,
                expected="storage-r1",
                current="storage-r1",
                retirements=[
                    {
                        "item_id": "ITEM-001",
                        "reason": "owner evidence confirms removal",
                        "evidence_refs": [feature_ref()],
                    }
                ],
            )
        )["candidate"]
        retired_condition = _materialize_condition(
            condition_request(
                candidates=[condition_candidate("retired-ref", item_refs=["ITEM-001"])]
            )
        )["candidate"]
        retired_result = self.crosscheck(retired_item, retired_condition)
        self.assertEqual(retired_result["retired_item_ids"], ["ITEM-001"])
        self.assertEqual(retired_result["items_without_pair_proposal"], [])
        self.assertEqual(
            retired_result["unresolved_item_references"][0]["reason"], "item_retired"
        )

    def test_crosscheck_gates_stale_retired_blocked_and_inconsistent_pairs(self):
        initial_item = _materialize_item(
            item_request(
                candidates=[
                    item_candidate(
                        "current-item",
                        evidence_refs=[feature_ref(), spec_ref()],
                    )
                ]
            )
        )["candidate"]
        initial_condition = _materialize_condition(
            condition_request(candidates=[condition_candidate("stale-condition")])
        )["candidate"]
        changed_spec = spec_ref(revision="spec-r2", content_hash="c" * 64)
        changed_sources = [feature_ref(), changed_spec]
        current_item = _materialize_item(
            item_request(
                candidates=[
                    item_candidate(
                        "current-item",
                        action="reuse",
                        item_id="ITEM-001",
                        evidence_refs=[feature_ref(), changed_spec],
                    )
                ],
                sources=changed_sources,
                previous=initial_item,
                expected="storage-r1",
                current="storage-r1",
            )
        )["candidate"]
        stale_condition = _materialize_condition(
            condition_request(
                candidates=[],
                sources=changed_sources,
                previous=initial_condition,
                expected="storage-r1",
                current="storage-r1",
            )
        )["candidate"]
        stale_result = self.crosscheck(current_item, stale_condition)
        self.assertEqual(stale_result["status"], "incomplete")
        self.assertEqual(stale_result["stale_condition_ids"], ["COND-001"])
        self.assertEqual(stale_result["candidate_pairs"], [])
        self.assertEqual(stale_result["candidate_identification_coverage"]["rate"], 0.5)
        self.assertEqual(
            stale_result["candidate_identification_coverage"]["status"], "measured"
        )

        item_artifact = _materialize_item(
            item_request(candidates=[item_candidate("kind-conflict", kind="api")])
        )["candidate"]
        condition_artifact = _materialize_condition(
            condition_request(
                candidates=[
                    condition_candidate(
                        "kind-conflict",
                        item_kinds=["ui"],
                        feature_refs=["FEAT-001"],
                    )
                ]
            )
        )["candidate"]
        pair = {
            "item_id": "ITEM-001",
            "condition_id": "COND-001",
            "status": "proposed",
            "rationale": "explicit pair with a kind contradiction",
            "evidence_refs": [spec_ref()],
        }
        conflict = self.crosscheck(item_artifact, condition_artifact, [pair])
        self.assertEqual(conflict["status"], "incomplete")
        self.assertEqual(conflict["candidate_pairs"][0]["status"], "unconfirmed")
        self.assertIn(
            "item_kind_not_in_condition_applicability",
            conflict["candidate_pair_inconsistencies"][0]["codes"],
        )
        self.assertFalse(conflict["cartesian_product_generated"])
        _assert_contract_code(
            self,
            "candidate_pair_duplicate",
            lambda: self.crosscheck(item_artifact, condition_artifact, [pair, pair]),
        )

        disjoint_condition = _materialize_condition(
            condition_request(
                candidates=[
                    condition_candidate(
                        "feature-conflict",
                        item_kinds=["api"],
                        feature_refs=["FEAT-002"],
                    )
                ]
            )
        )["candidate"]
        disjoint = self.crosscheck(
            item_artifact,
            disjoint_condition,
            [
                {
                    **pair,
                    "condition_id": "COND-001",
                    "rationale": "disjoint feature refs",
                }
            ],
        )
        self.assertIn(
            "item_and_condition_feature_refs_disjoint",
            disjoint["candidate_pair_inconsistencies"][0]["codes"],
        )

        reusable_items = _materialize_item(
            item_request(
                candidates=[
                    item_candidate("first", feature_refs=["FEAT-001"]),
                    item_candidate("second", feature_refs=["FEAT-002"]),
                ]
            )
        )["candidate"]
        reusable_condition = _materialize_condition(
            condition_request(
                candidates=[
                    condition_candidate(
                        "shared",
                        item_kinds=["api"],
                        feature_refs=["FEAT-001", "FEAT-002"],
                        item_refs=["ITEM-001", "ITEM-002"],
                    )
                ]
            )
        )["candidate"]
        reused = self.crosscheck(
            reusable_items,
            reusable_condition,
            [
                {**pair, "item_id": "ITEM-001", "rationale": "first item"},
                {**pair, "item_id": "ITEM-002", "rationale": "second item"},
            ],
        )
        self.assertEqual(reused["metrics"]["candidate_pair_count"], 2)
        self.assertEqual(
            {row["condition_id"] for row in reused["candidate_pairs"]}, {"COND-001"}
        )

        blocked_condition = _materialize_condition(
            condition_request(
                candidates=[
                    condition_candidate(
                        "blocked-without-pair",
                        authorities=[],
                        state="blocked",
                        unknowns=["Authority unavailable"],
                    )
                ]
            )
        )["candidate"]
        blocked = self.crosscheck(
            _materialize_item(item_request(candidates=[]))["candidate"],
            blocked_condition,
        )
        self.assertEqual(blocked["status"], "incomplete")
        self.assertEqual(blocked["blocked_condition_ids"], ["COND-001"])

        base_condition = _materialize_condition(
            condition_request(candidates=[condition_candidate("retire-condition")])
        )["candidate"]
        retired_condition = _materialize_condition(
            condition_request(
                candidates=[],
                previous=base_condition,
                expected="storage-r1",
                current="storage-r1",
                retirements=[
                    {
                        "condition_id": "COND-001",
                        "reason": "condition scope ended",
                        "evidence_refs": [spec_ref()],
                    }
                ],
            )
        )["candidate"]
        retired = self.crosscheck(
            _materialize_item(item_request(candidates=[]))["candidate"],
            retired_condition,
        )
        self.assertEqual(retired["retired_condition_ids"], ["COND-001"])
        self.assertEqual(retired["conditions_without_pair_proposal"], [])
        self.assertEqual(retired["metrics"]["condition_candidate_count"], 0)

    def test_write_precondition_matches_current_a_operation_claim(self):
        result = _materialize_item(item_request(candidates=[item_candidate("claim")]))
        precondition = result["write_precondition"]
        claim = precondition["operation_claim_details"]
        self.assertEqual(_validate_claim_details(claim), claim)
        self.assertFalse(precondition["performed"])
        self.assertFalse(precondition["provider_selected"])
        self.assertEqual(
            precondition["approval_state"], "not_resolved_by_candidate_helper"
        )
        self.assertTrue(precondition["requires_provider_native_cas"])
        self.assertTrue(precondition["requires_independent_readback"])
        self.assertNotEqual(
            result["candidate"]["content_fingerprint"],
            result["candidate"]["feature_inventory_context"]["artifact_revision"],
        )

    def test_legacy_v1_artifacts_read_without_rewriting_history(self):
        item = _materialize_item(
            item_request(candidates=[item_candidate("legacy-item")])
        )["candidate"]
        condition = _materialize_condition(
            condition_request(candidates=[condition_candidate("legacy-condition")])
        )["candidate"]
        legacy_item = copy.deepcopy(item)
        legacy_condition = copy.deepcopy(condition)
        legacy_item.pop("feature_inventory_context")
        legacy_condition.pop("feature_inventory_context")
        _refresh_artifact_fingerprint(legacy_item)
        _refresh_artifact_fingerprint(legacy_condition)
        item_history = copy.deepcopy(legacy_item["history"])
        condition_history = copy.deepcopy(legacy_condition["history"])
        self.assertIsNotNone(validate_item_artifact(legacy_item))
        self.assertIsNotNone(validate_crosscheck_item_artifact(legacy_item))
        self.assertTrue(
            run_conditions({"operation": "validate", "artifact": legacy_condition})[
                "valid"
            ]
        )

        legacy_crosscheck = self.crosscheck(legacy_item, legacy_condition)
        self.assertEqual(legacy_crosscheck["status"], "incomplete")
        self.assertTrue(
            any(
                issue["code"] == "source_population_incomplete"
                for issue in legacy_crosscheck["issues"]
            )
        )

        migrated_item = _materialize_item(
            item_request(
                candidates=[],
                previous=legacy_item,
                expected="provider-r1",
                current="provider-r1",
            )
        )["candidate"]
        migrated_condition = _materialize_condition(
            condition_request(
                candidates=[],
                previous=legacy_condition,
                expected="provider-r1",
                current="provider-r1",
            )
        )["candidate"]
        self.assertEqual(migrated_item["history"], item_history)
        self.assertEqual(migrated_condition["history"], condition_history)
        self.assertEqual(migrated_item["id_history"], legacy_item["id_history"])
        self.assertEqual(
            migrated_condition["id_history"], legacy_condition["id_history"]
        )
        self.assertIn("feature_inventory_context", migrated_item)
        self.assertIn("feature_inventory_context", migrated_condition)


if __name__ == "__main__":
    unittest.main()
