# Candidate output

```json
{
  "artifact_type": "report_snapshot",
  "build_ref": "build:41",
  "by_unit": {
    "logical_primary": {
      "FAIL": 0,
      "PASS": 1,
      "complete": false,
      "pass_rate": null,
      "planned": 2,
      "source_ids": [
        "e2e"
      ]
    },
    "test": {
      "FAIL": 0,
      "PASS": 3,
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
      "reason": "population_incomplete",
      "source_ids": [
        "e2e"
      ],
      "status": "unknown"
    },
    {
      "criterion_id": "EX-2",
      "metric": "fail_count",
      "reason": "population_incomplete",
      "source_ids": [
        "e2e"
      ],
      "status": "unknown",
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
  "issues": [],
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
  "snapshot_ref": "RPT-c729a1c7aa833d96c1da8e9fabc09c65918e5970",
  "sources": [
    {
      "closure": {
        "cleanup_closed": false,
        "population_complete": false,
        "results_observable": false,
        "source_current": true
      },
      "complete": false,
      "conflicting_unit_refs": [],
      "counts": {
        "PASS": 1
      },
      "empty_set": "not_empty",
      "excluded": [
        {
          "reason": "build_mismatch",
          "result_ref": "res:logical_primary:T2"
        }
      ],
      "executed_rate": null,
      "issues": [
        "planned_units_not_retrieved"
      ],
      "kind": "e2e",
      "missing_unit_refs": [
        "T2"
      ],
      "owner_skill": "owner",
      "pass_rate": null,
      "pass_rate_basis": "undetermined_incomplete_or_empty",
      "planned_total": 2,
      "records_digest": "eb096b1f1efd6e349256cd415daae37c3cd56c74809ac1fb59ddcb79f0da6f43",
      "retrieved_at": "2026-11-10T00:00:00+00:00",
      "retrieved_only_pass_rate": 1.0,
      "retrieved_total": 1,
      "source_id": "e2e",
      "source_revision": "rev1",
      "unexecuted": null,
      "unit": "logical_primary",
      "unplanned_unit_refs": [],
      "unretrieved": 1
    },
    {
      "closure": {
        "cleanup_closed": true,
        "population_complete": true,
        "results_observable": true,
        "source_current": false
      },
      "complete": false,
      "conflicting_unit_refs": [],
      "counts": {
        "PASS": 3
      },
      "empty_set": "not_empty",
      "excluded": [],
      "executed_rate": null,
      "issues": [
        "source_revision_not_current_or_unverified"
      ],
      "kind": "api",
      "missing_unit_refs": [],
      "owner_skill": "owner",
      "pass_rate": null,
      "pass_rate_basis": "undetermined_incomplete_or_empty",
      "planned_total": 3,
      "records_digest": "568d6d90e22b9dae49722e4736c6dd3186769e603d7b3cbb543c865e1e3b9b2a",
      "retrieved_at": "2026-11-10T00:00:00+00:00",
      "retrieved_only_pass_rate": 1.0,
      "retrieved_total": 3,
      "source_id": "api",
      "source_revision": "rev1",
      "unexecuted": null,
      "unit": "test",
      "unplanned_unit_refs": [],
      "unretrieved": 0
    }
  ],
  "unplanned_retrieved_sources": []
}
```
