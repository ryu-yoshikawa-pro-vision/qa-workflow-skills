"""Independent subprocess fixtures for the non-E2E runner's actual execution path."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
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
        code, summary, artifact = self.call(plan)
        self.assertEqual(code, 0)
        self.assertEqual(summary["outcome"], "runner_pass")
        self.assertEqual(artifact["source_revision"], self.sha)
        attempt = artifact["attempts"][0]
        self.assertTrue(attempt["started"])
        self.assertIsInstance(attempt["pid"], int)
        self.assertEqual(attempt["return_code"], 0)
        self.assertIn("runner observation", Path(attempt["stdout_ref"]).read_text())
        self.assertIsNone(artifact["tc_verdict"])

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
        plan["selection_verified"] = True
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
        plan["selection_verified"] = True
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

    def test_direct_batch_exit_zero_with_wrong_body_is_fail(self):
        plan = self.plan([sys.executable, "-c", "print('{\"ok\": false}')"])
        plan["direct_expectations"] = [
            {"id": "exit_code", "expected": 0},
            {"id": "stdout_json", "expected": {"ok": True}},
        ]
        code, _, artifact = self.call(plan)
        self.assertEqual(code, 1)
        self.assertEqual(artifact["outcome"], "observed_FAIL")
        self.assertEqual(artifact["tc_verdict"], "FAIL")
        self.assertEqual(artifact["attempts"][0]["return_code"], 0)

    def test_direct_missing_side_effect_observation_is_unknown(self):
        plan = self.plan([sys.executable, "-c", "print('{\"ok\": true}')"])
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


if __name__ == "__main__":
    unittest.main()
