# PR #17 統合workflow継続評価

## 結論

固定`qa-training-store` revisionで、Codex subagentによるQA workflowを実動作させた。必要な8種のQA成果物と条件付き`question-analysis`の計9件を生成し、production verifier、workflow runtime、artifact-index validatorで確認した。個別Skillの7 verifierはすべて`valid=true`で、current runtime fingerprintとEntity参照を確認できた。

一方、workflowは未完了である。coverageとworkflow runtimeは未解決モデルを含み`can_complete=false`、`qa-workflow` routingは`incomplete`、artifact-indexは正当な未完了・skipを理由に`needs_review`となった。これらをPASSへ読み替えていない。

通常のworkflow stateはattempt専用rootに初期化され、同じ`workflow_ref`での読み取りとProject Contextのcurrentness確認に成功した。前回attemptではSQLite状態rootがGit worktree内にあり初期化されていなかった。今回のCheckout / Payment分析にはWCAG評価用SQLiteは不要であり、SQLite経路は呼び出していない。今回のstateにも完了済みQA artifact bindingはなく、完了済みbaselineからの継続やconditional updateは実施していない。

同一シナリオの前回成果物と比べ、Question / UNKNOWN IDが別の意味へ割り当てられていた。現attempt内の参照は整合しているが、前回のQuestion Analysisをprevious artifactとして渡さず新規作成したため、run間のID継続性は実証できていない。これをstateful continuation成功とは扱わない。

## 実行条件

| 項目                | 条件                                                                     |
| ------------------- | ------------------------------------------------------------------------ |
| 評価開始HEAD        | `6ca543ce515a8501ad3d6a6dc542672d4a1bac68`                               |
| 作業終了HEAD        | この報告とvalidator修正を含むPR最終HEAD                                  |
| 評価Skill revision  | `6ca543ce515a8501ad3d6a6dc542672d4a1bac68`                               |
| 固定target revision | `84ce165493649550832731a60cf436f8ae29c56b`                               |
| Scenario            | `qa-training-store-checkout-payment-web-v1`                              |
| Codex CLI           | `0.165.0`                                                                |
| Model / reasoning   | `gpt-6-luna` / `max`。各subagent起動時のtool引数で明示指定、fallbackなし |
| 実行方式            | Codex subagentを逐次使用。`codex exec`は実行せず                         |
| provider build ID   | 未取得                                                                   |
| evidence root       | `.agent-eval-runs/pr17-integration-continuation-20261030-03/`            |

targetは固定revisionのtracked content 902ファイルからsanitized copyを作成し、22 Skill・215ファイルのpackageを配置した。package fingerprintは`sha256:0b39a0ec30e6ed20399b7f9fe950169beddb48ffab2f7385f89f174731c9fda2`。9個の`runtime_contract.py`複製はすべて現行source fingerprint `sha256:c17ad5878af581b5eb6d255b2a05853f82d39532479a473ae451bd6b2911dcf9`と一致した。prelaunch manifestに対するtarget検査は`unchanged=true`、変更path 0、commit数1、remoteなし。

有効なattempt前の`01`はverifier capture helperのsource path誤り、`02`はcandidate packageへeval fixtureが混入したため、いずれもAgent起動前に停止した。出力生成、runtime、graderは未実施であり評価ケース数に含めていない。`03`では正規package helperを使い、eval/test file 0件を確認してからAgentを起動した。

subagent起動tool記録には4件すべて`model=gpt-6-luna`、`reasoning_effort=max`、`fork_turns=none`が含まれる。fallbackは観測されなかったが、provider側のinference traceとbuild IDはtool surfaceから取得できず、実効backend buildまでは独立検証できていない。

Project Contextの`qa.workflow_state_root`はAgent起動前にattempt専用pathへ設定した。rootはsymlinkではなくmode `0700`で、ext4 backing mount上にあることを確認した。formal runnerの`/workspace`設定は変更していない。評価対象Agentへはtarget資料、Task、Skill packageだけを配置し、Evaluatorのrubric、expected、Judge fixture、graderは配置していない。ただしsubagentは親とworkspace権限を共有し、物理read-denialとfile-read auditは成立・確認していない。結果は実動作検証であり独立評価ではない。

## QTS統合結果

前回報告値との比較は次のとおり。前回の15 units / 62 Entitiesと今回の21 / 47は、それぞれ異なるruntime結果の実測であり、同一件数を要求しない。

| 項目                                           |                     前回報告 |                                                 今回 |
| ---------------------------------------------- | ---------------------------: | ---------------------------------------------------: |
| QA成果物                                       |                            9 |                                                    9 |
| routing rows                                   |                           22 |                                                   22 |
| executed / skipped / incomplete / blocked      |               8 / 13 / 1 / 0 |                                        9 / 9 / 3 / 1 |
| 最終Skill verifier                             |                      7 valid |                                              7 valid |
| workflow runtime                               | `valid`, `can_complete=true` |                   `unresolved`, `can_complete=false` |
| workflow runtime units / current Entities      |                      15 / 62 |                                              21 / 47 |
| coverage traceability units / current Entities |                       未報告 |                                              20 / 47 |
| artifact-index                                 |               `needs_review` | `needs_review`、13 noncompleted-routing findingsのみ |
| state initialization                           |              SQLite path拒否 |                        generic state create/read成功 |
| same-ref completed-baseline continuation       |                       未成立 |                     未成立。完了artifact bindingなし |
| COV/RISK 4件                                   |      保存出力の旧fingerprint |                         新規出力4件すべてgrader PASS |
| 独立Judge / formal runner                      |         未実施 / fail-closed |                                 未実施 / fail-closed |

### 成果物・routing

8必須成果物に`question-analysis`を加えたMarkdown 9件が揃い、`artifact-index.json`は22 routing rowsを持つ。

| routing status | 件数 | 確認                                                                                         |
| -------------- | ---: | -------------------------------------------------------------------------------------------- |
| executed       |    9 | 8必須工程とconditional question-analysis                                                     |
| reused         |    0 | なし                                                                                         |
| skipped        |    9 | test-target-inspection、test-execution、E2E 5工程、usability、WCAG。いずれもscenario scope外 |
| blocked        |    1 | TCN-003 / TCN-004のmaterialization                                                           |
| incomplete     |    3 | qa-workflow、test-case-design、coverage-analysis                                             |

最初のAgent出力では9 artifact rowsの`kind` / `scope`と対応routing scopeがscenario metadata契約に合わず、production validatorに構造問題が出た。保存済み初回indexを残したうえで、subagentが許可された9件のmetadataとrouting scopeを修正し、QAW markdown内の対応scope表記も揃えた。status、reason、artifact ID、13件のnoncompleted routeは変更していない。最終validatorは9 artifacts / 22 routesを認識し、参照欠落・path・ID・artifact-kind問題はなく、issueは13件の`noncompleted_routing`のみ。`needs_review`は正しい結果として維持した。

### Machine Runtimeとworkflow判断

最終7 Skill verifier（`spec-analysis`、`test-analysis`、`test-requirement-design`、`test-condition-design`、`test-case-design`、`coverage-analysis`、`qa-workflow`）はすべて`valid=true`、issue 0だった。`question-analysis`と`adversarial-review`にはpackage内Machine Runtime verifierがないため、同じ形式の個別verifier結果はない。

| runtime結果                             |                                                                                                                             今回 |
| --------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------: |
| workflow-runtime                        | `runtime_status=ok`、`result_status=unresolved`、`can_complete=false`、21 runtime units、47 current Entities、13 blocking issues |
| coverage traceability                   |                       `runtime_status=ok`、`result_status=unresolved`、20 runtime units、47 current Entities、12 blocking issues |
| current runtime fingerprint             |                                                                                                9 Skill複製すべて現行sourceと一致 |
| missing / extra runtime units、Entities |                                                                                                                        いずれも0 |

blocking issueは未完了model completionと、TCN-003 / TCN-004のmaterialization・downstream traceabilityの未完了である。最後のinventory shortageではOrder、Payment、Inventory、History、Customer表示の終端状態が規範仕様にない。Session開始からちょうど24時間のexpiry境界も未確定である。これらを期待値へ創作せず、影響するCoverage Item / caseに限定してblockedまたはincompleteを維持した。仕様に明示されたstale Cart Version、価格不一致、明確なPayment失敗、processing中のretry/cancel禁止、成功時のPayment / Order / Inventory更新は下流設計へ追跡した。

### Question IDの継続性

前回報告の固定シナリオでは`Q-001` / `UNK-001`が24時間expiry境界、`Q-002` / `UNK-002`が最終在庫不足だった。今回の新規作成では`Q-001` / `UNK-001`が最終在庫不足、`Q-002` / `UNK-002`が24時間境界になった。意味の不確定性は維持され、今回の仕様分析、question-analysis、下流参照間では整合するが、run間でstable IDの意味が入れ替わった。

Question Analysisの契約はprevious artifactを使う更新時に既存IDを保持する。今回のAgent入力に前回Question Analysisがなく、stateにも完了artifact bindingがないため、Skill違反とは断定できず、workflow継続入力の不足として分類する。今後同じworkflowを継続する場合は前回artifactを参照として明示し、ID履歴を保つ必要がある。この差を解消済みとは扱わない。

Adversarial Reviewは0件のfindingを報告したが、手動レビューでありMachine Runtime verifierはない。Judge未承認のため、0件を独立した意味評価のPASSとみなしていない。実画面観測やbrowser操作は固定scenarioで要求されておらず実施していない。

## Stateful workflow

前回attemptのstate-contextは`blocked`、理由は`workflow_state_database_must_be_outside_git_worktree`で、canonical state fileは存在しなかった。前回runtime記録には`workflow_ref=e07c7d1b-ea21-42cc-85d6-fc6a70ded230`があるが、そのrefのstate fileはなかった。今回の新規attemptは`workflow_ref=664cba71-c0b7-4bab-8526-c90df6fbb37c`で初期化した。旧refのstateを遡及作成して再開を装うことはしていない。今回のscenarioはWCAG formal evaluationではなく、SQLite persistenceを呼ぶ理由はない。通常workflow state helperを使い、state rootを`<attempt>/agent-visible/qts/target/.qa-eval-output/workflow-state`へ置いた。

- `qa.workflow_state_root`のparse / required-key validation: `resolved`
- 初回`create_workflow_state`: `created`、atomic file creation成功
- 別readでの再読込: `current`、同じworkflow_refとstate revision
- currentness: `current`、changed keys 0
- state: `in_progress`、固定scenario scope / revision
- conditional update / CAS: 未実行。保存revisionはCAS条件ではない
- `last_completed_qa_workflow_artifact`: 不在
- SQLite呼び出し / state更新 / baseline作成: なし
- 旧attemptの`workflow_ref`によるresume: 不可。canonical stateが元attemptに存在しない

親側でもtarget packageのproduction `artifact_graph.py`を使い、subagent報告と同じcontext / state読み取りを再確認した。初期化と同一refの再読込は成立したが、以前の完了済みbaselineからの再開は成立していない。旧attemptでstateが作成されていなかったこと、現attemptも未完了であることから、この制約は正しく未解決として残す。

## COV / RISK新規生成と保存済み46成果物

現行sourceから新規生成した4ケースは、既存graderで次の結果だった。

| Case         |       結果 |
| ------------ | ---------: |
| COV-OUT-001  | 38/38 PASS |
| COV-OUT-002  | 38/38 PASS |
| RISK-OUT-001 | 90/90 PASS |
| RISK-OUT-002 | 90/90 PASS |

`RISK-OUT-001`ではAuthority Machine Entityが入力されていないため、analysis entity生成を`invalid_input` / `blocked`のまま維持した。成果物はincompleteであり、graderは既存fixtureが要求する正しい停止状態をPASSとしている。`RISK-OUT-002`で`**false**`等のMarkdown emphasisを含む正規表現がD018で誤判定された原因に対し、deterministic validatorが完全一致するbalanced emphasis/code wrapperを認識するよう修正し、正しい値・壊れたwrapper・誤った値の回帰を追加した。期待値やseverityは変更していない。

保存済み46成果物は変更せず、現行graderで再採点した結果は41 PASS / 5 FAIL / 0例外。FAILは`COV-OUT-001/002`の旧runtime implementation fingerprint、`RISK-OUT-001/002`の旧D018および3件ずつの旧fingerprint、`TEX-OUT-002`の`TEX-D005` / `TEX-D012`。この保存済み再採点のPASS増加はSkill改善として数えていない。TEX旧成果物FAILは今回の新規生成評価対象外であり、前回の新規TEX出力15/15とは区別する。

新規COV/RISK出力は現在のruntime fingerprintで生成され、4件ともgrader例外なく全assertion PASSとなった。旧成果物のfingerprintを書き換えず、新旧結果を別々に保持した。

## 変更・テスト

| 対象                                                              | 原因と対応                                                                                                                           |
| ----------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| `skills/test-analysis/evals/deterministic/validator.py`           | Markdownで強調・code表記された正規gate値を文字どおり比較していたfalse negativeを修正。balanced wrapperを除去してから値を厳密一致比較 |
| `tests/skills/evals/deterministic/test_false_pass_regressions.py` | bold/code/italicの正規値を受理し、unbalanced wrapperと誤った値を拒否する回帰を追加                                                   |

この統合評価ではSkill、QTS product source/spec/test、grader expected、artifact-index validator、runtime helperを変更していない。indexのmetadata修正はGit管理外の生成物に限定した。

| 検証                              | 結果                                                                       |
| --------------------------------- | -------------------------------------------------------------------------- |
| false-pass regressions            | 58 tests PASS                                                              |
| workflow runtime                  | 13 tests PASS                                                              |
| qa-workflow runtime               | 14 tests PASS                                                              |
| artifact graph workflow tests     | 7 tests PASS                                                               |
| qa-training-store evaluator tests | 13 tests PASS                                                              |
| runtime contract identity         | 56 tests PASS                                                              |
| semantic repository structure     | 1 test PASS                                                                |
| semantic runtime portability      | 1 test PASS                                                                |
| semantic datasets                 | 2 tests PASS                                                               |
| 46 case current-source regrade    | 46件、missing 0、41 PASS / 5 FAIL / 0 exception                            |
| Python compileall                 | `python -m compileall -q scripts skills tests` PASS                        |
| dprint                            | `dprint fmt`後、対象reportの`dprint check` PASS                            |
| `git diff --check`                | PASS                                                                       |
| Ruff                              | 実行環境にRuff executableなし。依存導入はしていない                        |
| Full artifact-graph suite         | 40/43 PASS。3 SQLite path testはmanaged sandboxの`/tmp/.git`検出により失敗 |
| GitHub Actions                    | 最終push HEADで5 workflowを確認予定                                        |

Full artifact-graph suiteの3件はtemporary rootの親にあるmanaged sandboxの`/tmp/.git`をGit worktree境界として検出した環境制約である。今回のQTS評価には不要なSQLite経路を使っていない。これをproduction defectと混同していない。

## 正式評価の未達

- parent / subagent間の物理read-denialと実ファイルread audit
- 認証refresh persistence、process concurrencyに基づくformal runner受入
- formal `codex exec`実行
- Judge fixture 11件の承認（前回状態: human review待ち9、deterministic review待ち2）と独立Judge
- previous artifactを使ったQuestion / UNKNOWN stable IDの継続確認
- `qa-workflow`未完了状態のcompleted baseline作成とconditional state update
- 仕様未確定のinventory shortage終端状態と24時間expiry等号境界

これらを正式な独立評価成功へ読み替えていない。認証store、sandbox、Hook、execpolicy、Judge承認状態は変更していない。`codex exec`の試行も行っていない。

## 証拠

raw evidenceはGit管理外の`.agent-eval-runs/pr17-integration-continuation-20261030-03/`に保持する。case成果物とgrader結果、runtime request/result、旧46ケース再採点、初回・修正版artifact-index、state初期化・再読込、target unchanged manifest、subagent起動条件は`evidence-index.md`、`evaluator-private/execution-record.json`、`execution-record-addendum-current-cov-risk.json`、`setup-attempts.json`を参照。秘密情報は記録していない。
