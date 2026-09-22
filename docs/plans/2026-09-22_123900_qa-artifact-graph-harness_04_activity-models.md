# Regression / Exploratory Testing 統合Plan

## 1. QA活動

PR #13ではQA活動を次の責務へ分けます。

- 新規・改修: 既存Skill群
- Regression: 新規`regression-testing`
- Exploration / Investigation: 新規`exploratory-testing`

既存Skillへ別活動の責務を上乗せしません。

## 2. 新規・改修からRegressionへの接続

既存flow:

```text
仕様根拠
→ test-analysis
→ test-requirement-design
→ test-condition-design
→ test-case-design
→ coverage-analysis
→ 必要時 adversarial-review / E2E
```

このflowはcurrent QA設計を確定します。

完了後、`qa-workflow`は必要なcurrent成果物を`regression-testing`へhandoffします。

handoff候補:

- current TC refs
- PR #11 lifecycle / change impact
- current Product Risk
- project context / current scope
- Finding等のsource ref
- current TC→E2E mapping

既存の設計Skill自身はSuiteを更新しません。

## 3. initial baseline

既存TCを持つprojectで初めてRegression管理を開始する場合、`regression-testing`が全current TCをreconcileします。

```text
current Regression対象範囲
→ authoritative TC discovery
→ current TC
→ membership
→ baseline
→ coverage-analysis
```

baseline completenessを確認できなければfull baseline確定をblockします。

## 4. 通常のbaseline更新

新規・改修flowやExplorationのfollow-upで成果物が変わった場合、`qa-workflow`は変更結果を`regression-testing`へroutingします。

`regression-testing`は次を使ってmembership再評価範囲を決めます。

- TC lifecycle / content変更
- PR #11 change impact
- Regression対象範囲変更
- project policy変更
- relevant Risk / test objective変更
- one-off / 対象外判断変更

影響範囲を安全に限定できない場合はcurrent TC全体を再確認します。

## 5. Regression

```text
regression-testing
→ baseline snapshot
→ full / selected
→ required execution routes
→ test-execution / e2e-test-execution
→ execution result
→ regression-testing
→ Regression Activity更新 / 完了判定
```

`regression-testing`はbrowser操作やE2E failure分析を担当しません。

## 6. Exploration

`activity_type=exploration`

新規`exploratory-testing`を使用します。

Charter:

- 探索目的
- 対象 / 非対象
- 起点Risk / Question / Change
- timeboxまたは終了条件
- 許可操作範囲
- 副作用scope / 最大回数
- evidence方針

Findingから作られたQuestion / Risk / Test Condition / Test Caseはsource Findingへ追跡できるrefを保持します。

新しいTCやRiskがRegressionへ影響する場合、`qa-workflow`が`regression-testing`へhandoffします。

## 7. Investigation

既存責任Skillを先に判定します。

- currentな実対象情報 / UI構造 / 既知範囲のふるまい収集 → `test-target-inspection`
- Playwright E2E failure → `e2e-test-result-analysis`
- 既知TC実行 → `test-execution` / `e2e-test-execution`
- coverage gap → `coverage-analysis`
- 仕様不明点 → `question-analysis`

`exploratory-testing(mode=investigation)`は、既存責任Skillがなく、未確定問題について実対象を操作しながら仮説検証する場合だけ使用します。

## 8. qa-workflow routing

```text
新規・改修要求
→ existing design flow
→ 必要なら regression-testing へ変更成果物をhandoff

Regression要求
→ regression-testing
→ 必要なcoverage検証 / execution Skillへrouting
→ regression-testingへ結果を戻す

Exploration要求
→ exploratory-testing(mode=exploration)

Investigation要求
→ existing owner判定
→ ownerなしの仮説駆動調査だけ exploratory-testing(mode=investigation)
```

`qa-workflow`は活動間を接続しますが、Regression membership / selection / Run完了判定を自身で行いません。
