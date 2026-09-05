from __future__ import annotations

import unittest

from scripts.evals.deterministic.validators import VALIDATORS


class ClosureExclusivityRegressionTests(unittest.TestCase):
    def assert_fails(self, skill: str, text: str, expected: dict, assertion_id: str) -> None:
        result = VALIDATORS[skill](text, expected, "CLOSURE-EXCLUSIVITY").to_dict()
        failed = {assertion["id"] for assertion in result["assertions"] if assertion["status"] == "fail"}
        self.assertIn(assertion_id, failed, result)

    def test_test_requirement_cannot_link_and_dispose_same_upstream(self) -> None:
        text = """# テスト要求
## テスト要求一覧
| テスト要求ID | テスト要求 | Current Effective Authority | 関連Product Risk | 優先度 | テストレベル / 観測方法 |
| --- | --- | --- | --- | --- | --- |
| TR-001 | 保存を検証する | SPEC-001 | RISK-001 | 高 | システム / UI |
## Test Requirementを作らない上流項目
| 上流ID | 種別 | Disposition | 理由 / 根拠 |
| --- | --- | --- | --- |
| SPEC-001 | Authority | 対象外 | 対象外と判断 |
"""
        expected = {
            "known_authorities": ["SPEC-001"],
            "known_product_risks": ["RISK-001"],
        }
        self.assert_fails("test-requirement-design", text, expected, "TR-D009")

    def test_test_condition_cannot_link_and_dispose_same_requirement(self) -> None:
        text = """# テスト観点・条件
## Test Conditionへ展開しないTest Requirement
| テスト要求ID | Disposition | 理由 / 根拠 |
| --- | --- | --- |
| TR-001 | Blocked | 必要情報不足 |
## テスト観点・条件一覧
| 観点ID | テスト要求ID | テスト観点 / 条件 | テスト技法 / 根拠 | Coverage Criteria | 優先度 |
| --- | --- | --- | --- | --- | --- |
| TCN-001 | TR-001 | 保存条件を確認する | 状態遷移 / 状態変化あり | 有効遷移 | 高 |
## Coverage Item一覧
| Coverage Item ID | 観点ID | Coverage Item | 導出元の技法 / 基準 | 期待挙動の根拠 | 優先度 |
| --- | --- | --- | --- | --- | --- |
## Coverage候補のDisposition
| 候補 | 導出元 | Disposition | 理由 / 根拠 | カバー先 |
| --- | --- | --- | --- | --- |
"""
        expected = {"known_test_requirements": ["TR-001"]}
        self.assert_fails("test-condition-design", text, expected, "TCN-D013")

    def test_test_case_cannot_link_and_dispose_same_coverage_item(self) -> None:
        text = """# テストケース
## テストケース一覧
| テストケースID | タイトル / 目的 | 関連観点ID | 関連Coverage Item ID | 関連テスト要求ID | 優先度 | 前提条件 | テストデータ | 実施手順 | 期待結果 | 期待結果の根拠 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| TC-001 | 保存確認 | TCN-001 | TCN-001-CI01 | TR-001 | 高 | ログイン済み | 有効値 | 保存する | 保存済み表示 | SPEC-001 |
## Test Caseへ展開しないCoverage Item / Test Condition
| 上流ID | 種別 | Disposition | 理由 / 根拠 |
| --- | --- | --- | --- |
| TCN-001-CI01 | Coverage Item | 残存リスク | 意図的に未カバー |
"""
        expected = {
            "known_test_conditions": ["TCN-001"],
            "known_coverage_items": ["TCN-001-CI01"],
            "known_test_requirements": ["TR-001"],
            "known_authorities": ["SPEC-001"],
            "coverage_closure_ids": ["TCN-001-CI01"],
        }
        self.assert_fails("test-case-design", text, expected, "TC-D007")


if __name__ == "__main__":
    unittest.main()
