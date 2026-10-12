"""Behavioral contract tests for the repository PreToolUse Hook."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HOOK = ROOT / ".codex" / "hooks" / "pre_tool_use_policy.mjs"
NODE = shutil.which("node")
if NODE is None:
    local_node = (
        Path(tempfile.gettempdir())
        / "qa-workflow-skills-validation"
        / "node-tools"
        / "node.exe"
    )
    if local_node.is_file():
        NODE = str(local_node)


@unittest.skipUnless(NODE, "Node.js 24 is required by the harness contract")
class HookTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="hook repository with spaces ")
        self.repo = Path(self.temp.name) / "repository with spaces"
        self.repo.mkdir()
        subprocess.run(["git", "init", "-q", "-b", "main"], cwd=self.repo, check=True)
        subprocess.run(
            ["git", "config", "user.name", "Hook Test"], cwd=self.repo, check=True
        )
        subprocess.run(
            ["git", "config", "user.email", "hook@example.invalid"],
            cwd=self.repo,
            check=True,
        )
        (self.repo / "tracked.txt").write_text("fixture\n", encoding="utf-8")
        subprocess.run(["git", "add", "tracked.txt"], cwd=self.repo, check=True)
        subprocess.run(["git", "commit", "-qm", "fixture"], cwd=self.repo, check=True)
        subprocess.run(["git", "branch", "feature/existing"], cwd=self.repo, check=True)
        subprocess.run(["git", "branch", "feature/target"], cwd=self.repo, check=True)
        subprocess.run(
            [
                "git",
                "symbolic-ref",
                "refs/remotes/origin/HEAD",
                "refs/remotes/origin/main",
            ],
            cwd=self.repo,
            check=True,
        )
        subprocess.run(
            ["git", "switch", "feature/existing"],
            cwd=self.repo,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        reported_root = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=self.repo,
            text=True,
            encoding="utf-8",
        ).strip()
        self.posix_root = os.path.normpath(reported_root)
        self.posix_prefix = f"cd '{self.posix_root}' && "
        self.ps_root = self.posix_root.replace("'", "''")
        self.ps_prefix = (
            f"Set-Location -LiteralPath '{self.ps_root}' -ErrorAction Stop; "
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def run_hook(self, command: str, *, cwd: Path | None = None):
        payload = {"tool_name": "Bash", "tool_input": {"command": command}}
        return subprocess.run(
            [NODE, str(HOOK)],
            cwd=cwd or self.repo,
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            check=False,
        )

    def assert_denied(self, command: str, reason: str | None = None) -> None:
        result = self.run_hook(command)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(result.stdout, command)
        response = json.loads(result.stdout)
        output = response["hookSpecificOutput"]
        self.assertEqual(output["permissionDecision"], "deny", command)
        if reason:
            self.assertIn(reason, output["permissionDecisionReason"])

    def assert_hook_allows(self, command: str) -> None:
        result = self.run_hook(command)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "", command)

    def test_malformed_payload_blocks_and_safe_input_is_silent(self) -> None:
        malformed = subprocess.run(
            [NODE, str(HOOK)], cwd=self.repo, input="{", text=True, capture_output=True
        )
        self.assertEqual(malformed.returncode, 2)
        self.assertIn("invalid JSON", malformed.stderr)
        self.assert_hook_allows("git status")

    def test_stdin_failure_is_diagnostic_and_fails_closed(self) -> None:
        script = (
            'process.stdin.setEncoding = () => { throw new Error("fixture stdin failure"); };\n'
            f"await import({json.dumps(HOOK.as_uri())});\n"
        )
        result = subprocess.run(
            [NODE, "--input-type=module", "-e", script],
            cwd=self.repo,
            input="",
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertIn("PreToolUse policy hook: fixture stdin failure", result.stderr)

    def test_feature_branch_normal_git_and_gh_commands_reach_execpolicy(self) -> None:
        subprocess.run(["git", "switch", "feature/existing"], cwd=self.repo, check=True)
        for command in (
            self.posix_prefix + "git push origin feature/existing",
            self.posix_prefix + "git.exe push origin feature/existing",
            self.posix_prefix + "git commit -m test",
            self.ps_prefix + "git.exe push origin feature/existing",
            "gh pr merge 123 -R owner/repo",
            "gh.exe pr merge 123 -R owner/repo",
            "gh pr view 123 -R owner/repo",
            "git status",
        ):
            with self.subTest(command=command):
                self.assert_hook_allows(command)

    def test_protected_branch_mutations_are_denied_except_two_switch_forms(
        self,
    ) -> None:
        subprocess.run(
            ["git", "switch", "main"],
            cwd=self.repo,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self.assert_hook_allows("git branch -vv")
        for command in (
            self.posix_prefix + "git commit -m test",
            self.posix_prefix + "git reset 'HEAD~1'",
            self.ps_prefix + "git.exe push origin feature",
            self.posix_prefix + "git branch -v -D feature/foo",
            self.posix_prefix + "git branch -d feature/foo",
            self.posix_prefix + "git branch -vv -m main renamed-main",
            self.posix_prefix + "git branch -M main renamed-main",
            self.posix_prefix + "git branch -c main copied-main",
            self.posix_prefix + "git branch -C main copied-main",
            self.posix_prefix + "git branch -v --delete feature/foo",
            self.posix_prefix + "git branch --move main renamed-main",
            self.posix_prefix + "git branch --copy main copied-main",
            self.posix_prefix + "git branch --list -D feature/foo",
            self.posix_prefix + "git branch --force main HEAD",
            self.posix_prefix + "git branch --set-upstream-to=origin/main",
            self.posix_prefix + "git branch --unset-upstream",
            self.posix_prefix + "git branch --edit-description",
        ):
            with self.subTest(command=command):
                self.assert_denied(command, "protected branch")

        self.assert_hook_allows(
            self.posix_prefix + "git switch -c feature/new-from-main"
        )
        self.assert_hook_allows(self.ps_prefix + "git.exe switch feature/existing")
        for command in (
            self.posix_prefix + "git switch -c main",
            self.posix_prefix + "git switch master",
            self.posix_prefix + "git switch missing/local-branch",
            self.posix_prefix + "git switch -C feature/existing",
            self.posix_prefix + "git switch --discard-changes feature/existing",
            self.posix_prefix + "git switch -c feature/new origin/main",
            self.posix_prefix + "git switch feature/existing --track",
            self.ps_prefix + "git.exe switch -c feature/new --track",
        ):
            with self.subTest(command=command):
                self.assert_denied(command)

    def test_branch_listing_requires_a_read_only_argument_sequence(self) -> None:
        for command in (
            "git branch",
            "git branch -v",
            "git branch -vv",
            "git branch --list",
            "git branch --show-current",
            "git branch -a",
            "git branch -r",
            "git branch --all",
            "git branch --remotes",
            "git branch --merged",
            "git branch --merged=HEAD",
            "git branch --no-merged",
            "git branch --no-merged=HEAD",
            "git branch --contains HEAD",
            "git branch --contains=HEAD",
            "git branch --points-at HEAD",
            "git branch --sort=refname",
            "git branch --format='%(refname)'",
            "git branch --list feature/existing",
            "git branch --list -- -D",
        ):
            with self.subTest(command=command):
                self.assert_hook_allows(command)

    def test_feature_branch_mutations_reach_execpolicy_only_with_canonical_root(
        self,
    ) -> None:
        subprocess.run(["git", "switch", "feature/existing"], cwd=self.repo, check=True)
        for command in (
            self.posix_prefix + "git branch -v -D main",
            self.posix_prefix + "git branch -vv -m main renamed-main",
            self.posix_prefix + "git branch -f main HEAD",
        ):
            with self.subTest(command=command):
                self.assert_denied(command, "protected branch")

        for command in (
            self.posix_prefix + "git branch -d feature/target",
            self.posix_prefix + "git branch -D feature/target",
            self.posix_prefix + "git branch -m feature/target feature/renamed",
            self.posix_prefix + "git branch -M feature/target feature/renamed-force",
            self.posix_prefix + "git branch -c feature/target feature/copied",
            self.posix_prefix + "git branch -C feature/target feature/copied-force",
            self.posix_prefix + "git branch -f feature/target main",
            self.posix_prefix
            + "git branch --set-upstream-to=origin/main feature/existing",
            self.posix_prefix + "git branch --unset-upstream",
            self.posix_prefix + "git branch --edit-description feature/existing",
            self.posix_prefix + "git branch -v",
        ):
            with self.subTest(command=command):
                self.assert_hook_allows(command)

        for command in (
            "git branch -d feature/target",
            "git branch -D feature/target",
            "git branch --set-upstream-to=origin/main feature/existing",
            "git branch --unset-upstream",
            "git branch --edit-description feature/existing",
        ):
            with self.subTest(command=command):
                self.assert_denied(command)

    def test_state_changing_git_requires_literal_canonical_cwd_and_one_command(
        self,
    ) -> None:
        self.assert_hook_allows(self.posix_prefix + "git push origin feature/existing")
        self.assert_hook_allows(self.ps_prefix + "git.exe push origin feature/existing")
        for command in (
            "git push origin feature/existing",
            f'cd "{self.posix_root}" && git push origin feature/existing',
            f"cd '{self.posix_root}/.' && git push origin feature/existing",
            f"cd '{self.posix_root}' && git push origin feature/existing && git status",
            'cd "$(git rev-parse --show-toplevel)" && git push origin feature/existing',
            f"Set-Location -LiteralPath '{self.ps_root}'; git.exe push origin feature/existing",
            f"Set-Location -LiteralPath '{self.ps_root}' -ErrorAction Continue; git.exe push origin feature/existing",
            f"cd '{self.posix_root}' && git -C . push origin feature/existing",
            f"cd '{self.posix_root}' && git --git-dir=.git push origin feature/existing",
            f"cd '{self.posix_root}' && git --work-tree=. push origin feature/existing",
            f"cd '{self.posix_root}' && GIT_DIR=.git git push origin feature/existing",
            f"cd '{self.posix_root}' && env GIT_DIR=.git git push origin feature/existing",
            f"cd '{self.posix_root}' && command git push origin feature/existing",
        ):
            with self.subTest(command=command):
                self.assert_denied(command)

    def test_git_option_ordering_and_shell_expansions_are_denied(self) -> None:
        for command in (
            self.posix_prefix + "git -c user.name=test push origin feature/existing",
            self.posix_prefix + "git.exe --no-pager reset --hard",
            self.ps_prefix + "git.exe -C . push origin feature/existing",
            self.ps_prefix + "git.exe --no-pager reset --hard",
            self.ps_prefix + "git.exe reset HEAD~1",
            self.ps_prefix + "git.exe rm *.md",
            self.posix_prefix + "git reset HEAD~1",
            self.posix_prefix + "git rm *.md",
            self.posix_prefix + 'git "$GIT_SUBCOMMAND" origin feature/existing',
            self.ps_prefix + 'git.exe "$env:GIT_SUBCOMMAND" origin feature/existing',
            self.posix_prefix + 'gh pr create --body "$BODY"',
            'gh.exe pr create --body "$BODY"',
        ):
            with self.subTest(command=command):
                self.assert_denied(command)

        for command in (
            self.posix_prefix + "git reset 'HEAD~1'",
            self.posix_prefix + "git rm '*.md'",
            "gh pr create --body-file body.md",
            self.ps_prefix + "git.exe reset 'HEAD~1'",
            self.ps_prefix + "git.exe rm '*.md'",
            "gh.exe pr create --body-file body.md",
        ):
            with self.subTest(command=command):
                self.assert_hook_allows(command)

    def test_explicit_push_to_protected_refs_is_denied_from_feature_branch(
        self,
    ) -> None:
        subprocess.run(["git", "switch", "feature/existing"], cwd=self.repo, check=True)
        targets = (
            "main",
            "HEAD:main",
            "feature/existing:refs/heads/main",
            ":main",
            "--delete main",
            "+HEAD:main",
            "feature/existing HEAD:refs/heads/main",
        )
        for target in targets:
            for prefix in (
                self.posix_prefix + "git push origin ",
                self.ps_prefix + "git.exe push origin ",
            ):
                command = prefix + target
                with self.subTest(command=command):
                    self.assert_denied(command, "protected branch")
        self.assert_hook_allows(self.posix_prefix + "git push origin feature/existing")
        self.assert_hook_allows(
            self.posix_prefix + "git push origin HEAD:feature/existing"
        )

    def test_gh_leading_options_and_token_display_are_denied(self) -> None:
        for command in (
            "gh -R owner/repo pr merge 123",
            "gh.exe -R owner/repo pr merge 123",
            "gh pr -R owner/repo merge 123",
            "gh.exe pr -R owner/repo merge 123",
            "gh repo autolink -R owner/repo create T- https://example.invalid/T-<num>",
            "gh.exe repo autolink -R owner/repo create T- url",
            "gh auth status --show-token",
            "gh.exe auth status -t",
            "gh auth status --json hosts --show-token",
            "gh.exe auth status --show-token=always",
        ):
            with self.subTest(command=command):
                self.assert_denied(command)

        for command in (
            "gh auth status",
            "gh.exe auth status",
            "gh api /repos/owner/repo/issues",
            "gh.exe auth token",
            "gh skill add owner/repo skill",
            "gh.exe skills add owner/repo skill",
            "gh at download owner/repo --name artifact",
            "gh.exe pr co 123 --force",
            "gh issue new --title test",
            "gh repo autolink new T- url",
            "gh discussion comment 123 --body text",
        ):
            with self.subTest(command=command):
                self.assert_hook_allows(command)

    def test_git_family_classification_and_opaque_wrappers(self) -> None:
        self.assert_hook_allows(self.posix_prefix + "git branch")
        self.assert_hook_allows(self.posix_prefix + "git diff --output=report.txt")
        self.assert_hook_allows(self.posix_prefix + "git log --ext-diff")
        self.assert_hook_allows(self.posix_prefix + "git show --textconv HEAD")
        for command in (
            self.posix_prefix + "git rebase -x 'echo test' feature/existing",
            self.posix_prefix + "git rebase --exec='echo test' feature/existing",
            self.posix_prefix + "git rebase -i feature/existing",
            'bash -c "git status"',
            'sh -c "git status"',
            'powershell.exe -Command "git status"',
            "pwsh -EncodedCommand Z2l0IHN0YXR1cw==",
            'cmd.exe /c "git status"',
            'cmd.exe /d /c "echo hook-negative-marker"',
            'cmd /s /d /c "echo hook-negative-marker"',
            'cmd.exe /e:on /c "echo hook-negative-marker"',
            'cmd /d /s /k "echo hook-negative-marker"',
            "Invoke-Expression 'git status'",
            "Remove-Item file.txt",
            "del file.txt",
            "unlink file.txt",
        ):
            with self.subTest(command=command):
                self.assert_denied(command)

    def test_remote_verbose_listing_and_mutation_classification(self) -> None:
        for command in (
            "git remote",
            "git remote -v",
            "git remote --verbose",
            self.posix_prefix + "git remote -v",
            self.posix_prefix + "git remote --verbose",
        ):
            with self.subTest(command=command):
                self.assert_hook_allows(command)

        subprocess.run(
            ["git", "switch", "main"],
            cwd=self.repo,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        for command in (
            self.posix_prefix + "git remote -v remove origin",
            self.posix_prefix + "git remote --verbose remove origin",
        ):
            with self.subTest(command=command):
                self.assert_denied(command, "protected branch")

        subprocess.run(
            ["git", "switch", "feature/existing"],
            cwd=self.repo,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        for command in (
            self.posix_prefix + "git remote -v remove origin",
            self.posix_prefix + "git remote --verbose remove origin",
        ):
            with self.subTest(command=command):
                self.assert_hook_allows(command)

    def test_quoted_shell_wrappers_are_denied_but_argument_text_is_allowed(
        self,
    ) -> None:
        wrappers = (
            '"bash" -c "git status"',
            "'sh' -c 'git status'",
            '& "cmd.exe" /d /c "echo hook-negative-marker"',
            '& "powershell.exe" -Command "git status"',
            '& "pwsh.exe" -EncodedCommand Z2l0IHN0YXR1cw==',
        )
        for command in wrappers:
            with self.subTest(command=command):
                self.assert_denied(command, "Nested shell wrappers")

        for command in (
            "printf '%s' 'bash -c'",
            'echo "an ordinary argument contains bash -c"',
            'echo "an ordinary argument contains powershell.exe -Command"',
        ):
            with self.subTest(command=command):
                self.assert_hook_allows(command)

    def test_malformed_shape_and_wrong_tool_name_fail_closed(self) -> None:
        for payload in (
            "[]",
            json.dumps({"tool_name": "Other", "tool_input": {"command": "git status"}}),
            json.dumps({"tool_name": "Bash", "tool_input": {}}),
        ):
            result = subprocess.run(
                [NODE, str(HOOK)],
                cwd=self.repo,
                input=payload,
                text=True,
                capture_output=True,
            )
            self.assertEqual(result.returncode, 2, payload)


if __name__ == "__main__":
    unittest.main()
