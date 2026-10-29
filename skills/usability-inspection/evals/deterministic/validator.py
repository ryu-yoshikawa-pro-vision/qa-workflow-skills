from __future__ import annotations

import re

from scripts.skills.evals.deterministic.markdown_parser import find_table, parse_tables
from scripts.skills.evals.deterministic.result import EvalResult

SECTIONS = {
    "Inspection metadata",
    "Scope and closure",
    "Objective observations",
    "Accessibility requirement checks",
    "Supported test rule results",
    "Measurements",
    "Additional observation requests",
    "Summary and limitations",
}


def validate(text: str, expected: dict, eval_id: str) -> EvalResult:
    result = EvalResult("usability-inspection", eval_id)
    headings = set(re.findall(r"^##\s+(.+?)\s*$", text, re.M))
    missing = sorted(SECTIONS - headings)
    result.add(
        "UI-D001",
        not missing,
        "required inspection output sections exist",
        evidence=missing or None,
    )
    required = expected.get("required_tokens", [])
    result.add(
        "UI-D002",
        all(token in text for token in required),
        "fixture-required facts are present",
        evidence=[x for x in required if x not in text] or None,
    )
    forbidden = expected.get("forbidden_tokens", [])
    result.add(
        "UI-D003",
        not any(token.casefold() in text.casefold() for token in forbidden),
        "out-of-scope conformance and human outcome claims are absent",
        evidence=[x for x in forbidden if x.casefold() in text.casefold()] or None,
    )
    status_tokens = {"問題を確認", "問題なし", "判定不能", "対象外"}
    scope_table = find_table(
        parse_tables(text),
        section_contains="Scope and closure",
        required_headers=(
            "Scope ref",
            "Aspect",
            "Decision",
            "Outcome",
            "Reason / applicability",
        ),
    )
    scope_rows = scope_table.rows if scope_table else []
    preinitialization_block = (
        scope_table is not None
        and not scope_rows
        and re.search(
            r"scope initialization[^\n]{0,100}(?:scope skeleton|skeleton)[^\n]{0,100}(?:stopp|停止)|"
            r"scope initialization[^\n]{0,100}stopp[^\n]{0,100}(?:scope skeleton|skeleton)|"
            r"(?:scope skeleton|skeleton)[^\n]{0,100}(?:scope initialization|initialization)[^\n]{0,100}(?:stopp|停止)|"
            r"対象と観点が未確定のため、scope初期化前に停止|"
            r"(?:スコープ|scope)[^\n]*(?:初期化|initialization)[^\n]*(?:scope skeleton|スコープ骨格|scope骨格)[^\n]*(?:前に停止|stopp)|"
            r"スコープ初期化[^\n]*scope skeleton[^\n]*前に停止",
            text,
            re.IGNORECASE,
        )
        is not None
    )
    closed_rows = bool(scope_rows) and all(
        row.get("Outcome", "").strip() in status_tokens
        and (
            row.get("Outcome", "").strip() not in {"判定不能", "対象外"}
            or bool(row.get("Reason / applicability", "").strip())
        )
        for row in scope_rows
    )
    result.add(
        "UI-D004",
        preinitialization_block or closed_rows,
        "scope is explicitly blocked before initialization or every generated row has a closed outcome",
    )
    request_rows = re.findall(r"^\|\s*(OBSREQ-\d{3,})\s*\|([^\n]+)$", text, re.M)
    result.add(
        "UI-D005",
        not any("planned" in row.casefold() for _, row in request_rows),
        "final additional observation requests are closed",
    )
    return result
