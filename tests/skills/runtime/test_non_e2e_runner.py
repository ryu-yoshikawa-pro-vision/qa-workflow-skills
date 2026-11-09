"""Independent subprocess fixtures for the non-E2E runner's actual execution path."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RUNNER = ROOT / "skills/testware-execution/scripts/runner.py"


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


class ActualRunnerTests(unittest.TestCase):
    def setUp(self):
        self.space = tempfile.TemporaryDirectory()
        self.addCleanup(self.space.cleanup)
        base = Path(self.space.name)
        self.repo = base / "source"
        self.repo.mkdir()
        git(self.repo, "init", "-q")
        git(self.repo, "config", "user.email", "qa@example.invalid")
        git(self.repo, "config", "user.name", "QA")
        (self.repo / "README.md").write_text("fixture only\n", encoding="utf-8")
        git(self.repo, "add", "README.md")
        git(self.repo, "commit", "-qm", "fixture")
        self.sha = git(self.repo, "rev-parse", "HEAD")
        self.logs = base / "artifacts"

    def plan(self, argv: list[str], kind: str = "batch") -> dict:
        return {
            "runner_kind": kind,
            "repo_path": str(self.repo),
            "repo_revision": self.sha,
            "argv": argv,
            "reviewed_argv": argv,
            "attempts": 1,
            "timeout_seconds": 5,
            "fixture_only": True,
            "preflight": {
                "source_ref": "fixture:TC-1",
                "source_revision": self.sha,
                "build_revision": self.sha,
                "environment_ref": "isolated-test",
                "operation_ref": "test-fixture",
                "runner_ref": kind,
                "script_chain_reviewed": True,
                "permissions_verified": True,
                "side_effects": [],
                "isolated_environment": True,
                "external_side_effects": False,
                "shared_resource": False,
            },
        }

    def call(self, plan: dict) -> tuple[int, dict, dict | None]:
        plan_file = Path(self.space.name) / "plan.json"
        plan_file.write_text(json.dumps(plan), encoding="utf-8")
        proc = subprocess.run(
            [
                sys.executable,
                str(RUNNER),
                "--plan",
                str(plan_file),
                "--artifacts",
                str(self.logs),
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )
        summary = json.loads(proc.stdout)
        artifact = None
        if "artifact_directory" in summary:
            artifact = json.loads(
                (Path(summary["artifact_directory"]) / "manifest.json").read_text(
                    encoding="utf-8"
                )
            )
        return proc.returncode, summary, artifact

    def test_real_subprocess_preserves_stdout_and_identity(self):
        plan = self.plan([sys.executable, "-c", "print('runner observation')"])
        plan["direct_expectations"] = [
            {"id": "stdout_text", "expected": "runner observation\n"}
        ]
        code, summary, artifact = self.call(plan)
        self.assertEqual(code, 1)
        self.assertEqual(summary["outcome"], "incomplete")
        self.assertEqual(artifact["source_revision"], self.sha)
        attempt = artifact["attempts"][0]
        self.assertTrue(attempt["started"])
        self.assertIsInstance(attempt["pid"], int)
        self.assertEqual(attempt["return_code"], 0)
        self.assertIn("runner observation", Path(attempt["stdout_ref"]).read_text())
        self.assertIsNone(artifact["tc_verdict"])

    def test_invalid_diagnosis_preflight_never_launches_process(self):
        plan = self.plan(
            [sys.executable, "-c", "from pathlib import Path;Path('launched').touch()"]
        )
        plan["diagnosis_hypotheses"] = [
            {
                "cause": "runner",
                "confidence": "low",
                "evidence_ref": "",
                "next_owner": "",
            }
        ]
        code, summary, artifact = self.call(plan)
        self.assertEqual(code, 2)
        self.assertEqual(summary["reason"], "invalid_diagnosis")
        self.assertIsNone(artifact)
        self.assertFalse((self.repo / "launched").exists())
        self.assertFalse(self.logs.exists())

    def test_malformed_diagnosis_entry_is_blocked_without_execution(self):
        plan = self.plan(
            [sys.executable, "-c", "from pathlib import Path;Path('launched').touch()"]
        )
        plan["diagnosis_hypotheses"] = [None]
        code, summary, artifact = self.call(plan)
        self.assertEqual(code, 2)
        self.assertEqual(summary["reason"], "invalid_diagnosis")
        self.assertIsNone(artifact)
        self.assertFalse((self.repo / "launched").exists())

    def test_valid_diagnosis_survives_in_manifest_without_regrading(self):
        plan = self.plan([sys.executable, "-c", "print('run')"])
        plan["direct_expectations"] = [{"id": "exit_code", "expected": 0}]
        plan["diagnosis_hypotheses"] = [
            {
                "cause": "fixture",
                "confidence": "low",
                "evidence_ref": "fixture:observation",
                "next_owner": "testware-implementation",
            }
        ]
        code, _, artifact = self.call(plan)
        self.assertEqual(code, 1)
        self.assertEqual(artifact["diagnosis"]["original_run_ref"], "test-fixture")
        self.assertFalse(artifact["diagnosis"]["original_result_modified"])
        self.assertIsNone(artifact["tc_verdict"])

    def test_forbidden_artifact_root_has_no_write_side_effect(self):
        plan = self.plan([sys.executable, "-c", "print('should not launch')"])
        plan_file = Path(self.space.name) / "plan.json"
        plan_file.write_text(json.dumps(plan), encoding="utf-8")
        forbidden = self.repo / "forbidden" / "nested"
        proc = subprocess.run(
            [
                sys.executable,
                str(RUNNER),
                "--plan",
                str(plan_file),
                "--artifacts",
                str(forbidden),
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )
        self.assertEqual(proc.returncode, 2)
        self.assertEqual(
            json.loads(proc.stdout)["reason"], "artifacts_must_be_outside_repo"
        )
        self.assertFalse((self.repo / "forbidden").exists())
        self.assertEqual(git(self.repo, "status", "--porcelain"), "")

    def test_dirty_repo_and_unreviewed_command_refused(self):
        plan = self.plan([sys.executable, "-c", "print('safe')"])
        plan["reviewed_argv"] = [sys.executable, "-c", "print('different')"]
        self.assertEqual(self.call(plan)[1]["reason"], "argv_not_reviewed")
        (self.repo / "untracked.txt").write_text("do not alter", encoding="utf-8")
        plan["reviewed_argv"] = plan["argv"]
        self.assertEqual(self.call(plan)[1]["reason"], "repo_not_clean")
        self.assertEqual((self.repo / "untracked.txt").read_text(), "do not alter")

    def test_external_effects_blocked_without_native_provider(self):
        plan = self.plan([sys.executable, "-c", "pass"])
        plan["preflight"]["external_side_effects"] = True
        plan["preflight"]["approval_ref"] = "self-asserted-not-authenticated"
        self.assertEqual(
            self.call(plan)[1]["reason"], "native_provider_authorization_required"
        )

    def test_runner_exit_zero_without_case_evidence_is_not_test_complete(self):
        plan = self.plan([sys.executable, "-c", "print('not a test report')"])
        code, summary, artifact = self.call(plan)
        self.assertEqual(code, 1)
        self.assertEqual(summary["outcome"], "incomplete")
        self.assertEqual(artifact["attempts"][0]["return_code"], 0)
        self.assertFalse(artifact["collection_verified"])
        self.assertEqual(artifact["result_collection"], "not_provided_by_adapter")
        self.assertIsNone(artifact["tc_verdict"])

    def test_failed_cleanup_disallows_runner_success(self):
        plan = self.plan([sys.executable, "-c", "print('done')"])
        cleanup = [sys.executable, "-c", "raise SystemExit(1)"]
        plan["cleanup_argv"] = cleanup
        plan["reviewed_cleanup_argv"] = cleanup
        code, _, artifact = self.call(plan)
        self.assertEqual(code, 1)
        self.assertEqual(artifact["outcome"], "blocked_cleanup_or_timeout")
        self.assertEqual(artifact["attempts"][0]["return_code"], 0)
        self.assertEqual(artifact["attempts"][0]["cleanup_state"], "failed_or_unknown")

    def test_timeout_does_not_count_as_pass(self):
        plan = self.plan([sys.executable, "-c", "import time;time.sleep(3)"])
        plan["timeout_seconds"] = 1
        code, _, artifact = self.call(plan)
        self.assertEqual(code, 1)
        self.assertTrue(artifact["attempts"][0]["timeout"])
        self.assertEqual(artifact["outcome"], "blocked_cleanup_or_timeout")

    def test_vitest_absolute_path_reporter_reconciled(self):
        report = {
            "success": True,
            "numTotalTests": 1,
            "numPassedTests": 1,
            "numFailedTests": 0,
            "numPendingTests": 0,
            "numTodoTests": 0,
            "testResults": [
                {
                    "name": str(self.repo / "tests" / "sample.test.ts"),
                    "status": "passed",
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
        py = (
            "import pathlib,sys;"
            "pathlib.Path(sys.argv[1]).write_text("
            + repr(json.dumps(report))
            + ",encoding='utf-8')"
        )
        plan = self.plan(
            [sys.executable, "-c", py, "{reporter_file}"],
            kind="vitest",
        )
        plan["selected"] = [
            {"path": "tests/sample.test.ts", "title_path": ["suite", "one"]}
        ]
        plan["testware_ref"] = "fixture:sample-suite"
        plan["testware_revision"] = self.sha
        plan["runner_version"] = "vitest-fixture"
        plan["selection_verified"] = True
        plan["selection_evidence_ref"] = "fixture:selection"
        plan["planned_scope_ref"] = "fixture:planned-scope"
        code, _, artifact = self.call(plan)
        self.assertEqual(code, 0)
        reconciliation = artifact["attempts"][0]["reconciliation"]
        self.assertTrue(reconciliation["collection_complete"])
        self.assertIsNone(reconciliation["results"][0]["tc_verdict"])
        self.assertEqual(artifact["attempts"][0]["result_collection"], "complete")

    def test_vitest_incorrect_totals_or_setup_failure_incomplete(self):
        report = {
            "success": False,
            "numTotalTests": 2,
            "testResults": [
                {
                    "name": str(self.repo / "tests" / "sample.test.ts"),
                    "status": "failed",
                    "assertionResults": [],
                }
            ],
        }
        py = (
            "import pathlib,sys;"
            "pathlib.Path(sys.argv[1]).write_text("
            + repr(json.dumps(report))
            + ",encoding='utf-8')"
        )
        plan = self.plan([sys.executable, "-c", py, "{reporter_file}"], kind="vitest")
        plan["selected"] = [
            {"path": "tests/sample.test.ts", "title_path": ["suite", "one"]}
        ]
        plan["testware_ref"] = "fixture:sample-suite"
        plan["testware_revision"] = self.sha
        plan["runner_version"] = "vitest-fixture"
        plan["selection_verified"] = True
        plan["selection_evidence_ref"] = "fixture:selection"
        plan["planned_scope_ref"] = "fixture:planned-scope"
        code, _, artifact = self.call(plan)
        self.assertEqual(code, 1)
        self.assertEqual(artifact["outcome"], "incomplete")
        reconciliation = artifact["attempts"][0]["reconciliation"]
        self.assertFalse(reconciliation["reporter_consistent"])
        self.assertEqual(
            reconciliation["failed_suites_without_tests"], ["tests/sample.test.ts"]
        )

    def test_retry_preserves_failed_attempt(self):
        plan = self.plan([sys.executable, "-c", "raise SystemExit(1)"])
        plan["attempts"] = 2
        code, _, artifact = self.call(plan)
        self.assertEqual(code, 1)
        self.assertEqual(len(artifact["attempts"]), 2)
        self.assertTrue(all(a["return_code"] == 1 for a in artifact["attempts"]))

    def test_event_case_report_requires_complete_selected_population(self):
        report = {
            "schema": "non-e2e-cases/v1",
            "source_revision": self.sha,
            "testware_revision": "fixture-event-revision",
            "complete": True,
            "results": [
                {
                    "path": "tests/event.test.py",
                    "title_path": ["event", "processed"],
                    "status": "passed",
                    "attempt_results": [{"status": "passed"}],
                }
            ],
        }
        command = (
            "import pathlib,sys;"
            "pathlib.Path(sys.argv[1]).write_text("
            + repr(json.dumps(report))
            + ",encoding='utf-8')"
        )
        plan = self.plan(
            [sys.executable, "-c", command, "{reporter_file}"], kind="event"
        )
        plan.update(
            {
                "reporter_format": "case-json",
                "testware_ref": "fixture:event",
                "testware_revision": "fixture-event-revision",
                "runner_version": "adapter-fixture-1",
                "selected": [
                    {
                        "path": "tests/event.test.py",
                        "title_path": ["event", "processed"],
                    }
                ],
                "selection_verified": True,
                "selection_evidence_ref": "fixture:selection",
                "planned_scope_ref": "fixture:scope",
            }
        )
        code, _, artifact = self.call(plan)
        self.assertEqual(code, 0)
        self.assertTrue(artifact["collection_verified"])
        self.assertEqual(
            artifact["attempts"][0]["reconciliation"]["results"][0]["runner_status"],
            "passed",
        )
        report["results"] = []
        plan["argv"] = [
            sys.executable,
            "-c",
            "import pathlib,sys;pathlib.Path(sys.argv[1]).write_text("
            + repr(json.dumps(report))
            + ",encoding='utf-8')",
            "{reporter_file}",
        ]
        plan["reviewed_argv"] = plan["argv"]
        code, _, artifact = self.call(plan)
        self.assertEqual(code, 1)
        self.assertEqual(artifact["outcome"], "incomplete")
        self.assertFalse(artifact["collection_verified"])

    def test_playwright_native_json_report_reconciles_api_only_tests(self):
        report = {
            "suites": [
                {
                    "title": "tests/contracts/api.spec.ts",
                    "suites": [],
                    "specs": [
                        {
                            "file": "tests/contracts/api.spec.ts",
                            "title": "returns contract body",
                            "tests": [
                                {
                                    "projectName": "api",
                                    "status": "expected",
                                    "results": [{"status": "passed", "retry": 0}],
                                }
                            ],
                        }
                    ],
                }
            ],
            "errors": [],
            "stats": {"expected": 1, "unexpected": 0, "flaky": 0, "skipped": 0},
        }
        command = (
            "import os,pathlib;"
            "pathlib.Path(os.environ['PLAYWRIGHT_JSON_OUTPUT_FILE']).write_text("
            + repr(json.dumps(report))
            + ",encoding='utf-8')"
        )
        plan = self.plan(
            [sys.executable, "-c", command],
            kind="playwright-api",
        )
        plan.update(
            {
                "reporter_format": "playwright-json",
                "testware_ref": "fixture:api-only",
                "testware_revision": self.sha,
                "runner_version": "playwright-json-fixture",
                "selected": [
                    {
                        "path": "tests/contracts/api.spec.ts",
                        "title_path": ["returns contract body"],
                        "project_name": "api",
                    }
                ],
                "selection_verified": True,
                "selection_evidence_ref": "fixture:selection",
                "planned_scope_ref": "fixture:scope",
            }
        )
        code, _, artifact = self.call(plan)
        self.assertEqual(code, 0)
        self.assertEqual(artifact["reporter_format"], "playwright-json")
        self.assertTrue(
            Path(artifact["attempts"][0]["raw_report_ref"]).is_file()
        )
        self.assertTrue(artifact["collection_verified"])
        self.assertIsNone(artifact["tc_verdict"])

    def test_reporter_failure_with_exit_zero_is_not_verified(self):
        report = {
            "schema": "non-e2e-cases/v1",
            "source_revision": self.sha,
            "testware_revision": "v1",
            "complete": True,
            "results": [
                {
                    "path": "tests/batch.py",
                    "title_path": ["batch"],
                    "status": "failed",
                    "attempt_results": [{"status": "failed"}],
                }
            ],
        }
        command = (
            "import pathlib,sys;"
            "pathlib.Path(sys.argv[1]).write_text("
            + repr(json.dumps(report))
            + ",encoding='utf-8')"
        )
        plan = self.plan([sys.executable, "-c", command, "{reporter_file}"])
        plan.update(
            {
                "reporter_format": "case-json",
                "testware_ref": "fixture:batch",
                "testware_revision": "v1",
                "runner_version": "adapter-fixture",
                "selected": [{"path": "tests/batch.py", "title_path": ["batch"]}],
                "selection_verified": True,
                "selection_evidence_ref": "fixture:selection",
                "planned_scope_ref": "fixture:scope",
            }
        )
        code, _, artifact = self.call(plan)
        self.assertEqual(code, 1)
        self.assertEqual(artifact["outcome"], "incomplete")
        self.assertFalse(artifact["collection_verified"])
        self.assertEqual(artifact["attempts"][0]["return_code"], 0)

    def test_direct_batch_exit_zero_with_wrong_body_is_fail(self):
        plan = self.plan([sys.executable, "-c", "print('{\"ok\": false}')"])
        plan["direct_tc"] = True
        plan["tc_ref"] = "TC-fixture"
        plan["tc_revision"] = "r1"
        plan["expected_authority_ref"] = "fixture:authority"
        plan["direct_expectations"] = [
            {"id": "exit_code", "expected": 0},
            {"id": "stdout_json", "expected": {"ok": True}},
        ]
        code, _, artifact = self.call(plan)
        self.assertEqual(code, 1)
        self.assertEqual(artifact["outcome"], "observed_FAIL")
        self.assertEqual(artifact["tc_verdict"], "FAIL")
        self.assertEqual(artifact["attempts"][0]["return_code"], 0)

    def test_real_local_http_status_200_with_wrong_body_fails(self):
        class FixtureHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                body = json.dumps({"ok": False}).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, format, *args):
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), FixtureHandler)
        self.addCleanup(lambda: (server.shutdown(), server.server_close()))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        script = (
            "import json,urllib.request;"
            f"response=urllib.request.urlopen('http://127.0.0.1:{server.server_port}/',timeout=3);"
            "print(json.dumps({'status':response.status,'body':json.load(response)}))"
        )
        plan = self.plan([sys.executable, "-c", script])
        plan["direct_tc"] = True
        plan["tc_ref"] = "TC-fixture"
        plan["tc_revision"] = "r1"
        plan["expected_authority_ref"] = "fixture:authority"
        plan["direct_expectations"] = [
            {"id": "stdout_json", "expected": {"status": 200, "body": {"ok": True}}}
        ]
        code, _, artifact = self.call(plan)
        self.assertEqual(code, 1)
        self.assertEqual(artifact["tc_verdict"], "FAIL")
        self.assertEqual(artifact["outcome"], "observed_FAIL")
        self.assertEqual(artifact["attempts"][0]["return_code"], 0)

    def test_direct_missing_side_effect_observation_is_unknown(self):
        plan = self.plan([sys.executable, "-c", "print('{\"ok\": true}')"])
        plan["direct_tc"] = True
        plan["tc_ref"] = "TC-fixture"
        plan["tc_revision"] = "r1"
        plan["expected_authority_ref"] = "fixture:authority"
        plan["direct_expectations"] = [
            {"id": "stdout_json", "expected": {"ok": True}},
            {"id": "db_change", "expected": "unchanged"},
        ]
        code, _, artifact = self.call(plan)
        self.assertEqual(code, 1)
        self.assertEqual(artifact["tc_verdict"], "判定不能")
        self.assertEqual(artifact["outcome"], "observations_incomplete")

    def test_nonfunctional_threshold_is_evaluated_from_real_measurement(self):
        plan = self.plan(
            [sys.executable, "-c", "print('{\"p95_ms\": 225}')"],
            kind="nonfunctional",
        )
        plan.update(
            {
                "metric_criteria": [
                    {
                        "id": "p95_ms",
                        "characteristic": "performance",
                        "unit": "ms",
                        "maximum": 200,
                    }
                ],
                "measurement_condition_ref": "fixture-condition-v1",
                "measurement_conditions_verified": True,
                "threshold_authority_ref": "fixture-approved-threshold",
            }
        )
        code, _, artifact = self.call(plan)
        self.assertEqual(code, 1)
        self.assertEqual(artifact["quality_verdict"], "FAIL")
        self.assertEqual(artifact["outcome"], "measurement_FAIL")
        self.assertEqual(artifact["attempts"][0]["return_code"], 0)

    def test_nonfunctional_missing_measurement_is_not_zero(self):
        plan = self.plan(
            [sys.executable, "-c", "print('{\"unrelated\": 0}')"],
            kind="nonfunctional",
        )
        plan.update(
            {
                "metric_criteria": [
                    {
                        "id": "p95_ms",
                        "characteristic": "performance",
                        "unit": "ms",
                        "maximum": 200,
                    }
                ],
                "measurement_condition_ref": "fixture-condition-v1",
                "measurement_conditions_verified": True,
                "threshold_authority_ref": "fixture-approved-threshold",
            }
        )
        code, _, artifact = self.call(plan)
        self.assertEqual(code, 1)
        self.assertEqual(artifact["quality_verdict"], "判定不能")
        self.assertEqual(artifact["outcome"], "measurements_incomplete")

    def test_runner_workspace_side_effect_blocks_completion_without_cleanup(self):
        plan = self.plan(
            [
                sys.executable,
                "-c",
                "from pathlib import Path;Path('unexpected.tmp').write_text('unsafe')",
            ]
        )
        code, _, artifact = self.call(plan)
        self.assertEqual(code, 1)
        self.assertEqual(artifact["outcome"], "blocked_workspace_not_restored")
        self.assertEqual(
            artifact["attempts"][0]["workspace_state_after_cleanup"], "dirty"
        )
        self.assertTrue((self.repo / "unexpected.tmp").exists())

    def test_run_rejects_clean_workspace_with_changed_head(self):
        script = (
            "import pathlib,subprocess;"
            "pathlib.Path('README.md').write_text('changed\\n');"
            "subprocess.run(['git','add','README.md'],check=True);"
            "subprocess.run(['git','commit','-qm','tamper'],check=True)"
        )
        plan = self.plan([sys.executable, "-c", script])
        code, _, artifact = self.call(plan)
        self.assertEqual(code, 1)
        self.assertEqual(artifact["outcome"], "blocked_revision_changed")
        self.assertEqual(
            artifact["attempts"][0]["workspace_state_after_cleanup"], "clean"
        )
        self.assertNotEqual(
            artifact["attempts"][0]["workspace_head_after_cleanup"], self.sha
        )

    def test_nonfunctional_without_threshold_rejected(self):
        plan = self.plan([sys.executable, "-c", "print('ok')"], kind="nonfunctional")
        code, summary, artifact = self.call(plan)
        self.assertEqual(code, 2)
        self.assertEqual(summary["reason"], "missing_nonfunctional_criteria")
        self.assertIsNone(artifact)

    def test_static_requires_rule_and_tool_evidence(self):
        plan = self.plan([sys.executable, "-c", "print('ok')"], kind="static")
        code, summary, _ = self.call(plan)
        self.assertEqual(code, 2)
        self.assertEqual(summary["reason"], "static_analysis_contract_required")
        plan["static_analysis"] = {
            "tool_ref": "fixture",
            "tool_version": "0.1",
            "rules_ref": "fixture-rule",
            "config_ref": "fixture-config",
            "expected_paths": ["README.md"],
            "accepted_exit_codes": [0, 1],
        }
        raw = {
            "findings_count": 0,
            "analyzed_paths": ["README.md"],
            "skipped_paths": [],
            "tool_version": "0.1",
            "rules_ref": "fixture-rule",
            "config_ref": "fixture-config",
        }
        plan["argv"] = [sys.executable, "-c", "print(" + repr(json.dumps(raw)) + ")"]
        plan["reviewed_argv"] = plan["argv"]
        code, _, artifact = self.call(plan)
        self.assertEqual(code, 0)
        self.assertEqual(artifact["outcome"], "runner_pass")
        self.assertTrue(artifact["attempts"][0]["static_analysis"]["complete"])
        plan["argv"] = [sys.executable, "-c", "print('{}')"]
        plan["reviewed_argv"] = plan["argv"]
        code, _, artifact = self.call(plan)
        self.assertEqual(code, 1)
        self.assertEqual(artifact["outcome"], "incomplete")

    def test_direct_tc_without_authority_is_refused(self):
        plan = self.plan([sys.executable, "-c", "print('ok')"])
        plan["direct_tc"] = True
        plan["direct_expectations"] = [{"id": "stdout_text", "expected": "ok"}]
        code, summary, artifact = self.call(plan)
        self.assertEqual(code, 2)
        self.assertEqual(summary["reason"], "tc_ref_required_for_direct_tc")
        self.assertIsNone(artifact)

    def test_static_unapproved_exit_is_incomplete(self):
        plan = self.plan([sys.executable, "-c", "print('ok')"], kind="static")
        plan["static_analysis"] = {
            "tool_ref": "fixture",
            "tool_version": "0.1",
            "rules_ref": "fixture-rule",
            "config_ref": "fixture-config",
            "expected_paths": ["README.md"],
            "accepted_exit_codes": [0, 1],
        }
        report = {
            "findings_count": 0,
            "analyzed_paths": ["README.md"],
            "skipped_paths": [],
            "tool_version": "0.1",
            "rules_ref": "fixture-rule",
            "config_ref": "fixture-config",
        }
        plan["argv"] = [
            sys.executable,
            "-c",
            "print(" + repr(json.dumps(report)) + ");raise SystemExit(2)",
        ]
        plan["reviewed_argv"] = plan["argv"]
        code, _, artifact = self.call(plan)
        self.assertEqual(code, 1)
        self.assertEqual(artifact["outcome"], "incomplete")
        self.assertFalse(artifact["attempts"][0]["static_analysis"]["complete"])

    def test_preflight_flags_must_be_explicit(self):
        plan = self.plan([sys.executable, "-c", "print('ok')"])
        del plan["preflight"]["external_side_effects"]
        code, summary, artifact = self.call(plan)
        self.assertEqual(code, 2)
        self.assertEqual(
            summary["reason"], "preflight_external_side_effects_unverified"
        )
        self.assertIsNone(artifact)


if __name__ == "__main__":
    unittest.main()
