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
    baseline = group == "baseline"
    calls = 10 if baseline else 5
    elapsed = 100 if baseline else 70
    values = {key: metric(calls) for key in mod.COUNT_METRICS}
    values["wall_seconds"] = metric(elapsed, "seconds")
    values["human_review_seconds"] = metric(30 if baseline else 20, "seconds")
    values["human_approval_seconds"] = metric(5, "seconds")
    values["cost_amount"] = metric(120 if baseline else 100, "JPY")
    values["reused_artifact_count"] = metric(2 if baseline else 4)
    values["retry_count"] = metric(1 if baseline else 0)
    values["skill_restart_count"] = metric(2 if baseline else 1)
    started = datetime(2026, 11, 8, 9, 0, tzinfo=timezone.utc)
    finished = started + timedelta(seconds=elapsed)
    skill_runs = [
        {
            "skill": "test-analysis",
            "run_ref": f"skill-{scenario}-{group}-{index}-{n}",
            "started_at": started.isoformat(),
            "finished_at": finished.isoformat(),
        }
        for n in range(calls)
    ]
    attempts = [
        f"attempt-{scenario}-{group}-{index}-{n}"
        for n in range(2 if baseline else 1)
    ]
    return {
        "trial_ref": f"{scenario}-{group}-{index}",
        "run_ref": f"run-{scenario}-{group}-{index}",
        "product_commit": ("2" if scenario == "local_code_change" else "1") * 40,
        "source_revisions": [
            {
                "ref": "spec",
                "revision": "rev-2" if scenario == "external_spec_revision" else "rev-1",
            }
        ],
        "scope_refs": ["SCOPE-001"],
        "qa_goal_ref": f"goal-{scenario}",
        "expectation_ref": f"expect-{scenario}",
        "test_set_ref": f"tests-{scenario}",
        "environment_ref": "env-1",
        "agent_config_ref": "agent-config-before" if baseline else "agent-config-after",
        "execution_evidence": {
            "started_at": started.isoformat(),
            "finished_at": finished.isoformat(),
            "skill_runs": skill_runs,
            "owner_artifacts": [
                {
                    "owner": "test-analysis",
                    "artifact_ref": f"analysis-{scenario}",
                    "revision": "rev-1",
                }
            ],
            "attempt_refs": attempts,
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
            item["metrics"]["human_review_seconds"] = metric(
                baseline_values[index], "seconds"
            )
        for index, item in enumerate(data["scenarios"][0]["candidate"]):
            item["metrics"]["human_review_seconds"] = metric(
                candidate_values[index], "seconds"
            )
        result = mod.evaluate(data)
        first = result["scenarios"][0]
        self.assertEqual(first["metrics"]["human_review_seconds"]["baseline"]["median"], 15)
        self.assertEqual(
            first["metrics"]["human_review_seconds"]["candidate"]["median"], 35
        )
        self.assertEqual(first["metrics"]["human_review_seconds"]["change"], "regressed")
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

    def test_invalid_units_cannot_bypass_time_or_charge_validation(self) -> None:
        for key, unit in [
            ("wall_seconds", "count"),
            ("human_review_seconds", "count"),
            ("human_approval_seconds", "count"),
            ("skill_call_count", "seconds"),
            ("cost_amount", "count"),
        ]:
            with self.subTest(key=key, unit=unit):
                data = dataset()
                data["scenarios"][0]["candidate"][0]["metrics"][key]["unit"] = unit
                with self.assertRaises(ValueError):
                    mod.evaluate(data)

    def test_skill_run_and_attempt_counts_must_match_recorded_evidence(self) -> None:
        for metric_key in ("skill_call_count", "retry_count"):
            with self.subTest(metric=metric_key):
                data = dataset()
                data["scenarios"][0]["candidate"][0]["metrics"][metric_key] = metric(2)
                with self.assertRaises(ValueError):
                    mod.evaluate(data)

    def test_fractional_count_is_rejected(self) -> None:
        data = dataset()
        data["scenarios"][0]["candidate"][0]["metrics"]["request_count"] = metric(1.5)
        with self.assertRaises(ValueError):
            mod.evaluate(data)

    def test_scenario_specific_revisions_and_expected_inputs_are_independent(self) -> None:
        data = dataset()
        by_name = {item["scenario"]: item for item in data["scenarios"]}
        unchanged = by_name["unchanged_request"]["baseline"][0]
        code = by_name["local_code_change"]["baseline"][0]
        spec = by_name["external_spec_revision"]["baseline"][0]
        self.assertNotEqual(unchanged["product_commit"], code["product_commit"])
        self.assertEqual(unchanged["product_commit"], spec["product_commit"])
        self.assertNotEqual(
            unchanged["source_revisions"], spec["source_revisions"]
        )
        self.assertNotEqual(unchanged["qa_goal_ref"], code["qa_goal_ref"])
        self.assertEqual(mod.evaluate(data)["status"], "efficiency_evidenced")

    def test_scenario_specific_drift_is_not_comparable(self) -> None:
        data = dataset()
        data["scenarios"][2]["candidate"][0]["product_commit"] = "f" * 40
        data["scenarios"][3]["candidate"][0]["source_revisions"][0]["revision"] = "rev-3"
        result = mod.evaluate(data)
        self.assertEqual(result["scenarios"][2]["status"], "not_comparable")
        self.assertEqual(result["scenarios"][3]["status"], "not_comparable")
        self.assertEqual(result["status"], "unproven")

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

    def test_missing_cost_currency_when_measured_is_rejected(self) -> None:
        data = dataset()
        data["scenarios"][0]["candidate"][0]["metrics"]["cost_amount"] = metric(
            100, "unknown"
        )
        with self.assertRaises(ValueError):
            mod.evaluate(data)

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
            "rev-3"
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
            item["metrics"]["human_review_seconds"] = metric(120, "seconds")
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
                capture_output=True,
                text=True,
                check=False,
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "efficiency_evidenced")

    def test_cli_oversized_numeric_value_is_structurally_blocked(self) -> None:
        data = dataset()
        data["scenarios"][0]["candidate"][0]["metrics"]["token_count"] = metric(10**400)
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "huge-int.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--input", str(path)],
                capture_output=True,
                text=True,
                check=False,
            )
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "blocked")

    def test_cli_invalid_unicode_in_duplicate_key_returns_json_error(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "invalid-unicode.json"
            path.write_text(
                '{"\\ud800": 1, "\\ud800": 2}', encoding="utf-8"
            )
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--input", str(path)],
                capture_output=True,
                text=True,
                check=False,
            )
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "blocked")
        self.assertNotIn("Traceback", result.stderr)

    def test_cli_deeply_nested_json_returns_blocked_without_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "nested.json"
            path.write_bytes(b"[" * 1100 + b"0" + b"]" * 1100)
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--input", str(path)],
                capture_output=True,
                text=True,
                check=False,
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
