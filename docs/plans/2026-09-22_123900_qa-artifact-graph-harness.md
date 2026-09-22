# Regression / Exploratory Testing 統合Plan

このPlanは、PR #11「決定論的テスト技法自動化」とPR #12「テスト対象資料管理・テスト実行Skill追加」が`main`へmerge済みであることを実装開始時の前提とし、両PRで解決済みの設計traceability・change impact・execution lineageを再実装せず、継続RegressionとExploratory Testingに残る責務を追加する実装計画です。

PR #13では新規`regression-testing`と`exploratory-testing`を追加します。

既存の`test-analysis`、`test-requirement-design`、`test-condition-design`、`test-case-design`等は新規・改修テストの責務を維持します。Regression固有のmembership、baseline、full / selected、Run完了判定を既存Skillへ移しません。

Graphの構築自体は目的にしません。Regression / Exploration / Investigationの主経路はrelation indexなしで成立させ、direct refとdeterministic scanでも不足するqueryが実証された場合だけ最小relation indexを追加します。

## 対象ブランチ

`feat/qa-artifact-graph-harness`

Plan作成ブランチ名と既存Planファイル名は旧設計の名称を維持します。実装はPR #11 / #12 merge後の最新`main`へ追従し、両PRの実契約を再確認してから開始します。

## QA活動の責務

### 新規・改修

既存Skill群が担当します。

```text
spec-analysis
→ question-analysis
→ test-analysis
→ test-requirement-design
→ test-condition-design
→ test-case-design
→ coverage-analysis
```

この経路はcurrent仕様、Risk、TR、TCN / CI、TC、change impact等を確定し、Regression側が参照できるcurrent成果物を作ります。

既存Skill自身がRegression Suite membershipやRegression Run selectionを管理しません。

### Regression

新規`regression-testing`が担当します。

- initial baseline
- Regression Suite membership
- membership再評価
- full / selected scope
- selection rationale / residual risk
- required execution route
- TCなし補助testware
- Regression Activity
- Run完了判定
- Regression history

設計や実行の工程固有処理は既存Skillへ委譲します。

### Exploration / Investigation

新規`exploratory-testing`が担当します。

- Charter
- Session
- Observation
- Finding
- Follow-up
- 既存責任Skillがない仮説駆動Investigation

## 構成

1. [目的・現状・責務境界](./2026-09-22_123900_qa-artifact-graph-harness_01_scope-and-baseline.md)
2. [Cross-artifact relation index導入判定](./2026-09-22_123900_qa-artifact-graph-harness_02_graph-contract.md)
3. [決定論的補助runtime・履歴発見](./2026-09-22_123900_qa-artifact-graph-harness_03_harness-architecture.md)
4. [新規・改修 / Regression / Exploration / Investigation統合](./2026-09-22_123900_qa-artifact-graph-harness_04_activity-models.md)
5. [Regression Suite・Run・実行契約](./2026-09-22_123900_qa-artifact-graph-harness_04a_regression-suite.md)
6. [regression-testing Skill契約](./2026-09-22_123900_qa-artifact-graph-harness_04b_regression-testing-skill.md)
7. [既存Skill・PR #11/#12統合](./2026-09-22_123900_qa-artifact-graph-harness_05_skill-integration.md)
8. [評価・CI・実装順序・完了条件](./2026-09-22_123900_qa-artifact-graph-harness_06_evaluation-ci-implementation-order.md)

## 固定方針

1. PR #11をdesign identity / traceability / change impact / freshnessの正本とし、PR #13で第二のdesign graphやcurrentness state machineを作らない。
2. PR #12 / E2Eをexecution / result / evidence / rerun lineageの正本とし、PR #13でexecution schemaを複製しない。
3. 新規・改修Skillはcurrent QA設計を作る責務に留める。Regression固有のmembership / selection / Run管理を追加しない。
4. `qa-workflow`は新規・改修 / Regression / Explorationのroutingと共通workflow stateを担当し、Regression固有ロジックを持たない。
5. `regression-testing`はRegression Suite / baseline、membership、full / selected、required execution route、Activityを所有する。
6. `coverage-analysis`はRegressionの判断主体ではなく、current Regression対象範囲→TCおよびTC→E2E実装の意味上coverageを検証する。
7. Regression Suiteは全current TCの保管庫ではなく、現在のRegression対象範囲を継続的に検証するcurrentかつ再利用可能なlogical TCの基準集合とする。
8. 初回導入時はproject-wideなcurrent TC discoveryとmembership reconciliationを行う。全TCを漏れなく列挙できる根拠がない場合、baselineをcompleteとして確定しない。
9. membershipはTC lifecycle / contentだけでなく、Regression対象範囲、案件方針、関連Risk等が変わった場合も`regression-testing`が再評価する。
10. feature tagは任意filterとし、membership / coverageの正本にしない。
11. Suite completeness、Run scope、actual execution、PASS / FAILを分離する。
12. selected TCごとにrequired execution routeを固定し、required routeの一部だけでlogical TCをexecuted扱いしない。
13. TCなしE2Eはuser明示またはproject contextのRegression方針で補助testwareとして指定された場合だけ扱い、TC-based coverageへ算入しない。
14. Regression Activityはselection input refs / revisions、baseline、required route、execution refs、未実行 / blockedを保持し、当時の判断を再現可能にする。
15. Activity stateは既存`qa-workflow`の状態語彙を再利用するが、Regression Activityの生成・更新・完了判定は`regression-testing`が所有する。
16. `test-target-inspection`はcurrentな実対象情報の収集、`exploratory-testing(mode=investigation)`は既存責任Skillがない仮説駆動調査を担当する。
17. relation indexはdirect ref → deterministic scanでも実需を満たせない場合だけ追加する。
18. query結果の完全性を保証できない場合は`complete=false`相当を明示し、空集合を「影響なし」「Regression不要」と解釈しない。

## 対象外

- 既存の新規・改修SkillをRegression専用Skillへ拡張すること
- `qa-workflow`へRegression固有の意味判断を追加すること
- QA全体を新しいGraphへ移すこと
- Graph DB / query server / web UI
- 汎用artifact registry
- 新しい共通Feature ID体系 / feature hierarchy
- Suite maintenance専用Skill
- PR #11 / #12 runtimeの再設計
- PR #13独自freshness / currentness
- TCなしE2Eの自動TC化
- 全既存E2Eの暗黙Regression加入
- Regression scopeの完全自動決定
- Exploration結果の仕様Authorityへの自動昇格
- Findingの自動Defect化
