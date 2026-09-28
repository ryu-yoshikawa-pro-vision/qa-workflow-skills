"""Explicit supported accessibility check dispatch; no general rule DSL."""
from __future__ import annotations

from typing import Any

SUPPORTED_RULES = {
    "2779a5": {"criterion": "2.4.2", "dispatch": "non_empty_page_title"},
    "97a4e1": {"criterion": "4.1.2", "dispatch": "button_accessible_name"},
    "23a2a8": {"criterion": "1.1.1", "dispatch": "image_accessible_name"},
}
ACT_OUTCOMES = {"inapplicable", "passed", "failed", "cantTell", "untested"}


class RuleContractError(ValueError):
    pass


def run_supported_rule(rule_id: str, observations: dict[str, Any]) -> dict[str, Any]:
    rule = SUPPORTED_RULES.get(rule_id)
    if rule is None:
        raise RuleContractError("unsupported ACT rule cannot be dispatched")
    if rule_id == "2779a5":
        title = observations.get("document.title")
        outcome = "inapplicable" if title is None else ("passed" if isinstance(title, str) and title.strip() else "failed")
        refs = observations.get("evidence_refs", [])
    elif rule_id == "97a4e1":
        buttons = observations.get("buttons")
        if not isinstance(buttons, list):
            return {"rule_id": rule_id, "outcome": "cantTell", "criterion_ref": rule["criterion"], "evidence_refs": []}
        outcome = "inapplicable" if not buttons else ("passed" if all(isinstance(x.get("accessible_name"), str) and x["accessible_name"].strip() for x in buttons) else "failed")
        refs = [ref for item in buttons for ref in item.get("evidence_refs", [])]
    else:
        images = observations.get("images")
        if not isinstance(images, list):
            return {"rule_id": rule_id, "outcome": "cantTell", "criterion_ref": rule["criterion"], "evidence_refs": []}
        outcome = "inapplicable" if not images else ("passed" if all(isinstance(x.get("accessible_name"), str) and x["accessible_name"].strip() for x in images) else "failed")
        refs = [ref for item in images for ref in item.get("evidence_refs", [])]
    if outcome not in ACT_OUTCOMES:
        raise RuleContractError("invalid ACT outcome")
    return {"rule_id": rule_id, "outcome": outcome, "criterion_ref": rule["criterion"], "evidence_refs": sorted(set(refs))}


def requirement_result(*, applicability: str, semantic_result: str | None,
                       population_complete: bool, required_checks_complete: bool,
                       evidence_refs: list[str]) -> str:
    if applicability == "not-applicable":
        return "undetermined"
    if applicability != "applicable":
        return "undetermined"
    if semantic_result in {"satisfied", "not-satisfied"}:
        if semantic_result == "not-satisfied" and evidence_refs:
            return semantic_result
        if semantic_result == "satisfied" and population_complete and required_checks_complete and evidence_refs:
            return semantic_result
    return "undetermined"
