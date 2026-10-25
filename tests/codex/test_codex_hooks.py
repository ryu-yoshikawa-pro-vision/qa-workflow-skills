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
        self.empty_git_config = Path(self.temp.name) / "empty.gitconfig"
        self.empty_git_config.write_text("", encoding="utf-8")
        self.hook_env = os.environ.copy()
        self.hook_env["GIT_CONFIG_GLOBAL"] = str(self.empty_git_config)
        self.hook_env["GIT_CONFIG_NOSYSTEM"] = "1"
        self.repo = Path(self.temp.name) / "repository with spaces"
        self.repo.mkdir()
        self.remote = Path(self.temp.name) / "remote with spaces.git"
        subprocess.run(
            ["git", "init", "--bare", "-q", str(self.remote)],
            cwd=self.repo.parent,
            check=True,
        )
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
            ["git", "remote", "add", "origin", str(self.remote)],
            cwd=self.repo,
            check=True,
        )
        subprocess.run(
            [
                "git",
                "config",
                "--add",
                "remote.origin.fetch",
                "+refs/heads/*:refs/remotes/origin/*",
            ],
            cwd=self.repo,
            check=True,
        )
        subprocess.run(
            ["git", "config", "branch.feature/existing.remote", "origin"],
            cwd=self.repo,
            check=True,
        )
        subprocess.run(
            [
                "git",
                "config",
                "branch.feature/existing.merge",
                "refs/heads/feature/existing",
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
            env=self.hook_env,
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

    def add_remote(self, name: str, *, default_branch: str | None = None) -> None:
        subprocess.run(
            ["git", "remote", "add", name, str(self.remote)],
            cwd=self.repo,
            check=True,
        )
        subprocess.run(
            [
                "git",
                "config",
                "--add",
                f"remote.{name}.fetch",
                f"+refs/heads/*:refs/remotes/{name}/*",
            ],
            cwd=self.repo,
            check=True,
        )
        if default_branch is not None:
            subprocess.run(
                [
                    "git",
                    "symbolic-ref",
                    f"refs/remotes/{name}/HEAD",
                    f"refs/remotes/{name}/{default_branch}",
                ],
                cwd=self.repo,
                check=True,
            )

    def test_normal_commit_is_allowed_but_amend_and_unknown_forms_are_denied(
        self,
    ) -> None:
        for command in (
            self.posix_prefix + 'git commit -m "normal commit"',
            self.ps_prefix + 'git.exe commit --message "normal commit"',
            self.posix_prefix + 'git commit -a -m "normal commit"',
        ):
            with self.subTest(command=command):
                self.assert_hook_allows(command)

        for command in (
            self.posix_prefix + 'git commit --amend -m "rewrite"',
            self.posix_prefix + 'git commit -m "rewrite" --amend',
            self.posix_prefix + "git commit --message=rewrite --amend=HEAD",
            self.ps_prefix + 'git.exe commit --message "rewrite" --Amend',
            self.posix_prefix + 'git commit --ame -m "rewrite"',
            self.posix_prefix + 'git commit -m "$MESSAGE"',
            self.posix_prefix + "git commit --no-verify -m message",
            self.posix_prefix + "git commit path.txt",
            "git commit -m message",
        ):
            with self.subTest(command=command):
                self.assert_denied(command)

        subprocess.run(["git", "switch", "main"], cwd=self.repo, check=True)
        self.assert_denied(
            self.posix_prefix + 'git commit -m "protected"', "protected branch"
        )
        subprocess.run(
            [
                "git",
                "symbolic-ref",
                "refs/remotes/origin/HEAD",
                "refs/remotes/origin/develop",
            ],
            cwd=self.repo,
            check=True,
        )
        subprocess.run(["git", "branch", "develop"], cwd=self.repo, check=True)
        subprocess.run(["git", "switch", "develop"], cwd=self.repo, check=True)
        self.assert_denied(
            self.ps_prefix + 'git.exe commit -m "protected default"', "protected branch"
        )

    def test_normal_fetch_is_allowed_but_unsafe_ref_updates_are_denied(self) -> None:
        for command in (
            self.posix_prefix + "git fetch",
            self.posix_prefix + "git fetch origin",
            self.ps_prefix + "git.exe fetch origin",
            self.posix_prefix + "git fetch origin feature/existing",
            self.posix_prefix + "git fetch --dry-run origin",
            self.posix_prefix + "git fetch --prune origin",
        ):
            with self.subTest(command=command):
                self.assert_hook_allows(command)

        for command in (
            self.posix_prefix + "git fetch origin main:refs/heads/main",
            self.posix_prefix + "git fetch origin develop:refs/heads/develop",
            self.posix_prefix + "git fetch origin +main:refs/remotes/origin/main",
            self.posix_prefix + "git fetch origin --force",
            self.ps_prefix + "git.exe fetch -f origin",
            self.posix_prefix
            + "git fetch --refmap=refs/heads/main:refs/heads/main origin main",
            self.posix_prefix
            + "git fetch --refmap refs/heads/main:refs/heads/main origin main",
            self.posix_prefix + "git fetch origin --stdin",
            self.posix_prefix + "git fetch origin --prune-tags",
            self.ps_prefix + "git.exe fetch -P origin",
            self.posix_prefix + "git fetch --all",
            self.posix_prefix + "git fetch --multiple origin",
            self.posix_prefix + "git fetch origin --upload-pack=custom",
            self.posix_prefix + "git fetch https://example.invalid/repository.git",
        ):
            with self.subTest(command=command):
                self.assert_denied(command)

        subprocess.run(["git", "switch", "main"], cwd=self.repo, check=True)
        self.assert_hook_allows(self.posix_prefix + "git fetch origin")

    def test_fetch_pruning_and_effective_configuration_are_scoped_safely(self) -> None:
        subprocess.run(
            ["git", "config", "fetch.prune", "true"], cwd=self.repo, check=True
        )
        self.assert_hook_allows(self.posix_prefix + "git fetch origin")
        self.assert_hook_allows(self.posix_prefix + "git fetch --prune origin")

        subprocess.run(
            ["git", "config", "fetch.pruneTags", "true"], cwd=self.repo, check=True
        )
        self.assert_denied(self.posix_prefix + "git fetch --prune origin", "local tags")
        self.assert_hook_allows(self.posix_prefix + "git fetch --no-prune origin")

        subprocess.run(
            [
                "git",
                "config",
                "--replace-all",
                "remote.origin.fetch",
                "+refs/heads/*:refs/heads/*",
            ],
            cwd=self.repo,
            check=True,
        )
        self.assert_denied(
            self.posix_prefix + "git fetch origin",
            "remote-tracking namespace",
        )

        subprocess.run(
            [
                "git",
                "config",
                "--replace-all",
                "remote.origin.fetch",
                "+refs/heads/*:refs/remotes/origin/*",
            ],
            cwd=self.repo,
            check=True,
        )
        subprocess.run(
            ["git", "config", "remote.origin.mirror", "true"],
            cwd=self.repo,
            check=True,
        )
        self.assert_denied(self.posix_prefix + "git fetch origin", "Mirror fetch")

        subprocess.run(
            ["git", "config", "--unset-all", "remote.origin.mirror"],
            cwd=self.repo,
            check=True,
        )
        subprocess.run(
            ["git", "config", "fetch.recurseSubmodules", "on-demand"],
            cwd=self.repo,
            check=True,
        )
        self.assert_denied(
            self.posix_prefix + "git fetch origin", "Recursive submodule"
        )
        self.assert_hook_allows(
            self.posix_prefix + "git fetch --no-prune --no-recurse-submodules origin"
        )

    def test_safe_pull_requires_fast_forward_only_behavior_and_unprotected_branch(
        self,
    ) -> None:
        for command in (
            self.posix_prefix + "git pull --ff-only",
            self.posix_prefix + "git pull --ff-only origin",
            self.ps_prefix + "git.exe pull --ff-only origin feature/existing",
        ):
            with self.subTest(command=command):
                self.assert_hook_allows(command)

        self.assert_denied(self.posix_prefix + "git pull", "fast-forward-only")
        self.assert_denied(self.posix_prefix + "git pull origin", "fast-forward-only")

        subprocess.run(["git", "config", "pull.ff", "only"], cwd=self.repo, check=True)
        self.assert_hook_allows(self.posix_prefix + "git pull")
        subprocess.run(
            ["git", "config", "merge.ff", "false"], cwd=self.repo, check=True
        )
        self.assert_hook_allows(self.posix_prefix + "git pull")
        subprocess.run(
            ["git", "config", "--unset-all", "merge.ff"], cwd=self.repo, check=True
        )
        subprocess.run(
            ["git", "config", "pull.rebase", "false"], cwd=self.repo, check=True
        )
        self.assert_hook_allows(self.posix_prefix + "git pull --ff-only")
        self.assert_hook_allows(self.posix_prefix + "git pull")
        subprocess.run(["git", "config", "pull.ff", "false"], cwd=self.repo, check=True)
        subprocess.run(["git", "config", "merge.ff", "only"], cwd=self.repo, check=True)
        self.assert_denied(self.posix_prefix + "git pull", "fast-forward-only")
        subprocess.run(
            ["git", "config", "--unset-all", "pull.ff"], cwd=self.repo, check=True
        )
        subprocess.run(
            ["git", "config", "--unset-all", "merge.ff"], cwd=self.repo, check=True
        )
        self.assert_denied(self.posix_prefix + "git pull", "fast-forward-only")
        subprocess.run(["git", "config", "merge.ff", "only"], cwd=self.repo, check=True)
        self.assert_hook_allows(self.posix_prefix + "git pull")
        subprocess.run(
            ["git", "config", "--unset-all", "merge.ff"], cwd=self.repo, check=True
        )

        subprocess.run(["git", "switch", "main"], cwd=self.repo, check=True)
        self.assert_denied(self.posix_prefix + "git pull --ff-only", "protected branch")

    def test_pull_rejects_rebase_no_ff_unsafe_config_and_protected_refspecs(
        self,
    ) -> None:
        for command in (
            self.posix_prefix + "git pull --rebase",
            self.posix_prefix + "git pull --rebase=merges",
            self.ps_prefix + "git.exe pull -r",
            self.posix_prefix + "git pull --no-rebase",
            self.posix_prefix + "git pull --no-ff",
            self.posix_prefix + "git pull --squash",
            self.posix_prefix + "git pull --autostash",
            self.posix_prefix + "git pull origin main:refs/heads/main",
            self.posix_prefix + "git pull origin main other",
        ):
            with self.subTest(command=command):
                self.assert_denied(command)

        unsafe_settings = (
            ("pull.rebase", "true"),
            ("pull.rebase", "false"),
            ("branch.feature/existing.rebase", "true"),
            ("branch.feature/existing.rebase", "false"),
            ("pull.ff", "false"),
            ("merge.ff", "false"),
            ("branch.feature/existing.mergeOptions", "--no-ff"),
            ("pull.squash", "true"),
        )
        for key, value in unsafe_settings:
            with self.subTest(key=key, value=value):
                subprocess.run(
                    ["git", "config", "--replace-all", key, value],
                    cwd=self.repo,
                    check=True,
                )
                has_merge_strategy_without_ff_only = value == "false" and (
                    key in {"pull.ff", "merge.ff", "pull.rebase"}
                    or key.endswith(".rebase")
                )
                pull_command = (
                    "git pull"
                    if has_merge_strategy_without_ff_only
                    else "git pull --ff-only"
                )
                self.assert_denied(self.posix_prefix + pull_command)
                subprocess.run(
                    ["git", "config", "--unset-all", key],
                    cwd=self.repo,
                    check=False,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )

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
            self.posix_prefix + "git push origin HEAD:feature/existing",
            self.posix_prefix + "git push -u origin feature/existing",
            self.posix_prefix + "git commit -m test",
            self.ps_prefix + "git.exe push origin feature/existing",
            self.ps_prefix + "git.exe push --set-upstream origin feature/existing",
            "gh pr merge 123 -R owner/repo",
            "gh.exe pr merge 123 -R owner/repo",
            "gh pr view 123 -R owner/repo",
            "git status",
        ):
            with self.subTest(command=command):
                self.assert_hook_allows(command)

    def test_git_show_ref_queries_are_read_only(self) -> None:
        for command in (
            "git show-ref",
            self.posix_prefix + "git show-ref",
            self.posix_prefix
            + "git show-ref --verify --quiet refs/heads/feature/existing",
            self.posix_prefix
            + "git show-ref --verify --quiet -- refs/heads/feature/existing",
            self.posix_prefix + "git show-ref --head",
            self.posix_prefix + "git show-ref --branches --tags",
            self.ps_prefix + "git.exe show-ref --head --tags",
        ):
            with self.subTest(command=command):
                self.assert_hook_allows(command)

    def test_forbidden_git_mutations_keep_existing_hook_and_execpolicy_guards(
        self,
    ) -> None:
        for command in (
            "git update-ref -d refs/heads/feature/existing",
            "git clean -fd",
            "git rm tracked.txt",
            "git push --force origin feature/existing",
        ):
            with self.subTest(command=command):
                self.assert_denied(command)

        # These canonical forms reach execpolicy, which keeps their existing
        # forbidden decisions in test_execpolicy_cli.py.
        for command in (
            self.posix_prefix + "git update-ref -d refs/heads/feature/existing",
            self.posix_prefix + "git clean -fd",
            self.posix_prefix + "git rm tracked.txt",
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
        for target in (
            "main",
            "HEAD:main",
            "feature/existing:refs/heads/main",
            "master",
            "HEAD:master",
        ):
            for prefix in (
                self.posix_prefix + "git push origin ",
                self.ps_prefix + "git.exe push origin ",
            ):
                command = prefix + target
                with self.subTest(command=command):
                    self.assert_denied(command, "protected branch")
        for target in (
            ":main",
            "--delete main",
            "+HEAD:main",
            "feature/existing HEAD:refs/heads/main",
        ):
            for prefix in (
                self.posix_prefix + "git push origin ",
                self.ps_prefix + "git.exe push origin ",
            ):
                command = prefix + target
                with self.subTest(command=command):
                    self.assert_denied(command)
        self.assert_hook_allows(self.posix_prefix + "git push origin feature/existing")
        self.assert_hook_allows(
            self.posix_prefix + "git push origin HEAD:feature/existing"
        )
        self.assert_hook_allows(
            self.posix_prefix + "git push -u origin feature/existing"
        )

    def test_push_uses_the_named_remote_default_branch(self) -> None:
        self.add_remote("secondary", default_branch="develop")
        self.assert_hook_allows(
            self.posix_prefix + "git push secondary feature/existing"
        )

        subprocess.run(["git", "branch", "develop"], cwd=self.repo, check=True)
        subprocess.run(["git", "switch", "develop"], cwd=self.repo, check=True)
        self.assert_denied(
            self.posix_prefix + "git push secondary develop", "protected branch"
        )

    def test_origin_default_branch_remains_protected_for_local_mutations(self) -> None:
        subprocess.run(
            [
                "git",
                "symbolic-ref",
                "refs/remotes/origin/HEAD",
                "refs/remotes/origin/develop",
            ],
            cwd=self.repo,
            check=True,
        )
        subprocess.run(["git", "branch", "develop"], cwd=self.repo, check=True)
        subprocess.run(["git", "switch", "develop"], cwd=self.repo, check=True)
        self.assert_denied(self.posix_prefix + "git commit -m test", "protected branch")

    def test_git_context_does_not_ignore_origin_default_read_failure(self) -> None:
        ref_dir = self.repo / ".git" / "refs" / "remotes" / "origin"
        ref_dir.mkdir(parents=True, exist_ok=True)
        (ref_dir / "HEAD").write_text(
            "ref: refs/remotes/origin/OTHER\n", encoding="utf-8"
        )
        (ref_dir / "OTHER").write_text(
            "ref: refs/remotes/origin/HEAD\n", encoding="utf-8"
        )
        self.assert_denied(self.posix_prefix + "git commit -m test", "Could not read")

    def test_push_requires_valid_local_default_branch_metadata(self) -> None:
        cases = (
            ("secondary", None, "configured locally"),
            ("malformed", "refs/remotes/origin/main", "does not match"),
        )
        for remote, target, reason in cases:
            with self.subTest(remote=remote, target=target):
                self.add_remote(remote)
                if target is not None:
                    subprocess.run(
                        [
                            "git",
                            "symbolic-ref",
                            f"refs/remotes/{remote}/HEAD",
                            target,
                        ],
                        cwd=self.repo,
                        check=True,
                    )
                self.assert_denied(
                    self.posix_prefix + f"git push {remote} feature/existing", reason
                )

    def test_push_rejects_remote_default_branch_read_failure(self) -> None:
        self.add_remote("unreadable")
        ref_dir = self.repo / ".git" / "refs" / "remotes" / "unreadable"
        ref_dir.mkdir(parents=True, exist_ok=True)
        (ref_dir / "HEAD").write_text(
            "ref: refs/remotes/unreadable/OTHER\n", encoding="utf-8"
        )
        (ref_dir / "OTHER").write_text(
            "ref: refs/remotes/unreadable/HEAD\n", encoding="utf-8"
        )
        self.assert_denied(
            self.posix_prefix + "git push unreadable feature/existing",
            "Could not read",
        )

    def test_push_rejects_a_non_symbolic_remote_default_ref(self) -> None:
        self.add_remote("malformed")
        ref_dir = self.repo / ".git" / "refs" / "remotes" / "malformed"
        ref_dir.mkdir(parents=True, exist_ok=True)
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=self.repo, text=True
        ).strip()
        (ref_dir / "HEAD").write_text(commit + "\n", encoding="utf-8")
        self.assert_denied(
            self.posix_prefix + "git push malformed feature/existing",
            "metadata is invalid",
        )

    def test_push_requires_one_explicit_named_remote_and_branch_refspec(self) -> None:
        for command in (
            self.posix_prefix + "git push origin",
            self.posix_prefix + "git push origin HEAD",
            self.posix_prefix + "git push origin feature/target",
            self.posix_prefix + "git push origin HEAD:feature/target",
            self.posix_prefix + "git push origin feature/existing feature/target",
            self.posix_prefix
            + "git push origin HEAD:feature/existing HEAD:feature/target",
            self.posix_prefix
            + "git push https://example.invalid/owner/repo.git feature/existing",
            self.posix_prefix + f"git push '{self.remote.as_posix()}' feature/existing",
            self.posix_prefix + "git push origin feature/*",
            self.posix_prefix + "git push origin 'feature/*'",
            self.posix_prefix + "git push origin HEAD:feature/*",
            self.posix_prefix + "git push origin 'HEAD:feature/*'",
            self.posix_prefix + "git push origin :feature/target",
            self.posix_prefix + "git push origin :",
            self.posix_prefix + "git push origin +HEAD:feature/target",
            self.posix_prefix + "git push origin feature/existing --force",
            self.posix_prefix + "git push origin feature/existing -u",
            self.posix_prefix + "git push origin --delete feature/target",
            self.ps_prefix + "git.exe push origin feature/existing --mirror",
        ):
            with self.subTest(command=command):
                self.assert_denied(command)

    def test_push_rejects_an_unconfigured_remote(self) -> None:
        subprocess.run(["git", "remote", "remove", "origin"], cwd=self.repo, check=True)
        self.assert_denied(
            self.posix_prefix + "git push origin feature/existing",
            "configured named remote",
        )

    def test_force_bulk_and_other_unsupported_push_options_are_denied(self) -> None:
        unsafe_options = (
            "-f",
            "--force",
            "--force-with-lease",
            "--force-if-includes",
            "-fu",
            "--delete",
            "-d",
            "--prune",
            "--mirror",
            "--all",
            "--branches",
            "--tags",
            "--follow-tags",
        )
        for option in unsafe_options:
            for prefix in (
                self.posix_prefix + "git push ",
                self.ps_prefix + "git.exe push ",
            ):
                command = prefix + option + " origin feature/existing"
                with self.subTest(command=command):
                    self.assert_denied(command)

    def test_push_rejects_configuration_that_can_add_remote_updates(self) -> None:
        cases = (
            ("push.followTags", "true"),
            ("push.recurseSubmodules", "on-demand"),
            ("remote.origin.mirror", "true"),
            ("remote.origin.push", "HEAD:feature/target"),
            ("push.followTags", "not-a-boolean"),
        )
        for key, value in cases:
            with self.subTest(key=key, value=value):
                subprocess.run(
                    ["git", "config", "--replace-all", key, value],
                    cwd=self.repo,
                    check=True,
                )
                self.assert_denied(
                    self.posix_prefix + "git push origin feature/existing"
                )
                subprocess.run(
                    ["git", "config", "--unset-all", key],
                    cwd=self.repo,
                    check=False,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )

        subprocess.run(
            ["git", "config", "push.recurseSubmodules", "false"],
            cwd=self.repo,
            check=True,
        )
        self.assert_hook_allows(self.posix_prefix + "git push origin feature/existing")

    def test_multiple_configured_push_urls_are_denied(self) -> None:
        second_remote = Path(self.temp.name) / "second remote.git"
        subprocess.run(
            ["git", "init", "--bare", "-q", str(second_remote)],
            cwd=self.repo.parent,
            check=True,
        )
        for remote_url in (self.remote, second_remote):
            subprocess.run(
                [
                    "git",
                    "remote",
                    "set-url",
                    "--add",
                    "--push",
                    "origin",
                    str(remote_url),
                ],
                cwd=self.repo,
                check=True,
            )
        self.assert_denied(self.posix_prefix + "git push origin feature/existing")

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
