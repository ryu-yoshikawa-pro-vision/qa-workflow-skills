from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest


REPO_ROOT = Path(__file__).resolve().parents[3]
CONDITION_SCRIPT = REPO_ROOT / "skills" / "test-condition-design" / "scripts" / "condition_structure.py"
REQUIREMENT_SCRIPT = REPO_ROOT / "skills" / "test-requirement-design" / "scripts" / "requirement_structure.py"
EP_SCRIPT = REPO_ROOT / "skills" / "test-condition-design" / "scripts" / "equivalence_partitions.py"
MATERIALIZE_SCRIPT = REPO_ROOT / "skills" / "test-condition-design" / "scripts" / "materialize_coverage.py"
TDR_SCRIPT = REPO_ROOT / "skills" / "test-condition-design" / "scripts" / "test_data_requirements.py"
CASE_SCRIPT = REPO_ROOT / "skills" / "test-case-design" / "scripts" / "case_structure.py"
WORKFLOW_SCRIPT = REPO_ROOT / "skills" / "qa-workflow" / "scripts" / "workflow_runtime.py"
TRACEABILITY_SCRIPT = REPO_ROOT / "skills" / "coverage-analysis" / "scripts" / "traceability.py"
SCHEMA_SCRIPT = REPO_ROOT / "skills" / "test-condition-design" / "scripts" / "schema_cases.py"
RUNTIME_PATH = REPO_ROOT / "skills" / "test-condition-design" / "scripts" / "runtime_contract.py"
SPEC = importlib.util.spec_from_file_location("vertical_runtime_contract", RUNTIME_PATH)
assert SPEC is not None and SPEC.loader is not None
runtime = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = runtime
SPEC.loader.exec_module(runtime)


def run_script(script: Path, request: dict) -> dict:
    result = subprocess.run([sys.executable, str(script)], input=json.dumps(request, ensure_ascii=False).encode(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=REPO_ROOT, check=False)
    if result.stderr:
        raise AssertionError(result.stderr.decode())
    return json.loads(result.stdout)


def condition_metadata() -> dict:
    return {
        "envelope_version": "1", "skill": "test-condition-design", "runtime_contract_version": "runtime-v1", "generator_contract_version": "condition-structure-v1",
        "runtime_unit_key": "artifact:condition_structure:all", "model_key": None, "model_type": None, "technique_slug": None, "selection_source": None, "selection_key": None,
        "scope_key": "all", "input_mode": "direct", "upstream_entities": [], "upstream_runtime_units": [], "static_data_versions": {}, "authority_refs": [], "reference_refs": [],
    }


def condition_input() -> dict:
    return {
        "test_requirements": [{"tr_id": "TR-001", "priority": 1, "authority_refs": [], "risk_refs": []}],
        "technique_selections": [{"selection_key": "SEL-001", "selected_techniques": ["ep"], "undetermined_signal_closures": [], "status": "active"}],
        "test_conditions": [{"draft_key": "tcn-draft", "identity_action": "new", "reuse_id": None, "tr_refs": ["TR-001"], "condition": "role", "category": None, "technique_slugs": ["ep"], "coverage_criterion": "each-choice", "authority_refs": [], "risk_refs": [], "priority": 1, "priority_override_reason": None}],
        "requirement_dispositions": [],
        "models": [{"draft_key": "model-draft", "model_type": "ep", "technique_slug": "ep", "selection_source": "analysis", "selection_key": "SEL-001", "derived_from_model_draft_key": None, "identity_action": "new", "reuse_model_key": None, "parent_tcn_draft_key": "tcn-draft"}],
        "previous_tcn_ids": [], "previous_model_keys": [], "update_scope_tcn_ids": [], "update_scope_model_keys": [],
    }


def ep_metadata() -> dict:
    return {
        "envelope_version": "1", "skill": "test-condition-design", "runtime_contract_version": "runtime-v1", "generator_contract_version": "equivalence-partitions-v1",
        "runtime_unit_key": "model:ep-001", "model_key": "ep-001", "model_type": "ep", "technique_slug": "ep", "selection_source": "analysis", "selection_key": "SEL-001",
        "scope_key": None, "input_mode": "direct", "upstream_entities": [], "upstream_runtime_units": [], "static_data_versions": {}, "authority_refs": [], "reference_refs": [],
    }


def ep_input() -> dict:
    return {"sets": [{"set_key": "role", "label": "Role", "partitions": [
        {"partition_key": "admin", "label": "Admin", "validity": "valid", "definition": {"type": "enum", "values": [{"type": "enum", "value": "admin"}]}, "representative": None, "authority_refs": []},
        {"partition_key": "user", "label": "User", "validity": "valid", "definition": {"type": "enum", "values": [{"type": "enum", "value": "user"}]}, "representative": None, "authority_refs": []},
    ]}]}


def workflow_metadata() -> dict:
    return {
        "envelope_version": "1", "skill": "qa-workflow", "runtime_contract_version": "runtime-v1", "generator_contract_version": "workflow-runtime-v1",
        "runtime_unit_key": "artifact:workflow_runtime:all", "model_key": None, "model_type": None, "technique_slug": None, "selection_source": None, "selection_key": None,
        "scope_key": "all", "input_mode": "artifact", "upstream_entities": [], "upstream_runtime_units": [], "static_data_versions": {}, "authority_refs": [], "reference_refs": [],
    }


class EpVerticalIntegrationTests(unittest.TestCase):
    def test_schema_adapter_model_wide_requirements_flow_through_tdr_entity_to_materialize(self) -> None:
        schema_metadata = {
            "envelope_version": "1", "skill": "test-condition-design", "runtime_contract_version": "runtime-v1", "generator_contract_version": "schema-cases-v1",
            "runtime_unit_key": "model:schema-001", "model_key": "schema-001", "model_type": "schema", "technique_slug": None, "selection_source": None, "selection_key": None,
            "scope_key": None, "input_mode": "artifact", "upstream_entities": [], "upstream_runtime_units": [], "static_data_versions": {}, "authority_refs": [], "reference_refs": [],
        }
        schema_input = {
            "schema_kind": "json-schema-2020-12", "schema_pointer": "#", "context": "validation",
            "document": {"type": "object", "properties": {"role": {"enum": ["admin", "member"]}, "age": {"type": "integer", "minimum": 0, "maximum": 100}}, "required": ["role"]},
            "child_models": [],
        }
        schema = run_script(SCHEMA_SCRIPT, {"metadata": schema_metadata, "input": schema_input})
        self.assertEqual(schema["runtime_status"], "ok", schema)
        self.assertEqual(schema["result_status"], "ready", schema)

        tcn = runtime.make_machine_entity("test-condition-design", "tcn", "TCN-001", {
            "tcn_id": "TCN-001", "tr_refs": [], "condition": "schema-derived checkout fields", "category": None,
            "technique_slugs": [], "coverage_criterion": "schema constraints", "authority_refs": [], "risk_refs": [],
            "priority": 1, "priority_override_reason": None, "status": "active",
        })
        model = runtime.make_machine_entity("test-condition-design", "model", "schema-001", {
            "model_key": "schema-001", "model_type": "schema", "technique_slug": None, "parent_tcn_id": "TCN-001",
            "selection_key": None, "selection_source": None, "derived_from_model_key": None, "status": "active",
        }, model_key="schema-001", upstream_entity_dependencies=[{
            "skill": tcn["skill"], "entity_type": tcn["entity_type"], "entity_ref": tcn["entity_ref"], "content_fingerprint": tcn["content_fingerprint"],
        }])
        tdr_metadata = {
            "envelope_version": "1", "skill": "test-condition-design", "runtime_contract_version": "runtime-v1", "generator_contract_version": "test-data-requirements-v1",
            "runtime_unit_key": "artifact:test_data_requirements:all", "model_key": None, "model_type": None, "technique_slug": None, "selection_source": None, "selection_key": None,
            "scope_key": "all", "input_mode": "artifact", "upstream_entities": [{"skill": model["skill"], "entity_type": model["entity_type"], "entity_ref": model["entity_ref"], "content": model["content"]}],
            "upstream_runtime_units": [{"skill": "test-condition-design", "runtime_unit_key": "model:schema-001", "generation_fingerprint": schema["generation_fingerprint"]}],
            "static_data_versions": {}, "authority_refs": [], "reference_refs": [],
        }
        tdr_input = {
            "current_source_targets": [{
                "source_model_key": "schema-001", "target_ref": row["target_ref"], "target_content_fingerprint": row["target_content_fingerprint"],
                "generation_fingerprint": schema["generation_fingerprint"],
            } for row in schema["payload"]["targets"]],
            "requirements": schema["payload"]["derived"]["test_data_requirements"],
        }
        tdr = run_script(TDR_SCRIPT, {"metadata": tdr_metadata, "input": tdr_input})
        self.assertEqual(tdr["runtime_status"], "ok", tdr)
        self.assertEqual({row["source_model_key"] for row in tdr["payload"]["normalized_requirements"]}, {"schema-001"})
        self.assertTrue(all({
            "skill": "test-condition-design", "entity_type": "model", "entity_ref": "schema-001", "content_fingerprint": model["content_fingerprint"],
        } in row["upstream_entity_dependencies"] for row in tdr["payload"]["entities"]))
        self.assertTrue(all({
            "skill": "test-condition-design", "runtime_unit_key": "model:schema-001", "generation_fingerprint": schema["generation_fingerprint"],
        } in row["runtime_dependencies"] for row in tdr["payload"]["entities"]))

        materialize_metadata = {
            "envelope_version": "1", "skill": "test-condition-design", "runtime_contract_version": "runtime-v1", "generator_contract_version": "materialize-coverage-v1",
            "runtime_unit_key": "artifact:materialize_coverage:TCN-001", "model_key": None, "model_type": None, "technique_slug": None, "selection_source": None, "selection_key": None,
            "scope_key": "TCN-001", "input_mode": "artifact",
            "upstream_entities": [
                {"skill": row["skill"], "entity_type": row["entity_type"], "entity_ref": row["entity_ref"], "content": row["content"]}
                for row in [tcn, model, *tdr["payload"]["entities"]]
            ],
            "upstream_runtime_units": [
                {"skill": "test-condition-design", "runtime_unit_key": "model:schema-001", "generation_fingerprint": schema["generation_fingerprint"]},
                {"skill": "test-condition-design", "runtime_unit_key": "artifact:test_data_requirements:all", "generation_fingerprint": tdr["generation_fingerprint"]},
            ],
            "static_data_versions": {}, "authority_refs": [], "reference_refs": [],
        }
        model_result = {
            "skill": "test-condition-design", "model_key": "schema-001", "model_type": "schema", "technique_slug": None,
            "runtime_unit_key": "model:schema-001", "input_fingerprint": schema["input_fingerprint"], "model_fingerprint": schema["model_fingerprint"],
            "generation_fingerprint": schema["generation_fingerprint"], "generator_contract_version": schema["generator_contract_version"],
            "support_status": schema["support_status"], "runtime_status": schema["runtime_status"], "result_status": schema["result_status"],
            "deterministic_generated": schema["deterministic_generated"], "freshness_status": "current", "targets": schema["payload"]["targets"], "unsupported_items": [],
        }
        materialized = run_script(MATERIALIZE_SCRIPT, {
            "metadata": materialize_metadata,
            "input": {
                "tcn_id": "TCN-001",
                "active_model_metadata": [{"model_key": "schema-001", "model_type": "schema", "technique_slug": None, "parent_tcn_id": "TCN-001", "content_fingerprint": model["content_fingerprint"]}],
                "models": [model_result], "semantic_coverage_items": [], "test_data_requirements": tdr["payload"]["normalized_requirements"],
                "target_annotations": [], "target_dispositions": [], "previous_target_id_map": [], "previous_semantic_ci_map": [], "previous_ci_ids": [],
                "previous_expected_result_roots": [], "merge_groups": [],
            },
        })
        self.assertEqual(materialized["runtime_status"], "ok", materialized)
        self.assertEqual(materialized["result_status"], "ready", materialized)

    def test_standalone_evidence_and_qa_workflow_integration(self) -> None:
        requirement = run_script(REQUIREMENT_SCRIPT, {
            "metadata": {
                "envelope_version": "1", "skill": "test-requirement-design", "runtime_contract_version": "runtime-v1", "generator_contract_version": "requirement-structure-v1",
                "runtime_unit_key": "artifact:requirement_structure:all", "model_key": None, "model_type": None, "technique_slug": None, "selection_source": None, "selection_key": None,
                "scope_key": "all", "input_mode": "direct", "upstream_entities": [], "upstream_runtime_units": [], "static_data_versions": {}, "authority_refs": [], "reference_refs": [],
            },
            "input": {
                "authorities": [], "risks": [], "test_requirements": [{
                    "draft_key": "checkout", "identity_action": "new", "reuse_id": None, "text": "checkout completes",
                    "authority_refs": [], "risk_refs": [], "priority": "中", "priority_override_reason": None,
                    "test_level": "system", "observation_method": "assertion",
                }], "dispositions": [], "previous_tr_ids": [], "update_scope_tr_ids": [],
            },
        })
        tr_entity = next(row for row in requirement["payload"]["entities"] if row["entity_type"] == "tr")
        selection_entity = runtime.make_machine_entity("test-analysis", "technique_selection", "SEL-001", {"selection_key": "SEL-001", "selected_techniques": ["ep"]})
        condition_meta = condition_metadata()
        condition_meta["input_mode"] = "artifact"
        condition_meta["upstream_entities"] = [
            {"skill": tr_entity["skill"], "entity_type": tr_entity["entity_type"], "entity_ref": tr_entity["entity_ref"], "content": tr_entity["content"]},
            {"skill": selection_entity["skill"], "entity_type": selection_entity["entity_type"], "entity_ref": selection_entity["entity_ref"], "content": selection_entity["content"]},
        ]
        condition = run_script(CONDITION_SCRIPT, {"metadata": condition_meta, "input": condition_input()})
        self.assertEqual(condition["result_status"], "ready")
        condition_entities = condition["payload"]["entities"]
        ep = run_script(EP_SCRIPT, {"metadata": ep_metadata(), "input": ep_input()})
        self.assertEqual(ep["result_status"], "ready")

        tdr_metadata = {
            "envelope_version": "1", "skill": "test-condition-design", "runtime_contract_version": "runtime-v1", "generator_contract_version": "test-data-requirements-v1",
            "runtime_unit_key": "artifact:test_data_requirements:all", "model_key": None, "model_type": None, "technique_slug": None, "selection_source": None, "selection_key": None,
            "scope_key": "all", "input_mode": "artifact", "upstream_entities": [
                {"skill": row["skill"], "entity_type": row["entity_type"], "entity_ref": row["entity_ref"], "content": row["content"]}
                for row in condition_entities if row["entity_type"] == "model"
            ],
            "upstream_runtime_units": [{"skill": "test-condition-design", "runtime_unit_key": "model:ep-001", "generation_fingerprint": ep["generation_fingerprint"]}],
            "static_data_versions": {}, "authority_refs": [], "reference_refs": [],
        }
        tdr_input = {
            "current_source_targets": [{
                "source_model_key": "ep-001", "target_ref": target["target_ref"],
                "target_content_fingerprint": target["target_content_fingerprint"], "generation_fingerprint": ep["generation_fingerprint"],
            } for target in ep["payload"]["targets"]],
            "requirements": [{
                "requirement_key": "role", "environment_key": None, "dimension_key": "role", "operator": "enum", "authority_refs": [],
                "source_model_key": "ep-001", "source_target_versions": [],
                "values": [{"type": "string", "value": "admin"}, {"type": "string", "value": "user"}],
            }],
        }
        tdr = run_script(TDR_SCRIPT, {"metadata": tdr_metadata, "input": tdr_input})
        self.assertEqual(tdr["result_status"], "ready")
        requirement_rows = tdr["payload"]["normalized_requirements"]
        requirement_entities = tdr["payload"]["entities"]

        materialize_meta = {
            "envelope_version": "1", "skill": "test-condition-design", "runtime_contract_version": "runtime-v1", "generator_contract_version": "materialize-coverage-v1",
            "runtime_unit_key": "artifact:materialize_coverage:TCN-001", "model_key": None, "model_type": None, "technique_slug": None, "selection_source": None, "selection_key": None,
            "scope_key": "TCN-001", "input_mode": "artifact", "upstream_entities": [
                {"skill": row["skill"], "entity_type": row["entity_type"], "entity_ref": row["entity_ref"], "content": row["content"]} for row in condition_entities
            ] + [
                {"skill": row["skill"], "entity_type": row["entity_type"], "entity_ref": row["entity_ref"], "content": row["content"]} for row in requirement_entities
            ], "upstream_runtime_units": [
                {"skill": "test-condition-design", "runtime_unit_key": "model:ep-001", "generation_fingerprint": ep["generation_fingerprint"]},
                {"skill": "test-condition-design", "runtime_unit_key": "artifact:test_data_requirements:all", "generation_fingerprint": tdr["generation_fingerprint"]},
            ], "static_data_versions": {}, "authority_refs": [], "reference_refs": [],
        }
        model_result = {"skill": "test-condition-design", "model_key": "ep-001", "model_type": "ep", "technique_slug": "ep", "runtime_unit_key": "model:ep-001", "input_fingerprint": ep["input_fingerprint"], "model_fingerprint": ep["model_fingerprint"], "generator_contract_version": ep["generator_contract_version"], "generation_fingerprint": ep["generation_fingerprint"], "support_status": ep["support_status"], "runtime_status": ep["runtime_status"], "result_status": ep["result_status"], "deterministic_generated": ep["deterministic_generated"], "freshness_status": "current", "targets": ep["payload"]["targets"], "unsupported_items": [], "coverage_summary": ep["payload"]["coverage_summary"]}
        annotations = [{"target_ref": target["target_ref"], "target_content_fingerprint": target["target_content_fingerprint"], "generation_fingerprint": ep["generation_fingerprint"], "priority": "中", "priority_override_reason": None, "expected_result_root": f"root-{target['target_key'].replace(':', '-')}", "test_data_requirement_refs": ["data:role"]} for target in ep["payload"]["targets"]]
        materialize_input = {"tcn_id": "TCN-001", "active_model_metadata": condition["payload"]["active_model_metadata"], "models": [model_result], "semantic_coverage_items": [], "test_data_requirements": requirement_rows, "target_annotations": annotations, "target_dispositions": [], "previous_target_id_map": [], "previous_semantic_ci_map": [], "previous_ci_ids": [], "previous_expected_result_roots": [], "merge_groups": []}
        materialize = run_script(MATERIALIZE_SCRIPT, {"metadata": materialize_meta, "input": materialize_input})
        self.assertEqual(materialize["result_status"], "ready")
        entities = [tr_entity, selection_entity] + condition_entities + requirement_entities + materialize["payload"]["entities"]
        for entity in entities:
            try:
                runtime.validate_machine_entity(entity)
            except runtime.InvalidInput as exc:
                self.fail(f"invalid current entity {(entity.get('skill'), entity.get('entity_type'), entity.get('entity_ref'))}: {exc}")
        runtime.validate_entity_collection(entities)

        case_metadata = {
            "envelope_version": "1", "skill": "test-case-design", "runtime_contract_version": "runtime-v1", "generator_contract_version": "case-structure-v1",
            "runtime_unit_key": "artifact:case_structure:all", "model_key": None, "model_type": None, "technique_slug": None, "selection_source": None, "selection_key": None,
            "scope_key": None, "input_mode": "artifact", "upstream_entities": [], "upstream_runtime_units": [], "static_data_versions": {}, "authority_refs": [], "reference_refs": [],
        }
        ci_entities = [row for row in materialize["payload"]["entities"] if row["entity_type"] == "ci"]
        data_entities = requirement_entities
        case_current_entities = [tr_entity, next(row for row in condition_entities if row["entity_type"] == "tcn"), *ci_entities, *data_entities]
        case_metadata["upstream_entities"] = [
            {"skill": row["skill"], "entity_type": row["entity_type"], "entity_ref": row["entity_ref"], "content": row["content"]}
            for row in case_current_entities
        ]
        case_input = {
            "test_conditions": [{"tcn_id": "TCN-001", "tr_refs": ["TR-001"], "priority": "中"}],
            "coverage_items": [row["content"] for row in ci_entities], "environment_requirements": [], "test_data_requirements": [row["content"] for row in data_entities],
            "test_cases": [{
                "draft_key": "tc-admin", "identity_action": "new", "reuse_id": None, "title_or_purpose": "管理者ロールを確認する", "tr_refs": ["TR-001"],
                "tcn_refs": ["TCN-001"], "ci_refs": [ci_entities[0]["entity_ref"]], "environment_requirement_refs": [], "test_data_requirement_refs": ["data:role"],
                "priority": "中", "priority_override_reason": None, "preconditions": ["対象環境を準備する"], "test_data": ["role=admin"],
                "steps": [{"number": 1, "text": "管理者として操作する"}], "expected_results": [{"number": 1, "text": "管理者向け結果が表示される", "authority_refs": []}], "postconditions_or_cleanup": ["作成データを削除する"],
            }],
            "dispositions": [], "previous_tc_ids": [], "update_scope_tc_ids": [],
        }
        case_result = run_script(CASE_SCRIPT, {"metadata": case_metadata, "input": case_input})
        self.assertEqual(case_result["result_status"], "ready", case_result)

        artifact_parts = [
            runtime.render_runtime_input("test-condition-design", condition_meta, condition_input()),
            runtime.render_runtime_result("test-condition-design", condition),
            runtime.render_runtime_input("test-condition-design", ep_metadata(), ep_input()),
            runtime.render_runtime_result("test-condition-design", ep),
            runtime.render_runtime_input("test-condition-design", tdr_metadata, tdr_input),
            runtime.render_runtime_result("test-condition-design", tdr),
            runtime.render_runtime_input("test-condition-design", materialize_meta, materialize_input),
            runtime.render_runtime_result("test-condition-design", materialize),
            runtime.render_machine_entities("test-condition-design", condition_entities + requirement_entities + materialize["payload"]["entities"]),
            runtime.render_machine_entities("test-requirement-design", [tr_entity]),
            runtime.render_machine_entities("test-analysis", [selection_entity]),
        ]
        artifact = "\n".join(artifact_parts)
        normalized = {
            "tcn_id": "TCN-001", "test_conditions": [{"tcn_id": "TCN-001"}], "models": [{"model_key": "ep-001", "model_type": "ep"}],
            "ci_ids": [row["ci_id"] for row in materialize["payload"]["ci_id_state"] if row["status"] == "active"],
            "test_data_requirements": requirement_rows,
        }
        workflow_normalized = {
            **normalized,
            "upstream_entities": [
                {"skill": row["skill"], "entity_type": row["entity_type"], "entity_ref": row["entity_ref"]}
                for row in (tr_entity, selection_entity)
            ],
        }
        evidence_request = {"operation": "verify_runtime_evidence", "skill": "test-condition-design", "normalized_skill_input": normalized, "artifact_markdown": artifact, "previous_artifact_markdown": None}
        evidence = runtime.verify_runtime_evidence(evidence_request)
        self.assertTrue(evidence["valid"], evidence)
        cli_evidence = run_script(RUNTIME_PATH, evidence_request)
        self.assertTrue(cli_evidence["valid"], cli_evidence)

        rows = [runtime.runtime_unit_row(condition), runtime.runtime_unit_row(ep), runtime.runtime_unit_row(tdr), runtime.runtime_unit_row(materialize, materialize=materialize["payload"])]
        workflow_input = {
            "workflow_scopes": [{"skill": "test-condition-design", "target": None, "execution_range": None, "input_mode": "artifact", "normalized_input": workflow_normalized, "current_structure_state": {"tcn_id": "TCN-001"}}],
            "runtime_units": rows, "current_runtime_units": rows + [runtime.runtime_unit_row(requirement)], "current_entities": entities, "unsupported_item_closures": [],
        }
        workflow = run_script(WORKFLOW_SCRIPT, {"metadata": workflow_metadata(), "input": workflow_input})
        self.assertEqual(workflow["runtime_status"], "ok", workflow)
        self.assertTrue(workflow["payload"]["can_complete"], workflow)

    def test_duplicate_target_closes_across_materialize_scopes_at_current_ci(self) -> None:
        def model_run(model_key: str, tcn_id: str) -> tuple[dict, dict]:
            model_metadata = ep_metadata()
            model_metadata.update({"runtime_unit_key": f"model:{model_key}", "model_key": model_key, "selection_key": f"SEL-{model_key[-3:]}"})
            result = run_script(EP_SCRIPT, {"metadata": model_metadata, "input": ep_input()})
            model_content = {
                "derived_from_model_key": None, "model_key": model_key, "model_type": "ep", "parent_tcn_id": tcn_id,
                "selection_key": f"SEL-{model_key[-3:]}", "selection_source": "analysis", "status": "active", "technique_slug": "ep",
            }
            tcn_content = {"tcn_id": tcn_id, "tr_refs": ["TR-001"], "priority": 1}
            metadata = {
                "envelope_version": "1", "skill": "test-condition-design", "runtime_contract_version": "runtime-v1", "generator_contract_version": "materialize-coverage-v1",
                "runtime_unit_key": f"artifact:materialize_coverage:{tcn_id}", "model_key": None, "model_type": None, "technique_slug": None, "selection_source": None, "selection_key": None,
                "scope_key": tcn_id, "input_mode": "artifact", "upstream_entities": [
                    {"skill": "test-condition-design", "entity_type": "tcn", "entity_ref": tcn_id, "content": tcn_content},
                    {"skill": "test-condition-design", "entity_type": "model", "entity_ref": model_key, "content": model_content},
                ],
                "upstream_runtime_units": [{"skill": "test-condition-design", "runtime_unit_key": f"model:{model_key}", "generation_fingerprint": result["generation_fingerprint"]}],
                "static_data_versions": {}, "authority_refs": [], "reference_refs": [],
            }
            active_model = {"model_key": model_key, "model_type": "ep", "technique_slug": "ep", "parent_tcn_id": tcn_id, "content_fingerprint": runtime.sha256_digest(model_content)}
            model_result = {
                "skill": "test-condition-design", "model_key": model_key, "model_type": "ep", "technique_slug": "ep", "runtime_unit_key": f"model:{model_key}",
                "input_fingerprint": result["input_fingerprint"], "model_fingerprint": result["model_fingerprint"], "generator_contract_version": result["generator_contract_version"],
                "generation_fingerprint": result["generation_fingerprint"], "support_status": result["support_status"], "runtime_status": result["runtime_status"],
                "result_status": result["result_status"], "deterministic_generated": result["deterministic_generated"], "freshness_status": "current", "targets": result["payload"]["targets"],
                "unsupported_items": [], "coverage_summary": result["payload"]["coverage_summary"],
            }
            return result, {"metadata": metadata, "input": {"tcn_id": tcn_id, "active_model_metadata": [active_model], "models": [model_result], "semantic_coverage_items": [], "test_data_requirements": [], "target_annotations": [], "target_dispositions": [], "previous_target_id_map": [], "previous_semantic_ci_map": [], "previous_ci_ids": [], "previous_expected_result_roots": [], "merge_groups": []}}

        ep_a, request_a = model_run("ep-001", "TCN-001")
        ep_b, request_b = model_run("ep-002", "TCN-002")
        target_a = ep_a["payload"]["targets"][0]
        target_b = ep_b["payload"]["targets"][0]
        request_a["input"]["target_dispositions"] = [{
            "target_ref": target_a["target_ref"], "target_content_fingerprint": target_a["target_content_fingerprint"], "generation_fingerprint": ep_a["generation_fingerprint"],
            "handling": "重複", "reason": "TCN-002 current target covers this target", "authority_refs": [],
            "covered_by_target_version": {"target_ref": target_b["target_ref"], "target_content_fingerprint": target_b["target_content_fingerprint"], "generation_fingerprint": ep_b["generation_fingerprint"], "execution_fingerprint": target_b["execution_fingerprint"]},
        }]
        request_a["input"]["target_annotations"] = [{
            "target_ref": target["target_ref"], "target_content_fingerprint": target["target_content_fingerprint"], "generation_fingerprint": ep_a["generation_fingerprint"],
            "priority": "中", "priority_override_reason": None, "expected_result_root": f"root-{target['target_key'].replace(':', '-')}", "test_data_requirement_refs": [],
        } for target in ep_a["payload"]["targets"] if target["target_ref"] != target_a["target_ref"]]
        request_b["input"]["target_annotations"] = [{
            "target_ref": target["target_ref"], "target_content_fingerprint": target["target_content_fingerprint"], "generation_fingerprint": ep_b["generation_fingerprint"],
            "priority": "中", "priority_override_reason": None, "expected_result_root": f"root-{target['target_key'].replace(':', '-')}", "test_data_requirement_refs": [],
        } for target in ep_b["payload"]["targets"]]
        materialize_a = run_script(MATERIALIZE_SCRIPT, request_a)
        materialize_b = run_script(MATERIALIZE_SCRIPT, request_b)
        self.assertEqual(materialize_a["result_status"], "ready", materialize_a)
        self.assertEqual(materialize_b["result_status"], "ready", materialize_b)

        root_generation = runtime.sha256_digest({"condition_structure": "both-current-scopes"})
        root = {"skill": "test-condition-design", "runtime_unit_key": "artifact:condition_structure:all", "model_key": None, "support_status": "supported", "result_status": "ready", "runtime_status": "ok", "runtime_required": True, "deterministic_generated": True, "generation_fingerprint": root_generation, "upstream_entity_fingerprints": [], "upstream_runtime_units": [], "unsupported_items": [], "freshness_status": "current", "model_completion": [], "target_mappings": [], "target_dispositions": []}
        runtime_rows = [
            root, runtime.runtime_unit_row(ep_a), runtime.runtime_unit_row(ep_b),
            runtime.runtime_unit_row(materialize_a, materialize=materialize_a["payload"]), runtime.runtime_unit_row(materialize_b, materialize=materialize_b["payload"]),
        ]
        entities = []
        for model_key, tcn_id in (("ep-001", "TCN-001"), ("ep-002", "TCN-002")):
            model_content = {
                "derived_from_model_key": None, "model_key": model_key, "model_type": "ep", "parent_tcn_id": tcn_id,
                "selection_key": f"SEL-{model_key[-3:]}", "selection_source": "analysis", "status": "active", "technique_slug": "ep",
            }
            entities.extend([
                runtime.make_machine_entity("test-condition-design", "tcn", tcn_id, {"tcn_id": tcn_id, "tr_refs": ["TR-001"], "priority": 1}),
                runtime.make_machine_entity("test-condition-design", "model", model_key, model_content, model_key=model_key),
            ])
        entities.extend(materialize_a["payload"]["entities"])
        entities.extend(materialize_b["payload"]["entities"])
        normalized = [
            {"tcn_id": "TCN-001", "test_conditions": [{"tcn_id": "TCN-001", "tr_refs": ["TR-001"], "priority": "中"}], "models": [{"model_key": "ep-001", "model_type": "ep"}], "ci_ids": [row["ci_id"] for row in materialize_a["payload"]["ci_id_state"] if row["status"] == "active"]},
            {"tcn_id": "TCN-002", "test_conditions": [{"tcn_id": "TCN-002", "tr_refs": ["TR-001"], "priority": "中"}], "models": [{"model_key": "ep-002", "model_type": "ep"}], "ci_ids": [row["ci_id"] for row in materialize_b["payload"]["ci_id_state"] if row["status"] == "active"]},
        ]
        workflow_input = {
            "workflow_scopes": [{"skill": "test-condition-design", "target": row["tcn_id"], "execution_range": None, "input_mode": "artifact", "normalized_input": row, "current_structure_state": {"tcn_id": row["tcn_id"]}} for row in normalized],
            "runtime_units": runtime_rows, "current_runtime_units": runtime_rows, "current_entities": entities, "unsupported_item_closures": [],
        }
        workflow = run_script(WORKFLOW_SCRIPT, {"metadata": workflow_metadata(), "input": workflow_input})
        self.assertEqual(workflow["result_status"], "ready", workflow)
        self.assertTrue(workflow["payload"]["can_complete"])

        traceability_metadata = {**workflow_metadata(), "skill": "coverage-analysis", "generator_contract_version": "traceability-v1", "runtime_unit_key": "artifact:traceability:all"}
        traceability = run_script(TRACEABILITY_SCRIPT, {"metadata": traceability_metadata, "input": {
            "analysis_scopes": [{"skill": "test-condition-design", "target": row["tcn_id"], "execution_range": None, "input_mode": "artifact", "normalized_input": row, "current_structure_state": {"tcn_id": row["tcn_id"]}} for row in normalized],
            "nodes": [], "edges": [], "dispositions": [], "runtime_units": runtime_rows, "current_runtime_units": runtime_rows, "current_entities": entities, "unsupported_item_closures": [],
        }})
        self.assertEqual(traceability["result_status"], "ready", traceability)
        self.assertTrue(traceability["payload"]["can_complete"])


if __name__ == "__main__":
    unittest.main()
