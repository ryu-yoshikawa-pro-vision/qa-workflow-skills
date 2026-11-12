# Candidate output

```json
{
  "artifact_type": "external_operation",
  "context": {
    "approval": {
      "authentication_verified": true,
      "binding_matches": true,
      "expires_at": "2026-11-11T00:00:00+00:00",
      "issued_at": "2026-11-09T00:00:00+00:00",
      "policy_revision": "pol-3",
      "principal": "qa-lead",
      "revoked": false,
      "role": "defect_submitter",
      "source": "trusted_approval_service"
    },
    "atomic_dedupe": true,
    "candidate_state": "ready_for_external_handoff",
    "conditional_update": true,
    "fix_target_ref": "build:42",
    "fix_verification": {
      "status": "issue_marked_resolved"
    },
    "issue_revision_fresh": true,
    "now": "2026-11-10T00:00:00+00:00",
    "observed_target_ref": "build:41",
    "write_permission": true
  },
  "outcome": {
    "external_update_performed": false,
    "operation_id": "DEFOP-2191ade46c00a2a8d9f1194b408e8f5c406ae21a",
    "status": "not_attempted"
  },
  "plan": {
    "auto_retry_allowed": false,
    "candidate_ref": "DEFC-b0f7216bf8e36a23ab85eab518f0f7aac8154c31",
    "decision": "blocked",
    "issue_ref": "ISSUE-9",
    "operation": "close",
    "operation_id": "DEFOP-2191ade46c00a2a8d9f1194b408e8f5c406ae21a",
    "reasons": [
      "close_without_verified_fix_on_fix_target"
    ],
    "requires_readback": true
  },
  "schema_version": "1"
}
```
