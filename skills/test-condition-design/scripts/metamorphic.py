"""Normalize metamorphic relations and apply the fixed transform subset."""

from __future__ import annotations

import copy
import re
from pathlib import Path
from typing import Any

from runtime_contract import (
    ExactNumber,
    InvalidInput,
    canonical_decimal,
    canonicalize,
    ensure_key,
    ensure_list,
    ensure_nonempty_string,
    exact_add,
    exact_compare,
    exact_multiply,
    make_unsupported_item,
    post_process_targets,
    reject_unknown,
    run_cli,
    typed_value,
)


SKILL = "test-condition-design"
GENERATOR = "metamorphic"
GENERATOR_CONTRACT_VERSION = "metamorphic-v1"
SCRIPT_PATH = Path(__file__).resolve()
IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_-]*$")
INDEX_RE = re.compile(r"^(0|[1-9][0-9]*)$")
OUTPUT_KINDS = {"integer", "decimal", "scalar", "unique_scalar_array", "canonical_json"}


class PathIssue(Exception):
    def __init__(self, reason_code: str) -> None:
        self.reason_code = reason_code
        super().__init__(reason_code)


def _refs(value: Any, name: str) -> list[str]:
    if not isinstance(value, list) or len(set(value)) != len(value) or not all(isinstance(item, str) and item for item in value):
        raise InvalidInput(f"{name}が不正です")
    return sorted(value)


def _path_tokens(path: Any) -> list[tuple[str, Any]]:
    if not isinstance(path, str) or not path.startswith("$"):
        raise PathIssue("unsupported_path")
    if path == "$":
        return []
    tokens: list[tuple[str, Any]] = []
    index = 1
    while index < len(path):
        if path[index] == ".":
            match = re.match(r"\.([A-Za-z_][A-Za-z0-9_-]*)", path[index:])
            if match is None:
                raise PathIssue("unsupported_path")
            tokens.append(("key", match.group(1)))
            index += len(match.group(0))
        elif path[index] == "[":
            end = path.find("]", index + 1)
            if end < 0:
                raise PathIssue("unsupported_path")
            raw = path[index + 1:end]
            if INDEX_RE.fullmatch(raw) is None:
                raise PathIssue("unsupported_path")
            tokens.append(("index", int(raw)))
            index = end + 1
        else:
            raise PathIssue("unsupported_path")
    return tokens


def _resolve(root: Any, tokens: list[tuple[str, Any]]) -> tuple[Any, tuple[str, Any] | None]:
    if not tokens:
        return root, None
    current = root
    for kind, value in tokens[:-1]:
        if kind == "key":
            if not isinstance(current, dict) or value not in current:
                raise PathIssue("unsupported_path")
            current = current[value]
        else:
            if not isinstance(current, list) or value >= len(current):
                raise PathIssue("unsupported_path")
            current = current[value]
    return current, tokens[-1]


def _get(root: Any, tokens: list[tuple[str, Any]]) -> Any:
    current = root
    for kind, value in tokens:
        if kind == "key":
            if not isinstance(current, dict) or value not in current:
                raise PathIssue("unsupported_path")
            current = current[value]
        else:
            if not isinstance(current, list) or value >= len(current):
                raise PathIssue("unsupported_path")
            current = current[value]
    return current


def _set(root: Any, tokens: list[tuple[str, Any]], value: Any) -> Any:
    if not tokens:
        return value
    parent, last = _resolve(root, tokens)
    assert last is not None
    kind, key = last
    if kind == "key":
        if not isinstance(parent, dict) or key not in parent:
            raise PathIssue("unsupported_path")
        parent[key] = value
    else:
        if not isinstance(parent, list) or key >= len(parent):
            raise PathIssue("unsupported_path")
        parent[key] = value
    return root


def _scalar_kind(value: Any) -> str | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, ExactNumber)):
        return "number"
    if isinstance(value, str):
        return "string"
    return None


def _number_text(value: Any) -> str:
    if isinstance(value, ExactNumber):
        return value.text()
    return str(value)


def _apply_transform(root: Any, transform: dict[str, Any]) -> Any:
    op = transform["op"]
    tokens = _path_tokens(transform["path"])
    current = _get(root, tokens)
    if op == "set":
        return _set(root, tokens, typed_value(transform["value"]))
    if op in {"add_decimal", "multiply_decimal"}:
        if not isinstance(transform["operand"], str):
            raise InvalidInput("decimal operandはstringである必要があります")
        operand = canonical_decimal(transform["operand"])
        if not isinstance(current, dict) or set(current) != {"type", "value"} or current.get("type") != "decimal":
            raise PathIssue("unsupported_transform_type")
        current_value = canonical_decimal(current["value"])
        value = exact_add(current_value, operand) if op == "add_decimal" else exact_multiply(current_value, operand)
        return _set(root, tokens, {"type": "decimal", "value": value})
    if op == "append":
        value = canonicalize(transform["value"])
        if isinstance(current, list):
            current.append(value)
            return root
        if isinstance(current, str) and isinstance(value, str):
            return _set(root, tokens, current + value)
        raise PathIssue("unsupported_transform_type")
    if op == "permute":
        if not isinstance(current, list) or not isinstance(transform["indices"], list) or set(transform["indices"]) != set(range(len(current))) or len(transform["indices"]) != len(current):
            raise PathIssue("unsupported_transform_type")
        return _set(root, tokens, [current[index] for index in transform["indices"]])
    if op == "sort":
        if not isinstance(current, list) or transform["order"] not in {"asc", "desc"}:
            raise PathIssue("unsupported_transform_type")
        kinds = {_scalar_kind(item) for item in current}
        if len(kinds) != 1 or None in kinds:
            raise PathIssue("unsupported_transform_type")
        kind = next(iter(kinds))
        if kind == "string":
            sorted_values = sorted(current)
        else:
            sorted_values = sorted(current, key=_number_text)
            # Exact numeric order cannot use lexical text for mixed scales.
            for left_index in range(len(sorted_values)):
                for right_index in range(left_index + 1, len(sorted_values)):
                    if exact_compare(_number_text(sorted_values[left_index]), _number_text(sorted_values[right_index])) > 0:
                        sorted_values[left_index], sorted_values[right_index] = sorted_values[right_index], sorted_values[left_index]
        if transform["order"] == "desc":
            sorted_values.reverse()
        return _set(root, tokens, sorted_values)
    raise InvalidInput("transform opが不正です")


def _validate_transform(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or "op" not in value:
        raise InvalidInput("transformが不正です")
    op = value["op"]
    if op == "set":
        reject_unknown(value, {"op", "path", "value"})
        typed_value(value["value"])
    elif op in {"add_decimal", "multiply_decimal"}:
        reject_unknown(value, {"op", "path", "operand"})
        if not isinstance(value["operand"], str):
            raise InvalidInput("decimal operandが不正です")
        canonical_decimal(value["operand"])
    elif op == "append":
        reject_unknown(value, {"op", "path", "value"})
    elif op == "permute":
        reject_unknown(value, {"op", "path", "indices"})
        if not isinstance(value["indices"], list) or any(isinstance(index, bool) or not isinstance(index, int) or index < 0 for index in value["indices"]):
            raise InvalidInput("permute indicesが不正です")
    elif op == "sort":
        reject_unknown(value, {"op", "path", "order"})
        if value["order"] not in {"asc", "desc"}:
            raise InvalidInput("sort orderが不正です")
    else:
        raise InvalidInput("transform opが不正です")
    _path_tokens(value["path"])
    return canonicalize(value)


def _validate_expected(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise InvalidInput("expected_relationが不正です")
    reject_unknown(value, {"op", "output_path", "output_kind"})
    if value["op"] not in {"equal", "not_equal", "monotonic_non_decreasing", "monotonic_non_increasing", "subset", "superset"} or value["output_kind"] not in OUTPUT_KINDS:
        raise InvalidInput("expected_relation op/output_kindが不正です")
    _path_tokens(value["output_path"])
    if value["op"] in {"monotonic_non_decreasing", "monotonic_non_increasing"} and value["output_kind"] not in {"integer", "decimal"}:
        raise InvalidInput("monotonic relationとoutput_kindが不一致です")
    if value["op"] in {"subset", "superset"} and value["output_kind"] != "unique_scalar_array":
        raise InvalidInput("set relationとoutput_kindが不一致です")
    return canonicalize(value)


def generate(input_value: dict, metadata: dict) -> dict:
    if metadata["model_key"] is None or metadata["model_type"] != "metamorphic" or metadata["runtime_unit_key"] != f"model:{metadata['model_key']}":
        raise InvalidInput("Metamorphic Testingのruntime metadataが不正です")
    reject_unknown(input_value, {"relations"})
    relation_rows = ensure_list(input_value["relations"], "relations")
    if not relation_rows:
        raise InvalidInput("relationsは1件以上必要です")
    relations: list[dict[str, Any]] = []
    relation_keys: set[str] = set()
    targets: list[dict[str, Any]] = []
    unsupported_items: list[dict[str, Any]] = []
    required_pairs = 0
    generated_pairs = 0
    for index, row in enumerate(relation_rows):
        if not isinstance(row, dict):
            raise InvalidInput(f"relations[{index}]が不正です")
        reject_unknown(row, {"relation_key", "relation_label", "source_inputs", "follow_ups", "expected_relation", "authority_refs"})
        relation_key = ensure_key(row["relation_key"], "relation_key")
        if relation_key in relation_keys:
            raise InvalidInput("relation_keyが重複しています")
        relation_keys.add(relation_key)
        source_rows = ensure_list(row["source_inputs"], "source_inputs")
        follow_rows = ensure_list(row["follow_ups"], "follow_ups")
        if not source_rows or not follow_rows or len(follow_rows) > 10_000:
            raise InvalidInput("source_inputs / follow_upsの件数が不正です")
        sources: list[dict[str, Any]] = []
        source_keys: set[str] = set()
        for source in source_rows:
            if not isinstance(source, dict):
                raise InvalidInput("source inputが不正です")
            reject_unknown(source, {"source_id", "value"})
            source_id = ensure_key(source["source_id"], "source_id")
            if source_id in source_keys:
                raise InvalidInput("source_idがrelation内で重複しています")
            source_keys.add(source_id)
            sources.append({"source_id": source_id, "value": canonicalize(source["value"])})
        sources.sort(key=lambda source: source["source_id"])
        follow_ups: list[dict[str, Any]] = []
        follow_keys: set[str] = set()
        for follow in follow_rows:
            if not isinstance(follow, dict):
                raise InvalidInput("follow-upが不正です")
            reject_unknown(follow, {"follow_up_key", "transforms"})
            follow_key = ensure_key(follow["follow_up_key"], "follow_up_key")
            if follow_key in follow_keys:
                raise InvalidInput("follow_up_keyがrelation内で重複しています")
            follow_keys.add(follow_key)
            transforms = ensure_list(follow["transforms"], "follow_up.transforms")
            if not transforms:
                raise InvalidInput("follow_up.transformsは1件以上必要です")
            follow_ups.append({"follow_up_key": follow_key, "transforms": [_validate_transform(item) for item in transforms]})
        follow_ups.sort(key=lambda follow: follow["follow_up_key"])
        relation = {"relation_key": relation_key, "relation_label": ensure_nonempty_string(row["relation_label"], "relation_label"), "source_inputs": sources, "follow_ups": follow_ups, "expected_relation": _validate_expected(row["expected_relation"]), "authority_refs": _refs(row["authority_refs"], "relation authority_refs")}
        relations.append(relation)
        required_pairs += len(sources) * len(follow_ups)
        for source in sources:
            for follow in follow_ups:
                target_key = f"mr:{relation_key}:{source['source_id']}:{follow['follow_up_key']}"
                try:
                    transformed = copy.deepcopy(source["value"])
                    for transform in follow["transforms"]:
                        transformed = _apply_transform(transformed, transform)
                except PathIssue as exc:
                    unsupported_items.append(make_unsupported_item(generator=GENERATOR, item_type="metamorphic-pair", source_key=target_key, reason_code=exc.reason_code, affected_technique_slug="metamorphic", authority_refs=relation["authority_refs"]))
                    targets.append({"target_key": target_key, "relation_key": relation_key, "source_id": source["source_id"], "follow_up_key": follow["follow_up_key"], "materializable": False, "execution": None, "authority_refs": relation["authority_refs"]})
                    continue
                generated_pairs += 1
                targets.append({"target_key": target_key, "relation_key": relation_key, "source_id": source["source_id"], "follow_up_key": follow["follow_up_key"], "materializable": True, "execution": {"relation_key": relation_key, "relation_label": relation["relation_label"], "source_id": source["source_id"], "source_value": source["value"], "follow_up_key": follow["follow_up_key"], "follow_up_value": transformed, "transforms": follow["transforms"], "expected_relation": relation["expected_relation"]}, "authority_refs": relation["authority_refs"]})
    relations.sort(key=lambda relation: relation["relation_key"])
    targets = post_process_targets(metadata["model_key"], sorted(targets, key=lambda target: target["target_key"]))
    all_unsupported = bool(targets) and not generated_pairs
    partial = bool(unsupported_items) and generated_pairs > 0
    return {
        "runtime_status": "unsupported" if all_unsupported else "ok", "support_status": "unsupported" if all_unsupported else ("partial" if partial else "supported"), "result_status": "ready" if all_unsupported else ("unresolved" if generated_pairs != required_pairs else "ready"), "runtime_required": not all_unsupported, "deterministic_generated": not all_unsupported,
        "payload": {"relations": relations, "targets": targets, "unsupported_items": unsupported_items, "completion_summary": {"required_pairs": required_pairs, "generated_pairs": generated_pairs, "complete": generated_pairs == required_pairs}},
        "issues": [],
    }


if __name__ == "__main__":
    raise SystemExit(run_cli(generate, skill=SKILL, generator=GENERATOR, generator_contract_version=GENERATOR_CONTRACT_VERSION, generator_path=SCRIPT_PATH))
