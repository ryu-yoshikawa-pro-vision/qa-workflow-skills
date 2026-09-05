from __future__ import annotations

from pathlib import Path
import unittest

from scripts.skills.evals.deterministic.loader import discover_output_eval_skills, load_validators


REPO_ROOT = Path(__file__).resolve().parents[4]
SKILLS_ROOT = REPO_ROOT / "skills"


class RepositoryDeterministicIntegrationTests(unittest.TestCase):
    def test_output_eval_manifests_have_loadable_validators(self) -> None:
        expected = sorted(
            manifest.parents[2].name
            for manifest in SKILLS_ROOT.glob("*/evals/output/evals.json")
        )
        self.assertTrue(expected)
        self.assertEqual(discover_output_eval_skills(SKILLS_ROOT), expected)
        validators = load_validators(SKILLS_ROOT)
        self.assertEqual(sorted(validators), expected)
        self.assertTrue(all(callable(validate) for validate in validators.values()))


if __name__ == "__main__":
    unittest.main()
