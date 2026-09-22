"""Deterministically expand a Cause-Effect boolean graph into Decision Table input."""

from __future__ import annotations

import hashlib
from itertools import product
from pathlib import Path
from typing import Any

from runtime_contract import (
    InvalidInput,
    MAX_EXPLORATION_NODES,
    canonical_json_bytes,
    canonical_json_text,
    canonicalize,
    ensure_list,
    ensure_nonempty_string,
    post_process_targets,
    reject_unknown,
    run_cli,
    typed_sort_key,
    typed_value,
)


SKILL = "test-condition-design"
GENERATOR = "cause_effect"
GENERATOR_CONTRACT_VERSION = "cause-effect-v1"
SCRIPT_PATH = Path(__file__).resolve()
MAX_ASSIGNMENTS = 65_536


def _refs(value: Any, name: str) -> list[str]:
    if not isinstance(value, list) or len(set(value)) != len(value) or not all(isinstance(item, str) and item for item in value):
        raise InvalidInput(f"{name}が不正です")
    return sorted(value)


def _key(value: Any, name: str) -> str:
    return ensure_nonempty_string(value, name)


def _hash_component(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(canonicalize(value))).hexdigest()


def _validate_expression(value: Any, cause_keys: set[str], *, depth: int = 0) -> dict[str, Any]:
    if depth > 64 or not isinstance(value, dict):
        raise InvalidInput("Cause-Effect expressionが不正です")
    op = value.get("op")
    if op == "ref":
        reject_unknown(value, {"op", "key"})
        key = _key(value["key"], "expression.key")
        if key not in cause_keys:
            raise InvalidInput("expressionがunknown causeを参照しています")
        return {"op": "ref", "key": key}
    if op == "not":
        reject_unknown(value, {"op", "arg"})
        return {"op": "not", "arg": _validate_expression(value["arg"], cause_keys, depth=depth + 1)}
    if op in {"and", "or"}:
        reject_unknown(value, {"op", "args"})
        args = ensure_list(value["args"], "expression.args")
        if len(args) < 2:
            raise InvalidInput("and/or expressionは2項以上必要です")
        return {"op": op, "args": [_validate_expression(arg, cause_keys, depth=depth + 1) for arg in args]}
    raise InvalidInput("Cause-Effect expression opが不正です")


def _eval_expression(expression: dict[str, Any], assignment: dict[str, bool]) -> bool:
    op = expression["op"]
    if op == "ref":
        return assignment[expression["key"]]
    if op == "not":
        return not _eval_expression(expression["arg"], assignment)
    values = [_eval_expression(arg, assignment) for arg in expression["args"]]
    return all(values) if op == "and" else any(values)


def _normalize(input_value: dict[str, Any], metadata: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    reject_unknown(input_value, {"causes", "effects", "constraints", "child_models"})
    causes_raw = ensure_list(input_value["causes"], "causes")
    effects_raw = ensure_list(input_value["effects"], "effects")
    constraints_raw = ensure_list(input_value["constraints"], "constraints")
    children_raw = ensure_list(input_value["child_models"], "child_models")
    if len(children_raw) != 1:
        raise InvalidInput("Cause-Effect child_modelsは1件だけ必要です")
    child = children_raw[0]
    if not isinstance(child, dict):
        raise InvalidInput("child modelが不正です")
    reject_unknown(child, {"child_model_key", "model_type", "derived_from_model_key", "semantic_parameters"})
    child_key = _key(child["child_model_key"], "child_model_key")
    if child["model_type"] != "decision" or child["derived_from_model_key"] != metadata["model_key"] or child["semantic_parameters"] is not None:
        raise InvalidInput("Cause-Effect child model metadataが不正です")
    child = {"child_model_key": child_key, "model_type": "decision", "derived_from_model_key": metadata["model_key"], "semantic_parameters": None}

    causes: list[dict[str, Any]] = []
    cause_keys: set[str] = set()
    for index, row in enumerate(causes_raw):
        if not isinstance(row, dict):
            raise InvalidInput(f"causes[{index}]が不正です")
        reject_unknown(row, {"cause_key", "label", "authority_refs"})
        key = _key(row["cause_key"], f"causes[{index}].cause_key")
        if key in cause_keys:
            raise InvalidInput("cause_keyが重複しています")
        cause_keys.add(key)
        causes.append({"cause_key": key, "label": ensure_nonempty_string(row["label"], "cause label"), "authority_refs": _refs(row["authority_refs"], "cause authority_refs")})
    causes.sort(key=lambda row: row["cause_key"])

    effects: list[dict[str, Any]] = []
    effect_keys: set[str] = set()
    for index, row in enumerate(effects_raw):
        if not isinstance(row, dict):
            raise InvalidInput(f"effects[{index}]が不正です")
        reject_unknown(row, {"effect_key", "label", "expression", "true_value", "false_value", "authority_refs"})
        key = _key(row["effect_key"], f"effects[{index}].effect_key")
        if key in effect_keys:
            raise InvalidInput("effect_keyが重複しています")
        effect_keys.add(key)
        effects.append({
            "effect_key": key,
            "label": ensure_nonempty_string(row["label"], "effect label"),
            "expression": _validate_expression(row["expression"], cause_keys),
            "true_value": typed_value(row["true_value"]),
            "false_value": typed_value(row["false_value"]),
            "authority_refs": _refs(row["authority_refs"], "effect authority_refs"),
        })
    effects.sort(key=lambda row: row["effect_key"])

    constraints: list[dict[str, Any]] = []
    constraint_keys: set[str] = set()
    for index, row in enumerate(constraints_raw):
        if not isinstance(row, dict):
            raise InvalidInput(f"constraints[{index}]が不正です")
        reject_unknown(row, {"constraint_key", "assignment", "authority_refs"})
        key = _key(row["constraint_key"], f"constraints[{index}].constraint_key")
        if key in constraint_keys:
            raise InvalidInput("constraint_keyが重複しています")
        constraint_keys.add(key)
        assignment = row["assignment"]
        if not isinstance(assignment, dict) or not assignment:
            raise InvalidInput("constraint assignmentは1件以上必要です")
        normalized: dict[str, dict[str, Any]] = {}
        for cause_key, raw_value in assignment.items():
            if cause_key not in cause_keys:
                raise InvalidInput("constraintがunknown causeを参照しています")
            value = typed_value(raw_value)
            if value["type"] != "boolean":
                raise InvalidInput("Cause-Effect constraint valueはbooleanである必要があります")
            normalized[cause_key] = value
        constraints.append({"constraint_key": key, "assignment": {item: normalized[item] for item in sorted(normalized)}, "authority_refs": _refs(row["authority_refs"], "constraint authority_refs")})
    constraints.sort(key=lambda row: row["constraint_key"])
    return causes, effects, constraints, [child], {row["cause_key"]: row for row in causes}


def _matches(assignment: dict[str, bool], constraint: dict[str, Any]) -> bool:
    return all(assignment[key] == value["value"] for key, value in constraint["assignment"].items())


def generate(input_value: dict, metadata: dict) -> dict:
    if metadata["model_key"] is None or metadata["model_type"] != "cause-effect" or metadata["runtime_unit_key"] != f"model:{metadata['model_key']}":
        raise InvalidInput("Cause-Effectのruntime metadataが不正です")
    causes, effects, constraints, child_models, _cause_map = _normalize(input_value, metadata)
    assignment_count = 2 ** len(causes)
    if assignment_count > MAX_ASSIGNMENTS or assignment_count > MAX_EXPLORATION_NODES:
        raise InvalidInput("Cause-Effect assignment spaceがhard limitを超えています")
    cause_keys = [row["cause_key"] for row in causes]
    conditions = [{"condition_key": row["cause_key"], "label": row["label"], "values": [{"type": "boolean", "value": False}, {"type": "boolean", "value": True}], "authority_refs": row["authority_refs"]} for row in causes]
    actions = [{"action_key": row["effect_key"], "label": row["label"], "values": [row["false_value"], row["true_value"]] if row["false_value"] != row["true_value"] else [row["false_value"]], "authority_refs": row["authority_refs"]} for row in effects]
    actions = [{**row, "values": sorted(row["values"], key=typed_sort_key)} for row in actions]
    known_rules: list[dict[str, Any]] = []
    targets: list[dict[str, Any]] = []
    for index, values in enumerate(product([False, True], repeat=len(cause_keys)), start=1):
        assignment = {key: {"type": "boolean", "value": value} for key, value in zip(cause_keys, values)}
        plain_assignment = {key: value for key, value in zip(cause_keys, values)}
        if any(_matches(plain_assignment, constraint) for constraint in constraints):
            continue
        then = {}
        for effect in effects:
            enabled = _eval_expression(effect["expression"], plain_assignment)
            then[effect["effect_key"]] = effect["true_value"] if enabled else effect["false_value"]
        rule_key = f"CE-{len(known_rules) + 1:03d}"
        refs = sorted({ref for row in causes for ref in row["authority_refs"] if row["cause_key"] in assignment} | {ref for row in effects for ref in row["authority_refs"]})
        rule = {"rule_key": rule_key, "when": assignment, "then": then, "authority_refs": refs}
        known_rules.append(rule)
        target_key = "ce:h" + hashlib.sha256(canonical_json_bytes(canonicalize({"assignment": assignment}))).hexdigest()
        targets.append({
            "target_key": target_key,
            "assignment": assignment,
            "action_vector": then,
            "rule_key": rule_key,
            "authority_refs": refs,
            # Cause-Effect is an adapter.  Its decision child owns the
            # materializable Coverage target; the adapter itself never becomes
            # a CI source.
            "materializable": False,
            "execution": None,
        })
    known_rules.sort(key=lambda row: canonical_json_text(row["when"]))
    for index, rule in enumerate(known_rules, start=1):
        rule["rule_key"] = f"CE-{index:03d}"
    # Keep target execution rule keys aligned with the deterministic sorted rule list.
    by_assignment = {canonical_json_text(rule["when"]): rule["rule_key"] for rule in known_rules}
    for target in targets:
        key = canonical_json_text(target["assignment"])
        target["rule_key"] = by_assignment[key]
    targets = post_process_targets(metadata["model_key"], sorted(targets, key=lambda row: row["target_key"]))
    child_input = {"conditions": conditions, "actions": actions, "known_rules": known_rules, "constraints": constraints, "accepted_merges": []}
    return {
        "runtime_status": "ok", "support_status": "supported", "result_status": "ready", "runtime_required": True, "deterministic_generated": True,
        "payload": {
            "causes": causes, "effects": effects, "constraints": constraints, "child_models": child_models,
            "conditions": conditions, "actions": actions, "known_rules": known_rules, "targets": targets,
            "derived_child_inputs": [{"child_model_key": child_models[0]["child_model_key"], "model_type": "decision", "input": child_input}],
            "semantic_parameter_requests": [],
            "coverage_summary": {"criterion": "cause-effect-feasible-assignments", "required": len(known_rules), "covered": len(known_rules), "complete": True},
        },
        "issues": [],
    }


if __name__ == "__main__":
    raise SystemExit(run_cli(generate, skill=SKILL, generator=GENERATOR, generator_contract_version=GENERATOR_CONTRACT_VERSION, generator_path=SCRIPT_PATH))
