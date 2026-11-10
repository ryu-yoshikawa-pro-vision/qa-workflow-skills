# Candidate output

```json
{
  "artifact_type": "report_snapshot",
  "build_ref": "build:41",
  "by_unit": {
    "attempt": {
      "FAIL": 1,
      "PASS": 1,
      "complete": true,
      "pass_rate": 0.5,
      "planned": 2,
      "source_ids": [
        "e2e-attempts"
      ]
    },
    "logical_primary": {
      "FAIL": 0,
      "PASS": 1,
      "complete": true,
      "pass_rate": 1.0,
      "planned": 1,
      "source_ids": [
        "e2e"
      ]
    }
  },
  "defect_projection": {
    "count": 0,
    "issue_refs": [],
    "read_only": true
  },
  "exit_criteria": [],
  "exit_judgement": "undetermined",
  "issues": [],
  "overall": {
    "complete": true,
    "pass_rate": null,
    "pass_rate_note": "units_are_never_summed_see_by_unit",
    "population_known": true
  },
  "plan_approval_state": "approved",
  "plan_ref": "plan:qa-1",
  "plan_revision": "p3",
  "population_basis": "planned",
  "release_decision": "not_determined_by_this_skill",
  "schema_version": "1",
  "scope_ref": "scope:checkout",
  "snapshot_ref": "RPT-4ff149e4626e41c52ce34e803ab955cddca709ee",
  "sources": [
    {
      "closure": {
        "cleanup_closed": true,
        "population_complete": true,
        "results_observable": true,
        "source_current": true
      },
      "complete": true,
      "counts": {
        "PASS": 1
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
      "planned_total": 1,
      "retrieved_at": "2026-11-10T00:00:00+00:00",
      "retrieved_only_pass_rate": 1.0,
      "retrieved_total": 1,
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
      "counts": {
        "FAIL": 1,
        "PASS": 1
      },
      "empty_set": "not_empty",
      "excluded": [],
      "executed_rate": 1.0,
      "issues": [],
      "kind": "e2e",
      "missing_unit_refs": [],
      "owner_skill": "owner",
      "pass_rate": 0.5,
      "pass_rate_basis": "planned_population",
      "planned_total": 2,
      "retrieved_at": "2026-11-10T00:00:00+00:00",
      "retrieved_only_pass_rate": 0.5,
      "retrieved_total": 2,
      "source_id": "e2e-attempts",
      "source_revision": "rev1",
      "unexecuted": 0,
      "unit": "attempt",
      "unplanned_unit_refs": [],
      "unretrieved": 0
    }
  ],
  "unplanned_retrieved_sources": []
}
```
