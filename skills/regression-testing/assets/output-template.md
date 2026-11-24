# Regression artifact output

正規machine artifactはMarkdown内にJSON code blockをちょうど1つ置き、`artifact_type`を`baseline` / `run` / `activity`のいずれかにします。Baselineの初期形は`assets/baseline-template.json`を使い、`complete`を4つの`completeness_evidence`から導出します。Runではbaseline snapshot / currentness、scope、selected TC、required route（`manual` / `e2e` / `testware`）、TCなし補助testware（`completion_required`付きの`auxiliary_routes`）を分けます。Activityではidentityと固定snapshot、source execution、routeごとのactual start / result-finalization fact / raw result、補助routeのattempt / raw取得完全性、cleanup、unresolvedを保持します。各kindのfieldとprojectionは`references/data-contract.md`に記載します。

```json
{
  "artifact_type": "baseline | run | activity"
}
```

この短い例はartifact discriminatorだけを示します。実際のartifactでは、選んだkindに対応する上記template / data contractのfieldを含めます。source execution resultを再分類せず、preflightやartifact存在だけでactual startを推定しません。
