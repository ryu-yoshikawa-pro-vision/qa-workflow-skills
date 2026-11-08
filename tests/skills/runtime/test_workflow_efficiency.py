from __future__ import annotations

import importlib.util
import unittest
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
    values["wall_seconds"] = metric(100 if group == "baseline" else 70, "seconds")
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
        data["scenarios"][3]["candidate"][0]["source_revisions"][0]["revision"] = "rev-2"
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
            item["metrics"]["human_review_seconds"] = metric(30, "seconds")
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

    def test_missing_scenario_is_rejected(self) -> None:
        data = dataset()
        data["scenarios"].pop()
        with self.assertRaises(ValueError):
            mod.evaluate(data)


if __name__ == "__main__":
    unittest.main()
