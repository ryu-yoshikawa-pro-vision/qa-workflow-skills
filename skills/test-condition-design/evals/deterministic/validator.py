from __future__ import annotations

import re

from scripts.skills.evals.deterministic.common import (
    ID_PATTERNS,
    PRIORITIES,
    add_allowed_assertion,
    add_duplicate_assertion,
    assignment_forbidden,
    clean,
    covered_pairs,
    feasible_pairs,
    ids_in,
    nonempty_rows,
)
from scripts.skills.evals.deterministic.markdown_parser import find_table, parse_tables
from scripts.skills.evals.deterministic.result import EvalResult

DISPOSITIONS = {"対象外", "別テストレベル", "残存リスク", "成立不能", "重複", "ブロック中"}
TR_DISPOSITIONS = {"別テストレベル", "残存リスク", "対象外", "ブロック中"}


def _parse_pairwise_combination(value: str) -> tuple[dict[str, str], list[str]]:
    combo: dict[str, str] = {}
    errors: list[str] = []
    for raw in re.split(r"[;,]\s*", value.strip()):
        token = clean(raw)
        if not token:
            continue
        if "=" not in token:
            errors.append(f"不正なトークン: {token}")
            continue
        factor, val = token.split("=", 1)
        factor = clean(factor)
        val = clean(val)
        if not factor or not val:
            errors.append(f"不正なトークン: {token}")
            continue
        if factor in combo:
            errors.append(f"因子が重複: {factor}")
            continue
        combo[factor] = val
    return combo, errors


def validate(text: str, expected: dict, eval_id: str) -> EvalResult:
    result = EvalResult("test-condition-design", eval_id)
    tables = parse_tables(text)
    tcn_table = find_table(tables, section_contains="テスト観点・条件一覧", required_headers=("観点ID", "テスト要求ID", "カバレッジ基準"))
    ci_table = find_table(tables, section_contains="カバレッジ項目一覧", required_headers=("カバレッジ項目ID", "観点ID"))
    tr_disp_table = find_table(tables, section_contains="テスト条件へ展開しないテスト要求", required_headers=("テスト要求ID", "扱い"))
    cand_disp_table = find_table(tables, section_contains="カバレッジ候補の扱い", required_headers=("候補", "扱い"))
    missing_tables = [label for label, table in (
        ("テスト観点・条件一覧", tcn_table),
        ("カバレッジ項目一覧", ci_table),
        ("テスト条件へ展開しないテスト要求", tr_disp_table),
        ("カバレッジ候補の扱い", cand_disp_table),
    ) if table is None]
    result.add("TCN-D022", not missing_tables, "テスト条件設計の正規テーブルが存在すること", evidence=missing_tables or None)

    tcn = nonempty_rows(tcn_table)
    ci = nonempty_rows(ci_table)
    tr_disposed = nonempty_rows(tr_disp_table)
    candidate_disposed = nonempty_rows(cand_disp_table)

    tcn_ids = [clean(r.get("観点ID", "")) for r in tcn]
    ci_ids = [clean(r.get("カバレッジ項目ID", "")) for r in ci]
    bad_tcn = [v for v in tcn_ids if not ID_PATTERNS["TCN"].fullmatch(v)]
    bad_ci = [v for v in ci_ids if not ID_PATTERNS["CI"].fullmatch(v)]
    result.add("TCN-D001", not bad_tcn, "観点IDがTCN-xxx形式であること", evidence=bad_tcn or None)
    result.add("TCN-D002", not bad_ci, "カバレッジ項目IDがTCN-xxx-CIxx形式であること", evidence=bad_ci or None)
    add_duplicate_assertion(result, "TCN-D003", tcn_ids, "観点ID")
    add_duplicate_assertion(result, "TCN-D004", ci_ids, "カバレッジ項目ID")

    tcn_set = set(tcn_ids)
    ci_set = set(ci_ids)
    bad_parent = []
    for row in ci:
        ciid = clean(row.get("カバレッジ項目ID", ""))
        parent = clean(row.get("観点ID", ""))
        exp_parent = ciid.split("-CI", 1)[0] if "-CI" in ciid else ""
        if parent not in tcn_set or exp_parent != parent:
            bad_parent.append({"ci": ciid, "parent": parent, "expected_parent": exp_parent})
    result.add("TCN-D005", not bad_parent, "カバレッジ項目の親となる観点が存在し、IDと一致すること", evidence=bad_parent or None)

    tr_spec = "known_test_requirements" in expected
    auth_spec = "known_authorities" in expected
    risk_spec = "known_product_risks" in expected
    known_trs = set(expected.get("known_test_requirements", []))
    known_auth = set(expected.get("known_authorities", []))
    known_risks = set(expected.get("known_product_risks", []))
    unknown, missing = [], []
    for row in tcn:
        tid = clean(row.get("観点ID", ""))
        tr_refs = ids_in(row.get("テスト要求ID", ""))
        if tr_spec and any(ref not in known_trs for ref in tr_refs):
            unknown.append({"tcn": tid, "field": "TR", "refs": tr_refs})
        for ref in ids_in(row.get("関連仕様根拠 / プロダクトリスク", "")):
            if ref.startswith(("SPEC-", "DEC-", "ASM-")) and auth_spec and ref not in known_auth:
                unknown.append({"tcn": tid, "field": "related", "ref": ref})
            elif ref.startswith("RISK-") and risk_spec and ref not in known_risks:
                unknown.append({"tcn": tid, "field": "related", "ref": ref})
        for f in ("テスト要求ID", "テスト観点 / 条件", "テスト技法 / 根拠", "カバレッジ基準", "優先度"):
            if not clean(row.get(f, "")):
                missing.append({"tcn": tid, "field": f})
    result.add("TCN-D006", not unknown, "テスト要求 / 仕様根拠 / プロダクトリスクの参照が存在すること", evidence=unknown or None)
    result.add("TCN-D007", not missing, "テスト条件の必須項目が存在すること", evidence=missing or None)
    add_allowed_assertion(result, "TCN-D008", (r.get("優先度", "") for r in tcn), PRIORITIES, "テスト条件の優先度")
    add_allowed_assertion(result, "TCN-D009", (r.get("優先度", "") for r in ci), PRIORITIES, "カバレッジ項目の優先度")

    add_allowed_assertion(result, "TCN-D010", (r.get("扱い", "") for r in tr_disposed), TR_DISPOSITIONS, "テスト要求の扱い")
    add_allowed_assertion(result, "TCN-D011", (r.get("扱い", "") for r in candidate_disposed), DISPOSITIONS, "カバレッジ候補の扱い")
    unknown_disposed_trs = sorted({clean(r.get("テスト要求ID", "")) for r in tr_disposed if tr_spec and clean(r.get("テスト要求ID", "")) and clean(r.get("テスト要求ID", "")) not in known_trs})
    result.add("TCN-D029", not unknown_disposed_trs, "フィクスチャでテスト要求を指定した場合、扱い対象のテスト要求IDが存在すること", evidence=unknown_disposed_trs or None)

    bad_disp = []
    for row in tr_disposed + candidate_disposed:
        if not clean(row.get("理由 / 根拠", "")):
            bad_disp.append({"item": row.get("テスト要求ID") or row.get("候補"), "reason": "missing"})
        if clean(row.get("扱い", "")) == "重複":
            target = clean(row.get("カバー先", ""))
            if not target:
                bad_disp.append({"item": row.get("候補"), "reason": "duplicate without cover target"})
            else:
                explicit_ids = [ref for ref in ids_in(target) if ref.startswith("TCN-")]
                if explicit_ids and any(ref not in (tcn_set | ci_set) for ref in explicit_ids):
                    bad_disp.append({"item": row.get("候補"), "reason": "duplicate target does not exist", "targets": explicit_ids})
    result.add("TCN-D012", not bad_disp, "扱いには理由が必要で、重複では明示IDのカバー先が有効であること", evidence=bad_disp or None)

    linked_trs = {ref for row in tcn for ref in ids_in(row.get("テスト要求ID", "")) if ref in known_trs}
    disposed_trs = {clean(r.get("テスト要求ID", "")) for r in tr_disposed}
    missing_tr = sorted(known_trs - linked_trs - disposed_trs) if tr_spec else []
    duplicate_closure = sorted(linked_trs & disposed_trs) if tr_spec else []
    closure_evidence = {"missing": missing_tr, "linked_and_disposed": duplicate_closure} if missing_tr or duplicate_closure else None
    result.add("TCN-D013", not missing_tr and not duplicate_closure, "各フィクスチャテスト要求がテスト条件または扱いのどちらか一方へ閉じること", evidence=closure_evidence)

    pairwise = expected.get("pairwise")
    if pairwise:
        factor_table = find_table(tables, section_contains="因子 / 値 / 制約", required_headers=("因子", "値"))
        combo_table = find_table(tables, section_contains="生成組合せ", required_headers=("カバレッジ項目ID", "組合せ"))
        factor_rows = nonempty_rows(factor_table)
        combo_rows = nonempty_rows(combo_table)
        actual_factors: dict[str, set[str]] = {}
        for row in factor_rows:
            actual_factors.setdefault(clean(row.get("因子", "")), set()).add(clean(row.get("値", "")))
        expected_factors = {k: set(v) for k, v in pairwise.get("factors", {}).items()}
        mismatch = {k: {"expected": sorted(expected_factors.get(k, set())), "actual": sorted(actual_factors.get(k, set()))} for k in sorted(set(expected_factors) | set(actual_factors)) if actual_factors.get(k, set()) != expected_factors.get(k, set())}
        result.add("TCN-D014", not mismatch, "Pairwiseの因子 / 値の集合がフィクスチャと一致すること", evidence=mismatch or None)

        parsed_rows = []
        parse_errors = []
        combo_ci_ids = []
        for row in combo_rows:
            ciid = clean(row.get("カバレッジ項目ID", ""))
            combo, errors = _parse_pairwise_combination(row.get("組合せ", ""))
            combo_ci_ids.append(ciid)
            parsed_rows.append((ciid, combo, errors))
            if errors:
                parse_errors.append({"coverage_item": ciid, "errors": errors})

        unknown_combo_ci = sorted({ciid for ciid in combo_ci_ids if ciid not in ci_set})
        result.add("TCN-D026", not unknown_combo_ci, "Pairwise生成組合せが既存カバレッジ項目IDを参照すること", evidence=unknown_combo_ci or None)
        add_duplicate_assertion(result, "TCN-D027", combo_ci_ids, "Pairwise生成組合せのカバレッジ項目ID")
        result.add("TCN-D028", not parse_errors, "Pairwise生成組合せが一意な因子=値トークンを使用すること", evidence=parse_errors or None)

        expected_factor_names = set(expected_factors)
        forbidden = pairwise.get("forbidden_constraints", [])
        unknown_factor, unknown_value, forbidden_combo, missing_factor = [], [], [], []
        valid_combos = []
        for ciid, combo, errors in parsed_rows:
            extra = sorted(set(combo) - expected_factor_names)
            missing_names = sorted(expected_factor_names - set(combo))
            invalid_values = [{"factor": factor, "value": value} for factor, value in combo.items() if factor in expected_factors and value not in expected_factors[factor]]
            if extra:
                unknown_factor.append({"coverage_item": ciid, "factors": extra})
            if invalid_values:
                unknown_value.append({"coverage_item": ciid, "values": invalid_values})
            if missing_names:
                missing_factor.append({"coverage_item": ciid, "factors": missing_names})
            if not errors and not extra and not invalid_values and not missing_names and assignment_forbidden(combo, forbidden):
                forbidden_combo.append({"coverage_item": ciid, "combination": combo})
            if ciid in ci_set and not errors and not extra and not invalid_values and not missing_names and not assignment_forbidden(combo, forbidden):
                valid_combos.append(combo)

        result.add("TCN-D018", not unknown_factor, "Pairwise生成組合せに未知の因子を含めないこと", evidence=unknown_factor or None)
        result.add("TCN-D019", not unknown_value, "Pairwise生成組合せの値がフィクスチャの因子集合に存在すること", evidence=unknown_value or None)
        result.add("TCN-D020", not forbidden_combo, "Pairwise生成組合せが禁止制約に違反しないこと", evidence=forbidden_combo or None)
        result.add("TCN-D021", not missing_factor, "Pairwise生成組合せが必要なすべての因子を含むこと", evidence=missing_factor or None)

        feasible = feasible_pairs(pairwise.get("factors", {}), forbidden)
        covered = covered_pairs(valid_combos)
        missing_pairs = sorted(feasible - covered)
        result.add("TCN-D015", not pairwise.get("require_pairwise", True) or not missing_pairs, "Pairwise出力が成立可能な値ペアを100%カバーすること", evidence={"missing_pairs": missing_pairs} if missing_pairs else None)
    else:
        result.add("TCN-D014", True, "フィクスチャによるPairwise因子集合の指定なし")
        result.add("TCN-D015", True, "フィクスチャによるPairwiseカバレッジ確認は不要")
        for aid, msg in (
            ("TCN-D018", "フィクスチャによるPairwise組合せ確認は不要"),
            ("TCN-D019", "フィクスチャによるPairwise組合せ確認は不要"),
            ("TCN-D020", "フィクスチャによるPairwise組合せ確認は不要"),
            ("TCN-D021", "フィクスチャによるPairwise組合せ確認は不要"),
            ("TCN-D026", "フィクスチャによるPairwiseカバレッジ項目確認は不要"),
            ("TCN-D027", "フィクスチャによるPairwiseカバレッジ項目一意性確認は不要"),
            ("TCN-D028", "フィクスチャによるPairwiseトークン確認は不要"),
        ):
            result.add(aid, True, msg)

    transitions = expected.get("required_transitions", [])
    if transitions:
        rows = nonempty_rows(find_table(tables, section_contains="状態遷移表", required_headers=("現在状態", "イベント / 操作", "期待する次状態 / 結果", "対応カバレッジ項目ID")))
        missing_trans = []
        for t in transitions:
            matched = False
            for row in rows:
                if not (clean(row.get("現在状態", "")) == t["from"] and clean(row.get("イベント / 操作", "")) == t["event"] and clean(row.get("期待する次状態 / 結果", "")) == t["to"]):
                    continue
                ci_refs = [ref for ref in ids_in(row.get("対応カバレッジ項目ID", "")) if ID_PATTERNS["CI"].fullmatch(ref)]
                if ci_refs and all(ref in ci_set for ref in ci_refs):
                    matched = True
                    break
            if not matched and not t.get("disposition"):
                missing_trans.append(t)
        result.add("TCN-D016", not missing_trans, "フィクスチャの有効な状態遷移が既存カバレッジ項目または明示したフィクスチャ上の扱いへ閉じること", evidence=missing_trans or None)
    else:
        result.add("TCN-D016", True, "フィクスチャによる状態遷移確認は不要")

    bva = expected.get("bva", [])
    if bva:
        coverage_text = "\n".join(clean(r.get("カバレッジ項目", "")) for r in ci)
        missing_values = []
        for case in bva:
            for value in case.get("required_values", []):
                if not re.search(rf"(?<![\w.]){re.escape(str(value))}(?![\w.])", coverage_text):
                    missing_values.append(value)
        result.add("TCN-D017", not missing_values, "フィクスチャで指定したBVA必須値がカバレッジ項目に含まれること", evidence=missing_values or None)
    else:
        result.add("TCN-D017", True, "フィクスチャによるBVA確認は不要")

    required_entity_issues = []
    if "required_test_conditions" in expected:
        missing_ids = sorted(set(expected["required_test_conditions"]) - tcn_set)
        if missing_ids:
            required_entity_issues.append({"kind": "test_condition", "missing": missing_ids})
    if "required_coverage_items" in expected:
        missing_ids = sorted(set(expected["required_coverage_items"]) - ci_set)
        if missing_ids:
            required_entity_issues.append({"kind": "coverage_item", "missing": missing_ids})
    result.add("TCN-D023", not required_entity_issues, "フィクスチャで必須のテスト条件とカバレッジ項目が存在すること", evidence=required_entity_issues or None)

    ci_missing = []
    for row in ci:
        ciid = clean(row.get("カバレッジ項目ID", "")) or "<unknown>"
        absent = [f for f in ("カバレッジ項目ID", "観点ID", "カバレッジ項目", "導出元の技法 / 基準", "期待挙動の根拠", "優先度") if not clean(row.get(f, ""))]
        if absent:
            ci_missing.append({"ci": ciid, "fields": absent})
    result.add("TCN-D024", not ci_missing, "カバレッジ項目の必須項目が存在すること", evidence=ci_missing or None)

    ci_unknown_auth = []
    if auth_spec:
        for row in ci:
            for ref in ids_in(row.get("期待挙動の根拠", "")):
                if ref.startswith(("SPEC-", "DEC-", "ASM-")) and ref not in known_auth:
                    ci_unknown_auth.append({"ci": row.get("カバレッジ項目ID"), "reference": ref})
    result.add("TCN-D025", not ci_unknown_auth, "フィクスチャで仕様根拠を指定した場合、カバレッジ項目の明示的な仕様根拠参照が存在すること", evidence=ci_unknown_auth or None)
    return result
