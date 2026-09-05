from __future__ import annotations

import unittest

from scripts.evals.deterministic.markdown_parser import parse_tables
from scripts.evals.deterministic.validators import VALIDATORS


class FalsePassRegressionTests(unittest.TestCase):
    def assert_fails(self, skill: str, text: str, expected: dict, assertion_id: str) -> None:
        result = VALIDATORS[skill](text, expected, "REGRESSION").to_dict()
        failed = {a["id"] for a in result["assertions"] if a["status"] == "fail"}
        self.assertIn(assertion_id, failed, result)

    def assert_passes(self, skill: str, text: str, expected: dict) -> None:
        result = VALIDATORS[skill](text, expected, "REGRESSION").to_dict()
        self.assertEqual(result["status"], "pass", result)

    def _spec_base(self) -> str:
        return """# 仕様分析
## 情報源 / Canonical Registry参照一覧
| 参照ID | 情報源 / Canonical Registry |
| --- | --- |
| SRC-001 | 要件書 |
## 分析項目
| 項目ID | 内容 | 分類 | 情報源 / Canonical Registry参照 |
| --- | --- | --- | --- |
| SPEC-001 | 保存できる | SPEC | SRC-001 |
## Current Effective Authority
| Authority ID | 種別 | 現在有効な内容 | 適用範囲 | 情報源 / Canonical Registry | 関係 | 関連Authority ID |
| --- | --- | --- | --- | --- | --- | --- |
| SPEC-001 | SPEC | 保存できる | 保存画面 | SRC-001 | 独立 | |
"""

    def _question_base(self) -> str:
        return """# 質問分析
## 不明点 / 質問一覧
| ID | 問題 / 質問 | 根拠 | 分類 | 影響範囲 / 成果物 | 回答なしの場合の扱い | 回答後の正規化先 | 再開Skill |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Q-001 | 保存条件を確認する | 仕様に記載なし | Blocker | Test Requirement | 対象範囲を停止 | DECISION | spec-analysis |
## 仮定候補
| 仮定候補 | 状態 | 根拠 / 理由 | 影響範囲 | Canonical ASM ID |
| --- | --- | --- | --- | --- |
| タイムゾーンはJST | 承認済み | ステークホルダー承認 | 日時表示 | ASM-001 |
## Blocked範囲
| Blocker ID | Blocked成果物 / 範囲 | 必要な決定 / 情報源 | 再開Skill |
| --- | --- | --- | --- |
| Q-001 | Test Requirement | 保存条件の決定 | spec-analysis |
"""

    def _risk_base(self) -> str:
        return """# テスト分析
## Product Risk一覧
| リスクID | 製品上のリスク / 失敗 | 関連Current Effective Authority / 変更 / 依存 | 影響度 | 発生可能性 | レベル | 根拠 |
| --- | --- | --- | --- | --- | --- | --- |
| RISK-001 | 誤保存 | SPEC-001 / CHG-001 | 4 | 2 | 高 | 保存処理の変更 |
## 選択したテスト技法
| テスト技法 | 適用領域 | 選択理由 |
| --- | --- | --- |
| 状態遷移 | 保存状態 | 状態変化を確認するため |
## テスト可能性 / テストレベル判断
| 要件 / 懸念 | 操作可能か | 観測可能か | 合否判定可能か | 選択テストレベル | 扱い / 備考 |
| --- | --- | --- | --- | --- | --- |
| 保存 | 可 | 可 | 可 | システムテスト | 現在レベル |
"""

    def _pairwise_base(self, combination: str = "A=0; B=0") -> tuple[str, dict]:
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
        expected = {
            "known_test_requirements": ["TR-001"],
            "known_authorities": ["SPEC-001"],
            "pairwise": {
                "factors": {"A": ["0", "1"], "B": ["0", "1"]},
                "forbidden_constraints": [{"A": "1", "B": "1"}],
                "require_pairwise": False,
            },
        }
        return text, expected

    def _review_base(self, repair_target: str = "test-case-design") -> str:
        return f"""# Review
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
| REV-001 | 重大 | TC-001 | 根拠が不足 | Authority参照なし | 合否判定不能 | 根拠を追加 | {repair_target} | 修正済み | |
"""

    def test_empty_output_fails_for_all_skills(self):
        for skill in VALIDATORS:
            with self.subTest(skill=skill):
                result = VALIDATORS[skill]("", {}, "EMPTY").to_dict()
                self.assertEqual(result["status"], "fail", result)

    def test_required_table_missing(self):
        self.assert_fails("spec-analysis", "# 仕様分析\n", {}, "SPEC-D012")

    def test_required_entity_missing(self):
        text = self._risk_base().replace("| RISK-001 | 誤保存 | SPEC-001 / CHG-001 | 4 | 2 | 高 | 保存処理の変更 |\n", "")
        expected = {"required_risks": {"RISK-001": {"impact": 4, "likelihood": 2, "risk_level": "高"}}}
        self.assert_fails("test-analysis", text, expected, "RISK-D011")

    def test_expected_missing_vs_explicit_empty_set(self):
        text = self._risk_base()
        self.assert_passes("test-analysis", text, {})
        self.assert_fails("test-analysis", text, {"known_authorities": []}, "RISK-D006")

    def test_spec_current_authority_rejects_inf_unk_and_type_mismatch(self):
        base = self._spec_base()
        cases = [
            (base.replace("SPEC-001 | 保存できる | SPEC", "INF-001 | 推論 | INFERENCE").replace("SPEC-001 | SPEC | 保存できる", "INF-001 | SPEC | 推論"), {"known_authorities": ["INF-001"]}),
            (base.replace("SPEC-001 | 保存できる | SPEC", "UNK-001 | 不明 | UNKNOWN").replace("SPEC-001 | SPEC | 保存できる", "UNK-001 | SPEC | 不明"), {"known_authorities": ["UNK-001"]}),
            (base.replace("SPEC-001 | SPEC | 保存できる", "SPEC-001 | DECISION | 保存できる"), {}),
        ]
        for text, expected in cases:
            with self.subTest(text=text[:40]):
                self.assert_fails("spec-analysis", text, expected, "SPEC-D010")

    def test_spec_required_fields_and_source_integrity(self):
        base = self._spec_base()
        cases = [
            (base.replace("| SPEC-001 | 保存できる | SPEC |", "| SPEC-001 |  | SPEC |"), "SPEC-D014"),
            (base.replace("| SPEC-001 | SPEC | 保存できる |", "| SPEC-001 | SPEC |  |"), "SPEC-D015"),
            (base.replace("| SRC-001 | 要件書 |", "| BAD-001 | 要件書 |").replace("SRC-001 |", "BAD-001 |"), "SPEC-D017"),
            (base.replace("| SRC-001 | 要件書 |", "| SRC-001 | 要件書 |\n| SRC-001 | 設計書 |"), "SPEC-D018"),
            (base.replace("| SRC-001 | 要件書 |", "| SRC-001 |  |"), "SPEC-D016"),
        ]
        for text, assertion_id in cases:
            with self.subTest(assertion_id=assertion_id):
                self.assert_fails("spec-analysis", text, {}, assertion_id)

    def test_approved_assumptions_use_list_semantics(self):
        text = self._question_base()
        valid = {"approved_assumptions": ["ASM-001"], "required_approved_assumptions": ["ASM-001"]}
        self.assert_passes("question-analysis", text, valid)
        self.assert_fails("question-analysis", text, {"approved_assumptions": ["ASM-999"]}, "QUESTION-D009")
        missing = text.replace("| タイムゾーンはJST | 承認済み | ステークホルダー承認 | 日時表示 | ASM-001 |\n", "")
        self.assert_fails("question-analysis", missing, valid, "QUESTION-D015")

        spec = self._spec_base().replace("| SPEC-001 | SPEC | 保存できる | 保存画面 | SRC-001 | 独立 | |", "| ASM-001 | 承認済みASM | JSTを使う | 日時表示 | SRC-001 | 独立 | |")
        self.assert_passes("spec-analysis", spec, {"known_authorities": ["ASM-001"], "approved_assumptions": ["ASM-001"]})
        self.assert_fails("spec-analysis", spec, {"known_authorities": ["ASM-001"], "approved_assumptions": []}, "SPEC-D013")

    def test_question_required_fields_and_blocked_scope(self):
        base = self._question_base()
        for old, new, aid in [
            ("保存条件を確認する", "", "QUESTION-D012"),
            ("仕様に記載なし", "", "QUESTION-D012"),
            ("| Q-001 | Test Requirement | 保存条件の決定 |", "| Q-001 |  | 保存条件の決定 |", "QUESTION-D013"),
        ]:
            with self.subTest(assertion_id=aid):
                self.assert_fails("question-analysis", base.replace(old, new), {"approved_assumptions": ["ASM-001"]}, aid)

    def test_required_technique_and_testability(self):
        base = self._risk_base()
        expected = {"required_techniques": ["状態遷移"], "required_testability": {"操作可能か": "可", "観測可能か": "可", "合否判定可能か": "可"}}
        self.assert_passes("test-analysis", base, expected)
        no_technique = base.replace("| 状態遷移 | 保存状態 | 状態変化を確認するため |\n", "")
        self.assert_fails("test-analysis", no_technique, expected, "RISK-D014")
        no_testability = base.replace("| 保存 | 可 | 可 | 可 | システムテスト | 現在レベル |\n", "")
        self.assert_fails("test-analysis", no_testability, expected, "RISK-D015")
        mismatch = base.replace("| 保存 | 可 | 可 | 可 |", "| 保存 | 可 | 不可 | 可 |")
        self.assert_fails("test-analysis", mismatch, expected, "RISK-D015")

    def test_technique_and_testability_required_fields(self):
        base = self._risk_base()
        self.assert_fails("test-analysis", base.replace("| 状態遷移 | 保存状態 | 状態変化を確認するため |", "| 状態遷移 |  | 状態変化を確認するため |"), {}, "RISK-D012")
        self.assert_fails("test-analysis", base.replace("| 保存 | 可 | 可 | 可 | システムテスト |", "| 保存 | 可 | 可 | 可 |  |"), {}, "RISK-D013")

    def test_pairwise_invalid_generated_combinations(self):
        for combo, assertion_id in [("A=0; B=0; Foo=x", "TCN-D018"), ("A=2; B=0", "TCN-D019"), ("A=1; B=1", "TCN-D020"), ("A=0", "TCN-D021")]:
            with self.subTest(combo=combo):
                text, expected = self._pairwise_base(combo)
                self.assert_fails("test-condition-design", text, expected, assertion_id)

    def test_pairwise_existing_coverage_check_still_detects_missing_pair(self):
        text, expected = self._pairwise_base("A=0; B=0")
        expected["pairwise"]["forbidden_constraints"] = []
        expected["pairwise"]["require_pairwise"] = True
        self.assert_fails("test-condition-design", text, expected, "TCN-D015")

    def test_pairwise_generated_coverage_item_integrity(self):
        text, expected = self._pairwise_base()
        self.assert_fails("test-condition-design", text.replace("| TCN-001-CI01 | A=0; B=0 |", "| TCN-001-CI99 | A=0; B=0 |"), expected, "TCN-D026")
        duplicate = text.replace("| TCN-001-CI01 | A=0; B=0 |", "| TCN-001-CI01 | A=0; B=0 |\n| TCN-001-CI01 | A=1; B=0 |")
        self.assert_fails("test-condition-design", duplicate, expected, "TCN-D027")

    def test_pairwise_invalid_tokens_and_duplicate_factors(self):
        for combo in ("A=0; invalid-token; B=0", "A=0; A=1; B=0"):
            with self.subTest(combo=combo):
                text, expected = self._pairwise_base(combo)
                self.assert_fails("test-condition-design", text, expected, "TCN-D028")

    def test_state_transition_requires_existing_coverage_item(self):
        text, expected = self._pairwise_base()
        text += """\n## 状態遷移表
| 現在状態 | イベント / 操作 | 期待する次状態 / 結果 | 対応Coverage Item ID |
| --- | --- | --- | --- |
| draft | publish | published | TCN-999-CI99 |
"""
        expected.pop("pairwise")
        expected["required_transitions"] = [{"from": "draft", "event": "publish", "to": "published"}]
        self.assert_fails("test-condition-design", text, expected, "TCN-D016")

    def test_disposition_targets_must_exist_when_fixture_sets_are_present(self):
        tr = """# TR
## テスト要求一覧
| テスト要求ID | テスト要求 | Current Effective Authority | 関連Product Risk | 優先度 | テストレベル / 観測方法 |
| --- | --- | --- | --- | --- | --- |
| TR-001 | 保存を検証 | SPEC-001 | RISK-001 | 高 | システム / UI |
## Test Requirementを作らない上流項目
| 上流ID | 種別 | Disposition | 理由 / 根拠 |
| --- | --- | --- | --- |
| SPEC-999 | Authority | 対象外 | スコープ外 |
"""
        self.assert_fails("test-requirement-design", tr, {"known_authorities": ["SPEC-001"], "known_product_risks": ["RISK-001"]}, "TR-D013")

        tcn, expected = self._pairwise_base()
        tcn = tcn.replace("| --- | --- | --- |\n## テスト観点", "| --- | --- | --- |\n| TR-999 | 対象外 | 理由 |\n## テスト観点")
        self.assert_fails("test-condition-design", tcn, expected, "TCN-D029")

        tc = """# TC
## テストケース一覧
| テストケースID | タイトル / 目的 | 関連観点ID | 関連Coverage Item ID | 関連テスト要求ID | 優先度 | 前提条件 | テストデータ | 実施手順 | 期待結果 | 期待結果の根拠 | 備考 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| TC-001 | 保存 | TCN-001 | TCN-001-CI01 | TR-001 | 高 | ログイン済み | valid | 保存する | 保存済み表示 | SPEC-001 | |
## Test Caseへ展開しないCoverage Item / Test Condition
| 上流ID | 種別 | Disposition | 理由 / 根拠 |
| --- | --- | --- | --- |
| TCN-999-CI99 | Coverage Item | 対象外 | スコープ外 |
"""
        tc_expected = {"known_test_conditions": ["TCN-001"], "known_coverage_items": ["TCN-001-CI01"], "known_test_requirements": ["TR-001"], "known_authorities": ["SPEC-001"]}
        self.assert_fails("test-case-design", tc, tc_expected, "TC-D014")

    def test_coverage_expected_fix_target_must_exist(self):
        text = """# Coverage
## カバレッジマトリクス
| 上流層 | 上流ID / 挙動 | 下流層 | 下流ID / Disposition | カバレッジ | 修正Skill / 層 |
| --- | --- | --- | --- | --- | --- |
| TR | TR-001 | TCN | TCN-001 | 網羅済み | test-condition-design |
"""
        self.assert_fails("coverage-analysis", text, {"expected_fix_skills": {"TCN-001-CI01": "test-condition-design"}}, "COV-D005")

    def test_major_residual_acceptance_must_match_fixture_approval(self):
        text = self._review_base().replace("| 修正済み | |", "| 残存リスクとして受容 | APR-999 |")
        self.assert_fails("adversarial-review", text, {"known_artifact_ids": ["TC-001"], "approved_risk_acceptances": {"REV-001": "APR-001"}}, "REV-D008")

    def test_adversarial_repair_targets_and_summary_contract(self):
        expected = {"known_artifact_ids": ["TC-001"]}
        self.assert_passes("adversarial-review", self._review_base("test-case-design"), expected)
        self.assert_passes("adversarial-review", self._review_base("Project Context / 仕様決定"), expected)
        self.assert_fails("adversarial-review", self._review_base("unknown-target"), expected, "REV-D006")
        self.assert_fails("adversarial-review", self._review_base().replace("| 提案 | 0 |", "| unknown | 0 |"), expected, "REV-D013")
        self.assert_fails("adversarial-review", self._review_base().replace("| 軽微 | 0 |", "| 重大 | 0 |"), expected, "REV-D014")

    def test_adversarial_finding_required_fields(self):
        text = self._review_base().replace("| REV-001 | 重大 | TC-001 | 根拠が不足 | Authority参照なし | 合否判定不能 | 根拠を追加 | test-case-design |", "| REV-001 | 重大 | TC-001 |  |  |  | 根拠を追加 |  |")
        self.assert_fails("adversarial-review", text, {"known_artifact_ids": ["TC-001"]}, "REV-D012")

    def test_workflow_state_invariants_and_duplicate_skill(self):
        def workflow(overall: str, rows: str) -> str:
            return f"""- Workflow全体状態: {overall}
| Skill | 状態 | 成果物 / バージョン | Blocker / 備考 |
| --- | --- | --- | --- |
{rows}
"""
        self.assert_fails("qa-workflow", workflow("完了", "| test-case-design | 実行中 | v1 | |"), {}, "WF-D004")
        self.assert_fails("qa-workflow", workflow("部分完了（Blockedあり）", "| test-case-design | 完了 | v1 | |"), {}, "WF-D010")
        self.assert_fails("qa-workflow", workflow("Blocked", "| test-case-design | 完了 | v1 | |"), {}, "WF-D011")
        duplicate = workflow("実行中", "| test-case-design | 実行中 | v1 | |\n| test-case-design | 完了 | v1 | |")
        self.assert_fails("qa-workflow", duplicate, {}, "WF-D012")

    def test_test_case_priority_override_requires_reason(self):
        base = """# TC
## テストケース一覧
| テストケースID | タイトル / 目的 | 関連観点ID | 関連Coverage Item ID | 関連テスト要求ID | 優先度 | 前提条件 | テストデータ | 実施手順 | 期待結果 | 期待結果の根拠 | 備考 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| TC-001 | 保存 | TCN-001 | TCN-001-CI01 | TR-001 | 低 | ログイン済み | valid | 保存する | 保存済み表示 | SPEC-001 | {note} |
## Test Caseへ展開しないCoverage Item / Test Condition
| 上流ID | 種別 | Disposition | 理由 / 根拠 |
| --- | --- | --- | --- |
"""
        expected = {"known_test_conditions": ["TCN-001"], "known_coverage_items": ["TCN-001-CI01"], "known_test_requirements": ["TR-001"], "known_authorities": ["SPEC-001"], "coverage_item_priorities": {"TCN-001-CI01": "高"}}
        self.assert_fails("test-case-design", base.format(note=""), expected, "TC-D010")
        self.assert_passes("test-case-design", base.format(note="低リスクの補助確認として優先度を下げる"), expected)

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
