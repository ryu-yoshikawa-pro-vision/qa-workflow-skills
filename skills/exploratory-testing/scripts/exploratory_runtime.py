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


INVESTIGATION_ORIGIN_KEYS = (
    "symptom_ref",
    "hypothesis_ref",
    "unresolved_finding_ref",
    "symptom",
    "hypothesis",
)


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
    if not isinstance(charter, dict):
        return {
            "valid": False,
            "missing_fields": [],
            "issues": ["charter_must_be_object"],
        }
    missing = sorted(
        field
        for field in CHARTER_FIELDS
        if field not in charter or charter[field] is None or charter[field] == ""
    )
    issues: list[str] = []
    if not isinstance(mode, str) or mode not in MODES:
        issues.append("invalid_mode")
    if mode == "investigation" and not any(
        isinstance(charter.get(key), str) and charter[key].strip()
        for key in INVESTIGATION_ORIGIN_KEYS
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
    allowed_operations = charter.get("allowed_operations")
    if not isinstance(allowed_operations, list):
        allowed_operations = []
    if not isinstance(side_effect_operations, list) or any(
        item not in allowed_operations for item in side_effect_operations
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
    consumed = prior_side_effect_attempts + (1 if uncertain_previous_attempt else 0)
    next_attempt = consumed + 1
    if operation in charter.get(
        "side_effect_operations", []
    ) and next_attempt > charter.get("side_effect_maximum", 0):
        return {
            "status": "blocked",
            "reason": "side_effect_limit_reached",
            "consumed_attempts": consumed,
        }
    return {
        "status": "allowed",
        "origin": target_origin,
        "operation": operation,
        "side_effect_attempt_number": next_attempt
        if operation in charter.get("side_effect_operations", [])
        else None,
    }


def _is_ref(value: Any) -> bool:
    return isinstance(value, str) and bool(value)


def validate_session(session: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(session, dict):
        return {"valid": False, "issues": ["session_must_be_object"]}
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
    if (
        not isinstance(session.get("state"), str)
        or session["state"] not in SESSION_STATES
    ):
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
    # A ref must be a non-empty string; arrays / objects are an issue, not a crash.
    if (
        len(observation_refs) != len(observations)
        or not all(_is_ref(ref) for ref in observation_refs)
        or len(observation_refs) != len(set(observation_refs))
    ):
        issues.append("observation_refs_missing_or_duplicate")
    if (
        len(finding_refs) != len(findings)
        or not all(_is_ref(ref) for ref in finding_refs)
        or len(finding_refs) != len(set(finding_refs))
    ):
        issues.append("finding_refs_missing_or_duplicate")
    obs_set = {ref for ref in observation_refs if _is_ref(ref)}
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
        if (
            not isinstance(refs, list)
            or not refs
            or not all(_is_ref(ref) for ref in refs)
            or not set(refs) <= obs_set
        ):
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
    if not isinstance(cleanup, dict):
        cleanup = {}
    if not _is_ref(cleanup.get("status")) or cleanup["status"] not in CLEANUP_STATES:
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
    if not attempt.get("attempt_ref") or attempt["attempt_ref"] in refs:
        return {"status": "blocked", "reason": "attempt_ref_missing_or_duplicate"}
    if attempt.get("outcome") not in {"completed", "failed", "unknown"}:
        return {"status": "blocked", "reason": "invalid_attempt_outcome"}
    operation = attempt.get("operation")
    is_side_effect = operation in charter.get("side_effect_operations", [])
    if not operation or attempt.get("side_effect") is not is_side_effect:
        return {"status": "blocked", "reason": "side_effect_mapping_mismatch"}
    consumed = sum(1 for item in attempts if item.get("side_effect") is True)
    next_count = consumed + (1 if attempt.get("side_effect") else 0)
    if next_count > charter.get("side_effect_maximum", 0) and attempt.get(
        "side_effect"
    ):
        return {"status": "blocked", "reason": "side_effect_limit_reached"}
    return {
        "status": "recorded",
        "attempts": [*attempts, attempt],
        "side_effect_consumed": bool(attempt.get("side_effect")),
        "side_effect_count": next_count,
        "retry_without_state_check": attempt.get("outcome") == "unknown",
    }


def resolve_direct_start(request: dict[str, Any]) -> dict[str, Any]:
    """Resolve a direct entry request to a mode or to the owner that must handle it.

    No formal TC, TR or E2E testware is required to start. Only a Charter
    (exploration) or an owner-unknown symptom / hypothesis / unresolved Finding
    (investigation) is needed. The word "investigate" alone never selects
    investigation: work that an existing owner can handle is routed to that owner.
    """
    if request.get("current_ui_collection") is True:
        return _route("test-target-inspection", "current_ui_fact_collection")
    if request.get("e2e_failure_ref"):
        return _route("e2e-test-result-analysis", "known_e2e_failure_has_owner")
    if request.get("known_tc_ref") and not (
        request.get("symptom_ref")
        or request.get("hypothesis_ref")
        or request.get("unresolved_finding_ref")
    ):
        return _route("test-execution", "known_tc_faithful_execution")
    charter = request.get("charter")
    start_refs = [
        key
        for key in ("symptom_ref", "hypothesis_ref", "unresolved_finding_ref")
        if request.get(key)
    ]
    if start_refs:
        known_owner = request.get("known_owner")
        if known_owner:
            return _route(str(known_owner), "symptom_owner_already_known")
        if request.get("owner_unknown") is not True:
            return {"status": "blocked", "reason": "owner_resolution_unconfirmed"}
        mode = "investigation"
        start_ref = {key: request[key] for key in start_refs}
    elif isinstance(charter, dict) and charter:
        mode = "exploration"
        start_ref = {}
    else:
        return {"status": "blocked", "reason": "charter_or_unowned_symptom_required"}
    if not isinstance(charter, dict) or not charter:
        return {
            "status": "blocked",
            "reason": "charter_required",
            "mode": mode,
            "start_ref": start_ref,
        }
    # The start refs are the investigation origin. They are returned inside
    # "charter" so the saved Session, validation and can_resume() keep the same origin.
    checked = {**charter, **start_ref}
    validation = validate_charter(mode, checked)
    if not validation["valid"]:
        return {
            "status": "blocked",
            "reason": "charter_invalid",
            "mode": mode,
            "missing_fields": validation["missing_fields"],
            "issues": validation["issues"],
        }
    return {
        "status": "start",
        "mode": mode,
        "start_ref": start_ref,
        "charter": checked,
        "required_prerequisite_skills": [],
        "formal_tc_required": False,
    }


def _route(owner: str, reason: str) -> dict[str, Any]:
    return {"status": "route", "owner_skill": owner, "reason": reason}


FOLLOW_UP_ACTIONS = {
    "question-analysis": None,
    "test-analysis": None,
    "test-case-design": None,
    "test-target-inspection": None,
    "e2e-test-result-analysis": None,
    "qa-knowledge": "triage",
    "defect-management": "defect_candidate_review",
}


def source_revision_refs(session: dict[str, Any]) -> list[dict[str, Any]]:
    """Return each Charter source as {"ref", "revision"} for re-reading by the owner.

    A Charter source is a ref string or an object with "ref" and "revision".
    A string ref takes its revision from the Session's optional
    "source_revisions" map. A source without a revision keeps revision None; the
    revision is never guessed or taken from the Session revision.
    """
    revisions = session.get("source_revisions")
    revisions = revisions if isinstance(revisions, dict) else {}
    declared = session["charter"].get("source_refs", [])
    if not isinstance(declared, list):
        declared = [declared]
    sources = []
    for item in declared:
        if isinstance(item, dict):
            ref, revision = item.get("ref"), item.get("revision")
        elif isinstance(item, str):
            ref, revision = item, revisions.get(item)
        else:
            ref, revision = None, None
        if not isinstance(ref, str) or not ref:
            ref = json.dumps(item, ensure_ascii=False, sort_keys=True)
            revision = None
        if not isinstance(revision, str) or not revision:
            revision = None
        sources.append({"ref": ref, "revision": revision})
    return sources


def build_follow_up_handoff(
    session: dict[str, Any], finding_ref: str, *, session_revision: str | None
) -> dict[str, Any]:
    """Build a reference-only hand-off of one Finding to its follow-up owner.

    The hand-off carries IDs and the revision needed to re-read the Session, not
    the Observation text, spec or run results. Each source is a ref plus its own
    revision, separate from the Session revision. It never promotes the Finding to a
    formal defect or a knowledge entry; the receiving owner decides.
    """
    if not session_revision:
        return {"status": "blocked", "reason": "session_revision_required"}
    validation = validate_session(session)
    if not validation["valid"]:
        return {
            "status": "blocked",
            "reason": "session_invalid",
            "issues": validation["issues"],
        }
    finding = next(
        (
            item
            for item in session.get("findings", [])
            if isinstance(item, dict) and item.get("finding_ref") == finding_ref
        ),
        None,
    )
    if finding is None:
        return {"status": "blocked", "reason": "finding_not_in_session"}
    owner = finding.get("recommended_routing")
    if owner not in FOLLOW_UP_ACTIONS:
        return {"status": "blocked", "reason": "unknown_follow_up_owner"}
    session_unresolved = session.get("unresolved", [])
    finding_unresolved = finding.get("unresolved", [])
    if not isinstance(session_unresolved, list) or not isinstance(
        finding_unresolved, list
    ):
        return {"status": "blocked", "reason": "unresolved_must_be_list"}
    unresolved = [item for item in (*session_unresolved, *finding_unresolved) if item]
    sources = source_revision_refs(session)
    unresolved_sources = [item["ref"] for item in sources if item["revision"] is None]
    if owner == "defect-management" and unresolved:
        return {
            "status": "blocked",
            "reason": "unresolved_finding_not_defect_candidate",
            "next": "owner_resolution_or_investigation",
        }
    if owner == "defect-management" and unresolved_sources:
        return {
            "status": "blocked",
            "reason": "source_revision_unresolved",
            "unresolved": unresolved_sources,
            "next": "record_source_revisions",
        }
    unresolved.extend(f"source_revision_unresolved:{ref}" for ref in unresolved_sources)
    if session.get("state") in {"ブロック中", "部分完了（ブロック中あり）"}:
        state = "blocked"
        resume: dict[str, Any] | None = {
            "owner_skill": "exploratory-testing",
            "action": "resume_session",
            "condition": "same charter, scope, permitted range and environment",
        }
    elif unresolved_sources:
        state = "blocked"
        resume = {
            "owner_skill": "exploratory-testing",
            "action": "record_source_revisions",
            "condition": "re-read each source and record its revision",
        }
    elif unresolved:
        state = "current"
        resume = {
            "owner_skill": "exploratory-testing",
            "action": "owner_resolution_or_investigation",
        }
    else:
        state = "current"
        resume = None
    return {
        "status": "ready",
        "handoff": {
            "kind": "exploratory_finding_reference",
            "owner_skill": "exploratory-testing",
            "artifact_ref": session.get("session_ref"),
            "content_hash": session_revision,
            "state": state,
            "validation": {
                "runtime": "exploratory-testing/scripts/exploratory_runtime.py:validate_session",
                "valid": True,
                "issues": [],
                "result_ref": None,
            },
            "resume": resume,
            "required_approval": {
                "required": owner == "defect-management",
                "approval_ref": None,
                "decided_by": "receiving_owner",
            },
            "follow_up_owner_skill": owner,
            "target_action": FOLLOW_UP_ACTIONS[owner],
            "session_ref": session.get("session_ref"),
            "session_revision": session_revision,
            "charter_snapshot_identity": session.get("charter_snapshot_identity"),
            "finding_ref": finding_ref,
            "source_observation_refs": list(finding["source_observation_refs"]),
            "evidence_refs": list(finding["evidence_refs"]),
            "source_refs": sources,
            "follow_up_reason": finding["follow_up_reason"],
            "unresolved": unresolved,
            "promotion": "not_promoted",
            "formal_defect": False,
            "knowledge_entry_created": False,
        },
    }
