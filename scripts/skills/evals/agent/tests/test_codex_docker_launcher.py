from __future__ import annotations

import io
import json
import os
import tempfile
import textwrap
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from scripts.skills.evals.agent.common import capture_codex_jsonl_trace
from scripts.skills.evals.agent.tools.codex_docker_launcher import (
    launch,
    summarize_codex_jsonl,
)


class CodexDockerLauncherTests(unittest.TestCase):
    def _fake_docker(self, root: Path) -> tuple[Path, Path]:
        docker = root / "docker"
        argv_log = root / "captured-codex-argv.json"
        script = textwrap.dedent(
            r"""
            #!/usr/bin/env python3
            import json
            import os
            import sys
            from pathlib import Path

            args = sys.argv[1:]
            if args[:2] == ["image", "inspect"]:
                print("sha256:" + "a" * 64)
                raise SystemExit(0)
            if args[0] != "run":
                raise SystemExit(2)
            image_index = next(
                (index for index, value in enumerate(args)
                 if value.startswith("sha256:") or value == "codex-agent:0.163.0"),
                -1,
            )
            if image_index < 0:
                raise SystemExit(2)
            command = args[image_index + 1:]
            if command == ["codex", "--version"]:
                print("codex-cli 0.163.0")
                raise SystemExit(0)
            if command == ["python3.11", "--version"]:
                print("Python 3.11.17")
                raise SystemExit(0)
            output_mount = next(
                item for item in args if item.startswith("type=bind,")
                and "target=/workspace/.qa-eval-output" in item
            )
            output_fields = dict(part.split("=", 1) for part in output_mount.split(","))
            auth_mount = next(
                item for item in args if item.startswith("type=bind,")
                and "target=/codex-home" in item
            )
            auth_fields = dict(part.split("=", 1) for part in auth_mount.split(","))
            codex_home = Path(auth_fields["source"])
            output_path = Path(output_fields["source"])
            message_path = command[command.index("--output-last-message") + 1]
            (output_path / Path(message_path).name).write_text(
                "Final output. Bearer abcdefghijklmnopqrstuv", encoding="utf-8"
            )
            Path(os.environ["CODEX_LAUNCHER_TEST_ARGV"]).write_text(
                json.dumps({
                    "argv": command,
                    "image": args[image_index],
                    "auth_file_present": (codex_home / "auth.json").is_file(),
                    "auth_mount_source": str(codex_home),
                    "auth_mode_env": next(
                        (args[index + 1] for index, value in enumerate(args[:-1])
                         if value == "--env" and args[index + 1].startswith("CODEX_HOME=")),
                        None,
                    ),
                    "home_env": next(
                        (args[index + 1] for index, value in enumerate(args[:-1])
                         if value == "--env" and args[index + 1].startswith("HOME=")),
                        None,
                    ),
                }),
                encoding="utf-8",
            )
            events = [
                {"type": "thread.started"},
                {
                    "type": "item.completed",
                    "item": {
                        "type": "command_execution",
                        "command": "cat /workspace/.agents/skills/qa-workflow/SKILL.md && echo Bearer abcdefghijklmnopqrstuv",
                        "exit_code": 0,
                    },
                },
                {
                    "type": "item.completed",
                    "item": {
                        "type": "agent_message",
                        "text": "Final output. Bearer abcdefghijklmnopqrstuv",
                    },
                },
                {"type": "turn.completed"},
            ]
            sys.stdout.write("\n".join(json.dumps(item) for item in events) + "\n")
            """
        ).lstrip()
        docker.write_text(script, encoding="utf-8")
        docker.chmod(0o700)
        return docker, argv_log

    def test_final_message_without_a_successful_completed_turn_is_unverified(
        self,
    ) -> None:
        final_message = {
            "type": "item.completed",
            "item": {"type": "agent_message", "text": "Partial output."},
        }
        cases = (
            [final_message],
            [final_message, {"type": "turn.failed"}],
            [final_message, {"type": "error", "message": "request failed"}],
            [final_message, {"type": "turn.completed"}, {"type": "error"}],
        )
        for events in cases:
            with self.subTest(event_types=[event["type"] for event in events]):
                summary, response = summarize_codex_jsonl(
                    ("\n".join(json.dumps(event) for event in events) + "\n").encode()
                )
                self.assertEqual(summary["status"], "evidence_unverified")
                self.assertEqual(response, "Partial output.")

    def test_launcher_uses_supported_codex_flags_and_temporary_auth_home(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / "output"
            workspace = root / "workspace"
            source_codex_home = root / "user-codex-home"
            output.mkdir()
            workspace.mkdir()
            source_codex_home.mkdir()
            (source_codex_home / "auth.json").write_text(
                '{"access_token":"test-only-secret"}', encoding="utf-8"
            )
            docker, argv_log = self._fake_docker(root)
            docker_argv = [
                str(docker),
                "run",
                "--rm",
                "-i",
                "--read-only",
                "--cap-drop=ALL",
                "--security-opt=no-new-privileges",
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
                "sha256:" + "a" * 64,
                "codex",
                "exec",
            ]
            stdout = io.StringIO()
            with (
                patch.dict(
                    os.environ,
                    {
                        "CODEX_HOME": str(source_codex_home),
                        "OPENAI_API_KEY": "",
                        "CODEX_LAUNCHER_TEST_ARGV": str(argv_log),
                    },
                    clear=False,
                ),
                redirect_stdout(stdout),
                redirect_stderr(io.StringIO()),
            ):
                code = launch(
                    output_root=output,
                    model="gpt-test-model",
                    reasoning_effort="medium",
                    cli_version="codex-cli 0.163.0",
                    sandbox_policy="workspace-write",
                    docker_argv=docker_argv,
                    prompt="fixed test prompt",
                )

            self.assertEqual(code, 0, stdout.getvalue())
            envelope = json.loads(stdout.getvalue())
            self.assertTrue(envelope["observations"]["final_message_redacted"])
            self.assertIsNone(envelope["observations"]["final_message_sha256"])
            captured = capture_codex_jsonl_trace(
                json.dumps(envelope), skill_names=["qa-workflow"]
            )
            launch_argv = json.loads(argv_log.read_text(encoding="utf-8"))
            codex_argv = launch_argv["argv"]
            self.assertEqual(launch_argv["image"], "sha256:" + "a" * 64)
            exec_index = codex_argv.index("exec")
            self.assertEqual(
                codex_argv[exec_index - 4 : exec_index],
                [
                    "--no-daemon",
                    "--strict-config",
                    "--ask-for-approval",
                    "never",
                ],
            )
            self.assertIn("--output-last-message", codex_argv)
            self.assertEqual(captured["final_message"], "Final output. [redacted]")
            self.assertEqual(
                captured["skill_use_observation"]["qa-workflow"], "observed"
            )
            self.assertEqual(
                captured["launcher_observations"]["image"]["python_version"],
                "Python 3.11.17",
            )
            self.assertTrue(captured["redacted"])
            self.assertTrue(launch_argv["auth_file_present"])
            self.assertEqual(launch_argv["auth_mode_env"], "CODEX_HOME=/codex-home")
            self.assertEqual(launch_argv["home_env"], "HOME=/tmp")
            self.assertEqual(
                captured["launcher_observations"]["auth_mode"], "temporary_auth_file"
            )
            self.assertNotIn("test-only-secret", stdout.getvalue())
            self.assertNotIn("abcdefghijklmnopqrstuv", stdout.getvalue())
            self.assertFalse(Path(launch_argv["auth_mount_source"]).exists())
            self.assertEqual(list(output.iterdir()), [])

    def test_launcher_accepts_only_the_selected_writable_skill_in_repair_mode(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / "output"
            workspace = root / "workspace"
            skill_root = root / "qa-workflow"
            source_codex_home = root / "user-codex-home"
            output.mkdir()
            workspace.mkdir()
            skill_root.mkdir()
            source_codex_home.mkdir()
            (source_codex_home / "auth.json").write_text(
                '{"access_token":"test-only-secret"}', encoding="utf-8"
            )
            docker, argv_log = self._fake_docker(root)
            docker_argv = [
                str(docker),
                "run",
                "--rm",
                "-i",
                "--read-only",
                "--cap-drop=ALL",
                "--security-opt=no-new-privileges",
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
                "sha256:" + "a" * 64,
                "codex",
                "exec",
            ]
            stdout = io.StringIO()
            with (
                patch.dict(
                    os.environ,
                    {
                        "CODEX_HOME": str(source_codex_home),
                        "OPENAI_API_KEY": "",
                        "CODEX_LAUNCHER_TEST_ARGV": str(argv_log),
                    },
                    clear=False,
                ),
                redirect_stdout(stdout),
                redirect_stderr(io.StringIO()),
            ):
                code = launch(
                    output_root=output,
                    model="gpt-test-model",
                    reasoning_effort="medium",
                    cli_version="codex-cli 0.163.0",
                    sandbox_policy="workspace-write",
                    docker_argv=docker_argv,
                    prompt="fixed repair prompt",
                    mode="repair",
                    skill_name="qa-workflow",
                )
            self.assertEqual(code, 0, stdout.getvalue())
            envelope = json.loads(stdout.getvalue())
            self.assertEqual(envelope["observations"]["mode"], "repair")
            self.assertEqual(envelope["observations"]["status"], "completed")
            self.assertEqual(list(output.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
