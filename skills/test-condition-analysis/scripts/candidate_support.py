"""Small, isolated helpers shared by the test-item candidate contract."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

MAX_INPUT_BYTES = 16 * 1024 * 1024
HEX_SHA256 = re.compile(r"^[0-9a-f]{64}$")
FEATURE_ID = re.compile(r"^FEAT-[0-9]{3,}$")
SOURCE_REF_FIELDS = {"owner", "scope", "artifact_ref", "revision", "content_hash"}
ITEM_ID = re.compile(r"^ITEM-[0-9]{3,}$")
EVENT_ID = re.compile(r"^[0-9a-f]{64}$")
ITEM_KINDS = {
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
ITEM_STATUSES = {"planned", "unimplemented", "implemented", "unknown", "retired"}
B_CHANGE_CLASSES = {"impact", "no_impact", "out_of_scope", "unclassified", "unresolved"}
B_CANDIDATE_STATUSES = {"mapped", "unresolved", "excluded"}
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


class ContractError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ContractError("duplicate_json_key", "JSON object key is duplicated")
        result[key] = value
    return result


def _reject_nonfinite_constant(value: str) -> None:
    raise ContractError(
        "invalid_json_constant", f"non-finite JSON number is not allowed: {value}"
    )


def strict_loads(raw: bytes) -> Any:
    if len(raw) > MAX_INPUT_BYTES:
        raise ContractError("limit_exceeded", "input exceeds 16 MiB")
    try:
        return json.loads(
            raw.decode("utf-8", "strict"),
            object_pairs_hook=_pairs,
            parse_constant=_reject_nonfinite_constant,
        )
    except ContractError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as exc:
        raise ContractError("invalid_json", "input must be valid UTF-8 JSON") from exc


def canonical_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError, RecursionError) as exc:
        raise ContractError(
            "invalid_json_value", "value is not canonical JSON"
        ) from exc


def fingerprint(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def validate_history_event_ids(events: list[dict[str, Any]]) -> None:
    """Accept legacy event hashes, then require linked IDs for new appended events."""
    previous_event_id = None
    linked_history_started = False
    for sequence, event in enumerate(events):
        body = {key: value for key, value in event.items() if key != "event_id"}
        event_id = event["event_id"]
        legacy_id = fingerprint(body)
        linked_id = fingerprint(
            {
                "event": body,
                "sequence": sequence,
                "previous_event_id": previous_event_id,
            }
        )
        if linked_history_started:
            if event_id != linked_id:
                raise ContractError(
                    "history_event_integrity",
                    "linked history event is altered or missing",
                )
        elif event_id == linked_id:
            linked_history_started = True
        elif event_id != legacy_id:
            raise ContractError(
                "history_event_integrity",
                "legacy history event does not match its content",
            )
        previous_event_id = event_id


def text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip() or "\x00" in value:
        raise ContractError("invalid_field", f"{name} must be a non-empty string")
    return value.strip()


def string_list(value: Any, name: str, *, required: bool = False) -> list[str]:
    if not isinstance(value, list) or any(
        not isinstance(row, str) or not row.strip() or "\x00" in row for row in value
    ):
        raise ContractError("invalid_field", f"{name} must be a string array")
    values = [row.strip() for row in value]
    if len(values) != len(set(values)):
        raise ContractError("duplicate_reference", f"{name} contains duplicates")
    if required and not values:
        raise ContractError("missing_reference", f"{name} must not be empty")
    return values


def source_ref(value: Any, name: str = "source_ref") -> dict[str, str]:
    if not isinstance(value, dict) or set(value) != SOURCE_REF_FIELDS:
        raise ContractError("invalid_source_ref", f"{name} field set is invalid")
    result = {
        field: text(value[field], f"{name}.{field}") for field in SOURCE_REF_FIELDS
    }
    if not HEX_SHA256.fullmatch(result["content_hash"]):
        raise ContractError(
            "invalid_source_hash", f"{name}.content_hash must be SHA-256 hex"
        )
    return {field: result[field] for field in sorted(result)}


def source_key(value: dict[str, str]) -> tuple[str, str, str, str, str]:
    return tuple(
        value[field]
        for field in ("owner", "scope", "artifact_ref", "revision", "content_hash")
    )


def source_identity(value: dict[str, str]) -> tuple[str, str, str]:
    return value["owner"], value["scope"], value["artifact_ref"]


def source_refs(
    values: Any, name: str = "source_refs", *, required: bool = True
) -> list[dict[str, str]]:
    if not isinstance(values, list):
        raise ContractError("invalid_source_refs", f"{name} must be an array")
    rows = [source_ref(row, f"{name}[{index}]") for index, row in enumerate(values)]
    keys = [source_key(row) for row in rows]
    if len(keys) != len(set(keys)):
        raise ContractError("duplicate_source_ref", f"{name} contains duplicates")
    if required and not rows:
        raise ContractError("missing_source_ref", f"{name} must not be empty")
    return sorted(rows, key=source_key)


def active_source_refs(
    values: Any, name: str = "active_source_refs", *, required: bool = True
) -> list[dict[str, str]]:
    """Reject competing revisions for one logical source in a current set."""
    rows = source_refs(values, name, required=required)
    identities: set[tuple[str, str, str]] = set()
    for row in rows:
        identity = source_identity(row)
        if identity in identities:
            raise ContractError(
                "conflicting_source_revision",
                f"{name} contains competing revisions for one logical source",
            )
        identities.add(identity)
    return rows


def _feature_snapshot_projection(
    snapshot: dict[str, Any],
) -> tuple[list[dict], list[dict]]:
    source_projection = []
    for row in snapshot["sources"]:
        if not isinstance(row, dict):
            raise ContractError("invalid_feature_source", "snapshot source is invalid")
        source_projection.append(
            {
                "id": row.get("id"),
                "ref": row.get("ref"),
                "status": row.get("status"),
                "revision": row.get("revision"),
                "unretrieved": row.get("unretrieved"),
            }
        )
    feature_projection = []
    for row in snapshot["features"]:
        if not isinstance(row, dict):
            raise ContractError("invalid_feature", "snapshot feature is invalid")
        feature_projection.append(
            {
                "id": row.get("id"),
                "kind": row.get("kind"),
                "status": row.get("status"),
                "parent_id": row.get("parent_id"),
                "source_ids": row.get("source_ids"),
                "implementation_refs": row.get("implementation_refs"),
                "spec_refs": row.get("spec_refs"),
                "qa_refs": row.get("qa_refs"),
            }
        )
    return (
        sorted(source_projection, key=lambda row: row["id"] or ""),
        sorted(feature_projection, key=lambda row: row["id"] or ""),
    )


def _metric_ids(value: Any, name: str, prefix: str) -> tuple[list[str], list[str]]:
    if not isinstance(value, dict) or set(value) != {
        "numerator_ids",
        "denominator_ids",
        "rate",
    }:
        raise ContractError(
            "feature_inventory_contract_changed", f"{name} fields changed"
        )
    numerator = string_list(value["numerator_ids"], f"{name}.numerator_ids")
    denominator = string_list(value["denominator_ids"], f"{name}.denominator_ids")
    pattern = re.compile(rf"^{prefix}-[0-9]{{3,}}$")
    if (
        numerator != sorted(numerator)
        or denominator != sorted(denominator)
        or any(not pattern.fullmatch(row) for row in numerator + denominator)
        or not set(numerator).issubset(denominator)
    ):
        raise ContractError(
            "feature_inventory_analysis_mismatch", f"{name} IDs are inconsistent"
        )
    rate = value["rate"]
    expected_rate = len(numerator) / len(denominator) if denominator else None
    if isinstance(rate, bool) or rate != expected_rate:
        raise ContractError(
            "feature_inventory_analysis_mismatch", f"{name} rate is inconsistent"
        )
    return numerator, denominator


def feature_inventory(value: Any) -> dict[str, Any]:
    """Validate B's actual separated snapshot and feature_registry analysis result."""
    if not isinstance(value, dict) or set(value) != {"snapshot", "analysis"}:
        raise ContractError(
            "feature_inventory_contract_changed",
            "feature input must contain separate snapshot and analysis objects",
        )
    snapshot = value["snapshot"]
    analysis = value["analysis"]
    if (
        not isinstance(snapshot, dict)
        or snapshot.get("schema_version") != "feature-inventory-v1"
    ):
        raise ContractError(
            "feature_inventory_schema_invalid", "B snapshot schema is invalid"
        )
    snapshot_required = {
        "project_ref",
        "artifact_ref",
        "artifact_revision",
        "source_revision",
        "sources",
        "expected_source_ids",
        "features",
        "unknown_areas",
    }
    if not snapshot_required.issubset(snapshot):
        raise ContractError(
            "feature_inventory_snapshot_incomplete", "B snapshot fields are missing"
        )
    if not isinstance(snapshot["sources"], list) or not isinstance(
        snapshot["features"], list
    ):
        raise ContractError(
            "feature_inventory_snapshot_incomplete",
            "B source and feature arrays are required",
        )
    if not isinstance(analysis, dict) or set(analysis) != {
        "status",
        "reasons",
        "metrics",
        "handoff",
    }:
        raise ContractError(
            "feature_inventory_contract_changed",
            "feature_registry analysis result fields do not match the published contract",
        )
    status = analysis["status"]
    if not isinstance(status, str) or status not in {"complete", "incomplete"}:
        raise ContractError(
            "feature_inventory_not_current",
            "stale, blocked, and idempotent results lack a current analysis handoff",
        )
    reasons = string_list(
        analysis["reasons"], "analysis.reasons", required=status == "incomplete"
    )
    if reasons != sorted(reasons):
        raise ContractError(
            "feature_inventory_analysis_mismatch", "analysis reasons must be sorted"
        )
    if status == "complete" and reasons:
        raise ContractError(
            "feature_inventory_analysis_mismatch",
            "complete result has unresolved reasons",
        )
    metrics = analysis["metrics"]
    if not isinstance(metrics, dict) or set(metrics) != {
        "change_classification",
        "observed_candidate_mapping",
        "source_boundary_complete",
        "unknown_areas",
        "excluded_candidate_ids",
        "all_product_features_discovered",
    }:
        raise ContractError(
            "feature_inventory_contract_changed", "analysis metrics fields changed"
        )
    changes = snapshot.get("changes")
    candidates = snapshot.get("candidates")
    if not isinstance(changes, list) or not isinstance(candidates, list):
        raise ContractError(
            "feature_inventory_snapshot_incomplete",
            "B change and candidate arrays are required",
        )
    change_rows: dict[str, dict[str, Any]] = {}
    for row in changes:
        if not isinstance(row, dict) or not isinstance(row.get("id"), str):
            raise ContractError(
                "feature_inventory_analysis_mismatch", "B change row is invalid"
            )
        if not re.fullmatch(r"DIF-[0-9]{3,}", row["id"]) or row["id"] in change_rows:
            raise ContractError(
                "feature_inventory_analysis_mismatch", "B change IDs are invalid"
            )
        classification = row.get("classification")
        if (
            not isinstance(classification, str)
            or classification not in B_CHANGE_CLASSES
        ):
            raise ContractError(
                "feature_inventory_analysis_mismatch",
                "B change classification is invalid",
            )
        string_list(row.get("feature_ids"), f"{row['id']}.feature_ids")
        change_rows[row["id"]] = row
    candidate_rows: dict[str, dict[str, Any]] = {}
    for row in candidates:
        if not isinstance(row, dict) or not isinstance(row.get("id"), str):
            raise ContractError(
                "feature_inventory_analysis_mismatch", "B candidate row is invalid"
            )
        if (
            not re.fullmatch(r"CAND-[0-9]{3,}", row["id"])
            or row["id"] in candidate_rows
        ):
            raise ContractError(
                "feature_inventory_analysis_mismatch", "B candidate IDs are invalid"
            )
        candidate_status = row.get("status")
        if (
            not isinstance(candidate_status, str)
            or candidate_status not in B_CANDIDATE_STATUSES
        ):
            raise ContractError(
                "feature_inventory_analysis_mismatch", "B candidate status is invalid"
            )
        candidate_rows[row["id"]] = row
    classified_ids = sorted(
        change_id
        for change_id, row in change_rows.items()
        if row.get("classification") in {"impact", "no_impact", "out_of_scope"}
    )
    mapped_ids = sorted(
        candidate_id
        for candidate_id, row in candidate_rows.items()
        if row.get("status") == "mapped"
    )
    if _metric_ids(
        metrics["change_classification"], "change_classification", "DIF"
    ) != (
        classified_ids,
        sorted(change_rows),
    ):
        raise ContractError(
            "feature_inventory_analysis_mismatch", "change metric differs from snapshot"
        )
    if _metric_ids(
        metrics["observed_candidate_mapping"], "observed_candidate_mapping", "CAND"
    ) != (
        mapped_ids,
        sorted(candidate_rows),
    ):
        raise ContractError(
            "feature_inventory_analysis_mismatch",
            "candidate metric differs from snapshot",
        )
    excluded = string_list(
        metrics["excluded_candidate_ids"], "metrics.excluded_candidate_ids"
    )
    if (
        excluded != sorted(excluded)
        or not set(excluded).issubset(candidate_rows)
        or set(excluded).intersection(mapped_ids)
        or any(
            candidate_rows[candidate_id].get("status") != "excluded"
            for candidate_id in excluded
        )
        or metrics["all_product_features_discovered"] is not None
    ):
        raise ContractError(
            "feature_inventory_analysis_mismatch", "candidate exclusion metrics differ"
        )
    if not isinstance(metrics["source_boundary_complete"], bool):
        raise ContractError(
            "feature_inventory_analysis_mismatch", "source boundary state is invalid"
        )
    if not isinstance(analysis["handoff"], dict) or set(analysis["handoff"]) != {
        "snapshot_sha256",
        "source_inventory",
        "artifact_ref",
        "artifact_revision",
        "source_revision",
        "feature_ids",
        "feature_refs",
        "impacted_feature_ids",
        "approval_required_change_ids",
        "unknown_areas",
        "unclassified_change_ids",
        "expected_source_ids",
    }:
        raise ContractError(
            "feature_inventory_contract_changed", "analysis handoff fields changed"
        )

    project_ref = text(snapshot["project_ref"], "snapshot.project_ref")
    artifact_ref = text(snapshot["artifact_ref"], "snapshot.artifact_ref")
    artifact_revision = text(
        snapshot["artifact_revision"], "snapshot.artifact_revision"
    )
    source_revision = text(snapshot["source_revision"], "snapshot.source_revision")
    snapshot_hash = fingerprint(snapshot)
    handoff = analysis["handoff"]
    if (
        not isinstance(handoff["snapshot_sha256"], str)
        or handoff["snapshot_sha256"] != snapshot_hash
    ):
        raise ContractError(
            "feature_snapshot_hash_mismatch", "B snapshot and handoff hash differ"
        )
    if (
        handoff["artifact_ref"] != artifact_ref
        or handoff["artifact_revision"] != artifact_revision
        or handoff["source_revision"] != source_revision
    ):
        raise ContractError(
            "feature_inventory_revision_mismatch",
            "snapshot and handoff identity differ",
        )

    expected_source_ids = string_list(
        snapshot["expected_source_ids"], "snapshot.expected_source_ids"
    )
    if any(not re.fullmatch(r"SRC-[0-9]{3,}", row) for row in expected_source_ids):
        raise ContractError(
            "feature_inventory_source_ids_invalid", "expected source IDs are invalid"
        )
    unknown_areas = string_list(snapshot["unknown_areas"], "snapshot.unknown_areas")
    if (
        handoff["expected_source_ids"] != expected_source_ids
        or handoff["unknown_areas"] != unknown_areas
        or metrics["unknown_areas"] != unknown_areas
    ):
        raise ContractError(
            "feature_inventory_handoff_mismatch", "source boundary projection differs"
        )

    source_projection, feature_projection = _feature_snapshot_projection(snapshot)
    source_rows: dict[str, dict[str, Any]] = {}
    for index, row in enumerate(source_projection):
        source_id = text(row["id"], f"snapshot.sources[{index}].id")
        if not re.fullmatch(r"SRC-[0-9]{3,}", source_id) or source_id in source_rows:
            raise ContractError(
                "feature_inventory_source_ids_invalid",
                "source IDs are invalid or duplicated",
            )
        text(row["ref"], f"{source_id}.ref")
        if not isinstance(row["status"], str) or row["status"] not in {
            "complete",
            "partial",
            "denied",
            "unavailable",
        }:
            raise ContractError(
                "feature_inventory_source_status_invalid",
                f"{source_id} status is invalid",
            )
        if not isinstance(row["unretrieved"], list) or any(
            not isinstance(entry, str) or not entry.strip()
            for entry in row["unretrieved"]
        ):
            raise ContractError(
                "feature_inventory_source_invalid",
                f"{source_id} unretrieved is invalid",
            )
        if row["revision"] is not None:
            text(row["revision"], f"{source_id}.revision")
        if row["status"] == "complete":
            text(row["revision"], f"{source_id}.revision")
            if row["unretrieved"]:
                raise ContractError(
                    "feature_inventory_source_invalid",
                    f"{source_id} is falsely complete",
                )
        source_rows[source_id] = row
    if handoff["source_inventory"] != source_projection:
        raise ContractError(
            "feature_inventory_handoff_mismatch",
            "source inventory differs from snapshot",
        )

    feature_rows: dict[str, dict[str, Any]] = {}
    for index, row in enumerate(feature_projection):
        feature_id = text(row["id"], f"snapshot.features[{index}].id")
        if not FEATURE_ID.fullmatch(feature_id) or feature_id in feature_rows:
            raise ContractError(
                "feature_inventory_feature_ids_invalid",
                "feature IDs are invalid or duplicated",
            )
        if not isinstance(row["status"], str) or row["status"] not in {
            "planned",
            "implemented",
            "retired",
            "unknown",
        }:
            raise ContractError(
                "feature_inventory_feature_status_invalid",
                f"{feature_id} status is invalid",
            )
        if not isinstance(row["kind"], str) or row["kind"] not in {
            "ui",
            "api",
            "batch",
            "integration",
            "authorization",
            "data",
            "other",
        }:
            raise ContractError(
                "feature_inventory_feature_kind_invalid",
                f"{feature_id} kind is invalid",
            )
        parent_id = row["parent_id"]
        if parent_id is not None and (
            not isinstance(parent_id, str) or not FEATURE_ID.fullmatch(parent_id)
        ):
            raise ContractError(
                "feature_inventory_feature_parent_invalid",
                f"{feature_id} parent is invalid",
            )
        for field in ("source_ids", "implementation_refs", "spec_refs", "qa_refs"):
            values = string_list(row[field], f"{feature_id}.{field}")
            if field == "source_ids" and any(
                source_id not in source_rows for source_id in values
            ):
                raise ContractError(
                    "feature_inventory_feature_source_invalid",
                    f"{feature_id} source is unknown",
                )
        feature_rows[feature_id] = row
    for change_id, row in change_rows.items():
        changed_features = string_list(row["feature_ids"], f"{change_id}.feature_ids")
        if any(feature_id not in feature_rows for feature_id in changed_features):
            raise ContractError(
                "feature_inventory_analysis_mismatch",
                "B change references an unknown feature",
            )
    for candidate_id, row in candidate_rows.items():
        feature_id = row.get("feature_id")
        if row["status"] == "mapped":
            if not isinstance(feature_id, str) or feature_id not in feature_rows:
                raise ContractError(
                    "feature_inventory_analysis_mismatch",
                    f"{candidate_id} maps to an unknown feature",
                )
        elif feature_id is not None:
            raise ContractError(
                "feature_inventory_analysis_mismatch",
                f"{candidate_id} has an unexpected feature mapping",
            )
    for feature_id, row in feature_rows.items():
        if row["parent_id"] is not None and row["parent_id"] not in feature_rows:
            raise ContractError(
                "feature_inventory_feature_parent_invalid",
                f"{feature_id} parent is missing",
            )
    impacted = sorted(
        {
            feature_id
            for row in change_rows.values()
            if row.get("classification") == "impact"
            for feature_id in string_list(row["feature_ids"], "change.feature_ids")
        }
    )
    approval_required = sorted(
        change_id
        for change_id, row in change_rows.items()
        if row.get("classification") in {"no_impact", "out_of_scope"}
    )
    unclassified = sorted(set(change_rows) - set(classified_ids))
    if (
        handoff["impacted_feature_ids"] != impacted
        or handoff["approval_required_change_ids"] != approval_required
        or handoff["unclassified_change_ids"] != unclassified
    ):
        raise ContractError(
            "feature_inventory_handoff_mismatch", "analysis change projections differ"
        )
    feature_ids = sorted(feature_rows)
    if (
        handoff["feature_ids"] != feature_ids
        or handoff["feature_refs"] != feature_projection
    ):
        raise ContractError(
            "feature_inventory_handoff_mismatch",
            "feature projection differs from snapshot",
        )
    if not isinstance(metrics["source_boundary_complete"], bool):
        raise ContractError(
            "feature_inventory_analysis_mismatch", "source boundary is invalid"
        )
    boundary_complete = (
        bool(expected_source_ids)
        and not unknown_areas
        and set(expected_source_ids).issubset(source_rows)
        and all(row["status"] == "complete" for row in source_rows.values())
    )
    if metrics["source_boundary_complete"] != boundary_complete:
        raise ContractError(
            "feature_inventory_analysis_mismatch",
            "source boundary metric contradicts snapshot",
        )
    if status == "complete" and not boundary_complete:
        raise ContractError(
            "feature_inventory_analysis_mismatch",
            "complete result has an incomplete source boundary",
        )

    feature_source = {
        "owner": "feature-analysis",
        "scope": project_ref,
        "artifact_ref": artifact_ref,
        "revision": artifact_revision,
        "content_hash": snapshot_hash,
    }
    context = {
        "analysis_status": status,
        "project_ref": project_ref,
        "artifact_ref": artifact_ref,
        "artifact_revision": artifact_revision,
        "source_revision": source_revision,
        "snapshot_sha256": snapshot_hash,
        "source_inventory": source_projection,
        "expected_source_ids": expected_source_ids,
        "feature_ids": feature_ids,
        "source_boundary_complete": boundary_complete,
        "unknown_areas": unknown_areas,
    }
    return {
        "project_ref": project_ref,
        "artifact_ref": artifact_ref,
        "artifact_revision": artifact_revision,
        "source_revision": source_revision,
        "analysis_status": status,
        "sources": source_rows,
        "expected_source_ids": expected_source_ids,
        "features": feature_rows,
        "feature_ids": feature_ids,
        "unknown_areas": unknown_areas,
        "source_boundary_complete": boundary_complete,
        "analysis_complete": status == "complete",
        "feature_source_ref": feature_source,
        "feature_inventory_context": context,
        "active_feature_ids": sorted(
            feature_id
            for feature_id, row in feature_rows.items()
            if row["status"] != "retired"
        ),
    }


def validate_feature_inventory_context(
    value: Any,
    *,
    scope: str,
    feature_ref_value: dict[str, str],
    feature_population: list[dict[str, str]],
    source_boundary_complete: bool,
) -> dict[str, Any]:
    required = {
        "analysis_status",
        "project_ref",
        "artifact_ref",
        "artifact_revision",
        "source_revision",
        "snapshot_sha256",
        "source_inventory",
        "expected_source_ids",
        "feature_ids",
        "source_boundary_complete",
        "unknown_areas",
    }
    if not isinstance(value, dict) or set(value) != required:
        raise ContractError(
            "feature_inventory_context_invalid",
            "feature inventory context fields are invalid",
        )
    project_ref = text(value["project_ref"], "feature_inventory_context.project_ref")
    artifact_ref = text(value["artifact_ref"], "feature_inventory_context.artifact_ref")
    artifact_revision = text(
        value["artifact_revision"], "feature_inventory_context.artifact_revision"
    )
    text(value["source_revision"], "feature_inventory_context.source_revision")
    snapshot_hash = text(
        value["snapshot_sha256"], "feature_inventory_context.snapshot_sha256"
    )
    if not HEX_SHA256.fullmatch(snapshot_hash):
        raise ContractError(
            "feature_inventory_context_invalid", "snapshot hash is invalid"
        )
    if not isinstance(value["analysis_status"], str) or value[
        "analysis_status"
    ] not in {"complete", "incomplete"}:
        raise ContractError(
            "feature_inventory_context_invalid", "analysis status is invalid"
        )
    if (
        not isinstance(value["source_boundary_complete"], bool)
        or value["source_boundary_complete"] != source_boundary_complete
    ):
        raise ContractError(
            "feature_inventory_context_invalid", "source boundary differs from artifact"
        )
    if value["analysis_status"] == "complete" and not source_boundary_complete:
        raise ContractError(
            "feature_inventory_context_invalid",
            "complete analysis has an incomplete source boundary",
        )
    if project_ref != scope or project_ref != feature_ref_value["scope"]:
        raise ContractError(
            "feature_inventory_context_scope_mismatch",
            "project scope differs from feature ref",
        )
    if (
        artifact_ref != feature_ref_value["artifact_ref"]
        or artifact_revision != feature_ref_value["revision"]
        or snapshot_hash != feature_ref_value["content_hash"]
    ):
        raise ContractError(
            "feature_inventory_context_ref_mismatch",
            "feature reference differs from context",
        )

    expected = string_list(
        value["expected_source_ids"], "feature_inventory_context.expected_source_ids"
    )
    feature_ids = string_list(
        value["feature_ids"], "feature_inventory_context.feature_ids"
    )
    unknown = string_list(
        value["unknown_areas"], "feature_inventory_context.unknown_areas"
    )
    if any(not re.fullmatch(r"SRC-[0-9]{3,}", row) for row in expected):
        raise ContractError(
            "feature_inventory_context_invalid", "expected source IDs are invalid"
        )
    if feature_ids != sorted(feature_ids) or any(
        not FEATURE_ID.fullmatch(row) for row in feature_ids
    ):
        raise ContractError(
            "feature_inventory_context_invalid", "feature IDs are invalid"
        )
    if feature_ids != sorted(row["feature_id"] for row in feature_population):
        raise ContractError(
            "feature_inventory_context_invalid", "feature IDs differ from population"
        )
    sources = value["source_inventory"]
    if not isinstance(sources, list):
        raise ContractError(
            "feature_inventory_context_invalid", "source inventory must be an array"
        )
    source_ids: list[str] = []
    for index, row in enumerate(sources):
        if not isinstance(row, dict) or set(row) != {
            "id",
            "ref",
            "status",
            "revision",
            "unretrieved",
        }:
            raise ContractError(
                "feature_inventory_context_invalid",
                f"source inventory row {index} is invalid",
            )
        source_id = text(row["id"], f"source_inventory[{index}].id")
        if not re.fullmatch(r"SRC-[0-9]{3,}", source_id):
            raise ContractError(
                "feature_inventory_context_invalid", "source ID is invalid"
            )
        text(row["ref"], f"source_inventory[{index}].ref")
        if not isinstance(row["status"], str) or row["status"] not in {
            "complete",
            "partial",
            "denied",
            "unavailable",
        }:
            raise ContractError(
                "feature_inventory_context_invalid", "source status is invalid"
            )
        if row["revision"] is not None:
            text(row["revision"], f"source_inventory[{index}].revision")
        if row["status"] == "complete" and row["revision"] is None:
            raise ContractError(
                "feature_inventory_context_invalid",
                "complete source revision is missing",
            )
        string_list(row["unretrieved"], f"source_inventory[{index}].unretrieved")
        source_ids.append(source_id)
    if source_ids != sorted(set(source_ids)):
        raise ContractError(
            "feature_inventory_context_invalid",
            "source inventory IDs are duplicated or unordered",
        )
    if source_boundary_complete and (
        not expected
        or unknown
        or not set(expected).issubset(source_ids)
        or any(row["status"] != "complete" for row in sources if row["id"] in expected)
    ):
        raise ContractError(
            "feature_inventory_context_invalid",
            "complete source boundary contradicts context",
        )
    return value


def validate_item_artifact(value: Any) -> dict[str, Any]:
    """Canonical read-only test-item validator embedded in both isolated D Skills."""
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
        "items",
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
            "item_artifact_schema", "item artifact fields do not match v1"
        )
    if (
        value["schema_version"] != "test-item-candidates-v1"
        or value["owner"] != "test-item-analysis"
    ):
        raise ContractError(
            "item_artifact_identity", "item artifact owner or schema is invalid"
        )
    scope = text(value["scope"], "item_artifact.scope")
    text(value["artifact_ref"], "item_artifact.artifact_ref")
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
        if not FEATURE_ID.fullmatch(feature_id) or feature_id in population_ids:
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
    if any(ref["scope"] != scope for ref in all_sources):
        raise ContractError(
            "item_source_scope_mismatch", "source refs must use the artifact scope"
        )
    all_source_keys = {source_key(row) for row in all_sources}
    if not {source_key(row) for row in active_sources}.issubset(all_source_keys):
        raise ContractError(
            "active_source_missing", "active source refs must exist in source_refs"
        )
    feature_ref_value = source_ref(
        value["feature_inventory_ref"], "item_artifact.feature_inventory_ref"
    )
    if feature_ref_value["owner"] != "feature-analysis" or source_key(
        feature_ref_value
    ) not in {source_key(row) for row in active_sources}:
        raise ContractError(
            "feature_inventory_ref_invalid",
            "feature inventory ref must be a current source",
        )
    if feature_ref_value["scope"] != scope:
        raise ContractError(
            "feature_inventory_ref_invalid",
            "feature inventory scope differs from item artifact",
        )
    if "feature_inventory_context" in value:
        validate_feature_inventory_context(
            value["feature_inventory_context"],
            scope=scope,
            feature_ref_value=feature_ref_value,
            feature_population=population,
            source_boundary_complete=value["source_boundary_complete"],
        )
    rows = value["items"]
    if not isinstance(rows, list):
        raise ContractError("items_invalid", "items must be an array")
    items: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict) or set(row) != ITEM_FIELDS:
            raise ContractError("item_schema", "item fields do not match v1")
        item_id = text(row["item_id"], "item_id")
        if not ITEM_ID.fullmatch(item_id) or item_id in items:
            raise ContractError(
                "item_id_invalid", f"item ID is invalid or duplicated: {item_id}"
            )
        text(row["name"], f"{item_id}.name")
        text(row["description"], f"{item_id}.description")
        if (
            not isinstance(row["kind"], str)
            or row["kind"] not in ITEM_KINDS
            or not isinstance(row["status"], str)
            or row["status"] not in ITEM_STATUSES
        ):
            raise ContractError(
                "item_type_invalid", f"{item_id} kind or status is invalid"
            )
        parents = string_list(row["parent_item_ids"], f"{item_id}.parent_item_ids")
        if any(not ITEM_ID.fullmatch(parent) for parent in parents):
            raise ContractError(
                "item_parent_invalid", f"{item_id} parent ID is invalid"
            )
        features = string_list(row["feature_refs"], f"{item_id}.feature_refs")
        if any(feature not in population_ids for feature in features):
            raise ContractError(
                "item_feature_unknown", f"{item_id} references an unknown feature"
            )
        evidence = source_refs(row["evidence_refs"], f"{item_id}.evidence_refs")
        if not {source_key(ref) for ref in evidence}.issubset(all_source_keys):
            raise ContractError(
                "item_evidence_unknown", f"{item_id} references an unknown source"
            )
        expected_currentness = _currentness(evidence, active_sources)
        if row["currentness"] != expected_currentness:
            raise ContractError(
                "item_currentness_mismatch",
                f"{item_id} currentness contradicts its evidence",
            )
        items[item_id] = row
    _check_item_cycle(items)
    history_ids = string_list(value["id_history"], "id_history")
    if history_ids != sorted(history_ids) or any(
        not ITEM_ID.fullmatch(row) for row in history_ids
    ):
        raise ContractError(
            "item_history_ids_invalid", "id_history must contain sorted ITEM IDs"
        )
    if not set(items).issubset(history_ids):
        raise ContractError(
            "item_history_missing", "current item IDs must be retained in id_history"
        )
    events = value["history"]
    if not isinstance(events, list):
        raise ContractError("item_history_invalid", "history must be an array")
    seen_events: set[str] = set()
    observed_history_ids: set[str] = set()
    for event in events:
        if not isinstance(event, dict) or set(event) != {
            "event_id",
            "item_id",
            "action",
            "reason",
            "related_item_ids",
            "evidence_refs",
        }:
            raise ContractError("item_history_invalid", "history event is invalid")
        event_id = text(event["event_id"], "history.event_id")
        item_id = text(event["item_id"], "history.item_id")
        if (
            event_id in seen_events
            or not EVENT_ID.fullmatch(event_id)
            or not ITEM_ID.fullmatch(item_id)
        ):
            raise ContractError(
                "item_history_invalid",
                "history event is duplicated or has an invalid ID",
            )
        seen_events.add(event_id)
        observed_history_ids.add(item_id)
        if not isinstance(event["action"], str) or event["action"] not in {
            "created",
            "updated",
            "split",
            "merged",
            "retired",
            "source_changed",
        }:
            raise ContractError("item_history_invalid", "history action is invalid")
        text(event["reason"], "history.reason")
        related = string_list(event["related_item_ids"], "history.related_item_ids")
        if any(not ITEM_ID.fullmatch(ref) for ref in related) or not set(
            related
        ).issubset(history_ids):
            raise ContractError(
                "item_history_invalid", "history related IDs are invalid or unallocated"
            )
        evidence = source_refs(event["evidence_refs"], "history.evidence_refs")
        if not {source_key(ref) for ref in evidence}.issubset(all_source_keys):
            raise ContractError("item_history_invalid", "history source ref is missing")
    validate_history_event_ids(events)
    if set(history_ids) != observed_history_ids:
        raise ContractError(
            "item_history_incomplete",
            "every allocated ID must have a retained history event",
        )
    retired_ids = {event["item_id"] for event in events if event["action"] == "retired"}
    if (
        any(
            row["status"] == "retired" and row["item_id"] not in retired_ids
            for row in rows
        )
        or any(
            item_id not in items
            for item_id in history_ids
            if item_id not in retired_ids
        )
        or any(
            row["item_id"] in retired_ids and row["status"] != "retired" for row in rows
        )
    ):
        raise ContractError(
            "item_retirement_history_mismatch", "retired item state and history differ"
        )
    if value["content_fingerprint"] != fingerprint(
        {key: field for key, field in value.items() if key != "content_fingerprint"}
    ):
        raise ContractError(
            "item_fingerprint_mismatch", "item content fingerprint is invalid"
        )
    return value


def _check_item_cycle(items: dict[str, dict[str, Any]]) -> None:
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


def _currentness(evidence: list[dict[str, str]], active: list[dict[str, str]]) -> str:
    by_identity = {source_identity(ref): ref for ref in active}
    unknown = False
    for ref in evidence:
        current = by_identity.get(source_identity(ref))
        if current is None:
            unknown = True
        elif source_key(current) != source_key(ref):
            return "stale"
    return "unknown" if unknown else "current"


def _claim_text(value: Any, name: str) -> str:
    result = text(value, name)
    if len(result) > 512 or any(
        ord(char) < 32 or ord(char) == 127 or 0xD800 <= ord(char) <= 0xDFFF
        for char in result
    ):
        raise ContractError(
            "operation_claim_field_invalid", f"{name} exceeds A's ref contract"
        )
    return result


def operation_claim_ref(owner: str, scope: str, artifact_ref: str) -> str:
    from urllib.parse import quote

    parts = [
        quote(_claim_text(value, "operation_claim_ref"), safe="")
        for value in (owner, scope, artifact_ref)
    ]
    result = "qa-artifact:/" + "/".join(parts)
    if len(result) > 512:
        raise ContractError(
            "operation_claim_ref_too_long",
            "operation claim ref exceeds A's 512 character limit",
        )
    return result


def operation_claim_details(
    *,
    owner: str,
    scope: str,
    artifact_ref: str,
    source_refs_value: list[dict[str, str]],
    expected_revision: str | None,
    approval_ref: str | None,
    permission_scope: str,
) -> dict[str, Any]:
    if len(source_refs_value) > 256:
        raise ContractError(
            "operation_claim_sources_exceeded",
            "A accepts at most 256 source revisions",
        )
    target_ref = operation_claim_ref(owner, scope, artifact_ref)
    source_revisions = [
        {
            "ref": operation_claim_ref(row["owner"], row["scope"], row["artifact_ref"]),
            "revision": _claim_text(row["revision"], "source_revision"),
        }
        for row in source_refs_value
    ]
    return {
        "owner_skill": _claim_text(owner, "owner_skill"),
        "scope_ref": _claim_text(scope, "scope_ref"),
        "operation_type": _claim_text(
            "owner_artifact_create_or_update", "operation_type"
        ),
        "target_ref": target_ref,
        "source_revisions": sorted(source_revisions, key=lambda row: row["ref"]),
        "artifact_revisions": (
            [{"ref": target_ref, "revision": expected_revision}]
            if expected_revision is not None
            else []
        ),
        "expected_revision": (
            _claim_text(expected_revision, "expected_revision")
            if expected_revision is not None
            else None
        ),
        "approval_ref": (
            _claim_text(approval_ref, "approval_ref")
            if approval_ref is not None
            else None
        ),
        "permission_scope": (
            _claim_text(permission_scope, "permission_scope")
            if permission_scope is not None
            else None
        ),
        "resume_owner": _claim_text(owner, "resume_owner"),
    }


def make_result(
    status: str, *, valid: bool, issues: list[dict[str, Any]], **fields: Any
) -> dict[str, Any]:
    result = {"valid": valid, "status": status, "issues": issues}
    result.update(fields)
    return result
