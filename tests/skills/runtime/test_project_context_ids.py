from __future__ import annotations

import sys
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[3] / "skills" / "qa-workflow" / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))
from project_context_ids import handle  # noqa: E402

BASE = """# Project Context

## 12. 確定事項（決定事項の正本一覧）

| ID | 確定内容 | 状態 | 決定根拠 | 影響範囲 | 関係 | 関連仕様根拠ID | 置換先ID | 備考 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |

## 13. 仮定（仮定の正本一覧）

| ID | 仮定 | 状態 | 理由 / 根拠 | 承認根拠 | 影響範囲 | 置換先ID | 備考 |
| --- | --- | --- | --- | --- | --- | --- | --- |

## 14. その他

保持する narrative
"""


def dec(action: str, *, reuse_id: str | None = None, draft: str | None = None) -> dict:
    return {
        "draft_key": draft,
        "identity_action": action,
        "reuse_id": reuse_id,
        "cells": {
            "確定内容": "新しい認証動作",
            "状態": "有効",
            "決定根拠": "承認済み資料",
            "影響範囲": "認証画面",
            "関係": "独立",
            "関連仕様根拠ID": ["SPEC-001"],
            "置換先ID": [],
            "備考": "",
        },
    }


class ProjectContextIdsTests(unittest.TestCase):
    def test_create_allocates_canonical_dec_id_and_preserves_other_sections(
        self,
    ) -> None:
        response = handle(
            {
                "operation": "materialize",
                "artifact_mode": "create",
                "previous_artifact_markdown": None,
                "artifact_markdown": BASE,
                "decisions": [dec("new", draft="auth")],
                "assumptions": [],
            }
        )
        self.assertTrue(response["valid"], response)
        self.assertEqual(
            response["payload"]["allocated_ids"],
            [{"draft_key": "auth", "stable_id": "DEC-001"}],
        )
        self.assertIn("保持する narrative", response["payload"]["artifact_markdown"])

    def test_update_preserves_previous_ids_and_allocates_next_number(self) -> None:
        first = handle(
            {
                "operation": "materialize",
                "artifact_mode": "create",
                "previous_artifact_markdown": None,
                "artifact_markdown": BASE,
                "decisions": [dec("new", draft="auth")],
                "assumptions": [],
            }
        )["payload"]["artifact_markdown"]
        updated = handle(
            {
                "operation": "materialize",
                "artifact_mode": "update",
                "previous_artifact_markdown": first,
                "artifact_markdown": BASE,
                "decisions": [
                    dec("reuse", reuse_id="DEC-001"),
                    dec("new", draft="session-expiry"),
                ],
                "assumptions": [],
            }
        )
        self.assertTrue(updated["valid"], updated)
        self.assertEqual(
            updated["payload"]["allocated_ids"],
            [{"draft_key": "session-expiry", "stable_id": "DEC-002"}],
        )

    def test_validate_history_rejects_deleted_previous_identity(self) -> None:
        previous = BASE.replace(
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- |\n\n## 13.",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- |\n| DEC-001 | decision | 有効 | source | scope | 独立 | | | |\n\n## 13.",
        )
        response = handle(
            {
                "operation": "validate-history",
                "previous_artifact_markdown": previous,
                "artifact_markdown": BASE,
            }
        )
        self.assertFalse(response["valid"])
        self.assertEqual(response["payload"]["missing_previous_ids"], ["DEC-001"])

    def test_rejects_id_space_exhaustion(self) -> None:
        previous = BASE.replace(
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- |\n\n## 13.",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- |\n| DEC-999 | terminal | 撤回 | source | scope | 独立 | | | |\n\n## 13.",
        )
        response = handle(
            {
                "operation": "materialize",
                "artifact_mode": "update",
                "previous_artifact_markdown": previous,
                "artifact_markdown": previous,
                "decisions": [
                    dec("reuse", reuse_id="DEC-999"),
                    dec("new", draft="extra"),
                ],
                "assumptions": [],
            }
        )
        self.assertFalse(response["valid"])
        self.assertEqual(response["issues"][0]["issue_type"], "id_space_exhausted")


if __name__ == "__main__":
    unittest.main()
