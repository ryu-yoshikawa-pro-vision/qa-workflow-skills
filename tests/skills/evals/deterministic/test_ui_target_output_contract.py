from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]


def load_validator(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.validate


validate_spec = load_validator(
    "spec_analysis_output_validator",
    REPO_ROOT / "skills" / "spec-analysis" / "evals" / "deterministic" / "validator.py",
)
validate_tr = load_validator(
    "test_requirement_output_validator",
    REPO_ROOT
    / "skills"
    / "test-requirement-design"
    / "evals"
    / "deterministic"
    / "validator.py",
)


def failed_ids(result) -> set[str]:
    return {
        row["id"] for row in result.to_dict()["assertions"] if row["status"] == "fail"
    }


class UiTargetOutputContractTests(unittest.TestCase):
    def spec_projection(self) -> str:
        return """<!-- FILE: 00_scope_and_context.md -->
# Scope
## 分析対象機能scope一覧
| Scope ID | UI操作判定 | Behavior Decomposition |
| --- | --- | --- |
| SCOPE-001 | あり | required |
<!-- FILE: 01_ui_structure_and_navigation.md -->
## UI構造一覧
| 構造ID | 種別 | 状態軸 |
| --- | --- | --- |
| PAGE-001 | PAGE | - |
## 情報源 / 正本参照一覧
| 参照ID | 情報源 / 正本一覧 |
| --- | --- |
| SRC-001 | auth spec |
## 分析項目
| 項目ID | 内容 | 分類 | 情報源 / 正本参照 |
| --- | --- | --- | --- |
| SPEC-001 | login | SPEC | SRC-001 |
## 現在有効な仕様根拠
| 仕様根拠ID | 種別 | 現在有効な内容 | 適用範囲 | 情報源 / 正本一覧 | 関係 |
| --- | --- | --- | --- | --- | --- |
| SPEC-001 | SPEC | login | SCOPE-001 | SRC-001 | 独立 |
## Acceptance Criteria一覧
| AC ID | Behavior ID | Acceptance Criteria |
| --- | --- | --- |
| AC-001 | BH-001 | login succeeds |
"""

    def test_spec_analysis_checks_package_projection_markers_ids_and_tables(
        self,
    ) -> None:
        expected = {
            "known_authorities": ["SPEC-001"],
            "required_current_authorities": ["SPEC-001"],
            "required_package_files": ["00_scope_and_context.md"],
            "required_ui_target_ids": ["SCOPE-001", "PAGE-001", "AC-001"],
            "required_package_tables": [
                {
                    "section_contains": "UI構造一覧",
                    "headers": ["構造ID", "種別", "状態軸"],
                }
            ],
        }
        result = validate_spec(self.spec_projection(), expected, "SPEC-OUT-003")
        self.assertFalse(failed_ids(result), result.to_dict())

        broken = self.spec_projection().replace(
            "<!-- FILE: 00_scope_and_context.md -->", ""
        )
        result = validate_spec(broken, expected, "SPEC-OUT-003")
        self.assertIn("SPEC-D020", failed_ids(result))

    def tr_output(self, *, double_close: bool = False) -> str:
        extra_disposition = (
            "| AC-001 | Acceptance Criteria | 対象外 | duplicate closure |\n"
            if double_close
            else ""
        )
        return f"""# テスト要求
## テスト要求一覧
| テスト要求ID | 関連AC ID | テスト要求 | 現在有効な仕様根拠 | 関連プロダクトリスク | 優先度 | テストレベル / 観測方法 | 備考 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| TR-001 | AC-001 | ログイン成功後の遷移を保証する | SPEC-001 | RISK-001 | 中 | システム / UI | |
## テスト要求を作らない上流項目
| 上流ID | 種別 | 扱い | 理由 / 根拠 |
| --- | --- | --- | --- |
| AC-002 | Acceptance Criteria | ブロック中 | 文言が未確定 |
{extra_disposition}"""

    def test_trd_closes_ac_authority_and_risk_independently(self) -> None:
        expected = {
            "known_authorities": ["SPEC-001"],
            "known_product_risks": ["RISK-001"],
            "product_risk_levels": {"RISK-001": "中"},
            "known_acceptance_criteria": ["AC-001", "AC-002"],
            "required_linked_acceptance_ids": ["AC-001"],
            "required_linked_upstream_ids": ["SPEC-001", "RISK-001"],
            "expected_dispositions": {"AC-002": "ブロック中"},
        }
        valid = validate_tr(self.tr_output(), expected, "TR-OUT-003")
        self.assertFalse(failed_ids(valid), valid.to_dict())

        duplicate = validate_tr(
            self.tr_output(double_close=True), expected, "TR-OUT-003"
        )
        self.assertIn("TR-D009", failed_ids(duplicate))


if __name__ == "__main__":
    unittest.main()
