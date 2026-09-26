from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import re
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
        model_result = runtime.current_model_result_row(schema, schema_metadata)
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
        model_result = runtime.current_model_result_row(ep, ep_metadata())
        annotations = [{"target_ref": target["target_ref"], "target_content_fingerprint": target["target_content_fingerprint"], "generation_fingerprint": ep["generation_fingerprint"], "priority": "中", "priority_override_reason": None, "expected_result_root": f"root-{target['target_key'].replace(':', '-')}", "test_data_requirement_refs": ["data:role"]} for target in ep["payload"]["targets"]]
        materialize_input = {"tcn_id": "TCN-001", "active_model_metadata": condition["payload"]["active_model_metadata"], "models": [model_result], "semantic_coverage_items": [], "test_data_requirements": requirement_rows, "target_annotations": annotations, "target_dispositions": [], "previous_target_id_map": [], "previous_semantic_ci_map": [], "previous_ci_ids": [], "previous_expected_result_roots": [], "merge_groups": []}
        materialize = run_script(MATERIALIZE_SCRIPT, {"metadata": materialize_meta, "input": materialize_input})
        self.assertEqual(materialize["result_status"], "ready")
        tdr_entity_by_ref = {row["entity_ref"]: row for row in requirement_entities}
        for ci in materialize["payload"]["entities"]:
            dependencies = {
                (row["skill"], row["entity_type"], row["entity_ref"]): row["content_fingerprint"]
                for row in ci["upstream_entity_dependencies"]
            }
            self.assertEqual(set(dependencies), {
                ("test-condition-design", "tcn", "TCN-001"),
                ("test-condition-design", "model", "ep-001"),
                ("test-condition-design", "test_data_requirement", "data:role"),
            })
            self.assertEqual(dependencies[("test-condition-design", "test_data_requirement", "data:role")], tdr_entity_by_ref["data:role"]["content_fingerprint"])
        self.assertEqual({row["entity_ref"] for row in requirement_entities}, {"data:role"})
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
        evidence_request = {"operation": "verify_runtime_evidence", "skill": "test-condition-design", "normalized_skill_input": normalized, "artifact_markdown": artifact, "previous_artifact_markdown": None,
            "partial_rerun": False,
        }
        evidence = runtime.verify_runtime_evidence(evidence_request)
        self.assertTrue(evidence["valid"], evidence)
        cli_evidence = run_script(RUNTIME_PATH, evidence_request)
        self.assertTrue(cli_evidence["valid"], cli_evidence)

        def without_block(markdown: str, title: str) -> str:
            return re.sub(
                rf"(?ms)^### {re.escape(title)}\r?\n.*?(?=^### |\Z)",
                "",
                markdown,
                count=1,
            )

        missing_root_artifact = without_block(
            without_block(artifact, "Machine Runtime Input: test-condition-design::artifact:condition_structure:all"),
            "Machine Runtime Result: test-condition-design::artifact:condition_structure:all",
        )
        missing_root = run_script(RUNTIME_PATH, {**evidence_request, "artifact_markdown": missing_root_artifact})
        self.assertFalse(missing_root["valid"], missing_root)
        self.assertIn("test-condition-design::artifact:condition_structure:all", missing_root["missing"])

        missing_entities_artifact = without_block(artifact, "Machine Entities: test-condition-design")
        missing_entities = run_script(RUNTIME_PATH, {**evidence_request, "artifact_markdown": missing_entities_artifact})
        self.assertFalse(missing_entities["valid"], missing_entities)
        self.assertTrue(missing_entities["missing_entities"], missing_entities)

        rows = [runtime.runtime_unit_row(condition), runtime.runtime_unit_row(ep), runtime.runtime_unit_row(tdr), runtime.runtime_unit_row(materialize, materialize=materialize["payload"])]
        workflow_input = {
            "workflow_scopes": [{"skill": "test-condition-design", "target": None, "execution_range": None, "input_mode": "artifact", "normalized_input": workflow_normalized, "current_structure_state": evidence["current_structure_state"]}],
            "runtime_units": rows, "current_runtime_units": rows + [runtime.runtime_unit_row(requirement)], "current_entities": entities, "unsupported_item_closures": [],
        }
        workflow = run_script(WORKFLOW_SCRIPT, {"metadata": workflow_metadata(), "input": workflow_input})
        self.assertEqual(workflow["runtime_status"], "ok", workflow)
        self.assertTrue(workflow["payload"]["can_complete"], workflow)

    def test_multi_tcn_materialize_expected_and_partial_rerun_use_current_structure(self) -> None:
        requirement_metadata = {
            "envelope_version": "1", "skill": "test-requirement-design", "runtime_contract_version": "runtime-v1",
            "generator_contract_version": "requirement-structure-v1", "runtime_unit_key": "artifact:requirement_structure:all",
            "model_key": None, "model_type": None, "technique_slug": None, "selection_source": None, "selection_key": None,
            "scope_key": "all", "input_mode": "direct", "upstream_entities": [], "upstream_runtime_units": [],
            "static_data_versions": {}, "authority_refs": [], "reference_refs": [],
        }
        requirement_input = {
            "authorities": [], "risks": [], "dispositions": [], "previous_tr_ids": [], "update_scope_tr_ids": [],
            "test_requirements": [{
                "draft_key": f"requirement-{number:03d}", "identity_action": "new", "reuse_id": None,
                "text": f"Requirement {number}", "authority_refs": [], "risk_refs": [], "priority": "中",
                "priority_override_reason": None, "test_level": "system", "observation_method": "assertion",
            } for number in (1, 2, 3)],
        }
        requirement_result = run_script(REQUIREMENT_SCRIPT, {"metadata": requirement_metadata, "input": requirement_input})
        self.assertEqual(requirement_result["runtime_status"], "ok", requirement_result)
        self.assertEqual(requirement_result["result_status"], "ready", requirement_result)
        tr_entities = requirement_result["payload"]["entities"]
        self.assertEqual({row["entity_ref"] for row in tr_entities}, {"TR-001", "TR-002", "TR-003"})
        self.assertTrue(all(row["runtime_dependencies"] for row in tr_entities))
        selection = runtime.make_machine_entity(
            "test-analysis", "technique_selection", "SEL-001",
            {"selection_key": "SEL-001", "selected_techniques": ["ep"]},
        )
        upstream_rows = [
            {"skill": row["skill"], "entity_type": row["entity_type"], "entity_ref": row["entity_ref"], "content": row["content"]}
            for row in [*tr_entities, selection]
        ]
        tr_by_ref = {row["entity_ref"]: row for row in tr_entities}
        disposition = {
            "upstream_entity": runtime.machine_entity_dependency(tr_by_ref["TR-003"]),
            "handling": "対象外", "reason": "No applicable condition", "authority_refs": [], "covered_by_entity": None,
        }

        def condition_input(*, partial: bool, tcn_state: list[dict] | None = None, model_state: list[dict] | None = None) -> dict:
            tcn_rows = [
                {"draft_key": "condition-001", "identity_action": "reuse" if partial else "new", "reuse_id": "TCN-001" if partial else None,
                 "tr_refs": ["TR-001"], "condition": "updated checkout role" if partial else "checkout role", "category": None,
                 "technique_slugs": ["ep"], "coverage_criterion": "each partition", "authority_refs": [], "risk_refs": [],
                 "priority": 1, "priority_override_reason": None},
            ]
            model_rows = [
                {"draft_key": "model-001", "model_type": "ep", "technique_slug": "ep", "selection_source": "analysis", "selection_key": "SEL-001",
                 "derived_from_model_draft_key": None, "identity_action": "reuse" if partial else "new", "reuse_model_key": "ep-001" if partial else None,
                 "parent_tcn_draft_key": "condition-001"},
            ]
            if not partial:
                tcn_rows.append({
                    "draft_key": "condition-002", "identity_action": "new", "reuse_id": None,
                    "tr_refs": ["TR-002"], "condition": "checkout permission", "category": None,
                    "technique_slugs": ["ep"], "coverage_criterion": "each partition", "authority_refs": [], "risk_refs": [],
                    "priority": 1, "priority_override_reason": None,
                })
                model_rows.append({
                    "draft_key": "model-002", "model_type": "ep", "technique_slug": "ep", "selection_source": "analysis", "selection_key": "SEL-001",
                    "derived_from_model_draft_key": None, "identity_action": "new", "reuse_model_key": None,
                    "parent_tcn_draft_key": "condition-002",
                })
            return {
                "test_requirements": [
                    {"tr_id": "TR-001", "priority": 1, "authority_refs": [], "risk_refs": []},
                    {"tr_id": "TR-002", "priority": 1, "authority_refs": [], "risk_refs": []},
                    *([] if partial else [{"tr_id": "TR-003", "priority": 1, "authority_refs": [], "risk_refs": []}]),
                ],
                "technique_selections": [{"selection_key": "SEL-001", "selected_techniques": ["ep"], "undetermined_signal_closures": [], "status": "active"}],
                "test_conditions": tcn_rows,
                "requirement_dispositions": [] if partial else [disposition],
                "models": model_rows,
                "previous_tcn_ids": tcn_state or [], "previous_model_keys": model_state or [],
                "update_scope_tcn_ids": ["TCN-001"] if partial else [],
                "update_scope_model_keys": ["ep-001"] if partial else [],
            }

        def condition_run(value: dict) -> tuple[dict, dict]:
            metadata = condition_metadata()
            metadata.update({"input_mode": "artifact", "upstream_entities": upstream_rows})
            return metadata, run_script(CONDITION_SCRIPT, {"metadata": metadata, "input": value})

        def model_run(model_key: str) -> tuple[dict, dict]:
            metadata = ep_metadata()
            metadata.update({"runtime_unit_key": f"model:{model_key}", "model_key": model_key, "selection_key": "SEL-001"})
            return metadata, run_script(EP_SCRIPT, {"metadata": metadata, "input": ep_input()})

        def tdr_run(model_entity: dict, model_metadata: dict, model_result: dict) -> tuple[dict, dict]:
            metadata = {
                "envelope_version": "1", "skill": "test-condition-design", "runtime_contract_version": "runtime-v1", "generator_contract_version": "test-data-requirements-v1",
                "runtime_unit_key": "artifact:test_data_requirements:all", "model_key": None, "model_type": None, "technique_slug": None,
                "selection_source": None, "selection_key": None, "scope_key": "all", "input_mode": "artifact",
                "upstream_entities": [{"skill": model_entity["skill"], "entity_type": model_entity["entity_type"], "entity_ref": model_entity["entity_ref"], "content": model_entity["content"]}],
                "upstream_runtime_units": [{"skill": "test-condition-design", "runtime_unit_key": model_metadata["runtime_unit_key"], "generation_fingerprint": model_result["generation_fingerprint"]}],
                "static_data_versions": {}, "authority_refs": [], "reference_refs": [],
            }
            source_targets = [{
                "source_model_key": model_entity["entity_ref"], "target_ref": target["target_ref"],
                "target_content_fingerprint": target["target_content_fingerprint"], "generation_fingerprint": model_result["generation_fingerprint"],
            } for target in model_result["payload"]["targets"]]
            requirement = {
                "requirement_key": "REQ-002", "environment_key": None, "dimension_key": "role", "operator": "enum", "authority_refs": [],
                "source_model_key": model_entity["entity_ref"], "source_target_versions": [],
                "values": [{"type": "string", "value": "admin"}, {"type": "string", "value": "user"}],
            }
            return metadata, run_script(TDR_SCRIPT, {"metadata": metadata, "input": {"current_source_targets": source_targets, "requirements": [requirement]}})

        def materialize_run(
            tcn_id: str, tcn_entity: dict, model_entity: dict, model_metadata: dict, model_result: dict,
            model_entity_rows: list[dict], tdr_result: dict | None, previous_materialize: dict | None = None,
        ) -> tuple[dict, dict, dict]:
            data_rows = [] if tdr_result is None else [row for row in tdr_result["payload"]["normalized_requirements"] if row["source_model_key"] == model_entity["entity_ref"]]
            tdr_entities = [] if tdr_result is None else [row for row in tdr_result["payload"]["entities"] if row["content"]["source_model_key"] == model_entity["entity_ref"]]
            metadata = {
                "envelope_version": "1", "skill": "test-condition-design", "runtime_contract_version": "runtime-v1", "generator_contract_version": "materialize-coverage-v1",
                "runtime_unit_key": f"artifact:materialize_coverage:{tcn_id}", "model_key": None, "model_type": None, "technique_slug": None,
                "selection_source": None, "selection_key": None, "scope_key": tcn_id, "input_mode": "artifact",
                "upstream_entities": [
                    *[{"skill": row["skill"], "entity_type": row["entity_type"], "entity_ref": row["entity_ref"], "content": row["content"]} for row in [tcn_entity, model_entity]],
                    *[{"skill": row["skill"], "entity_type": row["entity_type"], "entity_ref": row["entity_ref"], "content": row["content"]} for row in tdr_entities],
                ],
                "upstream_runtime_units": [
                    {"skill": "test-condition-design", "runtime_unit_key": model_metadata["runtime_unit_key"], "generation_fingerprint": model_result["generation_fingerprint"]},
                    *([] if tdr_result is None or not data_rows else [{"skill": "test-condition-design", "runtime_unit_key": "artifact:test_data_requirements:all", "generation_fingerprint": tdr_result["generation_fingerprint"]}]),
                ],
                "static_data_versions": {}, "authority_refs": [], "reference_refs": [],
            }
            target_annotations = [{
                "target_ref": target["target_ref"], "target_content_fingerprint": target["target_content_fingerprint"],
                "generation_fingerprint": model_result["generation_fingerprint"], "priority": "中", "priority_override_reason": None,
                "expected_result_root": f"root-{target['target_key'].replace(':', '-')}",
                "test_data_requirement_refs": [row["data_ref"] for row in data_rows],
            } for target in model_result["payload"]["targets"]]
            previous_payload = previous_materialize["payload"] if previous_materialize is not None else {}
            value = {
                "tcn_id": tcn_id,
                "active_model_metadata": [row for row in model_entity_rows if row["parent_tcn_id"] == tcn_id],
                "models": [runtime.current_model_result_row(model_result, model_metadata)],
                "semantic_coverage_items": [], "test_data_requirements": data_rows,
                "target_annotations": target_annotations, "target_dispositions": [],
                "previous_target_id_map": previous_payload.get("target_mapping_state", []),
                "previous_semantic_ci_map": previous_payload.get("semantic_ci_mapping_state", []),
                "previous_ci_ids": previous_payload.get("ci_id_state", []),
                "previous_expected_result_roots": previous_payload.get("expected_result_root_state", []), "merge_groups": [],
            }
            return metadata, value, run_script(MATERIALIZE_SCRIPT, {"metadata": metadata, "input": value})

        def render_artifact(pairs: list[tuple[dict, dict, dict]], tcd_entities: list[dict]) -> str:
            blocks = []
            for metadata, value, envelope in pairs:
                blocks.append(runtime.render_runtime_input("test-condition-design", metadata, value))
                blocks.append(runtime.render_runtime_result("test-condition-design", envelope))
            blocks.append(runtime.render_machine_entities("test-condition-design", tcd_entities))
            blocks.append(runtime.render_machine_entities("test-requirement-design", tr_entities))
            blocks.append(runtime.render_machine_entities("test-analysis", [selection]))
            return "\n".join(blocks)

        def normalized_input(condition_result: dict, model_results: list[dict], materialize_results: list[dict], tdr_result: dict | None, *, partial: bool) -> dict:
            active_models = condition_result["payload"]["active_model_metadata"]
            active_cis = [
                row["ci_id"]
                for result in materialize_results
                for row in result["payload"]["ci_id_state"]
                if row["status"] == "active"
            ]
            return {
                "tcn_id": "TCN-001", "test_conditions": [{"tcn_id": row["tcn_id"]} for row in condition_result["payload"]["tcn_id_state"] if row["status"] == "active" and (not partial or row["tcn_id"] == "TCN-001")],
                "models": active_models, "ci_ids": active_cis,
                "test_data_requirements": [] if tdr_result is None else tdr_result["payload"]["normalized_requirements"],
                "requirement_dispositions": [] if partial else [disposition],
                "test_requirements": [{"tr_id": "TR-001"}, {"tr_id": "TR-002"}] + ([] if partial else [{"tr_id": "TR-003"}]),
                "previous_tcn_ids": [], "previous_model_keys": [], "previous_ci_ids": [],
                "update_scope_tcn_ids": [], "update_scope_model_keys": [],
            }

        full_condition_value = condition_input(partial=False)
        full_condition_metadata, full_condition = condition_run(full_condition_value)
        self.assertEqual(full_condition["runtime_status"], "ok", full_condition)
        self.assertEqual([row["tcn_id"] for row in full_condition["payload"]["tcn_id_state"]], ["TCN-001", "TCN-002"])
        tcn_by_id = {row["entity_ref"]: row for row in full_condition["payload"]["entities"] if row["entity_type"] == "tcn"}
        model_by_id = {row["entity_ref"]: row for row in full_condition["payload"]["entities"] if row["entity_type"] == "model"}
        metadata_by_model = {row["model_key"]: row for row in full_condition["payload"]["active_model_metadata"]}
        self.assertEqual(set(metadata_by_model), {"ep-001", "ep-002"})

        model_metadata_and_results = {key: model_run(key) for key in ("ep-001", "ep-002")}
        tdr_metadata, tdr_result = tdr_run(model_by_id["ep-002"], *model_metadata_and_results["ep-002"])
        self.assertEqual(tdr_result["result_status"], "ready", tdr_result)
        materialize_values = {}
        for tcn_id, model_key in (("TCN-001", "ep-001"), ("TCN-002", "ep-002")):
            model_metadata, model_result = model_metadata_and_results[model_key]
            materialize_values[tcn_id] = materialize_run(
                tcn_id, tcn_by_id[tcn_id], model_by_id[model_key], model_metadata, model_result,
                full_condition["payload"]["active_model_metadata"], tdr_result if tcn_id == "TCN-002" else None,
            )
            self.assertEqual(materialize_values[tcn_id][2]["result_status"], "ready", materialize_values[tcn_id][2])
        full_pairs = [
            (full_condition_metadata, full_condition_value, full_condition),
            *[(model_metadata_and_results[key][0], ep_input(), model_metadata_and_results[key][1]) for key in ("ep-001", "ep-002")],
            (tdr_metadata, {
                "current_source_targets": [{
                    "source_model_key": "ep-002", "target_ref": target["target_ref"],
                    "target_content_fingerprint": target["target_content_fingerprint"],
                    "generation_fingerprint": model_metadata_and_results["ep-002"][1]["generation_fingerprint"],
                } for target in model_metadata_and_results["ep-002"][1]["payload"]["targets"]],
                "requirements": [{
                    "requirement_key": "REQ-002", "environment_key": None, "dimension_key": "role", "operator": "enum", "authority_refs": [],
                    "source_model_key": "ep-002", "source_target_versions": [],
                    "values": [{"type": "string", "value": "admin"}, {"type": "string", "value": "user"}],
                }],
            }, tdr_result),
            *[materialize_values[tcn_id] for tcn_id in ("TCN-001", "TCN-002")],
        ]
        full_tcd_entities = [*full_condition["payload"]["entities"], *tdr_result["payload"]["entities"]]
        full_tcd_entities.extend(row for _metadata, _value, result in materialize_values.values() for row in result["payload"]["entities"])
        full_artifact = render_artifact(full_pairs, full_tcd_entities)
        full_tcd_normalized = normalized_input(full_condition, list(model_metadata_and_results.values()), [row[2] for row in materialize_values.values()], tdr_result, partial=False)
        full_request = {
            "operation": "verify_runtime_evidence", "skill": "test-condition-design", "normalized_skill_input": full_tcd_normalized,
            "artifact_markdown": full_artifact, "previous_artifact_markdown": None, "partial_rerun": False,
        }
        full_checked = runtime.verify_runtime_evidence(full_request)
        self.assertTrue(full_checked["valid"], full_checked)
        self.assertFalse(any(
            identity.startswith("test-requirement-design::")
            for identity, _body in runtime.extract_machine_blocks(full_artifact, "Machine Runtime Result")
        ))
        expected_runtime_ids = {row["runtime_unit_key"] for row in full_checked["expected_runtime_units"]}
        self.assertIn("artifact:materialize_coverage:TCN-001", expected_runtime_ids)
        self.assertIn("artifact:materialize_coverage:TCN-002", expected_runtime_ids)
        self.assertIsNotNone(full_checked["current_structure_state"])

        def remove_pair(markdown: str, unit: str) -> str:
            identity = f"test-condition-design::{unit}"
            for title in ("Machine Runtime Input", "Machine Runtime Result"):
                markdown = re.sub(
                    rf"(?ms)^### {re.escape(title)}: {re.escape(identity)}\r?\n.*?(?=^### |\Z)",
                    "", markdown, count=1,
                )
            return markdown

        missing_tcn_two = runtime.verify_runtime_evidence({
            **full_request, "artifact_markdown": remove_pair(full_artifact, "artifact:materialize_coverage:TCN-002"),
        })
        self.assertFalse(missing_tcn_two["valid"], missing_tcn_two)
        self.assertIn("test-condition-design::artifact:materialize_coverage:TCN-002", missing_tcn_two["missing"])

        extra_metadata = {
            "envelope_version": "1", "skill": "test-condition-design", "runtime_contract_version": "runtime-v1", "generator_contract_version": "materialize-coverage-v1",
            "runtime_unit_key": "artifact:materialize_coverage:TCN-003", "model_key": None, "model_type": None, "technique_slug": None,
            "selection_source": None, "selection_key": None, "scope_key": "TCN-003", "input_mode": "artifact",
            "upstream_entities": [], "upstream_runtime_units": [], "static_data_versions": {}, "authority_refs": [], "reference_refs": [],
        }
        extra_input = {
            "tcn_id": "TCN-003", "active_model_metadata": [], "models": [], "semantic_coverage_items": [], "test_data_requirements": [],
            "target_annotations": [], "target_dispositions": [], "previous_target_id_map": [], "previous_semantic_ci_map": [],
            "previous_ci_ids": [], "previous_expected_result_roots": [], "merge_groups": [],
        }
        extra_result = run_script(MATERIALIZE_SCRIPT, {"metadata": extra_metadata, "input": extra_input})
        self.assertEqual(extra_result["runtime_unit_key"], "artifact:materialize_coverage:TCN-003")
        extra_artifact = full_artifact + "\n" + runtime.render_runtime_input("test-condition-design", extra_metadata, extra_input) + "\n" + runtime.render_runtime_result("test-condition-design", extra_result)
        extra_checked = runtime.verify_runtime_evidence({**full_request, "artifact_markdown": extra_artifact})
        self.assertFalse(extra_checked["valid"], extra_checked)
        self.assertIn("test-condition-design::artifact:materialize_coverage:TCN-003", extra_checked["extra"])

        full_inputs = dict(runtime.extract_machine_blocks(full_artifact, "Machine Runtime Input"))
        materialize_id = "test-condition-design::artifact:materialize_coverage:TCN-002"
        materialize_body = json.loads(json.dumps(full_inputs[materialize_id]))
        bad_tcn_input = json.loads(json.dumps(materialize_body))
        bad_tcn_input["input"]["tcn_id"] = "TCN-001"
        bad_tcn_artifact = full_artifact.replace(
            runtime.render_runtime_input("test-condition-design", materialize_body["metadata"], materialize_body["input"]),
            runtime.render_runtime_input("test-condition-design", bad_tcn_input["metadata"], bad_tcn_input["input"]),
            1,
        )
        mismatch_tcn = runtime.verify_runtime_evidence({**full_request, "artifact_markdown": bad_tcn_artifact})
        self.assertFalse(mismatch_tcn["valid"], mismatch_tcn)
        self.assertIn("invalid_dispatch_input", [row["issue_type"] for row in mismatch_tcn["issues"]])
        bad_scope_input = json.loads(json.dumps(materialize_body))
        bad_scope_input["metadata"]["scope_key"] = "TCN-001"
        bad_scope_artifact = full_artifact.replace(
            runtime.render_runtime_input("test-condition-design", materialize_body["metadata"], materialize_body["input"]),
            runtime.render_runtime_input("test-condition-design", bad_scope_input["metadata"], bad_scope_input["input"]),
            1,
        )
        mismatch_scope = runtime.verify_runtime_evidence({**full_request, "artifact_markdown": bad_scope_artifact})
        self.assertFalse(mismatch_scope["valid"], mismatch_scope)
        self.assertIn("invalid_dispatch_input", [row["issue_type"] for row in mismatch_scope["issues"]])

        partial_condition_value = condition_input(
            partial=True,
            tcn_state=full_condition["payload"]["tcn_id_state"],
            model_state=full_condition["payload"]["model_key_state"],
        )
        partial_condition_metadata, partial_condition = condition_run(partial_condition_value)
        self.assertEqual(partial_condition["runtime_status"], "ok", partial_condition)
        self.assertEqual({row["model_key"] for row in partial_condition["payload"]["active_model_metadata"]}, {"ep-001"})
        partial_model_metadata, partial_model_result = model_metadata_and_results["ep-001"]
        partial_materialize_previous = materialize_values["TCN-001"][2]
        partial_materialize_metadata, partial_materialize_input, partial_materialize = materialize_run(
            "TCN-001", next(row for row in partial_condition["payload"]["entities"] if row["entity_type"] == "tcn"),
            next(row for row in partial_condition["payload"]["entities"] if row["entity_type"] == "model"),
            partial_model_metadata, partial_model_result, partial_condition["payload"]["active_model_metadata"], None,
            previous_materialize=partial_materialize_previous,
        )
        self.assertEqual(partial_materialize["runtime_status"], "ok", partial_materialize)
        partial_pairs = [
            (partial_condition_metadata, partial_condition_value, partial_condition),
            (partial_model_metadata, ep_input(), partial_model_result),
            (partial_materialize_metadata, partial_materialize_input, partial_materialize),
        ]
        partial_normalized = {
            **normalized_input(partial_condition, [("ep-001", (partial_model_metadata, partial_model_result))], [partial_materialize], None, partial=True),
            "previous_tcn_ids": full_condition["payload"]["tcn_id_state"],
            "previous_model_keys": full_condition["payload"]["model_key_state"],
            "previous_ci_ids": partial_materialize_previous["payload"]["ci_id_state"],
            "update_scope_tcn_ids": ["TCN-001"], "update_scope_model_keys": ["ep-001"],
            "test_data_requirements": [], "requirement_dispositions": [],
        }
        previous_entity_map = runtime._artifact_machine_entity_map(full_artifact)
        previous_entities = [row for rows in previous_entity_map.values() for row in rows]
        previous_results = runtime.extract_machine_blocks(full_artifact, "Machine Runtime Result")
        partial_previous_states = runtime._previous_entity_states("test-condition-design", partial_normalized, previous_results)
        carried = runtime._carry_forward_machine_entities("test-condition-design", partial_normalized, previous_entities, partial_previous_states)
        partial_result_entities = runtime._runtime_result_entities(
            [(f"test-condition-design::{row[0]}", row[2]) for row in partial_pairs], "test-condition-design",
        )
        partial_tcd_entities = [*partial_result_entities, *carried]
        partial_artifact = render_artifact(partial_pairs, partial_tcd_entities)
        partial_request = {
            "operation": "verify_runtime_evidence", "skill": "test-condition-design", "normalized_skill_input": partial_normalized,
            "artifact_markdown": partial_artifact, "previous_artifact_markdown": full_artifact, "partial_rerun": True,
        }
        partial_checked = runtime.verify_runtime_evidence(partial_request)
        self.assertTrue(partial_checked["valid"], partial_checked)
        self.assertIsNotNone(partial_checked["current_structure_state"])
        partial_runtime_ids = {row["identity"] for row in partial_checked["current_structure_state"]["runtime_results"]}
        self.assertIn("test-condition-design::artifact:materialize_coverage:TCN-001", partial_runtime_ids)
        self.assertNotIn("test-condition-design::artifact:materialize_coverage:TCN-002", partial_runtime_ids)
        self.assertFalse(any(identity.startswith("test-requirement-design::") for identity in partial_runtime_ids))
        tcn_two = next(row for row in carried if row["entity_type"] == "tcn" and row["entity_ref"] == "TCN-002")
        tr_two = tr_by_ref["TR-002"]
        self.assertIn(runtime.machine_entity_dependency(tr_two), tcn_two["upstream_entity_dependencies"])
        self.assertTrue(tr_two["runtime_dependencies"])
        self.assertEqual(
            partial_checked["current_structure_state"]["previous_ci_id_state"],
            [{"ci_id": row["ci_id"], "status": row["status"]} for tcn_id in ("TCN-001", "TCN-002") for row in materialize_values[tcn_id][2]["payload"]["ci_id_state"]],
        )
        carry_types = {(row["entity_type"], row["entity_ref"]) for row in partial_checked["current_structure_state"]["carry_forward_entities"]}
        self.assertTrue({("tcn", "TCN-002"), ("model", "ep-002"), ("ci", "TCN-002-CI01"), ("test_data_requirement", "data:REQ-002"), ("disposition", "tr:TR-003")}.issubset(carry_types), carry_types)

    def test_duplicate_target_closes_across_materialize_scopes_at_current_ci(self) -> None:
        def model_run(model_key: str, selection_key: str) -> tuple[dict, dict, dict]:
            model_metadata = ep_metadata()
            model_metadata.update({"runtime_unit_key": f"model:{model_key}", "model_key": model_key, "selection_key": selection_key})
            result = run_script(EP_SCRIPT, {"metadata": model_metadata, "input": ep_input()})
            return result, model_metadata, {}

        condition_value = {
            "test_requirements": [{"tr_id": "TR-001", "priority": 1, "authority_refs": [], "risk_refs": []}],
            "technique_selections": [
                {"selection_key": key, "selected_techniques": ["ep"], "undetermined_signal_closures": [], "status": "active"}
                for key in ("SEL-001", "SEL-002")
            ],
            "test_conditions": [
                {"draft_key": f"condition-{number:03d}", "identity_action": "new", "reuse_id": None, "tr_refs": ["TR-001"],
                 "condition": f"role coverage {number}", "category": None, "technique_slugs": ["ep"], "coverage_criterion": "each partition",
                 "authority_refs": [], "risk_refs": [], "priority": 1, "priority_override_reason": None}
                for number in (1, 2)
            ],
            "requirement_dispositions": [],
            "models": [
                {"draft_key": f"model-{number:03d}", "model_type": "ep", "technique_slug": "ep", "selection_source": "analysis",
                 "selection_key": f"SEL-{number:03d}", "derived_from_model_draft_key": None, "identity_action": "new", "reuse_model_key": None,
                 "parent_tcn_draft_key": f"condition-{number:03d}"}
                for number in (1, 2)
            ],
            "previous_tcn_ids": [], "previous_model_keys": [], "update_scope_tcn_ids": [], "update_scope_model_keys": [],
        }
        condition = run_script(CONDITION_SCRIPT, {"metadata": condition_metadata(), "input": condition_value})
        self.assertEqual(condition["result_status"], "ready", condition)
        tcn_by_id = {row["entity_ref"]: row for row in condition["payload"]["entities"] if row["entity_type"] == "tcn"}
        model_by_id = {row["entity_ref"]: row for row in condition["payload"]["entities"] if row["entity_type"] == "model"}
        metadata_by_model = {row["model_key"]: row for row in condition["payload"]["active_model_metadata"]}

        def materialize_request(tcn_id: str, model_key: str, model_result: dict, model_metadata: dict) -> dict:
            tcn = tcn_by_id[tcn_id]
            model = model_by_id[model_key]
            metadata = {
                "envelope_version": "1", "skill": "test-condition-design", "runtime_contract_version": "runtime-v1", "generator_contract_version": "materialize-coverage-v1",
                "runtime_unit_key": f"artifact:materialize_coverage:{tcn_id}", "model_key": None, "model_type": None, "technique_slug": None, "selection_source": None, "selection_key": None,
                "scope_key": tcn_id, "input_mode": "artifact", "upstream_entities": [
                    {"skill": row["skill"], "entity_type": row["entity_type"], "entity_ref": row["entity_ref"], "content": row["content"]}
                    for row in (tcn, model)
                ],
                "upstream_runtime_units": [{"skill": "test-condition-design", "runtime_unit_key": f"model:{model_key}", "generation_fingerprint": model_result["generation_fingerprint"]}],
                "static_data_versions": {}, "authority_refs": [], "reference_refs": [],
            }
            target_annotations = [{
                "target_ref": target["target_ref"], "target_content_fingerprint": target["target_content_fingerprint"],
                "generation_fingerprint": model_result["generation_fingerprint"], "priority": "中", "priority_override_reason": None,
                "expected_result_root": f"root-{target['target_key'].replace(':', '-')}", "test_data_requirement_refs": [],
            } for target in model_result["payload"]["targets"]]
            return {"metadata": metadata, "input": {
                "tcn_id": tcn_id, "active_model_metadata": [metadata_by_model[model_key]],
                "models": [runtime.current_model_result_row(model_result, model_metadata)], "semantic_coverage_items": [], "test_data_requirements": [],
                "target_annotations": target_annotations, "target_dispositions": [], "previous_target_id_map": [], "previous_semantic_ci_map": [],
                "previous_ci_ids": [], "previous_expected_result_roots": [], "merge_groups": [],
            }}

        ep_a, model_metadata_a, _ = model_run("ep-001", "SEL-001")
        ep_b, model_metadata_b, _ = model_run("ep-002", "SEL-002")
        target_a = ep_a["payload"]["targets"][0]
        target_b = ep_b["payload"]["targets"][0]
        request_a = materialize_request("TCN-001", "ep-001", ep_a, model_metadata_a)
        request_b = materialize_request("TCN-002", "ep-002", ep_b, model_metadata_b)
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

        runtime_rows = [
            runtime.runtime_unit_row(condition), runtime.runtime_unit_row(ep_a), runtime.runtime_unit_row(ep_b),
            runtime.runtime_unit_row(materialize_a, materialize=materialize_a["payload"]), runtime.runtime_unit_row(materialize_b, materialize=materialize_b["payload"]),
        ]
        entities = [*condition["payload"]["entities"], *materialize_a["payload"]["entities"], *materialize_b["payload"]["entities"]]
        models = [
            {"model_key": "ep-001", "model_type": "ep", "technique_slug": "ep", "selection_source": "analysis", "selection_key": "SEL-001"},
            {"model_key": "ep-002", "model_type": "ep", "technique_slug": "ep", "selection_source": "analysis", "selection_key": "SEL-002"},
        ]
        conditions = [{"tcn_id": "TCN-001"}, {"tcn_id": "TCN-002"}]
        ci_ids = {
            "TCN-001": [row["ci_id"] for row in materialize_a["payload"]["ci_id_state"] if row["status"] == "active"],
            "TCN-002": [row["ci_id"] for row in materialize_b["payload"]["ci_id_state"] if row["status"] == "active"],
        }
        full_normalized = {"tcn_id": "TCN-001", "test_conditions": conditions, "models": models, "ci_ids": ci_ids["TCN-001"] + ci_ids["TCN-002"]}
        normalized = [
            {**full_normalized, "tcn_id": tcn_id, "models": [model], "ci_ids": ci_ids[tcn_id]}
            for tcn_id, model in (("TCN-001", models[0]), ("TCN-002", models[1]))
        ]
        artifact_parts = [
            runtime.render_runtime_input("test-condition-design", condition_metadata(), condition_value),
            runtime.render_runtime_result("test-condition-design", condition),
            runtime.render_runtime_input("test-condition-design", model_metadata_a, ep_input()), runtime.render_runtime_result("test-condition-design", ep_a),
            runtime.render_runtime_input("test-condition-design", model_metadata_b, ep_input()), runtime.render_runtime_result("test-condition-design", ep_b),
            runtime.render_runtime_input("test-condition-design", request_a["metadata"], request_a["input"]), runtime.render_runtime_result("test-condition-design", materialize_a),
            runtime.render_runtime_input("test-condition-design", request_b["metadata"], request_b["input"]), runtime.render_runtime_result("test-condition-design", materialize_b),
            runtime.render_machine_entities("test-condition-design", entities),
        ]
        evidence = runtime.verify_runtime_evidence({
            "operation": "verify_runtime_evidence", "skill": "test-condition-design", "normalized_skill_input": full_normalized,
            "artifact_markdown": "\n".join(artifact_parts), "previous_artifact_markdown": None, "partial_rerun": False,
        })
        self.assertTrue(evidence["valid"], evidence)
        current_structure_state = evidence["current_structure_state"]
        scoped_structure_state = {
            **current_structure_state,
            "runtime_results": [
                row for row in current_structure_state["runtime_results"]
                if row["identity"] == "test-condition-design::artifact:condition_structure:all"
            ],
        }
        workflow_input = {
            "workflow_scopes": [{"skill": "test-condition-design", "target": row["tcn_id"], "execution_range": None, "input_mode": "artifact", "normalized_input": row, "current_structure_state": scoped_structure_state} for row in normalized],
            "runtime_units": runtime_rows, "current_runtime_units": runtime_rows, "current_entities": entities, "unsupported_item_closures": [],
        }
        workflow = run_script(WORKFLOW_SCRIPT, {"metadata": workflow_metadata(), "input": workflow_input})
        self.assertEqual(workflow["result_status"], "ready", workflow)
        self.assertTrue(workflow["payload"]["can_complete"])

        traceability_metadata = {**workflow_metadata(), "skill": "coverage-analysis", "generator_contract_version": "traceability-v1", "runtime_unit_key": "artifact:traceability:all"}
        traceability = run_script(TRACEABILITY_SCRIPT, {"metadata": traceability_metadata, "input": {
            "analysis_scopes": [{"skill": "test-condition-design", "target": row["tcn_id"], "execution_range": None, "input_mode": "artifact", "normalized_input": row, "current_structure_state": scoped_structure_state} for row in normalized],
            "nodes": [], "edges": [], "dispositions": [], "runtime_units": runtime_rows, "current_runtime_units": runtime_rows, "current_entities": entities, "unsupported_item_closures": [],
        }})
        self.assertEqual(traceability["result_status"], "ready", traceability)
        self.assertTrue(traceability["payload"]["can_complete"])


if __name__ == "__main__":
    unittest.main()
