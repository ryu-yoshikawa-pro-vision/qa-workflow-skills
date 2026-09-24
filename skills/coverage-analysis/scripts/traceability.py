"""Deterministic test-design traceability and freshness analysis."""

from __future__ import annotations

from pathlib import Path
import re
from typing import Any

from runtime_contract import (
    FULL_DIGEST_RE,
    InvalidInput,
    _default_expected_runtime_units,
    _expected_entities,
    canonical_json_text,
    canonicalize,
    ensure_list,
    ensure_nonempty_string,
    entity_identity,
    evaluate_entity_freshness,
    evaluate_materialize_completion,
    evaluate_target_disposition_closure,
    evaluate_runtime_unit_freshness,
    reject_unknown,
    run_cli,
    validate_unsupported_item_closures,
    validate_entity_collection,
)


SKILL = "coverage-analysis"
GENERATOR = "traceability"
GENERATOR_CONTRACT_VERSION = "traceability-v1"
SCRIPT_PATH = Path(__file__).resolve()
NODE_TYPES = {"Authority", "Risk", "TR", "TCN", "CI", "TC"}
ALLOWED_EDGES = {("Authority", "TR"), ("Risk", "TR"), ("TR", "TCN"), ("TCN", "CI"), ("CI", "TC"), ("TCN", "TC")}
HANDLINGS = {"対象外", "別テストレベル", "残存リスク", "ブロック中", "重複"}
SELF_UNITS = {(SKILL, "artifact:traceability:all"), ("qa-workflow", "artifact:workflow_runtime:all")}


def _scope_rows(value: Any) -> list[dict[str, Any]]:
    rows = ensure_list(value, "analysis_scopes")
    result: list[dict[str, Any]] = []
    seen: set[tuple[str, Any, Any]] = set()
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise InvalidInput(f"analysis_scopes[{index}]が不正です")
        fields = {"skill", "target", "execution_range", "input_mode", "normalized_input", "current_structure_state"}
        reject_unknown(row, fields)
        if set(row) != fields:
            raise InvalidInput("analysis_scopeの必須fieldが不足しています")
        skill = ensure_nonempty_string(row["skill"], "analysis_scope.skill")
        if skill in {SKILL, "qa-workflow"}:
            raise InvalidInput("traceability自身またはqa-workflowをanalysis scopeへ指定できません")
        if row["input_mode"] not in {"direct", "artifact"} or not isinstance(row["normalized_input"], dict):
            raise InvalidInput("analysis_scope inputが不正です")
        if row["target"] is not None and (not isinstance(row["target"], str) or not row["target"].strip()):
            raise InvalidInput("analysis_scope targetが不正です")
        if row["execution_range"] is not None and (not isinstance(row["execution_range"], str) or not row["execution_range"].strip()):
            raise InvalidInput("analysis_scope execution_rangeが不正です")
        if row["current_structure_state"] is not None and not isinstance(row["current_structure_state"], dict):
            raise InvalidInput("analysis_scope current_structure_stateが不正です")
        identity = (skill, row["target"], row["execution_range"])
        if identity in seen:
            raise InvalidInput("analysis_scopeが重複しています")
        seen.add(identity)
        result.append(canonicalize(row))
    return sorted(result, key=lambda row: (row["skill"], str(row["target"]), str(row["execution_range"])))


def _nodes(value: Any) -> tuple[list[dict[str, Any]], dict[str, str]]:
    result: list[dict[str, Any]] = []
    kinds: dict[str, str] = {}
    for index, row in enumerate(ensure_list(value, "nodes")):
        if not isinstance(row, dict) or set(row) != {"node_key", "node_type"}:
            raise InvalidInput(f"nodes[{index}]のschemaが不正です")
        key = ensure_nonempty_string(row["node_key"], "node.node_key")
        if row["node_type"] not in NODE_TYPES or key in kinds:
            raise InvalidInput("node identityが不正または重複しています")
        kinds[key] = row["node_type"]
        result.append({"node_key": key, "node_type": row["node_type"]})
    return sorted(result, key=lambda row: row["node_key"]), kinds


def _edges(value: Any, kinds: dict[str, str]) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for index, row in enumerate(ensure_list(value, "edges")):
        if not isinstance(row, dict) or set(row) != {"from", "to"}:
            raise InvalidInput(f"edges[{index}]のschemaが不正です")
        source = ensure_nonempty_string(row["from"], "edge.from")
        target = ensure_nonempty_string(row["to"], "edge.to")
        pair = (source, target)
        if source not in kinds or target not in kinds or pair in seen or (kinds[source], kinds[target]) not in ALLOWED_EDGES:
            raise InvalidInput("traceability edgeがunknown / duplicate / 不許可です")
        seen.add(pair)
        result.append({"from": source, "to": target})
    return sorted(result, key=lambda row: (row["from"], row["to"]))


def _runtime_rows(value: Any, name: str) -> list[dict[str, Any]]:
    required = {"skill", "runtime_unit_key", "model_key", "support_status", "result_status", "runtime_status", "runtime_required", "deterministic_generated", "generation_fingerprint", "upstream_entity_fingerprints", "upstream_runtime_units", "unsupported_items", "freshness_status", "model_completion", "target_mappings", "target_dispositions"}
    rows = ensure_list(value, name)
    result: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for index, row in enumerate(rows):
        if not isinstance(row, dict) or not required.issubset(row):
            raise InvalidInput(f"{name}[{index}]のruntime rowが不足しています")
        skill = ensure_nonempty_string(row["skill"], f"{name}.skill")
        unit = ensure_nonempty_string(row["runtime_unit_key"], f"{name}.runtime_unit_key")
        identity = (skill, unit)
        if identity in SELF_UNITS:
            raise InvalidInput("traceability / workflow_runtime自身をruntime集合へ含められません")
        if identity in seen:
            raise InvalidInput(f"{name}のruntime identityが重複しています")
        if row["support_status"] not in {"supported", "partial", "unsupported", "unknown"} or row["result_status"] not in {"ready", "unresolved", "blocked"} or row["runtime_status"] not in {"ok", "invalid_input", "unsupported", "limit_exceeded", "internal_error", "not_run"}:
            raise InvalidInput("runtime row statusが不正です")
        if row["freshness_status"] not in {"current", "stale"} or not isinstance(row["runtime_required"], bool) or not isinstance(row["deterministic_generated"], bool) or not FULL_DIGEST_RE.fullmatch(str(row["generation_fingerprint"])):
            raise InvalidInput("runtime row fingerprint/statusが不正です")
        for field in ("upstream_entity_fingerprints", "upstream_runtime_units", "unsupported_items", "model_completion", "target_mappings", "target_dispositions"):
            if not isinstance(row[field], list):
                raise InvalidInput(f"{name}.{field}がarrayではありません")
        seen.add(identity)
        result.append(canonicalize(row))
    return sorted(result, key=lambda row: (row["skill"], row["runtime_unit_key"]))


def _entity_rows(value: Any) -> list[dict[str, Any]]:
    rows = ensure_list(value, "current_entities")
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("skill"), str):
            raise InvalidInput("current_entities rowが不正です")
        grouped.setdefault(row["skill"], []).append(row)
    result: list[dict[str, Any]] = []
    for skill, skill_rows in grouped.items():
        result.extend(validate_entity_collection(skill_rows, expected_skill=skill))
    return sorted(result, key=lambda row: (row["skill"], row["entity_type"], row["entity_ref"]))


def _dispositions(value: Any, entities: dict[tuple[str, str, str], dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for index, row in enumerate(ensure_list(value, "dispositions")):
        required = {"upstream_entity", "handling", "reason", "authority_refs", "covered_by_entity"}
        if not isinstance(row, dict) or set(row) != required:
            raise InvalidInput(f"dispositions[{index}]のschemaが不正です")
        upstream = row["upstream_entity"]
        if not isinstance(upstream, dict) or set(upstream) != {"skill", "entity_type", "entity_ref", "content_fingerprint"} or not FULL_DIGEST_RE.fullmatch(str(upstream["content_fingerprint"])):
            raise InvalidInput("disposition upstream_entityが不正です")
        key = entity_identity(upstream["skill"], upstream["entity_type"], upstream["entity_ref"])
        if key in seen or key not in entities or entities[key]["content_fingerprint"] != upstream["content_fingerprint"]:
            raise InvalidInput("disposition upstream Entityがunknownまたはstaleです")
        if row["handling"] not in HANDLINGS or not isinstance(row["reason"], str) or not row["reason"].strip() or not isinstance(row["authority_refs"], list) or len(set(row["authority_refs"])) != len(row["authority_refs"]) or not all(isinstance(item, str) and item for item in row["authority_refs"]):
            raise InvalidInput("disposition handling/reason/authority_refsが不正です")
        covered = row["covered_by_entity"]
        if row["handling"] == "重複":
            if not isinstance(covered, dict) or set(covered) != {"skill", "entity_type", "entity_ref", "content_fingerprint"}:
                raise InvalidInput("重複 disposition covered_by_entityが不正です")
            covered_key = entity_identity(covered["skill"], covered["entity_type"], covered["entity_ref"])
            if covered_key == key or covered_key not in entities or entities[covered_key]["content_fingerprint"] != covered["content_fingerprint"]:
                raise InvalidInput("重複 dispositionの参照Entityが不正です")
        elif covered is not None:
            raise InvalidInput("重複以外のcovered_by_entityはnullである必要があります")
        seen.add(key)
        result.append(canonicalize(row))
    return sorted(result, key=lambda row: (row["upstream_entity"]["skill"], row["upstream_entity"]["entity_type"], row["upstream_entity"]["entity_ref"]))


def _graph_issues(nodes: list[dict[str, Any]], kinds: dict[str, str], edges: list[dict[str, str]], dispositions: list[dict[str, Any]], runtime_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    incoming: dict[str, set[str]] = {row["node_key"]: set() for row in nodes}
    outgoing: dict[str, set[str]] = {row["node_key"]: set() for row in nodes}
    for edge in edges:
        incoming[edge["to"]].add(edge["from"])
        outgoing[edge["from"]].add(edge["to"])
    disposed = {row["upstream_entity"]["entity_ref"] for row in dispositions}
    active_coverage_models = 0
    for runtime in runtime_rows:
        if runtime["runtime_unit_key"].startswith("artifact:materialize_coverage:"):
            active_coverage_models += sum(1 for row in runtime["model_completion"] if isinstance(row, dict) and row.get("model_key"))
    issues: list[dict[str, Any]] = []
    for node in nodes:
        key, node_type = node["node_key"], node["node_type"]
        if node_type in {"TR", "TCN", "CI", "TC"} and key not in disposed and not incoming[key]:
            issues.append({"issue_type": "orphan_node", "blocking": True, "node_key": key, "node_type": node_type})
        if node_type == "TR" and not (incoming[key] & {source for source, kind in kinds.items() if kind in {"Authority", "Risk"}}) and key not in disposed:
            issues.append({"issue_type": "missing_authority_or_risk_edge", "blocking": True, "node_key": key})
        if node_type == "TCN" and not (incoming[key] & {source for source, kind in kinds.items() if kind == "TR"}) and key not in disposed:
            issues.append({"issue_type": "missing_tr_edge", "blocking": True, "node_key": key})
        if node_type == "CI" and not (incoming[key] & {source for source, kind in kinds.items() if kind == "TCN"}) and key not in disposed:
            issues.append({"issue_type": "missing_tcn_edge", "blocking": True, "node_key": key})
        if node_type == "TC" and not (incoming[key] & {source for source, kind in kinds.items() if kind in {"CI", "TCN"}}) and key not in disposed:
            issues.append({"issue_type": "missing_ci_edge", "blocking": True, "node_key": key})
    for source, kind in kinds.items():
        if kind == "TCN" and active_coverage_models and not outgoing[source] and source not in disposed:
            issues.append({"issue_type": "coverage_model_closure_missing", "blocking": True, "node_key": source})
    return issues


def _build(input_value: dict[str, Any], metadata: dict[str, Any]) -> dict[str, Any]:
    required = {"analysis_scopes", "nodes", "edges", "dispositions", "runtime_units", "current_entities", "current_runtime_units", "unsupported_item_closures"}
    reject_unknown(input_value, required)
    scopes = _scope_rows(input_value["analysis_scopes"])
    nodes, kinds = _nodes(input_value["nodes"])
    edges = _edges(input_value["edges"], kinds)
    entities_list = _entity_rows(input_value["current_entities"])
    entities = {entity_identity(row["skill"], row["entity_type"], row["entity_ref"]): row for row in entities_list}
    dispositions = _dispositions(input_value["dispositions"], entities)
    runtime_rows = _runtime_rows(input_value["runtime_units"], "runtime_units")
    current_runtime_rows = _runtime_rows(input_value["current_runtime_units"], "current_runtime_units")
    expected_units: list[dict[str, Any]] = []
    expected_entities: list[dict[str, str]] = []
    for scope in scopes:
        expected_units.extend(_default_expected_runtime_units(
            scope["skill"],
            scope["normalized_input"],
            "",
            current_structure_state=scope["current_structure_state"],
            current_runtime_units=current_runtime_rows,
        ))
        expected_entities.extend(_expected_entities(
            scope["skill"],
            scope["normalized_input"],
            current_structure_state=scope["current_structure_state"],
            require_carry_forward_projection=True,
        ))
    expected_unit_map = {(row["skill"], row["runtime_unit_key"]): row for row in expected_units if (row["skill"], row["runtime_unit_key"]) not in SELF_UNITS}
    expected_entity_map = {(row["skill"], row["entity_type"], row["entity_ref"]): row for row in expected_entities}
    actual_unit_keys = {(row["skill"], row["runtime_unit_key"]) for row in runtime_rows}
    expected_unit_keys = set(expected_unit_map)
    actual_entity_keys = set(entities)
    missing_units = [list(key) for key in sorted(expected_unit_keys - actual_unit_keys)]
    extra_units = [list(key) for key in sorted(actual_unit_keys - expected_unit_keys)]
    missing_entities = [list(key) for key in sorted(set(expected_entity_map) - actual_entity_keys)]
    extra_entities = [list(key) for key in sorted(actual_entity_keys - set(expected_entity_map))]
    entity_freshness = evaluate_entity_freshness(entities_list, {(row["skill"], row["runtime_unit_key"]): row for row in current_runtime_rows})
    fresh_runtime_rows, freshness_issues = evaluate_runtime_unit_freshness(runtime_rows, current_runtime_rows, entities_list)
    closures, closure_issues = validate_unsupported_item_closures(input_value["unsupported_item_closures"], current_runtime_rows, entities_list, normalized=[scope["normalized_input"] for scope in scopes])
    issues: list[dict[str, Any]] = []
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
    issues.extend(_graph_issues(nodes, kinds, edges, dispositions, current_runtime_rows))
    issues.extend(evaluate_target_disposition_closure(current_runtime_rows, entities_list))
    for scope in scopes:
        issues.extend(evaluate_materialize_completion(scope["normalized_input"], current_runtime_rows, entities_list, closures))
    for row in fresh_runtime_rows:
        if row["result_status"] != "ready" or row["freshness_status"] != "current" or (row["runtime_required"] and not row["deterministic_generated"]):
            issues.append({"issue_type": "runtime_not_complete", "blocking": True, "skill": row["skill"], "runtime_unit_key": row["runtime_unit_key"]})
    issues_by_key = {canonical_json_text(row): row for row in issues}
    issues = [issues_by_key[key] for key in sorted(issues_by_key)]
    can_complete = bool(scopes) and not issues
    return {
        "runtime_status": "ok", "support_status": "supported", "result_status": "ready" if can_complete else "unresolved", "runtime_required": True, "deterministic_generated": True,
        "payload": {
            "analysis_scopes": scopes, "nodes": nodes, "edges": edges, "dispositions": dispositions,
            "expected_runtime_units": [expected_unit_map[key] for key in sorted(expected_unit_map)],
            "expected_entities": [expected_entity_map[key] for key in sorted(expected_entity_map)],
            "runtime_units": fresh_runtime_rows, "current_entities": entities_list,
            "missing_runtime_units": missing_units, "extra_runtime_units": extra_units,
            "missing_entities": missing_entities, "extra_entities": extra_entities,
            "runtime_freshness": [{"skill": row["skill"], "runtime_unit_key": row["runtime_unit_key"], "freshness_status": row["freshness_status"]} for row in fresh_runtime_rows],
            "entity_freshness": entity_freshness, "unsupported_item_closures": closures, "can_complete": can_complete,
        },
        "issues": issues,
    }


def handler(input_value: dict[str, Any], metadata: dict[str, Any]) -> dict[str, Any]:
    if metadata["model_key"] is not None or metadata["runtime_unit_key"] != "artifact:traceability:all" or metadata["scope_key"] not in {"all", None}:
        raise InvalidInput("traceability runtime metadataが不正です")
    return _build(input_value, metadata)


if __name__ == "__main__":
    raise SystemExit(run_cli(handler, skill=SKILL, generator=GENERATOR, generator_contract_version=GENERATOR_CONTRACT_VERSION, generator_path=SCRIPT_PATH, aggregate=True))
