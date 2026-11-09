"""Prepare UI-only human edits for the existing ui-target-v1 writer.

This helper extracts a proposed change from a valid saved package and an
isolated worktree copy. It never writes the package. The caller must run the
returned request through spec-analysis/scripts/ui_target_package.py and then
perform an independent readback. Approval references are carried as evidence;
this helper does not authenticate people or storage providers.
"""

from __future__ import annotations

import json
import os
import re
import stat
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
WRITER_DIR = ROOT / "skills" / "spec-analysis" / "scripts"
WRITER_PATH = WRITER_DIR / "ui_target_package.py"
MAX_INPUT_BYTES = 16 * 1024 * 1024
MAX_PACKAGE_BYTES = 16 * 1024 * 1024
MAX_FILE_BYTES = 4 * 1024 * 1024
MAX_FILES = 32

UI_TABLES = (
    ("01_ui_structure_and_navigation.md", "UI構造一覧"),
    ("02_behavior_and_business_rules.md", "UI操作一覧"),
    ("00_scope_and_context.md", "分析対象機能scope一覧"),
)
UI_PROSE = ("01_ui_structure_and_navigation.md", "Navigation / Entry / Exit")


class HumanEditError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _fail(code: str, message: str) -> None:
    raise HumanEditError(code, message)


def _writer_module():
    if not WRITER_PATH.is_file():
        _fail("writer_unavailable", "既存ui-target-v1 writerを利用できません")
    if str(WRITER_DIR) not in sys.path:
        sys.path.insert(0, str(WRITER_DIR))
    try:
        import ui_target_package as writer  # type: ignore[import-not-found]
    except Exception as exc:  # pragma: no cover - environment-specific import errors
        _fail("writer_unavailable", f"既存writerを読み込めません: {type(exc).__name__}")
    return writer


def _root(value: Any, name: str) -> Path:
    if not isinstance(value, str) or not value or "\x00" in value:
        _fail("invalid_input", f"{name}は空でないpathが必要です")
    lexical = Path(value)
    try:
        if lexical.is_symlink():
            _fail("symlink_not_allowed", f"{name}のroot symlinkは許可されません")
        resolved = lexical.resolve(strict=True)
        info = resolved.stat()
    except HumanEditError:
        raise
    except OSError:
        _fail("path_unavailable", f"{name}を読み取れません")
    if not stat.S_ISDIR(info.st_mode):
        _fail("path_unavailable", f"{name}はdirectoryではありません")
    return resolved


def _read_regular(root: Path, relative: str) -> bytes:
    if (
        not relative
        or relative.startswith("/")
        or "\\" in relative
        or any(part in {"", ".", ".."} for part in relative.split("/"))
    ):
        _fail("path_outside_package", f"非canonical package pathです: {relative!r}")
    path = root.joinpath(*relative.split("/"))
    try:
        path.resolve(strict=True).relative_to(root)
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(path, flags)
        try:
            info = os.fstat(descriptor)
            if not stat.S_ISREG(info.st_mode):
                _fail("file_type_not_allowed", f"regular fileではありません: {relative}")
            if info.st_size > MAX_FILE_BYTES:
                _fail("limit_exceeded", f"package fileが上限を超えています: {relative}")
            with os.fdopen(descriptor, "rb", closefd=False) as stream:
                raw = stream.read(MAX_FILE_BYTES + 1)
        finally:
            os.close(descriptor)
    except HumanEditError:
        raise
    except (OSError, ValueError):
        _fail("file_unreadable", f"package fileを安全に読めません: {relative}")
    if len(raw) > MAX_FILE_BYTES:
        _fail("limit_exceeded", f"package fileが上限を超えています: {relative}")
    return raw


def _file_set(root: Path, expected: set[str]) -> None:
    seen: set[str] = set()
    total = 0
    try:
        with os.scandir(root) as entries:
            for entry in entries:
                info = entry.stat(follow_symlinks=False)
                if stat.S_ISLNK(info.st_mode) or getattr(
                    info, "st_file_attributes", 0
                ) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400):
                    _fail("symlink_not_allowed", f"package symlinkは許可されません: {entry.name}")
                if not stat.S_ISREG(info.st_mode):
                    _fail("package_file_set_mismatch", "package内のdirectory等は許可されません")
                seen.add(entry.name)
                total += info.st_size
    except HumanEditError:
        raise
    except OSError:
        _fail("path_unavailable", "packageのfile setを確認できません")
    if len(seen) > MAX_FILES or total > MAX_PACKAGE_BYTES:
        _fail("limit_exceeded", "package全体がsize上限を超えています")
    if seen != expected:
        _fail("package_file_set_mismatch", "作業copyのfile setが元packageと一致しません")


def _run_inspect(root: Path) -> dict[str, Any]:
    if not WRITER_PATH.is_file():
        _fail("writer_unavailable", "既存ui-target-v1 writerを利用できません")
    request = {"operation": "inspect", "package_root": str(root)}
    try:
        result = subprocess.run(
            [sys.executable, str(WRITER_PATH)],
            input=(json.dumps(request, ensure_ascii=True) + "\n").encode("utf-8"),
            capture_output=True,
            check=False,
            timeout=30,
            cwd=ROOT,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        _fail("writer_unavailable", f"既存writerのinspectを実行できません: {type(exc).__name__}")
    try:
        response = json.loads(result.stdout.decode("utf-8", errors="strict"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        _fail("writer_invalid_response", "既存writerのinspect応答を検証できません")
    if result.returncode != 0 or not isinstance(response, dict) or response.get("valid") is not True:
        issues = response.get("issues", []) if isinstance(response, dict) else []
        _fail("package_not_current", json.dumps(issues, ensure_ascii=True)[:2000])
    payload = response.get("payload")
    if not isinstance(payload, dict) or not isinstance(payload.get("update_snapshot"), dict):
        _fail("writer_invalid_response", "inspectに有効なupdate_snapshotがありません")
    return payload


def _read_model(writer: Any, root: Path):
    try:
        with writer._package_lock(root):
            return writer._read_package(root)
    except Exception as exc:
        code = getattr(exc, "code", "package_not_current")
        _fail(str(code), str(getattr(exc, "message", "packageを検証できません")))


def _text(raw: bytes, path: str) -> str:
    try:
        value = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        _fail("invalid_encoding", f"UTF-8ではありません: {path}")
    if "\r" in value or not value.endswith("\n"):
        _fail("noncanonical_text", f"canonical LF/末尾改行ではありません: {path}")
    return value


def _row_identity(spec: Any) -> str:
    if not spec.id_column:
        _fail("owner_boundary", f"IDを持たないtableは編集できません: {spec.section}")
    return spec.id_column


def _table_rows(writer: Any, text: str, file: str, section: str) -> list[dict[str, str]]:
    spec = writer.TABLE_BY_KEY.get((file, section))
    if spec is None or not spec.id_column:
        _fail("package_schema_mismatch", f"tracking tableがありません: {file}/{section}")
    try:
        return writer.parse_table(text, section, spec.headers)
    except Exception as exc:
        _fail("package_schema_mismatch", str(getattr(exc, "message", "tableを解析できません")))


def _rows_by_id(rows: list[dict[str, str]], id_column: str, section: str) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    for row in rows:
        stable_id = row[id_column]
        if not stable_id or stable_id in result:
            _fail("duplicate_id", f"{section}のIDが空または重複しています")
        result[stable_id] = row
    return result


def _cell_values(writer: Any, spec: Any, row: dict[str, str]) -> dict[str, Any]:
    derived = {spec.id_column} if spec.id_column else set()
    if spec.status_column:
        derived.add(spec.status_column)
    if (spec.file, spec.section) == ("00_scope_and_context.md", "分析対象機能scope一覧"):
        derived.add("Behavior Decomposition")
    cells: dict[str, Any] = {}
    for field in spec.headers:
        if field in derived:
            continue
        value = row[field]
        cells[field] = writer._split_refs(value, allow_draft=True) if field in spec.refs else value
    try:
        return writer._table_change_cells(spec, cells)
    except Exception as exc:
        _fail("invalid_table_change", str(getattr(exc, "message", "table rowを検証できません")))


def _row_dependencies(writer: Any, spec: Any, row: dict[str, str]) -> set[str]:
    result = {row.get(spec.id_column or "", "")}
    for field in spec.refs:
        if field in row and row[field]:
            try:
                result.update(writer._split_refs(row[field], allow_draft=True))
            except Exception as exc:
                _fail("invalid_reference", str(getattr(exc, "message", "stable referenceが不正です")))
    return {item for item in result if item}


def _table_diff(writer: Any, base: dict[str, str], candidate: dict[str, str]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    retired: set[str] = set()
    identities: set[str] = set()
    dependencies: set[str] = set()
    by_key: dict[str, dict[str, Any]] = {}
    for file, section in UI_TABLES:
        spec = writer.TABLE_BY_KEY[(file, section)]
        id_column = _row_identity(spec)
        old_rows = _rows_by_id(_table_rows(writer, base[file], file, section), id_column, section)
        new_rows = _rows_by_id(_table_rows(writer, candidate[file], file, section), id_column, section)
        if file == "00_scope_and_context.md":
            allowed = {"対象機能 / 領域", "UI操作判定", "関連UNKNOWN ID", "関連仕様項目ID", "根拠 / 備考"}
            if set(spec.headers) - {id_column, "Behavior Decomposition"} != allowed:
                _fail("package_schema_mismatch", "SCOPE table schemaが想定と一致しません")
        for stable_id, old in old_rows.items():
            if stable_id not in new_rows:
                if stable_id.startswith("@"):
                    _fail("invalid_id", "既存IDの削除を推測して処理できません")
                retired.add(stable_id)
                identities.add(stable_id)
                dependencies.update(_row_dependencies(writer, spec, old))
        for stable_id, row in new_rows.items():
            if stable_id.startswith("@draft:"):
                draft_key = stable_id[len("@draft:") :]
                if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", draft_key):
                    _fail("invalid_draft_key", f"draft keyが不正です: {stable_id}")
                if stable_id in old_rows:
                    _fail("invalid_draft_key", "draft keyが既存IDと一致します")
                action = "new"
                reuse_id = None
                key = stable_id
            else:
                if not re.fullmatch(r"[A-Z][A-Z0-9]*-[0-9]{3,}", stable_id):
                    _fail("manual_id_not_allowed", f"stable IDを手入力できません: {stable_id}")
                if stable_id not in old_rows:
                    _fail("manual_id_not_allowed", f"新規IDには@draft:<key>を使ってください: {stable_id}")
                action = "reuse"
                reuse_id = stable_id
                key = stable_id
            if stable_id in old_rows and row == old_rows[stable_id]:
                continue
            cells = _cell_values(writer, spec, row)
            item = {
                "key": key,
                "file": file,
                "section": section,
                "row": {
                    "draft_key": key[len("@draft:") :] if action == "new" else None,
                    "identity_action": action,
                    "reuse_id": reuse_id,
                    "external_id": None,
                    "cells": cells,
                },
                "dependencies": sorted(_row_dependencies(writer, spec, row)),
            }
            rows.append(item)
            identities.add(key)
            dependencies.update(item["dependencies"])
            by_key[key] = item
    return {
        "rows": rows,
        "retired_ids": sorted(retired),
        "identities": identities,
        "dependencies": dependencies,
        "by_key": by_key,
    }


def _section_body(writer: Any, text: str, heading: str) -> str:
    try:
        lines, start, end = writer._heading_span(text, heading)
    except Exception as exc:
        _fail("package_schema_mismatch", str(getattr(exc, "message", "prose sectionを読めません")))
    return "\n".join(lines[start + 1 : end]).strip("\n")


def _extract_diff(
    writer: Any,
    base_files: dict[str, str],
    candidate_files: dict[str, str],
    *,
    allow_generated_differences: bool = False,
) -> dict[str, Any]:
    tables = _table_diff(writer, base_files, candidate_files)
    base_prose = _section_body(writer, base_files[UI_PROSE[0]], UI_PROSE[1])
    candidate_prose = _section_body(writer, candidate_files[UI_PROSE[0]], UI_PROSE[1])
    prose = None if base_prose == candidate_prose else candidate_prose
    # Rebuild the candidate from the base using only owned tables and prose.
    for file in set(base_files) | set(candidate_files):
        if file not in base_files or file not in candidate_files:
            _fail("package_file_set_mismatch", "candidateのpackage file setが異なります")
        if allow_generated_differences and file in {"README.md", "CHANGELOG.md", "MANIFEST.md"}:
            continue
        if file not in {"00_scope_and_context.md", "01_ui_structure_and_navigation.md", "02_behavior_and_business_rules.md"}:
            if base_files[file] != candidate_files[file]:
                _fail("owner_boundary", f"UI ownerが編集できないfileです: {file}")
    for file in ("00_scope_and_context.md", "01_ui_structure_and_navigation.md", "02_behavior_and_business_rules.md"):
        if file not in base_files:
            _fail("package_schema_mismatch", f"必須fileがありません: {file}")
    rebuilt = dict(base_files)
    for file, section in UI_TABLES:
        spec = writer.TABLE_BY_KEY[(file, section)]
        candidate_rows = _table_rows(writer, candidate_files[file], file, section)
        rebuilt[file] = writer.replace_table(rebuilt[file], section, spec.headers, candidate_rows)
    if prose is not None:
        try:
            rebuilt[UI_PROSE[0]] = writer._replace_user_prose_body(
                rebuilt[UI_PROSE[0]], UI_PROSE[1], prose
            )
        except Exception as exc:
            _fail("invalid_prose_update", str(getattr(exc, "message", "prose updateが不正です")))
    for file in rebuilt:
        if allow_generated_differences and file in {"README.md", "CHANGELOG.md", "MANIFEST.md"}:
            continue
        if writer.canonical_bytes(rebuilt[file]) != writer.canonical_bytes(candidate_files[file]):
            _fail("owner_boundary", f"UI owner scope外の編集または非canonical変更です: {file}")
    return {**tables, "prose": prose}


def _review(request: dict[str, Any], diff: dict[str, Any], current_snapshot: dict[str, Any], *, rebased: bool) -> dict[str, Any]:
    review = request.get("review")
    if not isinstance(review, dict):
        _fail("review_required", "ownerの意味確認と配置合意参照が必要です")
    if review.get("decision") != "approved":
        _fail("review_required", "未承認の編集差分は正式更新へ渡せません")
    for key in ("review_ref", "placement_agreement_ref", "change_summary"):
        value = review.get(key)
        if not isinstance(value, str) or not value.strip() or len(value) > 1000:
            _fail("review_required", f"review.{key}が必要です")
    if rebased and review.get("approved_current_snapshot") != current_snapshot:
        _fail("review_required", "再照合後のcurrent snapshotに対する再確認が必要です")
    expected_keys = set(diff["identities"])
    if diff["prose"] is not None:
        expected_keys.add(f"prose:{UI_PROSE[0]}:{UI_PROSE[1]}")
    approved = review.get("approved_change_keys")
    if not isinstance(approved, list) or any(not isinstance(item, str) for item in approved):
        _fail("review_required", "approved_change_keysはstring arrayが必要です")
    if set(approved) != expected_keys or len(approved) != len(set(approved)):
        _fail("review_mismatch", "承認対象がcandidateの変更差分と一致しません")
    evidence = review.get("evidence_refs")
    if not isinstance(evidence, dict) or set(evidence) != expected_keys:
        _fail("evidence_required", "各変更に対応するevidence_refsが必要です")
    for key, refs in evidence.items():
        if not isinstance(refs, list) or not refs or any(not isinstance(ref, str) or not ref.strip() for ref in refs):
            _fail("evidence_required", f"evidence refがありません: {key}")
    retirement_rows = review.get("approved_retirements", [])
    if not isinstance(retirement_rows, list):
        _fail("retirement_review_required", "approved_retirementsはarrayが必要です")
    retirement_map: dict[str, dict[str, str]] = {}
    for row in retirement_rows:
        if not isinstance(row, dict) or set(row) != {"id", "reason", "approval_ref"}:
            _fail("retirement_review_required", "廃止にはID・理由・承認参照が必要です")
        stable_id = row["id"]
        if not isinstance(stable_id, str) or stable_id in retirement_map:
            _fail("retirement_review_required", "廃止IDが不正または重複しています")
        if not isinstance(row["reason"], str) or not row["reason"].strip() or not isinstance(row["approval_ref"], str) or not row["approval_ref"].strip():
            _fail("retirement_review_required", f"廃止理由・承認参照が必要です: {stable_id}")
        retirement_map[stable_id] = {"reason": row["reason"], "approval_ref": row["approval_ref"]}
    if set(retirement_map) != set(diff["retired_ids"]):
        _fail("retirement_review_required", "削除行と明示承認されたretire IDが一致しません")
    retirement_evidence = review.get("retirement_evidence_refs", {})
    if not isinstance(retirement_evidence, dict) or set(retirement_evidence) != set(diff["retired_ids"]):
        if diff["retired_ids"]:
            _fail("evidence_required", "廃止根拠のrefが必要です")
    for stable_id, refs in retirement_evidence.items():
        if not isinstance(refs, list) or not refs or any(not isinstance(ref, str) or not ref.strip() for ref in refs):
            _fail("evidence_required", f"廃止根拠のrefがありません: {stable_id}")
    return {
        "review_ref": review["review_ref"],
        "placement_agreement_ref": review["placement_agreement_ref"],
        "evidence_refs": evidence,
        "retirement_evidence_refs": retirement_evidence,
        "retirements": retirement_map,
    }


def _same_diff(left: dict[str, Any], right: dict[str, Any]) -> bool:
    def signature(diff: dict[str, Any]) -> tuple[Any, ...]:
        rows = tuple(sorted(
            (
                item["key"],
                item["file"],
                item["section"],
                json.dumps(item["row"], ensure_ascii=True, sort_keys=True, separators=(",", ":")),
            )
            for item in diff["rows"]
        ))
        return rows, tuple(sorted(diff["retired_ids"])), diff["prose"]
    return signature(left) == signature(right)


def _materialize_request(
    writer: Any,
    canonical_root: Path,
    previous_snapshot: dict[str, Any],
    diff: dict[str, Any],
    change_summary: str,
) -> dict[str, Any]:
    by_table: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for item in diff["rows"]:
        by_table.setdefault((item["file"], item["section"]), []).append(item["row"])
    table_changes = [
        {"file": file, "section": section, "rows": rows}
        for (file, section), rows in sorted(
            by_table.items(),
            key=lambda entry: next(
                index
                for index, spec in enumerate(writer.TABLES)
                if (spec.file, spec.section) == entry[0]
            ),
        )
    ]
    prose_updates = []
    if diff["prose"] is not None:
        prose_updates.append(
            {
                "file": UI_PROSE[0],
                "section": UI_PROSE[1],
                "body_markdown": diff["prose"],
            }
        )
    return {
        "operation": "materialize",
        "package_root": str(canonical_root),
        "artifact_mode": "update",
        "previous_snapshot": previous_snapshot,
        "change_mode": "normal",
        "legacy_source_version": None,
        "migration_retained_ids": [],
        "legacy_lifecycle_events": [],
        "change_summary": change_summary,
        "retire_ids": diff["retired_ids"],
        "table_changes": table_changes,
        "keyed_table_updates": [],
        "prose_updates": prose_updates,
        "extension_file_updates": [],
        "extension_file_retirements": [],
    }


def _request_fingerprint(writer: Any, request: dict[str, Any]) -> str:
    normalized = writer._normalize_materialize_request(request)
    return "sha256:" + writer._sha(writer.canonical_json_bytes(normalized))


def _check_concurrent(
    base_files: dict[str, str],
    current_files: dict[str, str],
    candidate_diff: dict[str, Any],
    current_diff: dict[str, Any],
) -> None:
    for file in base_files:
        if (
            file not in {"00_scope_and_context.md", "01_ui_structure_and_navigation.md", "02_behavior_and_business_rules.md"}
            and file not in {"README.md", "CHANGELOG.md", "MANIFEST.md"}
            and base_files[file] != current_files[file]
        ):
            _fail("concurrent_edit_blocked", f"UI owner外のcurrent変更を確認してください: {file}")
    if _same_diff(candidate_diff, current_diff):
        return
    if candidate_diff["prose"] is not None or current_diff["prose"] is not None:
        _fail("concurrent_edit_blocked", "Navigation proseの同時更新は意味衝突として再確認が必要です")
    if candidate_diff["identities"] & current_diff["identities"]:
        _fail("concurrent_edit_blocked", "同じstable IDを複数の編集者が変更しています")
    if candidate_diff["dependencies"] & current_diff["dependencies"]:
        _fail("concurrent_edit_blocked", "編集差分の参照・scopeに意味上の依存があります")
    # Unrelated changes can be rebased only after an explicit review of current.


def _prepare(request: dict[str, Any]) -> dict[str, Any]:
    writer = _writer_module()
    canonical_root = _root(request.get("package_root"), "package_root")
    base_root = _root(request.get("base_root"), "base_root")
    edit_root = _root(request.get("edit_root"), "edit_root")
    if len({canonical_root, base_root, edit_root}) < 3:
        _fail("invalid_input", "canonical/base/edit rootは分離してください")
    previous_snapshot = request.get("previous_snapshot")
    base_inspect = _run_inspect(base_root)
    if previous_snapshot != base_inspect["update_snapshot"]:
        _fail("stale_snapshot", "提示された元snapshotが有効なbase packageと一致しません")
    base_model = _read_model(writer, base_root)
    if writer._read_update_snapshot(base_model) != base_inspect["update_snapshot"]:
        _fail("stale_snapshot", "inspect後にbase packageが変更されました")
    current_inspect = _run_inspect(canonical_root)
    current_model = _read_model(writer, canonical_root)
    if writer._read_update_snapshot(current_model) != current_inspect["update_snapshot"]:
        _fail("concurrent_edit_blocked", "inspect後にcanonical packageが変更されました")
    expected_paths = {row["path"] for row in base_inspect["payload_files"]} | {"MANIFEST.md"}
    for root in (base_root, edit_root):
        _file_set(root, expected_paths)
    if {row["path"] for row in current_inspect["payload_files"]} | {"MANIFEST.md"} != expected_paths:
        _fail("package_file_set_mismatch", "canonicalとbaseのpackage file setが異なります")
    base_files = {path: _text(_read_regular(base_root, path), path) for path in expected_paths}
    edit_files = {path: _text(_read_regular(edit_root, path), path) for path in expected_paths}
    current_files = {path: _text(_read_regular(canonical_root, path), path) for path in expected_paths}
    candidate_diff = _extract_diff(writer, base_files, edit_files)
    if not candidate_diff["identities"] and not candidate_diff["retired_ids"] and candidate_diff["prose"] is None:
        return {"status": "unchanged", "package_version": current_inspect["package_version"], "update_snapshot": current_inspect["update_snapshot"]}
    rebased = current_inspect["update_snapshot"] != previous_snapshot
    if rebased:
        retry_review = _review(request, candidate_diff, current_inspect["update_snapshot"], rebased=False)
        retry_request = _materialize_request(
            writer,
            canonical_root,
            previous_snapshot,
            candidate_diff,
            request.get("review", {}).get("change_summary"),
        )
        if (
            current_model.receipt.get("request_fingerprint")
            == _request_fingerprint(writer, retry_request)
        ):
            return {
                "status": "unchanged",
                "package_version": current_inspect["package_version"],
                "update_snapshot": current_inspect["update_snapshot"],
                "writer_receipt": {
                    "request_fingerprint": current_model.receipt["request_fingerprint"],
                    "allocated_ids": current_model.receipt["allocated_ids"],
                    "retired_ids": current_model.receipt["retired_ids"],
                },
                "review_evidence": retry_review,
                "reason": "同一materialize requestのreceiptがcurrent packageにあります",
            }
        try:
            current_diff = _extract_diff(writer, base_files, current_files, allow_generated_differences=True)
        except HumanEditError as exc:
            if exc.code == "manual_id_not_allowed":
                _fail("concurrent_edit_blocked", "current packageに元copyから対応付けられない採番済み行があります")
            raise
        _check_concurrent(base_files, current_files, candidate_diff, current_diff)
        if _same_diff(candidate_diff, current_diff):
            return {
                "status": "unchanged",
                "package_version": current_inspect["package_version"],
                "update_snapshot": current_inspect["update_snapshot"],
                "reason": "同じ意味の差分は既にcurrentへ反映済みです",
            }
    approved = _review(request, candidate_diff, current_inspect["update_snapshot"], rebased=rebased)
    materialize_request = _materialize_request(
        writer,
        canonical_root,
        current_inspect["update_snapshot"],
        candidate_diff,
        request.get("review", {}).get("change_summary"),
    )
    # Preserve evidence alongside, but outside, the canonical package schema.
    return {
        "status": "ready",
        "rebased": rebased,
        "base_package_version": base_inspect["package_version"],
        "current_package_version": current_inspect["package_version"],
        "previous_snapshot": current_inspect["update_snapshot"],
        "change_keys": sorted(candidate_diff["identities"] | ({f"prose:{UI_PROSE[0]}:{UI_PROSE[1]}"} if candidate_diff["prose"] is not None else set())),
        "changed_ids": sorted(candidate_diff["identities"] | set(candidate_diff["retired_ids"])),
        "review_evidence": approved,
        "materialize_request": materialize_request,
    }


def _row_locations(writer: Any, model: Any) -> dict[str, dict[str, Any]]:
    locations: dict[str, dict[str, Any]] = {}
    for file, section in UI_TABLES:
        spec = writer.TABLE_BY_KEY[(file, section)]
        text = model.files[file]
        lines, start, end = writer._heading_span(text, section)
        table_start = next((index for index in range(start + 1, end) if lines[index].startswith("|")), None)
        if table_start is None:
            _fail("package_schema_mismatch", f"tableがありません: {section}")
        for row_index, row in enumerate(writer._rows(model, file, section), start=1):
            physical_index = table_start + row_index + 1
            stable_id = row[spec.id_column]
            locations[stable_id] = {
                "id": stable_id,
                "file": file,
                "section": section,
                "row_index": row_index,
                "line": physical_index + 1,
            }
    return locations


def _feature_index(request: dict[str, Any]) -> dict[str, Any]:
    writer = _writer_module()
    package_root = _root(request.get("package_root"), "package_root")
    inspected = _run_inspect(package_root)
    model = _read_model(writer, package_root)
    if writer._read_update_snapshot(model) != inspected["update_snapshot"]:
        _fail("concurrent_edit_blocked", "inspect後にUI packageが変更されました")
    artifact_ref = request.get("feature_artifact_ref")
    revision = request.get("feature_artifact_revision")
    if not isinstance(artifact_ref, str) or not artifact_ref.strip() or not isinstance(revision, str) or not revision.strip():
        _fail("source_ref_required", "feature artifact refとrevisionが必要です")
    mapping = request.get("feature_scope_refs")
    if not isinstance(mapping, list):
        _fail("invalid_input", "feature_scope_refsはarrayが必要です")
    scopes = {row["Scope ID"] for row in writer._rows(model, "00_scope_and_context.md", "分析対象機能scope一覧")}
    uiops = writer._rows(model, "02_behavior_and_business_rules.md", "UI操作一覧")
    structures = {row["構造ID"]: row for row in writer._rows(model, "01_ui_structure_and_navigation.md", "UI構造一覧")}
    locations = _row_locations(writer, model)
    changed_ids = request.get("changed_ids", [])
    if not isinstance(changed_ids, list) or any(not isinstance(item, str) or not item for item in changed_ids):
        _fail("invalid_input", "changed_idsは空でないstable IDのarrayが必要です")
    if len(changed_ids) != len(set(changed_ids)):
        _fail("duplicate_id", "changed_idsが重複しています")
    result = []
    seen: set[tuple[str, str]] = set()
    for item in mapping:
        if not isinstance(item, dict) or set(item) != {"feature_id", "scope_id"}:
            _fail("invalid_input", "feature scope mapping schemaが不正です")
        feature_id, scope_id = item["feature_id"], item["scope_id"]
        if (
            not isinstance(feature_id, str)
            or not feature_id.strip()
            or not isinstance(scope_id, str)
            or scope_id not in scopes
        ):
            _fail("reference_not_found", "feature IDまたはUI Scope参照がありません")
        key = (feature_id, scope_id)
        if key in seen:
            _fail("duplicate_id", "featureとScopeのmappingが重複しています")
        seen.add(key)
        operation_rows = [row for row in uiops if scope_id in writer._refs(row, "Scope ID")]
        operation_ids = {row["操作ID"] for row in operation_rows}
        operation_dependencies = {
            ref
            for row in operation_rows
            for ref in _row_dependencies(writer, writer.TABLE_BY_KEY[("02_behavior_and_business_rules.md", "UI操作一覧")], row)
        }
        structure_ids: set[str] = set()
        for row in operation_rows:
            for structure_id in writer._refs(row, "対象構造ID"):
                cursor = structure_id
                while cursor:
                    if cursor in structure_ids:
                        break
                    structure_ids.add(cursor)
                    structure = structures.get(cursor)
                    if structure is None:
                        _fail("reference_not_found", f"UI構造がありません: {cursor}")
                    cursor = structure["親構造ID"]
        target_ids = sorted(operation_ids | structure_ids)
        target_ids.append(scope_id)
        target_ids = sorted(set(target_ids))
        result.append({
            "feature_id": feature_id,
            "scope_id": scope_id,
            "package_version": inspected["package_version"],
            "ui_rows": [locations[stable_id] for stable_id in target_ids if stable_id in locations],
            "changed_ui_rows": [locations[stable_id] for stable_id in target_ids if stable_id in set(changed_ids) and stable_id in locations],
            "changed_ids_without_current_row": sorted(set(changed_ids) & (operation_ids | structure_ids | {scope_id}) - set(locations)),
            "related_ids": sorted((operation_dependencies - operation_ids - {scope_id}) | structure_ids),
        })
    return {
        "status": "ok",
        "feature_artifact_ref": artifact_ref,
        "feature_artifact_revision": revision,
        "ui_package_ref": str(package_root),
        "ui_package_version": inspected["package_version"],
        "ui_package_snapshot": inspected["update_snapshot"],
        "feature_scope_index": result,
    }


def run(request: Any) -> dict[str, Any]:
    if not isinstance(request, dict):
        _fail("invalid_input", "top-level JSONはobjectである必要があります")
    operation = request.get("operation")
    allowed = {
        "prepare": {"operation", "package_root", "base_root", "edit_root", "previous_snapshot", "review"},
        "feature-index": {"operation", "package_root", "feature_artifact_ref", "feature_artifact_revision", "feature_scope_refs", "changed_ids"},
    }
    required = allowed.get(operation)
    if required is None or not required - {"changed_ids"} <= set(request) or set(request) - required:
        _fail("invalid_input", "operationまたはtop-level field集合が不正です")
    if operation == "prepare":
        return _prepare(request)
    return _feature_index(request)


def main() -> int:
    raw = sys.stdin.buffer.read(MAX_INPUT_BYTES + 1)
    if len(raw) > MAX_INPUT_BYTES:
        response = {"status": "blocked", "issues": [{"code": "limit_exceeded", "message": "入力が上限を超えています"}]}
        print(json.dumps(response, ensure_ascii=True, separators=(",", ":")))
        return 1
    try:
        def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
            result: dict[str, Any] = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError("duplicate JSON key")
                result[key] = value
            return result

        request = json.loads(raw.decode("utf-8", errors="strict"), object_pairs_hook=reject_duplicates)
        response = run(request)
        exit_code = 0
    except (UnicodeDecodeError, ValueError):
        response = {"status": "blocked", "issues": [{"code": "invalid_input", "message": "UTF-8 JSONを解析できません"}]}
        exit_code = 1
    except HumanEditError as exc:
        response = {"status": "blocked", "issues": [{"code": exc.code, "message": exc.message}]}
        exit_code = 1
    print(json.dumps(response, ensure_ascii=True, separators=(",", ":")))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
