# REG-SEM-007 Regression Run / Activity

## 結論

- Activity状態は **`部分完了（ブロック中あり）`** です。`完了`にはしません。
- TC-401の2つのrequired route（manual、非E2E `testware`）は、いずれも実開始済みで、owner側のresultがfinalizedです。raw resultはどちらも`PASS`で、これをそのまま投影しています。TC-401は全routeが開始済みなので、`executed_tc_count`は1です。
- `tests/unit/app-config.test.ts`は、利用者が今回のRunで実行するよう明示したため、`completion_required=true`（`selection_basis: "user_explicit"`）の必須補助です。runner起動前のpreflightでblockedになり、actual attemptは未開始、result finalized=falseです。preflightのblockedは実開始ではないので、実行済みや`完了`には変換しません。
- 必須補助が未開始かつblockedのままなので、Activityを`完了`にできません。TC routeは開始済みなので、状態は`ブロック中`ではなく`部分完了（ブロック中あり）`です。
- `tests/unit/native-stores.test.ts`は、参照候補として記録するだけの補助です（`completion_required=false`、`selection_basis: "reference_only"`）。未開始でも完了を妨げません。
- 補助testwareの件数と結果は、TCのexecution / coverageの分子へ加算しません。TC-401のPASSが2つあっても、補助の未完了は解消されません。逆に、補助のblockedがTC-401のPASSを覆すこともありません。
- 課題文にない情報（baseline、snapshot、scope identity、activity ref、app-config / native-storesの実装revisionなど）は推測せず、空または`未解決`として`unresolved`に記録しています。

## 状態とその理由

| 対象                                                  | actual start                 | result finalized | raw result                           | 判定への影響                                    |
| ----------------------------------------------------- | ---------------------------- | ---------------- | ------------------------------------ | ----------------------------------------------- |
| TC-401 manual                                         | 確認済み                     | true             | PASS                                 | 開始・確定済み                                  |
| TC-401 testware（`attempt-t401-1`、`rev-2026-11-09`） | 確認済み                     | true             | PASS（raw取得完了、cleanup対象なし） | 開始・確定済み。Runの実装revisionと一致         |
| `app-config.test.ts`（必須補助）                      | 未開始（preflightでblocked） | false            | なし                                 | 必須補助がblockedのため`完了`不可               |
| `native-stores.test.ts`（参照候補）                   | 未開始（実行対象外）         | false            | なし                                 | `completion_required=false`のため完了を妨げない |

- 今回の`完了`には、全required TC routeと`completion_required=true`の全補助routeについて、実開始、result確定、raw取得、`attempt_ref`、cleanup終了が揃うことが必要です。必須補助`app-config.test.ts`は実開始がなく、result確定もしていないので、この条件を満たしません。
- 一部のrouteまたは補助が開始済み（TC-401の2 route）なので、`部分完了（ブロック中あり）`です。
- `app-config.test.ts`の`cleanup_status`はsourceが返していません。補助では`対象なし`へ読み替えず`未確認`とします。実装revisionも課題文にないため、`implementation_revision_missing:tests/unit/app-config.test.ts`を未解決に加えます。
- TC-401 manualの`cleanup_status`も課題文に無く、推測せず`未確認`として扱います。ただしActivity状態は、必須補助のblockedで既に`完了`ではありません。
- 再開するには、同じscope / snapshotのまま、`app-config.test.ts`のpreflight blockを解消し、ownerが実開始、result確定、raw取得、`attempt_ref`、cleanupを返す必要があります。scopeやsnapshotを変える場合は別Activity / versionにします。

## Run artifact

```json
{
  "artifact_type": "run",
  "route_contract_version": "2",
  "run_ref": "unresolved",
  "run_scope": "selected",
  "baseline_ref": "unresolved",
  "baseline_complete": "unresolved",
  "baseline_currentness": "unresolved",
  "member_tc_refs": [],
  "selected_tc_refs": ["TC-401"],
  "excluded_tc_refs": [],
  "suite_complete": false,
  "required_routes": [
    {
      "tc_ref": "TC-401",
      "route_ref": "TC-401:manual",
      "route_type": "manual",
      "execution_ref": "exec:TC-401:manual"
    },
    {
      "tc_ref": "TC-401",
      "route_ref": "TC-401:testware:password-hasher",
      "route_type": "testware",
      "testware_ref": "tests/unit/password-hasher.test.ts",
      "executor_owner": "testware-execution",
      "implementation_revision": "rev-2026-11-09",
      "selection_basis": "file: tests/unit/password-hasher.test.ts (Vitest)",
      "execution_ref": "exec:TC-401:testware:password-hasher"
    }
  ],
  "auxiliary_routes": [
    {
      "testware_ref": "tests/unit/app-config.test.ts",
      "executor_owner": "testware-execution",
      "implementation_revision": "",
      "selection_basis": "user_explicit",
      "completion_required": true,
      "execution_ref": "exec:aux:app-config"
    },
    {
      "testware_ref": "tests/unit/native-stores.test.ts",
      "executor_owner": "testware-execution",
      "implementation_revision": "",
      "selection_basis": "reference_only",
      "completion_required": false,
      "execution_ref": "exec:aux:native-stores"
    }
  ],
  "auxiliary_testware_refs": [
    "tests/unit/app-config.test.ts",
    "tests/unit/native-stores.test.ts"
  ],
  "auxiliary_testware_count": 2,
  "risk_trace": {
    "status": "unresolved",
    "reason": "課題文にRisk refとTCのtraceabilityが無いため、関係を推測しない。残存する未検証影響はunresolvedで保持する"
  },
  "unresolved": [
    "baseline_ref_unresolved",
    "baseline_complete_unresolved",
    "baseline_currentness_unresolved",
    "implementation_revision_missing:tests/unit/app-config.test.ts"
  ]
}
```

注記: `app-config.test.ts`と`native-stores.test.ts`のexecutor ownerは、課題文に明示がありません。非E2EのVitestなので`testware-execution`としています。両補助の実装revisionは課題文に無いため空にしています。`native-stores.test.ts`は参照候補として記録するだけで、未実行でも構いません。

## Activity artifact

```json
{
  "artifact_type": "activity",
  "route_contract_version": "2",
  "activity_ref": "unresolved",
  "snapshot_ref": "unresolved",
  "scope_identity": "unresolved",
  "activity_state": "部分完了（ブロック中あり）",
  "source_executions": [
    {
      "execution_ref": "exec:TC-401:manual",
      "tc_ref": "TC-401",
      "route_type": "manual",
      "source_artifact_ref": "",
      "source_start_state": "started",
      "actual_start_confirmed": true,
      "result_finalized": true,
      "source_outcome": "PASS",
      "evidence_refs": []
    },
    {
      "execution_ref": "exec:TC-401:testware:password-hasher",
      "tc_ref": "TC-401",
      "route_type": "testware",
      "source_artifact_ref": "attempt-t401-1",
      "source_start_state": "started",
      "actual_start_confirmed": true,
      "result_finalized": true,
      "source_outcome": "PASS",
      "implementation_revision": "rev-2026-11-09",
      "raw_capture_complete": true,
      "cleanup_status": "対象なし",
      "evidence_refs": []
    }
  ],
  "route_results": [
    {
      "tc_ref": "TC-401",
      "route_ref": "TC-401:manual",
      "route_type": "manual",
      "execution_ref": "exec:TC-401:manual",
      "actual_start_confirmed": true,
      "result_finalized": true,
      "source_result": "PASS",
      "cleanup_status": "未確認"
    },
    {
      "tc_ref": "TC-401",
      "route_ref": "TC-401:testware:password-hasher",
      "route_type": "testware",
      "execution_ref": "exec:TC-401:testware:password-hasher",
      "actual_start_confirmed": true,
      "result_finalized": true,
      "source_result": "PASS",
      "implementation_revision": "rev-2026-11-09",
      "cleanup_status": "対象なし"
    }
  ],
  "auxiliary_route_results": [
    {
      "testware_ref": "tests/unit/app-config.test.ts",
      "executor_owner": "testware-execution",
      "execution_ref": "exec:aux:app-config",
      "completion_required": true,
      "selection_basis": "user_explicit",
      "route_state": "blocked",
      "block_reason": "runner起動前のpreflightでblocked",
      "actual_start_confirmed": false,
      "result_finalized": false,
      "source_result": null,
      "attempt_ref": null,
      "raw_capture_complete": false,
      "cleanup_status": "未確認",
      "implementation_revision": ""
    },
    {
      "testware_ref": "tests/unit/native-stores.test.ts",
      "executor_owner": "testware-execution",
      "execution_ref": "exec:aux:native-stores",
      "completion_required": false,
      "selection_basis": "reference_only",
      "route_state": "not_started",
      "actual_start_confirmed": false,
      "result_finalized": false,
      "source_result": null,
      "attempt_ref": null,
      "raw_capture_complete": false,
      "cleanup_status": "未確認"
    }
  ],
  "tc_execution_state": [
    {
      "tc_ref": "TC-401",
      "all_required_routes_started": true,
      "executed": true
    }
  ],
  "counts": {
    "selected_tc_count": 1,
    "executed_tc_count": 1,
    "auxiliary_testware_count": 2,
    "auxiliary_required_count": 1,
    "auxiliary_required_started_count": 0,
    "auxiliary_required_completed_count": 0
  },
  "cleanup_status": "未確認",
  "unresolved": [
    "auxiliary_required_blocked:tests/unit/app-config.test.ts",
    "implementation_revision_missing:tests/unit/app-config.test.ts",
    "cleanup_unconfirmed:tests/unit/app-config.test.ts",
    "cleanup_unconfirmed:TC-401:manual",
    "snapshot_ref_unresolved",
    "scope_identity_unresolved",
    "activity_ref_unresolved"
  ]
}
```

## ユーザー向け補足

- PASSは、ownerが返したraw resultをそのまま保持しています。Regression側で再判定や再分類はしていません。
- 補助`tests/unit/app-config.test.ts`は、今回のRunで実行を明示された必須補助なので、blockedを解消して実行・確定するまでActivityは`完了`になりません。
- 補助の件数と結果はTC countとTC coverageに含めていません。TC-401のPASSで補助の未完了を補うことも、その逆もしません。
- 課題文にFAIL / Findingは無いので、FAIL / Findingのfeedbackは該当しません。FAIL / FindingだけではDefectへ自動登録しません。
