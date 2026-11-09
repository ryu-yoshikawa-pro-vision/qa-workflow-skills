"""Enumerate a complete local Git tree and optional commit-to-commit diff.

Read-only Git commands, exact authorized repository root and commit SHAs are
required. Paths and rename events are evidence, not semantic feature identities.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

SHA = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")
MAX_INPUT = 1024 * 1024
MAX_OUTPUT = 32 * 1024 * 1024
TIMEOUT = 60


class Invalid(ValueError):
    pass


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise Invalid("duplicate_json_key")
        result[key] = value
    return result


def _sha(value: Any, field: str) -> str:
    if not isinstance(value, str) or not SHA.fullmatch(value):
        raise Invalid(f"{field}_must_be_full_hex_commit")
    return value


def _git(root: Path, *args: str) -> bytes:
    try:
        # Spool Git output to disk so a large repository cannot exhaust RAM
        # before the output-size guard runs.
        with tempfile.TemporaryFile() as output:
            process = subprocess.run(
                ["git", "-C", str(root), *args],
                stdout=output,
                stderr=subprocess.DEVNULL,
                timeout=TIMEOUT,
                check=False,
            )
            if process.returncode:
                raise Invalid(f"git_exit_{process.returncode}:{args[0]}")
            if output.tell() > MAX_OUTPUT:
                raise Invalid("git_output_too_large")
            output.seek(0)
            return output.read()
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise Invalid(f"git_execution_failed:{type(exc).__name__}") from exc


def _records(data: bytes, name: str) -> list[bytes]:
    if data and not data.endswith(b"\x00"):
        raise Invalid(f"{name}_unterminated")
    return data[:-1].split(b"\x00") if data else []


def _decode(raw: bytes, name: str) -> str:
    try:
        value = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise Invalid(f"{name}_not_utf8") from exc
    if not value or "\x00" in value:
        raise Invalid(f"{name}_empty")
    return value


def _tree(data: bytes) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    seen: set[str] = set()
    for record in _records(data, "tree"):
        if b"\t" not in record:
            raise Invalid("tree_record_invalid")
        header, name = record.split(b"\t", 1)
        parts = header.decode("ascii").split()
        if len(parts) != 3 or parts[1] not in {"blob", "commit"}:
            raise Invalid("tree_header_invalid")
        path = _decode(name, "tree_path")
        if path in seen:
            raise Invalid("duplicate_tree_path")
        seen.add(path)
        entries.append(
            {"path": path, "mode": parts[0], "kind": parts[1], "object_sha": parts[2]}
        )
    return entries


def _changes(data: bytes) -> list[dict[str, str]]:
    parts = _records(data, "diff")
    changes: list[dict[str, str]] = []
    index = 0
    while index < len(parts):
        raw_status = _decode(parts[index], "diff_status")
        index += 1
        if not re.fullmatch(r"(?:[AMDTUXB]|[RC][0-9]{1,3})", raw_status):
            raise Invalid("diff_status_unknown")
        if index >= len(parts):
            raise Invalid("diff_path_missing")
        first = _decode(parts[index], "diff_path")
        index += 1
        if raw_status.startswith(("R", "C")):
            if index >= len(parts):
                raise Invalid("rename_target_missing")
            second = _decode(parts[index], "rename_target")
            index += 1
            changes.append(
                {"status": raw_status, "before_path": first, "after_path": second}
            )
        else:
            changes.append(
                {"status": raw_status, "before_path": first, "after_path": first}
            )
    return changes


def analyze(request: Any) -> dict[str, Any]:
    if not isinstance(request, dict) or set(request) != {
        "repository_root",
        "authorized_root",
        "base_sha",
        "head_sha",
    }:
        raise Invalid("request_schema_invalid")
    try:
        root = Path(request["repository_root"]).resolve(strict=True)
        authorized = Path(request["authorized_root"]).resolve(strict=True)
    except (TypeError, OSError, ValueError) as exc:
        raise Invalid("authorized_repository_unavailable") from exc
    if not root.is_dir() or root != authorized:
        raise Invalid("repository_outside_authorized_root")
    head = _sha(request["head_sha"], "head_sha")
    base = request["base_sha"]
    if base is not None:
        base = _sha(base, "base_sha")
    top = _decode(_git(root, "rev-parse", "--show-toplevel").strip(), "git_root")
    if Path(top).resolve() != root:
        raise Invalid("repository_root_mismatch")
    _git(root, "cat-file", "-e", head + "^{commit}")
    # A valid historical commit is not evidence of the current checkout.
    # The trusted host must refresh the inventory if HEAD has advanced.
    checkout_head = _sha(
        _decode(_git(root, "rev-parse", "--verify", "HEAD").strip(), "checkout_head"),
        "checkout_head",
    )
    if checkout_head != head:
        raise Invalid("git_head_changed")
    if base is not None:
        _git(root, "cat-file", "-e", base + "^{commit}")
    files = _tree(_git(root, "ls-tree", "-r", "--full-tree", "-z", head))
    gitlinks = [row for row in files if row["kind"] == "commit"]
    changes = (
        _changes(
            _git(
                root,
                "diff",
                "--no-ext-diff",
                "--name-status",
                "--find-renames",
                "-z",
                base,
                head,
                "--",
            )
        )
        if base is not None
        else []
    )
    return {
        "status": "incomplete" if gitlinks else "complete",
        "repository_root": str(root),
        "base_sha": base,
        "head_sha": head,
        "files": files,
        "changes": changes,
        "complete_file_listing": not gitlinks,
        "complete_change_listing": base is not None,
        "unretrieved": [
            f"gitlink:{row['path']}@{row['object_sha']}" for row in gitlinks
        ],
        "feature_count": None,
    }


def handle(request: Any) -> dict[str, Any]:
    try:
        return analyze(request)
    except (Invalid, KeyError, TypeError, UnicodeError, RecursionError) as exc:
        return {"status": "blocked", "reason": str(exc)}


def main() -> int:
    try:
        raw = sys.stdin.buffer.read(MAX_INPUT + 1)
        if len(raw) > MAX_INPUT:
            raise Invalid("input_too_large")
        request = json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs)
        trusted = os.environ.get("QA_FEATURE_AUTHORIZED_ROOT")
        if not trusted:
            raise Invalid("trusted_authorized_root_missing")
        if not isinstance(request, dict) or not isinstance(
            request.get("authorized_root"), str
        ):
            raise Invalid("trusted_authorized_root_mismatch")
        try:
            authorized_root = Path(request["authorized_root"]).resolve(strict=True)
            trusted_root = Path(trusted).resolve(strict=True)
        except (OSError, ValueError) as exc:
            raise Invalid("trusted_authorized_root_unavailable") from exc
        if trusted_root != authorized_root:
            raise Invalid("trusted_authorized_root_mismatch")
        result = handle(request)
    except (Invalid, UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        result = {"status": "blocked", "reason": str(exc)}
    sys.stdout.write(json.dumps(result, ensure_ascii=False, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
