# PR #17 Agent評価ランナー認証・隔離検証 v05

- **確認日:** 2026-10-26
- **Repository:** `ryu-yoshikawa-pro-vision/qa-workflow-skills`
- **PR:** [#17](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/pull/17)
- **作業branch:** `work/pr17-auth-wsl-20261025`
- **検証基準HEAD:** `73328d4237a5c1ab913938ed83f980ee9b5a9a37`
- **検証対象:** 上記HEADを基準にしたlocal working tree。今回の修正は検証時点で未commitであり、別SHAの証拠として扱わない。
- **関連報告:** [v04](2026-10-25_pr17-chatgpt-auth-recovery_v04.md)

## 結果概要

現行のattempt専用`CODEX_HOME`のcopy/delete方式では、子processがattempt側のauth markerだけを更新してもcleanup後のattemptへ更新が引き継がれないことをsynthetic testで再現した。これはrunnerのfile操作の再現であり、Codex CLI自身のrefresh成功や過去の`refresh_token_reused`の直接原因を確定する証拠ではない。

Codex CLI `0.163.0`の固定sourceでは、refresh mutexは同一`AuthManager` instance内にあり、成功したtokenを選択中のstorageへ保存する。file storageは`auth.json`をtruncate/write/flushするが、CLI process間の共有lockやatomic replacementはない。従ってattempt-local copyは更新を失い、永続storeへ移すだけではshell可視性とrunner外Codex processとの競合を解決しない。公式実装は[auth manager](https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/login/src/auth/manager.rs)、[file storage](https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/login/src/auth/storage.rs)、[auth tests](https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/login/src/auth/auth_tests.rs)、[login status](https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/cli/src/login.rs)を参照。

安全な永続化・競合防止・shell非可視性を同時に保証する実装は確定できていない。そのため認証方式、store構成、評価条件は変えず、launcherをAgent/Judge/Repair全modeでfail-closedにした。ChatGPT login以外へのfallback、実認証・モデル通信、TC-OUT-001は実施していない。

## 変更内容

- `launch()`は`authentication_shell_visible_risk=true`の間、auth materialの確認・copyより前に`execution_error`を返す。観測値にはauth内容、marker、hashを出さない。
- formal launcher smokeはsynthetic `auth.json` markerをAgent/Judge/Repairのinner sandboxへ置き、store path、host側store path、他attempt store、environment、可視process FDを個別に検査する。記録するのはbooleanだけで、marker値をevidence/logへ出さない。
- 元の15 required isolation checksへ認証shell可視性checkを加え、計16件をevidence verifierの必須条件とした。marker readまたは別の可視性が成立した場合、modeおよび全体evidenceはverifiedにならない。
- auth copy/delete方式でfake childがattempt copyだけを更新する回帰testと、Agent/Judge/Repair全modeが認証情報に触れる前に拒否するtestを追加した。
- sandbox smokeのsetup中にsocket bind等が失敗したとき、一時auth home・他attempt home・outside sentinel・socketをcleanupし、cleanup失敗は隠さずsafe errorとして返す。
- READMEとWSL2移行Planへ追加check、現行fail-closed動作、通常WSL2での再検証コマンド、証拠の限界を追記した。v04は履歴として保持する。

## 検証結果

Python 3.11.17、PyYAML 6.0.3、Codex CLI 0.163.0の固定runtimeを使用した。依存の再インストールはしていない。Ruffは0.16.8、dprintは0.55.2。

| 検証                                                               | 結果                                                                                                                                                                                |
| ------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Agent suite                                                        | PASS: 138 tests、2 skipped                                                                                                                                                          |
| Agent repository contract                                          | PASS: 4 tests                                                                                                                                                                       |
| Semantic suite                                                     | PASS: 27 tests                                                                                                                                                                      |
| Codex Harness                                                      | PASS: 57 tests、8 skipped。PATHに固定Linux runtimeを追加して実行                                                                                                                    |
| Deterministic repository suite                                     | sandbox内293件中4 failures、1 error。AF_UNIX server bindは`EPERM`。他4件はsandbox実行時にProject Context state-root sourceを確保できず`blocked`になった。安全条件・テストは変更せず |
| WSL2 formal launcher integration                                   | 未完了: fixed runtimeを指定して再実行したが、synthetic marker検査前のhost AF_UNIX bindで`PermissionError(EPERM)`。通常WSL2から再実行が必要                                          |
| auth fail-closed / copy-refresh-loss / setup cleanup focused tests | PASS: 3 tests                                                                                                                                                                       |
| `compileall`                                                       | PASS                                                                                                                                                                                |
| `format_tracked.py check`                                          | PASS: Ruff 0.16.8 / dprint 0.55.2、239 files already formatted                                                                                                                      |
| `git diff --check`                                                 | PASS                                                                                                                                                                                |

Agent suiteの一部fake runner testは`pass`以外に`needs_review`や`execution_error`を意図的に生成する。これはAgent suite自体のtest failureではなく、summary resultを成功扱いへ変更していない。

利用者が前revisionについて通常WSL2 Ubuntuから共有したDeterministic 293件、formal integration 1件、AF_UNIX bindのPASSは、そのrevisionの結果としてのみ保持する。今回追加したsynthetic auth negative checkを含む現在の実装には流用しない。Codex開発sandbox内の結果も通常WSL2の結果と混同しない。

## Fresh isolation evidence

現在のworking treeは未commitであり、正式probeのclean-checkout条件を満たさない。加えてformal launcher integrationはsandboxのAF_UNIX bind `EPERM`で止まり、追加auth checkに到達しなかった。したがってこの変更に対するfresh isolation evidenceは生成していない。以前の`isolation.json`は再利用していない。

通常WSL2ターミナルで、変更をcommitしたclean checkout、schema 2 profile、`agent-command.json=["codex"]`、`verification.evidence_path="isolation.json"`、固定runtime、fresh output rootを使い、READMEの正式手順を実行する。期待する受入値は16 checks全true、Agent/Judge/Repairの各mode `verified`、同一revision/profile/command/runtime fingerprint、`model_api_used=false`である。もしsynthetic markerが読める場合、probeは`unverified`で終了し、そのevidenceはrunを許可しない。

## 未解決事項と実行再開条件

### refresh persistence / `refresh_token_reused`

attempt copyの更新喪失は再現したが、refresh reuseの過去障害に対する直接因果は確定していない。固定CLI sourceのloopback mock harnessによるrefresh・save・次process reloadは実行していない。`CODEX_REFRESH_TOKEN_URL_OVERRIDE`をproduction launcher/profileへ入れていない。

### process間競合

Codex `AuthManager`内のsemaphoreは別processと共有されず、file storageにもCLI間lockがない。runner内だけのlockでは、runner外のCodex CLIが同じstoreを使う競合を止められない。auth broker/proxyや認証方式変更はPlan対象外のため追加していない。全利用processを含む安全なstorage/lock契約が必要。

### shell可視性

過去にCodex shellからsynthetic markerが読めた事実があり、riskをtrueのまま維持する。追加したformal checkは現在のCodex development sandboxからは実行できていない。通常WSL2でcheckがread-deniedを示すまで安全性をverifiedにしない。Codex親processがauthと必要なAPI通信を維持することも、実authやmodel通信なしには確認していない。

### 残るユーザー操作

1. 通常WSL2 Ubuntu terminalからREADMEのDeterministic、formal integration、host AF_UNIX確認を実行する。
2. commit後のclean checkoutでREADMEにあるfresh `isolation_probe.py`を実行し、16 checks、3 mode evidence、fingerprintを確認する。auth markerが可視ならそこで停止する。
3. auth persistence、全process競合、inner shell可視性が解消・検証されるまで実認証評価を再開しない。

この報告作成時点では作業変更はlocal working treeのみで、PR #17へのpush、5 CIの変更後SHAでの実行、PR本文更新はまだ行っていない。`73328d4237a5c1ab913938ed83f980ee9b5a9a37`に対して以前確認した5 CI successは今回の修正を含まない。
