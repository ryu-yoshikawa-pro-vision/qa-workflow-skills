from __future__ import annotations

import ast
import inspect
import json
import os
import platform
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.skills.evals.agent.tools.codex_wsl2_bwrap_launcher import (
    CODEX_HOME_PREFIX,
    PACKAGE_SHA512,
    PACKAGE_VERSION,
    CodexWsl2LauncherError,
    _codex_exec_argv,
    _prepare_codex_home,
    cleanup_codex_home,
    judge_launcher_argv_for_profile,
    launcher_argv,
    sandbox_smoke,
    timeout_cleanup_smoke,
    verify_runtime,
)

IS_WSL2 = (
    platform.system() == "Linux"
    and "microsoft-standard-wsl2" in platform.release().lower()
)
RUN_WSL2_INTEGRATION = IS_WSL2 and os.environ.get("QAEVAL_RUN_WSL2_INTEGRATION") == "1"


class CodexWsl2LauncherUnitTests(unittest.TestCase):
    def test_exec_argv_uses_embedded_runtime_strict_config_and_fixed_sandbox(
        self,
    ) -> None:
        for mode, sandbox_policy in (
            ("agent", "workspace-write"),
            ("repair", "workspace-write"),
            ("judge", "read-only"),
        ):
            with self.subTest(mode=mode):
                command = _codex_exec_argv(
                    mode=mode,
                    model="model-test",
                    reasoning_effort="medium",
                    sandbox_policy=sandbox_policy,
                    output_message_path="/tmp/final.md"
                    if mode == "judge"
                    else "/workspace/.qa-eval-output/final.md",
                )
                self.assertEqual(command[:2], ["--no-daemon", "--strict-config"])
                self.assertEqual(
                    command[command.index("--sandbox") + 1], sandbox_policy
                )
                self.assertIn("exec", command)
                self.assertNotIn("--profile", command)
                self.assertNotIn("--mcp-config", command)

    def test_embedded_outer_and_inner_probe_scripts_parse(self) -> None:
        tree = ast.parse(inspect.getsource(sandbox_smoke))
        scripts = [
            node.value
            for node in ast.walk(tree)
            if isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and "import " in node.value
            and "sys.argv" in node.value
        ]
        self.assertEqual(len(scripts), 2)
        for script in scripts:
            compile(script, "<sandbox-probe>", "exec")

    def test_launcher_argv_uses_fixed_python_launcher_and_codex_template(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            workspace = root / "workspace"
            workspace.mkdir()
            output_mountpoint = workspace / ".qa-eval-output"
            output_mountpoint.mkdir()
            output = root / "attempt-output"
            output.mkdir()
            command = launcher_argv(
                mode="agent",
                workspace_root=workspace,
                output_root=output,
                observations_path=root / "observations.json",
                model="model-test",
                reasoning_effort="medium",
                sandbox_policy="workspace-write",
                cli_version="Codex CLI 0.163.0",
                docker_argv=["codex"],
            )
            self.assertEqual(command[0], os.sys.executable)
            self.assertEqual(Path(command[1]).name, "codex_wsl2_bwrap_launcher.py")
            self.assertIn("--workspace-root", command)
            self.assertEqual(command[command.index("--model") + 1], "model-test")

    def test_launcher_argv_rejects_arbitrary_commands_and_versions(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            workspace = root / "workspace"
            workspace.mkdir()
            (workspace / ".qa-eval-output").mkdir()
            output = root / "output"
            output.mkdir()
            arguments = {
                "mode": "agent",
                "workspace_root": workspace,
                "output_root": output,
                "observations_path": root / "observations.json",
                "model": "model-test",
                "reasoning_effort": "medium",
                "sandbox_policy": "workspace-write",
            }
            with self.assertRaises(CodexWsl2LauncherError):
                launcher_argv(**arguments, docker_argv=["docker", "run"])
            with self.assertRaises(CodexWsl2LauncherError):
                launcher_argv(**arguments, cli_version="0.164.0")

    def test_judge_profile_rejects_shell_mcp_and_extra_config(self) -> None:
        profile = {
            "model": "judge-model",
            "reasoning_effort": "medium",
            "sandbox_policy": "read-only",
            "approval_policy": "never",
            "launch_options": [],
            "tools": [],
            "mcp_servers": [],
            "skill_roots": [],
            "global_config": "none",
            "external_instructions": "none",
        }
        with tempfile.TemporaryDirectory() as temporary:
            judge_root = Path(temporary) / "judge"
            judge_root.mkdir()
            observations = judge_root / "observations.json"
            command = judge_launcher_argv_for_profile(
                profile, observations_path=observations
            )
            self.assertIn("--mode", command)
            self.assertEqual(command[command.index("--mode") + 1], "judge")
            for key, value in (("tools", ["shell"]), ("mcp_servers", ["test"])):
                invalid = {**profile, key: value}
                with self.assertRaises(CodexWsl2LauncherError):
                    judge_launcher_argv_for_profile(
                        invalid, observations_path=observations
                    )

    def test_codex_home_is_private_and_cleanup_removes_only_owned_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            home_parent = root / "homes"
            home_parent.mkdir(mode=0o700)
            home = home_parent / f"{CODEX_HOME_PREFIX}agent-test"
            _prepare_codex_home(
                home, mode="agent", reasoning_effort="medium", auth=None
            )
            config = (home / "config.toml").read_text(encoding="utf-8")
            self.assertIn('approval_policy = "never"', config)
            self.assertIn('web_search = "disabled"', config)
            self.assertIn("writable_roots = []", config)
            self.assertNotIn("auth.json", {path.name for path in home.iterdir()})
            scratch = Path(str(home) + ".git")
            scratch.mkdir()
            codex_scratch = Path(str(home) + ".workspace-codex")
            codex_scratch.mkdir()
            workspace = root / "workspace"
            workspace.mkdir()
            mountpoint = workspace / ".git"
            mountpoint.mkdir()
            codex_mountpoint = workspace / ".codex"
            codex_mountpoint.mkdir()
            cleanup_codex_home(
                home, allowed_parent=home_parent, workspace_root=workspace
            )
            self.assertFalse(home.exists())
            self.assertFalse(scratch.exists())
            self.assertFalse(codex_scratch.exists())
            self.assertFalse(mountpoint.exists())
            self.assertFalse(codex_mountpoint.exists())
            outsider = root / f"{CODEX_HOME_PREFIX}outsider"
            outsider.mkdir()
            with self.assertRaises(CodexWsl2LauncherError):
                cleanup_codex_home(outsider, allowed_parent=home_parent)

    def test_repair_codex_home_allows_only_the_selected_skill_root(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            home_parent = Path(temporary) / "homes"
            home_parent.mkdir(mode=0o700)
            home = home_parent / f"{CODEX_HOME_PREFIX}repair-test"
            _prepare_codex_home(
                home,
                mode="repair",
                reasoning_effort="medium",
                auth=None,
                skill_name="synthetic-skill",
            )
            config = (home / "config.toml").read_text(encoding="utf-8")
            self.assertIn(
                'writable_roots = ["/workspace/.agents/skills/synthetic-skill"]',
                config,
            )
            cleanup_codex_home(home, allowed_parent=home_parent)
            with self.assertRaises(CodexWsl2LauncherError):
                _prepare_codex_home(
                    home,
                    mode="repair",
                    reasoning_effort="medium",
                    auth=None,
                    skill_name="../outside",
                )

    def test_runtime_pin_mismatch_fails_before_binary_execution(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "runtime-manifest.json").write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "package_name": "@openai/codex",
                        "package_version": PACKAGE_VERSION,
                        "package_url": "https://invalid.example/package.tgz",
                        "package_sha512": PACKAGE_SHA512,
                    }
                ),
                encoding="utf-8",
            )
            with patch(
                "scripts.skills.evals.agent.tools.codex_wsl2_bwrap_launcher._require_wsl2"
            ):
                with self.assertRaisesRegex(CodexWsl2LauncherError, "manifest"):
                    verify_runtime(root)


@unittest.skipUnless(
    RUN_WSL2_INTEGRATION,
    "set QAEVAL_RUN_WSL2_INTEGRATION=1 in WSL2 to run the pinned Codex integration",
)
class CodexWsl2LauncherIntegrationTests(unittest.TestCase):
    def test_formal_launcher_modes_fd_network_paths_and_timeout_cleanup(self) -> None:
        with tempfile.TemporaryDirectory(prefix="qa-wsl2-formal-test-") as temporary:
            root = Path(temporary)
            for mode in ("agent", "repair"):
                workspace = root / mode / "workspace"
                workspace.mkdir(parents=True)
                (workspace / "protected.txt").write_text(
                    "synthetic-source\n", encoding="utf-8"
                )
                (workspace / ".agents" / "skills").mkdir(parents=True)
                mountpoint = workspace / ".qa-eval-output"
                mountpoint.mkdir()
                if mode == "agent":
                    output = root / mode / "output"
                    output.mkdir()
                    skill_root = None
                    skill_name = None
                else:
                    output = mountpoint
                    skill_name = "synthetic-skill"
                    skill_root = workspace / ".agents" / "skills" / skill_name
                    skill_root.mkdir(parents=True)
                    (skill_root / "SKILL.md").write_text(
                        "synthetic skill\n", encoding="utf-8"
                    )
                result = sandbox_smoke(
                    mode=mode,
                    workspace_root=workspace,
                    output_root=output,
                    skill_root=skill_root,
                    skill_name=skill_name,
                    permission_profile=":workspace",
                )
                self.assertEqual(
                    result["status"],
                    "verified",
                    {
                        "mode": mode,
                        "inner": result.get("inner"),
                        "checks": result.get("checks"),
                        "diagnostics": result.get("diagnostics"),
                    },
                )
                self.assertTrue(all(result["checks"].values()), result["checks"])
                self.assertFalse((workspace / ".git").exists())
                self.assertFalse((workspace / ".codex").exists())
                self.assertFalse((workspace / "synthetic-escape").exists())
                self.assertEqual(
                    (workspace / "protected.txt").read_text(encoding="utf-8"),
                    "synthetic-source\n",
                )

            judge = sandbox_smoke(
                mode="judge",
                workspace_root=None,
                output_root=None,
                permission_profile=":read-only",
            )
            self.assertEqual(judge["status"], "verified", judge)
            self.assertTrue(all(judge["checks"].values()), judge["checks"])

            timeout_workspace = root / "timeout" / "workspace"
            timeout_workspace.mkdir(parents=True)
            (timeout_workspace / "protected.txt").write_text(
                "synthetic-source\n", encoding="utf-8"
            )
            (timeout_workspace / ".agents" / "skills").mkdir(parents=True)
            (timeout_workspace / ".qa-eval-output").mkdir()
            timeout_output = root / "timeout" / "output"
            timeout_output.mkdir()
            timeout_result = timeout_cleanup_smoke(
                workspace_root=timeout_workspace,
                output_root=timeout_output,
                timeout_seconds=2,
            )
            self.assertEqual(timeout_result["status"], "verified", timeout_result)
