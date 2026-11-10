"""Deterministic test-design traceability and freshness analysis."""

from __future__ import annotations

import re
from pathlib import Path
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
    evaluate_runtime_unit_freshness,
    evaluate_target_disposition_closure,
    reject_unknown,
    run_cli,
    validate_current_structure_state,
    validate_entity_collection,
    validate_unsupported_item_closures,
)

SKILL = "coverage-analysis"
GENERATOR = "traceability"
GENERATOR_CONTRACT_VERSION = "traceability-v1"
SCRIPT_PATH = Path(__file__).resolve()
NODE_TYPES = {"Authority", "Risk", "TR", "TCN", "CI", "TC"}
ALLOWED_EDGES = {
    ("Authority", "TR"),
    ("Risk", "TR"),
    ("TR", "TCN"),
    ("TCN", "CI"),
    ("CI", "TC"),
    ("TCN", "TC"),
}
HANDLINGS = {"対象外", "別テストレベル", "残存リスク", "ブロック中", "重複"}
FORMAL_ITEM_RE = re.compile(r"^TI-\d{3,}$")
FORMAL_CONDITION_RE = re.compile(r"^COND-\d{3,}$")
FORMAL_CANDIDATE_RE = re.compile(r"^ER-\d{3,}$")
FORMAL_DECISIONS = {
    "adopted",
    "not_applicable",
    "out_of_scope",
    "other_test_level",
    "duplicate",
    "unconfirmed",
    "blocked",
}
SELF_UNITS = {
    (SKILL, "artifact:traceability:all"),
    ("qa-workflow", "artifact:workflow_runtime:all"),
}


def _scope_rows(value: Any) -> list[dict[str, Any]]:
    rows = ensure_list(value, "analysis_scopes")
    result: list[dict[str, Any]] = []
    seen: set[tuple[str, Any, Any]] = set()
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise InvalidInput(f"analysis_scopes[{index}]が不正です")
        fields = {
            "skill",
            "target",
            "execution_range",
            "input_mode",
            "normalized_input",
            "current_structure_state",
        }
        reject_unknown(row, fields)
        if set(row) != fields:
            raise InvalidInput("analysis_scopeの必須fieldが不足しています")
        skill = ensure_nonempty_string(row["skill"], "analysis_scope.skill")
        if skill in {SKILL, "qa-workflow"}:
            raise InvalidInput(
                "traceability自身またはqa-workflowをanalysis scopeへ指定できません"
            )
        if row["input_mode"] not in {"direct", "artifact"} or not isinstance(
            row["normalized_input"], dict
        ):
            raise InvalidInput("analysis_scope inputが不正です")
        if row["target"] is not None and (
            not isinstance(row["target"], str) or not row["target"].strip()
        ):
            raise InvalidInput("analysis_scope targetが不正です")
        if row["execution_range"] is not None and (
            not isinstance(row["execution_range"], str)
            or not row["execution_range"].strip()
        ):
            raise InvalidInput("analysis_scope execution_rangeが不正です")
        if row["current_structure_state"] is not None and not isinstance(
            row["current_structure_state"], dict
        ):
            raise InvalidInput("analysis_scope current_structure_stateが不正です")
        identity = (skill, row["target"], row["execution_range"])
        if identity in seen:
            raise InvalidInput("analysis_scopeが重複しています")
        seen.add(identity)
        result.append(canonicalize(row))
    return sorted(
        result,
        key=lambda row: (row["skill"], str(row["target"]), str(row["execution_range"])),
    )


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


def _edges(
    value: Any, kinds: dict[str, str], coverage_model_tcn_ids: set[str]
) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for index, row in enumerate(ensure_list(value, "edges")):
        if not isinstance(row, dict) or set(row) != {"from", "to"}:
            raise InvalidInput(f"edges[{index}]のschemaが不正です")
        source = ensure_nonempty_string(row["from"], "edge.from")
        target = ensure_nonempty_string(row["to"], "edge.to")
        pair = (source, target)
        if (
            source not in kinds
            or target not in kinds
            or pair in seen
            or (kinds[source], kinds[target]) not in ALLOWED_EDGES
        ):
            raise InvalidInput("traceability edgeがunknown / duplicate / 不許可です")
        if (
            kinds[source] == "TCN"
            and kinds[target] == "TC"
            and source in coverage_model_tcn_ids
        ):
            raise InvalidInput(
                "Coverage modelを持つTCNからTCへの直接edgeは許可されません"
            )
        seen.add(pair)
        result.append({"from": source, "to": target})
    return sorted(result, key=lambda row: (row["from"], row["to"]))


def _runtime_rows(value: Any, name: str) -> list[dict[str, Any]]:
    required = {
        "skill",
        "runtime_unit_key",
        "model_key",
        "support_status",
        "result_status",
        "runtime_status",
        "runtime_required",
        "deterministic_generated",
        "generation_fingerprint",
        "result_fingerprint",
        "upstream_entity_fingerprints",
        "upstream_runtime_units",
        "unsupported_items",
        "freshness_status",
        "model_completion",
        "target_mappings",
        "target_dispositions",
    }
    rows = ensure_list(value, name)
    result: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for index, row in enumerate(rows):
        if not isinstance(row, dict) or not required.issubset(row):
            raise InvalidInput(f"{name}[{index}]のruntime rowが不足しています")
        skill = ensure_nonempty_string(row["skill"], f"{name}.skill")
        unit = ensure_nonempty_string(
            row["runtime_unit_key"], f"{name}.runtime_unit_key"
        )
        identity = (skill, unit)
        if identity in SELF_UNITS:
            raise InvalidInput(
                "traceability / workflow_runtime自身をruntime集合へ含められません"
            )
        if identity in seen:
            raise InvalidInput(f"{name}のruntime identityが重複しています")
        if row["model_key"] is not None and (
            not isinstance(row["model_key"], str)
            or not row["model_key"].strip()
            or not unit.startswith("model:")
        ):
            raise InvalidInput(f"{name}[{index}]のmodel identityが不正です")
        if unit.startswith("model:") and row["model_key"] != unit.split(":", 1)[1]:
            raise InvalidInput(f"{name}[{index}]のmodel_keyが不一致です")
        if not unit.startswith("model:") and row["model_key"] is not None:
            raise InvalidInput(
                f"{name}[{index}]のartifact model_keyはnullである必要があります"
            )
        if (
            row["support_status"]
            not in {"supported", "partial", "unsupported", "unknown"}
            or row["result_status"] not in {"ready", "unresolved", "blocked"}
            or row["runtime_status"]
            not in {
                "ok",
                "invalid_input",
                "unsupported",
                "limit_exceeded",
                "internal_error",
                "not_run",
            }
        ):
            raise InvalidInput("runtime row statusが不正です")
        if (
            row["freshness_status"] not in {"current", "stale"}
            or not isinstance(row["runtime_required"], bool)
            or not isinstance(row["deterministic_generated"], bool)
            or not FULL_DIGEST_RE.fullmatch(str(row["generation_fingerprint"]))
            or not FULL_DIGEST_RE.fullmatch(str(row["result_fingerprint"]))
        ):
            raise InvalidInput("runtime row fingerprint/statusが不正です")
        for field in (
            "upstream_entity_fingerprints",
            "upstream_runtime_units",
            "unsupported_items",
            "model_completion",
            "target_mappings",
            "target_dispositions",
        ):
            if not isinstance(row[field], list):
                raise InvalidInput(f"{name}.{field}がarrayではありません")
        if not unit.startswith("artifact:materialize_coverage:") and any(
            row[field]
            for field in ("model_completion", "target_mappings", "target_dispositions")
        ):
            raise InvalidInput(
                "materialize以外のruntime unitはcoverage projectionを持てません"
            )
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
    return sorted(
        result, key=lambda row: (row["skill"], row["entity_type"], row["entity_ref"])
    )


def _coverage_models_by_tcn(entities: list[dict[str, Any]]) -> dict[str, list[str]]:
    models: dict[str, set[str]] = {}
    for row in entities:
        if row["entity_type"] != "model":
            continue
        content = row["content"]
        technique_slug = content.get("technique_slug")
        if technique_slug is None:
            continue
        ensure_nonempty_string(technique_slug, "Coverage model technique_slug")
        parent_tcn_id = ensure_nonempty_string(
            content.get("parent_tcn_id"), "Coverage model parent_tcn_id"
        )
        models.setdefault(parent_tcn_id, set()).add(row["entity_ref"])
    return {tcn_id: sorted(model_keys) for tcn_id, model_keys in sorted(models.items())}


def _dispositions(
    value: Any, entities: dict[tuple[str, str, str], dict[str, Any]]
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for index, row in enumerate(ensure_list(value, "dispositions")):
        required = {
            "upstream_entity",
            "handling",
            "reason",
            "authority_refs",
            "covered_by_entity",
        }
        if not isinstance(row, dict) or set(row) != required:
            raise InvalidInput(f"dispositions[{index}]のschemaが不正です")
        upstream = row["upstream_entity"]
        if (
            not isinstance(upstream, dict)
            or set(upstream)
            != {"skill", "entity_type", "entity_ref", "content_fingerprint"}
            or not FULL_DIGEST_RE.fullmatch(str(upstream["content_fingerprint"]))
        ):
            raise InvalidInput("disposition upstream_entityが不正です")
        key = entity_identity(
            upstream["skill"], upstream["entity_type"], upstream["entity_ref"]
        )
        if (
            key in seen
            or key not in entities
            or entities[key]["content_fingerprint"] != upstream["content_fingerprint"]
        ):
            raise InvalidInput("disposition upstream Entityがunknownまたはstaleです")
        if (
            row["handling"] not in HANDLINGS
            or not isinstance(row["reason"], str)
            or not row["reason"].strip()
            or not isinstance(row["authority_refs"], list)
            or len(set(row["authority_refs"])) != len(row["authority_refs"])
            or not all(isinstance(item, str) and item for item in row["authority_refs"])
        ):
            raise InvalidInput("disposition handling/reason/authority_refsが不正です")
        covered = row["covered_by_entity"]
        if row["handling"] == "重複":
            if not isinstance(covered, dict) or set(covered) != {
                "skill",
                "entity_type",
                "entity_ref",
                "content_fingerprint",
            }:
                raise InvalidInput("重複 disposition covered_by_entityが不正です")
            covered_key = entity_identity(
                covered["skill"], covered["entity_type"], covered["entity_ref"]
            )
            if (
                covered_key == key
                or covered_key not in entities
                or entities[covered_key]["content_fingerprint"]
                != covered["content_fingerprint"]
            ):
                raise InvalidInput("重複 dispositionの参照Entityが不正です")
        elif covered is not None:
            raise InvalidInput("重複以外のcovered_by_entityはnullである必要があります")
        seen.add(key)
        result.append(canonicalize(row))
    return sorted(
        result,
        key=lambda row: (
            row["upstream_entity"]["skill"],
            row["upstream_entity"]["entity_type"],
            row["upstream_entity"]["entity_ref"],
        ),
    )


def _graph_issues(
    nodes: list[dict[str, Any]],
    kinds: dict[str, str],
    edges: list[dict[str, str]],
    dispositions: list[dict[str, Any]],
    coverage_models_by_tcn: dict[str, list[str]],
) -> list[dict[str, Any]]:
    incoming: dict[str, set[str]] = {row["node_key"]: set() for row in nodes}
    outgoing: dict[str, set[str]] = {row["node_key"]: set() for row in nodes}
    for edge in edges:
        incoming[edge["to"]].add(edge["from"])
        outgoing[edge["from"]].add(edge["to"])
    disposed = {row["upstream_entity"]["entity_ref"] for row in dispositions}
    issues: list[dict[str, Any]] = []
    for node in nodes:
        key, node_type = node["node_key"], node["node_type"]
        if (
            node_type in {"TR", "TCN", "CI", "TC"}
            and key not in disposed
            and not incoming[key]
        ):
            issues.append(
                {
                    "issue_type": "orphan_node",
                    "blocking": True,
                    "node_key": key,
                    "node_type": node_type,
                }
            )
        if (
            node_type == "TR"
            and not (
                incoming[key]
                & {
                    source
                    for source, kind in kinds.items()
                    if kind in {"Authority", "Risk"}
                }
            )
            and key not in disposed
        ):
            issues.append(
                {
                    "issue_type": "missing_authority_or_risk_edge",
                    "blocking": True,
                    "node_key": key,
                }
            )
        if (
            node_type == "TCN"
            and not (
                incoming[key]
                & {source for source, kind in kinds.items() if kind == "TR"}
            )
            and key not in disposed
        ):
            issues.append(
                {"issue_type": "missing_tr_edge", "blocking": True, "node_key": key}
            )
        if (
            node_type == "CI"
            and not (
                incoming[key]
                & {source for source, kind in kinds.items() if kind == "TCN"}
            )
            and key not in disposed
        ):
            issues.append(
                {"issue_type": "missing_tcn_edge", "blocking": True, "node_key": key}
            )
        if (
            node_type == "TC"
            and not (
                incoming[key]
                & {source for source, kind in kinds.items() if kind in {"CI", "TCN"}}
            )
            and key not in disposed
        ):
            issues.append(
                {"issue_type": "missing_ci_edge", "blocking": True, "node_key": key}
            )
    for source, kind in kinds.items():
        has_ci_edge = any(kinds[target] == "CI" for target in outgoing[source])
        if (
            kind == "TCN"
            and coverage_models_by_tcn.get(source)
            and not has_ci_edge
            and source not in disposed
        ):
            issues.append(
                {
                    "issue_type": "coverage_model_closure_missing",
                    "blocking": True,
                    "node_key": source,
                }
            )
    return issues


def _build(input_value: dict[str, Any], metadata: dict[str, Any]) -> dict[str, Any]:
    required = {
        "analysis_scopes",
        "nodes",
        "edges",
        "dispositions",
        "runtime_units",
        "current_entities",
        "current_runtime_units",
        "unsupported_item_closures",
    }
    reject_unknown(input_value, required, {"formal_design_summaries"})
    scopes = _scope_rows(input_value["analysis_scopes"])
    nodes, kinds = _nodes(input_value["nodes"])
    entities_list = _entity_rows(input_value["current_entities"])
    coverage_models_by_tcn = _coverage_models_by_tcn(entities_list)
    edges = _edges(input_value["edges"], kinds, set(coverage_models_by_tcn))
    entities = {
        entity_identity(row["skill"], row["entity_type"], row["entity_ref"]): row
        for row in entities_list
    }
    dispositions = _dispositions(input_value["dispositions"], entities)
    runtime_rows = _runtime_rows(input_value["runtime_units"], "runtime_units")
    current_runtime_rows = _runtime_rows(
        input_value["current_runtime_units"], "current_runtime_units"
    )
    expected_units: list[dict[str, Any]] = []
    expected_entities: list[dict[str, str]] = []
    for scope in scopes:
        validate_current_structure_state(
            scope["skill"],
            scope["normalized_input"],
            scope["current_structure_state"],
            current_entities=entities_list,
            current_runtime_units=current_runtime_rows,
        )
        expected_units.extend(
            _default_expected_runtime_units(
                scope["skill"],
                scope["normalized_input"],
                "",
                current_structure_state=scope["current_structure_state"],
                current_runtime_units=current_runtime_rows,
            )
        )
        expected_entities.extend(
            _expected_entities(
                scope["skill"],
                scope["normalized_input"],
                current_structure_state=scope["current_structure_state"],
                require_carry_forward_projection=True,
            )
        )
    expected_unit_map = {
        (row["skill"], row["runtime_unit_key"]): row
        for row in expected_units
        if (row["skill"], row["runtime_unit_key"]) not in SELF_UNITS
    }
    expected_entity_map = {
        (row["skill"], row["entity_type"], row["entity_ref"]): row
        for row in expected_entities
    }
    actual_unit_keys = {(row["skill"], row["runtime_unit_key"]) for row in runtime_rows}
    expected_unit_keys = set(expected_unit_map)
    actual_entity_keys = set(entities)
    missing_units = [list(key) for key in sorted(expected_unit_keys - actual_unit_keys)]
    extra_units = [list(key) for key in sorted(actual_unit_keys - expected_unit_keys)]
    missing_entities = [
        list(key) for key in sorted(set(expected_entity_map) - actual_entity_keys)
    ]
    extra_entities = [
        list(key) for key in sorted(actual_entity_keys - set(expected_entity_map))
    ]
    entity_freshness = evaluate_entity_freshness(
        entities_list,
        {(row["skill"], row["runtime_unit_key"]): row for row in current_runtime_rows},
    )
    fresh_runtime_rows, freshness_issues = evaluate_runtime_unit_freshness(
        runtime_rows, current_runtime_rows, entities_list
    )
    closures, closure_issues = validate_unsupported_item_closures(
        input_value["unsupported_item_closures"],
        current_runtime_rows,
        entities_list,
        normalized=[scope["normalized_input"] for scope in scopes],
    )
    formal_design_metrics, formal_design_issues = _formal_design_summary_rows(
        input_value.get("formal_design_summaries", [])
    )
    issues: list[dict[str, Any]] = []
    if missing_units:
        issues.append(
            {
                "issue_type": "missing_runtime_unit",
                "blocking": True,
                "runtime_units": missing_units,
            }
        )
    if extra_units:
        issues.append(
            {
                "issue_type": "extra_runtime_unit",
                "blocking": True,
                "runtime_units": extra_units,
            }
        )
    if missing_entities:
        issues.append(
            {
                "issue_type": "missing_entity",
                "blocking": True,
                "entities": missing_entities,
            }
        )
    if extra_entities:
        issues.append(
            {"issue_type": "extra_entity", "blocking": True, "entities": extra_entities}
        )
    for row in entity_freshness:
        if row["freshness_status"] == "stale":
            issues.append(
                {
                    "issue_type": "stale_entity",
                    "blocking": True,
                    "skill": row["skill"],
                    "entity_type": row["entity_type"],
                    "entity_ref": row["entity_ref"],
                    "stale_reasons": row["stale_reasons"],
                }
            )
    issues.extend(freshness_issues)
    issues.extend(closure_issues)
    issues.extend(formal_design_issues)
    for summary in formal_design_metrics:
        if summary["pair_coverage_status"] != "complete":
            issues.append(
                {
                    "issue_type": "formal_candidate_coverage_incomplete",
                    "blocking": True,
                    "formal_design_ref": summary["design_ref"],
                    "pair_coverage_status": summary["pair_coverage_status"],
                    "pair_denominator": summary["pair_denominator"],
                    "pair_closed": summary["pair_closed"],
                }
            )
    issues.extend(
        _graph_issues(nodes, kinds, edges, dispositions, coverage_models_by_tcn)
    )
    issues.extend(
        evaluate_target_disposition_closure(current_runtime_rows, entities_list)
    )
    for scope in scopes:
        issues.extend(
            evaluate_materialize_completion(
                scope["normalized_input"], current_runtime_rows, entities_list, closures
            )
        )
    for row in fresh_runtime_rows:
        if (
            row["result_status"] != "ready"
            or row["freshness_status"] != "current"
            or (row["runtime_required"] and not row["deterministic_generated"])
        ):
            issues.append(
                {
                    "issue_type": "runtime_not_complete",
                    "blocking": True,
                    "skill": row["skill"],
                    "runtime_unit_key": row["runtime_unit_key"],
                }
            )
    issues_by_key = {canonical_json_text(row): row for row in issues}
    issues = [issues_by_key[key] for key in sorted(issues_by_key)]
    can_complete = bool(scopes) and not issues
    return {
        "runtime_status": "ok",
        "support_status": "supported",
        "result_status": "ready" if can_complete else "unresolved",
        "runtime_required": True,
        "deterministic_generated": True,
        "payload": {
            "analysis_scopes": scopes,
            "nodes": nodes,
            "edges": edges,
            "dispositions": dispositions,
            "expected_runtime_units": [
                expected_unit_map[key] for key in sorted(expected_unit_map)
            ],
            "expected_entities": [
                expected_entity_map[key] for key in sorted(expected_entity_map)
            ],
            "runtime_units": fresh_runtime_rows,
            "current_entities": entities_list,
            "missing_runtime_units": missing_units,
            "extra_runtime_units": extra_units,
            "missing_entities": missing_entities,
            "extra_entities": extra_entities,
            "runtime_freshness": [
                {
                    "skill": row["skill"],
                    "runtime_unit_key": row["runtime_unit_key"],
                    "freshness_status": row["freshness_status"],
                }
                for row in fresh_runtime_rows
            ],
            "entity_freshness": entity_freshness,
            "unsupported_item_closures": closures,
            "formal_design_metrics": formal_design_metrics,
            "can_complete": can_complete,
        },
        "issues": issues,
    }


def _formal_level_assignment(evidence: Any) -> dict[str, str]:
    if not isinstance(evidence, dict) or set(evidence) != {
        "explicit",
        "architecture",
        "default",
    }:
        raise InvalidInput("formal design test_level_evidence schemaが不正です")
    explicit = evidence["explicit"]
    architecture = evidence["architecture"]
    default = evidence["default"]
    if explicit is not None:
        if not isinstance(explicit, dict) or set(explicit) != {"level", "source_ref"}:
            raise InvalidInput("formal design explicit test level evidenceが不正です")
        return {
            "level": ensure_nonempty_string(explicit["level"], "formal explicit level"),
            "source": "explicit",
            "source_ref": ensure_nonempty_string(
                explicit["source_ref"], "formal explicit source_ref"
            ),
        }
    if architecture is not None:
        if (
            not isinstance(architecture, dict)
            or set(architecture) != {"level", "source_ref", "approved"}
            or not isinstance(architecture["approved"], bool)
        ):
            raise InvalidInput(
                "formal design architecture test level evidenceが不正です"
            )
        if architecture["approved"]:
            return {
                "level": ensure_nonempty_string(
                    architecture["level"], "formal architecture level"
                ),
                "source": "approved_architecture",
                "source_ref": ensure_nonempty_string(
                    architecture["source_ref"], "formal architecture source_ref"
                ),
            }
    if not isinstance(default, dict) or set(default) != {"level", "source_ref"}:
        raise InvalidInput("formal design default test level evidenceが不正です")
    if default["level"] != "system":
        raise InvalidInput("formal design default test levelはsystemが必要です")
    return {
        "level": "system",
        "source": "default",
        "source_ref": ensure_nonempty_string(
            default["source_ref"], "formal default source_ref"
        ),
    }


def _formal_record_metrics(
    record: Any, expected_design_ref: str, expected_revision: int
) -> dict[str, Any]:
    record_fields = {
        "schema_version",
        "design_ref",
        "revision",
        "change_reason",
        "source_refs",
        "items",
        "items_complete",
        "conditions_complete",
        "condition_candidates",
        "authorities",
        "test_level_evidence",
        "pair_assessments",
        "history",
        "retired_candidate_refs",
    }
    if not isinstance(record, dict) or set(record) != record_fields:
        raise InvalidInput("formal_design_record schemaが不正です")
    design_ref = ensure_nonempty_string(
        record["design_ref"], "formal record design_ref"
    )
    revision = record["revision"]
    if (
        record["schema_version"] != "formal-design-v1"
        or not re.fullmatch(r"FD-\d{3,}", design_ref)
        or not isinstance(revision, int)
        or isinstance(revision, bool)
        or revision < 1
    ):
        raise InvalidInput("formal_design_record identity is invalid")
    ensure_nonempty_string(record["change_reason"], "formal record change_reason")

    raw_sources = ensure_list(record["source_refs"], "formal record source_refs")
    sources: dict[str, tuple[str, str]] = {}
    for index, row in enumerate(raw_sources):
        if not isinstance(row, dict) or set(row) != {"ref", "revision", "currentness"}:
            raise InvalidInput(
                f"formal_design_record.source_refs[{index}] schemaが不正です"
            )
        ref = ensure_nonempty_string(row["ref"], "formal source ref")
        source_revision = ensure_nonempty_string(
            row["revision"], "formal source revision"
        )
        currentness = row["currentness"]
        if (
            not isinstance(currentness, str)
            or currentness not in {"current", "stale", "unknown"}
            or ref in sources
        ):
            raise InvalidInput("formal source currentnessまたは一意性が不正です")
        sources[ref] = (source_revision, currentness)

    raw_items = ensure_list(record["items"], "formal record items")
    items: dict[str, str] = {}
    for index, row in enumerate(raw_items):
        if not isinstance(row, dict) or set(row) != {"item_ref", "source_ref"}:
            raise InvalidInput(f"formal_design_record.items[{index}] schemaが不正です")
        item_ref = ensure_nonempty_string(row["item_ref"], "formal item_ref")
        source_ref = ensure_nonempty_string(row["source_ref"], "formal item source_ref")
        if (
            not FORMAL_ITEM_RE.fullmatch(item_ref)
            or item_ref in items
            or source_ref not in sources
        ):
            raise InvalidInput("formal item scope is invalid")
        items[item_ref] = source_ref

    raw_conditions = ensure_list(
        record["condition_candidates"], "formal record condition_candidates"
    )
    conditions: dict[str, str] = {}
    for index, row in enumerate(raw_conditions):
        if not isinstance(row, dict) or set(row) != {"condition_ref", "source_ref"}:
            raise InvalidInput(
                f"formal_design_record.condition_candidates[{index}] schemaが不正です"
            )
        condition_ref = ensure_nonempty_string(
            row["condition_ref"], "formal condition_ref"
        )
        source_ref = ensure_nonempty_string(
            row["source_ref"], "formal condition source_ref"
        )
        if (
            not FORMAL_CONDITION_RE.fullmatch(condition_ref)
            or condition_ref in conditions
            or source_ref not in sources
        ):
            raise InvalidInput("formal condition scope is invalid")
        conditions[condition_ref] = source_ref

    if not isinstance(record["items_complete"], bool) or not isinstance(
        record["conditions_complete"], bool
    ):
        raise InvalidInput("formal candidate population completeness is invalid")
    authorities: dict[str, str] = {}
    for index, row in enumerate(
        ensure_list(record["authorities"], "formal authorities")
    ):
        if not isinstance(row, dict) or set(row) != {
            "authority_ref",
            "revision",
            "currentness",
        }:
            raise InvalidInput(f"formal authorities[{index}] schemaが不正です")
        ref = ensure_nonempty_string(row["authority_ref"], "formal authority_ref")
        authority_revision = ensure_nonempty_string(
            row["revision"], "formal authority revision"
        )
        currentness = row["currentness"]
        if (
            ref in authorities
            or not isinstance(currentness, str)
            or currentness not in {"current", "stale", "unknown"}
            or sources.get(ref) != (authority_revision, currentness)
        ):
            raise InvalidInput(
                "formal Authority/source revision or currentness mismatch"
            )
        authorities[ref] = currentness

    item_refs = set(items)
    level_evidence = record["test_level_evidence"]
    level_assignment_by_item: dict[str, dict[str, str]] = {}
    if isinstance(level_evidence, dict):
        assignment = _formal_level_assignment(level_evidence)
        level_assignment_by_item = {item_ref: assignment for item_ref in item_refs}
    else:
        rows = ensure_list(level_evidence, "formal test_level_evidence")
        for index, row in enumerate(rows):
            if not isinstance(row, dict) or set(row) != {"item_ref", "evidence"}:
                raise InvalidInput(
                    f"formal test_level_evidence[{index}] schemaが不正です"
                )
            item_ref = ensure_nonempty_string(row["item_ref"], "formal level item_ref")
            if item_ref not in item_refs or item_ref in level_assignment_by_item:
                raise InvalidInput(
                    "formal item test_level_evidence is duplicate or unknown"
                )
            level_assignment_by_item[item_ref] = _formal_level_assignment(
                row["evidence"]
            )
        if set(level_assignment_by_item) != item_refs:
            raise InvalidInput(
                "formal item test_level_evidence population is incomplete"
            )
    if any(
        assignment["source_ref"] not in sources
        for assignment in level_assignment_by_item.values()
    ):
        raise InvalidInput("formal test level source_ref is unknown")

    expected_pairs = {
        (item_ref, condition_ref) for item_ref in items for condition_ref in conditions
    }
    assessments: dict[tuple[str, str], dict[str, Any]] = {}
    pair_sources: dict[tuple[str, str], set[str]] = {}
    candidate_ids: set[str] = set()
    current_candidate_pairs: dict[str, tuple[str, str]] = {}
    current_tcn_draft_keys: set[str] = set()
    for index, row in enumerate(
        ensure_list(record["pair_assessments"], "formal pair_assessments")
    ):
        if not isinstance(row, dict) or set(row) != {
            "item_ref",
            "condition_ref",
            "decision",
            "rationale",
            "test_level",
            "tcn_draft_key",
            "expected_result_candidates",
            "covered_by_pair",
            "reopen_condition",
        }:
            raise InvalidInput(f"formal pair_assessments[{index}] schemaが不正です")
        pair = (
            ensure_nonempty_string(row["item_ref"], "formal pair item_ref"),
            ensure_nonempty_string(row["condition_ref"], "formal pair condition_ref"),
        )
        decision = row["decision"]
        if (
            pair not in expected_pairs
            or pair in assessments
            or not isinstance(decision, str)
            or decision not in FORMAL_DECISIONS
        ):
            raise InvalidInput("formal pair identity or decision is invalid")
        ensure_nonempty_string(row["rationale"], "formal pair rationale")
        ensure_nonempty_string(row["test_level"], "formal pair test_level")
        pair_sources[pair] = {
            items[pair[0]],
            conditions[pair[1]],
            level_assignment_by_item[pair[0]]["source_ref"],
        }
        if row["test_level"] != level_assignment_by_item[pair[0]]["level"]:
            raise InvalidInput("formal pair test_level differs from item assignment")
        candidates = ensure_list(
            row["expected_result_candidates"], "formal expected_result_candidates"
        )
        if decision == "adopted":
            tcn_draft_key = ensure_nonempty_string(
                row["tcn_draft_key"], "formal tcn_draft_key"
            )
            if tcn_draft_key in current_tcn_draft_keys:
                raise InvalidInput("formal tcn_draft_key is assigned more than once")
            current_tcn_draft_keys.add(tcn_draft_key)
            if not candidates:
                raise InvalidInput("adopted formal pair has no expected result")
            for candidate_index, candidate in enumerate(candidates):
                if not isinstance(candidate, dict) or set(candidate) != {
                    "candidate_ref",
                    "text",
                    "authority_refs",
                    "observation_method",
                    "side_effects",
                    "revision",
                }:
                    raise InvalidInput(
                        f"formal expected_result_candidates[{candidate_index}] schemaが不正です"
                    )
                candidate_ref = ensure_nonempty_string(
                    candidate["candidate_ref"], "formal candidate_ref"
                )
                if (
                    not FORMAL_CANDIDATE_RE.fullmatch(candidate_ref)
                    or candidate_ref in candidate_ids
                ):
                    raise InvalidInput(
                        "formal expected result candidate identity is invalid"
                    )
                candidate_ids.add(candidate_ref)
                current_candidate_pairs[candidate_ref] = pair
                for field in ("text", "observation_method", "side_effects", "revision"):
                    ensure_nonempty_string(
                        candidate[field], f"formal candidate {field}"
                    )
                refs = candidate["authority_refs"]
                if (
                    not isinstance(refs, list)
                    or not refs
                    or any(not isinstance(ref, str) or not ref for ref in refs)
                    or refs != sorted(set(refs))
                    or set(refs) - set(authorities)
                ):
                    raise InvalidInput(
                        "formal expected result Authority refs are invalid"
                    )
                pair_sources[pair].update(refs)
            if [candidate["candidate_ref"] for candidate in candidates] != sorted(
                candidate["candidate_ref"] for candidate in candidates
            ):
                raise InvalidInput("formal expected result candidates are not ordered")
        elif row["tcn_draft_key"] is not None or candidates:
            raise InvalidInput(
                "non-adopted formal pair has an unexpected TCN or candidate"
            )
        if decision == "duplicate":
            covered = row["covered_by_pair"]
            if not isinstance(covered, dict) or set(covered) != {
                "item_ref",
                "condition_ref",
            }:
                raise InvalidInput("formal duplicate covered_by_pair is invalid")
            target = (
                ensure_nonempty_string(covered["item_ref"], "covered item_ref"),
                ensure_nonempty_string(
                    covered["condition_ref"], "covered condition_ref"
                ),
            )
            if target == pair or target not in expected_pairs:
                raise InvalidInput("formal duplicate target is outside candidate scope")
        elif row["covered_by_pair"] is not None:
            raise InvalidInput("non-duplicate formal pair has a duplicate target")
        if decision in {"unconfirmed", "blocked"}:
            ensure_nonempty_string(row["reopen_condition"], "formal reopen_condition")
        elif row["reopen_condition"] is not None:
            raise InvalidInput("closed formal pair has a reopen condition")
        if (
            decision == "other_test_level"
            and row["test_level"] == level_assignment_by_item[pair[0]]["level"]
        ):
            raise InvalidInput("formal other_test_level matches the assigned level")
        assessments[pair] = row

    history_revisions: list[int] = []
    historical_candidate_pairs: dict[str, tuple[str, str]] = {}
    historical_retirements: dict[str, str] = {}
    previous_history_candidate_ids: set[str] = set()
    for history_index, history_row in enumerate(
        ensure_list(record["history"], "formal record history")
    ):
        history_fields = {
            "revision",
            "change_reason",
            "pair_decisions",
            "candidate_assignments",
            "retired_candidate_refs",
        }
        if not isinstance(history_row, dict) or set(history_row) != history_fields:
            raise InvalidInput(
                f"formal record history[{history_index}] schema is invalid"
            )
        old_revision = history_row["revision"]
        if (
            not isinstance(old_revision, int)
            or isinstance(old_revision, bool)
            or old_revision < 1
        ):
            raise InvalidInput("formal record history revision is invalid")
        history_revisions.append(old_revision)
        ensure_nonempty_string(
            history_row["change_reason"], "formal history change_reason"
        )
        old_decisions: dict[tuple[str, str], str] = {}
        for old_pair in ensure_list(
            history_row["pair_decisions"], "formal history pair_decisions"
        ):
            if not isinstance(old_pair, dict) or set(old_pair) != {
                "item_ref",
                "condition_ref",
                "decision",
            }:
                raise InvalidInput("formal history pair decision schema is invalid")
            key = (
                ensure_nonempty_string(old_pair["item_ref"], "history item_ref"),
                ensure_nonempty_string(
                    old_pair["condition_ref"], "history condition_ref"
                ),
            )
            decision = old_pair["decision"]
            if (
                not FORMAL_ITEM_RE.fullmatch(key[0])
                or not FORMAL_CONDITION_RE.fullmatch(key[1])
                or key in old_decisions
                or not isinstance(decision, str)
                or decision not in FORMAL_DECISIONS
            ):
                raise InvalidInput("formal history pair decision is invalid")
            old_decisions[key] = decision

        history_candidate_ids: list[str] = []
        assigned_pairs: set[tuple[str, str]] = set()
        for assignment in ensure_list(
            history_row["candidate_assignments"], "formal history candidate_assignments"
        ):
            if not isinstance(assignment, dict) or set(assignment) != {
                "candidate_ref",
                "item_ref",
                "condition_ref",
            }:
                raise InvalidInput(
                    "formal history candidate assignment schema is invalid"
                )
            candidate_ref = ensure_nonempty_string(
                assignment["candidate_ref"], "history candidate_ref"
            )
            pair = (
                ensure_nonempty_string(assignment["item_ref"], "history item_ref"),
                ensure_nonempty_string(
                    assignment["condition_ref"], "history condition_ref"
                ),
            )
            if (
                not FORMAL_CANDIDATE_RE.fullmatch(candidate_ref)
                or old_decisions.get(pair) != "adopted"
            ):
                raise InvalidInput("formal history candidate assignment is invalid")
            history_candidate_ids.append(candidate_ref)
            assigned_pairs.add(pair)
            previous_pair = historical_candidate_pairs.get(candidate_ref)
            if previous_pair is not None and previous_pair != pair:
                raise InvalidInput("formal history candidate ID was reassigned")
            historical_candidate_pairs[candidate_ref] = pair
        if history_candidate_ids != sorted(set(history_candidate_ids)) or any(
            decision == "adopted" and pair not in assigned_pairs
            for pair, decision in old_decisions.items()
        ):
            raise InvalidInput("formal history candidate assignments are incomplete")
        if set(history_candidate_ids) & set(historical_retirements):
            raise InvalidInput("retired formal history candidate ID was reused")

        retirement_ids: list[str] = []
        row_retirements: dict[str, str] = {}
        for retired in ensure_list(
            history_row["retired_candidate_refs"],
            "formal history retired_candidate_refs",
        ):
            if not isinstance(retired, dict) or set(retired) != {
                "candidate_ref",
                "reason",
            }:
                raise InvalidInput("formal history retirement schema is invalid")
            candidate_ref = ensure_nonempty_string(
                retired["candidate_ref"], "history retired candidate_ref"
            )
            reason = ensure_nonempty_string(
                retired["reason"], "history retired candidate reason"
            )
            if (
                not FORMAL_CANDIDATE_RE.fullmatch(candidate_ref)
                or candidate_ref in row_retirements
            ):
                raise InvalidInput("formal history retirement identity is invalid")
            retirement_ids.append(candidate_ref)
            row_retirements[candidate_ref] = reason
        if (
            retirement_ids != sorted(retirement_ids)
            or not (previous_history_candidate_ids - set(history_candidate_ids))
            <= set(row_retirements)
            or set(row_retirements) & set(history_candidate_ids)
            or set(row_retirements) - set(historical_candidate_pairs)
            or not set(historical_retirements) <= set(row_retirements)
            or any(
                row_retirements[candidate_ref] != reason
                for candidate_ref, reason in historical_retirements.items()
            )
        ):
            raise InvalidInput(
                "formal history retirement lineage is incomplete or changed"
            )
        historical_retirements = row_retirements
        previous_history_candidate_ids = set(history_candidate_ids)
    history_complete = history_revisions == list(range(1, revision))
    identity_matches = (
        design_ref == expected_design_ref and revision == expected_revision
    )
    matrix_complete = set(assessments) == expected_pairs
    for pair, row in assessments.items():
        if row["decision"] == "duplicate":
            target = (
                row["covered_by_pair"]["item_ref"],
                row["covered_by_pair"]["condition_ref"],
            )
            if assessments.get(target, {}).get("decision") != "adopted":
                raise InvalidInput("formal duplicate target is not adopted")

    current_retirement_ids: list[str] = []
    current_retirements: dict[str, str] = {}
    for retired in ensure_list(
        record["retired_candidate_refs"], "formal retired_candidate_refs"
    ):
        if not isinstance(retired, dict) or set(retired) != {
            "candidate_ref",
            "reason",
        }:
            raise InvalidInput("formal retired_candidate_refs schema is invalid")
        candidate_ref = ensure_nonempty_string(
            retired["candidate_ref"], "retired candidate_ref"
        )
        reason = ensure_nonempty_string(retired["reason"], "retired candidate reason")
        if (
            not FORMAL_CANDIDATE_RE.fullmatch(candidate_ref)
            or candidate_ref in current_retirements
        ):
            raise InvalidInput("formal retired candidate identity is invalid")
        current_retirement_ids.append(candidate_ref)
        current_retirements[candidate_ref] = reason
    if (
        current_retirement_ids != sorted(current_retirement_ids)
        or set(current_retirements) & set(current_candidate_pairs)
        or set(current_retirements) - set(historical_candidate_pairs)
        or set(historical_retirements) & set(current_candidate_pairs)
        or not set(historical_retirements) <= set(current_retirements)
        or any(
            current_retirements[candidate_ref] != reason
            for candidate_ref, reason in historical_retirements.items()
        )
        or (set(historical_candidate_pairs) - set(current_candidate_pairs))
        - set(current_retirements)
        or any(
            candidate_ref in historical_candidate_pairs
            and historical_candidate_pairs[candidate_ref] != pair
            for candidate_ref, pair in current_candidate_pairs.items()
        )
    ):
        raise InvalidInput("formal current retirement lineage is incomplete or changed")
    pair_stale_sources = {
        pair: sorted(
            ref
            for ref in refs
            if sources[ref][1] != "current"
            or (ref in authorities and authorities[ref] != "current")
        )
        for pair, refs in pair_sources.items()
    }
    mapped_source_refs = (
        set(items.values())
        | set(conditions.values())
        | {assignment["source_ref"] for assignment in level_assignment_by_item.values()}
    )
    mapped_source_refs.update(ref for refs in pair_sources.values() for ref in refs)
    unmapped_stale_sources = {
        ref
        for ref, (_source_revision, currentness) in sources.items()
        if currentness != "current" and ref not in mapped_source_refs
    }
    if unmapped_stale_sources:
        # A stale source without a known pair dependency cannot be assumed irrelevant.
        for pair in pair_stale_sources:
            pair_stale_sources[pair] = sorted(
                set(pair_stale_sources[pair]) | unmapped_stale_sources
            )
    stale_pairs = {pair for pair, refs in pair_stale_sources.items() if refs}
    for pair, row in assessments.items():
        if row["decision"] == "duplicate":
            covered = row["covered_by_pair"]
            if not isinstance(covered, dict) or set(covered) != {
                "item_ref",
                "condition_ref",
            }:
                raise InvalidInput("formal duplicate pair target is invalid")
            target = (covered["item_ref"], covered["condition_ref"])
            if (
                target not in assessments
                or assessments[target]["decision"] != "adopted"
            ):
                raise InvalidInput("formal duplicate pair target is not adopted")
            if target in stale_pairs:
                stale_pairs.add(pair)
                pair_stale_sources[pair] = sorted(
                    set(pair_stale_sources[pair]) | set(pair_stale_sources[target])
                )

    unresolved_by_pair: dict[tuple[str, str], str] = {}
    for pair, row in assessments.items():
        if row["decision"] in {"unconfirmed", "blocked"}:
            unresolved_by_pair[pair] = row["decision"]
        elif pair in stale_pairs:
            unresolved_by_pair[pair] = "blocked"
    for pair in expected_pairs - set(assessments):
        unresolved_by_pair[pair] = "blocked"
    denominator = len(expected_pairs)
    closed = sum(
        1
        for pair, row in assessments.items()
        if row["decision"] not in {"unconfirmed", "blocked"} and pair not in stale_pairs
    )
    items_complete = record["items_complete"]
    conditions_complete = record["conditions_complete"]
    verified = identity_matches and history_complete and matrix_complete
    if not verified:
        items_complete = False
        conditions_complete = False
    if denominator == 0:
        coverage = None
        status = "unknown_zero_denominator"
    elif not items_complete or not conditions_complete or not matrix_complete:
        coverage = None
        status = "incomplete_population"
    else:
        coverage = f"{closed}/{denominator}"
        status = "incomplete" if unresolved_by_pair else "complete"
    return {
        "design_ref": design_ref,
        "revision": revision,
        "pair_denominator": denominator,
        "pair_closed": closed,
        "pair_coverage": coverage,
        "pair_coverage_status": status,
        "unresolved_pairs": [
            {"item_ref": item, "condition_ref": condition, "decision": decision}
            for (item, condition), decision in sorted(unresolved_by_pair.items())
        ],
        "items_complete": items_complete,
        "conditions_complete": conditions_complete,
        "record_verified": verified,
    }


def _formal_design_summary_rows(
    value: Any,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows = ensure_list(value, "formal_design_summaries")
    result: list[dict[str, Any]] = []
    issues: list[dict[str, Any]] = []
    seen = set()
    allowed_statuses = {
        "complete",
        "incomplete",
        "incomplete_population",
        "unknown_zero_denominator",
    }
    for index, row in enumerate(rows):
        required = {
            "design_ref",
            "revision",
            "pair_denominator",
            "pair_closed",
            "pair_coverage",
            "pair_coverage_status",
            "unresolved_pairs",
            "items_complete",
            "conditions_complete",
        }
        if (
            not isinstance(row, dict)
            or required - set(row)
            or set(row) - required - {"formal_design_record"}
        ):
            raise InvalidInput(f"formal_design_summaries[{index}] schemaが不正です")
        design_ref = ensure_nonempty_string(row["design_ref"], "formal design ref")
        revision = row["revision"]
        denominator = row["pair_denominator"]
        closed = row["pair_closed"]
        if (
            not isinstance(revision, int)
            or isinstance(revision, bool)
            or revision < 1
            or not isinstance(denominator, int)
            or isinstance(denominator, bool)
            or denominator < 0
            or not isinstance(closed, int)
            or isinstance(closed, bool)
            or closed < 0
            or closed > denominator
            or design_ref in seen
        ):
            raise InvalidInput(
                "formal design revision / denominator / identityが不正です"
            )
        seen.add(design_ref)
        if not isinstance(row["items_complete"], bool) or not isinstance(
            row["conditions_complete"], bool
        ):
            raise InvalidInput("formal design discovery completenessが不正です")
        status = row["pair_coverage_status"]
        if status not in allowed_statuses:
            raise InvalidInput("formal design pair_coverage_statusが不正です")
        unresolved = ensure_list(
            row["unresolved_pairs"], "formal design unresolved_pairs"
        )
        unresolved_keys = []
        for pair in unresolved:
            if not isinstance(pair, dict) or set(pair) != {
                "item_ref",
                "condition_ref",
                "decision",
            }:
                raise InvalidInput("formal design unresolved pair schemaが不正です")
            key = (
                ensure_nonempty_string(pair["item_ref"], "formal pair item_ref"),
                ensure_nonempty_string(
                    pair["condition_ref"], "formal pair condition_ref"
                ),
            )
            if pair["decision"] not in {"unconfirmed", "blocked"}:
                raise InvalidInput("unresolved pair decisionが不正です")
            unresolved_keys.append(key)
        if (
            unresolved_keys != sorted(set(unresolved_keys))
            or closed + len(unresolved_keys) != denominator
        ):
            raise InvalidInput(
                "formal design pair closure countとunresolved pairsが不一致です"
            )
        coverage = row["pair_coverage"]
        if denominator == 0:
            expected_status = "unknown_zero_denominator"
            if coverage is not None:
                raise InvalidInput(
                    "0件のformal design denominatorをcoverage値にしてはいけません"
                )
        elif not row["items_complete"] or not row["conditions_complete"]:
            expected_status = "incomplete_population"
            if coverage is not None:
                raise InvalidInput(
                    "不完全なformal candidate populationをcoverage値にしてはいけません"
                )
        else:
            expected_status = "incomplete" if unresolved_keys else "complete"
            if not isinstance(coverage, str) or coverage != f"{closed}/{denominator}":
                raise InvalidInput(
                    "formal design pair_coverageが分子／分母と不一致です"
                )
        if status != expected_status:
            raise InvalidInput("formal design pair coverage statusが根拠と不一致です")
        if status == "complete" and closed != denominator:
            raise InvalidInput(
                "formal designを未閉鎖pairを含むままcompleteにしてはいけません"
            )
        if "formal_design_record" not in row:
            result.append(
                {
                    "design_ref": design_ref,
                    "revision": revision,
                    "pair_denominator": None,
                    "pair_closed": None,
                    "pair_coverage": None,
                    "pair_coverage_status": "incomplete_population",
                    "unresolved_pairs": [],
                    "items_complete": False,
                    "conditions_complete": False,
                    "record_verified": False,
                }
            )
            issues.append(
                {
                    "issue_type": "formal_design_record_unverified",
                    "blocking": True,
                    "formal_design_ref": design_ref,
                    "revision": revision,
                }
            )
            continue

        metrics = _formal_record_metrics(
            row["formal_design_record"], design_ref, revision
        )
        mismatched_fields = [
            field for field in required if metrics[field] != row[field]
        ]
        if mismatched_fields:
            issues.append(
                {
                    "issue_type": "formal_design_summary_mismatch",
                    "blocking": True,
                    "formal_design_ref": design_ref,
                    "revision": revision,
                    "fields": sorted(mismatched_fields),
                }
            )
        if not metrics["record_verified"]:
            issues.append(
                {
                    "issue_type": "formal_design_record_incomplete",
                    "blocking": True,
                    "formal_design_ref": design_ref,
                    "revision": revision,
                }
            )
            if metrics["design_ref"] != design_ref or metrics["revision"] != revision:
                metrics = {
                    "design_ref": design_ref,
                    "revision": revision,
                    "pair_denominator": None,
                    "pair_closed": None,
                    "pair_coverage": None,
                    "pair_coverage_status": "incomplete_population",
                    "unresolved_pairs": [],
                    "items_complete": False,
                    "conditions_complete": False,
                    "record_verified": False,
                }
        result.append(canonicalize(metrics))
    return result, issues


def handler(input_value: dict[str, Any], metadata: dict[str, Any]) -> dict[str, Any]:
    if (
        metadata["model_key"] is not None
        or metadata["runtime_unit_key"] != "artifact:traceability:all"
        or metadata["scope_key"] not in {"all", None}
    ):
        raise InvalidInput("traceability runtime metadataが不正です")
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
