from __future__ import annotations

import json
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
ROUTING_DIR = REPO_ROOT / "skills" / "qa-workflow" / "evals" / "deterministic"


class UiTargetRoutingContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.cases = json.loads(
            (ROUTING_DIR / "routing_cases.json").read_text(encoding="utf-8")
        )
        self.candidates = json.loads(
            (ROUTING_DIR / "routing_candidate_outputs.json").read_text(encoding="utf-8")
        )

    def test_fixture_count_and_identity_sets_are_synchronized(self) -> None:
        self.assertEqual(len(self.cases), 69)
        self.assertEqual(len(self.candidates), 69)
        self.assertEqual(
            {row["id"] for row in self.cases},
            {row["id"] for row in self.candidates},
        )

    def test_ui_target_routes_match_the_expected_entry_and_stop_boundaries(
        self,
    ) -> None:
        expected = {
            "WF-UI-TARGET-001": ("spec-analysis", "spec-analysis", ["spec-analysis"]),
            "WF-UI-TARGET-002": (
                "spec-analysis",
                "question-analysis",
                ["spec-analysis", "question-analysis"],
            ),
            "WF-UI-TARGET-003": (
                "question-analysis",
                "spec-analysis",
                ["question-analysis", "spec-analysis"],
            ),
            "WF-UI-TARGET-004": (
                "test-target-inspection",
                "test-target-inspection",
                ["test-target-inspection"],
            ),
            "WF-UI-TARGET-005": ("spec-analysis", "spec-analysis", ["spec-analysis"]),
            "WF-UI-TARGET-006": (
                "usability-evaluation",
                "usability-evaluation",
                ["usability-evaluation"],
            ),
            "WF-UI-TARGET-007": (
                "usability-inspection",
                "usability-inspection",
                ["usability-inspection"],
            ),
            "WF-UI-TARGET-008": (
                "wcag-conformance-evaluation",
                "wcag-conformance-evaluation",
                ["wcag-conformance-evaluation"],
            ),
        }
        actual = {
            row["id"]: (row["start"], row["final"], row["skills"])
            for row in self.cases
            if row["id"].startswith("WF-UI-TARGET-")
        }
        self.assertEqual(actual, expected)

        candidates = {row["id"]: row for row in self.candidates}
        for case_id, (start, final, skills) in expected.items():
            with self.subTest(case_id=case_id):
                candidate = candidates[case_id]
                self.assertEqual(candidate["start"], start)
                self.assertEqual(candidate["final"], final)
                self.assertEqual(candidate["skills"], skills)
        for case_id in ("WF-UI-TARGET-001", "WF-UI-TARGET-005"):
            self.assertNotIn("test-analysis", candidates[case_id]["skills"])


if __name__ == "__main__":
    unittest.main()
