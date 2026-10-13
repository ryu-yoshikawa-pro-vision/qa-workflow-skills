"""Choose the next fixed migration action for qa-workflow inputs."""

from __future__ import annotations

import re
import sys
from typing import Any

from runtime_contract import (
    MAX_AGGREGATE_INPUT_BYTES,
    InvalidInput,
    LimitExceeded,
    canonical_json_bytes,
    ensure_list,
    reject_unknown,
    strict_loads,
)

_CORE_SKILLS = (
    "test-requirement-design",
    "test-condition-design",
    "test-case-design",
)
_OPTIONAL_SKILLS = ("usability-inspection", "wcag-conformance-evaluation")
_ORDER = (*_CORE_SKILLS, *_OPTIONAL_SKILLS)
_ENTITY_TYPES = {
    "test-requirement-design": {"tr"},
    "test-condition-design": {"tcn", "model", "ci"},
    "test-case-design": {"tc"},
}
_ENTITY_REF_PATTERNS = {
    "tr": r"TR-\d{3}",
    "tcn": r"TCN-\d{3}",
    "ci": r"TCN-\d{3}-CI\d{2,}",
    "tc": r"TC-\d{3}",
}


def _ids(value: Any, name: str, pattern: str) -> list[str]:
    rows = ensure_list(value, name)
    if not all(
        isinstance(row, str) and re.fullmatch(pattern, row) for row in rows
    ) or rows != sorted(set(rows)):
        raise InvalidInput(f"{name} must be unique, sorted, and valid")
    return rows


def _inventory(value: Any) -> list[dict[str, Any]]:
    rows = ensure_list(value, "runtime_inventory")
    if rows and not set(_CORE_SKILLS).issubset(
        {row.get("skill") for row in rows if isinstance(row, dict)}
    ):
        raise InvalidInput("runtime_inventory is missing a core skill")
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise InvalidInput(f"runtime_inventory[{index}] must be an object")
        reject_unknown(
            row,
            {
                "skill",
                "artifact_present",
                "runtime_contract_version",
                "entity_schema_version",
                "verification_status",
            },
        )
        skill = row.get("skill")
        if skill not in _ORDER or skill in seen:
            raise InvalidInput("runtime_inventory skill is unknown or duplicated")
        seen.add(skill)
        if row.get("artifact_present") is not True:
            raise InvalidInput("runtime_inventory may contain only present artifacts")
        status = row.get("verification_status")
        versions = (
            row.get("runtime_contract_version"),
            row.get("entity_schema_version"),
        )
        if status == "legacy_valid":
            valid_versions = versions == ("runtime-v1", "entity-state-v1")
        elif status == "current_valid":
            valid_versions = versions == ("runtime-v2", "entity-state-v2")
        elif status == "cutover_in_progress":
            valid_versions = skill == "test-condition-design" and versions == (
                "runtime-v2",
                "entity-state-v2",
            )
        else:
            valid_versions = False
        if not valid_versions:
            raise InvalidInput("runtime_inventory verification and versions disagree")
        result.append(dict(row))
    if [row["skill"] for row in result] != sorted(
        (row["skill"] for row in result), key=_ORDER.index
    ):
        raise InvalidInput("runtime_inventory is not in fixed migration order")

    # Current artifacts may form only a verified prefix. The first incomplete
    # artifact is followed by legacy artifacts; TCD alone may be resumable.
    statuses = [row["verification_status"] for row in result]
    seen_incomplete = False
    for row in result:
        status = row["verification_status"]
        if status == "current_valid":
            if seen_incomplete:
                raise InvalidInput("runtime inventory has out-of-order v2 artifacts")
        else:
            seen_incomplete = True
            if (
                status == "cutover_in_progress"
                and row["skill"] != "test-condition-design"
            ):
                raise InvalidInput("only TCD may have cutover_in_progress")
    if "cutover_in_progress" in statuses:
        index = statuses.index("cutover_in_progress")
        if any(status != "current_valid" for status in statuses[:index]):
            raise InvalidInput(
                "TCD partial cutover is not preceded by a verified v2 prefix"
            )
        if any(status != "legacy_valid" for status in statuses[index + 1 :]):
            raise InvalidInput("TCD partial cutover is followed by an invalid state")
    return result


def _validate_ui_target(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise InvalidInput("ui_target_package must be an object")
    reject_unknown(
        value,
        {"present", "current_scope_ids", "ready_scope_ids", "blocked_scope_ids"},
    )
    if not isinstance(value.get("present"), bool):
        raise InvalidInput("ui_target_package.present must be boolean")
    current = _ids(value.get("current_scope_ids"), "current_scope_ids", r"SCOPE-\d{3,}")
    ready = _ids(value.get("ready_scope_ids"), "ready_scope_ids", r"SCOPE-\d{3,}")
    blocked = _ids(value.get("blocked_scope_ids"), "blocked_scope_ids", r"SCOPE-\d{3,}")
    if not value["present"] and (current or ready or blocked):
        raise InvalidInput("absent ui_target_package must have empty scope arrays")
    if set(ready) & set(blocked) or set(ready) | set(blocked) != set(current):
        raise InvalidInput("ready and blocked scope sets must partition current scopes")
    return {
        "present": value["present"],
        "current_scope_ids": current,
        "ready_scope_ids": ready,
        "blocked_scope_ids": blocked,
    }


def _active_downstream(value: Any) -> list[dict[str, Any]]:
    rows = ensure_list(value, "active_downstream")
    result = []
    seen: set[tuple[str, str, str]] = set()
    order: list[tuple[str, str, str]] = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise InvalidInput(f"active_downstream[{index}] must be an object")
        reject_unknown(row, {"skill", "entity_type", "entity_ref", "scope_refs"})
        skill = row.get("skill")
        entity_type = row.get("entity_type")
        entity_ref = row.get("entity_ref")
        if (
            skill not in _ENTITY_TYPES
            or entity_type not in _ENTITY_TYPES[skill]
            or not isinstance(entity_ref, str)
            or not entity_ref.strip()
        ):
            raise InvalidInput("active_downstream identity is invalid")
        expected_pattern = _ENTITY_REF_PATTERNS.get(entity_type)
        if (
            expected_pattern is not None
            and re.fullmatch(expected_pattern, entity_ref) is None
        ):
            raise InvalidInput("active_downstream entity_ref is not canonical")
        identity = (skill, entity_type, entity_ref)
        if identity in seen:
            raise InvalidInput("active_downstream identity is duplicated")
        seen.add(identity)
        order.append(identity)
        scope_refs = _ids(row.get("scope_refs"), "scope_refs", r"SCOPE-\d{3,}")
        result.append(
            {
                "skill": skill,
                "entity_type": entity_type,
                "entity_ref": entity_ref,
                "scope_refs": scope_refs,
            }
        )
    if order != sorted(order):
        raise InvalidInput("active_downstream must be identity-sorted")
    return result


def evaluate(request: Any) -> dict[str, Any]:
    if not isinstance(request, dict):
        raise InvalidInput("top-level JSON must be an object")
    reject_unknown(
        request,
        {"runtime_inventory", "v2_baseline", "ui_target_package", "active_downstream"},
    )
    inventory = _inventory(request.get("runtime_inventory"))
    baseline = request.get("v2_baseline")
    if not isinstance(baseline, dict):
        raise InvalidInput("v2_baseline must be an object")
    reject_unknown(
        baseline, {"qa_workflow_verification_valid", "qa_workflow_can_complete"}
    )
    if not all(
        isinstance(baseline.get(field), bool)
        for field in ("qa_workflow_verification_valid", "qa_workflow_can_complete")
    ):
        raise InvalidInput("v2_baseline fields must be boolean")
    if (
        baseline["qa_workflow_can_complete"]
        and not baseline["qa_workflow_verification_valid"]
    ):
        raise InvalidInput("qa-workflow completion requires valid verification")
    package = _validate_ui_target(request.get("ui_target_package"))
    downstream = _active_downstream(request.get("active_downstream"))

    unfinished = [
        row for row in inventory if row["verification_status"] != "current_valid"
    ]
    if unfinished and baseline["qa_workflow_verification_valid"]:
        raise InvalidInput(
            "current qa-workflow baseline cannot contain unverified runtime artifacts"
        )
    if unfinished and not baseline["qa_workflow_verification_valid"]:
        next_row = unfinished[0]
        return {
            "valid": True,
            "migration_status": "runtime_v2_cutover_required",
            "cutover_next_action": {
                "skill": next_row["skill"],
                "phase": {
                    "test-requirement-design": "all",
                    "test-condition-design": "resume",
                    "test-case-design": "all",
                }.get(next_row["skill"]),
            },
            "blocking_issue": None,
            "issues": [],
        }
    if (
        not baseline["qa_workflow_verification_valid"]
        or not baseline["qa_workflow_can_complete"]
    ):
        return {
            "valid": True,
            "migration_status": "runtime_v2_cutover_required",
            "cutover_next_action": {"skill": "qa-workflow", "phase": None},
            "blocking_issue": None,
            "issues": [],
        }
    if not package["present"]:
        return {
            "valid": True,
            "migration_status": "ui_target_migration_required",
            "cutover_next_action": None,
            "blocking_issue": None,
            "issues": [],
        }
    unscoped = [row for row in downstream if not row["scope_refs"]]
    if unscoped:
        if package["blocked_scope_ids"] or not package["current_scope_ids"]:
            return {
                "valid": True,
                "migration_status": "scope_ownership_baseline_required",
                "cutover_next_action": None,
                "blocking_issue": "scope_ownership_baseline_required",
                "issues": [
                    {
                        "issue_type": "scope_ownership_baseline_required",
                        "blocking": True,
                    }
                ],
            }
        return {
            "valid": True,
            "migration_status": "scope_ownership_normalization_required",
            "cutover_next_action": None,
            "blocking_issue": None,
            "issues": [],
        }
    return {
        "valid": True,
        "migration_status": "partial_progression_ready",
        "cutover_next_action": None,
        "blocking_issue": None,
        "issues": [],
    }


def main() -> int:
    raw = sys.stdin.buffer.read(MAX_AGGREGATE_INPUT_BYTES + 1)
    try:
        if len(raw) > MAX_AGGREGATE_INPUT_BYTES:
            raise LimitExceeded("aggregate stdin limit exceeded")
        response = evaluate(strict_loads(raw, aggregate=True))
        exit_code = 0
    except (InvalidInput, LimitExceeded) as exc:
        response = {
            "valid": False,
            "migration_status": None,
            "cutover_next_action": None,
            "blocking_issue": None,
            "issues": [
                {"issue_type": exc.issue_type, "blocking": True, "message": exc.message}
            ],
        }
        exit_code = 0
    except Exception as exc:  # pragma: no cover - defensive CLI boundary
        response = {
            "valid": False,
            "migration_status": None,
            "cutover_next_action": None,
            "blocking_issue": None,
            "issues": [
                {"issue_type": "internal_error", "blocking": True, "message": str(exc)}
            ],
        }
        exit_code = 1
    sys.stdout.buffer.write(canonical_json_bytes(response) + b"\n")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
