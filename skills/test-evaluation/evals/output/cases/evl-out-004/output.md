# Candidate output

```json
{
  "artifact_type": "evaluation_report",
  "axes": {
    "efficiency": {
      "metrics": [],
      "status": "unmeasured",
      "trend": "unmeasured",
      "unresolved_metrics": []
    },
    "process": {
      "metrics": [
        {
          "axis": "process",
          "metric_id": "M-process",
          "reasons": [],
          "status": "measured",
          "value": 0.9
        }
      ],
      "status": "measured",
      "trend": "no_change_or_baseline",
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
  "claims": [],
  "composite_score": null,
  "evaluation_status": "final",
  "handoff": {
    "closed": false,
    "items": [
      {
        "confirmation_verified": true,
        "item_ref": "item:1",
        "receiver": "ops"
      },
      {
        "confirmation_verified": false,
        "item_ref": "item:2",
        "receiver": "ops"
      }
    ],
    "open_items": [
      {
        "item_ref": "item:2",
        "reasons": [
          "approval_missing"
        ]
      }
    ]
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
      "proposed": 0,
      "rejected": 0
    },
    "not_complete": [],
    "not_counted_as_achieved": []
  },
  "improvements": [],
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
      "axis": "process",
      "metric_id": "M-process",
      "reasons": [],
      "status": "measured",
      "value": 0.9
    }
  ],
  "raw_results_modified": false,
  "rejected_claims": [],
  "release_decision": "not_determined_by_this_skill",
  "schema_version": "1"
}
```
