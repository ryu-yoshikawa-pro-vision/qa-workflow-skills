"""Validate the Project Context owner's human-readable decision summary."""

from __future__ import annotations

from typing import Any

from scripts.skills.evals.deterministic.markdown_parser import parse_bullets
from scripts.skills.evals.deterministic.result import EvalResult

STATES = {
    "existing",
    "absent",
    "unconfirmed",
    "ambiguous",
    "draft",
    "blocked",
    "current",
    "incomplete",
}


def validate(text: str, expected: dict[str, Any], eval_id: str) -> EvalResult:
    result = EvalResult("project-context", eval_id)
    bullets = parse_bullets(text)
    state = bullets.get("判定状態")
    result.add(
        "PC-D001",
        text.startswith("# Project Contextの確認・変更")
        and state in STATES,
        "判断状態と正規出力の見出しがあること",
    )
    for assertion, key in (
        ("PC-D002", "対象案件と許可された探索範囲"),
        ("PC-D003", "既存候補ref／revision／確認状態"),
        ("PC-D004", "既存16節・DEC/ASMと必要stable keyの検証結果"),
        ("PC-D005", "blockedの操作・理由・再開条件"),
    ):
        result.add(
            assertion,
            bool(bullets.get(key)),
            f"{key}を明示すること",
        )
    result.add(
        "PC-D006",
        state == expected.get("status") if "status" in expected else True,
        "fixtureと判断状態が一致すること",
    )
    ref = bullets.get("Project Contextの正本ref／revision", "")
    if state in {"existing", "current"}:
        result.add(
            "PC-D007",
            bool(ref) and ref not in {"未確認", "なし", "UNKNOWN"},
            "currentな既存文書には正本ref／revisionが必要",
        )
    else:
        result.add(
            "PC-D007",
            state not in {"draft", "absent", "unconfirmed", "ambiguous", "blocked", "incomplete"}
            or not ref.startswith("保存済み"),
            "保存未確定の文書を保存済みと表記しないこと",
        )
    storage = bullets.get("native create-if-absent／CAS、履歴再取得、独立readbackの結果", "")
    result.add(
        "PC-D008",
        bool(storage)
        and not (
            state in {"draft", "blocked", "unconfirmed", "absent"}
            and storage in {"保存済み", "成功"}
        ),
        "未保存のdraftと実provider readbackを混同しないこと",
    )
    return result
