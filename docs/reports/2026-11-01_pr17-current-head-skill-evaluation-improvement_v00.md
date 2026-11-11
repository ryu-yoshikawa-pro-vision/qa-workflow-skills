# PR #17 現行HEADでのSkill改善再検証

## 結論

開始時のPR HEADは `7723b3f8b952bbc98fc51c2189612938c22a40ae` で、GitHub上のPR #17（OPEN、base `main`、head `feat/agent-eval-runner`）と一致した。今回の作業では、隔離された `test-requirement-design` template candidateを現行Skillに対して評価し直し、別Skill `test-analysis`でも保存済みの失敗を再評価した。

現行HEADでは、架空の「テスト要求を作らない上流項目」行は `TR-OUT-010` のbaselineで2/2回とも出なかった。candidateは1/2回だけ採点可能で、その成果物はPASSしたが、もう1回はartifact生成前に終了した。したがって、現行Skillに対する修正効果は確認できず、candidateは採用していない。candidate試行の失敗も除外・再試行していない。

`test-analysis`では過去の懸念 `RISK-D013` は再現しなかった。その他の1回限りの失敗は再現性がなく、`RISK-OUT-002`のruntime unit期待値にはSkill記述とfixtureの適用範囲の不一致が疑われる。Skill起因の確定問題は得られなかったため、修正は行っていない。

## 対象・条件

- PR #17: https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/pull/17
- 開始HEAD / 評価revision: `7723b3f8b952bbc98fc51c2189612938c22a40ae`
- 評価Skill: `test-requirement-design`、`test-analysis`
- Agentへの設定要求: `gpt-6-luna / max`、`fork_turns=none`
- CLI version、provider build、実効モデル設定のplatform telemetry: 未取得。要求値は記録されているが、実効設定の証明ではない。
- Evaluator: 開始HEADの既存deterministic runner / expected / Skill-local runtime verifierを使用。
- 生成Agentへpromptで渡したもの: 対象Skill package、対象input、出力先。expected/grader pathは渡していない。
- 実効情報隔離: サブエージェントと親はworkspace権限を共有するため、expected・graderへの物理的なread-denialは未証明。以下は開発用の実動作検証であり、正式な独立評価ではない。
- 認証storeの読み取り・変更、`codex exec`、launcherのfail-closed解除、独立Judgeは実施していない。
- 実行証拠はGit管理外の `.agent-eval-runs/` に保存し、raw成果物やexpectedはcommit対象にしていない。

## 旧candidateと因果関係

旧candidateはbaseline `b9aa550df8f4fe7e0a84b77fe534ed1a8426227d` と当時のcandidate `55869f870f48ebdbc89575d249373c8ecbcccfcb` に対するもので、現行HEADへの改善根拠とはならない。

保存済みの隔離patch `.agent-eval-runs/pr17-tr-causal-20261031-r1/evaluator-private/candidates/baseline-to-disposition-only.patch`（SHA-256 `4be619109b8e1f4327020a7102425a0d0d651b0fe31899c3fac5168077cf27bc`）は、`assets/output-template.md`だけを変更し、disposition表の架空例行を削除して、実在する未リンク上流項目のみ列挙するよう指示する。disposition欄の不具合に直接関係するのはこの変更である。

当時のfull candidateに追加された「要求一覧はheader-only」という `SKILL.md` の指示は、別の「テスト要求一覧」表に対するものだった。disposition表を直接修正する指示ではないため、disposition不具合の原因・修正とは区別する。現在のHEADでも要求一覧にはheader-onlyの指示がある一方、disposition表のtemplateには説明用の空行が残っている。

旧証拠の対応関係にも欠落がある。旧 `evidence-index.md` には55 attempt行と6 exclusion記載（重複を除く5 attempt）がある一方、attempt directoryは67件で、9件がindexにもexclusionにも記録されていない。このため旧比較は履歴として参照できるが、完全なattempt母集団として現行candidateの採否根拠には使用しない。

## 現行HEADの比較結果

### 18-attempt比較

証拠: `.agent-eval-runs/pr17-tr-current-head-20261031-r2/evidence-index.md`、`evaluator-private/experiment-manifest.json`、`evaluator-private/post-run-summary.json`。全18 attemptを事前固定し、明示的なquality除外は0件。expected/input/graderはarm間で固定され、各生成promptにexpected/grader pathを含めていない。

| Eval         | 条件                                               | Baseline                                               | Candidate                                                                | 判定                                                                                                     |
| ------------ | -------------------------------------------------- | ------------------------------------------------------ | ------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------- |
| `TR-OUT-001` | 既存、明示的dispositionあり                        | 1/1 grader PASS、runtime valid                         | 1/1 PASS、runtime valid                                                  | 明示的な実在項目の扱いを維持                                                                             |
| `TR-OUT-003` | 不完全なartifact入力、blocked維持                  | 1/1 PASS、runtime valid                                | 1/1 PASS、runtime valid                                                  | blocked処理を維持。candidate出力では未提供の`SPEC-001`をhelper入力に含めた疑義があり、意味面の注意を記録 |
| `TR-OUT-004` | 通常の要求生成                                     | 1/1 PASS、runtime valid                                | 1/1 PASS、runtime valid                                                  | 通常要求に回帰なし                                                                                       |
| `TR-OUT-005` | 旧対象ケース、通常要求生成                         | 2/2 PASS、runtime valid                                | grader 2/2 PASS、runtime 1/2 valid                                       | candidate a2は`missing_runtime_unit`。grader PASSだけで適合とは判定しない                                |
| `TR-OUT-013` | 事前固定のheld-out入力、実在する未解決上流項目あり | 0/2 PASS。両方`TR-D013/TR-D009/TR-D015`、runtime valid | 1/2 PASS、1/2同assertion FAIL、runtime両方valid                          | candidateの改善は不安定。FAILは安定IDにrevisionを混在させた問題で、disposition修正による効果ではない     |
| `TR-OUT-008` | stable ID / revision確認                           | 2回ともruntime gateで生成物が保存されず採点なし        | 1/2 grader PASSだが`missing_entity`、1/2は`TR-D013/TR-D009/TR-D015` FAIL | arm比較不成立。candidateの安定改善なし                                                                   |

`TR-OUT-013`はpatch決定前に固定された独立入力で、同じ意味範囲にrevisionが変わるケースである。dispositionそのものはcandidateの一方で期待どおりだったが、もう一方はstable ID規則に関する失敗を残した。特定修正の汎用的効果とはいえない。

### TR-OUT-010 targeted比較

証拠: `.agent-eval-runs/pr17-tr-current-targeted-20261101-r3/evidence-index.md` と `evaluator-private/manifest.json`。baseline 2回、template-only candidate 2回を固定し、明示的除外・quality retryは0件。Input SHA-256 `399c0af386a13e3a4873f1177719099ad093cd41a93180781237536746fee604`、expected SHA-256 `a6f438af50310d6b6ac70cfafbaeb287335436e0bb87266408a62e745a6dfe0c`。

- 現行baseline: 2/2 grader PASS（各17/17）、runtime verifier 2/2 valid。どちらもdisposition表はheader-onlyで、架空の行はない。
- Candidate: a1はhelperの戻り値に`payload.entities`がないとしてartifact組立時に停止したとのAgent報告があるが、request/resultログがなく独立再現できない。試行を失敗のまま保持し、再試行していない。a2は17/17 PASS、runtime verifier valid、架空のdisposition行なし。
- これは旧candidate形成時にも使われた入力であり、独立held-out評価ではない。現行baselineに不具合が再現しないため、candidateによる改善とは判定しない。
- Candidate a2の要求本文には英語表現が混じったがgrader違反ではなく、1例だけなのでtemplate変更の効果や回帰とは断定しない。

### 正当なdisposition・blocked・runtime契約

実在するdispositionは `TR-OUT-001` で保持され、入力不完全のblocked処理は `TR-OUT-003` でgrader上維持された。通常要求生成は `TR-OUT-004/005` で確認した。架空行がないことだけでなく、runtime verifierを別に判定し、candidate `TR-OUT-005` の1件を不適合として残した。旧revisionでの `TR-OUT-011` 2/2維持は旧証拠に限られ、現行HEADに対する再検証とは扱わない。

## 別Skill: test-analysis

証拠: `.agent-eval-runs/pr17-cross-skill-test-analysis-20261101/evidence-index.md`、`evaluator-private/manifest.json`、`evaluator-private/post-run-summary.json`。固定した4 attemptを全件採点し、quality除外なし。入力は `RISK-OUT-001` を2回、事前固定した独立回帰入力 `RISK-OUT-002` を2回使用した。

- `RISK-OUT-001`: 1回は90/90 PASS、1回は87/90で`RISK-D008/D014/D018` FAIL。過去に懸念した`RISK-D013`の未記載は再現しなかった。失敗出力はenum欄に説明を混ぜ、必須techniqueを欠いたが、別attemptで再現しない。Skill/guidanceはenum値と説明欄を分ける現行契約をすでに明記している。
- `RISK-OUT-002`: 1回は90/90 PASS、1回は86/88で`RISK-D018`と`RUNTIME-UNITS-EXACT` FAIL。失敗成果物はrisk別selection key `RISK-002`を使用し、expectedは`selection-001`を要求する。Inputの技法指定はRISK-002行の下にインデントされ、現行Skillは単一Riskの選択にはrisk ID、複数Riskにまたがる選択には`selection-001`を定める。ここはfixtureの期待値と入力のscopeが一致しない可能性があり、PASS件数を増やす目的でexpectedを変えず、契約上の未解決として残す。
- 4成果物すべてでSkill-local verifierは`missing_entity`を返した。入力に`SPEC-001/002`はあるが、現行Machine Runtimeが必要とするcurrent Authority EntitiesはAgent-visible入力に存在しない。deterministic expectedもanalysis entity生成をblocked扱いする。これをSkill欠陥や完了済runtimeとして扱わない。
- 最初の`RISK-OUT-001` grader呼出し1回はsource-root指定誤りで、同じ保存成果物を正しいroot指定で再採点し、その結果をcanonicalとした。Agent生成の再試行・除外はしていない。

## 評価改善工程の再利用状況

今回、既存のrun/eval入力、固定manifest、Skill packageのbaseline/candidate複製、既存deterministic runner、Skill-local runtime verifier、attemptごとの成果物・hash・grader結果保存を`test-requirement-design`と`test-analysis`で再利用した。候補patchはGit外に保存し、対象packageにtemplate 1ファイルだけを適用した。評価入力、期待値、graderは変更していない。

正式な`improve.py` repair acceptanceには進めていない。同実装は独立baseline attempt、保存済みtrace、検証済みAgent隔離、workspace integrity、runtime/provenance等を要求する。今回の共有workspace実行ではread-denialや隔離statusをverifiedにできないため、そのゲートを満たしたと偽らず、candidate自動採用もしていない。したがって実証できたのは、開発用の評価→原因分類→隔離candidate比較→別Skillでの手順再利用までであり、正式な自動修正受入ではない。

## テスト・CI

今回tracked code/testの変更はないため、focused regression suiteを実行済みの既存HEADで確認した。

- `tests.skills.runtime.test_runtime_contract`: 56 passed
- `tests.skills.runtime.test_test_requirement_structure`: 10 passed
- `tests.skills.runtime.test_test_analysis_entities`: 17 passed
- `tests.skills.runtime.test_test_analysis_technique_candidates`: 3 passed
- `tests.skills.evals.deterministic.test_deterministic`: 10 passed
- 対象agent/runtime/scripts/testsの`compileall`: success
- 7723 HEADでのGitHub Actions: Code Quality、Validate Deterministic Output Evals、Validate Semantic Output Evals、Validate Agent Skills、Codex Harnessの5 workflowがsuccess。
- 報告書を含むcommit `8da8f9b5e836f51f96a0c9a552d34b0aa3b997f6`のGitHub Actionsも5 workflowすべてsuccess。

## 判断と未達

- `test-requirement-design` template candidate: **隔離candidateのまま。正式Skillへ未採用。** 現行baselineで対象の架空disposition行が再現せず、独立ケースの結果も不安定で、candidate固有の効果を確認できなかった。
- `test-analysis`: **修正なし。** 再現性あるSkill契約欠陥は確認できず、RISK-OUT-002のkey scopeはfixture/inputとの整合を別途解決する必要がある。
- 再利用可能な評価工程: **開発用の手順再利用を確認。** `improve.py`の正式自動改善受入、物理的なEvaluator情報隔離、実効モデル/CLI telemetry、独立Judge、正式runner実行は未達。
- 既存Skill修正による品質改善: **今回確認なし。** 意図的なbaseline劣化、expected緩和、quality-based再試行・除外は行っていない。
