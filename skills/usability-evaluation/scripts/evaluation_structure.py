#!/usr/bin/env python3
"""Deterministic structure, reference closure, findings routing, and rendering.

The caller supplies semantic decisions. This module owns only fixed rows,
artifact-local refs, signatures, closure rules, cross references, and canonical
machine-owned Markdown.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any


ASPECTS = [
    ("purpose-understanding", "目的・理解可能性"),
    ("interaction", "interaction"),
    ("feedback", "feedback"),
    ("error-prevention-recovery", "error prevention / recovery"),
    ("accessibility", "accessibility"),
    ("visual-integrity", "visual integrity"),
    ("cross-pattern-flow", "cross-pattern / flow"),
]
ASPECT_KEYS = {key for key, _ in ASPECTS}
ASPECT_HANDLING = {"今回評価する", "対象外"}
STATUS = {"問題を確認", "問題なし", "判定不能", "対象外"}
BASIS = {"reference", "project-authority", "user-goal", "success-condition", "cross-state-consistency"}
REQUESTER_KINDS = {"usability-evaluation", "inspection-requirement", "wcag-procedure"}
EXECUTION_OWNERS = {"usability-inspection", "test-target-inspection", "test-execution"}
OBSERVATION_FIELDS = {
    "viewport.metrics",
    "element.geometry",
    "element.state",
    "document.location",
    "element.rendered-text",
    "element.control-value",
    "element.selected-values",
    "accessibility.semantics",
    "focus.state",
    "computed-style.properties",
    "responsive.conditions",
    "responsive.boundaries",
    "navigation.timing",
    "paint.timing",
    "interaction.timing",
    "screenshot.image",
}
REFERENCE_REF_RE = re.compile(r"^REF-\d{4,}$")
SOURCE_ITEM_REF_RE = re.compile(r"^SRC-\d{3,}-ITEM-\d{4,}$")
EVALUATION_REF_RE = re.compile(r"^EVAL-\d{3,}$")
PREDICATES = {
    "element-visible": {"target_ref"},
    "element-hidden": {"target_ref"},
    "text-present": {"expected_text"},
    "attribute-equals": {"target_ref", "attribute_name", "expected_value"},
    "aria-state-equals": {"target_ref", "state_name", "expected_value"},
    "element-enabled": {"target_ref"},
    "element-disabled": {"target_ref"},
    "url-changed": {"baseline_url"},
}
OPTIONAL_PREDICATE_FIELDS = {"text-present": {"within_target_ref"}}
ATTRIBUTE_NAMES = {"aria-current", "aria-label", "aria-live", "href", "name", "role", "title", "value"}
ARIA_STATE_NAMES = {"aria-checked", "aria-current", "aria-disabled", "aria-expanded", "aria-invalid", "aria-pressed", "aria-selected"}
EVALUATION_FIELDS = {
    "draft_key", "aspect_key", "target", "user_goal_task_flow_override", "basis", "observed_fact",
    "pattern_or_principle", "pattern_draft_key", "project_authority_refs", "applied_references", "reference_not_used_reason",
    "expected_characteristic", "difference", "expected_impact", "impact_basis", "judgment_reason",
    "additional_observation_links", "observed_user_impact", "evidence_refs",
    "test_rule_result_refs", "requirement_check_refs", "measurement_refs", "status",
    "status_reason", "routing", "finding_draft_key", "note", "follow_up_required",
}
CONDITION_FIELDS = {
    "target", "platform", "viewport_device", "locale", "current_state", "evidence_refs",
    "project_authority_refs", "adopted_design_system_refs", "limitations", "user", "user_goal_task_flow",
    "success_condition", "business_outcome", "business_rule",
}


class EvaluationStructureError(ValueError):
    pass


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def _string(value: Any, label: str, *, allow_dash: bool = False) -> str:
    if not isinstance(value, str) or not value.strip() or (not allow_dash and value.strip() == "-"):
        raise EvaluationStructureError(f"required_string:{label}")
    return value.strip()


def _optional_string(value: Any, label: str) -> str | None:
    if value is None or value == "" or value == "-":
        return None
    return _string(value, label)


def _list(value: Any, label: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value):
        raise EvaluationStructureError(f"invalid_string_array:{label}")
    values = [item.strip() for item in value]
    if len(values) != len(set(values)):
        raise EvaluationStructureError(f"duplicate_list_value:{label}")
    return values


def _sorted_refs(value: Any, label: str) -> list[str]:
    return sorted(_list(value, label))


def _enum(value: Any, allowed: set[str], label: str) -> str:
    text = _string(value, label)
    if text not in allowed:
        raise EvaluationStructureError(f"invalid_enum:{label}:{text}")
    return text


def _unknown_fields(value: dict[str, Any], allowed: set[str], label: str) -> None:
    unknown = set(value) - allowed
    if unknown:
        raise EvaluationStructureError(f"unknown_fields:{label}:{','.join(sorted(unknown))}")


def _known_ref(known: dict[str, set[str]], kind: str, ref: str, label: str) -> None:
    if ref not in known.get(kind, set()):
        raise EvaluationStructureError(f"unresolved_{kind}:{label}:{ref}")


def _known_refs(known: dict[str, set[str]], kind: str, values: list[str], label: str) -> None:
    for value in values:
        _known_ref(known, kind, value, label)


def _canonical_requester(kind: str, identity: Any) -> Any:
    if kind == "usability-evaluation":
        if isinstance(identity, str):
            return {"evaluation_draft_key_or_ref": _string(identity, "requester_identity")}
        if isinstance(identity, dict) and set(identity) == {"evaluation_draft_key"}:
            return {"evaluation_draft_key": _string(identity["evaluation_draft_key"], "requester_identity.evaluation_draft_key")}
        raise EvaluationStructureError("invalid_requester_identity:usability-evaluation")
    if kind == "inspection-requirement":
        if isinstance(identity, dict) and set(identity) in ({"requirement_ref"}, {"requirement_draft_key"}):
            key = next(iter(identity))
            return {key: _string(identity[key], f"requester_identity.{key}")}
        raise EvaluationStructureError("invalid_requester_identity:inspection-requirement")
    if kind == "wcag-procedure":
        required = {"criterion_evaluation_ref", "procedure_execution_ref"}
        if not isinstance(identity, dict) or set(identity) != required:
            raise EvaluationStructureError("invalid_requester_identity:wcag-procedure")
        return {key: _string(identity[key], f"requester_identity.{key}") for key in sorted(required)}
    raise EvaluationStructureError(f"invalid_requester_kind:{kind}")


def _canonical_predicate(field_key: str, predicate_key: str | None, payload: Any) -> tuple[str | None, Any]:
    if predicate_key is None:
        if payload not in (None, {}):
            raise EvaluationStructureError("predicate_payload_without_key")
        return None, None
    if field_key != "interaction.timing":
        raise EvaluationStructureError("predicate_only_allowed_for_interaction_timing")
    if predicate_key not in PREDICATES:
        raise EvaluationStructureError(f"unknown_predicate:{predicate_key}")
    if not isinstance(payload, dict):
        raise EvaluationStructureError("predicate_payload_must_be_object")
    required = PREDICATES[predicate_key]
    optional = OPTIONAL_PREDICATE_FIELDS.get(predicate_key, set())
    if set(payload) - required - optional or required - set(payload):
        raise EvaluationStructureError(f"predicate_payload_fields_mismatch:{predicate_key}")
    normalized: dict[str, Any] = {}
    for key in sorted(payload):
        value = payload[key]
        if not isinstance(value, str) or (key not in {"expected_text", "expected_value"} and not value.strip()):
            raise EvaluationStructureError(f"invalid_predicate_value:{predicate_key}:{key}")
        normalized[key] = value if key in {"expected_text", "expected_value"} else value.strip()
    if predicate_key == "attribute-equals" and normalized["attribute_name"] not in ATTRIBUTE_NAMES:
        raise EvaluationStructureError("predicate_attribute_outside_fixed_allowlist")
    if predicate_key == "aria-state-equals" and normalized["state_name"] not in ARIA_STATE_NAMES:
        raise EvaluationStructureError("predicate_aria_state_outside_fixed_allowlist")
    if predicate_key == "url-changed" and normalized["baseline_url"] != "capture-at-arm":
        raise EvaluationStructureError("url_changed_baseline_must_be_captured_by_browser_owner")
    return predicate_key, normalized


def _normalize_observation_link(
    row: dict[str, Any],
    *,
    known: dict[str, set[str]],
    draft_keys: set[str],
    existing_pairs: set[tuple[str, str]],
    invocation_pairs: set[tuple[str, str]],
    label: str,
) -> dict[str, Any]:
    allowed = {
        "request_draft_key", "requester_kind", "requester_identity", "execution_owner", "scope_ref",
        "target_ref", "target_draft_key", "state_description", "state_basis_refs",
        "current_document_identity", "observation_field_key", "predicate_key", "predicate_payload",
        "needed_observation", "reason", "input_evidence_refs", "request_signature",
        "input_evidence_fingerprint", "status", "inspection_request_ref", "owner_activity_ref",
        "returned_evidence_refs", "limitation",
    }
    _unknown_fields(row, allowed, label)
    draft = _string(row.get("request_draft_key"), f"{label}.request_draft_key")
    kind = _enum(row.get("requester_kind"), REQUESTER_KINDS, f"{label}.requester_kind")
    identity = _canonical_requester(kind, row.get("requester_identity"))
    if kind == "usability-evaluation":
        requester_key = identity.get("evaluation_draft_key")
        if requester_key is not None and requester_key not in draft_keys:
            raise EvaluationStructureError(f"requester_evaluation_draft_unresolved:{label}:{requester_key}")
        external_ref = identity.get("evaluation_draft_key_or_ref")
        if external_ref is not None and external_ref not in draft_keys and not EVALUATION_REF_RE.fullmatch(external_ref):
            raise EvaluationStructureError(f"requester_evaluation_identity_unresolved:{label}:{external_ref}")
    elif kind == "inspection-requirement":
        if "requirement_ref" in identity:
            _known_ref(known, "requirement_refs", identity["requirement_ref"], label)
        else:
            _known_ref(known, "requirement_draft_keys", identity["requirement_draft_key"], label)
    else:
        _known_ref(known, "criterion_evaluation_refs", identity["criterion_evaluation_ref"], label)
        _known_ref(known, "procedure_execution_refs", identity["procedure_execution_ref"], label)
    owner = _enum(row.get("execution_owner"), EXECUTION_OWNERS, f"{label}.execution_owner")
    scope_ref = _string(row.get("scope_ref"), f"{label}.scope_ref")
    _known_ref(known, "scope_refs", scope_ref, label)
    target_ref = _optional_string(row.get("target_ref"), f"{label}.target_ref")
    target_draft = _optional_string(row.get("target_draft_key"), f"{label}.target_draft_key")
    if target_ref and target_draft:
        raise EvaluationStructureError(f"target_identity_ambiguous:{label}")
    if target_ref:
        _known_ref(known, "target_refs", target_ref, label)
    if target_draft:
        _known_ref(known, "target_draft_keys", target_draft, label)
    target_identity = {"target_ref": target_ref} if target_ref else ({"target_draft_key": target_draft} if target_draft else None)
    state_basis_refs = _sorted_refs(row.get("state_basis_refs", []), f"{label}.state_basis_refs")
    _known_refs(known, "state_basis_refs", state_basis_refs, label)
    document = _optional_string(row.get("current_document_identity"), f"{label}.current_document_identity")
    field_key = _enum(row.get("observation_field_key"), OBSERVATION_FIELDS, f"{label}.observation_field_key")
    predicate_key = _optional_string(row.get("predicate_key"), f"{label}.predicate_key")
    predicate_key, predicate_payload = _canonical_predicate(field_key, predicate_key, row.get("predicate_payload"))
    input_evidence_refs = _sorted_refs(row.get("input_evidence_refs", []), f"{label}.input_evidence_refs")
    _known_refs(known, "evidence_refs", input_evidence_refs, label)
    signature_payload = {
        "requester_kind": kind,
        "requester_identity": identity,
        "execution_owner": owner,
        "scope_ref": scope_ref,
        "target_identity": target_identity,
        "state_basis_refs": state_basis_refs,
        "current_document_identity": document,
        "observation_field_key": field_key,
        "fixed_predicate_key": predicate_key,
        "canonical_predicate_payload": predicate_payload,
    }
    signature = _sha256(signature_payload)
    evidence_fingerprint = _sha256(input_evidence_refs)
    supplied_signature = _optional_string(row.get("request_signature"), f"{label}.request_signature")
    supplied_fingerprint = _optional_string(row.get("input_evidence_fingerprint"), f"{label}.input_evidence_fingerprint")
    if supplied_signature and supplied_signature != signature:
        raise EvaluationStructureError(f"request_signature_mismatch:{label}")
    if supplied_fingerprint and supplied_fingerprint != evidence_fingerprint:
        raise EvaluationStructureError(f"input_evidence_fingerprint_mismatch:{label}")
    pair = (signature, evidence_fingerprint)
    status = _enum(row.get("status"), {"completed", "unsupported", "no-progress", "blocked"}, f"{label}.status")
    duplicate = pair in existing_pairs or pair in invocation_pairs
    if duplicate and status != "no-progress":
        raise EvaluationStructureError(f"duplicate_additional_observation_must_be_no_progress:{label}")
    invocation_pairs.add(pair)
    request_ref = _optional_string(row.get("inspection_request_ref"), f"{label}.inspection_request_ref")
    activity_ref = _optional_string(row.get("owner_activity_ref"), f"{label}.owner_activity_ref")
    returned = _sorted_refs(row.get("returned_evidence_refs", []), f"{label}.returned_evidence_refs")
    _known_refs(known, "evidence_refs", returned, label)
    if owner == "usability-inspection":
        if activity_ref:
            raise EvaluationStructureError(f"wrong_owner_activity_ref:{label}")
        if status in {"completed", "no-progress"} and not request_ref:
            raise EvaluationStructureError(f"inspection_request_ref_required:{label}")
        if request_ref:
            _known_ref(known, "inspection_request_refs", request_ref, label)
    else:
        if request_ref:
            raise EvaluationStructureError(f"wrong_inspection_request_ref:{label}")
        if not activity_ref:
            raise EvaluationStructureError(f"owner_activity_ref_required:{label}")
        _known_ref(known, "owner_activity_refs", activity_ref, label)
    return {
        "request_draft_key": draft,
        "requester_kind": kind,
        "requester_identity": identity,
        "execution_owner": owner,
        "scope_ref": scope_ref,
        "target_identity": target_identity,
        "state_description": _string(row.get("state_description"), f"{label}.state_description"),
        "state_basis_refs": state_basis_refs,
        "current_document_identity": document,
        "observation_field_key": field_key,
        "predicate_key": predicate_key,
        "predicate_payload": predicate_payload,
        "needed_observation": _string(row.get("needed_observation"), f"{label}.needed_observation"),
        "reason": _string(row.get("reason"), f"{label}.reason"),
        "input_evidence_refs": input_evidence_refs,
        "request_signature": signature,
        "input_evidence_fingerprint": evidence_fingerprint,
        "status": status,
        "inspection_request_ref": request_ref,
        "owner_activity_ref": activity_ref,
        "returned_evidence_refs": returned,
        "limitation": _optional_string(row.get("limitation"), f"{label}.limitation"),
    }


def _known_refs_input(value: Any) -> dict[str, set[str]]:
    allowed = {
        "evidence_refs", "project_authority_refs", "test_rule_result_refs",
        "requirement_check_refs", "measurement_refs", "inspection_request_refs",
        "owner_activity_refs", "finding_refs", "scope_refs", "target_refs",
        "target_draft_keys", "state_basis_refs", "requirement_refs",
        "requirement_draft_keys", "criterion_evaluation_refs", "procedure_execution_refs",
    }
    if not isinstance(value, dict):
        raise EvaluationStructureError("known_refs_must_be_object")
    _unknown_fields(value, allowed, "known_refs")
    result = {}
    for key in allowed:
        result[key] = set(_list(value.get(key, []), f"known_refs.{key}"))
    return result


def _condition(value: Any, known: dict[str, set[str]]) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise EvaluationStructureError("condition_must_be_object")
    _unknown_fields(value, CONDITION_FIELDS, "condition")
    target = value.get("target")
    if not isinstance(target, dict):
        raise EvaluationStructureError("condition_target_must_be_object")
    if set(target) - {"ref", "name", "region"}:
        raise EvaluationStructureError("condition_target_unknown_fields")
    normalized_target = {
        "ref": _string(target.get("ref"), "condition.target.ref"),
        "name": _string(target.get("name"), "condition.target.name"),
        "region": _optional_string(target.get("region"), "condition.target.region"),
    }
    _known_ref(known, "target_refs", normalized_target["ref"], "condition.target")
    for field in ("platform", "viewport_device", "locale", "current_state"):
        _string(value.get(field), f"condition.{field}")
    evidence = _sorted_refs(value.get("evidence_refs", []), "condition.evidence_refs")
    authority = _sorted_refs(value.get("project_authority_refs", []), "condition.project_authority_refs")
    adopted = _sorted_refs(value.get("adopted_design_system_refs", []), "condition.adopted_design_system_refs")
    _known_refs(known, "evidence_refs", evidence, "condition")
    _known_refs(known, "project_authority_refs", authority, "condition")
    _known_refs(known, "project_authority_refs", adopted, "condition")
    limitations = _list(value.get("limitations", []), "condition.limitations")
    return {
        "target": normalized_target,
        "platform": value["platform"].strip(),
        "viewport_device": value["viewport_device"].strip(),
        "locale": value["locale"].strip(),
        "current_state": value["current_state"].strip(),
        "evidence_refs": evidence,
        "project_authority_refs": authority,
        "adopted_design_system_refs": adopted,
        "limitations": limitations,
        "user": value.get("user"),
        "user_goal_task_flow": value.get("user_goal_task_flow"),
        "success_condition": value.get("success_condition"),
        "business_outcome": value.get("business_outcome"),
        "business_rule": value.get("business_rule"),
    }


def _normalize_aspects(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise EvaluationStructureError("aspects_must_be_array")
    rows_by_key: dict[str, dict[str, Any]] = {}
    for row in value:
        if not isinstance(row, dict) or set(row) - {"aspect_key", "handling", "reason"}:
            raise EvaluationStructureError("invalid_aspect_decision")
        key = _enum(row.get("aspect_key"), ASPECT_KEYS, "aspect_key")
        if key in rows_by_key:
            raise EvaluationStructureError(f"duplicate_aspect_decision:{key}")
        handling = _enum(row.get("handling"), ASPECT_HANDLING, f"aspect.{key}.handling")
        reason = _optional_string(row.get("reason"), f"aspect.{key}.reason")
        if handling == "対象外" and not reason:
            raise EvaluationStructureError(f"out_of_scope_reason_required:{key}")
        if handling == "今回評価する" and reason:
            raise EvaluationStructureError(f"evaluated_aspect_must_not_have_out_of_scope_reason:{key}")
        rows_by_key[key] = {"aspect_key": key, "handling": handling, "reason": reason}
    missing = ASPECT_KEYS - set(rows_by_key)
    if missing:
        raise EvaluationStructureError(f"missing_aspect_decisions:{','.join(sorted(missing))}")
    return [{"aspect_key": key, "aspect": name, **rows_by_key[key]} for key, name in ASPECTS]


def _normalize_patterns(value: Any, reference_items: dict[str, set[str]], known: dict[str, set[str]], condition: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    if not isinstance(value, list):
        raise EvaluationStructureError("pattern_identifications_must_be_array")
    rows: list[dict[str, Any]] = []
    by_key: dict[str, dict[str, Any]] = {}
    for item in value:
        allowed = {"draft_key", "target_ref", "pattern_name", "purpose", "user_goal_relationship", "applicability", "source_refs", "not_identified_reason"}
        if not isinstance(item, dict):
            raise EvaluationStructureError("pattern_identification_not_object")
        _unknown_fields(item, allowed, "pattern_identification")
        key = _string(item.get("draft_key"), "pattern_identification.draft_key")
        if key in by_key:
            raise EvaluationStructureError(f"duplicate_pattern_draft_key:{key}")
        target_ref = _string(item.get("target_ref"), f"pattern.{key}.target_ref")
        _known_ref(known, "target_refs", target_ref, key)
        pattern_name = _optional_string(item.get("pattern_name"), f"pattern.{key}.pattern_name")
        source_refs_input = item.get("source_refs", [])
        if not isinstance(source_refs_input, list):
            raise EvaluationStructureError(f"pattern_source_refs_must_be_array:{key}")
        source_refs = []
        seen = set()
        for source_ref in source_refs_input:
            if not isinstance(source_ref, dict) or set(source_ref) != {"reference_entry_ref", "source_item_ref"}:
                raise EvaluationStructureError(f"invalid_pattern_source_ref:{key}")
            entry = _string(source_ref["reference_entry_ref"], f"pattern.{key}.reference_entry_ref")
            source_item = _string(source_ref["source_item_ref"], f"pattern.{key}.source_item_ref")
            if entry not in reference_items or source_item not in reference_items[entry]:
                raise EvaluationStructureError(f"pattern_source_ref_unresolved:{key}:{entry}:{source_item}")
            if (entry, source_item) in seen:
                raise EvaluationStructureError(f"duplicate_pattern_source_ref:{key}")
            seen.add((entry, source_item))
            source_refs.append({"reference_entry_ref": entry, "source_item_ref": source_item})
        source_refs.sort(key=lambda row: (row["reference_entry_ref"], row["source_item_ref"]))
        not_identified = _optional_string(item.get("not_identified_reason"), f"pattern.{key}.not_identified_reason")
        if pattern_name:
            if not source_refs:
                raise EvaluationStructureError(f"identified_pattern_requires_source:{key}")
            if not_identified:
                raise EvaluationStructureError(f"identified_pattern_has_not_identified_reason:{key}")
            purpose = _string(item.get("purpose"), f"pattern.{key}.purpose")
            applicability = _string(item.get("applicability"), f"pattern.{key}.applicability")
        else:
            if source_refs or not not_identified:
                raise EvaluationStructureError(f"unidentified_pattern_requires_reason:{key}")
            purpose = _optional_string(item.get("purpose"), f"pattern.{key}.purpose")
            applicability = _optional_string(item.get("applicability"), f"pattern.{key}.applicability")
        relationship = _optional_string(item.get("user_goal_relationship"), f"pattern.{key}.user_goal_relationship")
        if relationship and condition["user_goal_task_flow"] in (None, "", "-"):
            raise EvaluationStructureError(f"pattern_user_goal_relationship_without_context:{key}")
        row = {
            "draft_key": key,
            "target_ref": target_ref,
            "pattern_name": pattern_name,
            "purpose": purpose,
            "user_goal_relationship": relationship,
            "applicability": applicability,
            "source_refs": source_refs,
            "not_identified_reason": not_identified,
        }
        rows.append(row)
        by_key[key] = row
    return rows, by_key


def _normalize_evaluation(
    row: dict[str, Any],
    *,
    number: int,
    condition: dict[str, Any],
    aspects: dict[str, dict[str, Any]],
    reference_items: dict[str, set[str]],
    pattern_by_key: dict[str, dict[str, Any]],
    known: dict[str, set[str]],
    finding_refs: dict[str, str],
    draft_keys: set[str],
    existing_observation_pairs: set[tuple[str, str]],
    invocation_observation_pairs: set[tuple[str, str]],
) -> dict[str, Any]:
    _unknown_fields(row, EVALUATION_FIELDS, "evaluation")
    draft_key = _string(row.get("draft_key"), "evaluation.draft_key")
    aspect_key = _enum(row.get("aspect_key"), ASPECT_KEYS, f"evaluation.{draft_key}.aspect_key")
    aspect_row = aspects[aspect_key]
    if aspect_row["handling"] != "今回評価する":
        raise EvaluationStructureError(f"evaluation_for_out_of_scope_aspect:{draft_key}")
    target = _string(row.get("target"), f"evaluation.{draft_key}.target")
    basis = row.get("basis")
    if not isinstance(basis, list) or not basis:
        raise EvaluationStructureError(f"evaluation_basis_required:{draft_key}")
    normalized_basis = []
    for item in basis:
        normalized_basis.append(_enum(item, BASIS, f"evaluation.{draft_key}.basis"))
    if len(normalized_basis) != len(set(normalized_basis)):
        raise EvaluationStructureError(f"duplicate_evaluation_basis:{draft_key}")
    status = _enum(row.get("status"), STATUS, f"evaluation.{draft_key}.status")
    follow_up = row.get("follow_up_required")
    if not isinstance(follow_up, bool):
        raise EvaluationStructureError(f"follow_up_required_must_be_boolean:{draft_key}")
    observed = _string(row.get("observed_fact"), f"evaluation.{draft_key}.observed_fact")
    project_authority_refs = _sorted_refs(row.get("project_authority_refs", []), f"evaluation.{draft_key}.project_authority_refs")
    evidence_refs = _sorted_refs(row.get("evidence_refs", []), f"evaluation.{draft_key}.evidence_refs")
    if not evidence_refs:
        raise EvaluationStructureError(f"evaluation_evidence_required:{draft_key}")
    _known_refs(known, "project_authority_refs", project_authority_refs, draft_key)
    _known_refs(known, "evidence_refs", evidence_refs, draft_key)
    user_goal_override = _optional_string(row.get("user_goal_task_flow_override"), f"{draft_key}.user_goal_task_flow_override")
    if user_goal_override is not None and condition["user_goal_task_flow"] in (None, "", "-"):
        raise EvaluationStructureError(f"user_goal_override_without_condition:{draft_key}")
    applied = row.get("applied_references", [])
    if not isinstance(applied, list):
        raise EvaluationStructureError(f"applied_references_must_be_array:{draft_key}")
    applied_rows = []
    seen_reference_pairs = set()
    for item in applied:
        if not isinstance(item, dict) or set(item) - {"reference_entry_ref", "source_item_ref", "reference_position", "authority_binding_applied", "project_authority_refs"}:
            raise EvaluationStructureError(f"invalid_applied_reference:{draft_key}")
        entry_ref = _string(item.get("reference_entry_ref"), f"{draft_key}.reference_entry_ref")
        source_item_ref = _string(item.get("source_item_ref"), f"{draft_key}.source_item_ref")
        position = _string(item.get("reference_position"), f"{draft_key}.reference_position")
        if entry_ref not in reference_items or source_item_ref not in reference_items[entry_ref]:
            raise EvaluationStructureError(f"applied_reference_item_unresolved:{draft_key}:{entry_ref}:{source_item_ref}")
        pair = (entry_ref, source_item_ref)
        if pair in seen_reference_pairs:
            raise EvaluationStructureError(f"duplicate_applied_reference:{draft_key}:{entry_ref}:{source_item_ref}")
        seen_reference_pairs.add(pair)
        binding = item.get("authority_binding_applied", False)
        if not isinstance(binding, bool):
            raise EvaluationStructureError(f"authority_binding_applied_must_be_boolean:{draft_key}")
        applied_authority = _sorted_refs(item.get("project_authority_refs", []), f"{draft_key}.applied_reference.project_authority_refs")
        _known_refs(known, "project_authority_refs", applied_authority, draft_key)
        if binding and not applied_authority:
            raise EvaluationStructureError(f"project_binding_authority_required:{draft_key}:{entry_ref}")
        applied_rows.append({
            "reference_entry_ref": entry_ref,
            "source_item_ref": source_item_ref,
            "reference_position": position,
            "authority_binding_applied": binding,
            "project_authority_refs": applied_authority,
        })
    applied_rows.sort(key=lambda item: (item["reference_entry_ref"], item["source_item_ref"]))
    if "reference" in normalized_basis and not applied_rows:
        raise EvaluationStructureError(f"reference_basis_requires_applied_reference:{draft_key}")
    if "project-authority" in normalized_basis and not project_authority_refs:
        raise EvaluationStructureError(f"project_authority_basis_requires_ref:{draft_key}")
    if "user-goal" in normalized_basis and condition["user_goal_task_flow"] in (None, "", "-"):
        raise EvaluationStructureError(f"user_goal_basis_without_context:{draft_key}")
    if "success-condition" in normalized_basis and not any(condition[key] not in (None, "", "-") for key in ("success_condition", "business_outcome", "business_rule")):
        raise EvaluationStructureError(f"success_condition_basis_without_context:{draft_key}")
    if "cross-state-consistency" in normalized_basis:
        if not _optional_string(row.get("judgment_reason"), f"{draft_key}.judgment_reason") or len(evidence_refs) < 1:
            raise EvaluationStructureError(f"cross_state_basis_missing_reason_or_evidence:{draft_key}")
    no_reference_reason = _optional_string(row.get("reference_not_used_reason"), f"{draft_key}.reference_not_used_reason")
    if not applied_rows and not no_reference_reason:
        raise EvaluationStructureError(f"reference_not_used_reason_required:{draft_key}")
    if applied_rows and no_reference_reason:
        raise EvaluationStructureError(f"reference_not_used_reason_with_applied_reference:{draft_key}")
    judgment_reason = _optional_string(row.get("judgment_reason"), f"{draft_key}.judgment_reason")
    if not applied_rows and not judgment_reason:
        raise EvaluationStructureError(f"reference_free_evaluation_requires_judgment_reason:{draft_key}")
    test_rule_refs = _sorted_refs(row.get("test_rule_result_refs", []), f"{draft_key}.test_rule_result_refs")
    requirement_refs = _sorted_refs(row.get("requirement_check_refs", []), f"{draft_key}.requirement_check_refs")
    measurement_refs = _sorted_refs(row.get("measurement_refs", []), f"{draft_key}.measurement_refs")
    _known_refs(known, "test_rule_result_refs", test_rule_refs, draft_key)
    _known_refs(known, "requirement_check_refs", requirement_refs, draft_key)
    _known_refs(known, "measurement_refs", measurement_refs, draft_key)
    additional_input = row.get("additional_observation_links", [])
    if not isinstance(additional_input, list):
        raise EvaluationStructureError(f"additional_observation_links_must_be_array:{draft_key}")
    links = []
    for index, link in enumerate(additional_input, start=1):
        if not isinstance(link, dict):
            raise EvaluationStructureError(f"additional_observation_link_not_object:{draft_key}")
        links.append(_normalize_observation_link(
            link,
            known=known,
            draft_keys=draft_keys,
            existing_pairs=existing_observation_pairs,
            invocation_pairs=invocation_observation_pairs,
            label=f"{draft_key}.observation.{index}",
        ))
    status_reason = _optional_string(row.get("status_reason"), f"{draft_key}.status_reason")
    if status in {"判定不能", "対象外"} and not status_reason:
        raise EvaluationStructureError(f"status_reason_required:{draft_key}")
    impact = _string(row.get("expected_impact"), f"{draft_key}.expected_impact")
    impact_basis = _string(row.get("impact_basis"), f"{draft_key}.impact_basis")
    if status == "問題を確認" and (observed == "-" or not evidence_refs or impact == "-" or impact_basis == "-"):
        raise EvaluationStructureError(f"problem_finding_basis_incomplete:{draft_key}")
    observed_user_impact = row.get("observed_user_impact")
    if observed_user_impact not in (None, "", "-"):
        if not isinstance(observed_user_impact, dict) or set(observed_user_impact) != {"statement", "evidence_refs"}:
            raise EvaluationStructureError(f"observed_user_impact_schema_invalid:{draft_key}")
        impact_evidence = _sorted_refs(observed_user_impact["evidence_refs"], f"{draft_key}.observed_user_impact.evidence_refs")
        if not impact_evidence:
            raise EvaluationStructureError(f"observed_user_impact_evidence_required:{draft_key}")
        _known_refs(known, "evidence_refs", impact_evidence, draft_key)
        observed_user_impact = {"statement": _string(observed_user_impact["statement"], f"{draft_key}.observed_user_impact.statement"), "evidence_refs": impact_evidence}
    finding_draft_key = _optional_string(row.get("finding_draft_key"), f"{draft_key}.finding_draft_key")
    finding_required = status == "問題を確認" and follow_up or status == "判定不能" and follow_up
    finding_ref = None
    if finding_required:
        if not finding_draft_key or finding_draft_key not in finding_refs:
            raise EvaluationStructureError(f"required_finding_unresolved:{draft_key}")
        finding_ref = finding_refs[finding_draft_key]
        _known_ref(known, "finding_refs", finding_ref, draft_key)
    elif finding_draft_key:
        raise EvaluationStructureError(f"finding_not_allowed_for_status:{draft_key}")
    goal_flow = condition["user_goal_task_flow"]
    if user_goal_override is None and goal_flow not in (None, "", "-"):
        goal_flow = goal_flow
    elif user_goal_override is not None:
        goal_flow = user_goal_override
    pattern_draft_key = _optional_string(row.get("pattern_draft_key"), f"{draft_key}.pattern_draft_key")
    if pattern_draft_key is not None and pattern_draft_key not in pattern_by_key:
        raise EvaluationStructureError(f"evaluation_pattern_unresolved:{draft_key}:{pattern_draft_key}")
    return {
        "evaluation_ref": f"EVAL-{number:03d}",
        "draft_key": draft_key,
        "aspect_key": aspect_key,
        "aspect": aspects[aspect_key]["aspect"],
        "target": target,
        "user_goal_task_flow": goal_flow,
        "basis": normalized_basis,
        "observed_fact": observed,
        "pattern_or_principle": _optional_string(row.get("pattern_or_principle"), f"{draft_key}.pattern_or_principle"),
        "pattern_draft_key": pattern_draft_key,
        "project_authority_refs": project_authority_refs,
        "applied_references": applied_rows,
        "reference_not_used_reason": no_reference_reason,
        "expected_characteristic": _string(row.get("expected_characteristic"), f"{draft_key}.expected_characteristic", allow_dash=True),
        "difference": _string(row.get("difference"), f"{draft_key}.difference", allow_dash=True),
        "expected_impact": impact,
        "impact_basis": impact_basis,
        "judgment_reason": judgment_reason,
        "additional_observation_links": links,
        "observed_user_impact": observed_user_impact,
        "evidence_refs": evidence_refs,
        "test_rule_result_refs": test_rule_refs,
        "requirement_check_refs": requirement_refs,
        "measurement_refs": measurement_refs,
        "status": status,
        "status_reason": status_reason,
        "routing": _optional_string(row.get("routing"), f"{draft_key}.routing"),
        "finding_required": bool(finding_required),
        "finding_ref": finding_ref,
        "follow_up_required": follow_up,
        "note": _optional_string(row.get("note"), f"{draft_key}.note"),
    }


def _escape_cell(value: Any) -> str:
    if value is None or value == "":
        return "-"
    if isinstance(value, (dict, list)):
        value = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return str(value).replace("\\", "\\\\").replace("|", "\\|").replace("\r", " ").replace("\n", " ").strip() or "-"


def _render_machine_sections(condition: dict[str, Any], patterns: list[dict[str, Any]], aspects: list[dict[str, Any]], evaluations: list[dict[str, Any]], summary: dict[str, Any]) -> str:
    lines = [
        "## Evaluation Conditions",
        "",
        "| Field | Value |",
        "| --- | --- |",
    ]
    for key, value in condition.items():
        lines.append(f"| {_escape_cell(key)} | {_escape_cell(value)} |")
    lines.extend([
        "",
        "## Pattern Identification",
        "",
        "| Draft Key | Target Ref | Pattern | Purpose | User Goal Relationship | Applicability | Source Refs | Reason Not Identified |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ])
    for row in patterns:
        values = tuple(row[key] for key in ("draft_key", "target_ref", "pattern_name", "purpose", "user_goal_relationship", "applicability", "source_refs", "not_identified_reason"))
        lines.append("| " + " | ".join(_escape_cell(value) for value in values) + " |")
    lines.extend([
        "",
        "## Evaluation Scope Closure",
        "",
        "| Aspect Key | Aspect | Handling | Reason |",
        "| --- | --- | --- | --- |",
    ])
    for row in aspects:
        lines.append("| " + " | ".join(_escape_cell(row[key]) for key in ("aspect_key", "aspect", "handling", "reason")) + " |")
    lines.extend([
        "",
        "## UI / UX Evaluation Results",
        "",
        "| Evaluation Ref | Aspect Key | Draft Key | Status | Finding Ref | Machine Normalized Record |",
        "| --- | --- | --- | --- | --- | --- |",
    ])
    for row in evaluations:
        values = (row["evaluation_ref"], row["aspect_key"], row["draft_key"], row["status"], row["finding_ref"], row)
        lines.append("| " + " | ".join(_escape_cell(value) for value in values) + " |")
    lines.extend([
        "",
        "## Evaluation Summary",
        "",
        "| Metric | Count |",
        "| --- | ---: |",
    ])
    for key in sorted(summary):
        lines.append(f"| {_escape_cell(key)} | {_escape_cell(summary[key])} |")
    return "\n".join(lines) + "\n"


def materialize(input_value: dict[str, Any]) -> dict[str, Any]:
    allowed = {"condition", "aspects", "pattern_identifications", "evaluations", "reference_catalog", "known_refs", "findings", "existing_additional_observation_links"}
    _unknown_fields(input_value, allowed, "root")
    known = _known_refs_input(input_value.get("known_refs", {}))
    condition = _condition(input_value.get("condition"), known)
    aspects = _normalize_aspects(input_value.get("aspects"))
    aspect_map = {row["aspect_key"]: row for row in aspects}
    raw_catalog = input_value.get("reference_catalog")
    if not isinstance(raw_catalog, dict):
        raise EvaluationStructureError("reference_catalog_must_be_object")
    reference_items = {str(entry): set(_list(items, f"reference_catalog.{entry}")) for entry, items in raw_catalog.items()}
    for entry_ref, item_refs in reference_items.items():
        if not REFERENCE_REF_RE.fullmatch(entry_ref):
            raise EvaluationStructureError(f"invalid_reference_entry_ref:{entry_ref}")
        if not item_refs or any(not SOURCE_ITEM_REF_RE.fullmatch(item_ref) for item_ref in item_refs):
            raise EvaluationStructureError(f"invalid_reference_source_items:{entry_ref}")
    patterns, pattern_by_key = _normalize_patterns(input_value.get("pattern_identifications", []), reference_items, known, condition)
    findings_input = input_value.get("findings", [])
    if not isinstance(findings_input, list):
        raise EvaluationStructureError("findings_must_be_array")
    finding_refs: dict[str, str] = {}
    for item in findings_input:
        if not isinstance(item, dict) or set(item) != {"draft_key", "finding_ref"}:
            raise EvaluationStructureError("invalid_finding_link")
        key = _string(item["draft_key"], "finding.draft_key")
        ref = _string(item["finding_ref"], "finding.finding_ref")
        if key in finding_refs or ref in finding_refs.values():
            raise EvaluationStructureError(f"duplicate_finding_link:{key}")
        _known_ref(known, "finding_refs", ref, key)
        finding_refs[key] = ref
    evaluations_input = input_value.get("evaluations")
    if not isinstance(evaluations_input, list):
        raise EvaluationStructureError("evaluations_must_be_array")
    draft_keys = []
    for item in evaluations_input:
        if not isinstance(item, dict):
            raise EvaluationStructureError("evaluation_not_object")
        draft_keys.append(_string(item.get("draft_key"), "evaluation.draft_key"))
    if len(draft_keys) != len(set(draft_keys)):
        raise EvaluationStructureError("duplicate_evaluation_draft_key")
    request_draft_keys: list[str] = []
    for item in evaluations_input:
        links = item.get("additional_observation_links", [])
        if not isinstance(links, list):
            raise EvaluationStructureError(f"additional_observation_links_must_be_array:{item.get('draft_key')}")
        for link in links:
            if not isinstance(link, dict):
                raise EvaluationStructureError(f"additional_observation_link_not_object:{item.get('draft_key')}")
            request_draft_keys.append(_string(link.get("request_draft_key"), "request_draft_key"))
    if len(request_draft_keys) != len(set(request_draft_keys)):
        raise EvaluationStructureError("duplicate_observation_request_draft_key")
    evaluation_counts = {key: 0 for key in ASPECT_KEYS}
    for item in evaluations_input:
        key = _enum(item.get("aspect_key"), ASPECT_KEYS, "evaluation.aspect_key")
        if aspect_map[key]["handling"] == "今回評価する":
            evaluation_counts[key] += 1
    missing_evaluations = [key for key, count in evaluation_counts.items() if aspect_map[key]["handling"] == "今回評価する" and count == 0]
    if missing_evaluations:
        raise EvaluationStructureError(f"evaluated_aspect_without_result:{','.join(missing_evaluations)}")
    existing_pairs: set[tuple[str, str]] = set()
    prior = input_value.get("existing_additional_observation_links", [])
    if not isinstance(prior, list):
        raise EvaluationStructureError("existing_additional_observation_links_must_be_array")
    for item in prior:
        if not isinstance(item, dict):
            raise EvaluationStructureError("existing_observation_link_not_object")
        signature = _string(item.get("request_signature"), "existing.request_signature")
        fingerprint = _string(item.get("input_evidence_fingerprint"), "existing.input_evidence_fingerprint")
        existing_pairs.add((signature, fingerprint))
    invocation_pairs: set[tuple[str, str]] = set()
    normalized = []
    for number, row in enumerate(evaluations_input, start=1):
        normalized.append(_normalize_evaluation(
            row,
            number=number,
            condition=condition,
            aspects=aspect_map,
            reference_items=reference_items,
            pattern_by_key=pattern_by_key,
            known=known,
            finding_refs=finding_refs,
            draft_keys=set(draft_keys),
            existing_observation_pairs=existing_pairs,
            invocation_observation_pairs=invocation_pairs,
        ))
    used_finding_refs = {row["finding_ref"] for row in normalized if row["finding_required"]}
    unused_finding_refs = set(finding_refs.values()) - used_finding_refs
    if unused_finding_refs:
        raise EvaluationStructureError(f"orphan_finding_links:{','.join(sorted(unused_finding_refs))}")
    summary = {
        "evaluated_aspects": sum(row["handling"] == "今回評価する" for row in aspects),
        "out_of_scope_aspects": sum(row["handling"] == "対象外" for row in aspects),
        "evaluation_count": len(normalized),
        "finding_count": sum(row["finding_required"] for row in normalized),
        "issue_count": sum(row["status"] == "問題を確認" for row in normalized),
        "no_issue_count": sum(row["status"] == "問題なし" for row in normalized),
        "undetermined_count": sum(row["status"] == "判定不能" for row in normalized),
        "out_of_scope_result_count": sum(row["status"] == "対象外" for row in normalized),
    }
    summary["pattern_identification_count"] = len(patterns)
    markdown = _render_machine_sections(condition, patterns, aspects, normalized, summary)
    return {
        "condition": condition,
        "aspects": aspects,
        "pattern_identifications": patterns,
        "evaluations": normalized,
        "findings": [{"draft_key": key, "finding_ref": finding_refs[key]} for key in sorted(finding_refs)],
        "summary": summary,
        "machine_owned_markdown": markdown,
        "issues": [],
    }


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise EvaluationStructureError(f"invalid_json:{path}") from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Materialize evaluation refs, closure, finding routing, and Markdown.")
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("materialize")
    build.add_argument("--input", type=Path, required=True)
    build.add_argument("--output-markdown", type=Path)
    args = parser.parse_args(argv)
    try:
        input_value = _read_json(args.input)
        if not isinstance(input_value, dict):
            raise EvaluationStructureError("input_must_be_object")
        result = materialize(input_value)
        if args.output_markdown:
            args.output_markdown.parent.mkdir(parents=True, exist_ok=True)
            args.output_markdown.write_text(result["machine_owned_markdown"], encoding="utf-8", newline="\n")
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        print(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
        return 0
    except (EvaluationStructureError, OSError) as exc:
        print(f"evaluation_structure:{exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
