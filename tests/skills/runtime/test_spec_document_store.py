"""persist_document tests against throwaway Git repositories (kind spec-analysis).

Readback behaviour follows the existing store: the branch ref is moved by update-ref
before the independent readback, so a readback mismatch returns a failure to the caller
but the unverified commit stays on the branch head. This is a constraint shared by all
kinds; the tests pin the actual behaviour.
"""

from __future__ import annotations

import hashlib
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SKILL_ROOT = Path(__file__).resolve().parents[3] / "skills"
sys.path.insert(0, str(SKILL_ROOT / "project-context" / "scripts"))
sys.path.insert(0, str(SKILL_ROOT / "spec-analysis" / "scripts"))

import spec_document  # noqa: E402
from artifact_store import TRUSTED_CALLBACK, USER_CONFIRMED  # noqa: E402
from git_artifact_store import GitArtifactStore, branch_checked_out  # noqa: E402
from test_spec_document_validator import REVISION, VALID  # noqa: E402

BRANCH = "qa-artifacts/project-a/spec-analysis"
ARTIFACT = "spec-analysis/scope-1.md"
PROJECT = "project-a"
APPROVAL = "approval/verified"
REASON = "approved change"


def git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def edited(text: str, old: str, new: str) -> str:
    assert text.count(old) == 1, old
    return text.replace(old, new, 1)


class SpecDocumentStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        git(self.root, "init", "-q", "-b", "main")
        git(self.root, "config", "user.email", "qa@example.invalid")
        git(self.root, "config", "user.name", "QA")
        (self.root / "README.md").write_text("baseline\n", encoding="utf-8")
        git(self.root, "add", ".")
        git(self.root, "commit", "-qm", "baseline")
        git(self.root, "branch", BRANCH)
        self.store = self.new_store()

    def new_store(self, **kwargs: object) -> GitArtifactStore:
        return GitArtifactStore(
            self.root,
            self.root,
            BRANCH,
            kwargs.pop("authorize", None),
            author_name="QA",
            author_email="qa@example.invalid",
            approval_source=kwargs.pop("approval_source", USER_CONFIRMED),
            **kwargs,
        )

    def head(self) -> str:
        return git(self.root, "rev-parse", BRANCH)

    def confirm(
        self,
        markdown: str,
        expected: str | None,
        *,
        operation: str = "op-1",
        reason: str = REASON,
        store: GitArtifactStore | None = None,
    ) -> dict:
        record = spec_document.write_confirmation_record(
            project_ref=PROJECT,
            artifact_ref=ARTIFACT,
            expected_revision=expected,
            approval_ref=APPROVAL,
            markdown=markdown,
            source_ref="issue/1",
            source_revision=REVISION,
            operation_id=operation,
            change_reason=reason,
        )
        (store or self.store).record_user_confirmation(record)
        return record

    def save(
        self,
        markdown: str,
        expected: str | None,
        *,
        operation: str = "op-1",
        reason: str = REASON,
        scope_id: str = "scope-1",
        artifact_ref: str = ARTIFACT,
        store: GitArtifactStore | None = None,
    ) -> dict:
        record = self.confirm(
            markdown, expected, operation=operation, reason=reason, store=store
        )
        return spec_document.persist_document(
            store or self.store,
            {"project_ref": PROJECT, "scope_id": scope_id, "markdown": markdown},
            artifact_ref=artifact_ref,
            expected_revision=expected,
            operation_id=operation,
            approval_ref=APPROVAL,
            approval_revision=record["approval_revision"],
            change_reason=reason,
            source_ref="issue/1",
            source_revision=REVISION,
        )

    def test_create_stores_and_reads_back_the_same_content(self) -> None:
        result = self.save(VALID, None)
        self.assertEqual(result["status"], "stored", result)
        self.assertEqual(result["analysis_status"], "valid")
        current = self.store.read_current(spec_document.KIND, PROJECT, ARTIFACT)
        self.assertEqual(current["content"], VALID)
        self.assertEqual(result["document_sha256"], current["sha256"])

    def test_update_from_current_head_is_stored_with_previous_revision(self) -> None:
        first = self.save(VALID, None)
        updated = edited(VALID, "item one", "item one revised")
        second = self.save(updated, first["revision"], operation="op-2")
        self.assertEqual(second["status"], "stored", second)
        self.assertEqual(second["previous_revision"], first["revision"])
        self.assertEqual(
            self.store.read_current(spec_document.KIND, PROJECT, ARTIFACT)["content"],
            updated,
        )

    def test_stale_expected_revision_is_a_conflict_and_head_is_unchanged(self) -> None:
        first = self.save(VALID, None)
        self.save(edited(VALID, "item one", "v2"), first["revision"], operation="op-2")
        head = self.head()
        stale = self.save(
            edited(VALID, "item one", "v3"), first["revision"], operation="op-3"
        )
        self.assertEqual(stale["status"], "blocked")
        self.assertEqual(stale["reasons"], ["revision_conflict"])
        self.assertEqual(self.head(), head)

    def test_same_operation_and_content_is_idempotent_without_new_commit(self) -> None:
        self.save(VALID, None)
        head = self.head()
        again = self.save(VALID, None)
        self.assertEqual(again["status"], "idempotent", again)
        self.assertEqual(self.head(), head)

    def test_same_operation_with_different_content_is_stored_as_a_new_version(
        self,
    ) -> None:
        # Pinned current behaviour (not an intended contract): the store does not reject a
        # reused operation id when the content differs under the current head.
        first = self.save(VALID, None, operation="op-1")
        second = self.save(
            edited(VALID, "item one", "changed"), first["revision"], operation="op-1"
        )
        self.assertEqual(second["status"], "stored", second)
        self.assertEqual(
            git(self.root, "log", "-2", "--format=%B", BRANCH).count(
                "QA-Operation-Id: op-1"
            ),
            2,
        )

    def test_missing_confirmation_is_access_denied(self) -> None:
        head = self.head()
        result = spec_document.persist_document(
            self.store,
            {"project_ref": PROJECT, "scope_id": "scope-1", "markdown": VALID},
            artifact_ref=ARTIFACT,
            expected_revision=None,
            operation_id="op-1",
            approval_ref=APPROVAL,
            approval_revision="sha256:" + "0" * 64,
            change_reason=REASON,
            source_ref="issue/1",
            source_revision=REVISION,
        )
        self.assertEqual(result, {"status": "blocked", "reasons": ["access_denied"]})
        self.assertEqual(self.head(), head)

    def test_confirmation_differing_in_one_field_is_access_denied(self) -> None:
        self.confirm(VALID, None, reason="another reason")
        result = spec_document.persist_document(
            self.store,
            {"project_ref": PROJECT, "scope_id": "scope-1", "markdown": VALID},
            artifact_ref=ARTIFACT,
            expected_revision=None,
            operation_id="op-1",
            approval_ref=APPROVAL,
            approval_revision="sha256:"
            + hashlib.sha256(VALID.encode("utf-8")).hexdigest(),
            change_reason=REASON,
            source_ref="issue/1",
            source_revision=REVISION,
        )
        self.assertEqual(result["reasons"], ["access_denied"])

    def test_readback_mismatch_is_a_failure_and_the_unverified_commit_stays_on_head(
        self,
    ) -> None:
        first = self.save(VALID, None)
        head_before = self.head()
        tampered = {
            "content": "tampered",
            "sha256": "0" * 64,
            "revision": "git:" + head_before,
            "previous_revision": None,
        }
        with mock.patch.object(self.store, "read_revision", return_value=tampered):
            result = self.save(
                edited(VALID, "item one", "v2"), first["revision"], operation="op-2"
            )
        self.assertEqual(result["status"], "blocked", result)
        self.assertEqual(result["reasons"], ["independent_readback_mismatch"])
        # Actual behaviour: update-ref already moved the head; it is not restored.
        self.assertNotEqual(self.head(), head_before)
        self.assertEqual(
            git(self.root, "show", f"{BRANCH}:{ARTIFACT}"),
            edited(VALID, "item one", "v2").strip(),
        )

    def test_unchanged_content_is_blocked_as_unchanged_write(self) -> None:
        first = self.save(VALID, None)
        result = self.save(VALID, first["revision"], operation="op-2")
        self.assertEqual(
            result, {"status": "blocked", "reasons": ["unchanged_artifact_write"]}
        )

    def test_blocked_validation_writes_nothing_and_registers_nothing(self) -> None:
        head = self.head()
        broken = VALID.replace("## 後続Skillへの補足", "## 後続")
        with mock.patch.object(self.store, "write") as write:
            result = spec_document.persist_document(
                self.store,
                {"project_ref": PROJECT, "scope_id": "scope-1", "markdown": broken},
                artifact_ref=ARTIFACT,
                expected_revision=None,
                operation_id="op-1",
                approval_ref=APPROVAL,
                approval_revision="sha256:x",
                change_reason=REASON,
                source_ref="issue/1",
                source_revision=REVISION,
            )
        write.assert_not_called()
        self.assertEqual(result["status"], "blocked")
        self.assertIn(
            "spec_document_invalid:section_missing:後続Skillへの補足", result["reasons"]
        )
        self.assertEqual(self.head(), head)

    def test_artifact_ref_must_match_scope(self) -> None:
        for ref in ("../x.md", "spec-analysis/other.md", "spec-analysis/scope-1.txt"):
            with self.subTest(ref=ref), mock.patch.object(self.store, "write") as write:
                result = self.save(VALID, None, artifact_ref=ref)
                write.assert_not_called()
                self.assertEqual(
                    result, {"status": "blocked", "reasons": ["spec_scope_mismatch"]}
                )

    def test_other_project_on_same_branch_is_refused_as_project_mismatch(self) -> None:
        self.save(VALID, None)
        record = spec_document.write_confirmation_record(
            project_ref="project-b",
            artifact_ref=ARTIFACT,
            expected_revision=None,
            approval_ref=APPROVAL,
            markdown=VALID,
            source_ref="issue/1",
            source_revision=REVISION,
            operation_id="op-b",
            change_reason=REASON,
        )
        self.store.record_user_confirmation(record)  # project-b is registered for reads
        with self.assertRaisesRegex(Exception, "artifact_project_mismatch"):
            self.store.read_current(spec_document.KIND, "project-b", ARTIFACT)

    def test_branch_checked_out_is_refused_at_construction(self) -> None:
        with self.assertRaisesRegex(Exception, "branch_checked_out"):
            subprocess.run(
                ["git", "-C", str(self.root), "checkout", "-q", BRANCH],
                check=True,
                capture_output=True,
            )
            self.new_store()
        subprocess.run(
            ["git", "-C", str(self.root), "checkout", "-q", "main"],
            check=True,
            capture_output=True,
        )
        self.assertFalse(branch_checked_out(self.root, "refs/heads/" + BRANCH))

    def test_trusted_callback_mode_uses_the_same_persist_path(self) -> None:
        requests: list[dict] = []

        def allow(request: dict) -> bool:
            requests.append(request)
            return request["kind"] == spec_document.KIND

        store = self.new_store(authorize=allow, approval_source=TRUSTED_CALLBACK)
        record = spec_document.write_confirmation_record(
            project_ref=PROJECT,
            artifact_ref=ARTIFACT,
            expected_revision=None,
            approval_ref=APPROVAL,
            markdown=VALID,
            source_ref="issue/1",
            source_revision=REVISION,
            operation_id="op-1",
            change_reason=REASON,
        )
        result = spec_document.persist_document(
            store,
            {"project_ref": PROJECT, "scope_id": "scope-1", "markdown": VALID},
            artifact_ref=ARTIFACT,
            expected_revision=None,
            operation_id="op-1",
            approval_ref=APPROVAL,
            approval_revision=record["approval_revision"],
            change_reason=REASON,
            source_ref="issue/1",
            source_revision=REVISION,
        )
        self.assertEqual(result["status"], "stored", result)
        self.assertTrue(
            any(
                r["operation"] == "write" and r["kind"] == "spec-analysis"
                for r in requests
            )
        )

        denied = self.new_store(
            authorize=lambda request: False, approval_source=TRUSTED_CALLBACK
        )
        blocked = spec_document.persist_document(
            denied,
            {
                "project_ref": PROJECT,
                "scope_id": "scope-1",
                "markdown": edited(VALID, "item one", "x"),
            },
            artifact_ref=ARTIFACT,
            expected_revision=result["revision"],
            operation_id="op-2",
            approval_ref=APPROVAL,
            approval_revision="sha256:y",
            change_reason=REASON,
            source_ref="issue/1",
            source_revision=REVISION,
        )
        self.assertEqual(blocked, {"status": "blocked", "reasons": ["access_denied"]})


if __name__ == "__main__":
    unittest.main()
