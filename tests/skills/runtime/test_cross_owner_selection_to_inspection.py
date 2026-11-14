"""e2e-test-selectionの結果をe2e-test-inspectionへ渡す横断契約。

選定側の実`inspection_handoff()`の出力から、inspectionの出力とfixtureを組み立て、
inspectionの実validatorへ渡す。手書きのhandoffは使わない。
"""

from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tests" / "skills" / "runtime"))

import test_e2e_selection_contract as selection_fixture  # noqa: E402

from scripts.skills.evals.deterministic.loader import load_validators  # noqa: E402

VALIDATOR = load_validators()["e2e-test-inspection"]
contract = selection_fixture.contract

HEADER = """# E2E対象inspection
## 対象決定
| E2E対象 / 識別子 | TC ID（存在時のみ） | E2E実装参照 | 決定根拠 | 扱い |
| --- | --- | --- | --- | --- |
"""
TAIL = """## repo / 実対象の確認元・鮮度
| 項目 | 値 | 確認元 | 確認日時 / commit |
| --- | --- | --- | --- |
| branch | feat/e2e | repo | 2026-11-13 |
| commit | abc123 | repo | 2026-11-13 |
| working tree | clean | repo | 2026-11-13 |
| 対象repo / workspace | app | repo | 2026-11-13 |
| テスト環境URL / origin | https://app.test | 実対象 | 2026-11-13 |
| 実対象確認日時 | 2026-11-13T10:00+09:00 | 実対象 | 2026-11-13 |
| version / build ID | build-1 | 実対象 | 2026-11-13 |
## 実装・実行に影響する事実
| 事実 | 内容 | 確認元 | 実装 / 実行への影響 |
| --- | --- | --- | --- |
| Playwright構成 / 実行入口 | playwright.config.ts / npm test:e2e | repo | 既存入口を再利用 |
| spec / fixture / helper / Page Object | tests/checkout.spec.ts | repo | 既存helperを再利用 |
| 認証・データ・開始状態 | test user / clean account | repo | 開始前状態 |
| locator / 観測方法 | data-testid / URL | 実対象 | 安定参照 |
| 実効設定・reporter・証跡 | chromium / json reporter | repo | result artifact |
## 安全条件・準備・cleanup
| 条件 | 状態 | 根拠 / 許可 | 実行主体 / cleanup制約 |
| --- | --- | --- | --- |
| URL / origin | 許可済み | ユーザー提供情報 | execution |
| 副作用 | テストデータのみ | ユーザー提供情報 | runner cleanup |
| run外の準備 | test user準備済み | repo | 秘密情報を出力しない |
| runner管理setup / cleanup | 確認済み | repo | runner管理 |
| 証跡・認証状態 | local artifactのみ | repo | 共有不可 |
## 既存E2Eとの関係
| 対象 | 扱い | 既存E2E実装参照 | 根拠 / 備考 |
| --- | --- | --- | --- |
| checkout | 新規E2E実装 |  | 既存対象なし |
## 実装可否・未確認・ブロック
| 範囲 | 実装可否 / 状態 | 理由 | 次の担当 |
| --- | --- | --- | --- |
| checkout | 実装可能 | 必要事実が確認済み | e2e-test-implementation |
"""


def inspection_doc(rows: list[tuple[str, str, str]]) -> str:
    body = "".join(
        f"| {target} |  | tests/checkout.spec.ts > {target} | {basis} | {handling} |\n"
        for target, basis, handling in rows
    )
    return HEADER + body + TAIL


def expected_for(handoff: dict, *, excluded: list[str]) -> dict:
    return {
        "selection_handoff": {
            "selection_ref": handoff["selection_ref"],
            "selection_revision": str(handoff["selection_revision"]),
            "usable": handoff["usable"],
            "target_candidate_ids": [row["candidate_id"] for row in handoff["targets"]],
            "excluded_candidate_ids": excluded,
        }
    }


def failed(result) -> set[str]:
    return {a["id"] for a in result.to_dict()["assertions"] if a["status"] == "fail"}


class SelectionToInspectionTests(unittest.TestCase):
    def handoff(self, packet: dict | None = None) -> dict:
        return contract.inspection_handoff(
            packet if packet is not None else selection_fixture.selection()
        )

    def test_only_selected_current_candidates_are_handed_over(self) -> None:
        handoff = self.handoff()
        self.assertTrue(handoff["usable"])
        self.assertEqual(
            [t["candidate_id"] for t in handoff["targets"]], ["E2E-CAND-001"]
        )
        self.assertEqual(handoff["selection_ref"], "E2ESEL-001")
        self.assertEqual(
            [s["ref"] for s in handoff["targets"][0]["sources"]], ["SPEC-001", "TI-001"]
        )

    def test_inspection_accepts_output_that_records_the_selection(self) -> None:
        handoff = self.handoff()
        basis = (
            f"{handoff['selection_ref']}@{handoff['selection_revision']} / E2E-CAND-001"
        )
        doc = inspection_doc([("checkout-primary E2E-CAND-001", basis, "新規E2E実装")])
        result = VALIDATOR(doc, expected_for(handoff, excluded=["E2E-CAND-002"]), "X")
        self.assertEqual(failed(result), set(), result.to_dict())

    def test_inspection_rejects_missing_selection_ref_and_unselected_targets(
        self,
    ) -> None:
        handoff = self.handoff()
        expected = expected_for(handoff, excluded=["E2E-CAND-002"])
        no_ref = inspection_doc(
            [("checkout-primary E2E-CAND-001", "主要経路", "新規E2E実装")]
        )
        self.assertIn("E2E-INSP-D017", failed(VALIDATOR(no_ref, expected, "X")))
        basis = f"{handoff['selection_ref']}@{handoff['selection_revision']}"
        not_selected = inspection_doc(
            [
                ("checkout-primary E2E-CAND-001", basis, "新規E2E実装"),
                ("non-payment E2E-CAND-002", basis, "新規E2E実装"),
            ]
        )
        self.assertIn("E2E-INSP-D017", failed(VALIDATOR(not_selected, expected, "X")))
        missing_target = inspection_doc([("other flow", "対象外", "E2E対象外")])
        self.assertIn("E2E-INSP-D017", failed(VALIDATOR(missing_target, expected, "X")))

    def test_stale_selection_hands_over_nothing_and_blocks_implementation(
        self,
    ) -> None:
        packet = copy.deepcopy(selection_fixture.selection())
        packet["source_refs"][1]["currentness"] = "stale"
        handoff = self.handoff(packet)
        self.assertFalse(handoff["usable"])
        self.assertEqual(handoff["targets"], [])
        self.assertIn("TI-001", handoff["withheld_reason"]["unresolved_source_refs"])
        basis = f"{handoff['selection_ref']}@{handoff['selection_revision']}"
        expected = expected_for(handoff, excluded=[])
        implementing = inspection_doc(
            [("checkout-primary E2E-CAND-001", basis, "新規E2E実装")]
        )
        self.assertIn("E2E-INSP-D017", failed(VALIDATOR(implementing, expected, "X")))
        blocked = inspection_doc(
            [("checkout-primary E2E-CAND-001", basis, "ブロック中")]
        )
        self.assertNotIn("E2E-INSP-D017", failed(VALIDATOR(blocked, expected, "X")))

    def test_incomplete_population_is_not_usable(self) -> None:
        packet = copy.deepcopy(selection_fixture.selection())
        packet["population_complete"] = False
        packet["blockers"] = ["ownerから全item一覧を取得する"]
        handoff = self.handoff(packet)
        self.assertFalse(handoff["usable"])
        self.assertEqual(handoff["targets"], [])


if __name__ == "__main__":
    unittest.main()
