from __future__ import annotations

from ..common import CANONICAL_SKILLS, add_allowed_assertion, clean, nonempty_rows
from ..markdown_parser import find_table, parse_bullets, parse_tables
from ..result import EvalResult

WORKFLOW_STATES={"未開始","実行中","部分完了（Blockedあり）","Blocked","完了"}; SKILL_STATES={"未開始","実行中","要再検証","Blocked","完了","再利用","省略"}


def validate(text: str, expected: dict, eval_id: str) -> EvalResult:
    result=EvalResult("qa-workflow",eval_id); tables=parse_tables(text); bullets=parse_bullets(text); rows=nonempty_rows(find_table(tables,required_headers=("Skill","状態")),"Skill")
    overall=clean(bullets.get("Workflow全体状態","")); result.add("WF-D001",overall in WORKFLOW_STATES,"Workflow overall state must be allowed",evidence=overall if overall not in WORKFLOW_STATES else None)
    invalid_names=sorted({clean(r.get("Skill","")) for r in rows if clean(r.get("Skill","")) not in CANONICAL_SKILLS}); result.add("WF-D002",not invalid_names,"Workflow Skill rows must use Canonical Skill names",evidence=invalid_names or None); add_allowed_assertion(result,"WF-D003",(r.get("状態","") for r in rows),SKILL_STATES,"Skill state")
    blocked=[clean(r.get("Skill","")) for r in rows if clean(r.get("状態",""))=="Blocked"]; recheck=[clean(r.get("Skill","")) for r in rows if clean(r.get("状態",""))=="要再検証"]; result.add("WF-D004",not(overall=="完了" and blocked),"Workflow cannot be 完了 while Blocked remains",evidence=blocked or None); result.add("WF-D005",not(overall=="完了" and recheck),"Workflow cannot be 完了 while 要再検証 remains",evidence=recheck or None)
    exp_start=expected.get("expected_start_skill"); exp_final=expected.get("expected_final_skill"); actual_start=clean(bullets.get("開始Skill","")); actual_final=clean(bullets.get("最終Skill","")); result.add("WF-D006",not exp_start or actual_start==exp_start,"Fixture expected start Skill must match routing decision",evidence={"expected":exp_start,"actual":actual_start} if exp_start and actual_start!=exp_start else None); result.add("WF-D007",not exp_final or actual_final==exp_final,"Fixture expected final Skill must match routing decision",evidence={"expected":exp_final,"actual":actual_final} if exp_final and actual_final!=exp_final else None)
    expected_skills=set(expected.get("expected_skills",[])); actual_used={clean(r.get("Skill","")) for r in rows if clean(r.get("状態","")) not in {"未開始","省略"}}; missing=sorted(expected_skills-actual_used); result.add("WF-D008",not missing,"Expected routing Skills must be represented as used/reused/in-progress/completed",evidence=missing or None)
    return result
