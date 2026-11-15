"""I（exploratory-testing）のFindingをJ（defect-management）の欠陥候補へ渡す横断契約。

Iの実`build_follow_up_handoff()`の出力から`defect_candidate_source()`で候補を作り、
Jの実`assess_candidate()`へ渡す。手書きの候補は使わない。
"""

from __future__ import annotations

import copy
import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def _load(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


exploratory = _load(
    "cross_owner_exploratory",
    "skills/exploratory-testing/scripts/exploratory_runtime.py",
)
defect = _load(
    "cross_owner_defect", "skills/defect-management/scripts/defect_runtime.py"
)

CHARTER = {
    "purpose": "explore checkout without prepared cases",
    "in_scope": ["checkout"],
    "out_of_scope": ["payment"],
    "source_refs": ["change:CHG-1"],
    "focus_refs": ["risk:R-1"],
    "timebox_or_exit_condition": "20 minutes",
    "allowed_origins": ["https://staging.example.test"],
    "allowed_operations": ["navigate", "submit_form"],
    "side_effect_operations": ["submit_form"],
    "side_effect_scope": "test account only",
    "side_effect_action_definition": "one form submission",
    "side_effect_maximum": 2,
    "cleanup_plan": "delete created test data",
    "evidence_policy": "refs only",
    "block_conditions": ["origin changes"],
}
TARGET = {"build_ref": "build:41", "source_revision": "abc123"}
ENVIRONMENT = {"origin": "https://staging.example.test", "account": "test"}
SESSION_REVISION = "sess-rev-1"


def session(**overrides) -> dict:
    value = {
        "schema_version": "1",
        "session_ref": "SES-1",
        "mode": "exploration",
        "charter": copy.deepcopy(CHARTER),
        "state": "完了",
        "observations": [
            {
                "observation_ref": "OBS-1",
                "action_or_observation": "submit the order form",
                "observed_fact": "HTTP 500 is returned",
                "evidence_refs": ["ev:1"],
            }
        ],
        "findings": [
            {
                "finding_ref": "FND-1",
                "source_observation_refs": ["OBS-1"],
                "evidence_refs": ["ev:1"],
                "follow_up_reason": "order submission fails",
                "recommended_routing": "defect-management",
            }
        ],
        "unresolved": [],
        "cleanup": {"required": False, "status": "対象なし", "evidence_refs": []},
        "residual_side_effect": [],
        "charter_snapshot_identity": exploratory.charter_identity(
            CHARTER, TARGET, ENVIRONMENT
        ),
        "source_revisions": {"change:CHG-1": "rev-chg-1"},
    }
    value.update(overrides)
    return value


class ExplorationToDefectTests(unittest.TestCase):
    def handoff(self, value: dict) -> dict:
        result = exploratory.build_follow_up_handoff(
            value, "FND-1", session_revision=SESSION_REVISION
        )
        self.assertEqual(result["status"], "ready", result)
        return result["handoff"]

    def source(self, value: dict, **kwargs) -> dict:
        return exploratory.defect_candidate_source(
            self.handoff(value),
            value,
            target_snapshot=kwargs.pop("target_snapshot", TARGET),
            environment_conditions=kwargs.pop("environment_conditions", ENVIRONMENT),
            **kwargs,
        )

    def test_finding_without_cause_or_basis_is_returned_by_the_defect_owner(
        self,
    ) -> None:
        result = self.source(session())
        self.assertEqual(result["status"], "ready", result)
        candidate = result["candidate"]
        self.assertEqual(candidate["run_ref"], f"SES-1@{SESSION_REVISION}")
        self.assertEqual(candidate["result_ref"], "FND-1")
        self.assertEqual(candidate["target"], {"kind": "build", "ref": "build:41"})
        assessed = defect.assess_candidate(candidate)
        # Jは原因未確定・期待結果の根拠なしを既存規則で差し戻す（Iは補わない）。
        self.assertEqual(assessed["status"], "returned", assessed)
        self.assertEqual(
            set(assessed["reasons"]),
            {"cause_unconfirmed", "expected_result_basis_missing"},
        )
        self.assertEqual(
            assessed["return_to"],
            {"owner": "exploratory-testing", "spec": "spec-analysis"},
        )
        self.assertFalse(assessed["formal_defect"])

    def test_confirmed_cause_and_spec_basis_make_a_ready_candidate(self) -> None:
        result = self.source(
            session(),
            cause={"status": "confirmed"},
            expected_result={"basis_ref": "spec:SPEC-012", "basis_revision": "r5"},
        )
        assessed = defect.assess_candidate(result["candidate"])
        self.assertEqual(assessed["status"], "ready", assessed)
        self.assertEqual(assessed["candidate_state"], "ready_for_external_handoff")
        self.assertFalse(assessed["automatic_registration"])

    def test_unfinished_session_is_not_a_finalized_result(self) -> None:
        result = self.source(
            session(state="実行中"),
            cause={"status": "confirmed"},
            expected_result={"basis_ref": "spec:SPEC-012", "basis_revision": "r5"},
        )
        assessed = defect.assess_candidate(result["candidate"])
        self.assertEqual(assessed["status"], "returned")
        self.assertIn("source_result_not_finalized", assessed["reasons"])

    def test_other_build_or_environment_cannot_be_attached_to_the_finding(
        self,
    ) -> None:
        value = session()
        handoff = self.handoff(value)
        for kwargs in (
            {"target_snapshot": {**TARGET, "build_ref": "build:42"}},
            {"environment_conditions": {**ENVIRONMENT, "account": "other"}},
        ):
            with self.subTest(**kwargs):
                result = exploratory.defect_candidate_source(
                    handoff,
                    value,
                    **{
                        "target_snapshot": TARGET,
                        "environment_conditions": ENVIRONMENT,
                        **kwargs,
                    },
                )
                self.assertEqual(result["status"], "blocked")
                self.assertEqual(result["reason"], "charter_snapshot_identity_mismatch")

    def test_handoff_for_other_owners_or_unresolved_findings_is_blocked(self) -> None:
        other = session()
        other["findings"][0]["recommended_routing"] = "question-analysis"
        handoff = self.handoff(other)
        result = exploratory.defect_candidate_source(
            handoff,
            other,
            target_snapshot=TARGET,
            environment_conditions=ENVIRONMENT,
        )
        self.assertEqual(result["reason"], "not_a_defect_management_handoff")
        unresolved = session(unresolved=["owner unclear"])
        blocked = exploratory.build_follow_up_handoff(
            unresolved, "FND-1", session_revision=SESSION_REVISION
        )
        self.assertEqual(blocked["status"], "blocked")
        self.assertEqual(blocked["reason"], "unresolved_finding_not_defect_candidate")

    def test_target_without_build_or_revision_is_blocked(self) -> None:
        target = {"note": "no build"}
        value = session(
            charter_snapshot_identity=exploratory.charter_identity(
                CHARTER, target, ENVIRONMENT
            )
        )
        result = self.source(value, target_snapshot=target)
        self.assertEqual(result["reason"], "target_build_or_revision_missing")


if __name__ == "__main__":
    unittest.main()
