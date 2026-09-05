from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from scripts.skills.evals.deterministic.loader import (
    SKILLS_ROOT,
    discover_output_eval_skills,
    load_validators,
)


class ValidatorLoaderTests(unittest.TestCase):
    def _validator_path(self, skills_root: Path, skill: str) -> Path:
        output_root = skills_root / skill / "evals" / "output"
        output_root.mkdir(parents=True)
        (output_root / "evals.json").write_text('{"cases": []}\n', encoding="utf-8")
        return skills_root / skill / "evals" / "deterministic" / "validator.py"

    def test_loads_all_output_eval_validators(self) -> None:
        repo_root = Path(__file__).resolve().parents[5]
        expected_skills_root = repo_root / "skills"
        self.assertEqual(SKILLS_ROOT, expected_skills_root)
        expected = sorted(
            manifest.parents[2].name
            for manifest in expected_skills_root.glob("*/evals/output/evals.json")
        )
        self.assertTrue(expected)
        self.assertEqual(discover_output_eval_skills(), expected)
        validators = load_validators()
        self.assertEqual(sorted(validators), expected)
        self.assertTrue(all(callable(validate) for validate in validators.values()))

    def test_missing_validator_is_not_silently_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skills_root = Path(tmp)
            self._validator_path(skills_root, "missing")
            with self.assertRaises(FileNotFoundError):
                load_validators(skills_root)

    def test_validator_must_export_validate_callable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skills_root = Path(tmp)
            path = self._validator_path(skills_root, "no-validate")
            path.parent.mkdir(parents=True)
            path.write_text("VALUE = 1\n", encoding="utf-8")
            with self.assertRaises(TypeError):
                load_validators(skills_root)

    def test_malformed_validator_does_not_load(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skills_root = Path(tmp)
            path = self._validator_path(skills_root, "malformed")
            path.parent.mkdir(parents=True)
            path.write_text("def validate(:\n", encoding="utf-8")
            with self.assertRaises(SyntaxError):
                load_validators(skills_root)


if __name__ == "__main__":
    unittest.main()
