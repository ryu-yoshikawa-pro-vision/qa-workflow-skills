"""QA requirement packet: stored-artifact verification entry point (JSON stdin, JSON stdout).

The canonical JSON packet is the source of truth; the Markdown tables are rendered from it.
This script checks only the records it is given. It does not authenticate the provider,
the approver, or the source owners: approval and source evidence are caller-supplied
bindings, and their provenance is not established here.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from typing import Any

OWNER = "test-requirements-analysis"
SCHEMA = "test-requirements-analysis-v1"
MAX_INPUT_BYTES = 16 * 1024 * 1024
STORAGE_CONTENT_ENCODING = "canonical-json-utf8"
AUTHENTICITY = "not_established_by_this_validator"
MAX_REVISION = 10**9

HEX_SHA256 = re.compile(r"^[0-9a-f]{64}$")
REQUIREMENT_ID = re.compile(r"^QAR-[0-9]{3}$")
OPEN_ITEM_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
REVISION_TEXT = re.compile(r"^[1-9][0-9]{0,8}$")

ARTIFACT_STATES = {"草案", "承認済み", "要再確認", "blocked", "置換"}
REQUIREMENT_STATES = {
    "提案",
    "確認待ち",
    "合意済み",
    "対象外",
    "要再確認",
    "未解決",
    "置換",
}
REQUIREMENT_CLOSED = {"合意済み", "対象外"}
REQUIREMENT_OPEN = {"提案", "確認待ち", "要再確認", "未解決"}
ACQUISITION = {"取得済", "部分取得", "未取得", "取得不能", "0件確認済み", "不明"}
ACQUIRED_WITH_HASH = {"取得済", "部分取得", "0件確認済み"}
APPROVAL_STATES = {"承認済み", "未承認", "失効", "不要", "未設定", "未取得", "unknown"}
APPROVAL_BLOCK_CODES = {
    "未承認": "approval_not_approved",
    "失効": "approval_expired",
    "未設定": "approval_not_configured",
    "未取得": "approval_not_retrieved",
    "unknown": "approval_unknown",
}
UNRESOLVED_ITEM_STATES = {"未取得", "確認待ち", "未解決", "要再確認", "blocked"}
PLACEHOLDERS = {"", "-", "—", "n/a", "na", "tbd", "todo"}
UNRESOLVED_MARKERS = (
    "unknown",
    "未取得",
    "未設定",
    "未確定",
    "未確認",
    "取得不能",
    "stale",
    "blocked",
    "expired",
    "失効",
)

PACKET_KEYS = frozenset(
    {
        "schema",
        "owner",
        "artifact_ref",
        "revision",
        "scope",
        "status",
        "target_period",
        "purpose",
        "sources",
        "requirements",
        "open_items",
        "approval",
        "downstream",
        "history",
    }
)
PURPOSE_KEYS = frozenset(
    {
        "qa_purpose",
        "quality_goals",
        "in_scope",
        "out_of_scope",
        "success_conditions",
        "basis",
    }
)
SOURCE_KEYS = frozenset(
    {
        "owner",
        "scope",
        "artifact_ref",
        "revision",
        "content_hash",
        "acquisition",
        "unacquired_reason",
    }
)
CURRENT_SOURCE_KEYS = frozenset(
    {"owner", "scope", "artifact_ref", "revision", "content_hash"}
)
REQUIREMENT_KEYS = frozenset(
    {
        "requirement_id",
        "statement",
        "requester",
        "source_ref",
        "source_revision",
        "scope",
        "priority",
        "state",
        "basis",
        "open_item_id",
    }
)
OPEN_ITEM_KEYS = frozenset(
    {
        "item_id",
        "requirement_id",
        "impact_scope",
        "owner",
        "state",
        "resume_condition",
    }
)
APPROVAL_KEYS = frozenset({"state", "not_required_reason", "record"})
RECORD_KEYS = frozenset(
    {
        "scope",
        "artifact_ref",
        "revision",
        "approver",
        "role",
        "evidence_ref",
        "expiry_condition",
    }
)
DOWNSTREAM_KEYS = frozenset(
    {"owner", "artifact_ref", "revision", "scope", "requirement_ids"}
)
HISTORY_KEYS = frozenset(
    {
        "revision",
        "replaces_ref",
        "replaces_revision",
        "change_reason",
        "impact_scope",
        "rechecks",
    }
)


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


def storage_content_sha256(artifact: dict[str, Any]) -> str:
    """SHA-256 of the complete packet as stored (canonical UTF-8 JSON bytes)."""
    return hashlib.sha256(canonical_bytes(artifact)).hexdigest()


def _issue(code: str, message: str, *, blocking: bool = True) -> dict[str, Any]:
    return {"code": code, "message": message, "blocking": blocking}


def _result(status: str, *, valid: bool, issues: list[dict[str, Any]], **fields: Any):
    result: dict[str, Any] = {"valid": valid, "status": status, "issues": issues}
    result.update(fields)
    return result


def _blocking(issues: list[dict[str, Any]]) -> bool:
    return any(row["blocking"] for row in issues)


def _blank(value: Any) -> bool:
    return not isinstance(value, str) or value.strip().casefold() in PLACEHOLDERS


def _marker(value: str) -> bool:
    folded = value.casefold()
    return any(marker in folded for marker in UNRESOLVED_MARKERS)


# ---- shape checks (raise ContractError) -------------------------------------


def _exact_keys(value: Any, keys: frozenset[str], name: str) -> None:
    if not isinstance(value, dict) or set(value) != keys:
        raise ContractError("packet_schema", f"{name} fields do not match v1")


def _text(value: Any, name: str) -> str:
    if (
        not isinstance(value, str)
        or "\x00" in value
        or value.strip().casefold() in PLACEHOLDERS
    ):
        raise ContractError("invalid_field", f"{name} must be a non-empty text")
    return value


def _opt_text(value: Any, name: str) -> None:
    if value is not None and (not isinstance(value, str) or "\x00" in value):
        raise ContractError("invalid_field", f"{name} must be text or null")


def _text_list(value: Any, name: str, *, required: bool) -> None:
    if not isinstance(value, list):
        raise ContractError("invalid_field", f"{name} must be an array")
    items = [_text(row, f"{name}[]") for row in value]
    if len(items) != len(set(items)):
        raise ContractError("duplicate_value", f"{name} contains duplicates")
    if required and not items:
        raise ContractError("missing_value", f"{name} must not be empty")


def _rows(value: Any, name: str, *, required: bool) -> list[Any]:
    if not isinstance(value, list):
        raise ContractError("invalid_field", f"{name} must be an array")
    if required and not value:
        raise ContractError("missing_value", f"{name} must not be empty")
    return value


def _int(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ContractError("invalid_revision", f"{name} must be an integer")
    if not 1 <= value <= MAX_REVISION:
        raise ContractError("invalid_revision", f"{name} is out of range")
    return value


def _revision_any(value: Any, name: str) -> int:
    if isinstance(value, bool):
        raise ContractError("invalid_revision", f"{name} is invalid")
    if isinstance(value, int) and 1 <= value <= MAX_REVISION:
        return value
    if isinstance(value, str) and REVISION_TEXT.fullmatch(value):
        return int(value)
    raise ContractError("invalid_revision", f"{name} is invalid")


def _hash_or_null(value: Any, name: str) -> None:
    if value is not None and (
        not isinstance(value, str) or not HEX_SHA256.fullmatch(value)
    ):
        raise ContractError(
            "invalid_source_hash", f"{name} must be SHA-256 hex or null"
        )


def _shape(packet: Any) -> None:
    _exact_keys(packet, PACKET_KEYS, "packet")
    if packet["schema"] != SCHEMA:
        raise ContractError(
            "packet_schema", "schema must be test-requirements-analysis-v1"
        )
    _text(packet["owner"], "owner")
    _text(packet["artifact_ref"], "artifact_ref")
    _int(packet["revision"], "revision")
    _text(packet["scope"], "scope")
    _text(packet["status"], "status")
    _text(packet["target_period"], "target_period")

    purpose = packet["purpose"]
    _exact_keys(purpose, PURPOSE_KEYS, "purpose")
    _text(purpose["qa_purpose"], "purpose.qa_purpose")
    for key in ("quality_goals", "in_scope", "success_conditions", "basis"):
        _text_list(purpose[key], f"purpose.{key}", required=True)
    _text_list(purpose["out_of_scope"], "purpose.out_of_scope", required=False)

    for index, source in enumerate(_rows(packet["sources"], "sources", required=True)):
        name = f"sources[{index}]"
        _exact_keys(source, SOURCE_KEYS, name)
        for key in ("owner", "scope", "artifact_ref", "revision", "acquisition"):
            _text(source[key], f"{name}.{key}")
        _hash_or_null(source["content_hash"], f"{name}.content_hash")
        _opt_text(source["unacquired_reason"], f"{name}.unacquired_reason")

    for index, req in enumerate(
        _rows(packet["requirements"], "requirements", required=True)
    ):
        name = f"requirements[{index}]"
        _exact_keys(req, REQUIREMENT_KEYS, name)
        for key in (
            "requirement_id",
            "statement",
            "requester",
            "source_ref",
            "source_revision",
            "scope",
            "priority",
            "state",
            "basis",
        ):
            _text(req[key], f"{name}.{key}")
        _opt_text(req["open_item_id"], f"{name}.open_item_id")

    for index, item in enumerate(
        _rows(packet["open_items"], "open_items", required=False)
    ):
        name = f"open_items[{index}]"
        _exact_keys(item, OPEN_ITEM_KEYS, name)
        for key in ("item_id", "requirement_id", "owner", "state", "resume_condition"):
            _text(item[key], f"{name}.{key}")
        _text_list(item["impact_scope"], f"{name}.impact_scope", required=True)

    approval = packet["approval"]
    _exact_keys(approval, APPROVAL_KEYS, "approval")
    _text(approval["state"], "approval.state")
    _opt_text(approval["not_required_reason"], "approval.not_required_reason")
    record = approval["record"]
    if record is not None:
        _exact_keys(record, RECORD_KEYS, "approval.record")
        _text(record["scope"], "approval.record.scope")
        _text(record["artifact_ref"], "approval.record.artifact_ref")
        _int(record["revision"], "approval.record.revision")
        for key in ("approver", "role", "evidence_ref", "expiry_condition"):
            _opt_text(record[key], f"approval.record.{key}")

    for index, row in enumerate(
        _rows(packet["downstream"], "downstream", required=False)
    ):
        name = f"downstream[{index}]"
        _exact_keys(row, DOWNSTREAM_KEYS, name)
        for key in ("owner", "artifact_ref", "revision", "scope"):
            _text(row[key], f"{name}.{key}")
        _text_list(row["requirement_ids"], f"{name}.requirement_ids", required=True)

    for index, row in enumerate(_rows(packet["history"], "history", required=True)):
        name = f"history[{index}]"
        _exact_keys(row, HISTORY_KEYS, name)
        _int(row["revision"], f"{name}.revision")
        _opt_text(row["replaces_ref"], f"{name}.replaces_ref")
        if row["replaces_revision"] is not None:
            _int(row["replaces_revision"], f"{name}.replaces_revision")
        _text(row["change_reason"], f"{name}.change_reason")
        _text_list(row["impact_scope"], f"{name}.impact_scope", required=False)
        _text_list(row["rechecks"], f"{name}.rechecks", required=False)


def _current_refs(raw: Any) -> tuple[list[dict[str, str]] | None, list[dict[str, Any]]]:
    """Parse caller-supplied current source refs. Any unusable input is unknown (fail-closed)."""
    if raw is None:
        return None, [
            _issue(
                "current_source_refs_missing", "current source refs were not supplied"
            )
        ]
    if not isinstance(raw, list) or not raw:
        return None, [
            _issue(
                "current_source_refs_invalid",
                "current source refs must be a non-empty array",
            )
        ]
    rows: list[dict[str, str]] = []
    for row in raw:
        if (
            not isinstance(row, dict)
            or set(row) != CURRENT_SOURCE_KEYS
            or any(
                not isinstance(row[key], str) or not row[key].strip()
                for key in CURRENT_SOURCE_KEYS
            )
            or not HEX_SHA256.fullmatch(row["content_hash"])
        ):
            return None, [
                _issue(
                    "current_source_refs_invalid",
                    "current source ref fields do not match",
                )
            ]
        rows.append({key: row[key] for key in CURRENT_SOURCE_KEYS})
    identities = [(row["owner"], row["scope"], row["artifact_ref"]) for row in rows]
    if len(identities) != len(set(identities)):
        return None, [
            _issue(
                "conflicting_current_source_refs",
                "current source refs contain competing revisions",
            )
        ]
    return rows, []


def _source_states(
    packet: dict[str, Any], current: list[dict[str, str]] | None
) -> dict[str, Any]:
    by_ref = (
        {row["artifact_ref"]: row for row in current} if current is not None else {}
    )
    states: dict[str, str] = {}
    for source in packet["sources"]:
        ref = source["artifact_ref"]
        found = by_ref.get(ref)
        if (
            found is None
            or found["owner"] != source["owner"]
            or found["scope"] != source["scope"]
            or source["acquisition"] != "取得済"
        ):
            states[ref] = "unknown"
        elif (
            found["revision"] != source["revision"]
            or found["content_hash"] != source["content_hash"]
        ):
            states[ref] = "stale"
        else:
            states[ref] = "current"
    stale = sorted(ref for ref, state in states.items() if state == "stale")
    unknown = sorted(ref for ref, state in states.items() if state == "unknown")
    if stale:
        status = "stale"
    elif unknown:
        status = "unknown"
    else:
        status = "current"
    dependent = {"stale", "unknown"}
    impacted = sorted(
        row["requirement_id"]
        for row in packet["requirements"]
        if states.get(row["source_ref"]) in dependent
    )
    unaffected = sorted(
        row["requirement_id"]
        for row in packet["requirements"]
        if states.get(row["source_ref"]) not in dependent
    )
    issues = [_issue("source_stale", f"source changed: {ref}") for ref in stale]
    issues += [
        _issue("source_unknown", f"source not current or not acquired: {ref}")
        for ref in unknown
    ]
    return {
        "status": status,
        "source_states": [
            {"artifact_ref": ref, "currentness": states[ref]} for ref in sorted(states)
        ],
        "stale_source_refs": stale,
        "unknown_source_refs": unknown,
        "impacted_requirement_ids": impacted,
        "unaffected_requirement_ids": unaffected,
        "issues": issues,
    }


def _purpose_marker_issues(packet: dict[str, Any]) -> list[dict[str, Any]]:
    purpose = packet["purpose"]
    values: list[str] = [purpose["qa_purpose"]]
    for key in (
        "quality_goals",
        "in_scope",
        "out_of_scope",
        "success_conditions",
        "basis",
    ):
        values.extend(purpose[key])
    if any(_marker(value) for value in values):
        return [
            _issue(
                "purpose_unresolved_value",
                "purpose fields contain an unresolved value marker",
            )
        ]
    return []


# ---- semantic checks ---------------------------------------------------------


def _packet_issues(packet: dict[str, Any]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []

    def add(code: str, message: str) -> None:
        issues.append(_issue(code, message))

    if packet["owner"] != OWNER:
        add("owner_mismatch", "owner must be test-requirements-analysis")
    if packet["status"] not in ARTIFACT_STATES:
        add("artifact_status_invalid", "artifact status is not a defined state")
    if packet["status"] == "承認済み":
        issues.extend(_purpose_marker_issues(packet))

    source_by_ref: dict[str, dict[str, Any]] = {}
    for source in packet["sources"]:
        ref = source["artifact_ref"]
        if ref in source_by_ref:
            add("duplicate_source_ref", "source artifact_ref must be unique")
        source_by_ref[ref] = source
        if ref == packet["artifact_ref"]:
            add(
                "artifact_ref_reused_as_source",
                "packet artifact_ref must not be a source",
            )
        if source["acquisition"] not in ACQUISITION:
            add("source_acquisition_invalid", "source acquisition state is not defined")
        if (source["content_hash"] is None) == (
            source["acquisition"] in ACQUIRED_WITH_HASH
        ):
            add(
                "source_hash_state_mismatch",
                "content_hash presence does not match acquisition",
            )
        if source["acquisition"] != "取得済" and _blank(source["unacquired_reason"]):
            add("source_unacquired_reason_missing", "unacquired source needs a reason")

    req_by_id: dict[str, dict[str, Any]] = {}
    approval_state = packet["approval"]["state"]
    for req in packet["requirements"]:
        rid = req["requirement_id"]
        if not REQUIREMENT_ID.fullmatch(rid):
            add("requirement_id_invalid", "requirement_id must match QAR-NNN")
        if rid in req_by_id:
            add("duplicate_requirement_id", "requirement_id must be unique")
        req_by_id[rid] = req
        if req["state"] not in REQUIREMENT_STATES:
            add("requirement_state_invalid", "requirement state is not defined")
        if req["scope"] != packet["scope"]:
            add(
                "requirement_scope_mismatch",
                "requirement scope must equal the packet scope",
            )
        source = source_by_ref.get(req["source_ref"])
        if source is None:
            add(
                "requirement_source_missing",
                "requirement source_ref is not in the source inventory",
            )
        elif source["revision"] != req["source_revision"]:
            add(
                "requirement_source_revision_mismatch",
                "requirement source_revision differs from inventory",
            )
        if (req["open_item_id"] is not None) != (req["state"] in REQUIREMENT_OPEN):
            add(
                "requirement_open_item_link_invalid",
                "open_item_id must match the open requirement states",
            )
        if approval_state == "承認済み" and req["state"] not in REQUIREMENT_CLOSED:
            add(
                "approved_with_unresolved_requirement",
                "approved artifact contains an unresolved requirement",
            )

    open_by_req: dict[str, str] = {}
    seen_items: set[str] = set()
    for item in packet["open_items"]:
        item_id = item["item_id"]
        if not OPEN_ITEM_ID.fullmatch(item_id) or item_id in seen_items:
            add("open_item_id_invalid", "open item_id must be a unique identifier")
        seen_items.add(item_id)
        if item["state"] not in UNRESOLVED_ITEM_STATES:
            add("open_item_state_invalid", "open item state is not defined")
        req = req_by_id.get(item["requirement_id"])
        if req is None or req["open_item_id"] != item_id:
            add(
                "open_item_requirement_mismatch",
                "open item does not match its requirement",
            )
            continue
        if item["requirement_id"] in open_by_req:
            add(
                "open_item_duplicate_for_requirement",
                "requirement has more than one open item",
            )
        open_by_req[item["requirement_id"]] = item_id
        if req["scope"] not in item["impact_scope"]:
            add(
                "open_item_scope_excludes_requirement",
                "impact_scope must include the requirement scope",
            )
        if _blank(item["owner"]) or _blank(item["resume_condition"]):
            add(
                "open_item_owner_or_resume_missing",
                "open item needs an owner and a resume condition",
            )
    for req in packet["requirements"]:
        if (
            req["state"] in REQUIREMENT_OPEN
            and open_by_req.get(req["requirement_id"]) != req["open_item_id"]
        ):
            add(
                "open_item_missing",
                "open requirement needs exactly one matching open item",
            )

    approval = packet["approval"]
    state = approval["state"]
    if state not in APPROVAL_STATES:
        add("approval_state_invalid", "approval state is not defined")
    if state == "不要":
        if _blank(approval["not_required_reason"]):
            add(
                "approval_not_required_reason_missing",
                "not_required approval needs a reason",
            )
    elif approval["not_required_reason"] is not None:
        add(
            "approval_not_required_reason_unexpected",
            "reason is only for not_required approval",
        )
    record = approval["record"]
    if state == "承認済み" and record is None:
        add("approval_record_missing", "approved state needs an approval record")
    if record is not None and state not in {"承認済み", "失効"}:
        add(
            "approval_record_unexpected",
            "approval record is only allowed for approved or expired state",
        )
    if record is not None:
        if record["scope"] != packet["scope"]:
            add(
                "approval_scope_mismatch",
                "approval record scope differs from the packet scope",
            )
        if record["artifact_ref"] != packet["artifact_ref"]:
            add(
                "approval_artifact_ref_mismatch",
                "approval record artifact_ref differs from the packet",
            )
        if record["revision"] != packet["revision"]:
            add(
                "approval_revision_mismatch",
                "approval record revision differs from the packet revision",
            )
        if _blank(record["approver"]):
            add("approval_approver_missing", "approval record has no approver")
        if _blank(record["role"]):
            add("approval_role_missing", "approval record has no role")
        if _blank(record["evidence_ref"]):
            add("approval_evidence_ref_missing", "approval record has no evidence_ref")
        if _blank(record["expiry_condition"]):
            add(
                "approval_expiry_condition_missing",
                "approval record has no expiry condition",
            )
    if packet["status"] == "承認済み" and state != "承認済み":
        add(
            "status_approval_mismatch",
            "approved status requires an approved approval state",
        )

    for row in packet["downstream"]:
        if row["owner"] == OWNER:
            add(
                "downstream_owner_is_self", "downstream handoff must name another owner"
            )
        if any(rid not in req_by_id for rid in row["requirement_ids"]):
            add(
                "downstream_requirement_missing",
                "downstream handoff references an unknown requirement",
            )

    revisions = [row["revision"] for row in packet["history"]]
    if revisions != sorted(set(revisions)) or revisions[-1] != packet["revision"]:
        add(
            "history_revision_invalid",
            "history revisions must increase and end at the packet revision",
        )
    return issues


# ---- operations --------------------------------------------------------------


def validate(request: dict[str, Any]) -> dict[str, Any]:
    if set(request) != {"operation", "artifact"}:
        raise ContractError("request_schema", "validate request fields do not match v1")
    packet = request["artifact"]
    _shape(packet)
    issues = _packet_issues(packet)
    blocking = _blocking(issues)
    return _result(
        "blocked" if blocking else "valid",
        valid=not blocking,
        issues=issues,
        artifact_ref=packet["artifact_ref"],
        revision=packet["revision"],
        scope=packet["scope"],
    )


def validate_readback(request: dict[str, Any]) -> dict[str, Any]:
    if set(request) != {
        "operation",
        "candidate_artifact",
        "readback",
        "expected_revision",
    }:
        raise ContractError(
            "request_schema", "validate_readback request fields do not match v1"
        )
    expected_raw = request["expected_revision"]
    if expected_raw is None or (
        isinstance(expected_raw, str) and not expected_raw.strip()
    ):
        raise ContractError(
            "expected_revision_required", "expected_revision must be supplied"
        )
    expected = _revision_any(expected_raw, "expected_revision")
    packet = request["candidate_artifact"]
    _shape(packet)
    issues = _packet_issues(packet)
    readback = request["readback"]
    if not isinstance(readback, dict) or set(readback) != {
        "owner",
        "scope",
        "artifact_ref",
        "revision",
        "content_hash",
    }:
        raise ContractError("readback_schema", "provider readback fields do not match")
    if not isinstance(readback["content_hash"], str) or not HEX_SHA256.fullmatch(
        readback["content_hash"]
    ):
        raise ContractError(
            "readback_hash_invalid", "provider content_hash must be SHA-256 hex"
        )
    readback_revision = _revision_any(readback["revision"], "readback.revision")
    storage_hash = storage_content_sha256(packet)
    if (
        readback["owner"] != OWNER
        or readback["scope"] != packet["scope"]
        or readback["artifact_ref"] != packet["artifact_ref"]
    ):
        issues.append(
            _issue(
                "readback_identity_mismatch",
                "provider readback owner, scope, or artifact_ref differs",
            )
        )
    if readback_revision != packet["revision"]:
        issues.append(
            _issue(
                "readback_revision_mismatch",
                "provider readback revision differs from the packet",
            )
        )
    if expected != packet["revision"]:
        issues.append(
            _issue(
                "expected_revision_mismatch",
                "expected_revision differs from the packet revision",
            )
        )
    if readback["content_hash"] != storage_hash:
        issues.append(
            _issue(
                "readback_hash_mismatch",
                "saved content hash does not match the canonical stored packet",
            )
        )
    blocking = _blocking(issues)
    return _result(
        "blocked" if blocking else "readback_matches",
        valid=not blocking,
        issues=issues,
        artifact_ref=packet["artifact_ref"],
        revision=packet["revision"],
        scope=packet["scope"],
        storage_content_sha256=storage_hash,
        storage_content_encoding=STORAGE_CONTENT_ENCODING,
        provider_authenticity=AUTHENTICITY,
    )


def impact(request: dict[str, Any]) -> dict[str, Any]:
    if not {"operation", "artifact"} <= set(request) or set(request) - {
        "operation",
        "artifact",
        "current_source_refs",
    }:
        raise ContractError("request_schema", "impact request fields do not match v1")
    packet = request["artifact"]
    _shape(packet)
    issues = _packet_issues(packet)
    if _blocking(issues):
        return _result("blocked", valid=False, issues=issues)
    current, current_issues = _current_refs(request.get("current_source_refs"))
    state = _source_states(packet, current)
    return _result(
        state["status"],
        valid=True,
        issues=current_issues + state["issues"],
        artifact_ref=packet["artifact_ref"],
        revision=packet["revision"],
        source_states=state["source_states"],
        stale_source_refs=state["stale_source_refs"],
        unknown_source_refs=state["unknown_source_refs"],
        impacted_requirement_ids=state["impacted_requirement_ids"],
        unaffected_requirement_ids=state["unaffected_requirement_ids"],
    )


def completion_check(request: dict[str, Any]) -> dict[str, Any]:
    if not {"operation", "artifact"} <= set(request) or set(request) - {
        "operation",
        "artifact",
        "current_source_refs",
    }:
        raise ContractError(
            "request_schema", "completion_check request fields do not match v1"
        )
    packet = request["artifact"]
    _shape(packet)
    issues = _packet_issues(packet)
    approval_state = packet["approval"]["state"]
    authenticity = (
        {"approval_authenticity": AUTHENTICITY} if approval_state == "承認済み" else {}
    )
    if _blocking(issues):
        return _result(
            "blocked",
            valid=False,
            complete=False,
            issues=issues,
            artifact_ref=packet["artifact_ref"],
            revision=packet["revision"],
            approval_state=approval_state,
            **authenticity,
        )

    issues = list(issues)
    issues += _purpose_marker_issues(packet)
    if packet["status"] not in {"草案", "承認済み"}:
        issues.append(
            _issue(
                "artifact_status_not_completable",
                "artifact status does not allow completion",
            )
        )
    if approval_state == "承認済み" and packet["status"] != "承認済み":
        issues.append(
            _issue(
                "artifact_status_not_approved",
                "approved approval needs an approved artifact status",
            )
        )
    open_reqs = sorted(
        row["requirement_id"]
        for row in packet["requirements"]
        if row["state"] not in REQUIREMENT_CLOSED
    )
    if open_reqs:
        issues.append(
            _issue(
                "requirement_not_closed",
                f"requirements not closed: {', '.join(open_reqs)}",
            )
        )
    if packet["open_items"]:
        issues.append(_issue("open_items_remaining", "open items remain"))
    if approval_state in APPROVAL_BLOCK_CODES:
        issues.append(
            _issue(
                APPROVAL_BLOCK_CODES[approval_state],
                f"approval state is {approval_state}",
            )
        )
    elif approval_state not in {"承認済み", "不要"}:
        issues.append(_issue("approval_state_invalid", "approval state is not defined"))

    current, current_issues = _current_refs(request.get("current_source_refs"))
    state = _source_states(packet, current)
    issues += current_issues + state["issues"]
    if state["status"] != "current":
        issues.append(
            _issue("source_not_current", f"source currentness is {state['status']}")
        )

    blocking = _blocking(issues)
    return _result(
        "incomplete" if blocking else "complete",
        valid=True,
        complete=not blocking,
        issues=issues,
        artifact_ref=packet["artifact_ref"],
        revision=packet["revision"],
        approval_state=approval_state,
        source_currentness=state["status"],
        **authenticity,
    )


def run(request: Any) -> dict[str, Any]:
    if not isinstance(request, dict):
        raise ContractError("request_invalid", "request must be a JSON object")
    operation = request.get("operation")
    if operation == "validate":
        return validate(request)
    if operation == "validate_readback":
        return validate_readback(request)
    if operation == "impact":
        return impact(request)
    if operation == "completion_check":
        return completion_check(request)
    raise ContractError(
        "operation_invalid",
        "operation must be validate, validate_readback, impact, or completion_check",
    )


def main() -> int:
    try:
        request = strict_loads(sys.stdin.buffer.read(MAX_INPUT_BYTES + 1))
        result = run(request)
    except ContractError as exc:
        result = _result("blocked", valid=False, issues=[_issue(exc.code, exc.message)])
    except Exception:
        result = _result(
            "blocked",
            valid=False,
            issues=[_issue("internal_error", "packet verification failed closed")],
        )
    sys.stdout.buffer.write(canonical_bytes(result) + b"\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
