from __future__ import annotations

from scripts.skills.evals.deterministic.common import CANONICAL_SKILLS, add_allowed_assertion, add_duplicate_assertion, clean, nonempty_rows
from scripts.skills.evals.deterministic.markdown_parser import find_table, parse_bullets, parse_tables
from scripts.skills.evals.deterministic.result import EvalResult

WORKFLOW_STATES = {"未開始", "実行中", "部分完了（ブロック中あり）", "ブロック中", "完了"}
SKILL_STATES = {"未開始", "実行中", "要再検証", "ブロック中", "完了", "再利用", "省略"}


def validate(text: str, expected: dict, eval_id: str) -> EvalResult:
    result = EvalResult("qa-workflow", eval_id)
    tables = parse_tables(text)
    bullets = parse_bullets(text)
    state_table = find_table(tables, required_headers=("Skill", "状態"))
    result.add("WF-D009", state_table is not None, "ワークフロー状態表が存在すること", evidence={"missing_table": "ワークフロー状態"} if state_table is None else None)
    rows = nonempty_rows(state_table)

    overall = clean(bullets.get("ワークフロー全体状態", ""))
    result.add("WF-D001", overall in WORKFLOW_STATES, "ワークフロー全体状態が許可値であること", evidence=overall if overall not in WORKFLOW_STATES else None)
    skill_names = [clean(r.get("Skill", "")) for r in rows]
    invalid_names = sorted({name for name in skill_names if name not in CANONICAL_SKILLS})
    result.add("WF-D002", not invalid_names, "ワークフローのSkill行が正規Skill名を使用していること", evidence=invalid_names or None)
    add_duplicate_assertion(result, "WF-D012", skill_names, "ワークフローのSkill行")
    add_allowed_assertion(result, "WF-D003", (r.get("状態", "") for r in rows), SKILL_STATES, "Skill状態")

    blocked = [clean(r.get("Skill", "")) for r in rows if clean(r.get("状態", "")) == "ブロック中"]
    recheck = [clean(r.get("Skill", "")) for r in rows if clean(r.get("状態", "")) == "要再検証"]
    in_progress = [clean(r.get("Skill", "")) for r in rows if clean(r.get("状態", "")) == "実行中"]
    result.add("WF-D004", not (overall == "完了" and (blocked or in_progress)), "ブロック中または実行中が残る場合はワークフローを完了にできないこと", evidence=blocked + in_progress or None)
    result.add("WF-D005", not (overall == "完了" and recheck), "要再検証が残る場合はワークフローを完了にできないこと", evidence=recheck or None)
    result.add("WF-D010", not (overall == "部分完了（ブロック中あり）" and not blocked), "部分完了（ブロック中あり）には1件以上のブロック中Skillが必要であること", evidence={"blocked_skills": blocked} if overall == "部分完了（ブロック中あり）" and not blocked else None)
    result.add("WF-D011", not (overall == "ブロック中" and not blocked), "ワークフロー全体がブロック中の場合は1件以上のブロック中Skillが必要であること", evidence={"blocked_skills": blocked} if overall == "ブロック中" and not blocked else None)

    exp_start = expected.get("expected_start_skill")
    exp_final = expected.get("expected_final_skill")
    actual_start = clean(bullets.get("開始Skill", ""))
    actual_final = clean(bullets.get("最終Skill", ""))
    result.add("WF-D006", not exp_start or actual_start == exp_start, "フィクスチャで期待する開始Skillがルーティング判断と一致すること", evidence={"expected": exp_start, "actual": actual_start} if exp_start and actual_start != exp_start else None)
    result.add("WF-D007", not exp_final or actual_final == exp_final, "フィクスチャで期待する最終Skillがルーティング判断と一致すること", evidence={"expected": exp_final, "actual": actual_final} if exp_final and actual_final != exp_final else None)

    expected_skills = set(expected.get("expected_skills", []))
    actual_used = {clean(r.get("Skill", "")) for r in rows if clean(r.get("状態", "")) not in {"未開始", "省略"}}
    missing = sorted(expected_skills - actual_used)
    result.add("WF-D008", not missing, "期待するルーティング対象Skillが利用・再利用・実行中・完了のいずれかとして表現されていること", evidence=missing or None)

    overall_specified = "expected_overall_state" in expected
    expected_overall = expected.get("expected_overall_state")
    result.add(
        "WF-D013",
        not overall_specified or overall == expected_overall,
        "フィクスチャで期待するワークフロー全体状態が一致すること",
        evidence={"expected": expected_overall, "actual": overall} if overall_specified and overall != expected_overall else None,
    )

    expected_skill_states = expected.get("expected_skill_states", {})
    actual_skill_states = {clean(row.get("Skill", "")): clean(row.get("状態", "")) for row in rows}
    state_mismatches = []
    if "expected_skill_states" in expected:
        for skill, expected_state in expected_skill_states.items():
            actual_state = actual_skill_states.get(skill)
            if actual_state != expected_state:
                state_mismatches.append({"skill": skill, "expected": expected_state, "actual": actual_state})
    result.add("WF-D014", not state_mismatches, "フィクスチャで期待するSkill状態が一致すること", evidence=state_mismatches or None)
    return result
