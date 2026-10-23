"""Standalone deterministic lifecycle helpers for exploratory QA sessions."""

from __future__ import annotations

import hashlib
import json
from typing import Any
from urllib.parse import urlsplit

MODES = {"exploration", "investigation"}
SESSION_STATES = {
    "未開始",
    "実行中",
    "部分完了（ブロック中あり）",
    "ブロック中",
    "完了",
}
CLEANUP_STATES = {
    "成功",
    "失敗",
    "未確認",
    "対象なし",
    "意図的に残した状態",
    "一部失敗",
}
CHARTER_FIELDS = {
    "purpose",
    "in_scope",
    "out_of_scope",
    "source_refs",
    "focus_refs",
    "timebox_or_exit_condition",
    "allowed_origins",
    "allowed_operations",
    "side_effect_operations",
    "side_effect_scope",
    "side_effect_action_definition",
    "side_effect_maximum",
    "cleanup_plan",
    "evidence_policy",
    "block_conditions",
}


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def charter_identity(
    charter: dict[str, Any], target_snapshot: Any, environment_conditions: Any
) -> str:
    return hashlib.sha256(
        _canonical(
            {
                "charter": charter,
                "target_snapshot": target_snapshot,
                "environment_conditions": environment_conditions,
            }
        )
    ).hexdigest()


def validate_charter(mode: str, charter: dict[str, Any]) -> dict[str, Any]:
    missing = sorted(
        field
        for field in CHARTER_FIELDS
        if field not in charter or charter[field] is None or charter[field] == ""
    )
    issues: list[str] = []
    if mode not in MODES:
        issues.append("invalid_mode")
    if mode == "investigation" and not any(
        charter.get(key)
        for key in ("symptom_ref", "hypothesis_ref", "symptom", "hypothesis")
    ):
        issues.append("investigation_requires_symptom_or_hypothesis")
    if not isinstance(charter.get("allowed_origins"), list) or not charter.get(
        "allowed_origins"
    ):
        issues.append("allowed_origins_required")
    if not isinstance(charter.get("allowed_operations"), list) or not charter.get(
        "allowed_operations"
    ):
        issues.append("allowed_operations_required")
    side_effect_operations = charter.get("side_effect_operations")
    if not isinstance(side_effect_operations, list) or any(
        item not in charter.get("allowed_operations", [])
        for item in side_effect_operations
    ):
        issues.append("invalid_side_effect_operation_mapping")
    maximum = charter.get("side_effect_maximum")
    if not isinstance(maximum, int) or isinstance(maximum, bool) or maximum < 0:
        issues.append("invalid_side_effect_maximum")
    return {
        "valid": not missing and not issues,
        "missing_fields": missing,
        "issues": issues,
    }


def _origin(value: str) -> str | None:
    parsed = urlsplit(value)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username
        or parsed.password
    ):
        return None
    try:
        port = parsed.port
    except ValueError:
        return None
    default_port = (parsed.scheme == "http" and port == 80) or (
        parsed.scheme == "https" and port == 443
    )
    suffix = f":{port}" if port and not default_port else ""
    return f"{parsed.scheme.lower()}://{parsed.hostname.lower()}{suffix}"


def authorize_operation(
    charter: dict[str, Any],
    *,
    target_url: str,
    operation: str,
    prior_side_effect_attempts: int,
    uncertain_previous_attempt: bool = False,
    state_check_result: str | None = None,
) -> dict[str, Any]:
    target_origin = _origin(target_url)
    allowed = {
        _origin(value)
        for value in charter.get("allowed_origins", [])
        if isinstance(value, str)
    }
    if not target_origin or target_origin not in allowed:
        return {"status": "blocked", "reason": "origin_not_allowed"}
    if operation not in charter.get("allowed_operations", []):
        return {"status": "blocked", "reason": "operation_not_allowed"}
    if state_check_result is not None and (
        not isinstance(state_check_result, str)
        or state_check_result not in {"applied", "not_applied", "inconclusive"}
    ):
        return {"status": "blocked", "reason": "invalid_state_check_result"}
    if state_check_result is not None and not uncertain_previous_attempt:
        return {"status": "blocked", "reason": "state_check_without_uncertain_attempt"}
    is_side_effect = operation in charter.get("side_effect_operations", [])
    if is_side_effect and uncertain_previous_attempt:
        if state_check_result == "applied":
            return {
                "status": "blocked",
                "reason": "previous_side_effect_already_applied",
                "state_check_complete": True,
                "retryable": False,
            }
        if state_check_result != "not_applied":
            return {
                "status": "blocked",
                "reason": "state_check_required",
                "state_check_complete": False,
                "retryable": False,
            }
    consumed = prior_side_effect_attempts + (1 if uncertain_previous_attempt else 0)
    next_attempt = consumed + 1
    if is_side_effect and next_attempt > charter.get("side_effect_maximum", 0):
        return {
            "status": "blocked",
            "reason": "side_effect_limit_reached",
            "consumed_attempts": consumed,
            "state_check_complete": state_check_result == "not_applied",
            "retryable": False,
        }
    return {
        "status": "allowed",
        "origin": target_origin,
        "operation": operation,
        "side_effect_attempt_number": next_attempt if is_side_effect else None,
        "previous_attempt_outcome": "unknown" if uncertain_previous_attempt else None,
        "state_check_complete": (
            state_check_result in {"applied", "not_applied"}
            if uncertain_previous_attempt
            else None
        ),
        "retryable": (
            not is_side_effect
            or not uncertain_previous_attempt
            or state_check_result == "not_applied"
        ),
    }


def validate_session(session: dict[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    charter = session.get("charter")
    if not isinstance(charter, dict):
        return {"valid": False, "issues": ["charter_missing"]}
    result = validate_charter(session.get("mode"), charter)
    issues.extend(result["issues"])
    if result["missing_fields"]:
        issues.extend(
            f"missing_charter_field:{field}" for field in result["missing_fields"]
        )
    if session.get("state") not in SESSION_STATES:
        issues.append("invalid_session_state")
    observations = session.get("observations", [])
    findings = session.get("findings", [])
    if not isinstance(observations, list) or not isinstance(findings, list):
        issues.append("observations_and_findings_must_be_separate_lists")
        observations, findings = [], []
    observation_refs = [
        item.get("observation_ref") for item in observations if isinstance(item, dict)
    ]
    finding_refs = [
        item.get("finding_ref") for item in findings if isinstance(item, dict)
    ]
    if (
        len(observation_refs) != len(observations)
        or len(observation_refs) != len(set(observation_refs))
        or any(not ref for ref in observation_refs)
    ):
        issues.append("observation_refs_missing_or_duplicate")
    if (
        len(finding_refs) != len(findings)
        or len(finding_refs) != len(set(finding_refs))
        or any(not ref for ref in finding_refs)
    ):
        issues.append("finding_refs_missing_or_duplicate")
    obs_set = set(observation_refs)
    observation_evidence = all(
        isinstance(item, dict)
        and item.get("evidence_refs")
        and item.get("observed_fact")
        and item.get("action_or_observation")
        for item in observations
    )
    for finding in findings:
        if not isinstance(finding, dict):
            issues.append("invalid_finding")
            continue
        refs = finding.get("source_observation_refs", [])
        if not refs or not set(refs) <= obs_set:
            issues.append(
                f"finding_source_observation_unresolved:{finding.get('finding_ref')}"
            )
        if (
            not finding.get("evidence_refs")
            or not finding.get("follow_up_reason")
            or not finding.get("recommended_routing")
        ):
            issues.append(
                f"finding_missing_evidence_or_reason:{finding.get('finding_ref')}"
            )
    cleanup = session.get("cleanup", {})
    if cleanup.get("status") not in CLEANUP_STATES:
        issues.append("invalid_cleanup_state")
    if (
        session.get("state") == "完了"
        and cleanup.get("required")
        and cleanup.get("status") not in {"成功", "意図的に残した状態"}
    ):
        issues.append("completed_session_has_unresolved_cleanup")
    if (
        session.get("state") == "完了"
        and session.get("residual_side_effect")
        and (
            cleanup.get("status") != "意図的に残した状態"
            or cleanup.get("authorized_residual") is not True
        )
    ):
        issues.append("completed_session_has_unauthorized_residual_side_effect")
    if not observation_evidence:
        issues.append("observation_missing_action_fact_or_evidence")
    return {"valid": not issues, "issues": issues}


def can_resume(
    existing: dict[str, Any],
    incoming_charter: dict[str, Any],
    target_snapshot: Any,
    environment_conditions: Any,
) -> dict[str, Any]:
    if existing.get("state") == "完了":
        return {"status": "blocked", "reason": "completed_session_is_immutable"}
    identity = charter_identity(
        incoming_charter, target_snapshot, environment_conditions
    )
    if identity != existing.get("charter_snapshot_identity"):
        return {
            "status": "new_session_required",
            "reason": "charter_scope_or_environment_changed",
        }
    return {"status": "resume_allowed", "session_ref": existing.get("session_ref")}


def complete_session(
    session: dict[str, Any],
    *,
    exit_condition_reached: bool,
    cleanup: dict[str, Any],
    residual_side_effects: list[Any] | None = None,
) -> dict[str, Any]:
    if session.get("state") == "完了":
        return {"status": "blocked", "reason": "completed_session_is_immutable"}
    if not exit_condition_reached:
        return {"status": "blocked", "reason": "charter_exit_condition_not_reached"}
    if cleanup.get("required") and cleanup.get("status") not in {
        "成功",
        "意図的に残した状態",
    }:
        return {"status": "blocked", "reason": "required_cleanup_unconfirmed_or_failed"}
    residuals = list(residual_side_effects or [])
    if residuals and (
        cleanup.get("status") != "意図的に残した状態"
        or cleanup.get("authorized_residual") is not True
    ):
        return {"status": "blocked", "reason": "unauthorized_residual_side_effect"}
    next_session = dict(session)
    next_session["state"] = "完了"
    next_session["cleanup"] = cleanup
    next_session["residual_side_effect"] = residuals
    return {"status": "complete", "session": next_session}


def record_attempt(
    charter: dict[str, Any], attempts: list[dict[str, Any]], attempt: dict[str, Any]
) -> dict[str, Any]:
    refs = [item.get("attempt_ref") for item in attempts]
    attempt_ref = attempt.get("attempt_ref")
    if not isinstance(attempt_ref, str) or not attempt_ref or attempt_ref in refs:
        return {"status": "blocked", "reason": "attempt_ref_missing_or_duplicate"}
    outcome = attempt.get("outcome")
    if not isinstance(outcome, str) or outcome not in {
        "completed",
        "failed",
        "unknown",
    }:
        return {"status": "blocked", "reason": "invalid_attempt_outcome"}
    operation = attempt.get("operation")
    is_side_effect = operation in charter.get("side_effect_operations", [])
    if not operation or attempt.get("side_effect") is not is_side_effect:
        return {"status": "blocked", "reason": "side_effect_mapping_mismatch"}
    state_check_for = attempt.get("state_check_for")
    state_check_result = attempt.get("state_check_result")
    if (state_check_for is None) != (state_check_result is None):
        return {"status": "blocked", "reason": "invalid_state_check_record"}
    if state_check_for is not None:
        if is_side_effect:
            return {"status": "blocked", "reason": "state_check_must_be_read_only"}
        if not isinstance(state_check_result, str) or state_check_result not in {
            "applied",
            "not_applied",
            "inconclusive",
        }:
            return {"status": "blocked", "reason": "invalid_state_check_result"}
        referenced = next(
            (
                item
                for item in attempts
                if item.get("attempt_ref") == state_check_for
                and item.get("side_effect") is True
                and item.get("outcome") == "unknown"
            ),
            None,
        )
        if referenced is None:
            return {"status": "blocked", "reason": "state_check_target_not_unknown"}
        prior_checks = [
            item
            for item in attempts
            if item.get("state_check_for") == state_check_for
            and item.get("outcome") == "completed"
            and isinstance(item.get("state_check_result"), str)
            and item.get("state_check_result") in {"applied", "not_applied"}
        ]
        if prior_checks:
            return {"status": "blocked", "reason": "state_check_already_complete"}
        if state_check_result in {"applied", "not_applied"} and attempt.get(
            "outcome"
        ) != "completed":
            return {"status": "blocked", "reason": "state_check_not_completed"}
    unresolved_unknowns = []
    applied_unknowns = []
    for previous in attempts:
        if (
            previous.get("side_effect") is not True
            or previous.get("outcome") != "unknown"
        ):
            continue
        checks = [
            item
            for item in attempts
            if item.get("state_check_for") == previous.get("attempt_ref")
            and item.get("outcome") == "completed"
            and isinstance(item.get("state_check_result"), str)
            and item.get("state_check_result") in {"applied", "not_applied"}
        ]
        if not checks:
            unresolved_unknowns.append(previous.get("attempt_ref"))
        elif checks[0].get("state_check_result") == "applied":
            applied_unknowns.append(previous.get("attempt_ref"))
    if is_side_effect and applied_unknowns:
        return {
            "status": "blocked",
            "reason": "previous_side_effect_already_applied",
            "state_check_complete": True,
            "retryable": False,
        }
    if is_side_effect and unresolved_unknowns:
        return {
            "status": "blocked",
            "reason": "state_check_required",
            "unresolved_attempt_refs": unresolved_unknowns,
            "state_check_complete": False,
            "retryable": False,
        }
    consumed = sum(1 for item in attempts if item.get("side_effect") is True)
    next_count = consumed + (1 if attempt.get("side_effect") else 0)
    if next_count > charter.get("side_effect_maximum", 0) and attempt.get(
        "side_effect"
    ):
        return {"status": "blocked", "reason": "side_effect_limit_reached"}
    state_check_complete = (
        state_check_for is not None
        and attempt.get("outcome") == "completed"
        and state_check_result in {"applied", "not_applied"}
    )
    if state_check_for is not None:
        retryable = state_check_complete and state_check_result == "not_applied"
    elif outcome == "unknown":
        retryable = not is_side_effect
    elif attempt.get("outcome") == "failed":
        retryable = not is_side_effect or next_count < charter.get(
            "side_effect_maximum", 0
        )
    else:
        retryable = False
    return {
        "status": "recorded",
        "attempts": [*attempts, attempt],
        "side_effect_consumed": bool(attempt.get("side_effect")),
        "side_effect_count": next_count,
        "operation_outcome": {
            "completed": "succeeded",
            "failed": "failed",
            "unknown": "unknown",
        }[outcome],
        "state_check_complete": state_check_complete,
        "state_check_result": state_check_result,
        "resolved_attempt_ref": state_check_for,
        "resolved_attempt_outcome": (
            {"applied": "succeeded", "not_applied": "failed"}.get(
                state_check_result
            )
            if state_check_complete
            else None
        ),
        "retryable": retryable,
        "retry_without_state_check": retryable,
    }
