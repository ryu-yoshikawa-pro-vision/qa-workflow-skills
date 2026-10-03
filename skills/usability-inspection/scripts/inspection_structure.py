"""Deterministic inspection scope and artifact structure helpers."""
from __future__ import annotations

import hashlib
import json
from typing import Any

ASPECTS = (
    ("interaction-operability", "interaction / operability"),
    ("feedback-system-status", "feedback / system status"),
    ("error-prevention-recovery", "error prevention / recovery"),
    ("accessibility", "accessibility"),
    ("visual-responsive", "visual integrity / responsive"),
    ("measurable-standard-criteria", "measurable standard criteria"),
    ("performance-responsiveness", "user-facing performance / responsiveness"),
)
ASPECT_KEYS = {key for key, _ in ASPECTS}
OUTCOMES = {"問題を確認", "問題なし", "判定不能", "対象外"}


class InspectionContractError(ValueError):
    pass


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def fingerprint(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(value)).hexdigest()


def scope_skeleton(mode: str, *, requested_aspects: list[str] | None = None,
                   formal_scope: list[dict[str, Any]] | None = None,
                   task_flow: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    if mode == "general":
        selected = [key for key, _ in ASPECTS]
    elif mode == "scoped":
        selected = requested_aspects or []
        if not selected or len(selected) != len(set(selected)) or set(selected) - ASPECT_KEYS:
            raise InspectionContractError("scoped mode requires unique canonical aspect keys")
        selected = [key for key, _ in ASPECTS if key in set(selected)]
    elif mode == "formal-handoff":
        if not formal_scope:
            raise InspectionContractError("formal-handoff requires a non-empty typed required scope")
        rows = []
        for index, item in enumerate(formal_scope, 1):
            if set(item) != {"scope_ref", "description", "evidence_refs"}:
                raise InspectionContractError("formal scope rows require scope_ref, description, evidence_refs")
            rows.append({"scope_ref": f"SCOPE-{index:03d}", "aspect_key": None,
                         "label": item["description"], "scope_decision": "今回確認する",
                         "outcome": None, "reason": None, "evidence_refs": list(item["evidence_refs"])})
        return rows
    else:
        raise InspectionContractError("inspection mode must be general, scoped, or formal-handoff")

    labels = dict(ASPECTS)
    rows = [{"scope_ref": f"SCOPE-{index:03d}", "aspect_key": key, "label": labels[key],
             "scope_decision": "今回確認する", "outcome": None, "reason": None, "evidence_refs": []}
            for index, key in enumerate(selected, 1)]
    if task_flow is not None:
        if set(task_flow) != {"task_ref", "description", "goal_ref"}:
            raise InspectionContractError("task_flow requires task_ref, description, goal_ref")
        rows.append({"scope_ref": f"SCOPE-{len(rows)+1:03d}", "aspect_key": "task-flow",
                     "label": task_flow["description"], "scope_decision": "今回確認する",
                     "outcome": None, "reason": None, "evidence_refs": []})
    return rows


def materialize_refs(records: list[dict[str, Any]], prefix: str) -> list[dict[str, Any]]:
    seen: set[str] = set()
    output = []
    for index, record in enumerate(records, 1):
        key = record.get("draft_key")
        if not isinstance(key, str) or not key or key in seen:
            raise InspectionContractError("each invocation record requires a unique draft_key")
        seen.add(key)
        output.append({**record, "draft_key": key, "ref": f"{prefix}-{index:03d}"})
    return output


def close_scope(rows: list[dict[str, Any]]) -> dict[str, Any]:
    refs: set[str] = set()
    issues: list[str] = []
    for row in rows:
        ref = row.get("scope_ref")
        if not isinstance(ref, str) or ref in refs:
            issues.append("missing_or_duplicate_scope_ref")
        refs.add(ref)
        if row.get("scope_decision") not in {"今回確認する", "対象外"}:
            issues.append(f"invalid_scope_decision:{ref}")
        if row.get("outcome") not in OUTCOMES:
            issues.append(f"scope_not_closed:{ref}")
        if row.get("scope_decision") == "対象外" and not str(row.get("reason", "")).strip():
            issues.append(f"out_of_scope_reason_missing:{ref}")
        if row.get("outcome") == "対象外" and not str(row.get("reason", "")).strip():
            issues.append(f"outcome_reason_missing:{ref}")
        if row.get("outcome") == "問題を確認" and not row.get("evidence_refs"):
            issues.append(f"issue_without_evidence:{ref}")
    return {"closed": not issues, "issues": issues,
            "summary": {outcome: sum(row.get("outcome") == outcome for row in rows) for outcome in sorted(OUTCOMES)}}


def finding_requirement(outcome: str, follow_up_required: bool) -> bool:
    if outcome not in OUTCOMES or not isinstance(follow_up_required, bool):
        raise InspectionContractError("invalid outcome or follow_up_required")
    return outcome == "問題を確認" and follow_up_required


def validate_formal_handoff(request: dict[str, Any]) -> dict[str, Any]:
    required = {"request_kind", "observation_request_ref", "request_signature", "machine_probe_key",
                "currentness_dependency", "target_identity"}
    missing = sorted(required - set(request))
    if missing or request.get("request_kind") != "wcag-machine-probe":
        raise InspectionContractError(f"invalid formal handoff request; missing={missing}")
    return {"request_ref": request["observation_request_ref"],
            "request_signature": request["request_signature"],
            "machine_probe_key": request["machine_probe_key"],
            "input_fingerprint": fingerprint({k: request[k] for k in sorted(required - {"request_signature"})})}
