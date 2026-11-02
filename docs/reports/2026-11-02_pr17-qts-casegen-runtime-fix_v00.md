# PR #17 QTS case-generation runtime修正・品質検証

## 結論

sanitized targetからのhelper起動契約、typed inputの説明、artifact-indexの公開構造検査を追加し、修正後の条件で2つの開発用実Agent attemptを実行した。両attemptで8種類の必須QA成果物とQuestion Analysisが生成され、artifact-indexの構造検査とtarget integrityを確認できた。一方、両attemptともQA workflow runtimeは `can_complete=false` であり、attempt-02ではTest Condition Designの必須materializationが欠けてfinal verifierもinvalidだった。従って、統合QA workflowの完了や品質PASSは確認していない。

固定仕様にない最終在庫不足の結果を確定仕様へ昇格する問題は今回の2成果物では再現しなかった。TEST-SUCCESSなしの成功期待も再現しなかったが、attempt-01では成功条件に必要な在庫減算の期待が欠け、attempt-02で補われた。24時間境界の質問とexact-boundary条件はattempt間で揺れた。これらは単発または不一致の結果で、Skillの因果欠陥として再現性を確定できないため、意味品質を狙ったSkill修正候補は作成していない。

## 固定条件と証拠

| 項目                                         | 値                                                                                                                                                                 |
| -------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 開始HEAD                                     | `5f002a93a75c73a272aeca2785172df7f23afbd4`                                                                                                                         |
| Evaluator/Skill package revision             | `5f002a93a75c73a272aeca2785172df7f23afbd4` と同HEADの作業差分                                                                                                      |
| 作業差分fingerprint                          | `sha256:826d084e3450a8efdb827e48696ff2ff02cf6985cd67c27216f2e0e08a942676`                                                                                          |
| Skill package fingerprint                    | `sha256:4c675107f501d82e10f70b300b24956970a6ede9f55230dc36ef845ecb48bfd7`                                                                                          |
| Prompt fingerprint                           | `sha256:d32c5d5fda67c52edd4f3b5d356da5be93a86a45d485d7c3f4db680066b10333`                                                                                          |
| Scenario / task fingerprint                  | scenario `sha256:b9aedc1b00bc2bcdf3a91735b008f9e89ecb403482f4ca84a20b4648180a8a5c`; task `sha256:a40343bce1d62d727c236cdc759d125c1b77f7375b7786d9af7e0a65bc938e98` |
| 固定QTS source                               | `84ce165493649550832731a60cf436f8ae29c56b`、clean checkout                                                                                                         |
| Requested agent config                       | `gpt-6-luna / max / fork_turns=none`                                                                                                                               |
| Effective model / reasoning / provider build | 未検証。実効telemetryは取得できなかった                                                                                                                            |

attemptごとに異なるsynthetic target Git baselineを作成した（attempt-01 `7f88af9c3813e6139d1d3e81139cfa1e59ec3048`、attempt-02 `d3fbcb36ef46e1bcb872e7547598a22a88296bc9`）。両targetのGit root、合成HEAD、remoteなし、固定source由来manifest、生成後integrityは記録済みで、2件とも `unchanged=true` と `synthetic_baseline_matches=true`。固定source SHAとsynthetic HEADは別物として扱った。

全raw artifact、runtime request/result、attempt別launch/preparation、parent validationとfile SHA manifestはGit管理外の `.agent-eval-runs/pr17-qts-casegen-runtime-fix-20261102-r1/` に保存した。親側の整理とAgent summaryとの照合は同rootの `evaluator-private/evidence-index.md` と `evaluator-private/parent-review.md` を参照。Agent summaryの自己申告と不一致がある場合は、成果物本文・validator出力を正本として判定した。

## 実行経路の修正

### Test Case Design helper

`case_structure.py` はJSONをstdinから受け取るgeneratorで、`--help`は実装していない。前回の誤った作業directoryからのhelp呼出しを避けるため、[test-case-design SKILL.md](../../skills/test-case-design/SKILL.md) にsanitized target rootからの正規起動、正規request構造、runtime generatorと最終成果物の `verify_runtime_evidence` の役割分担を記載した。回帰テストは一時sanitized target rootを作り、記載したコマンド相当でJSON requestを実行し、`ok/ready`とbytecode非生成を検証する。

今回のpreflightでは同じ起動経路が通り、実Agent attemptでも誤った `--help` / cwd呼出しは再発しなかった。attempt内で発生した不正なgenerator requestは別問題として記録し、成功するまでの再試行で隠していない。

### Typed value

[test-condition-design SKILL.md](../../skills/test-condition-design/SKILL.md) にruntime generatorのtyped valueを `{ "type": "...", "value": ... }` と明記した。raw scalarをtyped valueへ黙って変換しない既存runtime契約を維持し、scalarを渡した場合に `invalid_input / blocked` となる回帰テストを追加した。preflightではtyped decision-table requestが `ok/ready` となった。

今回の生成では、attempt-02に `scope_key=null` など複数の初回request不備があり、後続の修正済みrequestと最終成果物を区別して保存した。これらはraw-scalar契約の不具合ではなく、初回model-generated requestの入力不適合である。

### artifact-index構造検査

sanitized targetに公開用の標準ライブラリcheckerと、scenarioにすでに公開されたartifact metadata・サイズ制限だけから作るcontractを配置した。Agentはartifact-indexを保存後にschema、ID、path、required artifact登録、routing参照、未登録Markdownを自己検査できる。checkerは意味的routingや成果物内容を判定せず、Evaluator-onlyのexpected、rubric、Reference、Judge fixtureを含めない。promptとtarget instructionsにもこの境界を明記した。

2 attemptとも公開checkerはvalid（9 artifacts、attempt-01は17 routing rows、attempt-02は16 rows）。一方、既存Evaluatorの `validate_artifact_index()` は両方とも `needs_review` を維持した。理由はincomplete / skipped routingであり、これは構造エラーではない。statusの意味を公開checkerや親処理でPASSへ書き換えていない。実行記録・runtime記録は9件の正規QA artifactへ混入していない。

agent-visible targetのfilename-only確認では `expected.json`、`rubric.json`、`judge-fixtures.json`、grader/Judge fixture名の一致は0件だった。これは共有workspace全体の物理read-denialを証明しない。

## 2 attemptの結果

| 項目                                               |                              attempt-01 |                                          attempt-02 |
| -------------------------------------------------- | --------------------------------------: | --------------------------------------------------: |
| 正規QA Markdown                                    |                                       9 |                                                   9 |
| routing rows                                       |                                      17 |                                                  16 |
| routing status                                     |   executed 6 / incomplete 3 / skipped 8 |               executed 4 / incomplete 5 / skipped 7 |
| 公開構造checker                                    |                                   valid |                                               valid |
| Evaluator `artifact-index`                         |                          `needs_review` |                                      `needs_review` |
| 生成ケース                                         |                                      18 |                                                  18 |
| final Test Condition Design verifier               |                                   valid | invalid: `TCN-003` materialization runtime unit欠落 |
| QA workflow runtime                                |    valid evidence、`can_complete=false` |                valid evidence、`can_complete=false` |
| target integrity / bytecode / secret-pattern check | unchanged、pycacheなし、pattern hitなし |             unchanged、pycacheなし、pattern hitなし |

両attemptのEvaluator固定条件、agent-visible資料、入力・生成物との対応はevidence indexと各attempt SHA manifestに保存した。共有workspaceから起動したため、expected/grader/Judge fixtureへの物理的read-denialは証明していない。したがって結果は開発用実動作評価であり、正式な独立評価ではない。

### Runtime evidence

Agentが実行したSkill-local runtime captureを固定sourceの現在のruntime contractでローカルreplayし、全captureのsemantic fieldsが保存済み結果と一致した（attempt-01 10件、attempt-02 8件、mismatch 0）。attempt-01のcapture verdictはvalid 9 / invalid 1、attempt-02はvalid 5 / invalid 3。無効な初回requestを含め、全結果を保存している。attempt-02のfinal Test Condition Design verifierは `test-condition-design::artifact:materialize_coverage:TCN-003` が欠落したためinvalidであり、正当な仕様blockedとは区別した。

このreplayはisolated production verifierの固定Docker replayではない。環境にDocker CLIがなく、Docker契約のproduction replayは未実施である。`workflow_runtime`のevidenceは両attemptでvalidだが、coverage/traceabilityに未解決があり、`can_complete=false` を維持した。

## QTS品質所見

### 最終在庫不足の仕様創作

固定sourceではAC-CHECKOUT-003が整合確認を要求する一方、最終在庫不足時のOrder / Payment / Inventory / Historyの詳細状態は規定されていない。attempt-01は独立質問Q-002、attempt-02はQ-001として扱い、両方とも期待状態の確定を保留した。今回の2成果物では、前回所見のように在庫不足状態を確定したSPECへ昇格する挙動は再現しなかった。Q IDはattempt間で異なるが、各attempt内の意味は一貫している。

### Payment成功条件・TC-016相当

旧所見の「TEST-SUCCESSなしで成功を期待」は今回再現しなかった。両attemptとも成功経路にTEST-SUCCESSとInventory再検証を含めた。ただしattempt-01のTC-016はPayment succeeded / Order paidのみを期待し、固定仕様にあるInventory decrementを期待結果へ含めていない。attempt-02の成功TC-012はTEST-SUCCESS、十分なInventory、Payment succeeded、Order paid、Inventory decrementを対応付けた。よってケース固有の不完全さは観測したが、2 attemptで結果が一致せず、特定Skillの再現性ある欠陥とは確定していない。独立の修正候補を作らない。

### TCN blocked範囲と24時間境界

attempt-01はQuestion Analysisで24時間境界と在庫不足を分けて質問し、Paymentの確定経路を別条件として扱った。attempt-02は在庫不足だけをQuestionとして記録し、SessionのTCN/CIではちょうど24時間にexpiredと判定するTC-016を生成した。固定仕様は「24時間でexpired」とするが、ちょうど境界の包含規則は定めていないため、このTC期待を正当化できない。境界質問・期待値はattempt間で揺れ、attempt-02ではTest Condition DesignのTCN-003 materializationも欠けてfinal verifierがinvalidである。従って過剰blockedの完全解消、または安定した質問抽出を立証していない。既存Skill記述から原因を単一箇所へ帰属できないため、追加の意味修正は保留する。

照合した正本は固定targetの `docs/spec/README.md`、`docs/spec/features/checkout-and-payment.md`、`docs/spec/state-and-scenarios.md`、`docs/spec/features/orders.md`、`docs/spec/features/admin-inventory.md`、`docs/spec/unresolved-specifications.md`。最終在庫不足の具体的な終端値と24時間ちょうどの包含は、これらに確定規則がない。

### Attempt summaryとroutingの扱い

保存されたAgent final summaryは両方で24時間境界質問がないと記載していたが、attempt-01のQuestion Analysis本文にはQ-001として質問が存在する。attempt-02は質問を持たない。報告では要約の自己申告を採用せず、artifact本文、runtime capture、Evaluator出力から事実を取り直した。全routingの意味的妥当性はJudge承認前であり、`needs_review`を最終品質判定として解釈しない。

## 修正採否

今回反映するのは実行契約とagent-visible構造自己検査の修正だけである。QTS製品source、仕様、Seed/Reset、製品テスト、expected、grader、Judge fixtureは変更していない。品質所見の意味修正は、同じ問題の再現とSkill起因の因果が不足するため作成・採用していない。baseline/candidateの品質改善比較や独立回帰も未実施であり、今回の2 attemptをSkill品質の改善証拠とは扱わない。

今回のprompt、public checker、Skill実行ガイダンスはr5/r6以降に変更された。今回の2 attemptは新しい評価条件のbaselineであり、r5/r6と厳密な同条件比較ではない。

## 検証

- `tests/skills/runtime` unittest: 382 passed.
- Agent evaluator unittest: 174 tests、2 skipped、残り成功。
- `tests/skills/evals/agent` unittest: 4 passed.
- `compileall`: passed.
- 対象Python / Markdownのdprint check: passed。
- `git diff --check`: passed。
- RuffはローカルPython環境に未導入。GitHub Code Quality CIで確認する。
- Docker CLI不在のためproduction verifier replayは未実施。

## 正式受入の残条件

- WSL2 formal runnerは認証refresh永続化と非協調process競合が未解決のためfail-closedを維持する。
- QTS Judge fixtureは11件とも未承認。必要な人間レビューと決定論的レビューを完了していない。
- 実効model/reasoning/build telemetry、Evaluator-only情報の物理read-denialは今回証明していない。
- 固定Docker contractによるproduction verifier replay、formal repeat評価、`improve.py`のlive repair flowは未実施。
- QTS workflow自体は未完了であり、未確定在庫不足・期限境界を仕様回答なしに解決しない。

これらは開発用評価の完了範囲とは別の正式受入条件である。認証・隔離のfail-closed、未承認Judge、QTSの未完了判断は変更していない。
