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
          "metric_id": "M-quality",
          "reasons": [
            "measurement_conditions_definition_or_unit_differ"
          ],
          "status": "not_comparable",
          "value": 0.8
        }
      ],
      "status": "measured",
      "trend": "not_comparable"
    },
    "reusability": {
      "metrics": [],
      "status": "unmeasured",
      "trend": "unmeasured"
    },
    "traceability": {
      "metrics": [
        {
          "axis": "traceability",
          "delta": -0.19999999999999996,
          "metric_id": "M-trace",
          "reasons": [],
          "status": "worsened",
          "value": 0.4
        }
      ],
      "status": "measured",
      "trend": "worsened"
    }
  },
  "claims": [
    {
      "assertion": "improved",
      "axis": "quality"
    },
    {
      "assertion": "worsened",
      "axis": "traceability"
    }
  ],
  "composite_score": null,
  "evaluation_status": "provisional",
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
      "measured_worsened": 1,
      "not_comparable": 1,
      "not_measurable": 0,
      "proposed": 0,
      "rejected": 0
    },
    "not_complete": [],
    "not_counted_as_achieved": [
      "IMP-1",
      "IMP-5"
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
        "metric_id": "M-quality",
        "reasons": [
          "measurement_conditions_definition_or_unit_differ"
        ],
        "status": "not_comparable",
        "value": 0.8
      },
      "improvement_ref": "IMP-1",
      "new_revision": "plan-4",
      "owner_skill": "test-management",
      "proposal_revision": "prop-1",
      "request_ref": "req:1",
      "scope_ref": "scope:checkout",
      "state": "not_comparable"
    },
    {
      "adoption_ref": "appr:1",
      "base_revision": "plan-3",
      "baseline_activity_ref": "act:1",
      "change_kind": "plan",
      "effect_metric": {
        "axis": "traceability",
        "delta": -0.19999999999999996,
        "metric_id": "M-trace",
        "reasons": [],
        "status": "worsened",
        "value": 0.4
      },
      "improvement_ref": "IMP-5",
      "new_revision": "plan-4",
      "owner_skill": "test-management",
      "proposal_revision": "prop-1",
      "request_ref": "req:1",
      "scope_ref": "scope:checkout",
      "state": "measured_worsened"
    }
  ],
  "input_check": {
    "stale_refs": [
      "plan:qa-1"
    ],
    "status": "stale_or_unverified",
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
      "metric_id": "M-quality",
      "reasons": [
        "measurement_conditions_definition_or_unit_differ"
      ],
      "status": "not_comparable",
      "value": 0.8
    },
    {
      "axis": "traceability",
      "delta": -0.19999999999999996,
      "metric_id": "M-trace",
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
