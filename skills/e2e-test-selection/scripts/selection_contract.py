"""Validate a technology-neutral E2E selection packet without persistence assumptions."""

from __future__ import annotations

import json
import re
import sys
from typing import Any

SELECTION_RE = re.compile(r"^E2ESEL-\d{3,}$")
CANDIDATE_RE = re.compile(r"^E2E-CAND-\d{3,}$")
DECISIONS = {"selected", "not_selected", "deferred", "blocked"}
SOURCE_STATES = {"current", "stale", "unknown"}


class ContractError(ValueError):
    pass


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
    if candidate_ids != sorted(candidate_ids):
        raise ContractError("candidatesはcandidate_id順のcanonical配列が必要です")
    if not data["population_complete"] and not data["blockers"]:
        raise ContractError("不完全な候補母集団にはblockerまたは再開条件が必要です")

    blockers = data["blockers"]
    if not isinstance(blockers, list) or any(
        not isinstance(item, str) or not item.strip() for item in blockers
    ):
        raise ContractError("blockersは非空文字列の配列が必要です")

    history = data["history"]
    if not isinstance(history, list):
        raise ContractError("historyは配列が必要です")
    seen_revisions: list[int] = []
    historical_ids: dict[str, str] = {}
    historical_keys: dict[str, str] = {}
    historical_retirements: dict[str, str] = {}
    previous_history_ids: set[str] = set()
    for index, raw in enumerate(history):
        row = _object(
            raw,
            f"history[{index}]",
            {"revision", "candidate_ids", "change_reason", "retired_candidates"},
        )
        old_revision = row["revision"]
        if (
            not isinstance(old_revision, int)
            or isinstance(old_revision, bool)
            or old_revision < 1
        ):
            raise ContractError("history revisionが不正です")
        seen_revisions.append(old_revision)
        _text(row["change_reason"], "history change_reason")
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

    unresolved_sources = sorted(
        ref for ref, state in sources.items() if state != "current"
    )
    unresolved_candidates = sorted(
        cid
        for cid, (_key, decision) in candidates.items()
        if decision in {"deferred", "blocked"}
    )
    if (
        unresolved_sources
        or unresolved_candidates
        or not data["population_complete"]
        or blockers
        or not candidates
    ):
        status = (
            "blocked"
            if blockers
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
        }
        for row in data["history"]
    ]
    return {
        "valid": True,
        "selection_ref": selection_ref,
        "revision": revision,
        "selection_status": status,
        "candidate_count": len(candidates),
        "selected_candidate_ids": sorted(
            cid
            for cid, (_key, decision) in candidates.items()
            if decision == "selected"
        ),
        "unresolved_source_refs": unresolved_sources,
        "unresolved_candidate_ids": unresolved_candidates,
        "selection_record": selection_record,
    }


def main() -> None:
    try:
        envelope = json.loads(sys.stdin.buffer.read().decode("utf-8"))
        if not isinstance(envelope, dict) or set(envelope) != {"input"}:
            raise ContractError("runtime envelopeはinputだけを持つobjectが必要です")
        result = validate(envelope["input"])
        output = {
            "runtime_status": "ok",
            "result_status": result["selection_status"],
            "payload": result,
        }
    except (ContractError, json.JSONDecodeError) as exc:
        output = {
            "runtime_status": "invalid_input",
            "result_status": "blocked",
            "error": str(exc),
        }
    sys.stdout.buffer.write(
        (json.dumps(output, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
    )


if __name__ == "__main__":
    main()
