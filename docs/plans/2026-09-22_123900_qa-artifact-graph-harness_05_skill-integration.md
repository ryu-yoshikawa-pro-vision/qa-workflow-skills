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
| `test-execution` | manual相当execution / result / evidence。既存TCの修正確認にも再利用 |
| `e2e-test-implementation` | E2E testware |
| `e2e-test-execution` | E2E execution / result / evidence。既存E2Eの修正確認にも再利用 |
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

## 5. 修正確認のrouting

修正確認は独立Skill、独立artifact、独立stateとして追加しません。`qa-workflow`が要求を修正確認として解釈し、必要な既存Skillへroutingします。

- currentな既存FAIL / 再現TCがある → analysis / designを省略し、manual相当は`test-execution`、repo E2Eは`e2e-test-execution`
- 期待結果、再現条件、current TCが不足する → 必要な最も早い既存analysis / design Skillで不足分だけ更新し、その後execution
- 周辺影響も確認する → `regression-testing`を別目的として追加

修正確認専用のテスト設計体系は作りません。既存のanalysis / design成果物を再利用できる場合は再利用します。

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
- source execution start / result / evidence / cleanup

修正確認でも同じexecution契約をそのまま再利用します。

を正本とします。

PR #12 Planでは最初の`scenario.when`操作開始がTCの開始済み境界です。`regression-testing`はこのsource contractを参照します。

### E2E

既存repo E2Eのexecution / rerun / raw result契約を正本とします。

TCなしE2EへTCを創作しません。

## 10. qa-workflow

`qa-workflow`は活動間routingだけでなく、複数Skillが必要なend-to-end QA要求をオーケストレーションします。

代表例:

- 新規・改修 + Regression asset reconciliation
- 修正確認 + Regression
- Regression Run planning + manual / E2E execution + Activity update
- Regression FAIL → analysis / investigation → fix → 既存TCの修正確認 → rerun
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

修正後はcurrentな既存TCが使えるなら直接再実行して修正確認し、設計不足がある場合だけ既存analysis / designへ戻します。必要ならbaseline / Run scopeを再評価します。

## 13. reporting / Defect Management

PR #13では汎用reporting Skillや`defect-reporting`を追加しません。

Finding / FAILを自動Defect化しません。

実装後に報告形式の重複や運用上の必要性が確認された場合は別課題として検討します。

## 14. Portability

既存Skillは単体利用時にRegression Suite / Activityを必須にしません。

`regression-testing`と`exploratory-testing`もGraph / relation indexなしで主要機能を利用できることを必須にします。

## 15. 継続QA知識

継続利用する知識の詳細契約は`_04d_continuous-qa-knowledge-and-concurrency.md`を正本とします。

新しいuser-facing Skillは追加しません。

既存正本へ属する知識は、その責任Skillへ戻します。

- 仕様・期待挙動 → `spec-analysis`
- Product Risk / test focus → `test-analysis`
- currentな実対象情報 → `test-target-inspection`
- TR / TCN / CI / TC → 各design Skill
- execution / result → PR #12 / E2E

それでも残る、複数workflowで再利用するテスト対象・仕組み・観点・環境の知識だけをproject-level知識成果物として扱います。

`qa-workflow`は知識の意味内容を独自に確定せず、project contextからrootを発見し、scopeに関係する有効entryを担当Skillへ入力として渡し、実際に利用したentry ref / revisionをworkflow stateへ残します。

## 16. project contextの追加入口

project contextへ知識本文やworkflow state本文を直接埋め込みません。

既存の「既存QA成果物」または最小追加欄から、少なくとも次の入口を発見できるようにします。

- 継続利用するQA知識成果物
- workflow history root
- Activity / Session history root
- shared environment / resource policy

既存の実施環境、test user、test data、cleanup等の案件固有値は引き続きproject contextへ保持します。

project context自体を汎用artifact registryにしません。

## 17. workflow state

`skills/qa-workflow/assets/workflow-state-template.md`は「1 project = 1 workflow」の形にしません。

各workflow stateへ最低限次を追加します。

- workflow_ref
- workflow objective / requested outcome
- workflow scope
- started source refs / revisions
- 利用したknowledge refs / revisions
- 利用したenvironment / shared resource refs
- produced artifact / Activity / Session refs
- optional related workflow refs

Skill状態表はそのworkflow内だけを表します。

同時進行する別workflowの状態を同じ行へmergeしません。

## 18. 共有成果物の並行更新

PR #12の`test-target-inspection`にあるrevision / SHA / ETagベースの競合防止を、共有current QA成果物更新時の共通原則として再利用します。

- 読み込み時revisionを保持
- 保存時にcurrent revisionを確認
- 条件付き更新が使える保存先では利用する
- 競合検出時に古いbaseで上書きしない
- stable ID / update scopeでdisjointを決定論的に証明できる場合だけcurrentを再読込してscope外を保持
- overlapping / unknown scopeでは責任Skillへ戻して再評価

汎用merge engineは追加しません。

## 19. shared environment / resource

`test-execution` / `exploratory-testing` / E2E等の実操作では、同時に利用するtest user、tenant、test data、external account等が他workflowへ影響し得ます。

実装時はproject context / Activity / Session / executionからshared mutable resourceと利用条件を追跡できるようにします。

安全な並行利用を確認できない場合は、project policyに従って直列化またはblockします。

resource reservation / lease / lockの具体方式は、PR #11 / #12 merge後の実装と外部リサーチを確認してから決定します。
