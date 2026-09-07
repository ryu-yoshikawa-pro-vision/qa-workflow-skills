from __future__ import annotations

import re

from scripts.skills.evals.deterministic.common import ID_PATTERNS, PRIORITIES, RISK_LEVEL_ORDER, add_allowed_assertion, add_duplicate_assertion, add_required_fields_assertion, clean, ids_in, nonempty_rows
from scripts.skills.evals.deterministic.markdown_parser import find_table, parse_tables
from scripts.skills.evals.deterministic.result import EvalResult

DISPOSITIONS = {"別テストレベル", "残存リスク", "対象外", "ブロック中"}
VAGUE_TERMS = ("正常", "正しく", "問題ない", "適切")
DEPENDENCY_TERMS = ("実行後", "前ケース", "上記ケース", "前のケース")


def _numbered_authority_mappings(value: str) -> dict[str, set[str]]:
    markers = list(re.finditer(r"(?:期待結果|根拠)\s*(\d+)\s*[→:：]", value or ""))
    mappings: dict[str, set[str]] = {}
    for index, marker in enumerate(markers):
        end = markers[index + 1].start() if index + 1 < len(markers) else len(value)
        mappings[marker.group(1)] = set(ids_in(value[marker.end():end]))
    return mappings


def validate(text: str, expected: dict, eval_id: str) -> EvalResult:
    result = EvalResult("test-case-design", eval_id)
    tables = parse_tables(text)
    case_table = find_table(tables, section_contains="テストケース一覧", required_headers=("テストケースID", "期待結果", "期待結果の根拠"))
    disp_table = find_table(tables, section_contains="テストケースへ展開しないカバレッジ項目 / テスト条件", required_headers=("上流ID", "扱い"))
    missing_tables = [label for label, table in (("テストケース一覧", case_table), ("テストケースへ展開しないカバレッジ項目 / テスト条件", disp_table)) if table is None]
    result.add("TC-D012", not missing_tables, "テストケース設計の正規テーブルが存在すること", evidence=missing_tables or None)

    cases = nonempty_rows(case_table)
    disposed = nonempty_rows(disp_table)
    ids = [clean(r.get("テストケースID", "")) for r in cases]
    bad = [v for v in ids if not ID_PATTERNS["TC"].fullmatch(v)]
    result.add("TC-D001", not bad, "テストケースIDがTC-xxx形式であること", evidence=bad or None)
    add_duplicate_assertion(result, "TC-D002", ids, "テストケースID")
    add_allowed_assertion(result, "TC-D003", (r.get("優先度", "") for r in cases), PRIORITIES, "テストケース優先度")
    add_required_fields_assertion(result, "TC-D004", cases, ("タイトル / 目的", "関連観点ID", "関連テスト要求ID", "優先度", "前提条件", "テストデータ", "実施手順", "期待結果", "期待結果の根拠"), "テストケースID", "詳細テストケース")

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
        for field, known, specified in (("関連観点ID", known_tcn, tcn_spec), ("関連カバレッジ項目ID", known_ci, ci_spec), ("関連テスト要求ID", known_tr, tr_spec)):
            for ref in ids_in(row.get(field, "")):
                if specified and ref not in known:
                    unknown.append({"tc": tcid, "field": field, "reference": ref})
        roots = ids_in(row.get("期待結果の根拠", ""))
        if not roots:
            missing_auth.append(tcid)
        for ref in roots:
            if auth_spec and ref not in known_auth:
                unknown.append({"tc": tcid, "field": "期待結果の根拠", "reference": ref})
    result.add("TC-D005", not unknown, "上流成果物と仕様根拠の参照が存在すること", evidence=unknown or None)
    result.add("TC-D006", not missing_auth, "各テストケースのPASS / FAIL期待結果が1件以上の仕様根拠へ対応すること", evidence=missing_auth or None)

    disposed_ids = {clean(r.get("上流ID", "")) for r in disposed}
    disposition_known = set()
    if tcn_spec:
        disposition_known |= known_tcn
    if ci_spec:
        disposition_known |= known_ci
    unknown_disposed = sorted({upstream for upstream in disposed_ids if upstream and (tcn_spec or ci_spec) and upstream not in disposition_known})
    result.add("TC-D014", not unknown_disposed, "fixtureでテスト条件またはカバレッジ項目を指定した場合、扱い対象の上流IDが存在すること", evidence=unknown_disposed or None)

    linked_ci = {ref for row in cases for ref in ids_in(row.get("関連カバレッジ項目ID", "")) if ref in known_ci}
    embedded_tcn = {ref for row in cases for ref in ids_in(row.get("関連観点ID", "")) if ref in known_tcn}
    linked_upstream = linked_ci | embedded_tcn
    if "coverage_closure_ids" in expected:
        universe = set(expected["coverage_closure_ids"])
    elif ci_spec:
        universe = known_ci
    else:
        universe = set()
    missing_closure = sorted(universe - linked_upstream - disposed_ids)
    duplicate_closure = sorted(linked_upstream & disposed_ids)
    closure_evidence = {"missing": missing_closure, "linked_and_disposed": duplicate_closure} if missing_closure or duplicate_closure else None
    result.add("TC-D007", not missing_closure and not duplicate_closure, "カバレッジ項目 / テスト条件がテストケースまたは扱いのどちらか一方へ閉じること", evidence=closure_evidence)

    add_allowed_assertion(result, "TC-D008", (r.get("扱い", "") for r in disposed), DISPOSITIONS, "扱い")
    no_reason = [clean(r.get("上流ID", "")) for r in disposed if not clean(r.get("理由 / 根拠", ""))]
    result.add("TC-D009", not no_reason, "扱いに理由 / 根拠があること", evidence=no_reason or None)

    ci_priorities = expected.get("coverage_item_priorities", {})
    issues = []
    for row in cases:
        linked = [ref for ref in ids_in(row.get("関連カバレッジ項目ID", "")) if ref in ci_priorities]
        if linked:
            high = max((ci_priorities[r] for r in linked), key=lambda x: RISK_LEVEL_ORDER.get(x, 0))
            actual = clean(row.get("優先度", ""))
            if RISK_LEVEL_ORDER.get(actual, 0) < RISK_LEVEL_ORDER.get(high, 0) and not clean(row.get("備考", "")):
                issues.append({"tc": row.get("テストケースID"), "expected_at_least": high, "actual": actual})
    result.add("TC-D010", not issues, "統合したテストケースが、説明された上書きがない限り最高のカバレッジ項目優先度を維持すること", evidence=issues or None)

    numbered_issues = []
    case_by_id = {clean(r.get("テストケースID", "")): r for r in cases}
    for row in cases:
        tcid = clean(row.get("テストケースID", ""))
        expectation_numbers = set(re.findall(r"期待結果\s*(\d+)", row.get("期待結果", "")))
        root_numbers = set(_numbered_authority_mappings(row.get("期待結果の根拠", "")))
        if len(expectation_numbers) > 1 and not expectation_numbers.issubset(root_numbers):
            numbered_issues.append({"tc": tcid, "reason": "missing numbered Authority mapping"})

    for tcid, expected_mapping in expected.get("expected_numbered_authorities", {}).items():
        row = case_by_id.get(tcid)
        if row is None:
            numbered_issues.append({"tc": tcid, "reason": "missing Test Case"})
            continue
        expectation_numbers = set(re.findall(r"期待結果\s*(\d+)", row.get("期待結果", "")))
        actual_mapping = _numbered_authority_mappings(row.get("期待結果の根拠", ""))
        for number, expected_ids in expected_mapping.items():
            number = str(number)
            if number not in expectation_numbers:
                numbered_issues.append({"tc": tcid, "number": number, "reason": "missing expectation number"})
                continue
            actual_ids = actual_mapping.get(number)
            expected_ids_set = set(expected_ids)
            if actual_ids is None:
                numbered_issues.append({"tc": tcid, "number": number, "reason": "missing Authority mapping"})
            elif actual_ids != expected_ids_set:
                numbered_issues.append({"tc": tcid, "number": number, "expected": sorted(expected_ids_set), "actual": sorted(actual_ids)})
    result.add("TC-D011", not numbered_issues, "番号付きPASS / FAIL期待結果が対応する番号付き仕様根拠を持ち、fixture指定時はその対応と一致すること", evidence=numbered_issues or None)

    vague, deps = [], []
    for row in cases:
        if any(t in row.get("期待結果", "") for t in VAGUE_TERMS):
            vague.append(clean(row.get("テストケースID", "")))
        full = " ".join(row.values())
        if any(t in full for t in DEPENDENCY_TERMS) or re.search(r"\bTC-\d{3}\s*実行後", full):
            deps.append(clean(row.get("テストケースID", "")))
    result.add("TC-W001", not vague, "期待結果が観測可能な結果ではなく曖昧表現を使用している可能性がある", severity="warning", evidence=vague or None)
    result.add("TC-W002", not deps, "テストケースが別ケースに依存している可能性がある", severity="warning", evidence=deps or None)

    required_missing = []
    if "required_test_cases" in expected:
        required_missing = sorted(set(expected["required_test_cases"]) - set(ids))
    result.add("TC-D013", not required_missing, "fixtureで必須のテストケースが存在すること", evidence=required_missing or None)
    return result
