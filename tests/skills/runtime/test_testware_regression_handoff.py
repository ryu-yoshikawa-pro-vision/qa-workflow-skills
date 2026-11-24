"""G（testware-execution）の実runner結果をH（regression-testing）へ渡す横断契約。

runnerを実プロセスとして起動し、そのmanifestを`regression_source_execution()`で
投影してから`project_activity()`へ渡す。手書きのsource executionは使わない。
"""

from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path

from tests.skills.runtime import test_non_e2e_runner as runner_tests

ROOT = Path(__file__).resolve().parents[3]


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


contract = _load(
    "g_testware_contract", ROOT / "skills/testware-execution/scripts/contract.py"
)
regression = _load(
    "h_regression_runtime_handoff",
    ROOT / "skills/regression-testing/scripts/regression_runtime.py",
)

REPORT = {
    "success": True,
    "numTotalTests": 1,
    "numPassedTests": 1,
    "numFailedTests": 0,
    "numPendingTests": 0,
    "numTodoTests": 0,
    "testResults": [
        {
            "name": "tests/sample.test.ts",
            "status": "passed",
            "assertionResults": [
                {"ancestorTitles": ["suite"], "title": "one", "status": "passed"}
            ],
        }
    ],
}


class TestwareRegressionHandoffTests(unittest.TestCase):
    # 実runnerを起動する既存fixture helperだけを再利用し、既存テストは継承しない。
    setUp = runner_tests.ActualRunnerTests.setUp
    plan = runner_tests.ActualRunnerTests.plan
    call = runner_tests.ActualRunnerTests.call

    def vitest_plan(
        self, *, report: dict | None = None, sleep: float = 0, exit_code: int = 0
    ) -> dict:
        body = json.dumps(report if report is not None else REPORT)
        py = (
            "import pathlib,sys,time;"
            f"time.sleep({sleep});"
            f"pathlib.Path(sys.argv[1]).write_text({body!r},encoding='utf-8');"
            f"sys.exit({exit_code})"
        )
        plan = self.plan([sys.executable, "-c", py, "{reporter_file}"], kind="vitest")
        plan.update(
            selected=[{"path": "tests/sample.test.ts", "title_path": ["suite", "one"]}],
            testware_ref="vitest:tests/sample.test.ts::suite one",
            testware_revision=self.sha,
            runner_version="vitest-fixture",
            selection_verified=True,
            selection_evidence_ref="fixture:selection",
            planned_scope_ref="fixture:planned-scope",
            # 実subprocessの結果として扱う。fixture証拠の扱いは個別テストで確認する。
            fixture_only=False,
        )
        return plan

    def run_with_route(self, artifact: dict, *, revision: str | None = None):
        projected = contract.regression_source_execution(artifact)
        route = {
            "tc_ref": "TC-001",
            "route_type": "testware",
            "route_ref": "testware:1",
            "testware_ref": projected["testware_ref"],
            "executor_owner": projected["executor_owner"],
            "implementation_revision": revision or self.sha,
            "selection_basis": "tests/sample.test.ts :: suite one",
            "execution_ref": projected["execution_ref"],
        }
        self.assertTrue(regression.validate_required_routes([route])["valid"])
        run = {
            "route_contract_version": "2",
            "required_routes": [route],
            "auxiliary_testware_count": 0,
        }
        sources = {projected["execution_ref"]: projected["source_execution"]}
        return projected, regression.project_activity(run, sources)

    def test_real_runner_pass_completes_the_regression_route(self) -> None:
        code, _, artifact = self.call(self.vitest_plan())
        self.assertEqual(code, 0)
        projected, activity = self.run_with_route(artifact)
        source = projected["source_execution"]
        self.assertEqual(source["source_result"], "runner_pass")
        self.assertTrue(source["actual_start_confirmed"])
        self.assertTrue(source["raw_capture_complete"])
        self.assertEqual(source["cleanup_status"], "対象なし")
        self.assertEqual(activity["activity_state"], "完了", activity)
        self.assertEqual(activity["counts"]["executed_tc_count"], 1)

    def test_unprojected_runner_manifest_is_not_accepted_as_execution(self) -> None:
        code, _, artifact = self.call(self.vitest_plan())
        self.assertEqual(code, 0)
        projected, _ = self.run_with_route(artifact)
        route = {
            "tc_ref": "TC-001",
            "route_type": "testware",
            "route_ref": "testware:1",
            "testware_ref": projected["testware_ref"],
            "executor_owner": "testware-execution",
            "implementation_revision": self.sha,
            "selection_basis": "tests/sample.test.ts :: suite one",
            "execution_ref": artifact["run_ref"],
        }
        run = {
            "route_contract_version": "2",
            "required_routes": [route],
            "auxiliary_testware_count": 0,
        }
        raw = regression.project_activity(run, {artifact["run_ref"]: artifact})
        self.assertNotEqual(raw["activity_state"], "完了")
        self.assertEqual(raw["counts"]["executed_tc_count"], 0)

    def test_runner_fail_is_executed_but_keeps_source_result(self) -> None:
        failing = json.loads(json.dumps(REPORT))
        failing.update(success=False, numPassedTests=0, numFailedTests=1)
        failing["testResults"][0]["status"] = "failed"
        failing["testResults"][0]["assertionResults"][0]["status"] = "failed"
        code, _, artifact = self.call(self.vitest_plan(report=failing, exit_code=1))
        self.assertEqual(code, 1)
        projected, activity = self.run_with_route(artifact)
        self.assertEqual(projected["source_execution"]["source_result"], "runner_fail")
        self.assertTrue(projected["source_execution"]["result_finalized"])
        self.assertEqual(activity["counts"]["executed_tc_count"], 1)
        self.assertEqual(activity["route_results"][0]["source_result"], "runner_fail")

    def test_timeout_does_not_finalize_or_close_the_route(self) -> None:
        plan = self.vitest_plan(sleep=3)
        plan["timeout_seconds"] = 1
        code, _, artifact = self.call(plan)
        self.assertEqual(code, 1)
        projected, activity = self.run_with_route(artifact)
        source = projected["source_execution"]
        self.assertFalse(source["result_finalized"])
        self.assertFalse(source["raw_capture_complete"])
        self.assertNotEqual(activity["activity_state"], "完了")

    def test_other_revision_is_not_counted_as_this_run(self) -> None:
        code, _, artifact = self.call(self.vitest_plan())
        self.assertEqual(code, 0)
        _, activity = self.run_with_route(artifact, revision="0" * 40)
        self.assertEqual(activity["counts"]["executed_tc_count"], 0)
        self.assertNotEqual(activity["activity_state"], "完了")

    def test_fixture_evidence_is_not_finalized(self) -> None:
        plan = self.vitest_plan()
        plan["fixture_only"] = True
        code, _, artifact = self.call(plan)
        self.assertEqual(code, 0)
        projected, activity = self.run_with_route(artifact)
        self.assertTrue(projected["source_execution"]["evidence_is_fixture"])
        self.assertFalse(projected["source_execution"]["result_finalized"])
        self.assertNotEqual(activity["activity_state"], "完了")

    def test_revision_is_the_verified_checkout_not_the_declared_one(self) -> None:
        plan = self.vitest_plan()
        plan["testware_revision"] = "f" * 40
        code, _, artifact = self.call(plan)
        self.assertEqual(code, 0)
        projected = contract.regression_source_execution(artifact)
        source = projected["source_execution"]
        self.assertEqual(source["implementation_revision"], self.sha)
        self.assertEqual(source["declared_testware_revision"], "f" * 40)
        # 申告revisionをRunの対象にしても、実行したcheckoutと一致しなければ実行扱いしない。
        _, activity = self.run_with_route(artifact, revision="f" * 40)
        self.assertEqual(activity["counts"]["executed_tc_count"], 0)

    def test_failed_cleanup_keeps_cleanup_unconfirmed(self) -> None:
        plan = self.vitest_plan()
        failing_cleanup = [sys.executable, "-c", "import sys; sys.exit(3)"]
        plan["cleanup_argv"] = failing_cleanup
        plan["reviewed_cleanup_argv"] = failing_cleanup
        _, _, artifact = self.call(plan)
        self.assertEqual(artifact["attempts"][-1]["cleanup_state"], "failed_or_unknown")
        projected, activity = self.run_with_route(artifact)
        self.assertEqual(projected["source_execution"]["cleanup_status"], "未確認")
        self.assertNotEqual(activity["activity_state"], "完了")

    def test_successful_cleanup_is_closed(self) -> None:
        plan = self.vitest_plan()
        cleanup = [sys.executable, "-c", "pass"]
        plan["cleanup_argv"] = cleanup
        plan["reviewed_cleanup_argv"] = cleanup
        code, _, artifact = self.call(plan)
        self.assertEqual(code, 0)
        projected, activity = self.run_with_route(artifact)
        self.assertEqual(projected["source_execution"]["cleanup_status"], "成功")
        self.assertEqual(activity["activity_state"], "完了", activity)

    def test_attempt_ref_points_to_the_raw_attempt_directory(self) -> None:
        code, _, artifact = self.call(self.vitest_plan())
        self.assertEqual(code, 0)
        source = contract.regression_source_execution(artifact)["source_execution"]
        attempt = Path(source["attempt_ref"])
        self.assertTrue((attempt / "reporter.json").is_file())
        self.assertIn(str(attempt / "reporter.json"), source["evidence_refs"])

    def test_projection_rejects_incomplete_manifests(self) -> None:
        for broken in ({}, {"run_ref": "r", "repo_revision": "x", "outcome": "o"}):
            with self.subTest(broken=broken):
                with self.assertRaises(contract.ContractError):
                    contract.regression_source_execution(broken)


if __name__ == "__main__":
    unittest.main()
