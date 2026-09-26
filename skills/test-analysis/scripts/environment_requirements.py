"""Normalize and intersect explicit environment requirements."""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Any

from runtime_contract import InvalidInput, UnsupportedInput, canonical_json_text, canonicalize, compare_versions, constraint_intersection_compatible, ensure_list, ensure_key, ensure_nonempty_string, reject_unknown, run_cli, typed_value, typed_value_compare


SKILL = "test-analysis"
GENERATOR = "environment_requirements"
GENERATOR_CONTRACT_VERSION = "environment-requirements-v1"
SCRIPT_PATH = Path(__file__).resolve()


def _typed(value: Any, name: str) -> dict:
    if not isinstance(value, dict):
        raise InvalidInput(f"{name}はtyped valueである必要があります")
    return typed_value(value)


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
            raise UnsupportedInput("unknown environment operator", item_type="environment_requirement", source_key=key, reason_code="unsupported_intersection")
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
        if not isinstance(normalized["minimum_inclusive"], bool) or not isinstance(normalized["maximum_inclusive"], bool):
            raise InvalidInput("environment rangeが不正です")
        if typed_value_compare(normalized["minimum"], normalized["maximum"]) > 0:
            raise InvalidInput("environment range minimumがmaximumを超えています")
        constraint_intersection_compatible([normalized])
    elif operator == "version_range":
        normalized["minimum"] = row.get("minimum")
        normalized["maximum"] = row.get("maximum")
        normalized["minimum_inclusive"] = row.get("minimum_inclusive")
        normalized["maximum_inclusive"] = row.get("maximum_inclusive")
        if not isinstance(normalized["minimum_inclusive"], bool) or not isinstance(normalized["maximum_inclusive"], bool) or compare_versions(normalized["minimum"], normalized["maximum"]) > 0:
            raise InvalidInput("version range inclusiveが不正です")
    elif operator == "boolean":
        if not isinstance(row.get("value"), bool):
            raise InvalidInput("environment boolean valueが不正です")
        normalized["value"] = row["value"]
    else:
        raise UnsupportedInput("unknown environment operator", item_type="environment_requirement", source_key=key, reason_code="unsupported_intersection")
    return normalized


def generate(input_value: dict, metadata: dict) -> dict:
    if metadata["runtime_unit_key"] != "artifact:environment_requirements:all":
        raise InvalidInput("environment_requirements runtime unitが不正です")
    reject_unknown(input_value, {"requirements"})
    rows = []
    for index, row in enumerate(ensure_list(input_value["requirements"], "requirements")):
        if not isinstance(row, dict):
            raise InvalidInput("requirement rowが不正です")
        try:
            rows.append(_normalize_requirement(row, index))
        except UnsupportedInput as exc:
            requirement_key = row.get("requirement_key")
            if isinstance(requirement_key, str) and requirement_key:
                raise UnsupportedInput(
                    exc.message,
                    item_type="environment_requirement",
                    source_key=requirement_key,
                    reason_code=exc.reason_code or "unsupported_intersection",
                    affected_technique_slug=exc.affected_technique_slug,
                ) from exc
            raise
    if len({row["requirement_key"] for row in rows}) != len(rows):
        raise InvalidInput("requirement_keyが重複しています")
    conflicts = []
    grouped: dict[tuple[str, str], list[dict]] = {}
    for row in rows:
        grouped.setdefault((row["environment_key"], row["dimension_key"]), []).append(row)
    for (environment_key, dimension_key), group in sorted(grouped.items()):
        try:
            compatible = constraint_intersection_compatible(group)
        except UnsupportedInput as exc:
            source_key = sorted(row["requirement_key"] for row in group)[0]
            raise UnsupportedInput(
                exc.message,
                item_type="environment_requirement",
                source_key=source_key,
                reason_code=exc.reason_code or "unsupported_intersection",
            ) from exc
        if not compatible:
            conflicts.append({"environment_key": environment_key, "dimension_key": dimension_key, "requirement_keys": sorted(row["requirement_key"] for row in group)})
    conflicts.sort(key=lambda row: (row["environment_key"], row["dimension_key"], row["requirement_keys"]))
    rows.sort(key=lambda row: row["requirement_key"])
    return {"runtime_status": "ok", "support_status": "supported", "result_status": "unresolved" if conflicts else "ready", "runtime_required": True, "deterministic_generated": True, "payload": {"normalized_requirements": rows, "conflicts": conflicts}, "issues": [{"issue_type": "environment_conflict", "blocking": True, "target_key": f"env:{row['environment_key']}", "authority_refs": []} for row in conflicts]}


if __name__ == "__main__":
    raise SystemExit(run_cli(generate, skill=SKILL, generator=GENERATOR, generator_contract_version=GENERATOR_CONTRACT_VERSION, generator_path=SCRIPT_PATH))
