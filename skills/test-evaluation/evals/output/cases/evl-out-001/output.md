# Candidate output

```json
{
  "artifact_type": "evaluation_report",
  "axes": {
    "efficiency": {
      "metrics": [
        {
          "axis": "efficiency",
          "delta": -2,
          "metric_id": "M-eff",
          "reasons": [],
          "status": "improved",
          "value": 3
        }
      ],
      "status": "measured",
      "trend": "improved",
      "unresolved_metrics": []
    },
    "process": {
      "metrics": [],
      "status": "unmeasured",
      "trend": "unmeasured",
      "unresolved_metrics": []
    },
    "quality": {
      "metrics": [],
      "status": "unmeasured",
      "trend": "unmeasured",
      "unresolved_metrics": []
    },
    "reusability": {
      "metrics": [],
      "status": "unmeasured",
      "trend": "unmeasured",
      "unresolved_metrics": []
    },
    "traceability": {
      "metrics": [],
      "status": "unmeasured",
      "trend": "unmeasured",
      "unresolved_metrics": []
    }
  },
  "claims": [
    {
      "assertion": "improved",
      "axis": "efficiency"
    },
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
    "achieved": 0,
    "counts": {
      "adopted": 0,
      "handed_off": 0,
      "implemented": 0,
      "measured_effective": 0,
      "measured_no_effect": 0,
      "measured_worsened": 0,
      "not_comparable": 0,
      "not_measurable": 0,
      "proposed": 1,
      "rejected": 0
    },
    "not_complete": [
      "IMP-1"
    ],
    "not_counted_as_achieved": [
      "IMP-1"
    ]
  },
  "improvements": [
    {
      "baseline_activity_ref": "act:1",
      "change_kind": "plan",
      "improvement_ref": "IMP-1",
      "proposal_revision": "prop-1",
      "scope_ref": "scope:checkout",
      "state": "proposed"
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
  "invalid_metrics": [],
  "metrics": [
    {
      "axis": "efficiency",
      "delta": -2,
      "metric_id": "M-eff",
      "reasons": [],
      "status": "improved",
      "value": 3
    }
  ],
  "raw_results_modified": false,
  "rejected_claims": [
    {
      "assertion": "improved",
      "axis": "quality",
      "reason": "claim_not_supported_by_axis_metrics"
    }
  ],
  "release_decision": "not_determined_by_this_skill",
  "schema_version": "1"
}
```
