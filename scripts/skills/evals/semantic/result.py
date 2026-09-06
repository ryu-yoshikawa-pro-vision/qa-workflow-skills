from __future__ import annotations

import json
from typing import Any


class JudgeResponseError(ValueError):
    pass


def _criterion_status(*, evaluable: bool, rating: int | None) -> str:
    if not evaluable:
        return "not_evaluable"
    if rating in (3, 4):
        return "pass"
    if rating == 2:
        return "needs_review"
    if rating == 1:
        return "fail"
    raise JudgeResponseError(f"invalid rating: {rating}")


def _overall_verdict(criteria: list[dict[str, Any]]) -> str:
    if any(item["critical"] and item["rating"] == 1 for item in criteria if item["rating"] is not None):
        return "fail"
    if any(
        item["status"] in {"needs_review", "fail", "not_evaluable"}
        for item in criteria
    ):
        return "needs_review"
    return "pass"


def normalize_judge_response(
    raw_response: str,
    *,
    skill: str,
    eval_id: str,
    requested_criteria: list[str],
    criteria_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    try:
        payload = json.loads(raw_response)
    except json.JSONDecodeError as exc:
        raise JudgeResponseError(f"judge response must be JSON only: {exc}") from exc

    if not isinstance(payload, dict) or set(payload) != {"criteria"}:
        raise JudgeResponseError("judge response must be an object containing only criteria")
    raw_criteria = payload["criteria"]
    if not isinstance(raw_criteria, list):
        raise JudgeResponseError("criteria must be an array")

    requested = set(requested_criteria)
    seen: set[str] = set()
    normalized: list[dict[str, Any]] = []

    for index, raw in enumerate(raw_criteria):
        if not isinstance(raw, dict):
            raise JudgeResponseError(f"criteria[{index}] must be an object")
        if set(raw) != {"id", "evaluable", "rating", "reason", "evidence"}:
            raise JudgeResponseError(f"criteria[{index}] has invalid fields")

        criterion_id = raw["id"]
        if not isinstance(criterion_id, str) or not criterion_id:
            raise JudgeResponseError(f"criteria[{index}].id must be a non-empty string")
        if criterion_id not in requested:
            raise JudgeResponseError(f"unknown criterion response: {criterion_id}")
        if criterion_id in seen:
            raise JudgeResponseError(f"duplicate criterion response: {criterion_id}")
        seen.add(criterion_id)

        evaluable = raw["evaluable"]
        if not isinstance(evaluable, bool):
            raise JudgeResponseError(f"{criterion_id}.evaluable must be boolean")

        rating = raw["rating"]
        if evaluable:
            if isinstance(rating, bool) or not isinstance(rating, int) or rating not in {1, 2, 3, 4}:
                raise JudgeResponseError(f"{criterion_id}.rating must be an integer from 1 to 4")
        elif rating is not None:
            raise JudgeResponseError(f"{criterion_id}.rating must be null when evaluable=false")

        reason = raw["reason"]
        if not isinstance(reason, str) or not reason.strip():
            raise JudgeResponseError(f"{criterion_id}.reason must be a non-empty string")

        evidence = raw["evidence"]
        if not isinstance(evidence, list) or any(not isinstance(item, str) for item in evidence):
            raise JudgeResponseError(f"{criterion_id}.evidence must be a string array")
        if evaluable and any(not item.strip() for item in evidence):
            raise JudgeResponseError(f"{criterion_id}.evidence must contain non-empty strings")
        if evaluable and not evidence:
            raise JudgeResponseError(f"{criterion_id}.evidence must contain at least one item when evaluable=true")
        if not evaluable and evidence:
            raise JudgeResponseError(f"{criterion_id}.evidence must be empty when evaluable=false")

        rubric = criteria_by_id[criterion_id]
        normalized.append(
            {
                "id": criterion_id,
                "title": rubric["title"],
                "critical": rubric["critical"],
                "rating": rating,
                "status": _criterion_status(evaluable=evaluable, rating=rating),
                "reason": reason,
                "evidence": evidence,
            }
        )

    missing = requested - seen
    if missing:
        raise JudgeResponseError(f"missing criterion response: {sorted(missing)}")
    if len(seen) != len(requested_criteria):
        raise JudgeResponseError("criterion response count does not match requested criteria")

    order = {criterion_id: index for index, criterion_id in enumerate(requested_criteria)}
    normalized.sort(key=lambda item: order[item["id"]])

    summary = {
        "pass": sum(item["status"] == "pass" for item in normalized),
        "needs_review": sum(item["status"] == "needs_review" for item in normalized),
        "fail": sum(item["status"] == "fail" for item in normalized),
        "not_evaluable": sum(item["status"] == "not_evaluable" for item in normalized),
    }
    return {
        "skill": skill,
        "eval_id": eval_id,
        "verdict": _overall_verdict(normalized),
        "criteria": normalized,
        "summary": summary,
    }
