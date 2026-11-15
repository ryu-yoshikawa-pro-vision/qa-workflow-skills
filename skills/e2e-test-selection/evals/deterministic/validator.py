from __future__ import annotations

import re

from scripts.skills.evals.deterministic.markdown_parser import (
    find_table,
    parse_bullets,
    parse_tables,
)
from scripts.skills.evals.deterministic.result import EvalResult

ID_RE = re.compile(r"^E2E-CAND-\d{3,}$")
REVISION_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
DECISIONS = {"selected", "not_selected", "deferred", "blocked"}
SOURCE_RE = re.compile(r"^([A-Z][A-Z0-9-]*)@([^=,、，;；\s]+)=(current|stale|unknown)$")
SOURCE_REVISION_RE = re.compile(r"([A-Z][A-Z0-9-]*)@([^@,、，;；\s]+)")
RETIREMENT_RE = re.compile(r"(E2E-CAND-\d{3,})\s*:\s*([^;；]+)")
HISTORY_CANDIDATE_RE = re.compile(r"(E2E-CAND-\d{3,})\s*/\s*([^;；]+)")
HISTORY_DECISION_RE = re.compile(
    r"(E2E-CAND-\d{3,})\s*:\s*(selected|not_selected|deferred|blocked)\s*[—-]\s*([^;；]+)"
)


def _clean(value: str) -> str:
    return value.strip().replace("`", "")


def _parse_sources(value: str) -> dict[str, tuple[str, str]] | None:
    entries = [part.strip() for part in re.split(r"[,、，;；]", value) if part.strip()]
    parsed: dict[str, tuple[str, str]] = {}
    for entry in entries:
        match = SOURCE_RE.fullmatch(_clean(entry))
        if match is None or match.group(1) in parsed:
            return None
        parsed[match.group(1)] = (match.group(2), match.group(3))
    return parsed


def _parse_source_revisions(value: str) -> set[tuple[str, str]] | None:
    cleaned = _clean(value)
    matches = list(SOURCE_REVISION_RE.finditer(cleaned))
    remainder = SOURCE_REVISION_RE.sub("", cleaned)
    if not matches or remainder.strip(" ,、，;；"):
        return None
    pairs = [(match.group(1), match.group(2)) for match in matches]
    if len(pairs) != len(set(pairs)):
        return None
    return set(pairs)


def _parse_retirements(value: str) -> dict[str, str] | None:
    cleaned = _clean(value)
    if cleaned in {"", "なし", "none"}:
        return {}
    matches = list(RETIREMENT_RE.finditer(cleaned))
    remainder = RETIREMENT_RE.sub("", cleaned)
    if not matches or remainder.strip(" ,、，;；"):
        return None
    result = {match.group(1): match.group(2).strip() for match in matches}
    if len(result) != len(matches) or any(not reason for reason in result.values()):
        return None
    return result


def _parse_history_decisions(value: str) -> dict[str, dict[str, str]] | None:
    cleaned = _clean(value)
    if cleaned in {"", "なし", "none"}:
        return {}
    matches = list(HISTORY_DECISION_RE.finditer(cleaned))
    remainder = HISTORY_DECISION_RE.sub("", cleaned)
    if not matches or remainder.strip(" ,、，;；"):
        return None
    result = {
        match.group(1): {
            "decision": match.group(2),
            "rationale": match.group(3).strip(),
        }
        for match in matches
    }
    if len(result) != len(matches) or any(
        not row["rationale"] for row in result.values()
    ):
        return None
    return result


def validate(text: str, expected: dict, eval_id: str) -> EvalResult:
    result = EvalResult("e2e-test-selection", eval_id)
    bullets = parse_bullets(text)

    selection_ref = expected.get("required_selection_ref")
    revision = expected.get("required_selection_revision")
    identity = bullets.get("selection ref / revision", "")
    identity_match = re.fullmatch(r"(E2ESEL-\d{3,})\s*/\s*(\d+)", _clean(identity))
    identity_ok = bool(
        identity_match
        and identity_match.group(1) == selection_ref
        and identity_match.group(2) == str(revision)
    )

    history_table = find_table(
        parse_tables(text),
        section_contains="履歴",
        required_headers=(
            "revision",
            "previous revision",
            "candidate IDs / keys",
            "decisions / rationale",
            "source refs / revisions / currentness",
            "retired candidate IDs / reason",
            "change reason",
            "revision digest",
        ),
    )
    expected_history = expected.get("history", [])
    history_rows = history_table.rows if history_table else []
    history_errors: list[dict] = []
    if history_table is None:
        history_errors.append({"missing": "履歴 table"})
    if len(history_rows) != len(expected_history):
        history_errors.append(
            {"expected_rows": len(expected_history), "actual_rows": len(history_rows)}
        )
    for index, expected_row in enumerate(expected_history):
        if index >= len(history_rows):
            break
        row = history_rows[index]
        actual_sources = _parse_sources(row["source refs / revisions / currentness"])
        actual_retirements = _parse_retirements(row["retired candidate IDs / reason"])
        actual_decisions = _parse_history_decisions(row["decisions / rationale"])
        actual_candidates = HISTORY_CANDIDATE_RE.findall(row["candidate IDs / keys"])
        actual_ids = [candidate_id for candidate_id, _key in actual_candidates]
        actual_keys = {
            candidate_id: key.strip() for candidate_id, key in actual_candidates
        }
        expected_ids = expected_row.get("candidate_ids", [])
        expected_sources = {
            source["ref"]: (source["revision"], source["currentness"])
            for source in expected_row.get("sources", [])
        }
        details = {}
        if _clean(row["revision"]) != str(expected_row["revision"]):
            details["revision"] = _clean(row["revision"])
        if _clean(row["previous revision"]) != str(expected_row["previous_revision"]):
            details["previous_revision"] = _clean(row["previous revision"])
        if actual_ids != expected_ids:
            details["candidate_ids"] = actual_ids
        if actual_keys != expected_row.get("candidate_keys", {}):
            details["candidate_keys"] = actual_keys
        if actual_decisions != expected_row.get("candidate_decisions", {}):
            details["candidate_decisions"] = actual_decisions
        if actual_sources != expected_sources:
            details["sources"] = actual_sources
        if actual_retirements != expected_row.get("retired_candidates", {}):
            details["retired_candidates"] = actual_retirements
        if _clean(row["change reason"]) != expected_row.get("change_reason"):
            details["change_reason"] = _clean(row["change reason"])
        actual_digest = _clean(row["revision digest"])
        if not REVISION_DIGEST_RE.fullmatch(
            actual_digest
        ) or actual_digest != expected_row.get("revision_digest"):
            details["revision_digest"] = actual_digest
        if details:
            history_errors.append({"row": index + 1, **details})
    current_revision_digest = _clean(bullets.get("current revision digest", ""))
    current_digest_ok = bool(
        REVISION_DIGEST_RE.fullmatch(current_revision_digest)
        and current_revision_digest == expected.get("required_current_revision_digest")
    )
    if not current_digest_ok:
        history_errors.append({"current_revision_digest": current_revision_digest})
    current_retirements = _parse_retirements(
        bullets.get("retired candidate IDs / 理由", "")
    )
    if current_retirements != expected.get("required_retired_candidates", {}):
        history_errors.append({"current_retired_candidates": current_retirements})
    result.add(
        "E2E-SEL-D001",
        identity_ok
        and current_digest_ok
        and not history_errors
        and bool(bullets.get("current change reason", "").strip()),
        "selection ref/revision、current change reason、連続履歴とretirementを保持する",
        evidence={"identity": identity, "history": history_errors}
        if not identity_ok
        or history_errors
        or not bullets.get("current change reason", "").strip()
        else None,
    )

    candidate_table = find_table(
        parse_tables(text),
        section_contains="候補と判断",
        required_headers=(
            "Candidate ID / key",
            "decision",
            "技術非依存の価値・根拠",
            "source revision",
        ),
    )
    result.add(
        "E2E-SEL-D002",
        candidate_table is not None,
        "候補と判断の表がある",
        evidence=None if candidate_table is not None else "候補と判断",
    )
    rows = candidate_table.rows if candidate_table else []
    by_id: dict[str, str] = {}
    by_key: dict[str, str] = {}
    invalid: list[dict] = []
    expected_sources = {
        (source["ref"], source["revision"])
        for source in expected.get("required_sources", [])
    }
    expected_candidate_sources = expected.get("required_candidate_sources", {})
    for row in rows:
        candidate_cell = _clean(row.get("Candidate ID / key", ""))
        candidate_match = re.fullmatch(r"(E2E-CAND-\d{3,})\s*/\s*(.+)", candidate_cell)
        candidate = candidate_match.group(1) if candidate_match else ""
        candidate_key = candidate_match.group(2).strip() if candidate_match else ""
        decision = _clean(row.get("decision", ""))
        if (
            not ID_RE.fullmatch(candidate)
            or not candidate_key
            or candidate in by_id
            or candidate_key in by_key.values()
            or decision not in DECISIONS
        ):
            invalid.append({"candidate": candidate, "decision": decision})
        else:
            by_id[candidate] = decision
            by_key[candidate] = candidate_key
        sources = _parse_source_revisions(row.get("source revision", ""))
        expected_for_candidate = expected_candidate_sources.get(candidate)
        if (
            sources is None
            or not sources
            or not sources <= expected_sources
            or (
                expected_for_candidate is not None
                and sources != set(map(tuple, expected_for_candidate))
            )
        ):
            invalid.append(
                {
                    "candidate": candidate,
                    "source_revision": row.get("source revision", ""),
                }
            )
        if not _clean(row.get("技術非依存の価値・根拠", "")):
            invalid.append({"candidate": candidate, "missing": "rationale"})
    result.add(
        "E2E-SEL-D003",
        bool(rows) and not invalid,
        "candidate ID、decision、理由、source revisionが有効",
        evidence=invalid or (None if rows else "候補行なし"),
    )
    required = expected.get("required_decisions", {})
    mismatch = {
        cid: {"expected": decision, "actual": by_id.get(cid)}
        for cid, decision in required.items()
        if by_id.get(cid) != decision
    }
    extra = sorted(set(by_id) - set(required))
    key_mismatch = {
        candidate_id: {"expected": key, "actual": by_key.get(candidate_id)}
        for candidate_id, key in expected.get("required_candidate_keys", {}).items()
        if by_key.get(candidate_id) != key
    }
    result.add(
        "E2E-SEL-D004",
        not mismatch and not extra and not key_mismatch,
        "候補集合、stable candidate key、fixtureのdecisionを保つ",
        evidence={
            "mismatch": mismatch,
            "extra_candidates": extra,
            "key_mismatch": key_mismatch,
        }
        if mismatch or extra or key_mismatch
        else None,
    )

    actual_sources = _parse_sources(
        bullets.get("source refs / revisions / currentness", "")
    )
    required_source_map = {
        source["ref"]: (source["revision"], source["currentness"])
        for source in expected.get("required_sources", [])
    }
    result.add(
        "E2E-SEL-D005",
        actual_sources == required_source_map,
        "fixtureのsource ref、revision、currentnessを個別に追跡する",
        evidence={"expected": required_source_map, "actual": actual_sources}
        if actual_sources != required_source_map
        else None,
    )

    source_states = actual_sources or {}
    population = bullets.get("候補母集団と完全性", "")
    population_complete = (
        "完全" in population
        and "未確認" not in population
        and "不完全" not in population
    )
    blockers = bullets.get("blocker / 再開条件", "").strip()
    has_blocker = blockers not in {"", "なし", "none"}
    decisions = set(by_id.values())
    if has_blocker or "blocked" in decisions:
        expected_status = "blocked"
    elif (
        any(state != "current" for _revision, state in source_states.values())
        or decisions & {"deferred", "blocked"}
        or not population_complete
        or not rows
    ):
        expected_status = "unresolved"
    else:
        expected_status = "ready"
    actual_status = bullets.get("選定状態", "")
    population_matches_fixture = population_complete is expected.get(
        "population_complete"
    )
    result.add(
        "E2E-SEL-D006",
        actual_status == expected_status and population_matches_fixture,
        "source、候補母集団、候補判断、blockerから選定状態を導出する",
        evidence={
            "expected": expected_status,
            "actual": actual_status,
            "population_complete_expected": expected.get("population_complete"),
            "population_complete_actual": population_complete,
        }
        if actual_status != expected_status or not population_matches_fixture
        else None,
    )
    return result
