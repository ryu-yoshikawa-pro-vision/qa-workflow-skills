from __future__ import annotations

import json
import os
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
from scripts.skills.evals.agent.tools.codex_wsl2_bwrap_launcher import PACKAGE_SHA512
from scripts.skills.evals.agent.workspace import (
    _validate_profile,
    expected_codex_exec_argv_fingerprints,
    prepare_agent_output_mountpoint,
    profile_fingerprint,
    verify_agent_docker_command,
    verify_agent_wsl2_command,
    verify_judge_docker_command,
    verify_profile_evidence,
    verify_repair_docker_command,
)


class WorkspaceIsolationTests(unittest.TestCase):
    @staticmethod
    def _wsl2_profile() -> dict:
        network_policy = "codex-parent-host-network-inner-shell-denied"
        return {
            "schema_version": 2,
            "agent": {
                "name": "codex",
                "model": "agent-model",
                "timeout_seconds": 60,
                "cli_version": "0.163.0",
                "reasoning_effort": "medium",
                "launch_options": [],
                "sandbox_policy": "workspace-write",
                "approval_policy": "never",
                "network_policy": network_policy,
                "tools": ["shell"],
                "mcp_servers": [],
                "skill_roots": ["/workspace/.agents/skills"],
                "external_instructions": "none",
                "global_config": "none",
            },
            "judge": {
                "model": "judge-model",
                "command_argv": ["codex"],
                "cwd": "isolated",
                "timeout_seconds": 60,
                "cli_version": "0.163.0",
                "reasoning_effort": "medium",
                "launch_options": [],
                "sandbox_policy": "read-only",
                "approval_policy": "never",
                "network_policy": network_policy,
                "skill_roots": [],
                "global_config": "none",
                "tools": [],
                "mcp_servers": [],
                "external_instructions": "none",
            },
            "isolation": {
                "method": "wsl2-dual-bubblewrap",
                "agent_read_roots": ["/workspace"],
                "evaluator_read_blocked": True,
            },
            "verification": {
                "status": "unverified",
                "method": "wsl2-dual-bubblewrap",
                "evidence_path": None,
            },
        }

    def test_schema2_profile_fixes_tool_and_network_boundaries(self) -> None:
        profile = self._wsl2_profile()
        _validate_profile(profile)

        profile["agent"]["tools"] = ["shell", "browser"]
        with self.assertRaises(AgentEvalError):
            _validate_profile(profile)

        profile = self._wsl2_profile()
        profile["judge"]["network_policy"] = "network-none"
        with self.assertRaises(AgentEvalError):
            _validate_profile(profile)

    def test_wsl2_agent_command_allows_only_the_named_output_mount(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            evaluator = root / "evaluator"
            evaluator.mkdir()
            workspace = root / "workspace"
            workspace.mkdir()
            nested_output = workspace / ".qa-eval-output"
            nested_output.mkdir()
            self.assertEqual(
                verify_agent_wsl2_command(
                    ["codex"],
                    workspace=workspace,
                    output_root=nested_output,
                    evaluator_root=evaluator,
                )["execution_method"],
                "wsl2-dual-bubblewrap",
            )
            unsafe_output = workspace / "arbitrary-output"
            unsafe_output.mkdir()
            with self.assertRaises(AgentEvalError):
                verify_agent_wsl2_command(
                    ["codex"],
                    workspace=workspace,
                    output_root=unsafe_output,
                    evaluator_root=evaluator,
                )

    def test_agent_output_mountpoint_is_created_empty_and_rejects_content(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary) / "workspace"
            workspace.mkdir()
            output = prepare_agent_output_mountpoint(workspace)
            self.assertEqual(output, workspace / ".qa-eval-output")
            self.assertEqual(list(output.iterdir()), [])

            (output / "unexpected").write_text("source content", encoding="utf-8")
            with self.assertRaisesRegex(AgentEvalError, "must be empty"):
                prepare_agent_output_mountpoint(workspace)

    def test_legacy_docker_evidence_cannot_authorize_new_profile(self) -> None:
        profile = {
            "agent": {"skill_roots": ["/workspace/.agents/skills"]},
            "judge": {"cwd": "isolated", "command_argv": ["docker", "run", "judge"]},
            "isolation": {"agent_read_roots": ["/workspace"]},
            "verification": {"status": "verified", "evidence_path": "isolation.json"},
        }
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with patch(
                "scripts.skills.evals.agent.workspace.assert_clean_checkout",
                return_value="a" * 40,
            ):
                self.assertFalse(verify_profile_evidence(profile, root))

    def test_wsl2_evidence_is_bound_to_mode_command_profile_and_revision(self) -> None:
        profile = {
            "schema_version": 2,
            "agent": {
                "model": "agent-model",
                "reasoning_effort": "medium",
                "sandbox_policy": "workspace-write",
                "skill_roots": ["/workspace/.agents/skills"],
            },
            "judge": {
                "model": "judge-model",
                "reasoning_effort": "high",
                "sandbox_policy": "read-only",
                "cwd": "isolated",
                "command_argv": ["codex"],
            },
            "isolation": {"agent_read_roots": ["/workspace"]},
            "verification": {"status": "verified", "evidence_path": "isolation.json"},
        }
        agent_command = ["codex"]
        required_checks = {
            "evaluator_read_denied",
            "authentication_shell_read_denied",
            "host_home_read_denied",
            "other_attempt_home_read_denied",
            "windows_filesystem_read_denied",
            "source_write_denied",
            "output_write_allowed",
            "inherited_fd_denied",
            "symlink_escape_denied",
            "fresh_procfs",
            "nested_namespaces",
            "inner_shell_network_blocked",
            "extra_tools_disabled",
            "mounts_reviewed",
            "agent_judge_separated",
            "timeout_cleanup",
        }
        fingerprint = profile_fingerprint(profile)
        exec_fingerprints = expected_codex_exec_argv_fingerprints(profile)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            evidence = {
                "status": "verified",
                "schema_version": 2,
                "execution_method": "wsl2-dual-bubblewrap",
                "probe": "scripts/skills/evals/agent/isolation_probe.py",
                "profile_fingerprint": fingerprint,
                "agent_command_fingerprint": canonical_fingerprint(agent_command),
                "judge_command_fingerprint": canonical_fingerprint(
                    profile["judge"]["command_argv"]
                ),
                "evaluator_revision": "a" * 40,
                "runtime": {
                    "package_sha512": PACKAGE_SHA512,
                    "package_version": "0.163.0-linux-x64",
                    "codex_sha256": "c" * 64,
                    "bwrap_sha256": "d" * 64,
                },
                "mode_evidence": {
                    mode: {
                        "status": "verified",
                        "mode": mode,
                        "profile_fingerprint": fingerprint,
                        "codex_exec_argv_fingerprint": exec_fingerprints[mode],
                    }
                    for mode in ("agent", "judge", "repair")
                },
                "details": {
                    "authentication_shell_visible_risk": False,
                    "authentication_refresh_persistence_unresolved": True,
                    "authentication_process_concurrency_unresolved": True,
                    "model_api_used": False,
                },
                "checks": {key: True for key in required_checks},
            }
            evidence_path = root / "isolation.json"
            evidence_path.write_text(json.dumps(evidence), encoding="utf-8")
            with patch(
                "scripts.skills.evals.agent.workspace.assert_clean_checkout",
                return_value="a" * 40,
            ):
                self.assertTrue(
                    verify_profile_evidence(
                        profile, root, agent_command_argv=agent_command
                    )
                )
                bad_evidence = json.loads(json.dumps(evidence))
                bad_evidence["checks"]["authentication_shell_read_denied"] = False
                evidence_path.write_text(json.dumps(bad_evidence), encoding="utf-8")
                with self.assertRaises(AgentEvalError):
                    verify_profile_evidence(
                        profile, root, agent_command_argv=agent_command
                    )
                evidence_path.write_text(json.dumps(evidence), encoding="utf-8")
                bad_evidence = json.loads(json.dumps(evidence))
                bad_evidence["details"]["authentication_shell_visible_risk"] = True
                evidence_path.write_text(json.dumps(bad_evidence), encoding="utf-8")
                with self.assertRaises(AgentEvalError):
                    verify_profile_evidence(
                        profile, root, agent_command_argv=agent_command
                    )
                evidence_path.write_text(json.dumps(evidence), encoding="utf-8")
                bad_evidence = json.loads(json.dumps(evidence))
                bad_evidence["details"][
                    "authentication_process_concurrency_unresolved"
                ] = False
                evidence_path.write_text(json.dumps(bad_evidence), encoding="utf-8")
                with self.assertRaises(AgentEvalError):
                    verify_profile_evidence(
                        profile, root, agent_command_argv=agent_command
                    )
                evidence_path.write_text(json.dumps(evidence), encoding="utf-8")
                bad_evidence = json.loads(json.dumps(evidence))
                bad_evidence["mode_evidence"]["repair"][
                    "codex_exec_argv_fingerprint"
                ] = exec_fingerprints["judge"]
                evidence_path.write_text(json.dumps(bad_evidence), encoding="utf-8")
                with self.assertRaises(AgentEvalError):
                    verify_profile_evidence(
                        profile, root, agent_command_argv=agent_command
                    )
                evidence_path.write_text(json.dumps(evidence), encoding="utf-8")
                with self.assertRaises(AgentEvalError):
                    verify_profile_evidence(
                        profile, root, agent_command_argv=agent_command + ["unsafe"]
                    )
                evidence["mode_evidence"]["judge"]["mode"] = "agent"
                evidence_path.write_text(json.dumps(evidence), encoding="utf-8")
                with self.assertRaises(AgentEvalError):
                    verify_profile_evidence(
                        profile, root, agent_command_argv=agent_command
                    )
            with patch(
                "scripts.skills.evals.agent.workspace.assert_clean_checkout",
                return_value="b" * 40,
            ):
                evidence["mode_evidence"]["judge"]["mode"] = "judge"
                evidence_path.write_text(json.dumps(evidence), encoding="utf-8")
                with self.assertRaises(AgentEvalError):
                    verify_profile_evidence(
                        profile, root, agent_command_argv=agent_command
                    )

    @unittest.skipUnless(os.name == "posix", "requires the Linux Docker probe")
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
                "--cap-drop=ALL",
                "--security-opt=no-new-privileges",
                "-i",
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
        self.assertEqual(
            agent_argv[agent_argv.index("--user") + 1],
            f"{os.getuid()}:{os.getgid()}",
        )
        self.assertIn("/workspace/.agent-eval-source-write-probe", agent_argv[-1])

    @unittest.skipUnless(os.name == "posix", "requires the Linux Docker probe")
    def test_live_probe_records_sanitized_failure_diagnostic(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            sentinel = Path(temporary) / "sentinel.txt"
            sentinel.write_text("isolation-sentinel", encoding="utf-8")
            responses = [
                subprocess.CompletedProcess([], 0, b"", b""),
                subprocess.CompletedProcess([], 2, b"", b"Permission denied\n"),
            ]
            with patch(
                "scripts.skills.evals.agent.isolation_probe.subprocess.run",
                side_effect=responses,
            ):
                result = _live_mount_probe(
                    ["docker", "run", "--rm", "codex-image", "codex", "exec"],
                    evaluator_sentinel=sentinel,
                )
        self.assertEqual(result["status"], "unverified")
        self.assertEqual(result["diagnostic"], "Permission denied")

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
                "--cap-drop=ALL",
                "--security-opt=no-new-privileges",
                "-i",
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
                "--cap-drop=ALL",
                "--security-opt=no-new-privileges",
                "-i",
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

    def test_agent_tmpfs_is_limited_to_tmp_and_launcher_owns_codex_home(self) -> None:
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
                "--cap-drop=ALL",
                "--security-opt=no-new-privileges",
                "-i",
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
                    base[: base.index("python:3.11")]
                    + ["--mount", "type=tmpfs,target=/codex-home"]
                    + base[base.index("python:3.11") :],
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
                "--cap-drop=ALL",
                "--security-opt=no-new-privileges",
                "--network",
                "bridge",
                "-i",
                "--mount",
                "type=tmpfs,target=/tmp",
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

    def test_repair_container_writes_only_the_selected_skill_package(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            workspace = root / "workspace"
            skill_root = root / "qa-workflow"
            output = root / "output"
            evaluator = root / "evaluator"
            for path in (workspace, skill_root, output, evaluator):
                path.mkdir()
            base = [
                "docker",
                "run",
                "--rm",
                "--read-only",
                "--cap-drop=ALL",
                "--security-opt=no-new-privileges",
                "-i",
                "--network",
                "bridge",
                "--workdir",
                "/workspace",
                "--mount",
                f"type=bind,source={workspace},target=/workspace,readonly",
                "--mount",
                f"type=bind,source={skill_root},target=/workspace/.agents/skills/qa-workflow",
                "--mount",
                f"type=bind,source={output},target=/workspace/.qa-eval-output",
                "--mount",
                "type=tmpfs,target=/tmp",
                "python:3.11",
                "codex",
                "exec",
                "-",
            ]
            result = verify_repair_docker_command(
                base,
                workspace=workspace,
                skill_root=skill_root,
                output_root=output,
                skill_name="qa-workflow",
            )
            self.assertEqual(result["single_skill_writable"], "qa-workflow")
            with self.assertRaises(AgentEvalError):
                verify_repair_docker_command(
                    base
                    + [
                        "--mount",
                        f"type=bind,source={evaluator},target=/evaluator,readonly",
                    ],
                    workspace=workspace,
                    skill_root=skill_root,
                    output_root=output,
                    skill_name="qa-workflow",
                )


if __name__ == "__main__":
    unittest.main()
