"""Isolated provider-native persistence and owner integration regression tests."""

from __future__ import annotations

import copy
import sqlite3
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[3] / "skills"
sys.path.insert(0, str(SKILL_ROOT / "project-context" / "scripts"))
sys.path.insert(0, str(SKILL_ROOT / "feature-analysis" / "scripts"))

from artifact_store import LocalArtifactStore, StoreError  # noqa: E402
from feature_registry import persist_snapshot  # noqa: E402
from project_context import persist_prepared  # noqa: E402
from test_feature_registry import fixture  # noqa: E402


class ArtifactStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.allowed = True
        self.approvals: list[dict] = []

        def authorize(request: dict) -> bool:
            self.approvals.append(request.copy())
            if request["operation"] == "read":
                return self.allowed and request["project_ref"] == "Sample"
            return self.allowed and request["approval_ref"] == "approval/verified"

        self.authorize = authorize
        self.store = LocalArtifactStore(self.root, self.root, self.authorize)

    def write(
        self,
        *,
        kind: str = "project-context",
        content: str = "initial",
        expected_revision: str | None = None,
        operation_id: str = "op-1",
    ) -> dict:
        return self.store.write(
            kind=kind,
            project_ref="Sample",
            artifact_ref="artifact.md",
            content=content,
            expected_revision=expected_revision,
            operation_id=operation_id,
            source_ref="issue/1",
            source_revision="source-v1",
            approval_ref="approval/verified",
            approval_revision="policy-v1",
            change_reason="reviewed",
        )

    def test_create_revision_readback_and_no_lost_update(self) -> None:
        first = self.write()
        self.assertEqual(first["status"], "stored")
        self.assertEqual(first["revision"], "r1")
        self.assertEqual(first["previous_revision"], None)
        self.assertEqual(
            self.store.read_current("project-context", "Sample", "artifact.md")[
                "content"
            ],
            "initial",
        )
        second = self.write(
            content="updated", expected_revision="r1", operation_id="op-2"
        )
        self.assertEqual(second["revision"], "r2")
        self.assertEqual(
            self.store.read_revision("project-context", "Sample", "artifact.md", "r1")[
                "content"
            ],
            "initial",
        )
        with self.assertRaisesRegex(StoreError, "revision_conflict"):
            self.write(content="stale", expected_revision="r1", operation_id="op-stale")
        self.assertEqual(
            self.store.read_current("project-context", "Sample", "artifact.md")[
                "content"
            ],
            "updated",
        )

    def test_duplicate_operation_same_payload_is_idempotent(self) -> None:
        self.write()
        self.assertEqual(self.write()["status"], "idempotent")
        self.write(content="v2", expected_revision="r1", operation_id="op-2")
        self.assertEqual(self.write()["status"], "superseded")
        with self.assertRaisesRegex(StoreError, "operation_id_reused"):
            self.write(content="different")

    def test_authorization_is_a_trusted_callback_not_json_flag(self) -> None:
        self.allowed = False
        with self.assertRaisesRegex(StoreError, "access_denied"):
            self.write()
        with self.assertRaisesRegex(StoreError, "access_denied"):
            self.store.read_current("project-context", "Sample", "artifact.md")
        self.allowed = True
        self.assertIsNone(
            self.store.read_current("project-context", "Sample", "artifact.md")
        )
        self.assertEqual(self.write()["status"], "stored")
        self.assertEqual(self.approvals[-1]["sha256"], self.write()["sha256"])


    def test_read_denied_for_other_project_and_revoked_access(self) -> None:
        self.write()
        with self.assertRaisesRegex(StoreError, "access_denied"):
            self.store.read_current("project-context", "Other", "artifact.md")
        with self.assertRaisesRegex(StoreError, "access_denied"):
            self.store.read_revision(
                "project-context", "Other", "artifact.md", "r1"
            )
        self.allowed = False
        with self.assertRaisesRegex(StoreError, "access_denied"):
            self.store.read_revision(
                "project-context", "Sample", "artifact.md", "r1"
            )
        with self.assertRaisesRegex(StoreError, "access_denied"):
            self.write()
        self.allowed = True

    def test_replayed_write_cannot_bypass_revoked_permission(self) -> None:
        self.write()
        self.allowed = False
        with self.assertRaisesRegex(StoreError, "access_denied"):
            self.write()
        self.allowed = True
        self.assertEqual(self.write()["status"], "idempotent")

    def test_authorization_service_error_does_not_write(self) -> None:
        def unavailable(_: dict) -> bool:
            raise RuntimeError("service unavailable")

        store = LocalArtifactStore(self.root, self.root, unavailable)
        with self.assertRaisesRegex(StoreError, "approval_provider_unavailable"):
            store.write(
                kind="project-context",
                project_ref="Sample",
                artifact_ref="unapproved.md",
                content="draft",
                expected_revision=None,
                operation_id="operation-denied",
                source_ref="issue/1",
                source_revision="r1",
                approval_ref="approval/verified",
                approval_revision="policy-v1",
                change_reason="attempt",
            )
        with self.assertRaisesRegex(StoreError, "approval_provider_unavailable"):
            store.read_current("project-context", "Sample", "unapproved.md")
        self.assertIsNone(
            self.store.read_current("project-context", "Sample", "unapproved.md")
        )

    def test_atomic_update_from_two_connections(self) -> None:
        self.write()

        def update(idx: int) -> str:
            store = LocalArtifactStore(self.root, self.root, self.authorize)
            try:
                return store.write(
                    kind="project-context",
                    project_ref="Sample",
                    artifact_ref="artifact.md",
                    content=f"parallel-{idx}",
                    expected_revision="r1",
                    operation_id=f"parallel-{idx}",
                    source_ref="issue/1",
                    source_revision="v2",
                    approval_ref="approval/verified",
                    approval_revision="policy-v1",
                    change_reason="concurrent edit",
                )["status"]
            except StoreError as exc:
                return str(exc)

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(update, (1, 2)))
        self.assertEqual(sorted(results), ["revision_conflict", "stored"])
        self.assertEqual(
            self.store.read_current("project-context", "Sample", "artifact.md")[
                "revision"
            ],
            "r2",
        )

    def test_untrusted_root_and_symlink_rejected(self) -> None:
        other = self.root / "other"
        other.mkdir()
        with self.assertRaisesRegex(StoreError, "unauthorized_root"):
            LocalArtifactStore(other, self.root, self.authorize)
        link = self.root / "link"
        try:
            link.symlink_to(other, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("directory symlinks unavailable")
        with self.assertRaisesRegex(StoreError, "root_symlink_rejected"):
            LocalArtifactStore(link, link, self.authorize)

    def test_corrupted_revision_is_not_verified(self) -> None:
        self.write()
        with sqlite3.connect(self.store.path) as conn:
            conn.execute(
                """UPDATE artifact_revisions SET content=? WHERE version=1""",
                (b"tampered",),
            )
        with self.assertRaisesRegex(StoreError, "readback_hash_mismatch"):
            self.store.read_current("project-context", "Sample", "artifact.md")


    def test_create_cannot_redirect_absence_to_unchecked_path(self) -> None:
        request = {
            "operation": "prepare-create",
            "project_name": "Sample",
            "enumeration_complete": True,
            "candidates": [{"ref": "approved.md", "status": "absent"}],
            "artifact_ref": "other.md",
            "source_ref": "issue/1",
            "source_revision": "r1",
            "change_reason": "initial",
        }
        result = persist_prepared(
            self.store,
            request,
            project_ref="Sample",
            operation_id="redirect",
            approval_ref="approval/verified",
            approval_revision="policy-v1",
        )
        self.assertEqual(result["status"], "blocked", result)
        self.assertIsNone(
            self.store.read_current("project-context", "Sample", "other.md")
        )

    def test_project_context_create_and_update_are_stored(self) -> None:
        initial = {
            "operation": "prepare-create",
            "project_name": "Sample",
            "enumeration_complete": True,
            "candidates": [{"ref": "project-context.md", "status": "absent"}],
            "artifact_ref": "project-context.md",
            "source_ref": "issue/1",
            "source_revision": "r1",
            "change_reason": "initialization",
        }
        first = persist_prepared(
            self.store,
            initial,
            project_ref="Sample",
            operation_id="project-create",
            approval_ref="approval/verified",
            approval_revision="policy-v1",
        )
        self.assertEqual(first["status"], "stored", first)
        current = self.store.read_current(
            "project-context", "Sample", "project-context.md"
        )
        update = {
            "operation": "prepare-update",
            "markdown": current["content"],
            "artifact_ref": "project-context.md",
            "expected_revision": current["revision"],
            "source_ref": "issue/2",
            "source_revision": "r2",
            "change_reason": "new source",
            "updates": {"qa.feature_artifact_root": "qa/feature-list"},
        }
        result = persist_prepared(
            self.store,
            update,
            project_ref="Sample",
            operation_id="project-update",
            approval_ref="approval/verified",
            approval_revision="policy-v1",
        )
        self.assertEqual(result["status"], "stored", result)
        self.assertEqual(result["revision"], "r2")
        self.assertIn(
            "qa/feature-list",
            self.store.read_current("project-context", "Sample", "project-context.md")[
                "content"
            ],
        )
        update["expected_revision"] = "r1"
        self.assertEqual(
            persist_prepared(
                self.store,
                update,
                project_ref="Sample",
                operation_id="project-stale",
                approval_ref="approval/verified",
                approval_revision="policy-v1",
            )["status"],
            "blocked",
        )

    def test_placement_is_persisted_only_after_verified_approval(self) -> None:
        initial = {
            "operation": "prepare-create",
            "project_name": "Sample",
            "enumeration_complete": True,
            "candidates": [{"ref": "context.md", "status": "absent"}],
            "artifact_ref": "context.md",
            "source_ref": "source/1",
            "source_revision": "rev-1",
            "change_reason": "init",
        }
        first = persist_prepared(
            self.store,
            initial,
            project_ref="Sample",
            operation_id="init",
            approval_ref="approval/verified",
            approval_revision="approval-v1",
        )
        self.assertEqual(first["status"], "stored", first)
        markdown = self.store.read_current("project-context", "Sample", "context.md")[
            "content"
        ]
        policy = {
            "owner": "project-context",
            "scope": "Sample",
            "target_ref": "qa/artifacts",
            "revision": "policy-v1",
            "approval_ref": "approval/verified",
            "approval_revision": "approval-v1",
            "editable_scope": "markdown/working",
            "feature_index_ref": "qa/features/index.md",
        }
        change = {
            "operation": "prepare-placement",
            "markdown": markdown,
            "dec_asm_owner": "project-context",
            "artifact_ref": "context.md",
            "expected_revision": "r1",
            "source_ref": "source/2",
            "source_revision": "rev-2",
            "change_reason": "approved layout",
            "policy": policy,
        }
        self.allowed = False
        rejected = persist_prepared(
            self.store,
            change,
            project_ref="Sample",
            operation_id="layout-1",
            approval_ref="approval/verified",
            approval_revision="approval-v1",
        )
        self.assertEqual(rejected["status"], "blocked")
        self.assertEqual(
            self.store.read_current("project-context", "Sample", "context.md")[
                "revision"
            ],
            "r1",
        )
        self.allowed = True
        stored = persist_prepared(
            self.store,
            change,
            project_ref="Sample",
            operation_id="layout-1",
            approval_ref="approval/verified",
            approval_revision="approval-v1",
        )
        self.assertEqual(stored["status"], "stored", stored)
        self.assertEqual(stored["revision"], "r2")
        self.assertIn(
            "qa/features/index.md",
            self.store.read_current("project-context", "Sample", "context.md")[
                "content"
            ],
        )


    def test_placement_change_retires_earlier_decision(self) -> None:
        initial = {
            "operation": "prepare-create",
            "project_name": "Sample",
            "enumeration_complete": True,
            "candidates": [{"ref": "context.md", "status": "absent"}],
            "artifact_ref": "context.md",
            "source_ref": "source/1",
            "source_revision": "r1",
            "change_reason": "init",
        }
        self.assertEqual(
            persist_prepared(
                self.store,
                initial,
                project_ref="Sample",
                operation_id="create-for-policy",
                approval_ref="approval/verified",
                approval_revision="policy-v1",
            )["status"],
            "stored",
        )
        initial_policy = {
            "owner": "project-context",
            "scope": "Sample",
            "target_ref": "qa/old",
            "revision": "policy-v1",
            "approval_ref": "approval/verified",
            "approval_revision": "policy-v1",
            "editable_scope": "markdown/worktree",
            "feature_index_ref": "qa/feature-index.md",
        }
        first = {
            "operation": "prepare-placement",
            "markdown": self.store.read_current(
                "project-context", "Sample", "context.md"
            )["content"],
            "dec_asm_owner": "project-context",
            "artifact_ref": "context.md",
            "expected_revision": "r1",
            "source_ref": "source/2",
            "source_revision": "r2",
            "change_reason": "initial policy",
            "policy": initial_policy,
        }
        stored = persist_prepared(
            self.store,
            first,
            project_ref="Sample",
            operation_id="first-policy",
            approval_ref="approval/verified",
            approval_revision="policy-v1",
        )
        self.assertEqual(stored["status"], "stored")
        previous = self.store.read_current(
            "project-context", "Sample", "context.md"
        )["content"]
        prior_decision = {
            "draft_key": None,
            "identity_action": "reuse",
            "reuse_id": "DEC-001",
            "cells": {
                "確定内容": "QA成果物配置・人間編集方針",
                "状態": "有効",
                "決定根拠": "approval/verified",
                "影響範囲": "Sample",
                "関係": "独立",
                "関連仕様根拠ID": "",
                "置換先ID": "",
                "備考": (
                    "owner=project-context; target=qa/old; policy=policy-v1; "
                    "editable=markdown/worktree; index=qa/feature-index.md"
                ),
            },
        }
        second = {
            **first,
            "markdown": previous,
            "expected_revision": "r2",
            "existing_policy": {**initial_policy, "decision_id": "DEC-001"},
            "existing_decisions": [prior_decision],
            "policy": {
                **initial_policy,
                "target_ref": "qa/new",
                "revision": "policy-v2",
                "approval_revision": "policy-v2",
            },
        }
        changed = persist_prepared(
            self.store,
            second,
            project_ref="Sample",
            operation_id="second-policy",
            approval_ref="approval/verified",
            approval_revision="policy-v2",
        )
        self.assertEqual(changed["status"], "stored", changed)
        self.assertEqual(changed["revision"], "r3")
        current = self.store.read_current(
            "project-context", "Sample", "context.md"
        )["content"]
        self.assertIn("| DEC-001 | QA成果物配置・人間編集方針 | 置換済み |", current)
        self.assertIn("| DEC-002 | QA成果物配置・人間編集方針 | 有効 |", current)
        self.assertIn("| QA成果物配置 | qa/new | Sample |", current)


    def test_section_update_requires_expected_revision_and_history(self) -> None:
        initial = {
            "operation": "prepare-create",
            "project_name": "Sample",
            "enumeration_complete": True,
            "candidates": [{"ref": "context.md", "status": "absent"}],
            "artifact_ref": "context.md",
            "source_ref": "source/1",
            "source_revision": "r1",
            "change_reason": "init",
        }
        first = persist_prepared(
            self.store,
            initial,
            project_ref="Sample",
            operation_id="create",
            approval_ref="approval/verified",
            approval_revision="policy-v1",
        )
        self.assertEqual(first["status"], "stored")
        current = self.store.read_current("project-context", "Sample", "context.md")
        update = {
            "operation": "prepare-sections",
            "markdown": current["content"],
            "artifact_ref": "context.md",
            "expected_revision": "r1",
            "source_ref": "source/2",
            "source_revision": "r2",
            "change_reason": "scope confirmed",
            "section_updates": {"2": "- 製品: Sample Store"},
        }
        changed = persist_prepared(
            self.store,
            update,
            project_ref="Sample",
            operation_id="scope-update",
            approval_ref="approval/verified",
            approval_revision="policy-v1",
        )
        self.assertEqual(changed["status"], "stored", changed)
        self.assertEqual(changed["revision"], "r2")
        self.assertEqual(
            self.store.read_revision("project-context", "Sample", "context.md", "r1")[
                "content"
            ],
            current["content"],
        )

    def test_feature_inventory_snapshot_requires_saved_predecessor(self) -> None:
        request = fixture()
        request["snapshot"]["project_ref"] = "Sample"
        first = persist_snapshot(
            self.store,
            request,
            expected_revision=None,
            approval_ref="approval/verified",
            approval_revision="policy-v1",
            change_reason="initial inventory",
        )
        self.assertEqual(first["status"], "stored", first)
        self.assertEqual(first["analysis_status"], "complete")
        prior = copy.deepcopy(request["snapshot"])
        request["previous_snapshot"] = prior
        request["snapshot"]["event"] = "analysis_update"
        request["snapshot"]["event_basis"] = {
            "source_revision": request["snapshot"]["source_revision"],
            "evidence_ref": "review/confirmed",
        }
        request["snapshot"]["artifact_revision"] = "art-v2"
        request["snapshot"]["previous_artifact_revision"] = "art-v1"
        request["snapshot"]["operation_id"] = "op-2"
        second = persist_snapshot(
            self.store,
            request,
            expected_revision="r1",
            approval_ref="approval/verified",
            approval_revision="policy-v1",
            change_reason="reconfirmed",
        )
        self.assertEqual(second["status"], "stored", second)
        self.assertEqual(second["revision"], "r2")
        request["snapshot"]["operation_id"] = "op-3"
        request["snapshot"]["artifact_revision"] = "art-v3"
        bad = persist_snapshot(
            self.store,
            request,
            expected_revision="r2",
            approval_ref="approval/verified",
            approval_revision="policy-v1",
            change_reason="stale prior snapshot",
        )
        self.assertEqual(bad["status"], "blocked", bad)
        self.assertEqual(bad["reasons"], ["previous_snapshot_not_current"])


if __name__ == "__main__":
    unittest.main()
