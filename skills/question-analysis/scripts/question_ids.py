"""Deterministic Q ID allocation and UNKNOWN link validation."""

from __future__ import annotations

import json
import re
import sys
from typing import Any

MAX_INPUT_BYTES = 16 * 1024 * 1024
Q_ID_RE = re.compile(r"^Q-(\d{3})$")
UNK_ID_RE = re.compile(r"^UNK-\d{3}$")
QUESTION_HEADING = "## 不明点 / 質問一覧"
HISTORY_HEADING = "## 質問ID履歴"
QUESTION_HEADERS = [
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
]
CELL_HEADERS = QUESTION_HEADERS[1:5] + QUESTION_HEADERS[5:]


class ContractError(ValueError):
    def __init__(self, issue_type: str, message: str) -> None:
        super().__init__(message)
        self.issue_type = issue_type
        self.message = message


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ContractError("invalid_input", "duplicate JSON object key")
        result[key] = value
    return result


def _loads(raw: bytes) -> Any:
    if len(raw) > MAX_INPUT_BYTES:
        raise ContractError("limit_exceeded", "stdin exceeds 16 MiB")
    try:
        return json.loads(raw.decode("utf-8", "strict"), object_pairs_hook=_pairs)
    except ContractError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as exc:
        raise ContractError("invalid_input", "invalid JSON input") from exc


def _exact_keys(value: Any, required: set[str], name: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != required:
        raise ContractError("invalid_input", f"{name} schema mismatch")
    return value


def _id_list(value: Any, pattern: re.Pattern[str], name: str) -> list[str]:
    if (
        not isinstance(value, list)
        or not all(isinstance(row, str) and pattern.fullmatch(row) for row in value)
        or value != sorted(set(value))
    ):
        raise ContractError("invalid_input", f"{name} must be unique sorted IDs")
    return value


def _section_bounds(text: str, heading: str) -> tuple[int, int, list[str]]:
    lines = text.splitlines()
    starts = [index for index, line in enumerate(lines) if line.strip() == heading]
    if len(starts) != 1:
        raise ContractError("invalid_input", f"{heading} must occur exactly once")
    start = starts[0]
    end = next(
        (
            index
            for index in range(start + 1, len(lines))
            if lines[index].startswith("## ")
        ),
        len(lines),
    )
    return start, end, lines


def _split_table_row(line: str) -> list[str]:
    value = line.strip()
    if not value.startswith("|") or not value.endswith("|"):
        raise ContractError("invalid_input", "malformed Markdown table row")
    cells: list[str] = []
    current: list[str] = []
    escaped = False
    for char in value[1:-1]:
        if char == "|" and not escaped:
            cells.append("".join(current).strip())
            current = []
        else:
            current.append(char)
        if char == "\\" and not escaped:
            escaped = True
        else:
            escaped = False
    cells.append("".join(current).strip())
    return cells


def _table_rows(
    lines: list[str], start: int, end: int, headers: list[str]
) -> list[list[str]]:
    table_at = next(
        (index for index in range(start + 1, end) if lines[index].startswith("|")), None
    )
    if table_at is None or table_at + 1 >= end:
        raise ContractError("invalid_input", "required Markdown table is missing")
    if _split_table_row(lines[table_at]) != headers:
        raise ContractError("invalid_input", "Markdown table header mismatch")
    separator = _split_table_row(lines[table_at + 1])
    if len(separator) != len(headers) or not all(
        re.fullmatch(r":?-{3,}:?", cell) for cell in separator
    ):
        raise ContractError("invalid_input", "Markdown table separator is invalid")
    rows = []
    for line in lines[table_at + 2 : end]:
        if not line.startswith("|"):
            continue
        cells = _split_table_row(line)
        if len(cells) != len(headers):
            raise ContractError("invalid_input", "Markdown table row width mismatch")
        rows.append(cells)
    return rows


def _parse_question_rows(markdown: str) -> list[dict[str, Any]]:
    _start, end, lines = _section_bounds(markdown, QUESTION_HEADING)
    start, _, _ = _section_bounds(markdown, QUESTION_HEADING)
    rows = _table_rows(lines, start, end, QUESTION_HEADERS)
    result = []
    seen = set()
    for row in rows:
        question_id = row[0]
        if not Q_ID_RE.fullmatch(question_id):
            raise ContractError("invalid_input", "question ID format is invalid")
        if question_id in seen:
            raise ContractError("invalid_input", "duplicate question ID")
        seen.add(question_id)
        raw_refs = row[5]
        refs = [] if not raw_refs else raw_refs.split("<br>")
        if not all(ref and UNK_ID_RE.fullmatch(ref) for ref in refs):
            raise ContractError("invalid_input", "related UNKNOWN ID format is invalid")
        if len(refs) != len(set(refs)):
            raise ContractError(
                "invalid_input", "duplicate UNKNOWN link in one question"
            )
        result.append({"question_id": question_id, "unknown_ids": refs})
    return result


def _parse_history(markdown: str) -> list[str]:
    start, end, lines = _section_bounds(markdown, HISTORY_HEADING)
    rows = _table_rows(lines, start, end, ["ID"])
    values = []
    for row in rows:
        value = row[0]
        if not Q_ID_RE.fullmatch(value):
            raise ContractError(
                "invalid_input", "question history ID format is invalid"
            )
        values.append(value)
    if values != sorted(set(values)):
        raise ContractError(
            "invalid_input", "question history must be sorted and unique"
        )
    return values


def _validate_links(
    markdown: str, current_unknown_ids: list[str], resolved_unknown_ids: list[str]
) -> dict[str, Any]:
    current = set(current_unknown_ids)
    resolved = set(resolved_unknown_ids)
    links = _parse_question_rows(markdown)
    for row in links:
        for ref in row["unknown_ids"]:
            if ref in resolved and ref not in current:
                raise ContractError("resolved_only_unknown", f"{ref} is resolved-only")
            if ref not in current:
                raise ContractError(
                    "unknown_reference", f"{ref} is not a current UNKNOWN"
                )
    return {
        "question_links": links,
        "unknown_refs": sorted({ref for row in links for ref in row["unknown_ids"]}),
    }


def validate_links(request: dict[str, Any]) -> dict[str, Any]:
    _exact_keys(
        request,
        {
            "operation",
            "artifact_markdown",
            "current_unknown_ids",
            "resolved_unknown_ids",
        },
        "validate-links request",
    )
    markdown = request["artifact_markdown"]
    if not isinstance(markdown, str):
        raise ContractError("invalid_input", "artifact_markdown must be a string")
    current = _id_list(request["current_unknown_ids"], UNK_ID_RE, "current_unknown_ids")
    resolved = _id_list(
        request["resolved_unknown_ids"], UNK_ID_RE, "resolved_unknown_ids"
    )
    if set(current) & set(resolved):
        raise ContractError(
            "invalid_input", "current and resolved UNKNOWN sets overlap"
        )
    return _validate_links(markdown, current, resolved)


def _cell_value(value: Any, name: str) -> str:
    if isinstance(value, list):
        if not all(isinstance(row, str) for row in value):
            raise ContractError("invalid_input", f"{name} must contain strings")
        return "<br>".join(value)
    if not isinstance(value, str):
        raise ContractError("invalid_input", f"{name} must be a string or string list")
    return value


def _escape_cell(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace("|", "\\|")
        .replace("\r\n", "<br>")
        .replace("\n", "<br>")
        .replace("\r", "<br>")
    )


def _table(headers: list[str], rows: list[list[str]]) -> str:
    rendered = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    rendered.extend(
        "| " + " | ".join(_escape_cell(value) for value in row) + " |" for row in rows
    )
    return "\n".join(rendered)


def _replace_section(markdown: str, heading: str, body: str) -> str:
    start, end, lines = _section_bounds(markdown, heading)
    replaced = lines[: start + 1] + ["", *body.splitlines(), ""] + lines[end:]
    return "\n".join(replaced).rstrip() + "\n"


def _question_history_ids(markdown: str, *, required: bool) -> list[str]:
    if HISTORY_HEADING not in markdown.splitlines():
        if required:
            raise ContractError("invalid_input", "question ID history is missing")
        return []
    try:
        return _parse_history(markdown)
    except ContractError:
        raise


def materialize(request: dict[str, Any]) -> dict[str, Any]:
    required = {
        "operation",
        "artifact_mode",
        "previous_artifact_markdown",
        "artifact_markdown",
        "current_unknown_ids",
        "resolved_unknown_ids",
        "questions",
    }
    _exact_keys(request, required, "materialize request")
    mode = request["artifact_mode"]
    previous = request["previous_artifact_markdown"]
    candidate = request["artifact_markdown"]
    if mode not in {"create", "update"}:
        raise ContractError("invalid_input", "artifact_mode must be create or update")
    if not isinstance(candidate, str) or (
        previous is not None and not isinstance(previous, str)
    ):
        raise ContractError("invalid_input", "artifact Markdown must be a string")
    if (mode == "create" and previous is not None) or (
        mode == "update" and previous is None
    ):
        raise ContractError(
            "invalid_input", "previous artifact does not match artifact_mode"
        )
    current = _id_list(request["current_unknown_ids"], UNK_ID_RE, "current_unknown_ids")
    resolved = _id_list(
        request["resolved_unknown_ids"], UNK_ID_RE, "resolved_unknown_ids"
    )
    if set(current) & set(resolved):
        raise ContractError(
            "invalid_input", "current and resolved UNKNOWN sets overlap"
        )
    questions = request["questions"]
    if not isinstance(questions, list):
        raise ContractError("invalid_input", "questions must be an array")

    previous_current = _parse_question_rows(previous) if previous is not None else []
    previous_ids = {row["question_id"] for row in previous_current}
    used = set(previous_ids)
    if previous is not None:
        used.update(_question_history_ids(previous, required=False))
    used.update(row["question_id"] for row in _parse_question_rows(candidate))
    used.update(_question_history_ids(candidate, required=False))

    current_rows: list[tuple[str, list[str]]] = []
    allocated: list[dict[str, str]] = []
    seen_ids: set[str] = set()
    seen_drafts: set[str] = set()
    new_rows: list[tuple[str, dict[str, Any]]] = []
    for index, raw in enumerate(questions):
        row = _exact_keys(
            raw,
            {"draft_key", "identity_action", "reuse_id", "cells"},
            f"questions[{index}]",
        )
        action = row["identity_action"]
        cells = row["cells"]
        if not isinstance(cells, dict) or set(cells) != set(CELL_HEADERS):
            raise ContractError(
                "invalid_input", f"questions[{index}].cells schema mismatch"
            )
        if action == "reuse":
            question_id = row["reuse_id"]
            if (
                not isinstance(question_id, str)
                or not Q_ID_RE.fullmatch(question_id)
                or question_id not in previous_ids
            ):
                raise ContractError(
                    "invalid_input",
                    "reuse_id must identify a previous current question",
                )
            if row["draft_key"] is not None:
                raise ContractError("invalid_input", "reuse row draft_key must be null")
        elif action == "new":
            draft_key = row["draft_key"]
            if (
                not isinstance(draft_key, str)
                or not draft_key.strip()
                or draft_key in seen_drafts
                or row["reuse_id"] is not None
            ):
                raise ContractError(
                    "invalid_input", "new question identity fields are invalid"
                )
            seen_drafts.add(draft_key)
            new_rows.append((draft_key, cells))
            continue
        else:
            raise ContractError("invalid_input", "identity_action must be reuse or new")
        if question_id in seen_ids:
            raise ContractError("invalid_input", "question identity is duplicated")
        seen_ids.add(question_id)
        current_rows.append((question_id, cells))

    next_number = (
        max(
            (
                int(match.group(1))
                for value in used
                if (match := Q_ID_RE.fullmatch(value))
            ),
            default=0,
        )
        + 1
    )
    if next_number + len(new_rows) - 1 > 999:
        raise ContractError("id_space_exhausted", "Q ID range is exhausted")
    for draft_key, cells in new_rows:
        question_id = f"Q-{next_number:03d}"
        next_number += 1
        seen_ids.add(question_id)
        current_rows.append((question_id, cells))
        allocated.append({"draft_key": draft_key, "question_id": question_id})

    current_rows.sort(key=lambda row: row[0])
    markdown_rows = []
    for question_id, cells in current_rows:
        values = [_cell_value(cells[header], header) for header in CELL_HEADERS]
        refs = values[CELL_HEADERS.index("関連UNKNOWN ID")]
        if refs:
            refs = "<br>".join(sorted(ref.strip() for ref in refs.split("<br>")))
        values[CELL_HEADERS.index("関連UNKNOWN ID")] = refs
        markdown_rows.append([question_id, *values])
    output = _replace_section(
        candidate, QUESTION_HEADING, _table(QUESTION_HEADERS, markdown_rows)
    )
    history = sorted(used | seen_ids)
    history_body = _table(["ID"], [[value] for value in history])
    if HISTORY_HEADING in output.splitlines():
        output = _replace_section(output, HISTORY_HEADING, history_body)
    else:
        output = (
            output.rstrip() + "\n\n" + HISTORY_HEADING + "\n\n" + history_body + "\n"
        )
    _validate_links(output, current, resolved)
    return {
        "allocated_ids": allocated,
        "artifact_markdown": output,
        "used_question_ids": history,
    }


def handle(request: Any) -> dict[str, Any]:
    try:
        if not isinstance(request, dict) or request.get("operation") not in {
            "materialize",
            "validate-links",
        }:
            raise ContractError("invalid_input", "unknown operation")
        payload = (
            materialize(request)
            if request["operation"] == "materialize"
            else validate_links(request)
        )
        return {"valid": True, "payload": payload, "issues": []}
    except ContractError as exc:
        return {
            "valid": False,
            "payload": None,
            "issues": [
                {"issue_type": exc.issue_type, "blocking": True, "message": exc.message}
            ],
        }


def main() -> int:
    raw = sys.stdin.buffer.read(MAX_INPUT_BYTES + 1)
    try:
        response = handle(_loads(raw))
        exit_code = 0
    except ContractError as exc:
        response = {
            "valid": False,
            "payload": None,
            "issues": [
                {"issue_type": exc.issue_type, "blocking": True, "message": exc.message}
            ],
        }
        exit_code = 0
    except Exception as exc:  # pragma: no cover - defensive CLI boundary
        response = {
            "valid": False,
            "payload": None,
            "issues": [
                {"issue_type": "internal_error", "blocking": True, "message": str(exc)}
            ],
        }
        exit_code = 1
    encoded = (
        json.dumps(
            response, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        + b"\n"
    )
    sys.stdout.buffer.write(encoded)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
