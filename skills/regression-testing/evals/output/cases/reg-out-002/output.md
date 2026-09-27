# Candidate output

```json
{
  "artifact_type": "activity",
  "activity_ref": "ACT-REG-010",
  "snapshot_ref": "DS-001",
  "scope_identity": "scope:checkout",
  "activity_state": "部分完了（ブロック中あり）",
  "baseline": {
    "complete": true,
    "currentness": "current",
    "member_tc_refs": [
      "TC-001"
    ]
  },
  "run_scope": "selected",
  "selected_tc_refs": [
    "TC-001"
  ],
  "suite_complete": false,
  "source_executions": {
    "EXEC-M-001": {
      "start_state": "開始済み",
      "actual_start_confirmed": true,
      "source_result": "FAIL",
      "evidence_refs": [
        "ev:manual-1"
      ]
    },
    "EXEC-E-001": {
      "start_state": "未開始",
      "actual_start_confirmed": false,
      "source_result": "未実行",
      "blocked": true,
      "evidence_refs": []
    }
  },
  "route_results": [
    {
      "tc_ref": "TC-001",
      "route_ref": "manual",
      "execution_ref": "EXEC-M-001",
      "source_start_state": "開始済み",
      "source_result": "FAIL",
      "executed": true,
      "blocked": false
    },
    {
      "tc_ref": "TC-001",
      "route_ref": "e2e:checkout",
      "execution_ref": "EXEC-E-001",
      "source_start_state": "未開始",
      "source_result": "未実行",
      "executed": false,
      "blocked": true
    }
  ],
  "tc_execution_state": {
    "TC-001": "blocked"
  },
  "counts": {
    "tc_member_count": 1,
    "executed_tc_count": 0,
    "unexecuted_tc_count": 0,
    "blocked_tc_count": 1,
    "auxiliary_testware_count": 0,
    "source_result_counts": {
      "FAIL": 1
    }
  },
  "auxiliary_route_results": [],
  "auxiliary_testware_refs": [],
  "auxiliary_testware_count": 0,
  "cleanup_status": "成功",
  "unresolved": [
    "E2E preflight blocked"
  ]
}
```
