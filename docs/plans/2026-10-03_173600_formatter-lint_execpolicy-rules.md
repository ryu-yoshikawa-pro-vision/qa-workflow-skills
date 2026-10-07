# Formatter / Python lint / Codex開発ハーネス導入Plan — execpolicy rule一覧

## 位置づけ

このファイルは `docs/plans/2026-10-03_173600_formatter-lint.md` の一部であり、PR #18で追加する `.codex/rules/20-risky-prompt.rules` / `.codex/rules/30-destructive-forbidden.rules` の正本です。

Main Planではexecpolicyの目的、Hookとの責務分離、実装順序、検証、完了条件を管理します。このファイルでは実装時に判断を残さないため、Codex 0.160.0の`prefix_rule`へ落とすpattern / decision / `match` / `not_match`だけを具体化します。

このファイルにないGit / GitHub CLIの将来subcommandを推測で追加しません。公式仕様または実際の必要性を確認し、Main Planとこのファイルを同じ変更で更新します。

### execpolicy rules

`.codex/rules/`はHookの代替ではなく、Hook failure時にも高影響操作を無承認で通しにくくする承認境界として使います。通常のread-only command用`allow` ruleは追加しません。

Codex 0.160.0のexecpolicyはargvのexact prefix matchingであり、pattern要素のunionと`match` / `not_match`を使えます。実装者判断を残さないため、今回追加するruleの**pattern / decision / representative match / boundary not_matchをこの節の正本**とします。`match` / `not_match`はrules file自身のload-time testとして同じ内容を保持します。

#### `20-risky-prompt.rules`

次をそのまま実装します。

```starlark
prefix_rule(
    pattern = ["git", ["commit", "merge", "rebase", "pull", "push", "fetch", "reset", "am", "cherry-pick", "revert"]],
    decision = "prompt",
    justification = "High-impact Git operations require explicit user approval.",
    match = [
        "git commit -m test",
        "git push origin feature",
        "git reset HEAD~1",
    ],
    not_match = [
        "git status",
        "git diff --stat",
    ],
)

prefix_rule(
    pattern = ["git", ["branch", "tag", "config", "remote", "worktree", "stash"]],
    decision = "prompt",
    justification = "These Git families mix read-only and state-changing forms; prompt the family instead of adding an option parser.",
    match = [
        "git branch",
        "git tag v1",
        "git config user.name test",
        "git remote set-url origin https://example.invalid/repo.git",
        "git worktree add ../tmp feature",
        "git stash push",
    ],
    not_match = [
        "git status",
        "git rev-parse --show-toplevel",
    ],
)

prefix_rule(
    pattern = ["gh", "pr", ["create", "checkout", "close", "comment", "edit", "lock", "merge", "ready", "reopen", "revert", "review", "unlock", "update-branch"]],
    decision = "prompt",
    justification = "Pull request mutations and local checkout require explicit user approval.",
    match = [
        "gh pr create --fill",
        "gh pr merge 123",
        "gh pr checkout 123",
    ],
    not_match = [
        "gh pr list",
        "gh pr status",
        "gh pr checks 123",
        "gh pr diff 123",
        "gh pr view 123",
    ],
)

prefix_rule(
    pattern = ["gh", "issue", ["create", "close", "comment", "delete", "develop", "edit", "lock", "pin", "reopen", "transfer", "unlock", "unpin"]],
    decision = "prompt",
    justification = "Issue mutations and development-branch creation require explicit user approval.",
    match = [
        "gh issue create --title test --body test",
        "gh issue close 123",
        "gh issue develop 123",
    ],
    not_match = [
        "gh issue list",
        "gh issue status",
        "gh issue view 123",
    ],
)

prefix_rule(
    pattern = ["gh", "repo", ["archive", "clone", "create", "delete", "edit", "fork", "read-file", "rename", "set-default", "unarchive"]],
    decision = "prompt",
    justification = "Repository mutations and repository-local file writes require explicit user approval.",
    match = [
        "gh repo create example",
        "gh repo clone owner/repo",
        "gh repo read-file README.md --output README.copy.md",
        "gh repo rename new-name",
    ],
    not_match = [
        "gh repo list",
        "gh repo view owner/repo",
        "gh repo read-dir .",
    ],
)

prefix_rule(
    pattern = ["gh", "repo", "autolink", ["create", "delete"]],
    decision = "prompt",
    justification = "Repository autolink mutations require explicit user approval.",
    match = [
        "gh repo autolink create TICKET- https://example.invalid/TICKET-<num>",
        "gh repo autolink delete 123",
    ],
    not_match = [
        "gh repo autolink list",
    ],
)

prefix_rule(
    pattern = ["gh", "repo", "deploy-key", ["add", "delete"]],
    decision = "prompt",
    justification = "Deploy-key mutations require explicit user approval.",
    match = [
        "gh repo deploy-key add key.pub --title test",
        "gh repo deploy-key delete 123",
    ],
    not_match = [
        "gh repo deploy-key list",
    ],
)

prefix_rule(
    pattern = ["gh", "workflow", ["disable", "enable", "run"]],
    decision = "prompt",
    justification = "Workflow state changes and manual runs require explicit user approval.",
    match = [
        "gh workflow disable ci.yml",
        "gh workflow run ci.yml",
    ],
    not_match = [
        "gh workflow list",
        "gh workflow view ci.yml",
    ],
)

prefix_rule(
    pattern = ["gh", "run", ["cancel", "delete", "download", "rerun"]],
    decision = "prompt",
    justification = "Workflow-run mutations and artifact downloads require explicit user approval.",
    match = [
        "gh run cancel 123",
        "gh run download 123",
    ],
    not_match = [
        "gh run list",
        "gh run view 123",
        "gh run watch 123",
    ],
)

prefix_rule(
    pattern = ["gh", "release", ["create", "delete", "delete-asset", "download", "edit", "upload"]],
    decision = "prompt",
    justification = "Release mutations and downloads require explicit user approval.",
    match = [
        "gh release create v1",
        "gh release upload v1 artifact.zip",
        "gh release download v1",
    ],
    not_match = [
        "gh release list",
        "gh release view v1",
        "gh release verify v1",
    ],
)

prefix_rule(
    pattern = ["gh", "secret", ["delete", "set"]],
    decision = "prompt",
    justification = "Secret mutations require explicit user approval.",
    match = [
        "gh secret set TOKEN --body value",
        "gh secret delete TOKEN",
    ],
    not_match = [
        "gh secret list",
    ],
)

prefix_rule(
    pattern = ["gh", "variable", ["delete", "set"]],
    decision = "prompt",
    justification = "Variable mutations require explicit user approval.",
    match = [
        "gh variable set NAME --body value",
        "gh variable delete NAME",
    ],
    not_match = [
        "gh variable get NAME",
        "gh variable list",
    ],
)

prefix_rule(
    pattern = ["gh", "cache", "delete"],
    decision = "prompt",
    justification = "Cache deletion requires explicit user approval.",
    match = [
        "gh cache delete --all",
    ],
    not_match = [
        "gh cache list",
    ],
)

prefix_rule(
    pattern = ["gh", "label", ["clone", "create", "delete", "edit"]],
    decision = "prompt",
    justification = "Label mutations require explicit user approval.",
    match = [
        "gh label create bug",
        "gh label edit bug --name defect",
    ],
    not_match = [
        "gh label list",
    ],
)

prefix_rule(
    pattern = ["gh", ["auth", "codespace", "gist", "org", "project", "ssh-key", "gpg-key", "extension", "alias", "config", "attestation"]],
    decision = "prompt",
    justification = "These less-common GitHub CLI families can mutate remote, authentication, extension, or local state; prompt the whole family instead of maintaining a subcommand parser.",
    match = [
        "gh auth status",
        "gh gist list",
        "gh project list",
        "gh attestation verify artifact.bin --owner example",
    ],
    not_match = [
        "gh status",
        "gh search prs test",
        "gh ruleset list",
        "gh browse --no-browser",
    ],
)

prefix_rule(
    pattern = [["curl", "wget", "Invoke-WebRequest", "iwr", "Invoke-RestMethod", "irm", "rsync", "robocopy", "mv", "move", "Move-Item", "mi", "Rename-Item", "ren", "rni"]],
    decision = "prompt",
    justification = "Network transfer, synchronization, move, and rename commands require explicit user approval in this harness.",
    match = [
        "curl https://example.com",
        "rsync -a src/ dst/",
        "Move-Item a.txt b.txt",
        "mv a.txt b.txt",
    ],
    not_match = [
        "git status",
        "python -m unittest",
    ],
)
```

GitHub CLIのmutation-only列挙は、実装時点で確認済みのGitHub CLI help referenceに存在する上記subcommandを今回の正本とします。将来GitHub CLIへ新しいsubcommandが追加されても自動的にこの集合へ含めません。別変更で公式helpを確認し、ruleと`match` / `not_match`を更新します。

`gh pr` / `issue` / `repo` / `workflow` / `run` / `release` / `secret` / `variable` / `cache` / `label`は通常開発でread操作を使うためmutation subcommandだけをpromptにします。それ以外の上記less-common familyは、read / mutationを細かく分離する必要性が今回ないためfamily全体をpromptにします。この差を独自parserで埋めません。

Gitでは`branch` / `tag` / `config` / `remote` / `worktree` / `stash`のread-only formまでprompt対象になることを明示的に許容します。execpolicyのprefix制約下でoption parserを追加して無承認read-onlyへ戻すより、ユーザー承認を優先します。

#### `30-destructive-forbidden.rules`

次をそのまま実装します。

```starlark
prefix_rule(
    pattern = ["gh", "api"],
    decision = "forbidden",
    justification = "Direct GitHub API access is outside this repository harness. Use a supported gh subcommand instead.",
    match = [
        "gh api /repos/owner/repo/issues",
    ],
    not_match = [
        "gh pr view 123",
    ],
)

prefix_rule(
    pattern = ["gh", "repo", "sync"],
    decision = "forbidden",
    justification = "Repository sync can update branches outside the supported development flow. Use explicit Git operations with approval instead.",
    match = [
        "gh repo sync owner/repo",
    ],
    not_match = [
        "gh repo view owner/repo",
    ],
)

prefix_rule(
    pattern = ["gh", "auth", "token"],
    decision = "forbidden",
    justification = "Do not print authentication tokens. Use gh auth status without token output.",
    match = [
        "gh auth token",
    ],
    not_match = [
        "gh auth status",
    ],
)

prefix_rule(
    pattern = ["git", ["clean", "rm", "update-ref"]],
    decision = "forbidden",
    justification = "These Git deletion or ref-update families are outside the supported autonomous workflow.",
    match = [
        "git clean -fd",
        "git rm file.txt",
        "git update-ref -d refs/heads/old",
    ],
    not_match = [
        "git status",
        "git restore file.txt",
    ],
)

prefix_rule(
    pattern = [["rm", "del", "erase", "rd", "ri", "Remove-Item", "rmdir", "unlink"]],
    decision = "forbidden",
    justification = "Direct deletion commands are not allowed in the repository harness. Use a scoped edit or explicit user-directed operation instead.",
    match = [
        "rm file.txt",
        "del file.txt",
        "Remove-Item file.txt",
        "rmdir tmp",
    ],
    not_match = [
        "mv a.txt b.txt",
        "git status",
    ],
)
```

`gh auth status --show-token`はoption位置を任意に解析する独自parserを追加しません。`gh auth` family全体が`prompt`であり、直接tokenを出力する`gh auth token`は`forbidden`です。これを「すべてのtoken出力variantを永久禁止した」とは扱いません。

force push、hard reset、commit amend等は永久禁止にしません。`git push` / `git reset` / `git commit`のfamily-level `prompt`でユーザー承認へ送り、protected branch上ではPreToolUseのcontextual denyを優先します。

CIでは固定版Codex CLI自身の`codex execpolicy check --rules ...`で、rules fileへ埋め込んだ`match` / `not_match`のload-time検証に加え、各ruleから少なくとも1つの`prompt` / `forbidden`代表caseと、read-only boundaryの代表caseを実行します。

このrule集合は今回のrepository開発workflowで使うGit / GitHub CLI / local shell commandを対象にしたguardrailです。Git / GitHub CLIの全subcommand・全option・将来versionの新commandをrepository独自policy engineで再実装しません。

## 更新時の確認

- Main Planの「承認境界」「実装順序」「検証」「完了条件」と矛盾しないこと
- Codex 0.160.0の`codex execpolicy check`で全ruleがloadでき、各`match` / `not_match`がPASSすること
- GitHub CLIのmutation-only集合を変更する場合は、実装時点の公式help referenceでsubcommandを再確認すること
- read-only commandを無承認に戻すためだけの独自option parserを追加しないこと
- rule追加を理由にGit / GitHub CLI全体のsecurity frameworkへ拡張しないこと

## 公式資料

- Codex execpolicy: https://github.com/openai/codex/blob/rust-v0.160.0/codex-rs/execpolicy/README.md
- GitHub CLI command reference: https://cli.github.com/manual/gh_help_reference
- GitHub CLI `gh pr`: https://cli.github.com/manual/gh_pr
- GitHub CLI `gh issue`: https://cli.github.com/manual/gh_issue
- GitHub CLI `gh repo`: https://cli.github.com/manual/gh_repo
- GitHub CLI `gh workflow`: https://cli.github.com/manual/gh_workflow
- GitHub CLI `gh run`: https://cli.github.com/manual/gh_run
- GitHub CLI `gh release`: https://cli.github.com/manual/gh_release
- GitHub CLI `gh secret`: https://cli.github.com/manual/gh_secret
- GitHub CLI `gh variable`: https://cli.github.com/manual/gh_variable
- GitHub CLI `gh cache`: https://cli.github.com/manual/gh_cache
- GitHub CLI `gh label`: https://cli.github.com/manual/gh_label
