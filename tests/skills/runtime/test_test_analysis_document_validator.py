"""Validator tests for test-analysis documents (kind test-analysis).

Fixtures use example identifiers only. The tests also fix the mirrored constants equal to
the store (artifact_store.py).
"""

from __future__ import annotations

import io
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[3] / "skills"
sys.path.insert(0, str(SKILL_ROOT / "test-analysis" / "scripts"))
sys.path.insert(0, str(SKILL_ROOT / "project-context" / "scripts"))

import test_analysis_document  # noqa: E402
from artifact_store import MAX_BYTES as STORE_MAX_BYTES  # noqa: E402

SCOPE = "scope-1"
REVISION = "rev-source-1"
REASON_PREFIX = "test_analysis_document_invalid:"

VALID = """# テスト分析: scope-1

## テスト分析範囲

- 対象機能 / 変更: 通知設定画面の既定値の保存
- 案件固有のテスト目的 / 重点: 既定値の保存と再表示
- テストレベル: システムテスト
- 環境制約: なし
- 対象外: 管理者向け一括設定（本変更の仕様根拠に含まれないため）
- ブロッカー: なし
- 対象 / 実行範囲: テスト分析
- 入力 revision: rev-source-1

## 変更 / 影響マップ

| 領域 | 変更種別 | 根拠 / 依存関係 | 想定影響 |
| --- | --- | --- | --- |
| 通知設定の保存 | 変更 | SPEC-001 | 既定値の保存処理 |

## プロダクトリスク一覧

| リスクID | 製品上のリスク / 失敗 | 関連する現在有効な仕様根拠 / 変更 / 依存 | 影響度 | 発生可能性 | レベル | 根拠 | 判断信頼度 / 備考 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| RISK-001 | 既定値が保存されず再表示で別の値になる | SPEC-001、変更: 通知設定の保存処理 | 3 | 3 | 高 | 影響度3: 主要設定の誤動作。発生可能性3: 保存処理に変更あり | 中 |
| RISK-002 | 表示順の既定値が誤って表示される | DEC-002 | 2 | 2 | 中 | 影響度2: 一部制限。発生可能性2: 判断材料が限定的 | 低 |

## テスト重点

| 優先度 | 重点領域 | 関連プロダクトリスク / 根拠 | 設計深度 / 備考 |
| --- | --- | --- | --- |
| 高 | 既定値の保存と再表示 | RISK-001 / SPEC-001 | 高リスク: 主要な保存・再表示経路を積極的に検討 |
| 中 | 表示順の既定値 | RISK-002 / DEC-002 | 中リスク: 基本カバレッジ |

## 選択したテスト技法

| テスト技法 | 適用領域 | 選択理由 | 関連プロダクトリスク / 現在有効な仕様根拠 | `test-condition-design`への着眼点 |
| --- | --- | --- | --- | --- |
| 状態遷移 | 設定の保存と再表示の順序 | 保存後に再表示される状態系列があるため | RISK-001 / SPEC-001 | 保存前後の状態の組合せ |

## テスト可能性 / テストレベル判断

| 要件 / 懸念 | 操作可能か | 観測可能か | 合否判定可能か | 選択テストレベル | 扱い / 備考 |
| --- | --- | --- | --- | --- | --- |
| 既定値の保存と再表示 | 可 | 可 | 可 | システムテスト | 現在レベル |

## 残存リスク

| リスク / 要件 | 十分にカバーできない理由 | 推奨対応 |
| --- | --- | --- |
| 管理者向け一括設定 | 対象外（本変更の仕様根拠に含まれない） | 別の変更で扱う |

## Machine Runtime / Entity（機械証拠）

runtime dispatchは行っていません。
"""


def replaced(text: str, old: str, new: str) -> str:
    assert text.count(old) == 1, old
    return text.replace(old, new, 1)


def check(markdown: str, scope: str = SCOPE, revision: str = REVISION) -> dict:
    return test_analysis_document.validate(markdown, scope, revision)


def reasons(markdown: str, scope: str = SCOPE, revision: str = REVISION) -> list[str]:
    return [
        r.removeprefix(REASON_PREFIX)
        for r in check(markdown, scope, revision)["reasons"]
    ]


class TestAnalysisValidatorTests(unittest.TestCase):
    def test_minimal_valid_document_passes(self) -> None:
        report = check(VALID)
        self.assertEqual(report["status"], "valid", report)
        self.assertEqual(report["reasons"], [])
        self.assertEqual(report["metrics"]["risks"], 2)
        self.assertFalse(report["metrics"]["blocker_declared"])

    def test_each_required_section_is_reported_when_missing(self) -> None:
        for heading in test_analysis_document.SECTIONS:
            with self.subTest(heading=heading):
                text = replaced(VALID, f"## {heading}\n", "## 別の見出し\n")
                self.assertIn(f"section_missing:{heading}", reasons(text))

    def test_duplicate_required_section_is_reported(self) -> None:
        text = VALID + "\n## 残存リスク\n\n残りの記述\n"
        self.assertIn("section_duplicate:残存リスク", reasons(text))

    def test_extra_heading_is_allowed(self) -> None:
        text = replaced(
            VALID, "## 残存リスク\n", "## 作業メモ\n\n補足\n\n## 残存リスク\n"
        )
        self.assertEqual(reasons(text), [])

    def test_scope_id_format_is_checked(self) -> None:
        for scope in ("../scope", "Scope-1", "", "a" * 65):
            with self.subTest(scope=scope):
                self.assertIn("scope_id_invalid", reasons(VALID, scope=scope))

    def test_source_revision_must_appear_in_document(self) -> None:
        self.assertIn(
            "source_revision_not_in_document", reasons(VALID, revision="rev-other")
        )
        self.assertIn("source_revision_not_in_document", reasons(VALID, revision=""))

    def test_scope_fields_are_required_and_non_empty(self) -> None:
        for label in ("対象機能 / 変更", "テストレベル", "対象外", "ブロッカー"):
            with self.subTest(label=label):
                lines = [
                    line
                    for line in VALID.split("\n")
                    if not line.startswith(f"- {label}:")
                ]
                self.assertIn(f"scope_field_missing:{label}", reasons("\n".join(lines)))
        text = replaced(
            VALID,
            "- 対象外: 管理者向け一括設定（本変更の仕様根拠に含まれないため）",
            "- 対象外:",
        )
        self.assertIn("scope_field_empty:対象外", reasons(text))
        for label in ("環境制約", "対象 / 実行範囲"):
            lines = [
                line for line in VALID.split("\n") if not line.startswith(f"- {label}:")
            ]
            self.assertIn(f"scope_field_missing:{label}", reasons("\n".join(lines)))

    def test_declared_blocker_is_reported_in_metrics_without_blocking(self) -> None:
        text = replaced(
            VALID, "- ブロッカー: なし", "- ブロッカー: 仕様根拠 SPEC-009 が未確定"
        )
        report = check(text)
        self.assertEqual(report["status"], "valid", report)
        self.assertTrue(report["metrics"]["blocker_declared"])

    def test_table_header_must_match_the_template(self) -> None:
        text = replaced(VALID, "| 優先度 | 重点領域 |", "| 優先 | 重点領域 |")
        self.assertIn("table_header_mismatch:テスト重点", reasons(text))

    def test_row_width_mismatch_is_reported(self) -> None:
        text = replaced(
            VALID,
            "| 高 | 既定値の保存と再表示 | RISK-001 / SPEC-001 | 高リスク: 主要な保存・再表示経路を積極的に検討 |",
            "| 高 | 既定値の保存と再表示 | RISK-001 / SPEC-001 |",
        )
        self.assertIn("table_row_width:テスト重点", reasons(text))

    def test_missing_required_table_and_empty_required_tables_are_reported(
        self,
    ) -> None:
        lines = VALID.split("\n")
        start = lines.index("## テスト可能性 / テストレベル判断")
        end = lines.index("## 残存リスク")
        without_table = (
            lines[:start]
            + [line for line in lines[start:end] if not line.startswith("|")]
            + lines[end:]
        )
        self.assertIn(
            "table_missing:テスト可能性 / テストレベル判断",
            reasons("\n".join(without_table)),
        )
        empty_risk = [line for line in lines if not line.startswith("| RISK-")]
        self.assertIn(
            "table_empty:プロダクトリスク一覧", reasons("\n".join(empty_risk))
        )

    def test_risk_identifier_format_and_duplicate_are_checked(self) -> None:
        text = replaced(VALID, "| RISK-002 |", "| RISK-2 |")
        self.assertIn("risk_id_invalid:RISK-2", reasons(text))
        text = replaced(VALID, "| RISK-002 |", "| RISK-001 |")
        self.assertIn("risk_id_duplicate:RISK-001", reasons(text))

    def test_risk_level_must_match_the_standard_matrix(self) -> None:
        text = replaced(VALID, "| 3 | 3 | 高 |", "| 3 | 3 | 中 |")
        self.assertIn("risk_level_mismatch:RISK-001", reasons(text))
        text = replaced(VALID, "| 2 | 2 | 中 |", "| 2 | 2 | 巨大 |")
        self.assertIn("risk_level_invalid:RISK-002", reasons(text))

    def test_scores_must_be_one_to_four(self) -> None:
        text = replaced(
            VALID,
            "| RISK-002 | 表示順の既定値が誤って表示される | DEC-002 | 2 | 2 | 中 |",
            "| RISK-002 | 表示順の既定値が誤って表示される | DEC-002 | 5 | 2 | 中 |",
        )
        self.assertIn("risk_impact_invalid:RISK-002", reasons(text))

    def test_unknown_and_inference_are_never_a_basis(self) -> None:
        for token in ("UNK-001", "INF-001", "UNKNOWN", "INFERENCE"):
            with self.subTest(token=token):
                text = replaced(VALID, "| DEC-002 |", f"| DEC-002、{token} |")
                found = reasons(text)
                self.assertTrue(
                    any(
                        item.startswith("non_basis_reference:RISK-002:")
                        for item in found
                    ),
                    found,
                )

    def test_missing_basis_and_reason_are_reported(self) -> None:
        text = replaced(
            VALID,
            "| DEC-002 | 2 | 2 | 中 | 影響度2: 一部制限。発生可能性2: 判断材料が限定的 |",
            "|  | 2 | 2 | 中 |  |",
        )
        found = reasons(text)
        self.assertIn("risk_basis_missing:RISK-002", found)
        self.assertIn("risk_reason_missing:RISK-002", found)

    def test_every_risk_must_be_placed_and_referenced_risks_must_exist(self) -> None:
        text = replaced(
            VALID,
            "| 中 | 表示順の既定値 | RISK-002 / DEC-002 | 中リスク: 基本カバレッジ |",
            "| 中 | 表示順の既定値 | DEC-002 | 中リスク: 基本カバレッジ |",
        )
        self.assertIn("risk_unplaced:RISK-002", reasons(text))
        text = replaced(
            VALID,
            "| RISK-001 / SPEC-001 | 保存前後の状態の組合せ",
            "| RISK-009 / SPEC-001 | 保存前後の状態の組合せ",
        )
        self.assertIn("risk_ref_missing:RISK-009", reasons(text))

    def test_priority_and_feasibility_values_are_checked(self) -> None:
        text = replaced(
            VALID, "| 高 | 既定値の保存と再表示 |", "| 最高 | 既定値の保存と再表示 |"
        )
        self.assertIn("priority_invalid:1", reasons(text))
        text = replaced(
            VALID,
            "| 既定値の保存と再表示 | 可 | 可 | 可 |",
            "| 既定値の保存と再表示 | 多分 | 可 | 可 |",
        )
        self.assertIn("feasibility_invalid:operable:1", reasons(text))

    def test_change_kind_is_checked(self) -> None:
        text = replaced(VALID, "| 通知設定の保存 | 変更 |", "| 通知設定の保存 | 修正 |")
        self.assertIn("change_kind_invalid:1", reasons(text))

    def test_machine_section_blocks_are_format_checked(self) -> None:
        bad_header = replaced(
            VALID,
            "runtime dispatchは行っていません。",
            "### Machine Entities: other-skill\n\n```json\n{}\n```\n",
        )
        self.assertIn("machine_block_invalid", reasons(bad_header))
        bad_json = replaced(
            VALID,
            "runtime dispatchは行っていません。",
            "### Machine Entities: test-analysis\n\n```json\n{not json\n```\n",
        )
        self.assertIn("machine_block_json_invalid", reasons(bad_json))
        no_json = replaced(
            VALID,
            "runtime dispatchは行っていません。",
            "### Machine Entities: test-analysis\n\n本文のみ\n",
        )
        self.assertIn("machine_block_json_missing", reasons(no_json))
        good = replaced(
            VALID,
            "runtime dispatchは行っていません。",
            '### Machine Entities: test-analysis\n\n```json\n{"entities": []}\n```\n',
        )
        self.assertEqual(reasons(good), [])

    def test_email_and_local_path_are_rejected(self) -> None:
        self.assertIn(
            "email_address_present",
            reasons(
                replaced(
                    VALID, "- 環境制約: なし", "- 環境制約: person@example.invalid"
                )
            ),
        )
        self.assertIn(
            "local_path_present",
            reasons(replaced(VALID, "- 環境制約: なし", "- 環境制約: /home/user/work")),
        )
        self.assertIn(
            "local_path_present",
            reasons(replaced(VALID, "- 環境制約: なし", "- 環境制約: Z:\\data")),
        )

    def test_encoding_and_size_are_checked(self) -> None:
        self.assertEqual(
            check("\x00" + VALID)["reasons"], [REASON_PREFIX + "encoding_invalid"]
        )
        self.assertEqual(
            test_analysis_document.validate(
                VALID + "a" * (16 * 1024 * 1024), SCOPE, REVISION
            )["reasons"],
            [REASON_PREFIX + "too_large"],
        )

    def test_constants_match_the_store(self) -> None:
        self.assertEqual(test_analysis_document.MAX_BYTES, STORE_MAX_BYTES)
        self.assertEqual(test_analysis_document.KIND, "test-analysis")

    def test_artifact_ref_is_derived_from_scope(self) -> None:
        self.assertEqual(
            test_analysis_document.artifact_ref_for("scope-1"),
            "test-analysis/scope-1.md",
        )
        self.assertIsNone(test_analysis_document.artifact_ref_for("../scope"))
        self.assertIsNone(test_analysis_document.artifact_ref_for(None))


class TestAnalysisDocumentCliTests(unittest.TestCase):
    def run_cli(self, data: bytes, scope: str = SCOPE) -> tuple[int, dict]:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "document.md"
            path.write_bytes(data)
            out = io.StringIO()
            with redirect_stdout(out):
                code = test_analysis_document.main(
                    [
                        "validate",
                        "--document-file",
                        str(path),
                        "--scope-id",
                        scope,
                        "--source-revision",
                        REVISION,
                    ]
                )
        return code, json.loads(out.getvalue())

    def test_validate_command_reports_valid_and_blocked(self) -> None:
        code, payload = self.run_cli(VALID.encode("utf-8"))
        self.assertEqual((code, payload["status"]), (0, "valid"), payload)
        code, payload = self.run_cli(
            replaced(VALID, "## 残存リスク", "## 別").encode("utf-8")
        )
        self.assertEqual(code, 1)
        self.assertEqual(payload["status"], "blocked")

    def test_validate_command_rejects_invalid_utf8(self) -> None:
        code, payload = self.run_cli(b"\xff\xfe")
        self.assertEqual(
            (code, payload["reasons"]), (1, [REASON_PREFIX + "encoding_invalid"])
        )

    def test_validate_command_reports_unreadable_file(self) -> None:
        out = io.StringIO()
        with redirect_stdout(out):
            code = test_analysis_document.main(
                [
                    "validate",
                    "--document-file",
                    "/nonexistent/none.md",
                    "--scope-id",
                    SCOPE,
                    "--source-revision",
                    REVISION,
                ]
            )
        self.assertEqual(code, 1)
        self.assertEqual(
            json.loads(out.getvalue())["reasons"], [REASON_PREFIX + "unavailable"]
        )

    def test_validate_runs_as_a_script_without_repo_imports(self) -> None:
        script = SKILL_ROOT / "test-analysis" / "scripts" / "test_analysis_document.py"
        source = script.read_text(encoding="utf-8")
        for name in (
            "question_",
            "spec_",
            "artifact_store",
            "project_context",
            "git_artifact_store",
            "artifact_host",
        ):
            self.assertNotIn(f"import {name}", source)
            self.assertNotIn(f"from {name}", source)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "document.md"
            path.write_text(VALID, encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    "-I",
                    str(script),
                    "validate",
                    "--document-file",
                    str(path),
                    "--scope-id",
                    SCOPE,
                    "--source-revision",
                    REVISION,
                ],
                capture_output=True,
                text=True,
                check=False,
                env={"PYTHONDONTWRITEBYTECODE": "1"},
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "valid")


if __name__ == "__main__":
    unittest.main()
