# Regression artifact output

正規machine artifactはMarkdown内にJSON code blockをちょうど1つ置きます。baselineには`assets/baseline-template.json`のfieldを使い、`complete`とその根拠を一致させます。Runでは`artifact_type: "run"`とbaseline snapshot/currentness、selected scope、required route、TCなし補助testwareを分離します。Activityでは`artifact_type: "activity"`とsource execution ref、owner-confirmed actual start、owner result-finalization fact、raw source result / outcomeの投影可能性、cleanup、unresolvedを保持します。

```json
{
  "artifact_type": "baseline | run | activity",
  "schema_version": "1"
}
```

この短い例はartifact discriminatorだけを示します。実際のartifactでは、選んだkindに必要なPlan記載の全fieldを含めます。source execution resultを再分類せず、preflightやartifact存在だけでactual startを推定しません。
