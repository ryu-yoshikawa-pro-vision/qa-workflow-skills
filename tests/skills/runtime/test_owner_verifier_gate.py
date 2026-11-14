from __future__ import annotations

import ast
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "skills" / "qa-workflow" / "scripts"))

import owner_verifiers  # noqa: E402

import tests.skills.runtime.test_owner_verifier_registry as registry_tests  # noqa: E402
from scripts.skills.evals.deterministic.common import CANONICAL_SKILLS  # noqa: E402
from tests.skills.runtime.test_workflow_runtime import (  # noqa: E402
    SCRIPT,
    WorkflowRuntimeTests,
    run,
    runtime,
)

WORKFLOW_REF = "00000000-0000-4000-8000-000000000023"


def _runtime_v2_roots_for_choice() -> set[str]:
    return {
        "test-analysis",
        "test-requirement-design",
        "test-condition-design",
        "test-case-design",
        "coverage-analysis",
        "qa-workflow",
    }


# 登録されていないSkillを動的に選ぶ（後続で登録されても検証の意味を保つ）。
UNREGISTERED_SKILL = sorted(
    set(CANONICAL_SKILLS)
    - _runtime_v2_roots_for_choice()
    - set(owner_verifiers.VERIFIERS)
)[0]


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


def unregistered_scope(skill: str = UNREGISTERED_SKILL) -> dict:
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
            result["payload"]["unverified_scopes"][0]["skill"], UNREGISTERED_SKILL
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
            runtime._default_expected_runtime_units(UNREGISTERED_SKILL, {}, ""), []
        )

    def test_unregistered_scope_cannot_inject_unverified_current_units(self) -> None:
        request = WorkflowRuntimeTests()._request()
        request["input"]["workflow_scopes"].append(unregistered_scope())
        request["input"]["runtime_units"].append(
            request["input"]["runtime_units"][0]
            | {"skill": UNREGISTERED_SKILL, "runtime_unit_key": "artifact:fake:all"}
        )
        result = run(request)
        self.assertFalse(result["payload"]["can_complete"])
        self.assertIn(
            [UNREGISTERED_SKILL, "artifact:fake:all"],
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
        unregistered = sorted(CANONICAL_SKILLS - runtime_v2_skill_roots())
        self.assertIn(UNREGISTERED_SKILL, unregistered)
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

    # --- 工程要求集合（requested_scopes）と owner 検証の組合せ ---------------
    def _owner_request(self, scopes: list[dict], requested: list[dict]) -> dict:
        request = WorkflowRuntimeTests()._request()
        request["input"].update(
            workflow_ref=WORKFLOW_REF,
            workflow_scopes=scopes,
            requested_scopes=requested,
            runtime_units=request["input"]["runtime_units"]
            if any(row["skill"] == "test-condition-design" for row in scopes)
            else [],
            current_runtime_units=request["input"]["current_runtime_units"]
            if any(row["skill"] == "test-condition-design" for row in scopes)
            else [],
            current_entities=request["input"]["current_entities"]
            if any(row["skill"] == "test-condition-design" for row in scopes)
            else [],
        )
        return request

    @staticmethod
    def _required(skill: str, target: str) -> dict:
        return {
            "skill": skill,
            "target": target,
            "execution_range": "plan",
            "requirement": "required",
        }

    def test_qa_plan_only_completes_with_its_declared_owner_scope(self) -> None:
        reg = registry_tests.OwnerVerifierRegistryTests(
            "test_ready_selection_with_matching_readback_completes"
        )
        evidence, ref = reg.selection_evidence()
        request = self._owner_request(
            [registry_tests.scope("e2e-test-selection", ref, evidence)],
            [self._required("e2e-test-selection", ref)],
        )
        result = run(request)
        self.assertEqual(result["runtime_status"], "ok", result)
        self.assertTrue(result["payload"]["can_complete"], result)
        self.assertEqual(result["payload"]["missing_requested_scopes"], [])

    def test_report_only_completes_with_its_declared_owner_scope(self) -> None:
        reg = registry_tests.OwnerVerifierRegistryTests(
            "test_recomputed_complete_current_snapshot_completes"
        )
        evidence, ref = reg.report_evidence()
        request = self._owner_request(
            [registry_tests.scope("test-reporting", ref, evidence)],
            [self._required("test-reporting", ref)],
        )
        result = run(request)
        self.assertTrue(result["payload"]["can_complete"], result)

    def test_partial_start_mixes_existing_owner_artifact_with_runtime_v2_scope(
        self,
    ) -> None:
        reg = registry_tests.OwnerVerifierRegistryTests(
            "test_recomputed_complete_current_snapshot_completes"
        )
        evidence, ref = reg.report_evidence()
        base = WorkflowRuntimeTests()._request()
        scopes = [
            *base["input"]["workflow_scopes"],
            registry_tests.scope("test-reporting", ref, evidence),
        ]
        request = self._owner_request(
            scopes,
            [
                {
                    "skill": "test-condition-design",
                    "target": None,
                    "execution_range": None,
                    "requirement": "required",
                },
                self._required("test-reporting", ref),
            ],
        )
        request["input"]["runtime_units"] = base["input"]["runtime_units"]
        request["input"]["current_runtime_units"] = base["input"][
            "current_runtime_units"
        ]
        request["input"]["current_entities"] = base["input"]["current_entities"]
        result = run(request)
        self.assertEqual(result["runtime_status"], "ok", result)
        self.assertTrue(result["payload"]["can_complete"], result)

    def test_failed_owner_verification_of_a_required_scope_blocks_completion(
        self,
    ) -> None:
        reg = registry_tests.OwnerVerifierRegistryTests(
            "test_recomputed_complete_current_snapshot_completes"
        )
        evidence, ref = reg.report_evidence()
        evidence["current"] = {
            "plan_revision": "p-other",
            "source_revisions": {"e2e": "rev2", "api": "rev1"},
        }
        request = self._owner_request(
            [registry_tests.scope("test-reporting", ref, evidence)],
            [self._required("test-reporting", ref)],
        )
        result = run(request)
        self.assertFalse(result["payload"]["can_complete"], result)
        self.assertEqual(
            [row["reason"] for row in result["payload"]["unverified_scopes"]],
            ["snapshot_not_current"],
        )

    def test_unrelated_verified_scope_survives_another_scope_being_unregistered(
        self,
    ) -> None:
        reg = registry_tests.OwnerVerifierRegistryTests(
            "test_recomputed_complete_current_snapshot_completes"
        )
        evidence, ref = reg.report_evidence()
        request = self._owner_request(
            [
                registry_tests.scope("test-reporting", ref, evidence),
                {
                    "skill": UNREGISTERED_SKILL,
                    "target": "project-1",
                    "execution_range": "plan",
                    "input_mode": "artifact",
                    "normalized_input": {},
                    "current_structure_state": None,
                },
            ],
            [
                self._required("test-reporting", ref),
                self._required(UNREGISTERED_SKILL, "project-1"),
            ],
        )
        result = run(request)
        self.assertFalse(result["payload"]["can_complete"], result)
        self.assertEqual(
            [row["skill"] for row in result["payload"]["verified_owner_scopes"]],
            ["test-reporting"],
        )
        self.assertEqual(
            [row["skill"] for row in result["payload"]["unverified_scopes"]],
            [UNREGISTERED_SKILL],
        )
        self.assertEqual(result["payload"]["missing_requested_scopes"], [])


if __name__ == "__main__":
    unittest.main()
