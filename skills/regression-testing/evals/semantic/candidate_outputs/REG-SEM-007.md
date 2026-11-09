# REG-SEM-007 Regression Run / Activity

入力にはBaseline、discovery snapshot、scope identityが含まれていません。これらは推測せず、`null` / `unresolved` として記録します。今回のRunはTC-401だけを対象にしたselected Runであり、Suite全体の完了には数えません。

## Run artifact

```json
{
  "artifact_type": "run",
  "route_contract_version": "2",
  "run_scope": {
    "kind": "selected",
    "basis": "user_specified",
    "selected_tc_refs": ["TC-401"],
    "rationale": "利用者が指定したTC-401とその必須routeを今回のRunの対象とする。"
  },
  "baseline": {
    "complete": null,
    "currentness": "unresolved",
    "member_tc_refs": [],
    "note": "入力にBaselineが無いため、complete / currentnessは確認できない。推測しない。"
  },
  "selected_tc_refs": ["TC-401"],
  "excluded_tc_refs": [],
  "suite_complete": false,
  "required_routes": [
    {
      "tc_ref": "TC-401",
      "route_ref": "TC-401-manual",
      "route_type": "manual",
      "execution_ref": "exec-TC-401-manual"
    },
    {
      "tc_ref": "TC-401",
      "route_ref": "TC-401-testware",
      "route_type": "testware",
      "testware_ref": "tests/unit/password-hasher.test.ts",
      "executor_owner": "testware-execution",
      "implementation_revision": "rev-2026-11-09",
      "selection_basis": "Vitest tests/unit/password-hasher.test.ts",
      "execution_ref": "exec-TC-401-testware"
    }
  ],
  "auxiliary_routes": [
    {
      "testware_ref": "tests/unit/app-config.test.ts",
      "executor_owner": "testware-execution",
      "implementation_revision": "rev-2026-11-09",
      "selection_basis": "user_explicit",
      "completion_required": true,
      "execution_ref": "exec-aux-app-config"
    },
    {
      "testware_ref": "tests/unit/native-stores.test.ts",
      "executor_owner": "testware-execution",
      "implementation_revision": "rev-2026-11-09",
      "selection_basis": "reference_only",
      "completion_required": false,
      "execution_ref": "exec-aux-native-stores"
    }
  ],
  "auxiliary_testware_refs": [
    "tests/unit/app-config.test.ts",
    "tests/unit/native-stores.test.ts"
  ],
  "auxiliary_testware_count": 2,
  "risk_relation": {
    "status": "unresolved",
    "note": "入力に既存Risk refとTCのtraceabilityが無いため、Riskとの関係は推測せず未解決とする。Product Riskは新規採点しない。"
  }
}
```

## Activity artifact

```json
{
  "artifact_type": "activity",
  "activity_ref": "activity-reg-sem-007",
  "snapshot_ref": null,
  "scope_identity": null,
  "route_contract_version": "2",
  "activity_state": "部分完了（ブロック中あり）",
  "source_executions": [
    {
      "execution_ref": "exec-TC-401-manual",
      "tc_ref": "TC-401",
      "route_ref": "TC-401-manual",
      "source_artifact_ref": null,
      "actual_start_confirmed": true,
      "result_finalized": true,
      "source_outcome": "PASS",
      "evidence_refs": []
    },
    {
      "execution_ref": "exec-TC-401-testware",
      "tc_ref": "TC-401",
      "route_ref": "TC-401-testware",
      "source_artifact_ref": null,
      "actual_start_confirmed": true,
      "attempt_ref": "attempt-t401-1",
      "implementation_revision": "rev-2026-11-09",
      "result_finalized": true,
      "source_outcome": "PASS",
      "raw_capture_complete": true,
      "cleanup_status": "not_applicable",
      "evidence_refs": []
    },
    {
      "execution_ref": "exec-aux-app-config",
      "testware_ref": "tests/unit/app-config.test.ts",
      "actual_start_confirmed": false,
      "attempt_ref": null,
      "implementation_revision": "rev-2026-11-09",
      "result_finalized": false,
      "source_outcome": null,
      "raw_capture_complete": false,
      "cleanup_status": "unconfirmed",
      "source_start_state": "blocked_before_runner_start_preflight"
    },
    {
      "execution_ref": "exec-aux-native-stores",
      "testware_ref": "tests/unit/native-stores.test.ts",
      "actual_start_confirmed": false,
      "attempt_ref": null,
      "result_finalized": false,
      "source_outcome": null,
      "source_start_state": "not_started_not_in_scope"
    }
  ],
  "route_results": [
    {
      "tc_ref": "TC-401",
      "route_ref": "TC-401-manual",
      "route_type": "manual",
      "execution_ref": "exec-TC-401-manual",
      "actual_start_confirmed": true,
      "result_finalized": true,
      "source_outcome": "PASS",
      "cleanup_status": "not_required"
    },
    {
      "tc_ref": "TC-401",
      "route_ref": "TC-401-testware",
      "route_type": "testware",
      "testware_ref": "tests/unit/password-hasher.test.ts",
      "execution_ref": "exec-TC-401-testware",
      "actual_start_confirmed": true,
      "result_finalized": true,
      "source_outcome": "PASS",
      "implementation_revision": "rev-2026-11-09",
      "cleanup_status": "not_applicable"
    }
  ],
  "tc_execution_state": [
    {
      "tc_ref": "TC-401",
      "executed": true,
      "reason": "全required route（manual / testware）のactual startを確認済み"
    }
  ],
  "auxiliary_route_results": [
    {
      "testware_ref": "tests/unit/app-config.test.ts",
      "completion_required": true,
      "execution_ref": "exec-aux-app-config",
      "actual_start_confirmed": false,
      "attempt_ref": null,
      "result_finalized": false,
      "source_outcome": null,
      "raw_capture_complete": false,
      "cleanup_status": "unconfirmed",
      "state": "blocked"
    },
    {
      "testware_ref": "tests/unit/native-stores.test.ts",
      "completion_required": false,
      "execution_ref": "exec-aux-native-stores",
      "actual_start_confirmed": false,
      "attempt_ref": null,
      "result_finalized": false,
      "source_outcome": null,
      "state": "not_started_reference_only"
    }
  ],
  "counts": {
    "tc": { "selected": 1, "executed": 1, "pass": 1 },
    "auxiliary": {
      "required": 1,
      "required_started": 0,
      "required_blocked": 1,
      "reference_only": 1
    }
  },
  "cleanup_status": "unconfirmed",
  "unresolved": [
    "auxiliary_blocked:tests/unit/app-config.test.ts",
    "snapshot_ref_unresolved",
    "scope_identity_unresolved"
  ]
}
```

## Activityの状態と理由

状態は **部分完了（ブロック中あり）** です。`完了` にはしません。

- TC-401のmanual routeとtestware routeは、どちらもactual startを確認でき、owner側でresult finalizedです。rawのsource resultはどちらもPASSで、そのまま投影しました。testwareはattempt ref `attempt-t401-1`、実装revision `rev-2026-11-09`（Runの値と一致）、raw取得完了、cleanup対象なしです。全required routeの開始を確認できたため、TC-401は実行済みと数えます。
- `tests/unit/app-config.test.ts` は利用者が今回のRunで実行するよう明示したので、`completion_required=true`（`selection_basis: "user_explicit"`）の必須補助です。runner起動前のpreflightでblockedになり、actual attemptは未開始、result finalized=falseです。preflightを通過しただけ、またはblockedだっただけでは開始扱いにしません。そのため必須補助が未開始・blockedで、`unresolved` に `auxiliary_blocked:tests/unit/app-config.test.ts` を残します。TC routeは開始済みの義務なので、状態は `ブロック中` ではなく `部分完了（ブロック中あり）` です。
- `tests/unit/native-stores.test.ts` は参照候補です（`completion_required=false`、`selection_basis: "reference_only"`）。未開始でも完了を妨げず、状態の判断に影響しません。
- 補助testwareの件数と結果は、TCのexecution / coverageの分子へ加算しません。app-configが失敗または不足しても、TC-401のPASSを覆しません。逆にTC-401のPASSでapp-configの未実行を補いません。
- このRunはselected Runです。`suite_complete=false` であり、Suite全体の完了には数えません。

## 未解決の事項と再開方法

- `app-config.test.ts` のblock原因（preflight失敗の内容）はowner（`testware-execution`）が解消します。解消後に同じActivityでresumeできるのは、scope / snapshotが変わらない場合だけです。変わる場合は別Activity / versionで実行します。
- Baseline、snapshot ref、scope identity、Riskとのtraceabilityは入力に無く、推測しませんでした。
- FAILやFindingは今回ありません。今後FAIL / Findingが出た場合も、FAIL / FindingだけではDefectへ自動登録せず、原因分析は担当ownerへ戻します。
