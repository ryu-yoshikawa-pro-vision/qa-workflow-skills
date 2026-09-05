from __future__ import annotations

import unittest

from scripts.evals.deterministic.validators import VALIDATORS


class FixtureContractRegressionTests(unittest.TestCase):
    def assert_fails(self, skill: str, text: str, expected: dict, assertion_id: str) -> None:
        result = VALIDATORS[skill](text, expected, "FIXTURE-CONTRACT").to_dict()
        failed = {a["id"] for a in result["assertions"] if a["status"] == "fail"}
        self.assertIn(assertion_id, failed, result)

    def assert_passes(self, skill: str, text: str, expected: dict) -> None:
        result = VALIDATORS[skill](text, expected, "FIXTURE-CONTRACT").to_dict()
        self.assertEqual(result["status"], "pass", result)

    def test_question_fixture_normalization(self):
        def output(normalization: str) -> str:
            return f"""# 質問分析
## 不明点 / 質問一覧
| ID | 問題 / 質問 | 根拠 | 分類 | 影響範囲 / 成果物 | 回答なしの場合の扱い | 回答後の正規化先 | 再開Skill |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Q-001 | 遷移先画面を確認する | 仕様に記載なし | Blocker | Test Case | 対象範囲を停止 | {normalization} | test-case-design |
## 仮定候補
| 仮定候補 | 状態 | 根拠 / 理由 | 影響範囲 | Canonical ASM ID |
| --- | --- | --- | --- | --- |
## Blocked範囲
| Blocker ID | Blocked成果物 / 範囲 | 必要な決定 / 情報源 | 再開Skill |
| --- | --- | --- | --- |
| Q-001 | Test Case | 遷移先仕様 | test-case-design |
"""

        expected = {"expected_normalizations": {"Q-001": "未確定"}}
        self.assert_passes("question-analysis", output("未確定"), expected)
        self.assert_fails("question-analysis", output("DECISION"), expected, "QUESTION-D016")
        self.assert_passes("question-analysis", output("DECISION"), {})

    def test_test_requirement_fixture_closure_modes(self):
        base = """# Test Requirement
## テスト要求一覧
| テスト要求ID | テスト要求 | Current Effective Authority | 関連Product Risk | 優先度 | テストレベル / 観測方法 |
| --- | --- | --- | --- | --- | --- |
| TR-001 | 保存挙動を検証する | SPEC-001 | RISK-001 / RISK-002 | 高 | システム / UI |
## Test Requirementを作らない上流項目
| 上流ID | 種別 | Disposition | 理由 / 根拠 |
| --- | --- | --- | --- |
| SPEC-002 | Authority | 対象外 | 対象範囲外 |
"""
        expected = {
            "known_authorities": ["SPEC-001", "SPEC-002"],
            "known_product_risks": ["RISK-001", "RISK-002"],
            "product_risk_levels": {"RISK-001": "高", "RISK-002": "中"},
            "required_linked_upstream_ids": ["SPEC-001", "RISK-001", "RISK-002"],
            "expected_dispositions": {"SPEC-002": "対象外"},
        }
        self.assert_passes("test-requirement-design", base, expected)

        risk_disposed = base.replace("RISK-001 / RISK-002", "RISK-001").replace(
            "| SPEC-002 | Authority | 対象外 | 対象範囲外 |",
            "| SPEC-002 | Authority | 対象外 | 対象範囲外 |\n| RISK-002 | Product Risk | 対象外 | 別扱い |",
        )
        self.assert_fails("test-requirement-design", risk_disposed, expected, "TR-D014")

        missing_disposition = base.replace("| SPEC-002 | Authority | 対象外 | 対象範囲外 |\n", "")
        self.assert_fails("test-requirement-design", missing_disposition, expected, "TR-D015")

        wrong_disposition = base.replace("| SPEC-002 | Authority | 対象外 |", "| SPEC-002 | Authority | 残存リスク |")
        self.assert_fails("test-requirement-design", wrong_disposition, expected, "TR-D015")

    def test_test_case_fixture_numbered_authorities(self):
        base = """# Test Case
## テストケース一覧
| テストケースID | タイトル / 目的 | 関連観点ID | 関連Coverage Item ID | 関連テスト要求ID | 優先度 | 前提条件 | テストデータ | 実施手順 | 期待結果 | 期待結果の根拠 | 備考 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| TC-001 | 保存と制御 | TCN-001 | TCN-001-CI01 / TCN-001-CI02 | TR-001 | 高 | ログイン済み | valid | 保存する | 期待結果1: 保存結果が表示される; 期待結果2: 操作制御が表示される | 期待結果1→SPEC-001; 期待結果2→DEC-001 | |
## Test Caseへ展開しないCoverage Item / Test Condition
| 上流ID | 種別 | Disposition | 理由 / 根拠 |
| --- | --- | --- | --- |
"""
        expected = {
            "known_test_requirements": ["TR-001"],
            "known_test_conditions": ["TCN-001"],
            "known_coverage_items": ["TCN-001-CI01", "TCN-001-CI02"],
            "coverage_closure_ids": ["TCN-001-CI01", "TCN-001-CI02"],
            "known_authorities": ["SPEC-001", "DEC-001"],
            "coverage_item_priorities": {"TCN-001-CI01": "中", "TCN-001-CI02": "高"},
            "expected_numbered_authorities": {"TC-001": {"1": ["SPEC-001"], "2": ["DEC-001"]}},
        }
        self.assert_passes("test-case-design", base, expected)

        no_numbers = base.replace("期待結果1: ", "").replace("期待結果2: ", "").replace("期待結果1→", "").replace("期待結果2→", "")
        self.assert_fails("test-case-design", no_numbers, expected, "TC-D011")

        swapped = base.replace("期待結果1→SPEC-001; 期待結果2→DEC-001", "期待結果1→DEC-001; 期待結果2→SPEC-001")
        self.assert_fails("test-case-design", swapped, expected, "TC-D011")

        missing_second = base.replace("; 期待結果2→DEC-001", "")
        self.assert_fails("test-case-design", missing_second, expected, "TC-D011")

    def test_workflow_fixture_downstream_states(self):
        expected = {
            "expected_start_skill": "test-analysis",
            "expected_final_skill": "test-case-design",
            "expected_skills": ["test-analysis", "test-requirement-design", "test-condition-design", "test-case-design"],
            "expected_overall_state": "部分完了（Blockedあり）",
            "expected_skill_states": {
                "test-analysis": "Blocked",
                "test-requirement-design": "完了",
                "test-condition-design": "完了",
                "test-case-design": "完了",
            },
        }

        def output(tcn_state: str = "完了") -> str:
            return f"""- Workflow全体状態: 部分完了（Blockedあり）
- 開始Skill: test-analysis
- 最終Skill: test-case-design
| Skill | 状態 | 成果物 / バージョン | Blocker / 備考 |
| --- | --- | --- | --- |
| test-analysis | Blocked | Risk | 局所Blocked |
| test-requirement-design | 完了 | TR | |
| test-condition-design | {tcn_state} | TCN | |
| test-case-design | 完了 | TC | |
"""

        self.assert_passes("qa-workflow", output(), expected)
        self.assert_fails("qa-workflow", output("Blocked"), expected, "WF-D014")


if __name__ == "__main__":
    unittest.main()
