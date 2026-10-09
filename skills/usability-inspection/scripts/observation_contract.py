"""Fixed browser observation request, resolver, and result contract.

This package does not own a browser runner. A Playwright owner executes only the
materialized fixed request and returns a payload for validation here.
"""
from __future__ import annotations

import hashlib
import json
import re
from decimal import Decimal, InvalidOperation
from typing import Any


OBSERVATION_FIELDS = {
    "viewport.metrics": "viewport-state",
    "element.geometry": "element-geometry",
    "element.state": "element-state",
    "document.location": "document-location",
    "document.title": "document-title",
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
DOCUMENT_IDENTITY_PATTERN = re.compile(r"^hmac-sha256:[0-9a-f]{64}$")
LIMITATION_CODES = {
    "background-not-machine-resolvable", "focus-indicator-not-machine-resolvable",
    "text-scaling-mechanism-not-machine-executable", "text-scaling-state-not-machine-readable",
}
PARTIAL_FORMAL_OBSERVATION_REASONS = {
    "paired-orientation-not-materialized",
    "declared-flow-not-materialized",
    "target-not-materialized",
    "trigger-not-materialized",
    "error-scenario-not-materialized",
    "pointer-action-not-materialized",
    "page-set-not-materialized",
    "prior-control-observation-not-materialized",
    "focus-observation-limit-reached",
    "focus-loop-detected",
    "focus-cycle-not-complete",
    "focus-left-document",
    "focus-target-removed",
    "population-changed-during-observation",
    "probe-result-limit-reached",
    "media-playback-origin-not-instrumented",
    "text-spacing-override-not-applied",
}
PARTIAL_CANDIDATE_NAME_FREE_PROBES = {
    "mp-hover-focus-content-run",
    "mp-multipage-signature",
    "mp-pointer-interaction-run",
}
FORMAL_DOCUMENT_IDENTITY_UNAVAILABLE = (
    "browser cannot create an in-memory keyed current-document identity"
)
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


def is_document_identity_token(value: Any) -> bool:
    return isinstance(value, str) and DOCUMENT_IDENTITY_PATTERN.fullmatch(value) is not None


def _exact_fields(value: dict[str, Any], required: set[str], optional: set[str] = set()) -> None:
    missing = required - set(value)
    extra = set(value) - required - optional
    if missing or extra:
        raise ObservationContractError(f"field mismatch missing={sorted(missing)} extra={sorted(extra)}")


def _decimal_number(value: Any) -> Decimal | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float, Decimal)):
        try:
            number = Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError):
            return None
        return number if number.is_finite() else None
    exact_text = getattr(value, "text", None)
    if not callable(exact_text):
        return None
    try:
        number = Decimal(exact_text())
    except (InvalidOperation, TypeError, ValueError):
        return None
    return number if number.is_finite() else None


def _decimal_text(value: Any, *, positive: bool = False) -> Decimal | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        number = Decimal(value)
    except (InvalidOperation, TypeError, ValueError):
        return None
    if not number.is_finite() or (positive and number <= 0):
        return None
    return number


def _decimal_string(value: Decimal) -> str:
    return format(value.normalize(), "f")


def _normalize_resize_text_value(value: Any, *, current_document_identity: str,
                                 require_complete: bool) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ObservationContractError("Resize Text result value must be an object")
    _exact_fields(value, {"schema", "resize_mechanism", "control", "mechanism_state_sequence",
                          "text_population_complete", "mechanism_state_sequence_complete", "cleanup"})
    if value["schema"] != "wcag-resize-text-observation-v1" or value["resize_mechanism"] not in {
        "user-agent-full-page-zoom", "user-agent-text-only-resize", "author-provided-resize-control"
    }:
        raise ObservationContractError("Resize Text schema or mechanism is outside the finite contract")
    control = value["control"]
    if not isinstance(control, dict):
        raise ObservationContractError("Resize Text control identity must be an object")
    _exact_fields(control, {"target_ref", "role", "accessible_name", "input_type", "minimum_value",
                            "maximum_value", "step_value", "baseline_value"})
    if (not isinstance(control["target_ref"], str) or not control["target_ref"].startswith("accessible-control:")
            or control["role"] != "slider" or control["accessible_name"] != "Text size"
            or control["input_type"] != "range"):
        raise ObservationContractError("Resize Text control is not the fixed accessible range control")
    minimum = _decimal_text(control["minimum_value"])
    maximum = _decimal_text(control["maximum_value"])
    step = _decimal_text(control["step_value"], positive=True)
    baseline_value = _decimal_text(control["baseline_value"])
    if minimum is None or maximum is None or step is None or baseline_value is None or not minimum <= baseline_value <= maximum:
        raise ObservationContractError("Resize Text range bounds or baseline value are invalid")
    if not isinstance(value["text_population_complete"], bool) or not isinstance(value["mechanism_state_sequence_complete"], bool):
        raise ObservationContractError("Resize Text completeness fields must be booleans")
    sequence = value["mechanism_state_sequence"]
    if not isinstance(sequence, list) or not 2 <= len(sequence) <= 101:
        raise ObservationContractError("Resize Text requires a bounded baseline and state sequence")

    baseline_refs: set[str] = set()
    baseline_sizes: dict[str, Decimal] = {}
    baseline_controls: dict[str, bool] = {}
    normalized_states: list[dict[str, Any]] = []
    prior_control_value: Decimal | None = None
    for index, state in enumerate(sequence):
        if not isinstance(state, dict):
            raise ObservationContractError("Resize Text state must be an object")
        _exact_fields(state, {"state_index", "control_value", "document_identity", "viewport", "overflow",
                              "text_candidates", "interactive_controls", "population_complete",
                              "unmeasurable_target_refs", "unsupported_visible_canvas", "inaccessible_visible_frame",
                              "content_loss_refs", "newly_clipped_target_refs", "newly_obscured_target_refs",
                              "functionality_loss_refs"})
        if (state["state_index"] != index or isinstance(state["state_index"], bool)
                or state["document_identity"] != current_document_identity
                or not isinstance(state["population_complete"], bool)
                or not isinstance(state["unsupported_visible_canvas"], bool)
                or not isinstance(state["inaccessible_visible_frame"], bool)):
            raise ObservationContractError("Resize Text state identity or completeness is invalid")
        current_control_value = _decimal_text(state["control_value"])
        if current_control_value is None or not minimum <= current_control_value <= maximum:
            raise ObservationContractError("Resize Text state control value must be a finite decimal string")
        if index == 0:
            if current_control_value != baseline_value:
                raise ObservationContractError("Resize Text state sequence does not begin at its baseline value")
        elif prior_control_value is None or current_control_value <= prior_control_value or (current_control_value - prior_control_value) % step != 0:
            raise ObservationContractError("Resize Text state sequence must advance through the fixed control step")
        prior_control_value = current_control_value

        viewport = state["viewport"]
        overflow = state["overflow"]
        if not isinstance(viewport, dict) or set(viewport) != {"width_css_px", "height_css_px"}:
            raise ObservationContractError("Resize Text viewport measurement is invalid")
        if any((number := _decimal_number(viewport[key])) is None or number <= 0 for key in viewport):
            raise ObservationContractError("Resize Text viewport dimensions must be positive finite numbers")
        if not isinstance(overflow, dict) or set(overflow) != {"scroll_width_css_px", "client_width_css_px",
                                                               "scroll_height_css_px", "client_height_css_px"}:
            raise ObservationContractError("Resize Text overflow measurement is invalid")
        if any((number := _decimal_number(overflow[key])) is None or number < 0 for key in overflow):
            raise ObservationContractError("Resize Text overflow dimensions must be non-negative finite numbers")

        candidates = state["text_candidates"]
        if not isinstance(candidates, list) or not candidates:
            raise ObservationContractError("Resize Text state requires rendered text candidates")
        normalized_candidates: list[dict[str, Any]] = []
        state_refs: set[str] = set()
        for candidate in candidates:
            if not isinstance(candidate, dict):
                raise ObservationContractError("Resize Text candidate must be an object")
            _exact_fields(candidate, {"target_ref", "present", "used_font_size_css_px", "rects", "clipped", "obscured"})
            ref = candidate["target_ref"]
            if (not isinstance(ref, str) or not ref.startswith(("dom-text:", "dom-control:", "dom-element:"))
                    or len(ref) > 2048 or ref in state_refs or not isinstance(candidate["present"], bool)):
                raise ObservationContractError("Resize Text candidate identity is invalid or duplicated")
            state_refs.add(ref)
            font_size = _decimal_text(candidate["used_font_size_css_px"], positive=True)
            if (not isinstance(candidate["clipped"], bool) or not isinstance(candidate["obscured"], bool)
                    or (candidate["present"] and font_size is None)
                    or (not candidate["present"] and (font_size is not None or candidate["clipped"] or candidate["obscured"]))):
                raise ObservationContractError("Resize Text candidate font metric or loss evidence is invalid")
            rects = candidate["rects"]
            if not isinstance(rects, list) or (candidate["present"] and not rects) or (not candidate["present"] and rects):
                raise ObservationContractError("Resize Text candidate requires visible geometry evidence")
            normalized_rects: list[dict[str, Any]] = []
            for rect in rects:
                if not isinstance(rect, dict) or set(rect) != {"left", "top", "width", "height"}:
                    raise ObservationContractError("Resize Text candidate rectangle schema is invalid")
                values = {key: _decimal_number(rect[key]) for key in ("left", "top", "width", "height")}
                if any(number is None for number in values.values()) or values["width"] <= 0 or values["height"] <= 0:
                    raise ObservationContractError("Resize Text candidate rectangle values are invalid")
                normalized_rects.append({key: rect[key] for key in ("left", "top", "width", "height")})
            if index == 0:
                if not candidate["present"]:
                    raise ObservationContractError("Resize Text baseline candidate must be present")
                baseline_sizes[ref] = font_size
            elif ref not in baseline_sizes:
                if require_complete:
                    raise ObservationContractError("Resize Text candidate population changed after baseline")
            base_size = baseline_sizes.get(ref)
            ratio = None if base_size is None or font_size is None else font_size / base_size
            ratio_text = None if ratio is None else _decimal_string(ratio.quantize(Decimal("0.00000001")))
            normalized_candidates.append({"target_ref": ref,
                "baseline_used_font_size_css_px": None if base_size is None else _decimal_string(base_size),
                "current_used_font_size_css_px": None if font_size is None else _decimal_string(font_size),
                "rendered_scale_ratio": ratio_text, "rects": normalized_rects,
                "present": candidate["present"], "clipped": candidate["clipped"], "obscured": candidate["obscured"]})
        if index == 0:
            baseline_refs = state_refs
        elif state_refs != baseline_refs and require_complete:
            raise ObservationContractError("Resize Text text population is not stable across states")

        controls = state["interactive_controls"]
        if not isinstance(controls, list):
            raise ObservationContractError("Resize Text interactive controls evidence must be an array")
        normalized_controls: list[dict[str, Any]] = []
        current_controls: dict[str, bool] = {}
        for item in controls:
            if (not isinstance(item, dict) or set(item) != {"target_ref", "role", "enabled"}
                    or not isinstance(item["target_ref"], str) or not item["target_ref"].startswith("dom-control:")
                    or not isinstance(item["role"], str) or not item["role"].strip()
                    or not isinstance(item["enabled"], bool) or item["target_ref"] in current_controls):
                raise ObservationContractError("Resize Text interactive control evidence is invalid")
            current_controls[item["target_ref"]] = item["enabled"]
            normalized_controls.append(dict(item))
        if index == 0:
            baseline_controls = current_controls
        for loss_field in ("unmeasurable_target_refs", "content_loss_refs", "newly_clipped_target_refs",
                           "newly_obscured_target_refs", "functionality_loss_refs"):
            refs = state[loss_field]
            if (not isinstance(refs, list) or any(not isinstance(ref, str) or not ref.strip() for ref in refs)
                    or len(refs) != len(set(refs))):
                raise ObservationContractError(f"Resize Text {loss_field} must contain unique non-empty refs")
        if any(ref not in baseline_refs for ref in state["content_loss_refs"] + state["newly_clipped_target_refs"]
               + state["newly_obscured_target_refs"]):
            raise ObservationContractError("Resize Text loss evidence references an unknown baseline candidate")
        if any(ref not in baseline_controls for ref in state["functionality_loss_refs"]):
            raise ObservationContractError("Resize Text functionality loss references an unknown baseline control")
        normalized_states.append({**state, "text_candidates": normalized_candidates,
                                  "interactive_controls": normalized_controls})

    cleanup = value["cleanup"]
    if not isinstance(cleanup, dict):
        raise ObservationContractError("Resize Text cleanup evidence must be an object")
    _exact_fields(cleanup, {"status", "baseline_control_value", "current_control_value"})
    cleanup_baseline = _decimal_text(cleanup["baseline_control_value"])
    cleanup_current = _decimal_text(cleanup["current_control_value"])
    cleanup_ok = (cleanup["status"] == "restored" and cleanup_baseline == baseline_value
                  and cleanup_current == baseline_value)
    complete = (value["text_population_complete"] is True and all(state["population_complete"] is True
                and not state["unmeasurable_target_refs"] and not state["unsupported_visible_canvas"]
                and not state["inaccessible_visible_frame"] for state in sequence)
                and all(set(row["target_ref"] for row in state["text_candidates"]) == baseline_refs
                        for state in sequence))
    final_candidates = normalized_states[-1]["text_candidates"]
    reached_target = bool(final_candidates) and all(candidate["present"]
        and candidate["rendered_scale_ratio"] is not None
        and Decimal(candidate["rendered_scale_ratio"]) >= Decimal("2") for candidate in final_candidates)
    sequence_complete = (value["mechanism_state_sequence_complete"] is True
                         and (reached_target or prior_control_value == maximum))
    if require_complete and (not complete or not sequence_complete or not cleanup_ok):
        raise ObservationContractError("successful Resize Text result lacks complete population, state, or cleanup evidence")
    return {**value, "control": dict(control), "mechanism_state_sequence": normalized_states,
            "text_population_complete": complete, "mechanism_state_sequence_complete": sequence_complete,
            "cleanup": {**cleanup, "status": "restored" if cleanup_ok else "unverified"}}


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
        if (not isinstance(payload["session_target_ref"], str) or not payload["session_target_ref"].strip()
                or not is_document_identity_token(payload["document_identity"])):
            raise ObservationContractError("session resolver identity fields are required")
    else:
        raise ObservationContractError("unknown resolver kind")


def materialize_targets(drafts: list[dict[str, Any]], *, document_identity: str,
                        population_revisions: dict[str, Any] | None = None) -> dict[str, Any]:
    if not is_document_identity_token(document_identity):
        raise ObservationContractError("target materialization requires an opaque current-document identity token")
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
    if (not is_document_identity_token(current_document_identity)
            or not is_document_identity_token(resolution["current_document_identity"])):
        raise ObservationContractError("target resolution requires opaque current-document identity tokens")
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
        "2779a5": {"document.title"},
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
               "target_refs": list(target_refs or []) if OBSERVATION_FIELDS[field] not in {"viewport-state", "document-location", "document-title", "navigation-timing", "paint-timing", "responsive-conditions"} else [],
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
        "document.title": ["is_html_document", "has_html_title_descendant", "first_title_children_are_text",
                           "has_non_whitespace_text", "status", "limitation"],
        "element.rendered-text": ["raw_text", "status"], "element.control-value": ["raw_value", "status"],
        "element.selected-values": ["selected_options", "status"],
        "accessibility.semantics": ["role", "accessible_name", "description", "states", "host_element",
                                    "host_type", "included_in_accessibility_tree", "programmatically_hidden", "status"],
        "focus.state": ["active_target_ref", "focusable", "focus_visible", "status"],
        "computed-style.properties": ["properties", "status"],
        "responsive.conditions": ["conditions", "complete", "status"],
        "responsive.boundaries": ["boundaries", "complete", "status"],
        "navigation.timing": ["entries", "status"], "paint.timing": ["entries", "status"],
        "interaction.timing": ["start_ms", "end_ms", "elapsed_ms", "predicate_result", "clock_domain", "status"],
        "screenshot.image": ["evidence_ref", "viewport", "status"],
    }
    return fields[field]


def _normalize_responsive_boundaries(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ObservationContractError("responsive boundary value must be an object")
    _exact_fields(value, {"boundaries", "complete", "status"}, {"closures"})
    if not isinstance(value["complete"], bool) or value["status"] not in FORMAL_STATUSES:
        raise ObservationContractError("responsive boundary completeness/status is invalid")
    if value["status"] != "ok" or not value["complete"]:
        raise ObservationContractError("successful responsive boundary result must be complete")
    if not isinstance(value["boundaries"], list):
        raise ObservationContractError("responsive boundaries must be an array")

    required = {
        "condition_ref", "axis", "before_viewport_css_px", "transition_viewport_css_px",
        "after_viewport_css_px", "match_states", "raw_condition", "derivation_method",
        "execution_status",
    }
    optional = {"evidence_ref", "evidence_refs"}
    by_identity: dict[tuple[str, str, int], dict[str, Any]] = {}
    for row in value["boundaries"]:
        if not isinstance(row, dict):
            raise ObservationContractError("responsive boundary row must be an object")
        _exact_fields(row, required, optional)
        if not all(isinstance(row[name], str) and row[name].strip()
                   for name in ("condition_ref", "raw_condition", "derivation_method")):
            raise ObservationContractError("responsive boundary identity and derivation fields must be non-empty strings")
        axis = row["axis"]
        if axis not in {"width", "height"}:
            raise ObservationContractError("responsive boundary axis is not supported by the fixed contract")
        before, transition, after = (
            row["before_viewport_css_px"], row["transition_viewport_css_px"], row["after_viewport_css_px"]
        )
        if any(isinstance(number, bool) or not isinstance(number, int) or number < 0
               for number in (before, transition, after)):
            raise ObservationContractError("responsive boundary positions must be non-negative integer CSS px")
        if (transition != before + 1 or after != transition + 1):
            raise ObservationContractError("responsive boundary positions must be neighboring CSS px values")
        states = row["match_states"]
        if (not isinstance(states, list) or len(states) != 3
                or any(not isinstance(state, bool) for state in states)
                or states[0] == states[1] or states[1] != states[2]):
            raise ObservationContractError("responsive boundary must retain a verified before/transition/after match sequence")
        if row["execution_status"] not in {"executable", "not-executable"}:
            raise ObservationContractError("responsive boundary execution status is invalid")
        refs: list[str] = []
        if "evidence_ref" in row:
            refs.append(row["evidence_ref"])
        if "evidence_refs" in row:
            evidence_refs = row["evidence_refs"]
            if not isinstance(evidence_refs, list):
                raise ObservationContractError("responsive boundary evidence_refs must be an array")
            refs.extend(evidence_refs)
        if not refs or any(not isinstance(ref, str) or not ref.strip() for ref in refs):
            raise ObservationContractError("responsive boundary requires non-empty evidence references")

        normalized = {
            "condition_ref": row["condition_ref"],
            "axis": axis,
            "before_viewport_css_px": before,
            "transition_viewport_css_px": transition,
            "after_viewport_css_px": after,
            "match_states": states,
            "raw_condition": row["raw_condition"],
            "derivation_method": row["derivation_method"],
            "execution_status": row["execution_status"],
            "evidence_refs": sorted(set(refs)),
        }
        identity = (row["condition_ref"], axis, transition)
        existing = by_identity.get(identity)
        if existing is not None:
            left = {key: item for key, item in existing.items() if key != "evidence_refs"}
            right = {key: item for key, item in normalized.items() if key != "evidence_refs"}
            if left != right:
                raise ObservationContractError("duplicate responsive boundary identity has conflicting observations")
            existing["evidence_refs"] = sorted(set(existing["evidence_refs"] + normalized["evidence_refs"]))
        else:
            by_identity[identity] = normalized

    boundaries = []
    for index, identity in enumerate(sorted(by_identity), 1):
        boundaries.append({
            "boundary_ref": f"BOUNDARY-{index:03d}",
            **by_identity[identity],
            "detection_status": "normalized",
        })
    closures_by_identity: dict[tuple[str, str], dict[str, str]] = {}
    closures = value.get("closures", [])
    if not isinstance(closures, list):
        raise ObservationContractError("responsive boundary closures must be an array")
    allowed_closure_statuses = {
        "non-numeric-presentation-variation", "no-numeric-transition", "not-executable", "unsupported",
    }
    for row in closures:
        if not isinstance(row, dict):
            raise ObservationContractError("responsive boundary closure must be an object")
        _exact_fields(row, {"condition_ref", "status", "reason"})
        if (not isinstance(row["condition_ref"], str) or not row["condition_ref"].strip()
                or row["status"] not in allowed_closure_statuses
                or not isinstance(row["reason"], str) or not row["reason"].strip()):
            raise ObservationContractError("responsive boundary closure fields are invalid")
        identity_key = (row["condition_ref"], row["status"])
        normalized = {"condition_ref": row["condition_ref"], "status": row["status"], "reason": row["reason"]}
        existing = closures_by_identity.get(identity_key)
        if existing is not None and existing != normalized:
            raise ObservationContractError("duplicate responsive closure has conflicting reasons")
        closures_by_identity[identity_key] = normalized
    normalized_closures = [closures_by_identity[key] for key in sorted(closures_by_identity)]
    return {"boundaries": boundaries, "closures": normalized_closures, "complete": True, "status": "ok"}


def _normalize_responsive_conditions(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ObservationContractError("responsive conditions value must be an object")
    _exact_fields(value, {"conditions", "complete", "status"}, {"issues", "viewport"})
    if value["status"] != "ok" or value["complete"] is not True:
        raise ObservationContractError("successful responsive conditions must be complete")
    if not isinstance(value["conditions"], list):
        raise ObservationContractError("responsive conditions must be an array")
    required = {
        "condition_ref", "source_ref", "query_kind", "raw_condition", "browser_capability",
        "evaluation_method", "current_match_state", "execution_status", "execution_reason", "evidence_refs",
    }
    optional = {"query_container_name", "query_container_type", "query_container_identity", "axis", "feature"}
    kinds = {"media", "container-size", "container-style", "container-scroll-state"}
    statuses = {"executable", "not-executable", "unsupported"}
    normalized_rows: list[dict[str, Any]] = []
    refs: set[str] = set()
    for row in value["conditions"]:
        if not isinstance(row, dict):
            raise ObservationContractError("responsive condition row must be an object")
        _exact_fields(row, required, optional)
        for name in ("condition_ref", "source_ref", "raw_condition", "evaluation_method"):
            if not isinstance(row[name], str) or not row[name].strip():
                raise ObservationContractError(f"responsive condition {name} must be non-empty")
        if row["condition_ref"] in refs:
            raise ObservationContractError("responsive condition refs must be unique")
        refs.add(row["condition_ref"])
        if row["query_kind"] not in kinds or row["execution_status"] not in statuses:
            raise ObservationContractError("responsive query kind or execution status is unsupported")
        if row["browser_capability"] not in {"available", "unavailable"}:
            raise ObservationContractError("responsive browser capability status is invalid")
        if row["current_match_state"] is not None and not isinstance(row["current_match_state"], bool):
            raise ObservationContractError("responsive current match state must be boolean or null")
        if row["execution_status"] != "executable" and (
                not isinstance(row["execution_reason"], str) or not row["execution_reason"].strip()):
            raise ObservationContractError("unexecutable responsive condition requires a reason")
        if row["execution_status"] == "executable" and row["current_match_state"] is None:
            raise ObservationContractError("executable responsive condition requires a current match state")
        evidence_refs = row["evidence_refs"]
        if (not isinstance(evidence_refs, list) or not evidence_refs
                or any(not isinstance(ref, str) or not ref.strip() for ref in evidence_refs)):
            raise ObservationContractError("responsive condition requires evidence refs")
        normalized_rows.append({key: row[key] for key in sorted(row)})
    if "issues" in value and not isinstance(value["issues"], list):
        raise ObservationContractError("responsive condition issues must be an array")
    result: dict[str, Any] = {
        "conditions": sorted(normalized_rows, key=lambda row: row["condition_ref"]),
        "complete": True,
        "status": "ok",
    }
    if "issues" in value:
        result["issues"] = value["issues"]
    if "viewport" in value:
        viewport = value["viewport"]
        if (not isinstance(viewport, dict) or set(viewport) != {"width_css_px", "height_css_px"}
                or any(isinstance(viewport[name], bool) or not isinstance(viewport[name], int) or viewport[name] < 0
                       for name in ("width_css_px", "height_css_px"))):
            raise ObservationContractError("responsive viewport metrics are invalid")
        result["viewport"] = viewport
    return result


def _normalize_interaction_timing(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ObservationContractError("interaction timing value must be an object")
    required = {"start_ms", "end_ms", "elapsed_ms", "predicate_result", "clock_domain", "status"}
    _exact_fields(value, required)
    if (value["status"] != "ok" or value["clock_domain"] != "same-page-performance-now"
            or not isinstance(value["predicate_result"], dict)
            or set(value["predicate_result"]) != {"predicate_key", "matched"}
            or value["predicate_result"]["predicate_key"] not in PREDICATES
            or value["predicate_result"]["matched"] is not True):
        raise ObservationContractError("interaction timing status, clock, or predicate result is invalid")
    timestamps = (value["start_ms"], value["end_ms"], value["elapsed_ms"])
    decimals = [_decimal_number(number) for number in timestamps]
    if any(number is None or number < 0 for number in decimals):
        raise ObservationContractError("interaction timing values must be finite non-negative numbers")
    if len(decimals) != 3:
        raise ObservationContractError("interaction timing values must be finite non-negative numbers")
    start_ms, end_ms, elapsed_ms = decimals
    if start_ms is None or end_ms is None or elapsed_ms is None:
        raise ObservationContractError("interaction timing values must be finite non-negative numbers")
    if end_ms < start_ms or abs(elapsed_ms - (end_ms - start_ms)) > Decimal("0.01"):
        raise ObservationContractError("interaction timing elapsed value does not match its same-page timestamps")
    return {**value, "predicate_result": dict(value["predicate_result"])}


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
        identity_unavailable = (
            result["current_document_identity"] is None and current_document_identity is None
        )
        if identity_unavailable:
            if (result["status"] != "blocked"
                    or result.get("limitation") != FORMAL_DOCUMENT_IDENTITY_UNAVAILABLE
                    or result.get("limitation_code") is not None
                    or "value" in result
                    or result.get("evidence_refs") != []):
                raise ObservationContractError(
                    "missing current-document identity is only valid for the fixed fail-closed WebCrypto limitation"
                )
        elif not is_document_identity_token(result["current_document_identity"]):
            raise ObservationContractError("formal result requires an opaque current-document identity token")
        evidence_refs = result.get("evidence_refs")
        if not isinstance(evidence_refs, list) or any(not isinstance(ref, str) or not ref.strip() for ref in evidence_refs):
            raise ObservationContractError("formal evidence_refs must be a string array")
        if result["status"] == "ok" and not isinstance(result.get("value"), dict):
            raise ObservationContractError("successful formal probe requires a typed value object")
        if result["status"] == "incomplete" and result.get("limitation_code") is None:
            value = result.get("value")
            completeness = value.get("observation_completeness") if isinstance(value, dict) else None
            if (not isinstance(completeness, dict) or set(completeness) != {"state", "reason"}
                    or completeness.get("state") != "partial"
                    or completeness.get("reason") not in PARTIAL_FORMAL_OBSERVATION_REASONS):
                raise ObservationContractError("incomplete formal observation requires a typed partial result reason")
        if result["machine_probe_key"] in PARTIAL_CANDIDATE_NAME_FREE_PROBES:
            value = result.get("value")
            if result["machine_probe_key"] == "mp-multipage-signature" and isinstance(value, dict):
                page_signature = value.get("current_page_signature")
                candidate_rows = page_signature.get("controls") if isinstance(page_signature, dict) else None
            else:
                candidate_rows = value.get("candidate_targets") if isinstance(value, dict) else None
            if (result["status"] == "incomplete"
                    and candidate_rows is not None
                    and (not isinstance(candidate_rows, list)
                         or any(not isinstance(row, dict) or "accessible_name" in row
                                for row in candidate_rows))):
                raise ObservationContractError(
                    "partial formal candidate summaries must omit accessible-name text"
                )
        if result["status"] in {"unsupported", "unavailable", "incomplete", "blocked"}:
            if not isinstance(result.get("limitation"), str) or not result["limitation"].strip():
                raise ObservationContractError("non-success formal probe requires a limitation")
        if (not identity_unavailable
                and result["current_document_identity"] != current_document_identity):
            result = {**result, "status": "blocked", "limitation_code": None, "limitation": "stale_document"}
        code = result.get("limitation_code")
        if code is not None and code not in LIMITATION_CODES:
            raise ObservationContractError("unknown formal limitation code")
        limitation_status = {
            "background-not-machine-resolvable": "unavailable",
            "focus-indicator-not-machine-resolvable": "incomplete",
            "text-scaling-mechanism-not-machine-executable": "unsupported",
            "text-scaling-state-not-machine-readable": "unavailable",
        }
        if code is not None and limitation_status[code] != result["status"]:
            raise ObservationContractError("formal limitation code does not match its fixed machine status")
        normalized_result = dict(result)
        if result["machine_probe_key"] == "mp-resize-text-run" and "value" in result:
            normalized_result["value"] = _normalize_resize_text_value(
                result["value"], current_document_identity=current_document_identity,
                require_complete=result["status"] == "ok")
        return {**normalized_result, "normalized": True,
                "input_fingerprint": fingerprint({k: formal_request[k] for k in sorted(formal_request) if k != "request_signature"})}

    if (not is_document_identity_token(current_document_identity)
            or not is_document_identity_token(result.get("document_identity"))):
        raise ObservationContractError("probe requires opaque current-document identity tokens")
    if result.get("probe_key") != probe["probe_key"] or result.get("document_identity") != current_document_identity:
        raise ObservationContractError("probe identity mismatch or stale document")
    if result.get("status") not in {"ok", "unavailable", "unsupported", "incomplete", "blocked"}:
        raise ObservationContractError("invalid probe status")
    if result.get("status") == "ok" and not isinstance(result.get("value"), dict):
        raise ObservationContractError("successful probe result requires an object value")
    missing = set(probe["required_result_fields"]) - set(result.get("value", {})) if result.get("status") == "ok" else set()
    if missing:
        raise ObservationContractError(f"missing required result values: {sorted(missing)}")
    if result["status"] != "ok" and (not isinstance(result.get("limitation"), str) or not result["limitation"].strip()):
        raise ObservationContractError("non-success probe result requires a limitation")
    evidence_refs = result.get("evidence_refs", [])
    if not isinstance(evidence_refs, list) or any(not isinstance(ref, str) or not ref.strip() for ref in evidence_refs):
        raise ObservationContractError("evidence refs must be non-empty strings")
    value = result.get("value", {})
    if probe["observation_field"] == "document.location" and result.get("status") == "ok":
        if (set(value) != {"safe_url", "status", "limitation"}
                or value["safe_url"] not in {"http://[redacted]", "https://[redacted]"}
                or value["status"] != "ok" or value["limitation"] is not None):
            raise ObservationContractError("document location must contain only a redacted HTTP(S) scheme marker")
    if probe["observation_field"] == "responsive.boundaries" and result.get("status") == "ok":
        value = _normalize_responsive_boundaries(value)
    if probe["observation_field"] == "responsive.conditions" and result.get("status") == "ok":
        value = _normalize_responsive_conditions(value)
    if probe["observation_field"] == "interaction.timing" and result.get("status") == "ok":
        value = _normalize_interaction_timing(value)
    if probe["observation_field"] == "element.geometry" and result.get("status") == "ok":
        for name in ("x_css_px", "y_css_px", "width_css_px", "height_css_px"):
            if _decimal_number(value[name]) is None:
                raise ObservationContractError("geometry values must be numeric CSS px")
    if probe["observation_field"] == "document.title" and result.get("status") == "ok":
        if (set(value) != {"is_html_document", "has_html_title_descendant", "first_title_children_are_text",
                           "has_non_whitespace_text", "status", "limitation"}
                or value["status"] != "ok" or value["limitation"] is not None
                or any(not isinstance(value[field], bool) for field in (
                    "is_html_document", "has_html_title_descendant", "first_title_children_are_text",
                    "has_non_whitespace_text"))):
            raise ObservationContractError("fixed document-title observation values are invalid")
    if probe["observation_field"] == "accessibility.semantics" and result.get("status") == "ok":
        if (not isinstance(value["role"], str) or not value["role"].strip()
                or not isinstance(value["accessible_name"], str)
                or (value["description"] is not None and not isinstance(value["description"], str))
                or not isinstance(value["states"], dict)
                or not isinstance(value["host_element"], str) or not value["host_element"].strip()
                or (value["host_type"] is not None and not isinstance(value["host_type"], str))
                or not isinstance(value["included_in_accessibility_tree"], bool)
                or not isinstance(value["programmatically_hidden"], bool)
                or value["status"] != "ok"):
            raise ObservationContractError("accessibility semantics applicability values are invalid")
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
                "variation_ref", "requirement_ref")) or not is_document_identity_token(request["target_identity"]):
        raise ObservationContractError("formal typed request identity fields must be non-empty strings")
    if request["process_ref"] is not None and (not isinstance(request["process_ref"], str) or not request["process_ref"].strip()):
        raise ObservationContractError("formal process ref must be a non-empty string or null")
    if not isinstance(request["currentness_dependency"], dict) or not request["currentness_dependency"]:
        raise ObservationContractError("formal currentness dependency must be a non-empty object")
    dependency = request["currentness_dependency"]
    if (set(dependency) != {"sample_identity_fingerprint", "variation_identity_fingerprint"}
            or any(not isinstance(value, str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", value)
                   for value in dependency.values())):
        raise ObservationContractError("formal currentness dependency must contain only canonical sample and variation fingerprints")
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
    if not is_document_identity_token(draft["current_document_identity"]):
        raise ObservationContractError("additional request requires an opaque current-document identity token")
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
        raise ObservationContractError(f"each of the {len(OBSERVATION_FIELDS)} canonical observation fields must have exactly one probe owner")
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
