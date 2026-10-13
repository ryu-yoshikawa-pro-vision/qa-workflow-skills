from __future__ import annotations

import sys
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[3] / "skills" / "qa-workflow" / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))
from migration_preflight import evaluate  # noqa: E402
from runtime_contract import InvalidInput  # noqa: E402


def inventory(*statuses: str) -> list[dict]:
    skills = (
        "test-requirement-design",
        "test-condition-design",
        "test-case-design",
    )
    rows = []
    for skill, status in zip(skills, statuses):
        is_v1 = status == "legacy_valid"
        rows.append(
            {
                "skill": skill,
                "artifact_present": True,
                "runtime_contract_version": "runtime-v1" if is_v1 else "runtime-v2",
                "entity_schema_version": "entity-state-v1"
                if is_v1
                else "entity-state-v2",
                "verification_status": status,
            }
        )
    return rows


def request() -> dict:
    return {
        "runtime_inventory": inventory(
            "current_valid", "cutover_in_progress", "legacy_valid"
        ),
        "v2_baseline": {
            "qa_workflow_verification_valid": False,
            "qa_workflow_can_complete": False,
        },
        "ui_target_package": {
            "present": False,
            "current_scope_ids": [],
            "ready_scope_ids": [],
            "blocked_scope_ids": [],
        },
        "active_downstream": [],
    }


class MigrationPreflightTests(unittest.TestCase):
    def test_resumes_at_tcd_cutover_in_fixed_order(self) -> None:
        result = evaluate(request())
        self.assertTrue(result["valid"])
        self.assertEqual(result["migration_status"], "runtime_v2_cutover_required")
        self.assertEqual(
            result["cutover_next_action"],
            {"skill": "test-condition-design", "phase": "resume"},
        )

    def test_rejects_out_of_order_v2_artifact(self) -> None:
        value = request()
        value["runtime_inventory"] = inventory(
            "legacy_valid", "current_valid", "legacy_valid"
        )
        with self.assertRaises(InvalidInput):
            evaluate(value)

    def test_rejects_v2_baseline_when_runtime_cutover_is_unfinished(self) -> None:
        value = request()
        value["v2_baseline"] = {
            "qa_workflow_verification_valid": True,
            "qa_workflow_can_complete": True,
        }
        with self.assertRaises(InvalidInput):
            evaluate(value)

    def test_rejects_tcd_partial_after_legacy_trd(self) -> None:
        value = request()
        value["runtime_inventory"] = inventory(
            "legacy_valid", "cutover_in_progress", "legacy_valid"
        )
        with self.assertRaises(InvalidInput):
            evaluate(value)

    def test_rejects_noncanonical_active_entity_ref(self) -> None:
        value = request()
        value["active_downstream"] = [
            {
                "skill": "test-requirement-design",
                "entity_type": "tr",
                "entity_ref": "TCN-001",
                "scope_refs": [],
            }
        ]
        with self.assertRaises(InvalidInput):
            evaluate(value)

    def test_requires_ui_target_migration_after_v2_baseline(self) -> None:
        value = request()
        value["runtime_inventory"] = inventory(
            "current_valid", "current_valid", "current_valid"
        )
        value["v2_baseline"] = {
            "qa_workflow_verification_valid": True,
            "qa_workflow_can_complete": True,
        }
        self.assertEqual(
            evaluate(value)["migration_status"], "ui_target_migration_required"
        )

    def test_unscoped_downstream_requires_all_scopes_ready(self) -> None:
        value = request()
        value["runtime_inventory"] = []
        value["v2_baseline"] = {
            "qa_workflow_verification_valid": True,
            "qa_workflow_can_complete": True,
        }
        value["ui_target_package"] = {
            "present": True,
            "current_scope_ids": ["SCOPE-001", "SCOPE-002"],
            "ready_scope_ids": ["SCOPE-001"],
            "blocked_scope_ids": ["SCOPE-002"],
        }
        value["active_downstream"] = [
            {
                "skill": "test-requirement-design",
                "entity_type": "tr",
                "entity_ref": "TR-001",
                "scope_refs": [],
            }
        ]
        result = evaluate(value)
        self.assertEqual(
            result["migration_status"], "scope_ownership_baseline_required"
        )
        self.assertEqual(result["blocking_issue"], "scope_ownership_baseline_required")

    def test_all_ready_scopes_allow_ownership_normalization(self) -> None:
        value = request()
        value["runtime_inventory"] = []
        value["v2_baseline"] = {
            "qa_workflow_verification_valid": True,
            "qa_workflow_can_complete": True,
        }
        value["ui_target_package"] = {
            "present": True,
            "current_scope_ids": ["SCOPE-001"],
            "ready_scope_ids": ["SCOPE-001"],
            "blocked_scope_ids": [],
        }
        value["active_downstream"] = [
            {
                "skill": "test-requirement-design",
                "entity_type": "tr",
                "entity_ref": "TR-001",
                "scope_refs": [],
            }
        ]
        self.assertEqual(
            evaluate(value)["migration_status"],
            "scope_ownership_normalization_required",
        )

    def test_current_scoped_baseline_allows_partial_progression(self) -> None:
        value = request()
        value["runtime_inventory"] = []
        value["v2_baseline"] = {
            "qa_workflow_verification_valid": True,
            "qa_workflow_can_complete": True,
        }
        value["ui_target_package"] = {
            "present": True,
            "current_scope_ids": ["SCOPE-001", "SCOPE-002"],
            "ready_scope_ids": ["SCOPE-001"],
            "blocked_scope_ids": ["SCOPE-002"],
        }
        value["active_downstream"] = [
            {
                "skill": "test-requirement-design",
                "entity_type": "tr",
                "entity_ref": "TR-001",
                "scope_refs": ["SCOPE-001"],
            }
        ]
        self.assertEqual(
            evaluate(value)["migration_status"], "partial_progression_ready"
        )


if __name__ == "__main__":
    unittest.main()
