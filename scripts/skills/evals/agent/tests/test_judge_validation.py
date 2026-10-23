from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.skills.evals.agent import judge_validation
from scripts.skills.evals.agent.executor import ExecutionResult
from scripts.skills.evals.agent.judge_validation import (
    load_fixture_catalogue,
    run_validation,
)
from scripts.skills.evals.agent.qa_training_store import load_scenario
from scripts.skills.evals.agent.target_workspace import DEFAULT_TARGET_REVISION


def _profile() -> dict:
    return {
        "schema_version": 1,
        "agent": {
            "name": "fake-agent",
            "model": "fake-model",
            "timeout_seconds": 30,
            "cli_version": "test",
            "reasoning_effort": "low",
            "launch_options": [],
            "sandbox_policy": "isolated",
            "approval_policy": "never",
            "network_policy": "model API only",
            "tools": [],
            "mcp_servers": [],
            "skill_roots": ["/workspace/.agents/skills"],
            "external_instructions": "disabled",
            "global_config": "disabled",
        },
        "judge": {
            "model": "fake-judge",
            "command_argv": [
                "docker",
                "run",
                "--rm",
                "--read-only",
                "--cap-drop=ALL",
                "--security-opt=no-new-privileges",
                "-i",
                "--mount",
                "type=tmpfs,target=/tmp",
                "python:3.11",
                "judge",
            ],
            "cwd": "isolated",
            "timeout_seconds": 30,
            "cli_version": "test",
            "reasoning_effort": "low",
            "launch_options": [],
            "sandbox_policy": "isolated",
            "approval_policy": "never",
            "network_policy": "model API only",
            "skill_roots": [],
            "global_config": "disabled",
            "tools": [],
            "mcp_servers": [],
            "external_instructions": "disabled",
        },
        "isolation": {
            "method": "fake-test",
            "agent_read_roots": ["/workspace"],
            "evaluator_read_blocked": True,
        },
        "verification": {
            "status": "verified",
            "method": "fake-test",
            "evidence_path": "isolation.json",
        },
    }


class JudgeValidationTests(unittest.TestCase):
    def test_real_normalizer_matches_normal_violation_and_not_evaluable(self) -> None:
        scenario = load_scenario()
        criteria = [item["id"] for item in scenario["rubric"][:2]]
        profile = _profile()["judge"]

        def raw_criterion(criterion_id: str, rating: int | None) -> dict:
            evaluable = rating is not None
            return {
                "id": criterion_id,
                "evaluable": evaluable,
                "rating": rating,
                "reason": "Fixed evidence.",
                "evidence": ["artifact-00.md"] if evaluable else [],
            }

        cases = (
            (
                "rating-3",
                [criteria[0]],
                [raw_criterion(criteria[0], 3)],
                "rating_at_least_3",
                True,
                "pass",
            ),
            (
                "rating-4",
                [criteria[0]],
                [raw_criterion(criteria[0], 4)],
                "rating_at_least_3",
                True,
                "pass",
            ),
            (
                "rating-1",
                [criteria[0]],
                [raw_criterion(criteria[0], 1)],
                "rating_1",
                True,
                "fail",
            ),
            (
                "rating-2",
                [criteria[0]],
                [raw_criterion(criteria[0], 2)],
                "rating_at_least_3",
                False,
                "needs_review",
            ),
            (
                "not-evaluable",
                [criteria[0]],
                [raw_criterion(criteria[0], None)],
                "rating_at_least_3",
                False,
                "not_evaluable",
            ),
            (
                "not-evaluable-rating-1",
                [criteria[0]],
                [raw_criterion(criteria[0], None)],
                "rating_1",
                False,
                "not_evaluable",
            ),
            (
                "multiple-pass",
                criteria,
                [raw_criterion(criteria[0], 3), raw_criterion(criteria[1], 4)],
                "rating_at_least_3",
                True,
                None,
            ),
            (
                "multiple-needs-review",
                criteria,
                [raw_criterion(criteria[0], 3), raw_criterion(criteria[1], 2)],
                "rating_at_least_3",
                False,
                None,
            ),
            (
                "missing-criterion",
                criteria,
                [raw_criterion(criteria[0], 3)],
                "rating_at_least_3",
                None,
                None,
            ),
            (
                "invalid-json",
                [criteria[0]],
                "not JSON",
                "rating_at_least_3",
                None,
                None,
            ),
            (
                "invalid-rating",
                [criteria[0]],
                [raw_criterion(criteria[0], 5)],
                "rating_at_least_3",
                None,
                None,
            ),
        )
        for label, requested, raw, expected, matched, normalized_status in cases:
            with self.subTest(case=label):
                response = (
                    raw if isinstance(raw, str) else json.dumps({"criteria": raw})
                )
                with (
                    tempfile.TemporaryDirectory() as temporary,
                    patch.object(
                        judge_validation,
                        "run_command",
                        return_value=ExecutionResult(
                            0, response, None, "empty", False, 0.01
                        ),
                    ),
                ):
                    row = judge_validation._run_judge_case(
                        command_argv=profile["command_argv"],
                        judge_profile=profile,
                        prompt="fixed prompt",
                        cwd=Path(temporary),
                        timeout=30,
                        run_tag="normalizer-contract",
                        criteria=requested,
                        scenario=scenario,
                    )
                if matched is None:
                    self.assertEqual(row["status"], "invalid_response")
                    self.assertNotIn("normalized", row)
                    self.assertFalse(
                        judge_validation._expected_matches(
                            {"expected": expected}, {"criteria": []}
                        )
                    )
                    continue
                self.assertEqual(row["status"], "pass")
                normalized_criteria = row["normalized"]["criteria"]
                if normalized_status is not None:
                    self.assertEqual(
                        normalized_criteria[0]["status"], normalized_status
                    )
                self.assertNotIn("evaluable", normalized_criteria[0])
                self.assertEqual(
                    judge_validation._expected_matches(
                        {"expected": expected}, row["normalized"]
                    ),
                    matched,
                )
                self.assertTrue(
                    set(normalized_criteria[0]) >= {"id", "status", "rating"}
                )

    def test_judge_execution_failure_is_not_a_normalizer_error(self) -> None:
        scenario = load_scenario()
        judge_profile = _profile()["judge"]
        criterion = scenario["rubric"][0]["id"]
        with (
            tempfile.TemporaryDirectory() as temporary,
            patch.object(
                judge_validation,
                "run_command",
                return_value=ExecutionResult(7, "", "failed", "captured", False, 0.01),
            ),
        ):
            row = judge_validation._run_judge_case(
                command_argv=judge_profile["command_argv"],
                judge_profile=judge_profile,
                prompt="fixed prompt",
                cwd=Path(temporary),
                timeout=30,
                run_tag="execution-error",
                criteria=[criterion],
                scenario=scenario,
            )
        self.assertEqual(row["status"], "execution_error")
        self.assertNotIn("normalized", row)

    def test_codex_judge_without_safe_launcher_observations_is_unverified(self) -> None:
        scenario = load_scenario()
        judge_profile = _profile()["judge"]
        judge_profile.update(
            {
                "cli_version": "codex-cli 0.163.0",
                "sandbox_policy": "read-only",
            }
        )
        criterion = scenario["rubric"][0]["id"]
        response = json.dumps(
            {
                "criteria": [
                    {
                        "id": criterion,
                        "evaluable": True,
                        "rating": 3,
                        "reason": "Evidence supports the criterion.",
                        "evidence": ["artifact-00.md"],
                    }
                ]
            }
        )
        with tempfile.TemporaryDirectory() as temporary:
            cwd = Path(temporary) / "judge"
            cwd.mkdir()
            with patch.object(
                judge_validation,
                "run_command",
                return_value=ExecutionResult(0, response, None, "empty", False, 0.01),
            ):
                result = judge_validation._run_judge_case(
                    command_argv=judge_profile["command_argv"],
                    judge_profile=judge_profile,
                    prompt="fixed prompt",
                    cwd=cwd,
                    timeout=30,
                    run_tag="missing-sidecar",
                    criteria=[criterion],
                    scenario=scenario,
                )
        self.assertEqual(result["status"], "evidence_unverified")
        self.assertNotIn("normalized", result)

    def _baseline_output(self, output: Path, scenario: dict) -> None:
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
            json.dumps(
                {"schema_version": 1, "artifacts": artifacts, "routing": routing}
            ),
            encoding="utf-8",
        )
        (output / "final-message.md").write_text(
            "Analysis and design workflow completed.\n", encoding="utf-8"
        )

    def _run(self, *, approved: bool, candidate: bool) -> dict:
        scenario = load_scenario()
        run_parent = judge_validation.REPO_ROOT / ".agent-eval-runs"
        created_parent = not run_parent.exists()
        run_parent.mkdir(exist_ok=True)
        try:
            with tempfile.TemporaryDirectory(dir=run_parent) as temporary:
                root = Path(temporary)
                baseline_root = root / "baseline"
                baseline_output = baseline_root / "attempt-01" / "qa-output"
                self._baseline_output(baseline_output, scenario)
                runtime_root = baseline_root / "attempt-01"
                (runtime_root / "runtime-checks.json").write_text(
                    json.dumps(
                        {
                            "workflow_runtime": {
                                "workflow_runtime_can_complete": True,
                                "workflow_runtime_has_unclosed_issues": False,
                            }
                        }
                    ),
                    encoding="utf-8",
                )
                second_output = baseline_root / "attempt-02" / "qa-output"
                self._baseline_output(second_output, scenario)
                second_runtime = baseline_root / "attempt-02"
                (second_runtime / "runtime-checks.json").write_text(
                    json.dumps(
                        {
                            "workflow_runtime": {
                                "workflow_runtime_can_complete": True,
                                "workflow_runtime_has_unclosed_issues": False,
                            }
                        }
                    ),
                    encoding="utf-8",
                )
                baseline_result = baseline_root / "result.json"
                baseline_result.write_text(
                    json.dumps(
                        {
                            "profile_verification": "verified",
                            "evaluator_revision": "1" * 40,
                            "target_revision": DEFAULT_TARGET_REVISION,
                            "scenario_fingerprint": scenario["scenario_fingerprint"],
                            "attempts": [
                                {
                                    "status": "pass",
                                    "saved_result_root": "attempt-01",
                                    "saved_output_root": "attempt-01/qa-output",
                                },
                                {
                                    "status": "pass",
                                    "saved_result_root": "attempt-02",
                                    "saved_output_root": "attempt-02/qa-output",
                                },
                            ],
                        }
                    ),
                    encoding="utf-8",
                )
                target = root / "target"
                target.mkdir()
                output = root / "judge-output"
                output.mkdir()
                (output / "isolation.json").write_text("{}\n", encoding="utf-8")
                catalogue = load_fixture_catalogue()
                approval = root / "approval.json"
                approval_path = None
                if approved:
                    approval.write_text(
                        json.dumps(
                            {
                                "dataset_revision": catalogue["dataset_revision"],
                                "approvals": [
                                    {
                                        "case_id": "normal-workflow",
                                        "reviewer": "test-only-fixture-reviewer",
                                        "approved_at": "2026-10-22T00:00:00Z",
                                        "evidence": "docs/spec/features/checkout-and-payment.md#workflow",
                                    }
                                ],
                            }
                        ),
                        encoding="utf-8",
                    )
                    approval_path = approval
                profile_path = root / "profile.json"
                profile_path.write_text(json.dumps(_profile()), encoding="utf-8")

                original_judge_case = judge_validation._run_judge_case

                def actual_judge(**kwargs):
                    response = json.dumps(
                        {
                            "criteria": [
                                {
                                    "id": criterion,
                                    "evaluable": True,
                                    "rating": 3,
                                    "reason": "Fixed fixture evidence.",
                                    "evidence": ["artifact-00.md"],
                                }
                                for criterion in kwargs["criteria"]
                            ]
                        }
                    )
                    with (
                        patch.object(
                            judge_validation,
                            "run_command",
                            return_value=ExecutionResult(
                                0, response, None, "empty", False, 0.01
                            ),
                        ),
                        patch.object(
                            judge_validation,
                            "verify_judge_docker_command",
                            return_value={"status": "verified"},
                        ),
                    ):
                        return original_judge_case(**kwargs)

                with (
                    patch.object(
                        judge_validation, "assert_clean_checkout", return_value="2" * 40
                    ),
                    patch.object(
                        judge_validation,
                        "resolve_commit",
                        return_value=DEFAULT_TARGET_REVISION,
                    ),
                    patch.object(
                        judge_validation,
                        "extract_revision_files",
                        return_value={
                            relative: b"Fixed specification reference.\n"
                            for relative in scenario["reference_paths"]
                        },
                    ),
                    patch.object(
                        judge_validation, "verify_profile_evidence", return_value=True
                    ),
                    patch.object(
                        judge_validation, "_run_judge_case", side_effect=actual_judge
                    ),
                ):
                    result = run_validation(
                        baseline_result=baseline_result,
                        target_root=target,
                        profile_path=profile_path,
                        output_root=output,
                        approval_path=approval_path,
                        proposal_command=None,
                        candidate_judge_command=[
                            "docker",
                            "run",
                            "--rm",
                            "--read-only",
                            "--cap-drop=ALL",
                            "--security-opt=no-new-privileges",
                            "-i",
                            "--mount",
                            "type=tmpfs,target=/tmp",
                            "python:3.11",
                            "candidate-judge",
                        ]
                        if candidate
                        else None,
                        max_cases=1,
                        max_seconds=60,
                        repeat=2,
                    )
                self.assertTrue((output / "result.json").is_file())
                saved_result = json.loads(
                    (output / "result.json").read_text(encoding="utf-8")
                )
                self.assertEqual(saved_result, result)
                self.assertIn(
                    "evaluable",
                    result["cases"][0]["judge_runs"][0]["response"],
                )
                self.assertNotIn(
                    "evaluable",
                    result["cases"][0]["judge_runs"][0]["normalized"]["criteria"][0],
                )
                return result
        finally:
            if created_parent:
                try:
                    run_parent.rmdir()
                except OSError:
                    pass

    def test_approved_fixture_and_candidate_judge_are_checked_on_independent_repeats(
        self,
    ) -> None:
        result = self._run(approved=True, candidate=True)
        self.assertEqual(result["status"], "verified")
        self.assertEqual(result["candidate_judge_validation_status"], "verified")
        self.assertEqual(result["cases"][0]["candidate_judge_status"], "verified")
        self.assertTrue(result["cases"][0]["candidate_matches_baseline"])

    def test_unapproved_fixture_remains_pending_even_when_fake_judge_matches(
        self,
    ) -> None:
        result = self._run(approved=False, candidate=False)
        self.assertEqual(result["status"], "review_pending")
        self.assertEqual(result["cases"][0]["status"], "review_pending")


if __name__ == "__main__":
    unittest.main()
