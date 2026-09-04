from __future__ import annotations

from ..common import ID_PATTERNS, add_allowed_assertion, add_duplicate_assertion, clean, ids_in, nonempty_rows
from ..markdown_parser import find_table, parse_tables
from ..result import EvalResult

CLASS_TO_PREFIX = {"SPEC": "SPEC", "DECISION": "DECISION", "INFERENCE": "INFERENCE", "UNKNOWN": "UNKNOWN"}
AUTHORITY_TYPES = {"SPEC", "DECISION", "承認済みASM"}
RELATIONS = {"独立", "補足", "上書き", "置換", "未定義部分の補完"}


def validate(text: str, expected: dict, eval_id: str) -> EvalResult:
    result = EvalResult("spec-analysis", eval_id)
    tables = parse_tables(text)
    refs = nonempty_rows(find_table(tables, section_contains="情報源 / Canonical Registry参照一覧", required_headers=("参照ID",)), "参照ID")
    items = nonempty_rows(find_table(tables, section_contains="分析項目", required_headers=("項目ID", "分類")), "項目ID")
    authorities = nonempty_rows(find_table(tables, section_contains="Current Effective Authority", required_headers=("Authority ID", "種別")), "Authority ID")

    bad_ids, bad_class, item_ids = [], [], []
    for row in items:
        item_id = clean(row.get("項目ID", "")); classification = clean(row.get("分類", "")); item_ids.append(item_id)
        pattern = ID_PATTERNS.get(CLASS_TO_PREFIX.get(classification, ""))
        if not pattern or not pattern.fullmatch(item_id): bad_ids.append(item_id)
        expected_prefix = {"SPEC":"SPEC-","DECISION":"DEC-","INFERENCE":"INF-","UNKNOWN":"UNK-"}.get(classification)
        if not expected_prefix or not item_id.startswith(expected_prefix): bad_class.append({"id":item_id,"classification":classification})
    result.add("SPEC-D001", not bad_ids, "Analysis item IDs must match their allowed formats", evidence=bad_ids or None)
    result.add("SPEC-D002", not bad_class, "Analysis item ID and classification must agree", evidence=bad_class or None)
    add_duplicate_assertion(result, "SPEC-D003", item_ids, "Analysis item IDs")

    known_src = {clean(r.get("参照ID", "")) for r in refs}; unknown_src=[]
    for row in items:
        for ref in ids_in(row.get("情報源 / Canonical Registry参照", "")):
            if ID_PATTERNS["SRC"].fullmatch(ref) and ref not in known_src: unknown_src.append({"item":row.get("項目ID"),"reference":ref})
    result.add("SPEC-D004", not unknown_src, "Referenced SRC IDs must exist", evidence=unknown_src or None)

    known_authorities=set(item_ids)|set(expected.get("known_authorities", [])); unknown_authorities=[]
    for row in authorities:
        aid=clean(row.get("Authority ID", ""))
        if aid not in known_authorities: unknown_authorities.append(aid)
    result.add("SPEC-D005", not unknown_authorities, "Current Effective Authority IDs must be known", evidence=unknown_authorities or None)
    add_allowed_assertion(result,"SPEC-D006",(r.get("種別","") for r in authorities),AUTHORITY_TYPES,"Authority type")
    add_allowed_assertion(result,"SPEC-D007",(r.get("関係","") for r in authorities),RELATIONS,"Authority relation")

    unknown_related=[]
    for row in authorities:
        for ref in ids_in(row.get("関連Authority ID", "")):
            if ref not in known_authorities: unknown_related.append({"authority":row.get("Authority ID"),"related":ref})
    result.add("SPEC-D008", not unknown_related, "Related Authority IDs must exist", evidence=unknown_related or None)

    decision_states=expected.get("decision_states",{}); invalid_current=[]
    for row in authorities:
        aid=clean(row.get("Authority ID", ""))
        if aid.startswith("DEC-") and decision_states.get(aid) in {"撤回","置換済み"}: invalid_current.append({"id":aid,"state":decision_states[aid]})
    result.add("SPEC-D009", not invalid_current, "Withdrawn or replaced Decisions must not be Current Effective Authority", evidence=invalid_current or None)
    return result
