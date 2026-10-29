# Regression artifact output

正規machine artifactをmaterializeできる場合だけ、Markdown内に正規JSON code blockをちょうど1つ置き、`artifact_type`を`baseline` / `run` / `activity`のいずれかにします。必要なidentityやprovenanceがなく正規schemaを満たせない場合は、block理由を文章で示し、`artifact_type`付きの部分JSONや`materialization_status: blocked`をartifactとして出力しません。Baselineの初期形は`assets/baseline-template.json`を使い、`complete`を4つの`completeness_evidence`から導出します。Runではbaseline snapshot / currentness、scope、selected TC、required route、TCなし補助testwareを分けます。Activityではidentityと固定snapshot、source execution、routeごとのactual start / result-finalization fact / raw result、cleanup、unresolvedを保持します。各kindのfieldとprojectionは`references/data-contract.md`に記載します。

次のJSONブロックは、必須のidentity・provenanceを含む正規artifactをmaterializeできた場合の形の例です。preflightでmaterializeできない場合は、理由と再開条件を文章で示し、JSON fenced blockを一切出力しません。

```json
{
  "artifact_type": "activity",
  "source_executions": {
    "<execution_ref>": { "start_state": "owner source value" }
  },
  "route_results": [],
  "tc_execution_state": { "<tc_ref>": "executed | blocked | unexecuted" },
  "counts": { "auxiliary_testware_count": 0 },
  "auxiliary_route_results": [],
  "unresolved": []
}
```

上記のActivity用fieldは形の説明例です。選んだkindに対応するdata contractのfieldと型を使います。Activityの`source_executions`と`tc_execution_state`はobject、`route_results`と`auxiliary_route_results`は配列、`counts`はobjectです。source execution resultを再分類せず、preflightやartifact存在だけでactual startを推定しません。
