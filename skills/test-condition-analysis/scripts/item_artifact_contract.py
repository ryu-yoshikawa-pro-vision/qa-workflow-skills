"""Read-only validator for the item artifact accepted by the D crosscheck."""

from __future__ import annotations

import re
from typing import Any

from candidate_support import (
    ContractError,
    fingerprint,
    source_key,
    source_ref,
    source_refs,
    string_list,
    text,
)

ITEM_FIELDS = {
    "item_id",
    "name",
    "description",
    "kind",
    "status",
    "parent_item_ids",
    "feature_refs",
    "evidence_refs",
    "currentness",
}


def validate_item_artifact(value: Any) -> dict[str, Any]:
    required = {
        "schema_version",
        "owner",
        "scope",
        "artifact_ref",
        "feature_inventory_ref",
        "feature_population",
        "source_boundary_complete",
        "source_refs",
        "active_source_refs",
        "previous_artifact_revision",
        "items",
        "id_history",
        "history",
        "content_fingerprint",
    }
    if not isinstance(value, dict) or set(value) != required:
        raise ContractError(
            "item_artifact_schema", "item artifact fields do not match v1"
        )
    if (
        value["schema_version"] != "test-item-candidates-v1"
        or value["owner"] != "test-item-analysis"
    ):
        raise ContractError(
            "item_artifact_identity", "item artifact owner or schema is invalid"
        )
    text(value["scope"], "item_artifact.scope")
    text(value["artifact_ref"], "item_artifact.artifact_ref")
    all_sources = source_refs(value["source_refs"])
    active_sources = source_refs(value["active_source_refs"])
    if not {source_key(row) for row in active_sources}.issubset(
        {source_key(row) for row in all_sources}
    ):
        raise ContractError(
            "item_active_source_missing",
            "active source refs are missing from item artifact",
        )
    feature_ref = source_ref(
        value["feature_inventory_ref"], "item_artifact.feature_inventory_ref"
    )
    if feature_ref["owner"] != "feature-analysis" or source_key(feature_ref) not in {
        source_key(row) for row in active_sources
    }:
        raise ContractError(
            "item_feature_ref_invalid", "item feature inventory ref is not current"
        )
    population = value["feature_population"]
    if not isinstance(population, list):
        raise ContractError(
            "item_feature_population_invalid", "feature_population must be an array"
        )
    feature_ids: set[str] = set()
    for row in population:
        if not isinstance(row, dict) or set(row) != {"feature_id", "status"}:
            raise ContractError(
                "item_feature_population_invalid", "feature population row is invalid"
            )
        feature_id = text(row["feature_id"], "item_artifact.feature_id")
        if not re.fullmatch(r"FEAT-[0-9]{3,}", feature_id) or feature_id in feature_ids:
            raise ContractError(
                "item_feature_population_invalid", "feature ID is invalid or duplicated"
            )
        feature_ids.add(feature_id)
    if not isinstance(value["source_boundary_complete"], bool):
        raise ContractError(
            "item_source_boundary_invalid", "source_boundary_complete must be boolean"
        )
    items = value["items"]
    if not isinstance(items, list):
        raise ContractError("item_rows_invalid", "items must be an array")
    by_id: dict[str, dict[str, Any]] = {}
    for row in items:
        if not isinstance(row, dict) or set(row) != ITEM_FIELDS:
            raise ContractError("item_row_schema", "item fields do not match v1")
        item_id = text(row["item_id"], "item_id")
        if not re.fullmatch(r"ITEM-[0-9]{3,}", item_id) or item_id in by_id:
            raise ContractError("item_id_invalid", "item IDs must be unique ITEM IDs")
        if row["status"] not in {
            "planned",
            "unimplemented",
            "implemented",
            "unknown",
            "retired",
        }:
            raise ContractError("item_status_invalid", "item status is invalid")
        parent_ids = string_list(row["parent_item_ids"], "parent_item_ids")
        feature_refs = string_list(row["feature_refs"], "feature_refs")
        if any(not re.fullmatch(r"ITEM-[0-9]{3,}", parent) for parent in parent_ids):
            raise ContractError("item_parent_invalid", "parent IDs must be ITEM IDs")
        if any(feature not in feature_ids for feature in feature_refs):
            raise ContractError(
                "item_feature_unknown", "item references an unknown feature"
            )
        evidence = source_refs(row["evidence_refs"], "item.evidence_refs")
        if not {source_key(ref) for ref in evidence}.issubset(
            {source_key(ref) for ref in all_sources}
        ):
            raise ContractError("item_evidence_unknown", "item evidence ref is missing")
        if row["currentness"] not in {"current", "stale", "unknown"}:
            raise ContractError(
                "item_currentness_invalid", "item currentness is invalid"
            )
        by_id[item_id] = row
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(item_id: str) -> None:
        if item_id in visiting:
            raise ContractError(
                "item_parent_cycle", "item parent graph contains a cycle"
            )
        if item_id in visited:
            return
        visiting.add(item_id)
        for parent in by_id[item_id]["parent_item_ids"]:
            if parent not in by_id:
                raise ContractError(
                    "item_parent_missing", "item references a missing parent"
                )
            visit(parent)
        visiting.remove(item_id)
        visited.add(item_id)

    for item_id in by_id:
        visit(item_id)
    id_history = string_list(value["id_history"], "item.id_history")
    if (
        id_history != sorted(id_history)
        or not set(by_id).issubset(id_history)
        or any(not re.fullmatch(r"ITEM-[0-9]{3,}", item_id) for item_id in id_history)
    ):
        raise ContractError("item_history_ids_invalid", "item id history is incomplete")
    events = value["history"]
    if not isinstance(events, list) or {
        event.get("item_id") for event in events if isinstance(event, dict)
    } != set(id_history):
        raise ContractError(
            "item_history_invalid", "item history events do not cover id history"
        )
    if value["content_fingerprint"] != fingerprint(
        {key: field for key, field in value.items() if key != "content_fingerprint"}
    ):
        raise ContractError(
            "item_fingerprint_mismatch", "item content fingerprint is invalid"
        )
    return value
