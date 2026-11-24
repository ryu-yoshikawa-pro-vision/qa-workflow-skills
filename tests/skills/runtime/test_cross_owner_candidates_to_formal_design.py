"""D（test-item／condition-analysis）の候補をE（formal-design-v1）へ渡す横断契約。

Dの実`materialize`で作った候補artifactを`formal_design_sources`で投影し、Eの実
`validate_formal_design`へ渡す。EのTI-*はEが採番し、Dの候補を自動採用しない。
"""

from __future__ import annotations

import copy
import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tests" / "skills" / "runtime"))

import test_formal_design_contract as e_fixture  # noqa: E402
import test_test_item_condition_analysis as d_fixture  # noqa: E402

E_PATH = ROOT / "skills/test-condition-design/scripts/condition_structure.py"
SPEC = importlib.util.spec_from_file_location("cross_owner_condition_structure", E_PATH)
assert SPEC is not None and SPEC.loader is not None
condition_structure = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(condition_structure)


class CandidatesToFormalDesignTests(unittest.TestCase):
    def materialized(self) -> tuple[dict, dict, list[dict]]:
        snapshot = d_fixture.feature_inventory()
        sources = [d_fixture._feature_ref_for(snapshot), d_fixture.spec_ref()]
        items = d_fixture._materialize_item(
            d_fixture.item_request(
                candidates=[d_fixture.item_candidate("order-api")],
                feature_snapshot=snapshot,
                sources=sources,
            )
        )
        conditions = d_fixture._materialize_condition(
            d_fixture.condition_request(
                candidates=[d_fixture.condition_candidate("order-authz")],
                feature_snapshot=snapshot,
                sources=sources,
            )
        )
        return items["candidate"], conditions["candidate"], sources

    def projected(self, current_sources: list[dict]) -> tuple[dict, dict]:
        item_artifact, condition_artifact, _ = self.materialized()
        items = d_fixture.run_items(
            {
                "operation": "formal_design_sources",
                "artifact": item_artifact,
                "current_source_refs": current_sources,
            }
        )
        conditions = d_fixture.run_conditions(
            {
                "operation": "formal_design_sources",
                "artifact": condition_artifact,
                "current_source_refs": current_sources,
            }
        )
        return items, conditions

    def formal_packet(self, items: dict, conditions: dict) -> dict:
        packet = e_fixture.packet()
        candidate_item = items["item_sources"][0]
        condition = conditions["condition_candidates"][0]
        packet["source_refs"] = [
            row
            for row in packet["source_refs"]
            if row["ref"] in {"ARCH-001", "SPEC-001"}
        ]
        packet["source_refs"].extend(items["source_refs"])
        packet["source_refs"].extend(conditions["source_refs"])
        # EのTI-*はEが採番し、Dの候補は根拠sourceとしてだけ参照する。
        packet["items"] = [
            {"item_ref": "TI-001", "source_ref": candidate_item["source_ref"]}
        ]
        packet["condition_candidates"] = [condition]
        packet["pair_assessments"][0]["condition_ref"] = condition["condition_ref"]
        return packet

    def test_current_candidates_are_accepted_as_formal_design_sources(self) -> None:
        _, _, sources = self.materialized()
        items, conditions = self.projected(sources)
        self.assertTrue(items["valid"], items)
        self.assertTrue(conditions["valid"], conditions)
        self.assertEqual(
            {row["currentness"] for row in items["source_refs"]}, {"current"}
        )
        self.assertTrue(items["item_sources"][0]["candidate_ref"].startswith("ITEM-"))
        self.assertTrue(
            conditions["condition_candidates"][0]["condition_ref"].startswith("COND-")
        )
        packet = self.formal_packet(items, conditions)
        result = condition_structure.validate_formal_design(packet, e_fixture.drafts())
        self.assertIn("formal-ti1-cond1", result)
        self.assertEqual(result["__blocked_draft_keys__"], [])
        self.assertEqual(result["__formal_design_summary__"]["pair_closed"], 1)

    def test_changed_feature_source_marks_candidates_stale_for_formal_design(
        self,
    ) -> None:
        _, _, sources = self.materialized()
        changed = copy.deepcopy(sources)
        changed[0]["revision"] = "feature-r-changed"
        changed[0]["content_hash"] = "c" * 64
        items, conditions = self.projected(changed)
        self.assertEqual(items["status"], "incomplete")
        self.assertEqual(
            {row["currentness"] for row in items["source_refs"]}, {"stale"}
        )
        packet = self.formal_packet(items, conditions)
        result = condition_structure.validate_formal_design(packet, e_fixture.drafts())
        # staleな候補sourceを根拠にした採用済みpairはTCN draftを生成せず、要再検証として残す。
        self.assertEqual(result["__blocked_draft_keys__"], ["formal-ti1-cond1"])
        self.assertNotIn("formal-ti1-cond1", result)
        summary = result["__formal_design_summary__"]
        self.assertEqual(summary["pair_closed"], 0)
        self.assertEqual(summary["pair_denominator"], 1)

    def test_d_item_ids_are_not_accepted_as_formal_item_refs(self) -> None:
        _, _, sources = self.materialized()
        items, conditions = self.projected(sources)
        packet = self.formal_packet(items, conditions)
        packet["items"][0]["item_ref"] = items["item_sources"][0]["candidate_ref"]
        packet["pair_assessments"][0]["item_ref"] = packet["items"][0]["item_ref"]
        with self.assertRaises(condition_structure.FormalDesignError):
            condition_structure.validate_formal_design(packet, e_fixture.drafts())


if __name__ == "__main__":
    unittest.main()
