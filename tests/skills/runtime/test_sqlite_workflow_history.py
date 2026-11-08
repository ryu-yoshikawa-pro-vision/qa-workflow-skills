from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[3] / "skills" / "qa-workflow" / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))
import artifact_graph  # noqa: E402

REF = "00000000-0000-4000-8000-000000000023"
OTHER = "00000000-0000-4000-8000-000000000024"


class SqliteWorkflowHistoryTests(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name) / "workflow-state"

    def create(self, ref: str = REF) -> dict:
        return artifact_graph.create_sqlite_workflow_state(
            self.root, ref, {"marker": "initial"}
        )

    def update(self, revision: str = "sqlite:1", marker: str = "changed") -> dict:
        return artifact_graph.conditional_write_sqlite_workflow_state(
            self.root, REF, revision, {"marker": marker}
        )

    def read_history(self, revision: str, ref: str = REF) -> dict:
        return artifact_graph.read_sqlite_workflow_state_revision(
            self.root, ref, revision
        )

    def test_create_and_cas_preserve_exact_readable_revisions(self) -> None:
        created = self.create()
        self.assertEqual(created["status"], "created", created)
        self.assertTrue(created["historical_revision_available"])
        written = self.update()
        self.assertEqual(written["status"], "written", written)
        self.assertTrue(written["historical_revision_available"])
        self.assertEqual(self.read_history("sqlite:1")["state"], {"marker": "initial"})
        self.assertEqual(self.read_history("sqlite:2")["state"], {"marker": "changed"})
        self.assertEqual(
            artifact_graph.read_sqlite_workflow_state(self.root, REF)["state_revision"],
            "sqlite:2",
        )

    def test_historical_retrieval_has_strict_workflow_and_revision_identity(
        self,
    ) -> None:
        self.create()
        for revision, ref in [
            ("sqlite:2", REF),
            ("sqlite:0", REF),
            ("sha256:" + "0" * 64, REF),
            ("sqlite:1", OTHER),
            ("sqlite:1", "bad-ref"),
        ]:
            with self.subTest(revision=revision, ref=ref):
                self.assertEqual(self.read_history(revision, ref)["status"], "blocked")

    def test_competing_updates_preserve_single_winner_and_history(self) -> None:
        self.create()
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(
                executor.map(lambda name: self.update(marker=name), ["a", "b"])
            )
        self.assertEqual(
            sorted(result["status"] for result in results),
            ["conflict", "written"],
        )
        self.assertEqual(self.read_history("sqlite:1")["state"], {"marker": "initial"})
        winner = next(result for result in results if result["status"] == "written")
        self.assertEqual(self.read_history("sqlite:2")["state"], winner["state"])
        self.assertEqual(self.read_history("sqlite:3")["status"], "blocked")

    def test_stale_expected_revision_never_creates_new_history(self) -> None:
        self.create()
        self.assertEqual(self.update()["status"], "written")
        conflict = self.update(marker="stale")
        self.assertEqual(conflict["status"], "conflict")
        self.assertEqual(self.read_history("sqlite:3")["status"], "blocked")
        self.assertEqual(self.read_history("sqlite:2")["state"], {"marker": "changed"})

    def test_history_write_failure_rolls_back_current_update(self) -> None:
        self.create()
        database = self.root / "workflow-state.sqlite3"
        with sqlite3.connect(database) as connection:
            connection.execute(
                "CREATE TRIGGER reject_revision_two "
                "BEFORE INSERT ON workflow_state_history "
                "WHEN NEW.provider_revision = 2 "
                "BEGIN SELECT RAISE(ABORT,'injected history failure'); END"
            )
        result = self.update()
        self.assertEqual(result["status"], "blocked", result)
        self.assertEqual(
            artifact_graph.read_sqlite_workflow_state(self.root, REF)["state"],
            {"marker": "initial"},
        )
        self.assertEqual(self.read_history("sqlite:2")["status"], "blocked")

    def test_divergent_history_blocks_read_and_update(self) -> None:
        self.create()
        database = self.root / "workflow-state.sqlite3"
        with sqlite3.connect(database) as connection:
            connection.execute(
                "UPDATE workflow_state_history SET envelope_json=? "
                "WHERE workflow_ref=? AND provider_revision=1",
                ('{"schema_version":"1","workflow_ref":"bad","state":{}}', REF),
            )
        current = artifact_graph.read_sqlite_workflow_state(self.root, REF)
        self.assertEqual(
            current,
            {"status": "blocked", "reason": "workflow_state_history_mismatch"},
        )
        self.assertEqual(self.read_history("sqlite:1")["status"], "blocked")
        self.assertEqual(self.update()["status"], "blocked")
        with sqlite3.connect(database) as connection:
            revision = connection.execute(
                "SELECT provider_revision FROM workflow_state WHERE workflow_ref=?",
                (REF,),
            ).fetchone()[0]
        self.assertEqual(revision, 1)

    def test_legacy_database_does_not_fabricate_missing_earlier_revisions(self) -> None:
        self.root.mkdir(parents=True)
        database = self.root / "workflow-state.sqlite3"
        with sqlite3.connect(database) as connection:
            connection.execute(
                "CREATE TABLE workflow_state("
                "workflow_ref TEXT PRIMARY KEY,envelope_json TEXT NOT NULL,"
                "provider_revision INTEGER NOT NULL CHECK(provider_revision > 0))"
            )
            envelope = {
                "workflow_ref": REF,
                "schema_version": "1",
                "state": {"marker": "legacy"},
            }
            connection.execute(
                "INSERT INTO workflow_state VALUES(?,?,3)",
                (REF, json.dumps(envelope, sort_keys=True, separators=(",", ":"))),
            )
        first = artifact_graph.read_sqlite_workflow_state(self.root, REF)
        self.assertEqual(first["status"], "current", first)
        self.assertFalse(first["historical_revision_available"])
        self.assertEqual(self.read_history("sqlite:1")["status"], "blocked")
        self.assertEqual(self.read_history("sqlite:3")["status"], "blocked")
        latest = self.update("sqlite:3", "after-migration")
        self.assertEqual(latest["status"], "written", latest)
        self.assertFalse(latest["historical_revision_available"])
        self.assertEqual(self.read_history("sqlite:3")["state"], {"marker": "legacy"})
        self.assertEqual(
            self.read_history("sqlite:4")["state"], {"marker": "after-migration"}
        )
        self.assertEqual(self.read_history("sqlite:1")["status"], "blocked")

    def test_separate_workflow_history_remains_isolated(self) -> None:
        self.create()
        self.create(OTHER)
        self.assertEqual(self.update()["status"], "written")
        self.assertEqual(self.read_history("sqlite:2", OTHER)["status"], "blocked")
        self.assertEqual(
            self.read_history("sqlite:1", OTHER)["state"], {"marker": "initial"}
        )

    def test_history_with_invalid_json_is_not_reused(self) -> None:
        self.create()
        database = self.root / "workflow-state.sqlite3"
        with sqlite3.connect(database) as connection:
            connection.execute(
                "UPDATE workflow_state_history SET envelope_json=? "
                "WHERE workflow_ref=? AND provider_revision=1",
                ("{not json", REF),
            )
        self.assertEqual(self.read_history("sqlite:1")["status"], "blocked")
        self.assertEqual(self.update()["status"], "blocked")


if __name__ == "__main__":
    unittest.main()
