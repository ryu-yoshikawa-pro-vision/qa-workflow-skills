"""Standalone deterministic cross-technique report snapshot builder.

The helper reads already-retrieved owner results (read-only projection), reconciles
them with the planned source population and returns a snapshot. It never rewrites a
raw result, never turns unknown into zero, and never decides release readiness.
"""

from __future__ import annotations

import hashlib
import json
import sys
from typing import Any

PLAN_APPROVED = "approved"
RETRIEVAL_COMPLETE = "complete"
FINAL_STATES = {"PASS", "FAIL", "未実行", "SKIP", "判定不能", "blocked"}
EXECUTION_KINDS = {
    "general_tc",
    "e2e",
    "regression",
    "exploration",
    "api",
    "batch",
    "component",
    "nonfunctional",
    "uiux",
    "wcag",
}
STATIC_KINDS = {"static_review", "static_analysis"}
SOURCE_KINDS = EXECUTION_KINDS | STATIC_KINDS | {"defect"}
CLEANUP_CLOSED = {"成功", "対象なし", "意図的に残した状態"}
MAX_INPUT_BYTES = 8 * 1024 * 1024
OPERATORS = {">=", "<=", "==", "<", ">"}
METRICS = {
    "pass_rate",
    "executed_rate",
    "fail_count",
    "unexecuted_count",
    "review_completion",
    "cleanup_complete",
}


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()


def _rate(numerator: int, denominator: int) -> float | None:
    return None if denominator <= 0 else round(numerator / denominator, 6)


def _source_summary(
    planned: dict[str, Any],
    retrieval: dict[str, Any] | None,
    plan: dict[str, Any],
    current_revisions: dict[str, str],
) -> dict[str, Any]:
    source_id = planned.get("source_id")
    kind = planned.get("kind")
    unit = planned.get("unit")
    issues: list[str] = []
    if kind not in SOURCE_KINDS or not _text(unit) or not _text(source_id):
        return {
            "source_id": source_id,
            "unit": unit,
            "complete": False,
            "closure": {},
            "issues": ["planned_source_invalid"],
            "counts": {},
        }
    expected_refs = planned.get("expected_refs")
    expected_count = planned.get("expected_count")
    refs_valid = isinstance(expected_refs, list) and all(
        _text(r) for r in expected_refs
    )
    if refs_valid:
        expected_set = set(expected_refs)
        if len(expected_set) != len(expected_refs):
            issues.append("expected_refs_duplicated")
        if expected_count is not None and expected_count != len(expected_set):
            issues.append("expected_count_and_refs_disagree")
    else:
        expected_set = None
    count_valid = (
        isinstance(expected_count, int)
        and not isinstance(expected_count, bool)
        and expected_count >= 0
    )
    population_known = refs_valid or count_valid
    legit_empty = (
        planned.get("no_target_confirmed") is True
        and (expected_count in (0, None))
        and not expected_set
    )
    if legit_empty:
        population_known, expected_count = True, 0
    if not population_known:
        issues.append("expected_population_unknown")
    planned_total = (
        len(expected_set)
        if expected_set is not None
        else (expected_count if isinstance(expected_count, int) else None)
    )

    build_ref = planned.get("build_ref") or plan.get("build_ref")
    env_ref = planned.get("environment_ref") or plan.get("environment_ref")
    retrieved = retrieval or {}
    retrieval_ok = (
        retrieved.get("status") == RETRIEVAL_COMPLETE
        and retrieved.get("pagination_complete") is True
        and retrieved.get("permission_ok") is True
    )
    if retrieval is None or retrieved.get("status") == "not_attempted":
        issues.append("source_not_retrieved")
    elif not retrieval_ok:
        issues.append("retrieval_partial_failed_or_unauthorized")
    current_revision = current_revisions.get(source_id)
    source_current = (
        retrieved.get("source_revision") is not None
        and _text(retrieved.get("source_revision"))
        and current_revision == retrieved.get("source_revision")
    )
    if retrieval is not None and not source_current:
        issues.append("source_revision_not_current_or_unverified")

    excluded: list[dict[str, str]] = []
    eligible: dict[str, dict[str, Any]] = {}
    seen_results: set[str] = set()
    conflicts: set[str] = set()
    unplanned: list[str] = []
    findings: list[dict[str, Any]] = []
    for record in retrieved.get("records", []) or []:
        if (
            kind in STATIC_KINDS
            and isinstance(record, dict)
            and record.get("unit") == "finding"
        ):
            findings.append(record)
            continue
        if (
            not isinstance(record, dict)
            or record.get("unit") != unit
            or not _text(record.get("unit_ref"))
            or not _text(record.get("result_ref"))
        ):
            issues.append("record_unit_or_identity_invalid")
            continue
        if record["result_ref"] in seen_results:
            issues.append("duplicate_result_ref_ignored")
            continue
        seen_results.add(record["result_ref"])
        if (
            kind != "defect"
            and record.get("state") not in FINAL_STATES
            and record.get("state")
            not in {"reviewed", "not_reviewed", "tool_failed", "finding"}
        ):
            issues.append("record_state_outside_raw_value_set")
            continue
        if build_ref and record.get("build_ref") != build_ref:
            excluded.append(
                {"result_ref": record["result_ref"], "reason": "build_mismatch"}
            )
            continue
        if env_ref and record.get("environment_ref") != env_ref:
            excluded.append(
                {"result_ref": record["result_ref"], "reason": "environment_mismatch"}
            )
            continue
        if record.get("source_revision") not in (
            None,
            retrieved.get("source_revision"),
        ):
            excluded.append(
                {
                    "result_ref": record["result_ref"],
                    "reason": "record_source_revision_mismatch",
                }
            )
            continue
        key = (
            record["unit_ref"]
            if unit != "attempt"
            else f"{record['unit_ref']}#{record.get('attempt_no')}"
        )
        if key in eligible:
            conflicts.add(key)
            continue
        eligible[key] = record
    if conflicts:
        issues.append("same_unit_reported_more_than_once_with_different_results")
    if expected_set is not None:
        unplanned = sorted(set(eligible) - expected_set) if unit != "attempt" else []
    planned_records = {
        k: v for k, v in eligible.items() if expected_set is None or k in expected_set
    }
    missing = (
        sorted(expected_set - set(planned_records)) if expected_set is not None else []
    )
    if missing:
        issues.append("planned_units_not_retrieved")
    if (
        expected_set is None
        and isinstance(expected_count, int)
        and len(planned_records) != expected_count
    ):
        issues.append("retrieved_count_differs_from_expected_count")

    counts: dict[str, int] = {}
    unfinalized = 0
    cleanup_open = 0
    for record in planned_records.values():
        state = record.get("state")
        counts[state] = counts.get(state, 0) + 1
        if record.get("result_finalized") is not True and kind in EXECUTION_KINDS:
            unfinalized += 1
        if (
            kind in EXECUTION_KINDS
            and record.get("state") != "未実行"
            and record.get("cleanup_status") not in CLEANUP_CLOSED
        ):
            cleanup_open += 1
    if unfinalized:
        issues.append("results_not_finalized")
    if cleanup_open:
        issues.append("cleanup_not_confirmed")

    population_complete = (
        population_known
        and retrieval_ok
        and not missing
        and not conflicts
        and "retrieved_count_differs_from_expected_count" not in issues
        and "expected_refs_duplicated" not in issues
        and "expected_count_and_refs_disagree" not in issues
    )
    closure = {
        "population_complete": population_complete,
        "source_current": bool(source_current),
        "results_observable": unfinalized == 0 and population_complete,
        "cleanup_closed": cleanup_open == 0 and population_complete,
    }
    complete = all(closure.values())
    retrieved_total = len(planned_records)
    summary: dict[str, Any] = {
        "source_id": source_id,
        "owner_skill": planned.get("owner_skill"),
        "kind": kind,
        "unit": unit,
        "planned_total": planned_total,
        "retrieved_total": retrieved_total,
        "unretrieved": len(missing)
        if expected_set is not None
        else (
            planned_total - retrieved_total
            if isinstance(planned_total, int) and planned_total >= retrieved_total
            else None
        ),
        "missing_unit_refs": missing,
        "unplanned_unit_refs": unplanned,
        "excluded": excluded,
        "counts": counts,
        "source_revision": retrieved.get("source_revision"),
        "retrieved_at": retrieved.get("retrieved_at"),
        "empty_set": "confirmed_no_target"
        if legit_empty and not planned_records
        else (
            "unknown_not_zero"
            if not population_complete and not planned_records
            else "not_empty"
        ),
        "closure": closure,
        "complete": complete,
        "issues": sorted(set(issues)),
    }
    if kind in STATIC_KINDS:
        reviewed = counts.get("reviewed", 0)
        summary["review_completion"] = {"planned": planned_total, "reviewed": reviewed}
        summary["finding_count"] = len(findings)
        summary["zero_findings_claim_allowed"] = bool(
            complete
            and planned_total is not None
            and reviewed == planned_total
            and not findings
        )
    elif kind == "defect":
        summary["complete"] = complete
    else:
        denominator = (
            planned_total if complete and isinstance(planned_total, int) else None
        )
        passed = counts.get("PASS", 0)
        executed = sum(v for k, v in counts.items() if k not in {"未実行", "blocked"})
        summary["pass_rate"] = _rate(passed, denominator) if denominator else None
        summary["executed_rate"] = _rate(executed, denominator) if denominator else None
        summary["unexecuted"] = (
            (counts.get("未実行", 0) + len(missing)) if complete else None
        )
        summary["pass_rate_basis"] = (
            "planned_population" if denominator else "undetermined_incomplete_or_empty"
        )
        summary["retrieved_only_pass_rate"] = _rate(passed, retrieved_total)
    return summary


def _evaluate_criterion(
    criterion: dict[str, Any], summaries: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    cid = criterion.get("criterion_id")
    metric, op, threshold = (
        criterion.get("metric"),
        criterion.get("operator"),
        criterion.get("threshold"),
    )
    ids = criterion.get("source_ids")
    if (
        metric not in METRICS
        or op not in OPERATORS
        or not isinstance(threshold, (int, float))
        or isinstance(threshold, bool)
        or not isinstance(ids, list)
        or not ids
    ):
        return {"criterion_id": cid, "status": "unknown", "reason": "criterion_invalid"}
    selected = [summaries.get(i) for i in ids]
    if any(s is None for s in selected):
        return {
            "criterion_id": cid,
            "status": "unknown",
            "reason": "criterion_source_not_planned",
        }
    complete = all(s["complete"] for s in selected)
    if metric == "fail_count":
        value = sum(s["counts"].get("FAIL", 0) for s in selected)
        observed_lower_bound = True
    elif not complete:
        return {
            "criterion_id": cid,
            "status": "unknown",
            "reason": "population_incomplete",
        }
    elif metric in {"pass_rate", "executed_rate"}:
        total = sum(s["planned_total"] or 0 for s in selected)
        key = "PASS" if metric == "pass_rate" else None
        count = sum(
            s["counts"].get("PASS", 0)
            if key
            else sum(
                v for k, v in s["counts"].items() if k not in {"未実行", "blocked"}
            )
            for s in selected
        )
        value = _rate(count, total)
        observed_lower_bound = False
    elif metric == "unexecuted_count":
        value, observed_lower_bound = sum(s["unexecuted"] or 0 for s in selected), False
    elif metric == "review_completion":
        total = sum(
            s["review_completion"]["planned"] or 0
            for s in selected
            if "review_completion" in s
        )
        done = sum(
            s["review_completion"]["reviewed"]
            for s in selected
            if "review_completion" in s
        )
        value, observed_lower_bound = _rate(done, total), False
    else:
        value, observed_lower_bound = (
            1 if all(s["closure"]["cleanup_closed"] for s in selected) else 0,
            False,
        )
    if value is None:
        return {
            "criterion_id": cid,
            "status": "unknown",
            "reason": "denominator_zero_or_unknown",
        }
    holds = {
        ">=": value >= threshold,
        "<=": value <= threshold,
        "==": value == threshold,
        "<": value < threshold,
        ">": value > threshold,
    }[op]
    if holds and observed_lower_bound and not complete:
        return {
            "criterion_id": cid,
            "status": "unknown",
            "value": value,
            "reason": "population_incomplete",
        }
    return {
        "criterion_id": cid,
        "status": "satisfied" if holds else "unsatisfied",
        "value": value,
    }


def _criterion(
    criterion: dict[str, Any], summaries: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    """Evaluate one exit criterion and keep what it was evaluated against."""
    return {
        **_evaluate_criterion(criterion, summaries),
        "metric": criterion.get("metric"),
        "source_ids": criterion.get("source_ids"),
    }


def build_snapshot(data: dict[str, Any]) -> dict[str, Any]:
    plan = data.get("plan") if isinstance(data.get("plan"), dict) else None
    scope = data.get("scope") if isinstance(data.get("scope"), dict) else {}
    retrievals = {
        r.get("source_id"): r for r in data.get("retrievals", []) if isinstance(r, dict)
    }
    current_revisions = (
        data.get("current_source_revisions")
        if isinstance(data.get("current_source_revisions"), dict)
        else {}
    )
    issues: list[str] = []
    if plan is None:
        planned_sources: list[dict[str, Any]] = []
        population = "unknown_direct_request"
        if not _text(scope.get("scope_ref")) or not scope.get("discovery_roots"):
            issues.append("explicit_scope_and_discovery_roots_required")
        plan_state = "no_plan"
    else:
        planned_sources = [
            p for p in plan.get("planned_sources", []) if isinstance(p, dict)
        ]
        population = "planned"
        plan_state = plan.get("approval_state")
        if not planned_sources:
            issues.append("planned_sources_missing")
        if plan_state != PLAN_APPROVED:
            issues.append("plan_not_approved")
        if data.get("current_plan_revision") not in (None, plan.get("plan_revision")):
            issues.append("plan_revision_superseded")
    ids = [p.get("source_id") for p in planned_sources]
    if len(ids) != len(set(ids)):
        issues.append("planned_source_ids_duplicated")
    summaries = [
        _source_summary(
            p, retrievals.get(p.get("source_id")), plan or {}, current_revisions
        )
        for p in planned_sources
    ]
    by_id = {s["source_id"]: s for s in summaries}
    unplanned_sources = sorted(i for i in retrievals if i not in by_id)
    all_complete = (
        population == "planned"
        and bool(summaries)
        and all(s["complete"] for s in summaries)
    )
    by_unit: dict[str, dict[str, Any]] = {}
    for s in summaries:
        if (
            s["kind"] in STATIC_KINDS
            or s["kind"] == "defect"
            or not _text(s.get("unit"))
        ):
            continue
        bucket = by_unit.setdefault(
            s["unit"],
            {"planned": 0, "PASS": 0, "FAIL": 0, "complete": True, "source_ids": []},
        )
        bucket["source_ids"].append(s["source_id"])
        bucket["complete"] = bucket["complete"] and s["complete"]
        bucket["planned"] += s["planned_total"] or 0
        bucket["PASS"] += s["counts"].get("PASS", 0)
        bucket["FAIL"] += s["counts"].get("FAIL", 0)
    for bucket in by_unit.values():
        bucket["pass_rate"] = (
            _rate(bucket["PASS"], bucket["planned"]) if bucket["complete"] else None
        )
    criteria = [
        _criterion(c, by_id)
        for c in (plan or {}).get("exit_criteria", [])
        if isinstance(c, dict)
    ]
    gate_blockers = [
        i
        for i in issues
        if i
        in {
            "plan_not_approved",
            "plan_revision_superseded",
            "planned_sources_missing",
            "planned_source_ids_duplicated",
            "explicit_scope_and_discovery_roots_required",
        }
    ]
    if gate_blockers or population != "planned" or not criteria:
        exit_state = "undetermined"
    elif any(c["status"] == "unsatisfied" for c in criteria):
        exit_state = "unsatisfied"
    elif all(c["status"] == "satisfied" for c in criteria) and all_complete:
        exit_state = "satisfied"
    else:
        exit_state = "undetermined"
    defects = [d for d in data.get("defects", []) if isinstance(d, dict)]
    snapshot_basis = {
        "plan": [plan.get("plan_ref"), plan.get("plan_revision")]
        if plan
        else [scope.get("scope_ref")],
        "sources": [
            [s["source_id"], s["source_revision"], s["retrieved_total"]]
            for s in summaries
        ],
    }
    return {
        "artifact_type": "report_snapshot",
        "schema_version": "1",
        "snapshot_ref": "RPT-" + _digest(snapshot_basis)[:40],
        "population_basis": population,
        "plan_ref": plan.get("plan_ref") if plan else None,
        "plan_revision": plan.get("plan_revision") if plan else None,
        "plan_approval_state": plan_state,
        "scope_ref": (plan or {}).get("scope_ref") or scope.get("scope_ref"),
        "build_ref": (plan or {}).get("build_ref") or scope.get("build_ref"),
        "sources": summaries,
        "unplanned_retrieved_sources": unplanned_sources,
        "by_unit": by_unit,
        "overall": {
            "complete": all_complete,
            "population_known": population == "planned"
            and bool(summaries)
            and all(
                "expected_population_unknown" not in s["issues"] for s in summaries
            ),
            "pass_rate": None,
            "pass_rate_note": "units_are_never_summed_see_by_unit",
        },
        "exit_criteria": criteria,
        "exit_judgement": exit_state,
        "defect_projection": {
            "count": len(defects),
            "issue_refs": sorted(
                str(d.get("external_issue_ref"))
                for d in defects
                if d.get("external_issue_ref")
            ),
            "read_only": True,
        },
        "release_decision": "not_determined_by_this_skill",
        "issues": sorted(set(issues)),
    }


def check_currentness(
    snapshot: dict[str, Any], current: dict[str, Any]
) -> dict[str, Any]:
    """Compare a stored snapshot with current plan and source revisions."""
    stale: list[str] = []
    if snapshot.get("plan_revision") != current.get("plan_revision"):
        stale.append("plan_revision")
    revisions = (
        current.get("source_revisions")
        if isinstance(current.get("source_revisions"), dict)
        else {}
    )
    for source in snapshot.get("sources", []):
        if revisions.get(source.get("source_id")) != source.get("source_revision"):
            stale.append(f"source:{source.get('source_id')}")
    return {"status": "current" if not stale else "stale", "stale": sorted(stale)}


def _load(text: str) -> Any:
    if len(text.encode("utf-8", "replace")) > MAX_INPUT_BYTES:
        raise ValueError("input_too_large")

    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        keys = [key for key, _ in items]
        if len(keys) != len(set(keys)):
            raise ValueError("duplicate_json_key")
        return dict(items)

    return json.loads(text, object_pairs_hook=pairs)


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1 or args[0] not in {"build-snapshot", "check-currentness"}:
        print(
            json.dumps(
                {
                    "status": "blocked",
                    "reason": "usage: reporting_runtime.py <build-snapshot|check-currentness> < input.json",
                }
            )
        )
        return 2
    try:
        data = _load(sys.stdin.buffer.read().decode("utf-8"))
        if not isinstance(data, dict):
            raise ValueError("input_must_be_object")
        result = (
            build_snapshot(data)
            if args[0] == "build-snapshot"
            else check_currentness(data["snapshot"], data["current"])
        )
    except (ValueError, KeyError, TypeError) as exc:
        print(
            json.dumps(
                {"status": "blocked", "reason": f"invalid_input:{type(exc).__name__}"},
                ensure_ascii=True,
            )
        )
        return 2
    print(json.dumps(result, ensure_ascii=True, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
