from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(
    0,
    str(
        Path(__file__).resolve().parents[3] / "skills" / "feature-analysis" / "scripts"
    ),
)
from feature_registry import handle  # noqa: E402


def fixture() -> dict:
    snapshot = {
        "schema_version": "feature-inventory-v1",
        "project_ref": "PROJECT-1",
        "artifact_ref": "feature-artifact",
        "artifact_revision": "art-v1",
        "previous_artifact_revision": None,
        "source_revision": "head-v1",
        "operation_id": "op-v1",
        "event": "initial",
        "expected_source_ids": ["SRC-001"],
        "sources": [
            {
                "id": "SRC-001",
                "kind": "code",
                "ref": "product/repo",
                "scope": "src",
                "status": "complete",
                "revision": "head-v1",
                "evidence_ref": "evidence/sources",
                "enumeration_complete": True,
                "unretrieved": [],
            }
        ],
        "features": [
            {
                "id": "FEAT-001",
                "identity": "checkout authorization",
                "name": "Purchase access control",
                "kind": "authorization",
                "status": "implemented",
                "parent_id": None,
                "source_ids": ["SRC-001"],
                "implementation_refs": ["src/auth.py"],
                "spec_refs": [],
                "qa_refs": [],
            }
        ],
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
                "before_revision": "head-old",
                "after_revision": "head-v1",
                "locator": "src/auth.py",
                "evidence_ref": "evidence/diff",
                "classification": "impact",
                "feature_ids": ["FEAT-001"],
                "reason": "Authorization behavior changed",
            }
        ],
        "history": [
            {
                "event_id": "event-1",
                "kind": "added",
                "revision": "head-v1",
                "evidence_ref": "evidence/created",
                "from_ids": [],
                "to_ids": ["FEAT-001"],
            }
        ],
        "unknown_areas": [],
    }
    return {
        "snapshot": snapshot,
        "previous_snapshot": None,
        "observed_head_revision": "head-v1",
    }


class FeatureRegistryTests(unittest.TestCase):
    def test_complete_local_inventory_has_no_full_product_guarantee(self) -> None:
        result = handle(fixture())
        self.assertEqual(result["status"], "complete", result)
        self.assertEqual(result["metrics"]["change_classification"]["rate"], 1.0)
        self.assertIsNone(result["metrics"]["all_product_features_discovered"])

    def test_old_head_is_stale_without_mutation(self) -> None:
        data = fixture()
        data["observed_head_revision"] = "head-v2"
        self.assertEqual(handle(data)["status"], "stale")

    def test_partial_source_is_not_empty_complete(self) -> None:
        data = fixture()
        data["snapshot"]["sources"][0].update(
            status="denied", reason="403", enumeration_complete=False
        )
        self.assertEqual(handle(data)["status"], "incomplete")

    def test_missing_expected_source_is_not_zero(self) -> None:
        data = fixture()
        data["snapshot"]["expected_source_ids"].append("SRC-002")
        self.assertIn("source_missing:SRC-002", handle(data)["reasons"])

    def test_unclassified_and_unknown_remain_visible(self) -> None:
        data = fixture()
        data["snapshot"]["changes"][0]["classification"] = "unclassified"
        data["snapshot"]["unknown_areas"] = ["unreadable batch"]
        result = handle(data)
        self.assertEqual(result["status"], "incomplete")
        self.assertEqual(result["metrics"]["change_classification"]["rate"], 0.0)
        self.assertEqual(result["handoff"]["unclassified_change_ids"], ["DIF-001"])

    def test_unknown_areas_invalidate_source_boundary(self) -> None:
        data = fixture()
        data["snapshot"]["unknown_areas"] = ["unexamined batch scheduler"]
        result = handle(data)
        self.assertEqual(result["status"], "incomplete")
        self.assertFalse(result["metrics"]["source_boundary_complete"])

    def test_zero_denominators_are_unknown(self) -> None:
        data = fixture()
        data["snapshot"]["changes"] = []
        data["snapshot"]["candidates"] = []
        result = handle(data)
        self.assertEqual(result["status"], "incomplete")
        self.assertIsNone(result["metrics"]["change_classification"]["rate"])
        self.assertIsNone(result["metrics"]["observed_candidate_mapping"]["rate"])

    def test_exclusion_is_reported_but_not_counted_as_mapped(self) -> None:
        data = fixture()
        candidate = data["snapshot"]["candidates"][0]
        candidate["status"] = "excluded"
        candidate["feature_id"] = None
        candidate["reason"] = "Approved out of scope"
        candidate["approval_ref"] = "approval/1"
        metrics = handle(data)["metrics"]
        self.assertEqual(metrics["observed_candidate_mapping"]["rate"], 0.0)
        self.assertEqual(metrics["excluded_candidate_ids"], ["CAND-001"])

    def test_path_change_preserves_semantic_feature_id(self) -> None:
        first = fixture()
        next_step = copy.deepcopy(first)
        next_step["previous_snapshot"] = copy.deepcopy(first["snapshot"])
        next_step["snapshot"]["previous_artifact_revision"] = "art-v1"
        next_step["snapshot"]["artifact_revision"] = "art-v2"
        next_step["snapshot"]["operation_id"] = "op-v2"
        next_step["snapshot"]["features"][0]["implementation_refs"] = [
            "src/new-auth.py"
        ]
        next_step["snapshot"]["history"].append(
            {
                "event_id": "changed-implementation",
                "kind": "changed",
                "revision": "head-v1",
                "evidence_ref": "evidence/path-change",
                "from_ids": ["FEAT-001"],
                "to_ids": ["FEAT-001"],
            }
        )
        self.assertEqual(handle(next_step)["status"], "complete")

    def test_feature_edit_requires_matching_history_event(self) -> None:
        data = fixture()
        data["previous_snapshot"] = copy.deepcopy(data["snapshot"])
        data["snapshot"]["artifact_revision"] = "art-v2"
        data["snapshot"]["previous_artifact_revision"] = "art-v1"
        data["snapshot"]["operation_id"] = "op-v2"
        data["snapshot"]["features"][0]["name"] = "Checkout access rules"
        result = handle(data)
        self.assertEqual(result["status"], "blocked", result)
        data["snapshot"]["history"].append(
            {
                "event_id": "renamed-feature",
                "kind": "renamed",
                "revision": "head-v1",
                "evidence_ref": "evidence/rename",
                "from_ids": ["FEAT-001"],
                "to_ids": ["FEAT-001"],
            }
        )
        self.assertEqual(handle(data)["status"], "complete")

    def test_no_impact_needs_approval_ref(self) -> None:
        data = fixture()
        data["snapshot"]["changes"][0].update(
            classification="no_impact", feature_ids=[], reason="format-only"
        )
        self.assertEqual(handle(data)["status"], "blocked")
        data["snapshot"]["changes"][0]["approval_ref"] = "approval/format"
        self.assertEqual(handle(data)["status"], "complete")

    def test_reuse_of_id_with_new_semantics_is_blocked(self) -> None:
        data = fixture()
        data["previous_snapshot"] = copy.deepcopy(data["snapshot"])
        data["snapshot"]["previous_artifact_revision"] = "art-v1"
        data["snapshot"]["operation_id"] = "op-v2"
        data["snapshot"]["features"][0]["identity"] = "unrelated feature"
        self.assertEqual(handle(data)["status"], "blocked")

    def test_split_requires_retirement_history(self) -> None:
        data = fixture()
        data["previous_snapshot"] = copy.deepcopy(data["snapshot"])
        data["snapshot"]["previous_artifact_revision"] = "art-v1"
        data["snapshot"]["operation_id"] = "op-v2"
        data["snapshot"]["artifact_revision"] = "art-v2"
        data["snapshot"]["features"][0]["status"] = "retired"
        self.assertEqual(handle(data)["status"], "blocked")
        data["snapshot"]["history"].append(
            {
                "event_id": "split-2",
                "kind": "retired",
                "revision": "head-v1",
                "evidence_ref": "evidence/retirement",
                "from_ids": ["FEAT-001"],
                "to_ids": [],
            }
        )
        self.assertEqual(handle(data)["status"], "complete")

    def test_parent_cycle_is_blocked(self) -> None:
        data = fixture()
        data["snapshot"]["features"][0]["parent_id"] = "FEAT-001"
        self.assertEqual(handle(data)["status"], "blocked")

    def test_bad_source_claim_does_not_count_as_complete(self) -> None:
        data = fixture()
        data["snapshot"]["sources"][0]["unretrieved"] = ["src/unreadable.py"]
        self.assertEqual(handle(data)["status"], "blocked")

    def test_source_candidate_and_change_ids_cannot_be_reused(self) -> None:
        changes = (
            ("sources", "ref", "different/repo"),
            ("candidates", "evidence_ref", "unrelated-candidate"),
            ("changes", "locator", "unrelated.py"),
        )
        for collection, key, replacement in changes:
            with self.subTest(collection=collection):
                data = fixture()
                data["previous_snapshot"] = copy.deepcopy(data["snapshot"])
                data["snapshot"]["previous_artifact_revision"] = "art-v1"
                data["snapshot"]["artifact_revision"] = "art-v2"
                data["snapshot"]["operation_id"] = "op-v2"
                data["snapshot"][collection][0][key] = replacement
                self.assertEqual(handle(data)["status"], "blocked")

    def test_duplicate_operation_does_not_rerun(self) -> None:
        data = fixture()
        data["previous_snapshot"] = copy.deepcopy(data["snapshot"])
        self.assertEqual(handle(data)["status"], "idempotent")
        data["snapshot"]["features"][0]["name"] = "Different"
        self.assertEqual(handle(data)["status"], "blocked")

    def test_duplicate_operation_does_not_bypass_schema_or_history(self) -> None:
        data = fixture()
        data["snapshot"]["features"][0]["source_ids"] = ["SRC-404"]
        data["previous_snapshot"] = copy.deepcopy(data["snapshot"])
        self.assertEqual(handle(data)["status"], "blocked")

        data = fixture()
        data["snapshot"]["history"][0]["from_ids"] = ["FEAT-999"]
        data["previous_snapshot"] = copy.deepcopy(data["snapshot"])
        self.assertEqual(handle(data)["status"], "blocked")

    def test_out_of_scope_requires_approval_reference(self) -> None:
        data = fixture()
        change = data["snapshot"]["changes"][0]
        change["classification"] = "out_of_scope"
        self.assertEqual(handle(data)["status"], "blocked")

    def test_changed_snapshot_requires_distinct_artifact_revision(self) -> None:
        data = fixture()
        data["previous_snapshot"] = copy.deepcopy(data["snapshot"])
        data["snapshot"]["previous_artifact_revision"] = "art-v1"
        data["snapshot"]["operation_id"] = "op-v2"
        self.assertEqual(handle(data)["status"], "blocked")
        data["snapshot"]["artifact_revision"] = "art-v2"
        self.assertEqual(handle(data)["status"], "complete")

    def test_split_merge_history_requires_real_lineage(self) -> None:
        for kind, from_ids, to_ids in (
            ("split", ["FEAT-001"], ["FEAT-001"]),
            ("merged", ["FEAT-001"], ["FEAT-001"]),
        ):
            with self.subTest(kind=kind):
                data = fixture()
                data["snapshot"]["history"].append(
                    {
                        "event_id": "bad-lineage",
                        "kind": kind,
                        "revision": "head-v1",
                        "evidence_ref": "evidence/lineage",
                        "from_ids": from_ids,
                        "to_ids": to_ids,
                    }
                )
                self.assertEqual(handle(data)["status"], "blocked")

    def test_code_events_require_full_revisions_and_previous_head(self) -> None:
        old_sha = "b" * 40
        new_sha = "a" * 40
        for event, basis in (
            (
                "pr_update",
                {
                    "base_sha": "c" * 40,
                    "head_sha": new_sha,
                    "previous_head_sha": old_sha,
                },
            ),
            (
                "rebase",
                {
                    "base_sha": "c" * 40,
                    "head_sha": new_sha,
                    "previous_head_sha": old_sha,
                    "previous_base_sha": "d" * 40,
                },
            ),
            (
                "merge",
                {
                    "merge_commit_sha": new_sha,
                    "target_ref": "refs/heads/main",
                    "previous_head_sha": old_sha,
                },
            ),
            (
                "release",
                {
                    "commit_sha": new_sha,
                    "build_ref": "release/2",
                    "target_ref": "refs/tags/v2",
                },
            ),
        ):
            with self.subTest(event=event):
                data = fixture()
                before = copy.deepcopy(data["snapshot"])
                before["source_revision"] = old_sha
                before["sources"][0]["revision"] = old_sha
                data["previous_snapshot"] = before
                snap = data["snapshot"]
                snap["event"] = event
                snap["event_basis"] = basis
                snap["source_revision"] = new_sha
                snap["sources"][0]["revision"] = new_sha
                snap["artifact_revision"] = "art-v2"
                snap["previous_artifact_revision"] = "art-v1"
                snap["operation_id"] = "op-v2"
                snap["changes"][0].update(
                    id="DIF-002", before_revision=old_sha, after_revision=new_sha
                )
                data["observed_head_revision"] = new_sha
                self.assertEqual(handle(data)["status"], "complete", data)
                del snap["event_basis"]
                self.assertEqual(handle(data)["status"], "blocked")

    def test_document_only_revision_has_independent_source_basis(self) -> None:
        data = fixture()
        before = copy.deepcopy(data["snapshot"])
        before["source_revision"] = "event-v1"
        before["sources"][0].update(
            kind="spec", ref="requirements/doc", revision="doc-v1"
        )
        data["previous_snapshot"] = before
        snap = data["snapshot"]
        snap["source_revision"] = "event-v2"
        snap["sources"][0].update(
            kind="spec", ref="requirements/doc", revision="doc-v2"
        )
        snap["event"] = "external_revision"
        snap["event_basis"] = {
            "document_ref": "requirements/doc",
            "before_revision": "doc-v1",
            "after_revision": "doc-v2",
            "evidence_ref": "source/change-1",
        }
        snap["artifact_revision"] = "art-v2"
        snap["previous_artifact_revision"] = "art-v1"
        snap["operation_id"] = "op-v2"
        snap["changes"][0].update(
            id="DIF-002", before_revision="doc-v1", after_revision="doc-v2"
        )
        data["observed_head_revision"] = "event-v2"
        self.assertEqual(handle(data)["status"], "complete", data)
        snap["event_basis"]["after_revision"] = "doc-v3"
        self.assertEqual(handle(data)["status"], "blocked")

    def test_handoff_carries_canonical_hash_and_source_scope(self) -> None:
        result = handle(fixture())
        handoff = result["handoff"]
        self.assertRegex(handoff["snapshot_sha256"], r"^[0-9a-f]{64}$")
        self.assertEqual(handoff["source_inventory"][0]["id"], "SRC-001")
        self.assertEqual(handoff["source_inventory"][0]["revision"], "head-v1")
        self.assertEqual(handoff["source_inventory"][0]["unretrieved"], [])
        self.assertEqual(handoff["feature_refs"][0]["id"], "FEAT-001")
        self.assertEqual(
            handoff["feature_refs"][0]["implementation_refs"], ["src/auth.py"]
        )
        self.assertEqual(handoff["impacted_feature_ids"], ["FEAT-001"])


if __name__ == "__main__":
    unittest.main()
