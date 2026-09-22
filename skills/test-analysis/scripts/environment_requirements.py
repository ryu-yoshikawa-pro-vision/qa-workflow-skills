"""Normalize and intersect explicit environment requirements."""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Any

from runtime_contract import InvalidInput, UnsupportedInput, canonical_json_text, canonicalize, ensure_list, ensure_key, ensure_nonempty_string, exact_compare, reject_unknown, run_cli, typed_value


SKILL = "test-analysis"
GENERATOR = "environment_requirements"
GENERATOR_CONTRACT_VERSION = "environment-requirements-v1"
SCRIPT_PATH = Path(__file__).resolve()


def _typed(value: Any, name: str) -> dict:
    if not isinstance(value, dict):
        raise InvalidInput(f"{name}はtyped valueである必要があります")
    return typed_value(value)


def _version(value: Any, name: str) -> tuple[int, ...]:
    if not isinstance(value, str) or not value or any(component != "0" and component.startswith("0") for component in value.split(".")) or any(not component.isdigit() for component in value.split(".")):
        raise InvalidInput(f"{name}のversion形式が不正です")
    return tuple(int(component) for component in value.split("."))


def _member(value: dict, constraint: dict) -> bool:
    operator = constraint["operator"]
    if operator == "eq":
        return canonical_json_text(value) == canonical_json_text(constraint["value"])
    if operator == "enum":
        return any(canonical_json_text(value) == canonical_json_text(candidate) for candidate in constraint["values"])
    if operator == "range":
        low = _compare(value, constraint["minimum"])
        high = _compare(value, constraint["maximum"])
        return (low > 0 or (low == 0 and constraint["minimum_inclusive"])) and (high < 0 or (high == 0 and constraint["maximum_inclusive"]))
    return False


def _compare(left: dict, right: dict) -> int:
    if left["type"] != right["type"]:
        raise InvalidInput("constraint typed value typeが不一致です")
    if left["type"] == "decimal":
        return exact_compare(left["value"], right["value"])
    return (left["value"] > right["value"]) - (left["value"] < right["value"])


def _compatible(left: dict, right: dict) -> bool:
    left_operator = left["operator"]
    right_operator = right["operator"]
    if left_operator in {"eq", "enum", "range"} and right_operator in {"eq", "enum", "range"}:
        if left_operator == "eq" and right_operator == "eq":
            return canonical_json_text(left["value"]) == canonical_json_text(right["value"])
        if left_operator == "eq":
            return _member(left["value"], right)
        if right_operator == "eq":
            return _member(right["value"], left)
        if left_operator == "enum" and right_operator == "enum":
            return any(canonical_json_text(value) == canonical_json_text(candidate) for value in left["values"] for candidate in right["values"])
        if left_operator == "enum":
            return any(_member(value, right) for value in left["values"])
        if right_operator == "enum":
            return any(_member(value, left) for value in right["values"])
        if left["minimum"]["type"] != right["minimum"]["type"]:
            raise UnsupportedInput("異なるtyped rangeのintersectionは未対応", item_key="environment:range", reason_code="unsupported_intersection")
        low_side = _compare(left["minimum"], right["minimum"])
        high_side = _compare(left["maximum"], right["maximum"])
        if low_side > 0:
            low, low_inclusive = left["minimum"], left["minimum_inclusive"]
        elif low_side < 0:
            low, low_inclusive = right["minimum"], right["minimum_inclusive"]
        else:
            low, low_inclusive = left["minimum"], left["minimum_inclusive"] and right["minimum_inclusive"]
        if high_side < 0:
            high, high_inclusive = left["maximum"], left["maximum_inclusive"]
        elif high_side > 0:
            high, high_inclusive = right["maximum"], right["maximum_inclusive"]
        else:
            high, high_inclusive = left["maximum"], left["maximum_inclusive"] and right["maximum_inclusive"]
        comparison = _compare(low, high)
        return comparison < 0 or (comparison == 0 and low_inclusive and high_inclusive)
    if left_operator == "boolean" and right_operator == "boolean":
        return left["value"] == right["value"]
    if left_operator == "boolean" and right_operator == "eq":
        return right["value"]["type"] == "boolean" and right["value"]["value"] == left["value"]
    if right_operator == "boolean" and left_operator == "eq":
        return left["value"]["type"] == "boolean" and left["value"]["value"] == right["value"]
    if left["operator"] == "version_range" and right["operator"] == "version_range":
        left_low, right_low = _version(left["minimum"], "minimum"), _version(right["minimum"], "minimum")
        left_high, right_high = _version(left["maximum"], "maximum"), _version(right["maximum"], "maximum")
        if left_low > right_low:
            low, low_inclusive = left_low, left["minimum_inclusive"]
        elif left_low < right_low:
            low, low_inclusive = right_low, right["minimum_inclusive"]
        else:
            low, low_inclusive = left_low, left["minimum_inclusive"] and right["minimum_inclusive"]
        if left_high < right_high:
            high, high_inclusive = left_high, left["maximum_inclusive"]
        elif left_high > right_high:
            high, high_inclusive = right_high, right["maximum_inclusive"]
        else:
            high, high_inclusive = left_high, left["maximum_inclusive"] and right["maximum_inclusive"]
        return low < high or (low == high and low_inclusive and high_inclusive)
    raise UnsupportedInput("constraint operatorのintersectionが未対応", item_key="environment:operator", reason_code="unsupported_intersection")


def _normalize_requirement(row: dict, index: int) -> dict:
    required = {"requirement_key", "environment_key", "dimension_key", "operator", "authority_refs", "source_model_key", "source_target_versions"}
    optional = {"value", "values", "minimum", "maximum", "minimum_inclusive", "maximum_inclusive"}
    reject_unknown(row, required, optional)
    key = ensure_key(row["requirement_key"], f"requirements[{index}].requirement_key")
    env = ensure_key(row["environment_key"], f"requirements[{index}].environment_key")
    dimension = ensure_key(row["dimension_key"], f"requirements[{index}].dimension_key")
    if row["source_model_key"] is not None or row["source_target_versions"] != []:
        raise InvalidInput("environment requirementのsourceはnull/空配列である必要があります")
    if not isinstance(row["authority_refs"], list) or len(set(row["authority_refs"])) != len(row["authority_refs"]) or not all(isinstance(value, str) for value in row["authority_refs"]):
        raise InvalidInput("environment authority_refsが不正です")
    operator = row["operator"]
    operator_fields = {
        "eq": {"value"},
        "enum": {"values"},
        "range": {"minimum", "maximum", "minimum_inclusive", "maximum_inclusive"},
        "version_range": {"minimum", "maximum", "minimum_inclusive", "maximum_inclusive"},
        "boolean": {"value"},
    }
    if operator not in operator_fields or set(row) != required | operator_fields[operator]:
        if operator not in operator_fields:
            raise UnsupportedInput("unknown environment operator", item_key=f"env:{key}", reason_code="unsupported_intersection")
        raise InvalidInput("environment operator fieldが不正です")
    normalized = {"requirement_key": key, "environment_key": env, "dimension_key": dimension, "operator": operator, "authority_refs": sorted(set(row["authority_refs"])), "source_model_key": None, "source_target_versions": []}
    if operator == "eq":
        normalized["value"] = _typed(row.get("value"), f"requirements[{index}].value")
    elif operator == "enum":
        values = [_typed(value, f"requirements[{index}].values") for value in ensure_list(row.get("values"), "requirement.values")]
        if not values or len({canonical_json_text(value) for value in values}) != len(values):
            raise InvalidInput("environment enum valuesが不正です")
        normalized["values"] = values
    elif operator == "range":
        normalized["minimum"] = _typed(row.get("minimum"), f"requirements[{index}].minimum")
        normalized["maximum"] = _typed(row.get("maximum"), f"requirements[{index}].maximum")
        normalized["minimum_inclusive"] = row.get("minimum_inclusive")
        normalized["maximum_inclusive"] = row.get("maximum_inclusive")
        if not isinstance(normalized["minimum_inclusive"], bool) or not isinstance(normalized["maximum_inclusive"], bool) or _compare(normalized["minimum"], normalized["maximum"]) > 0:
            raise InvalidInput("environment rangeが不正です")
    elif operator == "version_range":
        normalized["minimum"] = row.get("minimum")
        normalized["maximum"] = row.get("maximum")
        normalized["minimum_inclusive"] = row.get("minimum_inclusive")
        normalized["maximum_inclusive"] = row.get("maximum_inclusive")
        _version(normalized["minimum"], "minimum")
        _version(normalized["maximum"], "maximum")
        if not isinstance(normalized["minimum_inclusive"], bool) or not isinstance(normalized["maximum_inclusive"], bool):
            raise InvalidInput("version range inclusiveが不正です")
    elif operator == "boolean":
        if not isinstance(row.get("value"), bool):
            raise InvalidInput("environment boolean valueが不正です")
        normalized["value"] = row["value"]
    else:
        raise UnsupportedInput("unknown environment operator", item_key=f"env:{key}", reason_code="unsupported_intersection")
    return normalized


def generate(input_value: dict, metadata: dict) -> dict:
    if metadata["runtime_unit_key"] != "artifact:environment_requirements:all":
        raise InvalidInput("environment_requirements runtime unitが不正です")
    reject_unknown(input_value, {"requirements"})
    rows = []
    for index, row in enumerate(ensure_list(input_value["requirements"], "requirements")):
        if not isinstance(row, dict):
            raise InvalidInput("requirement rowが不正です")
        rows.append(_normalize_requirement(row, index))
    if len({row["requirement_key"] for row in rows}) != len(rows):
        raise InvalidInput("requirement_keyが重複しています")
    conflicts = []
    grouped: dict[tuple[str, str], list[dict]] = {}
    for row in rows:
        grouped.setdefault((row["environment_key"], row["dimension_key"]), []).append(row)
    for (environment_key, dimension_key), group in sorted(grouped.items()):
        for left_index, left in enumerate(group):
            for right in group[left_index + 1 :]:
                if not _compatible(left, right):
                    conflicts.append({"environment_key": environment_key, "dimension_key": dimension_key, "requirement_keys": sorted([left["requirement_key"], right["requirement_key"]])})
    conflicts.sort(key=lambda row: (row["environment_key"], row["dimension_key"], row["requirement_keys"]))
    rows.sort(key=lambda row: row["requirement_key"])
    return {"runtime_status": "ok", "support_status": "supported", "result_status": "ready", "runtime_required": True, "deterministic_generated": True, "payload": {"normalized_requirements": rows, "conflicts": conflicts}, "issues": [{"issue_type": "environment_conflict", "blocking": True, "target_key": f"env:{row['environment_key']}", "authority_refs": []} for row in conflicts]}


if __name__ == "__main__":
    raise SystemExit(run_cli(generate, skill=SKILL, generator=GENERATOR, generator_contract_version=GENERATOR_CONTRACT_VERSION, generator_path=SCRIPT_PATH))
