"""Host CLI tests for the user-confirmed Git artifact store.

All repositories are throwaway repositories under a temporary directory. The
qa-workspace parent repository is never touched.
"""

from __future__ import annotations

import hashlib
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
        self.content_file = self.base / "content.md"

    def write_content(self, text: str) -> Path:
        self.content_file.write_bytes(text.encode("utf-8"))
        return self.content_file

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

    def save(
        self,
        text: str,
        *,
        expected: str = "none",
        operation: str = "op-1",
        confirmation: str = "user confirmed 2026-11-18",
        reason: str = "initial",
    ) -> tuple[int, dict]:
        path = self.write_content(text)
        return run_host(
            "save",
            *self.common(),
            "--content-file",
            str(path),
            "--expected-revision",
            expected,
            "--operation-id",
            operation,
            "--source-ref",
            "issue/1",
            "--source-revision",
            "src-1",
            "--change-reason",
            reason,
            "--user-confirmed-ref",
            confirmation,
        )

    def read(
        self, *extra: str, confirmation: str = "user confirmed read"
    ) -> tuple[int, dict]:
        return run_host(
            "read", *self.common(), "--user-confirmed-ref", confirmation, *extra
        )

    def head(self) -> str:
        return git(self.repo, "rev-parse", "refs/heads/" + BRANCH)

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

    def test_save_stores_with_confirmation_and_records_trailer(self) -> None:
        self.init()
        code, payload = self.save("# PC\nbody\n")
        self.assertEqual((code, payload["status"]), (0, "stored"), payload)
        message = git(self.repo, "log", "-1", "--format=%B", BRANCH)
        self.assertIn("QA-Approval-Source: user-confirmed", message.splitlines())
        self.assertIn(
            "QA-Approval-Ref: user confirmed 2026-11-18", message.splitlines()
        )
        self.assertEqual(payload["revision"], "git:" + self.head())

    def test_save_without_confirmation_reference_is_rejected(self) -> None:
        self.init()
        before = self.head()
        for value in ["", "   ", "line one\nline two", "x" * 1025, "tab\tinside"]:
            with self.subTest(value=repr(value)):
                code, payload = self.save("# PC\n", confirmation=value)
                self.assertEqual(code, 1)
                self.assertEqual(payload["status"], "blocked")
                self.assertTrue(
                    payload["reason"].startswith("user_confirmed_ref_"), payload
                )
        self.assertEqual(self.head(), before)

    def test_save_rejects_branch_checked_out_in_main_worktree(self) -> None:
        self.init()
        git(self.repo, "switch", "-q", BRANCH)
        code, payload = self.save("# PC\n")
        self.assertEqual((code, payload["reason"]), (1, "branch_checked_out"))

    def test_same_operation_resend_is_idempotent(self) -> None:
        self.init()
        _, first = self.save("v1\n")
        code, again = self.save("v1\n", expected="none", operation="op-1")
        self.assertEqual((code, again["status"]), (0, "idempotent"), again)
        self.assertEqual(again["revision"], first["revision"])
        self.assertEqual(git(self.repo, "rev-list", "--count", BRANCH), "2")

        _, second = self.save("v2\n", expected=first["revision"], operation="op-2")
        self.assertEqual(second["status"], "stored", second)
        code, resent = self.save("v2\n", expected=first["revision"], operation="op-2")
        self.assertEqual((code, resent["status"]), (0, "idempotent"), resent)
        self.assertEqual(resent["revision"], second["revision"])
        self.assertEqual(git(self.repo, "rev-list", "--count", BRANCH), "3")

    def test_stale_expected_revision_is_a_revision_conflict(self) -> None:
        self.init()
        _, first = self.save("v1\n")
        _, second = self.save("v2\n", expected=first["revision"], operation="op-2")
        self.assertEqual(second["status"], "stored", second)
        code, payload = self.save("v3\n", expected=first["revision"], operation="op-3")
        self.assertEqual((code, payload["reason"]), (1, "revision_conflict"), payload)
        self.assertEqual(self.head(), second["revision"][4:])

    def test_save_readback_returns_exact_content_and_hash(self) -> None:
        self.init()
        text = "# Project\r\n日本語 ✓\n\nlast line without newline"
        _, saved = self.save(text)
        code, current = self.read()
        self.assertEqual(code, 0, current)
        self.assertEqual(current["content"], text)
        self.assertEqual(
            current["sha256"], hashlib.sha256(text.encode("utf-8")).hexdigest()
        )
        self.assertEqual(current["revision"], saved["revision"])

    def test_read_current_and_history_revisions(self) -> None:
        self.init()
        _, first = self.save("v1\n")
        _, second = self.save("v2\n", expected=first["revision"], operation="op-2")
        code, current = self.read()
        self.assertEqual(
            (code, current["content"], current["revision"]),
            (0, "v2\n", second["revision"]),
        )
        code, old = self.read("--revision", first["revision"])
        self.assertEqual(
            (code, old["content"], old["revision"]), (0, "v1\n", first["revision"])
        )
        # init -> v1 -> v2 の順。init（成果物を含まないroot commit）は履歴から読めない。
        init_revision = "git:" + git(self.repo, "rev-parse", BRANCH + "~2")
        code, absent = self.read("--revision", init_revision)
        self.assertEqual((code, absent["status"]), (1, "absent"))

    def test_export_is_byte_exact_read_only_and_atomic_into_existing_directory(
        self,
    ) -> None:
        self.init()
        text = "# PC\r\nbody\n"
        self.save(text)
        out = self.repo / "projections" / "PROJECT_CONTEXT.md"
        out.parent.mkdir()
        code, payload = run_host(
            "export", *self.common(), "--out", str(out), "--user-confirmed-ref", "read"
        )
        self.assertEqual((code, payload["status"]), (0, "exported"), payload)
        self.assertEqual(out.read_bytes(), text.encode("utf-8"))
        self.assertEqual(
            payload["sha256"], hashlib.sha256(text.encode("utf-8")).hexdigest()
        )
        self.assertEqual(stat.S_IMODE(out.stat().st_mode), 0o444)

    def test_export_refuses_missing_parent_directory(self) -> None:
        self.init()
        self.save("v1\n")
        out = self.base / "missing" / "PROJECT_CONTEXT.md"
        code, payload = run_host(
            "export", *self.common(), "--out", str(out), "--user-confirmed-ref", "read"
        )
        self.assertEqual((code, payload["reason"]), (1, "out_parent_missing"))
        self.assertFalse(out.parent.exists())

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
        self.save("v1\n")
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
        out.write_text("v1\nhand edit\n", encoding="utf-8")
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
        self.save("# PC\n")
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
        code, payload = run_host("save", "--repo", str(self.repo))
        self.assertEqual((code, payload["status"]), (1, "blocked"))
        self.assertIn("reason", payload)


if __name__ == "__main__":
    unittest.main()
