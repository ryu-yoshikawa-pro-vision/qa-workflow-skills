#!/usr/bin/env python3
"""Validate and persist one spec-analysis document (kind `spec-analysis`).

The Markdown body is the canonical artifact. `validate` is read-only and checks the
shape the output template defines: sections, table headers, identifiers, source and
authority references, and the absence of downstream test identifiers. It does not judge
meaning (whether a SPEC is really supported by an authority, or whether an UNKNOWN is
really unresolved); that remains the Skill's own self-check.

`persist_document` validates first, then writes through a store (CAS, idempotency and
independent readback are the store's). The caller registers the user confirmation with
`write_confirmation_record` before calling it. The confirmation is self-declared, not
authentication.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

# This skill's scripts stay self-contained (runtime portability contract): no import from
# project-context. The store is injected, so the limit and the error class are mirrored here.
# StoreError is a ValueError subclass; tests assert MAX_BYTES equals artifact_store.MAX_BYTES.
MAX_BYTES = 16 * 1024 * 1024
KIND = "spec-analysis"
REASON_PREFIX = "spec_document_invalid:"

# Heading texts of the output template (assets/output-template.md), in template order.
SECTIONS = (
    "分析範囲",
    "情報源 / 正本参照一覧",
    "分析項目",
    "現在有効な仕様根拠",
    "業務ルール",
    "状態 / 遷移",
    "処理 / 業務フロー",
    "制約 / 明示的境界",
    "矛盾 / 不明点 / 質問候補",
    "後続Skillへの補足",
    "Machine Entity（機械証拠）",
)

# Table headers of the template, per section. Cells are compared after trimming.
TABLE_HEADERS = {
    "情報源 / 正本参照一覧": (
        "参照ID",
        "情報源 / 正本一覧",
        "権威 / 優先順位",
        "鮮度 / バージョン",
        "対象範囲",
        "参照 / 備考",
    ),
    "分析項目": (
        "項目ID",
        "カテゴリ",
        "内容",
        "分類",
        "情報源 / 正本参照",
        "現在有効か",
        "補足 / 上書き / 置換関係",
        "備考",
    ),
    "現在有効な仕様根拠": (
        "仕様根拠ID",
        "種別",
        "現在有効な内容",
        "適用範囲",
        "情報源 / 正本一覧",
        "関係",
        "関連仕様根拠ID",
    ),
    "業務ルール": ("ルールID / 名称", "関連項目ID", "情報源 / 備考"),
    "状態 / 遷移": (
        "現在状態",
        "イベント / 操作",
        "条件",
        "遷移後状態",
        "関連項目ID",
    ),
    "処理 / 業務フロー": ("手順", "実行者", "操作 / イベント", "結果", "関連項目ID"),
    "制約 / 明示的境界": ("制約", "値 / ルール", "関連項目ID", "情報源"),
    "矛盾 / 不明点 / 質問候補": (
        "項目",
        "根拠",
        "影響範囲",
        "推奨する次の扱い",
    ),
    "後続Skillへの補足": ("項目", "関連項目ID", "後続Skillへの関連 / 備考"),
}

# Column index of the cells that the validator reads.
ITEM_COLUMNS = {
    "id": 0,
    "category": 1,
    "classification": 3,
    "source": 4,
    "currentness": 5,
    "note": 7,
}
AUTHORITY_COLUMNS = {"id": 0, "type": 1, "relation": 5, "related": 6}
ITEM_REFERENCE_COLUMNS = {
    "業務ルール": 1,
    "状態 / 遷移": 4,
    "処理 / 業務フロー": 4,
    "制約 / 明示的境界": 2,
}
SOURCE_COLUMNS = {"id": 0, "revision": 3, "note": 5}

AUTHORITY_TYPES = frozenset({"SPEC", "DECISION", "承認済みASM"})
CLASSIFICATION_PREFIX = {
    "SPEC": "SPEC-",
    "DECISION": "DEC-",
    "INFERENCE": "INF-",
    "UNKNOWN": "UNK-",
}
SOURCE_BACKED = frozenset({"SPEC", "DECISION", "INFERENCE"})

SCOPE = re.compile(r"[a-z0-9][a-z0-9-]{0,63}\Z")
SRC_ID = re.compile(r"SRC-[0-9]{3}\Z")
ITEM_ID = re.compile(r"(?:SPEC|DEC|INF|UNK)-[0-9]{3}\Z")
AUTH_ID = re.compile(r"AUTH-[0-9]{3}\Z")
SRC_TOKEN = re.compile(r"(?<![A-Za-z0-9])SRC-[0-9]{3}(?![A-Za-z0-9])")
AUTH_TOKEN = re.compile(r"(?<![A-Za-z0-9])AUTH-[0-9]{3}(?![A-Za-z0-9])")
ITEM_TOKEN = re.compile(r"(?<![A-Za-z0-9])(?:SPEC|DEC|INF|UNK)-[0-9]{3}(?![A-Za-z0-9])")
REVISION = re.compile(r"rev:\S+")
LOCATOR = re.compile(
    r"file:(?P<path>[^\s:]+):(?P<start>[1-9][0-9]*)(?:-(?P<end>[1-9][0-9]*))?\Z"
)
# Test-side identifiers must not appear in a spec document (test design is downstream).
DOWNSTREAM_ID = re.compile(r"(?<![A-Za-z0-9])(?:TR|TC|TCN|CI|COND|ITEM)-[A-Za-z0-9]+")
SEPARATOR_CELL = re.compile(r":?-+:?\Z")


def artifact_ref_for(scope_id: Any) -> str | None:
    """The only artifact_ref a scope may use: spec-analysis/<scope-id>.md."""
    if not isinstance(scope_id, str) or not SCOPE.fullmatch(scope_id):
        return None
    return f"spec-analysis/{scope_id}.md"


def _fenced_lines(lines: list[str]) -> list[tuple[str, bool]]:
    """Pair each line with whether it lies inside a fenced code block."""
    marked: list[tuple[str, bool]] = []
    fenced = False
    for line in lines:
        if line.lstrip().startswith("```"):
            marked.append((line, True))
            fenced = not fenced
            continue
        marked.append((line, fenced))
    return marked


def _split_sections(markdown: str) -> list[tuple[str, list[str]]]:
    sections: list[tuple[str, list[str]]] = []
    current: list[str] | None = None
    for line, fenced in _fenced_lines(markdown.split("\n")):
        if not fenced and line.startswith("## "):
            current = []
            sections.append((line[3:].strip(), current))
        elif current is not None:
            current.append(line)
    return sections


def _cells(line: str) -> list[str]:
    body = line.strip()
    if body.startswith("|"):
        body = body[1:]
    if body.endswith("|"):
        body = body[:-1]
    return [cell.strip() for cell in body.split("|")]


def _tables(body: list[str], width: int) -> list[dict[str, Any]]:
    """Markdown tables in a section body: header, separator validity and data rows.

    `width` is the template's column count. Rows are padded or cut to it so that column
    reads never fail; a width mismatch is reported separately (table_row_width).
    """
    tables: list[dict[str, Any]] = []
    block: list[str] = []
    for line, fenced in _fenced_lines(body) + [("", False)]:
        if not fenced and line.strip().startswith("|"):
            block.append(line)
            continue
        if block:
            tables.append(_table(block, width))
            block = []
    return tables


def _table(block: list[str], width: int) -> dict[str, Any]:
    header = _cells(block[0])
    separator = _cells(block[1]) if len(block) > 1 else []
    separator_ok = len(separator) == len(header) and all(
        SEPARATOR_CELL.fullmatch(cell) for cell in separator
    )
    raw_rows = [_cells(line) for line in block[2:]]
    raw_rows = [row for row in raw_rows if any(row)]
    rows = [(row + [""] * width)[:width] for row in raw_rows]
    header_width = len(header)
    return {
        "header": header,
        "separator_ok": separator_ok,
        "rows": rows,
        "widths_ok": all(len(row) == header_width for row in raw_rows),
    }


def _result(codes: list[str], metrics: dict[str, int]) -> dict[str, Any]:
    reasons = [f"{REASON_PREFIX}{code}" for code in codes]
    return {
        "status": "blocked" if reasons else "valid",
        "reasons": reasons,
        "metrics": metrics,
    }


def validate(markdown: str, scope_id: str, source_revision: str) -> dict[str, Any]:
    """Check one document. Read-only: no store, no write, no confirmation."""
    try:
        raw = markdown.encode("utf-8")
    except (UnicodeEncodeError, AttributeError):
        return _result(["encoding_invalid"], {})
    if "\x00" in markdown:
        return _result(["encoding_invalid"], {})
    if len(raw) > MAX_BYTES:
        return _result(["too_large"], {})

    codes: list[str] = []
    sections = _split_sections(markdown)
    found = [heading for heading, _ in sections]
    bodies: dict[str, list[str]] = {}
    for heading, body in sections:
        bodies.setdefault(heading, body)

    # V2: the eleven template headings, each once, in template order.
    for heading in SECTIONS:
        count = found.count(heading)
        if count == 0:
            codes.append(f"section_missing:{heading}")
        elif count > 1:
            codes.append(f"section_duplicate:{heading}")
    for heading in dict.fromkeys(found):
        if heading not in SECTIONS:
            codes.append(f"section_unexpected:{heading}")
    first_seen = [h for h in dict.fromkeys(found) if h in SECTIONS]
    if first_seen != [h for h in SECTIONS if h in first_seen]:
        codes.append("section_order_invalid")

    # V14 and scope identifier format are cheap and independent of the sections.
    if not isinstance(scope_id, str) or not SCOPE.fullmatch(scope_id):
        codes.append("scope_id_invalid")
    if (
        not isinstance(source_revision, str)
        or not source_revision
        or source_revision not in markdown
    ):
        codes.append("source_revision_not_in_document")

    # V3: scope fields of the 分析範囲 section.
    if "分析範囲" in bodies:
        scope_lines = [line.strip() for line in bodies["分析範囲"]]
        feature = next(
            (line for line in scope_lines if line.startswith("- 対象機能:")), None
        )
        if feature is None or not feature[len("- 対象機能:") :].strip():
            codes.append("scope_field_missing:対象機能")
        if not any(line.startswith("- 対象外:") for line in scope_lines):
            codes.append("scope_field_missing:対象外")

    # V4: table headers, separators and row widths for every template table.
    tables: dict[str, list[dict[str, Any]]] = {}
    for heading, header in TABLE_HEADERS.items():
        if heading not in bodies:
            continue
        found_tables = _tables(bodies[heading], len(header))
        if not found_tables:
            codes.append(f"table_missing:{heading}")
            continue
        if len(found_tables) > 1:
            codes.append(f"table_unexpected:{heading}")
        table = found_tables[0]
        if tuple(table["header"]) != header or not table["separator_ok"]:
            codes.append(f"table_header_mismatch:{heading}")
        if not table["widths_ok"]:
            codes.append(f"table_row_width:{heading}")
        tables[heading] = table

    src_ids, src_codes = _check_sources(tables.get("情報源 / 正本参照一覧"))
    codes.extend(src_codes)
    item_ids, item_codes = _check_items(tables.get("分析項目"), src_ids)
    codes.extend(item_codes)
    auth_ids, auth_codes = _check_authorities(tables.get("現在有効な仕様根拠"))
    codes.extend(auth_codes)

    # V12: item references in the rule, state, process and constraint tables.
    for heading, column in ITEM_REFERENCE_COLUMNS.items():
        table = tables.get(heading)
        if table is None:
            continue
        for row in table["rows"]:
            if column >= len(row):
                continue
            for token in ITEM_TOKEN.findall(row[column]):
                if token not in item_ids:
                    codes.append(f"item_ref_unknown:{heading}:{token}")

    # V13: no test-side identifiers anywhere in the document.
    for token in dict.fromkeys(DOWNSTREAM_ID.findall(markdown)):
        codes.append(f"forbidden_downstream_id:{token}")

    metrics = {
        "bytes": len(raw),
        "sections": len(dict.fromkeys(found)),
        "sources": len(src_ids),
        "items": len(item_ids),
        "authorities": len(auth_ids),
    }
    return _result(list(dict.fromkeys(codes)), metrics)


def _check_sources(table: dict[str, Any] | None) -> tuple[set[str], list[str]]:
    codes: list[str] = []
    ids: set[str] = set()
    if table is None:
        return ids, codes
    seen: set[str] = set()
    for row in table["rows"]:
        identifier = row[SOURCE_COLUMNS["id"]]
        if not SRC_ID.fullmatch(identifier):
            codes.append(f"src_id_invalid:{identifier}")
        elif identifier in seen:
            codes.append(f"src_id_duplicate:{identifier}")
        else:
            seen.add(identifier)
            ids.add(identifier)
        revision = row[SOURCE_COLUMNS["revision"]]
        if not REVISION.search(revision):
            codes.append(f"src_revision_missing:{identifier}")
        note = row[SOURCE_COLUMNS["note"]]
        if not note:
            codes.append(f"src_note_missing:{identifier}")
        elif note.startswith("file:") and not _valid_locator(note):
            codes.append(f"src_locator_invalid:{identifier}")
    return ids, codes


def _valid_locator(note: str) -> bool:
    match = LOCATOR.fullmatch(note)
    if match is None:
        return False
    path = match.group("path")
    # Repository-relative only: no absolute path, no parent segments, no backslash.
    return not (
        path.startswith("/")
        or "\\" in path
        or any(part in {"", "..", "."} for part in path.split("/"))
    )


def _check_items(
    table: dict[str, Any] | None, src_ids: set[str]
) -> tuple[set[str], list[str]]:
    codes: list[str] = []
    ids: set[str] = set()
    if table is None:
        return ids, codes
    seen: set[str] = set()
    for row in table["rows"]:
        identifier = row[ITEM_COLUMNS["id"]]
        if not ITEM_ID.fullmatch(identifier):
            codes.append(f"item_id_invalid:{identifier}")
            continue
        if identifier in seen:
            codes.append(f"item_id_duplicate:{identifier}")
            continue
        seen.add(identifier)
        ids.add(identifier)
        classification = row[ITEM_COLUMNS["classification"]]
        if classification not in CLASSIFICATION_PREFIX:
            codes.append(f"classification_invalid:{identifier}")
        elif not identifier.startswith(CLASSIFICATION_PREFIX[classification]):
            codes.append(f"classification_id_mismatch:{identifier}")
        if classification in SOURCE_BACKED:
            tokens = SRC_TOKEN.findall(row[ITEM_COLUMNS["source"]])
            if not tokens:
                codes.append(f"source_ref_missing:{identifier}")
            for token in dict.fromkeys(tokens):
                if token not in src_ids:
                    codes.append(f"source_ref_unknown:{identifier}:{token}")
        if classification == "UNKNOWN" and not row[ITEM_COLUMNS["note"]]:
            codes.append(f"unknown_reason_missing:{identifier}")
        if not row[ITEM_COLUMNS["currentness"]]:
            codes.append(f"currentness_missing:{identifier}")
    return ids, codes


def _check_authorities(table: dict[str, Any] | None) -> tuple[set[str], list[str]]:
    codes: list[str] = []
    ids: set[str] = set()
    if table is None:
        return ids, codes
    seen: set[str] = set()
    rows = table["rows"]
    for row in rows:
        identifier = row[AUTHORITY_COLUMNS["id"]]
        if not AUTH_ID.fullmatch(identifier):
            codes.append(f"authority_id_invalid:{identifier}")
        elif identifier in seen:
            codes.append(f"authority_id_duplicate:{identifier}")
        else:
            seen.add(identifier)
            ids.add(identifier)
        if row[AUTHORITY_COLUMNS["type"]] not in AUTHORITY_TYPES:
            codes.append(f"authority_type_invalid:{identifier}")
    for row in rows:
        for token in dict.fromkeys(
            AUTH_TOKEN.findall(row[AUTHORITY_COLUMNS["related"]])
        ):
            if token not in ids:
                codes.append(f"authority_relation_unknown:{row[0]}:{token}")
    return ids, codes


def write_confirmation_record(
    *,
    project_ref: str,
    artifact_ref: str,
    expected_revision: str | None,
    approval_ref: str,
    markdown: str,
    source_ref: str,
    source_revision: str,
    operation_id: str,
    change_reason: str,
) -> dict[str, Any]:
    """The write request that store.write will send, for record_user_confirmation.

    The keys match the store's user-confirmed write authorization exactly.
    """
    digest = hashlib.sha256(markdown.encode("utf-8")).hexdigest()
    return {
        "operation": "write",
        "kind": KIND,
        "project_ref": project_ref,
        "artifact_ref": artifact_ref,
        "expected_revision": expected_revision,
        "sha256": digest,
        "source_ref": source_ref,
        "source_revision": source_revision,
        "approval_ref": approval_ref,
        "approval_revision": "sha256:" + digest,
        "operation_id": operation_id,
        "change_reason": change_reason,
    }


def persist_document(
    store: Any,
    document: dict[str, Any],
    *,
    artifact_ref: str,
    expected_revision: str | None,
    operation_id: str,
    approval_ref: str,
    approval_revision: str,
    change_reason: str,
    source_ref: str,
    source_revision: str,
) -> dict[str, Any]:
    """Validate, then write through the store. Nothing is written when validation fails.

    document = {"project_ref": str, "scope_id": str, "markdown": str}.
    """
    if not isinstance(document, dict):
        return {"status": "blocked", "reasons": ["document_invalid"]}
    project_ref = document.get("project_ref")
    scope_id = document.get("scope_id")
    markdown = document.get("markdown")
    if not isinstance(project_ref, str) or not isinstance(markdown, str):
        return {"status": "blocked", "reasons": ["document_invalid"]}
    report = validate(markdown, scope_id, source_revision)
    if report["status"] != "valid":
        return {"status": "blocked", "reasons": report["reasons"]}
    if artifact_ref != artifact_ref_for(scope_id):
        return {"status": "blocked", "reasons": ["spec_scope_mismatch"]}
    try:
        written = store.write(
            kind=KIND,
            project_ref=project_ref,
            artifact_ref=artifact_ref,
            content=markdown,
            expected_revision=expected_revision,
            operation_id=operation_id,
            source_ref=source_ref,
            source_revision=source_revision,
            approval_ref=approval_ref,
            approval_revision=approval_revision,
            change_reason=change_reason,
        )
    except ValueError as exc:
        # The store's own reason code (StoreError), returned as-is.
        return {"status": "blocked", "reasons": [str(exc)]}
    written["analysis_status"] = "valid"
    written["document_sha256"] = hashlib.sha256(markdown.encode("utf-8")).hexdigest()
    return written


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="spec_document.py",
        description="Validate a spec-analysis Markdown document (read-only). Output is JSON.",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("validate", help="check one document without writing")
    check.add_argument("--document-file", required=True)
    check.add_argument("--scope-id", required=True)
    check.add_argument("--source-revision", required=True)
    args = parser.parse_args(argv)
    try:
        raw = Path(args.document_file).read_bytes()
    except OSError:
        print(
            json.dumps(
                {"status": "blocked", "reasons": [REASON_PREFIX + "unavailable"]}
            )
        )
        return 1
    try:
        markdown = raw.decode("utf-8")
    except UnicodeDecodeError:
        print(
            json.dumps(
                {"status": "blocked", "reasons": [REASON_PREFIX + "encoding_invalid"]}
            )
        )
        return 1
    report = validate(markdown, args.scope_id, args.source_revision)
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0 if report["status"] == "valid" else 1


if __name__ == "__main__":
    raise SystemExit(main())
