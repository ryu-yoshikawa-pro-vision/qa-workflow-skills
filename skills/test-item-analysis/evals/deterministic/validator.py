from __future__ import annotations

import re

from scripts.skills.evals.deterministic.markdown_parser import find_table, parse_tables
from scripts.skills.evals.deterministic.result import EvalResult

ITEM_ID = re.compile(r"^ITEM-[0-9]{3,}$")
FEATURE_ID = re.compile(r"^FEAT-[0-9]{3,}$")
STATUSES = {"planned", "unimplemented", "implemented", "unknown", "retired"}


def _clean(value: str) -> str:
    return " ".join(value.replace("<br>", ",").split()).strip()


def _rows(table) -> list[dict[str, str]]:
    return table.rows if table else []


def validate(text: str, expected: dict, eval_id: str) -> EvalResult:
    result = EvalResult("test-item-analysis", eval_id)
    try:
        tables = parse_tables(text)
    except ValueError as exc:
        result.add(
            "ITEM-D010",
            False,
            "output tables are malformed",
            evidence=str(exc),
        )
        return result
    feature_table = find_table(
        tables,
        section_contains="Feature population",
        required_headers=(
            "Feature ID",
            "Feature status",
            "Candidate item refs",
            "Candidate state",
        ),
    )
    item_table = find_table(
        tables,
        section_contains="Item candidates",
        required_headers=(
            "Item ID",
            "Name",
            "Kind",
            "Parent item IDs",
            "Feature refs",
            "Status",
            "Evidence refs",
            "Currentness",
        ),
    )
    history_table = find_table(
        tables,
        section_contains="Stable ID history",
        required_headers=(
            "Item ID",
            "Change",
            "Reason",
            "Related item IDs",
            "Evidence refs",
        ),
    )
    metric_table = find_table(
        tables,
        section_contains="Candidate identification metrics",
        required_headers=(
            "Metric",
            "Status",
            "Numerator",
            "Denominator",
            "Rate",
            "Basis",
        ),
    )
    owner_table = find_table(
        tables,
        section_contains="Separate owner metric",
        required_headers=("Separate owner metric", "State", "Value"),
    )
    missing = [
        name
        for name, table in (
            ("Feature population", feature_table),
            ("Item candidates", item_table),
            ("Stable ID history", history_table),
            ("Candidate identification metrics", metric_table),
            ("Separate owner metrics", owner_table),
        )
        if table is None
    ]
    result.add(
        "ITEM-D010",
        not missing,
        "candidate artifact, history, metrics, and owner boundaries are present",
        evidence=missing or None,
    )

    item_rows = _rows(item_table)
    item_ids = [_clean(row.get("Item ID", "")) for row in item_rows]
    invalid_ids = [value for value in item_ids if not ITEM_ID.fullmatch(value)]
    result.add(
        "ITEM-D001",
        not invalid_ids,
        "item IDs use the stable ITEM namespace",
        evidence=invalid_ids or None,
    )
    duplicates = sorted({value for value in item_ids if item_ids.count(value) > 1})
    result.add(
        "ITEM-D002",
        not duplicates,
        "item IDs are unique within scope",
        evidence=duplicates or None,
    )

    known_features = set(expected.get("known_features", []))
    population_ids = {_clean(row.get("Feature ID", "")) for row in _rows(feature_table)}
    unknown_features = sorted(
        feature
        for row in item_rows
        for feature in re.findall(r"FEAT-[0-9]{3,}", row.get("Feature refs", ""))
        if feature not in population_ids
        or (known_features and feature not in known_features)
    )
    result.add(
        "ITEM-D003",
        not unknown_features,
        "item feature refs resolve to the known population",
        evidence=unknown_features or None,
    )
    invalid_statuses = [
        row.get("Item ID", "")
        for row in item_rows
        if _clean(row.get("Status", "")) not in STATUSES
    ]
    actual_statuses = {
        _clean(row.get("Item ID", "")): _clean(row.get("Status", ""))
        for row in item_rows
    }
    status_mismatches = [
        {
            "item_id": item_id,
            "expected": expected_status,
            "actual": actual_statuses.get(item_id),
        }
        for item_id, expected_status in expected.get("expected_status", {}).items()
        if actual_statuses.get(item_id) != expected_status
    ]
    result.add(
        "ITEM-D004",
        not invalid_statuses and not status_mismatches,
        "item lifecycle status is distinct from feature status and matches the fixture",
        evidence={"invalid": invalid_statuses, "expected_mismatch": status_mismatches}
        if invalid_statuses or status_mismatches
        else None,
    )

    missing_required = sorted(
        set(expected.get("required_item_ids", [])) - set(item_ids)
    )
    result.add(
        "ITEM-D005",
        not missing_required,
        "fixture-required item candidates are present",
        evidence=missing_required or None,
    )
    parent_errors = []
    for row in item_rows:
        item_id = _clean(row.get("Item ID", ""))
        parents = re.findall(r"ITEM-[0-9]{3,}", row.get("Parent item IDs", ""))
        required = expected.get("expected_parent", {}).get(item_id)
        if required is not None and sorted(parents) != sorted(required):
            parent_errors.append(
                {"item_id": item_id, "expected": required, "actual": parents}
            )
        if any(parent not in item_ids for parent in parents):
            parent_errors.append(
                {
                    "item_id": item_id,
                    "missing_parent": [
                        parent for parent in parents if parent not in item_ids
                    ],
                }
            )
    result.add(
        "ITEM-D006",
        not parent_errors,
        "parent-child references resolve and match the fixture",
        evidence=parent_errors or None,
    )

    history_ids = {_clean(row.get("Item ID", "")) for row in _rows(history_table)}
    missing_history = sorted(set(item_ids) - history_ids)
    result.add(
        "ITEM-D007",
        not missing_history,
        "each current item has retained history",
        evidence=missing_history or None,
    )

    metric_rows = _rows(metric_table)
    candidate_metric = next(
        (
            row
            for row in metric_rows
            if _clean(row.get("Metric", ""))
            == "Confirmed feature-to-item candidate identification"
        ),
        None,
    )
    metric_errors = []
    if candidate_metric is None:
        metric_errors.append("candidate metric missing")
    else:
        status = _clean(candidate_metric.get("Status", ""))
        rate = _clean(candidate_metric.get("Rate", ""))
        denominator = _clean(candidate_metric.get("Denominator", ""))
        if denominator in {"0", "なし", "null", "N/A"} and rate in {
            "100%",
            "100",
            "1.0",
        }:
            metric_errors.append("zero denominator reported as complete")
        if expected.get("candidate_rate") is not None and rate not in {
            "100%",
            "100",
            "1",
            "1.0",
        }:
            metric_errors.append(
                {"expected_rate": expected["candidate_rate"], "actual_rate": rate}
            )
        if status != "measured" and rate in {"100%", "100", "1", "1.0"}:
            metric_errors.append("unmeasured population reports 100%")
    result.add(
        "ITEM-D008",
        not metric_errors,
        "unknown or zero-denominator scope is not reported as 100%",
        evidence=metric_errors or None,
    )

    owners = {
        _clean(row.get("Separate owner metric", "")): _clean(row.get("Value", ""))
        for row in _rows(owner_table)
    }
    missing_owners = sorted(
        set(expected.get("required_separate_metrics", [])) - set(owners)
    )
    wrongly_decided = [
        name
        for name, value in owners.items()
        if any(
            token in value.lower()
            for token in ("adopted", "accepted", "formal pass", "executed pass")
        )
    ]
    result.add(
        "ITEM-D009",
        not missing_owners and not wrongly_decided,
        "applicability, formal design, and execution stay with their owners",
        evidence={"missing": missing_owners, "decided_by_d": wrongly_decided}
        if missing_owners or wrongly_decided
        else None,
    )
    return result
