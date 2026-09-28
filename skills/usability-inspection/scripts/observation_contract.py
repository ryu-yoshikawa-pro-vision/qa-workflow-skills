"""Fixed browser observation request, resolver, and result contract.

This package does not own a browser runner. A Playwright owner executes only the
materialized fixed request and returns a payload for validation here.
"""
from __future__ import annotations

import hashlib
import json
import math
from typing import Any


OBSERVATION_FIELDS = {
    "viewport.metrics": "viewport-state",
    "element.geometry": "element-geometry",
    "element.state": "element-state",
    "document.location": "document-location",
    "element.rendered-text": "element-content",
    "element.control-value": "element-content",
    "element.selected-values": "element-content",
    "accessibility.semantics": "accessibility-semantics",
    "focus.state": "focus-state",
    "computed-style.properties": "computed-style",
    "responsive.conditions": "responsive-conditions",
    "responsive.boundaries": "responsive-boundaries",
    "navigation.timing": "navigation-timing",
    "paint.timing": "paint-timing",
    "interaction.timing": "interaction-timing",
    "screenshot.image": "screenshot",
}
RESOLVERS = {"role-name", "label", "visible-text", "machine-population-index", "current-session-ref"}
FORMAL_PROBES = {
    "mp-document-title", "mp-document-language", "mp-part-language-inventory", "mp-purpose-metadata",
    "mp-nontext-content-inventory", "mp-media-inventory", "mp-moving-updating-inventory", "mp-timer-inventory",
    "mp-shortcut-inventory", "mp-form-control-inventory", "mp-heading-label-inventory", "mp-link-inventory",
    "mp-structure-inventory", "mp-sequence-inventory", "mp-component-semantics", "mp-status-candidate-inventory",
    "mp-target-geometry", "mp-neighbor-geometry", "mp-focus-obscuring-geometry", "mp-computed-color-context",
    "mp-text-presentation-values", "mp-focus-appearance-evidence", "mp-viewport-state", "mp-focus-sequence-run",
    "mp-keyboard-functionality-run", "mp-pointer-interaction-run", "mp-hover-focus-content-run",
    "mp-change-trigger-run", "mp-error-scenario-run", "mp-orientation-run", "mp-reflow-run", "mp-resize-text-run",
    "mp-text-spacing-run", "mp-control-value-history", "mp-multipage-signature", "mp-audio-autoplay-run",
}
FORMAL_STATUSES = {"ok", "unsupported", "unavailable", "incomplete", "blocked"}
LIMITATION_CODES = {
    "background-not-machine-resolvable", "focus-indicator-not-machine-resolvable",
    "text-scaling-mechanism-not-machine-executable", "text-scaling-state-not-machine-readable",
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
OPTIONAL_PREDICATE_FIELDS = {"text-present": {"within_target_ref"}}
ATTRIBUTE_NAMES = {
    "aria-current", "aria-label", "aria-live", "href", "name", "role", "title", "value",
}
ARIA_STATE_NAMES = {
    "aria-checked", "aria-current", "aria-disabled", "aria-expanded", "aria-invalid",
    "aria-pressed", "aria-selected",
}


class ObservationContractError(ValueError):
    pass


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def fingerprint(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(value)).hexdigest()


def _exact_fields(value: dict[str, Any], required: set[str], optional: set[str] = set()) -> None:
    missing = required - set(value)
    extra = set(value) - required - optional
    if missing or extra:
        raise ObservationContractError(f"field mismatch missing={sorted(missing)} extra={sorted(extra)}")


def validate_predicate(predicate: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(predicate, dict) or not isinstance(predicate.get("predicate_key"), str):
        raise ObservationContractError("fixed interaction predicate is required")
    key = predicate["predicate_key"]
    required = PREDICATES.get(key)
    if required is None:
        raise ObservationContractError("unknown fixed interaction predicate")
    optional = OPTIONAL_PREDICATE_FIELDS.get(key, set())
    payload = {name: value for name, value in predicate.items() if name != "predicate_key"}
    _exact_fields(payload, required, optional)
    for name, value in payload.items():
        if not isinstance(value, str) or (name not in {"expected_text", "expected_value"} and not value.strip()):
            raise ObservationContractError(f"predicate field must be a non-empty string: {name}")
    if key == "attribute-equals" and payload["attribute_name"] not in ATTRIBUTE_NAMES:
        raise ObservationContractError("attribute name is outside the fixed allowlist")
    if key == "aria-state-equals" and payload["state_name"] not in ARIA_STATE_NAMES:
        raise ObservationContractError("ARIA state name is outside the fixed allowlist")
    if key == "url-changed" and payload["baseline_url"] != "capture-at-arm":
        raise ObservationContractError("url-changed baseline must be captured by the browser owner at arm time")
    return {"predicate_key": key, **{name: payload[name] for name in sorted(payload)}}


def validate_resolver(kind: str, payload: dict[str, Any]) -> None:
    if kind == "role-name":
        _exact_fields(payload, {"role", "name"}, {"within_target_ref"})
        if not all(isinstance(payload[k], str) and payload[k].strip() for k in ("role", "name")):
            raise ObservationContractError("role-name resolver requires non-empty role and name")
    elif kind == "label":
        _exact_fields(payload, {"label_text"}, {"within_target_ref"})
        if not isinstance(payload["label_text"], str) or not payload["label_text"].strip():
            raise ObservationContractError("label resolver requires label_text")
    elif kind == "visible-text":
        _exact_fields(payload, {"text"}, {"within_target_ref"})
        if not isinstance(payload["text"], str) or not payload["text"].strip():
            raise ObservationContractError("visible-text resolver requires text")
    elif kind == "machine-population-index":
        _exact_fields(payload, {"population_ref", "population_revision", "index", "identity_fingerprint"})
        if not isinstance(payload["index"], int) or isinstance(payload["index"], bool) or payload["index"] < 0:
            raise ObservationContractError("population index must be a non-negative integer")
        if not all(isinstance(payload[k], str) and payload[k] for k in ("population_ref", "population_revision", "identity_fingerprint")):
            raise ObservationContractError("population resolver identity fields are required")
    elif kind == "current-session-ref":
        _exact_fields(payload, {"session_target_ref", "document_identity"})
        if not all(isinstance(payload[k], str) and payload[k] for k in payload):
            raise ObservationContractError("session resolver identity fields are required")
    else:
        raise ObservationContractError("unknown resolver kind")


def materialize_targets(drafts: list[dict[str, Any]], *, document_identity: str,
                        population_revisions: dict[str, Any] | None = None) -> dict[str, Any]:
    target_refs: dict[str, str] = {}
    rows = []
    for i, draft in enumerate(drafts, 1):
        required = {"draft_target_key", "scope_ref", "semantic_label", "discovery_evidence_refs", "resolver_kind", "resolver_payload"}
        if set(draft) != required:
            raise ObservationContractError("target draft schema mismatch")
        key = draft["draft_target_key"]
        if not isinstance(key, str) or not key or key in target_refs:
            raise ObservationContractError("duplicate or missing draft target key")
        if draft["resolver_kind"] not in RESOLVERS:
            raise ObservationContractError("unsupported resolver kind")
        validate_resolver(draft["resolver_kind"], draft["resolver_payload"])
        parent = draft["resolver_payload"].get("within_target_ref")
        if parent and parent not in target_refs:
            raise ObservationContractError("parent target must be declared earlier and resolve uniquely")
        resolver_payload = dict(draft["resolver_payload"])
        if parent:
            resolver_payload["within_target_ref"] = target_refs[parent]
        if draft["resolver_kind"] == "machine-population-index":
            known = (population_revisions or {}).get(draft["resolver_payload"]["population_ref"])
            currentness = "current" if (
                isinstance(known, dict)
                and known.get("population_revision") == draft["resolver_payload"]["population_revision"]
                and known.get("identity_fingerprint") == draft["resolver_payload"]["identity_fingerprint"]
            ) else "stale"
        elif draft["resolver_kind"] == "current-session-ref":
            currentness = "current" if draft["resolver_payload"]["document_identity"] == document_identity else "stale"
        else:
            currentness = "current"
        ref = f"TARGET-{i:03d}"
        target_refs[key] = ref
        rows.append({"target_ref": ref, "draft_target_key": key, "scope_ref": draft["scope_ref"],
                     "document_identity": document_identity, "semantic_label": draft["semantic_label"],
                     "discovery_evidence_refs": list(draft["discovery_evidence_refs"]),
                     "resolver_kind": draft["resolver_kind"], "resolver_payload": resolver_payload,
                     "expected_match_count": 1, "resolution_status": currentness,
                     "limitation": None if currentness == "current" else "stale_identity"})
    return {"targets": rows, "draft_to_target_ref": target_refs}


def normalize_target_resolution(target: dict[str, Any], resolution: dict[str, Any], *,
                                current_document_identity: str,
                                current_populations: dict[str, Any] | None = None) -> dict[str, Any]:
    required = {"target_ref", "match_count", "current_document_identity"}
    if not isinstance(resolution, dict) or required - set(resolution):
        raise ObservationContractError("target resolution result schema invalid")
    if resolution["target_ref"] != target.get("target_ref"):
        raise ObservationContractError("target resolution ref mismatch")
    count = resolution["match_count"]
    if not isinstance(count, int) or isinstance(count, bool) or count < 0:
        raise ObservationContractError("target match count must be a non-negative integer")
    stale = resolution["current_document_identity"] != current_document_identity
    payload = target.get("resolver_payload", {})
    if target.get("resolver_kind") == "machine-population-index":
        population = (current_populations or {}).get(payload.get("population_ref"))
        stale = stale or not isinstance(population, dict) or any(
            population.get(key) != payload.get(key)
            for key in ("population_revision", "identity_fingerprint")
        )
        stale = stale or resolution.get("population_revision") != payload.get("population_revision")
        stale = stale or resolution.get("identity_fingerprint") != payload.get("identity_fingerprint")
    elif target.get("resolver_kind") == "current-session-ref":
        stale = stale or payload.get("document_identity") != current_document_identity
    status = "stale" if stale else ("missing" if count == 0 else "unique" if count == 1 else "ambiguous")
    return {"target_ref": target["target_ref"], "status": status, "match_count": count,
            "current_document_identity": current_document_identity,
            "resolved": status == "unique", "limitation": None if status == "unique" else status}


def plan_probes(*, selected_rule_keys: list[str], measurement_kinds: list[str],
                aspect_keys: list[str], target_refs: list[str] | None = None) -> dict[str, Any]:
    rules = {
        "2779a5": {"document.location"},
        "97a4e1": {"accessibility.semantics"},
        "23a2a8": {"accessibility.semantics"},
    }
    measurement_fields = {
        "navigation-timing": {"navigation.timing"}, "paint-timing": {"paint.timing"},
        "interaction-timing": {"interaction.timing"}, "responsive": {"viewport.metrics", "responsive.conditions", "responsive.boundaries"},
        "geometry": {"viewport.metrics", "element.geometry"}, "visual": {"screenshot.image", "viewport.metrics"},
        "accessibility": {"accessibility.semantics", "element.state", "focus.state"},
    }
    fields: set[str] = set()
    for key in selected_rule_keys:
        if key not in rules:
            raise ObservationContractError(f"unsupported test rule key: {key}")
        fields.update(rules[key])
    for kind in measurement_kinds:
        if kind not in measurement_fields:
            raise ObservationContractError(f"unsupported measurement kind: {kind}")
        fields.update(measurement_fields[kind])
    if "interaction-operability" in aspect_keys:
        fields.update({"element.state", "focus.state", "screenshot.image"})
    if "feedback-system-status" in aspect_keys:
        fields.update({"element.state", "accessibility.semantics", "screenshot.image"})
    if "accessibility" in aspect_keys:
        fields.update({"accessibility.semantics", "focus.state"})
    if "visual-responsive" in aspect_keys:
        fields.update({"viewport.metrics", "element.geometry", "responsive.conditions", "responsive.boundaries", "screenshot.image"})
    if "performance-responsiveness" in aspect_keys:
        fields.update({"navigation.timing", "paint.timing"})
    if fields - set(OBSERVATION_FIELDS):
        raise ObservationContractError("field has no unique fixed probe")
    probe_rows = []
    for index, field in enumerate(sorted(fields), 1):
        row = {"probe_ref": f"PROBE-{index:03d}", "observation_field": field,
               "probe_key": OBSERVATION_FIELDS[field],
               "target_refs": list(target_refs or []) if OBSERVATION_FIELDS[field] not in {"viewport-state", "document-location", "navigation-timing", "paint-timing", "responsive-conditions"} else [],
               "required_result_fields": _required_result_fields(field)}
        if field == "interaction.timing":
            row["clock_domain"] = "same-page-performance-now"
            row["predicate_key_required"] = True
        probe_rows.append(row)
    return {"probes": probe_rows, "required_observation_fields": sorted(fields),
            "unsupported_observation_fields": []}


def _required_result_fields(field: str) -> list[str]:
    fields = {
        "viewport.metrics": ["viewport_width_css_px", "viewport_height_css_px", "scroll_x_css_px", "scroll_y_css_px", "scroll_width_css_px", "scroll_height_css_px"],
        "element.geometry": ["x_css_px", "y_css_px", "width_css_px", "height_css_px"],
        "element.state": ["visible", "enabled", "checked", "selected", "expanded"],
        "document.location": ["safe_url", "status", "limitation"],
        "element.rendered-text": ["raw_text", "status"], "element.control-value": ["raw_value", "status"],
        "element.selected-values": ["selected_options", "status"],
        "accessibility.semantics": ["role", "accessible_name", "description", "states", "status"],
        "focus.state": ["active_target_ref", "focusable", "focus_visible", "status"],
        "computed-style.properties": ["properties", "status"],
        "responsive.conditions": ["conditions", "complete", "status"],
        "responsive.boundaries": ["boundaries", "complete", "status"],
        "navigation.timing": ["entries", "status"], "paint.timing": ["entries", "status"],
        "interaction.timing": ["start_ms", "end_ms", "elapsed_ms", "predicate_result", "clock_domain", "status"],
        "screenshot.image": ["evidence_ref", "viewport", "status"],
    }
    return fields[field]


def normalize_probe_result(probe: dict[str, Any], result: dict[str, Any], *, current_document_identity: str,
                           formal: bool = False, formal_request: dict[str, Any] | None = None) -> dict[str, Any]:
    if formal:
        if formal_request is None:
            raise ObservationContractError("formal result validation requires its typed request")
        validate_formal_probe_request(formal_request)
        identity_fields = {"observation_request_ref", "request_signature", "criterion_evaluation_ref",
                           "procedure_execution_ref", "machine_probe_key", "sample_ref", "variation_ref",
                           "process_ref", "requirement_ref", "target_identity", "currentness_dependency"}
        required = identity_fields | {"status", "current_document_identity", "evidence_refs"}
        allowed = required | {"value", "limitation", "limitation_code"}
        if required - set(result) or result.get("status") not in FORMAL_STATUSES:
            raise ObservationContractError("formal machine probe result schema/status invalid")
        if set(result) - allowed:
            raise ObservationContractError("formal machine probe result contains fields outside its fixed schema")
        if result["machine_probe_key"] not in FORMAL_PROBES:
            raise ObservationContractError("formal machine probe key is not in local finite catalog")
        for field in identity_fields:
            if result[field] != formal_request[field]:
                raise ObservationContractError(f"formal result currentness identity mismatch: {field}")
        if not isinstance(result["current_document_identity"], str) or not result["current_document_identity"].strip():
            raise ObservationContractError("formal result requires current document identity")
        evidence_refs = result.get("evidence_refs")
        if not isinstance(evidence_refs, list) or any(not isinstance(ref, str) or not ref.strip() for ref in evidence_refs):
            raise ObservationContractError("formal evidence_refs must be a string array")
        if result["status"] == "ok" and not isinstance(result.get("value"), dict):
            raise ObservationContractError("successful formal probe requires a typed value object")
        if result["status"] in {"unsupported", "unavailable", "incomplete", "blocked"}:
            if not isinstance(result.get("limitation"), str) or not result["limitation"].strip():
                raise ObservationContractError("non-success formal probe requires a limitation")
        if result["current_document_identity"] != current_document_identity:
            result = {**result, "status": "incomplete", "limitation_code": None, "limitation": "stale_document"}
        code = result.get("limitation_code")
        if code is not None and code not in LIMITATION_CODES:
            raise ObservationContractError("unknown formal limitation code")
        return {**result, "normalized": True,
                "input_fingerprint": fingerprint({k: formal_request[k] for k in sorted(formal_request) if k != "request_signature"})}

    if result.get("probe_key") != probe["probe_key"] or result.get("document_identity") != current_document_identity:
        raise ObservationContractError("probe identity mismatch or stale document")
    if result.get("status") not in {"ok", "unavailable", "unsupported", "incomplete", "blocked"}:
        raise ObservationContractError("invalid probe status")
    missing = set(probe["required_result_fields"]) - set(result.get("value", {})) if result.get("status") == "ok" else set()
    if missing:
        raise ObservationContractError(f"missing required result values: {sorted(missing)}")
    if result["status"] != "ok" and (not isinstance(result.get("limitation"), str) or not result["limitation"].strip()):
        raise ObservationContractError("non-success probe result requires a limitation")
    evidence_refs = result.get("evidence_refs", [])
    if not isinstance(evidence_refs, list) or any(not isinstance(ref, str) or not ref.strip() for ref in evidence_refs):
        raise ObservationContractError("evidence refs must be non-empty strings")
    value = result.get("value", {})
    if probe["observation_field"] == "element.geometry" and result.get("status") == "ok":
        for name in ("x_css_px", "y_css_px", "width_css_px", "height_css_px"):
            if isinstance(value[name], bool) or not isinstance(value[name], (int, float)) or not math.isfinite(value[name]):
                raise ObservationContractError("geometry values must be numeric CSS px")
    return {"observation_field": probe["observation_field"], "probe_ref": probe["probe_ref"],
            "probe_key": probe["probe_key"], "document_identity": current_document_identity,
            "status": result["status"], "value": value if result["status"] == "ok" else None,
            "limitation": result.get("limitation"), "evidence_refs": sorted(set(evidence_refs))}


def validate_formal_probe_request(request: dict[str, Any]) -> dict[str, Any]:
    required = {"request_kind", "observation_request_ref", "request_signature", "criterion_evaluation_ref",
                "procedure_execution_ref", "machine_probe_key", "sample_ref", "variation_ref", "process_ref",
                "requirement_ref", "currentness_dependency", "target_identity", "required_browser_capability"}
    if not isinstance(request, dict) or required - set(request):
        missing = sorted(required - set(request)) if isinstance(request, dict) else sorted(required)
        raise ObservationContractError(f"formal typed request schema invalid; missing={missing}")
    if set(request) != required:
        raise ObservationContractError("formal typed request contains fields outside the fixed schema")
    if request["request_kind"] != "wcag-machine-probe" or request["machine_probe_key"] not in FORMAL_PROBES:
        raise ObservationContractError("formal request kind or fixed probe key invalid")
    if request["required_browser_capability"] != request["machine_probe_key"]:
        raise ObservationContractError("required browser capability does not match fixed probe")
    if not all(isinstance(request[field], str) and request[field].strip() for field in
               ("observation_request_ref", "criterion_evaluation_ref", "procedure_execution_ref", "sample_ref",
                "variation_ref", "requirement_ref", "target_identity")):
        raise ObservationContractError("formal typed request identity fields must be non-empty strings")
    if request["process_ref"] is not None and (not isinstance(request["process_ref"], str) or not request["process_ref"].strip()):
        raise ObservationContractError("formal process ref must be a non-empty string or null")
    if not isinstance(request["currentness_dependency"], dict) or not request["currentness_dependency"]:
        raise ObservationContractError("formal currentness dependency must be a non-empty object")
    expected = fingerprint({key: value for key, value in request.items() if key != "request_signature"})
    if request["request_signature"] != expected:
        raise ObservationContractError("formal request signature mismatch")
    return {"request_ref": request["observation_request_ref"], "request_signature": expected,
            "machine_probe_key": request["machine_probe_key"], "input_fingerprint": expected}


def materialize_additional(draft: dict[str, Any], *, prior_requests: list[dict[str, Any]]) -> dict[str, Any]:
    required = {"request_draft_key", "requester_kind", "requester_identity", "scope_ref", "target_ref",
                "state_description", "state_basis_refs", "current_document_identity", "observation_field",
                "predicate", "reason", "current_evidence_refs"}
    if set(draft) != required:
        raise ObservationContractError("additional request schema mismatch")
    if draft["requester_kind"] not in {"usability-evaluation", "inspection-requirement", "wcag-procedure"}:
        raise ObservationContractError("unknown requester kind")
    if draft["observation_field"] not in OBSERVATION_FIELDS:
        raise ObservationContractError("unknown canonical observation field")
    if not isinstance(draft["request_draft_key"], str) or not draft["request_draft_key"].strip():
        raise ObservationContractError("request draft key is required")
    if any(row.get("request_draft_key") == draft["request_draft_key"] for row in prior_requests):
        raise ObservationContractError("duplicate request draft key")
    if not isinstance(draft["current_document_identity"], str) or not draft["current_document_identity"].strip():
        raise ObservationContractError("current document identity is required")
    target_required = draft["observation_field"] in {
        "element.geometry", "element.state", "element.rendered-text", "element.control-value",
        "element.selected-values", "accessibility.semantics", "focus.state", "computed-style.properties",
    }
    if target_required and (not isinstance(draft["target_ref"], str) or not draft["target_ref"].strip()):
        raise ObservationContractError("element observation requires a materialized target ref")
    if draft["target_ref"] is not None and not isinstance(draft["target_ref"], str):
        raise ObservationContractError("target ref must be a string or null")
    if not isinstance(draft["state_basis_refs"], list) or any(not isinstance(ref, str) or not ref.strip() for ref in draft["state_basis_refs"]):
        raise ObservationContractError("state basis refs must be non-empty strings")
    if len(draft["state_basis_refs"]) != len(set(draft["state_basis_refs"])):
        raise ObservationContractError("duplicate state basis ref")
    if not isinstance(draft["current_evidence_refs"], list) or any(not isinstance(ref, str) or not ref.strip() for ref in draft["current_evidence_refs"]):
        raise ObservationContractError("current evidence refs must be non-empty strings")
    if len(draft["current_evidence_refs"]) != len(set(draft["current_evidence_refs"])):
        raise ObservationContractError("duplicate current evidence ref")
    _validate_requester_identity(draft["requester_kind"], draft["requester_identity"])
    predicate = draft["predicate"]
    if predicate is not None:
        if draft["observation_field"] != "interaction.timing":
            raise ObservationContractError("fixed interaction predicate requires interaction.timing")
        predicate = validate_predicate(predicate)
    identity_payload = {k: draft[k] for k in ("requester_kind", "requester_identity", "scope_ref", "target_ref", "current_document_identity", "observation_field")}
    identity_payload["state_basis_refs"] = sorted(set(draft["state_basis_refs"]))
    identity_payload["predicate"] = predicate
    request_identity = fingerprint(identity_payload)
    evidence_fingerprint = fingerprint(sorted(set(draft["current_evidence_refs"])))
    duplicate = any(row.get("request_identity") == request_identity and row.get("input_evidence_fingerprint") == evidence_fingerprint for row in prior_requests)
    return {"observation_request_ref": f"OBSREQ-{len(prior_requests)+1:03d}",
            "request_draft_key": draft["request_draft_key"], "requester_kind": draft["requester_kind"],
            "requester_identity": draft["requester_identity"], "scope_ref": draft["scope_ref"],
            "target_ref": draft["target_ref"], "state_basis_refs": identity_payload["state_basis_refs"],
            "current_document_identity": draft["current_document_identity"],
            "observation_field": draft["observation_field"], "probe_key": OBSERVATION_FIELDS[draft["observation_field"]],
            "predicate": predicate, "request_identity": request_identity,
            "request_signature": fingerprint({"request_identity": request_identity, "input_evidence_fingerprint": evidence_fingerprint}),
            "input_evidence_fingerprint": evidence_fingerprint,
            "status": "no-progress" if duplicate else "requested",
            "reason": draft["reason"], "evidence_refs": sorted(set(draft["current_evidence_refs"]))}


def _validate_requester_identity(kind: str, identity: Any) -> None:
    if kind == "usability-evaluation":
        valid = isinstance(identity, str) and bool(identity.strip())
        valid = valid or (isinstance(identity, dict) and len(identity) == 1
                          and set(identity) in ({"evaluation_draft_key"}, {"evaluation_ref"})
                          and isinstance(next(iter(identity.values())), str)
                          and bool(next(iter(identity.values())).strip()))
    elif kind == "inspection-requirement":
        valid = isinstance(identity, dict) and len(identity) == 1
        valid = valid and set(identity) in ({"requirement_ref"}, {"requirement_draft_key"})
        valid = valid and isinstance(next(iter(identity.values())), str) and bool(next(iter(identity.values())).strip())
    elif kind == "wcag-procedure":
        valid = isinstance(identity, dict) and set(identity) == {"criterion_evaluation_ref", "procedure_execution_ref"}
        valid = valid and all(isinstance(value, str) and value.strip() for value in identity.values())
    else:
        valid = False
    if not valid:
        raise ObservationContractError("requester identity does not match its fixed requester kind")


def close_additional_request(request: dict[str, Any], result: dict[str, Any] | None = None) -> dict[str, Any]:
    """Close an OBSREQ without turning an unavailable browser result into product failure."""
    if request.get("status") == "no-progress":
        return {**request, "status": "no-progress", "terminal": True}
    if request.get("status") != "requested":
        raise ObservationContractError("additional request is not awaiting execution")
    if result is None:
        raise ObservationContractError("additional request cannot remain planned or requested in a final artifact")
    required = {"observation_request_ref", "request_signature", "input_evidence_fingerprint", "status"}
    if required - set(result):
        raise ObservationContractError("additional observation result identity is incomplete")
    for field in ("observation_request_ref", "request_signature", "input_evidence_fingerprint"):
        if result[field] != request.get(field):
            raise ObservationContractError(f"additional observation result identity mismatch: {field}")
    terminal_status = {"ok": "completed", "unsupported": "unsupported",
                       "unavailable": "blocked", "incomplete": "blocked", "blocked": "blocked"}.get(result["status"])
    if terminal_status is None:
        raise ObservationContractError("unknown additional observation result status")
    return {**request, "status": terminal_status, "terminal": True,
            "result_evidence_refs": sorted(set(result.get("evidence_refs", []))),
            "limitation": result.get("limitation")}


def validate_catalog(catalog: dict[str, Any]) -> None:
    rows = catalog.get("probes")
    if not isinstance(rows, list):
        raise ObservationContractError("catalog probes must be a list")
    owners: dict[str, list[str]] = {}
    keys: set[str] = set()
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("probe_key"), str):
            raise ObservationContractError("invalid catalog row")
        key = row["probe_key"]
        if key in keys:
            raise ObservationContractError(f"duplicate probe key: {key}")
        keys.add(key)
        for field in row.get("provided_observation_fields", []):
            owners.setdefault(field, []).append(key)
    if set(owners) != set(OBSERVATION_FIELDS) or any(len(v) != 1 for v in owners.values()):
        raise ObservationContractError("each of the 16 canonical observation fields must have exactly one probe owner")
    timing = catalog.get("interaction_timing_contract")
    if not isinstance(timing, dict) or timing.get("clock_domain") != "same-page-performance-now":
        raise ObservationContractError("interaction timing clock domain must be fixed")
    predicate_rows = timing.get("predicates")
    if not isinstance(predicate_rows, list):
        raise ObservationContractError("fixed interaction predicates must be catalogued")
    catalog_predicates = {row.get("predicate_key"): row for row in predicate_rows if isinstance(row, dict)}
    if set(catalog_predicates) != set(PREDICATES) or len(catalog_predicates) != len(predicate_rows):
        raise ObservationContractError("catalog must contain the exact eight fixed predicates")
    for key, required in PREDICATES.items():
        row = catalog_predicates[key]
        if set(row.get("required_fields", [])) != required or set(row.get("optional_fields", [])) != OPTIONAL_PREDICATE_FIELDS.get(key, set()):
            raise ObservationContractError(f"fixed predicate schema mismatch: {key}")
    if set(timing.get("allowed_attribute_names", [])) != ATTRIBUTE_NAMES:
        raise ObservationContractError("attribute name allowlist mismatch")
    if set(timing.get("allowed_aria_state_names", [])) != ARIA_STATE_NAMES:
        raise ObservationContractError("ARIA state allowlist mismatch")
