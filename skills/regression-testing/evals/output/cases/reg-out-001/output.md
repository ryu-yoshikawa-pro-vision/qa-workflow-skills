# Candidate output

```json
{
  "artifact_type": "baseline",
  "baseline_ref": "BASE-2026-09",
  "discovery_snapshot_ref": "DS-001",
  "source_revisions": [
    {
      "source_ref": "repo:qa/test-cases",
      "revision": "r18"
    }
  ],
  "completeness_evidence": {
    "root_listing_complete": true,
    "source_revisions_complete": true,
    "lifecycle_resolved": true,
    "membership_decisions_complete": true
  },
  "complete": true,
  "memberships": [
    {
      "tc_ref": "TC-001",
      "lifecycle_status": "current",
      "decision": "member",
      "reason": "継続的に検証する注文確定経路"
    },
    {
      "tc_ref": "TC-002",
      "lifecycle_status": "current",
      "decision": "one_off",
      "reason": "一時的な移行確認"
    }
  ],
  "coverage_gaps": [
    {
      "scope_ref": "scope:refund",
      "reason": "current TCとのtraceability未確定"
    }
  ]
}
```
