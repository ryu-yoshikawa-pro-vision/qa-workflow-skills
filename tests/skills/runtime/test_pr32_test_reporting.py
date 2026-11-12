"""PR #32/J: report snapshot completeness, raw units and false-100% rejection."""

from __future__ import annotations

import copy
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
HELPER = REPO_ROOT / "skills" / "test-reporting" / "scripts" / "reporting_runtime.py"
spec = importlib.util.spec_from_file_location("pr32_reporting_runtime", HELPER)
assert spec is not None and spec.loader is not None
reporting = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reporting)

BUILD, ENV = "build:41", "env:stg"


def record(unit, ref, state="PASS", result=None, **extra):
    value = {
        "result_ref": result or f"res:{unit}:{ref}",
        "unit_ref": ref,
        "unit": unit,
        "state": state,
        "build_ref": BUILD,
        "environment_ref": ENV,
        "result_finalized": True,
        "cleanup_status": "成功",
    }
    value.update(extra)
    return value


def retrieval(source_id, records, revision="rev1", **overrides):
    value = {
        "source_id": source_id,
        "status": "complete",
        "pagination_complete": True,
        "permission_ok": True,
        "source_revision": revision,
        "retrieved_at": "2026-11-10T00:00:00+00:00",
        "records": records,
    }
    value.update(overrides)
    return value


def planned(source_id, kind, unit, refs=None, **extra):
    value = {
        "source_id": source_id,
        "owner_skill": "owner",
        "kind": kind,
        "unit": unit,
        "expected_refs": refs,
    }
    value.update(extra)
    return value


def base_input():
    return {
        "plan": {
            "plan_ref": "plan:qa-1",
            "plan_revision": "p3",
            "approval_state": "approved",
            "scope_ref": "scope:checkout",
            "build_ref": BUILD,
            "environment_ref": ENV,
            "planned_sources": [
                planned("e2e", "e2e", "logical_primary", ["T1", "T2"]),
                planned("api", "api", "test", ["A1", "A2", "A3"]),
            ],
            "exit_criteria": [
                # One criterion per measurement unit: logical_primary and test
                # results are never pooled into one denominator.
                {
                    "criterion_id": "EX-1",
                    "metric": "pass_rate",
                    "operator": ">=",
                    "threshold": 1.0,
                    "source_ids": ["e2e"],
                },
                {
                    "criterion_id": "EX-2",
                    "metric": "fail_count",
                    "operator": "<=",
                    "threshold": 0,
                    "source_ids": ["e2e"],
                },
                {
                    "criterion_id": "EX-3",
                    "metric": "pass_rate",
                    "operator": ">=",
                    "threshold": 1.0,
                    "source_ids": ["api"],
                },
                {
                    "criterion_id": "EX-4",
                    "metric": "fail_count",
                    "operator": "<=",
                    "threshold": 0,
                    "source_ids": ["api"],
                },
            ],
        },
        "retrievals": [
            retrieval(
                "e2e",
                [record("logical_primary", "T1"), record("logical_primary", "T2")],
            ),
            retrieval(
                "api",
                [record("test", "A1"), record("test", "A2"), record("test", "A3")],
            ),
        ],
        "current_source_revisions": {"e2e": "rev1", "api": "rev1"},
        "current_plan_revision": "p3",
    }


def source(snapshot, source_id):
    return next(s for s in snapshot["sources"] if s["source_id"] == source_id)


class CompleteSnapshotTests(unittest.TestCase):
    def test_fully_retrieved_plan_is_complete_and_keeps_units_separate(self):
        snap = reporting.build_snapshot(base_input())
        self.assertTrue(snap["overall"]["complete"])
        self.assertIsNone(snap["overall"]["pass_rate"])
        self.assertEqual(snap["by_unit"]["logical_primary"]["pass_rate"], 1.0)
        self.assertEqual(snap["by_unit"]["test"]["planned"], 3)
        self.assertEqual(snap["exit_judgement"], "satisfied")
        self.assertEqual(snap["release_decision"], "not_determined_by_this_skill")
        self.assertTrue(snap["snapshot_ref"].startswith("RPT-"))

    def test_snapshot_ref_is_deterministic_and_input_is_not_mutated(self):
        data = base_input()
        before = copy.deepcopy(data)
        self.assertEqual(
            reporting.build_snapshot(data)["snapshot_ref"],
            reporting.build_snapshot(data)["snapshot_ref"],
        )
        self.assertEqual(data, before)


class FalseCompletionTests(unittest.TestCase):
    def test_planned_api_missing_while_e2e_present_is_not_complete(self):
        data = base_input()
        data["retrievals"] = data["retrievals"][:1]
        snap = reporting.build_snapshot(data)
        self.assertFalse(snap["overall"]["complete"])
        api = source(snap, "api")
        self.assertIn("source_not_retrieved", api["issues"])
        self.assertEqual(api["empty_set"], "unknown_not_zero")
        self.assertIsNone(api["pass_rate"])
        self.assertEqual(snap["exit_judgement"], "undetermined")
        self.assertIsNone(snap["by_unit"]["test"]["pass_rate"])
        self.assertEqual(source(snap, "e2e")["pass_rate"], 1.0)

    def test_partial_units_pagination_and_permission_failures(self):
        for name, mutate in {
            "missing_unit": lambda d: d["retrievals"][1]["records"].pop(),
            "pagination": lambda d: d["retrievals"][1].update(
                pagination_complete=False
            ),
            "permission": lambda d: d["retrievals"][1].update(permission_ok=False),
            "status_partial": lambda d: d["retrievals"][1].update(status="partial"),
        }.items():
            with self.subTest(name=name):
                data = base_input()
                mutate(data)
                snap = reporting.build_snapshot(data)
                self.assertFalse(source(snap, "api")["complete"])
                self.assertFalse(snap["overall"]["complete"])
                self.assertIsNone(source(snap, "api")["pass_rate"])
                self.assertNotEqual(snap["exit_judgement"], "satisfied")

    def test_old_source_revision_and_other_build_are_not_counted(self):
        data = base_input()
        data["current_source_revisions"]["api"] = "rev2"
        snap = reporting.build_snapshot(data)
        self.assertIn(
            "source_revision_not_current_or_unverified", source(snap, "api")["issues"]
        )
        self.assertFalse(source(snap, "api")["complete"])

        data = base_input()
        data["retrievals"][1]["records"][2]["build_ref"] = "build:40"
        snap = reporting.build_snapshot(data)
        api = source(snap, "api")
        self.assertEqual(
            api["excluded"], [{"result_ref": "res:test:A3", "reason": "build_mismatch"}]
        )
        self.assertEqual(api["missing_unit_refs"], ["A3"])
        self.assertFalse(api["complete"])

    def test_environment_mismatch_and_unfinalized_results(self):
        data = base_input()
        data["retrievals"][0]["records"][0]["environment_ref"] = "env:prod"
        self.assertFalse(source(reporting.build_snapshot(data), "e2e")["complete"])
        data = base_input()
        data["retrievals"][0]["records"][0]["result_finalized"] = False
        snap = reporting.build_snapshot(data)
        self.assertIn("results_not_finalized", source(snap, "e2e")["issues"])
        self.assertFalse(snap["overall"]["complete"])

    def test_unconfirmed_cleanup_keeps_counts_but_blocks_closure(self):
        data = base_input()
        data["retrievals"][0]["records"][0]["cleanup_status"] = "未確認"
        e2e = source(reporting.build_snapshot(data), "e2e")
        self.assertFalse(e2e["closure"]["cleanup_closed"])
        self.assertEqual(e2e["counts"]["PASS"], 2)
        self.assertFalse(e2e["complete"])

    def test_unplanned_results_do_not_inflate_the_denominator(self):
        data = base_input()
        data["retrievals"][1]["records"].append(record("test", "A9"))
        api = source(reporting.build_snapshot(data), "api")
        self.assertEqual(api["unplanned_unit_refs"], ["A9"])
        self.assertEqual(api["planned_total"], 3)
        self.assertEqual(api["counts"]["PASS"], 3)

    def test_unknown_expected_population_is_never_all_found(self):
        data = base_input()
        data["plan"]["planned_sources"][1] = planned("api", "api", "test", None)
        snap = reporting.build_snapshot(data)
        self.assertIn("expected_population_unknown", source(snap, "api")["issues"])
        self.assertFalse(snap["overall"]["population_known"])
        self.assertFalse(snap["overall"]["complete"])

    def test_confirmed_empty_set_differs_from_unretrievable_zero(self):
        data = base_input()
        data["plan"]["planned_sources"][1] = planned(
            "api", "api", "test", None, no_target_confirmed=True
        )
        data["retrievals"][1]["records"] = []
        api = source(reporting.build_snapshot(data), "api")
        self.assertEqual(api["empty_set"], "confirmed_no_target")
        self.assertTrue(api["complete"])
        self.assertIsNone(api["pass_rate"])
        data = base_input()
        data["retrievals"][1].update(records=[], status="failed")
        api = source(reporting.build_snapshot(data), "api")
        self.assertEqual(api["empty_set"], "unknown_not_zero")
        self.assertFalse(api["complete"])


class RawUnitTests(unittest.TestCase):
    def test_retry_attempts_are_not_added_to_the_logical_denominator(self):
        data = base_input()
        data["plan"]["planned_sources"] = [
            planned("e2e", "e2e", "logical_primary", ["T1"]),
            planned("e2e-attempts", "e2e", "attempt", ["T1#0", "T1#1"]),
        ]
        data["plan"]["exit_criteria"] = []
        data["retrievals"] = [
            retrieval("e2e", [record("logical_primary", "T1", "PASS")]),
            retrieval(
                "e2e-attempts",
                [
                    record("attempt", "T1", "FAIL", result="res:att:0", attempt_no=0),
                    record("attempt", "T1", "PASS", result="res:att:1", attempt_no=1),
                ],
            ),
        ]
        data["current_source_revisions"] = {"e2e": "rev1", "e2e-attempts": "rev1"}
        data["plan"]["planned_sources"][1]["expected_refs"] = ["T1#0", "T1#1"]
        snap = reporting.build_snapshot(data)
        self.assertEqual(snap["by_unit"]["logical_primary"]["planned"], 1)
        self.assertEqual(snap["by_unit"]["attempt"]["planned"], 2)
        self.assertEqual(snap["by_unit"]["attempt"]["FAIL"], 1)
        self.assertEqual(snap["by_unit"]["logical_primary"]["FAIL"], 0)
        self.assertTrue(snap["overall"]["complete"])
        self.assertNotIn("total", snap["overall"])

    def test_same_unit_reported_twice_is_a_conflict_and_duplicate_result_is_ignored(
        self,
    ):
        data = base_input()
        data["retrievals"][1]["records"].append(
            record("test", "A1", "FAIL", result="res:other")
        )
        api = source(reporting.build_snapshot(data), "api")
        self.assertIn(
            "same_unit_reported_more_than_once_with_different_results", api["issues"]
        )
        self.assertFalse(api["complete"])
        data = base_input()
        data["retrievals"][1]["records"].append(record("test", "A1"))
        api = source(reporting.build_snapshot(data), "api")
        self.assertIn("duplicate_result_ref_ignored", api["issues"])
        self.assertTrue(api["complete"])

    def test_raw_states_are_preserved_and_unexecuted_is_not_pass(self):
        data = base_input()
        data["retrievals"][1]["records"][2]["state"] = "未実行"
        data["retrievals"][1]["records"][1]["state"] = "判定不能"
        api = source(reporting.build_snapshot(data), "api")
        self.assertEqual(api["counts"], {"PASS": 1, "判定不能": 1, "未実行": 1})
        self.assertEqual(api["pass_rate"], round(1 / 3, 6))
        self.assertEqual(api["unexecuted"], 1)
        data["retrievals"][1]["records"][2]["state"] = "PASSED"
        self.assertIn(
            "record_state_outside_raw_value_set",
            source(reporting.build_snapshot(data), "api")["issues"],
        )


class StaticTestingTests(unittest.TestCase):
    def static_input(self, reviewed, findings=0):
        records = [
            record("review_target", f"D{i}", "reviewed") for i in range(reviewed)
        ]
        records += [
            {
                "result_ref": f"f{i}",
                "unit": "finding",
                "unit_ref": f"F{i}",
                "state": "finding",
                "build_ref": BUILD,
            }
            for i in range(findings)
        ]
        return {
            "plan": {
                "plan_ref": "plan:s",
                "plan_revision": "p1",
                "approval_state": "approved",
                "scope_ref": "s",
                "build_ref": BUILD,
                "environment_ref": ENV,
                "planned_sources": [
                    planned(
                        "review",
                        "static_review",
                        "review_target",
                        [f"D{i}" for i in range(5)],
                    )
                ],
                "exit_criteria": [],
            },
            "retrievals": [retrieval("review", records)],
            "current_source_revisions": {"review": "rev1"},
        }

    def test_zero_findings_with_incomplete_review_is_not_complete(self):
        partial = source(reporting.build_snapshot(self.static_input(3)), "review")
        self.assertEqual(partial["finding_count"], 0)
        self.assertFalse(partial["zero_findings_claim_allowed"])
        self.assertEqual(partial["review_completion"], {"planned": 5, "reviewed": 3})
        full = source(reporting.build_snapshot(self.static_input(5)), "review")
        self.assertTrue(full["zero_findings_claim_allowed"])
        with_findings = source(
            reporting.build_snapshot(self.static_input(5, 2)), "review"
        )
        self.assertFalse(with_findings["zero_findings_claim_allowed"])
        self.assertEqual(with_findings["finding_count"], 2)


class ExitCriteriaAndPlanTests(unittest.TestCase):
    def test_incomplete_population_never_satisfies_rate_criteria(self):
        data = base_input()
        data["retrievals"][1]["records"].pop()
        snap = reporting.build_snapshot(data)
        statuses = {c["criterion_id"]: c["status"] for c in snap["exit_criteria"]}
        self.assertEqual(statuses["EX-3"], "unknown")
        self.assertEqual(statuses["EX-4"], "unknown")
        self.assertEqual(statuses["EX-1"], "satisfied")

    def test_observed_failures_violate_a_zero_failure_criterion_even_when_incomplete(
        self,
    ):
        data = base_input()
        data["retrievals"][1]["records"].pop()
        data["retrievals"][0]["records"][0]["state"] = "FAIL"
        snap = reporting.build_snapshot(data)
        self.assertEqual(
            {c["criterion_id"]: c["status"] for c in snap["exit_criteria"]}["EX-2"],
            "unsatisfied",
        )
        self.assertEqual(snap["exit_judgement"], "unsatisfied")

    def test_unapproved_and_superseded_plans_leave_exit_undetermined(self):
        data = base_input()
        data["plan"]["approval_state"] = "draft"
        snap = reporting.build_snapshot(data)
        self.assertIn("plan_not_approved", snap["issues"])
        self.assertEqual(snap["exit_judgement"], "undetermined")
        data = base_input()
        data["current_plan_revision"] = "p4"
        snap = reporting.build_snapshot(data)
        self.assertIn("plan_revision_superseded", snap["issues"])
        self.assertEqual(snap["exit_judgement"], "undetermined")

    def test_direct_request_without_plan_has_unknown_population(self):
        snap = reporting.build_snapshot(
            {
                "scope": {"scope_ref": "scope:x", "discovery_roots": ["qa/results"]},
                "retrievals": [],
            }
        )
        self.assertEqual(snap["population_basis"], "unknown_direct_request")
        self.assertFalse(snap["overall"]["complete"])
        self.assertEqual(snap["exit_judgement"], "undetermined")
        undefined = reporting.build_snapshot({"retrievals": []})
        self.assertIn(
            "explicit_scope_and_discovery_roots_required", undefined["issues"]
        )

    def test_currentness_detects_changed_plan_and_source_revisions(self):
        snap = reporting.build_snapshot(base_input())
        same = reporting.check_currentness(
            snap,
            {"plan_revision": "p3", "source_revisions": {"e2e": "rev1", "api": "rev1"}},
        )
        self.assertEqual(same["status"], "current")
        stale = reporting.check_currentness(
            snap,
            {"plan_revision": "p4", "source_revisions": {"e2e": "rev1", "api": "rev9"}},
        )
        self.assertEqual(stale["stale"], ["plan_revision", "source:api"])

    def test_defect_projection_is_read_only(self):
        data = base_input()
        data["defects"] = [{"candidate_ref": "DEFC-1", "external_issue_ref": "ISSUE-4"}]
        projection = reporting.build_snapshot(data)["defect_projection"]
        self.assertEqual(
            projection, {"count": 1, "issue_refs": ["ISSUE-4"], "read_only": True}
        )


def permutations_of(data, key):
    """Yield the input with the list under `key` in every order."""
    import itertools

    for order in itertools.permutations(range(len(data[key]))):
        variant = copy.deepcopy(data)
        variant[key] = [data[key][i] for i in order]
        yield variant


class SnapshotIdentityTests(unittest.TestCase):
    def test_same_content_gives_a_stable_ref_regardless_of_input_order(self):
        base = reporting.build_snapshot(base_input())["snapshot_ref"]
        data = base_input()
        for variant in permutations_of(data, "retrievals"):
            for rec_variant in (variant,):
                rec_variant["retrievals"][0]["records"].reverse()
                self.assertEqual(
                    reporting.build_snapshot(rec_variant)["snapshot_ref"], base
                )

    def test_different_content_never_shares_a_ref_even_with_equal_plan_revision_and_counts(
        self,
    ):
        refs = {reporting.build_snapshot(base_input())["snapshot_ref"]}

        def failing(d):
            d["retrievals"][1]["records"][0]["state"] = "FAIL"

        def swapped_result(d):
            d["retrievals"][1]["records"][0]["result_ref"] = "res:other"

        def different_cleanup(d):
            d["retrievals"][0]["records"][0]["cleanup_status"] = "未確認"

        def incomplete_same_count(d):
            # same retrieved count per source, but one unit is another ref
            d["retrievals"][1]["records"][2]["unit_ref"] = "A9"

        def stale_source(d):
            d["current_source_revisions"]["api"] = "rev2"

        for name, mutate in {
            "state": failing,
            "result_ref": swapped_result,
            "cleanup": different_cleanup,
            "unit_ref": incomplete_same_count,
            "currentness": stale_source,
        }.items():
            with self.subTest(name=name):
                data = base_input()
                mutate(data)
                ref = reporting.build_snapshot(data)["snapshot_ref"]
                self.assertNotIn(ref, refs)
                refs.add(ref)
        self.assertEqual(len(refs), 6)

    def test_ref_covers_the_whole_content(self):
        import hashlib

        snap = reporting.build_snapshot(base_input())
        body = {k: v for k, v in snap.items() if k != "snapshot_ref"}
        digest = hashlib.sha256(
            json.dumps(
                body, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            ).encode("utf-8")
        ).hexdigest()
        self.assertEqual(snap["snapshot_ref"], "RPT-" + digest[:40])


class PlanCurrentnessTests(unittest.TestCase):
    def test_missing_or_blank_current_plan_revision_is_unverified_not_current(self):
        for name, mutate in {
            "absent": lambda d: d.pop("current_plan_revision"),
            "none": lambda d: d.update(current_plan_revision=None),
            "blank": lambda d: d.update(current_plan_revision="  "),
        }.items():
            with self.subTest(name=name):
                data = base_input()
                mutate(data)
                snap = reporting.build_snapshot(data)
                self.assertIn("plan_currentness_unverified", snap["issues"])
                self.assertNotIn("plan_revision_superseded", snap["issues"])
                self.assertEqual(snap["plan_currentness"], "unverified")
                self.assertEqual(snap["exit_judgement"], "undetermined")
                self.assertTrue(snap["overall"]["complete"])

    def test_mismatch_is_superseded_and_match_is_current(self):
        data = base_input()
        data["current_plan_revision"] = "p9"
        snap = reporting.build_snapshot(data)
        self.assertEqual(snap["plan_currentness"], "superseded")
        self.assertEqual(snap["exit_judgement"], "undetermined")
        self.assertEqual(
            reporting.build_snapshot(base_input())["plan_currentness"], "current"
        )
        self.assertEqual(
            reporting.build_snapshot(base_input())["exit_judgement"], "satisfied"
        )

    def test_expired_revoked_and_unknown_approval_states_never_satisfy(self):
        for state in ("expired", "revoked", "draft", None, "APPROVED"):
            with self.subTest(state=state):
                data = base_input()
                data["plan"]["approval_state"] = state
                self.assertEqual(
                    reporting.build_snapshot(data)["exit_judgement"], "undetermined"
                )

    def test_plan_without_ref_or_revision_is_not_identifiable(self):
        data = base_input()
        data["plan"].pop("plan_revision")
        snap = reporting.build_snapshot(data)
        self.assertIn("plan_ref_and_revision_required", snap["issues"])
        self.assertEqual(snap["exit_judgement"], "undetermined")

    def test_currentness_check_distinguishes_unverified_from_stale(self):
        snap = reporting.build_snapshot(base_input())
        fresh = {
            "plan_revision": "p3",
            "source_revisions": {"e2e": "rev1", "api": "rev1"},
        }
        self.assertEqual(reporting.check_currentness(snap, fresh)["status"], "current")
        missing_plan = reporting.check_currentness(
            snap, {"source_revisions": fresh["source_revisions"]}
        )
        self.assertEqual(missing_plan["status"], "unverified")
        self.assertEqual(missing_plan["unverified"], ["plan_revision"])
        missing_source = reporting.check_currentness(
            snap, {**fresh, "source_revisions": {"e2e": "rev1"}}
        )
        self.assertEqual(missing_source["status"], "unverified")
        changed_and_missing = reporting.check_currentness(
            snap, {"plan_revision": "p4", "source_revisions": {"e2e": "rev1"}}
        )
        self.assertEqual(changed_and_missing["status"], "stale")
        self.assertEqual(reporting.check_currentness(snap, {})["status"], "unverified")


class MeasurementUnitContractTests(unittest.TestCase):
    def criterion(self, metric, source_ids, **extra):
        return {
            "criterion_id": "C",
            "metric": metric,
            "operator": ">=",
            "threshold": 1.0,
            "source_ids": source_ids,
            **extra,
        }

    def snap(self, criteria, planned_sources=None, retrievals=None):
        data = base_input()
        if planned_sources is not None:
            data["plan"]["planned_sources"] = planned_sources
        if retrievals is not None:
            data["retrievals"] = retrievals
        data["plan"]["exit_criteria"] = criteria
        data["current_source_revisions"] = {
            r["source_id"]: "rev1" for r in data["retrievals"]
        }
        return reporting.build_snapshot(data)

    def test_pooling_logical_primary_and_test_results_is_unknown_not_satisfied(self):
        for metric in ("pass_rate", "executed_rate", "fail_count", "unexecuted_count"):
            with self.subTest(metric=metric):
                snap = self.snap(
                    [
                        self.criterion(
                            metric,
                            ["e2e", "api"],
                            operator=">=" if metric.endswith("rate") else "<=",
                            threshold=1.0 if metric.endswith("rate") else 99,
                        )
                    ]
                )
                criterion = snap["exit_criteria"][0]
                self.assertEqual(criterion["status"], "unknown")
                self.assertEqual(
                    criterion["reason"], "mixed_units_or_kinds_not_summable"
                )
                self.assertEqual(snap["exit_judgement"], "undetermined")

    def test_logical_primary_and_attempt_are_never_pooled_even_though_both_are_e2e(
        self,
    ):
        planned_sources = [
            planned("e2e", "e2e", "logical_primary", ["T1"]),
            planned("att", "e2e", "attempt", ["T1#0", "T1#1"]),
        ]
        retrievals = [
            retrieval("e2e", [record("logical_primary", "T1", "PASS")]),
            retrieval(
                "att",
                [
                    record("attempt", "T1", "FAIL", result="a0", attempt_no=0),
                    record("attempt", "T1", "PASS", result="a1", attempt_no=1),
                ],
            ),
        ]
        snap = self.snap(
            [self.criterion("pass_rate", ["e2e", "att"])], planned_sources, retrievals
        )
        self.assertEqual(snap["exit_criteria"][0]["status"], "unknown")
        self.assertEqual(snap["exit_judgement"], "undetermined")
        per_unit = self.snap(
            [self.criterion("pass_rate", ["e2e"])], planned_sources, retrievals
        )
        self.assertEqual(per_unit["exit_criteria"][0]["status"], "satisfied")
        attempts_alone = self.snap(
            [self.criterion("pass_rate", ["att"])], planned_sources, retrievals
        )
        self.assertEqual(attempts_alone["exit_criteria"][0]["status"], "unsatisfied")

    def test_formal_tc_individual_test_and_auxiliary_testware_are_separate_units(self):
        sources = [
            planned("tc", "general_tc", "resolved_testcase", ["TC1"]),
            planned("vt", "component", "test", ["V1"]),
            planned("aux", "e2e", "auxiliary_testware", ["X1"]),
        ]
        retrievals = [
            retrieval("tc", [record("resolved_testcase", "TC1")]),
            retrieval("vt", [record("test", "V1")]),
            retrieval("aux", [record("auxiliary_testware", "X1")]),
        ]
        for ids in (["tc", "vt"], ["tc", "aux"], ["vt", "aux"], ["tc", "vt", "aux"]):
            with self.subTest(ids=ids):
                snap = self.snap(
                    [self.criterion("pass_rate", ids)], sources, retrievals
                )
                self.assertEqual(snap["exit_criteria"][0]["status"], "unknown")
        # two sources of the same unit may be pooled when the criterion says so
        sources2 = [
            planned("a", "api", "test", ["A1"]),
            planned("c", "component", "test", ["C1"]),
        ]
        retrievals2 = [
            retrieval("a", [record("test", "A1")]),
            retrieval("c", [record("test", "C1")]),
        ]
        pooled = self.snap(
            [self.criterion("pass_rate", ["a", "c"])], sources2, retrievals2
        )
        self.assertEqual(pooled["exit_criteria"][0]["status"], "satisfied")

    def test_execution_results_and_static_review_do_not_share_metrics(self):
        review = planned("rev", "static_review", "review_target", ["D1"])
        reviews = retrieval("rev", [record("review_target", "D1", "reviewed")])
        sources = [planned("api", "api", "test", ["A1"]), review]
        retrievals = [retrieval("api", [record("test", "A1")]), reviews]
        for metric, ids in (
            ("pass_rate", ["rev"]),
            ("fail_count", ["rev"]),
            ("review_completion", ["api"]),
            ("review_completion", ["api", "rev"]),
        ):
            with self.subTest(metric=metric, ids=ids):
                snap = self.snap([self.criterion(metric, ids)], sources, retrievals)
                self.assertEqual(snap["exit_criteria"][0]["status"], "unknown")
        ok = self.snap(
            [self.criterion("review_completion", ["rev"])], sources, retrievals
        )
        self.assertEqual(ok["exit_criteria"][0]["status"], "satisfied")

    def test_executed_rate_counts_only_started_units(self):
        data = base_input()
        data["plan"]["exit_criteria"] = []
        states = ["PASS", "SKIP", "blocked"]
        for i, state in enumerate(states):
            data["retrievals"][1]["records"][i]["state"] = state
            data["retrievals"][1]["records"][i]["cleanup_status"] = "成功"
        api = source(reporting.build_snapshot(data), "api")
        self.assertEqual(api["executed_rate"], round(1 / 3, 6))
        data["retrievals"][1]["records"][1]["state"] = "判定不能"
        self.assertEqual(
            source(reporting.build_snapshot(data), "api")["executed_rate"],
            round(2 / 3, 6),
        )


class DuplicateAndConflictOrderTests(unittest.TestCase):
    def test_duplicate_source_ids_are_ambiguous_in_every_order(self):
        good = retrieval(
            "api", [record("test", "A1"), record("test", "A2"), record("test", "A3")]
        )
        bad = retrieval(
            "api", [record("test", "A1")], status="partial", pagination_complete=False
        )
        outcomes = []
        for order in ((good, bad), (bad, good)):
            data = base_input()
            data["retrievals"] = [data["retrievals"][0], *copy.deepcopy(list(order))]
            snap = reporting.build_snapshot(data)
            api = source(snap, "api")
            self.assertFalse(api["complete"])
            self.assertIn("duplicate_retrieval_for_source_id", api["issues"])
            self.assertIn("duplicate_retrieval_source_id", snap["issues"])
            self.assertFalse(snap["overall"]["complete"])
            self.assertEqual(snap["exit_judgement"], "undetermined")
            outcomes.append(snap["snapshot_ref"])
        self.assertEqual(outcomes[0], outcomes[1])

    def test_identical_duplicate_retrievals_are_still_ambiguous(self):
        data = base_input()
        data["retrievals"].append(copy.deepcopy(data["retrievals"][1]))
        snap = reporting.build_snapshot(data)
        self.assertFalse(source(snap, "api")["complete"])

    def test_retrieval_without_source_id_is_reported(self):
        data = base_input()
        data["retrievals"].append({"status": "complete"})
        data["retrievals"].append("junk")
        snap = reporting.build_snapshot(data)
        self.assertIn("retrieval_without_source_id", snap["issues"])
        self.assertEqual(snap["exit_judgement"], "undetermined")

    def test_conflicting_records_give_the_same_result_in_either_order(self):
        results = []
        for first, second in (("PASS", "FAIL"), ("FAIL", "PASS")):
            data = base_input()
            recs = data["retrievals"][1]["records"]
            recs[0]["state"] = first
            recs.append(record("test", "A1", second, result="res:second"))
            snap = reporting.build_snapshot(data)
            api = source(snap, "api")
            self.assertFalse(api["complete"])
            self.assertEqual(api["conflicting_unit_refs"], ["A1"])
            self.assertEqual(api["counts"], {"PASS": 2})
            results.append((api["counts"], api["missing_unit_refs"], api["issues"]))
        self.assertEqual(results[0], results[1])

    def test_same_result_ref_with_different_content_is_a_conflict_not_first_wins(self):
        for first, second in (("PASS", "FAIL"), ("FAIL", "PASS")):
            with self.subTest(first=first):
                data = base_input()
                recs = data["retrievals"][1]["records"]
                recs[0] = record("test", "A1", first, result="res:x")
                recs.append(record("test", "A1", second, result="res:x"))
                api = source(reporting.build_snapshot(data), "api")
                self.assertIn("result_ref_reused_with_different_content", api["issues"])
                self.assertFalse(api["complete"])

    def test_record_order_never_improves_completeness(self):
        data = base_input()
        data["retrievals"][1]["records"][0]["build_ref"] = "build:40"
        refs = set()
        for variant in permutations_of(data["retrievals"][1], "records"):
            d = copy.deepcopy(data)
            d["retrievals"][1] = variant
            snap = reporting.build_snapshot(d)
            self.assertFalse(source(snap, "api")["complete"])
            refs.add(snap["snapshot_ref"])
        self.assertEqual(len(refs), 1)


class PeriodTests(unittest.TestCase):
    PERIOD = {"from": "2026-11-01T00:00:00+00:00", "to": "2026-11-07T23:59:59+00:00"}

    def data(self, **record_extra):
        data = base_input()
        data["plan"]["period"] = dict(self.PERIOD)
        for item in data["retrievals"]:
            for rec in item["records"]:
                rec["executed_at"] = "2026-11-05T10:00:00+00:00"
        return data

    def test_runs_inside_the_planned_period_are_counted(self):
        snap = reporting.build_snapshot(self.data())
        self.assertTrue(snap["overall"]["complete"])
        self.assertEqual(snap["period"], self.PERIOD)

    def test_runs_outside_or_without_a_verifiable_time_are_excluded(self):
        for name, value, reason in (
            ("before", "2026-10-31T23:59:59+00:00", "period_mismatch"),
            ("after", "2026-11-08T00:00:00+00:00", "period_mismatch"),
            ("garbage", "yesterday", "period_unverified"),
            ("missing", None, "period_unverified"),
        ):
            with self.subTest(name=name):
                data = self.data()
                rec = data["retrievals"][1]["records"][2]
                if value is None:
                    rec.pop("executed_at")
                else:
                    rec["executed_at"] = value
                snap = reporting.build_snapshot(data)
                api = source(snap, "api")
                self.assertEqual(
                    api["excluded"],
                    [{"result_ref": rec["result_ref"], "reason": reason}],
                )
                self.assertEqual(api["missing_unit_refs"], ["A3"])
                self.assertFalse(api["complete"])
                self.assertEqual(snap["exit_judgement"], "undetermined")

    def test_boundaries_are_inclusive_and_timezones_are_honoured(self):
        data = self.data()
        data["retrievals"][1]["records"][0]["executed_at"] = self.PERIOD["from"]
        data["retrievals"][1]["records"][1]["executed_at"] = self.PERIOD["to"]
        data["retrievals"][1]["records"][2]["executed_at"] = "2026-11-08T08:00:00+09:00"
        self.assertTrue(source(reporting.build_snapshot(data), "api")["complete"])
        data["retrievals"][1]["records"][2]["executed_at"] = "2026-11-08T09:00:01+09:00"
        self.assertFalse(source(reporting.build_snapshot(data), "api")["complete"])

    def test_per_source_period_overrides_the_plan_and_invalid_periods_block(self):
        data = self.data()
        data["plan"]["planned_sources"][1]["period"] = {
            "from": "2026-11-06T00:00:00+00:00",
            "to": "2026-11-07T00:00:00+00:00",
        }
        self.assertFalse(source(reporting.build_snapshot(data), "api")["complete"])
        for bad in (
            {"from": "2026-11-09T00:00:00+00:00", "to": "2026-11-01T00:00:00+00:00"},
            {"from": "x", "to": "y"},
            "now",
        ):
            with self.subTest(bad=bad):
                data = self.data()
                data["plan"]["period"] = bad
                snap = reporting.build_snapshot(data)
                self.assertIn("plan_period_invalid", snap["issues"])
                self.assertEqual(snap["exit_judgement"], "undetermined")
                self.assertFalse(snap["overall"]["complete"])

    def test_no_declared_period_means_no_period_filter(self):
        self.assertTrue(reporting.build_snapshot(base_input())["overall"]["complete"])
        self.assertIsNone(reporting.build_snapshot(base_input())["period"])

    def test_static_review_targets_follow_the_same_period_rule(self):
        data = StaticTestingTests().static_input(5)
        data["plan"]["period"] = dict(self.PERIOD)
        for rec in data["retrievals"][0]["records"]:
            rec["executed_at"] = "2026-12-01T00:00:00+00:00"
        review = source(reporting.build_snapshot(data), "review")
        self.assertFalse(review["complete"])
        self.assertFalse(review["zero_findings_claim_allowed"])


class StateValueSetTests(unittest.TestCase):
    def test_static_states_are_not_accepted_for_execution_and_vice_versa(self):
        data = base_input()
        data["retrievals"][1]["records"][0]["state"] = "reviewed"
        self.assertIn(
            "record_state_outside_raw_value_set",
            source(reporting.build_snapshot(data), "api")["issues"],
        )
        static = StaticTestingTests().static_input(5)
        static["retrievals"][0]["records"][0]["state"] = "PASS"
        self.assertIn(
            "record_state_outside_raw_value_set",
            source(reporting.build_snapshot(static), "review")["issues"],
        )

    def test_attempt_records_need_an_integer_attempt_number(self):
        data = base_input()
        data["plan"]["planned_sources"] = [planned("att", "e2e", "attempt", ["T1#0"])]
        data["plan"]["exit_criteria"] = []
        for bad in (None, "0", True):
            data["retrievals"] = [
                retrieval("att", [record("attempt", "T1", attempt_no=bad)])
            ]
            data["current_source_revisions"] = {"att": "rev1"}
            self.assertIn(
                "record_unit_or_identity_invalid",
                source(reporting.build_snapshot(data), "att")["issues"],
            )


class CliTests(unittest.TestCase):
    def run_cli(self, command, payload, helper=HELPER, cwd=None):
        return subprocess.run(
            [sys.executable, "-I", str(helper), command],
            input=payload if isinstance(payload, str) else json.dumps(payload),
            capture_output=True,
            text=True,
            cwd=cwd,
            check=False,
        )

    def test_cli_and_isolated_copy(self):
        done = self.run_cli("build-snapshot", base_input())
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertTrue(json.loads(done.stdout)["overall"]["complete"])
        with tempfile.TemporaryDirectory() as temp:
            copied = Path(temp) / "test-reporting"
            shutil.copytree(REPO_ROOT / "skills" / "test-reporting", copied)
            result = self.run_cli(
                "build-snapshot",
                base_input(),
                helper=copied / "scripts" / "reporting_runtime.py",
                cwd=temp,
            )
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_cli_rejects_bad_input(self):
        for payload in ("[]", '{"a":1,"a":2}', "{bad"):
            with self.subTest(payload=payload):
                rejected = self.run_cli("build-snapshot", payload)
                self.assertEqual(rejected.returncode, 2)
                self.assertEqual(json.loads(rejected.stdout)["status"], "blocked")
        self.assertEqual(self.run_cli("nope", {}).returncode, 2)


class Utf8StdinTests(unittest.TestCase):
    def test_raw_utf8_stdin_is_decoded_independently_of_the_locale(self):
        payload = json.dumps(base_input(), ensure_ascii=False)
        completed = subprocess.run(
            [sys.executable, "-I", str(HELPER), "build-snapshot"],
            input=payload.encode("utf-8"),
            capture_output=True,
            check=False,
            env={
                "PYTHONIOENCODING": "cp932",
                "SYSTEMROOT": __import__("os").environ.get("SYSTEMROOT", ""),
            },
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        completed = subprocess.run(
            [sys.executable, "-I", str(HELPER), "build-snapshot"],
            input=b"\xff\xfe{}",
            capture_output=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 2)


if __name__ == "__main__":
    unittest.main()
