# Regression Run計画: release smoke補助testware（E2E-77）

## 判断理由

- 入力にあるのは、current TCを持たないE2E-77と、project policyが「release smoke補助testware」として今回参加を明示している事実だけです。したがってE2E-77はTCなし補助testwareとして`auxiliary_routes`に記録します。選定根拠は`policy`、今回実行する補助なので`completion_required=true`です。
- 他のTCなしE2Eはuser / policyのどちらにも指定されていないため、補助routeへ含めません。存在するだけで補助へ加える推測はしません。
- E2E-77にはcurrent TCがないため、TC IDを作りません。`selected_tc_refs`は空で、TC count / TC coverage / TCのexecution分子には加算しません。補助の件数と結果は`auxiliary_testware_count`と`auxiliary_route_results`に分けて扱います。
- 入力にはcurrent baseline、TC一覧、Riskの情報がありません。baselineのcomplete / currentnessは推測せず未解決とし、`suite_complete=false`です。このRunはSuite全体の完了にもfull Runにも数えません。
- 候補TCが0件であることを「Regression不要」とは扱いません。TCに紐付くRegression範囲は、このRunでは未判断（未解決）のままです。
- Riskの情報がないため、Risk refとの対応づけはできません。対応づけを推測せず、未解決として残します。Product Riskの新規採点はしません。
- E2E-77の`implementation_revision`と`execution_ref`は入力にありません。値を推測せず未解決にします。実行ownerは`e2e-test-execution`で、Regressionはrunnerを起動しません。
- actual start、result finalization、source resultはまだ確認できません。Activityは`未開始`で、`完了`にはしません。補助の必須routeが未開始・blockedのままActivityを完了にしない規則に従います。
- Activity `完了`の条件は次のとおりです。
  - E2E-77のactual start（`attempt_ref`付き）が確認できる。
  - owner側のresult finalizationが確認できる。
  - `raw_capture_complete`がtrueである。
  - cleanupが閉じている。
  - 未解決がない。
- source resultは再分類せず、ownerのraw valueをそのまま投影します。
- FAIL / Findingが出ても、FAIL / FindingだけではDefectへ自動登録しません。原因判断はowner Skill（`e2e-test-result-analysis`）へ戻します。

## 正規artifact

```json
{
  "artifact_type": "run",
  "route_contract_version": "2",
  "run_scope": {
    "type": "auxiliary_only",
    "rationale": "project policyがrelease smoke補助testwareとしてE2E-77の今回参加を明示。TCに紐付くRegression範囲は入力に無く未判断。"
  },
  "baseline": {
    "complete": null,
    "currentness": "unresolved",
    "member_tc_refs": []
  },
  "selected_tc_refs": [],
  "suite_complete": false,
  "required_routes": [],
  "auxiliary_routes": [
    {
      "testware_ref": "E2E-77",
      "executor_owner": "e2e-test-execution",
      "implementation_revision": null,
      "selection_basis": "policy",
      "completion_required": true,
      "execution_ref": null
    }
  ],
  "auxiliary_testware_refs": ["E2E-77"],
  "auxiliary_testware_count": 1,
  "excluded_auxiliary": [
    {
      "reason": "他のTCなしE2Eはuser / policyで指定されておらず、補助として含めない"
    }
  ],
  "risk_relation": {
    "status": "unresolved",
    "reason": "Risk / TCのtraceabilityが入力に無く、関係を推測しない。残る未検証影響の判断は未解決。"
  },
  "activity_preview": {
    "activity_state": "未開始",
    "tc_execution_state": "対象TCなし",
    "counts": {
      "tc_executed": 0,
      "auxiliary_started": 0
    }
  },
  "unresolved": [
    "baseline_currentness_unresolved",
    "tc_scope_unresolved",
    "risk_traceability_unresolved",
    "auxiliary_implementation_revision_unresolved:E2E-77",
    "auxiliary_execution_ref_unassigned:E2E-77",
    "auxiliary_actual_start_not_confirmed:E2E-77"
  ]
}
```
