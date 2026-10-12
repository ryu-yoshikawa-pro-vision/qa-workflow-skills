"""Execpolicy rules are loaded and probed by the pinned Codex CLI itself."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CODEX = shutil.which("codex")
RULES = [
    ROOT / ".codex" / "rules" / "20-risky-prompt.rules",
    ROOT / ".codex" / "rules" / "30-destructive-forbidden.rules",
]


@unittest.skipUnless(CODEX, "Codex CLI 0.160.0 is required for execpolicy tests")
class ExecpolicyCliTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if os.name == "nt":
            cls.command_prefix = [
                os.environ.get("COMSPEC", "cmd.exe"),
                "/d",
                "/c",
                CODEX,
            ]
        else:
            cls.command_prefix = [CODEX]
        version = subprocess.run(
            [*cls.command_prefix, "--version"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if version.returncode != 0 or version.stdout.strip() != "codex-cli 0.160.0":
            raise AssertionError(
                f"expected codex-cli 0.160.0; got {version.stdout.strip()!r} "
                f"(exit {version.returncode})"
            )

    def decision(self, *command: str) -> str:
        args = [*self.command_prefix, "execpolicy", "check"]
        for rule in RULES:
            args.extend(["--rules", str(rule)])
        args.extend(["--", *command])
        result = subprocess.run(
            args,
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        response = json.loads(result.stdout)
        return response.get("decision", "no_match")

    def test_each_rules_file_loads_and_runs_its_embedded_match_examples(self) -> None:
        for rule in RULES:
            with self.subTest(rule=rule.name):
                args = [
                    *self.command_prefix,
                    "execpolicy",
                    "check",
                    "--rules",
                    str(rule),
                    "--",
                    "git",
                    "status",
                ]
                result = subprocess.run(
                    args,
                    cwd=ROOT,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(
                    json.loads(result.stdout).get("decision", "no_match"), "no_match"
                )

    def test_git_high_impact_families_prompt(self) -> None:
        cases = (
            ("git", "commit", "--amend"),
            ("git.exe", "commit", "--amend"),
            ("git", "push", "--force", "origin", "feature"),
            ("git.exe", "push", "origin", "feature"),
            ("git", "reset", "--hard", "HEAD~1"),
            ("git.exe", "restore", "."),
            ("git", "checkout", "--", "."),
            ("git.exe", "switch", "--discard-changes", "feature/other"),
            ("git", "switch", "-c", "feature/new-work"),
            ("git.exe", "switch", "feature/existing-work"),
            ("git", "branch"),
            ("git.exe", "stash", "push"),
        )
        for command in cases:
            with self.subTest(command=command):
                self.assertEqual(self.decision(*command), "prompt")

    def test_github_cli_builtin_mutation_aliases_prompt_for_both_executables(
        self,
    ) -> None:
        aliases = (
            ("pr", "co", "123"),
            ("pr", "new", "--title", "test"),
            ("issue", "new", "--title", "test"),
            ("repo", "new", "example"),
            ("repo", "autolink", "new", "T-", "url"),
            ("secret", "remove", "TOKEN"),
            ("variable", "remove", "NAME"),
            ("skill", "add", "owner/repo", "skill"),
            ("skills", "add", "owner/repo", "skill"),
            ("at", "download", "owner/repo", "--name", "artifact"),
            ("agent-task", "create", "task"),
            ("agent-tasks", "create", "task"),
            ("agent", "create", "task"),
            ("agents", "create", "task"),
            ("discussion", "create", "--title", "test"),
            ("discussion", "comment", "123", "--body", "test"),
            ("discussion", "edit", "123", "--title", "test"),
            ("release", "new", "v1"),
        )
        for executable in ("gh", "gh.exe"):
            for alias in aliases:
                command = (executable, *alias)
                with self.subTest(command=command):
                    self.assertEqual(self.decision(*command), "prompt")

    def test_github_family_prompt_and_read_only_boundaries(self) -> None:
        prompt = (
            ("gh", "auth", "status"),
            ("gh.exe", "gist", "list"),
            ("gh", "project", "list"),
            ("gh.exe", "attestation", "verify", "artifact.bin", "--owner", "example"),
            ("gh", "pr", "merge", "123", "-R", "owner/repo"),
            ("gh.exe", "issue", "close", "123"),
            ("gh", "workflow", "run", "ci.yml"),
            ("gh.exe", "run", "download", "123"),
            ("gh", "repo", "rename", "new-name"),
            ("gh.exe", "cache", "delete", "--all"),
            ("curl", "https://example.invalid/file"),
            ("wget", "https://example.invalid/file"),
            ("rsync", "-a", "src/", "dst/"),
            ("mv", "a.txt", "b.txt"),
            ("Move-Item", "a.txt", "b.txt"),
            ("Rename-Item", "a.txt", "b.txt"),
        )
        for command in prompt:
            with self.subTest(command=command):
                self.assertEqual(self.decision(*command), "prompt")

        no_match = (
            ("git", "status"),
            ("git.exe", "diff", "--stat"),
            ("git", "add", "sample.txt"),
            ("git", "-c", "user.name=test", "push", "origin", "feature"),
            ("git.exe", "--no-pager", "reset", "--hard"),
            ("gh", "pr", "list"),
            ("gh.exe", "pr", "view", "123"),
            ("gh", "issue", "list"),
            ("gh.exe", "workflow", "view", "ci.yml"),
            ("gh", "run", "view", "123"),
            ("gh.exe", "release", "view", "v1"),
            ("gh", "secret", "list"),
            ("gh.exe", "variable", "get", "NAME"),
            ("gh", "cache", "list"),
            ("gh.exe", "label", "list"),
            ("gh", "skill", "list"),
            ("gh.exe", "skills", "preview", "owner/repo", "skill"),
            ("gh", "search", "prs", "test"),
        )
        for command in no_match:
            with self.subTest(command=command):
                self.assertEqual(self.decision(*command), "no_match")

    def test_forbidden_command_families(self) -> None:
        cases = (
            ("gh", "api", "/repos/owner/repo/issues"),
            ("gh.exe", "api", "/repos/owner/repo/issues"),
            ("gh", "repo", "sync", "owner/repo"),
            ("gh.exe", "repo", "sync", "owner/repo"),
            ("gh", "auth", "token"),
            ("gh.exe", "auth", "token"),
            ("git", "clean", "-fd"),
            ("git.exe", "rm", "file.txt"),
            ("git", "update-ref", "-d", "refs/heads/old"),
            ("rm", "file.txt"),
            ("Remove-Item", "file.txt"),
        )
        for command in cases:
            with self.subTest(command=command):
                self.assertEqual(self.decision(*command), "forbidden")


if __name__ == "__main__":
    unittest.main()
