# PR #17 残存不具合・未使用入力回帰・統合評価

## 1. 対象と実行条件

- Repository: `ryu-yoshikawa-pro-vision/qa-workflow-skills`
- PR: #17、base `main`、branch `feat/agent-eval-runner`、作業開始HEAD `fc5192282d76f48e4bf46aa9c2fc92f1b06a096a`。
- 実行対象の製品仕様は `qa-training-store` revision `84ce165493649550832731a60cf436f8ae29c56b`。
- Candidate Skill sourceは同じ開始HEAD上の今回のdirty working-tree overlay。Agentへ渡すpackageは22 Skillsで、評価・fixture・expectedデータを含めない。
- 実Agent方式は逐次起動したCodex subagent。各起動に `gpt-6-luna` / `max` を明示した。親Codex session記録のCLI versionは `0.165.0`。起動設定からモデル・推論設定を確認し、Agentの自己申告は設定の証拠に使用していない。Provider serving build IDは取得できない。
- `codex exec`および正式agent runnerは起動していない。既知の認証process concurrency / refresh persistence受入条件は変更・再調査せず、正式runnerはfail-closedのままとした。認証情報、sandbox、Hook、execpolicyは変更していない。
- 実験証拠はGit管理外の `.agent-eval-runs/pr17-followup-independent-qts-20261030-01/` に保存する。raw output、grader証拠、evaluator-private manifestはcommit・PR artifactへ含めない。
- subagentと親は同一workspace権限を持つ。評価用expectedへの物理的read denialおよびfile-read auditはない。よって全subagent結果は**実動作検証**であり、正式な独立評価ではない。

## 2. TEX-OUT-002

### 修正要否

元の保存成果物は `TEX-D005` と `TEX-D012` がFAILし、13/15 assertion PASSだった。元成果物を修正後graderで再採点した結果も13/15で同じ2 assertionがFAILした。

Skill、guidance、templateには、source revisionをTC snapshotやsource TC IDと区別すること、TC本文を復元できなければsnapshotを作らないこと、未実行slotを結果表と集計へ反映することが既に定義されている。期待値変更、grader緩和、指示の重複追加は行わなかった。

### 新規Agent再生成

新しい `gpt-6-luna / max` Agentが同じEval Inputから成果物を再生成した。既存graderは **15/15 PASS**、`TEX-D005` / `TEX-D012` を含む全assertionがPASS。

新規出力はsource revision `tcset-r10`を記録し、前回TC本文や実行環境のない状態でsnapshotを創作しなかった。未実行slot `input-001`を`未開始` / `未実行`として扱い、不足情報・再開条件を記録し、結果表と集計を一致させた。runtime操作、実行結果、cleanup結果は生成していない。前回FAILはモデル出力のばらつきであり、再現する契約不足は確認できなかったためSkill変更は不要と判断した。

既存別ケースの回帰として `TEX-OUT-001` は15/15 PASSだった。元入力・Agent出力に含まれるcredential-like文字列は、報告書へ転記せず、再表示しなかった。

## 3. 未使用入力による回帰

既存46 Eval Inputと異なる5件のtask-local inputを使用した。ケース作成時にexpected/checksを固定し、生成後に変更していない。いずれも親workspaceとの物理的隔離を証明できないため、held-out **実動作検証**としてのみ扱う。

| Case                 | Skill / 目的                                                                | 結果                                                                        | 判定                                                           |
| -------------------- | --------------------------------------------------------------------------- | --------------------------------------------------------------------------- | -------------------------------------------------------------- |
| `IND-SPEC-001`       | `spec-analysis`、Authority優先順位、enum、未解決境界                        | 7観点を確認。仕様上の期限競合を未解決のまま保持                             | 手動レビューpass（Machine EntityはSkill runtime evidenceあり） |
| `IND-TCN-ORDERS-001` | `test-condition-design`、複数根拠の追跡、状態遷移、blocked target           | 7観点を確認。transaction failure時の結果を創作せずblocked                   | 手動レビューpass、runtime verifier `valid=true`                |
| `IND-TEX-001`        | `test-execution`、source identity保持、安全な事前停止                       | 6観点を確認。endpoint/browser capabilityなしで未開始に留めた                | 手動レビューpass。製品実行は未実施                             |
| `IND-TR-ORDER-001`   | `test-requirement-design`、複数仕様・AC・リスク入力                         | 初回47/48、`TR-D005`で優先度enumに説明文を付加                              | 6/7内容レビューpass。enum欄契約違反を確認                      |
| `IND-TR-ROLE-001`    | `test-requirement-design`、role boundary、task-local Authority、AC/riskなし | 7/7内容レビューpass。runtime `ok/ready`、5 Entity、最終証拠検証`valid=true` | held-out inputでpass                                           |

`IND-TR-ORDER-001`の初回FAILから、正規enum `高/中/低`と説明・暫定性を`備考`へ分ける明示的根拠がguidance/templateにないことを確認し、両文書だけを修正した。同じ入力での再生成はheld-out caseとして数えない。再生成物はenum違反を直した一方、正規templateを維持せず、validatorの`TR-D011`（46/48中1件）と`TR-D009`（1件）がFAILした。`SKILL.md`にはtemplate利用指示が既にあり、同じ入力の出力ばらつきだけを根拠に追加の重複指示やgrader緩和は行わなかった。

修正後、別入力の`IND-TR-ROLE-001`で優先度enum・備考分離・5件のstable TR IDとAuthority参照が正規runtime verifierを通過した。これはこの特定契約の改善を支持する1件の運用証拠であり、一般化や正式受入の証拠ではない。

## 4. qa-training-store統合評価

### 固定条件

- Scenario: `qa-training-store-checkout-payment-web-v1`
- Target: `84ce165493649550832731a60cf436f8ae29c56b`
- Platform: Web、Checkout / Payment
- Agentが参照する対象: 固定targetのtask、最小評価用Project Context、22 Skills、対象scopeの規範仕様、runtime capture helper。
- Evaluator-privateのrubric、expected、Judge fixtures、他attemptの成果物をtargetへ配置しない。Targetの元作業tree・製品仕様・Product Code/Testは変更しない。

### Attempt 05

`attempt-05-postfix/`は8必須Markdownとconditional question-analysis、およびartifact-indexを生成した。しかしcandidate packageは9個のbyte-identical runtime contractを同期する前のsourceで、Agentは各Skill verifierおよび`qa-workflow` workflow runtimeを呼び出さなかった。`validate_artifact_index()`は9 artifact / 9 routingのpathとmetadataを認識したが、6工程が`incomplete`、`qa-workflow`が`blocked`となり`needs_review`。Runtime evidenceは存在しない。これは手動設計候補であり、統合workflow完了とは判定しない。

この直接subagent環境にrunnerの`/workspace` mountがなく、評価用Project Contextの `/workspace/.qa-eval-output/workflow-state` が解決できなかった。targetを再作成し、別attemptでrunner外のlocal pathを使う評価用Project Contextを既存parserへ通してから起動することにした。

### Attempt 07

修正後の準備確認で、`.qa-eval-input/task.md`がないこと、およびcandidate Skillが`.agents/skills/skills/<skill>`へ二重配置され、runtime capture helperの参照先と不一致であることを検出した。Skill生成・runtime評価は開始せず、このattemptはsetup failureとして保存した。

### Attempt 08

`attempt-08-local-root/`では`target_workspace.py`の既存sanitizationを使い、22 Skillsを`.agents/skills/<skill>`へ配置した。scenarioの`task.md`だけを`.qa-eval-input/`へ追加し、固定Artifact metadata対応を評価用AGENTSへ渡した。runner mountのない直接実行を明示するため、評価用Project Contextのstate rootを同じtargetの`.qa-eval-output/workflow-state`へ設定し、既存`artifact_graph.parse_project_context()`およびrequired-key/path resolverが受理することをAgent起動前に確認した。これはevaluation configurationだけのlocal実行条件であり、正式runnerの`/workspace`契約を変更していない。

Attempt 08の最終成果物、artifact-index判定、各runtime verifierの結果、`qa-workflow workflow_runtime`の`valid`と`payload.can_complete`はAgent完了後に本節とevidence indexへ記録する。未実行の工程は完了扱いしない。

Agentは9個の成果物（8必須Skill成果物と条件付き`question-analysis`）を生成し、`artifact-index.json`へ9 artifacts / 22 routing rowsを記録した。routing内訳は`executed=8`、`skipped=13`、`incomplete=1`、`blocked=0`、`reused=0`。7つの最終Skill verifier capture（6工程と`qa-workflow`）はすべて`captured`かつ`valid=true`だった。これとは別のworkflow-runtime captureも有効だった。最終case-structure結果は13ケース / 14 Entity、`ok/ready`、issues 0。Coverageのtraceabilityは14 runtime units / 62 Entity、`ok/ready`、issues 0だった。最終workflow runtimeは`runtime_status=ok`、`result_status=ready`、`payload.can_complete=true`、issues 0、15 runtime units / 62 Entity。これらは構造・runtime契約の検証結果であり、QA内容が完了したことを示さない。

親Agentが対象attemptの7 Skill `runtime_contract.py` verifier要求をローカルで再実行し、保存済み最終結果と7/7で完全一致するJSONを確認した。workflow runtimeの重複3要求も保存済み結果と一致した。Artifact-index validatorは9 artifacts / 22 routing rowsを認識し、path・artifact ID・参照の構造問題はなかったが、13件の意図的skipと1件のincompleteにより`needs_review`を返した。skipはE2E/browser、実行、UI usability、regression等の今回scope外工程で、incompleteは最終`qa-workflow`判断である。このstatusをPASSへ読み替えていない。

実Agentは、checkout expiryの境界値`Q-001`、在庫不足時の最終Order / Payment / Inventory / History / UI状態`Q-002`、実画面観測を要する`TCN-005`を未確定またはblockedのまま保持した。Adversarial reviewは最終修正後の静的レビューで指摘0件だったが、これらの未観測条件を解決したわけではない。TC-004/012（価格変更と未変更）およびTC-010/013（OperatorとCustomerの権限境界）を分割した後、case-structure runtimeで再検証した。TC-005/006とTCN-002-CI03/CI02の参照入替も修正し、final artifact fingerprint `sha256:465a426c449e3c6c11560839b534d0b85d96023c78d778530ebe9619198a2b53`に対してcase-structure検証が有効となった。これらはAgent出力内の修正で、製品コードやQA仕様を変更していない。

ただし、Project Contextのstate rootは`.qa-eval-output/workflow-state`でGit worktree内にあり、stateful context helperは`workflow_state_database_must_be_outside_git_worktree`で拒否した。一般workflow runtimeは別要求として実行できたが、stateful continuationは初期化されていない。Artifact-indexの`needs_review`と合わせ、統合成果物は構造的に検証できた実動作候補であり、runner受入やQA workflow完了ではない。

証拠は同attemptの`target/.qa-eval-output/`、`evaluator-private/execution-record.json`、`.runtime-evidence/`に保存した。最終artifact indexはschema v1で、各artifact IDは正規相対pathのSHA-256と一致し、全9参照先が存在した。生成Markdownは9件、case inputは1件、capture-historyは24記録（うち最終canonical current 8件）。最終成果物、実行条件、verifier request/resultの一覧とSHA-256はGit管理外の `evidence-index.md` を参照する。Codexのsubagent実行ではCLI `--json` tool traceを得られず、Agentのfile-read履歴も監査できない。禁止対象を読まない指示、agent-visible rootsとprelaunch manifestは記録したが、物理的read-denialは未検証である。

## 5. 既存46成果物の再採点

元46件の詳細なcase別原因分析は [2026-10-29報告書](2026-10-29_pr17-agent-eval-analysis_v00.md) を参照。raw case outputは `.agent-eval-runs/` に保持し、変更していない。

| 入力成果物                    | Grader                            | PASS | FAIL | 例外 | 説明                                                                          |
| ----------------------------- | --------------------------------- | ---: | ---: | ---: | ----------------------------------------------------------------------------- |
| 元46成果物                    | 元grader                          |    3 |   41 |    2 | 保存された元結果を再現                                                        |
| 元46成果物                    | 修正grader                        |   16 |   30 |    0 | Parser / validator / fixture是正の効果。Skill改善ではない                     |
| 修正後Skillからの新規46成果物 | package同期前の一致runtime source |   45 |    1 |    0 | 唯一のFAILは`TEX-OUT-002`の`TEX-D005` / `TEX-D012`                            |
| 同じ新規46成果物              | package同期後の最終source         |   41 |    5 |    0 | TEx 1件に加え、Coverage 2件とTest Analysis 2件の古いruntime fingerprint不一致 |

最終sourceでの追加4 FAILは`RUNTIME-IMPLEMENTATION` fingerprint鮮度不一致であり、COV-OUT-001/002とRISK-OUT-001/002の保存済みAgent runtime evidenceは今回同期したbyte-identical `runtime_contract.py` sourceに対応しない。これらを現行Skillの意味的品質FAILと解釈しない。証拠を改変してfingerprintを合わせない。`TEX-OUT-002`は保存済み旧成果物に同じ2 assertion FAILが残るが、新規実Agent再生成は15/15 PASSした。

現行source再採点結果: `.agent-eval-runs/pr17-followup-independent-qts-20261030-01/regression-46/grader-result-final-source-after-sync.json`。出力root: `.agent-eval-runs/pr17-agent-eval-final-luna-max-20261030/output-root/`。

## 6. 確認した変更

- `test-requirement-design` guidance/template: `高` / `中` / `低`の正規enumを優先度欄に限定し、説明・暫定性を備考へ分離。
- `test-requirement-design` parser / deterministic validator / tests: qualified AC IDを保持する契約・回帰を確認。
- `coverage-analysis` runtime `evaluate_materialize_completion`: 複数TCNのMaterialize evidenceを集約し、model-to-TCN owner整合を検証する。重複runtime unit、unknown model、scope跨ぎを拒否。
- 上記runtime contractのbyte-identical複製を持つ残り8 Skillにも同じ実装を同期し、リポジトリの同一性契約を維持。
- Agent evaluator prompt: qa-training-storeの固定scenarioから許可された`skill/kind/scope`対応を生成Agentへ与え、artifact-index作成に必要な最小metadataを固定する。expected本文やstatusは与えない。
- Skill package copier: `__pycache__`、`.pyc`、`.pyo`を配布対象から除外。
- 最初のGitHub Code Quality実行（commit `039d519e`）で新規testのimport順違反（Ruff `I001`）が見つかったため、`test_workspace.py`のimportだけを整列した。ロジック変更ではなく、修正後にAgent focused testsを28件再実行してPASSした。
- 既存46ケースのexpected、rubric、validatorの合否条件はPASSを増やす目的で変更していない。

## 7. Judgeと正式受入

Judge dataset `qts-judge-fixtures-v2`は11件。Human review待ち9件、deterministic review待ち2件で、承認状態は変更していない。`major-violation-001`（必須test-case-design routingのskip）と`major-violation-002`（必須stage未完了をcompleteと報告）はscenario、rubricのcritical criteriaと整合することを決定論的に確認した。Human review待ちはnormal baseline 2件とmajor violation 7件で、仕様判断をAgentが代行していない。独立Judgeは起動していない。

正式評価には、認証refresh persistence、別processとのconcurrency acceptance、run-specific隔離read-denial/evidence、未承認Judge fixtureの人間承認、独立Judge検証が残る。今回の直接subagent結果はformal runner受入やPR受入成功ではない。

## 8. Tests / CI

| 検証                                                           | 結果                                                                                                                                                                                                |
| -------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Agent runner tests                                             | 156 PASS / 2 SKIP                                                                                                                                                                                   |
| Focused Agent tests（QTS prompt / workspace copier）           | 28 PASS                                                                                                                                                                                             |
| Agent evaluator repository contracts                           | 4 PASS                                                                                                                                                                                              |
| Deterministic runner tests                                     | 19 PASS                                                                                                                                                                                             |
| Focused deterministic validator tests                          | 10 PASS                                                                                                                                                                                             |
| Semantic runner tests                                          | 27 PASS                                                                                                                                                                                             |
| Semantic repository contracts                                  | 13 PASS                                                                                                                                                                                             |
| Skill runtime suite                                            | 378 PASS                                                                                                                                                                                            |
| Focused Skill runtime tests（test-requirement / traceability） | 25 PASS                                                                                                                                                                                             |
| `dprint check`                                                 | PASS                                                                                                                                                                                                |
| `compileall`（`scripts skills tests`）                         | PASS                                                                                                                                                                                                |
| `git diff --check`                                             | PASS                                                                                                                                                                                                |
| Full deterministic output suite                                | sandbox制約で356件中4 FAIL / 1 ERROR。tempfileが`/tmp/.git`のためGit worktree内と判定されるstate-root testsとlocalhost bind `EPERM`。既存のnormal WSL2 CI経路では再実行していない                   |
| Ruff                                                           | ローカルPython環境に`ruff` moduleがなく未実施。インストールしていない。GitHub Code Qualityは固定Ruff 0.16.8で検査し、commit `039d519e`では新規testの`I001`を検出                                    |
| GitHub Actions（commit `039d519e`）                            | Agent Skills / Deterministic Output / Semantic Outputはsuccess。Code Qualityは上記import順でfailure。Codex Harnessは今回の観測時点でin progress。follow-up commitでimport順を修正し、再CIを確認する |

commit `039d519e`の[Code Quality](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/actions/runs/40998456735)、[Agent Skills](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/actions/runs/40998456993)、[Deterministic Output](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/actions/runs/40998456737)、[Semantic Output](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/actions/runs/40998456818)、[Codex Harness](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/actions/runs/40998456833)。最終follow-up commitのCI状態はPR checksで確認し、PR本文にも記録する。

## 9. 未達事項と結論

- `TEX-OUT-002`: 旧成果物の2項目FAILは新規Agent再生成で15/15 PASS。正規Skill contractは十分なためSkill / grader修正なし。
- `test-requirement-design`: 確認したenum説明不足を修正し、別の未使用input `IND-TR-ROLE-001`でruntime-validな出力を確認。Templateの逸脱は同一input rerunで再発したため、generic Skill指示の不足とは断定せず残す。
- 既存46成果物: final sourceでPASS 41 / FAIL 5 / 例外0。うち4件は同期後のruntime fingerprintが古い保存済み証拠、1件はTEX旧出力の内容FAIL。
- `qa-training-store`統合、Judge承認/実行、Codex正式runnerおよび物理隔離の合格条件は未達として保持する。
- Skill品質の一般的な改善を認定するだけの反復数、モデルbuild telemetry、read audit、正式Judgeはない。
- 統合評価は9成果物を生成し最終runtime captureとtraceabilityを検証したが、artifact-indexは`needs_review`、workflow routingは部分完了であり、stateful workflow continuationとlive UI/browser evidenceは未実施である。構造検証を統合QA完了とは扱わない。
