from __future__ import annotations

import re

from ..common import ID_PATTERNS, PRIORITIES, RISK_LEVEL_ORDER, add_allowed_assertion, add_duplicate_assertion, clean, ids_in, nonempty_rows
from ..markdown_parser import find_table, parse_tables
from ..result import EvalResult

DISPOSITIONS = {"別テストレベル", "残存リスク", "対象外", "Blocked"}
VAGUE_TERMS = ("正常", "正しく", "問題ない", "適切")
DEPENDENCY_TERMS = ("実行後", "前ケース", "上記ケース", "前のケース")


def validate(text: str, expected: dict, eval_id: str) -> EvalResult:
    result = EvalResult("test-case-design", eval_id)
    tables = parse_tables(text)
    case_table = find_table(tables, section_contains="テストケース一覧", required_headers=("テストケースID", "期待結果", "期待結果の根拠"))
    disp_table = find_table(tables, section_contains="Test Caseへ展開しないCoverage Item / Test Condition", required_headers=("上流ID", "Disposition"))
    missing_tables = [label for label, table in (("テストケース一覧", case_table), ("Test Caseへ展開しないCoverage Item / Test Condition", disp_table)) if table is None]
    result.add("TC-D012", not missing_tables, "Canonical test-case-design tables must exist", evidence=missing_tables or None)

    cases = nonempty_rows(case_table)
    disposed = nonempty_rows(disp_table)
    ids = [clean(r.get("テストケースID", "")) for r in cases]
    bad = [v for v in ids if not ID_PATTERNS["TC"].fullmatch(v)]
    result.add("TC-D001", not bad, "Test Case IDs must use TC-xxx", evidence=bad or None)
    add_duplicate_assertion(result, "TC-D002", ids, "Test Case IDs")
    add_allowed_assertion(result, "TC-D003", (r.get("優先度", "") for r in cases), PRIORITIES, "Test Case priority")

    required = ("タイトル / 目的", "関連観点ID", "関連テスト要求ID", "優先度", "前提条件", "テストデータ", "実施手順", "期待結果", "期待結果の根拠")
    missing = []
    for row in cases:
        for f in required:
            if not clean(row.get(f, "")):
                missing.append({"tc": row.get("テストケースID"), "field": f})
    result.add("TC-D004", not missing, "Low-Level Test Case required fields must exist", evidence=missing or None)

    tcn_spec = "known_test_conditions" in expected
    ci_spec = "known_coverage_items" in expected
    tr_spec = "known_test_requirements" in expected
    auth_spec = "known_authorities" in expected
    known_tcn = set(expected.get("known_test_conditions", []))
    known_ci = set(expected.get("known_coverage_items", []))
    known_tr = set(expected.get("known_test_requirements", []))
    known_auth = set(expected.get("known_authorities", []))
    unknown, missing_auth = [], []
    for row in cases:
        tcid = clean(row.get("テストケースID", ""))
        for field, known, specified in (
            ("関連観点ID", known_tcn, tcn_spec),
            ("関連Coverage Item ID", known_ci, ci_spec),
            ("関連テスト要求ID", known_tr, tr_spec),
        ):
            for ref in ids_in(row.get(field, "")):
                if specified and ref not in known:
                    unknown.append({"tc": tcid, "field": field, "reference": ref})
        roots = ids_in(row.get("期待結果の根拠", ""))
        if not roots:
            missing_auth.append(tcid)
        for ref in roots:
            if auth_spec and ref not in known_auth:
                unknown.append({"tc": tcid, "field": "期待結果の根拠", "reference": ref})
    result.add("TC-D005", not unknown, "Upstream and Authority references must exist", evidence=unknown or None)
    result.add("TC-D006", not missing_auth, "Every Test Case must map PASS/FAIL expectations to at least one Authority", evidence=missing_auth or None)

    disposed_ids = {clean(r.get("上流ID", "")) for r in disposed}
    linked_ci = {ref for row in cases for ref in ids_in(row.get("関連Coverage Item ID", "")) if ref in known_ci}
    embedded_tcn = {ref for row in cases for ref in ids_in(row.get("関連観点ID", "")) if ref in known_tcn}
    if "coverage_closure_ids" in expected:
        universe = set(expected["coverage_closure_ids"])
    elif ci_spec:
        universe = known_ci
    else:
        universe = set()
    missing_closure = sorted(universe - linked_ci - embedded_tcn - disposed_ids)
    result.add("TC-D007", not missing_closure, "Coverage Item/Test Condition must close to Test Case or Disposition", evidence=missing_closure or None)

    add_allowed_assertion(result, "TC-D008", (r.get("Disposition", "") for r in disposed), DISPOSITIONS, "Disposition")
    no_reason = [clean(r.get("上流ID", "")) for r in disposed if not clean(r.get("理由 / 根拠", ""))]
    result.add("TC-D009", not no_reason, "Disposition requires reason/evidence", evidence=no_reason or None)

    ci_priorities = expected.get("coverage_item_priorities", {})
    issues = []
    for row in cases:
        linked = [ref for ref in ids_in(row.get("関連Coverage Item ID", "")) if ref in ci_priorities]
        if linked:
            high = max((ci_priorities[r] for r in linked), key=lambda x: RISK_LEVEL_ORDER.get(x, 0))
            actual = clean(row.get("優先度", ""))
            if RISK_LEVEL_ORDER.get(actual, 0) < RISK_LEVEL_ORDER.get(high, 0) and not clean(row.get("備考", "")):
                issues.append({"tc": row.get("テストケースID"), "expected_at_least": high, "actual": actual})
    result.add("TC-D010", not issues, "Test Case priority must preserve the highest linked Coverage Item priority unless an override reason is provided", evidence=issues or None)

    ambiguous = []
    for row in cases:
        ex = re.findall(r"期待結果\s*(\d+)", row.get("期待結果", ""))
        roots = re.findall(r"(?:期待結果|根拠)\s*(\d+)\s*[→:：]", row.get("期待結果の根拠", ""))
        if len(set(ex)) > 1 and not set(ex).issubset(set(roots)):
            ambiguous.append(clean(row.get("テストケースID", "")))
    result.add("TC-D011", not ambiguous, "Numbered PASS/FAIL expectations should have corresponding numbered Authority mappings", evidence=ambiguous or None)

    vague, deps = [], []
    for row in cases:
        if any(t in row.get("期待結果", "") for t in VAGUE_TERMS):
            vague.append(clean(row.get("テストケースID", "")))
        full = " ".join(row.values())
        if any(t in full for t in DEPENDENCY_TERMS) or re.search(r"\bTC-\d{3}\s*実行後", full):
            deps.append(clean(row.get("テストケースID", "")))
    result.add("TC-W001", not vague, "Expected result may use vague terms instead of observable result", severity="warning", evidence=vague or None)
    result.add("TC-W002", not deps, "Test Case may depend on another case", severity="warning", evidence=deps or None)

    required_missing = []
    if "required_test_cases" in expected:
        required_missing = sorted(set(expected["required_test_cases"]) - set(ids))
    result.add("TC-D013", not required_missing, "Fixture-required Test Cases must be present", evidence=required_missing or None)
    return result
