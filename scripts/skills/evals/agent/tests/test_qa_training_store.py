from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.skills.evals.agent import qa_training_store
from scripts.skills.evals.agent.executor import ExecutionResult
from scripts.skills.evals.agent.qa_training_store import (
    DEFAULT_TARGET_REVISION,
    load_scenario,
    run_independent_judges,
    validate_artifact_index,
)


class QATrainingStoreTests(unittest.TestCase):
    def _valid_output(self, root: Path, scenario: dict) -> dict:
        artifacts = []
        routing = []
        for index, required in enumerate(scenario["required_artifacts"]):
            artifact_id = f"artifact-{index:02d}"
            name = f"artifact-{index:02d}.md"
            (root / name).write_text(
                f"QA artifact for {required['skill']}\n", encoding="utf-8"
            )
            artifacts.append({**required, "artifact_id": artifact_id, "path": name})
            routing.append(
                {
                    "skill": required["skill"],
                    "scope": required["scope"],
                    "status": "executed",
                    "reason": "Required analysis and design output was produced.",
                    "artifact_ids": [artifact_id],
                }
            )
        (root / "artifact-index.json").write_text(
            json.dumps(
                {"schema_version": 1, "artifacts": artifacts, "routing": routing}
            ),
            encoding="utf-8",
        )
        return {"artifacts": artifacts, "routing": routing}

    def test_artifact_registration_is_checked_against_files_and_routing(self) -> None:
        scenario = load_scenario()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._valid_output(root, scenario)
            self.assertEqual(validate_artifact_index(root, scenario)["status"], "pass")
            index = json.loads(
                (root / "artifact-index.json").read_text(encoding="utf-8")
            )
            index["routing"][0]["artifact_ids"] = []
            (root / "artifact-index.json").write_text(
                json.dumps(index), encoding="utf-8"
            )
            result = validate_artifact_index(root, scenario)
        self.assertEqual(result["status"], "needs_review")
        self.assertIn(
            "artifact_not_linked_from_routing",
            {row["kind"] for row in result["issues"]},
        )

    def test_missing_index_and_missing_file_are_distinct(self) -> None:
        scenario = load_scenario()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.assertEqual(
                validate_artifact_index(root, scenario)["reason"],
                "artifact_index_missing_or_unsafe",
            )
            output = self._valid_output(root, scenario)
            (root / output["artifacts"][0]["path"]).unlink()
            result = validate_artifact_index(root, scenario)
        self.assertIn(
            "artifact_missing_or_symlink", {row["kind"] for row in result["issues"]}
        )

    def test_two_independent_fake_judges_receive_separate_evidence(self) -> None:
        scenario = load_scenario()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / "qa-output"
            output.mkdir()
            validation = self._valid_output(output, scenario)
            validation["status"] = "pass"
            validation["issues"] = []
            target = root / "target"
            for relative in scenario["reference_paths"]:
                path = target / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("Fixed reference fixture.\n", encoding="utf-8")
            validation["routing"][0]["reason"] = "ROUTING-SECRET-SENTINEL"
            prompts = []

            def fake_judge(
                argv, *, input_text, cwd, timeout_seconds, timeout_cleanup_argv=None
            ):
                prompts.append(input_text)
                requested = [
                    f"QTS-SEM-{number:03d}"
                    for number in ((1, 2) if len(prompts) == 1 else range(3, 11))
                ]
                response = {
                    "criteria": [
                        {
                            "id": criterion,
                            "evaluable": True,
                            "rating": 3,
                            "reason": "The fixed evidence supports this result.",
                            "evidence": ["artifact-00.md"],
                        }
                        for criterion in requested
                    ]
                }
                return ExecutionResult(
                    0, json.dumps(response), None, "empty", False, 0.01
                )

            profile = {
                "judge": {
                    "command_argv": [
                        "docker",
                        "run",
                        "--rm",
                        "--read-only",
                        "--network",
                        "bridge",
                        "python:3.11",
                        "codex",
                        "exec",
                    ],
                    "timeout_seconds": 30,
                }
            }
            with patch(
                "scripts.skills.evals.agent.qa_training_store.run_command",
                side_effect=fake_judge,
            ):
                result = run_independent_judges(
                    scenario=scenario,
                    target_root=target,
                    output_root=output,
                    validation=validation,
                    final_message="FINAL-SECRET-SENTINEL",
                    machine_summary={
                        "workflow_runtime_can_complete": True,
                        "workflow_runtime_has_unclosed_issues": False,
                        "required_artifacts_present": True,
                    },
                    profile=profile,
                    judge_root=root / "fake-judge-workspaces",
                )
        self.assertEqual(result["status"], "pass")
        self.assertEqual(len(prompts), 2)
        self.assertIn("ROUTING-SECRET-SENTINEL", prompts[0])
        self.assertIn("FINAL-SECRET-SENTINEL", prompts[0])
        self.assertNotIn("ROUTING-SECRET-SENTINEL", prompts[1])
        self.assertNotIn("FINAL-SECRET-SENTINEL", prompts[1])
        self.assertEqual(len(result["normalized"]["criteria"]), 10)

    def test_invalid_judge_response_and_failed_cleanup_never_pass(self) -> None:
        scenario = load_scenario()
        for mode, expected_status in (
            ("invalid", "needs_review"),
            ("cleanup", "execution_error"),
        ):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                output = root / "qa-output"
                output.mkdir()
                validation = self._valid_output(output, scenario)
                validation["status"] = "pass"
                validation["issues"] = []
                target = root / "target"
                for relative in scenario["reference_paths"]:
                    path = target / relative
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text("Fixed reference fixture.\n", encoding="utf-8")
                judge_root = root / "judge-workspaces"
                judge_root.mkdir()

                def fake_judge(
                    _argv,
                    *,
                    input_text,
                    cwd,
                    timeout_seconds,
                    timeout_cleanup_argv=None,
                ):
                    if mode == "invalid":
                        response = "{}"
                        cleanup = "empty"
                    else:
                        requested = (
                            [f"QTS-SEM-{number:03d}" for number in (1, 2)]
                            if cwd.name == "workflow"
                            else [f"QTS-SEM-{number:03d}" for number in range(3, 11)]
                        )
                        response = json.dumps(
                            {
                                "criteria": [
                                    {
                                        "id": criterion,
                                        "evaluable": True,
                                        "rating": 3,
                                        "reason": "Supported.",
                                        "evidence": ["artifact-00.md"],
                                    }
                                    for criterion in requested
                                ]
                            }
                        )
                        cleanup = "failed"
                    return ExecutionResult(
                        0, response, None, "empty", False, 0.01, cleanup
                    )

                profile = {
                    "judge": {
                        "command_argv": [
                            "docker",
                            "run",
                            "--rm",
                            "--read-only",
                            "python:3.11",
                            "judge",
                        ],
                        "timeout_seconds": 30,
                    }
                }
                with patch(
                    "scripts.skills.evals.agent.qa_training_store.run_command",
                    side_effect=fake_judge,
                ):
                    result = qa_training_store.run_independent_judges(
                        scenario=scenario,
                        target_root=target,
                        output_root=output,
                        validation=validation,
                        final_message="Workflow response.",
                        machine_summary={"required_artifacts_present": True},
                        profile=profile,
                        judge_root=judge_root,
                    )
                self.assertEqual(result["status"], expected_status)
                self.assertIsNone(result["normalized"])

    def test_fake_agent_and_fake_judge_complete_the_two_attempt_runner(self) -> None:
        scenario = load_scenario()
        run_parent = qa_training_store.REPO_ROOT / ".agent-eval-runs"
        created_parent = not run_parent.exists()
        run_parent.mkdir(exist_ok=True)
        try:
            with tempfile.TemporaryDirectory(dir=run_parent) as temporary:
                output_root = Path(temporary) / "run"
                target_source = Path(temporary) / "target-source"
                target_source.mkdir()
                for relative in scenario["reference_paths"]:
                    reference = target_source / relative
                    reference.parent.mkdir(parents=True, exist_ok=True)
                    reference.write_text("Fixed reference fixture.\n", encoding="utf-8")
                evaluator_sha = "1" * 40
                profile = {
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
                package_sha = "sha256:" + "a" * 64

                def fake_package(_root, revision, destination):
                    skills_root = destination / "skills"
                    skills_root.mkdir(parents=True)
                    (skills_root / "qa-workflow").mkdir()
                    (skills_root / "qa-workflow" / "SKILL.md").write_text(
                        "fake", encoding="utf-8"
                    )
                    return {
                        "revision": revision,
                        "skills": ["qa-workflow"],
                        "files": [],
                        "package_fingerprint": package_sha,
                    }

                def fake_prepare(*, destination, source_revision, **kwargs):
                    destination.mkdir(parents=True)
                    (destination / ".qa-eval-output").mkdir()
                    return {
                        "source_revision": source_revision,
                        "synthetic_baseline_revision": "2" * 40,
                        "source_manifest_fingerprint": package_sha,
                        "baseline_manifest": {},
                        "baseline_manifest_fingerprint": package_sha,
                    }

                def fake_agent(_argv, *, cwd, **kwargs):
                    qa_root = cwd / ".qa-eval-output"
                    qa_root.mkdir(exist_ok=True)
                    self._valid_output(qa_root, scenario)
                    return ExecutionResult(
                        0, "Agent completed the workflow.", None, "empty", False, 0.01
                    )

                fake_profile = profile
                with (
                    patch.object(
                        qa_training_store,
                        "assert_clean_checkout",
                        side_effect=[evaluator_sha, DEFAULT_TARGET_REVISION],
                    ),
                    patch.object(
                        qa_training_store,
                        "resolve_commit",
                        side_effect=lambda _root, revision: revision,
                    ),
                    patch.object(
                        qa_training_store,
                        "load_execution_profile",
                        return_value=fake_profile,
                    ),
                    patch.object(
                        qa_training_store, "verify_profile_evidence", return_value=True
                    ),
                    patch.object(
                        qa_training_store,
                        "create_skill_workspace",
                        side_effect=fake_package,
                    ),
                    patch.object(
                        qa_training_store,
                        "prepare_sanitized_target",
                        side_effect=fake_prepare,
                    ),
                    patch.object(
                        qa_training_store,
                        "verify_workspace_unchanged",
                        return_value={
                            "unchanged": True,
                            "changed_paths": [],
                            "commit_count": 1,
                            "remotes": [],
                        },
                    ),
                    patch.object(
                        qa_training_store,
                        "verify_agent_docker_command",
                        return_value={"status": "verified"},
                    ),
                    patch.object(
                        qa_training_store,
                        "evaluate_runtime_captures",
                        return_value={"status": "pass", "captures": []},
                    ),
                    patch.object(
                        qa_training_store,
                        "evaluate_workflow_runtime_capture",
                        return_value={
                            "status": "pass",
                            "workflow_runtime_can_complete": True,
                            "workflow_runtime_has_unclosed_issues": False,
                        },
                    ),
                    patch.object(
                        qa_training_store,
                        "run_independent_judges",
                        return_value={
                            "status": "pass",
                            "runs": [],
                            "normalized": {"verdict": "pass"},
                        },
                    ),
                    patch.object(
                        qa_training_store, "run_command", side_effect=fake_agent
                    ),
                ):
                    exit_code = qa_training_store.run(
                        [
                            "--target-root",
                            str(target_source),
                            "--skill-revision",
                            evaluator_sha,
                            "--execution-profile",
                            str(Path(temporary) / "profile.json"),
                            "--verifier-image",
                            "sha256:" + "b" * 64,
                            "--output-root",
                            str(output_root),
                            "--repeat",
                            "2",
                            "--agent-command",
                            "docker",
                            "run",
                            "--rm",
                            "--read-only",
                            "python:3.11",
                            "agent",
                            "exec",
                        ]
                    )
                saved = json.loads(
                    (output_root / "result.json").read_text(encoding="utf-8")
                )
        finally:
            if created_parent:
                try:
                    run_parent.rmdir()
                except OSError:
                    pass
        self.assertEqual(exit_code, 0, saved)
        self.assertEqual(saved["status"], "pass")
        self.assertEqual(len(saved["attempts"]), 2)
        self.assertTrue(all(row["status"] == "pass" for row in saved["attempts"]))


if __name__ == "__main__":
    unittest.main()
