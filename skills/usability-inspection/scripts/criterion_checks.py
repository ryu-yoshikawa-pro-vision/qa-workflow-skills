"""Explicit supported accessibility check dispatch; no general rule DSL."""
from __future__ import annotations

from typing import Any

SUPPORTED_RULES = {
    "2779a5": {"criterion": "2.4.2", "dispatch": "non_empty_page_title"},
    "97a4e1": {"criterion": "4.1.2", "dispatch": "button_accessible_name"},
    "23a2a8": {"criterion": "1.1.1", "dispatch": "image_accessible_name"},
}
ACT_OUTCOMES = {"inapplicable", "passed", "failed", "cantTell", "untested"}
HTML_NAMESPACE = "http://www.w3.org/1999/xhtml"


class RuleContractError(ValueError):
    pass


def run_supported_rule(rule_id: str, observations: dict[str, Any]) -> dict[str, Any]:
    rule = SUPPORTED_RULES.get(rule_id)
    if rule is None:
        raise RuleContractError("unsupported ACT rule cannot be dispatched")
    if rule_id == "2779a5":
        refs = observations.get("evidence_refs", [])
        title = observations.get("document.title")
        if (not isinstance(title, dict) or title.get("status") != "ok"
                or not isinstance(refs, list) or not refs
                or any(not isinstance(ref, str) or not ref.strip() for ref in refs)):
            return {"rule_id": rule_id, "outcome": "cantTell", "criterion_ref": rule["criterion"], "evidence_refs": []}
        refs = list(refs)
        for field in ("is_html_document", "has_html_title_descendant", "first_title_children_are_text",
                      "has_non_whitespace_text"):
            if not isinstance(title.get(field), bool):
                return {"rule_id": rule_id, "outcome": "cantTell", "criterion_ref": rule["criterion"],
                        "evidence_refs": sorted(set(refs))}
        if not title["is_html_document"]:
            outcome = "inapplicable"
        elif (title["has_html_title_descendant"] and title["first_title_children_are_text"]
              and title["has_non_whitespace_text"]):
            outcome = "passed"
        else:
            outcome = "failed"
    elif rule_id == "97a4e1":
        buttons = observations.get("buttons")
        refs = observations.get("evidence_refs", [])
        if (not isinstance(buttons, list) or observations.get("population_complete") is not True
                or not isinstance(refs, list)
                or any(not isinstance(ref, str) or not ref.strip() for ref in refs)):
            return {"rule_id": rule_id, "outcome": "cantTell", "criterion_ref": rule["criterion"], "evidence_refs": []}
        refs = list(refs)
        applicable_buttons = []
        for item in buttons:
            if not isinstance(item, dict):
                return {"rule_id": rule_id, "outcome": "cantTell", "criterion_ref": rule["criterion"], "evidence_refs": []}
            item_refs = item.get("evidence_refs", [])
            if not isinstance(item_refs, list) or any(not isinstance(ref, str) or not ref.strip() for ref in item_refs):
                return {"rule_id": rule_id, "outcome": "cantTell", "criterion_ref": rule["criterion"], "evidence_refs": []}
            refs.extend(item_refs)
            included = item.get("included_in_accessibility_tree")
            role = item.get("role")
            host_element = item.get("host_element")
            host_type = item.get("host_type")
            if (item.get("status") != "ok" or not isinstance(included, bool)
                    or not isinstance(item.get("programmatically_hidden"), bool)
                    or not isinstance(role, str) or not role.strip()
                    or not isinstance(host_element, str) or not host_element.strip()
                    or (host_element.casefold() == "html:input"
                        and (not isinstance(host_type, str) or not host_type.strip()))):
                return {"rule_id": rule_id, "outcome": "cantTell", "criterion_ref": rule["criterion"],
                        "evidence_refs": sorted(set(refs))}
            if not included or role.casefold() != "button":
                continue
            if host_element.casefold() == "html:input" and host_type.casefold() == "image":
                continue
            name = item.get("accessible_name")
            if not isinstance(name, str):
                return {"rule_id": rule_id, "outcome": "cantTell", "criterion_ref": rule["criterion"],
                        "evidence_refs": sorted(set(refs))}
            applicable_buttons.append(name)
        outcome = ("inapplicable" if not applicable_buttons
                   else "passed" if all(name.strip() for name in applicable_buttons) else "failed")
    else:
        images = observations.get("images")
        refs = observations.get("evidence_refs", [])
        if (not isinstance(images, list) or observations.get("population_complete") is not True
                or not isinstance(refs, list)
                or any(not isinstance(ref, str) or not ref.strip() for ref in refs)):
            return {"rule_id": rule_id, "outcome": "cantTell", "criterion_ref": rule["criterion"], "evidence_refs": []}
        refs = list(refs)
        applicable_images = []
        for item in images:
            if not isinstance(item, dict):
                return {"rule_id": rule_id, "outcome": "cantTell", "criterion_ref": rule["criterion"],
                        "evidence_refs": sorted(set(refs))}
            item_refs = item.get("evidence_refs", [])
            if not isinstance(item_refs, list) or any(not isinstance(ref, str) or not ref.strip() for ref in item_refs):
                return {"rule_id": rule_id, "outcome": "cantTell", "criterion_ref": rule["criterion"],
                        "evidence_refs": sorted(set(refs))}
            refs.extend(item_refs)
            role = item.get("role")
            host_element = item.get("host_element")
            hidden = item.get("programmatically_hidden")
            if (item.get("status") != "ok" or not isinstance(role, str) or not role.strip()
                    or not isinstance(host_element, str) or not host_element.strip()
                    or not isinstance(hidden, bool)):
                return {"rule_id": rule_id, "outcome": "cantTell", "criterion_ref": rule["criterion"],
                        "evidence_refs": sorted(set(refs))}
            is_html_image = host_element.casefold() == "html:img"
            is_html_semantic_image = host_element.casefold().startswith("html:") and role.casefold() == "img"
            if hidden or not (is_html_image or is_html_semantic_image):
                continue
            name = item.get("accessible_name")
            if not isinstance(name, str):
                return {"rule_id": rule_id, "outcome": "cantTell", "criterion_ref": rule["criterion"],
                        "evidence_refs": sorted(set(refs))}
            applicable_images.append((role.casefold(), name))
        outcome = ("inapplicable" if not applicable_images
                   else "passed" if all(name.strip() or role in {"none", "presentation"}
                                        for role, name in applicable_images)
                   else "failed")
    if not isinstance(refs, list) or any(not isinstance(ref, str) or not ref.strip() for ref in refs) or not refs:
        outcome = "cantTell"
        refs = []
    if outcome not in ACT_OUTCOMES:
        raise RuleContractError("invalid ACT outcome")
    return {"rule_id": rule_id, "outcome": outcome, "criterion_ref": rule["criterion"], "evidence_refs": sorted(set(refs))}


def requirement_result(*, applicability: str, semantic_result: str | None,
                       population_complete: bool, required_checks_complete: bool,
                       evidence_refs: list[str], threshold_result: str | None = None,
                       authority_ref: str | None = None) -> str:
    if threshold_result is not None:
        if semantic_result is not None:
            raise RuleContractError("semantic and threshold requirement results are mutually exclusive")
        if threshold_result not in {"within-threshold", "over-threshold", "threshold-not-defined"}:
            raise RuleContractError("invalid threshold result")
        if threshold_result == "threshold-not-defined":
            if authority_ref:
                raise RuleContractError("threshold-not-defined cannot carry an Authority ref")
        elif not isinstance(authority_ref, str) or not authority_ref.strip():
            raise RuleContractError("threshold comparison requires a project Authority ref")
        if applicability != "applicable":
            return "undetermined"
        if threshold_result == "over-threshold":
            return "not-satisfied" if evidence_refs else "undetermined"
        if threshold_result == "within-threshold":
            return "satisfied" if population_complete and required_checks_complete and evidence_refs else "undetermined"
        return "undetermined"
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
