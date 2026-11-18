"""Local SQLite provider for Project Context and feature-inventory artifacts.

The trusted host selects an explicitly authorized local root and supplies a real
authorization callback. Neither JSON inputs nor approval_ref strings grant access.
The SQLite transaction provides native create-if-absent and revision CAS.
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import stat
from collections.abc import Mapping
from contextlib import closing
from pathlib import Path
from typing import Any, Callable

KINDS = frozenset({"project-context", "feature-inventory"})
MAX_BYTES = 16 * 1024 * 1024
MAX_REF = 1024
DB_DIR = ".qa-context-feature"
DB_FILE = "artifacts.sqlite3"
Authorization = Callable[[dict[str, str | None]], bool]
# gated: 信頼済みauthorize callbackが操作ごとに承認を判定する（既定）。
# user-confirmed: 呼出し元が明示的に渡した確認記録との完全一致で判定する。
GATED = "gated"
USER_CONFIRMED = "user-confirmed"
CONFIRMATION_MODES = frozenset({GATED, USER_CONFIRMED})
CONFIRMABLE_OPERATIONS = frozenset({"read", "write", "reclassify"})


class StoreError(ValueError):
    pass


def _confirmation_mode(confirmation: Any, authorize: Any) -> str:
    if not isinstance(confirmation, str) or confirmation not in CONFIRMATION_MODES:
        raise StoreError("confirmation_mode_invalid")
    # None は「callbackを渡していない」ことを表す。渡された callback と確認記録は併用しない。
    if confirmation == USER_CONFIRMED and authorize is not None:
        raise StoreError("confirmation_mode_conflict")
    return confirmation


def _canonical_request(request: Any) -> str | None:
    try:
        return json.dumps(
            request,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError):
        return None


class UserConfirmationMixin:
    """user-confirmed モードの確認記録と照合を両providerで共有する。

    確認記録は「ユーザーが当該操作を明示的に確認した」というホストの自己申告であり、
    認証ではない。ホストはユーザーが当該成果物を明示的に確認した後にだけ
    record_user_confirmation を呼ぶこと。AIが確認前に呼んではならない。
    """

    confirmation: str
    authorize: Any

    def _init_confirmation(self, confirmation: Any, authorize: Any) -> None:
        mode = _confirmation_mode(confirmation, authorize)
        self.confirmation = mode
        if mode == GATED:
            if not callable(authorize):
                raise StoreError("trusted_authorizer_required")
            self.authorize = authorize
            return
        self._confirmations: set[str] = set()
        self._confirmed_projects: set[str] = set()
        self.authorize = self._confirmed_authorize

    def record_user_confirmation(self, authorization: Mapping[str, Any]) -> None:
        """ユーザー確認済みの操作レコードを登録する。登録済みの完全一致だけを許可する。

        authorization は、gatedモードでcallbackに渡される要求と同じキーを持つdict。
        write は operation, kind, project_ref, artifact_ref, expected_revision, sha256,
        source_ref, source_revision, approval_ref, approval_revision, operation_id,
        change_reason を持つ。reclassify は feature_registry が authorize に渡す決定dict
        そのものを使う。どの operation の確認記録でも、登録された案件の読取scopeが開く。書込み後の独立readbackはこの挙動に依存する。read の記録は案件scopeだけを登録し、読取の個別承認にはならず、書込みを許可しない。
        """
        if self.confirmation != USER_CONFIRMED:
            raise StoreError("confirmation_mode_required")
        if not isinstance(authorization, dict):
            raise StoreError("confirmation_record_invalid")
        operation = authorization.get("operation")
        project = authorization.get("project_ref")
        if operation not in CONFIRMABLE_OPERATIONS or not isinstance(project, str):
            raise StoreError("confirmation_record_invalid")
        _name(project, "project_ref")
        canonical = _canonical_request(authorization)
        if canonical is None:
            raise StoreError("confirmation_record_invalid")
        self._confirmed_projects.add(project)
        if operation != "read":
            self._confirmations.add(canonical)

    def _confirmed_authorize(self, request: Any) -> bool:
        """user-confirmed時の authorize。確認記録と完全一致した書込み／再分類だけ True。

        読取は登録済み案件scope内なら確認記録なしで True（他案件・未登録案件は False）。
        """
        if not isinstance(request, dict):
            return False
        if request.get("operation") == "read":
            project = request.get("project_ref")
            return isinstance(project, str) and project in self._confirmed_projects
        canonical = _canonical_request(request)
        return canonical is not None and canonical in self._confirmations


def _name(value: Any, label: str) -> str:
    if (
        not isinstance(value, str)
        or not value.strip()
        or len(value) > MAX_REF
        or any(ord(ch) < 32 or ord(ch) == 127 for ch in value)
    ):
        raise StoreError(f"{label}_invalid")
    return value


def _check_root(root: Path, authorized_root: Path) -> Path:
    root = Path(root)
    authorized_root = Path(authorized_root)
    if not root.is_absolute() or not authorized_root.is_absolute():
        raise StoreError("absolute_authorized_root_required")
    # Do not silently resolve a symlink to an unrelated authorized location.
    for candidate in (root, *root.parents, authorized_root, *authorized_root.parents):
        if candidate.is_symlink():
            raise StoreError("root_symlink_rejected")
    resolved = root.resolve(strict=True)
    if resolved != authorized_root.resolve(strict=True) or not resolved.is_dir():
        raise StoreError("unauthorized_root")
    return resolved


class LocalArtifactStore(UserConfirmationMixin):
    """Provider-native SQLite CAS; not a substitute for an unselected remote store."""

    def __init__(
        self,
        root: Path,
        authorized_root: Path,
        authorize: Authorization | None,
        *,
        confirmation: str = GATED,
    ) -> None:
        self.root = _check_root(root, authorized_root)
        self._init_confirmation(confirmation, authorize)
        directory = self.root / DB_DIR
        try:
            directory.mkdir(mode=0o700, exist_ok=True)
        except OSError as exc:
            raise StoreError("store_directory_unavailable") from exc
        if directory.is_symlink() or not directory.is_dir():
            raise StoreError("store_directory_symlink_or_missing")
        if os.name == "posix" and stat.S_IMODE(directory.stat().st_mode) & 0o077:
            raise StoreError("store_directory_permissions_unsafe")
        self.path = directory / DB_FILE
        if self.path.is_symlink():
            raise StoreError("store_file_symlink_rejected")
        if not self.path.exists():
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
            if hasattr(os, "O_NOFOLLOW"):
                flags |= os.O_NOFOLLOW
            try:
                fd = os.open(self.path, flags, 0o600)
            except FileExistsError:
                pass
            except OSError as exc:
                raise StoreError("store_file_unavailable") from exc
            else:
                os.close(fd)
        if self.path.is_symlink() or not self.path.is_file():
            raise StoreError("store_file_invalid")
        if os.name == "posix" and stat.S_IMODE(self.path.stat().st_mode) & 0o077:
            raise StoreError("store_file_permissions_unsafe")
        with closing(self._connect()) as conn, conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS artifact_revisions (
                    kind TEXT NOT NULL,
                    project_ref TEXT NOT NULL,
                    artifact_ref TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    content BLOB NOT NULL,
                    digest TEXT NOT NULL,
                    previous_version INTEGER,
                    source_ref TEXT NOT NULL,
                    source_revision TEXT NOT NULL,
                    approval_ref TEXT NOT NULL,
                    approval_revision TEXT NOT NULL,
                    change_reason TEXT NOT NULL,
                    PRIMARY KEY (kind, project_ref, artifact_ref, version)
                );
                CREATE TABLE IF NOT EXISTS artifact_current (
                    kind TEXT NOT NULL,
                    project_ref TEXT NOT NULL,
                    artifact_ref TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    PRIMARY KEY (kind, project_ref, artifact_ref)
                );
                CREATE TABLE IF NOT EXISTS artifact_receipts (
                    kind TEXT NOT NULL,
                    project_ref TEXT NOT NULL,
                    artifact_ref TEXT NOT NULL,
                    operation_id TEXT NOT NULL,
                    fingerprint TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    PRIMARY KEY (kind, project_ref, artifact_ref, operation_id)
                );
                """
            )

    def _connect(self) -> sqlite3.Connection:
        if self.path.is_symlink() or not self.path.is_file():
            raise StoreError("store_file_changed")
        conn = sqlite3.connect(self.path, timeout=5, isolation_level=None)
        conn.execute("PRAGMA busy_timeout=5000")
        return conn

    @staticmethod
    def _key(kind: str, project_ref: str, artifact_ref: str) -> tuple[str, str, str]:
        if kind not in KINDS:
            raise StoreError("artifact_kind_invalid")
        return (
            kind,
            _name(project_ref, "project_ref"),
            _name(artifact_ref, "artifact_ref"),
        )

    def _authorized(self, request: dict[str, str | None]) -> None:
        try:
            permitted = self.authorize(request)
        except Exception as exc:
            raise StoreError("approval_provider_unavailable") from exc
        if permitted is not True:
            raise StoreError("access_denied")

    def read_revision(
        self, kind: str, project_ref: str, artifact_ref: str, revision: str
    ) -> dict[str, Any] | None:
        key = self._key(kind, project_ref, artifact_ref)
        self._authorized(
            {
                "operation": "read",
                "kind": kind,
                "project_ref": project_ref,
                "artifact_ref": artifact_ref,
                "expected_revision": revision,
                "approval_ref": None,
            }
        )
        if (
            not isinstance(revision, str)
            or not revision.startswith("r")
            or not revision[1:].isdigit()
        ):
            raise StoreError("revision_invalid")
        with closing(self._connect()) as conn, conn:
            row = conn.execute(
                """SELECT content, digest, previous_version, source_ref, source_revision,
                          approval_ref, approval_revision, change_reason
                   FROM artifact_revisions
                   WHERE kind=? AND project_ref=? AND artifact_ref=? AND version=?""",
                (*key, int(revision[1:])),
            ).fetchone()
        if row is None:
            return None
        (
            content,
            digest,
            previous,
            source_ref,
            source_revision,
            approval_ref,
            approval_revision,
            reason,
        ) = row
        if hashlib.sha256(content).hexdigest() != digest:
            raise StoreError("artifact_readback_hash_mismatch")
        try:
            decoded = content.decode("utf-8")
        except UnicodeError as exc:
            raise StoreError("artifact_readback_encoding_invalid") from exc
        return {
            "kind": kind,
            "project_ref": project_ref,
            "artifact_ref": artifact_ref,
            "revision": revision,
            "previous_revision": f"r{previous}" if previous is not None else None,
            "sha256": digest,
            "content": decoded,
            "source_ref": source_ref,
            "source_revision": source_revision,
            "approval_ref": approval_ref,
            "approval_revision": approval_revision,
            "change_reason": reason,
        }

    def read_current(
        self, kind: str, project_ref: str, artifact_ref: str
    ) -> dict[str, Any] | None:
        key = self._key(kind, project_ref, artifact_ref)
        self._authorized(
            {
                "operation": "read",
                "kind": kind,
                "project_ref": project_ref,
                "artifact_ref": artifact_ref,
                "expected_revision": None,
                "approval_ref": None,
            }
        )
        with closing(self._connect()) as conn, conn:
            row = conn.execute(
                """SELECT version FROM artifact_current
                   WHERE kind=? AND project_ref=? AND artifact_ref=?""",
                key,
            ).fetchone()
        if row is None:
            return None
        current = self.read_revision(*key, f"r{row[0]}")
        if current is None:
            raise StoreError("current_revision_missing")
        return current

    def write(
        self,
        *,
        kind: str,
        project_ref: str,
        artifact_ref: str,
        content: str,
        expected_revision: str | None,
        operation_id: str,
        source_ref: str,
        source_revision: str,
        approval_ref: str,
        approval_revision: str,
        change_reason: str,
    ) -> dict[str, Any]:
        key = self._key(kind, project_ref, artifact_ref)
        operation_id = _name(operation_id, "operation_id")
        source_ref = _name(source_ref, "source_ref")
        source_revision = _name(source_revision, "source_revision")
        approval_ref = _name(approval_ref, "approval_ref")
        approval_revision = _name(approval_revision, "approval_revision")
        change_reason = _name(change_reason, "change_reason")
        if expected_revision is not None:
            _name(expected_revision, "expected_revision")
        if not isinstance(content, str):
            raise StoreError("artifact_content_invalid")
        payload = content.encode("utf-8")
        if len(payload) > MAX_BYTES:
            raise StoreError("artifact_content_too_large")
        digest = hashlib.sha256(payload).hexdigest()
        fingerprint = hashlib.sha256(
            json.dumps(
                [
                    key,
                    expected_revision,
                    operation_id,
                    digest,
                    source_ref,
                    source_revision,
                    approval_ref,
                    approval_revision,
                    change_reason,
                ],
                ensure_ascii=False,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        approval_request: dict[str, str | None] = {
            "operation": "write",
            "kind": kind,
            "project_ref": project_ref,
            "artifact_ref": artifact_ref,
            "expected_revision": expected_revision,
            "sha256": digest,
            "source_ref": source_ref,
            "source_revision": source_revision,
            "approval_ref": approval_ref,
            "approval_revision": approval_revision,
        }
        # user-confirmed の確認記録は操作単位で照合するため、冪等キーと変更理由も含める。
        # gatedモードのcallbackへ渡す要求の形は変えない。
        authorization = dict(approval_request)
        if self.confirmation == USER_CONFIRMED:
            authorization.update(operation_id=operation_id, change_reason=change_reason)
        try:
            with closing(self._connect()) as conn, conn:
                conn.execute("BEGIN IMMEDIATE")
                self._authorized(authorization)
                receipt = conn.execute(
                    """SELECT fingerprint, version FROM artifact_receipts
                       WHERE kind=? AND project_ref=? AND artifact_ref=?
                             AND operation_id=?""",
                    (*key, operation_id),
                ).fetchone()
                if receipt is not None:
                    if receipt[0] != fingerprint:
                        raise StoreError("operation_id_reused")
                    version = int(receipt[1])
                    idempotent = True
                else:
                    current = conn.execute(
                        """SELECT version FROM artifact_current
                           WHERE kind=? AND project_ref=? AND artifact_ref=?""",
                        key,
                    ).fetchone()
                    if expected_revision is None:
                        if current is not None:
                            raise StoreError("create_if_absent_conflict")
                        version = 1
                        old_version = None
                    else:
                        if current is None or expected_revision != f"r{current[0]}":
                            raise StoreError("revision_conflict")
                        old_version = int(current[0])
                        version = old_version + 1
                    conn.execute(
                        """INSERT INTO artifact_revisions
                           (kind, project_ref, artifact_ref, version, content, digest,
                            previous_version, source_ref, source_revision, approval_ref,
                            approval_revision, change_reason)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            *key,
                            version,
                            payload,
                            digest,
                            old_version,
                            source_ref,
                            source_revision,
                            approval_ref,
                            approval_revision,
                            change_reason,
                        ),
                    )
                    conn.execute(
                        """INSERT INTO artifact_current (kind, project_ref, artifact_ref, version)
                           VALUES (?, ?, ?, ?)
                           ON CONFLICT(kind, project_ref, artifact_ref)
                           DO UPDATE SET version=excluded.version""",
                        (*key, version),
                    )
                    conn.execute(
                        """INSERT INTO artifact_receipts
                           (kind, project_ref, artifact_ref, operation_id, fingerprint, version)
                           VALUES (?, ?, ?, ?, ?, ?)""",
                        (*key, operation_id, fingerprint, version),
                    )
                    idempotent = False
        except sqlite3.Error as exc:
            raise StoreError("sqlite_write_failed") from exc
        # A new provider read is mandatory, not the in-memory INSERT result.
        recorded = self.read_current(*key)
        history = self.read_revision(*key, f"r{version}")
        if (
            recorded is None
            or history is None
            or (not idempotent and recorded["revision"] != f"r{version}")
            or history["sha256"] != digest
            or history["content"] != content
        ):
            raise StoreError("independent_readback_mismatch")
        return {
            "status": (
                "superseded"
                if idempotent and recorded["revision"] != f"r{version}"
                else "idempotent"
                if idempotent
                else "stored"
            ),
            "artifact_ref": artifact_ref,
            "revision": history["revision"],
            "previous_revision": history["previous_revision"],
            "sha256": digest,
            "source_revision": source_revision,
            "approval_ref": approval_ref,
        }
