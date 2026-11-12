"""B（feature-analysis）の保存済みsnapshotをD（test-item／condition-analysis）へ渡す横断契約。

実Gitリポジトリへ`persist_snapshot()`で保存し、`candidate_handoff()`で読み戻した値を
Dの実`materialize`へ渡す。Bの出力を手書きしたfixtureは使わない。
"""

from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
for skill in (
    "project-context",
    "feature-analysis",
    "test-item-analysis",
    "test-condition-analysis",
):
    sys.path.insert(0, str(ROOT / "skills" / skill / "scripts"))
sys.path.insert(0, str(ROOT / "tests" / "skills" / "runtime"))

import test_pr24_git_artifact_store as git_store_tests  # noqa: E402
from candidate_support import ContractError  # noqa: E402
from condition_candidates import run as run_conditions  # noqa: E402
from feature_registry import candidate_handoff, persist_snapshot  # noqa: E402
from item_candidates import run as run_items  # noqa: E402

ARTIFACT_REF = "qa/feature-inventory.json"


class FeatureToCandidateHandoffTests(unittest.TestCase):
    # 実Git storeとB fixtureの組立てだけを再利用し、既存テストは継承しない。
    setUp = git_store_tests.GitArtifactStoreTests.setUp
    new_store = git_store_tests.GitArtifactStoreTests.new_store
    _code_registry = git_store_tests.GitArtifactStoreTests._code_registry

    def saved_handoff(self) -> tuple[dict, dict, str]:
        request, evidence = self._code_registry()
        saved = persist_snapshot(
            self.store,
            request,
            expected_revision=None,
            approval_ref="approval/verified",
            approval_revision="policy-v1",
            change_reason="initial inventory",
            git_inventory_requests=evidence,
        )
        self.assertEqual(saved["status"], "stored", saved)
        head = evidence[0]["head_sha"]
        handoff = candidate_handoff(
            self.store,
            project_ref="Sample",
            artifact_ref=ARTIFACT_REF,
            storage_revision=saved["revision"],
            previous_snapshot=None,
            observed_head_revision=head,
        )
        return handoff, saved, head

    def item_request(self, handoff: dict) -> dict:
        feature_ids = [
            row["id"] for row in handoff["feature_inventory"]["snapshot"]["features"]
        ]
        return {
            "operation": "materialize",
            "scope": "Sample",
            "artifact_ref": "item-candidates:sample",
            "feature_inventory": handoff["feature_inventory"],
            "source_refs": [handoff["feature_ref"]],
            "expected_revision": None,
            "current_revision": None,
            "approval_ref": None,
            "required_permission": "owner_artifact_write",
            "previous_artifact": None,
            "candidates": [
                {
                    "candidate_key": "auth-access",
                    "identity_action": "new",
                    "item_id": None,
                    "related_item_ids": [],
                    "reason": "B inventory feature",
                    "name": "auth access",
                    "description": "access control target",
                    "kind": "api",
                    "status": "implemented",
                    "parent_item_refs": [],
                    "feature_refs": [feature_ids[0]],
                    "evidence_refs": [handoff["feature_ref"]],
                }
            ],
            "retirements": [],
        }

    def test_saved_snapshot_is_accepted_by_item_and_condition_analysis(self) -> None:
        handoff, saved, _ = self.saved_handoff()
        self.assertIn(handoff["status"], {"complete", "incomplete"}, handoff)
        ref = handoff["feature_ref"]
        self.assertEqual(ref["owner"], "feature-analysis")
        self.assertEqual(ref["scope"], "Sample")
        # 論理revisionと保存先revisionを混同しない。
        self.assertEqual(
            ref["revision"],
            handoff["feature_inventory"]["snapshot"]["artifact_revision"],
        )
        self.assertEqual(handoff["storage"]["storage_revision"], saved["revision"])
        self.assertNotEqual(ref["revision"], saved["revision"])
        self.assertEqual(ref["content_hash"], saved["sha256"])

        items = run_items(self.item_request(handoff))
        self.assertTrue(items["valid"], items)

        request = self.item_request(handoff)
        feature_id = request["candidates"][0]["feature_refs"][0]
        condition_request = {
            **{k: v for k, v in request.items() if k != "candidates"},
            "artifact_ref": "condition-candidates:sample",
            "candidates": [
                {
                    "candidate_key": "auth-required",
                    "identity_action": "new",
                    "condition_id": None,
                    "related_condition_ids": [],
                    "reason": "B inventory feature",
                    "name": "authentication required",
                    "intent": "verify access requires authentication",
                    "kind": "authorization",
                    "applicable_item_kinds": ["api"],
                    "feature_refs": [feature_id],
                    "item_refs": [],
                    "authority_refs": [],
                    "evidence_refs": [handoff["feature_ref"]],
                    "candidate_state": "unconfirmed",
                    "unknowns": ["authority not yet resolved"],
                }
            ],
        }
        conditions = run_conditions(condition_request)
        self.assertTrue(conditions["valid"], conditions)

    def test_d_rejects_a_feature_ref_that_differs_from_the_saved_snapshot(
        self,
    ) -> None:
        handoff, _, _ = self.saved_handoff()
        for field, value in (("content_hash", "0" * 64), ("revision", "other")):
            with self.subTest(field=field):
                tampered = copy.deepcopy(handoff)
                tampered["feature_ref"][field] = value
                with self.assertRaises(ContractError):
                    run_items(self.item_request(tampered))

    def test_handoff_blocks_when_source_head_moved(self) -> None:
        request, evidence = self._code_registry()
        saved = persist_snapshot(
            self.store,
            request,
            expected_revision=None,
            approval_ref="approval/verified",
            approval_revision="policy-v1",
            change_reason="initial inventory",
            git_inventory_requests=evidence,
        )
        stale = candidate_handoff(
            self.store,
            project_ref="Sample",
            artifact_ref=ARTIFACT_REF,
            storage_revision=saved["revision"],
            previous_snapshot=None,
            observed_head_revision="f" * 40,
        )
        self.assertEqual(stale["status"], "blocked")
        self.assertIn("analysis_stale", stale["reasons"])

    def test_handoff_blocks_for_unknown_storage_revision_or_project(self) -> None:
        handoff, saved, head = self.saved_handoff()
        self.assertNotEqual(handoff["status"], "blocked")
        for kwargs in (
            {"storage_revision": "git:" + "0" * 40, "project_ref": "Sample"},
            {"storage_revision": saved["revision"], "project_ref": "Other"},
        ):
            with self.subTest(**kwargs):
                result = candidate_handoff(
                    self.store,
                    artifact_ref=ARTIFACT_REF,
                    previous_snapshot=None,
                    observed_head_revision=head,
                    **kwargs,
                )
                self.assertEqual(result["status"], "blocked", result)


if __name__ == "__main__":
    unittest.main()
