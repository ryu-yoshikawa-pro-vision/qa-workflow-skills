"""Local directory persistence for the three context artifact kinds.

The caller supplies an already-authorized local root. This helper uses ordinary
filesystem permissions, atomic file operations, and per-file OS locks; it does
not select a provider, authenticate a principal, or claim cross-host CAS.
"""

from __future__ import annotations

import errno
import hashlib
import json
import os
import re
import stat
import sys
import tempfile
from pathlib import Path
from typing import Any

import context_artifacts as contracts

MAX_REQUEST_BYTES = contracts.MAX_ARTIFACT_BYTES + 1024 * 1024
_REVISION_RE = re.compile(r"^file-v1-[0-9a-f]{1,16}-[0-9a-f]{1,16}$")
_LOCAL_FILESYSTEMS = {
    "ext2",
    "ext3",
    "ext4",
    "xfs",
    "btrfs",
    "zfs",
    "tmpfs",
    "overlay",
    "f2fs",
}


class StoreError(ValueError):
    """A directory-store operation could not be completed safely."""


def _fail(code: str) -> None:
    raise StoreError(code)


def _revision(info: os.stat_result) -> str:
    return f"file-v1-{info.st_dev:x}-{info.st_ino:x}"


def _root_binding(root: Path) -> str:
    info = root.stat()
    material = f"context-artifact-root-v1:{info.st_dev:x}:{info.st_ino:x}".encode(
        "ascii"
    )
    return hashlib.sha256(material).hexdigest()


def _supports_local_conditioned_update(root: Path) -> bool:
    if os.name == "nt":
        try:
            import ctypes

            return ctypes.windll.kernel32.GetDriveTypeW(root.anchor) == 3
        except (AttributeError, OSError):
            return False
    mounts = Path("/proc/self/mounts")
    try:
        candidates: list[tuple[int, str]] = []
        for line in mounts.read_text(encoding="utf-8", errors="replace").splitlines():
            fields = line.split()
            if len(fields) < 3:
                continue
            mount = Path(fields[1].replace("\\040", " ").replace("\\011", "\t"))
            try:
                root.relative_to(mount)
            except ValueError:
                continue
            candidates.append((len(str(mount)), fields[2].lower()))
        return bool(candidates) and max(candidates)[1] in _LOCAL_FILESYSTEMS
    except OSError:
        return False


def _lock(fd: int) -> None:
    if os.name == "nt":
        import msvcrt

        os.lseek(fd, 0, os.SEEK_SET)
        msvcrt.locking(fd, msvcrt.LK_LOCK, 1)
        return
    import fcntl

    fcntl.flock(fd, fcntl.LOCK_EX)


def _unlock(fd: int) -> None:
    if os.name == "nt":
        import msvcrt

        os.lseek(fd, 0, os.SEEK_SET)
        msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
        return
    import fcntl

    fcntl.flock(fd, fcntl.LOCK_UN)


class DirectoryArtifactStore:
    """Store context artifacts under an explicit, local directory root.

    A stable ``<kind>/<identity>.json`` path holds the current canonical bytes.
    Older file revisions are retained under that kind's hidden ``.history``
    directory. The revision is the filesystem object identity, separate from the
    artifact content hash. Writers using this helper serialize updates to the
    same artifact with an OS lock on its current file; that guarantee is local to
    one host and is not a distributed lock.
    """

    def __init__(self, root: str | os.PathLike[str]) -> None:
        value = Path(root)
        if not value.is_absolute():
            _fail("root_must_be_absolute")
        try:
            self.root = value.resolve(strict=True)
        except OSError as exc:
            raise StoreError("root_unavailable") from exc
        if not self.root.is_dir():
            _fail("root_must_be_directory")
        if os.name == "nt" and str(self.root).startswith("\\\\"):
            _fail("network_root_unsupported")
        self.root_binding = _root_binding(self.root)
        self.supports_local_conditioned_update = _supports_local_conditioned_update(
            self.root
        )

    def _kind_dir(self, kind: str, *, create: bool = False) -> Path:
        if kind not in contracts.KINDS:
            _fail("artifact_kind_invalid")
        path = self.root / kind
        if create:
            try:
                path.mkdir(mode=0o700, exist_ok=True)
            except OSError as exc:
                raise StoreError("kind_directory_unavailable") from exc
        try:
            info = path.lstat()
        except FileNotFoundError:
            return path
        except OSError as exc:
            raise StoreError("kind_directory_unavailable") from exc
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
            _fail("kind_directory_not_regular")
        return path

    def _ref_path(self, ref: str, *, create: bool = False) -> tuple[str, str, Path]:
        if not isinstance(ref, str) or ref.count("/") != 1:
            _fail("artifact_ref_invalid")
        kind, leaf = ref.split("/", 1)
        if not leaf.endswith(".json"):
            _fail("artifact_ref_invalid")
        identity = leaf[:-5]
        canonical_ref = contracts.artifact_ref(kind, identity)
        if canonical_ref != ref:
            _fail("artifact_ref_invalid")
        return kind, identity, self._kind_dir(kind, create=create) / leaf

    def _history_dir(self, kind_dir: Path, identity: str, *, create: bool) -> Path:
        history_root = kind_dir / ".history"
        identity_dir = history_root / identity
        if create:
            try:
                history_root.mkdir(mode=0o700, exist_ok=True)
                identity_dir.mkdir(mode=0o700, exist_ok=True)
            except OSError as exc:
                raise StoreError("history_directory_unavailable") from exc
        for path in (history_root, identity_dir):
            try:
                info = path.lstat()
            except FileNotFoundError:
                return identity_dir
            except OSError as exc:
                raise StoreError("history_directory_unavailable") from exc
            if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
                _fail("history_directory_not_regular")
        return identity_dir

    @staticmethod
    def _open_regular(path: Path, flags: int) -> int:
        before = path.lstat()
        if stat.S_ISLNK(before.st_mode) or not stat.S_ISREG(before.st_mode):
            _fail("artifact_not_regular_file")
        nofollow = getattr(os, "O_NOFOLLOW", 0)
        try:
            fd = os.open(path, flags | nofollow)
            info = os.fstat(fd)
            after = path.lstat()
            if (
                not stat.S_ISREG(info.st_mode)
                or (before.st_dev, before.st_ino) != (info.st_dev, info.st_ino)
                or (after.st_dev, after.st_ino) != (info.st_dev, info.st_ino)
                or stat.S_ISLNK(after.st_mode)
            ):
                os.close(fd)
                _fail("artifact_changed_during_open")
            return fd
        except OSError as exc:
            if exc.errno == errno.ELOOP:
                raise StoreError("artifact_symlink_unsupported") from exc
            raise

    @staticmethod
    def _read_fd(fd: int) -> bytes:
        os.lseek(fd, 0, os.SEEK_SET)
        chunks: list[bytes] = []
        remaining = contracts.MAX_ARTIFACT_BYTES + 1
        while remaining:
            chunk = os.read(fd, min(1024 * 1024, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        data = b"".join(chunks)
        if len(data) > contracts.MAX_ARTIFACT_BYTES:
            _fail("artifact_content_too_large")
        return data

    def _read_path(
        self, path: Path, kind: str, ref: str, *, revision: str | None = None
    ) -> dict[str, Any]:
        fd = self._open_regular(path, os.O_RDONLY)
        try:
            info = os.fstat(fd)
            actual_revision = _revision(info)
            if revision is not None and revision != actual_revision:
                _fail("historical_revision_mismatch")
            data = self._read_fd(fd)
        finally:
            os.close(fd)
        artifact = contracts.parse_canonical_json(data)
        contracts.validate_artifact(artifact, kind)
        if artifact["artifact_ref"] != ref:
            _fail("artifact_ref_mismatch")
        return {
            "kind": kind,
            "root_binding": self.root_binding,
            "artifact_ref": ref,
            "revision": actual_revision,
            "sha256": hashlib.sha256(data).hexdigest(),
            "content": data.decode("utf-8", "strict"),
        }

    def read(self, ref: str, revision: str | None = None) -> dict[str, Any]:
        kind, identity, current_path = self._ref_path(ref)
        if revision is None:
            return self._read_path(current_path, kind, ref)
        if not isinstance(revision, str) or not _REVISION_RE.fullmatch(revision):
            _fail("revision_invalid")
        try:
            current = self._read_path(current_path, kind, ref)
        except FileNotFoundError:
            current = None
        if current is not None and current["revision"] == revision:
            return current
        kind_dir = current_path.parent
        history_dir = self._history_dir(kind_dir, identity, create=False)
        historical_path = history_dir / f"{revision}.json"
        return self._read_path(historical_path, kind, ref, revision=revision)

    def history(self, ref: str) -> list[dict[str, Any]]:
        kind, identity, current_path = self._ref_path(ref)
        kind_dir = current_path.parent
        history_dir = self._history_dir(kind_dir, identity, create=False)
        entries: dict[str, dict[str, Any]] = {}
        try:
            children = list(history_dir.iterdir())
        except FileNotFoundError:
            children = []
        except OSError as exc:
            raise StoreError("history_read_failed") from exc
        for path in children:
            if path.is_symlink() or not path.is_file():
                _fail("history_entry_not_regular")
            revision = path.name[:-5] if path.name.endswith(".json") else ""
            if not _REVISION_RE.fullmatch(revision):
                _fail("history_entry_invalid")
            readback = self._read_path(path, kind, ref, revision=revision)
            entries[revision] = {
                "artifact_ref": ref,
                "revision": revision,
                "sha256": readback["sha256"],
                "current": False,
            }
        try:
            current = self._read_path(current_path, kind, ref)
        except FileNotFoundError:
            current = None
        if current is not None:
            entries[current["revision"]] = {
                "artifact_ref": ref,
                "revision": current["revision"],
                "sha256": current["sha256"],
                "current": True,
            }
        return [entries[key] for key in sorted(entries)]

    def list(self, kind: str) -> dict[str, Any]:
        kind_dir = self._kind_dir(kind)
        try:
            children = list(kind_dir.iterdir()) if kind_dir.exists() else []
        except OSError as exc:
            raise StoreError("kind_listing_failed") from exc
        artifacts: list[dict[str, Any]] = []
        for path in sorted(children, key=lambda item: item.name):
            if path.name.startswith("."):
                continue
            if (
                path.is_symlink()
                or not path.is_file()
                or not path.name.endswith(".json")
            ):
                _fail("kind_entry_not_regular_artifact")
            ref = f"{kind}/{path.name}"
            readback = self.read(ref)
            artifacts.append(
                {
                    "artifact_ref": ref,
                    "revision": readback["revision"],
                    "sha256": readback["sha256"],
                }
            )
        return {
            "status": "complete",
            "root_binding": self.root_binding,
            "kind": kind,
            "artifacts": artifacts,
        }

    @staticmethod
    def _write_temp(directory: Path, identity: str, data: bytes) -> Path:
        fd, raw_path = tempfile.mkstemp(
            prefix=f".{identity}.", suffix=".tmp", dir=directory
        )
        path = Path(raw_path)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
        except OSError:
            path.unlink(missing_ok=True)
            raise
        return path

    @staticmethod
    def _sync_dir(path: Path) -> None:
        if os.name == "nt":
            return
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(fd)
        finally:
            os.close(fd)

    def _readback_or_none(
        self, path: Path, kind: str, ref: str
    ) -> dict[str, Any] | None:
        try:
            return self._read_path(path, kind, ref)
        except FileNotFoundError:
            return None

    def _create_if_absent(
        self, current_path: Path, kind: str, identity: str, ref: str, data: bytes
    ) -> dict[str, Any]:
        existing = self._readback_or_none(current_path, kind, ref)
        if existing is not None:
            if existing["content"].encode("utf-8") == data:
                return {"status": "reused", "readback": existing}
            return {"status": "conflict", "reason": "artifact_already_exists"}
        temp_path = self._write_temp(current_path.parent, identity, data)
        try:
            try:
                os.link(temp_path, current_path, follow_symlinks=False)
            except FileExistsError:
                existing = self._read_path(current_path, kind, ref)
                if existing["content"].encode("utf-8") == data:
                    return {"status": "reused", "readback": existing}
                return {"status": "conflict", "reason": "artifact_already_exists"}
            except OSError as exc:
                raise StoreError("atomic_create_unavailable") from exc
            self._sync_dir(current_path.parent)
        finally:
            temp_path.unlink(missing_ok=True)
        readback = self.read(ref)
        if readback["content"].encode("utf-8") != data:
            _fail("independent_readback_mismatch")
        return {"status": "stored", "readback": readback}

    def _archive_current(
        self, current_path: Path, kind_dir: Path, identity: str, revision: str, fd: int
    ) -> None:
        history_dir = self._history_dir(kind_dir, identity, create=True)
        history_path = history_dir / f"{revision}.json"
        try:
            os.link(current_path, history_path, follow_symlinks=False)
        except FileExistsError:
            history = self._read_path(
                history_path,
                current_path.parent.name,
                f"{current_path.parent.name}/{current_path.name}",
                revision=revision,
            )
            current_bytes = self._read_fd(fd)
            if history["content"].encode("utf-8") != current_bytes:
                _fail("history_revision_conflict")
        except OSError as exc:
            raise StoreError("history_link_unavailable") from exc
        history_info = os.stat(history_path, follow_symlinks=False)
        current_info = os.fstat(fd)
        if (history_info.st_dev, history_info.st_ino) != (
            current_info.st_dev,
            current_info.st_ino,
        ):
            _fail("history_revision_mismatch")
        self._sync_dir(history_dir)

    def write(
        self,
        kind: str,
        artifact: Any,
        *,
        expected_revision: str | None = None,
    ) -> dict[str, Any]:
        if kind not in contracts.KINDS:
            _fail("artifact_kind_invalid")
        normalized = contracts.validate_artifact(artifact, kind)
        data = contracts.canonical_bytes(normalized)
        if len(data) > contracts.MAX_ARTIFACT_BYTES:
            _fail("artifact_content_too_large")
        ref = normalized["artifact_ref"]
        selected_kind, identity, current_path = self._ref_path(ref, create=True)
        if selected_kind != kind:
            _fail("artifact_kind_mismatch")
        if kind == "context-signal-batch":
            if expected_revision is not None:
                _fail("immutable_batch_cannot_be_updated")
            return self._create_if_absent(current_path, kind, identity, ref, data)
        if expected_revision is None:
            return self._create_if_absent(current_path, kind, identity, ref, data)
        if not self.supports_local_conditioned_update:
            _fail("conditional_update_requires_local_filesystem")
        if not isinstance(expected_revision, str) or not _REVISION_RE.fullmatch(
            expected_revision
        ):
            _fail("expected_revision_invalid")
        while True:
            try:
                fd = self._open_regular(current_path, os.O_RDONLY)
            except FileNotFoundError:
                return {"status": "conflict", "reason": "expected_revision_missing"}
            try:
                _lock(fd)
                opened = os.fstat(fd)
                try:
                    current_info = os.stat(current_path, follow_symlinks=False)
                except FileNotFoundError:
                    continue
                if (opened.st_dev, opened.st_ino) != (
                    current_info.st_dev,
                    current_info.st_ino,
                ):
                    continue
                old_revision = _revision(opened)
                old_data = self._read_fd(fd)
                old_artifact = contracts.parse_canonical_json(old_data)
                contracts.validate_artifact(old_artifact, kind)
                if old_artifact["artifact_ref"] != ref:
                    _fail("artifact_ref_mismatch")
                current_readback = {
                    "kind": kind,
                    "root_binding": self.root_binding,
                    "artifact_ref": ref,
                    "revision": old_revision,
                    "sha256": hashlib.sha256(old_data).hexdigest(),
                    "content": old_data.decode("utf-8", "strict"),
                }
                if old_revision != expected_revision:
                    return {
                        "status": "conflict",
                        "reason": "expected_revision_changed",
                        "current": current_readback,
                    }
                if old_data == data:
                    return {"status": "reused", "readback": current_readback}
                self._archive_current(
                    current_path,
                    current_path.parent,
                    identity,
                    old_revision,
                    fd,
                )
                temp_path = self._write_temp(current_path.parent, identity, data)
                temp_info = os.stat(temp_path, follow_symlinks=False)
                written_revision = _revision(temp_info)
                try:
                    latest = os.stat(current_path, follow_symlinks=False)
                    if (latest.st_dev, latest.st_ino) != (
                        opened.st_dev,
                        opened.st_ino,
                    ):
                        return {
                            "status": "conflict",
                            "reason": "current_revision_changed_before_replace",
                        }
                    os.replace(temp_path, current_path)
                    self._sync_dir(current_path.parent)
                finally:
                    temp_path.unlink(missing_ok=True)
                # Reopen the provider path/history after replacing the current
                # file. Another writer may already have advanced it; the history
                # link preserves this exact content for independent readback.
                readback = self.read(ref, written_revision)
                if readback["content"].encode("utf-8") != data:
                    _fail("independent_readback_mismatch")
                return {"status": "stored", "readback": readback}
            finally:
                try:
                    _unlock(fd)
                except OSError:
                    pass
                os.close(fd)


def handle(request: Any) -> dict[str, Any]:
    if not isinstance(request, dict):
        return {"status": "blocked", "reason": "request_must_be_object"}
    try:
        root = request.get("root")
        if not isinstance(root, str) or not root:
            _fail("root_required")
        store = DirectoryArtifactStore(root)
        operation = request.get("operation")
        if operation == "write":
            result = store.write(
                request.get("kind"),
                request.get("artifact"),
                expected_revision=request.get("expected_revision"),
            )
            return {"root_binding": store.root_binding, **result}
        if operation == "read":
            ref = request.get("artifact_ref")
            revision = request.get("revision")
            return {
                "status": "current",
                "readback": store.read(ref, revision),
            }
        if operation == "history":
            ref = request.get("artifact_ref")
            return {"status": "complete", "history": store.history(ref)}
        if operation == "list":
            return store.list(request.get("kind"))
        _fail("operation_invalid")
    except (StoreError, contracts.ContractError, OSError, ValueError, TypeError) as exc:
        reason = str(exc) or type(exc).__name__
        return {"status": "blocked", "reason": reason}


def _pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in items:
        if key in result:
            _fail("duplicate_json_key")
        result[key] = value
    return result


def _constant(_: str) -> Any:
    _fail("nonfinite_json_value")


def main() -> int:
    raw = sys.stdin.buffer.read(MAX_REQUEST_BYTES + 1)
    if len(raw) > MAX_REQUEST_BYTES:
        result = {"status": "blocked", "reason": "request_too_large"}
    else:
        try:
            request = json.loads(
                raw.decode("utf-8", "strict"),
                object_pairs_hook=_pairs,
                parse_constant=_constant,
            )
            result = handle(request)
        except (UnicodeError, json.JSONDecodeError, RecursionError, StoreError) as exc:
            result = {
                "status": "blocked",
                "reason": str(exc) or type(exc).__name__,
            }
    sys.stdout.write(
        json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
