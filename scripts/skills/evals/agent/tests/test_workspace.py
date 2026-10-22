from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.skills.evals.agent.common import (
    AgentEvalError,
    canonical_fingerprint,
    prepare_run_output_root,
)
from scripts.skills.evals.agent.isolation_probe import _live_mount_probe
from scripts.skills.evals.agent.workspace import (
    profile_fingerprint,
    verify_agent_docker_command,
    verify_judge_docker_command,
    verify_profile_evidence,
)


class WorkspaceIsolationTests(unittest.TestCase):
    def test_profile_evidence_is_bound_to_command_and_evaluator_revision(self) -> None:
        profile = {
            "agent": {"skill_roots": ["/workspace/.agents/skills"]},
            "judge": {"cwd": "isolated", "command_argv": ["docker", "run", "judge"]},
            "isolation": {"agent_read_roots": ["/workspace"]},
            "verification": {"status": "verified", "evidence_path": "isolation.json"},
        }
        agent_command = ["docker", "run", "--read-only", "agent"]
        checks = {
            "evaluator_read_denied": True,
            "source_write_denied": True,
            "extra_tools_disabled": True,
            "mounts_reviewed": True,
        }
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "isolation.json").write_text(
                json.dumps(
                    {
                        "status": "verified",
                        "probe": "scripts/skills/evals/agent/isolation_probe.py",
                        "profile_fingerprint": profile_fingerprint(profile),
                        "agent_command_fingerprint": canonical_fingerprint(
                            agent_command
                        ),
                        "judge_command_fingerprint": canonical_fingerprint(
                            profile["judge"]["command_argv"]
                        ),
                        "evaluator_revision": "a" * 40,
                        "checks": checks,
                    }
                ),
                encoding="utf-8",
            )
            with patch(
                "scripts.skills.evals.agent.workspace.assert_clean_checkout",
                return_value="a" * 40,
            ):
                self.assertTrue(
                    verify_profile_evidence(
                        profile, root, agent_command_argv=agent_command
                    )
                )
                with self.assertRaises(AgentEvalError):
                    verify_profile_evidence(
                        profile, root, agent_command_argv=agent_command + ["different"]
                    )
            with patch(
                "scripts.skills.evals.agent.workspace.assert_clean_checkout",
                return_value="b" * 40,
            ):
                with self.assertRaises(AgentEvalError):
                    verify_profile_evidence(
                        profile, root, agent_command_argv=agent_command
                    )

    def test_live_probe_checks_sentinel_control_and_agent_mounts(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            workspace = root / "workspace"
            output = workspace / ".qa-eval-output"
            sentinel = root / "sentinel.txt"
            workspace.mkdir()
            output.mkdir()
            sentinel.write_text("isolation-sentinel", encoding="utf-8")
            argv = [
                "docker",
                "run",
                "--rm",
                "--read-only",
                "--network",
                "bridge",
                "--workdir",
                "/workspace",
                "--mount",
                f"type=bind,source={workspace},target=/workspace,readonly",
                "--mount",
                f"type=bind,source={output},target=/workspace/.qa-eval-output",
                "python:3.11",
                "codex",
                "exec",
                "-",
            ]
            completed = [
                subprocess.CompletedProcess([], 0, b"", b""),
                subprocess.CompletedProcess([], 0, b"isolation-probe:ok\n", b""),
            ]
            with patch(
                "scripts.skills.evals.agent.isolation_probe.subprocess.run",
                side_effect=completed,
            ) as run:
                result = _live_mount_probe(argv, evaluator_sentinel=sentinel)
        self.assertEqual(result["status"], "verified")
        self.assertTrue(result["checks"]["sentinel_control_readable"])
        self.assertTrue(result["checks"]["evaluator_sentinel_unreadable"])
        control_argv, agent_argv = (call.args[0] for call in run.call_args_list)
        self.assertTrue(any(str(sentinel) in item for item in control_argv))
        self.assertNotIn(str(sentinel), agent_argv)
        self.assertIn("/workspace/.agent-eval-source-write-probe", agent_argv[-1])

    def test_run_output_allows_only_isolation_evidence_before_evaluation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repository = Path(temporary)
            output = repository / ".agent-eval-runs" / "run-001"
            output.mkdir(parents=True)
            (output / "isolation.json").write_text("{}\n", encoding="utf-8")
            self.assertEqual(
                prepare_run_output_root(
                    output,
                    repository_root=repository,
                    evidence_relative_path="isolation.json",
                ),
                output / "isolation.json",
            )
            (output / "unexpected.json").write_text("{}\n", encoding="utf-8")
            with self.assertRaises(AgentEvalError):
                prepare_run_output_root(
                    output,
                    repository_root=repository,
                    evidence_relative_path="isolation.json",
                )

    def test_run_output_rejects_external_path_and_missing_evidence_path(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repository = Path(temporary) / "repo"
            repository.mkdir()
            with self.assertRaises(AgentEvalError):
                prepare_run_output_root(
                    repository / "outside" / "run",
                    repository_root=repository,
                    evidence_relative_path="isolation.json",
                )
            with self.assertRaises(AgentEvalError):
                prepare_run_output_root(
                    repository / ".agent-eval-runs" / "run-001",
                    repository_root=repository,
                    evidence_relative_path=None,
                )

    def test_agent_container_requires_read_only_workspace_and_single_output_mount(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            workspace = root / "workspace"
            output = root / "output"
            evaluator = root / "evaluator"
            workspace.mkdir()
            output.mkdir()
            evaluator.mkdir()
            argv = [
                "docker",
                "run",
                "--rm",
                "--read-only",
                "--network",
                "bridge",
                "--workdir",
                "/workspace",
                "--mount",
                f"type=bind,source={workspace},target=/workspace,readonly",
                "--mount",
                f"type=bind,source={output},target=/workspace/.qa-eval-output",
                "python:3.11",
                "codex",
                "exec",
                "-",
            ]
            result = verify_agent_docker_command(
                argv, workspace=workspace, output_root=output, evaluator_root=evaluator
            )
        self.assertEqual(result["status"], "verified")
        self.assertEqual(result["evaluator_bind_mounts"], 0)

    def test_agent_container_rejects_evaluator_mount_and_writable_source(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            workspace = root / "workspace"
            output = root / "output"
            evaluator = root / "evaluator"
            workspace.mkdir()
            output.mkdir()
            evaluator.mkdir()
            base = [
                "docker",
                "run",
                "--rm",
                "--read-only",
                "--network",
                "bridge",
                "--workdir",
                "/workspace",
            ]
            with self.assertRaises(AgentEvalError):
                verify_agent_docker_command(
                    base
                    + [
                        "--mount",
                        f"type=bind,source={workspace},target=/workspace",
                        "--mount",
                        f"type=bind,source={output},target=/workspace/.qa-eval-output",
                        "python:3.11",
                        "codex",
                        "exec",
                        "-",
                    ],
                    workspace=workspace,
                    output_root=output,
                    evaluator_root=evaluator,
                )

    def test_agent_tmpfs_is_limited_to_tmp_and_explicit_codex_home(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            workspace = root / "workspace"
            output = root / "output"
            evaluator = root / "evaluator"
            for path in (workspace, output, evaluator):
                path.mkdir()
            base = [
                "docker",
                "run",
                "--rm",
                "--read-only",
                "--network",
                "bridge",
                "--workdir",
                "/workspace",
                "--mount",
                f"type=bind,source={workspace},target=/workspace,readonly",
                "--mount",
                f"type=bind,source={output},target=/workspace/.qa-eval-output",
                "--mount",
                "type=tmpfs,target=/tmp",
                "--mount",
                "type=tmpfs,target=/codex-home",
                "--env",
                "CODEX_HOME=/codex-home",
                "python:3.11",
                "codex",
                "exec",
                "-",
            ]
            verify_agent_docker_command(
                base, workspace=workspace, output_root=output, evaluator_root=evaluator
            )
            unapproved = list(base)
            unapproved[unapproved.index("type=tmpfs,target=/tmp")] = (
                "type=tmpfs,target=/workspace"
            )
            with self.assertRaises(AgentEvalError):
                verify_agent_docker_command(
                    unapproved,
                    workspace=workspace,
                    output_root=output,
                    evaluator_root=evaluator,
                )
            with self.assertRaises(AgentEvalError):
                verify_agent_docker_command(
                    base[:2] + ["--tmpfs", "/workspace"] + base[2:],
                    workspace=workspace,
                    output_root=output,
                    evaluator_root=evaluator,
                )

    def test_judge_container_has_no_host_bind_mounts(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            argv = [
                "docker",
                "run",
                "--rm",
                "--read-only",
                "--network",
                "bridge",
                "python:3.11",
                "codex",
                "exec",
                "-",
            ]
            self.assertEqual(
                verify_judge_docker_command(argv, evaluator_root=root)[
                    "host_bind_mounts"
                ],
                0,
            )
            with self.assertRaises(AgentEvalError):
                verify_judge_docker_command(
                    argv[:6]
                    + ["--mount", f"type=bind,source={root},target=/data,readonly"]
                    + argv[6:],
                    evaluator_root=root,
                )


if __name__ == "__main__":
    unittest.main()
