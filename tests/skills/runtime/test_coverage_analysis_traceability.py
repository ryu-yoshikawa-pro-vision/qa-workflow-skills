from __future__ import annotations

import copy
import unittest

from tests.skills.runtime.test_formal_design_contract import (
    contract as formal_contract,
)
from tests.skills.runtime.test_formal_design_contract import (
    drafts as formal_drafts,
)
from tests.skills.runtime.test_formal_design_contract import (
    packet as formal_packet,
)
from tests.skills.runtime.test_traceability_runtime import (
    TraceabilityRuntimeTests,
    base_request,
    run,
)


def verified_formal_design(packet: dict | None = None) -> dict:
    validated = formal_contract.validate_formal_design(
        formal_packet() if packet is None else packet,
        formal_drafts(),
    )
    return {
        **validated["__formal_design_summary__"],
        "formal_design_record": validated["__formal_design_record__"],
    }


class CoverageAnalysisTraceabilityTests(unittest.TestCase):
    def test_expected_runtime_and_entity_closure_is_complete(self) -> None:
        TraceabilityRuntimeTests().test_expected_sets_and_graph_are_complete()

    def test_formal_candidate_coverage_stays_separate_from_ci_graph(self) -> None:
        request = base_request()
        request["input"]["formal_design_summaries"] = [verified_formal_design()]
        result = run(request)
        self.assertEqual(result["runtime_status"], "ok", result)
        self.assertTrue(result["payload"]["can_complete"], result["issues"])
        self.assertEqual(
            result["payload"]["formal_design_metrics"][0]["pair_coverage"], "1/1"
        )
        self.assertTrue(
            result["payload"]["formal_design_metrics"][0]["record_verified"]
        )
        self.assertFalse(
            any(node["node_type"] == "COND" for node in result["payload"]["nodes"])
        )

    def test_other_test_level_pair_is_closed_by_formal_and_coverage_validators(
        self,
    ) -> None:
        value = formal_packet()
        value["source_refs"].append(
            {"ref": "TI-002", "revision": "i5", "currentness": "current"}
        )
        value["items"].append({"item_ref": "TI-002", "source_ref": "TI-002"})
        other_level = copy.deepcopy(value["pair_assessments"][0])
        other_level.update(
            {
                "item_ref": "TI-002",
                "decision": "other_test_level",
                "rationale": "TI-002はsystem levelで確認する",
                "test_level": "system",
                "tcn_draft_key": None,
                "expected_result_candidates": [],
            }
        )
        value["pair_assessments"].append(other_level)
        summary = verified_formal_design(value)
        request = base_request()
        request["input"]["formal_design_summaries"] = [summary]

        result = run(request)

        self.assertEqual(result["runtime_status"], "ok", result)
        self.assertTrue(result["payload"]["can_complete"], result["issues"])
        metric = result["payload"]["formal_design_metrics"][0]
        self.assertTrue(metric["record_verified"])
        self.assertEqual(metric["pair_denominator"], 2)
        self.assertEqual(metric["pair_closed"], 2)
        self.assertEqual(metric["pair_coverage"], "2/2")
        self.assertFalse(
            any(node["node_type"] == "COND" for node in result["payload"]["nodes"])
        )

    def test_coverage_rejects_decision_level_mismatch(self) -> None:
        summary = verified_formal_design()
        summary["formal_design_record"]["pair_assessments"][0]["test_level"] = "system"
        request = base_request()
        request["input"]["formal_design_summaries"] = [summary]

        result = run(request)

        self.assertEqual(result["runtime_status"], "invalid_input", result)

    def test_coverage_rejects_other_test_level_that_matches_assignment(self) -> None:
        value = formal_packet()
        value["source_refs"].append(
            {"ref": "TI-002", "revision": "i5", "currentness": "current"}
        )
        value["items"].append({"item_ref": "TI-002", "source_ref": "TI-002"})
        other_level = copy.deepcopy(value["pair_assessments"][0])
        other_level.update(
            {
                "item_ref": "TI-002",
                "decision": "other_test_level",
                "rationale": "invalid matching level",
                "test_level": "system",
                "tcn_draft_key": None,
                "expected_result_candidates": [],
            }
        )
        value["pair_assessments"].append(other_level)
        summary = verified_formal_design(value)
        summary["formal_design_record"]["pair_assessments"][1]["test_level"] = (
            "integration"
        )
        request = base_request()
        request["input"]["formal_design_summaries"] = [summary]

        result = run(request)

        self.assertEqual(result["runtime_status"], "invalid_input", result)

    def test_self_consistent_summary_without_formal_record_cannot_complete(
        self,
    ) -> None:
        request = base_request()
        request["input"]["formal_design_summaries"] = [
            {
                "design_ref": "FD-001",
                "revision": 1,
                "pair_denominator": 2,
                "pair_closed": 2,
                "pair_coverage": "2/2",
                "pair_coverage_status": "complete",
                "unresolved_pairs": [],
                "items_complete": True,
                "conditions_complete": True,
            }
        ]
        result = run(request)
        self.assertEqual(result["runtime_status"], "ok", result)
        self.assertFalse(result["payload"]["can_complete"], result["issues"])
        metric = result["payload"]["formal_design_metrics"][0]
        self.assertFalse(metric["record_verified"])
        self.assertIsNone(metric["pair_coverage"])

    def test_forged_two_of_two_summary_cannot_hide_unconfirmed_record_pair(
        self,
    ) -> None:
        value = formal_packet()
        value["items"].append({"item_ref": "TI-002", "source_ref": "TI-001"})
        unresolved = {
            **value["pair_assessments"][0],
            "item_ref": "TI-002",
            "decision": "unconfirmed",
            "rationale": "ownerからTI-002の適用範囲を確認する",
            "tcn_draft_key": None,
            "expected_result_candidates": [],
            "covered_by_pair": None,
            "reopen_condition": "TI-002 owner confirmation",
        }
        value["pair_assessments"].append(unresolved)
        summary = verified_formal_design(value)
        summary.update(
            {
                "pair_closed": 2,
                "pair_coverage": "2/2",
                "pair_coverage_status": "complete",
                "unresolved_pairs": [],
            }
        )
        request = base_request()
        request["input"]["formal_design_summaries"] = [summary]
        result = run(request)
        self.assertEqual(result["runtime_status"], "ok", result)
        self.assertFalse(result["payload"]["can_complete"], result["issues"])
        metric = result["payload"]["formal_design_metrics"][0]
        self.assertEqual(metric["pair_coverage"], "1/2")
        self.assertEqual(metric["pair_coverage_status"], "incomplete")
        self.assertEqual(metric["unresolved_pairs"][0]["decision"], "unconfirmed")

    def test_formal_design_ref_or_revision_mismatch_cannot_be_current(self) -> None:
        for field, value in (("design_ref", "FD-009"), ("revision", 2)):
            with self.subTest(field=field):
                summary = verified_formal_design()
                summary[field] = value
                request = base_request()
                request["input"]["formal_design_summaries"] = [summary]
                result = run(request)
                self.assertEqual(result["runtime_status"], "ok", result)
                self.assertFalse(result["payload"]["can_complete"], result["issues"])
        self.assertFalse(
            any(
                "COND-001" in (edge["from"], edge["to"])
                for edge in result["payload"]["edges"]
            )
        )

    def test_stale_formal_source_cannot_close_its_pair(self) -> None:
        value = formal_packet()
        next(row for row in value["source_refs"] if row["ref"] == "TI-001")[
            "currentness"
        ] = "stale"
        summary = verified_formal_design(value)
        request = base_request()
        request["input"]["formal_design_summaries"] = [summary]

        result = run(request)

        self.assertEqual(result["runtime_status"], "ok", result)
        self.assertFalse(result["payload"]["can_complete"], result["issues"])
        metric = result["payload"]["formal_design_metrics"][0]
        self.assertEqual(metric["pair_coverage_status"], "incomplete")
        self.assertEqual(metric["pair_closed"], 0)
        self.assertEqual(metric["unresolved_pairs"][0]["decision"], "blocked")

    def test_unmapped_stale_formal_source_blocks_all_pairs(self) -> None:
        value = formal_packet()
        value["source_refs"].append(
            {"ref": "UNMAPPED-001", "revision": "u1", "currentness": "stale"}
        )
        summary = verified_formal_design(value)
        summary.update(
            {
                "pair_closed": 1,
                "pair_coverage": "1/1",
                "pair_coverage_status": "complete",
                "unresolved_pairs": [],
                "items_complete": True,
                "conditions_complete": True,
            }
        )
        request = base_request()
        request["input"]["formal_design_summaries"] = [summary]

        result = run(request)

        self.assertEqual(result["runtime_status"], "ok", result)
        self.assertFalse(result["payload"]["can_complete"], result["issues"])
        metric = result["payload"]["formal_design_metrics"][0]
        self.assertEqual(metric["pair_coverage_status"], "incomplete")
        self.assertEqual(metric["pair_closed"], 0)
        self.assertEqual(metric["unresolved_pairs"][0]["decision"], "blocked")

    def test_formal_record_with_incomplete_history_cannot_be_verified(self) -> None:
        value = formal_packet()
        value["revision"] = 2
        value["history"] = [
            {
                "revision": 1,
                "change_reason": "rev2 reason",
                "pair_decisions": [
                    {
                        "item_ref": "TI-001",
                        "condition_ref": "COND-001",
                        "decision": "adopted",
                    }
                ],
                "candidate_assignments": [
                    {
                        "candidate_ref": "ER-001",
                        "item_ref": "TI-001",
                        "condition_ref": "COND-001",
                    },
                    {
                        "candidate_ref": "ER-002",
                        "item_ref": "TI-001",
                        "condition_ref": "COND-001",
                    },
                ],
                "retired_candidate_refs": [],
            }
        ]
        summary = verified_formal_design(value)
        summary["formal_design_record"]["history"][0]["candidate_assignments"] = []
        request = base_request()
        request["input"]["formal_design_summaries"] = [summary]

        result = run(request)

        self.assertEqual(result["runtime_status"], "invalid_input")
        self.assertNotEqual(result.get("result_status"), "ready")

    def test_zero_or_incomplete_candidate_population_never_reports_100_percent(
        self,
    ) -> None:
        cases = [
            {
                "design_ref": "FD-001",
                "revision": 1,
                "pair_denominator": 0,
                "pair_closed": 0,
                "pair_coverage": None,
                "pair_coverage_status": "unknown_zero_denominator",
                "unresolved_pairs": [],
                "items_complete": True,
                "conditions_complete": True,
            },
            {
                "design_ref": "FD-002",
                "revision": 1,
                "pair_denominator": 1,
                "pair_closed": 1,
                "pair_coverage": None,
                "pair_coverage_status": "incomplete_population",
                "unresolved_pairs": [],
                "items_complete": False,
                "conditions_complete": True,
            },
        ]
        for summary in cases:
            with self.subTest(design_ref=summary["design_ref"]):
                request = base_request()
                request["input"]["formal_design_summaries"] = [summary]
                result = run(request)
                self.assertEqual(result["runtime_status"], "ok", result)
                self.assertFalse(result["payload"]["can_complete"], result["issues"])
                self.assertIsNone(
                    result["payload"]["formal_design_metrics"][0]["pair_coverage"]
                )

    def test_formal_candidate_summary_rejects_false_complete_100_percent(self) -> None:
        request = base_request()
        request["input"]["formal_design_summaries"] = [
            {
                "design_ref": "FD-003",
                "revision": 1,
                "pair_denominator": 1,
                "pair_closed": 1,
                "pair_coverage": "1/1",
                "pair_coverage_status": "complete",
                "unresolved_pairs": [],
                "items_complete": False,
                "conditions_complete": True,
            }
        ]
        self.assertEqual(run(request)["runtime_status"], "invalid_input")


if __name__ == "__main__":
    unittest.main()
