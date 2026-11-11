from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .common import (
    AgentEvalError,
    atomic_write_json,
    canonical_fingerprint,
    sanitize_diagnostic,
)


def _load_result(path: Path) -> tuple[dict[str, Any], Path]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AgentEvalError(f"run result is unreadable: {path}") from exc
    if not isinstance(value, dict) or not isinstance(value.get("attempts"), list):
        raise AgentEvalError("run result has no attempts array")
    return value, path.parent


def _profile_conditions(run: dict[str, Any]) -> dict[str, Any]:
    return {
        "evaluator_revision": run.get("evaluator", {}).get("revision")
        or run.get("evaluator_revision"),
        "suite": run.get("suite"),
        "dataset_fingerprint": run.get("dataset_fingerprint"),
        "scenario_fingerprint": run.get("scenario_fingerprint"),
        "target_revision": run.get("target_revision"),
        "judge_reference_fingerprint": run.get("judge_reference_fingerprint"),
        "agent_command_fingerprint": run.get("agent_command_fingerprint"),
        "judge_command_fingerprint": run.get("judge_command_fingerprint"),
        "verifier_image": run.get("verifier_image"),
        "isolation": run.get("isolation"),
        "profile_fingerprint": run.get("profile_fingerprint")
        or run.get("execution_profile_fingerprint"),
        "profile_verification": run.get("profile_verification"),
        "repeat": run.get("repeat"),
        "agent": run.get("agent"),
        "judge": run.get("judge"),
    }


def _attempt_index(run: dict[str, Any]) -> dict[tuple[str, str, int], dict[str, Any]]:
    indexed: dict[tuple[str, str, int], dict[str, Any]] = {}
    for index, row in enumerate(run["attempts"]):
        suite = str(row.get("suite", run.get("suite", "qa-training-store")))
        skill = str(row.get("skill", "qa-training-store"))
        eval_id = str(row.get("eval_id", row.get("attempt_id", index)))
        repeat = row.get("repeat", index + 1)
        if not isinstance(repeat, int) or isinstance(repeat, bool):
            repeat = index + 1
        key = (suite + ":" + skill, eval_id, repeat)
        if key in indexed:
            raise AgentEvalError("run contains duplicate attempt identity")
        indexed[key] = row
    return indexed


def _load_grade(root: Path, row: dict[str, Any]) -> dict[str, Any] | None:
    reference = row.get("grade", {}).get("path")
    if not isinstance(reference, str):
        return None
    path = (root / reference).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError:
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _load_qts_judge(root: Path, row: dict[str, Any]) -> dict[str, Any] | None:
    relative = row.get("saved_result_root")
    if not isinstance(relative, str):
        return None
    path = root / relative / "judge-result.json"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def compare_runs(baseline_path: Path, candidate_path: Path) -> dict[str, Any]:
    baseline, baseline_root = _load_result(baseline_path)
    candidate, candidate_root = _load_result(candidate_path)
    baseline_conditions = _profile_conditions(baseline)
    candidate_conditions = _profile_conditions(candidate)
    mismatches = {
        key: {
            "baseline": baseline_conditions[key],
            "candidate": candidate_conditions[key],
        }
        for key in baseline_conditions
        if baseline_conditions[key] != candidate_conditions[key]
    }
    if (
        baseline.get("profile_verification") != "verified"
        or candidate.get("profile_verification") != "verified"
    ):
        mismatches["profile_verification"] = {
            "baseline": baseline.get("profile_verification"),
            "candidate": candidate.get("profile_verification"),
        }
    baseline_package = baseline.get("skill_package", {}).get("package_fingerprint")
    candidate_package = candidate.get("skill_package", {}).get("package_fingerprint")
    if (
        not baseline_package
        or not candidate_package
        or baseline_package == candidate_package
    ):
        baseline_package = baseline.get("skill_package_manifest", {}).get(
            "package_fingerprint", baseline_package
        )
        candidate_package = candidate.get("skill_package_manifest", {}).get(
            "package_fingerprint", candidate_package
        )
    if (
        not baseline_package
        or not candidate_package
        or baseline_package == candidate_package
    ):
        mismatches["skill_package_content"] = {
            "reason": "identical_or_unavailable_candidate_package_fingerprint"
        }
    if baseline.get("skill_revision") == candidate.get("skill_revision"):
        if not (
            candidate.get("skill_candidate_revision_status") == "uncommitted_patch"
            and baseline_package != candidate_package
        ):
            mismatches["skill_revision"] = {
                "reason": "candidate_revision_is_not_distinct"
            }
    baseline_attempts = _attempt_index(baseline)
    candidate_attempts = _attempt_index(candidate)
    common = sorted(set(baseline_attempts) & set(candidate_attempts))
    if len(baseline_attempts) < 2 or len(candidate_attempts) < 2:
        mismatches["repeat"] = {
            "baseline_attempts": len(baseline_attempts),
            "candidate_attempts": len(candidate_attempts),
            "required": 2,
        }
    if set(baseline_attempts) != set(candidate_attempts):
        mismatches["attempt_identity"] = {
            "baseline_only": sorted(set(baseline_attempts) - set(candidate_attempts)),
            "candidate_only": sorted(set(candidate_attempts) - set(baseline_attempts)),
        }
    rows: list[dict[str, Any]] = []
    for key in common:
        left = baseline_attempts[key]
        right = candidate_attempts[key]
        left_judge = _load_qts_judge(baseline_root, left)
        right_judge = _load_qts_judge(candidate_root, right)
        left_grade = _load_grade(baseline_root, left)
        right_grade = _load_grade(candidate_root, right)
        rows.append(
            {
                "identity": list(key),
                "baseline_status": left.get("status"),
                "candidate_status": right.get("status"),
                "status_changed": left.get("status") != right.get("status"),
                "baseline_judge_verdict": (left_judge or {}).get("status")
                or (left_judge or {}).get("normalized", {}).get("verdict"),
                "candidate_judge_verdict": (right_judge or {}).get("status")
                or (right_judge or {}).get("normalized", {}).get("verdict"),
                "baseline_grade_status": (left_grade or {}).get("status"),
                "candidate_grade_status": (right_grade or {}).get("status"),
                "criterion_comparison_available": bool(left_judge or left_grade)
                and bool(right_judge or right_grade),
                "skill_use_observation": {
                    "baseline": left.get("skill_use_observation", "unverified"),
                    "candidate": right.get("skill_use_observation", "unverified"),
                },
            }
        )
    comparable = not mismatches
    return {
        "schema_version": 1,
        "status": "comparable" if comparable else "not_comparable",
        "comparable": comparable,
        "baseline_result": str(baseline_path),
        "candidate_result": str(candidate_path),
        "baseline_conditions_fingerprint": canonical_fingerprint(baseline_conditions),
        "candidate_conditions_fingerprint": canonical_fingerprint(candidate_conditions),
        "condition_mismatches": mismatches,
        "attempts": rows,
        "interpretation": "Per-attempt evidence only; no aggregate score or causal claim is computed.",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Compare two saved Agent evaluation runs under fixed conditions."
    )
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = compare_runs(args.baseline, args.candidate)
        atomic_write_json(args.result, result)
    except (AgentEvalError, OSError, ValueError) as exc:
        print(
            f"run comparison failed: {sanitize_diagnostic(str(exc), 1000)}",
            file=sys.stderr,
        )
        return 2
    print(
        json.dumps(
            {"result": str(args.result), "status": result["status"]}, ensure_ascii=True
        )
    )
    return 0 if result["comparable"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
