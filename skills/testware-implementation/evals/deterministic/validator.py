from __future__ import annotations

from scripts.skills.evals.deterministic.markdown_parser import find_table, parse_tables
from scripts.skills.evals.deterministic.result import EvalResult


def validate(text: str, expected: dict, eval_id: str) -> EvalResult:
    result = EvalResult("testware-implementation", eval_id)
    tables = parse_tables(text)
    primary = find_table(
        tables,
        section_contains="対象と根拠",
        required_headers=["対象ref","TC ref・revision／TCなし明示対象","仕様Authority・revision","実装方式","変更対象testware","状態"],
    )
    secondary = find_table(
        tables,
        section_contains="変更前と反映",
        required_headers=["branch／HEAD","許可path","対象pathの前提hash／dirty","隔離workspace","共有先条件付き反映・readback","競合／block"],
    )
    result.add("TW-IMPL-D001", primary is not None, "対象・根拠の表があること")
    result.add("TW-IMPL-D002", secondary is not None, "前提と実績を区別する表があること")
    if primary is not None:
        result.add(
            "TW-IMPL-D003",
            bool(primary.rows) and all(
                any(str(value).strip() for value in row.values())
                for row in primary.rows
            ),
            "対象を最低1件、または未実施理由で明示すること",
        )
    if secondary is not None:
        result.add(
            "TW-IMPL-D004",
            bool(secondary.rows),
            "実施または未実施の状態を記録すること",
        )
    return result
