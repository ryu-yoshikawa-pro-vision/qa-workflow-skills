from __future__ import annotations

import unittest

from tests.skills.runtime.test_traceability_runtime import (
    TraceabilityRuntimeTests,
    base_request,
    run,
)


class CoverageAnalysisTraceabilityTests(unittest.TestCase):
    def test_expected_runtime_and_entity_closure_is_complete(self) -> None:
        TraceabilityRuntimeTests().test_expected_sets_and_graph_are_complete()

    def test_formal_candidate_coverage_stays_separate_from_ci_graph(self) -> None:
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
        self.assertTrue(result["payload"]["can_complete"], result["issues"])
        self.assertEqual(
            result["payload"]["formal_design_metrics"][0]["pair_coverage"], "2/2"
        )
        self.assertFalse(
            any(node["node_type"] == "COND" for node in result["payload"]["nodes"])
        )
        self.assertFalse(
            any(
                "COND-001" in (edge["from"], edge["to"])
                for edge in result["payload"]["edges"]
            )
        )

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
