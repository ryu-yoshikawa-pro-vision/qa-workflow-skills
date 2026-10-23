from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.skills.evals.agent import improve as improve_module
from scripts.skills.evals.agent.common import (
    AgentEvalError,
    canonical_fingerprint,
    visible_skill_names,
)
from scripts.skills.evals.agent.improve import (
    _judge_verification_map,
    _skill_use_for_attempt,
    _stable_failures,
    _validate_repair_diff,
)
from scripts.skills.evals.agent.judge_validation import (
    _artifact_content_fingerprint,
    _fixture_approval_binding,
    _fixture_prompt,
    _prepare_fixture,
    load_fixture_catalogue,
)
from scripts.skills.evals.agent.qa_training_store import load_scenario
from scripts.skills.evals.agent.target_workspace import DEFAULT_TARGET_REVISION


def _write_baseline_output(output: Path, scenario: dict) -> None:
    output.mkdir(parents=True)
    artifacts = []
    routing = []
    for index, required in enumerate(scenario["required_artifacts"]):
        artifact_id = f"artifact-{index:02d}"
        name = f"artifact-{index:02d}.md"
        (output / name).write_text(
            f"Evidence for {required['skill']} {required['kind']}\n",
            encoding="utf-8",
        )
        artifacts.append({**required, "artifact_id": artifact_id, "path": name})
        routing.append(
            {
                "skill": required["skill"],
                "scope": required["scope"],
                "status": "executed",
                "reason": "The fixed request requires this artifact.",
                "artifact_ids": [artifact_id],
            }
        )
    (output / "artifact-index.json").write_text(
        json.dumps({"schema_version": 1, "artifacts": artifacts, "routing": routing}),
        encoding="utf-8",
    )
    (output / "final-message.md").write_text(
        "Analysis and design workflow completed.\n", encoding="utf-8"
    )


def _complete_validation_fixture(root: Path) -> tuple[Path, str]:
    scenario = load_scenario()
    catalogue = load_fixture_catalogue()
    baseline_output = root / "baseline" / "attempt-01" / "qa-output"
    _write_baseline_output(baseline_output, scenario)
    baseline_fingerprint = _artifact_content_fingerprint(baseline_output)
    references = {
        relative: b"Fixed specification reference.\n"
        for relative in scenario["reference_paths"]
    }
    (root / "fixtures").mkdir()
    cases = []
    for definition in catalogue["cases"]:
        case_root = root / "fixtures" / definition["id"]
        case_root.mkdir()
        fixture_output, validation, final_message = _prepare_fixture(
            definition=definition,
            baseline_output=baseline_output,
            fixture_root=case_root,
            scenario=scenario,
        )
        prompt, criteria = _fixture_prompt(
            definition=definition,
            scenario=scenario,
            references=references,
            output=fixture_output,
            validation=validation,
            final_message=final_message,
            machine_summary={
                "required_artifacts_present": validation["status"] == "pass",
                "workflow_runtime_can_complete": True,
                "workflow_runtime_has_unclosed_issues": False,
            },
        )
        artifact_fingerprint = _artifact_content_fingerprint(fixture_output)
        binding = _fixture_approval_binding(
            catalogue=catalogue,
            definition=definition,
            scenario=scenario,
            references=references,
            baseline_artifact_fingerprint=baseline_fingerprint,
            artifact_content_fingerprint=artifact_fingerprint,
            prompt=prompt,
            criteria=criteria,
            normative_revision=DEFAULT_TARGET_REVISION,
        )
        rating = 3 if definition["expected"] == "rating_at_least_3" else 1
        normalized = {
            "criteria": [
                {
                    "id": criterion,
                    "status": "pass" if rating >= 3 else "fail",
                    "rating": rating,
                }
                for criterion in criteria
            ]
        }
        approval = {
            "case_id": definition["id"],
            "reviewer": "test-only-synthetic-reviewer",
            "approved_at": "2026-10-22T00:00:00Z",
            "evidence": definition["references"][0] + "#synthetic-test",
            "binding": binding,
            "status": "approved",
            "binding_status": "matched",
        }
        cases.append(
            {
                "case_id": definition["id"],
                "criteria": criteria,
                "expected": definition["expected"],
                "status": "verified",
                "approval": approval,
                "approval_binding": binding,
                "fixture_fingerprint": canonical_fingerprint(binding),
                "fixture_content_integrity_status": "verified",
                "judge_runs": [
                    {
                        "status": "pass",
                        "prompt_sha256": binding["judge_input_fingerprint"],
                        "expectation_matched": True,
                        "normalized": normalized,
                    }
                    for _ in range(2)
                ],
            }
        )
    result_path = root / "result.json"
    result_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "dataset_revision": catalogue["dataset_revision"],
                "fixture_catalogue_fingerprint": canonical_fingerprint(catalogue),
                "evaluator_revision": "1" * 40,
                "target_revision": DEFAULT_TARGET_REVISION,
                "judge_profile_fingerprint": "test-profile-fingerprint",
                "repeat": 2,
                "cases": cases,
            }
        ),
        encoding="utf-8",
    )
    return result_path, baseline_fingerprint


class ImprovementGateTests(unittest.TestCase):
    def test_agent_workspace_exposes_only_skills_routed_by_selected_cases(self) -> None:
        self.assertEqual(
            visible_skill_names(
                [
                    {"skill": "qa-workflow"},
                    {"skill": "test-case-design"},
                    {"skill": "qa-workflow"},
                ]
            ),
            ["qa-workflow", "test-case-design"],
        )

    def test_skill_use_observation_is_read_from_the_specific_routed_skill(self) -> None:
        attempt = {
            "skill_use_observation": {
                "qa-workflow": "observed",
                "test-case-design": "unverified",
            }
        }
        self.assertEqual(_skill_use_for_attempt(attempt, "qa-workflow"), "observed")
        self.assertEqual(
            _skill_use_for_attempt(attempt, "test-case-design"), "unverified"
        )
        self.assertEqual(_skill_use_for_attempt({}, "qa-workflow"), "unverified")

    def test_reproducible_approved_critical_failure_is_selected(self) -> None:
        attempts = [
            {
                "attempt": {"attempt_id": f"attempt-{index}"},
                "criteria": {"QTS-SEM-006": {"rating": 1, "status": "fail"}},
            }
            for index in (1, 2)
        ]
        verified = {
            "QTS-SEM-006": {"status": "verified", "case_id": "major-violation-006"}
        }
        self.assertEqual(
            _stable_failures(attempts, verified)[0]["criterion"], "QTS-SEM-006"
        )

    def test_judge_jitter_or_unverified_fixture_blocks_repair(self) -> None:
        attempts = [
            {"criteria": {"QTS-SEM-006": {"rating": rating, "status": status}}}
            for rating, status in ((1, "fail"), (2, "needs_review"))
        ]
        self.assertEqual(
            _stable_failures(attempts, {"QTS-SEM-006": {"status": "verified"}}), []
        )
        stable = [
            {"criteria": {"QTS-SEM-006": {"rating": 1, "status": "fail"}}},
            {"criteria": {"QTS-SEM-006": {"rating": 1, "status": "fail"}}},
        ]
        self.assertEqual(_stable_failures(stable, {}), [])

    def test_judge_verification_aggregates_fixture_coverage_per_criterion(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result_path, baseline_fingerprint = _complete_validation_fixture(root)
            original = json.loads(result_path.read_text(encoding="utf-8"))

            def evaluate(value: dict, **expected) -> dict:
                evaluator_expected = expected.pop(
                    "expected_evaluator_revision", "1" * 40
                )
                target_expected = expected.pop(
                    "expected_target_revision", DEFAULT_TARGET_REVISION
                )
                profile_expected = expected.pop(
                    "expected_profile_fingerprint", "test-profile-fingerprint"
                )
                baseline_expected = expected.pop(
                    "expected_baseline_artifact_fingerprint", baseline_fingerprint
                )
                target_root = expected.pop("target_root", None)
                result_path.write_text(json.dumps(value), encoding="utf-8")
                return _judge_verification_map(
                    result_path,
                    expected_evaluator_revision=evaluator_expected,
                    expected_target_revision=target_expected,
                    expected_profile_fingerprint=profile_expected,
                    expected_baseline_artifact_fingerprint=baseline_expected,
                    target_root=target_root,
                    **expected,
                )

            complete = evaluate(json.loads(json.dumps(original)))
            self.assertEqual(complete["QTS-SEM-006"]["status"], "verified")
            self.assertEqual(complete["QTS-SEM-005"]["status"], "verified")
            self.assertEqual(complete["QTS-SEM-008"]["status"], "judge_unverified")
            self.assertIn(
                "missing_major_violation_fixture",
                complete["QTS-SEM-008"]["reason"],
            )

            cases = original["cases"]

            missing_violation = json.loads(json.dumps(original))
            missing_violation["cases"] = [
                row for row in cases if row["case_id"] != "major-violation-006"
            ]
            result = evaluate(missing_violation)
            self.assertEqual(result["QTS-SEM-006"]["status"], "judge_unverified")
            self.assertEqual(result["QTS-SEM-005"]["status"], "verified")

            missing_normal = json.loads(json.dumps(original))
            missing_normal["cases"] = [
                row for row in cases if row["case_id"] != "normal-artifacts"
            ]
            result = evaluate(missing_normal)
            self.assertEqual(result["QTS-SEM-006"]["status"], "judge_unverified")
            self.assertEqual(result["QTS-SEM-001"]["status"], "verified")

            normal_mismatch = json.loads(json.dumps(original))
            next(
                row
                for row in normal_mismatch["cases"]
                if row["case_id"] == "normal-artifacts"
            )["status"] = "label_or_judge_mismatch"
            self.assertEqual(
                evaluate(normal_mismatch)["QTS-SEM-006"]["status"],
                "judge_unverified",
            )

            violation_mismatch = json.loads(json.dumps(original))
            next(
                row
                for row in violation_mismatch["cases"]
                if row["case_id"] == "major-violation-006"
            )["status"] = "label_or_judge_mismatch"
            self.assertEqual(
                evaluate(violation_mismatch)["QTS-SEM-006"]["status"],
                "judge_unverified",
            )

            pending_approval = json.loads(json.dumps(original))
            approval_case = next(
                row
                for row in pending_approval["cases"]
                if row["case_id"] == "major-violation-006"
            )
            approval_case["approval"]["status"] = "review_pending"
            self.assertEqual(
                evaluate(pending_approval)["QTS-SEM-006"]["status"],
                "judge_unverified",
            )

            binding_mismatch = json.loads(json.dumps(original))
            binding_case = next(
                row
                for row in binding_mismatch["cases"]
                if row["case_id"] == "major-violation-006"
            )
            binding_case["approval_binding"]["expected"] = "rating_at_least_3"
            self.assertEqual(
                evaluate(binding_mismatch)["QTS-SEM-006"]["status"],
                "judge_unverified",
            )

            binding_version_mismatch = json.loads(json.dumps(original))
            version_case = next(
                row
                for row in binding_version_mismatch["cases"]
                if row["case_id"] == "major-violation-006"
            )
            version_case["approval_binding"]["binding_version"] = True
            version_case["approval"]["binding"]["binding_version"] = True
            version_case["fixture_fingerprint"] = canonical_fingerprint(
                version_case["approval_binding"]
            )
            self.assertEqual(
                evaluate(binding_version_mismatch)["QTS-SEM-006"]["status"],
                "judge_unverified",
            )

            jitter = json.loads(json.dumps(original))
            normal_case = next(
                row for row in jitter["cases"] if row["case_id"] == "normal-artifacts"
            )
            normal_case["judge_runs"][1]["normalized"]["criteria"][0]["rating"] = 4
            self.assertEqual(
                evaluate(jitter)["QTS-SEM-006"]["status"], "judge_unverified"
            )

            not_evaluable = json.loads(json.dumps(original))
            not_evaluable_case = next(
                row
                for row in not_evaluable["cases"]
                if row["case_id"] == "major-violation-006"
            )
            not_evaluable_case["judge_runs"][0]["normalized"]["criteria"][0] = {
                "id": "QTS-SEM-006",
                "status": "not_evaluable",
                "rating": None,
            }
            not_evaluable_case["judge_runs"][0]["expectation_matched"] = False
            self.assertEqual(
                evaluate(not_evaluable)["QTS-SEM-006"]["status"],
                "judge_unverified",
            )

            execution_error = json.loads(json.dumps(original))
            execution_case = next(
                row
                for row in execution_error["cases"]
                if row["case_id"] == "major-violation-006"
            )
            execution_case["judge_runs"][0]["status"] = "execution_error"
            self.assertEqual(
                evaluate(execution_error)["QTS-SEM-006"]["status"],
                "judge_unverified",
            )

            one_unverified = json.loads(json.dumps(original))
            next(
                row
                for row in one_unverified["cases"]
                if row["case_id"] == "major-violation-006"
            )["status"] = "review_pending"
            result = evaluate(one_unverified)
            attempts = [
                {
                    "attempt": {"attempt_id": f"attempt-{index}"},
                    "criteria": {
                        criterion: {"rating": 1, "status": "fail"}
                        for criterion in ("QTS-SEM-005", "QTS-SEM-006")
                    },
                }
                for index in (1, 2)
            ]
            failures = _stable_failures(attempts, result)
            self.assertEqual([row["criterion"] for row in failures], ["QTS-SEM-005"])

            all_unverified = json.loads(json.dumps(original))
            for row in all_unverified["cases"]:
                row["status"] = "review_pending"
            result = evaluate(all_unverified)
            self.assertTrue(
                all(row["status"] == "judge_unverified" for row in result.values())
            )
            self.assertEqual(_stable_failures(attempts, result), [])

            provenance_mismatch = evaluate(
                json.loads(json.dumps(original)),
                expected_profile_fingerprint="different-profile",
            )
            self.assertTrue(
                all(
                    row["status"] == "judge_unverified"
                    for row in provenance_mismatch.values()
                )
            )
            evaluator_mismatch = evaluate(
                json.loads(json.dumps(original)),
                expected_evaluator_revision="9" * 40,
            )
            self.assertTrue(
                all(
                    row["status"] == "judge_unverified"
                    for row in evaluator_mismatch.values()
                )
            )
            baseline_mismatch = evaluate(
                json.loads(json.dumps(original)),
                expected_baseline_artifact_fingerprint="sha256:" + "0" * 64,
            )
            self.assertEqual(
                baseline_mismatch["QTS-SEM-006"]["status"], "judge_unverified"
            )

            scenario = load_scenario()
            references = {
                relative: b"Fixed specification reference.\n"
                for relative in scenario["reference_paths"]
            }
            with patch.object(
                improve_module, "extract_revision_files", return_value=references
            ):
                normative_match = evaluate(
                    json.loads(json.dumps(original)), target_root=root
                )
            self.assertEqual(normative_match["QTS-SEM-003"]["status"], "verified")
            changed_references = dict(references)
            changed_references["docs/spec/unresolved-specifications.md"] = (
                b"Changed normative specification.\n"
            )
            with patch.object(
                improve_module,
                "extract_revision_files",
                return_value=changed_references,
            ):
                normative_mismatch = evaluate(
                    json.loads(json.dumps(original)), target_root=root
                )
            self.assertEqual(
                normative_mismatch["QTS-SEM-003"]["status"], "judge_unverified"
            )
            self.assertEqual(normative_mismatch["QTS-SEM-005"]["status"], "verified")

            changed_fixture = root / "fixtures" / "major-violation-006" / "qa-output"
            old_approval_case = next(
                row
                for row in original["cases"]
                if row["case_id"] == "major-violation-006"
            )
            self.assertTrue(
                all(
                    run["expectation_matched"] is True
                    for run in old_approval_case["judge_runs"]
                )
            )
            self.assertEqual(old_approval_case["approval"]["binding_status"], "matched")
            old_approval_fingerprint = old_approval_case["approval_binding"][
                "artifact_content_fingerprint"
            ]
            artifact_index = json.loads(
                (changed_fixture / "artifact-index.json").read_text(encoding="utf-8")
            )
            changed_artifact = changed_fixture / artifact_index["artifacts"][0]["path"]
            changed_artifact.write_text(
                changed_artifact.read_text(encoding="utf-8")
                + "Changed after approval.\n",
                encoding="utf-8",
            )
            result = evaluate(json.loads(json.dumps(original)))
            self.assertEqual(result["QTS-SEM-006"]["status"], "judge_unverified")
            self.assertEqual(result["QTS-SEM-005"]["status"], "verified")
            self.assertNotEqual(
                old_approval_fingerprint,
                _artifact_content_fingerprint(changed_fixture),
            )
            failures = _stable_failures(attempts, result)
            self.assertEqual([row["criterion"] for row in failures], ["QTS-SEM-005"])

    def test_repair_diff_accepts_only_requested_skill_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            skills = Path(temporary) / ".agents" / "skills"
            skill = skills / "qa-workflow"
            skill.mkdir(parents=True)
            source = skill / "SKILL.md"
            source.write_text("before\n", encoding="utf-8")
            before = {"qa-workflow/SKILL.md": "old"}
            source.write_text("after\n", encoding="utf-8")
            changes, _ = _validate_repair_diff(
                before, skills, "qa-workflow", {"SKILL.md"}
            )
        self.assertEqual(changes[0]["path"], "SKILL.md")

    def test_repair_diff_rejects_unrequested_path(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            skills = Path(temporary)
            skill = skills / "qa-workflow"
            skill.mkdir()
            (skill / "SKILL.md").write_text("changed", encoding="utf-8")
            with self.assertRaises(AgentEvalError):
                _validate_repair_diff(
                    {"qa-workflow/SKILL.md": "old"},
                    skills,
                    "qa-workflow",
                    {"references/guide.md"},
                )


if __name__ == "__main__":
    unittest.main()
