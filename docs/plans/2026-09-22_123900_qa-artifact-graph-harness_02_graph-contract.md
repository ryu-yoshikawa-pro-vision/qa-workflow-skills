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

## 3. QA Activity

`qa_activity`はQA業務を束ねる共通nodeです。

`activity_type`の正規値:

- `new_change`
- `regression`
- `exploration`
- `investigation`

活動種別ごとに別Graphを作りません。

最小machine field:

```json
{
  "node_type": "qa_activity",
  "activity_type": "regression",
  "source_artifact_ref": "...",
  "status": "active"
}
```

案件が既存Activity IDを持つ場合は保持できます。存在しない場合に正式IDを創作しません。

`qa_activity`の正本を新規registryにせず、`qa-workflow`の既存workflow state / project context等の成果物からprojectionします。既存assetでactivity_type等を保持できない場合だけ、そのassetへ最小fieldを追加します。独立したactivity DBは追加しません。

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

## 6. impact traversal規則

edgeの保存方向と変更影響の伝播方向を分離します。

`design-impact` queryでは次を固定します。

| Edge | 変更起点からの伝播 |
| --- | --- |
| `derived_from` | To変更 → 逆向きにFromへ |
| `depends_on` | To変更 → 逆向きにFromへ |
| `covers` | To変更 → 逆向きにFromへ |
| `verifies` | To変更 → 逆向きにtest_caseへ |
| `implemented_by` | test_case変更 / 要再検証 → 順方向にtestwareへ |
| `supersedes` | 旧nodeをcurrent候補として使わないためのlifecycle判断に使用し、通常の下流impact traversalへ直接混ぜない |
| activity / execution / evidence系edge | design-impactでは自動伝播しない |

Regression historyや過去FAILを調べる場合は別`activity-history` / `coverage-view` queryでactivity / execution / evidence系edgeを辿ります。

これにより、履歴edgeを通じて過去Resultから設計成果物へ無制限にimpactが逆流することを防ぎます。

## 7. PR #11 change impact graphとの関係

PR #11の`test-analysis` change impact graphは局所graphとして維持します。

PR #11で許可された:

- `depends_on`
- `traces_to`
- `derived_from`

を本Graphへprojectionするとき:

- `depends_on` → `depends_on`
- `derived_from` → `derived_from`
- `traces_to` → source/targetの意味がv1 edgeへ一意に対応できる場合だけ固定mapping。対応不能ならlocal graph参照として保持し、global edgeを推測生成しない

PR #11の`change_impact.py`をglobal Graph Harnessへ移植・削除しません。

## 8. currentness / history

Graph上の派生状態`graph_state`:

- `current`
- `revalidation_required`
- `blocked`
- `historical`
- `superseded`
- `unknown`

これは元成果物のstatusを上書きしません。

### current

current source artifactから抽出され、既知の再検証要求がない。

### revalidation_required

次のいずれかの候補:

- current upstreamのidentity / content version変更により到達可能な下流
- PR #11 runtimeが要再検証としたEntity
- explicit rerun / revalidation requirementを持つ
- Regression activityが再確認対象として選定した

Graph traversalだけで「内容が誤っている」と断定しません。

### historical

過去run / 過去version / 確定済み旧execution等。

履歴nodeを削除しません。

### superseded

明示`supersedes`関係または正本契約が置換済みとしたものだけ。

### blocked

正本側でblock中、または必須参照が未解決。

## 9. 変更伝播

変更伝播は2段階とします。

```text
deterministic reachability
        ↓
impact candidates
        ↓
responsible Skill semantic review
        ↓
current / revalidation / updated
```

Harnessは候補集合を返します。

例:

```json
{
  "changed": ["specification:SPEC-023"],
  "candidates": [
    {"node_key":"test_requirement:TR-014","distance":1},
    {"node_key":"test_condition:TCN-052","distance":2},
    {"node_key":"test_case:TC-087","distance":3}
  ]
}
```

意味上の影響がないと責任Skillが確認したnodeを、Harnessだけの判断で更新対象へ戻し続けません。確認結果を次回入力のexplicit closureとして参照できる契約を設けます。

## 10. Graphに保存しないもの

- secret実値
- cookie / token / storageState実値
- screenshot本体
- trace本体
- 生の個人情報
- LLM chain-of-thought
- source artifact本文全文

Graphは参照・identity・状態・必要最小metadataだけを保持します。
