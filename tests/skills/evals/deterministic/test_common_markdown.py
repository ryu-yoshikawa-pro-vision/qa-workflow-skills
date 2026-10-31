from __future__ import annotations

import unittest

from scripts.skills.evals.deterministic.common import fenced_code_blocks, ids_in
from scripts.skills.evals.deterministic.loader import load_validators


class CommonMarkdownTests(unittest.TestCase):
    def test_ids_are_found_next_to_japanese_text_without_matching_substrings(self):
        self.assertEqual(
            ids_in("TC-001の根拠と TCN-001-CI01を確認。XTC-002とTC-003xは不正。"),
            ["TC-001", "TCN-001-CI01"],
        )

    def test_fenced_code_blocks_accept_tildes_and_longer_closing_fence(self):
        self.assertEqual(
            fenced_code_blocks('~~~json\n{"ok":true}\n~~~~\n'),
            [("json", '{"ok":true}')],
        )

    def test_fenced_code_blocks_require_matching_fence_character(self):
        self.assertEqual(fenced_code_blocks("```json\n{}\n~~~\n"), [])

    def test_fenced_code_blocks_report_unlabelled_blocks_without_a_language(self):
        self.assertEqual(fenced_code_blocks("```\ntext\n```\n"), [("", "text")])

    def test_json_artifact_validators_parse_tilde_fences(self):
        validators = load_validators()
        knowledge = validators["qa-knowledge"]("~~~json\n{}\n~~~", {}, "KN-TEST")
        knowledge_assertions = {
            row["id"]: row for row in knowledge.to_dict()["assertions"]
        }
        self.assertEqual(knowledge_assertions["KN-D001"]["status"], "pass")

        regression = validators["regression-testing"](
            '~~~json\n{"artifact_type":"activity"}\n~~~', {}, "REG-TEST"
        )
        regression_assertions = {
            row["id"]: row for row in regression.to_dict()["assertions"]
        }
        self.assertEqual(regression_assertions["REG-D001"]["status"], "pass")

    def test_bva_values_are_recognized_next_to_japanese_text(self):
        text = """## テスト条件へ展開しないテスト要求
| テスト要求ID | 扱い | 理由 / 根拠 |
| --- | --- | --- |
## テスト観点・条件一覧
| 観点ID | テスト要求ID | テスト観点 / 条件 | テスト技法 / 根拠 | カバレッジ基準 | 優先度 |
| --- | --- | --- | --- | --- | --- |
| TCN-001 | TR-001 | 数値境界 | BVA | 整数値100、整数値101 | 高 |
## カバレッジ項目一覧
| カバレッジ項目ID | 観点ID | カバレッジ項目 | 導出元の技法 / 基準 | 期待挙動の根拠 | 優先度 |
| --- | --- | --- | --- | --- | --- |
| TCN-001-CI01 | TCN-001 | 整数値100 | BVA | SPEC-001 | 高 |
| TCN-001-CI02 | TCN-001 | 整数値101 | BVA | SPEC-001 | 高 |
## カバレッジ候補の扱い
| 候補 | 扱い | 理由 / 根拠 | カバー先 |
| --- | --- | --- | --- |
"""
        expected = {"bva": [{"required_values": [100, 101]}]}
        result = load_validators()["test-condition-design"](
            text, expected, "TCN-BVA-TEST"
        ).to_dict()
        assertions = {row["id"]: row for row in result["assertions"]}
        self.assertEqual(assertions["TCN-D017"]["status"], "pass")


if __name__ == "__main__":
    unittest.main()
