from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from scripts.skills.evals.deterministic.run import grade


REPO_ROOT = Path(__file__).resolve().parents[4]


def load_skill_helper(skill: str, filename: str):
    path = REPO_ROOT / "skills" / skill / "scripts" / filename
    spec = importlib.util.spec_from_file_location(f"test_{skill.replace('-', '_')}_{filename[:-3]}", path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_skill_validator(skill: str):
    path = REPO_ROOT / "skills" / skill / "evals" / "deterministic" / "validator.py"
    spec = importlib.util.spec_from_file_location(f"test_{skill.replace('-', '_')}_validator", path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


regression = load_skill_helper("regression-testing", "regression_runtime.py")
regression_validator = load_skill_validator("regression-testing")
exploratory = load_skill_helper("exploratory-testing", "exploratory_runtime.py")
knowledge = load_skill_helper("qa-knowledge", "knowledge_runtime.py")
workflow = load_skill_helper("qa-workflow", "artifact_graph.py")


class RegressionRuntimeTests(unittest.TestCase):
    def discovery(self, *, lifecycle="current", revision="r1", listing_complete=True):
        return regression.build_discovery_snapshot({
            "discovery_roots": ["qa/test-cases"],
            "listing_complete": listing_complete,
            "source_revisions": [{"source_ref": "repo:qa/test-cases", "revision": revision}],
            "cases": [
                {"tc_ref": "TC-002", "source_ref": "repo:qa/test-cases", "source_revision": revision, "lifecycle_status": lifecycle, "content_fingerprint": "owner-fingerprint-2"},
                {"tc_ref": "TC-001", "source_ref": "repo:qa/test-cases", "source_revision": revision, "lifecycle_status": "current", "content_fingerprint": "owner-fingerprint-1"},
            ],
        })

    def test_discovery_snapshot_and_lifecycle_resolution_are_separate(self):
        snapshot = self.discovery(lifecycle="unresolved")
        self.assertTrue(snapshot["discovery_complete"])
        self.assertFalse(snapshot["lifecycle_complete"])
        self.assertFalse(snapshot["complete"])
        self.assertEqual(snapshot["unresolved_tc_refs"], ["TC-002"])

        deleted = self.discovery(lifecycle="deleted")
        self.assertTrue(deleted["complete"])
        self.assertEqual([case["tc_ref"] for case in deleted["cases"]], ["TC-001", "TC-002"])

        truncated = self.discovery(listing_complete=False)
        self.assertFalse(truncated["discovery_complete"])
        self.assertFalse(truncated["complete"])

    def test_snapshot_batches_are_stable_and_stale_resume_requires_new_snapshot(self):
        old = self.discovery()
        first = regression.deterministic_batch(old, offset=0, limit=1)
        second = regression.deterministic_batch(old, offset=1, limit=1, expected_snapshot_ref=old["snapshot_ref"])
        self.assertEqual(first["tc_refs"], ["TC-001"])
        self.assertEqual(second["tc_refs"], ["TC-002"])
        self.assertTrue(second["complete"])

        new = self.discovery(revision="r2")
        resume = regression.deterministic_batch(new, offset=1, limit=1, expected_snapshot_ref=old["snapshot_ref"])
        self.assertEqual(resume["status"], "new_snapshot_required")

    def test_membership_and_coverage_gap_are_independent(self):
        snapshot = self.discovery()
        partial = regression.reconcile_membership(snapshot, [{
            "tc_ref": "TC-001",
            "decision": "member",
            "reason": "current in scope",
            "source_refs": ["risk:RISK-001"],
            "source_revisions": [{"source_ref": "risk:RISK-001", "revision": "r3"}],
        }])
        self.assertFalse(partial["complete"])
        self.assertEqual(partial["undecided_tc_refs"], ["TC-002"])
        complete = regression.reconcile_membership(snapshot, [
            {"tc_ref": "TC-001", "decision": "member", "reason": "current recurring path", "source_refs": ["risk:RISK-001"], "source_revisions": [{"source_ref": "risk:RISK-001", "revision": "r3"}]},
            {"tc_ref": "TC-002", "decision": "one_off", "reason": "migration only", "source_refs": ["issue:ISSUE-002"], "source_revisions": [{"source_ref": "issue:ISSUE-002", "revision": "r8"}]},
        ])
        self.assertTrue(complete["complete"])
        self.assertEqual(complete["member_tc_refs"], ["TC-001"])
        complete["coverage_gaps"] = ["scope:refund"]
        self.assertTrue(complete["complete"])

    def test_membership_provenance_is_required_for_completeness(self):
        snapshot = self.discovery()
        valid_decisions = [
            {"tc_ref": "TC-001", "decision": "member", "reason": "current recurring path", "source_refs": ["risk:RISK-001"], "source_revisions": [{"source_ref": "risk:RISK-001", "revision": "r3"}]},
            {"tc_ref": "TC-002", "decision": "one_off", "reason": "migration only", "source_refs": ["issue:ISSUE-002"], "source_revisions": [{"source_ref": "issue:ISSUE-002", "revision": "r8"}]},
        ]
        for field in ("source_refs", "source_revisions"):
            with self.subTest(field=field):
                decisions = [dict(item) for item in valid_decisions]
                decisions[0].pop(field)
                result = regression.reconcile_membership(snapshot, decisions)
                self.assertFalse(result["complete"])
                self.assertIn("invalid_membership_provenance:TC-001", result["issues"])

        malformed_payloads = [
            {"source_refs": []},
            {"source_refs": ["risk:RISK-001", "risk:RISK-001"]},
            {"source_revisions": []},
            {"source_revisions": [{"source_ref": "risk:RISK-001"}]},
            {"source_revisions": [{"source_ref": "other:RISK-001", "revision": "r3"}]},
            {"source_revisions": [
                {"source_ref": "risk:RISK-001", "revision": "r3"},
                {"source_ref": "risk:RISK-001", "revision": "r4"},
            ]},
        ]
        for malformed in malformed_payloads:
            with self.subTest(malformed=malformed):
                decisions = json.loads(json.dumps(valid_decisions))
                decisions[0].update(malformed)
                result = regression.reconcile_membership(snapshot, decisions)
                self.assertFalse(result["complete"])
                self.assertIn("invalid_membership_provenance:TC-001", result["issues"])

    def test_three_current_tc_population_produces_complete_current_full_run(self):
        discovery_revisions = [{"source_ref": "repo:qa/test-cases", "revision": "r18"}]
        snapshot = regression.build_discovery_snapshot({
            "discovery_roots": ["qa/test-cases"],
            "listing_complete": True,
            "source_revisions": discovery_revisions,
            "cases": [
                {"tc_ref": f"TC-00{number}", "source_ref": "repo:qa/test-cases", "source_revision": "r18", "lifecycle_status": "current"}
                for number in (1, 2, 3)
            ],
        })
        decisions = [
            {"tc_ref": "TC-001", "decision": "member", "reason": "recurring checkout path", "source_refs": ["risk:RISK-001"], "source_revisions": [{"source_ref": "risk:RISK-001", "revision": "r3"}]},
            {"tc_ref": "TC-002", "decision": "one_off", "reason": "migration-only check", "source_refs": ["issue:ISSUE-002"], "source_revisions": [{"source_ref": "issue:ISSUE-002", "revision": "r8"}]},
            {"tc_ref": "TC-003", "decision": "out_of_scope", "reason": "admin path is outside checkout regression", "source_refs": ["risk:RISK-003"], "source_revisions": [{"source_ref": "risk:RISK-003", "revision": "r2"}]},
        ]
        membership = regression.reconcile_membership(snapshot, decisions)
        self.assertTrue(membership["complete"], membership["issues"])
        self.assertEqual([item["tc_ref"] for item in membership["memberships"]], ["TC-001", "TC-002", "TC-003"])
        source_revisions = [
            *discovery_revisions,
            *[revision for decision in decisions for revision in decision["source_revisions"]],
        ]
        baseline = {
            "artifact_type": "baseline",
            "schema_version": "1",
            "baseline_ref": "BASE-TEST-003",
            "discovery_snapshot_ref": snapshot["snapshot_ref"],
            "source_revisions": source_revisions,
            "scope_identity": "scope:checkout",
            "scope_refs": ["scope:checkout"],
            "memberships": membership["memberships"],
            "member_tc_refs": membership["member_tc_refs"],
            "one_off_tc_refs": membership["one_off_tc_refs"],
            "unresolved_tc_refs": membership["unresolved_tc_refs"],
            "undecided_tc_refs": membership["undecided_tc_refs"],
            "coverage_gaps": [],
            "completeness_evidence": {
                "root_listing_complete": True,
                "source_revisions_complete": True,
                "lifecycle_resolved": True,
                "membership_decisions_complete": True,
            },
            "complete": membership["complete"],
        }
        rendered = "```json\n" + json.dumps(baseline, ensure_ascii=False) + "\n```"
        result = regression_validator.validate(rendered, {
            "artifact_type": "baseline",
            "expected_current_tc_refs": ["TC-001", "TC-002", "TC-003"],
        }, "REG-OUT-001")
        self.assertTrue(all(assertion.status == "pass" for assertion in result.assertions), result.to_dict())
        currentness = regression.check_baseline_currentness(baseline, {
            **snapshot,
            "scope_identity": "scope:checkout",
            "source_revisions": source_revisions,
        })
        self.assertEqual(currentness["status"], "current")
        full = regression.plan_run(baseline, requested_scope="full", currentness=currentness)
        self.assertEqual(full["status"], "ready")
        self.assertEqual(full["selected_tc_refs"], ["TC-001"])
        self.assertTrue(full["suite_complete"])

    def test_discovery_membership_baseline_currentness_and_full_run_contract(self):
        snapshot = self.discovery()
        decisions = [
            {
                "tc_ref": "TC-001",
                "decision": "member",
                "reason": "current recurring path",
                "lifecycle_status": "stale",
                "source_refs": ["risk:RISK-001"],
                "source_revisions": [{"source_ref": "risk:RISK-001", "revision": "r3"}],
            },
            {
                "tc_ref": "TC-002",
                "decision": "one_off",
                "reason": "migration only",
                "lifecycle_status": "deleted",
                "source_refs": ["issue:ISSUE-002"],
                "source_revisions": [{"source_ref": "issue:ISSUE-002", "revision": "r8"}],
            },
        ]
        membership = regression.reconcile_membership(snapshot, decisions)
        expected_memberships = [
            {
                "tc_ref": "TC-001",
                "lifecycle_status": "current",
                "decision": "member",
                "reason": "current recurring path",
                "source_refs": ["risk:RISK-001"],
                "source_revisions": [{"source_ref": "risk:RISK-001", "revision": "r3"}],
            },
            {
                "tc_ref": "TC-002",
                "lifecycle_status": "current",
                "decision": "one_off",
                "reason": "migration only",
                "source_refs": ["issue:ISSUE-002"],
                "source_revisions": [{"source_ref": "issue:ISSUE-002", "revision": "r8"}],
            },
        ]
        self.assertEqual(membership["memberships"], expected_memberships)
        self.assertEqual(membership["member_tc_refs"], ["TC-001"])
        self.assertEqual(membership["one_off_tc_refs"], ["TC-002"])
        caller_lifecycle = regression.reconcile_membership(snapshot, [
            {**decisions[0], "lifecycle_status": "stale"},
            {**decisions[1], "lifecycle_status": "deleted"},
        ])
        self.assertEqual(caller_lifecycle["memberships"], expected_memberships)

        scope_identity = "scope:checkout"
        baseline_source_revisions = [
            *snapshot["source_revisions"],
            *[revision for decision in decisions for revision in decision["source_revisions"]],
        ]
        baseline = {
            "artifact_type": "baseline",
            "schema_version": "1",
            "baseline_ref": "BASE-TEST-001",
            "discovery_snapshot_ref": snapshot["snapshot_ref"],
            "source_revisions": baseline_source_revisions,
            "scope_identity": scope_identity,
            "scope_refs": [],
            "memberships": membership["memberships"],
            "member_tc_refs": membership["member_tc_refs"],
            "one_off_tc_refs": membership["one_off_tc_refs"],
            "unresolved_tc_refs": membership["unresolved_tc_refs"],
            "undecided_tc_refs": membership["undecided_tc_refs"],
            "coverage_gaps": [],
            "completeness_evidence": {
                "root_listing_complete": True,
                "source_revisions_complete": True,
                "lifecycle_resolved": True,
                "membership_decisions_complete": True,
            },
            "complete": membership["complete"],
        }
        rendered = "```json\n" + json.dumps(baseline, ensure_ascii=False) + "\n```"
        validation = regression_validator.validate(rendered, {"artifact_type": "baseline"}, "REG-OUT-001")
        statuses = {item.id: item.status for item in validation.assertions}
        self.assertEqual(statuses["REG-D003"], "pass")
        self.assertEqual(statuses["REG-D004"], "pass")
        self.assertEqual(statuses["REG-D016"], "pass")
        self.assertTrue(all(status == "pass" for status in statuses.values()), statuses)

        current = {**snapshot, "scope_identity": scope_identity, "source_revisions": baseline_source_revisions}
        currentness = regression.check_baseline_currentness(baseline, current)
        self.assertEqual(currentness["status"], "current")
        full = regression.plan_run(baseline, requested_scope="full", currentness=currentness)
        self.assertEqual(full["status"], "ready")
        self.assertEqual(full["selected_tc_refs"], ["TC-001"])
        self.assertTrue(full["suite_complete"])

        changed_risk = [
            {"source_ref": "repo:qa/test-cases", "revision": "r1"},
            {"source_ref": "risk:RISK-001", "revision": "r4"},
            {"source_ref": "issue:ISSUE-002", "revision": "r8"},
        ]
        stale_currentness = regression.check_baseline_currentness(
            baseline, {**current, "source_revisions": changed_risk}
        )
        self.assertEqual(stale_currentness["status"], "stale")
        self.assertEqual(regression.plan_run(baseline, requested_scope="full", currentness=stale_currentness)["status"], "blocked")

        missing_currentness = regression.check_baseline_currentness(
            baseline,
            {**current, "source_revisions": [revision for revision in baseline_source_revisions if revision["source_ref"] != "risk:RISK-001"]},
        )
        self.assertEqual(missing_currentness["status"], "unresolved")
        self.assertEqual(regression.plan_run(baseline, requested_scope="full", currentness=missing_currentness)["status"], "blocked")

    def test_discovery_snapshot_identity_change_blocks_full_run(self):
        saved_snapshot = self.discovery()
        decisions = [
            {"tc_ref": "TC-001", "decision": "member", "reason": "recurring path", "source_refs": ["risk:RISK-001"], "source_revisions": [{"source_ref": "risk:RISK-001", "revision": "r3"}]},
            {"tc_ref": "TC-002", "decision": "one_off", "reason": "migration-only check", "source_refs": ["issue:ISSUE-002"], "source_revisions": [{"source_ref": "issue:ISSUE-002", "revision": "r8"}]},
        ]
        membership = regression.reconcile_membership(saved_snapshot, decisions)
        self.assertTrue(membership["complete"])
        source_revisions = [
            *saved_snapshot["source_revisions"],
            *[revision for decision in decisions for revision in decision["source_revisions"]],
        ]
        baseline = {
            "complete": membership["complete"],
            "discovery_snapshot_ref": saved_snapshot["snapshot_ref"],
            "scope_identity": "scope:checkout",
            "source_revisions": source_revisions,
            "memberships": membership["memberships"],
            "member_tc_refs": membership["member_tc_refs"],
            "unresolved_tc_refs": membership["unresolved_tc_refs"],
            "undecided_tc_refs": membership["undecided_tc_refs"],
        }
        saved_currentness = regression.check_baseline_currentness(baseline, {
            **saved_snapshot,
            "scope_identity": "scope:checkout",
            "source_revisions": source_revisions,
        })
        self.assertEqual(saved_currentness["status"], "current")

        current_snapshot = self.discovery(lifecycle="deleted")
        self.assertEqual(current_snapshot["source_revisions"], saved_snapshot["source_revisions"])
        self.assertNotEqual(current_snapshot["snapshot_ref"], saved_snapshot["snapshot_ref"])
        stale = regression.check_baseline_currentness(baseline, {
            **current_snapshot,
            "scope_identity": "scope:checkout",
            "source_revisions": source_revisions,
        })
        self.assertEqual(stale["status"], "stale")
        self.assertIn("<discovery_snapshot>", stale["changed_sources"])
        self.assertEqual(regression.plan_run(baseline, requested_scope="full", currentness=stale)["status"], "blocked")

    def test_currentness_requires_complete_saved_membership_population(self):
        snapshot = self.discovery()
        decisions = [
            {"tc_ref": "TC-001", "decision": "member", "reason": "recurring path", "source_refs": ["risk:RISK-001"], "source_revisions": [{"source_ref": "risk:RISK-001", "revision": "r3"}]},
            {"tc_ref": "TC-002", "decision": "one_off", "reason": "migration-only check", "source_refs": ["issue:ISSUE-002"], "source_revisions": [{"source_ref": "issue:ISSUE-002", "revision": "r8"}]},
        ]
        membership = regression.reconcile_membership(snapshot, decisions)
        source_revisions = [
            *snapshot["source_revisions"],
            *[revision for decision in decisions for revision in decision["source_revisions"]],
        ]
        baseline = {
            "complete": membership["complete"],
            "discovery_snapshot_ref": snapshot["snapshot_ref"],
            "scope_identity": "scope:checkout",
            "source_revisions": source_revisions,
            "memberships": membership["memberships"],
            "member_tc_refs": membership["member_tc_refs"],
            "one_off_tc_refs": membership["one_off_tc_refs"],
            "unresolved_tc_refs": membership["unresolved_tc_refs"],
            "undecided_tc_refs": membership["undecided_tc_refs"],
        }
        current = {
            **snapshot,
            "scope_identity": "scope:checkout",
            "source_revisions": source_revisions,
        }
        currentness = regression.check_baseline_currentness(baseline, current)
        self.assertEqual(currentness["status"], "current")
        full = regression.plan_run(baseline, requested_scope="full", currentness=currentness)
        self.assertEqual(full["status"], "ready")
        self.assertEqual(full["selected_tc_refs"], ["TC-001"])
        self.assertTrue(full["suite_complete"])

        missing = {
            **baseline,
            "memberships": [item for item in baseline["memberships"] if item["tc_ref"] == "TC-001"],
        }
        missing_currentness = regression.check_baseline_currentness(missing, current)
        self.assertEqual(missing_currentness["status"], "incomplete")
        self.assertEqual(
            regression.plan_run(missing, requested_scope="full", currentness=missing_currentness)["status"],
            "blocked",
        )

        extra_membership = {
            **baseline["memberships"][1],
            "tc_ref": "TC-003",
            "decision": "out_of_scope",
        }
        extra = {**baseline, "memberships": [*baseline["memberships"], extra_membership]}
        self.assertEqual(regression.check_baseline_currentness(extra, current)["status"], "incomplete")

        unresolved_membership = json.loads(json.dumps(baseline))
        unresolved_membership["memberships"][1]["decision"] = "unresolved"
        self.assertEqual(regression.check_baseline_currentness(unresolved_membership, current)["status"], "incomplete")

        for invalid_cases in (None, [{"lifecycle_status": "current"}]):
            with self.subTest(invalid_cases=invalid_cases):
                self.assertEqual(
                    regression.check_baseline_currentness(baseline, {**current, "cases": invalid_cases})["status"],
                    "unresolved",
                )

        empty_snapshot = regression.build_discovery_snapshot({
            "discovery_roots": ["qa/test-cases"],
            "listing_complete": True,
            "source_revisions": [{"source_ref": "repo:qa/test-cases", "revision": "r1"}],
            "cases": [],
        })
        empty_baseline = {
            "complete": True,
            "discovery_snapshot_ref": empty_snapshot["snapshot_ref"],
            "scope_identity": "scope:checkout",
            "source_revisions": empty_snapshot["source_revisions"],
            "memberships": [],
            "member_tc_refs": [],
            "unresolved_tc_refs": [],
            "undecided_tc_refs": [],
        }
        empty_currentness = regression.check_baseline_currentness(
            empty_baseline,
            {**empty_snapshot, "scope_identity": "scope:checkout"},
        )
        self.assertEqual(empty_currentness["status"], "current")
        empty_full = regression.plan_run(empty_baseline, requested_scope="full", currentness=empty_currentness)
        self.assertEqual(empty_full["status"], "ready")
        self.assertEqual(empty_full["selected_tc_refs"], [])
        self.assertTrue(empty_full["suite_complete"])

    def test_unresolved_membership_prevents_baseline_completion(self):
        snapshot = self.discovery()
        decisions = [
            {"tc_ref": "TC-001", "decision": "member", "reason": "recurring path", "source_refs": ["risk:RISK-001"], "source_revisions": [{"source_ref": "risk:RISK-001", "revision": "r3"}]},
            {"tc_ref": "TC-002", "decision": "unresolved", "reason": "scope evidence is insufficient", "source_refs": ["issue:ISSUE-002"], "source_revisions": [{"source_ref": "issue:ISSUE-002", "revision": "r8"}]},
        ]
        result = regression.reconcile_membership(snapshot, decisions)
        self.assertFalse(result["complete"])
        self.assertEqual(result["unresolved_tc_refs"], ["TC-002"])
        self.assertEqual(result["undecided_tc_refs"], [])

        valid_decisions = [
            decisions[0],
            {**decisions[1], "decision": "one_off", "reason": "migration-only check"},
        ]
        valid_membership = regression.reconcile_membership(snapshot, valid_decisions)
        source_revisions = [
            *snapshot["source_revisions"],
            *[revision for decision in valid_decisions for revision in decision["source_revisions"]],
        ]
        baseline = {
            "complete": True,
            "discovery_snapshot_ref": snapshot["snapshot_ref"],
            "scope_identity": "scope:checkout",
            "source_revisions": source_revisions,
            "memberships": valid_membership["memberships"],
            "unresolved_tc_refs": [],
            "undecided_tc_refs": [],
        }
        current = {
            **snapshot,
            "scope_identity": "scope:checkout",
            "source_revisions": source_revisions,
        }
        for field in ("unresolved_tc_refs", "undecided_tc_refs"):
            for invalid_refs in (["TC-002"], "TC-002", None):
                with self.subTest(field=field, invalid_refs=invalid_refs):
                    contradictory = {**baseline, field: invalid_refs}
                    self.assertEqual(regression.check_baseline_currentness(contradictory, current)["status"], "incomplete")

    def test_currentness_precedes_full_and_selected_run_planning(self):
        baseline = {"complete": True, "member_tc_refs": ["TC-001", "TC-002"]}
        self.assertEqual(regression.plan_run(baseline, requested_scope="full")["status"], "blocked")
        stale = regression.plan_run(baseline, requested_scope="full", currentness={"status": "stale"})
        self.assertEqual(stale["reason"], "baseline_not_current")
        full = regression.plan_run(baseline, requested_scope="full", currentness={"status": "current"})
        self.assertEqual(full["selected_tc_refs"], ["TC-001", "TC-002"])
        selected = regression.plan_run(baseline, requested_scope="selected", requested_tc_refs=["TC-002"], currentness={"status": "current"})
        self.assertFalse(selected["suite_complete"])
        self.assertEqual(selected["selected_tc_refs"], ["TC-002"])
        incomplete_candidates = regression.plan_run(baseline, requested_scope=None, candidate_query_complete=False, currentness={"status": "current"})
        self.assertEqual(incomplete_candidates["scope"], "full")
        self.assertTrue(incomplete_candidates["suite_complete"])

    def test_full_run_requires_member_projection_and_preserves_valid_empty_projection(self):
        currentness = {"status": "current"}
        fixture_memberships = [{"tc_ref": "TC-001", "decision": "member", "lifecycle_status": "current"}]
        missing = regression.plan_run(
            {"complete": True, "memberships": fixture_memberships},
            requested_scope="full",
            currentness=currentness,
        )
        self.assertNotEqual(missing["status"], "ready")
        self.assertFalse(missing.get("suite_complete", False))
        self.assertEqual(missing["selected_tc_refs"], [])

        for projection in (None, "TC-001", [None], ["TC-001", "TC-001"]):
            with self.subTest(projection=projection):
                malformed = regression.plan_run(
                    {"complete": True, "member_tc_refs": projection},
                    requested_scope="full",
                    currentness=currentness,
                )
                self.assertEqual(malformed["status"], "blocked")

        full = regression.plan_run(
            {"complete": True, "member_tc_refs": ["TC-001", "TC-002"]},
            requested_scope="full",
            currentness=currentness,
        )
        self.assertEqual(full["selected_tc_refs"], ["TC-001", "TC-002"])
        self.assertTrue(full["suite_complete"])

        empty = regression.plan_run(
            {"complete": True, "member_tc_refs": []},
            requested_scope="full",
            currentness=currentness,
        )
        self.assertEqual(empty["status"], "ready")
        self.assertEqual(empty["selected_tc_refs"], [])
        self.assertTrue(empty["suite_complete"])

        mismatch = regression.plan_run(
            {"complete": True, "member_tc_refs": [], "memberships": fixture_memberships},
            requested_scope="full",
            currentness=currentness,
        )
        self.assertEqual(mismatch["status"], "blocked")
        self.assertFalse(mismatch.get("suite_complete", False))

        fallback_missing = regression.plan_run(
            {"complete": True},
            requested_scope=None,
            candidate_query_complete=False,
            currentness=currentness,
        )
        self.assertEqual(fallback_missing["status"], "blocked")
        self.assertFalse(fallback_missing.get("suite_complete", False))
        fallback_full = regression.plan_run(
            {"complete": True, "member_tc_refs": ["TC-001"]},
            requested_scope=None,
            candidate_query_complete=False,
            currentness=currentness,
        )
        self.assertEqual(fallback_full["selected_tc_refs"], ["TC-001"])
        self.assertTrue(fallback_full["suite_complete"])

    def test_currentness_requires_scope_identity_and_revision_list(self):
        revisions = [
            {"source_ref": "repo:qa/test-cases", "revision": "r1"},
            {"source_ref": "risk:RISK-001", "revision": "r3"},
        ]
        memberships = [{
            "tc_ref": "TC-001",
            "decision": "member",
            "lifecycle_status": "current",
            "source_refs": ["risk:RISK-001"],
            "source_revisions": [{"source_ref": "risk:RISK-001", "revision": "r3"}],
        }]
        baseline = {
            "complete": True,
            "discovery_snapshot_ref": "DS-CURRENTNESS-TEST",
            "scope_identity": "scope:checkout",
            "source_revisions": revisions,
            "memberships": memberships,
            "unresolved_tc_refs": [],
            "undecided_tc_refs": [],
        }
        current = {
            "complete": True,
            "snapshot_ref": "DS-CURRENTNESS-TEST",
            "cases": [{"tc_ref": "TC-001", "lifecycle_status": "current"}],
            "scope_identity": "scope:checkout",
            "source_revisions": revisions,
        }
        self.assertEqual(regression.check_baseline_currentness(baseline, current)["status"], "current")

        missing_baseline_snapshot_ref = dict(baseline)
        missing_baseline_snapshot_ref.pop("discovery_snapshot_ref")
        self.assertEqual(regression.check_baseline_currentness(missing_baseline_snapshot_ref, current)["status"], "incomplete")
        missing_current_snapshot_ref = dict(current)
        missing_current_snapshot_ref.pop("snapshot_ref")
        self.assertEqual(regression.check_baseline_currentness(baseline, missing_current_snapshot_ref)["status"], "unresolved")
        for invalid_ref in (None, "", 7):
            with self.subTest(invalid_snapshot_ref=invalid_ref):
                self.assertEqual(
                    regression.check_baseline_currentness(
                        {**baseline, "discovery_snapshot_ref": invalid_ref}, current
                    )["status"],
                    "incomplete",
                )
                self.assertEqual(
                    regression.check_baseline_currentness(
                        baseline, {**current, "snapshot_ref": invalid_ref}
                    )["status"],
                    "unresolved",
                )

        missing_baseline_scope = regression.check_baseline_currentness(
            {**baseline, "scope_identity": None}, current
        )
        self.assertEqual(missing_baseline_scope["status"], "incomplete")
        missing_current_scope = regression.check_baseline_currentness(
            baseline, {**current, "scope_identity": None}
        )
        self.assertEqual(missing_current_scope["status"], "unresolved")
        missing_baseline_revisions = regression.check_baseline_currentness(
            {**baseline, "source_revisions": None}, current
        )
        self.assertEqual(missing_baseline_revisions["status"], "incomplete")
        empty_baseline_revisions = regression.check_baseline_currentness(
            {**baseline, "source_revisions": [], "memberships": []}, current
        )
        self.assertEqual(empty_baseline_revisions["status"], "incomplete")

        missing_membership_dependency = {
            **baseline,
            "source_revisions": [revision for revision in revisions if revision["source_ref"] != "risk:RISK-001"],
        }
        self.assertEqual(regression.check_baseline_currentness(missing_membership_dependency, current)["status"], "incomplete")

    def test_baseline_fixture_population_provenance_and_template_shape(self):
        fixture_dir = REPO_ROOT / "skills" / "regression-testing" / "evals" / "output" / "cases" / "reg-out-001"
        fixture_text = (fixture_dir / "output.md").read_text(encoding="utf-8")
        baseline, errors = regression_validator._document(fixture_text)
        self.assertEqual(errors, [])
        expected = json.loads((fixture_dir / "expected.json").read_text(encoding="utf-8"))
        valid = regression_validator.validate(fixture_text, expected, "REG-OUT-001")
        self.assertTrue(all(assertion.status == "pass" for assertion in valid.assertions), valid.to_dict())

        missing_tc = dict(baseline)
        missing_tc["memberships"] = [item for item in baseline["memberships"] if item["tc_ref"] != "TC-003"]
        rendered = "```json\n" + json.dumps(missing_tc, ensure_ascii=False) + "\n```"
        result = regression_validator.validate(rendered, expected, "REG-D003-POPULATION-MISSING")
        statuses = {item.id: item.status for item in result.assertions}
        self.assertEqual(statuses["REG-D003"], "fail")

        extra_tc = dict(baseline)
        extra_tc["memberships"] = [
            *baseline["memberships"],
            {**baseline["memberships"][2], "tc_ref": "TC-004"},
        ]
        rendered = "```json\n" + json.dumps(extra_tc, ensure_ascii=False) + "\n```"
        result = regression_validator.validate(rendered, expected, "REG-D003-POPULATION-EXTRA")
        statuses = {item.id: item.status for item in result.assertions}
        self.assertEqual(statuses["REG-D003"], "fail")

        unresolved_membership = json.loads(json.dumps(baseline))
        unresolved_membership["memberships"][2]["decision"] = "unresolved"
        rendered = "```json\n" + json.dumps(unresolved_membership, ensure_ascii=False) + "\n```"
        result = regression_validator.validate(rendered, expected, "REG-D003-UNRESOLVED-COMPLETE")
        statuses = {item.id: item.status for item in result.assertions}
        self.assertEqual(statuses["REG-D003"], "fail")
        self.assertEqual(statuses["REG-D017"], "pass")

        for field in ("schema_version", "baseline_ref", "discovery_snapshot_ref", "scope_refs", "unresolved_tc_refs", "undecided_tc_refs"):
            with self.subTest(field=field):
                malformed = dict(baseline)
                malformed.pop(field)
                rendered = "```json\n" + json.dumps(malformed, ensure_ascii=False) + "\n```"
                result = regression_validator.validate(rendered, expected, f"REG-D017-MISSING-{field}")
                statuses = {item.id: item.status for item in result.assertions}
                self.assertEqual(statuses["REG-D017"], "fail")

        unresolved_complete = {**baseline, "undecided_tc_refs": ["TC-003"]}
        rendered = "```json\n" + json.dumps(unresolved_complete, ensure_ascii=False) + "\n```"
        result = regression_validator.validate(rendered, expected, "REG-D017-UNDECIDED-COMPLETE")
        statuses = {item.id: item.status for item in result.assertions}
        self.assertEqual(statuses["REG-D017"], "fail")

        missing_dependency = dict(baseline)
        missing_dependency["source_revisions"] = [
            revision for revision in baseline["source_revisions"] if revision["source_ref"] != "risk:RISK-001"
        ]
        rendered = "```json\n" + json.dumps(missing_dependency, ensure_ascii=False) + "\n```"
        result = regression_validator.validate(rendered, expected, "REG-D016-MISSING-MEMBERSHIP-DEPENDENCY")
        statuses = {item.id: item.status for item in result.assertions}
        self.assertEqual(statuses["REG-D016"], "fail")
        self.assertNotEqual(
            regression.check_baseline_currentness(missing_dependency, {
                "complete": True,
                "snapshot_ref": baseline["discovery_snapshot_ref"],
                "cases": [{"tc_ref": item["tc_ref"], "lifecycle_status": "current"} for item in baseline["memberships"]],
                "scope_identity": baseline["scope_identity"],
                "source_revisions": baseline["source_revisions"],
            })["status"],
            "current",
        )

        malformed_provenance = json.loads(json.dumps(baseline))
        malformed_provenance["memberships"][1]["source_refs"] = ["risk:RISK-001"]
        malformed_provenance["memberships"][1]["source_revisions"] = [
            {"source_ref": "risk:RISK-001", "revision": "r4"}
        ]
        rendered = "```json\n" + json.dumps(malformed_provenance, ensure_ascii=False) + "\n```"
        result = regression_validator.validate(rendered, expected, "REG-D016-MEMBERSHIP-REVISION-CONFLICT")
        statuses = {item.id: item.status for item in result.assertions}
        self.assertEqual(statuses["REG-D016"], "fail")
        self.assertEqual(
            regression.check_baseline_currentness(malformed_provenance, {
                "complete": True,
                "snapshot_ref": baseline["discovery_snapshot_ref"],
                "cases": [{"tc_ref": item["tc_ref"], "lifecycle_status": "current"} for item in baseline["memberships"]],
                "scope_identity": baseline["scope_identity"],
                "source_revisions": baseline["source_revisions"],
            })["status"],
            "incomplete",
        )

    def test_baseline_validator_rejects_missing_scope_and_projection_fields(self):
        fixture_path = REPO_ROOT / "skills" / "regression-testing" / "evals" / "output" / "cases" / "reg-out-001" / "output.md"
        fixture_text = fixture_path.read_text(encoding="utf-8")
        baseline, errors = regression_validator._document(fixture_text)
        self.assertEqual(errors, [])
        self.assertIsNotNone(baseline)

        for field in ("scope_identity", "member_tc_refs", "one_off_tc_refs", "source_revisions"):
            with self.subTest(field=field):
                candidate = dict(baseline)
                candidate.pop(field)
                rendered = "```json\n" + json.dumps(candidate, ensure_ascii=False) + "\n```"
                result = regression_validator.validate(rendered, {"artifact_type": "baseline"}, f"REG-D016-MISSING-{field}")
                statuses = {item.id: item.status for item in result.assertions}
                self.assertEqual(statuses["REG-D016"], "fail")

        candidate = dict(baseline)
        candidate["member_tc_refs"] = []
        rendered = "```json\n" + json.dumps(candidate, ensure_ascii=False) + "\n```"
        result = regression_validator.validate(rendered, {"artifact_type": "baseline"}, "REG-D016-MISMATCH")
        statuses = {item.id: item.status for item in result.assertions}
        self.assertEqual(statuses["REG-D016"], "fail")

        candidate = dict(baseline)
        candidate["one_off_tc_refs"] = []
        rendered = "```json\n" + json.dumps(candidate, ensure_ascii=False) + "\n```"
        result = regression_validator.validate(rendered, {"artifact_type": "baseline"}, "REG-D016-ONE-OFF-MISMATCH")
        statuses = {item.id: item.status for item in result.assertions}
        self.assertEqual(statuses["REG-D016"], "fail")

        for field, value in (("scope_identity", " "), ("member_tc_refs", "TC-001")):
            with self.subTest(field=field, value=value):
                candidate = dict(baseline)
                candidate[field] = value
                rendered = "```json\n" + json.dumps(candidate, ensure_ascii=False) + "\n```"
                result = regression_validator.validate(rendered, {"artifact_type": "baseline"}, f"REG-D016-INVALID-{field}")
                statuses = {item.id: item.status for item in result.assertions}
                self.assertEqual(statuses["REG-D016"], "fail")

    def test_route_state_uses_actual_start_and_preserves_source_result(self):
        routes = regression.validate_required_routes([
            {"tc_ref": "TC-001", "route_type": "manual", "route_ref": "manual"},
            {"tc_ref": "TC-001", "route_type": "e2e", "route_ref": "e2e:one", "e2e_testware_ref": "E2E-1"},
            {"tc_ref": "TC-002", "route_type": "e2e", "route_ref": "e2e:two", "e2e_testware_ref": "E2E-2"},
        ])
        self.assertTrue(routes["valid"])
        invalid = regression.validate_required_routes([{"tc_ref": "TC-001", "route_type": "blocked", "route_ref": "blocked"}])
        self.assertFalse(invalid["valid"])

        # Supply execution refs without changing route kind / state contract.
        run = {"required_routes": [
            {**routes["routes"][0], "execution_ref": "RUN-M"},
            {**routes["routes"][1], "execution_ref": "RUN-E1"},
            {**routes["routes"][2], "execution_ref": "RUN-E2"},
            {"tc_ref": "TC-003", "route_type": "manual", "route_ref": "manual:003", "execution_ref": "RUN-M3"},
        ]}
        activity = regression.project_activity(run, {
            "RUN-M": {"start_state": "開始済み", "actual_start_confirmed": True, "result_finalized": True, "source_result": "FAIL", "evidence_refs": ["ev:m"]},
            "RUN-E1": {"start_state": "未開始", "actual_start_confirmed": False, "result_finalized": False, "source_result": "未実行", "blocked": True},
            "RUN-E2": {"start_state": "開始済み", "actual_start_confirmed": True, "result_finalized": True, "source_result": "判定不能", "evidence_refs": ["ev:e"]},
            "RUN-M3": {"start_state": "未開始", "actual_start_confirmed": False, "result_finalized": False, "source_result": "未実行"},
        })
        self.assertEqual(activity["tc_execution_state"], {"TC-001": "blocked", "TC-002": "executed", "TC-003": "unexecuted"})
        self.assertTrue(activity["route_results"][0]["executed"])
        self.assertFalse(activity["route_results"][1]["executed"])
        self.assertEqual(activity["route_results"][0]["source_result"], "FAIL")
        self.assertEqual(activity["counts"]["executed_tc_count"], 1)
        self.assertEqual(activity["counts"]["blocked_tc_count"], 1)
        self.assertEqual(activity["counts"]["unexecuted_tc_count"], 1)

    def test_activity_completion_waits_for_owner_result_finalization(self):
        one_route = {"required_routes": [{"tc_ref": "TC-101", "route_type": "manual", "route_ref": "manual:101", "execution_ref": "RUN-101"}]}
        pending_source = {"RUN-101": {"start_state": "開始済み", "actual_start_confirmed": True, "result_finalized": False}}
        pending = regression.project_activity(one_route, pending_source)
        self.assertEqual(pending["tc_execution_state"]["TC-101"], "executed")
        self.assertEqual(pending["activity_state"], "実行中")
        self.assertFalse(pending["route_results"][0]["result_finalized"])
        update = regression.update_activity(
            {**pending, "scope_identity": "scope-1", "snapshot_ref": "snapshot-1"},
            {**regression.project_activity(one_route, {"RUN-101": {"start_state": "開始済み", "actual_start_confirmed": True, "result_finalized": True, "source_result": "PASS"}}), "scope_identity": "scope-1", "snapshot_ref": "snapshot-1"},
        )
        self.assertEqual(update["status"], "update_allowed")

        for owner_result in ("PASS", "FAIL", "判定不能"):
            with self.subTest(owner_result=owner_result):
                source = {"RUN-101": {"start_state": "開始済み", "actual_start_confirmed": True, "result_finalized": True, "source_result": owner_result}}
                completed = regression.project_activity(one_route, source, cleanup_status="対象なし")
                self.assertEqual(completed["tc_execution_state"]["TC-101"], "executed")
                self.assertEqual(completed["activity_state"], "完了")
                self.assertEqual(completed["route_results"][0]["source_result"], owner_result)

        multiple_routes = {"required_routes": [
            {"tc_ref": "TC-102", "route_type": "manual", "route_ref": "manual:102", "execution_ref": "RUN-102M"},
            {"tc_ref": "TC-102", "route_type": "e2e", "route_ref": "e2e:102", "execution_ref": "RUN-102E", "e2e_testware_ref": "E2E-102"},
        ]}
        partial_results = regression.project_activity(multiple_routes, {
            "RUN-102M": {"start_state": "開始済み", "actual_start_confirmed": True, "result_finalized": True, "source_result": "FAIL"},
            "RUN-102E": {"start_state": "開始済み", "actual_start_confirmed": True, "result_finalized": False},
        })
        self.assertEqual(partial_results["tc_execution_state"]["TC-102"], "executed")
        self.assertEqual(partial_results["activity_state"], "実行中")

        def d011_status(activity: dict, source_executions: dict) -> str:
            doc = {
                **activity,
                "artifact_type": "activity",
                "activity_ref": "ACT-REG-1",
                "scope_identity": "scope-1",
                "snapshot_ref": "snapshot-1",
                "source_executions": source_executions,
                "counts": {"auxiliary_testware_count": 0},
                "auxiliary_route_results": [],
            }
            rendered = "```json\n" + json.dumps(doc, ensure_ascii=False) + "\n```"
            result = regression_validator.validate(rendered, {}, "REG-D011-UNIT")
            return next(item.status for item in result.assertions if item.id == "REG-D011")

        invalid_completed = {**pending, "activity_state": "完了"}
        self.assertEqual(d011_status(invalid_completed, pending_source), "fail")
        final_source = {"RUN-101": {"start_state": "開始済み", "actual_start_confirmed": True, "result_finalized": True, "source_result": "FAIL"}}
        self.assertEqual(d011_status(regression.project_activity(one_route, final_source), final_source), "pass")

    def test_auxiliary_testware_needs_explicit_scope_and_is_separate(self):
        rejected = regression.select_auxiliary_testware(requested_refs=["E2E-9"], user_explicit_refs=[], policy_refs=[], available_refs=["E2E-9"])
        self.assertEqual(rejected["status"], "unresolved")
        accepted = regression.select_auxiliary_testware(requested_refs=["E2E-9"], user_explicit_refs=[], policy_refs=["E2E-9"], available_refs=["E2E-9"])
        self.assertEqual(accepted["selected_refs"], ["E2E-9"])
        self.assertEqual(accepted["tc_member_count"], 0)

    def test_activity_immutability_and_listing_completeness(self):
        completed = {"activity_state": "完了", "scope_identity": "s1", "snapshot_ref": "d1"}
        self.assertEqual(regression.update_activity(completed, completed)["reason"], "completed_activity_is_immutable")
        changed = regression.update_activity({"activity_state": "実行中", "scope_identity": "s1", "snapshot_ref": "d1"}, {"scope_identity": "s2", "snapshot_ref": "d2"})
        self.assertEqual(changed["status"], "new_activity_required")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "ACT-2.json").write_text("{}", encoding="utf-8")
            (root / "ACT-1.json").write_text("{}", encoding="utf-8")
            self.assertEqual(regression.scan_activity_files(root)["activity_refs"], ["ACT-1", "ACT-2"])
            self.assertFalse(regression.scan_activity_files(root, listing_complete=False)["complete"])


class ExploratoryRuntimeTests(unittest.TestCase):
    def charter(self):
        return {
            "purpose": "verify one unresolved behavior", "in_scope": ["checkout"], "out_of_scope": ["payment"],
            "source_refs": ["symptom:S-1"], "focus_refs": [], "timebox_or_exit_condition": "20 minutes",
            "allowed_origins": ["https://staging.example.test"], "allowed_operations": ["navigate", "invalidate_session"],
            "side_effect_operations": ["invalidate_session"], "side_effect_scope": "session only",
            "side_effect_action_definition": "one session invalidation", "side_effect_maximum": 1,
            "cleanup_plan": "restore session", "evidence_policy": "retain refs, never credentials", "block_conditions": ["state unavailable"],
            "symptom": "redirect to login mid-operation",
        }

    def test_mode_and_charter_are_explicit(self):
        charter = self.charter()
        self.assertTrue(exploratory.validate_charter("investigation", charter)["valid"])
        no_hypothesis = dict(charter)
        no_hypothesis.pop("symptom")
        self.assertIn("investigation_requires_symptom_or_hypothesis", exploratory.validate_charter("investigation", no_hypothesis)["issues"])
        self.assertIn("invalid_mode", exploratory.validate_charter("research", charter)["issues"])

    def test_origin_and_side_effect_limits_fail_closed(self):
        charter = self.charter()
        self.assertEqual(exploratory.authorize_operation(charter, target_url="https://staging.example.test/orders", operation="navigate", prior_side_effect_attempts=0)["status"], "allowed")
        self.assertEqual(exploratory.authorize_operation(charter, target_url="https://staging.example.test.evil/orders", operation="navigate", prior_side_effect_attempts=0)["status"], "blocked")
        self.assertEqual(exploratory.authorize_operation(charter, target_url="https://staging.example.test", operation="invalidate_session", prior_side_effect_attempts=1, uncertain_previous_attempt=True)["reason"], "side_effect_limit_reached")
        attempt = {"attempt_ref": "ATT-1", "operation": "invalidate_session", "side_effect": True, "outcome": "unknown"}
        recorded = exploratory.record_attempt(charter, [], attempt)
        self.assertTrue(recorded["retry_without_state_check"])
        self.assertEqual(recorded["side_effect_count"], 1)
        attempt2 = {"attempt_ref": "ATT-2", "operation": "invalidate_session", "side_effect": True, "outcome": "completed"}
        self.assertEqual(exploratory.record_attempt(charter, recorded["attempts"], attempt2)["reason"], "side_effect_limit_reached")

    def test_cleanup_block_resume_and_completed_immutability(self):
        session = {"session_ref": "SES-1", "state": "実行中", "charter_snapshot_identity": exploratory.charter_identity(self.charter(), {"build": "b1"}, {"role": "viewer"})}
        same = exploratory.can_resume(session, self.charter(), {"build": "b1"}, {"role": "viewer"})
        self.assertEqual(same["status"], "resume_allowed")
        changed = exploratory.can_resume(session, self.charter(), {"build": "b2"}, {"role": "viewer"})
        self.assertEqual(changed["status"], "new_session_required")
        self.assertEqual(exploratory.complete_session(session, exit_condition_reached=True, cleanup={"required": True, "status": "未確認"})["status"], "blocked")
        complete = exploratory.complete_session(session, exit_condition_reached=True, cleanup={"required": False, "status": "対象なし"})
        self.assertEqual(complete["status"], "complete")
        self.assertEqual(exploratory.complete_session(complete["session"], exit_condition_reached=True, cleanup={"required": False, "status": "対象なし"})["reason"], "completed_session_is_immutable")
        self.assertEqual(exploratory.complete_session(session, exit_condition_reached=True, cleanup={"required": True, "status": "意図的に残した状態"}, residual_side_effects=["record-1"])["status"], "blocked")


class KnowledgeRuntimeTests(unittest.TestCase):
    def entry(self, identity=None):
        identity = identity or {"kind": "test_environment", "scope_refs": ["project:checkout"], "subject": "staging-job-delay"}
        return {
            "schema_version": "1", "entry_ref": knowledge.canonical_entry_ref(identity), "identity": identity,
            "kind": "test_environment", "content": "Wait for authoritative staging job completion state.",
            "scope_refs": ["project:checkout"], "applicability": {"environment": ["staging"], "version": "job-v3"},
            "provenance": [{"ref": "activity:ACT-1", "revision": "r1"}],
            "currentness_dependencies": [{"ref": "config:job", "revision": "r3"}],
            "last_verified": {"at": "2026-09-27", "condition": "staging/job-v3"},
            "state": "有効", "replacement_ref": None, "related_qa_refs": ["TC-1"],
        }

    def test_entry_identity_is_stable_and_update_requires_native_cas(self):
        identity = {"subject": "delay", "scope_refs": ["project:a"], "kind": "test_environment"}
        reversed_identity = {"kind": "test_environment", "subject": "delay", "scope_refs": ["project:a"]}
        self.assertEqual(knowledge.canonical_entry_ref(identity), knowledge.canonical_entry_ref(reversed_identity))
        self.assertNotEqual(knowledge.canonical_entry_ref(identity), knowledge.canonical_entry_ref({**identity, "subject": "other"}))
        self.assertEqual(knowledge.plan_update(expected_entry_revision="r1", native_atomic_conditional_write=False)["status"], "blocked")
        self.assertEqual(knowledge.plan_update(expected_entry_revision="r1", native_atomic_conditional_write=True)["status"], "conditional_write_required")
        self.assertFalse(knowledge.handle_update_conflict(target_entry_revision_changed=True, different_entry_only_changed=False)["auto_merge"])
        self.assertEqual(knowledge.plan_replacement(old_entry_ref="KN-1", new_entry_ref="KN-2", native_atomic_multi_entry_update=False)["status"], "blocked")

    def test_same_entry_concurrent_updates_fail_closed_without_provider_cas(self):
        with ThreadPoolExecutor(max_workers=2) as executor:
            decisions = list(executor.map(lambda _: knowledge.plan_update(expected_entry_revision="r1", native_atomic_conditional_write=False), range(2)))
        self.assertEqual([decision["status"] for decision in decisions], ["blocked", "blocked"])
        conflict = knowledge.handle_update_conflict(target_entry_revision_changed=True, different_entry_only_changed=False)
        self.assertEqual(conflict["status"], "reread_and_semantic_reevaluation")
        self.assertFalse(conflict["auto_merge"])

    def test_same_semantic_identity_concurrent_create_uses_one_canonical_file(self):
        entry = self.entry()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "knowledge"
            with ThreadPoolExecutor(max_workers=8) as executor:
                results = list(executor.map(lambda _: knowledge.create_entry(root, entry, complete_root_snapshot=True, atomic_create_if_absent_available=True, current_dependencies={"config:job": "r3"}), range(8)))
            self.assertEqual(sum(result["status"] == "created" for result in results), 1)
            self.assertEqual({result["entry_ref"] for result in results}, {entry["entry_ref"]})
            self.assertEqual(len(list(root.glob("*.md"))), 1)
            read = knowledge.read_entry(root, entry["entry_ref"], expected_revision=results[0]["entry_revision"])
            self.assertEqual(read["status"], "current")
            self.assertFalse(read["historical_revision_available"])
            self.assertEqual(knowledge.read_entry(root, entry["entry_ref"], expected_revision="sha256:old")["reason"], "historical_revision_unavailable")

    def test_read_entry_enforces_canonical_ref_path_and_body_identity(self):
        entry = self.entry()
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            root = base / "knowledge"
            root.mkdir()
            canonical_path = root / f"{entry['entry_ref']}.md"
            canonical_path.write_bytes(knowledge.render_entry(entry))
            self.assertEqual(knowledge.read_entry(root, entry["entry_ref"])["status"], "current")

            outside = base / "outside.md"
            outside.write_bytes(knowledge.render_entry(entry))
            (root / "KN-..").mkdir()
            malformed_refs = [
                "KN-../../outside",
                "KN-../../../outside",
                "KN-..\\..\\..\\outside",
                "KN-abc",
                "KN-" + "a" * 63,
                "KN-" + "a" * 65,
                "KN-" + "g" * 64,
                "KN-" + "A" * 64,
            ]
            for invalid_ref in malformed_refs:
                with self.subTest(entry_ref=invalid_ref):
                    self.assertEqual(knowledge.read_entry(root, invalid_ref)["status"], "blocked")
                    self.assertEqual(outside.read_bytes(), knowledge.render_entry(entry))

            body_ref_mismatch = {**entry, "entry_ref": knowledge.canonical_entry_ref({"kind": "other"})}
            canonical_path.write_bytes(knowledge.render_entry(body_ref_mismatch))
            read = knowledge.read_entry(root, entry["entry_ref"])
            self.assertEqual((read["status"], read["reason"]), ("blocked", "entry_identity_mismatch"))

            identity_mismatch = {**entry, "identity": {"kind": "other"}}
            canonical_path.write_bytes(knowledge.render_entry(identity_mismatch))
            read = knowledge.read_entry(root, entry["entry_ref"])
            self.assertEqual((read["status"], read["reason"]), ("blocked", "entry_identity_mismatch"))

    def test_distinct_identities_do_not_contend_and_incomplete_storage_blocks(self):
        first = self.entry()
        second = self.entry({"kind": "test_environment", "scope_refs": ["project:checkout"], "subject": "different-job"})
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "knowledge"
            with ThreadPoolExecutor(max_workers=2) as executor:
                results = list(executor.map(lambda entry: knowledge.create_entry(root, entry, complete_root_snapshot=True, atomic_create_if_absent_available=True, current_dependencies={"config:job": "r3"}), [first, second]))
            self.assertEqual([item["status"] for item in results], ["created", "created"])
            self.assertEqual(len(list(root.glob("*.md"))), 2)
            self.assertFalse(knowledge.scan_knowledge_root(root, max_entries=1)["complete"])
            self.assertEqual(knowledge.create_entry(root, first, complete_root_snapshot=False, atomic_create_if_absent_available=True, current_dependencies={"config:job": "r3"})["status"], "blocked")
            self.assertEqual(knowledge.create_entry(root, first, complete_root_snapshot=True, atomic_create_if_absent_available=False, current_dependencies={"config:job": "r3"})["status"], "blocked")
            unverified = {**first, "state": "要再検証"}
            self.assertEqual(knowledge.create_entry(root, unverified, complete_root_snapshot=True, atomic_create_if_absent_available=True, current_dependencies={"config:job": "r3"})["status"], "blocked")

    def test_currentness_lookup_ignores_unrelated_updates_but_excludes_stale_entry(self):
        entry = self.entry()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            created = knowledge.create_entry(root, entry, complete_root_snapshot=True, atomic_create_if_absent_available=True, current_dependencies={"config:job": "r3"})
            current_entry = {**entry, "entry_revision": created["entry_revision"]}
            found = knowledge.lookup([current_entry], scope_refs={"project:checkout"}, kind="test_environment", environment="staging", version="job-v3", current_dependencies={"config:job": "r3", "other:entry": "r2"}, listing_complete=True)
            self.assertEqual(found["status"], "complete")
            self.assertEqual(len(found["entries"]), 1)
            stale = knowledge.lookup([current_entry], scope_refs={"project:checkout"}, kind="test_environment", environment="staging", version="job-v3", current_dependencies={"config:job": "r4"}, listing_complete=True)
            self.assertEqual(stale["entries"], [])
            self.assertEqual(stale["historical_excluded_refs"], [entry["entry_ref"]])
            self.assertFalse(knowledge.lookup([current_entry], scope_refs=set(), kind=None, environment=None, version=None, current_dependencies={}, listing_complete=False)["complete"])


class WorkflowArtifactGraphTests(unittest.TestCase):
    def project_text(self, scope="checkout", root=".qa/knowledge"):
        return f"""# Context\n\n<!-- qa-context-field:start key=qa.regression_scope type=ordered_text -->\n{scope}\n<!-- qa-context-field:end -->\n\n<!-- qa-context-field:start key=qa.knowledge_root type=path -->\n{root}\n<!-- qa-context-field:end -->\n"""

    def test_project_context_stable_keys_normalize_and_compare_only_used_fields(self):
        old_text = self.project_text()
        old = workflow.parse_project_context(old_text)
        self.assertTrue(old["complete"])
        snapshot = {**old, "used_fields": ["qa.regression_scope"]}
        reordered = workflow.parse_project_context(self.project_text(root=".qa/knowledge-v2").replace("checkout", " checkout "))
        self.assertEqual(workflow.compare_used_context(snapshot, reordered)["status"], "current")
        changed = workflow.parse_project_context(self.project_text(scope="refund"))
        self.assertEqual(workflow.compare_used_context(snapshot, changed)["status"], "stale")
        # Explicit duplicate key markers are unresolved even when their values match.
        block = "<!-- qa-context-field:start key=qa.knowledge_root type=path -->\n.qa/knowledge\n<!-- qa-context-field:end -->"
        duplicate = workflow.parse_project_context(old_text + "\n" + block)
        self.assertFalse(duplicate["complete"])
        self.assertIn("duplicate_key", {item["reason"] for item in duplicate["unresolved"]})
        missing = workflow.parse_project_context("<!-- qa-context-field:start key=qa.workflow_state_root type=path -->\nroot")
        self.assertEqual(missing["status"] if "status" in missing else missing["complete"], False)
        required = workflow.validate_required_context_fields(workflow.parse_project_context(self.project_text(root="（未設定）")), ["qa.knowledge_root"])
        self.assertEqual(required["status"], "unresolved")

    def test_workflow_states_have_canonical_identity_and_atomic_create(self):
        ref = workflow.new_workflow_ref()
        other = workflow.new_workflow_ref()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "states"
            with ThreadPoolExecutor(max_workers=8) as executor:
                results = list(executor.map(lambda _: workflow.create_workflow_state(root, ref, {"overall_state": "実行中"}), range(8)))
            self.assertEqual(sum(item["status"] == "created" for item in results), 1)
            self.assertEqual(workflow.canonical_state_path(root, ref), Path(root) / f"{ref}.json")
            self.assertEqual(workflow.create_workflow_state(root, other, {"overall_state": "実行中"})["status"], "created")
            self.assertEqual(len(list(root.glob("*.json"))), 2)
            revision = next(item["state_revision"] for item in results if item["status"] == "created")
            self.assertEqual(workflow.read_workflow_state(root, ref, expected_revision=revision)["status"], "current")
            self.assertEqual(workflow.state_update_decision(revision, revision, False)["status"], "blocked")
            self.assertEqual(workflow.state_update_decision(revision, "new", True)["status"], "conflict")
            self.assertEqual(workflow.verify_historical_revision(revision, False)["status"], "blocked")

    def test_same_workflow_concurrent_resume_blocks_state_updates_without_provider_cas(self):
        with ThreadPoolExecutor(max_workers=2) as executor:
            decisions = list(executor.map(lambda _: workflow.state_update_decision("r1", "r1", False), range(2)))
        self.assertEqual([decision["status"] for decision in decisions], ["blocked", "blocked"])
        ready_for_provider = workflow.state_update_decision("r1", "r1", True)
        self.assertEqual(ready_for_provider["status"], "conditional_write_required")

    def test_pre_start_claim_and_resource_reservation_serialize_mutable_work(self):
        workflow_ref = workflow.new_workflow_ref()
        with tempfile.TemporaryDirectory() as temp:
            workflow_state_root = Path(temp) / "states"
            with ThreadPoolExecutor(max_workers=8) as executor:
                claims = list(executor.map(lambda _: workflow.claim_mutable_operation(workflow_state_root, workflow_ref, "browser:save-order"), range(8)))
            self.assertEqual(sum(item["status"] == "claim_acquired" for item in claims), 1)
            winner = next(item for item in claims if item["status"] == "claim_acquired")
            self.assertTrue(winner["may_start"])
            expected_claim_path = workflow_state_root / "claims" / f"{workflow.content_identity({'workflow_ref': workflow_ref, 'operation_ref': 'browser:save-order'})}.json"
            self.assertEqual(Path(winner["path"]), expected_claim_path)
            self.assertTrue(expected_claim_path.is_file())
            self.assertEqual(workflow.recover_claim(owner_source_state=None, cleanup_confirmed=False, expected_claim_revision=winner["claim_revision"], native_atomic_conditional_release=True)["status"], "blocked")
            self.assertEqual(workflow.recover_claim(owner_source_state="not_started", cleanup_confirmed=True, expected_claim_revision=winner["claim_revision"], native_atomic_conditional_release=False)["status"], "blocked")
            self.assertEqual(workflow.recover_claim(owner_source_state="not_started", cleanup_confirmed=True, expected_claim_revision=winner["claim_revision"], native_atomic_conditional_release=True)["status"], "conditional_release_required")

            reservation_root = Path(temp) / "reservations"
            with ThreadPoolExecutor(max_workers=2) as executor:
                reservations = list(executor.map(lambda owner: workflow.reserve_shared_resource(reservation_root, "resource:shared-user-1", owner, native_atomic_conditional_release=True), [workflow_ref, workflow.new_workflow_ref()]))
            self.assertEqual(sum(item["status"] == "reserved" for item in reservations), 1)
            reservation = next(item for item in reservations if item["status"] == "reserved")
            reservation_data = json.loads(Path(reservation["reservation_ref"]).read_text(encoding="utf-8"))
            owner_ref = reservation_data["workflow_ref"]
            self.assertEqual(workflow.release_shared_resource(current_workflow_ref=owner_ref, expected_workflow_ref=owner_ref, expected_reservation_revision=reservation["reservation_revision"], current_reservation_revision=reservation["reservation_revision"], native_atomic_conditional_release=False, owner_state_verified=True, owner_execution_state="complete", cleanup_confirmed=True)["status"], "blocked")
            self.assertEqual(workflow.release_shared_resource(current_workflow_ref="other", expected_workflow_ref=owner_ref, expected_reservation_revision=reservation["reservation_revision"], current_reservation_revision=reservation["reservation_revision"], native_atomic_conditional_release=True, owner_state_verified=True, owner_execution_state="complete", cleanup_confirmed=True)["reason"], "reservation_owner_mismatch")
            self.assertEqual(workflow.reserve_shared_resource(reservation_root, "resource:isolation", workflow_ref, native_atomic_conditional_release=False, isolated=True)["status"], "not_required")
            external = workflow.reserve_shared_resource(reservation_root, "resource:external", workflow_ref, native_atomic_conditional_release=False, external_reservation="external:reservation-1", external_reservation_acquired=True, external_reservation_revision="provider:revision-1")
            self.assertEqual(external["status"], "reserved")
            self.assertEqual(external["provider"], "existing_external_reservation")

            unsafe_resource = "resource:local-without-release"
            unsafe_target = reservation_root / f"{workflow.content_identity({'resource_ref': unsafe_resource})}.json"
            unsafe_local = workflow.reserve_shared_resource(reservation_root, unsafe_resource, workflow_ref, native_atomic_conditional_release=False)
            self.assertEqual((unsafe_local["status"], unsafe_local["reason"]), ("blocked", "atomic_conditional_release_unavailable"))
            self.assertFalse(unsafe_target.exists())
            safe_local = workflow.reserve_shared_resource(reservation_root, "resource:local-with-release", workflow_ref, native_atomic_conditional_release=True)
            self.assertEqual(safe_local["status"], "reserved")

    def test_partial_update_requires_owner_scope_dependency_and_cas_proof(self):
        base = {"owner_boundary_defined": True, "same_target_identity": True, "update_scopes_disjoint": True, "upstream_dependencies_unchanged": True, "native_atomic_conditional_write": True, "expected_revision": "r1"}
        self.assertEqual(workflow.partial_update_decision(**base)["status"], "conditional_write_required")
        self.assertEqual(workflow.partial_update_decision(**{**base, "same_target_identity": False})["status"], "blocked")
        self.assertEqual(workflow.partial_update_decision(**{**base, "native_atomic_conditional_write": False})["status"], "blocked")

    def test_provider_helper_failure_is_blocked_not_misreported_as_conflict(self):
        with tempfile.TemporaryDirectory() as temp:
            parent = Path(temp) / "not-a-directory"
            parent.write_text("file", encoding="utf-8")
            result = workflow.create_if_absent(parent / "state.json", b"{}")
            self.assertEqual(result["status"], "blocked")
            self.assertFalse(result["atomic"])

    def test_qa_workflow_contract_requires_artifact_graph_helper_at_checkpoints(self):
        skill = (REPO_ROOT / "skills" / "qa-workflow" / "SKILL.md").read_text(encoding="utf-8")
        guidance = (REPO_ROOT / "skills" / "qa-workflow" / "references" / "guidance.md").read_text(encoding="utf-8")
        workflow_template = (REPO_ROOT / "skills" / "qa-workflow" / "assets" / "workflow-state-template.md").read_text(encoding="utf-8")
        project_template = (REPO_ROOT / "skills" / "qa-workflow" / "assets" / "project-context-template.md").read_text(encoding="utf-8")

        resources = skill.split("## リソース", 1)[1].split("\n## ", 1)[0]
        self.assertIn("scripts/artifact_graph.py", resources)
        helper_contract = skill.split("## 継続管理workflowの決定論的処理", 1)[1].split("\n## ", 1)[0]
        for operation in ("stable key", "used-field currentness", "canonical path", "fixed-root scan", "CAS capability gate", "pre-start claim", "shared resource reservation"):
            with self.subTest(operation=operation):
                self.assertIn(operation, helper_contract)
        self.assertRegex(helper_contract, r"incomplete.{0,30}unresolved.{0,30}blocked")
        self.assertIn("LLM fallback", helper_contract)

        checkpoint_contract = guidance.split("## 継続管理workflowのproduction helper checkpoint", 1)[1].split("\n## ", 1)[0]
        for checkpoint in ("### workflow開始 / resume", "### mutable operation開始直前", "### shared resource使用前", "### current完了直前 / current成果物再利用直前"):
            with self.subTest(checkpoint=checkpoint):
                self.assertIn(checkpoint, checkpoint_contract)
        for operation in ("parse_project_context", "validate_required_context_fields", "canonical_state_path", "create_workflow_state", "compare_used_context", "claim_mutable_operation(workflow_state_root", "reserve_shared_resource", "scan_fixed_root", "state_update_decision"):
            with self.subTest(operation=operation):
                self.assertIn(operation, checkpoint_contract)
        self.assertIn("qa.workflow_state_root/claims/", workflow_template)
        self.assertIn("qa.reservation_root", workflow_template)
        self.assertNotIn("qa.claim_root", project_template)


class SQLiteWcagWorkflowStateTests(unittest.TestCase):
    def setUp(self):
        self.wcag_scripts = REPO_ROOT / "skills" / "wcag-conformance-evaluation" / "scripts"
        sys.path.insert(0, str(self.wcag_scripts))
        import wcag_em_structure
        import wcag_criterion_plan
        self.structure = wcag_em_structure
        self.criterion_plan = wcag_criterion_plan
        self.context = {
            "project_context_ref": "PROJECT-CONTEXT-001",
            "project_context_revision": "c" * 64,
            "project_context_fingerprint": "sha256:" + "d" * 64,
            "workflow_state_root_content_identity": "e" * 64,
        }

    def evaluation(self, *, revision="rev-7", level="AA"):
        inputs = {
            "artifact_ref": "WCAG-EVAL-001", "artifact_revision": revision,
            "evaluator": "EVALUATOR-001", "evaluation_date": "2026-10-10",
            "live_web_target": "https://fixture.test/", "commissioner": "COMMISSIONER-001",
            "wcag_version": "2.2", "level": level, "product_scope": "Fixture product",
            "product_enclosure": "PRODUCT-SCOPE-001", "accessibility_support_baseline": ["BASELINE-1"],
            "browser_user_agent_baseline": ["BROWSER-1"], "role_permission_environment": ["ENV-1"],
            "side_effect_scope": "fixture only", "cleanup_scope": "reset fixture",
            "evaluation_period": "2026-10-10",
        }
        initialization = self.structure.initialize_evaluation(inputs)
        scope = self.structure.materialize_scope_coverage([
            {"scope_key": key, "decision": "out-of-product", "reason": "not present in fixture",
             "evidence_refs": [f"E-SCOPE-{index}"]}
            for index, key in enumerate(self.structure.SCOPE_ROWS, 1)
        ])
        samples = [
            {"sample_ref": "SAMPLE-001", "sample_kind": "structured",
             "identity_fingerprint": "sha256:" + "a" * 64,
             "target_identity": "hmac-sha256:" + "1" * 64},
            {"sample_ref": "SAMPLE-002", "sample_kind": "random",
             "identity_fingerprint": "sha256:" + "b" * 64,
             "target_identity": "hmac-sha256:" + "2" * 64},
        ]
        variations = [
            {"sample_ref": "SAMPLE-001", "variation_ref": "VAR-001",
             "identity_fingerprint": "sha256:" + "3" * 64},
            {"sample_ref": "SAMPLE-001", "variation_ref": "VAR-002",
             "identity_fingerprint": "sha256:" + "4" * 64},
            {"sample_ref": "SAMPLE-002", "variation_ref": "VAR-003",
             "identity_fingerprint": "sha256:" + "5" * 64},
        ]
        memberships = {"SAMPLE-001": "PROCESS-001"}
        plan = self.criterion_plan.materialize_plan(
            wcag_version="2.2", level=level, samples=samples, variations=variations,
            process_memberships=memberships, evaluation_ref="WCAG-EVAL-001", evaluation_revision=revision,
        )
        sources = [
            {"artifact_ref": "WCAG-EVAL-001", "artifact_revision": revision, "purpose": "evaluation"},
            {"artifact_ref": "PRODUCT-SCOPE-001", "artifact_revision": "scope-r1", "purpose": "scope"},
            {"artifact_ref": "SAMPLE-SELECTION-001", "artifact_revision": "samples-r1", "purpose": "sample-selection"},
            {"artifact_ref": "VARIATION-SET-001", "artifact_revision": "variation-r1", "purpose": "variation"},
            {"artifact_ref": "PROCESS-001", "artifact_revision": "process-r1", "purpose": "process"},
        ]
        return inputs, initialization, scope, sources, plan

    def register(self, root: Path, workflow_ref: str, *, revision="rev-7", level="AA", context=None,
                 previous_revision=None, sources_override=None, plan_override=None):
        inputs, initialization, scope, sources, plan = self.evaluation(revision=revision, level=level)
        return workflow.register_wcag_evaluation_plan(
            root, workflow_ref, evaluation_initialization=initialization, evaluation_inputs=inputs,
            product_scope_ref="PRODUCT-SCOPE-001", scope_coverage=scope,
            source_artifacts=sources_override or sources, canonical_criterion_plan=plan_override or plan,
            previous_evaluation_revision=previous_revision, **(context or self.context),
        ), (inputs, initialization, scope, sources, plan)

    def test_sqlite_provider_uses_atomic_revision_compare_and_reread(self):
        import threading
        workflow_ref = workflow.new_workflow_ref()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "states"
            created = workflow.create_sqlite_workflow_state(root, workflow_ref, {"overall_state": "実行中"})
            self.assertEqual(created["status"], "created")
            self.assertEqual(created["state_revision"], "sqlite:1")
            barrier = threading.Barrier(2)

            def update(value):
                barrier.wait()
                return workflow.conditional_write_sqlite_workflow_state(
                    root, workflow_ref, created["state_revision"], {"overall_state": value}
                )

            with ThreadPoolExecutor(max_workers=2) as executor:
                outcomes = list(executor.map(update, ("完了", "部分完了")))
            self.assertEqual(sum(row["status"] == "written" for row in outcomes), 1)
            self.assertEqual(sum(row["status"] == "conflict" for row in outcomes), 1)
            reread = workflow.read_sqlite_workflow_state(root, workflow_ref)
            self.assertEqual(reread["status"], "current")
            self.assertEqual(reread["state_revision"], "sqlite:2")
            self.assertIn(reread["state"]["overall_state"], {"完了", "部分完了"})

    def test_wcag_canonical_plan_is_immutable_per_revision_and_context(self):
        workflow_ref = workflow.new_workflow_ref()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "states"
            registered, data = self.register(root, workflow_ref)
            self.assertEqual(registered["status"], "registered")
            inputs, initialization, scope, sources, plan = data
            # A lower level at the same evaluation revision is internally valid but conflicts with the saved plan.
            narrowed_inputs, narrowed_init, narrowed_scope, narrowed_sources, narrowed_plan = self.evaluation(level="A")
            narrowed = workflow.register_wcag_evaluation_plan(
                root, workflow_ref, evaluation_initialization=narrowed_init,
                evaluation_inputs=narrowed_inputs, product_scope_ref="PRODUCT-SCOPE-001",
                scope_coverage=narrowed_scope, source_artifacts=narrowed_sources,
                canonical_criterion_plan=narrowed_plan, **self.context,
            )
            self.assertEqual(narrowed["status"], "conflict")

            # A changed selected-sample set cannot be re-registered under the same revision.
            one_sample_plan = self.criterion_plan.materialize_plan(
                wcag_version="2.2", level="AA", samples=plan["plan_basis"]["samples"][:1],
                variations=plan["plan_basis"]["variations"][:2],
                process_memberships={"SAMPLE-001": "PROCESS-001"},
                evaluation_ref="WCAG-EVAL-001", evaluation_revision="rev-7",
            )
            shrunk = workflow.register_wcag_evaluation_plan(
                root, workflow_ref, evaluation_initialization=initialization, evaluation_inputs=inputs,
                product_scope_ref="PRODUCT-SCOPE-001", scope_coverage=scope, source_artifacts=sources,
                canonical_criterion_plan=one_sample_plan, **self.context,
            )
            self.assertEqual(shrunk["status"], "conflict")

            variation_shrunk_plan = self.criterion_plan.materialize_plan(
                wcag_version="2.2", level="AA", samples=plan["plan_basis"]["samples"],
                variations=[row for row in plan["plan_basis"]["variations"] if row["variation_ref"] != "VAR-002"],
                process_memberships={"SAMPLE-001": "PROCESS-001"},
                evaluation_ref="WCAG-EVAL-001", evaluation_revision="rev-7",
            )
            variation_shrunk = workflow.register_wcag_evaluation_plan(
                root, workflow_ref, evaluation_initialization=initialization, evaluation_inputs=inputs,
                product_scope_ref="PRODUCT-SCOPE-001", scope_coverage=scope, source_artifacts=sources,
                canonical_criterion_plan=variation_shrunk_plan, **self.context,
            )
            self.assertEqual(variation_shrunk["status"], "conflict")

            membership_changed_plan = self.criterion_plan.materialize_plan(
                wcag_version="2.2", level="AA", samples=plan["plan_basis"]["samples"],
                variations=plan["plan_basis"]["variations"],
                process_memberships={"SAMPLE-002": "PROCESS-001"},
                evaluation_ref="WCAG-EVAL-001", evaluation_revision="rev-7",
            )
            membership_changed = workflow.register_wcag_evaluation_plan(
                root, workflow_ref, evaluation_initialization=initialization, evaluation_inputs=inputs,
                product_scope_ref="PRODUCT-SCOPE-001", scope_coverage=scope, source_artifacts=sources,
                canonical_criterion_plan=membership_changed_plan, **self.context,
            )
            self.assertEqual(membership_changed["status"], "conflict")

            other_workflow = workflow.read_wcag_evaluation_state(
                root, workflow.new_workflow_ref(), "WCAG-EVAL-001", evaluation_revision="rev-7", **self.context,
            )
            self.assertEqual(other_workflow["status"], "blocked")

            changed_context = {**self.context, "workflow_state_root_content_identity": "f" * 64}
            conflict = workflow.read_wcag_evaluation_state(
                root, workflow_ref, "WCAG-EVAL-001", evaluation_revision="rev-7", **changed_context,
            )
            self.assertEqual(conflict["status"], "conflict")

            # A proper revision transition records the prior evaluation revision and can change the level.
            next_inputs, next_init, next_scope, next_sources, next_plan = self.evaluation(revision="rev-8", level="A")
            revision_update = workflow.register_wcag_evaluation_plan(
                root, workflow_ref, evaluation_initialization=next_init, evaluation_inputs=next_inputs,
                product_scope_ref="PRODUCT-SCOPE-001", scope_coverage=next_scope,
                source_artifacts=next_sources, canonical_criterion_plan=next_plan,
                previous_evaluation_revision="rev-7", **self.context,
            )
            self.assertEqual(revision_update["status"], "registered")
            self.assertEqual(workflow.read_wcag_evaluation_state(
                root, workflow_ref, "WCAG-EVAL-001", evaluation_revision="rev-7", **self.context,
            )["status"], "conflict")

    def test_wcag_report_requires_current_full_result_set_and_persists_with_cas(self):
        workflow_ref = workflow.new_workflow_ref()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "states"
            registered, data = self.register(root, workflow_ref)
            self.assertEqual(registered["status"], "registered")
            _inputs, _initialization, _scope, _sources, plan = data
            current = workflow.read_wcag_evaluation_state(
                root, workflow_ref, "WCAG-EVAL-001", evaluation_revision="rev-7", **self.context,
            )
            self.assertEqual(current["status"], "current")
            missing = workflow.finalize_wcag_report(
                root, workflow_ref, expected_provider_revision=current["provider_revision"],
                evaluation_ref="WCAG-EVAL-001", evaluation_revision="rev-7",
                canonical_criterion_plan=plan, sample_results=[], closure_status="complete", **self.context,
            )
            self.assertEqual(missing["status"], "blocked")

            rows = []
            for index, criterion in enumerate(plan["criteria"], 1):
                rows.append({"sample_result_ref": f"WCAG-RES-{index:03d}",
                    "criterion_evaluation_ref": criterion["criterion_evaluation_ref"],
                    "evaluation_ref": "WCAG-EVAL-001", "evaluation_revision": "rev-7",
                    "sample_ref": criterion["sample_ref"], "variation_ref": criterion["variation_ref"],
                    "process_ref": criterion["process_ref"], "requirement_ref": criterion["criterion_ref"],
                    "result": "satisfied", "freshness_status": "current"})
            complete = workflow.finalize_wcag_report(
                root, workflow_ref, expected_provider_revision=current["provider_revision"],
                evaluation_ref="WCAG-EVAL-001", evaluation_revision="rev-7",
                canonical_criterion_plan=plan, sample_results=rows, closure_status="complete", **self.context,
            )
            self.assertEqual(complete["status"], "complete")
            self.assertEqual(complete["provider_revision"], "sqlite:3")
            concurrent_close = workflow.finalize_wcag_report(
                root, workflow_ref, expected_provider_revision=current["provider_revision"],
                evaluation_ref="WCAG-EVAL-001", evaluation_revision="rev-7",
                canonical_criterion_plan=plan, sample_results=rows, closure_status="complete", **self.context,
            )
            self.assertEqual(concurrent_close["status"], "conflict")
            persisted = workflow.read_wcag_evaluation_state(
                root, workflow_ref, "WCAG-EVAL-001", evaluation_revision="rev-7", **self.context,
            )
            self.assertEqual(persisted["evaluation"]["report_status"], "complete")
            self.assertEqual(len(persisted["evaluation"]["report_result_refs"]), len(plan["criteria"]))
            stale = [dict(row, evaluation_revision="rev-6") for row in rows]
            rejected = workflow.finalize_wcag_report(
                root, workflow_ref, expected_provider_revision=persisted["provider_revision"],
                evaluation_ref="WCAG-EVAL-001", evaluation_revision="rev-7",
                canonical_criterion_plan=plan, sample_results=stale, closure_status="complete", **self.context,
            )
            self.assertNotEqual(rejected["status"], "complete")

    def test_wcag_sqlite_provider_blocks_corrupt_database_and_git_worktree_path(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "states"
            database = root / "workflow-state.sqlite3"
            root.mkdir()
            database.write_bytes(b"not a sqlite database")
            result = workflow.read_sqlite_workflow_state(root, workflow.new_workflow_ref())
            self.assertEqual(result["status"], "blocked")
        result = workflow.create_sqlite_workflow_state(REPO_ROOT / "output", workflow.new_workflow_ref(), {})
        self.assertEqual(result["status"], "blocked")


class StandaloneSkillPortabilityTests(unittest.TestCase):
    def test_new_skill_candidate_outputs_pass_existing_deterministic_runner(self):
        skills = {
            "regression-testing": ["REG-OUT-001", "REG-OUT-002"],
            "exploratory-testing": ["EXP-OUT-001", "EXP-OUT-002"],
            "qa-knowledge": ["KN-OUT-001", "KN-OUT-002"],
        }
        for skill, eval_ids in skills.items():
            eval_file = REPO_ROOT / "skills" / skill / "evals" / "output" / "evals.json"
            for eval_id in eval_ids:
                with self.subTest(skill=skill, eval_id=eval_id):
                    output = eval_file.parent / "cases" / eval_id.lower() / "output.md"
                    result = grade(skill, eval_id, output)
                    self.assertEqual(result["status"], "pass", json.dumps(result, ensure_ascii=False))

    def test_each_required_production_helper_runs_from_a_copied_skill_package(self):
        probes = {
            "regression-testing": ("regression_runtime.py", "assert module.build_discovery_snapshot({'discovery_roots':['tc'], 'listing_complete':True, 'source_revisions':[{'source_ref':'repo:tc','revision':'r1'}], 'cases':[]})['complete']"),
            "exploratory-testing": ("exploratory_runtime.py", "assert module.validate_charter('exploration', {'purpose':'p','in_scope':['x'],'out_of_scope':['y'],'source_refs':['s'],'focus_refs':[],'timebox_or_exit_condition':'t','allowed_origins':['https://example.test'],'allowed_operations':['read'],'side_effect_operations':[],'side_effect_scope':'none','side_effect_action_definition':'none','side_effect_maximum':0,'cleanup_plan':'none','evidence_policy':'refs','block_conditions':['unsafe']})['valid']"),
            "qa-knowledge": ("knowledge_runtime.py", "assert module.canonical_entry_ref({'kind':'test_environment','scope_refs':['p'],'subject':'s'}).startswith('KN-')"),
        }
        for skill, (filename, assertion) in probes.items():
            with self.subTest(skill=skill), tempfile.TemporaryDirectory() as temp:
                source = REPO_ROOT / "skills" / skill
                copied = Path(temp) / skill
                shutil.copytree(source, copied)
                helper = copied / "scripts" / filename
                script = Path(temp) / "probe.py"
                script.write_text(
                    "import importlib.util\n"
                    f"spec=importlib.util.spec_from_file_location('module', r'{helper}')\n"
                    "module=importlib.util.module_from_spec(spec)\n"
                    "spec.loader.exec_module(module)\n"
                    + assertion + "\n",
                    encoding="utf-8",
                )
                env = dict(__import__("os").environ)
                env["PYTHONPATH"] = ""
                env["PYTHONUTF8"] = "1"
                result = subprocess.run([sys.executable, str(script)], cwd=temp, env=env, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
