# QA Artifact Graph / Harness 導入Plan

## 1. 実装場所

Graph Harnessは新しいuser-facing Skillにせず、`qa-workflow`の決定論的補助runtimeとして実装します。

予定:

```text
skills/qa-workflow/
├── SKILL.md
├── references/
│   └── ...
├── assets/
│   ├── ...
│   └── qa-graph-source-manifest-template.json
└── scripts/
    └── qa_graph/
        ├── run.py
        ├── model.py
        ├── extract.py
        ├── validate.py
        ├── query.py
        └── adapters/
            ├── machine_entities.py
            ├── test_execution.py
            ├── e2e_execution.py
            └── exploratory_testing.py
```

ファイル数は実装時に責務が小さい場合は統合してよく、上記構成を増やすこと自体を目的にしません。

## 2. CLI

入口は1つに固定します。

```bash
python skills/qa-workflow/scripts/qa_graph/run.py <operation>
```

operation:

- `build`
- `validate`
- `impact`
- `activity-view`
- `coverage-view`

別CLIを増やしません。

## 3. source manifest

Graph Harnessはrepoや外部保存先を無制限crawlしません。

qa-workflowが今回利用する正本成果物をsource manifestへ列挙します。

例:

```json
{
  "schema_version": "qa-artifact-graph-source-v1",
  "artifacts": [
    {
      "artifact_ref": "project://qa/spec-analysis/v3",
      "skill": "spec-analysis",
      "path": "/safe/path/spec-analysis.md",
      "revision": "provided-or-null",
      "lifecycle": "current"
    }
  ]
}
```

規則:

- `artifact_ref`は入力元が既に持つ参照を優先する
- repo pathを利用する場合はそのpath + refを明示する
- identityがない外部成果物へhashを新設しない
- 同一manifest内でartifact_ref重複を拒否
- secret path / secret valueをmanifestへ入れない
- lifecycleは`current / historical / superseded`

## 4. adapter方針

自由文を汎用LLM parserでGraph化しません。

固定adapterで既知machine-readable情報を読みます。

優先順位:

1. PR #11 merge後のMachine Entity / canonical machine evidence
2. PR #12 merge後のstructured YAML / fixed result tables / explicit refs
3. E2E Skillの既存structured result / ID contract
4. `exploratory-testing`の本Planで追加するmachine-readable activity output
5. machine-readable情報がない成果物は、既存deterministic parserで安全に一意抽出できる項目だけ

一意抽出できない関係はGraph edgeへ推測追加しません。`unresolved_graph_relation`としてissue化できます。

## 5. build

`build`は次の順序を固定します。

1. manifest schema検証
2. artifactをmanifest順ではなく`artifact_ref` canonical sortで処理
3. skill / artifact typeに対応する固定adapter選択
4. nodes抽出
5. edges抽出
6. node identity canonicalization
7. edge canonicalization
8. duplicate検出
9. lifecycle / currentness projection
10. graph全体validate
11. canonical sort
12. JSON出力

LLMはbuild pathへ入りません。

## 6. validate

最低限:

- schema version
- node type
- edge type
- node_key一意
- edge key一意
- dangling source / target
- source/target type compatibility
- artifact-local ref scope
- canonical ID format
- PR #11 Machine Entity identity整合
- PR #12 `artifact_ref + test_case_ref` scope整合
- supersedes self-loop禁止
- derived_from self-loop禁止
- 明示的にacyclicとするdesign edge集合のcycle検出
- current nodeがsuperseded-only sourceへ依存していないか
- secret-like field名をgraph schemaに含めていないか

Graph全体をDAGとは仮定しません。`selected_for / executed_in / produced / evidenced_by / resolves`等は活動・履歴を表すため、cycle禁止は仕様→設計→TCの意味上DAGであるedge subsetだけへ限定します。

## 7. impact

入力:

- changed node refs
- traversal policy（v1は`design-impact`を正規値とし、自由定義しない）
- max depth（省略時はschema定義）

`design-impact`のedge方向はGraph contractの固定表だけを使用します。Agentがedge typeごとの順方向 / 逆方向を選択しません。

出力:

- reachable candidates
- path
- distance
- edge chain
- source activity / artifact refs

Graph Harnessは候補をrisk score順等へ勝手に並べ替えません。riskは既存Product Riskを属性として返せますが、selectionは`test-analysis`の責務です。

## 8. activity-view

`qa_activity`を中心に、次をprojectionします。

- trigger
- selected requirements / conditions / test cases / testware
- target snapshot
- executions
- results
- evidence refs
- findings
- unresolved / blocked
- historical reruns

Regression、Exploration等の専用DBを作りません。

## 9. coverage-view

既存`coverage-analysis`を置換しません。

Harnessは機械的な候補だけ返します。

- orphan Test Case
- Test Requirementから到達不能なTC
- selected_forされたのにexecutionがない対象
- Resultにevidence refが必要な契約なのに欠落
- historical executionしかないTC
- current Test Caseがdeleted / superseded upstreamだけへ閉じている
- Findingからfollow-up edgeがない候補

意味上十分なcoverageかは`coverage-analysis`が判定します。

## 10. 再生成性

同一source manifest、同一source artifact bytes、同一Harness versionから同一canonical graph JSONを得ることをcontract testにします。

Graph cacheを正本にしません。

source変更後は再buildします。

## 11. Harness version

Graph出力へ次を持たせます。

- graph schema version
- harness contract version
- implementation fingerprintまたは既存repoで採用済みの同等identity方式

PR #11のruntime fingerprint helperを無条件に流用しません。実装時に同helperがGraph Harnessへ意味的に適用可能な契約になっている場合だけ、重複実装回避として利用可否を確認します。利用できない場合はGraph Harness自身のversion文字列を固定し、新たな意味Entity fingerprint体系を作りません。
