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
    start = find_table(
        tables,
        section_contains="開始・直接観測／静的解析",
        required_headers=(
            "活動・対象",
            "開始状態",
            "期待結果／適用rule",
            "実観測・raw ref",
            "FAIL／判定不能／未実行",
            "備考",
        ),
    )
    cleanup = find_table(
        tables,
        section_contains="Cleanupと診断",
        required_headers=(
            "scope",
            "runner管理／run外",
            "cleanup状態",
            "残存副作用",
            "再開条件・owner",
        ),
    )
    diagnosis = find_table(
        tables,
        section_contains="Cleanupと診断",
        required_headers=(
            "元run ref",
            "原因候補・確度",
            "根拠・反証",
            "不足証拠",
            "修正／再実行先",
        ),
    )
    for identifier, table, description in (
        ("TW-EXEC-D005", start, "開始・直接観測の表"),
        ("TW-EXEC-D007", cleanup, "cleanupと残存副作用の表"),
        ("TW-EXEC-D009", diagnosis, "元runの診断と再実行先の表"),
    ):
        result.add(identifier, table is not None, description + "があること")
    for identifier, table, description in (
        ("TW-EXEC-D006", start, "開始状態と根拠"),
        ("TW-EXEC-D008", cleanup, "cleanupと再開条件"),
        ("TW-EXEC-D010", diagnosis, "元run参照と診断根拠"),
    ):
        if table is not None:
            result.add(
                identifier,
                bool(table.rows)
                and all(
                    all(str(value).strip() for value in row.values())
                    for row in table.rows
                ),
                description + "の必須欄を空欄にしないこと",
            )
    return result
