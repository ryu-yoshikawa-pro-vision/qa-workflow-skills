from __future__ import annotations

import json
from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[4]
SKILLS_ROOT = REPO_ROOT / "skills"
SKILLS = tuple(sorted(path.parent.name for path in SKILLS_ROOT.glob("*/SKILL.md")))


class TriggerDatasetTests(unittest.TestCase):
    def test_current_repository_datasets_are_nonempty_balanced_and_disjoint(self) -> None:
        total = 0
        for skill in SKILLS:
            with self.subTest(skill=skill):
                train = json.loads((SKILLS_ROOT / skill / "evals" / "trigger" / "train_queries.json").read_text(encoding="utf-8"))
                validation = json.loads((SKILLS_ROOT / skill / "evals" / "trigger" / "validation_queries.json").read_text(encoding="utf-8"))
                for rows in (train, validation):
                    self.assertTrue(rows)
                    self.assertTrue(all(isinstance(row.get("query"), str) and row["query"].strip() for row in rows))
                    self.assertTrue(all(isinstance(row.get("should_trigger"), bool) for row in rows))
                    positives = sum(row["should_trigger"] is True for row in rows)
                    negatives = sum(row["should_trigger"] is False for row in rows)
                    self.assertGreater(positives, 0)
                    self.assertEqual(positives, negatives)
                    self.assertTrue(all(isinstance(row.get("query"), str) and row["query"].strip() for row in rows))
                self.assertTrue(
                    {row["query"] for row in train}.isdisjoint({row["query"] for row in validation})
                )
                total += len(train) + len(validation)
        self.assertGreater(total, 0)


if __name__ == "__main__":
    unittest.main()
