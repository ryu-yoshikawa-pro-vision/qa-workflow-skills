from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
VALIDATOR_PATH = (
    ROOT / "skills" / "question-analysis" / "evals" / "deterministic" / "validator.py"
)
SPEC = importlib.util.spec_from_file_location(
    "question_analysis_eval_validator", VALIDATOR_PATH
)
assert SPEC is not None and SPEC.loader is not None
validator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validator)


def output(unknown_id: str = "UNK-001") -> str:
    return f"""# 不明点・矛盾分析

## 不明点 / 質問一覧

| ID | 問題 / 質問 | 根拠 | 分類 | 影響範囲 / 成果物 | 関連UNKNOWN ID | Runtime Skill | Runtime Unit Key | Model Key | Target Key | Generation Fingerprint | 回答なしの場合の扱い | 回答後の正規化先 | 再開Skill | 再開対象 / 実行範囲 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Q-001 | 遷移先が不明 | SPEC | 要確認 | login | {unknown_id} | | | | | | 確認まで保留 | SPEC | spec-analysis | |

## 質問ID履歴

| ID |
| --- |
| Q-001 |

## 仮定候補

| 仮定候補 | 状態 | 根拠 / 理由 | 影響範囲 | 正式ASM ID |
| --- | --- | --- | --- | --- |

## ブロック中範囲

| ブロッカーID | ブロック中成果物 / 範囲 | 必要な決定 / 情報源 | Runtime Skill | Runtime Unit Key | Model Key | Target Key | Generation Fingerprint | 再開Skill | 再開対象 / 実行範囲 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
"""


EXPECTED = {
    "require_blocked_for_blockers": False,
    "expected_classifications": {"Q-001": "要確認"},
    "expected_normalizations": {"Q-001": "SPEC"},
    "known_unknown_ids": ["UNK-001"],
    "expected_related_unknowns": {"Q-001": ["UNK-001"]},
    "question_id_history": ["Q-001"],
}


class QuestionAnalysisEvalContractTests(unittest.TestCase):
    def test_fixture_criteria_accept_exact_current_unknown_and_history(self) -> None:
        result = validator.validate(output(), EXPECTED, "QUESTION-OUT-001")
        self.assertEqual(result.status, "pass", result.assertions)

    def test_unknown_link_mismatch_cannot_false_pass(self) -> None:
        result = validator.validate(output("UNK-999"), EXPECTED, "QUESTION-OUT-001")
        assertion = next(row for row in result.assertions if row.id == "QUESTION-D021")
        self.assertEqual(assertion.status, "fail")

    def test_approved_assumption_does_not_require_a_restart_skill(self) -> None:
        text = output()
        q1 = "| Q-001 | 遷移先が不明 | SPEC | 要確認 | login | UNK-001 | | | | | | 確認まで保留 | SPEC | spec-analysis | |"
        q2 = "| Q-002 | JST仮定を適用 | ASM-001が承認済み | 仮定可能 | ASM-001の適用範囲 | | | | | | | 既存承認済みASM-001の範囲で利用 | ASM | 不要（承認済みASM-001） | |"
        text = text.replace(q1, q1 + "\n" + q2)
        text = text.replace("| Q-001 |\n", "| Q-001 |\n| Q-002 |\n")
        text = text.replace(
            "| --- | --- | --- | --- | --- |\n\n## ブロック中範囲",
            "| --- | --- | --- | --- | --- |\n| JSTを適用 | 承認済み | ステークホルダー承認済み | ASM-001の適用範囲 | ASM-001 |\n\n## ブロック中範囲",
        )
        result = validator.validate(text, {}, "QUESTION-APPROVED-ASM").to_dict()
        assertions = {row["id"]: row for row in result["assertions"]}
        self.assertEqual(assertions["QUESTION-D012"]["status"], "pass")
        self.assertEqual(assertions["QUESTION-D005"]["status"], "pass")
        self.assertEqual(assertions["QUESTION-D017"]["status"], "pass")


if __name__ == "__main__":
    unittest.main()
