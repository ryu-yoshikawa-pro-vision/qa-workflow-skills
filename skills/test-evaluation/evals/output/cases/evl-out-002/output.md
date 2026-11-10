# Candidate output

```json
{
  "artifact_type": "evaluation_report",
  "axes": {
    "efficiency": {
      "metrics": [],
      "status": "unmeasured",
      "trend": "unmeasured"
    },
    "process": {
      "metrics": [],
      "status": "unmeasured",
      "trend": "unmeasured"
    },
    "quality": {
      "metrics": [
        {
          "axis": "quality",
          "delta": 0.20000000000000007,
          "metric_id": "M-quality",
          "reasons": [],
          "status": "improved",
          "value": 0.8
        }
      ],
      "status": "measured",
      "trend": "improved"
    },
    "reusability": {
      "metrics": [],
      "status": "unmeasured",
      "trend": "unmeasured"
    },
    "traceability": {
      "metrics": [],
      "status": "unmeasured",
      "trend": "unmeasured"
    }
  },
  "claims": [
    {
      "assertion": "improved",
      "axis": "quality"
    }
  ],
  "composite_score": null,
  "evaluation_status": "final",
  "handoff": {
    "closed": false,
    "items": [],
    "open_items": []
  },
  "improvement_summary": {
    "achieved": 1,
    "counts": {
      "adopted": 1,
      "handed_off": 0,
      "implemented": 1,
      "measured_effective": 1,
      "measured_no_effect": 0,
      "measured_worsened": 0,
      "not_comparable": 0,
      "not_measurable": 0,
      "proposed": 1,
      "rejected": 0
    },
    "not_complete": [
      "IMP-2",
      "IMP-3",
      "IMP-4"
    ],
    "not_counted_as_achieved": [
      "IMP-2",
      "IMP-3",
      "IMP-4"
    ]
  },
  "improvements": [
    {
      "adoption_ref": "appr:1",
      "base_revision": "plan-3",
      "baseline_activity_ref": "act:1",
      "change_kind": "plan",
      "effect_metric": {
        "axis": "quality",
        "delta": 0.20000000000000007,
        "metric_id": "M-quality",
        "reasons": [],
        "status": "improved",
        "value": 0.8
      },
      "improvement_ref": "IMP-1",
      "new_revision": "plan-4",
      "owner_skill": "test-management",
      "proposal_revision": "prop-1",
      "request_ref": "req:1",
      "scope_ref": "scope:checkout",
      "state": "measured_effective"
    },
    {
      "baseline_activity_ref": "act:1",
      "change_kind": "plan",
      "improvement_ref": "IMP-2",
      "proposal_revision": "prop-2",
      "scope_ref": "scope:checkout",
      "state": "proposed"
    },
    {
      "adoption_ref": "appr:3",
      "baseline_activity_ref": "act:1",
      "change_kind": "plan",
      "improvement_ref": "IMP-3",
      "proposal_revision": "prop-1",
      "scope_ref": "scope:checkout",
      "state": "adopted"
    },
    {
      "adoption_ref": "appr:1",
      "base_revision": "plan-3",
      "baseline_activity_ref": "act:1",
      "change_kind": "plan",
      "improvement_ref": "IMP-4",
      "new_revision": "plan-4",
      "owner_skill": "test-management",
      "proposal_revision": "prop-1",
      "request_ref": "req:1",
      "scope_ref": "scope:checkout",
      "state": "implemented"
    }
  ],
  "input_check": {
    "stale_refs": [],
    "status": "current",
    "unverified_refs": []
  },
  "inputs": [
    {
      "content_hash": "h1",
      "ref": "report:RPT-1",
      "revision": "r1"
    },
    {
      "content_hash": "h2",
      "ref": "plan:qa-1",
      "revision": "p3"
    }
  ],
  "metrics": [
    {
      "axis": "quality",
      "delta": 0.20000000000000007,
      "metric_id": "M-quality",
      "reasons": [],
      "status": "improved",
      "value": 0.8
    }
  ],
  "raw_results_modified": false,
  "rejected_claims": [],
  "release_decision": "not_determined_by_this_skill",
  "schema_version": "1"
}
```
