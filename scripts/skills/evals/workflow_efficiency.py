"""Compare recorded QA workflow trials without inventing missing measurements."""

from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from pathlib import Path
from typing import Any

SCHEMA = "qa-workflow-efficiency-v1"
SCENARIOS = (
    "initial_qa",
    "unchanged_request",
    "local_code_change",
    "external_spec_revision",
    "interrupted_resume",
)
METRICS = {
    "wall_seconds": "lower",
    "skill_call_count": "lower",
    "skill_restart_count": "lower",
    "human_review_seconds": "lower",
    "human_approval_seconds": "lower",
    "reanalyze_count": "lower",
    "retry_count": "lower",
    "reused_artifact_count": "higher",
    "regenerated_artifact_count": "lower",
    "token_count": "lower",
    "request_count": "lower",
    "cost_amount": "lower",
}
REQUIRED_QUALITY = ("functional", "quality", "safety", "traceability")


def _obj(value: Any, fields: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != fields:
        raise ValueError(f"{label} fields invalid")
    return value


def _nonempty(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be nonempty")
    return value


def _refs(value: Any, label: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ValueError(f"{label} must be a list")
    rows = [_nonempty(item, label) for item in value]
    if len(rows) != len(set(rows)):
        raise ValueError(f"{label} contains duplicates")
    return tuple(sorted(rows))


def _metric(value: Any, label: str) -> tuple[float | None, str]:
    row = _obj(
        value,
        {"value", "unit", "source_ref", "unmeasured_reason"},
        label,
    )
    unit = _nonempty(row["unit"], f"{label} unit")
    raw = row["value"]
    if raw is None:
        if row["source_ref"] is not None or not isinstance(
            row["unmeasured_reason"], str
        ) or not row["unmeasured_reason"].strip():
            raise ValueError(f"{label} unmeasured provenance invalid")
        return None, unit
    if (
        isinstance(raw, bool)
        or not isinstance(raw, (int, float))
        or not math.isfinite(raw)
        or raw < 0
        or not isinstance(row["source_ref"], str)
        or not row["source_ref"].strip()
        or row["unmeasured_reason"] is not None
    ):
        raise ValueError(f"{label} measured provenance invalid")
    return float(raw), unit


def _trial(value: Any, label: str) -> dict[str, Any]:
    row = _obj(
        value,
        {
            "trial_ref",
            "run_ref",
            "product_commit",
            "source_revisions",
            "scope_refs",
            "qa_goal_ref",
            "expectation_ref",
            "test_set_ref",
            "environment_ref",
            "agent_config_ref",
            "quality",
            "metrics",
        },
        label,
    )
    for field in (
        "trial_ref",
        "run_ref",
        "product_commit",
        "qa_goal_ref",
        "expectation_ref",
        "test_set_ref",
        "environment_ref",
        "agent_config_ref",
    ):
        _nonempty(row[field], f"{label}.{field}")
    source = row["source_revisions"]
    if not isinstance(source, list) or not source:
        raise ValueError(f"{label} source revisions missing")
    revisions: list[tuple[str, str]] = []
    for item in source:
        ref = _obj(item, {"ref", "revision"}, "source revision")
        revisions.append(
            (_nonempty(ref["ref"], "source ref"), _nonempty(ref["revision"], "revision"))
        )
    if len({ref for ref, _ in revisions}) != len(revisions):
        raise ValueError("duplicate source revision")
    _refs(row["scope_refs"], "scope_refs")
    quality = _obj(
        row["quality"], {*REQUIRED_QUALITY, "independent_evidence_ref"}, "quality"
    )
    _nonempty(quality["independent_evidence_ref"], "independent quality evidence")
    for field in REQUIRED_QUALITY:
        if quality[field] not in {"pass", "fail", "unverified"}:
            raise ValueError(f"invalid independent quality: {field}")
    metrics = _obj(row["metrics"], set(METRICS), "trial metrics")
    for key, value in metrics.items():
        _metric(value, key)
    return row


def _basis(trial: dict[str, Any]) -> str:
    """Ignore Agent configuration, which is recorded but not the QA test scope."""
    fields = (
        "product_commit",
        "source_revisions",
        "scope_refs",
        "qa_goal_ref",
        "expectation_ref",
        "test_set_ref",
        "environment_ref",
    )
    canonical = {name: trial[name] for name in fields}
    canonical["source_revisions"] = sorted(
        canonical["source_revisions"], key=lambda row: row["ref"]
    )
    canonical["scope_refs"] = sorted(canonical["scope_refs"])
    return json.dumps(canonical, sort_keys=True, ensure_ascii=False)


def _summary(rows: list[dict[str, Any]], key: str) -> dict[str, Any]:
    values = [_metric(row["metrics"][key], key) for row in rows]
    units = {unit for _, unit in values}
    if len(units) != 1 or any(value is None for value, _ in values):
        return {"status": "not_measured", "reason": "missing_or_inconsistent_unit"}
    measured = [value for value, _ in values if value is not None]
    return {
        "status": "measured",
        "unit": next(iter(units)),
        "median": statistics.median(measured),
        "minimum": min(measured),
        "maximum": max(measured),
        "trial_count": len(measured),
    }


def evaluate(data: dict[str, Any]) -> dict[str, Any]:
    _obj(data, {"schema_version", "scenarios"}, "evaluation")
    if data["schema_version"] != SCHEMA:
        raise ValueError("unsupported evaluation schema")
    scenarios = data["scenarios"]
    if not isinstance(scenarios, list) or {
        row.get("scenario") for row in scenarios if isinstance(row, dict)
    } != set(SCENARIOS) or len(scenarios) != len(SCENARIOS):
        raise ValueError("all five independent scenarios are required exactly once")
    seen_trials: set[str] = set()
    results: list[dict[str, Any]] = []
    for scenario in scenarios:
        _obj(scenario, {"scenario", "baseline", "candidate"}, "scenario")
        groups: dict[str, list[dict[str, Any]]] = {}
        for group in ("baseline", "candidate"):
            raw = scenario[group]
            if not isinstance(raw, list):
                raise ValueError(f"{group} trials must be a list")
            groups[group] = [_trial(row, group) for row in raw]
            for trial in groups[group]:
                ref = trial["trial_ref"]
                if ref in seen_trials:
                    raise ValueError("duplicate trial_ref across comparisons")
                seen_trials.add(ref)
        reasons: list[str] = []
        combined = groups["baseline"] + groups["candidate"]
        if len(groups["baseline"]) < 2 or len(groups["candidate"]) < 2:
            reasons.append("independent_repeated_trials_missing")
        if combined and len({_basis(trial) for trial in combined}) != 1:
            reasons.append("comparison_conditions_differ")
        if any(
            trial["quality"][field] != "pass"
            for trial in combined
            for field in REQUIRED_QUALITY
        ):
            reasons.append("independent_quality_or_safety_not_passed")
        metrics: dict[str, dict[str, Any]] = {}
        improved = False
        regressed = False
        for key, direction in METRICS.items():
            before = _summary(groups["baseline"], key) if groups["baseline"] else {
                "status": "not_measured", "reason": "baseline_missing"
            }
            after = _summary(groups["candidate"], key) if groups["candidate"] else {
                "status": "not_measured", "reason": "candidate_missing"
            }
            change = "not_comparable"
            if (
                before["status"] == "measured"
                and after["status"] == "measured"
                and before["unit"] == after["unit"]
            ):
                delta = after["median"] - before["median"]
                if delta == 0:
                    change = "unchanged"
                elif (delta < 0 and direction == "lower") or (
                    delta > 0 and direction == "higher"
                ):
                    change = "improved"
                    improved = True
                else:
                    change = "regressed"
                    regressed = True
            metrics[key] = {"baseline": before, "candidate": after, "change": change}
        if reasons:
            status = "not_comparable"
        elif regressed:
            status = "needs_review"
        elif improved:
            status = "improvement_evidenced"
        else:
            status = "not_evidenced"
        results.append(
            {
                "scenario": scenario["scenario"],
                "status": status,
                "reasons": reasons,
                "trial_refs": {
                    name: [row["trial_ref"] for row in trials]
                    for name, trials in groups.items()
                },
                "metrics": metrics,
            }
        )
    overall = (
        "efficiency_evidenced"
        if all(row["status"] == "improvement_evidenced" for row in results)
        else "unproven"
    )
    return {"schema_version": "qa-workflow-efficiency-result-v1", "status": overall, "scenarios": results}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        if not args.input.is_file() or args.input.stat().st_size > 2 * 1024 * 1024:
            raise ValueError("evaluation input missing or too large")
        data = json.loads(args.input.read_text(encoding="utf-8"))
        report = evaluate(data)
    except (OSError, UnicodeError, ValueError, TypeError) as exc:
        print(
            json.dumps(
                {"status": "blocked", "reason": str(exc)},
                sort_keys=True,
                ensure_ascii=False,
            )
        )
        return 2
    print(json.dumps(report, sort_keys=True, ensure_ascii=False, separators=(",", ":")))
    return 0 if report["status"] == "efficiency_evidenced" else 1


if __name__ == "__main__":
    sys.exit(main())
