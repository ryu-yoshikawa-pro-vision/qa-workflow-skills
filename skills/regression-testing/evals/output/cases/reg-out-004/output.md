# Candidate output

```json
{
  "artifact_type": "activity",
  "activity_ref": "ACT-REG-OUT-004",
  "snapshot_ref": "DS-001",
  "scope_identity": "scope:checkout",
  "source_executions": {
    "EXEC-M-001": {
      "start_state": "開始済み",
      "actual_start_confirmed": true,
      "result_finalized": true,
      "source_result": "PASS"
    },
    "EXEC-T-002": {
      "start_state": "開始済み",
      "actual_start_confirmed": true,
      "result_finalized": true,
      "source_result": "PASS",
      "implementation_revision": "rev-2026-11-09",
      "attempt_ref": "attempt-t2",
      "raw_capture_complete": true
    },
    "EXEC-A-001": {
      "start_state": "開始済み",
      "actual_start_confirmed": true,
      "result_finalized": true,
      "source_result": "PASS",
      "implementation_revision": "rev-2026-11-09",
      "attempt_ref": "attempt-a1",
      "raw_capture_complete": true,
      "cleanup_status": "対象なし"
    },
    "EXEC-A-002": {
      "start_state": "未開始",
      "actual_start_confirmed": false,
      "result_finalized": false,
      "source_result": "未実行",
      "cleanup_status": "対象なし"
    }
  },
  "route_contract_version": "2",
  "activity_state": "完了",
  "route_results": [
    {
      "tc_ref": "TC-001",
      "route_ref": "manual",
      "route_type": "manual",
      "execution_ref": "EXEC-M-001",
      "implementation_revision": null,
      "source_start_state": "開始済み",
      "source_result": "PASS",
      "result_finalized": true,
      "source_result_projectable": true,
      "cleanup_status": "対象なし",
      "evidence_refs": [],
      "executed": true,
      "blocked": false
    },
    {
      "tc_ref": "TC-002",
      "route_ref": "testware:vitest:TC-002",
      "route_type": "testware",
      "execution_ref": "EXEC-T-002",
      "implementation_revision": "rev-2026-11-09",
      "source_start_state": "開始済み",
      "source_result": "PASS",
      "result_finalized": true,
      "source_result_projectable": true,
      "cleanup_status": "対象なし",
      "evidence_refs": [],
      "executed": true,
      "blocked": false
    }
  ],
  "auxiliary_route_results": [
    {
      "testware_ref": "vitest:tests/unit/app-config.test.ts",
      "executor_owner": "testware-execution",
      "implementation_revision": "rev-2026-11-09",
      "selection_basis": "user_explicit",
      "completion_required": true,
      "execution_ref": "EXEC-A-001",
      "attempt_ref": "attempt-a1",
      "source_start_state": "開始済み",
      "source_result": "PASS",
      "result_finalized": true,
      "source_result_projectable": true,
      "raw_capture_complete": true,
      "cleanup_status": "対象なし",
      "evidence_refs": [],
      "executed": true,
      "blocked": false
    },
    {
      "testware_ref": "vitest:tests/unit/native-stores.test.ts",
      "executor_owner": "testware-execution",
      "implementation_revision": "rev-2026-11-09",
      "selection_basis": "reference_only",
      "completion_required": false,
      "execution_ref": "EXEC-A-002",
      "attempt_ref": null,
      "source_start_state": "未開始",
      "source_result": "未実行",
      "result_finalized": false,
      "source_result_projectable": true,
      "raw_capture_complete": false,
      "cleanup_status": "対象なし",
      "evidence_refs": [],
      "executed": false,
      "blocked": false
    }
  ],
  "tc_execution_state": {
    "TC-001": "executed",
    "TC-002": "executed"
  },
  "counts": {
    "tc_member_count": 2,
    "executed_tc_count": 2,
    "unexecuted_tc_count": 0,
    "blocked_tc_count": 0,
    "source_result_counts": {
      "PASS": 2
    },
    "auxiliary_testware_count": 2,
    "auxiliary_executed_count": 1,
    "auxiliary_source_result_counts": {
      "PASS": 1
    },
    "auxiliary_required_count": 1,
    "auxiliary_required_completed_count": 1,
    "auxiliary_obligation_unknown_count": 0
  },
  "cleanup_status": "対象なし",
  "unresolved": [],
  "auxiliary_testware_refs": [
    "vitest:tests/unit/app-config.test.ts",
    "vitest:tests/unit/native-stores.test.ts"
  ],
  "auxiliary_testware_count": 2
}
```
