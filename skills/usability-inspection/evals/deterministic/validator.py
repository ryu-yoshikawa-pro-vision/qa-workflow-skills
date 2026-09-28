from __future__ import annotations
import json, re
from scripts.skills.evals.deterministic.result import EvalResult

SECTIONS={"Inspection metadata","Scope and closure","Objective observations","Accessibility requirement checks",
          "Supported test rule results","Measurements","Additional observation requests","Summary and limitations"}


def validate(text: str, expected: dict, eval_id: str) -> EvalResult:
    result=EvalResult('usability-inspection',eval_id)
    headings=set(re.findall(r'^##\s+(.+?)\s*$',text,re.M))
    missing=sorted(SECTIONS-headings)
    result.add('UI-D001',not missing,'required inspection output sections exist',evidence=missing or None)
    required=expected.get('required_tokens',[])
    result.add('UI-D002',all(token in text for token in required),'fixture-required facts are present',evidence=[x for x in required if x not in text] or None)
    forbidden=expected.get('forbidden_tokens',[])
    result.add('UI-D003',not any(token.casefold() in text.casefold() for token in forbidden),'out-of-scope conformance and human outcome claims are absent',evidence=[x for x in forbidden if x.casefold() in text.casefold()] or None)
    status_tokens=('問題を確認','問題なし','判定不能','対象外')
    closure='Scope and closure' in headings and any(token in text for token in status_tokens)
    result.add('UI-D004',closure,'scope rows have an allowed closed outcome')
    request_rows=re.findall(r'^\|\s*(OBSREQ-\d{3,})\s*\|([^\n]+)$',text,re.M)
    result.add('UI-D005',not any('planned' in row.casefold() for _,row in request_rows),'final additional observation requests are closed')
    return result
