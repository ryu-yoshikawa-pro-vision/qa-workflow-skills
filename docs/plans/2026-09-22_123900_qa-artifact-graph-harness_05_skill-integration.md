# Regression Suite / QA Activity 統合Plan

## 1. 既存Skillとの関係

| Skill / runtime | PR #13で利用する内容 |
| --- | --- |
| PR #11 Machine Entity / traceability | design identity / lifecycle / impact / freshnessの正本 |
| `test-analysis` | 継続Regression対象判断、selected scope判断 |
| `test-case-design` | current logical TC |
| `coverage-analysis` | Regression対象範囲coverage、TC → E2E実装coverage |
| `test-target-inspection` | currentな実対象情報 / UI / 既知範囲のふるまい収集 |
| `test-execution` | manual相当execution / result / evidence |
| `e2e-test-implementation` | testware |
| `e2e-test-execution` | E2E execution / result / evidence |
| `e2e-test-result-analysis` | E2E failure分析 |
| `qa-workflow` | initial baseline、Suite見直し、Activity lifecycle、routing、history discovery |
| `exploratory-testing` | Exploration / 仮説駆動Investigation |

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
- 独自currentness / membership freshness state
- Machine Entity再生成
- Graph目的のfingerprint拡張
- current / deleted / superseded相当の独自判定

PR #11がproject-wide artifact discoveryを保証するとは仮定しません。merge後の実装でcanonical inventoryが提供されていれば利用し、なければproject contextの既存QA成果物をdiscovery rootとして利用します。

## 3. project context

既存`skills/qa-workflow/assets/project-context-template.md`を拡張します。

既存欄を正本として再利用:

- §3 テスト範囲
- §8 非機能テスト範囲
- §11 対象外
- §14 既存QA成果物

新規に追加するのは、既存欄で表現できない案件固有Regression方針だけです。

- 既定Run scope / selection方針（必要な案件だけ）
- TCなしE2E等の補助Regression testware refs（必要な案件だけ）

対象機能、role、業務フロー等をRegression専用欄へ複製しません。

project context artifact ref / revisionをActivityへ保存し、後日のproject context更新後も当時の判断入力を特定できるようにします。

## 4. PR #12 / E2E

### test-target-inspection

currentな実対象情報、UI構造、既知範囲のふるまい確認を担当します。

「現在どうなっているか」を収集・更新する依頼を`exploratory-testing(mode=investigation)`へ送らないようにします。

### test-execution

- `test_case_ref`はartifact-local
- `source_test_case_id`をglobal keyへしない
- 実行時TC snapshotはPR #12を正本とする
- 再実行は別execution
- secret実値を別成果物へ複製しない

Regression Activityにはexecution refだけを保持し、TC snapshot内容を複製しません。

### E2E

TCあり / TCなしの既存経路を維持します。

TCなしE2EへSuite都合でTCを創作しません。

Regression参加はuser明示またはproject contextの補助testware方針に限定します。

## 5. exploratory-testing

### 目的

詳細TCの厳密実行と分離し、charterに基づく探索・仮説検証を行います。

### mode

- `exploration`
- `investigation`

### routing

`investigation`は、既存責任Skillがなく、未確定問題について実対象を操作しながら仮説検証する場合だけ使用します。

優先:

- currentなUI / ふるまい情報収集 → `test-target-inspection`
- 既知TC実行 → `test-execution` / `e2e-test-execution`
- E2E failure → `e2e-test-result-analysis`
- 仕様不明 → `question-analysis`
- coverage gap → `coverage-analysis` / `test-analysis`

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

## 6. Regression専用Skillを追加しない理由

Regression固有処理は既存責務で分割できます。

- membership意味判断 → `test-analysis`
- design impact → PR #11
- coverage → `coverage-analysis`
- initial baseline / Suite bookkeeping / Run routing / Activity lifecycle → `qa-workflow`
- manual execution → `test-execution`
- E2E execution → `e2e-test-execution`
- failure analysis → 既存analysis Skill

新しい`regression-testing` Skillは追加しません。

## 7. coverage-analysis拡張

確認すること:

- Suiteとは独立したcurrent Regression対象範囲を入力にする
- 対象範囲内の仕様根拠 / Risk / TR / TCN / CIがSuite member TCへ意味上閉じている
- stale / `要再検証`のTCをcurrent coverageとして数えない
- selected Runでは指定scope / Riskへ意味上閉じている
- TC → E2E実装について、E2E存在だけで十分と判定しない
- one-off TCをSuiteから外す場合、その検証責務自体がcurrent Regression対象範囲外であることを確認する

feature tag不存在をcoverage gapにしません。

## 8. test-analysis拡張

### membership

current TCが継続Regression対象か、一時的な検証かを判断します。

判断材料:

- current test objective
- Product Risk
- current Regression対象範囲
- 将来の変更後にも同じ検証責務を繰り返す意味があるか
- one-off migration / 調査等か

membership sourceの変更時は影響TCを再評価します。

### selected Regression

入力:

- baseline snapshot
- user / project policy scope
- PR #11 impact result
- Product Risk
- explicit relationで接続された過去FAIL / Finding

出力:

- candidate
- selected
- excluded
- rationale
- residual risk

selectionに実際に使ったinput artifact refs / revisionsをActivityへ渡します。

## 9. qa-workflow拡張

追加責務:

- 初回baseline reconciliationを起動する
- TC / scope / membership source変更時に必要範囲の再評価を起動する
- membership判断結果を反映する
- user指定 → project policy → full fallbackでRun scopeをroutingする
- required execution routesを担当Skillへ接続する
- Activity stateを既存workflow state語彙で管理する
- scope / snapshot不変の再開と、変更時の別activity / versionを分ける
- project context / fixed root / 必要時indexからpast activityを発見する
- candidate query不完全時に安全側へroutingする

`qa-workflow`自身はmembershipの意味判断、Risk、coverage、E2E sufficiencyを再判定しません。

## 10. Portability

各既存Skillは単体利用時にRegression Suite / Activity / relation indexを必須にしません。

relation indexが実装されない場合でも、Regression / Exploration / Investigation workflowが成立することを必須条件にします。
