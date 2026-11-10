# Candidate output

```json
{
  "artifact_type": "fix_verification",
  "request": {
    "change_refs": [
      "commit:abc"
    ],
    "fix_target_ref": "build:42",
    "notice_is_confirmation": false,
    "observed_target_ref": "build:41",
    "original_owner_skill": "e2e-test-execution",
    "performed_by": "original_execution_owner",
    "regression_selection_owner": "regression-testing",
    "request_ref": "DEFOP-aca9536288ed05e3b1afd8f0c2fee98fe07ab0a5",
    "same_acceptance_basis": true,
    "send_to": "e2e-test-execution",
    "status": "request_ready",
    "verification_targets": [
      {
        "current": true,
        "ref": "tc:TC-007",
        "revision": "t3"
      }
    ]
  },
  "result": {
    "actual_start_confirmed": true,
    "cleanup_status": "成功",
    "fix_confirmed": true,
    "owner_skill": "e2e-test-execution",
    "result_finalized": true,
    "status": "fix_confirmed",
    "target_ref": "build:42",
    "verified_target_ref": "build:42"
  },
  "schema_version": "1"
}
```
