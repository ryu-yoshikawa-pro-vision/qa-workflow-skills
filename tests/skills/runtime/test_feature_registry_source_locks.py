"""persist_snapshot の hold_source_refs（読取専用ソースの ref lock 任意化）のテスト。

すべて使い捨てのソースrepoと一時storeで実行する。製品repoには一切書き込まない。
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "skills" / "feature-analysis" / "scripts"))
sys.path.insert(0, str(ROOT / "tests" / "skills" / "runtime"))

import feature_registry  # noqa: E402
from feature_registry import LocalArtifactStore, persist_snapshot  # noqa: E402
from test_feature_registry import fixture  # noqa: E402

ARTIFACT_REF = "qa/feature-inventory.json"


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def git_dir_listing(repo: Path) -> dict[str, tuple[int, int]]:
    """Relative path -> (size, mtime_ns) for every file under the source's .git."""
    base = repo / ".git"
    listing: dict[str, tuple[int, int]] = {}
    for current, _dirs, files in os.walk(base):
        for name in files:
            path = Path(current) / name
            stat = path.stat()
            listing[str(path.relative_to(base))] = (stat.st_size, stat.st_mtime_ns)
    return listing


class SourceRefLockOptionTests(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        base = Path(tmp.name)
        self.source = base / "source"
        self.source.mkdir()
        git(self.source, "init", "-q", "-b", "main")
        git(self.source, "config", "user.email", "qa@example.invalid")
        git(self.source, "config", "user.name", "QA")
        (self.source / "README.md").write_text("baseline\n", encoding="utf-8")
        git(self.source, "add", ".")
        git(self.source, "commit", "-qm", "baseline")
        self.baseline = git(self.source, "rev-parse", "HEAD")
        self.commit_source_change("def access(): return True\n")
        self.head = git(self.source, "rev-parse", "HEAD")

        store_root = base / "store"
        store_root.mkdir()
        self.store = LocalArtifactStore(
            store_root,
            store_root,
            lambda request: True,
        )

    def commit_source_change(self, text: str) -> None:
        src = self.source / "src"
        src.mkdir(exist_ok=True)
        (src / "auth.py").write_text(text, encoding="utf-8")
        git(self.source, "add", "src")
        git(self.source, "commit", "-qm", "source change")

    def request(self) -> dict:
        data = fixture()
        snap = data["snapshot"]
        snap["project_ref"] = "Sample"
        snap["artifact_ref"] = ARTIFACT_REF
        snap["source_revision"] = self.head
        snap["sources"][0]["revision"] = self.head
        snap["changes"][0].update(
            before_revision=self.baseline,
            after_revision=self.head,
            locator="src/auth.py",
        )
        snap["history"][0]["revision"] = self.head
        data["observed_head_revision"] = self.head
        return data

    def evidence(self) -> list[dict]:
        return [
            {
                "source_id": "SRC-001",
                "repository_root": str(self.source),
                "authorized_root": str(self.source),
                "base_sha": self.baseline,
                "head_sha": self.head,
            }
        ]

    def save(self, *, hold: bool | None = None, data: dict | None = None) -> dict:
        kwargs = {} if hold is None else {"hold_source_refs": hold}
        return persist_snapshot(
            self.store,
            data or self.request(),
            expected_revision=None,
            approval_ref="approval/verified",
            approval_revision="policy-v1",
            change_reason="initial inventory",
            git_inventory_requests=self.evidence(),
            **kwargs,
        )

    def record_store_writes(self, seen: list[dict]) -> None:
        """Wrap store.write to note the source's lock files at write time."""
        original = self.store.write

        def write(**kwargs):
            seen.append(
                {
                    "locks": sorted(
                        str(p.relative_to(self.source / ".git"))
                        for p in (self.source / ".git").rglob("*.lock")
                    ),
                    "listing": git_dir_listing(self.source),
                }
            )
            return original(**kwargs)

        self.store.write = write

    def test_default_holds_source_ref_locks_during_write_and_releases_them(
        self,
    ) -> None:
        seen: list[dict] = []
        self.record_store_writes(seen)
        result = self.save()
        self.assertEqual(result["status"], "stored", result)
        self.assertEqual(len(seen), 1)
        self.assertIn("HEAD.lock", seen[0]["locks"])
        self.assertIn("refs/heads/main.lock", seen[0]["locks"])
        self.assertEqual(
            sorted(p.name for p in (self.source / ".git").rglob("*.lock")), []
        )

    def test_hold_false_creates_no_file_under_source_git(self) -> None:
        before = git_dir_listing(self.source)
        seen: list[dict] = []
        self.record_store_writes(seen)
        result = self.save(hold=False)
        self.assertEqual(result["status"], "stored", result)
        self.assertEqual(len(seen), 1)
        self.assertEqual(seen[0]["locks"], [])
        self.assertEqual(seen[0]["listing"], before)
        self.assertEqual(git_dir_listing(self.source), before)

    def test_hold_false_rejects_head_moved_before_write(self) -> None:
        original = feature_registry._verify_git_evidence

        def verify_then_move_head(*args, **kwargs):
            original(*args, **kwargs)
            # The source is a throwaway repository. Without locks, a commit is possible.
            self.commit_source_change("def access(): return False\n")

        feature_registry._verify_git_evidence = verify_then_move_head
        try:
            result = self.save(hold=False)
        finally:
            feature_registry._verify_git_evidence = original
        self.assertEqual(result["status"], "blocked", result)
        self.assertIn("git_head_changed", result["reasons"])
        self.assertIsNone(
            self.store.read_current("feature-inventory", "Sample", ARTIFACT_REF)
        )

    def test_hold_false_refuses_an_existing_lockfile_without_touching_it(self) -> None:
        lock = self.source / ".git" / "HEAD.lock"
        lock.write_text("", encoding="utf-8")
        try:
            result = self.save(hold=False)
            self.assertEqual(result["status"], "blocked", result)
            self.assertIn("git_source_ref_lock_unavailable", result["reasons"])
            self.assertTrue(lock.exists())
        finally:
            lock.unlink()

    def test_default_hold_still_refuses_an_existing_lockfile(self) -> None:
        lock = self.source / ".git" / "HEAD.lock"
        lock.write_text("", encoding="utf-8")
        try:
            result = self.save()
            self.assertEqual(result["status"], "blocked", result)
            self.assertIn("git_source_ref_lock_unavailable", result["reasons"])
            self.assertTrue(lock.exists())
        finally:
            lock.unlink()
        self.assertIsNone(
            self.store.read_current("feature-inventory", "Sample", ARTIFACT_REF)
        )

    def test_head_moved_after_write_is_stored_with_a_warning(self) -> None:
        original = self.store.write

        def write_then_move_head(**kwargs):
            written = original(**kwargs)
            # The write is already stored; the source HEAD moves after it.
            self.commit_source_change("def access(): return False\n")
            return written

        self.store.write = write_then_move_head
        result = self.save(hold=False)
        self.assertEqual(result["status"], "stored", result)
        self.assertEqual(result["warnings"], ["source_head_changed_after_write"])
        self.assertIsInstance(result["reasons"], list)
        stored = self.store.read_current("feature-inventory", "Sample", ARTIFACT_REF)
        self.assertIsNotNone(stored)
        self.assertEqual(stored["revision"], result["revision"])

    def test_default_save_without_head_move_has_no_warning(self) -> None:
        result = self.save(hold=False)
        self.assertEqual(result["status"], "stored", result)
        self.assertNotIn("warnings", result)
        self.assertEqual(result["reasons"], [])

    def test_read_only_git_calls_carry_no_lazy_fetch_and_no_optional_locks(
        self,
    ) -> None:
        seen: list[dict] = []
        real_run = subprocess.run

        def recording_run(args, **kwargs):
            if args and args[0] == "git":
                seen.append(kwargs.get("env") or {})
            return real_run(args, **kwargs)

        with (
            mock.patch.dict(os.environ, {"QA_SENTINEL_ENV": "kept"}),
            mock.patch("subprocess.run", recording_run),
        ):
            result = self.save(hold=False)
        self.assertEqual(result["status"], "stored", result)
        self.assertGreater(len(seen), 0)
        for env in seen:
            self.assertEqual(env.get("GIT_NO_LAZY_FETCH"), "1", env)
            self.assertEqual(env.get("GIT_OPTIONAL_LOCKS"), "0", env)
            self.assertEqual(env.get("QA_SENTINEL_ENV"), "kept")

    def test_non_finite_numbers_are_refused_with_a_reason(self) -> None:
        for value in (float("nan"), float("inf"), float("-inf")):
            data = self.request()
            # An extra top-level key is not validated per field, so the value reaches the digest.
            data["snapshot"]["probe_value"] = value
            result = self.save(data=data)
            self.assertEqual(result["status"], "blocked", result)
            self.assertIn("snapshot_nonfinite_number", result["reasons"], result)
            self.assertIsNone(
                self.store.read_current("feature-inventory", "Sample", ARTIFACT_REF)
            )
        with self.assertRaises(feature_registry.ContractError):
            feature_registry.snapshot_content({"value": float("nan")})


if __name__ == "__main__":
    unittest.main()
