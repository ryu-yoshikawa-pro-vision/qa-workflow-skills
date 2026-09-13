from __future__ import annotations

from scripts.skills.evals.deterministic.common import (
    CANONICAL_SKILLS,
    MULTI_USE_SKILL_TARGETS,
    add_allowed_assertion,
    add_duplicate_assertion,
    clean,
    nonempty_rows,
)
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
    has_target_column = state_table is not None and "対象 / 実行範囲" in state_table.headers
    result.add(
        "WF-D015",
        has_target_column,
        "ワークフロー状態表が対象 / 実行範囲列を持つこと",
        evidence={"required_header": "対象 / 実行範囲"} if not has_target_column else None,
    )

    overall = clean(bullets.get("ワークフロー全体状態", ""))
    result.add("WF-D001", overall in WORKFLOW_STATES, "ワークフロー全体状態が許可値であること", evidence=overall if overall not in WORKFLOW_STATES else None)
    skill_names = [clean(r.get("Skill", "")) for r in rows]
    invalid_names = sorted({name for name in skill_names if name not in CANONICAL_SKILLS})
    result.add("WF-D002", not invalid_names, "ワークフローのSkill行が正規Skill名を使用していること", evidence=invalid_names or None)
    scoped_keys = []
    invalid_targets = []
    for row in rows:
        skill = clean(row.get("Skill", ""))
        target = clean(row.get("対象 / 実行範囲", ""))
        scoped_keys.append(f"{skill} | {target}")
        allowed_targets = MULTI_USE_SKILL_TARGETS.get(skill)
        if allowed_targets is not None:
            if target not in allowed_targets:
                invalid_targets.append({"skill": skill, "target": target, "allowed": sorted(allowed_targets)})
        elif target:
            invalid_targets.append({"skill": skill, "target": target, "allowed": ["<空欄>"]})
    add_duplicate_assertion(result, "WF-D012", scoped_keys, "ワークフローのSkill + 対象 / 実行範囲")
    result.add(
        "WF-D016",
        not invalid_targets,
        "複数用途Skillは正規対象を必須とし、単一用途Skillは対象を空欄にできること",
        evidence=invalid_targets or None,
    )
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
    actual_start_target = clean(bullets.get("開始対象 / 実行範囲", ""))
    actual_final_target = clean(bullets.get("最終対象 / 実行範囲", ""))
    start_mismatch = bool(exp_start and actual_start != exp_start)
    final_mismatch = bool(exp_final and actual_final != exp_final)
    if "expected_start_target" in expected and actual_start_target != clean(str(expected.get("expected_start_target", ""))):
        start_mismatch = True
    if "expected_final_target" in expected and actual_final_target != clean(str(expected.get("expected_final_target", ""))):
        final_mismatch = True
    result.add(
        "WF-D006",
        not start_mismatch,
        "フィクスチャで期待する開始Skill / 対象がルーティング判断と一致すること",
        evidence={
            "expected_skill": exp_start,
            "actual_skill": actual_start,
            "expected_target": expected.get("expected_start_target"),
            "actual_target": actual_start_target,
        } if start_mismatch else None,
    )
    result.add(
        "WF-D007",
        not final_mismatch,
        "フィクスチャで期待する最終Skill / 対象がルーティング判断と一致すること",
        evidence={
            "expected_skill": exp_final,
            "actual_skill": actual_final,
            "expected_target": expected.get("expected_final_target"),
            "actual_target": actual_final_target,
        } if final_mismatch else None,
    )
    restart_target_errors = []
    for label, skill, target in (
        ("開始", actual_start, actual_start_target),
        ("最終", actual_final, actual_final_target),
    ):
        allowed_targets = MULTI_USE_SKILL_TARGETS.get(skill)
        if allowed_targets is not None and target not in allowed_targets:
            restart_target_errors.append({"label": label, "skill": skill, "target": target, "allowed": sorted(allowed_targets)})
        elif allowed_targets is None and target:
            restart_target_errors.append({"label": label, "skill": skill, "target": target, "allowed": ["<空欄>"]})
    result.add(
        "WF-D017",
        not restart_target_errors,
        "複数用途Skillの開始 / 最終対象が正規値で必須であること",
        evidence=restart_target_errors or None,
    )

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
            actual_states = [clean(row.get("状態", "")) for row in rows if clean(row.get("Skill", "")) == skill]
            if not actual_states or any(actual_state != expected_state for actual_state in actual_states):
                state_mismatches.append({"skill": skill, "expected": expected_state, "actual": actual_states or None})

    expected_scoped = expected.get("expected_scoped_skill_states", [])
    if isinstance(expected_scoped, dict):
        expected_scoped = [
            {"skill": key.split("|", 1)[0].strip(), "target": key.split("|", 1)[1].strip(), "state": value}
            for key, value in expected_scoped.items()
            if "|" in key
        ]
    actual_scoped_states = {
        (clean(row.get("Skill", "")), clean(row.get("対象 / 実行範囲", ""))): clean(row.get("状態", ""))
        for row in rows
    }
    scoped_mismatches = []
    for item in expected_scoped:
        if not isinstance(item, dict):
            scoped_mismatches.append({"expected": item, "actual": None})
            continue
        key = (clean(str(item.get("skill", ""))), clean(str(item.get("target", ""))))
        expected_state = clean(str(item.get("state", "")))
        actual_state = actual_scoped_states.get(key)
        if actual_state != expected_state:
            scoped_mismatches.append({"skill": key[0], "target": key[1], "expected": expected_state, "actual": actual_state})
    state_mismatches.extend(scoped_mismatches)
    result.add("WF-D014", not state_mismatches, "フィクスチャで期待するSkill状態（必要時は対象別）が一致すること", evidence=state_mismatches or None)
    return result
