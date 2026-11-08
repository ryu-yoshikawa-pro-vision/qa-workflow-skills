from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts" / "skills" / "evals" / "workflow_efficiency.py"
SPEC = importlib.util.spec_from_file_location("workflow_efficiency", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


def metric(value: float | None, unit: str = "count") -> dict:
    return {
        "value": value,
        "unit": unit,
        "source_ref": "log-run-1" if value is not None else None,
        "unmeasured_reason": None if value is not None else "provider_did_not_report",
    }


def trial(scenario: str, group: str, index: int) -> dict:
    values = {key: metric(10 if group == "baseline" else 5) for key in mod.METRICS}
    values["reused_artifact_count"] = metric(2 if group == "baseline" else 4)
    elapsed = 100 if group == "baseline" else 70
    values["wall_seconds"] = metric(elapsed, "seconds")
    started = datetime(2026, 11, 8, 9, 0, tzinfo=timezone.utc)
    finished = started + timedelta(seconds=elapsed)
    return {
        "trial_ref": f"{scenario}-{group}-{index}",
        "run_ref": f"run-{scenario}-{group}-{index}",
        "product_commit": "1" * 40,
        "source_revisions": [{"ref": "spec", "revision": "rev-1"}],
        "scope_refs": ["SCOPE-001"],
        "qa_goal_ref": "goal-1",
        "expectation_ref": "expect-1",
        "test_set_ref": "tests-1",
        "environment_ref": "env-1",
        "agent_config_ref": "agent-config-1",
        "execution_evidence": {
            "started_at": started.isoformat(),
            "finished_at": finished.isoformat(),
            "skill_runs": [
                {
                    "skill": "test-analysis",
                    "run_ref": f"skill-{scenario}-{group}-{index}",
                    "started_at": started.isoformat(),
                    "finished_at": finished.isoformat(),
                }
            ],
            "owner_artifacts": [
                {
                    "owner": "test-analysis",
                    "artifact_ref": "analysis-1",
                    "revision": "rev-1",
                }
            ],
            "attempt_refs": [f"attempt-{scenario}-{group}-{index}"],
            "runner_refs": [],
            "cleanup_refs": [],
            "interruption_ref": f"resume-{scenario}-{group}-{index}"
            if scenario == "interrupted_resume"
            else None,
        },
        "quality": {
            "functional": "pass",
            "quality": "pass",
            "safety": "pass",
            "traceability": "pass",
            "independent_evidence_ref": f"judge-{scenario}-{group}-{index}",
        },
        "metrics": values,
    }


def dataset() -> dict:
    return {
        "schema_version": mod.SCHEMA,
        "scenarios": [
            {
                "scenario": name,
                "baseline": [trial(name, "baseline", i) for i in range(2)],
                "candidate": [trial(name, "candidate", i) for i in range(2)],
            }
            for name in mod.SCENARIOS
        ],
    }


class WorkflowEfficiencyTests(unittest.TestCase):
    def test_all_five_comparable_scenarios(self) -> None:
        result = mod.evaluate(dataset())
        self.assertEqual(result["status"], "efficiency_evidenced")
        first = result["scenarios"][0]
        self.assertEqual(first["metrics"]["wall_seconds"]["baseline"]["median"], 100)
        self.assertEqual(first["metrics"]["wall_seconds"]["candidate"]["median"], 70)

    def test_direction_uses_independent_median_values(self) -> None:
        data = dataset()
        baseline_values = (10, 20)
        candidate_values = (30, 40)
        for index, item in enumerate(data["scenarios"][0]["baseline"]):
            item["metrics"]["skill_call_count"] = metric(baseline_values[index])
        for index, item in enumerate(data["scenarios"][0]["candidate"]):
            item["metrics"]["skill_call_count"] = metric(candidate_values[index])
        result = mod.evaluate(data)
        first = result["scenarios"][0]
        self.assertEqual(first["metrics"]["skill_call_count"]["baseline"]["median"], 15)
        self.assertEqual(first["metrics"]["skill_call_count"]["candidate"]["median"], 35)
        self.assertEqual(first["metrics"]["skill_call_count"]["change"], "regressed")
        self.assertEqual(first["status"], "needs_review")
        self.assertEqual(result["status"], "unproven")

    def test_huge_finite_equal_values_do_not_generate_infinity(self) -> None:
        data = dataset()
        for item in (
            data["scenarios"][0]["baseline"] + data["scenarios"][0]["candidate"]
        ):
            item["metrics"]["token_count"] = metric(1e308)
        result = mod.evaluate(data)
        first = result["scenarios"][0]["metrics"]["token_count"]
        self.assertEqual(first["baseline"]["median"], 1e308)
        self.assertEqual(first["candidate"]["median"], 1e308)
        self.assertEqual(first["change"], "unchanged")
        self.assertNotIn("Infinity", json.dumps(result, allow_nan=False))

    def test_missing_execution_evidence_is_not_efficiency_proof(self) -> None:
        data = dataset()
        del data["scenarios"][0]["candidate"][0]["execution_evidence"]
        result = mod.evaluate(data)
        self.assertEqual(result["status"], "unproven")
        self.assertIn("execution_evidence_missing", result["scenarios"][0]["reasons"])

    def test_missing_interruption_reference_blocks_resume_comparison(self) -> None:
        data = dataset()
        data["scenarios"][4]["candidate"][0]["execution_evidence"][
            "interruption_ref"
        ] = None
        result = mod.evaluate(data)
        self.assertIn(
            "interruption_evidence_missing", result["scenarios"][4]["reasons"]
        )

    def test_wall_time_mismatch_cannot_claim_measured_improvement(self) -> None:
        data = dataset()
        data["scenarios"][0]["candidate"][0]["execution_evidence"]["finished_at"] = (
            "2026-11-08T09:02:00+00:00"
        )
        data["scenarios"][0]["candidate"][0]["execution_evidence"]["skill_runs"][0][
            "finished_at"
        ] = "2026-11-08T09:02:00+00:00"
        with self.assertRaises(ValueError):
            mod.evaluate(data)

    def test_invalid_or_missing_owner_evidence_rejected(self) -> None:
        data = dataset()
        data["scenarios"][0]["candidate"][0]["execution_evidence"][
            "owner_artifacts"
        ] = []
        with self.assertRaises(ValueError):
            mod.evaluate(data)

    def test_timezone_is_required_for_logged_intervals(self) -> None:
        data = dataset()
        data["scenarios"][0]["candidate"][0]["execution_evidence"]["started_at"] = (
            "2026-11-08T09:00:00"
        )
        with self.assertRaises(ValueError):
            mod.evaluate(data)

    def test_same_skill_execution_cannot_count_as_independent_trials(self) -> None:
        data = dataset()
        data["scenarios"][0]["candidate"][0]["execution_evidence"]["skill_runs"][0][
            "run_ref"
        ] = data["scenarios"][0]["baseline"][0]["execution_evidence"]["skill_runs"][0][
            "run_ref"
        ]
        with self.assertRaises(ValueError):
            mod.evaluate(data)

    def test_unmeasured_is_not_zero(self) -> None:
        data = dataset()
        for item in data["scenarios"][0]["candidate"]:
            item["metrics"]["wall_seconds"] = metric(None, "seconds")
        result = mod.evaluate(data)
        self.assertEqual(
            result["scenarios"][0]["metrics"]["wall_seconds"]["change"],
            "not_comparable",
        )
        self.assertEqual(
            result["scenarios"][0]["metrics"]["wall_seconds"]["candidate"]["status"],
            "not_measured",
        )

    def test_missing_required_metric_prevents_efficiency_claim(self) -> None:
        data = dataset()
        for item in data["scenarios"][0]["candidate"]:
            item["metrics"]["wall_seconds"] = metric(None, "seconds")
        result = mod.evaluate(data)
        self.assertEqual(result["status"], "unproven")
        self.assertIn(
            "required_measurement_unavailable",
            result["scenarios"][0]["reasons"],
        )

    def test_mismatched_metric_units_prevent_comparison(self) -> None:
        data = dataset()
        for item in data["scenarios"][0]["candidate"]:
            item["metrics"]["human_review_seconds"] = metric(3, "seconds")
        result = mod.evaluate(data)
        self.assertIn(
            "required_measurement_unavailable", result["scenarios"][0]["reasons"]
        )

    def test_quality_failure_disallows_efficiency_pass(self) -> None:
        data = dataset()
        data["scenarios"][1]["candidate"][0]["quality"]["safety"] = "fail"
        result = mod.evaluate(data)
        self.assertEqual(result["status"], "unproven")
        self.assertIn(
            "independent_quality_or_safety_not_passed",
            result["scenarios"][1]["reasons"],
        )

    def test_source_revision_drift_is_not_comparable(self) -> None:
        data = dataset()
        data["scenarios"][3]["candidate"][0]["source_revisions"][0]["revision"] = (
            "rev-2"
        )
        result = mod.evaluate(data)
        self.assertEqual(result["scenarios"][3]["status"], "not_comparable")

    def test_single_trial_is_insufficient(self) -> None:
        data = dataset()
        data["scenarios"][4]["candidate"].pop()
        result = mod.evaluate(data)
        self.assertIn(
            "independent_repeated_trials_missing", result["scenarios"][4]["reasons"]
        )

    def test_regression_visible_even_when_other_metrics_improve(self) -> None:
        data = dataset()
        for item in data["scenarios"][2]["candidate"]:
            item["metrics"]["human_review_seconds"] = metric(30)
        result = mod.evaluate(data)
        self.assertEqual(result["scenarios"][2]["status"], "needs_review")
        self.assertEqual(
            result["scenarios"][2]["metrics"]["human_review_seconds"]["change"],
            "regressed",
        )

    def test_missing_baseline_is_not_improvement(self) -> None:
        data = dataset()
        data["scenarios"][0]["baseline"] = []
        result = mod.evaluate(data)
        self.assertEqual(result["scenarios"][0]["status"], "not_comparable")

    def test_unmeasured_requires_reason(self) -> None:
        data = dataset()
        data["scenarios"][0]["candidate"][0]["metrics"]["wall_seconds"] = {
            "value": None,
            "unit": "seconds",
            "source_ref": None,
            "unmeasured_reason": None,
        }
        with self.assertRaises(ValueError):
            mod.evaluate(data)

    def test_duplicate_run_identity_is_rejected(self) -> None:
        data = dataset()
        data["scenarios"][0]["candidate"][0]["trial_ref"] = data["scenarios"][0][
            "baseline"
        ][0]["trial_ref"]
        with self.assertRaises(ValueError):
            mod.evaluate(data)

    def test_distinct_trial_refs_cannot_alias_same_owner_run(self) -> None:
        data = dataset()
        data["scenarios"][0]["candidate"][0]["run_ref"] = data["scenarios"][0][
            "baseline"
        ][0]["run_ref"]
        with self.assertRaises(ValueError):
            mod.evaluate(data)

    def test_cli_success_exit_code_and_report_are_consistent(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "success.json"
            path.write_text(json.dumps(dataset()), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--input", str(path)],
                capture_output=True, text=True, check=False,
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "efficiency_evidenced")

    def test_cli_oversized_numeric_value_is_structurally_blocked(self) -> None:
        data = dataset()
        data["scenarios"][0]["candidate"][0]["metrics"]["token_count"] = metric(
            10**400
        )
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "huge-int.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--input", str(path)],
                capture_output=True, text=True, check=False,
            )
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "blocked")

    def test_cli_deeply_nested_json_returns_blocked_without_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "nested.json"
            path.write_bytes(b"[" * 1100 + b"0" + b"]" * 1100)
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--input", str(path)],
                capture_output=True, text=True, check=False,
            )
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "blocked")

    def test_cli_rejects_duplicate_json_properties(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "duplicate.json"
            data = json.dumps(dataset())
            data = data.replace(
                '"schema_version": "qa-workflow-efficiency-v1"',
                '"schema_version": "qa-workflow-efficiency-v1", '
                '"schema_version": "qa-workflow-efficiency-v1"',
                1,
            )
            path.write_text(data, encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--input", str(path)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertEqual(json.loads(result.stdout)["status"], "blocked")

    def test_cli_limits_raw_json_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "huge.json"
            path.write_bytes(b" " * (2 * 1024 * 1024 + 1))
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--input", str(path)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 2, result.stderr)

    def test_missing_scenario_is_rejected(self) -> None:
        data = dataset()
        data["scenarios"].pop()
        with self.assertRaises(ValueError):
            mod.evaluate(data)


if __name__ == "__main__":
    unittest.main()
