"""Generate deterministic Equivalence Partitioning / Each Choice targets."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import sys
from typing import Any

from runtime_contract import (
    InvalidInput,
    RuntimeErrorBase,
    canonical_json_text,
    canonicalize,
    ensure_list,
    ensure_nonempty_string,
    exact_add,
    exact_compare,
    exact_to_decimal,
    post_process_targets,
    reject_unknown,
    run_cli,
    typed_sort_key,
    typed_value,
)


SKILL = "test-condition-design"
GENERATOR = "equivalence_partitions"
GENERATOR_CONTRACT_VERSION = "equivalence-partitions-v1"
SCRIPT_PATH = Path(__file__).resolve()


def _typed(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise InvalidInput(f"{name}はtyped value objectである必要があります")
    try:
        return typed_value(value)
    except RuntimeErrorBase:
        raise
    except (TypeError, ValueError) as exc:
        raise InvalidInput(f"{name}が不正です") from exc


def _compare(left: dict[str, Any], right: dict[str, Any], name: str) -> int:
    left = _typed(left, name)
    right = _typed(right, name)
    if left["type"] != right["type"]:
        raise InvalidInput(f"{name}のtyped value typeが一致しません")
    kind = left["type"]
    if kind == "integer":
        return (left["value"] > right["value"]) - (left["value"] < right["value"])
    if kind == "decimal":
        return exact_compare(left["value"], right["value"])
    if kind in {"string", "enum", "date", "local_datetime", "fixed_offset_datetime"}:
        if kind == "fixed_offset_datetime":
            left_dt = datetime.fromisoformat(left["value"])
            right_dt = datetime.fromisoformat(right["value"])
            return (left_dt > right_dt) - (left_dt < right_dt)
        return (left["value"] > right["value"]) - (left["value"] < right["value"])
    raise InvalidInput(f"{name}はrange比較に対応しないtyped valueです")


def _range_definition(definition: dict[str, Any], name: str) -> tuple[dict[str, Any], dict[str, Any], bool, bool]:
    reject_unknown(definition, {"type", "minimum", "maximum", "minimum_inclusive", "maximum_inclusive"})
    if definition["type"] != "range":
        raise InvalidInput(f"{name}.typeが不正です")
    minimum = _typed(definition["minimum"], f"{name}.minimum")
    maximum = _typed(definition["maximum"], f"{name}.maximum")
    if minimum["type"] not in {"integer", "decimal", "date", "local_datetime", "fixed_offset_datetime"} or maximum["type"] != minimum["type"]:
        raise InvalidInput(f"{name}のrange typeが不正です")
    minimum_inclusive = definition["minimum_inclusive"]
    maximum_inclusive = definition["maximum_inclusive"]
    if not isinstance(minimum_inclusive, bool) or not isinstance(maximum_inclusive, bool):
        raise InvalidInput(f"{name}.minimum_inclusive / maximum_inclusiveが不正です")
    comparison = _compare(minimum, maximum, name)
    if comparison > 0 or (comparison == 0 and not (minimum_inclusive and maximum_inclusive)):
        raise InvalidInput(f"{name}のrangeが空です")
    return minimum, maximum, minimum_inclusive, maximum_inclusive


def _member(value: dict[str, Any], definition: dict[str, Any], name: str) -> bool:
    value = _typed(value, name)
    if definition["type"] == "enum":
        return any(canonical_json_text(value) == canonical_json_text(candidate) for candidate in definition["values"])
    minimum, maximum, minimum_inclusive, maximum_inclusive = _range_definition(definition, name)
    low = _compare(value, minimum, name)
    high = _compare(value, maximum, name)
    return (low > 0 or (low == 0 and minimum_inclusive)) and (high < 0 or (high == 0 and maximum_inclusive))


def _overlap(left: dict[str, Any], right: dict[str, Any], name: str) -> bool:
    if left["type"] == "enum" and right["type"] == "enum":
        return any(canonical_json_text(a) == canonical_json_text(b) for a in left["values"] for b in right["values"])
    if left["type"] == "range" and right["type"] == "range":
        lmin, lmax, lmin_inc, lmax_inc = _range_definition(left, name)
        rmin, rmax, rmin_inc, rmax_inc = _range_definition(right, name)
        if lmin["type"] != rmin["type"]:
            return False
        low = (lmin, lmin_inc) if _compare(lmin, rmin, name) > 0 else (rmin, rmin_inc) if _compare(lmin, rmin, name) < 0 else (lmin, lmin_inc and rmin_inc)
        high = (lmax, lmax_inc) if _compare(lmax, rmax, name) < 0 else (rmax, rmax_inc) if _compare(lmax, rmax, name) > 0 else (lmax, lmax_inc and rmax_inc)
        comparison = _compare(low[0], high[0], name)
        if comparison < 0:
            return True
        if comparison > 0:
            return False
        return low[1] and high[1]
    enum_definition = left if left["type"] == "enum" else right
    range_definition = right if left["type"] == "enum" else left
    _range_min, _range_max, _min_inc, _max_inc = _range_definition(range_definition, name)
    return any(_member(value, range_definition, name) for value in enum_definition["values"])


def _representative(partition: dict[str, Any], definition: dict[str, Any], name: str) -> tuple[dict[str, Any] | None, bool]:
    supplied = partition["representative"]
    if supplied is not None:
        value = _typed(supplied, f"{name}.representative")
        if not _member(value, definition, name):
            raise InvalidInput(f"{name}.representativeがpartitionに属しません")
        return value, False
    if definition["type"] == "enum":
        return canonicalize(definition["values"][0]), False
    minimum, maximum, minimum_inclusive, _maximum_inclusive = _range_definition(definition, name)
    if minimum["type"] == "integer":
        if minimum_inclusive:
            value = minimum
        else:
            candidate = minimum["value"] + 1
            if candidate > maximum["value"] or (candidate == maximum["value"] and not _maximum_inclusive):
                raise InvalidInput(f"{name}のinteger representativeが存在しません")
            value = {"type": "integer", "value": candidate}
        if not _member(value, definition, name):
            raise InvalidInput(f"{name}のinteger representativeが不正です")
        return value, False
    return None, True


def _validate_partition_set(row: dict[str, Any], index: int) -> list[dict[str, Any]]:
    reject_unknown(row, {"set_key", "label", "partitions"})
    set_key = ensure_nonempty_string(row["set_key"], f"sets[{index}].set_key")
    ensure_nonempty_string(row["label"], f"sets[{index}].label")
    partitions = ensure_list(row["partitions"], f"sets[{index}].partitions")
    if not partitions:
        raise InvalidInput(f"sets[{index}].partitionsは1件以上必要です")
    seen: set[str] = set()
    result = []
    for p_index, partition in enumerate(partitions):
        if not isinstance(partition, dict):
            raise InvalidInput(f"sets[{index}].partitions[{p_index}]が不正です")
        reject_unknown(partition, {"partition_key", "label", "validity", "definition", "representative", "authority_refs"})
        partition_key = ensure_nonempty_string(partition["partition_key"], f"sets[{index}].partitions[{p_index}].partition_key")
        if partition_key in seen:
            raise InvalidInput(f"partition_keyが重複しています: {partition_key}")
        seen.add(partition_key)
        ensure_nonempty_string(partition["label"], f"sets[{index}].partitions[{p_index}].label")
        if partition["validity"] not in {"valid", "invalid"}:
            raise InvalidInput("partition validityが不正です")
        definition = partition["definition"]
        if not isinstance(definition, dict) or definition.get("type") not in {"enum", "range"}:
            raise InvalidInput("partition definitionが不正です")
        if definition["type"] == "enum":
            reject_unknown(definition, {"type", "values"})
            values = ensure_list(definition["values"], "partition definition.values")
            if not values:
                raise InvalidInput("enum valuesは1件以上必要です")
            normalized_values = [_typed(value, "partition enum value") for value in values]
            if len({canonical_json_text(value) for value in normalized_values}) != len(normalized_values):
                raise InvalidInput("enum valuesが重複しています")
            definition = {"type": "enum", "values": normalized_values}
        else:
            definition = canonicalize(definition)
            _range_definition(definition, "partition definition")
        _unique_refs = partition["authority_refs"]
        if not isinstance(_unique_refs, list) or not all(isinstance(value, str) for value in _unique_refs) or len(set(_unique_refs)) != len(_unique_refs):
            raise InvalidInput("partition authority_refsが不正です")
        result.append({**partition, "set_key": set_key, "set_label": row["label"], "definition": definition})
    for left_index, left in enumerate(result):
        for right in result[left_index + 1 :]:
            if _overlap(left["definition"], right["definition"], f"set {set_key}"):
                raise InvalidInput(f"同一set内のpartition定義が重複しています: {set_key}")
    return result


def generate(input_value: dict[str, Any], metadata: dict[str, Any]) -> dict[str, Any]:
    if metadata["model_type"] != "ep" or metadata["technique_slug"] != "ep":
        raise InvalidInput("EP runtime metadataが不正です")
    reject_unknown(input_value, {"sets"})
    sets = ensure_list(input_value["sets"], "sets")
    if not sets:
        raise InvalidInput("setsは1件以上必要です")
    all_partitions: list[tuple[dict[str, Any], dict[str, Any]]] = []
    seen_sets: set[str] = set()
    for index, row in enumerate(sorted(sets, key=lambda value: value.get("set_key", "") if isinstance(value, dict) else "")):
        if not isinstance(row, dict):
            raise InvalidInput(f"sets[{index}]がobjectである必要があります")
        if row.get("set_key") in seen_sets:
            raise InvalidInput("set_keyが重複しています")
        seen_sets.add(row.get("set_key"))
        partitions = _validate_partition_set(row, index)
        for partition in sorted(partitions, key=lambda value: value["partition_key"]):
            all_partitions.append((row, partition))
    targets: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []
    for set_row, partition in all_partitions:
        representative, is_unresolved = _representative(partition, partition["definition"], f"{set_row['set_key']}:{partition['partition_key']}")
        if is_unresolved:
            unresolved.append({"target_key": f"ep:{set_row['set_key']}:{partition['partition_key']}", "required_information": "decimal/date/datetime range representative or step"})
            continue
        set_ref = {"key": set_row["set_key"], "label": set_row["label"]}
        partition_ref = {"key": partition["partition_key"], "label": partition["label"]}
        targets.append(
            {
                "target_key": f"ep:{set_row['set_key']}:{partition['partition_key']}",
                "set": set_ref,
                "partition": partition_ref,
                "validity": partition["validity"],
                "representative": representative,
                "authority_refs": partition["authority_refs"],
                "materializable": True,
                "execution": {"set": set_ref, "partition": partition_ref, "representative": representative},
            }
        )
    targets.sort(key=lambda row: row["target_key"])
    processed = post_process_targets(metadata["model_key"], targets)
    required = len(all_partitions)
    covered = len(processed)
    return {
        "runtime_status": "ok",
        "support_status": "supported",
        "result_status": "unresolved" if unresolved else "ready",
        "runtime_required": True,
        "deterministic_generated": True,
        "payload": {
            "targets": processed,
            "coverage_summary": {"criterion": "each-choice", "required": required, "covered": covered, "complete": required > 0 and required == covered},
            "derived": {},
            "metadata": {"coverage_mode": "each-choice"},
        },
        "issues": [
            {"issue_type": "unresolved_representative", "blocking": True, "required_information": row["required_information"], "target_key": row["target_key"], "authority_refs": []}
            for row in unresolved
        ],
    }


if __name__ == "__main__":
    raise SystemExit(
        run_cli(
            generate,
            skill=SKILL,
            generator=GENERATOR,
            generator_contract_version=GENERATOR_CONTRACT_VERSION,
            generator_path=SCRIPT_PATH,
        )
    )
