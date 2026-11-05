# Codex開発ハーネスの安全境界

この文書は、repository-local Codex開発ハーネスの目的、承認経路、保証範囲を説明します。Codex CLIのversionは固定しません。Codex Harness CIはnpmの`latest` stable tagからCLIを導入し、実行versionを記録してから、Hook・execpolicy・config・launcherの契約を実CLIで検証します。現在のexecpolicyは`.codex/rules/*.rules`、pushの動的判定は`.codex/hooks/pre_tool_use_policy.mjs`、その期待分類は契約テストを正本とします。[2026-10-03のexecpolicy Plan](../plans/2026-10-03_173600_formatter-lint_execpolicy-rules.md)は導入時点の記録であり、現在のrule全文との一致要件ではありません。

## 責務の分担

- `.codex/config.toml`はgranular approval、4つのcustom agent、`Bash`の`PreToolUse` command Hook、固定profileを宣言します。
- `.codex/rules/20-risky-prompt.rules`は通常commit・pull・fetch・pushを除く高影響Git / GitHub CLI familyを`prompt`へ送り、`.codex/rules/30-destructive-forbidden.rules`は限定した破壊command family、commit amendの標準形、静的に判別できる危険pushを`forbidden`にします。通常command用の`allow` ruleはありません。
- `pre_tool_use_policy.mjs`は実行時にrepository rootやcurrent branchを必要とする誤操作guardrailです。承認分類をexecpolicyと二重実装せず、特定の非対応形式を実行前denyします。
- Windowsの`.ps1` launcherはJSON stdin、stdout、stderr、exit codeをNode Hookへ転送するtransportだけを担当します。
- `AGENTS.md`は全作業で必要な短いrepository契約です。Codex標準のproject instruction復元とcompact後の挙動を受け入れます。独自`SessionStart` Hookや独自context-limit overrideは使いません。

この構成はCodexの通常開発経路で誤操作を防ぐためのguardrailです。OS process境界や別security principalを作るsecurity sandboxではなく、任意shell、Git、GitHub CLI、MCP入力の全構文や全副作用を解析・隔離するpolicy engineでもありません。

## execpolicyの承認範囲

通常commit・pull・fetch・pushはexecpolicyの`prompt`対象外です。commit amendの標準形と静的に判別できる危険pushは`forbidden`で拒否します。`no_match`はHookやsandboxを通過してよいという意味ではありません。Hookはcommitを明示メッセージ付きの通常形式に限定し、amend・未対応option・動的引数を拒否します。pullはprotected branch上で拒否し、明示`--ff-only`、実効`pull.ff=only`、または`pull.ff`未設定時の`merge.ff=only`が確認できる場合だけ許可します。未設定時のGit既定動作には依存せず、rebase、`--no-ff`、squash、実効設定による履歴書換えや追加mergeがあり得る形式は拒否します。

fetchでは、明示refspecと`remote.<name>.fetch`のマッピングが、指定remoteの`refs/remotes/<remote>/`配下以外を直接更新する形式を拒否します。通常の名前付きremote fetchと、そのremote-tracking ref配下に限定できるpruneは許可候補です。force、`+refspec`、`--refmap`、`--stdin`、`--prune-tags`、対象外のref更新や判定不能なGit設定を拒否します。`fetch.prune`等の設定は、pruneの対象をremote-tracking namespaceに限定できる場合だけ許可します。`fetch.recurseSubmodules`など明示的な再帰設定も検査します。

ただし、Git標準のfetchでは、取得する履歴に関連するタグが自動取得される場合があります。また、`fetch.recurseSubmodules`が未設定の場合、Gitの既定動作は`on-demand`であり、変更されたsubmoduleを再帰取得する場合があります。現行Hookはこの既定動作を完全には遮断しません。したがって、**更新先がremote-tracking refのみであることや、submoduleへの取得が一切発生しないことは保証しません**。詳細は[Git公式のgit-fetch仕様](https://git-scm.com/docs/git-fetch)を参照してください。`.rules`の`no_match`に対する実行可否は引き続きHook・sandbox等の制御を受けます。

merge、rebase、reset、am、cherry-pick、revert、restore、checkout、switchと、混在するbranch / tag / config / remote / worktree / stash familyは従来どおり`prompt`へ送ります。静的に判別できるref削除、mirror、一括push等は`forbidden`で拒否し、引数位置やGit設定を含む動的な危険条件はHookが拒否します。protected branch上のcommit・pull等はHookのcontextual denyが優先し、通常fetchのみ安全なref更新を確認した場合に許可します。

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

作業branchからの通常pushは、設定済みの名前付きremote 1件と1つの明示refspecに限ります。sourceは現在branchまたは`HEAD`、宛先は現在branchまたは既知の非保護branch（local branch、または指定remoteのremote-tracking branch）である必要があります。現在branchと異なる宛先には`HEAD:feature/target`または`feature/current:feature/target`のようなsource:destination形式を使います。sourceと宛先を兼ねる単一branch名は現在branchに限り、未確認の宛先branchはdenyします。`-u` / `--set-upstream`以外のpush option、refspec後のoption、URLやpathの直接指定、remoteまたはrefspecの省略、複数refspec、wildcard/matching refspec、削除・force prefix、protected branch宛はHookがdenyします。

Hookはremoteに有効なpush URLが1件だけあることを確認します。保護対象は`main` / `master`に加え、push先remoteのローカル`refs/remotes/<remote>/HEAD`が示すデフォルトbranchです。このHEAD情報が未設定、読取失敗、不正、またはpush先remoteと不整合なら通常pushをdenyします。判定はローカル記録に基づき、Hook実行時にネットワークでremoteの最新状態を確認しません。`push.followTags`、`push.recurseSubmodules`、`remote.<name>.mirror`、`remote.<name>.push`が追加更新を起こし得る値の場合や、その設定を解決できない場合もdenyします。非fast-forwardや認証失敗はGit本体またはremoteが拒否します。Hookの通過はpush成功やbranch protectionの解除を意味しません。

## Gitのread-only分類と信頼境界

read-only Gitとは、refs、staged contents、working-tree contents、repository config、remote、worktreeをcommandの目的として変更しない形式です。`git status`等が内部でindex stat cacheを更新する可能性までlocal file writeゼロとは保証しません。

Gitはtrusted repository / user configurationやattributesに従い、filter、GPG、pager、Git Hook、credential helper、transport helperなどのprogramを起動する場合があります。このrepository-local Hookはそれらを完全に隔離・認証しません。`core.fsmonitor`、`core.hooksPath`、`filter.*`、`gpg.*`等を網羅するchild-process security frameworkは設けません。`git diff` / `log` / `show`の`--output`、`--ext-diff`、`--textconv`のような既知副作用形式はread-only扱いにしません。

Git aliasの展開は保証対象外です。また、進行中のmergeを`git commit -m`で確定する場合、Hookは`MERGE_HEAD`などの状態から通常commitとmerge commitを区別しません。これらの操作を含むすべての実行経路へ、個別のexecpolicy承認分類が適用されるとは保証しません。

同様に、HookはGitHub CLIのread-only全optionや将来の全alias、任意programの秘密情報出力を完全に分類しません。明示された変更family、unsupported option位置、shell展開形式、token表示flagだけを扱います。

## Hook trustとCodex runtime

Repository Hookが実行されるには、project trustとCodex CLIによるHook登録が必要です。起動したfresh sessionの`/hooks`で、このprojectの`Bash` `PreToolUse`が登録され、競合する同期Hookや`PermissionRequest` Hookが今回のsupported構成に混ざっていないことを確認します。trustを確認できないsessionやHook dispatchを確認できないtool modeは受入PASSにしません。

Windowsのquote-free `command_windows` payloadはtrusted repository内のlauncher sourceを読み込み、script blockとして実行します。PowerShell 5.1の`Restricted` policyでも必要なtransportを動作させるためです。launcherはrepository-local sourceのままtransport-onlyに保ち、通常ユーザーcommandを`Invoke-Expression`で評価しません。

実runtime受入を行う場合は、利用versionを記録し、`codex --no-daemon --strict-config`のembedded / non-shared sessionで対象tool modeのHook dispatch、execpolicy分類、sandbox、およびprotected branch / destructive Git guardを確認します。managed/shared app-serverは承認のsession isolationを確認できないため、受入済みと扱いません。version番号だけで検証を停止またはskipせず、必要な機能が存在しない、挙動が変わった、またはsession条件を確認できない場合は、その機能・範囲を未検証または互換性問題として記録します。

Primary profileは`unified_exec = true` / `unified_exec_tty = false`です。#51175のfallback比較は、Plan所定の同一version・同一environment・同一tool modeのsupported runtimeでpositive smokeが実際にFAILした場合だけ適用します。PR #18ではPOSIX runtimeを利用できない場合にfallbackを試さず、その範囲を未検証と記録します。

PR #18では承認UIのprobe、手動cancel、破棄操作の状態不変確認、一時repository作成を行いません。破壊commandや実remote mutationも実行せず、既存contract testsと利用可能なexecpolicy分類確認を使います。

## Compact後のrepository指示

独自`SessionStart` Hookや全文重複注入でなく、Codex標準のproject instruction復元を使います。このPRでは自動compactを強制せず、取得できない内部model input / rolloutの直接検査を完了条件にしません。保持をruntime確認していない場合は未検証と記録し、確認済みと主張しません。

4 custom agentのrole記述は行動契約です。agentのrole固有read-only等を独立したhard sandbox境界として説明しません。

## Validationの証拠

CIのcontract test、実行環境にインストールされたCodex CLIの`execpolicy check`、公式`skills-ref` validationは静的構造と回帰を検査します。Codex Harnessは使用versionを記録し、version一致ではなく利用可能なCLI機能と安全contractを検証します。これらはfresh Codex runtime acceptanceを代替せず、PR #18でもそのように記載しません。特にargvだけの`execpolicy check`は完全なPOSIX / Windows shell commandの分解やHook dispatchを証明しません。必要なCLI機能を利用できない、挙動が変わった、またはsession条件を確認できない場合は、その機能・範囲を未検証または互換性問題として記録します。他の完了条件を満たしていれば、version番号だけを理由に実装完了を止めません。実行したruntime検証で不具合を確認した場合はFAILとして修正します。
