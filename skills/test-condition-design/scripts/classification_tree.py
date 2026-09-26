"""Adapt a normalized Classification Tree into a combinatorial child input."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from runtime_contract import (
    InvalidInput,
    canonical_json_bytes,
    canonicalize,
    ensure_int,
    ensure_key,
    ensure_list,
    ensure_nonempty_string,
    post_process_targets,
    reject_unknown,
    run_cli,
    typed_sort_key,
    typed_value,
)


SKILL = "test-condition-design"
GENERATOR = "classification_tree"
GENERATOR_CONTRACT_VERSION = "classification-tree-v1"
SCRIPT_PATH = Path(__file__).resolve()


def _refs(value: Any, name: str) -> list[str]:
    if not isinstance(value, list) or len(set(value)) != len(value) or not all(isinstance(item, str) and item for item in value):
        raise InvalidInput(f"{name}が不正です")
    return sorted(value)


def _source_key(factors: list[dict[str, Any]]) -> str:
    digest = hashlib.sha256(canonical_json_bytes(canonicalize({"factor_keys": [row["factor_key"] for row in factors]}))).hexdigest()
    return "class:h" + digest


def _validate_combinatorial_input(input_value: dict[str, Any]) -> None:
    """Validate the child contract without importing the child generator.

    The child runtime performs its own generation later.  The adapter only
    validates the semantic parameter boundary so a malformed child request is
    not emitted as a seemingly valid derived model.
    """
    reject_unknown(input_value, {"mode", "factors", "constraints"}, {"base_assignment", "strength", "global_strength", "subsets", "coverage_selection_reason"})
    mode = input_value.get("mode")
    if mode not in {"exhaustive", "base-choice", "t-wise", "mixed-strength"}:
        raise InvalidInput("combinatorial modeが不正です")
    factor_rows = ensure_list(input_value.get("factors"), "factors")
    if not factor_rows:
        raise InvalidInput("factorsは1件以上必要です")
    factor_map: dict[str, set[str]] = {}
    for row in factor_rows:
        if not isinstance(row, dict):
            raise InvalidInput("factorが不正です")
        reject_unknown(row, {"factor_key", "label", "values", "authority_refs"})
        key = ensure_key(row.get("factor_key"), "factor_key")
        if key in factor_map:
            raise InvalidInput("factor_keyが重複しています")
        values = ensure_list(row.get("values"), "factor.values")
        if not values:
            raise InvalidInput("factor valuesは1件以上必要です")
        normalized = [typed_value(value) for value in values]
        if len({canonical_json_bytes(value) for value in normalized}) != len(normalized):
            raise InvalidInput("factor valueが重複しています")
        factor_map[key] = {canonical_json_bytes(value).decode("utf-8") for value in normalized}
    constraints = ensure_list(input_value.get("constraints"), "constraints")
    constraint_keys: set[str] = set()
    for row in constraints:
        if not isinstance(row, dict):
            raise InvalidInput("constraintが不正です")
        reject_unknown(row, {"constraint_key", "assignment", "authority_refs"})
        key = ensure_key(row.get("constraint_key"), "constraint_key")
        if key in constraint_keys:
            raise InvalidInput("constraint_keyが重複しています")
        constraint_keys.add(key)
        assignment = row.get("assignment")
        if not isinstance(assignment, dict) or not assignment:
            raise InvalidInput("constraint assignmentは1件以上必要です")
        for factor_key, value in assignment.items():
            if factor_key not in factor_map or canonical_json_bytes(typed_value(value)).decode("utf-8") not in factor_map[factor_key]:
                raise InvalidInput("constraintがfactor domainを参照しています")
    factor_count = len(factor_map)
    allowed = {
        "exhaustive": {"mode", "factors", "constraints"},
        "base-choice": {"mode", "factors", "constraints", "base_assignment"},
        "t-wise": {"mode", "factors", "constraints", "strength", "coverage_selection_reason"},
        "mixed-strength": {"mode", "factors", "constraints", "global_strength", "subsets", "coverage_selection_reason"},
    }[mode]
    if set(input_value) - allowed:
        raise InvalidInput("combinatorial modeに不要なfieldがあります")
    if mode == "base-choice":
        base = input_value.get("base_assignment")
        if not isinstance(base, dict) or set(base) != set(factor_map):
            raise InvalidInput("base_assignmentは全factorを持つ必要があります")
        for key, value in base.items():
            if canonical_json_bytes(typed_value(value)).decode("utf-8") not in factor_map[key]:
                raise InvalidInput("base_assignment valueがfactor domainにありません")
    elif mode == "t-wise":
        strength = ensure_int(input_value.get("strength"), "strength", minimum=2, maximum=factor_count)
        reason = input_value.get("coverage_selection_reason")
        if strength > 2 and (not isinstance(reason, str) or not reason.strip()):
            raise InvalidInput("strength>2ではcoverage_selection_reasonが必要です")
    elif mode == "mixed-strength":
        global_strength = ensure_int(input_value.get("global_strength"), "global_strength", minimum=2, maximum=factor_count)
        subsets = ensure_list(input_value.get("subsets"), "subsets")
        if not subsets:
            raise InvalidInput("mixed-strength subsetsは1件以上必要です")
        seen: set[tuple[str, ...]] = set()
        maximum = global_strength
        for row in subsets:
            if not isinstance(row, dict):
                raise InvalidInput("subsetが不正です")
            reject_unknown(row, {"factor_keys", "strength"})
            keys = ensure_list(row.get("factor_keys"), "subset.factor_keys")
            if len(keys) < 2 or len(set(keys)) != len(keys) or any(key not in factor_map for key in keys):
                raise InvalidInput("subset.factor_keysが不正です")
            normalized_keys = tuple(sorted(keys))
            if normalized_keys in seen:
                raise InvalidInput("subsetが重複しています")
            seen.add(normalized_keys)
            strength = ensure_int(row.get("strength"), "subset.strength", minimum=2, maximum=len(keys))
            maximum = max(maximum, strength)
        reason = input_value.get("coverage_selection_reason")
        if maximum > 2 and (not isinstance(reason, str) or not reason.strip()):
            raise InvalidInput("strength>2ではcoverage_selection_reasonが必要です")


def generate(input_value: dict, metadata: dict) -> dict:
    if metadata["model_key"] is None or metadata["model_type"] != "classification" or metadata["runtime_unit_key"] != f"model:{metadata['model_key']}":
        raise InvalidInput("Classification Treeのruntime metadataが不正です")
    reject_unknown(input_value, {"classifications", "constraints", "child_models"})
    classification_rows = ensure_list(input_value["classifications"], "classifications")
    constraints = ensure_list(input_value["constraints"], "constraints")
    children = ensure_list(input_value["child_models"], "child_models")
    if len(children) != 1:
        raise InvalidInput("Classification Tree child_modelsは1件だけ必要です")
    child = children[0]
    if not isinstance(child, dict):
        raise InvalidInput("child modelが不正です")
    reject_unknown(child, {"child_model_key", "model_type", "derived_from_model_key", "semantic_parameters"})
    child_key = ensure_key(child["child_model_key"], "child_model_key")
    if child["model_type"] != "comb" or child["derived_from_model_key"] != metadata["model_key"]:
        raise InvalidInput("Classification Tree child metadataが不正です")

    classifications: list[dict[str, Any]] = []
    factors: list[dict[str, Any]] = []
    classification_keys: set[str] = set()
    for index, row in enumerate(classification_rows):
        if not isinstance(row, dict):
            raise InvalidInput(f"classifications[{index}]が不正です")
        reject_unknown(row, {"classification_key", "label", "classes", "authority_refs"})
        classification_key = ensure_key(row["classification_key"], "classification_key")
        if classification_key in classification_keys:
            raise InvalidInput("classification_keyが重複しています")
        classification_keys.add(classification_key)
        class_rows = ensure_list(row["classes"], "classification.classes")
        if not class_rows:
            raise InvalidInput("classification classesは1件以上必要です")
        classes: list[dict[str, Any]] = []
        class_keys: set[str] = set()
        value_keys: set[str] = set()
        for class_index, class_row in enumerate(class_rows):
            if not isinstance(class_row, dict):
                raise InvalidInput("classが不正です")
            reject_unknown(class_row, {"class_key", "value", "authority_refs"})
            class_key = ensure_key(class_row["class_key"], "class_key")
            if class_key in class_keys:
                raise InvalidInput("class_keyが重複しています")
            class_keys.add(class_key)
            value = typed_value(class_row["value"])
            value_text = canonical_json_bytes(value)
            if value_text in value_keys:
                raise InvalidInput("同一classification内のclass valueが重複しています")
            value_keys.add(value_text)
            classes.append({"class_key": class_key, "value": value, "authority_refs": _refs(class_row["authority_refs"], "class authority_refs")})
        classes.sort(key=lambda row: row["class_key"])
        authority_refs = sorted(set(_refs(row["authority_refs"], "classification authority_refs")) | {ref for class_row in classes for ref in class_row["authority_refs"]})
        normalized = {"classification_key": classification_key, "label": ensure_nonempty_string(row["label"], "classification label"), "classes": classes, "authority_refs": authority_refs}
        classifications.append(normalized)
        factors.append({"factor_key": classification_key, "label": normalized["label"], "values": [class_row["value"] for class_row in classes], "authority_refs": authority_refs})
    classifications.sort(key=lambda row: row["classification_key"])
    factors.sort(key=lambda row: row["factor_key"])

    base_child = {"mode": "exhaustive", "factors": factors, "constraints": constraints}
    _validate_combinatorial_input(base_child)

    semantic = child["semantic_parameters"]
    child_models = [{"child_model_key": child_key, "model_type": "comb", "derived_from_model_key": metadata["model_key"], "semantic_parameters": canonicalize(semantic) if semantic is not None else None}]
    source_key = _source_key(factors)
    requests: list[dict[str, Any]] = []
    derived: list[dict[str, Any]] = []
    issues: list[dict[str, Any]] = []
    if semantic is None:
        requests.append({"child_model_key": child_key, "model_type": "comb", "source_key": source_key, "required_fields": ["mode", "strategy parameters"]})
    else:
        if not isinstance(semantic, dict):
            raise InvalidInput("semantic_parametersが不正です")
        if set(semantic) - {"mode", "strength", "global_strength", "subsets", "base_assignment", "coverage_selection_reason"}:
            raise InvalidInput("Classification Tree semantic_parametersに未知fieldがあります")
        child_input = {"mode": semantic.get("mode"), "factors": factors, "constraints": constraints}
        for field in ("base_assignment", "strength", "coverage_selection_reason", "global_strength", "subsets"):
            if field in semantic:
                child_input[field] = semantic[field]
        _validate_combinatorial_input(child_input)
        derived.append({"child_model_key": child_key, "model_type": "comb", "input": child_input})

    targets: list[dict[str, Any]] = []
    for classification in classifications:
        for class_row in classification["classes"]:
            targets.append({
                "target_key": f"class:{classification['classification_key']}:{class_row['class_key']}",
                "classification_key": classification["classification_key"], "class_key": class_row["class_key"], "value": class_row["value"],
                "materializable": False, "execution": None, "authority_refs": sorted(set(classification["authority_refs"]) | set(class_row["authority_refs"])),
            })
    targets = post_process_targets(metadata["model_key"], sorted(targets, key=lambda row: row["target_key"]))
    return {
        "runtime_status": "ok", "support_status": "supported", "result_status": "ready" if not requests else "unresolved", "runtime_required": True, "deterministic_generated": True,
        "payload": {
            "classifications": classifications, "factors": factors, "constraints": canonicalize(constraints), "child_models": child_models,
            "targets": targets, "semantic_parameter_requests": requests, "derived_child_inputs": derived,
        },
        "issues": issues,
    }


if __name__ == "__main__":
    raise SystemExit(run_cli(generate, skill=SKILL, generator=GENERATOR, generator_contract_version=GENERATOR_CONTRACT_VERSION, generator_path=SCRIPT_PATH))
