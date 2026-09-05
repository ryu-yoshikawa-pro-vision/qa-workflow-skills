from __future__ import annotations

import re

from ..common import (
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
from ..markdown_parser import find_table, parse_tables
from ..result import EvalResult

DISPOSITIONS = {"対象外", "別テストレベル", "残存リスク", "成立不能", "重複", "Blocked"}
TR_DISPOSITIONS = {"別テストレベル", "残存リスク", "対象外", "Blocked"}


def _parse_pairwise_combination(value: str) -> tuple[dict[str, str], list[str]]:
    combo: dict[str, str] = {}
    errors: list[str] = []
    for raw in re.split(r"[;,]\s*", value.strip()):
        token = clean(raw)
        if not token:
            continue
        if "=" not in token:
            errors.append(f"invalid token: {token}")
            continue
        factor, val = token.split("=", 1)
        factor = clean(factor)
        val = clean(val)
        if not factor or not val:
            errors.append(f"invalid token: {token}")
            continue
        if factor in combo:
            errors.append(f"duplicate factor: {factor}")
            continue
        combo[factor] = val
    return combo, errors


def validate(text: str, expected: dict, eval_id: str) -> EvalResult:
    result = EvalResult("test-condition-design", eval_id)
    tables = parse_tables(text)
    tcn_table = find_table(tables, section_contains="テスト観点・条件一覧", required_headers=("観点ID", "テスト要求ID", "Coverage Criteria"))
    ci_table = find_table(tables, section_contains="Coverage Item一覧", required_headers=("Coverage Item ID", "観点ID"))
    tr_disp_table = find_table(tables, section_contains="Test Conditionへ展開しないTest Requirement", required_headers=("テスト要求ID", "Disposition"))
    cand_disp_table = find_table(tables, section_contains="Coverage候補のDisposition", required_headers=("候補", "Disposition"))
    missing_tables = [label for label, table in (
        ("テスト観点・条件一覧", tcn_table),
        ("Coverage Item一覧", ci_table),
        ("Test Conditionへ展開しないTest Requirement", tr_disp_table),
        ("Coverage候補のDisposition", cand_disp_table),
    ) if table is None]
    result.add("TCN-D022", not missing_tables, "Canonical test-condition-design tables must exist", evidence=missing_tables or None)

    tcn = nonempty_rows(tcn_table)
    ci = nonempty_rows(ci_table)
    tr_disposed = nonempty_rows(tr_disp_table)
    candidate_disposed = nonempty_rows(cand_disp_table)

    tcn_ids = [clean(r.get("観点ID", "")) for r in tcn]
    ci_ids = [clean(r.get("Coverage Item ID", "")) for r in ci]
    bad_tcn = [v for v in tcn_ids if not ID_PATTERNS["TCN"].fullmatch(v)]
    bad_ci = [v for v in ci_ids if not ID_PATTERNS["CI"].fullmatch(v)]
    result.add("TCN-D001", not bad_tcn, "TCN IDs must use TCN-xxx", evidence=bad_tcn or None)
    result.add("TCN-D002", not bad_ci, "Coverage Item IDs must use TCN-xxx-CIxx", evidence=bad_ci or None)
    add_duplicate_assertion(result, "TCN-D003", tcn_ids, "TCN IDs")
    add_duplicate_assertion(result, "TCN-D004", ci_ids, "Coverage Item IDs")

    tcn_set = set(tcn_ids)
    ci_set = set(ci_ids)
    bad_parent = []
    for row in ci:
        ciid = clean(row.get("Coverage Item ID", ""))
        parent = clean(row.get("観点ID", ""))
        exp_parent = ciid.split("-CI", 1)[0] if "-CI" in ciid else ""
        if parent not in tcn_set or exp_parent != parent:
            bad_parent.append({"ci": ciid, "parent": parent, "expected_parent": exp_parent})
    result.add("TCN-D005", not bad_parent, "Coverage Item parent TCN must exist and match its ID", evidence=bad_parent or None)

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
        for ref in ids_in(row.get("関連Authority / Product Risk", "")):
            if ref.startswith(("SPEC-", "DEC-", "ASM-")) and auth_spec and ref not in known_auth:
                unknown.append({"tcn": tid, "field": "related", "ref": ref})
            elif ref.startswith("RISK-") and risk_spec and ref not in known_risks:
                unknown.append({"tcn": tid, "field": "related", "ref": ref})
        for f in ("テスト要求ID", "テスト観点 / 条件", "テスト技法 / 根拠", "Coverage Criteria", "優先度"):
            if not clean(row.get(f, "")):
                missing.append({"tcn": tid, "field": f})
    result.add("TCN-D006", not unknown, "TR/Authority/Product Risk references must exist", evidence=unknown or None)
    result.add("TCN-D007", not missing, "TCN required fields must exist", evidence=missing or None)
    add_allowed_assertion(result, "TCN-D008", (r.get("優先度", "") for r in tcn), PRIORITIES, "TCN priority")
    add_allowed_assertion(result, "TCN-D009", (r.get("優先度", "") for r in ci), PRIORITIES, "Coverage Item priority")

    add_allowed_assertion(result, "TCN-D010", (r.get("Disposition", "") for r in tr_disposed), TR_DISPOSITIONS, "TR Disposition")
    add_allowed_assertion(result, "TCN-D011", (r.get("Disposition", "") for r in candidate_disposed), DISPOSITIONS, "Coverage candidate Disposition")

    bad_disp = []
    for row in tr_disposed + candidate_disposed:
        if not clean(row.get("理由 / 根拠", "")):
            bad_disp.append({"item": row.get("テスト要求ID") or row.get("候補"), "reason": "missing"})
        if clean(row.get("Disposition", "")) == "重複":
            target = clean(row.get("カバー先", ""))
            if not target:
                bad_disp.append({"item": row.get("候補"), "reason": "duplicate without cover target"})
            else:
                explicit_ids = [ref for ref in ids_in(target) if ref.startswith("TCN-")]
                if explicit_ids and any(ref not in (tcn_set | ci_set) for ref in explicit_ids):
                    bad_disp.append({"item": row.get("候補"), "reason": "duplicate target does not exist", "targets": explicit_ids})
    result.add("TCN-D012", not bad_disp, "Disposition requires reason; duplicate requires a valid cover target when an ID is explicit", evidence=bad_disp or None)

    linked_trs = {ref for row in tcn for ref in ids_in(row.get("テスト要求ID", "")) if ref in known_trs}
    disposed_trs = {clean(r.get("テスト要求ID", "")) for r in tr_disposed}
    missing_tr = sorted(known_trs - linked_trs - disposed_trs) if tr_spec else []
    result.add("TCN-D013", not missing_tr, "Each fixture TR must close to TCN or Disposition", evidence=missing_tr or None)

    pairwise = expected.get("pairwise")
    if pairwise:
        factor_table = find_table(tables, section_contains="Factor / Value / Constraint", required_headers=("Factor", "Value"))
        combo_table = find_table(tables, section_contains="生成組合せ", required_headers=("Coverage Item ID", "組合せ"))
        factor_rows = nonempty_rows(factor_table)
        combo_rows = nonempty_rows(combo_table)
        actual_factors: dict[str, set[str]] = {}
        for row in factor_rows:
            actual_factors.setdefault(clean(row.get("Factor", "")), set()).add(clean(row.get("Value", "")))
        expected_factors = {k: set(v) for k, v in pairwise.get("factors", {}).items()}
        mismatch = {
            k: {"expected": sorted(expected_factors.get(k, set())), "actual": sorted(actual_factors.get(k, set()))}
            for k in sorted(set(expected_factors) | set(actual_factors))
            if actual_factors.get(k, set()) != expected_factors.get(k, set())
        }
        result.add("TCN-D014", not mismatch, "Pairwise Factor/Value universe must match fixture", evidence=mismatch or None)

        parsed_rows = []
        parse_errors = []
        combo_ci_ids = []
        for row in combo_rows:
            ciid = clean(row.get("Coverage Item ID", ""))
            combo, errors = _parse_pairwise_combination(row.get("組合せ", ""))
            combo_ci_ids.append(ciid)
            parsed_rows.append((ciid, combo, errors))
            if errors:
                parse_errors.append({"coverage_item": ciid, "errors": errors})

        unknown_combo_ci = sorted({ciid for ciid in combo_ci_ids if ciid not in ci_set})
        result.add("TCN-D026", not unknown_combo_ci, "Pairwise generated combinations must reference existing Coverage Item IDs", evidence=unknown_combo_ci or None)
        add_duplicate_assertion(result, "TCN-D027", combo_ci_ids, "Pairwise generated Coverage Item IDs")
        result.add("TCN-D028", not parse_errors, "Pairwise generated combinations must use unique Factor=Value tokens", evidence=parse_errors or None)

        expected_factor_names = set(expected_factors)
        forbidden = pairwise.get("forbidden_constraints", [])
        unknown_factor, unknown_value, forbidden_combo, missing_factor = [], [], [], []
        valid_combos = []
        for ciid, combo, errors in parsed_rows:
            extra = sorted(set(combo) - expected_factor_names)
            missing_names = sorted(expected_factor_names - set(combo))
            invalid_values = [
                {"factor": factor, "value": value}
                for factor, value in combo.items()
                if factor in expected_factors and value not in expected_factors[factor]
            ]
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

        result.add("TCN-D018", not unknown_factor, "Generated Pairwise combinations must not contain unknown Factors", evidence=unknown_factor or None)
        result.add("TCN-D019", not unknown_value, "Generated Pairwise combination Values must exist in the fixture Factor universe", evidence=unknown_value or None)
        result.add("TCN-D020", not forbidden_combo, "Generated Pairwise combinations must not violate forbidden constraints", evidence=forbidden_combo or None)
        result.add("TCN-D021", not missing_factor, "Generated Pairwise combinations must contain every required Factor", evidence=missing_factor or None)

        feasible = feasible_pairs(pairwise.get("factors", {}), forbidden)
        covered = covered_pairs(valid_combos)
        missing_pairs = sorted(feasible - covered)
        result.add("TCN-D015", not pairwise.get("require_pairwise", True) or not missing_pairs, "Pairwise output must cover 100% of feasible value pairs", evidence={"missing_pairs": missing_pairs} if missing_pairs else None)
    else:
        result.add("TCN-D014", True, "No fixture-backed Pairwise universe supplied")
        result.add("TCN-D015", True, "No fixture-backed Pairwise coverage check required")
        for aid, msg in (
            ("TCN-D018", "No fixture-backed Pairwise combination check required"),
            ("TCN-D019", "No fixture-backed Pairwise combination check required"),
            ("TCN-D020", "No fixture-backed Pairwise combination check required"),
            ("TCN-D021", "No fixture-backed Pairwise combination check required"),
            ("TCN-D026", "No fixture-backed Pairwise Coverage Item check required"),
            ("TCN-D027", "No fixture-backed Pairwise Coverage Item uniqueness check required"),
            ("TCN-D028", "No fixture-backed Pairwise token check required"),
        ):
            result.add(aid, True, msg)

    transitions = expected.get("required_transitions", [])
    if transitions:
        rows = nonempty_rows(find_table(tables, section_contains="状態遷移表", required_headers=("現在状態", "イベント / 操作", "期待する次状態 / 結果", "対応Coverage Item ID")))
        missing_trans = []
        for t in transitions:
            matched = False
            for row in rows:
                if not (
                    clean(row.get("現在状態", "")) == t["from"]
                    and clean(row.get("イベント / 操作", "")) == t["event"]
                    and clean(row.get("期待する次状態 / 結果", "")) == t["to"]
                ):
                    continue
                ci_refs = [ref for ref in ids_in(row.get("対応Coverage Item ID", "")) if ID_PATTERNS["CI"].fullmatch(ref)]
                if ci_refs and all(ref in ci_set for ref in ci_refs):
                    matched = True
                    break
            if not matched and not t.get("disposition"):
                missing_trans.append(t)
        result.add("TCN-D016", not missing_trans, "Fixture valid transitions must close to existing Coverage Items or explicit fixture disposition", evidence=missing_trans or None)
    else:
        result.add("TCN-D016", True, "No fixture-backed state-transition check required")

    bva = expected.get("bva", [])
    if bva:
        coverage_text = "\n".join(clean(r.get("Coverage Item", "")) for r in ci)
        missing_values = []
        for case in bva:
            for value in case.get("required_values", []):
                if not re.search(rf"(?<![\w.]){re.escape(str(value))}(?![\w.])", coverage_text):
                    missing_values.append(value)
        result.add("TCN-D017", not missing_values, "Fixture-backed BVA required values must appear in Coverage Items", evidence=missing_values or None)
    else:
        result.add("TCN-D017", True, "No fixture-backed BVA check required")

    required_entity_issues = []
    if "required_test_conditions" in expected:
        missing_ids = sorted(set(expected["required_test_conditions"]) - tcn_set)
        if missing_ids:
            required_entity_issues.append({"kind": "test_condition", "missing": missing_ids})
    if "required_coverage_items" in expected:
        missing_ids = sorted(set(expected["required_coverage_items"]) - ci_set)
        if missing_ids:
            required_entity_issues.append({"kind": "coverage_item", "missing": missing_ids})
    result.add("TCN-D023", not required_entity_issues, "Fixture-required Test Conditions and Coverage Items must be present", evidence=required_entity_issues or None)

    ci_missing = []
    for row in ci:
        ciid = clean(row.get("Coverage Item ID", "")) or "<unknown>"
        absent = [
            f for f in ("Coverage Item ID", "観点ID", "Coverage Item", "導出元の技法 / 基準", "期待挙動の根拠", "優先度")
            if not clean(row.get(f, ""))
        ]
        if absent:
            ci_missing.append({"ci": ciid, "fields": absent})
    result.add("TCN-D024", not ci_missing, "Coverage Item required fields must exist", evidence=ci_missing or None)

    ci_unknown_auth = []
    if auth_spec:
        for row in ci:
            for ref in ids_in(row.get("期待挙動の根拠", "")):
                if ref.startswith(("SPEC-", "DEC-", "ASM-")) and ref not in known_auth:
                    ci_unknown_auth.append({"ci": row.get("Coverage Item ID"), "reference": ref})
    result.add("TCN-D025", not ci_unknown_auth, "Explicit Coverage Item Authority references must exist when fixture Authorities are specified", evidence=ci_unknown_auth or None)
    return result
