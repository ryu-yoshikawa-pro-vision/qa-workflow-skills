# Codex開発ハーネスの安全境界

この文書は、repository-local Codex開発ハーネスの目的、承認経路、保証範囲を説明します。対象はCodex CLI `0.160.0`です。設定・Hook・execpolicyの具体例は [Main Plan](../plans/2026-10-03_173600_formatter-lint.md) と [execpolicy rule一覧](../plans/2026-10-03_173600_formatter-lint_execpolicy-rules.md) を正本とします。

## 責務の分担

- `.codex/config.toml`はgranular approval、4つのcustom agent、`Bash`の`PreToolUse` command Hook、固定profileを宣言します。
- `.codex/rules/20-risky-prompt.rules`は高影響Git / GitHub CLI familyを`prompt`へ送り、`.codex/rules/30-destructive-forbidden.rules`は限定した破壊command familyを`forbidden`にします。通常command用の`allow` ruleはありません。
- `pre_tool_use_policy.mjs`は実行時にrepository rootやcurrent branchを必要とする誤操作guardrailです。承認分類をexecpolicyと二重実装せず、特定の非対応形式を実行前denyします。
- Windowsの`.ps1` launcherはJSON stdin、stdout、stderr、exit codeをNode Hookへ転送するtransportだけを担当します。
- `AGENTS.md`は全作業で必要な短いrepository契約です。Codex標準のproject instruction復元とcompact後の挙動を受け入れます。独自`SessionStart` Hookや独自context-limit overrideは使いません。

この構成はCodexの通常開発経路で誤操作を防ぐためのguardrailです。OS process境界や別security principalを作るsecurity sandboxではなく、任意shell、Git、GitHub CLI、MCP入力の全構文や全副作用を解析・隔離するpolicy engineでもありません。

## execpolicyの承認範囲

Gitのcommit、merge、rebase、pull、push、fetch、reset、amend、cherry-pick、revert、restore、checkout、switchと、混在するbranch / tag / config / remote / worktree / stash familyはPlanに列挙したprefixで承認へ送ります。feature branch上のforce push、hard reset、commit amendも承認対象のままです。protected branch上ではHookのcontextual denyが優先します。

GitHub CLIの変更操作とローカル状態を変える操作は、Planに列挙した組み込みaliasを含めて`prompt`にします。これには`pr co` / `new`、`issue new`、`repo new`、`repo autolink new`、`secret remove`、`variable remove`、`skill add` / `skills add`、`at`、`agent-task`別名、release aliasが含まれます。これらはGitHub CLIの組み込みaliasだけを扱い、ユーザー定義alias、将来追加されるsubcommand、未知のCLI形式を網羅しません。`gh auth status`の通常形もfamily-level `prompt`です。

`gh api`、`gh repo sync`、`gh auth token`、Gitの`clean` / `rm` / `update-ref`と直接の削除commandはPlanの範囲で`forbidden`にします。`gh auth status --show-token`、`-t`、`--show-token=...`はHookが実行前にdenyします。実tokenを出すprobeは行いません。

execpolicy prefixは分解済みargvへ照合します。subcommandより前にglobal optionを置くGit / gh形式や、shellが展開する引数を含む一部のcommandは内部のGit / gh argvとして照合されないことがあります。そのため、execpolicyのrule未一致だけを無承認実行の安全根拠にしません。

## 承認モード

通常運用ではCodex UIの`Approve for me`を使い、`.codex/config.toml`でも`approvals_reviewer = "auto_review"`を設定します。OpenAIの[公式config reference](https://developers.openai.com/ja-JP/docs/config-file/config-reference)では`user` / `auto_review`が有効値として定義されています。`auto_review`は承認要求のreviewerを指定する設定で、sandboxやgranular approvalの値は変えません。

この設定は実行権限や作業範囲を広げません。`PreToolUse`のdeny、execpolicyの`forbidden`、sandbox制約を維持し、`Approve for me`を理由にGit安全境界を省略しません。実repositoryへのcommit / push等は、ユーザーが依頼した範囲と適用Planに従います。

PR #18では`Ask for approval`への切替、ユーザー本人による承認・取消し、取消し後の状態不変を必須runtime検証にしません。`prompt` / `forbidden`の期待分類はrules、contract tests、利用可能な`codex execpolicy check`で確認し、`Approve for me`で危険commandを実行して表示だけを試しません。これは実runtimeの承認UIを検証したことを意味しません。

## Hookが受け付けるcommand形式

State-changing Gitでprotected branchを判定するとき、Hookが受け付けるのは次のliteralなcanonical repository root移動と、直後のdirect Git commandだけです。

```sh
cd '/literal/repository/root' && git push origin feature
```

```powershell
Set-Location -LiteralPath 'C:\literal\repository root' -ErrorAction Stop; git.exe push origin feature
```

Windowsでroot移動が失敗した場合は、`-ErrorAction Stop`により後続Gitを起動しません。`git -C`、`--git-dir`、`--work-tree`、動的なroot解決、wrapper、複数のmutation command、command-local environment overrideはこのcontext判定形式として扱わず、Hookがdenyします。異なる quoting や shell 記法について安全性を推測しません。

既知のshell解析失敗形式として、POSIXの未引用`git reset HEAD~1` / `git rm *.md` / `gh pr create --body "$BODY"`と、Windows PowerShellの対応する変数・wildcard展開を含む形式は実行前denyします。意味が同じliteral引数は既存execpolicyへ送ります。例: `git reset 'HEAD~1'`、`git rm '*.md'`、`gh pr create --body-file body.md`。この対応は汎用shell parserを意味しません。nested `bash -c`、`sh -c`、PowerShell command wrapper、`cmd /c`、`Invoke-Expression`等のopaque wrapperはdenyします。

`git` / `gh`のsubcommandより前にoptionを置く非対応形もdenyします。例えば`git -c user.name=test push ...`、`git --no-pager reset --hard`、`gh pr -R owner/repo merge ...`、`gh -R owner/repo pr merge ...`です。対応する通常prefixはHookが不要にdenyせず、execpolicyの承認・禁止分類へ進みます。

protected branch上のstate-changing Gitはdenyします。限定例外として、新しいlocal非protected branchへの`git switch -c <name>`と、既存local非protected branchへの`git switch <name>`だけをHookが通します。追加start-point、force/discard option、protected branch宛、存在しないbranchはdenyします。例外のswitchもexecpolicyの`prompt`を通す必要があります。

Feature branchからでも明示的にprotected branchをpush先とするrefspec（短縮名、`refs/heads`、削除、force prefix、複数refspecを含む）はHookがdenyします。Hookは暗黙push先、wildcard/matching refspec、Git configによる書換えなど全push先を解決しません。他の高影響pushはexecpolicyの`prompt`とtrusted Git設定へ委譲します。

## Gitのread-only分類と信頼境界

read-only Gitとは、refs、staged contents、working-tree contents、repository config、remote、worktreeをcommandの目的として変更しない形式です。`git status`等が内部でindex stat cacheを更新する可能性までlocal file writeゼロとは保証しません。

Gitはtrusted repository / user configurationやattributesに従い、filter、GPG、pager、Git Hook、credential helper、transport helperなどのprogramを起動する場合があります。このrepository-local Hookはそれらを完全に隔離・認証しません。`core.fsmonitor`、`core.hooksPath`、`filter.*`、`gpg.*`等を網羅するchild-process security frameworkは設けません。`git diff` / `log` / `show`の`--output`、`--ext-diff`、`--textconv`のような既知副作用形式はread-only扱いにしません。

同様に、HookはGitHub CLIのread-only全optionや将来の全alias、任意programの秘密情報出力を完全に分類しません。明示された変更family、unsupported option位置、shell展開形式、token表示flagだけを扱います。

## Hook trustとCodex runtime

Repository Hookが実行されるには、project trustとCodex CLIによるHook登録が必要です。起動したfresh sessionの`/hooks`で、このprojectの`Bash` `PreToolUse`が登録され、競合する同期Hookや`PermissionRequest` Hookが今回のsupported構成に混ざっていないことを確認します。trustを確認できないsessionやHook dispatchを確認できないtool modeは受入PASSにしません。

Windowsのquote-free `command_windows` payloadはtrusted repository内のlauncher sourceを読み込み、script blockとして実行します。PowerShell 5.1の`Restricted` policyでも必要なtransportを動作させるためです。launcherはrepository-local sourceのままtransport-onlyに保ち、通常ユーザーcommandを`Invoke-Expression`で評価しません。

Codex CLI `0.160.0`はruntime qualificationの対象です。実runtime受入を行う場合はversion完全一致と`codex --no-daemon --strict-config`のembedded / non-shared sessionを確認し、managed/shared app-serverを受入済みと扱いません。現在のCLI versionやsession条件が異なる、または取得できない場合はその範囲を未検証とし、`0.160.0` runtime受入済みとは記載しません。PR #18では実行可能な安全確認だけを行い、この未検証だけで実装完了を停止しません。

Primary profileは`unified_exec = true` / `unified_exec_tty = false`です。#51175のfallback比較は、Plan所定の同一version・同一environment・同一tool modeのsupported runtimeでpositive smokeが実際にFAILした場合だけ適用します。PR #18ではPOSIX runtimeを利用できない場合にfallbackを試さず、その範囲を未検証と記録します。

PR #18では承認UIのprobe、手動cancel、破棄操作の状態不変確認、一時repository作成を行いません。破壊commandや実remote mutationも実行せず、既存contract testsと利用可能なexecpolicy分類確認を使います。

## Compact後のrepository指示

独自`SessionStart` Hookや全文重複注入でなく、Codex標準のproject instruction復元を使います。このPRでは自動compactを強制せず、取得できない内部model input / rolloutの直接検査を完了条件にしません。保持をruntime確認していない場合は未検証と記録し、確認済みと主張しません。

4 custom agentのrole記述は行動契約です。agentのrole固有read-only等を独立したhard sandbox境界として説明しません。

## Validationの証拠

CIのcontract test、利用可能な固定版CLIの`execpolicy check`、公式`skills-ref` validationは静的構造と回帰を検査します。これらはfresh Codex runtime acceptanceを代替せず、PR #18でもそのように記載しません。特にargvだけの`execpolicy check`は完全なPOSIX / Windows shell commandの分解やHook dispatchを証明しません。実runtimeを利用できない、または対象versionと一致しない場合はその範囲を未検証とし、他の完了条件を満たしていればそれだけを理由に実装完了を止めません。実行したruntime検証で不具合を確認した場合はFAILとして修正します。
