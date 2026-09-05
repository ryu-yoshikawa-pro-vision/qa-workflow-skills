from __future__ import annotations

from ..common import ID_PATTERNS, PRIORITIES, RISK_LEVEL_ORDER, add_allowed_assertion, add_duplicate_assertion, clean, ids_in, nonempty_rows
from ..markdown_parser import find_table, parse_tables
from ..result import EvalResult

DISPOSITIONS = {"別テストレベル", "残存リスク", "対象外", "Blocked"}


def validate(text: str, expected: dict, eval_id: str) -> EvalResult:
    result = EvalResult("test-requirement-design", eval_id)
    tables = parse_tables(text)
    tr_table = find_table(tables, section_contains="テスト要求一覧", required_headers=("テスト要求ID", "Current Effective Authority", "優先度"))
    disp_table = find_table(tables, section_contains="Test Requirementを作らない上流項目", required_headers=("上流ID", "Disposition"))
    missing_tables = [label for label, table in (("テスト要求一覧", tr_table), ("Test Requirementを作らない上流項目", disp_table)) if table is None]
    result.add("TR-D011", not missing_tables, "Canonical test-requirement-design tables must exist", evidence=missing_tables or None)

    trs = nonempty_rows(tr_table)
    disposed = nonempty_rows(disp_table)
    tr_ids = [clean(r.get("テスト要求ID", "")) for r in trs]
    bad = [v for v in tr_ids if not ID_PATTERNS["TR"].fullmatch(v)]
    result.add("TR-D001", not bad, "Test Requirement IDs must use TR-xxx", evidence=bad or None)
    add_duplicate_assertion(result, "TR-D002", tr_ids, "Test Requirement IDs")

    auth_spec = "known_authorities" in expected
    risk_spec = "known_product_risks" in expected or "product_risk_levels" in expected
    known_auth = set(expected.get("known_authorities", []))
    known_risks = set(expected.get("known_product_risks", []))
    if isinstance(expected.get("product_risk_levels"), dict):
        known_risks |= set(expected["product_risk_levels"])

    ua, ur, missing = [], [], []
    for row in trs:
        tid = clean(row.get("テスト要求ID", ""))
        for ref in ids_in(row.get("Current Effective Authority", "")):
            if auth_spec and ref not in known_auth:
                ua.append({"tr": tid, "reference": ref})
        for ref in ids_in(row.get("関連Product Risk", "")):
            if risk_spec and ref not in known_risks:
                ur.append({"tr": tid, "reference": ref})
        for f in ("テスト要求", "Current Effective Authority", "優先度", "テストレベル / 観測方法"):
            if not clean(row.get(f, "")):
                missing.append({"tr": tid, "field": f})
    result.add("TR-D003", not ua, "Authority references must exist", evidence=ua or None)
    result.add("TR-D004", not ur, "Product Risk references must exist", evidence=ur or None)
    add_allowed_assertion(result, "TR-D005", (r.get("優先度", "") for r in trs), PRIORITIES, "Priority")
    result.add("TR-D006", not missing, "Required Test Requirement fields must exist", evidence=missing or None)

    add_allowed_assertion(result, "TR-D007", (r.get("Disposition", "") for r in disposed), DISPOSITIONS, "Disposition")
    no_reason = [clean(r.get("上流ID", "")) for r in disposed if not clean(r.get("理由 / 根拠", ""))]
    result.add("TR-D008", not no_reason, "Disposition rows require reason/evidence", evidence=no_reason or None)

    linked_auth = {ref for row in trs for ref in ids_in(row.get("Current Effective Authority", "")) if ref in known_auth}
    linked_risk = {ref for row in trs for ref in ids_in(row.get("関連Product Risk", "")) if ref in known_risks}
    disposed_ids = {clean(r.get("上流ID", "")) for r in disposed}
    closure_universe = (known_auth if auth_spec else set()) | (known_risks if risk_spec else set())
    missing_closure = sorted(closure_universe - linked_auth - linked_risk - disposed_ids)
    result.add("TR-D009", not missing_closure, "Fixture upstream Authority/Risk must close to TR or Disposition", evidence=missing_closure or None)

    levels = expected.get("product_risk_levels", {})
    overrides = set(expected.get("priority_override_trs", []))
    issues = []
    for row in trs:
        linked = [ref for ref in ids_in(row.get("関連Product Risk", "")) if ref in levels]
        if linked:
            high = max((levels[r] for r in linked), key=lambda x: RISK_LEVEL_ORDER.get(x, 0))
            actual = clean(row.get("優先度", ""))
            tid = clean(row.get("テスト要求ID", ""))
            if RISK_LEVEL_ORDER.get(actual, 0) < RISK_LEVEL_ORDER.get(high, 0) and tid not in overrides and not clean(row.get("備考", "")):
                issues.append({"tr": tid, "expected_at_least": high, "actual": actual})
    result.add("TR-D010", not issues, "Priority must inherit highest linked Product Risk unless override is explained", evidence=issues or None)

    required_missing = []
    if "required_test_requirements" in expected:
        required_missing = sorted(set(expected["required_test_requirements"]) - set(tr_ids))
    result.add("TR-D012", not required_missing, "Fixture-required Test Requirements must be present", evidence=required_missing or None)
    return result
