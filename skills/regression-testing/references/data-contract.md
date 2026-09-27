# Regression data contract

Production helperはPR #11 ownerが解決したcurrent TCデータと保存先が返したsource revisionを入力として受け取ります。PR #11 Machine Entity、execution artifact、E2E run artifactそのもののparser / identity / freshnessは複製しません。

## Discovery snapshot input

```json
{
  "discovery_roots": ["qa/test-cases"],
  "listing_complete": true,
  "source_revisions": [{"source_ref":"repo:path", "revision":"opaque-token"}],
  "cases": [{
    "tc_ref":"machine-entity-ref",
    "source_ref":"repo:path",
    "source_revision":"opaque-token",
    "lifecycle_status":"current",
    "content_fingerprint":"owner-produced-value"
  }]
}
```

`lifecycle_status`はownerからの`current` / `unresolved` / `stale` / `deleted` / `superseded` projectionです。helperは値を検証し、PR #11の意味を再計算しません。

## Baseline / Run / Activity input

Membership decisionには`tc_ref`, `decision` (`member`, `one_off`, `out_of_scope`, `unresolved`), `reason`, source refs / revisionsが必要です。Run routeは`manual`またはconcrete `e2e_ref`のいずれかです。Activity route resultにsource artifact ref、source start state、owner execution contractが返す`actual_start_confirmed`と`result_finalized`、source outcome、evidence refsを保持します。source result stringはsource artifactの値をそのまま保持し、新しいRegression taxonomyへ変換しません。

`executed`はrequired routeのactual startだけから判定します。Activity `完了`には、全required routeのactual start確認、owner側result finalization、source result / outcomeのraw projection、必要cleanupの閉鎖、unresolvedなしを別々に確認します。result finalizationはsource contractから渡される事実であり、Regressionはresult文字列から推測しません。

`complete`はroot listingが完全、source revisionsが取得でき、discovery TCが全件lifecycle-resolved、membership判定が全件完了した場合だけtrueです。coverage gapは別項目です。
