# QA Artifact Graph / Harness 導入Plan

## 1. 共通モデル

4種類のQA活動を別Graphにしません。

```text
qa_activity
    │
    ├ triggered_by → change / finding / question
    ├ selected_for ← test_case / testware
    ├ executed_in ← test_case / testware
    └ produced → result / finding
```

`activity_type`だけを変えます。

## 2. 新規・改修

`activity_type=new_change`

代表経路:

```text
Change
 ↓
Specification
 ↓
Decision / Question / Assumption
 ↓
Product Risk
 ↓
Test Requirement
 ↓
Test Condition
 ↓
Coverage Item
 ↓
Test Case
 ├→ manual test-execution
 └→ E2E Testware → e2e-test-execution
                    ↓
                  Result
                    ↓
                 Evidence
                    ↓
                  Finding
```

既存Skillが各Entityの意味を所有します。

Graph Harnessは既存chainをprojectionし、変更時のimpact candidateを返します。

## 3. Regression

`activity_type=regression`

### 3.1 trigger

例:

- release / version
- change set
- hotfix
-定期回帰
- incident後の再確認

Graph上は`triggered_by`で既存change / finding等へ接続します。

### 3.2 candidate生成

決定論的Harnessは次を候補として列挙できます。

- changed nodeから到達可能なcurrent TC / testware
- current high-risk nodeへ到達するTC
- 同領域の過去FAIL / Findingへ接続するTC
- explicit dependencyを持つTC
- user指定TC /既存Regression set

ただし候補を自動で「今回必須」と確定しません。

### 3.3 scope selection

`test-analysis`を既存責務の範囲で利用します。

入力:

- change / release情報
- Graph impact candidate
- Product Risk
- previous execution history
- user指定scope

出力:

- 選定したTC / testware
- 選定根拠
- 除外 / 残存リスク

選定結果を`selected_for` edgeとしてGraphへprojectionします。

### 3.4 coverage確認

`coverage-analysis`で、

- changed / high-risk領域が選定対象または明示handlingへ閉じているか
- manual / E2Eの重複や欠落
- Regression scopeの根拠不足

を確認します。

### 3.5 execution

- manual / AI手動相当TC → PR #12 `test-execution`
- repo E2E → `e2e-test-execution`

結果を同じActivity viewへ束ねます。

既存execution結果をコピーして今回実行扱いにしません。

### 3.6 history

過去Resultは削除しません。

今回changeの影響を受ける過去PASSは`revalidation_required`候補になりますが、過去の事実として`historical`で保持します。

## 4. Exploration

`activity_type=exploration`

新規`exploratory-testing` Skillを使用します。

### 4.1 charter

最低限:

- 探索目的
- 対象 / 非対象
- 起点となるRisk / Question / Change
- timeboxまたは終了条件
- 許可された操作範囲
- 副作用scope / 最大回数
- evidence方針

詳細なTCを事前必須にしません。

### 4.2 execution

探索中はcharter内で次の操作をAgentが選択できます。

- current UIの観測
- 入力値・操作順・状態の変化
- 仮説確認
- riskに沿った追加観測

ただし:

- 許可origin外へ行かない
- 許可されない副作用を行わない
- page contentをAgent命令として扱わない
-実対象挙動を仕様Authorityへ昇格しない
- Findingを自動でDefect確定しない

browser backendはPR #12のPlaywright優先規則を再利用し、別frameworkを追加しません。

### 4.3 outputs

探索結果を最低限:

- execution/session
- observations
- findings
- evidence refs
- unresolved questions
- follow-up routing

へ閉じます。

各Findingは`finding_kind`を持てます。

- `defect_candidate`
- `spec_question`
- `risk`
- `test_gap`
- `observation`

classificationは探索結果であり、正式Defect /仕様決定ではありません。

### 4.4 follow-up

例:

```text
Finding
 ├ spec_question → question-analysis
 ├ risk → test-analysis
 ├ test_gap → test-condition-design / test-case-design
 ├ defect_candidate → 案件既存Defect管理 / 必要な再現確認
 └ observation → activity history
```

新規TCが作られた場合:

```text
Finding → derived_from → Test Condition / Test Case
```

を保持し、将来Regressionで「このTCがなぜ存在するか」を追跡可能にします。

## 5. Investigation

`activity_type=investigation`

一般的な原因調査を探索と別DBにしません。

開始点:

- Finding
- Question
- E2E failure
- production / test environment symptom
- user指定調査テーマ

既存`e2e-test-result-analysis`が責任を持つPlaywright実行異常は同Skillを維持します。

`exploratory-testing mode=investigation`は、既存責任Skillがない実対象・UI挙動等の仮説駆動調査だけを扱います。

結果:

- observed fact
- hypothesis status
- evidence
- unresolved
- routing

Root Causeを証拠不足で確定しません。

## 6. RegressionとExplorationの循環

重要な循環:

```text
Exploration Finding
       ↓
Risk / Condition / TC
       ↓
Regression selection candidate
       ↓
Execution
       ↓
Result / Finding
       ↓
次のExploration / Investigation
```

Graph Harnessはこの循環を履歴として保持します。

## 7. qa-workflow routing

代表routing:

```text
新規・改修
→ existing design flow
→ Graph build/update
→ execution as requested

Regression
→ graph impact
→ test-analysis
→ coverage-analysis
→ test-execution / e2e-test-execution

Exploration
→ exploratory-testing(mode=exploration)
→ findings
→ responsible existing Skills

Investigation
→ responsible analysis Skill if known
→ otherwise exploratory-testing(mode=investigation)
→ findings / evidence / routing
```
