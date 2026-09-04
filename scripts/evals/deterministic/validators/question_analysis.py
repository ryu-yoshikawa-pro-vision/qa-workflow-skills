from __future__ import annotations

from ..common import CANONICAL_SKILLS, ID_PATTERNS, add_allowed_assertion, add_duplicate_assertion, clean, nonempty_rows
from ..markdown_parser import find_table, parse_tables
from ..result import EvalResult

CLASSIFICATIONS={"Blocker","要確認","仮定可能","提案・任意"}
NORMALIZATIONS={"SPEC","DECISION","ASM","未確定"}
ASSUMPTION_STATES={"提案","承認済み","撤回","置換済み"}


def validate(text: str, expected: dict, eval_id: str) -> EvalResult:
    result=EvalResult("question-analysis",eval_id); tables=parse_tables(text)
    questions=nonempty_rows(find_table(tables,section_contains="不明点 / 質問一覧",required_headers=("ID","分類")),"ID")
    assumptions=nonempty_rows(find_table(tables,section_contains="仮定候補",required_headers=("仮定候補","状態")),"仮定候補")
    blocked=nonempty_rows(find_table(tables,section_contains="Blocked範囲",required_headers=("Blocker ID",)),"Blocker ID")
    ids=[clean(r.get("ID","")) for r in questions]; bad=[v for v in ids if not ID_PATTERNS["QUESTION"].fullmatch(v)]
    result.add("QUESTION-D001",not bad,"Question IDs must use Q-xxx",evidence=bad or None); add_duplicate_assertion(result,"QUESTION-D002",ids,"Question IDs")
    add_allowed_assertion(result,"QUESTION-D003",(r.get("分類","") for r in questions),CLASSIFICATIONS,"Classification")
    add_allowed_assertion(result,"QUESTION-D004",(r.get("回答後の正規化先","") for r in questions),NORMALIZATIONS,"Normalization target")
    invalid_skills=sorted({clean(r.get("再開Skill","")) for r in questions+blocked if clean(r.get("再開Skill","")) and clean(r.get("再開Skill","")) not in CANONICAL_SKILLS})
    result.add("QUESTION-D005",not invalid_skills,"Resume skills must be Canonical Skill names",evidence=invalid_skills or None)
    blocker_ids={clean(r.get("ID","")) for r in questions if clean(r.get("分類",""))=="Blocker"}; blocked_ids={clean(r.get("Blocker ID","")) for r in blocked}
    missing=sorted(blocker_ids-blocked_ids) if expected.get("require_blocked_for_blockers",True) else []; unknown=sorted(blocked_ids-set(ids))
    result.add("QUESTION-D006",not missing and not unknown,"Blocker rows and Blocked scope must be consistent",evidence={"missing":missing,"unknown":unknown} if missing or unknown else None)
    add_allowed_assertion(result,"QUESTION-D007",(r.get("状態","") for r in assumptions),ASSUMPTION_STATES,"Assumption state")
    bad_asm=[]
    for row in assumptions:
        asm=clean(row.get("Canonical ASM ID",""))
        if asm and not ID_PATTERNS["ASM"].fullmatch(asm): bad_asm.append(asm)
        if clean(row.get("状態",""))=="承認済み" and not asm: bad_asm.append("<missing approved ASM ID>")
    result.add("QUESTION-D008",not bad_asm,"Canonical ASM IDs must be valid when present and required for approved assumptions",evidence=bad_asm or None)
    approvals=expected.get("approved_assumptions",{}); mismatch=[]
    for row in assumptions:
        asm=clean(row.get("Canonical ASM ID",""))
        if clean(row.get("状態",""))=="承認済み" and approvals and asm not in approvals: mismatch.append(asm)
    result.add("QUESTION-D009",not mismatch,"Approved assumptions must exist in fixture approval data",evidence=mismatch or None)
    expected_cls=expected.get("expected_classifications",{}); actual={clean(r.get("ID","")):clean(r.get("分類","")) for r in questions}; mm=[]
    for qid,cls in expected_cls.items():
        if actual.get(qid)!=cls: mm.append({"id":qid,"expected":cls,"actual":actual.get(qid)})
    result.add("QUESTION-D010",not mm,"Fixture-backed classifications must match",evidence=mm or None)
    return result
