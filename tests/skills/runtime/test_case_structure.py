from __future__ import annotations

import json
import importlib.util
from pathlib import Path
import subprocess
import sys
import unittest


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "skills" / "test-case-design" / "scripts" / "case_structure.py"
RUNTIME_PATH = REPO_ROOT / "skills" / "test-case-design" / "scripts" / "runtime_contract.py"
SPEC = importlib.util.spec_from_file_location("case_structure_runtime_contract", RUNTIME_PATH)
assert SPEC is not None and SPEC.loader is not None
runtime = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = runtime
SPEC.loader.exec_module(runtime)


def metadata() -> dict:
    return {
        "envelope_version": "1", "skill": "test-case-design", "runtime_contract_version": "runtime-v1", "generator_contract_version": "case-structure-v1",
        "runtime_unit_key": "artifact:case_structure:all", "model_key": None, "model_type": None, "technique_slug": None,
        "selection_source": None, "selection_key": None, "scope_key": None, "input_mode": "direct", "upstream_entities": [],
        "upstream_runtime_units": [], "static_data_versions": {}, "authority_refs": [], "reference_refs": [],
    }


def run(value: dict, *, meta: dict | None = None) -> dict:
    result = subprocess.run([sys.executable, str(SCRIPT)], input=json.dumps({"metadata": meta or metadata(), "input": value}, ensure_ascii=False).encode(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=REPO_ROOT, check=False)
    if result.stderr:
        raise AssertionError(result.stderr.decode())
    return json.loads(result.stdout)


def valid_input() -> dict:
    return {
        "test_conditions": [{"tcn_id": "TCN-001", "tr_refs": ["TR-001"], "priority": "中"}],
        "coverage_items": [{
            "ci_id": "TCN-001-CI01", "tcn_id": "TCN-001", "model_key": "ep-001", "priority": "中", "authority_refs": ["SPEC-001"],
            "source_kind": "runtime_target", "execution": {"input": {"role": "admin"}}, "semantic_item_key": None,
            "semantic_item_text": None, "semantic_source_targets": [], "test_data_requirement_refs": ["data:role"],
        }],
        "environment_requirements": [{"requirement_key": "ENV-001", "environment_key": "web", "dimension_key": "browser", "operator": "eq", "value": {"type": "string", "value": "chromium"}}],
        "test_data_requirements": [{"data_ref": "data:role", "requirement_key": "role", "environment_key": None, "dimension_key": "role", "operator": "eq", "value": {"type": "string", "value": "admin"}, "source_model_key": "ep-001", "source_target_versions": []}],
        "test_cases": [{
            "draft_key": "tc-admin", "identity_action": "new", "reuse_id": None, "title_or_purpose": "管理者ロールを確認する",
            "tr_refs": ["TR-001"], "tcn_refs": ["TCN-001"], "ci_refs": ["TCN-001-CI01"], "environment_requirement_refs": ["ENV-001"],
            "test_data_requirement_refs": ["data:role"], "priority": "中", "priority_override_reason": None,
            "preconditions": ["対象環境を準備する"], "test_data": ["role=admin"], "steps": [{"number": 1, "text": "管理者として操作する"}],
            "expected_results": [{"number": 1, "text": "管理者向け結果が表示される", "authority_refs": ["SPEC-001"]}], "postconditions_or_cleanup": ["作成データを削除する"],
        }],
        "dispositions": [], "previous_tc_ids": [], "update_scope_tc_ids": [],
    }


class CaseStructureRuntimeTests(unittest.TestCase):
    def test_ci_machine_content_is_materialized_to_stable_tc(self) -> None:
        result = run(valid_input())
        self.assertEqual(result["runtime_status"], "ok")
        self.assertEqual(result["result_status"], "ready")
        self.assertEqual(result["payload"]["tc_id_map"], [{"draft_key": "tc-admin", "tc_id": "TC-001", "identity_action": "new"}])
        entity = result["payload"]["entities"][0]
        self.assertEqual(entity["entity_type"], "tc")
        self.assertEqual(entity["content"]["ci_refs"], ["TCN-001-CI01"])

    def test_tc_dependency_freshness_tracks_each_explicit_machine_entity_ref(self) -> None:
        value = valid_input()
        source_entities = [
            runtime.make_machine_entity("test-requirement-design", "tr", "TR-001", {"text": "checkout completes"}),
            runtime.make_machine_entity("test-condition-design", "tcn", "TCN-001", {"tcn_id": "TCN-001", "tr_refs": ["TR-001"], "priority": 2}),
            runtime.make_machine_entity("test-analysis", "environment_requirement", "ENV-001", value["environment_requirements"][0] | {"source_model_key": None, "source_target_versions": []}),
            runtime.make_machine_entity("test-condition-design", "test_data_requirement", "data:role", value["test_data_requirements"][0]),
            runtime.make_machine_entity("test-condition-design", "ci", "TCN-001-CI01", value["coverage_items"][0] | {"ci_id": "TCN-001-CI01"}, model_key="ep-001"),
            runtime.make_machine_entity("spec-analysis", "authority", "SPEC-001", {"title": "Checkout contract"}),
        ]
        ci_01 = next(row for row in source_entities if row["entity_type"] == "ci")
        ci_02 = runtime.make_machine_entity(
            "test-condition-design", "ci", "TCN-001-CI02",
            {**ci_01["content"], "ci_id": "TCN-001-CI02", "execution": {"input": {"role": "user"}}},
            model_key="ep-001",
        )
        source_entities.append(ci_02)
        value["coverage_items"] = [next(row for row in source_entities if row["entity_type"] == "ci")]
        value["coverage_items"].append(ci_02)
        value["environment_requirements"] = [next(row for row in source_entities if row["entity_type"] == "environment_requirement")]
        value["test_data_requirements"] = [next(row for row in source_entities if row["entity_type"] == "test_data_requirement")]
        current_meta = metadata()
        current_meta["input_mode"] = "artifact"
        current_meta["upstream_entities"] = [
            {"skill": row["skill"], "entity_type": row["entity_type"], "entity_ref": row["entity_ref"], "content": row["content"]}
            for row in source_entities
        ]
        value["dispositions"] = [{
            "upstream_entity": {key: ci_02[key] for key in ("skill", "entity_type", "entity_ref", "content_fingerprint")},
            "handling": "重複", "reason": "covered by the first CI", "authority_refs": ["SPEC-001"],
            "covered_by_entity": {key: ci_01[key] for key in ("skill", "entity_type", "entity_ref", "content_fingerprint")},
        }]
        result = run(value, meta=current_meta)
        self.assertEqual(result["result_status"], "ready", result)
        tc = next(row for row in result["payload"]["entities"] if row["entity_type"] == "tc")
        expected = {
            ("test-requirement-design", "tr", "TR-001"),
            ("test-condition-design", "tcn", "TCN-001"),
            ("test-condition-design", "ci", "TCN-001-CI01"),
            ("test-analysis", "environment_requirement", "ENV-001"),
            ("test-condition-design", "test_data_requirement", "data:role"),
            ("spec-analysis", "authority", "SPEC-001"),
        }
        actual = {(row["skill"], row["entity_type"], row["entity_ref"]) for row in tc["upstream_entity_dependencies"]}
        self.assertEqual(actual, expected)
        disposition = next(row for row in result["payload"]["entities"] if row["entity_type"] == "disposition")
        self.assertEqual(
            {(row["skill"], row["entity_type"], row["entity_ref"]) for row in disposition["upstream_entity_dependencies"]},
            {("test-condition-design", "ci", "TCN-001-CI01"), ("test-condition-design", "ci", "TCN-001-CI02"), ("spec-analysis", "authority", "SPEC-001")},
        )
        runtime_units = {("test-case-design", "artifact:case_structure:all"): {"generation_fingerprint": result["generation_fingerprint"]}}
        unrelated_authority = runtime.make_machine_entity("spec-analysis", "authority", "SPEC-OTHER", {"title": "unrelated"})
        unrelated_tc = runtime.make_machine_entity(
            "test-case-design", "tc", "TC-002", {"tc_id": "TC-002"},
            upstream_entity_dependencies=[runtime.machine_entity_dependency(unrelated_authority)],
            runtime_dependencies=[{"skill": "test-case-design", "runtime_unit_key": "artifact:case_structure:all", "generation_fingerprint": result["generation_fingerprint"]}],
        )
        fresh = runtime.evaluate_entity_freshness(source_entities + [unrelated_authority, tc, unrelated_tc], runtime_units)
        status_by_ref = {row["entity_ref"]: row["freshness_status"] for row in fresh if row["entity_type"] == "tc"}
        self.assertEqual(status_by_ref, {"TC-001": "current", "TC-002": "current"})

        for identity in sorted(expected):
            with self.subTest(changed_identity=identity):
                changed = []
                for row in source_entities:
                    row_identity = (row["skill"], row["entity_type"], row["entity_ref"])
                    if row_identity == identity:
                        row = runtime.make_machine_entity(row["skill"], row["entity_type"], row["entity_ref"], {**row["content"], "changed": True}, model_key=row["model_key"])
                    changed.append(row)
                status = {row["entity_ref"]: row["freshness_status"] for row in runtime.evaluate_entity_freshness(changed + [unrelated_authority, tc, unrelated_tc], runtime_units) if row["entity_type"] == "tc"}
                self.assertEqual(status, {"TC-001": "stale", "TC-002": "current"})

        status = {row["entity_ref"]: row["freshness_status"] for row in runtime.evaluate_entity_freshness(source_entities + [unrelated_authority, tc, unrelated_tc], runtime_units) if row["entity_type"] == "tc"}
        self.assertEqual(status, {"TC-001": "current", "TC-002": "current"})

    def test_artifact_mode_does_not_treat_tcn_summary_as_current_entity(self) -> None:
        value = valid_input()
        current_meta = metadata()
        current_meta["input_mode"] = "artifact"
        # CI and requirements are present, but the current TCN Machine Entity is not.
        current_meta["upstream_entities"] = []
        result = run(value, meta=current_meta)
        self.assertEqual(result["runtime_status"], "invalid_input")

    def test_scope_reuse_and_deleted_state_are_deterministic(self) -> None:
        value = valid_input()
        value["previous_tc_ids"] = [{"tc_id": "TC-001", "status": "active"}, {"tc_id": "TC-002", "status": "deleted"}]
        value["update_scope_tc_ids"] = ["TC-001"]
        value["test_cases"][0]["identity_action"] = "reuse"
        value["test_cases"][0]["reuse_id"] = "TC-001"
        result = run(value)
        self.assertEqual(result["runtime_status"], "ok")
        self.assertEqual(result["payload"]["tc_id_state"], [{"tc_id": "TC-001", "status": "active"}, {"tc_id": "TC-002", "status": "deleted"}])

    def test_conflicting_test_data_is_unresolved(self) -> None:
        value = valid_input()
        value["test_data_requirements"].append({"data_ref": "data:role-other", "requirement_key": "role-other", "environment_key": None, "dimension_key": "role", "operator": "eq", "value": {"type": "string", "value": "user"}, "source_model_key": "ep-001", "source_target_versions": []})
        value["coverage_items"].append({
            "ci_id": "TCN-001-CI02", "tcn_id": "TCN-001", "model_key": "ep-001", "priority": "中", "authority_refs": [],
            "source_kind": "runtime_target", "execution": {"input": {"role": "user"}}, "semantic_item_key": None,
            "semantic_item_text": None, "semantic_source_targets": [], "test_data_requirement_refs": ["data:role-other"],
        })
        value["test_cases"][0]["ci_refs"].append("TCN-001-CI02")
        result = run(value)
        self.assertEqual(result["runtime_status"], "ok")
        self.assertEqual(result["result_status"], "unresolved")
        self.assertTrue(any(issue["violation_type"] == "test_data_conflict" for issue in result["issues"]))

    def test_tc_rechecks_environment_intersection_by_key(self) -> None:
        value = valid_input()
        value["environment_requirements"] = [
            {"requirement_key": "ENV-001", "environment_key": "web", "dimension_key": "browser", "operator": "range", "minimum": {"type": "integer", "value": 1}, "maximum": {"type": "integer", "value": 3}, "minimum_inclusive": True, "maximum_inclusive": True},
            {"requirement_key": "ENV-002", "environment_key": "web", "dimension_key": "browser", "operator": "range", "minimum": {"type": "integer", "value": 3}, "maximum": {"type": "integer", "value": 5}, "minimum_inclusive": False, "maximum_inclusive": True},
            {"requirement_key": "ENV-003", "environment_key": "mobile", "dimension_key": "browser", "operator": "eq", "value": {"type": "string", "value": "webkit"}},
        ]
        value["test_cases"][0]["environment_requirement_refs"] = ["ENV-001", "ENV-002", "ENV-003"]
        result = run(value)
        self.assertEqual(result["result_status"], "unresolved")
        self.assertTrue(any(issue["violation_type"] == "environment_requirement_conflict" and issue["environment_key"] == "web" for issue in result["issues"]))


if __name__ == "__main__":
    unittest.main()
