# Candidate output

```json
{
  "artifact_type": "external_operation",
  "context": {
    "approval": {
      "authentication_verified": true,
      "binding_matches": false,
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
    "duplicate_check": "no_match",
    "now": "2026-11-10T00:00:00+00:00",
    "write_permission": true
  },
  "outcome": {
    "external_update_performed": false,
    "operation_id": "DEFOP-d33b01e38532fc29351482ed48070a257ec68cea",
    "status": "not_attempted"
  },
  "plan": {
    "auto_retry_allowed": false,
    "candidate_ref": "DEFC-b0f7216bf8e36a23ab85eab518f0f7aac8154c31",
    "decision": "blocked",
    "issue_ref": null,
    "operation": "create",
    "operation_id": "DEFOP-d33b01e38532fc29351482ed48070a257ec68cea",
    "reasons": [
      "approval_binding_mismatch:issue_ref",
      "approval_binding_mismatch:issue_revision"
    ],
    "requires_readback": true
  },
  "schema_version": "1"
}
```
