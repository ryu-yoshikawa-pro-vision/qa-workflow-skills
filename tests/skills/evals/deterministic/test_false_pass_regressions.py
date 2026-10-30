from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

from scripts.skills.evals.deterministic.loader import load_validators

VALIDATORS = load_validators()


class FalsePassRegressionTests(unittest.TestCase):
    def test_skill_markdown_tables_use_valid_separator_widths(self) -> None:
        repo_root = Path(__file__).resolve().parents[4]
        malformed: list[str] = []
        for path in (repo_root / "skills").rglob("*.md"):
            in_fence = False
            lines = path.read_text(encoding="utf-8").splitlines()
            for index, line in enumerate(lines):
                if line.lstrip().startswith("```"):
                    in_fence = not in_fence
                    continue
                if in_fence or not line.strip().startswith("|") or index == 0:
                    continue
                if not lines[index - 1].strip().startswith("|"):
                    continue
                cells = line.strip().strip("|").split("|")
                if cells and all(re.fullmatch(r"\s*:?-+:?\s*", cell) for cell in cells):
                    if any(cell.count("-") < 1 for cell in cells):
                        malformed.append(f"{path.relative_to(repo_root)}:{index + 1}")

        self.assertEqual(malformed, [])

    def assert_fails(
        self, skill: str, text: str, expected: dict, assertion_id: str
    ) -> None:
        result = VALIDATORS[skill](text, expected, "REGRESSION").to_dict()
        failed = {a["id"] for a in result["assertions"] if a["status"] == "fail"}
        self.assertIn(assertion_id, failed, result)

    def assert_passes(self, skill: str, text: str, expected: dict) -> None:
        result = VALIDATORS[skill](text, expected, "REGRESSION").to_dict()
        self.assertEqual(result["status"], "pass", result)

    def _spec_base(self) -> str:
        return """# 仕様分析
## 情報源 / 正本参照一覧
| 参照ID | 情報源 / 正本一覧 |
| --- | --- |
| SRC-001 | 要件書 |
## 分析項目
| 項目ID | 内容 | 分類 | 情報源 / 正本参照 |
| --- | --- | --- | --- |
| SPEC-001 | 保存できる | SPEC | SRC-001 |
## 現在有効な仕様根拠
| 仕様根拠ID | 種別 | 現在有効な内容 | 適用範囲 | 情報源 / 正本一覧 | 関係 | 関連仕様根拠ID |
| --- | --- | --- | --- | --- | --- | --- |
| SPEC-001 | SPEC | 保存できる | 保存画面 | SRC-001 | 独立 | |
"""

    def _question_base(self) -> str:
        return """# 質問分析
## 不明点 / 質問一覧
| ID | 問題 / 質問 | 根拠 | 分類 | 影響範囲 / 成果物 | 回答なしの場合の扱い | 回答後の正規化先 | 再開Skill |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Q-001 | 保存条件を確認する | 仕様に記載なし | ブロッカー | テスト要求 | 対象範囲を停止 | DECISION | spec-analysis |
## 仮定候補
| 仮定候補 | 状態 | 根拠 / 理由 | 影響範囲 | 正式ASM ID |
| --- | --- | --- | --- | --- |
| タイムゾーンはJST | 承認済み | ステークホルダー承認 | 日時表示 | ASM-001 |
## ブロック中範囲
| ブロッカーID | ブロック中成果物 / 範囲 | 必要な決定 / 情報源 | 再開Skill |
| --- | --- | --- | --- |
| Q-001 | テスト要求 | 保存条件の決定 | spec-analysis |
"""

    def _risk_base(self) -> str:
        return """# テスト分析
## プロダクトリスク一覧
| リスクID | 製品上のリスク / 失敗 | 関連する現在有効な仕様根拠 / 変更 / 依存 | 影響度 | 発生可能性 | レベル | 根拠 |
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
## テスト条件へ展開しないテスト要求
| テスト要求ID | 扱い | 理由 / 根拠 |
| --- | --- | --- |
## テスト観点・条件一覧
| 観点ID | テスト要求ID | テスト観点 / 条件 | テスト技法 / 根拠 | カバレッジ基準 | 優先度 |
| --- | --- | --- | --- | --- | --- |
| TCN-001 | TR-001 | 組合せ | Pairwise | 全2-wise | 高 |
## カバレッジ項目一覧
| カバレッジ項目ID | 観点ID | カバレッジ項目 | 導出元の技法 / 基準 | 期待挙動の根拠 | 優先度 |
| --- | --- | --- | --- | --- | --- |
| TCN-001-CI01 | TCN-001 | combo | Pairwise | SPEC-001 | 高 |
## カバレッジ候補の扱い
| 候補 | 導出元 | 扱い | 理由 / 根拠 | カバー先 |
| --- | --- | --- | --- | --- |
## 因子 / 値 / 制約
| 因子 | 値 |
| --- | --- |
| A | 0 |
| A | 1 |
| B | 0 |
| B | 1 |
## 生成組合せ
| カバレッジ項目ID | 組合せ |
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
| REV-001 | 重大 | TC-001 | 根拠が不足 | 仕様根拠参照なし | 合否判定不能 | 根拠を追加 | {repair_target} | 修正済み | |
"""

    def test_empty_output_fails_for_all_skills(self):
        for skill in VALIDATORS:
            with self.subTest(skill=skill):
                result = VALIDATORS[skill]("", {}, "EMPTY").to_dict()
                self.assertEqual(result["status"], "fail", result)

    def test_tcn_unprovided_priorities_may_be_blank_but_invalid_values_fail(self):
        text, expected = self._pairwise_base()
        text = text.replace("全2-wise | 高 |", "全2-wise |  |")
        text = text.replace("SPEC-001 | 高 |", "SPEC-001 |  |")
        self.assert_passes("test-condition-design", text, expected)

        invalid = text.replace("全2-wise |  |", "全2-wise | — |")
        self.assert_fails("test-condition-design", invalid, expected, "TCN-D008")

    def test_tcn_disposition_template_placeholder_is_not_a_real_item(self):
        text, expected = self._pairwise_base()
        text = text.replace(
            "| --- | --- | --- |\n## テスト観点・条件一覧",
            "| --- | --- | --- |\n"
            "| — | — | 該当なし（該当するテスト要求がない場合） |\n"
            "## テスト観点・条件一覧",
        )
        self.assert_passes("test-condition-design", text, expected)

    def test_tcn_real_disposition_row_still_requires_a_valid_enum_and_known_id(self):
        text, expected = self._pairwise_base()
        text = text.replace(
            "| --- | --- | --- |\n## テスト観点・条件一覧",
            "| --- | --- | --- |\n| TR-999 | — | 未展開の理由 |\n"
            "## テスト観点・条件一覧",
        )
        result = VALIDATORS["test-condition-design"](
            text, expected, "REGRESSION"
        ).to_dict()
        failed = {a["id"] for a in result["assertions"] if a["status"] == "fail"}
        self.assertIn("TCN-D010", failed, result)
        self.assertIn("TCN-D029", failed, result)

    def test_required_table_missing(self):
        self.assert_fails("spec-analysis", "# 仕様分析\n", {}, "SPEC-D012")

    def test_required_entity_missing(self):
        text = self._risk_base().replace(
            "| RISK-001 | 誤保存 | SPEC-001 / CHG-001 | 4 | 2 | 高 | 保存処理の変更 |\n",
            "",
        )
        expected = {
            "required_risks": {
                "RISK-001": {"impact": 4, "likelihood": 2, "risk_level": "高"}
            }
        }
        self.assert_fails("test-analysis", text, expected, "RISK-D011")

    def test_expected_missing_vs_explicit_empty_set(self):
        text = self._risk_base()
        self.assert_passes("test-analysis", text, {})
        self.assert_fails("test-analysis", text, {"known_authorities": []}, "RISK-D006")

    def test_test_analysis_runtime_contract_cannot_pass_without_evidence(self):
        identity = "test-analysis::artifact:analysis_entities:all"
        expected = {
            "runtime_contract": {
                "expected_runtime_units": [identity],
                "expected_generators": {identity: "analysis_entities"},
                "expected_status": {
                    identity: {
                        "runtime_status": "ok",
                        "result_status": "ready",
                        "support_status": "supported",
                        "runtime_required": True,
                        "deterministic_generated": True,
                    }
                },
            }
        }
        result = VALIDATORS["test-analysis"](
            self._risk_base(), expected, "REGRESSION"
        ).to_dict()
        failed = {a["id"] for a in result["assertions"] if a["status"] == "fail"}
        self.assertIn("RISK-D018", failed, result)

    def test_test_analysis_accepts_guidance_technique_labels(self):
        supported = (
            "Domain Testing",
            "CRUD Testing",
            "Random Testing",
            "Metamorphic Testing",
            "Syntax-Based Testing",
        )
        for label in supported:
            with self.subTest(label=label):
                text = self._risk_base().replace(
                    "| 状態遷移 | 保存状態 |",
                    f"| {label} | 保存状態 |",
                )
                result = VALIDATORS["test-analysis"](text, {}, "REGRESSION").to_dict()
                assertion = next(
                    a for a in result["assertions"] if a["id"] == "RISK-D008"
                )
                self.assertEqual(assertion["status"], "pass", assertion)

    def test_test_analysis_template_requires_final_gate_and_blocked_state(self):
        repo_root = Path(__file__).resolve().parents[4]
        template = (
            repo_root / "skills/test-analysis/assets/output-template.md"
        ).read_text(encoding="utf-8")
        self.assertIn("verify_runtime_evidence valid: true / false", template)
        self.assertIn("成果物状態: 完成 / 未完成（ブロック中）", template)
        self.assertIn('render_machine_entities("test-analysis", [])', template)
        self.assertIn("Entity blockを省略せず", template)
        self.assertIn("完成済みとして扱いません", template)

    def test_test_analysis_allows_only_expected_explicit_blocked_gate(self):
        identity = "test-analysis::artifact:analysis_entities:all"
        helper = VALIDATORS["test-analysis"].__globals__[
            "_is_expected_blocked_gate_outcome"
        ]
        explicit_state = VALIDATORS["test-analysis"].__globals__[
            "_has_explicit_gate_state"
        ]
        expected_status = {
            identity: {"runtime_status": "invalid_input", "result_status": "blocked"}
        }
        entity_blocks = [("test-analysis", {"entities": []})]
        text = (
            "- `verify_runtime_evidence valid: false`\n"
            "- `成果物状態: 未完成（ブロック中）`"
        )
        self.assertTrue(explicit_state(text, valid=False))
        self.assertFalse(explicit_state(text, valid=True))
        self.assertTrue(
            explicit_state(
                "- `verify_runtime_evidence valid: true`\n- `成果物状態: 完成`",
                valid=True,
            )
        )
        self.assertTrue(
            explicit_state(
                "- verify_runtime_evidence valid: **false**\n"
                "- 成果物状態: **未完成（ブロック中）**",
                valid=False,
            )
        )
        self.assertTrue(
            explicit_state(
                "- verify_runtime_evidence valid: `true`\n- 成果物状態: *完成*",
                valid=True,
            )
        )
        self.assertFalse(
            explicit_state(
                "- verify_runtime_evidence valid: **false*\n"
                "- 成果物状態: **未完成（ブロック中）**",
                valid=False,
            )
        )
        self.assertFalse(
            explicit_state(
                "- verify_runtime_evidence valid: **true**\n- 成果物状態: **完成**",
                valid=False,
            )
        )
        gate = {
            "valid": False,
            "issues": [{"issue_type": "missing_entity", "blocking": True}],
        }
        self.assertTrue(helper(gate, [identity], expected_status, entity_blocks, text))
        bold_text = (
            "- verify_runtime_evidence valid: **false**\n"
            "- 成果物状態: **未完成（ブロック中）**"
        )
        self.assertTrue(
            helper(gate, [identity], expected_status, entity_blocks, bold_text)
        )
        unexpected_issue = {
            "valid": False,
            "issues": [{"issue_type": "duplicate_runtime_unit", "blocking": True}],
        }
        self.assertFalse(
            helper(
                unexpected_issue,
                [identity],
                expected_status,
                entity_blocks,
                text,
            )
        )
        self.assertFalse(
            helper(gate, [identity], expected_status, entity_blocks, "valid: false")
        )
        self.assertFalse(helper(gate, [identity], expected_status, [], text))

    def test_spec_current_authority_rejects_inf_unk_and_type_mismatch(self):
        base = self._spec_base()
        cases = [
            (
                base.replace(
                    "SPEC-001 | 保存できる | SPEC", "INF-001 | 推論 | INFERENCE"
                ).replace("SPEC-001 | SPEC | 保存できる", "INF-001 | SPEC | 推論"),
                {"known_authorities": ["INF-001"]},
            ),
            (
                base.replace(
                    "SPEC-001 | 保存できる | SPEC", "UNK-001 | 不明 | UNKNOWN"
                ).replace("SPEC-001 | SPEC | 保存できる", "UNK-001 | SPEC | 不明"),
                {"known_authorities": ["UNK-001"]},
            ),
            (
                base.replace(
                    "SPEC-001 | SPEC | 保存できる", "SPEC-001 | DECISION | 保存できる"
                ),
                {},
            ),
        ]
        for text, expected in cases:
            with self.subTest(text=text[:40]):
                self.assert_fails("spec-analysis", text, expected, "SPEC-D010")

    def test_spec_required_fields_and_source_integrity(self):
        base = self._spec_base()
        cases = [
            (
                base.replace(
                    "| SPEC-001 | 保存できる | SPEC |", "| SPEC-001 |  | SPEC |"
                ),
                "SPEC-D014",
            ),
            (
                base.replace(
                    "| SPEC-001 | SPEC | 保存できる |", "| SPEC-001 | SPEC |  |"
                ),
                "SPEC-D015",
            ),
            (
                base.replace("| SRC-001 | 要件書 |", "| BAD-001 | 要件書 |").replace(
                    "SRC-001 |", "BAD-001 |"
                ),
                "SPEC-D017",
            ),
            (
                base.replace(
                    "| SRC-001 | 要件書 |", "| SRC-001 | 要件書 |\n| SRC-001 | 設計書 |"
                ),
                "SPEC-D018",
            ),
            (base.replace("| SRC-001 | 要件書 |", "| SRC-001 |  |"), "SPEC-D016"),
        ]
        for text, assertion_id in cases:
            with self.subTest(assertion_id=assertion_id):
                self.assert_fails("spec-analysis", text, {}, assertion_id)

    def test_approved_assumptions_use_list_semantics(self):
        text = self._question_base()
        valid = {
            "approved_assumptions": ["ASM-001"],
            "required_approved_assumptions": ["ASM-001"],
        }
        self.assert_passes("question-analysis", text, valid)
        self.assert_fails(
            "question-analysis",
            text,
            {"approved_assumptions": ["ASM-999"]},
            "QUESTION-D009",
        )
        missing = text.replace(
            "| タイムゾーンはJST | 承認済み | ステークホルダー承認 | 日時表示 | ASM-001 |\n",
            "",
        )
        self.assert_fails("question-analysis", missing, valid, "QUESTION-D015")

        spec = self._spec_base().replace(
            "| SPEC-001 | SPEC | 保存できる | 保存画面 | SRC-001 | 独立 | |",
            "| ASM-001 | 承認済みASM | JSTを使う | 日時表示 | SRC-001 | 独立 | |",
        )
        self.assert_passes(
            "spec-analysis",
            spec,
            {"known_authorities": ["ASM-001"], "approved_assumptions": ["ASM-001"]},
        )
        self.assert_fails(
            "spec-analysis",
            spec,
            {"known_authorities": ["ASM-001"], "approved_assumptions": []},
            "SPEC-D013",
        )

    def test_question_required_fields_and_blocked_scope(self):
        base = self._question_base()
        for old, new, aid in [
            ("保存条件を確認する", "", "QUESTION-D012"),
            ("仕様に記載なし", "", "QUESTION-D012"),
            (
                "| Q-001 | テスト要求 | 保存条件の決定 |",
                "| Q-001 |  | 保存条件の決定 |",
                "QUESTION-D013",
            ),
        ]:
            with self.subTest(assertion_id=aid):
                self.assert_fails(
                    "question-analysis",
                    base.replace(old, new),
                    {"approved_assumptions": ["ASM-001"]},
                    aid,
                )

    def test_question_fixture_normalization(self):
        expected = {"expected_normalizations": {"Q-001": "未確定"}}
        matching = self._question_base().replace(
            "| DECISION | spec-analysis |", "| 未確定 | spec-analysis |"
        )
        self.assert_passes("question-analysis", matching, expected)
        self.assert_fails(
            "question-analysis", self._question_base(), expected, "QUESTION-D016"
        )
        self.assert_passes("question-analysis", self._question_base(), {})

    def test_required_technique_and_testability(self):
        base = self._risk_base()
        expected = {
            "required_techniques": ["状態遷移"],
            "required_testability": {
                "操作可能か": "可",
                "観測可能か": "可",
                "合否判定可能か": "可",
            },
        }
        self.assert_passes("test-analysis", base, expected)
        no_technique = base.replace(
            "| 状態遷移 | 保存状態 | 状態変化を確認するため |\n", ""
        )
        self.assert_fails("test-analysis", no_technique, expected, "RISK-D014")
        no_testability = base.replace(
            "| 保存 | 可 | 可 | 可 | システムテスト | 現在レベル |\n", ""
        )
        self.assert_fails("test-analysis", no_testability, expected, "RISK-D015")
        mismatch = base.replace("| 保存 | 可 | 可 | 可 |", "| 保存 | 可 | 不可 | 可 |")
        self.assert_fails("test-analysis", mismatch, expected, "RISK-D015")

    def test_technique_and_testability_required_fields(self):
        base = self._risk_base()
        self.assert_fails(
            "test-analysis",
            base.replace(
                "| 状態遷移 | 保存状態 | 状態変化を確認するため |",
                "| 状態遷移 |  | 状態変化を確認するため |",
            ),
            {},
            "RISK-D012",
        )
        self.assert_fails(
            "test-analysis",
            base.replace(
                "| 保存 | 可 | 可 | 可 | システムテスト |", "| 保存 | 可 | 可 | 可 |  |"
            ),
            {},
            "RISK-D013",
        )

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

    def _blocked_pairwise_base(self) -> tuple[str, dict]:
        text, expected = self._pairwise_base()
        text = text.replace(
            "| TCN-001-CI01 | TCN-001 | combo | Pairwise | SPEC-001 | 高 |\n", ""
        )
        text = text.replace("| TCN-001-CI01 | A=0; B=0 |\n", "")
        candidate_table = """## Pairwise runtime target候補（CI ID未採番）
| 候補target key | 対象2-wise pair | 生成row（全因子割当） | 扱い | 理由 / 根拠 |
| --- | --- | --- | --- | --- |
| pair:a0-b0 | A=0; B=0 | A=0; B=0 | ブロック中 | Authority未解決 |
| pair:a0-b1 | A=0; B=1 | A=0; B=1 | ブロック中 | Authority未解決 |
| pair:a1-b0 | A=1; B=0 | A=1; B=0 | ブロック中 | Authority未解決 |
"""
        text = text.replace("## 生成組合せ\n", candidate_table + "\n## 生成組合せ\n")
        expected["pairwise"]["require_pairwise"] = True
        expected["pairwise"]["blocked_candidate_disposition"] = "ブロック中"
        return text, expected

    def test_blocked_pairwise_candidates_cover_input_pairs_without_ci_entities(self):
        text, expected = self._blocked_pairwise_base()
        self.assert_passes("test-condition-design", text, expected)

    def test_blocked_pairwise_candidates_must_cover_every_feasible_pair(self):
        text, expected = self._blocked_pairwise_base()
        text = text.replace(
            "| pair:a1-b0 | A=1; B=0 | A=1; B=0 | ブロック中 | Authority未解決 |\n",
            "",
        )
        self.assert_fails("test-condition-design", text, expected, "TCN-D015")

    def test_blocked_pairwise_candidates_require_full_valid_rows_and_reason(self):
        text, expected = self._blocked_pairwise_base()
        mutations = [
            (
                "| pair:a0-b0 | A=0; B=0 | A=0; B=0 | ブロック中 | Authority未解決 |",
                "| pair:a0-b0 | A=0; B=0 | A=0 | ブロック中 | Authority未解決 |",
            ),
            (
                "| pair:a0-b0 | A=0; B=0 | A=0; B=0 | ブロック中 | Authority未解決 |",
                "| pair:a0-b0 | A=0; B=0 | A=1; B=1 | ブロック中 | Authority未解決 |",
            ),
            (
                "| pair:a0-b0 | A=0; B=0 | A=0; B=0 | ブロック中 | Authority未解決 |",
                "| pair:a0-b0 | A=0; B=0 | A=0; B=0 | 対象外 | Authority未解決 |",
            ),
            (
                "| pair:a0-b0 | A=0; B=0 | A=0; B=0 | ブロック中 | Authority未解決 |",
                "| pair:a0-b0 | A=0; B=0 | A=0; B=0 | ブロック中 |  |",
            ),
        ]
        for before, after in mutations:
            with self.subTest(after=after):
                mutated = text.replace(before, after)
                self.assert_fails(
                    "test-condition-design", mutated, expected, "TCN-D030"
                )

    def _blocked_bva_transition_base(self) -> tuple[str, dict]:
        text = """# TCN
## テスト条件へ展開しないテスト要求
| テスト要求ID | 扱い | 理由 / 根拠 |
| --- | --- | --- |
## テスト観点・条件一覧
| 観点ID | テスト要求ID | テスト観点 / 条件 | テスト技法 / 根拠 | カバレッジ基準 | 優先度 |
| --- | --- | --- | --- | --- | --- |
| TCN-001 | TR-001 | 入力値と遷移候補を保持 | BVA / 状態遷移 | 入力指定値と遷移を個別に確認 | |
## カバレッジ項目一覧
| カバレッジ項目ID | 観点ID | カバレッジ項目 | 導出元の技法 / 基準 | 期待挙動の根拠 | 優先度 |
| --- | --- | --- | --- | --- | --- |
## カバレッジ候補の扱い
| 候補 | 導出元 | 扱い | 理由 / 根拠 | カバー先 |
| --- | --- | --- | --- | --- |
| bva:upper:100 | 入力値100 | ブロック中 | current Authority未解決 | |
| bva:upper:101 | 入力値101 | ブロック中 | current Authority未解決 | |
| state:draft-publish | 入力遷移 | ブロック中 | current Authority未解決 | |
| state:published-archive | 入力遷移 | ブロック中 | current Authority未解決 | |
## 状態遷移表
| 現在状態 | イベント / 操作 | 条件 | 期待する次状態 / 結果 | 対応カバレッジ項目ID |
| --- | --- | --- | --- | --- |
| draft | publish | fixture開始状態 | published | |
| published | archive | fixture開始状態 | archived | |
## 境界値runtime target候補（CI ID未採番）
| Runtime target key | 境界 / 位置 | 入力値 | 扱い | 理由 / 根拠 |
| --- | --- | --- | --- | --- |
| bva:upper:100 | integer upper | 100 | ブロック中 | current Authority未解決 |
| bva:upper:101 | integer adjacent | 101 | ブロック中 | current Authority未解決 |
## 状態遷移runtime target候補（CI ID未採番）
| Runtime target key | Coverage transition | 扱い | 理由 / 根拠 |
| --- | --- | --- | --- |
| state:draft-publish | draft --publish--> published | ブロック中 | current Authority未解決 |
| state:published-archive | published --archive--> archived | ブロック中 | current Authority未解決 |
"""
        expected = {
            "known_test_requirements": ["TR-001"],
            "required_transitions": [
                {
                    "from": "draft",
                    "event": "publish",
                    "to": "published",
                    "disposition": "ブロック中",
                },
                {
                    "from": "published",
                    "event": "archive",
                    "to": "archived",
                    "disposition": "ブロック中",
                },
            ],
            "bva": [
                {
                    "required_values": [100, 101],
                    "blocked_candidate_disposition": "ブロック中",
                }
            ],
        }
        return text, expected

    def test_blocked_bva_and_state_candidates_close_without_active_ci(self):
        text, expected = self._blocked_bva_transition_base()
        self.assert_passes("test-condition-design", text, expected)

    def test_blocked_candidate_disposition_accepts_runtime_key_in_cover_target(self):
        text, expected = self._blocked_bva_transition_base()
        text = text.replace(
            "| bva:upper:100 | 入力値100 | ブロック中 | current Authority未解決 | |",
            "| 入力値100 | BVA | ブロック中 | current Authority未解決 | bva:upper:100 |",
        )
        text = text.replace(
            "| bva:upper:101 | 入力値101 | ブロック中 | current Authority未解決 | |",
            "| 入力値101 | BVA | ブロック中 | current Authority未解決 | bva:upper:101 |",
        )
        text = text.replace(
            "| state:draft-publish | 入力遷移 | ブロック中 | current Authority未解決 | |",
            "| draftからpublished | 状態遷移 | ブロック中 | current Authority未解決 | state:draft-publish |",
        )
        text = text.replace(
            "| state:published-archive | 入力遷移 | ブロック中 | current Authority未解決 | |",
            "| publishedからarchived | 状態遷移 | ブロック中 | current Authority未解決 | state:published-archive |",
        )
        self.assert_passes("test-condition-design", text, expected)
        wrong_bva_destination = text.replace(
            "| 入力値100 | BVA | ブロック中 | current Authority未解決 | bva:upper:100 |",
            "| 入力値100 | BVA | ブロック中 | current Authority未解決 | bva:upper:other |",
        )
        self.assert_fails(
            "test-condition-design",
            wrong_bva_destination,
            expected,
            "TCN-D017",
        )
        wrong_transition_destination = text.replace(
            "| draftからpublished | 状態遷移 | ブロック中 | current Authority未解決 | state:draft-publish |",
            "| draftからpublished | 状態遷移 | ブロック中 | current Authority未解決 | state:other |",
        )
        self.assert_fails(
            "test-condition-design",
            wrong_transition_destination,
            expected,
            "TCN-D016",
        )

    def test_blocked_bva_requires_every_value_and_matching_disposition(self):
        text, expected = self._blocked_bva_transition_base()
        missing_value = text.replace(
            "| bva:upper:101 | integer adjacent | 101 | ブロック中 | current Authority未解決 |\n",
            "",
        )
        self.assert_fails("test-condition-design", missing_value, expected, "TCN-D017")
        wrong_disposition = text.replace(
            "| bva:upper:101 | integer adjacent | 101 | ブロック中 | current Authority未解決 |",
            "| bva:upper:101 | integer adjacent | 101 | 対象外 | current Authority未解決 |",
        )
        self.assert_fails(
            "test-condition-design", wrong_disposition, expected, "TCN-D017"
        )

    def test_blocked_transition_requires_matching_target_and_disposition(self):
        text, expected = self._blocked_bva_transition_base()
        missing_target = text.replace(
            "| state:draft-publish | draft --publish--> published | ブロック中 | current Authority未解決 |\n",
            "",
        )
        self.assert_fails("test-condition-design", missing_target, expected, "TCN-D016")
        wrong_transition = text.replace(
            "draft --publish--> published", "draft --archive--> archived"
        )
        self.assert_fails(
            "test-condition-design", wrong_transition, expected, "TCN-D016"
        )

    def test_pairwise_constraint_only_row_is_not_parsed_as_empty_factor(self):
        text, expected = self._pairwise_base()
        text = text.replace(
            "| 因子 | 値 |\n| --- | --- |",
            "| 因子 | 値 | 制約 / 備考 |\n| --- | --- | --- |",
        )
        for factor, value in (("A", "0"), ("A", "1"), ("B", "0"), ("B", "1")):
            text = text.replace(
                f"| {factor} | {value} |\n",
                f"| {factor} | {value} |  |\n",
            )
        text = text.replace(
            "## 生成組合せ",
            "|  |  | A=1 and B=1 is infeasible |\n## 生成組合せ",
        )
        result = VALIDATORS["test-condition-design"](
            text, expected, "REGRESSION"
        ).to_dict()
        assertion = next(row for row in result["assertions"] if row["id"] == "TCN-D014")
        self.assertEqual(assertion["status"], "pass", result)

    def test_pairwise_factor_order_is_canonical(self):
        text = """# TCN
## テスト条件へ展開しないテスト要求
| テスト要求ID | 扱い | 理由 / 根拠 |
| --- | --- | --- |
## テスト観点・条件一覧
| 観点ID | テスト要求ID | テスト観点 / 条件 | テスト技法 / 根拠 | カバレッジ基準 | 優先度 |
| --- | --- | --- | --- | --- | --- |
| TCN-001 | TR-001 | 組合せ | Pairwise | 全2-wise | 高 |
## カバレッジ項目一覧
| カバレッジ項目ID | 観点ID | カバレッジ項目 | 導出元の技法 / 基準 | 期待挙動の根拠 | 優先度 |
| --- | --- | --- | --- | --- | --- |
| TCN-001-CI01 | TCN-001 | combo1 | Pairwise | SPEC-001 | 高 |
| TCN-001-CI02 | TCN-001 | combo2 | Pairwise | SPEC-001 | 高 |
| TCN-001-CI03 | TCN-001 | combo3 | Pairwise | SPEC-001 | 高 |
| TCN-001-CI04 | TCN-001 | combo4 | Pairwise | SPEC-001 | 高 |
## カバレッジ候補の扱い
| 候補 | 導出元 | 扱い | 理由 / 根拠 | カバー先 |
| --- | --- | --- | --- | --- |
## 因子 / 値 / 制約
| 因子 | 値 |
| --- | --- |
| Role | admin |
| Role | member |
| Browser | Chrome |
| Browser | Edge |
| Flag | on |
| Flag | off |
## 生成組合せ
| カバレッジ項目ID | 組合せ |
| --- | --- |
| TCN-001-CI01 | Role=admin; Browser=Chrome; Flag=on |
| TCN-001-CI02 | Role=admin; Browser=Edge; Flag=off |
| TCN-001-CI03 | Role=member; Browser=Chrome; Flag=off |
| TCN-001-CI04 | Role=member; Browser=Edge; Flag=on |
"""
        expected = {
            "known_test_requirements": ["TR-001"],
            "known_authorities": ["SPEC-001"],
            "pairwise": {
                "factors": {
                    "Role": ["admin", "member"],
                    "Browser": ["Chrome", "Edge"],
                    "Flag": ["on", "off"],
                },
                "forbidden_constraints": [],
                "require_pairwise": True,
            },
        }
        self.assert_passes("test-condition-design", text, expected)
        missing = text.replace(
            "| TCN-001-CI04 | Role=member; Browser=Edge; Flag=on |\n", ""
        )
        self.assert_fails("test-condition-design", missing, expected, "TCN-D015")

    def test_pairwise_generated_coverage_item_integrity(self):
        text, expected = self._pairwise_base()
        self.assert_fails(
            "test-condition-design",
            text.replace("| TCN-001-CI01 | A=0; B=0 |", "| TCN-001-CI99 | A=0; B=0 |"),
            expected,
            "TCN-D026",
        )
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

    def test_state_transition_requires_existing_coverage_item(self):
        text, expected = self._pairwise_base()
        text += """\n## 状態遷移表
| 現在状態 | イベント / 操作 | 期待する次状態 / 結果 | 対応カバレッジ項目ID |
| --- | --- | --- | --- |
| draft | publish | published | TCN-999-CI99 |
"""
        expected.pop("pairwise")
        expected["required_transitions"] = [
            {"from": "draft", "event": "publish", "to": "published"}
        ]
        self.assert_fails("test-condition-design", text, expected, "TCN-D016")

    def test_disposition_targets_must_exist_when_fixture_sets_are_present(self):
        tr = """# TR
## テスト要求一覧
| テスト要求ID | テスト要求 | 現在有効な仕様根拠 | 関連プロダクトリスク | 優先度 | テストレベル / 観測方法 |
| --- | --- | --- | --- | --- | --- |
| TR-001 | 保存を検証 | SPEC-001 | RISK-001 | 高 | システム / UI |
## テスト要求を作らない上流項目
| 上流ID | 種別 | 扱い | 理由 / 根拠 |
| --- | --- | --- | --- |
| SPEC-999 | 仕様根拠 | 対象外 | スコープ外 |
"""
        self.assert_fails(
            "test-requirement-design",
            tr,
            {"known_authorities": ["SPEC-001"], "known_product_risks": ["RISK-001"]},
            "TR-D013",
        )

        risk_disposition = """# TR
## テスト要求一覧
| テスト要求ID | テスト要求 | 現在有効な仕様根拠 | 関連プロダクトリスク | 優先度 | テストレベル / 観測方法 |
| --- | --- | --- | --- | --- | --- |
| TR-001 | 保存を検証 | SPEC-001 | | 高 | システム / UI |
## テスト要求を作らない上流項目
| 上流ID | 種別 | 扱い | 理由 / 根拠 |
| --- | --- | --- | --- |
| RISK-001 | プロダクトリスク | 対象外 | スコープ外 |
"""
        risk_expected = {
            "known_authorities": ["SPEC-001"],
            "product_risk_levels": {"RISK-001": "高"},
        }
        self.assert_passes("test-requirement-design", risk_disposition, risk_expected)
        self.assert_fails(
            "test-requirement-design",
            risk_disposition.replace(
                "| RISK-001 | プロダクトリスク |", "| RISK-999 | プロダクトリスク |"
            ),
            risk_expected,
            "TR-D013",
        )

        tcn, expected = self._pairwise_base()
        tcn = tcn.replace(
            "| --- | --- | --- |\n## テスト観点",
            "| --- | --- | --- |\n| TR-999 | 対象外 | 理由 |\n## テスト観点",
        )
        self.assert_fails("test-condition-design", tcn, expected, "TCN-D029")

        tc = """# TC
## テストケース一覧
| テストケースID | タイトル / 目的 | 関連観点ID | 関連カバレッジ項目ID | 関連テスト要求ID | 優先度 | 前提条件 | テストデータ | 実施手順 | 期待結果 | 期待結果の根拠 | 備考 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| TC-001 | 保存 | TCN-001 | TCN-001-CI01 | TR-001 | 高 | ログイン済み | valid | 保存する | 保存済み表示 | SPEC-001 | |
## テストケースへ展開しないカバレッジ項目 / テスト条件
| 上流ID | 種別 | 扱い | 理由 / 根拠 |
| --- | --- | --- | --- |
| TCN-999-CI99 | カバレッジ項目 | 対象外 | スコープ外 |
"""
        tc_expected = {
            "known_test_conditions": ["TCN-001"],
            "known_coverage_items": ["TCN-001-CI01"],
            "known_test_requirements": ["TR-001"],
            "known_authorities": ["SPEC-001"],
        }
        self.assert_fails("test-case-design", tc, tc_expected, "TC-D014")

    def test_fixture_required_tr_links_and_dispositions(self):
        text = """# TR
## テスト要求一覧
| テスト要求ID | テスト要求 | 現在有効な仕様根拠 | 関連プロダクトリスク | 優先度 | テストレベル / 観測方法 |
| --- | --- | --- | --- | --- | --- |
| TR-001 | 保存条件を検証 | SPEC-001 | RISK-001, RISK-002 | 高 | システム / UI |
## テスト要求を作らない上流項目
| 上流ID | 種別 | 扱い | 理由 / 根拠 |
| --- | --- | --- | --- |
| SPEC-002 | 仕様根拠 | 対象外 | 今回の対象外 |
"""
        expected = {
            "known_authorities": ["SPEC-001", "SPEC-002"],
            "known_product_risks": ["RISK-001", "RISK-002"],
            "product_risk_levels": {"RISK-001": "高", "RISK-002": "中"},
            "required_linked_upstream_ids": ["SPEC-001", "RISK-001", "RISK-002"],
            "expected_dispositions": {"SPEC-002": "対象外"},
        }
        self.assert_passes("test-requirement-design", text, expected)

        risk_as_disposition = text.replace("RISK-001, RISK-002", "RISK-001").replace(
            "| SPEC-002 | 仕様根拠 | 対象外 | 今回の対象外 |",
            "| SPEC-002 | 仕様根拠 | 対象外 | 今回の対象外 |\n| RISK-002 | プロダクトリスク | 対象外 | 今回の対象外 |",
        )
        self.assert_fails(
            "test-requirement-design", risk_as_disposition, expected, "TR-D014"
        )
        self.assert_fails(
            "test-requirement-design",
            text.replace("| SPEC-002 | 仕様根拠 | 対象外 | 今回の対象外 |\n", ""),
            expected,
            "TR-D015",
        )
        self.assert_fails(
            "test-requirement-design",
            text.replace(
                "| SPEC-002 | 仕様根拠 | 対象外 |",
                "| SPEC-002 | 仕様根拠 | 残存リスク |",
            ),
            expected,
            "TR-D015",
        )

    def test_missing_source_content_is_blocked_in_test_design_skills(self):
        tc_block = """# TC
## テストケース一覧
| テストケースID | タイトル / 目的 | 関連観点ID | 関連カバレッジ項目ID | 関連テスト要求ID | 優先度 | 前提条件 | テストデータ | 実施手順 | 期待結果 | 期待結果の根拠 | 備考 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
## テストケースへ展開しないカバレッジ項目 / テスト条件
| 上流ID | 種別 | 扱い | 理由 / 根拠 |
| --- | --- | --- | --- |
| TCN-001 | テスト条件 | ブロック中 | 条件本文がなく手順を決められない |
| TCN-001-CI01 | カバレッジ項目 | ブロック中 | 項目本文と有効な仕様根拠がない |
"""
        tc_expected = {
            "known_test_requirements": ["TR-001"],
            "known_test_conditions": ["TCN-001"],
            "known_coverage_items": ["TCN-001-CI01"],
            "coverage_closure_ids": ["TCN-001-CI01"],
            "known_authorities": ["SPEC-001"],
            "expected_blocked_upstream_ids": ["TCN-001", "TCN-001-CI01"],
        }
        self.assert_passes("test-case-design", tc_block, tc_expected)
        combined_ids = tc_block.replace(
            "| TCN-001 | テスト条件 |",
            "| TR-001 / TCN-001 | テスト条件 |",
        )
        self.assert_passes("test-case-design", combined_ids, tc_expected)
        self.assert_fails(
            "test-case-design",
            tc_block.replace(
                "TCN-001-CI01 | カバレッジ項目 | ブロック中",
                "TCN-001-CI01 | カバレッジ項目 | 対象外",
            ),
            tc_expected,
            "TC-D015",
        )
        invented_case = tc_block.replace(
            "## テストケースへ展開しないカバレッジ項目 / テスト条件",
            "| TC-001 | invented test | TCN-001 | TCN-001-CI01 | TR-001 | 高 | start | data | action | saved | 期待結果1→SPEC-001 | |\n"
            "## テストケースへ展開しないカバレッジ項目 / テスト条件",
        )
        self.assert_fails("test-case-design", invented_case, tc_expected, "TC-D015")

        tr_block = """# TR
## テスト要求一覧
| テスト要求ID | 関連AC ID | テスト要求 | 現在有効な仕様根拠 | 関連プロダクトリスク | 優先度 | テストレベル / 観測方法 |
| --- | --- | --- | --- | --- | --- | --- |
## テスト要求を作らない上流項目
| 上流ID | 種別 | 扱い | 理由 / 根拠 |
| --- | --- | --- | --- |
| SPEC-001 | 仕様根拠 | ブロック中 | 仕様本文と現行性がない |
| RISK-001 | プロダクトリスク | ブロック中 | リスク内容がない |
"""
        tr_expected = {
            "known_authorities": ["SPEC-001"],
            "known_acceptance_criteria": [],
            "known_product_risks": ["RISK-001"],
            "product_risk_levels": {"RISK-001": "中"},
            "expected_blocked_upstream_ids": ["SPEC-001", "RISK-001"],
        }
        self.assert_passes("test-requirement-design", tr_block, tr_expected)
        self.assert_fails(
            "test-requirement-design",
            tr_block.replace(
                "SPEC-001 | 仕様根拠 | ブロック中", "SPEC-001 | 仕様根拠 | 対象外"
            ),
            tr_expected,
            "TR-D018",
        )
        invented_requirement = tr_block.replace(
            "## テスト要求を作らない上流項目",
            "| TR-001 | - | invented requirement | SPEC-001 | RISK-001 | 中 | system / UI |\n"
            "## テスト要求を作らない上流項目",
        )
        self.assert_fails(
            "test-requirement-design",
            invented_requirement,
            tr_expected,
            "TR-D018",
        )

    def test_fixture_numbered_authority_mapping(self):
        text = """# TC
## テストケース一覧
| テストケースID | タイトル / 目的 | 関連観点ID | 関連カバレッジ項目ID | 関連テスト要求ID | 優先度 | 前提条件 | テストデータ | 実施手順 | 期待結果 | 期待結果の根拠 | 備考 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| TC-001 | 保存 | TCN-001 | TCN-001-CI01, TCN-001-CI02 | TR-001 | 高 | ログイン済み | valid | 保存する | 期待結果1: 保存済み表示; 期待結果2: 編集不可表示 | 期待結果1→SPEC-001; 期待結果2→DEC-001 | |
## テストケースへ展開しないカバレッジ項目 / テスト条件
| 上流ID | 種別 | 扱い | 理由 / 根拠 |
| --- | --- | --- | --- |
"""
        expected = {
            "known_test_requirements": ["TR-001"],
            "known_test_conditions": ["TCN-001"],
            "known_coverage_items": ["TCN-001-CI01", "TCN-001-CI02"],
            "coverage_closure_ids": ["TCN-001-CI01", "TCN-001-CI02"],
            "known_authorities": ["SPEC-001", "DEC-001"],
            "coverage_item_priorities": {"TCN-001-CI01": "中", "TCN-001-CI02": "高"},
            "expected_numbered_authorities": {
                "TC-001": {"1": ["SPEC-001"], "2": ["DEC-001"]}
            },
        }
        self.assert_passes("test-case-design", text, expected)

        unnumbered = text.replace(
            "期待結果1: 保存済み表示; 期待結果2: 編集不可表示",
            "保存済み表示; 編集不可表示",
        ).replace("期待結果1→SPEC-001; 期待結果2→DEC-001", "SPEC-001; DEC-001")
        self.assert_fails("test-case-design", unnumbered, expected, "TC-D011")
        reversed_mapping = text.replace(
            "期待結果1→SPEC-001; 期待結果2→DEC-001",
            "期待結果1→DEC-001; 期待結果2→SPEC-001",
        )
        self.assert_fails("test-case-design", reversed_mapping, expected, "TC-D011")
        missing_second = text.replace(
            "期待結果1→SPEC-001; 期待結果2→DEC-001", "期待結果1→SPEC-001"
        )
        self.assert_fails("test-case-design", missing_second, expected, "TC-D011")

    def test_coverage_expected_fix_target_must_exist(self):
        text = """# Coverage
## カバレッジマトリクス
| 上流層 | 上流ID / 挙動 | 下流層 | 下流ID / 扱い | カバレッジ | 修正Skill / 層 |
| --- | --- | --- | --- | --- | --- |
| TR | TR-001 | TCN | TCN-001 | 網羅済み | test-condition-design |
"""
        self.assert_fails(
            "coverage-analysis",
            text,
            {"expected_fix_skills": {"TCN-001-CI01": "test-condition-design"}},
            "COV-D005",
        )

    def test_major_residual_acceptance_must_match_fixture_approval(self):
        text = self._review_base().replace(
            "| 修正済み | |", "| 残存リスクとして受容 | APR-999 |"
        )
        self.assert_fails(
            "adversarial-review",
            text,
            {
                "known_artifact_ids": ["TC-001"],
                "approved_risk_acceptances": {"REV-001": "APR-001"},
            },
            "REV-D008",
        )

    def test_adversarial_repair_targets_and_summary_contract(self):
        expected = {"known_artifact_ids": ["TC-001"]}
        self.assert_passes(
            "adversarial-review", self._review_base("test-case-design"), expected
        )
        self.assert_passes(
            "adversarial-review",
            self._review_base("案件コンテキスト / 仕様決定"),
            expected,
        )
        self.assert_fails(
            "adversarial-review",
            self._review_base("unknown-target"),
            expected,
            "REV-D006",
        )
        self.assert_fails(
            "adversarial-review",
            self._review_base().replace("| 提案 | 0 |", "| unknown | 0 |"),
            expected,
            "REV-D013",
        )
        self.assert_fails(
            "adversarial-review",
            self._review_base().replace("| 軽微 | 0 |", "| 重大 | 0 |"),
            expected,
            "REV-D014",
        )

    def test_test_case_disposition_accepts_any_known_upstream_type(self):
        text = """## テストケース一覧
| テストケースID | 期待結果 | 期待結果の根拠 |
| --- | --- | --- |
## テストケースへ展開しないカバレッジ項目 / テスト条件
| 上流ID | 扱い |
| --- | --- |
| TR-001 | ブロック中 |
| TCN-001 | ブロック中 |
| TCN-001-CI01 | ブロック中 |
| SPEC-001 | ブロック中 |
"""
        expected = {
            "known_test_requirements": ["TR-001"],
            "known_test_conditions": ["TCN-001"],
            "known_coverage_items": ["TCN-001-CI01"],
            "known_authorities": ["SPEC-001"],
        }
        result = VALIDATORS["test-case-design"](text, expected, "TC-UPSTREAM").to_dict()
        assertions = {item["id"]: item for item in result["assertions"]}
        self.assertEqual(assertions["TC-D014"]["status"], "pass")

        unknown = text.replace("TR-001", "TR-999")
        result = VALIDATORS["test-case-design"](
            unknown, expected, "TC-UPSTREAM"
        ).to_dict()
        assertions = {item["id"]: item for item in result["assertions"]}
        self.assertEqual(assertions["TC-D014"]["status"], "fail")
        self.assertIn("TR-999", assertions["TC-D014"]["evidence"])

    def test_adversarial_fixture_expected_attributes(self):
        expected = {
            "known_artifact_ids": ["TC-001"],
            "expected_defects": [
                {
                    "target_id": "TC-001",
                    "contains": "存在しないAuthority ID",
                    "severity": "重大",
                    "repair_target": "test-case-design",
                }
            ],
        }
        base = self._review_base().replace("仕様根拠参照なし", "存在しないAuthority ID")
        self.assert_passes("adversarial-review", base, expected)

        severity_mismatch = (
            base.replace("| 重大 | 1 |", "| 重大 | 0 |")
            .replace("| 軽微 | 0 |", "| 軽微 | 1 |")
            .replace("| REV-001 | 重大 |", "| REV-001 | 軽微 |")
        )
        self.assert_fails("adversarial-review", severity_mismatch, expected, "REV-D010")
        self.assert_fails(
            "adversarial-review",
            self._review_base("spec-analysis"),
            expected,
            "REV-D010",
        )

        optional_expected = {
            "known_artifact_ids": ["TC-001"],
            "expected_defects": [{"target_id": "TC-001", "contains": "仕様根拠"}],
        }
        optional_text = (
            self._review_base("spec-analysis")
            .replace("| 重大 | 1 |", "| 重大 | 0 |")
            .replace("| 軽微 | 0 |", "| 軽微 | 1 |")
            .replace("| REV-001 | 重大 |", "| REV-001 | 軽微 |")
        )
        self.assert_passes("adversarial-review", optional_text, optional_expected)

    def test_adversarial_finding_required_fields(self):
        text = self._review_base().replace(
            "| REV-001 | 重大 | TC-001 | 根拠が不足 | 仕様根拠参照なし | 合否判定不能 | 根拠を追加 | test-case-design |",
            "| REV-001 | 重大 | TC-001 |  |  |  | 根拠を追加 |  |",
        )
        self.assert_fails(
            "adversarial-review", text, {"known_artifact_ids": ["TC-001"]}, "REV-D012"
        )

    def test_workflow_state_invariants_and_duplicate_skill(self):
        def workflow(overall: str, rows: str) -> str:
            return f"""- ワークフロー全体状態: {overall}
| Skill | 対象 / 実行範囲 | 状態 | 成果物 / バージョン | ブロッカー / 備考 |
| --- | --- | --- | --- | --- |
{rows}
"""

        self.assert_fails(
            "qa-workflow",
            workflow("完了", "| test-case-design |  | 実行中 | v1 | |"),
            {},
            "WF-D004",
        )
        self.assert_fails(
            "qa-workflow",
            workflow(
                "部分完了（ブロック中あり）", "| test-case-design |  | 完了 | v1 | |"
            ),
            {},
            "WF-D010",
        )
        self.assert_fails(
            "qa-workflow",
            workflow("ブロック中", "| test-case-design |  | 完了 | v1 | |"),
            {},
            "WF-D011",
        )
        duplicate = workflow(
            "実行中",
            "| test-case-design |  | 実行中 | v1 | |\n| test-case-design |  | 完了 | v1 | |",
        )
        self.assert_fails("qa-workflow", duplicate, {}, "WF-D012")

    def test_workflow_template_keeps_unused_multiskill_targets_blank(self):
        template = (
            Path(__file__).resolve().parents[4]
            / "skills/qa-workflow/assets/workflow-state-template.md"
        ).read_text(encoding="utf-8")
        for skill in (
            "test-analysis",
            "coverage-analysis",
            "adversarial-review",
            "regression-testing",
            "exploratory-testing",
            "qa-knowledge",
            "usability-inspection",
        ):
            match = re.search(rf"(?m)^\|\s*{re.escape(skill)}\s*\|([^|]*)\|", template)
            self.assertIsNotNone(match, skill)
            self.assertEqual(match.group(1).strip(), "", skill)

    def test_workflow_fixture_expected_states(self):
        expected = {
            "expected_start_skill": "test-analysis",
            "expected_start_target": "テスト分析",
            "expected_final_skill": "test-case-design",
            "expected_final_target": "",
            "expected_skills": [
                "test-analysis",
            ],
            "expected_overall_state": "実行中",
            "expected_skill_states": {
                "test-analysis": "実行中",
            },
        }

        def workflow(
            overall: str,
            test_analysis_state: str,
            tr_state: str = "完了",
            tcn_state: str = "完了",
            tc_state: str = "完了",
        ) -> str:
            return f"""- ワークフロー全体状態: {overall}
- 開始Skill: test-analysis
- 開始対象 / 実行範囲: テスト分析
- 最終Skill: test-case-design
- 最終対象 / 実行範囲:
| Skill | 対象 / 実行範囲 | 状態 | 成果物 / バージョン | ブロッカー / 備考 |
| --- | --- | --- | --- | --- |
| test-analysis | テスト分析 | {test_analysis_state} | Risk | |
| test-requirement-design |  | {tr_state} | TR | |
| test-condition-design |  | {tcn_state} | TCN | |
| test-case-design |  | {tc_state} | TC | |
"""

        self.assert_passes(
            "qa-workflow",
            workflow("実行中", "実行中", "未開始", "未開始", "未開始"),
            expected,
        )
        self.assert_fails(
            "qa-workflow", workflow("完了", "実行中"), expected, "WF-D013"
        )
        self.assert_fails(
            "qa-workflow",
            workflow("実行中", "ブロック中"),
            expected,
            "WF-D014",
        )

    def test_test_case_priority_override_requires_reason(self):
        base = """# TC
## テストケース一覧
| テストケースID | タイトル / 目的 | 関連観点ID | 関連カバレッジ項目ID | 関連テスト要求ID | 優先度 | 前提条件 | テストデータ | 実施手順 | 期待結果 | 期待結果の根拠 | 備考 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| TC-001 | 保存 | TCN-001 | TCN-001-CI01 | TR-001 | 低 | ログイン済み | valid | 保存する | 保存済み表示 | SPEC-001 | {note} |
## テストケースへ展開しないカバレッジ項目 / テスト条件
| 上流ID | 種別 | 扱い | 理由 / 根拠 |
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
        self.assert_passes(
            "test-case-design",
            base.format(note="低リスクの補助確認として優先度を下げる"),
            expected,
        )

    def test_spec_package_headings_are_recognized_as_file_boundaries(self):
        expected = {
            "required_package_files": [
                "00_scope_and_context.md",
                "07_current_unknowns.md",
            ]
        }
        text = (
            self._spec_base()
            + "\n"
            + "\n".join(
                [
                    "### Package file: 00_scope_and_context.md",
                    "payload",
                    "### Package file: 07_current_unknowns.md",
                    "payload",
                ]
            )
        )
        result = VALIDATORS["spec-analysis"](text, expected, "SPEC-TEST").to_dict()
        assertions = {item["id"]: item for item in result["assertions"]}
        self.assertEqual(assertions["SPEC-D020"]["status"], "pass")

        prose_only = self._spec_base() + "\nPackage file: 00_scope_and_context.md"
        result = VALIDATORS["spec-analysis"](
            prose_only, expected, "SPEC-TEST"
        ).to_dict()
        assertions = {item["id"]: item for item in result["assertions"]}
        self.assertEqual(assertions["SPEC-D020"]["status"], "fail")

        empty_heading = (
            self._spec_base()
            + "\n### Package file: 00_scope_and_context.md\n\n### Package file: 07_current_unknowns.md\npayload"
        )
        result = VALIDATORS["spec-analysis"](
            empty_heading, expected, "SPEC-TEST"
        ).to_dict()
        assertions = {item["id"]: item for item in result["assertions"]}
        self.assertEqual(assertions["SPEC-D020"]["status"], "fail")

        filename_heading = (
            self._spec_base()
            + "\n## 00_scope_and_context.md\npayload\n## 07_current_unknowns.md\npayload"
        )
        result = VALIDATORS["spec-analysis"](
            filename_heading, expected, "SPEC-TEST"
        ).to_dict()
        assertions = {item["id"]: item for item in result["assertions"]}
        self.assertEqual(assertions["SPEC-D020"]["status"], "pass")

        level_three_filename_heading = (
            self._spec_base()
            + "\n### 00_scope_and_context.md\npayload"
            + "\n### 07_current_unknowns.md\npayload"
        )
        result = VALIDATORS["spec-analysis"](
            level_three_filename_heading, expected, "SPEC-TEST"
        ).to_dict()
        assertions = {item["id"]: item for item in result["assertions"]}
        self.assertEqual(assertions["SPEC-D020"]["status"], "pass")

        package_bundle = (
            self._spec_base()
            + "\n"
            + "\n".join(
                [
                    "## File: `00_scope_and_context.md`",
                    "# Scope and Context",
                    "\n## Nested payload heading\ncontent",
                    "## File: `07_current_unknowns.md`",
                    "# Current Unknowns",
                    "\n## Nested payload heading\ncontent",
                ]
            )
        )
        result = VALIDATORS["spec-analysis"](
            package_bundle, expected, "SPEC-TEST"
        ).to_dict()
        assertions = {item["id"]: item for item in result["assertions"]}
        self.assertEqual(assertions["SPEC-D020"]["status"], "pass")

        plain_package_bundle = (
            self._spec_base()
            + "\n"
            + "\n".join(
                [
                    "## File: 00_scope_and_context.md",
                    "# Scope and Context",
                    "## File: 07_current_unknowns.md",
                    "# Current Unknowns",
                    "payload",
                ]
            )
        )
        result = VALIDATORS["spec-analysis"](
            plain_package_bundle, expected, "SPEC-TEST"
        ).to_dict()
        assertions = {item["id"]: item for item in result["assertions"]}
        self.assertEqual(assertions["SPEC-D020"]["status"], "pass")

        empty_package_file = (
            self._spec_base()
            + "\n"
            + "\n".join(
                [
                    "## File: `00_scope_and_context.md`",
                    "## File: `07_current_unknowns.md`",
                    "# Current Unknowns",
                    "payload",
                ]
            )
        )
        result = VALIDATORS["spec-analysis"](
            empty_package_file, expected, "SPEC-TEST"
        ).to_dict()
        assertions = {item["id"]: item for item in result["assertions"]}
        self.assertEqual(assertions["SPEC-D020"]["status"], "fail")

        empty_plain_package_file = (
            self._spec_base()
            + "\n"
            + "\n".join(
                [
                    "## File: 00_scope_and_context.md",
                    "## File: 07_current_unknowns.md",
                    "# Current Unknowns",
                    "payload",
                ]
            )
        )
        result = VALIDATORS["spec-analysis"](
            empty_plain_package_file, expected, "SPEC-TEST"
        ).to_dict()
        assertions = {item["id"]: item for item in result["assertions"]}
        self.assertEqual(assertions["SPEC-D020"]["status"], "fail")

    def test_coverage_dash_is_empty_model_key(self):
        text = """## カバレッジマトリクス
| 上流層 | 上流ID / 挙動 | 下流層 | 下流ID / 扱い | カバレッジ | プロダクトリスク / 優先度 | 根拠 / ギャップ | 推奨対応 | 修正Skill / 層 | Model Key |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| SPEC | SPEC-001 | TC | TC-001 | covered | 高 | 根拠あり | 保持 | test-case-design | — |
"""
        result = VALIDATORS["coverage-analysis"](text, {}, "COV-TEST").to_dict()
        assertion = next(a for a in result["assertions"] if a["id"] == "COV-D013")
        self.assertEqual(assertion["status"], "pass", assertion)

        text = text.replace(
            "| test-case-design | — |", "| test-case-design | invalid-key |"
        )
        result = VALIDATORS["coverage-analysis"](text, {}, "COV-TEST").to_dict()
        assertion = next(a for a in result["assertions"] if a["id"] == "COV-D013")
        self.assertEqual(assertion["status"], "fail", assertion)

    def test_qa_workflow_requires_canonical_targets_only_for_used_multi_use_skills(
        self,
    ):
        text = """- ワークフロー全体状態: 実行中
- 開始Skill: test-case-design
- 開始対象 / 実行範囲: checkoutの注文確定
- 最終Skill: test-case-design
- 最終対象 / 実行範囲: checkoutの注文確定
| Skill | 対象 / 実行範囲 | 状態 |
| --- | --- | --- |
| test-case-design | checkoutの注文確定 | 実行中 |
"""
        result = VALIDATORS["qa-workflow"](text, {}, "WF-TEST").to_dict()
        assertions = {a["id"]: a for a in result["assertions"]}
        self.assertEqual(assertions["WF-D016"]["status"], "fail")
        self.assertEqual(assertions["WF-D017"]["status"], "fail")

        multi_use = text.replace("test-case-design", "coverage-analysis").replace(
            "checkoutの注文確定", "任意の範囲"
        )
        result = VALIDATORS["qa-workflow"](multi_use, {}, "WF-TEST").to_dict()
        assertions = {a["id"]: a for a in result["assertions"]}
        self.assertEqual(assertions["WF-D016"]["status"], "fail")
        self.assertEqual(assertions["WF-D017"]["status"], "fail")

        omitted = """- ワークフロー全体状態: 実行中
- 開始Skill: test-analysis
- 開始対象 / 実行範囲: テスト分析
- 最終Skill: test-case-design
- 最終対象 / 実行範囲:
| Skill | 対象 / 実行範囲 | 状態 |
| --- | --- | --- |
| test-analysis | テスト分析 | 実行中 |
| coverage-analysis | — | 省略 |
| test-case-design |  | 未開始 |
"""
        result = VALIDATORS["qa-workflow"](omitted, {}, "WF-TEST").to_dict()
        assertions = {a["id"]: a for a in result["assertions"]}
        self.assertEqual(assertions["WF-D016"]["status"], "pass")
        self.assertEqual(assertions["WF-D017"]["status"], "pass")

        reused_coverage = omitted.replace(
            "| coverage-analysis | — | 省略 |",
            "| coverage-analysis | テスト設計 | 再利用 |",
        )
        result = VALIDATORS["qa-workflow"](reused_coverage, {}, "WF-TEST").to_dict()
        assertions = {a["id"]: a for a in result["assertions"]}
        self.assertEqual(assertions["WF-D016"]["status"], "pass")
        self.assertEqual(assertions["WF-D017"]["status"], "pass")

    def test_wcag_report_accepts_canonical_headings_and_no_score_marker(self):
        text = """# WCAG-EM report
## Evaluation Input
## Step 1: Define evaluation scope
## Step 2: Explore the target Web product
## Step 3: Select representative samples
## Step 4: Audit the selected sample
### Criterion Evaluation Plan
### Sample Evaluation Results
## Step 5: Report the evaluation findings
| aggregated score | not generated |

No conformance conclusion is available. Neither conformance nor nonconformance assessed.
"""
        expected = {
            "required_sections": [
                "Step 1: Define evaluation scope",
                "Step 2: Explore the target Web product",
                "Step 3: Select representative samples",
                "Step 4: Audit the selected sample",
                "Step 5: Report the evaluation findings",
                "Criterion Evaluation Plan",
                "Sample Evaluation Results",
            ],
            "forbidden_tokens": ["aggregated score"],
            "required_tokens": ["Neither conformance nor nonconformance assessed"],
        }
        result = VALIDATORS["wcag-conformance-evaluation"](
            text, expected, "WCAG-REPORT-TEST"
        ).to_dict()
        assertions = {item["id"]: item for item in result["assertions"]}
        self.assertEqual(assertions["WCAG-D002"]["status"], "pass")
        self.assertEqual(assertions["WCAG-D004"]["status"], "pass")

        actual_score = text.replace(
            "| aggregated score | not generated |", "| aggregated score | 8/10 |"
        )
        result = VALIDATORS["wcag-conformance-evaluation"](
            actual_score, expected, "WCAG-REPORT-TEST"
        ).to_dict()
        assertions = {item["id"]: item for item in result["assertions"]}
        self.assertEqual(assertions["WCAG-D004"]["status"], "fail")

        no_score_statement = text.replace(
            "No conformance conclusion is available.",
            "No conformance conclusion or aggregated score is reported.",
        )
        result = VALIDATORS["wcag-conformance-evaluation"](
            no_score_statement, expected, "WCAG-REPORT-TEST"
        ).to_dict()
        assertions = {item["id"]: item for item in result["assertions"]}
        self.assertEqual(assertions["WCAG-D004"]["status"], "pass")

        inline_score = text.replace(
            "No conformance conclusion is available.",
            "The aggregated score is 8/10.",
        )
        result = VALIDATORS["wcag-conformance-evaluation"](
            inline_score, expected, "WCAG-REPORT-TEST"
        ).to_dict()
        assertions = {item["id"]: item for item in result["assertions"]}
        self.assertEqual(assertions["WCAG-D004"]["status"], "fail")

        past_tense_score = text.replace(
            "No conformance conclusion is available.",
            "The aggregated score was 8/10.",
        )
        result = VALIDATORS["wcag-conformance-evaluation"](
            past_tense_score, expected, "WCAG-REPORT-TEST"
        ).to_dict()
        assertions = {item["id"]: item for item in result["assertions"]}
        self.assertEqual(assertions["WCAG-D004"]["status"], "fail")

        multi_column_score = text.replace(
            "| aggregated score | not generated |",
            "| aggregated score | 8/10 | computed from the sample set |",
        )
        result = VALIDATORS["wcag-conformance-evaluation"](
            multi_column_score, expected, "WCAG-REPORT-TEST"
        ).to_dict()
        assertions = {item["id"]: item for item in result["assertions"]}
        self.assertEqual(assertions["WCAG-D004"]["status"], "fail")

        missing_section = text.replace(
            "## Step 4: Audit the selected sample", "## Step 4: omitted"
        )
        result = VALIDATORS["wcag-conformance-evaluation"](
            missing_section, expected, "WCAG-REPORT-TEST"
        ).to_dict()
        assertions = {item["id"]: item for item in result["assertions"]}
        self.assertEqual(assertions["WCAG-D002"]["status"], "fail")

        missing_conclusion = text.replace(
            "Neither conformance nor nonconformance assessed.", ""
        )
        result = VALIDATORS["wcag-conformance-evaluation"](
            missing_conclusion, expected, "WCAG-REPORT-TEST"
        ).to_dict()
        assertions = {item["id"]: item for item in result["assertions"]}
        self.assertEqual(assertions["WCAG-D003"]["status"], "fail")

    def test_usability_inspection_requires_real_scope_closure_or_explicit_block(self):
        prefix = """## Scope and closure
| Scope ref | Aspect | Decision | Outcome | Reason / applicability | Evidence refs |
| --- | --- | --- | --- | --- | --- |
"""
        blocked = (
            prefix
            + "\nScope initialization stopped before a scope skeleton was created."
        )
        result = VALIDATORS["usability-inspection"](
            blocked, {}, "UI-CLOSURE-TEST"
        ).to_dict()
        assertions = {item["id"]: item for item in result["assertions"]}
        self.assertEqual(assertions["UI-D004"]["status"], "pass")

        blocked_with_article = (
            prefix
            + "\nScope initialization stopped before the scope skeleton was created."
        )
        result = VALIDATORS["usability-inspection"](
            blocked_with_article, {}, "UI-CLOSURE-TEST"
        ).to_dict()
        assertions = {item["id"]: item for item in result["assertions"]}
        self.assertEqual(assertions["UI-D004"]["status"], "pass")

        localized_block = (
            prefix + "\n対象と観点が未確定のため、scope初期化前に停止しました。"
        )
        result = VALIDATORS["usability-inspection"](
            localized_block, {}, "UI-CLOSURE-TEST"
        ).to_dict()
        assertions = {item["id"]: item for item in result["assertions"]}
        self.assertEqual(assertions["UI-D004"]["status"], "pass")

        japanese_equivalent = (
            prefix + "\nスコープ初期化はscope skeletonを作る前に停止しました。"
        )
        result = VALIDATORS["usability-inspection"](
            japanese_equivalent, {}, "UI-CLOSURE-TEST"
        ).to_dict()
        assertions = {item["id"]: item for item in result["assertions"]}
        self.assertEqual(assertions["UI-D004"]["status"], "pass")

        missing_scope_table = "## Scope and closure\n\n" + (
            "対象と観点が未確定のため、scope初期化前に停止しました。"
        )
        result = VALIDATORS["usability-inspection"](
            missing_scope_table, {}, "UI-CLOSURE-TEST"
        ).to_dict()
        assertions = {item["id"]: item for item in result["assertions"]}
        self.assertEqual(assertions["UI-D004"]["status"], "fail")

        false_closure = prefix + "\n| — | — | — | — | — | — |\n判定不能: 0"
        result = VALIDATORS["usability-inspection"](
            false_closure, {}, "UI-CLOSURE-TEST"
        ).to_dict()
        assertions = {item["id"]: item for item in result["assertions"]}
        self.assertEqual(assertions["UI-D004"]["status"], "fail")

        unresolved_row = (
            prefix
            + "| SCOPE-001 | Keyboard | unresolved | 判定不能 | Target evidence absent | — |\n"
        )
        result = VALIDATORS["usability-inspection"](
            unresolved_row, {}, "UI-CLOSURE-TEST"
        ).to_dict()
        assertions = {item["id"]: item for item in result["assertions"]}
        self.assertEqual(assertions["UI-D004"]["status"], "pass")

        unreasoned_row = (
            prefix + "| SCOPE-001 | Keyboard | unresolved | 判定不能 | | — |\n"
        )
        result = VALIDATORS["usability-inspection"](
            unreasoned_row, {}, "UI-CLOSURE-TEST"
        ).to_dict()
        assertions = {item["id"]: item for item in result["assertions"]}
        self.assertEqual(assertions["UI-D004"]["status"], "fail")

    def test_regression_validator_reports_malformed_container_shapes(self):
        artifact = {
            "artifact_type": "activity",
            "activity_ref": "ACT-FIXTURE",
            "snapshot_ref": "SNAP-FIXTURE",
            "scope_identity": "scope:fixture",
            "activity_state": "blocked",
            "source_executions": {},
            "route_results": [],
            "tc_execution_state": {"TC-001": "blocked"},
            "counts": {"auxiliary_testware_count": 0},
            "auxiliary_route_results": [],
            "cleanup_status": "未確認",
            "unresolved": ["fixture shape test"],
        }
        malformed_values = [
            ("source_executions", []),
            ("source_executions", None),
            ("source_executions", "execution-ref"),
            ("tc_execution_state", []),
            ("tc_execution_state", "executed"),
            ("counts", []),
            ("counts", 1),
            ("route_results", {}),
            ("route_results", None),
            ("auxiliary_route_results", None),
            ("source_executions", {"exec-1": []}),
            ("route_results", ["invalid-route"]),
            ("counts", {"auxiliary_testware_count": "0"}),
        ]
        for field, malformed in malformed_values:
            with self.subTest(field=field, malformed_type=type(malformed).__name__):
                candidate = dict(artifact)
                candidate[field] = malformed
                text = "```json\n" + json.dumps(candidate) + "\n```"
                result = VALIDATORS["regression-testing"](
                    text, {"artifact_type": "activity"}, "REG-SHAPE-TEST"
                ).to_dict()
                assertions = {a["id"]: a for a in result["assertions"]}
                self.assertEqual(result["status"], "fail")
                self.assertEqual(assertions["REG-D018"]["status"], "fail")
                self.assertTrue(assertions["REG-D018"]["evidence"])

        for field in ("source_executions", "route_results", "counts"):
            with self.subTest(kind="activity", missing_field=field):
                candidate = dict(artifact)
                candidate.pop(field, None)
                result = VALIDATORS["regression-testing"](
                    "```json\n" + json.dumps(candidate) + "\n```",
                    {"artifact_type": "activity"},
                    "REG-SHAPE-TEST",
                ).to_dict()
                assertions = {a["id"]: a for a in result["assertions"]}
                self.assertEqual(result["status"], "fail")
                self.assertEqual(assertions["REG-D018"]["status"], "fail")

        baseline_path = (
            Path(__file__).resolve().parents[4]
            / "skills/regression-testing/evals/output/cases/reg-out-001/output.md"
        )
        baseline_text = baseline_path.read_text(encoding="utf-8")
        baseline = json.loads(
            baseline_text.split("```json\n", 1)[1].split("\n```", 1)[0]
        )
        for field, malformed in [
            ("memberships", {}),
            ("source_revisions", None),
            ("member_tc_refs", {"TC-001": True}),
            ("member_tc_refs", None),
            ("coverage_gaps", {"scope_ref": "scope:refund"}),
            ("coverage_gaps", "scope:refund"),
            ("coverage_gaps", None),
        ]:
            with self.subTest(kind="baseline", field=field):
                candidate = dict(baseline)
                candidate[field] = malformed
                result = VALIDATORS["regression-testing"](
                    "```json\n" + json.dumps(candidate) + "\n```",
                    {"artifact_type": "baseline"},
                    "REG-SHAPE-TEST",
                ).to_dict()
                assertions = {a["id"]: a for a in result["assertions"]}
                self.assertEqual(result["status"], "fail")
                self.assertEqual(assertions["REG-D018"]["status"], "fail")

        missing_baseline_field = dict(baseline)
        missing_baseline_field.pop("memberships")
        result = VALIDATORS["regression-testing"](
            "```json\n" + json.dumps(missing_baseline_field) + "\n```",
            {"artifact_type": "baseline"},
            "REG-SHAPE-TEST",
        ).to_dict()
        assertions = {a["id"]: a for a in result["assertions"]}
        self.assertEqual(result["status"], "fail")
        self.assertEqual(assertions["REG-D018"]["status"], "fail")

        missing_coverage_gaps = dict(baseline)
        missing_coverage_gaps.pop("coverage_gaps")
        result = VALIDATORS["regression-testing"](
            "```json\n" + json.dumps(missing_coverage_gaps) + "\n```",
            {"artifact_type": "baseline"},
            "REG-SHAPE-TEST",
        ).to_dict()
        assertions = {a["id"]: a for a in result["assertions"]}
        self.assertEqual(result["status"], "fail")
        self.assertEqual(assertions["REG-D018"]["status"], "fail")

        expected_path = (
            Path(__file__).resolve().parents[4]
            / "skills/regression-testing/evals/output/cases/reg-out-001/expected.json"
        )
        expected = json.loads(expected_path.read_text(encoding="utf-8"))
        identity_doc = {
            "artifact_type": "baseline",
            "schema_version": "1",
            "baseline_ref": expected["expected_baseline_ref"],
            "discovery_snapshot_ref": "DS-fixture",
            "scope_refs": [],
            "unresolved_tc_refs": [],
            "undecided_tc_refs": [],
            "complete": True,
        }
        for baseline_ref, expected_status in (
            (expected["expected_baseline_ref"], "pass"),
            ("fixture:qa/regression/baseline/other", "fail"),
        ):
            candidate = {**identity_doc, "baseline_ref": baseline_ref}
            result = VALIDATORS["regression-testing"](
                "```json\n" + json.dumps(candidate) + "\n```",
                expected,
                "REG-IDENTITY-TEST",
            ).to_dict()
            assertions = {a["id"]: a for a in result["assertions"]}
            self.assertEqual(assertions["REG-D017"]["status"], expected_status)

        run_artifact = {
            "artifact_type": "run",
            "baseline": {},
            "selected_tc_refs": {},
            "required_routes": [],
            "auxiliary_testware_refs": [],
            "auxiliary_testware_count": 0,
        }
        result = VALIDATORS["regression-testing"](
            "```json\n" + json.dumps(run_artifact) + "\n```",
            {"artifact_type": "run"},
            "REG-SHAPE-TEST",
        ).to_dict()
        assertions = {a["id"]: a for a in result["assertions"]}
        self.assertEqual(result["status"], "fail")
        self.assertEqual(assertions["REG-D018"]["status"], "fail")

        for field, malformed in (
            ("baseline", []),
            ("selected_tc_refs", "TC-001"),
            ("required_routes", None),
            ("required_routes", {"route_type": "manual"}),
        ):
            with self.subTest(
                kind="run", field=field, malformed_type=type(malformed).__name__
            ):
                candidate = dict(run_artifact)
                candidate[field] = malformed
                result = VALIDATORS["regression-testing"](
                    "```json\n" + json.dumps(candidate) + "\n```",
                    {"artifact_type": "run"},
                    "REG-SHAPE-TEST",
                ).to_dict()
                assertions = {a["id"]: a for a in result["assertions"]}
                self.assertEqual(result["status"], "fail")
                self.assertEqual(assertions["REG-D018"]["status"], "fail")

        missing_run_field = dict(run_artifact)
        missing_run_field.pop("required_routes")
        result = VALIDATORS["regression-testing"](
            "```json\n" + json.dumps(missing_run_field) + "\n```",
            {"artifact_type": "run"},
            "REG-SHAPE-TEST",
        ).to_dict()
        assertions = {a["id"]: a for a in result["assertions"]}
        self.assertEqual(result["status"], "fail")
        self.assertEqual(assertions["REG-D018"]["status"], "fail")

    def test_regression_out002_blocks_without_inventing_activity_identity(self):
        repo_root = Path(__file__).resolve().parents[4]
        case_root = (
            repo_root / "skills/regression-testing/evals/output/cases/reg-out-002"
        )
        output = (case_root / "output.md").read_text(encoding="utf-8")
        expected = json.loads((case_root / "expected.json").read_text(encoding="utf-8"))
        result = VALIDATORS["regression-testing"](
            output, expected, "REG-OUT-002"
        ).to_dict()
        assertions = {item["id"]: item for item in result["assertions"]}
        self.assertEqual(assertions["REG-D001"]["status"], "pass")
        self.assertEqual(assertions["REG-D019"]["status"], "pass")

        runtime_diagnostic = (
            output
            + """
```json
{"valid": false, "issues": ["missing_source_execution_ref"]}
```
"""
        )
        result = VALIDATORS["regression-testing"](
            runtime_diagnostic, expected, "REG-OUT-002-RUNTIME-DIAGNOSTIC"
        ).to_dict()
        assertions = {item["id"]: item for item in result["assertions"]}
        self.assertEqual(assertions["REG-D001"]["status"], "fail")
        self.assertEqual(assertions["REG-D019"]["status"], "fail")

        invented = output + '\n```json\n{"artifact_type":"activity"}\n```\n'
        result = VALIDATORS["regression-testing"](
            invented, expected, "REG-OUT-002-ARTIFACT"
        ).to_dict()
        assertions = {item["id"]: item for item in result["assertions"]}
        self.assertEqual(assertions["REG-D001"]["status"], "fail")
        self.assertEqual(assertions["REG-D019"]["status"], "fail")

        missing_reason = output.replace("Activity identity", "unknown values")
        result = VALIDATORS["regression-testing"](
            missing_reason, expected, "REG-OUT-002-NO-IDENTITY-REASON"
        ).to_dict()
        assertions = {item["id"]: item for item in result["assertions"]}
        self.assertEqual(assertions["REG-D019"]["status"], "fail")

    def test_regression_template_only_shows_json_for_materialized_artifacts(self):
        repo_root = Path(__file__).resolve().parents[4]
        template = (
            repo_root / "skills/regression-testing/assets/output-template.md"
        ).read_text(encoding="utf-8")
        self.assertIn("preflightでmaterializeできない場合は", template)
        self.assertIn("JSON fenced blockを一切出力しません", template)

    def test_regression_activity_projects_source_execution_facts(self):
        activity = {
            "artifact_type": "activity",
            "activity_ref": "ACT-001",
            "snapshot_ref": "SNAP-001",
            "scope_identity": "scope-v1",
            "activity_state": "完了",
            "source_executions": {
                "EXEC-001": {
                    "start_state": "開始済み",
                    "actual_start_confirmed": True,
                    "result_finalized": True,
                    "source_result": "FAIL",
                }
            },
            "route_results": [
                {
                    "tc_ref": "TC-001",
                    "route_ref": "ROUTE-001",
                    "execution_ref": "EXEC-001",
                    "executed": True,
                    "blocked": False,
                    "result_finalized": True,
                    "source_result_projectable": True,
                    "source_result": "FAIL",
                }
            ],
            "tc_execution_state": {"TC-001": "executed"},
            "counts": {"auxiliary_testware_count": 0},
            "auxiliary_route_results": [],
            "auxiliary_testware_refs": [],
            "cleanup_status": "対象なし",
            "unresolved": [],
        }

        def validate(candidate):
            return VALIDATORS["regression-testing"](
                "```json\n" + json.dumps(candidate) + "\n```",
                {"artifact_type": "activity"},
                "REG-ACTIVITY-TEST",
            ).to_dict()

        valid = validate(activity)
        valid_assertions = {item["id"]: item for item in valid["assertions"]}
        self.assertEqual(valid_assertions["REG-D010"]["status"], "pass")
        self.assertEqual(valid_assertions["REG-D011"]["status"], "pass")

        diagnostic = '```json\n{"valid": true, "issues": []}\n```\n'
        artifact_block = "```json\n" + json.dumps(activity) + "\n```"
        combined = VALIDATORS["regression-testing"](
            diagnostic + artifact_block,
            {"artifact_type": "activity"},
            "REG-ACTIVITY-WITH-DIAGNOSTIC",
        ).to_dict()
        combined_assertions = {item["id"]: item for item in combined["assertions"]}
        self.assertEqual(combined_assertions["REG-D001"]["status"], "pass")
        self.assertEqual(combined_assertions["REG-D018"]["status"], "pass")

        malformed_diagnostic = '```json\n{"valid":}\n```\n' + artifact_block
        malformed_combined = VALIDATORS["regression-testing"](
            malformed_diagnostic,
            {"artifact_type": "activity"},
            "REG-ACTIVITY-WITH-MALFORMED-DIAGNOSTIC",
        ).to_dict()
        malformed_assertions = {
            item["id"]: item for item in malformed_combined["assertions"]
        }
        self.assertEqual(malformed_assertions["REG-D001"]["status"], "fail")

        wrong_result = json.loads(json.dumps(activity))
        wrong_result["source_executions"]["EXEC-001"]["source_result"] = "PASS"
        result = validate(wrong_result)
        assertions = {item["id"]: item for item in result["assertions"]}
        self.assertEqual(assertions["REG-D010"]["status"], "fail")

        unfinalized = json.loads(json.dumps(activity))
        unfinalized["source_executions"]["EXEC-001"]["result_finalized"] = False
        unfinalized["route_results"][0]["result_finalized"] = False
        result = validate(unfinalized)
        assertions = {item["id"]: item for item in result["assertions"]}
        self.assertEqual(assertions["REG-D011"]["status"], "fail")

    def test_adversarial_review_enforces_evidence_block_and_exact_empty_findings(self):
        text = """## 指摘概要
| 重要度 | 件数 |
| --- | ---: |
| 致命的 | 0 |
| 重大 | 0 |
| 軽微 | 0 |
| 提案 | 0 |

## 指摘一覧
| 指摘ID | 重要度 | 対象成果物 / 位置 | 問題 | 根拠 | 影響 | 推奨修正 | 修正Skill / 層 | 処置 | 処置根拠 / 承認参照 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

## レビュー制約
TCN-001-CI01は本文未提示のため、欠陥の有無と重大度は判定不能。
"""
        expected = {
            "known_artifact_ids": ["TCN-001-CI01"],
            "expected_defects": [],
            "expected_finding_count": 0,
            "required_tokens": ["本文未提示", "判定不能"],
        }
        result = VALIDATORS["adversarial-review"](
            text, expected, "REV-BLOCK-TEST"
        ).to_dict()
        assertions = {item["id"]: item for item in result["assertions"]}
        self.assertEqual(assertions["REV-D017"]["status"], "pass")
        self.assertEqual(assertions["REV-D018"]["status"], "pass")

        extra_finding = "| REV-001 | 致命的 | TCN-001-CI01 | inferred defect | no evidence | unknown | unspecified | test-case-design | ブロック中 | |\n"
        separator = "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n\n## レビュー制約"
        bad_text = text.replace(
            separator,
            separator.replace(
                "\n\n## レビュー制約", "\n" + extra_finding + "\n## レビュー制約"
            ),
            1,
        )
        result = VALIDATORS["adversarial-review"](
            bad_text, expected, "REV-BLOCK-TEST"
        ).to_dict()
        assertions = {item["id"]: item for item in result["assertions"]}
        self.assertEqual(assertions["REV-D017"]["status"], "fail")

    def test_exploratory_validator_accepts_explicit_block_for_missing_charter_inputs(
        self,
    ):
        blocked_session = {
            "schema_version": "1",
            "session_ref": "EXP-BLOCK-TEST",
            "mode": "investigation",
            "charter": {
                "purpose": "Investigation inputs are incomplete.",
                "in_scope": [],
                "out_of_scope": [],
                "source_refs": ["input:case"],
                "focus_refs": [],
                "timebox_or_exit_condition": "not supplied",
                "allowed_origins": [],
                "allowed_operations": [],
                "side_effect_operations": [],
                "side_effect_scope": "not supplied",
                "side_effect_action_definition": "not supplied",
                "side_effect_maximum": 0,
                "cleanup_plan": "not supplied",
                "evidence_policy": "use only supplied input",
                "block_conditions": [
                    "symptom or hypothesis is not supplied",
                    "allowed origins and operations are not supplied",
                ],
            },
            "state": "ブロック中",
            "observations": [],
            "findings": [],
            "unresolved": [
                "symptom or hypothesis is not supplied",
                "allowed origins and operations are not supplied",
            ],
            "cleanup": {"required": True, "status": "未確認", "evidence_refs": []},
            "residual_side_effect": ["Existing state is unverified."],
        }
        expected = {"requires_blocked": True}

        def validate(session):
            return VALIDATORS["exploratory-testing"](
                "```json\n" + json.dumps(session) + "\n```", expected, "EXP-BLOCK-TEST"
            ).to_dict()

        result = validate(blocked_session)
        assertions = {item["id"]: item for item in result["assertions"]}
        self.assertEqual(assertions["EXP-D002"]["status"], "pass")
        self.assertEqual(assertions["EXP-D003"]["status"], "pass")
        self.assertEqual(assertions["EXP-D008"]["status"], "pass")

        active_session = json.loads(json.dumps(blocked_session))
        active_session["state"] = "実行中"
        result = validate(active_session)
        assertions = {item["id"]: item for item in result["assertions"]}
        self.assertEqual(assertions["EXP-D002"]["status"], "fail")
        self.assertEqual(assertions["EXP-D003"]["status"], "fail")

        unreasoned_block = json.loads(json.dumps(blocked_session))
        unreasoned_block["unresolved"] = []
        result = validate(unreasoned_block)
        assertions = {item["id"]: item for item in result["assertions"]}
        self.assertEqual(assertions["EXP-D002"]["status"], "fail")


if __name__ == "__main__":
    unittest.main()
