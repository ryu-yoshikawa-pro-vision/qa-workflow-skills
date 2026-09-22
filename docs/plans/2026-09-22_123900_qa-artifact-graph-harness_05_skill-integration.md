# Regression / Exploratory Testing 統合Plan

## 1. Skill構成

PR #13ではuser-facing Skillを2件追加します。

- `regression-testing`
- `exploratory-testing`

既存の新規・改修Skillは責務を維持します。

| Skill / runtime | PR #13での位置づけ |
| --- | --- |
| PR #11 Machine Entity / traceability | identity / lifecycle / impact / freshnessの正本 |
| `test-analysis` | 新規・改修のRisk / test objective / test scope |
| `test-case-design` | current logical TC |
| `coverage-analysis` | 指定された成果物のcoverage検証 |
| `regression-testing` | Regression baseline / membership / selection / Activity |
| `test-target-inspection` | currentな実対象情報 / UI / 既知範囲のふるまい収集 |
| `test-execution` | manual相当execution / result / evidence |
| `e2e-test-implementation` | E2E testware |
| `e2e-test-execution` | E2E execution / result / evidence |
| `e2e-test-result-analysis` | E2E failure分析 |
| `exploratory-testing` | Exploration / 仮説駆動Investigation |
| `qa-workflow` | QA活動間のrouting / common workflow state |

## 2. 既存の新規・改修Skill

`test-analysis`等へRegression固有責務を追加しません。

新規・改修側は次を作ります。

- current仕様
- Product Risk
- test objective / test scope
- TR / TCN / CI / TC
- current TC→E2E mapping
- PR #11によるchange impact / freshness

これらは`regression-testing`の入力です。

「新しいTCを作ったらSuiteへ追加する」のは`test-case-design`の責務ではありません。

## 3. regression-testing

詳細契約は`_04b_regression-testing-skill.md`を正本とします。

責務:

- initial baseline
- membership / membership再評価
- full / selected
- candidate / selected / excluded
- residual risk
- required execution route
- TCなし補助testware
- Regression Activity
- Run完了判定
- history参照

担当しないもの:

- 仕様分析
- Product Riskの新規評価
- TR / TCN / CI / TC設計
- browser操作
- E2E failure原因分析
- PR #11 freshness再実装

## 4. project context

既存`skills/qa-workflow/assets/project-context-template.md`を拡張します。

既存欄を再利用:

- §3 テスト範囲
- §8 非機能テスト範囲
- §11 対象外
- §14 既存QA成果物

必要な案件だけ追加:

- Regression既定Run方針
- TCなしE2E等の補助Regression testware refs

対象機能、role、業務フローをRegression専用欄へ複製しません。

## 5. coverage-analysis

Regression専用Skillにはしません。

`regression-testing`または`qa-workflow`から指定された対象に対し、既存責務の範囲で確認します。

- current Regression対象範囲→TCの意味上coverage
- stale / `要再検証`TCをcurrent coverageへ数えていないか
- selected scopeのcoverage
- TC→E2E実装の十分性

coverage gapを見つけた場合は既存routingに従って責任Skillへ戻します。

Regression membership / selectionを`coverage-analysis`自身で決定しません。

## 6. PR #11

正本:

- stable QA ID
- Machine Entity
- design dependency / traceability
- change impact
- freshness / stale / `要再検証`
- partial update lifecycle

`regression-testing`はこれを入力として利用します。

PR #11がproject-wide artifact discoveryを保証するとは仮定しません。

## 7. PR #12 / E2E

### test-target-inspection

currentな実対象情報 / UI / 既知範囲のふるまい確認を担当します。

### test-execution

実行時TC snapshot、manual相当execution / result / evidenceを正本として扱います。

Regression Activityにはexecution refだけを保持します。

### E2E

TCあり / TCなしの既存経路を維持します。

TCなしE2EへTCを創作しません。

## 8. exploratory-testing

### 目的

既知TC実行と分離し、charterに基づく探索・仮説検証を担当します。

### mode

- `exploration`
- `investigation`

### routing

- current UI / ふるまい情報収集 → `test-target-inspection`
- 既知TC実行 → `test-execution` / `e2e-test-execution`
- E2E failure → `e2e-test-result-analysis`
- 仕様不明 → `question-analysis`
- coverage gap → `coverage-analysis`
- ownerなしの仮説駆動調査 → `exploratory-testing(mode=investigation)`

## 9. qa-workflow

`qa-workflow`は活動間routingへ集中します。

追加するrouting:

- 新規・改修完了 → 必要なら`regression-testing`へ変更成果物をhandoff
- Regression要求 → `regression-testing`
- Regression中のcoverage確認 → `coverage-analysis`
- Regression中のmanual実行 → `test-execution`
- Regression中のE2E実行 → `e2e-test-execution`
- execution結果 → `regression-testing`
- Exploration → `exploratory-testing`

`qa-workflow`自身は次を決めません。

- Regression membership
- full / selectedの意味判断
- candidate / selected / excluded
- required execution route
- Regression Activity完了条件

## 10. Portability

既存Skillは単体利用時にRegression Suite / Activityを必須にしません。

`regression-testing`と`exploratory-testing`も、汎用Graph / relation indexなしで主要機能を利用できることを必須にします。
