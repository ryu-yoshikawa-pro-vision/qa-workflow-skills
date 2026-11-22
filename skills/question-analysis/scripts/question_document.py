#!/usr/bin/env python3
"""Validate and persist one question-analysis document (kind `question-analysis`).

The Markdown body is the canonical artifact. `validate` is read-only and checks the shape
the output template defines: the required headings, the 15-column question table, the
question and UNKNOWN identifiers, the question ID history and the source revision. It does
not judge meaning (whether a classification is right, or whether a question is really
needed); that remains the Skill's own self-check.

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
# question_ids or project-context. The constants below are mirrored, and the tests fix them
# equal to question_ids.py and artifact_store.py. StoreError is a ValueError subclass.
MAX_BYTES = 16 * 1024 * 1024
KIND = "question-analysis"
REASON_PREFIX = "question_document_invalid:"

# Headings the output template (assets/output-template.md) requires, each exactly once.
# Other headings (for example 作業メモ) are allowed; their order is not checked.
SECTIONS = (
    "概要",
    "不明点 / 質問一覧",
    "質問ID履歴",
    "仮定候補",
    "ブロック中範囲",
)
QUESTION_HEADING = "不明点 / 質問一覧"
HISTORY_HEADING = "質問ID履歴"

# Table headers of the template (the 15-column question table is question_ids.QUESTION_HEADERS).
QUESTION_HEADERS = (
    "ID",
    "問題 / 質問",
    "根拠",
    "分類",
    "影響範囲 / 成果物",
    "関連UNKNOWN ID",
    "Runtime Skill",
    "Runtime Unit Key",
    "Model Key",
    "Target Key",
    "Generation Fingerprint",
    "回答なしの場合の扱い",
    "回答後の正規化先",
    "再開Skill",
    "再開対象 / 実行範囲",
)
TABLE_HEADERS = {
    "不明点 / 質問一覧": QUESTION_HEADERS,
    "質問ID履歴": ("ID",),
    "仮定候補": ("仮定候補", "状態", "根拠 / 理由", "影響範囲", "正式ASM ID"),
    "ブロック中範囲": (
        "ブロッカーID",
        "ブロック中成果物 / 範囲",
        "必要な決定 / 情報源",
        "Runtime Skill",
        "Runtime Unit Key",
        "Model Key",
        "Target Key",
        "Generation Fingerprint",
        "再開Skill",
        "再開対象 / 実行範囲",
    ),
}

# Column index of the cells that the validator reads in the question table.
QUESTION_COLUMNS = {
    "id": 0,
    "question": 1,
    "basis": 2,
    "classification": 3,
    "impact": 4,
    "unknown": 5,
    "unanswered": 11,
}
CLASSIFICATIONS = frozenset({"ブロッカー", "要確認", "仮定可能", "提案・任意"})
UNKNOWN_SEPARATOR = "<br>"

SCOPE = re.compile(r"[a-z0-9][a-z0-9-]{0,63}\Z")
Q_ID = re.compile(r"Q-[0-9]{3}\Z")
UNK_ID = re.compile(r"UNK-[0-9]{3}\Z")
# Test-side identifiers must not appear in a question document (test design is downstream).
DOWNSTREAM_ID = re.compile(r"(?<![A-Za-z0-9])(?:TR|TC|TCN|CI|COND|ITEM)-[A-Za-z0-9]+")
SEPARATOR_CELL = re.compile(r":?-{3,}:?\Z")


def artifact_ref_for(scope_id: Any) -> str | None:
    """The only artifact_ref a scope may use: question-analysis/<scope-id>.md."""
    if not isinstance(scope_id, str) or not SCOPE.fullmatch(scope_id):
        return None
    return f"question-analysis/{scope_id}.md"


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
    """Split one Markdown table row. An escaped pipe (\\|) stays inside its cell."""
    body = line.strip()
    if body.startswith("|"):
        body = body[1:]
    if body.endswith("|") and not body.endswith("\\|"):
        body = body[:-1]
    cells: list[str] = []
    current: list[str] = []
    escaped = False
    for char in body:
        if char == "|" and not escaped:
            cells.append("".join(current).strip())
            current = []
        else:
            current.append(char)
        escaped = char == "\\" and not escaped
    cells.append("".join(current).strip())
    return [cell.replace("\\|", "|") for cell in cells]


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

    # The required headings, each exactly once.
    for heading in SECTIONS:
        count = found.count(heading)
        if count == 0:
            codes.append(f"section_missing:{heading}")
        elif count > 1:
            codes.append(f"section_duplicate:{heading}")

    # The scope identifier and the source revision.
    if not isinstance(scope_id, str) or not SCOPE.fullmatch(scope_id):
        codes.append("scope_id_invalid")
    if (
        not isinstance(source_revision, str)
        or not source_revision
        or source_revision not in markdown
    ):
        codes.append("source_revision_not_in_document")

    # Table headers, separators and row widths for every template table.
    tables: dict[str, dict[str, Any]] = {}
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

    question_ids, question_codes = _check_questions(tables.get(QUESTION_HEADING))
    codes.extend(question_codes)
    history_ids, history_codes = _check_history(tables.get(HISTORY_HEADING))
    codes.extend(history_codes)
    # Every current question must have been allocated in the ID history.
    for identifier in sorted(question_ids - history_ids):
        codes.append(f"history_missing_question:{identifier}")

    # No test-side identifiers anywhere in the document.
    for token in dict.fromkeys(DOWNSTREAM_ID.findall(markdown)):
        codes.append(f"forbidden_downstream_id:{token}")

    metrics = {
        "bytes": len(raw),
        "sections": len(dict.fromkeys(found)),
        "questions": len(question_ids),
        "history": len(history_ids),
    }
    return _result(list(dict.fromkeys(codes)), metrics)


def _check_questions(table: dict[str, Any] | None) -> tuple[set[str], list[str]]:
    codes: list[str] = []
    ids: set[str] = set()
    if table is None:
        return ids, codes
    seen: set[str] = set()
    for row in table["rows"]:
        identifier = row[QUESTION_COLUMNS["id"]]
        if not Q_ID.fullmatch(identifier):
            codes.append(f"question_id_invalid:{identifier}")
            continue
        if identifier in seen:
            codes.append(f"question_id_duplicate:{identifier}")
            continue
        seen.add(identifier)
        ids.add(identifier)
        if not row[QUESTION_COLUMNS["question"]]:
            codes.append(f"question_text_missing:{identifier}")
        if row[QUESTION_COLUMNS["classification"]] not in CLASSIFICATIONS:
            codes.append(f"classification_invalid:{identifier}")
        if not row[QUESTION_COLUMNS["basis"]]:
            codes.append(f"basis_missing:{identifier}")
        if not row[QUESTION_COLUMNS["impact"]]:
            codes.append(f"impact_missing:{identifier}")
        if not row[QUESTION_COLUMNS["unanswered"]]:
            codes.append(f"unanswered_handling_missing:{identifier}")
        refs = row[QUESTION_COLUMNS["unknown"]]
        tokens = refs.split(UNKNOWN_SEPARATOR) if refs else []
        for token in tokens:
            if not UNK_ID.fullmatch(token):
                codes.append(f"unknown_ref_invalid:{identifier}:{token}")
        for token in dict.fromkeys(tokens):
            if tokens.count(token) > 1:
                codes.append(f"unknown_ref_duplicate:{identifier}:{token}")
    return ids, codes


def _check_history(table: dict[str, Any] | None) -> tuple[set[str], list[str]]:
    codes: list[str] = []
    if table is None:
        return set(), codes
    values: list[str] = []
    for row in table["rows"]:
        identifier = row[0]
        if not Q_ID.fullmatch(identifier):
            codes.append(f"history_id_invalid:{identifier}")
            continue
        values.append(identifier)
    if values != sorted(set(values)):
        codes.append("history_order_invalid")
    return set(values), codes


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
        return {"status": "blocked", "reasons": ["question_scope_mismatch"]}
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
        prog="question_document.py",
        description="Validate a question-analysis Markdown document (read-only). Output is JSON.",
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
