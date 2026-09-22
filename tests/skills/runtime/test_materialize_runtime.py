from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest


REPO_ROOT = Path(__file__).resolve().parents[3]
EP_SCRIPT = REPO_ROOT / "skills" / "test-condition-design" / "scripts" / "equivalence_partitions.py"
MATERIALIZE_SCRIPT = REPO_ROOT / "skills" / "test-condition-design" / "scripts" / "materialize_coverage.py"


def digest(value: object) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def ep_metadata() -> dict:
    return {
        "envelope_version": "1", "skill": "test-condition-design", "runtime_contract_version": "runtime-v1",
        "generator_contract_version": "equivalence-partitions-v1", "runtime_unit_key": "model:ep-001", "model_key": "ep-001",
        "model_type": "ep", "technique_slug": "ep", "selection_source": "analysis", "selection_key": "SEL-001",
        "scope_key": None, "input_mode": "direct", "upstream_entities": [], "upstream_runtime_units": [],
        "static_data_versions": {}, "authority_refs": [], "reference_refs": [],
    }


def materialize_metadata() -> dict:
    return {
        "envelope_version": "1", "skill": "test-condition-design", "runtime_contract_version": "runtime-v1",
        "generator_contract_version": "materialize-coverage-v1", "runtime_unit_key": "artifact:materialize_coverage:TCN-001", "model_key": None,
        "model_type": None, "technique_slug": None, "selection_source": None, "selection_key": None, "scope_key": "TCN-001",
        "input_mode": "artifact", "upstream_entities": [
            {"skill": "test-condition-design", "entity_type": "tcn", "entity_ref": "TCN-001", "content": {"tcn_id": "TCN-001"}},
            {"skill": "test-condition-design", "entity_type": "model", "entity_ref": "ep-001", "content": {"model_key": "ep-001", "model_type": "ep"}},
        ], "upstream_runtime_units": [], "static_data_versions": {}, "authority_refs": [], "reference_refs": [],
    }


def run_script(script: Path, request: dict) -> dict:
    result = subprocess.run([sys.executable, str(script)], input=json.dumps(request).encode(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=REPO_ROOT, check=False)
    if result.stderr:
        raise AssertionError(result.stderr.decode())
    return json.loads(result.stdout)


def ep_result() -> dict:
    return run_script(
        EP_SCRIPT,
        {
            "metadata": ep_metadata(),
            "input": {
                "sets": [{"set_key": "role", "label": "Role", "partitions": [
                    {"partition_key": "admin", "label": "Admin", "validity": "valid", "definition": {"type": "enum", "values": [{"type": "enum", "value": "admin"}]}, "representative": None, "authority_refs": []},
                    {"partition_key": "user", "label": "User", "validity": "valid", "definition": {"type": "enum", "values": [{"type": "enum", "value": "user"}]}, "representative": None, "authority_refs": []},
                ]}],
            },
        },
    )


def materialize_request(ep: dict, *, previous: dict | None = None) -> dict:
    model_result = {
        "skill": "test-condition-design", "model_key": "ep-001", "model_type": "ep", "technique_slug": "ep", "runtime_unit_key": "model:ep-001",
        "input_fingerprint": ep["input_fingerprint"], "model_fingerprint": ep["model_fingerprint"], "generator_contract_version": ep["generator_contract_version"],
        "generation_fingerprint": ep["generation_fingerprint"], "support_status": ep["support_status"], "runtime_status": ep["runtime_status"],
        "result_status": ep["result_status"], "deterministic_generated": ep["deterministic_generated"], "targets": ep["payload"]["targets"],
        "unsupported_items": [], "coverage_summary": ep["payload"]["coverage_summary"], "freshness_status": "current",
    }
    previous = previous or {}
    annotations = [{
        "target_ref": target["target_ref"], "target_content_fingerprint": target["target_content_fingerprint"],
        "generation_fingerprint": ep["generation_fingerprint"], "priority": "中", "priority_override_reason": None,
        "expected_result_root": f"root-{target['target_key'].replace(':', '-')}", "test_data_requirement_refs": [],
    } for target in ep["payload"]["targets"]]
    return {
        "metadata": materialize_metadata(),
        "input": {
            "tcn_id": "TCN-001",
            "active_model_metadata": [{"model_key": "ep-001", "model_type": "ep", "technique_slug": "ep", "parent_tcn_id": "TCN-001", "content_fingerprint": digest({"model_key": "ep-001", "model_type": "ep"})}],
            "models": [model_result], "semantic_coverage_items": [], "test_data_requirements": [],
            "target_annotations": annotations, "target_dispositions": [], "previous_semantic_ci_map": [],
            "previous_target_id_map": previous.get("target_mapping_state", []), "previous_ci_ids": previous.get("ci_id_state", []),
            "previous_expected_result_roots": [], "merge_groups": [],
        },
    }


class MaterializeRuntimeTests(unittest.TestCase):
    def test_targets_materialize_to_stable_ci_and_machine_entity(self) -> None:
        ep = ep_result()
        result = run_script(MATERIALIZE_SCRIPT, materialize_request(ep))
        self.assertEqual(result["runtime_status"], "ok")
        self.assertEqual(result["result_status"], "ready")
        mapping = {row["target_key"]: row["ci_id"] for row in result["payload"]["target_id_map"]}
        self.assertEqual(mapping, {"ep:role:admin": "TCN-001-CI01", "ep:role:user": "TCN-001-CI02"})
        self.assertTrue(result["payload"]["model_completion"][0]["materialize_complete"])
        self.assertEqual(len(result["payload"]["entities"]), 2)
        self.assertEqual(result["payload"]["entities"][0]["content"]["source_kind"], "runtime_target")
        self.assertIsNotNone(result["payload"]["entities"][0]["content"]["execution"])

    def test_previous_full_state_preserves_ci_ids(self) -> None:
        ep = ep_result()
        first = run_script(MATERIALIZE_SCRIPT, materialize_request(ep))
        second = run_script(MATERIALIZE_SCRIPT, materialize_request(ep, previous=first["payload"]))
        self.assertEqual(first["payload"]["target_id_map"], second["payload"]["target_id_map"])
        self.assertEqual(first["payload"]["ci_id_state"], second["payload"]["ci_id_state"])

    def test_previous_mapping_target_ref_is_recomputed(self) -> None:
        ep = ep_result()
        request = materialize_request(ep)
        request["input"]["previous_target_id_map"] = [{
            "target_ref": "sha256:" + "0" * 64, "model_key": "ep-001", "target_key": "ep:role:admin",
            "target_content_fingerprint": ep["payload"]["targets"][0]["target_content_fingerprint"], "ci_id": "TCN-001-CI01", "mapping_status": "active",
        }]
        result = run_script(MATERIALIZE_SCRIPT, request)
        self.assertEqual(result["runtime_status"], "invalid_input")

    def test_semantic_item_materializes_as_separate_ci_and_round_trips(self) -> None:
        ep = ep_result()
        request = materialize_request(ep)
        source = ep["payload"]["targets"][0]
        request["input"]["semantic_coverage_items"] = [{
            "draft_key": "semantic-error-path",
            "model_key": "ep-001",
            "identity_action": "new",
            "reuse_semantic_item_key": None,
            "reuse_ci_id": None,
            "source_target_versions": [{"target_ref": source["target_ref"], "target_content_fingerprint": source["target_content_fingerprint"], "generation_fingerprint": ep["generation_fingerprint"]}],
            "item_text": "仕様根拠で確認が必要な追加観点",
            "authority_refs": [], "reference_refs": [], "priority": "中", "priority_override_reason": None,
            "expected_result_root": "root-semantic-error-path", "test_data_requirement_refs": [],
        }]
        result = run_script(MATERIALIZE_SCRIPT, request)
        self.assertEqual(result["runtime_status"], "ok")
        semantic = [row for row in result["payload"]["entities"] if row["content"]["source_kind"] == "semantic_item"]
        self.assertEqual(len(semantic), 1)
        self.assertEqual(semantic[0]["entity_ref"], "TCN-001-CI03")
        self.assertEqual(result["payload"]["semantic_ci_mapping_state"][0]["semantic_item_key"], "semantic:TCN-001-CI03")


if __name__ == "__main__":
    unittest.main()
