from __future__ import annotations

import json
from pathlib import Path
import unittest

from scripts.skills.evals.semantic.loader import load_semantic_skill
from test_repository_structure import CANONICAL_SKILLS


REPO_ROOT = Path(__file__).resolve().parents[4]
SKILLS_ROOT = REPO_ROOT / "skills"

class SemanticDatasetTests(unittest.TestCase):
    def test_repository_semantic_datasets_are_complete(self):
        total_cases = 0
        for skill in CANONICAL_SKILLS:
            with self.subTest(skill=skill):
                dataset = load_semantic_skill(skill, SKILLS_ROOT)
                self.assertEqual(dataset["skill"], skill)
                manifest = json.loads((SKILLS_ROOT / skill / "evals" / "semantic" / "evals.json").read_text(encoding="utf-8"))
                self.assertEqual(len(dataset["cases"]), len(manifest["cases"]))
                self.assertEqual(len(dataset["criteria"]), len(dataset["criteria_by_id"]))
                self.assertEqual(len({case["id"] for case in dataset["cases"]}), len(manifest["cases"]))

                for case in dataset["cases"]:
                    self.assertTrue(case["input_text"].strip())
                    self.assertTrue(case["reference_text"].strip())
                    self.assertTrue(case["criteria"])
                    self.assertTrue(set(case["criteria"]) <= set(dataset["criteria_by_id"]))
                if skill in {"test-target-inspection", "test-execution", "regression-testing", "exploratory-testing", "qa-knowledge"}:
                    critical_ids = {criterion["id"] for criterion in dataset["criteria"] if criterion["critical"]}
                    covered_ids = {
                        criterion_id
                        for case in dataset["cases"]
                        for criterion_id in case["criteria"]
                    }
                    missing_critical_ids = sorted(critical_ids - covered_ids)
                    self.assertFalse(missing_critical_ids, f"critical criteria without semantic case coverage: {missing_critical_ids}")
                total_cases += len(dataset["cases"])

        actual_total = sum(
            len(load_semantic_skill(skill, SKILLS_ROOT)["cases"])
            for skill in CANONICAL_SKILLS
        )
        self.assertEqual(total_cases, actual_total)

    def test_plan_responsibility_mapping_is_documented(self):
        text = (REPO_ROOT / "EVALS.md").read_text(encoding="utf-8")
        required_ids = [
            *(f"RISK-SEM-{index:03d}" for index in range(3, 8)),
            *(f"TCN-SEM-{index:03d}" for index in range(3, 15)),
            *(f"REV-SEM-{index:03d}" for index in range(3, 9)),
        ]
        for case_id in required_ids:
            with self.subTest(case_id=case_id):
                self.assertIn(case_id, text)


if __name__ == "__main__":
    unittest.main()
