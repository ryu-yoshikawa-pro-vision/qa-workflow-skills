from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT = REPO_ROOT / "skills" / "usability-evaluation" / "scripts" / "evaluation_structure.py"
VALIDATOR_SCRIPT = REPO_ROOT / "skills" / "usability-evaluation" / "evals" / "deterministic" / "validator.py"
spec = importlib.util.spec_from_file_location("usability_evaluation_structure", SCRIPT)
structure = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(structure)
validator_spec = importlib.util.spec_from_file_location("usability_evaluation_validator", VALIDATOR_SCRIPT)
output_validator = importlib.util.module_from_spec(validator_spec)
assert validator_spec and validator_spec.loader
validator_spec.loader.exec_module(output_validator)


ASPECTS = [
    {"aspect_key": "purpose-understanding", "handling": "対象外", "reason": "このfixtureでは評価しない"},
    {"aspect_key": "interaction", "handling": "今回評価する", "reason": None},
    {"aspect_key": "feedback", "handling": "対象外", "reason": "このfixtureでは評価しない"},
    {"aspect_key": "error-prevention-recovery", "handling": "対象外", "reason": "このfixtureでは評価しない"},
    {"aspect_key": "accessibility", "handling": "対象外", "reason": "このfixtureでは評価しない"},
    {"aspect_key": "visual-integrity", "handling": "対象外", "reason": "このfixtureでは評価しない"},
    {"aspect_key": "cross-pattern-flow", "handling": "対象外", "reason": "このfixtureでは評価しない"},
]


def valid_input() -> dict:
    known_refs = {
        "evidence_refs": ["EV-001", "EV-002"],
        "project_authority_refs": [],
        "test_rule_result_refs": ["RULE-001"],
        "requirement_check_refs": ["REQCHK-001"],
        "measurement_refs": [],
        "inspection_request_refs": [],
        "owner_activity_refs": ["ACTIVITY-001"],
        "finding_refs": ["FND-001"],
        "scope_refs": ["SCOPE-001"],
        "target_refs": ["TARGET-001", "ELEMENT-001"],
        "state_basis_refs": ["STATE-001"],
    }
    return {
        "condition": {
            "target": {"ref": "TARGET-001", "name": "Dialog", "region": "Account settings"},
            "platform": "Web",
            "viewport_device": "desktop viewport",
            "locale": "en",
            "current_state": "modal open",
            "evidence_refs": ["EV-001", "EV-002"],
            "project_authority_refs": [],
            "adopted_design_system_refs": [],
            "limitations": [],
            "user": None,
            "user_goal_task_flow": None,
            "success_condition": None,
            "business_outcome": None,
            "business_rule": None,
        },
        "aspects": [dict(row) for row in ASPECTS],
        "reference_catalog": {"REF-0001": ["SRC-012-ITEM-0001"]},
        "pattern_identifications": [{
            "draft_key": "modal-pattern",
            "target_ref": "TARGET-001",
            "pattern_name": "Modal dialog",
            "purpose": "Temporarily focus a task above the primary view.",
            "user_goal_relationship": None,
            "applicability": "The content interrupts the current workflow and prevents interaction with the underlying page.",
            "source_refs": [{"reference_entry_ref": "REF-0001", "source_item_ref": "SRC-012-ITEM-0001"}],
            "not_identified_reason": None,
        }],
        "known_refs": known_refs,
        "findings": [{"draft_key": "finding-focus", "finding_ref": "FND-001"}],
        "existing_additional_observation_links": [],
        "evaluations": [{
            "draft_key": "dialog-focus",
            "aspect_key": "interaction",
            "target": "Modal dialog title and opening focus",
            "user_goal_task_flow_override": None,
            "basis": ["reference"],
            "observed_fact": "Opening the modal leaves focus on the background trigger.",
            "pattern_or_principle": "Modal dialog",
            "pattern_draft_key": "modal-pattern",
            "project_authority_refs": [],
            "applied_references": [{
                "reference_entry_ref": "REF-0001",
                "source_item_ref": "SRC-012-ITEM-0001",
                "reference_position": "informative pattern guidance",
                "authority_binding_applied": False,
                "project_authority_refs": [],
            }],
            "reference_not_used_reason": None,
            "expected_characteristic": "Focus moves into the modal dialog when it opens.",
            "difference": "The background trigger retains focus.",
            "expected_impact": "Keyboard users may not discover the dialog content or current interaction context.",
            "impact_basis": "Focus and dialog evidence, interpreted against the APG pattern guidance.",
            "judgment_reason": "The observation conflicts with the modal dialog interaction guidance.",
            "additional_observation_links": [{
                "request_draft_key": "observe-dialog-title",
                "requester_kind": "usability-evaluation",
                "requester_identity": {"evaluation_draft_key": "dialog-focus"},
                "execution_owner": "test-target-inspection",
                "scope_ref": "SCOPE-001",
                "target_ref": "ELEMENT-001",
                "target_draft_key": None,
                "state_description": "dialog open after invocation",
                "state_basis_refs": ["STATE-001"],
                "current_document_identity": "hmac-sha256:" + "a" * 64,
                "observation_field_key": "element.rendered-text",
                "predicate_key": None,
                "predicate_payload": None,
                "needed_observation": "Capture the rendered dialog heading text in the opened state.",
                "reason": "The label associated with the dialog needs direct confirmation.",
                "input_evidence_refs": ["EV-001"],
                "status": "completed",
                "inspection_request_ref": None,
                "owner_activity_ref": "ACTIVITY-001",
                "returned_evidence_refs": ["EV-002"],
                "limitation": None,
            }],
            "observed_user_impact": None,
            "evidence_refs": ["EV-001", "EV-002"],
            "test_rule_result_refs": ["RULE-001"],
            "requirement_check_refs": ["REQCHK-001"],
            "measurement_refs": [],
            "status": "問題を確認",
            "status_reason": None,
            "routing": "usability-inspection",
            "finding_draft_key": "finding-focus",
            "note": None,
            "follow_up_required": True,
        }],
    }


class EvaluationStructureTests(unittest.TestCase):
    def test_materializes_fixed_aspects_refs_findings_and_summary(self) -> None:
        result = structure.materialize(valid_input())
        self.assertEqual(len(result["aspects"]), 7)
        self.assertEqual(result["evaluations"][0]["evaluation_ref"], "EVAL-001")
        self.assertTrue(result["evaluations"][0]["finding_required"])
        self.assertEqual(result["evaluations"][0]["finding_ref"], "FND-001")
        self.assertEqual(result["summary"]["finding_count"], 1)
        self.assertIn("## Evaluation Scope Closure", result["machine_owned_markdown"])
        self.assertIn("| EVAL-001 | interaction | dialog-focus | 問題を確認 | FND-001 |", result["machine_owned_markdown"])
        self.assertEqual(result["evaluations"][0]["test_rule_result_refs"], ["RULE-001"])
        self.assertEqual(result["evaluations"][0]["requirement_check_refs"], ["REQCHK-001"])

    def test_independent_output_validator_accepts_materialized_contract(self) -> None:
        output = structure.materialize(valid_input())
        expected = {
            "aspect_handling": {row["aspect_key"]: row["handling"] for row in output["aspects"]},
            "reference_catalog": {"REF-0001": ["SRC-012-ITEM-0001"]},
            "known_refs": {
                "evidence_refs": ["EV-001", "EV-002"],
                "project_authority_refs": [],
                "test_rule_result_refs": ["RULE-001"],
                "requirement_check_refs": ["REQCHK-001"],
                "measurement_refs": [],
                "finding_refs": ["FND-001"],
                "scope_refs": ["SCOPE-001"],
                "target_refs": ["TARGET-001", "ELEMENT-001"],
                "owner_activity_refs": ["ACTIVITY-001"],
                "inspection_request_refs": [],
                "state_basis_refs": ["STATE-001"],
                "target_draft_keys": [],
            },
        }
        result = output_validator.validate(output["machine_owned_markdown"], expected, "UE-OUT-001")
        self.assertEqual(result.status, "pass", result.to_dict())

    def test_independent_output_validator_rejects_modified_signature(self) -> None:
        output = structure.materialize(valid_input())
        markdown = output["machine_owned_markdown"].replace(
            "element.rendered-text", "focus.state", 1
        )
        expected = {
            "aspect_handling": {row["aspect_key"]: row["handling"] for row in output["aspects"]},
            "reference_catalog": {"REF-0001": ["SRC-012-ITEM-0001"]},
            "known_refs": {
                "evidence_refs": ["EV-001", "EV-002"],
                "project_authority_refs": [],
                "test_rule_result_refs": ["RULE-001"],
                "requirement_check_refs": ["REQCHK-001"],
                "measurement_refs": [],
                "finding_refs": ["FND-001"],
                "scope_refs": ["SCOPE-001"],
                "target_refs": ["TARGET-001", "ELEMENT-001"],
                "owner_activity_refs": ["ACTIVITY-001"],
                "inspection_request_refs": [],
            },
        }
        result = output_validator.validate(markdown, expected, "UE-OUT-NEG-001")
        self.assertEqual(result.status, "fail")
        self.assertIn("request_signature_mismatch", str(result.to_dict()))

    def test_additional_observation_signature_excludes_explanatory_prose(self) -> None:
        first = structure.materialize(valid_input())["evaluations"][0]["additional_observation_links"][0]
        changed = valid_input()
        link = changed["evaluations"][0]["additional_observation_links"][0]
        link["state_description"] = "same state, different explanatory wording"
        link["reason"] = "different semantic explanation"
        link["needed_observation"] = "different prose"
        second = structure.materialize(changed)["evaluations"][0]["additional_observation_links"][0]
        self.assertEqual(first["request_signature"], second["request_signature"])
        self.assertEqual(first["input_evidence_fingerprint"], second["input_evidence_fingerprint"])

    def test_additional_observation_signature_changes_with_identity_and_evidence(self) -> None:
        base = structure.materialize(valid_input())["evaluations"][0]["additional_observation_links"][0]
        changed = valid_input()
        link = changed["evaluations"][0]["additional_observation_links"][0]
        link["state_basis_refs"] = []
        link["input_evidence_refs"] = ["EV-002"]
        updated = structure.materialize(changed)["evaluations"][0]["additional_observation_links"][0]
        self.assertNotEqual(base["request_signature"], updated["request_signature"])
        self.assertNotEqual(base["input_evidence_fingerprint"], updated["input_evidence_fingerprint"])

    def test_same_signature_and_input_fingerprint_must_close_as_no_progress(self) -> None:
        first = structure.materialize(valid_input())["evaluations"][0]["additional_observation_links"][0]
        payload = valid_input()
        payload["existing_additional_observation_links"] = [first]
        link = payload["evaluations"][0]["additional_observation_links"][0]
        link["status"] = "no-progress"
        result = structure.materialize(payload)
        self.assertEqual(result["evaluations"][0]["additional_observation_links"][0]["status"], "no-progress")
        link["status"] = "completed"
        with self.assertRaisesRegex(structure.EvaluationStructureError, "duplicate_additional_observation_must_be_no_progress"):
            structure.materialize(payload)

    def test_wrong_owner_reference_is_rejected(self) -> None:
        payload = valid_input()
        link = payload["evaluations"][0]["additional_observation_links"][0]
        link["inspection_request_ref"] = "OBSREQ-001"
        with self.assertRaisesRegex(structure.EvaluationStructureError, "wrong_inspection_request_ref"):
            structure.materialize(payload)

    def test_reference_item_must_belong_to_selected_entry(self) -> None:
        payload = valid_input()
        payload["evaluations"][0]["applied_references"][0]["source_item_ref"] = "SRC-001-ITEM-0001"
        with self.assertRaisesRegex(structure.EvaluationStructureError, "applied_reference_item_unresolved"):
            structure.materialize(payload)

    def test_every_evaluated_aspect_requires_a_closed_evaluation(self) -> None:
        payload = valid_input()
        payload["aspects"][2] = {"aspect_key": "feedback", "handling": "今回評価する", "reason": None}
        with self.assertRaisesRegex(structure.EvaluationStructureError, "evaluated_aspect_without_result"):
            structure.materialize(payload)

    def test_finding_is_derived_from_status_and_follow_up(self) -> None:
        payload = valid_input()
        row = payload["evaluations"][0]
        row["status"] = "問題なし"
        row["follow_up_required"] = False
        row["finding_draft_key"] = None
        payload["findings"] = []
        result = structure.materialize(payload)
        self.assertFalse(result["evaluations"][0]["finding_required"])
        self.assertIsNone(result["evaluations"][0]["finding_ref"])
        self.assertEqual(result["summary"]["finding_count"], 0)

    def test_reference_free_semantic_evaluation_requires_reason_and_evidence(self) -> None:
        payload = valid_input()
        row = payload["evaluations"][0]
        row["basis"] = ["cross-state-consistency"]
        row["applied_references"] = []
        row["reference_not_used_reason"] = "No public pattern applies to the cross-state inconsistency."
        row["pattern_or_principle"] = None
        row["judgment_reason"] = "The saved state and success state conflict."
        result = structure.materialize(payload)
        self.assertEqual(result["evaluations"][0]["applied_references"], [])

    def test_user_goal_basis_requires_declared_context(self) -> None:
        payload = valid_input()
        payload["evaluations"][0]["basis"] = ["user-goal"]
        with self.assertRaisesRegex(structure.EvaluationStructureError, "user_goal_basis_without_context"):
            structure.materialize(payload)

    def test_formal_wcag_requester_identity_requires_both_execution_refs(self) -> None:
        payload = valid_input()
        link = payload["evaluations"][0]["additional_observation_links"][0]
        link["requester_kind"] = "wcag-procedure"
        link["requester_identity"] = {"criterion_evaluation_ref": "CRIT-EVAL-001"}
        with self.assertRaisesRegex(structure.EvaluationStructureError, "invalid_requester_identity:wcag-procedure"):
            structure.materialize(payload)


if __name__ == "__main__":
    unittest.main()
