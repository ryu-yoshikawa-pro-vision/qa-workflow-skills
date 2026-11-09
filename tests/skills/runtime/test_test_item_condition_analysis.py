from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
ITEM_SCRIPTS = ROOT / "skills" / "test-item-analysis" / "scripts"
CONDITION_SCRIPTS = ROOT / "skills" / "test-condition-analysis" / "scripts"
sys.path.insert(0, str(ITEM_SCRIPTS))
sys.path.insert(0, str(CONDITION_SCRIPTS))

from candidate_support import ContractError  # noqa: E402
from condition_candidates import run as run_conditions  # noqa: E402
from item_candidates import run as run_items  # noqa: E402


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def feature_inventory(*, features=None, status="complete", source_status="complete"):
    return {
        "schema_version": "feature-inventory-v1",
        "project_ref": "project:shop",
        "artifact_ref": "feature-inventory:shop",
        "artifact_revision": "feature-r1",
        "source_revision": "commit:abc123",
        "previous_artifact_revision": None,
        "operation_id": "fixture:feature-1",
        "event": "initial",
        "status": status,
        "sources": [
            {
                "id": "SRC-001",
                "status": source_status,
                "revision": "source-r1",
                "evidence_ref": "source:evidence-1"
                if source_status == "complete"
                else None,
            }
        ],
        "expected_source_ids": ["SRC-001"],
        "features": features
        if features is not None
        else [
            {"id": "FEAT-001", "status": "implemented"},
            {"id": "FEAT-002", "status": "planned"},
        ],
        "unknown_areas": [],
        "handoff": {"snapshot_sha256": "a" * 64},
    }


def feature_ref(revision="feature-r1", content_hash="a" * 64):
    return {
        "owner": "feature-analysis",
        "scope": "project:shop",
        "artifact_ref": "feature-inventory:shop",
        "revision": revision,
        "content_hash": content_hash,
    }


def _feature_ref_for(snapshot):
    return feature_ref(
        revision=snapshot["artifact_revision"],
        content_hash=snapshot["handoff"]["snapshot_sha256"],
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

    def test_readback_checks_hash_and_does_not_claim_authenticity(self):
        candidate = _materialize_item(
            item_request(candidates=[item_candidate("item")])
        )["candidate"]
        readback = {
            "owner": "test-item-analysis",
            "scope": "project:shop",
            "artifact_ref": "item-candidates:shop",
            "revision": "provider-r1",
            "content_hash": candidate["content_fingerprint"],
        }
        good = run_items(
            {
                "operation": "validate_readback",
                "candidate_artifact": candidate,
                "readback": readback,
            }
        )
        self.assertTrue(good["valid"])
        self.assertEqual(
            good["provider_authenticity"], "not_established_by_this_validator"
        )
        readback["content_hash"] = "0" * 64
        self.assertEqual(
            run_items(
                {
                    "operation": "validate_readback",
                    "candidate_artifact": candidate,
                    "readback": readback,
                }
            )["issues"][0]["code"],
            "readback_hash_mismatch",
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
                    condition_candidate("one", feature_refs=["FEAT-001"]),
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
        changed_feature["artifact_revision"] = "feature-r2"
        changed_feature["handoff"]["snapshot_sha256"] = "c" * 64
        stale_condition = _materialize_condition(
            condition_request(
                feature_snapshot=changed_feature,
                candidates=[
                    condition_candidate(
                        "one",
                        feature_refs=["FEAT-001"],
                        evidence_refs=[feature_ref("feature-r2", "c" * 64), spec_ref()],
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

    def test_provider_readback_is_structural_not_authenticated(self):
        candidate = _materialize_condition(
            condition_request(candidates=[condition_candidate("one")])
        )["candidate"]
        readback = {
            "owner": "test-condition-analysis",
            "scope": "project:shop",
            "artifact_ref": "condition-candidates:shop",
            "revision": "provider-r1",
            "content_hash": candidate["content_fingerprint"],
        }
        result = run_conditions(
            {
                "operation": "validate_readback",
                "candidate_artifact": candidate,
                "readback": readback,
            }
        )
        self.assertTrue(result["valid"])
        self.assertEqual(result["provider_cas"], "not_established_by_this_validator")

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


if __name__ == "__main__":
    unittest.main()
