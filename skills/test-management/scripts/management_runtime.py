"""Saved test-management plan packet: structure, readback, currentness and completion.

The owner-side verifier for a saved plan packet (canonical JSON). It reads one JSON
request from stdin and writes one canonical JSON result to stdout. It never reads or
writes files and never calls the network. It does not decide provider authenticity,
approval authority or source-owner raw results: those stay caller-supplied evidence and
are reported as ``not_established_by_this_validator``.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from typing import Any

SCHEMA = "test-management-plan-v1"
OWNER = "test-management"
STORAGE_CONTENT_ENCODING = "canonical-json-utf8"
NOT_ESTABLISHED = "not_established_by_this_validator"
MAX_INPUT_BYTES = 8 * 1024 * 1024
OUTCOME_NONE = "-"

HEX_SHA256 = re.compile(r"^[0-9a-f]{64}$")
SOURCE_ID = re.compile(r"^SRC-[0-9]{3,}$")
POPULATION_ID = re.compile(r"^POP-[0-9]{3,}$")
PLAN_ID = re.compile(r"^PLAN-[0-9]{3,}$")
CRITERION_ID = re.compile(r"^CRIT-[0-9]{3,}$")
RISK_ID = re.compile(r"^PROJ-RISK-[0-9]{3,}$")
ACTION_ID = re.compile(r"^CA-[0-9]{3,}$")
DIFFERENCE_ID = re.compile(r"^DIFF-[0-9]{3,}$")

# Japanese state labels follow data-contract.md; machine keys are used in counts.
ACQUISITION = {
    "取得済": "acquired",
    "部分取得": "partial",
    "未取得": "not_acquired",
    "取得不能": "unavailable",
    "0件確認済み": "zero_confirmed",
    "不明": "acquisition_unknown",
}
EXECUTION = {
    "実行済み": "executed",
    "実行中": "running",
    "未実行": "not_run",
    "取消": "cancelled",
    "実行失敗": "execution_failed",
    "結果不明": "result_unknown",
    "対象なし": "not_applicable",
}
OUTCOME = {
    "PASS": "pass",
    "FAIL": "fail",
    "判定不能": "undetermined",
    "未判定": "unjudged",
}
CURRENTNESS = frozenset({"current", "stale", "unknown"})
JUDGMENTS = frozenset({"達成", "未達", "未判定", "評価不能"})
CRITERION_KINDS = frozenset({"開始", "終了"})
RISK_STATES = frozenset(
    {"対応中", "blocked", "解決済み", "受容済み", "未判定", "unknown"}
)
ACTION_STATES = frozenset(
    {"対応中", "blocked", "完了", "対応不要", "未判定", "unknown"}
)
APPROVAL_STATES = frozenset({"不要", "承認済み", "未承認", "失効", "unknown"})
PLACEHOLDERS = frozenset(
    value.casefold()
    for value in (
        "",
        "-",
        "—",
        "unknown",
        "不明",
        "未取得",
        "未設定",
        "未確定",
        "未確認",
        "取得不能",
        "未判定",
        "判定不能",
        "失効",
        "未承認",
        "不要",
        "n/a",
        "na",
        "expired",
        "unapproved",
        "not required",
        "not retrieved",
    )
)
COUNT_KEYS = (
    "planned_total",
    "required_total",
    "readback_missing",
    *ACQUISITION.values(),
    *EXECUTION.values(),
    *OUTCOME.values(),
)

PACKET_KEYS = frozenset(
    {
        "schema",
        "owner",
        "artifact_ref",
        "revision",
        "scope",
        "plan_version",
        "target",
        "planned_sources",
        "planned_populations",
        "readbacks",
        "plan_items",
        "criteria",
        "project_risks",
        "corrective_actions",
        "differences",
        "approval",
        "history",
        "monitoring",
    }
)
TARGET_KEYS = frozenset({"build", "environment", "period"})
SOURCE_KEYS = frozenset(
    {"source_id", "owner", "scope", "artifact_ref", "revision", "content_hash"}
)
SOURCE_REF_KEYS = frozenset(
    {"owner", "scope", "artifact_ref", "revision", "content_hash"}
)
POPULATION_KEYS = frozenset(
    {
        "population_id",
        "source_id",
        "query_range",
        "execution_unit",
        "target_build",
        "environment",
        "required",
    }
)
READBACK_KEYS = frozenset(
    {
        "population_id",
        "acquisition_state",
        "execution_state",
        "outcome",
        "currentness",
        "actual",
        "readback_ref",
        "reason",
        "zero_check",
    }
)
ACTUAL_KEYS = frozenset(
    {
        "owner",
        "source_ref",
        "revision",
        "scope",
        "range",
        "execution_unit",
        "build",
        "environment",
    }
)
ZERO_KEYS = frozenset({"query", "checked_at"})
PLAN_ITEM_KEYS = frozenset(
    {
        "plan_id",
        "qa_ref",
        "architecture_ref",
        "level_type",
        "suite_order",
        "owner",
        "effort",
        "resource",
        "source_ids",
    }
)
CRITERION_KEYS = frozenset(
    {"criterion_id", "kind", "criterion", "scope", "evidence_ref", "judgment"}
)
RISK_KEYS = frozenset(
    {
        "risk_id",
        "description",
        "scope",
        "evidence_ref",
        "response",
        "owner",
        "state",
        "state_evidence_ref",
        "approver",
    }
)
DIFFERENCE_KEYS = frozenset(
    {
        "difference_id",
        "scope",
        "difference",
        "evidence_ref",
        "response",
        "owner",
        "state",
        "state_evidence_ref",
        "approver",
    }
)
ACTION_KEYS = frozenset(
    {
        "action_id",
        "finding_ref",
        "scope",
        "action",
        "owner",
        "due",
        "state",
        "result_ref",
        "approver",
    }
)
APPROVAL_KEYS = frozenset({"state", "record"})
APPROVAL_RECORD_KEYS = frozenset(
    {"artifact_ref", "scope", "revision", "approver", "role", "evidence_ref"}
)
HISTORY_KEYS = frozenset({"revision", "replaces_revision", "reason", "scope"})
MONITORING_KEYS = frozenset({"snapshot_ref", "measured_at", "counts"})
MONITORING_COUNT_KEYS = frozenset(COUNT_KEYS)
VALIDATE_READBACK_KEYS = frozenset(
    {"owner", "scope", "artifact_ref", "revision", "content_hash"}
)


class ContractError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def _issue(code: str, message: str, *, blocking: bool = True) -> dict[str, Any]:
    return {"code": code, "message": message, "blocking": blocking}


def make_result(
    status: str, *, valid: bool, issues: list[dict[str, Any]], **fields: Any
) -> dict[str, Any]:
    result: dict[str, Any] = {"valid": valid, "status": status, "issues": issues}
    result.update(fields)
    return result


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ContractError("duplicate_json_key", "JSON object key is duplicated")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise ContractError(
        "invalid_json_constant", f"non-finite JSON number is not allowed: {value}"
    )


def strict_loads(raw: bytes) -> Any:
    if len(raw) > MAX_INPUT_BYTES:
        raise ContractError("limit_exceeded", "input exceeds 8 MiB")
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


def storage_content_sha256(artifact: Any) -> str:
    """SHA-256 of the whole packet as stored: the canonical UTF-8 JSON bytes."""
    return hashlib.sha256(canonical_bytes(artifact)).hexdigest()


# Field helpers. Texts must be trimmed, non-empty and free of NUL.
def _text(value: Any, name: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or "\x00" in value
    ):
        raise ContractError(
            "invalid_field", f"{name} must be a trimmed non-empty string"
        )
    return value


def _ref(value: Any, name: str) -> str:
    text = _text(value, name)
    if text.casefold() in PLACEHOLDERS:
        raise ContractError("placeholder_value", f"{name} must be a concrete value")
    return text


def _optional(value: Any, name: str, check: Any = _ref) -> str | None:
    return None if value is None else check(value, name)


def _enum(value: Any, name: str, allowed: Any) -> str:
    if not isinstance(value, str) or value not in allowed:
        raise ContractError("invalid_state", f"{name} is not an allowed state")
    return value


def _identifier(value: Any, name: str, pattern: re.Pattern[str]) -> str:
    if not isinstance(value, str) or not pattern.fullmatch(value):
        raise ContractError("invalid_identifier", f"{name} has an invalid identifier")
    return value


def _bool(value: Any, name: str) -> bool:
    if not isinstance(value, bool):
        raise ContractError("invalid_field", f"{name} must be a boolean")
    return value


def _count(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ContractError("invalid_field", f"{name} must be a non-negative integer")
    return value


def _mapping(value: Any, name: str, keys: frozenset[str]) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise ContractError("field_set_invalid", f"{name} fields do not match v1")
    return value


def _rows(value: Any, name: str, *, minimum: int = 0) -> list[Any]:
    if not isinstance(value, list) or len(value) < minimum:
        raise ContractError("invalid_list", f"{name} must be an array")
    return value


def _string_list(value: Any, name: str, *, minimum: int = 0) -> list[str]:
    rows = _rows(value, name, minimum=minimum)
    texts = [_text(row, name) for row in rows]
    if len(texts) != len(set(texts)):
        raise ContractError("duplicate_reference", f"{name} contains duplicates")
    return texts


def _unique(seen: set[str], value: str, code: str) -> None:
    if value in seen:
        raise ContractError(code, "identifier is duplicated")
    seen.add(value)


def _parse_sources(value: Any) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    identities: set[tuple[str, str, str]] = set()
    seen: set[str] = set()
    for row in _rows(value, "planned_sources", minimum=0):
        source = _mapping(row, "planned_sources[]", SOURCE_KEYS)
        source_id = _identifier(source["source_id"], "source_id", SOURCE_ID)
        _unique(seen, source_id, "duplicate_source_id")
        for field in ("owner", "scope", "artifact_ref", "revision"):
            _text(source[field], field)
        if not isinstance(source["content_hash"], str) or not HEX_SHA256.fullmatch(
            source["content_hash"]
        ):
            raise ContractError(
                "invalid_source_hash", "content_hash must be SHA-256 hex"
            )
        identity = (source["owner"], source["scope"], source["artifact_ref"])
        if identity in identities:
            raise ContractError(
                "duplicate_source_identity", "one logical source has two planned rows"
            )
        identities.add(identity)
        result[source_id] = source
    return result


def _parse_populations(
    value: Any, sources: dict[str, dict[str, Any]], target: dict[str, str]
) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    seen: set[str] = set()
    for row in _rows(value, "planned_populations"):
        population = _mapping(row, "planned_populations[]", POPULATION_KEYS)
        population_id = _identifier(
            population["population_id"], "population_id", POPULATION_ID
        )
        _unique(seen, population_id, "duplicate_population_id")
        source_id = _identifier(population["source_id"], "source_id", SOURCE_ID)
        if source_id not in sources:
            raise ContractError(
                "population_source_unknown", "population names no planned source"
            )
        for field in ("query_range", "execution_unit", "target_build", "environment"):
            _text(population[field], field)
        if (
            population["target_build"] != target["build"]
            or population["environment"] != target["environment"]
        ):
            raise ContractError(
                "population_target_mismatch",
                "population build or environment differs from target",
            )
        _bool(population["required"], "required")
        result[population_id] = population
    return result


def _check_zero(zero: Any) -> dict[str, Any] | None:
    if zero is None:
        return None
    zero = _mapping(zero, "zero_check", ZERO_KEYS)
    _text(zero["query"], "zero_check.query")
    _text(zero["checked_at"], "zero_check.checked_at")
    return zero


def _check_actual(actual: Any) -> dict[str, Any] | None:
    if actual is None:
        return None
    actual = _mapping(actual, "actual", ACTUAL_KEYS)
    for field in ACTUAL_KEYS:
        _text(actual[field], f"actual.{field}")
    return actual


def _expected_identity(
    population: dict[str, Any], source: dict[str, Any]
) -> dict[str, str]:
    return {
        "owner": source["owner"],
        "source_ref": source["artifact_ref"],
        "revision": source["revision"],
        "scope": source["scope"],
        "range": population["query_range"],
        "execution_unit": population["execution_unit"],
        "build": population["target_build"],
        "environment": population["environment"],
    }


def _check_readback(
    row: dict[str, Any],
    expected: dict[str, str],
    zero: dict[str, Any] | None,
    actual: dict[str, Any] | None,
    readback_ref: str | None,
    reason: str | None,
) -> None:
    acquisition = row["acquisition_state"]
    execution = row["execution_state"]
    outcome = row["outcome"]
    if acquisition in {"未取得", "取得不能", "不明"}:
        if actual is not None or readback_ref is not None or zero is not None:
            raise ContractError(
                "unacquired_identity_present", "unacquired row carries identity"
            )
        if execution not in {"未実行", "結果不明"} or outcome != OUTCOME_NONE:
            raise ContractError(
                "unacquired_state_invalid", "unacquired row has an execution state"
            )
        if row["currentness"] != "unknown":
            raise ContractError(
                "unacquired_state_invalid", "unacquired row must be unknown"
            )
        if reason is None:
            raise ContractError("reason_required", "unacquired row needs a reason")
        return
    if acquisition == "0件確認済み":
        if zero is None or actual is None or readback_ref is None:
            raise ContractError(
                "zero_check_required", "0件確認 needs query, identity and readback"
            )
        if execution != "対象なし" or outcome != OUTCOME_NONE:
            raise ContractError(
                "zero_state_invalid", "0件確認 must be 対象なし without outcome"
            )
        if zero["query"] != expected["range"] or actual != expected:
            raise ContractError(
                "readback_identity_mismatch", "0件確認 identity differs from plan"
            )
        return
    if zero is not None:
        raise ContractError(
            "zero_check_unexpected", "zero_check is only for 0件確認済み"
        )
    if actual is None or readback_ref is None:
        raise ContractError(
            "readback_identity_required", "acquired row needs identity and readback"
        )
    if execution == "対象なし":
        raise ContractError("execution_state_invalid", "対象なし needs 0件確認済み")
    if acquisition == "部分取得":
        if reason is None:
            raise ContractError(
                "reason_required", "partial acquisition needs a missing reason"
            )
        if actual["range"] == expected["range"]:
            raise ContractError(
                "partial_range_not_partial", "partial acquisition covers full range"
            )
        same = {key: value for key, value in actual.items() if key != "range"}
        plan = {key: value for key, value in expected.items() if key != "range"}
        if same != plan:
            raise ContractError(
                "readback_identity_mismatch", "partial identity differs from plan"
            )
    elif actual != expected:
        raise ContractError(
            "readback_identity_mismatch", "acquired identity differs from plan"
        )
    if execution == "実行済み":
        if outcome == OUTCOME_NONE:
            raise ContractError("outcome_required", "実行済み needs a judged outcome")
        if outcome == "判定不能" and reason is None:
            raise ContractError("reason_required", "判定不能 needs a reason")
    elif execution == "実行失敗":
        if outcome != "判定不能" or reason is None:
            raise ContractError(
                "execution_failure_invalid", "実行失敗 needs 判定不能 and a reason"
            )
    elif execution == "結果不明":
        if outcome != OUTCOME_NONE or reason is None:
            raise ContractError(
                "result_unknown_invalid", "結果不明 needs a reason and no outcome"
            )
    elif outcome != OUTCOME_NONE:
        raise ContractError(
            "outcome_state_invalid", "outcome is only allowed after execution"
        )


def _parse_readbacks(
    value: Any,
    populations: dict[str, dict[str, Any]],
    sources: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for item in _rows(value, "readbacks"):
        row = _mapping(item, "readbacks[]", READBACK_KEYS)
        population_id = _identifier(
            row["population_id"], "population_id", POPULATION_ID
        )
        if population_id not in populations:
            raise ContractError(
                "readback_orphan", "readback names no planned population"
            )
        if population_id in result:
            raise ContractError("readback_duplicate", "population has two readbacks")
        _enum(row["acquisition_state"], "acquisition_state", ACQUISITION)
        _enum(row["execution_state"], "execution_state", EXECUTION)
        if row["outcome"] != OUTCOME_NONE:
            _enum(row["outcome"], "outcome", OUTCOME)
        _enum(row["currentness"], "currentness", CURRENTNESS)
        actual = _check_actual(row["actual"])
        readback_ref = _optional(row["readback_ref"], "readback_ref")
        reason = _optional(row["reason"], "reason", _text)
        zero = _check_zero(row["zero_check"])
        population = populations[population_id]
        expected = _expected_identity(population, sources[population["source_id"]])
        _check_readback(row, expected, zero, actual, readback_ref, reason)
        result[population_id] = row
    return result


def _parse_plan_items(
    value: Any, sources: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in _rows(value, "plan_items"):
        row = _mapping(item, "plan_items[]", PLAN_ITEM_KEYS)
        _unique(
            seen, _identifier(row["plan_id"], "plan_id", PLAN_ID), "duplicate_plan_id"
        )
        _ref(row["qa_ref"], "qa_ref")
        _ref(row["architecture_ref"], "architecture_ref")
        for field in ("level_type", "suite_order", "owner", "effort", "resource"):
            _text(row[field], field)
        source_ids = _string_list(row["source_ids"], "source_ids", minimum=1)
        for source_id in source_ids:
            if source_id not in sources:
                raise ContractError(
                    "plan_source_unknown", "plan item names no planned source"
                )
        result.append(row)
    return result


def _parse_criteria(value: Any) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in _rows(value, "criteria"):
        row = _mapping(item, "criteria[]", CRITERION_KEYS)
        _unique(
            seen,
            _identifier(row["criterion_id"], "criterion_id", CRITERION_ID),
            "duplicate_criterion_id",
        )
        _enum(row["kind"], "kind", CRITERION_KINDS)
        _text(row["criterion"], "criterion")
        _text(row["scope"], "scope")
        judgment = _enum(row["judgment"], "judgment", JUDGMENTS)
        evidence = _optional(row["evidence_ref"], "evidence_ref")
        if judgment in {"達成", "未達"} and evidence is None:
            raise ContractError("evidence_required", "judged criterion needs evidence")
        result.append(row)
    return result


def _parse_findings(
    value: Any,
    name: str,
    keys: frozenset[str],
    id_key: str,
    id_pattern: re.Pattern[str],
    text_key: str,
    states: frozenset[str],
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in _rows(value, name):
        row = _mapping(item, f"{name}[]", keys)
        _unique(
            seen, _identifier(row[id_key], id_key, id_pattern), f"duplicate_{id_key}"
        )
        _text(row[text_key], text_key)
        _text(row["scope"], "scope")
        _ref(row["evidence_ref"], "evidence_ref")
        _text(row["response"], "response")
        _text(row["owner"], "owner")
        state = _enum(row["state"], "state", states)
        state_ref = _optional(row["state_evidence_ref"], "state_evidence_ref")
        approver = _optional(row["approver"], "approver")
        if state == "解決済み" and state_ref is None:
            raise ContractError(
                "state_evidence_required", "解決済み needs processing evidence"
            )
        if state == "受容済み" and (state_ref is None or approver is None):
            raise ContractError(
                "judgment_evidence_required", "受容済み needs evidence and approver"
            )
        result.append(row)
    return result


def _parse_actions(value: Any) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in _rows(value, "corrective_actions"):
        row = _mapping(item, "corrective_actions[]", ACTION_KEYS)
        _unique(
            seen,
            _identifier(row["action_id"], "action_id", ACTION_ID),
            "duplicate_action_id",
        )
        _ref(row["finding_ref"], "finding_ref")
        _text(row["scope"], "scope")
        _text(row["action"], "action")
        _text(row["owner"], "owner")
        _text(row["due"], "due")
        state = _enum(row["state"], "state", ACTION_STATES)
        result_ref = _optional(row["result_ref"], "result_ref")
        approver = _optional(row["approver"], "approver")
        if state == "完了" and result_ref is None:
            raise ContractError(
                "result_evidence_required", "完了 needs a result reference"
            )
        if state == "対応不要" and (result_ref is None or approver is None):
            raise ContractError(
                "judgment_evidence_required", "対応不要 needs result and approver"
            )
        result.append(row)
    return result


def _parse_approval(value: Any, packet: dict[str, Any]) -> dict[str, Any]:
    approval = _mapping(value, "approval", APPROVAL_KEYS)
    state = _enum(approval["state"], "approval.state", APPROVAL_STATES)
    record = approval["record"]
    if state == "承認済み":
        rec = _mapping(record, "approval.record", APPROVAL_RECORD_KEYS)
        for field in ("artifact_ref", "scope", "revision"):
            _text(rec[field], f"approval.record.{field}")
        for field in ("approver", "role", "evidence_ref"):
            _ref(rec[field], f"approval.record.{field}")
        if (
            rec["artifact_ref"] != packet["artifact_ref"]
            or rec["scope"] != packet["scope"]
            or rec["revision"] != packet["revision"]
        ):
            raise ContractError(
                "approval_binding_mismatch",
                "approval is not bound to this artifact, scope and revision",
            )
    elif record is not None:
        raise ContractError(
            "approval_record_unexpected", "only 承認済み may carry an approval record"
        )
    return {"state": state, "record": record}


def _parse_history(value: Any, packet: dict[str, Any]) -> None:
    rows = _rows(value, "history", minimum=1)
    previous: str | None = None
    seen: set[str] = set()
    for index, item in enumerate(rows):
        row = _mapping(item, "history[]", HISTORY_KEYS)
        revision = _text(row["revision"], "history.revision")
        _unique(seen, revision, "duplicate_history_revision")
        replaces = _optional(row["replaces_revision"], "replaces_revision", _text)
        _text(row["reason"], "reason")
        if _text(row["scope"], "scope") != packet["scope"]:
            raise ContractError(
                "history_scope_mismatch", "history scope differs from packet scope"
            )
        if replaces != (None if index == 0 else previous):
            raise ContractError(
                "history_chain_broken",
                "history does not chain to the previous revision",
            )
        previous = revision
    if previous != packet["revision"]:
        raise ContractError(
            "history_current_missing", "history does not end at the packet revision"
        )


def _parse_monitoring(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    monitoring = _mapping(value, "monitoring", MONITORING_KEYS)
    _text(monitoring["snapshot_ref"], "snapshot_ref")
    _text(monitoring["measured_at"], "measured_at")
    counts = _mapping(monitoring["counts"], "monitoring.counts", MONITORING_COUNT_KEYS)
    for name in COUNT_KEYS:
        _count(counts[name], f"monitoring.counts.{name}")
    return monitoring


def _parse(packet: Any) -> dict[str, Any]:
    packet = _mapping(packet, "artifact", PACKET_KEYS)
    if packet["schema"] != SCHEMA:
        raise ContractError(
            "schema_invalid", "artifact schema is not test-management-plan-v1"
        )
    if packet["owner"] != OWNER:
        raise ContractError("owner_invalid", "artifact owner is not test-management")
    for field in ("artifact_ref", "revision", "scope", "plan_version"):
        _text(packet[field], field)
    target = _mapping(packet["target"], "target", TARGET_KEYS)
    for field in TARGET_KEYS:
        _text(target[field], f"target.{field}")
    sources = _parse_sources(packet["planned_sources"])
    populations = _parse_populations(packet["planned_populations"], sources, target)
    readbacks = _parse_readbacks(packet["readbacks"], populations, sources)
    plan_items = _parse_plan_items(packet["plan_items"], sources)
    criteria = _parse_criteria(packet["criteria"])
    risks = _parse_findings(
        packet["project_risks"],
        "project_risks",
        RISK_KEYS,
        "risk_id",
        RISK_ID,
        "description",
        RISK_STATES,
    )
    differences = _parse_findings(
        packet["differences"],
        "differences",
        DIFFERENCE_KEYS,
        "difference_id",
        DIFFERENCE_ID,
        "difference",
        RISK_STATES,
    )
    actions = _parse_actions(packet["corrective_actions"])
    approval = _parse_approval(packet["approval"], packet)
    _parse_history(packet["history"], packet)
    monitoring = _parse_monitoring(packet["monitoring"])
    return {
        "packet": packet,
        "sources": sources,
        "populations": populations,
        "readbacks": readbacks,
        "plan_items": plan_items,
        "criteria": criteria,
        "risks": risks,
        "differences": differences,
        "actions": actions,
        "approval": approval,
        "monitoring": monitoring,
    }


def _snapshot(parsed: dict[str, Any]) -> dict[str, int]:
    populations = parsed["populations"]
    readbacks = parsed["readbacks"]
    counts = dict.fromkeys(COUNT_KEYS, 0)
    counts["planned_total"] = len(populations)
    counts["required_total"] = sum(1 for row in populations.values() if row["required"])
    for population_id in populations:
        row = readbacks.get(population_id)
        if row is None:
            counts["readback_missing"] += 1
            continue
        counts[ACQUISITION[row["acquisition_state"]]] += 1
        counts[EXECUTION[row["execution_state"]]] += 1
        if row["outcome"] != OUTCOME_NONE:
            counts[OUTCOME[row["outcome"]]] += 1
    acquired = sum(counts[name] for name in ACQUISITION.values())
    executed = sum(counts[name] for name in EXECUTION.values())
    if (
        acquired + counts["readback_missing"] != counts["planned_total"]
        or executed != acquired
    ):
        raise ContractError(
            "count_invariant_violated", "planned and readback totals do not reconcile"
        )
    return counts


def _consistency_issues(
    parsed: dict[str, Any], counts: dict[str, int]
) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    monitoring = parsed["monitoring"]
    if monitoring is None:
        issues.append(
            _issue(
                "monitoring_missing",
                "declared monitoring snapshot is absent",
                blocking=False,
            )
        )
    else:
        mismatched = sorted(
            name for name in COUNT_KEYS if monitoring["counts"][name] != counts[name]
        )
        if mismatched:
            issues.append(
                _issue(
                    "monitoring_mismatch",
                    "declared counts differ from recomputed counts: "
                    + ", ".join(mismatched),
                )
            )
    missing = sorted(
        pid for pid in parsed["populations"] if pid not in parsed["readbacks"]
    )
    if missing:
        issues.append(
            _issue(
                "readback_missing",
                "planned populations without source owner readback: "
                + ", ".join(missing),
                blocking=False,
            )
        )
    return issues


def _request(request: Any, keys: set[str], operation: str) -> None:
    if (
        not isinstance(request, dict)
        or set(request) != keys
        or request.get("operation") != operation
    ):
        raise ContractError(
            "request_schema", f"{operation} request fields do not match v1"
        )


def validate(request: dict[str, Any]) -> dict[str, Any]:
    _request(request, {"operation", "artifact"}, "validate")
    parsed = _parse(request["artifact"])
    counts = _snapshot(parsed)
    issues = _consistency_issues(parsed, counts)
    valid = not any(issue["blocking"] for issue in issues)
    return make_result(
        "valid" if valid else "invalid", valid=valid, issues=issues, counts=counts
    )


def validate_readback(request: dict[str, Any]) -> dict[str, Any]:
    _request(
        request,
        {"operation", "candidate_artifact", "readback", "expected_revision"},
        "validate_readback",
    )
    packet = request["candidate_artifact"]
    parsed = _parse(packet)
    if request["expected_revision"] is None:
        raise ContractError(
            "expected_revision_required", "expected_revision must be supplied"
        )
    expected_revision = _text(request["expected_revision"], "expected_revision")
    readback = _mapping(request["readback"], "readback", VALIDATE_READBACK_KEYS)
    for field in ("owner", "scope", "artifact_ref", "revision"):
        _text(readback[field], f"readback.{field}")
    if not isinstance(readback["content_hash"], str) or not HEX_SHA256.fullmatch(
        readback["content_hash"]
    ):
        raise ContractError(
            "readback_hash_invalid", "provider content_hash must be SHA-256 hex"
        )
    artifact = parsed["packet"]
    if (
        readback["owner"] != OWNER
        or readback["scope"] != artifact["scope"]
        or readback["artifact_ref"] != artifact["artifact_ref"]
    ):
        raise ContractError(
            "readback_identity_mismatch",
            "provider readback owner, scope, or artifact ref does not match",
        )
    storage_hash = storage_content_sha256(packet)
    issues: list[dict[str, Any]] = []
    if readback["content_hash"] != storage_hash:
        issues.append(
            _issue(
                "readback_hash_mismatch",
                "saved content hash does not match the canonical stored packet",
            )
        )
    if (
        readback["revision"] != artifact["revision"]
        or readback["revision"] != expected_revision
    ):
        issues.append(
            _issue(
                "readback_revision_mismatch",
                "provider readback revision differs from the packet or expected revision",
            )
        )
    matches = not issues
    return make_result(
        "readback_matches" if matches else "blocked",
        valid=matches,
        issues=issues,
        artifact_ref=artifact["artifact_ref"],
        revision=artifact["revision"],
        storage_content_sha256=storage_hash,
        storage_content_encoding=STORAGE_CONTENT_ENCODING,
        readback={field: readback[field] for field in sorted(VALIDATE_READBACK_KEYS)},
        provider_authenticity=NOT_ESTABLISHED,
    )


def _current_sources(value: Any) -> tuple[dict[tuple[str, str, str], Any], bool]:
    """Return current refs by identity; ``True`` when the whole set is unavailable.

    A malformed row makes the whole supplied set unavailable (fail-closed). Competing
    revisions of one logical source map to ``None`` so that source stays unknown.
    """
    if not isinstance(value, list) or not value:
        return {}, True
    result: dict[tuple[str, str, str], Any] = {}
    try:
        for row in value:
            if not isinstance(row, dict) or set(row) != SOURCE_REF_KEYS:
                return {}, True
            for field in ("owner", "scope", "artifact_ref", "revision"):
                _text(row[field], field)
            if not isinstance(row["content_hash"], str) or not HEX_SHA256.fullmatch(
                row["content_hash"]
            ):
                return {}, True
            identity = (row["owner"], row["scope"], row["artifact_ref"])
            current = (row["revision"], row["content_hash"])
            if identity in result and result[identity] != current:
                result[identity] = None
            else:
                result[identity] = current
    except ContractError:
        return {}, True
    return result, False


def impact(request: dict[str, Any]) -> dict[str, Any]:
    _request(request, {"operation", "artifact", "current_source_refs"}, "impact")
    parsed = _parse(request["artifact"])
    current, unavailable = _current_sources(request["current_source_refs"])
    stale: list[str] = []
    unknown: list[str] = []
    for source_id, source in sorted(parsed["sources"].items()):
        if unavailable:
            unknown.append(source_id)
            continue
        identity = (source["owner"], source["scope"], source["artifact_ref"])
        if identity not in current or current[identity] is None:
            unknown.append(source_id)
        elif current[identity] != (source["revision"], source["content_hash"]):
            stale.append(source_id)
    changed = set(stale) | set(unknown)
    impacted_populations = sorted(
        pid for pid, row in parsed["populations"].items() if row["source_id"] in changed
    )
    impacted_plans = sorted(
        row["plan_id"]
        for row in parsed["plan_items"]
        if changed & set(row["source_ids"])
    )
    issues = []
    if stale:
        issues.append(
            _issue(
                "source_stale",
                "changed planned sources need revalidation of their populations",
            )
        )
    if unknown:
        issues.append(
            _issue(
                "source_unknown",
                "planned sources without current evidence are not current",
            )
        )
    return make_result(
        "incomplete" if changed else "current",
        valid=True,
        issues=issues,
        stale_source_ids=stale,
        unknown_source_ids=unknown,
        impacted_population_ids=impacted_populations,
        unaffected_population_ids=sorted(
            set(parsed["populations"]) - set(impacted_populations)
        ),
        impacted_plan_ids=impacted_plans,
        unaffected_plan_ids=sorted(
            row["plan_id"]
            for row in parsed["plan_items"]
            if row["plan_id"] not in impacted_plans
        ),
    )


def build_snapshot(request: dict[str, Any]) -> dict[str, Any]:
    _request(request, {"operation", "artifact"}, "build_snapshot")
    parsed = _parse(request["artifact"])
    counts = _snapshot(parsed)
    monitoring = parsed["monitoring"]
    if monitoring is None:
        matches: bool | None = None
        mismatched: list[str] = []
        snapshot_ref = None
    else:
        mismatched = sorted(
            name for name in COUNT_KEYS if monitoring["counts"][name] != counts[name]
        )
        matches = not mismatched
        snapshot_ref = monitoring["snapshot_ref"]
    return make_result(
        "built",
        valid=True,
        issues=[],
        counts=counts,
        matches_stored=matches,
        mismatched_count_keys=mismatched,
        snapshot_ref=snapshot_ref,
    )


def completion_check(request: dict[str, Any]) -> dict[str, Any]:
    _request(request, {"operation", "artifact"}, "completion_check")
    parsed = _parse(request["artifact"])
    counts = _snapshot(parsed)
    issues = _consistency_issues(parsed, counts)
    approval_state = parsed["approval"]["state"]
    approval_authenticity = NOT_ESTABLISHED if approval_state == "承認済み" else None
    if any(issue["blocking"] for issue in issues):
        return make_result(
            "blocked",
            valid=False,
            issues=issues,
            complete=False,
            counts=counts,
            open={},
            approval_authenticity=approval_authenticity,
        )
    open_items: dict[str, set[str]] = {}

    def hold(code: str, ids: list[str] | tuple[str, ...] = ()) -> None:
        open_items.setdefault(code, set()).update(ids)

    populations = parsed["populations"]
    readbacks = parsed["readbacks"]
    required = [pid for pid, row in populations.items() if row["required"]]
    if not required:
        hold("required_population_missing")
    for population_id in required:
        row = readbacks.get(population_id)
        if row is None:
            hold("readback_missing", [population_id])
            continue
        if row["acquisition_state"] not in {"取得済", "0件確認済み"}:
            hold("acquisition_incomplete", [population_id])
        elif row["currentness"] != "current":
            hold("readback_not_current", [population_id])
        elif row["acquisition_state"] == "取得済" and (
            row["execution_state"] != "実行済み"
            or row["outcome"] not in {"PASS", "FAIL"}
        ):
            hold("execution_unconfirmed", [population_id])
    for criterion in parsed["criteria"]:
        if criterion["judgment"] != "達成":
            hold("criteria_unmet", [criterion["criterion_id"]])
    if not any(row["kind"] == "終了" for row in parsed["criteria"]):
        hold("end_criteria_missing")
    for risk in parsed["risks"]:
        if risk["state"] not in {"解決済み", "受容済み"}:
            hold("project_risk_open", [risk["risk_id"]])
    for difference in parsed["differences"]:
        if difference["state"] not in {"解決済み", "受容済み"}:
            hold("difference_open", [difference["difference_id"]])
    for action in parsed["actions"]:
        if action["state"] not in {"完了", "対応不要"}:
            hold("corrective_action_open", [action["action_id"]])
    if approval_state not in {"不要", "承認済み"}:
        hold("approval_not_effective")
    if parsed["monitoring"] is None:
        hold("monitoring_missing")
    complete = not open_items
    return make_result(
        "complete" if complete else "incomplete",
        valid=True,
        issues=issues,
        complete=complete,
        counts=counts,
        open={code: sorted(ids) for code, ids in sorted(open_items.items())},
        approval_authenticity=approval_authenticity,
    )


OPERATIONS = {
    "validate": validate,
    "validate_readback": validate_readback,
    "impact": impact,
    "build_snapshot": build_snapshot,
    "completion_check": completion_check,
}


def run(request: Any) -> dict[str, Any]:
    if not isinstance(request, dict):
        raise ContractError("request_invalid", "request must be a JSON object")
    operation = request.get("operation")
    if operation not in OPERATIONS:
        raise ContractError(
            "operation_invalid",
            "operation must be validate, validate_readback, impact, build_snapshot, or completion_check",
        )
    return OPERATIONS[operation](request)


def main() -> int:
    try:
        request = strict_loads(sys.stdin.buffer.read(MAX_INPUT_BYTES + 1))
        result = run(request)
    except ContractError as exc:
        result = make_result(
            "blocked", valid=False, issues=[_issue(exc.code, exc.message)]
        )
    except Exception:
        result = make_result(
            "blocked",
            valid=False,
            issues=[_issue("internal_error", "plan packet validation failed closed")],
        )
    sys.stdout.buffer.write(canonical_bytes(result) + b"\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
