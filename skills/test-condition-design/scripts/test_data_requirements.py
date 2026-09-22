"""Normalize test-data requirements and check simultaneous target intersections."""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Any

from runtime_contract import FULL_DIGEST_RE, InvalidInput, UnsupportedInput, canonical_json_text, canonicalize, ensure_key, ensure_list, ensure_nonempty_string, exact_compare, make_machine_entity, reject_unknown, run_cli, typed_value


SKILL = "test-condition-design"
GENERATOR = "test_data_requirements"
GENERATOR_CONTRACT_VERSION = "test-data-requirements-v1"
SCRIPT_PATH = Path(__file__).resolve()
OPERATORS = {"eq", "enum", "range", "version_range", "boolean"}


def _version(value: Any, name: str) -> tuple[int, ...]:
    if not isinstance(value, str) or not value or any(not part.isdigit() or (len(part) > 1 and part.startswith("0")) for part in value.split(".")):
        raise InvalidInput(f"{name}のversion形式が不正です")
    return tuple(int(part) for part in value.split("."))


def _typed(value: Any, name: str) -> dict:
    if not isinstance(value, dict):
        raise InvalidInput(f"{name}はtyped valueである必要があります")
    return typed_value(value)


def _compare(left: dict, right: dict) -> int:
    if left["type"] != right["type"]:
        raise UnsupportedInput("異なるtyped valueのintersectionは未対応", item_key="unsupported:test-data:type", reason_code="unsupported_intersection")
    if left["type"] == "decimal":
        return exact_compare(left["value"], right["value"])
    return (left["value"] > right["value"]) - (left["value"] < right["value"])


def _member(value: dict, row: dict) -> bool:
    if row["operator"] == "eq":
        return canonical_json_text(value) == canonical_json_text(row["value"])
    if row["operator"] == "enum":
        return any(canonical_json_text(value) == canonical_json_text(candidate) for candidate in row["values"])
    if row["operator"] == "range":
        low = _compare(value, row["minimum"])
        high = _compare(value, row["maximum"])
        return (low > 0 or low == 0 and row["minimum_inclusive"]) and (high < 0 or high == 0 and row["maximum_inclusive"])
    return False


def _compatible(left: dict, right: dict) -> bool:
    a, b = left["operator"], right["operator"]
    if a in {"eq", "enum", "range"} and b in {"eq", "enum", "range"}:
        if a == "eq":
            return _member(left["value"], right)
        if b == "eq":
            return _member(right["value"], left)
        if a == "enum" and b == "enum":
            return any(canonical_json_text(x) == canonical_json_text(y) for x in left["values"] for y in right["values"])
        if a == "enum":
            return any(_member(value, right) for value in left["values"])
        if b == "enum":
            return any(_member(value, left) for value in right["values"])
        low_cmp = _compare(left["minimum"], right["minimum"])
        high_cmp = _compare(left["maximum"], right["maximum"])
        low = left["minimum"] if low_cmp > 0 else right["minimum"] if low_cmp < 0 else left["minimum"]
        high = left["maximum"] if high_cmp < 0 else right["maximum"] if high_cmp > 0 else left["maximum"]
        low_inclusive = left["minimum_inclusive"] if low_cmp > 0 else right["minimum_inclusive"] if low_cmp < 0 else left["minimum_inclusive"] and right["minimum_inclusive"]
        high_inclusive = left["maximum_inclusive"] if high_cmp < 0 else right["maximum_inclusive"] if high_cmp > 0 else left["maximum_inclusive"] and right["maximum_inclusive"]
        comparison = _compare(low, high)
        return comparison < 0 or comparison == 0 and low_inclusive and high_inclusive
    if a == "boolean" and b == "boolean":
        return left["value"] == right["value"]
    if a == "boolean" and b == "eq":
        return right["value"]["type"] == "boolean" and right["value"]["value"] == left["value"]
    if b == "boolean" and a == "eq":
        return left["value"]["type"] == "boolean" and left["value"]["value"] == right["value"]
    if a == "version_range" and b == "version_range":
        low_a, low_b = _version(left["minimum"], "minimum"), _version(right["minimum"], "minimum")
        high_a, high_b = _version(left["maximum"], "maximum"), _version(right["maximum"], "maximum")
        if low_a > low_b:
            low, low_inc = low_a, left["minimum_inclusive"]
        elif low_a < low_b:
            low, low_inc = low_b, right["minimum_inclusive"]
        else:
            low, low_inc = low_a, left["minimum_inclusive"] and right["minimum_inclusive"]
        if high_a < high_b:
            high, high_inc = high_a, left["maximum_inclusive"]
        elif high_a > high_b:
            high, high_inc = high_b, right["maximum_inclusive"]
        else:
            high, high_inc = high_a, left["maximum_inclusive"] and right["maximum_inclusive"]
        return low < high or low == high and low_inc and high_inc
    raise UnsupportedInput("test-data operator組合せが未対応", item_key="unsupported:test-data:operator", reason_code="unsupported_intersection")


def _normalize(row: dict, index: int, current_targets: dict[str, dict]) -> dict:
    required = {"requirement_key", "environment_key", "dimension_key", "operator", "authority_refs", "source_model_key", "source_target_versions"}
    reject_unknown(row, required, {"value", "values", "minimum", "maximum", "minimum_inclusive", "maximum_inclusive"})
    key = ensure_key(row["requirement_key"], f"requirements[{index}].requirement_key")
    if row["environment_key"] is not None or not ensure_key(row["dimension_key"], f"requirements[{index}].dimension_key") or row["operator"] not in OPERATORS:
        raise InvalidInput("test-data requirement identity/operatorが不正です")
    if not isinstance(row["authority_refs"], list) or len(set(row["authority_refs"])) != len(row["authority_refs"]) or not all(isinstance(value, str) and value for value in row["authority_refs"]):
        raise InvalidInput("test-data authority_refsが不正です")
    source_model = row["source_model_key"]
    if not isinstance(source_model, str) or not source_model:
        raise InvalidInput("source_model_keyが不正です")
    source_versions = ensure_list(row["source_target_versions"], f"requirements[{index}].source_target_versions")
    normalized = {"requirement_key": key, "environment_key": None, "dimension_key": row["dimension_key"], "operator": row["operator"], "authority_refs": sorted(row["authority_refs"]), "source_model_key": source_model, "source_target_versions": [], "data_ref": f"data:{key}"}
    if row["operator"] == "eq":
        normalized["value"] = _typed(row.get("value"), f"requirements[{index}].value")
    elif row["operator"] == "enum":
        values = [_typed(value, f"requirements[{index}].values") for value in ensure_list(row.get("values"), f"requirements[{index}].values")]
        if not values or len({canonical_json_text(value) for value in values}) != len(values):
            raise InvalidInput("test-data enumが不正です")
        normalized["values"] = values
    elif row["operator"] == "range":
        normalized["minimum"] = _typed(row.get("minimum"), f"requirements[{index}].minimum")
        normalized["maximum"] = _typed(row.get("maximum"), f"requirements[{index}].maximum")
        normalized["minimum_inclusive"] = row.get("minimum_inclusive")
        normalized["maximum_inclusive"] = row.get("maximum_inclusive")
        if not isinstance(normalized["minimum_inclusive"], bool) or not isinstance(normalized["maximum_inclusive"], bool) or _compare(normalized["minimum"], normalized["maximum"]) > 0:
            raise InvalidInput("test-data rangeが不正です")
    elif row["operator"] == "version_range":
        normalized["minimum"], normalized["maximum"] = row.get("minimum"), row.get("maximum")
        normalized["minimum_inclusive"], normalized["maximum_inclusive"] = row.get("minimum_inclusive"), row.get("maximum_inclusive")
        _version(normalized["minimum"], "minimum")
        _version(normalized["maximum"], "maximum")
        if not isinstance(normalized["minimum_inclusive"], bool) or not isinstance(normalized["maximum_inclusive"], bool):
            raise InvalidInput("test-data version rangeが不正です")
    else:
        if not isinstance(row.get("value"), bool):
            raise InvalidInput("test-data booleanが不正です")
        normalized["value"] = row["value"]
    if source_versions:
        seen = set()
        for version in source_versions:
            if not isinstance(version, dict) or set(version) != {"target_ref", "target_content_fingerprint", "generation_fingerprint"} or version["target_ref"] in seen:
                raise InvalidInput("source_target_versionsが不正です")
            seen.add(version["target_ref"])
            if version["target_ref"] not in current_targets or not FULL_DIGEST_RE.fullmatch(str(version["target_content_fingerprint"])) or not FULL_DIGEST_RE.fullmatch(str(version["generation_fingerprint"])):
                raise InvalidInput("source_target_versionsがcurrent targetと不一致です")
            if current_targets[version["target_ref"]]["source_model_key"] != source_model:
                raise InvalidInput("source_target_versionsがsource_model_keyと不一致です")
        normalized["source_target_versions"] = sorted(canonicalize(source_versions), key=lambda value: value["target_ref"])
    return normalized


def generate(input_value: dict, metadata: dict) -> dict:
    if metadata["runtime_unit_key"] != "artifact:test_data_requirements:all":
        raise InvalidInput("test_data_requirements runtime unitが不正です")
    reject_unknown(input_value, {"requirements", "current_source_targets"})
    target_rows = ensure_list(input_value["current_source_targets"], "current_source_targets")
    current_targets: dict[str, dict] = {}
    for index, row in enumerate(target_rows):
        if not isinstance(row, dict) or set(row) != {"source_model_key", "target_ref", "target_content_fingerprint", "generation_fingerprint"} or row["target_ref"] in current_targets:
            raise InvalidInput(f"current_source_targets[{index}]が不正です")
        if not ensure_nonempty_string(row["source_model_key"], "source_model_key") or not FULL_DIGEST_RE.fullmatch(str(row["target_ref"])) or not FULL_DIGEST_RE.fullmatch(str(row["target_content_fingerprint"])) or not FULL_DIGEST_RE.fullmatch(str(row["generation_fingerprint"])):
            raise InvalidInput("current_source_targetsのdigestが不正です")
        current_targets[row["target_ref"]] = canonicalize(row)
    requirements = []
    seen = set()
    for index, row in enumerate(ensure_list(input_value["requirements"], "requirements")):
        if not isinstance(row, dict):
            raise InvalidInput("requirement rowが不正です")
        normalized = _normalize(row, index, current_targets)
        if normalized["requirement_key"] in seen:
            raise InvalidInput("requirement_keyが重複しています")
        seen.add(normalized["requirement_key"])
        source_model = normalized["source_model_key"]
        refs = [ref for ref, target in current_targets.items() if target["source_model_key"] == source_model]
        if normalized["source_target_versions"]:
            selected = {row["target_ref"] for row in normalized["source_target_versions"]}
            if not selected.issubset(set(refs)):
                raise InvalidInput("target-specific requirementのtarget所属が不正です")
            refs = sorted(selected)
        normalized["applicable_target_refs"] = sorted(refs)
        requirements.append(normalized)
    conflicts = []
    for target_ref, target in sorted(current_targets.items()):
        active = [row for row in requirements if target_ref in row["applicable_target_refs"]]
        grouped: dict[str, list[dict]] = {}
        for row in active:
            grouped.setdefault(row["dimension_key"], []).append(row)
        for dimension, rows in sorted(grouped.items()):
            for index, left in enumerate(rows):
                for right in rows[index + 1 :]:
                    if not _compatible(left, right):
                        conflicts.append({"target_ref": target_ref, "dimension_key": dimension, "requirement_keys": sorted([left["requirement_key"], right["requirement_key"]])})
    conflicts.sort(key=lambda row: (row["target_ref"], row["dimension_key"], row["requirement_keys"]))
    entities = [make_machine_entity(SKILL, "test_data_requirement", row["data_ref"], row, runtime_dependencies=[{"skill": SKILL, "runtime_unit_key": "artifact:test_data_requirements:all", "generation_fingerprint": "__CURRENT__"}]) for row in requirements]
    return {"runtime_status": "ok", "support_status": "supported", "result_status": "unresolved" if conflicts else "ready", "runtime_required": True, "deterministic_generated": True, "payload": {"normalized_requirements": sorted(requirements, key=lambda row: row["requirement_key"]), "conflicts": conflicts, "entities": sorted(entities, key=lambda row: row["entity_ref"]), "expected_entity_identities": [{"skill": SKILL, "entity_type": "test_data_requirement", "entity_ref": row["data_ref"]} for row in sorted(requirements, key=lambda row: row["requirement_key"])]}, "issues": [{"issue_type": "test_data_conflict", "blocking": True, "target_key": row["target_ref"], "authority_refs": []} for row in conflicts]}


if __name__ == "__main__":
    raise SystemExit(run_cli(generate, skill=SKILL, generator=GENERATOR, generator_contract_version=GENERATOR_CONTRACT_VERSION, generator_path=SCRIPT_PATH))
