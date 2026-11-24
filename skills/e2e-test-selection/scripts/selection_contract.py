"""Validate a technology-neutral E2E selection packet without persistence assumptions."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from decimal import Decimal
from typing import Any

SELECTION_RE = re.compile(r"^E2ESEL-\d{3,}$")
CANDIDATE_RE = re.compile(r"^E2E-CAND-\d{3,}$")
DECISIONS = {"selected", "not_selected", "deferred", "blocked"}
SOURCE_STATES = {"current", "stale", "unknown"}
MAX_INPUT_BYTES = 2 * 1024 * 1024
MAX_OUTPUT_BYTES = 16 * 1024 * 1024
MAX_JSON_DEPTH = 64
MAX_JSON_STRING_BYTES = 64 * 1024
MAX_JSON_NUMBER_CHARS = 4096


class ContractError(ValueError):
    pass


class InputLimitError(ContractError):
    pass


class DuplicateJsonKeyError(ContractError):
    pass


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateJsonKeyError("JSON objectにduplicate keyがあります")
        result[key] = value
    return result


def _reject_non_finite(value: str) -> None:
    raise ContractError(f"非有限JSON number {value} は許可されません")


def _parse_finite_float(value: str) -> Decimal:
    if len(value) > MAX_JSON_NUMBER_CHARS:
        raise InputLimitError("JSON number tokenの上限を超えました")
    mantissa, _, exponent_text = value.lower().partition("e")
    exponent = int(exponent_text) if exponent_text else 0
    unsigned_mantissa = mantissa.lstrip("-")
    integer, _, fraction = unsigned_mantissa.partition(".")
    digits = (integer + fraction).lstrip("0") or "0"
    scale = len(fraction) - exponent
    expanded_chars = (
        len(digits) + (-scale)
        if scale < 0
        else max(len(digits), scale + 1) + (1 if scale else 0)
    )
    if expanded_chars > MAX_JSON_NUMBER_CHARS:
        raise InputLimitError("JSON numberの展開桁数が上限を超えました")
    parsed = Decimal(value)
    if not parsed.is_finite():
        raise ContractError("非有限JSON numberは許可されません")
    return parsed


def _parse_bounded_int(value: str) -> int:
    if len(value) > MAX_JSON_NUMBER_CHARS:
        raise InputLimitError("JSON number tokenの上限を超えました")
    return int(value)


def _check_json_depth(text: str) -> None:
    depth = 0
    in_string = False
    escaped = False
    for char in text:
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char in "[{":
            depth += 1
            if depth > MAX_JSON_DEPTH:
                raise InputLimitError("JSON nesting depthの上限を超えました")
        elif char in "]}":
            depth -= 1
            if depth < 0:
                raise ContractError("JSON containerの構造が不正です")
    if in_string or depth != 0:
        raise ContractError("JSON stringまたはcontainerが閉じていません")


def _check_json_string_limits(text: str) -> None:
    index = 0
    while index < len(text):
        if text[index] != '"':
            index += 1
            continue
        start = index + 1
        end = start
        escaped = False
        while end < len(text):
            char = text[end]
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                break
            end += 1
        token_bytes = len(text[start:end].encode("utf-8", errors="surrogatepass"))
        if token_bytes > MAX_JSON_STRING_BYTES:
            raise InputLimitError("JSON stringのbyte上限を超えました")
        index = end + 1


def _reject_surrogates(value: Any) -> None:
    if isinstance(value, str):
        if any(0xD800 <= ord(char) <= 0xDFFF for char in value):
            raise ContractError("unpaired surrogate code pointは許可されません")
    elif isinstance(value, dict):
        for key, child in value.items():
            _reject_surrogates(key)
            _reject_surrogates(child)
    elif isinstance(value, list):
        for child in value:
            _reject_surrogates(child)


def _load_request(raw: bytes) -> Any:
    if len(raw) > MAX_INPUT_BYTES:
        raise InputLimitError("runtime stdinのbyte上限を超えました")
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise ContractError("stdinはUTF-8である必要があります") from exc
    _check_json_depth(text)
    _check_json_string_limits(text)
    try:
        request = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_keys,
            parse_int=_parse_bounded_int,
            parse_float=_parse_finite_float,
            parse_constant=_reject_non_finite,
        )
    except (json.JSONDecodeError, RecursionError, ValueError) as exc:
        if isinstance(exc, ContractError):
            raise
        raise ContractError("stdinのJSONが不正です") from exc
    _reject_surrogates(request)
    return request


def _error_envelope(status: str, message: str) -> dict[str, str]:
    return {
        "runtime_status": status,
        "result_status": "blocked",
        "error": message,
    }


def _encode_output(output: dict[str, Any]) -> bytes:
    try:
        encoded = (
            json.dumps(output, ensure_ascii=False, sort_keys=True, allow_nan=False)
            + "\n"
        ).encode("utf-8", errors="strict")
    except (TypeError, ValueError, UnicodeError, RecursionError) as exc:
        raise ContractError("runtime outputをJSON化できません") from exc
    if len(encoded) > MAX_OUTPUT_BYTES:
        encoded = (
            json.dumps(
                _error_envelope(
                    "limit_exceeded", "runtime stdoutのbyte上限を超えました"
                ),
                ensure_ascii=False,
                sort_keys=True,
            )
            + "\n"
        ).encode("utf-8")
    return encoded


def _object(
    value: Any, name: str, required: set[str], optional: set[str] = set()
) -> dict:
    if (
        not isinstance(value, dict)
        or required - set(value)
        or set(value) - required - optional
    ):
        raise ContractError(f"{name}のschemaが不正です")
    return value


def _text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ContractError(f"{name}は空でない文字列が必要です")
    return value.strip()


def _retirement_map(value: Any, name: str) -> dict[str, str]:
    if not isinstance(value, list) or not all(isinstance(row, dict) for row in value):
        raise ContractError(f"{name}はobject配列が必要です")
    result: dict[str, str] = {}
    ids = []
    for row in value:
        _object(row, name, {"candidate_id", "reason"})
        candidate_id = _text(row["candidate_id"], f"{name}.candidate_id")
        if not CANDIDATE_RE.fullmatch(candidate_id) or candidate_id in result:
            raise ContractError(f"{name}のcandidate ID形式または一意性が不正です")
        ids.append(candidate_id)
        result[candidate_id] = _text(row["reason"], f"{name}.reason")
    if ids != sorted(ids):
        raise ContractError(f"{name}はcandidate_id順のcanonical配列が必要です")
    return result


def _selection_snapshot(value: Any, name: str) -> dict[str, Any]:
    snapshot = _object(
        value,
        name,
        {
            "scope_refs",
            "automation_goal",
            "population_complete",
            "source_refs",
            "candidates",
            "blockers",
        },
    )
    scope_refs = snapshot["scope_refs"]
    if (
        not isinstance(scope_refs, list)
        or not scope_refs
        or any(not isinstance(ref, str) or not ref for ref in scope_refs)
        or scope_refs != sorted(set(scope_refs))
    ):
        raise ContractError(f"{name}.scope_refsが不正です")
    _text(snapshot["automation_goal"], f"{name}.automation_goal")
    if not isinstance(snapshot["population_complete"], bool):
        raise ContractError(f"{name}.population_completeが不正です")
    if not isinstance(snapshot["blockers"], list) or any(
        not isinstance(item, str) or not item.strip() for item in snapshot["blockers"]
    ):
        raise ContractError(f"{name}.blockersが不正です")
    if not snapshot["population_complete"] and not snapshot["blockers"]:
        raise ContractError("不完全な候補母集団にはblockerまたは再開条件が必要です")

    if not isinstance(snapshot["source_refs"], list) or not snapshot["source_refs"]:
        raise ContractError(f"{name}.source_refsが不正です")
    sources: dict[str, dict[str, str]] = {}
    source_order = []
    for index, raw in enumerate(snapshot["source_refs"]):
        row = _object(
            raw,
            f"{name}.source_refs[{index}]",
            {"ref", "revision", "currentness"},
        )
        ref = _text(row["ref"], f"{name}.source_refs.ref")
        revision = _text(row["revision"], f"{name}.source_refs.revision")
        currentness = row["currentness"]
        if not isinstance(currentness, str) or currentness not in SOURCE_STATES:
            raise ContractError(f"{name}.source_refs.currentnessが不正です")
        if ref in sources:
            raise ContractError(f"{name}.source_refs.refが重複しています")
        source_order.append(ref)
        sources[ref] = {"ref": ref, "revision": revision, "currentness": currentness}
    if source_order != sorted(source_order) or set(scope_refs) - set(sources):
        raise ContractError(f"{name}.source_refsまたはscope_refsが不正です")

    raw_candidates = snapshot["candidates"]
    if not isinstance(raw_candidates, list):
        raise ContractError(f"{name}.candidatesが不正です")
    if not raw_candidates and (
        snapshot["population_complete"] or not snapshot["blockers"]
    ):
        raise ContractError(
            f"{name}で候補0件を記録するには不完全な母集団とblockerが必要です"
        )
    candidate_ids: list[str] = []
    candidate_keys: set[str] = set()
    candidates: list[dict[str, Any]] = []
    for index, raw in enumerate(raw_candidates):
        row = _object(
            raw,
            f"{name}.candidates[{index}]",
            {"candidate_id", "candidate_key", "source_refs", "decision", "rationale"},
        )
        candidate_id = _text(row["candidate_id"], "snapshot candidate_id")
        candidate_key = _text(row["candidate_key"], "snapshot candidate_key")
        if (
            not CANDIDATE_RE.fullmatch(candidate_id)
            or candidate_id in candidate_ids
            or candidate_key in candidate_keys
        ):
            raise ContractError(f"{name}.candidate identityが不正です")
        candidate_ids.append(candidate_id)
        candidate_keys.add(candidate_key)
        if not isinstance(row["decision"], str) or row["decision"] not in DECISIONS:
            raise ContractError(f"{name}.candidate decisionが不正です")
        _text(row["rationale"], "snapshot candidate rationale")
        refs = row["source_refs"]
        if (
            not isinstance(refs, list)
            or not refs
            or any(not isinstance(ref, str) or not ref for ref in refs)
            or refs != sorted(set(refs))
            or set(refs) - set(sources)
        ):
            raise ContractError(f"{name}.candidate source_refsが不正です")
        candidates.append(
            {
                "candidate_id": candidate_id,
                "candidate_key": candidate_key,
                "source_refs": list(refs),
                "decision": row["decision"],
                "rationale": row["rationale"].strip(),
            }
        )
    if candidate_ids != sorted(candidate_ids):
        raise ContractError(f"{name}.candidatesはcandidate_id順が必要です")
    if set(scope_refs) - set(sources):
        raise ContractError(f"{name}.scope_refsに未知のsourceがあります")
    return {
        "scope_refs": list(scope_refs),
        "automation_goal": snapshot["automation_goal"].strip(),
        "population_complete": snapshot["population_complete"],
        "source_refs": [sources[ref] for ref in sorted(sources)],
        "candidates": candidates,
        "blockers": list(snapshot["blockers"]),
    }


def _revision_digest(
    selection_ref: str,
    revision: int,
    change_reason: str,
    candidate_ids: list[dict[str, str]],
    retired_candidates: list[dict[str, str]],
    snapshot: dict[str, Any],
) -> str:
    payload = {
        "schema_version": "e2e-selection-v1",
        "selection_ref": selection_ref,
        "revision": revision,
        "change_reason": change_reason,
        "candidate_ids": candidate_ids,
        "retired_candidates": retired_candidates,
        "selection_snapshot": snapshot,
    }
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8", errors="strict")
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


def validate(packet: Any) -> dict:
    required = {
        "schema_version",
        "selection_ref",
        "revision",
        "change_reason",
        "scope_refs",
        "automation_goal",
        "population_complete",
        "source_refs",
        "candidates",
        "history",
        "retired_candidates",
        "blockers",
    }
    data = _object(packet, "selection", required)
    if data["schema_version"] != "e2e-selection-v1":
        raise ContractError("schema_versionが未対応です")
    selection_ref = _text(data["selection_ref"], "selection_ref")
    if not SELECTION_RE.fullmatch(selection_ref):
        raise ContractError("selection_refの形式が不正です")
    revision = data["revision"]
    if not isinstance(revision, int) or isinstance(revision, bool) or revision < 1:
        raise ContractError("revisionは1以上の整数が必要です")
    if not isinstance(data["population_complete"], bool):
        raise ContractError("population_completeはbooleanが必要です")
    _text(data["automation_goal"], "automation_goal")
    _text(data["change_reason"], "change_reason")

    scope_refs = data["scope_refs"]
    if (
        not isinstance(scope_refs, list)
        or not scope_refs
        or any(not isinstance(ref, str) or not ref for ref in scope_refs)
        or scope_refs != sorted(set(scope_refs))
    ):
        raise ContractError("scope_refsは重複なしのcanonicalな非空配列が必要です")

    if not isinstance(data["source_refs"], list):
        raise ContractError("source_refsは配列が必要です")
    sources: dict[str, str] = {}
    source_rows: dict[str, dict[str, str]] = {}
    for index, raw in enumerate(data["source_refs"]):
        row = _object(raw, f"source_refs[{index}]", {"ref", "revision", "currentness"})
        ref = _text(row["ref"], "source ref")
        _text(row["revision"], "source revision")
        if (
            not isinstance(row["currentness"], str)
            or row["currentness"] not in SOURCE_STATES
            or ref in sources
        ):
            raise ContractError("source refのcurrentnessまたは一意性が不正です")
        sources[ref] = row["currentness"]
        source_rows[ref] = {
            "ref": ref,
            "revision": row["revision"].strip(),
            "currentness": row["currentness"],
        }
    if not sources:
        raise ContractError("source_refsが空です")
    if source_refs := [row["ref"] for row in data["source_refs"]]:
        if source_refs != sorted(source_refs):
            raise ContractError("source_refsはref順のcanonical配列が必要です")
    if set(scope_refs) - set(sources):
        raise ContractError("scope_refsにsource_refsにないrefがあります")

    if not isinstance(data["candidates"], list):
        raise ContractError("candidatesは配列が必要です")
    candidates: dict[str, tuple[str, str]] = {}
    candidate_source_refs: dict[str, list[str]] = {}
    candidate_keys: set[str] = set()
    candidate_ids: list[str] = []
    for index, raw in enumerate(data["candidates"]):
        row = _object(
            raw,
            f"candidates[{index}]",
            {"candidate_id", "candidate_key", "source_refs", "decision", "rationale"},
        )
        cid = _text(row["candidate_id"], "candidate_id")
        key = _text(row["candidate_key"], "candidate_key")
        if (
            not CANDIDATE_RE.fullmatch(cid)
            or cid in candidates
            or key in candidate_keys
        ):
            raise ContractError("candidate_idの形式または一意性が不正です")
        candidate_ids.append(cid)
        candidate_keys.add(key)
        refs = row["source_refs"]
        if (
            not isinstance(refs, list)
            or not refs
            or any(not isinstance(ref, str) or not ref for ref in refs)
            or refs != sorted(set(refs))
        ):
            raise ContractError("candidate.source_refsはcanonicalな非空配列が必要です")
        if set(refs) - set(sources):
            raise ContractError("candidateが未知のsourceを参照しています")
        if not isinstance(row["decision"], str) or row["decision"] not in DECISIONS:
            raise ContractError("candidate decisionが不正です")
        _text(row["rationale"], "candidate rationale")
        candidates[cid] = (key, row["decision"])
        candidate_source_refs[cid] = list(refs)
    if candidate_ids != sorted(candidate_ids):
        raise ContractError("candidatesはcandidate_id順のcanonical配列が必要です")
    if not data["population_complete"] and not data["blockers"]:
        raise ContractError("不完全な候補母集団にはblockerまたは再開条件が必要です")

    blockers = data["blockers"]
    if not isinstance(blockers, list) or any(
        not isinstance(item, str) or not item.strip() for item in blockers
    ):
        raise ContractError("blockersは非空文字列の配列が必要です")
    if not candidates and (data["population_complete"] or not blockers):
        raise ContractError("候補0件を記録するには不完全な母集団とblockerが必要です")

    history = data["history"]
    if not isinstance(history, list):
        raise ContractError("historyは配列が必要です")
    seen_revisions: list[int] = []
    historical_ids: dict[str, str] = {}
    historical_keys: dict[str, str] = {}
    historical_retirements: dict[str, str] = {}
    previous_history_ids: set[str] = set()
    history_complete = True
    unresolved_history_revisions: list[int] = []
    history_snapshots: dict[int, dict[str, Any]] = {}
    history_digests: dict[int, str] = {}
    for index, raw in enumerate(history):
        row = _object(
            raw,
            f"history[{index}]",
            {"revision", "candidate_ids", "change_reason", "retired_candidates"},
            {"selection_snapshot", "revision_digest"},
        )
        old_revision = row["revision"]
        if (
            not isinstance(old_revision, int)
            or isinstance(old_revision, bool)
            or old_revision < 1
        ):
            raise ContractError("history revisionが不正です")
        seen_revisions.append(old_revision)
        old_change_reason = _text(row["change_reason"], "history change_reason")
        old_ids = row["candidate_ids"]
        if not isinstance(old_ids, list) or not all(
            isinstance(old, dict) for old in old_ids
        ):
            raise ContractError("history candidate_idsが不正です")
        candidate_id_order = [old.get("candidate_id") for old in old_ids]
        if any(
            not isinstance(old_id, str) for old_id in candidate_id_order
        ) or candidate_id_order != sorted(set(candidate_id_order)):
            raise ContractError("history candidate_idsが不正です")
        if set(candidate_id_order) & set(historical_retirements):
            raise ContractError(
                "過去にretiredとなったcandidate IDがhistoryで再利用されています"
            )
        normalized_old_ids = []
        for old in old_ids:
            _object(old, "history candidate", {"candidate_id", "candidate_key"})
            old_id = _text(old["candidate_id"], "history candidate_id")
            old_key = _text(old["candidate_key"], "history candidate_key")
            if not CANDIDATE_RE.fullmatch(old_id):
                raise ContractError("history candidate_id形式が不正です")
            previous_key = historical_ids.get(old_id)
            if previous_key is not None and previous_key != old_key:
                raise ContractError(
                    "過去に使ったcandidate IDを別candidateへ再利用しています"
                )
            previous_id = historical_keys.get(old_key)
            if previous_id is not None and previous_id != old_id:
                raise ContractError(
                    "過去に使ったcandidate keyのIDが改訂時に変更されています"
                )
            historical_ids[old_id] = old_key
            historical_keys[old_key] = old_id
            normalized_old_ids.append(
                {"candidate_id": old_id, "candidate_key": old_key}
            )
        old_retirements = _retirement_map(
            row["retired_candidates"], f"history[{index}].retired_candidates"
        )
        removed_ids = previous_history_ids - set(candidate_id_order)
        if not removed_ids <= set(old_retirements):
            raise ContractError(
                "historyで削除されたcandidateにはretirement reasonが必要です"
            )
        if not set(historical_retirements) <= set(old_retirements):
            raise ContractError("historyから過去のcandidate retirementが失われています")
        if set(old_retirements) & set(candidate_id_order):
            raise ContractError(
                "history内でretired candidateが現行候補として再利用されています"
            )
        if set(old_retirements) - set(historical_ids):
            raise ContractError("未使用のcandidate IDをhistoryでretiredにできません")
        if any(
            old_retirements[candidate_id] != reason
            for candidate_id, reason in historical_retirements.items()
        ):
            raise ContractError(
                "history内のcandidate retirement reasonが変化しています"
            )
        if "selection_snapshot" not in row:
            history_complete = False
            unresolved_history_revisions.append(old_revision)
            if "revision_digest" in row:
                raise ContractError(
                    "snapshotのないhistory rowにrevision_digestがあります"
                )
        else:
            snapshot = _selection_snapshot(
                row["selection_snapshot"], f"history[{index}].selection_snapshot"
            )
            snapshot_id_keys = {
                candidate["candidate_id"]: candidate["candidate_key"]
                for candidate in snapshot["candidates"]
            }
            if snapshot_id_keys != {
                candidate["candidate_id"]: candidate["candidate_key"]
                for candidate in old_ids
            }:
                raise ContractError(
                    "history candidate snapshotとcandidate_idsが一致しません"
                )
            history_snapshots[old_revision] = snapshot
            expected_digest = _revision_digest(
                selection_ref,
                old_revision,
                old_change_reason,
                normalized_old_ids,
                [
                    {"candidate_id": candidate_id, "reason": reason}
                    for candidate_id, reason in sorted(old_retirements.items())
                ],
                snapshot,
            )
            if "revision_digest" not in row:
                history_complete = False
                unresolved_history_revisions.append(old_revision)
            else:
                supplied_digest = _text(
                    row["revision_digest"], "history revision_digest"
                )
                if not re.fullmatch(r"sha256:[0-9a-f]{64}", supplied_digest):
                    raise ContractError("history revision_digestの形式が不正です")
                if supplied_digest != expected_digest:
                    raise ContractError(
                        "history snapshotまたはrevision metadataが改変されています"
                    )
                history_digests[old_revision] = supplied_digest
        historical_retirements = old_retirements
        previous_history_ids = set(candidate_id_order)
    if seen_revisions != list(range(1, revision)):
        raise ContractError("revision履歴が欠落しています")
    for cid, (key, _decision) in candidates.items():
        if cid in historical_retirements:
            raise ContractError("過去にretiredとなったcandidate IDは再利用できません")
        if cid in historical_ids and historical_ids[cid] != key:
            raise ContractError("candidate IDが別candidate_keyへ再利用されています")
        if key in historical_ids.values() and cid not in historical_ids:
            raise ContractError("既存candidate_keyのIDが改訂時に変更されています")

    retired_by_id = _retirement_map(data["retired_candidates"], "retired_candidates")
    retired_ids = list(retired_by_id)
    if set(retired_ids) & set(candidates):
        raise ContractError("current candidateを同時にretiredにできません")
    if not (previous_history_ids - set(candidates)) <= set(retired_by_id):
        raise ContractError(
            "直前revisionから削除されたcandidateにはretirement reasonが必要です"
        )
    if set(retired_ids) - set(historical_ids):
        raise ContractError("未使用のcandidate IDをretiredにできません")
    missing_retirement = sorted(
        set(historical_ids) - set(candidates) - set(retired_ids)
    )
    if missing_retirement:
        raise ContractError(
            "削除された過去candidateには明示的なretirement reasonが必要です"
        )
    if not set(historical_retirements) <= set(retired_by_id):
        raise ContractError(
            "current selectionから過去のcandidate retirementが失われています"
        )
    if any(
        retired_by_id[candidate_id] != reason
        for candidate_id, reason in historical_retirements.items()
    ):
        raise ContractError(
            "current selectionで過去のcandidate retirement reasonが変化しています"
        )

    current_snapshot = _selection_snapshot(
        {
            "scope_refs": scope_refs,
            "automation_goal": data["automation_goal"],
            "population_complete": data["population_complete"],
            "source_refs": [source_rows[ref] for ref in sorted(source_rows)],
            "candidates": [
                {
                    "candidate_id": cid,
                    "candidate_key": key,
                    "source_refs": candidate_source_refs[cid],
                    "decision": decision,
                    "rationale": next(
                        row["rationale"]
                        for row in data["candidates"]
                        if row["candidate_id"] == cid
                    ),
                }
                for cid, (key, decision) in sorted(candidates.items())
            ],
            "blockers": blockers,
        },
        "current selection snapshot",
    )
    current_candidate_ids = [
        {"candidate_id": cid, "candidate_key": key}
        for cid, (key, _decision) in sorted(candidates.items())
    ]
    current_revision_digest = _revision_digest(
        selection_ref,
        revision,
        _text(data["change_reason"], "change_reason"),
        current_candidate_ids,
        [
            {"candidate_id": candidate_id, "reason": reason}
            for candidate_id, reason in sorted(retired_by_id.items())
        ],
        current_snapshot,
    )

    unresolved_sources = sorted(
        ref for ref, state in sources.items() if state != "current"
    )
    unresolved_candidates = sorted(
        cid
        for cid, (_key, decision) in candidates.items()
        if decision in {"deferred", "blocked"}
        or any(sources[ref] != "current" for ref in candidate_source_refs[cid])
    )
    referenced_candidate_sources = {
        ref for refs in candidate_source_refs.values() for ref in refs
    }
    unresolved_unassigned_sources = sorted(
        ref
        for ref in unresolved_sources
        if ref not in data["scope_refs"] and ref not in referenced_candidate_sources
    )
    unresolved_scope_sources = sorted(
        ref for ref in data["scope_refs"] if sources[ref] != "current"
    )
    if (
        unresolved_candidates
        or not history_complete
        or not data["population_complete"]
        or blockers
        or not candidates
        or unresolved_scope_sources
        or unresolved_unassigned_sources
    ):
        status = (
            "blocked"
            if blockers
            or not history_complete
            or any(candidates[cid][1] == "blocked" for cid in unresolved_candidates)
            else "unresolved"
        )
    else:
        status = "ready"
    selection_record = dict(data)
    selection_record["source_refs"] = sorted(
        (dict(row) for row in data["source_refs"]), key=lambda row: row["ref"]
    )
    selection_record["candidates"] = sorted(
        (dict(row) for row in data["candidates"]), key=lambda row: row["candidate_id"]
    )
    selection_record["history"] = [
        {
            **row,
            "candidate_ids": sorted(
                (dict(candidate) for candidate in row["candidate_ids"]),
                key=lambda candidate: candidate["candidate_id"],
            ),
            "retired_candidates": [
                {"candidate_id": candidate_id, "reason": reason}
                for candidate_id, reason in sorted(
                    _retirement_map(
                        row["retired_candidates"], "history.retired_candidates"
                    ).items()
                )
            ],
            **(
                {"selection_snapshot": history_snapshots[row["revision"]]}
                if row["revision"] in history_snapshots
                else {}
            ),
            **(
                {"revision_digest": history_digests[row["revision"]]}
                if row["revision"] in history_digests
                else {}
            ),
        }
        for row in data["history"]
    ]
    return {
        "valid": True,
        "selection_ref": selection_ref,
        "revision": revision,
        "selection_status": status,
        "history_complete": history_complete,
        "unresolved_history_revisions": sorted(unresolved_history_revisions),
        "current_revision_digest": current_revision_digest,
        "candidate_count": len(candidates),
        "selected_candidate_ids": sorted(
            cid
            for cid, (_key, decision) in candidates.items()
            if decision == "selected"
            and all(sources[ref] == "current" for ref in candidate_source_refs[cid])
        ),
        "unresolved_source_refs": unresolved_sources,
        "unresolved_candidate_ids": unresolved_candidates,
        "selection_record": selection_record,
    }


def _current_source_revisions(value: Any) -> dict[str, str]:
    """Validate the caller-supplied ``ref -> revision`` map of current sources.

    The map is evidence supplied by the caller (the source owner's readback). This
    function only checks its shape; it never fetches a revision itself.
    """
    if not isinstance(value, dict) or not value:
        raise ContractError("current_source_revisionsは空でないobjectが必要です")
    result: dict[str, str] = {}
    for key, revision in value.items():
        ref = _text(key, "current_source_revisions key")
        if not isinstance(revision, str):
            raise ContractError("current_source_revisionsの値は文字列が必要です")
        if ref in result:
            raise ContractError("current_source_revisionsのrefが重複しています")
        result[ref] = _text(revision, "current_source_revisions value")
    return result


def impact(packet: Any, current_source_revisions: Any) -> dict:
    """Compare saved source refs with the current revisions supplied by the caller.

    The saved packet must pass ``validate`` first. A saved source is ``current``
    only when the supplied map has the same ref with the same revision; a changed
    revision is ``stale`` and a ref absent from the map is ``unknown`` (fail-closed).
    The saved ``currentness`` self-declaration is ignored here. Candidates that
    depend on a changed or unknown source are impacted; the others are unaffected.
    The saved packet is not modified, so stable IDs and revision history are kept.
    Refs in the map that the packet does not save are ignored.
    """
    result = validate(packet)
    current = _current_source_revisions(current_source_revisions)
    saved = {
        row["ref"].strip(): row["revision"].strip() for row in packet["source_refs"]
    }
    changed = sorted(
        ref
        for ref, revision in saved.items()
        if ref in current and current[ref] != revision
    )
    unknown = sorted(ref for ref in saved if ref not in current)
    affected = set(changed) | set(unknown)
    impacted = []
    unaffected = []
    for row in packet["candidates"]:
        target = impacted if affected & set(row["source_refs"]) else unaffected
        target.append(row["candidate_id"])
    if unknown:
        source_status = "unknown"
    elif changed:
        source_status = "stale"
    else:
        source_status = "current"
    return {
        "valid": True,
        "selection_ref": result["selection_ref"],
        "revision": result["revision"],
        "source_status": source_status,
        "changed_source_refs": changed,
        "unknown_source_refs": unknown,
        "impacted_candidate_ids": sorted(impacted),
        "unaffected_candidate_ids": sorted(unaffected),
    }


def inspection_handoff(packet: Any) -> dict:
    """Derive the targets that ``e2e-test-inspection`` may take from a selection.

    Only ``selected`` candidates whose sources are all current are handed over.
    Deferred, not-selected and blocked candidates are never targets, and a
    selection that is not ``ready`` (stale or unknown source, incomplete
    population, blockers, incomplete history) hands over nothing: inspection
    must stop as blocked for the affected targets instead of using it.
    """
    result = validate(packet)
    data = packet
    source_revisions = {row["ref"]: row["revision"] for row in data["source_refs"]}
    selected = set(result["selected_candidate_ids"])
    targets = [
        {
            "candidate_id": row["candidate_id"],
            "candidate_key": row["candidate_key"],
            "rationale": row["rationale"],
            "sources": [
                {"ref": ref, "revision": source_revisions[ref]}
                for ref in row["source_refs"]
            ],
        }
        for row in sorted(data["candidates"], key=lambda row: row["candidate_id"])
        if row["candidate_id"] in selected
    ]
    ready = result["selection_status"] == "ready"
    return {
        "selection_ref": result["selection_ref"],
        "selection_revision": result["revision"],
        "selection_status": result["selection_status"],
        "usable": ready,
        "targets": targets if ready else [],
        "withheld_reason": None
        if ready
        else {
            "selection_status": result["selection_status"],
            "unresolved_source_refs": result["unresolved_source_refs"],
            "unresolved_candidate_ids": result["unresolved_candidate_ids"],
        },
    }


def main() -> int:
    try:
        raw = sys.stdin.buffer.read(MAX_INPUT_BYTES + 1)
        envelope = _load_request(raw)
        if not isinstance(envelope, dict):
            raise ContractError("runtime envelopeはobjectが必要です")
        if set(envelope) == {"input"}:
            result = validate(envelope["input"])
            output = {
                "runtime_status": "ok",
                "result_status": result["selection_status"],
                "payload": result,
            }
        elif (
            set(envelope)
            == {
                "operation",
                "input",
                "current_source_revisions",
            }
            and envelope["operation"] == "impact"
        ):
            result = impact(envelope["input"], envelope["current_source_revisions"])
            output = {
                "runtime_status": "ok",
                "result_status": result["source_status"],
                "payload": result,
            }
        else:
            raise ContractError(
                "runtime envelopeはinputだけ、またはimpact operationの3キーだけを持つobjectが必要です"
            )
    except InputLimitError as exc:
        output = _error_envelope("limit_exceeded", str(exc))
    except ContractError as exc:
        output = _error_envelope("invalid_input", str(exc))
    except (KeyError, TypeError, IndexError, AttributeError, OverflowError):
        output = _error_envelope("invalid_input", "selection JSON schemaが不正です")
    except Exception:
        sys.stdout.buffer.write(
            _encode_output(
                _error_envelope(
                    "internal_error", "runtimeで予期しないエラーが発生しました"
                )
            )
        )
        return 1
    try:
        encoded = _encode_output(output)
    except ContractError:
        encoded = (
            json.dumps(
                _error_envelope("internal_error", "runtime outputを生成できません"),
                ensure_ascii=False,
                sort_keys=True,
            )
            + "\n"
        ).encode("utf-8")
        sys.stdout.buffer.write(encoded)
        return 1
    sys.stdout.buffer.write(encoded)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
