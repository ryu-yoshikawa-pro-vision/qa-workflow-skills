from __future__ import annotations

import json
import unittest
from pathlib import Path

from scripts.skills.evals.semantic.loader import load_semantic_skill
from scripts.skills.evals.semantic.result import normalize_judge_response

REPO_ROOT = Path(__file__).resolve().parents[4]
SKILLS_ROOT = REPO_ROOT / "skills"


class UiTargetCandidateResultTests(unittest.TestCase):
    def test_candidate_judgements_match_cases_and_quote_candidate_evidence(self) -> None:
        dataset = load_semantic_skill("ui-target-analysis", SKILLS_ROOT)
        output_root = dataset["semantic_root"] / "candidate_outputs"

        for case in dataset["cases"]:
            with self.subTest(eval_id=case["id"]):
                output_path = output_root / f"{case['id']}.md"
                result_path = output_root / "results" / f"{case['id']}.json"
                output = output_path.read_text(encoding="utf-8")
                result = json.loads(result_path.read_text(encoding="utf-8"))

                self.assertEqual(result["skill"], "ui-target-analysis")
                self.assertEqual(result["eval_id"], case["id"])
                self.assertEqual(
                    [item["id"] for item in result["criteria"]], case["criteria"]
                )
                self.assertTrue(
                    all(
                        evidence in output
                        for item in result["criteria"]
                        for evidence in item["evidence"]
                    )
                )

                judge_response = {
                    "criteria": [
                        {
                            "id": item["id"],
                            "evaluable": True,
                            "rating": item["rating"],
                            "reason": item["reason"],
                            "evidence": item["evidence"],
                        }
                        for item in result["criteria"]
                    ]
                }
                normalized = normalize_judge_response(
                    json.dumps(judge_response, ensure_ascii=False),
                    skill="ui-target-analysis",
                    eval_id=case["id"],
                    requested_criteria=case["criteria"],
                    criteria_by_id=dataset["criteria_by_id"],
                )
                self.assertEqual(normalized["verdict"], result["verdict"])
                self.assertEqual(normalized["summary"], result["summary"])


if __name__ == "__main__":
    unittest.main()
