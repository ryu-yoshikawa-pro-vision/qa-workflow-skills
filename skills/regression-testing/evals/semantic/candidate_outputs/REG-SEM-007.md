# REG-SEM-007 Regression Run / Activity

## 結論

- Activityの状態は **`部分完了（ブロック中あり）`** です。`完了`にはしません。
- 理由1: TC-401の2 route（manual、非E2E `testware`）はどちらもactual start確認済み、result finalized=true、raw result=PASSです。TC-401は`executed`と数えます。ただしこれだけでは`完了`の根拠になりません。
- 理由2: `tests/unit/app-config.test.ts`は利用者が今回実行を明示した補助testwareなので、`completion_required=true`（`selection_basis: "user_explicit"`）の必須補助です。runner起動前のpreflightでblockedとなり、actual attemptは未開始、result finalized=falseです。必須補助が未開始・blockedのため`完了`にできません。
- 理由3: TC routeは開始済みなので、状態は`ブロック中`ではなく`部分完了（ブロック中あり）`です。
- 理由4: `tests/unit/native-stores.test.ts`は「参照候補として記録するだけ」の指示なので`completion_required=false`（`selection_basis: "reference_only"`）です。未開始でもActivity完了を妨げません。完了にできない原因はnative-storesではありません。
- 補助testware（app-config、native-stores）はTCではありません。TC ID、TC count、TC coverageの分子には入れません。PASSしたTC-401の結果で、補助のblockedを埋めることもしません。

## 課題文にないため未解決として扱った項目

課題文に無い値は、他の値からの類推や既定値で補完していません。

- `app-config.test.ts`補助の`executor_owner`と`implementation_revision`は課題文にありません。TC-401 testwareの`testware-execution` / `rev-2026-11-09`は別routeの値であり、流用しません。
  - Run側の補助entryでは両fieldを省略し、`execution_ready: false`としました。`select_auxiliary_testware()`がowner・revisionの詳細なしで返す形と同じです。
  - Activityの`unresolved`へ`implementation_revision_missing:tests/unit/app-config.test.ts`と`auxiliary_executor_owner_unresolved:tests/unit/app-config.test.ts`を追加しました。
- `native-stores.test.ts`の`executor_owner`と`implementation_revision`も課題文にありません。参照候補なので完了は妨げませんが、値は補完せず省略しています。
- `app-config.test.ts`補助の`cleanup_status`は、ownerから返っていません。`対象なし`へ読み替えず`未確認`として扱います。確認できるまでActivityは`完了`になりません。`unresolved`に`cleanup_unconfirmed:tests/unit/app-config.test.ts`を追加しました。
- `app-config.test.ts`の`attempt_ref`は、actual attempt未開始のため存在しません。`null`とし、補完しません。`raw_capture_complete`も未取得（false）です。
- TC-401 manual routeの`cleanup_status`、`attempt_ref`、`implementation_revision`は返却値に含まれていません。`manual` routeの既定値は変更しない契約なので、値を足していません。
- TC-401 testware routeの`selection_basis`は、課題文が示すfile指定（`tests/unit/password-hasher.test.ts`）だけを記録しました。test名・filterは示されていないため、補っていません。
- 次の値は課題文に無いため、`null`にしました。値を作っていません。
  - `activity_ref`、`snapshot_ref`、`scope_identity`
  - baselineの`complete` / `currentness` / `member_tc_refs`
  - Run scopeの選定根拠、`route_ref`以外のID類
  - `unresolved`には`activity_identity_unresolved`と`baseline_currentness_unresolved`を追加しました。
- `execution_ref`は、課題文に値が無いため、このartifact内のlocal keyとして`EXEC-M-401`、`EXEC-T-401`、`EXEC-A-APP-CONFIG`、`EXEC-A-NATIVE-STORES`を使います。
- Product Riskと各TCのtraceabilityは入力に無いため、Riskとの関係は推測していません。このRunで残る未検証影響は、Risk refと結び付けられず未解決です。新規Risk採点が必要なら`test-analysis`へ戻します。

## Run artifact

selected Runです。baselineのcomplete / currentnessが確認できていないため、`suite_complete`はfalseです。Suite全体の完了には数えません。

```json
{
  "artifact_type": "run",
  "route_contract_version": "2",
  "run_scope": {
    "type": "selected",
    "selection_basis": null
  },
  "baseline": {
    "complete": null,
    "currentness": "unresolved",
    "member_tc_refs": null
  },
  "selected_tc_refs": ["TC-401"],
  "suite_complete": false,
  "required_routes": [
    {
      "tc_ref": "TC-401",
      "route_ref": "manual:TC-401",
      "route_type": "manual",
      "execution_ref": "EXEC-M-401"
    },
    {
      "tc_ref": "TC-401",
      "route_ref": "testware:TC-401",
      "route_type": "testware",
      "testware_ref": "tests/unit/password-hasher.test.ts",
      "executor_owner": "testware-execution",
      "implementation_revision": "rev-2026-11-09",
      "selection_basis": "file:tests/unit/password-hasher.test.ts",
      "execution_ref": "EXEC-T-401"
    }
  ],
  "auxiliary_routes": [
    {
      "testware_ref": "tests/unit/app-config.test.ts",
      "completion_required": true,
      "selection_basis": "user_explicit",
      "execution_ref": "EXEC-A-APP-CONFIG",
      "execution_ready": false
    },
    {
      "testware_ref": "tests/unit/native-stores.test.ts",
      "completion_required": false,
      "selection_basis": "reference_only",
      "execution_ref": "EXEC-A-NATIVE-STORES",
      "execution_ready": false
    }
  ],
  "auxiliary_testware_refs": [
    "tests/unit/app-config.test.ts",
    "tests/unit/native-stores.test.ts"
  ],
  "auxiliary_testware_count": 2
}
```

## Activity artifact

```json
{
  "artifact_type": "activity",
  "route_contract_version": "2",
  "activity_ref": null,
  "snapshot_ref": null,
  "scope_identity": null,
  "activity_state": "部分完了（ブロック中あり）",
  "source_executions": {
    "EXEC-M-401": {
      "start_state": "開始済み",
      "actual_start_confirmed": true,
      "result_finalized": true,
      "source_result": "PASS"
    },
    "EXEC-T-401": {
      "start_state": "開始済み",
      "actual_start_confirmed": true,
      "result_finalized": true,
      "source_result": "PASS",
      "implementation_revision": "rev-2026-11-09",
      "attempt_ref": "attempt-t401-1",
      "raw_capture_complete": true,
      "cleanup_status": "対象なし"
    },
    "EXEC-A-APP-CONFIG": {
      "start_state": "未開始",
      "actual_start_confirmed": false,
      "result_finalized": false,
      "source_result": null,
      "blocked": true,
      "block_reason": "runner起動前preflightでblocked",
      "attempt_ref": null,
      "raw_capture_complete": false,
      "cleanup_status": "未確認"
    },
    "EXEC-A-NATIVE-STORES": {
      "start_state": "未開始",
      "actual_start_confirmed": false,
      "result_finalized": false,
      "source_result": null
    }
  },
  "tc_execution_state": {
    "TC-401": "executed"
  },
  "route_results": [
    {
      "tc_ref": "TC-401",
      "route_ref": "manual:TC-401",
      "route_type": "manual",
      "execution_ref": "EXEC-M-401",
      "executed": true,
      "actual_start_confirmed": true,
      "result_finalized": true,
      "source_result": "PASS"
    },
    {
      "tc_ref": "TC-401",
      "route_ref": "testware:TC-401",
      "route_type": "testware",
      "execution_ref": "EXEC-T-401",
      "executed": true,
      "actual_start_confirmed": true,
      "result_finalized": true,
      "source_result": "PASS",
      "implementation_revision": "rev-2026-11-09",
      "attempt_ref": "attempt-t401-1",
      "raw_capture_complete": true,
      "cleanup_status": "対象なし"
    }
  ],
  "auxiliary_route_results": [
    {
      "testware_ref": "tests/unit/app-config.test.ts",
      "completion_required": true,
      "execution_ref": "EXEC-A-APP-CONFIG",
      "executed": false,
      "actual_start_confirmed": false,
      "result_finalized": false,
      "source_result": null,
      "attempt_ref": null,
      "raw_capture_complete": false,
      "cleanup_status": "未確認"
    },
    {
      "testware_ref": "tests/unit/native-stores.test.ts",
      "completion_required": false,
      "execution_ref": "EXEC-A-NATIVE-STORES",
      "executed": false,
      "actual_start_confirmed": false,
      "result_finalized": false,
      "source_result": null
    }
  ],
  "counts": {
    "selected_tc_count": 1,
    "executed_tc_count": 1,
    "auxiliary_testware_count": 2,
    "auxiliary_required_count": 1,
    "auxiliary_required_completed_count": 0
  },
  "cleanup_status": "未確認",
  "unresolved": [
    "auxiliary_required_blocked:tests/unit/app-config.test.ts",
    "auxiliary_executor_owner_unresolved:tests/unit/app-config.test.ts",
    "implementation_revision_missing:tests/unit/app-config.test.ts",
    "cleanup_unconfirmed:tests/unit/app-config.test.ts",
    "activity_identity_unresolved",
    "baseline_currentness_unresolved"
  ]
}
```

## 状態判定の根拠

| 対象                                | actual start                 | result finalized | raw result | Activityへの影響                                                            |
| ----------------------------------- | ---------------------------- | ---------------- | ---------- | --------------------------------------------------------------------------- |
| TC-401 manual                       | 確認済み                     | true             | PASS       | 完了条件を満たす                                                            |
| TC-401 testware（`rev-2026-11-09`） | 確認済み（`attempt-t401-1`） | true             | PASS       | 実装revisionがRunと一致し、raw取得完了、cleanup対象なしで、完了条件を満たす |
| `app-config.test.ts`（必須補助）    | 未開始（preflightでblocked） | false            | なし       | 必須補助がblockedのため`完了`不可                                           |
| `native-stores.test.ts`（参照候補） | 未開始                       | false            | なし       | `completion_required=false`のため影響なし                                   |

- TC-401の全required routeが開始済みなので、`tc_execution_state`は`executed`、`executed_tc_count`は1です。
- 必須補助`app-config.test.ts`は、actual attempt未開始なので`executed`ではありません。runnerの起動前にpreflightで止まった事実を、実行済みや開始済みへ変換していません。
- 補助のcleanupは、sourceが返さないため`未確認`です。この点でも`完了`にできません。
- 結果として、開始済みのrouteがあり、必須補助がblockedのため`部分完了（ブロック中あり）`です。
- 解消条件は次のとおりです。
  - `testware-execution`が`app-config.test.ts`のowner・実装revisionを確定する。
  - preflightのblockを解消し、actual attempt開始、result finalized、raw取得完了、`attempt_ref`、cleanupの終了を確認する。
  - Run scope / snapshotが不変なら、同じActivityでresumeできます。scopeやsnapshotが変わる場合は別Activityにします。
