"""Stable test-item candidate identity, history, revision and impact contract."""

from __future__ import annotations

import copy
import re
import sys
from typing import Any

from candidate_support import (
    ITEM_ID,
    ITEM_KINDS,
    ITEM_STATUSES,
    ContractError,
    active_source_refs,
    canonical_bytes,
    feature_inventory,
    fingerprint,
    make_result,
    operation_claim_details,
    source_key,
    source_ref,
    source_refs,
    strict_loads,
    string_list,
    text,
)
from candidate_support import (
    validate_item_artifact as _validate_item_artifact,
)

SCHEMA = "test-item-candidates-v1"
OWNER = "test-item-analysis"
DRAFT_REF = re.compile(r"^@draft:([a-zA-Z0-9][a-zA-Z0-9._-]{0,63})$")
IDENTITY_ACTIONS = {"new", "reuse", "split", "merge"}


def _issue(code: str, message: str, *, blocking: bool = True) -> dict[str, Any]:
    return {"code": code, "message": message, "blocking": blocking}


def _sort_sources(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    return sorted(rows, key=source_key)


def _source_union(*groups: list[dict[str, str]]) -> list[dict[str, str]]:
    by_key = {source_key(row): row for group in groups for row in group}
    return [by_key[key] for key in sorted(by_key)]


def _same_source(left: dict[str, str], right: dict[str, str]) -> bool:
    return source_key(left) == source_key(right)


def _core(artifact: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value for key, value in artifact.items() if key != "content_fingerprint"
    }


def _check_cycle(items: dict[str, dict[str, Any]]) -> None:
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(item_id: str) -> None:
        if item_id in visiting:
            raise ContractError("item_parent_cycle", f"parent cycle includes {item_id}")
        if item_id in visited:
            return
        visiting.add(item_id)
        for parent_id in items[item_id]["parent_item_ids"]:
            if parent_id not in items:
                raise ContractError(
                    "item_parent_missing",
                    f"{item_id} references missing parent {parent_id}",
                )
            visit(parent_id)
        visiting.remove(item_id)
        visited.add(item_id)

    for item_id in items:
        visit(item_id)


def validate_artifact(value: Any) -> dict[str, Any]:
    return _validate_item_artifact(value)


def feature_key(ref: dict[str, str]) -> tuple[str, str, str]:
    return (ref["owner"], ref["scope"], ref["artifact_ref"])


def _currentness(evidence: list[dict[str, str]], active: list[dict[str, str]]) -> str:
    by_identity = {feature_key(ref): ref for ref in active}
    unknown = False
    for ref in evidence:
        current = by_identity.get(feature_key(ref))
        if current is None:
            unknown = True
        elif not _same_source(current, ref):
            return "stale"
    return "unknown" if unknown else "current"


def _history_event(
    item_id: str,
    action: str,
    reason: str,
    related: list[str],
    evidence: list[dict[str, str]],
    history: list[dict[str, Any]],
) -> dict[str, Any]:
    event = {
        "item_id": item_id,
        "action": action,
        "reason": reason,
        "related_item_ids": sorted(set(related)),
        "evidence_refs": _sort_sources(evidence),
    }
    event["event_id"] = fingerprint(
        {
            "event": event,
            "sequence": len(history),
            "previous_event_id": history[-1]["event_id"] if history else None,
        }
    )
    if event["event_id"] in {row["event_id"] for row in history}:
        raise ContractError(
            "history_event_id_collision", "history event ID is already allocated"
        )
    return event


def _check_revision_gate(
    request: dict[str, Any], previous: dict[str, Any] | None
) -> tuple[str | None, dict[str, Any] | None]:
    expected = request.get("expected_revision")
    current = request.get("current_revision")
    if expected is not None:
        expected = text(expected, "expected_revision")
    if current is not None:
        current = text(current, "current_revision")
    if expected != current:
        return "cas_conflict", None
    if previous is None:
        if current is not None:
            return "current_artifact_missing", None
    else:
        validate_artifact(previous)
        if (
            current is None
            or previous["scope"] != request.get("scope")
            or previous["artifact_ref"] != request.get("artifact_ref")
        ):
            return "previous_artifact_identity_mismatch", None
    return None, previous


def materialize(request: dict[str, Any]) -> dict[str, Any]:
    required = {
        "operation",
        "scope",
        "artifact_ref",
        "feature_inventory",
        "source_refs",
        "expected_revision",
        "current_revision",
        "approval_ref",
        "required_permission",
        "previous_artifact",
        "candidates",
        "retirements",
    }
    if set(request) != required or request.get("operation") != "materialize":
        raise ContractError(
            "request_schema", "materialize request fields do not match v1"
        )
    scope = text(request["scope"], "scope")
    artifact_ref = text(request["artifact_ref"], "artifact_ref")
    required_permission = text(request["required_permission"], "required_permission")
    approval_ref = request["approval_ref"]
    if approval_ref is not None:
        approval_ref = text(approval_ref, "approval_ref")
    inventory = feature_inventory(request["feature_inventory"])
    if inventory["project_ref"] != scope:
        raise ContractError(
            "scope_mismatch", "feature inventory project_ref does not match scope"
        )
    current_sources = active_source_refs(request["source_refs"])
    feature_source = source_ref(inventory["feature_source_ref"])
    if source_key(feature_source) not in {source_key(ref) for ref in current_sources}:
        raise ContractError(
            "feature_source_missing",
            "source_refs must include the current feature inventory ref",
        )
    previous = request["previous_artifact"]
    if previous is not None and not isinstance(previous, dict):
        raise ContractError(
            "previous_artifact_invalid", "previous_artifact must be an object or null"
        )
    conflict, previous = _check_revision_gate(request, previous)
    if conflict:
        return make_result(
            "blocked",
            valid=False,
            issues=[
                _issue(
                    conflict,
                    "storage revision precondition does not match current state",
                )
            ],
            candidate=None,
            write_precondition=None,
        )
    if not isinstance(request["candidates"], list) or not isinstance(
        request["retirements"], list
    ):
        raise ContractError(
            "candidate_list_invalid", "candidates and retirements must be arrays"
        )
    if previous is not None and previous["artifact_ref"] != artifact_ref:
        raise ContractError(
            "artifact_ref_mismatch", "artifact_ref cannot change across revisions"
        )

    old_items = {
        row["item_id"]: copy.deepcopy(row)
        for row in (previous["items"] if previous else [])
    }
    old_history = copy.deepcopy(previous["history"] if previous else [])
    old_ids = set(previous["id_history"] if previous else [])
    historical_sources = previous["source_refs"] if previous else []
    allocated = sorted(old_ids)
    max_id = max((int(value.split("-")[1]) for value in allocated), default=0)
    candidates = request["candidates"]
    if any(not isinstance(row, dict) for row in candidates):
        raise ContractError("candidate_invalid", "each candidate must be an object")
    candidate_fields = {
        "candidate_key",
        "identity_action",
        "item_id",
        "related_item_ids",
        "reason",
        "name",
        "description",
        "kind",
        "status",
        "parent_item_refs",
        "feature_refs",
        "evidence_refs",
    }
    if any(set(row) != candidate_fields for row in candidates):
        raise ContractError("candidate_schema", "candidate fields do not match v1")
    keys = [text(row.get("candidate_key"), "candidate_key") for row in candidates]
    if len(keys) != len(set(keys)):
        raise ContractError(
            "candidate_key_duplicate", "candidate_key values must be unique"
        )
    candidates = sorted(
        candidates, key=lambda row: text(row.get("candidate_key"), "candidate_key")
    )
    assigned: dict[str, str] = {}
    for row in candidates:
        action = row.get("identity_action")
        candidate_key = text(row.get("candidate_key"), "candidate_key")
        if not isinstance(action, str) or action not in IDENTITY_ACTIONS:
            raise ContractError(
                "identity_action_invalid",
                "identity_action must be new, reuse, split, or merge",
            )
        if action == "reuse":
            item_id = text(row.get("item_id"), "item_id")
            if (
                not ITEM_ID.fullmatch(item_id)
                or item_id not in old_items
                or old_items[item_id]["status"] == "retired"
            ):
                raise ContractError(
                    "item_reuse_invalid",
                    "reuse must reference an active current item ID",
                )
            if item_id in assigned.values():
                raise ContractError(
                    "item_reuse_duplicate",
                    "one item ID cannot be reused by multiple candidates",
                )
            assigned[candidate_key] = item_id
        else:
            if row.get("item_id") is not None:
                raise ContractError(
                    "manual_item_id_forbidden",
                    "new stable IDs are allocated from history, not supplied by the candidate",
                )
            max_id += 1
            assigned[candidate_key] = f"ITEM-{max_id:03d}"

    items = copy.deepcopy(old_items)
    events = list(old_history)
    changed_ids: set[str] = set()
    merge_sources: set[str] = set()
    source_map = {source_key(ref): ref for ref in current_sources}
    for row in candidates:
        candidate_key = text(row["candidate_key"], "candidate_key")
        action = row["identity_action"]
        item_id = assigned[candidate_key]
        related = string_list(row.get("related_item_ids", []), "related_item_ids")
        reason = text(row.get("reason"), "reason")
        if action == "reuse" and related:
            raise ContractError(
                "reuse_relations_invalid", "reuse cannot also split or merge IDs"
            )
        if action == "split" and (
            not related
            or any(
                ref not in old_items or old_items[ref]["status"] == "retired"
                for ref in related
            )
        ):
            raise ContractError(
                "split_source_invalid", "split requires active existing item IDs"
            )
        if action == "merge" and (
            len(related) < 2
            or any(
                ref not in old_items or old_items[ref]["status"] == "retired"
                for ref in related
            )
        ):
            raise ContractError(
                "merge_source_invalid",
                "merge requires at least two active existing item IDs",
            )
        if action == "merge":
            if merge_sources.intersection(related):
                raise ContractError(
                    "merge_source_duplicate",
                    "one existing item cannot feed multiple merges in the same update",
                )
            merge_sources.update(related)
        if action == "new" and related:
            raise ContractError(
                "new_relations_invalid",
                "new candidates cannot carry split or merge relations",
            )
        name = text(row.get("name"), "candidate.name")
        description = text(row.get("description"), "candidate.description")
        kind = row.get("kind")
        status = row.get("status")
        if (
            not isinstance(kind, str)
            or kind not in ITEM_KINDS
            or not isinstance(status, str)
            or status not in ITEM_STATUSES - {"retired"}
        ):
            raise ContractError(
                "candidate_classification_invalid",
                "candidate kind or status is invalid",
            )
        parent_refs = string_list(row.get("parent_item_refs", []), "parent_item_refs")
        feature_refs = string_list(row.get("feature_refs", []), "feature_refs")
        if any(ref not in inventory["features"] for ref in feature_refs):
            raise ContractError(
                "candidate_feature_unknown",
                "candidate references a feature outside the current inventory",
            )
        evidence_refs = source_refs(row.get("evidence_refs"), "candidate.evidence_refs")
        if any(source_key(ref) not in source_map for ref in evidence_refs):
            raise ContractError(
                "candidate_evidence_not_current",
                "candidate evidence must reference current input revisions",
            )
        parent_ids: list[str] = []
        for parent_ref in parent_refs:
            match = DRAFT_REF.fullmatch(parent_ref)
            parent_id = assigned.get(match.group(1)) if match else parent_ref
            if not parent_id or not ITEM_ID.fullmatch(parent_id):
                raise ContractError(
                    "candidate_parent_unknown",
                    f"parent reference cannot be resolved: {parent_ref}",
                )
            parent_ids.append(parent_id)
        currentness = _currentness(evidence_refs, current_sources)
        updated = {
            "item_id": item_id,
            "name": name,
            "description": description,
            "kind": kind,
            "status": status,
            "parent_item_ids": sorted(set(parent_ids)),
            "feature_refs": sorted(set(feature_refs)),
            "evidence_refs": evidence_refs,
            "currentness": currentness,
        }
        old = old_items.get(item_id)
        if action != "reuse":
            event_action = {"new": "created", "split": "split", "merge": "merged"}[
                action
            ]
            events.append(
                _history_event(
                    item_id, event_action, reason, related, evidence_refs, events
                )
            )
            changed_ids.add(item_id)
        elif old != updated:
            events.append(
                _history_event(item_id, "updated", reason, [], evidence_refs, events)
            )
            changed_ids.add(item_id)
        items[item_id] = updated

    for retirement in request["retirements"]:
        if not isinstance(retirement, dict) or set(retirement) != {
            "item_id",
            "reason",
            "evidence_refs",
        }:
            raise ContractError(
                "retirement_invalid", "retirement row fields do not match v1"
            )
        item_id = text(retirement["item_id"], "retirement.item_id")
        if (
            item_id not in items
            or items[item_id]["status"] == "retired"
            or item_id in assigned.values()
        ):
            raise ContractError(
                "retirement_target_invalid",
                "retirement must target an existing item not updated in this request",
            )
        evidence_refs = source_refs(
            retirement["evidence_refs"], "retirement.evidence_refs"
        )
        if any(source_key(ref) not in source_map for ref in evidence_refs):
            raise ContractError(
                "retirement_evidence_not_current",
                "retirement evidence must be current input",
            )
        reason = text(retirement["reason"], "retirement.reason")
        items[item_id]["status"] = "retired"
        items[item_id]["currentness"] = _currentness(
            items[item_id]["evidence_refs"], current_sources
        )
        events.append(
            _history_event(item_id, "retired", reason, [], evidence_refs, events)
        )
        changed_ids.add(item_id)

    unretired_merge_sources = sorted(
        item_id for item_id in merge_sources if items[item_id]["status"] != "retired"
    )
    if unretired_merge_sources:
        raise ContractError(
            "merge_sources_not_retired",
            "merge source items must be explicitly retired in the same update",
        )

    # A source change affects only candidates whose evidence points at the changed artifact.
    active_by_identity = {feature_key(ref): ref for ref in current_sources}
    previous_active_by_identity = (
        {feature_key(ref): ref for ref in previous["active_source_refs"]}
        if previous
        else {}
    )
    for item_id, item in items.items():
        if item_id in changed_ids:
            continue
        currentness = _currentness(item["evidence_refs"], current_sources)
        item["currentness"] = currentness
        if currentness == "stale":
            changed_source = next(
                (
                    active_by_identity.get(feature_key(ref))
                    for ref in item["evidence_refs"]
                    if feature_key(ref) in active_by_identity
                    and feature_key(ref) in previous_active_by_identity
                    and not _same_source(
                        previous_active_by_identity[feature_key(ref)],
                        active_by_identity[feature_key(ref)],
                    )
                    and not _same_source(active_by_identity[feature_key(ref)], ref)
                ),
                None,
            )
            if changed_source is not None:
                events.append(
                    _history_event(
                        item_id,
                        "source_changed",
                        "evidence source revision changed; revalidation is required",
                        [],
                        [changed_source],
                        events,
                    )
                )
                changed_ids.add(item_id)

    current_items = sorted(items.values(), key=lambda row: row["item_id"])
    _check_cycle({row["item_id"]: row for row in current_items})
    all_sources = _source_union(historical_sources, current_sources)
    feature_population = [
        {
            "feature_id": feature_id,
            "status": inventory["features"][feature_id]["status"],
        }
        for feature_id in sorted(inventory["features"])
    ]
    feature_population_ref = {
        **feature_source,
    }
    core = {
        "schema_version": SCHEMA,
        "owner": OWNER,
        "scope": scope,
        "artifact_ref": artifact_ref,
        "feature_inventory_ref": feature_population_ref,
        "feature_inventory_context": inventory["feature_inventory_context"],
        "feature_population": feature_population,
        "source_boundary_complete": inventory["source_boundary_complete"],
        "source_refs": all_sources,
        "active_source_refs": current_sources,
        "previous_artifact_revision": request["current_revision"],
        "items": current_items,
        "id_history": sorted(old_ids | set(items)),
        "history": events,
    }
    candidate = {**core, "content_fingerprint": fingerprint(core)}
    validate_artifact(candidate)
    if previous is not None:
        old_projection = {
            key: value
            for key, value in previous.items()
            if key not in {"content_fingerprint", "previous_artifact_revision"}
        }
        new_projection = {
            key: value
            for key, value in candidate.items()
            if key not in {"content_fingerprint", "previous_artifact_revision"}
        }
    else:
        old_projection = None
        new_projection = None
    if previous is not None and fingerprint(old_projection) == fingerprint(
        new_projection
    ):
        return make_result(
            "no_change",
            valid=True,
            issues=[],
            candidate=previous,
            write_precondition={
                "performed": False,
                "requires_native_cas": True,
                "requires_readback": True,
            },
            candidate_item_ids={key: value for key, value in sorted(assigned.items())},
        )
    stale = sorted(
        row["item_id"] for row in current_items if row["currentness"] == "stale"
    )
    unknown = sorted(
        row["item_id"] for row in current_items if row["currentness"] == "unknown"
    )
    status = (
        "candidate_ready_unpersisted"
        if not stale
        and not unknown
        and inventory["source_boundary_complete"]
        and inventory["analysis_complete"]
        else "incomplete"
    )
    issues = []
    if stale:
        issues.append(
            _issue(
                "source_stale",
                "source changes require revalidation of affected item candidates",
            )
        )
    if unknown:
        issues.append(
            _issue(
                "source_unknown",
                "some item candidates do not have a current source ref",
                blocking=False,
            )
        )
    if not inventory["source_boundary_complete"]:
        issues.append(
            _issue(
                "feature_population_incomplete",
                "feature population is partial or unknown",
                blocking=False,
            )
        )
    if not inventory["analysis_complete"]:
        issues.append(
            _issue(
                "upstream_analysis_incomplete",
                "feature analysis has unresolved findings",
                blocking=False,
            )
        )
    active_features = {
        row["feature_id"] for row in feature_population if row["status"] != "retired"
    }
    represented = {
        ref
        for row in current_items
        if row["status"] != "retired"
        for ref in row["feature_refs"]
    }
    gap_ids = sorted(active_features - represented)
    metric_status = "measured"
    metric_rate = None
    metric_denominator = None
    if not inventory["source_boundary_complete"] or not inventory["analysis_complete"]:
        metric_status = "not_measurable_incomplete_population"
    elif stale or unknown:
        metric_status = "not_measurable_stale_or_unknown_items"
    elif active_features:
        metric_rate = len(active_features & represented) / len(active_features)
        metric_denominator = len(active_features)
    else:
        metric_status = "not_measurable_zero_denominator"
    return make_result(
        status,
        valid=True,
        issues=issues,
        candidate=candidate,
        candidate_item_ids={key: value for key, value in sorted(assigned.items())},
        impacted_item_ids=sorted(changed_ids),
        unrepresented_feature_ids=gap_ids,
        item_candidate_coverage={
            "status": metric_status,
            "basis": "confirmed active feature inventory only",
            "numerator": len(active_features & represented),
            "denominator": metric_denominator,
            "rate": metric_rate,
        },
        write_precondition={
            "performed": False,
            "owner": OWNER,
            "scope": scope,
            "artifact_ref": artifact_ref,
            "operation_kind": "owner_artifact_create_or_update",
            "source_revisions": current_sources,
            "expected_revision": request["expected_revision"],
            "approval_ref": approval_ref,
            "required_permission": required_permission,
            "resume_owner": OWNER,
            "requires_provider_native_cas": True,
            "requires_independent_readback": True,
            "provider_selected": False,
            "approval_state": "not_resolved_by_candidate_helper",
            "operation_claim_details": operation_claim_details(
                owner=OWNER,
                scope=scope,
                artifact_ref=artifact_ref,
                source_refs_value=current_sources,
                expected_revision=request["expected_revision"],
                approval_ref=approval_ref,
                permission_scope=required_permission,
            ),
        },
    )


def validate(request: dict[str, Any]) -> dict[str, Any]:
    if (
        set(request) != {"operation", "artifact"}
        or request.get("operation") != "validate"
    ):
        raise ContractError("request_schema", "validate request fields do not match v1")
    artifact = validate_artifact(request["artifact"])
    return make_result(
        "valid_unpersisted_candidate_model",
        valid=True,
        issues=[],
        artifact_ref=artifact["artifact_ref"],
        scope=artifact["scope"],
        candidate_revision=artifact["content_fingerprint"],
        provider_readback="not_verified_by_this_validator",
    )


def impact(request: dict[str, Any]) -> dict[str, Any]:
    if (
        set(request) != {"operation", "artifact", "current_source_refs"}
        or request.get("operation") != "impact"
    ):
        raise ContractError("request_schema", "impact request fields do not match v1")
    artifact = validate_artifact(request["artifact"])
    active = active_source_refs(request["current_source_refs"])
    stale_ids: list[str] = []
    unknown_ids: list[str] = []
    for item in artifact["items"]:
        state = _currentness(item["evidence_refs"], active)
        if state == "stale":
            stale_ids.append(item["item_id"])
        elif state == "unknown":
            unknown_ids.append(item["item_id"])
    return make_result(
        "incomplete" if stale_ids or unknown_ids else "current",
        valid=True,
        issues=(
            [
                _issue(
                    "source_stale",
                    "only candidates linked to changed source refs need revalidation",
                )
            ]
            if stale_ids
            else []
        )
        + (
            [
                _issue(
                    "source_unknown",
                    "some candidate evidence sources were not supplied",
                    blocking=False,
                )
            ]
            if unknown_ids
            else []
        ),
        impacted_item_ids=stale_ids,
        source_unknown_item_ids=unknown_ids,
        unaffected_item_ids=sorted(
            row["item_id"]
            for row in artifact["items"]
            if row["item_id"] not in set(stale_ids + unknown_ids)
        ),
    )


def validate_readback(request: dict[str, Any]) -> dict[str, Any]:
    expected = {"operation", "candidate_artifact", "readback"}
    if set(request) != expected or request.get("operation") != "validate_readback":
        raise ContractError(
            "request_schema", "validate_readback request fields do not match v1"
        )
    artifact = validate_artifact(request["candidate_artifact"])
    readback = request["readback"]
    fields = {"owner", "scope", "artifact_ref", "revision", "content_hash"}
    if not isinstance(readback, dict) or set(readback) != fields:
        raise ContractError(
            "readback_schema", "provider readback fields do not match A contract"
        )
    normalized = {field: text(readback[field], f"readback.{field}") for field in fields}
    if (
        normalized["owner"] != OWNER
        or normalized["scope"] != artifact["scope"]
        or normalized["artifact_ref"] != artifact["artifact_ref"]
    ):
        raise ContractError(
            "readback_identity_mismatch",
            "provider readback owner, scope, or artifact ref does not match",
        )
    if not re.fullmatch(r"[0-9a-f]{64}", normalized["content_hash"]):
        raise ContractError(
            "readback_hash_invalid", "provider content_hash must be SHA-256 hex"
        )
    matches = normalized["content_hash"] == artifact["content_fingerprint"]
    return make_result(
        "readback_matches" if matches else "blocked",
        valid=matches,
        issues=[]
        if matches
        else [
            _issue(
                "readback_hash_mismatch",
                "saved content does not match candidate fingerprint",
            )
        ],
        readback={**normalized, "revision_is_provider_owned": True},
        provider_authenticity="not_established_by_this_validator",
        provider_cas="not_established_by_this_validator",
    )


def run(request: Any) -> dict[str, Any]:
    if not isinstance(request, dict):
        raise ContractError("request_invalid", "request must be a JSON object")
    operation = request.get("operation")
    if operation == "materialize":
        return materialize(request)
    if operation == "validate":
        return validate(request)
    if operation == "impact":
        return impact(request)
    if operation == "validate_readback":
        return validate_readback(request)
    raise ContractError(
        "operation_invalid", "operation must be materialize, validate, or impact"
    )


def main() -> int:
    try:
        request = strict_loads(sys.stdin.buffer.read(16 * 1024 * 1024 + 1))
        result = run(request)
    except ContractError as exc:
        result = make_result(
            "blocked", valid=False, issues=[_issue(exc.code, exc.message)]
        )
    except Exception:
        result = make_result(
            "blocked",
            valid=False,
            issues=[_issue("internal_error", "candidate validation failed closed")],
        )
    sys.stdout.buffer.write(canonical_bytes(result) + b"\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
