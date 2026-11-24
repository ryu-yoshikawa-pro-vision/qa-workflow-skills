"""persist_document tests against throwaway Git repositories (kind question-analysis).

Readback behaviour follows the existing store: the branch ref is moved by update-ref
before the independent readback, so a readback mismatch returns a failure to the caller
but the unverified commit stays on the branch head. This is a constraint shared by all
kinds; the tests pin the actual behaviour.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SKILL_ROOT = Path(__file__).resolve().parents[3] / "skills"
sys.path.insert(0, str(SKILL_ROOT / "project-context" / "scripts"))
sys.path.insert(0, str(SKILL_ROOT / "question-analysis" / "scripts"))

import question_document  # noqa: E402
from artifact_store import TRUSTED_CALLBACK, USER_CONFIRMED  # noqa: E402
from git_artifact_store import GitArtifactStore  # noqa: E402
from test_question_document_validator import REVISION, VALID  # noqa: E402

BRANCH = "qa-artifacts/project-a/question-analysis"
ARTIFACT = "question-analysis/scope-1.md"
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


class QuestionDocumentStoreTests(unittest.TestCase):
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
        record = question_document.write_confirmation_record(
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
        return question_document.persist_document(
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
        self.assertEqual(git(self.root, "show", f"{BRANCH}:{ARTIFACT}"), VALID.strip())

    def test_update_from_current_head_is_stored_with_previous_revision(self) -> None:
        first = self.save(VALID, None)
        updated = edited(VALID, "通知の既定値は何か", "通知の既定値を確定する")
        second = self.save(updated, first["revision"], operation="op-2")
        self.assertEqual(second["status"], "stored", second)
        self.assertEqual(second["previous_revision"], first["revision"])

    def test_stale_expected_revision_is_a_conflict_and_head_is_unchanged(self) -> None:
        first = self.save(VALID, None)
        self.save(
            edited(VALID, "通知の既定値は何か", "通知A"),
            first["revision"],
            operation="op-2",
        )
        head = self.head()
        stale = self.save(
            edited(VALID, "通知の既定値は何か", "通知B"),
            first["revision"],
            operation="op-3",
        )
        self.assertEqual(stale["status"], "blocked", stale)
        self.assertEqual(stale["reasons"], ["revision_conflict"])
        self.assertEqual(self.head(), head)

    def test_same_operation_and_content_is_idempotent_without_new_commit(self) -> None:
        first = self.save(VALID, None)
        head = self.head()
        again = self.save(VALID, None, operation="op-1")
        self.assertEqual(again["status"], "idempotent", again)
        self.assertEqual(self.head(), head)
        self.assertEqual(first["revision"], again["revision"])

    def test_unchanged_content_is_blocked_as_unchanged_write(self) -> None:
        first = self.save(VALID, None)
        result = self.save(VALID, first["revision"], operation="op-2")
        self.assertEqual(result["status"], "blocked", result)
        self.assertEqual(result["reasons"], ["unchanged_artifact_write"])

    def test_missing_confirmation_is_access_denied(self) -> None:
        result = question_document.persist_document(
            self.store,
            {"project_ref": PROJECT, "scope_id": "scope-1", "markdown": VALID},
            artifact_ref=ARTIFACT,
            expected_revision=None,
            operation_id="op-1",
            approval_ref=APPROVAL,
            approval_revision="sha256:none",
            change_reason=REASON,
            source_ref="issue/1",
            source_revision=REVISION,
        )
        self.assertEqual(result, {"status": "blocked", "reasons": ["access_denied"]})
        self.assertEqual(
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(self.root),
                    "rev-parse",
                    "--verify",
                    "-q",
                    BRANCH + ":" + ARTIFACT,
                ],
                capture_output=True,
                check=False,
            ).returncode,
            1,
        )

    def test_confirmation_differing_in_one_field_is_access_denied(self) -> None:
        record = self.confirm(VALID, None, operation="op-1")
        result = question_document.persist_document(
            self.store,
            {"project_ref": PROJECT, "scope_id": "scope-1", "markdown": VALID},
            artifact_ref=ARTIFACT,
            expected_revision=None,
            operation_id="op-1",
            approval_ref=APPROVAL,
            approval_revision=record["approval_revision"],
            change_reason="another reason",
            source_ref="issue/1",
            source_revision=REVISION,
        )
        self.assertEqual(result, {"status": "blocked", "reasons": ["access_denied"]})

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
                edited(VALID, "通知の既定値は何か", "v2"),
                first["revision"],
                operation="op-2",
            )
        self.assertEqual(result["status"], "blocked", result)
        self.assertEqual(result["reasons"], ["independent_readback_mismatch"])
        # Actual behaviour: update-ref already moved the head; it is not restored.
        self.assertNotEqual(self.head(), head_before)

    def test_blocked_validation_writes_nothing_and_registers_nothing(self) -> None:
        broken = edited(VALID, "## 仮定候補", "## 別の見出し")
        result = question_document.persist_document(
            self.store,
            {"project_ref": PROJECT, "scope_id": "scope-1", "markdown": broken},
            artifact_ref=ARTIFACT,
            expected_revision=None,
            operation_id="op-1",
            approval_ref=APPROVAL,
            approval_revision="sha256:none",
            change_reason=REASON,
            source_ref="issue/1",
            source_revision=REVISION,
        )
        self.assertEqual(result["status"], "blocked")
        self.assertIn(
            "question_document_invalid:section_missing:仮定候補", result["reasons"]
        )
        self.assertNotIn("independent_readback_mismatch", result["reasons"])
        self.assertEqual(
            git(self.root, "branch", "--list", BRANCH).strip().count(BRANCH), 1
        )
        self.assertEqual(
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(self.root),
                    "rev-parse",
                    "--verify",
                    "-q",
                    BRANCH + ":" + ARTIFACT,
                ],
                capture_output=True,
                check=False,
            ).returncode,
            1,
        )

    def test_artifact_ref_must_match_scope(self) -> None:
        result = self.save(VALID, None, artifact_ref="question-analysis/other.md")
        self.assertEqual(
            result, {"status": "blocked", "reasons": ["question_scope_mismatch"]}
        )

    def test_other_project_on_same_branch_is_refused_as_project_mismatch(self) -> None:
        self.save(VALID, None)
        head = self.head()
        record = question_document.write_confirmation_record(
            project_ref="project-b",
            artifact_ref=ARTIFACT,
            expected_revision=None,
            approval_ref=APPROVAL,
            markdown=edited(VALID, "通知の既定値は何か", "別案件"),
            source_ref="issue/1",
            source_revision=REVISION,
            operation_id="op-9",
            change_reason=REASON,
        )
        self.store.record_user_confirmation(record)
        result = question_document.persist_document(
            self.store,
            {
                "project_ref": "project-b",
                "scope_id": "scope-1",
                "markdown": edited(VALID, "通知の既定値は何か", "別案件"),
            },
            artifact_ref=ARTIFACT,
            expected_revision=None,
            operation_id="op-9",
            approval_ref=APPROVAL,
            approval_revision=record["approval_revision"],
            change_reason=REASON,
            source_ref="issue/1",
            source_revision=REVISION,
        )
        self.assertEqual(result["status"], "blocked", result)
        self.assertEqual(self.head(), head)

    def test_trusted_callback_mode_uses_the_same_persist_path(self) -> None:
        requests: list[dict] = []

        def allow(request: dict) -> bool:
            requests.append(request)
            return request["kind"] == question_document.KIND

        store = self.new_store(authorize=allow, approval_source=TRUSTED_CALLBACK)
        record = question_document.write_confirmation_record(
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
        result = question_document.persist_document(
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
                r["operation"] == "write" and r["kind"] == "question-analysis"
                for r in requests
            )
        )

        denied = self.new_store(
            authorize=lambda request: False, approval_source=TRUSTED_CALLBACK
        )
        blocked = question_document.persist_document(
            denied,
            {
                "project_ref": PROJECT,
                "scope_id": "scope-1",
                "markdown": edited(VALID, "通知の既定値は何か", "x"),
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
