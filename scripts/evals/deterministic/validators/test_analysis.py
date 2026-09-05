from __future__ import annotations

from ..common import ID_PATTERNS, add_duplicate_assertion, clean, ids_in, nonempty_rows
from ..markdown_parser import find_table, parse_tables
from ..result import EvalResult

RISK_MATRIX = {
    4: {1: "中", 2: "高", 3: "高", 4: "高"},
    3: {1: "中", 2: "中", 3: "高", 4: "高"},
    2: {1: "低", 2: "中", 3: "中", 4: "高"},
    1: {1: "低", 2: "低", 3: "低", 4: "中"},
}
TESTABILITY = {"可", "不可", "一部"}
TECHNIQUES = {"同値分割", "境界値分析", "デシジョンテーブル", "状態遷移", "Pairwise", "組合せ", "Pairwise / 組合せ", "エラー推測", "シナリオ", "ユースケース", "シナリオ / ユースケース"}


def _int_1_4(value: str) -> int | None:
    try:
        parsed = int(clean(value))
    except ValueError:
        return None
    return parsed if 1 <= parsed <= 4 else None


def validate(text: str, expected: dict, eval_id: str) -> EvalResult:
    result = EvalResult("test-analysis", eval_id)
    tables = parse_tables(text)
    risk_table = find_table(tables, section_contains="Product Risk一覧", required_headers=("リスクID", "影響度", "発生可能性", "レベル"))
    testability_table = find_table(tables, section_contains="テスト可能性", required_headers=("要件 / 懸念", "操作可能か", "観測可能か", "合否判定可能か"))
    technique_table = find_table(tables, section_contains="選択したテスト技法", required_headers=("テスト技法",))
    missing_tables = [label for label, table in (("Product Risk一覧", risk_table), ("選択したテスト技法", technique_table), ("テスト可能性 / テストレベル判断", testability_table)) if table is None]
    result.add("RISK-D010", not missing_tables, "Canonical test-analysis tables must exist", evidence=missing_tables or None)

    risks = nonempty_rows(risk_table)
    testability = nonempty_rows(testability_table)
    techniques = nonempty_rows(technique_table)
    ids = [clean(r.get("リスクID", "")) for r in risks]
    bad = [v for v in ids if not ID_PATTERNS["RISK"].fullmatch(v)]
    result.add("RISK-D001", not bad, "Risk IDs must use RISK-xxx", evidence=bad or None)
    add_duplicate_assertion(result, "RISK-D002", ids, "Risk IDs")

    missing, ranges, matrix = [], [], []
    for row in risks:
        rid = clean(row.get("リスクID", ""))
        req = ["製品上のリスク / 失敗", "関連Current Effective Authority / 変更 / 依存", "影響度", "発生可能性", "レベル", "根拠"]
        absent = [f for f in req if not clean(row.get(f, ""))]
        if absent:
            missing.append({"id": rid, "fields": absent})
        impact = _int_1_4(row.get("影響度", ""))
        likelihood = _int_1_4(row.get("発生可能性", ""))
        if impact is None or likelihood is None:
            ranges.append({"id": rid, "impact": row.get("影響度"), "likelihood": row.get("発生可能性")})
        else:
            exp = RISK_MATRIX[impact][likelihood]
            actual = clean(row.get("レベル", ""))
            if actual != exp:
                matrix.append({"id": rid, "expected": exp, "actual": actual})
    result.add("RISK-D003", not missing, "Risk required fields must be present", evidence=missing or None)
    result.add("RISK-D004", not ranges, "Impact and likelihood must be integers 1..4", evidence=ranges or None)
    result.add("RISK-D005", not matrix, "Risk level must match the canonical 4x4 matrix", evidence=matrix or None)

    unknown = []
    auth_spec = "known_authorities" in expected
    change_spec = "known_changes" in expected
    dep_spec = "known_dependencies" in expected
    known_auth = set(expected.get("known_authorities", []))
    known_changes = set(expected.get("known_changes", []))
    known_deps = set(expected.get("known_dependencies", []))
    for row in risks:
        for ref in ids_in(row.get("関連Current Effective Authority / 変更 / 依存", "")):
            if ref.startswith(("SPEC-", "DEC-", "ASM-")) and auth_spec and ref not in known_auth:
                unknown.append({"risk": row.get("リスクID"), "reference": ref})
            elif ref.startswith("CHG-") and change_spec and ref not in known_changes:
                unknown.append({"risk": row.get("リスクID"), "reference": ref})
            elif ref.startswith("DEP-") and dep_spec and ref not in known_deps:
                unknown.append({"risk": row.get("リスクID"), "reference": ref})
    result.add("RISK-D006", not unknown, "Risk references must exist in fixture data", evidence=unknown or None)

    invalid = []
    for row in testability:
        for f in ("操作可能か", "観測可能か", "合否判定可能か"):
            v = clean(row.get(f, ""))
            if v and v not in TESTABILITY:
                invalid.append({"field": f, "value": v})
    result.add("RISK-D007", not invalid, "Testability values must be allowed", evidence=invalid or None)

    invalid_tech = sorted({clean(r.get("テスト技法", "")) for r in techniques if clean(r.get("テスト技法", "")) and clean(r.get("テスト技法", "")) not in TECHNIQUES})
    result.add("RISK-D008", not invalid_tech, "Selected techniques must use allowed canonical values", evidence=invalid_tech or None)

    terms = ("納期", "予算", "人員", "スケジュール")
    suspicious = [clean(r.get("リスクID", "")) for r in risks if any(t in " ".join(r.values()) for t in terms)]
    result.add("RISK-D009", not suspicious, "Risk rows may contain Project Risk concepts; semantic review required", severity="warning", evidence=suspicious or None)

    required_issues = []
    if "required_risks" in expected:
        by_id = {clean(r.get("リスクID", "")): r for r in risks}
        for rid, spec in expected["required_risks"].items():
            row = by_id.get(rid)
            if row is None:
                required_issues.append({"id": rid, "reason": "missing"})
                continue
            actual = {
                "impact": _int_1_4(row.get("影響度", "")),
                "likelihood": _int_1_4(row.get("発生可能性", "")),
                "risk_level": clean(row.get("レベル", "")),
            }
            expected_values = {
                "impact": spec.get("impact"),
                "likelihood": spec.get("likelihood"),
                "risk_level": spec.get("risk_level"),
            }
            if actual != expected_values:
                required_issues.append({"id": rid, "expected": expected_values, "actual": actual})
    result.add("RISK-D011", not required_issues, "Fixture-required Product Risks must be present with expected matrix values", evidence=required_issues or None)
    return result
