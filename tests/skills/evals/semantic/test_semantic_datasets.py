from __future__ import annotations

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
                self.assertEqual(len(dataset["cases"]), 2)
                self.assertEqual(len(dataset["criteria"]), len(dataset["criteria_by_id"]))
                self.assertEqual(len({case["id"] for case in dataset["cases"]}), 2)

                for case in dataset["cases"]:
                    self.assertTrue(case["input_text"].strip())
                    self.assertTrue(case["reference_text"].strip())
                    self.assertTrue(case["criteria"])
                    self.assertTrue(set(case["criteria"]) <= set(dataset["criteria_by_id"]))
                total_cases += len(dataset["cases"])

        self.assertEqual(total_cases, 18)


if __name__ == "__main__":
    unittest.main()
