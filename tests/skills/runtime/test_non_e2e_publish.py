"""Native Git fast-forward publication and conflict rejection tests."""

from __future__ import annotations

import hashlib
import importlib.util
import subprocess
import tempfile
import unittest
from unittest import mock
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location(
    "publish_git", ROOT / "skills/testware-implementation/scripts/publish_git.py"
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


class GitPublishTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.remote = root / "remote.git"
        subprocess.run(["git", "init", "--bare", "-q", str(self.remote)], check=True)
        self.a = root / "writer-a"
        subprocess.run(
            ["git", "clone", "-q", str(self.remote), str(self.a)], check=True
        )
        git(self.a, "config", "user.name", "QA fixture")
        git(self.a, "config", "user.email", "qa@example.invalid")
        (self.a / "tests").mkdir()
        (self.a / "tests" / "case.txt").write_text("old\n", encoding="utf-8")
        (self.a / "tests" / "other.txt").write_text("old\n", encoding="utf-8")
        git(self.a, "add", "tests")
        git(self.a, "commit", "-qm", "base")
        git(self.a, "branch", "-M", "fixture")
        git(self.a, "push", "-q", "origin", "fixture")
        self.base = git(self.a, "rev-parse", "HEAD")
        self.b = root / "writer-b"
        subprocess.run(
            ["git", "clone", "-q", "-b", "fixture", str(self.remote), str(self.b)],
            check=True,
        )
        git(self.b, "config", "user.name", "QA fixture")
        git(self.b, "config", "user.email", "qa@example.invalid")

    def _candidate(self, repo: Path, file: str, value: str) -> tuple[str, str]:
        path = repo / file
        original = path.read_bytes()
        digest = "sha256:" + hashlib.sha256(original).hexdigest()
        path.write_text(value, encoding="utf-8")
        git(repo, "add", file)
        git(repo, "commit", "-qm", "candidate")
        return git(repo, "rev-parse", "HEAD"), digest

    def _publish(self, repo: Path, base: str, candidate: str, file: str, digest: str):
        return MODULE.publish(
            repo_path=repo,
            remote="origin",
            branch="fixture",
            expected_head=base,
            candidate=candidate,
            allowed_prefixes=["tests"],
            prior_content_hashes={file: digest},
        )

    def test_first_writer_succeeds_and_stale_second_writer_is_rejected(self):
        first, digest = self._candidate(self.a, "tests/case.txt", "first\n")
        second, second_digest = self._candidate(self.b, "tests/case.txt", "second\n")
        published = self._publish(self.a, self.base, first, "tests/case.txt", digest)
        self.assertEqual(published["state"], "published_and_readback_verified")
        with self.assertRaisesRegex(MODULE.PublishError, "remote_branch_changed"):
            self._publish(self.b, self.base, second, "tests/case.txt", second_digest)
        git(self.b, "fetch", "-q", "origin", "fixture")
        self.assertEqual(git(self.b, "rev-parse", "FETCH_HEAD"), first)
        self.assertEqual(git(self.b, "show", "FETCH_HEAD:tests/case.txt"), "first")

    def test_independent_path_can_rebase_to_new_head_and_publish(self):
        first, digest = self._candidate(self.a, "tests/case.txt", "first\n")
        self._publish(self.a, self.base, first, "tests/case.txt", digest)
        git(self.b, "pull", "-q", "--ff-only", "origin", "fixture")
        second, other_digest = self._candidate(self.b, "tests/other.txt", "second\n")
        result = self._publish(self.b, first, second, "tests/other.txt", other_digest)
        self.assertEqual(result["commit_sha"], second)
        self.assertEqual(git(self.b, "show", "HEAD:tests/case.txt"), "first")

    def test_unapproved_file_change_is_rejected_before_push(self):
        candidate, digest = self._candidate(self.a, "tests/case.txt", "test change")
        with self.assertRaisesRegex(MODULE.PublishError, "path_out_of_scope"):
            MODULE.publish(
                repo_path=self.a,
                remote="origin",
                branch="fixture",
                expected_head=self.base,
                candidate=candidate,
                allowed_prefixes=["docs"],
                prior_content_hashes={"tests/case.txt": digest},
            )
        self.assertEqual(
            git(self.a, "ls-remote", "--heads", "origin", "refs/heads/fixture").split()[
                0
            ],
            self.base,
        )

    def test_unicode_path_with_core_quote_path_enabled(self):
        git(self.a, "config", "core.quotePath", "true")
        path = "tests/価格.test.ts"
        (self.a / path).write_text("new\n", encoding="utf-8")
        git(self.a, "add", path)
        git(self.a, "commit", "-qm", "unicode path")
        commit = git(self.a, "rev-parse", "HEAD")
        result = self._publish(self.a, self.base, commit, path, None)
        self.assertEqual(result["commit_sha"], commit)
        git(self.b, "fetch", "-q", "origin", "fixture")
        self.assertEqual(git(self.b, "show", "FETCH_HEAD:" + path), "new")

    def test_reviewed_deletion_is_published_and_read_back(self):
        path = "tests/other.txt"
        digest = "sha256:" + hashlib.sha256((self.a / path).read_bytes()).hexdigest()
        (self.a / path).unlink()
        git(self.a, "add", path)
        git(self.a, "commit", "-qm", "delete testware")
        commit = git(self.a, "rev-parse", "HEAD")
        result = self._publish(self.a, self.base, commit, path, digest)
        self.assertEqual(result["state"], "published_and_readback_verified")
        git(self.b, "fetch", "-q", "origin", "fixture")
        self.assertFalse(
            subprocess.run(
                ["git", "-C", str(self.b), "cat-file", "-e",
                 "FETCH_HEAD:" + path],
                capture_output=True,
            ).returncode == 0
        )

    def test_remote_rewind_between_read_and_push_is_rejected(self):
        first, digest = self._candidate(self.a, "tests/case.txt", "first\n")
        self._publish(self.a, self.base, first, "tests/case.txt", digest)
        second, digest = self._candidate(self.a, "tests/other.txt", "second\n")
        original_remote_head = MODULE._remote_head
        def rewind_after_read(repo, remote, branch):
            current = original_remote_head(repo, remote, branch)
            git(self.remote, "update-ref", "refs/heads/fixture", self.base)
            return current
        with mock.patch.object(MODULE, "_remote_head", side_effect=rewind_after_read):
            with self.assertRaisesRegex(
                MODULE.PublishError, "push_rejected_or_response_unknown"
            ):
                self._publish(self.a, first, second, "tests/other.txt", digest)
        self.assertEqual(
            git(self.a, "ls-remote", "origin", "refs/heads/fixture").split()[0],
            self.base,
        )

    def test_wrong_base_digest_or_extra_diff_is_rejected(self):
        candidate, digest = self._candidate(self.a, "tests/case.txt", "new")
        with self.assertRaisesRegex(MODULE.PublishError, "changed_base_snapshot"):
            self._publish(
                self.a, self.base, candidate, "tests/case.txt", "sha256:wrong"
            )
        with self.assertRaisesRegex(MODULE.PublishError, "incomplete_changed_paths"):
            self._publish(self.a, self.base, candidate, "tests/other.txt", digest)


if __name__ == "__main__":
    unittest.main()
