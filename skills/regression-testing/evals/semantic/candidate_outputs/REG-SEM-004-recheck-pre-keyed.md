# Regression Activity: TC-301 Run結果更新

## 判断理由

- TC-301の必須routeは`manual`とE2E testware `E2E-55`の2つです。executedと数えられるのは全required routeのactual startが確認できた場合だけです。
- manual routeは`scenario.when`の操作が開始済みで、owner execution contractが`result_finalized=true`、raw result `FAIL`を返しています。Regressionは`FAIL`を再判定せず、そのまま投影します。開始済みなので、FAILでもmanual routeのexecutedの事実とは両立します。
- E2E `E2E-55`はartifactが存在しますが、preflightでblockedになり、actual attemptは未開始（`actual_start_confirmed=false`）で`result_finalized=false`です。artifactの存在やpreflight通過状況だけでは開始扱いにしません。そのため、E2E routeはexecutedに数えません。
- 全required routeのactual startが揃っていないため、TC-301はlogical TCとしてexecutedにしません。manualのFAILやmanualの開始実績をTC全体の実行完了の代替にもしません。
- Activityの`完了`には、全required routeの開始、result確定、cleanup閉鎖が必要です。E2E-55は未開始でblockedのままなので`完了`にできません。manual routeは開始済みで必須義務があるため、`activity_state`は`部分完了（ブロック中あり）`にします。
- E2E-55のcleanup状態は入力にないため推測せず、`unresolved`に残します。blockedの解除、またはE2E-55のactual attemptの開始・結果確定が、scope・snapshotを変えないresumeの条件です。
- `activity_ref`、`snapshot_ref`、`scope_identity`、source artifact refは入力に出所がないため推測せず、未解決として記録します。

## Failure feedback

- FAIL / FindingだけではDefectへ自動登録しません。
- manual FAILの原因判断はRegression Skillでは行わず、ownerへ戻します。期待結果や仕様authorityが不明なら`question-analysis`で不足条件を確認し、既存仕様の解釈・Authority確定が必要な場合は`spec-analysis`へ渡します。TC自体に問題があれば`test-case-design`、現行UI情報の不足は`test-target-inspection`、owner不明の実対象仮説調査は`exploratory-testing | investigation`の担当です。
- E2E-55のpreflight blockedは、`e2e-test-execution`でblockedの解除または実行を行います。実行後にE2E異常があれば`e2e-test-result-analysis`が担当します。
- 修正確認と周辺Regressionは別の目的です。周辺Regressionを要求された場合は、別のRun目的として`regression-testing`で選定し、更新後のsource / baseline currentnessを確認します。

```json
{
  "artifact_type": "activity",
  "route_contract_version": "2",
  "activity_ref": null,
  "snapshot_ref": null,
  "scope_identity": null,
  "activity_state": "部分完了（ブロック中あり）",
  "source_executions": [
    {
      "execution_ref": "TC-301:manual",
      "tc_ref": "TC-301",
      "route_type": "manual",
      "source_artifact_ref": null,
      "source_start_state": "scenario.when started",
      "actual_start_confirmed": true,
      "result_finalized": true,
      "source_outcome": "FAIL",
      "evidence_refs": []
    },
    {
      "execution_ref": "TC-301:e2e:E2E-55",
      "tc_ref": "TC-301",
      "route_type": "e2e",
      "testware_ref": "E2E-55",
      "source_artifact_ref": null,
      "source_start_state": "preflight blocked; actual attempt not started",
      "actual_start_confirmed": false,
      "result_finalized": false,
      "source_outcome": null,
      "evidence_refs": []
    }
  ],
  "route_results": [
    {
      "tc_ref": "TC-301",
      "route_type": "manual",
      "route_ref": "TC-301:manual",
      "execution_ref": "TC-301:manual",
      "actual_start_confirmed": true,
      "result_finalized": true,
      "source_result": "FAIL",
      "route_status": "started_result_finalized"
    },
    {
      "tc_ref": "TC-301",
      "route_type": "e2e",
      "route_ref": "TC-301:e2e:E2E-55",
      "testware_ref": "E2E-55",
      "execution_ref": "TC-301:e2e:E2E-55",
      "actual_start_confirmed": false,
      "result_finalized": false,
      "source_result": null,
      "route_status": "blocked"
    }
  ],
  "tc_execution_state": [
    {
      "tc_ref": "TC-301",
      "executed": false,
      "reason": "required route E2E-55 のactual startが未確認のため、全required routeのstart条件を満たさない"
    }
  ],
  "counts": {
    "required_tc_count": 1,
    "executed_tc_count": 0,
    "routes_total": 2,
    "routes_actual_started": 1,
    "routes_result_finalized": 1,
    "routes_blocked": 1
  },
  "cleanup_status": "unresolved",
  "unresolved": [
    "route_blocked:TC-301:e2e:E2E-55 (preflight blocked, actual attempt not started, result not finalized)",
    "cleanup_status_unknown:TC-301:e2e:E2E-55",
    "activity_ref / snapshot_ref / scope_identity / source_artifact_ref は入力に出所がなく未解決"
  ],
  "auxiliary_route_results": [],
  "feedback": {
    "defect_auto_registration": "FAIL / FindingだけではDefectへ自動登録しない",
    "manual_fail_owner": "原因分析はownerへ戻す（期待結果・仕様authority不明: question-analysis、既存仕様の解釈・Authority確定: spec-analysis、TC問題: test-case-design）",
    "e2e_blocked_owner": "e2e-test-execution"
  }
}
```
