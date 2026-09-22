"""Join semantic analysis drafts with current deterministic runtime results."""

from __future__ import annotations

from pathlib import Path
import re
import sys
from typing import Any

from runtime_contract import FULL_DIGEST_RE, InvalidInput, TECHNIQUE_SLUGS, canonicalize, ensure_int, ensure_key, ensure_list, ensure_nonempty_string, make_machine_entity, reject_unknown, run_cli, validate_upstream_entities, upstream_entity_fingerprints


SKILL = "test-analysis"
GENERATOR = "analysis_entities"
GENERATOR_CONTRACT_VERSION = "analysis-entities-v1"
SCRIPT_PATH = Path(__file__).resolve()


def _runtime_refs(input_value: dict) -> list[dict[str, Any]]:
    rows = input_value.get("current_runtime_units", [])
    if not isinstance(rows, list):
        raise InvalidInput("current_runtime_unitsが不正です")
    refs = []
    seen = set()
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"skill", "runtime_unit_key", "generation_fingerprint"} or not ensure_nonempty_string(row["skill"], "current_runtime_units.skill") or not ensure_nonempty_string(row["runtime_unit_key"], "current_runtime_units.runtime_unit_key") or not FULL_DIGEST_RE.fullmatch(str(row["generation_fingerprint"])):
            raise InvalidInput("current_runtime_units rowが不正です")
        key = (row["skill"], row["runtime_unit_key"])
        if key in seen:
            raise InvalidInput("current_runtime_unitsが重複しています")
        seen.add(key)
        refs.append(canonicalize(row))
    return sorted(refs, key=lambda row: (row["skill"], row["runtime_unit_key"]))


def _string_refs(value: Any, name: str) -> list[str]:
    rows = ensure_list(value, name)
    if not all(isinstance(row, str) and row for row in rows) or len(set(rows)) != len(rows):
        raise InvalidInput(f"{name}が不正です")
    return rows


def _context(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise InvalidInput("test_analysis_contextが不正です")
    fields = {"scope", "objectives", "test_levels", "environment_constraints", "exclusions", "blockers", "test_focus_items", "testability_decisions", "residual_risks"}
    reject_unknown(value, fields)
    if not isinstance(value["scope"], str) or not value["scope"]:
        raise InvalidInput("test_analysis_context.scopeが不正です")
    for field in fields - {"scope"}:
        _string_refs(value[field], f"test_analysis_context.{field}")
    return canonicalize(value)


def _risk_entities(rows: Any, results: dict[str, dict], upstream: list[dict], runtime_refs: list[dict]) -> list[dict]:
    entities = []
    seen = set()
    for index, row in enumerate(ensure_list(rows, "product_risks")):
        if not isinstance(row, dict):
            raise InvalidInput("product risk rowが不正です")
        required = {"risk_id", "failure", "source_refs", "authority_refs", "impact", "likelihood", "assessment_reason", "confidence_note"}
        reject_unknown(row, required)
        risk_id = ensure_nonempty_string(row["risk_id"], f"product_risks[{index}].risk_id")
        if risk_id in seen or risk_id not in results:
            raise InvalidInput("product riskとrisk_matrix resultが1対1ではありません")
        if not isinstance(row["failure"], str) or not row["failure"] or not isinstance(row["assessment_reason"], str) or not row["assessment_reason"] or not isinstance(row["confidence_note"], str) or not row["confidence_note"]:
            raise InvalidInput("product riskの意味fieldが不正です")
        _string_refs(row["source_refs"], f"product_risks[{index}].source_refs")
        _string_refs(row["authority_refs"], f"product_risks[{index}].authority_refs")
        ensure_int(row["impact"], f"product_risks[{index}].impact")
        ensure_int(row["likelihood"], f"product_risks[{index}].likelihood")
        seen.add(risk_id)
        joined = {**row, "level": results[risk_id]["level"], "mapped_priority": results[risk_id]["mapped_priority"]}
        dependencies = [ref for ref in upstream if ref["entity_type"] == "authority" and ref["entity_ref"] in set(row["authority_refs"] + row["source_refs"])]
        entities.append(make_machine_entity(SKILL, "product_risk", risk_id, joined, upstream_entity_dependencies=dependencies, runtime_dependencies=runtime_refs))
    if seen != set(results):
        raise InvalidInput("risk_matrix resultにunknown / missing riskがあります")
    return entities


def _selection_entities(rows: Any, results: dict[str, dict], upstream: list[dict], runtime_refs: list[dict]) -> list[dict]:
    entities = []
    seen = set()
    for index, row in enumerate(ensure_list(rows, "technique_selections")):
        if not isinstance(row, dict):
            raise InvalidInput("technique selection rowが不正です")
        required = {"selection_key", "applicability_scope", "selection_source", "signals", "selected_techniques", "selection_reason", "risk_refs", "authority_refs", "condition_design_focus", "undetermined_signal_closures", "status"}
        reject_unknown(row, required)
        key = ensure_key(row["selection_key"], f"technique_selections[{index}].selection_key")
        if key in seen or key not in results:
            raise InvalidInput("technique selectionとcandidate resultが1対1ではありません")
        seen.add(key)
        if not isinstance(row["applicability_scope"], str) or not row["applicability_scope"] or row["selection_source"] not in {"analysis", "condition_design", "user"} or not isinstance(row["signals"], dict) or not isinstance(row["selection_reason"], str) or not row["selection_reason"] or row["status"] not in {"active", "blocked", "unresolved"}:
            raise InvalidInput("technique selectionの意味fieldが不正です")
        signal_keys = {"ordered_domain", "explicit_boundaries", "equivalence_classes", "multiple_discrete_conditions", "stateful", "multiple_factors", "explicit_flow", "multi_variable_domain", "crud_model", "operational_profile", "metamorphic_relation", "grammar_model"}
        if set(row["signals"]) != signal_keys or any(value not in {True, False, None} for value in row["signals"].values()):
            raise InvalidInput("technique selection signalsが不正です")
        selected = _string_refs(row["selected_techniques"], f"technique_selections[{index}].selected_techniques")
        if len(set(selected)) != len(selected) or any(value not in TECHNIQUE_SLUGS for value in selected):
            raise InvalidInput("selected_techniquesが不正です")
        _string_refs(row["risk_refs"], f"technique_selections[{index}].risk_refs")
        _string_refs(row["authority_refs"], f"technique_selections[{index}].authority_refs")
        _string_refs(row["condition_design_focus"], f"technique_selections[{index}].condition_design_focus")
        result = results[key]
        undetermined = result["undetermined_signals"]
        closures = row["undetermined_signal_closures"]
        if not isinstance(closures, list) or len(closures) != len(undetermined) or {item.get("signal_key") for item in closures if isinstance(item, dict)} != set(undetermined):
            raise InvalidInput("undetermined signal closureがresultと一致しません")
        closure_keys = set()
        for closure in closures:
            if not isinstance(closure, dict) or set(closure) != {"signal_key", "handling", "reason", "question_id"} or closure["handling"] not in {"selection_not_affected", "question"}:
                raise InvalidInput("selection closure schemaが不正です")
            if closure["signal_key"] in closure_keys:
                raise InvalidInput("selection closureが重複しています")
            closure_keys.add(closure["signal_key"])
            if closure["handling"] == "selection_not_affected" and (not isinstance(closure["reason"], str) or not closure["reason"] or closure["question_id"] is not None):
                raise InvalidInput("selection_not_affected closureが不正です")
            if closure["handling"] == "question" and (not isinstance(closure["reason"], str) or not closure["reason"] or not isinstance(closure["question_id"], str) or re.fullmatch(r"Q-\d{3}", closure["question_id"]) is None):
                raise InvalidInput("question closureが不正です")
        if row["status"] == "active" and any(closure["handling"] == "question" for closure in closures):
            raise InvalidInput("question closureを含むselectionはactiveにできません")
        dependencies = [ref for ref in upstream if (ref["entity_type"] == "authority" and ref["entity_ref"] in set(row["authority_refs"])) or (ref["entity_type"] == "product_risk" and ref["entity_ref"] in set(row["risk_refs"]))]
        entities.append(make_machine_entity(SKILL, "technique_selection", key, {**row, "candidates": result["candidates"], "undetermined_signals": undetermined}, upstream_entity_dependencies=dependencies, runtime_dependencies=runtime_refs))
    if seen != set(results):
        raise InvalidInput("technique candidate resultにunknown / missing selectionがあります")
    return entities


def _graph_entities(nodes: Any, edges: Any, runtime_refs: list[dict]) -> list[dict]:
    entities = []
    node_keys = set()
    for index, row in enumerate(ensure_list(nodes, "change_nodes")):
        if not isinstance(row, dict):
            raise InvalidInput("change node rowが不正です")
        reject_unknown(row, {"node_key", "node_type", "source_ref", "change_kind", "expected_impact"})
        key = ensure_nonempty_string(row["node_key"], f"change_nodes[{index}].node_key")
        if key in node_keys or row["node_type"] not in {"Authority", "Risk", "TR", "TCN", "CI", "TC"} or not isinstance(row["source_ref"], str) or not row["source_ref"] or row["change_kind"] not in {"新規", "変更", "削除", "回帰影響", "参考", None} or (row["expected_impact"] is not None and (not isinstance(row["expected_impact"], str) or not row["expected_impact"])):
            raise InvalidInput("change node keyが重複しています")
        node_keys.add(key)
        entities.append(make_machine_entity(SKILL, "change_node", key, row, runtime_dependencies=runtime_refs))
    edge_keys = set()
    for index, row in enumerate(ensure_list(edges, "change_edges")):
        if not isinstance(row, dict):
            raise InvalidInput("change edge rowが不正です")
        reject_unknown(row, {"edge_key", "from", "to", "edge_type", "evidence_refs"})
        key = ensure_nonempty_string(row["edge_key"], f"change_edges[{index}].edge_key")
        if key in edge_keys or row["from"] not in node_keys or row["to"] not in node_keys or row["edge_type"] not in {"depends_on", "traces_to", "derived_from"} or not isinstance(row["evidence_refs"], list) or not all(isinstance(value, str) and value for value in row["evidence_refs"]) or len(set(row["evidence_refs"])) != len(row["evidence_refs"]):
            raise InvalidInput("change edge referenceが不正です")
        edge_keys.add(key)
        entities.append(make_machine_entity(SKILL, "change_edge", key, row, runtime_dependencies=runtime_refs))
    return entities


def generate(input_value: dict, metadata: dict) -> dict:
    if metadata["runtime_unit_key"] != "artifact:analysis_entities:all":
        raise InvalidInput("analysis_entities runtime unitが不正です")
    required = {"test_analysis_context", "product_risks", "technique_selections", "change_nodes", "change_edges", "environment_requirements", "risk_matrix_results", "technique_candidate_results"}
    reject_unknown(input_value, required, {"current_runtime_units"})
    context = _context(input_value["test_analysis_context"])
    runtime_refs = _runtime_refs(input_value)
    risk_results = {}
    for row in ensure_list(input_value["risk_matrix_results"], "risk_matrix_results"):
        if not isinstance(row, dict) or set(row) != {"risk_id", "level", "mapped_priority"} or row["risk_id"] in risk_results:
            raise InvalidInput("risk_matrix_results schemaが不正です")
        risk_results[row["risk_id"]] = canonicalize(row)
    candidate_results = {}
    for row in ensure_list(input_value["technique_candidate_results"], "technique_candidate_results"):
        if not isinstance(row, dict) or set(row) != {"selection_key", "candidates", "undetermined_signals"} or row["selection_key"] in candidate_results:
            raise InvalidInput("technique_candidate_results schemaが不正です")
        candidate_results[row["selection_key"]] = canonicalize(row)
    upstream_entities = upstream_entity_fingerprints(validate_upstream_entities(metadata))
    entities = _graph_entities(input_value["change_nodes"], input_value["change_edges"], runtime_refs)
    entities.extend(_risk_entities(input_value["product_risks"], risk_results, upstream_entities, runtime_refs))
    entities.extend(_selection_entities(input_value["technique_selections"], candidate_results, upstream_entities, runtime_refs))
    environment_keys = set()
    for index, row in enumerate(ensure_list(input_value["environment_requirements"], "environment_requirements")):
        if not isinstance(row, dict):
            raise InvalidInput(f"environment_requirements[{index}]が不正です")
        required_env = {"requirement_key", "environment_key", "dimension_key", "operator", "authority_refs", "source_model_key", "source_target_versions"}
        reject_unknown(row, required_env, {"value", "values", "minimum", "maximum", "minimum_inclusive", "maximum_inclusive"})
        key = ensure_key(row["requirement_key"], f"environment_requirements[{index}].requirement_key")
        if key in environment_keys or not ensure_key(row["environment_key"], f"environment_requirements[{index}].environment_key") or not ensure_key(row["dimension_key"], f"environment_requirements[{index}].dimension_key") or row["operator"] not in {"eq", "enum", "range", "version_range", "boolean"} or row["source_model_key"] is not None or row["source_target_versions"] != []:
            raise InvalidInput("environment requirement schemaが不正です")
        _string_refs(row["authority_refs"], f"environment_requirements[{index}].authority_refs")
        environment_keys.add(key)
        dependencies = [ref for ref in upstream_entities if ref["entity_type"] == "authority" and ref["entity_ref"] in set(row["authority_refs"])]
        entities.append(make_machine_entity(SKILL, "environment_requirement", key, row, upstream_entity_dependencies=dependencies, runtime_dependencies=runtime_refs))
    entities.append(make_machine_entity(SKILL, "test_analysis_context", "analysis-context:all", context, runtime_dependencies=runtime_refs))
    entities.sort(key=lambda row: (row["entity_type"], row["entity_ref"]))
    expected_sources = [("test_analysis_context", "analysis-context:all")]
    expected_sources.extend(("product_risk", row["risk_id"]) for row in ensure_list(input_value["product_risks"], "product_risks"))
    expected_sources.extend(("technique_selection", row["selection_key"]) for row in ensure_list(input_value["technique_selections"], "technique_selections"))
    expected_sources.extend(("change_node", row["node_key"]) for row in ensure_list(input_value["change_nodes"], "change_nodes"))
    expected_sources.extend(("change_edge", row["edge_key"]) for row in ensure_list(input_value["change_edges"], "change_edges"))
    expected_sources.extend(("environment_requirement", row["requirement_key"]) for row in ensure_list(input_value["environment_requirements"], "environment_requirements"))
    identities = [{"skill": SKILL, "entity_type": entity_type, "entity_ref": entity_ref} for entity_type, entity_ref in sorted(expected_sources)]
    return {"runtime_status": "ok", "support_status": "supported", "result_status": "ready", "runtime_required": True, "deterministic_generated": True, "payload": {"machine_entities": entities, "expected_entity_identities": identities}, "issues": []}


if __name__ == "__main__":
    raise SystemExit(run_cli(generate, skill=SKILL, generator=GENERATOR, generator_contract_version=GENERATOR_CONTRACT_VERSION, generator_path=SCRIPT_PATH))
