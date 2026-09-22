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

## 5. Edge種別

v1の正規edge typeは次だけとします。

- `derived_from`
- `clarifies`
- `resolves`
- `supersedes`
- `depends_on`
- `covers`
- `verifies`
- `implemented_by`
- `triggered_by`
- `selected_for`
- `executed_in`
- `executed_against`
- `evidenced_by`
- `produced`
- `blocks`
- `resolved_by`

edgeごとに許可source/target node typeをschemaへ固定します。

名称類似、同一画面、同一単語だけを理由にedgeを自動生成しません。

## 6. PR #11 change impact graphとの関係

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

## 7. currentness / history

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
- explicit invalidation / rerun requirementを持つ
- Regression activityが再確認対象として選定した

Graph traversalだけで「内容が誤っている」と断定しません。

### historical

過去run / 過去version / 確定済み旧execution等。

履歴nodeを削除しません。

### superseded

明示`supersedes`関係または正本契約が置換済みとしたものだけ。

### blocked

正本側でblock中、または必須参照が未解決。

## 8. 変更伝播

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

## 9. Graphに保存しないもの

- secret実値
- cookie / token / storageState実値
- screenshot本体
- trace本体
- 生の個人情報
- LLM chain-of-thought
- source artifact本文全文

Graphは参照・identity・状態・必要最小metadataだけを保持します。
