# Regression / Exploratory Testing 統合Plan

このPlanは、PR #11「決定論的テスト技法自動化」とPR #12「テスト対象資料管理・テスト実行Skill追加」が`main`へmerge済みであることを実装開始時の前提とし、両PRで解決済みのdesign traceability、change impact、execution / result / rerun lineageを再実装せず、継続RegressionとExploratory Testingに残る責務を追加する実装計画です。

PR #13では新規`regression-testing`と`exploratory-testing`を追加します。

「新規・改修」「Regression」「Exploration / Investigation」はQA活動全体を排他的に分類するものではありません。PR #13で責任Skillを持つ主要workflow入口として扱い、同一workflowで複数活動を組み合わせられるようにします。特に不具合修正ではConfirmation TestingとRegression Testingを別目的として扱います。

Graphの構築自体は目的にしません。主要workflowはrelation indexなしで成立させ、direct refとdeterministic scanで実需を満たせないことを実測した場合だけ、必要なquery向けの最小indexをその時点で設計します。

## 対象ブランチ

`feat/qa-artifact-graph-harness`

Plan作成ブランチ名と既存Planファイル名は旧設計の名称を維持します。実装はPR #11 / #12 merge後の最新`main`へ追従し、両PRの実契約を再確認してから開始します。

## 主要workflow入口と責任Skill

### 新規・改修

既存Skill群がcurrentなQA設計を作ります。

```text
spec-analysis
→ question-analysis
→ test-analysis
→ test-requirement-design
→ test-condition-design
→ test-case-design
→ coverage-analysis
```

既存Skill自身はRegression Suite membership、Run selection、Regression Activityを管理しません。

### Regression

新規`regression-testing`がRegression domainを担当します。

- initial baseline
- Regression Suite membership
- membership再評価
- full / selected
- selection rationale
- required execution route
- TCなし補助testware
- Regression Activity
- Run結果の集約
- Run完了判定
- Regression history

実際のmanual相当操作やE2E実行はPR #12 / E2E Skillへ委譲します。

### Exploration / Investigation

新規`exploratory-testing`が担当します。

- Charter
- Session
- Observation
- Finding
- Evidence
- Follow-up
- 既存責任Skillがない仮説駆動Investigation

### Confirmation Testing

新Skillは追加しません。

不具合修正後に既知のFAIL / 再現TCを再実行して元のdefectが解消したか確認する経路として、`test-execution` / `e2e-test-execution`を再利用します。

```text
defect fix
→ Confirmation Testing
→ 必要なRegression Testing
```

ConfirmationとRegressionは同一workflowで両方実施できます。

## 構成

1. [目的・現状・責務境界](./2026-09-22_123900_qa-artifact-graph-harness_01_scope-and-baseline.md)
2. [Cross-artifact query / relation index導入判定](./2026-09-22_123900_qa-artifact-graph-harness_02_graph-contract.md)
3. [決定論的補助runtime・履歴発見](./2026-09-22_123900_qa-artifact-graph-harness_03_harness-architecture.md)
4. [QA活動の接続・Confirmation・feedback](./2026-09-22_123900_qa-artifact-graph-harness_04_activity-models.md)
5. [Regression Suite・Run・実行契約](./2026-09-22_123900_qa-artifact-graph-harness_04a_regression-suite.md)
6. [regression-testing Skill契約](./2026-09-22_123900_qa-artifact-graph-harness_04b_regression-testing-skill.md)
7. [exploratory-testing Skill契約](./2026-09-22_123900_qa-artifact-graph-harness_04c_exploratory-testing-skill.md)
8. [既存Skill・PR #11/#12統合](./2026-09-22_123900_qa-artifact-graph-harness_05_skill-integration.md)
9. [評価・CI・実装順序・完了条件](./2026-09-22_123900_qa-artifact-graph-harness_06_evaluation-ci-implementation-order.md)

## 固定方針

1. PR #11をdesign identity / traceability / change impact / freshnessの正本とし、PR #13で第二のdesign graphやcurrentness state machineを作らない。
2. PR #12 / E2Eをexecution / result / evidence / rerun lineageの正本とし、PR #13でexecution schemaを複製しない。
3. 新規・改修Skillはcurrent QA設計を作る責務に留める。Regression固有のmembership / Run selection / Activity管理を追加しない。
4. `test-analysis`は変更影響候補とProduct Risk等を分析する。既存Suiteから今回実行するTCを確定するRegression Run selectionは`regression-testing`が担当する。
5. `qa-workflow`は活動間のrouting、共通workflow state、blocked / resume、複合workflowのオーケストレーションを担当し、Regression固有の意味判断を再実装しない。
6. baseline更新・Run selection・history参照等の単独要求は`regression-testing`から開始できる。manual / E2E実行まで含むend-to-end Regressionは`qa-workflow`が`regression-testing`とexecution Skillを接続する。
7. Confirmation Testingは独立Skillにせず、既知のFAIL / 再現TCの再実行としてexecution Skillを使う。必要なRegressionとは別に扱う。
8. Regression運用中のprojectでmembership入力が変わった場合、古いbaselineをcurrent扱いしない。変更時handoffに加え、各Run開始前にsource ref / revisionとcurrent stateを照合して必要なreconciliationを行う。
9. initial baselineはauthoritative TC discovery snapshotを固定してからmembershipを処理する。TC数が多い場合はdeterministicに分割・再開でき、全件が閉じるまで`complete=false`とする。
10. TC discoveryの完全性、PR #11 lifecycleへ解決できるか、test basisからのcoverageが閉じるかは別々に判定する。legacy TCを発見しただけでinventory欠落扱いにせず、currentnessを判定できない場合はbaseline completeを成立させない。
11. Regression Suiteは全current TCの保管庫ではなく、current Regression対象範囲を継続的に検証するlogical TCの基準集合とする。current TCとpersistしたmembership判断から再構成できる場合は派生viewを優先する。
12. `coverage-analysis`はRegressionの判断主体にせず、Regression対象範囲→TC、TC→E2E実装等の意味上coverageを検証する。
13. required execution routeは「何を実行する必要があるか」だけを表し、manualと具体的E2E testware refの組合せで構成する。`未実行` / `blocked`はrouteではなく実行状態として分離する。
14. execution artifactの存在だけでexecutedと判断しない。PR #12 / E2Eのsource execution契約上、実際に開始されたことを確認してexecutedを集計する。
15. Suite completeness、Run scope、executed / unexecuted、source resultのPASS / FAIL / 判定不能等を分離する。Regression Activityはsource resultを再判定せずrefと確認済み状態を投影する。
16. `regression-testing`のresidual riskはcurrent Product Risk等を再採点せず、excluded / blocked / unexecuted / coverage gapによって残る既存Riskへの影響を示す。新しいRisk identification / scoringは`test-analysis`へ戻す。
17. Regression中のFAIL / Findingでworkflowを終了しない。証拠に応じて既存責任Skillまたは`exploratory-testing(mode=investigation)`へroutingし、修正後のConfirmation、必要なRegression再評価 / rerunへつなぐ。
18. `exploratory-testing`はCharter / Session / Observation / Finding / Follow-up、block / resume / completion、安全・cleanupを明示的な契約として持つ。`investigation`は別Skill / 別runtimeにせず、symptom / hypothesisを起点にする同じSession契約として扱う。
19. Activity stateの正規値は既存`qa-workflow`語彙を再利用する。Regression Activityのdomain stateは`regression-testing`が判断し、`qa-workflow`は独立計算せずworkflow状態へ反映する。
20. relation indexは実装対象ではなく将来gateとする。direct ref + deterministic scanで不足を実測するまでrelation schemaも確定しない。
21. query結果の完全性を保証できない場合は`complete=false`相当を明示し、空集合を「影響なし」「Regression不要」と解釈しない。
22. 新2 Skillの意味品質はdataset構造検証だけで完了扱いにしない。既存semantic runnerと実Judgeを用いた代表caseの評価を実装完了時に別途記録する。

## 対象外

- 既存の新規・改修SkillをRegression専用Skillへ拡張すること
- Confirmation専用Skill
- Investigation専用Skill
- Suite maintenance専用Skill
- 汎用reporting Skill / defect-reporting Skill
- Finding / FAILの自動Defect化
- `qa-workflow`へRegression固有の意味判断を追加すること
- QA全体を新しいGraphへ移すこと
- Graph DB / query server / web UI
- 汎用artifact registry
- 新しい共通Feature ID体系 / feature hierarchy
- PR #11 / #12 runtimeの再設計
- PR #13独自freshness / currentness state
- TCなしE2Eの自動TC化
- 全既存E2Eの暗黙Regression加入
- Regression scopeの完全自動決定
- Exploration結果の仕様Authorityへの自動昇格
