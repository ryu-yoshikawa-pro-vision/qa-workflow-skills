"""Host CLI tests for the user-confirmed Git artifact store.

All repositories are throwaway repositories under a temporary directory. The
qa-workspace parent repository is never touched.
"""

from __future__ import annotations

import contextlib
import copy
import hashlib
import io
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SKILL_ROOT = Path(__file__).resolve().parents[3] / "skills"
SCRIPTS = SKILL_ROOT / "project-context" / "scripts"
HOST = SCRIPTS / "artifact_host.py"
PROJECT_CONTEXT_CLI = SCRIPTS / "project_context.py"
sys.path.insert(0, str(SCRIPTS))

import artifact_host  # noqa: E402

EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
BRANCH = "qa-artifacts/Sample/project-context"
ARTIFACT = "docs/PROJECT_CONTEXT.md"
CONFIRMATION = "user confirmed 2026-11-19"


def git(repo: Path, *args: str, check: bool = True) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if check and result.returncode != 0:
        raise AssertionError(result.stderr)
    return result.stdout.strip()


def run_host(*args: str) -> tuple[int, dict]:
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    completed = subprocess.run(
        [sys.executable, str(HOST), *args],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    lines = [line for line in completed.stdout.splitlines() if line.strip()]
    payload = json.loads(lines[-1]) if lines else {}
    return completed.returncode, payload


def run_context(request: dict) -> dict:
    """The JSON CLI of project_context.py (prepare-* only; it never saves)."""
    completed = subprocess.run(
        [sys.executable, str(PROJECT_CONTEXT_CLI)],
        input=json.dumps(request, ensure_ascii=False).encode("utf-8"),
        capture_output=True,
        check=False,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )
    return json.loads(completed.stdout.decode("utf-8"))


class ArtifactHostTests(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name)
        self.repo = self.base / "repo"
        self.repo.mkdir()
        git(self.repo, "init", "-q", "-b", "main")
        git(self.repo, "config", "user.email", "qa@example.invalid")
        git(self.repo, "config", "user.name", "QA")
        (self.repo / "README.md").write_text("original\n", encoding="utf-8")
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-qm", "baseline")

    def common(self) -> list[str]:
        return [
            "--repo",
            str(self.repo),
            "--branch",
            BRANCH,
            "--project-ref",
            "Sample",
            "--kind",
            "project-context",
            "--artifact-ref",
            ARTIFACT,
        ]

    def init(self) -> None:
        code, payload = run_host(
            "init-branch", "--repo", str(self.repo), "--branch", BRANCH
        )
        self.assertEqual((code, payload["status"]), (0, "created"), payload)

    def create_request(self, **overrides: object) -> dict:
        request: dict = {
            "operation": "prepare-create",
            "project_name": "Sample",
            "enumeration_complete": True,
            "candidates": [{"ref": ARTIFACT, "status": "absent"}],
            "artifact_ref": ARTIFACT,
            "source_ref": "source/1",
            "source_revision": "r1",
            "change_reason": "initial",
        }
        request.update(overrides)
        return request

    def update_request(
        self,
        markdown: str,
        expected: str,
        product: str,
        *,
        source_revision: str = "r2",
    ) -> dict:
        return {
            "operation": "prepare-sections",
            "markdown": markdown,
            "artifact_ref": ARTIFACT,
            "expected_revision": expected,
            "source_ref": "source/2",
            "source_revision": source_revision,
            "change_reason": "confirmed product name",
            "section_updates": {"2": "- 製品: " + product},
        }

    def save_prepared(
        self,
        request: dict | None,
        *,
        operation: str | None = "op-1",
        confirmation: str | None = CONFIRMATION,
        project: str = "Sample",
        artifact: str = ARTIFACT,
        kind: str = "project-context",
        raw: bytes | None = None,
    ) -> tuple[int, dict]:
        path = self.base / "prepared.json"
        if raw is not None:
            path.write_bytes(raw)
        else:
            path.write_text(json.dumps(request, ensure_ascii=False), encoding="utf-8")
        args = [
            "save-prepared",
            "--repo",
            str(self.repo),
            "--branch",
            BRANCH,
            "--project-ref",
            project,
            "--kind",
            kind,
            "--artifact-ref",
            artifact,
            "--prepared-file",
            str(path),
        ]
        if operation is not None:
            args += ["--operation-id", operation]
        if confirmation is not None:
            args += ["--user-confirmed-ref", confirmation]
        return run_host(*args)

    def create(self, operation: str = "op-1") -> dict:
        code, payload = self.save_prepared(self.create_request(), operation=operation)
        self.assertEqual((code, payload["status"]), (0, "stored"), payload)
        return payload

    def read(
        self, *extra: str, confirmation: str = "user confirmed read"
    ) -> tuple[int, dict]:
        return run_host(
            "read", *self.common(), "--user-confirmed-ref", confirmation, *extra
        )

    def head(self) -> str:
        return git(self.repo, "rev-parse", "refs/heads/" + BRANCH)

    def current_content(self) -> tuple[str, str]:
        code, current = self.read()
        self.assertEqual(code, 0, current)
        return current["content"], current["revision"]

    def test_init_branch_creates_empty_root_commit_and_reports_existing(self) -> None:
        self.init()
        self.assertEqual(git(self.repo, "rev-parse", BRANCH + "^{tree}"), EMPTY_TREE)
        self.assertEqual(
            git(self.repo, "log", "-1", "--format=%s", BRANCH), "qa artifact: init"
        )
        self.assertEqual(git(self.repo, "rev-list", "--count", BRANCH), "1")
        code, payload = run_host(
            "init-branch", "--repo", str(self.repo), "--branch", BRANCH
        )
        self.assertEqual((code, payload["status"]), (0, "exists"))

    def test_init_branch_refuses_unborn_branch_that_is_checked_out(self) -> None:
        git(self.repo, "checkout", "-q", "--orphan", BRANCH)
        code, payload = run_host(
            "init-branch", "--repo", str(self.repo), "--branch", BRANCH
        )
        self.assertEqual((code, payload["reason"]), (1, "branch_checked_out"))
        missing = subprocess.run(
            [
                "git",
                "-C",
                str(self.repo),
                "show-ref",
                "--verify",
                "--quiet",
                "refs/heads/" + BRANCH,
            ],
            check=False,
        )
        self.assertNotEqual(missing.returncode, 0)

    def test_init_branch_rejects_invalid_branch_name(self) -> None:
        for name in ["../escape", "-x", "bad branch", "a..b/..c"]:
            with self.subTest(name=name):
                code, payload = run_host(
                    "init-branch", "--repo", str(self.repo), "--branch", name
                )
                self.assertEqual((code, payload["status"]), (1, "blocked"))

    def test_init_branch_does_not_run_source_repository_hooks(self) -> None:
        marker = self.base / "hook-ran"
        hook = self.repo / ".git" / "hooks" / "reference-transaction"
        hook.write_text(
            "#!/bin/sh\ntouch '" + str(marker) + "'\nexit 0\n", encoding="utf-8"
        )
        os.chmod(hook, 0o755)
        code, payload = run_host(
            "init-branch", "--repo", str(self.repo), "--branch", BRANCH
        )
        self.assertEqual((code, payload["status"]), (0, "created"), payload)
        self.assertFalse(marker.exists())

    def test_init_branch_rejects_author_with_line_break_or_control_character(
        self,
    ) -> None:
        cases = [
            ("QA\nSigned-off-by: x", "qa@example.invalid", "author_name_invalid"),
            ("QA\x07", "qa@example.invalid", "author_name_invalid"),
            ("QA", "qa@example.invalid\n", "author_email_invalid"),
            ("QA", "no-at-sign", "author_email_invalid"),
        ]
        for name, email, reason in cases:
            with self.subTest(name=repr(name), email=repr(email)):
                code, payload = run_host(
                    "init-branch",
                    "--repo",
                    str(self.repo),
                    "--branch",
                    BRANCH,
                    "--author-name",
                    name,
                    "--author-email",
                    email,
                )
                self.assertEqual(
                    (code, payload), (1, {"status": "blocked", "reason": reason})
                )
        self.assertNotEqual(
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(self.repo),
                    "show-ref",
                    "--verify",
                    "--quiet",
                    "refs/heads/" + BRANCH,
                ],
                check=False,
            ).returncode,
            0,
        )

    def test_save_prepared_stores_with_confirmation_and_records_trailer(self) -> None:
        self.init()
        saved = self.create()
        message = git(self.repo, "log", "-1", "--format=%B", BRANCH)
        self.assertIn("QA-Approval-Source: user-confirmed", message.splitlines())
        self.assertIn("QA-Approval-Ref: " + CONFIRMATION, message.splitlines())
        self.assertEqual(saved["revision"], "git:" + self.head())

    def test_prepared_file_from_project_context_cli_is_saved(self) -> None:
        self.init()
        request = self.create_request()
        prepared = run_context(request)
        self.assertEqual(prepared["status"], "draft", prepared)
        self.assertIn("# 案件コンテキスト", prepared["artifact_markdown"])
        code, payload = self.save_prepared(request)
        self.assertEqual((code, payload["status"]), (0, "stored"), payload)
        content, revision = self.current_content()
        self.assertEqual(content, prepared["artifact_markdown"])
        self.assertEqual(revision, payload["revision"])

    def test_save_prepared_without_or_with_invalid_confirmation_is_rejected(
        self,
    ) -> None:
        self.init()
        before = self.head()
        cases = [
            ("", "user_confirmed_ref_required"),
            ("   ", "user_confirmed_ref_required"),
            ("line one\nline two", "user_confirmed_ref_invalid"),
            ("a b", "user_confirmed_ref_invalid"),
            ("x" * 1025, "user_confirmed_ref_invalid"),
            ("tab\tinside", "user_confirmed_ref_invalid"),
        ]
        for value, reason in cases:
            with self.subTest(value=repr(value)):
                code, payload = self.save_prepared(
                    self.create_request(), confirmation=value
                )
                self.assertEqual(
                    (code, payload), (1, {"status": "blocked", "reason": reason})
                )
        code, payload = self.save_prepared(self.create_request(), confirmation=None)
        self.assertEqual((code, payload["reason"]), (1, "arguments_invalid"))
        self.assertEqual(self.head(), before)

    def test_confirmation_reference_of_1024_characters_is_accepted(self) -> None:
        self.init()
        code, payload = self.save_prepared(
            self.create_request(), confirmation="x" * 1024
        )
        self.assertEqual((code, payload["status"]), (0, "stored"), payload)

    def test_save_prepared_rejects_branch_checked_out_in_main_worktree(self) -> None:
        self.init()
        git(self.repo, "switch", "-q", BRANCH)
        code, payload = self.save_prepared(self.create_request())
        self.assertEqual((code, payload["reason"]), (1, "branch_checked_out"))

    def test_save_prepared_with_detached_head_writes_branch_not_checked_out(
        self,
    ) -> None:
        self.init()
        git(self.repo, "checkout", "-q", "--detach")
        code, payload = self.save_prepared(self.create_request())
        self.assertEqual((code, payload["status"]), (0, "stored"), payload)
        self.assertEqual(git(self.repo, "symbolic-ref", "-q", "HEAD", check=False), "")

    def test_save_prepared_works_in_repository_path_with_spaces(self) -> None:
        self.repo = self.base / "my repo with spaces"
        self.repo.mkdir()
        git(self.repo, "init", "-q", "-b", "main")
        git(self.repo, "config", "user.email", "qa@example.invalid")
        git(self.repo, "config", "user.name", "QA")
        (self.repo / "README.md").write_text("x\n", encoding="utf-8")
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-qm", "baseline")
        self.init()
        code, payload = self.save_prepared(self.create_request())
        self.assertEqual((code, payload["status"]), (0, "stored"), payload)

    def test_same_operation_resend_is_idempotent(self) -> None:
        self.init()
        first = self.create("op-1")
        code, again = self.save_prepared(self.create_request(), operation="op-1")
        self.assertEqual((code, again["status"]), (0, "idempotent"), again)
        self.assertEqual(again["revision"], first["revision"])
        self.assertEqual(git(self.repo, "rev-list", "--count", BRANCH), "2")

        content, _ = self.current_content()
        second_request = self.update_request(content, first["revision"], "Sample App")
        code, second = self.save_prepared(second_request, operation="op-2")
        self.assertEqual((code, second["status"]), (0, "stored"), second)
        code, resent = self.save_prepared(second_request, operation="op-2")
        self.assertEqual((code, resent["status"]), (0, "idempotent"), resent)
        self.assertEqual(resent["revision"], second["revision"])
        self.assertEqual(git(self.repo, "rev-list", "--count", BRANCH), "3")

    def test_stale_expected_revision_is_a_revision_conflict(self) -> None:
        self.init()
        first = self.create("op-1")
        first_content, _ = self.current_content()
        code, second = self.save_prepared(
            self.update_request(first_content, first["revision"], "Sample App"),
            operation="op-2",
        )
        self.assertEqual((code, second["status"]), (0, "stored"), second)
        code, payload = self.save_prepared(
            self.update_request(first_content, first["revision"], "Other App"),
            operation="op-3",
        )
        self.assertEqual((code, payload["reason"]), (1, "revision_conflict"), payload)
        self.assertEqual(self.head(), second["revision"][4:])

    def test_save_readback_returns_exact_content_and_hash(self) -> None:
        self.init()
        saved = self.create()
        code, current = self.read()
        self.assertEqual(code, 0, current)
        self.assertIn("- プロジェクト: Sample", current["content"])
        self.assertEqual(
            current["sha256"],
            hashlib.sha256(current["content"].encode("utf-8")).hexdigest(),
        )
        self.assertEqual(current["revision"], saved["revision"])

    def test_read_current_and_history_revisions(self) -> None:
        self.init()
        first = self.create("op-1")
        first_content, _ = self.current_content()
        second = self.save_prepared(
            self.update_request(first_content, first["revision"], "Sample App"),
            operation="op-2",
        )[1]
        code, current = self.read()
        self.assertEqual((code, current["revision"]), (0, second["revision"]))
        self.assertIn("- 製品: Sample App", current["content"])
        code, old = self.read("--revision", first["revision"])
        self.assertEqual(
            (code, old["content"], old["revision"]),
            (0, first_content, first["revision"]),
        )
        # init -> v1 -> v2 の順。init（成果物を含まないroot commit）は履歴から読めない。
        init_revision = "git:" + git(self.repo, "rev-parse", BRANCH + "~2")
        code, absent = self.read("--revision", init_revision)
        self.assertEqual((code, absent["status"]), (1, "absent"))

    def test_export_is_byte_exact_read_only_and_atomic_into_existing_directory(
        self,
    ) -> None:
        self.init()
        self.create()
        content, _ = self.current_content()
        out = self.repo / "projections" / "PROJECT_CONTEXT.md"
        out.parent.mkdir()
        code, payload = run_host(
            "export", *self.common(), "--out", str(out), "--user-confirmed-ref", "read"
        )
        self.assertEqual((code, payload["status"]), (0, "exported"), payload)
        self.assertEqual(out.read_bytes(), content.encode("utf-8"))
        self.assertEqual(
            payload["sha256"], hashlib.sha256(content.encode("utf-8")).hexdigest()
        )
        self.assertEqual(stat.S_IMODE(out.stat().st_mode), 0o444)

    def test_export_refuses_missing_parent_directory(self) -> None:
        self.init()
        self.create()
        out = self.base / "missing" / "PROJECT_CONTEXT.md"
        code, payload = run_host(
            "export", *self.common(), "--out", str(out), "--user-confirmed-ref", "read"
        )
        self.assertEqual((code, payload["reason"]), (1, "out_parent_missing"))
        self.assertFalse(out.parent.exists())

    def test_export_refuses_hand_edited_projection_without_force(self) -> None:
        self.init()
        self.create()
        out = self.repo / "PROJECT_CONTEXT.md"
        run_host(
            "export", *self.common(), "--out", str(out), "--user-confirmed-ref", "read"
        )
        os.chmod(out, 0o644)
        edited = out.read_bytes() + b"hand edit\n"
        out.write_bytes(edited)
        code, payload = run_host(
            "export", *self.common(), "--out", str(out), "--user-confirmed-ref", "read"
        )
        self.assertEqual(
            (code, payload), (1, {"status": "blocked", "reason": "projection_drifted"})
        )
        self.assertEqual(out.read_bytes(), edited)

    def test_export_force_overwrites_drifted_projection_and_reports_it(self) -> None:
        self.init()
        self.create()
        content, _ = self.current_content()
        out = self.repo / "PROJECT_CONTEXT.md"
        run_host(
            "export", *self.common(), "--out", str(out), "--user-confirmed-ref", "read"
        )
        os.chmod(out, 0o644)
        out.write_text("hand edit\n", encoding="utf-8")
        code, payload = run_host(
            "export",
            *self.common(),
            "--out",
            str(out),
            "--user-confirmed-ref",
            "read",
            "--force",
        )
        self.assertEqual((code, payload["status"]), (0, "exported"), payload)
        self.assertIs(payload.get("overwrote_drifted"), True)
        self.assertEqual(out.read_bytes(), content.encode("utf-8"))

    def test_export_over_matching_projection_succeeds_without_force(self) -> None:
        self.init()
        self.create()
        out = self.repo / "PROJECT_CONTEXT.md"
        run_host(
            "export", *self.common(), "--out", str(out), "--user-confirmed-ref", "read"
        )
        code, payload = run_host(
            "export", *self.common(), "--out", str(out), "--user-confirmed-ref", "read"
        )
        self.assertEqual((code, payload["status"]), (0, "exported"), payload)
        self.assertNotIn("overwrote_drifted", payload)

    def test_failed_export_never_leaves_a_broken_projection(self) -> None:
        out = self.base / "projection.md"
        out.write_bytes(b"previous complete copy\n")
        with mock.patch.object(
            artifact_host.os, "fsync", side_effect=OSError("disk full")
        ):
            with self.assertRaises(OSError):
                artifact_host.atomic_write(
                    out, b"new content that must not be partial\n"
                )
        self.assertEqual(out.read_bytes(), b"previous complete copy\n")
        self.assertEqual(
            sorted(p.name for p in self.base.iterdir()), ["projection.md", "repo"]
        )

    def test_failed_rename_removes_temporary_file_and_keeps_target(self) -> None:
        out = self.base / "projection.md"
        out.write_bytes(b"previous\n")
        with mock.patch.object(
            artifact_host.os, "replace", side_effect=OSError("rename failed")
        ):
            with self.assertRaises(OSError):
                artifact_host.atomic_write(out, b"next\n")
        self.assertEqual(out.read_bytes(), b"previous\n")
        self.assertEqual(
            [
                p.name
                for p in self.base.iterdir()
                if p.name.startswith(".projection.md.")
            ],
            [],
        )

    def test_verify_projection_reports_in_sync_then_drifted(self) -> None:
        self.init()
        self.create()
        out = self.repo / "PROJECT_CONTEXT.md"
        run_host(
            "export", *self.common(), "--out", str(out), "--user-confirmed-ref", "read"
        )
        code, payload = run_host(
            "verify-projection",
            *self.common(),
            "--out",
            str(out),
            "--user-confirmed-ref",
            "read",
        )
        self.assertEqual((code, payload["status"]), (0, "in_sync"), payload)
        os.chmod(out, 0o644)
        out.write_text("hand edit\n", encoding="utf-8")
        code, payload = run_host(
            "verify-projection",
            *self.common(),
            "--out",
            str(out),
            "--user-confirmed-ref",
            "read",
        )
        self.assertEqual((code, payload["status"]), (0, "drifted"), payload)
        self.assertNotEqual(payload["file_sha256"], payload["store_sha256"])

    def test_read_export_and_verify_require_a_confirmation_reference(self) -> None:
        self.init()
        self.create()
        out = self.repo / "PROJECT_CONTEXT.md"
        for command in ["read", "export", "verify-projection"]:
            with self.subTest(command=command):
                extra = ["--out", str(out)] if command != "read" else []
                code, payload = run_host(command, *self.common(), *extra)
                self.assertEqual((code, payload["status"]), (1, "blocked"))
                self.assertEqual(payload["reason"], "arguments_invalid")
        self.assertFalse(out.exists())

    def test_save_command_is_removed_in_favor_of_save_prepared(self) -> None:
        self.init()
        before = self.head()
        code, payload = run_host(
            "save",
            *self.common(),
            "--content-file",
            str(self.repo / "README.md"),
            "--expected-revision",
            "none",
            "--operation-id",
            "op-1",
            "--source-ref",
            "s",
            "--source-revision",
            "r",
            "--change-reason",
            "c",
            "--user-confirmed-ref",
            CONFIRMATION,
        )
        self.assertEqual(
            (code, payload), (1, {"status": "blocked", "reason": "arguments_invalid"})
        )
        self.assertEqual(self.head(), before)

    def test_save_prepared_rejects_content_that_is_not_a_16_section_context(
        self,
    ) -> None:
        self.init()
        before = self.head()
        request = {
            "operation": "prepare-sections",
            "markdown": "# PC\nbody\n",
            "artifact_ref": ARTIFACT,
            "expected_revision": "git:" + before,
            "source_ref": "s",
            "source_revision": "r",
            "change_reason": "c",
            "section_updates": {"2": "- 製品: X"},
        }
        code, payload = self.save_prepared(request, operation="op-1")
        self.assertEqual(
            (code, payload),
            (
                1,
                {"status": "blocked", "reason": "project_context_16_sections_required"},
            ),
        )
        self.assertEqual(self.head(), before)

    def test_save_prepared_rejects_non_json_prepared_file(self) -> None:
        self.init()
        before = self.head()
        code, payload = self.save_prepared(None, raw=b"{not json")
        self.assertEqual((code, payload["reason"]), (1, "prepared_file_invalid"))
        self.assertEqual(self.head(), before)

    def test_save_prepared_rejects_feature_inventory_for_now(self) -> None:
        self.init()
        before = self.head()
        code, payload = self.save_prepared(
            self.create_request(), kind="feature-inventory"
        )
        self.assertEqual((code, payload["reason"]), (1, "unsupported_kind_for_now"))
        self.assertEqual(self.head(), before)

    def test_save_prepared_rejects_project_that_does_not_match_the_document(
        self,
    ) -> None:
        self.init()
        before = self.head()
        code, payload = self.save_prepared(self.create_request(), project="Other")
        self.assertEqual((code, payload["reason"]), (1, "project_scope_mismatch"))
        self.assertEqual(self.head(), before)

    def test_save_prepared_rejects_artifact_ref_that_differs_from_the_request(
        self,
    ) -> None:
        self.init()
        before = self.head()
        code, payload = self.save_prepared(
            self.create_request(), artifact="docs/OTHER.md"
        )
        self.assertEqual((code, payload["reason"]), (1, "artifact_ref_mismatch"))
        self.assertEqual(self.head(), before)

    def test_save_prepared_rejects_update_whose_previous_text_is_not_stored(
        self,
    ) -> None:
        self.init()
        first = self.create("op-1")
        alternative = run_context(
            self.create_request(section_updates={"2": "- 製品: Other"})
        )["artifact_markdown"]
        before = self.head()
        code, payload = self.save_prepared(
            self.update_request(alternative, first["revision"], "Sample App"),
            operation="op-2",
        )
        self.assertEqual((code, payload["reason"]), (1, "previous_document_mismatch"))
        self.assertEqual(self.head(), before)

    def test_save_leaves_head_index_and_worktree_unchanged(self) -> None:
        (self.repo / "staged.txt").write_text("staged\n", encoding="utf-8")
        git(self.repo, "add", "staged.txt")
        (self.repo / "README.md").write_text("edited but unstaged\n", encoding="utf-8")
        (self.repo / "untracked.txt").write_text("untracked\n", encoding="utf-8")
        snapshot = (
            git(self.repo, "rev-parse", "HEAD"),
            git(self.repo, "symbolic-ref", "HEAD"),
            git(self.repo, "ls-files", "-s"),
            git(self.repo, "diff", "--cached", "--name-status"),
            git(self.repo, "status", "--porcelain"),
        )
        self.init()
        self.create()
        after = (
            git(self.repo, "rev-parse", "HEAD"),
            git(self.repo, "symbolic-ref", "HEAD"),
            git(self.repo, "ls-files", "-s"),
            git(self.repo, "diff", "--cached", "--name-status"),
            git(self.repo, "status", "--porcelain"),
        )
        self.assertEqual(after, snapshot)
        self.assertEqual(git(self.repo, "rev-list", "--count", BRANCH), "2")

    def test_blocked_output_is_json_with_nonzero_exit_for_bad_arguments(self) -> None:
        code, payload = run_host("save-prepared", "--repo", str(self.repo))
        self.assertEqual((code, payload["status"]), (1, "blocked"))
        self.assertIn("reason", payload)

    def test_project_context_cli_still_cannot_save(self) -> None:
        self.init()
        before = self.head()
        for operation in [
            "save",
            "write",
            "persist",
            "persist-prepared",
            "persist_prepared",
        ]:
            with self.subTest(operation=operation):
                request = {
                    "operation": operation,
                    "project_ref": "Sample",
                    "approval_ref": "user confirmed",
                }
                completed = subprocess.run(
                    [sys.executable, str(PROJECT_CONTEXT_CLI)],
                    input=json.dumps(request).encode("utf-8"),
                    capture_output=True,
                    check=False,
                    env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
                )
                payload = json.loads(completed.stdout.decode("utf-8"))
                self.assertEqual(payload["status"], "blocked")
                self.assertEqual(payload["reason"], "operation_invalid")
        self.assertEqual(self.head(), before)


# ---------------------------------------------------------------------------
# save-snapshot（feature-inventory）。すべて使い捨てのstore repoとsource repoで実行する。
# ---------------------------------------------------------------------------

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_feature_registry import fixture as feature_fixture  # noqa: E402

FI_BRANCH = "qa-artifacts/Sample/feature-inventory"
FI_ARTIFACT = "qa/feature-inventory.json"


def source_listing(repo: Path) -> dict[str, tuple[int, int]]:
    base = repo / ".git"
    listing: dict[str, tuple[int, int]] = {}
    for current, _dirs, files in os.walk(base):
        for name in files:
            path = Path(current) / name
            stat = path.stat()
            listing[str(path.relative_to(base))] = (stat.st_size, stat.st_mtime_ns)
    return listing


def make_source(base: Path) -> tuple[Path, str, str]:
    source = base / "source"
    source.mkdir()
    git(source, "init", "-q", "-b", "main")
    git(source, "config", "user.email", "qa@example.invalid")
    git(source, "config", "user.name", "QA")
    (source / "README.md").write_text("baseline\n", encoding="utf-8")
    git(source, "add", ".")
    git(source, "commit", "-qm", "baseline")
    baseline = git(source, "rev-parse", "HEAD")
    (source / "src").mkdir()
    (source / "src" / "auth.py").write_text(
        "def access(): return True\n", encoding="utf-8"
    )
    git(source, "add", "src")
    git(source, "commit", "-qm", "source change")
    return source, baseline, git(source, "rev-parse", "HEAD")


def evidence_for(source: Path, baseline: str, head: str) -> list:
    return [
        {
            "source_id": "SRC-001",
            "repository_root": str(source),
            "authorized_root": str(source),
            "base_sha": baseline,
            "head_sha": head,
        }
    ]


def initial_snapshot(
    source: Path, baseline: str, head: str, operation: str = "op-1"
) -> tuple[dict, list]:
    data = feature_fixture()
    snap = data["snapshot"]
    snap["project_ref"] = "Sample"
    snap["artifact_ref"] = FI_ARTIFACT
    snap["operation_id"] = operation
    snap["source_revision"] = head
    snap["sources"][0]["revision"] = head
    snap["changes"][0].update(
        before_revision=baseline, after_revision=head, locator="src/auth.py"
    )
    snap["history"][0]["revision"] = head
    return snap, evidence_for(source, baseline, head)


class SaveSnapshotTests(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name)
        self.repo = self.base / "store"
        self.repo.mkdir()
        git(self.repo, "init", "-q", "-b", "main")
        git(self.repo, "config", "user.email", "qa@example.invalid")
        git(self.repo, "config", "user.name", "QA")
        (self.repo / "README.md").write_text("store\n", encoding="utf-8")
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-qm", "baseline")
        code, payload = run_host(
            "init-branch", "--repo", str(self.repo), "--branch", FI_BRANCH
        )
        self.assertEqual((code, payload["status"]), (0, "created"), payload)
        self.source, self.baseline, self.head = make_source(self.base)
        self.counter = 0

    def write_json(self, value: object) -> Path:
        self.counter += 1
        path = self.base / f"input-{self.counter}.json"
        path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
        return path

    def argv(
        self,
        snapshot: Path,
        evidence: object,
        *,
        expected: str = "none",
        previous: Path | None = None,
        observed: str | None = None,
        extra: tuple[str, ...] = (),
        confirmation: str = CONFIRMATION,
    ) -> list[str]:
        args = [
            "save-snapshot",
            "--repo",
            str(self.repo),
            "--branch",
            FI_BRANCH,
            "--project-ref",
            "Sample",
            "--snapshot-file",
            str(snapshot),
            "--git-inventory-requests-file",
            str(self.write_json(evidence)),
            "--expected-revision",
            expected,
            "--observed-head-revision",
            observed or self.head,
            "--change-reason",
            "initial inventory",
            "--user-confirmed-ref",
            confirmation,
            *extra,
        ]
        if previous is not None:
            args += ["--previous-snapshot-file", str(previous)]
        return args

    def save(
        self, snapshot: dict, evidence: list, **kwargs: object
    ) -> tuple[int, dict]:
        return run_host(*self.argv(self.write_json(snapshot), evidence, **kwargs))

    def read(self, revision: str | None = None) -> tuple[int, dict]:
        args = [
            "read",
            "--repo",
            str(self.repo),
            "--branch",
            FI_BRANCH,
            "--project-ref",
            "Sample",
            "--kind",
            "feature-inventory",
            "--artifact-ref",
            FI_ARTIFACT,
            "--user-confirmed-ref",
            CONFIRMATION,
        ]
        if revision:
            args += ["--revision", revision]
        return run_host(*args)

    def store_state(self) -> tuple[str, str, str]:
        return (
            git(self.repo, "rev-parse", "HEAD"),
            git(self.repo, "ls-files", "--stage"),
            git(self.repo, "status", "--porcelain"),
        )

    def test_first_save_stores_and_reads_back_identical_bytes(self) -> None:
        snap, evidence = initial_snapshot(self.source, self.baseline, self.head)
        code, payload = self.save(snap, evidence)
        self.assertEqual((code, payload["status"]), (0, "stored"), payload)
        self.assertEqual(payload["analysis_status"], "complete", payload)
        code, read = self.read()
        self.assertEqual((code, read["status"]), (0, "read"), read)
        expected = hashlib.sha256(
            json.dumps(
                snap, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            ).encode("utf-8")
        ).hexdigest()
        self.assertEqual(read["sha256"], expected)
        self.assertEqual(read["sha256"], payload["sha256"])
        self.assertEqual(read["revision"], payload["revision"])

    def test_save_without_a_user_confirmation_is_refused(self) -> None:
        snap, evidence = initial_snapshot(self.source, self.baseline, self.head)
        for value in ("", "   ", "line\nbreak", "x" * 1025):
            code, payload = self.save(snap, evidence, confirmation=value)
            self.assertEqual(
                (code, payload["status"]), (1, "blocked"), (value, payload)
            )
        code, payload = run_host(
            *[
                a
                for a in self.argv(self.write_json(snap), evidence)
                if a not in {"--user-confirmed-ref", CONFIRMATION}
            ]
        )
        self.assertEqual((code, payload["status"]), (1, "blocked"), payload)
        self.assertIsNone(self.read()[1].get("revision"))

    def test_same_operation_retry_is_idempotent_and_stale_revision_conflicts(
        self,
    ) -> None:
        snap, evidence = initial_snapshot(self.source, self.baseline, self.head)
        code, first = self.save(snap, evidence)
        self.assertEqual(code, 0, first)
        code, retry = self.save(snap, evidence)
        self.assertEqual((code, retry["status"]), (0, "idempotent"), retry)
        self.assertEqual(retry["revision"], first["revision"])

        update, evidence2 = updated_snapshot(
            snap, self.head, self.source, self.baseline
        )
        previous = self.write_json(snap)
        code, second = self.save(
            update, evidence2, expected=first["revision"], previous=previous
        )
        self.assertEqual((code, second["status"]), (0, "stored"), second)
        third_op, evidence3 = updated_snapshot(
            snap, self.head, self.source, self.baseline, operation="op-3"
        )
        code, stale = self.save(
            third_op, evidence3, expected=first["revision"], previous=previous
        )
        self.assertEqual((code, stale["status"]), (1, "blocked"), stale)
        self.assertIn("revision_conflict", stale["reasons"])

    def test_store_head_index_and_worktree_are_unchanged_by_save(self) -> None:
        before = self.store_state()
        snap, evidence = initial_snapshot(self.source, self.baseline, self.head)
        code, payload = self.save(snap, evidence)
        self.assertEqual((code, payload["status"]), (0, "stored"), payload)
        after = self.store_state()
        self.assertEqual(after[0], before[0])
        self.assertEqual(after[1], before[1])
        self.assertEqual(after[2], before[2])

    def test_default_save_writes_no_file_into_the_source_git(self) -> None:
        before = source_listing(self.source)
        snap, evidence = initial_snapshot(self.source, self.baseline, self.head)
        code, payload = self.save(snap, evidence)
        self.assertEqual((code, payload["status"]), (0, "stored"), payload)
        self.assertEqual(source_listing(self.source), before)
        self.assertEqual(list(self.source.joinpath(".git").rglob("*.lock")), [])

    def test_hold_source_refs_takes_locks_during_write_and_releases_them(self) -> None:
        snap, evidence = initial_snapshot(self.source, self.baseline, self.head)
        seen: list[list[str]] = []
        original = artifact_host.GitArtifactStore.write

        def spy(store, **kwargs):
            seen.append(
                sorted(
                    str(p.relative_to(self.source / ".git"))
                    for p in (self.source / ".git").rglob("*.lock")
                )
            )
            return original(store, **kwargs)

        argv = self.argv(self.write_json(snap), evidence, extra=("--hold-source-refs",))
        buffer = io.StringIO()
        with (
            mock.patch.object(artifact_host.GitArtifactStore, "write", spy),
            contextlib.redirect_stdout(buffer),
        ):
            code = artifact_host.main(argv)
        payload = json.loads(buffer.getvalue().splitlines()[-1])
        self.assertEqual((code, payload["status"]), (0, "stored"), payload)
        self.assertEqual(len(seen), 1)
        self.assertIn("HEAD.lock", seen[0])
        self.assertIn("refs/heads/main.lock", seen[0])
        self.assertEqual(list(self.source.joinpath(".git").rglob("*.lock")), [])

    def test_invalid_snapshots_are_refused_without_writing(self) -> None:
        def assert_refused(
            snap: dict, evidence: list, reasons: tuple[str, ...] | None
        ) -> dict:
            code, payload = self.save(snap, evidence)
            self.assertEqual((code, payload["status"]), (1, "blocked"), payload)
            if reasons:
                self.assertTrue(set(payload["reasons"]) & set(reasons), payload)
            self.assertIsNone(self.read()[1].get("revision"))
            return payload

        snap, evidence = initial_snapshot(self.source, self.baseline, self.head)
        missing = copy.deepcopy(snap)
        del missing["operation_id"]
        assert_refused(missing, evidence, None)

        # The snapshot's code source revision differs from the evidence head (the source is at head).
        snap, evidence = initial_snapshot(self.source, self.baseline, self.head)
        snap["sources"][0]["revision"] = self.baseline
        assert_refused(
            snap,
            evidence,
            (
                "git_evidence_source_revision_mismatch",
                "event_primary_code_source_missing",
                "change_source_revision_mismatch:DIF-001",
            ),
        )

        # The evidence names a head that is not the source's current HEAD.
        snap, evidence = initial_snapshot(self.source, self.baseline, self.head)
        evidence[0]["head_sha"] = self.baseline
        snap["sources"][0]["revision"] = self.baseline
        assert_refused(
            snap,
            evidence,
            (
                "git_head_changed",
                "git_evidence_source_revision_mismatch",
                "event_primary_code_source_missing",
                "change_source_revision_mismatch:DIF-001",
            ),
        )

        snap, evidence = initial_snapshot(self.source, self.baseline, self.head)
        code, payload = self.save(snap, evidence, observed=self.baseline)
        self.assertEqual((code, payload["status"]), (1, "stale"), payload)
        self.assertIn("source_head_changed", payload["reasons"])

        snap, evidence = initial_snapshot(self.source, self.baseline, self.head)
        snap["project_ref"] = "Other"
        code, payload = self.save(snap, evidence)
        self.assertEqual(
            (code, payload["reason"]), (1, "project_ref_mismatch"), payload
        )

        snap, evidence = initial_snapshot(self.source, self.baseline, self.head)
        code, payload = self.save(
            snap, evidence, extra=("--operation-id", "not-the-op")
        )
        self.assertEqual((code, payload["status"]), (1, "blocked"), payload)
        self.assertEqual(payload["reason"], "operation_id_mismatch")

        snap, evidence = initial_snapshot(self.source, self.baseline, self.head)
        code, payload = self.save(snap, evidence, expected="git:not-a-sha")
        self.assertEqual((code, payload["status"]), (1, "blocked"), payload)

    def test_branch_checked_out_in_the_store_is_refused(self) -> None:
        git(self.repo, "checkout", "-q", FI_BRANCH)
        snap, evidence = initial_snapshot(self.source, self.baseline, self.head)
        code, payload = self.save(snap, evidence)
        self.assertEqual((code, payload["status"]), (1, "blocked"), payload)
        self.assertEqual(payload["reason"], "branch_checked_out")

    def test_reclassification_is_stored_only_with_registered_confirmations(
        self,
    ) -> None:
        snap, evidence = initial_snapshot(self.source, self.baseline, self.head)
        code, first = self.save(snap, evidence)
        self.assertEqual(code, 0, first)
        previous = self.write_json(snap)
        update, evidence2 = reclassified_snapshot(
            snap, self.head, self.source, self.baseline
        )

        # Without the host's registration (no confirmations in this process), the store refuses.
        store = artifact_host.GitArtifactStore(
            self.repo,
            self.repo,
            FI_BRANCH,
            None,
            author_name="QA",
            author_email="qa@example.invalid",
            approval_source="user-confirmed",
        )
        store.record_user_confirmation(
            {
                "operation": "read",
                "kind": "feature-inventory",
                "project_ref": "Sample",
                "artifact_ref": FI_ARTIFACT,
                "approval_ref": CONFIRMATION,
            }
        )
        feature_registry = artifact_host._feature_registry()
        unverified = feature_registry.persist_snapshot(
            store,
            {
                "snapshot": update,
                "previous_snapshot": snap,
                "observed_head_revision": self.head,
            },
            expected_revision=first["revision"],
            approval_ref="approval/verified",
            approval_revision="policy-v1",
            change_reason="approved correction",
            git_inventory_requests=evidence2,
        )
        self.assertEqual(unverified["status"], "blocked", unverified)
        self.assertIn(
            "change_reclassification_approval_unverified:DIF-002", unverified["reasons"]
        )

        code, payload = self.save(
            update, evidence2, expected=first["revision"], previous=previous
        )
        self.assertEqual((code, payload["status"]), (0, "stored"), payload)
        self.assertEqual(payload["analysis_status"], "complete", payload)

    def test_read_export_and_verify_work_for_feature_inventory(self) -> None:
        snap, evidence = initial_snapshot(self.source, self.baseline, self.head)
        code, payload = self.save(snap, evidence)
        self.assertEqual(code, 0, payload)
        out = self.base / "projection.json"
        code, exported = run_host(
            "export",
            "--repo",
            str(self.repo),
            "--branch",
            FI_BRANCH,
            "--project-ref",
            "Sample",
            "--kind",
            "feature-inventory",
            "--artifact-ref",
            FI_ARTIFACT,
            "--out",
            str(out),
            "--user-confirmed-ref",
            CONFIRMATION,
        )
        self.assertEqual((code, exported["status"]), (0, "exported"), exported)
        self.assertEqual(exported["sha256"], payload["sha256"])
        code, verified = run_host(
            "verify-projection",
            "--repo",
            str(self.repo),
            "--branch",
            FI_BRANCH,
            "--project-ref",
            "Sample",
            "--kind",
            "feature-inventory",
            "--artifact-ref",
            FI_ARTIFACT,
            "--out",
            str(out),
            "--user-confirmed-ref",
            CONFIRMATION,
        )
        self.assertEqual((code, verified["status"]), (0, "in_sync"), verified)

    def test_save_prepared_still_refuses_feature_inventory(self) -> None:
        prepared = self.write_json(
            {"operation": "prepare-create", "artifact_ref": FI_ARTIFACT}
        )
        code, payload = run_host(
            "save-prepared",
            "--repo",
            str(self.repo),
            "--branch",
            FI_BRANCH,
            "--project-ref",
            "Sample",
            "--kind",
            "feature-inventory",
            "--artifact-ref",
            FI_ARTIFACT,
            "--prepared-file",
            str(prepared),
            "--user-confirmed-ref",
            CONFIRMATION,
        )
        self.assertEqual(
            (code, payload["reason"]), (1, "unsupported_kind_for_now"), payload
        )
        self.assertIn("save-snapshot", payload["hint"])


def updated_snapshot(
    previous: dict, head: str, source: Path, baseline: str, operation: str = "op-2"
) -> tuple[dict, list]:
    snap = copy.deepcopy(previous)
    snap["event"] = "analysis_update"
    snap["event_basis"] = {
        "source_revision": head,
        "evidence_ref": "review/" + operation,
    }
    snap["operation_id"] = operation
    snap["previous_artifact_revision"] = previous["artifact_revision"]
    snap["artifact_revision"] = "art-" + operation
    return snap, evidence_for(source, baseline, head)


def reclassified_snapshot(
    previous: dict, head: str, source: Path, baseline: str
) -> tuple[dict, list]:
    snap, evidence = updated_snapshot(previous, head, source, baseline)
    override = copy.deepcopy(snap["changes"][0])
    override.update(
        id="DIF-002",
        supersedes_id="DIF-001",
        classification="no_impact",
        feature_ids=[],
        reason="Approved correction after source review",
        evidence_ref="review/evidence-2",
        approval_ref="approval/verified",
        approval_revision="policy-v2",
    )
    snap["changes"].append(override)
    return snap, evidence


if __name__ == "__main__":
    unittest.main()
