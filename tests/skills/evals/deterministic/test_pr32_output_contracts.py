"""PR #32/J: deterministic output contracts for the three new QA-activity Skills."""

from __future__ import annotations

import copy
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from scripts.skills.evals.deterministic.run import grade  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[4]
SKILLS = {
    "defect-management": "DEF",
    "test-reporting": "RPT",
    "test-evaluation": "EVL",
}


def case_dir(skill: str, case_id: str) -> Path:
    return REPO_ROOT / "skills" / skill / "evals" / "output" / "cases" / case_id.lower()


def load_artifact(skill: str, case_id: str) -> dict:
    text = (case_dir(skill, case_id) / "output.md").read_text(encoding="utf-8")
    return json.loads(re.search(r"```json\n(.*)\n```", text, re.DOTALL).group(1))


def grade_artifact(skill: str, case_id: str, artifact) -> dict:
    expected_path = case_dir(skill, case_id) / "expected.json"
    with tempfile.TemporaryDirectory() as temp:
        output = Path(temp) / "output.md"
        text = (
            artifact
            if isinstance(artifact, str)
            else "```json\n"
            + json.dumps(artifact, ensure_ascii=False, indent=2)
            + "\n```\n"
        )
        output.write_text(text, encoding="utf-8")
        eval_dir = REPO_ROOT / "skills" / skill / "evals" / "output"
        manifest = json.loads((eval_dir / "evals.json").read_text(encoding="utf-8"))
        assert any(c["id"] == case_id for c in manifest["cases"]), case_id
        assert expected_path.is_file()
        return grade(skill, case_id, output)


def failed(result: dict) -> set[str]:
    return {a["id"] for a in result["assertions"] if a["status"] == "fail"}


class ManifestTests(unittest.TestCase):
    def test_every_case_passes_the_repository_runner(self):
        total = 0
        for skill, prefix in SKILLS.items():
            manifest = json.loads(
                (
                    REPO_ROOT / "skills" / skill / "evals" / "output" / "evals.json"
                ).read_text(encoding="utf-8")
            )
            self.assertEqual(manifest["skill"], skill)
            for case in manifest["cases"]:
                with self.subTest(case=case["id"]):
                    self.assertTrue(case["id"].startswith(f"{prefix}-OUT-"))
                    output = case_dir(skill, case["id"]) / "output.md"
                    result = grade(skill, case["id"], output)
                    self.assertEqual(
                        result["status"], "pass", json.dumps(result, ensure_ascii=False)
                    )
                    total += 1
        self.assertEqual(total, 22)

    def test_inputs_reference_the_canonical_template(self):
        for skill in SKILLS:
            manifest = json.loads(
                (
                    REPO_ROOT / "skills" / skill / "evals" / "output" / "evals.json"
                ).read_text(encoding="utf-8")
            )
            for case in manifest["cases"]:
                text = (case_dir(skill, case["id"]) / "input.md").read_text(
                    encoding="utf-8"
                )
                self.assertIn("output-template.md", text)


class DefectManagementValidatorTests(unittest.TestCase):
    skill = "defect-management"

    def test_non_json_and_unknown_artifact_types_fail(self):
        self.assertEqual(
            failed(grade_artifact(self.skill, "DEF-OUT-001", "no json")), {"DEF-D001"}
        )
        bad = load_artifact(self.skill, "DEF-OUT-001")
        bad["artifact_type"] = "defect"
        self.assertIn(
            "DEF-D002", failed(grade_artifact(self.skill, "DEF-OUT-001", bad))
        )

    def test_hypothesis_cause_cannot_be_ready_for_handoff(self):
        artifact = load_artifact(self.skill, "DEF-OUT-001")
        artifact["candidate"]["candidate_state"] = "ready_for_external_handoff"
        artifact["candidate"]["status"] = "ready"
        self.assertIn(
            "DEF-D003", failed(grade_artifact(self.skill, "DEF-OUT-001", artifact))
        )

    def test_candidate_must_not_be_auto_registered_and_must_name_the_return_owner(self):
        artifact = load_artifact(self.skill, "DEF-OUT-001")
        artifact["candidate"]["automatic_registration"] = True
        self.assertIn(
            "DEF-D004", failed(grade_artifact(self.skill, "DEF-OUT-001", artifact))
        )
        artifact = load_artifact(self.skill, "DEF-OUT-001")
        artifact["candidate"]["return_to"] = {"owner": "someone-else"}
        self.assertIn(
            "DEF-D005", failed(grade_artifact(self.skill, "DEF-OUT-001", artifact))
        )

    def test_allow_requires_trusted_bound_unexpired_approval_and_write_permission(self):
        for name, mutate in {
            "text_approval": lambda a: a["context"]["approval"].update(
                source="issue_body"
            ),
            "unauthenticated": lambda a: a["context"]["approval"].update(
                authentication_verified=False
            ),
            "binding": lambda a: a["context"]["approval"].update(binding_matches=False),
            "expired": lambda a: a["context"]["approval"].update(
                expires_at="2026-11-09T12:00:00+00:00"
            ),
            "no_write_permission": lambda a: a["context"].update(
                write_permission=False
            ),
            "immature_candidate": lambda a: a["context"].update(
                candidate_state="needs_owner_analysis"
            ),
            "no_readback_requirement": lambda a: a["plan"].update(
                requires_readback=False
            ),
        }.items():
            with self.subTest(name=name):
                artifact = load_artifact(self.skill, "DEF-OUT-002")
                mutate(artifact)
                self.assertIn(
                    "DEF-D007",
                    failed(grade_artifact(self.skill, "DEF-OUT-002", artifact)),
                )

    def test_create_requires_no_duplicate_and_atomic_dedupe_or_no_auto_retry(self):
        artifact = load_artifact(self.skill, "DEF-OUT-002")
        artifact["context"]["duplicate_check"] = "human_confirmation_required"
        self.assertIn(
            "DEF-D008", failed(grade_artifact(self.skill, "DEF-OUT-002", artifact))
        )
        artifact = load_artifact(self.skill, "DEF-OUT-002")
        artifact["context"]["atomic_dedupe"] = False
        artifact["plan"]["auto_retry_allowed"] = True
        self.assertIn(
            "DEF-D010", failed(grade_artifact(self.skill, "DEF-OUT-002", artifact))
        )

    def test_close_without_verified_fix_on_the_fix_target_is_rejected(self):
        for name, fix in {
            "notice_only": {"status": "issue_marked_resolved"},
            "old_build": {
                "status": "fix_confirmed",
                "verified_target_ref": "build:41",
                "result_finalized": True,
                "cleanup_status": "成功",
            },
            "cleanup": {
                "status": "fix_confirmed",
                "verified_target_ref": "build:42",
                "result_finalized": True,
                "cleanup_status": "未確認",
            },
        }.items():
            with self.subTest(name=name):
                artifact = load_artifact(self.skill, "DEF-OUT-003")
                artifact["plan"]["decision"] = "allow"
                artifact["plan"]["requires_readback"] = True
                artifact["plan"]["operation"] = "close"
                artifact["context"]["fix_verification"] = fix
                self.assertIn(
                    "DEF-D009",
                    failed(grade_artifact(self.skill, "DEF-OUT-003", artifact)),
                )

    def test_external_success_needs_readback_and_an_allowed_plan(self):
        artifact = load_artifact(self.skill, "DEF-OUT-002")
        artifact["outcome"]["readback_verified"] = False
        self.assertIn(
            "DEF-D011", failed(grade_artifact(self.skill, "DEF-OUT-002", artifact))
        )
        artifact = load_artifact(self.skill, "DEF-OUT-003")
        artifact["outcome"] = {
            "status": "applied",
            "external_update_performed": True,
            "readback_verified": True,
        }
        self.assertIn(
            "DEF-D011", failed(grade_artifact(self.skill, "DEF-OUT-003", artifact))
        )

    def test_fix_verification_request_and_result_contracts(self):
        for name, mutate, assertion in (
            (
                "same_target",
                lambda a: a["request"].update(
                    fix_target_ref=a["request"]["observed_target_ref"]
                ),
                "DEF-D012",
            ),
            (
                "wrong_owner",
                lambda a: a["request"].update(send_to="test-execution"),
                "DEF-D012",
            ),
            (
                "notice_is_confirmation",
                lambda a: a["request"].update(notice_is_confirmation=True),
                "DEF-D012",
            ),
            ("no_changes", lambda a: a["request"].update(change_refs=[]), "DEF-D012"),
            (
                "old_build_result",
                lambda a: a["result"].update(target_ref="build:41"),
                "DEF-D013",
            ),
            (
                "cleanup_unknown",
                lambda a: a["result"].update(cleanup_status="未確認"),
                "DEF-D013",
            ),
            (
                "not_started",
                lambda a: a["result"].update(actual_start_confirmed=False),
                "DEF-D013",
            ),
        ):
            with self.subTest(name=name):
                artifact = load_artifact(self.skill, "DEF-OUT-004")
                mutate(artifact)
                self.assertIn(
                    assertion,
                    failed(grade_artifact(self.skill, "DEF-OUT-004", artifact)),
                )

    def test_tracking_closure_is_derived_and_secrets_are_rejected(self):
        artifact = load_artifact(self.skill, "DEF-OUT-005")
        artifact["record"]["fix_verification"] = {"status": "pending"}
        self.assertIn(
            "DEF-D014", failed(grade_artifact(self.skill, "DEF-OUT-005", artifact))
        )
        artifact = load_artifact(self.skill, "DEF-OUT-001")
        artifact["candidate"]["reasons"].append("token: abcd1234efgh5678")
        self.assertIn(
            "DEF-D015", failed(grade_artifact(self.skill, "DEF-OUT-001", artifact))
        )

    def test_independent_expectation_catches_a_wrong_decision(self):
        artifact = load_artifact(self.skill, "DEF-OUT-003")
        artifact["plan"]["decision"] = "reconfirm"
        self.assertIn(
            "DEF-D016", failed(grade_artifact(self.skill, "DEF-OUT-003", artifact))
        )


class TestReportingValidatorTests(unittest.TestCase):
    skill = "test-reporting"

    def mutated(self, case_id, mutate):
        artifact = load_artifact(self.skill, case_id)
        mutate(artifact)
        return failed(grade_artifact(self.skill, case_id, artifact))

    def source(self, artifact, source_id):
        return next(s for s in artifact["sources"] if s["source_id"] == source_id)

    def test_false_complete_and_false_hundred_percent_are_rejected(self):
        def fake_complete(a):
            a["overall"]["complete"] = True

        self.assertIn("RPT-D004", self.mutated("RPT-OUT-002", fake_complete))

        def fake_rate(a):
            self.source(a, "api")["pass_rate"] = 1.0
            a["by_unit"]["test"]["pass_rate"] = 1.0

        self.assertTrue(
            {"RPT-D005", "RPT-D007"} & self.mutated("RPT-OUT-002", fake_rate)
        )

        def overall_rate(a):
            a["overall"]["pass_rate"] = 1.0

        self.assertIn("RPT-D004", self.mutated("RPT-OUT-002", overall_rate))

    def test_source_completion_must_follow_independent_closures(self):
        def mark_complete(a):
            self.source(a, "api")["complete"] = True

        self.assertIn("RPT-D003", self.mutated("RPT-OUT-002", mark_complete))

        def cleanup_ignored(a):
            self.source(a, "e2e")["closure"]["cleanup_closed"] = False

        self.assertIn("RPT-D003", self.mutated("RPT-OUT-001", cleanup_ignored))

    def test_units_are_not_mixed_and_population_is_preserved(self):
        def mix_units(a):
            a["by_unit"]["logical_primary"]["planned"] = 3

        self.assertIn("RPT-D006", self.mutated("RPT-OUT-003", mix_units))

        def total_added(a):
            a["overall"]["total"] = 3

        self.assertIn("RPT-D006", self.mutated("RPT-OUT-003", total_added))

        def drop_source(a):
            a["sources"] = [s for s in a["sources"] if s["source_id"] != "api"]
            a["by_unit"].pop("test", None)

        self.assertIn("RPT-D015", self.mutated("RPT-OUT-001", drop_source))

    def test_raw_values_counts_and_exclusions(self):
        def renamed_state(a):
            self.source(a, "e2e")["counts"] = {"PASSED": 2}

        self.assertIn("RPT-D007", self.mutated("RPT-OUT-001", renamed_state))

        def inflated(a):
            self.source(a, "e2e")["counts"]["PASS"] = 5

        self.assertIn("RPT-D007", self.mutated("RPT-OUT-001", inflated))

        def silent_incomplete(a):
            self.source(a, "api")["issues"] = []

        self.assertIn("RPT-D007", self.mutated("RPT-OUT-002", silent_incomplete))

    def test_zero_results_are_distinguished_from_confirmed_empty_sets(self):
        def hide_unknown_zero(a):
            self.source(a, "api")["empty_set"] = "confirmed_no_target"

        self.assertIn("RPT-D008", self.mutated("RPT-OUT-002", hide_unknown_zero))

    def test_exit_judgement_is_derived(self):
        def force_satisfied(a):
            a["exit_judgement"] = "satisfied"

        self.assertIn("RPT-D009", self.mutated("RPT-OUT-002", force_satisfied))

        def stale_plan_satisfied(a):
            a["issues"] = ["plan_not_approved"]

        self.assertIn("RPT-D009", self.mutated("RPT-OUT-001", stale_plan_satisfied))

    def test_static_zero_findings_and_release_boundaries(self):
        def claim_zero(a):
            self.source(a, "review")["zero_findings_claim_allowed"] = True

        self.assertIn("RPT-D010", self.mutated("RPT-OUT-004", claim_zero))

        def release(a):
            a["release_decision"] = "release_ok"

        self.assertIn("RPT-D011", self.mutated("RPT-OUT-001", release))

        def mutable_defects(a):
            a["defect_projection"]["read_only"] = False

        self.assertIn("RPT-D011", self.mutated("RPT-OUT-001", mutable_defects))

    def test_independent_expectations_detect_missing_incomplete_sources(self):
        def hide_incompleteness(a):
            for s in a["sources"]:
                s["complete"] = True
                s["closure"] = dict.fromkeys(s["closure"], True)
            a["overall"]["complete"] = True

        failures = self.mutated("RPT-OUT-002", hide_incompleteness)
        self.assertTrue({"RPT-D013", "RPT-D016"} <= failures)


class TestEvaluationValidatorTests(unittest.TestCase):
    skill = "test-evaluation"

    def mutated(self, case_id, mutate):
        artifact = load_artifact(self.skill, case_id)
        mutate(artifact)
        return failed(grade_artifact(self.skill, case_id, artifact))

    def test_composite_scores_and_missing_axes_are_rejected(self):
        self.assertIn(
            "EVL-D003",
            self.mutated("EVL-OUT-001", lambda a: a.update(composite_score=80)),
        )
        self.assertIn(
            "EVL-D003",
            self.mutated("EVL-OUT-001", lambda a: a["axes"].pop("reusability")),
        )

    def test_axis_state_must_follow_the_metrics(self):
        self.assertIn(
            "EVL-D004",
            self.mutated(
                "EVL-OUT-001", lambda a: a["axes"]["quality"].update(status="measured")
            ),
        )
        self.assertIn(
            "EVL-D004",
            self.mutated(
                "EVL-OUT-001", lambda a: a["axes"]["quality"].update(trend="improved")
            ),
        )

        def unmeasured_value(a):
            a["metrics"].append(
                {
                    "metric_id": "X",
                    "axis": "quality",
                    "status": "unmeasured",
                    "value": 0,
                }
            )

        self.assertIn("EVL-D004", self.mutated("EVL-OUT-001", unmeasured_value))

    def test_time_reduction_cannot_support_a_quality_claim(self):
        def accept_claim(a):
            a["rejected_claims"] = []

        self.assertIn("EVL-D005", self.mutated("EVL-OUT-001", accept_claim))

        def reject_supported(a):
            a["rejected_claims"].append({"axis": "efficiency", "assertion": "improved"})

        self.assertIn("EVL-D005", self.mutated("EVL-OUT-001", reject_supported))

    def test_improvement_states_need_their_evidence(self):
        for name, mutate in {
            "no_adoption": lambda i: i.pop("adoption_ref"),
            "wrong_owner": lambda i: i.update(owner_skill="test-architecture-design"),
            "same_revision": lambda i: i.update(new_revision=i["base_revision"]),
            "unbacked_effect": lambda i: i["effect_metric"].update(status="unchanged"),
        }.items():
            with self.subTest(name=name):
                artifact = load_artifact(self.skill, "EVL-OUT-002")
                mutate(artifact["improvements"][0])
                self.assertIn(
                    "EVL-D006",
                    failed(grade_artifact(self.skill, "EVL-OUT-002", artifact)),
                )

    def test_achieved_count_includes_only_measured_effective_improvements(self):
        def inflate(a):
            a["improvement_summary"]["achieved"] = 4

        self.assertIn("EVL-D007", self.mutated("EVL-OUT-002", inflate))

        def promote_unmeasured(a):
            a["improvements"][3]["state"] = "measured_effective"

        failures = self.mutated("EVL-OUT-002", promote_unmeasured)
        self.assertTrue({"EVL-D006", "EVL-D007"} <= failures)

    def test_stale_inputs_cannot_make_a_final_evaluation(self):
        def finalize(a):
            a["evaluation_status"] = "final"

        self.assertIn("EVL-D008", self.mutated("EVL-OUT-003", finalize))
        self.assertIn(
            "EVL-D002",
            self.mutated("EVL-OUT-001", lambda a: a.update(raw_results_modified=True)),
        )

    def test_handoff_closure_is_derived_from_confirmations(self):
        self.assertIn(
            "EVL-D009",
            self.mutated("EVL-OUT-004", lambda a: a["handoff"].update(closed=True)),
        )

    def test_independent_expectations_detect_wrong_counts(self):
        self.assertIn(
            "EVL-D012",
            self.mutated(
                "EVL-OUT-002", lambda a: a["improvement_summary"].update(achieved=2)
            ),
        )
        self.assertIn(
            "EVL-D011",
            self.mutated(
                "EVL-OUT-004",
                lambda a: a["axes"]["process"].update(status="unmeasured"),
            ),
        )


def rehash(artifact: dict) -> dict:
    """Re-derive a content-addressed snapshot_ref after a deliberate edit."""
    import hashlib

    body = {k: v for k, v in artifact.items() if k != "snapshot_ref"}
    digest = hashlib.sha256(
        json.dumps(
            body, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()
    artifact["snapshot_ref"] = "RPT-" + digest[:40]
    return artifact


class ReviewDrivenReportingValidatorTests(unittest.TestCase):
    skill = "test-reporting"

    def failing(self, case_id, mutate, rehash_ref=True):
        artifact = load_artifact(self.skill, case_id)
        mutate(artifact)
        if rehash_ref:
            rehash(artifact)
        return failed(grade_artifact(self.skill, case_id, artifact))

    def test_snapshot_ref_must_be_the_content_hash(self):
        self.assertIn(
            "RPT-D017",
            self.failing(
                "RPT-OUT-001",
                lambda a: a["overall"].update(complete=False),
                rehash_ref=False,
            ),
        )
        # a content edit that is re-hashed keeps D017 satisfied; other assertions still catch it
        self.assertNotIn(
            "RPT-D017", self.failing("RPT-OUT-001", lambda a: a["issues"].append("x"))
        )

    def test_mixed_unit_criteria_cannot_be_judged(self):
        def pooled(a):
            a["exit_criteria"] = [
                {
                    "criterion_id": "EX-POOL",
                    "metric": "pass_rate",
                    "status": "satisfied",
                    "value": 1.0,
                    "source_ids": ["e2e", "api"],
                }
            ]

        self.assertIn("RPT-D018", self.failing("RPT-OUT-001", pooled))

        def static_pass_rate(a):
            a["exit_criteria"].append(
                {
                    "criterion_id": "X",
                    "metric": "pass_rate",
                    "status": "unsatisfied",
                    "source_ids": ["e2e", "nope"],
                }
            )

        self.assertIn("RPT-D018", self.failing("RPT-OUT-001", static_pass_rate))

    def test_unverified_plan_currentness_cannot_be_presented_as_current_or_satisfied(
        self,
    ):
        def claim_current(a):
            a["plan_currentness"] = "current"

        failures = self.failing("RPT-OUT-006", claim_current)
        self.assertTrue({"RPT-D019", "RPT-D020"} <= failures)

        def satisfied(a):
            a["exit_judgement"] = "satisfied"

        self.assertIn("RPT-D009", self.failing("RPT-OUT-006", satisfied))

        def hide_issue(a):
            a["issues"] = []
            a["exit_judgement"] = "satisfied"

        self.assertIn("RPT-D009", self.failing("RPT-OUT-006", hide_issue))

    def test_pooled_criterion_expectation_is_checked_independently(self):
        def pretend_satisfied(a):
            a["exit_criteria"][0]["status"] = "satisfied"
            a["exit_judgement"] = "satisfied"

        failures = self.failing("RPT-OUT-007", pretend_satisfied)
        self.assertTrue({"RPT-D018", "RPT-D021", "RPT-D014"} <= failures)

    def test_duplicate_retrieval_and_period_cases_cannot_be_reported_complete(self):
        for case_id in ("RPT-OUT-008", "RPT-OUT-009"):
            with self.subTest(case=case_id):

                def force(a):
                    for s in a["sources"]:
                        s["complete"] = True
                        s["closure"] = dict.fromkeys(s["closure"], True)
                    a["overall"]["complete"] = True

                failures = self.failing(case_id, force)
                self.assertTrue({"RPT-D013", "RPT-D016"} <= failures)


class ReviewDrivenEvaluationValidatorTests(unittest.TestCase):
    skill = "test-evaluation"

    def failing(self, case_id, mutate):
        artifact = load_artifact(self.skill, case_id)
        mutate(artifact)
        return failed(grade_artifact(self.skill, case_id, artifact))

    def test_axis_wide_trend_is_derived_from_all_metrics(self):
        self.assertIn(
            "EVL-D004",
            self.failing(
                "EVL-OUT-005", lambda a: a["axes"]["quality"].update(trend="improved")
            ),
        )
        self.assertIn(
            "EVL-D004",
            self.failing(
                "EVL-OUT-006", lambda a: a["axes"]["quality"].update(trend="improved")
            ),
        )
        self.assertIn(
            "EVL-D014",
            self.failing(
                "EVL-OUT-005",
                lambda a: a["axes"]["quality"].update(trend="no_change_or_baseline"),
            ),
        )

    def test_axis_wide_improvement_claim_with_unresolved_or_worsened_metrics_is_rejected(
        self,
    ):
        for case_id in ("EVL-OUT-005", "EVL-OUT-006"):
            with self.subTest(case=case_id):

                def accept(a):
                    a["rejected_claims"] = [
                        c for c in a["rejected_claims"] if c["assertion"] != "improved"
                    ]

                self.assertIn("EVL-D005", self.failing(case_id, accept))

    def test_metric_level_claims_need_the_named_metric_to_have_improved(self):
        def wrong_metric(a):
            a["claims"].append(
                {
                    "axis": "quality",
                    "assertion": "metric_improved",
                    "metric_id": "Q-review",
                }
            )

        self.assertIn("EVL-D005", self.failing("EVL-OUT-005", wrong_metric))

    def test_metric_level_claims_must_match_the_axis_of_the_metric(self):
        def efficiency_for_quality(a):
            a["axes"]["efficiency"]["metrics"] = [
                {
                    "axis": "efficiency",
                    "delta": -5.0,
                    "metric_id": "E-time",
                    "reasons": [],
                    "status": "improved",
                    "value": 10.0,
                }
            ]
            a["metrics"].append(a["axes"]["efficiency"]["metrics"][0])
            a["axes"]["efficiency"].update(status="measured", trend="improved")
            a["claims"].append(
                {
                    "axis": "quality",
                    "assertion": "metric_improved",
                    "metric_id": "E-time",
                }
            )

        # accepted although E-time belongs to the efficiency axis -> invalid
        self.assertIn("EVL-D005", self.failing("EVL-OUT-005", efficiency_for_quality))

        def rejected_correctly(a):
            efficiency_for_quality(a)
            a["rejected_claims"].append(
                {
                    "axis": "quality",
                    "assertion": "metric_improved",
                    "metric_id": "E-time",
                    "reason": "claim_not_supported_by_axis_metrics",
                }
            )

        self.assertNotIn("EVL-D005", self.failing("EVL-OUT-005", rejected_correctly))

        def same_axis_claim(a):
            efficiency_for_quality(a)
            a["claims"][-1]["axis"] = "efficiency"

        self.assertNotIn("EVL-D005", self.failing("EVL-OUT-005", same_axis_claim))

    def test_inputs_need_a_content_hash_and_invalid_metrics_block_final(self):
        def drop_hash(a):
            a["inputs"][0].pop("content_hash")

        self.assertIn("EVL-D008", self.failing("EVL-OUT-001", drop_hash))

        def final_with_invalid(a):
            a["evaluation_status"] = "final"
            a["invalid_metrics"] = ["M-x"]

        self.assertIn("EVL-D008", self.failing("EVL-OUT-001", final_with_invalid))


class ReviewDrivenDefectValidatorTests(unittest.TestCase):
    skill = "defect-management"

    def failing(self, case_id, mutate):
        artifact = load_artifact(self.skill, case_id)
        mutate(artifact)
        return failed(grade_artifact(self.skill, case_id, artifact))

    def test_close_needs_the_fix_verification_of_the_same_candidate(self):
        def make_close(a):
            a["plan"].update(
                decision="allow", operation="close", requires_readback=True
            )
            a["context"]["fix_verification"] = {
                "status": "fix_confirmed",
                "candidate_ref": "DEFC-someone-else",
                "verified_target_ref": "build:42",
                "result_finalized": True,
                "cleanup_status": "成功",
            }

        self.assertIn("DEF-D009", self.failing("DEF-OUT-003", make_close))

    def test_confirmation_needs_every_requested_testware_at_the_requested_revision(
        self,
    ):
        def confirm_partial(a):
            a["result"].update(
                status="fix_confirmed",
                fix_confirmed=True,
                candidate_ref=a["request"]["candidate_ref"],
            )

        self.assertIn("DEF-D013", self.failing("DEF-OUT-007", confirm_partial))

        def other_candidate(a):
            a["result"]["candidate_ref"] = "DEFC-other"

        self.assertIn("DEF-D013", self.failing("DEF-OUT-004", other_candidate))

        def old_revision(a):
            a["result"]["executed_targets"] = [{"ref": "tc:TC-007", "revision": "t2"}]

        self.assertIn("DEF-D013", self.failing("DEF-OUT-004", old_revision))

    def test_approval_bound_to_another_issue_cannot_be_allowed_for_create(self):
        def allow(a):
            a["plan"].update(decision="allow", reasons=[])
            a["context"]["approval"]["binding_matches"] = False

        self.assertIn("DEF-D007", self.failing("DEF-OUT-006", allow))


class IsolatedPackagingTests(unittest.TestCase):
    def test_each_skill_runs_the_repository_runner_from_a_single_skill_copy(self):
        probes = {
            "defect-management": "DEF-OUT-001",
            "test-reporting": "RPT-OUT-001",
            "test-evaluation": "EVL-OUT-001",
        }
        for skill, case_id in probes.items():
            with self.subTest(skill=skill), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                shutil.copytree(REPO_ROOT / "skills" / skill, root / "skills" / skill)
                shutil.copytree(
                    REPO_ROOT / "scripts" / "skills" / "evals",
                    root / "scripts" / "skills" / "evals",
                )
                self.assertEqual([p.name for p in (root / "skills").iterdir()], [skill])
                completed = subprocess.run(
                    [
                        sys.executable,
                        "scripts/skills/evals/deterministic/run.py",
                        "--skill",
                        skill,
                        "--eval-id",
                        case_id,
                        "--output",
                        str(case_dir(skill, case_id) / "output.md"),
                    ],
                    cwd=root,
                    text=True,
                    capture_output=True,
                    check=False,
                )
                self.assertEqual(
                    completed.returncode, 0, completed.stdout + completed.stderr
                )
                self.assertEqual(json.loads(completed.stdout)["status"], "pass")


class StructureTests(unittest.TestCase):
    def test_frontmatter_and_required_resources(self):
        for skill in SKILLS:
            root = REPO_ROOT / "skills" / skill
            text = (root / "SKILL.md").read_text(encoding="utf-8")
            self.assertTrue(text.startswith("---\n"))
            front = text.split("---", 2)[1]
            self.assertRegex(front, rf"(?m)^name: {skill}$")
            self.assertRegex(front, r"(?m)^description: .{20,}$")
            self.assertLessEqual(
                len(re.search(r"(?m)^description: (.+)$", front).group(1)), 1024
            )
            for relative in (
                "references/guidance.md",
                "references/data-contract.md",
                "assets/output-template.md",
                "evals/deterministic/validator.py",
                "evals/output/evals.json",
                "evals/semantic/evals.json",
                "evals/semantic/rubric.json",
                "evals/trigger/train_queries.json",
                "evals/trigger/validation_queries.json",
            ):
                self.assertTrue((root / relative).is_file(), f"{skill}: {relative}")
            self.assertEqual(len(list((root / "scripts").glob("*_runtime.py"))), 1)

    def test_runtime_scripts_do_not_import_sibling_skills_or_repository_packages(self):
        for skill in SKILLS:
            for script in (REPO_ROOT / "skills" / skill / "scripts").glob("*.py"):
                source = script.read_text(encoding="utf-8")
                self.assertNotRegex(
                    source, r"(?m)^\s*(?:from|import)\s+(?:scripts|skills|tests)\b"
                )
                self.assertNotIn("qa-workflow", source)

    def test_semantic_critical_criteria_are_covered_and_trigger_sets_separate_adjacent_skills(
        self,
    ):
        for skill, prefix in SKILLS.items():
            root = REPO_ROOT / "skills" / skill / "evals"
            rubric = json.loads(
                (root / "semantic" / "rubric.json").read_text(encoding="utf-8")
            )
            cases = json.loads(
                (root / "semantic" / "evals.json").read_text(encoding="utf-8")
            )
            critical = {c["id"] for c in rubric["criteria"] if c["critical"]}
            covered = {c for case in cases["cases"] for c in case["criteria"]}
            self.assertEqual(critical - covered, set(), skill)
            self.assertTrue(
                all(c["id"].startswith(f"{prefix}-SEM-") for c in cases["cases"])
            )
            for part in ("train", "validation"):
                rows = json.loads(
                    (root / "trigger" / f"{part}_queries.json").read_text(
                        encoding="utf-8"
                    )
                )
                self.assertGreaterEqual(len(rows), 12)
                self.assertEqual(sum(r["should_trigger"] for r in rows), len(rows) // 2)

    def test_deepcopy_guard_for_loader_isolation(self):
        artifact = load_artifact("test-reporting", "RPT-OUT-001")
        self.assertEqual(copy.deepcopy(artifact), artifact)


if __name__ == "__main__":
    unittest.main()
