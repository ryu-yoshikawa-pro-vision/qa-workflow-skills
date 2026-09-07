from __future__ import annotations

from scripts.skills.evals.deterministic.common import (
    ID_PATTERNS,
    add_allowed_assertion,
    add_duplicate_assertion,
    add_required_fields_assertion,
    clean,
    ids_in,
    nonempty_rows,
)
from scripts.skills.evals.deterministic.markdown_parser import find_table, parse_tables
from scripts.skills.evals.deterministic.result import EvalResult

CLASS_TO_PREFIX = {"SPEC": "SPEC", "DECISION": "DECISION", "INFERENCE": "INFERENCE", "UNKNOWN": "UNKNOWN"}
AUTHORITY_TYPES = {"SPEC", "DECISION", "承認済みASM"}
RELATIONS = {"独立", "補足", "上書き", "置換", "未定義部分の補完"}


def validate(text: str, expected: dict, eval_id: str) -> EvalResult:
    result = EvalResult("spec-analysis", eval_id)
    tables = parse_tables(text)

    refs_table = find_table(tables, section_contains="情報源 / 正本参照一覧", required_headers=("参照ID",))
    items_table = find_table(tables, section_contains="分析項目", required_headers=("項目ID", "分類"))
    authorities_table = find_table(tables, section_contains="現在有効な仕様根拠", required_headers=("仕様根拠ID", "種別"))
    structure_ok = all(t is not None for t in (refs_table, items_table, authorities_table))
    result.add(
        "SPEC-D012",
        structure_ok,
        "仕様分析の正規テーブルが存在すること",
        evidence={"missing": [label for label, table in (("情報源 / 正本参照一覧", refs_table), ("分析項目", items_table), ("現在有効な仕様根拠", authorities_table)) if table is None]} if not structure_ok else None,
    )

    refs = nonempty_rows(refs_table)
    items = nonempty_rows(items_table)
    authorities = nonempty_rows(authorities_table)

    add_required_fields_assertion(result, "SPEC-D016", refs, ("参照ID", "情報源 / 正本一覧"), "参照ID", "情報源参照")
    src_ids = [clean(r.get("参照ID", "")) for r in refs]
    bad_src_ids = [src_id for src_id in src_ids if not ID_PATTERNS["SRC"].fullmatch(src_id)]
    result.add("SPEC-D017", not bad_src_ids, "情報源参照IDがSRC-xxx形式であること", evidence=bad_src_ids or None)
    add_duplicate_assertion(result, "SPEC-D018", src_ids, "情報源参照ID")

    add_required_fields_assertion(result, "SPEC-D014", items, ("項目ID", "内容", "分類", "情報源 / 正本参照"), "項目ID", "分析項目")
    add_required_fields_assertion(result, "SPEC-D015", authorities, ("仕様根拠ID", "種別", "現在有効な内容", "適用範囲", "情報源 / 正本一覧", "関係"), "仕様根拠ID", "現在有効な仕様根拠")

    bad_ids, bad_class, item_ids = [], [], []
    eligible_local: set[str] = set()
    for row in items:
        item_id = clean(row.get("項目ID", ""))
        classification = clean(row.get("分類", ""))
        item_ids.append(item_id)
        pattern = ID_PATTERNS.get(CLASS_TO_PREFIX.get(classification, ""))
        if not pattern or not pattern.fullmatch(item_id):
            bad_ids.append(item_id)
        expected_prefix = {"SPEC": "SPEC-", "DECISION": "DEC-", "INFERENCE": "INF-", "UNKNOWN": "UNK-"}.get(classification)
        if not expected_prefix or not item_id.startswith(expected_prefix):
            bad_class.append({"id": item_id, "classification": classification})
        if classification in {"SPEC", "DECISION"} and item_id:
            eligible_local.add(item_id)

    result.add("SPEC-D001", not bad_ids, "分析項目IDが分類ごとの許可形式に一致すること", evidence=bad_ids or None)
    result.add("SPEC-D002", not bad_class, "分析項目IDと分類が一致すること", evidence=bad_class or None)
    add_duplicate_assertion(result, "SPEC-D003", item_ids, "分析項目ID")

    known_src = set(src_ids)
    unknown_src = []
    for row in items:
        for ref in ids_in(row.get("情報源 / 正本参照", "")):
            if ID_PATTERNS["SRC"].fullmatch(ref) and ref not in known_src:
                unknown_src.append({"item": row.get("項目ID"), "reference": ref})
    result.add("SPEC-D004", not unknown_src, "参照したSRC IDが存在すること", evidence=unknown_src or None)

    external_known = set(expected["known_authorities"]) if "known_authorities" in expected else set()
    known_authorities = eligible_local | external_known
    authority_ids = [clean(r.get("仕様根拠ID", "")) for r in authorities]
    unknown_authorities = [aid for aid in authority_ids if aid not in known_authorities]
    result.add("SPEC-D005", not unknown_authorities, "現在有効な仕様根拠IDが既知であること", evidence=unknown_authorities or None)
    add_allowed_assertion(result, "SPEC-D006", (r.get("種別", "") for r in authorities), AUTHORITY_TYPES, "仕様根拠の種別")
    add_allowed_assertion(result, "SPEC-D007", (r.get("関係", "") for r in authorities), RELATIONS, "仕様根拠の関係")

    unknown_related = []
    for row in authorities:
        for ref in ids_in(row.get("関連仕様根拠ID", "")):
            if ref not in known_authorities:
                unknown_related.append({"authority": row.get("仕様根拠ID"), "related": ref})
    result.add("SPEC-D008", not unknown_related, "関連仕様根拠IDが存在すること", evidence=unknown_related or None)

    decision_states = expected.get("decision_states", {})
    invalid_current = []
    for row in authorities:
        aid = clean(row.get("仕様根拠ID", ""))
        if aid.startswith("DEC-") and decision_states.get(aid) in {"撤回", "置換済み"}:
            invalid_current.append({"id": aid, "state": decision_states[aid]})
    result.add("SPEC-D009", not invalid_current, "撤回または置換済みの決定事項を現在有効な仕様根拠に含めないこと", evidence=invalid_current or None)

    type_mismatches = []
    for row in authorities:
        aid = clean(row.get("仕様根拠ID", ""))
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
    result.add("SPEC-D010", not type_mismatches, "現在有効な仕様根拠IDと種別が一致し、INF/UNKを仕様根拠に含めないこと", evidence=type_mismatches or None)

    required_issues = []
    if "required_analysis_ids" in expected:
        missing = sorted(set(expected["required_analysis_ids"]) - set(item_ids))
        if missing:
            required_issues.append({"kind": "analysis", "missing": missing})
    if "required_current_authorities" in expected:
        missing = sorted(set(expected["required_current_authorities"]) - set(authority_ids))
        if missing:
            required_issues.append({"kind": "current_authority", "missing": missing})
    result.add("SPEC-D011", not required_issues, "フィクスチャで必須の分析項目と現在有効な仕様根拠が存在すること", evidence=required_issues or None)

    approval_issues = []
    if "approved_assumptions" in expected:
        approved_ids = set(expected["approved_assumptions"])
        for row in authorities:
            aid = clean(row.get("仕様根拠ID", ""))
            if ID_PATTERNS["ASM"].fullmatch(aid) and aid not in approved_ids:
                approval_issues.append(aid)
    result.add("SPEC-D013", not approval_issues, "フィクスチャで参照するASMの仕様根拠が承認済みであること", evidence=approval_issues or None)
    return result
