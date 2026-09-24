"""Aggregate deterministic runtime and Machine Entity state for qa-workflow."""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Any

from runtime_contract import (
    FULL_DIGEST_RE,
    InvalidInput,
    _default_expected_runtime_units,
    _expected_entities,
    canonical_json_text,
    canonicalize,
    evaluate_entity_freshness,
    evaluate_materialize_completion,
    evaluate_target_disposition_closure,
    evaluate_runtime_unit_freshness,
    ensure_list,
    ensure_nonempty_string,
    entity_identity,
    reject_unknown,
    run_cli,
    validate_unsupported_item_closures,
    validate_entity_collection,
)


SKILL = "qa-workflow"
GENERATOR = "workflow_runtime"
GENERATOR_CONTRACT_VERSION = "workflow-runtime-v1"
SCRIPT_PATH = Path(__file__).resolve()


def _scope_rows(value: Any) -> list[dict[str, Any]]:
    rows = ensure_list(value, "workflow_scopes")
    result = []
    seen: set[tuple[str, str, str]] = set()
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise InvalidInput(f"workflow_scopes[{index}]が不正です")
        reject_unknown(row, {"skill", "target", "execution_range", "input_mode", "normalized_input", "current_structure_state"})
        skill = ensure_nonempty_string(row["skill"], f"workflow_scopes[{index}].skill")
        if skill == "qa-workflow":
            raise InvalidInput("workflow scopeへqa-workflow自身を含められません")
        if row["input_mode"] not in {"artifact", "direct"} or not isinstance(row["normalized_input"], dict):
            raise InvalidInput("workflow scope inputが不正です")
        for field in ("target", "execution_range"):
            if row[field] is not None and (not isinstance(row[field], str) or not row[field].strip()):
                raise InvalidInput(f"workflow scope {field}が不正です")
        if row["current_structure_state"] is not None and not isinstance(row["current_structure_state"], dict):
            raise InvalidInput("workflow scope current_structure_stateが不正です")
        identity = (skill, str(row["target"]), str(row["execution_range"]))
        if identity in seen:
            raise InvalidInput("workflow scopeが重複しています")
        seen.add(identity)
        result.append(canonicalize(row))
    return result


def _runtime_rows(value: Any, name: str) -> list[dict[str, Any]]:
    rows = ensure_list(value, name)
    result = []
    seen: set[tuple[str, str]] = set()
    required = {"skill", "runtime_unit_key", "model_key", "support_status", "result_status", "runtime_status", "runtime_required", "deterministic_generated", "generation_fingerprint", "upstream_entity_fingerprints", "upstream_runtime_units", "unsupported_items", "freshness_status", "model_completion", "target_mappings", "target_dispositions"}
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise InvalidInput(f"{name}[{index}]が不正です")
        if not required.issubset(row):
            raise InvalidInput(f"{name}[{index}]のruntime rowが不足しています")
        skill = ensure_nonempty_string(row["skill"], f"{name}[{index}].skill")
        unit = ensure_nonempty_string(row["runtime_unit_key"], f"{name}[{index}].runtime_unit_key")
        identity = (skill, unit)
        if identity[0] == SKILL or identity in seen:
            raise InvalidInput(f"{name}のruntime identityが重複または不正です")
        seen.add(identity)
        if row["model_key"] is not None and (not isinstance(row["model_key"], str) or not unit.startswith("model:")):
            raise InvalidInput(f"{name}[{index}]のmodel identityが不正です")
        if unit.startswith("model:") and row["model_key"] != unit.split(":", 1)[1]:
            raise InvalidInput(f"{name}[{index}]のmodel_keyが不一致です")
        if not unit.startswith("model:") and row["model_key"] is not None:
            raise InvalidInput(f"{name}[{index}]のartifact model_keyはnullである必要があります")
        if not FULL_DIGEST_RE.fullmatch(str(row["generation_fingerprint"])):
            raise InvalidInput(f"{name}[{index}]のgeneration_fingerprintが不正です")
        if row["freshness_status"] not in {"current", "stale"}:
            raise InvalidInput("freshness_statusが不正です")
        if row["result_status"] not in {"ready", "unresolved", "blocked"} or row["support_status"] not in {"supported", "partial", "unsupported", "unknown"} or row["runtime_status"] not in {"ok", "invalid_input", "unsupported", "limit_exceeded", "internal_error", "not_run"}:
            raise InvalidInput("runtime row statusが不正です")
        if not isinstance(row["runtime_required"], bool) or not isinstance(row["deterministic_generated"], bool):
            raise InvalidInput("runtime row booleanが不正です")
        for field in ("upstream_entity_fingerprints", "upstream_runtime_units", "unsupported_items", "model_completion", "target_mappings", "target_dispositions"):
            if not isinstance(row[field], list):
                raise InvalidInput(f"{name}[{index}].{field}はarrayである必要があります")
        if not unit.startswith("artifact:materialize_coverage:") and any(row[field] for field in ("model_completion", "target_mappings", "target_dispositions")):
            raise InvalidInput("materialize以外のruntime unitはcoverage projectionを持てません")
        result.append(canonicalize(row))
    return result


def _current_runtime_rows(value: Any) -> list[dict[str, Any]]:
    rows = ensure_list(value, "current_runtime_units")
    projected: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict) or not {"skill", "runtime_unit_key", "generation_fingerprint"}.issubset(row):
            raise InvalidInput(f"current_runtime_units[{index}]のidentityが不正です")
        normalized = dict(row)
        normalized.setdefault("model_key", normalized["runtime_unit_key"].split(":", 1)[1] if str(normalized["runtime_unit_key"]).startswith("model:") else None)
        normalized.setdefault("support_status", "supported")
        normalized.setdefault("result_status", "ready")
        normalized.setdefault("runtime_status", "ok")
        normalized.setdefault("runtime_required", True)
        normalized.setdefault("deterministic_generated", True)
        normalized.setdefault("upstream_entity_fingerprints", [])
        normalized.setdefault("upstream_runtime_units", [])
        normalized.setdefault("unsupported_items", [])
        normalized.setdefault("freshness_status", "current")
        normalized.setdefault("model_completion", [])
        normalized.setdefault("target_mappings", [])
        normalized.setdefault("target_dispositions", [])
        projected.append(normalized)
    return _runtime_rows(projected, "current_runtime_units")


def _entity_rows(value: Any) -> list[dict[str, Any]]:
    rows = ensure_list(value, "current_entities")
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("skill"), str):
            raise InvalidInput("current_entities rowが不正です")
        grouped.setdefault(row["skill"], []).append(row)
    result = []
    for skill, skill_rows in grouped.items():
        result.extend(validate_entity_collection(skill_rows, expected_skill=skill))
    return sorted(result, key=lambda row: entity_identity(row["skill"], row["entity_type"], row["entity_ref"]))


def _build(input_value: dict[str, Any], metadata: dict[str, Any]) -> dict[str, Any]:
    reject_unknown(input_value, {"workflow_scopes", "runtime_units", "current_entities", "current_runtime_units", "unsupported_item_closures"})
    scopes = _scope_rows(input_value["workflow_scopes"])
    if not scopes:
        raise InvalidInput("本Plan対象scopeがないworkflowではworkflow_runtimeをdispatchできません")
    runtime_rows = _runtime_rows(input_value["runtime_units"], "runtime_units")
    current_runtime_rows = _current_runtime_rows(input_value["current_runtime_units"])
    entities = _entity_rows(input_value["current_entities"])
    closures, closure_issues = validate_unsupported_item_closures(
        input_value["unsupported_item_closures"],
        runtime_rows,
        entities,
        normalized=[scope["normalized_input"] for scope in scopes],
    )

    expected_units: list[dict[str, Any]] = []
    expected_entities: list[dict[str, str]] = []
    for scope in scopes:
        scope_skill = scope["skill"]
        normalized = scope["normalized_input"]
        expected_units.extend(_default_expected_runtime_units(
            scope_skill,
            normalized,
            "",
            current_structure_state=scope["current_structure_state"],
            current_runtime_units=current_runtime_rows,
        ))
        expected_entities.extend(_expected_entities(
            scope_skill,
            normalized,
            current_structure_state=scope["current_structure_state"],
        ))
    expected_unit_keys = sorted({(row["skill"], row["runtime_unit_key"]) for row in expected_units})
    actual_unit_keys = sorted((row["skill"], row["runtime_unit_key"]) for row in runtime_rows)
    missing_units = [list(value) for value in sorted(set(expected_unit_keys) - set(actual_unit_keys))]
    extra_units = [list(value) for value in sorted(set(actual_unit_keys) - set(expected_unit_keys))]
    fresh_rows, freshness_issues = evaluate_runtime_unit_freshness(runtime_rows, current_runtime_rows, entities)
    current_generation = {(row["skill"], row["runtime_unit_key"]): row.get("generation_fingerprint") for row in current_runtime_rows}
    for row in fresh_rows:
        key = (row["skill"], row["runtime_unit_key"])
        if current_generation.get(key) != row.get("generation_fingerprint"):
            row["freshness_status"] = "stale"
            freshness_issues.append({"issue_type": "current_runtime_generation_mismatch", "blocking": True, "runtime_unit_key": row["runtime_unit_key"], "skill": row["skill"]})
    entity_freshness = evaluate_entity_freshness(entities, {(row["skill"], row["runtime_unit_key"]): row for row in current_runtime_rows})
    entity_status = {(row["skill"], row["entity_type"], row["entity_ref"]): row for row in entity_freshness}
    for row in fresh_rows:
        for dependency in row["upstream_entity_fingerprints"]:
            entity_key = (dependency.get("skill"), dependency.get("entity_type"), dependency.get("entity_ref"))
            if entity_status.get(entity_key, {}).get("freshness_status") == "stale":
                row["freshness_status"] = "stale"
                freshness_issues.append({"issue_type": "stale_entity_propagation", "blocking": True, "runtime_unit_key": row["runtime_unit_key"], "skill": row["skill"], "entity": list(entity_key)})
    expected_entity_keys = sorted((row["skill"], row["entity_type"], row["entity_ref"]) for row in expected_entities)
    actual_entity_keys = sorted((row["skill"], row["entity_type"], row["entity_ref"]) for row in entities)
    missing_entities = [list(value) for value in sorted(set(expected_entity_keys) - set(actual_entity_keys))]
    extra_entities = [list(value) for value in sorted(set(actual_entity_keys) - set(expected_entity_keys))]
    issues = []
    if missing_units:
        issues.append({"issue_type": "missing_runtime_unit", "blocking": True, "runtime_units": missing_units})
    if extra_units:
        issues.append({"issue_type": "extra_runtime_unit", "blocking": True, "runtime_units": extra_units})
    if missing_entities:
        issues.append({"issue_type": "missing_entity", "blocking": True, "entities": missing_entities})
    if extra_entities:
        issues.append({"issue_type": "extra_entity", "blocking": True, "entities": extra_entities})
    for row in entity_freshness:
        if row["freshness_status"] == "stale":
            issues.append({
                "issue_type": "stale_entity", "blocking": True,
                "skill": row["skill"], "entity_type": row["entity_type"], "entity_ref": row["entity_ref"],
                "stale_reasons": row["stale_reasons"],
            })
    issues.extend(freshness_issues)
    issues.extend(closure_issues)
    issues.extend(evaluate_target_disposition_closure(runtime_rows, entities))
    for scope in scopes:
        issues.extend(evaluate_materialize_completion(scope["normalized_input"], runtime_rows, entities, closures))
    if any(row.get("handling") == "ブロック中" for row in closures):
        issues.append({"issue_type": "unsupported_closure_blocked", "blocking": True})
    for row in fresh_rows:
        if row["result_status"] != "ready" or row["freshness_status"] != "current" or (row["runtime_required"] and not row["deterministic_generated"]):
            issues.append({"issue_type": "runtime_not_complete", "blocking": True, "skill": row["skill"], "runtime_unit_key": row["runtime_unit_key"]})
    issues_by_key = {canonical_json_text(row): row for row in issues}
    issues = [issues_by_key[key] for key in sorted(issues_by_key)]
    can_complete = not issues and bool(scopes)
    return {
        "runtime_status": "ok",
        "support_status": "supported",
        "result_status": "ready" if can_complete else "unresolved",
        "runtime_required": True,
        "deterministic_generated": True,
        "payload": {
            "expected_runtime_units": expected_units,
            "runtime_units": fresh_rows,
            "expected_entities": expected_entities,
            "current_entities": entities,
            "missing_runtime_units": missing_units,
            "extra_runtime_units": extra_units,
            "missing_entities": missing_entities,
            "extra_entities": extra_entities,
            "runtime_freshness": [{"skill": row["skill"], "runtime_unit_key": row["runtime_unit_key"], "freshness_status": row["freshness_status"]} for row in fresh_rows],
            "entity_freshness": entity_freshness,
            "unsupported_item_closures": canonicalize(closures),
            "can_complete": can_complete,
        },
        "issues": issues,
    }


def handler(input_value: dict[str, Any], metadata: dict[str, Any]) -> dict[str, Any]:
    if metadata["model_key"] is not None or metadata["runtime_unit_key"] != "artifact:workflow_runtime:all" or metadata["scope_key"] != "all":
        raise InvalidInput("workflow_runtimeのruntime metadataが不正です")
    return _build(input_value, metadata)


if __name__ == "__main__":
    raise SystemExit(
        run_cli(
            handler,
            skill=SKILL,
            generator=GENERATOR,
            generator_contract_version=GENERATOR_CONTRACT_VERSION,
            generator_path=SCRIPT_PATH,
            aggregate=True,
        )
    )
