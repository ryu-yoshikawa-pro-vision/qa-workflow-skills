from __future__ import annotations

import re

from scripts.skills.evals.deterministic.markdown_parser import find_table, parse_tables
from scripts.skills.evals.deterministic.result import EvalResult

CONDITION_ID = re.compile(r"^COND-[0-9]{3,}$")
ITEM_ID = re.compile(r"^ITEM-[0-9]{3,}$")


def _clean(value: str) -> str:
    return " ".join(value.replace("<br>", ",").split()).strip()


def _rows(table) -> list[dict[str, str]]:
    return table.rows if table else []


def validate(text: str, expected: dict, eval_id: str) -> EvalResult:
    result = EvalResult("test-condition-analysis", eval_id)
    try:
        tables = parse_tables(text)
    except ValueError as exc:
        result.add(
            "COND-D010",
            False,
            "output tables are malformed",
            evidence=str(exc),
        )
        return result
    condition_table = find_table(
        tables,
        section_contains="Condition candidates",
        required_headers=(
            "Condition ID",
            "Name",
            "Intent",
            "Kind",
            "Applicable item kinds",
            "Feature refs",
            "Known item refs",
            "Candidate state",
            "Authority refs",
            "Evidence refs",
            "Currentness",
            "Unknowns",
        ),
    )
    pair_table = find_table(
        tables,
        section_contains="Advisory item-condition candidate pairs",
        required_headers=(
            "Item ID",
            "Condition ID",
            "Candidate state",
            "Rationale",
            "Evidence refs",
        ),
    )
    separate_table = find_table(
        tables,
        section_contains="Separate owner metrics",
        required_headers=("Metric", "Owner", "State", "Count"),
    )
    missing = [
        name
        for name, table in (
            ("Condition candidates", condition_table),
            ("Advisory pairs", pair_table),
            ("Separate owner metrics", separate_table),
        )
        if table is None
    ]
    result.add(
        "COND-D010",
        not missing,
        "condition candidates, advisory pair crosscheck, and owner-separated metrics are present",
        evidence=missing or None,
    )

    rows = _rows(condition_table)
    ids = [_clean(row.get("Condition ID", "")) for row in rows]
    invalid_ids = [value for value in ids if not CONDITION_ID.fullmatch(value)]
    duplicates = sorted({value for value in ids if ids.count(value) > 1})
    result.add(
        "COND-D001",
        not invalid_ids,
        "condition candidates use the stable COND namespace",
        evidence=invalid_ids or None,
    )
    result.add(
        "COND-D002",
        not duplicates,
        "condition IDs are unique within scope",
        evidence=duplicates or None,
    )
    missing_ids = sorted(set(expected.get("required_condition_ids", [])) - set(ids))
    result.add(
        "COND-D003",
        not missing_ids,
        "fixture-required independent condition candidates are present",
        evidence=missing_ids or None,
    )

    known_features = set(expected.get("known_features", []))
    feature_refs = [
        ref
        for row in rows
        for ref in re.findall(r"FEAT-[0-9]{3,}", row.get("Feature refs", ""))
    ]
    unknown_features = (
        sorted(set(feature_refs) - known_features) if known_features else []
    )
    result.add(
        "COND-D004",
        not unknown_features,
        "condition feature refs resolve to the fixed source inventory",
        evidence=unknown_features or None,
    )
    required_authorities = set(expected.get("required_authority_refs", []))
    authority_refs = {
        ref
        for row in rows
        for ref in re.findall(
            r"(?:AUTH|SPEC|DECISION|UNKNOWN)-[A-Za-z0-9._-]+",
            row.get("Authority refs", ""),
        )
    }
    missing_authorities = sorted(required_authorities - authority_refs)
    result.add(
        "COND-D005",
        not missing_authorities,
        "candidate Authority refs are retained",
        evidence=missing_authorities or None,
    )
    missing_evidence = [
        row.get("Condition ID", "")
        for row in rows
        if not _clean(row.get("Evidence refs", ""))
        or _clean(row.get("Evidence refs", "")) in {"なし", "none"}
    ]
    result.add(
        "COND-D006",
        not missing_evidence,
        "every condition candidate has source evidence",
        evidence=missing_evidence or None,
    )

    expected_state = expected.get("required_candidate_state")
    state_errors = [
        row.get("Condition ID", "")
        for row in rows
        if expected_state and _clean(row.get("Candidate state", "")) != expected_state
    ]
    result.add(
        "COND-D007",
        not state_errors,
        "candidate state preserves uncertainty and is not a formal disposition",
        evidence=state_errors or None,
    )

    pair_rows = _rows(pair_table)
    pair_errors = []
    for row in pair_rows:
        item_id = _clean(row.get("Item ID", ""))
        condition_id = _clean(row.get("Condition ID", ""))
        state = _clean(row.get("Candidate state", ""))
        if item_id not in {"未確定", "unknown", "none"} and not ITEM_ID.fullmatch(
            item_id
        ):
            pair_errors.append({"item_id": item_id, "error": "invalid stable item ref"})
        if condition_id not in ids:
            pair_errors.append(
                {"condition_id": condition_id, "error": "unknown candidate condition"}
            )
        if state.lower() in {
            "adopted",
            "accepted",
            "not applicable",
            "excluded",
            "duplicate",
            "pass",
        }:
            pair_errors.append(
                {
                    "item_id": item_id,
                    "condition_id": condition_id,
                    "error": "formal decision is outside D",
                }
            )
    result.add(
        "COND-D008",
        not pair_errors,
        "crosscheck rows are advisory and do not decide applicability",
        evidence=pair_errors or None,
    )

    separate_rows = _rows(separate_table)
    separate_names = {_clean(row.get("Metric", "")) for row in separate_rows}
    missing_metrics = sorted(
        set(expected.get("required_separate_metrics", [])) - separate_names
    )
    formal_values = [
        row
        for row in separate_rows
        if _clean(row.get("Metric", ""))
        in set(expected.get("required_separate_metrics", []))
        and (
            _clean(row.get("Count", "")) not in {"N/A", "null", ""}
            or _clean(row.get("State", "")) != "Not provided to D"
        )
    ]
    result.add(
        "COND-D009",
        not missing_metrics and not formal_values,
        "candidate, applicability, formal design, and execution metrics remain separate",
        evidence={"missing": missing_metrics, "formal_values": formal_values}
        if missing_metrics or formal_values
        else None,
    )

    forbidden = [
        token
        for token in (
            "cartesian product generated",
            "all combinations adopted",
            "正式採用済み",
        )
        if token in text.lower()
    ]
    result.add(
        "COND-D011",
        not forbidden,
        "no full Cartesian product or automatic adoption is claimed",
        evidence=forbidden or None,
    )
    return result
