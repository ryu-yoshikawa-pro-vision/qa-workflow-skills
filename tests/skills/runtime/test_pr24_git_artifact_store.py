"""Isolated Git-native canonical Markdown and feature inventory CAS tests."""

from __future__ import annotations

import copy
import hashlib
import subprocess
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[3] / "skills"
sys.path.insert(0, str(SKILL_ROOT / "project-context" / "scripts"))
sys.path.insert(0, str(SKILL_ROOT / "feature-analysis" / "scripts"))

from artifact_store import StoreError  # noqa: E402
from feature_registry import persist_snapshot  # noqa: E402
from git_artifact_store import GitArtifactStore  # noqa: E402
from project_context import handle as context_handle  # noqa: E402
from project_context import persist_prepared  # noqa: E402
from test_feature_registry import fixture  # noqa: E402


def git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


class GitArtifactStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        git(self.root, "init", "-q")
        git(self.root, "config", "user.email", "qa@example.invalid")
        git(self.root, "config", "user.name", "QA")
        (self.root / "README.md").write_text("original\n", encoding="utf-8")
        git(self.root, "add", ".")
        git(self.root, "commit", "-qm", "baseline")
        git(self.root, "branch", "qa-artifacts")
        self.allowed_projects = {"Sample"}
        self.allow_write = True

        def authorize(request: dict) -> bool:
            if request["project_ref"] not in self.allowed_projects:
                return False
            if request["operation"] == "read":
                return True
            return (
                self.allow_write
                and request["approval_ref"] == "approval/verified"
                and request["kind"] in {"project-context", "feature-inventory"}
            )

        self.authorize = authorize
        self.store = self.new_store()

    def new_store(self) -> GitArtifactStore:
        return GitArtifactStore(
            self.root,
            self.root,
            "qa-artifacts",
            self.authorize,
            author_name="QA",
            author_email="qa@example.invalid",
        )

    def write(
        self,
        *,
        ref: str = "docs/PROJECT_CONTEXT.md",
        content: str = "first",
        expected: str | None = None,
        operation: str = "op-1",
        kind: str = "project-context",
    ) -> dict:
        return self.store.write(
            kind=kind,
            project_ref="Sample",
            artifact_ref=ref,
            content=content,
            expected_revision=expected,
            operation_id=operation,
            source_ref="issue/1",
            source_revision="source-1",
            approval_ref="approval/verified",
            approval_revision="policy-v1",
            change_reason="approved change",
        )

    def test_new_markdown_is_in_git_tree_without_secondary_copy(self) -> None:
        first = self.write()
        self.assertEqual(first["status"], "stored", first)
        self.assertTrue(first["revision"].startswith("git:"))
        self.assertEqual(
            git(self.root, "show", "qa-artifacts:docs/PROJECT_CONTEXT.md"), "first"
        )
        self.assertFalse((self.root / "docs" / "PROJECT_CONTEXT.md").exists())
        self.assertEqual(
            self.store.read_current(
                "project-context", "Sample", "docs/PROJECT_CONTEXT.md"
            )["content"],
            "first",
        )

    def test_existing_markdown_updated_at_same_git_path(self) -> None:
        initial = context_handle(
            {
                "operation": "prepare-create",
                "project_name": "Sample",
                "enumeration_complete": True,
                "candidates": [{"ref": "docs/PROJECT_CONTEXT.md", "status": "absent"}],
            }
        )
        self.assertEqual(initial["status"], "draft")
        docs = self.root / "docs"
        docs.mkdir()
        path = docs / "PROJECT_CONTEXT.md"
        path.write_text(initial["artifact_markdown"], encoding="utf-8")
        git(self.root, "add", "docs/PROJECT_CONTEXT.md")
        git(self.root, "commit", "-qm", "existing canonical markdown")
        git(self.root, "branch", "-f", "qa-artifacts")
        before = self.store.read_current(
            "project-context", "Sample", "docs/PROJECT_CONTEXT.md"
        )
        self.assertIsNotNone(before)
        prep = {
            "operation": "prepare-sections",
            "markdown": before["content"],
            "artifact_ref": "docs/PROJECT_CONTEXT.md",
            "expected_revision": before["revision"],
            "source_ref": "source/2",
            "source_revision": "r2",
            "change_reason": "confirmed project facts",
            "section_updates": {"2": "- 製品: Sample App\n- 根拠: source/2"},
        }
        result = persist_prepared(
            self.store,
            prep,
            project_ref="Sample",
            operation_id="update-existing",
            approval_ref="approval/verified",
            approval_revision="policy-v1",
        )
        self.assertEqual(result["status"], "stored", result)
        self.assertIn(
            "- 製品: Sample App",
            git(self.root, "show", "qa-artifacts:docs/PROJECT_CONTEXT.md"),
        )
        self.assertEqual(
            self.store.read_revision(
                "project-context",
                "Sample",
                "docs/PROJECT_CONTEXT.md",
                before["revision"],
            )["content"],
            before["content"],
        )
        self.assertTrue(path.is_file())
        self.assertEqual(path.read_text(encoding="utf-8"), before["content"])
        self.assertFalse((self.root / ".qa-context-feature").exists())

    def test_retry_of_same_git_operation_is_idempotent(self) -> None:
        first = self.write()
        self.assertEqual(self.write()["status"], "idempotent")
        updated = self.write(
            content="second", expected=first["revision"], operation="op-2"
        )
        self.assertEqual(updated["status"], "stored")
        self.assertEqual(
            self.write(
                content="second",
                expected=first["revision"],
                operation="op-2",
            )["status"],
            "idempotent",
        )
        with self.assertRaisesRegex(StoreError, "revision_conflict"):
            self.write(content="changed", expected=first["revision"], operation="op-2")

    def test_native_ref_cas_detects_concurrent_edits(self) -> None:
        first = self.write()

        def update(index: int) -> str:
            store = self.new_store()
            try:
                return store.write(
                    kind="project-context",
                    project_ref="Sample",
                    artifact_ref="docs/PROJECT_CONTEXT.md",
                    content=f"change-{index}",
                    expected_revision=first["revision"],
                    operation_id=f"parallel-{index}",
                    source_ref="source/2",
                    source_revision="rev-2",
                    approval_ref="approval/verified",
                    approval_revision="policy-v1",
                    change_reason="parallel update",
                )["status"]
            except StoreError as exc:
                return str(exc)

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(update, (1, 2)))
        self.assertEqual(sorted(results), ["revision_conflict", "stored"])
        self.assertEqual(
            self.store.read_current(
                "project-context", "Sample", "docs/PROJECT_CONTEXT.md"
            )["revision"],
            "git:" + git(self.root, "rev-parse", "qa-artifacts"),
        )

    def test_untrusted_reference_transaction_hook_is_not_executed(self) -> None:
        hook = self.root / ".git" / "hooks" / "reference-transaction"
        marker = self.root / "unsafe-hook-executed"
        hook.write_text(
            "#!/bin/sh\nprintf executed > " + str(marker) + "\n",
            encoding="utf-8",
        )
        hook.chmod(0o700)
        self.assertEqual(self.write()["status"], "stored")
        self.assertFalse(marker.exists())

    def test_git_metadata_outside_authorized_root_is_rejected(self) -> None:
        worktree = self.root / "isolated-checkout"
        metadata = self.root / "external-gitdir"
        git(self.root, "init", "-q", "--separate-git-dir", str(metadata), str(worktree))
        with self.assertRaisesRegex(StoreError, "git_metadata_outside_authorized_root"):
            GitArtifactStore(
                worktree,
                worktree,
                "qa-artifacts",
                self.authorize,
                author_name="QA",
                author_email="qa@example.invalid",
            )

    def test_unknown_authorization_or_path_is_rejected(self) -> None:
        with self.assertRaisesRegex(StoreError, "artifact_ref_invalid"):
            self.write(ref="../escape.md")
        with self.assertRaisesRegex(StoreError, "artifact_ref_invalid"):
            self.write(ref=".git/config")
        with self.assertRaisesRegex(StoreError, "access_denied"):
            self.store.read_current(
                "project-context", "Other", "docs/PROJECT_CONTEXT.md"
            )
        self.allow_write = False
        with self.assertRaisesRegex(StoreError, "access_denied"):
            self.write()
        self.assertEqual(git(self.root, "rev-list", "--count", "qa-artifacts"), "1")

    def test_source_ref_and_digest_are_preserved_in_git_history(self) -> None:
        result = self.write(content="verified")
        self.assertEqual(result["sha256"], hashlib.sha256(b"verified").hexdigest())
        message = git(self.root, "log", "-1", "--format=%B", "qa-artifacts")
        self.assertIn("QA-Operation-Id: op-1", message)
        self.assertIn("QA-Approval-Ref: approval/verified", message)
        self.assertIn("QA-Source-Revision: source-1", message)

    def test_feature_inventory_uses_same_git_cas_without_schema_copy(self) -> None:
        request = fixture()
        request["snapshot"]["project_ref"] = "Sample"
        request["snapshot"]["artifact_ref"] = "qa/feature-inventory.json"
        saved = persist_snapshot(
            self.store,
            request,
            expected_revision=None,
            approval_ref="approval/verified",
            approval_revision="policy-v1",
            change_reason="first inventory",
        )
        self.assertEqual(saved["status"], "stored", saved)
        before = copy.deepcopy(request["snapshot"])
        request["previous_snapshot"] = before
        request["snapshot"]["event"] = "analysis_update"
        request["snapshot"]["event_basis"] = {
            "source_revision": "head-v1",
            "evidence_ref": "review/checked",
        }
        request["snapshot"]["operation_id"] = "op-v2"
        request["snapshot"]["artifact_revision"] = "art-v2"
        request["snapshot"]["previous_artifact_revision"] = "art-v1"
        saved2 = persist_snapshot(
            self.store,
            request,
            expected_revision=saved["revision"],
            approval_ref="approval/verified",
            approval_revision="policy-v1",
            change_reason="inventory review",
        )
        self.assertEqual(saved2["status"], "stored", saved2)


if __name__ == "__main__":
    unittest.main()
