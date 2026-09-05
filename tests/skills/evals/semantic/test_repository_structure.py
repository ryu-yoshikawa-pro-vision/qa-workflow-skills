from __future__ import annotations

from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[4]
SKILLS_ROOT = REPO_ROOT / "skills"
CANONICAL_SKILLS = (
    "qa-workflow",
    "spec-analysis",
    "question-analysis",
    "test-analysis",
    "test-requirement-design",
    "test-condition-design",
    "test-case-design",
    "coverage-analysis",
    "adversarial-review",
)


class SemanticRepositoryStructureTests(unittest.TestCase):
    def test_all_canonical_skills_have_semantic_dataset_files(self):
        for skill in CANONICAL_SKILLS:
            with self.subTest(skill=skill):
                semantic = SKILLS_ROOT / skill / "evals" / "semantic"
                self.assertTrue((semantic / "rubric.json").is_file())
                self.assertTrue((semantic / "evals.json").is_file())


if __name__ == "__main__":
    unittest.main()
