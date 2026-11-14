"""テストアーキテクチャの保存済みpacketを検証する本番入口。

保存する正本はcanonical JSON packetである。Markdownの表は、このpacketから描画する
表示用の派生物であり、検証の正本ではない。owner verifierは保存本文のexact bytes、
読み戻し、現在のsource、完了条件をこのscriptへ渡して確認する。

承認の認証主体、保存先のrevision、source ownerからの取得手段はこのscriptでは確立しない。
呼出し側が渡した承認証拠・readbackの束縛（artifact ref、scope、content fingerprint、
revision、割当ID）と内部整合だけを検査する。
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
import unicodedata
from typing import Any

SCHEMA = "test-architecture-v1"
OWNER = "test-architecture-design"
STORAGE_CONTENT_ENCODING = "canonical-json-utf8"
NOT_ESTABLISHED = "not_established_by_this_validator"
MAX_INPUT_BYTES = 16 * 1024 * 1024
MAX_ROWS = 500
MAX_TEXT = 2000
MAX_REF = 512
MAX_SCOPE = 200

CONFIRMED_LEVELS = ("コンポーネント", "API", "システム", "受入", "別レベル")
BASES = ("明示指定", "承認済みarchitecture", "test-analysis既定値", "未確定")
DECISION_BY_BASIS = {
    "explicit": "明示指定",
    "approved": "承認済みarchitecture",
    "default": "test-analysis既定値",
}
DISPOSITIONS = ("確定", "未承認案", "blocked", "対象外")
DECIDED_DECISIONS = ("明示指定", "承認済みarchitecture", "test-analysis既定値")
READINESS = ("準備済み", "未確定", "blocked")
AUTOMATION = ("自動", "手動", "混在", "未確定")
ACQUISITIONS = ("取得済", "部分取得", "未取得", "取得不能", "0件確認済み", "不明")
APPROVAL_STATES = ("承認済み", "未承認", "失効", "不要", "unknown")
COVERAGE_STATES = ("割当済み", "未割当", "対象外")
TARGET_KINDS = ("test_item", "quality_attribute", "risk", "requirement", "other")
SOURCE_ROLES = ("qa_requirement", "test_analysis", "formal_design", "other")
DOWNSTREAM_KINDS = ("Risk", "TR", "TCN", "CI", "TC")
OPEN_STATES = ("未解決", "blocked", "解決済み", "対象外")

GENERAL_PLACEHOLDERS = frozenset(
    {
        "",
        "-",
        "—",
        "unknown",
        "n/a",
        "na",
        "tbd",
        "todo",
        "未取得",
        "未設定",
        "未確定",
        "未確認",
        "取得不能",
        "不明",
        "未定",
    }
)
APPROVAL_PLACEHOLDERS = GENERAL_PLACEHOLDERS | frozenset(
    {
        "none",
        "null",
        "nil",
        "tba",
        "dummy",
        "pending",
        "placeholder",
        "未承認",
        "失効",
        "不要",
        "expired",
        "unapproved",
        "not required",
        "not retrieved",
        "承認済み",
        "承認済",
        "approved",
    }
)

ROOT_KEYS = frozenset(
    {
        "schema",
        "owner",
        "artifact_ref",
        "scope",
        "content_fingerprint",
        "sources",
        "requirement_coverage",
        "assignments",
        "level_priority",
        "constraints",
        "open_items",
        "change_impacts",
        "history",
    }
)
SOURCE_KEYS = frozenset(
    {
        "source_id",
        "role",
        "owner",
        "scope",
        "artifact_ref",
        "revision",
        "content_hash",
        "acquisition",
        "approval_state",
        "approval_evidence_ref",
        "local_id",
    }
)
COVERAGE_KEYS = frozenset(
    {"qa_requirement_ref", "coverage", "assignment_ids", "exclusion_reason"}
)
ASSIGNMENT_KEYS = frozenset(
    {
        "assignment_id",
        "target_ref",
        "target_kind",
        "qa_requirement_ref",
        "level",
        "test_type",
        "method",
        "verification_responsibility",
        "environment",
        "data",
        "runner_tool",
        "automation",
        "measurement",
        "selection_basis",
        "basis_source_ids",
        "source_ids",
        "approval_id",
        "disposition",
        "readiness",
        "exclusion_reason",
        "downstream_refs",
    }
)
DOWNSTREAM_KEYS = frozenset({"kind", "ref"})
PRIORITY_KEYS = frozenset(
    {
        "target_ref",
        "explicit_levels",
        "approved_levels",
        "default_levels",
        "levels",
        "decision",
        "conflict_resolution",
    }
)
CONSTRAINT_KEYS = frozenset(
    {
        "constraint_id",
        "target_ref",
        "quality_attribute",
        "assignment_ids",
        "measurement_method",
        "threshold_source_id",
        "environment_data",
        "readiness",
        "remaining_constraint",
    }
)
OPEN_KEYS = frozenset(
    {
        "open_item_id",
        "subject_ref",
        "owner",
        "state",
        "resume_condition",
        "exclusion_reason",
    }
)
IMPACT_KEYS = frozenset(
    {
        "change_ref",
        "revision",
        "impact_scope",
        "reconfirm_refs",
        "retained_refs",
        "resume_owner",
        "reason",
    }
)
HISTORY_KEYS = frozenset(
    {
        "content_fingerprint",
        "replaces",
        "change_reason",
        "impact_scope",
        "reconfirm_refs",
    }
)
CURRENT_REF_KEYS = frozenset(
    {"owner", "scope", "artifact_ref", "revision", "content_hash"}
)
EVIDENCE_KEYS = frozenset(
    {
        "approval_id",
        "artifact_ref",
        "scope",
        "content_fingerprint",
        "revision",
        "assignment_ids",
        "approver",
        "approver_role",
        "evidence_ref",
        "state",
    }
)

SOURCE_ID = re.compile(r"^SRC-[0-9]{3,}$")
ASSIGNMENT_ID = re.compile(r"^ARCH-[0-9]{3,}$")
CONSTRAINT_ID = re.compile(r"^CON-[0-9]{3,}$")
OPEN_ID = re.compile(r"^OPEN-[0-9]{3,}$")
APPROVAL_ID = re.compile(r"^APR-[0-9]{3,}$")
LOCAL_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
QA_REF = re.compile(
    r"^(?P<artifact_ref>[^#\s]+)#(?P<local_id>[A-Za-z0-9][A-Za-z0-9._-]{0,63})"
    r"@(?P<revision>[^@#\s]+)$"
)


class ContractError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def _fail(code: str, message: str) -> None:
    raise ContractError(code, message)


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            _fail("duplicate_json_key", "JSON object key is duplicated")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    _fail("invalid_json_constant", f"non-finite JSON number is not allowed: {value}")


def strict_loads(raw: bytes) -> Any:
    if len(raw) > MAX_INPUT_BYTES:
        _fail("limit_exceeded", "input exceeds 16 MiB")
    try:
        return json.loads(
            raw.decode("utf-8", "strict"),
            object_pairs_hook=_pairs,
            parse_constant=_reject_constant,
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


def storage_content_sha256(artifact: dict[str, Any]) -> str:
    """SHA-256 of the complete packet as stored (canonical UTF-8 JSON bytes)."""
    return hashlib.sha256(canonical_bytes(artifact)).hexdigest()


def _issue(code: str, message: str, subject_id: str | None = None) -> dict[str, Any]:
    issue: dict[str, Any] = {"code": code, "message": message, "blocking": True}
    if subject_id is not None:
        issue["subject_id"] = subject_id
    return issue


def make_result(
    status: str, *, valid: bool, issues: list[dict[str, Any]], **fields: Any
) -> dict[str, Any]:
    result: dict[str, Any] = {"valid": valid, "status": status, "issues": issues}
    result.update(fields)
    return result


# --- field helpers -----------------------------------------------------------


def _exact(value: Any, keys: frozenset[str], name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        _fail("field_invalid", f"{name} must be an object")
    if set(value) != keys:
        _fail("field_schema_invalid", f"{name} fields do not match v1")
    return value


def _text(value: Any, name: str, *, limit: int = MAX_TEXT) -> str:
    if not isinstance(value, str) or not value.strip():
        _fail("field_invalid", f"{name} must be a non-empty string")
    if len(value) > limit:
        _fail("field_too_long", f"{name} exceeds {limit} characters")
    if value != value.strip():
        _fail("field_not_normalized", f"{name} has leading or trailing spaces")
    if any(
        ord(ch) < 32 or ord(ch) == 127 or 0xD800 <= ord(ch) <= 0xDFFF for ch in value
    ):
        _fail("field_invalid", f"{name} contains control characters")
    return value


def _optional_text(value: Any, name: str, *, limit: int = MAX_TEXT) -> str | None:
    return None if value is None else _text(value, name, limit=limit)


def _ref(value: Any, name: str) -> str:
    result = _text(value, name, limit=MAX_REF)
    if "#" in result or re.search(r"\s", result):
        _fail("field_invalid", f"{name} must not contain '#' or whitespace")
    return result


def _revision(value: Any, name: str) -> str:
    result = _text(value, name, limit=MAX_REF)
    if any(ch in result for ch in "#@") or re.search(r"\s", result):
        _fail("field_invalid", f"{name} must not contain '#', '@' or whitespace")
    return result


def _id(value: Any, name: str, pattern: re.Pattern[str]) -> str:
    if not isinstance(value, str) or not pattern.fullmatch(value):
        _fail("id_invalid", f"{name} has an invalid identifier")
    return value


def _enum(value: Any, name: str, allowed: tuple[str, ...]) -> str:
    if not isinstance(value, str) or value not in allowed:
        _fail("enum_invalid", f"{name} is not an allowed value")
    return value


def _hex(value: Any, name: str) -> str:
    if not isinstance(value, str) or not HEX64.fullmatch(value):
        _fail("hash_invalid", f"{name} must be SHA-256 hex")
    return value


def _list(value: Any, name: str, *, min_items: int = 0) -> list[Any]:
    if not isinstance(value, list):
        _fail("field_invalid", f"{name} must be an array")
    if len(value) > MAX_ROWS:
        _fail("limit_exceeded", f"{name} exceeds {MAX_ROWS} rows")
    if len(value) < min_items:
        _fail("field_missing", f"{name} must not be empty")
    return value


def _text_list(value: Any, name: str, *, min_items: int = 0) -> list[str]:
    rows = _list(value, name, min_items=min_items)
    result = [_text(row, f"{name}[]", limit=MAX_REF) for row in rows]
    if len(result) != len(set(result)):
        _fail("duplicate_reference", f"{name} contains duplicates")
    return result


def _placeholder_key(value: str) -> str:
    """placeholder判定用の正規化: NFKC、書式文字（ゼロ幅等）除去、空白圧縮、casefold。"""
    text = unicodedata.normalize("NFKC", value)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Cf")
    return " ".join(text.split()).casefold()


def _is_placeholder(
    value: str, placeholders: frozenset[str] = GENERAL_PLACEHOLDERS
) -> bool:
    return _placeholder_key(value) in {_placeholder_key(item) for item in placeholders}


def _parse_qa_ref(value: str, name: str) -> tuple[str, str, str]:
    match = QA_REF.fullmatch(value) if isinstance(value, str) else None
    if match is None:
        _fail("qa_ref_invalid", f"{name} must be <artifact_ref>#<local_id>@<revision>")
    return match["artifact_ref"], match["local_id"], match["revision"]


def _qa_ref(artifact_ref: str, local_id: str, revision: str) -> str:
    return f"{artifact_ref}#{local_id}@{revision}"


# --- packet validation -------------------------------------------------------


def _body(packet: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in packet.items() if key != "content_fingerprint"}


def _validate_sources(rows: list[Any]) -> dict[str, dict[str, Any]]:
    sources: dict[str, dict[str, Any]] = {}
    identities: set[tuple[str, str, str]] = set()
    for index, raw in enumerate(_list(rows, "sources", min_items=1)):
        row = _exact(raw, SOURCE_KEYS, f"sources[{index}]")
        source_id = _id(row["source_id"], "source_id", SOURCE_ID)
        if source_id in sources:
            _fail("duplicate_id", "source_id is duplicated")
        source = {
            "source_id": source_id,
            "role": _enum(row["role"], "role", SOURCE_ROLES),
            "owner": _text(row["owner"], "owner", limit=MAX_SCOPE),
            "scope": _text(row["scope"], "scope", limit=MAX_SCOPE),
            "artifact_ref": _ref(row["artifact_ref"], "artifact_ref"),
            "revision": _revision(row["revision"], "revision"),
            "content_hash": _hex(row["content_hash"], "content_hash"),
            "acquisition": _enum(row["acquisition"], "acquisition", ACQUISITIONS),
            "approval_state": _enum(
                row["approval_state"], "approval_state", APPROVAL_STATES
            ),
            "approval_evidence_ref": _optional_text(
                row["approval_evidence_ref"], "approval_evidence_ref", limit=MAX_REF
            ),
            "local_id": row["local_id"],
        }
        evidence = source["approval_evidence_ref"]
        if source["approval_state"] == "承認済み" and (
            evidence is None or _is_placeholder(evidence, APPROVAL_PLACEHOLDERS)
        ):
            _fail(
                "approval_evidence_missing",
                "approved source needs a concrete evidence ref",
            )
        if evidence is not None and _is_placeholder(evidence, APPROVAL_PLACEHOLDERS):
            _fail(
                "approval_evidence_placeholder",
                "approval evidence ref is a placeholder",
            )
        if source["role"] == "qa_requirement":
            source["local_id"] = _id(row["local_id"], "local_id", LOCAL_ID)
        elif row["local_id"] is not None:
            _fail(
                "field_invalid", "local_id is allowed only for qa_requirement sources"
            )
        identity = (source["owner"], source["scope"], source["artifact_ref"])
        if identity in identities:
            _fail("conflicting_source_revision", "one logical source has two rows")
        identities.add(identity)
        sources[source_id] = source
    if not any(row["role"] == "qa_requirement" for row in sources.values()):
        _fail("field_missing", "at least one qa_requirement source is required")
    return sources


def _validate_assignments(
    rows: list[Any], sources: dict[str, dict[str, Any]]
) -> dict[str, dict[str, Any]]:
    assignments: dict[str, dict[str, Any]] = {}
    keys: set[tuple[str, str, str, str, str]] = set()
    for index, raw in enumerate(_list(rows, "assignments")):
        row = _exact(raw, ASSIGNMENT_KEYS, f"assignments[{index}]")
        assignment_id = _id(row["assignment_id"], "assignment_id", ASSIGNMENT_ID)
        if assignment_id in assignments:
            _fail("duplicate_id", "assignment_id is duplicated")
        assignment = dict(row)
        assignment["target_ref"] = _text(row["target_ref"], "target_ref", limit=MAX_REF)
        _enum(row["target_kind"], "target_kind", TARGET_KINDS)
        artifact_ref, local_id, revision = _parse_qa_ref(
            _text(row["qa_requirement_ref"], "qa_requirement_ref", limit=MAX_REF),
            "qa_requirement_ref",
        )
        qa_sources = [
            source
            for source in sources.values()
            if source["role"] == "qa_requirement"
            and source["artifact_ref"] == artifact_ref
            and source["local_id"] == local_id
            and source["revision"] == revision
        ]
        if len(qa_sources) != 1:
            _fail("reference_missing", "qa_requirement_ref has no matching source")
        _enum(row["level"], "level", CONFIRMED_LEVELS)
        for field in (
            "test_type",
            "method",
            "verification_responsibility",
            "environment",
            "data",
            "runner_tool",
            "measurement",
        ):
            _text(row[field], field)
        _enum(row["automation"], "automation", AUTOMATION)
        basis = _enum(row["selection_basis"], "selection_basis", BASES)
        basis_ids = _text_list(row["basis_source_ids"], "basis_source_ids")
        source_ids = _text_list(row["source_ids"], "source_ids", min_items=1)
        for source_id in source_ids:
            if source_id not in sources:
                _fail("reference_missing", "source_ids references an unknown source")
        if qa_sources[0]["source_id"] not in source_ids:
            _fail(
                "reference_missing", "source_ids must include the qa_requirement source"
            )
        for source_id in basis_ids:
            if source_id not in source_ids:
                _fail(
                    "reference_missing",
                    "basis_source_ids must be a subset of source_ids",
                )
        if basis == "test-analysis既定値" and not any(
            sources[source_id]["role"] == "test_analysis" for source_id in basis_ids
        ):
            _fail("basis_source_missing", "default basis needs a test_analysis source")
        approval_id = row["approval_id"]
        if approval_id is not None:
            approval_id = _id(approval_id, "approval_id", APPROVAL_ID)
        if basis == "承認済みarchitecture" and approval_id is None:
            _fail("approval_reference_missing", "approved basis needs an approval_id")
        disposition = _enum(row["disposition"], "disposition", DISPOSITIONS)
        if basis == "未確定" and disposition == "確定":
            _fail(
                "undetermined_level_confirmed", "unresolved basis cannot be confirmed"
            )
        _enum(row["readiness"], "readiness", READINESS)
        exclusion = _optional_text(row["exclusion_reason"], "exclusion_reason")
        if (disposition == "対象外") != (exclusion is not None):
            _fail(
                "exclusion_reason_invalid",
                "exclusion_reason is required only for 対象外",
            )
        for index_ref, raw_ref in enumerate(
            _list(row["downstream_refs"], "downstream_refs")
        ):
            ref = _exact(raw_ref, DOWNSTREAM_KEYS, f"downstream_refs[{index_ref}]")
            _enum(ref["kind"], "downstream kind", DOWNSTREAM_KINDS)
            _text(ref["ref"], "downstream ref", limit=MAX_REF)
        key = (
            assignment["target_ref"],
            row["level"],
            row["test_type"],
            row["method"],
            row["verification_responsibility"],
        )
        if key in keys:
            _fail("duplicate_assignment", "same target, level, type and responsibility")
        keys.add(key)
        assignment["approval_id"] = approval_id
        assignment["source_ids"] = source_ids
        assignment["basis_source_ids"] = basis_ids
        assignment["qa_source_id"] = qa_sources[0]["source_id"]
        assignments[assignment_id] = assignment
    return assignments


def _validate_coverage(
    rows: list[Any],
    sources: dict[str, dict[str, Any]],
    assignments: dict[str, dict[str, Any]],
) -> None:
    expected_refs = {
        _qa_ref(source["artifact_ref"], source["local_id"], source["revision"])
        for source in sources.values()
        if source["role"] == "qa_requirement"
    }
    seen: set[str] = set()
    for index, raw in enumerate(_list(rows, "requirement_coverage")):
        row = _exact(raw, COVERAGE_KEYS, f"requirement_coverage[{index}]")
        ref = _text(row["qa_requirement_ref"], "qa_requirement_ref", limit=MAX_REF)
        if ref not in expected_refs or ref in seen:
            _fail(
                "requirement_coverage_mismatch",
                "coverage row does not match one qa source",
            )
        seen.add(ref)
        state = _enum(row["coverage"], "coverage", COVERAGE_STATES)
        listed = set(_text_list(row["assignment_ids"], "assignment_ids"))
        actual = {
            aid for aid, a in assignments.items() if a["qa_requirement_ref"] == ref
        }
        if listed != actual:
            _fail(
                "requirement_coverage_mismatch",
                "coverage assignment_ids differ from assignments",
            )
        if state == "割当済み" and not actual:
            _fail(
                "requirement_coverage_mismatch", "assigned coverage needs assignments"
            )
        if state != "割当済み" and actual:
            _fail(
                "requirement_coverage_mismatch",
                "unassigned coverage cannot reference assignments",
            )
        exclusion = _optional_text(row["exclusion_reason"], "exclusion_reason")
        if (state == "対象外") != (exclusion is not None):
            _fail(
                "exclusion_reason_invalid",
                "exclusion_reason is required only for 対象外",
            )
    if seen != expected_refs:
        _fail(
            "requirement_coverage_missing",
            "every qa_requirement source needs a coverage row",
        )


def _validate_priorities(
    rows: list[Any], assignments: dict[str, dict[str, Any]]
) -> dict[str, dict[str, Any]]:
    priorities: dict[str, dict[str, Any]] = {}
    for index, raw in enumerate(_list(rows, "level_priority")):
        row = _exact(raw, PRIORITY_KEYS, f"level_priority[{index}]")
        target = _text(row["target_ref"], "target_ref", limit=MAX_REF)
        if target in priorities:
            _fail("duplicate_id", "level_priority target is duplicated")
        explicit = _level_set(row["explicit_levels"], "explicit_levels")
        approved = _level_set(row["approved_levels"], "approved_levels")
        default = _level_set(row["default_levels"], "default_levels")
        kept = _level_set(row["levels"], "levels")
        conflict = bool(explicit) and bool(approved) and set(explicit) != set(approved)
        if conflict:
            decision = "未確定"
            expected = set(explicit) | set(approved)
            _text(row["conflict_resolution"], "conflict_resolution")
        else:
            if row["conflict_resolution"] is not None:
                _fail(
                    "conflict_resolution_invalid",
                    "conflict_resolution is only for conflicts",
                )
            if explicit:
                decision, expected = DECISION_BY_BASIS["explicit"], set(explicit)
            elif approved:
                decision, expected = DECISION_BY_BASIS["approved"], set(approved)
            elif default:
                decision, expected = DECISION_BY_BASIS["default"], set(default)
            else:
                decision, expected = "未確定", set()
        if row["decision"] != decision:
            _fail(
                "level_priority_mismatch",
                "decision does not follow explicit > approved > default",
            )
        if set(kept) != expected:
            _fail("level_priority_mismatch", "levels must equal the decided level set")
        group = {a["level"] for a in assignments.values() if a["target_ref"] == target}
        if group != set(kept):
            _fail(
                "level_priority_mismatch",
                "assignment levels differ from the kept levels",
            )
        for assignment in assignments.values():
            if assignment["target_ref"] != target:
                continue
            if conflict:
                if (
                    assignment["selection_basis"] != "未確定"
                    or assignment["disposition"] == "確定"
                ):
                    _fail(
                        "conflict_assignment_confirmed",
                        "conflicting target cannot be confirmed",
                    )
            elif assignment["selection_basis"] != decision:
                _fail(
                    "level_priority_mismatch",
                    "assignment basis differs from the decision",
                )
        priorities[target] = {
            "decision": decision,
            "levels": set(kept),
            "conflict": conflict,
        }
    for assignment in assignments.values():
        if assignment["target_ref"] not in priorities:
            _fail(
                "level_priority_missing",
                "every assignment target needs a level_priority row",
            )
    return priorities


def _level_set(value: Any, name: str) -> list[str]:
    rows = _list(value, name)
    result = [_enum(row, name, CONFIRMED_LEVELS) for row in rows]
    if len(result) != len(set(result)):
        _fail("duplicate_reference", f"{name} contains duplicates")
    return result


def _validate_rest(
    packet: dict[str, Any], sources: dict[str, Any], assignments: dict[str, Any]
) -> None:
    constraints = _list(packet["constraints"], "constraints")
    for index, raw in enumerate(constraints):
        row = _exact(raw, CONSTRAINT_KEYS, f"constraints[{index}]")
        _id(row["constraint_id"], "constraint_id", CONSTRAINT_ID)
        for field in (
            "target_ref",
            "quality_attribute",
            "measurement_method",
            "environment_data",
            "remaining_constraint",
        ):
            _text(
                row[field], field, limit=MAX_REF if field == "target_ref" else MAX_TEXT
            )
        for aid in _text_list(row["assignment_ids"], "assignment_ids", min_items=1):
            if aid not in assignments:
                _fail(
                    "reference_missing", "constraint references an unknown assignment"
                )
        threshold = row["threshold_source_id"]
        if threshold is not None and threshold not in sources:
            _fail(
                "reference_missing", "threshold_source_id references an unknown source"
            )
        _enum(row["readiness"], "readiness", READINESS)
    for index, raw in enumerate(_list(packet["open_items"], "open_items")):
        row = _exact(raw, OPEN_KEYS, f"open_items[{index}]")
        _id(row["open_item_id"], "open_item_id", OPEN_ID)
        _text(row["subject_ref"], "subject_ref", limit=MAX_REF)
        _text(row["owner"], "owner", limit=MAX_SCOPE)
        state = _enum(row["state"], "state", OPEN_STATES)
        _text(row["resume_condition"], "resume_condition")
        exclusion = _optional_text(row["exclusion_reason"], "exclusion_reason")
        if (state == "対象外") != (exclusion is not None):
            _fail(
                "exclusion_reason_invalid",
                "exclusion_reason is required only for 対象外",
            )
    for index, raw in enumerate(_list(packet["change_impacts"], "change_impacts")):
        row = _exact(raw, IMPACT_KEYS, f"change_impacts[{index}]")
        for field in (
            "change_ref",
            "revision",
            "impact_scope",
            "resume_owner",
            "reason",
        ):
            _text(row[field], field, limit=MAX_REF)
        _text_list(row["reconfirm_refs"], "reconfirm_refs")
        _text_list(row["retained_refs"], "retained_refs")
    for index, raw in enumerate(_list(packet["history"], "history")):
        row = _exact(raw, HISTORY_KEYS, f"history[{index}]")
        _hex(row["content_fingerprint"], "content_fingerprint")
        if row["replaces"] is not None:
            _text(row["replaces"], "replaces", limit=MAX_REF)
        _text(row["change_reason"], "change_reason")
        _text(row["impact_scope"], "impact_scope")
        _text_list(row["reconfirm_refs"], "reconfirm_refs")


def validate_packet(value: Any) -> dict[str, Any]:
    packet = _exact(value, ROOT_KEYS, "artifact")
    if packet["schema"] != SCHEMA or packet["owner"] != OWNER:
        _fail("artifact_identity_invalid", "schema or owner does not match v1")
    _ref(packet["artifact_ref"], "artifact_ref")
    _text(packet["scope"], "scope", limit=MAX_SCOPE)
    _hex(packet["content_fingerprint"], "content_fingerprint")
    if fingerprint(_body(packet)) != packet["content_fingerprint"]:
        _fail(
            "content_fingerprint_mismatch",
            "content_fingerprint does not match the packet body",
        )
    sources = _validate_sources(packet["sources"])
    assignments = _validate_assignments(packet["assignments"], sources)
    _validate_coverage(packet["requirement_coverage"], sources, assignments)
    _validate_priorities(packet["level_priority"], assignments)
    _validate_rest(packet, sources, assignments)
    return packet


def _validate_previous_levels(
    artifact: dict[str, Any], previous: dict[str, Any]
) -> None:
    previous_levels: dict[str, set[str]] = {}
    for row in previous["assignments"]:
        previous_levels.setdefault(row["target_ref"], set()).add(row["level"])
    current_levels: dict[str, set[str]] = {}
    for row in artifact["assignments"]:
        current_levels.setdefault(row["target_ref"], set()).add(row["level"])
    for target, levels in previous_levels.items():
        if len(levels) >= 2 and not levels <= current_levels.get(target, set()):
            _fail("level_collapsed", "a multi-level target must keep every level")


# --- operations --------------------------------------------------------------


def validate(request: dict[str, Any]) -> dict[str, Any]:
    _request_keys(request, {"operation", "artifact"}, {"previous_artifact"})
    artifact = validate_packet(request["artifact"])
    if "previous_artifact" in request:
        _validate_previous_levels(
            artifact, validate_packet(request["previous_artifact"])
        )
    return make_result(
        "valid",
        valid=True,
        issues=[],
        content_fingerprint=artifact["content_fingerprint"],
        assignment_ids=sorted(row["assignment_id"] for row in artifact["assignments"]),
    )


def _request_keys(request: Any, required: set[str], optional: set[str]) -> None:
    if not isinstance(request, dict):
        _fail("request_invalid", "request must be a JSON object")
    if not required.issubset(request) or set(request) - required - optional:
        _fail("request_schema", "request fields do not match v1")


def validate_readback(request: dict[str, Any]) -> dict[str, Any]:
    _request_keys(
        request,
        {"operation", "candidate_artifact", "readback", "expected_revision"},
        set(),
    )
    expected_revision = _text(
        request["expected_revision"], "expected_revision", limit=MAX_REF
    )
    artifact = validate_packet(request["candidate_artifact"])
    readback = _exact(
        request["readback"],
        frozenset({"owner", "scope", "artifact_ref", "revision", "content_hash"}),
        "readback",
    )
    normalized = {
        "owner": _text(readback["owner"], "readback.owner", limit=MAX_SCOPE),
        "scope": _text(readback["scope"], "readback.scope", limit=MAX_SCOPE),
        "artifact_ref": _ref(readback["artifact_ref"], "readback.artifact_ref"),
        "revision": _text(readback["revision"], "readback.revision", limit=MAX_REF),
        "content_hash": _hex(readback["content_hash"], "readback.content_hash"),
    }
    if (
        normalized["owner"] != OWNER
        or normalized["scope"] != artifact["scope"]
        or normalized["artifact_ref"] != artifact["artifact_ref"]
    ):
        _fail(
            "readback_identity_mismatch",
            "readback owner, scope or artifact ref does not match",
        )
    storage_hash = storage_content_sha256(artifact)
    issues = []
    if normalized["content_hash"] != storage_hash:
        issues.append(
            _issue(
                "readback_hash_mismatch",
                "saved content hash does not match the canonical packet",
            )
        )
    if normalized["revision"] != expected_revision:
        issues.append(
            _issue(
                "readback_revision_mismatch",
                "provider readback revision differs from expected_revision",
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
        provider_authenticity=NOT_ESTABLISHED,
        provider_cas=NOT_ESTABLISHED,
    )


def _current_refs(value: Any) -> list[dict[str, str]] | None:
    if not isinstance(value, list) or len(value) > MAX_ROWS:
        return None
    rows: list[dict[str, str]] = []
    identities: set[tuple[str, str, str]] = set()
    for raw in value:
        if not isinstance(raw, dict) or set(raw) != CURRENT_REF_KEYS:
            return None
        try:
            row = {
                "owner": _text(raw["owner"], "owner", limit=MAX_SCOPE),
                "scope": _text(raw["scope"], "scope", limit=MAX_SCOPE),
                "artifact_ref": _ref(raw["artifact_ref"], "artifact_ref"),
                "revision": _revision(raw["revision"], "revision"),
                "content_hash": _hex(raw["content_hash"], "content_hash"),
            }
        except ContractError:
            return None
        identity = (row["owner"], row["scope"], row["artifact_ref"])
        if identity in identities:
            return None
        identities.add(identity)
        rows.append(row)
    return rows


def _source_key(row: dict[str, str]) -> tuple[str, ...]:
    return tuple(
        row[field]
        for field in ("owner", "scope", "artifact_ref", "revision", "content_hash")
    )


def impact(request: dict[str, Any]) -> dict[str, Any]:
    _request_keys(request, {"operation", "artifact"}, {"current_source_refs"})
    artifact = validate_packet(request["artifact"])
    available = "current_source_refs" in request
    current = _current_refs(request["current_source_refs"]) if available else None
    usable = current is not None
    by_identity = {
        (r["owner"], r["scope"], r["artifact_ref"]): r for r in (current or [])
    }
    sources = {row["source_id"]: row for row in artifact["sources"]}
    stale: list[str] = []
    unknown: list[str] = []
    unconfirmed_sources: list[str] = []
    for source_id, source in sorted(sources.items()):
        if not usable:
            state = "unknown"
        else:
            found = by_identity.get(
                (source["owner"], source["scope"], source["artifact_ref"])
            )
            if found is None:
                state = "unknown"
            elif _source_key(found) != _source_key(source):
                state = "stale"
            else:
                state = "current"
        if state == "stale":
            stale.append(source_id)
        elif state == "unknown":
            unknown.append(source_id)
        if source["acquisition"] != "取得済" or (
            source["role"] == "qa_requirement"
            and source["approval_state"] != "承認済み"
        ):
            unconfirmed_sources.append(source_id)
    changed = set(stale) | set(unknown)
    unconfirmed_set = set(unconfirmed_sources)
    impacted, unconfirmed, retained = [], [], []
    refs: set[tuple[str, str]] = set()
    for assignment in sorted(
        artifact["assignments"], key=lambda row: row["assignment_id"]
    ):
        aid = assignment["assignment_id"]
        if changed & set(assignment["source_ids"]):
            impacted.append(aid)
        elif unconfirmed_set & set(assignment["source_ids"]):
            unconfirmed.append(aid)
        else:
            retained.append(aid)
            continue
        refs.update((ref["kind"], ref["ref"]) for ref in assignment["downstream_refs"])
    reconfirm = [{"kind": kind, "ref": ref} for kind, ref in sorted(refs)]
    issues = []
    if not usable:
        issues.append(
            _issue(
                "current_source_refs_unavailable",
                "current source refs are missing or invalid",
            )
        )
    if stale:
        issues.append(
            _issue(
                "source_stale",
                "some packet sources changed; only dependent assignments are impacted",
            )
        )
    if unknown:
        issues.append(
            _issue("source_unknown", "some packet sources were not supplied as current")
        )
    if unconfirmed:
        issues.append(
            _issue(
                "upstream_unconfirmed",
                "dependent assignments are not confirmed upstream",
            )
        )
    if not usable:
        status, valid = "unknown", False
    elif stale or unknown or impacted or unconfirmed or unconfirmed_sources:
        status, valid = "incomplete", True
    else:
        status, valid = "current", True
    return make_result(
        status,
        valid=valid,
        issues=issues,
        source_states=[
            {"source_id": sid, "currentness": _state_of(sid, stale, unknown)}
            for sid in sorted(sources)
        ],
        stale_source_ids=stale,
        unknown_source_ids=unknown,
        unconfirmed_source_ids=sorted(unconfirmed_sources),
        impacted_assignment_ids=impacted,
        unconfirmed_assignment_ids=unconfirmed,
        retained_assignment_ids=retained,
        reconfirm_refs=reconfirm,
    )


def _state_of(source_id: str, stale: list[str], unknown: list[str]) -> str:
    if source_id in stale:
        return "stale"
    if source_id in unknown:
        return "unknown"
    return "current"


def _evidence_by_id(value: Any) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for index, raw in enumerate(_list(value, "approval_evidence")):
        row = _exact(raw, EVIDENCE_KEYS, f"approval_evidence[{index}]")
        approval_id = _id(row["approval_id"], "approval_id", APPROVAL_ID)
        for field in (
            "approver",
            "approver_role",
            "evidence_ref",
            "state",
            "artifact_ref",
            "scope",
            "revision",
        ):
            if not isinstance(row[field], str) or len(row[field]) > MAX_TEXT:
                _fail("field_invalid", f"approval evidence {field} must be a string")
        _hex(row["content_fingerprint"], "content_fingerprint")
        _text_list(row["assignment_ids"], "assignment_ids")
        grouped.setdefault(approval_id, []).append(row)
    return grouped


def completion_check(request: dict[str, Any]) -> dict[str, Any]:
    _request_keys(
        request, {"operation", "artifact"}, {"expected_revision", "approval_evidence"}
    )
    artifact = validate_packet(request["artifact"])
    expected_revision = request.get("expected_revision")
    if expected_revision is not None:
        expected_revision = _text(expected_revision, "expected_revision", limit=MAX_REF)
    evidence = _evidence_by_id(request.get("approval_evidence", []))
    sources = {row["source_id"]: row for row in artifact["sources"]}
    reasons: list[dict[str, Any]] = []

    def add(code: str, message: str, subject: str | None = None) -> None:
        reasons.append(_issue(code, message, subject))

    for row in artifact["open_items"]:
        if row["state"] in ("未解決", "blocked"):
            add(
                "open_item_unresolved",
                "an open or blocked item remains",
                row["open_item_id"],
            )
    for row in artifact["level_priority"]:
        if row["decision"] == "未確定":
            add(
                "level_unresolved",
                "a target has conflicting or undecided levels",
                row["target_ref"],
            )
    for row in artifact["requirement_coverage"]:
        if row["coverage"] == "未割当":
            add(
                "requirement_unassigned",
                "a qa requirement has no assignment",
                row["qa_requirement_ref"],
            )
    for row in artifact["constraints"]:
        if row["readiness"] != "準備済み" or row["threshold_source_id"] is None:
            add(
                "constraint_not_ready",
                "a non-functional constraint lacks readiness or threshold",
                row["constraint_id"],
            )

    confirmed, approved, unapproved, blocked = [], [], [], []
    for row in sorted(artifact["assignments"], key=lambda item: item["assignment_id"]):
        aid = row["assignment_id"]
        if row["disposition"] == "未承認案":
            unapproved.append(aid)
            continue
        if row["disposition"] != "確定":
            if row["disposition"] == "blocked":
                blocked.append(aid)
                add("assignment_blocked", "a blocked assignment remains", aid)
            continue
        confirmed.append(aid)
        if row["readiness"] != "準備済み":
            add("readiness_not_ready", "environment, data or runner is not ready", aid)
        if row["automation"] == "未確定":
            add(
                "automation_undetermined",
                "manual or automated execution is undetermined",
                aid,
            )
        for field in (
            "test_type",
            "method",
            "verification_responsibility",
            "environment",
            "data",
            "runner_tool",
            "measurement",
        ):
            if _is_placeholder(row[field]):
                add("placeholder_value", f"{field} is a placeholder", aid)
        for source_id in row["source_ids"]:
            source = sources[source_id]
            if source["acquisition"] != "取得済":
                add("source_not_acquired", "a dependent source is not acquired", aid)
            if (
                source["role"] == "qa_requirement"
                and source["approval_state"] != "承認済み"
            ):
                add(
                    "upstream_not_approved",
                    "the qa requirement source is not approved",
                    aid,
                )
        if row["selection_basis"] == "未確定":
            add("level_unresolved", "the level is not decided", aid)
        default_levels = _default_levels(artifact, row["target_ref"])
        approval_required = row["selection_basis"] == "承認済みarchitecture" or (
            bool(default_levels) and row["level"] not in default_levels
        )
        if not approval_required:
            continue
        before = len(reasons)
        _check_approval(row, artifact, evidence, expected_revision, add)
        if len(reasons) == before:
            approved.append(aid)

    _check_confirmed_coverage(artifact, set(confirmed), add)

    complete = not reasons
    return make_result(
        "complete" if complete else "incomplete",
        valid=True,
        issues=reasons,
        complete=complete,
        confirmed_assignment_ids=confirmed,
        approved_assignment_ids=approved,
        unapproved_assignment_ids=unapproved,
        blocked_assignment_ids=blocked,
        approval_authenticity=NOT_ESTABLISHED,
    )


def _check_confirmed_coverage(
    artifact: dict[str, Any], confirmed: set[str], add: Any
) -> None:
    """完了対象（packetのscopeに属するqa_requirement）ごとに確定割当の裏付けを確認する。

    割当はscopeを持たず、qa_requirement_refで参照するqa_requirement sourceのscopeに属する。
    したがって、要求の充足・決定済みlevelの充足は、現scopeの割当だけで判定する。
    別scopeの確定割当は現scopeの要求やlevelを満たさず、別scopeの未承認案は完了を止めない。
    """
    sources = {row["source_id"]: row for row in artifact["sources"]}
    in_scope = {
        _qa_ref(source["artifact_ref"], source["local_id"], source["revision"])
        for source in sources.values()
        if source["role"] == "qa_requirement" and source["scope"] == artifact["scope"]
    }
    scoped = [
        item
        for item in artifact["assignments"]
        if item["qa_requirement_ref"] in in_scope
    ]
    scoped_confirmed = {
        item["assignment_id"] for item in scoped if item["assignment_id"] in confirmed
    }
    for row in artifact["requirement_coverage"]:
        ref = row["qa_requirement_ref"]
        if ref not in in_scope or row["coverage"] != "割当済み":
            continue
        if not any(
            item["qa_requirement_ref"] == ref
            and item["assignment_id"] in scoped_confirmed
            for item in scoped
        ):
            add(
                "requirement_unconfirmed",
                "an assigned qa requirement has no confirmed assignment",
                ref,
            )
    used_levels = {(item["target_ref"], item["level"]) for item in scoped}
    confirmed_levels = {
        (item["target_ref"], item["level"])
        for item in scoped
        if item["assignment_id"] in scoped_confirmed
    }
    for row in artifact["level_priority"]:
        # 採用が決まったlevel（明示指定・承認済みarchitecture・既定値）のうち、現scopeの割当で使われるものを
        # 確定割当で裏付ける。validatorは割当のlevelが決定集合（levels）と一致することを要求する。
        if row["decision"] not in DECIDED_DECISIONS:
            continue
        for level in row["levels"]:
            key = (row["target_ref"], level)
            if key in used_levels and key not in confirmed_levels:
                add(
                    "level_unconfirmed",
                    f"decided level {level} ({row['decision']}) has no confirmed assignment",
                    row["target_ref"],
                )


def _default_levels(artifact: dict[str, Any], target: str) -> set[str]:
    for row in artifact["level_priority"]:
        if row["target_ref"] == target:
            return set(row["default_levels"])
    return set()


def _check_approval(
    row: dict[str, Any],
    artifact: dict[str, Any],
    evidence: dict[str, list[dict[str, Any]]],
    expected_revision: str | None,
    add: Any,
) -> None:
    aid = row["assignment_id"]
    approval_id = row["approval_id"]
    if approval_id is None or approval_id not in evidence:
        add("approval_missing", "a required approval has no evidence", aid)
        return
    rows = evidence[approval_id]
    if len(rows) != 1:
        add("approval_ambiguous", "approval evidence is duplicated", aid)
        return
    item = rows[0]
    if item["state"] != "承認済み":
        add("approval_not_approved", "approval is not in the approved state", aid)
    if (
        item["artifact_ref"] != artifact["artifact_ref"]
        or item["scope"] != artifact["scope"]
    ):
        add(
            "approval_identity_mismatch",
            "approval belongs to another artifact or scope",
            aid,
        )
    if item["content_fingerprint"] != artifact["content_fingerprint"]:
        add("approval_revision_mismatch", "approval was given for other content", aid)
    if expected_revision is None:
        add(
            "expected_revision_missing",
            "a saved revision is required to bind the approval",
            aid,
        )
    elif item["revision"] != expected_revision:
        add(
            "approval_revision_mismatch",
            "approval was given for another saved revision",
            aid,
        )
    if aid not in item["assignment_ids"]:
        add(
            "approval_assignment_mismatch",
            "approval does not cover this assignment",
            aid,
        )
    if any(
        _is_placeholder(item[field], APPROVAL_PLACEHOLDERS)
        for field in ("approver", "approver_role", "evidence_ref")
    ):
        add(
            "approval_identity_missing",
            "approver, role or evidence ref is missing",
            aid,
        )


def run(request: Any) -> dict[str, Any]:
    if not isinstance(request, dict):
        _fail("request_invalid", "request must be a JSON object")
    operation = request.get("operation")
    handlers = {
        "validate": validate,
        "validate_readback": validate_readback,
        "impact": impact,
        "completion_check": completion_check,
    }
    if operation not in handlers:
        _fail(
            "operation_invalid",
            "operation must be validate, validate_readback, impact or completion_check",
        )
    return handlers[operation](request)


def main() -> int:
    operation = None
    try:
        request = strict_loads(sys.stdin.buffer.read(MAX_INPUT_BYTES + 1))
        if isinstance(request, dict):
            operation = request.get("operation")
        result = run(request)
    except ContractError as exc:
        result = make_result(
            "blocked", valid=False, issues=[_issue(exc.code, exc.message)]
        )
    except Exception:
        result = make_result(
            "blocked",
            valid=False,
            issues=[_issue("internal_error", "architecture validation failed closed")],
        )
    if operation == "completion_check" and "complete" not in result:
        result["complete"] = False
        result["approval_authenticity"] = NOT_ESTABLISHED
    sys.stdout.buffer.write(canonical_bytes(result) + b"\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
