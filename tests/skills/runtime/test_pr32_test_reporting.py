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
                {
                    "criterion_id": "EX-1",
                    "metric": "pass_rate",
                    "operator": ">=",
                    "threshold": 1.0,
                    "source_ids": ["e2e", "api"],
                },
                {
                    "criterion_id": "EX-2",
                    "metric": "fail_count",
                    "operator": "<=",
                    "threshold": 0,
                    "source_ids": ["e2e", "api"],
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
        self.assertEqual(statuses["EX-1"], "unknown")
        self.assertEqual(statuses["EX-2"], "unknown")

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
