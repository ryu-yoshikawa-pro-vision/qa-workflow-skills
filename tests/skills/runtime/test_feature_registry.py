from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "skills" / "feature-analysis" / "scripts"))
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

    def test_zero_denominators_are_unknown(self) -> None:
        data = fixture()
        data["snapshot"]["changes"] = []
        data["snapshot"]["candidates"] = []
        result = handle(data)
        self.assertEqual(result["status"], "incomplete")
        self.assertIsNone(result["metrics"]["change_classification"]["rate"])
        self.assertIsNone(result["metrics"]["observed_candidate_mapping"]["rate"])

    def test_path_change_preserves_semantic_feature_id(self) -> None:
        first = fixture()
        next_step = copy.deepcopy(first)
        next_step["previous_snapshot"] = copy.deepcopy(first["snapshot"])
        next_step["snapshot"]["previous_artifact_revision"] = "art-v1"
        next_step["snapshot"]["artifact_revision"] = "art-v2"
        next_step["snapshot"]["operation_id"] = "op-v2"
        next_step["snapshot"]["features"][0]["implementation_refs"] = ["src/new-auth.py"]
        self.assertEqual(handle(next_step)["status"], "complete")

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

    def test_duplicate_operation_does_not_rerun(self) -> None:
        data = fixture()
        data["previous_snapshot"] = copy.deepcopy(data["snapshot"])
        self.assertEqual(handle(data)["status"], "idempotent")
        data["snapshot"]["features"][0]["name"] = "Different"
        self.assertEqual(handle(data)["status"], "blocked")

    def test_out_of_scope_requires_approval_reference(self) -> None:
        data = fixture()
        change = data["snapshot"]["changes"][0]
        change["classification"] = "out_of_scope"
        self.assertEqual(handle(data)["status"], "blocked")


if __name__ == "__main__":
    unittest.main()
