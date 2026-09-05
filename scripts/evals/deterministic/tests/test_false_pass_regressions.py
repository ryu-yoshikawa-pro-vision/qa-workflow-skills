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
| テスト技法 | 適用領域 | 選択理由 |
| --- | --- | --- |
| 状態遷移 | 保存 | 状態あり |
## テスト可能性 / テストレベル判断
| 要件 / 懸念 | 操作可能か | 観測可能か | 合否判定可能か | 選択テストレベル |
| --- | --- | --- | --- | --- |
| 保存 | 可 | 可 | 可 | システム |
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
| 項目ID | 内容 | 分類 | 情報源 / Canonical Registry参照 |
| --- | --- | --- | --- |
| {item_id} | 内容 | {classification} | SRC-001 |
## Current Effective Authority
| Authority ID | 種別 | 現在有効な内容 | 適用範囲 | 情報源 / Canonical Registry | 関係 |
| --- | --- | --- | --- | --- | --- |
| {authority_id} | {authority_type} | 内容 | 対象 | SRC-001 | 独立 |
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

    def test_spec_required_fields(self):
        base = """# 仕様分析
## 情報源 / Canonical Registry参照一覧
| 参照ID |
| --- |
| SRC-001 |
## 分析項目
| 項目ID | 内容 | 分類 | 情報源 / Canonical Registry参照 |
| --- | --- | --- | --- |
| SPEC-001 | 保存できる | SPEC | SRC-001 |
## Current Effective Authority
| Authority ID | 種別 | 現在有効な内容 | 適用範囲 | 情報源 / Canonical Registry | 関係 |
| --- | --- | --- | --- | --- | --- |
| SPEC-001 | SPEC | 保存できる | 設定 | SRC-001 | 独立 |
"""
        cases = [
            ("| SPEC-001 | 保存できる | SPEC | SRC-001 |", "| SPEC-001 |  | SPEC | SRC-001 |", "SPEC-D014"),
            ("| SPEC-001 | SPEC | 保存できる | 設定 | SRC-001 | 独立 |", "| SPEC-001 | SPEC |  | 設定 | SRC-001 | 独立 |", "SPEC-D015"),
            ("| SPEC-001 | SPEC | 保存できる | 設定 | SRC-001 | 独立 |", "| SPEC-001 | SPEC | 保存できる | 設定 |  | 独立 |", "SPEC-D015"),
        ]
        for old, new, assertion_id in cases:
            with self.subTest(assertion_id=assertion_id, replacement=new):
                self.assert_fails("spec-analysis", base.replace(old, new), {}, assertion_id)

    def _question_base(self) -> str:
        return """# 不明点
## 不明点 / 質問一覧
| ID | 問題 / 質問 | 根拠 | 分類 | 影響範囲 / 成果物 | 回答なしの場合の扱い | 回答後の正規化先 | 再開Skill |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Q-001 | 遷移先が未定義 | SPECに記載なし | Blocker | TC | 対象範囲を停止 | 未確定 | test-case-design |
## 仮定候補
| 仮定候補 | 状態 | 根拠 / 理由 | 影響範囲 | Canonical ASM ID |
| --- | --- | --- | --- | --- |
| JSTとして扱う | 承認済み | ステークホルダー承認 | 日時 | ASM-001 |
## Blocked範囲
| Blocker ID | Blocked成果物 / 範囲 | 必要な決定 / 情報源 | 再開Skill |
| --- | --- | --- | --- |
| Q-001 | TC | 遷移先仕様 | test-case-design |
"""

    def test_question_required_fields_and_blocked_scope(self):
        base = self._question_base()
        cases = [
            ("| Q-001 | 遷移先が未定義 | SPECに記載なし |", "| Q-001 |  | SPECに記載なし |", "QUESTION-D012"),
            ("| Q-001 | 遷移先が未定義 | SPECに記載なし |", "| Q-001 | 遷移先が未定義 |  |", "QUESTION-D012"),
            ("| Q-001 | TC | 遷移先仕様 | test-case-design |", "| Q-001 |  | 遷移先仕様 | test-case-design |", "QUESTION-D013"),
        ]
        for old, new, assertion_id in cases:
            with self.subTest(assertion_id=assertion_id, replacement=new):
                self.assert_fails("question-analysis", base.replace(old, new), {}, assertion_id)

    def test_required_approved_assumption_must_exist(self):
        text = self._question_base().replace("| JSTとして扱う | 承認済み | ステークホルダー承認 | 日時 | ASM-001 |", "")
        expected = {
            "approved_assumptions": {"ASM-001": {"approved": True}},
            "required_approved_assumptions": ["ASM-001"],
        }
        self.assert_fails("question-analysis", text, expected, "QUESTION-D015")

    def _risk_base(self) -> str:
        return """# テスト分析
## Product Risk一覧
| リスクID | 製品上のリスク / 失敗 | 関連Current Effective Authority / 変更 / 依存 | 影響度 | 発生可能性 | レベル | 根拠 |
| --- | --- | --- | --- | --- | --- | --- |
| RISK-001 | 誤保存 | SPEC-001 | 4 | 2 | 高 | 全面変更 |
## 選択したテスト技法
| テスト技法 | 適用領域 | 選択理由 |
| --- | --- | --- |
| 状態遷移 | 保存 | 状態あり |
## テスト可能性 / テストレベル判断
| 要件 / 懸念 | 操作可能か | 観測可能か | 合否判定可能か | 選択テストレベル |
| --- | --- | --- | --- | --- |
| 保存 | 可 | 可 | 可 | システム |
"""

    def test_required_technique_and_testability(self):
        base = self._risk_base()
        self.assert_fails(
            "test-analysis",
            base.replace("| 状態遷移 | 保存 | 状態あり |", ""),
            {"required_techniques": ["状態遷移"]},
            "RISK-D014",
        )
        self.assert_fails(
            "test-analysis",
            base.replace("| 保存 | 可 | 可 | 可 | システム |", ""),
            {"required_testability": {"操作可能か": "可", "観測可能か": "可", "合否判定可能か": "可"}},
            "RISK-D015",
        )
        self.assert_fails(
            "test-analysis",
            base.replace("| 保存 | 可 | 可 | 可 | システム |", "| 保存 | 一部 | 可 | 可 | システム |"),
            {"required_testability": {"操作可能か": "可", "観測可能か": "可", "合否判定可能か": "可"}},
            "RISK-D015",
        )

    def test_technique_and_testability_required_fields(self):
        base = self._risk_base()
        self.assert_fails("test-analysis", base.replace("| 状態遷移 | 保存 | 状態あり |", "| 状態遷移 | 保存 |  |"), {}, "RISK-D012")
        self.assert_fails("test-analysis", base.replace("| 保存 | 可 | 可 | 可 | システム |", "| 保存 | 可 | 可 | 可 |  |"), {}, "RISK-D013")

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

    def test_pairwise_generated_coverage_item_integrity(self):
        text, expected = self._pairwise_base("A=0; B=0")
        ghost = text.replace("| TCN-001-CI01 | A=0; B=0 |", "| TCN-001-CI99 | A=0; B=0 |")
        self.assert_fails("test-condition-design", ghost, expected, "TCN-D026")

        duplicate = text.replace(
            "| TCN-001-CI01 | A=0; B=0 |",
            "| TCN-001-CI01 | A=0; B=0 |\n| TCN-001-CI01 | A=1; B=0 |",
        )
        self.assert_fails("test-condition-design", duplicate, expected, "TCN-D027")

    def test_pairwise_invalid_tokens_and_duplicate_factors(self):
        for combo in ("A=0; invalid-token; B=0", "A=0; A=1; B=0"):
            with self.subTest(combo=combo):
                text, expected = self._pairwise_base(combo)
                self.assert_fails("test-condition-design", text, expected, "TCN-D028")

    def test_pairwise_existing_coverage_check_still_detects_missing_pair(self):
        text, expected = self._pairwise_base("A=0; B=0")
        expected["pairwise"]["forbidden_constraints"] = []
        expected["pairwise"]["require_pairwise"] = True
        self.assert_fails("test-condition-design", text, expected, "TCN-D015")

    def test_state_transition_requires_existing_coverage_item(self):
        text = """# TCN
## Test Conditionへ展開しないTest Requirement
| テスト要求ID | Disposition | 理由 / 根拠 |
| --- | --- | --- |
## テスト観点・条件一覧
| 観点ID | テスト要求ID | テスト観点 / 条件 | テスト技法 / 根拠 | Coverage Criteria | 関連Authority / Product Risk | 優先度 |
| --- | --- | --- | --- | --- | --- | --- |
| TCN-001 | TR-001 | 公開遷移 | 状態遷移 | 全有効遷移 | SPEC-001 | 高 |
## Coverage Item一覧
| Coverage Item ID | 観点ID | Coverage Item | 導出元の技法 / 基準 | 期待挙動の根拠 | 優先度 |
| --- | --- | --- | --- | --- | --- |
| TCN-001-CI01 | TCN-001 | draft→published | 状態遷移 | SPEC-001 | 高 |
## Coverage候補のDisposition
| 候補 | 導出元 | Disposition | 理由 / 根拠 | カバー先 |
| --- | --- | --- | --- | --- |
## 状態遷移表
| 現在状態 | イベント / 操作 | 期待する次状態 / 結果 | 対応Coverage Item ID |
| --- | --- | --- | --- |
| draft | publish | published | TCN-999-CI99 |
"""
        expected = {
            "known_test_requirements": ["TR-001"],
            "known_authorities": ["SPEC-001"],
            "required_transitions": [{"from": "draft", "event": "publish", "to": "published"}],
        }
        self.assert_fails("test-condition-design", text, expected, "TCN-D016")

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
| 指摘ID | 重要度 | 対象成果物 / 位置 | 問題 | 根拠 | 影響 | 推奨修正 | 修正Skill / 層 | 処置 | 処置根拠 / 承認参照 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| REV-001 | 重大 | TC-001 | リスク受容 | Authority | 品質リスク | 承認確認 | test-case-design | 残存リスクとして受容 | APR-999 |
"""
        self.assert_fails("adversarial-review", text, {"known_artifact_ids": ["TC-001"], "approved_risk_acceptances": {"REV-001": "APR-001"}}, "REV-D008")

    def test_adversarial_finding_required_fields(self):
        text = """# Review
## 指摘概要
| 重要度 | 件数 |
| --- | --- |
| 致命的 | 0 |
| 重大 | 1 |
| 軽微 | 0 |
| 提案 | 0 |
## 指摘一覧
| 指摘ID | 重要度 | 対象成果物 / 位置 | 問題 | 根拠 | 影響 | 推奨修正 | 修正Skill / 層 | 処置 | 処置根拠 / 承認参照 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| REV-001 | 重大 | TC-001 |  |  |  | 修正 |  | 未処置 | |
"""
        expected = {"known_artifact_ids": ["TC-001"], "expected_defects": [{"target_id": "TC-001"}]}
        self.assert_fails("adversarial-review", text, expected, "REV-D012")

    def test_workflow_state_invariants(self):
        template = """# Workflow
- Workflow全体状態: {overall}
| Skill | 状態 | 成果物 / バージョン | Blocker / 備考 |
| --- | --- | --- | --- |
| test-case-design | {skill_state} | TC | |
"""
        cases = [
            ("完了", "実行中", "WF-D004"),
            ("部分完了（Blockedあり）", "完了", "WF-D010"),
            ("Blocked", "完了", "WF-D011"),
        ]
        for overall, skill_state, assertion_id in cases:
            with self.subTest(overall=overall, skill_state=skill_state):
                self.assert_fails("qa-workflow", template.format(overall=overall, skill_state=skill_state), {}, assertion_id)

    def test_test_case_priority_override_requires_reason(self):
        base = """# TC
## テストケース一覧
| テストケースID | タイトル / 目的 | 関連観点ID | 関連Coverage Item ID | 関連テスト要求ID | 優先度 | 前提条件 | テストデータ | 実施手順 | 期待結果 | 期待結果の根拠 | 備考 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| TC-001 | 保存 | TCN-001 | TCN-001-CI01 | TR-001 | 中 | 管理者 | 名前=A | 保存 | Aが表示 | SPEC-001 | {note} |
## Test Caseへ展開しないCoverage Item / Test Condition
| 上流ID | 種別 | Disposition | 理由 / 根拠 |
| --- | --- | --- | --- |
"""
        expected = {
            "known_test_conditions": ["TCN-001"],
            "known_coverage_items": ["TCN-001-CI01"],
            "known_test_requirements": ["TR-001"],
            "known_authorities": ["SPEC-001"],
            "coverage_item_priorities": {"TCN-001-CI01": "高"},
        }
        self.assert_fails("test-case-design", base.format(note=""), expected, "TC-D010")
        self.assertEqual(VALIDATORS["test-case-design"](base.format(note="限定的な業務影響のため優先度を下げる"), expected, "OVERRIDE").to_dict()["status"], "pass")

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
