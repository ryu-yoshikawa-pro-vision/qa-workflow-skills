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


if __name__ == "__main__":
    unittest.main()
