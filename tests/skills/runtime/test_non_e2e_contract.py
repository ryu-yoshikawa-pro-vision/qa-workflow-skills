from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def load(relative: str, name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


contract = load("skills/testware-execution/scripts/contract.py", "non_e2e_contract")
guard = load(
    "skills/testware-implementation/scripts/snapshot_guard.py", "non_e2e_guard"
)


class RoutingTests(unittest.TestCase):
    def test_activity_not_runner_brand(self):
        self.assertEqual(
            contract.classify_owner(activity="run", tool="playwright", browser=False),
            "testware-execution",
        )
        self.assertEqual(
            contract.classify_owner(
                activity="run", tool="playwright", browser=True, persistent=True
            ),
            "e2e-test-execution",
        )
        self.assertEqual(
            contract.classify_owner(activity="direct_tc", tool="http", browser=True),
            "test-execution",
        )
        self.assertEqual(
            contract.classify_owner(activity="static_tool", tool="ruff"),
            "testware-execution",
        )
        self.assertEqual(
            contract.classify_owner(activity="meaning_review", tool="agent"),
            "adversarial-review",
        )

    def test_preflight_fail_closed(self):
        spec = {
            "source_ref": "TC-1",
            "source_revision": "v1",
            "build_revision": "a1",
            "environment_ref": "fixture",
            "operation_ref": "op1",
            "runner_ref": "vitest",
            "script_chain_reviewed": True,
            "permissions_verified": True,
            "side_effects": [],
            "isolated_environment": True,
            "external_side_effects": False,
            "shared_resource": False,
        }
        self.assertTrue(contract.preflight(spec)["may_start"])
        self.assertEqual(
            contract.preflight(
                {
                    key: value
                    for key, value in spec.items()
                    if key != "external_side_effects"
                }
            )["reason"],
            "external_side_effects_unverified",
        )
        self.assertFalse(
            contract.preflight({**spec, "script_chain_reviewed": False})["may_start"]
        )
        self.assertEqual(
            contract.preflight({**spec, "shared_resource": True})["reason"],
            "shared_reservation_provider_required",
        )
        self.assertEqual(
            contract.preflight(
                {**spec, "side_effects": [{"scope": "mail", "max_count": 1}]}
            )["reason"],
            "cleanup_unverified",
        )
        self.assertEqual(
            contract.preflight({**spec, "external_side_effects": True})["reason"],
            "external_approval_required",
        )


class VitestTests(unittest.TestCase):
    def test_partial_and_skipped_remain_incomplete(self):
        selected = [
            {"path": "tests/a.test.ts", "title_path": ["suite", "one"]},
            {"path": "tests/a.test.ts", "title_path": ["suite", "two"]},
        ]
        report = {
            "testResults": [
                {
                    "name": "tests/a.test.ts",
                    "assertionResults": [
                        {
                            "ancestorTitles": ["suite"],
                            "title": "one",
                            "status": "passed",
                        }
                    ],
                }
            ]
        }
        result = contract.reconcile_vitest(
            selected=selected,
            report=report,
            source_revision="sha123",
            raw_ref="local:report",
            selection_verified=True,
        )
        self.assertFalse(result["collection_complete"])
        self.assertEqual(result["results"][1]["runner_status"], "not_collected")
        self.assertFalse(result["tc_verdicts_assessed"])
        self.assertIsNone(result["results"][0]["tc_verdict"])

    def test_vitest_official_json_root_ancestor_is_ignored(self):
        report = {
            "success": True,
            "numTotalTests": 1,
            "numPassedTests": 1,
            "numFailedTests": 0,
            "numPendingTests": 0,
            "numTodoTests": 0,
            "testResults": [
                {
                    "name": "tests/official.test.ts",
                    "status": "passed",
                    "assertionResults": [
                        {
                            "ancestorTitles": ["", "first test file"],
                            "title": "2 + 2 should equal 4",
                            "status": "passed",
                        }
                    ],
                }
            ],
        }
        result = contract.reconcile_vitest(
            selected=[
                {
                    "path": "tests/official.test.ts",
                    "title_path": ["first test file", "2 + 2 should equal 4"],
                }
            ],
            report=report,
            source_revision="fixed",
            raw_ref="raw",
            selection_verified=True,
        )
        self.assertTrue(result["collection_complete"])
        report["testResults"][0]["assertionResults"][0]["ancestorTitles"] = [
            "first test file",
            "",
            "inner suite",
        ]
        with self.assertRaises(contract.ContractError):
            contract.reconcile_vitest(
                selected=[
                    {
                        "path": "tests/official.test.ts",
                        "title_path": ["first test file", "2 + 2 should equal 4"],
                    }
                ],
                report=report,
                source_revision="fixed",
                raw_ref="raw",
                selection_verified=True,
            )
        # Official Vitest 4 has one structural empty root, not several.
        report["testResults"][0]["assertionResults"][0]["ancestorTitles"] = [
            "",
            "",
            "first test file",
        ]
        with self.assertRaises(contract.ContractError):
            contract.reconcile_vitest(
                selected=[
                    {
                        "path": "tests/official.test.ts",
                        "title_path": ["first test file", "2 + 2 should equal 4"],
                    }
                ],
                report=report,
                source_revision="fixed",
                raw_ref="raw",
                selection_verified=True,
            )

    def test_vitest_project_requires_verifiable_single_project(self):
        report = {
            "success": True, "numTotalTests": 1, "numPassedTests": 1,
            "numFailedTests": 0, "numPendingTests": 0, "numTodoTests": 0,
            "testResults": [{
                "name": "tests/one.test.ts", "status": "passed",
                "assertionResults": [{
                    "ancestorTitles": [""], "title": "case", "status": "passed",
                }],
            }],
        }
        item = {
            "path": "tests/one.test.ts", "title_path": ["case"],
            "project_name": "node",
        }
        kwargs = dict(
            report=report, source_revision="sha", raw_ref="raw",
            selection_verified=True,
        )
        with self.assertRaisesRegex(contract.ContractError, "project_identity"):
            contract.reconcile_vitest(selected=[item], **kwargs)
        good = contract.reconcile_vitest(
            selected=[item], project_name="node", project_verified=True,
            **kwargs,
        )
        self.assertTrue(good["collection_complete"])
        with self.assertRaisesRegex(contract.ContractError, "project_identity"):
            contract.reconcile_vitest(
                selected=[item, {**item, "project_name": "browser"}],
                project_name="node", project_verified=True, **kwargs,
            )

    def test_duplicates_are_not_implicitly_matched(self):
        case = {"ancestorTitles": ["s"], "title": "a", "status": "passed"}
        report = {
            "testResults": [
                {"name": "tests/a.test.ts", "assertionResults": [case, case]}
            ]
        }
        actual = contract.reconcile_vitest(
            selected=[{"path": "tests/a.test.ts", "title_path": ["s", "a"]}],
            report=report,
            source_revision="v1",
            raw_ref="raw",
            selection_verified=True,
        )
        self.assertEqual(actual["results"][0]["runner_status"], "ambiguous")
        self.assertFalse(actual["collection_complete"])

    def test_skip_todo_and_file_revision(self):
        report = {
            "success": True,
            "numTotalTests": 2,
            "numPassedTests": 0,
            "numFailedTests": 0,
            "numPendingTests": 1,
            "numTodoTests": 1,
            "testResults": [
                {
                    "name": "tests/new.test.ts",
                    "status": "passed",
                    "assertionResults": [
                        {"ancestorTitles": [], "title": "skipped", "status": "pending"},
                        {"ancestorTitles": [], "title": "todo", "status": "todo"},
                    ],
                }
            ],
        }
        selected = [
            {"path": "tests/new.test.ts", "title_path": [x]}
            for x in ("skipped", "todo")
        ]
        r = contract.reconcile_vitest(
            selected=selected,
            report=report,
            source_revision="fixed-sha",
            raw_ref="raw",
            selection_verified=True,
        )
        self.assertTrue(r["collection_complete"])
        self.assertEqual(
            [x["runner_status"] for x in r["results"]], ["pending", "todo"]
        )
        missing_total = {k: v for k, v in report.items() if k != "numTotalTests"}
        partial = contract.reconcile_vitest(
            selected=selected,
            report=missing_total,
            source_revision="fixed-sha",
            raw_ref="raw",
            selection_verified=True,
        )
        self.assertFalse(partial["collection_complete"])
        missing_success = {k: v for k, v in report.items() if k != "success"}
        partial = contract.reconcile_vitest(
            selected=selected,
            report=missing_success,
            source_revision="fixed-sha",
            raw_ref="raw",
            selection_verified=True,
        )
        self.assertFalse(partial["collection_complete"])
        with self.assertRaises(contract.ContractError):
            contract.reconcile_vitest(
                selected=selected,
                report={
                    "testResults": [
                        {"name": "/private/old.test.ts", "assertionResults": []}
                    ]
                },
                source_revision="fixed-sha",
                raw_ref="raw",
            )

    def test_skipped_suite_with_executed_assertion_is_incomplete(self):
        report = {
            "success": True,
            "numTotalTests": 1,
            "numPassedTests": 1,
            "numFailedTests": 0,
            "numPendingTests": 0,
            "numTodoTests": 0,
            "testResults": [
                {
                    "name": "tests/skipped.test.ts",
                    "status": "skipped",
                    "assertionResults": [
                        {
                            "ancestorTitles": ["group"],
                            "title": "really ran",
                            "status": "passed",
                        }
                    ],
                }
            ],
        }
        actual = contract.reconcile_vitest(
            selected=[
                {"path": "tests/skipped.test.ts", "title_path": ["group", "really ran"]}
            ],
            report=report,
            source_revision="pinned",
            raw_ref="raw",
            selection_verified=True,
        )
        self.assertEqual(actual["inconsistent_suites"], ["tests/skipped.test.ts"])
        self.assertFalse(actual["collection_complete"])

    def test_suite_failure_with_passing_assertions_is_not_complete(self):
        report = {
            "success": True,
            "numTotalTests": 1,
            "numPassedTests": 1,
            "testResults": [
                {
                    "name": "tests/api.test.ts",
                    "status": "failed",
                    "assertionResults": [
                        {
                            "ancestorTitles": ["suite"],
                            "title": "one",
                            "status": "passed",
                        }
                    ],
                }
            ],
        }
        result = contract.reconcile_vitest(
            selected=[{"path": "tests/api.test.ts", "title_path": ["suite", "one"]}],
            report=report,
            source_revision="sha",
            raw_ref="raw",
            selection_verified=True,
        )
        self.assertFalse(result["collection_complete"])
        self.assertEqual(result["inconsistent_suites"], ["tests/api.test.ts"])


class OtherRunnerReportTests(unittest.TestCase):
    def test_case_report_keeps_planned_population_and_attempts(self):
        selected = [
            {"path": "tests/batch.py", "title_path": ["batch", "one"]},
            {"path": "tests/batch.py", "title_path": ["batch", "two"]},
        ]
        report = {
            "schema": "non-e2e-cases/v1",
            "source_revision": "commit-1",
            "testware_revision": "revision-1",
            "runner_version": "fixture-runner",
            "complete": True,
            "results": [
                {
                    "path": "tests/batch.py",
                    "title_path": ["batch", "one"],
                    "status": "passed",
                    "attempt_results": [
                        {"status": "failed", "retry": 0},
                        {"status": "passed", "retry": 1},
                    ],
                },
                {
                    "path": "tests/batch.py",
                    "title_path": ["batch", "two"],
                    "status": "skipped",
                    "attempt_results": [],
                },
            ],
        }
        result = contract.reconcile_case_report(
            selected=selected,
            report=report,
            source_revision="commit-1",
            testware_revision="revision-1",
            runner_version="fixture-runner",
            raw_ref="run:raw",
            selection_verified=True,
        )
        self.assertTrue(result["collection_complete"])
        self.assertEqual(len(result["results"][0]["attempt_results"]), 2)
        report["results"][0]["attempt_results"][1]["retry"] = 0
        with self.assertRaises(contract.ContractError):
            contract.reconcile_case_report(
                selected=selected,
                report=report,
                source_revision="commit-1",
                testware_revision="revision-1",
                runner_version="fixture-runner",
                raw_ref="run:raw",
                selection_verified=True,
            )
        report["results"][0]["attempt_results"][1]["retry"] = 1
        self.assertIsNone(result["results"][0]["tc_verdict"])
        report["results"].pop()
        partial = contract.reconcile_case_report(
            selected=selected,
            report=report,
            source_revision="commit-1",
            testware_revision="revision-1",
            runner_version="fixture-runner",
            raw_ref="run:raw",
            selection_verified=True,
        )
        self.assertFalse(partial["collection_complete"])
        self.assertEqual(partial["results"][1]["runner_status"], "not_collected")

    def test_case_report_does_not_discard_empty_titles(self):
        selected = [{"path": "tests/event.py", "title_path": ["one"]}]
        report = {
            "schema": "non-e2e-cases/v1",
            "source_revision": "a",
            "testware_revision": "b",
            "runner_version": "c",
            "complete": True,
            "results": [{
                "path": "tests/event.py",
                "title_path": ["", "one"],
                "status": "passed",
                "attempt_results": [{"status": "passed", "retry": 0}],
            }],
        }
        with self.assertRaisesRegex(contract.ContractError, "invalid_title"):
            contract.reconcile_case_report(
                selected=selected, report=report, source_revision="a",
                testware_revision="b", runner_version="c", raw_ref="raw",
                selection_verified=True,
            )

    def test_case_report_rejects_stale_and_duplicate(self):
        selected = [{"path": "tests/event.py", "title_path": ["event"]}]
        row = {
            "path": "tests/event.py",
            "title_path": ["event"],
            "status": "passed",
            "attempt_results": [{"status": "passed", "retry": 0}],
        }
        report = {
            "schema": "non-e2e-cases/v1",
            "source_revision": "base",
            "testware_revision": "v1",
            "runner_version": "fixture-runner",
            "complete": True,
            "results": [row, row],
        }
        result = contract.reconcile_case_report(
            selected=selected,
            report=report,
            source_revision="base",
            testware_revision="v1",
            runner_version="fixture-runner",
            raw_ref="raw",
            selection_verified=True,
        )
        self.assertFalse(result["collection_complete"])
        self.assertEqual(result["results"][0]["runner_status"], "ambiguous")
        with self.assertRaises(contract.ContractError):
            contract.reconcile_case_report(
                selected=selected,
                report=report,
                source_revision="new-base",
                testware_revision="v1",
                runner_version="fixture-runner",
                raw_ref="raw",
                selection_verified=True,
            )

    def test_playwright_report_preserves_project_and_attempts(self):
        report = {
            "config": {"version": "fixture-playwright-1"},
            "suites": [
                {
                    "title": "tests/api.spec.ts",
                    "specs": [],
                    "suites": [
                        {
                            "title": "API",
                            "suites": [],
                            "specs": [
                                {
                                    "file": "tests/api.spec.ts",
                                    "title": "returns body",
                                    "tests": [
                                        {
                                            "projectName": "api",
                                            "expectedStatus": "passed",
                                            "status": "flaky",
                                            "results": [
                                                {"status": "failed", "retry": 0},
                                                {"status": "passed", "retry": 1},
                                            ],
                                        }
                                    ],
                                }
                            ],
                        }
                    ],
                }
            ],
            "errors": [],
            "stats": {"expected": 0, "unexpected": 0, "flaky": 1, "skipped": 0},
        }
        selected = [
            {
                "path": "tests/api.spec.ts",
                "title_path": ["API", "returns body"],
                "project_name": "api",
            }
        ]
        result = contract.reconcile_playwright(
            selected=selected,
            report=report,
            source_revision="sha",
            runner_version="fixture-playwright-1",
            raw_ref="raw",
            selection_verified=True,
        )
        self.assertTrue(result["collection_complete"])
        self.assertEqual(result["results"][0]["runner_status"], "flaky")
        report["config"]["version"] = "another-playwright-version"
        wrong_version = contract.reconcile_playwright(
            selected=selected,
            report=report,
            source_revision="sha",
            runner_version="fixture-playwright-1",
            raw_ref="raw",
            selection_verified=True,
        )
        self.assertFalse(wrong_version["collection_complete"])
        report["config"]["version"] = "fixture-playwright-1"
        report["suites"][0]["suites"][0]["specs"][0]["tests"][0]["status"] = "expected"
        with self.assertRaises(contract.ContractError):
            contract.reconcile_playwright(
                selected=selected,
                report=report,
                source_revision="sha",
                runner_version="fixture-playwright-1",
                raw_ref="raw",
                selection_verified=True,
            )
        report["suites"][0]["suites"][0]["specs"][0]["tests"][0]["status"] = "flaky"
        self.assertEqual(
            [r["retry"] for r in result["results"][0]["attempt_results"]],
            [0, 1],
        )
        report["errors"] = [{"message": "global teardown failed"}]
        incomplete = contract.reconcile_playwright(
            selected=selected,
            report=report,
            source_revision="sha",
            runner_version="fixture-playwright-1",
            raw_ref="raw",
            selection_verified=True,
        )
        self.assertFalse(incomplete["collection_complete"])

    def test_playwright_root_dir_normalization_and_escape(self):
        report = {
            "config": {"version": "fixture", "rootDir": "/work/project/tests"},
            "suites": [{
                "title": "api.spec.ts",
                "specs": [{
                    "file": "api.spec.ts", "title": "request",
                    "tests": [{
                        "projectName": "api", "expectedStatus": "passed",
                        "status": "expected",
                        "results": [{"status": "passed", "retry": 0}],
                    }],
                }],
            }],
            "errors": [],
            "stats": {"expected": 1, "unexpected": 0, "flaky": 0, "skipped": 0},
        }
        params = dict(
            selected=[{
                "path": "tests/api.spec.ts", "title_path": ["request"],
                "project_name": "api",
            }],
            report=report, repo_root="/work/project",
            source_revision="sha", runner_version="fixture",
            raw_ref="raw", selection_verified=True,
        )
        self.assertTrue(contract.reconcile_playwright(**params)["collection_complete"])
        report["config"]["rootDir"] = "/outside/tests"
        with self.assertRaisesRegex(contract.ContractError, "outside_root"):
            contract.reconcile_playwright(**params)

    def test_playwright_report_rejects_missing_spec_and_wrong_selection(self):
        report = {
            "config": {"version": "fixture-playwright-1"},
            "suites": [{"title": "tests/api.spec.ts", "specs": [], "suites": []}],
            "errors": [],
            "stats": {"expected": 0, "unexpected": 0, "flaky": 0, "skipped": 0},
        }
        r = contract.reconcile_playwright(
            selected=[{"path": "tests/api.spec.ts", "title_path": ["missing"]}],
            report=report,
            source_revision="sha",
            runner_version="fixture-playwright-1",
            raw_ref="raw",
            selection_verified=True,
        )
        self.assertFalse(r["collection_complete"])
        self.assertEqual(r["results"][0]["runner_status"], "not_collected")


class DirectAndStaticTests(unittest.TestCase):
    def test_http_200_but_body_fails(self):
        checks = [
            {"id": "code", "expected": 200},
            {"id": "body", "expected": {"ok": True}},
        ]
        r = contract.compare_direct(
            started=True,
            expectations=checks,
            observations={"code": 200, "body": {"ok": False}},
        )
        self.assertEqual(r["result"], "FAIL")
        # In Python True == 1; an actual JSON number must not satisfy
        # an expected JSON boolean nested in the response body.
        nested_type_mismatch = contract.compare_direct(
            started=True,
            expectations=checks,
            observations={"code": 200, "body": {"ok": 1}},
        )
        self.assertEqual(nested_type_mismatch["result"], "FAIL")
        self.assertEqual(
            contract.compare_direct(
                started=True, expectations=checks, observations={"code": 200}
            )["result"],
            "判定不能",
        )
        self.assertEqual(
            contract.compare_direct(
                started=False, expectations=checks, observations={}
            )["result"],
            "未実行",
        )

    def test_static_zero_exit_is_not_auto_zero_findings(self):
        self.assertEqual(
            contract.interpret_static(
                started=True, exit_code=0, raw_ref="raw", findings_count=None
            )["state"],
            "取得不完全",
        )
        self.assertEqual(
            contract.interpret_static(
                started=True, exit_code=0, raw_ref="raw", findings_count=0
            )["state"],
            "実行済み",
        )
        with self.assertRaises(contract.ContractError):
            contract.interpret_static(
                started=False, exit_code=0, raw_ref=None, findings_count=None
            )

    def test_hypotheses_cannot_become_defects(self):
        d = contract.diagnosis(
            run_ref="run-v1",
            hypotheses=[
                {
                    "cause": "fixture",
                    "confidence": "low",
                    "evidence_ref": "raw:1",
                    "next_owner": "testware-implementation",
                }
            ],
        )
        self.assertFalse(d["defect_confirmed"])


class GuardTests(unittest.TestCase):
    def test_stale_path_and_dirty_rejected(self):
        digest = guard.file_digest(b"first")
        args = dict(
            expected_head="h1",
            actual_head="h1",
            tracked={"tests/a.py": digest},
            actual={"tests/a.py": b"first"},
            allowed_prefixes=["tests"],
            dirty_paths=[],
            change_paths=["tests/a.py"],
        )
        self.assertTrue(guard.check_snapshot(**args)["safe_to_prepare"])
        self.assertFalse(
            guard.check_snapshot(**{**args, "actual": {"tests/a.py": b"second"}})[
                "safe_to_prepare"
            ]
        )
        self.assertFalse(
            guard.check_snapshot(**{**args, "actual_head": "h2"})["safe_to_prepare"]
        )
        self.assertFalse(
            guard.check_snapshot(**{**args, "dirty_paths": ["tests/a.py"]})[
                "safe_to_prepare"
            ]
        )
        self.assertTrue(
            guard.check_snapshot(**{**args, "dirty_paths": ["README.md"]})[
                "safe_to_prepare"
            ]
        )

    def test_out_of_scope_and_missing_snapshot_refused(self):
        with self.assertRaises(guard.SnapshotError):
            guard.check_snapshot(
                expected_head="a",
                actual_head="a",
                tracked={},
                actual={},
                allowed_prefixes=["tests"],
                dirty_paths=[],
                change_paths=["../src/app.py"],
            )
        with self.assertRaises(guard.SnapshotError):
            guard.check_snapshot(
                expected_head="a",
                actual_head="a",
                tracked={},
                actual={},
                allowed_prefixes=["tests"],
                dirty_paths=[],
                change_paths=["tests/a.py"],
            )
        # A valid normalized path outside the permitted prefix must also fail.
        scope = guard.check_snapshot(
            expected_head="a",
            actual_head="a",
            tracked={"src/app.py": guard.file_digest(b"source")},
            actual={"src/app.py": b"source"},
            allowed_prefixes=["tests"],
            dirty_paths=[],
            change_paths=["src/app.py"],
        )
        self.assertFalse(scope["safe_to_prepare"])
        self.assertIn("path_out_of_scope", scope["reasons"])


if __name__ == "__main__":
    unittest.main()
