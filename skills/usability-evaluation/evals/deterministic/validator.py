from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from scripts.skills.evals.deterministic.markdown_parser import find_table, parse_tables
from scripts.skills.evals.deterministic.result import EvalResult


ASPECTS = [
    ("purpose-understanding", "目的・理解可能性"),
    ("interaction", "interaction"),
    ("feedback", "feedback"),
    ("error-prevention-recovery", "error prevention / recovery"),
    ("accessibility", "accessibility"),
    ("visual-integrity", "visual integrity"),
    ("cross-pattern-flow", "cross-pattern / flow"),
]
STATUS = {"問題を確認", "問題なし", "判定不能", "対象外"}
BASIS = {"reference", "project-authority", "user-goal", "success-condition", "cross-state-consistency"}
REQUESTER_KINDS = {"usability-evaluation", "inspection-requirement", "wcag-procedure"}
OWNERS = {"usability-inspection", "test-target-inspection", "test-execution"}
OBSERVATION_FIELDS = {
    "viewport.metrics", "element.geometry", "element.state", "document.location",
    "element.rendered-text", "element.control-value", "element.selected-values",
    "accessibility.semantics", "focus.state", "computed-style.properties",
    "responsive.conditions", "responsive.boundaries", "navigation.timing",
    "paint.timing", "interaction.timing", "screenshot.image",
}
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
ATTRIBUTE_NAMES = {"aria-current", "aria-label", "aria-live", "href", "name", "role", "title", "value"}
ARIA_STATE_NAMES = {"aria-checked", "aria-current", "aria-disabled", "aria-expanded", "aria-invalid", "aria-pressed", "aria-selected"}
REF = re.compile(r"^EVAL-(\d{3,})$")
RECORD_FIELDS = {
    "evaluation_ref", "aspect_key", "draft_key", "user_goal_task_flow", "target", "basis",
    "aspect", "observed_fact", "pattern_or_principle", "pattern_draft_key", "project_authority_refs",
    "applied_references", "reference_not_used_reason", "expected_characteristic", "difference",
    "expected_impact", "impact_basis", "judgment_reason", "additional_observation_links",
    "observed_user_impact", "evidence_refs", "test_rule_result_refs", "requirement_check_refs",
    "measurement_refs", "status", "status_reason", "routing", "finding_required", "finding_ref",
    "note", "follow_up_required",
}
APPLIED_REFERENCE_FIELDS = {
    "reference_entry_ref", "source_item_ref", "reference_position", "authority_binding_applied",
    "project_authority_refs",
}


def _value(row: dict[str, str], field: str) -> str:
    return (row.get(field) or "").strip().strip(chr(96))


def _rows(table) -> list[dict[str, str]]:
    return table.rows if table else []


def _hash(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _known(expected: dict[str, Any], kind: str) -> set[str]:
    values = expected.get("known_refs", {}).get(kind, [])
    return set(values) if isinstance(values, list) else set()


def _cross_refs(values: Any, known: set[str], label: str, errors: list[str]) -> None:
    if not isinstance(values, list) or any(not isinstance(value, str) for value in values):
        errors.append(f"invalid_ref_array:{label}")
        return
    for value in values:
        if value not in known:
            errors.append(f"unresolved_ref:{label}:{value}")


def _validate_signature(link: dict[str, Any], label: str, errors: list[str]) -> None:
    kind = link.get("requester_kind")
    owner = link.get("execution_owner")
    field = link.get("observation_field_key")
    predicate = link.get("predicate_key")
    payload = link.get("predicate_payload")
    if kind not in REQUESTER_KINDS:
        errors.append(f"invalid_requester_kind:{label}")
    if owner not in OWNERS:
        errors.append(f"invalid_execution_owner:{label}")
    if field not in OBSERVATION_FIELDS:
        errors.append(f"invalid_observation_field:{label}")
    if predicate is None:
        if payload is not None:
            errors.append(f"predicate_payload_without_key:{label}")
        canonical_predicate = None
    else:
        if field != "interaction.timing" or predicate not in PREDICATES or not isinstance(payload, dict):
            errors.append(f"invalid_predicate:{label}")
        else:
            required = PREDICATES[predicate]
            optional = {"within_target_ref"} if predicate == "text-present" else set()
            if set(payload) - required - optional or required - set(payload):
                errors.append(f"predicate_fields_mismatch:{label}")
            if any(not isinstance(value, str) or (key not in {"expected_text", "expected_value"} and not value.strip()) for key, value in payload.items()):
                errors.append(f"predicate_value_invalid:{label}")
            if predicate == "attribute-equals" and payload.get("attribute_name") not in ATTRIBUTE_NAMES:
                errors.append(f"predicate_attribute_outside_fixed_allowlist:{label}")
            if predicate == "aria-state-equals" and payload.get("state_name") not in ARIA_STATE_NAMES:
                errors.append(f"predicate_aria_state_outside_fixed_allowlist:{label}")
            if predicate == "url-changed" and payload.get("baseline_url") != "capture-at-arm":
                errors.append(f"url_changed_baseline_not_browser_owned:{label}")
        canonical_predicate = payload
    state_basis_refs = link.get("state_basis_refs")
    if not isinstance(state_basis_refs, list) or any(not isinstance(value, str) for value in state_basis_refs):
        errors.append(f"state_basis_refs_invalid:{label}")
        state_basis_refs = []
    elif state_basis_refs != sorted(set(state_basis_refs)):
        errors.append(f"state_basis_refs_not_canonical:{label}")
    input_refs = link.get("input_evidence_refs")
    if not isinstance(input_refs, list) or any(not isinstance(value, str) for value in input_refs):
        errors.append(f"input_evidence_refs_invalid:{label}")
        input_refs = []
    elif input_refs != sorted(set(input_refs)):
        errors.append(f"input_evidence_refs_not_canonical:{label}")
    signature_payload = {
        "requester_kind": kind,
        "requester_identity": link.get("requester_identity"),
        "execution_owner": owner,
        "scope_ref": link.get("scope_ref"),
        "target_identity": link.get("target_identity"),
        "state_basis_refs": state_basis_refs,
        "current_document_identity": link.get("current_document_identity"),
        "observation_field_key": field,
        "fixed_predicate_key": predicate,
        "canonical_predicate_payload": canonical_predicate,
    }
    if link.get("request_signature") != _hash(signature_payload):
        errors.append(f"request_signature_mismatch:{label}")
    if link.get("input_evidence_fingerprint") != _hash(input_refs):
        errors.append(f"input_evidence_fingerprint_mismatch:{label}")


def validate(text: str, expected: dict[str, Any], eval_id: str) -> EvalResult:
    result = EvalResult("usability-evaluation", eval_id)
    errors: list[str] = []
    try:
        tables = parse_tables(text)
    except Exception as exc:
        result.add("UE-D001", False, "machine-owned output tables parse", evidence=str(exc))
        return result

    table_specs = {
        "conditions": ("Evaluation Conditions", ("Field", "Value")),
        "patterns": ("Pattern Identification", ("Draft Key", "Target Ref", "Pattern", "Purpose", "User Goal Relationship", "Applicability", "Source Refs", "Reason Not Identified")),
        "aspects": ("Evaluation Scope Closure", ("Aspect Key", "Aspect", "Handling", "Reason")),
        "evaluations": ("UI / UX Evaluation Results", ("Evaluation Ref", "Aspect Key", "Draft Key", "Status", "Finding Ref", "Machine Normalized Record")),
        "summary": ("Evaluation Summary", ("Metric", "Count")),
    }
    found = {}
    for key, (section, headers) in table_specs.items():
        found[key] = find_table(tables, section_contains=section, required_headers=headers)
    missing = [key for key, table in found.items() if table is None]
    result.add("UE-D001", not missing, "condition, pattern, fixed closure, evaluation, and summary tables exist", evidence={"missing": missing} if missing else None)
    if missing:
        return result

    condition_rows = _rows(found["conditions"])
    condition = {_value(row, "Field"): _value(row, "Value") for row in condition_rows}
    required_condition = {"target", "platform", "viewport_device", "locale", "current_state", "evidence_refs", "project_authority_refs", "adopted_design_system_refs", "limitations"}
    missing_condition = sorted(required_condition - set(condition))
    result.add("UE-D002", not missing_condition, "evaluation conditions preserve required scope and context", evidence=missing_condition or None)
    if condition.get("evidence_refs"):
        try:
            refs = json.loads(condition["evidence_refs"])
            _cross_refs(refs, _known(expected, "evidence_refs"), "condition.evidence_refs", errors)
        except json.JSONDecodeError:
            errors.append("condition_evidence_refs_not_json")
    if condition.get("project_authority_refs"):
        try:
            refs = json.loads(condition["project_authority_refs"])
            _cross_refs(refs, _known(expected, "project_authority_refs"), "condition.project_authority_refs", errors)
        except json.JSONDecodeError:
            errors.append("condition_authority_refs_not_json")

    aspect_rows = _rows(found["aspects"])
    actual_aspects = [(_value(row, "Aspect Key"), _value(row, "Aspect")) for row in aspect_rows]
    expected_aspects = [(key, name) for key, name in ASPECTS]
    if actual_aspects != expected_aspects:
        errors.append("aspect_rows_missing_reordered_or_renamed")
    aspect_handling: dict[str, str] = {}
    for row in aspect_rows:
        key = _value(row, "Aspect Key")
        handling = _value(row, "Handling")
        reason = _value(row, "Reason")
        if handling not in {"今回評価する", "対象外"}:
            errors.append(f"invalid_aspect_handling:{key}")
        if handling == "対象外" and not reason:
            errors.append(f"out_of_scope_aspect_reason_missing:{key}")
        if handling == "今回評価する" and reason not in {"", "-", "None"}:
            errors.append(f"evaluated_aspect_has_exclusion_reason:{key}")
        aspect_handling[key] = handling
    expected_handling = expected.get("aspect_handling", {})
    aspect_errors = [error for error in errors if error in {
        "aspect_rows_missing_reordered_or_renamed", "aspect_handling_differs_from_expected"
    } or error.startswith(("invalid_aspect_handling:", "out_of_scope_aspect_reason_missing:", "evaluated_aspect_has_exclusion_reason:"))]
    if expected_handling and aspect_handling != expected_handling and "aspect_handling_differs_from_expected" not in aspect_errors:
        aspect_errors.append("aspect_handling_differs_from_expected")
    result.add("UE-D003", not aspect_errors and actual_aspects == expected_aspects, "fixed aspect row order and names are canonical", evidence=aspect_errors or None)

    reference_catalog = expected.get("reference_catalog", {})
    if not isinstance(reference_catalog, dict):
        reference_catalog = {}
        errors.append("expected_reference_catalog_invalid")
    pattern_rows = _rows(found["patterns"])
    pattern_keys = []
    for row in pattern_rows:
        key = _value(row, "Draft Key")
        pattern_keys.append(key)
        name = _value(row, "Pattern")
        source_cell = _value(row, "Source Refs")
        try:
            source_refs = json.loads(source_cell) if source_cell not in {"", "-"} else []
        except json.JSONDecodeError:
            source_refs = []
            errors.append(f"pattern_source_refs_not_json:{key}")
        if name not in {"", "-", "None"} and not source_refs:
            errors.append(f"identified_pattern_missing_source:{key}")
        for source_ref in source_refs:
            entry = source_ref.get("reference_entry_ref") if isinstance(source_ref, dict) else None
            item = source_ref.get("source_item_ref") if isinstance(source_ref, dict) else None
            if entry not in reference_catalog or item not in reference_catalog.get(entry, []):
                errors.append(f"pattern_source_ref_unresolved:{key}:{entry}:{item}")
    if len(pattern_keys) != len(set(pattern_keys)):
        errors.append("duplicate_pattern_draft_key")
    result.add("UE-D004", not any(value.startswith(("pattern_", "identified_pattern", "duplicate_pattern")) for value in errors), "pattern identification source links resolve", evidence=[value for value in errors if value.startswith(("pattern_", "identified_pattern", "duplicate_pattern"))] or None)

    evaluation_rows = _rows(found["evaluations"])
    evaluation_refs = []
    evaluation_records = []
    evaluation_draft_keys = []
    finding_refs = set(expected.get("known_refs", {}).get("finding_refs", []))
    used_finding_refs = []
    completed_observation_pairs: dict[tuple[str, str], str] = {}
    for row in evaluation_rows:
        eval_ref = _value(row, "Evaluation Ref")
        evaluation_refs.append(eval_ref)
        if not REF.fullmatch(eval_ref):
            errors.append(f"invalid_evaluation_ref:{eval_ref}")
        machine_text = _value(row, "Machine Normalized Record")
        try:
            record = json.loads(machine_text)
        except json.JSONDecodeError:
            errors.append(f"evaluation_record_not_json:{eval_ref}")
            continue
        if not isinstance(record, dict):
            errors.append(f"evaluation_record_not_object:{eval_ref}")
            continue
        if set(record) != RECORD_FIELDS:
            errors.append(f"evaluation_record_fields_mismatch:{eval_ref}")
        evaluation_draft_keys.append(record.get("draft_key"))
        evaluation_records.append(record)
        if record.get("evaluation_ref") != eval_ref:
            errors.append(f"evaluation_ref_record_mismatch:{eval_ref}")
        if record.get("aspect_key") != _value(row, "Aspect Key") or record.get("status") != _value(row, "Status"):
            errors.append(f"evaluation_table_record_mismatch:{eval_ref}")
        if record.get("finding_ref") not in (None, "", "-") and record.get("finding_ref") != _value(row, "Finding Ref"):
            errors.append(f"finding_ref_table_record_mismatch:{eval_ref}")
        if record.get("finding_ref") in (None, "", "-") and _value(row, "Finding Ref") not in {"", "-"}:
            errors.append(f"unexpected_finding_ref_in_table:{eval_ref}")
        aspect = record.get("aspect_key")
        if aspect not in aspect_handling:
            errors.append(f"evaluation_aspect_unresolved:{eval_ref}:{aspect}")
        elif aspect_handling[aspect] != "今回評価する":
            errors.append(f"evaluation_for_excluded_aspect:{eval_ref}:{aspect}")
        status = record.get("status")
        if status not in STATUS:
            errors.append(f"invalid_evaluation_status:{eval_ref}")
        basis = record.get("basis")
        if not isinstance(basis, list) or not basis or any(value not in BASIS for value in basis) or len(basis) != len(set(basis)):
            errors.append(f"evaluation_basis_invalid:{eval_ref}")
            basis = []
        evidence_refs = record.get("evidence_refs", [])
        _cross_refs(evidence_refs, _known(expected, "evidence_refs"), f"{eval_ref}.evidence_refs", errors)
        if not evidence_refs:
            errors.append(f"evaluation_evidence_missing:{eval_ref}")
        for field in ("target", "observed_fact", "expected_characteristic", "difference", "expected_impact", "impact_basis"):
            if not isinstance(record.get(field), str) or not record[field].strip():
                errors.append(f"evaluation_required_text_missing:{eval_ref}:{field}")
        if not isinstance(record.get("follow_up_required"), bool):
            errors.append(f"follow_up_required_not_boolean:{eval_ref}")
        if record.get("follow_up_required") and not record.get("routing"):
            errors.append(f"follow_up_routing_missing:{eval_ref}")
        authority_refs = record.get("project_authority_refs", [])
        _cross_refs(authority_refs, _known(expected, "project_authority_refs"), f"{eval_ref}.project_authority_refs", errors)
        applied_refs = record.get("applied_references", [])
        if not isinstance(applied_refs, list):
            errors.append(f"applied_references_invalid:{eval_ref}")
            applied_refs = []
        seen_pairs = set()
        for applied in applied_refs:
            if not isinstance(applied, dict):
                errors.append(f"applied_reference_invalid:{eval_ref}")
                continue
            if set(applied) != APPLIED_REFERENCE_FIELDS:
                errors.append(f"applied_reference_fields_mismatch:{eval_ref}")
            entry, item = applied.get("reference_entry_ref"), applied.get("source_item_ref")
            if entry not in reference_catalog or item not in reference_catalog.get(entry, []):
                errors.append(f"applied_reference_unresolved:{eval_ref}:{entry}:{item}")
            if not applied.get("reference_position"):
                errors.append(f"applied_reference_position_missing:{eval_ref}")
            if not isinstance(applied.get("authority_binding_applied"), bool):
                errors.append(f"applied_reference_binding_not_boolean:{eval_ref}")
            if not isinstance(applied.get("project_authority_refs"), list):
                errors.append(f"applied_reference_authority_refs_invalid:{eval_ref}")
            pair = (entry, item)
            if pair in seen_pairs:
                errors.append(f"duplicate_applied_reference:{eval_ref}:{entry}:{item}")
            seen_pairs.add(pair)
            if applied.get("authority_binding_applied") and not applied.get("project_authority_refs"):
                errors.append(f"binding_reference_missing_authority:{eval_ref}")
            _cross_refs(applied.get("project_authority_refs", []), _known(expected, "project_authority_refs"), f"{eval_ref}.applied_reference", errors)
        if "reference" in basis and not applied_refs:
            errors.append(f"reference_basis_without_reference:{eval_ref}")
        if not applied_refs and not record.get("reference_not_used_reason"):
            errors.append(f"reference_not_used_reason_missing:{eval_ref}")
        if not applied_refs and not record.get("judgment_reason"):
            errors.append(f"reference_free_judgment_reason_missing:{eval_ref}")
        if "project-authority" in basis and not authority_refs:
            errors.append(f"authority_basis_without_ref:{eval_ref}")
        if "user-goal" in basis and condition.get("user_goal_task_flow") in {"", "-", "null", "None"}:
            errors.append(f"user_goal_basis_without_context:{eval_ref}")
        if "success-condition" in basis and all(condition.get(key) in {"", "-", "null", "None"} for key in ("success_condition", "business_outcome", "business_rule")):
            errors.append(f"success_condition_basis_without_context:{eval_ref}")
        if "cross-state-consistency" in basis and (not record.get("judgment_reason") or not evidence_refs):
            errors.append(f"cross_state_basis_missing_context:{eval_ref}")
        if status in {"判定不能", "対象外"} and not record.get("status_reason"):
            errors.append(f"status_reason_missing:{eval_ref}")
        if status == "問題を確認" and (not record.get("observed_fact") or not record.get("expected_impact") or not record.get("impact_basis")):
            errors.append(f"issue_basis_missing:{eval_ref}")
        follow_up = record.get("follow_up_required")
        finding_required = status in {"問題を確認", "判定不能"} and follow_up is True
        if record.get("finding_required") is not finding_required:
            errors.append(f"finding_requirement_mismatch:{eval_ref}")
        finding_ref = record.get("finding_ref")
        if finding_required:
            if finding_ref not in finding_refs:
                errors.append(f"required_finding_missing:{eval_ref}:{finding_ref}")
            used_finding_refs.append(finding_ref)
        elif finding_ref not in (None, "", "-"):
            errors.append(f"finding_not_allowed:{eval_ref}")
        for kind in ("test_rule_result_refs", "requirement_check_refs", "measurement_refs"):
            known_kind = {"test_rule_result_refs": "test_rule_result_refs", "requirement_check_refs": "requirement_check_refs", "measurement_refs": "measurement_refs"}[kind]
            _cross_refs(record.get(kind, []), _known(expected, known_kind), f"{eval_ref}.{kind}", errors)
        observation_links = record.get("additional_observation_links", [])
        if not isinstance(observation_links, list):
            errors.append(f"observation_links_invalid:{eval_ref}")
            observation_links = []
        request_draft_keys = set()
        for index, link in enumerate(observation_links):
            label = f"{eval_ref}.observation.{index + 1}"
            if not isinstance(link, dict):
                errors.append(f"observation_link_invalid:{label}")
                continue
            required_observation_fields = {
                "request_draft_key", "requester_kind", "requester_identity", "execution_owner", "scope_ref",
                "target_identity", "state_description", "state_basis_refs", "current_document_identity",
                "observation_field_key", "predicate_key", "predicate_payload", "needed_observation", "reason",
                "input_evidence_refs", "request_signature", "input_evidence_fingerprint", "status",
                "inspection_request_ref", "owner_activity_ref", "returned_evidence_refs", "limitation",
            }
            if set(link) != required_observation_fields:
                errors.append(f"observation_link_fields_mismatch:{label}")
            request_key = link.get("request_draft_key")
            if not isinstance(request_key, str) or not request_key.strip() or request_key in request_draft_keys:
                errors.append(f"observation_request_key_invalid_or_duplicate:{label}")
            request_draft_keys.add(request_key)
            _validate_signature(link, label, errors)
            for text_field in ("state_description", "needed_observation", "reason"):
                if not isinstance(link.get(text_field), str) or not link[text_field].strip():
                    errors.append(f"observation_required_text_missing:{label}:{text_field}")
            _cross_refs([link.get("scope_ref")], _known(expected, "scope_refs"), f"{label}.scope_ref", errors)
            _cross_refs(link.get("state_basis_refs", []), _known(expected, "state_basis_refs"), f"{label}.state_basis_refs", errors)
            if link.get("target_identity"):
                target = link["target_identity"]
                if not isinstance(target, dict) or len(target) != 1 or set(target) - {"target_ref", "target_draft_key"}:
                    errors.append(f"observation_target_identity_invalid:{label}")
                elif target.get("target_ref"):
                    _cross_refs([target["target_ref"]], _known(expected, "target_refs"), f"{label}.target_ref", errors)
                elif target.get("target_draft_key") not in _known(expected, "target_draft_keys"):
                    errors.append(f"observation_target_draft_unresolved:{label}")
            _cross_refs(link.get("input_evidence_refs", []), _known(expected, "evidence_refs"), f"{label}.input_evidence_refs", errors)
            _cross_refs(link.get("returned_evidence_refs", []), _known(expected, "evidence_refs"), f"{label}.returned_evidence_refs", errors)
            if link.get("execution_owner") == "usability-inspection":
                if link.get("owner_activity_ref") not in (None, "", "-") or (link.get("status") in {"completed", "no-progress"} and not link.get("inspection_request_ref")):
                    errors.append(f"inspection_owner_link_invalid:{label}")
                if link.get("inspection_request_ref"):
                    _cross_refs([link["inspection_request_ref"]], _known(expected, "inspection_request_refs"), f"{label}.inspection_request_ref", errors)
            elif link.get("execution_owner") in {"test-target-inspection", "test-execution"}:
                if link.get("inspection_request_ref") not in (None, "", "-") or not link.get("owner_activity_ref"):
                    errors.append(f"external_owner_link_invalid:{label}")
                if link.get("owner_activity_ref"):
                    _cross_refs([link["owner_activity_ref"]], _known(expected, "owner_activity_refs"), f"{label}.owner_activity_ref", errors)
            if link.get("status") not in {"completed", "unsupported", "no-progress", "blocked"}:
                errors.append(f"observation_status_invalid:{label}")
            if link.get("status") == "completed" and link.get("execution_owner") in {"test-target-inspection", "test-execution"} and not link.get("returned_evidence_refs"):
                errors.append(f"completed_external_observation_missing_evidence:{label}")
            if link.get("status") in {"unsupported", "blocked"} and not link.get("limitation"):
                errors.append(f"blocked_observation_limitation_missing:{label}")
            pair = (link.get("request_signature"), link.get("input_evidence_fingerprint"))
            if pair in completed_observation_pairs and link.get("status") != "no-progress":
                errors.append(f"duplicate_observation_not_no_progress:{label}")
            if pair not in completed_observation_pairs:
                completed_observation_pairs[pair] = link.get("status")

    expected_evaluation_refs = [f"EVAL-{index:03d}" for index in range(1, len(evaluation_rows) + 1)]
    if evaluation_refs != expected_evaluation_refs:
        errors.append("evaluation_refs_not_sequential_in_decision_order")
    evaluated_aspects = {record.get("aspect_key") for record in evaluation_records}
    missing_aspects = sorted(key for key, handling in aspect_handling.items() if handling == "今回評価する" and key not in evaluated_aspects)
    if missing_aspects:
        errors.append(f"evaluated_aspects_not_closed:{','.join(missing_aspects)}")
    if len(used_finding_refs) != len(set(used_finding_refs)):
        errors.append("finding_ref_reused")
    if len(evaluation_draft_keys) != len(set(evaluation_draft_keys)):
        errors.append("duplicate_evaluation_draft_key")

    summary = {_value(row, "Metric"): _value(row, "Count") for row in _rows(found["summary"])}
    expected_summary = {
        "evaluated_aspects": sum(value == "今回評価する" for value in aspect_handling.values()),
        "out_of_scope_aspects": sum(value == "対象外" for value in aspect_handling.values()),
        "evaluation_count": len(evaluation_records),
        "finding_count": len(used_finding_refs),
        "issue_count": sum(row.get("status") == "問題を確認" for row in evaluation_records),
        "no_issue_count": sum(row.get("status") == "問題なし" for row in evaluation_records),
        "undetermined_count": sum(row.get("status") == "判定不能" for row in evaluation_records),
        "out_of_scope_result_count": sum(row.get("status") == "対象外" for row in evaluation_records),
        "pattern_identification_count": len(pattern_rows),
    }
    summary_issues = {key: (summary.get(key), str(value)) for key, value in expected_summary.items() if summary.get(key) != str(value)}
    result.add("UE-D005", not errors, "evaluation basis, findings, source/evidence links, and observation-owner contracts close", evidence=errors[:40] or None)
    result.add("UE-D006", not summary_issues, "summary is deterministically derived from closed rows", evidence=summary_issues or None)
    required_tokens = expected.get("required_output_tokens", [])
    forbidden_tokens = expected.get("forbidden_output_values", [])
    token_errors = []
    if not isinstance(required_tokens, list) or any(not isinstance(value, str) for value in required_tokens):
        token_errors.append("expected_required_output_tokens_invalid")
    else:
        token_errors.extend(f"required_output_token_missing:{value}" for value in required_tokens if value not in text)
    if not isinstance(forbidden_tokens, list) or any(not isinstance(value, str) for value in forbidden_tokens):
        token_errors.append("expected_forbidden_output_values_invalid")
    else:
        token_errors.extend(f"forbidden_output_value_present:{value}" for value in forbidden_tokens if value in text)
    result.add("UE-D007", not token_errors, "fixture-specific contract values are preserved without forbidden writeback", evidence=token_errors or None)
    return result
