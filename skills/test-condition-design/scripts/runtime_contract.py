"""Skill-local deterministic runtime contract helpers.

This module deliberately contains only contract, canonicalization, exact value,
fingerprint, evidence, and dependency helpers.  Technique-specific generators
must remain in their own script and may import this module only.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import re
import sys
from typing import Any, Callable, Iterable


RUNTIME_CONTRACT_VERSION = "runtime-v1"
ENVELOPE_VERSION = "1"
ENTITY_SCHEMA_VERSION = "entity-state-v1"
MAX_NORMAL_INPUT_BYTES = 2 * 1024 * 1024
MAX_AGGREGATE_INPUT_BYTES = 16 * 1024 * 1024
MAX_STDOUT_BYTES = 16 * 1024 * 1024
MAX_DEPTH = 64
MAX_STRING_BYTES = 64 * 1024
MAX_NUMERIC_CHARS = 4096
MAX_EXPLORATION_NODES = 1_000_000
STABLE_COMPONENT_RE = re.compile(r"^[A-Za-z][A-Za-z0-9._-]{0,64}$")
FULL_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
TR_ID_RE = re.compile(r"^TR-(\d{3})$")
TCN_ID_RE = re.compile(r"^TCN-(\d{3})$")
TC_ID_RE = re.compile(r"^TC-(\d{3})$")
CI_ID_RE = re.compile(r"^(TCN-\d{3})-CI(\d{2,})$")

SUPPORTED_STATUSES = {"ok", "invalid_input", "unsupported", "limit_exceeded", "internal_error", "not_run"}
SUPPORTED_RESULT_STATUSES = {"ready", "unresolved", "blocked"}
SUPPORTED_SUPPORT_STATUSES = {"supported", "partial", "unsupported", "unknown"}
MODEL_TYPES = {
    "ep", "bva", "domain", "decision", "comb", "classification", "state", "flow", "crud",
    "cause-effect", "syntax", "schema", "ui", "random", "metamorphic", "error-guessing",
}
MODEL_GENERATORS = {
    "ep": "equivalence_partitions",
    "bva": "bva",
    "domain": "domain_testing",
    "decision": "decision_table",
    "comb": "combinatorial",
    "classification": "classification_tree",
    "state": "state_transition",
    "flow": "flow_paths",
    "crud": "crud_matrix",
    "cause-effect": "cause_effect",
    "syntax": "grammar_cases",
    "schema": "schema_cases",
    "ui": "ui_pattern_candidates",
    "random": "random_testing",
    "metamorphic": "metamorphic",
}
TECHNIQUE_SLUGS = {"ep", "bva", "domain", "decision", "comb", "state", "error-guessing", "scenario", "crud", "syntax", "random", "metamorphic"}


class RuntimeErrorBase(Exception):
    """A structured failure which can be returned in the runtime envelope."""

    def __init__(
        self,
        message: str,
        *,
        issue_type: str = "invalid_input",
        blocking: bool = True,
        target_key: str | None = None,
        route_to: str | None = None,
        resume_skill: str | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.issue_type = issue_type
        self.blocking = blocking
        self.target_key = target_key
        self.route_to = route_to
        self.resume_skill = resume_skill


class InvalidInput(RuntimeErrorBase):
    def __init__(self, message: str, **kwargs: Any) -> None:
        super().__init__(message, issue_type="invalid_input", **kwargs)


class LimitExceeded(RuntimeErrorBase):
    def __init__(self, message: str) -> None:
        super().__init__(message, issue_type="limit_exceeded")


class UnsupportedInput(RuntimeErrorBase):
    def __init__(self, message: str, *, item_type: str | None = None, reason_code: str | None = None, source_key: str | None = None, affected_technique_slug: str | None = None) -> None:
        super().__init__(message, issue_type="unsupported")
        self.item_type = item_type
        self.reason_code = reason_code
        self.source_key = source_key
        self.affected_technique_slug = affected_technique_slug


class UnresolvedInput(RuntimeErrorBase):
    def __init__(self, message: str, *, issue_type: str = "unresolved_input", target_key: str | None = None, route_to: str | None = None, resume_skill: str | None = None) -> None:
        super().__init__(message, issue_type=issue_type, target_key=target_key, route_to=route_to, resume_skill=resume_skill)


class InternalRuntimeError(RuntimeErrorBase):
    def __init__(self, message: str) -> None:
        super().__init__(message, issue_type="internal_error")


class DuplicateKeyError(ValueError):
    pass


@dataclass(frozen=True)
class NumberToken:
    raw: str
    integer: bool


@dataclass(frozen=True)
class ExactNumber:
    """An exact JSON number represented as coefficient * 10**(-scale)."""

    coefficient: int
    scale: int

    def normalized(self) -> "ExactNumber":
        coefficient = self.coefficient
        scale = self.scale
        if coefficient == 0:
            return ExactNumber(0, 0)
        while scale > 0 and coefficient % 10 == 0:
            coefficient //= 10
            scale -= 1
        if scale < 0:
            coefficient *= 10 ** (-scale)
            scale = 0
        return ExactNumber(coefficient, scale)

    def text(self) -> str:
        value = self.normalized()
        sign = "-" if value.coefficient < 0 else ""
        digits = str(abs(value.coefficient))
        if value.scale == 0:
            return sign + digits
        if len(digits) <= value.scale:
            digits = "0" * (value.scale - len(digits) + 1) + digits
        point = len(digits) - value.scale
        return sign + digits[:point] + "." + digits[point:]


def _reject_constant(value: str) -> Any:
    raise InvalidInput(f"非有限数は許可されません: {value}")


def _object_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateKeyError(f"duplicate object key: {key}")
        result[key] = value
    return result


def _scan_json_limits(text: str, *, max_depth: int = MAX_DEPTH) -> None:
    depth = 0
    in_string = False
    escaped = False
    string_bytes = 0
    for char in text:
        if in_string:
            string_bytes += len(char.encode("utf-8", "surrogatepass"))
            if string_bytes > MAX_STRING_BYTES:
                raise LimitExceeded("1文字列の上限を超えました")
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
            string_bytes = 0
        elif char in "[{":
            depth += 1
            if depth > max_depth:
                raise LimitExceeded("JSON nesting depthの上限を超えました")
        elif char in "]}":
            depth -= 1
            if depth < 0:
                raise InvalidInput("不正なJSON nesting")
    if in_string:
        raise InvalidInput("閉じていないJSON string")
    if depth != 0:
        raise InvalidInput("JSON containerが閉じていません")


def _reject_surrogates(value: Any) -> None:
    if isinstance(value, str):
        for char in value:
            code = ord(char)
            if 0xD800 <= code <= 0xDFFF:
                raise InvalidInput("unpaired surrogate code pointは許可されません")
    elif isinstance(value, dict):
        for key, child in value.items():
            _reject_surrogates(key)
            _reject_surrogates(child)
    elif isinstance(value, list):
        for child in value:
            _reject_surrogates(child)


_NUMBER_RE = re.compile(r"^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?$")


def _number_from_token(token: NumberToken) -> int | ExactNumber:
    raw = token.raw
    if len(raw) > MAX_NUMERIC_CHARS or not _NUMBER_RE.fullmatch(raw):
        raise LimitExceeded("JSON number tokenの上限または形式に違反しました")
    sign = -1 if raw.startswith("-") else 1
    body = raw[1:] if raw.startswith("-") else raw
    exponent = 0
    if "e" in body.lower():
        mantissa, exponent_text = re.split("[eE]", body, maxsplit=1)
        exponent = int(exponent_text)
    else:
        mantissa = body
    if "." in mantissa:
        integer, fraction = mantissa.split(".", 1)
    else:
        integer, fraction = mantissa, ""
    digits = (integer + fraction).lstrip("0") or "0"
    coefficient = sign * int(digits)
    scale = len(fraction) - exponent
    if scale < 0:
        expanded_chars = len(digits) + (-scale)
    else:
        expanded_chars = max(len(digits), scale + 1) + (1 if scale else 0)
    if expanded_chars > MAX_NUMERIC_CHARS:
        raise LimitExceeded("JSON numberを展開したcanonical桁数が上限を超えました")
    exact = ExactNumber(coefficient, scale).normalized()
    if exact.scale == 0:
        return exact.coefficient
    return exact


def _normalize_numbers(value: Any) -> Any:
    if isinstance(value, NumberToken):
        return _number_from_token(value)
    if isinstance(value, dict):
        return {key: _normalize_numbers(child) for key, child in value.items()}
    if isinstance(value, list):
        return [_normalize_numbers(child) for child in value]
    return value


def strict_loads(raw: bytes | str, *, aggregate: bool = False) -> Any:
    raw_bytes = raw.encode("utf-8") if isinstance(raw, str) else raw
    limit = MAX_AGGREGATE_INPUT_BYTES if aggregate else MAX_NORMAL_INPUT_BYTES
    if len(raw_bytes) > limit:
        raise LimitExceeded("runtime stdinのbyte上限を超えました")
    try:
        text = raw_bytes.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise InvalidInput("stdinはUTF-8である必要があります") from exc
    _scan_json_limits(text)
    try:
        value = json.loads(
            text,
            object_pairs_hook=_object_pairs,
            parse_int=lambda token: NumberToken(token, True),
            parse_float=lambda token: NumberToken(token, False),
            parse_constant=_reject_constant,
        )
    except DuplicateKeyError as exc:
        raise InvalidInput(str(exc)) from exc
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        raise InvalidInput(f"strict JSON decodeに失敗しました: {exc}") from exc
    _reject_surrogates(value)
    return _normalize_numbers(value)


def _json_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def canonical_json_text(value: Any) -> str:
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, str):
        return _json_string(value)
    if isinstance(value, int) and not isinstance(value, bool):
        if len(str(abs(value))) > MAX_NUMERIC_CHARS:
            raise LimitExceeded("canonical integerの上限を超えました")
        return str(value)
    if isinstance(value, ExactNumber):
        text = value.text()
        if len(text) > MAX_NUMERIC_CHARS:
            raise LimitExceeded("canonical decimalの上限を超えました")
        return text
    if isinstance(value, float):
        if not math.isfinite(value):
            raise InvalidInput("非有限floatは許可されません")
        raise InvalidInput("binary floatはruntime canonical valueへ使用できません")
    if isinstance(value, list):
        return "[" + ",".join(canonical_json_text(child) for child in value) + "]"
    if isinstance(value, dict):
        parts = []
        for key in sorted(value):
            if not isinstance(key, str):
                raise InvalidInput("JSON object keyはstringである必要があります")
            parts.append(_json_string(key) + ":" + canonical_json_text(value[key]))
        return "{" + ",".join(parts) + "}"
    raise InvalidInput(f"canonical JSONで未対応の型です: {type(value).__name__}")


def canonical_json_bytes(value: Any) -> bytes:
    return canonical_json_text(value).encode("utf-8")


def _sort_record_array(key: str, values: list[Any]) -> list[Any]:
    if key in {"authority_refs", "risk_refs"} and all(isinstance(value, str) for value in values):
        # Keep duplicate semantic references visible to the owning schema
        # validator; canonicalization orders these sets but must not hide input errors.
        return sorted(values)
    if key in {"authority_refs", "reference_refs", "risk_refs", "tr_refs", "ci_refs", "source_refs", "related_authority_refs", "selected_techniques", "changed_node_keys", "initial_states", "initial_node_keys"}:
        unique: dict[str, Any] = {}
        for value in values:
            unique[canonical_json_text(value)] = value
        return [unique[item] for item in sorted(unique)]
    sort_fields = {
        "upstream_entities": ("skill", "entity_type", "entity_ref"),
        "upstream_runtime_units": ("skill", "runtime_unit_key"),
        "previous_tr_ids": ("tr_id",),
        "previous_tcn_ids": ("tcn_id",),
        "previous_tc_ids": ("tc_id",),
        "previous_model_keys": ("model_key",),
        "previous_ci_ids": ("ci_id",),
        "target_annotations": ("target_ref",),
        "target_dispositions": ("target_ref",),
        "merge_groups": ("merge_group_key",),
        "source_target_versions": ("target_ref",),
        "sets": ("set_key",),
        "partitions": ("partition_key",),
        "test_requirements": ("tr_id",),
        "technique_selections": ("selection_key",),
        "test_conditions": ("draft_key",),
        "models": ("parent_tcn_draft_key", "model_type", "draft_key"),
        "upstream_entity_dependencies": ("skill", "entity_type", "entity_ref"),
        "runtime_dependencies": ("skill", "runtime_unit_key"),
    }
    fields = sort_fields.get(key)
    if fields and all(isinstance(value, dict) for value in values):
        return sorted(values, key=lambda value: tuple(str(value.get(field, "")) for field in fields))
    return values


def canonicalize(value: Any, *, parent_key: str | None = None) -> Any:
    if isinstance(value, dict):
        normalized = {key: canonicalize(child, parent_key=key) for key, child in value.items()}
        return {key: normalized[key] for key in sorted(normalized)}
    if isinstance(value, list):
        normalized = [canonicalize(child, parent_key=parent_key) for child in value]
        return _sort_record_array(parent_key or "", normalized)
    if isinstance(value, ExactNumber):
        return value.normalized()
    if isinstance(value, (str, int, bool)) or value is None:
        return value
    raise InvalidInput(f"canonicalizationで未対応の値です: {type(value).__name__}")


def sha256_digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_json_bytes(canonicalize(value))).hexdigest()


def stable_component(value: Any) -> str:
    if isinstance(value, str) and STABLE_COMPONENT_RE.fullmatch(value) and ":" not in value:
        return value
    return "h" + hashlib.sha256(canonical_json_bytes(canonicalize(value))).hexdigest()


def implementation_fingerprint(path: str | Path) -> str:
    data = Path(path).read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return "sha256:" + hashlib.sha256(data).hexdigest()


def static_data_fingerprint(path: str | Path) -> str:
    value = strict_loads(Path(path).read_bytes())
    return sha256_digest(value)


def canonical_decimal(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?", value):
        raise InvalidInput(f"decimal文字列が不正です: {value!r}")
    sign = "-" if value.startswith("-") else ""
    body = value[1:] if sign else value
    integer, _, fraction = body.partition(".")
    fraction = fraction.rstrip("0")
    integer = integer.lstrip("0") or "0"
    if not fraction:
        result = integer
    else:
        result = integer + "." + fraction
    if result == "0":
        sign = ""
    result = sign + result
    if len(result) > MAX_NUMERIC_CHARS:
        raise LimitExceeded("decimal文字列の上限を超えました")
    return result


def exact_from_decimal(value: str) -> ExactNumber:
    text = canonical_decimal(value)
    sign = -1 if text.startswith("-") else 1
    body = text[1:] if sign < 0 else text
    integer, _, fraction = body.partition(".")
    return ExactNumber(sign * int(integer + fraction), len(fraction)).normalized()


def exact_to_decimal(value: ExactNumber | int | str) -> str:
    if isinstance(value, str):
        return canonical_decimal(value)
    if isinstance(value, int):
        return str(value)
    return canonical_decimal(value.text())


def exact_add(left: str, right: str) -> str:
    a = exact_from_decimal(left)
    b = exact_from_decimal(right)
    scale = max(a.scale, b.scale)
    coefficient = a.coefficient * 10 ** (scale - a.scale) + b.coefficient * 10 ** (scale - b.scale)
    return exact_to_decimal(ExactNumber(coefficient, scale))


def exact_multiply(left: str, right: str) -> str:
    a = exact_from_decimal(left)
    b = exact_from_decimal(right)
    return exact_to_decimal(ExactNumber(a.coefficient * b.coefficient, a.scale + b.scale))


def exact_compare(left: str, right: str) -> int:
    a = exact_from_decimal(left)
    b = exact_from_decimal(right)
    scale = max(a.scale, b.scale)
    av = a.coefficient * 10 ** (scale - a.scale)
    bv = b.coefficient * 10 ** (scale - b.scale)
    return (av > bv) - (av < bv)


def typed_value(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != {"type", "value"}:
        raise InvalidInput("typed valueはtype/valueだけを持つobjectである必要があります")
    kind = value["type"]
    raw = value["value"]
    allowed = {"integer", "boolean", "string", "enum", "decimal", "null", "date", "local_datetime", "fixed_offset_datetime"}
    if kind not in allowed:
        raise InvalidInput(f"typed value typeが不正です: {kind}")
    if kind == "integer" and (isinstance(raw, bool) or not isinstance(raw, int)):
        raise InvalidInput("integer typed valueが不正です")
    if kind == "boolean" and not isinstance(raw, bool):
        raise InvalidInput("boolean typed valueが不正です")
    if kind in {"string", "enum"} and not isinstance(raw, str):
        raise InvalidInput("string / enum typed valueが不正です")
    if kind == "decimal":
        if not isinstance(raw, str):
            raise InvalidInput("decimal typed valueはcanonical decimal stringである必要があります")
        try:
            raw = canonical_decimal(raw)
        except (TypeError, ValueError) as exc:
            raise InvalidInput("decimal typed valueが不正です") from exc
    if kind == "null" and raw is not None:
        raise InvalidInput("null typed valueはvalue=nullである必要があります")
    if kind == "date":
        if not isinstance(raw, str):
            raise InvalidInput("date typed valueが不正です")
        try:
            date.fromisoformat(raw)
        except (TypeError, ValueError) as exc:
            raise InvalidInput("date typed valueが不正です") from exc
    if kind == "local_datetime":
        if not isinstance(raw, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", raw):
            raise InvalidInput("local_datetime typed valueが不正です")
        try:
            datetime.fromisoformat(raw)
        except ValueError as exc:
            raise InvalidInput("local_datetime typed valueが不正です") from exc
    if kind == "fixed_offset_datetime":
        if not isinstance(raw, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}", raw):
            raise InvalidInput("fixed_offset_datetime typed valueが不正です")
        try:
            datetime.fromisoformat(raw)
        except ValueError as exc:
            raise InvalidInput("fixed_offset_datetime typed valueが不正です") from exc
    return {"type": kind, "value": raw}


def version_components(value: Any, name: str = "version") -> tuple[int, ...]:
    if not isinstance(value, str) or not value or any(not part.isdigit() or (len(part) > 1 and part.startswith("0")) for part in value.split(".")):
        raise InvalidInput(f"{name}のversion形式が不正です")
    return tuple(int(part) for part in value.split("."))


def compare_versions(left: Any, right: Any) -> int:
    left_parts = version_components(left, "minimum")
    right_parts = version_components(right, "maximum")
    width = max(len(left_parts), len(right_parts))
    left_padded = left_parts + (0,) * (width - len(left_parts))
    right_padded = right_parts + (0,) * (width - len(right_parts))
    return (left_padded > right_padded) - (left_padded < right_padded)


def typed_value_compare(left: dict[str, Any], right: dict[str, Any]) -> int:
    """Compare same-type range values without changing their canonical form."""
    left_value = typed_value(left)
    right_value = typed_value(right)
    kind = left_value["type"]
    if kind != right_value["type"]:
        raise UnsupportedInput("異なるtyped valueのrange比較は未対応です", reason_code="unsupported_intersection")
    if kind == "integer":
        return (left_value["value"] > right_value["value"]) - (left_value["value"] < right_value["value"])
    if kind == "decimal":
        return exact_compare(left_value["value"], right_value["value"])
    if kind == "date":
        a, b = date.fromisoformat(left_value["value"]), date.fromisoformat(right_value["value"])
    elif kind == "local_datetime":
        a, b = datetime.fromisoformat(left_value["value"]), datetime.fromisoformat(right_value["value"])
    elif kind == "fixed_offset_datetime":
        a, b = datetime.fromisoformat(left_value["value"]), datetime.fromisoformat(right_value["value"])
    else:
        raise UnsupportedInput("このtyped valueのrange比較は未対応です", reason_code="unsupported_intersection")
    return (a > b) - (a < b)


def constraint_intersection_compatible(constraints: Iterable[dict[str, Any]]) -> bool:
    """Return whether normalized constraints on one dimension have a common value.

    This is the shared runtime-v1 intersection contract used by environment,
    test-data, merge, and case-level requirement validation.
    """
    rows = list(constraints)
    if not rows:
        return True
    operators = [row.get("operator") for row in rows]
    allowed = {"eq", "enum", "range", "version_range", "boolean"}
    if any(operator not in allowed for operator in operators):
        raise UnsupportedInput("constraint operatorのintersectionは未対応です", reason_code="unsupported_intersection")

    if "version_range" in operators:
        if any(operator != "version_range" for operator in operators):
            raise UnsupportedInput("version_rangeと他operatorのintersectionは未対応です", reason_code="unsupported_intersection")
        lower: tuple[int, ...] | None = None
        lower_inclusive = True
        upper: tuple[int, ...] | None = None
        upper_inclusive = True
        for row in rows:
            minimum = version_components(row.get("minimum"), "minimum")
            maximum = version_components(row.get("maximum"), "maximum")
            minimum_text = row["minimum"]
            maximum_text = row["maximum"]
            if compare_versions(minimum_text, maximum_text) > 0:
                raise InvalidInput("version_rangeのminimumがmaximumを超えています")
            if lower is None or compare_versions(minimum_text, ".".join(map(str, lower))) > 0:
                lower, lower_inclusive = minimum, row["minimum_inclusive"]
            elif compare_versions(minimum_text, ".".join(map(str, lower))) == 0:
                lower_inclusive = lower_inclusive and row["minimum_inclusive"]
            if upper is None or compare_versions(maximum_text, ".".join(map(str, upper))) < 0:
                upper, upper_inclusive = maximum, row["maximum_inclusive"]
            elif compare_versions(maximum_text, ".".join(map(str, upper))) == 0:
                upper_inclusive = upper_inclusive and row["maximum_inclusive"]
        assert lower is not None and upper is not None
        relation = compare_versions(".".join(map(str, lower)), ".".join(map(str, upper)))
        return relation < 0 or (relation == 0 and lower_inclusive and upper_inclusive)

    has_boolean = "boolean" in operators
    if has_boolean and any(operator not in {"boolean", "eq"} for operator in operators):
        raise UnsupportedInput("booleanとこのoperatorのintersectionは未対応です", reason_code="unsupported_intersection")

    finite_sets: list[set[str]] = []
    ranges: list[dict[str, Any]] = []
    for row in rows:
        operator = row["operator"]
        if operator == "eq":
            finite_sets.append({canonical_json_text(typed_value(row["value"]))})
        elif operator == "enum":
            finite_sets.append({canonical_json_text(typed_value(value)) for value in row["values"]})
        elif operator == "boolean":
            finite_sets.append({canonical_json_text({"type": "boolean", "value": row["value"]})})
        elif operator == "range":
            minimum = typed_value(row["minimum"])
            maximum = typed_value(row["maximum"])
            if minimum["type"] != maximum["type"]:
                raise UnsupportedInput("異なるtyped valueのrange比較は未対応です", reason_code="unsupported_intersection")
            if typed_value_compare(minimum, maximum) > 0:
                raise InvalidInput("constraint rangeのminimumがmaximumを超えています")
            ranges.append({**row, "minimum": minimum, "maximum": maximum})

    if finite_sets:
        candidates = set.intersection(*finite_sets)
        if not ranges:
            return bool(candidates)
        for encoded in sorted(candidates):
            value = strict_loads(encoded)
            matches = True
            for row in ranges:
                if value["type"] != row["minimum"]["type"]:
                    matches = False
                    break
                low = typed_value_compare(value, row["minimum"])
                high = typed_value_compare(value, row["maximum"])
                if not ((low > 0 or (low == 0 and row["minimum_inclusive"])) and (high < 0 or (high == 0 and row["maximum_inclusive"]))):
                    matches = False
                    break
            if matches:
                return True
        return False

    if not ranges:
        return True
    range_type = ranges[0]["minimum"]["type"]
    if any(row["minimum"]["type"] != range_type for row in ranges):
        raise UnsupportedInput("異なるtyped rangeのintersectionは未対応です", reason_code="unsupported_intersection")
    lower = ranges[0]["minimum"]
    lower_inclusive = ranges[0]["minimum_inclusive"]
    upper = ranges[0]["maximum"]
    upper_inclusive = ranges[0]["maximum_inclusive"]
    for row in ranges[1:]:
        low_relation = typed_value_compare(row["minimum"], lower)
        if low_relation > 0:
            lower, lower_inclusive = row["minimum"], row["minimum_inclusive"]
        elif low_relation == 0:
            lower_inclusive = lower_inclusive and row["minimum_inclusive"]
        high_relation = typed_value_compare(row["maximum"], upper)
        if high_relation < 0:
            upper, upper_inclusive = row["maximum"], row["maximum_inclusive"]
        elif high_relation == 0:
            upper_inclusive = upper_inclusive and row["maximum_inclusive"]
    relation = typed_value_compare(lower, upper)
    return relation < 0 or (relation == 0 and lower_inclusive and upper_inclusive)


def typed_sort_key(value: dict[str, Any]) -> str:
    return canonical_json_text(typed_value(value))


def ensure_object(value: Any, name: str = "input") -> dict[str, Any]:
    if not isinstance(value, dict):
        raise InvalidInput(f"{name}はJSON objectである必要があります")
    return value


def ensure_list(value: Any, name: str) -> list[Any]:
    if not isinstance(value, list):
        raise InvalidInput(f"{name}はarrayである必要があります")
    return value


def reject_unknown(value: dict[str, Any], required: Iterable[str], optional: Iterable[str] = ()) -> None:
    required_set = set(required)
    optional_set = set(optional)
    missing = sorted(required_set - set(value))
    unknown = sorted(set(value) - required_set - optional_set)
    if missing:
        raise InvalidInput(f"必須fieldがありません: {', '.join(missing)}")
    if unknown:
        raise InvalidInput(f"未知fieldです: {', '.join(unknown)}")


def ensure_nonempty_string(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise InvalidInput(f"{name}は非空stringである必要があります")
    return value


def ensure_key(value: Any, name: str) -> str:
    value = ensure_nonempty_string(value, name)
    if not STABLE_COMPONENT_RE.fullmatch(value) or ":" in value:
        raise InvalidInput(f"{name}はstable component key形式である必要があります")
    return value


def ensure_bool(value: Any, name: str) -> bool:
    if not isinstance(value, bool):
        raise InvalidInput(f"{name}はbooleanである必要があります")
    return value


def ensure_int(value: Any, name: str, *, minimum: int | None = None, maximum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise InvalidInput(f"{name}はintegerである必要があります")
    if minimum is not None and value < minimum:
        raise InvalidInput(f"{name}が小さすぎます")
    if maximum is not None and value > maximum:
        raise InvalidInput(f"{name}が大きすぎます")
    return value


def parse_stable_id(value: Any, pattern: re.Pattern[str], name: str) -> tuple[str, int]:
    if not isinstance(value, str):
        raise InvalidInput(f"{name}はstringである必要があります")
    match = pattern.fullmatch(value)
    if match is None:
        raise InvalidInput(f"{name}の形式が不正です")
    return value, int(match.group(1) if pattern is not CI_ID_RE else match.group(2))


def seed_legacy_ids(values: Any, pattern: re.Pattern[str], name: str) -> list[dict[str, Any]]:
    rows = ensure_list(values, name)
    result = []
    seen: set[str] = set()
    for value in rows:
        ref, _number = parse_stable_id(value, pattern, name)
        if ref in seen:
            raise InvalidInput(f"{name}が重複しています")
        seen.add(ref)
        result.append({"id": ref, "status": "active"})
    return sorted(result, key=lambda row: row["id"])


def allocate_stable_id(prefix: str, previous_ids: Iterable[str], *, minimum: int = 1, maximum: int | None = 999, width: int = 3) -> str:
    previous = set(previous_ids)
    numbers: list[int] = []
    pattern = re.compile(r"^" + re.escape(prefix) + r"-(\d+)$")
    for value in previous:
        match = pattern.fullmatch(value)
        if match:
            numbers.append(int(match.group(1)))
    candidate_number = max(numbers, default=minimum - 1) + 1
    if maximum is not None and candidate_number > maximum:
        raise InvalidInput("id_space_exhausted")
    return f"{prefix}-{candidate_number:0{width}d}"


def unsupported_item_key(generator: str, item_type: str, source_key: str | None, affected_technique_slug: str | None) -> str:
    identity = {
        "generator": generator,
        "item_type": item_type,
        "source_key": source_key,
        "affected_technique_slug": affected_technique_slug,
    }
    digest = hashlib.sha256(canonical_json_bytes(canonicalize(identity))).hexdigest()
    return f"unsupported:{generator}:h{digest}"


def make_unsupported_item(*, generator: str, item_type: str, source_key: str | None, reason_code: str, affected_technique_slug: str | None = None, authority_refs: list[str] | None = None) -> dict[str, Any]:
    if not isinstance(reason_code, str) or not reason_code:
        raise InvalidInput("unsupported reason_codeが不正です")
    return {
        "item_key": unsupported_item_key(generator, item_type, source_key, affected_technique_slug),
        "item_type": item_type,
        "source_key": source_key,
        "reason_code": reason_code,
        "affected_technique_slug": affected_technique_slug,
        "authority_refs": sorted(set(authority_refs or [])),
    }


def validate_target_disposition(row: Any, *, current_targets: dict[str, dict[str, Any]], generation_by_ref: dict[str, str]) -> dict[str, Any]:
    if not isinstance(row, dict):
        raise InvalidInput("target disposition rowはobjectである必要があります")
    required = {"target_ref", "target_content_fingerprint", "generation_fingerprint", "handling", "reason", "authority_refs", "covered_by_target_version"}
    if set(row) != required:
        raise InvalidInput("target disposition schemaが不正です")
    ref = row["target_ref"]
    if ref not in current_targets or row["target_content_fingerprint"] != current_targets[ref].get("target_content_fingerprint") or row["generation_fingerprint"] != generation_by_ref.get(ref):
        raise InvalidInput("target dispositionがcurrent target versionと不一致です")
    if row["handling"] not in {"対象外", "別テストレベル", "残存リスク", "ブロック中", "重複"}:
        raise InvalidInput("target disposition handlingが不正です")
    ensure_nonempty_string(row["reason"], "target disposition reason")
    if not isinstance(row["authority_refs"], list) or not all(isinstance(value, str) for value in row["authority_refs"]):
        raise InvalidInput("target disposition authority_refsが不正です")
    covered = row["covered_by_target_version"]
    if row["handling"] == "重複":
        if not isinstance(covered, dict) or set(covered) != {"target_ref", "target_content_fingerprint", "generation_fingerprint", "execution_fingerprint"} or covered["target_ref"] == ref:
            raise InvalidInput("重複 dispositionのcovered_by_target_versionが不正です")
    elif covered is not None:
        raise InvalidInput("重複以外のcovered_by_target_versionはnullである必要があります")
    return canonicalize(row)


def dependency_graph_status(rows: list[dict[str, Any]], *, identity_fields: tuple[str, ...], dependency_field: str) -> list[dict[str, Any]]:
    identities: dict[tuple[Any, ...], dict[str, Any]] = {}
    graph: dict[tuple[Any, ...], set[tuple[Any, ...]]] = {}
    for row in rows:
        identity = tuple(row.get(field) for field in identity_fields)
        if any(value is None for value in identity) or identity in identities:
            raise InvalidInput("dependency identityが重複または不正です")
        identities[identity] = row
    graph = {identity: set() for identity in identities}
    for identity, row in identities.items():
        dependencies = row.get(dependency_field, [])
        if not isinstance(dependencies, list):
            raise InvalidInput("dependency listが不正です")
        for dependency in dependencies:
            if not isinstance(dependency, dict):
                raise InvalidInput("dependency rowが不正です")
            target = tuple(dependency.get(field) for field in identity_fields)
            if any(value is None for value in target):
                raise InvalidInput("dependency identityが不正です")
            if target not in identities:
                raise UnresolvedInput("missing dependency")
            graph[identity].add(target)
    visiting: set[tuple[Any, ...]] = set()
    visited: set[tuple[Any, ...]] = set()

    def visit(node: tuple[Any, ...]) -> None:
        if node in visiting:
            raise InvalidInput("dependency cycle")
        if node in visited:
            return
        visiting.add(node)
        for dependency in graph.get(node, set()):
            visit(dependency)
        visiting.remove(node)
        visited.add(node)

    for identity in sorted(graph, key=str):
        visit(identity)
    return rows


def compare_entity_dependencies(entity: dict[str, Any], current_entities: dict[tuple[str, str, str], dict[str, Any]]) -> str:
    validate_machine_entity(entity)
    for dependency in entity["upstream_entity_dependencies"]:
        if not isinstance(dependency, dict) or set(dependency) != {"skill", "entity_type", "entity_ref", "content_fingerprint"}:
            raise InvalidInput("upstream_entity_dependencies schemaが不正です")
        key = entity_identity(dependency["skill"], dependency["entity_type"], dependency["entity_ref"])
        current = current_entities.get(key)
        if current is None or current.get("content_fingerprint") != dependency["content_fingerprint"]:
            return "stale"
    return "current"


def compare_runtime_dependencies(runtime_unit: dict[str, Any], current_runtime_units: dict[tuple[str, str], dict[str, Any]]) -> str:
    dependencies = runtime_unit.get("upstream_runtime_units", [])
    if not isinstance(dependencies, list):
        raise InvalidInput("upstream_runtime_units schemaが不正です")
    for dependency in dependencies:
        if not isinstance(dependency, dict) or set(dependency) != {"skill", "runtime_unit_key", "generation_fingerprint"}:
            raise InvalidInput("runtime dependency schemaが不正です")
        key = (dependency["skill"], dependency["runtime_unit_key"])
        current = current_runtime_units.get(key)
        if current is None or current.get("generation_fingerprint") != dependency["generation_fingerprint"]:
            return "stale"
    return "current"


def evaluate_entity_freshness(
    entities: list[dict[str, Any]],
    current_runtime_units: dict[tuple[str, str], dict[str, Any]],
) -> list[dict[str, Any]]:
    """Evaluate upstream Entity and runtime dependencies using one shared rule."""
    validated = validate_entity_collection(entities)
    entity_map = {entity_identity(row["skill"], row["entity_type"], row["entity_ref"]): row for row in validated}
    state: dict[tuple[str, str, str], tuple[str, list[dict[str, Any]]]] = {}
    visiting: set[tuple[str, str, str]] = set()

    def visit(entity: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
        key = entity_identity(entity["skill"], entity["entity_type"], entity["entity_ref"])
        if key in state:
            return state[key]
        if key in visiting:
            raise InvalidInput("Machine Entity dependency cycle")
        visiting.add(key)
        reasons: list[dict[str, Any]] = []
        for dependency in entity["upstream_entity_dependencies"]:
            dep_key = entity_identity(dependency["skill"], dependency["entity_type"], dependency["entity_ref"])
            current = entity_map.get(dep_key)
            if current is None:
                reasons.append({"reason_code": "missing_upstream_entity", "dependency": list(dep_key)})
            elif current["content_fingerprint"] != dependency["content_fingerprint"]:
                reasons.append({"reason_code": "upstream_entity_fingerprint_mismatch", "dependency": list(dep_key)})
            else:
                dep_status, _ = visit(current)
                if dep_status == "stale":
                    reasons.append({"reason_code": "upstream_entity_stale", "dependency": list(dep_key)})
        for dependency in entity["runtime_dependencies"]:
            if not isinstance(dependency, dict) or set(dependency) != {"skill", "runtime_unit_key", "generation_fingerprint"}:
                raise InvalidInput("Machine Entity runtime dependency schemaが不正です")
            runtime_unit_key = dependency["runtime_unit_key"]
            scoped = "#entity:" in runtime_unit_key
            base_runtime_unit_key = runtime_unit_key.rsplit("#entity:", 1)[0] if scoped else runtime_unit_key
            dep_key = (dependency["skill"], base_runtime_unit_key if scoped else runtime_unit_key)
            current_runtime = current_runtime_units.get(dep_key)
            if current_runtime is None:
                reasons.append({"reason_code": "missing_runtime_dependency", "dependency": list(dep_key)})
            elif current_runtime.get("freshness_status") == "stale":
                reasons.append({"reason_code": "runtime_dependency_stale", "dependency": list(dep_key)})
            elif scoped and (
                runtime_unit_key != machine_entity_runtime_unit_key(base_runtime_unit_key, entity)
                or dependency["generation_fingerprint"] != machine_entity_runtime_generation(entity, current_runtime)
            ):
                reasons.append({"reason_code": "runtime_generation_mismatch", "dependency": list(dep_key)})
            elif not scoped and current_runtime.get("generation_fingerprint") != dependency["generation_fingerprint"]:
                reasons.append({"reason_code": "runtime_generation_mismatch", "dependency": list(dep_key)})
            elif current_runtime.get("freshness_status") == "stale":
                reasons.append({"reason_code": "runtime_dependency_stale", "dependency": list(dep_key)})
        visiting.remove(key)
        status = "stale" if reasons else "current"
        state[key] = (status, reasons)
        return state[key]

    rows: list[dict[str, Any]] = []
    for entity in validated:
        status, reasons = visit(entity)
        rows.append({
            "skill": entity["skill"], "entity_type": entity["entity_type"], "entity_ref": entity["entity_ref"],
            "model_key": entity.get("model_key"), "freshness_status": status, "stale_reasons": reasons,
        })
    return rows


def validate_runtime_dependency_graph(rows: list[dict[str, Any]]) -> None:
    """Reject duplicate runtime dependencies and cycles in the current graph."""
    identities: dict[tuple[str, str], dict[str, Any]] = {}
    graph: dict[tuple[str, str], set[tuple[str, str]]] = {}
    for row in rows:
        key = (row.get("skill"), row.get("runtime_unit_key"))
        if not all(isinstance(value, str) for value in key) or key in identities:
            raise InvalidInput("runtime dependency graph identityが重複または不正です")
        identities[key] = row
        graph[key] = set()
    for key, row in identities.items():
        dependencies = row.get("upstream_runtime_units", [])
        if not isinstance(dependencies, list):
            raise InvalidInput("runtime dependency graph listが不正です")
        seen: set[tuple[str, str]] = set()
        for dependency in dependencies:
            if not isinstance(dependency, dict) or set(dependency) != {"skill", "runtime_unit_key", "generation_fingerprint"}:
                raise InvalidInput("runtime dependency graph schemaが不正です")
            dependency_key = (dependency["skill"], dependency["runtime_unit_key"])
            if not all(isinstance(value, str) for value in dependency_key) or dependency_key in seen:
                raise InvalidInput("runtime dependency graph dependencyが重複または不正です")
            seen.add(dependency_key)
            if dependency_key in identities:
                graph[key].add(dependency_key)
    visiting: set[tuple[str, str]] = set()
    visited: set[tuple[str, str]] = set()

    def visit(node: tuple[str, str]) -> None:
        if node in visiting:
            raise InvalidInput("runtime dependency graph cycle")
        if node in visited:
            return
        visiting.add(node)
        for dependency in sorted(graph[node]):
            visit(dependency)
        visiting.remove(node)
        visited.add(node)

    for identity in sorted(graph):
        visit(identity)


def evaluate_runtime_unit_freshness(
    runtime_units: list[dict[str, Any]],
    current_runtime_units: list[dict[str, Any]],
    entities: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Apply the same runtime/entity dependency rule to workflow and traceability."""
    entity_map = {
        entity_identity(row["skill"], row["entity_type"], row["entity_ref"]): row
        for row in validate_entity_collection(entities)
    }
    current_runtime = {
        (row["skill"], row["runtime_unit_key"]): row
        for row in current_runtime_units
    }
    validate_runtime_dependency_graph(current_runtime_units)
    entity_status = {
        (row["skill"], row["entity_type"], row["entity_ref"]): row
        for row in evaluate_entity_freshness(entities, current_runtime)
    }
    fresh_rows: list[dict[str, Any]] = []
    issues: list[dict[str, Any]] = []
    for row in runtime_units:
        key = (row.get("skill"), row.get("runtime_unit_key"))
        stale = row.get("freshness_status") == "stale"
        reasons: list[dict[str, Any]] = []
        for dependency in row.get("upstream_entity_fingerprints", []):
            if not isinstance(dependency, dict) or set(dependency) != {"skill", "entity_type", "entity_ref", "content_fingerprint"}:
                raise InvalidInput("runtime upstream_entity_fingerprints schemaが不正です")
            entity_key = entity_identity(dependency["skill"], dependency["entity_type"], dependency["entity_ref"])
            current = entity_map.get(entity_key)
            if current is None:
                stale = True
                reasons.append({"reason_code": "missing_upstream_entity", "dependency": list(entity_key)})
            elif current["content_fingerprint"] != dependency["content_fingerprint"]:
                stale = True
                reasons.append({"reason_code": "upstream_entity_fingerprint_mismatch", "dependency": list(entity_key)})
            elif entity_status.get(entity_key, {}).get("freshness_status") == "stale":
                stale = True
                reasons.append({"reason_code": "upstream_entity_stale", "dependency": list(entity_key)})
        for dependency in row.get("upstream_runtime_units", []):
            if not isinstance(dependency, dict) or set(dependency) != {"skill", "runtime_unit_key", "generation_fingerprint"}:
                raise InvalidInput("runtime upstream_runtime_units schemaが不正です")
            runtime_key = (dependency["skill"], dependency["runtime_unit_key"])
            current = current_runtime.get(runtime_key)
            if current is None:
                stale = True
                reasons.append({"reason_code": "missing_runtime_dependency", "dependency": list(runtime_key)})
            elif current.get("generation_fingerprint") != dependency["generation_fingerprint"]:
                stale = True
                reasons.append({"reason_code": "runtime_generation_mismatch", "dependency": list(runtime_key)})
            elif current.get("freshness_status") == "stale":
                stale = True
                reasons.append({"reason_code": "runtime_dependency_stale", "dependency": list(runtime_key)})
        current = current_runtime.get(key)
        if current is None or current.get("generation_fingerprint") != row.get("generation_fingerprint"):
            stale = True
            reasons.append({"reason_code": "current_runtime_generation_mismatch", "dependency": list(key)})
        elif runtime_result_projection_mismatch(row, current):
            stale = True
            reasons.append({"reason_code": "current_runtime_result_mismatch", "dependency": list(key)})
        updated = dict(row)
        updated["freshness_status"] = "stale" if stale else "current"
        fresh_rows.append(updated)
        for reason in reasons:
            issue_type = (
                "stale_entity_dependency"
                if reason["reason_code"] in {"missing_upstream_entity", "upstream_entity_fingerprint_mismatch", "upstream_entity_stale"}
                else "stale_runtime_dependency"
                if reason["reason_code"] in {"missing_runtime_dependency", "runtime_generation_mismatch", "runtime_dependency_stale"}
                else reason["reason_code"]
            )
            issues.append({
                "issue_type": issue_type,
                "blocking": True,
                "skill": row.get("skill"),
                "runtime_unit_key": row.get("runtime_unit_key"),
                **reason,
            })
    return fresh_rows, issues


_RUNTIME_RESULT_PROJECTION_FIELDS = (
    "skill", "runtime_unit_key", "model_key", "support_status", "runtime_status", "result_status",
    "runtime_required", "deterministic_generated", "generation_fingerprint", "upstream_entity_fingerprints",
    "upstream_runtime_units", "unsupported_items", "runtime_contract_version", "generator_contract_version",
    "runtime_implementation_fingerprint", "generator_implementation_fingerprint", "static_data_versions",
    "model_completion", "target_mappings", "target_dispositions", "result_fingerprint",
)


def runtime_result_projection_mismatch(saved: dict[str, Any], current: dict[str, Any]) -> bool:
    """Compare the stored consumer projection with the projection of the current rerun."""
    return any(
        canonical_json_text(saved.get(field)) != canonical_json_text(current.get(field))
        for field in _RUNTIME_RESULT_PROJECTION_FIELDS
    )


def entity_identity(skill: str, entity_type: str, entity_ref: str) -> tuple[str, str, str]:
    return (skill, entity_type, entity_ref)


def machine_entity_runtime_unit_key(runtime_unit_key: str, entity: dict[str, Any]) -> str:
    """Identify the generator's stable per-entity runtime projection."""
    identity = {
        "skill": entity.get("skill"),
        "entity_type": entity.get("entity_type"),
        "entity_ref": entity.get("entity_ref"),
    }
    return f"{runtime_unit_key}#entity:{sha256_digest(identity)}"


def machine_entity_runtime_generation(entity: dict[str, Any], runtime_unit: dict[str, Any]) -> str:
    """Return the current scoped generation for an entity-producing runtime.

    The aggregate runtime generation changes when any partial scope changes.
    Entity content and its explicit semantic dependencies provide the local
    meaning boundary; this scoped generation tracks that content together
    with the producer implementation and contract versions.
    """
    required = {
        "runtime_contract_version", "generator_contract_version",
        "runtime_implementation_fingerprint", "generator_implementation_fingerprint",
    }
    if not required.issubset(runtime_unit):
        raise InvalidInput("current runtime unit lacks entity generation metadata")
    for field in ("runtime_implementation_fingerprint", "generator_implementation_fingerprint"):
        if not FULL_DIGEST_RE.fullmatch(str(runtime_unit[field])):
            raise InvalidInput("current runtime implementation fingerprint is invalid")
    static_versions = runtime_unit.get("static_data_versions", {})
    if not isinstance(static_versions, dict):
        raise InvalidInput("current runtime static_data_versions is invalid")
    if not isinstance(entity, dict) or not isinstance(entity.get("content"), dict) or entity.get("content_fingerprint") != sha256_digest(entity.get("content")):
        raise InvalidInput("Machine Entity content fingerprint is invalid for scoped generation")
    return sha256_digest({
        "schema": "machine-entity-runtime-generation-v1",
        "identity": {
            "skill": entity["skill"],
            "entity_type": entity["entity_type"],
            "entity_ref": entity["entity_ref"],
        },
        "content_fingerprint": entity["content_fingerprint"],
        "runtime_contract_version": runtime_unit["runtime_contract_version"],
        "generator_contract_version": runtime_unit["generator_contract_version"],
        "runtime_implementation_fingerprint": runtime_unit["runtime_implementation_fingerprint"],
        "generator_implementation_fingerprint": runtime_unit["generator_implementation_fingerprint"],
        "static_data_versions": canonicalize(static_versions),
    })


def machine_entity_runtime_dependency(skill: str, runtime_unit_key: str) -> dict[str, str]:
    """Mark an entity's local producer dependency for run_cli to bind."""
    return {
        "skill": ensure_nonempty_string(skill, "machine entity runtime skill"),
        "runtime_unit_key": ensure_nonempty_string(runtime_unit_key, "machine entity runtime unit"),
        "generation_fingerprint": "__CURRENT_ENTITY__",
    }


ALLOWED_ENTITY_TYPES = {
    "authority", "test_analysis_context", "product_risk", "technique_selection", "change_node", "change_edge",
    "environment_requirement", "test_data_requirement", "tr", "tcn", "model", "ci", "tc", "disposition",
}


def make_machine_entity(
    skill: str,
    entity_type: str,
    entity_ref: str,
    content: dict[str, Any],
    *,
    model_key: str | None = None,
    upstream_entity_dependencies: list[dict[str, Any]] | None = None,
    runtime_dependencies: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if entity_type not in ALLOWED_ENTITY_TYPES:
        raise InvalidInput(f"unknown entity_type: {entity_type}")
    canonical_content = canonicalize(content)
    upstream = canonicalize(upstream_entity_dependencies or [], parent_key="upstream_entity_dependencies")
    runtime = canonicalize(runtime_dependencies or [], parent_key="runtime_dependencies")
    return {
        "schema_version": ENTITY_SCHEMA_VERSION,
        "skill": skill,
        "entity_type": entity_type,
        "entity_ref": entity_ref,
        "model_key": model_key,
        "content": canonical_content,
        "content_fingerprint": sha256_digest(canonical_content),
        "upstream_entity_dependencies": upstream,
        "runtime_dependencies": runtime,
    }


def validate_machine_entity(entity: Any, *, expected_skill: str | None = None) -> dict[str, Any]:
    if not isinstance(entity, dict):
        raise InvalidInput("Machine Entity rowはobjectである必要があります")
    required = {"schema_version", "skill", "entity_type", "entity_ref", "model_key", "content", "content_fingerprint", "upstream_entity_dependencies", "runtime_dependencies"}
    if set(entity) != required:
        raise InvalidInput("Machine Entity schemaが不正です")
    if entity["schema_version"] != ENTITY_SCHEMA_VERSION:
        raise InvalidInput("Machine Entity schema_versionが不正です")
    if expected_skill is not None and entity["skill"] != expected_skill:
        raise InvalidInput("Machine Entity skillが不一致です")
    if not isinstance(entity["skill"], str) or not entity["skill"].strip() or entity["entity_type"] not in ALLOWED_ENTITY_TYPES or not isinstance(entity["entity_ref"], str) or not entity["entity_ref"].strip() or (entity["model_key"] is not None and (not isinstance(entity["model_key"], str) or not entity["model_key"].strip())):
        raise InvalidInput("Machine Entity identityが不正です")
    if not isinstance(entity["content"], dict) or entity["content_fingerprint"] != sha256_digest(entity["content"]):
        raise InvalidInput("Machine Entity content_fingerprintが不一致です")
    if not isinstance(entity["upstream_entity_dependencies"], list) or not isinstance(entity["runtime_dependencies"], list):
        raise InvalidInput("Machine Entity dependencyが不正です")
    identity = entity_identity(entity["skill"], entity["entity_type"], entity["entity_ref"])
    upstream_seen: set[tuple[str, str, str]] = set()
    for dependency in entity["upstream_entity_dependencies"]:
        if not isinstance(dependency, dict) or set(dependency) != {"skill", "entity_type", "entity_ref", "content_fingerprint"}:
            raise InvalidInput("upstream_entity_dependencies schemaが不正です")
        dependency_identity = entity_identity(dependency["skill"], dependency["entity_type"], dependency["entity_ref"])
        if not all(isinstance(value, str) and value.strip() for value in dependency_identity) or dependency_identity == identity or dependency_identity in upstream_seen or not FULL_DIGEST_RE.fullmatch(str(dependency["content_fingerprint"])):
            raise InvalidInput("upstream_entity_dependenciesが重複またはself参照です")
        upstream_seen.add(dependency_identity)
    runtime_seen: set[tuple[str, str]] = set()
    for dependency in entity["runtime_dependencies"]:
        if not isinstance(dependency, dict) or set(dependency) != {"skill", "runtime_unit_key", "generation_fingerprint"}:
            raise InvalidInput("Machine Entity runtime dependency schemaが不正です")
        dependency_identity = (dependency["skill"], dependency["runtime_unit_key"])
        if not all(isinstance(value, str) and value.strip() for value in dependency_identity) or dependency_identity in runtime_seen or not FULL_DIGEST_RE.fullmatch(str(dependency["generation_fingerprint"])):
            raise InvalidInput("Machine Entity runtime dependencyが重複またはself参照です")
        runtime_seen.add(dependency_identity)
    return entity


def validate_entity_collection(entities: Any, *, expected_skill: str | None = None) -> list[dict[str, Any]]:
    rows = ensure_list(entities, "entities")
    result: list[dict[str, Any]] = []
    identities: set[tuple[str, str, str]] = set()
    for row in rows:
        entity = validate_machine_entity(row, expected_skill=expected_skill)
        identity = entity_identity(entity["skill"], entity["entity_type"], entity["entity_ref"])
        if identity in identities:
            raise InvalidInput("Machine Entity identityが重複しています")
        identities.add(identity)
        result.append(entity)
    return sorted(result, key=lambda row: (row["skill"], row["entity_type"], row["entity_ref"]))


def upstream_entity_fingerprints(entities: list[dict[str, Any]]) -> list[dict[str, str]]:
    result = []
    seen: set[tuple[str, str, str]] = set()
    for row in entities:
        validate_machine_entity(row)
        identity = entity_identity(row["skill"], row["entity_type"], row["entity_ref"])
        if identity in seen:
            raise InvalidInput("upstream Entityが重複しています")
        seen.add(identity)
        result.append({"skill": row["skill"], "entity_type": row["entity_type"], "entity_ref": row["entity_ref"], "content_fingerprint": row["content_fingerprint"]})
    return sorted(result, key=lambda row: (row["skill"], row["entity_type"], row["entity_ref"]))


def machine_entity_dependency(entity: dict[str, Any]) -> dict[str, str]:
    """Return the canonical freshness dependency for a current Machine Entity."""
    # Generator-local entities carry this placeholder until run_cli binds the
    # just-computed generation fingerprint. Their canonical content and
    # content_fingerprint are already fixed and can safely supply an entity
    # dependency during the same invocation.
    candidate = dict(entity) if isinstance(entity, dict) else entity
    if isinstance(candidate, dict) and isinstance(candidate.get("runtime_dependencies"), list):
        candidate["runtime_dependencies"] = [
            {
                **dependency,
                "generation_fingerprint": "sha256:" + "0" * 64,
            }
            if isinstance(dependency, dict) and dependency.get("generation_fingerprint") in {"__CURRENT__", "__CURRENT_ENTITY__"}
            else dependency
            for dependency in candidate["runtime_dependencies"]
        ]
    current = validate_machine_entity(candidate)
    return {
        "skill": current["skill"],
        "entity_type": current["entity_type"],
        "entity_ref": current["entity_ref"],
        "content_fingerprint": current["content_fingerprint"],
    }


def resolve_entity_dependencies(
    references: Iterable[tuple[str, str, str]],
    current_entities: Iterable[dict[str, Any]],
    *,
    require_all: bool = True,
) -> list[dict[str, str]]:
    """Resolve explicit full Machine Entity identities against current rows."""
    current_by_identity: dict[tuple[str, str, str], dict[str, Any]] = {}
    for value in current_entities:
        dependency = machine_entity_dependency(value)
        identity = entity_identity(dependency["skill"], dependency["entity_type"], dependency["entity_ref"])
        if identity in current_by_identity:
            raise InvalidInput("current Machine Entity identityが重複しています")
        current_by_identity[identity] = {
            "skill": dependency["skill"],
            "entity_type": dependency["entity_type"],
            "entity_ref": dependency["entity_ref"],
            "content_fingerprint": dependency["content_fingerprint"],
        }

    requested: set[tuple[str, str, str]] = set()
    for identity in references:
        if not isinstance(identity, tuple) or len(identity) != 3 or not all(isinstance(value, str) and value.strip() for value in identity):
            raise InvalidInput("Machine Entity reference identityが不正です")
        if identity in requested:
            raise InvalidInput("Machine Entity reference identityが重複しています")
        requested.add(identity)

    missing = requested - set(current_by_identity)
    if missing and require_all:
        raise InvalidInput("明示されたMachine Entity referenceをcurrent Entityへ解決できません")
    return [
        current_by_identity[identity]
        for identity in sorted(requested & set(current_by_identity))
    ]


def normalize_machine_entity_disposition(
    row: Any,
    current_entities: Iterable[dict[str, Any]],
    *,
    allowed_handlings: set[str],
    allowed_upstream_entity_types: set[str],
    input_mode: str,
) -> tuple[dict[str, Any], list[dict[str, str]]]:
    """Validate the shared Machine Entity Disposition schema and dependencies."""
    if not isinstance(row, dict) or set(row) != {"upstream_entity", "handling", "reason", "authority_refs", "covered_by_entity"}:
        raise InvalidInput("Machine Entity disposition schemaが不正です")
    current_rows = list(current_entities)
    current_by_identity: dict[tuple[str, str, str], dict[str, Any]] = {}
    for value in current_rows:
        entity = validate_machine_entity(value)
        identity = entity_identity(entity["skill"], entity["entity_type"], entity["entity_ref"])
        if identity in current_by_identity:
            raise InvalidInput("current Machine Entity identityが重複しています")
        current_by_identity[identity] = entity

    def current_reference(value: Any, name: str) -> tuple[str, str, str]:
        if not isinstance(value, dict) or set(value) != {"skill", "entity_type", "entity_ref", "content_fingerprint"}:
            raise InvalidInput(f"{name} schemaが不正です")
        identity = (value["skill"], value["entity_type"], value["entity_ref"])
        if not all(isinstance(part, str) and part.strip() for part in identity) or not FULL_DIGEST_RE.fullmatch(str(value["content_fingerprint"])):
            raise InvalidInput(f"{name} identity/fingerprintが不正です")
        current = current_by_identity.get(identity)
        if current is None or current["content_fingerprint"] != value["content_fingerprint"]:
            raise InvalidInput(f"{name}がunknownまたはstaleです")
        return identity

    upstream = row["upstream_entity"]
    upstream_identity = current_reference(upstream, "disposition upstream_entity")
    if upstream_identity[1] not in allowed_upstream_entity_types:
        raise InvalidInput("disposition upstream_entity_typeがこのSkillで許可されていません")
    handling = row["handling"]
    if handling not in allowed_handlings or not isinstance(row["reason"], str) or not row["reason"].strip():
        raise InvalidInput("disposition handling/reasonが不正です")
    refs = row["authority_refs"]
    if not isinstance(refs, list) or not all(isinstance(value, str) and value for value in refs) or len(set(refs)) != len(refs):
        raise InvalidInput("disposition authority_refsが不正です")

    covered = row["covered_by_entity"]
    dependency_identities = [upstream_identity]
    if handling == "重複":
        covered_identity = current_reference(covered, "重複disposition covered_by_entity")
        if covered_identity == upstream_identity:
            raise InvalidInput("重複dispositionはself referenceできません")
        dependency_identities.append(covered_identity)
    elif covered is not None:
        raise InvalidInput("重複以外のcovered_by_entityはnullである必要があります")

    authority_identities = [("spec-analysis", "authority", ref) for ref in refs]
    authority_dependencies = resolve_entity_dependencies(
        authority_identities,
        current_rows,
        require_all=input_mode == "artifact",
    )
    dependency_identities.extend(
        (row["skill"], row["entity_type"], row["entity_ref"])
        for row in authority_dependencies
    )
    dependencies = resolve_entity_dependencies(sorted(set(dependency_identities)), current_rows, require_all=True)
    normalized = canonicalize(row)
    normalized["authority_refs"] = sorted(refs)
    return normalized, dependencies


def validate_upstream_entities(metadata: dict[str, Any]) -> list[dict[str, Any]]:
    rows = ensure_list(metadata.get("upstream_entities"), "metadata.upstream_entities")
    entities: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"skill", "entity_type", "entity_ref", "content"}:
            raise InvalidInput("metadata.upstream_entitiesのschemaが不正です")
        content = row["content"]
        if not isinstance(content, dict):
            raise InvalidInput("upstream Entity contentはobjectである必要があります")
        entity = make_machine_entity(row["skill"], row["entity_type"], row["entity_ref"], content)
        validate_machine_entity(entity)
        identity = entity_identity(entity["skill"], entity["entity_type"], entity["entity_ref"])
        if identity in seen:
            raise InvalidInput("metadata.upstream_entitiesが重複しています")
        seen.add(identity)
        entities.append(entity)
    return entities


def input_fingerprint(skill: str, runtime_unit_key: str, input_mode: str, input_value: Any, authority_refs: list[str], reference_refs: list[str], selection_source: str | None) -> str:
    value: dict[str, Any] = {
        "skill": skill,
        "runtime_unit_key": runtime_unit_key,
        "input_mode": input_mode,
        "input": canonicalize(input_value),
        "authority_refs": sorted(set(authority_refs)),
        "reference_refs": sorted(set(reference_refs)),
    }
    if selection_source is not None:
        value["selection_source"] = selection_source
    return sha256_digest(value)


def model_fingerprint(metadata: dict[str, Any], input_fp: str) -> str | None:
    if metadata.get("model_key") is None:
        return None
    return sha256_digest({
        "model_key": metadata.get("model_key"),
        "model_type": metadata.get("model_type"),
        "technique_slug": metadata.get("technique_slug"),
        "selection_source": metadata.get("selection_source"),
        "selection_key": metadata.get("selection_key"),
        "input_fingerprint": input_fp,
    })


def generation_fingerprint(
    *,
    generator: str,
    input_fp: str,
    model_fp: str | None,
    runtime_contract_version: str,
    generator_contract_version: str,
    runtime_impl_fp: str,
    generator_impl_fp: str,
    upstream: list[dict[str, str]],
    static_data_versions: dict[str, str],
) -> str:
    return sha256_digest({
        "generator": generator,
        "envelope_version": ENVELOPE_VERSION,
        "input_fingerprint": input_fp,
        "model_fingerprint": model_fp,
        "runtime_contract_version": runtime_contract_version,
        "generator_contract_version": generator_contract_version,
        "runtime_implementation_fingerprint": runtime_impl_fp,
        "generator_implementation_fingerprint": generator_impl_fp,
        "upstream_entity_fingerprints": upstream,
        "static_data_versions": canonicalize(static_data_versions),
    })


def issue_row(
    *,
    issue_type: str,
    blocking: bool,
    skill: str,
    runtime_unit_key: str,
    model_key: str | None,
    target_key: str | None,
    generation_fp: str | None,
    authority_refs: list[str],
    required_information: str | None = None,
    route_to: str | None = None,
    resume_skill: str | None = None,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "issue_type": issue_type,
        "blocking": blocking,
        "skill": skill,
        "runtime_unit_key": runtime_unit_key,
        "model_key": model_key,
        "target_key": target_key,
        "generation_fingerprint": generation_fp,
        "authority_refs": sorted(set(authority_refs)),
    }
    if required_information is not None:
        row["required_information"] = required_information
    if route_to is not None:
        row["route_to"] = route_to
    if resume_skill is not None:
        row["resume_skill"] = resume_skill
    return row


def target_ref(model_key: str, target_key: str) -> str:
    return sha256_digest({"model_key": model_key, "target_key": target_key})


def post_process_targets(model_key: str, targets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    processed: list[dict[str, Any]] = []
    seen_keys: set[str] = set()
    seen_refs: dict[str, tuple[str, str]] = {}
    for raw in targets:
        if not isinstance(raw, dict):
            raise InvalidInput("targetはobjectである必要があります")
        if "target_key" not in raw or not isinstance(raw["target_key"], str) or not raw["target_key"]:
            raise InvalidInput("target_keyがありません")
        key = raw["target_key"]
        if key in seen_keys:
            raise InvalidInput("target_keyが重複しています")
        seen_keys.add(key)
        row = canonicalize(raw)
        materializable = row.get("materializable")
        if not isinstance(materializable, bool):
            raise InvalidInput("materializableはbooleanである必要があります")
        if materializable:
            execution = row.get("execution")
            if not isinstance(execution, dict):
                raise InvalidInput("materializable targetにはexecutionが必要です")
            execution_fp = sha256_digest(execution)
        else:
            if row.get("execution") is not None:
                raise InvalidInput("non-materializable targetのexecutionはnullである必要があります")
            execution_fp = None
        ref = target_ref(model_key, key)
        content = dict(row)
        content.pop("target_ref", None)
        content.pop("target_content_fingerprint", None)
        content.pop("execution_fingerprint", None)
        content_fp = sha256_digest(content)
        existing = seen_refs.get(ref)
        if existing and existing != (model_key, key):
            raise InternalRuntimeError("target_ref collision")
        seen_refs[ref] = (model_key, key)
        row["target_ref"] = ref
        row["execution_fingerprint"] = execution_fp
        row["target_content_fingerprint"] = content_fp
        processed.append(row)
    return processed


_ADAPTER_MODEL_TYPES = {"classification", "cause-effect", "schema", "ui"}
_UNSUPPORTED_HANDLINGS = {"llm_fallback", "対象外", "別テストレベル", "残存リスク", "成立不能", "重複", "ブロック中"}


def _normalized_models(normalized: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = normalized.get("models")
    if not isinstance(rows, list) or not rows:
        rows = normalized.get("active_model_metadata", [])
    if not isinstance(rows, list):
        return {}
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("model_key"), str):
            continue
        if row["model_key"] in result:
            raise InvalidInput("normalized modelsのmodel_keyが重複しています")
        result[row["model_key"]] = canonicalize(row)
    return result


def _normalized_model_union(normalized: dict[str, Any] | list[dict[str, Any]] | None) -> dict[str, dict[str, Any]]:
    scopes = normalized if isinstance(normalized, list) else [normalized or {}]
    result: dict[str, dict[str, Any]] = {}
    for scope in scopes:
        for model_key, row in _normalized_models(scope).items():
            previous = result.get(model_key)
            if previous is not None and canonical_json_text(previous) != canonical_json_text(row):
                raise InvalidInput("複数scopeでmodel metadataが不一致です")
            result[model_key] = row
    return result


def _entity_map(entities: list[dict[str, Any]]) -> dict[tuple[str, str, str], dict[str, Any]]:
    return {
        entity_identity(row["skill"], row["entity_type"], row["entity_ref"]): row
        for row in validate_entity_collection(entities)
    }


def _current_ci_ids(entities: list[dict[str, Any]], model_key: str) -> list[str]:
    result: list[str] = []
    for row in validate_entity_collection(entities):
        if row["entity_type"] != "ci":
            continue
        content = row.get("content", {})
        row_model = row.get("model_key") or (content.get("model_key") if isinstance(content, dict) else None)
        status = content.get("status") if isinstance(content, dict) else None
        if row_model == model_key and status not in {"deleted", "inactive"}:
            result.append(row["entity_ref"])
    return sorted(set(result))


def validate_unsupported_item_closures(
    value: Any,
    runtime_rows: list[dict[str, Any]],
    entities: list[dict[str, Any]],
    normalized: dict[str, Any] | list[dict[str, Any]] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Validate per-item and whole-model unsupported closure state.

    A closure is evidence for the current runtime generation; its presence
    alone never makes a runtime complete.  The function is shared by
    traceability and workflow aggregation so both paths apply the same
    generation, entity, model, and handling rules.
    """
    rows = ensure_list(value, "unsupported_item_closures")
    runtime_map = {(row["skill"], row["runtime_unit_key"]): row for row in runtime_rows}
    entity_map = _entity_map(entities)
    model_map = _normalized_model_union(normalized)
    unsupported: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    unsupported_by_runtime: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for runtime in runtime_rows:
        runtime_key = (runtime.get("skill"), runtime.get("runtime_unit_key"), runtime.get("generation_fingerprint"))
        items = runtime.get("unsupported_items", [])
        if not isinstance(items, list):
            raise InvalidInput("unsupported_itemsはarrayである必要があります")
        for item in items:
            required = {"item_key", "item_type", "source_key", "reason_code", "affected_technique_slug", "authority_refs"}
            if not isinstance(item, dict) or set(item) != required or not isinstance(item["item_key"], str) or not item["item_key"] or not isinstance(item["reason_code"], str) or not item["reason_code"]:
                raise InvalidInput("unsupported_items schemaが不正です")
            if not isinstance(item["authority_refs"], list) or len(set(item["authority_refs"])) != len(item["authority_refs"]) or not all(isinstance(ref, str) and ref for ref in item["authority_refs"]):
                raise InvalidInput("unsupported_items authority_refsが不正です")
            key = (runtime_key[0], runtime_key[1], str(runtime_key[2]), item["item_key"])
            if key in unsupported:
                raise InvalidInput("unsupported item identityが重複しています")
            unsupported[key] = item
            unsupported_by_runtime.setdefault(runtime_key, []).append(item)

    closures: list[dict[str, Any]] = []
    issues: list[dict[str, Any]] = []
    seen_items: set[tuple[str, str, str, str]] = set()
    seen_whole: set[tuple[str, str, str]] = set()
    for index, row in enumerate(rows):
        required = {"skill", "runtime_unit_key", "generation_fingerprint", "item_key", "reason_code", "handling", "reason", "authority_refs", "covered_by_entity"}
        if not isinstance(row, dict) or set(row) != required:
            raise InvalidInput(f"unsupported_item_closures[{index}]のschemaが不正です")
        runtime_key = (row["skill"], row["runtime_unit_key"])
        runtime = runtime_map.get(runtime_key)
        if runtime is None:
            issues.append({"issue_type": "unsupported_closure_unknown_runtime", "blocking": True, "runtime_unit_key": row["runtime_unit_key"], "skill": row["skill"]})
        elif row["generation_fingerprint"] != runtime.get("generation_fingerprint"):
            issues.append({"issue_type": "unsupported_closure_stale_generation", "blocking": True, "runtime_unit_key": row["runtime_unit_key"], "skill": row["skill"]})
        if row["handling"] not in _UNSUPPORTED_HANDLINGS or not isinstance(row["reason"], str) or not row["reason"].strip() or not isinstance(row["authority_refs"], list) or len(set(row["authority_refs"])) != len(row["authority_refs"]) or not all(isinstance(ref, str) and ref for ref in row["authority_refs"]):
            raise InvalidInput("unsupported closure handling/reason/authority_refsが不正です")
        if row["item_key"] is None:
            if row["reason_code"] is not None:
                raise InvalidInput("whole-model closureのreason_codeはnullである必要があります")
            whole_key = (row["skill"], row["runtime_unit_key"], row["generation_fingerprint"])
            if whole_key in seen_whole:
                raise InvalidInput("whole-model unsupported closureが重複しています")
            seen_whole.add(whole_key)
        else:
            if not isinstance(row["item_key"], str) or not row["item_key"] or not isinstance(row["reason_code"], str) or not row["reason_code"]:
                raise InvalidInput("unsupported closure item_key/reason_codeが不正です")
            item_key = (row["skill"], row["runtime_unit_key"], row["generation_fingerprint"], row["item_key"])
            if item_key in seen_items:
                raise InvalidInput("unsupported closureが重複しています")
            seen_items.add(item_key)
            item = unsupported.get(item_key)
            if item is None:
                issues.append({"issue_type": "unsupported_closure_missing_item", "blocking": True, "item_key": row["item_key"], "runtime_unit_key": row["runtime_unit_key"]})
            elif item["reason_code"] != row["reason_code"]:
                issues.append({"issue_type": "unsupported_closure_reason_mismatch", "blocking": True, "item_key": row["item_key"], "runtime_unit_key": row["runtime_unit_key"]})

        covered = row["covered_by_entity"]
        if row["handling"] in {"llm_fallback", "重複"}:
            if not isinstance(covered, dict) or set(covered) != {"skill", "entity_type", "entity_ref", "content_fingerprint"} or not FULL_DIGEST_RE.fullmatch(str(covered.get("content_fingerprint"))):
                issues.append({"issue_type": "unsupported_closure_missing_entity", "blocking": True, "item_key": row["item_key"], "runtime_unit_key": row["runtime_unit_key"]})
            else:
                covered_key = entity_identity(covered["skill"], covered["entity_type"], covered["entity_ref"])
                entity = entity_map.get(covered_key)
                if entity is None or entity.get("content_fingerprint") != covered["content_fingerprint"]:
                    issues.append({"issue_type": "unsupported_closure_stale_entity", "blocking": True, "item_key": row["item_key"], "runtime_unit_key": row["runtime_unit_key"]})
                elif runtime is not None and row["handling"] == "llm_fallback":
                    model_key = runtime.get("model_key")
                    item = unsupported.get((row["skill"], row["runtime_unit_key"], row["generation_fingerprint"], row["item_key"])) if row["item_key"] is not None else None
                    model_type = model_map.get(model_key, {}).get("model_type")
                    if entity.get("entity_type") != "ci":
                        issues.append({"issue_type": "unsupported_closure_not_ci", "blocking": True, "item_key": row["item_key"], "runtime_unit_key": row["runtime_unit_key"]})
                    elif model_type in _ADAPTER_MODEL_TYPES:
                        covered_model = entity.get("model_key") or entity.get("content", {}).get("model_key")
                        covered_model_meta = model_map.get(covered_model, {})
                        affected = item.get("affected_technique_slug") if item else None
                        if covered_model == model_key or not affected or covered_model_meta.get("technique_slug") != affected:
                            issues.append({"issue_type": "adapter_fallback_wrong_model", "blocking": True, "item_key": row["item_key"], "runtime_unit_key": row["runtime_unit_key"]})
                    elif entity.get("model_key") != model_key:
                        issues.append({"issue_type": "unsupported_closure_wrong_model", "blocking": True, "item_key": row["item_key"], "runtime_unit_key": row["runtime_unit_key"]})
        elif covered is not None:
            raise InvalidInput("unsupported closure covered_by_entityはnullである必要があります")
        closures.append(canonicalize(row))

    for runtime in runtime_rows:
        runtime_key = (runtime.get("skill"), runtime.get("runtime_unit_key"), runtime.get("generation_fingerprint"))
        items = unsupported_by_runtime.get(runtime_key, [])
        matching_items = {row["item_key"] for row in closures if row["skill"] == runtime_key[0] and row["runtime_unit_key"] == runtime_key[1] and row["generation_fingerprint"] == runtime_key[2] and row["item_key"] is not None}
        if runtime.get("support_status") == "unsupported":
            if not any(row["skill"] == runtime_key[0] and row["runtime_unit_key"] == runtime_key[1] and row["generation_fingerprint"] == runtime_key[2] and row["item_key"] is None for row in closures):
                issues.append({"issue_type": "whole_model_unsupported_closure_missing", "blocking": True, "runtime_unit_key": runtime_key[1], "skill": runtime_key[0]})
            if any(row["skill"] == runtime_key[0] and row["runtime_unit_key"] == runtime_key[1] and row["generation_fingerprint"] == runtime_key[2] and row["item_key"] is not None for row in closures):
                issues.append({"issue_type": "whole_model_unsupported_item_closure", "blocking": True, "runtime_unit_key": runtime_key[1], "skill": runtime_key[0]})
        elif runtime.get("support_status") == "partial" or items:
            for item in items:
                if item["item_key"] not in matching_items:
                    issues.append({"issue_type": "unsupported_closure_missing", "blocking": True, "item_key": item["item_key"], "runtime_unit_key": runtime_key[1], "skill": runtime_key[0]})
    return sorted(closures, key=lambda row: (row["skill"], row["runtime_unit_key"], str(row["item_key"]))), issues


def evaluate_target_disposition_closure(runtime_rows: list[dict[str, Any]], entities: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    """Check materialized target mapping/disposition chains across all units."""
    mappings: dict[str, dict[str, Any]] = {}
    dispositions: dict[str, dict[str, Any]] = {}
    entity_rows = validate_entity_collection(entities or []) if entities is not None else []
    entity_map = _entity_map(entity_rows) if entity_rows else {}
    issues: list[dict[str, Any]] = []
    for runtime in runtime_rows:
        for row in runtime.get("target_mappings", []):
            required = {"target_ref", "target_content_fingerprint", "generation_fingerprint", "execution_fingerprint", "model_key", "target_key", "ci_id"}
            if not isinstance(row, dict) or set(row) != required or not FULL_DIGEST_RE.fullmatch(str(row.get("target_ref"))) or not FULL_DIGEST_RE.fullmatch(str(row.get("target_content_fingerprint"))) or not FULL_DIGEST_RE.fullmatch(str(row.get("generation_fingerprint"))) or not FULL_DIGEST_RE.fullmatch(str(row.get("execution_fingerprint"))) or not isinstance(row.get("model_key"), str) or not isinstance(row.get("target_key"), str) or not CI_ID_RE.fullmatch(str(row.get("ci_id"))):
                raise InvalidInput("target mapping schemaが不正です")
            if row["target_ref"] != target_ref(row["model_key"], row["target_key"]):
                raise InvalidInput("target_refが不一致です")
            if row["target_ref"] in mappings or row["target_ref"] in dispositions:
                raise InvalidInput("target mappingが重複またはDispositionと重複しています")
            ci = entity_map.get(("test-condition-design", "ci", row["ci_id"]))
            if ci is not None and (ci.get("model_key") or ci.get("content", {}).get("model_key")) != row["model_key"]:
                issues.append({"issue_type": "target_mapping_wrong_model_ci", "blocking": True, "target_ref": row["target_ref"]})
            mappings[row["target_ref"]] = row
        for row in runtime.get("target_dispositions", []):
            required = {"target_ref", "target_content_fingerprint", "generation_fingerprint", "handling", "covered_by_target_version"}
            if not isinstance(row, dict) or set(row) != required or not FULL_DIGEST_RE.fullmatch(str(row.get("target_ref"))) or not FULL_DIGEST_RE.fullmatch(str(row.get("target_content_fingerprint"))) or not FULL_DIGEST_RE.fullmatch(str(row.get("generation_fingerprint"))) or row.get("handling") not in {"対象外", "別テストレベル", "残存リスク", "ブロック中", "重複"}:
                raise InvalidInput("target disposition projectionが不正です")
            if row["target_ref"] in mappings or row["target_ref"] in dispositions:
                raise InvalidInput("target dispositionが重複またはmappingと重複しています")
            covered = row["covered_by_target_version"]
            if row["handling"] == "重複":
                if (
                    not isinstance(covered, dict)
                    or set(covered) != {"target_ref", "target_content_fingerprint", "generation_fingerprint", "execution_fingerprint"}
                    or covered["target_ref"] == row["target_ref"]
                    or not FULL_DIGEST_RE.fullmatch(str(covered.get("target_ref")))
                    or not FULL_DIGEST_RE.fullmatch(str(covered.get("target_content_fingerprint")))
                    or not FULL_DIGEST_RE.fullmatch(str(covered.get("generation_fingerprint")))
                    or (covered.get("execution_fingerprint") is not None and not FULL_DIGEST_RE.fullmatch(str(covered.get("execution_fingerprint"))))
                ):
                    raise InvalidInput("target disposition covered versionが不正です")
            elif covered is not None:
                raise InvalidInput("重複以外のtarget disposition covered versionはnullである必要があります")
            dispositions[row["target_ref"]] = row

    def semantic_terminal(version: dict[str, Any]) -> bool | None:
        found_ref = False
        for entity in entity_rows:
            if entity["entity_type"] != "ci":
                continue
            content = entity.get("content", {})
            if content.get("source_kind") != "semantic_item" or content.get("status") != "active":
                continue
            for source in content.get("semantic_source_targets", []):
                if not isinstance(source, dict) or source.get("target_ref") != version["target_ref"]:
                    continue
                found_ref = True
                if (
                    source.get("target_content_fingerprint") == version["target_content_fingerprint"]
                    and source.get("generation_fingerprint") == version["generation_fingerprint"]
                ):
                    if version["execution_fingerprint"] is not None:
                        issues.append({"issue_type": "target_disposition_stale_execution", "blocking": True, "target_ref": version["target_ref"]})
                        return False
                    return True
        if found_ref:
            issues.append({"issue_type": "target_disposition_stale_covered_version", "blocking": True, "target_ref": version["target_ref"]})
            return False
        return None

    def mapping_terminal(ref: str, version: dict[str, Any] | None) -> bool:
        target = mappings[ref]
        if version is not None:
            if target["target_content_fingerprint"] != version["target_content_fingerprint"] or target["generation_fingerprint"] != version["generation_fingerprint"]:
                issues.append({"issue_type": "target_disposition_stale_covered_version", "blocking": True, "target_ref": ref})
                return False
            if target["execution_fingerprint"] != version["execution_fingerprint"]:
                issues.append({"issue_type": "target_disposition_stale_execution", "blocking": True, "target_ref": ref})
                return False
        ci = entity_map.get(("test-condition-design", "ci", target["ci_id"]))
        if ci is None:
            issues.append({"issue_type": "target_disposition_terminal_ci_missing", "blocking": True, "target_ref": ref})
            return False
        content = ci.get("content", {})
        mapped_targets = content.get("covered_targets", [])
        if (
            content.get("source_kind") != "runtime_target"
            or content.get("status") != "active"
            or (ci.get("model_key") or content.get("model_key")) != target["model_key"]
            or not any(
                isinstance(item, dict)
                and item.get("target_ref") == ref
                and item.get("target_content_fingerprint") == target["target_content_fingerprint"]
                and item.get("execution_fingerprint") == target["execution_fingerprint"]
                for item in mapped_targets
            )
        ):
            issues.append({"issue_type": "target_disposition_terminal_ci_mismatch", "blocking": True, "target_ref": ref})
            return False
        return True

    def terminal(ref: str, visiting: set[str], version: dict[str, Any] | None = None, *, through_duplicate: bool = False) -> bool:
        if ref in mappings:
            return mapping_terminal(ref, version)
        if ref in visiting:
            issues.append({"issue_type": "target_disposition_cycle", "blocking": True, "target_ref": ref})
            return False
        row = dispositions.get(ref)
        if row is None:
            if version is not None:
                semantic = semantic_terminal(version)
                if semantic is not None:
                    return semantic
            issues.append({"issue_type": "target_disposition_missing", "blocking": True, "target_ref": ref})
            return False
        if version is not None and (row["target_content_fingerprint"] != version["target_content_fingerprint"] or row["generation_fingerprint"] != version["generation_fingerprint"]):
            issues.append({"issue_type": "target_disposition_stale_covered_version", "blocking": True, "target_ref": ref})
            return False
        if through_duplicate and row["handling"] != "重複":
            issues.append({"issue_type": "target_disposition_non_coverage_terminal", "blocking": True, "target_ref": ref})
            return False
        if row["handling"] == "ブロック中":
            issues.append({"issue_type": "target_disposition_blocked", "blocking": True, "target_ref": ref})
            return False
        if row["handling"] == "重複":
            covered = row["covered_by_target_version"]
            target = mappings.get(covered["target_ref"]) or dispositions.get(covered["target_ref"])
            if target is not None and (target["target_content_fingerprint"] != covered["target_content_fingerprint"] or target["generation_fingerprint"] != covered["generation_fingerprint"]):
                issues.append({"issue_type": "target_disposition_stale_covered_version", "blocking": True, "target_ref": ref})
                return False
            if target is None:
                semantic = semantic_terminal(covered)
                if semantic is not None:
                    return semantic
                issues.append({"issue_type": "target_disposition_missing", "blocking": True, "target_ref": covered["target_ref"]})
                return False
            return terminal(covered["target_ref"], visiting | {ref}, covered, through_duplicate=True)
        return True

    for ref in sorted(dispositions):
        terminal(ref, set())
    return issues


def evaluate_materialize_completion(
    normalized: dict[str, Any],
    runtime_rows: list[dict[str, Any]],
    entities: list[dict[str, Any]],
    closures: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Validate model-level materialize completion without using actual sets as expected input."""
    models = _normalized_models(normalized)
    if not models:
        return []
    tcn_id = normalized.get("tcn_id")
    materialize_unit = f"artifact:materialize_coverage:{tcn_id}" if isinstance(tcn_id, str) and tcn_id else None
    materialize_rows = [
        row for row in runtime_rows
        if str(row.get("runtime_unit_key", "")).startswith("artifact:materialize_coverage:")
        and (materialize_unit is None or row.get("runtime_unit_key") == materialize_unit)
    ]
    if len(materialize_rows) > 1:
        raise InvalidInput("materialize runtime unitが重複しています")
    materialize = materialize_rows[0] if materialize_rows else None
    issues: list[dict[str, Any]] = []
    completion_rows = materialize.get("model_completion", []) if materialize is not None else []
    if not isinstance(completion_rows, list):
        raise InvalidInput("model_completionはarrayである必要があります")
    completion_by_model: dict[str, dict[str, Any]] = {}
    for row in completion_rows:
        required = {"model_key", "required_target_refs", "closed_target_refs", "active_ci_ids", "semantic_item_keys", "materialize_complete"}
        if not isinstance(row, dict) or set(row) != required or not isinstance(row["model_key"], str) or not isinstance(row["materialize_complete"], bool) or not all(isinstance(row[field], list) and len(set(row[field])) == len(row[field]) and all(isinstance(value, str) for value in row[field]) for field in ("required_target_refs", "closed_target_refs", "active_ci_ids", "semantic_item_keys")):
            raise InvalidInput("model_completion schemaが不正です")
        if row["model_key"] in completion_by_model:
            raise InvalidInput("model_completion model_keyが重複しています")
        completion_by_model[row["model_key"]] = row

    whole_closures = {(row["skill"], row["runtime_unit_key"], row["generation_fingerprint"]) for row in closures if row.get("item_key") is None}
    for model_key, model in models.items():
        model_type = model.get("model_type")
        if model_type in _ADAPTER_MODEL_TYPES:
            continue
        runtime = next((row for row in runtime_rows if row.get("runtime_unit_key") == f"model:{model_key}"), None)
        if runtime is not None and runtime.get("support_status") == "unsupported":
            key = (runtime.get("skill"), runtime.get("runtime_unit_key"), runtime.get("generation_fingerprint"))
            if key not in whole_closures:
                issues.append({"issue_type": "whole_model_unsupported_closure_missing", "blocking": True, "model_key": model_key})
            continue
        completion = completion_by_model.get(model_key)
        if completion is None:
            issues.append({"issue_type": "model_completion_missing", "blocking": True, "model_key": model_key})
            continue
        current_ci_ids = _current_ci_ids(entities, model_key)
        if sorted(completion["active_ci_ids"]) != current_ci_ids:
            issues.append({"issue_type": "model_completion_ci_mismatch", "blocking": True, "model_key": model_key})
        if model_type == "error-guessing":
            if not completion["active_ci_ids"] or not completion["semantic_item_keys"] or not completion["materialize_complete"]:
                issues.append({"issue_type": "semantic_model_incomplete", "blocking": True, "model_key": model_key})
        else:
            if not completion["required_target_refs"]:
                issues.append({"issue_type": "model_required_targets_missing", "blocking": True, "model_key": model_key})
            if not completion["materialize_complete"]:
                issues.append({"issue_type": "model_materialize_incomplete", "blocking": True, "model_key": model_key})
        if runtime is None and model_type not in {"error-guessing"}:
            issues.append({"issue_type": "model_runtime_missing", "blocking": True, "model_key": model_key})
    return issues


def runtime_unit_row(envelope: dict[str, Any], *, freshness_status: str = "current", materialize: dict[str, Any] | None = None) -> dict[str, Any]:
    fields = ("skill", "runtime_unit_key", "model_key", "support_status", "result_status", "runtime_status", "runtime_required", "deterministic_generated", "generation_fingerprint", "upstream_entity_fingerprints", "upstream_runtime_units", "unsupported_items")
    row = {field: envelope.get(field) for field in fields}
    payload = envelope.get("payload") if isinstance(envelope.get("payload"), dict) else {}
    if row["unsupported_items"] is None:
        row["unsupported_items"] = canonicalize(payload.get("unsupported_items", []))
    row["freshness_status"] = freshness_status
    for field in ("runtime_contract_version", "runtime_implementation_fingerprint", "generator_implementation_fingerprint", "generator_contract_version", "static_data_versions"):
        if field in envelope:
            row[field] = canonicalize(envelope[field])
    row["result_fingerprint"] = sha256_digest(envelope)
    row["model_completion"] = []
    row["target_mappings"] = []
    row["target_dispositions"] = []
    if materialize is not None:
        row["model_completion"] = canonicalize(materialize.get("model_completion", []))
        row["target_mappings"] = canonicalize(materialize.get("target_id_map", []))
        disposition_fields = ("target_ref", "target_content_fingerprint", "generation_fingerprint", "handling", "covered_by_target_version")
        dispositions = materialize.get("disposed_target_refs", [])
        if not isinstance(dispositions, list) or any(not isinstance(item, dict) or not set(disposition_fields).issubset(item) for item in dispositions):
            raise InvalidInput("materialize disposed_target_refs projectionが不正です")
        row["target_dispositions"] = canonicalize([{key: item[key] for key in disposition_fields} for item in dispositions])
    return row


def _runtime_unit_result_row(envelope: dict[str, Any], *, freshness_status: str = "current") -> dict[str, Any]:
    runtime_unit_key = envelope.get("runtime_unit_key")
    payload = envelope.get("payload")
    materialize = payload if isinstance(runtime_unit_key, str) and runtime_unit_key.startswith("artifact:materialize_coverage:") else None
    return runtime_unit_row(envelope, freshness_status=freshness_status, materialize=materialize)


def current_model_result_row(envelope: dict[str, Any], metadata: dict[str, Any]) -> dict[str, Any]:
    row = runtime_unit_row(envelope)
    payload = envelope.get("payload") or {}
    row.update({
        "model_key": metadata.get("model_key"),
        "model_type": metadata.get("model_type"),
        "technique_slug": metadata.get("technique_slug"),
        "generator_contract_version": envelope.get("generator_contract_version"),
        "input_fingerprint": envelope.get("input_fingerprint"),
        "model_fingerprint": envelope.get("model_fingerprint"),
        "freshness_status": "current",
        "targets": canonicalize(payload.get("targets", [])),
        "unsupported_items": canonicalize(payload.get("unsupported_items", [])),
    })
    for key in ("coverage_summary", "completion_summary"):
        if key in payload:
            row[key] = canonicalize(payload[key])
    return row


def bind_current_entity_runtime_dependencies(
    value: Any,
    generation_fp: str,
    *,
    runtime_context: dict[str, Any] | None = None,
) -> Any:
    """Bind current aggregate or content-scoped runtime generations."""
    if isinstance(value, dict):
        result = {key: bind_current_entity_runtime_dependencies(child, generation_fp, runtime_context=runtime_context) for key, child in value.items()}
        if "runtime_dependencies" in result and isinstance(result["runtime_dependencies"], list):
            dependencies = []
            for dependency in result["runtime_dependencies"]:
                if not isinstance(dependency, dict):
                    dependencies.append(dependency)
                    continue
                dependency = dict(dependency)
                if dependency.get("generation_fingerprint") == "__CURRENT__":
                    dependency["generation_fingerprint"] = generation_fp
                elif dependency.get("generation_fingerprint") == "__CURRENT_ENTITY__":
                    if not isinstance(runtime_context, dict):
                        raise InvalidInput("entity-scoped runtime generation context is missing")
                    base_unit_key = dependency["runtime_unit_key"]
                    dependency["runtime_unit_key"] = machine_entity_runtime_unit_key(base_unit_key, result)
                    dependency["generation_fingerprint"] = machine_entity_runtime_generation(result, runtime_context)
                dependencies.append(dependency)
            result["runtime_dependencies"] = dependencies
        return result
    if isinstance(value, list):
        return [bind_current_entity_runtime_dependencies(child, generation_fp, runtime_context=runtime_context) for child in value]
    return value


def render_json_fence(value: Any) -> str:
    return "```json\n" + canonical_json_text(canonicalize(value)) + "\n```"


def render_runtime_input(skill: str, metadata: dict[str, Any], input_value: Any) -> str:
    unit = f"{skill}::{metadata['runtime_unit_key']}"
    return f"### Machine Runtime Input: {unit}\n\n{render_json_fence({'metadata': metadata, 'input': input_value})}\n"


def render_runtime_result(skill: str, envelope: dict[str, Any]) -> str:
    unit = f"{skill}::{envelope['runtime_unit_key']}"
    return f"### Machine Runtime Result: {unit}\n\n{render_json_fence(envelope)}\n"


def render_machine_entities(skill: str, entities: list[dict[str, Any]]) -> str:
    return f"### Machine Entities: {skill}\n\n{render_json_fence({'schema_version': ENTITY_SCHEMA_VERSION, 'skill': skill, 'entities': entities})}\n"


_BLOCK_RE = re.compile(r"^### (?P<kind>Machine Runtime Input|Machine Runtime Result|Machine Entities): (?P<identity>[^\r\n]+)\r?\n\r?\n```json\r?\n(?P<body>.*?)\r?\n```", re.MULTILINE | re.DOTALL)


def extract_machine_blocks(markdown: str, kind: str, *, allow_duplicates: bool = False) -> list[tuple[str, dict[str, Any]]]:
    result: list[tuple[str, dict[str, Any]]] = []
    seen: set[str] = set()
    for match in _BLOCK_RE.finditer(markdown):
        if match.group("kind") != kind:
            continue
        identity = match.group("identity")
        if identity in seen and not allow_duplicates:
            raise InvalidInput(f"Machine blockが重複しています: {identity}")
        seen.add(identity)
        try:
            decoded = strict_loads(match.group("body").encode("utf-8"), aggregate=True)
        except RuntimeErrorBase:
            raise
        if not isinstance(decoded, dict):
            raise InvalidInput(f"Machine blockはobjectである必要があります: {identity}")
        result.append((identity, decoded))
    return result


def _unit_identity(skill: str, runtime_unit_key: str) -> str:
    return f"{skill}::{runtime_unit_key}"


def _state_result_blocks(state: dict[str, Any] | None, skill: str) -> dict[str, dict[str, Any]]:
    """Read only the fixed current-structure result projection, never actual units."""
    if not isinstance(state, dict):
        return {}
    source = state.get("runtime_results")
    if source is None:
        source = state.get("current_runtime_results")
    if source is None:
        source = state.get("parent_runtime_results")
    rows: list[tuple[str, Any]] = []
    if isinstance(source, dict):
        rows = [(str(identity), value) for identity, value in source.items()]
    elif isinstance(source, list):
        for row in source:
            if not isinstance(row, dict):
                continue
            identity = row.get("identity")
            if not isinstance(identity, str) and isinstance(row.get("skill"), str) and isinstance(row.get("runtime_unit_key"), str):
                identity = _unit_identity(row["skill"], row["runtime_unit_key"])
            if isinstance(identity, str):
                rows.append((identity, row.get("result", row)))
    result: dict[str, dict[str, Any]] = {}
    for identity, value in rows:
        if not identity.startswith(skill + "::") or not isinstance(value, dict):
            continue
        result[identity] = value
    return result


def _default_expected_runtime_units(
    skill: str,
    normalized: dict[str, Any],
    artifact_markdown: str,
    *,
    current_structure_state: dict[str, Any] | None = None,
    current_runtime_units: list[dict[str, Any]] | dict[tuple[str, str], dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Derive root units from normalized input and fixed dispatch metadata.

    This intentionally does not inspect the actual unit set to decide what is
    expected.  Conditional child units are added only from a verified parent
    result in the candidate artifact.
    """
    roots: list[tuple[str, str | None]] = []
    root_map = {
        "test-analysis": ["artifact:analysis_entities:all"],
        "test-requirement-design": ["artifact:requirement_structure:all"],
        "test-condition-design": ["artifact:condition_structure:all"],
        "test-case-design": ["artifact:case_structure:all"],
        "coverage-analysis": ["artifact:traceability:all"],
        "qa-workflow": ["artifact:workflow_runtime:all"],
    }
    for unit in root_map.get(skill, []):
        roots.append((unit, None))
    if skill == "test-analysis":
        conditional = (
            ("product_risks", "artifact:risk_matrix:all"),
            ("change_nodes", "artifact:change_impact:all"),
            ("change_edges", "artifact:change_impact:all"),
            ("environment_requirements", "artifact:environment_requirements:all"),
        )
        for field, unit in conditional:
            if isinstance(normalized.get(field), list) and normalized[field]:
                roots.append((unit, None))
        selections = normalized.get("technique_selections", [])
        if isinstance(selections, list):
            for row in selections:
                if isinstance(row, dict) and isinstance(row.get("selection_key"), str):
                    roots.append((f"artifact:technique_candidates:{row['selection_key']}", None))
    models = normalized.get("models", normalized.get("active_model_metadata", []))
    if not isinstance(models, list) or not models:
        models = normalized.get("active_model_metadata", [])
    model_state = {
        row.get("model_key"): row
        for row in normalized.get("model_key_state", [])
        if isinstance(row, dict) and isinstance(row.get("model_key"), str)
    }
    if isinstance(models, list):
        for model in models:
            if not isinstance(model, dict) or not isinstance(model.get("model_key"), str):
                continue
            model_type = model.get("model_type")
            state_row = model_state.get(model.get("model_key"), {})
            derived_from = model.get("derived_from_model_key", state_row.get("derived_from_model_key"))
            # Adapter-derived child models are conditional: the parent result
            # must first expose exactly one compatible derived_child_inputs row.
            if model_type in MODEL_GENERATORS and derived_from is None:
                roots.append((f"model:{model['model_key']}", model["model_key"]))
    if skill == "test-condition-design" and isinstance(normalized.get("test_data_requirements"), list) and normalized["test_data_requirements"]:
        roots.append(("artifact:test_data_requirements:all", None))
    if skill == "test-condition-design" and isinstance(models, list) and models:
        tcn_id = normalized.get("tcn_id")
        if isinstance(tcn_id, str):
            roots.append((f"artifact:materialize_coverage:{tcn_id}", None))
    deduped = {(skill, unit, model_key): {"skill": skill, "runtime_unit_key": unit, "model_key": model_key} for unit, model_key in roots}
    expected = [deduped[key] for key in sorted(deduped)]
    state_blocks = _state_result_blocks(current_structure_state, skill)
    if state_blocks:
        current_map: dict[tuple[str, str], dict[str, Any]] = {}
        if isinstance(current_runtime_units, dict):
            current_map = current_runtime_units
        elif isinstance(current_runtime_units, list):
            current_map = {(row.get("skill"), row.get("runtime_unit_key")): row for row in current_runtime_units if isinstance(row, dict)}
        verified_blocks = {
            identity: result
            for identity, result in state_blocks.items()
            if not current_map or current_map.get(tuple(identity.split("::", 1)), {}).get("generation_fingerprint") == result.get("generation_fingerprint")
        }
        _verified_child_units(skill, normalized, verified_blocks, expected)
    return expected


def _verified_child_units(
    skill: str,
    normalized: dict[str, Any],
    blocks: dict[str, dict[str, Any]],
    expected: list[dict[str, Any]],
    *,
    input_blocks: dict[str, dict[str, Any]] | None = None,
    issues: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    models = normalized.get("models", normalized.get("active_model_metadata", []))
    if not isinstance(models, list) or not models:
        models = normalized.get("active_model_metadata", [])
    model_state = {
        row.get("model_key"): row
        for row in normalized.get("model_key_state", [])
        if isinstance(row, dict) and isinstance(row.get("model_key"), str)
    }
    model_map = {
        row.get("model_key"): {**model_state.get(row.get("model_key"), {}), **row}
        for row in models
        if isinstance(row, dict) and isinstance(row.get("model_key"), str)
    } if isinstance(models, list) else {}
    expected_keys = {(row["skill"], row["runtime_unit_key"]) for row in expected}
    adapter_types = {"classification", "cause-effect", "schema", "ui"}
    for identity, result in blocks.items():
        if not identity.startswith(skill + "::model:"):
            continue
        payload = result.get("payload")
        if not isinstance(payload, dict) or result.get("result_status") != "ready":
            continue
        parent_key = identity.split("::model:", 1)[1]
        children_raw = payload.get("derived_child_inputs", [])
        if not isinstance(children_raw, list):
            if issues is not None:
                issues.append({"issue_type": "invalid_derived_child_inputs", "blocking": True, "runtime_unit": identity})
            continue
        children = [
            child for child in children_raw
            if isinstance(child, dict)
            and isinstance(child.get("child_model_key"), str)
            and child.get("parent_model_key", parent_key) == parent_key
        ]
        child_counts: dict[str, int] = {}
        for child in children:
            child_counts[child["child_model_key"]] = child_counts.get(child["child_model_key"], 0) + 1
        for child_key, count in child_counts.items():
            if count != 1 and issues is not None:
                issues.append({"issue_type": "duplicate_derived_child_input", "blocking": True, "runtime_unit": identity, "child_model_key": child_key})
        seen_children: set[str] = set()
        for child in children:
            child_key = child["child_model_key"]
            model = model_map.get(child_key)
            if model is None or model.get("derived_from_model_key") != parent_key:
                if issues is not None:
                    issues.append({"issue_type": "unknown_derived_child_input", "blocking": True, "runtime_unit": identity, "child_model_key": child_key})
                continue
            if child_key in seen_children or child_counts.get(child_key) != 1:
                continue
            if child.get("model_type") != model.get("model_type"):
                if issues is not None:
                    issues.append({"issue_type": "derived_child_model_type_mismatch", "blocking": True, "runtime_unit": identity, "child_model_key": child_key})
                continue
            seen_children.add(child_key)
            unit = f"model:{child_key}"
            if (skill, unit) not in expected_keys:
                expected.append({"skill": skill, "runtime_unit_key": unit, "model_key": child_key})
                expected_keys.add((skill, unit))
            if input_blocks is not None and result.get("generation_fingerprint"):
                child_input = input_blocks.get(_unit_identity(skill, unit))
                dependency = {"skill": skill, "runtime_unit_key": identity.split("::", 1)[1], "generation_fingerprint": result["generation_fingerprint"]}
                actual_dependencies = child_input.get("metadata", {}).get("upstream_runtime_units", []) if isinstance(child_input, dict) else None
                if not isinstance(actual_dependencies, list) or dependency not in actual_dependencies:
                    if issues is not None:
                        issues.append({"issue_type": "missing_derived_child_runtime_dependency", "blocking": True, "runtime_unit": _unit_identity(skill, unit), "upstream_runtime_unit": dependency})
        if result.get("result_status") == "ready" and model_map.get(parent_key, {}).get("model_type") in adapter_types:
            for child_key, model in model_map.items():
                if model.get("derived_from_model_key") != parent_key:
                    continue
                matching = [child for child in children if child.get("child_model_key") == child_key]
                if len(matching) != 1 and issues is not None:
                    issues.append({"issue_type": "missing_or_duplicate_derived_child_input", "blocking": True, "runtime_unit": identity, "child_model_key": child_key, "count": len(matching)})
    return expected


def _expected_generator(skill: str, runtime_unit_key: str, normalized: dict[str, Any]) -> str | None:
    artifact_generators = {
        "test-analysis": {
            "artifact:analysis_entities:all": "analysis_entities",
            "artifact:risk_matrix:all": "risk_matrix",
            "artifact:technique_candidates:all": "technique_candidates",
            "artifact:change_impact:all": "change_impact",
            "artifact:environment_requirements:all": "environment_requirements",
        },
        "test-requirement-design": {"artifact:requirement_structure:all": "requirement_structure"},
        "test-condition-design": {
            "artifact:condition_structure:all": "condition_structure",
            "artifact:test_data_requirements:all": "test_data_requirements",
            f"artifact:materialize_coverage:{normalized.get('tcn_id')}": "materialize_coverage",
        },
        "test-case-design": {"artifact:case_structure:all": "case_structure"},
        "coverage-analysis": {"artifact:traceability:all": "traceability"},
        "qa-workflow": {"artifact:workflow_runtime:all": "workflow_runtime"},
    }
    if runtime_unit_key in artifact_generators.get(skill, {}):
        return artifact_generators[skill][runtime_unit_key]
    if skill == "test-analysis" and runtime_unit_key.startswith("artifact:technique_candidates:"):
        return "technique_candidates"
    if runtime_unit_key.startswith("model:"):
        model_key = runtime_unit_key.split(":", 1)[1]
        models = normalized.get("models", normalized.get("active_model_metadata", []))
        if not isinstance(models, list) or not models:
            models = normalized.get("active_model_metadata", [])
        if isinstance(models, list):
            for row in models:
                if isinstance(row, dict) and row.get("model_key") == model_key:
                    return MODEL_GENERATORS.get(row.get("model_type"))
    return None


def _runtime_result_entities(result_blocks: Iterable[tuple[str, dict[str, Any]]], skill: str) -> list[dict[str, Any]]:
    """Project generated Machine Entities only from fixed runtime result payloads."""
    entities: dict[tuple[str, str, str], dict[str, Any]] = {}
    for identity, result in result_blocks:
        if not identity.startswith(skill + "::"):
            continue
        payload = result.get("payload")
        if not isinstance(payload, dict) or "entities" not in payload:
            continue
        rows = validate_entity_collection(payload["entities"], expected_skill=skill)
        for entity in rows:
            key = entity_identity(entity["skill"], entity["entity_type"], entity["entity_ref"])
            previous = entities.get(key)
            if previous is not None and canonical_json_text(previous) != canonical_json_text(entity):
                raise InvalidInput("current runtime result Machine Entity identity conflicts")
            entities[key] = entity
    return [entities[key] for key in sorted(entities)]


def _artifact_machine_entity_map(markdown: str) -> dict[str, list[dict[str, Any]]]:
    blocks = extract_machine_blocks(markdown, "Machine Entities", allow_duplicates=True)
    grouped: dict[str, list[dict[str, Any]]] = {}
    seen_block_skills: set[str] = set()
    identities: set[tuple[str, str, str]] = set()
    for block_skill, body in blocks:
        if block_skill in seen_block_skills:
            raise InvalidInput("Machine Entities block is duplicated")
        seen_block_skills.add(block_skill)
        if set(body) != {"schema_version", "skill", "entities"} or body.get("schema_version") != ENTITY_SCHEMA_VERSION or body.get("skill") != block_skill:
            raise InvalidInput("Machine Entities block schema or owner is invalid")
        rows = validate_entity_collection(body.get("entities"), expected_skill=block_skill)
        for row in rows:
            key = entity_identity(row["skill"], row["entity_type"], row["entity_ref"])
            if key in identities:
                raise InvalidInput("Machine Entity identity is duplicated across blocks")
            identities.add(key)
        grouped[block_skill] = rows
    return grouped


def _validate_previous_entity_state(
    skill: str,
    entities: list[dict[str, Any]],
    states: dict[str, dict[str, str]],
) -> None:
    for entity_type, state in states.items():
        entity_refs = {row["entity_ref"] for row in entities if row["skill"] == skill and row["entity_type"] == entity_type}
        if entity_refs != {ref for ref, status in state.items() if status == "active"}:
            raise InvalidInput("previous ID state and Machine Entities are inconsistent")


def _state_map(rows: Any, id_field: str, *, state_field: str = "status") -> dict[str, str]:
    if not isinstance(rows, list):
        return {}
    result: dict[str, str] = {}
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get(id_field), str) or row.get(state_field) not in {"active", "deleted"}:
            raise InvalidInput("previous full ID state is invalid")
        ref = row[id_field]
        if ref in result:
            raise InvalidInput("previous full ID state is duplicated")
        result[ref] = row[state_field]
    return result


def _previous_entity_states(
    skill: str,
    normalized: dict[str, Any],
    previous_result_blocks: Iterable[tuple[str, dict[str, Any]]] | None = None,
) -> dict[str, dict[str, str]]:
    state_fields = {
        "test-requirement-design": {"tr": ("tr_id_state", "tr_id")},
        "test-condition-design": {
            "tcn": ("tcn_id_state", "tcn_id"),
            "model": ("model_key_state", "model_key"),
            "ci": ("ci_id_state", "ci_id"),
        },
        "test-case-design": {"tc": ("tc_id_state", "tc_id")},
    }.get(skill, {})
    normalized_fields = {
        "tr": "previous_tr_ids",
        "tcn": "previous_tcn_ids",
        "model": "previous_model_keys",
        "tc": "previous_tc_ids",
        "ci": "previous_ci_ids",
    }
    if previous_result_blocks is None:
        return {
            entity_type: _state_map(normalized.get(normalized_fields[entity_type], []), id_field)
            for entity_type, (_field, id_field) in state_fields.items()
        }

    payloads: list[tuple[str, dict[str, Any]]] = []
    for identity, result in previous_result_blocks:
        if identity.startswith(skill + "::") and isinstance(result.get("payload"), dict):
            payloads.append((identity, result["payload"]))
    output: dict[str, dict[str, str]] = {}
    root_units = {
        "test-requirement-design": "artifact:requirement_structure:all",
        "test-condition-design": "artifact:condition_structure:all",
        "test-case-design": "artifact:case_structure:all",
    }
    for entity_type, (field, id_field) in state_fields.items():
        if entity_type == "ci":
            merged_rows: list[dict[str, Any]] = []
            seen_ci_ids: set[str] = set()
            for identity, payload in sorted(payloads):
                runtime_unit_key = identity.split("::", 1)[1]
                prefix = "artifact:materialize_coverage:"
                is_materialize = runtime_unit_key.startswith(prefix)
                if is_materialize and field not in payload:
                    raise InvalidInput("previous TCN materialize result is missing ci_id_state")
                if field not in payload:
                    continue
                if not is_materialize:
                    raise InvalidInput("previous ci_id_state must come from a TCN-scoped materialize result")
                tcn_id = runtime_unit_key[len(prefix):]
                if re.fullmatch(r"TCN-[0-9]{3}", tcn_id) is None:
                    raise InvalidInput("previous materialize runtime TCN identity is invalid")
                rows = payload[field]
                if not isinstance(rows, list):
                    raise InvalidInput("previous ci_id_state is invalid")
                for row in rows:
                    if not isinstance(row, dict) or set(row) != {id_field, "status"}:
                        raise InvalidInput("previous ci_id_state row schema is invalid")
                    ci_id = row.get(id_field)
                    if not isinstance(ci_id, str) or re.fullmatch(re.escape(tcn_id) + r"-CI[0-9]{2,}", ci_id) is None:
                        raise InvalidInput("previous ci_id_state TCN prefix does not match materialize runtime")
                    if ci_id in seen_ci_ids:
                        raise InvalidInput("previous ci_id_state contains a duplicate CI identity")
                    seen_ci_ids.add(ci_id)
                    merged_rows.append(row)
            output[entity_type] = _state_map(merged_rows, id_field)
            continue

        field_rows: list[Any] = []
        expected_identity = _unit_identity(skill, root_units[skill])
        for identity, payload in payloads:
            if field not in payload:
                continue
            if identity != expected_identity:
                raise InvalidInput(f"previous {field} must come from {expected_identity}")
            field_rows.append(payload[field])
        if len(field_rows) > 1:
            raise InvalidInput(f"previous {field} is duplicated")
        source = field_rows[0] if field_rows else []
        output[entity_type] = _state_map(source, id_field)
    return output


def _identity_is_updated(skill: str, entity: dict[str, Any], normalized: dict[str, Any]) -> bool:
    entity_type = entity["entity_type"]
    ref = entity["entity_ref"]
    update_tcn = set(normalized.get("update_scope_tcn_ids", []))
    update_model = set(normalized.get("update_scope_model_keys", []))
    update_tr = set(normalized.get("update_scope_tr_ids", []))
    update_tc = set(normalized.get("update_scope_tc_ids", []))
    if skill == "test-requirement-design" and entity_type == "tr":
        return ref in update_tr
    if skill == "test-condition-design":
        if entity_type == "tcn":
            return ref in update_tcn
        if entity_type == "model":
            return (entity.get("model_key") or ref) in update_model
        if entity_type == "ci":
            content = entity.get("content", {})
            return content.get("tcn_id") in update_tcn or (entity.get("model_key") or content.get("model_key")) in update_model
        if entity_type == "test_data_requirement":
            content = entity.get("content", {})
            model_key = content.get("source_model_key")
            return isinstance(model_key, str) and model_key in update_model
    if skill == "test-case-design" and entity_type == "tc":
        return ref in update_tc
    if entity_type == "disposition":
        upstream = entity.get("content", {}).get("upstream_entity")
        if not isinstance(upstream, dict):
            raise InvalidInput("Disposition ownership is missing from previous Machine Entity")
        upstream_type = upstream.get("entity_type")
        upstream_ref = upstream.get("entity_ref")
        if not isinstance(upstream_type, str) or not isinstance(upstream_ref, str):
            raise InvalidInput("Disposition upstream identity is invalid")
        if skill == "test-requirement-design":
            current_authorities = {row.get("authority_id") for row in normalized.get("authorities", []) if isinstance(row, dict)}
            current_risks = {row.get("risk_id") for row in normalized.get("risks", []) if isinstance(row, dict)}
            return (upstream_type == "authority" and upstream_ref in current_authorities) or (upstream_type == "product_risk" and upstream_ref in current_risks)
        if skill == "test-condition-design":
            if upstream_type == "tr":
                current_trs = {
                    row.get("tr_id") or row.get("entity_ref")
                    for row in normalized.get("test_requirements", []) if isinstance(row, dict)
                }
                return upstream_ref in current_trs
            if upstream_type == "tcn":
                return upstream_ref in update_tcn
            if upstream_type == "model":
                return upstream_ref in update_model
            if upstream_type in {"ci", "test_data_requirement"}:
                owner_entity = entity.get("_owner_entity")
                if not isinstance(owner_entity, dict):
                    return False
                owner_content = owner_entity.get("content", {})
                if upstream_type == "ci":
                    return owner_content.get("tcn_id") in update_tcn or owner_entity.get("model_key") in update_model
                return owner_content.get("source_model_key") in update_model
        if skill == "test-case-design":
            current_refs = {
                "tcn": {row.get("tcn_id") for row in normalized.get("test_conditions", []) if isinstance(row, dict)},
                "ci": {row.get("ci_id") or row.get("entity_ref") for row in normalized.get("coverage_items", []) if isinstance(row, dict)},
                "environment_requirement": {row.get("requirement_key") or row.get("entity_ref") for row in normalized.get("environment_requirements", []) if isinstance(row, dict)},
                "test_data_requirement": {row.get("data_ref") or row.get("entity_ref") for row in normalized.get("test_data_requirements", []) if isinstance(row, dict)},
            }
            return upstream_ref in current_refs.get(upstream_type, set())
    return False


def _active_previous_entity_identities(
    skill: str,
    normalized: dict[str, Any],
    states: dict[str, dict[str, str]],
) -> set[tuple[str, str, str]]:
    result: set[tuple[str, str, str]] = set()
    state_types = {
        "test-requirement-design": (("tr", "update_scope_tr_ids"),),
        "test-condition-design": (("tcn", "update_scope_tcn_ids"), ("model", "update_scope_model_keys")),
        "test-case-design": (("tc", "update_scope_tc_ids"),),
    }.get(skill, ())
    for entity_type, scope_field in state_types:
        scope = set(normalized.get(scope_field, []))
        for ref, status in states.get(entity_type, {}).items():
            if status == "active" and ref not in scope:
                result.add((skill, entity_type, ref))
    if skill == "test-condition-design":
        current_tcn = normalized.get("tcn_id")
        # materialize_coverage is TCN-scoped; an invoked TCN replaces its CI
        # snapshot, while active CI state for other TCNs remains carryable.
        materialized_tcn = current_tcn if isinstance(current_tcn, str) else None
        updated_tcns = set(normalized.get("update_scope_tcn_ids", []))
        for ref, status in states.get("ci", {}).items():
            if status != "active":
                continue
            match = re.fullmatch(r"(TCN-[0-9]{3})-CI[0-9]{2,}", ref)
            if match is None:
                raise InvalidInput("previous CI identity has no valid TCN owner")
            owner_tcn = match.group(1)
            if owner_tcn in updated_tcns or owner_tcn == materialized_tcn:
                continue
            result.add((skill, "ci", ref))
    return result


def _carry_forward_machine_entities(
    skill: str,
    normalized: dict[str, Any],
    previous_entities: list[dict[str, Any]],
    states: dict[str, dict[str, str]],
) -> list[dict[str, Any]]:
    owners = {
        entity_identity(row["skill"], row["entity_type"], row["entity_ref"]): row
        for row in previous_entities
        if isinstance(row, dict) and all(isinstance(row.get(field), str) for field in ("skill", "entity_type", "entity_ref"))
    }
    result: list[dict[str, Any]] = []
    for row in previous_entities:
        if not isinstance(row, dict) or row.get("skill") != skill:
            continue
        status_map = states.get(row["entity_type"], {})
        if row["entity_type"] in states and status_map.get(row["entity_ref"]) != "active":
            continue
        candidate = dict(row)
        if row["entity_type"] == "disposition":
            upstream = row.get("content", {}).get("upstream_entity", {})
            owner_key = (upstream.get("skill"), upstream.get("entity_type"), upstream.get("entity_ref")) if isinstance(upstream, dict) else None
            if owner_key in owners:
                candidate["_owner_entity"] = owners[owner_key]
        if not _identity_is_updated(skill, candidate, normalized):
            result.append(row)
    return result


def _previous_artifact_required_for_carry_forward(skill: str, normalized: dict[str, Any]) -> bool:
    """Whether normalized full state proves that an out-of-scope entity must survive."""
    states = _previous_entity_states(skill, normalized)
    return bool(_active_previous_entity_identities(skill, normalized, states))


def _current_scope_disposition_owner_ids(skill: str, normalized: dict[str, Any]) -> set[tuple[str, str, str]]:
    """Producer-valid upstream identities being regenerated by this invocation."""
    result: set[tuple[str, str, str]] = set()

    def add(owner_skill: str, entity_type: str, ref: Any) -> None:
        if isinstance(ref, str) and ref:
            result.add((owner_skill, entity_type, ref))

    if skill == "test-requirement-design":
        for row in normalized.get("authorities", []):
            if isinstance(row, dict):
                add("spec-analysis", "authority", row.get("authority_id"))
        for row in normalized.get("risks", []):
            if isinstance(row, dict):
                add("test-analysis", "product_risk", row.get("risk_id"))
    elif skill == "test-condition-design":
        for row in normalized.get("test_requirements", []):
            if isinstance(row, dict):
                add("test-requirement-design", "tr", row.get("tr_id") or row.get("entity_ref"))
        for ref in normalized.get("update_scope_tcn_ids", []):
            add(skill, "tcn", ref)
        for ref in normalized.get("update_scope_model_keys", []):
            add(skill, "model", ref)
        tcn_id = normalized.get("tcn_id")
        if isinstance(tcn_id, str):
            add(skill, "tcn", tcn_id)
        for ref in normalized.get("ci_ids", []):
            add(skill, "ci", ref)
        materialize = normalized.get("materialize_coverage")
        if isinstance(materialize, dict):
            for row in materialize.get("ci_id_state", []):
                if isinstance(row, dict) and row.get("status") == "active":
                    add(skill, "ci", row.get("ci_id"))
        for row in normalized.get("test_data_requirements", []):
            if isinstance(row, dict):
                add(skill, "test_data_requirement", row.get("data_ref") or (f"data:{row['requirement_key']}" if isinstance(row.get("requirement_key"), str) else None))
    elif skill == "test-case-design":
        rows = (
            ("test_conditions", "test-condition-design", "tcn", ("tcn_id",)),
            ("coverage_items", "test-condition-design", "ci", ("ci_id", "entity_ref")),
            ("environment_requirements", "test-analysis", "environment_requirement", ("requirement_key", "entity_ref")),
            ("test_data_requirements", "test-condition-design", "test_data_requirement", ("data_ref", "entity_ref")),
        )
        for field, owner_skill, entity_type, ref_fields in rows:
            for row in normalized.get(field, []):
                if not isinstance(row, dict):
                    continue
                ref = next((row.get(name) for name in ref_fields if isinstance(row.get(name), str)), None)
                add(owner_skill, entity_type, ref)
    return result


def validate_current_structure_state(
    skill: str,
    normalized: dict[str, Any],
    state: Any,
    *,
    current_entities: list[dict[str, Any]] | None = None,
    current_runtime_units: list[dict[str, Any]] | dict[tuple[str, str], dict[str, Any]] | None = None,
) -> dict[str, Any] | None:
    """Strictly validate the fixed verifier projection consumed by workflow/traceability."""
    if state is None:
        raise InvalidInput("current_structure_state from verify_runtime_evidence is required")
    if not isinstance(state, dict) or set(state) != {"runtime_results", "carry_forward_entities", "previous_ci_id_state"}:
        raise InvalidInput("current_structure_state schema is invalid")
    raw_results = state["runtime_results"]
    if not isinstance(raw_results, list):
        raise InvalidInput("current_structure_state.runtime_results must be an array")
    result_blocks: list[tuple[str, dict[str, Any]]] = []
    seen_results: set[str] = set()
    for row in raw_results:
        if not isinstance(row, dict) or set(row) != {"identity", "result"}:
            raise InvalidInput("current_structure_state runtime result row schema is invalid")
        identity, result = row["identity"], row["result"]
        if not isinstance(identity, str) or not identity.startswith(skill + "::") or identity in seen_results or not isinstance(result, dict):
            raise InvalidInput("current_structure_state runtime result identity is unknown or duplicated")
        result_fields = {
            "envelope_version", "skill", "runtime_contract_version", "generator_contract_version", "generator", "runtime_unit_key", "model_key",
            "input_fingerprint", "model_fingerprint", "generation_fingerprint", "runtime_implementation_fingerprint", "generator_implementation_fingerprint",
            "upstream_entity_fingerprints", "upstream_runtime_units", "support_status", "static_data_versions", "runtime_status", "result_status",
            "runtime_required", "deterministic_generated", "fallback_reason", "payload", "issues",
        }
        if set(result) != result_fields or result.get("envelope_version") != ENVELOPE_VERSION or result.get("runtime_contract_version") != RUNTIME_CONTRACT_VERSION:
            raise InvalidInput("current_structure_state runtime result schema/version is invalid")
        if result.get("support_status") not in SUPPORTED_SUPPORT_STATUSES or result.get("runtime_status") not in SUPPORTED_STATUSES or result.get("result_status") not in SUPPORTED_RESULT_STATUSES:
            raise InvalidInput("current_structure_state runtime result status is invalid")
        if not isinstance(result.get("payload"), dict) or not isinstance(result.get("issues"), list):
            raise InvalidInput("current_structure_state runtime result payload is invalid")
        for field in ("input_fingerprint", "generation_fingerprint", "runtime_implementation_fingerprint", "generator_implementation_fingerprint"):
            if not FULL_DIGEST_RE.fullmatch(str(result.get(field))):
                raise InvalidInput("current_structure_state runtime result fingerprint is invalid")
        if result.get("model_key") is None:
            if result.get("model_fingerprint") is not None:
                raise InvalidInput("current_structure_state artifact model_fingerprint must be null")
        elif not FULL_DIGEST_RE.fullmatch(str(result.get("model_fingerprint"))):
            raise InvalidInput("current_structure_state model_fingerprint is invalid")
        runtime_row = _runtime_unit_result_row(result)
        if _unit_identity(runtime_row["skill"], runtime_row["runtime_unit_key"]) != identity:
            raise InvalidInput("current_structure_state runtime result identity does not match its result")
        seen_results.add(identity)
        result_blocks.append((identity, result))
    raw_carry = state["carry_forward_entities"]
    carry = validate_entity_collection(raw_carry, expected_skill=skill)
    if len(carry) != len(raw_carry):
        raise InvalidInput("current_structure_state carry-forward entity identity is duplicated")
    raw_previous_ci_state = state["previous_ci_id_state"]
    if not isinstance(raw_previous_ci_state, list):
        raise InvalidInput("current_structure_state.previous_ci_id_state must be an array")
    if skill == "test-condition-design":
        if any(not isinstance(row, dict) or set(row) != {"ci_id", "status"} for row in raw_previous_ci_state):
            raise InvalidInput("current_structure_state previous CI state row schema is invalid")
        previous_ci_state = _state_map(raw_previous_ci_state, "ci_id")
        if any(re.fullmatch(r"TCN-[0-9]{3}-CI[0-9]{2,}", ci_id) is None for ci_id in previous_ci_state):
            raise InvalidInput("current_structure_state previous CI identity is invalid")
        if raw_previous_ci_state != [{"ci_id": ci_id, "status": previous_ci_state[ci_id]} for ci_id in sorted(previous_ci_state)]:
            raise InvalidInput("current_structure_state previous CI state is not canonical")
    else:
        if raw_previous_ci_state:
            raise InvalidInput("current_structure_state previous CI state is only valid for test-condition-design")
        previous_ci_state = {}

    result_entities = _runtime_result_entities(result_blocks, skill)
    result_ids = {entity_identity(row["skill"], row["entity_type"], row["entity_ref"]) for row in result_entities}
    carry_ids = {entity_identity(row["skill"], row["entity_type"], row["entity_ref"]) for row in carry}
    primary_types = {
        "test-requirement-design": {"tr"},
        "test-condition-design": {"tcn", "model", "ci"},
        "test-case-design": {"tc"},
    }.get(skill, set())
    states = _previous_entity_states(skill, normalized)
    required_primary = _active_previous_entity_identities(skill, normalized, states)
    if skill == "test-condition-design":
        states["ci"] = previous_ci_state
        required_primary = _active_previous_entity_identities(skill, normalized, states)
    projected_primary = {key for key in carry_ids if key[1] in primary_types}
    if projected_primary != required_primary:
        raise InvalidInput("current_structure_state primary carry-forward identities do not exactly match normalized scope")
    if result_ids & carry_ids:
        raise InvalidInput("current_structure_state carries an entity generated by current runtime results")

    carry_by_id = {entity_identity(row["skill"], row["entity_type"], row["entity_ref"]): row for row in carry}
    current_by_id = {
        entity_identity(row["skill"], row["entity_type"], row["entity_ref"]): row
        for row in (current_entities or [])
    }
    carried_model_keys = {key[2] for key in required_primary if key[1] == "model"}
    carried_tcn_ids = {key[2] for key in required_primary if key[1] == "tcn"}
    allowed_disposition_upstreams = {
        "test-requirement-design": {"authority": "spec-analysis", "product_risk": "test-analysis"},
        "test-condition-design": {"tr": "test-requirement-design"},
        "test-case-design": {"tcn": "test-condition-design", "ci": "test-condition-design", "environment_requirement": "test-analysis", "test_data_requirement": "test-condition-design"},
    }.get(skill, {})
    current_scope_owners = _current_scope_disposition_owner_ids(skill, normalized)
    for row in carry:
        key = entity_identity(row["skill"], row["entity_type"], row["entity_ref"])
        if row["entity_type"] in primary_types:
            if row["entity_type"] == "ci":
                match = re.fullmatch(r"(TCN-[0-9]{3})-CI[0-9]{2,}", row["entity_ref"])
                content = row.get("content", {})
                owner_tcn = content.get("tcn_id") if isinstance(content, dict) else None
                owner_model = content.get("model_key") if isinstance(content, dict) else None
                if key not in required_primary or match is None or owner_tcn != match.group(1) or owner_tcn not in carried_tcn_ids or owner_model not in carried_model_keys:
                    raise InvalidInput("carry-forward CI is not owned by a scope-out TCN/model")
                if key in result_ids or owner_tcn in set(normalized.get("update_scope_tcn_ids", [])) or owner_tcn == normalized.get("tcn_id"):
                    raise InvalidInput("current TCN CI cannot be carried forward")
                continue
            if key not in required_primary:
                raise InvalidInput("current_structure_state includes an unknown or in-scope primary entity")
            continue
        if skill == "test-condition-design" and row["entity_type"] == "test_data_requirement":
            model_key = row["content"].get("source_model_key")
            if not isinstance(model_key, str) or model_key not in carried_model_keys or model_key in set(normalized.get("update_scope_model_keys", [])):
                raise InvalidInput("carry-forward test data requirement is not owned by a scope-out model")
            if (skill, "model", model_key) not in carry_by_id:
                raise InvalidInput("carry-forward test data requirement owner model is missing")
            continue
        if row["entity_type"] != "disposition":
            raise InvalidInput("current_structure_state contains an unsupported carry-forward entity type")
        content = row["content"]
        upstream = content.get("upstream_entity") if isinstance(content, dict) else None
        if not isinstance(upstream, dict):
            raise InvalidInput("carry-forward disposition owner is missing")
        owner_id = entity_identity(upstream.get("skill"), upstream.get("entity_type"), upstream.get("entity_ref"))
        if upstream.get("entity_type") not in allowed_disposition_upstreams or upstream.get("skill") != allowed_disposition_upstreams.get(upstream.get("entity_type")):
            raise InvalidInput("carry-forward disposition upstream type is not produced by this Skill")
        owner = current_by_id.get(owner_id)
        if owner is None or owner.get("content_fingerprint") != upstream.get("content_fingerprint"):
            raise InvalidInput("carry-forward disposition owner is unknown or stale")
        if owner_id in current_scope_owners:
            raise InvalidInput("in-scope disposition cannot be carried forward")
        if skill == "test-case-design" and owner_id in current_scope_owners:
            raise InvalidInput("in-scope disposition cannot be carried forward")

    expected_runtime = _default_expected_runtime_units(
        skill, normalized, "", current_structure_state=state, current_runtime_units=current_runtime_units,
    )
    expected_runtime_ids = {_unit_identity(row["skill"], row["runtime_unit_key"]) for row in expected_runtime}
    if not seen_results.issubset(expected_runtime_ids):
        raise InvalidInput("current_structure_state contains an unknown runtime result")
    runtime_map: dict[tuple[str, str], dict[str, Any]] = {}
    if isinstance(current_runtime_units, dict):
        runtime_map = current_runtime_units
    elif isinstance(current_runtime_units, list):
        runtime_map = {(row.get("skill"), row.get("runtime_unit_key")): row for row in current_runtime_units if isinstance(row, dict)}
    for identity, result in result_blocks:
        runtime_id = tuple(identity.split("::", 1))
        current = runtime_map.get(runtime_id)
        if current is None:
            raise InvalidInput("current_structure_state runtime result has no current rerun counterpart")
        if current.get("generation_fingerprint") != result.get("generation_fingerprint"):
            raise InvalidInput("current_structure_state runtime result is stale")
        if runtime_result_projection_mismatch(_runtime_unit_result_row(result), current):
            raise InvalidInput("current_structure_state runtime result differs from the current rerun")
    return {
        "runtime_results": canonicalize(raw_results),
        "carry_forward_entities": carry,
        "previous_ci_id_state": [
            {"ci_id": ci_id, "status": status}
            for ci_id, status in sorted(previous_ci_state.items())
        ] if skill == "test-condition-design" else [],
    }


def _current_structure_state_projection(
    skill: str,
    result_blocks: Iterable[tuple[str, dict[str, Any]]],
    carry_forward_entities: list[dict[str, Any]],
    previous_states: dict[str, dict[str, str]],
) -> dict[str, Any]:
    """Expose only fixed runtime results and strictly validated prior entity rows."""
    runtime_results = []
    for identity, result in sorted(result_blocks, key=lambda row: row[0]):
        if identity.startswith(skill + "::"):
            runtime_results.append({"identity": identity, "result": canonicalize(result)})
    return {
        "runtime_results": runtime_results,
        "carry_forward_entities": canonicalize(carry_forward_entities),
        "previous_ci_id_state": [
            {"ci_id": ci_id, "status": status}
            for ci_id, status in sorted(previous_states.get("ci", {}).items())
        ] if skill == "test-condition-design" else [],
    }


def _expected_entities(
    skill: str,
    normalized: dict[str, Any],
    previous_entities: list[dict[str, Any]] | None = None,
    *,
    current_result_entities: list[dict[str, Any]] | None = None,
    previous_states: dict[str, dict[str, str]] | None = None,
    current_structure_state: dict[str, Any] | None = None,
    require_carry_forward_projection: bool = False,
) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    def add(entity_type: str, ref: Any) -> None:
        if isinstance(entity_type, str) and isinstance(ref, str):
            result.append({"skill": skill, "entity_type": entity_type, "entity_ref": ref})
    if skill == "spec-analysis":
        for row in normalized.get("authorities", []):
            add("authority", row.get("authority_id") if isinstance(row, dict) else None)
    elif skill == "test-analysis":
        result.append({"skill": skill, "entity_type": "test_analysis_context", "entity_ref": "analysis-context:all"})
        for row in normalized.get("product_risks", []):
            add("product_risk", row.get("risk_id") if isinstance(row, dict) else None)
        for row in normalized.get("technique_selections", []):
            add("technique_selection", row.get("selection_key") if isinstance(row, dict) else None)
        for row in normalized.get("change_nodes", []):
            add("change_node", row.get("node_key") if isinstance(row, dict) else None)
        for row in normalized.get("change_edges", []):
            add("change_edge", row.get("edge_key") if isinstance(row, dict) else None)
        for row in normalized.get("environment_requirements", []):
            add("environment_requirement", row.get("requirement_key") if isinstance(row, dict) else None)
    elif skill == "test-requirement-design":
        for row in normalized.get("test_requirements", []):
            value = (row.get("tr_id") or row.get("reuse_id")) if isinstance(row, dict) else None
            add("tr", value)
        for row in normalized.get("dispositions", []):
            if isinstance(row, dict) and isinstance(row.get("upstream_entity"), dict):
                upstream = row["upstream_entity"]
                if isinstance(upstream.get("entity_type"), str) and isinstance(upstream.get("entity_ref"), str):
                    add("disposition", f"{upstream['entity_type']}:{upstream['entity_ref']}")
    elif skill == "test-condition-design":
        for row in normalized.get("test_conditions", normalized.get("tcns", [])):
            value = (row.get("tcn_id") or row.get("reuse_id")) if isinstance(row, dict) else None
            add("tcn", value)
        model_rows = normalized.get("models", normalized.get("active_model_metadata", []))
        if not isinstance(model_rows, list) or not model_rows:
            model_rows = normalized.get("active_model_metadata", [])
        for row in model_rows:
            add("model", row.get("model_key") if isinstance(row, dict) else None)
        for ref in normalized.get("ci_ids", []):
            add("ci", ref)
        materialize = normalized.get("materialize_coverage")
        if isinstance(materialize, dict):
            for row in materialize.get("ci_id_state", []):
                if isinstance(row, dict) and row.get("status") == "active":
                    add("ci", row.get("ci_id"))
        for row in normalized.get("requirement_dispositions", []):
            if isinstance(row, dict) and isinstance(row.get("upstream_entity"), dict):
                upstream = row["upstream_entity"]
                if isinstance(upstream.get("entity_type"), str) and isinstance(upstream.get("entity_ref"), str):
                    add("disposition", f"{upstream['entity_type']}:{upstream['entity_ref']}")
        for row in normalized.get("test_data_requirements", normalized.get("normalized_requirements", [])):
            if isinstance(row, dict):
                add("test_data_requirement", row.get("data_ref") or (f"data:{row.get('requirement_key')}" if isinstance(row.get("requirement_key"), str) else None))
    elif skill == "test-case-design":
        for row in normalized.get("test_cases", []):
            value = (row.get("tc_id") or row.get("reuse_id")) if isinstance(row, dict) else None
            add("tc", value)
    for row in normalized.get("upstream_entities", []):
        if isinstance(row, dict) and isinstance(row.get("skill"), str) and isinstance(row.get("entity_type"), str):
            upstream_ref = row.get("entity_ref")
            if isinstance(upstream_ref, str):
                result.append({"skill": row["skill"], "entity_type": row["entity_type"], "entity_ref": upstream_ref})
    for entity in current_result_entities or []:
        if isinstance(entity, dict):
            add(entity.get("entity_type"), entity.get("entity_ref"))
    state = previous_states if previous_states is not None else _previous_entity_states(skill, normalized)
    if isinstance(current_structure_state, dict) and skill == "test-condition-design":
        state = {**state, "ci": _state_map(current_structure_state.get("previous_ci_id_state"), "ci_id")}
    if previous_entities is None:
        for _skill, entity_type, ref in _active_previous_entity_identities(skill, normalized, state):
            result.append({"skill": _skill, "entity_type": entity_type, "entity_ref": ref})
    state_results = _state_result_blocks(current_structure_state, skill)
    state_entities = _runtime_result_entities([(identity, body) for identity, body in state_results.items()], skill)
    for entity in state_entities:
        result.append({"skill": entity["skill"], "entity_type": entity["entity_type"], "entity_ref": entity["entity_ref"]})
    carry_projection_present = isinstance(current_structure_state, dict) and "carry_forward_entities" in current_structure_state
    carry_projection = validate_entity_collection(current_structure_state["carry_forward_entities"], expected_skill=skill) if carry_projection_present else []
    if require_carry_forward_projection:
        required_carry = _active_previous_entity_identities(skill, normalized, state)
        if required_carry and not carry_projection_present:
            raise InvalidInput("scope-out Machine Entity fixed projection is missing")
        available = {
            entity_identity(row["skill"], row["entity_type"], row["entity_ref"])
            for row in [*state_entities, *carry_projection]
        }
        if not required_carry.issubset(available):
            raise InvalidInput("scope-out active ID is missing from the fixed Machine Entity projection")
    for entity in carry_projection:
        result.append({"skill": entity["skill"], "entity_type": entity["entity_type"], "entity_ref": entity["entity_ref"]})
    for row in _carry_forward_machine_entities(skill, normalized, previous_entities or [], state):
        result.append({"skill": skill, "entity_type": row["entity_type"], "entity_ref": row["entity_ref"]})
    unique: dict[tuple[str, str, str], dict[str, str]] = {}
    for row in result:
        key = (row["skill"], row["entity_type"], row["entity_ref"])
        unique[key] = row
    return [unique[key] for key in sorted(unique)]


def _validate_runtime_pair(
    skill: str,
    identity: str,
    input_body: dict[str, Any],
    result: dict[str, Any],
    *,
    normalized: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    if "::" not in identity:
        return [{"issue_type": "invalid_runtime_identity", "blocking": True, "runtime_unit": identity}]
    identity_skill, runtime_unit_key = identity.split("::", 1)
    if identity_skill != skill:
        issues.append({"issue_type": "invalid_runtime_identity", "blocking": True, "runtime_unit": identity})
    if set(input_body) != {"metadata", "input"} or not isinstance(input_body.get("metadata"), dict) or not isinstance(input_body.get("input"), dict):
        issues.append({"issue_type": "invalid_runtime_input_block", "blocking": True, "runtime_unit": identity})
        return issues
    try:
        metadata = _validate_metadata(input_body["metadata"], skill=skill)
    except RuntimeErrorBase as exc:
        issues.append({"issue_type": exc.issue_type, "blocking": True, "runtime_unit": identity, "message": exc.message})
        return issues
    if metadata["runtime_unit_key"] != runtime_unit_key:
        issues.append({"issue_type": "invalid_runtime_identity", "blocking": True, "runtime_unit": identity})
    if normalized is not None:
        models = _normalized_models(normalized)
        if runtime_unit_key.startswith("model:"):
            model_key = runtime_unit_key.split(":", 1)[1]
            model = models.get(model_key)
            if model is None:
                issues.append({"issue_type": "invalid_dispatch_input", "blocking": True, "runtime_unit": identity})
            else:
                for field in ("model_type", "technique_slug", "selection_source", "selection_key"):
                    if field in model and metadata.get(field) != model.get(field):
                        issues.append({"issue_type": "invalid_dispatch_input", "blocking": True, "runtime_unit": identity, "field": field})
        elif runtime_unit_key.startswith("artifact:materialize_coverage:"):
            tcn_id = normalized.get("tcn_id")
            if not isinstance(tcn_id, str) or runtime_unit_key != f"artifact:materialize_coverage:{tcn_id}":
                issues.append({"issue_type": "invalid_dispatch_input", "blocking": True, "runtime_unit": identity})
        elif skill == "test-analysis" and runtime_unit_key.startswith("artifact:technique_candidates:"):
            selection_key = runtime_unit_key.split("artifact:technique_candidates:", 1)[1]
            selection_keys = {row.get("selection_key") for row in normalized.get("technique_selections", []) if isinstance(row, dict)}
            if selection_key not in selection_keys:
                issues.append({"issue_type": "invalid_dispatch_input", "blocking": True, "runtime_unit": identity})
    expected_keys = {
        "envelope_version", "skill", "runtime_contract_version", "generator_contract_version", "generator", "runtime_unit_key", "model_key",
        "input_fingerprint", "model_fingerprint", "generation_fingerprint", "runtime_implementation_fingerprint", "generator_implementation_fingerprint",
        "upstream_entity_fingerprints", "upstream_runtime_units", "support_status", "static_data_versions", "runtime_status", "result_status",
        "runtime_required", "deterministic_generated", "fallback_reason", "payload", "issues",
    }
    if set(result) != expected_keys:
        issues.append({"issue_type": "invalid_runtime_result_block", "blocking": True, "runtime_unit": identity})
        return issues
    if result.get("skill") != skill or result.get("runtime_unit_key") != runtime_unit_key or result.get("model_key") != metadata.get("model_key"):
        issues.append({"issue_type": "runtime_result_identity_mismatch", "blocking": True, "runtime_unit": identity})
    if result.get("envelope_version") != ENVELOPE_VERSION or result.get("runtime_contract_version") != RUNTIME_CONTRACT_VERSION:
        issues.append({"issue_type": "runtime_result_version_mismatch", "blocking": True, "runtime_unit": identity})
    if result.get("generator_contract_version") != metadata.get("generator_contract_version"):
        issues.append({"issue_type": "runtime_result_generator_version_mismatch", "blocking": True, "runtime_unit": identity})
    if result.get("support_status") not in SUPPORTED_SUPPORT_STATUSES or result.get("runtime_status") not in SUPPORTED_STATUSES or result.get("result_status") not in SUPPORTED_RESULT_STATUSES:
        issues.append({"issue_type": "invalid_runtime_status", "blocking": True, "runtime_unit": identity})
    if not isinstance(result.get("payload"), dict) or not isinstance(result.get("issues"), list):
        issues.append({"issue_type": "invalid_runtime_payload", "blocking": True, "runtime_unit": identity})
        return issues
    if result.get("result_status") == "ready" and any(isinstance(issue, dict) and issue.get("blocking") is True for issue in result["issues"]):
        issues.append({"issue_type": "ready_runtime_has_blocking_issue", "blocking": True, "runtime_unit": identity})
    if result.get("runtime_implementation_fingerprint") != implementation_fingerprint(Path(__file__)):
        issues.append({"issue_type": "stale_runtime_implementation", "blocking": True, "runtime_unit": identity})
    if not isinstance(result.get("generator"), str) or not result["generator"]:
        issues.append({"issue_type": "invalid_generator", "blocking": True, "runtime_unit": identity})
    else:
        generator_path = Path(__file__).parent / f"{result['generator']}.py"
        if generator_path.is_file() and result.get("generator_implementation_fingerprint") != implementation_fingerprint(generator_path):
            issues.append({"issue_type": "stale_generator_implementation", "blocking": True, "runtime_unit": identity})
    if not FULL_DIGEST_RE.fullmatch(str(result.get("runtime_implementation_fingerprint"))) or not FULL_DIGEST_RE.fullmatch(str(result.get("generator_implementation_fingerprint"))):
        issues.append({"issue_type": "invalid_implementation_fingerprint", "blocking": True, "runtime_unit": identity})
    if not isinstance(result.get("upstream_entity_fingerprints"), list) or not isinstance(result.get("upstream_runtime_units"), list):
        issues.append({"issue_type": "invalid_dependency_projection", "blocking": True, "runtime_unit": identity})
    if not isinstance(result.get("runtime_required"), bool) or not isinstance(result.get("deterministic_generated"), bool):
        issues.append({"issue_type": "invalid_runtime_flags", "blocking": True, "runtime_unit": identity})
    status = result.get("runtime_status")
    status_rules = {
        "unsupported": ("unsupported", False, False, "ready", "outside_supported_subset"),
        "not_run": ("unknown", True, False, "blocked", "python_unavailable"),
    }
    if status in status_rules:
        expected_support, expected_required, expected_deterministic, expected_result, expected_fallback = status_rules[status]
        if (result.get("support_status"), result.get("runtime_required"), result.get("deterministic_generated"), result.get("result_status"), result.get("fallback_reason")) != (expected_support, expected_required, expected_deterministic, expected_result, expected_fallback):
            issues.append({"issue_type": "invalid_status_projection", "blocking": True, "runtime_unit": identity})
    elif status in {"invalid_input", "limit_exceeded", "internal_error"}:
        if result.get("runtime_required") is not True or result.get("deterministic_generated") is not False or result.get("result_status") != "blocked":
            issues.append({"issue_type": "invalid_error_projection", "blocking": True, "runtime_unit": identity})
    try:
        expected_input_fp = input_fingerprint(skill, metadata["runtime_unit_key"], metadata["input_mode"], canonicalize(input_body["input"]), metadata["authority_refs"], metadata["reference_refs"], metadata["selection_source"])
        expected_model_fp = model_fingerprint(metadata, expected_input_fp)
        upstream = upstream_entity_fingerprints(validate_upstream_entities(metadata))
        result_static_versions = result.get("static_data_versions")
        if not isinstance(result_static_versions, dict):
            raise InvalidInput("runtime result static_data_versionsが不正です")
        expected_generation_fp = generation_fingerprint(
            generator=result["generator"], input_fp=expected_input_fp, model_fp=expected_model_fp,
            runtime_contract_version=RUNTIME_CONTRACT_VERSION, generator_contract_version=metadata["generator_contract_version"],
            runtime_impl_fp=result["runtime_implementation_fingerprint"], generator_impl_fp=result["generator_implementation_fingerprint"],
            upstream=upstream, static_data_versions=result_static_versions,
        )
        if result["input_fingerprint"] != expected_input_fp:
            issues.append({"issue_type": "input_fingerprint_mismatch", "blocking": True, "runtime_unit": identity})
        if result["model_fingerprint"] != expected_model_fp:
            issues.append({"issue_type": "model_fingerprint_mismatch", "blocking": True, "runtime_unit": identity})
        if result["upstream_entity_fingerprints"] != upstream:
            issues.append({"issue_type": "upstream_entity_fingerprint_mismatch", "blocking": True, "runtime_unit": identity})
        if result["upstream_runtime_units"] != canonicalize(metadata["upstream_runtime_units"], parent_key="upstream_runtime_units"):
            issues.append({"issue_type": "upstream_runtime_unit_mismatch", "blocking": True, "runtime_unit": identity})
        if result["generation_fingerprint"] != expected_generation_fp:
            issues.append({"issue_type": "generation_fingerprint_mismatch", "blocking": True, "runtime_unit": identity})
    except RuntimeErrorBase as exc:
        issues.append({"issue_type": exc.issue_type, "blocking": True, "runtime_unit": identity, "message": exc.message})
    return issues


def verify_runtime_evidence(request: dict[str, Any]) -> dict[str, Any]:
    reject_unknown(request, {"operation", "skill", "normalized_skill_input", "artifact_markdown", "previous_artifact_markdown", "partial_rerun"})
    if request.get("operation") != "verify_runtime_evidence":
        raise InvalidInput("operationが不正です")
    skill = ensure_nonempty_string(request.get("skill"), "skill")
    normalized = ensure_object(request.get("normalized_skill_input"), "normalized_skill_input")
    artifact = request.get("artifact_markdown")
    if not isinstance(artifact, str):
        raise InvalidInput("artifact_markdownはstringである必要があります")
    previous = request.get("previous_artifact_markdown")
    if previous is not None and not isinstance(previous, str):
        raise InvalidInput("previous_artifact_markdownはstringまたはnullである必要があります")
    partial_rerun = request.get("partial_rerun")
    if not isinstance(partial_rerun, bool):
        raise InvalidInput("partial_rerunはbooleanである必要があります")
    input_blocks = extract_machine_blocks(artifact, "Machine Runtime Input", allow_duplicates=True)
    result_blocks = extract_machine_blocks(artifact, "Machine Runtime Result", allow_duplicates=True)
    input_map = {identity: body for identity, body in input_blocks}
    result_map = {identity: body for identity, body in result_blocks}
    actual_ids = sorted(set(input_map) | set(result_map))
    incomplete = sorted(set(input_map) ^ set(result_map))
    issues: list[dict[str, Any]] = []
    carry_forward_skills = {"test-requirement-design", "test-condition-design", "test-case-design"}
    no_carry_forward_skills = {"test-analysis", "coverage-analysis", "qa-workflow"}
    if skill in no_carry_forward_skills and (partial_rerun or previous is not None):
        issues.append({
            "issue_type": "invalid_previous_artifact",
            "blocking": True,
            "message": f"{skill} requires partial_rerun=false and previous_artifact_markdown=null in runtime-v1",
        })
    elif skill in carry_forward_skills and partial_rerun != (previous is not None):
        issues.append({
            "issue_type": "invalid_previous_artifact",
            "blocking": True,
            "message": "partial rerun requires the full previous artifact; full build requires previous_artifact_markdown=null",
        })
    elif skill not in carry_forward_skills | no_carry_forward_skills and (partial_rerun or previous is not None):
        issues.append({
            "issue_type": "invalid_previous_artifact",
            "blocking": True,
            "message": f"{skill} does not support previous artifact carry-forward in runtime-v1",
        })
    graph_rows = []
    for identity, body in input_blocks:
        metadata = body.get("metadata") if isinstance(body, dict) else None
        if isinstance(metadata, dict) and isinstance(metadata.get("skill"), str) and isinstance(metadata.get("runtime_unit_key"), str):
            graph_rows.append({"skill": metadata["skill"], "runtime_unit_key": metadata["runtime_unit_key"], "upstream_runtime_units": metadata.get("upstream_runtime_units", [])})
    try:
        validate_runtime_dependency_graph(graph_rows)
    except RuntimeErrorBase as exc:
        issues.append({"issue_type": exc.issue_type, "blocking": True, "message": exc.message})
    expected = _default_expected_runtime_units(skill, normalized, artifact)
    _verified_child_units(skill, normalized, result_map, expected, input_blocks=input_map, issues=issues)
    expected_keys = sorted(_unit_identity(row["skill"], row["runtime_unit_key"]) for row in expected)
    actual_keys = sorted(actual_ids)
    missing = sorted(set(expected_keys) - set(actual_keys))
    extra = sorted(set(actual_keys) - set(expected_keys))
    input_ids = [identity for identity, _ in input_blocks]
    result_ids = [identity for identity, _ in result_blocks]
    duplicates = sorted({identity for identity in input_ids if input_ids.count(identity) > 1} | {identity for identity in result_ids if result_ids.count(identity) > 1})
    for identity in sorted(set(input_map) & set(result_map)):
        issues.extend(_validate_runtime_pair(skill, identity, input_map[identity], result_map[identity], normalized=normalized))
        expected_generator = _expected_generator(skill, identity.split("::", 1)[1], normalized)
        if expected_generator is not None and result_map[identity].get("generator") != expected_generator:
            issues.append({"issue_type": "generator_mismatch", "blocking": True, "runtime_unit": identity})
    if missing:
        issues.append({"issue_type": "missing_runtime_unit", "blocking": True, "runtime_units": missing})
    if extra:
        issues.append({"issue_type": "extra_runtime_unit", "blocking": True, "runtime_units": extra})
    if incomplete:
        issues.append({"issue_type": "incomplete_runtime_pair", "blocking": True, "runtime_units": incomplete})
        input_only = sorted(set(input_ids) - set(result_ids))
        result_only = sorted(set(result_ids) - set(input_ids))
        if input_only:
            issues.append({"issue_type": "input_only_runtime_unit", "blocking": True, "runtime_units": input_only})
        if result_only:
            issues.append({"issue_type": "result_only_runtime_unit", "blocking": True, "runtime_units": result_only})
    if duplicates:
        issues.append({"issue_type": "duplicate_runtime_unit", "blocking": True, "runtime_units": sorted(set(duplicates))})
    actual_entities: list[dict[str, Any]] = []
    duplicate_entities: list[tuple[str, str, str]] = []
    entity_blocks = extract_machine_blocks(artifact, "Machine Entities", allow_duplicates=True)
    entity_block_ids = [identity for identity, _ in entity_blocks if identity == skill]
    if len(entity_block_ids) > 1:
        issues.append({"issue_type": "duplicate_machine_entities_block", "blocking": True, "skill": skill})
    candidate_entity_rows: dict[tuple[str, str, str], dict[str, Any]] = {}
    for identity, body in [block for block in entity_blocks if block[0] == skill][:1]:
        if identity != skill:
            continue
        if set(body) != {"schema_version", "skill", "entities"}:
            issues.append({"issue_type": "invalid_machine_entities", "blocking": True})
            continue
        try:
            rows = body["entities"]
            if not isinstance(rows, list):
                raise InvalidInput("Machine Entity entitiesはarrayである必要があります")
            row_identities = []
            for row in rows:
                if isinstance(row, dict) and all(isinstance(row.get(field), str) for field in ("skill", "entity_type", "entity_ref")):
                    row_identities.append((row["skill"], row["entity_type"], row["entity_ref"]))
            duplicate_entities.extend(sorted({key for key in row_identities if row_identities.count(key) > 1}))
            actual_entities = validate_entity_collection(rows, expected_skill=skill)
            candidate_entity_rows.update({
                entity_identity(row["skill"], row["entity_type"], row["entity_ref"]): row
                for row in actual_entities
            })
        except RuntimeErrorBase as exc:
            issues.append({"issue_type": exc.issue_type, "blocking": True, "message": exc.message})
    try:
        candidate_blocks = _artifact_machine_entity_map(artifact)
        for upstream in normalized.get("upstream_entities", []):
            if not isinstance(upstream, dict):
                continue
            key = entity_identity(upstream.get("skill"), upstream.get("entity_type"), upstream.get("entity_ref"))
            row = next((candidate for candidate in candidate_blocks.get(key[0], []) if entity_identity(candidate["skill"], candidate["entity_type"], candidate["entity_ref"]) == key), None)
            if row is not None:
                candidate_entity_rows[key] = row
        actual_entities = [candidate_entity_rows[key] for key in sorted(candidate_entity_rows)]
    except RuntimeErrorBase as exc:
        issues.append({"issue_type": "invalid_machine_entities", "blocking": True, "message": exc.message})
    previous_entities: list[dict[str, Any]] = []
    previous_states: dict[str, dict[str, str]] = {}
    previous_result_blocks: list[tuple[str, dict[str, Any]]] = []
    previous_valid = False
    if previous is not None and skill in no_carry_forward_skills:
        previous_valid = False
    elif previous is not None and skill in carry_forward_skills and partial_rerun:
        try:
            previous_entity_map = _artifact_machine_entity_map(previous)
            if skill not in previous_entity_map:
                raise InvalidInput("previous artifact has no Machine Entities block for this Skill")
            previous_entities = [entity for rows in previous_entity_map.values() for entity in rows]
            previous_result_blocks = extract_machine_blocks(previous, "Machine Runtime Result", allow_duplicates=True)
            previous_input_blocks = extract_machine_blocks(previous, "Machine Runtime Input", allow_duplicates=True)
            previous_result_ids = [identity for identity, _ in previous_result_blocks]
            previous_input_ids = [identity for identity, _ in previous_input_blocks]
            if len(previous_result_ids) != len(set(previous_result_ids)) or len(previous_input_ids) != len(set(previous_input_ids)) or set(previous_result_ids) != set(previous_input_ids):
                raise InvalidInput("previous runtime input/result pairs are incomplete or duplicated")
            previous_inputs = dict(previous_input_blocks)
            for old_identity, old_result in previous_result_blocks:
                old_skill = old_identity.split("::", 1)[0]
                if old_skill != skill:
                    continue
                old_pair_issues = _validate_runtime_pair(skill, old_identity, previous_inputs[old_identity], old_result)
                if old_pair_issues:
                    raise InvalidInput("previous runtime evidence is not current under this runtime contract")
            previous_states = _previous_entity_states(skill, normalized, previous_result_blocks)
            tracked_types = set(previous_states)
            state_keys = {key for _, row in previous_result_blocks if _.startswith(skill + "::") for key in (row.get("payload", {}) if isinstance(row.get("payload"), dict) else {})}
            required_state_fields = {
                "tr": "tr_id_state", "tcn": "tcn_id_state", "model": "model_key_state", "tc": "tc_id_state", "ci": "ci_id_state",
            }
            for entity_type in tracked_types:
                if any(row["skill"] == skill and row["entity_type"] == entity_type for row in previous_entities) and required_state_fields[entity_type] not in state_keys:
                    raise InvalidInput("previous full ID state is missing")
            _validate_previous_entity_state(skill, previous_entities, previous_states)
            normalized_states = _previous_entity_states(skill, normalized)
            normalized_state_fields = {
                "tr": "previous_tr_ids", "tcn": "previous_tcn_ids", "model": "previous_model_keys",
                "tc": "previous_tc_ids", "ci": "previous_ci_ids",
            }
            for entity_type, state in previous_states.items():
                field = normalized_state_fields[entity_type]
                if field not in normalized:
                    raise InvalidInput("normalized previous ID state does not match previous artifact")
                if entity_type == "ci":
                    tcn_id = normalized.get("tcn_id")
                    if not isinstance(tcn_id, str):
                        raise InvalidInput("normalized previous_ci_ids require the current tcn_id")
                    current_ci_state = normalized_states.get(entity_type, {})
                    if any(not re.fullmatch(re.escape(tcn_id) + r"-CI[0-9]{2,}", ci_id) for ci_id in current_ci_state):
                        raise InvalidInput("normalized previous_ci_ids contain another TCN")
                    previous_ci_subset = {ci_id: status for ci_id, status in state.items() if ci_id.startswith(tcn_id + "-")}
                    if current_ci_state != previous_ci_subset:
                        raise InvalidInput("normalized previous_ci_ids do not match the current TCN state")
                elif normalized_states.get(entity_type, {}) != state:
                    raise InvalidInput("normalized previous ID state does not match previous artifact")
            previous_result_entities = _runtime_result_entities(previous_result_blocks, skill)
            previous_entity_by_key = {
                entity_identity(row["skill"], row["entity_type"], row["entity_ref"]): row
                for row in previous_entity_map[skill]
            }
            for row in previous_result_entities:
                key = entity_identity(row["skill"], row["entity_type"], row["entity_ref"])
                if key not in previous_entity_by_key or canonical_json_text(previous_entity_by_key[key]) != canonical_json_text(row):
                    raise InvalidInput("previous runtime result entity does not match Machine Entities")
            previous_valid = True
        except RuntimeErrorBase as exc:
            previous_entities = []
            try:
                previous_states = _previous_entity_states(skill, normalized)
            except RuntimeErrorBase:
                previous_states = {}
            issues.append({"issue_type": "invalid_previous_artifact", "blocking": True, "message": exc.message})
        except (KeyError, TypeError, ValueError) as exc:
            previous_entities = []
            try:
                previous_states = _previous_entity_states(skill, normalized)
            except RuntimeErrorBase:
                previous_states = {}
            issues.append({"issue_type": "invalid_previous_artifact", "blocking": True, "message": f"previous state could not be validated: {type(exc).__name__}"})
    else:
        try:
            previous_states = _previous_entity_states(skill, normalized)
            if skill in carry_forward_skills and partial_rerun:
                issues.append({
                    "issue_type": "invalid_previous_artifact",
                    "blocking": True,
                    "message": "partial rerun requires the complete previous artifact, including when only a Disposition is out of scope",
                })
            elif skill in carry_forward_skills and _previous_artifact_required_for_carry_forward(skill, normalized):
                issues.append({
                    "issue_type": "invalid_previous_artifact",
                    "blocking": True,
                    "message": "scope-out active Machine Entities require the previous artifact全文",
                })
        except RuntimeErrorBase as exc:
            issues.append({"issue_type": exc.issue_type, "blocking": True, "message": exc.message})
    try:
        current_result_entities = _runtime_result_entities(result_blocks, skill)
    except RuntimeErrorBase as exc:
        current_result_entities = []
        issues.append({"issue_type": "invalid_current_runtime_entities", "blocking": True, "message": exc.message})
    expected_entity_rows = _expected_entities(
        skill,
        normalized,
        previous_entities if previous_valid else None,
        current_result_entities=current_result_entities,
        previous_states=previous_states,
    )
    expected_entity_keys = sorted((row["skill"], row["entity_type"], row["entity_ref"]) for row in expected_entity_rows)
    actual_entity_keys = sorted((row["skill"], row["entity_type"], row["entity_ref"]) for row in actual_entities)
    missing_entities = sorted(set(expected_entity_keys) - set(actual_entity_keys))
    extra_entities = sorted(set(actual_entity_keys) - set(expected_entity_keys))
    if missing_entities:
        issues.append({"issue_type": "missing_entity", "blocking": True, "entities": [list(row) for row in missing_entities]})
    if extra_entities:
        issues.append({"issue_type": "extra_entity", "blocking": True, "entities": [list(row) for row in extra_entities]})
    if duplicate_entities:
        issues.append({"issue_type": "duplicate_entity", "blocking": True, "entities": [list(row) for row in sorted(set(duplicate_entities))]})
    candidate_entity_map: dict[tuple[str, str, str], dict[str, Any]] = {}
    try:
        candidate_entity_map = {
            entity_identity(row["skill"], row["entity_type"], row["entity_ref"]): row
            for rows in _artifact_machine_entity_map(artifact).values()
            for row in rows
        }
    except RuntimeErrorBase as exc:
        issues.append({"issue_type": "invalid_machine_entities", "blocking": True, "message": exc.message})
    current_result_map = {
        entity_identity(row["skill"], row["entity_type"], row["entity_ref"]): row
        for row in current_result_entities
    }
    for key, expected_entity in current_result_map.items():
        actual_entity = candidate_entity_map.get(key)
        if actual_entity is not None and canonical_json_text(actual_entity) != canonical_json_text(expected_entity):
            issues.append({"issue_type": "current_entity_result_mismatch", "blocking": True, "entity": list(key)})
    carry_rows = _carry_forward_machine_entities(skill, normalized, previous_entities, previous_states) if previous_valid and previous_entities else []
    for row in carry_rows:
        key = entity_identity(row["skill"], row["entity_type"], row["entity_ref"])
        actual = candidate_entity_map.get(key)
        if actual is not None and canonical_json_text(actual) != canonical_json_text(row):
            issues.append({"issue_type": "carry_forward_entity_changed", "blocking": True, "entity": list(key)})
    if carry_rows and candidate_entity_map:
        try:
            runtime_rows: list[dict[str, Any]] = []
            for result_identity, body in result_blocks:
                if "::" not in result_identity:
                    continue
                runtime_rows.append(_runtime_unit_result_row(body))
            fresh_runtime_rows, _runtime_issues = evaluate_runtime_unit_freshness(
                runtime_rows, runtime_rows, list(candidate_entity_map.values()),
            )
            current_runtime_rows = {
                (row["skill"], row["runtime_unit_key"]): row
                for row in fresh_runtime_rows
            }
            freshness = evaluate_entity_freshness(list(candidate_entity_map.values()), current_runtime_rows)
            freshness_by_key = {
                (row["skill"], row["entity_type"], row["entity_ref"]): row
                for row in freshness
            }
            for row in carry_rows:
                key = entity_identity(row["skill"], row["entity_type"], row["entity_ref"])
                status = freshness_by_key.get(key, {}).get("freshness_status")
                if status != "current":
                    issues.append({"issue_type": "stale_carry_forward_entity", "blocking": True, "entity": list(key), "stale_reasons": freshness_by_key.get(key, {}).get("stale_reasons", [])})
        except RuntimeErrorBase as exc:
            issues.append({"issue_type": exc.issue_type, "blocking": True, "message": exc.message})
    current_structure_state = _current_structure_state_projection(skill, result_blocks, carry_rows, previous_states)
    if skill in {"test-analysis", "test-requirement-design", "test-condition-design", "test-case-design", "coverage-analysis", "qa-workflow"}:
        try:
            current_runtime_rows = [_runtime_unit_result_row(body) for identity, body in result_blocks if identity.startswith(skill + "::")]
            validate_current_structure_state(
                skill,
                normalized,
                current_structure_state,
                current_entities=list(candidate_entity_map.values()),
                current_runtime_units=current_runtime_rows,
            )
        except RuntimeErrorBase as exc:
            issues.append({"issue_type": "invalid_current_structure_state", "blocking": True, "message": exc.message})
    valid = not issues
    return {
        "valid": valid,
        "issues": issues,
        "expected_runtime_units": expected,
        "actual_runtime_units": actual_ids,
        "missing": missing,
        "extra": extra,
        "incomplete_pairs": incomplete,
        "duplicates": sorted(set(duplicates)),
        "expected_entities": expected_entity_rows,
        "actual_entities": actual_entities,
        "missing_entities": [list(row) for row in missing_entities],
        "extra_entities": [list(row) for row in extra_entities],
        "duplicate_entities": [list(row) for row in sorted(set(duplicate_entities))],
        "current_structure_state": current_structure_state if valid else None,
    }


def _validate_metadata(metadata: Any, *, skill: str) -> dict[str, Any]:
    if not isinstance(metadata, dict):
        raise InvalidInput("metadataはobjectである必要があります")
    required = {"envelope_version", "skill", "runtime_contract_version", "generator_contract_version", "runtime_unit_key", "model_key", "model_type", "technique_slug", "selection_source", "selection_key", "scope_key", "input_mode", "upstream_entities", "upstream_runtime_units", "static_data_versions", "authority_refs", "reference_refs"}
    if set(metadata) != required:
        missing = sorted(required - set(metadata))
        unknown = sorted(set(metadata) - required)
        raise InvalidInput(f"metadata schemaが不正です missing={missing} unknown={unknown}")
    if metadata["envelope_version"] != ENVELOPE_VERSION or metadata["runtime_contract_version"] != RUNTIME_CONTRACT_VERSION:
        raise InvalidInput("runtime contract versionが不一致です")
    if metadata["skill"] != skill:
        raise InvalidInput("metadata.skillがscript所属Skillと不一致です")
    if metadata["input_mode"] not in {"artifact", "direct"}:
        raise InvalidInput("input_modeが不正です")
    unit = ensure_nonempty_string(metadata["runtime_unit_key"], "runtime_unit_key")
    model_key = metadata["model_key"]
    if model_key is not None:
        if not re.fullmatch(r"[a-z][a-z0-9-]*-[0-9]{3,}", str(model_key)):
            raise InvalidInput("model_keyが不正です")
        if unit != "model:" + model_key:
            raise InvalidInput("model runtime unit keyがmodel_keyと不一致です")
        if metadata["scope_key"] is not None:
            raise InvalidInput("model scriptのscope_keyはnullです")
        model_type = metadata["model_type"]
        if model_type not in MODEL_TYPES or not str(model_key).startswith(model_type + "-"):
            raise InvalidInput("model_type / model_keyが不一致です")
        technique_slug = metadata["technique_slug"]
        if model_type in {"classification", "cause-effect", "schema", "ui"}:
            if technique_slug is not None or metadata["selection_source"] is not None or metadata["selection_key"] is not None:
                raise InvalidInput("adapter modelのtechnique selectionが不正です")
        elif model_type == "error-guessing":
            if technique_slug != "error-guessing":
                raise InvalidInput("error-guessing modelのtechnique_slugが不正です")
        elif technique_slug not in TECHNIQUE_SLUGS:
            raise InvalidInput("Coverage modelのtechnique_slugが不正です")
    else:
        if not re.fullmatch(r"artifact:[^:]+:[^:]+", unit):
            raise InvalidInput("artifact scriptのruntime_unit_keyが不正です")
        if any(metadata[field] is not None for field in ("model_type", "technique_slug", "selection_source", "selection_key")):
            raise InvalidInput("artifact scriptのmodel metadataが不正です")
    if metadata["selection_source"] not in {None, "analysis", "condition_design", "user"}:
        raise InvalidInput("selection_sourceが不正です")
    if metadata["selection_source"] == "analysis" and not isinstance(metadata["selection_key"], str):
        raise InvalidInput("analysis selectionにはselection_keyが必要です")
    if not isinstance(metadata["authority_refs"], list) or not all(isinstance(row, str) for row in metadata["authority_refs"]):
        raise InvalidInput("authority_refsが不正です")
    if not isinstance(metadata["reference_refs"], list) or not all(isinstance(row, str) for row in metadata["reference_refs"]):
        raise InvalidInput("reference_refsが不正です")
    static = metadata["static_data_versions"]
    if not isinstance(static, dict):
        raise InvalidInput("static_data_versionsが不正です")
    for key, value in static.items():
        if not re.fullmatch(r"[a-z][a-z0-9_]*", str(key)) or not isinstance(value, str):
            raise InvalidInput("static_data_versionsのkey/valueが不正です")
        if not (FULL_DIGEST_RE.fullmatch(value) or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", value)):
            raise InvalidInput("static_data_versionsのvalueが不正です")
    validate_upstream_entities(metadata)
    if not isinstance(metadata["upstream_runtime_units"], list):
        raise InvalidInput("upstream_runtime_unitsが不正です")
    upstream_runtime_keys: set[tuple[str, str]] = set()
    for row in metadata["upstream_runtime_units"]:
        if not isinstance(row, dict) or set(row) != {"skill", "runtime_unit_key", "generation_fingerprint"} or not FULL_DIGEST_RE.fullmatch(str(row["generation_fingerprint"])):
            raise InvalidInput("upstream_runtime_unitsのschemaが不正です")
        dependency_key = (row["skill"], row["runtime_unit_key"])
        if not all(isinstance(value, str) for value in dependency_key) or dependency_key in upstream_runtime_keys:
            raise InvalidInput("upstream_runtime_unitsが重複または不正です")
        if dependency_key == (skill, metadata["runtime_unit_key"]):
            raise InvalidInput("runtime unit自身をupstream_runtime_unitsへ指定できません")
        upstream_runtime_keys.add(dependency_key)
    return metadata


def _error_envelope(*, skill: str, generator: str, generator_contract_version: str, generator_path: str | Path, status: str, message: str, runtime_unit_key: str | None = None, model_key: str | None = None, runtime_required: bool = True, fallback_reason: str | None = None) -> dict[str, Any]:
    return {
        "envelope_version": ENVELOPE_VERSION,
        "skill": skill,
        "runtime_contract_version": RUNTIME_CONTRACT_VERSION,
        "generator_contract_version": generator_contract_version,
        "generator": generator,
        "runtime_unit_key": runtime_unit_key,
        "model_key": model_key,
        "input_fingerprint": None,
        "model_fingerprint": None,
        "generation_fingerprint": None,
        "runtime_implementation_fingerprint": implementation_fingerprint(Path(__file__)),
        "generator_implementation_fingerprint": implementation_fingerprint(generator_path),
        "upstream_entity_fingerprints": [],
        "upstream_runtime_units": [],
        "support_status": "unknown" if status in {"invalid_input", "internal_error", "not_run", "limit_exceeded"} else "unsupported",
        "static_data_versions": {},
        "runtime_status": status,
        "result_status": "blocked" if status not in {"unsupported"} else "ready",
        "runtime_required": runtime_required,
        "deterministic_generated": False,
        "fallback_reason": fallback_reason,
        "payload": {},
        "issues": [{"issue_type": status, "blocking": True, "message": message, "skill": skill, "runtime_unit_key": runtime_unit_key, "model_key": model_key, "target_key": None, "generation_fingerprint": None}],
    }


def _emit(value: dict[str, Any]) -> None:
    raw = canonical_json_bytes(value)
    if len(raw) > MAX_STDOUT_BYTES:
        value = _error_envelope(skill=str(value.get("skill", "unknown")), generator=str(value.get("generator", "unknown")), generator_contract_version=str(value.get("generator_contract_version", "unknown")), generator_path=__file__, status="limit_exceeded", message="stdout JSONのbyte上限を超えました")
        raw = canonical_json_bytes(value)
    sys.stdout.buffer.write(raw + b"\n")


def run_cli(
    handler: Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]],
    *,
    skill: str,
    generator: str,
    generator_contract_version: str,
    generator_path: str | Path,
    aggregate: bool = False,
) -> int:
    # Read up to the aggregate hard limit first so the standalone verifier can
    # use 16 MiB even when it is invoked through a Skill-local CLI. Ordinary
    # generator requests are rejected at the 2 MiB boundary after decoding.
    raw = sys.stdin.buffer.read(MAX_AGGREGATE_INPUT_BYTES + 1)
    try:
        request = strict_loads(raw, aggregate=True)
        if not aggregate and not (isinstance(request, dict) and request.get("operation") == "verify_runtime_evidence") and len(raw) > MAX_NORMAL_INPUT_BYTES:
            raise LimitExceeded("通常runtime stdinのbyte上限を超えました")
    except RuntimeErrorBase as exc:
        _emit(_error_envelope(skill=skill, generator=generator, generator_contract_version=generator_contract_version, generator_path=generator_path, status=exc.issue_type if exc.issue_type in SUPPORTED_STATUSES else "invalid_input", message=exc.message))
        return 0 if exc.issue_type in {"invalid_input", "limit_exceeded", "unsupported"} else 1
    if not isinstance(request, dict):
        _emit(_error_envelope(skill=skill, generator=generator, generator_contract_version=generator_contract_version, generator_path=generator_path, status="invalid_input", message="top-level JSONはobjectである必要があります"))
        return 0
    if request.get("operation") == "verify_runtime_evidence":
        try:
            _emit(verify_runtime_evidence(request))
            return 0
        except RuntimeErrorBase as exc:
            _emit({"valid": False, "issues": [{"issue_type": exc.issue_type, "blocking": True, "message": exc.message}], "expected_runtime_units": [], "actual_runtime_units": [], "missing": [], "extra": [], "incomplete_pairs": [], "duplicates": [], "expected_entities": [], "actual_entities": [], "missing_entities": [], "extra_entities": [], "duplicate_entities": []})
            return 0
    # These values are populated only after the request has crossed the
    # metadata/input boundary.  Handler failures can therefore still emit a
    # pairable envelope with the verified runtime identity and fingerprints;
    # malformed pre-boundary requests continue to use the anonymous error
    # envelope above.
    metadata: dict[str, Any] | None = None
    canonical_input: dict[str, Any] | None = None
    upstream_fps: list[dict[str, str]] = []
    input_fp: str | None = None
    model_fp: str | None = None
    runtime_fp: str | None = None
    generator_fp: str | None = None
    try:
        reject_unknown(request, {"metadata", "input"})
        metadata = _validate_metadata(request.get("metadata"), skill=skill)
        input_value = ensure_object(request.get("input"), "input")
        canonical_input = canonicalize(input_value)
        upstream_rows = validate_upstream_entities(metadata)
        upstream_fps = upstream_entity_fingerprints(upstream_rows)
        input_fp = input_fingerprint(skill, metadata["runtime_unit_key"], metadata["input_mode"], canonical_input, metadata["authority_refs"], metadata["reference_refs"], metadata["selection_source"])
        model_fp = model_fingerprint(metadata, input_fp)
        runtime_fp = implementation_fingerprint(Path(__file__))
        generator_fp = implementation_fingerprint(generator_path)
        result = handler(canonical_input, metadata)
        if not isinstance(result, dict):
            raise InternalRuntimeError("runtime handlerはobjectを返す必要があります")
        effective_static_data_versions = canonicalize(result.get("static_data_versions", metadata["static_data_versions"]))
        if not isinstance(effective_static_data_versions, dict):
            raise InternalRuntimeError("static_data_versionsはobjectである必要があります")
        for static_key, static_value in effective_static_data_versions.items():
            if not isinstance(static_key, str) or not re.fullmatch(r"[a-z][a-z0-9_]*", static_key) or not isinstance(static_value, str) or not (FULL_DIGEST_RE.fullmatch(static_value) or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", static_value)):
                raise InternalRuntimeError("runtime static_data_versionsが不正です")
        payload = canonicalize(result.get("payload", {}))
        support_status = result.get("support_status", "supported")
        runtime_status = result.get("runtime_status", "ok")
        result_status = result.get("result_status", "ready")
        runtime_required = result.get("runtime_required")
        deterministic_generated = result.get("deterministic_generated")
        fallback_reason = result.get("fallback_reason")
        if support_status not in SUPPORTED_SUPPORT_STATUSES or runtime_status not in SUPPORTED_STATUSES or result_status not in SUPPORTED_RESULT_STATUSES:
            raise InternalRuntimeError("runtime statusが不正です")
        if runtime_status == "unsupported":
            support_status, runtime_required, deterministic_generated, result_status, fallback_reason = "unsupported", False, False, "ready", "outside_supported_subset"
        elif runtime_status == "not_run":
            support_status, runtime_required, deterministic_generated, result_status, fallback_reason = "unknown", True, False, "blocked", "python_unavailable"
        elif runtime_status in {"invalid_input", "limit_exceeded", "internal_error"}:
            runtime_required, deterministic_generated, result_status = True, False, "blocked"
        else:
            if runtime_required is None:
                runtime_required = support_status != "unsupported"
            if deterministic_generated is None:
                deterministic_generated = bool(runtime_status == "ok" and runtime_required)
        if not isinstance(runtime_required, bool) or not isinstance(deterministic_generated, bool):
            raise InternalRuntimeError("runtime_required / deterministic_generatedが不正です")
        generation_fp = generation_fingerprint(generator=generator, input_fp=input_fp, model_fp=model_fp, runtime_contract_version=RUNTIME_CONTRACT_VERSION, generator_contract_version=generator_contract_version, runtime_impl_fp=runtime_fp, generator_impl_fp=generator_fp, upstream=upstream_fps, static_data_versions=effective_static_data_versions)
        payload = bind_current_entity_runtime_dependencies(
            payload,
            generation_fp,
            runtime_context={
                "runtime_contract_version": RUNTIME_CONTRACT_VERSION,
                "generator_contract_version": generator_contract_version,
                "runtime_implementation_fingerprint": runtime_fp,
                "generator_implementation_fingerprint": generator_fp,
                "static_data_versions": effective_static_data_versions,
            },
        )
        issues = canonicalize(result.get("issues", []))
        if not isinstance(issues, list):
            raise InternalRuntimeError("issuesはarrayである必要があります")
        for issue in issues:
            if not isinstance(issue, dict):
                raise InternalRuntimeError("issue rowはobjectである必要があります")
        if result_status == "ready" and any(issue.get("blocking") is True for issue in issues):
            raise InternalRuntimeError("blocking issueを含むruntime resultはreadyにできません")
        for issue in issues:
            issue.setdefault("skill", skill)
            issue.setdefault("runtime_unit_key", metadata["runtime_unit_key"])
            issue.setdefault("model_key", metadata["model_key"])
            issue.setdefault("target_key", None)
            issue.setdefault("generation_fingerprint", generation_fp)
        envelope = {
            "envelope_version": ENVELOPE_VERSION,
            "skill": skill,
            "runtime_contract_version": RUNTIME_CONTRACT_VERSION,
            "generator_contract_version": generator_contract_version,
            "generator": generator,
            "runtime_unit_key": metadata["runtime_unit_key"],
            "model_key": metadata["model_key"],
            "input_fingerprint": input_fp,
            "model_fingerprint": model_fp,
            "generation_fingerprint": generation_fp,
            "runtime_implementation_fingerprint": runtime_fp,
            "generator_implementation_fingerprint": generator_fp,
            "upstream_entity_fingerprints": upstream_fps,
            "upstream_runtime_units": canonicalize(metadata["upstream_runtime_units"], parent_key="upstream_runtime_units"),
            "support_status": support_status,
            "static_data_versions": effective_static_data_versions,
            "runtime_status": runtime_status,
            "result_status": result_status,
            "runtime_required": runtime_required,
            "deterministic_generated": deterministic_generated,
            "fallback_reason": fallback_reason,
            "payload": payload,
            "issues": issues,
        }
        _emit(envelope)
        return 1 if runtime_status == "internal_error" else 0
    except RuntimeErrorBase as exc:
        status = exc.issue_type if exc.issue_type in SUPPORTED_STATUSES else "invalid_input"
        has_verified_context = metadata is not None and canonical_input is not None and input_fp is not None and runtime_fp is not None and generator_fp is not None
        envelope = _error_envelope(
            skill=skill,
            generator=generator,
            generator_contract_version=generator_contract_version,
            generator_path=generator_path,
            status=status,
            message=exc.message,
            runtime_unit_key=metadata["runtime_unit_key"] if has_verified_context and metadata is not None else None,
            model_key=metadata["model_key"] if has_verified_context and metadata is not None else None,
        )
        if has_verified_context and metadata is not None and input_fp is not None and runtime_fp is not None and generator_fp is not None:
            static_data_versions = canonicalize(metadata["static_data_versions"])
            envelope["input_fingerprint"] = input_fp
            envelope["model_fingerprint"] = model_fp
            envelope["upstream_entity_fingerprints"] = upstream_fps
            envelope["upstream_runtime_units"] = canonicalize(metadata["upstream_runtime_units"], parent_key="upstream_runtime_units")
            envelope["static_data_versions"] = static_data_versions
            envelope["generation_fingerprint"] = generation_fingerprint(
                generator=generator,
                input_fp=input_fp,
                model_fp=model_fp,
                runtime_contract_version=RUNTIME_CONTRACT_VERSION,
                generator_contract_version=generator_contract_version,
                runtime_impl_fp=runtime_fp,
                generator_impl_fp=generator_fp,
                upstream=upstream_fps,
                static_data_versions=static_data_versions,
            )
            envelope["issues"][0].update({
                "runtime_unit_key": metadata["runtime_unit_key"],
                "model_key": metadata["model_key"],
                "generation_fingerprint": envelope["generation_fingerprint"],
            })
        if isinstance(exc, UnsupportedInput):
            if (
                isinstance(exc.item_type, str) and exc.item_type
                and isinstance(exc.source_key, str) and exc.source_key
                and isinstance(exc.reason_code, str) and exc.reason_code
                and (exc.affected_technique_slug is None or isinstance(exc.affected_technique_slug, str))
            ):
                item = make_unsupported_item(
                    generator=generator,
                    item_type=exc.item_type,
                    source_key=exc.source_key,
                    reason_code=exc.reason_code,
                    affected_technique_slug=exc.affected_technique_slug,
                )
                envelope["payload"] = {"unsupported_items": [item]}
            else:
                # No stable partial-item identity means the runtime can only
                # report a whole-model unsupported closure.
                envelope["payload"] = {"unsupported_items": []}
            envelope["runtime_status"] = "unsupported"
            envelope["support_status"] = "unsupported"
            envelope["runtime_required"] = False
            envelope["result_status"] = "ready"
            envelope["fallback_reason"] = "outside_supported_subset"
        _emit(envelope)
        return 0 if status in {"invalid_input", "limit_exceeded", "unsupported"} else 1
    except Exception as exc:  # pragma: no cover - defensive subprocess boundary
        if metadata is not None and canonical_input is not None and input_fp is not None and runtime_fp is not None and generator_fp is not None:
            generation_fp = generation_fingerprint(
                generator=generator,
                input_fp=input_fp,
                model_fp=model_fp,
                runtime_contract_version=RUNTIME_CONTRACT_VERSION,
                generator_contract_version=generator_contract_version,
                runtime_impl_fp=runtime_fp,
                generator_impl_fp=generator_fp,
                upstream=upstream_fps,
                static_data_versions=canonicalize(metadata["static_data_versions"]),
            )
            envelope = _error_envelope(
                skill=skill,
                generator=generator,
                generator_contract_version=generator_contract_version,
                generator_path=generator_path,
                status="internal_error",
                message=f"runtime internal error: {type(exc).__name__}",
                runtime_unit_key=metadata["runtime_unit_key"],
                model_key=metadata["model_key"],
            )
            envelope.update({
                "input_fingerprint": input_fp,
                "model_fingerprint": model_fp,
                "generation_fingerprint": generation_fp,
                "upstream_entity_fingerprints": upstream_fps,
                "upstream_runtime_units": canonicalize(metadata["upstream_runtime_units"], parent_key="upstream_runtime_units"),
                "static_data_versions": canonicalize(metadata["static_data_versions"]),
            })
            envelope["issues"][0].update({
                "runtime_unit_key": metadata["runtime_unit_key"],
                "model_key": metadata["model_key"],
                "generation_fingerprint": generation_fp,
            })
            _emit(envelope)
        else:
            _emit(_error_envelope(skill=skill, generator=generator, generator_contract_version=generator_contract_version, generator_path=generator_path, status="internal_error", message=f"runtime internal error: {type(exc).__name__}"))
        return 1


def verify_runtime_evidence_cli() -> int:
    raw = sys.stdin.buffer.read(MAX_AGGREGATE_INPUT_BYTES + 1)
    try:
        request = strict_loads(raw, aggregate=True)
        if not isinstance(request, dict):
            raise InvalidInput("top-level JSONはobjectである必要があります")
        _emit(verify_runtime_evidence(request))
        return 0
    except RuntimeErrorBase as exc:
        _emit({"valid": False, "issues": [{"issue_type": exc.issue_type, "blocking": True, "message": exc.message}], "expected_runtime_units": [], "actual_runtime_units": [], "missing": [], "extra": [], "incomplete_pairs": [], "duplicates": [], "expected_entities": [], "actual_entities": [], "missing_entities": [], "extra_entities": [], "duplicate_entities": [], "current_structure_state": None})
        return 0


if __name__ == "__main__":
    raise SystemExit(verify_runtime_evidence_cli())
