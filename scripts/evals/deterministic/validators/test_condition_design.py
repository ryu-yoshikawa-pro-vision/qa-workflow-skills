from __future__ import annotations

import re

from ..common import ID_PATTERNS, PRIORITIES, add_allowed_assertion, add_duplicate_assertion, clean, covered_pairs, feasible_pairs, ids_in, nonempty_rows, parse_combination
from ..markdown_parser import find_table, parse_tables
from ..result import EvalResult

DISPOSITIONS={"対象外","別テストレベル","残存リスク","成立不能","重複","Blocked"}
TR_DISPOSITIONS={"別テストレベル","残存リスク","対象外","Blocked"}


def validate(text: str, expected: dict, eval_id: str) -> EvalResult:
    result=EvalResult("test-condition-design",eval_id); tables=parse_tables(text)
    tcn=nonempty_rows(find_table(tables,section_contains="テスト観点・条件一覧",required_headers=("観点ID","テスト要求ID","Coverage Criteria")),"観点ID")
    ci=nonempty_rows(find_table(tables,section_contains="Coverage Item一覧",required_headers=("Coverage Item ID","観点ID")),"Coverage Item ID")
    tr_disposed=nonempty_rows(find_table(tables,section_contains="Test Conditionへ展開しないTest Requirement",required_headers=("テスト要求ID","Disposition")),"テスト要求ID")
    candidate_disposed=nonempty_rows(find_table(tables,section_contains="Coverage候補のDisposition",required_headers=("候補","Disposition")),"候補")
    tcn_ids=[clean(r.get("観点ID","")) for r in tcn]; ci_ids=[clean(r.get("Coverage Item ID","")) for r in ci]
    bad_tcn=[v for v in tcn_ids if not ID_PATTERNS["TCN"].fullmatch(v)]; bad_ci=[v for v in ci_ids if not ID_PATTERNS["CI"].fullmatch(v)]
    result.add("TCN-D001",not bad_tcn,"TCN IDs must use TCN-xxx",evidence=bad_tcn or None); result.add("TCN-D002",not bad_ci,"Coverage Item IDs must use TCN-xxx-CIxx",evidence=bad_ci or None); add_duplicate_assertion(result,"TCN-D003",tcn_ids,"TCN IDs"); add_duplicate_assertion(result,"TCN-D004",ci_ids,"Coverage Item IDs")
    tcn_set=set(tcn_ids); bad_parent=[]
    for row in ci:
        ciid=clean(row.get("Coverage Item ID","")); parent=clean(row.get("観点ID","")); exp_parent=ciid.split("-CI",1)[0] if "-CI" in ciid else ""
        if parent not in tcn_set or exp_parent!=parent: bad_parent.append({"ci":ciid,"parent":parent,"expected_parent":exp_parent})
    result.add("TCN-D005",not bad_parent,"Coverage Item parent TCN must exist and match its ID",evidence=bad_parent or None)
    known_trs=set(expected.get("known_test_requirements",[])); known_auth=set(expected.get("known_authorities",[])); known_risks=set(expected.get("known_product_risks",[])); unknown=[]; missing=[]
    for row in tcn:
        tid=clean(row.get("観点ID","")); tr_refs=ids_in(row.get("テスト要求ID",""))
        if known_trs and any(ref not in known_trs for ref in tr_refs): unknown.append({"tcn":tid,"field":"TR","refs":tr_refs})
        for ref in ids_in(row.get("関連Authority / Product Risk","")):
            if (ref.startswith(("SPEC-","DEC-","ASM-")) and known_auth and ref not in known_auth) or (ref.startswith("RISK-") and known_risks and ref not in known_risks): unknown.append({"tcn":tid,"field":"related","ref":ref})
        for f in ("テスト要求ID","テスト観点 / 条件","テスト技法 / 根拠","Coverage Criteria","優先度"):
            if not clean(row.get(f,"")): missing.append({"tcn":tid,"field":f})
    result.add("TCN-D006",not unknown,"TR/Authority/Product Risk references must exist",evidence=unknown or None); result.add("TCN-D007",not missing,"TCN required fields must exist",evidence=missing or None); add_allowed_assertion(result,"TCN-D008",(r.get("優先度","") for r in tcn),PRIORITIES,"TCN priority"); add_allowed_assertion(result,"TCN-D009",(r.get("優先度","") for r in ci),PRIORITIES,"Coverage Item priority")
    add_allowed_assertion(result,"TCN-D010",(r.get("Disposition","") for r in tr_disposed),TR_DISPOSITIONS,"TR Disposition"); add_allowed_assertion(result,"TCN-D011",(r.get("Disposition","") for r in candidate_disposed),DISPOSITIONS,"Coverage candidate Disposition")
    bad_disp=[]
    for row in tr_disposed+candidate_disposed:
        if not clean(row.get("理由 / 根拠","")): bad_disp.append({"item":row.get("テスト要求ID") or row.get("候補"),"reason":"missing"})
        if clean(row.get("Disposition",""))=="重複" and not clean(row.get("カバー先","")): bad_disp.append({"item":row.get("候補"),"reason":"duplicate without cover target"})
    result.add("TCN-D012",not bad_disp,"Disposition requires reason; duplicate requires cover target",evidence=bad_disp or None)
    linked_trs={ref for row in tcn for ref in ids_in(row.get("テスト要求ID","")) if ref in known_trs}; disposed_trs={clean(r.get("テスト要求ID","")) for r in tr_disposed}; missing_tr=sorted(known_trs-linked_trs-disposed_trs); result.add("TCN-D013",not missing_tr,"Each fixture TR must close to TCN or Disposition",evidence=missing_tr or None)
    pairwise=expected.get("pairwise")
    if pairwise:
        factor_rows=nonempty_rows(find_table(tables,section_contains="Factor / Value / Constraint",required_headers=("Factor","Value")),"Factor"); combo_rows=nonempty_rows(find_table(tables,section_contains="生成組合せ",required_headers=("Coverage Item ID","組合せ")),"Coverage Item ID")
        actual_factors={}
        for row in factor_rows: actual_factors.setdefault(clean(row.get("Factor","")),set()).add(clean(row.get("Value","")))
        expected_factors={k:set(v) for k,v in pairwise.get("factors",{}).items()}; mismatch={k:{"expected":sorted(v),"actual":sorted(actual_factors.get(k,set()))} for k,v in expected_factors.items() if actual_factors.get(k,set())!=v}; result.add("TCN-D014",not mismatch,"Pairwise Factor/Value universe must match fixture",evidence=mismatch or None)
        combos=[parse_combination(r.get("組合せ","")) for r in combo_rows]; combos=[c for c in combos if c]; feasible=feasible_pairs(pairwise.get("factors",{}),pairwise.get("forbidden_constraints",[])); covered=covered_pairs(combos); missing_pairs=sorted(feasible-covered)
        result.add("TCN-D015",not pairwise.get("require_pairwise",True) or not missing_pairs,"Pairwise output must cover 100% of feasible value pairs",evidence={"missing_pairs":missing_pairs} if missing_pairs else None)
    else:
        result.add("TCN-D014",True,"No fixture-backed Pairwise universe supplied"); result.add("TCN-D015",True,"No fixture-backed Pairwise coverage check required")
    transitions=expected.get("required_transitions",[])
    if transitions:
        rows=nonempty_rows(find_table(tables,section_contains="状態遷移表",required_headers=("現在状態","イベント / 操作","期待する次状態 / 結果","対応Coverage Item ID")),"現在状態"); missing_trans=[]
        for t in transitions:
            matched=any(clean(r.get("現在状態",""))==t["from"] and clean(r.get("イベント / 操作",""))==t["event"] and clean(r.get("期待する次状態 / 結果",""))==t["to"] and clean(r.get("対応Coverage Item ID","")) for r in rows)
            if not matched and not t.get("disposition"): missing_trans.append(t)
        result.add("TCN-D016",not missing_trans,"Fixture valid transitions must close to Coverage Item or explicit fixture disposition",evidence=missing_trans or None)
    else: result.add("TCN-D016",True,"No fixture-backed state-transition check required")
    bva=expected.get("bva",[])
    if bva:
        coverage_text="\n".join(clean(r.get("Coverage Item","")) for r in ci); missing_values=[]
        for case in bva:
            for value in case.get("required_values",[]):
                if not re.search(rf"(?<![\w.]){re.escape(str(value))}(?![\w.])",coverage_text): missing_values.append(value)
        result.add("TCN-D017",not missing_values,"Fixture-backed BVA required values must appear in Coverage Items",evidence=missing_values or None)
    else: result.add("TCN-D017",True,"No fixture-backed BVA check required")
    return result
