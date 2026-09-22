"""Reliable Domain Coverage using exact rational border arithmetic."""

from __future__ import annotations

from fractions import Fraction
from pathlib import Path
import sys
from typing import Any

from runtime_contract import InvalidInput, canonical_decimal, ensure_list, ensure_nonempty_string, exact_from_decimal, post_process_targets, reject_unknown, run_cli, typed_value


SKILL = "test-condition-design"
GENERATOR = "domain_testing"
GENERATOR_CONTRACT_VERSION = "domain-testing-v1"
SCRIPT_PATH = Path(__file__).resolve()
RELATIONS = {"<", "<=", ">", ">=", "=", "!="}


def _fraction(value: str) -> Fraction:
    exact = exact_from_decimal(value)
    return Fraction(exact.coefficient, 10 ** exact.scale)


def _typed_number(value: Any, name: str) -> Fraction:
    if not isinstance(value, dict) or value.get("type") not in {"integer", "decimal"}:
        raise InvalidInput(f"{name}はinteger/decimal typed valueである必要があります")
    normalized = typed_value(value)
    return Fraction(normalized["value"]) if normalized["type"] == "integer" else _fraction(normalized["value"])


def _fraction_to_typed(value: Fraction, name: str) -> dict[str, Any]:
    denominator = value.denominator
    for prime in (2, 5):
        while denominator % prime == 0:
            denominator //= prime
    if denominator != 1:
        raise InvalidInput(f"{name}がfinite decimalへ表現できません")
    scale = 0
    denominator = value.denominator
    while denominator > 1:
        if denominator % 2 == 0:
            denominator //= 2
        elif denominator % 5 == 0:
            denominator //= 5
        else:
            raise InvalidInput(f"{name}がfinite decimalへ表現できません")
        scale += 1
    coefficient = value.numerator * (10 ** scale) // value.denominator
    if scale == 0:
        return {"type": "integer", "value": value.numerator}
    sign = "-" if coefficient < 0 else ""
    body = str(abs(coefficient)).rjust(scale + 1, "0")
    text = canonical_decimal(sign + body[:-scale] + "." + body[-scale:])
    return {"type": "decimal", "value": text}


def _relation(value: Fraction, relation: str) -> bool:
    if relation == "<":
        return value < 0
    if relation == "<=":
        return value <= 0
    if relation == ">":
        return value > 0
    if relation == ">=":
        return value >= 0
    if relation == "=":
        return value == 0
    return value != 0


def _validate_expression(value: Any, border_keys: set[str], partition_key: str) -> None:
    if not isinstance(value, dict):
        raise InvalidInput("partition expressionが不正です")
    op = value.get("op")
    if op == "border_ref":
        if set(value) != {"op", "border_key"} or value["border_key"] not in border_keys:
            raise InvalidInput(f"partition {partition_key}のborder_refが不正です")
        return
    if op not in {"and", "or"} or set(value) != {"op", "args"} or not isinstance(value["args"], list) or len(value["args"]) < 1:
        raise InvalidInput(f"partition {partition_key}のexpressionが不正です")
    for child in value["args"]:
        _validate_expression(child, border_keys, partition_key)


def _eval_expression(expr: dict, point: dict[str, Fraction], borders: dict[str, dict]) -> bool:
    if expr["op"] == "border_ref":
        border = borders[expr["border_key"]]
        total = sum((_fraction(border["coefficients"].get(key, "0")) * point[key] for key in point), Fraction(0)) + _fraction(border["constant"])
        return _relation(total, border["relation"])
    values = [_eval_expression(child, point, borders) for child in expr["args"]]
    return all(values) if expr["op"] == "and" else any(values)


def _point(border: dict, base: dict[str, Fraction], offset: Fraction) -> dict[str, Fraction]:
    coefficient = _fraction(border["coefficients"][border["pivot_key"]])
    if coefficient == 0:
        raise InvalidInput("pivot coefficientが0です")
    rest = _fraction(border["constant"])
    for key, value in base.items():
        if key != border["pivot_key"]:
            rest += _fraction(border["coefficients"].get(key, "0")) * value
    pivot = (-rest / coefficient) + offset
    return {**base, border["pivot_key"]: pivot}


def _offsets(relation: str, coefficient: Fraction, step: Fraction) -> list[tuple[str, Fraction]]:
    direction = Fraction(1 if coefficient > 0 else -1)
    if relation in {"<=", ">="}:
        outward = direction if relation == "<=" else -direction
        inward = -outward
        return [("ON", Fraction(0)), ("OFF", outward * step), ("IN", inward * step), ("OUT", outward * 2 * step)]
    if relation in {"<", ">"}:
        inward = -direction if relation == "<" else direction
        outward = -inward
        return [("OFF", Fraction(0)), ("ON", inward * step), ("IN", inward * 2 * step), ("OUT", outward * step)]
    if relation == "=":
        return [("ON", Fraction(0)), ("OFF_NEG", -direction * step), ("OFF_POS", direction * step)]
    return [("OFF", Fraction(0)), ("ON_NEG", -direction * step), ("ON_POS", direction * step)]


def generate(input_value: dict, metadata: dict) -> dict:
    if metadata["model_key"] is None or metadata["model_type"] != "domain" or metadata["runtime_unit_key"] != f"model:{metadata['model_key']}":
        raise InvalidInput("domain_testingのruntime metadataが不正です")
    reject_unknown(input_value, {"partitions", "borders"})
    partitions = ensure_list(input_value["partitions"], "partitions")
    borders = ensure_list(input_value["borders"], "borders")
    if not partitions or not borders:
        raise InvalidInput("partitionsとbordersは各1件以上必要です")
    partition_map: dict[str, dict] = {}
    for index, row in enumerate(partitions):
        if not isinstance(row, dict):
            raise InvalidInput(f"partitions[{index}]が不正です")
        reject_unknown(row, {"partition_key", "label", "dimensions", "expression", "authority_refs"})
        key = ensure_nonempty_string(row["partition_key"], "partition_key")
        if key in partition_map:
            raise InvalidInput("partition_keyが重複しています")
        dimensions = ensure_list(row["dimensions"], f"partitions[{index}].dimensions")
        dim_keys = set()
        normalized_dims = []
        for dim in dimensions:
            if not isinstance(dim, dict) or set(dim) != {"dimension_key", "label"} or not isinstance(dim["label"], str) or not dim["label"]:
                raise InvalidInput("partition dimensionが不正です")
            dkey = ensure_nonempty_string(dim["dimension_key"], "dimension_key")
            if dkey in dim_keys:
                raise InvalidInput("dimension_keyが重複しています")
            dim_keys.add(dkey)
            normalized_dims.append({"dimension_key": dkey, "label": dim["label"]})
        if not normalized_dims or not isinstance(row["authority_refs"], list) or not all(isinstance(value, str) and value for value in row["authority_refs"]):
            raise InvalidInput("partition metadataが不正です")
        partition_map[key] = {**row, "partition_key": key, "dimensions": normalized_dims}
    border_map: dict[str, dict] = {}
    references: dict[str, set[str]] = {key: set() for key in partition_map}
    for index, row in enumerate(borders):
        if not isinstance(row, dict):
            raise InvalidInput(f"borders[{index}]が不正です")
        required = {"border_key", "label", "partition_key", "relation", "coefficients", "constant", "pivot_key", "anchor", "pivot_step", "authority_refs"}
        reject_unknown(row, required)
        key = ensure_nonempty_string(row["border_key"], "border_key")
        if key in border_map or row["partition_key"] not in partition_map or row["relation"] not in RELATIONS:
            raise InvalidInput("border identity/referenceが不正です")
        partition = partition_map[row["partition_key"]]
        dim_keys = {item["dimension_key"] for item in partition["dimensions"]}
        coefficients = row["coefficients"]
        if not isinstance(coefficients, dict) or not coefficients or any(dimension not in dim_keys or not isinstance(value, str) for dimension, value in coefficients.items()):
            raise InvalidInput("border coefficientsが不正です")
        for value in coefficients.values():
            canonical_decimal(value)
        if not isinstance(row["constant"], str) or not isinstance(row["pivot_step"], str):
            raise InvalidInput("border decimal fieldが不正です")
        canonical_decimal(row["constant"])
        step = _fraction(row["pivot_step"])
        if step <= 0 or row["pivot_key"] not in dim_keys or _fraction(coefficients.get(row["pivot_key"], "0")) == 0:
            raise InvalidInput("border pivotが不正です")
        anchor = row["anchor"]
        if not isinstance(anchor, dict) or any(key not in dim_keys or key == row["pivot_key"] for key in anchor):
            raise InvalidInput("border anchorが不正です")
        for dimension in dim_keys - {row["pivot_key"]}:
            if _fraction(coefficients.get(dimension, "0")) != 0 and dimension not in anchor:
                raise InvalidInput("border anchorが不足しています")
        normalized_anchor = {}
        for dimension, value in anchor.items():
            normalized_anchor[dimension] = _typed_number(value, f"anchor.{dimension}")
        if not isinstance(row["authority_refs"], list) or not all(isinstance(value, str) and value for value in row["authority_refs"]):
            raise InvalidInput("border authority_refsが不正です")
        border_map[key] = {**row, "anchor_fraction": normalized_anchor}
    for key, partition in partition_map.items():
        _validate_expression(partition["expression"], {ref for ref, border in border_map.items() if border["partition_key"] == key}, key)
        def collect(expr: dict) -> None:
            if expr["op"] == "border_ref":
                references[key].add(expr["border_key"])
            else:
                for child in expr["args"]:
                    collect(child)
        collect(partition["expression"])
    if any(not references[key] for key in references):
        raise InvalidInput("partitionがborderを参照していません")
    targets: list[dict[str, Any]] = []
    issues: list[dict[str, Any]] = []
    for border_key, border in sorted(border_map.items()):
        partition = partition_map[border["partition_key"]]
        base = {item["dimension_key"]: Fraction(0) for item in partition["dimensions"]}
        base.update(border["anchor_fraction"])
        step = _fraction(border["pivot_step"])
        coefficient = _fraction(border["coefficients"][border["pivot_key"]])
        for position, offset in _offsets(border["relation"], coefficient, step):
            point = _point(border, base, offset)
            try:
                values = {key: _fraction_to_typed(value, f"{border_key}.{key}") for key, value in point.items()}
            except InvalidInput:
                issues.append({"issue_type": "unrepresentable_point", "blocking": True, "target_key": f"domain:{partition['partition_key']}:{border_key}:{position}", "authority_refs": border["authority_refs"]})
                continue
            inside = _eval_expression(partition["expression"], point, {key: value for key, value in border_map.items() if value["partition_key"] == partition["partition_key"]})
            expected_inside = position in {"ON", "IN", "ON_NEG", "ON_POS"} if border["relation"] not in {"=", "!="} else position == "ON" if border["relation"] == "=" else position in {"ON_NEG", "ON_POS"}
            if inside != expected_inside:
                issues.append({"issue_type": "partition_membership_mismatch", "blocking": True, "target_key": f"domain:{partition['partition_key']}:{border_key}:{position}", "authority_refs": border["authority_refs"]})
                continue
            execution = {"partition": {"partition_key": partition["partition_key"], "label": partition["label"]}, "border": {"border_key": border_key, "label": border["label"], "relation": border["relation"], "pivot_key": border["pivot_key"], "authority_refs": border["authority_refs"]}, "position": position, "values": values}
            targets.append({"target_key": f"domain:{partition['partition_key']}:{border_key}:{position}", "partition_key": partition["partition_key"], "border_key": border_key, "position": position, "values": values, "authority_refs": border["authority_refs"], "materializable": True, "execution": execution})
    processed = post_process_targets(metadata["model_key"], sorted(targets, key=lambda row: row["target_key"]))
    required = sum(3 if border["relation"] in {"=", "!="} else 4 for border in border_map.values())
    return {"runtime_status": "ok", "support_status": "supported", "result_status": "unresolved" if issues else "ready", "runtime_required": True, "deterministic_generated": True, "payload": {"targets": processed, "coverage_summary": {"criterion": "reliable-domain", "required": required, "covered": len(processed), "complete": not issues and required == len(processed)}}, "issues": issues}


if __name__ == "__main__":
    raise SystemExit(run_cli(generate, skill=SKILL, generator=GENERATOR, generator_contract_version=GENERATOR_CONTRACT_VERSION, generator_path=SCRIPT_PATH))
