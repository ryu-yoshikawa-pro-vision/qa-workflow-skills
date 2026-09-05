from __future__ import annotations

from collections.abc import Callable
import importlib.util
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SKILLS_ROOT = REPO_ROOT / "skills"


def discover_output_eval_skills(skills_root: Path = SKILLS_ROOT) -> list[str]:
    manifests = sorted(skills_root.glob("*/evals/output/evals.json"))
    return [manifest.parents[2].name for manifest in manifests]


def validator_path(skill: str, skills_root: Path = SKILLS_ROOT) -> Path:
    return skills_root / skill / "evals" / "deterministic" / "validator.py"


def load_validator(skill: str, skills_root: Path = SKILLS_ROOT) -> Callable:
    path = validator_path(skill, skills_root)
    if not path.is_file():
        raise FileNotFoundError(f"deterministic validator is required for output-eval skill {skill}: {path}")

    module_name = f"_deterministic_validator_{skill.replace('-', '_')}"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot create module spec for deterministic validator {skill}: {path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    validate = getattr(module, "validate", None)
    if not callable(validate):
        raise TypeError(f"deterministic validator must export callable validate: {path}")
    return validate


def load_validators(skills_root: Path = SKILLS_ROOT) -> dict[str, Callable]:
    return {skill: load_validator(skill, skills_root) for skill in discover_output_eval_skills(skills_root)}
