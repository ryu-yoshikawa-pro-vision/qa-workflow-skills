from __future__ import annotations

import json
import re
from typing import Any

from scripts.skills.evals.deterministic.result import EvalResult

_SECRET = re.compile(
    r"(?i)(?:password|access[_-]?token|client[_-]?secret|api[_-]?key)\s*[:=]\s*['\"]?[A-Za-z0-9_./+=-]{8,}"
)


def _is_ref(value: Any) -> bool:
    """Same rule as exploratory_runtime._is_ref: a non-empty string."""
    return isinstance(value, str) and bool(value)


def _ref_list(value: Any) -> bool:
    """Same rule as exploratory_runtime._ref_list: a non-empty list of refs."""
    return isinstance(value, list) and bool(value) and all(_is_ref(v) for v in value)


def _usable_origin(value: Any) -> bool:
    """Same rule as exploratory_runtime.validate_charter: a non-blank string."""
    return isinstance(value, str) and bool(value.strip())


# Keep in step with exploratory_runtime.INVESTIGATION_ORIGIN_KEYS. The validator
# does not import the runtime so the Skill stays isolated when it is packaged.
_ORIGIN_KEYS = (
    "symptom_ref",
    "hypothesis_ref",
    "unresolved_finding_ref",
    "symptom",
    "hypothesis",
)
_MODES = {"exploration", "investigation"}
_STATES = {"未開始", "実行中", "部分完了（ブロック中あり）", "ブロック中", "完了"}


def _document(text: str) -> tuple[dict[str, Any] | None, list[str]]:
    matches = re.findall(
        r"```json\s*\n(.*?)\n```", text, flags=re.DOTALL | re.IGNORECASE
    )
    if len(matches) != 1:
        return None, ["exactly_one_json_session_required"]
    try:
        value = json.loads(matches[0])
    except json.JSONDecodeError as exc:
        return None, [f"invalid_json:{exc.msg}"]
    return (
        (value, [])
        if isinstance(value, dict)
        else (None, ["session_root_must_be_object"])
    )


def validate(text: str, expected: dict[str, Any], eval_id: str) -> EvalResult:
    result = EvalResult("exploratory-testing", eval_id)
    doc, errors = _document(text)
    result.add(
        "EXP-D001",
        doc is not None,
        "Session artifactが一つだけ整形式で存在すること",
        evidence=errors or None,
    )
    if doc is None:
        return result
    # Any JSON value can appear in a graded output: a wrong type is a failed check,
    # never an exception in the evaluator.
    charter = doc.get("charter", {})
    if not isinstance(charter, dict):
        charter = {}
    mode = doc.get("mode")
    state = doc.get("state")
    required = {
        "purpose",
        "in_scope",
        "out_of_scope",
        "source_refs",
        "timebox_or_exit_condition",
        "allowed_origins",
        "allowed_operations",
        "side_effect_operations",
        "side_effect_scope",
        "side_effect_action_definition",
        "side_effect_maximum",
        "cleanup_plan",
        "evidence_policy",
        "block_conditions",
    }
    missing = sorted(
        key
        for key in required
        if key not in charter
        or charter[key] is None
        or charter[key] == ""
        or (key != "side_effect_operations" and charter[key] == [])
    )
    result.add(
        "EXP-D002",
        isinstance(mode, str) and mode in _MODES and not missing,
        "modeとCharter必須項目が揃うこと",
        evidence={"mode": mode if isinstance(mode, str) else None, "missing": missing},
    )
    inv_ok = mode != "investigation" or any(
        _usable_origin(charter.get(key)) for key in _ORIGIN_KEYS
    )
    result.add(
        "EXP-D003",
        inv_ok,
        "investigationはsymptom・hypothesis・unresolved Findingのいずれかを起点にすること",
    )
    observations, findings = doc.get("observations"), doc.get("findings")
    separated = isinstance(observations, list) and isinstance(findings, list)
    observations = observations if isinstance(observations, list) else []
    findings = findings if isinstance(findings, list) else []
    # Refs are compared only after they are known to be non-empty strings.
    obs_refs = [
        item.get("observation_ref") for item in observations if isinstance(item, dict)
    ]
    finding_refs = [
        item.get("finding_ref") for item in findings if isinstance(item, dict)
    ]
    refs_valid = (
        len(obs_refs) == len(observations)
        and len(finding_refs) == len(findings)
        and all(_is_ref(ref) for ref in obs_refs)
        and all(_is_ref(ref) for ref in finding_refs)
        and len(obs_refs) == len(set(obs_refs))
        and len(finding_refs) == len(set(finding_refs))
    )
    obs_set = {ref for ref in obs_refs if _is_ref(ref)}
    finding_links = all(
        isinstance(item, dict)
        and _ref_list(item.get("source_observation_refs"))
        and set(item["source_observation_refs"]) <= obs_set
        and _ref_list(item.get("evidence_refs"))
        and bool(item.get("follow_up_reason"))
        and _is_ref(item.get("recommended_routing"))
        for item in findings
    )
    result.add(
        "EXP-D004",
        separated and refs_valid and finding_links,
        "Observation / Findingを分離し、unique ref・evidence・source / follow-upを閉じること",
    )
    cleanup = doc.get("cleanup", {})
    if not isinstance(cleanup, dict):
        cleanup = {}
    complete = state != "完了" or (
        not cleanup.get("required")
        or cleanup.get("status") in ("成功", "意図的に残した状態")
    )
    if state == "完了" and doc.get("residual_side_effect"):
        complete = (
            complete
            and cleanup.get("status") == "意図的に残した状態"
            and cleanup.get("authorized_residual") is True
        )
    result.add(
        "EXP-D005",
        isinstance(state, str) and state in _STATES and complete,
        "required cleanupが未確認 / 失敗なら安全完了にしないこと",
    )
    result.add(
        "EXP-D006",
        not (
            doc.get("previous_state") == "完了" and doc.get("mutation_applied") is True
        ),
        "completed Sessionをimmutableとして扱うこと",
    )
    result.add(
        "EXP-D007",
        _SECRET.search(text) is None,
        "secret実値を正規Sessionへ含めないこと",
    )
    result.add(
        "EXP-D008",
        not expected.get("requires_blocked", False) or state == "ブロック中",
        "fixtureのunsafe / unavailable条件をblockすること",
    )
    return result
