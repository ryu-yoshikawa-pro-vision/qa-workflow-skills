from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.skills.evals.agent import compare, judge_validation
from scripts.skills.evals.agent.common import AgentEvalError, sha256_bytes
from scripts.skills.evals.agent.executor import ExecutionResult
from scripts.skills.evals.agent.judge_validation import (
    _approval_binding_status,
    _artifact_content_fingerprint,
    _baseline_attempt_eligibility,
    _baseline_fixture_precondition,
    _fixture_approval_binding,
    _fixture_prompt,
    _prepare_fixture,
    load_fixture_catalogue,
    run_validation,
)
from scripts.skills.evals.agent.qa_training_store import (
    build_artifact_manifest,
    load_scenario,
)
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
    def test_schema2_rejects_docker_candidate_judge_and_proposal_commands(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_root = root / "baseline-run"
            (run_root / "attempt-01" / "qa-output").mkdir(parents=True)
            profile = _profile()
            profile["schema_version"] = 2
            baseline = {
                "profile_verification": "verified",
                "execution_profile_fingerprint": judge_validation.profile_fingerprint(
                    profile
                ),
                "agent_command_template": ["fake-agent"],
                "attempts": [
                    {
                        "status": "pass",
                        "saved_output_root": "attempt-01/qa-output",
                    }
                ],
            }
            docker_argv = ["docker", "run", "candidate"]
            for field, message in (
                ("candidate_judge_command", "schema 2 candidate Judge"),
                ("proposal_command", "schema 2 proposal Agent"),
            ):
                arguments = {
                    "candidate_judge_command": None,
                    "proposal_command": None,
                }
                arguments[field] = docker_argv
                with self.subTest(field=field):
                    with (
                        patch.object(
                            compare,
                            "_load_result",
                            return_value=(baseline, run_root),
                        ),
                        patch.object(
                            judge_validation,
                            "load_execution_profile",
                            return_value=profile,
                        ),
                        patch.object(
                            judge_validation,
                            "verify_profile_evidence",
                            return_value=True,
                        ),
                        self.assertRaisesRegex(AgentEvalError, message),
                    ):
                        run_validation(
                            baseline_result=run_root / "result.json",
                            target_root=root,
                            profile_path=root / "profile.json",
                            output_root=root / "output",
                            approval_path=None,
                            max_cases=1,
                            max_seconds=60,
                            repeat=2,
                            **arguments,
                        )

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

    def test_redacted_wsl2_judge_response_is_not_scored_or_hashed(self) -> None:
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
                        "reason": "Safe synthetic response.",
                        "evidence": ["artifact-00.md"],
                    }
                ]
            }
        )

        def fake_launcher(_profile, *, observations_path):
            return ["fake-launcher", "--observations-path", str(observations_path)]

        def fake_run(argv, **_kwargs):
            sidecar = Path(argv[argv.index("--observations-path") + 1])
            sidecar.write_text(
                json.dumps(
                    {
                        "protocol": "codex_wsl2_bwrap_launcher_v1",
                        "mode": "judge",
                        "status": "evidence_unverified",
                        "final_message_redacted": True,
                        "response_sha256": None,
                        "jsonl": {"status": "captured", "tool_event_count": 0},
                    }
                ),
                encoding="utf-8",
            )
            return ExecutionResult(0, response, None, "empty", False, 0.01)

        with tempfile.TemporaryDirectory() as temporary:
            cwd = Path(temporary) / "judge"
            cwd.mkdir()
            with (
                patch.object(
                    judge_validation,
                    "verify_judge_wsl2_command",
                    return_value={"status": "verified"},
                ),
                patch.object(
                    judge_validation,
                    "judge_launcher_argv_for_profile",
                    side_effect=fake_launcher,
                ),
                patch.object(judge_validation, "run_command", side_effect=fake_run),
                patch(
                    "scripts.skills.evals.semantic.result.normalize_judge_response",
                    side_effect=AssertionError(
                        "redacted Judge response must not be scored"
                    ),
                ),
            ):
                result = judge_validation._run_judge_case(
                    command_argv=["codex"],
                    judge_profile=judge_profile,
                    prompt="fixed prompt",
                    cwd=cwd,
                    timeout=30,
                    run_tag="redacted-wsl2-response",
                    criteria=[criterion],
                    scenario=scenario,
                )

        self.assertEqual(result["status"], "evidence_unverified")
        self.assertEqual(result["evidence_status"], "evidence_unverified")
        self.assertIsNone(result["response_sha256"])
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

    def _baseline_attempt(
        self,
        root: Path,
        *,
        scenario: dict,
        attempt_id: str,
        status: str = "pass",
        incomplete_workflow_route: bool = False,
        runtime_status: str = "pass",
        judge_status: str | None = None,
    ) -> dict:
        attempt_root = root / attempt_id
        output = attempt_root / "qa-output"
        self._baseline_output(output, scenario)
        final_message_path = output / "final-message.md"
        final_message = final_message_path.read_text(encoding="utf-8")
        final_message_path.unlink()
        if incomplete_workflow_route:
            index_path = output / "artifact-index.json"
            index = json.loads(index_path.read_text(encoding="utf-8"))
            route = next(
                row for row in index["routing"] if row["skill"] == "qa-workflow"
            )
            route.update(
                {"status": "incomplete", "reason": "Unresolved scope remains."}
            )
            index_path.write_text(json.dumps(index), encoding="utf-8")
        validation = judge_validation.validate_artifact_index(output, scenario)
        (output / "artifact-manifest.json").write_text(
            json.dumps(build_artifact_manifest(output, validation)), encoding="utf-8"
        )
        final_message_path.write_text(final_message, encoding="utf-8")
        attempt_root.mkdir(parents=True, exist_ok=True)
        evidence = {
            "target-integrity.json": {"unchanged": True},
            "output-safety-scan.json": {
                "status": "clear",
                "secret_shaped_or_unreadable_paths": [],
            },
            "artifact-validation.json": validation,
            "runtime-checks.json": {
                "verifier": {"status": runtime_status},
                "workflow_runtime": {
                    "status": runtime_status,
                    "workflow_runtime_can_complete": not incomplete_workflow_route,
                    "workflow_runtime_has_unclosed_issues": incomplete_workflow_route,
                },
            },
            "saved-agent-output.json": {"status": "saved", "files": []},
        }
        for name, payload in evidence.items():
            (attempt_root / name).write_text(json.dumps(payload), encoding="utf-8")
        trace_path = f"{attempt_id}/agent-trace.json"
        (attempt_root / "agent-execution.json").write_text(
            json.dumps(
                {
                    "exit_code": 0,
                    "timed_out": False,
                    "container_cleanup_status": "not_needed",
                    "trace_status": "captured",
                    "trace_redacted": False,
                    "trace_path": trace_path,
                    "final_message_sha256": sha256_bytes(final_message.encode("utf-8")),
                }
            ),
            encoding="utf-8",
        )
        (attempt_root / "agent-trace.json").write_text(
            json.dumps(
                {
                    "format": "codex_exec_jsonl",
                    "status": "captured",
                    "turn_completed": True,
                    "turn_failed": False,
                    "commands": [
                        {
                            "successful": True,
                            "skill_files_read": sorted(
                                {row["skill"] for row in scenario["required_artifacts"]}
                            ),
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        attempt = {
            "attempt_id": attempt_id,
            "status": status,
            "agent_exit_code": 0,
            "agent_timed_out": False,
            "agent_trace_status": "captured",
            "agent_trace_path": trace_path,
            "agent_isolation": {"status": "verified"},
            "workspace_integrity": {"unchanged": True},
            "runtime_status": {
                "verifier": runtime_status,
                "workflow_runtime": runtime_status,
            },
            "judge_status": judge_status
            if judge_status is not None
            else "needs_review"
            if status == "needs_review"
            else "pass",
            "artifact_index_status": validation["status"],
            "saved_result_root": attempt_id,
            "saved_output_root": f"{attempt_id}/qa-output",
        }
        (attempt_root / "attempt.json").write_text(
            json.dumps(attempt), encoding="utf-8"
        )
        return attempt

    def test_skip_test_case_design_preserves_cross_referenced_review_artifact(
        self,
    ) -> None:
        scenario = load_scenario()
        catalogue = load_fixture_catalogue()
        definition = next(
            row for row in catalogue["cases"] if row["id"] == "major-violation-001"
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            baseline_output = root / "baseline"
            self._baseline_output(baseline_output, scenario)
            index_path = baseline_output / "artifact-index.json"
            index = json.loads(index_path.read_text(encoding="utf-8"))
            case_row = next(
                row for row in index["routing"] if row["skill"] == "test-case-design"
            )
            review_artifact = next(
                artifact
                for artifact in index["artifacts"]
                if artifact["skill"] == "adversarial-review"
            )
            case_row["artifact_ids"].append(review_artifact["artifact_id"])
            index_path.write_text(
                json.dumps(index, ensure_ascii=False) + "\n", encoding="utf-8"
            )

            output, validation, _ = _prepare_fixture(
                definition=definition,
                baseline_output=baseline_output,
                fixture_root=root / "fixture",
                scenario=scenario,
            )

            mutated = json.loads(
                (output / "artifact-index.json").read_text(encoding="utf-8")
            )
            self.assertEqual(validation["status"], "needs_review")
            self.assertTrue(
                any(
                    issue["kind"] == "noncompleted_routing"
                    and issue["skill"] == "test-case-design"
                    and issue["status"] == "skipped"
                    for issue in validation["issues"]
                )
            )
            self.assertFalse(
                any(
                    issue["kind"]
                    in {
                        "routing_references_unknown_artifacts",
                        "artifact_not_linked_from_routing",
                    }
                    for issue in validation["issues"]
                )
            )
            self.assertIn(review_artifact, mutated["artifacts"])

    def _run(
        self,
        *,
        approved: bool,
        candidate: bool,
        case_id: str = "normal-workflow",
        legacy_approval: bool = False,
        mutate_baseline_after_binding: bool = False,
        stale_binding: bool = False,
        include_gate: bool = False,
        baseline_statuses: tuple[str, ...] = ("pass", "pass"),
        incomplete_workflow_route: bool = False,
        runtime_status: str = "pass",
        judge_status: str | None = None,
    ) -> dict | tuple[dict, dict, list[dict]]:
        scenario = load_scenario()
        with tempfile.TemporaryDirectory() as repository_temporary:
            repository_root = Path(repository_temporary)
            run_parent = repository_root / ".agent-eval-runs"
            run_parent.mkdir()
            with tempfile.TemporaryDirectory(dir=run_parent) as temporary:
                root = Path(temporary)
                baseline_root = root / "baseline"
                attempts = [
                    self._baseline_attempt(
                        baseline_root,
                        scenario=scenario,
                        attempt_id=f"attempt-{index:02d}",
                        status=status,
                        incomplete_workflow_route=incomplete_workflow_route,
                        runtime_status=runtime_status,
                        judge_status=judge_status
                        or (
                            "pass"
                            if incomplete_workflow_route and status == "needs_review"
                            else None
                        ),
                    )
                    for index, status in enumerate(baseline_statuses, start=1)
                ]
                attempt_one, attempt_two = attempts[:2]
                baseline_output = baseline_root / "attempt-01" / "qa-output"
                runtime_root = baseline_root / "attempt-01"
                baseline_result = baseline_root / "result.json"
                baseline_result.write_text(
                    json.dumps(
                        {
                            "profile_verification": "verified",
                            "execution_profile_fingerprint": (
                                judge_validation.profile_fingerprint(_profile())
                            ),
                            "agent_command_template": ["fake-agent"],
                            "evaluator_revision": "1" * 40,
                            "target_revision": DEFAULT_TARGET_REVISION,
                            "scenario_fingerprint": scenario["scenario_fingerprint"],
                            "attempts": attempts,
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
                selected_definition = next(
                    row for row in catalogue["cases"] if row["id"] == case_id
                )
                ordered_catalogue = {
                    **catalogue,
                    "cases": [
                        selected_definition,
                        *[row for row in catalogue["cases"] if row["id"] != case_id],
                    ],
                }
                approval = root / "approval.json"
                approval_path = None
                if approved:
                    definition = selected_definition
                    preview_root = root / "approval-preview"
                    preview_root.mkdir()
                    fixture_output, fixture_validation, final_message = (
                        _prepare_fixture(
                            definition=definition,
                            baseline_output=baseline_output,
                            fixture_root=preview_root,
                            scenario=scenario,
                        )
                    )
                    runtime = json.loads(
                        (runtime_root / "runtime-checks.json").read_text(
                            encoding="utf-8"
                        )
                    )
                    workflow = runtime["workflow_runtime"]
                    machine = {
                        "required_artifacts_present": fixture_validation["status"]
                        == "pass",
                        "workflow_runtime_can_complete": workflow[
                            "workflow_runtime_can_complete"
                        ],
                        "workflow_runtime_has_unclosed_issues": workflow[
                            "workflow_runtime_has_unclosed_issues"
                        ],
                    }
                    references = {
                        relative: b"Fixed specification reference.\n"
                        for relative in scenario["reference_paths"]
                    }
                    prompt, criteria = _fixture_prompt(
                        definition=definition,
                        scenario=scenario,
                        references=references,
                        output=fixture_output,
                        validation=fixture_validation,
                        final_message=final_message,
                        machine_summary=machine,
                    )
                    binding = _fixture_approval_binding(
                        catalogue=catalogue,
                        definition=definition,
                        scenario=scenario,
                        references=references,
                        baseline_artifact_fingerprint=(
                            _artifact_content_fingerprint(baseline_output)
                        ),
                        artifact_content_fingerprint=(
                            _artifact_content_fingerprint(fixture_output)
                        ),
                        prompt=prompt,
                        criteria=criteria,
                        normative_revision=DEFAULT_TARGET_REVISION,
                    )
                    if stale_binding:
                        binding["dataset_revision"] = "qts-judge-fixtures-v1"
                    approval_row = {
                        "case_id": definition["id"],
                        "reviewer": "test-only-fixture-reviewer",
                        "approved_at": "2026-10-22T00:00:00Z",
                        "evidence": f"{definition['references'][0]}#fixture-review",
                    }
                    if not legacy_approval:
                        approval_row["binding"] = binding
                    approval.write_text(
                        json.dumps(
                            {
                                "dataset_revision": catalogue["dataset_revision"],
                                "approvals": [approval_row],
                            }
                        ),
                        encoding="utf-8",
                    )
                    approval_path = approval
                    if mutate_baseline_after_binding:
                        changed_artifact = baseline_output / "artifact-00.md"
                        changed_artifact.write_text(
                            changed_artifact.read_text(encoding="utf-8")
                            + "Changed after approval.\n",
                            encoding="utf-8",
                        )
                profile_path = root / "profile.json"
                profile_path.write_text(json.dumps(_profile()), encoding="utf-8")

                original_judge_case = judge_validation._run_judge_case

                def actual_judge(**kwargs):
                    rating = 1 if selected_definition["expected"] == "rating_1" else 3
                    response = json.dumps(
                        {
                            "criteria": [
                                {
                                    "id": criterion,
                                    "evaluable": True,
                                    "rating": rating,
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
                    patch.object(judge_validation, "REPO_ROOT", repository_root),
                    patch.object(
                        judge_validation,
                        "load_fixture_catalogue",
                        return_value=ordered_catalogue,
                    ),
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
                if include_gate:
                    from scripts.skills.evals.agent.improve import (
                        _judge_verification_map,
                        _stable_failures,
                    )

                    verification = _judge_verification_map(
                        output / "result.json",
                        expected_evaluator_revision="1" * 40,
                        expected_target_revision=DEFAULT_TARGET_REVISION,
                        expected_profile_fingerprint=result[
                            "judge_profile_fingerprint"
                        ],
                        expected_baseline_artifact_fingerprint=(
                            _artifact_content_fingerprint(baseline_output)
                        ),
                    )
                    attempts = [
                        {
                            "attempt": {"attempt_id": f"attempt-{index}"},
                            "criteria": {
                                criterion: {"rating": 1, "status": "fail"}
                                for criterion in ("QTS-SEM-001", "QTS-SEM-002")
                            },
                        }
                        for index in (1, 2)
                    ]
                    return (
                        result,
                        verification,
                        _stable_failures(attempts, verification),
                    )
                return result

    def test_approved_fixture_and_candidate_judge_are_checked_on_independent_repeats(
        self,
    ) -> None:
        result, verification, failures = self._run(
            approved=True, candidate=True, include_gate=True
        )
        self.assertEqual(result["status"], "verified")
        self.assertEqual(result["candidate_judge_validation_status"], "verified")
        self.assertEqual(result["cases"][0]["candidate_judge_status"], "verified")
        self.assertTrue(result["cases"][0]["candidate_matches_baseline"])
        case = result["cases"][0]
        binding = case["approval"]["binding"]
        self.assertEqual(case["approval"]["binding_status"], "matched")
        self.assertEqual(binding["fixture_id"], "normal-workflow")
        self.assertEqual(binding["criteria"], case["criteria"])
        self.assertEqual(binding["expected"], case["expected"])
        self.assertEqual(binding["normative_revision"], DEFAULT_TARGET_REVISION)
        self.assertTrue(binding["fixture_definition_fingerprint"].startswith("sha256:"))
        self.assertTrue(binding["baseline_artifact_fingerprint"].startswith("sha256:"))
        self.assertTrue(binding["artifact_content_fingerprint"].startswith("sha256:"))
        self.assertTrue(binding["judge_input_fingerprint"].startswith("sha256:"))
        self.assertTrue(binding["normative_content_fingerprint"].startswith("sha256:"))
        self.assertEqual(
            [row["prompt_sha256"] for row in case["judge_runs"]],
            [binding["judge_input_fingerprint"]] * 2,
        )
        self.assertEqual(verification["QTS-SEM-001"]["status"], "judge_unverified")
        self.assertEqual(verification["QTS-SEM-002"]["status"], "judge_unverified")
        self.assertEqual(failures, [])
        for field in (
            "fixture_id",
            "fixture_definition_fingerprint",
            "baseline_artifact_fingerprint",
            "artifact_content_fingerprint",
            "judge_input_fingerprint",
            "criteria",
            "expected",
            "normative_revision",
            "normative_content_fingerprint",
        ):
            changed_binding = dict(binding)
            changed_binding[field] = "changed"
            self.assertEqual(
                _approval_binding_status({"binding": changed_binding}, binding),
                "mismatch",
                field,
            )
        bool_binding_version = dict(binding)
        bool_binding_version["binding_version"] = True
        self.assertEqual(
            _approval_binding_status({"binding": bool_binding_version}, binding),
            "mismatch",
        )

    def test_baseline_selection_skips_fail_and_prefers_a_qualified_pass(self) -> None:
        result = self._run(
            approved=False,
            candidate=False,
            baseline_statuses=("fail", "pass", "pass"),
        )
        self.assertEqual(result["baseline_attempt_id"], "attempt-02")
        self.assertEqual(result["baseline_attempt_status"], "pass")
        self.assertEqual(
            result["baseline_attempt_eligibility"], "passed_machine_checks"
        )
        self.assertEqual(
            [row["eligible"] for row in result["baseline_attempt_selection"]],
            [False, True, True],
        )

    def test_judge_validation_refuses_run_without_eligible_attempt(self) -> None:
        with self.assertRaisesRegex(AgentEvalError, "no eligible saved Agent attempt"):
            self._run(
                approved=False,
                candidate=False,
                baseline_statuses=("fail", "execution_error"),
            )

    def test_legitimate_incomplete_routing_can_be_a_needs_review_baseline(
        self,
    ) -> None:
        result = self._run(
            approved=True,
            candidate=False,
            baseline_statuses=("needs_review", "needs_review"),
            incomplete_workflow_route=True,
        )
        self.assertEqual(result["baseline_attempt_id"], "attempt-01")
        self.assertEqual(
            result["baseline_attempt_eligibility"],
            "passed_machine_checks_with_incomplete_routing",
        )
        self.assertEqual(result["cases"][0]["status"], "verified")

    def test_incomplete_routing_does_not_hide_unresolved_judge_review(self) -> None:
        with self.assertRaisesRegex(AgentEvalError, "no eligible saved Agent attempt"):
            self._run(
                approved=False,
                candidate=False,
                baseline_statuses=("needs_review", "needs_review"),
                incomplete_workflow_route=True,
                judge_status="needs_review",
            )

    def test_needs_review_baseline_with_unverified_runtime_is_rejected(self) -> None:
        with self.assertRaisesRegex(AgentEvalError, "no eligible saved Agent attempt"):
            self._run(
                approved=False,
                candidate=False,
                baseline_statuses=("needs_review", "needs_review"),
                runtime_status="evidence_unverified",
            )

    def test_needs_review_without_incomplete_routing_is_not_a_normal_baseline(
        self,
    ) -> None:
        with self.assertRaisesRegex(AgentEvalError, "no eligible saved Agent attempt"):
            self._run(
                approved=False,
                candidate=False,
                baseline_statuses=("needs_review", "needs_review"),
            )

    def test_mutation_fixture_requires_approved_normal_baseline(self) -> None:
        result = self._run(
            approved=True,
            candidate=False,
            case_id="major-violation-001",
        )
        case = result["cases"][0]
        self.assertTrue(case["judge_runs"][0]["expectation_matched"])
        self.assertEqual(case["approval"]["binding_status"], "matched")
        self.assertEqual(case["baseline_precondition"]["status"], "not_evaluated")
        self.assertEqual(case["status"], "review_pending")

    def test_baseline_fixture_precondition_requires_same_approved_baseline_and_criteria(
        self,
    ) -> None:
        mutation = next(
            row
            for row in load_fixture_catalogue()["cases"]
            if row["id"] == "major-violation-001"
        )
        baseline = {
            "case_id": "normal-workflow",
            "status": "verified",
            "criteria": ["QTS-SEM-001", "QTS-SEM-002"],
            "fixture_content_integrity_status": "verified",
            "approval": {"binding_status": "matched"},
            "approval_binding": {"baseline_artifact_fingerprint": "sha256:" + "a" * 64},
        }
        verified = _baseline_fixture_precondition(
            mutation,
            prior_cases=[baseline],
            baseline_fingerprint="sha256:" + "a" * 64,
        )
        self.assertEqual(verified["status"], "verified")
        self.assertEqual(
            _baseline_fixture_precondition(
                mutation,
                prior_cases=[{**baseline, "status": "review_pending"}],
                baseline_fingerprint="sha256:" + "a" * 64,
            )["status"],
            "review_pending",
        )
        self.assertEqual(
            _baseline_fixture_precondition(
                mutation,
                prior_cases=[baseline],
                baseline_fingerprint="sha256:" + "b" * 64,
            )["reason"],
            "normal_baseline_binding_mismatch",
        )
    def test_pixel_parity_fixture_targets_the_unresolved_oracle_without_cart_overlap(
        self,
    ) -> None:
        catalogue = load_fixture_catalogue()
        definition = next(
            row for row in catalogue["cases"] if row["id"] == "major-violation-003"
        )

        self.assertEqual(catalogue["dataset_revision"], "qts-judge-fixtures-v2")
        self.assertEqual(definition["criteria"], ["QTS-SEM-003"])
        self.assertEqual(definition["approval_status"], "pending_human_review")
        self.assertFalse(
            any(
                row["id"].startswith("major-violation-")
                and "QTS-SEM-008" in row["criteria"]
                for row in catalogue["cases"]
            )
        )
        self.assertEqual(
            set(definition["references"]),
            {
                "docs/spec/README.md",
                "docs/spec/features/checkout-and-payment.md",
                "docs/spec/unresolved-specifications.md",
            },
        )
        self.assertEqual(
            judge_validation.canonical_fingerprint(
                {
                    "splits": catalogue["splits"],
                    "cases": [
                        row
                        for row in catalogue["cases"]
                        if row["id"] != "major-violation-003"
                    ],
                }
            ),
            "sha256:6b62add8809319e487322aa639fe03a04705726fffe352bcb978027b49b11424",
        )
        self.assertNotEqual(
            judge_validation.canonical_fingerprint(catalogue),
            "sha256:a747ad74b4ec383afc4427352e349243511861e99460e2af52d1ae2378524da6",
        )
        self.assertNotEqual(
            judge_validation.canonical_fingerprint(definition),
            "sha256:e6b7f334eb3e3057321a445230725de9d25ca2057312d0f37e759c85ff70fd49",
        )

        mutation = judge_validation._MUTATIONS[definition["mutation"]]
        for phrase in (
            "Cross-platform visual parity beyond shared behavior",
            "Web and Native Checkout",
            "pixel-for-pixel visual parity",
            "Navigation",
            "Typography",
            "must FAIL",
        ):
            self.assertIn(phrase, mutation)
        for stale_cart_claim in ("stale Cart", "Cart Version", "price mismatch"):
            self.assertNotIn(stale_cart_claim, mutation)
        self.assertNotIn(
            "promote-unresolved-specification-to-confirmed-oracle",
            judge_validation._MUTATIONS,
        )

        scenario = load_scenario()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            baseline_output = root / "baseline"
            self._baseline_output(baseline_output, scenario)
            fixture_output, validation, _ = _prepare_fixture(
                definition=definition,
                baseline_output=baseline_output,
                fixture_root=root / "fixture",
                scenario=scenario,
            )
            self.assertEqual(validation["status"], "pass")
            index = json.loads(
                (fixture_output / "artifact-index.json").read_text(encoding="utf-8")
            )
            mutated = next(
                row
                for row in index["artifacts"]
                if row["kind"] in {"test-requirement", "spec-analysis"}
            )
            content = (fixture_output / mutated["path"]).read_text(encoding="utf-8")
            self.assertIn(
                "Cross-platform visual parity beyond shared behavior", content
            )
            self.assertIn("Navigation", content)
            self.assertIn("Typography", content)
            self.assertIn("pixel-for-pixel", content)
            self.assertIn("must FAIL", content)
            self.assertNotIn("stale Cart", content)

    def test_pixel_parity_fixture_run_requires_fresh_human_approval(self) -> None:
        unapproved = self._run(
            approved=False,
            candidate=False,
            case_id="major-violation-003",
        )
        case = unapproved["cases"][0]
        self.assertEqual(unapproved["dataset_revision"], "qts-judge-fixtures-v2")
        self.assertTrue(case["judge_runs"][0]["expectation_matched"])
        self.assertEqual(case["approval"]["status"], "pending_human_review")
        self.assertEqual(case["approval"]["binding_status"], "missing")
        self.assertEqual(case["status"], "review_pending")

        stale_approval = self._run(
            approved=True,
            candidate=False,
            case_id="major-violation-003",
            stale_binding=True,
        )["cases"][0]
        self.assertTrue(stale_approval["judge_runs"][0]["expectation_matched"])
        self.assertEqual(stale_approval["approval"]["binding_status"], "mismatch")
        self.assertNotEqual(
            stale_approval["fixture_fingerprint"],
            judge_validation.canonical_fingerprint(
                stale_approval["approval"]["binding"]
            ),
        )
        self.assertEqual(stale_approval["approval"]["status"], "review_pending")
        self.assertEqual(stale_approval["status"], "review_pending")

    def test_unapproved_fixture_remains_pending_even_when_fake_judge_matches(
        self,
    ) -> None:
        result = self._run(approved=False, candidate=False)
        self.assertEqual(result["status"], "review_pending")
        self.assertEqual(result["cases"][0]["status"], "review_pending")

    def test_legacy_approval_is_unbound_and_remains_pending(self) -> None:
        result = self._run(approved=True, candidate=False, legacy_approval=True)
        case = result["cases"][0]
        self.assertTrue(case["judge_runs"][0]["expectation_matched"])
        self.assertEqual(case["approval"]["binding_status"], "legacy_unbound")
        self.assertEqual(case["approval"]["status"], "review_pending")
        self.assertEqual(case["status"], "review_pending")

    def test_tampered_attempt_artifact_is_rejected_in_favor_of_intact_attempt(
        self,
    ) -> None:
        result = self._run(
            approved=True,
            candidate=False,
            mutate_baseline_after_binding=True,
        )
        case = result["cases"][0]
        self.assertTrue(case["judge_runs"][0]["expectation_matched"])
        self.assertEqual(result["baseline_attempt_id"], "attempt-02")
        self.assertEqual(case["approval"]["binding_status"], "matched")
        self.assertEqual(case["status"], "verified")

    def test_baseline_attempt_rejects_manifest_numeric_type_confusion(self) -> None:
        scenario = load_scenario()
        mutations = (
            ("schema_version", lambda manifest: manifest.update(schema_version=True)),
            (
                "file_size",
                lambda manifest: manifest["files"][0].update(
                    size=float(manifest["files"][0]["size"])
                ),
            ),
        )
        for label, mutate in mutations:
            with self.subTest(label=label), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                attempt = self._baseline_attempt(
                    root,
                    scenario=scenario,
                    attempt_id="attempt-01",
                )
                manifest_path = (
                    root / "attempt-01" / "qa-output" / "artifact-manifest.json"
                )
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                mutate(manifest)
                manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

                eligible, reason, _ = _baseline_attempt_eligibility(
                    attempt, run_root=root, scenario=scenario
                )

                self.assertFalse(eligible)
                self.assertEqual(reason, "saved_output_manifest_not_verified")

    def test_baseline_attempt_rejects_output_from_another_attempt(self) -> None:
        scenario = load_scenario()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            attempt = self._baseline_attempt(
                root, scenario=scenario, attempt_id="attempt-01"
            )
            other_attempt = self._baseline_attempt(
                root, scenario=scenario, attempt_id="attempt-02"
            )
            attempt["saved_output_root"] = other_attempt["saved_output_root"]
            (root / "attempt-01" / "attempt.json").write_text(
                json.dumps(attempt), encoding="utf-8"
            )

            eligible, reason, _ = _baseline_attempt_eligibility(
                attempt, run_root=root, scenario=scenario
            )

            self.assertFalse(eligible)
            self.assertEqual(reason, "saved_attempt_paths_not_verified")

    def test_fixture_manifest_is_rebuilt_after_mutated_artifact_body(self) -> None:
        scenario = load_scenario()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            baseline_output = root / "baseline"
            self._baseline_output(baseline_output, scenario)
            (baseline_output / "artifact-manifest.json").write_text(
                '{"stale": true}\n', encoding="utf-8"
            )
            definition = next(
                row
                for row in load_fixture_catalogue()["cases"]
                if row["id"] == "major-violation-006"
            )
            output, validation, _ = _prepare_fixture(
                definition=definition,
                baseline_output=baseline_output,
                fixture_root=root / "fixture",
                scenario=scenario,
            )
            manifest = json.loads(
                (output / "artifact-manifest.json").read_text(encoding="utf-8")
            )
            self.assertEqual(manifest, build_artifact_manifest(output, validation))
            self.assertNotIn(
                "artifact-manifest.json", {row["path"] for row in manifest["files"]}
            )
            index = json.loads(
                (output / "artifact-index.json").read_text(encoding="utf-8")
            )
            test_case = next(
                row for row in index["artifacts"] if row["kind"] == "test-case"
            )
            self.assertIn(
                "Inventory is decremented and purchase history is created",
                (output / test_case["path"]).read_text(encoding="utf-8"),
            )


if __name__ == "__main__":
    unittest.main()
