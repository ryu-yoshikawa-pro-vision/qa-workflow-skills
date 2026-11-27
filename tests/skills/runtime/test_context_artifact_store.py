from __future__ import annotations

import copy
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests" / "skills" / "runtime"))

import test_context_artifacts as fixtures  # noqa: E402
from context_artifact_store import DirectoryArtifactStore, StoreError  # noqa: E402


class ContextArtifactDirectoryStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.store = DirectoryArtifactStore(self.root)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _store_cli(self, request: dict) -> dict:
        completed = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "context_artifact_store.py")],
            input=json.dumps(request, ensure_ascii=False).encode("utf-8"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=ROOT,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr.decode("utf-8"))
        self.assertEqual(completed.stderr, b"")
        return json.loads(completed.stdout)

    def test_three_kinds_support_create_list_read_history_and_restart(self) -> None:
        batch = fixtures.build_batch()
        candidate = fixtures.build_candidate()
        run = fixtures.build_run()

        for kind, artifact in (
            ("context-signal-batch", batch),
            ("context-rule-candidate", candidate),
            ("context-synthesis-run", run),
        ):
            with self.subTest(kind=kind):
                created = self.store.write(kind, artifact)
                self.assertEqual(created["status"], "stored")
                readback = created["readback"]
                self.assertEqual(readback, self.store.read(artifact["artifact_ref"]))
                self.assertEqual(
                    readback["content"].encode(), fixtures.canonical_bytes(artifact)
                )
                self.assertEqual(
                    self.store.list(kind)["artifacts"],
                    [
                        {
                            "artifact_ref": artifact["artifact_ref"],
                            "revision": readback["revision"],
                            "sha256": readback["sha256"],
                        }
                    ],
                )

        restarted = DirectoryArtifactStore(self.root)
        for artifact in (batch, candidate, run):
            exact = restarted.read(artifact["artifact_ref"])
            self.assertEqual(
                exact["content"], fixtures.canonical_bytes(artifact).decode()
            )
            self.assertEqual(
                restarted.history(artifact["artifact_ref"])[0]["current"], True
            )

    def test_storage_cli_round_trips_all_kinds_and_conditioned_history(self) -> None:
        artifacts = (
            ("context-signal-batch", fixtures.build_batch()),
            ("context-rule-candidate", fixtures.build_candidate()),
            ("context-synthesis-run", fixtures.build_run()),
        )
        for kind, artifact in artifacts:
            with self.subTest(kind=kind):
                written = self._store_cli(
                    {
                        "operation": "write",
                        "root": str(self.root),
                        "kind": kind,
                        "artifact": artifact,
                    }
                )
                self.assertEqual(written["status"], "stored")
                first = written["readback"]
                self.assertEqual(first["root_binding"], self.store.root_binding)
                self.assertEqual(
                    self._store_cli(
                        {
                            "operation": "read",
                            "root": str(self.root),
                            "artifact_ref": artifact["artifact_ref"],
                            "revision": first["revision"],
                        }
                    )["readback"],
                    first,
                )
                self.assertEqual(
                    self._store_cli(
                        {
                            "operation": "list",
                            "root": str(self.root),
                            "kind": kind,
                        }
                    )["artifacts"],
                    [
                        {
                            "artifact_ref": artifact["artifact_ref"],
                            "revision": first["revision"],
                            "sha256": first["sha256"],
                        }
                    ],
                )
                self.assertEqual(
                    self._store_cli(
                        {
                            "operation": "history",
                            "root": str(self.root),
                            "artifact_ref": artifact["artifact_ref"],
                        }
                    )["history"],
                    [
                        {
                            "artifact_ref": artifact["artifact_ref"],
                            "revision": first["revision"],
                            "sha256": first["sha256"],
                            "current": True,
                        }
                    ],
                )

                if kind == "context-rule-candidate":
                    changed = copy.deepcopy(artifact)
                    changed["rule_statement"] = "Updated through the storage CLI."
                    updated = self._store_cli(
                        {
                            "operation": "write",
                            "root": str(self.root),
                            "kind": kind,
                            "artifact": changed,
                            "expected_revision": first["revision"],
                            "expected_content_hash": first["sha256"],
                        }
                    )
                    self.assertEqual(updated["status"], "stored")
                    exact_base = self._store_cli(
                        {
                            "operation": "read",
                            "root": str(self.root),
                            "artifact_ref": artifact["artifact_ref"],
                            "revision": first["revision"],
                        }
                    )
                    self.assertEqual(exact_base["readback"], first)
                    history = self._store_cli(
                        {
                            "operation": "history",
                            "root": str(self.root),
                            "artifact_ref": artifact["artifact_ref"],
                        }
                    )["history"]
                    self.assertEqual(len(history), 2)
                    self.assertEqual(sum(bool(item["current"]) for item in history), 1)

    def test_conditioned_updates_retain_exact_revisions_even_when_content_repeats(
        self,
    ) -> None:
        original = fixtures.build_candidate()
        first = self.store.write("context-rule-candidate", original)["readback"]

        changed = copy.deepcopy(original)
        changed["rule_statement"] = "Updated wording for an unchanged hypothesis."
        second_result = self.store.write(
            "context-rule-candidate",
            changed,
            expected_revision=first["revision"],
            expected_content_hash=first["sha256"],
        )
        self.assertEqual(second_result["status"], "stored")
        second = second_result["readback"]
        self.assertNotEqual(first["revision"], second["revision"])
        self.assertEqual(
            self.store.read(original["artifact_ref"], first["revision"]), first
        )

        restored = self.store.write(
            "context-rule-candidate",
            original,
            expected_revision=second["revision"],
            expected_content_hash=second["sha256"],
        )
        self.assertEqual(restored["status"], "stored")
        third = restored["readback"]
        self.assertNotEqual(third["revision"], first["revision"])
        self.assertEqual(third["content"], first["content"])
        self.assertEqual(
            self.store.read(original["artifact_ref"], third["revision"]), third
        )
        self.assertEqual(len(self.store.history(original["artifact_ref"])), 3)

        stale = self.store.write(
            "context-rule-candidate",
            changed,
            expected_revision=first["revision"],
            expected_content_hash=first["sha256"],
        )
        self.assertEqual(stale["status"], "conflict")
        self.assertEqual(stale["reason"], "expected_revision_changed")

    def test_conditioned_update_checks_base_hash_even_when_file_revision_is_unchanged(
        self,
    ) -> None:
        candidate = fixtures.build_candidate()
        first = self.store.write("context-rule-candidate", candidate)["readback"]
        path = self.root / first["artifact_ref"]
        externally_changed = copy.deepcopy(candidate)
        externally_changed["rule_statement"] = "Changed in place outside the store."
        path.write_bytes(fixtures.canonical_bytes(externally_changed))

        stale = self.store.write(
            "context-rule-candidate",
            candidate,
            expected_revision=first["revision"],
            expected_content_hash=first["sha256"],
        )

        self.assertEqual(stale["status"], "conflict")
        self.assertEqual(stale["reason"], "expected_content_hash_changed")
        self.assertEqual(
            self.store.read(candidate["artifact_ref"])["sha256"],
            hashlib.sha256(fixtures.canonical_bytes(externally_changed)).hexdigest(),
        )

    def test_related_candidate_revision_and_hash_are_checked_at_update_boundary(
        self,
    ) -> None:
        candidate = fixtures.build_candidate()
        related = fixtures.build_candidate(role="administrator")
        target_readback = self.store.write("context-rule-candidate", candidate)[
            "readback"
        ]
        related_readback = self.store.write("context-rule-candidate", related)[
            "readback"
        ]
        precondition = {
            "candidate_ref": related["artifact_ref"],
            "expected_revision": related_readback["revision"],
            "content_hash": related_readback["sha256"],
        }

        changed_related = copy.deepcopy(related)
        changed_related["rule_statement"] = "A related candidate changed first."
        current_related = self.store.write(
            "context-rule-candidate",
            changed_related,
            expected_revision=related_readback["revision"],
            expected_content_hash=related_readback["sha256"],
        )["readback"]
        changed_target = copy.deepcopy(candidate)
        changed_target["rule_statement"] = (
            "Merge was planned against an old related revision."
        )
        stale = self.store.write(
            "context-rule-candidate",
            changed_target,
            expected_revision=target_readback["revision"],
            expected_content_hash=target_readback["sha256"],
            related_preconditions=[precondition],
        )

        self.assertEqual(stale["status"], "conflict")
        self.assertEqual(stale["reason"], "related_precondition_changed")
        self.assertEqual(self.store.read(candidate["artifact_ref"]), target_readback)

        refreshed = {
            "candidate_ref": related["artifact_ref"],
            "expected_revision": current_related["revision"],
            "content_hash": current_related["sha256"],
        }
        saved = self.store.write(
            "context-rule-candidate",
            changed_target,
            expected_revision=target_readback["revision"],
            expected_content_hash=target_readback["sha256"],
            related_preconditions=[refreshed],
        )
        self.assertEqual(saved["status"], "stored")

    def test_related_candidate_remains_locked_until_dependent_update_is_saved(
        self,
    ) -> None:
        candidate = fixtures.build_candidate()
        related = fixtures.build_candidate(role="administrator")
        target_readback = self.store.write("context-rule-candidate", candidate)[
            "readback"
        ]
        related_readback = self.store.write("context-rule-candidate", related)[
            "readback"
        ]
        changed_target = copy.deepcopy(candidate)
        changed_target["rule_statement"] = (
            "Update that depends on the related candidate."
        )
        changed_related = copy.deepcopy(related)
        changed_related["rule_statement"] = "Concurrent dependency update."
        entered_archive = threading.Event()
        allow_archive = threading.Event()
        related_started = threading.Event()
        original_archive = self.store._archive_current

        def pause_after_precondition_check(*args: object) -> None:
            entered_archive.set()
            if not allow_archive.wait(timeout=5):
                raise TimeoutError("test archive gate timed out")
            original_archive(*args)

        with (
            ThreadPoolExecutor(max_workers=2) as pool,
            mock.patch.object(
                self.store,
                "_archive_current",
                side_effect=pause_after_precondition_check,
            ),
        ):
            dependent = pool.submit(
                self.store.write,
                "context-rule-candidate",
                changed_target,
                expected_revision=target_readback["revision"],
                expected_content_hash=target_readback["sha256"],
                related_preconditions=[
                    {
                        "candidate_ref": related["artifact_ref"],
                        "expected_revision": related_readback["revision"],
                        "content_hash": related_readback["sha256"],
                    }
                ],
            )
            self.assertTrue(entered_archive.wait(timeout=5))

            def update_related() -> dict:
                related_started.set()
                return self.store.write(
                    "context-rule-candidate",
                    changed_related,
                    expected_revision=related_readback["revision"],
                    expected_content_hash=related_readback["sha256"],
                )

            concurrent = pool.submit(update_related)
            self.assertTrue(related_started.wait(timeout=5))
            self.assertFalse(concurrent.done())
            allow_archive.set()
            self.assertEqual(dependent.result(timeout=5)["status"], "stored")
            self.assertEqual(concurrent.result(timeout=5)["status"], "stored")
        self.assertNotEqual(
            self.store.read(related["artifact_ref"])["sha256"],
            related_readback["sha256"],
        )

    def test_signal_batch_is_create_if_absent_and_conflicting_rewrite_is_rejected(
        self,
    ) -> None:
        batch = fixtures.build_batch()
        created = self.store.write("context-signal-batch", batch)
        self.assertEqual(created["status"], "stored")
        self.assertEqual(
            self.store.write("context-signal-batch", batch)["status"], "reused"
        )

        changed = copy.deepcopy(batch)
        changed["candidate_check"] = {
            "status": "not_checked",
            "triggered_candidate_identities": [],
        }
        conflict = self.store.write("context-signal-batch", changed)
        self.assertEqual(conflict["status"], "conflict")
        self.assertEqual(self.store.read(batch["artifact_ref"]), created["readback"])

    def test_only_one_writer_can_update_the_same_expected_revision(self) -> None:
        candidate = fixtures.build_candidate()
        first = self.store.write("context-rule-candidate", candidate)["readback"]
        barrier = threading.Barrier(2)

        def update(statement: str) -> dict:
            changed = copy.deepcopy(candidate)
            changed["rule_statement"] = statement
            local_store = DirectoryArtifactStore(self.root)
            barrier.wait(timeout=5)
            return local_store.write(
                "context-rule-candidate",
                changed,
                expected_revision=first["revision"],
                expected_content_hash=first["sha256"],
            )

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(update, ("Writer A", "Writer B")))
        self.assertEqual(
            sorted(item["status"] for item in results), ["conflict", "stored"]
        )
        self.assertEqual(len(self.store.history(candidate["artifact_ref"])), 2)

    def test_ordinary_create_remains_available_without_conditioned_update_capability(
        self,
    ) -> None:
        candidate = fixtures.build_candidate()
        created = self.store.write("context-rule-candidate", candidate)["readback"]
        self.store.supports_local_conditioned_update = False
        changed = copy.deepcopy(candidate)
        changed["rule_statement"] = "Changed without a local CAS guarantee."

        with self.assertRaisesRegex(
            StoreError, "conditional_update_requires_local_filesystem"
        ):
            self.store.write(
                "context-rule-candidate",
                changed,
                expected_revision=created["revision"],
                expected_content_hash=created["sha256"],
            )

        self.assertEqual(self.store.read(candidate["artifact_ref"]), created)
        self.assertEqual(len(self.store.history(candidate["artifact_ref"])), 1)

    def test_symlink_paths_and_noncanonical_refs_are_rejected(self) -> None:
        outside = Path(self.temp.name).parent / (Path(self.temp.name).name + "-outside")
        outside.mkdir()
        try:
            (self.root / "context-rule-candidate").symlink_to(
                outside, target_is_directory=True
            )
            with self.assertRaisesRegex(StoreError, "kind_directory_not_regular"):
                self.store.write("context-rule-candidate", fixtures.build_candidate())
        finally:
            (self.root / "context-rule-candidate").unlink(missing_ok=True)
            outside.rmdir()

        with self.assertRaisesRegex(StoreError, "artifact_ref_invalid"):
            self.store.read("context-rule-candidate/../outside.json")
        with self.assertRaisesRegex(StoreError, "root_must_be_absolute"):
            DirectoryArtifactStore("relative/root")

    def test_history_symlink_is_rejected_before_any_outside_directory_is_created(
        self,
    ) -> None:
        candidate = fixtures.build_candidate()
        created = self.store.write("context-rule-candidate", candidate)["readback"]
        changed = copy.deepcopy(candidate)
        changed["rule_statement"] = "Attempted history write through a symlink."
        outside = self.root.parent / (self.root.name + "-history-outside")
        outside.mkdir()
        history_root = self.root / "context-rule-candidate" / ".history"
        try:
            history_root.symlink_to(outside, target_is_directory=True)
            with self.assertRaisesRegex(StoreError, "history_directory_not_regular"):
                self.store.write(
                    "context-rule-candidate",
                    changed,
                    expected_revision=created["revision"],
                    expected_content_hash=created["sha256"],
                )
            self.assertEqual(list(outside.iterdir()), [])
            self.assertEqual(self.store.read(candidate["artifact_ref"]), created)
        finally:
            history_root.unlink(missing_ok=True)
            outside.rmdir()

    def test_history_directory_fallback_checks_symlink_before_mkdir(self) -> None:
        candidate = fixtures.build_candidate()
        created = self.store.write("context-rule-candidate", candidate)["readback"]
        outside = self.root.parent / (self.root.name + "-fallback-history-outside")
        outside.mkdir()
        history_root = self.root / "context-rule-candidate" / ".history"
        try:
            history_root.symlink_to(outside, target_is_directory=True)
            with mock.patch.object(os, "supports_dir_fd", set()):
                with self.assertRaisesRegex(
                    StoreError, "history_directory_not_regular"
                ):
                    self.store.write(
                        "context-rule-candidate",
                        {**candidate, "rule_statement": "Fallback symlink probe."},
                        expected_revision=created["revision"],
                        expected_content_hash=created["sha256"],
                    )
            self.assertEqual(list(outside.iterdir()), [])
            self.assertEqual(self.store.read(candidate["artifact_ref"]), created)
        finally:
            history_root.unlink(missing_ok=True)
            outside.rmdir()


if __name__ == "__main__":
    unittest.main()
