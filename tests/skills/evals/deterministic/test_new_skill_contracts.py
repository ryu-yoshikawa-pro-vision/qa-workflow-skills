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

    def test_target_inspection_requires_confirmation_info_table_and_items(self):
        validate = load_validator("test-target-inspection")
        text, expected = eval_case("test-target-inspection", "TTI-OUT-001")
        section_start = text.index("## 確認情報")
        next_section = text.index("\n## 画面 / 領域", section_start)
        without_table = text[:section_start] + text[next_section + 1 :]
        without_item = "\n".join(
            line for line in text.splitlines() if not line.startswith("| 対象URL / origin |")
        )

        for name, broken in (("missing table", without_table), ("missing item", without_item)):
            with self.subTest(name=name):
                result = validate(broken, expected, "TTI-OUT-001")
                self.assertEqual(next(item.status for item in result.assertions if item.id == "TTI-D001"), "fail")

    def test_target_inspection_checks_optional_tables_confirmation_states(self):
        validate = load_validator("test-target-inspection")
        text, expected = eval_case("test-target-inspection", "TTI-OUT-001")
        lines = text.splitlines()
        visual_row = next(
            index
            for index, line in enumerate(lines)
            if line.startswith("| target-001 | state-001 | 行の重なり |")
        )
        lines[visual_row] = lines[visual_row].replace("| 確認済み |", "| 不明 |", 1)
        invalid_visual_state = "\n".join(lines)

        lines = text.splitlines()
        dependency_section = lines.index("## データ・権限依存")
        dependency_row = "| target-001 | state-001 | role=admin | 管理者メニューを確認 | 不明 | 管理者 | build-23 | 2026-09-26T09:00:00+09:00 |"
        lines.insert(dependency_section + 4, dependency_row)
        invalid_dependency_state = "\n".join(lines)

        for name, broken in (
            ("visual state", invalid_visual_state),
            ("dependency state", invalid_dependency_state),
        ):
            with self.subTest(name=name):
                result = validate(broken, expected, "TTI-OUT-001")
                self.assertEqual(next(item.status for item in result.assertions if item.id == "TTI-D004"), "fail")

    def test_target_inspection_checks_optional_implementation_references(self):
        validate = load_validator("test-target-inspection")
        text, expected = eval_case("test-target-inspection", "TTI-OUT-001")
        lines = text.splitlines()
        mapping_section = lines.index("## 既存テスト実装との対応（任意）")
        lines.insert(mapping_section + 4, "| target-999 | なし | POM | src/pages/orders.ts | 注文画面 | rev-2 |")
        broken = "\n".join(lines)

        result = validate(broken, expected, "TTI-OUT-001")
        self.assertEqual(next(item.status for item in result.assertions if item.id == "TTI-D005"), "fail")

    def test_target_inspection_requires_and_matches_existing_source_revision(self):
        validate = load_validator("test-target-inspection")
        text, expected = eval_case("test-target-inspection", "TTI-OUT-002")
        save_row = "| user-specified-store | rev-4 | If-Match | 保存済み | rev-5 | 条件付き更新成功を再読込で確認 | 保存先 |"
        missing_source_revision = text.replace(
            save_row,
            "| user-specified-store |  | If-Match | 保存済み | rev-5 | 条件付き更新成功を再読込で確認 | 保存先 |",
            1,
        )
        mismatched_source_revision = text.replace(
            save_row,
            "| user-specified-store | rev-999 | If-Match | 保存済み | rev-5 | 条件付き更新成功を再読込で確認 | 保存先 |",
            1,
        )

        for name, broken in (
            ("missing source revision", missing_source_revision),
            ("mismatched source revision", mismatched_source_revision),
        ):
            with self.subTest(name=name):
                result = validate(broken, expected, "TTI-OUT-002")
                self.assertEqual(next(item.status for item in result.assertions if item.id == "TTI-D011"), "fail")

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
        visual_a = "| target-001 | state-001 | 行の重なり | 行の間隔が保たれている | evidence/orders.png | 確認済み | 1440x900 | build-23 | 2026-09-26T09:00:00+09:00 | 画像で確認 |"
        old_visual_a = "| target-001 | state-001 | 行の重なり | 行の間隔が保たれている | evidence/orders.png | 未確認 | 1440x900 | build-22 | 2026-09-25T09:00:00+09:00 | 前回未確認 |"
        old_visual_b = "| target-001 | element-001 | 文字色 | 文字色と背景色の差 | evidence/orders-text.png | 未確認 | 1280x800 | build-21 | 2026-09-24T09:00:00+09:00 | 前回未確認 |"
        prior_a = {
            "確認条件": "1440x900",
            "確認version / build": "build-22",
            "確認日時": "2026-09-25T09:00:00+09:00",
        }
        prior_b = {
            "確認条件": "1280x800",
            "確認version / build": "build-21",
            "確認日時": "2026-09-24T09:00:00+09:00",
        }
        prepared = text.replace(visual_a, old_visual_a, 1).replace(
            old_visual_a, old_visual_a + "\n" + old_visual_b, 1
        )
        expected["unconfirmed_facts"] = {
            '["視覚情報", "target-001", "state-001", "行の重なり"]': prior_a,
            '["視覚情報", "target-001", "element-001", "文字色"]': prior_b,
        }
        refreshed_visual_a = old_visual_a.replace("| build-22 |", "| build-23 |", 1)
        broken = prepared.replace(old_visual_a, refreshed_visual_a, 1)
        result = validate(broken, expected, "TTI-OUT-001")
        freshness = next(item for item in result.assertions if item.id == "TTI-D007")
        self.assertEqual(freshness.status, "fail")
        self.assertEqual(len(freshness.evidence), 1)
        self.assertEqual(freshness.evidence[0]["key"], '["視覚情報", "target-001", "state-001", "行の重なり"]')

    def test_new_target_artifact_rejects_update_records(self):
        validate = load_validator("test-target-inspection")
        text, expected = eval_case("test-target-inspection", "TTI-OUT-001")
        update_record = (
            "\n## 今回の更新\n\n"
            "| 対象種別 | 対象キー | 更新区分 |\n"
            "| --- | --- | --- |\n"
            "| 画面 | target-001 | 追加 |\n"
        )
        result = validate(text + update_record, expected, "TTI-OUT-001")
        self.assertEqual(next(item.status for item in result.assertions if item.id == "TTI-D008"), "fail")

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

    def test_test_execution_tracks_only_rerun_tcs_when_snapshot_mixes_new_tcs(self):
        validate = load_validator("test-execution")
        text, expected = eval_case("test-execution", "TEX-OUT-001")
        text = text.replace(
            "| 前回実行成果物参照 | なし | 初回実行 |",
            "| 前回実行成果物参照 | execution-v1 | 前回成果物 |",
            1,
        )
        text = text.replace(
            "| input-001 | EXT-17 | 1 | なし |",
            "| input-001 | EXT-17 | 1 | input-001 |",
            1,
        )
        expected["expected_previous_artifact"] = "execution-v1"
        expected["expected_previous_refs"] = {"input-001": "input-001"}
        self.assertEqual(validate(text, expected, "TEX-OUT-001").status, "pass")

        without_known_map = dict(expected)
        without_known_map.pop("expected_previous_refs")
        self.assertEqual(validate(text, without_known_map, "TEX-OUT-001").status, "pass")

        missing_rerun_ref = text.replace(
            "| input-001 | EXT-17 | 1 | input-001 |",
            "| input-001 | EXT-17 | 1 | なし |",
            1,
        )
        unexpected_new_tc_ref = text.replace(
            "| input-002 | EXT-17 | 2 | なし |",
            "| input-002 | EXT-17 | 2 | input-002 |",
            1,
        )
        for name, broken in (
            ("missing rerun TC reference", missing_rerun_ref),
            ("unexpected reference for new TC", unexpected_new_tc_ref),
        ):
            with self.subTest(name=name):
                result = validate(broken, expected, "TEX-OUT-001")
                self.assertEqual(next(item.status for item in result.assertions if item.id == "TEX-D006"), "fail")

    def test_test_execution_validates_run_safety_rows_and_precondition_refs(self):
        validate = load_validator("test-execution")
        text, expected = eval_case("test-execution", "TEX-OUT-002")
        mutations = {}
        for condition in ("対象環境", "許可origin", "version / build"):
            lines = text.splitlines()
            lines = [line for line in lines if not line.startswith(f"| {condition} |")]
            mutations[f"missing {condition}"] = "\n".join(lines)

        lines = text.splitlines()
        precondition = next(index for index, line in enumerate(lines) if line.startswith("| input-001 | profile-update |"))
        lines[precondition] = lines[precondition].replace("| input-001 |", "| input-999 |", 1)
        mutations["unknown precondition TC"] = "\n".join(lines)

        lines = text.splitlines()
        precondition_index = next(index for index, line in enumerate(lines) if line.startswith("| input-001 | profile-update |"))
        lines.insert(precondition_index + 1, lines[precondition_index])
        mutations["duplicate precondition TC"] = "\n".join(lines)

        for name, broken in mutations.items():
            with self.subTest(name=name):
                result = validate(broken, expected, "TEX-OUT-002")
                self.assertEqual(next(item.status for item in result.assertions if item.id == "TEX-D009"), "fail")

    def test_test_execution_separates_tc_postprocessing_from_runtime_cleanup(self):
        validate = load_validator("test-execution")
        text, expected = eval_case("test-execution", "TEX-OUT-002")
        self.assertEqual(
            next(item.status for item in validate(text, expected, "TEX-OUT-002").assertions if item.id == "TEX-D011"),
            "pass",
        )

        post_row = "| input-001 | 元TCで定義された事後処理 | 成功 | 変更前の値へ復元済み | 元TC cleanup |"
        post_table = (
            "| TC参照 | 事後状態 / 後処理 | 実施結果 | 残存状態 | 根拠 |\n"
            "| --- | --- | --- | --- | --- |"
        )
        inconsistent = text.replace("| input-001 | profile-update | なし |", "| input-001 | profile-update | 元TCで定義された事後処理 |", 1)
        inconsistent = inconsistent.replace(post_table, post_table + "\n" + post_row, 1)
        result = validate(inconsistent, expected, "TEX-OUT-002")
        self.assertEqual(next(item.status for item in result.assertions if item.id == "TEX-D011"), "fail")

        declared_cleanup = text.replace("cleanup: []", "cleanup:\n  - 元TCで定義された事後状態を確認する", 1)
        declared_cleanup = declared_cleanup.replace(
            "| input-001 | profile-update | なし |",
            "| input-001 | profile-update | 元TCで定義された事後状態を確認する |",
            1,
        )
        declared_cleanup = declared_cleanup.replace(
            "| profile-update | 1回はプロフィール値1件の変更操作 | 3 | 1 | 1 | 0 | 1 | 3 |",
            "| profile-update | 1回はプロフィール値1件の変更操作 | 4 | 1 | 1 | 1 | 1 | 4 |",
            1,
        )
        declared_cleanup = declared_cleanup.replace(post_table, post_table + "\n" + post_row, 1)
        result = validate(declared_cleanup, expected, "TEX-OUT-002")
        self.assertEqual(next(item.status for item in result.assertions if item.id == "TEX-D011"), "pass")

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

    def test_test_execution_rejects_undefined_tc_side_effect_scope(self):
        validate = load_validator("test-execution")
        text, expected = eval_case("test-execution", "TEX-OUT-002")
        lines = text.splitlines()
        precondition_row = next(
            index
            for index, line in enumerate(lines)
            if line.startswith("| input-001 | profile-update |")
        )
        lines[precondition_row] = lines[precondition_row].replace("profile-update", "unknown-scope", 1)
        broken = "\n".join(lines)

        result = validate(broken, expected, "TEX-OUT-002")
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
