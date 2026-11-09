from __future__ import annotations

from scripts.skills.evals.deterministic.markdown_parser import find_table, parse_tables
from scripts.skills.evals.deterministic.result import EvalResult


def validate(text: str, expected: dict, eval_id: str) -> EvalResult:
    result = EvalResult("testware-execution", eval_id)
    tables = parse_tables(text)
    primary = find_table(
        tables,
        section_contains="固定条件とpreflight",
        required_headers=[
            "run ref",
            "TC／明示testware ref・revision",
            "source／build commit",
            "環境／権限／approval",
            "runner・実入口／filter・version",
            "preflight結果・根拠",
        ],
    )
    secondary = find_table(
        tables,
        section_contains="選択集合と収集",
        required_headers=[
            "testware ref・file／title",
            "元TC ref（なければなし）",
            "予定対象",
            "取得対象",
            "attempt／raw status",
            "証跡ref・取得完全性",
        ],
    )
    result.add("TW-EXEC-D001", primary is not None, "対象・根拠の表があること")
    result.add(
        "TW-EXEC-D002", secondary is not None, "前提と実績を区別する表があること"
    )
    if primary is not None:
        result.add(
            "TW-EXEC-D003",
            bool(primary.rows)
            and all(
                all(str(value).strip() for value in row.values())
                for row in primary.rows
            ),
            "run固定条件の必須列を空欄にしないこと",
        )
    if secondary is not None:
        result.add(
            "TW-EXEC-D004",
            bool(secondary.rows)
            and all(
                all(str(value).strip() for value in row.values())
                for row in secondary.rows
            ),
            "選択集合と収集の必須列を空欄にしないこと",
        )
    return result
