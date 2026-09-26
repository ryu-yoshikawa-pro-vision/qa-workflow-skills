from __future__ import annotations

import json
from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[4]
SKILLS_ROOT = REPO_ROOT / "skills"
SKILLS = (
    "qa-workflow",
    "spec-analysis",
    "question-analysis",
    "test-analysis",
    "test-requirement-design",
    "test-condition-design",
    "test-case-design",
    "coverage-analysis",
    "adversarial-review",
    "e2e-test-inspection",
    "e2e-test-implementation",
    "e2e-test-execution",
    "e2e-test-result-analysis",
    "e2e-test-reporting",
)


class TriggerDatasetTests(unittest.TestCase):
    def test_plan_counts_and_split_are_exact(self) -> None:
        total = 0
        for skill in SKILLS:
            with self.subTest(skill=skill):
                train_expected = (24, 12, 12) if skill in {"test-analysis", "test-condition-design"} else (12, 6, 6)
                validation_expected = (20, 10, 10) if skill in {"test-analysis", "test-condition-design"} else (8, 4, 4)
                train = json.loads((SKILLS_ROOT / skill / "evals" / "trigger" / "train_queries.json").read_text(encoding="utf-8"))
                validation = json.loads((SKILLS_ROOT / skill / "evals" / "trigger" / "validation_queries.json").read_text(encoding="utf-8"))
                for rows, expected in ((train, train_expected), (validation, validation_expected)):
                    self.assertEqual(len(rows), expected[0])
                    self.assertEqual(sum(row["should_trigger"] is True for row in rows), expected[1])
                    self.assertEqual(sum(row["should_trigger"] is False for row in rows), expected[2])
                    self.assertTrue(all(isinstance(row.get("query"), str) and row["query"].strip() for row in rows))
                self.assertTrue(
                    {row["query"] for row in train}.isdisjoint({row["query"] for row in validation})
                )
                total += len(train) + len(validation)
        self.assertEqual(total, 328)


if __name__ == "__main__":
    unittest.main()
