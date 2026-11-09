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


def continue_analysis(data: dict) -> dict:
    """Represent a manual correction at an unchanged source revision."""
    data["snapshot"]["event"] = "analysis_update"
    data["snapshot"]["event_basis"] = {
        "source_revision": data["snapshot"]["source_revision"],
        "evidence_ref": "review/confirmed",
    }
    return data


class FeatureRegistryTests(unittest.TestCase):
    def test_new_change_after_revision_must_match_source(self) -> None:
        data = fixture()
        data["snapshot"]["changes"][0]["after_revision"] = "unrelated-revision"
        self.assertEqual(handle(data)["status"], "blocked")
        self.assertIn(
            "change_source_revision_mismatch:DIF-001", handle(data)["reasons"]
        )

    def test_historical_diff_keeps_old_revision_after_source_update(self) -> None:
        data = fixture()
        previous = copy.deepcopy(data["snapshot"])
        data["previous_snapshot"] = previous
        snap = data["snapshot"]
        snap["event"] = "pr_update"
        snap["event_basis"] = {
            "base_sha": "c" * 40,
            "head_sha": "a" * 40,
            "previous_head_sha": "b" * 40,
        }
        previous["source_revision"] = "b" * 40
        previous["sources"][0]["revision"] = "b" * 40
        snap["source_revision"] = "a" * 40
        snap["sources"][0]["revision"] = "a" * 40
        data["observed_head_revision"] = "a" * 40
        snap["operation_id"] = "op-v2"
        snap["artifact_revision"] = "art-v2"
        snap["previous_artifact_revision"] = "art-v1"
        snap["changes"][0]["after_revision"] = "head-v1"
        snap["changes"].append(
            {
                **copy.deepcopy(snap["changes"][0]),
                "id": "DIF-002",
                "before_revision": "b" * 40,
                "after_revision": "a" * 40,
            }
        )
        self.assertEqual(handle(data)["status"], "complete", handle(data))
        snap["changes"][-1]["before_revision"] = "d" * 40
        self.assertEqual(handle(data)["status"], "blocked")

    def test_incomplete_change_source_never_reports_complete(self) -> None:
        data = fixture()
        data["snapshot"]["sources"][0].update(
            status="unavailable", reason="source unavailable"
        )
        report = handle(data)
        self.assertEqual(report["status"], "incomplete", report)
        self.assertIn("change_source_incomplete:DIF-001", report["reasons"])

    def test_classification_history_is_immutable(self) -> None:
        data = fixture()
        data["previous_snapshot"] = copy.deepcopy(data["snapshot"])
        continue_analysis(data)
        snapshot = data["snapshot"]
        snapshot["operation_id"] = "op-v2"
        snapshot["previous_artifact_revision"] = "art-v1"
        snapshot["artifact_revision"] = "art-v2"
        snapshot["changes"][0].update(
            classification="no_impact",
            feature_ids=[],
            reason="revised impact",
            approval_ref="approval/verified",
        )
        result = handle(data)
        self.assertEqual(result["status"], "blocked", result)
        self.assertIn("change_history_rewritten:DIF-001", result["reasons"])

    def test_reclassification_requires_new_id_evidence_and_approval_revision(
        self,
    ) -> None:
        data = fixture()
        data["previous_snapshot"] = copy.deepcopy(data["snapshot"])
        continue_analysis(data)
        snapshot = data["snapshot"]
        snapshot["operation_id"] = "op-v2"
        snapshot["previous_artifact_revision"] = "art-v1"
        snapshot["artifact_revision"] = "art-v2"
        replacement = {
            **copy.deepcopy(snapshot["changes"][0]),
            "id": "DIF-002",
            "supersedes_id": "DIF-001",
            "classification": "no_impact",
            "feature_ids": [],
            "reason": "Reviewed current classification",
            "evidence_ref": "review/decision-v2",
            "approval_ref": "approval/verified",
            "approval_revision": "approval-revision-v2",
        }
        snapshot["changes"].append(replacement)
        self.assertEqual(handle(data)["status"], "complete", handle(data))
        replacement.pop("approval_revision")
        self.assertIn("DIF-002_approval_revision_invalid", handle(data)["reasons"])
        replacement["approval_revision"] = "approval-revision-v2"
        replacement["evidence_ref"] = snapshot["changes"][0]["evidence_ref"]
        self.assertEqual(handle(data)["status"], "blocked")
        replacement["evidence_ref"] = "review/decision-v2"
        replacement["before_revision"] = "forged-base"
        self.assertEqual(handle(data)["status"], "blocked")

    def test_superseded_unclassified_change_does_not_remain_in_current_denominator(
        self,
    ) -> None:
        data = fixture()
        original = data["snapshot"]["changes"][0]
        original["classification"] = "unclassified"
        data["previous_snapshot"] = copy.deepcopy(data["snapshot"])
        continue_analysis(data)
        snap = data["snapshot"]
        snap["operation_id"] = "op-v2"
        snap["artifact_revision"] = "art-v2"
        snap["previous_artifact_revision"] = "art-v1"
        revised = copy.deepcopy(original)
        revised.update(
            id="DIF-002",
            supersedes_id="DIF-001",
            classification="no_impact",
            feature_ids=[],
            reason="Reviewed and approved the current classification",
            evidence_ref="review/current-v2",
            approval_ref="approval/verified",
            approval_revision="review-v2",
        )
        snap["changes"].append(revised)
        result = handle(data)
        self.assertEqual(result["status"], "complete", result)
        self.assertEqual(
            result["metrics"]["change_classification"]["denominator_ids"],
            ["DIF-002"],
        )
        self.assertEqual(result["metrics"]["change_classification"]["rate"], 1.0)
        self.assertEqual(result["handoff"]["unclassified_change_ids"], [])
        self.assertEqual(snap["changes"][0]["classification"], "unclassified")

    def test_same_classification_can_correct_feature_scope_with_approval(self) -> None:
        data = fixture()
        prior = copy.deepcopy(data["snapshot"])
        data["previous_snapshot"] = prior
        continue_analysis(data)
        snap = data["snapshot"]
        snap["operation_id"] = "reclass-same-state"
        snap["artifact_revision"] = "art-v2"
        snap["previous_artifact_revision"] = "art-v1"
        other = copy.deepcopy(snap["features"][0])
        other.update(id="FEAT-002", identity="independent endpoint", name="Endpoint")
        snap["features"].append(other)
        snap["history"].append(
            {
                "event_id": "event-2",
                "kind": "added",
                "revision": "head-v1",
                "evidence_ref": "evidence/new-feature",
                "from_ids": [],
                "to_ids": ["FEAT-002"],
            }
        )
        correction = copy.deepcopy(snap["changes"][0])
        correction.update(
            id="DIF-002",
            supersedes_id="DIF-001",
            classification="impact",
            feature_ids=["FEAT-002"],
            evidence_ref="review/new-feature-scope",
            reason="Reassigned impact after source inspection",
            approval_ref="approval/verified",
            approval_revision="policy-v2",
        )
        snap["changes"].append(correction)
        report = handle(data)
        self.assertEqual(report["status"], "complete", report)
        self.assertEqual(report["handoff"]["impacted_feature_ids"], ["FEAT-002"])

    def test_legacy_duplicate_difs_can_be_migrated_without_data_loss(self) -> None:
        data = fixture()
        old = data["snapshot"]
        duplicate = copy.deepcopy(old["changes"][0])
        duplicate.update(id="DIF-002", classification="no_impact", feature_ids=[],
                         approval_ref="approval/legacy", reason="Old alternate verdict")
        old["changes"].append(duplicate)
        previous = copy.deepcopy(old)
        data["previous_snapshot"] = previous
        continue_analysis(data)
        old["operation_id"] = "op-legacy-migration"
        old["artifact_revision"] = "art-v2"
        old["previous_artifact_revision"] = "art-v1"
        unresolved = handle(data)
        self.assertEqual(unresolved["status"], "incomplete", unresolved)
        self.assertTrue(
            any(x.startswith("legacy_duplicate_active_change:") for x in unresolved["reasons"])
        )
        correction = copy.deepcopy(old["changes"][0])
        correction.update(
            id="DIF-003",
            supersedes_ids=["DIF-001", "DIF-002"],
            evidence_ref="review/legacy-merged",
            reason="Reviewed and consolidated old conflicting verdicts",
            approval_ref="approval/verified",
            approval_revision="policy-v2",
        )
        old["changes"].append(correction)
        merged = handle(data)
        self.assertEqual(merged["status"], "complete", merged)
        self.assertEqual(merged["handoff"]["impacted_feature_ids"], ["FEAT-001"])
        self.assertEqual(len(old["changes"]), 3)
        correction["supersedes_ids"] = ["DIF-001"]
        self.assertEqual(handle(data)["status"], "blocked")
        correction["supersedes_ids"] = ["DIF-001", "DIF-002"]
        correction["locator"] = "other/path"
        self.assertEqual(handle(data)["status"], "blocked")

    def test_analysis_update_requires_all_source_revisions_unchanged(self) -> None:
        data = fixture()
        prior = copy.deepcopy(data["snapshot"])
        secondary = copy.deepcopy(prior["sources"][0])
        secondary.update(id="SRC-002", ref="product/other", revision="c" * 40)
        prior["sources"].append(secondary)
        prior["expected_source_ids"].append("SRC-002")
        data["previous_snapshot"] = prior
        data["snapshot"] = copy.deepcopy(prior)
        continue_analysis(data)
        snap = data["snapshot"]
        snap["artifact_revision"] = "art-v2"
        snap["previous_artifact_revision"] = "art-v1"
        snap["operation_id"] = "op-v2"
        self.assertEqual(handle(data)["status"], "complete")
        snap["sources"][1]["revision"] = "d" * 40
        blocked = handle(data)
        self.assertEqual(blocked["status"], "blocked", blocked)
        self.assertIn("analysis_update_source_revisions_changed", blocked["reasons"])

    def test_two_code_repositories_may_have_independent_head_revision(self) -> None:
        data = fixture()
        source = {
            **copy.deepcopy(data["snapshot"]["sources"][0]),
            "id": "SRC-002",
            "ref": "product/backend",
            "revision": "f" * 40,
        }
        data["snapshot"]["sources"].append(source)
        data["snapshot"]["expected_source_ids"].append("SRC-002")
        data["snapshot"]["features"][0]["source_ids"].append("SRC-002")
        self.assertEqual(handle(data)["status"], "complete", handle(data))

    def test_complete_local_inventory_has_no_full_product_guarantee(self) -> None:
        result = handle(fixture())
        self.assertEqual(result["status"], "complete", result)
        self.assertEqual(result["metrics"]["change_classification"]["rate"], 1.0)
        self.assertIsNone(result["metrics"]["all_product_features_discovered"])

    def test_pr_update_handoff_excludes_prior_revision_impact(self) -> None:
        data = fixture()
        previous = copy.deepcopy(data["snapshot"])
        data["previous_snapshot"] = previous
        before, head, base = "b" * 40, "a" * 40, "c" * 40
        previous["source_revision"] = before
        previous["sources"][0]["revision"] = before
        snapshot = data["snapshot"]
        snapshot["event"] = "pr_update"
        snapshot["event_basis"] = {
            "base_sha": base,
            "head_sha": head,
            "previous_head_sha": before,
        }
        snapshot["source_revision"] = head
        snapshot["sources"][0]["revision"] = head
        snapshot["operation_id"] = "op-v2"
        snapshot["artifact_revision"] = "art-v2"
        snapshot["previous_artifact_revision"] = "art-v1"
        data["observed_head_revision"] = head
        second = copy.deepcopy(snapshot["features"][0])
        second.update(
            id="FEAT-002",
            identity="batch settlement",
            name="Batch settlement",
            kind="batch",
            implementation_refs=["src/batch.py"],
        )
        snapshot["features"].append(second)
        snapshot["history"].append(
            {
                "event_id": "event-2",
                "kind": "added",
                "revision": head,
                "evidence_ref": "evidence/batch",
                "from_ids": [],
                "to_ids": ["FEAT-002"],
            }
        )
        latest = copy.deepcopy(snapshot["changes"][0])
        latest.update(
            id="DIF-002",
            before_revision=before,
            after_revision=head,
            locator="src/batch.py",
            feature_ids=["FEAT-002"],
        )
        snapshot["changes"].append(latest)
        result = handle(data)
        self.assertEqual(result["status"], "complete", result)
        self.assertEqual(
            result["metrics"]["change_classification"]["denominator_ids"],
            ["DIF-002"],
        )
        self.assertEqual(result["handoff"]["impacted_feature_ids"], ["FEAT-002"])
        self.assertEqual(result["handoff"]["approval_required_change_ids"], [])
        latest.update(
            classification="no_impact",
            feature_ids=[],
            approval_ref="approval/QA",
        )
        result = handle(data)
        self.assertEqual(result["status"], "complete", result)
        self.assertEqual(result["handoff"]["impacted_feature_ids"], [])
        self.assertEqual(result["handoff"]["approval_required_change_ids"], ["DIF-002"])

    def test_pr_update_ignores_reclassification_of_past_revision(self) -> None:
        for old_class, current_class, reviewed_class, impacted, approvals in (
            ("no_impact", "no_impact", "impact", [], ["DIF-002"]),
            ("impact", "impact", "no_impact", ["FEAT-001"], []),
        ):
            with self.subTest(reviewed_classification=reviewed_class):
                data = fixture()
                previous = copy.deepcopy(data["snapshot"])
                old_head, new_head = "b" * 40, "a" * 40
                previous["source_revision"] = old_head
                previous["sources"][0]["revision"] = old_head
                prior_change = previous["changes"][0]
                prior_change["after_revision"] = old_head
                prior_change["classification"] = old_class
                prior_change["feature_ids"] = (
                    ["FEAT-001"] if old_class == "impact" else []
                )
                if old_class == "no_impact":
                    prior_change["approval_ref"] = "approval/old"
                snapshot = copy.deepcopy(previous)
                data["previous_snapshot"] = previous
                data["snapshot"] = snapshot
                data["observed_head_revision"] = new_head
                snapshot["event"] = "pr_update"
                snapshot["event_basis"] = {
                    "base_sha": "c" * 40,
                    "head_sha": new_head,
                    "previous_head_sha": old_head,
                }
                snapshot["source_revision"] = new_head
                snapshot["sources"][0]["revision"] = new_head
                snapshot["operation_id"] = "op-v2"
                snapshot["artifact_revision"] = "art-v2"
                snapshot["previous_artifact_revision"] = "art-v1"
                new_change = copy.deepcopy(prior_change)
                new_change.update(
                    id="DIF-002",
                    before_revision=old_head,
                    after_revision=new_head,
                    locator="src/current.py",
                    classification=current_class,
                    feature_ids=["FEAT-001"] if current_class == "impact" else [],
                    reason="Current PR source change reviewed",
                )
                if current_class == "no_impact":
                    new_change["approval_ref"] = "approval/current"
                correction = copy.deepcopy(prior_change)
                correction.update(
                    id="DIF-003",
                    supersedes_id="DIF-001",
                    classification=reviewed_class,
                    feature_ids=["FEAT-001"] if reviewed_class == "impact" else [],
                    evidence_ref="review/old-diff-correction",
                    approval_ref="approval/reclassification",
                    approval_revision="approval-v2",
                    reason="Historical source revision reviewed",
                )
                snapshot["changes"].extend([new_change, correction])
                report = handle(data)
                self.assertEqual(report["status"], "complete", report)
                self.assertEqual(
                    report["metrics"]["change_classification"]["denominator_ids"],
                    ["DIF-002"],
                )
                self.assertEqual(report["handoff"]["impacted_feature_ids"], impacted)
                self.assertEqual(
                    report["handoff"]["approval_required_change_ids"], approvals
                )

    def test_same_git_revision_pair_cannot_have_conflicting_active_difs(self) -> None:
        data = fixture()
        duplicate = copy.deepcopy(data["snapshot"]["changes"][0])
        duplicate.update(
            id="DIF-002",
            classification="no_impact",
            feature_ids=[],
            reason="Different verdict for exactly the same Git change",
            approval_ref="approval/QA",
        )
        data["snapshot"]["changes"].append(duplicate)
        result = handle(data)
        self.assertEqual(result["status"], "blocked", result)
        self.assertIn(
            "duplicate_active_change:DIF-001:DIF-002",
            result["reasons"],
        )
        duplicate["locator"] = "src/another.py"
        self.assertEqual(handle(data)["status"], "complete")

    def test_shared_git_sha_needs_explicit_primary_source_id(self) -> None:
        data = fixture()
        previous = copy.deepcopy(data["snapshot"])
        prior_code = copy.deepcopy(previous["sources"][0])
        prior_code.update(id="SRC-002", ref="product/other")
        previous["sources"].append(prior_code)
        previous["expected_source_ids"].append("SRC-002")
        data["previous_snapshot"] = previous
        snapshot = data["snapshot"]
        current_source = copy.deepcopy(snapshot["sources"][0])
        current_source.update(id="SRC-002", ref="product/other")
        snapshot["sources"].append(current_source)
        snapshot["expected_source_ids"].append("SRC-002")
        before, head, base, secondary_base = ("b" * 40, "a" * 40, "c" * 40, "d" * 40)
        previous["source_revision"] = before
        for row in previous["sources"]:
            row["revision"] = before
        snapshot["source_revision"] = head
        for row in snapshot["sources"]:
            row["revision"] = head
        snapshot["event"] = "pr_update"
        snapshot["event_basis"] = {
            "base_sha": base,
            "head_sha": head,
            "previous_head_sha": before,
        }
        snapshot["operation_id"] = "op-v2"
        snapshot["artifact_revision"] = "art-v2"
        snapshot["previous_artifact_revision"] = "art-v1"
        data["observed_head_revision"] = head
        primary = copy.deepcopy(snapshot["changes"][0])
        primary.update(
            id="DIF-002",
            before_revision=base,
            after_revision=head,
            locator="src/new.py",
        )
        secondary = copy.deepcopy(primary)
        secondary.update(
            id="DIF-003",
            source_id="SRC-002",
            before_revision=secondary_base,
        )
        snapshot["changes"].extend([primary, secondary])
        self.assertIn("event_primary_source_ambiguous", handle(data)["reasons"])
        snapshot["event_basis"]["primary_source_id"] = "SRC-001"
        self.assertEqual(handle(data)["status"], "complete", handle(data))
        snapshot["event_basis"]["primary_source_id"] = "SRC-002"
        self.assertIn(
            "change_before_revision_mismatch:DIF-003", handle(data)["reasons"]
        )
        snapshot["event_basis"]["primary_source_id"] = "SRC-003"
        self.assertIn("event_primary_source_invalid", handle(data)["reasons"])

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
        continue_analysis(next_step)
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
        continue_analysis(data)
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
        continue_analysis(data)
        data["snapshot"]["previous_artifact_revision"] = "art-v1"
        data["snapshot"]["operation_id"] = "op-v2"
        data["snapshot"]["features"][0]["identity"] = "unrelated feature"
        self.assertEqual(handle(data)["status"], "blocked")

    def test_split_requires_retirement_history(self) -> None:
        data = fixture()
        data["previous_snapshot"] = copy.deepcopy(data["snapshot"])
        continue_analysis(data)
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
                continue_analysis(data)
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
        continue_analysis(data)
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

    def test_initial_event_with_previous_changed_snapshot_is_rejected(self) -> None:
        data = fixture()
        data["previous_snapshot"] = copy.deepcopy(data["snapshot"])
        data["snapshot"]["operation_id"] = "new-operation"
        data["snapshot"]["artifact_revision"] = "art-v2"
        data["snapshot"]["previous_artifact_revision"] = "art-v1"
        self.assertEqual(handle(data)["status"], "blocked")
        self.assertIn("initial_event_with_previous_snapshot", handle(data)["reasons"])
        continue_analysis(data)
        self.assertEqual(handle(data)["status"], "complete")

    def test_analysis_update_cannot_hide_changed_source(self) -> None:
        data = fixture()
        data["previous_snapshot"] = copy.deepcopy(data["snapshot"])
        continue_analysis(data)
        data["snapshot"]["source_revision"] = "new-head"
        data["observed_head_revision"] = "new-head"
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
                change = copy.deepcopy(snap["changes"][0])
                change.update(
                    id="DIF-002", before_revision=old_sha, after_revision=new_sha
                )
                snap["changes"].append(change)
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
        change = copy.deepcopy(snap["changes"][0])
        change.update(id="DIF-002", before_revision="doc-v1", after_revision="doc-v2")
        snap["changes"].append(change)
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
