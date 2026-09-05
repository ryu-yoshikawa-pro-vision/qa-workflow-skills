from __future__ import annotations

import unittest

from scripts.skills.evals.deterministic.loader import load_validators


VALIDATORS = load_validators()


class DeterministicValidatorTests(unittest.TestCase):
    def assert_pass(self, skill: str, text: str, expected: dict) -> None:
        result = VALIDATORS[skill](text, expected, "UNIT").to_dict()
        self.assertEqual(result["status"], "pass", result)

    def assert_fails(self, skill: str, text: str, expected: dict, assertion_id: str) -> None:
        result = VALIDATORS[skill](text, expected, "UNIT").to_dict()
        failed = {a["id"] for a in result["assertions"] if a["status"] == "fail"}
        self.assertIn(assertion_id, failed, result)

    def test_spec_analysis_valid_and_duplicate_id(self):
        valid = """# 仕様分析
## 情報源 / Canonical Registry参照一覧
| 参照ID | 情報源 / Canonical Registry | 権威 / 優先順位 | 鮮度 / バージョン | 対象範囲 | 参照 / 備考 |
| --- | --- | --- | --- | --- | --- |
| SRC-001 | 要件書 | 正本 | v1 | 設定 | - |
## 分析項目
| 項目ID | カテゴリ | 内容 | 分類 | 情報源 / Canonical Registry参照 | 現在有効か | 補足 / 上書き / 置換関係 | 備考 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| SPEC-001 | 保存 | 保存できる | SPEC | SRC-001 | Yes | 独立 | - |
## Current Effective Authority
| Authority ID | 種別 | 現在有効な内容 | 適用範囲 | 情報源 / Canonical Registry | 関係 | 関連Authority ID |
| --- | --- | --- | --- | --- | --- | --- |
| SPEC-001 | SPEC | 保存できる | 設定 | SRC-001 | 独立 | |
"""
        self.assert_pass("spec-analysis", valid, {"known_authorities": []})
        invalid = valid.replace("| SPEC-001 | 保存 | 保存できる | SPEC | SRC-001 | Yes | 独立 | - |", "| SPEC-001 | 保存 | 保存できる | SPEC | SRC-001 | Yes | 独立 | - |\n| SPEC-001 | 保存2 | 保存できる | SPEC | SRC-001 | Yes | 独立 | - |")
        self.assert_fails("spec-analysis", invalid, {}, "SPEC-D003")

    def test_question_analysis_valid_and_missing_blocked(self):
        valid = """# 不明点
## 不明点 / 質問一覧
| ID | 問題 / 質問 | 根拠 | 分類 | 影響範囲 / 成果物 | 回答なしの場合の扱い | 回答後の正規化先 | 再開Skill |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Q-001 | 遷移先不明 | SPECなし | Blocker | TC | 停止 | 未確定 | test-case-design |
## 仮定候補
| 仮定候補 | 状態 | 根拠 / 理由 | 影響範囲 | Canonical ASM ID |
| --- | --- | --- | --- | --- |
## Blocked範囲
| Blocker ID | Blocked成果物 / 範囲 | 必要な決定 / 情報源 | 再開Skill |
| --- | --- | --- | --- |
| Q-001 | TC | 仕様決定 | test-case-design |
"""
        self.assert_pass("question-analysis", valid, {"require_blocked_for_blockers": True})
        invalid = valid.replace("| Q-001 | TC | 仕様決定 | test-case-design |", "")
        self.assert_fails("question-analysis", invalid, {"require_blocked_for_blockers": True}, "QUESTION-D006")

    def test_test_analysis_risk_matrix(self):
        valid = """# テスト分析
## Product Risk一覧
| リスクID | 製品上のリスク / 失敗 | 関連Current Effective Authority / 変更 / 依存 | 影響度 | 発生可能性 | レベル | 根拠 | 判断信頼度 / 備考 |
| --- | --- | --- | ---: | ---: | --- | --- | --- |
| RISK-001 | 誤保存 | SPEC-001 | 4 | 2 | 高 | 全面変更 | 高 |
## 選択したテスト技法
| テスト技法 | 適用領域 | 選択理由 | 関連Product Risk / Current Effective Authority | `test-condition-design`への着眼点 |
| --- | --- | --- | --- | --- |
| 状態遷移 | 保存 | 状態あり | RISK-001 | 遷移 |
## テスト可能性 / テストレベル判断
| 要件 / 懸念 | 操作可能か | 観測可能か | 合否判定可能か | 選択テストレベル | 扱い / 備考 |
| --- | --- | --- | --- | --- | --- |
| 保存 | 可 | 可 | 可 | システム | 現在レベル |
"""
        self.assert_pass("test-analysis", valid, {"known_authorities": ["SPEC-001"]})
        invalid = valid.replace("| 4 | 2 | 高 |", "| 4 | 2 | 中 |")
        self.assert_fails("test-analysis", invalid, {"known_authorities": ["SPEC-001"]}, "RISK-D005")

    def test_test_requirement_valid_and_unknown_reference(self):
        valid = """# TR
## テスト要求一覧
| テスト要求ID | テスト要求 | Current Effective Authority | 関連Product Risk | 優先度 | テストレベル / 観測方法 | 備考 |
| --- | --- | --- | --- | --- | --- | --- |
| TR-001 | 保存を保証 | SPEC-001 | RISK-001 | 高 | システム / UI | |
## Test Requirementを作らない上流項目
| 上流ID | 種別 | Disposition | 理由 / 根拠 |
| --- | --- | --- | --- |
"""
        exp = {"known_authorities":["SPEC-001"],"known_product_risks":["RISK-001"],"product_risk_levels":{"RISK-001":"高"}}
        self.assert_pass("test-requirement-design", valid, exp)
        invalid = valid.replace("SPEC-001", "SPEC-999")
        self.assert_fails("test-requirement-design", invalid, exp, "TR-D003")

    def test_test_condition_pairwise_valid_and_missing_pair(self):
        base = """# TCN
## Test Conditionへ展開しないTest Requirement
| テスト要求ID | Disposition | 理由 / 根拠 |
| --- | --- | --- |
## テスト観点・条件一覧
| 観点ID | テスト要求ID | テスト観点 / 条件 | カテゴリ | テスト技法 / 根拠 | Coverage Criteria | 関連Authority / Product Risk | 優先度 | 備考 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| TCN-001 | TR-001 | 組合せ | 組合せ | Pairwise | 全2-wise | SPEC-001 / RISK-001 | 高 | |
## Coverage Item一覧
| Coverage Item ID | 観点ID | Coverage Item | 導出元の技法 / 基準 | 期待挙動の根拠 | 優先度 | 備考 |
| --- | --- | --- | --- | --- | --- | --- |
| TCN-001-CI01 | TCN-001 | combo1 | Pairwise | SPEC-001 | 高 | |
| TCN-001-CI02 | TCN-001 | combo2 | Pairwise | SPEC-001 | 高 | |
| TCN-001-CI03 | TCN-001 | combo3 | Pairwise | SPEC-001 | 高 | |
| TCN-001-CI04 | TCN-001 | combo4 | Pairwise | SPEC-001 | 高 | |
## Coverage候補のDisposition
| 候補 | 導出元 | Disposition | 理由 / 根拠 | カバー先 |
| --- | --- | --- | --- | --- |
## Factor / Value / Constraint
| Factor | Value | 制約 / 備考 |
| --- | --- | --- |
| A | 0 | |
| A | 1 | |
| B | 0 | |
| B | 1 | |
| C | 0 | |
| C | 1 | |
## 生成組合せ
| Coverage Item ID | 組合せ | 備考 |
| --- | --- | --- |
| TCN-001-CI01 | A=0; B=0; C=0 | |
| TCN-001-CI02 | A=0; B=1; C=1 | |
| TCN-001-CI03 | A=1; B=0; C=1 | |
| TCN-001-CI04 | A=1; B=1; C=0 | |
"""
        exp={"known_test_requirements":["TR-001"],"known_authorities":["SPEC-001"],"known_product_risks":["RISK-001"],"pairwise":{"factors":{"A":["0","1"],"B":["0","1"],"C":["0","1"]},"forbidden_constraints":[],"require_pairwise":True}}
        self.assert_pass("test-condition-design",base,exp)
        invalid=base.replace("| TCN-001-CI04 | A=1; B=1; C=0 | |","")
        self.assert_fails("test-condition-design",invalid,exp,"TCN-D015")

    def test_test_case_valid_and_unclosed_coverage(self):
        valid="""# TC
## テストケース一覧
| テストケースID | タイトル / 目的 | 関連観点ID | 関連Coverage Item ID | 関連テスト要求ID | 優先度 | 前提条件 | テストデータ | 実施手順 | 期待結果 | 期待結果の根拠 | 事後状態 / 後処理 | 備考 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| TC-001 | 保存 | TCN-001 | TCN-001-CI01 | TR-001 | 高 | 管理者 | 名前=A | 保存を押す | 設定一覧にAが表示される | 期待結果1→SPEC-001 | 不要 | |
## Test Caseへ展開しないCoverage Item / Test Condition
| 上流ID | 種別 | Disposition | 理由 / 根拠 |
| --- | --- | --- | --- |
"""
        exp={"known_test_requirements":["TR-001"],"known_test_conditions":["TCN-001"],"known_coverage_items":["TCN-001-CI01"],"coverage_closure_ids":["TCN-001-CI01"],"known_authorities":["SPEC-001"],"coverage_item_priorities":{"TCN-001-CI01":"高"}}
        self.assert_pass("test-case-design",valid,exp)
        bad=dict(exp); bad["known_coverage_items"]=["TCN-001-CI01","TCN-001-CI02"]; bad["coverage_closure_ids"]=["TCN-001-CI01","TCN-001-CI02"]
        self.assert_fails("test-case-design",valid,bad,"TC-D007")

    def test_coverage_analysis_valid_and_missed_gap(self):
        graph={"node_types":{"SPEC-001":"Authority","TR-001":"TR","TCN-001":"TCN","TCN-001-CI01":"CI"},"edges":[["SPEC-001","TR-001"],["TR-001","TCN-001"],["TCN-001","TCN-001-CI01"]],"dispositions":{}}
        valid="""# Coverage
## Authority / Product Riskの閉鎖状況
| 上流ID | 種別 | 接続先Test Requirement / Disposition | 状態 | 根拠 / ギャップ |
| --- | --- | --- | --- | --- |
| SPEC-001 | Authority | TR-001 | 閉鎖 | |
## Coverage ItemのDisposition
| Coverage Item ID / 項目 | 観点ID | Disposition | 対応テストケースID / 扱い | 根拠 / 備考 |
| --- | --- | --- | --- | --- |
| TCN-001-CI01 | TCN-001 | テストケース | なし | 未閉鎖 ギャップ |
## カバレッジマトリクス
| 上流層 | 上流ID / 挙動 | 下流層 | 下流ID / Disposition | カバレッジ | Product Risk / 優先度 | 根拠 / ギャップ | 推奨対応 | 修正Skill / 層 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| CI | TCN-001-CI01 | TC | なし | 未網羅 | | Test Caseなし | ケース化 | test-condition-design |
"""
        self.assert_pass("coverage-analysis",valid,{"graph":graph,"expected_fix_skills":{"TCN-001-CI01":"test-condition-design"}})
        invalid=valid.replace("未閉鎖 ギャップ","閉鎖").replace("未網羅","網羅済み").replace("Test Caseなし","問題なし")
        self.assert_fails("coverage-analysis",invalid,{"graph":graph},"COV-D002")

    def test_adversarial_review_valid_and_fatal_residual(self):
        valid="""# Review
## 指摘概要
| 重要度 | 件数 |
| --- | ---: |
| 致命的 | 0 |
| 重大 | 1 |
| 軽微 | 0 |
| 提案 | 0 |
## 指摘一覧
| 指摘ID | 重要度 | 対象成果物 / 位置 | 問題 | 根拠 | 影響 | 推奨修正 | 修正Skill / 層 | 処置 | 処置根拠 / 承認参照 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| REV-001 | 重大 | TC-001 | Authority参照不明 | Authority | Oracle不明 | 修正 | test-case-design | 修正済み | |
"""
        exp={"known_artifact_ids":["TC-001"],"expected_defects":[{"target_id":"TC-001","contains":"Authority"}]}
        self.assert_pass("adversarial-review",valid,exp)
        invalid=valid.replace("| 致命的 | 0 |","| 致命的 | 1 |").replace("| 重大 | 1 |","| 重大 | 0 |").replace("| REV-001 | 重大 |","| REV-001 | 致命的 |").replace("| 修正済み |","| 残存リスクとして受容 |")
        self.assert_fails("adversarial-review",invalid,exp,"REV-D007")

    def test_workflow_valid_and_complete_with_blocked(self):
        valid="""# Workflow
- Workflow全体状態: 実行中
- 開始Skill: test-case-design
- 最終Skill: test-case-design
| Skill | 状態 | 成果物 / バージョン | Blocker / 備考 |
| --- | --- | --- | --- |
| test-case-design | 実行中 | TC | |
"""
        exp={"expected_start_skill":"test-case-design","expected_final_skill":"test-case-design","expected_skills":["test-case-design"]}
        self.assert_pass("qa-workflow",valid,exp)
        invalid=valid.replace("Workflow全体状態: 実行中","Workflow全体状態: 完了").replace("| test-case-design | 実行中 |","| test-case-design | Blocked |")
        self.assert_fails("qa-workflow",invalid,exp,"WF-D004")


if __name__ == "__main__":
    unittest.main()
