# Candidate output

```json
{
  "artifact_type": "report_snapshot",
  "build_ref": "build:41",
  "by_unit": {
    "logical_primary": {
      "FAIL": 0,
      "PASS": 2,
      "complete": true,
      "pass_rate": 1.0,
      "planned": 2,
      "source_ids": [
        "e2e"
      ]
    },
    "test": {
      "FAIL": 0,
      "PASS": 3,
      "complete": true,
      "pass_rate": 1.0,
      "planned": 3,
      "source_ids": [
        "api"
      ]
    }
  },
  "defect_projection": {
    "count": 0,
    "issue_refs": [],
    "read_only": true
  },
  "exit_criteria": [
    {
      "criterion_id": "EX-1",
      "metric": "pass_rate",
      "source_ids": [
        "e2e"
      ],
      "status": "satisfied",
      "value": 1.0
    },
    {
      "criterion_id": "EX-2",
      "metric": "fail_count",
      "source_ids": [
        "e2e"
      ],
      "status": "satisfied",
      "value": 0
    },
    {
      "criterion_id": "EX-3",
      "metric": "pass_rate",
      "source_ids": [
        "api"
      ],
      "status": "satisfied",
      "value": 1.0
    },
    {
      "criterion_id": "EX-4",
      "metric": "fail_count",
      "source_ids": [
        "api"
      ],
      "status": "satisfied",
      "value": 0
    }
  ],
  "exit_judgement": "undetermined",
  "issues": [
    "plan_currentness_unverified"
  ],
  "overall": {
    "complete": true,
    "pass_rate": null,
    "pass_rate_note": "units_are_never_summed_see_by_unit",
    "population_known": true
  },
  "period": null,
  "plan_approval_state": "approved",
  "plan_currentness": "unverified",
  "plan_ref": "plan:qa-1",
  "plan_revision": "p3",
  "population_basis": "planned",
  "release_decision": "not_determined_by_this_skill",
  "schema_version": "1",
  "scope_ref": "scope:checkout",
  "snapshot_ref": "RPT-daecc325e68681b48e37e66df692ca296bdfd332",
  "sources": [
    {
      "closure": {
        "cleanup_closed": true,
        "population_complete": true,
        "results_observable": true,
        "source_current": true
      },
      "complete": true,
      "conflicting_unit_refs": [],
      "counts": {
        "PASS": 2
      },
      "empty_set": "not_empty",
      "excluded": [],
      "executed_rate": 1.0,
      "issues": [],
      "kind": "e2e",
      "missing_unit_refs": [],
      "owner_skill": "owner",
      "pass_rate": 1.0,
      "pass_rate_basis": "planned_population",
      "planned_total": 2,
      "records_digest": "c157fc9e410af97b048b12d3c224b5fff486b4431a670500abc8af8066c34726",
      "retrieved_at": "2026-11-10T00:00:00+00:00",
      "retrieved_only_pass_rate": 1.0,
      "retrieved_total": 2,
      "source_id": "e2e",
      "source_revision": "rev1",
      "unexecuted": 0,
      "unit": "logical_primary",
      "unplanned_unit_refs": [],
      "unretrieved": 0
    },
    {
      "closure": {
        "cleanup_closed": true,
        "population_complete": true,
        "results_observable": true,
        "source_current": true
      },
      "complete": true,
      "conflicting_unit_refs": [],
      "counts": {
        "PASS": 3
      },
      "empty_set": "not_empty",
      "excluded": [],
      "executed_rate": 1.0,
      "issues": [],
      "kind": "api",
      "missing_unit_refs": [],
      "owner_skill": "owner",
      "pass_rate": 1.0,
      "pass_rate_basis": "planned_population",
      "planned_total": 3,
      "records_digest": "568d6d90e22b9dae49722e4736c6dd3186769e603d7b3cbb543c865e1e3b9b2a",
      "retrieved_at": "2026-11-10T00:00:00+00:00",
      "retrieved_only_pass_rate": 1.0,
      "retrieved_total": 3,
      "source_id": "api",
      "source_revision": "rev1",
      "unexecuted": 0,
      "unit": "test",
      "unplanned_unit_refs": [],
      "unretrieved": 0
    }
  ],
  "unplanned_retrieved_sources": []
}
```
