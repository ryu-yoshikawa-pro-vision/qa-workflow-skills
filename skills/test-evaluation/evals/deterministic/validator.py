from __future__ import annotations

import json
import re
from typing import Any

from scripts.skills.evals.deterministic.result import EvalResult

AXES = ("traceability", "quality", "efficiency", "process", "reusability")
METRIC_STATUSES = {
    "measured",
    "unmeasured",
    "improved",
    "worsened",
    "unchanged",
    "not_comparable",
}
MEASURED = {"measured", "improved", "worsened", "unchanged", "not_comparable"}
OWNERS = {
    "plan": {"test-management"},
    "architecture": {"test-architecture-design"},
    "design": {"test-requirement-design", "test-condition-design", "test-case-design"},
}
STATES = (
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
AFTER_ADOPTION = set(STATES) - {"proposed", "rejected"}
AFTER_HANDOFF = AFTER_ADOPTION - {"adopted"}
AFTER_IMPLEMENTATION = AFTER_HANDOFF - {"handed_off"}
MEASUREMENT_MAP = {
    "measured_effective": "improved",
    "measured_no_effect": "unchanged",
    "measured_worsened": "worsened",
    "not_comparable": "not_comparable",
    "not_measurable": "unmeasured",
}
UNRESOLVED = {"not_comparable", "unmeasured", "invalid"}


def _derived_trend(statuses: set[str]) -> str:
    """Axis-wide trend derived from per-metric statuses (independent of the runtime)."""
    if "worsened" in statuses:
        return "mixed" if "improved" in statuses else "worsened"
    if "invalid" in statuses:
        return "invalid"
    if "improved" in statuses:
        return "partially_improved" if statuses & UNRESOLVED else "improved"
    if statuses & {"unchanged", "measured"}:
        return "no_change_or_baseline"
    if "not_comparable" in statuses:
        return "not_comparable"
    return "unmeasured"


_SCORE_KEYS = {"composite_score", "total_score", "overall_score", "score"}
_SECRET = re.compile(
    r"(?i)(?:password|passwd|(?:access[_-]?|auth[_-]?|refresh[_-]?)?token|client[_-]?secret|api[_-]?key|cookie|storage[_-]?state|authorization)\s*[:=]\s*['\"]?(?:bearer\s+)?[A-Za-z0-9_./+=-]{8,}"
)


def _document(text: str) -> tuple[dict[str, Any] | None, list[str]]:
    matches = re.findall(
        r"```json\s*\n(.*?)\n```", text, flags=re.DOTALL | re.IGNORECASE
    )
    if len(matches) != 1:
        return None, ["exactly_one_json_artifact_required"]
    try:
        value = json.loads(matches[0])
    except json.JSONDecodeError as exc:
        return None, [f"invalid_json:{exc.msg}"]
    if not isinstance(value, dict):
        return None, ["artifact_root_must_be_object"]
    return value, []


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


def _keys(value: Any):
    if isinstance(value, dict):
        for key, item in value.items():
            yield key
            yield from _keys(item)
    elif isinstance(value, list):
        for item in value:
            yield from _keys(item)


def _improvement_problems(item: dict[str, Any]) -> list[str]:
    problems: list[str] = []
    state = item.get("state")
    if state not in STATES:
        return ["state_invalid"]
    if state in AFTER_ADOPTION and not _text(item.get("adoption_ref")):
        problems.append("adopted_without_authenticated_adoption_ref")
    if state in AFTER_HANDOFF:
        owners = OWNERS.get(item.get("change_kind"), set())
        if (
            item.get("owner_skill") not in owners
            or not _text(item.get("request_ref"))
            or not _text(item.get("base_revision"))
        ):
            problems.append("handoff_owner_request_or_base_revision_invalid")
    if state in AFTER_IMPLEMENTATION and (
        not _text(item.get("new_revision"))
        or item.get("new_revision") == item.get("base_revision")
    ):
        problems.append("implemented_without_new_owner_revision")
    if state in MEASUREMENT_MAP:
        effect = (
            item.get("effect_metric")
            if isinstance(item.get("effect_metric"), dict)
            else {}
        )
        if effect.get("status") != MEASUREMENT_MAP[state]:
            problems.append("measurement_state_not_backed_by_comparable_metric")
    return problems


def validate(text: str, expected: dict[str, Any], eval_id: str) -> EvalResult:
    result = EvalResult("test-evaluation", eval_id)
    doc, errors = _document(text)
    result.add(
        "EVL-D001",
        doc is not None,
        "正規JSON artifactが一つだけ整形式で存在すること",
        evidence=errors or None,
    )
    if doc is None:
        return result
    result.add(
        "EVL-D002",
        doc.get("artifact_type") == "evaluation_report"
        and doc.get("schema_version") == "1"
        and doc.get("evaluation_status") in {"final", "provisional"}
        and doc.get("raw_results_modified") is False
        and doc.get("release_decision") == "not_determined_by_this_skill",
        "評価reportのtype・状態を持ち、元実績を改変せず、リリース・終了の判断を行わないこと",
    )
    axes = doc.get("axes") if isinstance(doc.get("axes"), dict) else {}
    metrics = doc.get("metrics") if isinstance(doc.get("metrics"), list) else []
    result.add(
        "EVL-D003",
        set(axes) == set(AXES)
        and doc.get("composite_score") is None
        and not (_SCORE_KEYS & set(_keys(axes)) or _SCORE_KEYS & set(_keys(metrics))),
        "追跡性・品質・効率・プロセス・再利用性の5軸を個別に示し、根拠のない総合点を出さないこと",
        evidence=sorted(set(axes)),
    )
    metric_errors = []
    by_axis: dict[str, list[dict[str, Any]]] = {axis: [] for axis in AXES}
    for metric in metrics:
        if (
            not isinstance(metric, dict)
            or metric.get("axis") not in AXES
            or metric.get("status") not in METRIC_STATUSES
        ):
            metric_errors.append(
                str(metric.get("metric_id") if isinstance(metric, dict) else metric)
            )
            continue
        by_axis[metric["axis"]].append(metric)
        if metric["status"] in MEASURED and not isinstance(
            metric.get("value"), (int, float)
        ):
            metric_errors.append(f"{metric.get('metric_id')}:measured_without_value")
        if metric["status"] == "unmeasured" and "value" in metric:
            metric_errors.append(f"{metric.get('metric_id')}:unmeasured_has_value")
        if metric["status"] == "not_comparable" and "delta" in metric:
            metric_errors.append(f"{metric.get('metric_id')}:not_comparable_has_delta")
    axis_errors = []
    for axis, entry in axes.items():
        if not isinstance(entry, dict):
            axis_errors.append(axis)
            continue
        statuses = {m["status"] for m in by_axis.get(axis, [])}
        if (entry.get("status") == "measured") is not bool(statuses & MEASURED):
            axis_errors.append(f"{axis}:status")
        if entry.get("trend") != _derived_trend(statuses):
            axis_errors.append(f"{axis}:trend_not_derived_from_all_metrics")
    result.add(
        "EVL-D004",
        not metric_errors and not axis_errors,
        "各指標が測定値と測定元、または未測定・比較不能の区別を持ち、軸のstatusと傾向が指標から導出されること",
        evidence={"metrics": metric_errors, "axes": axis_errors}
        if metric_errors or axis_errors
        else None,
    )
    claims = doc.get("claims") if isinstance(doc.get("claims"), list) else []
    rejected = {
        (c.get("axis"), c.get("assertion"))
        for c in doc.get("rejected_claims", [])
        if isinstance(c, dict)
    }
    claim_errors = []
    for claim in claims:
        if not isinstance(claim, dict):
            claim_errors.append(str(claim))
            continue
        axis, assertion = claim.get("axis"), claim.get("assertion")
        entry = axes.get(axis) if isinstance(axes.get(axis), dict) else None
        statuses = (
            {m["status"] for m in by_axis.get(axis, [])} if axis in by_axis else set()
        )
        if assertion == "metric_improved":
            by_id = {
                m.get("metric_id"): m.get("status")
                for ms in by_axis.values()
                for m in ms
            }
            supported = by_id.get(claim.get("metric_id")) == "improved"
        elif entry is None:
            supported = False
        elif assertion in {"improved", "partially_improved", "mixed", "worsened"}:
            trend = _derived_trend(statuses)
            supported = trend == assertion or (
                assertion == "worsened" and trend == "mixed"
            )
        elif assertion == "measured":
            supported = bool(statuses & MEASURED)
        else:
            supported = False
        if supported == ((axis, assertion) in rejected):
            claim_errors.append(f"{axis}:{assertion}")
    result.add(
        "EVL-D005",
        not claim_errors,
        "改善等の主張はその軸の比較可能な指標で支えられる場合だけ採用し、時間短縮だけで品質改善を主張しないこと",
        evidence=claim_errors or None,
    )
    improvements = (
        doc.get("improvements") if isinstance(doc.get("improvements"), list) else []
    )
    improvement_errors = []
    for item in improvements:
        if not isinstance(item, dict):
            improvement_errors.append(str(item))
            continue
        for problem in _improvement_problems(item):
            improvement_errors.append(f"{item.get('improvement_ref')}:{problem}")
    result.add(
        "EVL-D006",
        not improvement_errors,
        "改善は採用→正本ownerへの引継ぎ→新revisionでの実施→後続活動での測定の証拠を満たす状態にだけ進むこと",
        evidence=improvement_errors or None,
    )
    summary = (
        doc.get("improvement_summary")
        if isinstance(doc.get("improvement_summary"), dict)
        else {}
    )
    counts = {state: 0 for state in STATES}
    for item in improvements:
        if isinstance(item, dict) and item.get("state") in counts:
            counts[item["state"]] += 1
    result.add(
        "EVL-D007",
        summary.get("counts") == counts
        and summary.get("achieved") == counts["measured_effective"],
        "達成した改善の件数は、比較可能な効果が測定された改善だけから数え、未承認・未実施・未測定・悪化・比較不能を含めないこと",
        evidence={
            "derived_achieved": counts["measured_effective"],
            "actual": summary.get("achieved"),
        },
    )
    input_check = (
        doc.get("input_check") if isinstance(doc.get("input_check"), dict) else {}
    )
    inputs = doc.get("inputs") if isinstance(doc.get("inputs"), list) else []
    result.add(
        "EVL-D008",
        bool(inputs)
        and all(
            isinstance(i, dict)
            and _text(i.get("ref"))
            and _text(i.get("revision"))
            and _text(i.get("content_hash"))
            for i in inputs
        )
        and (
            doc.get("evaluation_status") != "final"
            or (
                input_check.get("status") == "current"
                and not doc.get("invalid_metrics")
            )
        ),
        "評価入力をref・revision・content hashで固定し、旧版・未検証の入力や無効な指標がある評価をfinalにしないこと",
        evidence=input_check or None,
    )
    handoff = doc.get("handoff") if isinstance(doc.get("handoff"), dict) else {}
    items = handoff.get("items") if isinstance(handoff.get("items"), list) else []
    derived_closed = bool(items) and all(
        isinstance(i, dict)
        and i.get("confirmation_verified") is True
        and _text(i.get("receiver"))
        for i in items
    )
    result.add(
        "EVL-D009",
        handoff.get("closed") is derived_closed
        and (derived_closed or bool(handoff.get("open_items")) or not items),
        "保管・引継ぎは、各項目の受領者の認証済み確認がある場合だけ完了とすること",
    )
    result.add(
        "EVL-D010",
        not any(_SECRET.search(item) for item in _strings(doc)),
        "secret・cookie・token等の実値を成果物へ転載しないこと",
    )
    if "expected_axis_status" in expected:
        actual = {axis: (entry or {}).get("status") for axis, entry in axes.items()}
        wanted = expected["expected_axis_status"]
        result.add(
            "EVL-D011",
            all(actual.get(axis) == status for axis, status in wanted.items()),
            "独立した期待基準が示す軸ごとの測定状態と一致すること",
            evidence={"expected": wanted, "actual": actual},
        )
    if "expected_axis_trend" in expected:
        wanted_trend = expected["expected_axis_trend"]
        actual_trend = {
            axis: (entry or {}).get("trend") for axis, entry in axes.items()
        }
        result.add(
            "EVL-D014",
            all(
                actual_trend.get(axis) == trend for axis, trend in wanted_trend.items()
            ),
            "独立した期待基準が示す軸全体の傾向（指標単位の改善と軸全体の判定の区別）と一致すること",
            evidence={"expected": wanted_trend, "actual": actual_trend},
        )
    if "expected_achieved" in expected:
        result.add(
            "EVL-D012",
            summary.get("achieved") == expected["expected_achieved"],
            "独立した期待基準が示す達成した改善件数と一致すること",
            evidence={
                "expected": expected["expected_achieved"],
                "actual": summary.get("achieved"),
            },
        )
    if "expected_rejected_claims" in expected:
        wanted_claims = sorted(
            f"{a}:{b}"
            for a, b in (tuple(x) for x in expected["expected_rejected_claims"])
        )
        actual_claims = sorted(f"{a}:{b}" for a, b in rejected)
        result.add(
            "EVL-D013",
            wanted_claims == actual_claims,
            "独立した期待基準が示す、根拠のない主張の棄却と一致すること",
            evidence={"expected": wanted_claims, "actual": actual_claims},
        )
    return result
