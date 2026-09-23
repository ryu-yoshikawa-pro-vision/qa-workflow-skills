from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import unittest


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "skills" / "test-case-design" / "scripts" / "case_structure.py"


def metadata() -> dict:
    return {
        "envelope_version": "1", "skill": "test-case-design", "runtime_contract_version": "runtime-v1", "generator_contract_version": "case-structure-v1",
        "runtime_unit_key": "artifact:case_structure:all", "model_key": None, "model_type": None, "technique_slug": None,
        "selection_source": None, "selection_key": None, "scope_key": None, "input_mode": "direct", "upstream_entities": [],
        "upstream_runtime_units": [], "static_data_versions": {}, "authority_refs": [], "reference_refs": [],
    }


def run(value: dict) -> dict:
    result = subprocess.run([sys.executable, str(SCRIPT)], input=json.dumps({"metadata": metadata(), "input": value}, ensure_ascii=False).encode(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=REPO_ROOT, check=False)
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
