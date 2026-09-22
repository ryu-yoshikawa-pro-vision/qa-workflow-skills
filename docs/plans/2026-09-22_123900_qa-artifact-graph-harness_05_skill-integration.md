# Regression / Exploratory Testing 統合Plan

## 1. Skill構成

PR #13ではuser-facing Skillを2件追加します。

- `regression-testing`
- `exploratory-testing`

既存の新規・改修Skillは責務を維持します。

| Skill / runtime | PR #13での位置づけ |
| --- | --- |
| PR #11 Machine Entity / traceability | identity / lifecycle / impact / freshnessの正本 |
| `test-analysis` | 新規・改修の変更影響候補 / Product Risk / test objective / test scope |
| `test-case-design` | current logical TC |
| `coverage-analysis` | 指定された成果物の意味上coverage検証 |
| `regression-testing` | Regression baseline / membership / Run計画 / Activity / history |
| `test-target-inspection` | currentな実対象情報 / UI / 既知範囲のふるまい収集 |
| `test-execution` | manual相当execution / Confirmation / result / evidence |
| `e2e-test-implementation` | E2E testware |
| `e2e-test-execution` | E2E execution / Confirmation / result / evidence |
| `e2e-test-result-analysis` | E2E failure分析 |
| `exploratory-testing` | Exploration / 仮説駆動Investigation |
| `qa-workflow` | 複合workflowのrouting / common workflow state / blocked / resume |

## 2. 既存の新規・改修Skill

`test-analysis`等へRegression固有責務を追加しません。

新規・改修側は次を作ります。

- current仕様
- Product Risk
- test objective / test scope
- TR / TCN / CI / TC
- current TC→E2E mapping
- PR #11によるchange impact / freshness

「変更による回帰影響候補とProduct Riskを整理する」は`test-analysis`の既存責務として維持します。

「その影響候補等を使って、既存baselineから今回実行するRegression TCを確定する」は`regression-testing`です。

この境界をtrigger / semantic evalで固定します。

## 3. regression-testing

詳細契約は`_04b_regression-testing-skill.md`を正本とします。

正規の`対象 / 実行範囲`:

- `baseline / membership`
- `Run計画`
- `Run結果更新`
- `履歴参照`

`regression-testing`単体で完結できる要求と、`qa-workflow`がexecutionまでオーケストレーションする要求を分離します。

## 4. exploratory-testing

詳細契約は`_04c_exploratory-testing-skill.md`を正本とします。

正規の`対象 / 実行範囲`:

- `exploration`
- `investigation`

Investigation専用Skill / 別runtimeは追加しません。

## 5. Confirmation Testing

Confirmation専用Skillは追加しません。

既知のFAIL / reproductionに対して、

- manual相当 → `test-execution`
- repo E2E → `e2e-test-execution`

を再利用します。

ConfirmationとRegressionは目的を分離し、同じ`qa-workflow`内で順に実施できます。

## 6. project context

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

## 7. coverage-analysis

Regression専用Skillにはしません。

`regression-testing`または`qa-workflow`から指定された対象に対し、既存責務の範囲で確認します。

- current Regression対象範囲 → TC
- selected scope → selected TC
- TC → E2E実装

Regression membership / Run selectionを`coverage-analysis`自身で決定しません。

## 8. PR #11

正本:

- stable QA ID
- Machine Entity
- design dependency / traceability
- change impact
- freshness / stale / `要再検証`
- partial update lifecycle

`regression-testing`は入力として利用し、独自freshnessを作りません。

PR #11がproject-wide artifact discoveryを保証するとは仮定しません。

## 9. PR #12 / E2E

### test-target-inspection

currentな実対象情報 / UI / 既知範囲のふるまい確認を担当します。

### test-execution

- TC snapshot
- manual相当execution
- Confirmation execution
- source execution start / result / evidence / cleanup

を正本とします。

PR #12 Planでは最初の`scenario.when`操作開始がTCの開始済み境界です。`regression-testing`はこのsource contractを参照します。

### E2E

既存repo E2Eのexecution / rerun / raw result契約を正本とします。

TCなしE2EへTCを創作しません。

## 10. qa-workflow

`qa-workflow`は活動間routingだけでなく、複数Skillが必要なend-to-end QA要求をオーケストレーションします。

代表例:

- 新規・改修 + Regression asset reconciliation
- Confirmation + Regression
- Regression Run planning + manual / E2E execution + Activity update
- Regression FAIL → analysis / investigation → fix → Confirmation → rerun
- Regression + Exploration

`qa-workflow`自身は次を独立再判定しません。

- Regression membership
- full / selected
- candidate / selected / excluded
- required execution route
- source result
- Regression Activity domain state

## 11. workflow state / canonical Skill更新

PR #11 / #12 merge後の最新実装を確認し、少なくとも次をPR #13実装対象へ含めます。

- `skills/qa-workflow/assets/workflow-state-template.md`
- `scripts/skills/evals/deterministic/common.py`の`CANONICAL_SKILLS`
- 同ファイルの`MULTI_USE_SKILL_TARGETS`
- `skills/qa-workflow/evals/deterministic/validator.py`への影響確認
- qa-workflow routing fixtures / candidate outputs
- `.github/workflows/validate-skills.yml`のSkill一覧 / 件数
- README / EVALS / ASSERTIONS等のSkill一覧と件数

`MULTI_USE_SKILL_TARGETS`へ少なくとも次を追加します。

```text
regression-testing:
- baseline / membership
- Run計画
- Run結果更新
- 履歴参照

exploratory-testing:
- exploration
- investigation
```

最新mainのSkill数を実装時に再取得し、古い14 Skill前提をハードコードしません。

## 12. FAIL / Finding feedback

Regression中のFAIL / 判定不能は`regression-testing`が原因確定しません。

`qa-workflow`が証拠に応じて、

- E2E異常 → `e2e-test-result-analysis`
- 仕様不明 → `question-analysis`
- current実対象情報不足 → `test-target-inspection`
- TC問題 → `test-case-design`
- coverage gap → `coverage-analysis`
- ownerなしの仮説駆動調査 → `exploratory-testing | investigation`

へroutingします。

修正後はConfirmationを実施し、必要ならbaseline / Run scopeを再評価します。

## 13. reporting / Defect Management

PR #13では汎用reporting Skillや`defect-reporting`を追加しません。

Finding / FAILを自動Defect化しません。

実装後に報告形式の重複や運用上の必要性が確認された場合は別課題として検討します。

## 14. Portability

既存Skillは単体利用時にRegression Suite / Activityを必須にしません。

`regression-testing`と`exploratory-testing`もGraph / relation indexなしで主要機能を利用できることを必須にします。
