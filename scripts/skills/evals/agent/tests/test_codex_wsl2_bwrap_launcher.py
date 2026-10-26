from __future__ import annotations

import ast
import hashlib
import inspect
import io
import json
import os
import platform
import subprocess
import tempfile
import tomllib
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import Mock, patch

from scripts.skills.evals.agent.tools import codex_wsl2_bwrap_launcher
from scripts.skills.evals.agent.tools.codex_wsl2_bwrap_launcher import (
    CODEX_HOME_PREFIX,
    PACKAGE_SHA512,
    PACKAGE_VERSION,
    CodexWsl2LauncherError,
    _auth_material,
    _codex_exec_argv,
    _prepare_codex_home,
    cleanup_argv,
    cleanup_codex_home,
    codex_exec_argv_fingerprint,
    judge_launcher_argv_for_profile,
    launch,
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
    def test_launch_redaction_is_unverified_and_raw_message_file_is_removed(
        self,
    ) -> None:
        secret = "sk-syntheticsecret012345678901"
        for mode, redact in (
            ("agent", False),
            ("agent", True),
            ("judge", True),
            ("repair", True),
        ):
            with (
                self.subTest(mode=mode, redact=redact),
                tempfile.TemporaryDirectory() as temporary,
            ):
                root = Path(temporary)
                output_root = root / "output"
                output_root.mkdir()
                workspace_root = root / "workspace" if mode != "judge" else None
                if workspace_root is not None:
                    workspace_root.mkdir()
                    (workspace_root / ".qa-eval-output").mkdir()
                codex_home_parent = root / "homes"
                codex_home_parent.mkdir(mode=0o700)
                codex_home = codex_home_parent / f"{CODEX_HOME_PREFIX}{mode}-test"
                source_home = root / "source-home"
                source_home.mkdir()
                auth_file = source_home / "auth.json"
                auth_file.write_text("SYNTHETIC_CHATGPT_AUTH_MARKER", encoding="utf-8")
                observations_path = root / "launcher-observations.json"
                child_environments = []
                child_commands = []
                login_status_environments = []
                response = f"Answer {secret}" if redact else "Ordinary answer"
                events = (
                    json.dumps(
                        {
                            "type": "item.completed",
                            "item": {"type": "agent_message", "text": response},
                        }
                    )
                    + "\n"
                    + json.dumps({"type": "turn.completed"})
                    + "\n"
                ).encode("utf-8")

                def fake_subprocess(command, **kwargs):
                    if command[1:] == ["login", "status"]:
                        login_status_environments.append(kwargs["env"])
                        return subprocess.CompletedProcess(
                            command,
                            0,
                            stdout=b"",
                            stderr=b"Logged in using ChatGPT\n",
                        )
                    child_environments.append(kwargs["env"])
                    child_commands.append(command)
                    output_index = command.index("--output-last-message") + 1
                    output_message = command[output_index]
                    if output_message.startswith("/workspace/.qa-eval-output/"):
                        (output_root / output_message.rsplit("/", 1)[-1]).write_text(
                            response, encoding="utf-8"
                        )
                    stderr = (
                        f"API_KEY={secret}\n" if redact else "safe diagnostic\n"
                    ).encode("utf-8")
                    return subprocess.CompletedProcess(
                        command, 0, stdout=events, stderr=stderr
                    )

                stdout = io.StringIO()
                stderr = io.StringIO()
                with (
                    patch.object(codex_wsl2_bwrap_launcher, "_require_wsl2"),
                    patch.object(
                        codex_wsl2_bwrap_launcher,
                        "AUTHENTICATION_SHELL_VISIBLE_RISK",
                        False,
                    ),
                    patch.object(
                        codex_wsl2_bwrap_launcher,
                        "AUTHENTICATION_REFRESH_PERSISTENCE_UNRESOLVED",
                        False,
                    ),
                    patch.object(
                        codex_wsl2_bwrap_launcher,
                        "AUTHENTICATION_PROCESS_CONCURRENCY_UNRESOLVED",
                        False,
                    ),
                    patch.object(
                        codex_wsl2_bwrap_launcher,
                        "verify_runtime",
                        return_value={
                            "runtime": "synthetic",
                            "codex_path": "/fixed/runtime/codex",
                            "codex_version": "codex-cli 0.163.0",
                        },
                    ),
                    patch.object(
                        codex_wsl2_bwrap_launcher,
                        "_outer_argv",
                        side_effect=lambda **kwargs: (
                            list(kwargs["codex_argv"]),
                            {"mode": kwargs["mode"]},
                        ),
                    ),
                    patch.object(
                        codex_wsl2_bwrap_launcher.subprocess,
                        "run",
                        side_effect=fake_subprocess,
                    ),
                    patch.dict(
                        os.environ,
                        {
                            "CODEX_HOME": str(source_home),
                            "OPENAI_API_KEY": "sk-synthetic-api-key",
                            "CODEX_API_KEY": "synthetic-codex-api-key",
                        },
                    ),
                    redirect_stdout(stdout),
                    redirect_stderr(stderr),
                ):
                    exit_code = launch(
                        mode=mode,
                        output_root=output_root,
                        prompt="synthetic prompt",
                        observations_path=observations_path,
                        model="synthetic-model",
                        reasoning_effort="low",
                        sandbox_policy=(
                            "read-only" if mode == "judge" else "workspace-write"
                        ),
                        workspace_root=workspace_root,
                        skill_name="synthetic-skill" if mode == "repair" else None,
                        codex_home=codex_home,
                        runtime_root=root,
                    )

                if mode == "judge":
                    final_message = stdout.getvalue().strip()
                    observations = json.loads(
                        observations_path.read_text(encoding="utf-8")
                    )
                else:
                    envelope = json.loads(stdout.getvalue())
                    final_message = envelope["final_message"]
                    observations = envelope["observations"]
                self.assertEqual(observations["authentication_method"], "chatgpt_login")
                self.assertEqual(len(child_commands), 1)
                self.assertEqual(child_commands[0].count("--skip-git-repo-check"), 1)
                self.assertEqual(
                    observations["codex_exec_argv_fingerprint"],
                    codex_exec_argv_fingerprint(child_commands[0], mode=mode),
                )
                if redact:
                    self.assertEqual(exit_code, 2)
                    self.assertEqual(final_message, "Answer [redacted]")
                    self.assertTrue(observations["final_message_redacted"])
                    self.assertEqual(observations["status"], "evidence_unverified")
                    self.assertIsNone(observations["response_sha256"])
                    self.assertNotIn(secret, stdout.getvalue())
                    self.assertNotIn(secret, stderr.getvalue())
                else:
                    self.assertEqual(exit_code, 0)
                    self.assertEqual(final_message, response)
                    self.assertFalse(observations["final_message_redacted"])
                    self.assertEqual(observations["status"], "completed")
                    self.assertEqual(
                        observations["response_sha256"],
                        hashlib.sha256(response.encode("utf-8")).hexdigest(),
                    )
                self.assertEqual(
                    observations["final_message_cleanup_status"],
                    "isolated_tmpfs" if mode == "judge" else "removed",
                )
                self.assertEqual(observations["codex_home_cleanup_status"], "succeeded")
                self.assertEqual(observations["authentication_method"], "chatgpt_login")
                self.assertEqual(
                    observations["authentication_check_status"], "verified"
                )
                self.assertEqual(observations["codex_cli_version"], "0.163.0")
                self.assertTrue(child_environments)
                self.assertTrue(login_status_environments)
                self.assertNotIn("OPENAI_API_KEY", login_status_environments[0])
                self.assertNotIn("CODEX_API_KEY", login_status_environments[0])
                for child_environment in child_environments:
                    self.assertNotIn("OPENAI_API_KEY", child_environment)
                    self.assertNotIn("CODEX_API_KEY", child_environment)
                self.assertNotIn(
                    "SYNTHETIC_CHATGPT_AUTH_MARKER", json.dumps(observations)
                )
                self.assertNotIn("SYNTHETIC_CHATGPT_AUTH_MARKER", stdout.getvalue())
                self.assertNotIn("SYNTHETIC_CHATGPT_AUTH_MARKER", stderr.getvalue())
                self.assertFalse(any(output_root.iterdir()))
                self.assertFalse(codex_home.exists())
                persisted = b"".join(
                    path.read_bytes() for path in root.rglob("*") if path.is_file()
                )
                self.assertNotIn(secret.encode("utf-8"), persisted)

    def test_launch_fails_closed_for_unresolved_auth_state_safety(self) -> None:
        marker = "SYNTHETIC_AUTH_VISIBILITY_MARKER"
        for mode in ("agent", "judge", "repair"):
            with (
                self.subTest(mode=mode),
                tempfile.TemporaryDirectory() as temporary,
            ):
                root = Path(temporary)
                output_root = root / "output"
                output_root.mkdir()
                workspace_root = root / "workspace" if mode != "judge" else None
                if workspace_root is not None:
                    workspace_root.mkdir()
                    (workspace_root / ".qa-eval-output").mkdir()
                auth_source = root / "source-home"
                auth_source.mkdir()
                (auth_source / "auth.json").write_text(marker, encoding="utf-8")
                codex_home_parent = root / "homes"
                codex_home_parent.mkdir(mode=0o700)
                codex_home = codex_home_parent / f"{CODEX_HOME_PREFIX}{mode}-blocked"
                observations_path = root / "launcher-observations.json"

                with (
                    patch.object(codex_wsl2_bwrap_launcher, "_require_wsl2"),
                    patch.object(
                        codex_wsl2_bwrap_launcher,
                        "verify_runtime",
                        return_value={"runtime": "synthetic"},
                    ) as verify,
                    patch.object(
                        codex_wsl2_bwrap_launcher.subprocess, "run"
                    ) as subprocess_run,
                    patch.dict(os.environ, {"CODEX_HOME": str(auth_source)}),
                ):
                    exit_code = launch(
                        mode=mode,
                        output_root=output_root,
                        prompt="synthetic prompt",
                        observations_path=observations_path,
                        model="gpt-6-luna",
                        reasoning_effort="max",
                        sandbox_policy=(
                            "read-only" if mode == "judge" else "workspace-write"
                        ),
                        workspace_root=workspace_root,
                        skill_name="synthetic-skill" if mode == "repair" else None,
                        codex_home=codex_home,
                        runtime_root=root,
                    )

                observations = json.loads(observations_path.read_text(encoding="utf-8"))
                self.assertEqual(exit_code, 2)
                self.assertEqual(observations["status"], "execution_error")
                self.assertEqual(
                    observations["error"], "authentication_execution_safety_unresolved"
                )
                self.assertEqual(observations["authentication_method"], "not_checked")
                self.assertEqual(observations["authentication_check_status"], "blocked")
                self.assertFalse(observations["authentication_shell_visible_risk"])
                self.assertTrue(
                    observations["authentication_refresh_persistence_unresolved"]
                )
                self.assertTrue(
                    observations["authentication_process_concurrency_unresolved"]
                )
                self.assertEqual(
                    observations["authentication_execution_blockers"],
                    [
                        "authentication_refresh_persistence_unresolved",
                        "authentication_process_concurrency_unresolved",
                    ],
                )
                self.assertEqual(observations["mode"], mode)
                self.assertNotIn(marker, observations_path.read_text(encoding="utf-8"))
                self.assertFalse(codex_home.exists())
                self.assertFalse(any(output_root.iterdir()))
                verify.assert_not_called()
                subprocess_run.assert_not_called()

    def test_auth_material_accepts_only_official_chatgpt_login_status(self) -> None:
        cases = (
            (b"", b"Logged in using ChatGPT\n", 0, "chatgpt_login"),
            (
                b"",
                b"Logged in using an API key - sk-synthetic-secret\n",
                0,
                "api_key",
            ),
            (b"", b"Not logged in\n", 1, "not_logged_in"),
            (b"", b"Logged in using an access token\n", 0, "unknown"),
            (
                b"",
                b"Error checking login status: synthetic-secret\n",
                1,
                "check_failed",
            ),
        )
        runtime = {
            "codex_path": "/fixed/runtime/codex",
            "codex_version": "codex-cli 0.163.0",
        }
        for stdout, stderr, returncode, expected_status in cases:
            with self.subTest(expected_status=expected_status):
                with tempfile.TemporaryDirectory() as temporary:
                    source_home = Path(temporary) / "codex-home"
                    source_home.mkdir()
                    auth_file = source_home / "auth.json"
                    auth_file.write_text("SYNTHETIC_AUTH_MARKER", encoding="utf-8")
                    process = subprocess.CompletedProcess(
                        [runtime["codex_path"], "login", "status"],
                        returncode,
                        stdout=stdout,
                        stderr=stderr,
                    )
                    with (
                        patch.dict(
                            os.environ,
                            {
                                "CODEX_HOME": str(source_home),
                                "OPENAI_API_KEY": "sk-parent-synthetic",
                                "CODEX_API_KEY": "parent-synthetic-codex-key",
                            },
                            clear=True,
                        ),
                        patch.object(
                            codex_wsl2_bwrap_launcher.subprocess,
                            "run",
                            return_value=process,
                        ) as run,
                    ):
                        auth, status = _auth_material(runtime)

                    expected_auth = (
                        auth_file if expected_status == "chatgpt_login" else None
                    )
                    self.assertEqual(auth, expected_auth)
                    self.assertEqual(status, expected_status)
                    self.assertEqual(
                        run.call_args.args[0],
                        [runtime["codex_path"], "login", "status"],
                    )
                    child_env = run.call_args.kwargs["env"]
                    self.assertNotIn("OPENAI_API_KEY", child_env)
                    self.assertNotIn("CODEX_API_KEY", child_env)
                    self.assertFalse(run.call_args.kwargs["shell"])
                    self.assertTrue(run.call_args.kwargs["close_fds"])
                    self.assertNotIn("sk-synthetic-secret", status)
                    self.assertNotIn("synthetic-secret", status)

    def test_auth_material_ignores_api_key_environment_without_auth_file(self) -> None:
        runtime = {
            "codex_path": "/fixed/runtime/codex",
            "codex_version": "codex-cli 0.163.0",
        }
        with tempfile.TemporaryDirectory() as temporary:
            source_home = Path(temporary) / "codex-home"
            source_home.mkdir()
            process = subprocess.CompletedProcess(
                [runtime["codex_path"], "login", "status"],
                1,
                stdout=b"",
                stderr=b"Not logged in\n",
            )
            with (
                patch.dict(
                    os.environ,
                    {
                        "CODEX_HOME": str(source_home),
                        "OPENAI_API_KEY": "sk-environment-only",
                        "CODEX_API_KEY": "codex-environment-only",
                    },
                    clear=True,
                ),
                patch.object(
                    codex_wsl2_bwrap_launcher.subprocess,
                    "run",
                    return_value=process,
                ) as run,
            ):
                auth, status = _auth_material(runtime)

        self.assertIsNone(auth)
        self.assertEqual(status, "not_logged_in")
        self.assertNotIn("OPENAI_API_KEY", run.call_args.kwargs["env"])
        self.assertNotIn("CODEX_API_KEY", run.call_args.kwargs["env"])

    def test_auth_material_rejects_chatgpt_marker_with_failed_status_exit(self) -> None:
        runtime = {
            "codex_path": "/fixed/runtime/codex",
            "codex_version": "codex-cli 0.163.0",
        }
        with tempfile.TemporaryDirectory() as temporary:
            source_home = Path(temporary) / "codex-home"
            source_home.mkdir()
            (source_home / "auth.json").write_text("SYNTHETIC_AUTH", encoding="utf-8")
            process = subprocess.CompletedProcess(
                [runtime["codex_path"], "login", "status"],
                1,
                stdout=b"Logged in using ChatGPT\n",
                stderr=b"status command failed\n",
            )
            with (
                patch.dict(os.environ, {"CODEX_HOME": str(source_home)}, clear=True),
                patch.object(
                    codex_wsl2_bwrap_launcher.subprocess,
                    "run",
                    return_value=process,
                ),
            ):
                auth, status = _auth_material(runtime)

        self.assertIsNone(auth)
        self.assertEqual(status, "check_failed")

    def test_auth_material_rejects_chatgpt_status_without_copyable_auth_file(
        self,
    ) -> None:
        runtime = {
            "codex_path": "/fixed/runtime/codex",
            "codex_version": "codex-cli 0.163.0",
        }
        with tempfile.TemporaryDirectory() as temporary:
            source_home = Path(temporary) / "codex-home"
            source_home.mkdir()
            process = subprocess.CompletedProcess(
                [runtime["codex_path"], "login", "status"],
                0,
                stdout=b"",
                stderr=b"Logged in using ChatGPT\n",
            )
            with (
                patch.dict(os.environ, {"CODEX_HOME": str(source_home)}, clear=True),
                patch.object(
                    codex_wsl2_bwrap_launcher.subprocess,
                    "run",
                    return_value=process,
                ),
            ):
                auth, status = _auth_material(runtime)

        self.assertIsNone(auth)
        self.assertEqual(status, "unsupported_auth_store")

    def test_auth_material_rejects_invalid_auth_file_before_status_check(self) -> None:
        runtime = {
            "codex_path": "/fixed/runtime/codex",
            "codex_version": "codex-cli 0.163.0",
        }
        with tempfile.TemporaryDirectory() as temporary:
            source_home = Path(temporary) / "codex-home"
            source_home.mkdir()
            (source_home / "auth.json").write_bytes(b"x" * 1_000_001)
            with (
                patch.dict(os.environ, {"CODEX_HOME": str(source_home)}, clear=True),
                patch.object(codex_wsl2_bwrap_launcher.subprocess, "run") as run,
            ):
                auth, status = _auth_material(runtime)

        self.assertIsNone(auth)
        self.assertEqual(status, "invalid_auth_file")
        run.assert_not_called()

    def test_auth_material_classifies_login_status_timeout_without_details(
        self,
    ) -> None:
        runtime = {
            "codex_path": "/fixed/runtime/codex",
            "codex_version": "codex-cli 0.163.0",
        }
        with tempfile.TemporaryDirectory() as temporary:
            source_home = Path(temporary) / "codex-home"
            source_home.mkdir()
            (source_home / "auth.json").write_text("SYNTHETIC_AUTH", encoding="utf-8")
            with (
                patch.dict(os.environ, {"CODEX_HOME": str(source_home)}, clear=True),
                patch.object(
                    codex_wsl2_bwrap_launcher.subprocess,
                    "run",
                    side_effect=subprocess.TimeoutExpired(
                        [runtime["codex_path"], "login", "status"], 15
                    ),
                ),
            ):
                auth, status = _auth_material(runtime)

        self.assertIsNone(auth)
        self.assertEqual(status, "check_failed")

    def test_auth_material_rejects_windows_home_and_pinned_version_mismatch(
        self,
    ) -> None:
        with (
            patch.dict(
                os.environ, {"CODEX_HOME": r"C:\Users\person\.codex"}, clear=True
            ),
            patch.object(codex_wsl2_bwrap_launcher, "_is_wsl2", return_value=True),
        ):
            auth, status = _auth_material(
                {
                    "codex_path": "/fixed/runtime/codex",
                    "codex_version": "codex-cli 0.163.0",
                }
            )
        self.assertIsNone(auth)
        self.assertEqual(status, "unsupported_auth_store")

        with tempfile.TemporaryDirectory() as temporary:
            source_home = Path(temporary) / "codex-home"
            source_home.mkdir()
            (source_home / "auth.json").write_text("SYNTHETIC_AUTH", encoding="utf-8")
            with (
                patch.dict(os.environ, {"CODEX_HOME": str(source_home)}, clear=True),
                patch.object(codex_wsl2_bwrap_launcher.subprocess, "run") as run,
            ):
                auth, status = _auth_material(
                    {
                        "codex_path": "/wrong/runtime/codex",
                        "codex_version": "codex-cli 0.162.0",
                    }
                )
        self.assertIsNone(auth)
        self.assertEqual(status, "cli_version_mismatch")
        run.assert_not_called()

    def test_launch_rejects_api_key_status_before_codex_execution(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output_root = root / "output"
            output_root.mkdir()
            workspace = root / "workspace"
            workspace.mkdir()
            (workspace / ".qa-eval-output").mkdir()
            observations_path = root / "observations.json"
            codex_home = root / "homes" / f"{CODEX_HOME_PREFIX}agent-rejected"
            codex_home.parent.mkdir(mode=0o700)
            with (
                patch.object(codex_wsl2_bwrap_launcher, "_require_wsl2"),
                patch.object(
                    codex_wsl2_bwrap_launcher,
                    "AUTHENTICATION_SHELL_VISIBLE_RISK",
                    False,
                ),
                patch.object(
                    codex_wsl2_bwrap_launcher,
                    "AUTHENTICATION_REFRESH_PERSISTENCE_UNRESOLVED",
                    False,
                ),
                patch.object(
                    codex_wsl2_bwrap_launcher,
                    "AUTHENTICATION_PROCESS_CONCURRENCY_UNRESOLVED",
                    False,
                ),
                patch.object(
                    codex_wsl2_bwrap_launcher,
                    "verify_runtime",
                    return_value={"runtime": "synthetic"},
                ),
                patch.object(
                    codex_wsl2_bwrap_launcher,
                    "_auth_material",
                    return_value=(None, "api_key"),
                ),
                patch.object(codex_wsl2_bwrap_launcher.subprocess, "run") as run,
                patch.dict(
                    os.environ,
                    {
                        "OPENAI_API_KEY": "sk-synthetic-forbidden",
                        "CODEX_API_KEY": "synthetic-forbidden",
                    },
                ),
            ):
                exit_code = launch(
                    mode="agent",
                    output_root=output_root,
                    prompt="synthetic prompt",
                    observations_path=observations_path,
                    model="synthetic-model",
                    reasoning_effort="medium",
                    sandbox_policy="workspace-write",
                    workspace_root=workspace,
                    codex_home=codex_home,
                    runtime_root=root,
                )

            observations = json.loads(observations_path.read_text(encoding="utf-8"))
            self.assertEqual(exit_code, 2)
            self.assertEqual(observations["authentication_method"], "api_key")
            self.assertEqual(observations["authentication_check_status"], "rejected")
            self.assertEqual(observations["error"], "authentication_rejected")
            self.assertNotIn("sk-synthetic-forbidden", json.dumps(observations))
            self.assertFalse(codex_home.exists())
            run.assert_not_called()

    def test_auth_status_only_outputs_sanitized_chatgpt_classification(self) -> None:
        stdout = io.StringIO()
        synthetic_auth = "SYNTHETIC_AUTH_SECRET_MARKER"
        with (
            patch.object(
                codex_wsl2_bwrap_launcher,
                "verify_runtime",
                return_value={"codex_version": "codex-cli 0.163.0"},
            ),
            patch.object(
                codex_wsl2_bwrap_launcher,
                "_auth_material",
                return_value=(Path(synthetic_auth), "chatgpt_login"),
            ),
            patch("sys.stdout", stdout),
        ):
            exit_code = codex_wsl2_bwrap_launcher.main(["--auth-status-only"])

        result = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(result["authentication_method"], "chatgpt_login")
        self.assertEqual(result["codex_cli_version"], "0.163.0")
        self.assertEqual(result["runtime_digest_status"], "verified")
        self.assertNotIn(synthetic_auth, stdout.getvalue())

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
                profile = f"qa_eval_{mode}"
                self.assertNotIn("--sandbox", command)
                self.assertEqual(
                    command[command.index("--config") + 1],
                    f'default_permissions="{profile}"',
                )
                self.assertEqual(
                    command[command.index("--cd") + 1],
                    "/tmp" if mode == "judge" else "/workspace",
                )
                self.assertEqual(command.count("--skip-git-repo-check"), 1)
                self.assertEqual(
                    command[command.index("--ask-for-approval") + 1], "never"
                )
                self.assertEqual(command[command.index("--model") + 1], "model-test")
                self.assertIn('model_reasoning_effort="medium"', command)
                self.assertIn('web_search="disabled"', command)
                self.assertEqual(
                    command[command.index("--output-last-message") + 1],
                    "/tmp/final.md"
                    if mode == "judge"
                    else "/workspace/.qa-eval-output/final.md",
                )
                self.assertIn("exec", command)
                self.assertNotIn("--profile", command)
                self.assertNotIn("--mcp-config", command)
                self.assertNotIn("--dangerously-bypass-approvals-and-sandbox", command)
                self.assertNotIn("--yolo", command)

    def test_named_permission_profiles_deny_auth_without_changing_mode_rights(
        self,
    ) -> None:
        for mode in ("agent", "judge", "repair"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                home_parent = root / "homes"
                home_parent.mkdir(mode=0o700)
                home = home_parent / f"{CODEX_HOME_PREFIX}{mode}-profile"
                skill_name = "synthetic-skill" if mode == "repair" else None
                _prepare_codex_home(
                    home,
                    mode=mode,
                    reasoning_effort="max",
                    auth=None,
                    skill_name=skill_name,
                )

                config_text = (home / "config.toml").read_text(encoding="utf-8")
                config = tomllib.loads(config_text)
                profile_name = f"qa_eval_{mode}"
                profile = config["permissions"][profile_name]
                self.assertEqual(config["default_permissions"], profile_name)
                self.assertEqual(
                    profile["extends"],
                    ":read-only" if mode == "judge" else ":workspace",
                )
                self.assertFalse(profile["network"]["enabled"])
                self.assertEqual(profile["filesystem"]["/codex-home/auth.json"], "deny")
                self.assertNotIn("sandbox_mode", config)
                self.assertNotIn("sandbox_workspace_write", config)
                self.assertEqual(config["features"]["shell_tool"], mode != "judge")
                self.assertFalse(config["features"]["code_mode"])
                if mode == "repair":
                    self.assertEqual(
                        profile["workspace_roots"],
                        {"/workspace/.agents/skills/synthetic-skill": True},
                    )
                else:
                    self.assertNotIn("workspace_roots", profile)
                self.assertNotIn("SYNTHETIC_AUTH_MARKER", config_text)
                self.assertEqual((home.stat().st_mode & 0o777), 0o700)
                self.assertEqual((home / "config.toml").stat().st_mode & 0o777, 0o600)

    def test_sandbox_smoke_rejects_builtin_or_cross_mode_permission_profiles(
        self,
    ) -> None:
        with self.assertRaisesRegex(CodexWsl2LauncherError, "does not match its mode"):
            sandbox_smoke(
                mode="agent",
                workspace_root=None,
                output_root=None,
                permission_profile=":workspace",
            )

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

    def test_exec_argv_fingerprint_covers_mode_and_normalizes_attempt_output(
        self,
    ) -> None:
        for mode, sandbox_policy, output_root in (
            ("agent", "workspace-write", "/workspace/.qa-eval-output"),
            ("repair", "workspace-write", "/workspace/.qa-eval-output"),
            ("judge", "read-only", "/tmp"),
        ):
            with self.subTest(mode=mode):
                first = _codex_exec_argv(
                    mode=mode,
                    model="model-test",
                    reasoning_effort="medium",
                    sandbox_policy=sandbox_policy,
                    output_message_path=f"{output_root}/.codex-final-first.md",
                )
                second = _codex_exec_argv(
                    mode=mode,
                    model="model-test",
                    reasoning_effort="medium",
                    sandbox_policy=sandbox_policy,
                    output_message_path=f"{output_root}/.codex-final-second.md",
                )
                self.assertEqual(
                    codex_exec_argv_fingerprint(first, mode=mode),
                    codex_exec_argv_fingerprint(second, mode=mode),
                )
                second[second.index("--model") + 1] = "different-model"
                self.assertNotEqual(
                    codex_exec_argv_fingerprint(first, mode=mode),
                    codex_exec_argv_fingerprint(second, mode=mode),
                )

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
            cleanup = cleanup_argv(command)
            self.assertIsNotNone(cleanup)
            self.assertEqual(
                cleanup[cleanup.index("--cleanup-final-messages") + 1],
                str(output),
            )

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
            self.assertNotIn("--cleanup-final-messages", cleanup_argv(command))
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
            self.assertIn('default_permissions = "qa_eval_agent"', config)
            self.assertIn('extends = ":workspace"', config)
            self.assertIn('"/codex-home/auth.json" = "deny"', config)
            self.assertIn("enabled = false", config)
            self.assertNotIn("sandbox_mode", config)
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

    def test_attempt_refresh_copy_is_lost_at_cleanup_and_not_reused(self) -> None:
        old_marker = "SYNTHETIC_AUTH_STATE_OLD"
        refreshed_marker = "SYNTHETIC_AUTH_STATE_REFRESHED"
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            home_parent = root / "homes"
            home_parent.mkdir(mode=0o700)
            source_home = root / "source-home"
            source_home.mkdir(mode=0o700)
            auth_source = source_home / "auth.json"
            auth_source.write_text(old_marker, encoding="utf-8")
            first_home = home_parent / f"{CODEX_HOME_PREFIX}agent-first"
            second_home = home_parent / f"{CODEX_HOME_PREFIX}agent-second"

            _prepare_codex_home(
                first_home,
                mode="agent",
                reasoning_effort="max",
                auth=auth_source,
            )

            def fake_child_refresh(attempt_home: Path) -> None:
                (attempt_home / "auth.json").write_text(
                    refreshed_marker, encoding="utf-8"
                )

            fake_child_refresh(first_home)
            self.assertEqual(
                (first_home / "auth.json").read_text(encoding="utf-8"),
                refreshed_marker,
            )
            cleanup_codex_home(first_home, allowed_parent=home_parent)
            self.assertFalse(first_home.exists())

            _prepare_codex_home(
                second_home,
                mode="agent",
                reasoning_effort="max",
                auth=auth_source,
            )
            self.assertEqual(
                (second_home / "auth.json").read_text(encoding="utf-8"), old_marker
            )
            self.assertEqual(auth_source.read_text(encoding="utf-8"), old_marker)
            cleanup_codex_home(second_home, allowed_parent=home_parent)

    def test_timeout_cleanup_removes_only_reserved_final_message_files(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            final_message = output / (".codex-final-" + "a" * 32 + ".md")
            final_message.write_text("synthetic final message", encoding="utf-8")
            unrelated = output / "agent-output.md"
            unrelated.write_text("keep", encoding="utf-8")

            codex_wsl2_bwrap_launcher._cleanup_temporary_final_messages(output)

            self.assertFalse(final_message.exists())
            self.assertEqual(unrelated.read_text(encoding="utf-8"), "keep")

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
                '"/workspace/.agents/skills/synthetic-skill" = true',
                config,
            )
            self.assertIn('extends = ":workspace"', config)
            self.assertIn('"/codex-home/auth.json" = "deny"', config)
            cleanup_codex_home(home, allowed_parent=home_parent)
            with self.assertRaises(CodexWsl2LauncherError):
                _prepare_codex_home(
                    home,
                    mode="repair",
                    reasoning_effort="medium",
                    auth=None,
                    skill_name="../outside",
                )

    def test_sandbox_smoke_cleans_temporary_auth_and_paths_when_socket_bind_fails(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            home_parent = root / "homes"
            home_parent.mkdir(mode=0o700)
            outside_root = root / "outside"
            workspace = root / "workspace"
            workspace.mkdir()
            (workspace / ".qa-eval-output").mkdir()
            output_root = root / "output"
            output_root.mkdir()
            outside_root.mkdir()
            server = Mock()
            server.bind.side_effect = PermissionError("synthetic EPERM")

            with (
                patch.object(codex_wsl2_bwrap_launcher, "_require_wsl2"),
                patch.object(
                    codex_wsl2_bwrap_launcher,
                    "verify_runtime",
                    return_value={"runtime": "synthetic"},
                ),
                patch.object(
                    codex_wsl2_bwrap_launcher,
                    "_private_temp_root",
                    return_value=home_parent,
                ),
                patch.object(
                    codex_wsl2_bwrap_launcher.tempfile,
                    "mkdtemp",
                    return_value=str(outside_root),
                ),
                patch.object(
                    codex_wsl2_bwrap_launcher.socket, "socket", return_value=server
                ),
            ):
                with self.assertRaisesRegex(PermissionError, "synthetic EPERM"):
                    sandbox_smoke(
                        mode="agent",
                        workspace_root=workspace,
                        output_root=output_root,
                        permission_profile="qa_eval_agent",
                    )

            self.assertEqual(list(home_parent.iterdir()), [])
            self.assertFalse(outside_root.exists())
            self.assertFalse((workspace / "synthetic-escape").exists())
            server.close.assert_called_once()

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
                    permission_profile=f"qa_eval_{mode}",
                )
                self.assertTrue(
                    all(result["checks"].values()),
                    {"mode": mode, "checks": result["checks"]},
                )
                self.assertEqual(result["status"], "verified", result)
                self.assertNotIn("SYNTHETIC_AUTH_MARKER", json.dumps(result))
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
                permission_profile="qa_eval_judge",
            )
            self.assertTrue(all(judge["checks"].values()), judge["checks"])
            self.assertEqual(judge["status"], "verified", judge)
            self.assertNotIn("SYNTHETIC_AUTH_MARKER", json.dumps(judge))

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
