from __future__ import annotations

from collections import defaultdict
from itertools import combinations, product
import re
from typing import Iterable, Mapping, Sequence

from .markdown_parser import MarkdownTable
from .result import EvalResult

CANONICAL_SKILLS = {
    "qa-workflow",
    "spec-analysis",
    "question-analysis",
    "test-analysis",
    "test-requirement-design",
    "test-condition-design",
    "test-case-design",
    "coverage-analysis",
    "adversarial-review",
}

PRIORITIES = {"高", "中", "低"}
RISK_LEVEL_ORDER = {"低": 1, "中": 2, "高": 3}

ID_PATTERNS = {
    "SPEC": re.compile(r"^SPEC-\d{3}$"),
    "DECISION": re.compile(r"^DEC-\d{3}$"),
    "INFERENCE": re.compile(r"^INF-\d{3}$"),
    "UNKNOWN": re.compile(r"^UNK-\d{3}$"),
    "QUESTION": re.compile(r"^Q-\d{3}$"),
    "RISK": re.compile(r"^RISK-\d{3}$"),
    "TR": re.compile(r"^TR-\d{3}$"),
    "TCN": re.compile(r"^TCN-\d{3}$"),
    "CI": re.compile(r"^TCN-\d{3}-CI\d{2}$"),
    "TC": re.compile(r"^TC-\d{3}$"),
    "REV": re.compile(r"^REV-\d{3}$"),
    "SRC": re.compile(r"^SRC-\d{3}$"),
    "ASM": re.compile(r"^ASM-\d{3}$"),
    "CHANGE": re.compile(r"^CHG-\d{3}$"),
    "DEPENDENCY": re.compile(r"^DEP-\d{3}$"),
}

ALL_ID_RE = re.compile(
    r"\b(?:SPEC|DEC|INF|UNK|Q|RISK|TR|TCN|TC|REV|SRC|ASM|CHG|DEP)-\d{3}(?:-CI\d{2})?\b"
)


def clean(value: str) -> str:
    return value.strip().strip("`")


def ids_in(value: str) -> list[str]:
    return ALL_ID_RE.findall(value or "")


def nonempty_rows(table: MarkdownTable | None, key: str | None = None) -> list[dict[str, str]]:
    if table is None:
        return []
    if key is None:
        return [r for r in table.rows if any(clean(v) for v in r.values())]
    return [r for r in table.rows if clean(r.get(key, ""))]


def add_duplicate_assertion(result: EvalResult, assertion_id: str, values: Sequence[str], label: str) -> None:
    counts: dict[str, int] = defaultdict(int)
    for value in values:
        if value:
            counts[value] += 1
    dupes = sorted(v for v, c in counts.items() if c > 1)
    result.add(assertion_id, not dupes, f"{label} must be unique", evidence={"duplicates": dupes} if dupes else None)


def add_allowed_assertion(result: EvalResult, assertion_id: str, values: Iterable[str], allowed: set[str], label: str) -> None:
    invalid = sorted({clean(v) for v in values if clean(v) and clean(v) not in allowed})
    result.add(assertion_id, not invalid, f"{label} must use allowed values", evidence={"invalid": invalid, "allowed": sorted(allowed)} if invalid else None)


def add_required_fields_assertion(result: EvalResult, assertion_id: str, rows: Sequence[Mapping[str, str]], fields: Sequence[str], row_id_field: str, label: str) -> None:
    missing = []
    for row in rows:
        missing_fields = [field for field in fields if not clean(row.get(field, ""))]
        if missing_fields:
            missing.append({"row": clean(row.get(row_id_field, "")) or "<unknown>", "fields": missing_fields})
    result.add(assertion_id, not missing, f"{label} required fields must be present", evidence=missing or None)


def add_reference_assertion(result: EvalResult, assertion_id: str, rows: Sequence[Mapping[str, str]], fields: Sequence[str], known_ids: set[str], label: str, *, ignore_patterns: tuple[re.Pattern[str], ...] = ()) -> None:
    unknown: list[dict[str, str]] = []
    for row in rows:
        for field in fields:
            for ref in ids_in(row.get(field, "")):
                if any(p.fullmatch(ref) for p in ignore_patterns):
                    continue
                if ref not in known_ids:
                    unknown.append({"field": field, "reference": ref})
    result.add(assertion_id, not unknown, f"{label} references must exist", evidence=unknown or None)


def check_expected_closure(upstream_ids: Iterable[str], linked_ids: Iterable[str], disposition_ids: Iterable[str]) -> list[str]:
    linked = set(linked_ids)
    disposed = set(disposition_ids)
    return sorted(set(upstream_ids) - linked - disposed)


def compute_graph_gaps(graph: Mapping) -> set[str]:
    node_types = graph.get("node_types", {})
    edges = graph.get("edges", [])
    dispositions = set(graph.get("dispositions", {}))
    outgoing: dict[str, set[str]] = defaultdict(set)
    for src, dst in edges:
        outgoing[src].add(dst)
    gaps: set[str] = set()
    for node, node_type in node_types.items():
        if node in dispositions:
            continue
        targets = outgoing.get(node, set())
        target_types = {node_types.get(t) for t in targets}
        if node_type in {"Authority", "Risk"} and "TR" not in target_types:
            gaps.add(node)
        elif node_type == "TR" and "TCN" not in target_types:
            gaps.add(node)
        elif node_type == "TCN" and not ({"CI", "TC"} & target_types):
            gaps.add(node)
        elif node_type == "CI" and "TC" not in target_types:
            gaps.add(node)
    return gaps


def parse_combination(value: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for part in re.split(r"[;,]\s*", value.strip()):
        if not part:
            continue
        if "=" in part:
            key, val = part.split("=", 1)
        elif ":" in part or "：" in part:
            key, val = re.split(r"[:：]", part, maxsplit=1)
        else:
            continue
        result[clean(key)] = clean(val)
    return result


def assignment_forbidden(assignment: Mapping[str, str], forbidden_constraints: Sequence[Mapping[str, str]]) -> bool:
    return any(all(assignment.get(k) == v for k, v in constraint.items()) for constraint in forbidden_constraints)


def feasible_pairs(factors: Mapping[str, Sequence[str]], forbidden_constraints: Sequence[Mapping[str, str]]) -> set[tuple[str, str, str, str]]:
    names = list(factors)
    valid_assignments = [
        assignment
        for assignment in (dict(zip(names, values)) for values in product(*(factors[name] for name in names)))
        if not assignment_forbidden(assignment, forbidden_constraints)
    ]
    feasible: set[tuple[str, str, str, str]] = set()
    for a, b in combinations(names, 2):
        for assignment in valid_assignments:
            feasible.add((a, assignment[a], b, assignment[b]))
    return feasible


def covered_pairs(combinations_: Sequence[Mapping[str, str]]) -> set[tuple[str, str, str, str]]:
    covered: set[tuple[str, str, str, str]] = set()
    for combo in combinations_:
        names = sorted(combo)
        for a, b in combinations(names, 2):
            covered.add((a, combo[a], b, combo[b]))
    return covered
