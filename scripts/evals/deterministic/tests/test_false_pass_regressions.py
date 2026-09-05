from __future__ import annotations

import unittest

from scripts.evals.deterministic.markdown_parser import parse_tables
from scripts.evals.deterministic.validators import VALIDATORS


class FalsePassRegressionTests(unittest.TestCase):
    def assert_fails(self, skill: str, text: str, expected: dict, assertion_id: str) -> None:
        result = VALIDATORS[skill](text, expected, "REGRESSION").to_dict()
        failed = {a["id"] for a in result["assertions"] if a["status"] == "fail"}
        self.assertIn(assertion_id, failed, result)

    def test_empty_output_fails_for_all_skills(self):
        for skill in VALIDATORS:
            with self.subTest(skill=skill):
                result = VALIDATORS[skill]("", {}, "EMPTY").to_dict()
                self.assertEqual(result["status"], "fail", result)

    def test_required_table_missing(self):
        text = """# 仕様分析
## 分析項目
| 項目ID | 分類 |
| --- | --- |
| SPEC-001 | SPEC |
## Current Effective Authority
| Authority ID | 種別 |
| --- | --- |
| SPEC-001 | SPEC |
"""
        self.assert_fails("spec-analysis", text, {}, "SPEC-D012")

    def test_required_entity_missing(self):
        text = """# テスト分析
## Product Risk一覧
| リスクID | 製品上のリスク / 失敗 | 関連Current Effective Authority / 変更 / 依存 | 影響度 | 発生可能性 | レベル | 根拠 |
| --- | --- | --- | --- | --- | --- | --- |
## 選択したテスト技法
| テスト技法 |
| --- |
## テスト可能性 / テストレベル判断
| 要件 / 懸念 | 操作可能か | 観測可能か | 合否判定可能か |
| --- | --- | --- | --- |
"""
        self.assert_fails("test-analysis", text, {"required_risks": {"RISK-001": {"impact": 4, "likelihood": 2, "risk_level": "高"}}}, "RISK-D011")

    def test_expected_missing_vs_explicit_empty_set(self):
        text = """# テスト分析
## Product Risk一覧
| リスクID | 製品上のリスク / 失敗 | 関連Current Effective Authority / 変更 / 依存 | 影響度 | 発生可能性 | レベル | 根拠 |
| --- | --- | --- | --- | --- | --- | --- |
| RISK-001 | 誤保存 | SPEC-001 | 4 | 2 | 高 | 変更 |
## 選択したテスト技法
| テスト技法 |
| --- |
| 状態遷移 |
## テスト可能性 / テストレベル判断
| 要件 / 懸念 | 操作可能か | 観測可能か | 合否判定可能か |
| --- | --- | --- | --- |
| 保存 | 可 | 可 | 可 |
"""
        self.assertEqual(VALIDATORS["test-analysis"](text, {}, "UNSPEC").to_dict()["status"], "pass")
        self.assert_fails("test-analysis", text, {"known_authorities": []}, "RISK-D006")

    def test_spec_current_authority_rejects_inf_unk_and_type_mismatch(self):
        base = """# 仕様分析
## 情報源 / Canonical Registry参照一覧
| 参照ID |
| --- |
| SRC-001 |
## 分析項目
| 項目ID | 分類 | 情報源 / Canonical Registry参照 |
| --- | --- | --- |
| {item_id} | {classification} | SRC-001 |
## Current Effective Authority
| Authority ID | 種別 | 関係 |
| --- | --- | --- |
| {authority_id} | {authority_type} | 独立 |
"""
        cases = [
            ("INF-001", "INFERENCE", "INF-001", "SPEC"),
            ("UNK-001", "UNKNOWN", "UNK-001", "SPEC"),
            ("SPEC-001", "SPEC", "SPEC-001", "DECISION"),
        ]
        for item_id, classification, authority_id, authority_type in cases:
            with self.subTest(item_id=item_id, authority_type=authority_type):
                text = base.format(item_id=item_id, classification=classification, authority_id=authority_id, authority_type=authority_type)
                self.assert_fails("spec-analysis", text, {"known_authorities": [authority_id]}, "SPEC-D010")

    def _pairwise_base(self, combination: str) -> tuple[str, dict]:
        text = f"""# TCN
## Test Conditionへ展開しないTest Requirement
| テスト要求ID | Disposition | 理由 / 根拠 |
| --- | --- | --- |
## テスト観点・条件一覧
| 観点ID | テスト要求ID | テスト観点 / 条件 | テスト技法 / 根拠 | Coverage Criteria | 優先度 |
| --- | --- | --- | --- | --- | --- |
| TCN-001 | TR-001 | 組合せ | Pairwise | 全2-wise | 高 |
## Coverage Item一覧
| Coverage Item ID | 観点ID | Coverage Item | 導出元の技法 / 基準 | 期待挙動の根拠 | 優先度 |
| --- | --- | --- | --- | --- | --- |
| TCN-001-CI01 | TCN-001 | combo | Pairwise | SPEC-001 | 高 |
## Coverage候補のDisposition
| 候補 | 導出元 | Disposition | 理由 / 根拠 | カバー先 |
| --- | --- | --- | --- | --- |
## Factor / Value / Constraint
| Factor | Value |
| --- | --- |
| A | 0 |
| A | 1 |
| B | 0 |
| B | 1 |
## 生成組合せ
| Coverage Item ID | 組合せ |
| --- | --- |
| TCN-001-CI01 | {combination} |
"""
        expected = {"known_test_requirements": ["TR-001"], "known_authorities": ["SPEC-001"], "pairwise": {"factors": {"A": ["0", "1"], "B": ["0", "1"]}, "forbidden_constraints": [{"A": "1", "B": "1"}], "require_pairwise": False}}
        return text, expected

    def test_pairwise_invalid_generated_combinations(self):
        for combo, assertion_id in [
            ("A=0; B=0; Foo=x", "TCN-D018"),
            ("A=2; B=0", "TCN-D019"),
            ("A=1; B=1", "TCN-D020"),
            ("A=0", "TCN-D021"),
        ]:
            with self.subTest(combo=combo):
                text, expected = self._pairwise_base(combo)
                self.assert_fails("test-condition-design", text, expected, assertion_id)

    def test_pairwise_existing_coverage_check_still_detects_missing_pair(self):
        text, expected = self._pairwise_base("A=0; B=0")
        expected["pairwise"]["forbidden_constraints"] = []
        expected["pairwise"]["require_pairwise"] = True
        self.assert_fails("test-condition-design", text, expected, "TCN-D015")

    def test_coverage_expected_fix_target_must_exist(self):
        text = """# Coverage
## カバレッジマトリクス
| 上流層 | 上流ID / 挙動 | 下流層 | 下流ID / Disposition | カバレッジ | 修正Skill / 層 |
| --- | --- | --- | --- | --- | --- |
| TR | TR-001 | TCN | TCN-001 | 網羅済み | test-condition-design |
"""
        self.assert_fails("coverage-analysis", text, {"expected_fix_skills": {"TCN-001-CI01": "test-condition-design"}}, "COV-D005")

    def test_major_residual_acceptance_must_match_fixture_approval(self):
        text = """# Review
## 指摘概要
| 重要度 | 件数 |
| --- | --- |
| 致命的 | 0 |
| 重大 | 1 |
| 軽微 | 0 |
| 提案 | 0 |
## 指摘一覧
| 指摘ID | 重要度 | 対象成果物 / 位置 | 修正Skill / 層 | 処置 | 処置根拠 / 承認参照 |
| --- | --- | --- | --- | --- | --- |
| REV-001 | 重大 | TC-001 | test-case-design | 残存リスクとして受容 | APR-999 |
"""
        self.assert_fails("adversarial-review", text, {"known_artifact_ids": ["TC-001"], "approved_risk_acceptances": {"REV-001": "APR-001"}}, "REV-D008")

    def test_parser_supports_escaped_pipe(self):
        tables = parse_tables("""## T
| A | B |
| --- | --- |
| x\\|y | z |
""")
        self.assertEqual(tables[0].rows[0]["A"], "x|y")

    def test_parser_rejects_column_mismatch(self):
        with self.assertRaises(ValueError):
            parse_tables("""## T
| A | B |
| --- | --- |
| 1 | 2 | 3 |
""")


if __name__ == "__main__":
    unittest.main()
