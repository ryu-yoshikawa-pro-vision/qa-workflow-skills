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

    def attach_direct_tc_authority(self, plan: dict) -> None:
        """Commit the accepted complete TC expected observations in source HEAD."""
        authority = self.repo / "tests" / "direct-authority.json"
        authority.parent.mkdir(exist_ok=True)
        authority.write_text(
            json.dumps(
                {
                    "tc_ref": plan["tc_ref"],
                    "tc_revision": plan["tc_revision"],
                    "expected_authority_ref": plan["expected_authority_ref"],
                    "direct_expectations": plan["direct_expectations"],
                }
            ),
            encoding="utf-8",
        )
        git(self.repo, "add", "tests/direct-authority.json")
        git(self.repo, "commit", "-qm", "fixture direct TC expected outcomes")
        self.sha = git(self.repo, "rev-parse", "HEAD")
        plan["repo_revision"] = self.sha
        plan["preflight"]["source_revision"] = self.sha
        plan["preflight"]["build_revision"] = self.sha
        plan["direct_tc_authority_file"] = "tests/direct-authority.json"

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

    def test_fixed_product_vitest_plan_requires_independent_preflight(self):
        example = (
            ROOT
            / "skills/testware-execution/assets"
            / "qa-training-store-pricing-vitest.plan.json"
        )
        plan = json.loads(example.read_text(encoding="utf-8"))
        self.assertEqual(
            plan["repo_revision"], "2a8bcf57ff091e84a8b3bf7b123568e967000d88"
        )
        self.assertEqual(plan["preflight"]["source_revision"], plan["repo_revision"])
        self.assertEqual(plan["argv"], plan["reviewed_argv"])
        self.assertEqual(plan["runner_kind"], "vitest")
        self.assertEqual(len(plan["selected"]), 3)
        self.assertFalse(plan["preflight"]["script_chain_reviewed"])
        self.assertFalse(plan["preflight"]["permissions_verified"])
        self.assertFalse(plan["preflight"]["isolated_environment"])
        self.assertFalse(plan["selection_verified"])
        self.assertEqual(plan["preflight"]["environment_ref"], "")
        self.assertEqual(plan["preflight"]["operation_ref"], "")
        self.assertEqual(plan["selection_evidence_ref"], "")
        code, summary, artifact = self.call(plan)
        self.assertEqual(code, 2)
        self.assertEqual(summary["reason"], "preflight_missing_run_identity")
        self.assertIsNone(artifact)
        # Simply switching approval flags cannot turn an ungrounded example
        # into valid acceptance evidence without real run identities.
        for field in (
            "script_chain_reviewed",
            "permissions_verified",
            "isolated_environment",
        ):
            plan["preflight"][field] = True
        plan["selection_verified"] = True
        code, summary, artifact = self.call(plan)
        self.assertEqual(code, 2)
        self.assertEqual(summary["reason"], "preflight_missing_run_identity")
        self.assertIsNone(artifact)

    def test_duplicate_preflight_key_is_rejected_before_execution(self):
        plan = self.plan([sys.executable, "-c", "print('should-not-run')"])
        source = json.dumps(plan)
        sentinel = '"script_chain_reviewed": true'
        self.assertEqual(source.count(sentinel), 1)
        source = source.replace(
            sentinel,
            '"script_chain_reviewed": false, "script_chain_reviewed": true',
        )
        plan_file = Path(self.space.name) / "duplicate-plan.json"
        plan_file.write_text(source, encoding="utf-8")
        result = subprocess.run(
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
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stdout)["reason"], "duplicate_json_key")
        self.assertFalse(self.logs.exists())

        # Python's JSON parser otherwise accepts NaN/Infinity, which are not
        # valid JSON values and must not enter authorization metadata.
        source = json.dumps(plan)
        self.assertEqual(source.count('"attempts": 1'), 1)
        plan_file.write_text(
            source.replace('"attempts": 1', '"attempts": NaN'),
            encoding="utf-8",
        )
        result = subprocess.run(
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
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stdout)["reason"], "nonfinite_json_number")
        self.assertFalse(self.logs.exists())

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

        # Missing official global success must not turn a zero-exit process
        # into a verified Vitest pass, even with a matching selected test.
        report.pop("success")
        incomplete_script = (
            "import pathlib,sys;"
            "pathlib.Path(sys.argv[1]).write_text("
            + repr(json.dumps(report))
            + ",encoding='utf-8')"
        )
        plan["argv"] = [sys.executable, "-c", incomplete_script, "{reporter_file}"]
        plan["reviewed_argv"] = plan["argv"]
        code, _, artifact = self.call(plan)
        self.assertEqual(code, 1)
        self.assertEqual(artifact["outcome"], "incomplete")
        self.assertEqual(artifact["attempts"][0]["result_collection"], "incomplete")

    def test_component_native_jest_compatible_json_report(self):
        report = {
            "success": True,
            "numTotalTests": 1,
            "numPassedTests": 1,
            "numFailedTests": 0,
            "numPendingTests": 0,
            "numTodoTests": 0,
            "testResults": [
                {
                    "name": str(self.repo / "tests" / "native.test.tsx"),
                    "status": "passed",
                    "assertionResults": [
                        {
                            "ancestorTitles": ["", "Native component"],
                            "title": "renders state",
                            "status": "passed",
                        }
                    ],
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
            [sys.executable, "-c", command, "{reporter_file}"],
            kind="component",
        )
        plan.update(
            {
                "reporter_format": "jest-json",
                "selected": [
                    {
                        "path": "tests/native.test.tsx",
                        "title_path": ["Native component", "renders state"],
                    }
                ],
                "testware_ref": "fixture:jest-component",
                "testware_revision": self.sha,
                "runner_version": "jest-fixture",
                "selection_verified": True,
                "selection_evidence_ref": "fixture:selection",
                "planned_scope_ref": "fixture:scope",
            }
        )
        code, _, artifact = self.call(plan)
        self.assertEqual(code, 0)
        self.assertEqual(artifact["reporter_format"], "jest-json")
        self.assertTrue(artifact["collection_verified"])
        self.assertEqual(artifact["attempts"][0]["reconciliation"]["selected_count"], 1)
        self.assertIsNone(artifact["tc_verdict"])

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

    def test_missing_results_must_not_retry_even_with_clean_checkout(self):
        plan = self.plan([sys.executable, "-c", "raise SystemExit(1)"])
        plan["attempts"] = 2
        code, _, artifact = self.call(plan)
        self.assertEqual(code, 1)
        self.assertEqual(len(artifact["attempts"]), 1)
        self.assertEqual(artifact["attempts"][0]["return_code"], 1)
        self.assertEqual(
            artifact["attempts"][0]["result_collection"], "not_provided_by_adapter"
        )

    def test_event_case_report_requires_complete_selected_population(self):
        report = {
            "schema": "non-e2e-cases/v1",
            "source_revision": self.sha,
            "testware_revision": "fixture-event-revision",
            "runner_version": "adapter-fixture-1",
            "complete": True,
            "results": [
                {
                    "path": "tests/event.test.py",
                    "title_path": ["event", "processed"],
                    "status": "passed",
                    "attempt_results": [{"status": "passed", "retry": 0}],
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
            "config": {"version": "playwright-json-fixture"},
            "suites": [
                {
                    "title": "tests/contracts/api.spec.ts",
                    "specs": [
                        {
                            "file": "tests/contracts/api.spec.ts",
                            "title": "returns contract body",
                            "tests": [
                                {
                                    "projectName": "api",
                                    "expectedStatus": "passed",
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
        self.assertTrue(Path(artifact["attempts"][0]["raw_report_ref"]).is_file())
        self.assertTrue(artifact["collection_verified"])
        self.assertIsNone(artifact["tc_verdict"])

    def test_reporter_failure_with_exit_zero_is_not_verified(self):
        report = {
            "schema": "non-e2e-cases/v1",
            "source_revision": self.sha,
            "testware_revision": "v1",
            "runner_version": "adapter-fixture",
            "complete": True,
            "results": [
                {
                    "path": "tests/batch.py",
                    "title_path": ["batch"],
                    "status": "failed",
                    "attempt_results": [{"status": "failed", "retry": 0}],
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

    def test_malformed_reporters_still_run_cleanup_and_write_manifest(self):
        reports = [
            (
                "vitest",
                None,
                {
                    "success": True,
                    "testResults": [
                        {
                            "name": "tests/broken.test.ts",
                            "status": "passed",
                            "assertionResults": [
                                {
                                    "ancestorTitles": ["suite"],
                                    "title": "one",
                                    "status": [],
                                }
                            ],
                        }
                    ],
                },
                [{"path": "tests/broken.test.ts", "title_path": ["suite", "one"]}],
            ),
            (
                "playwright-api",
                "playwright-json",
                {
                    "config": {"version": "fixture-version"},
                    "errors": [],
                    "stats": {"expected": 1, "unexpected": 0, "flaky": 0, "skipped": 0},
                    "suites": [
                        {
                            "title": "tests/api.spec.ts",
                            "specs": [
                                {
                                    "file": "tests/api.spec.ts",
                                    "title": "one",
                                    "tests": [
                                        {
                                            "status": [],
                                            "expectedStatus": "passed",
                                            "results": [
                                                {"status": "passed", "retry": 0}
                                            ],
                                        }
                                    ],
                                }
                            ],
                        }
                    ],
                },
                [{"path": "tests/api.spec.ts", "title_path": ["one"]}],
            ),
            (
                "event",
                "case-json",
                {
                    "schema": "non-e2e-cases/v1",
                    "source_revision": self.sha,
                    "testware_revision": "fixture-revision",
                    "runner_version": "fixture-version",
                    "complete": True,
                    "results": [
                        {
                            "path": "tests/event.py",
                            "title_path": ["one"],
                            "status": [],
                            "attempt_results": [{"status": "passed", "retry": 0}],
                        }
                    ],
                },
                [{"path": "tests/event.py", "title_path": ["one"]}],
            ),
        ]
        for kind, reporter_format, report, selected in reports:
            with self.subTest(kind=kind):
                output = repr(json.dumps(report))
                if reporter_format == "playwright-json":
                    script = (
                        "import os,pathlib;"
                        "pathlib.Path(os.environ['PLAYWRIGHT_JSON_OUTPUT_FILE'])."
                        f"write_text({output},encoding='utf-8')"
                    )
                    argv = [sys.executable, "-c", script]
                else:
                    script = (
                        "import pathlib,sys;"
                        f"pathlib.Path(sys.argv[1]).write_text({output},encoding='utf-8')"
                    )
                    argv = [sys.executable, "-c", script, "{reporter_file}"]
                plan = self.plan(argv, kind=kind)
                plan.update(
                    {
                        "testware_ref": "fixture:testware",
                        "testware_revision": "fixture-revision",
                        "runner_version": "fixture-version",
                        "selected": selected,
                        "selection_verified": True,
                        "selection_evidence_ref": "fixture:selection",
                        "planned_scope_ref": "fixture:scope",
                    }
                )
                if reporter_format is not None:
                    plan["reporter_format"] = reporter_format
                cleanup = [sys.executable, "-c", "print('cleanup marker')"]
                plan["cleanup_argv"] = cleanup
                plan["reviewed_cleanup_argv"] = cleanup
                code, summary, artifact = self.call(plan)
                self.assertEqual(code, 1)
                self.assertEqual(summary["outcome"], "incomplete")
                attempt = artifact["attempts"][0]
                self.assertEqual(attempt["processing_error"], "TypeError")
                self.assertEqual(attempt["return_code"], 0)
                self.assertEqual(attempt["cleanup_state"], "success")
                self.assertIn(
                    "cleanup marker",
                    (
                        Path(artifact["artifact_directory"])
                        / "attempt-1"
                        / "cleanup.stdout.log"
                    ).read_text(encoding="utf-8"),
                )
                self.assertTrue(Path(attempt["raw_report_ref"]).is_file())
                self.assertFalse(artifact["collection_verified"])

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
        self.attach_direct_tc_authority(plan)
        code, _, artifact = self.call(plan)
        self.assertEqual(code, 1)
        self.assertEqual(artifact["outcome"], "observed_FAIL")
        self.assertIsNone(artifact["tc_verdict"])
        self.assertEqual(artifact["direct_observation_verdict"], "FAIL")
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
        self.attach_direct_tc_authority(plan)
        code, _, artifact = self.call(plan)
        self.assertEqual(code, 1)
        self.assertIsNone(artifact["tc_verdict"])
        self.assertEqual(artifact["direct_observation_verdict"], "FAIL")
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
        self.attach_direct_tc_authority(plan)
        code, _, artifact = self.call(plan)
        self.assertEqual(code, 1)
        self.assertIsNone(artifact["tc_verdict"])
        self.assertEqual(artifact["direct_observation_verdict"], "判定不能")
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
            "tool_ref": "fixture",
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
        wrong_tool = {**raw, "tool_ref": "unrelated-tool"}
        plan["argv"] = [
            sys.executable,
            "-c",
            "print(" + repr(json.dumps(wrong_tool)) + ")",
        ]
        plan["reviewed_argv"] = plan["argv"]
        code, _, artifact = self.call(plan)
        self.assertEqual(code, 1)
        self.assertEqual(artifact["outcome"], "incomplete")
        self.assertFalse(artifact["attempts"][0]["static_analysis"]["complete"])
        plan["argv"] = [sys.executable, "-c", "print('{}')"]
        plan["reviewed_argv"] = plan["argv"]
        code, _, artifact = self.call(plan)
        self.assertEqual(code, 1)
        self.assertEqual(artifact["outcome"], "incomplete")

    def test_direct_tc_requires_full_pinned_expectation_set(self):
        plan = self.plan([sys.executable, "-c", "print('{\\\"ok\\\": true}')"])
        plan["direct_tc"] = True
        plan["tc_ref"] = "TC-complete"
        plan["tc_revision"] = "accepted-revision"
        plan["expected_authority_ref"] = "accepted:reference"
        plan["direct_expectations"] = [
            {"id": "exit_code", "expected": 0},
            {"id": "stdout_json", "expected": {"ok": True}},
        ]
        self.attach_direct_tc_authority(plan)
        code, _, artifact = self.call(plan)
        self.assertEqual(code, 0)
        self.assertIsNone(artifact["tc_verdict"])
        self.assertEqual(artifact["direct_observation_verdict"], "PASS")
        self.assertEqual(artifact["outcome"], "runner_pass")
        source = artifact["direct_tc_authority_evidence"]
        self.assertEqual(source["authority_repo_revision"], self.sha)
        self.assertEqual(
            source["authority_review_status"], "not_authenticated_by_runner"
        )

        # Omitting even one actual expectation must stop before launching.
        plan["direct_expectations"] = [{"id": "exit_code", "expected": 0}]
        code, summary, artifact = self.call(plan)
        self.assertEqual(code, 2)
        self.assertEqual(
            summary["reason"], "direct_tc_expectations_incomplete_or_mismatched"
        )
        self.assertIsNone(artifact)

        # A nested boolean in the committed expected result is not the
        # JSON number 1, despite Python's True == 1 behavior.
        plan["direct_expectations"] = [
            {"id": "exit_code", "expected": 0},
            {"id": "stdout_json", "expected": {"ok": 1}},
        ]
        code, summary, artifact = self.call(plan)
        self.assertEqual(code, 2)
        self.assertEqual(
            summary["reason"], "direct_tc_expectations_incomplete_or_mismatched"
        )
        self.assertIsNone(artifact)

    def test_direct_tc_rejects_ambiguous_authority_snapshot_json(self):
        plan = self.plan([sys.executable, "-c", "print('should-not-run')"])
        plan["direct_tc"] = True
        plan["tc_ref"] = "TC-duplicate-authority"
        plan["tc_revision"] = "accepted"
        plan["expected_authority_ref"] = "accepted:reference"
        plan["direct_expectations"] = [{"id": "exit_code", "expected": 0}]
        self.attach_direct_tc_authority(plan)
        authority = self.repo / plan["direct_tc_authority_file"]
        raw = authority.read_text(encoding="utf-8")
        self.assertIn('"tc_revision": "accepted"', raw)
        authority.write_text(
            raw.replace(
                '"tc_revision": "accepted"',
                '"tc_revision": "stale", "tc_revision": "accepted"',
            ),
            encoding="utf-8",
        )
        git(self.repo, "add", plan["direct_tc_authority_file"])
        git(self.repo, "commit", "-qm", "duplicate Authority key fixture")
        self.sha = git(self.repo, "rev-parse", "HEAD")
        plan["repo_revision"] = self.sha
        plan["preflight"]["source_revision"] = self.sha
        plan["preflight"]["build_revision"] = self.sha
        code, summary, artifact = self.call(plan)
        self.assertEqual(code, 2)
        self.assertEqual(summary["reason"], "invalid_direct_tc_authority")
        self.assertIsNone(artifact)

    def test_direct_tc_rejects_untracked_authority_and_mismatched_revision(self):
        plan = self.plan([sys.executable, "-c", "pass"])
        plan["direct_tc"] = True
        plan["tc_ref"] = "TC-1"
        plan["tc_revision"] = "v1"
        plan["expected_authority_ref"] = "accepted:spec"
        plan["direct_expectations"] = [{"id": "exit_code", "expected": 0}]
        plan["direct_tc_authority_file"] = "tests/not-committed.json"
        code, summary, artifact = self.call(plan)
        self.assertEqual(code, 2)
        self.assertEqual(summary["reason"], "direct_tc_authority_not_tracked")
        self.assertIsNone(artifact)
        self.attach_direct_tc_authority(plan)
        plan["tc_revision"] = "v2"
        code, summary, artifact = self.call(plan)
        self.assertEqual(code, 2)
        self.assertEqual(summary["reason"], "direct_tc_authority_identity_mismatch")
        self.assertIsNone(artifact)

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
