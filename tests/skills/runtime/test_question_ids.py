from __future__ import annotations

import sys
import unittest
from pathlib import Path

SCRIPT_DIR = (
    Path(__file__).resolve().parents[3] / "skills" / "question-analysis" / "scripts"
)
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(SCRIPT_DIR))
from question_ids import handle  # noqa: E402

QUESTION_TABLE = """| ID | 問題 / 質問 | 根拠 | 分類 | 影響範囲 / 成果物 | 関連UNKNOWN ID | Runtime Skill | Runtime Unit Key | Model Key | Target Key | Generation Fingerprint | 回答なしの場合の扱い | 回答後の正規化先 | 再開Skill | 再開対象 / 実行範囲 |
| --- | ---------- | ---- | ---- | ----------------- | -------------- | ------------- | ---------------- | --------- | ---------- | ---------------------- | -------------------- | ---------------- | --------- | ------------------- |"""
HISTORY_TABLE = """| ID |
| --- |"""


def artifact(question_rows: str = "", history_rows: str = "") -> str:
    return (
        "# Questions\n\n## 不明点 / 質問一覧\n\n"
        + QUESTION_TABLE
        + ("\n" + question_rows if question_rows else "")
        + "\n\n## 質問ID履歴\n\n"
        + HISTORY_TABLE
        + ("\n" + history_rows if history_rows else "")
        + "\n\n## 仮定候補\n\n本文\n"
    )


def question(
    action: str,
    *,
    reuse_id: str | None = None,
    draft_key: str | None = None,
    unknown_id: str = "UNK-001",
) -> dict:
    return {
        "draft_key": draft_key,
        "identity_action": action,
        "reuse_id": reuse_id,
        "cells": {
            "問題 / 質問": "ログイン権限が未確定",
            "根拠": "spec-analysis UNKNOWN",
            "分類": "ブロッカー",
            "影響範囲 / 成果物": "認証画面",
            "関連UNKNOWN ID": [unknown_id],
            "Runtime Skill": "",
            "Runtime Unit Key": "",
            "Model Key": "",
            "Target Key": "",
            "Generation Fingerprint": "",
            "回答なしの場合の扱い": "回答まで該当範囲を停止",
            "回答後の正規化先": "SPEC",
            "再開Skill": "spec-analysis",
            "再開対象 / 実行範囲": "認証",
        },
    }


class QuestionIdTests(unittest.TestCase):
    def test_default_output_template_is_accepted_by_materialize(self) -> None:
        template = (
            ROOT / "skills" / "question-analysis" / "assets" / "output-template.md"
        ).read_text(encoding="utf-8")
        response = handle(
            {
                "operation": "materialize",
                "artifact_mode": "create",
                "previous_artifact_markdown": None,
                "artifact_markdown": template,
                "current_unknown_ids": [],
                "resolved_unknown_ids": [],
                "questions": [],
            }
        )
        self.assertTrue(response["valid"], response)
        self.assertIn("## 質問ID履歴", response["payload"]["artifact_markdown"])

    def test_materialize_allocates_and_validates_unknown_links(self) -> None:
        response = handle(
            {
                "operation": "materialize",
                "artifact_mode": "create",
                "previous_artifact_markdown": None,
                "artifact_markdown": artifact(),
                "current_unknown_ids": ["UNK-001"],
                "resolved_unknown_ids": [],
                "questions": [question("new", draft_key="login-role")],
            }
        )
        self.assertTrue(response["valid"], response)
        self.assertEqual(
            response["payload"]["allocated_ids"],
            [{"draft_key": "login-role", "question_id": "Q-001"}],
        )
        self.assertEqual(response["payload"]["used_question_ids"], ["Q-001"])
        self.assertIn("| Q-001 |", response["payload"]["artifact_markdown"])

    def test_resolved_question_id_is_not_reused_after_current_table_clears(
        self,
    ) -> None:
        first = handle(
            {
                "operation": "materialize",
                "artifact_mode": "create",
                "previous_artifact_markdown": None,
                "artifact_markdown": artifact(),
                "current_unknown_ids": ["UNK-001"],
                "resolved_unknown_ids": [],
                "questions": [question("new", draft_key="first")],
            }
        )["payload"]["artifact_markdown"]
        cleared = handle(
            {
                "operation": "materialize",
                "artifact_mode": "update",
                "previous_artifact_markdown": first,
                "artifact_markdown": artifact(),
                "current_unknown_ids": [],
                "resolved_unknown_ids": ["UNK-001"],
                "questions": [],
            }
        )["payload"]["artifact_markdown"]
        resumed = handle(
            {
                "operation": "materialize",
                "artifact_mode": "update",
                "previous_artifact_markdown": cleared,
                "artifact_markdown": artifact(),
                "current_unknown_ids": ["UNK-002"],
                "resolved_unknown_ids": [],
                "questions": [
                    question("new", draft_key="second", unknown_id="UNK-002")
                ],
            }
        )
        self.assertEqual(
            resumed["payload"]["allocated_ids"],
            [{"draft_key": "second", "question_id": "Q-002"}],
        )

    def test_validate_links_rejects_resolved_only_unknown(self) -> None:
        markdown = artifact(
            "| Q-001 | question | source | 要確認 | scope | UNK-002 | | | | | | | SPEC | spec-analysis | |",
            "| Q-001 |",
        )
        response = handle(
            {
                "operation": "validate-links",
                "artifact_markdown": markdown,
                "current_unknown_ids": [],
                "resolved_unknown_ids": ["UNK-002"],
            }
        )
        self.assertFalse(response["valid"])
        self.assertEqual(response["issues"][0]["issue_type"], "resolved_only_unknown")

    def test_rejects_q_id_exhaustion_without_expanding_number_width(self) -> None:
        previous = artifact(history_rows="| Q-999 |")
        response = handle(
            {
                "operation": "materialize",
                "artifact_mode": "update",
                "previous_artifact_markdown": previous,
                "artifact_markdown": artifact(),
                "current_unknown_ids": ["UNK-001"],
                "resolved_unknown_ids": [],
                "questions": [question("new", draft_key="last")],
            }
        )
        self.assertFalse(response["valid"])
        self.assertEqual(response["issues"][0]["issue_type"], "id_space_exhausted")


if __name__ == "__main__":
    unittest.main()
