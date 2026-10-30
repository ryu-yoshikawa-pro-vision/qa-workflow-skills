# PR #17 Stateful workflow継続・baseline再利用検証

## 結論

前回のQTS attemptを同じ`workflow_ref`で読み直し、Project Contextとstate revisionのcurrentnessを確認できました。`question_ids.py`のupdate契約を通じ、保存済みQuestion AnalysisのQ/UNKNOWN IDと意味を維持しました。一方、QTS stateにはcompleted artifact bindingがなく、変更時のnative CASも確認できないため、下流artifactをbaselineとして再利用せず、stateも更新しませんでした。workflowは正しく未完了のままです。

完了済みbaselineの保存・exact refetch・再利用判断は、既存のruntime test fixtureから作った独立の合成fixtureで確認しました。この結果はQTSの製品QA品質を示しません。

## 実行条件と証拠

| 項目                             | 値                                                                                                                                                           |
| -------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 開始HEAD                         | `648b1d03002b61dc5a610f2c02567c9954b3127d`                                                                                                                   |
| 回帰testを含む検証終了HEAD       | `3b54e82fbb12952c761310f1032992591e44d2e3`                                                                                                                   |
| 開始branch                       | `feat/agent-eval-runner`のPR headと同一内容（ローカル作業branch上で検証）                                                                                    |
| 対象scenario / target            | `qa-training-store-checkout-payment-web-v1` / `84ce165493649550832731a60cf436f8ae29c56b`                                                                     |
| 実Agent方式                      | Codexサブエージェント。親の起動記録に`model=gpt-6-luna`、`reasoning_effort=max`、`fork_turns=none`を明示                                                     |
| Agent実行                        | QTS継続1回、baseline再利用の合成fixture 2回（初回はcurrentness資料不足を検出、2回目はfixtureを正しく準備して実行）                                           |
| provider build / inference trace | 未取得。サブエージェント起動設定以外のprovider実効記録は取得できない                                                                                         |
| Codex CLI / `codex exec`         | 今回はサブエージェント方式で、CLI processは起動していない。PATH上のWindows npm wrapperはLinux optional dependency不足で失敗し、CLI versionを確認できなかった |
| 評価証拠                         | `.agent-eval-runs/pr17-stateful-continuation-20261031-01/`（Git管理外）                                                                                      |
| formal isolation                 | 未成立。親とAgentはworkspace権限を共有し、物理read-denialとfile-read auditは確認していない                                                                   |

raw Agent成果物と実行記録は上記attempt内に保管し、repositoryへ追加していません。Agent-visibleな各rootにはgrader、expected、rubric、Judge fixtureを配置していません。

## A. 未完了QTS workflowの継続

元attempt`.agent-eval-runs/pr17-integration-continuation-20261030-03/`を変更せずに読み、今回の別attemptへ必要なartifactだけを履歴入力として複製しました。実際のcanonical stateは次のとおりです。

- `workflow_ref`: `664cba71-c0b7-4bab-8526-c90df6fbb37c`
- target revision / scope: `84ce165493649550832731a60cf436f8ae29c56b` / `qa-training-store-checkout-payment-web-v1`
- state: `in_progress`、revision `sha256:d9a39913bf994970b5a6fe3c2d71a5e33fb68a5dbe89d1542cab577f4e0f5bee`
- stateに`last_completed_qa_workflow_artifact` bindingはありません。
- 初回attemptに記録されたProject Context keyは`current`でした。実行前後のstate SHA-256は同じで、元stateは変更されていません。

継続Agentは`create_workflow_state()`ではなく既存の`read_workflow_state()`を使い、同じcanonical refとrevisionを読みました。前回Question Analysisを`question_ids.py`の`operation=materialize`、`artifact_mode=update`へprevious artifactとして渡し、helper resultは`valid=true`、`issues=[]`、`allocated_ids=[]`でした。成果物hashも前回と一致し、次の意味対応を維持しています。

| ID                  | 保存済み成果物で確認した意味                                              | 状態         |
| ------------------- | ------------------------------------------------------------------------- | ------------ |
| `Q-001` / `UNK-001` | 最終在庫不足時のPayment / Order / Session / Inventory / Historyの終端状態 | 未解決を維持 |
| `Q-002` / `UNK-002` | Checkout Sessionがちょうど24時間となるexpiry境界                          | 未解決を維持 |

前の作業指示に書かれたQ-001 / Q-002の説明順とは保存済みQuestion Analysisの対応が逆でした。今回Agentは実ファイルの意味に従い、番号を入れ替えずに維持しました。

下流のtest-analysis、TR、TCN、TC、coverage、adversarial reviewは新しいruntime evidenceで再検証していません。completed bindingのないhistorical copyを`reused`とは表示していません。入力に新しい決定事項もないため、QTSに対する変更影響伝播は発生していません。既存の`test_workflow_runtime` stale-fingerprint回帰testは今回もPASSしましたが、これは実Agentによる上流変更runではありません。

継続Agentの`artifact-index.json`を既存`validate_artifact_index()`で検査した結果は`needs_review`でした。実測は10 artifact rows、24 routing rows（executed 3、blocked 4、incomplete 8、skipped 9）です。診断には次が含まれます。

- scenarioにない`qa-workflow / workflow-continuation-result` artifact kind
- 必須の`qa-workflow`と`spec-analysis` routingでscopeが正規の`checkout-payment-web`と不一致
- 必須artifactと該当routing row間のlink不足
- blocked / incomplete / scope外skip。これらはvalidatorがreviewを要求する既存契約どおりです。

したがって、QTSの成果物生成やroutingを全体PASSとは扱いません。workflow最終判断はincompleteのままで、追加仕様なしに状態をcompleteへ変えていません。Agent成果物は`agent-visible/qts/target/.qa-eval-output/`、helper request/resultはその`.runtime-evidence/`にあります。

## B. 完了済みbaselineの保存・再取得・再利用

QTSの未完了stateからbaselineを作らず、既存`tests/skills/runtime/test_workflow_runtime.py`由来の1 scope / 5 Entity / 3 runtime unit fixtureを使用しました。production `verify_runtime_evidence`はvalid、`workflow_runtime`は`runtime_status=ok`、`result_status=ready`、`can_complete=true`、issue 0でした。これはテストfixtureのMachine Runtime品質だけを確認するものです。

既存の`commit_qa_workflow_baseline_local()`で、immutable artifactを保存し、state bindingを更新して再読込しました。

- artifact ref: `qa-workflow-local:00000000-0000-4000-8000-000000000016`
- revision / SHA-256: `sha256:ddaf1cee9485f141473264c7f17376f2046962f9147a774cba8d02dbe0853ed2`
- state revision: `sha256:a1cbd70475e9ec9326901634353c952c0866cf0e47b03fdb79fe78743cc8f011`
- exact historical refetchは`current`で、本文とcandidate bytes/hashが一致しました。
- 同一要求のretryは`committed_replay`。wrong workflow binding、wrong revision、artifact bytes改変は拒否されました。
- v2 Agent attemptではbaseline前にProject Contextと使用snapshotを固定しました。context比較、state read、exact artifact refetchがすべてcurrentで、workflow_ref / scope / source revisionとbindingが一致しました。5 Entityと3 runtime unitすべてのfreshnessもcurrentでした。
- Agentはこのfixtureに限りstable IDを維持して再利用し、generatorの再実行は不要と判断しました。Agent実行後もstateとimmutable artifactのhashは不変でした。

初回の合成attemptはProject Context snapshotと現在source revisionの比較入力が不足し、Agentはhistorical artifactの存在だけからcurrent reuseを確定しませんでした。その成果物も保持し、後付けの履歴として使っていません。v2でbaseline作成前にsnapshotを記録した上で再評価しています。

これは完了済みfixtureに対するhelperと実Agentの再利用確認です。QTSの2 UNKNOWN、未完了downstream、QTS baseline bindingの欠如を解消する結果ではありません。

## 修正と回帰

production helperの不具合は確認されませんでした。既存baseline helperはimmutable artifact、正確なrevision再読込、idempotent retry、競合保護を実装しており、一般的な未完了state更新にはnative conditional writeがないため`state_update_decision()`どおりblockedにするのが正しい状態です。read-compare-unconditional-writeは追加していません。

`tests/skills/runtime/test_qa_workflow_baseline.py`へ次の2件を追加しました。

- wrong workflowのartifact refを指定したhistorical readを`historical_artifact_binding_invalid`で拒否する。
- 保存後にartifact bytesを改変した場合、revision mismatchで拒否する。

既存のexpected revision conflict、2 process競合、symlink拒否、idempotent retry、CAS非対応providerのfail-closed testも含め、baseline test moduleは11件PASSでした。Skill、runtime実装、fixtureの期待値は変更していません。

## ローカル検証

| 検証                                                      | 結果                                  |
| --------------------------------------------------------- | ------------------------------------- |
| `tests.skills.runtime.test_qa_workflow_baseline`          | 11 PASS                               |
| `tests.skills.runtime.test_question_ids`                  | 5 PASS                                |
| `tests.skills.runtime.test_workflow_runtime`              | 13 PASS                               |
| `tests.skills.runtime.test_qa_workflow_runtime`           | 14 PASS                               |
| `tests.skills.runtime.test_downstream_state`              | 20 PASS                               |
| `scripts.skills.evals.agent.tests.test_qa_training_store` | 13 PASS                               |
| `compileall`（変更test）                                  | PASS                                  |
| `scripts/format_tracked.py check`                         | PASS（Ruffとdprint、tracked targets） |
| `git diff --check`                                        | PASS                                  |

## GitHub Actions

報告書を含むcommit `5234e3899d6c4e28bb3f10d0dbbc0c995c56a599`のPR merge refで、既存5 workflowはすべてsuccessでした。

| Workflow                            | Run                                                                                                    |
| ----------------------------------- | ------------------------------------------------------------------------------------------------------ |
| Code Quality                        | [41105828874](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/actions/runs/41105828874) |
| Validate Agent Skills               | [41105828746](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/actions/runs/41105828746) |
| Validate Deterministic Output Evals | [41105828900](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/actions/runs/41105828900) |
| Validate Semantic Output Evals      | [41105829047](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/actions/runs/41105829047) |
| Codex Harness                       | [41105828898](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/actions/runs/41105828898) |

この記録を加えた後のreport-only commitでも最終PR HEADのCIを再確認します。

## 未達・正式評価の残条件

- QTS in-progress stateへの安全なCAS更新APIはなく、今回はread-only継続に限定しました。native conditional writeなしでのstate update、QTS downstreamの保存・再開、QTSの完了baseline再利用は未成立です。
- QTSに実際の上流変更入力がないため、QTS Agentでの変更伝播runは未実施です。依存fingerprintの変更によるstale伝播は既存unit testで検証しています。
- `codex exec`、独立Judge、formal runnerは今回実行していません。Judge fixtureの承認状態を変更していません。
- subagentは親と同じworkspace権限を持ち、expected / grader / Judge dataへの物理read-denialやread auditは未検証です。provider build IDも未取得です。今回の結果はすべて実動作または合成fixture検証で、正式な独立評価ではありません。
- 固定Linux Codex CLIの実行versionを今回のsubagent sessionから取得できませんでした。`codex exec`に関する認証・隔離条件の再調査や変更は行っていません。

## 証拠索引

- 全attempt: `.agent-eval-runs/pr17-stateful-continuation-20261031-01/evidence-index.md`
- QTS継続成果物: `.agent-eval-runs/pr17-stateful-continuation-20261031-01/agent-visible/qts/target/.qa-eval-output/`
- 合成baseline v1/v2とAgent判断: `.agent-eval-runs/pr17-stateful-continuation-20261031-01/agent-visible/baseline-resume*/.qa-eval-output/reuse-decision.md`
- evaluator-side実行・hash検査: `.agent-eval-runs/pr17-stateful-continuation-20261031-01/evaluator-private/`
