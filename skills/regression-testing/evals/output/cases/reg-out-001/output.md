# Candidate output

```json
{
  "artifact_type": "baseline",
  "schema_version": "1",
  "baseline_ref": "BASE-2026-09",
  "discovery_snapshot_ref": "DS-001",
  "source_revisions": [
    {
      "source_ref": "repo:qa/test-cases",
      "revision": "r18"
    },
    {
      "source_ref": "risk:RISK-001",
      "revision": "r3"
    },
    {
      "source_ref": "issue:ISSUE-002",
      "revision": "r8"
    },
    {
      "source_ref": "risk:RISK-003",
      "revision": "r2"
    }
  ],
  "scope_identity": "scope:checkout",
  "scope_refs": [
    "scope:checkout"
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
      "reason": "継続的に検証する注文確定経路",
      "source_refs": [
        "risk:RISK-001"
      ],
      "source_revisions": [
        {
          "source_ref": "risk:RISK-001",
          "revision": "r3"
        }
      ]
    },
    {
      "tc_ref": "TC-002",
      "lifecycle_status": "current",
      "decision": "one_off",
      "reason": "一時的な移行確認",
      "source_refs": [
        "issue:ISSUE-002"
      ],
      "source_revisions": [
        {
          "source_ref": "issue:ISSUE-002",
          "revision": "r8"
        }
      ]
    },
    {
      "tc_ref": "TC-003",
      "lifecycle_status": "current",
      "decision": "out_of_scope",
      "reason": "管理者設定経路はcheckout Regression範囲外",
      "source_refs": [
        "risk:RISK-003"
      ],
      "source_revisions": [
        {
          "source_ref": "risk:RISK-003",
          "revision": "r2"
        }
      ]
    }
  ],
  "member_tc_refs": [
    "TC-001"
  ],
  "one_off_tc_refs": [
    "TC-002"
  ],
  "unresolved_tc_refs": [],
  "undecided_tc_refs": [],
  "coverage_gaps": [
    {
      "scope_ref": "scope:refund",
      "reason": "current TCとのtraceability未確定"
    }
  ]
}
```
