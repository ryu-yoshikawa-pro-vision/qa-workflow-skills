# QA Artifact Graph / Harness 導入Plan

## 1. Graph schema v1

machine-readable schema versionを`qa-artifact-graph-v1`とします。

Graph JSONの最小形:

```json
{
  "schema_version": "qa-artifact-graph-v1",
  "build": {
    "source_manifest_ref": "...",
    "source_artifact_count": 0
  },
  "nodes": [],
  "edges": [],
  "issues": []
}
```

Graph JSONは派生成果物であり、担当Skill成果物へ書き戻しません。

## 2. Node種別

v1は次だけを正規node typeとします。

### Knowledge / Design

- `change`
- `specification`
- `decision`
- `assumption`
- `question`
- `product_risk`
- `test_requirement`
- `test_condition`
- `coverage_item`
- `test_case`

### Target / Testware

- `test_target_snapshot`
- `testware`

### Activity / Execution

- `qa_activity`
- `execution`
- `result`
- `evidence`
- `finding`

新しいnode typeをruntime入力から自由生成しません。追加はschema version変更を伴う明示実装とします。

## 3. QA Activity / Regression Suite

`qa_activity`はRegression / Exploration / Investigationを後から参照するための活動成果物からprojectionします。optionalなworkflow stateだけを正本にしません。

`activity_type`の正規値:

- `regression`
- `exploration`
- `investigation`

新規・改修の通常設計は既存`qa-workflow`を正本とし、PR #13のactivity成果物を必須にしません。新規・改修セッションで確定したTCはRegression Suite更新時にsource artifact refを保持します。

Regression SuiteはGraph nodeを正本にせず、project-localなsuite成果物を正本とします。Suiteは機能タグ一覧、current member TC、明示的な除外理由を持ちます。Graph / Harnessはその内容を読み取る消費者です。

Regression / Exploration / Investigation成果物はproject-localなactivity indexへ登録し、過去成果物の発見経路を固定します。汎用artifact registryは追加しません。

## 4. identity contract

### 4.1 既存stable IDを持つEntity

PR #11 merge後の既存identityをそのまま使用します。

例:

- SPEC / DEC / ASM等の既存仕様系identity
- `TR-...`
- `TCN-...`
- `TCN-...-CI...`
- `TC-...`
- `model_key`
- Machine Entityの`(skill, entity_type, entity_ref)`

Graph Harnessはこれらを再採番・semantic matchingしません。

### 4.2 PR #12 test-execution

PR #12の次の契約を維持します。

- `test_case_ref`は成果物snapshot内ローカル
- `source_test_case_id`は入力元identity
- 入力identityがなくてもfingerprintを新設しない
- 再実行は別artifact / version

Graphでは`test_case_ref`単独をglobal identityにしません。

内部参照は次のscopeで解決します。

```text
<source_artifact_ref> + <test_case_ref>
```

`source_test_case_id`が重複してもGraph Harnessが改名しません。

### 4.3 Graph内部node_key

Graph JSON内のedge参照用に内部`node_key`を持てます。

規則:

1. 既存canonical identityがある場合はtype + canonical refから生成
2. artifact-local identityしかない場合はartifact_ref + local_refから生成
3. URL / path等は固定percent-encodingでエンコード
4. content hashは使わない
5. node_keyはGraph内部identityであり正式QA IDではない
6. 同一build入力から同一node_keyを得る
7. collisionは`invalid_graph_input`

## 5. Edge契約

v1ではedge方向を固定し、Agent / adapterが都度解釈しません。

| Edge | From → To | 意味 |
| --- | --- | --- |
| `derived_from` | 派生物 → 根拠 / 起点 | FromはToから導出された |
| `supersedes` | 新しいnode → 置換対象node | FromがToを明示的に置換する |
| `depends_on` | 依存元 → 依存先 | Fromの成立にToが必要 |
| `covers` | 下流coverage node → 上流対象 | FromがToをcoverageする |
| `verifies` | test_case → coverage_item / test_condition / test_requirement | TCがToを検証する |
| `implemented_by` | test_case → testware | TCが当該testwareで実装される |
| `triggered_by` | qa_activity → change / finding / question | Activity開始の起点 |
| `selected_for` | test_case / testware → qa_activity | 対象がActivityへ選定された |
| `executed_in` | test_case / testware → execution | 対象がExecutionで実行された |
| `executed_against` | execution → test_target_snapshot | Execution対象の実環境 / 実対象snapshot |
| `evidenced_by` | result / finding → evidence | 判定 / Findingの証拠 |
| `produced` | qa_activity → execution、execution → result / finding | 実行・結果の生成関係 |
| `blocks` | question / finding → qa_activity / test artifact / execution | 未解決対象がToをblockする |
| `resolves` | decision / result / finding → question / finding | FromがToを解消した |

`clarifies` / `resolved_by`のような逆向き同義edgeはv1では追加しません。同じ関係を両方向edgeで重複保持せず、必要な逆探索はquery側で行います。

edgeごとに許可source/target node typeをschemaへ固定します。

名称類似、同一画面、同一単語だけを理由にedgeを自動生成しません。

## 6. query / impact規則

設計成果物のimpact traversalはPR #11の`change_impact.py` / traceability runtimeを正本とします。PR #13のHarnessがSPEC → TR → TCN → CI → TCを独自計算しません。

PR #13が行うのは、PR #11が返したcurrent TC / relationを起点に、必要な場合だけ次へ接続することです。

- TC → current E2E testware
- TC / testware → Regression activity selection
- execution → result / evidence
- Finding → follow-up Question / Risk / Test Condition / Test Case

過去FAIL / Findingを部分Regressionの参考にする場合も、文字列類似や「同じ画面」等をHarnessが推測しません。明示relationだけを機械的候補として返し、意味上の関連判断は`test-analysis`へ残します。

query結果は`complete`を持ちます。unsupported artifact、unmapped relation、dangling ref等により候補集合の完全性を保証できない場合は`complete=false`とし、空集合を「影響なし」と解釈しません。

## 7. PR #11 / #12との関係

### PR #11

- Machine Entity identityをそのまま使用する
- design dependency / traceability / change impact / freshnessを再計算しない
- `depends_on / traces_to / derived_from`等の既存明示relationは、cross-artifact queryに必要な範囲だけprojectionする
- PR #11 runtimeと異なるstateをGraph側で生成しない

### PR #12 / E2E

- `test_case_ref`はartifact-localのまま保持する
- `source_test_case_id`をglobal keyへ昇格しない
- execution / result / evidence / rerunの事実を再判定しない
- current executionかhistorical executionかはsource artifactのrevision / previous ref / lifecycleから読み取る

## 8. source state / history

Graph独自の`graph_state`は追加しません。

- design freshness / stale / 要再検証 → PR #11
- workflow block / completion → `qa-workflow`
- execution result / rerun / cleanup → PR #12 / E2E
- Regression Suite current membership → Regression Suite成果物
- activity history → immutableなactivity成果物 + activity index

Harnessはこれらのsource stateをviewへ表示できますが、別state machineとして上書きしません。

過去Result / Findingは履歴として保持し、current runへコピーして今回実行扱いにしません。

## 9. Regression selectionの安全条件

部分Regressionでrelation / impact候補を利用する場合、次のいずれかがあれば候補集合を完全と扱いません。

- PR #11 impact resultが未検証 / unavailable
- unsupported artifactがある
- current Suite memberに機能タグがない
- changed scopeとSuite feature scopeの対応が未解決
- dangling / unmapped relationがある
- current TC / testwareのfreshnessが不明

`complete=false`の候補集合だけを根拠にscopeを狭めません。`test-analysis`は明示ユーザーscope、機能タグによる広い範囲、または全件Regressionへ安全側に閉じます。

## 10. Graphに保存しないもの

- secret実値
- cookie / token / storageState実値
- screenshot本体
- trace本体
- 生の個人情報
- LLM chain-of-thought
- source artifact本文全文

Graphは参照・identity・状態・必要最小metadataだけを保持します。
