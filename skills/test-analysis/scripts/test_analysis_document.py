#!/usr/bin/env python3
"""Validate and persist one test-analysis document (kind `test-analysis`).

The Markdown body is the canonical artifact. `validate` is read-only and checks the shape
the output template defines: the required headings, the scope fields, the template tables
(headers, separators and row widths), the risk identifiers and the risk matrix levels, the
reference identifiers, the placement of every risk, the source revision, the machine block
format and the absence of real values (e-mail addresses and local paths). It does not judge
meaning (whether a risk is really high, or whether a technique fits); that remains the
Skill's own self-check and the runtime evidence gate (`runtime_contract.py
verify_runtime_evidence`).

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
# another skill. The constants below are mirrored, and the tests fix them equal to
# artifact_store.py. StoreError is a ValueError subclass.
MAX_BYTES = 16 * 1024 * 1024
KIND = "test-analysis"
REASON_PREFIX = "test_analysis_document_invalid:"

# Headings the output template (assets/output-template.md) requires, each exactly once.
# Other headings are allowed; their order is not checked.
SECTIONS = (
    "テスト分析範囲",
    "変更 / 影響マップ",
    "プロダクトリスク一覧",
    "テスト重点",
    "選択したテスト技法",
    "テスト可能性 / テストレベル判断",
    "残存リスク",
    "Machine Runtime / Entity（機械証拠）",
)
SCOPE_HEADING = "テスト分析範囲"
CHANGE_HEADING = "変更 / 影響マップ"
RISK_HEADING = "プロダクトリスク一覧"
EMPHASIS_HEADING = "テスト重点"
TECHNIQUE_HEADING = "選択したテスト技法"
FEASIBILITY_HEADING = "テスト可能性 / テストレベル判断"
RESIDUAL_HEADING = "残存リスク"
MACHINE_HEADING = "Machine Runtime / Entity（機械証拠）"

# Bullet labels of the scope section. The first group must be non-empty; the second group
# must be present (its value may be empty).
SCOPE_NONEMPTY_LABELS = ("対象機能 / 変更", "テストレベル", "対象外", "ブロッカー")
SCOPE_PRESENT_LABELS = ("案件固有のテスト目的 / 重点", "環境制約", "対象 / 実行範囲")
BLOCKER_LABEL = "ブロッカー"
NO_BLOCKER_VALUES = frozenset({"なし", "-", "ー"})

# Table headers of the template, in the template's column order.
TABLE_HEADERS = {
    CHANGE_HEADING: ("領域", "変更種別", "根拠 / 依存関係", "想定影響"),
    RISK_HEADING: (
        "リスクID",
        "製品上のリスク / 失敗",
        "関連する現在有効な仕様根拠 / 変更 / 依存",
        "影響度",
        "発生可能性",
        "レベル",
        "根拠",
        "判断信頼度 / 備考",
    ),
    EMPHASIS_HEADING: (
        "優先度",
        "重点領域",
        "関連プロダクトリスク / 根拠",
        "設計深度 / 備考",
    ),
    TECHNIQUE_HEADING: (
        "テスト技法",
        "適用領域",
        "選択理由",
        "関連プロダクトリスク / 現在有効な仕様根拠",
        "`test-condition-design`への着眼点",
    ),
    FEASIBILITY_HEADING: (
        "要件 / 懸念",
        "操作可能か",
        "観測可能か",
        "合否判定可能か",
        "選択テストレベル",
        "扱い / 備考",
    ),
    RESIDUAL_HEADING: ("リスク / 要件", "十分にカバーできない理由", "推奨対応"),
}

# Tables that must contain at least one data row.
NONEMPTY_TABLES = (RISK_HEADING, EMPHASIS_HEADING, FEASIBILITY_HEADING)

CHANGE_KINDS = frozenset({"新規", "変更", "削除", "回帰影響", "参考"})
PRIORITIES = frozenset({"高", "中", "低"})
LEVELS = frozenset({"高", "中", "低"})
FEASIBILITY_VALUES = frozenset({"可", "不可", "一部"})
SCORES = frozenset({"1", "2", "3", "4"})

# Standard risk matrix of guidance.md (impact row, likelihood column). A project-specific
# method is not represented here; such a method is outside this validator's scope.
RISK_MATRIX = {
    "4": {"1": "中", "2": "高", "3": "高", "4": "高"},
    "3": {"1": "中", "2": "中", "3": "高", "4": "高"},
    "2": {"1": "低", "2": "中", "3": "中", "4": "高"},
    "1": {"1": "低", "2": "低", "3": "低", "4": "中"},
}

# Column indexes read by the validator.
RISK_COLUMNS = {
    "id": 0,
    "risk": 1,
    "basis": 2,
    "impact": 3,
    "likelihood": 4,
    "level": 5,
    "reason": 6,
}
EMPHASIS_COLUMNS = {"priority": 0, "reference": 2}
TECHNIQUE_COLUMNS = {"reference": 3}
FEASIBILITY_COLUMNS = {
    "operable": 1,
    "observable": 2,
    "judgeable": 3,
    "level": 4,
}

SCOPE = re.compile(r"[a-z0-9][a-z0-9-]{0,63}\Z")
RISK_ID = re.compile(r"RISK-[0-9]{3}\Z")
RISK_TOKEN = re.compile(r"(?<![A-Za-z0-9])RISK-[0-9]{3}(?![A-Za-z0-9])")
# Basis tokens: approved specification, decision and assumption identifiers. UNKNOWN and
# INFERENCE items are never a basis of a product risk or a test technique.
BASIS_TOKEN = re.compile(r"(?<![A-Za-z0-9])(?:SPEC|DEC|ASM)-[0-9]{3}(?![A-Za-z0-9])")
NON_BASIS_TOKEN = re.compile(
    r"(?<![A-Za-z0-9])(?:UNK|INF)-[0-9]{3}(?![A-Za-z0-9])|UNKNOWN|INFERENCE"
)
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
LOCAL_PATH = re.compile(
    r"(?<![A-Za-z0-9])[A-Za-z]:\\|(?<![A-Za-z0-9])/(?:mnt|home|Users|root|var|opt)/"
)
SEPARATOR_CELL = re.compile(r":?-{3,}:?\Z")
MACHINE_HEADER = re.compile(
    r"### (?P<kind>Machine Runtime Input|Machine Runtime Result|Machine Entities): "
    r"(?P<identity>test-analysis(?:::[^\r\n]+)?)\Z"
)


def artifact_ref_for(scope_id: Any) -> str | None:
    """The only artifact_ref a scope may use: test-analysis/<scope-id>.md."""
    if not isinstance(scope_id, str) or not SCOPE.fullmatch(scope_id):
        return None
    return f"test-analysis/{scope_id}.md"


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


def _tables(body: list[str]) -> list[dict[str, Any]]:
    """Markdown tables in a section body: header, separator validity and data rows."""
    tables: list[dict[str, Any]] = []
    block: list[str] = []
    for line, fenced in _fenced_lines(body) + [("", False)]:
        if not fenced and line.strip().startswith("|"):
            block.append(line)
            continue
        if block:
            tables.append(_table(block))
            block = []
    return tables


def _table(block: list[str]) -> dict[str, Any]:
    header = _cells(block[0])
    separator = _cells(block[1]) if len(block) > 1 else []
    separator_ok = len(separator) == len(header) and all(
        SEPARATOR_CELL.fullmatch(cell) for cell in separator
    )
    raw_rows = [_cells(line) for line in block[2:]]
    # Template placeholder rows are blank; they carry no data and are dropped.
    raw_rows = [row for row in raw_rows if any(row)]
    return {
        "header": header,
        "separator_ok": separator_ok,
        "rows": raw_rows,
        "widths_ok": all(len(row) == len(header) for row in raw_rows),
    }


def _result(codes: list[str], metrics: dict[str, Any]) -> dict[str, Any]:
    reasons = [f"{REASON_PREFIX}{code}" for code in codes]
    return {
        "status": "blocked" if reasons else "valid",
        "reasons": reasons,
        "metrics": metrics,
    }


def _scope_fields(body: list[str]) -> dict[str, str]:
    """The `- <label>: <value>` bullets of the scope section (first occurrence wins)."""
    fields: dict[str, str] = {}
    for line, fenced in _fenced_lines(body):
        if fenced or not line.startswith("- "):
            continue
        label, sep, value = line[2:].partition(":")
        if not sep:
            label, sep, value = line[2:].partition("：")
        if not sep:
            continue
        fields.setdefault(label.strip(), value.strip())
    return fields


def _machine_blocks(body: list[str]) -> tuple[list[str], list[str]]:
    """Machine block headers and their JSON fences in the machine section."""
    codes: list[str] = []
    headers: list[str] = []
    lines = _fenced_lines(body)
    index = 0
    while index < len(lines):
        line, fenced = lines[index]
        if fenced or not line.startswith("### Machine "):
            index += 1
            continue
        match = MACHINE_HEADER.fullmatch(line.rstrip())
        if match is None:
            codes.append("machine_block_invalid")
            index += 1
            continue
        headers.append(line.rstrip())
        # The JSON fence follows the header after one blank line.
        cursor = index + 1
        while cursor < len(lines) and lines[cursor][0].strip() == "":
            cursor += 1
        if cursor >= len(lines) or lines[cursor][0].strip() != "```json":
            codes.append("machine_block_json_missing")
            index = cursor
            continue
        payload: list[str] = []
        cursor += 1
        while cursor < len(lines) and lines[cursor][0].strip() != "```":
            payload.append(lines[cursor][0])
            cursor += 1
        try:
            decoded = json.loads("\n".join(payload))
        except ValueError:
            codes.append("machine_block_json_invalid")
        else:
            if not isinstance(decoded, dict):
                codes.append("machine_block_json_invalid")
        index = cursor + 1
    return headers, codes


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

    # Scope fields.
    blocker_declared = False
    if SCOPE_HEADING in bodies:
        fields = _scope_fields(bodies[SCOPE_HEADING])
        for label in SCOPE_NONEMPTY_LABELS:
            if label not in fields:
                codes.append(f"scope_field_missing:{label}")
            elif not fields[label]:
                codes.append(f"scope_field_empty:{label}")
        for label in SCOPE_PRESENT_LABELS:
            if label not in fields:
                codes.append(f"scope_field_missing:{label}")
        blocker_declared = fields.get(BLOCKER_LABEL, "") not in ("", *NO_BLOCKER_VALUES)

    # Template tables: presence, headers, separators, row widths and single occurrence.
    tables: dict[str, dict[str, Any]] = {}
    for heading, header in TABLE_HEADERS.items():
        if heading not in bodies:
            continue
        found_tables = _tables(bodies[heading])
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
        if heading in NONEMPTY_TABLES and not table["rows"]:
            codes.append(f"table_empty:{heading}")
        tables[heading] = table

    risk_ids, risk_codes = _check_risks(tables.get(RISK_HEADING))
    codes.extend(risk_codes)
    codes.extend(_check_change_map(tables.get(CHANGE_HEADING)))
    codes.extend(_check_emphasis(tables.get(EMPHASIS_HEADING)))
    codes.extend(_check_technique(tables.get(TECHNIQUE_HEADING)))
    codes.extend(_check_feasibility(tables.get(FEASIBILITY_HEADING)))

    # Every risk ID cited anywhere outside the risk table must exist, and every risk must be
    # placed in the test emphasis, the technique table or the residual risks (no silent drop).
    placed: set[str] = set()
    for heading in (EMPHASIS_HEADING, TECHNIQUE_HEADING, RESIDUAL_HEADING):
        if heading not in bodies:
            continue
        text = "\n".join(bodies[heading])
        for token in dict.fromkeys(RISK_TOKEN.findall(text)):
            placed.add(token)
            if token not in risk_ids:
                codes.append(f"risk_ref_missing:{token}")
    for identifier in sorted(risk_ids - placed):
        codes.append(f"risk_unplaced:{identifier}")

    # Machine evidence section: the block headers and JSON must be well formed. The runtime
    # gate (verify_runtime_evidence) verifies the content; this only checks the format.
    if MACHINE_HEADING in bodies:
        _, machine_codes = _machine_blocks(bodies[MACHINE_HEADING])
        codes.extend(machine_codes)

    # Real values must not be written into a document.
    if EMAIL.search(markdown):
        codes.append("email_address_present")
    if LOCAL_PATH.search(markdown):
        codes.append("local_path_present")

    metrics = {
        "bytes": len(raw),
        "sections": len(dict.fromkeys(found)),
        "risks": len(risk_ids),
        "blocker_declared": blocker_declared,
    }
    return _result(list(dict.fromkeys(codes)), metrics)


def _check_risks(table: dict[str, Any] | None) -> tuple[set[str], list[str]]:
    codes: list[str] = []
    ids: set[str] = set()
    if table is None:
        return ids, codes
    for row in table["rows"]:
        identifier = row[RISK_COLUMNS["id"]]
        if not RISK_ID.fullmatch(identifier):
            codes.append(f"risk_id_invalid:{identifier}")
            continue
        if identifier in ids:
            codes.append(f"risk_id_duplicate:{identifier}")
            continue
        ids.add(identifier)
        if not row[RISK_COLUMNS["risk"]]:
            codes.append(f"risk_text_missing:{identifier}")
        basis = row[RISK_COLUMNS["basis"]]
        if not basis:
            codes.append(f"risk_basis_missing:{identifier}")
        reason = row[RISK_COLUMNS["reason"]]
        if not reason:
            codes.append(f"risk_reason_missing:{identifier}")
        for text in (basis, reason):
            for token in dict.fromkeys(NON_BASIS_TOKEN.findall(text)):
                codes.append(f"non_basis_reference:{identifier}:{token}")
        impact = row[RISK_COLUMNS["impact"]]
        likelihood = row[RISK_COLUMNS["likelihood"]]
        level = row[RISK_COLUMNS["level"]]
        if impact not in SCORES:
            codes.append(f"risk_impact_invalid:{identifier}")
        if likelihood not in SCORES:
            codes.append(f"risk_likelihood_invalid:{identifier}")
        if level not in LEVELS:
            codes.append(f"risk_level_invalid:{identifier}")
        elif impact in SCORES and likelihood in SCORES:
            expected = RISK_MATRIX[impact][likelihood]
            if level != expected:
                codes.append(f"risk_level_mismatch:{identifier}")
    return ids, codes


def _check_change_map(table: dict[str, Any] | None) -> list[str]:
    codes: list[str] = []
    if table is None:
        return codes
    for index, row in enumerate(table["rows"], start=1):
        if row[1] not in CHANGE_KINDS:
            codes.append(f"change_kind_invalid:{index}")
        if not row[0]:
            codes.append(f"change_area_missing:{index}")
    return codes


def _check_emphasis(table: dict[str, Any] | None) -> list[str]:
    codes: list[str] = []
    if table is None:
        return codes
    for index, row in enumerate(table["rows"], start=1):
        if row[EMPHASIS_COLUMNS["priority"]] not in PRIORITIES:
            codes.append(f"priority_invalid:{index}")
        basis = row[EMPHASIS_COLUMNS["reference"]]
        if not basis:
            codes.append(f"emphasis_basis_missing:{index}")
        for token in dict.fromkeys(NON_BASIS_TOKEN.findall(basis)):
            codes.append(f"non_basis_reference:emphasis-{index}:{token}")
    return codes


def _check_technique(table: dict[str, Any] | None) -> list[str]:
    codes: list[str] = []
    if table is None:
        return codes
    for index, row in enumerate(table["rows"], start=1):
        if not row[0]:
            codes.append(f"technique_missing:{index}")
        basis = row[TECHNIQUE_COLUMNS["reference"]]
        if not basis:
            codes.append(f"technique_basis_missing:{index}")
        for token in dict.fromkeys(NON_BASIS_TOKEN.findall(basis)):
            codes.append(f"non_basis_reference:technique-{index}:{token}")
    return codes


def _check_feasibility(table: dict[str, Any] | None) -> list[str]:
    codes: list[str] = []
    if table is None:
        return codes
    for index, row in enumerate(table["rows"], start=1):
        for name in ("operable", "observable", "judgeable"):
            if row[FEASIBILITY_COLUMNS[name]] not in FEASIBILITY_VALUES:
                codes.append(f"feasibility_invalid:{name}:{index}")
        if not row[FEASIBILITY_COLUMNS["level"]]:
            codes.append(f"test_level_missing:{index}")
    return codes


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
        return {"status": "blocked", "reasons": ["test_scope_mismatch"]}
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
        prog="test_analysis_document.py",
        description="Validate a test-analysis Markdown document (read-only). Output is JSON.",
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
