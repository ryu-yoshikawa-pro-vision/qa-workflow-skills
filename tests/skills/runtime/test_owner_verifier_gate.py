from __future__ import annotations

import unittest

from tests.skills.runtime.test_workflow_runtime import (
    WorkflowRuntimeTests,
    run,
    runtime,
)

WORKFLOW_REF = "00000000-0000-4000-8000-000000000023"


def unregistered_scope(skill: str = "test-management") -> dict:
    return {
        "skill": skill,
        "target": "project-1",
        "execution_range": "plan",
        "input_mode": "artifact",
        "normalized_input": {},
        "current_structure_state": None,
    }


class OwnerVerifierGateTests(unittest.TestCase):
    def test_unregistered_scope_with_no_units_or_entities_cannot_complete(self) -> None:
        request = WorkflowRuntimeTests()._request()
        request["input"].update(
            workflow_ref=WORKFLOW_REF,
            workflow_scopes=[unregistered_scope()],
            runtime_units=[],
            current_runtime_units=[],
            current_entities=[],
        )
        result = run(request)
        self.assertEqual(result["runtime_status"], "ok", result)
        self.assertFalse(result["payload"]["can_complete"])
        self.assertEqual(result["payload"]["expected_runtime_units"], [])
        self.assertEqual(result["payload"]["unverified_scopes"][0]["skill"], "test-management")
        self.assertIn(
            "unsupported_skill_verifier",
            {issue["issue_type"] for issue in result["issues"]},
        )

    def test_supported_scope_stays_current_when_another_scope_is_unregistered(self) -> None:
        request = WorkflowRuntimeTests()._request()
        baseline = run(request)
        self.assertTrue(baseline["payload"]["can_complete"], baseline)
        request["input"]["workflow_scopes"].append(unregistered_scope())
        result = run(request)
        self.assertEqual(result["runtime_status"], "ok", result)
        self.assertFalse(result["payload"]["can_complete"])
        self.assertEqual(
            baseline["payload"]["runtime_units"],
            result["payload"]["runtime_units"],
        )
        self.assertEqual(
            baseline["payload"]["entity_freshness"],
            result["payload"]["entity_freshness"],
        )
        self.assertEqual(result["payload"]["missing_runtime_units"], [])
        self.assertEqual(result["payload"]["missing_entities"], [])

    def test_unregistered_skill_cannot_use_runtime_v2_zero_evidence(self) -> None:
        with self.assertRaises(runtime.InvalidInput):
            runtime._default_expected_runtime_units("test-management", {}, "")
        with self.assertRaises(runtime.InvalidInput):
            runtime.verify_runtime_evidence(
                {
                    "operation": "verify_runtime_evidence",
                    "skill": "test-management",
                    "normalized_skill_input": {},
                    "artifact_markdown": "",
                    "previous_artifact_markdown": None,
                    "partial_rerun": False,
                }
            )

    def test_unregistered_scope_cannot_inject_unverified_current_units(self) -> None:
        request = WorkflowRuntimeTests()._request()
        request["input"]["workflow_scopes"].append(unregistered_scope())
        request["input"]["runtime_units"].append(
            request["input"]["runtime_units"][0]
            | {"skill": "test-management", "runtime_unit_key": "artifact:fake:all"}
        )
        result = run(request)
        self.assertFalse(result["payload"]["can_complete"])
        self.assertIn(
            ["test-management", "artifact:fake:all"],
            result["payload"]["extra_runtime_units"],
        )


if __name__ == "__main__":
    unittest.main()
