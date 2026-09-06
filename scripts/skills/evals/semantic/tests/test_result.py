from __future__ import annotations

import json
import unittest

from scripts.skills.evals.semantic.result import JudgeResponseError, normalize_judge_response


CRITERIA = {
    "SEM-EX-001": {"id": "SEM-EX-001", "title": "Critical", "description": "d", "critical": True},
    "SEM-EX-002": {"id": "SEM-EX-002", "title": "Non critical", "description": "d", "critical": False},
}


def response(items: list[dict]) -> str:
    return json.dumps({"criteria": items}, ensure_ascii=False)


def item(criterion_id: str, rating: int | None = 4, evaluable: bool = True, evidence: list[str] | None = None) -> dict:
    return {
        "id": criterion_id,
        "evaluable": evaluable,
        "rating": rating,
        "reason": "具体的な根拠がある",
        "evidence": ["候補成果物の記述"] if evidence is None and evaluable else (evidence or []),
    }


class SemanticResultTests(unittest.TestCase):
    def normalize(self, raw: str, requested: list[str] | None = None):
        return normalize_judge_response(
            raw,
            skill="example-skill",
            eval_id="EX-SEM-001",
            requested_criteria=requested or ["SEM-EX-001", "SEM-EX-002"],
            criteria_by_id=CRITERIA,
        )

    def test_invalid_json_raises(self):
        with self.assertRaises(JudgeResponseError):
            self.normalize("```json\n{}\n```")

    def test_unknown_criterion_raises(self):
        with self.assertRaises(JudgeResponseError):
            self.normalize(response([item("SEM-EX-001"), item("SEM-EX-999")]))

    def test_duplicate_criterion_raises(self):
        with self.assertRaises(JudgeResponseError):
            self.normalize(response([item("SEM-EX-001"), item("SEM-EX-001")]))

    def test_missing_criterion_raises(self):
        with self.assertRaises(JudgeResponseError):
            self.normalize(response([item("SEM-EX-001")]))

    def test_rating_out_of_range_raises(self):
        with self.assertRaises(JudgeResponseError):
            self.normalize(response([item("SEM-EX-001", 5), item("SEM-EX-002")]))

    def test_not_evaluable_requires_null_rating(self):
        with self.assertRaises(JudgeResponseError):
            self.normalize(response([item("SEM-EX-001", 3, False, []), item("SEM-EX-002")]))

    def test_evaluable_requires_evidence(self):
        with self.assertRaises(JudgeResponseError):
            self.normalize(response([item("SEM-EX-001", 4, True, []), item("SEM-EX-002")]))

    def test_rating_three_and_four_pass(self):
        result = self.normalize(response([item("SEM-EX-001", 4), item("SEM-EX-002", 3)]))
        self.assertEqual(result["verdict"], "pass")
        self.assertEqual([entry["status"] for entry in result["criteria"]], ["pass", "pass"])

    def test_rating_two_needs_review(self):
        result = self.normalize(response([item("SEM-EX-001", 4), item("SEM-EX-002", 2)]))
        self.assertEqual(result["verdict"], "needs_review")
        self.assertEqual(result["criteria"][1]["status"], "needs_review")

    def test_non_critical_rating_one_needs_review(self):
        result = self.normalize(response([item("SEM-EX-001", 4), item("SEM-EX-002", 1)]))
        self.assertEqual(result["verdict"], "needs_review")

    def test_critical_rating_one_fails(self):
        result = self.normalize(response([item("SEM-EX-001", 1), item("SEM-EX-002", 4)]))
        self.assertEqual(result["verdict"], "fail")

    def test_not_evaluable_needs_review(self):
        result = self.normalize(
            response([item("SEM-EX-001", None, False, []), item("SEM-EX-002", 4)])
        )
        self.assertEqual(result["verdict"], "needs_review")
        self.assertEqual(result["criteria"][0]["status"], "not_evaluable")


if __name__ == "__main__":
    unittest.main()
