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

from scripts.skills.evals.agent.common import capture_codex_judge_output
from scripts.skills.evals.agent.tools.codex_judge_docker_launcher import (
    CodexJudgeLauncherError,
    _summarize_jsonl,
    launch,
    launcher_argv_for_profile,
)


class CodexJudgeDockerLauncherTests(unittest.TestCase):
    def _fake_docker(self, root: Path) -> tuple[Path, Path]:
        docker = root / "docker"
        argv_log = root / "captured-judge-argv.json"
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
                 if value.startswith("sha256:") or value == "codex-judge:0.163.0"),
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
            codex_home_mount = next(
                item for item in args if item.startswith("type=bind,")
                and "target=/codex-home" in item
            )
            fields = dict(part.split("=", 1) for part in codex_home_mount.split(","))
            home = Path(fields["source"])
            codex_index = command.index("codex")
            codex_argv = command[codex_index:]
            Path(os.environ["CODEX_JUDGE_LAUNCHER_TEST_ARGV"]).write_text(
                json.dumps({
                    "image": args[image_index],
                    "argv": codex_argv,
                    "auth_file_present": (home / "auth.json").is_file(),
                    "config": (home / "config.toml").read_text(encoding="utf-8"),
                    "prompt": sys.stdin.read(),
                    "home_mount_source": str(home),
                    "api_key_env_passed": "OPENAI_API_KEY" in args,
                }),
                encoding="utf-8",
            )
            events = [
                {"type": "thread.started"},
                {
                    "type": "item.completed",
                    "item": {
                    "type": "reasoning",
                    "text": "I will return the requested Judge JSON.",
                    },
                },
                {
                    "type": "item.completed",
                    "item": {
                        "type": "agent_message",
                        "text": '{"criteria":[]}',
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

    def _profile(self, docker: Path) -> dict:
        return {
            "model": "gpt-test-judge",
            "command_argv": [
                str(docker),
                "run",
                "--rm",
                "--read-only",
                "--cap-drop=ALL",
                "--security-opt=no-new-privileges",
                "-i",
                "--network",
                "bridge",
                "--mount",
                "type=tmpfs,target=/tmp",
                "sha256:" + "a" * 64,
                "codex",
                "exec",
            ],
            "cli_version": "codex-cli 0.163.0",
            "reasoning_effort": "medium",
            "sandbox_policy": "read-only",
            "approval_policy": "never",
            "launch_options": [],
            "tools": [],
            "mcp_servers": [],
            "skill_roots": [],
            "global_config": "disabled",
            "external_instructions": "disabled",
        }

    def test_judge_uses_separate_fixed_runtime_and_stdout_contains_only_final_json(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source_codex_home = root / "source-codex-home"
            source_codex_home.mkdir()
            (source_codex_home / "auth.json").write_text(
                '{"access_token":"test-only-secret"}', encoding="utf-8"
            )
            docker, argv_log = self._fake_docker(root)
            profile = self._profile(docker)
            observations_path = root / "launcher-observations.json"
            docker_argv = launcher_argv_for_profile(
                profile,
                docker_argv=profile["command_argv"],
                observations_path=observations_path,
            )
            stdout = io.StringIO()
            with (
                patch.dict(
                    os.environ,
                    {
                        "CODEX_HOME": str(source_codex_home),
                        "OPENAI_API_KEY": "",
                        "CODEX_JUDGE_LAUNCHER_TEST_ARGV": str(argv_log),
                    },
                    clear=False,
                ),
                patch("pathlib.Path.cwd", return_value=root),
                redirect_stdout(stdout),
                redirect_stderr(io.StringIO()),
            ):
                code = launch(
                    model=profile["model"],
                    reasoning_effort=profile["reasoning_effort"],
                    cli_version=profile["cli_version"],
                    sandbox_policy=profile["sandbox_policy"],
                    approval_policy=profile["approval_policy"],
                    docker_argv=docker_argv[docker_argv.index("--") + 1 :],
                    prompt="fixed isolated Judge prompt",
                    observations_path=observations_path,
                )

            self.assertEqual(code, 0)
            self.assertEqual(stdout.getvalue(), '{"criteria":[]}\n')
            observations = json.loads(observations_path.read_text(encoding="utf-8"))
            launch_info = json.loads(argv_log.read_text(encoding="utf-8"))
            self.assertEqual(observations["status"], "completed")
            self.assertEqual(observations["image"]["image_id"], "sha256:" + "a" * 64)
            self.assertEqual(launch_info["image"], "sha256:" + "a" * 64)
            self.assertEqual(launch_info["prompt"], "fixed isolated Judge prompt")
            self.assertTrue(launch_info["auth_file_present"])
            self.assertIn('sandbox_mode = "read-only"', launch_info["config"])
            self.assertEqual(
                launch_info["argv"][0:6],
                [
                    "codex",
                    "--no-daemon",
                    "--strict-config",
                    "--ask-for-approval",
                    "never",
                    "exec",
                ],
            )
            self.assertIn("--json", launch_info["argv"])
            self.assertIn("--sandbox", launch_info["argv"])
            self.assertNotIn("--search", launch_info["argv"])
            self.assertFalse(launch_info["api_key_env_passed"])
            self.assertEqual(observations["jsonl"]["event_count"], 4)
            self.assertFalse(observations["jsonl"]["tool_use_detected"])
            self.assertFalse(observations["web_search_enabled"])
            self.assertNotIn("test-only-secret", json.dumps(observations))
            self.assertFalse(Path(launch_info["home_mount_source"]).exists())

            captured = capture_codex_judge_output(
                stdout.getvalue(), observations_path=observations_path
            )
            self.assertEqual(captured["response"], '{"criteria":[]}\n')
            self.assertEqual(captured["status"], "completed")
            self.assertEqual(
                captured["launcher_observations"]["auth_mode"], "temporary_auth_file"
            )

    def test_judge_tool_event_makes_the_output_unverified(self) -> None:
        events = [
            {"type": "thread.started"},
            {
                "type": "item.completed",
                "item": {
                    "type": "command_execution",
                    "command": "cat /evaluator/secret.txt",
                    "exit_code": 0,
                },
            },
            {
                "type": "item.completed",
                "item": {"type": "agent_message", "text": '{"criteria":[]}'},
            },
            {"type": "turn.completed"},
        ]
        summary, response = _summarize_jsonl(
            "\n".join(json.dumps(event) for event in events).encode("utf-8")
        )
        self.assertEqual(summary["status"], "evidence_unverified")
        self.assertTrue(summary["tool_use_detected"])
        self.assertIsNone(response)

    def test_codex_judge_profile_rejects_extra_skills_and_mcp(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            docker, _ = self._fake_docker(root)
            profile = self._profile(docker)
            profile["mcp_servers"] = ["example"]
            with self.assertRaisesRegex(CodexJudgeLauncherError, "disable user tools"):
                launcher_argv_for_profile(
                    profile,
                    docker_argv=profile["command_argv"],
                    observations_path=root / "observations.json",
                )


if __name__ == "__main__":
    unittest.main()
