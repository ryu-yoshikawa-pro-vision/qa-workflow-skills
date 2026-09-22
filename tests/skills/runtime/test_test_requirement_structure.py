from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import unittest


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "skills" / "test-requirement-design" / "scripts" / "requirement_structure.py"
DIGEST = "sha256:" + "a" * 64


def metadata(input_mode: str = "direct") -> dict:
    return {
        "envelope_version": "1", "skill": "test-requirement-design", "runtime_contract_version": "runtime-v1", "generator_contract_version": "requirement-structure-v1",
        "runtime_unit_key": "artifact:requirement_structure:all", "model_key": None, "model_type": None, "technique_slug": None, "selection_source": None, "selection_key": None,
        "scope_key": "all", "input_mode": input_mode, "upstream_entities": [], "upstream_runtime_units": [], "static_data_versions": {}, "authority_refs": [], "reference_refs": [],
    }


def run(value: dict, input_mode: str = "direct") -> dict:
    result = subprocess.run([sys.executable, str(SCRIPT)], input=json.dumps({"metadata": metadata(input_mode), "input": value}, ensure_ascii=False).encode(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=REPO_ROOT, check=False)
    if result.stderr:
        raise AssertionError(result.stderr.decode())
    return json.loads(result.stdout)


def draft(key: str, action: str, reuse_id: str | None, *, priority: str = "高", override: str | None = None, authority_refs: list[str] | None = None, risk_refs: list[str] | None = None) -> dict:
    return {
        "draft_key": key, "identity_action": action, "reuse_id": reuse_id, "text": f"Requirement {key}",
        "authority_refs": authority_refs or [], "risk_refs": risk_refs or [], "priority": priority, "priority_override_reason": override,
        "test_level": "system", "observation_method": "assertion",
    }


def base_input() -> dict:
    return {
        "authorities": [{"authority_id": "AUTH-001"}],
        "risks": [{"risk_id": "R-001", "mapped_priority": "高"}],
        "test_requirements": [draft("keep", "reuse", "TR-001", priority="中", override="legacy scope"), draft("new", "new", None)],
        "dispositions": [],
        "previous_tr_ids": [{"tr_id": "TR-001", "status": "active"}, {"tr_id": "TR-002", "status": "deleted"}],
        "update_scope_tr_ids": ["TR-001"],
    }


class RequirementStructureRuntimeTests(unittest.TestCase):
    def test_reuse_new_and_scope_lifecycle_preserve_full_snapshot(self) -> None:
        value = base_input()
        value["test_requirements"][0]["authority_refs"] = ["AUTH-001"]
        value["test_requirements"][0]["risk_refs"] = ["R-001"]
        value["test_requirements"][1]["authority_refs"] = ["AUTH-001"]
        value["test_requirements"][1]["risk_refs"] = ["R-001"]
        result = run(value)
        self.assertEqual(result["runtime_status"], "ok")
        self.assertEqual(result["result_status"], "ready")
        self.assertEqual(result["payload"]["tr_id_map"], [
            {"draft_key": "keep", "tr_id": "TR-001", "identity_action": "reuse"},
            {"draft_key": "new", "tr_id": "TR-003", "identity_action": "new"},
        ])
        self.assertEqual(result["payload"]["tr_id_state"], [
            {"tr_id": "TR-001", "status": "active"}, {"tr_id": "TR-002", "status": "deleted"}, {"tr_id": "TR-003", "status": "active"},
        ])
        tr = next(row for row in result["payload"]["entities"] if row["entity_type"] == "tr" and row["entity_ref"] == "TR-001")
        self.assertEqual(tr["content"]["text"], "Requirement keep")
        self.assertEqual(tr["content"]["priority"], "中")

    def test_linked_and_disposed_is_unresolved_and_reason_is_preserved(self) -> None:
        value = base_input()
        for row in value["test_requirements"]:
            row["authority_refs"] = ["AUTH-001"]
            row["risk_refs"] = ["R-001"]
        value["dispositions"] = [{
            "upstream_entity": {"skill": "spec-analysis", "entity_type": "authority", "entity_ref": "AUTH-001", "content_fingerprint": DIGEST},
            "handling": "対象外", "reason": "not in scope", "authority_refs": [], "covered_by_entity": None,
        }]
        result = run(value)
        self.assertEqual(result["runtime_status"], "ok")
        self.assertEqual(result["result_status"], "unresolved")
        self.assertTrue(any(issue["issue_type"] == "linked_and_disposed" for issue in result["issues"]))

    def test_legacy_seed_uses_active_previous_state_and_forbids_partial_scope(self) -> None:
        value = {
            "authorities": [], "risks": [], "test_requirements": [draft("legacy", "reuse", "TR-004")], "dispositions": [],
            "previous_tr_ids": [], "update_scope_tr_ids": [], "legacy_tr_ids": ["TR-004"],
        }
        result = run(value)
        self.assertEqual(result["runtime_status"], "ok")
        self.assertEqual(result["payload"]["tr_id_map"][0]["tr_id"], "TR-004")
        bad = dict(value, update_scope_tr_ids=["TR-004"])
        self.assertEqual(run(bad)["runtime_status"], "invalid_input")

    def test_low_priority_without_override_reason_is_reported(self) -> None:
        value = base_input()
        value["test_requirements"][0]["priority_override_reason"] = ""
        value["test_requirements"][0]["risk_refs"] = ["R-001"]
        value["test_requirements"][1]["risk_refs"] = ["R-001"]
        result = run(value)
        self.assertEqual(result["runtime_status"], "invalid_input")


if __name__ == "__main__":
    unittest.main()
