"""Skill-local deterministic Regression snapshot, routing, and Activity helpers."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


LIFECYCLE = {"current", "unresolved", "stale", "deleted", "superseded"}
MEMBERSHIP = {"member", "one_off", "out_of_scope", "unresolved"}
ACTIVITY_STATES = {"未開始", "実行中", "部分完了（ブロック中あり）", "ブロック中", "完了"}


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _revision_map(items: Any) -> tuple[dict[str, str], list[str]]:
    mapping: dict[str, str] = {}
    errors: list[str] = []
    if not isinstance(items, list):
        return {}, ["source_revisions_not_list"]
    for item in items:
        if not isinstance(item, dict):
            errors.append("invalid_source_revision")
            continue
        ref, revision = item.get("source_ref"), item.get("revision")
        if not isinstance(ref, str) or not ref.strip() or not isinstance(revision, str) or not revision.strip():
            errors.append("missing_source_ref_or_revision")
            continue
        if ref in mapping:
            errors.append(f"duplicate_source_revision:{ref}")
        mapping[ref] = revision
    return mapping, errors


def build_discovery_snapshot(data: dict[str, Any]) -> dict[str, Any]:
    """Freeze complete source listings and owner-resolved TC projections."""
    roots = data.get("discovery_roots")
    roots_ok = isinstance(roots, list) and bool(roots) and all(isinstance(x, str) and x.strip() for x in roots)
    revisions, errors = _revision_map(data.get("source_revisions"))
    if not roots_ok:
        errors.append("authoritative_discovery_roots_missing")
    cases = data.get("cases")
    if not isinstance(cases, list):
        cases = []
        errors.append("cases_not_list")
    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    lifecycle_unresolved: list[str] = []
    for case in cases:
        if not isinstance(case, dict):
            errors.append("invalid_case_projection")
            continue
        tc_ref, source_ref = case.get("tc_ref"), case.get("source_ref")
        source_revision, lifecycle = case.get("source_revision"), case.get("lifecycle_status")
        if not isinstance(tc_ref, str) or not tc_ref or not isinstance(source_ref, str) or not source_ref:
            errors.append("missing_tc_or_source_ref")
            continue
        if tc_ref in seen:
            errors.append(f"duplicate_tc_ref:{tc_ref}")
        seen.add(tc_ref)
        if lifecycle not in LIFECYCLE:
            errors.append(f"invalid_lifecycle_projection:{tc_ref}")
            lifecycle = "unresolved"
        if lifecycle in {"unresolved", "stale"}:
            lifecycle_unresolved.append(tc_ref)
        if not isinstance(source_revision, str) or revisions.get(source_ref) != source_revision:
            errors.append(f"source_revision_mismatch:{tc_ref}")
        normalized.append({
            "tc_ref": tc_ref,
            "source_ref": source_ref,
            "source_revision": source_revision,
            "lifecycle_status": lifecycle,
            "content_fingerprint": case.get("content_fingerprint"),
        })
    normalized.sort(key=lambda item: (item["tc_ref"], item["source_ref"]))
    discovery_complete = bool(data.get("listing_complete")) and roots_ok and not any("source_revision" in issue or "source_ref" in issue or "roots" in issue or "cases_not" in issue or "duplicate_tc_ref" in issue for issue in errors)
    lifecycle_complete = not lifecycle_unresolved
    source_snapshot = {
        "discovery_roots": sorted(set(roots)) if roots_ok else [],
        "source_revisions": [{"source_ref": ref, "revision": revisions[ref]} for ref in sorted(revisions)],
        "cases": normalized,
    }
    snapshot_ref = f"DS-{_digest(source_snapshot)}"
    return {
        "snapshot_ref": snapshot_ref,
        **source_snapshot,
        "listing_complete": bool(data.get("listing_complete")),
        "discovery_complete": discovery_complete,
        "lifecycle_complete": lifecycle_complete,
        "complete": discovery_complete and lifecycle_complete and not errors,
        "unresolved_tc_refs": sorted(set(lifecycle_unresolved)),
        "issues": errors,
    }


def deterministic_batch(snapshot: dict[str, Any], *, offset: int, limit: int, expected_snapshot_ref: str | None = None) -> dict[str, Any]:
    if offset < 0 or limit <= 0:
        return {"status": "blocked", "reason": "invalid_batch_bounds"}
    if expected_snapshot_ref and expected_snapshot_ref != snapshot.get("snapshot_ref"):
        return {"status": "new_snapshot_required", "reason": "source_snapshot_changed", "snapshot_ref": snapshot.get("snapshot_ref")}
    cases = snapshot.get("cases", [])
    return {
        "status": "ready",
        "snapshot_ref": snapshot.get("snapshot_ref"),
        "offset": offset,
        "limit": limit,
        "tc_refs": [case["tc_ref"] for case in cases[offset:offset + limit]],
        "next_offset": min(offset + limit, len(cases)),
        "complete": offset + limit >= len(cases) and bool(snapshot.get("complete")),
    }


def reconcile_membership(snapshot: dict[str, Any], decisions: list[dict[str, Any]]) -> dict[str, Any]:
    cases = {case["tc_ref"]: case for case in snapshot.get("cases", []) if case.get("lifecycle_status") == "current"}
    decision_by_ref: dict[str, dict[str, Any]] = {}
    issues: list[str] = []
    for decision in decisions:
        ref = decision.get("tc_ref")
        if not isinstance(ref, str) or ref in decision_by_ref:
            issues.append("missing_or_duplicate_membership_decision")
            continue
        if ref not in cases:
            issues.append(f"decision_for_noncurrent_or_unknown_tc:{ref}")
        if decision.get("decision") not in MEMBERSHIP or not str(decision.get("reason", "")).strip():
            issues.append(f"invalid_membership_decision:{ref}")
        decision_by_ref[ref] = decision
    undecided = sorted(set(cases) - set(decision_by_ref))
    member_refs = sorted(ref for ref, item in decision_by_ref.items() if item.get("decision") == "member" and ref in cases)
    one_off = sorted(ref for ref, item in decision_by_ref.items() if item.get("decision") == "one_off" and ref in cases)
    complete = bool(snapshot.get("complete")) and not undecided and not issues
    memberships = [
        {
            **decision_by_ref[ref],
            "tc_ref": ref,
            "lifecycle_status": cases[ref]["lifecycle_status"],
        }
        for ref in sorted(decision_by_ref)
        if ref in cases
    ]
    return {
        "snapshot_ref": snapshot.get("snapshot_ref"),
        "memberships": memberships,
        "member_tc_refs": member_refs,
        "one_off_tc_refs": one_off,
        "unresolved_tc_refs": sorted(set(snapshot.get("unresolved_tc_refs", [])) | {ref for ref, item in decision_by_ref.items() if item.get("decision") == "unresolved"}),
        "undecided_tc_refs": undecided,
        "complete": complete,
        "issues": issues,
    }


def check_baseline_currentness(baseline: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
    if baseline.get("complete") is not True:
        return {"status": "incomplete", "changed_sources": [], "reason": "baseline_incomplete"}
    if current.get("complete") is not True:
        return {"status": "unresolved", "changed_sources": [], "reason": "current_discovery_incomplete"}
    baseline_scope = baseline.get("scope_identity")
    current_scope = current.get("scope_identity")
    if not isinstance(baseline_scope, str) or not baseline_scope.strip():
        return {"status": "incomplete", "changed_sources": [], "reason": "baseline_scope_identity_missing"}
    if not isinstance(current_scope, str) or not current_scope.strip():
        return {"status": "unresolved", "changed_sources": [], "reason": "current_scope_identity_missing"}
    old, old_errors = _revision_map(baseline.get("source_revisions"))
    if old_errors:
        return {"status": "incomplete", "changed_sources": [], "reason": "baseline_source_revisions_invalid"}
    new, new_errors = _revision_map(current.get("source_revisions"))
    if new_errors:
        return {"status": "unresolved", "changed_sources": [], "reason": "current_source_revisions_invalid"}
    changed = sorted(ref for ref in set(old) | set(new) if old.get(ref) != new.get(ref))
    if baseline_scope != current_scope:
        changed.append("<scope>")
    return {"status": "stale" if changed else "current", "changed_sources": changed, "reason": "dependency_changed" if changed else "dependencies_match"}


def plan_run(baseline: dict[str, Any], *, requested_scope: str | None, requested_tc_refs: list[str] | None = None, candidate_query_complete: bool = True, currentness: dict[str, Any] | None = None) -> dict[str, Any]:
    if currentness is None:
        return {"status": "blocked", "reason": "baseline_currentness_unverified", "selected_tc_refs": []}
    if currentness.get("status") != "current":
        return {"status": "blocked", "reason": "baseline_not_current", "selected_tc_refs": []}
    if requested_scope == "full":
        if baseline.get("complete") is not True:
            return {"status": "blocked", "reason": "full_requires_complete_baseline", "selected_tc_refs": []}
    elif requested_scope not in {None, "selected"}:
        return {"status": "blocked", "reason": "invalid_scope", "selected_tc_refs": []}
    if requested_scope == "selected":
        selected = sorted(set(requested_tc_refs or []))
        if not selected:
            return {"status": "unresolved", "reason": "selected_scope_empty", "selected_tc_refs": []}

    needs_members = requested_scope in {"full", "selected"} or (
        requested_scope is None and not candidate_query_complete and baseline.get("complete") is True
    )
    members: set[str] = set()
    if needs_members:
        raw_members = baseline.get("member_tc_refs")
        if not isinstance(raw_members, list) or any(not isinstance(ref, str) or not ref.strip() for ref in raw_members) or len(raw_members) != len(set(raw_members)):
            return {"status": "blocked", "reason": "baseline_member_projection_invalid", "selected_tc_refs": []}
        members = set(raw_members)
        if "memberships" in baseline:
            memberships = baseline.get("memberships")
            if not isinstance(memberships, list):
                return {"status": "blocked", "reason": "baseline_membership_projection_invalid", "selected_tc_refs": []}
            membership_refs: set[str] = set()
            expected_members: set[str] = set()
            for item in memberships:
                if not isinstance(item, dict):
                    return {"status": "blocked", "reason": "baseline_membership_projection_invalid", "selected_tc_refs": []}
                tc_ref = item.get("tc_ref")
                decision = item.get("decision")
                if not isinstance(tc_ref, str) or not tc_ref.strip() or tc_ref in membership_refs or decision not in MEMBERSHIP:
                    return {"status": "blocked", "reason": "baseline_membership_projection_invalid", "selected_tc_refs": []}
                membership_refs.add(tc_ref)
                if decision == "member":
                    if item.get("lifecycle_status") != "current":
                        return {"status": "blocked", "reason": "baseline_membership_projection_invalid", "selected_tc_refs": []}
                    expected_members.add(tc_ref)
            if members != expected_members:
                return {"status": "blocked", "reason": "baseline_membership_projection_mismatch", "selected_tc_refs": []}

    if requested_scope == "full":
        return {"status": "ready", "scope": "full", "selected_tc_refs": sorted(members), "suite_complete": True}
    if requested_scope == "selected":
        unknown = sorted(set(selected) - members)
        if unknown:
            return {"status": "unresolved", "reason": "selected_tc_not_in_current_suite", "unresolved_tc_refs": unknown, "selected_tc_refs": []}
        return {"status": "ready", "scope": "selected", "selected_tc_refs": selected, "suite_complete": False}
    if not candidate_query_complete and baseline.get("complete") is True:
        return {"status": "ready", "scope": "full", "selected_tc_refs": sorted(members), "suite_complete": True, "fallback_reason": "candidate_query_incomplete"}
    if not candidate_query_complete:
        return {"status": "blocked", "reason": "candidate_query_and_baseline_incomplete", "selected_tc_refs": []}
    return {"status": "unresolved", "reason": "run_scope_required", "selected_tc_refs": []}


def select_auxiliary_testware(*, requested_refs: list[str], user_explicit_refs: list[str], policy_refs: list[str], available_refs: list[str]) -> dict[str, Any]:
    authorized = set(user_explicit_refs) | set(policy_refs)
    available = set(available_refs)
    requested = set(requested_refs)
    unauthorized = sorted(requested - authorized)
    missing = sorted(requested - available)
    if unauthorized or missing:
        return {"status": "unresolved", "selected_refs": [], "unauthorized_refs": unauthorized, "missing_refs": missing}
    return {"status": "ready", "selected_refs": sorted(requested), "tc_member_count": 0, "tc_coverage_refs": []}


def validate_required_routes(routes: list[dict[str, Any]]) -> dict[str, Any]:
    issues: list[str] = []
    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for route in routes:
        tc_ref = route.get("tc_ref")
        kind = route.get("route_type")
        route_ref = route.get("route_ref")
        if kind not in {"manual", "e2e"}:
            issues.append(f"invalid_required_route_type:{tc_ref}")
        if not isinstance(tc_ref, str) or not tc_ref or not isinstance(route_ref, str) or not route_ref:
            issues.append("missing_tc_or_route_ref")
        if kind == "e2e" and not route.get("e2e_testware_ref"):
            issues.append(f"missing_e2e_testware_ref:{tc_ref}")
        key = f"{tc_ref}|{route_ref}"
        if key in seen:
            issues.append(f"duplicate_required_route:{key}")
        seen.add(key)
        normalized.append({"tc_ref": tc_ref, "route_type": kind, "route_ref": route_ref, "e2e_testware_ref": route.get("e2e_testware_ref")})
    return {"routes": normalized, "valid": not issues, "issues": issues}


def project_activity(run: dict[str, Any], source_executions: dict[str, dict[str, Any]], *, cleanup_status: str = "対象なし", unresolved: list[Any] | None = None) -> dict[str, Any]:
    routes = run.get("required_routes", [])
    projected: list[dict[str, Any]] = []
    by_tc: dict[str, list[dict[str, Any]]] = {}
    for route in routes:
        execution_ref = route.get("execution_ref")
        source = source_executions.get(execution_ref, {}) if execution_ref else {}
        start_state = source.get("start_state", "未開始")
        actual_start = start_state == "開始済み" and source.get("actual_start_confirmed") is True
        source_result = source.get("source_result")
        result_finalized = source.get("result_finalized") is True
        source_result_projectable = isinstance(source_result, str) and bool(source_result.strip())
        item = {
            "tc_ref": route.get("tc_ref"),
            "route_ref": route.get("route_ref"),
            "execution_ref": execution_ref,
            "source_start_state": start_state,
            "source_result": source_result,
            "result_finalized": result_finalized,
            "source_result_projectable": source_result_projectable,
            "evidence_refs": list(source.get("evidence_refs", [])),
            "executed": actual_start,
            "blocked": not actual_start and source.get("blocked") is True,
        }
        projected.append(item)
        by_tc.setdefault(str(route.get("tc_ref")), []).append(item)
    auxiliary_projected: list[dict[str, Any]] = []
    for route in run.get("auxiliary_routes", []):
        execution_ref = route.get("execution_ref")
        source = source_executions.get(execution_ref, {}) if execution_ref else {}
        actual_start = source.get("start_state") == "開始済み" and source.get("actual_start_confirmed") is True
        source_result = source.get("source_result")
        auxiliary_projected.append({
            "testware_ref": route.get("testware_ref"),
            "execution_ref": execution_ref,
            "source_start_state": source.get("start_state", "未開始"),
            "source_result": source_result,
            "result_finalized": source.get("result_finalized") is True,
            "source_result_projectable": isinstance(source_result, str) and bool(source_result.strip()),
            "evidence_refs": list(source.get("evidence_refs", [])),
            "executed": actual_start,
            "blocked": not actual_start and source.get("blocked") is True,
        })
    tc_states = {}
    for tc_ref, items in by_tc.items():
        started = all(item["executed"] for item in items)
        blocked = any(item["blocked"] for item in items)
        tc_states[tc_ref] = "executed" if started else ("blocked" if blocked else "unexecuted")
    started_count = sum(state == "executed" for state in tc_states.values())
    blocked_count = sum(state == "blocked" for state in tc_states.values())
    unexecuted_count = sum(state == "unexecuted" for state in tc_states.values())
    result_counts: dict[str, int] = {}
    for item in projected:
        value = item.get("source_result")
        if item["executed"] and isinstance(value, str) and value:
            result_counts[value] = result_counts.get(value, 0) + 1
    auxiliary_result_counts: dict[str, int] = {}
    for item in auxiliary_projected:
        value = item.get("source_result")
        if item["executed"] and isinstance(value, str) and value:
            auxiliary_result_counts[value] = auxiliary_result_counts.get(value, 0) + 1
    unresolved_values = list(unresolved or [])
    if cleanup_status in {"失敗", "未確認", "一部失敗"} or unresolved_values:
        state = "部分完了（ブロック中あり）" if started_count else "ブロック中"
    elif unexecuted_count or blocked_count:
        state = "部分完了（ブロック中あり）" if started_count else "ブロック中"
    elif routes and any(
        not (item["result_finalized"] and item["source_result_projectable"])
        for item in projected
    ):
        state = "実行中"
    elif routes:
        state = "完了"
    else:
        state = "未開始"
    return {
        "activity_state": state,
        "route_results": projected,
        "auxiliary_route_results": auxiliary_projected,
        "tc_execution_state": tc_states,
        "counts": {"tc_member_count": len(by_tc), "executed_tc_count": started_count, "unexecuted_tc_count": unexecuted_count, "blocked_tc_count": blocked_count, "source_result_counts": result_counts, "auxiliary_testware_count": len(auxiliary_projected), "auxiliary_executed_count": sum(1 for item in auxiliary_projected if item["executed"]), "auxiliary_source_result_counts": auxiliary_result_counts},
        "cleanup_status": cleanup_status,
        "unresolved": unresolved_values,
    }


def update_activity(existing: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    if existing.get("activity_state") == "完了":
        return {"status": "blocked", "reason": "completed_activity_is_immutable"}
    if existing.get("scope_identity") != incoming.get("scope_identity") or existing.get("snapshot_ref") != incoming.get("snapshot_ref"):
        return {"status": "new_activity_required", "reason": "scope_or_snapshot_changed"}
    return {"status": "update_allowed", "activity": incoming}


def scan_activity_files(root: str | Path, *, listing_complete: bool = True) -> dict[str, Any]:
    """Fixed-root direct scan; callers must report listing truncation or failures."""
    try:
        files = sorted((p for p in Path(root).rglob("*.json") if p.is_file() and not p.is_symlink()), key=lambda p: p.as_posix())
    except OSError as exc:
        return {"activity_refs": [], "complete": False, "unresolved": [f"scan_failed:{type(exc).__name__}"]}
    return {"activity_refs": [p.stem for p in files], "complete": bool(listing_complete), "unresolved": [] if listing_complete else ["listing_incomplete_or_truncated"]}
