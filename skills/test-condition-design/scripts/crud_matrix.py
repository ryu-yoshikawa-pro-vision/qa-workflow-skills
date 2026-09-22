"""Generate CRUD completeness and consistency coverage without guessing business meaning."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from runtime_contract import (
    InvalidInput,
    canonical_json_bytes,
    canonicalize,
    ensure_key,
    ensure_list,
    ensure_nonempty_string,
    post_process_targets,
    reject_unknown,
    run_cli,
)


SKILL = "test-condition-design"
GENERATOR = "crud_matrix"
GENERATOR_CONTRACT_VERSION = "crud-matrix-v1"
SCRIPT_PATH = Path(__file__).resolve()
OPERATIONS = ("C", "R", "U", "D")


def _refs(value: Any, name: str) -> list[str]:
    if not isinstance(value, list) or len(set(value)) != len(value) or not all(isinstance(item, str) and item for item in value):
        raise InvalidInput(f"{name}が不正です")
    return sorted(value)


def _label(value: Any, name: str) -> str:
    return ensure_nonempty_string(value, name)


def _hash_component(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(canonicalize(value))).hexdigest()


def generate(input_value: dict, metadata: dict) -> dict:
    if metadata["model_key"] is None or metadata["model_type"] != "crud" or metadata["runtime_unit_key"] != f"model:{metadata['model_key']}":
        raise InvalidInput("CRUDのruntime metadataが不正です")
    reject_unknown(input_value, {"entities", "functions", "cells", "consistency_sequences", "operation_dispositions"})
    entities_raw = ensure_list(input_value["entities"], "entities")
    functions_raw = ensure_list(input_value["functions"], "functions")
    cells_raw = ensure_list(input_value["cells"], "cells")
    sequences_raw = ensure_list(input_value["consistency_sequences"], "consistency_sequences")
    dispositions_raw = ensure_list(input_value["operation_dispositions"], "operation_dispositions")

    entities: list[dict[str, Any]] = []
    entity_map: dict[str, dict[str, Any]] = {}
    for index, row in enumerate(entities_raw):
        if not isinstance(row, dict):
            raise InvalidInput(f"entities[{index}]が不正です")
        reject_unknown(row, {"entity_key", "label", "authority_refs"})
        key = ensure_key(row["entity_key"], f"entities[{index}].entity_key")
        if key in entity_map:
            raise InvalidInput("entity_keyが重複しています")
        normalized = {"entity_key": key, "label": _label(row["label"], "entity label"), "authority_refs": _refs(row["authority_refs"], "entity authority_refs")}
        entity_map[key] = normalized
        entities.append(normalized)
    entities.sort(key=lambda row: row["entity_key"])

    functions: list[dict[str, Any]] = []
    function_map: dict[str, dict[str, Any]] = {}
    for index, row in enumerate(functions_raw):
        if not isinstance(row, dict):
            raise InvalidInput(f"functions[{index}]が不正です")
        reject_unknown(row, {"function_key", "label", "authority_refs"})
        key = ensure_key(row["function_key"], f"functions[{index}].function_key")
        if key in function_map:
            raise InvalidInput("function_keyが重複しています")
        normalized = {"function_key": key, "label": _label(row["label"], "function label"), "authority_refs": _refs(row["authority_refs"], "function authority_refs")}
        function_map[key] = normalized
        functions.append(normalized)
    functions.sort(key=lambda row: row["function_key"])

    cell_map: dict[tuple[str, str], dict[str, Any]] = {}
    cells: list[dict[str, Any]] = []
    for index, row in enumerate(cells_raw):
        if not isinstance(row, dict):
            raise InvalidInput(f"cells[{index}]が不正です")
        reject_unknown(row, {"entity_key", "function_key", "operations", "authority_refs"})
        entity_key = ensure_key(row["entity_key"], "cell.entity_key")
        function_key = ensure_key(row["function_key"], "cell.function_key")
        if entity_key not in entity_map or function_key not in function_map:
            raise InvalidInput("cellがunknown entity/functionを参照しています")
        operations = ensure_list(row["operations"], "cell.operations")
        if len(set(operations)) != len(operations) or any(operation not in OPERATIONS for operation in operations):
            raise InvalidInput("cell.operationsが不正です")
        identity = (entity_key, function_key)
        if identity in cell_map:
            raise InvalidInput("cellが重複しています")
        normalized = {"entity_key": entity_key, "function_key": function_key, "operations": sorted(operations), "authority_refs": _refs(row["authority_refs"], "cell authority_refs")}
        cell_map[identity] = normalized
        cells.append(normalized)
    cells.sort(key=lambda row: (row["entity_key"], row["function_key"]))

    dispositions: list[dict[str, Any]] = []
    disposition_map: dict[tuple[str, str], dict[str, Any]] = {}
    for index, row in enumerate(dispositions_raw):
        if not isinstance(row, dict):
            raise InvalidInput(f"operation_dispositions[{index}]が不正です")
        reject_unknown(row, {"entity_key", "operation", "handling", "reason", "authority_refs"})
        entity_key = ensure_key(row["entity_key"], "disposition.entity_key")
        operation = row["operation"]
        if entity_key not in entity_map or operation not in OPERATIONS or row["handling"] != "not_applicable":
            raise InvalidInput("operation dispositionが不正です")
        identity = (entity_key, operation)
        if identity in disposition_map:
            raise InvalidInput("operation dispositionが重複しています")
        normalized = {"entity_key": entity_key, "operation": operation, "handling": "not_applicable", "reason": _label(row["reason"], "disposition reason"), "authority_refs": _refs(row["authority_refs"], "disposition authority_refs")}
        disposition_map[identity] = normalized
        dispositions.append(normalized)
    dispositions.sort(key=lambda row: (row["entity_key"], row["operation"]))

    existing_ops: dict[str, set[str]] = {key: set() for key in entity_map}
    operation_rows: list[dict[str, Any]] = []
    for cell in cells:
        for operation in cell["operations"]:
            existing_ops[cell["entity_key"]].add(operation)
            entity = entity_map[cell["entity_key"]]
            function = function_map[cell["function_key"]]
            refs = sorted(set(entity["authority_refs"]) | set(function["authority_refs"]) | set(cell["authority_refs"]))
            operation_rows.append({
                "target_key": f"crud:op:{cell['entity_key']}:{cell['function_key']}:{operation}",
                "entity_key": cell["entity_key"], "entity_label": entity["label"], "function_key": cell["function_key"], "function_label": function["label"], "operation": operation,
                "authority_refs": refs,
                "materializable": True,
                "execution": {"entity_key": cell["entity_key"], "entity_label": entity["label"], "function_key": cell["function_key"], "function_label": function["label"], "operation": operation, "authority_refs": refs},
            })
    operation_rows.sort(key=lambda row: row["target_key"])

    missing_rows: list[dict[str, Any]] = []
    unresolved_missing: list[tuple[str, str]] = []
    for entity in entities:
        for operation in OPERATIONS:
            if operation not in existing_ops[entity["entity_key"]]:
                disposition = disposition_map.get((entity["entity_key"], operation))
                closed = disposition is not None
                if not closed:
                    unresolved_missing.append((entity["entity_key"], operation))
                missing_rows.append({
                    "target_key": f"crud:missing:{entity['entity_key']}:{operation}",
                    "entity_key": entity["entity_key"], "entity_label": entity["label"], "operation": operation,
                    "disposition": disposition,
                    "authority_refs": sorted(set(entity["authority_refs"]) | set(disposition["authority_refs"] if disposition else [])),
                    "materializable": False, "execution": None,
                })

    sequences: list[dict[str, Any]] = []
    sequence_targets: list[dict[str, Any]] = []
    sequence_issues: list[dict[str, Any]] = []
    sequence_keys: set[str] = set()
    for index, row in enumerate(sequences_raw):
        if not isinstance(row, dict):
            raise InvalidInput(f"consistency_sequences[{index}]が不正です")
        reject_unknown(row, {"sequence_key", "entity_key", "kind", "steps", "authority_refs"})
        sequence_key = ensure_key(row["sequence_key"], "sequence_key")
        if sequence_key in sequence_keys:
            raise InvalidInput("sequence_keyが重複しています")
        sequence_keys.add(sequence_key)
        entity_key = ensure_key(row["entity_key"], "sequence.entity_key")
        if entity_key not in entity_map or row["kind"] not in {"lifecycle", "negative"}:
            raise InvalidInput("sequence identityが不正です")
        steps_raw = ensure_list(row["steps"], "sequence.steps")
        if not steps_raw:
            raise InvalidInput("sequence.stepsは1件以上必要です")
        steps: list[dict[str, Any]] = []
        for step_index, step in enumerate(steps_raw):
            if not isinstance(step, dict):
                raise InvalidInput(f"sequence.steps[{step_index}]が不正です")
            reject_unknown(step, {"function_key", "operation"})
            function_key = ensure_key(step["function_key"], "sequence step.function_key")
            operation = step["operation"]
            if function_key not in function_map or operation not in OPERATIONS:
                raise InvalidInput("sequence stepが不正です")
            cell = cell_map.get((entity_key, function_key))
            if cell is None or operation not in cell["operations"]:
                raise InvalidInput("sequence stepがCRUD matrixに存在しません")
            steps.append({"function_key": function_key, "function_label": function_map[function_key]["label"], "operation": operation})
        normalized = {"sequence_key": sequence_key, "entity_key": entity_key, "entity_label": entity_map[entity_key]["label"], "kind": row["kind"], "steps": steps, "authority_refs": _refs(row["authority_refs"], "sequence authority_refs")}
        sequences.append(normalized)
        sequence_ops = {step["operation"] for step in steps}
        applicable = existing_ops[entity_key] - {operation for operation in OPERATIONS if (entity_key, operation) in disposition_map}
        missing_lifecycle = sorted(applicable - sequence_ops) if row["kind"] == "lifecycle" else []
        complete = not missing_lifecycle
        if not complete:
            sequence_issues.append({"issue_type": "incomplete_lifecycle_sequence", "blocking": True, "target_key": f"crud:seq:{sequence_key}", "authority_refs": normalized["authority_refs"], "missing_operations": missing_lifecycle})
        execution = {"sequence_key": sequence_key, "entity_key": entity_key, "entity_label": entity_map[entity_key]["label"], "kind": row["kind"], "steps": steps, "authority_refs": normalized["authority_refs"]}
        sequence_targets.append({"target_key": f"crud:seq:{sequence_key}", "sequence_key": sequence_key, "entity_key": entity_key, "kind": row["kind"], "materializable": complete, "execution": execution if complete else None, "authority_refs": normalized["authority_refs"]})
    sequences.sort(key=lambda row: row["sequence_key"])
    sequence_targets.sort(key=lambda row: row["target_key"])

    issues: list[dict[str, Any]] = []
    if unresolved_missing:
        issues.append({"issue_type": "missing_operation_disposition", "blocking": True, "target_key": None, "authority_refs": [], "required_information": "missing CRUD operationのnot_applicable disposition"})
    if not sequences:
        issues.append({"issue_type": "missing_consistency_sequence", "blocking": True, "target_key": None, "authority_refs": [], "required_information": "正規化済みCRUD consistency sequence"})
    issues.extend(sequence_issues)
    targets = post_process_targets(metadata["model_key"], operation_rows + missing_rows + sequence_targets)
    complete_operation_count = len(operation_rows) + sum(1 for row in missing_rows if row["disposition"] is not None)
    completeness = {"criterion": "crud-completeness", "required": len(operation_rows) + len(missing_rows), "covered": complete_operation_count, "complete": not unresolved_missing}
    consistency_required = len(sequences)
    consistency_covered = sum(1 for row in sequence_targets if row["materializable"])
    consistency = {"criterion": "crud-consistency", "required": consistency_required, "covered": consistency_covered, "complete": bool(sequences) and consistency_required == consistency_covered}
    overall_complete = completeness["complete"] and consistency["complete"]
    return {
        "runtime_status": "ok", "support_status": "supported", "result_status": "ready" if overall_complete else "unresolved", "runtime_required": True, "deterministic_generated": True,
        "payload": {
            "entities": entities, "functions": functions, "cells": cells, "operation_dispositions": dispositions, "consistency_sequences": sequences,
            "targets": targets, "missing_operations": missing_rows,
            "coverage_summary": {"completeness": completeness, "consistency": consistency, "complete": overall_complete},
        },
        "issues": issues,
    }


if __name__ == "__main__":
    raise SystemExit(run_cli(generate, skill=SKILL, generator=GENERATOR, generator_contract_version=GENERATOR_CONTRACT_VERSION, generator_path=SCRIPT_PATH))
