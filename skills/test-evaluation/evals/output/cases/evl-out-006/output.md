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
      "metrics": [],
      "status": "unmeasured",
      "trend": "unmeasured",
      "unresolved_metrics": []
    },
    "quality": {
      "metrics": [
        {
          "axis": "quality",
          "delta": 0.20000000000000007,
          "metric_id": "Q-detect",
          "reasons": [],
          "status": "improved",
          "value": 0.8
        },
        {
          "axis": "quality",
          "delta": -0.19999999999999996,
          "metric_id": "Q-escape",
          "reasons": [],
          "status": "worsened",
          "value": 0.4
        }
      ],
      "status": "measured",
      "trend": "mixed",
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
      "axis": "quality"
    },
    {
      "assertion": "mixed",
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
      "axis": "quality",
      "delta": 0.20000000000000007,
      "metric_id": "Q-detect",
      "reasons": [],
      "status": "improved",
      "value": 0.8
    },
    {
      "axis": "quality",
      "delta": -0.19999999999999996,
      "metric_id": "Q-escape",
      "reasons": [],
      "status": "worsened",
      "value": 0.4
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
