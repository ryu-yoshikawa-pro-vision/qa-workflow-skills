"""Standalone deterministic defect-candidate, external Issue operation and fix-verification checks.

Trust boundary: every input is untrusted data. The helpers never call an external
Issue service and never create an approval. They decide whether a candidate is
ready for hand-off, whether a proposed external operation may be attempted, and
whether an execution owner's result may be treated as fix confirmation. The
caller performs the provider call and passes the observed outcome back in.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from typing import Any

SOURCE_KINDS = {"FAIL", "Observation", "Finding"}
CAUSE_STATUSES = {"confirmed", "hypothesis", "unknown"}
TARGET_KINDS = {"build", "source_revision"}
OPERATIONS = {"create", "comment", "update", "link", "close", "reopen"}
DEDUPE_OPERATIONS = {"create", "comment"}
CONDITIONAL_OPERATIONS = {"update", "link", "close", "reopen"}
CLEANUP_CLOSED = {"成功", "対象なし", "意図的に残した状態"}
OWNER_SKILLS = {
    "test-execution",
    "e2e-test-execution",
    "e2e-test-result-analysis",
    "testware-execution",
    "exploratory-testing",
    "adversarial-review",
    "usability-inspection",
    "wcag-conformance-evaluation",
}
APPROVAL_SOURCE = "trusted_approval_service"
MAX_INPUT_BYTES = 2 * 1024 * 1024
_SECRET = re.compile(
    r"(?i)(?:password|passwd|(?:access[_-]?|auth[_-]?|refresh[_-]?)?token|client[_-]?secret|api[_-]?key|cookie|storage[_-]?state|authorization)\s*[:=]\s*['\"]?(?:bearer\s+)?[A-Za-z0-9_./+=-]{8,}"
)
_SPACE = re.compile(r"\s+")


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _strings(value: Any):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _strings(item)


def _instant(value: Any) -> datetime | None:
    if not _text(value):
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def symptom_key(symptom: str) -> str:
    """Normalize whitespace and case only; no semantic merging of symptoms."""
    return _SPACE.sub(" ", symptom).strip().casefold()


def candidate_ref(candidate: dict[str, Any]) -> str:
    """Deterministic identity: same source run/result/attempt, scope and symptom."""
    return (
        "DEFC-"
        + _digest(
            {
                "owner_skill": candidate.get("owner_skill"),
                "run_ref": candidate.get("run_ref"),
                "result_ref": candidate.get("result_ref"),
                "attempt_ref": candidate.get("attempt_ref"),
                "scope_ref": candidate.get("scope_ref"),
                "symptom_key": symptom_key(str(candidate.get("symptom", ""))),
            }
        )[:40]
    )


def operation_id(
    cand_ref: str,
    operation: str,
    issue_ref: str | None,
    expected_revision: str | None,
    target_ref: str | None,
) -> str:
    """Stable identity so a re-accepted request is never executed a second time."""
    return (
        "DEFOP-"
        + _digest([cand_ref, operation, issue_ref, expected_revision, target_ref])[:40]
    )


def assess_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    """Classify a FAIL / Observation / Finding. Never registers a formal defect."""
    issues: list[str] = []
    if not isinstance(candidate, dict):
        return {"status": "blocked", "issues": ["candidate_must_be_object"]}
    if candidate.get("source_kind") not in SOURCE_KINDS:
        issues.append("invalid_source_kind")
    if candidate.get("owner_skill") not in OWNER_SKILLS:
        issues.append("unknown_execution_owner")
    for field in ("run_ref", "result_ref", "scope_ref", "environment_ref", "symptom"):
        if not _text(candidate.get(field)):
            issues.append(f"missing_field:{field}")
    target = candidate.get("target")
    if (
        not isinstance(target, dict)
        or target.get("kind") not in TARGET_KINDS
        or not _text(target.get("ref"))
    ):
        issues.append("target_build_or_source_revision_required")
    if any(_SECRET.search(item) for item in _strings(candidate)):
        issues.append("secret_value_detected")
    if issues:
        return {"status": "blocked", "issues": sorted(set(issues))}

    reasons: list[str] = []
    return_to: dict[str, str] = {}
    cause = candidate.get("cause") if isinstance(candidate.get("cause"), dict) else {}
    expected = (
        candidate.get("expected_result")
        if isinstance(candidate.get("expected_result"), dict)
        else {}
    )
    evidence = candidate.get("evidence")
    if candidate.get("result_finalized") is not True:
        reasons.append("source_result_not_finalized")
        return_to["owner"] = candidate["owner_skill"]
    if cause.get("status") not in CAUSE_STATUSES:
        reasons.append("cause_status_invalid")
        return_to["owner"] = candidate["owner_skill"]
    elif cause["status"] != "confirmed":
        reasons.append("cause_unconfirmed")
        return_to["owner"] = candidate["owner_skill"]
    if not _text(expected.get("basis_ref")) or not _text(
        expected.get("basis_revision")
    ):
        reasons.append("expected_result_basis_missing")
        return_to["spec"] = "spec-analysis"
    if (
        not isinstance(evidence, list)
        or not evidence
        or any(
            not isinstance(item, dict) or not _text(item.get("ref"))
            for item in evidence
        )
    ):
        reasons.append("evidence_missing")
        return_to["owner"] = candidate["owner_skill"]
    ready = not reasons
    return {
        "status": "ready" if ready else "returned",
        "candidate_ref": candidate_ref(candidate),
        "candidate_state": "ready_for_external_handoff"
        if ready
        else (
            "needs_spec_basis" if set(return_to) == {"spec"} else "needs_owner_analysis"
        ),
        "reasons": reasons,
        "return_to": return_to,
        "symptom_key": symptom_key(candidate["symptom"]),
        "automatic_registration": False,
        "formal_defect": False,
    }


def match_external_issues(
    candidate: dict[str, Any], search: dict[str, Any]
) -> dict[str, Any]:
    """Combine own-run/symptom/scope keys with an external search. Never asserts identity."""
    ref = candidate_ref(candidate)
    key = symptom_key(str(candidate.get("symptom", "")))
    if (
        not isinstance(search, dict)
        or search.get("complete") is not True
        or search.get("permission_ok") is not True
        or not _text(search.get("service_revision"))
        or not _text(search.get("retrieved_at"))
    ):
        return {
            "candidate_ref": ref,
            "duplicate_check": "incomplete",
            "decision": "incomplete",
            "matches": [],
            "reasons": ["search_incomplete_or_unauthorized_or_unversioned"],
        }
    matches = []
    for item in search.get("issues", []):
        if not isinstance(item, dict) or not _text(item.get("issue_ref")):
            continue
        if item.get("candidate_ref") == ref:
            strength = "linked_exact"
        elif (
            item.get("run_ref") == candidate.get("run_ref")
            and item.get("symptom_key") == key
        ):
            strength = "same_run_and_symptom"
        elif (
            item.get("scope_ref") == candidate.get("scope_ref")
            and item.get("symptom_key") == key
        ):
            strength = "same_symptom_scope"
        elif item.get("scope_ref") == candidate.get("scope_ref"):
            strength = "related"
        else:
            continue
        matches.append(
            {
                "issue_ref": item["issue_ref"],
                "revision": item.get("revision"),
                "strength": strength,
            }
        )
    return {
        "candidate_ref": ref,
        "duplicate_check": "complete",
        "decision": "human_confirmation_required" if matches else "no_match",
        "matches": sorted(matches, key=lambda m: (m["strength"], m["issue_ref"])),
        "service_revision": search["service_revision"],
        "retrieved_at": search["retrieved_at"],
        "reasons": [],
    }


def verify_approval(
    approval: Any, binding: dict[str, Any], now: str | None
) -> list[str]:
    """Return rejection reasons. Text claims are never authorization evidence."""
    if not isinstance(approval, dict):
        return ["approval_missing"]
    problems: list[str] = []
    if approval.get("source") != APPROVAL_SOURCE:
        problems.append("approval_not_from_trusted_service")
    if approval.get("authentication_verified") is not True:
        problems.append("principal_not_authenticated")
    for field in ("principal", "role", "policy_revision", "authenticated_by"):
        if not _text(approval.get(field)):
            problems.append(f"approval_missing:{field}")
    if approval.get("revoked") is True:
        problems.append("approval_revoked")
    issued, expires, current = (
        _instant(approval.get("issued_at")),
        _instant(approval.get("expires_at")),
        _instant(now),
    )
    if issued is None or expires is None or current is None:
        problems.append("approval_validity_period_unverifiable")
    elif not issued <= current < expires:
        problems.append("approval_expired_or_not_yet_valid")
    for field, expected in binding.items():
        if expected is not None and approval.get(field) != expected:
            problems.append(f"approval_binding_mismatch:{field}")
    return sorted(set(problems))


def plan_external_operation(request: dict[str, Any]) -> dict[str, Any]:
    """Decide whether one external Issue operation may be attempted now."""
    operation = request.get("operation")
    candidate = (
        request.get("candidate") if isinstance(request.get("candidate"), dict) else {}
    )
    issue = request.get("issue") if isinstance(request.get("issue"), dict) else None
    service = request.get("service") if isinstance(request.get("service"), dict) else {}
    if operation not in OPERATIONS:
        return {"decision": "blocked", "reasons": ["unsupported_operation"]}
    cand_ref = candidate.get("candidate_ref")
    if not _text(cand_ref) or not _text(candidate.get("target_ref")):
        return {"decision": "blocked", "reasons": ["candidate_identity_required"]}
    needs_issue = operation != "create"
    if needs_issue and (issue is None or not _text(issue.get("issue_ref"))):
        return {"decision": "blocked", "reasons": ["issue_ref_required"]}
    op_id = operation_id(
        cand_ref,
        operation,
        issue.get("issue_ref") if issue else None,
        issue.get("revision") if issue else None,
        candidate["target_ref"],
    )
    base = {
        "operation": operation,
        "operation_id": op_id,
        "auto_retry_allowed": False,
        "requires_readback": True,
    }

    for prior in request.get("prior_operations", []) or []:
        if isinstance(prior, dict) and prior.get("operation_id") == op_id:
            if prior.get("status") == "applied":
                return {
                    **base,
                    "decision": "already_applied",
                    "reasons": ["operation_already_applied"],
                }
            if (
                prior.get("status") == "failed"
                and prior.get("side_effect") == "none_confirmed"
            ):
                continue
            return {
                **base,
                "decision": "reconcile_first",
                "reasons": ["prior_operation_state_unknown_or_started"],
            }

    if service.get("write_permission") is not True:
        return {
            **base,
            "decision": "read_only",
            "reasons": ["external_write_permission_absent"],
            "external_update_performed": False,
        }
    if candidate.get("candidate_state") != "ready_for_external_handoff":
        return {
            **base,
            "decision": "blocked",
            "reasons": ["candidate_not_ready_cause_or_basis_unconfirmed"],
        }

    reasons: list[str] = []
    binding = {
        "operation": operation,
        "candidate_ref": cand_ref,
        "scope_ref": candidate.get("scope_ref"),
        "artifact_revision": candidate.get("artifact_revision"),
        "target_ref": candidate["target_ref"],
        "service_ref": service.get("service_ref"),
        "issue_ref": issue.get("issue_ref") if issue else None,
        "issue_revision": issue.get("revision") if issue else None,
    }
    if not _text(candidate.get("artifact_revision")) or not _text(
        service.get("service_ref")
    ):
        reasons.append("artifact_revision_and_service_ref_required")
    reasons += verify_approval(request.get("approval"), binding, request.get("now"))

    auto_retry = True
    if operation == "create":
        check = (
            request.get("duplicate_check")
            if isinstance(request.get("duplicate_check"), dict)
            else {}
        )
        if check.get("duplicate_check") != "complete":
            reasons.append("duplicate_check_incomplete")
        elif check.get("decision") != "no_match":
            return {
                **base,
                "decision": "reconfirm",
                "reasons": ["possible_duplicate_requires_human_confirmation"],
            }
    if operation in DEDUPE_OPERATIONS and service.get("atomic_dedupe") is not True:
        auto_retry = False
    if operation in CONDITIONAL_OPERATIONS:
        if service.get("conditional_update") is not True:
            reasons.append("conditional_update_unavailable")
        if issue and issue.get("current_revision") != issue.get("revision"):
            reasons.append("stale_issue_read_reread_required")
        if issue and not _text(issue.get("revision")):
            reasons.append("expected_issue_revision_required")
    if operation == "close":
        fix = (
            request.get("fix_verification")
            if isinstance(request.get("fix_verification"), dict)
            else {}
        )
        if not (
            fix.get("status") == "fix_confirmed"
            and fix.get("verified_target_ref") == candidate.get("fix_target_ref")
            and _text(fix.get("verified_target_ref"))
            and fix.get("verified_target_ref") != candidate["target_ref"]
            and fix.get("result_finalized") is True
            and fix.get("cleanup_status") in CLEANUP_CLOSED
        ):
            reasons.append("close_without_verified_fix_on_fix_target")
    if operation == "reopen":
        fix = (
            request.get("fix_verification")
            if isinstance(request.get("fix_verification"), dict)
            else {}
        )
        if fix.get("status") != "fix_not_confirmed":
            reasons.append("reopen_requires_owner_confirmed_failure")
    if reasons:
        return {**base, "decision": "blocked", "reasons": sorted(set(reasons))}
    return {
        **base,
        "auto_retry_allowed": auto_retry,
        "decision": "allow",
        "reasons": [],
        "single_attempt_only": not auto_retry,
    }


def record_operation_outcome(
    plan: dict[str, Any], call: dict[str, Any], readback: dict[str, Any] | None
) -> dict[str, Any]:
    """Classify an attempted provider call. Success needs an independent readback."""
    if plan.get("decision") != "allow":
        return {
            "operation_id": plan.get("operation_id"),
            "status": "not_attempted",
            "external_update_performed": False,
        }
    status = call.get("status") if isinstance(call, dict) else None
    if status == "failure" and call.get("error") == "conflict":
        outcome = "conflict"
    elif status == "failure" and call.get("side_effect") == "none_confirmed":
        outcome = "failed"
    elif status == "success":
        ok = (
            isinstance(readback, dict)
            and _text(readback.get("revision"))
            and readback.get("revision") == call.get("returned_revision")
            and readback.get("issue_ref") == call.get("issue_ref")
            and readback.get("matches_request") is True
        )
        outcome = "applied" if ok else "unknown"
    else:
        outcome = "unknown"
    return {
        "operation_id": plan["operation_id"],
        "status": outcome,
        "external_update_performed": outcome == "applied",
        "external_issue": {
            "issue_ref": call.get("issue_ref"),
            "revision": (readback or {}).get("revision"),
            "retrieved_at": (readback or {}).get("retrieved_at"),
        }
        if outcome == "applied"
        else None,
        "auto_retry_allowed": False,
        "next": "reconcile_with_external_service" if outcome == "unknown" else None,
    }


def request_fix_verification(
    candidate: dict[str, Any], notice: dict[str, Any]
) -> dict[str, Any]:
    """Return a re-execution request to the original owner or refuse it."""
    reasons: list[str] = []
    observed = candidate.get("target_ref")
    fix_target = notice.get("fix_target_ref") if isinstance(notice, dict) else None
    if candidate.get("owner_skill") not in OWNER_SKILLS:
        reasons.append("original_execution_owner_unknown")
    if not _text(fix_target):
        reasons.append("fix_target_not_identified")
    elif fix_target == observed:
        reasons.append("fix_target_same_as_observed_target")
    changes = notice.get("change_refs") if isinstance(notice, dict) else None
    if (
        not isinstance(changes, list)
        or not changes
        or notice.get("change_unknown") is True
    ):
        reasons.append("unknown_change_not_a_fix_claim")
    targets = candidate.get("verification_targets")
    if (
        not isinstance(targets, list)
        or not targets
        or any(
            not isinstance(t, dict)
            or not _text(t.get("ref"))
            or not _text(t.get("revision"))
            or t.get("current") is not True
            for t in targets
        )
    ):
        reasons.append("verification_testware_not_current")
    if reasons:
        return {
            "status": "blocked",
            "reasons": sorted(set(reasons)),
            "rerun_allowed": False,
        }
    ref = operation_id(
        candidate["candidate_ref"],
        "fix_verification",
        notice.get("issue_ref"),
        notice.get("issue_revision"),
        fix_target,
    )
    return {
        "status": "request_ready",
        "request_ref": ref,
        "send_to": candidate["owner_skill"],
        "observed_target_ref": observed,
        "fix_target_ref": fix_target,
        "verification_targets": targets,
        "same_acceptance_basis": True,
        "regression_selection_owner": "regression-testing",
        "performed_by": "original_execution_owner",
        "notice_is_confirmation": False,
    }


def evaluate_fix_result(
    request: dict[str, Any], result: dict[str, Any]
) -> dict[str, Any]:
    """Judge an owner result for a request; the owner's raw result is not rescored."""
    if request.get("status") != "request_ready":
        return {"status": "rejected", "reasons": ["request_not_ready"]}
    if not isinstance(result, dict):
        return {"status": "rejected", "reasons": ["result_missing"]}
    reasons = []
    if result.get("request_ref") != request["request_ref"]:
        reasons.append("request_ref_mismatch")
    if result.get("owner_skill") != request["send_to"]:
        reasons.append("wrong_owner")
    if result.get("target_ref") != request["fix_target_ref"]:
        reasons.append("target_mismatch_old_or_other_build")
    if reasons:
        return {"status": "rejected", "reasons": reasons, "fix_confirmed": False}
    if (
        result.get("actual_start_confirmed") is not True
        or result.get("result_finalized") is not True
        or result.get("cleanup_status") not in CLEANUP_CLOSED
    ):
        return {
            "status": "pending",
            "reasons": ["start_result_or_cleanup_unconfirmed"],
            "fix_confirmed": False,
        }
    state = result.get("state")
    if state == "PASS":
        return {
            "status": "fix_confirmed",
            "verified_target_ref": request["fix_target_ref"],
            "fix_confirmed": True,
            "result_finalized": True,
            "cleanup_status": result["cleanup_status"],
        }
    if state == "FAIL":
        return {
            "status": "fix_not_confirmed",
            "verified_target_ref": request["fix_target_ref"],
            "fix_confirmed": False,
            "result_finalized": True,
            "cleanup_status": result["cleanup_status"],
        }
    return {
        "status": "pending",
        "reasons": ["owner_state_not_decisive"],
        "fix_confirmed": False,
    }


def closure_status(record: dict[str, Any]) -> dict[str, Any]:
    """A candidate is closed only with a recorded disposition and current tracking."""
    open_items: list[str] = []
    submission = (
        record.get("submission") if isinstance(record.get("submission"), dict) else {}
    )
    state = submission.get("status")
    if state == "withheld":
        if not _text(submission.get("withheld_reason")) or not _text(
            submission.get("decided_by")
        ):
            open_items.append("withheld_reason_and_decider_required")
    elif state == "registered":
        issue = (
            submission.get("external_issue")
            if isinstance(submission.get("external_issue"), dict)
            else {}
        )
        if (
            not _text(issue.get("issue_ref"))
            or not _text(issue.get("revision"))
            or not _text(issue.get("retrieved_at"))
        ):
            open_items.append("external_issue_ref_revision_retrieved_at_required")
        if record.get("external_confirmation") != "current":
            open_items.append("external_issue_state_not_current")
        fix = (
            record.get("fix_verification")
            if isinstance(record.get("fix_verification"), dict)
            else {}
        )
        if fix.get("status") != "fix_confirmed":
            open_items.append("fix_not_confirmed_by_execution_owner")
    else:
        open_items.append("submission_disposition_missing")
    return {"closed": not open_items, "open_items": open_items}


def _load(text: str) -> Any:
    if len(text.encode("utf-8", "replace")) > MAX_INPUT_BYTES:
        raise ValueError("input_too_large")

    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        keys = [key for key, _ in items]
        if len(keys) != len(set(keys)):
            raise ValueError("duplicate_json_key")
        return dict(items)

    return json.loads(text, object_pairs_hook=pairs)


COMMANDS = {
    "assess-candidate": lambda d: assess_candidate(d),
    "match-issues": lambda d: match_external_issues(d["candidate"], d["search"]),
    "plan-operation": lambda d: plan_external_operation(d),
    "record-outcome": lambda d: record_operation_outcome(
        d["plan"], d["call"], d.get("readback")
    ),
    "fix-request": lambda d: request_fix_verification(d["candidate"], d["notice"]),
    "fix-result": lambda d: evaluate_fix_result(d["request"], d["result"]),
    "closure": lambda d: closure_status(d),
}


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1 or args[0] not in COMMANDS:
        print(
            json.dumps(
                {
                    "status": "blocked",
                    "reason": "usage: defect_runtime.py <"
                    + "|".join(COMMANDS)
                    + "> < input.json",
                }
            )
        )
        return 2
    try:
        data = _load(sys.stdin.buffer.read().decode("utf-8"))
        if not isinstance(data, dict):
            raise ValueError("input_must_be_object")
        result = COMMANDS[args[0]](data)
    except (ValueError, KeyError, TypeError) as exc:
        print(
            json.dumps(
                {"status": "blocked", "reason": f"invalid_input:{type(exc).__name__}"},
                ensure_ascii=True,
            )
        )
        return 2
    print(json.dumps(result, ensure_ascii=True, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
