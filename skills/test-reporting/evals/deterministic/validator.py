from __future__ import annotations

import json
import re
from typing import Any

from scripts.skills.evals.deterministic.result import EvalResult

RAW_STATES = {"PASS", "FAIL", "未実行", "SKIP", "判定不能", "blocked"}
EXCLUSION_REASONS = {
    "build_mismatch",
    "environment_mismatch",
    "record_source_revision_mismatch",
    "period_mismatch",
    "period_unverified",
}
EXECUTION_KINDS = {
    "general_tc",
    "e2e",
    "regression",
    "exploration",
    "api",
    "batch",
    "component",
    "nonfunctional",
    "uiux",
    "wcag",
}
RATE_AND_COUNT_METRICS = {
    "pass_rate",
    "executed_rate",
    "fail_count",
    "unexecuted_count",
}
STATIC_KINDS = {"static_review", "static_analysis"}
CLOSURE_KEYS = (
    "population_complete",
    "source_current",
    "results_observable",
    "cleanup_closed",
)
BLOCKING_ISSUES = {
    "plan_not_approved",
    "plan_revision_superseded",
    "planned_sources_missing",
    "planned_source_ids_duplicated",
    "explicit_scope_and_discovery_roots_required",
    "plan_currentness_unverified",
    "plan_ref_and_revision_required",
    "plan_period_invalid",
    "duplicate_retrieval_source_id",
    "retrieval_without_source_id",
}
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


def _strings(value: Any):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _strings(item)


def _sources(doc: dict[str, Any]) -> list[dict[str, Any]]:
    value = doc.get("sources")
    return [s for s in value if isinstance(s, dict)] if isinstance(value, list) else []


def validate(text: str, expected: dict[str, Any], eval_id: str) -> EvalResult:
    result = EvalResult("test-reporting", eval_id)
    doc, errors = _document(text)
    result.add(
        "RPT-D001",
        doc is not None,
        "正規JSON artifactが一つだけ整形式で存在すること",
        evidence=errors or None,
    )
    if doc is None:
        return result
    sources = _sources(doc)
    result.add(
        "RPT-D002",
        doc.get("artifact_type") == "report_snapshot"
        and doc.get("schema_version") == "1"
        and str(doc.get("snapshot_ref", "")).startswith("RPT-")
        and doc.get("population_basis") in {"planned", "unknown_direct_request"}
        and (
            doc.get("population_basis") != "planned"
            or (doc.get("plan_ref") and doc.get("plan_revision"))
        ),
        "報告snapshotのtype・schema・snapshot ref・母集団の根拠（計画ref / revision）を持つこと",
    )
    closure_bad = [
        s.get("source_id")
        for s in sources
        if not isinstance(s.get("closure"), dict)
        or any(type(s["closure"].get(k)) is not bool for k in CLOSURE_KEYS)
        or s.get("complete")
        is not all(s["closure"].get(k) is True for k in CLOSURE_KEYS)
    ]
    result.add(
        "RPT-D003",
        not closure_bad,
        "sourceのcompleteが、母集団・source現在性・元結果の確定・cleanupの独立した閉鎖判定から導出されること",
        evidence=closure_bad or None,
    )
    overall = doc.get("overall") if isinstance(doc.get("overall"), dict) else {}
    expected_complete = (
        doc.get("population_basis") == "planned"
        and bool(sources)
        and all(s.get("complete") is True for s in sources)
    )
    result.add(
        "RPT-D004",
        overall.get("complete") is expected_complete
        and overall.get("pass_rate") is None,
        "全体completeが全planned sourceの完了から導出され、異なる単位をまたぐ全体PASS率を出さないこと",
        evidence={"derived": expected_complete, "actual": overall.get("complete")},
    )
    false_hundred = []
    for s in sources:
        rate = s.get("pass_rate")
        if rate is None:
            continue
        counts = s.get("counts") if isinstance(s.get("counts"), dict) else {}
        planned_total = s.get("planned_total")
        if not (
            s.get("complete") is True
            and isinstance(planned_total, int)
            and planned_total > 0
            and rate == round(counts.get("PASS", 0) / planned_total, 6)
        ):
            false_hundred.append(s.get("source_id"))
    by_unit = doc.get("by_unit") if isinstance(doc.get("by_unit"), dict) else {}
    for unit, bucket in by_unit.items():
        if (
            isinstance(bucket, dict)
            and bucket.get("pass_rate") is not None
            and bucket.get("complete") is not True
        ):
            false_hundred.append(f"unit:{unit}")
    result.add(
        "RPT-D005",
        not false_hundred,
        "PASS率は完全取得済みの計画母集団に対してだけ出し、未取得・部分取得・旧revisionで見かけの率を出さないこと",
        evidence=false_hundred or None,
    )
    unit_errors = []
    for unit, bucket in by_unit.items():
        members = [
            s
            for s in sources
            if s.get("source_id") in (bucket or {}).get("source_ids", [])
        ]
        if (
            not members
            or any(s.get("unit") != unit for s in members)
            or bucket.get("planned")
            != sum(s.get("planned_total") or 0 for s in members)
            or bucket.get("complete")
            is not all(s.get("complete") is True for s in members)
        ):
            unit_errors.append(unit)
    result.add(
        "RPT-D006",
        not unit_errors and "total" not in overall,
        "logical primary・attempt・test等の集計単位を混ぜず、単位別の分母が各sourceの計画母集団と一致すること",
        evidence=unit_errors or None,
    )
    shortfall_bad = []
    for s in sources:
        counts = s.get("counts") if isinstance(s.get("counts"), dict) else {}
        if sum(counts.values()) != s.get("retrieved_total"):
            shortfall_bad.append(
                (s.get("source_id"), "counts_do_not_sum_to_retrieved_total")
            )
        if any(
            state not in RAW_STATES
            and state not in {"reviewed", "not_reviewed", "tool_failed"}
            for state in counts
        ):
            shortfall_bad.append((s.get("source_id"), "raw_state_changed"))
        if s.get("complete") is not True and not s.get("issues"):
            shortfall_bad.append((s.get("source_id"), "incomplete_without_reason"))
        if (
            s.get("complete") is not True
            and isinstance(s.get("planned_total"), int)
            and s.get("kind") not in STATIC_KINDS
            and s.get("kind") != "defect"
            and s.get("pass_rate") is not None
        ):
            shortfall_bad.append((s.get("source_id"), "rate_on_incomplete_source"))
        for item in (
            s.get("excluded", []) if isinstance(s.get("excluded"), list) else []
        ):
            if (
                not isinstance(item, dict)
                or item.get("reason") not in EXCLUSION_REASONS
            ):
                shortfall_bad.append((s.get("source_id"), "exclusion_reason_invalid"))
    result.add(
        "RPT-D007",
        not shortfall_bad,
        "元のraw state値を保ち、集計件数が取得件数と一致し、未完了sourceは理由と不足を示すこと",
        evidence=shortfall_bad or None,
    )
    empty_bad = [
        s.get("source_id")
        for s in sources
        if s.get("retrieved_total") == 0
        and (
            (s.get("complete") is not True and s.get("empty_set") != "unknown_not_zero")
            or (
                s.get("empty_set") == "confirmed_no_target"
                and s.get("complete") is not True
            )
        )
    ]
    result.add(
        "RPT-D008",
        not empty_bad,
        "計画上の対象なし（正当な空集合）と、取得できず0件に見える状態を区別すること",
        evidence=empty_bad or None,
    )
    criteria = (
        doc.get("exit_criteria") if isinstance(doc.get("exit_criteria"), list) else []
    )
    by_id = {s.get("source_id"): s for s in sources}
    issues = (
        set(doc.get("issues", [])) if isinstance(doc.get("issues"), list) else set()
    )
    satisfied_without_population = [
        c.get("criterion_id")
        for c in criteria
        if isinstance(c, dict)
        and c.get("status") == "satisfied"
        and (
            not isinstance(c.get("source_ids"), list)
            or any(
                by_id.get(i) is None or by_id[i].get("complete") is not True
                for i in c["source_ids"]
            )
        )
    ]
    all_satisfied = bool(criteria) and all(
        isinstance(c, dict) and c.get("status") == "satisfied" for c in criteria
    )
    any_unsatisfied = any(
        isinstance(c, dict) and c.get("status") == "unsatisfied" for c in criteria
    )
    blocked = (
        bool(issues & BLOCKING_ISSUES)
        or doc.get("population_basis") != "planned"
        or doc.get("plan_approval_state") != "approved"
        or doc.get("plan_currentness") != "current"
        or not criteria
    )
    derived_exit = (
        "undetermined"
        if blocked
        else "unsatisfied"
        if any_unsatisfied
        else "satisfied"
        if all_satisfied and expected_complete
        else "undetermined"
    )
    result.add(
        "RPT-D009",
        not satisfied_without_population and doc.get("exit_judgement") == derived_exit,
        "終了判定は、承認済みで現在の計画、完全な母集団、各終了基準の充足から導出し、不完全な母集団でsatisfiedにしないこと",
        evidence={
            "derived": derived_exit,
            "actual": doc.get("exit_judgement"),
            "unproven": satisfied_without_population,
        },
    )
    static_bad = []
    for s in sources:
        if s.get("kind") in STATIC_KINDS:
            review = (
                s.get("review_completion")
                if isinstance(s.get("review_completion"), dict)
                else {}
            )
            allowed = bool(
                s.get("complete") is True
                and review.get("planned") is not None
                and review.get("reviewed") == review.get("planned")
                and s.get("finding_count") == 0
            )
            if s.get("zero_findings_claim_allowed") is not allowed:
                static_bad.append(s.get("source_id"))
    result.add(
        "RPT-D010",
        not static_bad,
        "静的レビューは計画対象すべてのレビュー完了と完全取得がなければ「指摘0件・完了」を主張しないこと",
        evidence=static_bad or None,
    )
    projection = (
        doc.get("defect_projection")
        if isinstance(doc.get("defect_projection"), dict)
        else {}
    )
    result.add(
        "RPT-D011",
        projection.get("read_only") is True
        and doc.get("release_decision") == "not_determined_by_this_skill",
        "欠陥は読取りprojectionに留め、リリース可否を判断しないこと",
    )
    result.add(
        "RPT-D012",
        not any(_SECRET.search(item) for item in _strings(doc)),
        "secret・cookie・token等の実値を成果物へ転載しないこと",
    )

    # --- review-driven independent checks ---------------------------------
    import hashlib

    body = {k: v for k, v in doc.items() if k != "snapshot_ref"}
    digest = hashlib.sha256(
        json.dumps(
            body, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()
    result.add(
        "RPT-D017",
        doc.get("snapshot_ref") == "RPT-" + digest[:40],
        "snapshot refが内容全体（件数・完全性・判定・取得内容）から決定され、異なる内容が同じrefにならないこと",
    )
    unit_by_source = {s.get("source_id"): s.get("unit") for s in sources}
    kind_by_source = {s.get("source_id"): s.get("kind") for s in sources}
    mixed = []
    for c in criteria:
        if not isinstance(c, dict) or c.get("status") not in {
            "satisfied",
            "unsatisfied",
        }:
            continue
        ids = c.get("source_ids") if isinstance(c.get("source_ids"), list) else []
        units = {unit_by_source.get(i) for i in ids}
        kinds = {kind_by_source.get(i) for i in ids}
        allowed = (
            STATIC_KINDS if c.get("metric") == "review_completion" else EXECUTION_KINDS
        )
        if c.get("metric") in RATE_AND_COUNT_METRICS | {
            "review_completion",
            "cleanup_complete",
        } and (len(units) != 1 or not kinds <= allowed):
            mixed.append(c.get("criterion_id"))
    result.add(
        "RPT-D018",
        not mixed,
        "終了基準は単一の計測単位・適用可能な方式のsourceだけを対象とし、異なる単位（logical primary / attempt / test / TC / 補助testware / 静的レビュー）を合算した率・件数で判定しないこと",
        evidence=mixed or None,
    )
    issues_set = (
        set(doc.get("issues", [])) if isinstance(doc.get("issues"), list) else set()
    )
    expected_currentness = (
        "not_applicable"
        if doc.get("population_basis") != "planned"
        else "unverified"
        if "plan_currentness_unverified" in issues_set
        else "superseded"
        if "plan_revision_superseded" in issues_set
        else "current"
    )
    result.add(
        "RPT-D019",
        doc.get("plan_currentness") == expected_currentness
        and (
            doc.get("population_basis") != "planned"
            or "plan_currentness_unverified" in issues_set
            or "plan_revision_superseded" in issues_set
            or doc.get("plan_currentness") == "current"
        ),
        "計画revisionの現在性を、未確認（unverified）・改版済み（superseded）・現在（current）で区別し、確認できない場合に現在扱いしないこと",
        evidence={
            "actual": doc.get("plan_currentness"),
            "derived": expected_currentness,
        },
    )
    if "expected_plan_currentness" in expected:
        result.add(
            "RPT-D020",
            doc.get("plan_currentness") == expected["expected_plan_currentness"],
            "独立した期待基準が示す計画revisionの現在性（current / unverified / superseded）と一致すること",
            evidence={
                "expected": expected["expected_plan_currentness"],
                "actual": doc.get("plan_currentness"),
            },
        )
    if "expected_criterion_status" in expected:
        actual_status = {
            c.get("criterion_id"): c.get("status")
            for c in criteria
            if isinstance(c, dict)
        }
        result.add(
            "RPT-D021",
            all(
                actual_status.get(k) == v
                for k, v in expected["expected_criterion_status"].items()
            ),
            "独立した期待基準が示す終了基準ごとの判定（satisfied / unsatisfied / unknown）と一致すること",
            evidence={
                "expected": expected["expected_criterion_status"],
                "actual": actual_status,
            },
        )
    if "expected_complete" in expected:
        result.add(
            "RPT-D013",
            overall.get("complete") is expected["expected_complete"],
            "独立した期待基準が示す全体完了状態と一致すること",
            evidence={
                "expected": expected["expected_complete"],
                "actual": overall.get("complete"),
            },
        )
    if "expected_exit_judgement" in expected:
        result.add(
            "RPT-D014",
            doc.get("exit_judgement") == expected["expected_exit_judgement"],
            "独立した期待基準が示す終了判定と一致すること",
            evidence={
                "expected": expected["expected_exit_judgement"],
                "actual": doc.get("exit_judgement"),
            },
        )
    if "expected_planned_totals" in expected:
        expected_totals = expected["expected_planned_totals"]
        actual_totals = {s.get("source_id"): s.get("planned_total") for s in sources}
        result.add(
            "RPT-D015",
            actual_totals == expected_totals,
            "独立した期待母集団（source IDと計画件数）が報告から欠落・増減していないこと",
            evidence={"expected": expected_totals, "actual": actual_totals},
        )
    if "expected_incomplete_sources" in expected:
        incomplete = sorted(
            s.get("source_id") for s in sources if s.get("complete") is not True
        )
        result.add(
            "RPT-D016",
            incomplete == sorted(expected["expected_incomplete_sources"]),
            "独立した期待基準が示す取得未完了sourceを検出していること",
            evidence={
                "expected": sorted(expected["expected_incomplete_sources"]),
                "actual": incomplete,
            },
        )
    return result
