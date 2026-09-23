"""Normalize JSON Schema, OpenAPI 3.0, and extracted HTML controls into child skeletons."""

from __future__ import annotations

from urllib.parse import unquote_to_bytes
from pathlib import Path
import re
import sys
from typing import Any

from runtime_contract import ExactNumber, InvalidInput, UnsupportedInput, canonical_decimal, canonicalize, ensure_int, ensure_list, ensure_nonempty_string, exact_compare, exact_to_decimal, make_unsupported_item, post_process_targets, reject_unknown, run_cli, sha256_digest, typed_value


SKILL = "test-condition-design"
GENERATOR = "schema_cases"
GENERATOR_CONTRACT_VERSION = "schema-cases-v1"
SCRIPT_PATH = Path(__file__).resolve()
SCHEMA_KINDS = {"json-schema-2020-12", "openapi-3.0", "html-control"}
CHILD_TYPES = {"ep", "bva", "comb"}
ANNOTATIONS = {"title", "description", "$comment", "default", "examples"}
JSON_SCHEMA_KEYWORDS = {"$schema", "$id", "$defs", "$ref", "type", "properties", "items", "enum", "const", "required", "minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum", "multipleOf", "minLength", "maxLength", "minItems", "maxItems", "minProperties", "maxProperties", "title", "description", "$comment", "default", "examples"}
OPENAPI_KEYWORDS = {"$ref", "type", "format", "title", "description", "default", "example", "deprecated", "readOnly", "writeOnly", "nullable", "required", "properties", "items", "enum", "minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum", "multipleOf", "minLength", "maxLength", "minItems", "maxItems", "additionalProperties"}
SCHEMA_UNSUPPORTED_REASONS = {"cyclic_local_ref", "unsupported_reference", "unsupported_schema_keyword", "unsupported_value_shape", "unsupported_html_control", "unsupported_html_constraint"}


def _decode_pointer_token(raw: str) -> str:
    if "%" in raw and re.search(r"%(?![0-9A-Fa-f]{2})", raw):
        raise InvalidInput("schema JSON Pointer percent escapeが不正です")
    try:
        return unquote_to_bytes(raw.encode("utf-8")).decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise InvalidInput("schema JSON PointerはUTF-8である必要があります") from exc


def _pointer(document: Any, pointer: str) -> Any:
    if pointer in {"", "#"}:
        return document
    if not isinstance(pointer, str) or not pointer.startswith("#/"):
        raise InvalidInput("schema_pointerはlocal JSON Pointerである必要があります")
    current = document
    for raw in pointer[2:].split("/"):
        token = _decode_pointer_token(raw)
        if "~" in token:
            index = 0
            decoded = []
            while index < len(token):
                if token[index] != "~":
                    decoded.append(token[index])
                    index += 1
                    continue
                if index + 1 >= len(token) or token[index + 1] not in "01":
                    raise InvalidInput("schema JSON Pointer escapeが不正です")
                decoded.append("/" if token[index + 1] == "1" else "~")
                index += 2
            token = "".join(decoded)
        if isinstance(current, dict):
            if token not in current:
                raise InvalidInput("schema JSON Pointerが存在しません")
            current = current[token]
        elif isinstance(current, list):
            if not re.fullmatch(r"0|[1-9][0-9]*", token) or int(token) >= len(current):
                raise InvalidInput("schema JSON Pointer array indexが不正です")
            current = current[int(token)]
        else:
            raise InvalidInput("schema JSON Pointerがscalarへ到達しました")
    return current


def _typed_scalar(value: Any, name: str) -> dict[str, Any]:
    if isinstance(value, ExactNumber):
        text = exact_to_decimal(value)
        return {"type": "integer" if "." not in text else "decimal", "value": int(text) if "." not in text else text}
    if value is None:
        return {"type": "null", "value": None}
    if isinstance(value, bool):
        return {"type": "boolean", "value": value}
    if isinstance(value, int):
        return {"type": "integer", "value": value}
    if isinstance(value, str):
        return {"type": "string", "value": value}
    raise UnsupportedInput("object/array enum valueはruntime-v1未対応です", source_key=name, reason_code="unsupported_value_shape")


def _source_digest(kind: str, pointer: str, keyword: str, role: str) -> tuple[str, str]:
    digest = sha256_digest({"schema_kind": kind, "schema_pointer": pointer, "keyword": keyword, "role": role})
    return digest, "h" + digest.split(":", 1)[1]


def _resolve_schema(document: dict, schema: dict, base_pointer: str, active: set[str], unsupported: list[dict], *, kind: str) -> dict:
    if not isinstance(schema, dict):
        raise InvalidInput("schema subtreeはobjectである必要があります")
    if "$ref" not in schema:
        return schema
    ref = schema["$ref"]
    if not isinstance(ref, str) or not ref.startswith("#") or (ref != "#" and not ref.startswith("#/")):
        raise UnsupportedInput("external schema referenceは未対応です", source_key=ref if isinstance(ref, str) else base_pointer, reason_code="unsupported_reference")
    if ref in active:
        unsupported.append(make_unsupported_item(generator=GENERATOR, item_type="schema_subtree", source_key=ref, reason_code="cyclic_local_ref"))
        return {}
    target = _pointer(document, ref)
    active.add(ref)
    resolved = _resolve_schema(document, target, ref, active, unsupported, kind=kind)
    active.remove(ref)
    siblings = {key: value for key, value in schema.items() if key != "$ref"}
    if kind == "openapi-3.0":
        # OpenAPI Reference Objects ignore sibling fields; they are not
        # Schema Object assertions and must not be merged into the target.
        siblings = {}
    if any(key not in (OPENAPI_KEYWORDS if kind == "openapi-3.0" else JSON_SCHEMA_KEYWORDS) for key in siblings):
        unsupported.append(make_unsupported_item(generator=GENERATOR, item_type="schema_subtree", source_key=base_pointer, reason_code="unsupported_schema_keyword"))
    return {**resolved, **siblings}


def _test_data_requirement(kind: str, source_pointer: str, keyword: str, dimension_role: str, model_key: str, operator: str, **fields: Any) -> dict[str, Any]:
    requirement_key = "schema-" + _source_digest(kind, source_pointer, keyword, "test-data-requirement")[1]
    dimension_key = "schema-" + _source_digest(kind, source_pointer, dimension_role, "test-data-dimension")[1]
    return {
        "requirement_key": requirement_key,
        "environment_key": None,
        "dimension_key": dimension_key,
        "operator": operator,
        "authority_refs": [],
        "source_model_key": model_key,
        "source_target_versions": [],
        **fields,
    }


def _json_skeletons(kind: str, document: dict, pointer: str, context: str, unsupported: list[dict], model_key: str) -> tuple[list[dict], list[dict], list[dict], list[dict], list[dict]]:
    keywords = OPENAPI_KEYWORDS if kind == "openapi-3.0" else JSON_SCHEMA_KEYWORDS
    root = _resolve_schema(document, _pointer(document, pointer), pointer, {pointer}, unsupported, kind=kind)
    ep_sets: list[dict] = []
    bva_boundaries: list[dict] = []
    factors: list[dict] = []
    grid_constraints: list[dict] = []
    data_requirements: list[dict] = []

    def visit(schema: dict, schema_pointer: str, label: str) -> None:
        if not isinstance(schema, dict):
            raise InvalidInput("schema subtreeが不正です")
        if "required" in schema:
            required = schema["required"]
            if not isinstance(required, list) or not all(isinstance(item, str) and item for item in required) or len(required) != len(set(required)):
                raise InvalidInput("schema.requiredが不正です")
        properties = schema.get("properties")
        if properties is not None and (not isinstance(properties, dict) or any(not isinstance(key, str) or not isinstance(value, dict) for key, value in properties.items())):
            raise InvalidInput("schema.propertiesが不正です")
        allowed_types = {"array", "boolean", "integer", "number", "object", "string"}
        if kind == "json-schema-2020-12":
            allowed_types = allowed_types | {"null"}
        schema_type = schema.get("type")
        if isinstance(schema_type, str) and schema_type not in allowed_types:
            unsupported.append(make_unsupported_item(generator=GENERATOR, item_type="schema_subtree", source_key=schema_pointer, reason_code="unsupported_value_shape"))
        if kind == "openapi-3.0":
            if "nullable" in schema and not isinstance(schema["nullable"], bool):
                raise InvalidInput("OpenAPI nullableが不正です")
            if schema.get("readOnly") is True and schema.get("writeOnly") is True:
                raise InvalidInput("OpenAPI readOnly/writeOnlyを同時指定できません")
            if isinstance(schema.get("type"), list):
                raise InvalidInput("OpenAPI type unionはruntime-v1未対応です")
        unknown = set(schema) - keywords
        if unknown:
            unsupported.append(make_unsupported_item(generator=GENERATOR, item_type="schema_subtree", source_key=schema_pointer, reason_code="unsupported_schema_keyword"))
        if "$anchor" in schema or "$dynamicAnchor" in schema or "$dynamicRef" in schema or ("$id" in schema and schema_pointer != pointer):
            unsupported.append(make_unsupported_item(generator=GENERATOR, item_type="schema_subtree", source_key=schema_pointer, reason_code="unsupported_reference"))
        if "enum" in schema:
            try:
                values = [_typed_scalar(value, schema_pointer) for value in ensure_list(schema["enum"], f"{schema_pointer}.enum")]
            except UnsupportedInput as exc:
                unsupported.append(make_unsupported_item(generator=GENERATOR, item_type="schema_subtree", source_key=exc.source_key or schema_pointer, reason_code="unsupported_value_shape"))
                values = []
            if not values or len({str(value) for value in values}) != len(values):
                if schema["enum"] == []:
                    raise InvalidInput("schema enumが不正です")
            else:
                data_requirements.append(_test_data_requirement(kind, schema_pointer, "enum", "value", model_key, "enum", values=values))
                _digest, set_key = _source_digest(kind, schema_pointer, "enum", "set")
                partitions = []
                for index, value in enumerate(values):
                    _digest, partition_key = _source_digest(kind, schema_pointer, f"enum[{index}]", "partition")
                    partitions.append({"partition_key": partition_key, "label": f"{label} enum {index + 1}", "validity": "valid", "definition": {"type": "enum", "values": [value]}, "representative": value, "authority_refs": []})
                ep_sets.append({"set_key": set_key, "label": label, "partitions": partitions, "source_pointer": schema_pointer, "keyword": "enum"})
        if "const" in schema:
            try:
                value = _typed_scalar(schema["const"], schema_pointer)
            except UnsupportedInput as exc:
                unsupported.append(make_unsupported_item(generator=GENERATOR, item_type="schema_subtree", source_key=exc.source_key or schema_pointer, reason_code="unsupported_value_shape"))
                value = None
            if value is not None:
                data_requirements.append(_test_data_requirement(kind, schema_pointer, "const", "value", model_key, "enum", values=[value]))
                _digest, set_key = _source_digest(kind, schema_pointer, "const", "set")
                _digest, partition_key = _source_digest(kind, schema_pointer, "const", "partition")
                ep_sets.append({"set_key": set_key, "label": label, "partitions": [{"partition_key": partition_key, "label": f"{label} const", "validity": "valid", "definition": {"type": "enum", "values": [value]}, "representative": value, "authority_refs": []}], "source_pointer": schema_pointer, "keyword": "const"})
        bounds: list[tuple[str, str, bool]] = []
        if kind == "openapi-3.0":
            if "exclusiveMinimum" in schema and not isinstance(schema["exclusiveMinimum"], bool):
                raise InvalidInput("OpenAPI exclusiveMinimumはbooleanである必要があります")
            if "exclusiveMaximum" in schema and not isinstance(schema["exclusiveMaximum"], bool):
                raise InvalidInput("OpenAPI exclusiveMaximumはbooleanである必要があります")
            if "exclusiveMinimum" in schema and schema["exclusiveMinimum"] and "minimum" not in schema:
                raise InvalidInput("OpenAPI exclusiveMinimumにはminimumが必要です")
            if "exclusiveMaximum" in schema and schema["exclusiveMaximum"] and "maximum" not in schema:
                raise InvalidInput("OpenAPI exclusiveMaximumにはmaximumが必要です")
            if "minimum" in schema:
                bounds.append(("minimum", "lower", not schema.get("exclusiveMinimum", False)))
            if "maximum" in schema:
                bounds.append(("maximum", "upper", not schema.get("exclusiveMaximum", False)))
        else:
            if "exclusiveMinimum" in schema and isinstance(schema["exclusiveMinimum"], bool):
                raise InvalidInput("JSON Schema exclusiveMinimumはnumberである必要があります")
            if "exclusiveMaximum" in schema and isinstance(schema["exclusiveMaximum"], bool):
                raise InvalidInput("JSON Schema exclusiveMaximumはnumberである必要があります")
            if "minimum" in schema:
                bounds.append(("minimum", "lower", True))
            if "exclusiveMinimum" in schema:
                bounds.append(("exclusiveMinimum", "lower", False))
            if "maximum" in schema:
                bounds.append(("maximum", "upper", True))
            if "exclusiveMaximum" in schema:
                bounds.append(("exclusiveMaximum", "upper", False))
        numeric_keywords = {keyword for keyword, _side, _inclusive in bounds}
        for keyword in numeric_keywords:
            raw_value = schema[keyword]
            if isinstance(raw_value, bool) or not isinstance(raw_value, (int, ExactNumber)):
                raise InvalidInput(f"schema.{keyword}はnumberである必要があります")
        lower_constraint: tuple[dict[str, Any], bool] | None = None
        upper_constraint: tuple[dict[str, Any], bool] | None = None
        for keyword, side, inclusive in bounds:
            value = _typed_scalar(schema["minimum" if keyword == "minimum" and kind == "openapi-3.0" else "maximum" if keyword == "maximum" and kind == "openapi-3.0" else keyword], schema_pointer)
            if side == "lower":
                if lower_constraint is None or exact_compare(str(value["value"]), str(lower_constraint[0]["value"])) > 0 or (exact_compare(str(value["value"]), str(lower_constraint[0]["value"])) == 0 and not inclusive):
                    lower_constraint = (value, inclusive)
            elif upper_constraint is None or exact_compare(str(value["value"]), str(upper_constraint[0]["value"])) < 0 or (exact_compare(str(value["value"]), str(upper_constraint[0]["value"])) == 0 and not inclusive):
                upper_constraint = (value, inclusive)
            _digest, boundary_key = _source_digest(kind, schema_pointer, keyword, "bva-boundary")
            bva_boundaries.append({"boundary_key": boundary_key, "label": f"{label} {keyword}", "side": side, "threshold": value, "inclusive": inclusive, "step": {"unit": "integer" if value["type"] == "integer" else "decimal", "amount": 1 if value["type"] == "integer" else "1"}, "source_pointer": schema_pointer, "keyword": keyword, "authority_refs": []})
        if lower_constraint is not None and upper_constraint is not None:
            minimum, minimum_inclusive = lower_constraint
            maximum, maximum_inclusive = upper_constraint
            if minimum["type"] != maximum["type"]:
                minimum = {"type": "decimal", "value": str(minimum["value"])}
                maximum = {"type": "decimal", "value": str(maximum["value"])}
            data_requirements.append(_test_data_requirement(kind, schema_pointer, "numeric-range", "value", model_key, "range", minimum=minimum, maximum=maximum, minimum_inclusive=minimum_inclusive, maximum_inclusive=maximum_inclusive))
        for keyword, side in (("minLength", "lower"), ("maxLength", "upper"), ("minItems", "lower"), ("maxItems", "upper"), ("minProperties", "lower"), ("maxProperties", "upper")):
            if keyword not in schema:
                continue
            value = schema[keyword]
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise InvalidInput(f"schema.{keyword}が不正です")
            _digest, boundary_key = _source_digest(kind, schema_pointer, keyword, "bva-boundary")
            bva_boundaries.append({"boundary_key": boundary_key, "label": f"{label} {keyword}", "side": side, "threshold": {"type": "integer", "value": value}, "inclusive": True, "step": {"unit": "integer", "amount": 1}, "source_pointer": schema_pointer, "keyword": keyword, "authority_refs": []})
        for minimum_key, maximum_key in (("minLength", "maxLength"), ("minItems", "maxItems"), ("minProperties", "maxProperties")):
            if minimum_key in schema and maximum_key in schema and schema[minimum_key] > schema[maximum_key]:
                raise InvalidInput(f"schema.{minimum_key}がschema.{maximum_key}を超えています")
            if minimum_key in schema and maximum_key in schema:
                dimension_role = {"minLength": "length", "minItems": "item-count", "minProperties": "property-count"}[minimum_key]
                data_requirements.append(_test_data_requirement(kind, schema_pointer, f"{minimum_key}-{maximum_key}", dimension_role, model_key, "range", minimum={"type": "integer", "value": schema[minimum_key]}, maximum={"type": "integer", "value": schema[maximum_key]}, minimum_inclusive=True, maximum_inclusive=True))
        if "multipleOf" in schema:
            multiple = schema["multipleOf"]
            if isinstance(multiple, bool) or not isinstance(multiple, (int, ExactNumber)):
                raise InvalidInput("schema.multipleOfが不正です")
            multiple_text = exact_to_decimal(multiple)
            if exact_compare(multiple_text, "0") <= 0:
                raise InvalidInput("schema.multipleOfは正である必要があります")
            declared_type = schema.get("type")
            if isinstance(declared_type, list):
                declared_type = next((value for value in declared_type if value != "null"), None)
            if declared_type in {None, "integer", "number"}:
                _digest, grid_key = _source_digest(kind, schema_pointer, "multipleOf", "grid")
                grid_constraints.append({"grid_key": grid_key, "operator": "grid", "base": {"type": "decimal", "value": "0"}, "step": {"type": "decimal", "value": canonical_decimal(multiple_text)}, "source_pointer": schema_pointer, "keyword": "multipleOf", "authority_refs": []})
        scalar_type = schema.get("type")
        if isinstance(scalar_type, list):
            if len(scalar_type) != 2 or "null" not in scalar_type:
                unsupported.append(make_unsupported_item(generator=GENERATOR, item_type="schema_subtree", source_key=schema_pointer, reason_code="unsupported_schema_keyword"))
                scalar_type = None
            else:
                scalar_type = next(value for value in scalar_type if value != "null")
        if scalar_type in {"string", "integer", "number", "boolean"} or "enum" in schema or "const" in schema:
            _digest, factor_key = _source_digest(kind, schema_pointer, "type", "factor")
            values = []
            if "enum" in schema:
                values = [_typed_scalar(value, schema_pointer) for value in schema["enum"]]
            elif scalar_type == "boolean":
                values = [{"type": "boolean", "value": False}, {"type": "boolean", "value": True}]
            elif scalar_type in {"integer", "number"}:
                lower_bound = next((keyword for keyword, side, _inclusive in bounds if side == "lower"), None)
                upper_bound = next((keyword for keyword, side, _inclusive in bounds if side == "upper"), None)
                if lower_bound is not None and upper_bound is not None:
                    lower_key = "minimum" if kind == "openapi-3.0" and lower_bound == "minimum" else lower_bound
                    upper_key = "maximum" if kind == "openapi-3.0" and upper_bound == "maximum" else upper_bound
                    values = [_typed_scalar(schema[lower_key], schema_pointer), _typed_scalar(schema[upper_key], schema_pointer)]
            if values:
                factor = {"factor_key": factor_key, "label": label, "values": values, "source_pointer": schema_pointer, "keyword": "type", "authority_refs": []}
                if kind == "openapi-3.0":
                    factor["allows_null"] = schema.get("nullable", False) is True
                elif isinstance(schema.get("type"), list):
                    factor["allows_null"] = True
                factors.append(factor)
        if properties is not None:
            if not isinstance(properties, dict):
                raise InvalidInput("schema.propertiesが不正です")
            for name in sorted(properties):
                child = properties[name]
                if kind == "openapi-3.0" and context == "request" and isinstance(child, dict) and child.get("readOnly") is True:
                    continue
                if kind == "openapi-3.0" and context == "response" and isinstance(child, dict) and child.get("writeOnly") is True:
                    continue
                child_pointer = schema_pointer.rstrip("/") + "/properties/" + name.replace("~", "~0").replace("/", "~1")
                try:
                    resolved_child = _resolve_schema(document, child, child_pointer, {child_pointer}, unsupported, kind=kind)
                except UnsupportedInput as exc:
                    unsupported.append(make_unsupported_item(generator=GENERATOR, item_type="schema_subtree", source_key=exc.source_key or child_pointer, reason_code="unsupported_reference"))
                    continue
                visit(resolved_child, child_pointer, name)
        if schema.get("required"):
            for name in schema["required"]:
                child = (properties or {}).get(name, {}) if isinstance(properties, dict) else {}
                if kind == "openapi-3.0" and context == "request" and isinstance(child, dict) and child.get("readOnly") is True:
                    continue
                if kind == "openapi-3.0" and context == "response" and isinstance(child, dict) and child.get("writeOnly") is True:
                    continue
                child_pointer = schema_pointer.rstrip("/") + "/properties/" + name.replace("~", "~0").replace("/", "~1")
                data_requirements.append(_test_data_requirement(kind, child_pointer, "required", "required", model_key, "boolean", value=True))
        if "items" in schema and isinstance(schema["items"], dict):
            child_pointer = schema_pointer.rstrip("/") + "/items"
            try:
                resolved_item = _resolve_schema(document, schema["items"], child_pointer, {child_pointer}, unsupported, kind=kind)
            except UnsupportedInput as exc:
                unsupported.append(make_unsupported_item(generator=GENERATOR, item_type="schema_subtree", source_key=exc.source_key or child_pointer, reason_code="unsupported_reference"))
            else:
                visit(resolved_item, child_pointer, label + " item")

    visit(root, pointer, pointer or "schema")
    data_requirements.sort(key=lambda row: row["requirement_key"])
    return ep_sets, bva_boundaries, factors, grid_constraints, data_requirements


def _html_skeletons(document: dict, unsupported: list[dict], model_key: str) -> tuple[list[dict], list[dict], list[dict], list[dict], list[dict]]:
    allowed = {"type", "required", "min", "max", "minlength", "maxlength", "step", "value", "pattern", "disabled", "readonly", "multiple"}
    reject_unknown(document, {"type"}, allowed - {"type"})
    control_type = document.get("type")
    if control_type not in {"text", "number", "date", "datetime-local"}:
        raise UnsupportedInput("HTML control typeはruntime-v1未対応です", item_key="unsupported:schema:html-control", reason_code="unsupported_html_control")
    if document.get("disabled") is True or (control_type in {"text", "number", "date", "datetime-local"} and document.get("readonly") is True):
        return [], [], [], [], []
    if control_type == "text" and document.get("pattern") is not None:
        raise UnsupportedInput("HTML patternはruntime-v1で安全に評価できません", item_key="unsupported:schema:html-pattern", reason_code="unsupported_html_constraint")
    ep_sets: list[dict] = []
    bva: list[dict] = []
    factors: list[dict] = []
    grid_constraints: list[dict] = []
    data_requirements: list[dict] = []
    for boolean_key in ("required", "disabled", "readonly", "multiple"):
        if boolean_key in document and not isinstance(document[boolean_key], bool):
            raise InvalidInput(f"HTML {boolean_key}が不正です")
    if document.get("required") is True:
        data_requirements.append(_test_data_requirement("html-control", "#", "required", "required", model_key, "boolean", value=True))
    if control_type == "text" and ("minlength" in document or "maxlength" in document):
        for key in ("minlength", "maxlength"):
            if key in document:
                value = document[key]
                if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                    raise InvalidInput(f"HTML {key}が不正です")
                _digest, boundary_key = _source_digest("html-control", "#", key, "bva-boundary")
                bva.append({"boundary_key": boundary_key, "label": key, "side": "lower" if key == "minlength" else "upper", "threshold": {"type": "integer", "value": value}, "inclusive": True, "step": {"unit": "integer", "amount": 1}, "source_pointer": "#", "keyword": key, "authority_refs": []})
        if "minlength" in document and "maxlength" in document and document["minlength"] > document["maxlength"]:
            raise InvalidInput("HTML minlengthがmaxlengthを超えています")
        if "minlength" in document and "maxlength" in document:
            data_requirements.append(_test_data_requirement("html-control", "#", "minlength-maxlength", "length", model_key, "range", minimum={"type": "integer", "value": document["minlength"]}, maximum={"type": "integer", "value": document["maxlength"]}, minimum_inclusive=True, maximum_inclusive=True))
    if control_type in {"number", "date", "datetime-local"}:
        step_typed: dict[str, Any] | None = None
        valid_min: dict[str, Any] | None = None
        valid_value: dict[str, Any] | None = None
        if control_type == "number":
            def number_value(raw: Any, name: str) -> dict[str, Any]:
                if not isinstance(raw, str):
                    raise InvalidInput(f"HTML number {name}が不正です")
                try:
                    return {"type": "decimal", "value": canonical_decimal(raw)}
                except (InvalidInput, TypeError, ValueError) as exc:
                    raise InvalidInput(f"HTML number {name}が不正です") from exc
            if "min" in document:
                valid_min = number_value(document["min"], "min")
            if "value" in document:
                try:
                    valid_value = number_value(document["value"], "value")
                except InvalidInput:
                    valid_value = None
            step_raw = document.get("step", "1")
            if step_raw != "any":
                step_text = None
                if isinstance(step_raw, str):
                    try:
                        candidate = canonical_decimal(step_raw)
                        if exact_compare(candidate, "0") > 0:
                            step_text = candidate
                    except (InvalidInput, TypeError, ValueError):
                        step_text = None
                # HTML's invalid/zero/negative step token falls back to the
                # default step, rather than disabling the grid constraint.
                step_text = step_text or "1"
                step_typed = {"type": "decimal", "value": step_text}
                base = valid_min or valid_value or {"type": "decimal", "value": "0"}
                _digest, grid_key = _source_digest("html-control", "#", "step", "grid")
                grid_constraints.append({"grid_key": grid_key, "operator": "grid", "base": base, "step": step_typed, "source_pointer": "#", "keyword": "step", "authority_refs": []})
        for key in ("min", "max"):
            if key in document:
                value = document[key]
                if control_type == "number":
                    value = number_value(value, key)
                else:
                    value = {"type": "date" if control_type == "date" else "local_datetime", "value": value}
                    typed_value(value)
                _digest, boundary_key = _source_digest("html-control", "#", key, "bva-boundary")
                if control_type == "number":
                    boundary_step = {"unit": "decimal", "amount": step_typed["value"] if step_typed is not None else "1"}
                else:
                    boundary_step = {"unit": "day" if value["type"] == "date" else "second", "amount": 1}
                bva.append({"boundary_key": boundary_key, "label": key, "side": "lower" if key == "min" else "upper", "threshold": value, "inclusive": True, "step": boundary_step, "source_pointer": "#", "keyword": key, "authority_refs": []})
        if control_type == "number" and "min" in document and "max" in document and exact_compare(valid_min["value"], canonical_decimal(document["max"])) > 0:
            raise InvalidInput("HTML minがmaxを超えています")
        if "min" in document and "max" in document:
            minimum = valid_min if control_type == "number" else {"type": "date" if control_type == "date" else "local_datetime", "value": document["min"]}
            maximum = number_value(document["max"], "max") if control_type == "number" else {"type": "date" if control_type == "date" else "local_datetime", "value": document["max"]}
            if control_type != "number":
                typed_value(minimum)
                typed_value(maximum)
            if minimum["type"] != maximum["type"]:
                minimum = {"type": "decimal", "value": str(minimum["value"])}
                maximum = {"type": "decimal", "value": str(maximum["value"])}
            data_requirements.append(_test_data_requirement("html-control", "#", "min-max", "value", model_key, "range", minimum=minimum, maximum=maximum, minimum_inclusive=True, maximum_inclusive=True))
    return ep_sets, bva, factors, grid_constraints, data_requirements


def generate(input_value: dict, metadata: dict) -> dict:
    if metadata["model_key"] is None or metadata["model_type"] != "schema" or metadata["runtime_unit_key"] != f"model:{metadata['model_key']}":
        raise InvalidInput("schema_casesのruntime metadataが不正です")
    required = {"schema_kind", "document", "schema_pointer", "context", "child_models"}
    reject_unknown(input_value, required)
    kind = input_value["schema_kind"]
    if kind not in SCHEMA_KINDS or not isinstance(input_value["document"], dict):
        raise InvalidInput("schema_kind / documentが不正です")
    if kind == "json-schema-2020-12" and input_value["context"] != "validation":
        raise InvalidInput("JSON Schema contextが不正です")
    if kind == "openapi-3.0" and input_value["context"] not in {"request", "response"}:
        raise InvalidInput("OpenAPI contextが不正です")
    if kind == "html-control" and input_value["context"] != "form-control":
        raise InvalidInput("HTML contextが不正です")
    pointer = input_value["schema_pointer"]
    if not isinstance(pointer, str) or (kind != "html-control" and not (pointer == "#" or pointer.startswith("#/"))):
        raise InvalidInput("schema_pointerが不正です")
    unsupported: list[dict] = []
    try:
        if kind == "html-control":
            ep_sets, bva_boundaries, factors, grid_constraints, test_data_requirements = _html_skeletons(input_value["document"], unsupported, metadata["model_key"])
        else:
            ep_sets, bva_boundaries, factors, grid_constraints, test_data_requirements = _json_skeletons(kind, input_value["document"], pointer, input_value["context"], unsupported, metadata["model_key"])
    except UnsupportedInput as exc:
        reason_code = exc.reason_code if exc.reason_code in SCHEMA_UNSUPPORTED_REASONS else "unsupported_schema_keyword"
        unsupported.append(make_unsupported_item(generator=GENERATOR, item_type="schema_subtree", source_key=exc.source_key, reason_code=reason_code, affected_technique_slug=None))
        ep_sets, bva_boundaries, factors, grid_constraints, test_data_requirements = [], [], [], [], []
    children = ensure_list(input_value["child_models"], "child_models")
    seen_children: set[str] = set()
    requests: list[dict] = []
    derived: list[dict] = []
    issues: list[dict] = []
    for child in children:
        if not isinstance(child, dict) or set(child) != {"child_model_key", "model_type", "derived_from_model_key", "semantic_parameters"}:
            raise InvalidInput("child_models schemaが不正です")
        child_key = ensure_nonempty_string(child["child_model_key"], "child_model_key")
        if child_key in seen_children or child["model_type"] not in CHILD_TYPES or child["derived_from_model_key"] != metadata["model_key"]:
            raise InvalidInput("child model identityが不正です")
        seen_children.add(child_key)
        skeletons = ep_sets if child["model_type"] == "ep" else bva_boundaries if child["model_type"] == "bva" else factors
        if not skeletons:
            issues.append({"issue_type": "selected_technique_not_derivable", "blocking": True, "target_key": child_key, "route_to": "test-analysis" if metadata.get("selection_source") == "analysis" else "test-condition-design" if metadata.get("selection_source") == "condition_design" else "question-analysis", "resume_skill": "test-condition-design", "authority_refs": []})
            continue
        parameters = child["semantic_parameters"]
        if child["model_type"] == "ep":
            if parameters is not None:
                raise InvalidInput("EP semantic_parametersはnullである必要があります")
            derived.append({"child_model_key": child_key, "model_type": "ep", "input": {"sets": [{key: value for key, value in item.items() if key in {"set_key", "label", "partitions"}} for item in ep_sets]}})
        elif child["model_type"] == "bva":
            keys = {item["boundary_key"] for item in bva_boundaries}
            if parameters is None:
                requests.extend({"child_model_key": child_key, "model_type": "bva", "source_key": item["boundary_key"], "required_fields": ["mode", "coverage_selection_reason"]} for item in bva_boundaries)
            else:
                if not isinstance(parameters, dict) or set(parameters) != {"boundaries"}:
                    raise InvalidInput("BVA semantic_parametersが不正です")
                rows = ensure_list(parameters["boundaries"], "semantic_parameters.boundaries")
                if len(rows) != len(keys) or {row.get("boundary_key") for row in rows if isinstance(row, dict)} != keys:
                    raise InvalidInput("BVA boundary parameterが不足または重複しています")
                prepared = []
                for row in rows:
                    if not isinstance(row, dict) or set(row) != {"boundary_key", "mode", "coverage_selection_reason"} or row["mode"] not in {"2-value", "3-value"} or not isinstance(row["coverage_selection_reason"], str) or (row["mode"] == "3-value" and not row["coverage_selection_reason"]):
                        raise InvalidInput("BVA boundary parameterが不正です")
                    skeleton = next(item for item in bva_boundaries if item["boundary_key"] == row["boundary_key"])
                    prepared.append({**skeleton, "mode": row["mode"], "coverage_selection_reason": row["coverage_selection_reason"]})
                derived.append({"child_model_key": child_key, "model_type": "bva", "input": {"boundaries": prepared}})
        else:
            if parameters is None:
                requests.append({"child_model_key": child_key, "model_type": "comb", "source_key": "factors", "required_fields": ["mode", "strength", "global_strength", "subsets", "base_assignment", "coverage_selection_reason"]})
            else:
                if not isinstance(parameters, dict) or "mode" not in parameters or parameters["mode"] not in {"exhaustive", "base-choice", "t-wise", "mixed-strength"}:
                    raise InvalidInput("combinatorial semantic_parametersが不正です")
                derived.append({"child_model_key": child_key, "model_type": "comb", "input": {**parameters, "factors": [{key: value for key, value in item.items() if key in {"factor_key", "label", "values", "authority_refs"}} for item in factors], "constraints": []}})
    requests.sort(key=lambda row: (row["child_model_key"], row["source_key"]))
    schema_digest = _source_digest(kind, pointer, "document", "schema")[0].split(":", 1)[1]
    schema_target = {
        "target_key": "schema:h" + schema_digest,
        "source_pointer": pointer,
        "materializable": False,
        "execution": None,
        "authority_refs": [],
    }
    schema_targets = post_process_targets(metadata["model_key"], [schema_target])
    document_metadata = {}
    if kind == "json-schema-2020-12":
        for key in ("$schema", "$id"):
            if key in input_value["document"]:
                if not isinstance(input_value["document"][key], str) or not input_value["document"][key]:
                    raise InvalidInput(f"schema document metadata {key}が不正です")
                document_metadata[key] = input_value["document"][key]
    payload = {"schema_kind": kind, "schema_pointer": pointer, "document_metadata": document_metadata, "schema_targets": schema_targets, "targets": schema_targets, "ep_skeletons": canonicalize(ep_sets), "bva_skeletons": canonicalize(bva_boundaries), "comb_skeletons": canonicalize(factors), "grid_constraints": canonicalize(grid_constraints), "semantic_parameter_requests": requests, "derived_child_inputs": derived, "derived": {"test_data_requirements": canonicalize(test_data_requirements)}, "unsupported_items": canonicalize(unsupported)}
    status = "unresolved" if requests or issues else "ready"
    support = "partial" if unsupported else "supported"
    return {"runtime_status": "ok", "support_status": support, "result_status": status, "runtime_required": True, "deterministic_generated": True, "payload": payload, "issues": issues}


if __name__ == "__main__":
    raise SystemExit(run_cli(generate, skill=SKILL, generator=GENERATOR, generator_contract_version=GENERATOR_CONTRACT_VERSION, generator_path=SCRIPT_PATH))
