"""Standalone deterministic cross-technique report snapshot builder.

The helper reads already-retrieved owner results (read-only projection), reconciles
them with the planned source population and returns a snapshot. It never rewrites a
raw result, never turns unknown into zero, and never decides release readiness.
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from typing import Any

PLAN_APPROVED = "approved"
RETRIEVAL_COMPLETE = "complete"
FINAL_STATES = {"PASS", "FAIL", "未実行", "SKIP", "判定不能", "blocked"}
STATIC_STATES = {"reviewed", "not_reviewed", "tool_failed"}
# Only these raw states mean the planned unit was actually started.
STARTED_STATES = {"PASS", "FAIL", "判定不能"}
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


def _instant(value: Any) -> datetime | None:
    if not _text(value):
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _period(value: Any) -> tuple[datetime, datetime] | None:
    """Return a valid closed [from, to] period, or None when absent or invalid."""
    if not isinstance(value, dict):
        return None
    start, end = _instant(value.get("from")), _instant(value.get("to"))
    return (start, end) if start and end and start <= end else None


def _rate(numerator: int, denominator: int) -> float | None:
    return None if denominator <= 0 else round(numerator / denominator, 6)


def _source_summary(
    planned: dict[str, Any],
    retrieval: dict[str, Any] | None,
    plan: dict[str, Any],
    current_revisions: dict[str, str],
    ambiguous_retrieval: bool = False,
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
    if ambiguous_retrieval:
        issues.append("duplicate_retrieval_for_source_id")
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

    declared_period = planned.get("period") or plan.get("period")
    period = _period(declared_period)
    if declared_period is not None and period is None:
        issues.append("period_invalid")
    allowed_states = (
        FINAL_STATES
        if kind in EXECUTION_KINDS
        else STATIC_STATES
        if kind in STATIC_KINDS
        else None
    )
    excluded: list[dict[str, str]] = []
    eligible: dict[str, dict[str, Any]] = {}
    seen_results: dict[str, dict[str, Any]] = {}
    conflicts: set[str] = set()
    unplanned: list[str] = []
    findings: list[dict[str, Any]] = []
    records = retrieved.get("records")
    if records is not None and not isinstance(records, list):
        issues.append("records_must_be_a_list")
        records = []
    for record in records or []:
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
            or (
                unit == "attempt"
                and (
                    not isinstance(record.get("attempt_no"), int)
                    or isinstance(record.get("attempt_no"), bool)
                )
            )
        ):
            issues.append("record_unit_or_identity_invalid")
            continue
        if record["result_ref"] in seen_results:
            if seen_results[record["result_ref"]] == record:
                issues.append("duplicate_result_ref_ignored")
            else:
                issues.append("result_ref_reused_with_different_content")
                conflicts.add(f"result:{record['result_ref']}")
            continue
        seen_results[record["result_ref"]] = record
        if allowed_states is not None and record.get("state") not in allowed_states:
            issues.append("record_state_outside_raw_value_set")
            continue
        if allowed_states is None and not _text(record.get("state")):
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
        if period is not None:
            observed = _instant(record.get("executed_at"))
            if observed is None:
                reason = "period_unverified"
            elif not period[0] <= observed <= period[1]:
                reason = "period_mismatch"
            else:
                reason = None
            if reason:
                excluded.append({"result_ref": record["result_ref"], "reason": reason})
                continue
        key = (
            record["unit_ref"]
            if unit != "attempt"
            else f"{record['unit_ref']}#{record['attempt_no']}"
        )
        if key in eligible or key in conflicts:
            conflicts.add(key)
            eligible.pop(key, None)
            continue
        eligible[key] = record
    unit_conflicts = sorted(c for c in conflicts if not c.startswith("result:"))
    if unit_conflicts:
        issues.append("same_unit_reported_more_than_once_with_different_results")
    if expected_set is not None:
        unplanned = sorted(set(eligible) - expected_set) if unit != "attempt" else []
    planned_records = {
        k: v for k, v in eligible.items() if expected_set is None or k in expected_set
    }
    missing = (
        sorted(expected_set - set(planned_records) - set(unit_conflicts))
        if expected_set is not None
        else []
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
        and not ambiguous_retrieval
        and "period_invalid" not in issues
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
        "conflicting_unit_refs": unit_conflicts,
        "records_digest": _digest(
            sorted(
                [
                    k,
                    v.get("result_ref"),
                    v.get("state"),
                    v.get("result_finalized"),
                    v.get("cleanup_status"),
                ]
                for k, v in planned_records.items()
            )
        ),
        "excluded": sorted(excluded, key=lambda e: e["result_ref"]),
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
        executed = sum(v for k, v in counts.items() if k in STARTED_STATES)
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
    units = {s.get("unit") for s in selected}
    kinds = {s.get("kind") for s in selected}
    allowed_kinds = STATIC_KINDS if metric == "review_completion" else EXECUTION_KINDS
    if len(units) != 1 or not kinds <= allowed_kinds:
        return {
            "criterion_id": cid,
            "status": "unknown",
            "reason": "mixed_units_or_kinds_not_summable"
            if len(units) != 1
            else "metric_not_applicable_to_source_kind",
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
        count = sum(
            s["counts"].get("PASS", 0)
            if metric == "pass_rate"
            else sum(v for k, v in s["counts"].items() if k in STARTED_STATES)
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
    retrievals: dict[Any, dict[str, Any]] = {}
    duplicated_ids: set[Any] = set()
    issues: list[str] = []
    for item in data.get("retrievals", []) or []:
        if not isinstance(item, dict) or not _text(item.get("source_id")):
            issues.append("retrieval_without_source_id")
            continue
        if item["source_id"] in retrievals:
            duplicated_ids.add(item["source_id"])
        retrievals[item["source_id"]] = item
    current_revisions = (
        data.get("current_source_revisions")
        if isinstance(data.get("current_source_revisions"), dict)
        else {}
    )
    if duplicated_ids:
        issues.append("duplicate_retrieval_source_id")
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
        if not _text(plan.get("plan_revision")) or not _text(plan.get("plan_ref")):
            issues.append("plan_ref_and_revision_required")
        current_plan = data.get("current_plan_revision")
        if not _text(current_plan):
            issues.append("plan_currentness_unverified")
        elif current_plan != plan.get("plan_revision"):
            issues.append("plan_revision_superseded")
        if plan.get("period") is not None and _period(plan.get("period")) is None:
            issues.append("plan_period_invalid")
    ids = [p.get("source_id") for p in planned_sources]
    if len(ids) != len(set(ids)):
        issues.append("planned_source_ids_duplicated")
    summaries = [
        _source_summary(
            p,
            None
            if p.get("source_id") in duplicated_ids
            else retrievals.get(p.get("source_id")),
            plan or {},
            current_revisions,
            p.get("source_id") in duplicated_ids,
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
            "plan_currentness_unverified",
            "plan_ref_and_revision_required",
            "plan_period_invalid",
            "duplicate_retrieval_source_id",
            "retrieval_without_source_id",
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
    snapshot = {
        "artifact_type": "report_snapshot",
        "schema_version": "1",
        "population_basis": population,
        "plan_currentness": (
            "not_applicable"
            if plan is None
            else "unverified"
            if "plan_currentness_unverified" in issues
            else "superseded"
            if "plan_revision_superseded" in issues
            else "current"
        ),
        "period": plan.get("period") if plan else None,
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
    # Content-addressed: any difference in counts, completeness, judgement or the
    # retrieved records yields a different ref, so an immutable create-if-absent
    # save can never alias two different snapshots.
    return {"snapshot_ref": "RPT-" + _digest(snapshot)[:40], **snapshot}


def check_currentness(
    snapshot: dict[str, Any], current: dict[str, Any]
) -> dict[str, Any]:
    """Compare a stored snapshot with fresh plan and source revisions.

    A revision that changed is `stale`; a revision that could not be read now is
    `unverified`. Neither is `current`.
    """
    stale: list[str] = []
    unverified: list[str] = []
    if snapshot.get("population_basis") == "planned":
        if not _text(current.get("plan_revision")):
            unverified.append("plan_revision")
        elif current["plan_revision"] != snapshot.get("plan_revision"):
            stale.append("plan_revision")
    revisions = (
        current.get("source_revisions")
        if isinstance(current.get("source_revisions"), dict)
        else {}
    )
    for source in snapshot.get("sources", []):
        name = f"source:{source.get('source_id')}"
        fresh = revisions.get(source.get("source_id"))
        if not _text(fresh):
            unverified.append(name)
        elif fresh != source.get("source_revision"):
            stale.append(name)
    status = "stale" if stale else "unverified" if unverified else "current"
    return {
        "status": status,
        "stale": sorted(stale),
        "unverified": sorted(unverified),
    }


def _read_stdin() -> str:
    """Read at most MAX_INPUT_BYTES of UTF-8 from stdin, independent of the locale."""
    raw = sys.stdin.buffer.read(MAX_INPUT_BYTES + 1)
    if len(raw) > MAX_INPUT_BYTES:
        raise ValueError("input_too_large")
    return raw.decode("utf-8")


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
        data = _load(_read_stdin())
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
