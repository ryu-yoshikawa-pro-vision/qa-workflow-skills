from __future__ import annotations

import sqlite3
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[3] / "skills" / "qa-workflow" / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))
import artifact_graph  # noqa: E402

OWNER_A = "00000000-0000-4000-8000-000000000023"
OWNER_B = "00000000-0000-4000-8000-000000000024"
RESOURCE = "shared-test-user"


class SqliteSharedReservationTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name) / "reservations"

    def acquire(self, owner: str = OWNER_A, resource: str = RESOURCE) -> dict:
        return artifact_graph.reserve_sqlite_shared_resource(self.root, resource, owner)

    def release(
        self,
        revision: str,
        *,
        owner: str = OWNER_A,
        verified: bool = True,
        state: str | None = "complete",
        cleanup: bool = True,
        resource: str = RESOURCE,
    ) -> dict:
        return artifact_graph.release_sqlite_shared_resource(
            self.root,
            resource,
            owner,
            revision,
            owner_state_verified=verified,
            owner_execution_state=state,
            cleanup_confirmed=cleanup,
        )

    def read(self, resource: str = RESOURCE) -> dict:
        return artifact_graph.read_sqlite_shared_resource(self.root, resource)

    def test_native_acquire_release_and_reacquire_are_revisioned(self) -> None:
        first = self.acquire()
        self.assertEqual(first["status"], "reserved", first)
        self.assertEqual(first["reservation_revision"], "sqlite:1")
        self.assertEqual(self.read()["reservation_status"], "reserved")
        released = self.release(first["reservation_revision"])
        self.assertEqual(released["status"], "released", released)
        self.assertEqual(released["reservation_revision"], "sqlite:2")
        self.assertEqual(self.read()["reservation_status"], "released")
        new_owner = self.acquire(OWNER_B)
        self.assertEqual(new_owner["status"], "reserved", new_owner)
        self.assertEqual(new_owner["reservation_revision"], "sqlite:3")
        self.assertEqual(new_owner["owner_workflow_ref"], OWNER_B)
        self.assertEqual(self.release("sqlite:1")["status"], "blocked")
        self.assertEqual(self.read()["owner_workflow_ref"], OWNER_B)

    def test_concurrent_acquire_only_one_owner_can_claim(self) -> None:
        with ThreadPoolExecutor(max_workers=2) as executor:
            outcomes = list(executor.map(self.acquire, [OWNER_A, OWNER_B]))
        self.assertEqual(
            sorted(result["status"] for result in outcomes),
            ["conflict", "reserved"],
            outcomes,
        )
        winner = next(row for row in outcomes if row["status"] == "reserved")
        self.assertEqual(
            self.read()["owner_workflow_ref"], winner["owner_workflow_ref"]
        )

    def test_unverified_owner_or_cleanup_never_releases(self) -> None:
        acquired = self.acquire()
        revision = acquired["reservation_revision"]
        for verified, state, cleanup in [
            (False, "complete", True),
            (True, None, True),
            (True, "in_progress", True),
            (True, "complete", False),
        ]:
            with self.subTest(verified=verified, state=state, cleanup=cleanup):
                result = self.release(
                    revision,
                    verified=verified,
                    state=state,
                    cleanup=cleanup,
                )
                self.assertEqual(result["status"], "blocked")
                self.assertEqual(self.read()["reservation_status"], "reserved")
        self.assertEqual(self.release(revision)["status"], "released")

    def test_wrong_owner_and_stale_revision_are_rejected(self) -> None:
        acquired = self.acquire()
        self.assertEqual(
            self.release(acquired["reservation_revision"], owner=OWNER_B)["reason"],
            "reservation_owner_mismatch",
        )
        self.assertEqual(self.release("sqlite:23")["status"], "conflict")
        self.assertEqual(self.read()["reservation_status"], "reserved")

    def test_repeated_release_never_operates_twice(self) -> None:
        acquired = self.acquire()
        self.assertEqual(
            self.release(acquired["reservation_revision"])["status"], "released"
        )
        self.assertEqual(
            self.release(acquired["reservation_revision"])["status"], "conflict"
        )
        self.assertEqual(self.read()["reservation_revision"], "sqlite:2")

    def test_independent_resources_do_not_share_owner_or_token(self) -> None:
        self.assertEqual(self.acquire(resource="resource-a")["status"], "reserved")
        self.assertEqual(
            self.acquire(owner=OWNER_B, resource="resource-b")["status"], "reserved"
        )
        self.assertEqual(self.read("resource-a")["owner_workflow_ref"], OWNER_A)
        self.assertEqual(self.read("resource-b")["owner_workflow_ref"], OWNER_B)
        self.assertEqual(self.read("resource-missing")["status"], "blocked")

    def test_database_error_during_release_keeps_reservation(self) -> None:
        acquired = self.acquire()
        database = self.root / "resource-reservations.sqlite3"
        with sqlite3.connect(database) as connection:
            connection.execute(
                "CREATE TRIGGER fail_release BEFORE UPDATE ON shared_resource_reservation "
                "WHEN NEW.reservation_status='released' "
                "BEGIN SELECT RAISE(ABORT,'injected release failure'); END"
            )
        failed = self.release(acquired["reservation_revision"])
        self.assertEqual(failed["status"], "blocked")
        self.assertEqual(self.read()["reservation_status"], "reserved")
        self.assertEqual(self.read()["reservation_revision"], "sqlite:1")

    def test_database_symlink_is_blocked(self) -> None:
        self.root.mkdir()
        target = self.root.parent / "elsewhere.sqlite3"
        target.write_bytes(b"")
        link = self.root / "resource-reservations.sqlite3"
        try:
            link.symlink_to(target)
        except (NotImplementedError, OSError):
            self.skipTest("symlink unsupported")
        self.assertEqual(self.acquire()["status"], "blocked")
        self.assertEqual(self.read()["status"], "blocked")
        self.assertEqual(target.read_bytes(), b"")

    def test_bad_resource_and_workflow_ref_are_rejected(self) -> None:
        for bad in ["", "not\nvalid", chr(0xD800)]:
            with self.subTest(bad=repr(bad)):
                self.assertEqual(self.acquire(resource=bad)["status"], "blocked")
        self.assertEqual(self.acquire(owner="bad-workflow")["status"], "blocked")
        self.assertEqual(self.read("missing")["status"], "blocked")

    def test_existing_public_helper_uses_same_native_provider(self) -> None:
        reserved = artifact_graph.reserve_shared_resource(
            self.root,
            RESOURCE,
            OWNER_A,
            native_atomic_conditional_release=True,
        )
        self.assertEqual(reserved["status"], "reserved", reserved)
        self.assertEqual(self.read()["reservation_revision"], "sqlite:1")
        decision = artifact_graph.release_shared_resource(
            current_workflow_ref=OWNER_A,
            expected_workflow_ref=OWNER_A,
            expected_reservation_revision=reserved["reservation_revision"],
            current_reservation_revision=reserved["reservation_revision"],
            native_atomic_conditional_release=True,
            owner_state_verified=True,
            owner_execution_state="complete",
            cleanup_confirmed=True,
            reservation_root=self.root,
            resource_ref=RESOURCE,
        )
        self.assertEqual(decision["status"], "released", decision)
        self.assertEqual(self.read()["reservation_revision"], "sqlite:2")
        self.assertEqual(
            artifact_graph.release_shared_resource(
                current_workflow_ref=OWNER_A,
                expected_workflow_ref=OWNER_A,
                expected_reservation_revision="sqlite:2",
                current_reservation_revision="sqlite:2",
                native_atomic_conditional_release=True,
                owner_state_verified=True,
                owner_execution_state="complete",
                cleanup_confirmed=True,
                reservation_root=self.root,
            )["reason"],
            "reservation_target_missing",
        )

    def test_legacy_file_claim_blocks_sqlite_provider_migration(self) -> None:
        self.root.mkdir(parents=True)
        old_path = self.root / (
            artifact_graph.content_identity({"resource_ref": RESOURCE}) + ".json"
        )
        old_path.write_bytes(b'{"status":"reserved"}')
        result = self.acquire()
        self.assertEqual(result["reason"], "legacy_reservation_requires_reconciliation")
        self.assertEqual(old_path.read_bytes(), b'{"status":"reserved"}')
        self.assertFalse((self.root / "resource-reservations.sqlite3").exists())

    def test_corrupt_database_is_blocked(self) -> None:
        self.root.mkdir()
        (self.root / "resource-reservations.sqlite3").write_bytes(b"not sqlite")
        self.assertEqual(self.acquire()["status"], "blocked")
        self.assertEqual(self.read()["status"], "blocked")


if __name__ == "__main__":
    unittest.main()
