"""Repository-local Codex configuration and execpolicy contracts."""

from __future__ import annotations

import base64
import subprocess
import tomllib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / ".codex" / "config.toml"
class CodexConfigTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config_text = CONFIG_PATH.read_text(encoding="utf-8")
        cls.config = tomllib.loads(cls.config_text)

    def test_granular_approval_and_primary_profile_contract(self) -> None:
        self.assertEqual(self.config["sandbox_mode"], "workspace-write")
        self.assertEqual(self.config["approvals_reviewer"], "auto_review")
        self.assertEqual(
            self.config["approval_policy"],
            {
                "granular": {
                    "sandbox_approval": True,
                    "rules": True,
                    "mcp_elicitations": False,
                    "request_permissions": False,
                    "skill_approval": False,
                }
            },
        )
        features = self.config["features"]
        self.assertTrue(features["unified_exec"])
        self.assertFalse(features["unified_exec_tty"])
        self.assertNotIn("SessionStart", self.config.get("hooks", {}))
        self.assertNotIn("additionalContextLimit", self.config)
        self.assertNotIn("additionalContextLimit = 0", self.config_text)

    def test_exactly_four_agents_use_role_override_files(self) -> None:
        agents = self.config["agents"]
        expected = {
            "code_researcher",
            "implementation_worker",
            "test_investigator",
            "quality_gate_runner",
        }
        self.assertEqual(set(agents) - {"max_concurrent_threads_per_session"}, expected)
        for name in expected:
            with self.subTest(agent=name):
                role = agents[name]
                self.assertTrue(role["description"])
                agent_path = ROOT / ".codex" / role["config_file"]
                agent = tomllib.loads(agent_path.read_text(encoding="utf-8"))
                self.assertEqual(set(agent), {"developer_instructions"})
                self.assertTrue(agent["developer_instructions"].strip())

    def test_one_pre_tool_use_bash_hook_and_transport_commands(self) -> None:
        hooks = self.config["hooks"]
        self.assertEqual(set(hooks), {"PreToolUse"})
        pre_tool_use = hooks["PreToolUse"]
        self.assertEqual(len(pre_tool_use), 1)
        self.assertEqual(pre_tool_use[0]["matcher"], "^Bash$")
        hook_entries = pre_tool_use[0]["hooks"]
        self.assertEqual(len(hook_entries), 1)
        hook = hook_entries[0]
        self.assertEqual(hook["type"], "command")
        self.assertIn(
            'node "$repo_root/.codex/hooks/pre_tool_use_policy.mjs"', hook["command"]
        )
        self.assertRegex(
            hook["command_windows"],
            r"^powershell\.exe -NoProfile -NonInteractive -EncodedCommand [A-Za-z0-9+/=]+$",
        )
        payload64 = hook["command_windows"].rsplit(" ", 1)[1]
        payload = base64.b64decode(payload64).decode("utf-16-le")
        self.assertTrue(payload.startswith("$ProgressPreference = 'SilentlyContinue'"))
        self.assertIn("git rev-parse --show-toplevel", payload)
        self.assertIn(
            "$rootOutput = @(& git rev-parse --show-toplevel 2>$null)", payload
        )
        self.assertIn("$gitExit = $LASTEXITCODE", payload)
        self.assertNotIn("Select-Object", payload)
        self.assertIn("Set-Location -LiteralPath $root -ErrorAction Stop", payload)
        self.assertIn("pre_tool_use_policy_windows.ps1", payload)
        self.assertIn("[System.IO.File]::ReadAllText($launcher)", payload)
        self.assertIn("[scriptblock]::Create($source)", payload)
        self.assertNotIn('"', hook["command_windows"])

    def test_execpolicy_files_have_no_allow_rules(self) -> None:
        actual = [
            (ROOT / ".codex" / "rules" / "20-risky-prompt.rules")
            .read_text(encoding="utf-8")
            .rstrip(),
            (ROOT / ".codex" / "rules" / "30-destructive-forbidden.rules")
            .read_text(encoding="utf-8")
            .rstrip(),
        ]
        self.assertNotIn('decision = "allow"', "\n".join(actual))

    def test_gitignore_only_reopens_repository_owned_harness_paths(self) -> None:
        owned = (
            "AGENTS.md",
            "PLANS.md",
            "CODE_REVIEW.md",
            "scripts/format_tracked.py",
            ".agents/skills/feature-plan/SKILL.md",
            ".agents/skills/code-review/references/review-workflow.md",
            ".codex/config.toml",
            ".codex/agents/code_researcher.toml",
            ".codex/hooks/pre_tool_use_policy.mjs",
            ".codex/rules/README.md",
        )
        local_only = (
            "scripts/unrelated.py",
            ".agents/local-skill/SKILL.md",
            ".codex/runs/session/events.jsonl",
            ".codex/tmp/temporary.txt",
            ".codex/unknown-local-file.txt",
        )
        safe_directory = str(ROOT).replace("\\", "/")
        for path in owned:
            with self.subTest(path=path, expected="tracked"):
                result = subprocess.run(
                    [
                        "git",
                        "-c",
                        f"safe.directory={safe_directory}",
                        "check-ignore",
                        "--no-index",
                        "--",
                        path,
                    ],
                    cwd=ROOT,
                    capture_output=True,
                    check=False,
                )
                self.assertEqual(
                    result.returncode,
                    1,
                    result.stderr.decode(errors="replace")
                    or result.stdout.decode(errors="replace"),
                )
        for path in local_only:
            with self.subTest(path=path, expected="ignored"):
                result = subprocess.run(
                    [
                        "git",
                        "-c",
                        f"safe.directory={safe_directory}",
                        "check-ignore",
                        "--no-index",
                        "--",
                        path,
                    ],
                    cwd=ROOT,
                    capture_output=True,
                    check=False,
                )
                self.assertEqual(
                    result.returncode, 0, result.stderr.decode(errors="replace") or path
                )


if __name__ == "__main__":
    unittest.main()
