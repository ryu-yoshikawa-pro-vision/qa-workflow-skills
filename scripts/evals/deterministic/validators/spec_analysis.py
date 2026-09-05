from __future__ import annotations

from ..common import (
    ID_PATTERNS,
    add_allowed_assertion,
    add_duplicate_assertion,
    clean,
    ids_in,
    nonempty_rows,
)
from ..markdown_parser import find_table, parse_tables
from ..result import EvalResult

CLASS_TO_PREFIX = {"SPEC": "SPEC", "DECISION": "DECISION", "INFERENCE": "INFERENCE", "UNKNOWN": "UNKNOWN"}
AUTHORITY_TYPES = {"SPEC", "DECISION", "承認済みASM"}
RELATIONS = {"独立", "補足", "上書き", "置換", "未定義部分の補完"}


def validate(text: str, expected: dict, eval_id: str) -> EvalResult:
    result = EvalResult("spec-analysis", eval_id)
    tables = parse_tables(text)

    refs_table = find_table(
        tables,
        section_contains="情報源 / Canonical Registry参照一覧",
        required_headers=("参照ID",),
    )
    items_table = find_table(
        tables,
        section_contains="分析項目",
        required_headers=("項目ID", "分類"),
    )
    authorities_table = find_table(
        tables,
        section_contains="Current Effective Authority",
        required_headers=("Authority ID", "種別"),
    )
    structure_ok = all(t is not None for t in (refs_table, items_table, authorities_table))
    result.add(
        "SPEC-D012",
        structure_ok,
        "Canonical spec-analysis tables must exist",
        evidence={
            "missing": [
                label
                for label, table in (
                    ("情報源 / Canonical Registry参照一覧", refs_table),
                    ("分析項目", items_table),
                    ("Current Effective Authority", authorities_table),
                )
                if table is None
            ]
        }
        if not structure_ok
        else None,
    )

    refs = nonempty_rows(refs_table, "参照ID")
    items = nonempty_rows(items_table)
    authorities = nonempty_rows(authorities_table)

    bad_ids, bad_class, item_ids = [], [], []
    eligible_local: set[str] = set()
    for row in items:
        item_id = clean(row.get("項目ID", ""))
        classification = clean(row.get("分類", ""))
        item_ids.append(item_id)
        pattern = ID_PATTERNS.get(CLASS_TO_PREFIX.get(classification, ""))
        if not pattern or not pattern.fullmatch(item_id):
            bad_ids.append(item_id)
        expected_prefix = {
            "SPEC": "SPEC-",
            "DECISION": "DEC-",
            "INFERENCE": "INF-",
            "UNKNOWN": "UNK-",
        }.get(classification)
        if not expected_prefix or not item_id.startswith(expected_prefix):
            bad_class.append({"id": item_id, "classification": classification})
        if classification in {"SPEC", "DECISION"} and item_id:
            eligible_local.add(item_id)

    result.add("SPEC-D001", not bad_ids, "Analysis item IDs must match their allowed formats", evidence=bad_ids or None)
    result.add("SPEC-D002", not bad_class, "Analysis item ID and classification must agree", evidence=bad_class or None)
    add_duplicate_assertion(result, "SPEC-D003", item_ids, "Analysis item IDs")

    known_src = {clean(r.get("参照ID", "")) for r in refs}
    unknown_src = []
    for row in items:
        for ref in ids_in(row.get("情報源 / Canonical Registry参照", "")):
            if ID_PATTERNS["SRC"].fullmatch(ref) and ref not in known_src:
                unknown_src.append({"item": row.get("項目ID"), "reference": ref})
    result.add("SPEC-D004", not unknown_src, "Referenced SRC IDs must exist", evidence=unknown_src or None)

    external_known = set(expected["known_authorities"]) if "known_authorities" in expected else set()
    known_authorities = eligible_local | external_known
    authority_ids = [clean(r.get("Authority ID", "")) for r in authorities]
    unknown_authorities = [aid for aid in authority_ids if aid not in known_authorities]
    result.add("SPEC-D005", not unknown_authorities, "Current Effective Authority IDs must be known", evidence=unknown_authorities or None)
    add_allowed_assertion(result, "SPEC-D006", (r.get("種別", "") for r in authorities), AUTHORITY_TYPES, "Authority type")
    add_allowed_assertion(result, "SPEC-D007", (r.get("関係", "") for r in authorities), RELATIONS, "Authority relation")

    unknown_related = []
    for row in authorities:
        for ref in ids_in(row.get("関連Authority ID", "")):
            if ref not in known_authorities:
                unknown_related.append({"authority": row.get("Authority ID"), "related": ref})
    result.add("SPEC-D008", not unknown_related, "Related Authority IDs must exist", evidence=unknown_related or None)

    decision_states = expected.get("decision_states", {})
    invalid_current = []
    for row in authorities:
        aid = clean(row.get("Authority ID", ""))
        if aid.startswith("DEC-") and decision_states.get(aid) in {"撤回", "置換済み"}:
            invalid_current.append({"id": aid, "state": decision_states[aid]})
    result.add("SPEC-D009", not invalid_current, "Withdrawn or replaced Decisions must not be Current Effective Authority", evidence=invalid_current or None)

    type_mismatches = []
    for row in authorities:
        aid = clean(row.get("Authority ID", ""))
        actual_type = clean(row.get("種別", ""))
        if ID_PATTERNS["SPEC"].fullmatch(aid):
            expected_type = "SPEC"
        elif ID_PATTERNS["DECISION"].fullmatch(aid):
            expected_type = "DECISION"
        elif ID_PATTERNS["ASM"].fullmatch(aid):
            expected_type = "承認済みASM"
        else:
            expected_type = None
        if expected_type is None or actual_type != expected_type:
            type_mismatches.append({"id": aid, "expected_type": expected_type, "actual_type": actual_type})
    result.add(
        "SPEC-D010",
        not type_mismatches,
        "Current Effective Authority ID and type must agree; INF/UNK cannot be Authority",
        evidence=type_mismatches or None,
    )

    required_issues = []
    if "required_analysis_ids" in expected:
        missing = sorted(set(expected["required_analysis_ids"]) - set(item_ids))
        if missing:
            required_issues.append({"kind": "analysis", "missing": missing})
    if "required_current_authorities" in expected:
        missing = sorted(set(expected["required_current_authorities"]) - set(authority_ids))
        if missing:
            required_issues.append({"kind": "current_authority", "missing": missing})
    result.add("SPEC-D011", not required_issues, "Fixture-required analysis items and Current Authorities must be present", evidence=required_issues or None)

    approval_issues = []
    if "approved_assumptions" in expected:
        approved = expected["approved_assumptions"]
        approved_ids = set(approved) if isinstance(approved, dict) else set(approved)
        for row in authorities:
            aid = clean(row.get("Authority ID", ""))
            if ID_PATTERNS["ASM"].fullmatch(aid) and aid not in approved_ids:
                approval_issues.append(aid)
    result.add("SPEC-D013", not approval_issues, "Fixture-backed ASM Authorities must be approved", evidence=approval_issues or None)
    return result
