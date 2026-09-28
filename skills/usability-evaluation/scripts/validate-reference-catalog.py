#!/usr/bin/env python3
"""Independent validator for usability-evaluation source/reference Markdown."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit


SOURCE_ID = re.compile(r"^SRC-(\d{3,})$")
ITEM_ID = re.compile(r"^(SRC-\d{3,})-ITEM-(\d{4,})$")
REF_ID = re.compile(r"^REF-(\d{4,})$")
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
SOURCE_POSITIONS = {"normative", "informative", "advisory", "methodology"}
SOURCE_STATUSES = {"current", "draft", "proposed", "archived", "superseded", "unknown"}
ACCESS = {"public", "restricted", "unavailable"}
ADOPTION = {"adopted", "reference-only", "replaced", "unavailable", "rejected"}
CANDIDATE_STATUSES = {"pending", "adopted", "reference-only", "rejected", "duplicate", "unavailable", "replaced"}
ORIGINS = {"seed", "query", "cross-link"}
COMPLETION = {"completed", "blocked"}
COVERAGE_STATUS = {"covered", "not-applicable", "blocked"}
DISPOSITION = {"included", "merged-duplicate", "reference-only", "unavailable", "out-of-scope"}
LOCATOR = {"none", "fragment", "section-id", "heading", "page"}
SEMANTIC = {"pass", "fail", "not-required"}

SOURCE_COLUMNS = ["Source ID", "Name", "Canonical URL", "Publisher / Owner", "Category", "Source Position", "Platform / Product Scope", "Source Status / Lifecycle", "Access State", "Checked At", "Adoption Status", "License / Terms", "Coverage Axes", "Note"]
CANDIDATE_COLUMNS = ["Candidate Name", "Canonical URL", "Discovery Origin", "Discovery Detail", "Coverage Gap", "Status", "Reason", "Checked At", "Source ID"]
DISCOVERY_COLUMNS = ["Discovery Type", "Discovery Target", "Discovery Category", "Checked At", "Checked Scope", "Checked Count", "New Candidate Count", "Retrieval Boundary", "Completion", "Block Reason"]
COVERAGE_COLUMNS = ["Coverage Axis", "Concern / Pattern Family", "Required Source Position", "Selected Source Refs", "Reference Entry Refs", "Coverage Status", "Gap / Reason", "Checked At"]
ITEM_COLUMNS = ["Source ID", "Source Item Ref", "Name / Section", "Document Canonical URL", "Locator Type", "Locator", "Disposition", "Access State", "Source Status / Lifecycle", "Reference Destination", "Available Dimensions", "Captured Dimensions", "Semantic Validation", "Checked At"]
ENTRY_SOURCE_COLUMNS = ["Source Item Ref", "Source Position", "Source Status / Maturity", "Applicability"]


class ValidationError(ValueError):
    pass


def _split_row(line: str) -> list[str]:
    line = line.strip()
    if not line.startswith("|") or not line.endswith("|"):
        raise ValidationError("malformed table row")
    cells: list[str] = []
    current: list[str] = []
    escaped = False
    for char in line[1:-1]:
        if char == "|" and not escaped:
            cells.append("".join(current).strip())
            current = []
            continue
        current.append(char)
        if char == "\\" and not escaped:
            escaped = True
        else:
            escaped = False
    cells.append("".join(current).strip())
    return [cell.replace("\\|", "|").replace("\\\\", "\\") for cell in cells]


def _table(lines: list[str], heading: str, columns: list[str]) -> list[dict[str, str]]:
    indexes = [index for index, line in enumerate(lines) if line.strip() == heading]
    if len(indexes) != 1:
        raise ValidationError(f"heading_count:{heading}:{len(indexes)}")
    i = indexes[0] + 1
    while i < len(lines) and not lines[i].lstrip().startswith("|"):
        if lines[i].startswith("## "):
            break
        i += 1
    if i + 1 >= len(lines):
        raise ValidationError(f"table_missing:{heading}")
    if _split_row(lines[i]) != columns:
        raise ValidationError(f"columns_mismatch:{heading}")
    if not re.fullmatch(r"\|(?:\s*:?-{3,}:?\s*\|)+", lines[i + 1].strip()):
        raise ValidationError(f"separator_missing:{heading}")
    rows = []
    i += 2
    while i < len(lines) and lines[i].lstrip().startswith("|"):
        values = _split_row(lines[i])
        if len(values) != len(columns):
            raise ValidationError(f"column_count:{heading}")
        rows.append(dict(zip(columns, values)))
        i += 1
    return rows


def _unescape_list(value: str) -> list[str]:
    if value == "-":
        return []
    tokens: list[str] = []
    current: list[str] = []
    escaped = False
    for char in value:
        if char == ";" and not escaped:
            tokens.append("".join(current).strip())
            current = []
            continue
        current.append(char)
        if char == "\\" and not escaped:
            escaped = True
        else:
            escaped = False
    tokens.append("".join(current).strip())
    result = [token.replace("\\;", ";").replace("\\|", "|").replace("\\\\", "\\") for token in tokens]
    if not all(result) or len(result) != len(set(result)) or result != sorted(result):
        raise ValidationError("list_field_not_canonical")
    return result


def _date(value: str, label: str) -> None:
    if not DATE.fullmatch(value):
        raise ValidationError(f"invalid_date:{label}:{value}")


def _url(value: str, label: str) -> None:
    try:
        parts = urlsplit(value)
        _ = parts.port
    except ValueError as exc:
        raise ValidationError(f"invalid_url:{label}") from exc
    if parts.scheme not in {"http", "https"} or not parts.hostname or parts.fragment or parts.username or parts.password:
        raise ValidationError(f"invalid_canonical_url:{label}:{value}")


def _entry_records(root: Path) -> tuple[dict[str, dict], list[str]]:
    entries: dict[str, dict] = {}
    errors: list[str] = []
    if not root.is_dir():
        return entries, ["references_directory_missing"]
    for path in sorted(root.rglob("*.md")):
        text = path.read_text(encoding="utf-8")
        lines = text.splitlines()
        for index, line in enumerate(lines):
            if "reference-entry-id:" not in line:
                continue
            match = re.fullmatch(r"<!-- reference-entry-id: (REF-\d{4,}) -->", line.strip())
            if not match:
                errors.append(f"malformed_reference_id_marker:{path}:{index + 1}")
                continue
            ref = match.group(1)
            if index == 0 or not lines[index - 1].startswith("## "):
                errors.append(f"reference_id_not_after_h2:{ref}")
                continue
            if ref in entries:
                errors.append(f"duplicate_reference_id:{ref}")
                continue
            end = next((position for position in range(index + 1, len(lines)) if lines[position].startswith("## ")), len(lines))
            entry_lines = lines[index - 1:end]
            try:
                rows = _table(entry_lines, "### Source Items", ENTRY_SOURCE_COLUMNS)
            except ValidationError as exc:
                errors.append(f"{path}:{exc}")
                continue
            entries[ref] = {"path": path.relative_to(root).as_posix(), "name": lines[index - 1][3:].strip(), "rows": rows}
    return entries, errors


def _validate_links(root: Path) -> list[str]:
    errors = []
    pattern = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
    for path in root.rglob("*.md"):
        for target in pattern.findall(path.read_text(encoding="utf-8")):
            if target.startswith(("https://", "http://", "mailto:")):
                continue
            local = target.split("#", 1)[0]
            if not local:
                continue
            resolved = (path.parent / local).resolve()
            try:
                resolved.relative_to(root.resolve())
            except ValueError:
                errors.append(f"link_escapes_references:{path}:{target}")
                continue
            if not resolved.is_file():
                errors.append(f"broken_reference_link:{path}:{target}")
    return errors


def validate(references_dir: Path, *, allow_incomplete: bool = False) -> list[str]:
    issues: list[str] = []
    catalog_path = references_dir / "source-catalog.md"
    coverage_path = references_dir / "source-coverage.md"
    for path in (catalog_path, coverage_path):
        if not path.is_file():
            issues.append(f"missing_file:{path.name}")
    if issues:
        return issues
    catalog = catalog_path.read_text(encoding="utf-8").splitlines()
    coverage = coverage_path.read_text(encoding="utf-8").splitlines()
    try:
        sources = _table(catalog, "## Sources", SOURCE_COLUMNS)
        candidates = _table(catalog, "## Candidates", CANDIDATE_COLUMNS)
        runs = _table(catalog, "## Discovery Runs", DISCOVERY_COLUMNS)
        coverage_rows = _table(coverage, "## Capability Coverage", COVERAGE_COLUMNS)
        items = _table(coverage, "## Source Items", ITEM_COLUMNS)
    except ValidationError as exc:
        return [str(exc)]

    source_by_id: dict[str, dict[str, str]] = {}
    url_to_id: dict[str, str] = {}
    for row in sources:
        sid = row["Source ID"]
        if sid != "-":
            if not SOURCE_ID.fullmatch(sid) or sid in source_by_id:
                issues.append(f"invalid_or_duplicate_source_id:{sid}")
            source_by_id[sid] = row
        try:
            _url(row["Canonical URL"], f"source:{sid}")
        except ValidationError as exc:
            issues.append(str(exc))
        if row["Canonical URL"] in url_to_id:
            issues.append(f"duplicate_source_url:{row['Canonical URL']}")
        url_to_id[row["Canonical URL"]] = sid
        if row["Source Position"] not in SOURCE_POSITIONS or row["Source Status / Lifecycle"] not in SOURCE_STATUSES or row["Access State"] not in ACCESS or row["Adoption Status"] not in ADOPTION:
            issues.append(f"invalid_source_enum:{sid}")
        _date(row["Checked At"], f"source:{sid}") if DATE.fullmatch(row["Checked At"]) else issues.append(f"invalid_source_date:{sid}")
        if row["Adoption Status"] in {"adopted", "reference-only", "replaced"} and sid == "-":
            issues.append(f"tracked_source_missing_id:{row['Name']}")
        if row["Adoption Status"] in {"unavailable", "rejected"} and sid != "-":
            issues.append(f"untracked_source_has_id:{row['Name']}")
        try:
            _unescape_list(row["Coverage Axes"])
        except ValidationError as exc:
            issues.append(f"source:{sid}:{exc}")
        for required in ("Name", "Publisher / Owner", "Category", "Platform / Product Scope", "License / Terms", "Note"):
            if not row[required] or row[required] == "-":
                issues.append(f"source_missing:{sid}:{required}")

    known_source_ids = set(source_by_id)
    item_by_id: dict[str, dict[str, str]] = {}
    for row in items:
        item_ref = row["Source Item Ref"]
        match = ITEM_ID.fullmatch(item_ref)
        if not match or item_ref in item_by_id or match.group(1) != row["Source ID"]:
            issues.append(f"invalid_or_duplicate_source_item_ref:{item_ref}")
        if row["Source ID"] not in known_source_ids:
            issues.append(f"unresolved_item_source:{item_ref}")
        item_by_id[item_ref] = row
        try:
            _url(row["Document Canonical URL"], f"item:{item_ref}")
        except ValidationError as exc:
            issues.append(str(exc))
        if row["Locator Type"] not in LOCATOR:
            issues.append(f"invalid_locator_type:{item_ref}")
        elif (row["Locator Type"] == "none") != (row["Locator"] == "-"):
            issues.append(f"locator_type_value_mismatch:{item_ref}")
        if row["Disposition"] not in DISPOSITION or row["Access State"] not in ACCESS or row["Source Status / Lifecycle"] not in SOURCE_STATUSES or row["Semantic Validation"] not in SEMANTIC:
            issues.append(f"invalid_item_enum:{item_ref}")
        if row["Disposition"] in {"included", "merged-duplicate"}:
            try:
                available = _unescape_list(row["Available Dimensions"])
                captured = _unescape_list(row["Captured Dimensions"])
                if available != captured:
                    issues.append(f"dimension_coverage_mismatch:{item_ref}")
            except ValidationError as exc:
                issues.append(f"item:{item_ref}:{exc}")
            if row["Semantic Validation"] != "pass":
                issues.append(f"included_item_not_semantically_validated:{item_ref}")
            if row["Reference Destination"] == "-":
                issues.append(f"included_item_missing_reference_destination:{item_ref}")
        _date(row["Checked At"], f"item:{item_ref}") if DATE.fullmatch(row["Checked At"]) else issues.append(f"invalid_item_date:{item_ref}")

    ref_entries, ref_errors = _entry_records(references_dir)
    issues.extend(ref_errors)
    known_refs = set(ref_entries)
    for row in candidates:
        try:
            _url(row["Canonical URL"], f"candidate:{row['Candidate Name']}")
        except ValidationError as exc:
            issues.append(str(exc))
        if row["Discovery Origin"] not in ORIGINS or row["Status"] not in CANDIDATE_STATUSES:
            issues.append(f"invalid_candidate_enum:{row['Candidate Name']}")
        _date(row["Checked At"], f"candidate:{row['Candidate Name']}") if DATE.fullmatch(row["Checked At"]) else issues.append(f"invalid_candidate_date:{row['Candidate Name']}")
        if row["Status"] in {"adopted", "reference-only", "replaced"}:
            source = source_by_id.get(row["Source ID"])
            if source is None:
                issues.append(f"candidate_source_unresolved:{row['Candidate Name']}")
            elif source["Canonical URL"] != row["Canonical URL"]:
                issues.append(f"candidate_source_url_mismatch:{row['Candidate Name']}")
        elif row["Source ID"] != "-":
            issues.append(f"unresolved_candidate_has_source_id:{row['Candidate Name']}")
        if row["Status"] == "pending" and not allow_incomplete:
            issues.append(f"pending_candidate:{row['Candidate Name']}")

    query_categories = [row["Discovery Category"] for row in runs]
    if set(query_categories) != {f"Q{i}" for i in range(1, 8)} or len(query_categories) != len(set(query_categories)):
        issues.append("discovery_runs_must_close_Q1_through_Q7_once_each")
    for row in runs:
        if row["Completion"] not in COMPLETION or not row["Retrieval Boundary"] or not row["Checked Scope"]:
            issues.append(f"discovery_run_incomplete:{row['Discovery Category']}")
        if not row["Checked Count"].isdigit() or not row["New Candidate Count"].isdigit():
            issues.append(f"discovery_run_count_invalid:{row['Discovery Category']}")
        if row["Completion"] == "blocked" and row["Block Reason"] in {"", "-"}:
            issues.append(f"discovery_run_block_reason_missing:{row['Discovery Category']}")
    for row in coverage_rows:
        if row["Coverage Status"] not in COVERAGE_STATUS:
            issues.append(f"invalid_coverage_status:{row['Coverage Axis']}")
        _date(row["Checked At"], f"coverage:{row['Coverage Axis']}") if DATE.fullmatch(row["Checked At"]) else issues.append(f"invalid_coverage_date:{row['Coverage Axis']}")
        if row["Coverage Status"] == "blocked" and not allow_incomplete:
            issues.append(f"blocked_coverage:{row['Coverage Axis']}")
        try:
            selected_sources = _unescape_list(row["Selected Source Refs"])
            selected_refs = _unescape_list(row["Reference Entry Refs"])
            issues.extend(f"coverage_source_unresolved:{value}" for value in selected_sources if value not in known_source_ids)
            issues.extend(f"coverage_reference_unresolved:{value}" for value in selected_refs if value not in known_refs)
        except ValidationError as exc:
            issues.append(f"coverage:{row['Coverage Axis']}:{exc}")
        if row["Coverage Status"] == "not-applicable" and row["Gap / Reason"] in {"", "-"}:
            issues.append(f"not_applicable_reason_missing:{row['Coverage Axis']}")
        if row["Coverage Status"] == "covered" and row["Selected Source Refs"] == "-" and row["Reference Entry Refs"] == "-":
            issues.append(f"covered_without_source_or_reference:{row['Coverage Axis']}")

    for ref, entry in ref_entries.items():
        if not REF_ID.fullmatch(ref):
            issues.append(f"invalid_reference_id:{ref}")
        for row in entry["rows"]:
            item_ref = row["Source Item Ref"]
            if item_ref not in item_by_id:
                issues.append(f"reference_item_unresolved:{ref}:{item_ref}")
            if row["Source Position"] not in SOURCE_POSITIONS:
                issues.append(f"reference_item_position_invalid:{ref}:{item_ref}")
            if not row["Source Status / Maturity"] or row["Source Status / Maturity"] == "-" or not row["Applicability"] or row["Applicability"] == "-":
                issues.append(f"reference_item_metadata_missing:{ref}:{item_ref}")
    for item_ref, row in item_by_id.items():
        destinations = [] if row["Reference Destination"] == "-" else row["Reference Destination"].split(";")
        for destination in destinations:
            ref, sep, relative = destination.partition(":")
            if not sep or ref not in ref_entries or ref_entries[ref]["path"] != relative:
                issues.append(f"item_destination_unresolved:{item_ref}:{destination}")
            elif not any(source_row["Source Item Ref"] == item_ref for source_row in ref_entries[ref]["rows"]):
                issues.append(f"item_destination_missing_source_row:{item_ref}:{ref}")
        if row["Disposition"] in {"included", "merged-duplicate"} and not destinations:
            issues.append(f"included_item_orphan:{item_ref}")

    issues.extend(_validate_links(references_dir))
    return sorted(set(issues))


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate source and reference catalog contracts.")
    parser.add_argument("--references-dir", type=Path, default=Path(__file__).resolve().parents[1] / "references")
    parser.add_argument("--allow-incomplete", action="store_true", help="Validate structure while planned coverage expansion is in progress.")
    args = parser.parse_args()
    try:
        issues = validate(args.references_dir, allow_incomplete=args.allow_incomplete)
    except (OSError, UnicodeError) as exc:
        print(f"reference catalog validation error: {exc}", file=sys.stderr)
        return 2
    if issues:
        print("reference catalog validation failed:", file=sys.stderr)
        for issue in issues:
            print(f"- {issue}", file=sys.stderr)
        return 1
    print("reference catalog validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
