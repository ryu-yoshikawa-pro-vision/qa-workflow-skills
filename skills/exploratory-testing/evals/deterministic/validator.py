from __future__ import annotations

import json
import re
from typing import Any

from scripts.skills.evals.deterministic.result import EvalResult


_SECRET = re.compile(r"(?i)(?:password|access[_-]?token|client[_-]?secret|api[_-]?key)\s*[:=]\s*['\"]?[A-Za-z0-9_./+=-]{8,}")


def _document(text: str) -> tuple[dict[str, Any] | None, list[str]]:
    matches = re.findall(r"```json\s*\n(.*?)\n```", text, flags=re.DOTALL | re.IGNORECASE)
    if len(matches) != 1:
        return None, ["exactly_one_json_session_required"]
    try:
        value = json.loads(matches[0])
    except json.JSONDecodeError as exc:
        return None, [f"invalid_json:{exc.msg}"]
    return (value, []) if isinstance(value, dict) else (None, ["session_root_must_be_object"])


def validate(text: str, expected: dict[str, Any], eval_id: str) -> EvalResult:
    result = EvalResult("exploratory-testing", eval_id)
    doc, errors = _document(text)
    result.add("EXP-D001", doc is not None, "Session artifactが一つだけ整形式で存在すること", evidence=errors or None)
    if doc is None:
        return result
    charter = doc.get("charter", {})
    required = {"purpose", "in_scope", "out_of_scope", "source_refs", "timebox_or_exit_condition", "allowed_origins", "allowed_operations", "side_effect_operations", "side_effect_scope", "side_effect_action_definition", "side_effect_maximum", "cleanup_plan", "evidence_policy", "block_conditions"}
    missing = sorted(
        key for key in required
        if key not in charter
        or charter[key] is None
        or charter[key] == ""
        or (key != "side_effect_operations" and charter[key] == [])
    )
    result.add("EXP-D002", doc.get("mode") in {"exploration", "investigation"} and not missing, "modeとCharter必須項目が揃うこと", evidence={"mode": doc.get("mode"), "missing": missing})
    inv_ok = doc.get("mode") != "investigation" or bool(charter.get("symptom_ref") or charter.get("hypothesis_ref") or charter.get("symptom") or charter.get("hypothesis"))
    result.add("EXP-D003", inv_ok, "investigationはsymptomまたはhypothesisを起点にすること")
    observations, findings = doc.get("observations"), doc.get("findings")
    separated = isinstance(observations, list) and isinstance(findings, list)
    obs_refs = [item.get("observation_ref") for item in observations if isinstance(item, dict)] if isinstance(observations, list) else []
    finding_refs = [item.get("finding_ref") for item in findings if isinstance(item, dict)] if isinstance(findings, list) else []
    refs_valid = len(obs_refs) == len(set(obs_refs)) and len(finding_refs) == len(set(finding_refs)) and all(obs_refs) and all(finding_refs)
    obs_set = set(obs_refs)
    finding_links = all(set(item.get("source_observation_refs", [])) <= obs_set and item.get("evidence_refs") and item.get("follow_up_reason") for item in findings if isinstance(item, dict))
    result.add("EXP-D004", separated and refs_valid and finding_links, "Observation / Findingを分離し、unique ref・evidence・source / follow-upを閉じること")
    cleanup = doc.get("cleanup", {})
    complete = doc.get("state") != "完了" or (not cleanup.get("required") or cleanup.get("status") in {"成功", "意図的に残した状態"})
    if doc.get("state") == "完了" and doc.get("residual_side_effect"):
        complete = complete and cleanup.get("status") == "意図的に残した状態" and cleanup.get("authorized_residual") is True
    result.add("EXP-D005", doc.get("state") in {"未開始", "実行中", "部分完了（ブロック中あり）", "ブロック中", "完了"} and complete, "required cleanupが未確認 / 失敗なら安全完了にしないこと")
    result.add("EXP-D006", not (doc.get("previous_state") == "完了" and doc.get("mutation_applied") is True), "completed Sessionをimmutableとして扱うこと")
    result.add("EXP-D007", _SECRET.search(text) is None, "secret実値を正規Sessionへ含めないこと")
    result.add("EXP-D008", not expected.get("requires_blocked", False) or doc.get("state") == "ブロック中", "fixtureのunsafe / unavailable条件をblockすること")
    return result
