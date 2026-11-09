"""Preflight and readback checks for isolated non-E2E testware edits.

This is an advisory read-only check, NOT an atomic commit operation. The final
publish must separately require a native expected-HEAD conditional update.
"""

from __future__ import annotations

import hashlib
from pathlib import PurePosixPath
from typing import Any


class SnapshotError(ValueError):
    pass


def _path(value: Any) -> str:
    if not isinstance(value, str) or not value or "\\" in value:
        raise SnapshotError("invalid_repo_path")
    parts = value.split("/")
    if (value.startswith("/") or ":" in parts[0]
            or any(part in {"", ".", ".."} for part in parts)
            or PurePosixPath(value).is_absolute()):
        raise SnapshotError("unsafe_repo_path")
    return value


def file_digest(contents: bytes | None) -> str | None:
    return None if contents is None else "sha256:" + hashlib.sha256(contents).hexdigest()


def check_snapshot(*, expected_head: str, actual_head: str,
                   tracked: dict[str, str | None], actual: dict[str, bytes | None],
                   allowed_prefixes: list[str], dirty_paths: list[str],
                   change_paths: list[str]) -> dict[str, Any]:
    """Check all edited paths, including shared config/lockfiles, before publish.

    Caller must read each path from a trusted worktree, rejecting symlinks and
    ensuring no intervening modifications, then publish with native CAS.
    """
    if not isinstance(expected_head, str) or not expected_head:
        raise SnapshotError("missing_expected_head")
    if not isinstance(actual_head, str) or not actual_head:
        raise SnapshotError("missing_actual_head")
    if not isinstance(allowed_prefixes, list) or not allowed_prefixes:
        raise SnapshotError("no_allowed_paths")
    prefixes = [_path(x).rstrip("/") for x in allowed_prefixes]
    changes = [_path(x) for x in change_paths]
    if not changes or len(set(changes)) != len(changes):
        raise SnapshotError("invalid_change_set")
    dirty = {_path(x) for x in dirty_paths}
    if not all(x in tracked and x in actual for x in changes):
        raise SnapshotError("incomplete_snapshot")
    out_of_scope = [p for p in changes if not any(
        p == prefix or p.startswith(prefix + "/") for prefix in prefixes)]
    conflicting_dirty = sorted(set(changes) & dirty)
    content_conflicts = []
    for p in changes:
        expected = tracked[p]
        if expected is not None and (not isinstance(expected, str)
                                     or not expected.startswith("sha256:")):
            raise SnapshotError("invalid_expected_digest")
        if actual[p] is not None and not isinstance(actual[p], bytes):
            raise SnapshotError("invalid_actual_contents")
        if file_digest(actual[p]) != expected:
            content_conflicts.append(p)
    reasons = []
    if actual_head != expected_head:
        reasons.append("head_changed")
    if out_of_scope:
        reasons.append("path_out_of_scope")
    if conflicting_dirty:
        reasons.append("dirty_target")
    if content_conflicts:
        reasons.append("file_changed")
    return {"safe_to_prepare": not reasons, "reasons": reasons,
            "content_conflicts": content_conflicts,
            "dirty_conflicts": conflicting_dirty, "out_of_scope": out_of_scope,
            "native_cas_publish_required": True}
