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

    def test_target_inspection_checks_parent_target_for_entity_references(self):
        validate = load_validator("test-target-inspection")
        text, expected = eval_case("test-target-inspection", "TTI-OUT-001")
        screen_row = "| target-001 | 注文履歴 | ナビゲーションから注文履歴 | 確認済み | 閲覧者、ja-JP、1440x900、test-order-42 | build-23 | 2026-09-26T09:00:00+09:00 |"
        target_2 = "| target-002 | 別領域 | 別経路 | 確認済み | 管理者 | build-23 | 2026-09-26T09:00:00+09:00 |"
        element_row = "| element-002 | target-002 | 別領域のボタン | button / 保存 | 操作可能 | 確認済み | 管理者 | build-23 | 2026-09-26T09:00:00+09:00 |"
        state_row = "| state-002 | target-002 | 別領域の状態 | 表示される | 初期表示 | 確認済み | 管理者 | build-23 | 2026-09-26T09:00:00+09:00 |"

        def add_row(source, anchor, row):
            self.assertIn(anchor, source)
            return source.replace(anchor, anchor + "\n" + row, 1)

        def with_second_target(source):
            return add_row(source, screen_row, target_2)

        cases = {}
        behavior = with_second_target(text)
        behavior = add_row(
            behavior,
            "| element-001 | target-001 | 注文番号リンク | link / Order 42 | 操作可能 | 確認済み | test-order-42、閲覧者 | build-23 | 2026-09-26T09:00:00+09:00 |",
            element_row,
        )
        cases["behavior element parent"] = add_row(
            behavior,
            "| target-001 | element-001 | 履歴表示 | 注文番号リンクを開く | 注文詳細へ遷移 | 注文詳細表示 | 確認済み | test-order-42、閲覧者 | build-23 | 2026-09-26T09:00:00+09:00 |",
            "| target-001 | element-002 | 別領域表示 | クリック | 保存画面へ遷移 | 保存画面 | 確認済み | 管理者 | build-23 | 2026-09-26T09:00:00+09:00 |",
        )

        state_base = with_second_target(text)
        state_base = add_row(
            state_base,
            "| state-001 | target-001 | 履歴表示 | 注文42が一覧に表示 | test-order-42を準備 | 確認済み | 閲覧者、ja-JP | build-23 | 2026-09-26T09:00:00+09:00 |",
            state_row,
        )
        cases["visual state parent"] = add_row(
            state_base,
            "| target-001 | state-001 | 行の重なり | 行の間隔が保たれている | evidence/orders.png | 確認済み | 1440x900 | build-23 | 2026-09-26T09:00:00+09:00 | 画像で確認 |",
            "| target-001 | state-002 | 別領域の表示 | 別領域状態を観測 |  | 確認済み | 管理者 | build-23 | 2026-09-26T09:00:00+09:00 | 参照のみ |",
        )
        dependency_table_end = "| --- | --- | --- | --- | --- | --- | --- | --- |\n\n## 既存テスト実装との対応（任意）"
        dependency_row = "| target-001 | state-002 | role=admin | 別領域の差異 | 確認済み | 管理者 | build-23 | 2026-09-26T09:00:00+09:00 |"
        self.assertIn(dependency_table_end, state_base)
        cases["dependency state parent"] = state_base.replace(
            dependency_table_end,
            "| --- | --- | --- | --- | --- | --- | --- | --- |\n" + dependency_row + "\n\n## 既存テスト実装との対応（任意）",
            1,
        )

        mapping_table_end = "| --- | --- | --- | --- | --- | --- |\n\n## 未確認 / 確認不能"
        mapping_row = "| target-001 | element-002 | POM | src/pages/other.ts | 別領域 | rev-2 |"
        self.assertIn(mapping_table_end, behavior)
        cases["repository mapping element parent"] = behavior.replace(
            mapping_table_end,
            "| --- | --- | --- | --- | --- | --- |\n" + mapping_row + "\n\n## 未確認 / 確認不能",
            1,
        )
        cases["snapshot state parent"] = add_row(
            state_base,
            "| target-001 | なし | 注文履歴領域 | snapshots/orders.yml | sha256:ab23 | なし | なし | 初回取得 | 機密値なしを確認 | 閲覧者、ja-JP | build-23 | 2026-09-26T09:00:00+09:00 |",
            "| target-001 | state-002 | 別領域 | snapshots/other.yml | sha256:cd45 | なし | なし | 初回取得 | 機密値なしを確認 | 管理者 | build-23 | 2026-09-26T09:00:00+09:00 |",
        )

        for name, broken in cases.items():
            with self.subTest(name=name):
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

    def test_target_inspection_disallows_save_records_without_persistence_request(self):
        validate = load_validator("test-target-inspection")
        text, expected = eval_case("test-target-inspection", "TTI-OUT-001")
        empty_template_table = text + "\n| 保存先 | 更新元revision / content identity | 更新方式 | 保存状態 | 保存後revision / content identity | 競合・制約 / 理由 | 確認元 |\n| --- | --- | --- | --- | --- | --- | --- |\n|  |  |  |  |  |  |  |\n"
        self.assertEqual(
            next(item.status for item in validate(empty_template_table, expected, "TTI-OUT-001").assertions if item.id == "TTI-D011"),
            "pass",
        )

        save_record = "| some-store | なし | create | 保存済み | rev-1 | 保存成功を確認 | 保存先 |"
        with_record = empty_template_table.replace("|  |  |  |  |  |  |  |", save_record, 1)
        result = validate(with_record, expected, "TTI-OUT-001")
        self.assertEqual(next(item.status for item in result.assertions if item.id == "TTI-D011"), "fail")

        update_text, update_expected = eval_case("test-target-inspection", "TTI-OUT-002")
        self.assertEqual(
            next(item.status for item in validate(update_text, update_expected, "TTI-OUT-002").assertions if item.id == "TTI-D011"),
            "pass",
        )

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

        invalid_kind = text.replace("| 画面 | target-002 | なし | 削除確認 |", "| 未知種別 | target-002 | なし | 削除確認 |", 1)
        result = validate(invalid_kind, expected, "TTI-OUT-002")
        self.assertEqual(next(item.status for item in result.assertions if item.id == "TTI-D009"), "fail")

    def test_deleted_elements_and_states_are_checked_against_their_own_tables(self):
        validate = load_validator("test-target-inspection")
        text, expected = eval_case("test-target-inspection", "TTI-OUT-002")

        element_deletion = "| UI要素 | target-001 | element-002 | 削除確認 | 要素が比較条件で存在しない | 管理者、user-25 | build-18 | 2026-09-26T09:30:00+09:00 |"
        element_update_table = "| UI要素 | target-001 | element-001 | 更新 | 検索ラベルを確認 | 管理者、user-25、同じ到達経路 | build-18 | 2026-09-26T09:30:00+09:00 |"
        with_element_deletion = text.replace(element_update_table, element_update_table + "\n" + element_deletion, 1)
        self.assertEqual(
            next(item.status for item in validate(with_element_deletion, expected, "TTI-OUT-002").assertions if item.id == "TTI-D009"),
            "pass",
        )
        current_element = "| element-002 | target-001 | 削除済み要素 | button / 削除済み | disabled | 確認済み | 管理者 | build-18 | 2026-09-26T09:30:00+09:00 |"
        resurrected_element = with_element_deletion.replace(
            "| element-001 | target-001 | ユーザー検索 | textbox / ユーザーを検索 | 操作可能 | 確認済み | 管理者、user-25 | build-18 | 2026-09-26T09:30:00+09:00 |",
            "| element-001 | target-001 | ユーザー検索 | textbox / ユーザーを検索 | 操作可能 | 確認済み | 管理者、user-25 | build-18 | 2026-09-26T09:30:00+09:00 |\n" + current_element,
            1,
        )
        self.assertEqual(
            next(item.status for item in validate(resurrected_element, expected, "TTI-OUT-002").assertions if item.id == "TTI-D009"),
            "fail",
        )

        state_deletion = "| 状態 | target-001 | state-002 | 削除確認 | 状態が比較条件で存在しない | 管理者、user-25 | build-18 | 2026-09-26T09:30:00+09:00 |"
        with_state_deletion = with_element_deletion.replace(element_deletion, "", 1).replace(
            element_update_table, element_update_table + "\n" + state_deletion, 1
        )
        self.assertEqual(
            next(item.status for item in validate(with_state_deletion, expected, "TTI-OUT-002").assertions if item.id == "TTI-D009"),
            "pass",
        )
        current_state = "| state-002 | target-001 | 削除済み状態 | 状態が表示される | user-25 | 確認済み | 管理者 | build-18 | 2026-09-26T09:30:00+09:00 |"
        resurrected_state = with_state_deletion.replace(
            "| state-001 | target-001 | 検索結果 | user-25が表示される | user-25あり | 確認済み | 管理者、ja-JP | build-18 | 2026-09-26T09:30:00+09:00 |",
            "| state-001 | target-001 | 検索結果 | user-25が表示される | user-25あり | 確認済み | 管理者、ja-JP | build-18 | 2026-09-26T09:30:00+09:00 |\n" + current_state,
            1,
        )
        self.assertEqual(
            next(item.status for item in validate(resurrected_state, expected, "TTI-OUT-002").assertions if item.id == "TTI-D009"),
            "fail",
        )

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

    def test_unconfirmed_behavior_rows_include_start_state_in_freshness_identity(self):
        validate = load_validator("test-target-inspection")
        text, expected = eval_case("test-target-inspection", "TTI-OUT-001")
        behavior_a = "| target-001 | element-001 | 履歴表示 | 注文番号リンクを開く | 注文詳細へ遷移 | 注文詳細表示 | 確認済み | test-order-42、閲覧者 | build-23 | 2026-09-26T09:00:00+09:00 |"
        old_behavior_a = behavior_a.replace("| 確認済み | test-order-42、閲覧者 | build-23 | 2026-09-26T09:00:00+09:00 |", "| 未確認 | test-order-42、閲覧者 | build-22 | 2026-09-25T09:00:00+09:00 |", 1)
        old_behavior_b = old_behavior_a.replace("| 履歴表示 |", "| 注文一覧 |", 1).replace(
            "| test-order-42、閲覧者 | build-22 | 2026-09-25T09:00:00+09:00 |",
            "| test-order-41、閲覧者 | build-21 | 2026-09-24T09:00:00+09:00 |",
            1,
        )
        prepared = text.replace(behavior_a, old_behavior_a, 1).replace(
            old_behavior_a, old_behavior_a + "\n" + old_behavior_b, 1
        )
        key_a = '["操作・ふるまい", "target-001", "element-001", "履歴表示", "注文番号リンクを開く"]'
        key_b = '["操作・ふるまい", "target-001", "element-001", "注文一覧", "注文番号リンクを開く"]'
        expected["unconfirmed_facts"] = {
            key_a: {
                "確認条件": "test-order-42、閲覧者",
                "確認version / build": "build-22",
                "確認日時": "2026-09-25T09:00:00+09:00",
            },
            key_b: {
                "確認条件": "test-order-41、閲覧者",
                "確認version / build": "build-21",
                "確認日時": "2026-09-24T09:00:00+09:00",
            },
        }
        refreshed_behavior_a = old_behavior_a.replace("| build-22 |", "| build-23 |", 1)
        broken = prepared.replace(old_behavior_a, refreshed_behavior_a, 1)
        result = validate(broken, expected, "TTI-OUT-001")
        freshness = next(item for item in result.assertions if item.id == "TTI-D007")
        self.assertEqual(freshness.status, "fail")
        self.assertEqual(len(freshness.evidence), 1)
        self.assertEqual(freshness.evidence[0]["key"], key_a)

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

    def test_test_execution_treats_target_none_as_a_value_outside_tc_cleanup(self):
        validate = load_validator("test-execution")
        text, expected = eval_case("test-execution", "TEX-OUT-001")
        row = "| input-001 | 開始済み | PASS | 注文番号42が表示 | 注文番号42を観測 | accessibility treeで確認 | observation:input-001 |"
        updated = text.replace(
            row,
            "| input-001 | 開始済み | PASS | 対象なし | 対象なし | accessibility treeで確認 | observation:input-001 |",
            1,
        )
        result = validate(updated, expected, "TEX-OUT-001")
        self.assertEqual(next(item.status for item in result.assertions if item.id == "TEX-D008"), "pass")

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

    def test_test_execution_requires_nonempty_when_action(self):
        validate = load_validator("test-execution")
        text, expected = eval_case("test-execution", "TEX-OUT-001")
        action_line = "      action: 注文番号42を検索欄へ入力する"
        self.assertIn(action_line, text)
        mutations = {
            "missing action": text.replace(action_line + "\n", "", 1),
            "empty action": text.replace(action_line, '      action: ""', 1),
        }
        for name, broken in mutations.items():
            with self.subTest(name=name):
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
        no_rerun_refs = text.replace(
            "| 前回実行成果物参照 | なし | 初回実行 |",
            "| 前回実行成果物参照 | execution-v1 | 前回成果物 |",
            1,
        )
        result = validate(no_rerun_refs, expected, "TEX-OUT-001")
        self.assertEqual(next(item.status for item in result.assertions if item.id == "TEX-D006"), "fail")

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

        for condition in ("対象環境", "許可origin", "version / build"):
            with self.subTest(empty_value=condition):
                lines = text.splitlines()
                index = next(i for i, line in enumerate(lines) if line.startswith(f"| {condition} |"))
                cells = lines[index].split("|")
                cells[2] = "  "
                lines[index] = "|".join(cells)
                broken = "\n".join(lines)
                result = validate(broken, expected, "TEX-OUT-002")
                self.assertEqual(next(item.status for item in result.assertions if item.id == "TEX-D009"), "fail")

        unavailable_version = text.replace(
            "| version / build | build-23 | 実対象 |",
            "| version / build | 取得不能 | 実対象 |",
            1,
        )
        result = validate(unavailable_version, expected, "TEX-OUT-002")
        self.assertEqual(next(item.status for item in result.assertions if item.id == "TEX-D009"), "pass")

    def test_test_execution_rejects_unrun_method_when_a_tc_started(self):
        validate = load_validator("test-execution")
        text, expected = eval_case("test-execution", "TEX-OUT-002")
        self.assertEqual(
            next(item.status for item in validate(text, expected, "TEX-OUT-002").assertions if item.id == "TEX-D007"),
            "pass",
        )
        started_but_unrun = text.replace(
            "| 使用した実行手段 | Playwright CLI | MCPに必要な能力なし、既存CLI利用可 |",
            "| 使用した実行手段 | 未実行 | MCPに必要な能力なし、既存CLI利用可 |",
            1,
        )
        result = validate(started_but_unrun, expected, "TEX-OUT-002")
        self.assertEqual(next(item.status for item in result.assertions if item.id == "TEX-D007"), "fail")

    def test_test_execution_separates_tc_postprocessing_from_runtime_cleanup(self):
        validate = load_validator("test-execution")
        text, expected = eval_case("test-execution", "TEX-OUT-002")
        self.assertEqual(
            next(item.status for item in validate(text, expected, "TEX-OUT-002").assertions if item.id == "TEX-D011"),
            "pass",
        )

        no_tc_cleanup_row = "| input-001 | 対象なし | 対象なし | なし | 元TCに事後cleanupの定義なし |"
        post_row = "| input-001 | 元TCで定義された事後処理 | 成功 | 変更前の値へ復元済み | 元TC cleanup |"
        inconsistent = text.replace("| input-001 | profile-update | なし |", "| input-001 | profile-update | 元TCで定義された事後処理 |", 1)
        inconsistent = inconsistent.replace(
            no_tc_cleanup_row, no_tc_cleanup_row + "\n" + post_row, 1
        )
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
        declared_cleanup = declared_cleanup.replace(no_tc_cleanup_row, post_row, 1)
        result = validate(declared_cleanup, expected, "TEX-OUT-002")
        self.assertEqual(next(item.status for item in result.assertions if item.id == "TEX-D011"), "pass")

        for absent_value in ("なし", "対象なし"):
            with self.subTest(absent_precondition=absent_value):
                missing_precondition_cleanup = declared_cleanup.replace(
                    "| input-001 | profile-update | 元TCで定義された事後状態を確認する |",
                    f"| input-001 | profile-update | {absent_value} |",
                    1,
                )
                result = validate(missing_precondition_cleanup, expected, "TEX-OUT-002")
                self.assertEqual(next(item.status for item in result.assertions if item.id == "TEX-D011"), "fail")

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
