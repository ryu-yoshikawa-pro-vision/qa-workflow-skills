from __future__ import annotations

from scripts.skills.evals.deterministic.common import (
    CANONICAL_SKILLS,
    ID_PATTERNS,
    add_allowed_assertion,
    add_duplicate_assertion,
    add_required_fields_assertion,
    clean,
    nonempty_rows,
)
from scripts.skills.evals.deterministic.markdown_parser import find_table, parse_tables
from scripts.skills.evals.deterministic.result import EvalResult

CLASSIFICATIONS = {"ブロッカー", "要確認", "仮定可能", "提案・任意"}
NORMALIZATIONS = {"SPEC", "DECISION", "ASM", "未確定"}
ASSUMPTION_STATES = {"提案", "承認済み", "撤回", "置換済み"}


def validate(text: str, expected: dict, eval_id: str) -> EvalResult:
    result = EvalResult("question-analysis", eval_id)
    tables = parse_tables(text)
    q_table = find_table(tables, section_contains="不明点 / 質問一覧", required_headers=("ID", "分類"))
    a_table = find_table(tables, section_contains="仮定候補", required_headers=("仮定候補", "状態"))
    b_table = find_table(tables, section_contains="ブロック中範囲", required_headers=("ブロッカーID",))
    missing_tables = [label for label, table in (("不明点 / 質問一覧", q_table), ("仮定候補", a_table), ("ブロック中範囲", b_table)) if table is None]
    result.add("QUESTION-D011", not missing_tables, "不明点・矛盾分析の正規テーブルが存在すること", evidence=missing_tables or None)

    questions = nonempty_rows(q_table)
    assumptions = nonempty_rows(a_table)
    blocked = nonempty_rows(b_table)

    add_required_fields_assertion(result, "QUESTION-D012", questions, ("ID", "問題 / 質問", "根拠", "分類", "影響範囲 / 成果物", "回答なしの場合の扱い", "回答後の正規化先", "再開Skill"), "ID", "質問")
    add_required_fields_assertion(result, "QUESTION-D013", blocked, ("ブロッカーID", "ブロック中成果物 / 範囲", "必要な決定 / 情報源", "再開Skill"), "ブロッカーID", "ブロック中範囲")
    add_required_fields_assertion(result, "QUESTION-D014", assumptions, ("仮定候補", "状態", "根拠 / 理由", "影響範囲"), "正本ASM ID", "仮定候補")

    ids = [clean(r.get("ID", "")) for r in questions]
    bad = [v for v in ids if not ID_PATTERNS["QUESTION"].fullmatch(v)]
    result.add("QUESTION-D001", not bad, "質問IDがQ-xxx形式であること", evidence=bad or None)
    add_duplicate_assertion(result, "QUESTION-D002", ids, "質問ID")
    add_allowed_assertion(result, "QUESTION-D003", (r.get("分類", "") for r in questions), CLASSIFICATIONS, "分類")
    add_allowed_assertion(result, "QUESTION-D004", (r.get("回答後の正規化先", "") for r in questions), NORMALIZATIONS, "正規化先")

    invalid_skills = sorted({clean(r.get("再開Skill", "")) for r in questions + blocked if clean(r.get("再開Skill", "")) and clean(r.get("再開Skill", "")) not in CANONICAL_SKILLS})
    result.add("QUESTION-D005", not invalid_skills, "再開Skillが正規Skill名であること", evidence=invalid_skills or None)

    blocker_ids = {clean(r.get("ID", "")) for r in questions if clean(r.get("分類", "")) == "ブロッカー"}
    blocked_ids = {clean(r.get("ブロッカーID", "")) for r in blocked if clean(r.get("ブロッカーID", ""))}
    missing = sorted(blocker_ids - blocked_ids) if expected.get("require_blocked_for_blockers", True) else []
    unknown = sorted(blocked_ids - set(ids))
    result.add("QUESTION-D006", not missing and not unknown, "ブロッカー行とブロック中範囲が整合すること", evidence={"missing": missing, "unknown": unknown} if missing or unknown else None)

    add_allowed_assertion(result, "QUESTION-D007", (r.get("状態", "") for r in assumptions), ASSUMPTION_STATES, "仮定状態")
    bad_asm = []
    approved_output_ids = set()
    for row in assumptions:
        asm = clean(row.get("正本ASM ID", ""))
        if asm and not ID_PATTERNS["ASM"].fullmatch(asm):
            bad_asm.append(asm)
        if clean(row.get("状態", "")) == "承認済み":
            if not asm:
                bad_asm.append("<missing approved ASM ID>")
            elif ID_PATTERNS["ASM"].fullmatch(asm):
                approved_output_ids.add(asm)
    result.add("QUESTION-D008", not bad_asm, "正本ASM IDが有効で、承認済み仮定では必須であること", evidence=bad_asm or None)

    mismatch = []
    if "approved_assumptions" in expected:
        approval_ids = set(expected["approved_assumptions"])
        for row in assumptions:
            asm = clean(row.get("正本ASM ID", ""))
            if clean(row.get("状態", "")) == "承認済み" and asm not in approval_ids:
                mismatch.append(asm)
    result.add("QUESTION-D009", not mismatch, "承認済み仮定がfixtureの承認情報に存在すること", evidence=mismatch or None)

    required_approved = set(expected.get("required_approved_assumptions", []))
    missing_required_approved = sorted(required_approved - approved_output_ids)
    result.add("QUESTION-D015", not missing_required_approved, "fixtureで必須の承認済み仮定が正本ASMとして存在すること", evidence=missing_required_approved or None)

    expected_cls = expected.get("expected_classifications", {})
    actual_cls = {clean(r.get("ID", "")): clean(r.get("分類", "")) for r in questions}
    classification_mismatch = []
    for qid, cls in expected_cls.items():
        if actual_cls.get(qid) != cls:
            classification_mismatch.append({"id": qid, "expected": cls, "actual": actual_cls.get(qid)})
    result.add("QUESTION-D010", not classification_mismatch, "fixtureで指定した分類が一致すること", evidence=classification_mismatch or None)

    expected_normalizations = expected.get("expected_normalizations", {})
    actual_normalizations = {clean(r.get("ID", "")): clean(r.get("回答後の正規化先", "")) for r in questions}
    normalization_mismatch = []
    for qid, target in expected_normalizations.items():
        if actual_normalizations.get(qid) != target:
            normalization_mismatch.append({"id": qid, "expected": target, "actual": actual_normalizations.get(qid)})
    result.add("QUESTION-D016", not normalization_mismatch, "fixtureで指定した正規化先が一致すること", evidence=normalization_mismatch or None)
    return result
