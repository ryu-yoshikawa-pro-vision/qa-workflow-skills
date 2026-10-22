# Codexハーネスの通常commit・pull・fetch・push許可Plan

## 目的

`qa-workflow-skills` のCodexハーネスで、通常の `git commit`、安全な `git pull` / `git fetch`、作業ブランチへの通常の `git push` をexecpolicyの一律promptなしで実行できるようにする。`qa-training-store` のGit操作ポリシーを参考にするが、既存ハーネスのHook・execpolicy・テストを最小限修正する。

`main` への直接push、Force push、リモートrefの削除など、保護を外してはならない操作は引き続き拒否する。GitHubのRuleset変更は行わない。

## 現状と根拠

- 基準: `main` の `7cc6cba7772de549841a39d71694cbafbc783324`（Plan作成時）。
- `.codex/rules/20-risky-prompt.rules` の先頭ルールは `git` / `git.exe` の `commit`、`pull`、`fetch`、`push` を他の高影響Git操作と同様に `prompt` とする。そのため通常操作も承認を要求する。
- `.codex/rules/30-destructive-forbidden.rules` にpush専用の禁止ルールはない。現状のexecpolicyでは作業ブランチへのForce pushなども `prompt` に分類される。
- `.codex/hooks/pre_tool_use_policy.mjs` はcanonical repository root、直接Gitコマンド、current branch、明示されたprotected branch宛のpushを検証する。ただし `protectedPushTarget()` は明示された宛先の保護判定が中心で、Force push・暗黙のpush先・複数refspec・リモート設定由来の追加更新を包括的に拒否しない。
- `tests/codex/test_codex_hooks.py` は作業ブランチ・保護ブランチ・canonical rootのHook契約を検証し、`tests/codex/test_execpolicy_cli.py` は `git push` を `prompt` と期待している。
- `tests/codex/test_codex_config.py` は、実行中の2つの `.rules` と `docs/plans/2026-10-03_173600_formatter-lint_execpolicy-rules.md` のコードブロックの全文一致を必須としている。`.rules` だけ変更するとこの契約テストが失敗する。`docs/reference/codex-safety-harness.md` も過去Planを正本として参照している。
- `.github/workflows/codex-harness.yml` はUbuntu / WindowsでCodex CLIを導入し、既存のPython契約テストを実行する。追加CIワークフローは不要。
- 参考: `qa-training-store` の `.codex/rules/20-risky-prompt.rules` は通常pushを承認対象から除外し、同リポジトリの `.codex/rules/30-destructive-forbidden.rules` と `.codex/hooks/pre_tool_use_policy.mjs` は破壊的なpushを拒否する。

## 既存契約

- `.codex/config.toml` のgranular approval、`approvals_reviewer = "auto_review"`、Hook接続、sandbox設定は変更しない。
- Git mutationのcanonical root明示、1つの直接Gitコマンド、Windows / POSIX両経路、実行コンテキストが不明な場合の拒否は維持する。
- `main` / `master` とpush先remoteのローカル `refs/remotes/<remote>/HEAD` が示すデフォルトブランチへの直接push禁止、および従来の保護ブランチ上での状態変更禁止を維持する。remote HEADが未設定・読取失敗・不正またはpush先remoteと不整合の場合、通常pushは許可しない。これはローカル記録に基づく判定であり、Hook実行時にリモートへ接続して鮮度を確認しない。
- 通常commit・pull・fetch・pushを一律prompt対象から除外する。merge、rebase、reset、am、cherry-pick、revert、restore、checkout、switch等の既存分類は維持する。commit amendはHookで拒否し、静的な標準prefixはexecpolicyでもforbiddenにする。
- `git` / `git.exe` 以外のコマンド、GitHub CLI、QA Skill本体の挙動は変更しない。
- `2026-10-03_173600_formatter-lint_execpolicy-rules.md` は導入時点の記録として残す。変更後の有効なexecpolicyは `.codex/rules/*.rules` を正本とし、その判定を `codex execpolicy check` による契約テストで検証する。過去Planを新仕様に合わせて全面書換えしない。

## 対象範囲

### 変更するファイル

1. `.codex/rules/20-risky-prompt.rules` — 通常commit・pull・fetch・pushを既存の広い `prompt` ルールから除外し、`match` / `not_match`例を整合させる。他の操作分類は維持する。
2. `.codex/rules/30-destructive-forbidden.rules` — amendの標準prefixと、`git` / `git.exe` の静的に判別可能なForce push、リモートref削除・mirror等を `forbidden` にする。execpolicyのprefixで捕捉できない引数配置・refspecはHook側が判定する。
3. `.codex/hooks/pre_tool_use_policy.mjs` — 通常commit、fetch、fast-forward-only pull、pushの各許可条件を既存のroot検証と保護ブランチ判定に追加し、危険・不明形式は拒否する。汎用Git option parserは追加しない。
4. `tests/codex/test_codex_hooks.py` / `tests/codex/test_execpolicy_cli.py` — 判定変更と拒否条件の回帰テストを更新・追加する。
5. `tests/codex/test_codex_config.py` — 過去Planとの `.rules` 全文一致チェックを現在の契約から外す。`decision = "allow"` 禁止や既存設定・Hookのテストは残す。既存のGit操作の分類維持は `test_execpolicy_cli.py` で検証する。
6. `.codex/rules/README.md` / `docs/reference/codex-safety-harness.md` — 通常commit・pull・fetch・pushの承認・拒否条件と、現在の`.rules`が正本であることを明記する。
7. このPlan — 追加するcommit・pull・fetch契約を追記し、既存のpush目的と実Codex runtime完了条件を保持する。

### 対象外

- GitHub Ruleset、ブランチ保護、CI必須チェック、`.codex/config.toml` の承認方式の変更。
- commit・pull・fetch・push以外のGit操作に関する承認ルール変更。
- ラッパー・Run Artifact・ログ・Agent Skillsの新設や移植。

## 実装方針と順序

1. **基準確認:** 変更着手時の最新 `main`、関連ルール、Hook、既存テストの挙動を再確認する。差異があればPlanとの整合を確認する。
2. **危険なpushを拒否:** Hookで `git push` の引数をトークン単位で検証する。明示的な単一refspec、構成済みの名前付きremote、非保護ブランチ宛であり、追加更新が発生しないと確認できる場合だけ許可候補とする。判定不能なケースは拒否する。
3. **禁止対象:** `--force`、`-f`、`--force-with-lease`、`--force-if-includes`、`+refspec`、`--delete`、`-d`、空source（`:branch`）、`--prune`、`--mirror`、`--all`、`--branches`、`--tags`、`--follow-tags`、wildcard / matching refspec、複数refspec、宛先省略、URLやパスを直接remoteに指定する形式を拒否する。オプションの位置・短縮フラグの組合せでも抜け道を作らない。
4. **Git設定:** `push.followTags`、`push.recurseSubmodules`、`remote.<name>.mirror` 等、通常push以外のrefやsubmoduleを更新し得る実効設定を安全側に検証する。必要な値を取得できない場合も許可しない。既存の `qa-training-store` の判定手法を参考にし、汎用Gitパーサーは作らない。
5. **execpolicy調整:** Hookで安全境界を先に検証した後で `.codex/rules/20-risky-prompt.rules` から通常commit・pull・fetch・pushを外し、`.codex/rules/30-destructive-forbidden.rules` へ静的に判別できるamend / push禁止prefixを追加する。`no_match` はHookの安全判定を代替しない。Hookの動的引数拒否は維持する。
6. **既存契約との整合:** `tests/codex/test_codex_config.py` の全文一致チェックを過去Planに依存しない契約へ変更する。過去Planは変更せず、現在の `.rules` の妥当性はルール自体の `match` / `not_match` と `test_execpolicy_cli.py` の分類テストで判定する。`decision = "allow"` 禁止、および対象外Git操作の既存分類を維持する。
7. **テスト・文書更新:** 既存テストに通常commit・pull・fetch・pushと危険形式の正負例を追加し、README・安全ハーネス文書・このPlanの条件を更新する。実装時の編集対象は上記7項目に限定する。

**追加するcommit・pull・fetch契約:** 通常commitは明示的な`-m` / `--message`と対応optionに限り、amend・未知option・保護branchを拒否する。fetchは名前付きremoteのremote-tracking ref更新を許可し、保護local branchへのrefspec、force、refmap、stdin、prune-tags、明示設定により再帰取得が有効な一部の形式、判定不能な設定を拒否する。pruneは削除先をそのremoteのremote-tracking namespaceに限定できる場合だけ許可する。pullは保護branchを拒否し、`--ff-only`、実効`pull.ff=only`、または`pull.ff`未設定時の`merge.ff=only`が確認できる場合だけ許可する。未設定時のGit既定動作には依存しない。rebase、`--no-ff`、squash等の履歴書換えや追加mergeにつながる引数・実効設定は拒否する。

**保証範囲:** `qa-training-store`と同様、Git aliasの展開や進行中のmergeを通常commitで確定する操作まで一律に遮断するものではない。fetchでは、明示refspecとremoteのfetch設定に由来する更新先を検査するが、関連タグの自動取得と、再帰設定が未指定の場合のsubmodule取得（Git既定の`on-demand`）を完全には禁止しない。これらはGit標準動作として扱い、許可したfetchがremote-tracking refのみを更新すると保証しない。

## 検証

- `node --check .codex/hooks/pre_tool_use_policy.mjs` が成功する。
- `python -m unittest discover -s tests/codex -p 'test_codex_hooks.py' -v` が成功する。POSIX / PowerShell形式、`git` / `git.exe`、作業ブランチ / 保護ブランチ / コンテキスト不明を検証する。
- Codex CLIのある環境で `python -m unittest discover -s tests/codex -p 'test_execpolicy_cli.py' -v` が成功する。通常commit・pull・fetch・pushは `no_match`、標準commit amendと静的な危険pushは `forbidden`、対象外の高影響Git操作は従来どおり `prompt` を期待する。
- `python -m unittest discover -s tests/codex -p 'test_codex_config.py' -v` が成功する。過去Planとの全文一致に依存せず、現在の `.rules` の安全性契約を検証する。
- `python -m unittest discover -s tests/codex -p 'test_*.py' -v` が成功し、実装PRの `Codex Harness`（Ubuntu / Windows）の結果を確認する。
- Hook契約では通常commit・fetch・安全なpullをPOSIX / PowerShellの`git` / `git.exe`形式で許可し、保護branch上のcommit / pull、amend、保護local ref更新、force / refmap / stdin / prune-tags、rebase / no-ff / squashや危険な実効設定を拒否する。pruneは削除先をremote-tracking namespaceに限定できる設定だけ許可する。
- 許可例: canonical root上の `git push origin feature/existing`、`git push origin HEAD:feature/existing`、必要なら `git push -u origin feature/existing`。remote設定が安全で作業ブランチを指すことを前提とする。
- 拒否例: `git push origin HEAD:main`、`git push --force origin feature/existing`、`git push origin +HEAD:feature/existing`、`git push --delete origin feature/existing`、`git push origin :feature/existing`、`git push --mirror origin`、`git push origin`、`git push origin feature/existing other`。オプションをrefspecの後に置いた場合も拒否する。
- 非fast-forwardやGitHub認証失敗はGit本体・リモートのエラーとして扱う。Hookの許可はpushの成功やGitHubブランチ保護の解除を意味しない。
- **実Codexランタイムでの受入（必須）:** 利用するCodex CLIのversion、`CODEX_HOME`、承認設定、実行tool modeを記録する。freshな実セッションの `/hooks` で、このrepositoryの `Bash` `PreToolUse` Hookが信頼され有効であることを確認する。同じ経路で、通常commit・fetch・安全なpull・pushがHookの安全条件を通過しexecpolicyが一律promptを要求しないこと、amend・危険ref更新 / rebase pull・Force push・リモートref削除・保護branch上のcommit / pullおよび保護branch宛pushが実際のHook配送で拒否されることを確認する。Hookを直接起動する契約テストや `codex execpolicy check` だけでは代替しない。
- 実行まで試す通常pushは隔離した検証用ローカルGit repositoryとbare remoteなどに限定する。ユーザーの実リモートrefを変更せず、危険なpushはHookが実行前に拒否することだけを確かめ、実際には送信しない。
- 実ランタイムのHook信頼状態・配送・承認不要と拒否の振る舞いを確認できない場合は、理由と未検証範囲を `BLOCKED / 未検証` として記録し、安全性の受入や実装完了を宣言しない。

## リスク・前提

- **高リスク:** commit・pull・fetch・pushをexecpolicyの `prompt` から外した後にHookが未対応形式を見落とすと、履歴書換えや危険なref更新を無承認で実行し得る。Hookとexecpolicyの両側の拒否テストを先に整える。
- **前提:** リポジトリ固有Hookが信頼され有効であり、意図するCodex実行経路で動作する。Hookが未接続・未信頼の場合、execpolicyの `no_match` を安全性の保証に使えない。`/hooks` の信頼状態と実際の `PreToolUse` 配送を確認できない実行経路は、安全性の受入対象外とする。
- **制約:** execpolicyのprefixだけでは、引数の位置が変わるForce pushや `+refspec` を網羅できない。補完するHookの判定を必須とする。
- **制約:** Gitのpushにはリモート状態・認証・ブランチ保護による独立した拒否条件があるため、本変更でそれらを上書きしない。

## 完了条件

- 作業branch上の安全な通常commit・pull・fetch・pushは、既存のcanonical root形式でHookが各操作の安全条件を確認し、execpolicyでも一律promptを要求しない。
- commit amend、履歴書換えpull、保護local ref更新・force/refmap/stdin形式のfetch、Force push・リモートref削除・保護branch宛・曖昧な送信先・追加更新の可能性がある操作は、承認の有無にかかわらず拒否される。
- 対象外Git操作の既存承認分類、root固定、Windows経路、保護branchの安全性に回帰がない。
- 過去Planとの全文一致による既存テストの不整合を解消し、他のGit操作の承認分類・設定に回帰がない。
- 対象の契約テスト・実装PRの `Codex Harness` CI（Ubuntu / Windows）が成功している。
- 実CodexセッションでHookの信頼・有効化と `PreToolUse` 配送、通常commit・fetch・安全なpull・pushの承認不要と危険操作の拒否を確認できている。未確認の場合は実装未完了とする。

## 参照

- [`qa-workflow-skills` のexecpolicy](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/blob/main/.codex/rules/20-risky-prompt.rules)
- [`qa-workflow-skills` のPreToolUse Hook](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/blob/main/.codex/hooks/pre_tool_use_policy.mjs)
- [`qa-training-store` のexecpolicy](https://github.com/ryu-yoshikawa-pro-vision/qa-training-store/blob/main/.codex/rules/20-risky-prompt.rules)
- [`qa-training-store` のPreToolUse Hook](https://github.com/ryu-yoshikawa-pro-vision/qa-training-store/blob/main/.codex/hooks/pre_tool_use_policy.mjs)
