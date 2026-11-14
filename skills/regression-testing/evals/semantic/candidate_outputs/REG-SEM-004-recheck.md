# REG-SEM-004 Regression Run / Activity

## 結論

- Activity状態は `部分完了（ブロック中あり）` です。`完了` でも `実行中` でもありません。
- TC-301の `tc_execution_state` は `executed` にしません。required routeはmanualとE2E-55の2つで、E2E-55のactual startが未確認だからです。論理TCは全required routeの実開始後だけexecutedと数えます。
- manual routeは実開始済み、result finalized=true、source resultは `FAIL` です。ownerのraw resultのまま保持し、再判定、再分類、PASS / 判定不能への読替えはしません。
- E2E-55 routeはartifactが存在し、preflightがblockedで、actual attemptが未開始、result finalized=falseです。artifactの存在やpreflightの状態から開始を推定しません。blockedのまま、未開始として扱います。
- manualのFAILがfinalizedでも、もう一方のrequired routeが未開始・blockedなので `完了` にしません。manual routeが開始済みでE2E routeがblockedなので、`ブロック中` ではなく `部分完了（ブロック中あり）` です。
- 課題文に無い値は補完せず、`null` または空として未解決に入れました。対象は `activity_ref`、`snapshot_ref`、`scope_identity`、`attempt_ref`、`raw_capture_complete`、`implementation_revision`、`cleanup_status`、source artifact ref、evidence refs、Runの値です。

## Activity artifact

課題文はTC-301の2 route分のsource factだけを与えています。このためmachine artifactはActivityのみ出力します。Baseline / Runの保存値は課題文に無く、Runを正本とする照合（`validate_activity_against_run`）はできません。`route_ref` と `execution_ref` は、課題文のTC-301 / manual / E2E-55から作ったkeyで、Run側の値と一致するかは未確認です。

```json
{
  "artifact_type": "activity",
  "route_contract_version": "2",
  "activity_ref": null,
  "snapshot_ref": null,
  "scope_identity": null,
  "activity_state": "部分完了（ブロック中あり）",
  "source_executions": {
    "manual:TC-301": {
      "start_state": "開始済み",
      "actual_start_confirmed": true,
      "result_finalized": true,
      "source_result": "FAIL",
      "source_artifact_ref": null,
      "source_outcome": null,
      "evidence_refs": [],
      "implementation_revision": null,
      "attempt_ref": null,
      "raw_capture_complete": null,
      "cleanup_status": "未確認"
    },
    "e2e:E2E-55": {
      "start_state": "未開始",
      "actual_start_confirmed": false,
      "result_finalized": false,
      "source_result": null,
      "source_artifact_ref": null,
      "source_outcome": null,
      "evidence_refs": [],
      "implementation_revision": null,
      "attempt_ref": null,
      "raw_capture_complete": null,
      "cleanup_status": "未確認"
    }
  },
  "route_results": [
    {
      "tc_ref": "TC-301",
      "route_ref": "manual:TC-301",
      "route_type": "manual",
      "execution_ref": "manual:TC-301",
      "executed": true
    },
    {
      "tc_ref": "TC-301",
      "route_ref": "e2e:E2E-55",
      "route_type": "e2e",
      "testware_ref": "E2E-55",
      "execution_ref": "e2e:E2E-55",
      "executed": false
    }
  ],
  "auxiliary_route_results": [],
  "tc_execution_state": {
    "TC-301": "blocked"
  },
  "counts": {
    "required_tc_count": 1,
    "executed_tc_count": 0,
    "required_route_count": 2,
    "started_route_count": 1,
    "finalized_route_count": 1,
    "blocked_route_count": 1,
    "auxiliary_required_completed_count": 0
  },
  "cleanup_status": "未確認",
  "unresolved": [
    "route_not_started:e2e:E2E-55",
    "e2e_preflight_blocked:E2E-55",
    "result_not_finalized:e2e:E2E-55",
    "cleanup_unconfirmed:manual:TC-301",
    "cleanup_unconfirmed:e2e:E2E-55",
    "activity_ref_unresolved",
    "snapshot_ref_unresolved",
    "scope_identity_unresolved",
    "source_artifact_ref_unresolved:manual:TC-301",
    "evidence_refs_unresolved:manual:TC-301",
    "run_not_provided"
  ]
}
```

## 状態とその理由

| 項目                        | 値                               | 理由                                                                                                                                                              |
| --------------------------- | -------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| manual route actual start   | 確認済み (`true`)                | ownerのexecution contractが `scenario.when` の開始を返した。                                                                                                      |
| manual route result         | finalized=true / `FAIL`          | ownerが返したraw resultをそのまま投影する。再判定しない。                                                                                                         |
| E2E-55 route actual start   | 未確認 (`false`)                 | actual attemptが未開始。artifact存在とpreflight blockedは開始の証拠にならない。                                                                                   |
| E2E-55 result finalization  | `false`                          | ownerが `false` を返した。結果文字列から推測しない。                                                                                                              |
| `tc_execution_state.TC-301` | `blocked`（`executed` ではない） | 全required routeのactual startが確認できていない。manualが開始済みでもTC-301は実行済みと数えない。FAILとexecutedの両立は、全route開始後の場合に限る。             |
| `activity_state`            | `部分完了（ブロック中あり）`     | 一部routeが開始済み（manual）で、別のrequired routeが未開始・blocked（E2E-55）。状態は論理TC単位ではなくrouteの開始単位で判定する。                               |
| `完了` にしない理由         | -                                | 完了には全required routeのactual start、各owner resultのfinalized、必要cleanupの閉鎖、unresolvedなしが必要。E2E-55は開始・finalizedとも未達で、unresolvedが残る。 |
| `実行中` にしない理由       | -                                | `実行中` は実開始済みで結果未確定・raw未取得の場合の状態。E2E-55は開始自体が無くblockedで、これには当たらない。                                                   |
| cleanup                     | `未確認`                         | 課題文にcleanupの情報が無い。`対象なし` / `成功` と読み替えず、確認できるまで未確認とする。                                                                       |
| `executed_tc_count`         | 0                                | 全routeが開始済みのTCだけを数える。TC-301は対象外。                                                                                                               |

## 残る未解決と次の対応

- E2E-55のpreflight blockの解消は `e2e-test-execution` が担当します。解消後にactual attemptの開始を確認し、source executionを更新します。Regressionはrunnerを起動せず、preflightの通過だけでは開始扱いにしません。
- scope / snapshot不変のblockなので、同じActivityをresumeできます。scope / snapshotを変える場合は別Activity / versionです。完了Activityはimmutableです。
- `attempt_ref`、`raw_capture_complete`、`implementation_revision` は課題文に無いため `null` としました。値を推測せず、ownerのsource executionで確認します。
- Run（`required_routes`、baseline currentness、`implementation_revision`）が未提供のため、Runとの照合は未実施です。Activity単体では検証済み扱いにしません。

## FAIL feedback

- manualのFAIL（raw result）とそのevidenceはsourceのまま保持し、Regression Skillでは原因を判断しません。原因分析は担当ownerへ戻します。期待結果や仕様authorityが不明な場合は `question-analysis` で不足条件を確認し、既存仕様の解釈・Authority確定が必要なら `spec-analysis` へ渡します。TC自体の問題は `test-case-design` が担当です。
- FAIL / FindingだけではDefectへ自動登録しません。
- 修正後の確認は、currentな既存TCを既存execution Skillで再利用します。周辺Regressionも要求された場合は、修正確認とは別のRun目的として選定します。
