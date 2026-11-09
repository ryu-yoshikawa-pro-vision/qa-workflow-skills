from __future__ import annotations

from scripts.skills.evals.deterministic.markdown_parser import (
    find_table,
    parse_bullets,
    parse_tables,
)
from scripts.skills.evals.deterministic.result import EvalResult


def validate(text: str, expected: dict, eval_id: str) -> EvalResult:
    result = EvalResult("testware-implementation", eval_id)
    tables = parse_tables(text)
    primary = find_table(
        tables,
        section_contains="対象と根拠",
        required_headers=[
            "対象ref",
            "TC ref・revision／TCなし明示対象",
            "仕様Authority・revision",
            "実装方式",
            "変更対象testware",
            "状態",
        ],
    )
    secondary = find_table(
        tables,
        section_contains="変更前と反映",
        required_headers=[
            "branch／HEAD",
            "許可path",
            "対象pathの前提hash／dirty",
            "隔離workspace",
            "共有先条件付き反映・readback",
            "競合／block",
        ],
    )
    result.add("TW-IMPL-D001", primary is not None, "対象・根拠の表があること")
    result.add(
        "TW-IMPL-D002", secondary is not None, "前提と実績を区別する表があること"
    )
    if primary is not None:
        result.add(
            "TW-IMPL-D003",
            bool(primary.rows)
            and all(
                all(str(value).strip() for value in row.values())
                for row in primary.rows
            ),
            "対象・根拠の必須列を空欄にしないこと",
        )
    if secondary is not None:
        result.add(
            "TW-IMPL-D004",
            bool(secondary.rows)
            and all(
                all(str(value).strip() for value in row.values())
                for row in secondary.rows
            ),
            "変更前・反映の必須列を空欄にしないこと",
        )
    testware = find_table(
        tables,
        section_contains="testwareと検証",
        required_headers=(
            "testware ref／revision",
            "assertion・fixtureの根拠",
            "変更／再利用path",
            "実行した軽量検証と実結果",
            "未実施の理由",
            "独立レビュー先",
        ),
    )
    result.add("TW-IMPL-D005", testware is not None, "testwareと検証の表があること")
    if testware is not None:
        result.add(
            "TW-IMPL-D006",
            bool(testware.rows)
            and all(
                all(str(value).strip() for value in row.values())
                for row in testware.rows
            ),
            "testwareと検証の必須欄を空欄にしないこと",
        )
    handoff = parse_bullets(text)
    handoff_fields = (
        "実runner実行owner",
        "必要な認証・副作用・cleanup・未確定の条件",
        "変更の復旧／再開条件",
        "実run未実施の明示",
    )
    result.add(
        "TW-IMPL-D007",
        "## 引継ぎ" in text
        and all(str(handoff.get(key, "")).strip() for key in handoff_fields),
        "引継ぎのrunner owner・条件・再開・実run状況を明示すること",
    )
    return result
