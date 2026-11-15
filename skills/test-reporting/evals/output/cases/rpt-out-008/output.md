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
      "PASS": 0,
      "complete": false,
      "pass_rate": null,
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
      "reason": "population_incomplete",
      "source_ids": [
        "api"
      ],
      "status": "unknown"
    },
    {
      "criterion_id": "EX-4",
      "metric": "fail_count",
      "reason": "population_incomplete",
      "source_ids": [
        "api"
      ],
      "status": "unknown",
      "value": 0
    }
  ],
  "exit_judgement": "undetermined",
  "issues": [
    "duplicate_retrieval_source_id"
  ],
  "overall": {
    "complete": false,
    "pass_rate": null,
    "pass_rate_note": "units_are_never_summed_see_by_unit",
    "population_known": true
  },
  "period": null,
  "plan_approval_state": "approved",
  "plan_currentness": "current",
  "plan_ref": "plan:qa-1",
  "plan_revision": "p3",
  "population_basis": "planned",
  "release_decision": "not_determined_by_this_skill",
  "schema_version": "1",
  "scope_ref": "scope:checkout",
  "snapshot_ref": "RPT-728026f3ab9739b20213465afb44c7953a1eb46a",
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
        "cleanup_closed": false,
        "population_complete": false,
        "results_observable": false,
        "source_current": false
      },
      "complete": false,
      "conflicting_unit_refs": [],
      "counts": {},
      "empty_set": "unknown_not_zero",
      "excluded": [],
      "executed_rate": null,
      "issues": [
        "duplicate_retrieval_for_source_id",
        "planned_units_not_retrieved",
        "source_not_retrieved"
      ],
      "kind": "api",
      "missing_unit_refs": [
        "A1",
        "A2",
        "A3"
      ],
      "owner_skill": "owner",
      "pass_rate": null,
      "pass_rate_basis": "undetermined_incomplete_or_empty",
      "planned_total": 3,
      "records_digest": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945",
      "retrieved_at": null,
      "retrieved_only_pass_rate": null,
      "retrieved_total": 0,
      "source_id": "api",
      "source_revision": null,
      "unexecuted": null,
      "unit": "test",
      "unplanned_unit_refs": [],
      "unretrieved": 3
    }
  ],
  "unplanned_retrieved_sources": []
}
```
