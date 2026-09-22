# Regression Suite / QA Activity 統合Plan

## 1. 既存Skillとの関係

| Skill / runtime | PR #13で利用する内容 |
| --- | --- |
| PR #11 Machine Entity / traceability | design identity / lifecycle / impact / freshnessの正本 |
| `test-analysis` | 継続Regression対象判断、selected scope判断 |
| `test-case-design` | current logical TC |
| `coverage-analysis` | Regression対象範囲coverage、TC → E2E実装coverage |
| `test-target-inspection` | target snapshot |
| `test-execution` | manual相当execution / result / evidence |
| `e2e-test-implementation` | testware |
| `e2e-test-execution` | E2E execution / result / evidence |
| `e2e-test-result-analysis` | E2E failure分析 |
| `qa-workflow` | Suite見直し、activity、routing、history discovery |
| `exploratory-testing` | Exploration / Investigation |

## 2. PR #11

PR #11を次の正本とします。

- stable QA ID
- Machine Entity
- design dependency / traceability
- change impact
- freshness / stale / `要再検証`
- partial update lifecycle

PR #13で行いません。

- design impact再計算
- Graph独自currentness
- Machine Entity再生成
- Graph目的のfingerprint拡張
- current / deleted / superseded相当の独自判定

Regression SuiteはPR #11のcurrent TC / lifecycleを参照します。

## 3. PR #12 / E2E

### test-target-inspection

target snapshotの正本として利用します。実測挙動をspecificationへ自動昇格しません。

### test-execution

- `test_case_ref`はartifact-local
- `source_test_case_id`をglobal keyへしない
- 実行時TC snapshotはPR #12を正本とする
- 再実行は別execution
- secret実値を別成果物へ複製しない

Regression activityにはexecution refだけを保持し、PR #12のsnapshot内容を複製しません。

### E2E

TCあり / TCなしの既存経路を維持します。

TCなしE2EへSuite都合でTCを創作しません。

## 4. exploratory-testing

### 目的

詳細TCの厳密実行と分離し、charterに基づく探索・仮説検証を行います。

### mode

- `exploration`
- `investigation`

### 必須入力

exploration:

- 対象 / 入口
- charter objective
- scope / non-scope
- 許可origin
- 副作用scope
- 終了条件またはtimebox
- evidence制約

investigationでは加えて、対象Finding / Question / symptomと確認したい仮説を扱います。

### browser safety

PR #12のPlaywright実行基盤、安全境界、secret保護、side-effect / cleanupを再利用します。

`test-execution`固有の詳細TC手順固定は継承しません。

### output

- session
- observations
- findings
- evidence refs
- follow-up refs

Findingを自動Defect化せず、実測を仕様Authorityへ昇格しません。

## 5. Regression専用Skillを追加しない理由

Regression固有処理は既存責務で分割できます。

- 継続Regression対象判断 → `test-analysis`
- design impact → PR #11
- coverage → `coverage-analysis`
- Suite bookkeeping / Run routing → `qa-workflow`
- manual execution → `test-execution`
- E2E execution → `e2e-test-execution`
- failure analysis → 既存analysis Skill

新しい`regression-testing` Skillは追加しません。

## 6. coverage-analysis拡張

新しい確認対象としてRegression Suiteを扱います。

確認すること:

- Suiteとは独立したcurrent Regression対象範囲を入力にする
- 対象範囲内の仕様根拠 / Risk / TR / TCN / CIがSuite member TCへ意味上閉じている
- stale / `要再検証`のTCをcurrent coverageとして数えない
- selected Runでは指定scope / Riskへ意味上閉じている
- TC → E2E実装について、E2E存在だけで十分と判定しない

feature tag不存在をcoverage gapにしません。

## 7. test-analysis拡張

既存責務の範囲で次を扱います。

### 新規・改修時

current TCが継続Regression対象か、一時的な検証かを判断します。

判断材料:

- current test objective
- Product Risk
- current scope
- 将来の変更後にも同じ検証責務を繰り返す意味があるか
- 一回限りのmigration / 調査等か

### selected Regression

入力:

- Suite snapshot
- user / project policy scope
- PR #11 impact result
- Product Risk
- 明示relationで接続された過去FAIL / Finding

出力:

- candidate
- selected
- excluded
- rationale
- residual risk

full Runではscope selectionを行いません。

## 8. qa-workflow拡張

追加責務:

- 各新規・改修完了時のSuite見直しを起動する
- membership判断結果を反映する
- user指定 → project policy → full fallbackの順でRun scopeをroutingする
- Regression activity artifactを作成する
- execution routeの担当Skillへ接続する
- Exploration / Investigation activityを記録する
- 固定保存場所または必要時の最小indexからpast activityを発見する
- candidate query不完全時に安全側へroutingする

`qa-workflow`自身はmembershipの意味判断、Risk、coverage、E2E sufficiencyを再判定しません。

## 9. Portability

各既存Skillは単体利用時にRegression Suite / relation indexを必須にしません。

統合workflowでのみSuite / Activityを利用します。

relation indexが実装されない場合でも、Regression / Exploration / Investigation workflowが成立することを必須条件にします。
