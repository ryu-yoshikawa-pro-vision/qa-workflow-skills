from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from scripts.skills.evals.deterministic.loader import discover_output_eval_skills, load_validators


class ValidatorLoaderTests(unittest.TestCase):
    def _create_output_manifest(self, skills_root: Path, skill: str) -> Path:
        output_root = skills_root / skill / "evals" / "output"
        output_root.mkdir(parents=True)
        (output_root / "evals.json").write_text('{"cases": []}\n', encoding="utf-8")
        return skills_root / skill / "evals" / "deterministic" / "validator.py"

    def _write_validator(self, path: Path, source: str) -> None:
        path.parent.mkdir(parents=True)
        path.write_text(source, encoding="utf-8")

    def test_discovers_output_eval_skill_from_explicit_skills_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skills_root = Path(tmp) / "skills"
            path = self._create_output_manifest(skills_root, "example-skill")
            self._write_validator(path, "def validate(text, expected, eval_id):\n    return text, expected, eval_id\n")
            self.assertEqual(discover_output_eval_skills(skills_root), ["example-skill"])

    def test_loads_validator_from_explicit_skills_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skills_root = Path(tmp) / "skills"
            path = self._create_output_manifest(skills_root, "example-skill")
            self._write_validator(path, "def validate(text, expected, eval_id):\n    return text, expected, eval_id\n")
            validators = load_validators(skills_root)
            self.assertEqual(set(validators), {"example-skill"})
            self.assertEqual(
                validators["example-skill"]("output", {"known": True}, "EXAMPLE"),
                ("output", {"known": True}, "EXAMPLE"),
            )

    def test_missing_validator_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skills_root = Path(tmp) / "skills"
            self._create_output_manifest(skills_root, "example-skill")
            with self.assertRaises(FileNotFoundError):
                load_validators(skills_root)

    def test_validate_must_be_callable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skills_root = Path(tmp) / "skills"
            path = self._create_output_manifest(skills_root, "example-skill")
            self._write_validator(path, "validate = 1\n")
            with self.assertRaises(TypeError):
                load_validators(skills_root)

    def test_malformed_validator_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skills_root = Path(tmp) / "skills"
            path = self._create_output_manifest(skills_root, "example-skill")
            self._write_validator(path, "def validate(:\n")
            with self.assertRaises(SyntaxError):
                load_validators(skills_root)


if __name__ == "__main__":
    unittest.main()
