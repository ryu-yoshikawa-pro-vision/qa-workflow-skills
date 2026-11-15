"""G／H／Iの実結果をJ（test-reporting）の集計へ渡す横断契約。

Gは実runnerを起動して得たmanifest、HはそのmanifestをGの投影経由で`project_activity()`へ
渡したActivity、Iは検証済みSessionから、それぞれ`reporting_records()`でrecordを作り、
Jの実`build_snapshot()`へ渡す。手書きのrecordは使わない。
"""

from __future__ import annotations

import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tests" / "skills" / "runtime"))

import test_cross_owner_exploration_to_defect as i_fixture  # noqa: E402
import test_pr32_test_reporting as j_fixture  # noqa: E402
import test_testware_regression_handoff as gh_fixture  # noqa: E402

contract = gh_fixture.contract
regression = gh_fixture.regression
exploratory = i_fixture.exploratory
reporting = j_fixture.reporting

UNIT_REF = "tests/sample.test.ts::suite > one"


_BASE = gh_fixture.TestwareRegressionHandoffTests


class ResultsToReportingTests(unittest.TestCase):
    # 実runner起動のhelperだけを借用し、既存の個別テストは継承しない。
    setUp = _BASE.setUp
    plan = _BASE.plan
    call = _BASE.call
    vitest_plan = _BASE.vitest_plan
    run_with_route = _BASE.run_with_route

    def run_manifest(self, **kwargs) -> dict:
        code, _, artifact = self.call(self.vitest_plan(**kwargs))
        self.assertIn(code, {0, 1})
        return artifact

    def plan_for(
        self, source_id: str, kind: str, unit: str, refs: list[str], build, env
    ):
        return {
            "plan": {
                "plan_ref": "plan:cross-owner",
                "plan_revision": "p1",
                "approval_state": "approved",
                "scope_ref": "scope:sample",
                "build_ref": build,
                "environment_ref": env,
                "planned_sources": [
                    {
                        "source_id": source_id,
                        "owner_skill": "owner",
                        "kind": kind,
                        "unit": unit,
                        "expected_refs": refs,
                    }
                ],
                "exit_criteria": [],
            },
            "current_source_revisions": {source_id: self.sha},
            "current_plan_revision": "p1",
        }

    def snapshot(self, source_id, kind, unit, refs, records, build, env):
        value = self.plan_for(source_id, kind, unit, refs, build, env)
        value["retrievals"] = [
            j_fixture.retrieval(source_id, records, revision=self.sha)
        ]
        return reporting.build_snapshot(value)

    # --- G -------------------------------------------------------------
    def test_real_runner_results_are_counted_by_unit(self) -> None:
        manifest = self.run_manifest()
        projected = contract.reporting_records(manifest)
        record = projected["records"][0]
        self.assertEqual(record["unit"], "test")
        self.assertEqual(record["unit_ref"], UNIT_REF)
        self.assertEqual(record["state"], "PASS")
        self.assertTrue(record["result_finalized"])
        snap = self.snapshot(
            "api",
            "component",
            "test",
            [UNIT_REF],
            projected["records"],
            record["build_ref"],
            record["environment_ref"],
        )
        source = next(s for s in snap["sources"] if s["source_id"] == "api")
        self.assertTrue(source["complete"], source)
        self.assertEqual(source["counts"], {"PASS": 1})

    def test_timeout_and_fixture_results_never_become_pass(self) -> None:
        plan = self.vitest_plan(sleep=3)
        plan["timeout_seconds"] = 1
        code, _, timed_out = self.call(plan)
        self.assertEqual(code, 1)
        for manifest in (timed_out, self.fixture_manifest()):
            with self.subTest(outcome=manifest["outcome"]):
                records = contract.reporting_records(manifest)["records"]
                self.assertNotIn("PASS", {r["state"] for r in records})
                self.assertFalse(any(r["result_finalized"] for r in records))
                snap = self.snapshot(
                    "api",
                    "component",
                    "test",
                    [UNIT_REF],
                    records,
                    records[0]["build_ref"],
                    records[0]["environment_ref"],
                )
                self.assertFalse(snap["overall"]["complete"])

    def fixture_manifest(self) -> dict:
        plan = self.vitest_plan()
        plan["fixture_only"] = True
        code, _, manifest = self.call(plan)
        self.assertEqual(code, 0)
        return manifest

    def test_unplanned_unit_is_not_counted_as_planned(self) -> None:
        manifest = self.run_manifest()
        records = contract.reporting_records(manifest)["records"]
        snap = self.snapshot(
            "api",
            "component",
            "test",
            ["tests/other.test.ts::suite > two"],
            records,
            records[0]["build_ref"],
            records[0]["environment_ref"],
        )
        self.assertFalse(snap["overall"]["complete"])

    # --- H -------------------------------------------------------------
    def test_regression_activity_results_reach_the_report(self) -> None:
        manifest = self.run_manifest()
        projected, activity = self.run_with_route(manifest)
        self.assertEqual(activity["activity_state"], "完了")
        out = regression.reporting_records(
            activity,
            build_ref=manifest["build_revision"],
            environment_ref=manifest["environment_ref"],
            source_revision=self.sha,
        )
        self.assertEqual(out["status"], "ready", out)
        record = out["records"][0]
        # Activityの「完了」は結果ではなく、元のrunner結果（runner_pass）がPASSになる。
        self.assertEqual(record["unit"], "tc_route")
        self.assertEqual(record["state"], "PASS")
        snap = self.snapshot(
            "regression",
            "regression",
            "tc_route",
            [record["unit_ref"]],
            out["records"],
            manifest["build_revision"],
            manifest["environment_ref"],
        )
        source = next(s for s in snap["sources"] if s["source_id"] == "regression")
        self.assertTrue(source["complete"], source)

    def test_regression_unexecuted_and_blocked_routes_are_not_pass(self) -> None:
        plan = self.vitest_plan(sleep=3)
        plan["timeout_seconds"] = 1
        code, _, timed_out = self.call(plan)
        self.assertEqual(code, 1)
        _, activity = self.run_with_route(timed_out)
        out = regression.reporting_records(
            activity,
            build_ref=timed_out["build_revision"],
            environment_ref=timed_out["environment_ref"],
            source_revision=self.sha,
        )
        self.assertNotIn("PASS", {r["state"] for r in out["records"]})
        self.assertFalse(any(r["result_finalized"] for r in out["records"]))
        missing = regression.reporting_records(
            activity, build_ref="", environment_ref="", source_revision=None
        )
        self.assertEqual(missing["reason"], "build_and_environment_required")

    # --- I -------------------------------------------------------------
    def test_exploration_session_is_reported_but_never_as_pass_or_fail(self) -> None:
        session = i_fixture.session()
        out = exploratory.reporting_records(
            session,
            session_revision=i_fixture.SESSION_REVISION,
            target_snapshot=i_fixture.TARGET,
            environment_conditions=i_fixture.ENVIRONMENT,
            executed_at=datetime(2026, 11, 13, tzinfo=timezone.utc).isoformat(),
        )
        self.assertEqual(out["status"], "ready", out)
        record = out["records"][0]
        self.assertEqual(record["state"], "判定不能")
        snap = self.snapshot(
            "explore",
            "exploration",
            "session",
            [record["unit_ref"]],
            out["records"],
            record["build_ref"],
            record["environment_ref"],
        )
        source = next(s for s in snap["sources"] if s["source_id"] == "explore")
        self.assertEqual(source["counts"], {"判定不能": 1})
        self.assertEqual(source["counts"].get("PASS", 0), 0)

    def test_session_with_other_environment_is_rejected(self) -> None:
        out = exploratory.reporting_records(
            i_fixture.session(),
            session_revision=i_fixture.SESSION_REVISION,
            target_snapshot=i_fixture.TARGET,
            environment_conditions={"origin": "https://other.example.test"},
        )
        self.assertEqual(out["reason"], "charter_snapshot_identity_mismatch")


# 借用元のテストclassを、このmoduleのloader対象から外す。
del _BASE

if __name__ == "__main__":
    unittest.main()
