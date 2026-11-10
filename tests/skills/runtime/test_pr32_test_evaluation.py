"""PR #32/J: QA-activity evaluation, improvement lifecycle and measurement contracts."""

from __future__ import annotations

import copy
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
HELPER = REPO_ROOT / "skills" / "test-evaluation" / "scripts" / "evaluation_runtime.py"
spec = importlib.util.spec_from_file_location("pr32_evaluation_runtime", HELPER)
assert spec is not None and spec.loader is not None
evaluation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(evaluation)

NOW = "2026-11-10T00:00:00+00:00"
CONDITIONS = {
    "scope_ref": "scope:checkout",
    "environment_ref": "env:stg",
    "population_ref": "pop:v1",
}


def metric(axis="quality", value=0.8, previous=0.6, **overrides):
    value_ = {
        "metric_id": f"M-{axis}",
        "axis": axis,
        "definition_version": "d1",
        "unit": "ratio",
        "numerator": 8,
        "denominator": 10,
        "value": value,
        "direction": "higher_is_better",
        "source_refs": [{"ref": "report:RPT-1", "revision": "r1"}],
        "conditions": dict(CONDITIONS),
        "previous": {
            "value": previous,
            "definition_version": "d1",
            "unit": "ratio",
            "conditions": dict(CONDITIONS),
        }
        if previous is not None
        else None,
    }
    value_.update(overrides)
    return value_


class MetricTests(unittest.TestCase):
    def test_comparable_metrics_are_improved_worsened_or_unchanged(self):
        self.assertEqual(evaluation.evaluate_metric(metric())["status"], "improved")
        self.assertEqual(
            evaluation.evaluate_metric(metric(value=0.5, numerator=5))["status"],
            "worsened",
        )
        self.assertEqual(
            evaluation.evaluate_metric(metric(value=0.6, numerator=6, previous=0.6))[
                "status"
            ],
            "unchanged",
        )
        lower = metric(
            axis="efficiency",
            value=3,
            numerator=None,
            denominator=None,
            direction="lower_is_better",
            previous=5,
        )
        self.assertEqual(evaluation.evaluate_metric(lower)["status"], "improved")

    def test_first_measurement_is_baseline_not_improvement(self):
        self.assertEqual(
            evaluation.evaluate_metric(metric(previous=None))["status"], "measured"
        )

    def test_condition_definition_or_unit_differences_are_not_comparable(self):
        other_env = metric()
        other_env["conditions"]["environment_ref"] = "env:prod"
        other_definition = metric()
        other_definition["definition_version"] = "d2"
        other_unit = metric()
        other_unit["previous"]["unit"] = "count"
        no_conditions = metric(conditions={})
        for name, item in {
            "env": other_env,
            "definition": other_definition,
            "unit": other_unit,
            "none": no_conditions,
        }.items():
            with self.subTest(name=name):
                self.assertEqual(
                    evaluation.evaluate_metric(item)["status"], "not_comparable"
                )

    def test_unmeasured_needs_reason_and_never_becomes_zero(self):
        item = metric(
            value=None,
            numerator=None,
            denominator=None,
            previous=None,
            unmeasured_reason="工数ログ未取得",
        )
        result = evaluation.evaluate_metric(item)
        self.assertEqual(result["status"], "unmeasured")
        self.assertNotIn("value", result)
        self.assertEqual(
            evaluation.evaluate_metric({**item, "unmeasured_reason": ""})["status"],
            "invalid",
        )
        zero_denominator = metric(
            numerator=0,
            denominator=0,
            value=0,
            previous=None,
            unmeasured_reason="分母0",
        )
        self.assertEqual(
            evaluation.evaluate_metric(zero_denominator)["status"], "unmeasured"
        )
        no_source = metric(source_refs=[], unmeasured_reason="source不明")
        self.assertEqual(evaluation.evaluate_metric(no_source)["status"], "unmeasured")

    def test_inconsistent_value_axis_and_direction_are_invalid(self):
        self.assertEqual(
            evaluation.evaluate_metric(metric(value=0.9))["status"], "invalid"
        )
        self.assertEqual(
            evaluation.evaluate_metric(metric(axis="speed"))["status"], "invalid"
        )
        self.assertEqual(
            evaluation.evaluate_metric(metric(direction=None))["status"], "invalid"
        )


class AxisAndClaimTests(unittest.TestCase):
    def test_no_composite_score_and_each_axis_is_reported(self):
        result = evaluation.evaluate_axes(
            [
                metric("quality"),
                metric(
                    "efficiency",
                    value=3,
                    numerator=None,
                    denominator=None,
                    direction="lower_is_better",
                    previous=5,
                ),
            ]
        )
        self.assertIsNone(result["composite_score"])
        self.assertEqual(set(result["axes"]), set(evaluation.AXES))
        self.assertEqual(result["axes"]["traceability"]["status"], "unmeasured")
        self.assertEqual(result["axes"]["quality"]["trend"], "improved")

    def test_time_reduction_alone_does_not_support_a_quality_claim(self):
        faster = metric(
            "efficiency",
            value=3,
            numerator=None,
            denominator=None,
            direction="lower_is_better",
            previous=5,
        )
        result = evaluation.evaluate_axes(
            [faster],
            claims=[
                {"axis": "efficiency", "assertion": "improved"},
                {"axis": "quality", "assertion": "improved"},
            ],
        )
        self.assertEqual(result["axes"]["quality"]["status"], "unmeasured")
        self.assertEqual([c["axis"] for c in result["rejected_claims"]], ["quality"])

    def test_improvement_claim_is_rejected_when_a_metric_on_the_axis_worsened(self):
        mixed = evaluation.evaluate_axes(
            [
                metric("quality"),
                {
                    **metric("quality", value=0.4, numerator=4, previous=0.6),
                    "metric_id": "M2",
                },
            ],
            claims=[{"axis": "quality", "assertion": "improved"}],
        )
        self.assertEqual(len(mixed["rejected_claims"]), 1)
        self.assertEqual(mixed["axes"]["quality"]["trend"], "worsened")

    def test_not_comparable_axis_has_no_trend_claim(self):
        other = metric()
        other["conditions"]["scope_ref"] = "scope:other"
        result = evaluation.evaluate_axes(
            [other], claims=[{"axis": "quality", "assertion": "improved"}]
        )
        self.assertEqual(result["axes"]["quality"]["trend"], "not_comparable")
        self.assertEqual(len(result["rejected_claims"]), 1)


def proposal(**overrides):
    value = {
        "improvement_ref": "IMP-1",
        "state": "proposed",
        "change_kind": "plan",
        "scope_ref": "scope:checkout",
        "proposal_revision": "prop-1",
        "baseline_activity_ref": "act:1",
    }
    value.update(overrides)
    return value


def adoption(**overrides):
    value = {
        "source": "trusted_approval_service",
        "authentication_verified": True,
        "authenticated_by": "idp:corp",
        "principal": "qa-manager",
        "role": "qa_manager",
        "policy_revision": "pol-1",
        "issued_at": "2026-11-09T00:00:00+00:00",
        "expires_at": "2026-11-11T00:00:00+00:00",
        "approval_ref": "appr:1",
        "operation": "adopt_improvement",
        "improvement_ref": "IMP-1",
        "artifact_revision": "prop-1",
        "scope_ref": "scope:checkout",
    }
    value.update(overrides)
    return value


def advance(improvement, event):
    result = evaluation.advance_improvement(improvement, event, NOW)
    return result


class ImprovementLifecycleTests(unittest.TestCase):
    def full_path(self):
        adopted = advance(proposal(), {"type": "adopt", "approval": adoption()})[
            "improvement"
        ]
        handed = advance(
            adopted,
            {
                "type": "handoff",
                "owner_skill": "test-management",
                "request_ref": "req:1",
                "base_revision": "plan-3",
            },
        )["improvement"]
        applied = advance(
            handed,
            {
                "type": "implement",
                "owner_result": {
                    "request_ref": "req:1",
                    "owner_skill": "test-management",
                    "status": "applied",
                    "new_revision": "plan-4",
                    "adoption_ref": "appr:1",
                },
            },
        )["improvement"]
        return adopted, handed, applied

    def test_full_path_to_a_measured_effect(self):
        _, _, applied = self.full_path()
        self.assertEqual(applied["state"], "implemented")
        measured = advance(
            applied,
            {
                "type": "measure",
                "activity": {
                    "activity_ref": "act:2",
                    "applied_revision": "plan-4",
                    "started_after_implementation": True,
                },
                "metric": metric(),
            },
        )
        self.assertEqual(measured["improvement"]["state"], "measured_effective")
        self.assertEqual(
            evaluation.summarize_improvements([measured["improvement"]])["achieved"], 1
        )

    def test_adoption_needs_trusted_bound_unexpired_approval(self):
        for name, approval in {
            "text": {"source": "pr_comment", "text": "LGTM"},
            "expired": adoption(expires_at="2026-11-09T12:00:00+00:00"),
            "other_revision": adoption(artifact_revision="prop-0"),
            "other_improvement": adoption(improvement_ref="IMP-2"),
            "unauthenticated": adoption(authentication_verified=False),
            "wrong_operation": adoption(operation="confirm_handoff"),
            "none": None,
        }.items():
            with self.subTest(name=name):
                result = advance(proposal(), {"type": "adopt", "approval": approval})
                self.assertEqual(result["status"], "blocked")
                self.assertEqual(result["improvement"]["state"], "proposed")

    def test_steps_cannot_be_skipped(self):
        adopted, handed, applied = self.full_path()
        for state, event in (
            (
                proposal(),
                {
                    "type": "handoff",
                    "owner_skill": "test-management",
                    "request_ref": "r",
                    "base_revision": "b",
                },
            ),
            (proposal(), {"type": "implement", "owner_result": {}}),
            (proposal(), {"type": "measure", "activity": {}, "metric": metric()}),
            (adopted, {"type": "implement", "owner_result": {}}),
            (handed, {"type": "measure", "activity": {}, "metric": metric()}),
        ):
            with self.subTest(state=state["state"], event=event["type"]):
                self.assertEqual(advance(state, event)["status"], "blocked")

    def test_handoff_must_go_to_the_owner_for_the_change_kind(self):
        adopted = advance(proposal(), {"type": "adopt", "approval": adoption()})[
            "improvement"
        ]
        wrong = advance(
            adopted,
            {
                "type": "handoff",
                "owner_skill": "test-architecture-design",
                "request_ref": "r",
                "base_revision": "b",
            },
        )
        self.assertIn("owner_does_not_match_change_kind", wrong["reasons"])
        design = advance(
            {**adopted, "change_kind": "design"},
            {
                "type": "handoff",
                "owner_skill": "test-case-design",
                "request_ref": "r",
                "base_revision": "b",
            },
        )
        self.assertEqual(design["status"], "advanced")

    def test_owner_must_record_a_new_revision_for_this_adoption(self):
        _, handed, _ = self.full_path()
        good = {
            "request_ref": "req:1",
            "owner_skill": "test-management",
            "status": "applied",
            "new_revision": "plan-4",
            "adoption_ref": "appr:1",
        }
        for name, overrides in {
            "same_revision": {"new_revision": "plan-3"},
            "not_applied": {"status": "submitted"},
            "other_request": {"request_ref": "req:9"},
            "other_adoption": {"adoption_ref": "appr:9"},
            "other_owner": {"owner_skill": "test-architecture-design"},
            "no_revision": {"new_revision": ""},
        }.items():
            with self.subTest(name=name):
                result = advance(
                    handed, {"type": "implement", "owner_result": {**good, **overrides}}
                )
                self.assertEqual(result["status"], "blocked")
                self.assertEqual(result["improvement"]["state"], "handed_off")

    def test_measurement_requires_a_later_activity_on_the_new_revision(self):
        _, _, applied = self.full_path()
        for name, activity in {
            "same_activity": {
                "activity_ref": "act:1",
                "applied_revision": "plan-4",
                "started_after_implementation": True,
            },
            "old_revision": {
                "activity_ref": "act:2",
                "applied_revision": "plan-3",
                "started_after_implementation": True,
            },
            "before_implementation": {
                "activity_ref": "act:2",
                "applied_revision": "plan-4",
                "started_after_implementation": False,
            },
        }.items():
            with self.subTest(name=name):
                self.assertEqual(
                    advance(
                        applied,
                        {"type": "measure", "activity": activity, "metric": metric()},
                    )["status"],
                    "blocked",
                )

    def test_measurement_outcomes_are_not_all_counted_as_achieved(self):
        _, _, applied = self.full_path()
        activity = {
            "activity_ref": "act:2",
            "applied_revision": "plan-4",
            "started_after_implementation": True,
        }
        other_env = metric()
        other_env["conditions"]["environment_ref"] = "env:prod"
        unmeasured = metric(
            value=None,
            numerator=None,
            denominator=None,
            previous=None,
            unmeasured_reason="未取得",
        )
        expected = {
            "measured_no_effect": metric(value=0.6, numerator=6, previous=0.6),
            "measured_worsened": metric(value=0.4, numerator=4, previous=0.6),
            "not_comparable": other_env,
            "not_measurable": unmeasured,
        }
        outcomes = []
        for state, item in expected.items():
            result = advance(
                applied, {"type": "measure", "activity": activity, "metric": item}
            )
            self.assertEqual(result["improvement"]["state"], state)
            outcomes.append(result["improvement"])
        summary = evaluation.summarize_improvements(
            outcomes + [proposal(improvement_ref="IMP-2"), applied]
        )
        self.assertEqual(summary["achieved"], 0)
        self.assertIn("IMP-2", summary["not_complete"])
        self.assertIn("IMP-1", summary["not_complete"])

    def test_knowledge_registration_is_not_an_implementation(self):
        adopted = advance(proposal(), {"type": "adopt", "approval": adoption()})[
            "improvement"
        ]
        result = advance(
            adopted, {"type": "knowledge_registered", "knowledge_ref": "KN-abc"}
        )
        self.assertEqual(result["status"], "recorded")
        self.assertEqual(result["improvement"]["state"], "adopted")
        self.assertEqual(
            evaluation.summarize_improvements([result["improvement"]])["achieved"], 0
        )

    def test_reject_is_only_possible_before_handoff_and_unknown_events_fail(self):
        self.assertEqual(
            advance(proposal(), {"type": "reject"})["improvement"]["state"], "rejected"
        )
        _, handed, _ = self.full_path()
        self.assertEqual(advance(handed, {"type": "reject"})["status"], "blocked")
        self.assertEqual(advance(proposal(), {"type": "complete"})["status"], "blocked")
        self.assertEqual(
            advance({"state": "done", "improvement_ref": "x"}, {"type": "adopt"})[
                "status"
            ],
            "blocked",
        )

    def test_events_do_not_mutate_the_input(self):
        item = proposal()
        before = copy.deepcopy(item)
        advance(item, {"type": "adopt", "approval": adoption()})
        self.assertEqual(item, before)


class InputsHandoffAndPropagationTests(unittest.TestCase):
    def test_changed_or_missing_source_is_stale_or_unverified(self):
        recorded = [
            {"ref": "report:1", "revision": "r1", "content_hash": "h1"},
            {"ref": "plan:1", "revision": "p1"},
        ]
        current = {
            "report:1": {"revision": "r1", "content_hash": "h1"},
            "plan:1": {"revision": "p1"},
        }
        self.assertEqual(
            evaluation.verify_inputs(recorded, current)["status"], "current"
        )
        changed = {
            **current,
            "report:1": {"revision": "r1", "content_hash": "tampered"},
        }
        self.assertEqual(
            evaluation.verify_inputs(recorded, changed)["stale_refs"], ["report:1"]
        )
        missing = {"report:1": current["report:1"]}
        self.assertEqual(
            evaluation.verify_inputs(recorded, missing)["unverified_refs"], ["plan:1"]
        )
        self.assertEqual(
            evaluation.verify_inputs([{"ref": "x"}], {})["status"],
            "stale_or_unverified",
        )

    def test_handoff_is_closed_only_with_authenticated_confirmation_for_each_item(self):
        confirmation = {
            "source": "trusted_approval_service",
            "authentication_verified": True,
            "authenticated_by": "idp",
            "principal": "owner",
            "role": "project_owner",
            "policy_revision": "p1",
            "issued_at": "2026-11-09T00:00:00+00:00",
            "expires_at": "2026-11-11T00:00:00+00:00",
            "operation": "confirm_handoff",
            "artifact_revision": "a1",
            "item_ref": "item:1",
        }
        item = {
            "item_ref": "item:1",
            "receiver": "ops",
            "artifact_revision": "a1",
            "confirmation": confirmation,
        }
        self.assertTrue(evaluation.handoff_status([item], NOW)["closed"])
        bad = {**item, "confirmation": {**confirmation, "item_ref": "item:2"}}
        self.assertFalse(evaluation.handoff_status([item, bad], NOW)["closed"])
        self.assertFalse(evaluation.handoff_status([], NOW)["closed"])
        self.assertFalse(
            evaluation.handoff_status([{**item, "confirmation": None}], NOW)["closed"]
        )

    def test_plan_change_propagates_only_to_dependents(self):
        depends_on = {
            "architecture": ["plan"],
            "risk": ["architecture"],
            "execution_prep": ["plan"],
            "unrelated_tc": ["spec"],
        }
        current = [
            "plan",
            "architecture",
            "risk",
            "execution_prep",
            "unrelated_tc",
            "spec",
        ]
        result = evaluation.propagate_change("plan", depends_on, current)
        self.assertEqual(
            result["revalidate"], ["architecture", "execution_prep", "risk"]
        )
        self.assertEqual(result["retained_current"], ["spec", "unrelated_tc"])
        cycle = evaluation.propagate_change("a", {"b": ["a"], "a": ["b"]}, ["a", "b"])
        self.assertEqual(cycle["revalidate"], ["b"])


class CliTests(unittest.TestCase):
    def run_cli(self, command, payload, helper=HELPER, cwd=None):
        return subprocess.run(
            [sys.executable, "-I", str(helper), command],
            input=payload if isinstance(payload, str) else json.dumps(payload),
            capture_output=True,
            text=True,
            cwd=cwd,
            check=False,
        )

    def test_cli_round_trip_isolated_copy_and_rejections(self):
        done = self.run_cli("evaluate-axes", {"metrics": [metric()]})
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIsNone(json.loads(done.stdout)["composite_score"])
        with tempfile.TemporaryDirectory() as temp:
            copied = Path(temp) / "test-evaluation"
            shutil.copytree(REPO_ROOT / "skills" / "test-evaluation", copied)
            result = self.run_cli(
                "evaluate-axes",
                {"metrics": [metric()]},
                helper=copied / "scripts" / "evaluation_runtime.py",
                cwd=temp,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
        for payload in ("[]", '{"a":1,"a":2}', "{bad", "{}"):
            with self.subTest(payload=payload):
                rejected = self.run_cli("evaluate-axes", payload)
                self.assertEqual(rejected.returncode, 2)
                self.assertEqual(json.loads(rejected.stdout)["status"], "blocked")
        self.assertEqual(self.run_cli("nope", {}).returncode, 2)


class Utf8StdinTests(unittest.TestCase):
    def test_raw_utf8_stdin_is_decoded_independently_of_the_locale(self):
        payload = json.dumps({"metrics": [metric()]}, ensure_ascii=False)
        completed = subprocess.run(
            [sys.executable, "-I", str(HELPER), "evaluate-axes"],
            input=payload.encode("utf-8"),
            capture_output=True,
            check=False,
            env={
                "PYTHONIOENCODING": "cp932",
                "SYSTEMROOT": __import__("os").environ.get("SYSTEMROOT", ""),
            },
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        completed = subprocess.run(
            [sys.executable, "-I", str(HELPER), "evaluate-axes"],
            input=b"\xff\xfe{}",
            capture_output=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 2)


if __name__ == "__main__":
    unittest.main()
