"""Standalone deterministic QA-activity evaluation and improvement-lifecycle checks.

The helper evaluates already-measured values against their sources and conditions.
It never rewrites a raw result, never builds a composite score, never treats a
Knowledge registration as an implemented improvement and never decides release
or project closure.
"""

from __future__ import annotations

import json
import math
import sys
from datetime import datetime, timezone
from typing import Any

AXES = ("traceability", "quality", "efficiency", "process", "reusability")
DIRECTIONS = {"higher_is_better", "lower_is_better"}
APPROVAL_SOURCE = "trusted_approval_service"
OWNER_BY_CHANGE_KIND = {
    "plan": {"test-management"},
    "architecture": {"test-architecture-design"},
    "design": {
        "test-requirement-design",
        "test-condition-design",
        "test-case-design",
    },
}
IMPROVEMENT_STATES = (
    "proposed",
    "adopted",
    "handed_off",
    "implemented",
    "measured_effective",
    "measured_no_effect",
    "measured_worsened",
    "not_comparable",
    "not_measurable",
    "rejected",
)
MAX_INPUT_BYTES = 4 * 1024 * 1024
_COMPARABLE_CONDITIONS = ("scope_ref", "environment_ref", "population_ref")


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _number(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _instant(value: Any) -> datetime | None:
    if not _text(value):
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def verify_inputs(
    recorded: list[dict[str, Any]], current: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    """Compare recorded input refs with a fresh read; raw sources are never edited."""
    stale: list[str] = []
    unverified: list[str] = []
    for item in recorded:
        ref = item.get("ref") if isinstance(item, dict) else None
        if not _text(ref) or not _text(item.get("revision")):
            unverified.append(str(ref))
            continue
        now = current.get(ref)
        if now is None:
            unverified.append(ref)
        elif now.get("revision") != item["revision"] or (
            item.get("content_hash") and now.get("content_hash") != item["content_hash"]
        ):
            stale.append(ref)
    status = "current" if not stale and not unverified else "stale_or_unverified"
    return {
        "status": status,
        "stale_refs": sorted(stale),
        "unverified_refs": sorted(unverified),
    }


def evaluate_metric(metric: dict[str, Any]) -> dict[str, Any]:
    """Classify one metric as measured / unmeasured / improved / worsened / not comparable."""
    metric_id = metric.get("metric_id") if isinstance(metric, dict) else None
    reasons: list[str] = []
    if not isinstance(metric, dict) or metric.get("axis") not in AXES:
        return {
            "metric_id": metric_id,
            "status": "invalid",
            "reasons": ["axis_not_one_of_five"],
        }
    if metric.get("direction") not in DIRECTIONS:
        reasons.append("direction_required")
    sources = metric.get("source_refs")
    value, numerator, denominator = (
        metric.get("value"),
        metric.get("numerator"),
        metric.get("denominator"),
    )
    measured = (
        _number(value)
        and isinstance(sources, list)
        and bool(sources)
        and all(
            isinstance(s, dict) and _text(s.get("ref")) and _text(s.get("revision"))
            for s in sources
        )
    )
    if measured and _number(denominator) and denominator > 0 and _number(numerator):
        if not math.isclose(value, numerator / denominator, rel_tol=1e-6, abs_tol=1e-9):
            reasons.append("value_does_not_match_numerator_over_denominator")
    if (
        measured
        and _number(numerator)
        and not (_number(denominator) and denominator > 0)
    ):
        measured = False
    if not measured:
        if not _text(metric.get("unmeasured_reason")):
            reasons.append("unmeasured_reason_required")
        return {
            "metric_id": metric_id,
            "axis": metric["axis"],
            "status": "invalid" if reasons else "unmeasured",
            "reasons": reasons or ["no_value_or_source_or_denominator"],
        }
    if reasons:
        return {
            "metric_id": metric_id,
            "axis": metric["axis"],
            "status": "invalid",
            "reasons": reasons,
        }
    previous = metric.get("previous")
    if previous is None:
        return {
            "metric_id": metric_id,
            "axis": metric["axis"],
            "status": "measured",
            "value": value,
            "reasons": [],
        }
    prior_conditions = (
        previous.get("conditions") if isinstance(previous, dict) else None
    )
    conditions = metric.get("conditions")
    comparable = (
        isinstance(previous, dict)
        and _number(previous.get("value"))
        and isinstance(conditions, dict)
        and isinstance(prior_conditions, dict)
        and previous.get("definition_version") == metric.get("definition_version")
        and previous.get("unit") == metric.get("unit")
        and all(
            _text(conditions.get(k)) and conditions.get(k) == prior_conditions.get(k)
            for k in _COMPARABLE_CONDITIONS
        )
        and _text(metric.get("definition_version"))
    )
    if not comparable:
        return {
            "metric_id": metric_id,
            "axis": metric["axis"],
            "status": "not_comparable",
            "value": value,
            "reasons": ["measurement_conditions_definition_or_unit_differ"],
        }
    delta = value - previous["value"]
    better = delta > 0 if metric["direction"] == "higher_is_better" else delta < 0
    status = (
        "unchanged"
        if math.isclose(delta, 0, abs_tol=1e-9)
        else ("improved" if better else "worsened")
    )
    return {
        "metric_id": metric_id,
        "axis": metric["axis"],
        "status": status,
        "value": value,
        "delta": delta,
        "reasons": [],
    }


def evaluate_axes(
    metrics: list[dict[str, Any]], claims: list[dict[str, Any]] | None = None
) -> dict[str, Any]:
    """Per-axis results with no composite score; reject claims the metrics do not support."""
    evaluated = [evaluate_metric(m) for m in metrics]
    axes: dict[str, dict[str, Any]] = {
        axis: {"status": "unmeasured", "metrics": []} for axis in AXES
    }
    for item in evaluated:
        if item.get("axis") in axes:
            axes[item["axis"]]["metrics"].append(item)
    for axis, entry in axes.items():
        statuses = {m["status"] for m in entry["metrics"]}
        if statuses & {
            "improved",
            "unchanged",
            "worsened",
            "measured",
            "not_comparable",
        }:
            entry["status"] = "measured"
        if "worsened" in statuses:
            entry["trend"] = "worsened"
        elif "improved" in statuses:
            entry["trend"] = "improved"
        elif statuses & {"unchanged", "measured"}:
            entry["trend"] = "no_change_or_baseline"
        elif "not_comparable" in statuses:
            entry["trend"] = "not_comparable"
        else:
            entry["trend"] = "unmeasured"
    rejected: list[dict[str, str]] = []
    for claim in claims or []:
        axis, assertion = claim.get("axis"), claim.get("assertion")
        entry = axes.get(axis)
        statuses = {m["status"] for m in entry["metrics"]} if entry else set()
        if entry is None:
            supported = False
        elif assertion == "improved":
            supported = entry["trend"] == "improved" and "worsened" not in statuses
        elif assertion == "worsened":
            supported = entry["trend"] == "worsened"
        elif assertion == "measured":
            supported = entry["status"] == "measured"
        else:
            supported = False
        if not supported:
            rejected.append(
                {
                    "axis": str(axis),
                    "assertion": str(assertion),
                    "reason": "claim_not_supported_by_axis_metrics",
                }
            )
    return {
        "metrics": evaluated,
        "axes": axes,
        "rejected_claims": rejected,
        "composite_score": None,
    }


def verify_approval(
    approval: Any, binding: dict[str, Any], now: str | None
) -> list[str]:
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


def advance_improvement(
    improvement: dict[str, Any], event: dict[str, Any], now: str | None = None
) -> dict[str, Any]:
    """Apply one lifecycle event. Skipping a step or using unverified evidence is refused."""
    state = improvement.get("state")
    kind = event.get("type")
    ref = improvement.get("improvement_ref")
    if state not in IMPROVEMENT_STATES or not _text(ref):
        return {
            "status": "blocked",
            "reasons": ["improvement_state_or_ref_invalid"],
            "improvement": improvement,
        }
    updated = dict(improvement)

    def refuse(*reasons: str) -> dict[str, Any]:
        return {
            "status": "blocked",
            "reasons": sorted(reasons),
            "improvement": improvement,
        }

    if kind == "knowledge_registered":
        updated["knowledge_candidate_ref"] = event.get("knowledge_ref")
        return {
            "status": "recorded",
            "note": "knowledge_registration_is_not_adoption_handoff_or_implementation",
            "improvement": updated,
        }
    if kind == "adopt":
        if state != "proposed":
            return refuse("adopt_requires_proposed_state")
        binding = {
            "operation": "adopt_improvement",
            "improvement_ref": ref,
            "artifact_revision": improvement.get("proposal_revision"),
            "scope_ref": improvement.get("scope_ref"),
        }
        problems = verify_approval(event.get("approval"), binding, now)
        if problems:
            return refuse(*problems)
        updated.update(
            state="adopted", adoption_ref=event["approval"].get("approval_ref")
        )
        return {"status": "advanced", "improvement": updated}
    if kind == "handoff":
        if state != "adopted":
            return refuse("handoff_requires_adopted_state")
        owners = OWNER_BY_CHANGE_KIND.get(improvement.get("change_kind"))
        if owners is None or event.get("owner_skill") not in owners:
            return refuse("owner_does_not_match_change_kind")
        if not (_text(event.get("request_ref")) and _text(event.get("base_revision"))):
            return refuse("request_ref_and_base_revision_required")
        updated.update(
            state="handed_off",
            owner_skill=event["owner_skill"],
            request_ref=event["request_ref"],
            base_revision=event["base_revision"],
        )
        return {"status": "advanced", "improvement": updated}
    if kind == "implement":
        if state != "handed_off":
            return refuse("implement_requires_handed_off_state")
        result = (
            event.get("owner_result")
            if isinstance(event.get("owner_result"), dict)
            else {}
        )
        if (
            result.get("request_ref") != improvement.get("request_ref")
            or result.get("owner_skill") != improvement.get("owner_skill")
            or result.get("status") != "applied"
            or not _text(result.get("new_revision"))
            or result.get("new_revision") == improvement.get("base_revision")
            or result.get("adoption_ref") != improvement.get("adoption_ref")
        ):
            return refuse("owner_did_not_record_applied_revision_for_this_adoption")
        updated.update(state="implemented", new_revision=result["new_revision"])
        return {"status": "advanced", "improvement": updated}
    if kind == "measure":
        if state != "implemented":
            return refuse("measure_requires_implemented_state")
        later = event.get("activity") if isinstance(event.get("activity"), dict) else {}
        if (
            later.get("applied_revision") != improvement.get("new_revision")
            or later.get("started_after_implementation") is not True
            or later.get("activity_ref") == improvement.get("baseline_activity_ref")
        ):
            return refuse(
                "measurement_must_come_from_a_later_activity_using_the_new_revision"
            )
        outcome = evaluate_metric(
            event.get("metric") if isinstance(event.get("metric"), dict) else {}
        )
        mapping = {
            "improved": "measured_effective",
            "unchanged": "measured_no_effect",
            "worsened": "measured_worsened",
            "not_comparable": "not_comparable",
            "unmeasured": "not_measurable",
        }
        if outcome["status"] not in mapping:
            return refuse("metric_not_evaluable")
        updated.update(state=mapping[outcome["status"]], effect_metric=outcome)
        return {"status": "advanced", "improvement": updated}
    if kind == "reject":
        if state not in {"proposed", "adopted"}:
            return refuse("reject_only_before_handoff")
        updated.update(state="rejected")
        return {"status": "advanced", "improvement": updated}
    return refuse("unknown_event")


def summarize_improvements(improvements: list[dict[str, Any]]) -> dict[str, Any]:
    """Only a measured, comparable effect counts as an achieved improvement."""
    counts = {state: 0 for state in IMPROVEMENT_STATES}
    for item in improvements:
        if item.get("state") in counts:
            counts[item["state"]] += 1
    return {
        "counts": counts,
        "achieved": counts["measured_effective"],
        "not_complete": sorted(
            str(i.get("improvement_ref"))
            for i in improvements
            if i.get("state") in {"proposed", "adopted", "handed_off", "implemented"}
        ),
        "not_counted_as_achieved": sorted(
            str(i.get("improvement_ref"))
            for i in improvements
            if i.get("state") != "measured_effective"
        ),
    }


def handoff_status(handoffs: list[dict[str, Any]], now: str | None) -> dict[str, Any]:
    """Archive / hand-over is closed only with an authenticated confirmation of each item."""
    open_items: list[dict[str, Any]] = []
    for item in handoffs:
        problems = []
        if not _text(item.get("item_ref")) or not _text(item.get("receiver")):
            problems.append("item_and_receiver_required")
        confirmation = item.get("confirmation")
        problems += verify_approval(
            confirmation,
            {
                "operation": "confirm_handoff",
                "artifact_revision": item.get("artifact_revision"),
                "item_ref": item.get("item_ref"),
            },
            now,
        )
        if problems:
            open_items.append(
                {"item_ref": item.get("item_ref"), "reasons": sorted(set(problems))}
            )
    return {"closed": bool(handoffs) and not open_items, "open_items": open_items}


def propagate_change(
    changed_ref: str, depends_on: dict[str, list[str]], current_refs: list[str]
) -> dict[str, Any]:
    """Only transitive dependents of the changed artifact need re-verification."""
    affected: set[str] = set()
    frontier = {changed_ref}
    while frontier:
        nxt = {
            ref
            for ref, deps in depends_on.items()
            if ref not in affected and ref != changed_ref and frontier & set(deps)
        }
        affected |= nxt
        frontier = nxt
    return {
        "revalidate": sorted(affected),
        "retained_current": sorted(
            r for r in current_refs if r not in affected and r != changed_ref
        ),
    }


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
    "verify-inputs": lambda d: verify_inputs(d["recorded"], d["current"]),
    "evaluate-axes": lambda d: evaluate_axes(d["metrics"], d.get("claims")),
    "advance-improvement": lambda d: advance_improvement(
        d["improvement"], d["event"], d.get("now")
    ),
    "summarize-improvements": lambda d: summarize_improvements(d["improvements"]),
    "handoff-status": lambda d: handoff_status(d["handoffs"], d.get("now")),
    "propagate-change": lambda d: propagate_change(
        d["changed_ref"], d["depends_on"], d["current_refs"]
    ),
}


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1 or args[0] not in COMMANDS:
        print(
            json.dumps(
                {
                    "status": "blocked",
                    "reason": "usage: evaluation_runtime.py <"
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
