"""Validate the feature inventory summary without asserting product-wide completeness."""

from __future__ import annotations

import re
from typing import Any

from scripts.skills.evals.deterministic.markdown_parser import parse_bullets
from scripts.skills.evals.deterministic.result import EvalResult

STATES = {"complete", "incomplete", "blocked", "stale", "idempotent"}
FEATURE_ID = re.compile(r"\bFEAT-\d{3,}\b")
DIFF_ID = re.compile(r"\bDIF-\d{3,}\b")


def validate(text: str, expected: dict[str, Any], eval_id: str) -> EvalResult:
    result = EvalResult("feature-analysis", eval_id)
    bullets = parse_bullets(text)
    status = bullets.get("判定状態")
    result.add(
        "FA-D001",
        text.startswith("# 機能分析と開発差分") and status in STATES,
        "機能分析の判定状態と正規見出しがあること",
    )
    result.add(
        "FA-D002",
        bool(bullets.get("案件・製品"))
        and bool(bullets.get("分析時点・source revision／変更イベント"))
        and bool(bullets.get("機能成果物ref／revision")),
        "案件・イベント・sourceと成果物revisionが明示されること",
    )
    result.add(
        "FA-D003",
        bool(bullets.get("許可された情報源・取得範囲・pagination・revision"))
        and bool(bullets.get("未取得情報源・未知領域と再開条件")),
        "取得範囲と未取得領域が別々に記載されること",
    )
    result.add(
        "FA-D004",
        bool(bullets.get("開発差分分類率（分子IDs／分母IDs・rate）"))
        and bool(bullets.get("確認済み候補の機能対応率（分子IDs／分母IDs・rate）"))
        and bool(bullets.get("未分類と分母0・未知領域")),
        "指標・ID母集団・未解決を明示すること",
    )
    guarantee = bullets.get("製品全機能の発見保証", "")
    result.add(
        "FA-D005",
        guarantee in {"未判定", "保証しない", "未確認"},
        "情報源を完全取得しても製品全体の発見を保証しないこと",
    )
    result.add(
        "FA-D006",
        status == expected.get("status") if "status" in expected else True,
        "fixtureと判断状態が一致すること",
    )
    feature_ids = set(FEATURE_ID.findall(text))
    difference_ids = set(DIFF_ID.findall(text))
    result.add(
        "FA-D007",
        set(expected.get("feature_ids", [])) <= feature_ids,
        "期待された機能IDが人間向け出力から追跡できること",
    )
    result.add(
        "FA-D008",
        set(expected.get("unclassified_difference_ids", [])) <= difference_ids,
        "未分類差分のIDが欠落しないこと",
    )
    storage = bullets.get("providerのCAS・履歴・readback・承認の結果", "")
    result.add(
        "FA-D009",
        bool(storage)
        and not (
            status in {"blocked", "stale", "incomplete"}
            and storage in {"保存済み", "成功"}
        ),
        "未検証の保存・承認を成功としないこと",
    )
    return result
