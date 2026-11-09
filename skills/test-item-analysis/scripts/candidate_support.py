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


def strict_loads(raw: bytes) -> Any:
    if len(raw) > MAX_INPUT_BYTES:
        raise ContractError("limit_exceeded", "input exceeds 16 MiB")
    try:
        return json.loads(raw.decode("utf-8", "strict"), object_pairs_hook=_pairs)
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
    except (TypeError, ValueError, UnicodeEncodeError) as exc:
        raise ContractError(
            "invalid_json_value", "value is not canonical JSON"
        ) from exc


def fingerprint(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


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


def feature_inventory(value: Any) -> dict[str, Any]:
    """Read B's published feature-inventory-v1 projection without mutating it."""
    required = {
        "project_ref",
        "artifact_ref",
        "artifact_revision",
        "source_revision",
        "status",
        "sources",
        "expected_source_ids",
        "features",
        "unknown_areas",
        "handoff",
    }
    if not isinstance(value, dict) or not required.issubset(value):
        raise ContractError(
            "invalid_feature_inventory", "feature-inventory-v1 fields are missing"
        )
    project_ref = text(value["project_ref"], "feature_inventory.project_ref")
    artifact_ref = text(value["artifact_ref"], "feature_inventory.artifact_ref")
    artifact_revision = text(
        value["artifact_revision"], "feature_inventory.artifact_revision"
    )
    source_revision = text(
        value["source_revision"], "feature_inventory.source_revision"
    )
    if value.get("schema_version") not in {None, "feature-inventory-v1"}:
        raise ContractError(
            "unsupported_feature_inventory", "unsupported feature inventory schema"
        )
    if value["status"] not in {
        "complete",
        "incomplete",
        "idempotent",
        "stale",
        "blocked",
    }:
        raise ContractError(
            "invalid_feature_inventory", "feature inventory status is invalid"
        )
    if value["status"] in {"stale", "blocked"}:
        raise ContractError(
            "feature_inventory_not_current", "feature inventory is stale or blocked"
        )
    handoff = value["handoff"]
    if not isinstance(handoff, dict) or not HEX_SHA256.fullmatch(
        str(handoff.get("snapshot_sha256", ""))
    ):
        raise ContractError(
            "invalid_feature_inventory", "feature inventory snapshot hash is missing"
        )
    sources = value["sources"]
    expected_source_ids = string_list(
        value["expected_source_ids"], "expected_source_ids"
    )
    unknown_areas = value["unknown_areas"]
    if not isinstance(sources, list) or not isinstance(unknown_areas, list):
        raise ContractError(
            "invalid_feature_inventory", "source inventory fields are invalid"
        )
    source_rows: dict[str, dict[str, Any]] = {}
    for index, row in enumerate(sources):
        if not isinstance(row, dict):
            raise ContractError(
                "invalid_feature_source", f"sources[{index}] is invalid"
            )
        source_id = text(row.get("id"), f"sources[{index}].id")
        if not re.fullmatch(r"SRC-[0-9]{3,}", source_id) or source_id in source_rows:
            raise ContractError(
                "invalid_feature_source",
                f"source ID is invalid or duplicated: {source_id}",
            )
        if row.get("status") not in {"complete", "partial", "denied", "unavailable"}:
            raise ContractError(
                "invalid_feature_source", f"{source_id} status is invalid"
            )
        source_rows[source_id] = row
    features = value["features"]
    if not isinstance(features, list):
        raise ContractError("invalid_feature_inventory", "features must be an array")
    feature_rows: dict[str, dict[str, Any]] = {}
    for index, row in enumerate(features):
        if not isinstance(row, dict):
            raise ContractError("invalid_feature", f"features[{index}] is invalid")
        feature_id = text(row.get("id"), f"features[{index}].id")
        if not FEATURE_ID.fullmatch(feature_id) or feature_id in feature_rows:
            raise ContractError(
                "invalid_feature", f"feature ID is invalid or duplicated: {feature_id}"
            )
        if row.get("status") not in {"planned", "implemented", "retired", "unknown"}:
            raise ContractError("invalid_feature", f"{feature_id} status is invalid")
        feature_rows[feature_id] = row
    missing_sources = set(expected_source_ids) - set(source_rows)
    boundary_complete = (
        value["status"] in {"complete", "idempotent"}
        and bool(expected_source_ids)
        and not missing_sources
        and not unknown_areas
        and all(
            source_rows[source_id]["status"] == "complete"
            for source_id in expected_source_ids
            if source_id in source_rows
        )
    )
    feature_source = {
        "owner": "feature-analysis",
        "scope": project_ref,
        "artifact_ref": artifact_ref,
        "revision": artifact_revision,
        "content_hash": handoff["snapshot_sha256"],
    }
    return {
        "project_ref": project_ref,
        "artifact_ref": artifact_ref,
        "artifact_revision": artifact_revision,
        "source_revision": source_revision,
        "status": value["status"],
        "sources": source_rows,
        "expected_source_ids": sorted(expected_source_ids),
        "features": feature_rows,
        "unknown_areas": unknown_areas,
        "boundary_complete": boundary_complete,
        "feature_source_ref": feature_source,
        "active_feature_ids": sorted(
            feature_id
            for feature_id, row in feature_rows.items()
            if row["status"] != "retired"
        ),
    }


def make_result(
    status: str, *, valid: bool, issues: list[dict[str, Any]], **fields: Any
) -> dict[str, Any]:
    result = {"valid": valid, "status": status, "issues": issues}
    result.update(fields)
    return result
