"""入力revisionのSHA-256を計算し、記録との差分を比較する決定論的helper。

subcommand:
- hash: 対象fileのSHA-256をJSONで出す。
- record: 同じJSONを --state のfileへ原子的に書く。--state のfile名は input-revisions.json に限り、別形式の既存fileは上書きしない。
- compare: --state の記録と現在の対象を比べ、same / changed / no_record を出す。

Python標準ライブラリだけを使い、ネットワークを使わず、--state 以外へ書き込みません。
入力エラーは {"status":"error","reason":...} を標準出力へ出し、終了コード2で終わります。
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import stat
import sys
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any, NoReturn

REVISION_SCHEMA = "input-revision-v1"
STATE_NAME = "input-revisions.json"
COMPARE_SCHEMA = "input-revision-compare-v1"
MAX_FILE_BYTES = 32 * 1024 * 1024
_CHUNK_BYTES = 1024 * 1024


class InputError(Exception):
    """入力またはstateの問題。reasonは固定のsnake_case識別子。"""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def _dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def _emit(value: Any) -> None:
    sys.stdout.write(_dumps(value) + "\n")
    sys.stdout.flush()


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        _emit({"status": "error", "reason": "invalid_arguments"})
        raise SystemExit(2)


def _resolve_target(root: Path, raw: str) -> tuple[str, Path]:
    """相対pathを検証し、(正規化した相対path, 解決済みの実path) を返す。"""
    if not raw or "\x00" in raw:
        raise InputError("invalid_path")
    relative = PurePosixPath(raw)
    if relative.is_absolute() or ".." in relative.parts:
        raise InputError("path_outside_root")
    try:
        resolved = (root / relative).resolve(strict=True)
    except OSError as exc:
        raise InputError("path_not_found") from exc
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise InputError("path_outside_root") from exc
    try:
        mode = resolved.stat().st_mode
    except OSError as exc:
        raise InputError("path_not_found") from exc
    if not stat.S_ISREG(mode):
        raise InputError("not_a_regular_file")
    if resolved.stat().st_size > MAX_FILE_BYTES:
        raise InputError("file_too_large")
    return relative.as_posix(), resolved


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    total = 0
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(_CHUNK_BYTES), b""):
                total += len(chunk)
                if total > MAX_FILE_BYTES:
                    raise InputError("file_too_large")
                digest.update(chunk)
    except OSError as exc:
        raise InputError("read_failed") from exc
    return digest.hexdigest()


def _compute_document(root_arg: str, raw_paths: list[str]) -> dict[str, Any]:
    if "\x00" in root_arg:
        raise InputError("invalid_path")
    root = Path(root_arg).resolve()
    if not root.is_dir():
        raise InputError("root_not_directory")
    revisions: dict[str, str] = {}
    for raw in raw_paths:
        key, path = _resolve_target(root, raw)
        revisions[key] = _sha256_file(path)
    return {
        "schema_version": REVISION_SCHEMA,
        "root": str(root),
        "revisions": dict(sorted(revisions.items())),
    }


def _load_recorded(state: Path) -> dict[str, str] | None:
    """記録済みrevisionを返す。存在しない・空・壊れた記録はNoneを返す。"""
    try:
        text = state.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    except UnicodeDecodeError:
        return None
    except OSError as exc:
        raise InputError("state_read_failed") from exc
    if not text.strip():
        return None
    try:
        document = json.loads(text)
    except (ValueError, RecursionError):
        return None
    if not isinstance(document, dict):
        return None
    if document.get("schema_version") != REVISION_SCHEMA:
        return None
    revisions = document.get("revisions")
    if not isinstance(revisions, dict):
        return None
    if not all(
        isinstance(key, str) and isinstance(value, str)
        for key, value in revisions.items()
    ):
        return None
    return revisions


def _check_record_state(state: Path) -> None:
    """record の --state を検査する。拒否時は何も書かない。

    名前は input-revisions.json に限る。既存fileがあれば、空fileか
    schema_version が REVISION_SCHEMA のJSON objectの場合だけ置換を許す。
    """
    if "\x00" in str(state):
        raise InputError("invalid_path")
    if state.name != STATE_NAME:
        raise InputError("state_name_not_allowed")
    try:
        text = state.read_text(encoding="utf-8")
    except FileNotFoundError:
        return
    except UnicodeDecodeError as exc:
        raise InputError("state_not_a_record") from exc
    except OSError as exc:
        raise InputError("state_read_failed") from exc
    if not text.strip():
        return
    try:
        document = json.loads(text)
    except (ValueError, RecursionError) as exc:
        raise InputError("state_not_a_record") from exc
    if (
        not isinstance(document, dict)
        or document.get("schema_version") != REVISION_SCHEMA
    ):
        raise InputError("state_not_a_record")


def _write_state(state: Path, text: str) -> None:
    """同じdirectoryの一時fileへ書いてから os.replace で置換する。"""
    if not state.parent.is_dir():
        raise InputError("state_parent_missing")
    temporary: str | None = None
    try:
        fd, temporary = tempfile.mkstemp(
            dir=str(state.parent), prefix=".input-revisions-", suffix=".tmp"
        )
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, state)
        temporary = None
    except OSError as exc:
        raise InputError("state_write_failed") from exc
    finally:
        if temporary is not None:
            with contextlib.suppress(OSError):
                os.unlink(temporary)


def _record(args: argparse.Namespace) -> dict[str, Any]:
    _check_record_state(args.state)
    document = _compute_document(args.root, args.paths)
    _write_state(args.state, _dumps(document) + "\n")
    return document


def _compare(args: argparse.Namespace) -> dict[str, Any]:
    current = _compute_document(args.root, args.paths)["revisions"]
    recorded = _load_recorded(args.state)
    if recorded is None:
        return {
            "schema_version": COMPARE_SCHEMA,
            "status": "no_record",
            "changed": [],
            "added": [],
            "removed": [],
        }
    changed = sorted(
        key for key in current if key in recorded and current[key] != recorded[key]
    )
    added = sorted(key for key in current if key not in recorded)
    removed = sorted(key for key in recorded if key not in current)
    status = "same" if not (changed or added or removed) else "changed"
    return {
        "schema_version": COMPARE_SCHEMA,
        "status": status,
        "changed": changed,
        "added": added,
        "removed": removed,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = _Parser(description=__doc__)
    subparsers = parser.add_subparsers(
        dest="command", required=True, parser_class=_Parser
    )
    specs = (
        ("hash", "対象fileのSHA-256をJSONで出す"),
        ("record", "対象fileのSHA-256を --state へ記録する"),
        ("compare", "--state の記録と現在の対象を比べる"),
    )
    for name, help_text in specs:
        sub = subparsers.add_parser(name, help=help_text)
        sub.add_argument("--root", required=True, help="入力fileの基準directory")
        if name != "hash":
            sub.add_argument("--state", type=Path, required=True, help="記録JSON")
        sub.add_argument(
            "paths", nargs="+", metavar="PATH", help="--rootからの相対path"
        )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        if args.command == "hash":
            _emit(_compute_document(args.root, args.paths))
        elif args.command == "record":
            _emit(_record(args))
        else:
            _emit(_compare(args))
    except InputError as exc:
        _emit({"status": "error", "reason": exc.reason})
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
