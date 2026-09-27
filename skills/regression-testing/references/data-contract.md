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

## 正規artifactのfield

全artifactは`artifact_type`を`baseline` / `run` / `activity`のいずれかにします。Baselineは`assets/baseline-template.json`で定義する`schema_version`も持ちます。

- **Baseline**: `assets/baseline-template.json`をfieldの一覧と初期値の正本にします。currentnessに使う`scope_identity`は空でないscope identity、`source_revisions`は`source_ref` / `revision`の組の一覧です。どちらかの値が欠落・不正で照合できない場合、currentnessを`current`にしません。`memberships`にTC decision（`member` / `one_off` / `out_of_scope` / `unresolved`）を記録し、`member_tc_refs`は`lifecycle_status == "current"`かつ`decision == "member"`のref、`one_off_tc_refs`は`decision == "one_off"`のrefをそれぞれ重複なく投影します。full Run planningは`member_tc_refs`全件を使い、欠落・不正型・membershipとの不一致は使用可能なcomplete Baselineとして扱いません。`completeness_evidence`には`root_listing_complete`、`source_revisions_complete`、`lifecycle_resolved`、`membership_decisions_complete`を持たせ、4値すべてが`true`の場合だけ`complete`を`true`にします。`coverage_gaps`をinventory / lifecycle不完全と混ぜません。
- **Run**: `run_scope`、baselineの`complete` / `currentness` / `member_tc_refs`、`selected_tc_refs`、`suite_complete`、`required_routes`を保持します。routeは`manual`または具体的E2E testware ref付き`e2e`です。TCなし補助testwareは`auxiliary_testware_refs`と`auxiliary_testware_count`に分けます。
- **Activity**: `activity_ref`、`snapshot_ref`、`scope_identity`、`activity_state`、`source_executions`、`route_results`、`tc_execution_state`、`counts`、`cleanup_status`、`unresolved`を保持します。TCなし補助testwareがあれば`auxiliary_route_results`と補助件数へ分けます。各routeのactual start、result finalization、source result / outcomeのraw valueをowner sourceから投影します。
