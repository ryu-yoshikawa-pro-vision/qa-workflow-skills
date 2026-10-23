from __future__ import annotations

import json
import os
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

from scripts.skills.evals.agent import run
from scripts.skills.evals.agent.common import atomic_write_text
from scripts.skills.evals.agent.executor import ExecutionResult
from scripts.skills.evals.agent.tests.test_judge_validation import _profile


class CommonRunnerTests(unittest.TestCase):
    def _run(
        self,
        *,
        link=None,
        failure=None,
        judge_status=None,
        race_save=False,
        save_failure=False,
    ):
        run_output_parent = run.REPO_ROOT / ".agent-eval-runs"
        run_output_parent.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=run_output_parent) as temporary:
            root = Path(temporary)
            output = root / "run"
            sentinel = root / "dummy-source-sentinel"
            sentinel.write_text("unchanged", encoding="utf-8")
            dangling = root / "must-not-be-created"
            agent_output_roots = []
            profile = _profile()
            if judge_status:
                profile["judge"].update(
                    {
                        "cli_version": "codex-cli 0.163.0",
                        "sandbox_policy": "read-only",
                    }
                )
            case = run._load_semantic_cases("test-case-design", "TC-SEM-001")[0]

            def package(_root, revision, destination):
                skill = destination / "skills" / case["skill"]
                skill.mkdir(parents=True)
                (skill / "SKILL.md").write_text("fake skill", encoding="utf-8")
                return {"revision": revision, "skills": [case["skill"]], "files": []}

            def execute(argv, *, cwd, **kwargs):
                if "judge-workspaces" in cwd.parts:
                    sidecar = cwd / "launcher-observations.json"
                    if judge_status == "invalid":
                        sidecar.write_text("invalid json", encoding="utf-8")
                    elif judge_status in {"tool", "completed"}:
                        sidecar.write_text(
                            json.dumps(
                                {
                                    "protocol": "codex_judge_docker_launcher_v1",
                                    "status": "completed",
                                    "auth_mode": "temporary_auth_file",
                                    "web_search_enabled": False,
                                    "tool_policy": "no_cli_tools_or_mcp_configured",
                                    "image": {"image_id": "sha256:" + "a" * 64},
                                    "docker_exit_code": 0,
                                    "jsonl": {
                                        "status": "captured",
                                        "tool_use_detected": judge_status == "tool",
                                    },
                                }
                            ),
                            encoding="utf-8",
                        )
                    return ExecutionResult(0, "{}", None, "empty", False, 0.01)
                mount = next(
                    token
                    for token in argv
                    if "target=/workspace/.qa-eval-output" in token
                )
                mount_root = Path(mount.split("source=", 1)[1].split(",", 1)[0])
                agent_output_roots.append(mount_root)
                if link == "parent":
                    (mount_root / "linked-parent").symlink_to(
                        sentinel.parent, target_is_directory=True
                    )
                for name in ("output.md", "agent.stderr.log"):
                    path = mount_root / name
                    if link and link != "parent":
                        destination = dangling if link == "dangling" else sentinel
                        path.symlink_to(
                            os.path.relpath(destination, mount_root)
                            if link == "relative"
                            else destination
                        )
                    else:
                        path.write_text("old output", encoding="utf-8")
                return ExecutionResult(
                    1 if failure else 0,
                    "candidate",
                    "safe stderr",
                    "captured",
                    failure == "timeout",
                    0.01,
                    "failed" if failure == "cleanup" else "succeeded",
                )

            def grade(**kwargs):
                self.assertEqual(
                    kwargs["output_path"].read_text(encoding="utf-8"), "candidate"
                )
                return {"status": "pass", "grade": {"verdict": "pass"}}, []

            with ExitStack() as stack:
                for name, value in {
                    "assert_clean_checkout": "1" * 40,
                    "resolve_commit": "1" * 40,
                    "load_execution_profile": profile,
                    "verify_profile_evidence": True,
                    "verify_agent_docker_command": {"status": "verified"},
                    "verify_judge_docker_command": {"status": "verified"},
                    "_load_semantic_cases": [case],
                }.items():
                    stack.enter_context(patch.object(run, name, return_value=value))
                stack.enter_context(
                    patch.object(run, "create_skill_workspace", side_effect=package)
                )
                stack.enter_context(
                    patch.object(run, "run_command", side_effect=execute)
                )
                if save_failure:
                    original_write_text = run.atomic_write_text

                    def fail_output_save(path, content):
                        if Path(path).name == "output.md":
                            raise OSError("simulated result save failure")
                        original_write_text(path, content)

                    stack.enter_context(
                        patch.object(
                            run,
                            "atomic_write_text",
                            side_effect=fail_output_save,
                        )
                    )
                if race_save:
                    original_replace = os.replace

                    def replace_after_symlink(source, destination):
                        destination = Path(destination)
                        if destination.name in {"output.md", "agent.stderr.log"}:
                            destination.symlink_to(sentinel)
                        original_replace(source, destination)

                    stack.enter_context(
                        patch(
                            "scripts.skills.evals.agent.common.os.replace",
                            side_effect=replace_after_symlink,
                        )
                    )
                if judge_status:
                    stack.enter_context(
                        patch.object(
                            run,
                            "judge_launcher_argv_for_profile",
                            return_value=["fake-judge"],
                        )
                    )
                    stack.enter_context(
                        patch.object(
                            run,
                            "normalize_judge_response",
                            return_value={"verdict": "pass"},
                        )
                    )
                else:
                    stack.enter_context(
                        patch.object(run, "_render_grade", side_effect=grade)
                    )
                exit_code = run.run(
                    [
                        "--suite",
                        "semantic",
                        "--skill",
                        case["skill"],
                        "--eval-id",
                        case["id"],
                        "--skill-revision",
                        "1" * 40,
                        "--execution-profile",
                        str(root / "profile.json"),
                        "--output-root",
                        str(output),
                        "--agent-name",
                        "fake-agent",
                        "--agent-model",
                        "fake-model",
                        "--agent-command",
                        "docker",
                        "run",
                        "--rm",
                        "--read-only",
                        "--mount",
                        "type=bind,source={output_root},target=/workspace/.qa-eval-output",
                        "fake-image",
                        "agent",
                    ]
                )
            saved = json.loads((output / "result.json").read_text(encoding="utf-8"))
            if judge_status and judge_status != "completed":
                saved_attempt = saved["attempts"][0]
                self.assertIn("grade", saved_attempt)
                saved_grade = json.loads(
                    (output / saved_attempt["grade"]["path"]).read_text(
                        encoding="utf-8"
                    )
                )
                self.assertEqual(saved_grade["status"], "needs_review")
                self.assertEqual(saved_grade["reason"], "judge_evidence_unverified")
                self.assertEqual(saved_attempt["reason"], saved_grade["reason"])
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "unchanged")
            self.assertFalse(dangling.exists())
            self.assertEqual(len(agent_output_roots), 1)
            agent_output_root = agent_output_roots[0]
            self.assertEqual(agent_output_root.name, "agent-output")
            if "output" in saved["attempts"][0]:
                result_output = output / saved["attempts"][0]["output"]["path"]
                self.assertEqual(result_output.parent, agent_output_root.parent)
                self.assertNotEqual(result_output.parent, agent_output_root)
                self.assertEqual(result_output.read_text(encoding="utf-8"), "candidate")
            return exit_code, saved["attempts"][0]

    def test_normal_output_is_saved(self):
        exit_code, attempt = self._run()
        self.assertEqual(exit_code, 0, attempt)

    @unittest.skipUnless(os.name == "posix", "requires Linux symlink semantics")
    def test_host_result_writes_do_not_follow_agent_links(self):
        for link in ("relative", "absolute", "dangling", "parent"):
            with self.subTest(link=link):
                exit_code, attempt = self._run(link=link)
                self.assertEqual(exit_code, 1, attempt)
                self.assertEqual(attempt["status"], "needs_review")
                self.assertEqual(attempt["agent_output_status"], "evidence_unverified")

    @unittest.skipUnless(os.name == "posix", "requires Linux symlink semantics")
    def test_host_result_saves_after_destination_is_replaced(self):
        exit_code, attempt = self._run(race_save=True)
        self.assertEqual(exit_code, 0, attempt)
        self.assertEqual(attempt["status"], "pass")

    def test_result_save_failure_is_recorded(self):
        exit_code, attempt = self._run(save_failure=True)
        self.assertEqual(exit_code, 2, attempt)
        self.assertEqual(attempt["status"], "execution error")
        self.assertIn("simulated result save failure", attempt["reason"])

    @unittest.skipUnless(os.name == "posix", "requires Linux symlink semantics")
    def test_destination_swapped_before_atomic_replace_cannot_escape_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / "output"
            output.mkdir()
            sentinel = root / "dummy-source-sentinel"
            sentinel.write_text("unchanged", encoding="utf-8")
            original_replace = os.replace

            def replace(source, destination):
                Path(destination).symlink_to(sentinel)
                original_replace(source, destination)

            with patch(
                "scripts.skills.evals.agent.common.os.replace", side_effect=replace
            ):
                atomic_write_text(output / "final-message.md", "result")
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "unchanged")
            self.assertEqual(
                (output / "final-message.md").read_text(encoding="utf-8"), "result"
            )

    def test_timeout_and_cleanup_failure_are_recorded(self):
        for failure in ("timeout", "cleanup"):
            with self.subTest(failure=failure):
                exit_code, attempt = self._run(failure=failure)
                self.assertEqual(exit_code, 2, attempt)
                self.assertEqual(attempt["status"], "execution error")

    @unittest.skipUnless(os.name == "posix", "requires Linux symlink semantics")
    def test_timeout_cleanup_does_not_follow_agent_output_links(self):
        for link in ("relative", "absolute", "dangling", "parent"):
            with self.subTest(link=link):
                exit_code, attempt = self._run(link=link, failure="timeout")
                self.assertEqual(exit_code, 2, attempt)
                self.assertEqual(attempt["status"], "execution error")

    def test_unverified_judge_evidence_keeps_reason_and_judge_runs(self):
        for status in ("missing", "invalid", "tool", "completed"):
            with self.subTest(status=status):
                exit_code, attempt = self._run(judge_status=status)
                self.assertEqual(exit_code, 0 if status == "completed" else 1, attempt)
                self.assertEqual(
                    attempt["status"],
                    "pass" if status == "completed" else "needs_review",
                )
                self.assertEqual(len(attempt["judge"]), 1)
                if status != "completed":
                    self.assertEqual(attempt["reason"], "judge_evidence_unverified")


if __name__ == "__main__":
    unittest.main()
