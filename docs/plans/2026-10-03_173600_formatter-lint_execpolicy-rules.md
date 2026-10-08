# Formatter / Python lint / Codex開発ハーネス導入Plan — execpolicy rule一覧

## 位置づけ

このファイルは `docs/plans/2026-10-03_173600_formatter-lint.md` の一部であり、PR #18で追加する `.codex/rules/20-risky-prompt.rules` / `.codex/rules/30-destructive-forbidden.rules` の正本です。

Main Planではexecpolicyの目的、Hookとの責務分離、実装順序、検証、完了条件を管理します。このファイルでは実装時に判断を残さないため、Codex 0.160.0の`prefix_rule`へ落とすpattern / decision / `match` / `not_match`だけを具体化します。

Windows実行名はすべてのGit / ghルールで`git` / `git.exe`、`gh` / `gh.exe`をunionで扱います。`gh skill` / `skills`、`gh agent-task` / `agent-tasks` / `agent` / `agents`、`gh release create` / `new`も既知aliasとして含めます。

このファイルにないGit / GitHub CLIの将来subcommandを推測で追加しません。公式仕様または実際の必要性を確認し、Main Planとこのファイルを同じ変更で更新します。

### execpolicy rules

`.codex/rules/`はHookの代替ではなく、Hook failure時にも高影響操作を無承認で通しにくくする承認境界として使います。通常のread-only command用`allow` ruleは追加しません。

Codex 0.160.0のexecpolicyはargvのexact prefix matchingであり、pattern要素のunionと`match` / `not_match`を使えます。サブコマンドより前にオプションが入るGit / GitHub CLI形式はprefixに一致しないため、Main Plan「CLIの対応形式とprefix判定」に従ってPreToolUseでdenyします。rule未一致だけを拒否済みの証拠として扱いません。実装者判断を残さないため、今回追加するruleの**pattern / decision / representative match / boundary not_matchをこの節の正本**とします。`match` / `not_match`はrules file自身のload-time testとして同じ内容を保持します。

#### `20-risky-prompt.rules`

次をそのまま実装します。

```starlark
prefix_rule(
    pattern = [["git", "git.exe"], ["commit", "merge", "rebase", "pull", "push", "fetch", "reset", "am", "cherry-pick", "revert", "restore", "checkout", "switch"]],
    decision = "prompt",
    justification = "High-impact Git operations, including commands that can discard uncommitted changes, require explicit user approval.",
    match = [
        "git commit -m test",
        "git.exe commit -m test",
        "git push origin feature",
        "git.exe push origin feature",
        "git reset HEAD~1",
        "git restore .",
        "git.exe restore .",
        "git checkout -- .",
        "git.exe checkout -- .",
        "git switch --discard-changes feature/other",
        "git.exe switch --discard-changes feature/other",
        "git switch -c feature/new-work",
        "git.exe switch feature/existing-work",
    ],
    not_match = [
        "git status",
        "git diff --stat",
        "git add sample.txt",
        "git -c user.name=test push origin feature",
        "git --no-pager reset --hard",
    ],
)

prefix_rule(
    pattern = [["git", "git.exe"], ["branch", "tag", "config", "remote", "worktree", "stash"]],
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
    pattern = [["gh", "gh.exe"], "pr", ["create", "checkout", "close", "comment", "edit", "lock", "merge", "ready", "reopen", "revert", "review", "unlock", "update-branch"]],
    decision = "prompt",
    justification = "Pull request mutations and local checkout require explicit user approval.",
    match = [
        "gh pr create --fill",
        "gh.exe pr create --fill",
        "gh pr merge 123",
        "gh pr merge 123 -R owner/repo",
        "gh pr checkout 123",
    ],
    not_match = [
        "gh pr list",
        "gh pr status",
        "gh pr checks 123",
        "gh pr diff 123",
        "gh pr view 123",
        "gh pr -R owner/repo merge 123",
        "gh -R owner/repo pr merge 123",
    ],
)

prefix_rule(
    pattern = [["gh", "gh.exe"], "issue", ["create", "close", "comment", "delete", "develop", "edit", "lock", "pin", "reopen", "transfer", "unlock", "unpin"]],
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
    pattern = [["gh", "gh.exe"], "repo", ["archive", "clone", "create", "delete", "edit", "fork", "read-file", "rename", "set-default", "unarchive"]],
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
    pattern = [["gh", "gh.exe"], "repo", "autolink", ["create", "delete"]],
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
    pattern = [["gh", "gh.exe"], "repo", "deploy-key", ["add", "delete"]],
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
    pattern = [["gh", "gh.exe"], ["skill", "skills"], ["publish", "install", "update"]],
    decision = "prompt",
    justification = "Publishing creates a release; installing and updating write local files.",
    match = ["gh skill publish --tag v1", "gh skills publish --tag v1", "gh.exe skill publish --tag v1", "gh skill install owner/repo skill", "gh skill update --all"],
    not_match = ["gh skill list", "gh skills preview owner/repo skill", "gh skill search test"],
)

prefix_rule(
    pattern = [["gh", "gh.exe"], ["agent-task", "agent-tasks", "agent", "agents"], "create"],
    decision = "prompt",
    justification = "Creating remote agent tasks requires approval, including aliases.",
    match = ["gh agent-task create task", "gh agent-tasks create task", "gh agent create task", "gh agents create task", "gh.exe agent-task create task"],
    not_match = ["gh agent-task list", "gh agents view 123"],
)

prefix_rule(
    pattern = [["gh", "gh.exe"], "discussion", ["create", "comment", "edit"]],
    decision = "prompt",
    justification = "Creating and changing discussions or comments requires approval.",
    match = ["gh discussion create --title Test --body Text --category General", "gh discussion comment 123 --body Text", "gh discussion comment 123 --delete", "gh discussion edit 123 --title New", "gh.exe discussion create --title Test --body Text --category General"],
    not_match = ["gh discussion list", "gh discussion view 123"],
)

prefix_rule(
    pattern = [["gh", "gh.exe"], "workflow", ["disable", "enable", "run"]],
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
    pattern = [["gh", "gh.exe"], "run", ["cancel", "delete", "download", "rerun"]],
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
    pattern = [["gh", "gh.exe"], "release", ["create", "new", "delete", "delete-asset", "download", "edit", "upload"]],
    decision = "prompt",
    justification = "Release mutations and downloads require explicit user approval.",
    match = [
        "gh release create v1",
        "gh release new v1",
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
    pattern = [["gh", "gh.exe"], "secret", ["delete", "set"]],
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
    pattern = [["gh", "gh.exe"], "variable", ["delete", "set"]],
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
    pattern = [["gh", "gh.exe"], "cache", "delete"],
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
    pattern = [["gh", "gh.exe"], "label", ["clone", "create", "delete", "edit"]],
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
    pattern = [["gh", "gh.exe"], ["auth", "codespace", "gist", "org", "project", "ssh-key", "gpg-key", "extension", "alias", "config", "attestation"]],
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

Gitでは`branch` / `tag` / `config` / `remote` / `worktree` / `stash`のread-only formまでprompt対象になることを明示的に許容します。`restore` / `checkout` / `switch`も破棄optionの有無によらずfamily-level `prompt`とし、protected branchからの限定的な安全な`switch`もPreToolUseの許可後にユーザー承認を要求します。execpolicyのprefix制約下でoption parserを追加して無承認操作を区別するより、ユーザー承認を優先します。

#### `30-destructive-forbidden.rules`

次をそのまま実装します。

```starlark
prefix_rule(
    pattern = [["gh", "gh.exe"], "api"],
    decision = "forbidden",
    justification = "Direct GitHub API access is outside this repository harness. Use a supported gh subcommand instead.",
    match = [
        "gh api /repos/owner/repo/issues",
        "gh.exe api /repos/owner/repo/issues",
    ],
    not_match = [
        "gh pr view 123",
    ],
)

prefix_rule(
    pattern = [["gh", "gh.exe"], "repo", "sync"],
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
    pattern = [["gh", "gh.exe"], "auth", "token"],
    decision = "forbidden",
    justification = "Do not print authentication tokens. Use gh auth status without token output.",
    match = [
        "gh auth token",
        "gh.exe auth token",
    ],
    not_match = [
        "gh auth status",
    ],
)

prefix_rule(
    pattern = [["git", "git.exe"], ["clean", "rm", "update-ref"]],
    decision = "forbidden",
    justification = "These Git deletion or ref-update families are outside the supported autonomous workflow.",
    match = [
        "git clean -fd",
        "git.exe clean -fd",
        "git rm file.txt",
        "git update-ref -d refs/heads/old",
        "git.exe update-ref -d refs/heads/old",
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

`gh auth token` / `gh.exe auth token`は`forbidden`です。`gh auth status --show-token` / `-t`と`gh.exe`経路（`--json hosts`との組合せを含む）はrepository-owned PreToolUse Hookで実行前denyとします。`gh auth status`単体は既存の`gh auth` family-level `prompt`を維持します。Hookでは`auth status`の既知フラグ`--show-token` / `-t`と`--show-token=...`だけを扱い、CLI全体やnested shellを再帰解析しません。あらゆる認証情報露出経路の遮断を保証するものではありません。

force push、hard reset、commit amendは永久禁止にしません。`git push` / `git reset` / `git commit`のfamily-level `prompt`でユーザー承認へ送り、protected branch上ではPreToolUseのcontextual denyを優先します。`restore` / `checkout` / `switch`は未commit変更の破棄を防ぐため同じ既存ruleの`prompt`に含め、protected branchからの安全な`switch`はHook通過とexecpolicy承認の両方を必要とします。

CIでは固定版Codex CLI自身の`codex execpolicy check --rules ...`で、rules fileへ埋め込んだ`match` / `not_match`のload-time検証に加え、各ruleから少なくとも1つの`prompt` / `forbidden`代表caseと、read-only boundaryの代表caseを実行します。

このrule集合は今回のrepository開発workflowで使うGit / GitHub CLI / local shell commandを対象にしたguardrailです。Git / GitHub CLIの全subcommand・全option・将来versionの新commandをrepository独自policy engineで再実装しません。

## 更新時の確認

- Main Planの「承認境界」「実装順序」「検証」「完了条件」と矛盾しないこと
- Codex 0.160.0の`codex execpolicy check`で全ruleがloadでき、各`match` / `not_match`がPASSすること
- `git` / `git.exe`、`gh` / `gh.exe`で代表`prompt` / `forbidden`が一致すること
- `git restore .`、`git checkout -- .`、`git switch --discard-changes feature/other`と、それぞれの`.exe`形式、安全な`git switch -c feature/new-work` / `git switch feature/existing-work`がすべて`prompt`になること。実Codexでは一時Git repositoryを使用し、破棄操作の承認を取り消して未commit変更が保持されること
- 正規prefixのexecpolicy承認と、先行オプションによる非対応形式のPreToolUse実行前denyをMain PlanのPOSIX / Windows contract testおよびfresh runtime受入で別々に確認すること
- 新規GitHub CLI操作と別名の代表例、およびMain Plan記載のtoken表示Hook denyを別途検証すること
- GitHub CLIのmutation-only集合を変更する場合は、実装時点の公式help referenceでsubcommandを再確認すること
- read-only commandを無承認に戻すためだけの独自option parserを追加しないこと
- rule追加を理由にGit / GitHub CLI全体のsecurity frameworkへ拡張しないこと

## 公式資料

- Codex execpolicy: https://github.com/openai/codex/blob/rust-v0.160.0/codex-rs/execpolicy/README.md
- GitHub CLI command reference: https://cli.github.com/manual/gh_help_reference
- GitHub CLI skill publish: https://cli.github.com/manual/gh_skill_publish
- GitHub CLI agent-task: https://cli.github.com/manual/gh_agent-task
- GitHub CLI discussion: https://cli.github.com/manual/gh_discussion
- GitHub CLI auth status: https://cli.github.com/manual/gh_auth_status
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
