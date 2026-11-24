"""qa-workflowのowner verifier登録（Plan 04 section 1）の検証。

登録済みownerの実成果物（実`materialize`、実`build_snapshot`、実選定packet）を
`workflow_runtime.py`へ渡し、ownerの本番CLIによる検証が通った場合だけscopeが完了すること、
読み戻しhash不一致・source変更・script欠落・自己申告だけの入力は完了にならないことを確認する。
"""

from __future__ import annotations

import copy
import hashlib
import json
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tests" / "skills" / "runtime"))
sys.path.insert(0, str(ROOT / "skills" / "qa-workflow" / "scripts"))

import owner_verifiers  # noqa: E402
import test_e2e_selection_contract as selection_fixture  # noqa: E402
import test_pr32_test_reporting as j_fixture  # noqa: E402
import test_test_item_condition_analysis as d_fixture  # noqa: E402
import test_workflow_runtime as wf  # noqa: E402

WORKFLOW_REF = "00000000-0000-4000-8000-000000000044"


def scope(skill: str, target: str, evidence: object) -> dict:
    return {
        "skill": skill,
        "target": target,
        "execution_range": "plan",
        "input_mode": "artifact",
        "normalized_input": {"owner_verification": evidence},
        "current_structure_state": None,
    }


def workflow(scopes: list[dict]) -> dict:
    request = wf.WorkflowRuntimeTests()._request()
    request["input"].update(
        workflow_ref=WORKFLOW_REF,
        # 工程開始時の要求集合は、検証対象のscopeそのものにする（基準fixtureの要求を残さない）。
        requested_scopes=[
            wf.required_scope(row["skill"], row["target"], row["execution_range"])
            for row in scopes
        ],
        workflow_scopes=scopes,
        runtime_units=[],
        current_runtime_units=[],
        current_entities=[],
    )
    return wf.run(request)


def stored_text(value: object) -> str:
    """The text a provider would store (canonical JSON), hashed as exact bytes."""
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class OwnerVerifierRegistryTests(unittest.TestCase):
    def candidate_evidence(self, kind: str) -> tuple[dict, str, str]:
        snapshot = d_fixture.feature_inventory()
        sources = [d_fixture._feature_ref_for(snapshot), d_fixture.spec_ref()]
        if kind == "item":
            artifact = d_fixture._materialize_item(
                d_fixture.item_request(
                    candidates=[d_fixture.item_candidate("order-api")],
                    feature_snapshot=snapshot,
                    sources=sources,
                )
            )["candidate"]
            owner = "test-item-analysis"
        else:
            artifact = d_fixture._materialize_condition(
                d_fixture.condition_request(
                    candidates=[d_fixture.condition_candidate("order-authz")],
                    feature_snapshot=snapshot,
                    sources=sources,
                )
            )["candidate"]
            owner = "test-condition-analysis"
        readback = d_fixture._stored_readback(
            artifact, owner=owner, artifact_ref=artifact["artifact_ref"]
        )
        evidence = {
            "stored_content": stored_text(artifact),
            "readback": readback,
            "expected_revision": readback["revision"],
            "current_source_refs": sources,
        }
        return evidence, owner, artifact["artifact_ref"]

    def assert_blocked(self, result: dict, skill: str, reason: str | None) -> None:
        self.assertEqual(result["runtime_status"], "ok", result)
        self.assertFalse(result["payload"]["can_complete"], result)
        rows = result["payload"]["unverified_scopes"]
        self.assertEqual([row["skill"] for row in rows], [skill], rows)
        if reason is not None:
            self.assertEqual(rows[0]["reason"], reason)
        self.assertEqual(result["payload"]["verified_owner_scopes"], [])

    # --- test-item-analysis / test-condition-analysis --------------------
    def test_stored_candidate_artifacts_complete_their_scope(self) -> None:
        for kind in ("item", "condition"):
            with self.subTest(kind=kind):
                evidence, owner, ref = self.candidate_evidence(kind)
                result = workflow([scope(owner, ref, evidence)])
                self.assertEqual(result["runtime_status"], "ok", result)
                self.assertTrue(result["payload"]["can_complete"], result)
                self.assertEqual(result["payload"]["unverified_scopes"], [])
                [verified] = result["payload"]["verified_owner_scopes"]
                self.assertEqual(verified["skill"], owner)
                self.assertEqual(
                    verified["verified_artifact"]["content_hash"],
                    evidence["readback"]["content_hash"],
                )

    def test_readback_hash_mismatch_is_not_completed(self) -> None:
        evidence, owner, ref = self.candidate_evidence("item")
        evidence["readback"]["content_hash"] = "0" * 64
        self.assert_blocked(
            workflow([scope(owner, ref, evidence)]),
            owner,
            "stored_artifact_readback_not_verified",
        )
        # 保存本文を書き換えても、providerが返したhashと一致しなければ完了にしない。
        evidence, owner, ref = self.candidate_evidence("item")
        tampered = json.loads(evidence["stored_content"])
        tampered["items"][0]["name"] = "edited after save"
        evidence["stored_content"] = stored_text(tampered)
        self.assert_blocked(
            workflow([scope(owner, ref, evidence)]),
            owner,
            "stored_artifact_readback_not_verified",
        )

    def test_changed_source_is_not_current(self) -> None:
        evidence, owner, ref = self.candidate_evidence("condition")
        changed = copy.deepcopy(evidence["current_source_refs"])
        changed[0]["revision"] = "feature-r-changed"
        changed[0]["content_hash"] = "c" * 64
        evidence["current_source_refs"] = changed
        self.assert_blocked(
            workflow([scope(owner, ref, evidence)]), owner, "source_not_current"
        )

    def test_artifact_for_another_target_is_rejected(self) -> None:
        evidence, owner, _ = self.candidate_evidence("item")
        self.assert_blocked(
            workflow([scope(owner, "item-candidates:other", evidence)]),
            owner,
            "artifact_ref_differs_from_scope_target",
        )

    # --- e2e-test-selection ------------------------------------------------
    def selection_evidence(self) -> tuple[dict, str]:
        packet = selection_fixture.selection()
        text = stored_text(packet)
        current = {row["ref"]: row["revision"] for row in packet["source_refs"]}
        return {
            "stored_content": text,
            "readback": {"revision": "git:" + "a" * 40, "content_hash": sha(text)},
            "current_source_revisions": current,
        }, packet["selection_ref"]

    def test_ready_selection_with_matching_readback_completes(self) -> None:
        evidence, ref = self.selection_evidence()
        result = workflow([scope("e2e-test-selection", ref, evidence)])
        self.assertTrue(result["payload"]["can_complete"], result)
        [verified] = result["payload"]["verified_owner_scopes"]
        self.assertEqual(verified["verified_artifact"]["artifact_ref"], ref)

    def test_stale_selection_or_other_stored_content_is_not_completed(self) -> None:
        evidence, ref = self.selection_evidence()
        stale = copy.deepcopy(evidence)
        packet = json.loads(stale["stored_content"])
        packet["source_refs"][1]["currentness"] = "stale"
        stale["stored_content"] = stored_text(packet)
        stale["readback"]["content_hash"] = sha(stale["stored_content"])
        self.assert_blocked(
            workflow([scope("e2e-test-selection", ref, stale)]),
            "e2e-test-selection",
            "selection_not_ready",
        )
        other = copy.deepcopy(evidence)
        other["readback"]["content_hash"] = "0" * 64
        self.assert_blocked(
            workflow([scope("e2e-test-selection", ref, other)]),
            "e2e-test-selection",
            "stored_artifact_readback_not_verified",
        )

    def with_current(self, evidence: dict, **revisions: str) -> dict:
        changed = copy.deepcopy(evidence)
        changed["current_source_revisions"].update(revisions)
        return changed

    def test_selection_source_revision_changes_are_not_current(self) -> None:
        evidence, ref = self.selection_evidence()
        # 仕様改版（SPEC-001 s8→s9）。保存側のcurrentnessは current のまま。
        spec_changed = self.with_current(evidence, **{"SPEC-001": "s9"})
        self.assertEqual(
            json.loads(spec_changed["stored_content"])["source_refs"][0]["currentness"],
            "current",
        )
        self.assert_blocked(
            workflow([scope("e2e-test-selection", ref, spec_changed)]),
            "e2e-test-selection",
            "source_not_current",
        )
        # test item（TI-001 i4→i5）の変更でも不可。
        item_changed = self.with_current(evidence, **{"TI-001": "i5"})
        self.assert_blocked(
            workflow([scope("e2e-test-selection", ref, item_changed)]),
            "e2e-test-selection",
            "source_not_current",
        )

    def test_selection_with_a_source_missing_from_current_map_is_unknown(self) -> None:
        evidence, ref = self.selection_evidence()
        missing = copy.deepcopy(evidence)
        del missing["current_source_revisions"]["TI-001"]
        self.assert_blocked(
            workflow([scope("e2e-test-selection", ref, missing)]),
            "e2e-test-selection",
            "source_revision_unknown",
        )
        # 別selectionのsourceを渡した場合（refが一致しない）も unknown になる。
        other = copy.deepcopy(evidence)
        other["current_source_revisions"] = {"SPEC-777": "s8", "TI-777": "i4"}
        self.assert_blocked(
            workflow([scope("e2e-test-selection", ref, other)]),
            "e2e-test-selection",
            "source_revision_unknown",
        )

    def test_selection_with_empty_or_malformed_current_map_is_rejected(self) -> None:
        evidence, ref = self.selection_evidence()
        for value in ({}, None, ["SPEC-001"], {"SPEC-001": 8}, {"SPEC-001": ""}):
            with self.subTest(value=value):
                broken = copy.deepcopy(evidence)
                broken["current_source_revisions"] = value
                self.assert_blocked(
                    workflow([scope("e2e-test-selection", ref, broken)]),
                    "e2e-test-selection",
                    "owner_verification_schema_invalid",
                )
        missing_key = copy.deepcopy(evidence)
        del missing_key["current_source_revisions"]
        self.assert_blocked(
            workflow([scope("e2e-test-selection", ref, missing_key)]),
            "e2e-test-selection",
            "owner_verification_schema_invalid",
        )

    def test_change_to_a_source_the_selection_does_not_save_is_ignored(self) -> None:
        evidence, ref = self.selection_evidence()
        unrelated = self.with_current(evidence, **{"SPEC-999": "changed"})
        result = workflow([scope("e2e-test-selection", ref, unrelated)])
        self.assertTrue(result["payload"]["can_complete"], result)
        self.assertEqual(result["payload"]["unverified_scopes"], [])

    def test_selection_with_invalid_stored_body_is_not_completed(self) -> None:
        evidence, ref = self.selection_evidence()
        broken = json.loads(evidence["stored_content"])
        broken["history"] = [{"revision": 2}]
        evidence["stored_content"] = stored_text(broken)
        evidence["readback"]["content_hash"] = sha(evidence["stored_content"])
        self.assert_blocked(
            workflow([scope("e2e-test-selection", ref, evidence)]),
            "e2e-test-selection",
            "selection_not_ready",
        )

    def test_candidate_expected_revision_must_be_a_real_saved_revision(self) -> None:
        # owner側はexpected_revision=Noneで比較を省略するため、入口で必ず拒否する。
        for kind, owner in (
            ("item", "test-item-analysis"),
            ("condition", "test-condition-analysis"),
        ):
            evidence, _, ref = self.candidate_evidence(kind)
            evidence["readback"]["revision"] = "rev-WRONG"
            for expected in (None, "", "   ", 7):
                with self.subTest(kind=kind, expected=expected):
                    bypass = copy.deepcopy(evidence)
                    bypass["expected_revision"] = expected
                    self.assert_blocked(
                        workflow([scope(owner, ref, bypass)]),
                        owner,
                        "owner_verification_schema_invalid",
                    )
            missing = copy.deepcopy(evidence)
            del missing["expected_revision"]
            self.assert_blocked(
                workflow([scope(owner, ref, missing)]),
                owner,
                "owner_verification_schema_invalid",
            )
            # 正しいexpected_revisionを渡しても、readback revisionが違えば完了しない。
            mismatch = copy.deepcopy(evidence)
            mismatch["expected_revision"] = "sha256:" + "1" * 64
            self.assert_blocked(
                workflow([scope(owner, ref, mismatch)]),
                owner,
                "stored_artifact_readback_not_verified",
            )

    # --- test-reporting ----------------------------------------------------
    def report_evidence(self) -> tuple[dict, str]:
        build_input = j_fixture.base_input()
        stored = j_fixture.reporting.build_snapshot(build_input)
        return {
            "build_input_content": stored_text(build_input),
            "stored_snapshot_content": stored_text(stored),
            "current": {
                "plan_revision": "p3",
                "source_revisions": {"e2e": "rev1", "api": "rev1"},
            },
        }, stored["snapshot_ref"]

    def test_recomputed_complete_current_snapshot_completes(self) -> None:
        evidence, ref = self.report_evidence()
        result = workflow([scope("test-reporting", ref, evidence)])
        self.assertTrue(result["payload"]["can_complete"], result)

    def test_edited_snapshot_stale_source_or_incomplete_plan_is_not_completed(
        self,
    ) -> None:
        evidence, ref = self.report_evidence()
        edited = copy.deepcopy(evidence)
        snapshot = json.loads(edited["stored_snapshot_content"])
        snapshot["overall"]["complete"] = True
        snapshot["sources"][0]["counts"] = {"PASS": 99}
        edited["stored_snapshot_content"] = stored_text(snapshot)
        self.assert_blocked(
            workflow([scope("test-reporting", ref, edited)]),
            "test-reporting",
            "stored_snapshot_differs_from_recomputed",
        )
        stale = copy.deepcopy(evidence)
        stale["current"]["source_revisions"]["api"] = "rev2"
        self.assert_blocked(
            workflow([scope("test-reporting", ref, stale)]),
            "test-reporting",
            "snapshot_not_current",
        )
        partial = copy.deepcopy(evidence)
        build_input = json.loads(partial["build_input_content"])
        build_input["retrievals"][1]["records"].pop()
        partial["build_input_content"] = stored_text(build_input)
        recomputed = j_fixture.reporting.build_snapshot(build_input)
        partial["stored_snapshot_content"] = stored_text(recomputed)
        self.assert_blocked(
            workflow([scope("test-reporting", recomputed["snapshot_ref"], partial)]),
            "test-reporting",
            "snapshot_not_complete",
        )

    # --- 共通 ---------------------------------------------------------------
    def test_self_declared_verification_without_evidence_is_not_completed(
        self,
    ) -> None:
        declared = {"verified": True, "can_complete": True, "valid": True}
        for skill in (
            "test-item-analysis",
            "e2e-test-selection",
            "test-reporting",
            "defect-management",
        ):
            with self.subTest(skill=skill):
                result = workflow([scope(skill, "any", declared)])
                self.assertFalse(result["payload"]["can_complete"], result)
                self.assertEqual(
                    [row["skill"] for row in result["payload"]["unverified_scopes"]],
                    [skill],
                )

    def test_missing_owner_script_leaves_the_scope_unverified(self) -> None:
        evidence, ref = self.selection_evidence()
        with mock.patch.object(owner_verifiers, "SKILLS_ROOT", Path("/nonexistent")):
            outcome = owner_verifiers.verify(
                "e2e-test-selection", scope("e2e-test-selection", ref, evidence)
            )
        self.assertEqual(
            outcome,
            {"status": "unverified", "reason": "owner_verifier_unavailable"},
        )

    def test_registered_owners_have_an_entry_point_and_others_stay_blocked(
        self,
    ) -> None:
        self.assertEqual(
            set(owner_verifiers.VERIFIERS),
            {
                "test-item-analysis",
                "test-condition-analysis",
                "e2e-test-selection",
                "test-reporting",
                "test-requirements-analysis",
                "test-architecture-design",
                "test-management",
            },
        )
        # 検証入口を持たないownerは登録しない（登録しないことが完了不可を保つ）。
        for skill in (
            "defect-management",
            "test-evaluation",
            "feature-analysis",
            "project-context",
        ):
            with self.subTest(skill=skill):
                self.assertEqual(
                    owner_verifiers.verify(skill, scope(skill, "x", {})),
                    {
                        "status": "unverified",
                        "reason": owner_verifiers.NOT_REGISTERED,
                    },
                )

    def test_runtime_v2_skills_are_unchanged_by_the_registry(self) -> None:
        request = wf.WorkflowRuntimeTests()._request()
        baseline = wf.run(request)
        self.assertTrue(baseline["payload"]["can_complete"], baseline)
        evidence, ref = self.selection_evidence()
        request["input"]["workflow_scopes"].append(
            scope("e2e-test-selection", ref, evidence)
        )
        request["input"]["requested_scopes"].append(
            wf.required_scope("e2e-test-selection", ref, "plan")
        )
        result = wf.run(request)
        self.assertTrue(result["payload"]["can_complete"], result)
        self.assertEqual(
            baseline["payload"]["runtime_units"], result["payload"]["runtime_units"]
        )
        self.assertEqual(
            baseline["payload"]["entity_freshness"],
            result["payload"]["entity_freshness"],
        )


if __name__ == "__main__":
    unittest.main()
