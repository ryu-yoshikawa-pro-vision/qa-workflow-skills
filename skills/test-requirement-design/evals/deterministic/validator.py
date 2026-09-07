from __future__ import annotations

from scripts.skills.evals.deterministic.common import ID_PATTERNS, PRIORITIES, RISK_LEVEL_ORDER, add_allowed_assertion, add_duplicate_assertion, add_required_fields_assertion, clean, ids_in, nonempty_rows
from scripts.skills.evals.deterministic.markdown_parser import find_table, parse_tables
from scripts.skills.evals.deterministic.result import EvalResult

DISPOSITIONS = {"別テストレベル", "残存リスク", "対象外", "ブロック中"}


def validate(text: str, expected: dict, eval_id: str) -> EvalResult:
    result = EvalResult("test-requirement-design", eval_id)
    tables = parse_tables(text)
    tr_table = find_table(tables, section_contains="テスト要求一覧", required_headers=("テスト要求ID", "現在有効な仕様根拠", "優先度"))
    disp_table = find_table(tables, section_contains="テスト要求を作らない上流項目", required_headers=("上流ID", "扱い"))
    missing_tables = [label for label, table in (("テスト要求一覧", tr_table), ("テスト要求を作らない上流項目", disp_table)) if table is None]
    result.add("TR-D011", not missing_tables, "テスト要求設計の正規テーブルが存在すること", evidence=missing_tables or None)

    trs = nonempty_rows(tr_table)
    disposed = nonempty_rows(disp_table)
    tr_ids = [clean(r.get("テスト要求ID", "")) for r in trs]
    bad = [v for v in tr_ids if not ID_PATTERNS["TR"].fullmatch(v)]
    result.add("TR-D001", not bad, "テスト要求IDがTR-xxx形式であること", evidence=bad or None)
    add_duplicate_assertion(result, "TR-D002", tr_ids, "テスト要求ID")

    auth_spec = "known_authorities" in expected
    risk_spec = "known_product_risks" in expected or "product_risk_levels" in expected
    known_auth = set(expected.get("known_authorities", []))
    known_risks = set(expected.get("known_product_risks", []))
    if isinstance(expected.get("product_risk_levels"), dict):
        known_risks |= set(expected["product_risk_levels"])

    ua, ur = [], []
    for row in trs:
        tid = clean(row.get("テスト要求ID", ""))
        for ref in ids_in(row.get("現在有効な仕様根拠", "")):
            if auth_spec and ref not in known_auth:
                ua.append({"tr": tid, "reference": ref})
        for ref in ids_in(row.get("関連プロダクトリスク", "")):
            if risk_spec and ref not in known_risks:
                ur.append({"tr": tid, "reference": ref})
    result.add("TR-D003", not ua, "仕様根拠参照が存在すること", evidence=ua or None)
    result.add("TR-D004", not ur, "プロダクトリスク参照が存在すること", evidence=ur or None)
    add_allowed_assertion(result, "TR-D005", (r.get("優先度", "") for r in trs), PRIORITIES, "優先度")
    add_required_fields_assertion(result, "TR-D006", trs, ("テスト要求", "現在有効な仕様根拠", "優先度", "テストレベル / 観測方法"), "テスト要求ID", "テスト要求")

    add_allowed_assertion(result, "TR-D007", (r.get("扱い", "") for r in disposed), DISPOSITIONS, "扱い")
    no_reason = [clean(r.get("上流ID", "")) for r in disposed if not clean(r.get("理由 / 根拠", ""))]
    result.add("TR-D008", not no_reason, "扱いを記載した行に理由 / 根拠があること", evidence=no_reason or None)

    disposition_known = (known_auth if auth_spec else set()) | (known_risks if risk_spec else set())
    disposition_check = auth_spec or risk_spec
    unknown_disposed = sorted({clean(r.get("上流ID", "")) for r in disposed if disposition_check and clean(r.get("上流ID", "")) and clean(r.get("上流ID", "")) not in disposition_known})
    result.add("TR-D013", not unknown_disposed, "fixtureで上流集合を指定した場合、扱い対象の上流IDが存在すること", evidence=unknown_disposed or None)

    linked_auth = {ref for row in trs for ref in ids_in(row.get("現在有効な仕様根拠", "")) if ref in known_auth}
    linked_risk = {ref for row in trs for ref in ids_in(row.get("関連プロダクトリスク", "")) if ref in known_risks}
    linked_upstream = linked_auth | linked_risk
    disposed_ids = {clean(r.get("上流ID", "")) for r in disposed}
    closure_universe = (known_auth if auth_spec else set()) | (known_risks if risk_spec else set())
    missing_closure = sorted(closure_universe - linked_upstream - disposed_ids)
    duplicate_closure = sorted(linked_upstream & disposed_ids)
    closure_evidence = {"missing": missing_closure, "linked_and_disposed": duplicate_closure} if missing_closure or duplicate_closure else None
    result.add("TR-D009", not missing_closure and not duplicate_closure, "fixtureの上流仕様根拠 / リスクがテスト要求または扱いのどちらか一方へ閉じること", evidence=closure_evidence)

    required_links = set(expected.get("required_linked_upstream_ids", []))
    missing_required_links = sorted(required_links - linked_auth - linked_risk)
    result.add("TR-D014", not missing_required_links, "fixtureで必須の上流IDがテスト要求へ接続されていること", evidence=missing_required_links or None)

    actual_dispositions = {clean(r.get("上流ID", "")): clean(r.get("扱い", "")) for r in disposed if clean(r.get("上流ID", ""))}
    disposition_mismatch = []
    for upstream_id, disposition in expected.get("expected_dispositions", {}).items():
        if actual_dispositions.get(upstream_id) != disposition:
            disposition_mismatch.append({"id": upstream_id, "expected": disposition, "actual": actual_dispositions.get(upstream_id)})
    result.add("TR-D015", not disposition_mismatch, "fixtureで指定した上流項目の扱いが一致すること", evidence=disposition_mismatch or None)

    levels = expected.get("product_risk_levels", {})
    overrides = set(expected.get("priority_override_trs", []))
    issues = []
    for row in trs:
        linked = [ref for ref in ids_in(row.get("関連プロダクトリスク", "")) if ref in levels]
        if linked:
            high = max((levels[r] for r in linked), key=lambda x: RISK_LEVEL_ORDER.get(x, 0))
            actual = clean(row.get("優先度", ""))
            tid = clean(row.get("テスト要求ID", ""))
            if RISK_LEVEL_ORDER.get(actual, 0) < RISK_LEVEL_ORDER.get(high, 0) and tid not in overrides and not clean(row.get("備考", "")):
                issues.append({"tr": tid, "expected_at_least": high, "actual": actual})
    result.add("TR-D010", not issues, "優先度が、説明された上書きがない限り関連する最高のプロダクトリスクを引き継ぐこと", evidence=issues or None)

    required_missing = []
    if "required_test_requirements" in expected:
        required_missing = sorted(set(expected["required_test_requirements"]) - set(tr_ids))
    result.add("TR-D012", not required_missing, "fixtureで必須のテスト要求が存在すること", evidence=required_missing or None)
    return result
