"""Stable DEC / ASM identity lifecycle for Project Context owner artifacts."""

from __future__ import annotations

import json
import re
import sys
from typing import Any

MAX_INPUT_BYTES = 16 * 1024 * 1024
DEC_HEADING = "## 12. 確定事項（決定事項の正本一覧）"
ASM_HEADING = "## 13. 仮定（仮定の正本一覧）"
DEC_HEADERS = [
    "ID",
    "確定内容",
    "状態",
    "決定根拠",
    "影響範囲",
    "関係",
    "関連仕様根拠ID",
    "置換先ID",
    "備考",
]
ASM_HEADERS = [
    "ID",
    "仮定",
    "状態",
    "理由 / 根拠",
    "承認根拠",
    "影響範囲",
    "置換先ID",
    "備考",
]
DEC_CELLS = DEC_HEADERS[1:]
ASM_CELLS = ASM_HEADERS[1:]
ID_PATTERNS = {"DEC": re.compile(r"^DEC-(\d{3})$"), "ASM": re.compile(r"^ASM-(\d{3})$")}


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


def _exact(value: Any, keys: set[str], name: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise ContractError("invalid_input", f"{name} schema mismatch")
    return value


def _section(text: str, heading: str) -> tuple[list[str], int, int]:
    lines = text.splitlines()
    indexes = [index for index, line in enumerate(lines) if line.strip() == heading]
    if len(indexes) != 1:
        raise ContractError("invalid_input", f"{heading} must occur exactly once")
    start = indexes[0]
    end = next(
        (
            index
            for index in range(start + 1, len(lines))
            if lines[index].startswith("## ")
        ),
        len(lines),
    )
    return lines, start, end


def _split_row(line: str) -> list[str]:
    value = line.strip()
    if not value.startswith("|") or not value.endswith("|"):
        raise ContractError("invalid_input", "malformed Markdown table row")
    cells: list[str] = []
    cell: list[str] = []
    escaped = False
    for char in value[1:-1]:
        if char == "|" and not escaped:
            cells.append("".join(cell).strip())
            cell = []
        else:
            cell.append(char)
        if char == "\\" and not escaped:
            escaped = True
        else:
            escaped = False
    cells.append("".join(cell).strip())
    return cells


def _table_rows(markdown: str, heading: str, headers: list[str]) -> list[list[str]]:
    lines, start, end = _section(markdown, heading)
    index = next((i for i in range(start + 1, end) if lines[i].startswith("|")), None)
    if index is None or index + 1 >= end or _split_row(lines[index]) != headers:
        raise ContractError("invalid_input", f"{heading} table header is invalid")
    separators = _split_row(lines[index + 1])
    if len(separators) != len(headers) or not all(
        re.fullmatch(r":?-{3,}:?", row) for row in separators
    ):
        raise ContractError("invalid_input", f"{heading} table separator is invalid")
    rows = []
    for line in lines[index + 2 : end]:
        if line.startswith("|"):
            row = _split_row(line)
            if len(row) != len(headers):
                raise ContractError(
                    "invalid_input", f"{heading} table row width is invalid"
                )
            rows.append(row)
    return rows


def _ids(markdown: str, kind: str) -> list[str]:
    heading, headers = (
        (DEC_HEADING, DEC_HEADERS) if kind == "DEC" else (ASM_HEADING, ASM_HEADERS)
    )
    values = [row[0] for row in _table_rows(markdown, heading, headers)]
    pattern = ID_PATTERNS[kind]
    if any(not pattern.fullmatch(value) for value in values) or len(values) != len(
        set(values)
    ):
        raise ContractError(
            "invalid_input", f"{kind} identity is malformed or duplicated"
        )
    return values


def validate_history(request: dict[str, Any]) -> dict[str, Any]:
    _exact(
        request,
        {"operation", "previous_artifact_markdown", "artifact_markdown"},
        "validate-history request",
    )
    previous, candidate = (
        request["previous_artifact_markdown"],
        request["artifact_markdown"],
    )
    if (
        previous is not None
        and not isinstance(previous, str)
        or not isinstance(candidate, str)
    ):
        raise ContractError("invalid_input", "artifact Markdown must be string or null")
    previous_dec = set(_ids(previous, "DEC")) if previous is not None else set()
    previous_asm = set(_ids(previous, "ASM")) if previous is not None else set()
    decisions = _ids(candidate, "DEC")
    assumptions = _ids(candidate, "ASM")
    missing = sorted(
        (previous_dec - set(decisions)) | (previous_asm - set(assumptions))
    )
    return {
        "missing_previous_ids": missing,
        "decision_ids": sorted(decisions),
        "assumption_ids": sorted(assumptions),
    }


def _value(value: Any, name: str) -> str:
    if isinstance(value, list):
        if not all(isinstance(row, str) for row in value):
            raise ContractError("invalid_input", f"{name} must contain strings")
        return "<br>".join(value)
    if not isinstance(value, str):
        raise ContractError("invalid_input", f"{name} must be string or string list")
    return value


def _escape(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace("|", "\\|")
        .replace("\r\n", "<br>")
        .replace("\n", "<br>")
        .replace("\r", "<br>")
    )


def _table(headers: list[str], rows: list[list[str]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    lines.extend(
        "| " + " | ".join(_escape(value) for value in row) + " |" for row in rows
    )
    return "\n".join(lines)


def _replace(markdown: str, heading: str, body: str) -> str:
    lines, start, end = _section(markdown, heading)
    return (
        "\n".join(
            lines[: start + 1] + ["", *body.splitlines(), ""] + lines[end:]
        ).rstrip()
        + "\n"
    )


def _allocate_rows(
    kind: str,
    request_rows: Any,
    existing_ids: set[str],
    headers: list[str],
    cells_headers: list[str],
) -> tuple[list[list[str]], list[dict[str, str]], set[str]]:
    if not isinstance(request_rows, list):
        raise ContractError("invalid_input", f"{kind.lower()}s must be an array")
    pattern = ID_PATTERNS[kind]
    used = set(existing_ids)
    seen_ids: set[str] = set()
    seen_drafts: set[str] = set()
    allocated: list[dict[str, str]] = []
    new_rows: list[tuple[str, dict[str, Any]]] = []
    result_rows: list[tuple[str, dict[str, Any]]] = []
    for index, raw in enumerate(request_rows):
        row = _exact(
            raw,
            {"draft_key", "identity_action", "reuse_id", "cells"},
            f"{kind.lower()}s[{index}]",
        )
        cells = row["cells"]
        if not isinstance(cells, dict) or set(cells) != set(cells_headers):
            raise ContractError(
                "invalid_input", f"{kind.lower()}s[{index}].cells schema mismatch"
            )
        if row["identity_action"] == "reuse":
            identity = row["reuse_id"]
            if (
                not isinstance(identity, str)
                or not pattern.fullmatch(identity)
                or identity not in used
            ):
                raise ContractError("invalid_input", f"{kind} reuse ID is not tracked")
            if row["draft_key"] is not None:
                raise ContractError("invalid_input", "reuse draft_key must be null")
        elif row["identity_action"] == "new":
            draft = row["draft_key"]
            if (
                not isinstance(draft, str)
                or not draft.strip()
                or draft in seen_drafts
                or row["reuse_id"] is not None
            ):
                raise ContractError("invalid_input", "new draft identity is invalid")
            seen_drafts.add(draft)
            new_rows.append((draft, cells))
            continue
        else:
            raise ContractError("invalid_input", "identity_action must be reuse or new")
        if identity in seen_ids:
            raise ContractError("invalid_input", f"{kind} identity is duplicated")
        seen_ids.add(identity)
        result_rows.append((identity, cells))

    for identity in sorted(existing_ids):
        if identity not in seen_ids and not any(
            row["identity_action"] == "reuse" and row["reuse_id"] == identity
            for row in request_rows
        ):
            raise ContractError(
                "invalid_input", f"previous {kind} ID cannot be removed"
            )

    next_number = (
        max(
            (
                int(match.group(1))
                for value in used
                if (match := pattern.fullmatch(value))
            ),
            default=0,
        )
        + 1
    )
    if next_number + len(new_rows) - 1 > 999:
        raise ContractError("id_space_exhausted", f"{kind} ID range is exhausted")
    for draft, cells in new_rows:
        identity = f"{kind}-{next_number:03d}"
        next_number += 1
        used.add(identity)
        allocated.append({"draft_key": draft, "stable_id": identity})
        result_rows.append((identity, cells))

    output = []
    for identity, cells in sorted(result_rows, key=lambda row: row[0]):
        output.append(
            [identity, *[_value(cells[name], name) for name in cells_headers]]
        )
    return output, allocated, used


def materialize(request: dict[str, Any]) -> dict[str, Any]:
    _exact(
        request,
        {
            "operation",
            "artifact_mode",
            "previous_artifact_markdown",
            "artifact_markdown",
            "decisions",
            "assumptions",
        },
        "materialize request",
    )
    mode = request["artifact_mode"]
    previous, candidate = (
        request["previous_artifact_markdown"],
        request["artifact_markdown"],
    )
    if mode not in {"create", "update"} or not isinstance(candidate, str):
        raise ContractError("invalid_input", "artifact mode or candidate is invalid")
    if (mode == "create" and previous is not None) or (
        mode == "update" and not isinstance(previous, str)
    ):
        raise ContractError(
            "invalid_input", "previous artifact does not match artifact_mode"
        )
    previous_dec = set(_ids(previous, "DEC")) if previous is not None else set()
    previous_asm = set(_ids(previous, "ASM")) if previous is not None else set()
    candidate_dec = set(_ids(candidate, "DEC"))
    candidate_asm = set(_ids(candidate, "ASM"))
    dec_rows, dec_allocated, dec_used = _allocate_rows(
        "DEC",
        request["decisions"],
        previous_dec | candidate_dec,
        DEC_HEADERS,
        DEC_CELLS,
    )
    asm_rows, asm_allocated, asm_used = _allocate_rows(
        "ASM",
        request["assumptions"],
        previous_asm | candidate_asm,
        ASM_HEADERS,
        ASM_CELLS,
    )
    output = _replace(candidate, DEC_HEADING, _table(DEC_HEADERS, dec_rows))
    output = _replace(output, ASM_HEADING, _table(ASM_HEADERS, asm_rows))
    history = validate_history(
        {
            "operation": "validate-history",
            "previous_artifact_markdown": previous,
            "artifact_markdown": output,
        }
    )
    if history["missing_previous_ids"]:
        raise ContractError("invalid_input", "previous DEC / ASM IDs cannot be removed")
    return {
        "allocated_ids": dec_allocated + asm_allocated,
        "artifact_markdown": output,
        "decision_ids": history["decision_ids"],
        "assumption_ids": history["assumption_ids"],
    }


def handle(request: Any) -> dict[str, Any]:
    try:
        if not isinstance(request, dict) or request.get("operation") not in {
            "materialize",
            "validate-history",
        }:
            raise ContractError("invalid_input", "unknown operation")
        payload = (
            materialize(request)
            if request["operation"] == "materialize"
            else validate_history(request)
        )
        valid = (
            not payload.get("missing_previous_ids")
            if request["operation"] == "validate-history"
            else True
        )
        issues = (
            []
            if valid
            else [
                {
                    "issue_type": "history_missing",
                    "blocking": True,
                    "missing_previous_ids": payload["missing_previous_ids"],
                }
            ]
        )
        return {"valid": valid, "payload": payload, "issues": issues}
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
        request = _loads(raw)
        result = handle(request)
        return_code = 0
    except ContractError as exc:
        result = {
            "valid": False,
            "payload": None,
            "issues": [
                {"issue_type": exc.issue_type, "blocking": True, "message": exc.message}
            ],
        }
        return_code = 0
    except Exception as exc:  # pragma: no cover
        result = {
            "valid": False,
            "payload": None,
            "issues": [
                {"issue_type": "internal_error", "blocking": True, "message": str(exc)}
            ],
        }
        return_code = 1
    sys.stdout.buffer.write(
        json.dumps(
            result, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        + b"\n"
    )
    return return_code


if __name__ == "__main__":
    raise SystemExit(main())
