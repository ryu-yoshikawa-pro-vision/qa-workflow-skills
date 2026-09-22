from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest


REPO_ROOT = Path(__file__).resolve().parents[3]
CONDITION_SCRIPT = REPO_ROOT / "skills" / "test-condition-design" / "scripts" / "condition_structure.py"
EP_SCRIPT = REPO_ROOT / "skills" / "test-condition-design" / "scripts" / "equivalence_partitions.py"
MATERIALIZE_SCRIPT = REPO_ROOT / "skills" / "test-condition-design" / "scripts" / "materialize_coverage.py"
WORKFLOW_SCRIPT = REPO_ROOT / "skills" / "qa-workflow" / "scripts" / "workflow_runtime.py"
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
    def test_standalone_evidence_and_qa_workflow_integration(self) -> None:
        condition = run_script(CONDITION_SCRIPT, {"metadata": condition_metadata(), "input": condition_input()})
        self.assertEqual(condition["result_status"], "ready")
        condition_entities = condition["payload"]["entities"]
        ep = run_script(EP_SCRIPT, {"metadata": ep_metadata(), "input": ep_input()})
        self.assertEqual(ep["result_status"], "ready")

        materialize_meta = {
            "envelope_version": "1", "skill": "test-condition-design", "runtime_contract_version": "runtime-v1", "generator_contract_version": "materialize-coverage-v1",
            "runtime_unit_key": "artifact:materialize_coverage:TCN-001", "model_key": None, "model_type": None, "technique_slug": None, "selection_source": None, "selection_key": None,
            "scope_key": "TCN-001", "input_mode": "artifact", "upstream_entities": [
                {"skill": row["skill"], "entity_type": row["entity_type"], "entity_ref": row["entity_ref"], "content": row["content"]} for row in condition_entities
            ], "upstream_runtime_units": [], "static_data_versions": {}, "authority_refs": [], "reference_refs": [],
        }
        model_result = {"skill": "test-condition-design", "model_key": "ep-001", "model_type": "ep", "technique_slug": "ep", "runtime_unit_key": "model:ep-001", "input_fingerprint": ep["input_fingerprint"], "model_fingerprint": ep["model_fingerprint"], "generator_contract_version": ep["generator_contract_version"], "generation_fingerprint": ep["generation_fingerprint"], "support_status": ep["support_status"], "runtime_status": ep["runtime_status"], "result_status": ep["result_status"], "deterministic_generated": ep["deterministic_generated"], "freshness_status": "current", "targets": ep["payload"]["targets"], "unsupported_items": [], "coverage_summary": ep["payload"]["coverage_summary"]}
        annotations = [{"target_ref": target["target_ref"], "target_content_fingerprint": target["target_content_fingerprint"], "generation_fingerprint": ep["generation_fingerprint"], "priority": "中", "priority_override_reason": None, "expected_result_root": f"root-{target['target_key'].replace(':', '-')}", "test_data_requirement_refs": []} for target in ep["payload"]["targets"]]
        materialize_input = {"tcn_id": "TCN-001", "active_model_metadata": condition["payload"]["active_model_metadata"], "models": [model_result], "semantic_coverage_items": [], "test_data_requirements": [], "target_annotations": annotations, "target_dispositions": [], "previous_target_id_map": [], "previous_semantic_ci_map": [], "previous_ci_ids": [], "previous_expected_result_roots": [], "merge_groups": []}
        materialize = run_script(MATERIALIZE_SCRIPT, {"metadata": materialize_meta, "input": materialize_input})
        self.assertEqual(materialize["result_status"], "ready")
        entities = condition_entities + materialize["payload"]["entities"]

        artifact_parts = [
            runtime.render_runtime_input("test-condition-design", condition_metadata(), condition_input()),
            runtime.render_runtime_result("test-condition-design", condition),
            runtime.render_runtime_input("test-condition-design", ep_metadata(), ep_input()),
            runtime.render_runtime_result("test-condition-design", ep),
            runtime.render_runtime_input("test-condition-design", materialize_meta, materialize_input),
            runtime.render_runtime_result("test-condition-design", materialize),
            runtime.render_machine_entities("test-condition-design", entities),
        ]
        artifact = "\n".join(artifact_parts)
        normalized = {"tcn_id": "TCN-001", "test_conditions": [{"tcn_id": "TCN-001"}], "models": [{"model_key": "ep-001", "model_type": "ep"}], "ci_ids": [row["ci_id"] for row in materialize["payload"]["ci_id_state"] if row["status"] == "active"]}
        evidence_request = {"operation": "verify_runtime_evidence", "skill": "test-condition-design", "normalized_skill_input": normalized, "artifact_markdown": artifact, "previous_artifact_markdown": None}
        evidence = runtime.verify_runtime_evidence(evidence_request)
        self.assertTrue(evidence["valid"], evidence)
        cli_evidence = run_script(RUNTIME_PATH, evidence_request)
        self.assertTrue(cli_evidence["valid"], cli_evidence)

        rows = [runtime.runtime_unit_row(condition), runtime.runtime_unit_row(ep), runtime.runtime_unit_row(materialize, materialize=materialize["payload"])]
        workflow_input = {
            "workflow_scopes": [{"skill": "test-condition-design", "target": None, "execution_range": None, "input_mode": "artifact", "normalized_input": normalized, "current_structure_state": {"tcn_id": "TCN-001"}}],
            "runtime_units": rows, "current_runtime_units": rows, "current_entities": entities, "unsupported_item_closures": [],
        }
        workflow = run_script(WORKFLOW_SCRIPT, {"metadata": workflow_metadata(), "input": workflow_input})
        self.assertEqual(workflow["runtime_status"], "ok")
        self.assertTrue(workflow["payload"]["can_complete"], workflow)


if __name__ == "__main__":
    unittest.main()
