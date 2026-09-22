# QA Artifact Graph / Harness 導入Plan

## 1. 実装場所

Harnessは新しいuser-facing Skillにせず、`qa-workflow`の決定論的補助runtimeとして実装します。

予定:

```text
skills/qa-workflow/
├── assets/
│   ├── regression-suite-template.md
│   ├── qa-activity-template.md
│   ├── qa-activity-index-template.md
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
            ├── regression_suite.py
            ├── qa_activity.py
            └── exploratory_testing.py
```

PR #11側の各SkillごとにGraph adapterを重複実装せず、Machine Entity / canonical traceabilityを設計側の共通入力境界にします。

## 2. CLI

入口は1つに固定します。

```bash
python skills/qa-workflow/scripts/qa_graph/run.py <operation>
```

operation:

- `build`
- `validate`
- `query`
- `activity-view`
- `regression-suite-view`

`coverage-view`は追加しません。設計coverageは`coverage-analysis` / PR #11 traceabilityを正本とし、Regression実行のselected-but-not-executed等はactivity / suite validatorで検査します。

## 3. source manifest / activity index

source manifestは**今回のbuild input一覧**に限定します。正本や汎用artifact registryにしません。

qa-workflowは次からmanifestを作ります。

- project contextのcurrent QA成果物
- current Regression Suite
- project-local activity indexが指すRegression / Exploration / Investigation成果物
- 必要なPR #11 / PR #12 / E2E成果物

過去activityを発見するため、別にproject-localなactivity indexを持ちます。最小項目は次です。

```text
activity_ref
activity_type
artifact_ref / path
release / version（利用可能な場合）
completed_at（利用可能な場合）
```

activity indexは活動成果物の所在を列挙するだけで、TC、Result、Finding本文や独自lifecycleを複製しません。

## 4. adapter方針

自由文を汎用LLM parserでGraph化しません。

優先順位:

1. PR #11のMachine Entity / canonical traceability
2. Regression Suite machine block
3. PR #12のstructured execution / result
4. E2E Skillの既存structured result / testware ref
5. `exploratory-testing` / `qa_activity`のmachine block

一意に抽出できないrelationは推測せずissue化し、query結果を`complete=false`にできます。

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

## 7. query

`query`は保存済みの明示relationを順方向 / 逆方向へ検索します。

主な用途:

- TC → testware → execution history
- Regression activity → selected TC / testware → execution / result
- Finding → follow-up artifact
- PR #11 impact candidate → testware / past activity

design impactそのものはPR #11の結果を入力として利用し、Harnessが独自に再計算しません。

出力には、候補、path、distance、relation chain、source artifact refs、`complete`を含めます。

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

## 9. regression-suite-view

current Regression Suiteについて次を機械的に表示 / 検査します。

- feature tag一覧
- feature tag別member TC
- untagged member
- duplicate member
- current TCへ解決できないmember
- explicit exclusionと理由
- suite snapshot revision / source ref

「各機能が意味上十分にテストされているか」はここで判定せず、`coverage-analysis`を正本とします。

Regression activityについては別validatorで次を検査します。

- full runがcurrent Suite snapshotの全memberを選択している
- selected runがsnapshotのsubsetである
- selected runをfull扱いしていない
- selected memberにexecutionまたは明示未実行理由がある

## 10. 再生成性

同一source manifest、同一source artifact bytes、同一Harness versionから同一canonical graph JSONを得ることをcontract testにします。

Graph cacheを正本にしません。

source変更後は再buildします。

## 11. Harness version

Graph schema versionとHarness contract versionを持たせます。

repo内実装revisionを識別できる既存commit / source revisionが利用できる場合はそれを使用し、独自の意味Entity fingerprint体系は作りません。



Graph出力へ次を持たせます。

- graph schema version
- harness contract version
- implementation fingerprintまたは既存repoで採用済みの同等identity方式

PR #11のruntime fingerprint helperを無条件に流用しません。実装時に同helperがGraph Harnessへ意味的に適用可能な契約になっている場合だけ、重複実装回避として利用可否を確認します。利用できない場合はGraph Harness自身のversion文字列を固定し、新たな意味Entity fingerprint体系を作りません。
