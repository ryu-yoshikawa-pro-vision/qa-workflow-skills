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
    "duplicate_check": "no_match",
    "now": "2026-11-10T00:00:00+00:00",
    "write_permission": true
  },
  "outcome": {
    "auto_retry_allowed": false,
    "external_issue": {
      "issue_ref": "ISSUE-9",
      "retrieved_at": "2026-11-10T00:00:00+00:00",
      "revision": "1"
    },
    "external_update_performed": true,
    "next": null,
    "operation_id": "DEFOP-d33b01e38532fc29351482ed48070a257ec68cea",
    "readback_verified": true,
    "status": "applied"
  },
  "plan": {
    "auto_retry_allowed": true,
    "candidate_ref": "DEFC-b0f7216bf8e36a23ab85eab518f0f7aac8154c31",
    "decision": "allow",
    "issue_ref": null,
    "operation": "create",
    "operation_id": "DEFOP-d33b01e38532fc29351482ed48070a257ec68cea",
    "reasons": [],
    "requires_readback": true,
    "single_attempt_only": false
  },
  "schema_version": "1"
}
```
