from __future__ import annotations

import ast
import unittest

from tests.skills.runtime.test_workflow_runtime import (
    SCRIPT,
    WorkflowRuntimeTests,
    run,
    runtime,
)

WORKFLOW_REF = "00000000-0000-4000-8000-000000000023"


def runtime_v2_skill_roots() -> set[str]:
    tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
    for node in tree.body:
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id == "RUNTIME_V2_SKILL_ROOTS"
        ):
            call = node.value
            assert isinstance(call, ast.Call) and len(call.args) == 1
            return set(ast.literal_eval(call.args[0]))
    raise AssertionError("RUNTIME_V2_SKILL_ROOTS is not declared")


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
        self.assertEqual(
            result["payload"]["unverified_scopes"][0]["skill"], "test-management"
        )
        self.assertIn(
            "unsupported_skill_verifier",
            {issue["issue_type"] for issue in result["issues"]},
        )

    def test_supported_scope_stays_current_when_another_scope_is_unregistered(
        self,
    ) -> None:
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

    def test_unregistered_model_metadata_cannot_abort_supported_scope(self) -> None:
        request = WorkflowRuntimeTests()._request()
        baseline = run(request)
        self.assertEqual(baseline["runtime_status"], "ok")
        unsupported = unregistered_scope()
        unsupported["normalized_input"] = {
            "models": [
                {"model_key": "ep-001", "model_type": "ep", "untrusted": "metadata"}
            ]
        }
        request["input"]["workflow_scopes"].append(unsupported)
        result = run(request)
        self.assertEqual(result["runtime_status"], "ok", result)
        self.assertFalse(result["payload"]["can_complete"])
        self.assertEqual(
            result["payload"]["runtime_units"], baseline["payload"]["runtime_units"]
        )
        self.assertEqual(
            result["payload"]["entity_freshness"],
            baseline["payload"]["entity_freshness"],
        )
        self.assertEqual(len(result["payload"]["unverified_scopes"]), 1)
        self.assertEqual(
            {issue["issue_type"] for issue in result["issues"]},
            {"unsupported_skill_verifier"},
        )

    def test_unregistered_model_does_not_enter_materialize_completion(self) -> None:
        request = WorkflowRuntimeTests()._request()
        unsupported = unregistered_scope()
        unsupported["normalized_input"] = {
            "models": [{"model_key": "unknown-only", "model_type": "ep"}]
        }
        request["input"]["workflow_scopes"].append(unsupported)
        result = run(request)
        self.assertEqual(result["runtime_status"], "ok", result)
        self.assertEqual(
            {issue["issue_type"] for issue in result["issues"]},
            {"unsupported_skill_verifier"},
        )

    def test_unregistered_skill_has_no_runtime_v2_root(self) -> None:
        self.assertEqual(
            runtime._default_expected_runtime_units("test-management", {}, ""), []
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

    def test_runtime_v2_roots_are_not_extended_by_routing_registration(self) -> None:
        # routingやCANONICAL_SKILLSへの名前追加は完了検証の登録ではない。
        self.assertEqual(
            runtime_v2_skill_roots(),
            {
                "test-analysis",
                "test-requirement-design",
                "test-condition-design",
                "test-case-design",
                "coverage-analysis",
                "qa-workflow",
            },
        )

    def test_every_routed_skill_without_owner_verifier_blocks_completion(
        self,
    ) -> None:
        from scripts.skills.evals.deterministic.common import CANONICAL_SKILLS

        unregistered = sorted(CANONICAL_SKILLS - runtime_v2_skill_roots())
        self.assertIn("test-management", unregistered)
        self.assertIn("defect-management", unregistered)
        for skill in unregistered:
            with self.subTest(skill=skill):
                request = WorkflowRuntimeTests()._request()
                request["input"].update(
                    workflow_ref=WORKFLOW_REF,
                    workflow_scopes=[unregistered_scope(skill)],
                    runtime_units=[],
                    current_runtime_units=[],
                    current_entities=[],
                )
                result = run(request)
                self.assertEqual(result["runtime_status"], "ok", result)
                self.assertFalse(result["payload"]["can_complete"])
                self.assertEqual(result["result_status"], "unresolved")
                self.assertEqual(
                    [row["skill"] for row in result["payload"]["unverified_scopes"]],
                    [skill],
                )


if __name__ == "__main__":
    unittest.main()
