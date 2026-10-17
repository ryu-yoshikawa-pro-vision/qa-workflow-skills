"""Canonical reader/writer for spec-analysis UI target packages.

This module deliberately supports only the fixed ``ui-target-v1`` package
schema.  Meaning is supplied by the caller; this module validates references,
allocates package-local identities, renders the known tables and owns the
package's atomic write path.
"""

from __future__ import annotations

import contextlib
import hashlib
import os
import re
import stat
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

# ``python -I`` and embeddable Python builds do not automatically add the
# script's directory to ``sys.path``. Keep this skill-local import stable for
# both module imports and direct CLI execution.
SCRIPT_PATH = Path(__file__).resolve()
if str(SCRIPT_PATH.parent) not in sys.path:
    sys.path.insert(0, str(SCRIPT_PATH.parent))

from runtime_contract import (  # noqa: E402
    RuntimeErrorBase,
    canonical_json_bytes,
    canonicalize,
    extract_machine_blocks,
    make_machine_entity,
    render_machine_entities,
    strict_loads,
)

SCHEMA_VERSION = "ui-target-v1"
RECEIPT_VERSION = "materialize-receipt-v1"
MAX_PACKAGE_BYTES = 16 * 1024 * 1024
MAX_IO_BYTES = 16 * 1024 * 1024
ASSET_ROOT = SCRIPT_PATH.parent.parent / "assets" / "ui-test-target-analysis"


class PackageError(RuntimeErrorBase):
    def __init__(self, issue_type: str, message: str):
        super().__init__(message)
        self.issue_type = issue_type
        self.message = message


def fail(issue_type: str, message: str) -> None:
    raise PackageError(issue_type, message)


@dataclass(frozen=True)
class TableSpec:
    file: str
    section: str
    headers: tuple[str, ...]
    id_column: str | None = None
    prefix: str | None = None
    status_column: str | None = None
    refs: tuple[str, ...] = ()


TABLES: tuple[TableSpec, ...] = (
    TableSpec(
        "00_scope_and_context.md",
        "分析対象機能scope一覧",
        (
            "Scope ID",
            "対象機能 / 領域",
            "UI操作判定",
            "Behavior Decomposition",
            "関連UNKNOWN ID",
            "関連仕様項目ID",
            "根拠 / 備考",
        ),
        "Scope ID",
        "SCOPE",
        refs=("関連UNKNOWN ID", "関連仕様項目ID"),
    ),
    TableSpec(
        "00_scope_and_context.md",
        "条件付き必須file applicability",
        (
            "ファイル",
            "Scope ID",
            "Trigger判定",
            "状態",
            "関連仕様項目ID",
            "根拠 / 備考",
            "関連UNKNOWN ID",
        ),
        refs=("関連仕様項目ID", "関連UNKNOWN ID"),
    ),
    TableSpec(
        "00_scope_and_context.md",
        "案件固有extension file一覧",
        (
            "ファイル",
            "Slug",
            "責務",
            "分割理由",
            "関連Scope ID",
            "関連仕様項目ID",
            "関連構造ID",
            "関連UNKNOWN ID",
        ),
        refs=("関連Scope ID", "関連仕様項目ID", "関連構造ID", "関連UNKNOWN ID"),
    ),
    TableSpec(
        "01_ui_structure_and_navigation.md",
        "UI構造一覧",
        (
            "構造ID",
            "種別",
            "名称",
            "状態軸",
            "Path / 識別子",
            "親構造ID",
            "関連仕様項目ID",
            "関連構造ID",
            "備考",
        ),
        "構造ID",
        refs=("親構造ID", "関連仕様項目ID", "関連構造ID"),
    ),
    TableSpec(
        "02_behavior_and_business_rules.md",
        "UI操作一覧",
        (
            "操作ID",
            "Scope ID",
            "Actor / Role",
            "対象構造ID",
            "操作",
            "関連仕様項目ID",
            "対応UC ID",
            "状態",
            "関連UNKNOWN ID",
        ),
        "操作ID",
        "UIOP",
        "状態",
        ("Scope ID", "対象構造ID", "関連仕様項目ID", "対応UC ID", "関連UNKNOWN ID"),
    ),
    TableSpec(
        "02_behavior_and_business_rules.md",
        "User Story一覧",
        (
            "US ID",
            "Scope ID",
            "Actor / Role",
            "Goal",
            "関連仕様項目ID",
            "関連構造ID",
            "状態",
            "関連UNKNOWN ID",
        ),
        "US ID",
        "US",
        "状態",
        ("Scope ID", "関連仕様項目ID", "関連構造ID", "関連UNKNOWN ID"),
    ),
    TableSpec(
        "02_behavior_and_business_rules.md",
        "Use Case一覧",
        (
            "UC ID",
            "関連US ID",
            "Use Case",
            "Trigger",
            "Preconditions",
            "Success Postcondition",
            "関連仕様項目ID",
            "関連構造ID",
            "状態",
            "関連UNKNOWN ID",
        ),
        "UC ID",
        "UC",
        "状態",
        ("関連US ID", "関連仕様項目ID", "関連構造ID", "関連UNKNOWN ID"),
    ),
    TableSpec(
        "02_behavior_and_business_rules.md",
        "Behavior一覧",
        (
            "Behavior ID",
            "UC ID",
            "関連操作ID",
            "結果分類",
            "振る舞い",
            "Postcondition / Result",
            "関連仕様項目ID",
            "関連構造ID",
            "状態",
            "関連UNKNOWN ID",
        ),
        "Behavior ID",
        "BH",
        "状態",
        ("UC ID", "関連操作ID", "関連仕様項目ID", "関連構造ID", "関連UNKNOWN ID"),
    ),
    TableSpec(
        "02_behavior_and_business_rules.md",
        "Use Case振る舞い完全性",
        (
            "UC ID",
            "結果分類",
            "判定",
            "関連Behavior ID",
            "関連仕様項目ID",
            "関連UNKNOWN ID",
            "理由 / 根拠",
        ),
        refs=("関連Behavior ID", "関連仕様項目ID", "関連UNKNOWN ID"),
    ),
    TableSpec(
        "02_behavior_and_business_rules.md",
        "Acceptance Criteria一覧",
        (
            "AC ID",
            "Behavior ID",
            "Acceptance Criteria",
            "関連仕様項目ID",
            "関連構造ID",
            "状態",
            "関連UNKNOWN ID",
        ),
        "AC ID",
        "AC",
        "状態",
        ("Behavior ID", "関連仕様項目ID", "関連構造ID", "関連UNKNOWN ID"),
    ),
    TableSpec(
        "02_behavior_and_business_rules.md",
        "ビジネスルール一覧",
        (
            "ルールID",
            "関連Scope ID",
            "ルール名",
            "ルール詳細",
            "適用条件",
            "関連仕様項目ID",
            "関連構造ID",
            "状態",
            "関連UNKNOWN ID",
            "備考",
        ),
        "ルールID",
        "RULE",
        "状態",
        ("関連Scope ID", "関連仕様項目ID", "関連構造ID", "関連UNKNOWN ID"),
    ),
    TableSpec(
        "03_fields_and_validation.md",
        "項目・バリデーション一覧",
        (
            "項目ID",
            "関連Scope ID",
            "対象構造ID",
            "ラベル / 名称",
            "要素タイプ",
            "入力 / 表示仕様",
            "制約 / バリデーション",
            "関連仕様項目ID",
            "状態",
            "関連UNKNOWN ID",
            "備考",
        ),
        "項目ID",
        "FIELD",
        "状態",
        ("関連Scope ID", "対象構造ID", "関連仕様項目ID", "関連UNKNOWN ID"),
    ),
    TableSpec(
        "04_flows_and_data.md",
        "処理フロー一覧",
        (
            "フローID",
            "関連Scope ID",
            "処理名",
            "トリガー / 操作",
            "手順 / 状態遷移",
            "結果",
            "関連仕様項目ID",
            "関連構造ID",
            "状態",
            "関連UNKNOWN ID",
            "備考",
        ),
        "フローID",
        "FLOW",
        "状態",
        ("関連Scope ID", "関連仕様項目ID", "関連構造ID", "関連UNKNOWN ID"),
    ),
    TableSpec(
        "05_notifications_and_external_interactions.md",
        "通知・外部連携一覧",
        (
            "連携ID",
            "関連Scope ID",
            "種別",
            "名称",
            "発火条件",
            "宛先 / 遷移先",
            "内容 / 挙動",
            "関連仕様項目ID",
            "関連構造ID",
            "状態",
            "関連UNKNOWN ID",
            "備考",
        ),
        "連携ID",
        status_column="状態",
        refs=("関連Scope ID", "関連仕様項目ID", "関連構造ID", "関連UNKNOWN ID"),
    ),
    TableSpec(
        "06_spec_inconsistencies_and_pending.md",
        "仕様矛盾・保留一覧",
        (
            "ISSUE ID",
            "種別",
            "内容",
            "根拠",
            "影響範囲",
            "関連仕様項目ID",
            "関連構造ID",
            "状態 / 扱い",
        ),
        "ISSUE ID",
        "ISSUE",
        refs=("関連仕様項目ID", "関連構造ID"),
    ),
    TableSpec(
        "07_current_unknowns.md",
        "Current UNKNOWN一覧",
        (
            "UNKNOWN ID",
            "確認事項",
            "根拠",
            "影響範囲",
            "関連Scope ID",
            "Blocking Scope ID",
            "関連File",
            "関連構造ID",
            "次の扱い",
        ),
        refs=("関連Scope ID", "Blocking Scope ID", "関連構造ID"),
    ),
    TableSpec(
        "08_repository_implementation_status.md",
        "Repository確認基準",
        (
            "Repository",
            "Branch / Ref",
            "Commit / Revision",
            "確認時点",
            "関連Scope ID",
            "備考",
        ),
        refs=("関連Scope ID",),
    ),
    TableSpec(
        "08_repository_implementation_status.md",
        "Repository実装状況",
        (
            "実装確認ID",
            "Repository",
            "関連Scope ID",
            "対象",
            "観測事実",
            "関連仕様項目ID",
            "判定",
            "証拠 / 参照",
            "備考",
        ),
        "実装確認ID",
        "IMPL",
        refs=("関連Scope ID", "関連仕様項目ID"),
    ),
    TableSpec(
        "09_authority_and_traceability.md",
        "情報源 / 正本参照一覧",
        (
            "参照ID",
            "情報源 / 正本一覧",
            "権威 / 優先順位",
            "鮮度 / バージョン",
            "対象範囲",
            "参照 / 備考",
        ),
        "参照ID",
        "SRC",
    ),
    TableSpec(
        "09_authority_and_traceability.md",
        "分析項目",
        (
            "項目ID",
            "カテゴリ",
            "内容",
            "分類",
            "情報源 / 正本参照",
            "現在有効か",
            "解消先ID",
            "補足 / 上書き / 置換関係",
            "備考",
        ),
        "項目ID",
        refs=("情報源 / 正本参照", "解消先ID"),
    ),
    TableSpec(
        "09_authority_and_traceability.md",
        "現在有効な仕様根拠",
        (
            "仕様根拠ID",
            "種別",
            "現在有効な内容",
            "適用範囲",
            "情報源 / 正本一覧",
            "関係",
            "関連仕様根拠ID",
        ),
        refs=("情報源 / 正本一覧", "関連仕様根拠ID"),
    ),
    TableSpec(
        "09_authority_and_traceability.md",
        "後続Skillへの補足",
        ("項目", "関連項目ID", "後続Skillへの関連 / 備考"),
        refs=("関連項目ID",),
    ),
)

TABLE_BY_KEY = {(spec.file, spec.section): spec for spec in TABLES}
CORE_FILES = (
    "README.md",
    "00_scope_and_context.md",
    "01_ui_structure_and_navigation.md",
    "02_behavior_and_business_rules.md",
    "06_spec_inconsistencies_and_pending.md",
    "07_current_unknowns.md",
    "09_authority_and_traceability.md",
    "CHANGELOG.md",
)
CONDITIONAL_FILES = (
    "03_fields_and_validation.md",
    "04_flows_and_data.md",
    "05_notifications_and_external_interactions.md",
    "08_repository_implementation_status.md",
)
CANONICAL_ORDER = (
    "README.md",
    "00_scope_and_context.md",
    "01_ui_structure_and_navigation.md",
    "02_behavior_and_business_rules.md",
    "03_fields_and_validation.md",
    "04_flows_and_data.md",
    "05_notifications_and_external_interactions.md",
    "06_spec_inconsistencies_and_pending.md",
    "07_current_unknowns.md",
    "08_repository_implementation_status.md",
    "09_authority_and_traceability.md",
)
PREFIXES = (
    "SRC",
    "SPEC",
    "INF",
    "UNK",
    "DEC",
    "ASM",
    "SCOPE",
    "PAGE",
    "STATE",
    "VIEW",
    "STEP",
    "MODAL",
    "BDLG",
    "PANEL",
    "EXT",
    "SHARED",
    "FIELD",
    "RULE",
    "FLOW",
    "NOTIFY",
    "INTERACT",
    "ISSUE",
    "IMPL",
    "UIOP",
    "US",
    "UC",
    "BH",
    "AC",
)
ALLOCATABLE_PREFIXES = set(PREFIXES) - {"DEC", "ASM"}
UI_PREFIXES = {
    "PAGE",
    "STATE",
    "VIEW",
    "STEP",
    "MODAL",
    "BDLG",
    "PANEL",
    "EXT",
    "SHARED",
}
DOMAIN_PREFIXES = {"FIELD", "RULE", "FLOW", "NOTIFY", "INTERACT"}
PREFIX_RE = {
    p: re.compile(rf"^{p}-[0-9]{{3}}$")
    if p in {"SRC", "SPEC", "INF", "UNK", "DEC", "ASM"}
    else re.compile(rf"^{p}-[0-9]{{3,}}$")
    for p in PREFIXES
}


def normalize_text(value: str) -> str:
    return value.replace("\r\n", "\n").replace("\r", "\n")


def canonical_bytes(text: str) -> bytes:
    return (normalize_text(text).rstrip("\n") + "\n").encode("utf-8")


def canonical_path(root: Path, rel: str) -> Path:
    if (
        not isinstance(rel, str)
        or not rel
        or "\\" in rel
        or rel.startswith("/")
        or re.match(r"^[A-Za-z]:", rel)
    ):
        fail(
            "path_outside_package",
            f"package pathがcanonical relative pathではありません: {rel!r}",
        )
    parts = rel.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        fail("path_outside_package", f"package pathがroot外を指します: {rel!r}")
    path = root.joinpath(*parts)
    try:
        resolved_root = root.resolve(strict=False)
        resolved_path = path.resolve(strict=False)
        resolved_path.relative_to(resolved_root)
    except (OSError, ValueError):
        fail("path_outside_package", f"package pathがroot外を指します: {rel!r}")
    return path


def _check_no_symlink(path: Path) -> None:
    try:
        info = path.lstat()
    except FileNotFoundError:
        return
    except OSError as exc:
        fail("file_unreadable", f"filesystem pathを確認できません: {path.name}: {exc}")
    if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & getattr(
        stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400
    ):
        fail(
            "symlink_not_allowed",
            f"symlink / reparse pointは許可されません: {path.name}",
        )


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _id_sort(value: str) -> tuple[str, int]:
    match = re.fullmatch(r"([A-Z]+)-([0-9]+)", value)
    if not match:
        return value, -1
    return match.group(1), int(match.group(2))


def _valid_id(value: str) -> bool:
    for prefix, pattern in PREFIX_RE.items():
        if value.startswith(prefix + "-"):
            return pattern.fullmatch(value) is not None
    return False


def _split_refs(cell: str, *, allow_draft: bool = False) -> list[str]:
    if not cell:
        return []
    values = cell.replace("<br>", "\n").split("\n")
    if any(not value or value != value.strip() for value in values):
        fail(
            "package_schema_mismatch",
            "stable referenceに空要素または余分な空白があります",
        )
    if len(set(values)) != len(values):
        fail("duplicate_id", "stable referenceが重複しています")
    for value in values:
        if allow_draft and re.fullmatch(r"@draft:[a-z0-9]+(?:-[a-z0-9]+)*", value):
            continue
        if not _valid_id(value):
            fail("package_schema_mismatch", f"stable ID形式が不正です: {value}")
    return values


def _encode_cell(value: str) -> str:
    value = normalize_text(value)
    if "<br>" in value:
        fail("invalid_input", "scalar table cellへliteral <br>は指定できません")
    return value.replace("\\", "\\\\").replace("|", "\\|").replace("\n", "<br>")


def _decode_cell(value: str) -> str:
    if "\n" in value:
        fail("package_schema_mismatch", "canonical table rowにraw LFがあります")
    out: list[str] = []
    i = 0
    while i < len(value):
        char = value[i]
        if char == "\\":
            if i + 1 >= len(value) or value[i + 1] not in {"\\", "|"}:
                fail("package_schema_mismatch", "ambiguous table escapeです")
            out.append(value[i + 1])
            i += 2
            continue
        out.append(char)
        i += 1
    decoded = "".join(out).replace("<br>", "\n")
    if _encode_cell(decoded) != value:
        fail("package_schema_mismatch", "table cellがcanonical encodeではありません")
    return decoded


def _split_markdown_row(line: str) -> list[str]:
    if not line.startswith("|") or not line.endswith("|"):
        fail("package_schema_mismatch", "Markdown table rowは両端を|で閉じてください")
    values: list[str] = []
    current: list[str] = []
    escaped = False
    for char in line[1:-1]:
        if escaped:
            current.extend(("\\", char))
            escaped = False
        elif char == "\\":
            escaped = True
        elif char == "|":
            values.append("".join(current).strip())
            current = []
        else:
            current.append(char)
    if escaped:
        fail("package_schema_mismatch", "table row末尾に孤立escapeがあります")
    values.append("".join(current).strip())
    return values


def _heading_span(text: str, heading: str) -> tuple[list[str], int, int]:
    lines = normalize_text(text).splitlines()
    indexes = [
        i
        for i, line in enumerate(lines)
        if line.strip() in {f"## {heading}", f"### {heading}"}
    ]
    if len(indexes) != 1:
        fail(
            "package_schema_mismatch",
            f"canonical headingがexactly oneではありません: {heading}",
        )
    start = indexes[0]
    level = len(lines[start]) - len(lines[start].lstrip("#"))
    end = len(lines)
    for i in range(start + 1, len(lines)):
        match = re.match(r"^(#{1,6})\s", lines[i])
        if match and len(match.group(1)) <= level:
            end = i
            break
    return lines, start, end


def parse_table(
    text: str, heading: str, expected_headers: tuple[str, ...]
) -> list[dict[str, str]]:
    lines, start, end = _heading_span(text, heading)
    table_lines: list[str] = []
    for line in lines[start + 1 : end]:
        if line.startswith("|"):
            table_lines.append(line)
        elif table_lines:
            break
    if len(table_lines) < 2:
        fail("package_schema_mismatch", f"structured tableがありません: {heading}")
    header = [_decode_cell(cell) for cell in _split_markdown_row(table_lines[0])]
    if tuple(header) != expected_headers:
        fail("package_schema_mismatch", f"table headerが不一致です: {heading}")
    separator = _split_markdown_row(table_lines[1])
    if len(separator) != len(expected_headers) or any(
        not re.fullmatch(r":?-{3,}:?", cell) for cell in separator
    ):
        fail("package_schema_mismatch", f"table separatorが不正です: {heading}")
    rows: list[dict[str, str]] = []
    for line in table_lines[2:]:
        cells = _split_markdown_row(line)
        if len(cells) != len(expected_headers):
            fail("package_schema_mismatch", f"table列数が不一致です: {heading}")
        decoded = [_decode_cell(cell) for cell in cells]
        rows.append(dict(zip(expected_headers, decoded, strict=True)))
    return rows


def render_table(headers: tuple[str, ...], rows: list[dict[str, str]]) -> str:
    output = [
        "| " + " | ".join(_encode_cell(value) for value in headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        output.append(
            "| "
            + " | ".join(_encode_cell(str(row.get(header, ""))) for header in headers)
            + " |"
        )
    return "\n".join(output)


def replace_table(
    text: str, heading: str, headers: tuple[str, ...], rows: list[dict[str, str]]
) -> str:
    lines, start, end = _heading_span(text, heading)
    first = next((i for i in range(start + 1, end) if lines[i].startswith("|")), None)
    if first is None:
        fail("package_schema_mismatch", f"structured tableがありません: {heading}")
    last = first
    while last + 1 < end and lines[last + 1].startswith("|"):
        last += 1
    lines[first : last + 1] = render_table(headers, rows).splitlines()
    return "\n".join(lines) + "\n"


def _empty_row(spec: TableSpec) -> dict[str, str]:
    return {header: "" for header in spec.headers}


def _parse_all_tables(
    files: dict[str, str],
) -> dict[tuple[str, str], list[dict[str, str]]]:
    result: dict[tuple[str, str], list[dict[str, str]]] = {}
    for spec in TABLES:
        if spec.file not in files:
            continue
        result[(spec.file, spec.section)] = parse_table(
            files[spec.file], spec.section, spec.headers
        )
    return result


def _table_index(
    tables: dict[tuple[str, str], list[dict[str, str]]],
) -> tuple[
    dict[str, tuple[TableSpec, dict[str, str]]],
    dict[str, tuple[TableSpec, dict[str, str]]],
]:
    by_id: dict[str, tuple[TableSpec, dict[str, str]]] = {}
    current_authorities: dict[str, tuple[TableSpec, dict[str, str]]] = {}
    seen: set[str] = set()
    for spec in TABLES:
        for row in tables.get((spec.file, spec.section), []):
            if spec.id_column:
                stable_id = row[spec.id_column]
                if not stable_id:
                    fail(
                        "package_schema_mismatch",
                        f"stable IDが空です: {spec.file}/{spec.section}",
                    )
                if not _valid_id(stable_id):
                    fail(
                        "package_schema_mismatch",
                        f"stable ID形式が不正です: {stable_id}",
                    )
                if stable_id in seen:
                    fail("duplicate_id", f"stable IDが重複しています: {stable_id}")
                seen.add(stable_id)
                by_id[stable_id] = (spec, row)
            if (
                spec.file == "09_authority_and_traceability.md"
                and spec.section == "分析項目"
                and row.get("現在有効か") == "Yes"
                and row.get("分類") in {"SPEC", "DECISION", "承認済みASM"}
            ):
                current_authorities[row["項目ID"]] = (spec, row)
    return by_id, current_authorities


def _all_ids(tables: dict[tuple[str, str], list[dict[str, str]]]) -> set[str]:
    values: set[str] = set()
    for rows in tables.values():
        for row in rows:
            for cell in row.values():
                for item in re.findall(
                    r"(?<![A-Za-z0-9@])(?:[A-Z]+-[0-9]{3,})(?![A-Za-z0-9])", cell
                ):
                    if _valid_id(item):
                        values.add(item)
    return values


def _tracked_ids(tables: dict[tuple[str, str], list[dict[str, str]]]) -> set[str]:
    return {
        row[spec.id_column]
        for spec in TABLES
        if spec.id_column
        for row in tables.get((spec.file, spec.section), [])
    }


def _read_regular_file(root: Path, rel: str) -> bytes:
    path = canonical_path(root, rel)
    _check_no_symlink(path)
    try:
        info = path.stat()
        if not stat.S_ISREG(info.st_mode):
            fail("package_schema_mismatch", f"regular fileではありません: {rel}")
        raw = path.read_bytes()
    except PackageError:
        raise
    except OSError as exc:
        fail("file_unreadable", f"fileを読めません: {rel}: {exc}")
    return raw


def _decode_current(raw: bytes, rel: str) -> str:
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        fail("package_schema_mismatch", f"UTF-8ではありません: {rel}")
    if (
        text.startswith("\ufeff")
        or "\r" in text
        or not text.endswith("\n")
        or text.endswith("\n\n")
    ):
        fail(
            "package_schema_mismatch",
            f"canonical UTF-8 / LF / terminal LFではありません: {rel}",
        )
    return text


def _root_file_set(root: Path) -> set[str]:
    _check_no_symlink(root)
    try:
        entries = list(root.iterdir())
    except OSError as exc:
        fail("file_unreadable", f"package directoryを読めません: {exc}")
    result: set[str] = set()
    normalized: set[str] = set()
    for entry in entries:
        _check_no_symlink(entry)
        try:
            mode = entry.stat().st_mode
        except OSError as exc:
            fail(
                "file_unreadable", f"package entryを確認できません: {entry.name}: {exc}"
            )
        if not stat.S_ISREG(mode):
            fail(
                "package_schema_mismatch",
                f"package直下はcanonical regular filesだけ許可されます: {entry.name}",
            )
        name = entry.name
        normalized_name = name.casefold()
        if normalized_name in normalized:
            fail(
                "package_schema_mismatch",
                f"case-insensitive filename collisionです: {name}",
            )
        normalized.add(normalized_name)
        result.add(name)
    return result


def _parse_metadata(readme: str) -> dict[str, str]:
    rows = parse_table(readme, "Package metadata", ("項目", "値"))
    values: dict[str, str] = {}
    for row in rows:
        key = row["項目"]
        if key in values:
            fail(
                "package_schema_mismatch", f"README metadata keyが重複しています: {key}"
            )
        values[key] = row["値"]
    expected = {
        "Package Schema Version",
        "Package Version",
        "Previous Package Version",
        "Current UNKNOWN Count",
        "Completion Status",
        "Ready Scope Count",
        "Blocked Scope Count",
    }
    if set(values) != expected:
        fail("package_schema_mismatch", "README metadata row集合が不一致です")
    return values


def _parse_json_fence(text: str, heading: str) -> Any:
    lines, start, end = _heading_span(text, heading)
    blocks = []
    for i in range(start + 1, end - 2):
        if lines[i] == "```json" and lines[i + 2] == "```":
            blocks.append(lines[i + 1])
    if len(blocks) != 1:
        fail(
            "package_schema_mismatch",
            f"canonical JSON fenceがexactly oneではありません: {heading}",
        )
    try:
        return strict_loads(blocks[0].encode("utf-8"), aggregate=True)
    except RuntimeErrorBase as exc:
        fail(
            "package_schema_mismatch", f"JSON fenceが不正です: {heading}: {exc.message}"
        )


def _parse_manifest(
    text: str,
) -> tuple[dict[str, str], list[dict[str, str]], dict[str, Any]]:
    lines = normalize_text(text).splitlines()
    schema_rows = [
        line for line in lines if line.startswith("Package Schema Version: ")
    ]
    version_rows = [line for line in lines if line.startswith("Package Version: ")]
    if len(schema_rows) != 1 or len(version_rows) != 1:
        fail(
            "package_schema_mismatch",
            "MANIFEST package schema/version headerが不正です",
        )
    heading_lines, _, _ = _heading_span(text, "Package manifest")
    table_rows = parse_table(text, "Package manifest", ("順序", "ファイル", "SHA-256"))
    receipt = _parse_json_fence(text, "Last materialize receipt")
    if not isinstance(receipt, dict):
        fail(
            "package_schema_mismatch",
            "Last materialize receiptはobjectである必要があります",
        )
    return (
        {
            "Package Schema Version": schema_rows[0].split(": ", 1)[1],
            "Package Version": version_rows[0].split(": ", 1)[1],
        },
        table_rows,
        receipt,
    )


def _parse_readme_payloads(readme: str) -> list[dict[str, str]]:
    return parse_table(readme, "Current payload files", ("順序", "ファイル", "種別"))


def _manifest_payload_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    result = []
    expected_order = 1
    for row in rows:
        try:
            order = int(row["順序"])
        except ValueError:
            fail("manifest_mismatch", "MANIFEST順序が整数ではありません")
        if order != expected_order:
            fail(
                "manifest_mismatch",
                "MANIFEST file orderがcanonical sequenceではありません",
            )
        if not re.fullmatch(r"[0-9a-f]{64}", row["SHA-256"]):
            fail(
                "manifest_mismatch",
                f"MANIFEST SHA-256形式が不正です: {row['ファイル']}",
            )
        result.append(row)
        expected_order += 1
    return result


def _extension_paths(tables: dict[tuple[str, str], list[dict[str, str]]]) -> list[str]:
    rows = tables.get(("00_scope_and_context.md", "案件固有extension file一覧"), [])
    result: list[str] = []
    slugs: set[str] = set()
    for row in rows:
        path = row["ファイル"]
        slug = row["Slug"]
        if not re.fullmatch(
            r"(?:1[0-9]|[2-9][0-9]+)_[a-z0-9]+(?:-[a-z0-9]+)*\.md", path
        ):
            fail(
                "package_schema_mismatch",
                f"extension pathがcanonicalではありません: {path}",
            )
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
            fail(
                "package_schema_mismatch",
                f"extension slugがcanonicalではありません: {slug}",
            )
        if slug in slugs or path in result:
            fail("duplicate_id", f"extension path / slugが重複しています: {path}")
        slugs.add(slug)
        result.append(path)
    numbers = [int(path.split("_", 1)[0]) for path in result]
    if numbers != sorted(set(numbers)):
        fail("package_schema_mismatch", "extension fileが番号順ではありません")
    return result


def _ordered_payloads(
    tables: dict[tuple[str, str], list[dict[str, str]]], file_set: set[str]
) -> list[str]:
    extension_paths = _extension_paths(tables)
    known = set(CORE_FILES) | set(CONDITIONAL_FILES) | set(extension_paths)
    unexpected = file_set - known - {"MANIFEST.md"}
    missing_core = set(CORE_FILES) - file_set
    if unexpected or missing_core or set(extension_paths) - file_set:
        fail(
            "package_schema_mismatch",
            f"package file setが不正です (missing={sorted(missing_core | (set(extension_paths) - file_set))}, unexpected={sorted(unexpected)})",
        )
    if file_set & set(CONDITIONAL_FILES):
        applicability = tables.get(
            ("00_scope_and_context.md", "条件付き必須file applicability"), []
        )
        by_file: dict[str, set[str]] = {name: set() for name in CONDITIONAL_FILES}
        for row in applicability:
            if row["状態"] in {"required", "blocked"}:
                by_file[row["ファイル"]].add(row["状態"])
        for name in CONDITIONAL_FILES:
            should_exist = "required" in by_file[name] or (
                "blocked" in by_file[name] and name in file_set
            )
            if (name in file_set) != should_exist:
                fail(
                    "package_schema_mismatch",
                    f"conditional payload file applicabilityとfile setが不一致です: {name}",
                )
    else:
        applicability = tables.get(
            ("00_scope_and_context.md", "条件付き必須file applicability"), []
        )
        if applicability and any(row["状態"] == "required" for row in applicability):
            fail(
                "package_schema_mismatch",
                "required conditional payload fileがありません",
            )
    ordered = [name for name in CANONICAL_ORDER if name in file_set]
    ordered.extend(
        sorted(extension_paths, key=lambda value: int(value.split("_", 1)[0]))
    )
    ordered.append("CHANGELOG.md")
    return ordered


@dataclass
class PackageModel:
    root: Path
    files: dict[str, str]
    raw_files: dict[str, bytes]
    tables: dict[tuple[str, str], list[dict[str, str]]]
    metadata: dict[str, str]
    manifest_metadata: dict[str, str]
    manifest_rows: list[dict[str, str]]
    receipt: dict[str, Any]
    payload_paths: list[str]
    by_id: dict[str, tuple[TableSpec, dict[str, str]]]
    current_authorities: dict[str, tuple[TableSpec, dict[str, str]]]


def _read_package(root: Path, *, validate_content: bool = True) -> PackageModel:
    _check_no_symlink(root)
    try:
        info = root.stat()
    except OSError as exc:
        fail("file_unreadable", f"package rootを確認できません: {exc}")
    if not stat.S_ISDIR(info.st_mode):
        fail("package_schema_mismatch", "package_rootはdirectoryである必要があります")
    file_set = _root_file_set(root)
    total = 0
    raw_files: dict[str, bytes] = {}
    files: dict[str, str] = {}
    for rel in sorted(file_set):
        raw = _read_regular_file(root, rel)
        total += len(raw)
        if total > MAX_PACKAGE_BYTES:
            fail("limit_exceeded", "current UI target packageが16 MiBを超えています")
        raw_files[rel] = raw
        files[rel] = _decode_current(raw, rel)
    if "MANIFEST.md" not in files:
        fail("package_schema_mismatch", "MANIFEST.mdがありません")
    for rel in CORE_FILES:
        if rel not in files:
            fail(
                "package_schema_mismatch",
                f"required core payload fileがありません: {rel}",
            )
    tables = _parse_all_tables(files)
    ordered_paths = _ordered_payloads(tables, file_set)
    metadata = _parse_metadata(files["README.md"])
    manifest_metadata, manifest_rows, receipt = _parse_manifest(files["MANIFEST.md"])
    readme_rows = _parse_readme_payloads(files["README.md"])
    readme_paths = [row["ファイル"] for row in readme_rows]
    manifest_rows = _manifest_payload_rows(manifest_rows)
    manifest_paths = [row["ファイル"] for row in manifest_rows]
    if readme_paths != ordered_paths or manifest_paths != ordered_paths:
        fail(
            "manifest_mismatch",
            "README / MANIFEST payload file setまたはorderが一致しません",
        )
    if any(row["種別"] != _file_kind(row["ファイル"]) for row in readme_rows):
        fail("manifest_mismatch", "README payload file kindが不一致です")
    if (
        manifest_metadata.get("Package Schema Version") != SCHEMA_VERSION
        or metadata.get("Package Schema Version") != SCHEMA_VERSION
    ):
        fail(
            "package_schema_mismatch",
            "Package Schema Versionがui-target-v1ではありません",
        )
    package_version = metadata.get("Package Version", "")
    if (
        not re.fullmatch(r"v[0-9]{2,}", package_version)
        or manifest_metadata.get("Package Version") != package_version
    ):
        fail(
            "package_schema_mismatch", "Package Versionが不正またはMANIFESTと不一致です"
        )
    previous_version = metadata.get("Previous Package Version", "")
    current_number = int(package_version[1:])
    if previous_version == "-":
        if package_version != "v00":
            fail(
                "package_schema_mismatch",
                "Previous Package Version=-はv00だけ許可されます",
            )
    elif previous_version == "legacy-unversioned":
        if package_version != "v00":
            fail(
                "package_schema_mismatch",
                "legacy-unversioned migrationはv00で開始します",
            )
    elif re.fullmatch(r"v[0-9]{2,}", previous_version):
        if current_number != int(previous_version[1:]) + 1:
            fail(
                "package_schema_mismatch",
                "Package VersionとPrevious Package Versionが1 revision差ではありません",
            )
    else:
        fail("package_schema_mismatch", "Previous Package Versionが不正です")
    if validate_content:
        for index, rel in enumerate(ordered_paths, start=1):
            row = manifest_rows[index - 1]
            if (
                int(row["順序"]) != index
                or row["ファイル"] != rel
                or row["SHA-256"] != _sha(raw_files[rel])
            ):
                fail("manifest_mismatch", f"MANIFEST hash / orderが不一致です: {rel}")
        by_id, authorities = _table_index(tables)
        model = PackageModel(
            root,
            files,
            raw_files,
            tables,
            metadata,
            manifest_metadata,
            manifest_rows,
            receipt,
            ordered_paths,
            by_id,
            authorities,
        )
        _validate_semantics(model)
        progress = _scope_progress(model, check_closure=True)
        current_unknown_count = sum(
            1
            for row in _current_item_rows(model)
            if row["分類"] == "UNKNOWN" and row["現在有効か"] == "Yes"
        )
        try:
            unknown_count = int(metadata["Current UNKNOWN Count"])
            ready_count = int(metadata["Ready Scope Count"])
            blocked_count = int(metadata["Blocked Scope Count"])
        except (KeyError, ValueError):
            fail(
                "package_schema_mismatch", "README generated countが整数ではありません"
            )
        if (
            metadata["Completion Status"] != progress["completion_status"]
            or unknown_count != current_unknown_count
            or ready_count != len(progress["ready_scope_ids"])
            or blocked_count != len(progress["blocked_scope_ids"])
        ):
            fail(
                "package_schema_mismatch",
                "README progress controlsがcurrent packageと不一致です",
            )
        generated_readme = dict(files)
        _make_readme(
            generated_readme,
            package_version,
            previous_version,
            progress,
            ordered_paths,
            current_unknown_count,
        )
        if generated_readme["README.md"] != files["README.md"]:
            fail(
                "package_schema_mismatch",
                "README generated controlsがcanonical outputと不一致です",
            )
        receipt_keys = {
            "receipt_version",
            "request_fingerprint",
            "artifact_mode",
            "change_mode",
            "changed",
            "allocated_ids",
            "allocated_extension_files",
            "retired_ids",
            "retired_extension_files",
            "changed_files",
            "previous_package_version",
            "package_version",
        }
        if (
            set(receipt) != receipt_keys
            or receipt.get("receipt_version") != RECEIPT_VERSION
        ):
            fail("manifest_mismatch", "materialize receipt versionが不正です")
        if not re.fullmatch(
            r"sha256:[0-9a-f]{64}", str(receipt.get("request_fingerprint", ""))
        ):
            fail("manifest_mismatch", "materialize receipt fingerprintが不正です")
        if receipt.get("package_version") != package_version:
            fail("manifest_mismatch", "materialize receipt package_versionが不一致です")
        if receipt.get("artifact_mode") not in {"create", "update"} or receipt.get(
            "change_mode"
        ) not in {"normal", "legacy-migration"}:
            fail("manifest_mismatch", "materialize receipt modeが不正です")
        if receipt.get("changed") is not True:
            fail(
                "manifest_mismatch",
                "committed package receipt changedはtrueである必要があります",
            )
        for field in (
            "allocated_ids",
            "allocated_extension_files",
            "retired_ids",
            "retired_extension_files",
            "changed_files",
        ):
            if not isinstance(receipt.get(field), list):
                fail("manifest_mismatch", f"materialize receipt {field}はarrayです")
        if any(
            not isinstance(row, dict)
            or set(row) != {"draft_key", "stable_id"}
            or not isinstance(row["draft_key"], str)
            or not _valid_id(row["stable_id"])
            for row in receipt["allocated_ids"]
        ):
            fail("manifest_mismatch", "receipt allocated_ids schemaが不正です")
        if any(
            not isinstance(row, dict)
            or set(row) != {"draft_key", "path"}
            or not isinstance(row["draft_key"], str)
            or not isinstance(row["path"], str)
            for row in receipt["allocated_extension_files"]
        ):
            fail(
                "manifest_mismatch",
                "receipt allocated_extension_files schemaが不正です",
            )
        if any(
            not isinstance(value, str) or not _valid_id(value)
            for value in receipt["retired_ids"]
        ) or any(
            not isinstance(value, str) for value in receipt["retired_extension_files"]
        ):
            fail("manifest_mismatch", "receipt retired IDs / pathsが不正です")
        canonical_changed = set(CORE_FILES) | set(CONDITIONAL_FILES) | {"MANIFEST.md"}
        if any(
            not isinstance(value, str)
            or (
                value not in canonical_changed
                and not re.fullmatch(
                    r"(?:1[0-9]|[2-9][0-9]+)_[a-z0-9]+(?:-[a-z0-9]+)*\.md", value
                )
            )
            for value in receipt["changed_files"]
        ):
            fail("manifest_mismatch", "receipt changed_files pathが不正です")
        if len(receipt["changed_files"]) != len(set(receipt["changed_files"])):
            fail("manifest_mismatch", "receipt changed_filesが重複しています")
        if len({row["draft_key"] for row in receipt["allocated_ids"]}) != len(
            receipt["allocated_ids"]
        ) or len({row["stable_id"] for row in receipt["allocated_ids"]}) != len(
            receipt["allocated_ids"]
        ):
            fail("manifest_mismatch", "receipt allocated_idsが重複しています")
        if len({row["path"] for row in receipt["allocated_extension_files"]}) != len(
            receipt["allocated_extension_files"]
        ):
            fail(
                "manifest_mismatch", "receipt allocated extension pathが重複しています"
            )
        if (
            receipt["change_mode"] == "legacy-migration"
            and receipt["artifact_mode"] != "create"
        ):
            fail(
                "manifest_mismatch",
                "legacy migration receiptはcreateである必要があります",
            )
        if receipt.get("previous_package_version") != previous_version:
            fail("manifest_mismatch", "receipt previous_package_versionが不一致です")
        _validate_changelog(files["CHANGELOG.md"], package_version)
        _validate_lifecycle_consistency(model)
        _validate_machine_entities(model)
        return model
    by_id, authorities = _table_index(tables)
    return PackageModel(
        root,
        files,
        raw_files,
        tables,
        metadata,
        manifest_metadata,
        manifest_rows,
        receipt,
        ordered_paths,
        by_id,
        authorities,
    )


def _rows(model: PackageModel, file: str, section: str) -> list[dict[str, str]]:
    return model.tables.get((file, section), [])


def _refs(row: dict[str, str], column: str) -> list[str]:
    return _split_refs(row.get(column, ""))


def _id_prefix(stable_id: str) -> str:
    return stable_id.split("-", 1)[0]


def _authority_ids(row: dict[str, str]) -> list[str]:
    return [
        value
        for value in _refs(row, "関連仕様項目ID")
        if _id_prefix(value) in {"SPEC", "DECISION", "ASM", "INF"}
    ]


def _current_item_rows(model: PackageModel) -> list[dict[str, str]]:
    return _rows(model, "09_authority_and_traceability.md", "分析項目")


def _unknown_rows(model: PackageModel) -> list[dict[str, str]]:
    return _rows(model, "07_current_unknowns.md", "Current UNKNOWN一覧")


def _scope_rows(model: PackageModel) -> list[dict[str, str]]:
    return _rows(model, "00_scope_and_context.md", "分析対象機能scope一覧")


def _scope_by_id(model: PackageModel) -> dict[str, dict[str, str]]:
    return {row["Scope ID"]: row for row in _scope_rows(model)}


def _validate_semantics(model: PackageModel) -> None:
    tables = model.tables
    by_id, _ = _table_index(tables)
    # Validate every stable-reference cell against the package-local identity set.
    for spec in TABLES:
        for row in tables.get((spec.file, spec.section), []):
            for column in spec.refs:
                for stable_id in _refs(row, column):
                    if stable_id not in by_id:
                        fail(
                            "reference_not_found",
                            f"参照先stable IDがありません: {stable_id} ({spec.file}/{spec.section})",
                        )
                    allowed_prefixes = {
                        "関連UNKNOWN ID": {"UNK"},
                        "関連Scope ID": {"SCOPE"},
                        "Blocking Scope ID": {"SCOPE"},
                        "Scope ID": {"SCOPE"},
                        "対象構造ID": UI_PREFIXES,
                        "親構造ID": UI_PREFIXES,
                        "関連構造ID": UI_PREFIXES | DOMAIN_PREFIXES,
                        "対応UC ID": {"UC"},
                        "関連US ID": {"US"},
                        "UC ID": {"UC"},
                        "Behavior ID": {"BH"},
                        "関連Behavior ID": {"BH"},
                        "関連操作ID": {"UIOP"},
                        "関連仕様項目ID": {"SPEC", "DEC", "ASM", "INF"},
                        "情報源 / 正本参照": {"SRC"},
                        "情報源 / 正本一覧": {"SRC"},
                        "関連仕様根拠ID": {"SPEC", "DEC", "ASM"},
                        "解消先ID": {"SPEC", "DEC", "ASM"},
                        "関連項目ID": {"SRC", "SPEC", "INF", "UNK", "DEC", "ASM"},
                    }.get(column)
                    if (
                        allowed_prefixes is not None
                        and _id_prefix(stable_id) not in allowed_prefixes
                    ):
                        fail(
                            "package_schema_mismatch",
                            f"stable reference prefixが不正です: {column}={stable_id}",
                        )
    # The analysis-item ID is both the canonical identity ledger and the only
    # source of current Authority / UNKNOWN records.
    items = _current_item_rows(model)
    item_by_id: dict[str, dict[str, str]] = {}
    for row in items:
        stable_id = row["項目ID"]
        category = row["分類"]
        prefix = {
            "SPEC": "SPEC",
            "INFERENCE": "INF",
            "UNKNOWN": "UNK",
            "DECISION": "DEC",
            "承認済みASM": "ASM",
        }.get(category)
        if prefix is None or _id_prefix(stable_id) != prefix:
            fail(
                "package_schema_mismatch",
                f"分析項目の分類とstable ID prefixが不一致です: {stable_id}/{category}",
            )
        if row["現在有効か"] not in {"Yes", "No"}:
            fail(
                "package_schema_mismatch",
                f"分析項目の現在有効かが不正です: {stable_id}",
            )
        item_by_id[stable_id] = row
        if category == "UNKNOWN":
            resolved = row["現在有効か"] == "No"
            targets = _refs(row, "解消先ID")
            if resolved and not targets:
                fail(
                    "package_schema_mismatch",
                    f"resolved UNKNOWNに解消先IDがありません: {stable_id}",
                )
            if not resolved and targets:
                fail(
                    "package_schema_mismatch",
                    f"current UNKNOWNに解消先IDがあります: {stable_id}",
                )
            for target in targets:
                target_row = item_by_id.get(target)
                if target_row is not None and (
                    target_row["分類"] not in {"SPEC", "DECISION", "承認済みASM"}
                    or target_row["現在有効か"] != "Yes"
                ):
                    fail(
                        "reference_not_found",
                        f"UNKNOWN解消先がcurrent Authorityではありません: {target}",
                    )
        elif row["解消先ID"]:
            fail(
                "package_schema_mismatch",
                f"UNKNOWN以外に解消先IDがあります: {stable_id}",
            )
    for row in items:
        if row["分類"] == "UNKNOWN" and row["現在有効か"] == "No":
            for target in _refs(row, "解消先ID"):
                target_row = item_by_id.get(target)
                if (
                    target_row is None
                    or target_row["分類"] not in {"SPEC", "DECISION", "承認済みASM"}
                    or target_row["現在有効か"] != "Yes"
                ):
                    fail(
                        "reference_not_found",
                        f"UNKNOWN解消先がcurrent Authorityではありません: {target}",
                    )
    # Current effective Authority is a derived mirror, not a second source.
    expected_authorities = {
        row["項目ID"]
        for row in items
        if row["分類"] in {"SPEC", "DECISION", "承認済みASM"}
        and row["現在有効か"] == "Yes"
    }
    effective_rows = _rows(
        model, "09_authority_and_traceability.md", "現在有効な仕様根拠"
    )
    effective_ids = [row["仕様根拠ID"] for row in effective_rows]
    if (
        len(effective_ids) != len(set(effective_ids))
        or set(effective_ids) != expected_authorities
    ):
        fail(
            "package_schema_mismatch",
            "現在有効な仕様根拠とcurrent Authority itemが一致しません",
        )
    # Validate exact item prefix selectors for all package stable-ID records.
    for row in tables.get(("01_ui_structure_and_navigation.md", "UI構造一覧"), []):
        expected_prefix = {
            "PAGE": "PAGE",
            "STATE": "STATE",
            "VIEW": "VIEW",
            "STEP": "STEP",
            "MODAL": "MODAL",
            "BROWSER-DIALOG": "BDLG",
            "PANEL": "PANEL",
            "POPOVER": "PANEL",
            "GLOBAL UI": "PANEL",
            "EXTERNAL": "EXT",
            "SHARED PAGE": "SHARED",
        }.get(row["種別"])
        if expected_prefix is None or _id_prefix(row["構造ID"]) != expected_prefix:
            fail(
                "package_schema_mismatch",
                f"UI構造の種別とID prefixが不一致です: {row['構造ID']}/{row['種別']}",
            )
        if (row["種別"] == "STATE") != bool(row["状態軸"]):
            fail(
                "package_schema_mismatch",
                f"STATE rowだけ状態軸が必要です: {row['構造ID']}",
            )
        if row["種別"] not in {"STATE"} and row["状態軸"]:
            fail(
                "package_schema_mismatch",
                f"STATE以外の状態軸は空である必要があります: {row['構造ID']}",
            )
        if (
            row["Path / 識別子"]
            and row["Path / 識別子"] != "PATH-TBD"
            and "\n" in row["Path / 識別子"]
        ):
            fail(
                "package_schema_mismatch",
                f"UI構造Pathに改行は使えません: {row['構造ID']}",
            )
    # Scope enum and helper-derived behavior decomposition.
    for row in _scope_rows(model):
        expected = {
            "あり": "required",
            "なし": "not-applicable",
            "未確定": "blocked",
        }.get(row["UI操作判定"])
        if expected is None or row["Behavior Decomposition"] != expected:
            fail(
                "package_schema_mismatch",
                f"Scope Behavior Decompositionが固定対応と不一致です: {row['Scope ID']}",
            )
        if expected == "blocked" and not _refs(row, "関連UNKNOWN ID"):
            fail(
                "state_transition_required",
                f"UI操作判定=未確定のScopeにUNKNOWNがありません: {row['Scope ID']}",
            )
    # Conditional applicability is exactly four rows per current Scope, with
    # status derived from its semantic trigger.
    scope_ids = set(_scope_by_id(model))
    applicability = _rows(
        model, "00_scope_and_context.md", "条件付き必須file applicability"
    )
    expected_app = {
        (file, scope_id) for file in CONDITIONAL_FILES for scope_id in scope_ids
    }
    actual_app: set[tuple[str, str]] = set()
    for row in applicability:
        key = (row["ファイル"], row["Scope ID"])
        if key in actual_app:
            fail("duplicate_id", f"file applicability keyが重複しています: {key}")
        actual_app.add(key)
        if row["ファイル"] not in CONDITIONAL_FILES or row["Scope ID"] not in scope_ids:
            fail(
                "reference_not_found",
                f"file applicabilityのfile / Scopeが不正です: {key}",
            )
        expected_state = {
            "あり": "required",
            "なし": "not-applicable",
            "未確定": "blocked",
        }.get(row["Trigger判定"])
        if expected_state is None or row["状態"] != expected_state:
            fail(
                "package_schema_mismatch",
                f"file applicability状態がTriggerから導出されていません: {key}",
            )
        if expected_state == "blocked" and not _refs(row, "関連UNKNOWN ID"):
            fail(
                "state_transition_required",
                f"未確定file applicabilityにUNKNOWNがありません: {key}",
            )
    if actual_app != expected_app:
        fail(
            "package_schema_mismatch",
            "current Scopeごとにfile applicabilityを4件持つ必要があります",
        )
    app_state = {
        (row["ファイル"], row["Scope ID"]): row["状態"] for row in applicability
    }
    domain_owner = {
        "FIELD": "03_fields_and_validation.md",
        "FLOW": "04_flows_and_data.md",
        "NOTIFY": "05_notifications_and_external_interactions.md",
        "INTERACT": "05_notifications_and_external_interactions.md",
        "IMPL": "08_repository_implementation_status.md",
    }
    for spec in TABLES:
        if not spec.id_column:
            continue
        for row in tables.get((spec.file, spec.section), []):
            row_prefix = _id_prefix(row[spec.id_column])
            if row_prefix not in domain_owner:
                continue
            for scope_id in _refs(row, "関連Scope ID"):
                if (
                    app_state.get((domain_owner[row_prefix], scope_id))
                    == "not-applicable"
                ):
                    fail(
                        "state_transition_required",
                        f"not-applicable scopeにdomain itemがあります: {row_prefix}/{scope_id}",
                    )
    _validate_tracking_states(model)
    _validate_hierarchies(model)
    _scope_progress(model, check_closure=True)


def _validate_tracking_states(model: PackageModel) -> None:
    specs_with_state = [spec for spec in TABLES if spec.status_column]
    unknown_ids = {row["UNKNOWN ID"] for row in _unknown_rows(model)}
    analysis = {row["項目ID"]: row for row in _current_item_rows(model)}
    unknown_rows = {row["UNKNOWN ID"]: row for row in _unknown_rows(model)}
    stories = {
        row["US ID"]: row
        for row in _rows(model, "02_behavior_and_business_rules.md", "User Story一覧")
    }
    cases = {
        row["UC ID"]: row
        for row in _rows(model, "02_behavior_and_business_rules.md", "Use Case一覧")
    }
    behaviors = {
        row["Behavior ID"]: row
        for row in _rows(model, "02_behavior_and_business_rules.md", "Behavior一覧")
    }
    if unknown_ids != {
        row["項目ID"]
        for row in _current_item_rows(model)
        if row["分類"] == "UNKNOWN" and row["現在有効か"] == "Yes"
    }:
        fail(
            "package_schema_mismatch",
            "Current UNKNOWN tableが分析項目のcurrent UNKNOWN集合と一致しません",
        )

    def ancestor_blocked(spec: TableSpec, row: dict[str, str]) -> bool:
        if spec.section == "Use Case一覧":
            parents = [stories[value] for value in _refs(row, "関連US ID")]
            return any(parent["状態"] == "blocked" for parent in parents)
        if spec.section == "Behavior一覧":
            parent = cases.get(row["UC ID"])
            return parent is not None and parent["状態"] == "blocked"
        if spec.section == "Acceptance Criteria一覧":
            parent = behaviors.get(row["Behavior ID"])
            return parent is not None and parent["状態"] == "blocked"
        return False

    def scope_for(spec: TableSpec, row: dict[str, str]) -> str | None:
        if spec.section in {"UI操作一覧", "User Story一覧"}:
            refs = _refs(row, "Scope ID")
            return refs[0] if len(refs) == 1 else None
        if spec.section == "Use Case一覧":
            parents = [stories[value] for value in _refs(row, "関連US ID")]
            scopes = {
                _refs(parent, "Scope ID")[0]
                for parent in parents
                if _refs(parent, "Scope ID")
            }
            return next(iter(scopes)) if len(scopes) == 1 else None
        if spec.section == "Behavior一覧":
            uc = cases.get(row["UC ID"])
            return (
                scope_for(
                    TABLE_BY_KEY[("02_behavior_and_business_rules.md", "Use Case一覧")],
                    uc,
                )
                if uc
                else None
            )
        if spec.section == "Acceptance Criteria一覧":
            behavior = behaviors.get(row["Behavior ID"])
            return (
                scope_for(
                    TABLE_BY_KEY[("02_behavior_and_business_rules.md", "Behavior一覧")],
                    behavior,
                )
                if behavior
                else None
            )
        refs = _refs(row, "関連Scope ID") if row.get("関連Scope ID") else []
        return refs[0] if len(refs) == 1 else None

    def require_root_blocker(
        unknown_id: str, scope_id: str | None, stable_id: str
    ) -> None:
        unknown = unknown_rows[unknown_id]
        related_files = (
            unknown["関連File"].replace("<br>", "\n").split("\n")
            if unknown["関連File"]
            else []
        )
        if (
            scope_id is None
            or scope_id not in _refs(unknown, "Blocking Scope ID")
            or "02_behavior_and_business_rules.md" not in related_files
        ):
            fail(
                "state_transition_required",
                f"階層rowのUNKNOWN blocker scope / related fileが不正です: {stable_id}/{unknown_id}",
            )

    for spec in specs_with_state:
        rows = _rows(model, spec.file, spec.section)
        for row in rows:
            stable_id = row[spec.id_column] if spec.id_column else None
            unknown_refs = _refs(row, "関連UNKNOWN ID")
            if any(value not in unknown_ids for value in unknown_refs):
                fail(
                    "reference_not_found",
                    f"rowがcurrent UNKNOWN以外を参照しています: {stable_id}",
                )
            if any(analysis[value]["現在有効か"] != "Yes" for value in unknown_refs):
                fail(
                    "reference_not_found",
                    f"rowがinactive UNKNOWNを参照しています: {stable_id}",
                )
            allowed_states = (
                {"mapped", "blocked"}
                if spec.section == "UI操作一覧"
                else {"current", "blocked"}
            )
            if row[spec.status_column] not in allowed_states:
                fail("package_schema_mismatch", f"state enumが不正です: {stable_id}")
            required = _required_fields(spec, row)
            missing = any(not row.get(field, "").strip() for field in required)
            has_ancestor_blocker = ancestor_blocked(spec, row)
            normal_state = "mapped" if spec.section == "UI操作一覧" else "current"
            if row[spec.status_column] == normal_state:
                if missing or unknown_refs or has_ancestor_blocker:
                    fail(
                        "state_transition_required",
                        f"current rowに必須field不足 / blocker / blocked ancestorがあります: {stable_id}",
                    )
            else:
                minimum = _blocked_minimum_fields(spec)
                if any(not row.get(field, "").strip() for field in minimum):
                    fail(
                        "state_transition_required",
                        f"blocked rowにidentity closure用の必須fieldがありません: {stable_id}",
                    )
                if spec.section == "User Story一覧" and not (
                    row["Actor / Role"].strip() or row["Goal"].strip()
                ):
                    fail(
                        "state_transition_required",
                        f"blocked USはActor / RoleまたはGoalを必要とします: {stable_id}",
                    )
                if not unknown_refs and not has_ancestor_blocker:
                    fail(
                        "state_transition_required",
                        f"blocked rowに自身またはancestorのroot causeがありません: {stable_id}",
                    )
                if missing and not unknown_refs and not has_ancestor_blocker:
                    fail(
                        "state_transition_required",
                        f"row固有field不足を説明するUNKNOWNがありません: {stable_id}",
                    )
                if spec.section in {
                    "UI操作一覧",
                    "User Story一覧",
                    "Use Case一覧",
                    "Behavior一覧",
                    "Acceptance Criteria一覧",
                }:
                    scope_id = scope_for(spec, row)
                    for unknown_id in unknown_refs:
                        require_root_blocker(unknown_id, scope_id, stable_id)
            authority_refs = (
                _refs(row, "関連仕様項目ID") if "関連仕様項目ID" in row else []
            )
            for authority_ref in authority_refs:
                item = analysis.get(authority_ref)
                if (
                    item is None
                    or item["現在有効か"] != "Yes"
                    or item["分類"]
                    not in {"SPEC", "DECISION", "承認済みASM", "INFERENCE"}
                ):
                    fail(
                        "reference_not_found",
                        f"tracking rowの仕様参照はcurrent itemである必要があります: {stable_id}/{authority_ref}",
                    )
    # UNKNOWN blocker rows must point to current scoped UNKNOWNs and preserve
    # the declared related-scope subset contract.
    scope_ids = set(_scope_by_id(model))
    for row in _unknown_rows(model):
        related = _refs(row, "関連Scope ID")
        blocking = _refs(row, "Blocking Scope ID")
        if not set(blocking) <= set(related) or not set(related) <= scope_ids:
            fail(
                "reference_not_found",
                f"UNKNOWN scope refsが不正です: {row['UNKNOWN ID']}",
            )
        files = (
            row["関連File"].replace("<br>", "\n").split("\n") if row["関連File"] else []
        )
        if len(files) != len(set(files)):
            fail(
                "duplicate_id", f"UNKNOWN関連Fileが重複しています: {row['UNKNOWN ID']}"
            )
        for path in files:
            if path not in set(CORE_FILES) | set(CONDITIONAL_FILES) | set(
                _extension_paths(model.tables)
            ):
                fail(
                    "reference_not_found",
                    f"UNKNOWN関連Fileがcanonical package pathではありません: {path}",
                )
            if path not in CORE_FILES + CONDITIONAL_FILES and path not in set(
                model.files
            ):
                fail(
                    "reference_not_found",
                    f"UNKNOWN関連extension fileがありません: {path}",
                )
    # Required fixed enums and current Authority constraints.
    for row in _rows(
        model, "05_notifications_and_external_interactions.md", "通知・外部連携一覧"
    ):
        if row["種別"] not in {"通知", "メール", "外部連携", "外部遷移イベント"}:
            fail(
                "package_schema_mismatch",
                f"NOTIFY / INTERACT種別が不正です: {row['種別']}",
            )
        expected_prefix = "NOTIFY" if row["種別"] in {"通知", "メール"} else "INTERACT"
        if _id_prefix(row["連携ID"]) != expected_prefix:
            fail(
                "package_schema_mismatch",
                f"種別と連携ID prefixが不一致です: {row['連携ID']}",
            )
    for row in _rows(model, "09_authority_and_traceability.md", "現在有効な仕様根拠"):
        if row["種別"] not in {"SPEC", "DECISION", "承認済みASM"}:
            fail(
                "package_schema_mismatch",
                f"Current Effective Authorityの種別が不正です: {row['仕様根拠ID']}",
            )
        item = analysis.get(row["仕様根拠ID"])
        if (
            item is None
            or item["分類"] not in {"SPEC", "DECISION", "承認済みASM"}
            or item["現在有効か"] != "Yes"
        ):
            fail(
                "reference_not_found",
                f"Current Effective Authorityの分析項目がcurrentではありません: {row['仕様根拠ID']}",
            )
        source_refs = _refs(row, "情報源 / 正本一覧")
        if not source_refs or any(_id_prefix(value) != "SRC" for value in source_refs):
            fail(
                "state_transition_required",
                f"Authorityにはcurrent source refが必要です: {row['仕様根拠ID']}",
            )
        if row["関係"] not in {"独立", "補足", "上書き", "置換", "未定義部分の補完"}:
            fail(
                "package_schema_mismatch",
                f"Authority relation enumが不正です: {row['仕様根拠ID']}",
            )


def _required_fields(spec: TableSpec, row: dict[str, str]) -> tuple[str, ...]:
    by_section = {
        "UI操作一覧": (
            "Scope ID",
            "Actor / Role",
            "対象構造ID",
            "操作",
            "関連仕様項目ID",
            "対応UC ID",
        ),
        "User Story一覧": ("Scope ID", "Actor / Role", "Goal", "関連仕様項目ID"),
        "Use Case一覧": (
            "関連US ID",
            "Use Case",
            "Trigger",
            "Success Postcondition",
            "関連仕様項目ID",
        ),
        "Behavior一覧": (
            "UC ID",
            "結果分類",
            "振る舞い",
            "Postcondition / Result",
            "関連仕様項目ID",
        ),
        "Acceptance Criteria一覧": (
            "Behavior ID",
            "Acceptance Criteria",
            "関連仕様項目ID",
        ),
        "ビジネスルール一覧": (
            "関連Scope ID",
            "ルール名",
            "ルール詳細",
            "適用条件",
            "関連仕様項目ID",
        ),
        "項目・バリデーション一覧": (
            "関連Scope ID",
            "ラベル / 名称",
            "要素タイプ",
            "入力 / 表示仕様",
            "制約 / バリデーション",
            "関連仕様項目ID",
        ),
        "処理フロー一覧": (
            "関連Scope ID",
            "処理名",
            "トリガー / 操作",
            "手順 / 状態遷移",
            "結果",
            "関連仕様項目ID",
        ),
        "通知・外部連携一覧": (
            "関連Scope ID",
            "種別",
            "名称",
            "発火条件",
            "宛先 / 遷移先",
            "内容 / 挙動",
            "関連仕様項目ID",
        ),
        "Repository実装状況": (
            "Repository",
            "関連Scope ID",
            "対象",
            "観測事実",
            "関連仕様項目ID",
            "判定",
        ),
    }
    required = list(by_section.get(spec.section, ()))
    if spec.section == "Behavior一覧" and row.get("状態") == "blocked":
        required = [field for field in required if field not in {"関連操作ID"}]
    return tuple(required)


def _blocked_minimum_fields(spec: TableSpec) -> tuple[str, ...]:
    return {
        "UI操作一覧": ("Scope ID", "操作"),
        "User Story一覧": ("Scope ID",),
        "Use Case一覧": ("関連US ID", "Use Case"),
        "Behavior一覧": ("UC ID", "結果分類", "振る舞い"),
        "Acceptance Criteria一覧": ("Behavior ID",),
        "ビジネスルール一覧": ("関連Scope ID", "ルール名"),
        "項目・バリデーション一覧": ("関連Scope ID", "ラベル / 名称"),
        "処理フロー一覧": ("関連Scope ID", "処理名"),
        "通知・外部連携一覧": ("関連Scope ID", "種別", "名称"),
    }.get(spec.section, ())


def _validate_hierarchies(model: PackageModel) -> None:
    scopes = _scope_by_id(model)
    uiops = {
        row["操作ID"]: row
        for row in _rows(model, "02_behavior_and_business_rules.md", "UI操作一覧")
    }
    stories = {
        row["US ID"]: row
        for row in _rows(model, "02_behavior_and_business_rules.md", "User Story一覧")
    }
    cases = {
        row["UC ID"]: row
        for row in _rows(model, "02_behavior_and_business_rules.md", "Use Case一覧")
    }
    behaviors = {
        row["Behavior ID"]: row
        for row in _rows(model, "02_behavior_and_business_rules.md", "Behavior一覧")
    }
    acs = {
        row["AC ID"]: row
        for row in _rows(
            model, "02_behavior_and_business_rules.md", "Acceptance Criteria一覧"
        )
    }
    for row in uiops.values():
        scope_refs = _refs(row, "Scope ID")
        scope = scopes.get(scope_refs[0]) if len(scope_refs) == 1 else None
        if scope is None or scope["Behavior Decomposition"] != "required":
            fail(
                "reference_not_found",
                f"UIOPがrequired scopeに属していません: {row['操作ID']}",
            )
        for uc_id in _refs(row, "対応UC ID"):
            uc = cases[uc_id]
            uc_scope_ids = {
                stories[us_id]["Scope ID"] for us_id in _refs(uc, "関連US ID")
            }
            if uc_scope_ids != {scope_refs[0]}:
                fail(
                    "reference_not_found",
                    f"UIOPとUCのScopeが一致しません: {row['操作ID']}/{uc_id}",
                )
    for row in stories.values():
        scope = scopes.get(row["Scope ID"])
        if scope is None or scope["Behavior Decomposition"] != "required":
            fail(
                "reference_not_found",
                f"USがrequired scopeに属していません: {row['US ID']}",
            )
        child_cases = [
            uc for uc in cases.values() if row["US ID"] in _refs(uc, "関連US ID")
        ]
        if row["状態"] == "current" and not child_cases:
            fail(
                "state_transition_required",
                f"current USにUCがありません: {row['US ID']}",
            )
    for row in cases.values():
        parent_us = [stories[us_id] for us_id in _refs(row, "関連US ID")]
        parent_scopes = {parent["Scope ID"] for parent in parent_us}
        if not parent_us or len(parent_scopes) != 1:
            fail(
                "reference_not_found",
                f"UCは同一ScopeのUSを1件以上参照する必要があります: {row['UC ID']}",
            )
        if row["状態"] == "current" and any(
            us["状態"] != "current" for us in parent_us
        ):
            fail(
                "package_schema_mismatch",
                f"current UCの親USがblockedです: {row['UC ID']}",
            )
    complete = _rows(
        model, "02_behavior_and_business_rules.md", "Use Case振る舞い完全性"
    )
    completeness: dict[tuple[str, str], dict[str, str]] = {}
    categories = {"正常", "準正常", "例外"}
    for row in complete:
        key = (row["UC ID"], row["結果分類"])
        if (
            key in completeness
            or row["結果分類"] not in categories
            or row["UC ID"] not in cases
        ):
            fail("duplicate_id", f"Use Case振る舞い完全性rowが不正です: {key}")
        completeness[key] = row
        if row["判定"] not in {"定義あり", "なし", "未定義"}:
            fail(
                "package_schema_mismatch",
                f"Use Case振る舞い完全性の判定が不正です: {key}",
            )
        if row["判定"] == "未定義" and not _refs(row, "関連UNKNOWN ID"):
            fail("state_transition_required", f"未定義分類にUNKNOWNがありません: {key}")
        if row["判定"] == "定義あり" and not _refs(row, "関連Behavior ID"):
            fail(
                "state_transition_required",
                f"定義あり分類にBehaviorがありません: {key}",
            )
        if row["判定"] == "定義あり" and _refs(row, "関連UNKNOWN ID"):
            fail(
                "package_schema_mismatch",
                f"定義あり分類の関連UNKNOWN IDは空である必要があります: {key}",
            )
        if row["判定"] == "なし" and (
            _refs(row, "関連Behavior ID")
            or _refs(row, "関連UNKNOWN ID")
            or not row["理由 / 根拠"].strip()
        ):
            fail(
                "state_transition_required",
                f"なし判定はBehavior / UNKNOWNなしと理由を要求します: {key}",
            )
        if row["判定"] in {"なし", "未定義"} and not _refs(row, "関連仕様項目ID"):
            fail(
                "state_transition_required",
                f"なし / 未定義の完全性判断に仕様根拠が必要です: {key}",
            )
        if row["判定"] in {"なし", "未定義"}:
            authority_refs = _refs(row, "関連仕様項目ID")
            for authority_ref in authority_refs:
                item = next(
                    (
                        item
                        for item in _current_item_rows(model)
                        if item["項目ID"] == authority_ref
                    ),
                    None,
                )
                if (
                    item is None
                    or item["分類"] not in {"SPEC", "DECISION", "承認済みASM"}
                    or item["現在有効か"] != "Yes"
                ):
                    fail(
                        "reference_not_found",
                        f"完全性判断はcurrent Authorityを参照する必要があります: {key}/{authority_ref}",
                    )
        for behavior_id in _refs(row, "関連Behavior ID"):
            behavior = behaviors[behavior_id]
            if (
                behavior["UC ID"] != row["UC ID"]
                or behavior["結果分類"] != row["結果分類"]
            ):
                fail(
                    "reference_not_found",
                    f"Behaviorと完全性rowが一致しません: {behavior_id}",
                )
            if row["判定"] == "定義あり" and behavior["状態"] != "current":
                fail(
                    "package_schema_mismatch",
                    f"定義あり分類はcurrent Behaviorだけを参照できます: {behavior_id}",
                )
        if row["判定"] == "未定義":
            uc = cases[row["UC ID"]]
            parent_us = [stories[value] for value in _refs(uc, "関連US ID")]
            scope_id = parent_us[0]["Scope ID"] if parent_us else None
            for unknown_id in _refs(row, "関連UNKNOWN ID"):
                unknown = next(
                    item
                    for item in _unknown_rows(model)
                    if item["UNKNOWN ID"] == unknown_id
                )
                related_files = (
                    unknown["関連File"].replace("<br>", "\n").split("\n")
                    if unknown["関連File"]
                    else []
                )
                if (
                    scope_id is None
                    or scope_id not in _refs(unknown, "Blocking Scope ID")
                    or "02_behavior_and_business_rules.md" not in related_files
                ):
                    fail(
                        "state_transition_required",
                        f"未定義BehaviorのUNKNOWN blockerがscope / fileへ閉じていません: {key}/{unknown_id}",
                    )
    for uc_id, uc in cases.items():
        keys = {(uc_id, category) for category in categories}
        if uc["状態"] == "current" and not keys <= set(completeness):
            fail(
                "package_schema_mismatch",
                f"current UCに3種類の完全性rowが必要です: {uc_id}",
            )
        if uc["状態"] == "blocked" and keys & set(completeness):
            fail(
                "package_schema_mismatch",
                f"blocked UCに振る舞い完全性rowを生成できません: {uc_id}",
            )
    for row in behaviors.values():
        uc = cases[row["UC ID"]]
        if row["状態"] == "current" and uc["状態"] != "current":
            fail(
                "package_schema_mismatch",
                f"current Behaviorの親UCがblockedです: {row['Behavior ID']}",
            )
        if row["結果分類"] not in categories:
            fail(
                "package_schema_mismatch",
                f"Behaviorの結果分類が不正です: {row['Behavior ID']}",
            )
        operation_refs = _refs(row, "関連操作ID")
        if row["状態"] == "current" and not operation_refs:
            fail(
                "state_transition_required",
                f"current Behaviorに関連UIOPがありません: {row['Behavior ID']}",
            )
        scope_ids = {stories[us_id]["Scope ID"] for us_id in _refs(uc, "関連US ID")}
        for operation_id in operation_refs:
            op = uiops[operation_id]
            operation_scopes = _refs(op, "Scope ID")
            if (
                uc["UC ID"] not in _refs(op, "対応UC ID")
                or len(operation_scopes) != 1
                or operation_scopes[0] not in scope_ids
            ):
                fail(
                    "reference_not_found",
                    f"BehaviorのUIOP mapping / scopeが不正です: {row['Behavior ID']}/{operation_id}",
                )
            if row["状態"] == "current" and op["状態"] != "mapped":
                fail(
                    "package_schema_mismatch",
                    f"current Behaviorがblocked UIOPを参照しています: {row['Behavior ID']}",
                )
        child_acs = [
            ac for ac in acs.values() if ac["Behavior ID"] == row["Behavior ID"]
        ]
        if row["状態"] == "current" and not child_acs:
            fail(
                "state_transition_required",
                f"current Behaviorにcurrent/blocked ACまたはAC blockerがありません: {row['Behavior ID']}",
            )
        if row["状態"] == "blocked" and any(
            ac["状態"] == "current" for ac in child_acs
        ):
            fail(
                "package_schema_mismatch",
                f"blocked Behaviorにcurrent ACを接続できません: {row['Behavior ID']}",
            )
    for row in acs.values():
        behavior = behaviors[row["Behavior ID"]]
        if row["状態"] == "current" and behavior["状態"] != "current":
            fail(
                "package_schema_mismatch",
                f"current ACの親Behaviorがblockedです: {row['AC ID']}",
            )
        if row["状態"] == "current":
            authorities = [
                value
                for value in _refs(row, "関連仕様項目ID")
                if value in model.current_authorities
            ]
            if not authorities:
                fail(
                    "state_transition_required",
                    f"current ACにcurrent Authorityがありません: {row['AC ID']}",
                )
    for uc_id, uc in cases.items():
        if uc["状態"] == "blocked":
            continue
        rows = [completeness[(uc_id, category)] for category in categories]
        defined = any(row["判定"] == "定義あり" for row in rows)
        unresolved = any(row["判定"] == "未定義" for row in rows)
        has_behaviors = any(row["UC ID"] == uc_id for row in behaviors.values())
        if (
            uc["状態"] == "current"
            and not (defined and has_behaviors)
            and not unresolved
        ):
            fail(
                "state_transition_required",
                f"current UCにBehavior closureがありません: {uc_id}",
            )


def _scope_progress(model: PackageModel, *, check_closure: bool) -> dict[str, Any]:
    scopes = _scope_by_id(model)
    scope_ids = sorted(scopes, key=_id_sort)
    unknown_by_id = {row["UNKNOWN ID"]: row for row in _unknown_rows(model)}
    applicability = _rows(
        model, "00_scope_and_context.md", "条件付き必須file applicability"
    )
    app_by_key = {(row["ファイル"], row["Scope ID"]): row for row in applicability}
    rows_by_scope: dict[str, list[tuple[TableSpec, dict[str, str]]]] = {
        scope_id: [] for scope_id in scope_ids
    }
    for spec in TABLES:
        if not spec.status_column:
            continue
        for row in _rows(model, spec.file, spec.section):
            scope_refs = (
                _refs(row, "Scope ID")
                if "Scope ID" in row
                else _refs(row, "関連Scope ID")
                if "関連Scope ID" in row
                else []
            )
            if spec.section == "Use Case一覧":
                us_by_id = {
                    item["US ID"]: item
                    for item in _rows(
                        model, "02_behavior_and_business_rules.md", "User Story一覧"
                    )
                }
                scope_refs = sorted(
                    {
                        us_by_id[value]["Scope ID"]
                        for value in _refs(row, "関連US ID")
                        if value in us_by_id
                    },
                    key=_id_sort,
                )
            elif spec.section in {"Behavior一覧", "Acceptance Criteria一覧"}:
                uc_id = row.get("UC ID")
                if not uc_id and row.get("Behavior ID"):
                    parent_behavior = next(
                        (
                            item
                            for item in _rows(
                                model,
                                "02_behavior_and_business_rules.md",
                                "Behavior一覧",
                            )
                            if item["Behavior ID"] == row["Behavior ID"]
                        ),
                        None,
                    )
                    uc_id = parent_behavior["UC ID"] if parent_behavior else None
                uc = next(
                    (
                        item
                        for item in _rows(
                            model, "02_behavior_and_business_rules.md", "Use Case一覧"
                        )
                        if item["UC ID"] == uc_id
                    ),
                    None,
                )
                us_by_id = {
                    item["US ID"]: item
                    for item in _rows(
                        model, "02_behavior_and_business_rules.md", "User Story一覧"
                    )
                }
                scope_refs = sorted(
                    {
                        us_by_id[value]["Scope ID"]
                        for value in (_refs(uc, "関連US ID") if uc else [])
                        if value in us_by_id
                    },
                    key=_id_sort,
                )
            elif spec.section == "UI操作一覧":
                scope_refs = [row["Scope ID"]]
            for scope_id in scope_refs:
                if scope_id in rows_by_scope:
                    rows_by_scope[scope_id].append((spec, row))
    completeness = _rows(
        model, "02_behavior_and_business_rules.md", "Use Case振る舞い完全性"
    )
    cases = {
        row["UC ID"]: row
        for row in _rows(model, "02_behavior_and_business_rules.md", "Use Case一覧")
    }
    stories = {
        row["US ID"]: row
        for row in _rows(model, "02_behavior_and_business_rules.md", "User Story一覧")
    }
    blocked_ids: set[str] = set()
    readiness: list[dict[str, Any]] = []
    for scope_id in scope_ids:
        scope = scopes[scope_id]
        blockers: set[str] = (
            set(_refs(scope, "関連UNKNOWN ID"))
            if scope["Behavior Decomposition"] == "blocked"
            else set()
        )
        blocked = scope["Behavior Decomposition"] == "blocked"
        for spec, row in rows_by_scope[scope_id]:
            if row.get(spec.status_column or "") == "blocked":
                blocked = True
                blockers.update(_refs(row, "関連UNKNOWN ID"))
        for (file, candidate_scope), row in app_by_key.items():
            if candidate_scope == scope_id and row["状態"] == "blocked":
                blocked = True
                blockers.update(_refs(row, "関連UNKNOWN ID"))
        for unknown in unknown_by_id.values():
            if scope_id in _refs(unknown, "Blocking Scope ID"):
                blocked = True
                blockers.add(unknown["UNKNOWN ID"])
        scope_uc_ids = {
            uc_id
            for uc_id, uc in cases.items()
            if any(
                stories[us_id]["Scope ID"] == scope_id
                for us_id in _refs(uc, "関連US ID")
            )
        }
        for row in completeness:
            if row["UC ID"] in scope_uc_ids and row["判定"] == "未定義":
                blocked = True
                blockers.update(_refs(row, "関連UNKNOWN ID"))
        # Blocked descendants inherit their ancestor cause at scope level.
        for spec, row in rows_by_scope[scope_id]:
            refs = _refs(row, "関連UNKNOWN ID")
            if row.get(spec.status_column or "") == "blocked":
                blockers.update(refs)
        if blocked and not blockers:
            fail(
                "state_transition_required",
                f"blocked Scopeにroot cause UNKNOWNがありません: {scope_id}",
            )
        if check_closure and scope["Behavior Decomposition"] == "required":
            op_rows = [
                row
                for row in _rows(
                    model, "02_behavior_and_business_rules.md", "UI操作一覧"
                )
                if row["Scope ID"] == scope_id
            ]
            unknown_closure = any(
                scope_id in _refs(row, "Blocking Scope ID")
                and "02_behavior_and_business_rules.md"
                in (row["関連File"].split("\n") if row["関連File"] else [])
                for row in unknown_by_id.values()
            )
            if not op_rows and not unknown_closure:
                fail(
                    "state_transition_required",
                    f"required scopeのUIOP identity closureがありません: {scope_id}",
                )
            # Each conditional domain with Trigger=あり needs at least one
            # current/blocked identity row or a matching file-level UNKNOWN.
            closure_targets = {
                "03_fields_and_validation.md": ("項目ID", "項目・バリデーション一覧"),
                "04_flows_and_data.md": ("フローID", "処理フロー一覧"),
                "05_notifications_and_external_interactions.md": (
                    "連携ID",
                    "通知・外部連携一覧",
                ),
                "08_repository_implementation_status.md": (
                    "実装確認ID",
                    "Repository実装状況",
                ),
            }
            for file, (id_col, section) in closure_targets.items():
                app = app_by_key[(file, scope_id)]
                if app["Trigger判定"] != "あり":
                    continue
                domain_rows = [
                    row
                    for row in _rows(model, file, section)
                    if scope_id
                    in (_refs(row, "関連Scope ID") if "関連Scope ID" in row else [])
                ]
                file_blocker = any(
                    scope_id in _refs(row, "Blocking Scope ID")
                    and file in (row["関連File"].split("\n") if row["関連File"] else [])
                    for row in unknown_by_id.values()
                )
                if not domain_rows and not file_blocker:
                    fail(
                        "state_transition_required",
                        f"required applicabilityにdomain row / blockerがありません: {file}/{scope_id}",
                    )
        status = "blocked" if blocked else "ready"
        if blocked:
            blocked_ids.add(scope_id)
        readiness.append(
            {
                "scope_id": scope_id,
                "status": status,
                "blocking_unknown_ids": sorted(blockers, key=_id_sort),
            }
        )
    ready_ids = [scope_id for scope_id in scope_ids if scope_id not in blocked_ids]
    completion = (
        "complete" if not blocked_ids else "partial" if ready_ids else "blocked"
    )
    return {
        "current_scope_ids": scope_ids,
        "ready_scope_ids": ready_ids,
        "blocked_scope_ids": sorted(blocked_ids, key=_id_sort),
        "scope_readiness": readiness,
        "completion_status": completion,
    }


def _row_refs_any(rows: list[dict[str, str]], columns: tuple[str, ...]) -> set[str]:
    result: set[str] = set()
    for row in rows:
        for column in columns:
            result.update(_refs(row, column))
    return result


def _authority_projection(
    model: PackageModel,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, dict[str, Any]]]:
    effective_rows = _rows(
        model, "09_authority_and_traceability.md", "現在有効な仕様根拠"
    )
    normalized: list[dict[str, Any]] = []
    for row in effective_rows:
        source_refs = _refs(row, "情報源 / 正本一覧")
        related_refs = _refs(row, "関連仕様根拠ID")
        relation = row["関係"].strip()
        authority_type = row["種別"].strip()
        active_content = row["現在有効な内容"].strip()
        scope = row["適用範囲"].strip()
        if not active_content or not scope:
            fail(
                "state_transition_required",
                f"Authority content / scopeが空です: {row['仕様根拠ID']}",
            )
        normalized.append(
            {
                "authority_id": row["仕様根拠ID"],
                "authority_type": authority_type,
                "active_content": {"text": active_content},
                "scope": scope,
                "source_refs": sorted(source_refs),
                "relations": [relation],
                "related_authority_refs": sorted(related_refs),
            }
        )
    normalized.sort(key=lambda row: row["authority_id"])
    try:
        from authority_entities import build as build_authority_entities

        built = build_authority_entities(normalized)
    except RuntimeErrorBase as exc:
        fail(exc.issue_type, exc.message)
    entities = built["entities"]
    by_ref = {entity["entity_ref"]: entity for entity in entities}
    return normalized, entities, by_ref


def _structured_ref_sets(rows: list[dict[str, str]]) -> tuple[set[str], set[str]]:
    structures: set[str] = set()
    domain: set[str] = set()
    for row in rows:
        for column in ("関連構造ID", "対象構造ID"):
            for ref in _refs(row, column) if row.get(column) else []:
                (structures if _id_prefix(ref) in UI_PREFIXES else domain).add(ref)
    return structures, domain


def _build_machine_entities(
    model: PackageModel, *, scope_ids: set[str] | None = None
) -> dict[str, Any]:
    normalized_authorities, authority_entities, authority_by_id = _authority_projection(
        model
    )
    if scope_ids is not None:
        # Select Authority source rows through the same explicit package graph
        # used for AC reachability. This projects the requested scopes from
        # source data instead of filtering a package-global Entity collection.
        relevant_authorities = _scope_authority_ids(model, scope_ids)
        normalized_authorities = [
            row
            for row in normalized_authorities
            if row["authority_id"] in relevant_authorities
        ]
        authority_entities = [
            row
            for row in authority_entities
            if row["entity_ref"] in relevant_authorities
        ]
        authority_by_id = {
            key: value
            for key, value in authority_by_id.items()
            if key in relevant_authorities
        }
    items = {row["項目ID"]: row for row in _current_item_rows(model)}
    scopes = {row["Scope ID"]: row for row in _scope_rows(model)}
    structures = {
        row["構造ID"]: row
        for row in _rows(model, "01_ui_structure_and_navigation.md", "UI構造一覧")
    }
    uiops = {
        row["操作ID"]: row
        for row in _rows(model, "02_behavior_and_business_rules.md", "UI操作一覧")
    }
    stories = {
        row["US ID"]: row
        for row in _rows(model, "02_behavior_and_business_rules.md", "User Story一覧")
    }
    cases = {
        row["UC ID"]: row
        for row in _rows(model, "02_behavior_and_business_rules.md", "Use Case一覧")
    }
    behaviors = {
        row["Behavior ID"]: row
        for row in _rows(model, "02_behavior_and_business_rules.md", "Behavior一覧")
    }
    acs = {
        row["AC ID"]: row
        for row in _rows(
            model, "02_behavior_and_business_rules.md", "Acceptance Criteria一覧"
        )
    }
    domains: dict[str, tuple[str, dict[str, str]]] = {}
    for spec in TABLES:
        if spec.id_column and (
            spec.prefix in DOMAIN_PREFIXES
            or spec.file == "05_notifications_and_external_interactions.md"
        ):
            for row in _rows(model, spec.file, spec.section):
                domains[row[spec.id_column]] = (spec.section, row)

    def source_authorities(rows: list[dict[str, str]]) -> set[str]:
        refs = _row_refs_any(rows, ("関連仕様項目ID",))
        return {ref for ref in refs if ref in authority_by_id}

    def add_structure_ancestors(seed: set[str]) -> set[str]:
        found: set[str] = set()
        visiting: set[str] = set()

        def visit(ref: str) -> None:
            if ref in visiting:
                fail("package_schema_mismatch", f"UI structure parent cycleです: {ref}")
            if ref in found:
                return
            row = structures.get(ref)
            if row is None:
                fail("reference_not_found", f"UI structureがありません: {ref}")
            visiting.add(ref)
            found.add(ref)
            parent = row["親構造ID"]
            if parent:
                visit(parent)
            visiting.remove(ref)

        for ref in sorted(seed):
            visit(ref)
        return found

    def build_ac(
        ac_id: str, *, included_scope_ids: set[str] | None = None
    ) -> tuple[dict[str, Any], dict[str, Any]] | None:
        ac = acs[ac_id]
        if ac["状態"] != "current":
            return None
        behavior = behaviors[ac["Behavior ID"]]
        uc = cases[behavior["UC ID"]]
        us_rows = [stories[us_id] for us_id in _refs(uc, "関連US ID")]
        scope_ids = {us["Scope ID"] for us in us_rows}
        if len(scope_ids) != 1 or not us_rows:
            fail(
                "reference_not_found",
                f"AC parent chainが同一Scopeに閉じていません: {ac_id}",
            )
        scope_id = next(iter(scope_ids))
        if included_scope_ids is not None and scope_id not in included_scope_ids:
            return None
        if any(row["状態"] != "current" for row in (behavior, uc, *us_rows)):
            fail(
                "state_transition_required",
                f"current AC chainにblocked parentがあります: {ac_id}",
            )
        chain_rows = [ac, behavior, uc, *us_rows]
        operation_rows = []
        for operation_id in _refs(behavior, "関連操作ID"):
            operation = uiops[operation_id]
            if uc["UC ID"] not in _refs(operation, "対応UC ID"):
                fail(
                    "reference_not_found",
                    f"Behaviorに明示mappingがないUIOP参照です: {ac_id}/{operation_id}",
                )
            if operation["状態"] != "mapped":
                fail(
                    "state_transition_required",
                    f"current AC chainのlinked UIOPがmappedではありません: {ac_id}/{operation_id}",
                )
            if scope_id not in _refs(operation, "Scope ID"):
                fail(
                    "reference_not_found",
                    f"linked UIOPがAC Scopeと一致しません: {ac_id}/{operation_id}",
                )
            operation_rows.append(operation)
        scope = scopes[scope_id]
        base_rows = [*chain_rows, *operation_rows, scope]
        refs = source_authorities(base_rows)
        if not refs:
            fail(
                "state_transition_required",
                f"current AC chainにcurrent Authorityがありません: {ac_id}",
            )
        # Direct references to domain items are only those explicitly named by
        # the AC / Behavior / UC / US rows.  No domain-to-domain recursion.
        seed_structures, seed_domains = _structured_ref_sets(
            [*chain_rows, *operation_rows]
        )
        for operation in operation_rows:
            seed_structures.update(_refs(operation, "対象構造ID"))
        linked_domain_rows: list[dict[str, str]] = []
        for domain_id in sorted(seed_domains, key=_id_sort):
            domain_entry = domains.get(domain_id)
            if domain_entry is None:
                fail(
                    "reference_not_found",
                    f"linked domain itemがありません: {domain_id}",
                )
            linked_domain_rows.append(domain_entry[1])
            domain_row = domain_entry[1]
            refs.update(
                value
                for value in _refs(domain_row, "関連仕様項目ID")
                if value in authority_by_id
            )
            domain_structures, _ = _structured_ref_sets([domain_row])
            seed_structures.update(domain_structures)
        if not refs:
            fail(
                "state_transition_required",
                f"AC Entityにcurrent Authorityがありません: {ac_id}",
            )
        linked_structure_ids = add_structure_ancestors(seed_structures)
        linked_structure_rows = [
            structures[ref] for ref in sorted(linked_structure_ids, key=_id_sort)
        ]
        refs.update(source_authorities(linked_structure_rows))
        for row in linked_domain_rows:
            refs.update(
                value
                for value in _refs(row, "関連仕様項目ID")
                if value in authority_by_id
            )
        refs = set(sorted(refs))
        if not refs:
            fail(
                "state_transition_required",
                f"AC Entityにcurrent Authorityがありません: {ac_id}",
            )

        linked_ui_operations = []
        for operation in sorted(
            operation_rows, key=lambda item: _id_sort(item["操作ID"])
        ):
            operation_authorities = sorted(
                value
                for value in _refs(operation, "関連仕様項目ID")
                if value in authority_by_id
            )
            linked_ui_operations.append(
                {
                    "uiop_id": operation["操作ID"],
                    "actor_role": operation["Actor / Role"],
                    "target_structure_id": operation["対象構造ID"],
                    "operation": operation["操作"],
                    "authority_refs": operation_authorities,
                }
            )
        linked_structures = []
        for structure in linked_structure_rows:
            linked_structures.append(
                {
                    "structure_id": structure["構造ID"],
                    "type": structure["種別"],
                    "name": structure["名称"],
                    "state_axis": structure["状態軸"],
                    "path_identifier": structure["Path / 識別子"],
                    "parent_structure_id": structure["親構造ID"] or None,
                    "authority_refs": sorted(
                        value
                        for value in _refs(structure, "関連仕様項目ID")
                        if value in authority_by_id
                    ),
                }
            )
        linked_domain_items = []
        domain_fields = {
            "ビジネスルール一覧": ("ルール名", "ルール詳細", "適用条件", "備考"),
            "項目・バリデーション一覧": (
                "ラベル / 名称",
                "要素タイプ",
                "入力 / 表示仕様",
                "制約 / バリデーション",
                "備考",
            ),
            "処理フロー一覧": (
                "処理名",
                "トリガー / 操作",
                "手順 / 状態遷移",
                "結果",
                "備考",
            ),
            "通知・外部連携一覧": (
                "種別",
                "名称",
                "発火条件",
                "宛先 / 遷移先",
                "内容 / 挙動",
                "備考",
            ),
        }
        for domain_id in sorted(seed_domains, key=_id_sort):
            section, row = domains[domain_id]
            refs_for_domain = sorted(
                value
                for value in _refs(row, "関連仕様項目ID")
                if value in authority_by_id
            )
            structure_refs = sorted(
                set(_refs(row, "対象構造ID") + _refs(row, "関連構造ID")), key=_id_sort
            )
            linked_domain_items.append(
                {
                    "item_id": domain_id,
                    "item_type": _id_prefix(domain_id),
                    "scope_refs": sorted(
                        set(
                            _refs(row, "関連Scope ID") if "関連Scope ID" in row else []
                        ),
                        key=_id_sort,
                    ),
                    "semantic_content": {
                        field: row.get(field, "") for field in domain_fields[section]
                    },
                    "authority_refs": refs_for_domain,
                    "structure_refs": structure_refs,
                }
            )
        linked_inferences = []
        inference_refs = set()
        for row in (
            chain_rows
            + operation_rows
            + [scope]
            + linked_structure_rows
            + linked_domain_rows
        ):
            inference_refs.update(
                ref
                for ref in _refs(row, "関連仕様項目ID")
                if ref in items
                and items[ref]["分類"] == "INFERENCE"
                and items[ref]["現在有効か"] == "Yes"
            )
        for inf_id in sorted(inference_refs, key=_id_sort):
            linked_inferences.append(
                {"inf_id": inf_id, "content": items[inf_id]["内容"]}
            )
        content = {
            "ac_id": ac_id,
            "acceptance_criteria": ac["Acceptance Criteria"],
            "linked_ui_operations": linked_ui_operations,
            "behavior_id": behavior["Behavior ID"],
            "behavior_result_classification": behavior["結果分類"],
            "behavior_text": behavior["振る舞い"],
            "behavior_postcondition": behavior["Postcondition / Result"],
            "uc_id": uc["UC ID"],
            "use_case": uc["Use Case"],
            "trigger": uc["Trigger"],
            "preconditions": uc["Preconditions"],
            "success_postcondition": uc["Success Postcondition"],
            "user_stories": [
                {
                    "us_id": us["US ID"],
                    "actor_role": us["Actor / Role"],
                    "goal": us["Goal"],
                }
                for us in sorted(us_rows, key=lambda row: _id_sort(row["US ID"]))
            ],
            "scope": {
                "scope_id": scope_id,
                "target": scope["対象機能 / 領域"].strip(),
                "authority_refs": sorted(
                    value
                    for value in _refs(scope, "関連仕様項目ID")
                    if value in authority_by_id
                ),
            },
            "linked_structures": linked_structures,
            "linked_domain_items": linked_domain_items,
            "linked_inferences": linked_inferences,
            "authority_refs": sorted(refs),
        }
        dependencies = [
            {
                "skill": "spec-analysis",
                "entity_type": "authority",
                "entity_ref": ref,
                "content_fingerprint": authority_by_id[ref]["content_fingerprint"],
            }
            for ref in sorted(refs)
        ]
        entity = make_machine_entity(
            "spec-analysis",
            "acceptance_criterion",
            ac_id,
            content,
            upstream_entity_dependencies=dependencies,
        )
        return entity, {"ac_id": ac_id, "authority_refs": sorted(refs)}

    all_ac_pairs = [
        pair
        for ac_id in sorted(acs, key=_id_sort)
        if (pair := build_ac(ac_id, included_scope_ids=scope_ids)) is not None
    ]
    acceptance_entities = [pair[0] for pair in all_ac_pairs]
    acceptance_rows = [pair[1] for pair in all_ac_pairs]
    current_entities = sorted(
        [*authority_entities, *acceptance_entities],
        key=lambda row: (row["skill"], row["entity_type"], row["entity_ref"]),
    )
    expected = [
        {
            "skill": row["skill"],
            "entity_type": row["entity_type"],
            "entity_ref": row["entity_ref"],
        }
        for row in current_entities
    ]
    return {
        "normalized_authorities": normalized_authorities,
        "normalized_skill_input": {
            "authorities": [
                {"authority_id": row["authority_id"]} for row in normalized_authorities
            ],
            "acceptance_criteria": acceptance_rows,
        },
        "acceptance_criterion_entities": acceptance_entities,
        "machine_entities": current_entities,
        "expected_entity_identities": expected,
        "machine_entities_markdown": render_machine_entities(
            "spec-analysis", current_entities
        ),
    }


def build_machine_evidence(
    model: PackageModel, scope_ids: list[str] | None
) -> dict[str, Any]:
    progress = _scope_progress(model, check_closure=True)
    if scope_ids is not None:
        if (
            not isinstance(scope_ids, list)
            or not scope_ids
            or any(not isinstance(value, str) for value in scope_ids)
        ):
            fail("invalid_input", "scope_idsはnullまたはnon-empty string arrayです")
        if len(scope_ids) != len(set(scope_ids)):
            fail("duplicate_id", "scope_idsが重複しています")
        if any(value not in progress["ready_scope_ids"] for value in scope_ids):
            fail(
                "reference_not_found",
                "scope_idsにはcurrent ready Scopeだけ指定できます",
            )
        selected = sorted(scope_ids, key=_id_sort)
        selected_set = set(selected)
        projection = _build_machine_entities(model, scope_ids=selected_set)
        by_scope = _scope_by_id(model)
        scope_index = []
        for scope_id in selected:
            scope = by_scope[scope_id]
            scope_index.append(
                {
                    "scope_id": scope_id,
                    "target": scope["対象機能 / 領域"],
                    "ui_operation": scope["UI操作判定"],
                    "authority_refs": sorted(
                        _scope_authority_ids(model, {scope_id}), key=_id_sort
                    ),
                }
            )
        batch = {
            "scope_ids": selected,
            "scope_index": scope_index,
            "normalized_skill_input": projection["normalized_skill_input"],
            "machine_entities": projection["machine_entities"],
            "expected_entity_identities": projection["expected_entity_identities"],
        }
        if len(canonical_json_bytes(batch)) > MAX_IO_BYTES:
            fail("limit_exceeded", "ready-scope batch handoffが16 MiBを超えています")
        return {"batch_handoff": batch}
    projection = _build_machine_entities(model)
    return {
        **projection,
        "current_scope_ids": progress["current_scope_ids"],
        "ready_scope_ids": progress["ready_scope_ids"],
        "blocked_scope_ids": progress["blocked_scope_ids"],
    }


def _scope_authority_ids(model: PackageModel, scope_ids: set[str]) -> set[str]:
    refs: set[str] = set()
    scopes = _scope_by_id(model)
    all_items = {row["項目ID"]: row for row in _current_item_rows(model)}
    structures = {
        row["構造ID"]: row
        for row in _rows(model, "01_ui_structure_and_navigation.md", "UI構造一覧")
    }
    uiops = _rows(model, "02_behavior_and_business_rules.md", "UI操作一覧")
    stories = _rows(model, "02_behavior_and_business_rules.md", "User Story一覧")
    cases = _rows(model, "02_behavior_and_business_rules.md", "Use Case一覧")
    behaviors = _rows(model, "02_behavior_and_business_rules.md", "Behavior一覧")
    acs = _rows(model, "02_behavior_and_business_rules.md", "Acceptance Criteria一覧")
    domain_rows: dict[str, dict[str, str]] = {}
    for spec in TABLES:
        if spec.id_column and (
            spec.prefix in DOMAIN_PREFIXES
            or spec.file == "05_notifications_and_external_interactions.md"
        ):
            for row in _rows(model, spec.file, spec.section):
                domain_rows[row[spec.id_column]] = row
    extensions = _rows(model, "00_scope_and_context.md", "案件固有extension file一覧")

    for scope_id in scope_ids:
        scope = scopes[scope_id]
        scope_refs: set[str] = set()
        selected_stories = [
            row
            for row in stories
            if row["Scope ID"] == scope_id and row["状態"] == "current"
        ]
        story_ids = {row["US ID"] for row in selected_stories}
        selected_cases = [
            row
            for row in cases
            if set(_refs(row, "関連US ID")) & story_ids and row["状態"] == "current"
        ]
        case_ids = {row["UC ID"] for row in selected_cases}
        selected_behaviors = [
            row
            for row in behaviors
            if row["UC ID"] in case_ids and row["状態"] == "current"
        ]
        behavior_ids = {row["Behavior ID"] for row in selected_behaviors}
        selected_acs = [
            row
            for row in acs
            if row["Behavior ID"] in behavior_ids and row["状態"] == "current"
        ]
        selected_uiops = [
            row
            for row in uiops
            if row["状態"] == "mapped" and _refs(row, "Scope ID") == [scope_id]
        ]
        selected_domain = [
            row
            for row in domain_rows.values()
            if row["状態"] == "current" and scope_id in _refs(row, "関連Scope ID")
        ]
        selected_app = [
            row
            for row in _rows(
                model, "00_scope_and_context.md", "条件付き必須file applicability"
            )
            if row["Scope ID"] == scope_id
        ]
        selected_extensions = [
            row for row in extensions if scope_id in _refs(row, "関連Scope ID")
        ]
        seed_rows = [
            scope,
            *selected_app,
            *selected_uiops,
            *selected_stories,
            *selected_cases,
            *selected_behaviors,
            *selected_acs,
            *selected_domain,
            *selected_extensions,
        ]
        for row in seed_rows:
            scope_refs.update(
                value
                for value in _refs(row, "関連仕様項目ID")
                if value in model.current_authorities
            )
        structure_seeds: set[str] = set()
        domain_seeds: set[str] = set()
        for row in seed_rows:
            direct_structures, direct_domains = _structured_ref_sets([row])
            structure_seeds.update(direct_structures)
            domain_seeds.update(direct_domains)
        for operation in selected_uiops:
            structure_seeds.update(_refs(operation, "対象構造ID"))
        for domain_id in domain_seeds:
            row = domain_rows.get(domain_id)
            if row is None:
                fail(
                    "reference_not_found",
                    f"scope handoff linked domain itemがありません: {domain_id}",
                )
            scope_refs.update(
                value
                for value in _refs(row, "関連仕様項目ID")
                if value in model.current_authorities
            )
            direct_structures, _ = _structured_ref_sets([row])
            structure_seeds.update(direct_structures)
        visited: set[str] = set()
        pending = list(structure_seeds)
        while pending:
            structure_id = pending.pop()
            if structure_id in visited:
                continue
            row = structures.get(structure_id)
            if row is None:
                fail(
                    "reference_not_found",
                    f"scope handoff linked UI structureがありません: {structure_id}",
                )
            visited.add(structure_id)
            scope_refs.update(
                value
                for value in _refs(row, "関連仕様項目ID")
                if value in model.current_authorities
            )
            if row["親構造ID"]:
                pending.extend(_refs(row, "親構造ID"))
        # Current INF contributes to AC content, but never to Authority handoff.
        scope_refs = {
            value
            for value in scope_refs
            if value in all_items
            and all_items[value]["分類"] in {"SPEC", "DECISION", "承認済みASM"}
            and all_items[value]["現在有効か"] == "Yes"
        }
        refs.update(scope_refs)
    return refs


def _validate_machine_entities(model: PackageModel) -> None:
    try:
        expected = _build_machine_entities(model)["machine_entities_markdown"]
        blocks = extract_machine_blocks(
            model.files["09_authority_and_traceability.md"], "Machine Entities"
        )
    except PackageError:
        raise
    except RuntimeErrorBase as exc:
        fail(
            "package_schema_mismatch",
            f"Machine Entitiesを検証できません: {exc.message}",
        )
    if len(blocks) != 1 or blocks[0][0] != "spec-analysis":
        fail(
            "package_schema_mismatch",
            "Machine Entities: spec-analysis blockがexactly oneではありません",
        )
    if expected not in model.files["09_authority_and_traceability.md"]:
        fail(
            "package_schema_mismatch",
            "Machine Entities blockがbuild-machine-evidence再生成結果と一致しません",
        )


def _validate_snapshot(model: PackageModel, snapshot: Any) -> None:
    if not isinstance(snapshot, dict) or set(snapshot) != {
        "package_version",
        "payload_file_sha256",
        "manifest_sha256",
    }:
        fail("invalid_input", "previous_snapshot schemaが不正です")
    if snapshot["package_version"] != model.metadata["Package Version"]:
        fail("stale_snapshot", "package_versionがprevious_snapshotと一致しません")
    if not isinstance(snapshot["payload_file_sha256"], list):
        fail(
            "invalid_input",
            "previous_snapshot.payload_file_sha256はarrayである必要があります",
        )
    current_hashes = [
        {"path": rel, "sha256": _sha(model.raw_files[rel])}
        for rel in model.payload_paths
    ]
    supplied = snapshot["payload_file_sha256"]
    if supplied != current_hashes or snapshot["manifest_sha256"] != _sha(
        model.raw_files["MANIFEST.md"]
    ):
        fail(
            "stale_snapshot",
            "package payload / MANIFEST bytesがprevious_snapshotと一致しません",
        )


def _read_update_snapshot(model: PackageModel) -> dict[str, Any]:
    return {
        "package_version": model.metadata["Package Version"],
        "payload_file_sha256": [
            {"path": rel, "sha256": _sha(model.raw_files[rel])}
            for rel in model.payload_paths
        ],
        "manifest_sha256": _sha(model.raw_files["MANIFEST.md"]),
    }


def _reference_index(model: PackageModel) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    additional = {
        ("00_scope_and_context.md", "条件付き必須file applicability"): ("Scope ID",),
        ("02_behavior_and_business_rules.md", "Use Case振る舞い完全性"): ("UC ID",),
        ("07_current_unknowns.md", "Current UNKNOWN一覧"): ("UNKNOWN ID",),
        ("09_authority_and_traceability.md", "現在有効な仕様根拠"): ("仕様根拠ID",),
    }
    for spec in TABLES:
        for row_index, row in enumerate(_rows(model, spec.file, spec.section), start=1):
            columns = tuple(
                dict.fromkeys(
                    (*spec.refs, *additional.get((spec.file, spec.section), ()))
                )
            )
            for column in columns:
                if column not in row:
                    continue
                for target in _refs(row, column):
                    rows.append(
                        {
                            "target_id": target,
                            "file": spec.file,
                            "section": spec.section,
                            "row_index": row_index,
                            "column": column,
                        }
                    )
    return sorted(
        rows,
        key=lambda row: (
            row["target_id"],
            row["file"],
            row["section"],
            row["row_index"],
            row["column"],
        ),
    )


def _inspect_payload(model: PackageModel) -> dict[str, Any]:
    progress = _scope_progress(model, check_closure=True)
    canonical_ids = sorted(_tracked_ids(model.tables), key=_id_sort)
    analysis = _current_item_rows(model)
    current_unknowns = sorted(
        (
            row["項目ID"]
            for row in analysis
            if row["分類"] == "UNKNOWN" and row["現在有効か"] == "Yes"
        ),
        key=_id_sort,
    )
    resolved_unknowns = sorted(
        (
            row["項目ID"]
            for row in analysis
            if row["分類"] == "UNKNOWN" and row["現在有効か"] == "No"
        ),
        key=_id_sort,
    )
    structural = sorted((row["Scope ID"] for row in _scope_rows(model)), key=_id_sort)
    structural.extend(
        sorted(
            (
                row["構造ID"]
                for row in _rows(
                    model, "01_ui_structure_and_navigation.md", "UI構造一覧"
                )
            ),
            key=_id_sort,
        )
    )
    applicability = []
    for row in _rows(
        model, "00_scope_and_context.md", "条件付き必須file applicability"
    ):
        applicability.append(
            {
                "path": row["ファイル"],
                "scope_id": row["Scope ID"],
                "trigger": row["Trigger判定"],
                "status": row["状態"],
                "authority_refs": sorted(_refs(row, "関連仕様項目ID"), key=_id_sort),
                "unknown_refs": sorted(_refs(row, "関連UNKNOWN ID"), key=_id_sort),
            }
        )
    applicability.sort(
        key=lambda row: (
            CONDITIONAL_FILES.index(row["path"]),
            _id_sort(row["scope_id"]),
        )
    )
    extensions = _extension_paths(model.tables)
    return {
        "package_schema_version": SCHEMA_VERSION,
        "package_version": model.metadata["Package Version"],
        "previous_package_version": model.metadata["Previous Package Version"],
        "completion_status": progress["completion_status"],
        **{
            key: progress[key]
            for key in (
                "current_scope_ids",
                "ready_scope_ids",
                "blocked_scope_ids",
                "scope_readiness",
            )
        },
        "payload_files": [
            {
                "order": index,
                "path": path,
                "kind": "extension"
                if path in extensions
                else "conditional"
                if path in CONDITIONAL_FILES
                else "core",
            }
            for index, path in enumerate(model.payload_paths, start=1)
        ],
        "file_applicability": applicability,
        "domain_files": [
            {
                "order": int(path.split("_", 1)[0]),
                "path": path,
                "slug": path.split("_", 1)[1][:-3],
            }
            for path in extensions
        ],
        "canonical_item_ids": canonical_ids,
        "current_unknown_ids": current_unknowns,
        "resolved_unknown_ids": resolved_unknowns,
        "current_unknown_count": len(current_unknowns),
        "structural_ids": structural,
        "exact_reference_index": _reference_index(model),
        "update_snapshot": _read_update_snapshot(model),
        "unresolved_structural_issues": [],
    }


@contextlib.contextmanager
def _package_lock(root: Path) -> Iterator[None]:
    parent = root.parent
    if not parent.exists() or not parent.is_dir():
        fail("path_outside_package", "package_rootのparent directoryがありません")
    lock_path = parent / f".{root.name}.ui-target.lock"
    _check_no_symlink(lock_path)
    try:
        handle = lock_path.open("a+b")
    except OSError as exc:
        fail("write_lock_unavailable", f"package lock fileを開けません: {exc}")
    acquired = False
    try:
        _check_no_symlink(lock_path)
        try:
            if os.name == "nt":
                import msvcrt

                handle.seek(0, os.SEEK_END)
                if handle.tell() == 0:
                    handle.write(b"\0")
                    handle.flush()
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            elif os.name == "posix":
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            else:
                fail(
                    "write_lock_unavailable",
                    "process-scoped package lockを利用できません",
                )
            acquired = True
        except PackageError:
            raise
        except (BlockingIOError, OSError) as exc:
            if getattr(exc, "errno", None) in {11, 13, 36} or isinstance(
                exc, BlockingIOError
            ):
                fail("write_locked", "package lockを別processが保持しています")
            fail(
                "write_lock_unavailable",
                f"process-scoped package lockに失敗しました: {exc}",
            )
        yield
    finally:
        if acquired:
            try:
                if os.name == "nt":
                    import msvcrt

                    handle.seek(0)
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            except OSError:
                pass
        handle.close()


def _remove_owned(path: Path) -> None:
    _check_no_symlink(path)
    if not path.exists():
        return
    if path.is_dir():
        for child in path.iterdir():
            _check_no_symlink(child)
            if child.is_dir():
                _remove_owned(child)
            else:
                child.unlink()
        path.rmdir()
    else:
        path.unlink()


def _preflight_recovery(root: Path) -> PackageModel | None:
    parent = root.parent
    staging = parent / f".{root.name}.ui-target-staging"
    backup = parent / f".{root.name}.ui-target-backup"
    _check_no_symlink(staging)
    _check_no_symlink(backup)
    root_exists = root.exists()
    staging_exists = staging.exists()
    backup_exists = backup.exists()
    root_valid = False
    backup_valid = False
    root_model: PackageModel | None = None
    backup_model: PackageModel | None = None
    if root_exists:
        try:
            root_model = _read_package(root)
            root_valid = True
        except PackageError:
            root_valid = False
    if backup_exists:
        try:
            backup_model = _read_package(backup)
            backup_valid = True
        except PackageError:
            backup_valid = False
    if root_valid:
        if staging_exists:
            try:
                _remove_owned(staging)
            except PackageError as exc:
                fail(
                    "write_recovery_failed",
                    f"orphan stagingをcleanupできません: {exc.message}",
                )
        if backup_exists:
            try:
                _remove_owned(backup)
            except PackageError as exc:
                fail(
                    "write_recovery_failed",
                    f"orphan backupをcleanupできません: {exc.message}",
                )
        return root_model
    if not root_exists and backup_exists and backup_valid:
        try:
            backup.rename(root)
        except OSError as exc:
            fail(
                "write_recovery_failed", f"backupをpackage rootへ復旧できません: {exc}"
            )
        if staging_exists:
            try:
                _remove_owned(staging)
            except PackageError as exc:
                fail(
                    "write_recovery_failed",
                    f"stagingをcleanupできません: {exc.message}",
                )
        assert backup_model is not None
        backup_model.root = root
        return backup_model
    if not root_exists and not backup_exists and staging_exists:
        try:
            _remove_owned(staging)
        except PackageError as exc:
            fail(
                "write_recovery_failed",
                f"uncommitted stagingをcleanupできません: {exc.message}",
            )
        return None
    if root_exists and not root_valid and not staging_exists and not backup_exists:
        return None
    if not root_exists and not backup_exists and not staging_exists:
        return None
    fail(
        "write_recovery_failed", "package root / backup / stagingを一意に復旧できません"
    )


def _resolve_root(value: Any) -> Path:
    if not isinstance(value, str) or not value.strip():
        fail("invalid_input", "package_rootはnon-empty path stringである必要があります")
    try:
        root = Path(os.path.abspath(os.path.expanduser(value)))
    except OSError as exc:
        fail("path_outside_package", f"package_rootをresolveできません: {exc}")
    if root.name in {"", ".", ".."}:
        fail("path_outside_package", "package_root pathが不正です")
    _check_no_symlink(root)
    return root


CHANGELOG_HEADER = ("Stable ID", "Change")


def _latest_change_summary(changelog: str) -> str:
    matches = list(re.finditer(r"(?m)^## (v[0-9]{2,})\s*$", changelog))
    if not matches:
        return ""
    start = matches[0].end()
    next_heading = re.search(r"(?m)^## v[0-9]{2,}\s*$", changelog[start:])
    entry = (
        changelog[start : start + next_heading.start()]
        if next_heading
        else changelog[start:]
    )
    match = re.search(r"(?ms)^### 変更概要\n(.*?)(?=^### )", entry)
    if not match:
        return ""
    value = normalize_text(match.group(1))
    if value.startswith("\n\n"):
        value = value[2:]
    if value.endswith("\n\n"):
        value = value[:-2]
    return value


def _validate_changelog(changelog: str, current_version: str) -> None:
    headings = list(re.finditer(r"(?m)^## (v[0-9]{2,})\s*$", changelog))
    if not headings or headings[0].group(1) != current_version:
        fail(
            "package_schema_mismatch",
            "CHANGELOG最新versionとPackage Versionが一致しません",
        )
    seen_versions: set[str] = set()
    history_events: dict[str, list[tuple[str, str]]] = {}
    for index, match in enumerate(headings):
        version = match.group(1)
        if version in seen_versions:
            fail(
                "package_schema_mismatch",
                f"CHANGELOG versionが重複しています: {version}",
            )
        seen_versions.add(version)
        end = (
            headings[index + 1].start() if index + 1 < len(headings) else len(changelog)
        )
        entry = changelog[match.start() : end]
        for section in ("変更概要", "Stable ID changes", "影響file"):
            if len(re.findall(rf"(?m)^### {re.escape(section)}$", entry)) != 1:
                fail(
                    "package_schema_mismatch",
                    f"CHANGELOG sectionがexactly oneではありません: {version}/{section}",
                )
        changes = parse_table(entry, "Stable ID changes", CHANGELOG_HEADER)
        seen_ids: set[str] = set()
        for row in changes:
            stable_id = row["Stable ID"]
            change = row["Change"]
            if not _valid_id(stable_id) or change not in {
                "added",
                "changed",
                "resolved",
                "retired",
                "migrated",
            }:
                fail(
                    "package_schema_mismatch",
                    f"CHANGELOG stable ID eventが不正です: {stable_id}/{change}",
                )
            if stable_id in seen_ids:
                fail(
                    "duplicate_id",
                    f"同一versionのCHANGELOG eventが重複しています: {stable_id}",
                )
            seen_ids.add(stable_id)
            if change == "resolved" and not stable_id.startswith("UNK-"):
                fail(
                    "package_schema_mismatch", f"resolvedはUNKNOWN専用です: {stable_id}"
                )
            if change == "retired" and stable_id.startswith(("DEC-", "ASM-")):
                fail(
                    "package_schema_mismatch",
                    f"外部owner IDはretiredできません: {stable_id}",
                )
            history_events.setdefault(stable_id, []).append((version, change))
    for stable_id, events in history_events.items():
        if sum(1 for _, change in events if change in {"added", "migrated"}) > 1:
            fail(
                "package_schema_mismatch",
                f"CHANGELOG added / migratedが複数回あります: {stable_id}",
            )
        retired = False
        for _, change in reversed(events):
            if retired:
                fail(
                    "package_schema_mismatch",
                    f"retired後にstable ID eventがあります: {stable_id}",
                )
            retired = change == "retired"


def _validate_lifecycle_consistency(model: PackageModel) -> None:
    current_rows: dict[str, dict[str, str]] = {}
    for spec in TABLES:
        if not spec.id_column:
            continue
        for row in _rows(model, spec.file, spec.section):
            current_rows[row[spec.id_column]] = row
    events: dict[str, list[tuple[str, str]]] = {}
    changelog = model.files["CHANGELOG.md"]
    headings = list(re.finditer(r"(?m)^## (v[0-9]{2,})\s*$", changelog))
    for match in headings:
        end = next(
            (other.start() for other in headings if other.start() > match.start()),
            len(changelog),
        )
        entry = changelog[match.start() : end]
        for row in parse_table(entry, "Stable ID changes", CHANGELOG_HEADER):
            events.setdefault(row["Stable ID"], []).append(
                (match.group(1), row["Change"])
            )
    for stable_id, history in events.items():
        newest_change = history[0][1]
        current = current_rows.get(stable_id)
        if newest_change == "retired" and current is not None:
            fail(
                "package_schema_mismatch",
                f"retired IDがcurrent tracking modelに残っています: {stable_id}",
            )
        if newest_change != "retired" and current is None:
            fail(
                "package_schema_mismatch",
                f"non-terminal lifecycle eventのstable IDがcurrent modelにありません: {stable_id}",
            )
        if newest_change == "resolved":
            item = next(
                (
                    row
                    for row in _current_item_rows(model)
                    if row["項目ID"] == stable_id
                ),
                None,
            )
            if item is None or item["分類"] != "UNKNOWN" or item["現在有効か"] != "No":
                fail(
                    "package_schema_mismatch",
                    f"resolved eventとcurrent UNKNOWN stateが一致しません: {stable_id}",
                )
        if stable_id.startswith(("DEC-", "ASM-")) and newest_change == "retired":
            fail("package_schema_mismatch", f"DEC / ASMをretireできません: {stable_id}")


def _replace_section_body(text: str, heading: str, body: str) -> str:
    lines, start, end = _heading_span(text, heading)
    lines[start + 1 : end] = normalize_text(body).rstrip("\n").splitlines()
    return "\n".join(lines) + "\n"


def _replace_user_prose_body(text: str, heading: str, body: str) -> str:
    lines, start, end = _heading_span(text, heading)
    prefix = "\n".join(lines[: start + 1])
    suffix = "\n".join(lines[end:])
    return prefix + "\n\n" + normalize_text(body) + "\n\n" + suffix + "\n"


def _replace_machine_section(text: str, markdown: str) -> str:
    pattern = re.compile(
        r"(?ms)^### Machine Entities: spec-analysis\s*\n.*?(?=^### |\Z)"
    )
    matches = list(pattern.finditer(text))
    if len(matches) != 1:
        fail(
            "package_schema_mismatch",
            "Machine Entities sectionがexactly oneではありません",
        )
    return (
        text[: matches[0].start()]
        + markdown.rstrip("\n")
        + "\n"
        + text[matches[0].end() :]
    )


def _file_kind(path: str) -> str:
    if path in CONDITIONAL_FILES:
        return "conditional"
    if re.fullmatch(r"(?:1[0-9]|[2-9][0-9]+)_[a-z0-9]+(?:-[a-z0-9]+)*\.md", path):
        return "extension"
    return "core"


def _make_readme(
    files: dict[str, str],
    version: str,
    previous_version: str,
    progress: dict[str, Any],
    payload_paths: list[str],
    unknown_count: int,
) -> None:
    readme = files["README.md"]
    metadata_rows = [
        {"項目": "Package Schema Version", "値": SCHEMA_VERSION},
        {"項目": "Package Version", "値": version},
        {"項目": "Previous Package Version", "値": previous_version},
        {"項目": "Current UNKNOWN Count", "値": str(unknown_count)},
        {"項目": "Completion Status", "値": progress["completion_status"]},
        {"項目": "Ready Scope Count", "値": str(len(progress["ready_scope_ids"]))},
        {"項目": "Blocked Scope Count", "値": str(len(progress["blocked_scope_ids"]))},
    ]
    readme = replace_table(readme, "Package metadata", ("項目", "値"), metadata_rows)
    payload_rows = [
        {"順序": str(index), "ファイル": path, "種別": _file_kind(path)}
        for index, path in enumerate(payload_paths, start=1)
    ]
    readme = replace_table(
        readme, "Current payload files", ("順序", "ファイル", "種別"), payload_rows
    )
    scope_map = _scope_by_id_from_files(files)
    ready_body = "\n".join(
        f"- {scope_id}: {scope_map[scope_id]['対象機能 / 領域']}"
        for scope_id in progress["ready_scope_ids"]
    )
    if not ready_body:
        ready_body = "- 進行可能なscopeはありません。"
    blocking = {
        row["scope_id"]: row["blocking_unknown_ids"]
        for row in progress["scope_readiness"]
        if row["status"] == "blocked"
    }
    blocked_body = "\n".join(
        f"- {scope_id}: {scope_map[scope_id]['対象機能 / 領域']}（UNKNOWN: {', '.join(blocking[scope_id])}）"
        for scope_id in progress["blocked_scope_ids"]
    )
    if not blocked_body:
        blocked_body = "- ブロック中のscopeはありません。"
    readme = _replace_section_body(readme, "次の工程へ進める範囲", ready_body)
    readme = _replace_section_body(readme, "ブロック中範囲", blocked_body)
    files["README.md"] = readme


def _scope_by_id_from_files(files: dict[str, str]) -> dict[str, dict[str, str]]:
    rows = parse_table(
        files["00_scope_and_context.md"],
        "分析対象機能scope一覧",
        TABLE_BY_KEY[("00_scope_and_context.md", "分析対象機能scope一覧")].headers,
    )
    return {row["Scope ID"]: row for row in rows}


def _changelog_event_rows(events: list[dict[str, str]]) -> list[dict[str, str]]:
    return [
        {"Stable ID": row["stable_id"], "Change": row["change"]}
        for row in sorted(events, key=lambda row: _id_sort(row["stable_id"]))
    ]


def _render_changelog_entry(
    version: str, summary: str, events: list[dict[str, str]], affected_files: list[str]
) -> str:
    table = render_table(CHANGELOG_HEADER, _changelog_event_rows(events))
    affected = (
        "\n".join(f"- {path}" for path in affected_files)
        if affected_files
        else "- 影響fileはありません。"
    )
    return f"## {version}\n\n### 変更概要\n\n{normalize_text(summary)}\n\n### Stable ID changes\n\n{table}\n\n### 影響file\n\n{affected}\n"


def _replace_latest_changelog(
    existing: str,
    version: str,
    summary: str,
    events: list[dict[str, str]],
    affected_files: list[str],
) -> str:
    headings = list(re.finditer(r"(?m)^## v[0-9]{2,}\s*$", existing))
    rest = ""
    if headings:
        rest = existing[headings[0].end() :]
        next_heading = re.search(r"(?m)^## v[0-9]{2,}\s*$", rest)
        if next_heading:
            rest = rest[next_heading.start() :]
        else:
            rest = ""
    rest = rest.lstrip("\n")
    prefix = "# CHANGELOG\n\n"
    return (
        prefix
        + _render_changelog_entry(version, summary, events, affected_files)
        + ("\n" + rest if rest else "")
    )


def _render_manifest(
    files: dict[str, str],
    payload_paths: list[str],
    version: str,
    receipt: dict[str, Any],
) -> None:
    rows = [
        {
            "順序": str(index),
            "ファイル": path,
            "SHA-256": _sha(canonical_bytes(files[path])),
        }
        for index, path in enumerate(payload_paths, start=1)
    ]
    manifest = (
        "# Package Manifest\n\n"
        f"Package Schema Version: {SCHEMA_VERSION}\n"
        f"Package Version: {version}\n\n"
        "### Package manifest\n\n"
        + render_table(("順序", "ファイル", "SHA-256"), rows)
        + "\n\n### Last materialize receipt\n\n```json\n"
        + canonical_json_bytes(receipt).decode("utf-8")
        + "\n```\n"
    )
    files["MANIFEST.md"] = manifest


def _semantic_files(files: dict[str, str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for name, text in files.items():
        if name in {"MANIFEST.md", "CHANGELOG.md"}:
            continue
        value = text
        if name == "README.md":
            for heading in (
                "Package metadata",
                "Current payload files",
                "次の工程へ進める範囲",
                "ブロック中範囲",
            ):
                try:
                    value = _replace_section_body(value, heading, "")
                except PackageError:
                    pass
        elif name == "09_authority_and_traceability.md":
            pattern = re.compile(
                r"(?ms)^### Machine Entities: spec-analysis\s*\n.*?(?=^### |\Z)"
            )
            value = pattern.sub("", value)
        result[name] = normalize_text(value)
    return result


def _table_change_cells(
    spec: TableSpec, cells: Any, *, allow_draft: bool = True
) -> dict[str, Any]:
    if not isinstance(cells, dict):
        fail("invalid_input", "table_changes.rows[].cellsはobjectである必要があります")
    derived = {spec.id_column} if spec.id_column else set()
    if spec.status_column:
        derived.add(spec.status_column)
    if (spec.file, spec.section) == (
        "00_scope_and_context.md",
        "分析対象機能scope一覧",
    ):
        derived.add("Behavior Decomposition")
    expected = set(spec.headers) - derived
    if set(cells) != expected:
        fail(
            "invalid_input",
            f"table cellsのheader集合が不一致です: {spec.file}/{spec.section}",
        )
    result: dict[str, Any] = {}
    for field, value in cells.items():
        if field in spec.refs:
            if not isinstance(value, list) or any(
                not isinstance(item, str) for item in value
            ):
                fail(
                    "invalid_input",
                    f"stable reference cellはstring arrayで指定してください: {field}",
                )
            if len(value) != len(set(value)):
                fail("duplicate_id", f"stable reference arrayが重複しています: {field}")
            for item in value:
                if allow_draft and item.startswith("@draft:"):
                    if not re.fullmatch(r"@draft:[a-z0-9]+(?:-[a-z0-9]+)*", item):
                        fail("invalid_input", f"draft reference形式が不正です: {item}")
                elif not _valid_id(item):
                    fail("invalid_input", f"stable reference形式が不正です: {item}")
            result[field] = list(value)
        else:
            if not isinstance(value, str):
                fail(
                    "invalid_input",
                    f"通常table cellはstringで指定してください: {field}",
                )
            result[field] = normalize_text(value)
    return result


def _keyed_row_from_input(
    spec: TableSpec, value: Any, *, allow_draft: bool = True
) -> dict[str, str]:
    expected_headers = set(spec.headers) - (
        {"状態"} if spec.section == "条件付き必須file applicability" else set()
    )
    if not isinstance(value, dict) or set(value) != expected_headers:
        fail(
            "invalid_input",
            f"keyed rowのheader集合が不一致です: {spec.file}/{spec.section}",
        )
    row: dict[str, str] = {}
    for field in expected_headers:
        cell = value[field]
        if field in spec.refs:
            if not isinstance(cell, list) or any(
                not isinstance(item, str) for item in cell
            ):
                fail(
                    "invalid_input",
                    f"keyed stable referenceはstring arrayで指定してください: {field}",
                )
            if len(cell) != len(set(cell)):
                fail("duplicate_id", f"keyed reference arrayが重複しています: {field}")
            for item in cell:
                if allow_draft and item.startswith("@draft:"):
                    if not re.fullmatch(r"@draft:[a-z0-9]+(?:-[a-z0-9]+)*", item):
                        fail("invalid_input", f"draft reference形式が不正です: {item}")
                elif not _valid_id(item):
                    fail("invalid_input", f"stable reference形式が不正です: {item}")
            row[field] = "\n".join(cell)
        elif not isinstance(cell, str):
            fail(
                "invalid_input", f"keyed table cellはstringで指定してください: {field}"
            )
        else:
            row[field] = normalize_text(cell)
    if spec.section == "条件付き必須file applicability":
        expected_state = {
            "あり": "required",
            "なし": "not-applicable",
            "未確定": "blocked",
        }.get(row["Trigger判定"])
        if expected_state is None:
            fail("invalid_input", "Trigger判定が不正です")
        row["状態"] = expected_state
        if expected_state == "blocked" and not _split_refs(
            row["関連UNKNOWN ID"], allow_draft=allow_draft
        ):
            fail(
                "state_transition_required",
                "未確定file applicabilityに関連UNKNOWN IDが必要です",
            )
    return row


def _primary_prefix(spec: TableSpec, cells: dict[str, Any]) -> str:
    if spec.section == "UI構造一覧":
        prefix = {
            "PAGE": "PAGE",
            "STATE": "STATE",
            "VIEW": "VIEW",
            "STEP": "STEP",
            "MODAL": "MODAL",
            "BROWSER-DIALOG": "BDLG",
            "PANEL": "PANEL",
            "POPOVER": "PANEL",
            "GLOBAL UI": "PANEL",
            "EXTERNAL": "EXT",
            "SHARED PAGE": "SHARED",
        }.get(cells.get("種別"))
        if prefix is None:
            fail("invalid_input", "UI構造の種別が不正です")
        return prefix
    if spec.section == "通知・外部連携一覧":
        prefix = {
            "通知": "NOTIFY",
            "メール": "NOTIFY",
            "外部連携": "INTERACT",
            "外部遷移イベント": "INTERACT",
        }.get(cells.get("種別"))
        if prefix is None:
            fail("invalid_input", "通知・外部連携の種別が不正です")
        return prefix
    if spec.section == "分析項目":
        prefix = {
            "SPEC": "SPEC",
            "INFERENCE": "INF",
            "UNKNOWN": "UNK",
            "DECISION": "DEC",
            "承認済みASM": "ASM",
        }.get(cells.get("分類"))
        if prefix is None:
            fail("invalid_input", "分析項目の分類が不正です")
        return prefix
    if spec.prefix:
        return spec.prefix
    fail(
        "invalid_input",
        f"stable ID allocatorがないtableです: {spec.file}/{spec.section}",
    )


def _history_ids(changelog: str) -> tuple[set[str], set[str]]:
    all_ids: set[str] = set()
    retired: set[str] = set()
    headings = list(re.finditer(r"(?m)^## v[0-9]{2,}\s*$", changelog))
    for match in headings:
        start = match.start()
        next_match = next((item for item in headings if item.start() > start), None)
        entry = changelog[start : next_match.start() if next_match else len(changelog)]
        try:
            rows = parse_table(entry, "Stable ID changes", CHANGELOG_HEADER)
        except PackageError:
            # Empty unmaterialized asset templates are not current packages.
            continue
        for row in rows:
            all_ids.add(row["Stable ID"])
            if row["Change"] == "retired":
                retired.add(row["Stable ID"])
    return all_ids, retired


def _allocate_id(prefix: str, used: set[str], counters: dict[str, int]) -> str:
    if prefix not in ALLOCATABLE_PREFIXES:
        fail("invalid_input", f"stable ID prefixはこのhelperで採番できません: {prefix}")
    pattern = PREFIX_RE[prefix]
    maximum = counters.get(prefix, 0)
    for stable_id in used:
        match = pattern.fullmatch(stable_id)
        if match:
            maximum = max(maximum, int(stable_id.rsplit("-", 1)[1]))
    if prefix in {"SRC", "SPEC", "INF", "UNK"} and maximum >= 999:
        fail("id_space_exhausted", f"{prefix} ID空間が上限です")
    number = maximum + 1
    stable_id = f"{prefix}-{number:03d}"
    if prefix in {"SRC", "SPEC", "INF", "UNK"} and number > 999:
        fail("id_space_exhausted", f"{prefix} ID空間が上限です")
    counters[prefix] = number
    used.add(stable_id)
    return stable_id


def _resolve_cell_drafts(value: Any, draft_map: dict[str, str]) -> Any:
    if isinstance(value, list):
        result = []
        for item in value:
            if isinstance(item, str) and item.startswith("@draft:"):
                key = item[len("@draft:") :]
                if key not in draft_map:
                    fail(
                        "reference_not_found",
                        f"draft referenceが解決できません: {item}",
                    )
                result.append(draft_map[key])
            else:
                result.append(item)
        return sorted(result, key=_id_sort)
    return value


def _cell_values_to_row(
    spec: TableSpec, stable_id: str, cells: dict[str, Any], draft_map: dict[str, str]
) -> dict[str, str]:
    resolved = {
        field: _resolve_cell_drafts(value, draft_map) for field, value in cells.items()
    }
    row = _empty_row(spec)
    if spec.id_column:
        row[spec.id_column] = stable_id
    for field, value in resolved.items():
        row[field] = "\n".join(value) if isinstance(value, list) else value
    if spec.section == "分析対象機能scope一覧":
        row["Behavior Decomposition"] = {
            "あり": "required",
            "なし": "not-applicable",
            "未確定": "blocked",
        }.get(row["UI操作判定"], "")
    return row


def _derive_tracking_states(
    tables: dict[tuple[str, str], list[dict[str, str]]],
) -> None:
    stories = {
        row["US ID"]: row
        for row in tables.get(
            ("02_behavior_and_business_rules.md", "User Story一覧"), []
        )
    }
    cases = {
        row["UC ID"]: row
        for row in tables.get(("02_behavior_and_business_rules.md", "Use Case一覧"), [])
    }
    behaviors = {
        row["Behavior ID"]: row
        for row in tables.get(("02_behavior_and_business_rules.md", "Behavior一覧"), [])
    }
    for spec in TABLES:
        if not spec.status_column:
            continue
        for row in tables.get((spec.file, spec.section), []):
            missing = any(
                not row.get(field, "").strip() for field in _required_fields(spec, row)
            )
            unknowns = _refs(row, "関連UNKNOWN ID")
            ancestor_blocked = False
            if spec.section == "Use Case一覧":
                ancestor_blocked = any(
                    stories.get(us_id, {}).get("状態") == "blocked"
                    for us_id in _refs(row, "関連US ID")
                )
            elif spec.section == "Behavior一覧":
                ancestor_blocked = cases.get(row["UC ID"], {}).get("状態") == "blocked"
            elif spec.section == "Acceptance Criteria一覧":
                ancestor_blocked = (
                    behaviors.get(row["Behavior ID"], {}).get("状態") == "blocked"
                )
            normal_state = "mapped" if spec.section == "UI操作一覧" else "current"
            row[spec.status_column] = (
                "blocked" if missing or unknowns or ancestor_blocked else normal_state
            )
    for row in tables.get(("00_scope_and_context.md", "分析対象機能scope一覧"), []):
        row["Behavior Decomposition"] = {
            "あり": "required",
            "なし": "not-applicable",
            "未確定": "blocked",
        }.get(row["UI操作判定"], "")
    for row in tables.get(
        ("00_scope_and_context.md", "条件付き必須file applicability"), []
    ):
        row["状態"] = {
            "あり": "required",
            "なし": "not-applicable",
            "未確定": "blocked",
        }.get(row["Trigger判定"], "")


def _apply_table_changes(
    files: dict[str, str],
    tables: dict[tuple[str, str], list[dict[str, str]]],
    request: dict[str, Any],
    previous: PackageModel | None,
    change_mode: str,
    retained_ids: set[str],
    reserved_ids: set[str] | None = None,
) -> tuple[dict[str, str], dict[str, str]]:
    changes = request.get("table_changes", [])
    if not isinstance(changes, list):
        fail("invalid_input", "table_changesはarrayである必要があります")
    parsed: list[tuple[int, TableSpec, list[dict[str, Any]]]] = []
    seen_tables: set[tuple[str, str]] = set()
    table_order = {
        (spec.file, spec.section): index for index, spec in enumerate(TABLES)
    }
    for change in changes:
        if not isinstance(change, dict) or set(change) != {"file", "section", "rows"}:
            fail("invalid_input", "table_changes item schemaが不正です")
        key = (change["file"], change["section"])
        spec = TABLE_BY_KEY.get(key)
        if spec is None or spec.id_column is None:
            fail(
                "invalid_input",
                f"table_changes targetはtracking tableだけ許可されます: {key}",
            )
        if key in seen_tables:
            fail("duplicate_id", f"table_changes targetが重複しています: {key}")
        seen_tables.add(key)
        if not isinstance(change["rows"], list):
            fail("invalid_input", "table_changes.rowsはarrayである必要があります")
        parsed.append((table_order[key], spec, change["rows"]))
    parsed.sort(key=lambda item: item[0])
    for _, spec, _rows_in_request in parsed:
        key = (spec.file, spec.section)
        if key not in tables:
            asset = ASSET_ROOT / spec.file
            if not asset.is_file():
                fail(
                    "package_schema_mismatch", f"table用assetがありません: {spec.file}"
                )
            try:
                files[spec.file] = _decode_current(asset.read_bytes(), spec.file)
            except OSError as exc:
                fail("file_unreadable", f"table assetを読めません: {spec.file}: {exc}")
            tables[key] = parse_table(files[spec.file], spec.section, spec.headers)
    previous_rows: dict[tuple[str, str, str], dict[str, str]] = {}
    if previous is not None:
        for spec in TABLES:
            if spec.id_column:
                for row in _rows(previous, spec.file, spec.section):
                    previous_rows[(spec.file, spec.section, row[spec.id_column])] = row
    used = set(retained_ids) | set(reserved_ids or set())
    if previous is not None:
        used.update(_tracked_ids(previous.tables))
        history, retired = _history_ids(previous.files["CHANGELOG.md"])
        used.update(history)
    else:
        history, retired = set(), set()
        for rows in tables.values():
            for row in rows:
                for value in row.values():
                    used.update(
                        item
                        for item in re.findall(r"[A-Z]+-[0-9]{3,}", value)
                        if _valid_id(item)
                    )
    draft_map: dict[str, str] = {}
    pending: list[tuple[TableSpec, dict[str, Any], str]] = []
    for _, spec, rows in parsed:
        for row in rows:
            if not isinstance(row, dict) or set(row) != {
                "draft_key",
                "identity_action",
                "reuse_id",
                "external_id",
                "cells",
            }:
                fail("invalid_input", "table_changes row identity schemaが不正です")
            cells = _table_change_cells(spec, row["cells"])
            action = row["identity_action"]
            if action == "new":
                key = row["draft_key"]
                if (
                    not isinstance(key, str)
                    or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", key)
                    or row["reuse_id"] is not None
                    or row["external_id"] is not None
                ):
                    fail("invalid_input", "new tracking row identityが不正です")
                if key in draft_map:
                    fail("duplicate_id", f"draft_keyが重複しています: {key}")
                prefix = _primary_prefix(spec, cells)
                if prefix not in ALLOCATABLE_PREFIXES:
                    fail(
                        "invalid_input",
                        f"DEC / ASMは外部ownerのIDをexternalで渡してください: {prefix}",
                    )
                stable_id = _allocate_id(prefix, used, {})
                draft_map[key] = stable_id
                pending.append((spec, row, stable_id))
            elif action == "reuse":
                if (
                    row["draft_key"] is not None
                    or row["external_id"] is not None
                    or not isinstance(row["reuse_id"], str)
                ):
                    fail("invalid_input", "reuse tracking row identityが不正です")
                stable_id = row["reuse_id"]
                prior = previous_rows.get((spec.file, spec.section, stable_id))
                if prior is None and not (
                    change_mode == "legacy-migration" and stable_id in retained_ids
                ):
                    fail(
                        "reference_not_found",
                        f"reuse IDがprevious model / migration retained IDsにありません: {stable_id}",
                    )
                prefix = _primary_prefix(spec, cells)
                if _id_prefix(stable_id) != prefix:
                    fail(
                        "state_transition_required",
                        f"reuse ID prefixがsemantic selectorと不一致です: {stable_id}",
                    )
                if stable_id in retired:
                    fail(
                        "duplicate_id",
                        f"retired stable IDを再利用できません: {stable_id}",
                    )
                pending.append((spec, row, stable_id))
            elif action == "external":
                key = row["draft_key"]
                external_id = row["external_id"]
                if (
                    spec.section != "分析項目"
                    or not isinstance(key, str)
                    or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", key)
                    or row["reuse_id"] is not None
                    or not isinstance(external_id, str)
                ):
                    fail(
                        "invalid_input",
                        "external identityはanalysis itemのDEC / ASMだけ許可されます",
                    )
                if (
                    key in draft_map
                    or external_id in used
                    or not _valid_id(external_id)
                ):
                    fail(
                        "duplicate_id",
                        f"external owner IDが重複または不正です: {external_id}",
                    )
                expected = _primary_prefix(spec, cells)
                if (
                    expected not in {"DEC", "ASM"}
                    or _id_prefix(external_id) != expected
                ):
                    fail(
                        "invalid_input",
                        f"external owner IDと分類が一致しません: {external_id}/{expected}",
                    )
                draft_map[key] = external_id
                used.add(external_id)
                pending.append((spec, row, external_id))
            else:
                fail("invalid_input", f"identity_actionが不正です: {action}")
    for spec, row, stable_id in pending:
        cells = _table_change_cells(spec, row["cells"])
        final_cells = {
            field: _resolve_cell_drafts(value, draft_map)
            for field, value in cells.items()
        }
        row_data = _cell_values_to_row(spec, stable_id, final_cells, {})
        if previous is not None and spec.file in CONDITIONAL_FILES:
            app_by_scope = {
                (app["ファイル"], app["Scope ID"]): app
                for app in _rows(
                    previous,
                    "00_scope_and_context.md",
                    "条件付き必須file applicability",
                )
            }
            row_scopes = (
                _refs(row_data, "Scope ID")
                if "Scope ID" in row_data
                else _refs(row_data, "関連Scope ID")
                if "関連Scope ID" in row_data
                else []
            )
            for scope_id in row_scopes:
                app = app_by_scope.get((spec.file, scope_id))
                if app is not None and app["状態"] != "required":
                    fail(
                        "state_transition_required",
                        f"conditional tracking rowはrequired scopeだけ更新できます: {spec.file}/{scope_id}",
                    )
        rows = tables[(spec.file, spec.section)]
        if spec.id_column:
            rows[:] = [
                existing for existing in rows if existing[spec.id_column] != stable_id
            ]
        rows.append(row_data)
        rows.sort(key=lambda value: _id_sort(value[spec.id_column]))
    _derive_tracking_states(tables)
    for spec in TABLES:
        if spec.file in files and (spec.file, spec.section) in tables:
            files[spec.file] = replace_table(
                files[spec.file],
                spec.section,
                spec.headers,
                tables[(spec.file, spec.section)],
            )
    return draft_map, {"retired_ids": []}


KEYED_TABLE_KEYS = {
    ("00_scope_and_context.md", "条件付き必須file applicability"),
    ("02_behavior_and_business_rules.md", "Use Case振る舞い完全性"),
    ("07_current_unknowns.md", "Current UNKNOWN一覧"),
    ("08_repository_implementation_status.md", "Repository確認基準"),
    ("09_authority_and_traceability.md", "現在有効な仕様根拠"),
    ("09_authority_and_traceability.md", "後続Skillへの補足"),
}
KEY_COLUMNS = {
    "条件付き必須file applicability": ("ファイル", "Scope ID"),
    "Use Case振る舞い完全性": ("UC ID", "結果分類"),
    "Current UNKNOWN一覧": ("UNKNOWN ID",),
    "Repository確認基準": ("Repository",),
    "現在有効な仕様根拠": ("仕様根拠ID",),
    "後続Skillへの補足": ("項目",),
}


def _apply_keyed_updates(
    files: dict[str, str],
    tables: dict[tuple[str, str], list[dict[str, str]]],
    request: dict[str, Any],
    previous: PackageModel | None,
    draft_map: dict[str, str],
    change_mode: str,
) -> None:
    updates = request.get("keyed_table_updates", [])
    if not isinstance(updates, list):
        fail("invalid_input", "keyed_table_updatesはarrayである必要があります")
    seen: set[tuple[str, str]] = set()
    for update in updates:
        if not isinstance(update, dict) or set(update) != {"file", "section", "rows"}:
            fail("invalid_input", "keyed_table_updates item schemaが不正です")
        key = (update["file"], update["section"])
        if key not in KEYED_TABLE_KEYS:
            fail("invalid_input", f"keyed_table_updates targetがregistry外です: {key}")
        if key in seen:
            fail("duplicate_id", f"keyed_table_updates targetが重複しています: {key}")
        seen.add(key)
        spec = TABLE_BY_KEY[key]
        if key not in tables:
            asset = ASSET_ROOT / spec.file
            if not asset.is_file():
                fail(
                    "package_schema_mismatch",
                    f"keyed table用assetがありません: {spec.file}",
                )
            try:
                files[spec.file] = _decode_current(asset.read_bytes(), spec.file)
            except OSError as exc:
                fail(
                    "file_unreadable",
                    f"keyed table assetを読めません: {spec.file}: {exc}",
                )
            tables[key] = parse_table(files[spec.file], spec.section, spec.headers)
        if not isinstance(update["rows"], list):
            fail("invalid_input", "keyed_table_updates.rowsはarrayである必要があります")
        new_rows = [_keyed_row_from_input(spec, value) for value in update["rows"]]
        # Resolve same-request references only after all tracking IDs are known.
        for row in new_rows:
            for field in KEY_COLUMNS[spec.section]:
                key_value = row[field]
                if field in {"Scope ID", "UC ID", "UNKNOWN ID", "仕様根拠ID"}:
                    if key_value.startswith("@draft:"):
                        draft_key = key_value[len("@draft:") :]
                        if draft_key not in draft_map:
                            fail(
                                "reference_not_found",
                                f"keyed stable ID draftを解決できません: {key_value}",
                            )
                        row[field] = draft_map[draft_key]
                    elif not _valid_id(key_value):
                        fail(
                            "invalid_input",
                            f"keyed stable ID形式が不正です: {key_value}",
                        )
            for field in spec.refs:
                if row.get(field):
                    refs = _split_refs(row[field], allow_draft=True)
                    row[field] = "\n".join(_resolve_cell_drafts(refs, draft_map))
        key_columns = KEY_COLUMNS[spec.section]
        keys: set[tuple[str, ...]] = set()
        for row in new_rows:
            identity = tuple(row[column] for column in key_columns)
            if identity in keys:
                fail("duplicate_id", f"keyed table keyが重複しています: {identity}")
            keys.add(identity)
        if spec.section == "条件付き必須file applicability":
            if previous is not None:
                prior = {
                    (row["ファイル"], row["Scope ID"]): row
                    for row in _rows(previous, spec.file, spec.section)
                }
                for row in new_rows:
                    old = prior.get((row["ファイル"], row["Scope ID"]))
                    if old is not None and old["状態"] == "blocked" and row != old:
                        fail(
                            "state_transition_required",
                            f"blocked scopeのapplicabilityはcarry-forwardしてください: {row['ファイル']}/{row['Scope ID']}",
                        )
            new_rows.sort(
                key=lambda row: (
                    CONDITIONAL_FILES.index(row["ファイル"]),
                    _id_sort(row["Scope ID"]),
                )
            )
        elif spec.section == "Use Case振る舞い完全性":
            category_order = {"正常": 0, "準正常": 1, "例外": 2}
            new_rows.sort(
                key=lambda row: (
                    _id_sort(row["UC ID"]),
                    category_order.get(row["結果分類"], 99),
                )
            )
        elif spec.section in {"Current UNKNOWN一覧", "現在有効な仕様根拠"}:
            id_column = key_columns[0]
            new_rows.sort(key=lambda row: _id_sort(row[id_column]))
        else:
            new_rows.sort(key=lambda row: tuple(row[column] for column in key_columns))
        tables[key] = new_rows
        if spec.file in files:
            files[spec.file] = replace_table(
                files[spec.file], spec.section, spec.headers, new_rows
            )
    if previous is None or change_mode == "legacy-migration":
        required = {
            ("00_scope_and_context.md", "条件付き必須file applicability"),
            ("07_current_unknowns.md", "Current UNKNOWN一覧"),
        }
        if not required <= seen:
            fail(
                "invalid_input",
                "create / migrationにはapplicabilityとCurrent UNKNOWNのfull replacementが必要です",
            )
    if (
        "00_scope_and_context.md",
        "条件付き必須file applicability",
    ) not in seen and previous is None:
        fail("invalid_input", "createではfile applicabilityを必ず指定してください")


PROSE_HEADINGS = {
    "README.md": {"対象とAuthority方針"},
    "00_scope_and_context.md": {
        "対象機能",
        "対象ユーザー / ロール",
        "対象画面",
        "対象情報源",
        "正本 / 優先順位",
        "対象外",
        "用語",
        "分析上の前提",
    },
    "01_ui_structure_and_navigation.md": {"Navigation / Entry / Exit"},
}


def _apply_prose_updates(files: dict[str, str], request: dict[str, Any]) -> None:
    updates = request.get("prose_updates", [])
    if not isinstance(updates, list):
        fail("invalid_input", "prose_updatesはarrayである必要があります")
    seen: set[tuple[str, str]] = set()
    for update in updates:
        if (
            not isinstance(update, dict)
            or set(update) != {"file", "section", "body_markdown"}
            or not isinstance(update["body_markdown"], str)
        ):
            fail("invalid_input", "prose_updates item schemaが不正です")
        file, section = update["file"], update["section"]
        if (
            file not in PROSE_HEADINGS
            or section not in PROSE_HEADINGS[file]
            or file not in files
        ):
            fail(
                "invalid_input",
                f"prose update targetは既存の自由記述sectionではありません: {file}/{section}",
            )
        if (file, section) in seen:
            fail(
                "duplicate_id", f"prose update targetが重複しています: {file}/{section}"
            )
        seen.add((file, section))
        files[file] = _replace_user_prose_body(
            files[file], section, normalize_text(update["body_markdown"])
        )


def _validate_ref_array(
    value: Any, name: str, *, allow_draft: bool = True
) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        fail("invalid_input", f"{name}はstable ID string arrayである必要があります")
    if len(value) != len(set(value)):
        fail("duplicate_id", f"{name}が重複しています")
    for item in value:
        if allow_draft and item.startswith("@draft:"):
            if not re.fullmatch(r"@draft:[a-z0-9]+(?:-[a-z0-9]+)*", item):
                fail("invalid_input", f"draft reference形式が不正です: {item}")
        elif not _valid_id(item):
            fail("invalid_input", f"stable ID形式が不正です: {item}")
    return list(value)


def _apply_extensions(
    files: dict[str, str],
    tables: dict[tuple[str, str], list[dict[str, str]]],
    request: dict[str, Any],
    draft_map: dict[str, str],
    previous: PackageModel | None,
) -> tuple[dict[str, str], list[dict[str, str]], list[str]]:
    updates = request.get("extension_file_updates", [])
    retirements = request.get("extension_file_retirements", [])
    if (
        not isinstance(updates, list)
        or not isinstance(retirements, list)
        or any(not isinstance(value, str) for value in retirements)
    ):
        fail("invalid_input", "extension updates / retirements schemaが不正です")
    declarations = tables[("00_scope_and_context.md", "案件固有extension file一覧")]
    existing = {row["ファイル"]: row for row in declarations}
    if previous is not None:
        old_paths = set(_extension_paths(previous.tables))
    else:
        old_paths = set()
    if len(retirements) != len(set(retirements)):
        fail("duplicate_id", "extension_file_retirementsが重複しています")
    if not set(retirements) <= old_paths:
        fail(
            "reference_not_found",
            "retire対象extension fileがprevious packageにありません",
        )
    draft_keys: set[str] = set()
    used_paths = set(existing)
    max_number = max((int(path.split("_", 1)[0]) for path in used_paths), default=9)
    allocated: list[dict[str, str]] = []
    updated_paths: set[str] = set()
    new_declarations = {
        path: dict(row)
        for path, row in existing.items()
        if path not in set(retirements)
    }
    retired_paths = list(retirements)
    for item in updates:
        expected_keys = {
            "draft_key",
            "identity_action",
            "path",
            "slug",
            "responsibility",
            "split_reason",
            "scope_refs",
            "authority_refs",
            "structure_refs",
            "unknown_refs",
            "body_markdown",
        }
        if not isinstance(item, dict) or set(item) != expected_keys:
            fail("invalid_input", "extension_file_updates item schemaが不正です")
        action, draft_key, path = (
            item["identity_action"],
            item["draft_key"],
            item["path"],
        )
        if action == "new":
            if (
                not isinstance(draft_key, str)
                or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", draft_key)
                or draft_key in draft_keys
            ):
                fail("invalid_input", "new extension draft identityが不正です")
            draft_keys.add(draft_key)
            if path is not None:
                fail("invalid_input", "new extension pathはnullで指定します")
            max_number += 1
            path = f"{max_number}_{item['slug']}.md"
            if path in used_paths:
                fail("duplicate_id", f"extension pathが重複しています: {path}")
            allocated.append({"draft_key": draft_key, "path": path})
        elif action == "reuse":
            if (
                draft_key is not None
                or not isinstance(path, str)
                or path not in old_paths
                or path in set(retirements)
            ):
                fail(
                    "reference_not_found",
                    "reuse extension identityがprevious packageにありません",
                )
        else:
            fail("invalid_input", f"extension identity_actionが不正です: {action}")
        if path in updated_paths:
            fail(
                "duplicate_id",
                f"extension fileが同じrequestで重複更新されています: {path}",
            )
        updated_paths.add(path)
        slug = item["slug"]
        if (
            not isinstance(slug, str)
            or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug)
            or not path.endswith(f"_{slug}.md")
        ):
            fail("invalid_input", "extension slugとpathが一致しません")
        for field in ("responsibility", "split_reason", "body_markdown"):
            if not isinstance(item[field], str) or not item[field].strip():
                fail("invalid_input", f"extension {field}はnon-empty stringです")
        ref_values = {}
        for field in ("scope_refs", "authority_refs", "structure_refs", "unknown_refs"):
            ref_values[field] = _validate_ref_array(item[field], field)
        ref_values = {
            field: _resolve_cell_drafts(values, draft_map)
            for field, values in ref_values.items()
        }
        row = {
            "ファイル": path,
            "Slug": slug,
            "責務": normalize_text(item["responsibility"]),
            "分割理由": normalize_text(item["split_reason"]),
            "関連Scope ID": "\n".join(ref_values["scope_refs"]),
            "関連仕様項目ID": "\n".join(ref_values["authority_refs"]),
            "関連構造ID": "\n".join(ref_values["structure_refs"]),
            "関連UNKNOWN ID": "\n".join(ref_values["unknown_refs"]),
        }
        new_declarations[path] = row
        files[path] = normalize_text(item["body_markdown"])
    for path in retired_paths:
        files.pop(path, None)
        new_declarations.pop(path, None)
    declarations = sorted(
        new_declarations.values(), key=lambda row: int(row["ファイル"].split("_", 1)[0])
    )
    tables[("00_scope_and_context.md", "案件固有extension file一覧")] = declarations
    files["00_scope_and_context.md"] = replace_table(
        files["00_scope_and_context.md"],
        "案件固有extension file一覧",
        TABLE_BY_KEY[("00_scope_and_context.md", "案件固有extension file一覧")].headers,
        declarations,
    )
    return files, allocated, retired_paths


def _apply_retirements(
    tables: dict[tuple[str, str], list[dict[str, str]]],
    retire_ids: Any,
    previous: PackageModel | None,
) -> list[str]:
    if not isinstance(retire_ids, list) or any(
        not isinstance(value, str) for value in retire_ids
    ):
        fail("invalid_input", "retire_idsはstring arrayである必要があります")
    if len(retire_ids) != len(set(retire_ids)):
        fail("duplicate_id", "retire_idsが重複しています")
    if retire_ids and previous is None:
        fail("invalid_input", "create / migrationではretire_idsを使用できません")
    prior: dict[str, tuple[TableSpec, dict[str, str]]] = {}
    if previous is not None:
        for spec in TABLES:
            if spec.id_column:
                for row in _rows(previous, spec.file, spec.section):
                    prior[row[spec.id_column]] = (spec, row)
    for stable_id in retire_ids:
        if not _valid_id(stable_id):
            fail("invalid_input", f"retire ID形式が不正です: {stable_id}")
        if stable_id.startswith(("DEC-", "ASM-")):
            fail(
                "state_transition_required",
                f"外部owner IDはretireできません: {stable_id}",
            )
        owner = prior.get(stable_id)
        if owner is None:
            fail(
                "reference_not_found",
                f"retire IDがprevious packageにありません: {stable_id}",
            )
    retire_set = set(retire_ids)
    for stable_id in retire_ids:
        spec, _row = prior[stable_id]
        tables[(spec.file, spec.section)] = [
            row
            for row in tables[(spec.file, spec.section)]
            if row[spec.id_column] != stable_id
        ]
    # Removal from tracking tables is accepted only when explicitly listed.
    if previous is not None:
        retire_set = set(retire_ids)
        for spec in TABLES:
            if not spec.id_column:
                continue
            current_ids = {
                row[spec.id_column] for row in tables.get((spec.file, spec.section), [])
            }
            previous_ids = {
                row[spec.id_column] for row in _rows(previous, spec.file, spec.section)
            }
            missing = previous_ids - current_ids
            if missing != retire_set & previous_ids:
                fail(
                    "state_transition_required",
                    f"tracking row消失とretire intentが一致しません: {sorted(missing ^ (retire_set & previous_ids))}",
                )
    return sorted(retire_ids, key=_id_sort)


def _materialize_conditional_files(
    files: dict[str, str],
    tables: dict[tuple[str, str], list[dict[str, str]]],
    previous: PackageModel | None,
    retire_ids: list[str],
) -> None:
    applicability = tables.get(
        ("00_scope_and_context.md", "条件付き必須file applicability"), []
    )
    by_file: dict[str, list[dict[str, str]]] = {name: [] for name in CONDITIONAL_FILES}
    for row in applicability:
        by_file[row["ファイル"]].append(row)
    for path in CONDITIONAL_FILES:
        rows = by_file[path]
        required = any(row["状態"] == "required" for row in rows)
        blocked = any(row["状態"] == "blocked" for row in rows)
        existed = previous is not None and path in previous.files
        if required and path not in files:
            asset = ASSET_ROOT / path
            try:
                files[path] = _decode_current(asset.read_bytes(), path)
            except OSError as exc:
                fail(
                    "file_unreadable",
                    f"conditional file assetを読めません: {path}: {exc}",
                )
            spec_tables = [spec for spec in TABLES if spec.file == path]
            for spec in spec_tables:
                tables[(spec.file, spec.section)] = parse_table(
                    files[path], spec.section, spec.headers
                )
        if blocked and not required and not existed:
            for spec in TABLES:
                if spec.file != path or not spec.id_column:
                    continue
                for row in tables.get((spec.file, spec.section), []):
                    row_scopes = (
                        _refs(row, "関連Scope ID") if "関連Scope ID" in row else []
                    )
                    if any(
                        app["Scope ID"] in row_scopes and app["状態"] == "blocked"
                        for app in rows
                    ):
                        fail(
                            "state_transition_required",
                            f"createではblocked scopeのconditional tracking rowを生成できません: {path}",
                        )
        if not required and not blocked:
            if path in files:
                pending = []
                for spec in TABLES:
                    if spec.file == path and spec.id_column:
                        pending.extend(
                            row[spec.id_column]
                            for row in tables.get((spec.file, spec.section), [])
                        )
                missing = set(pending) - set(retire_ids)
                if missing:
                    fail(
                        "state_transition_required",
                        f"conditional file除去にはtracked IDを明示retireしてください: {sorted(missing)}",
                    )
                files.pop(path, None)
                for spec in TABLES:
                    if spec.file == path:
                        tables.pop((spec.file, spec.section), None)
        elif path not in files and blocked and not required:
            # A blocked-only file is omitted in create and may be omitted after
            # its prior rows have been retired.
            continue
        if path in files:
            for spec in TABLES:
                if spec.file == path and (spec.file, spec.section) in tables:
                    files[path] = replace_table(
                        files[path],
                        spec.section,
                        spec.headers,
                        tables[(spec.file, spec.section)],
                    )


def _materialize_table_text(
    files: dict[str, str], tables: dict[tuple[str, str], list[dict[str, str]]]
) -> None:
    for spec in TABLES:
        if spec.file in files and (spec.file, spec.section) in tables:
            files[spec.file] = replace_table(
                files[spec.file],
                spec.section,
                spec.headers,
                tables[(spec.file, spec.section)],
            )


def _validate_previous_model_transition(
    previous: PackageModel | None,
    tables: dict[tuple[str, str], list[dict[str, str]]],
    retire_ids: list[str],
    change_mode: str,
    retained_ids: set[str],
) -> None:
    if previous is None:
        if change_mode == "legacy-migration":
            present = set()
            for spec in TABLES:
                if spec.id_column:
                    present.update(
                        row[spec.id_column]
                        for row in tables.get((spec.file, spec.section), [])
                    )
            if not retained_ids <= present:
                fail(
                    "state_transition_required",
                    f"migration retained IDがcurrent modelにありません: {sorted(retained_ids - present)}",
                )
        return
    previous_ids = _tracked_ids(previous.tables)
    current_ids = _tracked_ids(tables)
    tracked_previous = {
        row[spec.id_column]
        for spec in TABLES
        if spec.id_column
        for row in _rows(previous, spec.file, spec.section)
    }
    tracked_current = {
        row[spec.id_column]
        for spec in TABLES
        if spec.id_column
        for row in tables.get((spec.file, spec.section), [])
    }
    missing = tracked_previous - tracked_current
    if missing != set(retire_ids):
        fail(
            "state_transition_required",
            "previous stable IDs消失にはexact retire_idsが必要です",
        )
    if set(retire_ids) & tracked_current:
        fail(
            "state_transition_required",
            "retire_idsがcurrent tracking rowへ残っています",
        )
    if previous_ids and not current_ids:
        # Zero current rows are only legal when all package-owned identities
        # were explicitly retired; the downstream terminal route handles it.
        if not tracked_previous <= set(retire_ids):
            fail(
                "state_transition_required",
                "package-owned stable ID retirementが不足しています",
            )


def _migration_inputs(request: dict[str, Any]) -> tuple[set[str], list[dict[str, str]]]:
    retained = request["migration_retained_ids"]
    legacy_events = request["legacy_lifecycle_events"]
    if not isinstance(retained, list) or any(
        not isinstance(value, str) or not _valid_id(value) for value in retained
    ):
        fail("invalid_input", "migration_retained_idsはstable ID string arrayです")
    if len(retained) != len(set(retained)):
        fail("duplicate_id", "migration_retained_idsが重複しています")
    if not isinstance(legacy_events, list):
        fail("invalid_input", "legacy_lifecycle_eventsはarrayです")
    events: list[dict[str, str]] = []
    seen: set[str] = set()
    for row in legacy_events:
        if not isinstance(row, dict) or set(row) != {"stable_id", "change"}:
            fail("invalid_input", "legacy_lifecycle_events row schemaが不正です")
        stable_id, change = row["stable_id"], row["change"]
        if (
            not isinstance(stable_id, str)
            or not _valid_id(stable_id)
            or change not in {"changed", "resolved", "retired"}
        ):
            fail("invalid_input", "legacy lifecycle eventが不正です")
        if stable_id in seen:
            fail("duplicate_id", f"legacy lifecycle eventが重複しています: {stable_id}")
        if change == "resolved" and not stable_id.startswith("UNK-"):
            fail("invalid_input", f"resolvedはUNKNOWNだけに使えます: {stable_id}")
        if change == "retired" and stable_id.startswith(("DEC-", "ASM-")):
            fail("invalid_input", f"external owner IDはretiredできません: {stable_id}")
        seen.add(stable_id)
        events.append({"stable_id": stable_id, "change": change})
    if set(retained) & {
        row["stable_id"] for row in events if row["change"] == "retired"
    }:
        fail(
            "state_transition_required",
            "retired legacy IDをretained current IDに含められません",
        )
    return set(retained), events


def _apply_lifecycle_events(
    tables: dict[tuple[str, str], list[dict[str, str]]],
    previous: PackageModel | None,
    retired_ids: list[str],
    change_mode: str,
    retained_ids: set[str],
    legacy_events: list[dict[str, str]],
) -> list[dict[str, str]]:
    if previous is None and change_mode == "normal":
        return []
    if change_mode == "legacy-migration":
        current_ids = {
            row[spec.id_column]
            for spec in TABLES
            if spec.id_column
            for row in tables.get((spec.file, spec.section), [])
        }
        if not retained_ids <= current_ids:
            fail(
                "state_transition_required",
                f"retained IDがcurrent modelにありません: {sorted(retained_ids - current_ids)}",
            )
        for event in legacy_events:
            if event["change"] == "retired" and event["stable_id"] in current_ids:
                fail(
                    "state_transition_required",
                    f"legacy retired IDがcurrent modelに残っています: {event['stable_id']}",
                )
            if event["change"] == "resolved":
                item = next(
                    (
                        row
                        for row in tables.get(
                            ("09_authority_and_traceability.md", "分析項目"), []
                        )
                        if row["項目ID"] == event["stable_id"]
                    ),
                    None,
                )
                if (
                    item is None
                    or item["分類"] != "UNKNOWN"
                    or item["現在有効か"] != "No"
                ):
                    fail(
                        "state_transition_required",
                        f"legacy resolved eventとcurrent UNKNOWNが不一致です: {event['stable_id']}",
                    )
            if (
                event["change"] in {"changed", "resolved"}
                and event["stable_id"] not in current_ids
            ):
                fail(
                    "state_transition_required",
                    f"legacy lifecycle eventのcurrent rowがありません: {event['stable_id']}",
                )
        events = []
        event_map = {row["stable_id"]: row["change"] for row in legacy_events}
        for stable_id in current_ids:
            if stable_id in retained_ids:
                change = event_map.get(stable_id, "migrated")
                events.append({"stable_id": stable_id, "change": change})
            else:
                events.append({"stable_id": stable_id, "change": "added"})
        events.extend(row for row in legacy_events if row["change"] == "retired")
        return sorted(events, key=lambda row: _id_sort(row["stable_id"]))
    assert previous is not None
    before: dict[str, tuple[TableSpec, dict[str, str]]] = {}
    after: dict[str, tuple[TableSpec, dict[str, str]]] = {}
    for spec in TABLES:
        if not spec.id_column:
            continue
        for row in _rows(previous, spec.file, spec.section):
            before[row[spec.id_column]] = (spec, row)
        for row in tables.get((spec.file, spec.section), []):
            after[row[spec.id_column]] = (spec, row)
    events = []
    for stable_id in sorted(set(before) | set(after), key=_id_sort):
        if stable_id in retired_ids:
            events.append({"stable_id": stable_id, "change": "retired"})
        elif stable_id not in before:
            events.append({"stable_id": stable_id, "change": "added"})
        elif stable_id not in after:
            fail(
                "state_transition_required",
                f"stable row消失に明示retireがありません: {stable_id}",
            )
        elif before[stable_id][1] != after[stable_id][1]:
            change = "changed"
            if stable_id.startswith("UNK-"):
                old = before[stable_id][1]
                new = after[stable_id][1]
                if old.get("現在有効か") == "Yes" and new.get("現在有効か") == "No":
                    change = "resolved"
            events.append({"stable_id": stable_id, "change": change})
    return events


def _impact_files(
    events: list[dict[str, str]],
    previous: PackageModel | None,
    current_tables: dict[tuple[str, str], list[dict[str, str]]],
) -> list[str]:
    changed_ids = {row["stable_id"] for row in events}
    result: set[str] = set()
    current_by_id, current_authorities = _table_index(current_tables)
    current_model = PackageModel(
        Path("."),
        {},
        {},
        current_tables,
        {},
        {},
        [],
        {},
        [],
        current_by_id,
        current_authorities,
    )
    current_reference_index = _reference_index(current_model)
    for stable_id in changed_ids:
        if previous is not None:
            for spec in TABLES:
                if spec.id_column and any(
                    row[spec.id_column] == stable_id
                    for row in _rows(previous, spec.file, spec.section)
                ):
                    result.add(spec.file)
            for entry in _reference_index(previous):
                if entry["target_id"] == stable_id:
                    result.add(entry["file"])
        for spec in TABLES:
            if spec.id_column and any(
                row[spec.id_column] == stable_id
                for row in current_tables.get((spec.file, spec.section), [])
            ):
                result.add(spec.file)
        for entry in current_reference_index:
            if entry["target_id"] == stable_id:
                result.add(entry["file"])
    order = {path: index for index, path in enumerate(CANONICAL_ORDER)}
    return sorted(
        result,
        key=lambda path: (
            order.get(path, 100),
            int(path.split("_", 1)[0]) if path[:1].isdigit() else 0,
            path,
        ),
    )


def _payload_from_progress(progress: dict[str, Any]) -> dict[str, Any]:
    return {
        key: progress[key]
        for key in (
            "completion_status",
            "current_scope_ids",
            "ready_scope_ids",
            "blocked_scope_ids",
            "scope_readiness",
        )
    }


def _materialize_response(
    receipt: dict[str, Any],
    request_fingerprint: str,
    progress: dict[str, Any],
    *,
    replayed: bool,
) -> dict[str, Any]:
    return {
        "changed": receipt["changed"],
        "replayed": replayed,
        "request_fingerprint": request_fingerprint,
        **_payload_from_progress(progress),
        "allocated_ids": receipt["allocated_ids"],
        "allocated_extension_files": receipt["allocated_extension_files"],
        "retired_ids": receipt["retired_ids"],
        "retired_extension_files": receipt["retired_extension_files"],
        "changed_files": receipt["changed_files"],
        "previous_package_version": receipt["previous_package_version"],
        "package_version": receipt["package_version"],
    }


def _normalize_materialize_request(request: dict[str, Any]) -> dict[str, Any]:
    value = {
        key: child
        for key, child in request.items()
        if key not in {"operation", "package_root"}
    }

    def normalize(node: Any) -> Any:
        if isinstance(node, str):
            return normalize_text(node)
        if isinstance(node, list):
            return [normalize(child) for child in node]
        if isinstance(node, dict):
            return {key: normalize(child) for key, child in node.items()}
        return node

    return normalize(value)


def _write_staging(
    staging: Path,
    files: dict[str, str],
    payload_paths: list[str],
    version: str,
    previous_version: str,
    progress: dict[str, Any],
    receipt: dict[str, Any],
) -> None:
    _remove_owned(staging)
    staging.mkdir()
    ordered = payload_paths
    for rel in ordered:
        path = canonical_path(staging, rel)
        raw = canonical_bytes(files[rel])
        try:
            with path.open("xb") as handle:
                handle.write(raw)
        except OSError as exc:
            fail("write_commit_failed", f"staging payloadを書けません: {rel}: {exc}")
    _render_manifest(files, payload_paths, version, receipt)
    try:
        with (staging / "MANIFEST.md").open("xb") as handle:
            handle.write(canonical_bytes(files["MANIFEST.md"]))
    except OSError as exc:
        fail("write_commit_failed", f"staging MANIFESTを書けません: {exc}")


def _commit_package(root: Path, staging: Path, backup: Path, *, had_root: bool) -> None:
    moved_old = False
    try:
        if had_root:
            root.rename(backup)
            moved_old = True
        elif root.exists():
            # create is permitted to target an empty directory only.
            if any(root.iterdir()):
                fail(
                    "write_commit_failed",
                    "create targetがcommit直前に空ではなくなりました",
                )
            root.rmdir()
        staging.rename(root)
    except Exception as exc:
        if moved_old:
            try:
                if root.exists():
                    _remove_owned(root)
                backup.rename(root)
            except OSError as recovery_exc:
                fail(
                    "write_recovery_failed",
                    f"package rollbackに失敗しました: {recovery_exc}",
                )
        if isinstance(exc, PackageError):
            raise
        fail("write_commit_failed", f"package directory commitに失敗しました: {exc}")
    if backup.exists():
        try:
            _remove_owned(backup)
        except OSError as exc:
            fail(
                "write_commit_failed",
                f"committed package後のbackup cleanupに失敗しました: {exc}",
            )


def _create_files_from_assets() -> tuple[
    dict[str, str], dict[tuple[str, str], list[dict[str, str]]]
]:
    files: dict[str, str] = {}
    try:
        asset_paths = sorted(ASSET_ROOT.glob("*.md"))
        for path in asset_paths:
            if path.name == "MANIFEST.md":
                continue
            files[path.name] = _decode_current(path.read_bytes(), path.name)
    except OSError as exc:
        fail("file_unreadable", f"Skill-local package assetを読めません: {exc}")
    missing = set(CORE_FILES) - set(files)
    if missing:
        fail(
            "package_schema_mismatch",
            f"package assetが不足しています: {sorted(missing)}",
        )
    tables = _parse_all_tables(files)
    return files, tables


MATERIALIZE_FIELDS = {
    "operation",
    "package_root",
    "artifact_mode",
    "previous_snapshot",
    "change_mode",
    "legacy_source_version",
    "migration_retained_ids",
    "legacy_lifecycle_events",
    "change_summary",
    "retire_ids",
    "table_changes",
    "keyed_table_updates",
    "prose_updates",
    "extension_file_updates",
    "extension_file_retirements",
}


def _validate_materialize_request(request: dict[str, Any]) -> None:
    if set(request) != MATERIALIZE_FIELDS:
        fail(
            "invalid_input",
            f"materialize request field集合が不一致です: {sorted(set(request) ^ MATERIALIZE_FIELDS)}",
        )
    if request["artifact_mode"] not in {"create", "update"} or request[
        "change_mode"
    ] not in {"normal", "legacy-migration"}:
        fail("invalid_input", "artifact_mode / change_modeが不正です")
    if not isinstance(request["change_summary"], str):
        fail("invalid_input", "change_summaryはstringである必要があります")
    for field in (
        "migration_retained_ids",
        "legacy_lifecycle_events",
        "retire_ids",
        "table_changes",
        "keyed_table_updates",
        "prose_updates",
        "extension_file_updates",
        "extension_file_retirements",
    ):
        if not isinstance(request[field], list):
            fail("invalid_input", f"{field}はarrayである必要があります")
    if request["artifact_mode"] == "update" and request["change_mode"] != "normal":
        fail("invalid_input", "legacy-migrationはartifact_mode=createだけ許可されます")
    if request["change_mode"] == "normal":
        if (
            request["legacy_source_version"] is not None
            or request["migration_retained_ids"]
            or request["legacy_lifecycle_events"]
        ):
            fail(
                "invalid_input",
                "normal change modeにlegacy migration fieldは指定できません",
            )
    else:
        source = request["legacy_source_version"]
        if source != "legacy-unversioned" and (
            not isinstance(source, str) or not re.fullmatch(r"v[0-9]{2,}", source)
        ):
            fail(
                "invalid_input",
                "legacy_source_versionはvNNまたはlegacy-unversionedです",
            )
        if (
            request["previous_snapshot"] is not None
            or request["retire_ids"]
            or request["extension_file_retirements"]
        ):
            fail(
                "invalid_input",
                "legacy migrationではsnapshot / retire inputを使いません",
            )
    if (
        request["artifact_mode"] == "create"
        and request["change_mode"] == "normal"
        and request["previous_snapshot"] is not None
    ):
        fail("invalid_input", "normal createのprevious_snapshotはnullです")
    if request["artifact_mode"] == "update" and request["previous_snapshot"] is None:
        fail("invalid_input", "normal updateにはprevious_snapshotが必要です")


def _empty_or_missing_root(root: Path) -> bool:
    if not root.exists():
        return True
    _check_no_symlink(root)
    if not root.is_dir():
        return False
    try:
        return not any(root.iterdir())
    except OSError as exc:
        fail("file_unreadable", f"create targetを読めません: {exc}")


def _model_from_memory(
    root: Path,
    files: dict[str, str],
    tables: dict[tuple[str, str], list[dict[str, str]]],
) -> PackageModel:
    by_id, authorities = _table_index(tables)
    payload_paths = _ordered_payloads(tables, set(files) | {"MANIFEST.md"})
    return PackageModel(
        root, files, {}, tables, {}, {}, [], {}, payload_paths, by_id, authorities
    )


def _next_version(current: str) -> str:
    return f"v{int(current[1:]) + 1:02d}"


def _changed_file_names(
    files: dict[str, str], payload_paths: list[str], previous: PackageModel | None
) -> list[str]:
    if previous is None:
        paths = set(payload_paths) | {"MANIFEST.md"}
    else:
        all_paths = set(previous.raw_files) | set(payload_paths) | {"MANIFEST.md"}
        paths = set()
        for path in all_paths:
            if path == "MANIFEST.md":
                paths.add(path)
            elif (
                path not in files
                or path not in previous.raw_files
                or canonical_bytes(files[path]) != previous.raw_files[path]
            ):
                paths.add(path)
    order = {path: index for index, path in enumerate(CANONICAL_ORDER)}
    return sorted(
        paths,
        key=lambda path: (
            path == "MANIFEST.md",
            order.get(path, 100),
            int(path.split("_", 1)[0]) if path[:1].isdigit() else 0,
            path,
        ),
    )


def _materialize_locked(
    request: dict[str, Any], root: Path, fingerprint: str, current: PackageModel | None
) -> dict[str, Any]:
    artifact_mode = request["artifact_mode"]
    change_mode = request["change_mode"]
    if (
        current is not None
        and current.receipt.get("request_fingerprint") == fingerprint
    ):
        progress = _scope_progress(current, check_closure=True)
        return _materialize_response(
            current.receipt, fingerprint, progress, replayed=True
        )
    if artifact_mode == "update":
        if current is None:
            fail(
                "package_schema_mismatch",
                "update対象に有効なui-target-v1 packageがありません",
            )
        _validate_snapshot(current, request["previous_snapshot"])
    else:
        if not _empty_or_missing_root(root):
            fail(
                "invalid_input",
                "create targetは不存在または空directoryである必要があります",
            )

    retained_ids, legacy_events = (
        _migration_inputs(request) if change_mode == "legacy-migration" else (set(), [])
    )
    reserved_ids = retained_ids | {row["stable_id"] for row in legacy_events}
    if current is None:
        files, tables = _create_files_from_assets()
    else:
        files = dict(current.files)
        tables = {
            key: [dict(row) for row in values] for key, values in current.tables.items()
        }
    draft_map, _ = _apply_table_changes(
        files, tables, request, current, change_mode, retained_ids, reserved_ids
    )
    _apply_keyed_updates(files, tables, request, current, draft_map, change_mode)
    files, allocated_extensions, retired_extensions = _apply_extensions(
        files, tables, request, draft_map, current
    )
    _apply_prose_updates(files, request)
    retired_ids = _apply_retirements(tables, request["retire_ids"], current)
    _materialize_conditional_files(files, tables, current, retired_ids)
    _validate_previous_model_transition(
        current, tables, retired_ids, change_mode, retained_ids
    )
    _materialize_table_text(files, tables)
    provisional = _model_from_memory(root, files, tables)
    _validate_semantics(provisional)
    machine = _build_machine_entities(provisional)
    files["09_authority_and_traceability.md"] = _replace_machine_section(
        files["09_authority_and_traceability.md"], machine["machine_entities_markdown"]
    )

    summary = normalize_text(request["change_summary"])
    if artifact_mode == "update" and current is not None:
        semantic_changed = _semantic_files(files) != _semantic_files(current.files)
        summary_changed = summary != _latest_change_summary(
            current.files["CHANGELOG.md"]
        )
        if not semantic_changed and not summary_changed:
            progress = _scope_progress(provisional, check_closure=True)
            unchanged = {
                "changed": False,
                "allocated_ids": [],
                "allocated_extension_files": [],
                "retired_ids": [],
                "retired_extension_files": [],
                "changed_files": [],
                "previous_package_version": current.metadata["Package Version"],
                "package_version": current.metadata["Package Version"],
            }
            return _materialize_response(
                unchanged, fingerprint, progress, replayed=False
            )

    if artifact_mode == "create" and change_mode == "normal":
        version, previous_version = "v00", "-"
    elif change_mode == "legacy-migration":
        source = request["legacy_source_version"]
        if source == "legacy-unversioned":
            version, previous_version = "v00", "legacy-unversioned"
        else:
            version, previous_version = _next_version(source), source
    else:
        assert current is not None
        previous_version = current.metadata["Package Version"]
        version = _next_version(previous_version)

    events = _apply_lifecycle_events(
        tables, current, retired_ids, change_mode, retained_ids, legacy_events
    )
    impact = _impact_files(events, current, tables)
    files["CHANGELOG.md"] = _replace_latest_changelog(
        files["CHANGELOG.md"], version, summary, events, impact
    )
    progress = _scope_progress(provisional, check_closure=True)
    current_unknown_count = len(_unknown_rows(provisional))
    provisional_payload_paths = _ordered_payloads(tables, set(files) | {"MANIFEST.md"})
    _make_readme(
        files,
        version,
        previous_version,
        progress,
        provisional_payload_paths,
        current_unknown_count,
    )
    # README controls and Machine Entities are generated before hashing.
    payload_paths = _ordered_payloads(tables, set(files) | {"MANIFEST.md"})
    changed_files = _changed_file_names(files, payload_paths, current)
    allocated_ids = [
        {"draft_key": key, "stable_id": value} for key, value in draft_map.items()
    ]
    allocated_ids.sort(key=lambda row: row["draft_key"])
    allocated_extensions = sorted(
        allocated_extensions, key=lambda row: row["draft_key"]
    )
    retired_ids = sorted(retired_ids, key=_id_sort)
    retired_extensions = sorted(
        retired_extensions, key=lambda value: int(value.split("_", 1)[0])
    )
    receipt = {
        "receipt_version": RECEIPT_VERSION,
        "request_fingerprint": fingerprint,
        "artifact_mode": artifact_mode,
        "change_mode": change_mode,
        "changed": True,
        "allocated_ids": allocated_ids,
        "allocated_extension_files": allocated_extensions,
        "retired_ids": retired_ids,
        "retired_extension_files": retired_extensions,
        "changed_files": changed_files,
        "previous_package_version": previous_version,
        "package_version": version,
    }
    parent = root.parent
    staging = parent / f".{root.name}.ui-target-staging"
    backup = parent / f".{root.name}.ui-target-backup"
    _write_staging(
        staging, files, payload_paths, version, previous_version, progress, receipt
    )
    _read_package(staging)
    if current is not None:
        fresh_current = _read_package(root)
        _validate_snapshot(fresh_current, request["previous_snapshot"])
    elif root.exists() and any(root.iterdir()):
        fail("stale_snapshot", "create targetがstaging検証中に変更されました")
    _commit_package(root, staging, backup, had_root=current is not None)
    committed = _read_package(root)
    return _materialize_response(
        committed.receipt,
        fingerprint,
        _scope_progress(committed, check_closure=True),
        replayed=False,
    )


def _execute_operation(request: Any) -> dict[str, Any]:
    if not isinstance(request, dict):
        fail("invalid_input", "top-level JSONはobjectである必要があります")
    operation = request.get("operation")
    if operation not in {
        "inspect",
        "validate",
        "materialize",
        "build-machine-evidence",
    }:
        fail("invalid_input", f"unknown operationです: {operation!r}")
    allowed = {
        "inspect": {"operation", "package_root"},
        "validate": {"operation", "package_root", "previous_snapshot"},
        "materialize": MATERIALIZE_FIELDS,
        "build-machine-evidence": {"operation", "package_root", "scope_ids"},
    }[operation]
    if set(request) - set(allowed):
        fail(
            "invalid_input",
            f"unknown top-level fieldです: {sorted(set(request) - set(allowed))}",
        )
    if operation == "materialize":
        _validate_materialize_request(request)
        normalized = canonicalize(_normalize_materialize_request(request))
        fingerprint = "sha256:" + _sha(canonical_json_bytes(normalized))
    else:
        fingerprint = ""
    root = _resolve_root(request.get("package_root"))
    with _package_lock(root):
        preflight_model = _preflight_recovery(root)
        if operation == "materialize":
            current: PackageModel | None = preflight_model
            if (
                current is None
                and root.exists()
                and root.is_dir()
                and any(root.iterdir())
            ):
                try:
                    current = _read_package(root)
                except PackageError:
                    if request["artifact_mode"] == "update":
                        raise
            return {
                "valid": True,
                "status": "ok",
                "operation": operation,
                "payload": _materialize_locked(request, root, fingerprint, current),
                "issues": [],
            }
        model = preflight_model or _read_package(root)
        if operation == "inspect":
            payload = _inspect_payload(model)
        elif operation == "validate":
            snapshot = request.get("previous_snapshot")
            if snapshot is not None:
                _validate_snapshot(model, snapshot)
            payload = _inspect_payload(model)
        else:
            payload = build_machine_evidence(model, request.get("scope_ids"))
        encoded = canonical_json_bytes(payload)
        if len(encoded) > MAX_IO_BYTES:
            fail("limit_exceeded", "helper stdout payloadが16 MiBを超えています")
        return {
            "valid": True,
            "status": "ok",
            "operation": operation,
            "payload": payload,
            "issues": [],
        }


def main() -> int:
    raw = sys.stdin.buffer.read(MAX_IO_BYTES + 1)
    operation = "unknown"
    try:
        if len(raw) > MAX_IO_BYTES:
            raise PackageError("limit_exceeded", "helper stdinが16 MiBを超えています")
        request = strict_loads(raw, aggregate=True)
        if isinstance(request, dict) and isinstance(request.get("operation"), str):
            operation = request["operation"]
        result = _execute_operation(request)
        output = canonical_json_bytes(result) + b"\n"
        if len(output) > MAX_IO_BYTES:
            raise PackageError("limit_exceeded", "helper stdoutが16 MiBを超えています")
        sys.stdout.buffer.write(output)
        return 0
    except RuntimeErrorBase as exc:
        issue_type = (
            exc.issue_type
            if exc.issue_type
            in {
                "invalid_input",
                "limit_exceeded",
                "package_schema_mismatch",
                "path_outside_package",
                "symlink_not_allowed",
                "file_unreadable",
                "reference_not_found",
                "duplicate_id",
                "id_space_exhausted",
                "manifest_mismatch",
                "stale_snapshot",
                "state_transition_required",
                "write_locked",
                "write_lock_unavailable",
                "write_commit_failed",
                "write_recovery_failed",
            }
            else "invalid_input"
        )
        result = {
            "valid": False,
            "status": "blocked",
            "operation": operation,
            "payload": {},
            "issues": [
                {"issue_type": issue_type, "blocking": True, "message": exc.message}
            ],
        }
        sys.stdout.buffer.write(canonical_json_bytes(result) + b"\n")
        return 0
    except Exception:
        result = {
            "valid": False,
            "status": "blocked",
            "operation": operation,
            "payload": {},
            "issues": [
                {
                    "issue_type": "invalid_input",
                    "blocking": True,
                    "message": "unexpected internal error",
                }
            ],
        }
        sys.stdout.buffer.write(canonical_json_bytes(result) + b"\n")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
