from __future__ import annotations

import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[4]
SKILLS_ROOT = REPO_ROOT / "skills"


class SemanticDatasetError(ValueError):
    pass


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SemanticDatasetError(f"invalid JSON: {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise SemanticDatasetError(f"JSON root must be an object: {path}")
    return data


def _non_empty_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SemanticDatasetError(f"{field} must be a non-empty string")
    return value


def discover_semantic_skills(skills_root: Path = SKILLS_ROOT) -> list[str]:
    return sorted(
        path.parents[1].name
        for path in skills_root.glob("*/evals/semantic")
        if path.is_dir()
    )


def load_semantic_skill(skill: str, skills_root: Path = SKILLS_ROOT) -> dict[str, Any]:
    semantic_root = skills_root / skill / "evals" / "semantic"
    rubric_path = semantic_root / "rubric.json"
    evals_path = semantic_root / "evals.json"

    rubric = _read_json(rubric_path)
    evals = _read_json(evals_path)

    if set(rubric) != {"skill", "criteria"}:
        raise SemanticDatasetError(f"rubric.json must contain only skill and criteria: {rubric_path}")
    if set(evals) != {"skill", "cases"}:
        raise SemanticDatasetError(f"evals.json must contain only skill and cases: {evals_path}")

    if rubric.get("skill") != skill:
        raise SemanticDatasetError(f"rubric skill must match directory name: {rubric_path}")
    if evals.get("skill") != skill:
        raise SemanticDatasetError(f"evals skill must match directory name: {evals_path}")

    raw_criteria = rubric.get("criteria")
    if not isinstance(raw_criteria, list):
        raise SemanticDatasetError(f"criteria must be an array: {rubric_path}")

    criteria: list[dict[str, Any]] = []
    criteria_by_id: dict[str, dict[str, Any]] = {}
    for index, raw in enumerate(raw_criteria):
        if not isinstance(raw, dict):
            raise SemanticDatasetError(f"criterion must be an object: {rubric_path}#{index}")
        if set(raw) != {"id", "title", "description", "critical"}:
            raise SemanticDatasetError(f"criterion has invalid fields: {rubric_path}#{index}")
        criterion_id = _non_empty_string(raw.get("id"), f"criteria[{index}].id")
        title = _non_empty_string(raw.get("title"), f"criteria[{index}].title")
        description = _non_empty_string(raw.get("description"), f"criteria[{index}].description")
        critical = raw.get("critical")
        if not isinstance(critical, bool):
            raise SemanticDatasetError(f"criteria[{index}].critical must be boolean")
        if criterion_id in criteria_by_id:
            raise SemanticDatasetError(f"duplicate criterion id: {criterion_id}")
        criterion = {
            "id": criterion_id,
            "title": title,
            "description": description,
            "critical": critical,
        }
        criteria.append(criterion)
        criteria_by_id[criterion_id] = criterion

    raw_cases = evals.get("cases")
    if not isinstance(raw_cases, list):
        raise SemanticDatasetError(f"cases must be an array: {evals_path}")

    cases: list[dict[str, Any]] = []
    case_ids: set[str] = set()
    for index, raw in enumerate(raw_cases):
        if not isinstance(raw, dict):
            raise SemanticDatasetError(f"case must be an object: {evals_path}#{index}")
        if set(raw) != {"id", "input", "reference", "criteria"}:
            raise SemanticDatasetError(f"case has invalid fields: {evals_path}#{index}")
        case_id = _non_empty_string(raw.get("id"), f"cases[{index}].id")
        if case_id in case_ids:
            raise SemanticDatasetError(f"duplicate case id: {case_id}")
        case_ids.add(case_id)

        input_rel = _non_empty_string(raw.get("input"), f"cases[{index}].input")
        reference_rel = _non_empty_string(raw.get("reference"), f"cases[{index}].reference")
        requested = raw.get("criteria")
        if not isinstance(requested, list) or not requested:
            raise SemanticDatasetError(f"cases[{index}].criteria must be a non-empty array")
        if any(not isinstance(item, str) or not item.strip() for item in requested):
            raise SemanticDatasetError(f"cases[{index}].criteria must contain non-empty strings")
        if len(requested) != len(set(requested)):
            raise SemanticDatasetError(f"duplicate criterion in case {case_id}")
        unknown = sorted(set(requested) - set(criteria_by_id))
        if unknown:
            raise SemanticDatasetError(f"unknown criterion in case {case_id}: {unknown}")

        input_path = semantic_root / input_rel
        reference_path = semantic_root / reference_rel
        if not input_path.is_file():
            raise FileNotFoundError(input_path)
        if not reference_path.is_file():
            raise FileNotFoundError(reference_path)

        cases.append(
            {
                "id": case_id,
                "input": input_rel,
                "reference": reference_rel,
                "criteria": list(requested),
                "input_path": input_path,
                "reference_path": reference_path,
                "input_text": input_path.read_text(encoding="utf-8"),
                "reference_text": reference_path.read_text(encoding="utf-8"),
            }
        )

    return {
        "skill": skill,
        "criteria": criteria,
        "criteria_by_id": criteria_by_id,
        "cases": cases,
        "semantic_root": semantic_root,
    }


def load_semantic_case(
    skill: str,
    eval_id: str,
    skills_root: Path = SKILLS_ROOT,
) -> tuple[dict[str, Any], dict[str, Any]]:
    dataset = load_semantic_skill(skill, skills_root)
    for case in dataset["cases"]:
        if case["id"] == eval_id:
            return dataset, case
    raise KeyError(f"unknown semantic eval id for {skill}: {eval_id}")
