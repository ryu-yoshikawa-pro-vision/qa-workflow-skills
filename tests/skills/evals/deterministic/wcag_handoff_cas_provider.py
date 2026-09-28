"""Test-only SQLite provider for the canonical WCAG handoff E2E contract."""
from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any


class SQLiteHandoffCASProvider:
    def __init__(self, path: str | Path):
        self.path = str(path)
        with closing(self._connect()) as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS workflow_state (
                    workflow_ref TEXT PRIMARY KEY,
                    payload TEXT NOT NULL,
                    revision INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS reservations (
                    resource_ref TEXT PRIMARY KEY,
                    owner_workflow_ref TEXT,
                    revision INTEGER NOT NULL,
                    status TEXT NOT NULL
                );
                """
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=15, isolation_level=None)
        connection.execute("PRAGMA busy_timeout=15000")
        return connection

    @staticmethod
    def _encode(value: dict[str, Any]) -> str:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    def create_state(self, workflow_ref: str, state: dict[str, Any]) -> dict[str, Any]:
        with closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT payload, revision FROM workflow_state WHERE workflow_ref=?", (workflow_ref,)
            ).fetchone()
            if row:
                connection.execute("COMMIT")
                return {"status": "exists", "state": json.loads(row[0]), "revision": row[1]}
            connection.execute(
                "INSERT INTO workflow_state(workflow_ref,payload,revision) VALUES(?,?,1)",
                (workflow_ref, self._encode(state)),
            )
            connection.execute("COMMIT")
            return {"status": "created", "state": state, "revision": 1}

    def read_state(self, workflow_ref: str) -> dict[str, Any] | None:
        with closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT payload, revision FROM workflow_state WHERE workflow_ref=?", (workflow_ref,)
            ).fetchone()
        if not row:
            return None
        return {"state": json.loads(row[0]), "revision": row[1]}

    def compare_and_set_state(self, workflow_ref: str, expected_revision: int,
                              state: dict[str, Any]) -> dict[str, Any]:
        with closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            cursor = connection.execute(
                "UPDATE workflow_state SET payload=?, revision=revision+1 "
                "WHERE workflow_ref=? AND revision=?",
                (self._encode(state), workflow_ref, expected_revision),
            )
            if cursor.rowcount != 1:
                connection.execute("ROLLBACK")
                current = connection.execute(
                    "SELECT revision FROM workflow_state WHERE workflow_ref=?", (workflow_ref,)
                ).fetchone()
                return {"status": "conflict", "current_revision": current[0] if current else None}
            connection.execute("COMMIT")
            return {"status": "written", "revision": expected_revision + 1, "state": state}

    def acquire_reservation(self, resource_ref: str, workflow_ref: str) -> dict[str, Any]:
        with closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT owner_workflow_ref, revision, status FROM reservations WHERE resource_ref=?",
                (resource_ref,),
            ).fetchone()
            if row and row[2] == "reserved":
                connection.execute("COMMIT")
                return {"status": "conflict", "owner_workflow_ref": row[0], "revision": row[1]}
            revision = (row[1] + 1) if row else 1
            connection.execute(
                "INSERT INTO reservations(resource_ref,owner_workflow_ref,revision,status) VALUES(?,?,?,?) "
                "ON CONFLICT(resource_ref) DO UPDATE SET owner_workflow_ref=excluded.owner_workflow_ref, "
                "revision=excluded.revision, status=excluded.status",
                (resource_ref, workflow_ref, revision, "reserved"),
            )
            connection.execute("COMMIT")
        return {"status": "reserved", "reservation_ref": f"sqlite:{resource_ref}",
                "owner_workflow_ref": workflow_ref, "revision": revision}

    def release_reservation(self, resource_ref: str, workflow_ref: str,
                            expected_revision: int) -> dict[str, Any]:
        with closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT owner_workflow_ref, revision, status FROM reservations WHERE resource_ref=?",
                (resource_ref,),
            ).fetchone()
            if not row or row != (workflow_ref, expected_revision, "reserved"):
                connection.execute("ROLLBACK")
                return {"status": "conflict", "current": row}
            connection.execute(
                "UPDATE reservations SET owner_workflow_ref=NULL, revision=revision+1, status='released' "
                "WHERE resource_ref=? AND owner_workflow_ref=? AND revision=?",
                (resource_ref, workflow_ref, expected_revision),
            )
            connection.execute("COMMIT")
        return {"status": "released", "revision": expected_revision + 1}
