from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[4]
SKILLS_ROOT = REPO_ROOT / "skills"


def load_validator(skill: str):
    path = SKILLS_ROOT / skill / "evals" / "deterministic" / "validator.py"
    spec = importlib.util.spec_from_file_location(f"{skill.replace('-', '_')}_validator", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load validator: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.validate


def eval_case(skill: str, eval_id: str):
    root = SKILLS_ROOT / skill / "evals" / "output"
    manifest = json.loads((root / "evals.json").read_text(encoding="utf-8"))
    case = next(row for row in manifest["cases"] if row["id"] == eval_id)
    expected = json.loads((root / case["expected"]).read_text(encoding="utf-8"))
    output = (root / case["input"]).parent / "reference.md"
    return output.read_text(encoding="utf-8"), expected


class NewSkillDeterministicContractTests(unittest.TestCase):
    def test_test_target_inspection_fixtures_pass(self):
        validate = load_validator("test-target-inspection")
        for eval_id in ("TTI-OUT-001", "TTI-OUT-002"):
            with self.subTest(eval_id=eval_id):
                text, expected = eval_case("test-target-inspection", eval_id)
                self.assertEqual(validate(text, expected, eval_id).status, "pass")

    def test_deleted_target_may_be_absent_from_current_body(self):
        validate = load_validator("test-target-inspection")
        text, expected = eval_case("test-target-inspection", "TTI-OUT-002")
        self.assertIn("target-002", text)
        result = validate(text, expected, "TTI-OUT-002")
        self.assertEqual(result.status, "pass")
        deletion = next(item for item in result.assertions if item.id == "TTI-D009")
        self.assertEqual(deletion.status, "pass")

    def test_deleted_target_must_not_reappear_in_current_body(self):
        validate = load_validator("test-target-inspection")
        text, expected = eval_case("test-target-inspection", "TTI-OUT-002")
        current_row = "| target-001 | ユーザー一覧 | 管理メニューからユーザー | 確認済み | 管理者、1440x900、ja-JP、users-v3=on、user-25 | build-18 | 2026-09-26T09:30:00+09:00 |"
        resurrected = "| target-002 | 削除済み画面 | 管理メニューからユーザー | 確認済み | 管理者、1440x900、ja-JP、users-v3=on、user-25 | build-18 | 2026-09-26T09:30:00+09:00 |"
        broken = text.replace(current_row, current_row + "\n" + resurrected, 1)
        result = validate(broken, expected, "TTI-OUT-002")
        self.assertEqual(next(item.status for item in result.assertions if item.id == "TTI-D009"), "fail")

    def test_unconfirmed_visual_row_keeps_previous_freshness(self):
        validate = load_validator("test-target-inspection")
        text, expected = eval_case("test-target-inspection", "TTI-OUT-001")
        old = "| target-001 | state-001 | 行の重なり | 行の間隔が保たれている | evidence/orders.png | 確認済み | 1440x900 | build-23 | 2026-09-26T09:00:00+09:00 | 画像で確認 |"
        refreshed = "| target-001 | state-001 | 行の重なり | 行の間隔が保たれている | evidence/orders.png | 未確認 | 1440x900 | build-24 | 2026-09-26T09:30:00+09:00 | 今回未確認 |"
        broken = text.replace(old, refreshed, 1)
        expected["unconfirmed_facts"] = {
            "target-001": {
                "確認条件": "1440x900",
                "確認version / build": "build-23",
                "確認日時": "2026-09-26T09:00:00+09:00",
            }
        }
        result = validate(broken, expected, "TTI-OUT-001")
        self.assertEqual(next(item.status for item in result.assertions if item.id == "TTI-D007"), "fail")

    def test_snapshot_reference_requires_retrievable_identity(self):
        validate = load_validator("test-target-inspection")
        text, expected = eval_case("test-target-inspection", "TTI-OUT-001")
        broken = text.replace("sha256:ab23", "", 1)
        result = validate(broken, expected, "TTI-OUT-001")
        self.assertEqual(next(item.status for item in result.assertions if item.id == "TTI-D010"), "fail")

    def test_target_inspection_requires_fixture_entities(self):
        validate = load_validator("test-target-inspection")
        text, expected = eval_case("test-target-inspection", "TTI-OUT-001")
        expected["required_target_keys"] = ["target-999"]
        result = validate(text, expected, "TTI-OUT-001")
        self.assertEqual(next(item.status for item in result.assertions if item.id == "TTI-D015"), "fail")

    def test_target_inspection_rejects_unconditional_shared_store_overwrite(self):
        validate = load_validator("test-target-inspection")
        text, expected = eval_case("test-target-inspection", "TTI-OUT-002")
        unsafe = text.replace("If-Match", "通常上書き", 1)
        result = validate(unsafe, expected, "TTI-OUT-002")
        self.assertEqual(next(item.status for item in result.assertions if item.id == "TTI-D011"), "fail")

    def test_target_inspection_rejects_side_effect_scope_overrun(self):
        validate = load_validator("test-target-inspection")
        text, expected = eval_case("test-target-inspection", "TTI-OUT-001")
        unsafe_row = "| order-update | 1回は注文状態1件の変更 | 2 | 1 | 1 | 1 | 3 | 注文を元に戻す | 成功 | 元に復元済み | 明示許可 |"
        separator = "| --- | --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- | --- |"
        unsafe = text.replace(separator, separator + "\n" + unsafe_row, 1)
        result = validate(unsafe, expected, "TTI-OUT-001")
        self.assertEqual(next(item.status for item in result.assertions if item.id == "TTI-D012"), "fail")

    def test_target_inspection_rejects_duplicate_side_effect_scope_rows(self):
        validate = load_validator("test-target-inspection")
        text, expected = eval_case("test-target-inspection", "TTI-OUT-001")
        row = "| order-update | 1回は注文状態1件の変更 | 3 | 1 | 1 | 1 | 3 | 注文を元に戻す | 成功 | 元に復元済み | 明示許可 |"
        separator = "| --- | --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- | --- |"
        duplicated = text.replace(separator, separator + "\n" + row + "\n" + row, 1)
        result = validate(duplicated, expected, "TTI-OUT-001")
        self.assertEqual(next(item.status for item in result.assertions if item.id == "TTI-D012"), "fail")

    def test_test_execution_fixtures_pass_with_duplicate_source_ids_and_rerun(self):
        validate = load_validator("test-execution")
        for eval_id in ("TEX-OUT-001", "TEX-OUT-002"):
            with self.subTest(eval_id=eval_id):
                text, expected = eval_case("test-execution", eval_id)
                self.assertEqual(validate(text, expected, eval_id).status, "pass")

    def test_test_execution_detects_secret_leak(self):
        validate = load_validator("test-execution")
        text, expected = eval_case("test-execution", "TEX-OUT-002")
        leaked = text + "\nSAMPLE-SECRET-9218\n"
        result = validate(leaked, expected, "TEX-OUT-002")
        self.assertEqual(next(item.status for item in result.assertions if item.id == "TEX-D013"), "fail")

    def test_test_execution_rejects_invalid_yaml_structure(self):
        validate = load_validator("test-execution")
        text, expected = eval_case("test-execution", "TEX-OUT-001")
        broken = text.replace("source_test_case_id: EXT-17", "source_test_case_id: [invalid", 1)
        result = validate(broken, expected, "TEX-OUT-001")
        self.assertEqual(next(item.status for item in result.assertions if item.id == "TEX-D003"), "fail")

    def test_test_execution_rejects_yaml_snapshot_out_of_input_order(self):
        validate = load_validator("test-execution")
        text, expected = eval_case("test-execution", "TEX-OUT-001")
        reordered = (
            text.replace("test_case_ref: input-001", "test_case_ref: __TEMP__", 1)
            .replace("test_case_ref: input-002", "test_case_ref: input-001", 1)
            .replace("test_case_ref: __TEMP__", "test_case_ref: input-002", 1)
        )
        result = validate(reordered, expected, "TEX-OUT-001")
        self.assertEqual(next(item.status for item in result.assertions if item.id == "TEX-D003"), "fail")

    def test_test_execution_rejects_missing_prior_case_reference(self):
        validate = load_validator("test-execution")
        text, expected = eval_case("test-execution", "TEX-OUT-002")
        broken = text.replace("| input-001 | TC-044 | 1 | input-001 |", "| input-001 | TC-044 | 1 | なし |", 1)
        result = validate(broken, expected, "TEX-OUT-002")
        self.assertEqual(next(item.status for item in result.assertions if item.id == "TEX-D006"), "fail")

    def test_test_execution_rejects_scope_limit_overrun(self):
        validate = load_validator("test-execution")
        text, expected = eval_case("test-execution", "TEX-OUT-002")
        broken = text.replace("| profile-update | 1回はプロフィール値1件の変更操作 | 3 | 1 | 1 | 0 | 1 | 3 |", "| profile-update | 1回はプロフィール値1件の変更操作 | 3 | 1 | 1 | 0 | 1 | 4 |", 1)
        result = validate(broken, expected, "TEX-OUT-002")
        self.assertEqual(next(item.status for item in result.assertions if item.id == "TEX-D011"), "fail")

    def test_test_execution_rejects_duplicate_side_effect_scope_rows(self):
        validate = load_validator("test-execution")
        text, expected = eval_case("test-execution", "TEX-OUT-002")
        row = "| profile-update | 1回はプロフィール値1件の変更操作 | 3 | 1 | 1 | 0 | 1 | 3 | 元の表示名へ戻す | 成功 | 元の表示名へ復元済み | 0 | scope契約 |"
        duplicated = text.replace(row, row + "\n" + row, 1)
        result = validate(duplicated, expected, "TEX-OUT-002")
        self.assertEqual(next(item.status for item in result.assertions if item.id == "TEX-D011"), "fail")

    def test_test_execution_requires_observation_for_passed_steps(self):
        validate = load_validator("test-execution")
        text, expected = eval_case("test-execution", "TEX-OUT-001")
        procedure = "| input-001 | step-001 | 注文番号42を検索欄へ入力 | accessibility tree | 注文番号42が表示 | 注文番号42を観測 | 一致 |\n"
        broken = text.replace(procedure, "", 1)
        result = validate(broken, expected, "TEX-OUT-001")
        self.assertEqual(next(item.status for item in result.assertions if item.id == "TEX-D010"), "fail")

    def test_test_execution_rejects_unknown_cleanup_state(self):
        validate = load_validator("test-execution")
        text, expected = eval_case("test-execution", "TEX-OUT-002")
        broken = text.replace("| 元の表示名へ戻す | 成功 | 元の表示名へ復元済み |", "| 元の表示名へ戻す | 保留 | 元の表示名へ復元済み |", 1)
        result = validate(broken, expected, "TEX-OUT-002")
        self.assertEqual(next(item.status for item in result.assertions if item.id == "TEX-D011"), "fail")


if __name__ == "__main__":
    unittest.main()
