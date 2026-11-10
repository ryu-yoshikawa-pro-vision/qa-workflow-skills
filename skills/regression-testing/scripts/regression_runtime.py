"""Skill-local deterministic Regression snapshot, routing, and Activity helpers."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

LIFECYCLE = {"current", "unresolved", "stale", "deleted", "superseded"}
MEMBERSHIP = {"member", "one_off", "out_of_scope", "unresolved"}
ACTIVITY_STATES = {
    "未開始",
    "実行中",
    "部分完了（ブロック中あり）",
    "ブロック中",
    "完了",
}
# Run / Activityのroute契約version。未設定は旧形式（補助testwareの実施義務なし）。
ROUTE_CONTRACT_VERSION = "2"
REQUIRED_ROUTE_TYPES = {"manual", "e2e", "testware"}
TESTWARE_ROUTE_OWNER = "testware-execution"
AUXILIARY_OWNERS = {"e2e-test-execution", "testware-execution"}
AUXILIARY_REQUIRED_BASES = {"user_explicit", "policy"}
AUXILIARY_BASES = AUXILIARY_REQUIRED_BASES | {"reference_only"}
CLEANUP_CLOSED = {"成功", "対象なし", "意図的に残した状態"}


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


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
        if (
            not isinstance(ref, str)
            or not ref.strip()
            or not isinstance(revision, str)
            or not revision.strip()
        ):
            errors.append("missing_source_ref_or_revision")
            continue
        if ref in mapping:
            errors.append(f"duplicate_source_revision:{ref}")
        mapping[ref] = revision
    return mapping, errors


def _membership_revision_map(membership: Any) -> tuple[dict[str, str], list[str]]:
    errors: list[str] = []
    source_refs = (
        membership.get("source_refs") if isinstance(membership, dict) else None
    )
    if (
        not isinstance(source_refs, list)
        or not source_refs
        or any(not isinstance(ref, str) or not ref.strip() for ref in source_refs)
    ):
        errors.append("membership_source_refs_invalid")
    elif len(source_refs) != len(set(source_refs)):
        errors.append("duplicate_membership_source_ref")

    source_revisions = (
        membership.get("source_revisions") if isinstance(membership, dict) else None
    )
    revisions: dict[str, str] = {}
    if not isinstance(source_revisions, list) or not source_revisions:
        errors.append("membership_source_revisions_invalid")
    else:
        for item in source_revisions:
            if not isinstance(item, dict):
                errors.append("invalid_membership_source_revision")
                continue
            source_ref, revision = item.get("source_ref"), item.get("revision")
            if (
                not isinstance(source_ref, str)
                or not source_ref.strip()
                or not isinstance(revision, str)
                or not revision.strip()
            ):
                errors.append("missing_membership_source_ref_or_revision")
                continue
            if source_ref in revisions:
                errors.append(f"duplicate_membership_source_revision:{source_ref}")
            revisions[source_ref] = revision

    if isinstance(source_refs, list) and all(
        isinstance(ref, str) and ref.strip() for ref in source_refs
    ):
        if set(source_refs) != set(revisions):
            errors.append("membership_source_refs_revision_mismatch")
    return revisions, errors


def build_discovery_snapshot(data: dict[str, Any]) -> dict[str, Any]:
    """Freeze complete source listings and owner-resolved TC projections."""
    roots = data.get("discovery_roots")
    roots_ok = (
        isinstance(roots, list)
        and bool(roots)
        and all(isinstance(x, str) and x.strip() for x in roots)
    )
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
        source_revision, lifecycle = (
            case.get("source_revision"),
            case.get("lifecycle_status"),
        )
        if (
            not isinstance(tc_ref, str)
            or not tc_ref
            or not isinstance(source_ref, str)
            or not source_ref
        ):
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
        if (
            not isinstance(source_revision, str)
            or revisions.get(source_ref) != source_revision
        ):
            errors.append(f"source_revision_mismatch:{tc_ref}")
        normalized.append(
            {
                "tc_ref": tc_ref,
                "source_ref": source_ref,
                "source_revision": source_revision,
                "lifecycle_status": lifecycle,
                "content_fingerprint": case.get("content_fingerprint"),
            }
        )
    normalized.sort(key=lambda item: (item["tc_ref"], item["source_ref"]))
    discovery_complete = (
        bool(data.get("listing_complete"))
        and roots_ok
        and not any(
            "source_revision" in issue
            or "source_ref" in issue
            or "roots" in issue
            or "cases_not" in issue
            or "duplicate_tc_ref" in issue
            for issue in errors
        )
    )
    lifecycle_complete = not lifecycle_unresolved
    source_snapshot = {
        "discovery_roots": sorted(set(roots)) if roots_ok else [],
        "source_revisions": [
            {"source_ref": ref, "revision": revisions[ref]} for ref in sorted(revisions)
        ],
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


def deterministic_batch(
    snapshot: dict[str, Any],
    *,
    offset: int,
    limit: int,
    expected_snapshot_ref: str | None = None,
) -> dict[str, Any]:
    if offset < 0 or limit <= 0:
        return {"status": "blocked", "reason": "invalid_batch_bounds"}
    if expected_snapshot_ref and expected_snapshot_ref != snapshot.get("snapshot_ref"):
        return {
            "status": "new_snapshot_required",
            "reason": "source_snapshot_changed",
            "snapshot_ref": snapshot.get("snapshot_ref"),
        }
    cases = snapshot.get("cases", [])
    return {
        "status": "ready",
        "snapshot_ref": snapshot.get("snapshot_ref"),
        "offset": offset,
        "limit": limit,
        "tc_refs": [case["tc_ref"] for case in cases[offset : offset + limit]],
        "next_offset": min(offset + limit, len(cases)),
        "complete": offset + limit >= len(cases) and bool(snapshot.get("complete")),
    }


def reconcile_membership(
    snapshot: dict[str, Any], decisions: list[dict[str, Any]]
) -> dict[str, Any]:
    cases = {
        case["tc_ref"]: case
        for case in snapshot.get("cases", [])
        if case.get("lifecycle_status") == "current"
    }
    decision_by_ref: dict[str, dict[str, Any]] = {}
    issues: list[str] = []
    for decision in decisions:
        ref = decision.get("tc_ref")
        if not isinstance(ref, str) or ref in decision_by_ref:
            issues.append("missing_or_duplicate_membership_decision")
            continue
        if ref not in cases:
            issues.append(f"decision_for_noncurrent_or_unknown_tc:{ref}")
        if (
            decision.get("decision") not in MEMBERSHIP
            or not str(decision.get("reason", "")).strip()
        ):
            issues.append(f"invalid_membership_decision:{ref}")
        _, provenance_errors = _membership_revision_map(decision)
        if provenance_errors:
            issues.append(f"invalid_membership_provenance:{ref}")
        decision_by_ref[ref] = decision
    undecided = sorted(set(cases) - set(decision_by_ref))
    member_refs = sorted(
        ref
        for ref, item in decision_by_ref.items()
        if item.get("decision") == "member" and ref in cases
    )
    one_off = sorted(
        ref
        for ref, item in decision_by_ref.items()
        if item.get("decision") == "one_off" and ref in cases
    )
    unresolved_decisions = {
        ref
        for ref, item in decision_by_ref.items()
        if item.get("decision") == "unresolved"
    }
    complete = (
        bool(snapshot.get("complete"))
        and not undecided
        and not unresolved_decisions
        and not issues
    )
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
        "unresolved_tc_refs": sorted(
            set(snapshot.get("unresolved_tc_refs", []))
            | {
                ref
                for ref, item in decision_by_ref.items()
                if item.get("decision") == "unresolved"
            }
        ),
        "undecided_tc_refs": undecided,
        "complete": complete,
        "issues": issues,
    }


def check_baseline_currentness(
    baseline: dict[str, Any], current: dict[str, Any]
) -> dict[str, Any]:
    if baseline.get("complete") is not True:
        return {
            "status": "incomplete",
            "changed_sources": [],
            "reason": "baseline_incomplete",
        }
    unresolved_refs = baseline.get("unresolved_tc_refs")
    undecided_refs = baseline.get("undecided_tc_refs")
    if (
        not isinstance(unresolved_refs, list)
        or unresolved_refs
        or not isinstance(undecided_refs, list)
        or undecided_refs
    ):
        return {
            "status": "incomplete",
            "changed_sources": [],
            "reason": "baseline_membership_completion_invalid",
        }
    if current.get("complete") is not True:
        return {
            "status": "unresolved",
            "changed_sources": [],
            "reason": "current_discovery_incomplete",
        }
    baseline_scope = baseline.get("scope_identity")
    current_scope = current.get("scope_identity")
    if not isinstance(baseline_scope, str) or not baseline_scope.strip():
        return {
            "status": "incomplete",
            "changed_sources": [],
            "reason": "baseline_scope_identity_missing",
        }
    if not isinstance(current_scope, str) or not current_scope.strip():
        return {
            "status": "unresolved",
            "changed_sources": [],
            "reason": "current_scope_identity_missing",
        }
    baseline_snapshot_ref = baseline.get("discovery_snapshot_ref")
    current_snapshot_ref = current.get("snapshot_ref")
    if not isinstance(baseline_snapshot_ref, str) or not baseline_snapshot_ref.strip():
        return {
            "status": "incomplete",
            "changed_sources": [],
            "reason": "baseline_discovery_snapshot_ref_missing",
        }
    if not isinstance(current_snapshot_ref, str) or not current_snapshot_ref.strip():
        return {
            "status": "unresolved",
            "changed_sources": [],
            "reason": "current_discovery_snapshot_ref_missing",
        }
    old, old_errors = _revision_map(baseline.get("source_revisions"))
    if old_errors:
        return {
            "status": "incomplete",
            "changed_sources": [],
            "reason": "baseline_source_revisions_invalid",
        }
    if not old:
        return {
            "status": "incomplete",
            "changed_sources": [],
            "reason": "baseline_source_revisions_empty",
        }
    memberships = baseline.get("memberships")
    if not isinstance(memberships, list):
        return {
            "status": "incomplete",
            "changed_sources": [],
            "reason": "baseline_memberships_invalid",
        }
    membership_revisions: dict[str, str] = {}
    membership_refs: set[str] = set()
    for membership in memberships:
        if not isinstance(membership, dict):
            return {
                "status": "incomplete",
                "changed_sources": [],
                "reason": "baseline_memberships_invalid",
            }
        tc_ref = membership.get("tc_ref")
        decision = membership.get("decision")
        if (
            not isinstance(tc_ref, str)
            or not tc_ref.strip()
            or tc_ref in membership_refs
            or not isinstance(decision, str)
            or decision not in MEMBERSHIP
        ):
            return {
                "status": "incomplete",
                "changed_sources": [],
                "reason": "baseline_memberships_invalid",
            }
        membership_refs.add(tc_ref)
        if decision == "unresolved":
            return {
                "status": "incomplete",
                "changed_sources": [],
                "reason": "baseline_membership_completion_invalid",
            }
        revisions, errors = _membership_revision_map(membership)
        if errors:
            return {
                "status": "incomplete",
                "changed_sources": [],
                "reason": "baseline_membership_provenance_invalid",
            }
        for source_ref, revision in revisions.items():
            if (
                source_ref in membership_revisions
                and membership_revisions[source_ref] != revision
            ):
                return {
                    "status": "incomplete",
                    "changed_sources": [],
                    "reason": "baseline_membership_revision_conflict",
                }
            if old.get(source_ref) != revision:
                return {
                    "status": "incomplete",
                    "changed_sources": [],
                    "reason": "baseline_membership_revision_missing",
                }
            membership_revisions[source_ref] = revision
    current_cases = current.get("cases")
    if not isinstance(current_cases, list):
        return {
            "status": "unresolved",
            "changed_sources": [],
            "reason": "current_discovery_cases_invalid",
        }
    current_tc_refs: set[str] = set()
    seen_current_refs: set[str] = set()
    for case in current_cases:
        if not isinstance(case, dict):
            return {
                "status": "unresolved",
                "changed_sources": [],
                "reason": "current_discovery_cases_invalid",
            }
        tc_ref = case.get("tc_ref")
        lifecycle = case.get("lifecycle_status")
        if (
            not isinstance(tc_ref, str)
            or not tc_ref.strip()
            or tc_ref in seen_current_refs
            or not isinstance(lifecycle, str)
            or lifecycle not in LIFECYCLE
        ):
            return {
                "status": "unresolved",
                "changed_sources": [],
                "reason": "current_discovery_cases_invalid",
            }
        seen_current_refs.add(tc_ref)
        if lifecycle == "current":
            current_tc_refs.add(tc_ref)
    population_mismatch = current_tc_refs != membership_refs
    snapshot_changed = baseline_snapshot_ref != current_snapshot_ref
    if population_mismatch and not snapshot_changed:
        return {
            "status": "incomplete",
            "changed_sources": [],
            "reason": "baseline_membership_population_mismatch",
        }
    new, new_errors = _revision_map(current.get("source_revisions"))
    if new_errors:
        return {
            "status": "unresolved",
            "changed_sources": [],
            "reason": "current_source_revisions_invalid",
        }
    missing_current = sorted(set(old) - set(new))
    if missing_current:
        return {
            "status": "unresolved",
            "changed_sources": missing_current,
            "reason": "current_source_revision_missing",
        }
    changed = sorted(ref for ref in set(old) | set(new) if old.get(ref) != new.get(ref))
    if baseline_scope != current_scope:
        changed.append("<scope>")
    if snapshot_changed:
        changed.append("<discovery_snapshot>")
    changed.sort()
    return {
        "status": "stale" if changed else "current",
        "changed_sources": changed,
        "reason": "dependency_changed" if changed else "dependencies_match",
    }


def plan_run(
    baseline: dict[str, Any],
    *,
    requested_scope: str | None,
    requested_tc_refs: list[str] | None = None,
    candidate_query_complete: bool = True,
    currentness: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if currentness is None:
        return {
            "status": "blocked",
            "reason": "baseline_currentness_unverified",
            "selected_tc_refs": [],
        }
    if currentness.get("status") != "current":
        return {
            "status": "blocked",
            "reason": "baseline_not_current",
            "selected_tc_refs": [],
        }
    if requested_scope == "full":
        if baseline.get("complete") is not True:
            return {
                "status": "blocked",
                "reason": "full_requires_complete_baseline",
                "selected_tc_refs": [],
            }
    elif requested_scope not in {None, "selected"}:
        return {"status": "blocked", "reason": "invalid_scope", "selected_tc_refs": []}
    if requested_scope == "selected":
        selected = sorted(set(requested_tc_refs or []))
        if not selected:
            return {
                "status": "unresolved",
                "reason": "selected_scope_empty",
                "selected_tc_refs": [],
            }

    needs_members = requested_scope in {"full", "selected"} or (
        requested_scope is None
        and not candidate_query_complete
        and baseline.get("complete") is True
    )
    members: set[str] = set()
    if needs_members:
        raw_members = baseline.get("member_tc_refs")
        if (
            not isinstance(raw_members, list)
            or any(not isinstance(ref, str) or not ref.strip() for ref in raw_members)
            or len(raw_members) != len(set(raw_members))
        ):
            return {
                "status": "blocked",
                "reason": "baseline_member_projection_invalid",
                "selected_tc_refs": [],
            }
        members = set(raw_members)
        if "memberships" in baseline:
            memberships = baseline.get("memberships")
            if not isinstance(memberships, list):
                return {
                    "status": "blocked",
                    "reason": "baseline_membership_projection_invalid",
                    "selected_tc_refs": [],
                }
            membership_refs: set[str] = set()
            expected_members: set[str] = set()
            for item in memberships:
                if not isinstance(item, dict):
                    return {
                        "status": "blocked",
                        "reason": "baseline_membership_projection_invalid",
                        "selected_tc_refs": [],
                    }
                tc_ref = item.get("tc_ref")
                decision = item.get("decision")
                if (
                    not isinstance(tc_ref, str)
                    or not tc_ref.strip()
                    or tc_ref in membership_refs
                    or decision not in MEMBERSHIP
                ):
                    return {
                        "status": "blocked",
                        "reason": "baseline_membership_projection_invalid",
                        "selected_tc_refs": [],
                    }
                membership_refs.add(tc_ref)
                if decision == "member":
                    if item.get("lifecycle_status") != "current":
                        return {
                            "status": "blocked",
                            "reason": "baseline_membership_projection_invalid",
                            "selected_tc_refs": [],
                        }
                    expected_members.add(tc_ref)
            if members != expected_members:
                return {
                    "status": "blocked",
                    "reason": "baseline_membership_projection_mismatch",
                    "selected_tc_refs": [],
                }

    if requested_scope == "full":
        return {
            "status": "ready",
            "scope": "full",
            "selected_tc_refs": sorted(members),
            "suite_complete": True,
        }
    if requested_scope == "selected":
        unknown = sorted(set(selected) - members)
        if unknown:
            return {
                "status": "unresolved",
                "reason": "selected_tc_not_in_current_suite",
                "unresolved_tc_refs": unknown,
                "selected_tc_refs": [],
            }
        return {
            "status": "ready",
            "scope": "selected",
            "selected_tc_refs": selected,
            "suite_complete": False,
        }
    if not candidate_query_complete and baseline.get("complete") is True:
        return {
            "status": "ready",
            "scope": "full",
            "selected_tc_refs": sorted(members),
            "suite_complete": True,
            "fallback_reason": "candidate_query_incomplete",
        }
    if not candidate_query_complete:
        return {
            "status": "blocked",
            "reason": "candidate_query_and_baseline_incomplete",
            "selected_tc_refs": [],
        }
    return {
        "status": "unresolved",
        "reason": "run_scope_required",
        "selected_tc_refs": [],
    }


def select_auxiliary_testware(
    *,
    requested_refs: list[str],
    user_explicit_refs: list[str],
    policy_refs: list[str],
    available_refs: list[str],
    reference_only_refs: list[str] | None = None,
    testware_details: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Select TC-less auxiliary testware and record each completion obligation.

    `requested_refs`は今回Runで実行する補助testware。利用者の明示指示または有効な
    policyがある場合だけ`completion_required=true`にする。`reference_only_refs`は
    参照候補として記録するだけで`false`。根拠が不明な値は推測せずunresolvedにする。
    """
    all_inputs = [
        *_list_of(requested_refs),
        *_list_of(user_explicit_refs),
        *_list_of(policy_refs),
        *_list_of(available_refs),
        *_list_of(reference_only_refs),
    ]
    invalid_refs = [str(ref) for ref in all_inputs if not _text(ref)]
    if invalid_refs:
        return {
            "status": "unresolved",
            "selected_refs": [],
            "invalid_refs": invalid_refs,
        }
    user_explicit = set(user_explicit_refs)
    authorized = user_explicit | set(policy_refs)
    available = set(available_refs)
    requested = set(requested_refs)
    reference_only = set(reference_only_refs or [])
    unauthorized = sorted(requested - authorized)
    missing = sorted((requested | reference_only) - available)
    conflicting = sorted(requested & reference_only)
    missing_details: list[str] = []
    if testware_details is not None:
        for ref in sorted(requested | reference_only):
            detail = testware_details.get(ref)
            if (
                not isinstance(detail, dict)
                or not _in(detail.get("executor_owner"), AUXILIARY_OWNERS)
                or not _text(detail.get("implementation_revision"))
            ):
                missing_details.append(ref)
    if unauthorized or missing or conflicting or missing_details:
        return {
            "status": "unresolved",
            "selected_refs": [],
            "unauthorized_refs": unauthorized,
            "missing_refs": missing,
            "conflicting_refs": conflicting,
            "missing_detail_refs": missing_details,
        }
    details = testware_details or {}
    routes: list[dict[str, Any]] = []
    for ref in sorted(requested | reference_only):
        detail = details.get(ref, {})
        is_required = ref in requested
        route: dict[str, Any] = {
            "testware_ref": ref,
            "selection_basis": (
                ("user_explicit" if ref in user_explicit else "policy")
                if is_required
                else "reference_only"
            ),
            "completion_required": is_required,
        }
        if testware_details is not None:
            route["executor_owner"] = detail.get("executor_owner")
            route["implementation_revision"] = detail.get("implementation_revision")
        routes.append(route)
    # `testware_details`が無い呼び出しは選定結果だけを返す。ownerとrevisionが
    # 無いrouteは`validate_auxiliary_routes()`に拒否されるため、実行可能とは言わない。
    return {
        "status": "ready",
        "execution_ready": testware_details is not None,
        "selected_refs": sorted(requested),
        "auxiliary_routes": routes,
        "tc_member_count": 0,
        "tc_coverage_refs": [],
    }


def _in(value: Any, allowed: set[str]) -> bool:
    """型不正の値（list・dict等）を集合照会へ渡さず不一致として扱う。"""
    return isinstance(value, str) and value in allowed


def _source_of(sources: Any, ref: Any) -> dict[str, Any]:
    """不正なexecution_ref・sourceでも例外にせず、空sourceとして扱う。"""
    value = sources.get(ref) if isinstance(sources, dict) and _text(ref) else None
    return value if isinstance(value, dict) else {}


def _list_of(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def validate_required_routes(routes: list[dict[str, Any]]) -> dict[str, Any]:
    if not isinstance(routes, list):
        return {"routes": [], "valid": False, "issues": ["required_routes_not_list"]}
    issues: list[str] = []
    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, route in enumerate(routes):
        if not isinstance(route, dict):
            issues.append(f"invalid_required_route:{index}")
            continue
        tc_ref = route.get("tc_ref")
        kind = route.get("route_type")
        route_ref = route.get("route_ref")
        if not _in(kind, REQUIRED_ROUTE_TYPES):
            issues.append(f"invalid_required_route_type:{tc_ref}")
        if not _text(tc_ref) or not _text(route_ref):
            issues.append("missing_tc_or_route_ref")
        if kind == "e2e" and not _text(route.get("e2e_testware_ref")):
            issues.append(f"missing_e2e_testware_ref:{tc_ref}")
        if kind == "testware":
            if not _text(route.get("testware_ref")):
                issues.append(f"missing_testware_ref:{tc_ref}")
            if route.get("executor_owner") != TESTWARE_ROUTE_OWNER:
                issues.append(f"invalid_testware_executor_owner:{tc_ref}")
            if not _text(route.get("implementation_revision")):
                issues.append(f"missing_implementation_revision:{tc_ref}")
            if not _text(route.get("selection_basis")):
                issues.append(f"missing_selection_basis:{tc_ref}")
        execution_ref = route.get("execution_ref")
        if execution_ref is not None and not _text(execution_ref):
            issues.append(f"invalid_execution_ref:{route_ref}")
        key = f"{tc_ref}|{route_ref}"
        if key in seen:
            issues.append(f"duplicate_required_route:{key}")
        seen.add(key)
        item = {
            "tc_ref": tc_ref,
            "route_type": kind,
            "route_ref": route_ref,
            "e2e_testware_ref": route.get("e2e_testware_ref"),
        }
        if kind == "testware":
            for field in (
                "testware_ref",
                "executor_owner",
                "implementation_revision",
                "selection_basis",
            ):
                item[field] = route.get(field)
        if _text(execution_ref):
            # Activity投影がsourceを引けるよう、実行済みrouteのexecution_refを保持する。
            item["execution_ref"] = execution_ref
        normalized.append(item)
    return {"routes": normalized, "valid": not issues, "issues": issues}


def validate_auxiliary_routes(
    routes: list[dict[str, Any]],
    *,
    tc_testware_refs: list[str] | None = None,
    contract_v2: bool = False,
) -> dict[str, Any]:
    """Validate Run `auxiliary_routes`; legacy entries are reported as unknown.

    `contract_v2=True`は`route_contract_version: "2"`のRunを検証する入口の指定で、
    `completion_required`の欠落・`None`を義務不明ではなく契約違反として報告する。
    既定（旧形式・selection-only）は従来どおり義務不明（`obligation_unknown_refs`）にする。
    """
    if not isinstance(routes, list):
        return {
            "valid": False,
            "issues": ["auxiliary_routes_not_list"],
            "obligation_unknown_refs": [],
        }
    issues: list[str] = []
    unknown: list[str] = []
    seen: set[str] = set()
    tc_refs = {ref for ref in _list_of(tc_testware_refs) if _text(ref)}
    for index, entry in enumerate(routes):
        if not isinstance(entry, dict):
            issues.append(f"invalid_auxiliary_route:{index}")
            continue
        ref = entry.get("testware_ref")
        if not _text(ref):
            issues.append(f"missing_auxiliary_testware_ref:{index}")
            continue
        if ref in seen:
            issues.append(f"duplicate_auxiliary_route:{ref}")
        seen.add(ref)
        if entry.get("tc_ref"):
            issues.append(f"auxiliary_route_has_tc_ref:{ref}")
        if ref in tc_refs:
            issues.append(f"auxiliary_ref_also_tc_route:{ref}")
        execution_ref = entry.get("execution_ref")
        if execution_ref is not None and not _text(execution_ref):
            issues.append(f"invalid_execution_ref:{ref}")
        required = entry.get("completion_required")
        if required is None:
            if contract_v2:
                issues.append(f"missing_completion_required:{ref}")
            else:
                unknown.append(ref)
            continue
        if type(required) is not bool:
            issues.append(f"invalid_completion_required:{ref}")
            continue
        if not _in(entry.get("executor_owner"), AUXILIARY_OWNERS):
            issues.append(f"invalid_auxiliary_executor_owner:{ref}")
        if not _text(entry.get("implementation_revision")):
            issues.append(f"missing_auxiliary_implementation_revision:{ref}")
        basis = entry.get("selection_basis")
        if not _in(basis, AUXILIARY_BASES) or required is not (
            basis in AUXILIARY_REQUIRED_BASES
        ):
            issues.append(f"invalid_auxiliary_selection_basis:{ref}")
    return {
        "valid": not issues,
        "issues": issues,
        "obligation_unknown_refs": sorted(unknown),
    }


def _auxiliary_declaration_issues(run: dict[str, Any]) -> list[str]:
    """Runが宣言した補助routeと参照一覧の構造不正を返す（宣言が無ければ空）。

    不正な要素を除外して再解決を続けると、宣言された補助が新revisionから黙って
    消えるため、`resolve_auxiliary_obligations()`はこの結果が空でない限り進めない。
    フィールド未指定（旧Runの省略）と、不正な値を明示した状態は区別する。
    """
    issues: list[str] = []
    if "auxiliary_routes" in run:
        entries = run["auxiliary_routes"]
        if not isinstance(entries, list):
            issues.append("auxiliary_routes_not_list")
        else:
            seen: set[str] = set()
            for index, entry in enumerate(entries):
                if not isinstance(entry, dict):
                    issues.append(f"invalid_auxiliary_route:{index}")
                    continue
                ref = entry.get("testware_ref")
                if not _text(ref):
                    issues.append(f"missing_auxiliary_testware_ref:{index}")
                elif ref in seen:
                    issues.append(f"duplicate_auxiliary_route:{ref}")
                else:
                    seen.add(ref)
    if "auxiliary_testware_refs" in run:
        refs = run["auxiliary_testware_refs"]
        if not isinstance(refs, list):
            issues.append("auxiliary_testware_refs_not_list")
        else:
            listed: set[str] = set()
            for index, ref in enumerate(refs):
                if not _text(ref):
                    issues.append(f"invalid_auxiliary_testware_ref:{index}")
                elif ref in listed:
                    issues.append(f"duplicate_auxiliary_testware_ref:{ref}")
                else:
                    listed.add(ref)
    return issues


def resolve_auxiliary_obligations(
    run: dict[str, Any],
    *,
    user_explicit_refs: list[str],
    policy_refs: list[str],
    reference_only_refs: list[str] | None = None,
    testware_details: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Resolve legacy Run auxiliary obligations into a new Run revision.

    入力のRunは変更しない。現在の利用者指示・policyで根拠を解決できない補助は
    `blocked`のまま残し、完了済みActivityを書き換えず新revisionで復旧する。
    補助routeや参照一覧が不正な型・要素を含むRunは、正常な要素だけを拾って続けず
    `blocked`（`reason: "auxiliary_declaration_invalid"`、`invalid_inputs`に理由）にする。
    `route_contract_version`が存在して`"2"`以外のRunも未対応versionとして`blocked`
    （`reason: "unsupported_route_contract_version"`）にし、新しいv2 Runを作らない。
    """
    if not isinstance(run, dict):
        return {
            "status": "blocked",
            "reason": "auxiliary_declaration_invalid",
            "invalid_inputs": ["run_not_object"],
            "unresolved_refs": [],
            "missing_detail_refs": [],
            "run": None,
            "new_revision_required": True,
        }
    # 旧形式として扱えるのは`route_contract_version`が無いRunだけ。存在して`"2"`以外なら
    # 未対応versionであり、旧Runとして再解決して新しいv2 Runへ置換しない。
    if (
        "route_contract_version" in run
        and run["route_contract_version"] != ROUTE_CONTRACT_VERSION
    ):
        return {
            "status": "blocked",
            "reason": "unsupported_route_contract_version",
            "invalid_inputs": ["unsupported_route_contract_version"],
            "unresolved_refs": [],
            "missing_detail_refs": [],
            "run": None,
            "new_revision_required": True,
        }
    invalid_inputs = _auxiliary_declaration_issues(run)
    if invalid_inputs:
        return {
            "status": "blocked",
            "reason": "auxiliary_declaration_invalid",
            "invalid_inputs": invalid_inputs,
            "unresolved_refs": [],
            "missing_detail_refs": [],
            "run": None,
            "new_revision_required": True,
        }
    user_explicit = {ref for ref in _list_of(user_explicit_refs) if _text(ref)}
    policy = {ref for ref in _list_of(policy_refs) if _text(ref)}
    reference_only = {ref for ref in _list_of(reference_only_refs) if _text(ref)}
    details = testware_details if isinstance(testware_details, dict) else {}
    # 構造は上で検証済みなので、ここでは宣言された全entryをそのまま使う。
    entries = [dict(entry) for entry in run.get("auxiliary_routes", [])]
    known = {e.get("testware_ref") for e in entries}
    for ref in run.get("auxiliary_testware_refs", []):
        if ref not in known:
            entries.append({"testware_ref": ref})
    resolved: list[dict[str, Any]] = []
    unresolved: list[str] = []
    missing_details: list[str] = []
    is_v2 = run.get("route_contract_version") == ROUTE_CONTRACT_VERSION
    for entry in entries:
        ref = entry.get("testware_ref")
        if not _text(ref):
            unresolved.append(str(ref))
            continue
        # version無しの旧Runが持つ`completion_required`は根拠を確認できないため引き継がない。
        if is_v2 and type(entry.get("completion_required")) is bool:
            resolved.append(entry)
            continue
        if ref in user_explicit:
            basis, required = "user_explicit", True
        elif ref in policy:
            basis, required = "policy", True
        elif ref in reference_only:
            basis, required = "reference_only", False
        else:
            unresolved.append(str(ref))
            continue
        detail = details.get(ref)
        detail = detail if isinstance(detail, dict) else {}
        owner = entry.get("executor_owner") or detail.get("executor_owner")
        revision = entry.get("implementation_revision") or detail.get(
            "implementation_revision"
        )
        if not _in(owner, AUXILIARY_OWNERS) or not _text(revision):
            missing_details.append(str(ref))
            continue
        resolved.append(
            {
                **entry,
                "executor_owner": owner,
                "implementation_revision": revision,
                "selection_basis": basis,
                "completion_required": required,
            }
        )
    if unresolved or missing_details:
        return {
            "status": "blocked",
            "reason": "auxiliary_obligation_unresolved",
            "unresolved_refs": sorted(unresolved),
            "missing_detail_refs": sorted(missing_details),
            "run": None,
            "new_revision_required": True,
        }
    resolved.sort(key=lambda item: str(item.get("testware_ref")))
    return {
        "status": "ready",
        "unresolved_refs": [],
        "missing_detail_refs": [],
        "run": {
            **copy.deepcopy(run),
            "route_contract_version": ROUTE_CONTRACT_VERSION,
            "auxiliary_routes": resolved,
            "auxiliary_testware_refs": [item["testware_ref"] for item in resolved],
            "auxiliary_testware_count": len(resolved),
        },
        "new_revision_required": True,
    }


def _revision_confirmed(
    declared: Any, source: dict[str, Any], *, required: bool = False
) -> bool:
    """旧build・別revisionの結果を今回の実行として数えない。

    `required`のroute（testware route・実施義務のある補助）は、宣言revisionが
    欠落していれば照合できないため確認済みにしない。旧manual／e2e routeは従来どおり。
    """
    if not _text(declared):
        return not required
    return source.get("implementation_revision") == declared


def _revision_issue(ref: Any, declared: Any) -> str:
    kind = "missing" if not _text(declared) else "mismatch"
    return f"implementation_revision_{kind}:{ref}"


def _run_contract_issues(run: Any) -> list[str]:
    """Runそのものの妥当性を、既存のroute検証を再利用して確認する。

    不正なroute種別・必須識別子の欠落・不正なowner／revision／選定根拠・補助refの
    型不正を含むRunは、Activity投影の入力として正当な実施義務とは扱わない。
    `route_contract_version`が無い旧Runは読取互換のため版の検査だけを免除する。
    """
    if not isinstance(run, dict):
        return ["run_not_object"]
    issues: list[str] = []
    if (
        "route_contract_version" in run
        and run.get("route_contract_version") != ROUTE_CONTRACT_VERSION
    ):
        issues.append("unsupported_route_contract_version")
    routes = run.get("required_routes", [])
    issues += validate_required_routes(routes)["issues"]
    tc_testware = [
        route.get("testware_ref")
        for route in _list_of(routes)
        if isinstance(route, dict) and route.get("route_type") == "testware"
    ]
    entries = run.get("auxiliary_routes", [])
    issues += validate_auxiliary_routes(
        entries,
        tc_testware_refs=tc_testware,
        contract_v2=run.get("route_contract_version") == ROUTE_CONTRACT_VERSION,
    )["issues"]
    refs = run.get("auxiliary_testware_refs", [])
    if not isinstance(refs, list):
        issues.append("auxiliary_testware_refs_not_list")
    else:
        issues += [
            f"invalid_auxiliary_testware_ref:{index}"
            for index, ref in enumerate(refs)
            if not _text(ref)
        ]
        # v2 Runの件数は型を厳密に確認し、補助routeの件数（refs宣言時はその件数）と一致させる。
        count = run.get("auxiliary_testware_count")
        if run.get("route_contract_version") == ROUTE_CONTRACT_VERSION and isinstance(
            entries, list
        ):
            actual = [len(entries)]
            if isinstance(refs, list) and "auxiliary_testware_refs" in run:
                actual.append(len(refs))
            if type(count) is not int or count < 0:
                issues.append("invalid_auxiliary_testware_count")
            elif any(count != value for value in actual):
                issues.append("auxiliary_testware_count_mismatch")
        # refsを宣言したv2 Runは、補助routeの集合と一致しなければならない（宣言が無い場合は検査しない）。
        if (
            run.get("route_contract_version") == ROUTE_CONTRACT_VERSION
            and "auxiliary_testware_refs" in run
            and isinstance(entries, list)
        ):
            listed = {
                e.get("testware_ref")
                for e in entries
                if isinstance(e, dict) and _text(e.get("testware_ref"))
            }
            text_refs = [ref for ref in refs if _text(ref)]
            if (
                len(text_refs) != len(refs)
                or len(set(text_refs)) != len(text_refs)
                or set(text_refs) != listed
            ):
                issues.append("auxiliary_refs_routes_mismatch")
    return issues


def _route_done(item: dict[str, Any]) -> bool:
    """TC routeのowner結果が確定・投影済みか。testware routeはattempt・raw取得も要する。"""
    done = item["result_finalized"] and item["source_result_projectable"]
    if item["route_type"] == "testware":
        done = done and item["raw_capture_complete"] and _text(item["attempt_ref"])
    return bool(done)


def project_activity(
    run: dict[str, Any],
    source_executions: dict[str, dict[str, Any]],
    *,
    cleanup_status: str = "対象なし",
    unresolved: list[Any] | None = None,
) -> dict[str, Any]:
    # Run自体が不正な場合（未知のroute種別等）は、Activityを完了へ進めない。
    derived_unresolved: list[str] = list(_run_contract_issues(run))
    if not isinstance(run, dict):
        run = {}
    sources: Any = source_executions
    if not isinstance(sources, dict):
        derived_unresolved.append("source_executions_not_object")
        sources = {}
    raw_routes = run.get("required_routes", [])
    if not isinstance(raw_routes, list):
        derived_unresolved.append("required_routes_not_list")
        raw_routes = []
    routes: list[dict[str, Any]] = []
    for index, route in enumerate(raw_routes):
        if isinstance(route, dict):
            routes.append(route)
        else:
            derived_unresolved.append(f"invalid_required_route:{index}")
    projected: list[dict[str, Any]] = []
    by_tc: dict[str, list[dict[str, Any]]] = {}
    seen_routes: set[str] = set()
    for route in routes:
        route_ref = route.get("route_ref")
        execution_ref = route.get("execution_ref")
        if execution_ref is not None and not _text(execution_ref):
            derived_unresolved.append(f"invalid_execution_ref:{route_ref}")
            execution_ref = None
        route_key = f"{route.get('tc_ref')}|{route_ref}"
        if route_key in seen_routes:
            derived_unresolved.append(f"duplicate_required_route:{route_key}")
        seen_routes.add(route_key)
        source = _source_of(sources, execution_ref)
        is_testware = route.get("route_type") == "testware"
        start_state = source.get("start_state", "未開始")
        started = (
            start_state == "開始済み" and source.get("actual_start_confirmed") is True
        )
        revision_ok = _revision_confirmed(
            route.get("implementation_revision"), source, required=is_testware
        )
        actual_start = started and revision_ok
        if started and not revision_ok:
            derived_unresolved.append(
                _revision_issue(route_ref, route.get("implementation_revision"))
            )
        source_result = source.get("source_result")
        result_finalized = source.get("result_finalized") is True
        source_result_projectable = isinstance(source_result, str) and bool(
            source_result.strip()
        )
        item = {
            "tc_ref": route.get("tc_ref"),
            "route_ref": route_ref,
            "route_type": route.get("route_type"),
            "execution_ref": execution_ref,
            "implementation_revision": route.get("implementation_revision"),
            "source_start_state": start_state,
            "source_result": source_result,
            "result_finalized": result_finalized,
            "source_result_projectable": source_result_projectable,
            # testware routeのcleanupは明示された値だけを確認済みとし、欠落は未確認にする。
            "cleanup_status": source.get(
                "cleanup_status", "未確認" if is_testware else "対象なし"
            ),
            "evidence_refs": list(_list_of(source.get("evidence_refs"))),
            "executed": actual_start,
            "blocked": not actual_start
            and (source.get("blocked") is True or (started and not revision_ok)),
        }
        if route.get("route_type") == "e2e":
            # 実行対象のE2E testware参照もRun照合できるよう投影する。
            item["e2e_testware_ref"] = route.get("e2e_testware_ref")
        if is_testware:
            # Runの選定情報（testware・owner・選定根拠）もRun照合できるよう投影する。
            for field in ("testware_ref", "executor_owner", "selection_basis"):
                item[field] = route.get(field)
            item["attempt_ref"] = source.get("attempt_ref")
            item["raw_capture_complete"] = source.get("raw_capture_complete") is True
        projected.append(item)
        by_tc.setdefault(str(route.get("tc_ref")), []).append(item)

    tc_execution_refs = {i["execution_ref"] for i in projected if i["execution_ref"]}
    raw_auxiliary = run.get("auxiliary_routes", [])
    if not isinstance(raw_auxiliary, list):
        derived_unresolved.append("auxiliary_routes_not_list")
        raw_auxiliary = []
    auxiliary_entries: list[dict[str, Any]] = []
    for index, entry in enumerate(raw_auxiliary):
        if isinstance(entry, dict):
            auxiliary_entries.append(entry)
        else:
            derived_unresolved.append(f"invalid_auxiliary_route:{index}")
    covered = {
        e.get("testware_ref") for e in auxiliary_entries if _text(e.get("testware_ref"))
    }
    # 旧Runのrefだけの補助は義務不明のまま別枠に残し、完了へ数えない。
    raw_refs = run.get("auxiliary_testware_refs", [])
    if not isinstance(raw_refs, list):
        derived_unresolved.append("auxiliary_testware_refs_not_list")
        raw_refs = []
    for index, ref in enumerate(raw_refs):
        if not _text(ref):
            derived_unresolved.append(f"invalid_auxiliary_testware_ref:{index}")
        elif ref not in covered:
            auxiliary_entries.append({"testware_ref": ref})
            covered.add(ref)
    auxiliary_projected: list[dict[str, Any]] = []
    seen_auxiliary: set[str] = set()
    run_is_v2 = run.get("route_contract_version") == ROUTE_CONTRACT_VERSION
    for index, route in enumerate(auxiliary_entries):
        testware_ref = route.get("testware_ref")
        if not _text(testware_ref):
            derived_unresolved.append(f"invalid_auxiliary_testware_ref:{index}")
        elif testware_ref in seen_auxiliary:
            derived_unresolved.append(f"duplicate_auxiliary_route:{testware_ref}")
        else:
            seen_auxiliary.add(testware_ref)
        execution_ref = route.get("execution_ref")
        if execution_ref is not None and not _text(execution_ref):
            derived_unresolved.append(f"invalid_execution_ref:{testware_ref}")
            execution_ref = None
        source = _source_of(sources, execution_ref)
        started = (
            source.get("start_state") == "開始済み"
            and source.get("actual_start_confirmed") is True
        )
        required = route.get("completion_required")
        # version無しの旧Runの値は根拠不明として扱い、義務を確定しない。
        if not run_is_v2 or type(required) is not bool:
            required = None
        revision_ok = _revision_confirmed(
            route.get("implementation_revision"), source, required=required is True
        )
        shared = bool(execution_ref) and execution_ref in tc_execution_refs
        if shared:
            derived_unresolved.append(
                f"execution_ref_shared_with_tc_route:{execution_ref}"
            )
        if started and not revision_ok:
            derived_unresolved.append(
                _revision_issue(testware_ref, route.get("implementation_revision"))
            )
        actual_start = started and revision_ok and not shared
        source_result = source.get("source_result")
        auxiliary_projected.append(
            {
                "testware_ref": testware_ref,
                "executor_owner": route.get("executor_owner"),
                "implementation_revision": route.get("implementation_revision"),
                "selection_basis": route.get("selection_basis"),
                "completion_required": required,
                "execution_ref": execution_ref,
                "attempt_ref": source.get("attempt_ref"),
                "source_start_state": source.get("start_state", "未開始"),
                "source_result": source_result,
                "result_finalized": source.get("result_finalized") is True,
                "source_result_projectable": isinstance(source_result, str)
                and bool(source_result.strip()),
                "raw_capture_complete": source.get("raw_capture_complete") is True,
                # 補助のcleanupは明示された値だけを確認済みとし、欠落は未確認にする。
                "cleanup_status": source.get("cleanup_status", "未確認"),
                "evidence_refs": list(_list_of(source.get("evidence_refs"))),
                "executed": actual_start,
                "blocked": not actual_start
                and (
                    source.get("blocked") is True
                    or shared
                    or (started and not revision_ok)
                ),
            }
        )
        if required is None:
            derived_unresolved.append(f"auxiliary_obligation_unknown:{testware_ref}")

    required_aux = [i for i in auxiliary_projected if i["completion_required"] is True]
    tc_states = {}
    for tc_ref, items in by_tc.items():
        started = all(item["executed"] for item in items)
        blocked = any(item["blocked"] for item in items)
        tc_states[tc_ref] = (
            "executed" if started else ("blocked" if blocked else "unexecuted")
        )
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

    def aux_completed(item: dict[str, Any]) -> bool:
        return bool(
            item["executed"]
            and item["result_finalized"]
            and item["source_result_projectable"]
            and item["raw_capture_complete"]
            and _text(item["attempt_ref"])
            and _in(item["cleanup_status"], CLEANUP_CLOSED)
        )

    unresolved_values = list(unresolved or [])
    for value in derived_unresolved:
        if value not in unresolved_values:
            unresolved_values.append(value)
    # 状態判定は論理TCではなくrouteの開始単位で数える（一部routeだけ開始済みも含む）。
    started_units = sum(i["executed"] for i in projected) + sum(
        i["executed"] for i in required_aux
    )
    started_cleanups = [
        item["cleanup_status"]
        for item in [*projected, *auxiliary_projected]
        if item["executed"]
    ]
    bad_cleanups = [
        value
        for value in [cleanup_status, *started_cleanups]
        if not _in(value, CLEANUP_CLOSED)
    ]
    if bad_cleanups and _in(cleanup_status, CLEANUP_CLOSED):
        cleanup_status = bad_cleanups[0]
    if bad_cleanups or unresolved_values:
        state = "部分完了（ブロック中あり）" if started_units else "ブロック中"
    elif (
        unexecuted_count
        or blocked_count
        or any(not i["executed"] for i in required_aux)
    ):
        if (
            not routes
            and not started_units
            and not any(i["blocked"] for i in required_aux)
        ):
            state = "未開始"
        else:
            state = "部分完了（ブロック中あり）" if started_units else "ブロック中"
    elif any(not _route_done(item) for item in projected) or any(
        not aux_completed(i) for i in required_aux
    ):
        state = "実行中"
    elif routes or required_aux:
        state = "完了"
    else:
        state = "未開始"
    return {
        "route_contract_version": ROUTE_CONTRACT_VERSION,
        "activity_state": state,
        "route_results": projected,
        "auxiliary_route_results": auxiliary_projected,
        "tc_execution_state": tc_states,
        "counts": {
            "tc_member_count": len(by_tc),
            "executed_tc_count": started_count,
            "unexecuted_tc_count": unexecuted_count,
            "blocked_tc_count": blocked_count,
            "source_result_counts": result_counts,
            "auxiliary_testware_count": len(auxiliary_projected),
            "auxiliary_executed_count": sum(
                1 for item in auxiliary_projected if item["executed"]
            ),
            "auxiliary_source_result_counts": auxiliary_result_counts,
            "auxiliary_required_count": len(required_aux),
            "auxiliary_required_completed_count": sum(
                1 for item in required_aux if aux_completed(item)
            ),
            "auxiliary_obligation_unknown_count": sum(
                1 for item in auxiliary_projected if item["completion_required"] is None
            ),
        },
        "cleanup_status": cleanup_status,
        "unresolved": unresolved_values,
    }


def verify_activity_against_run(
    run: dict[str, Any], activity: dict[str, Any]
) -> dict[str, Any]:
    """保存済みRunを正本として、Activityのroute集合・実施義務・状態・件数を再計算し照合する。

    Activity自身の申告（`route_results`・`completion_required`・件数）は、Runから
    導出した値と一致しない限り検証済みにしない。RunとActivityのどちらかが
    objectでない場合も例外にせず不一致として返す。
    """
    if not isinstance(run, dict) or not isinstance(activity, dict):
        return {"valid": False, "mismatches": ["run_or_activity_not_object"]}
    # 保存済みActivityとして検証する入口なので、種別が`activity`以外の成果物は受け入れない。
    # （`project_activity()`の戻り値は投影helperであり、`artifact_type`を持たせない。）
    if activity.get("artifact_type") != "activity":
        return {"valid": False, "mismatches": ["activity_artifact_required"]}
    # 不正なRunを再投影して一致しただけでは、検証済みの実施義務として扱わない。
    run_issues = _run_contract_issues(run)
    # 保存済みRunの代わりに、Activity・Baseline等のRun以外のartifactを受け入れない。
    # `project_activity()`の簡略入力は対象外（この検証入口だけの条件）。
    if run.get("artifact_type") != "run":
        run_issues.append("run_artifact_required")
    if run.get("route_contract_version") != ROUTE_CONTRACT_VERSION:
        run_issues.append("run_not_contract_v2")
    if run_issues:
        return {
            "valid": False,
            "mismatches": ["run_contract_invalid"],
            "run_issues": run_issues,
        }
    reported_unresolved = _list_of(activity.get("unresolved"))
    recomputed = project_activity(
        run,
        activity.get("source_executions", {}),
        cleanup_status=activity.get("cleanup_status", "対象なし"),
        unresolved=reported_unresolved,
    )
    mismatches = [
        field
        for field in (
            "route_contract_version",
            "activity_state",
            "route_results",
            "auxiliary_route_results",
            "tc_execution_state",
            "counts",
            "cleanup_status",
            "unresolved",
        )
        if recomputed.get(field) != activity.get(field)
    ]
    return {"valid": not mismatches, "mismatches": mismatches}


def update_activity(
    existing: dict[str, Any], incoming: dict[str, Any]
) -> dict[str, Any]:
    if existing.get("activity_state") == "完了":
        return {
            "status": "blocked",
            "reason": "completed_activity_is_immutable",
            "resolution": "create_new_activity_or_run_revision",
        }
    if existing.get("scope_identity") != incoming.get("scope_identity") or existing.get(
        "snapshot_ref"
    ) != incoming.get("snapshot_ref"):
        return {
            "status": "new_activity_required",
            "reason": "scope_or_snapshot_changed",
        }
    return {"status": "update_allowed", "activity": incoming}


def scan_activity_files(
    root: str | Path, *, listing_complete: bool = True
) -> dict[str, Any]:
    """Fixed-root direct scan; callers must report listing truncation or failures."""
    try:
        files = sorted(
            (
                p
                for p in Path(root).rglob("*.json")
                if p.is_file() and not p.is_symlink()
            ),
            key=lambda p: p.as_posix(),
        )
    except OSError as exc:
        return {
            "activity_refs": [],
            "complete": False,
            "unresolved": [f"scan_failed:{type(exc).__name__}"],
        }
    return {
        "activity_refs": [p.stem for p in files],
        "complete": bool(listing_complete),
        "unresolved": [] if listing_complete else ["listing_incomplete_or_truncated"],
    }
