"""担当H：非E2E testware route・補助testwareの実施義務・Activity完了判定の局所検証。

他担当（G: testware実行）の実成果物は使わず、合意した契約と独立fixtureで検証する。
"""

from __future__ import annotations

import copy
import importlib.util
import json
import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SKILL = REPO_ROOT / "skills" / "regression-testing"
FIXTURE = (
    REPO_ROOT
    / "tests"
    / "skills"
    / "fixtures"
    / "regression-testware"
    / "vitest-qa-training-store-2a8bcf5.json"
)


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


regression = _load("h_regression_runtime", SKILL / "scripts" / "regression_runtime.py")
validator = _load(
    "h_regression_validator", SKILL / "evals" / "deterministic" / "validator.py"
)

REV = "rev-A"
V2 = {"route_contract_version": "2"}


def started(result="PASS", *, finalized=True, **extra):
    return {
        "start_state": "開始済み",
        "actual_start_confirmed": True,
        "result_finalized": finalized,
        "source_result": result,
        **extra,
    }


def aux_started(result="PASS", *, revision=REV, **extra):
    return started(
        result,
        implementation_revision=revision,
        attempt_ref=extra.pop("attempt_ref", "attempt-1"),
        raw_capture_complete=extra.pop("raw_capture_complete", True),
        cleanup_status=extra.pop("cleanup_status", "対象なし"),
        **extra,
    )


def tw_started(result="PASS", *, revision=REV, **extra):
    """testware routeのsource：attempt・raw取得・cleanupを明示して返す。"""
    return started(
        result,
        implementation_revision=revision,
        attempt_ref=extra.pop("attempt_ref", "attempt-tw"),
        raw_capture_complete=extra.pop("raw_capture_complete", True),
        cleanup_status=extra.pop("cleanup_status", "対象なし"),
        **extra,
    )


NOT_STARTED = {
    "start_state": "未開始",
    "actual_start_confirmed": False,
    "result_finalized": False,
}


def tc_route(tc, execution, kind="testware", **extra):
    route = {
        "tc_ref": tc,
        "route_type": kind,
        "route_ref": f"{kind}:{tc}",
        "execution_ref": execution,
    }
    if kind == "testware":
        route.update(
            testware_ref=f"vitest:{tc}",
            executor_owner="testware-execution",
            implementation_revision=REV,
            selection_basis="tests/unit/password-hasher.test.ts",
        )
    return {**route, **extra}


def aux(ref, execution, *, required=True, **extra):
    return {
        "testware_ref": ref,
        "execution_ref": execution,
        "executor_owner": "testware-execution",
        "implementation_revision": REV,
        "selection_basis": "user_explicit" if required else "reference_only",
        "completion_required": required,
        **extra,
    }


def activity_doc(run, source, **kwargs):
    activity = regression.project_activity(run, source, **kwargs)
    return {
        **activity,
        "artifact_type": "activity",
        "activity_ref": "ACT-H-1",
        "snapshot_ref": "DS-1",
        "scope_identity": "scope-1",
        "source_executions": source,
    }


def check(doc, assertion):
    rendered = "```json\n" + json.dumps(doc, ensure_ascii=False) + "\n```"
    result = validator.validate(rendered, {}, "H-UNIT")
    return next(item.status for item in result.assertions if item.id == assertion)


class RequiredRouteTests(unittest.TestCase):
    def test_testware_route_requires_owner_revision_and_selection(self):
        valid = regression.validate_required_routes(
            [
                {"tc_ref": "TC-1", "route_type": "manual", "route_ref": "m"},
                tc_route("TC-2", "X-2"),
            ]
        )
        self.assertTrue(valid["valid"], valid["issues"])
        self.assertEqual(valid["routes"][1]["testware_ref"], "vitest:TC-2")
        # 既存manual / e2eの正規化形は変えない。
        self.assertNotIn("testware_ref", valid["routes"][0])
        for field in (
            "testware_ref",
            "executor_owner",
            "implementation_revision",
            "selection_basis",
        ):
            with self.subTest(field=field):
                route = tc_route("TC-2", "X-2")
                route.pop(field)
                result = regression.validate_required_routes([route])
                self.assertFalse(result["valid"])
        wrong_owner = tc_route("TC-2", "X-2", executor_owner="regression-testing")
        self.assertFalse(regression.validate_required_routes([wrong_owner])["valid"])
        legacy_invalid = regression.validate_required_routes(
            [{"tc_ref": "TC-1", "route_type": "unit", "route_ref": "u"}]
        )
        self.assertFalse(legacy_invalid["valid"])

    def test_run_validator_accepts_testware_and_rejects_incomplete_route(self):
        run = {
            "artifact_type": "run",
            "run_scope": "selected",
            "suite_complete": False,
            "baseline": {
                "complete": True,
                "currentness": "current",
                "member_tc_refs": ["TC-1"],
            },
            "selected_tc_refs": ["TC-1"],
            "required_routes": [tc_route("TC-1", "X-1")],
            "auxiliary_testware_refs": [],
            "auxiliary_testware_count": 0,
        }
        self.assertEqual(check(run, "REG-D008"), "pass")
        broken = copy.deepcopy(run)
        del broken["required_routes"][0]["implementation_revision"]
        self.assertEqual(check(broken, "REG-D008"), "fail")


class AuxiliarySelectionTests(unittest.TestCase):
    details = {
        "T-1": {"executor_owner": "testware-execution", "implementation_revision": REV},
        "T-2": {
            "executor_owner": "e2e-test-execution",
            "implementation_revision": REV,
        },
    }

    def test_obligation_follows_explicit_selection_only(self):
        result = regression.select_auxiliary_testware(
            requested_refs=["T-1"],
            user_explicit_refs=["T-1"],
            policy_refs=[],
            available_refs=["T-1", "T-2"],
            reference_only_refs=["T-2"],
            testware_details=self.details,
        )
        self.assertEqual(result["status"], "ready")
        by_ref = {r["testware_ref"]: r for r in result["auxiliary_routes"]}
        self.assertIs(by_ref["T-1"]["completion_required"], True)
        self.assertEqual(by_ref["T-1"]["selection_basis"], "user_explicit")
        self.assertIs(by_ref["T-2"]["completion_required"], False)
        self.assertEqual(by_ref["T-2"]["selection_basis"], "reference_only")
        self.assertEqual(result["selected_refs"], ["T-1"])
        self.assertEqual(result["tc_member_count"], 0)
        policy = regression.select_auxiliary_testware(
            requested_refs=["T-1"],
            user_explicit_refs=[],
            policy_refs=["T-1"],
            available_refs=["T-1"],
            testware_details=self.details,
        )
        self.assertEqual(policy["auxiliary_routes"][0]["selection_basis"], "policy")

    def test_unknown_basis_or_missing_detail_is_not_guessed(self):
        base = dict(
            user_explicit_refs=[],
            policy_refs=[],
            available_refs=["T-1"],
            testware_details=self.details,
        )
        unauthorized = regression.select_auxiliary_testware(
            requested_refs=["T-1"], **base
        )
        self.assertEqual(unauthorized["status"], "unresolved")
        conflict = regression.select_auxiliary_testware(
            requested_refs=["T-1"],
            reference_only_refs=["T-1"],
            **{**base, "user_explicit_refs": ["T-1"]},
        )
        self.assertEqual(conflict["conflicting_refs"], ["T-1"])
        no_detail = regression.select_auxiliary_testware(
            requested_refs=["T-1"],
            **{**base, "user_explicit_refs": ["T-1"], "testware_details": {}},
        )
        self.assertEqual(no_detail["missing_detail_refs"], ["T-1"])

    def test_auxiliary_route_validation_reports_legacy_as_unknown(self):
        result = regression.validate_auxiliary_routes(
            [aux("A", "E-A"), {"testware_ref": "LEGACY", "execution_ref": "E-L"}],
            tc_testware_refs=["vitest:TC-1"],
        )
        self.assertTrue(result["valid"], result["issues"])
        self.assertEqual(result["obligation_unknown_refs"], ["LEGACY"])
        self.assertFalse(
            regression.validate_auxiliary_routes([aux("A", "E", required="yes")])[
                "valid"
            ]
        )
        inconsistent = aux("A", "E", required=True, selection_basis="reference_only")
        self.assertFalse(regression.validate_auxiliary_routes([inconsistent])["valid"])
        self.assertFalse(
            regression.validate_auxiliary_routes(
                [aux("vitest:TC-1", "E")], tc_testware_refs=["vitest:TC-1"]
            )["valid"]
        )
        self.assertFalse(
            regression.validate_auxiliary_routes([{**aux("A", "E"), "tc_ref": "TC-1"}])[
                "valid"
            ]
        )


class ActivityObligationTests(unittest.TestCase):
    def test_required_auxiliary_not_started_blocks_completion_despite_tc_pass(self):
        run = {
            "route_contract_version": "2",
            "required_routes": [tc_route("TC-1", "X-1")],
            "auxiliary_routes": [aux("A", "E-A")],
        }
        source = {
            "X-1": tw_started("PASS"),
            "E-A": NOT_STARTED,
        }
        activity = regression.project_activity(run, source)
        self.assertEqual(activity["activity_state"], "部分完了（ブロック中あり）")
        self.assertEqual(activity["counts"]["executed_tc_count"], 1)
        self.assertEqual(activity["counts"]["auxiliary_executed_count"], 0)
        forged = {**activity_doc(run, source), "activity_state": "完了"}
        self.assertEqual(check(forged, "REG-D011"), "fail")
        self.assertEqual(check(activity_doc(run, source), "REG-D011"), "pass")

    def test_optional_candidate_unstarted_does_not_block(self):
        run = {
            "route_contract_version": "2",
            "required_routes": [tc_route("TC-1", "X-1")],
            "auxiliary_routes": [aux("OPT", "E-O", required=False)],
            "auxiliary_testware_count": 1,
        }
        source = {
            "X-1": tw_started("PASS"),
            "E-O": NOT_STARTED,
        }
        activity = regression.project_activity(run, source)
        self.assertEqual(activity["activity_state"], "完了")
        self.assertEqual(activity["counts"]["auxiliary_required_count"], 0)
        self.assertEqual(check(activity_doc(run, source), "REG-D011"), "pass")

    def test_auxiliary_only_run_progresses_from_measurement(self):
        run = {
            **V2,
            "required_routes": [],
            "auxiliary_routes": [aux("A", "E-A")],
            "auxiliary_testware_count": 1,
        }
        steps = [
            (NOT_STARTED, "未開始"),
            ({**NOT_STARTED, "blocked": True}, "ブロック中"),
            (aux_started("PASS", finalized=False), "実行中"),
            (aux_started("PASS"), "完了"),
        ]
        for source_a, expected in steps:
            with self.subTest(expected=expected, source=source_a):
                source = {"E-A": source_a}
                activity = regression.project_activity(run, source)
                self.assertEqual(activity["activity_state"], expected)
                doc = activity_doc(run, source)
                self.assertEqual(check(doc, "REG-D011"), "pass")
                self.assertEqual(check(doc, "REG-D015"), "pass")
        # 補助PASSは正式TCのexecution / coverage分子へ入らない。
        counts = regression.project_activity(run, {"E-A": aux_started("PASS")})[
            "counts"
        ]
        self.assertEqual(counts["tc_member_count"], 0)
        self.assertEqual(counts["executed_tc_count"], 0)
        self.assertEqual(counts["source_result_counts"], {})
        self.assertEqual(counts["auxiliary_source_result_counts"], {"PASS": 1})

    def test_empty_sets_never_complete(self):
        activity = regression.project_activity(
            {
                "route_contract_version": "2",
                "required_routes": [],
                "auxiliary_routes": [aux("OPT", "E", required=False)],
                "auxiliary_testware_count": 1,
            },
            {},
        )
        self.assertEqual(activity["activity_state"], "未開始")
        forced = {
            **activity_doc(
                {**V2, "required_routes": [], "auxiliary_testware_count": 0}, {}
            ),
            "activity_state": "完了",
        }
        self.assertEqual(check(forced, "REG-D011"), "fail")

    def test_partial_run_with_two_required_auxiliaries(self):
        run = {
            "route_contract_version": "2",
            "required_routes": [],
            "auxiliary_routes": [aux("A", "E-A"), aux("B", "E-B")],
        }
        source = {"E-A": aux_started("PASS"), "E-B": NOT_STARTED}
        activity = regression.project_activity(run, source)
        self.assertEqual(activity["activity_state"], "部分完了（ブロック中あり）")
        self.assertEqual(activity["counts"]["auxiliary_required_completed_count"], 1)

    def test_timeout_then_retry_uses_latest_finalized_attempt(self):
        run = {
            **V2,
            "required_routes": [],
            "auxiliary_routes": [aux("A", "E-A")],
            "auxiliary_testware_count": 1,
        }
        timeout = {
            "E-A": aux_started(
                "timeout",
                finalized=False,
                attempt_ref="attempt-1",
                raw_capture_complete=False,
            )
        }
        self.assertEqual(
            regression.project_activity(run, timeout)["activity_state"], "実行中"
        )
        retry = {"E-A": aux_started("FAIL", attempt_ref="attempt-2")}
        done = regression.project_activity(run, retry)
        self.assertEqual(done["activity_state"], "完了")
        self.assertEqual(done["auxiliary_route_results"][0]["attempt_ref"], "attempt-2")
        self.assertEqual(done["auxiliary_route_results"][0]["source_result"], "FAIL")

    def test_skip_runner_error_and_unconfirmed_runner_result_do_not_complete(self):
        run = {
            **V2,
            "required_routes": [],
            "auxiliary_routes": [aux("A", "E-A")],
            "auxiliary_testware_count": 1,
        }
        cases = {
            "skip": {**NOT_STARTED, "source_result": "skipped"},
            "runner_error": {**NOT_STARTED, "blocked": True, "source_result": "error"},
            "unconfirmed_start": {
                "start_state": "開始済み",
                "actual_start_confirmed": False,
                "result_finalized": True,
                "source_result": "PASS",
            },
        }
        for name, source_a in cases.items():
            with self.subTest(name):
                activity = regression.project_activity(run, {"E-A": source_a})
                self.assertNotEqual(activity["activity_state"], "完了")
                self.assertFalse(activity["auxiliary_route_results"][0]["executed"])

    def test_raw_capture_attempt_and_cleanup_must_be_confirmed(self):
        run = {
            **V2,
            "required_routes": [],
            "auxiliary_routes": [aux("A", "E-A")],
            "auxiliary_testware_count": 1,
        }
        raw = regression.project_activity(
            run, {"E-A": aux_started("PASS", raw_capture_complete=False)}
        )
        self.assertEqual(raw["activity_state"], "実行中")
        no_attempt = regression.project_activity(
            run, {"E-A": aux_started("PASS", attempt_ref=None)}
        )
        self.assertEqual(no_attempt["activity_state"], "実行中")
        for cleanup in ("失敗", "未確認", "一部失敗", "進行中"):
            with self.subTest(cleanup=cleanup):
                source = {"E-A": aux_started("PASS", cleanup_status=cleanup)}
                activity = regression.project_activity(run, source)
                self.assertNotEqual(activity["activity_state"], "完了")
                forged = {**activity_doc(run, source), "activity_state": "完了"}
                self.assertEqual(check(forged, "REG-D011"), "fail")
        # activity全体のcleanup未確認もTC route・補助routeの双方で完了を妨げる。
        tc_run = {
            **V2,
            "required_routes": [tc_route("TC-1", "X-1")],
            "auxiliary_testware_count": 0,
        }
        tc_source = {"X-1": tw_started("PASS")}
        self.assertNotEqual(
            regression.project_activity(tc_run, tc_source, cleanup_status="未確認")[
                "activity_state"
            ],
            "完了",
        )

    def test_old_build_result_is_not_counted_for_current_run(self):
        run = {
            "route_contract_version": "2",
            "required_routes": [tc_route("TC-1", "X-1")],
            "auxiliary_routes": [aux("A", "E-A")],
        }
        source = {
            "X-1": started("PASS", implementation_revision="rev-OLD"),
            "E-A": aux_started("PASS", revision="rev-OLD"),
        }
        activity = regression.project_activity(run, source)
        self.assertNotEqual(activity["activity_state"], "完了")
        self.assertEqual(activity["tc_execution_state"], {"TC-1": "blocked"})
        self.assertEqual(activity["counts"]["executed_tc_count"], 0)
        self.assertEqual(activity["counts"]["auxiliary_executed_count"], 0)
        self.assertTrue(
            any(
                v.startswith("implementation_revision_mismatch")
                for v in activity["unresolved"]
            )
        )
        doc = activity_doc(run, source)
        self.assertEqual(check(doc, "REG-D010"), "pass")
        # 旧buildの実行をexecutedへ偽装したActivityは独立再計算で検出される。
        forged = copy.deepcopy(doc)
        forged["route_results"][0]["executed"] = True
        self.assertEqual(check(forged, "REG-D010"), "fail")
        forged_aux = copy.deepcopy(doc)
        forged_aux["auxiliary_route_results"][0]["executed"] = True
        self.assertEqual(check(forged_aux, "REG-D015"), "fail")

    def test_auxiliary_cannot_share_execution_with_tc_route(self):
        run = {
            "route_contract_version": "2",
            "required_routes": [tc_route("TC-1", "X-1")],
            "auxiliary_routes": [aux("A", "X-1")],
        }
        source = {"X-1": aux_started("PASS")}
        activity = regression.project_activity(run, source)
        self.assertNotEqual(activity["activity_state"], "完了")
        self.assertFalse(activity["auxiliary_route_results"][0]["executed"])
        # TC routeと補助routeが同じ実行を参照する構成自体を分離違反として拒否する。
        shared = activity_doc(run, source)
        self.assertEqual(check(shared, "REG-D015"), "fail")
        self.assertEqual(
            check({**shared, "activity_state": "完了"}, "REG-D011"), "fail"
        )

    def test_mixed_manual_e2e_testware_and_auxiliary_keep_counts_separate(self):
        run = {
            "route_contract_version": "2",
            "required_routes": [
                tc_route("TC-1", "M-1", "manual"),
                tc_route("TC-1", "E-1", "e2e", e2e_testware_ref="E2E-1"),
                tc_route("TC-2", "X-2"),
            ],
            "auxiliary_routes": [aux("A", "E-A"), aux("OPT", "E-O", required=False)],
            "auxiliary_testware_count": 2,
        }
        source = {
            "M-1": started("FAIL"),
            "E-1": started("PASS"),
            "X-2": tw_started("PASS"),
            "E-A": aux_started("PASS"),
            "E-O": NOT_STARTED,
        }
        doc = activity_doc(run, source)
        self.assertEqual(doc["activity_state"], "完了")
        counts = doc["counts"]
        self.assertEqual(counts["tc_member_count"], 2)
        self.assertEqual(counts["executed_tc_count"], 2)
        self.assertEqual(counts["source_result_counts"], {"FAIL": 1, "PASS": 2})
        self.assertEqual(counts["auxiliary_testware_count"], 2)
        self.assertEqual(counts["auxiliary_executed_count"], 1)
        for assertion in ("REG-D010", "REG-D011", "REG-D015"):
            self.assertEqual(check(doc, assertion), "pass", assertion)
        # 補助PASSを正式TC件数へ混ぜたActivityはD015で拒否する。
        mixed = copy.deepcopy(doc)
        mixed["counts"]["executed_tc_count"] = 3
        mixed["counts"]["source_result_counts"] = {"FAIL": 1, "PASS": 3}
        self.assertEqual(check(mixed, "REG-D015"), "fail")
        with_tc_ref = copy.deepcopy(doc)
        with_tc_ref["auxiliary_route_results"][0]["tc_ref"] = "TC-1"
        self.assertEqual(check(with_tc_ref, "REG-D015"), "fail")

    def test_unprojected_auxiliary_raw_result_fails_validator(self):
        run = {
            **V2,
            "required_routes": [],
            "auxiliary_routes": [aux("A", "E-A")],
            "auxiliary_testware_count": 1,
        }
        source = {"E-A": aux_started("PASS", raw_capture_complete=False)}
        doc = activity_doc(run, source)
        self.assertEqual(check(doc, "REG-D015"), "pass")
        forged = copy.deepcopy(doc)
        forged["auxiliary_route_results"][0]["raw_capture_complete"] = True
        forged["activity_state"] = "完了"
        self.assertEqual(check(forged, "REG-D015"), "fail")
        self.assertEqual(check(forged, "REG-D011"), "fail")


class LegacyCompatibilityTests(unittest.TestCase):
    def test_legacy_run_without_auxiliary_still_completes(self):
        run = {"required_routes": [tc_route("TC-1", "M-1", "manual")]}
        activity = regression.project_activity(run, {"M-1": started("PASS")})
        self.assertEqual(activity["activity_state"], "完了")

    def test_legacy_auxiliary_obligation_unknown_is_blocked(self):
        legacy_entry = {"testware_ref": "A", "execution_ref": "E-A"}
        for run in (
            {
                "required_routes": [tc_route("TC-1", "M-1", "manual")],
                "auxiliary_routes": [legacy_entry],
            },
            {
                "required_routes": [tc_route("TC-1", "M-1", "manual")],
                "auxiliary_testware_refs": ["A"],
            },
        ):
            with self.subTest(run=run):
                source = {"M-1": started("PASS"), "E-A": aux_started("PASS")}
                activity = regression.project_activity(run, source)
                self.assertEqual(
                    activity["activity_state"], "部分完了（ブロック中あり）"
                )
                self.assertEqual(
                    activity["counts"]["auxiliary_obligation_unknown_count"], 1
                )
                self.assertIn("auxiliary_obligation_unknown:A", activity["unresolved"])
                forced = {**activity_doc(run, source), "activity_state": "完了"}
                self.assertEqual(check(forced, "REG-D011"), "fail")

    def test_stored_legacy_activity_remains_valid_and_immutable(self):
        fixture = (
            SKILL / "evals" / "output" / "cases" / "reg-out-002" / "output.md"
        ).read_text(encoding="utf-8")
        self.assertNotIn("route_contract_version", fixture)
        result = validator.validate(
            fixture, {"artifact_type": "activity"}, "REG-OUT-002"
        )
        self.assertTrue(
            all(item.status == "pass" for item in result.assertions),
            [(i.id, i.status) for i in result.assertions],
        )
        legacy_completed = {
            "activity_state": "完了",
            "scope_identity": "s",
            "snapshot_ref": "d",
        }
        update = regression.update_activity(legacy_completed, legacy_completed)
        self.assertEqual(update["reason"], "completed_activity_is_immutable")
        self.assertEqual(update["resolution"], "create_new_activity_or_run_revision")
        # 旧形式のまま完了済みの履歴を検証しても、補助義務を遡って要求しない。
        legacy_doc = {
            "artifact_type": "activity",
            "activity_ref": "A",
            "snapshot_ref": "d",
            "scope_identity": "s",
            "activity_state": "完了",
            "cleanup_status": "対象なし",
            "unresolved": [],
            "source_executions": {"M-1": started("PASS")},
            "route_results": [
                {
                    "tc_ref": "TC-1",
                    "route_ref": "manual",
                    "execution_ref": "M-1",
                    "executed": True,
                    "result_finalized": True,
                    "source_result_projectable": True,
                    "source_result": "PASS",
                }
            ],
            "tc_execution_state": {"TC-1": "executed"},
            "counts": {"auxiliary_testware_count": 1},
            "auxiliary_route_results": [{"testware_ref": "A"}],
        }
        self.assertEqual(check(legacy_doc, "REG-D011"), "pass")
        self.assertEqual(check(legacy_doc, "REG-D015"), "pass")

    def test_completion_required_needs_contract_version(self):
        run = {
            "artifact_type": "run",
            "run_scope": "selected",
            "suite_complete": False,
            "baseline": {"member_tc_refs": []},
            "selected_tc_refs": [],
            "required_routes": [],
            "auxiliary_routes": [aux("A", "E-A")],
            "auxiliary_testware_refs": ["A"],
            "auxiliary_testware_count": 1,
        }
        self.assertEqual(check(run, "REG-D009"), "fail")
        self.assertEqual(
            check({**run, "route_contract_version": "2"}, "REG-D009"), "pass"
        )
        legacy = {
            **run,
            "auxiliary_routes": [{"testware_ref": "A", "execution_ref": "E-A"}],
        }
        self.assertEqual(check(legacy, "REG-D009"), "pass")
        invalid_v2 = {
            **run,
            "route_contract_version": "2",
            "auxiliary_routes": [{"testware_ref": "A", "execution_ref": "E-A"}],
        }
        self.assertEqual(check(invalid_v2, "REG-D009"), "fail")

    def test_resolve_legacy_obligations_creates_new_revision_without_mutation(self):
        legacy_run = {
            "required_routes": [tc_route("TC-1", "M-1", "manual")],
            "auxiliary_routes": [{"testware_ref": "A", "execution_ref": "E-A"}],
            "auxiliary_testware_refs": ["A", "B"],
            "auxiliary_testware_count": 2,
        }
        snapshot = copy.deepcopy(legacy_run)
        details = {
            "A": {
                "executor_owner": "testware-execution",
                "implementation_revision": REV,
            },
            "B": {
                "executor_owner": "e2e-test-execution",
                "implementation_revision": REV,
            },
        }
        blocked = regression.resolve_auxiliary_obligations(
            legacy_run,
            user_explicit_refs=["A"],
            policy_refs=[],
            testware_details=details,
        )
        self.assertEqual(blocked["status"], "blocked")
        self.assertEqual(blocked["unresolved_refs"], ["B"])
        self.assertIsNone(blocked["run"])
        ready = regression.resolve_auxiliary_obligations(
            legacy_run,
            user_explicit_refs=["A"],
            policy_refs=[],
            reference_only_refs=["B"],
            testware_details=details,
        )
        self.assertEqual(ready["status"], "ready")
        self.assertTrue(ready["new_revision_required"])
        entries = {e["testware_ref"]: e for e in ready["run"]["auxiliary_routes"]}
        self.assertIs(entries["A"]["completion_required"], True)
        self.assertEqual(entries["A"]["execution_ref"], "E-A")
        self.assertIs(entries["B"]["completion_required"], False)
        self.assertEqual(ready["run"]["route_contract_version"], "2")
        self.assertEqual(legacy_run, snapshot)
        self.assertTrue(
            regression.validate_auxiliary_routes(ready["run"]["auxiliary_routes"])[
                "valid"
            ]
        )
        missing_detail = regression.resolve_auxiliary_obligations(
            legacy_run, user_explicit_refs=["A", "B"], policy_refs=[]
        )
        self.assertEqual(missing_detail["status"], "blocked")
        self.assertEqual(missing_detail["missing_detail_refs"], ["A", "B"])

    def test_non_completed_legacy_activity_can_resume_with_new_contract(self):
        existing = {
            "activity_state": "実行中",
            "scope_identity": "s",
            "snapshot_ref": "d",
        }
        run = {"required_routes": [tc_route("TC-1", "M-1", "manual")]}
        incoming = {
            **regression.project_activity(run, {"M-1": started("PASS")}),
            "scope_identity": "s",
            "snapshot_ref": "d",
        }
        self.assertEqual(
            regression.update_activity(existing, incoming)["status"], "update_allowed"
        )


class VitestFixtureTests(unittest.TestCase):
    """固定qa-training-store commitで取得したVitest JSON形式のRun→Activity判定。"""

    def setUp(self):
        self.fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def test_fixture_is_pinned_to_a_commit(self):
        self.assertRegex(self.fixture["repo_revision"], r"^[0-9a-f]{40}$")
        self.assertEqual(self.fixture["runner"], "vitest")

    def _result_by_identity(self):
        # 永続識別はrepo revision・file・test名／階層。runner内部の一時IDは使わない。
        return {
            (
                self.fixture["repo_revision"],
                f["file"],
                tuple(t["ancestorTitles"]),
                t["title"],
            ): t
            for f in self.fixture["files"]
            for t in f["tests"]
        }

    def test_tc_linked_vitest_selection_to_activity(self):
        results = self._result_by_identity()
        pick = [
            ("tests/unit/password-hasher.test.ts", 0),
            ("tests/unit/app-config.test.ts", 0),
        ]
        routes, source = [], {}
        for index, (file, offset) in enumerate(pick, start=1):
            entry = next(f for f in self.fixture["files"] if f["file"] == file)
            test = entry["tests"][offset]
            identity = (
                self.fixture["repo_revision"],
                file,
                tuple(test["ancestorTitles"]),
                test["title"],
            )
            self.assertIn(identity, results)
            ref = f"vitest:{file}::{test['fullName']}"
            routes.append(
                {
                    "tc_ref": f"TC-{index:03d}",
                    "route_type": "testware",
                    "route_ref": f"testware:{index}",
                    "testware_ref": ref,
                    "executor_owner": "testware-execution",
                    "implementation_revision": self.fixture["repo_revision"],
                    "selection_basis": f"{file} :: {test['fullName']}",
                    "execution_ref": f"EXEC-{index}",
                }
            )
            passed = test["status"] == "passed"
            source[f"EXEC-{index}"] = started(
                "PASS" if passed else "FAIL",
                implementation_revision=self.fixture["repo_revision"],
                attempt_ref=f"attempt-{index}",
                raw_capture_complete=True,
                cleanup_status="対象なし",
            )
        validated = regression.validate_required_routes(routes)
        self.assertTrue(validated["valid"], validated["issues"])
        run = {**V2, "required_routes": routes, "auxiliary_testware_count": 0}
        doc = activity_doc(run, source)
        self.assertEqual(doc["activity_state"], "完了")
        self.assertEqual(doc["counts"]["tc_member_count"], 2)
        self.assertEqual(doc["counts"]["executed_tc_count"], 2)
        for assertion in ("REG-D010", "REG-D011", "REG-D015"):
            self.assertEqual(check(doc, assertion), "pass", assertion)
        # 同じ結果を別revision（旧build）として受け取ると今回Runの実行にしない。
        stale_source = {
            key: {**value, "implementation_revision": "0" * 40}
            for key, value in source.items()
        }
        stale = regression.project_activity(run, stale_source)
        self.assertEqual(stale["activity_state"], "ブロック中")
        self.assertEqual(stale["counts"]["executed_tc_count"], 0)

    def test_tc_less_vitest_file_as_required_auxiliary(self):
        entry = self.fixture["files"][0]
        ref = f"vitest:{entry['file']}"
        run = {
            "route_contract_version": "2",
            "required_routes": [],
            "auxiliary_routes": [
                aux(
                    ref,
                    "EXEC-AUX",
                    implementation_revision=self.fixture["repo_revision"],
                )
            ],
            "auxiliary_testware_count": 1,
        }
        source = {
            "EXEC-AUX": aux_started(
                "PASS" if entry["status"] == "passed" else "FAIL",
                revision=self.fixture["repo_revision"],
            )
        }
        doc = activity_doc(run, source)
        self.assertEqual(doc["activity_state"], "完了")
        self.assertEqual(doc["counts"]["tc_member_count"], 0)
        self.assertEqual(doc["counts"]["auxiliary_required_completed_count"], 1)
        self.assertEqual(check(doc, "REG-D015"), "pass")


class ReviewHardeningTests(unittest.TestCase):
    """PR #30のレビュー指摘（偽装・欠落入力・誤った状態判定）の回帰テスト。"""

    def aux_only(self, source_a, **aux_extra):
        run = {
            **V2,
            "required_routes": [],
            "auxiliary_routes": [aux("A", "E-A", **aux_extra)],
            "auxiliary_testware_count": 1,
        }
        source = {"E-A": source_a}
        return run, source, activity_doc(run, source)

    def run_doc(self, **extra):
        return {
            "artifact_type": "run",
            "run_scope": "selected",
            "baseline": {
                "complete": True,
                "currentness": "current",
                "member_tc_refs": ["TC-1"],
            },
            "selected_tc_refs": ["TC-1"],
            "suite_complete": False,
            "required_routes": [tc_route("TC-1", "X-1")],
            "auxiliary_testware_count": 1,
            "auxiliary_testware_refs": ["A"],
            "auxiliary_routes": [aux("A", "E-A")],
            **V2,
            **extra,
        }

    def test_run_validator_does_not_crash_on_unhashable_refs(self):
        self.assertEqual(check(self.run_doc(), "REG-D009"), "pass")
        for broken in (
            self.run_doc(auxiliary_routes=[aux({"x": 1}, "E-A")]),
            self.run_doc(auxiliary_routes=[aux(["A"], "E-A")]),
            self.run_doc(auxiliary_testware_refs=[{"x": 1}]),
            self.run_doc(auxiliary_testware_refs=5),
        ):
            with self.subTest(broken=broken):
                self.assertEqual(check(broken, "REG-D009"), "fail")
        bad_route = self.run_doc(
            required_routes=[{"route_type": "testware", "testware_ref": []}]
        )
        self.assertEqual(check(bad_route, "REG-D008"), "fail")
        self.assertEqual(check(self.run_doc(required_routes={}), "REG-D008"), "fail")

    def test_unsupported_contract_version_is_rejected_not_treated_as_legacy(self):
        run = {
            **V2,
            "required_routes": [tc_route("TC-1", "X-1")],
            "auxiliary_routes": [aux("A", "E-A")],
        }
        source = {
            "X-1": tw_started("PASS"),
            "E-A": NOT_STARTED,
        }
        forged = {**activity_doc(run, source), "activity_state": "完了"}
        for version in (2, "3", None):
            with self.subTest(version=version):
                doc = {**forged, "route_contract_version": version}
                self.assertEqual(check(doc, "REG-D011"), "fail")
                self.assertEqual(check(doc, "REG-D015"), "fail")
                self.assertEqual(
                    check(self.run_doc(route_contract_version=version), "REG-D009"),
                    "fail",
                )

    def test_non_list_auxiliary_results_do_not_bypass_validation(self):
        run, source, doc = self.aux_only(NOT_STARTED)
        forged = {**doc, "activity_state": "完了", "auxiliary_route_results": {}}
        forged["counts"] = {**doc["counts"], "auxiliary_testware_count": 0}
        self.assertEqual(check(forged, "REG-D015"), "fail")
        for field, value in (
            ("source_executions", []),
            ("tc_execution_state", []),
            ("route_results", {}),
        ):
            with self.subTest(field=field):
                broken = {**doc, field: value}
                self.assertEqual(check(broken, "REG-D010"), "fail")

    def test_expected_state_and_required_auxiliary_refs_are_checked_against_fixture(
        self,
    ):
        run = {
            **V2,
            "required_routes": [tc_route("TC-1", "X-1")],
            "auxiliary_routes": [aux("A", "E-A")],
        }
        source = {
            "X-1": tw_started("PASS"),
            "E-A": NOT_STARTED,
        }
        doc = activity_doc(run, source)
        expected = {
            "artifact_type": "activity",
            "activity_state": "部分完了（ブロック中あり）",
            "required_auxiliary_refs": ["A"],
        }

        def d014(document, exp):
            rendered = "```json\n" + json.dumps(document, ensure_ascii=False) + "\n```"
            result = validator.validate(rendered, exp, "H-UNIT")
            return next(i.status for i in result.assertions if i.id == "REG-D014")

        self.assertEqual(d014(doc, expected), "pass")
        self.assertEqual(d014({**doc, "activity_state": "実行中"}, expected), "fail")
        dropped = copy.deepcopy(doc)
        dropped["auxiliary_route_results"][0]["completion_required"] = False
        self.assertEqual(d014(dropped, expected), "fail")
        removed = copy.deepcopy(doc)
        removed["auxiliary_route_results"] = []
        self.assertEqual(d014(removed, expected), "fail")

    def test_forged_auxiliary_completion_and_unknown_counts_are_detected(self):
        run, source, doc = self.aux_only(NOT_STARTED)
        self.assertEqual(check(doc, "REG-D015"), "pass")
        for field, value in (
            ("auxiliary_required_completed_count", 1),
            ("auxiliary_obligation_unknown_count", 1),
        ):
            with self.subTest(field=field):
                forged = copy.deepcopy(doc)
                forged["counts"][field] = value
                self.assertEqual(check(forged, "REG-D015"), "fail")

    def test_executed_tc_count_comes_from_routes_not_state_entries(self):
        run = {
            **V2,
            "required_routes": [tc_route("TC-1", "X-1")],
            "auxiliary_routes": [],
        }
        doc = activity_doc(run, {"X-1": NOT_STARTED})
        self.assertEqual(check(doc, "REG-D015"), "pass")
        forged = copy.deepcopy(doc)
        forged["tc_execution_state"]["TC-GHOST"] = "executed"
        forged["counts"]["executed_tc_count"] = 1
        self.assertEqual(check(forged, "REG-D015"), "fail")
        self.assertEqual(check(forged, "REG-D010"), "fail")

    def test_selection_without_details_is_not_execution_ready(self):
        selection_only = regression.select_auxiliary_testware(
            requested_refs=["A"],
            user_explicit_refs=["A"],
            policy_refs=[],
            available_refs=["A"],
        )
        self.assertEqual(selection_only["selected_refs"], ["A"])
        self.assertFalse(selection_only["execution_ready"])
        self.assertNotIn("executor_owner", selection_only["auxiliary_routes"][0])
        detailed = regression.select_auxiliary_testware(
            requested_refs=["A"],
            user_explicit_refs=["A"],
            policy_refs=[],
            available_refs=["A"],
            testware_details={
                "A": {
                    "executor_owner": "testware-execution",
                    "implementation_revision": REV,
                }
            },
        )
        self.assertTrue(detailed["execution_ready"])
        self.assertTrue(
            regression.validate_auxiliary_routes(detailed["auxiliary_routes"])["valid"]
        )

    def test_normalized_required_routes_keep_execution_ref(self):
        routes = [tc_route("TC-1", "X-1"), tc_route("TC-2", "M-2", "manual")]
        normalized = regression.validate_required_routes(routes)["routes"]
        self.assertEqual([r["execution_ref"] for r in normalized], ["X-1", "M-2"])
        run = {"required_routes": normalized}
        source = {
            "X-1": tw_started("PASS"),
            "M-2": started("PASS"),
        }
        self.assertEqual(
            regression.project_activity(run, source)["activity_state"], "完了"
        )

    def test_required_auxiliary_without_declared_revision_never_completes(self):
        run = {
            **V2,
            "required_routes": [],
            "auxiliary_routes": [aux("A", "E-A", implementation_revision="")],
        }
        source = {"E-A": aux_started("PASS")}
        activity = regression.project_activity(run, source)
        self.assertNotEqual(activity["activity_state"], "完了")
        self.assertIn("implementation_revision_missing:A", activity["unresolved"])
        self.assertEqual(activity["counts"]["auxiliary_required_completed_count"], 0)
        doc = activity_doc(run, source)
        self.assertEqual(check({**doc, "activity_state": "完了"}, "REG-D011"), "fail")
        self.assertEqual(check(doc, "REG-D015"), "pass")
        # testware route（TC付き）も宣言revisionが無ければ開始として数えない。
        tc_run = {
            "required_routes": [tc_route("TC-1", "X-1", implementation_revision="")]
        }
        tc_activity = regression.project_activity(tc_run, {"X-1": tw_started("PASS")})
        self.assertNotEqual(tc_activity["activity_state"], "完了")

    def test_legacy_run_completion_required_is_not_trusted(self):
        legacy_aux = aux("A", "E-A", required=False)
        run = {
            "required_routes": [tc_route("TC-1", "M-1", "manual")],
            "auxiliary_routes": [legacy_aux],
        }
        source = {"M-1": started("PASS"), "E-A": NOT_STARTED}
        activity = regression.project_activity(run, source)
        self.assertNotEqual(activity["activity_state"], "完了")
        self.assertIn("auxiliary_obligation_unknown:A", activity["unresolved"])
        blocked = regression.resolve_auxiliary_obligations(
            run, user_explicit_refs=[], policy_refs=[]
        )
        self.assertEqual(blocked["status"], "blocked")
        self.assertIsNone(blocked["run"])
        ready = regression.resolve_auxiliary_obligations(
            run, user_explicit_refs=["A"], policy_refs=[]
        )
        self.assertEqual(ready["status"], "ready")
        self.assertTrue(ready["run"]["auxiliary_routes"][0]["completion_required"])

    def test_missing_auxiliary_cleanup_status_is_unconfirmed(self):
        source_a = aux_started("PASS")
        del source_a["cleanup_status"]
        run, source, doc = self.aux_only(source_a)
        self.assertNotEqual(doc["activity_state"], "完了")
        self.assertEqual(doc["auxiliary_route_results"][0]["cleanup_status"], "未確認")
        self.assertEqual(check({**doc, "activity_state": "完了"}, "REG-D011"), "fail")
        self.assertEqual(check(doc, "REG-D015"), "pass")
        explicit = {"E-A": aux_started("PASS", cleanup_status="対象なし")}
        self.assertEqual(
            regression.project_activity(run, explicit)["activity_state"], "完了"
        )

    def test_auxiliary_completed_count_requires_closed_cleanup(self):
        _, _, doc = self.aux_only(aux_started("PASS", cleanup_status="失敗"))
        self.assertEqual(doc["counts"]["auxiliary_required_completed_count"], 0)
        self.assertEqual(doc["counts"]["auxiliary_executed_count"], 1)
        self.assertEqual(check(doc, "REG-D015"), "pass")

    def test_partially_started_tc_routes_are_partial_not_blocked(self):
        run = {
            "required_routes": [
                tc_route("TC-1", "M-1", "manual"),
                tc_route("TC-1", "X-1"),
            ]
        }
        source = {
            "M-1": started("PASS"),
            "X-1": {**NOT_STARTED, "blocked": True},
        }
        activity = regression.project_activity(run, source)
        self.assertEqual(activity["activity_state"], "部分完了（ブロック中あり）")
        self.assertEqual(activity["counts"]["executed_tc_count"], 0)
        self.assertEqual(activity["counts"]["blocked_tc_count"], 1)


def check_with_run(doc, assertion, run=None):
    rendered = "```json\n" + json.dumps(doc, ensure_ascii=False) + "\n```"
    result = validator.validate(rendered, {}, "H-UNIT", run=run)
    return next(item.status for item in result.assertions if item.id == assertion)


class RunVerificationTests(unittest.TestCase):
    """Activityの申告ではなく保存済みRunを正本として実施義務を照合する。"""

    def setUp(self):
        self.run = {
            **V2,
            "artifact_type": "run",
            "required_routes": [
                tc_route("TC-1", "M-1", "manual"),
                tc_route("TC-1", "X-1"),
            ],
            "auxiliary_routes": [
                aux("A", "E-A"),
                aux("OPT", "E-O", required=False),
            ],
            "auxiliary_testware_refs": ["A", "OPT"],
            "auxiliary_testware_count": 2,
        }
        self.source = {
            "M-1": started("PASS"),
            "X-1": tw_started("PASS"),
            "E-A": NOT_STARTED,
            "E-O": NOT_STARTED,
        }
        self.doc = activity_doc(self.run, self.source)

    def test_consistent_activity_passes_run_verification(self):
        self.assertEqual(check_with_run(self.doc, "REG-D018", self.run), "pass")
        self.assertTrue(
            regression.verify_activity_against_run(self.run, self.doc)["valid"]
        )

    def test_removed_required_auxiliary_is_rejected_even_when_counts_are_adjusted(self):
        forged = copy.deepcopy(self.doc)
        forged["auxiliary_route_results"] = [
            i for i in forged["auxiliary_route_results"] if i["testware_ref"] != "A"
        ]
        counts = forged["counts"]
        counts.update(
            auxiliary_testware_count=1,
            auxiliary_required_count=0,
            auxiliary_required_completed_count=0,
        )
        forged["activity_state"] = "完了"
        # Activity単体の検証（D011/D015）は、自己整合した改ざんを通してしまう。
        self.assertEqual(check_with_run(forged, "REG-D011"), "pass")
        self.assertEqual(check_with_run(forged, "REG-D015"), "pass")
        # Runを渡さない経路では、完了の主張をRun照合済みとして受け入れない。
        self.assertEqual(check_with_run(forged, "REG-D018"), "fail")
        # 保存済みRunと照合すれば、欠落した義務を検出する。
        self.assertEqual(check_with_run(forged, "REG-D018", self.run), "fail")
        self.assertFalse(
            regression.verify_activity_against_run(self.run, forged)["valid"]
        )

    def test_changed_completion_required_is_rejected(self):
        forged = copy.deepcopy(self.doc)
        item = next(
            i for i in forged["auxiliary_route_results"] if i["testware_ref"] == "A"
        )
        item["completion_required"] = False
        forged["counts"]["auxiliary_required_count"] = 0
        forged["activity_state"] = "完了"
        self.assertEqual(check_with_run(forged, "REG-D018", self.run), "fail")
        self.assertFalse(
            regression.verify_activity_against_run(self.run, forged)["valid"]
        )

    def test_added_duplicated_and_missing_routes_are_rejected(self):
        added = copy.deepcopy(self.doc)
        extra = copy.deepcopy(added["auxiliary_route_results"][0])
        extra["testware_ref"] = "GHOST"
        added["auxiliary_route_results"].append(extra)
        duplicated = copy.deepcopy(self.doc)
        duplicated["route_results"].append(
            copy.deepcopy(duplicated["route_results"][0])
        )
        missing = copy.deepcopy(self.doc)
        missing["route_results"] = missing["route_results"][:1]
        for name, forged in (
            ("added", added),
            ("duplicated", duplicated),
            ("missing", missing),
        ):
            with self.subTest(name=name):
                self.assertEqual(check_with_run(forged, "REG-D018", self.run), "fail")
                self.assertFalse(
                    regression.verify_activity_against_run(self.run, forged)["valid"]
                )

    def test_legacy_run_obligations_cannot_be_dropped_by_activity(self):
        legacy_run = {
            **self.run,
            "auxiliary_routes": [],
            "auxiliary_testware_refs": ["OLD"],
            "auxiliary_testware_count": 1,
        }
        del legacy_run["route_contract_version"]
        dropped = {**self.doc, "auxiliary_route_results": []}
        self.assertEqual(check_with_run(dropped, "REG-D018", legacy_run), "fail")

    def test_run_must_be_supplied_to_accept_a_completion_claim(self):
        completed_run = {
            **self.run,
            "auxiliary_routes": [aux("OPT", "E-O", required=False)],
            "auxiliary_testware_refs": ["OPT"],
            "auxiliary_testware_count": 1,
        }
        doc = activity_doc(completed_run, self.source)
        self.assertEqual(doc["activity_state"], "完了")
        self.assertEqual(check_with_run(doc, "REG-D018"), "fail")
        self.assertEqual(check_with_run(doc, "REG-D018", completed_run), "pass")
        # 完了を主張しない場合は警告にとどめ、Run照合済みとは扱わない。
        self.assertEqual(check_with_run(self.doc, "REG-D018"), "warning")
        # Runがobjectでない・種別が違う場合も例外にせず拒否する。
        for bad_run in ({}, [], "run", {"artifact_type": "activity"}):
            with self.subTest(run=bad_run):
                self.assertEqual(check_with_run(doc, "REG-D018", bad_run), "fail")
        self.assertFalse(regression.verify_activity_against_run([], doc)["valid"])

    def test_legacy_activity_is_outside_run_verification(self):
        legacy = {
            "artifact_type": "activity",
            "activity_state": "完了",
            "route_results": [],
        }
        self.assertEqual(check_with_run(legacy, "REG-D018"), "pass")

    def test_fixture_runs_verify_the_saved_output_cases(self):
        cases = SKILL / "evals" / "output" / "cases"
        for case in ("reg-out-004", "reg-out-005"):
            with self.subTest(case=case):
                expected = json.loads(
                    (cases / case / "expected.json").read_text(encoding="utf-8")
                )
                text = (cases / case / "output.md").read_text(encoding="utf-8")
                document = json.loads(
                    text.split("```json\n", 1)[1].split("\n```", 1)[0]
                )
                self.assertEqual(
                    validator.validate_activity_against_run(document, expected["run"]),
                    [],
                )
                self.assertTrue(
                    regression.verify_activity_against_run(expected["run"], document)[
                        "valid"
                    ]
                )
                dropped = copy.deepcopy(document)
                dropped["auxiliary_route_results"] = []
                self.assertTrue(
                    validator.validate_activity_against_run(dropped, expected["run"])
                )


class TestwareOwnerContractTests(unittest.TestCase):
    """testware routeはcleanup・attempt・raw取得をownerが明示するまで完了にしない。"""

    def run_for(self):
        return {
            **V2,
            "required_routes": [tc_route("TC-1", "X-1")],
            "auxiliary_testware_count": 0,
        }

    def project(self, source):
        run = self.run_for()
        return run, activity_doc(run, {"X-1": source})

    def test_missing_cleanup_is_unconfirmed_not_not_applicable(self):
        source = tw_started("PASS")
        del source["cleanup_status"]
        _, doc = self.project(source)
        self.assertNotEqual(doc["activity_state"], "完了")
        self.assertEqual(doc["route_results"][0]["cleanup_status"], "未確認")
        self.assertEqual(check({**doc, "activity_state": "完了"}, "REG-D011"), "fail")
        self.assertEqual(check(doc, "REG-D010"), "pass")

    def test_unclosed_cleanup_states_never_complete(self):
        for state in (
            "未確認",
            "失敗",
            "一部失敗",
            "進行中",
            "",
            None,
            ["x"],
            {"a": 1},
        ):
            with self.subTest(cleanup=state):
                _, doc = self.project(tw_started("PASS", cleanup_status=state))
                self.assertNotEqual(doc["activity_state"], "完了")
                forged = {**doc, "activity_state": "完了", "cleanup_status": "成功"}
                self.assertEqual(check(forged, "REG-D011"), "fail")

    def test_closed_cleanup_states_are_kept(self):
        for state in ("成功", "対象なし", "意図的に残した状態"):
            with self.subTest(cleanup=state):
                _, doc = self.project(tw_started("PASS", cleanup_status=state))
                self.assertEqual(doc["activity_state"], "完了")
                self.assertEqual(check(doc, "REG-D011"), "pass")
                self.assertEqual(check(doc, "REG-D010"), "pass")

    def test_attempt_and_raw_capture_are_required_for_testware_route(self):
        for field, value in (
            ("attempt_ref", None),
            ("attempt_ref", ""),
            ("raw_capture_complete", False),
        ):
            with self.subTest(field=field, value=value):
                _, doc = self.project(tw_started("PASS", **{field: value}))
                self.assertEqual(doc["activity_state"], "実行中")
                forged = {**doc, "activity_state": "完了"}
                self.assertEqual(check(forged, "REG-D011"), "fail")
        # projectionを偽って確認済みに見せかけてもsourceと照合して拒否する。
        _, doc = self.project(tw_started("PASS", raw_capture_complete=False))
        forged = copy.deepcopy(doc)
        forged["route_results"][0]["raw_capture_complete"] = True
        forged["activity_state"] = "完了"
        self.assertEqual(check(forged, "REG-D010"), "fail")
        self.assertEqual(check(forged, "REG-D011"), "fail")

    def test_manual_and_e2e_routes_keep_legacy_cleanup_default(self):
        run = {"required_routes": [tc_route("TC-1", "M-1", "manual")]}
        self.assertEqual(
            regression.project_activity(run, {"M-1": started("PASS")})[
                "activity_state"
            ],
            "完了",
        )
        legacy_doc = activity_doc(run, {"M-1": started("PASS")})
        self.assertEqual(check(legacy_doc, "REG-D011"), "pass")


class CountRecomputationTests(unittest.TestCase):
    def setUp(self):
        self.run = {
            **V2,
            "required_routes": [
                tc_route("TC-1", "M-1", "manual"),
                tc_route("TC-2", "X-2"),
                tc_route("TC-3", "X-3"),
                tc_route("TC-4", "X-4"),
            ],
            "auxiliary_routes": [aux("A", "E-A"), aux("OPT", "E-O", required=False)],
        }
        self.source = {
            "M-1": started("PASS"),
            "X-2": tw_started("FAIL"),
            "X-3": {**NOT_STARTED, "blocked": True},
            "X-4": NOT_STARTED,
            "E-A": aux_started("PASS"),
            "E-O": aux_started("FAIL"),
        }
        self.doc = activity_doc(self.run, self.source)

    def test_all_published_counts_are_recomputed(self):
        counts = self.doc["counts"]
        self.assertEqual(counts["tc_member_count"], 4)
        self.assertEqual(counts["executed_tc_count"], 2)
        self.assertEqual(counts["unexecuted_tc_count"], 1)
        self.assertEqual(counts["blocked_tc_count"], 1)
        self.assertEqual(counts["source_result_counts"], {"PASS": 1, "FAIL": 1})
        self.assertEqual(
            counts["auxiliary_source_result_counts"], {"PASS": 1, "FAIL": 1}
        )
        self.assertEqual(check(self.doc, "REG-D015"), "pass")
        for field in counts:
            with self.subTest(field=field):
                forged = copy.deepcopy(self.doc)
                value = forged["counts"][field]
                forged["counts"][field] = (
                    {"PASS": 99} if isinstance(value, dict) else value + 1
                )
                self.assertEqual(check(forged, "REG-D015"), "fail")

    def test_auxiliary_result_is_not_added_to_tc_counts_or_results(self):
        forged = copy.deepcopy(self.doc)
        forged["counts"]["source_result_counts"] = {"PASS": 2, "FAIL": 1}
        forged["counts"]["executed_tc_count"] = 3
        self.assertEqual(check(forged, "REG-D015"), "fail")
        moved = copy.deepcopy(self.doc)
        moved["counts"]["auxiliary_source_result_counts"] = {}
        self.assertEqual(check(moved, "REG-D015"), "fail")


class InvalidInputTests(unittest.TestCase):
    """識別子・route配列・sourceの型が不正でも、例外にせず制御された失敗として扱う。"""

    BAD_REFS = ([], {"a": 1}, 7, "", "  ")

    def test_required_route_validation_does_not_raise(self):
        self.assertFalse(regression.validate_required_routes({})["valid"])
        self.assertFalse(regression.validate_required_routes([None, 1, "x"])["valid"])
        for bad in self.BAD_REFS:
            with self.subTest(execution_ref=bad):
                route = {
                    "tc_ref": "TC-1",
                    "route_type": "manual",
                    "route_ref": "m",
                    "execution_ref": bad,
                }
                result = regression.validate_required_routes([route])
                if bad == "" or bad == "  " or not isinstance(bad, str):
                    self.assertFalse(result["valid"])
                    self.assertNotIn("execution_ref", result["routes"][0])
            with self.subTest(route_type=bad):
                result = regression.validate_required_routes(
                    [{"tc_ref": "TC-1", "route_type": bad, "route_ref": "m"}]
                )
                self.assertFalse(result["valid"])

    def test_auxiliary_validation_does_not_raise(self):
        self.assertFalse(regression.validate_auxiliary_routes({})["valid"])
        self.assertFalse(regression.validate_auxiliary_routes([5, None])["valid"])
        for bad in self.BAD_REFS:
            with self.subTest(value=bad):
                for entry in (
                    aux(bad, "E"),
                    aux("A", "E", executor_owner=bad),
                    aux("A", "E", selection_basis=bad),
                    aux("A", "E", execution_ref=bad),
                ):
                    result = regression.validate_auxiliary_routes(
                        [entry], tc_testware_refs=[bad, "T"]
                    )
                    if (
                        entry.get("execution_ref") != "E"
                        or entry["testware_ref"] != "A"
                    ):
                        self.assertFalse(result["valid"], entry)

    def test_selection_and_resolution_do_not_raise(self):
        selected = regression.select_auxiliary_testware(
            requested_refs=[["A"]],
            user_explicit_refs=[{"a": 1}],
            policy_refs=[],
            available_refs=["A"],
        )
        self.assertEqual(selected["status"], "unresolved")
        self.assertTrue(selected["invalid_refs"])
        for run in (
            {**V2, "auxiliary_routes": [{"testware_ref": ["A"]}, 5]},
            {**V2, "auxiliary_testware_refs": [["A"], None]},
            {**V2, "auxiliary_routes": {}, "auxiliary_testware_refs": 3},
        ):
            with self.subTest(run=run):
                resolved = regression.resolve_auxiliary_obligations(
                    run, user_explicit_refs=["A"], policy_refs=[]
                )
                self.assertIn(resolved["status"], {"ready", "blocked"})

    def test_project_activity_reports_invalid_input_as_unresolved(self):
        for bad in self.BAD_REFS[:4]:
            with self.subTest(execution_ref=bad):
                run = {
                    **V2,
                    "required_routes": [tc_route("TC-1", bad, "manual")],
                    "auxiliary_routes": [aux("A", bad)],
                }
                doc = regression.project_activity(run, {"E": started("PASS")})
                self.assertNotEqual(doc["activity_state"], "完了")
                self.assertTrue(
                    any(
                        u.startswith("invalid_execution_ref") for u in doc["unresolved"]
                    )
                )
        doc = regression.project_activity(
            {**V2, "required_routes": [None, "x", {"tc_ref": "TC-1"}]}, []
        )
        self.assertNotEqual(doc["activity_state"], "完了")
        self.assertIn("source_executions_not_object", doc["unresolved"])
        self.assertIn("invalid_required_route:0", doc["unresolved"])
        doc = regression.project_activity(
            {**V2, "required_routes": {}, "auxiliary_routes": 3}, {}
        )
        self.assertIn("required_routes_not_list", doc["unresolved"])
        self.assertIn("auxiliary_routes_not_list", doc["unresolved"])
        self.assertIn(
            "run_not_object", regression.project_activity([], {})["unresolved"]
        )
        dup = regression.project_activity(
            {
                **V2,
                "required_routes": [tc_route("TC-1", "M", "manual")] * 2,
                "auxiliary_routes": [aux("A", "E1"), aux("A", "E2")],
            },
            {},
        )
        self.assertIn("duplicate_required_route:TC-1|manual:TC-1", dup["unresolved"])
        self.assertIn("duplicate_auxiliary_route:A", dup["unresolved"])

    def test_validator_does_not_raise_on_unhashable_identifiers(self):
        run = {
            **V2,
            "required_routes": [tc_route("TC-1", "X-1")],
            "auxiliary_routes": [aux("A", "E-A")],
        }
        doc = activity_doc(run, {"X-1": tw_started("PASS"), "E-A": aux_started("PASS")})
        for mutate in (
            lambda d: d["route_results"][0].update(execution_ref=["X-1"]),
            lambda d: d["route_results"][0].update(route_type={"a": 1}),
            lambda d: d["auxiliary_route_results"][0].update(execution_ref={"a": 1}),
            lambda d: d["auxiliary_route_results"][0].update(cleanup_status=["x"]),
            lambda d: d["source_executions"]["E-A"].update(cleanup_status=["x"]),
            lambda d: d["source_executions"].update({"E-A": [1, 2]}),
            lambda d: d.update(cleanup_status={"a": 1}),
            lambda d: d.update(counts=[1]),
        ):
            forged = copy.deepcopy(doc)
            mutate(forged)
            forged["activity_state"] = "完了"
            with self.subTest(mutation=mutate.__code__.co_consts):
                statuses = [
                    check_with_run(forged, assertion, run)
                    for assertion in ("REG-D010", "REG-D011", "REG-D015", "REG-D018")
                ]
                # 例外にならず、いずれかの検証が改ざんを失敗として検出する。
                self.assertIn("fail", statuses)


class RunBranchRobustnessTests(unittest.TestCase):
    def test_run_with_invalid_baseline_or_ref_lists_fails_without_raising(self):
        base = {
            "artifact_type": "run",
            "run_scope": "selected",
            "suite_complete": False,
            "required_routes": [],
            "auxiliary_testware_count": 0,
            "auxiliary_testware_refs": [],
            **V2,
        }
        for name, doc in (
            (
                "member_tc_refs_null",
                {
                    **base,
                    "baseline": {"member_tc_refs": None},
                    "selected_tc_refs": ["T"],
                },
            ),
            (
                "selected_not_list",
                {**base, "baseline": {"member_tc_refs": ["T"]}, "selected_tc_refs": 5},
            ),
            (
                "unhashable_selected",
                {
                    **base,
                    "baseline": {"member_tc_refs": ["T"]},
                    "selected_tc_refs": [["T"]],
                },
            ),
            (
                "baseline_not_object",
                {**base, "baseline": [], "selected_tc_refs": ["T"]},
            ),
        ):
            with self.subTest(case=name):
                self.assertEqual(check(doc, "REG-D007"), "fail")
        ok = {**base, "baseline": {"member_tc_refs": ["T"]}, "selected_tc_refs": ["T"]}
        self.assertEqual(check(ok, "REG-D007"), "pass")


def mk_run(routes, auxes=(), **extra):
    """検証用のv2 Run。補助routeのrefsと件数をrouteから揃える。"""
    return {
        **V2,
        "artifact_type": "run",
        "required_routes": list(routes),
        "auxiliary_routes": list(auxes),
        "auxiliary_testware_refs": [a["testware_ref"] for a in auxes],
        "auxiliary_testware_count": len(list(auxes)),
        **extra,
    }


def verify_all(run, doc):
    """D011（Run無し）・D018（Run有り）・runtimeの照合結果をまとめて返す。"""
    return {
        "d011": check_with_run(doc, "REG-D011"),
        "d018": check_with_run(doc, "REG-D018", run),
        "runtime": regression.verify_activity_against_run(run, doc)["valid"],
    }


class InvalidRunTests(unittest.TestCase):
    """不正なRunは、再投影が一致してもActivityを完了にも検証済みにもしない。"""

    def routes(self, **changes):
        return [tc_route("TC-1", "M-1", "manual"), tc_route("TC-1", "X-1", **changes)]

    def source(self):
        return {"M-1": started("PASS"), "X-1": tw_started("PASS")}

    def test_valid_mixed_run_is_the_baseline(self):
        run = mk_run(self.routes(), [aux("A", "E-A")])
        doc = activity_doc(run, {**self.source(), "E-A": aux_started("PASS")})
        self.assertEqual(doc["activity_state"], "完了")
        self.assertEqual(
            verify_all(run, doc), {"d011": "pass", "d018": "pass", "runtime": True}
        )

    def test_unknown_route_type_never_completes(self):
        for kind in ("unknown", "", None, ["manual"], {"a": 1}, 3):
            with self.subTest(route_type=kind):
                run = mk_run(
                    [{**tc_route("TC-1", "M-1", "manual"), "route_type": kind}]
                )
                doc = activity_doc(run, {"M-1": started("PASS")})
                self.assertNotEqual(doc["activity_state"], "完了")
                self.assertTrue(
                    any(
                        u.startswith("invalid_required_route_type")
                        for u in doc["unresolved"]
                    )
                )
                # 状態の主張を偽って完了にしても、sourceから確認できず拒否する。
                forged = {**doc, "activity_state": "完了", "unresolved": []}
                self.assertEqual(check_with_run(forged, "REG-D018", run), "fail")
                self.assertFalse(
                    regression.verify_activity_against_run(run, forged)["valid"]
                )
                # 真のActivityでも、不正なRunは正当な義務として受け入れない。
                self.assertEqual(check_with_run(doc, "REG-D018", run), "fail")
                self.assertFalse(
                    regression.verify_activity_against_run(run, doc)["valid"]
                )
                self.assertEqual(check_with_run(run, "REG-D008"), "fail")

    def test_missing_identifiers_and_invalid_testware_fields_are_rejected(self):
        broken = {
            "missing_route_ref": {"route_ref": None},
            "missing_tc_ref": {"tc_ref": ""},
            "no_testware_ref": {"testware_ref": None},
            "wrong_owner": {"executor_owner": "someone-else"},
            "no_revision": {"implementation_revision": None},
            "no_selection": {"selection_basis": ""},
            "bad_execution_ref": {"execution_ref": ["X-1"]},
        }
        for name, change in broken.items():
            with self.subTest(case=name):
                run = mk_run(self.routes(**change))
                self.assertFalse(
                    regression.validate_required_routes(run["required_routes"])["valid"]
                )
                doc = activity_doc(run, self.source())
                self.assertNotEqual(doc["activity_state"], "完了")
                forged = {**doc, "activity_state": "完了", "unresolved": []}
                self.assertEqual(check_with_run(forged, "REG-D018", run), "fail")
                self.assertFalse(
                    regression.verify_activity_against_run(run, forged)["valid"]
                )
                self.assertEqual(check_with_run(run, "REG-D008"), "fail")

    def test_e2e_route_without_concrete_testware_is_rejected(self):
        route = tc_route("TC-1", "E-1", "e2e")
        run = mk_run([route])
        doc = activity_doc(run, {"E-1": started("PASS")})
        self.assertNotEqual(doc["activity_state"], "完了")
        self.assertEqual(check_with_run(doc, "REG-D018", run), "fail")
        valid = mk_run([{**route, "e2e_testware_ref": "e2e/login.spec.ts"}])
        good = activity_doc(valid, {"E-1": started("PASS")})
        self.assertEqual(good["activity_state"], "完了")
        self.assertEqual(check_with_run(good, "REG-D018", valid), "pass")

    def test_unsupported_run_version_is_rejected_but_legacy_is_readable(self):
        for version in ("3", 2, None, ""):
            with self.subTest(version=version):
                run = {
                    **mk_run([tc_route("TC-1", "M-1", "manual")]),
                    "route_contract_version": version,
                }
                doc = activity_doc(run, {"M-1": started("PASS")})
                self.assertNotEqual(doc["activity_state"], "完了")
                self.assertFalse(
                    regression.verify_activity_against_run(run, doc)["valid"]
                )
        legacy = {"required_routes": [tc_route("TC-1", "M-1", "manual")]}
        self.assertEqual(
            regression.project_activity(legacy, {"M-1": started("PASS")})[
                "activity_state"
            ],
            "完了",
        )

    def test_invalid_auxiliary_entries_in_run_are_rejected(self):
        manual = [tc_route("TC-1", "M-1", "manual")]
        bad_aux = {
            "wrong_owner": {**aux("A", "E-A"), "executor_owner": "x"},
            "no_revision": {**aux("A", "E-A"), "implementation_revision": None},
            "bad_basis": {**aux("A", "E-A"), "selection_basis": "guess"},
            "required_mismatch": {**aux("A", "E-A"), "completion_required": False},
        }
        for name, entry in bad_aux.items():
            with self.subTest(case=name):
                run = mk_run(manual, [entry])
                doc = activity_doc(
                    run, {"M-1": started("PASS"), "E-A": aux_started("PASS")}
                )
                self.assertNotEqual(doc["activity_state"], "完了", name)
                self.assertEqual(check_with_run(doc, "REG-D018", run), "fail")
                self.assertFalse(
                    regression.verify_activity_against_run(run, doc)["valid"]
                )


class TestwareSelectionIdentityTests(unittest.TestCase):
    """TC付きtestwareの選定情報（testware_ref・owner・選定根拠）もRunと照合する。"""

    def setUp(self):
        self.run = mk_run(
            [tc_route("TC-1", "M-1", "manual"), tc_route("TC-1", "X-1")],
            [aux("A", "E-A")],
        )
        self.source = {
            "M-1": started("PASS"),
            "X-1": tw_started("PASS"),
            "E-A": aux_started("PASS"),
        }
        self.doc = activity_doc(self.run, self.source)

    def tw_item(self, doc):
        return next(r for r in doc["route_results"] if r["route_type"] == "testware")

    def test_selection_is_projected_only_for_testware_routes(self):
        item = self.tw_item(self.doc)
        self.assertEqual(item["testware_ref"], "vitest:TC-1")
        self.assertEqual(item["executor_owner"], "testware-execution")
        self.assertEqual(item["selection_basis"], "tests/unit/password-hasher.test.ts")
        manual = next(
            r for r in self.doc["route_results"] if r["route_type"] == "manual"
        )
        for field in ("testware_ref", "executor_owner", "selection_basis"):
            self.assertNotIn(field, manual)
        self.assertEqual(check_with_run(self.doc, "REG-D018", self.run), "pass")

    def test_changed_selection_in_activity_is_detected(self):
        for field, value in (
            ("testware_ref", "vitest:OTHER"),
            ("executor_owner", "e2e-test-execution"),
            ("selection_basis", "tests/unit/other.test.ts"),
        ):
            with self.subTest(field=field):
                forged = copy.deepcopy(self.doc)
                self.tw_item(forged)[field] = value
                # route_ref・execution_ref・revisionは維持したまま、選定情報だけを変える。
                self.assertEqual(check_with_run(forged, "REG-D018", self.run), "fail")
                self.assertFalse(
                    regression.verify_activity_against_run(self.run, forged)["valid"]
                )

    def test_changed_selection_in_run_is_detected_against_stored_activity(self):
        for field, value in (
            ("testware_ref", "vitest:OTHER"),
            ("selection_basis", "tests/unit/other.test.ts"),
        ):
            with self.subTest(field=field):
                changed = copy.deepcopy(self.run)
                next(
                    r
                    for r in changed["required_routes"]
                    if r["route_type"] == "testware"
                )[field] = value
                self.assertEqual(check_with_run(self.doc, "REG-D018", changed), "fail")
                self.assertFalse(
                    regression.verify_activity_against_run(changed, self.doc)["valid"]
                )

    def test_dropped_selection_fields_are_rejected_without_a_run_too(self):
        for field in ("testware_ref", "executor_owner", "selection_basis"):
            with self.subTest(field=field):
                forged = copy.deepcopy(self.doc)
                del self.tw_item(forged)[field]
                self.assertEqual(check_with_run(forged, "REG-D010"), "fail")
                self.assertEqual(check_with_run(forged, "REG-D018", self.run), "fail")

    def test_old_v2_activity_without_selection_fields_is_not_silently_accepted(self):
        old = copy.deepcopy(self.doc)
        for field in ("testware_ref", "executor_owner", "selection_basis"):
            self.tw_item(old).pop(field)
        self.assertFalse(regression.verify_activity_against_run(self.run, old)["valid"])


class ActivityStateVerificationTests(unittest.TestCase):
    """Activity状態はsourceから独立に再計算し、runtimeとvalidatorの判定を一致させる。"""

    def scenarios(self):
        manual = tc_route("TC-1", "M-1", "manual")
        tw = tc_route("TC-1", "X-1")
        other = tc_route("TC-2", "M-2", "manual")
        a = aux("A", "E-A")
        opt = aux("OPT", "E-O", required=False)
        done = {"M-1": started("PASS"), "X-1": tw_started("PASS")}
        return {
            "complete": (
                mk_run([manual, tw], [a, opt]),
                {**done, "E-A": aux_started("PASS"), "E-O": NOT_STARTED},
                {},
            ),
            "running_unfinalized": (
                mk_run([manual, tw]),
                {"M-1": started("PASS", finalized=False), "X-1": tw_started("PASS")},
                {},
            ),
            "running_raw_incomplete": (
                mk_run([manual, tw]),
                {
                    "M-1": started("PASS"),
                    "X-1": tw_started("PASS", raw_capture_complete=False),
                },
                {},
            ),
            "running_aux_unfinalized": (
                mk_run([manual], [a]),
                {"M-1": started("PASS"), "E-A": aux_started("PASS", finalized=False)},
                {},
            ),
            "partial": (
                mk_run([manual, other]),
                {"M-1": started("PASS"), "M-2": NOT_STARTED},
                {},
            ),
            "partial_one_route_of_tc": (
                mk_run([manual, tw]),
                {"M-1": started("PASS"), "X-1": NOT_STARTED},
                {},
            ),
            "unstarted_routes": (
                mk_run([manual, other]),
                {"M-1": NOT_STARTED, "M-2": NOT_STARTED},
                {},
            ),
            "blocked_route": (
                mk_run([manual]),
                {"M-1": {**NOT_STARTED, "blocked": True}},
                {},
            ),
            "aux_only_unstarted": (
                mk_run([], [a]),
                {"E-A": NOT_STARTED},
                {},
            ),
            "aux_only_blocked": (
                mk_run([], [a]),
                {"E-A": {**NOT_STARTED, "blocked": True}},
                {},
            ),
            "revision_mismatch": (
                mk_run([manual, tw]),
                {"M-1": started("PASS"), "X-1": tw_started("PASS", revision="rev-B")},
                {},
            ),
            "cleanup_failed": (
                mk_run([manual, tw]),
                {
                    "M-1": started("PASS"),
                    "X-1": tw_started("PASS", cleanup_status="失敗"),
                },
                {},
            ),
            "activity_cleanup_failed": (
                mk_run([manual]),
                {"M-1": started("PASS")},
                {"cleanup_status": "失敗"},
            ),
            "shared_execution": (
                mk_run([manual], [aux("A", "M-1")]),
                {"M-1": started("PASS", implementation_revision=REV)},
                {},
            ),
        }

    def test_runtime_and_validator_agree_on_every_state(self):
        states = set()
        for name, (run, source, kwargs) in self.scenarios().items():
            with self.subTest(case=name):
                doc = activity_doc(run, source, **kwargs)
                states.add(doc["activity_state"])
                # validatorは申告されたunresolved・executed等を使わず、同じ状態を導く。
                derived = validator._derive_activity_state(
                    run["required_routes"],
                    run["auxiliary_routes"],
                    source,
                    doc["cleanup_status"],
                    unresolved=False,
                )
                self.assertEqual(derived, doc["activity_state"])
                self.assertEqual(
                    verify_all(run, doc),
                    {"d011": "pass", "d018": "pass", "runtime": True},
                )
        # 5種類すべての状態を実際に通している。
        self.assertEqual(
            states,
            {"完了", "実行中", "未開始", "ブロック中", "部分完了（ブロック中あり）"},
        )

    def test_any_changed_state_is_rejected_by_both(self):
        all_states = {
            "完了",
            "実行中",
            "未開始",
            "ブロック中",
            "部分完了（ブロック中あり）",
        }
        for name, (run, source, kwargs) in self.scenarios().items():
            doc = activity_doc(run, source, **kwargs)
            for forged_state in all_states - {doc["activity_state"]}:
                with self.subTest(case=name, forged=forged_state):
                    forged = {**doc, "activity_state": forged_state}
                    self.assertEqual(check_with_run(forged, "REG-D011"), "fail")
                    self.assertEqual(check_with_run(forged, "REG-D018", run), "fail")
                    self.assertFalse(
                        regression.verify_activity_against_run(run, forged)["valid"]
                    )

    def test_completed_work_cannot_be_downgraded_to_running(self):
        run, source, kwargs = self.scenarios()["complete"]
        doc = activity_doc(run, source, **kwargs)
        self.assertEqual(doc["activity_state"], "完了")
        forged = {**doc, "activity_state": "実行中"}
        self.assertEqual(check_with_run(forged, "REG-D011"), "fail")
        self.assertEqual(check_with_run(forged, "REG-D018", run), "fail")

    def test_forged_unstarted_blocked_and_unfinalized_routes_are_detected(self):
        run, source, _ = self.scenarios()["blocked_route"]
        doc = activity_doc(run, source)
        unblocked = copy.deepcopy(doc)
        unblocked["route_results"][0]["blocked"] = False
        unblocked["tc_execution_state"] = {"TC-1": "unexecuted"}
        unblocked["counts"].update(blocked_tc_count=0, unexecuted_tc_count=1)
        self.assertEqual(check_with_run(unblocked, "REG-D010"), "fail")
        self.assertFalse(
            regression.verify_activity_against_run(run, unblocked)["valid"]
        )
        # 未開始のsourceを開始済みに偽装する。
        started_forged = copy.deepcopy(doc)
        started_forged["route_results"][0]["executed"] = True
        started_forged["tc_execution_state"] = {"TC-1": "executed"}
        self.assertEqual(check_with_run(started_forged, "REG-D010"), "fail")
        # 結果未確定のsourceを確定済みに偽装して完了にする。
        run2, source2, _ = self.scenarios()["running_unfinalized"]
        doc2 = activity_doc(run2, source2)
        forged = copy.deepcopy(doc2)
        forged["route_results"][0]["result_finalized"] = True
        forged["activity_state"] = "完了"
        self.assertEqual(check_with_run(forged, "REG-D010"), "fail")
        self.assertEqual(check_with_run(forged, "REG-D011"), "fail")
        self.assertFalse(regression.verify_activity_against_run(run2, forged)["valid"])

    def test_executed_count_that_contradicts_state_is_rejected(self):
        run, source, kwargs = self.scenarios()["partial"]
        doc = activity_doc(run, source, **kwargs)
        forged = copy.deepcopy(doc)
        forged["counts"]["executed_tc_count"] = 2
        forged["counts"]["unexecuted_tc_count"] = 0
        forged["activity_state"] = "完了"
        self.assertEqual(check_with_run(forged, "REG-D015"), "fail")
        self.assertEqual(check_with_run(forged, "REG-D011"), "fail")
        self.assertEqual(check_with_run(forged, "REG-D018", run), "fail")

    def test_removing_derived_unresolved_cannot_restore_a_better_state(self):
        run, source, kwargs = self.scenarios()["revision_mismatch"]
        doc = activity_doc(run, source, **kwargs)
        self.assertTrue(doc["unresolved"])
        forged = {**doc, "unresolved": [], "activity_state": "完了"}
        self.assertEqual(check_with_run(forged, "REG-D011"), "fail")
        self.assertEqual(check_with_run(forged, "REG-D018", run), "fail")
        self.assertFalse(regression.verify_activity_against_run(run, forged)["valid"])

    def test_legacy_activity_state_is_not_recomputed(self):
        legacy = {
            "artifact_type": "activity",
            "activity_ref": "A",
            "snapshot_ref": "S",
            "scope_identity": "scope",
            "activity_state": "実行中",
            "cleanup_status": "対象なし",
            "route_results": [],
        }
        self.assertEqual(check_with_run(legacy, "REG-D011"), "pass")
        self.assertEqual(check_with_run(legacy, "REG-D018"), "pass")


class RunAuxiliaryRefInputTests(unittest.TestCase):
    """REG-D018は不正な補助refを集合へ入れず、例外ではなく失敗として扱う。"""

    def setUp(self):
        self.run = mk_run([tc_route("TC-1", "M-1", "manual")], [aux("A", "E-A")])
        self.doc = activity_doc(
            self.run, {"M-1": started("PASS"), "E-A": aux_started("PASS")}
        )

    def test_unhashable_or_invalid_testware_ref_in_run_fails_without_raising(self):
        for bad in (["A"], {"a": 1}, 5, None, "", True):
            with self.subTest(testware_ref=bad):
                run = {**self.run, "auxiliary_routes": [aux(bad, "E-A")]}
                self.assertEqual(check_with_run(self.doc, "REG-D018", run), "fail")
                self.assertFalse(
                    regression.verify_activity_against_run(run, self.doc)["valid"]
                )
                self.assertEqual(
                    check_with_run(
                        {**self.doc, "auxiliary_route_results": [aux(bad, "E-A")]},
                        "REG-D018",
                        self.run,
                    ),
                    "fail",
                )

    def test_invalid_auxiliary_refs_list_is_not_silently_dropped(self):
        for bad in ([["A"]], [{"a": 1}], [None, "A"], ["A", "A"], "A", 3, {"A": 1}):
            with self.subTest(refs=bad):
                run = {**self.run, "auxiliary_testware_refs": bad}
                self.assertEqual(check_with_run(self.doc, "REG-D018", run), "fail")
                self.assertFalse(
                    regression.verify_activity_against_run(run, self.doc)["valid"]
                )

    def test_invalid_run_shapes_fail_without_raising(self):
        for key, bad in (
            ("auxiliary_routes", "A"),
            ("auxiliary_routes", [["A"]]),
            ("required_routes", {"a": 1}),
            ("required_routes", [["x"]]),
            ("required_routes", None),
        ):
            with self.subTest(key=key, value=bad):
                run = {**self.run, key: bad}
                self.assertEqual(check_with_run(self.doc, "REG-D018", run), "fail")
                self.assertFalse(
                    regression.verify_activity_against_run(run, self.doc)["valid"]
                )

    def test_identity_comparison_tolerates_incomparable_values(self):
        entry = {"testware_ref": "A", "execution_ref": {1: "a", "b": 2}}
        key = validator._identity_key(entry, ("testware_ref", "execution_ref"))
        self.assertIsInstance(key, str)
        counts = validator._identity_counts([entry, entry], ("testware_ref",))
        self.assertEqual(sum(counts.values()), 2)

    def test_valid_run_with_legacy_refs_is_still_read(self):
        legacy = {
            **self.run,
            "auxiliary_routes": [],
            "auxiliary_testware_refs": ["OLD"],
            "auxiliary_testware_count": 1,
        }
        del legacy["route_contract_version"]
        self.assertEqual(check_with_run(self.doc, "REG-D018", legacy), "fail")
        legacy_doc = activity_doc(legacy, {"M-1": started("PASS")})
        self.assertEqual(legacy_doc["counts"]["auxiliary_obligation_unknown_count"], 1)
        self.assertNotEqual(legacy_doc["activity_state"], "完了")


class AuxiliaryOwnerAndBasisInputTests(unittest.TestCase):
    """補助routeのexecutor_owner・selection_basisが不正型でも例外にせず失敗にする。"""

    def setUp(self):
        self.run = mk_run([tc_route("TC-1", "M-1", "manual")], [aux("A", "E-A")])
        self.doc = activity_doc(
            self.run, {"M-1": started("PASS"), "E-A": aux_started("PASS")}
        )

    def broken(self, field, value):
        run = copy.deepcopy(self.run)
        run["auxiliary_routes"][0][field] = value
        return run

    def test_unhashable_owner_or_basis_fails_in_every_path_without_raising(self):
        for field, value in (
            ("executor_owner", []),
            ("executor_owner", {"owner": "testware-execution"}),
            ("selection_basis", ["policy"]),
            ("selection_basis", {"basis": "user_explicit"}),
            ("executor_owner", 5),
            ("selection_basis", None),
        ):
            with self.subTest(field=field, value=value):
                run = self.broken(field, value)
                self.assertEqual(check_with_run(run, "REG-D009"), "fail")
                self.assertEqual(check_with_run(self.doc, "REG-D018", run), "fail")
                self.assertFalse(
                    regression.verify_activity_against_run(run, self.doc)["valid"]
                )
                # 不正値を有効値へ正規化して完了へ進めない。
                projected = activity_doc(
                    run, {"M-1": started("PASS"), "E-A": aux_started("PASS")}
                )
                self.assertNotEqual(projected["activity_state"], "完了")

    def test_invalid_values_in_activity_are_also_a_failure(self):
        forged = copy.deepcopy(self.doc)
        forged["auxiliary_route_results"][0]["executor_owner"] = []
        self.assertEqual(check_with_run(forged, "REG-D018", self.run), "fail")

    def test_valid_owner_and_basis_keep_the_existing_result(self):
        self.assertEqual(check_with_run(self.run, "REG-D009"), "pass")
        self.assertEqual(check_with_run(self.doc, "REG-D018", self.run), "pass")
        for owner in ("e2e-test-execution", "testware-execution"):
            for basis, required in (
                ("user_explicit", True),
                ("policy", True),
                ("reference_only", False),
            ):
                with self.subTest(owner=owner, basis=basis):
                    run = copy.deepcopy(self.run)
                    entry = run["auxiliary_routes"][0]
                    entry.update(
                        executor_owner=owner,
                        selection_basis=basis,
                        completion_required=required,
                    )
                    self.assertEqual(check_with_run(run, "REG-D009"), "pass")
        # 実施義務と選定根拠の整合は維持する。
        mismatch = self.broken("completion_required", False)
        self.assertEqual(check_with_run(mismatch, "REG-D009"), "fail")

    def test_other_unhashable_discriminators_fail_without_raising(self):
        for doc in (
            {"artifact_type": []},
            {"artifact_type": {"a": 1}},
        ):
            with self.subTest(doc=doc):
                self.assertEqual(check_with_run(doc, "REG-D002"), "fail")
        baseline = {
            "artifact_type": "baseline",
            "memberships": [{"tc_ref": "T", "decision": ["member"]}],
        }
        self.assertEqual(check_with_run(baseline, "REG-D016"), "fail")


class E2ETestwareRefTests(unittest.TestCase):
    """E2E required routeの実行対象（e2e_testware_ref）もRunとActivityで照合する。"""

    REF = "e2e/login.spec.ts"

    def setUp(self):
        self.e2e = tc_route("TC-1", "E-1", "e2e", e2e_testware_ref=self.REF)
        self.run = mk_run(
            [tc_route("TC-1", "M-1", "manual"), self.e2e, tc_route("TC-2", "X-2")]
        )
        self.source = {
            "M-1": started("PASS"),
            "E-1": started("PASS"),
            "X-2": tw_started("PASS"),
        }
        self.doc = activity_doc(self.run, self.source)

    def e2e_item(self, doc):
        return next(r for r in doc["route_results"] if r["route_type"] == "e2e")

    def test_reference_is_projected_only_for_e2e_routes(self):
        self.assertEqual(self.doc["activity_state"], "完了")
        self.assertEqual(self.e2e_item(self.doc)["e2e_testware_ref"], self.REF)
        for item in self.doc["route_results"]:
            if item["route_type"] != "e2e":
                self.assertNotIn("e2e_testware_ref", item)
        self.assertEqual(check_with_run(self.doc, "REG-D018", self.run), "pass")
        self.assertTrue(
            regression.verify_activity_against_run(self.run, self.doc)["valid"]
        )

    def test_changed_reference_in_activity_is_detected(self):
        forged = copy.deepcopy(self.doc)
        self.e2e_item(forged)["e2e_testware_ref"] = "e2e/other.spec.ts"
        # route_ref・execution_ref・結果は同じまま、実行対象だけを変えている。
        self.assertEqual(check_with_run(forged, "REG-D018", self.run), "fail")
        self.assertFalse(
            regression.verify_activity_against_run(self.run, forged)["valid"]
        )

    def test_changed_reference_in_run_is_detected_against_stored_activity(self):
        changed = copy.deepcopy(self.run)
        next(r for r in changed["required_routes"] if r["route_type"] == "e2e")[
            "e2e_testware_ref"
        ] = "e2e/other.spec.ts"
        self.assertEqual(check_with_run(self.doc, "REG-D018", changed), "fail")
        self.assertFalse(
            regression.verify_activity_against_run(changed, self.doc)["valid"]
        )

    def test_removed_reference_is_detected(self):
        forged = copy.deepcopy(self.doc)
        del self.e2e_item(forged)["e2e_testware_ref"]
        self.assertEqual(check_with_run(forged, "REG-D010"), "fail")
        self.assertEqual(check_with_run(forged, "REG-D018", self.run), "fail")
        self.assertFalse(
            regression.verify_activity_against_run(self.run, forged)["valid"]
        )

    def test_invalid_reference_types_are_rejected_by_run_validation(self):
        for name, value in (
            ("list", ["e2e/a.spec.ts"]),
            ("dict", {"ref": self.REF}),
            ("empty", ""),
            ("blank", "   "),
            ("number", 5),
            ("none", None),
            ("missing", ...),
        ):
            with self.subTest(case=name):
                route = {**self.e2e}
                if value is ...:
                    del route["e2e_testware_ref"]
                else:
                    route["e2e_testware_ref"] = value
                run = mk_run([route])
                self.assertFalse(
                    regression.validate_required_routes(run["required_routes"])["valid"]
                )
                self.assertEqual(check_with_run(run, "REG-D008"), "fail")
                projected = activity_doc(run, {"E-1": started("PASS")})
                self.assertNotEqual(projected["activity_state"], "完了")
                self.assertEqual(check_with_run(projected, "REG-D018", run), "fail")
                self.assertFalse(
                    regression.verify_activity_against_run(run, projected)["valid"]
                )

    def test_manual_and_testware_do_not_require_an_e2e_reference(self):
        run = mk_run([tc_route("TC-1", "M-1", "manual"), tc_route("TC-1", "X-1")])
        self.assertTrue(
            regression.validate_required_routes(run["required_routes"])["valid"]
        )
        self.assertEqual(check_with_run(run, "REG-D008"), "pass")

    def test_legacy_activity_without_the_reference_is_still_readable(self):
        legacy_run = {"required_routes": [self.e2e]}
        legacy = {
            "artifact_type": "activity",
            "activity_ref": "A",
            "snapshot_ref": "S",
            "scope_identity": "scope",
            "activity_state": "完了",
            "cleanup_status": "対象なし",
            "source_executions": {"E-1": started("PASS")},
            "route_results": [
                {
                    "tc_ref": "TC-1",
                    "route_ref": "e2e:TC-1",
                    "route_type": "e2e",
                    "execution_ref": "E-1",
                    "executed": True,
                    "result_finalized": True,
                    "source_result_projectable": True,
                    "source_result": "PASS",
                }
            ],
        }
        self.assertEqual(check_with_run(legacy, "REG-D011"), "pass")
        self.assertEqual(check_with_run(legacy, "REG-D018"), "pass")
        self.assertEqual(
            regression.project_activity(legacy_run, {"E-1": started("PASS")})[
                "activity_state"
            ],
            "完了",
        )


class AuxiliaryCountTests(unittest.TestCase):
    """auxiliary_testware_countは型を厳密に確認し、実際の補助route件数と照合する。"""

    def setUp(self):
        self.run = mk_run([tc_route("TC-1", "M-1", "manual")], [aux("A", "E-A")])
        self.source = {"M-1": started("PASS"), "E-A": aux_started("PASS")}
        self.doc = activity_doc(self.run, self.source)

    def with_count(self, count):
        run = copy.deepcopy(self.run)
        if count is ...:
            del run["auxiliary_testware_count"]
        else:
            run["auxiliary_testware_count"] = count
        return run

    def paths(self, run):
        return {
            "d009": check_with_run(run, "REG-D009"),
            "d018": check_with_run(self.doc, "REG-D018", run),
            "runtime": regression.verify_activity_against_run(run, self.doc)["valid"],
        }

    def test_exact_count_passes_every_path(self):
        self.assertEqual(
            self.paths(self.with_count(1)),
            {"d009": "pass", "d018": "pass", "runtime": True},
        )

    def test_mismatched_or_invalid_counts_fail_every_path(self):
        for count in (0, 99, -1, "1", True, 1.0, None, [1], {"n": 1}, ...):
            with self.subTest(count=count):
                self.assertEqual(
                    self.paths(self.with_count(count)),
                    {"d009": "fail", "d018": "fail", "runtime": False},
                )

    def test_invalid_count_never_completes_the_activity(self):
        for count in (0, 99, True, "1", ...):
            with self.subTest(count=count):
                run = self.with_count(count)
                doc = activity_doc(run, self.source)
                self.assertNotEqual(doc["activity_state"], "完了")
                self.assertTrue(
                    any("auxiliary_testware_count" in u for u in doc["unresolved"])
                )

    def test_zero_multiple_and_optional_only_runs(self):
        manual = [tc_route("TC-1", "M-1", "manual")]
        cases = {
            "none": ([], {"M-1": started("PASS")}),
            "multiple": (
                [aux("A", "E-A"), aux("B", "E-B"), aux("OPT", "E-O", required=False)],
                {
                    "M-1": started("PASS"),
                    "E-A": aux_started("PASS"),
                    "E-B": aux_started("PASS"),
                    "E-O": NOT_STARTED,
                },
            ),
            "optional_only": (
                [aux("OPT", "E-O", required=False)],
                {"M-1": started("PASS"), "E-O": NOT_STARTED},
            ),
        }
        for name, (auxes, source) in cases.items():
            with self.subTest(case=name):
                run = mk_run(manual, auxes)
                doc = activity_doc(run, source)
                self.assertEqual(doc["activity_state"], "完了")
                self.assertEqual(
                    verify_all(run, doc),
                    {"d011": "pass", "d018": "pass", "runtime": True},
                )
                self.assertEqual(check_with_run(run, "REG-D009"), "pass")
                wrong = {**run, "auxiliary_testware_count": len(auxes) + 1}
                self.assertEqual(check_with_run(wrong, "REG-D009"), "fail")
                self.assertFalse(
                    regression.verify_activity_against_run(wrong, doc)["valid"]
                )

    def test_count_must_match_routes_even_when_refs_agree_with_the_count(self):
        run = {**self.run, "auxiliary_routes": [aux("A", "E-A"), aux("B", "E-B")]}
        run["auxiliary_testware_refs"] = ["A"]
        run["auxiliary_testware_count"] = 1
        self.assertEqual(self.paths(run)["d018"], "fail")
        self.assertFalse(self.paths(run)["runtime"])

    def test_legacy_run_without_a_count_stays_readable(self):
        legacy = {"required_routes": [tc_route("TC-1", "M-1", "manual")]}
        self.assertEqual(
            regression.project_activity(legacy, {"M-1": started("PASS")})[
                "activity_state"
            ],
            "完了",
        )
        legacy_refs = {
            "required_routes": [tc_route("TC-1", "M-1", "manual")],
            "auxiliary_testware_refs": ["OLD"],
        }
        projected = regression.project_activity(legacy_refs, {"M-1": started("PASS")})
        self.assertNotEqual(projected["activity_state"], "完了")
        self.assertFalse(
            any("auxiliary_testware_count" in u for u in projected["unresolved"])
        )


class AuxiliaryRefsPresenceTests(unittest.TestCase):
    """v2 Runの`auxiliary_testware_refs`は省略でき、省略と空配列は区別する。

    REG-D009・REG-D018・runtimeのRun検証・project_activity()の判定は同じになる。
    """

    SOURCE = {"M-1": started("PASS"), "E-A": aux_started("PASS")}

    def setUp(self):
        self.run = mk_run([tc_route("TC-1", "M-1", "manual")], [aux("A", "E-A")])
        self.doc = activity_doc(self.run, self.SOURCE)
        self.assertEqual(self.doc["activity_state"], "完了")

    def variant(self, **changes):
        run = copy.deepcopy(self.run)
        for key, value in changes.items():
            if value is ...:
                run.pop(key, None)
            else:
                run[key] = value
        return run

    def paths(self, run, doc=None):
        doc = doc or self.doc
        return {
            "d009": check_with_run(run, "REG-D009"),
            "d018": check_with_run(doc, "REG-D018", run),
            "verify": regression.verify_activity_against_run(run, doc)["valid"],
            "complete": regression.project_activity(run, self.SOURCE)["activity_state"]
            == "完了",
        }

    OK = {"d009": "pass", "d018": "pass", "verify": True, "complete": True}
    NG = {"d009": "fail", "d018": "fail", "verify": False, "complete": False}

    def test_omitted_refs_are_accepted_by_every_path(self):
        self.assertEqual(self.paths(self.variant(auxiliary_testware_refs=...)), self.OK)
        self.assertEqual(
            self.paths(self.variant(auxiliary_testware_refs=["A"])), self.OK
        )

    def test_declared_refs_must_match_the_routes_exactly(self):
        for name, refs in (
            ("empty", []),
            ("other", ["B"]),
            ("duplicate", ["A", "A"]),
            ("extra", ["A", "B"]),
            ("null", None),
            ("string", "A"),
            ("dict", {"A": 1}),
            ("nested", [["A"]]),
        ):
            with self.subTest(refs=name):
                self.assertEqual(
                    self.paths(self.variant(auxiliary_testware_refs=refs)), self.NG
                )

    def test_omitted_refs_still_require_a_strict_count(self):
        for count in (0, 2, -1, True, "1", 1.0, None):
            with self.subTest(count=count):
                run = self.variant(
                    auxiliary_testware_refs=..., auxiliary_testware_count=count
                )
                self.assertEqual(self.paths(run), self.NG)
        self.assertEqual(
            self.paths(
                self.variant(auxiliary_testware_refs=..., auxiliary_testware_count=1)
            ),
            self.OK,
        )

    def test_omitted_refs_do_not_skip_route_validation(self):
        bad = copy.deepcopy(self.run)
        del bad["auxiliary_testware_refs"]
        bad["auxiliary_routes"][0]["executor_owner"] = ["x"]
        self.assertEqual(self.paths(bad), self.NG)

    def test_zero_auxiliary_routes_with_zero_count(self):
        run = mk_run([tc_route("TC-1", "M-1", "manual")])
        doc = activity_doc(run, {"M-1": started("PASS")})
        for refs in (..., []):
            with self.subTest(refs=refs):
                candidate = {
                    k: v for k, v in run.items() if k != "auxiliary_testware_refs"
                }
                if refs is not ...:
                    candidate["auxiliary_testware_refs"] = refs
                self.assertEqual(self.paths(candidate, doc)["d009"], "pass")
                self.assertEqual(check_with_run(doc, "REG-D018", candidate), "pass")
                self.assertTrue(
                    regression.verify_activity_against_run(candidate, doc)["valid"]
                )

    def test_legacy_run_keeps_the_previous_refs_rule(self):
        # 旧形式（版なし）はrefs一覧だけが補助の根拠で、省略は空一覧として扱う。
        legacy = {
            "artifact_type": "run",
            "run_scope": "selected",
            "suite_complete": False,
            "baseline": {"member_tc_refs": ["TC-1"]},
            "selected_tc_refs": ["TC-1"],
            "required_routes": [],
            "auxiliary_testware_count": 1,
        }
        self.assertEqual(check_with_run(legacy, "REG-D009"), "fail")
        legacy["auxiliary_testware_refs"] = ["OLD"]
        self.assertEqual(check_with_run(legacy, "REG-D009"), "pass")


class RunArtifactTypeVerificationTests(unittest.TestCase):
    """保存済みRunの代わりに、Run以外のartifactを受け入れない。"""

    def setUp(self):
        self.run = mk_run([tc_route("TC-1", "M-1", "manual")], [aux("A", "E-A")])
        self.source = {"M-1": started("PASS"), "E-A": aux_started("PASS")}
        self.doc = activity_doc(self.run, self.source)

    def test_only_run_artifact_type_is_accepted(self):
        for value in ("activity", "baseline", "", None, [], {}, 5, True, "Run", ...):
            with self.subTest(artifact_type=value):
                run = copy.deepcopy(self.run)
                if value is ...:
                    del run["artifact_type"]
                else:
                    run["artifact_type"] = value
                result = regression.verify_activity_against_run(run, self.doc)
                self.assertFalse(result["valid"])
                self.assertEqual(result["mismatches"], ["run_contract_invalid"])
                self.assertIn("run_artifact_required", result["run_issues"])
                self.assertEqual(check_with_run(self.doc, "REG-D018", run), "fail")
        valid = regression.verify_activity_against_run(self.run, self.doc)
        self.assertEqual(valid, {"valid": True, "mismatches": []})
        self.assertEqual(check_with_run(self.doc, "REG-D018", self.run), "pass")

    def test_non_object_runs_fail_without_raising(self):
        for bad in (None, [], "run", 5, [self.run]):
            with self.subTest(run=bad):
                self.assertFalse(
                    regression.verify_activity_against_run(bad, self.doc)["valid"]
                )
                self.assertEqual(check_with_run(self.doc, "REG-D018", bad), "fail")

    def test_project_activity_keeps_accepting_simplified_runs(self):
        # 投影helperは保存済みRunの検証入口ではなく、artifact_type省略の簡略Runも従来どおり。
        simple = {"required_routes": [tc_route("TC-1", "M-1", "manual")]}
        self.assertEqual(
            regression.project_activity(simple, {"M-1": started("PASS")})[
                "activity_state"
            ],
            "完了",
        )
        no_type = {k: v for k, v in self.run.items() if k != "artifact_type"}
        self.assertEqual(
            regression.project_activity(no_type, self.source)["activity_state"], "完了"
        )
        # 同じRunをArtifactとして照合する入口では拒否する。
        self.assertFalse(
            regression.verify_activity_against_run(no_type, self.doc)["valid"]
        )

    def test_valid_run_results_are_unchanged(self):
        # route集合・状態・件数の照合は従来どおり働く。
        forged = {**self.doc, "activity_state": "実行中"}
        self.assertFalse(
            regression.verify_activity_against_run(self.run, forged)["valid"]
        )
        legacy = {
            "artifact_type": "activity",
            "activity_state": "完了",
            "route_results": [],
        }
        self.assertEqual(check_with_run(legacy, "REG-D018"), "pass")


class SemanticCandidateShapeTests(unittest.TestCase):
    """意味評価の候補が保存するActivityは、正規のkey付きobject形を使う。

    意味評価のPASSは、validatorが要求する正規契約への完全適合を意味しない。ここでは
    過去に配列で保存されていた`source_executions`・`tc_execution_state`の形だけを固定する。
    """

    CANDIDATES = ("REG-SEM-007.md", "REG-SEM-004-recheck.md")

    def test_saved_candidate_activities_use_keyed_objects(self):
        directory = SKILL / "evals" / "semantic" / "candidate_outputs"
        for name in self.CANDIDATES:
            text = (directory / name).read_text(encoding="utf-8")
            blocks = [
                json.loads(block)
                for block in re.findall(r"```json\s*\n(.*?)\n```", text, re.DOTALL)
            ]
            activities = [b for b in blocks if b.get("artifact_type") == "activity"]
            with self.subTest(candidate=name):
                self.assertTrue(activities)
                for activity in activities:
                    self.assertIsInstance(activity.get("source_executions"), dict)
                    self.assertIsInstance(activity.get("tc_execution_state"), dict)


if __name__ == "__main__":
    unittest.main()
