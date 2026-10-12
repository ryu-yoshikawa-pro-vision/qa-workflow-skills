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

通常運用では、ユーザーがCodex UIの`Approve for me`を選び、自動レビューによる承認処理を利用できます。execpolicyの`prompt`は承認要求を意味しますが、常にユーザー本人による承認を保証しません。`Approve for me`では個々の要求が自動レビューによって処理される場合があります。

この設定は実行権限や作業範囲を広げません。`PreToolUse`のdeny、execpolicyの`forbidden`、sandbox制約を維持し、`Approve for me`を理由にGit安全ゲートを省略しません。実repositoryへのcommit / push等は、ユーザーが依頼した権限とMain Planの完了条件を満たした場合に限ります。

承認画面の表示、取消し、取消し後の状態不変をruntime受入する場合は、Codex UIの`/permissions`で`Ask for approval`を選びます。画面を確認した後は承認せずcancel / denyします。`Approve for me`でcommandが完了しても、ユーザー本人の承認を確認した証拠にはしません。受入記録には実効承認モードを含め、手動受入後は`Approve for me`へ戻してかまいません。`.codex/config.toml`の`approvals_reviewer = "user"`はこの手動受入の基準設定として維持できます。

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

runtime受入は`codex-cli 0.160.0`完全一致を確認した後、`codex --no-daemon --strict-config`のfresh embedded / non-shared sessionで実施します。managed/shared app-serverのcross-session isolationを保証範囲に含めません。guardrail negative probeより先に、POSIX / Windowsでexit code 0と`codex-runtime-smoke` markerを返すharmless positive commandを確認します。Code Mode / CodeModeOnlyではnested `tools.exec_command()`がHookを実際に通ることを別途確認します.

Primary profileは`unified_exec = true` / `unified_exec_tty = false`です。これを使用するときは、通常文字列`write_stdin`でPreToolUseを迂回できないこともruntime acceptanceに含めます。#51175の同一version・同一environment・同一tool mode比較条件を満たしたときだけ、Planどおり`unified_exec = false`へfallbackできます。その場合`unified_exec_tty`および`write_stdin`前提の検査を残しません。fallbackでもcommand、Hook、execpolicy、approval、protected branch、compactの再検証がPASSしなければ受入はblockedです。

承認UIのprobeは安全な一時repositoryやdummy commandを使い、表示だけ確認して承認せずcancelします。reset / restore / checkout / switch discard、PR checkout、secret / variable変更、実remote push、token表示を実行しません。`git restore .`等のcancel後に一時repositoryのHEAD / refs / index / working treeが不変であることを確認します。

## Compact後のrepository指示

独自`SessionStart` Hookや全文重複注入でなく、Codex標準のproject instruction復元を使います。fresh trusted runtimeで、rootおよびnested directoryから手動compact、turn前およびturn途中の自動compact後に、root `AGENTS.md`の先頭・中間・末尾の既知契約が実際のmodel-visible inputに含まれることを確認します。返答文面のみで推定せず、可能なrollout / model input根拠を確認します。指示の欠落、不要な重複、trustや`project_doc_max_bytes`による未読込みを確認できない場合は受入をPASSにしません。

4 custom agentのrole記述は行動契約です。agentのrole固有read-only等を独立したhard sandbox境界として説明しません。

## Validationの証拠

CIのcontract test、固定版CLIの`execpolicy check`、公式`skills-ref` validationは静的構造と回帰を検査します。これらはfresh Codex runtime acceptanceを代替しません。特にargvだけの`execpolicy check`は完全なPOSIX / Windows shell commandの分解、Hook dispatch、approval UI、compact後のmodel inputを証明しません。Planに列挙されたruntime acceptanceが利用できない、または失敗した場合は未達・blockedとして記録し、静的test成功と混同しません。
