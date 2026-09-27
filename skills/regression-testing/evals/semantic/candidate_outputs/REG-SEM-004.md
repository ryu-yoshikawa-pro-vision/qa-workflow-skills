# Regression Activity候補

**Activity：未完了**
**TC-301：未実行**（required route のすべてで actual start が確認されていないため）

| Required route | Actual start | Result finalized（owner fact） | Raw source result |
|---|---|---|---|
| manual | 開始確認済み（`scenario.when` 開始） | `true` | `FAIL` |
| E2E-55 | 未開始（preflight blocked） | `false` | 未解決（未提示） |

**未解決：** manual と E2E-55 の source execution refs、cleanup facts、source outcome、evidence refs は未提示です。E2E artifact は存在しますが、実行 ref の提示にはなりません。その他の未提示項目も未解決のままです。FAIL の原因は未判定で、FAIL / Finding だけでは Defect に自動登録しません。

```json
{
  "artifact_type": "activity",
  "schema_version": "1",
  "tc_ref": "TC-301",
  "complete": false,
  "executed": false,
  "required_routes": [
    {
      "route": "manual",
      "source_start_state": "scenario.when 開始済み",
      "actual_start_confirmed": true,
      "result_finalized": true,
      "raw_source_result": "FAIL",
      "source_execution_ref": null,
      "source_outcome": null,
      "evidence_refs": null,
      "cleanup_facts": null
    },
    {
      "e2e_ref": "E2E-55",
      "source_start_state": "preflight blocked; actual attempt 未開始",
      "actual_start_confirmed": false,
      "result_finalized": false,
      "raw_source_result": null,
      "source_execution_ref": null,
      "source_outcome": null,
      "evidence_refs": null,
      "cleanup_facts": null
    }
  ],
  "unresolved": [
    "両routeのsource execution refs",
    "両routeのcleanup facts",
    "source outcomeとevidence refs",
    "E2E-55のraw source result",
    "その他の未提示項目"
  ]
}
```
