# Regression / Exploratory Testing 統合Plan

## 1. regression-testingの目的

`regression-testing`は、既存の新規・改修テスト設計成果物を継続Regressionへ接続し、Regression固有のbaseline / membership / Run / Activityを管理するuser-facing Skillです。

新規・改修のテスト分析やテスト設計は担当しません。

## 2. 使用する依頼

例:

- Regressionを実施したい
- full Regressionを実施したい
- 変更影響から今回のRegression対象を選びたい
- Regression baselineを初期構築 / 更新したい
- 過去のRegression Activityを確認したい
- Regressionの未実行 / blocked / residual riskを確認したい

次はこのSkillへroutingしません。

- 新規機能のRisk分析
- 変更機能のテスト分析
- TR / TCN / CI / TC設計
- current UIの事実収集
- 既知TCの実操作そのもの
- E2E failure原因分析
- Exploratory Testing

## 3. 入力

利用可能な範囲で次を使用します。

- userのRegression要求 / scope
- project context
- current Regression対象範囲
- authoritative TC discovery root
- PR #11 current TC identity / lifecycle / change impact
- current Product Risk / test objective
- current TC→E2E mapping
- previous Regression Suite / baseline metadata
- previous Regression Activity
- past FAIL / Finding
- user / project policyで明示されたTCなし補助testware

入力不足を推測で補いません。

## 4. 出力

### baseline / Suite

- current Regression対象範囲
- member TC refs
- membership判断 / 理由
- membership source refs / revisions
- exclusions / one-off理由
- completeness

### Regression Activity

- activity ref / state
- baseline snapshot
- run scope: full / selected
- candidate / selected / excluded
- selection rationale / residual risk
- selection input refs / revisions
- auxiliary testware refs
- required execution routes
- execution refs
- executed / unexecuted / blocked
- unresolved

## 5. initial baseline

初回は全current TCをreconcileします。

```text
current Regression対象範囲
→ authoritative TC discovery
→ PR #11 current lifecycle
→ membership判断
→ baseline
→ coverage-analysis
```

全TCを漏れなく列挙できる根拠がない場合、complete baselineとして扱いません。

## 6. membership

membership条件:

- current logical TC
- current Regression対象範囲内
- 継続的に再検証する意味がある

`regression-testing`はcurrent仕様、Risk、test objectiveを参照しますが、新規分析をやり直しません。

one-off migration、調査専用、一時確認等は恒常memberから外せます。

高コスト / manual / 特殊環境だけを理由に外しません。

## 7. membership再評価

trigger:

- TC lifecycle / content変更
- Regression対象範囲変更
- project Regression policy変更
- relevant Risk / test objective変更
- one-off / 対象外判断変更

PR #11 impact / traceabilityで安全に限定できる場合は影響TCだけ再評価します。

限定できなければcurrent TC全体を再確認します。

## 8. full / selected

優先順位:

1. user明示scope
2. project policy
3. 未指定ならfull fallback

### full

baseline snapshotの全TC memberをselectedにします。

### selected

PR #11 impact、current Risk、past FAIL / Finding、明示TC / filter等からcandidate / selected / excludedを決定します。

selectionの判断根拠をActivityへ保存します。

Regression selectionを`test-analysis`へ委譲しません。

## 9. coverage-analysisとの関係

`coverage-analysis`は検証役です。

必要に応じて次を確認します。

- current Regression対象範囲がSuite member TCへ閉じているか
- selected scopeが要求範囲へ意味上閉じているか
- TC→E2E実装が今回必要な検証責務を満たすか

`coverage-analysis`の結果を利用できますが、membership / selectionの最終判断主体は`regression-testing`です。

## 10. required execution route

selected TCごとに今回必要なrouteを固定します。

- manual
- E2E
- manual + E2E
- 未実行 / blocked

browser実行は担当しません。

`qa-workflow`を介して`test-execution` / `e2e-test-execution`へ渡し、execution ref / resultを受け取ります。

logical TCをexecutedとして数えるのはrequired routeがすべてexecution artifactへ閉じた場合です。

FAIL / 判定不能とexecutedを分離します。

## 11. TCなしE2E

参加条件:

- user明示
- project policyで補助testwareとして明示

TCを創作しません。

TC member / coverageとは別集計にします。

## 12. Activity lifecycle

状態値は既存`qa-workflow`語彙を使います。

- 未開始
- 実行中
- 部分完了（ブロック中あり）
- ブロック中
- 完了

`regression-testing`がRegression Activityについて状態遷移を判断します。

- scope / snapshot不変 → 同activityで再開可能
- scope / snapshot変更 → 別Activity / version
- 完了後 → immutable

全TC PASSをActivity完了条件と同一視しません。

## 13. history

過去Activityは固定rootからのdeterministic scanを優先します。

indexが必要な場合だけ最小indexを使います。

history queryのためだけにGraphを必須化しません。

## 14. qa-workflowとの関係

`qa-workflow`はroutingを担当します。

```text
Regression要求
→ regression-testing
→ coverage / execution等が必要なら担当Skillへrouting
→ execution結果
→ regression-testing
→ Activity更新 / 完了判定
```

`qa-workflow`自身はmembership / selection / required route / Run完了条件を判断しません。

## 15. 新規・改修flowとの関係

新規・改修Skillはcurrent QA成果物を作ります。

完了後、必要な変更成果物を`regression-testing`へhandoffします。

例:

- current TC追加 / 更新 / 削除
- Risk変更
- scope変更
- E2E mapping変更
- Finding由来の新規TC

設計Skill自身がSuiteを更新しません。

## 16. 対象外

- 新規・改修の仕様分析 / Risk評価
- TR / TCN / CI / TC設計
- PR #11 impact / freshness再計算
- browser操作
- E2E failure分析
- generic Exploration / Investigation
- Graphを前提にした履歴管理
