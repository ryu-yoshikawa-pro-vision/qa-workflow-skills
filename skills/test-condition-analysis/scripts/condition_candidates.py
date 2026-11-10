"""Manage stable common test-condition candidates and non-formal item crosschecks."""

from __future__ import annotations

import copy
import re
import sys
from typing import Any

from candidate_support import (
    EVENT_ID,
    STORAGE_CONTENT_ENCODING,
    ContractError,
    active_source_refs,
    canonical_bytes,
    derive_currentness,
    feature_inventory,
    fingerprint,
    identification_coverage,
    make_result,
    operation_claim_details,
    source_identity,
    source_key,
    source_ref,
    source_refs,
    storage_content_sha256,
    strict_loads,
    string_list,
    text,
    validate_feature_inventory_context,
    validate_history_event_ids,
)

SCHEMA = "test-condition-candidates-v1"
CROSSCHECK_SCHEMA = "item-condition-candidate-crosscheck-v1"
OWNER = "test-condition-analysis"
CONDITION_ID = re.compile(r"^COND-[0-9]{3,}$")
ITEM_ID = re.compile(r"^ITEM-[0-9]{3,}$")
DRAFT_REF = re.compile(r"^@draft:([a-zA-Z0-9][a-zA-Z0-9._-]{0,63})$")
KINDS = {
    "ui",
    "api",
    "batch",
    "component",
    "event",
    "integration",
    "data",
    "security",
    "nonfunctional",
    "other",
}
CONDITION_KINDS = {
    "input",
    "boundary",
    "authorization",
    "business_state",
    "transition",
    "error_recovery",
    "external_dependency",
    "data_integrity",
    "nonfunctional",
    "other",
}
STATUSES = {"candidate", "unconfirmed", "blocked", "retired"}
IDENTITY_ACTIONS = {"new", "reuse", "split", "merge"}
CONDITION_FIELDS = {
    "condition_id",
    "name",
    "intent",
    "kind",
    "applicable_item_kinds",
    "feature_refs",
    "item_refs",
    "authority_refs",
    "evidence_refs",
    "candidate_state",
    "currentness",
    "unknowns",
}


def _issue(code: str, message: str, *, blocking: bool = True) -> dict[str, Any]:
    return {"code": code, "message": message, "blocking": blocking}


def _source_union(*groups: list[dict[str, str]]) -> list[dict[str, str]]:
    by_key = {source_key(row): row for group in groups for row in group}
    return [by_key[key] for key in sorted(by_key)]


def _same_source(left: dict[str, str], right: dict[str, str]) -> bool:
    return source_key(left) == source_key(right)


def _core(artifact: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value for key, value in artifact.items() if key != "content_fingerprint"
    }


def _authority_ref(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != {"source_ref", "entity_ref"}:
        raise ContractError("authority_ref_invalid", f"{name} fields are invalid")
    ref = source_ref(value["source_ref"], f"{name}.source_ref")
    if ref["owner"] != "spec-analysis":
        raise ContractError(
            "authority_owner_invalid", f"{name} must reference spec-analysis"
        )
    entity_ref = text(value["entity_ref"], f"{name}.entity_ref")
    if not re.fullmatch(r"(?:AUTH|SPEC|DECISION|UNKNOWN)-[A-Za-z0-9._-]+", entity_ref):
        raise ContractError(
            "authority_entity_invalid", f"{name}.entity_ref format is invalid"
        )
    return {"source_ref": ref, "entity_ref": entity_ref}


def _history_event(
    condition_id: str,
    action: str,
    reason: str,
    related: list[str],
    evidence: list[dict[str, str]],
    history: list[dict[str, Any]],
) -> dict[str, Any]:
    event = {
        "condition_id": condition_id,
        "action": action,
        "reason": reason,
        "related_condition_ids": sorted(set(related)),
        "evidence_refs": sorted(evidence, key=source_key),
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


def validate_artifact(value: Any) -> dict[str, Any]:
    required = {
        "schema_version",
        "owner",
        "scope",
        "artifact_ref",
        "feature_inventory_ref",
        "feature_inventory_context",
        "feature_population",
        "source_boundary_complete",
        "source_refs",
        "active_source_refs",
        "previous_artifact_revision",
        "conditions",
        "id_history",
        "history",
        "content_fingerprint",
    }
    legacy_required = required - {"feature_inventory_context"}
    if not isinstance(value, dict) or frozenset(value) not in {
        frozenset(required),
        frozenset(legacy_required),
    }:
        raise ContractError(
            "condition_artifact_schema", "condition artifact fields do not match v1"
        )
    if value["schema_version"] != SCHEMA or value["owner"] != OWNER:
        raise ContractError(
            "condition_artifact_identity",
            "condition artifact owner or schema is invalid",
        )
    text(value["scope"], "scope")
    text(value["artifact_ref"], "artifact_ref")
    if value["previous_artifact_revision"] is not None:
        text(value["previous_artifact_revision"], "previous_artifact_revision")
    population = value["feature_population"]
    if not isinstance(population, list):
        raise ContractError(
            "feature_population_invalid", "feature_population must be an array"
        )
    population_ids: set[str] = set()
    for row in population:
        if not isinstance(row, dict) or set(row) != {"feature_id", "status"}:
            raise ContractError(
                "feature_population_invalid", "feature population row is invalid"
            )
        feature_id = text(row["feature_id"], "feature_population.feature_id")
        if (
            not re.fullmatch(r"FEAT-[0-9]{3,}", feature_id)
            or feature_id in population_ids
        ):
            raise ContractError(
                "feature_population_invalid",
                "feature population IDs must be unique FEAT IDs",
            )
        if not isinstance(row["status"], str) or row["status"] not in {
            "planned",
            "implemented",
            "retired",
            "unknown",
        }:
            raise ContractError(
                "feature_population_invalid", "feature status is invalid"
            )
        population_ids.add(feature_id)
    if not isinstance(value["source_boundary_complete"], bool):
        raise ContractError(
            "source_boundary_invalid", "source_boundary_complete must be boolean"
        )
    all_sources = source_refs(value["source_refs"])
    active_sources = active_source_refs(value["active_source_refs"])
    if any(ref["scope"] != value["scope"] for ref in all_sources):
        raise ContractError(
            "condition_source_scope_mismatch",
            "source refs must use the artifact scope",
        )
    all_source_keys = {source_key(ref) for ref in all_sources}
    if any(source_key(ref) not in all_source_keys for ref in active_sources):
        raise ContractError(
            "active_source_missing", "active source refs must exist in source_refs"
        )
    feature_ref = source_ref(value["feature_inventory_ref"], "feature_inventory_ref")
    if (
        feature_ref["owner"] != "feature-analysis"
        or feature_ref["scope"] != value["scope"]
        or source_key(feature_ref) not in {source_key(row) for row in active_sources}
    ):
        raise ContractError(
            "feature_inventory_ref_invalid",
            "feature inventory ref must be a current source",
        )
    if "feature_inventory_context" in value:
        validate_feature_inventory_context(
            value["feature_inventory_context"],
            scope=value["scope"],
            feature_ref_value=feature_ref,
            feature_population=population,
            source_boundary_complete=value["source_boundary_complete"],
        )
    conditions = value["conditions"]
    if not isinstance(conditions, list):
        raise ContractError("conditions_invalid", "conditions must be an array")
    ids: set[str] = set()
    for row in conditions:
        if not isinstance(row, dict) or set(row) != CONDITION_FIELDS:
            raise ContractError("condition_schema", "condition fields do not match v1")
        condition_id = text(row["condition_id"], "condition_id")
        if not CONDITION_ID.fullmatch(condition_id) or condition_id in ids:
            raise ContractError(
                "condition_id_invalid",
                f"condition ID is invalid or duplicated: {condition_id}",
            )
        ids.add(condition_id)
        text(row["name"], f"{condition_id}.name")
        text(row["intent"], f"{condition_id}.intent")
        if (
            not isinstance(row["kind"], str)
            or row["kind"] not in CONDITION_KINDS
            or not isinstance(row["candidate_state"], str)
            or row["candidate_state"] not in STATUSES
        ):
            raise ContractError(
                "condition_classification_invalid",
                f"{condition_id} kind or state is invalid",
            )
        if row["candidate_state"] == "retired":
            raise ContractError(
                "condition_retirement_invalid",
                "retired conditions must be retained by explicit retirement only",
            )
        item_kinds = string_list(
            row["applicable_item_kinds"],
            f"{condition_id}.applicable_item_kinds",
            required=True,
        )
        if any(kind not in KINDS for kind in item_kinds):
            raise ContractError(
                "condition_item_kind_invalid",
                f"{condition_id} has an unknown item kind",
            )
        features = string_list(row["feature_refs"], f"{condition_id}.feature_refs")
        if any(ref not in population_ids for ref in features):
            raise ContractError(
                "condition_feature_unknown",
                f"{condition_id} references an unknown feature",
            )
        item_refs = string_list(row["item_refs"], f"{condition_id}.item_refs")
        if any(not ITEM_ID.fullmatch(ref) for ref in item_refs):
            raise ContractError(
                "condition_item_ref_invalid",
                f"{condition_id} item refs must be stable ITEM IDs",
            )
        evidence = source_refs(row["evidence_refs"], f"{condition_id}.evidence_refs")
        if not evidence or any(
            source_key(ref) not in all_source_keys for ref in evidence
        ):
            raise ContractError(
                "condition_evidence_invalid",
                f"{condition_id} evidence refs are missing",
            )
        authority_values = row["authority_refs"]
        if not isinstance(authority_values, list):
            raise ContractError(
                "authority_refs_invalid",
                f"{condition_id} authority_refs must be an array",
            )
        authorities = [
            _authority_ref(value, f"{condition_id}.authority_refs[{index}]")
            for index, value in enumerate(authority_values)
        ]
        if len(
            {
                (source_key(value["source_ref"]), value["entity_ref"])
                for value in authorities
            }
        ) != len(authorities):
            raise ContractError(
                "authority_refs_duplicate",
                f"{condition_id} authority refs are duplicated",
            )
        if any(
            source_key(value["source_ref"]) not in {source_key(ref) for ref in evidence}
            for value in authorities
        ):
            raise ContractError(
                "authority_not_evidence",
                f"{condition_id} authority refs must be supported by its evidence refs",
            )
        unknowns = string_list(row["unknowns"], f"{condition_id}.unknowns")
        if row["candidate_state"] == "candidate" and not authorities:
            raise ContractError(
                "condition_authority_required",
                f"{condition_id} without Authority must remain unconfirmed",
            )
        if row["candidate_state"] in {"unconfirmed", "blocked"} and not unknowns:
            raise ContractError(
                "condition_unknown_reason_required",
                f"{condition_id} requires an explicit unknown or blocker",
            )
        if not isinstance(row["currentness"], str) or row["currentness"] not in {
            "current",
            "stale",
            "unknown",
        }:
            raise ContractError(
                "condition_currentness_invalid",
                f"{condition_id} currentness is invalid",
            )
        if row["currentness"] != derive_currentness(evidence, active_sources):
            raise ContractError(
                "condition_currentness_mismatch",
                f"{condition_id} currentness contradicts its evidence",
            )
    history_ids = string_list(value["id_history"], "id_history")
    if history_ids != sorted(history_ids) or any(
        not CONDITION_ID.fullmatch(condition_id) for condition_id in history_ids
    ):
        raise ContractError(
            "condition_history_ids_invalid", "id_history must contain sorted COND IDs"
        )
    if not ids.issubset(history_ids):
        raise ContractError(
            "condition_history_missing", "current IDs must be retained in id_history"
        )
    history = value["history"]
    if not isinstance(history, list):
        raise ContractError("condition_history_invalid", "history must be an array")
    observed_history_ids: set[str] = set()
    seen_events: set[str] = set()
    for event in history:
        if not isinstance(event, dict) or set(event) != {
            "event_id",
            "condition_id",
            "action",
            "reason",
            "related_condition_ids",
            "evidence_refs",
        }:
            raise ContractError(
                "condition_history_invalid", "history event fields are invalid"
            )
        event_id = text(event["event_id"], "history.event_id")
        condition_id = text(event["condition_id"], "history.condition_id")
        if (
            event_id in seen_events
            or not EVENT_ID.fullmatch(event_id)
            or not CONDITION_ID.fullmatch(condition_id)
        ):
            raise ContractError(
                "condition_history_invalid",
                "history event is duplicated or has an invalid ID",
            )
        seen_events.add(event_id)
        observed_history_ids.add(condition_id)
        if event["action"] not in {
            "created",
            "updated",
            "split",
            "merged",
            "retired",
            "source_changed",
        }:
            raise ContractError(
                "condition_history_invalid", "history action is invalid"
            )
        text(event["reason"], "history.reason")
        related = string_list(
            event["related_condition_ids"], "history.related_condition_ids"
        )
        if any(not CONDITION_ID.fullmatch(ref) for ref in related):
            raise ContractError(
                "condition_history_invalid", "history related IDs are invalid"
            )
        evidence = source_refs(event["evidence_refs"], "history.evidence_refs")
        if any(source_key(ref) not in all_source_keys for ref in evidence):
            raise ContractError(
                "condition_history_invalid", "history evidence ref is missing"
            )
    validate_history_event_ids(history)
    if set(history_ids) != observed_history_ids:
        raise ContractError(
            "condition_history_incomplete",
            "each allocated ID must have retained history",
        )
    if any(
        not set(event["related_condition_ids"]).issubset(history_ids)
        for event in history
    ):
        raise ContractError(
            "condition_history_invalid", "history refers to an unallocated condition ID"
        )
    retired_ids = {
        event["condition_id"] for event in history if event["action"] == "retired"
    }
    if any(
        condition_id not in retired_ids for condition_id in set(history_ids) - ids
    ) or any(condition_id in retired_ids for condition_id in ids):
        raise ContractError(
            "condition_retirement_history_mismatch",
            "retired condition state and history differ",
        )
    if value["content_fingerprint"] != fingerprint(_core(value)):
        raise ContractError(
            "condition_fingerprint_mismatch",
            "content_fingerprint does not match artifact",
        )
    return value


def _check_revision_gate(
    request: dict[str, Any], previous: dict[str, Any] | None
) -> str | None:
    expected = request.get("expected_revision")
    current = request.get("current_revision")
    if expected is not None:
        expected = text(expected, "expected_revision")
    if current is not None:
        current = text(current, "current_revision")
    if expected != current:
        return "cas_conflict"
    if previous is None:
        return "current_artifact_missing" if current is not None else None
    validate_artifact(previous)
    if (
        current is None
        or previous["scope"] != request.get("scope")
        or previous["artifact_ref"] != request.get("artifact_ref")
    ):
        return "previous_artifact_identity_mismatch"
    return None


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
            "source_refs must include current feature inventory ref",
        )
    previous = request["previous_artifact"]
    if previous is not None and not isinstance(previous, dict):
        raise ContractError(
            "previous_artifact_invalid", "previous_artifact must be an object or null"
        )
    conflict = _check_revision_gate(request, previous)
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
    if previous is not None and previous["artifact_ref"] != artifact_ref:
        raise ContractError(
            "artifact_ref_mismatch", "artifact_ref cannot change across revisions"
        )
    if not isinstance(request["candidates"], list) or not isinstance(
        request["retirements"], list
    ):
        raise ContractError(
            "candidate_list_invalid", "candidates and retirements must be arrays"
        )
    candidates = request["candidates"]
    if any(not isinstance(row, dict) for row in candidates):
        raise ContractError("candidate_invalid", "each candidate must be an object")
    candidate_fields = {
        "candidate_key",
        "identity_action",
        "condition_id",
        "related_condition_ids",
        "reason",
        "name",
        "intent",
        "kind",
        "applicable_item_kinds",
        "feature_refs",
        "item_refs",
        "authority_refs",
        "evidence_refs",
        "candidate_state",
        "unknowns",
    }
    if any(set(row) != candidate_fields for row in candidates):
        raise ContractError("candidate_schema", "candidate fields do not match v1")
    candidate_keys = [
        text(row.get("candidate_key"), "candidate_key") for row in candidates
    ]
    if len(candidate_keys) != len(set(candidate_keys)):
        raise ContractError(
            "candidate_key_duplicate", "candidate_key values must be unique"
        )
    candidates = sorted(
        candidates, key=lambda row: text(row.get("candidate_key"), "candidate_key")
    )
    previous_rows = {
        row["condition_id"]: copy.deepcopy(row)
        for row in (previous["conditions"] if previous else [])
    }
    previous_ids = set(previous["id_history"] if previous else [])
    current_history = copy.deepcopy(previous["history"] if previous else [])
    all_sources_before = previous["source_refs"] if previous else []
    max_id = max(
        (int(condition_id.split("-")[1]) for condition_id in previous_ids), default=0
    )
    assigned: dict[str, str] = {}
    for row in candidates:
        action = row.get("identity_action")
        key = text(row.get("candidate_key"), "candidate_key")
        if not isinstance(action, str) or action not in IDENTITY_ACTIONS:
            raise ContractError(
                "identity_action_invalid",
                "identity_action must be new, reuse, split, or merge",
            )
        if action == "reuse":
            condition_id = text(row.get("condition_id"), "condition_id")
            if (
                not CONDITION_ID.fullmatch(condition_id)
                or condition_id not in previous_rows
            ):
                raise ContractError(
                    "condition_reuse_invalid",
                    "reuse must reference an existing condition ID",
                )
            if condition_id in assigned.values():
                raise ContractError(
                    "condition_reuse_duplicate",
                    "one condition ID cannot be reused twice",
                )
            assigned[key] = condition_id
        else:
            if row.get("condition_id") is not None:
                raise ContractError(
                    "manual_condition_id_forbidden",
                    "new condition IDs are allocated from history",
                )
            max_id += 1
            assigned[key] = f"COND-{max_id:03d}"
    conditions = copy.deepcopy(previous_rows)
    events = list(current_history)
    changed_ids: set[str] = set()
    merge_sources: set[str] = set()
    source_map = {source_key(ref): ref for ref in current_sources}
    for row in candidates:
        key = text(row["candidate_key"], "candidate_key")
        action = row["identity_action"]
        condition_id = assigned[key]
        related = string_list(
            row.get("related_condition_ids", []), "related_condition_ids"
        )
        reason = text(row.get("reason"), "reason")
        if action == "reuse" and related:
            raise ContractError(
                "reuse_relations_invalid", "reuse cannot also split or merge IDs"
            )
        if action == "split" and (
            not related or any(ref not in previous_rows for ref in related)
        ):
            raise ContractError(
                "split_source_invalid", "split requires existing condition IDs"
            )
        if action == "merge" and (
            len(related) < 2
            or any(
                ref not in previous_rows
                or previous_rows[ref]["candidate_state"] == "retired"
                for ref in related
            )
        ):
            raise ContractError(
                "merge_source_invalid",
                "merge requires at least two existing condition IDs",
            )
        if action == "merge":
            if merge_sources.intersection(related):
                raise ContractError(
                    "merge_source_duplicate",
                    "one existing condition cannot feed multiple merges in the same update",
                )
            merge_sources.update(related)
        if action == "new" and related:
            raise ContractError(
                "new_relations_invalid",
                "new candidate cannot carry split or merge relations",
            )
        name = text(row.get("name"), "candidate.name")
        intent = text(row.get("intent"), "candidate.intent")
        kind = row.get("kind")
        state = row.get("candidate_state")
        if (
            not isinstance(kind, str)
            or kind not in CONDITION_KINDS
            or not isinstance(state, str)
            or state not in STATUSES - {"retired"}
        ):
            raise ContractError(
                "condition_classification_invalid", "candidate kind or state is invalid"
            )
        item_kinds = string_list(
            row.get("applicable_item_kinds"), "applicable_item_kinds", required=True
        )
        if any(item_kind not in KINDS for item_kind in item_kinds):
            raise ContractError(
                "condition_item_kind_invalid", "candidate has an unsupported item kind"
            )
        feature_refs = string_list(row.get("feature_refs", []), "feature_refs")
        if any(ref not in inventory["features"] for ref in feature_refs):
            raise ContractError(
                "candidate_feature_unknown",
                "candidate references a feature outside current inventory",
            )
        item_refs = string_list(row.get("item_refs", []), "item_refs")
        if any(not ITEM_ID.fullmatch(ref) for ref in item_refs):
            raise ContractError(
                "candidate_item_ref_invalid", "item_refs must use stable ITEM IDs"
            )
        evidence = source_refs(row.get("evidence_refs"), "candidate.evidence_refs")
        if any(source_key(ref) not in source_map for ref in evidence):
            raise ContractError(
                "candidate_evidence_not_current",
                "candidate evidence must use current input revisions",
            )
        raw_authorities = row.get("authority_refs")
        if not isinstance(raw_authorities, list):
            raise ContractError(
                "authority_refs_invalid", "authority_refs must be an array"
            )
        authorities = [
            _authority_ref(value, f"authority_refs[{index}]")
            for index, value in enumerate(raw_authorities)
        ]
        if any(
            source_key(value["source_ref"]) not in {source_key(ref) for ref in evidence}
            for value in authorities
        ):
            raise ContractError(
                "authority_not_evidence",
                "Authority refs must be supported by evidence_refs",
            )
        unknowns = string_list(row.get("unknowns", []), "unknowns")
        if state == "candidate" and not authorities:
            raise ContractError(
                "condition_authority_required",
                "a condition without Authority must remain unconfirmed",
            )
        if state in {"unconfirmed", "blocked"} and not unknowns:
            raise ContractError(
                "condition_unknown_reason_required",
                "unconfirmed or blocked candidates require unknowns",
            )
        updated = {
            "condition_id": condition_id,
            "name": name,
            "intent": intent,
            "kind": kind,
            "applicable_item_kinds": sorted(set(item_kinds)),
            "feature_refs": sorted(set(feature_refs)),
            "item_refs": sorted(set(item_refs)),
            "authority_refs": sorted(
                authorities,
                key=lambda value: (
                    source_key(value["source_ref"]),
                    value["entity_ref"],
                ),
            ),
            "evidence_refs": evidence,
            "candidate_state": state,
            "currentness": derive_currentness(evidence, current_sources),
            "unknowns": sorted(set(unknowns)),
        }
        old = previous_rows.get(condition_id)
        if action != "reuse":
            event_action = {"new": "created", "split": "split", "merge": "merged"}[
                action
            ]
            events.append(
                _history_event(
                    condition_id, event_action, reason, related, evidence, events
                )
            )
            changed_ids.add(condition_id)
        elif old != updated:
            events.append(
                _history_event(condition_id, "updated", reason, [], evidence, events)
            )
            changed_ids.add(condition_id)
        conditions[condition_id] = updated
    for retirement in request["retirements"]:
        if not isinstance(retirement, dict) or set(retirement) != {
            "condition_id",
            "reason",
            "evidence_refs",
        }:
            raise ContractError(
                "retirement_invalid", "retirement fields do not match v1"
            )
        condition_id = text(retirement["condition_id"], "retirement.condition_id")
        if (
            condition_id not in conditions
            or condition_id in assigned.values()
            or condition_id in previous_ids
            and conditions[condition_id].get("candidate_state") == "retired"
        ):
            raise ContractError(
                "retirement_target_invalid",
                "retirement must target an existing condition not updated in this request",
            )
        evidence = source_refs(retirement["evidence_refs"], "retirement.evidence_refs")
        if any(source_key(ref) not in source_map for ref in evidence):
            raise ContractError(
                "retirement_evidence_not_current",
                "retirement evidence must be current input",
            )
        reason = text(retirement["reason"], "retirement.reason")
        conditions.pop(condition_id)
        events.append(
            _history_event(condition_id, "retired", reason, [], evidence, events)
        )
        changed_ids.add(condition_id)

    unretired_merge_sources = sorted(
        condition_id for condition_id in merge_sources if condition_id in conditions
    )
    if unretired_merge_sources:
        raise ContractError(
            "merge_sources_not_retired",
            "merge source conditions must be explicitly retired in the same update",
        )
    active_by_identity = {source_identity(ref): ref for ref in current_sources}
    previous_active_by_identity = (
        {source_identity(ref): ref for ref in previous["active_source_refs"]}
        if previous
        else {}
    )
    for condition_id, condition in conditions.items():
        if condition_id in changed_ids:
            continue
        currentness = derive_currentness(condition["evidence_refs"], current_sources)
        condition["currentness"] = currentness
        if currentness == "stale":
            changed_source = next(
                (
                    active_by_identity.get(source_identity(ref))
                    for ref in condition["evidence_refs"]
                    if source_identity(ref) in active_by_identity
                    and source_identity(ref) in previous_active_by_identity
                    and not _same_source(
                        previous_active_by_identity[source_identity(ref)],
                        active_by_identity[source_identity(ref)],
                    )
                    and not _same_source(active_by_identity[source_identity(ref)], ref)
                ),
                None,
            )
            if changed_source is not None:
                events.append(
                    _history_event(
                        condition_id,
                        "source_changed",
                        "evidence source revision changed; revalidation is required",
                        [],
                        [changed_source],
                        events,
                    )
                )
                changed_ids.add(condition_id)
    all_sources = _source_union(all_sources_before, current_sources)
    feature_population = [
        {
            "feature_id": feature_id,
            "status": inventory["features"][feature_id]["status"],
        }
        for feature_id in sorted(inventory["features"])
    ]
    core = {
        "schema_version": SCHEMA,
        "owner": OWNER,
        "scope": scope,
        "artifact_ref": artifact_ref,
        "feature_inventory_ref": feature_source,
        "feature_inventory_context": inventory["feature_inventory_context"],
        "feature_population": feature_population,
        "source_boundary_complete": inventory["source_boundary_complete"],
        "source_refs": all_sources,
        "active_source_refs": current_sources,
        "previous_artifact_revision": request["current_revision"],
        "conditions": sorted(conditions.values(), key=lambda row: row["condition_id"]),
        "id_history": sorted(
            previous_ids | set(conditions) | {event["condition_id"] for event in events}
        ),
        "history": events,
    }
    candidate = {**core, "content_fingerprint": fingerprint(core)}
    validate_artifact(candidate)
    if previous is not None:
        old_projection = {
            key: value
            for key, value in previous.items()
            if key != "content_fingerprint"
        }
        new_projection = {
            key: value
            for key, value in candidate.items()
            if key not in {"content_fingerprint", "previous_artifact_revision"}
        }
        old_projection.pop("previous_artifact_revision", None)
        no_change = fingerprint(old_projection) == fingerprint(new_projection)
    else:
        no_change = False
    stale = sorted(
        row["condition_id"]
        for row in candidate["conditions"]
        if row["currentness"] == "stale"
    )
    unknown = sorted(
        row["condition_id"]
        for row in candidate["conditions"]
        if row["currentness"] == "unknown"
    )
    unconfirmed = sorted(
        row["condition_id"]
        for row in candidate["conditions"]
        if row["candidate_state"] == "unconfirmed"
    )
    blocked = sorted(
        row["condition_id"]
        for row in candidate["conditions"]
        if row["candidate_state"] == "blocked"
    )
    unknown_feature_ids = sorted(
        row["feature_id"] for row in feature_population if row["status"] == "unknown"
    )
    status = (
        "candidate_ready_unpersisted"
        if not stale
        and not unknown
        and not unconfirmed
        and not blocked
        and not unknown_feature_ids
        and inventory["source_boundary_complete"]
        and inventory["analysis_complete"]
        else "incomplete"
    )
    analysis_status = (
        "complete" if status == "candidate_ready_unpersisted" else "incomplete"
    )
    issues = []
    if stale:
        issues.append(
            _issue(
                "source_stale",
                "source changes require revalidation of affected condition candidates",
            )
        )
    if unknown:
        issues.append(
            _issue(
                "source_unknown",
                "some condition candidates do not have current source refs",
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
    if unknown_feature_ids:
        issues.append(
            _issue(
                "unknown_feature_status",
                "some features have unknown status and are not confirmed active",
                blocking=False,
            )
        )
    if unconfirmed:
        issues.append(
            _issue(
                "unconfirmed_conditions",
                "unconfirmed conditions are not complete candidates",
                blocking=False,
            )
        )
    if blocked:
        issues.append(
            _issue(
                "blocked_conditions",
                "blocked conditions are not complete candidates",
                blocking=False,
            )
        )
    recheck_condition_ids = sorted(
        set(stale) | set(unknown) | set(unconfirmed) | set(blocked)
    )
    if no_change:
        return make_result(
            "no_change",
            valid=True,
            issues=issues,
            analysis_status=analysis_status,
            candidate=previous,
            candidate_condition_ids=dict(sorted(assigned.items())),
            impacted_condition_ids=sorted(changed_ids),
            stale_condition_ids=stale,
            unknown_condition_ids=unknown,
            unconfirmed_condition_ids=unconfirmed,
            blocked_condition_ids=blocked,
            unknown_feature_ids=unknown_feature_ids,
            recheck_condition_ids=recheck_condition_ids,
            write_precondition={"performed": False, "provider_selected": False},
        )
    return make_result(
        status,
        valid=True,
        issues=issues,
        analysis_status=analysis_status,
        candidate=candidate,
        candidate_condition_ids=dict(sorted(assigned.items())),
        impacted_condition_ids=sorted(changed_ids),
        stale_condition_ids=stale,
        unknown_condition_ids=unknown,
        unconfirmed_condition_ids=unconfirmed,
        blocked_condition_ids=blocked,
        unknown_feature_ids=unknown_feature_ids,
        recheck_condition_ids=recheck_condition_ids,
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
            "storage_content_encoding": STORAGE_CONTENT_ENCODING,
            "storage_content_sha256": storage_content_sha256(candidate),
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


def validate_readback(request: dict[str, Any]) -> dict[str, Any]:
    required = {"operation", "candidate_artifact", "readback"}
    if (
        not required.issubset(request)
        or set(request) - required - {"expected_revision"}
        or request.get("operation") != "validate_readback"
    ):
        raise ContractError(
            "request_schema", "validate_readback request fields do not match v1"
        )
    expected_revision = request.get("expected_revision")
    if expected_revision is not None:
        expected_revision = text(expected_revision, "expected_revision")
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
    # content_hash is the provider's hash of the stored bytes (the complete
    # canonical artifact), not the candidate fingerprint or the provider revision.
    storage_hash = storage_content_sha256(artifact)
    issues = []
    if normalized["content_hash"] != storage_hash:
        issues.append(
            _issue(
                "readback_hash_mismatch",
                "saved content hash does not match the canonical stored artifact",
            )
        )
    if expected_revision is not None and normalized["revision"] != expected_revision:
        issues.append(
            _issue(
                "readback_revision_mismatch",
                "provider readback revision differs from the expected saved revision",
            )
        )
    matches = not issues
    return make_result(
        "readback_matches" if matches else "blocked",
        valid=matches,
        issues=issues,
        candidate_fingerprint=artifact["content_fingerprint"],
        storage_content_sha256=storage_hash,
        storage_content_encoding=STORAGE_CONTENT_ENCODING,
        readback={**normalized, "revision_is_provider_owned": True},
        provider_authenticity="not_established_by_this_validator",
        provider_cas="not_established_by_this_validator",
    )


def impact(request: dict[str, Any]) -> dict[str, Any]:
    if (
        set(request) != {"operation", "artifact", "current_source_refs"}
        or request.get("operation") != "impact"
    ):
        raise ContractError("request_schema", "impact request fields do not match v1")
    artifact = validate_artifact(request["artifact"])
    active = active_source_refs(request["current_source_refs"])
    stale: list[str] = []
    unknown: list[str] = []
    for condition in artifact["conditions"]:
        state = derive_currentness(condition["evidence_refs"], active)
        if state == "stale":
            stale.append(condition["condition_id"])
        elif state == "unknown":
            unknown.append(condition["condition_id"])
    return make_result(
        "incomplete" if stale or unknown else "current",
        valid=True,
        issues=(
            [
                _issue(
                    "source_stale",
                    "only candidates linked to changed source refs require revalidation",
                )
            ]
            if stale
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
            if unknown
            else []
        ),
        impacted_condition_ids=stale,
        source_unknown_condition_ids=unknown,
        unaffected_condition_ids=sorted(
            row["condition_id"]
            for row in artifact["conditions"]
            if row["condition_id"] not in set(stale + unknown)
        ),
    )


def crosscheck(request: dict[str, Any]) -> dict[str, Any]:
    required = {"operation", "item_artifact", "condition_artifact", "candidate_pairs"}
    if set(request) != required or request.get("operation") != "crosscheck":
        raise ContractError(
            "request_schema", "crosscheck request fields do not match v1"
        )
    item_artifact = request["item_artifact"]
    if not isinstance(item_artifact, dict):
        raise ContractError("item_artifact_invalid", "item_artifact must be an object")
    from item_artifact_contract import validate_item_artifact

    validate_item_artifact(item_artifact)
    condition_artifact = validate_artifact(request["condition_artifact"])
    if item_artifact["scope"] != condition_artifact["scope"]:
        raise ContractError(
            "scope_mismatch", "item and condition artifacts must share scope"
        )
    item_feature_ref = item_artifact["feature_inventory_ref"]
    condition_feature_ref = condition_artifact["feature_inventory_ref"]
    if source_key(item_feature_ref) != source_key(condition_feature_ref):
        raise ContractError(
            "feature_revision_mismatch",
            "item and condition artifacts must use the same feature inventory revision",
        )
    item_context = item_artifact.get("feature_inventory_context")
    condition_context = condition_artifact.get("feature_inventory_context")
    if (
        item_context is not None
        and condition_context is not None
        and item_context != condition_context
    ):
        raise ContractError(
            "feature_inventory_context_mismatch",
            "item and condition artifacts must preserve the same B snapshot handoff",
        )
    if item_artifact["feature_population"] != condition_artifact["feature_population"]:
        raise ContractError(
            "feature_population_mismatch",
            "item and condition artifacts must preserve the same feature population",
        )
    if not isinstance(request["candidate_pairs"], list):
        raise ContractError(
            "candidate_pairs_invalid", "candidate_pairs must be an array"
        )

    item_by_id = {row["item_id"]: row for row in item_artifact["items"]}
    condition_by_id = {
        row["condition_id"]: row for row in condition_artifact["conditions"]
    }
    item_history = set(item_artifact["id_history"])
    condition_history = set(condition_artifact["id_history"])
    retired_item_ids = sorted(
        (item_history - set(item_by_id))
        | {item_id for item_id, row in item_by_id.items() if row["status"] == "retired"}
    )
    retired_condition_ids = sorted(condition_history - set(condition_by_id))

    active_sources_by_identity: dict[tuple[str, str, str], dict[str, str]] = {}
    for ref in (
        item_artifact["active_source_refs"] + condition_artifact["active_source_refs"]
    ):
        identity = source_identity(ref)
        old = active_sources_by_identity.get(identity)
        if old is not None and source_key(old) != source_key(ref):
            raise ContractError(
                "crosscheck_source_revision_mismatch",
                "item and condition artifacts use competing revisions of one source",
            )
        active_sources_by_identity[identity] = ref
    active_sources = sorted(active_sources_by_identity.values(), key=source_key)
    all_source_keys = {
        source_key(ref)
        for ref in item_artifact["source_refs"] + condition_artifact["source_refs"]
    }

    unresolved_item_refs: list[dict[str, Any]] = []
    unresolved_condition_refs: list[dict[str, Any]] = []
    recheck_item_ids: set[str] = set()
    recheck_condition_ids: set[str] = set()

    def item_reference_reason(item_id: str) -> str | None:
        row = item_by_id.get(item_id)
        if row is not None and row["status"] == "retired":
            return "item_retired"
        if row is not None and row["status"] == "unknown":
            return "item_unconfirmed"
        if row is not None and row["currentness"] == "stale":
            return "item_stale"
        if row is not None and row["currentness"] == "unknown":
            return "item_currentness_unknown"
        if row is not None:
            return None
        if item_id in item_history:
            return "item_retired"
        return "item_not_found"

    def condition_reference_reason(condition_id: str) -> str | None:
        if condition_id in condition_by_id:
            return None
        if condition_id in condition_history:
            return "condition_retired"
        return "condition_not_found"

    def condition_currentness_reason(row: dict[str, Any]) -> str | None:
        if row["currentness"] == "stale":
            return "condition_stale"
        if row["currentness"] == "unknown":
            return "condition_currentness_unknown"
        return None

    for condition in condition_by_id.values():
        for item_id in condition["item_refs"]:
            reason = item_reference_reason(item_id)
            if reason is not None:
                unresolved_item_refs.append(
                    {
                        "origin": "condition_item_refs",
                        "condition_id": condition["condition_id"],
                        "item_id": item_id,
                        "reason": reason,
                        "state": "unconfirmed",
                    }
                )
                recheck_condition_ids.add(condition["condition_id"])
                recheck_item_ids.add(item_id)

    pair_rows: list[dict[str, Any]] = []
    candidate_pair_inconsistencies: list[dict[str, Any]] = []
    seen_pairs: set[tuple[str, str]] = set()
    for index, pair in enumerate(request["candidate_pairs"]):
        expected = {"item_id", "condition_id", "status", "rationale", "evidence_refs"}
        if not isinstance(pair, dict) or set(pair) != expected:
            raise ContractError(
                "candidate_pair_schema", f"candidate_pairs[{index}] fields are invalid"
            )
        item_id = text(pair["item_id"], "candidate_pair.item_id")
        condition_id = text(pair["condition_id"], "candidate_pair.condition_id")
        if not ITEM_ID.fullmatch(item_id):
            raise ContractError(
                "candidate_pair_item_id_invalid", "candidate item ID format is invalid"
            )
        if not CONDITION_ID.fullmatch(condition_id):
            raise ContractError(
                "candidate_pair_condition_id_invalid",
                "candidate condition ID format is invalid",
            )
        status = pair["status"]
        if not isinstance(status, str) or status not in {
            "proposed",
            "unconfirmed",
            "blocked",
        }:
            raise ContractError(
                "formal_disposition_forbidden",
                "D crosscheck cannot record E-owned applicability or formal disposition decisions",
            )
        rationale = text(pair["rationale"], "candidate_pair.rationale")
        evidence = source_refs(pair["evidence_refs"], "candidate_pair.evidence_refs")
        if any(source_key(ref) not in all_source_keys for ref in evidence):
            raise ContractError(
                "candidate_pair_evidence_missing",
                "candidate pair evidence must come from supplied owner artifacts",
            )
        pair_key = (item_id, condition_id)
        if pair_key in seen_pairs:
            raise ContractError(
                "candidate_pair_duplicate", "candidate pair is duplicated"
            )
        seen_pairs.add(pair_key)

        item_reason = item_reference_reason(item_id)
        condition_reason = condition_reference_reason(condition_id)
        if item_reason is not None:
            unresolved_item_refs.append(
                {
                    "origin": "candidate_pairs",
                    "condition_id": condition_id,
                    "item_id": item_id,
                    "reason": item_reason,
                    "state": "unconfirmed",
                    "candidate_pair": {
                        "status": status,
                        "rationale": rationale,
                        "evidence_refs": evidence,
                    },
                }
            )
            recheck_item_ids.add(item_id)
            if condition_id in condition_by_id:
                recheck_condition_ids.add(condition_id)
        if condition_reason is not None:
            unresolved_condition_refs.append(
                {
                    "origin": "candidate_pairs",
                    "condition_id": condition_id,
                    "item_id": item_id,
                    "reason": condition_reason,
                    "state": "unconfirmed",
                    "candidate_pair": {
                        "status": status,
                        "rationale": rationale,
                        "evidence_refs": evidence,
                    },
                }
            )
            recheck_condition_ids.add(condition_id)
            if item_id in item_by_id and item_by_id[item_id]["status"] != "retired":
                recheck_item_ids.add(item_id)
        if item_reason is not None or condition_reason is not None:
            continue

        item = item_by_id[item_id]
        condition = condition_by_id[condition_id]
        # A condition recorded as unconfirmed/blocked must not be promoted to a
        # proposed pair; that stays a contract violation. A condition that is
        # still a candidate but whose evidence went stale/unknown is an ordinary
        # owner-side recheck, reported like the unresolved item references above.
        # (The item was already resolved as current and confirmed here.)
        if status == "proposed" and condition["candidate_state"] != "candidate":
            raise ContractError(
                "candidate_pair_unconfirmed",
                "only confirmed candidate conditions may be a proposed pair",
            )
        currentness_reason = condition_currentness_reason(condition)
        if currentness_reason is not None:
            unresolved_condition_refs.append(
                {
                    "origin": "candidate_pairs",
                    "condition_id": condition_id,
                    "item_id": item_id,
                    "reason": currentness_reason,
                    "state": "unconfirmed",
                    "candidate_pair": {
                        "status": status,
                        "rationale": rationale,
                        "evidence_refs": evidence,
                    },
                }
            )
            recheck_condition_ids.add(condition_id)
            recheck_item_ids.add(item_id)
            continue

        machine_issues: list[str] = []
        if item["kind"] not in condition["applicable_item_kinds"]:
            machine_issues.append("item_kind_not_in_condition_applicability")
        if (
            item["feature_refs"]
            and condition["feature_refs"]
            and not set(item["feature_refs"]).intersection(condition["feature_refs"])
        ):
            machine_issues.append("item_and_condition_feature_refs_disjoint")
        pair_currentness = derive_currentness(evidence, active_sources)
        if pair_currentness != "current":
            machine_issues.append(f"pair_evidence_{pair_currentness}")
        if machine_issues:
            candidate_pair_inconsistencies.append(
                {
                    "item_id": item_id,
                    "condition_id": condition_id,
                    "codes": machine_issues,
                }
            )
            recheck_item_ids.add(item_id)
            recheck_condition_ids.add(condition_id)
            if status == "proposed":
                status = "unconfirmed"
        pair_rows.append(
            {
                "item_id": item_id,
                "condition_id": condition_id,
                "status": status,
                "rationale": rationale,
                "evidence_refs": evidence,
                "machine_check_issues": machine_issues,
            }
        )

    item_rows = list(item_by_id.values())
    condition_rows = list(condition_by_id.values())
    active_items = [row for row in item_rows if row["status"] != "retired"]
    active_conditions = condition_rows
    stale_item_ids = sorted(
        row["item_id"] for row in active_items if row["currentness"] == "stale"
    )
    unknown_item_ids = sorted(
        row["item_id"]
        for row in active_items
        if row["currentness"] == "unknown" or row["status"] == "unknown"
    )
    stale_condition_ids = sorted(
        row["condition_id"]
        for row in active_conditions
        if row["currentness"] == "stale"
    )
    unknown_condition_ids = sorted(
        row["condition_id"]
        for row in active_conditions
        if row["currentness"] == "unknown"
    )
    unconfirmed_condition_ids = sorted(
        row["condition_id"]
        for row in active_conditions
        if row["candidate_state"] == "unconfirmed"
    )
    blocked_condition_ids = sorted(
        row["condition_id"]
        for row in active_conditions
        if row["candidate_state"] == "blocked"
    )
    item_candidates_in_pairs = {row["item_id"] for row in pair_rows}
    condition_candidates_in_pairs = {row["condition_id"] for row in pair_rows}
    items_without_pair = sorted(
        row["item_id"]
        for row in active_items
        if row["item_id"] not in item_candidates_in_pairs
    )
    conditions_without_pair = sorted(
        row["condition_id"]
        for row in active_conditions
        if row["condition_id"] not in condition_candidates_in_pairs
    )

    feature_population = item_artifact["feature_population"]
    active_feature_rows = [
        row for row in feature_population if row["status"] != "retired"
    ]
    active_feature_ids = {row["feature_id"] for row in active_feature_rows}
    unknown_feature_ids = sorted(
        row["feature_id"] for row in active_feature_rows if row["status"] == "unknown"
    )
    item_features = {feature for row in active_items for feature in row["feature_refs"]}
    unrepresented = sorted(active_feature_ids - item_features)
    context_available = item_context is not None and condition_context is not None
    item_context = item_context or {}
    condition_context = condition_context or {}
    source_population_complete = context_available and (
        item_context["analysis_status"] == "complete"
        and condition_context["analysis_status"] == "complete"
        and item_artifact["source_boundary_complete"]
        and condition_artifact["source_boundary_complete"]
    )
    all_items_current = not stale_item_ids and not unknown_item_ids
    all_conditions_confirmed = not (
        stale_condition_ids
        or unknown_condition_ids
        or unconfirmed_condition_ids
        or blocked_condition_ids
    ) and all(row["candidate_state"] == "candidate" for row in active_conditions)
    no_unresolved_references = (
        not unresolved_item_refs and not unresolved_condition_refs
    )
    no_unresolved_pairs = all(row["status"] == "proposed" for row in pair_rows)
    no_machine_conflicts = not candidate_pair_inconsistencies
    coverage = identification_coverage(
        feature_population,
        item_features,
        population_complete=source_population_complete,
        items_current=all_items_current,
    )
    zero_denominator = coverage["zero_denominator"]
    complete = (
        source_population_complete
        and all_items_current
        and all_conditions_confirmed
        and no_unresolved_references
        and no_unresolved_pairs
        and no_machine_conflicts
        and not unknown_feature_ids
        and not zero_denominator
    )

    issues = []
    if not source_population_complete:
        issues.append(
            _issue(
                "source_population_incomplete",
                "B analysis, feature source boundary, or legacy handoff context is incomplete",
                blocking=False,
            )
        )
    if zero_denominator:
        issues.append(
            _issue(
                "zero_denominator",
                "confirmed active feature population is empty",
                blocking=False,
            )
        )
    if stale_item_ids or stale_condition_ids:
        issues.append(
            _issue(
                "stale_candidates",
                "stale item or condition evidence requires revalidation",
                blocking=False,
            )
        )
    if unknown_item_ids or unknown_condition_ids:
        issues.append(
            _issue(
                "unknown_candidates",
                "candidate currentness or item status is unknown",
                blocking=False,
            )
        )
    if unconfirmed_condition_ids:
        issues.append(
            _issue(
                "unconfirmed_conditions",
                "unconfirmed conditions are not complete candidates",
                blocking=False,
            )
        )
    if blocked_condition_ids:
        issues.append(
            _issue(
                "blocked_conditions",
                "blocked conditions are not complete candidates",
                blocking=False,
            )
        )
    if unresolved_item_refs or unresolved_condition_refs:
        issues.append(
            _issue(
                "unresolved_candidate_references",
                "well-formed references need owner-side recheck",
                blocking=False,
            )
        )
    if candidate_pair_inconsistencies:
        issues.append(
            _issue(
                "candidate_pair_inconsistency",
                "machine-detectable pair conflicts need review",
                blocking=False,
            )
        )
    if any(row["status"] in {"unconfirmed", "blocked"} for row in pair_rows):
        issues.append(
            _issue(
                "candidate_pairs_unresolved",
                "candidate pairs include unconfirmed or blocked entries",
                blocking=False,
            )
        )

    return make_result(
        "candidate_crosscheck_complete" if complete else "incomplete",
        valid=True,
        issues=issues,
        crosscheck_schema=CROSSCHECK_SCHEMA,
        scope=item_artifact["scope"],
        item_artifact_ref={
            "owner": item_artifact["owner"],
            "scope": item_artifact["scope"],
            "artifact_ref": item_artifact["artifact_ref"],
            "content_fingerprint": item_artifact["content_fingerprint"],
        },
        condition_artifact_ref={
            "owner": condition_artifact["owner"],
            "scope": condition_artifact["scope"],
            "artifact_ref": condition_artifact["artifact_ref"],
            "content_fingerprint": condition_artifact["content_fingerprint"],
        },
        candidate_pairs=sorted(
            pair_rows, key=lambda row: (row["item_id"], row["condition_id"])
        ),
        candidate_pair_inconsistencies=candidate_pair_inconsistencies,
        unresolved_item_references=unresolved_item_refs,
        unresolved_condition_references=unresolved_condition_refs,
        recheck_item_ids=sorted(recheck_item_ids),
        recheck_condition_ids=sorted(recheck_condition_ids),
        retired_item_ids=retired_item_ids,
        retired_condition_ids=retired_condition_ids,
        unconfirmed_item_ids=sorted(set(unknown_item_ids)),
        stale_item_ids=stale_item_ids,
        stale_condition_ids=stale_condition_ids,
        unknown_condition_ids=unknown_condition_ids,
        unconfirmed_condition_ids=unconfirmed_condition_ids,
        blocked_condition_ids=blocked_condition_ids,
        unrepresented_feature_refs=unrepresented,
        items_without_pair_proposal=items_without_pair,
        conditions_without_pair_proposal=conditions_without_pair,
        candidate_identification_coverage=coverage,
        metrics={
            "candidate_item_count": sum(
                row["status"] != "retired" for row in item_rows
            ),
            "condition_candidate_count": len(active_conditions),
            "candidate_pair_count": len(pair_rows),
            "candidate_pair_proposed_count": sum(
                row["status"] == "proposed" for row in pair_rows
            ),
            "candidate_pair_unconfirmed_count": sum(
                row["status"] == "unconfirmed" for row in pair_rows
            ),
            "candidate_pair_blocked_count": sum(
                row["status"] == "blocked" for row in pair_rows
            ),
            "formal_applicability_decisions": {
                "owner": "test-condition-design",
                "state": "not_provided_to_D",
                "count": None,
            },
            "formal_tcn_ci_design": {
                "owner": "test-condition-design",
                "state": "not_provided_to_D",
                "count": None,
            },
            "execution": {
                "owner": "test-execution or testware-execution",
                "state": "not_provided_to_D",
                "count": None,
            },
        },
        cartesian_product_generated=False,
    )


def run(request: Any) -> dict[str, Any]:
    if not isinstance(request, dict):
        raise ContractError("request_invalid", "request must be a JSON object")
    operation = request.get("operation")
    if operation == "materialize":
        return materialize(request)
    if operation == "validate":
        return validate(request)
    if operation == "validate_readback":
        return validate_readback(request)
    if operation == "impact":
        return impact(request)
    if operation == "crosscheck":
        return crosscheck(request)
    raise ContractError(
        "operation_invalid",
        "operation must be materialize, validate, impact, or crosscheck",
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
