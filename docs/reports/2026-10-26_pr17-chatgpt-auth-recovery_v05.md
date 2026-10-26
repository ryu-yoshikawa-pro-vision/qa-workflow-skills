# PR #17 Agent評価ランナー認証・隔離検証 v05

- **確認日:** 2026-10-26
- **Repository:** `ryu-yoshikawa-pro-vision/qa-workflow-skills`
- **PR:** [#17](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/pull/17)
- **作業branch:** `work/pr17-auth-wsl-20261025`
- **検証基準HEAD:** `73328d4237a5c1ab913938ed83f980ee9b5a9a37`
- **検証対象:** 上記HEADを基準にしたlocal working tree。今回の修正は検証時点で未commitであり、別SHAの証拠として扱わない。
- **関連報告:** [v04](2026-10-25_pr17-chatgpt-auth-recovery_v04.md)

> **現在状態の参照:** 以下の初版結果・commit後追記はHEAD `73328d...`時点の履歴を含みます。HEAD `e87a4890514af6bff09b90bb180e4dcd9c3fddb7`に対する追加suite、fresh isolation evidence、固定CLI source再確認の最新結果は末尾の「2026-10-26 HEAD e87a489での再検証」を参照してください。GitHub CIはe87a489で5件すべてSUCCESSでした。

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

## 2026-10-26 commit後の追記

- 上記の修正内容をcommit `32294d24b776df4ec3f50c103b62672131ede873`に記録した。このcommitのparentは検証基準の`73328d4237a5c1ab913938ed83f980ee9b5a9a37`であり、検証後に実装treeの変更は加えていない。
- PR branchのremote HEADは`73328d4237a5c1ab913938ed83f980ee9b5a9a37`のままで、作業commitは未push。clean cloneでのcherry-pickはPreToolUse Hookがcanonical repository root条件で拒否したため停止した。別のdirty worktreeは変更していない。
- PR本文の冒頭をremote HEAD、同HEADの5件のCI、未push修正、未達の隔離・認証条件に合わせて更新し、それ以前の本文は保持した。
- 現在の5 CI successはremote HEAD `73328d4237a5c1ab913938ed83f980ee9b5a9a37`に対するもので、commit `32294d24b776df4ec3f50c103b62672131ede873`のCI結果ではない。

## 2026-10-26 HEAD e87a489での再検証

### 対象と実行環境

GitHub PR #17のheadと作業treeのHEADが`e87a4890514af6bff09b90bb180e4dcd9c3fddb7`で一致し、検証開始時のworking treeはcleanだった。元のdirty worktree `/home/sella/src/qa-workflow-skills`はread-onlyで状態を確認し、変更していない。実行環境はWSL2 Ubuntu、Python 3.11.17、PyYAML 6.0.3、固定runtime `/home/sella/.cache/qa-workflow-skills/pr17-wsl2-migration-20261024-a/runtime-final`、Codex CLI 0.163.0、同梱bubblewrap。

GitHub ActionsはこのHEADで5件すべてSUCCESS: Validate Agent Skills (run 1438)、Validate Deterministic Output Evals (run 1437)、Validate Semantic Output Evals (run 1402)、Code Quality (run 132)、Codex Harness (run 132)。この結果は後続commitのCIを示すものではない。

### 回帰suite

| 検証                           | 結果                                                                       |
| ------------------------------ | -------------------------------------------------------------------------- |
| Agent suite                    | PASS: 138 tests、2 skipped                                                 |
| Agent repository contract      | PASS: 4 tests                                                              |
| Semantic suite                 | PASS: 27 tests                                                             |
| Deterministic repository suite | PASS: 293 tests。host WSL実行で`TMPDIR=/var/tmp`を指定                     |
| Codex Harness                  | PASS: 57 tests、8 skipped。固定Linux Codex binaryをPATH先頭に指定          |
| 認証関連focused tests          | PASS: 3 tests。fail-closed、attempt copy更新喪失、ChatGPT login status分類 |
| `compileall`                   | PASS: `scripts/skills/evals/agent`とagent repository tests                 |
| Ruff 0.16.8 lint / format      | PASS: lintとtracked Python 239 filesのformat check                         |
| dprint 0.55.2                  | PASS: 今回変更した3文書を整形・check。full tracked formatterもPASS         |
| `git diff --check`             | PASS                                                                       |

Deterministic suiteをCodex sandbox既定条件で実行すると293件中4 failures / 1 errorとなった。errorはhost AF_UNIX bindの`EPERM`、4 failuresは`/tmp/.git`が検出されTemporaryDirectory配下のstate rootをrejectする環境条件だった。`TMPDIR=/var/tmp`はGit worktree外で書込み可能であり、同suiteはhost WSL実行で293件PASSした。テスト条件やsandboxは緩めていない。

正式launcher integrationもCodex sandbox内ではhost AF_UNIX bindの`EPERM`でmarker checkに到達しなかった。host WSL実行では1 testが認証可視性checkでFAILし、`authentication_store_read_denied=false`を検出した。他の記録checkはtrue。host AF_UNIX bind単体はPASSした。ここでのFAILは要件未達を正しく検出した結果であり、隔離受入のPASSではない。

Ruffは固定0.16.8を使い`format_tracked.py ruff-check`とtracked Python全fileのformat checkを個別実行した。dprint 0.55.2はWSL上のnpm cacheにあるLinux binaryを使い、今回変更した3文書とfull tracked formatterを実行した。Code Quality CIのe87 SUCCESSは、この文書差分を含む検証ではない。

### Fresh isolation evidence

READMEの正式なschema 2 profile、`agent-command.json=["codex"]`、`verification.evidence_path="isolation.json"`、`gpt-6-luna`、reasoning `max`、timeout 900秒、固定Codex runtimeを使い、run root `.agent-eval-runs/pr17-isolation-e87a489-20261025T234245Z`へ新しいevidenceを作成した。固定package / CLI / bwrap digest照合は成功し、evaluator revisionはHEADと一致した。

- Evidence path: `.agent-eval-runs/pr17-isolation-e87a489-20261025T234245Z/isolation.json`（ignored runtime artifact。repositoryにはcommitしない）
- Profile fingerprint: `sha256:10d3a666dd26c19123cf8ed2cfff1ea4914f14f9f3f5aa15a6316e73c38175d4`
- Agent/Judge/Repair command fingerprint: `sha256:e25eaf648dc7039953915d93cac78cc23b21b780b60f562ff1aaa53086f25364`
- Required checks: 14/16 true。`authentication_shell_read_denied=false`、`agent_judge_separated=false`
- Agent/Judge/Repair mode evidence: すべて`unverified`。Overall: `unverified`
- `model_api_used=false`: Codex sandbox smokeとsynthetic marker以外は起動していない。実認証、`codex exec`、model APIは使用していない。

Agent/Judge/Repair各modeで合成markerがinner shellから読めるため、auth store本体へのread拒否が成立しなかった。host auth path、other attempt store、environment、process FD等の該当checkはtrueだが、marker read可を補うものではない。`agent_judge_separated`は全mode evidenceがverifiedでないためfalseで、fresh evidenceを受入根拠にできない。実行後も`authentication_shell_visible_risk=true`を維持する。

### 固定Codex CLI 0.163.0認証実装の再確認

固定sourceの[`manager.rs`](https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/login/src/auth/manager.rs)では、ChatGPT access tokenのexpiryが5分以内ならproactive refresh対象となり、expiryを解析できない場合は`last_refresh`が8日より古いかをfallback判定する。401/unauthorized recoveryからもrefreshが呼ばれる。成功時には`request_chatgpt_token_refresh`、`persist_tokens(auth.storage(), ...)`、`reload()`の順で、選択中のstorageへ保存してからmemory cacheを再読込する。保存失敗はrefresh errorとなる。固定CLIの[`run_login_status`](https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/cli/src/login.rs#L421-L483)は`load_auth()`の結果を分類して表示し、refreshを呼び出さない。

`AuthManager`の`refresh_lock`はmanager instanceごとのsemaphoreでありprocessをまたがない。固定source [`storage.rs`](https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/login/src/auth/storage.rs)のfile backendはUnix mode 0600で`auth.json`をtruncate/write/flushするが、atomic replaceやCLI process間lockは実装していない。従ってattempt-local copyでは更新がcleanupで失われるというsynthetic runner testの結果と、Codex自身の保存契約は整合する。ただし過去の`refresh_token_reused`の直接原因とは確定できない。保存はtruncate後にwriteするため、open後にwrite/flushが失敗した場合に旧内容が保全される契約もない。

固定source [`auth_tests.rs`](https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/login/src/auth/auth_tests.rs)には`persist_tokens()`が合成tokenを保存するtestがあるが、ChatGPT refresh endpointを通したrefresh→保存→別process reloadの一連のtestは確認できなかった。同fileで`CODEX_REFRESH_TOKEN_URL_OVERRIDE`も参照されていない。本作業treeにもCodex CLI Rust source/test harnessはないため、このintegration harnessは実行していない。runnerのfake child testはcopy/delete file操作のみの検証として扱う。

### fail-closedの影響と未達条件

`AUTHENTICATION_SHELL_VISIBLE_RISK=True`のため、共通launcherのAgent/Judge/Repairは`_auth_material()`、auth file copy、Codex child起動前に`execution_error`で拒否する。これはdeterministic / semantic Agent、Judge validation、QTS Judge、improve analysis / Repair / re-evaluationの各共通launcher pathに適用される。既存focused test 3件は通過した。合成markerの読取りが可能な状態で認証実行を許可する変更は行っていない。

同じrunnerからの並行attemptは、それぞれ別CODEX_HOMEへ同じ元refresh tokenをcopyするため、ファイルlockがなくてもOAuth authority側でrefreshの競合が起こり得る。Agent/Judge/Repairは別Codex process/managerなのでmanager内semaphoreを共有しない。runner外のCodex processは元storeのpathを共有するが、runner attempt copyとはstore pathが異なる一方、元のrefresh tokenを同時利用すればauthority側で競合し得る。専用永続CODEX_HOMEへ移しても、Codex file backendにprocess間lockはなく、別processとの競合が閉じない。外部processを含む協調契約またはCodex公式のprocess横断排他と、inner shellからstoreをread-denyする方法の両方を実証可能なことが必要条件である。

そのためrefresh更新の永続化、process間競合、Agent/Judge/Repair shell非可視性のいずれも解消済みとは判定しない。実認証、TC-OUT-001、その他model通信は行っていない。docs-only follow-up commit後には新HEADを対象にformal evidenceを再生成する必要があり、この節のevidenceはe87a489以外のrevisionには結び付かない。
