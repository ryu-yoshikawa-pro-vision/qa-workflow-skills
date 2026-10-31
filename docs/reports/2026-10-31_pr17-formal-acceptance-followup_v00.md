# PR #17 認証異常終了・競合・Judge受入準備の追跡報告

## 結論

認証storeの異常終了を安全側に保つlauncher回帰と、process-concurrencyが未解決の間にoperator login / recoveryを拒否するガードを追加した。固定Codex CLIの通常refreshを記録した合成試験は、2 process間の保存・再読込を示す。一方、試験記録に実行binary digestがなく、Codex CLI本体のtruncate後partial-write / 強制終了は試験していない。非協調processの起動主体を制限するOS境界もない。

そのため`AUTHENTICATION_REFRESH_PERSISTENCE_UNRESOLVED`と`AUTHENTICATION_PROCESS_CONCURRENCY_UNRESOLVED`を`True`のまま維持する。通常Agent / Judge / Repair、operator login / recoveryは現状のままfail-closedとし、実認証、`codex exec`、モデルAPI、独立Judge、正式QTS repeat、自動Skill改善は実施していない。Judge fixtureは11件すべて未承認で維持する。

## 対象revisionと既存証拠

| 項目                   | 確認結果                                                                                                                                                                                                                                 |
| ---------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 作業開始HEAD           | `8801520f1a7c32979a3a0507fa555fd9f7cea5f8`                                                                                                                                                                                               |
| GitHub PR開始状態      | PR #17 OPEN、base `main`、head `feat/agent-eval-runner`、HEAD一致                                                                                                                                                                        |
| 作業worktree           | `work/pr17-auth-wsl-20261025`、開始時clean。別worktreeは変更していない                                                                                                                                                                   |
| 開始HEAD CI            | PR-triggered 5 workflowすべてSUCCESS。run IDはCode Quality `41106525817`、Agent Skills `41106525873`、Deterministic `41106525614`、Semantic `41106525782`、Codex Harness `41106525827`                                                   |
| 前回refresh evidence   | `.agent-eval-runs/pr17-auth-refresh-synthetic-20261031-04/`。directoryと記録はowner-only mode `0700` / `0600`                                                                                                                            |
| 前回isolation evidence | `.agent-eval-runs/pr17-residual-formal-smoke-20261031-01/isolation.json`。HEAD `8801520…`のschema 2、16 checks、`verified`                                                                                                               |
| 固定CLI                | `/home/sella/.cache/qa-workflow-skills/pr17-wsl2-migration-20261024-a/runtime-final/package/vendor/x86_64-unknown-linux-musl/bin/codex`。`codex-cli 0.163.0`、SHA-256 `399ff69c431c066e40de318fba45c2b07f45a76b19939d247ee4828fc70c4215` |
| 前回QTS完了解釈メモ    | `.agent-eval-runs/pr17-residual-formal-smoke-20261031-01/plan-workflow-completion-interpretation.md`                                                                                                                                     |

refresh結果JSONは合成tokenの値・内容hashを含まない。`protocol`はCodex CLI 0.163.0 app-server `getAuthStatus(refreshToken=true)`と記録され、source harness / fake childを使った通常refresh結果とは区別されている。ただし各processのbinary digestが記録されていないため、別のisolation evidenceにある固定binary digestとは結び付かず、固定binaryのrevision-bound実行証明としては不十分である。実験は2つの独立process、2 mock request、clean exit、2つ目のprocessによる更新refresh状態の再読込を記録し、実auth store・model APIを使っていない。`interrupted_or_partial_write_tested=false`である。

固定CLI 0.163.0の[file backend](https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/login/src/auth/storage.rs#L1795-L1824)は`auth.json`をtruncateしてwrite / flushする。該当実装にはatomic replacementとfile `fsync`がない。成功時のrefresh永続化証拠だけでは、途中終了後に元tokenへ戻すことや、破損storeを再利用することの安全性は示せない。

## 異常終了・retry・回復

| 条件                               | 実施・証拠                                                                                                                                                                                                                                        | 判定 |
| ---------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---- |
| refresh前状態                      | 既存の合成probeがisolated temporary `CODEX_HOME`と合成tokenを使用。実storeは未使用。refresh attemptの個別binary digestは欠落                                                                                                                      |      |
| 通常refresh成功後の別process再読込 | 前回record: 2 process / 2 mock request、boolean summaryで更新state再読込あり                                                                                                                                                                      |      |
| truncate後の途中write・強制終了    | 新規回帰test `test_killed_process_after_partial_auth_write_keeps_marker_and_blocks_retry`。合成childがmode `0600`のtest fileをtruncateしpartial bytesを書いた後SIGKILLされ、marker残存とretry拒否を確認。固定CLI processのcrash injectionではない |      |
| store `fsync` failure              | 既存 / 新規launcher testでstore sync failure時に不確定markerを保持                                                                                                                                                                                |      |
| process timeout / 異常終了         | `test_timed_out_attempt_keeps_uncertain_marker_and_refuses_retry`等のlauncher testでmarker保持・retry拒否                                                                                                                                         |      |
| marker保存・除去sync失敗           | marker clear directory sync failure時、再作成したmarkerを確認。recovery fsync failureではauth fileを復元せずmarkerを保持                                                                                                                          |      |
| 次attempt                          | `test_killed_process_after_partial_auth_write_keeps_marker_and_blocks_retry`でuncertain stateによる拒否を確認                                                                                                                                     |      |
| 復旧                               | 明示確認がなければ拒否。確認済みの合成経路は不確定storeを読まず削除しdirectory sync後markerを消し、`operator_login_required=true`を返す。古いstoreのbackup / restore、login、Codex起動、model APIなし                                             |      |
| 競合未解決中のlogin / recovery     | 今回追加したprocess-concurrency gateがhelper・subprocess実行前に拒否。`AUTHENTICATION_PROCESS_CONCURRENCY_UNRESOLVED=true`の本番値を変更していない                                                                                                |      |

したがって、partial-write safetyは**launcher側のmarker/retry制御を合成processで確認した範囲**に限る。固定Codex CLIの途中書込み・fsync failure・SIGKILL後の実際のauth file状態、timeout中のCLI内部挙動、実専用UIDからの回復、正常login後の再試行は未検証である。古いrefresh tokenを復元する処理は追加していない。回復は確認後に専用storeを破棄し、所有者が別途新規loginする設計である。

## 非協調process競合

既存のnonblocking `flock`は同じlockを取得するrunner同士を直列化する。process inventoryは検査時点の同じUID processを見つけて停止できる。しかし、advisory lockを使わない同UID processはstoreを開ける。inventory後に新しいprocessを開始することも、`0600` storeへの同UIDアクセスも防げない。launcherのlockだけを競合解決証拠にしていない。

| 起動主体 / 状況             | 現在の挙動・限界                                                                             |
| --------------------------- | -------------------------------------------------------------------------------------------- |
| 協調runner                  | `flock`が競合runを拒否                                                                       |
| lockを無視する同UID process | 現在のscanで見つかれば拒否。scan後の起動、またはscanを無視する別processは排除できない        |
| 管理者 / root               | UIDを指定してprocessを開始でき、file・process境界を迂回できる。信頼境界として扱う            |
| inventory後の競合           | atomicなUID予約・起動制御がないため防止を証明できない                                        |
| 異常終了後に残るCodex       | markerがretryを止める。残存service processはinventoryが検出すればrecovery/finalizationを拒否 |

読み取り確認では`qa-agent-eval` user/groupは未登録だった。`systemctl`実行ファイルはあるが、service bus照会はsandboxから`Failed to connect to bus: Operation not permitted`で停止した。account、systemd policy、sudoers、固定runtime/sourceは作成・変更していない。よってprocess競合は未解消である。

### 管理者に必要な操作

この作業では管理者操作を実行していない。正式評価前に管理者が以下を行う必要がある。

1. `getent passwd qa-agent-eval`と`getent group qa-agent-eval`で既存entryがないことを確認する。既存なら変更せず停止する。
2. root権限で専用system accountを作成し、`/usr/sbin/nologin`、locked password、追加groupなし、sudo権限なし、mode `0700`の専用home/storeを設定する。現READMEの準備例は`sudo useradd --system --user-group --create-home --home-dir /var/lib/qa-agent-eval --shell /usr/sbin/nologin qa-agent-eval`、`sudo passwd --lock qa-agent-eval`および専用directory作成である。
3. 固定Codex runtime、clean evaluator checkout、Python環境をroot所有・service UID read-onlyの`/opt/qa-agent-eval/`へ配置し、source revision / binary digestを照合する。評価outputと必要なstateだけをservice UID writableにする。既存の開発者`CODEX_HOME`はコピーしない。
4. 同UID processの起動元を限定する。root所有のfixed runner entrypoint / service unitを用意し、sudoersまたはpolkitで許可する起動操作をそのentrypointだけに限定する。一般利用者に汎用`sudo -u qa-agent-eval`、`runuser`、shell、interpreter起動を許可しない。service unitの`ExecStart`を既存launcher / runnerに固定し、同時起動を拒否する。root/WSL administratorは依然として信頼主体であり、同時に別processを始めない運用が必要。
5. `id qa-agent-eval`、`passwd -S qa-agent-eval`、`sudo -l -U qa-agent-eval`、`stat`で所有者・mode・group・権限を確認する。許可されたrunner以外の同UID process起動が拒否されること、同時runnerが一方だけになること、lockを無視する既存processが検知されること、service entrypoint以外からの任意Codex起動を拒否することを確認する。失敗時はsystemd unit / policyを無効化し、login前ならaccountを削除してもhomeを残す。認証後のtoken/store削除やrevokeは所有者の判断なしに行わない。

作成・変更対象は`/etc/passwd`・`/etc/shadow`・`/etc/group`、`/var/lib/qa-agent-eval/`、`/opt/qa-agent-eval/`、必要ならroot-owned systemd / sudoers / polkit設定である。root/sudoが必要で、通常WSLユーザー設定や既存auth storeを変更しない。今の作業環境ではsystemd busがsandboxから利用不能なため、これらの検証に必要な管理者・通常WSL2 host環境が必要となる。

## QTS workflow完了条件

前回の解釈記録`.agent-eval-runs/pr17-residual-formal-smoke-20261031-01/plan-workflow-completion-interpretation.md`は、親Planの「QA workflow品質を完了」とフェーズ2Planの「評価attemptを最後まで実行」を別の対象として整理している。フェーズ2のattemptは終端routing（`complete` / `blocked` / `incomplete`）と証拠保存まで進める。親Planの受入はCheckout / Payment QA自体が各完了条件を満たすことを別途要求する。表現はやや曖昧だが、この解釈に論理的な受入条件の矛盾は確認されなかった。

固定QTSの未解決仕様が残るため、保存済みworkflowの`in_progress` / `can_complete=false`と親PlanのQA完了項目未達を維持する。tracked Plan、QTS製品仕様、保存済み成果物は今回変更していない。品質条件を弱める文言変更もしていない。

## Judge fixtureの受入準備

catalog revisionは`qts-judge-fixtures-v2`、target revisionは`84ce165493649550832731a60cf436f8ae29c56b`。11 fixtureはtune 5件とindependent 6件でsplitは重複しない。rubricは10 criterion（critical 9、`QTS-SEM-008`はnoncritical）。承認状態はpending deterministic 2件、pending human 9件、approved 0件。approval mapは0件で、fixture / rubric / Reference / approval bindingは変更していない。

| Fixture               | split / criterion | 固定mutation・期待                                                 | 確認済み根拠 / 推奨                                                                                                      | 必要な人間判断                                                                                               |
| --------------------- | ----------------- | ------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------ |
| `normal-workflow`     | tune / 001–002    | mutationなし、各rating >=3                                         | 実baseline成果物なし。routing・最終判断のcriterion別coverageを立証できない。pending維持                                  | baselineが両criterionを独立に満たすか、rating下限が妥当か                                                    |
| `normal-artifacts`    | tune / 003–010    | mutationなし、各rating >=3                                         | 実baseline成果物なし。8 criterion別に根拠が割り当てられていない。pending維持                                             | 成果物ごとのroot evidenceと各criterion rating範囲                                                            |
| `major-violation-001` | independent / 001 | 必須`test-case-design`をskip、rating 1                             | synthetic mutationで`noncompleted_routing`と`required_artifact_not_registered`を検出。実baselineとartifact bindingなし   | validator findingがrubric 001のcritical rating 1を直接裏付けるか。決定論的承認者がevidence bindingを確定する |
| `major-violation-002` | independent / 002 | 必須incomplete stageがあるのにcompleteを主張、rating 1             | synthetic mutationで`noncompleted_routing`を検出。実baselineとartifact bindingなし                                       | incomplete stageと完了主張がcriterion 002のrating 1に十分か。決定論的承認者がbindingを確定する               |
| `major-violation-003` | tune / 003        | unresolved cross-platform pixel parityをWeb oracleへ昇格、rating 1 | 固定QTSのunresolved-specはpixel parityを未決定とし、unresolved事項をoracleにしない。違反の狭さは妥当そうだが人間確認待ち | mutationが未確定事項の不正な昇格だけを評価するか                                                             |
| `major-violation-004` | independent / 004 | expired Checkout Sessionを有効として再開、rating 1                 | BR-CHECKOUT-001とstate/scenarioで24h expiry / expired terminalを確認                                                     | Checkout Session境界とrating 1の対応が正確か                                                                 |
| `major-violation-005` | tune / 005        | stale Cart Version / price mismatch後にOrder確定、rating 1         | BR-CHECKOUT-002とBR-CART-003が不一致時の再検証を要求                                                                     | 明示された不一致のみを対象にし、承認済み価格変更を誤検出しないか                                             |
| `major-violation-006` | independent / 006 | 明確なPayment failure後にinventory減算、rating 1                   | BR-CHECKOUT-003、orders、admin-inventoryの整合契約                                                                       | explicit failureとprocessing / success後の不足を混同しないか                                                 |
| `major-violation-007` | independent / 007 | processing中retry / cancel許可、rating 1                           | BR-CHECKOUT-003とstate/scenarioが処理中のretry / cancelを禁止                                                            | failure後の許容状態へ過剰一般化していないか                                                                  |
| `major-violation-009` | independent / 009 | Authorityから別要件の意味へ誤接続、rating 1                        | Checkout ACの意味差からtraceability violationを確認可能                                                                  | criterionが単なるID linkでなく意味保持を採点すること、期待ratingの妥当性                                     |
| `major-violation-010` | tune / 010        | 外部Stripe連携を確定済みbehaviorとして追加、rating 1               | Product ScopeはLocal Mock Payment、外部providerはscope外。unresolvedを確定仕様へしない                                   | unsupported confirmed behaviorを限定して採点し、提案の単なる言及を誤検出しないか                             |

violation fixtureの規範path・詳細な確認質問は[2026-10-26現在状態報告のJudgeレビュー資料](./2026-10-26_pr17-current-status_v00.md#judge-fixtureの判定と人間レビュー資料)に記録済みである。001 / 002の既存deterministic mutation確認はJudge rubric全体の正解承認ではない。正常fixtureには正規baselineがなく、major violationの一部も仕様解釈と評価幅の人間確認が残る。AIはfixtureをapprovedにせず、正式Judge評価を開始しない。

## 変更とローカル検証

| ファイル                                                             | 変更                                                                                                                                              |
| -------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| `scripts/skills/evals/agent/tools/codex_wsl2_bwrap_launcher.py`      | 明示確認付きの不確定専用store破棄・再login recovery CLIを追加。process-concurrency unresolved時はoperator login / recoveryをstoreアクセス前に拒否 |
| `scripts/skills/evals/agent/tests/test_codex_wsl2_bwrap_launcher.py` | truncate後SIGKILL、marker保持、retry拒否、fsync failure、recovery拒否・未実行login、process gateの合成回帰を追加                                  |
| `scripts/skills/evals/agent/README.md`                               | refresh evidenceの不足、process-start boundary、recovery/login gate、管理者操作条件を明記                                                         |
| `docs/plans/2026-10-24_135100_pr17-wsl2-bubblewrap-migration.md`     | 現状、実装範囲、未達gate、Judge statusを追記                                                                                                      |
| 本報告                                                               | 判定・証拠・残課題を記録                                                                                                                          |

検証結果：

- launcher unit suite: 46 tests PASS、1 skipped。
- Agent eval suite: 163 tests PASS、2 skipped。fake Agent/QTSのnegative fixtureが意図的に`execution_error` / `needs_review`を出力するがsuiteは成功。これらを実Agent結果と扱っていない。
- fixed-runtime WSL2 launcher integration: 開発sandboxではAF_UNIX bindが`EPERM`で失敗。通常WSL2実行境界で同じ合成テストを再実行しPASS（1 test）。認証store・model APIは未使用。
- Judge validation suite: 12 tests PASS。fixture approvalは変更していない。
- `tests.skills.runtime.test_qa_workflow_baseline`, `test_question_ids`, `test_workflow_runtime`, `test_qa_workflow_runtime`: 43 tests PASS。
- repository Agent eval contract suite: 4 tests PASS。
- `compileall`: PASS。
- Ruff `check` / format: PASS。repo venvにruffがなく、既存固定Ruff 0.16.8 tool pathを使った。新規installなし。
- `python scripts/format_tracked.py check`: PASS、241 tracked files formatted。
- dprint 0.55.2で変更済みPlan / READMEをcheck: PASS。
- `git diff --check`: PASS。

`--operator-recover-auth`成功テストは合成pathとprocess-concurrencyが解決済みというテスト内の明示条件だけで実施した。現在のproduction flag値は変更していない。全Unit / Fake testsは認証file・token・モデルAPIを使用しない。

開始HEADのGitHub Actions 5件はSUCCESSだった。今回のcommit後の5 workflowはpush後、最終HEADのcheck結果をGitHub PR Checksから確認する。ローカルで実Agent評価やJudge呼出しは実行していない。

## 正式受入に残る条件

### コード・合成検証で進めた範囲

- launcherの異常終了marker / retry拒否test、明示確認付き回復helper、process-concurrency未解決時のoperator login / recovery gateを追加した。
- 固定CLI 0.163.0の通常合成refresh/reload evidenceと、Codex file backendのwrite実装を照合した。
- Judge fixtureごとの入力mutation / criterion / 期待rating / 規範根拠と人間判断事項を整理した。

### 人間・管理者の対応が必要な範囲

- **専用OS identity / process-start boundary:** account、root-owned runtime/source/venv、fixed service entrypointと限定sudoers / polkitは未作成。OS管理者によるsetupと起動制限の実証が必要。
- **refresh異常時の固定CLI実測:** synthetic process testと異なり、Codex CLI本体のtruncate後partial write / forced termination / file sync failureを実バイナリで記録し、同一binary digestをevidenceへbindingする必要がある。auth recovery後の本人再loginは別途明示的な所有者操作。
- **非協調process:** lockを無視する同UIDプロセスとinventory-after-check起動をOS start boundary上でnegative testする必要がある。root / WSL管理者は信頼境界として明示し、同時起動を避ける。
- **Judge approval:** 11件中2 deterministic reviewは実baseline/bindingの最終確認、9件は規範仕様とrating rangeの人間判断を要する。承認後にのみ、fixed independent Judge profileによるJudge validationが可能。
- **正式Agent / QTS evaluation:** 前記auth / process conditions、current revision用fresh isolation evidence、本人のChatGPT認証とmodel API利用許可、Judge approvalが揃うまで未実施。
- **自動Skill改善受入:** fixed baselineの2-attempt再現、検証済みJudge、隔離candidate、独立回帰と比較が未実施。

これらが未達のため、認証の両fail-closed flag、Judge fixture status、QTSの`can_complete=false`、PRの未完了受入項目を変更していない。
