#!/usr/bin/env python3
"""Deterministic source/reference catalog materializer for usability-evaluation.

Semantic choices are supplied as normalized decisions. This module owns package
IDs, table enums/order, source/item/reference links, and canonical Markdown.
It performs no network access and does not infer meaning from prose.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
REFERENCES_ROOT = PACKAGE_ROOT / "references"
SOURCE_RE = re.compile(r"^SRC-(\d{3,})$")
ITEM_RE = re.compile(r"^(SRC-\d{3,})-ITEM-(\d{4,})$")
REF_RE = re.compile(r"^REF-(\d{4,})$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
SOURCE_POSITIONS = {"normative", "informative", "advisory", "methodology"}
SOURCE_STATUSES = {"current", "draft", "proposed", "archived", "superseded", "unknown"}
ACCESS_STATES = {"public", "restricted", "unavailable"}
ADOPTION_STATUSES = {"adopted", "reference-only", "replaced", "unavailable", "rejected"}
CANDIDATE_STATUSES = {"pending", "adopted", "reference-only", "rejected", "duplicate", "unavailable", "replaced"}
DISCOVERY_ORIGINS = {"seed", "query", "cross-link"}
COMPLETIONS = {"completed", "blocked"}
COVERAGE_STATUSES = {"covered", "not-applicable", "blocked"}
DISPOSITIONS = {"included", "merged-duplicate", "reference-only", "unavailable", "out-of-scope"}
LOCATOR_TYPES = {"none", "fragment", "section-id", "heading", "page"}
SEMANTIC_VALIDATION = {"pass", "fail", "not-required"}

SOURCE_COLUMNS = [
    "Source ID", "Name", "Canonical URL", "Publisher / Owner", "Category",
    "Source Position", "Platform / Product Scope", "Source Status / Lifecycle",
    "Access State", "Checked At", "Adoption Status", "License / Terms",
    "Coverage Axes", "Note",
]
CANDIDATE_COLUMNS = [
    "Candidate Name", "Canonical URL", "Discovery Origin", "Discovery Detail",
    "Coverage Gap", "Status", "Reason", "Checked At", "Source ID",
]
DISCOVERY_COLUMNS = [
    "Discovery Type", "Discovery Target", "Discovery Category", "Checked At",
    "Checked Scope", "Checked Count", "New Candidate Count", "Retrieval Boundary",
    "Completion", "Block Reason",
]
COVERAGE_COLUMNS = [
    "Coverage Axis", "Concern / Pattern Family", "Required Source Position",
    "Selected Source Refs", "Reference Entry Refs", "Coverage Status", "Gap / Reason",
    "Checked At",
]
ITEM_COLUMNS = [
    "Source ID", "Source Item Ref", "Name / Section", "Document Canonical URL",
    "Locator Type", "Locator", "Disposition", "Access State", "Source Status / Lifecycle",
    "Reference Destination", "Available Dimensions", "Captured Dimensions",
    "Semantic Validation", "Checked At",
]
ENTRY_SOURCE_COLUMNS = ["Source Item Ref", "Source Position", "Source Status / Maturity", "Applicability"]


class CatalogError(ValueError):
    pass


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _json_load(path: Path) -> Any:
    try:
        raw = path.read_bytes()
        value = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise CatalogError(f"invalid_json:{path}") from exc
    return value


def _need(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CatalogError(f"required_string:{label}")
    return value.strip()


def _enum(value: Any, allowed: set[str], label: str) -> str:
    text = _need(value, label)
    if text not in allowed:
        raise CatalogError(f"invalid_enum:{label}:{text}")
    return text


def normalize_url(url: str) -> str:
    """Normalize URL syntax only; fragment and identity-changing details are rejected/preserved."""
    value = _need(url, "url")
    try:
        parts = urlsplit(value)
        if parts.scheme.lower() not in {"http", "https"} or not parts.hostname:
            raise CatalogError("url_must_be_absolute_http_or_https")
        if parts.username is not None or parts.password is not None:
            raise CatalogError("url_userinfo_forbidden")
        if parts.fragment:
            raise CatalogError("fragment_must_be_a_source_item_locator")
        port = parts.port
    except CatalogError:
        raise
    except ValueError as exc:
        raise CatalogError("invalid_url") from exc
    host = parts.hostname.lower()
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"
    default = (parts.scheme.lower() == "http" and port == 80) or (parts.scheme.lower() == "https" and port == 443)
    netloc = host if port is None or default else f"{host}:{port}"
    return urlunsplit((parts.scheme.lower(), netloc, parts.path or "/", parts.query, ""))


def escape_cell(value: Any) -> str:
    if value is None or value == "":
        return "-"
    text = str(value).replace("\\", "\\\\").replace("|", "\\|")
    return text.replace("\r\n", " ").replace("\r", " ").replace("\n", " ").strip() or "-"


def encode_list(values: Any, label: str) -> str:
    if values is None or values == []:
        return "-"
    if not isinstance(values, list) or not all(isinstance(x, str) and x.strip() for x in values):
        raise CatalogError(f"invalid_list:{label}")
    normalized = sorted(set(x.strip() for x in values))
    out = []
    for value in normalized:
        out.append(value.replace("\\", "\\\\").replace(";", "\\;").replace("|", "\\|"))
    return ";".join(out) if out else "-"


def _render_table(columns: list[str], rows: list[dict[str, Any]], *, list_fields: set[str] | None = None) -> str:
    list_fields = list_fields or set()
    head = "| " + " | ".join(columns) + " |"
    rule = "| " + " | ".join("---" for _ in columns) + " |"
    rendered = [head, rule]
    for row in rows:
        cells = []
        for column in columns:
            value = row.get(column)
            cell = encode_list(value, column) if column in list_fields else escape_cell(value)
            cells.append(cell)
        rendered.append("| " + " | ".join(cells) + " |")
    return "\n".join(rendered)


def _split_row(line: str) -> list[str]:
    line = line.strip()
    if not line.startswith("|") or not line.endswith("|"):
        raise CatalogError("malformed_markdown_table_row")
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
    return cells


def _table_after(lines: list[str], heading: str, columns: list[str]) -> list[dict[str, str]]:
    try:
        start = lines.index(heading)
    except ValueError as exc:
        raise CatalogError(f"missing_heading:{heading}") from exc
    i = start + 1
    while i < len(lines) and not lines[i].startswith("|"):
        if lines[i].startswith("## "):
            break
        i += 1
    if i + 1 >= len(lines):
        raise CatalogError(f"missing_table:{heading}")
    actual = _split_row(lines[i])
    if actual != columns:
        raise CatalogError(f"wrong_columns:{heading}")
    if not re.fullmatch(r"\|(?:\s*:?-{3,}:?\s*\|)+", lines[i + 1].strip()):
        raise CatalogError(f"missing_table_rule:{heading}")
    rows: list[dict[str, str]] = []
    i += 2
    while i < len(lines) and lines[i].startswith("|"):
        cells = _split_row(lines[i])
        if len(cells) != len(columns):
            raise CatalogError(f"wrong_cell_count:{heading}")
        rows.append(dict(zip(columns, cells)))
        i += 1
    return rows


def _read_source_rows(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    return _table_after(lines, "## Sources", SOURCE_COLUMNS)


def _read_item_rows(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    return _table_after(lines, "## Source Items", ITEM_COLUMNS)


def _entry_markers(root: Path) -> dict[str, tuple[str, str]]:
    found: dict[str, tuple[str, str]] = {}
    if not root.is_dir():
        return found
    for path in sorted(root.rglob("*.md")):
        lines = path.read_text(encoding="utf-8").splitlines()
        for index, line in enumerate(lines[:-1]):
            match = re.fullmatch(r"<!-- reference-entry-id: (REF-\d{4,}) -->", lines[index + 1].strip())
            if line.startswith("## ") and match:
                identity = match.group(1)
                if identity in found:
                    raise CatalogError(f"duplicate_reference_id:{identity}")
                found[identity] = (path.relative_to(root).as_posix(), line[3:].strip())
    return found


def _max_id(pattern: re.Pattern[str], values: list[str], label: str) -> int:
    numbers = []
    seen: set[str] = set()
    for value in values:
        match = pattern.fullmatch(value)
        if not match or value in seen:
            raise CatalogError(f"malformed_or_duplicate_{label}:{value}")
        seen.add(value)
        numbers.append(int(match.group(1) if len(match.groups()) == 1 else match.group(2)))
    return max(numbers, default=0)


def _load_existing(root: Path) -> tuple[list[dict[str, str]], list[dict[str, str]], dict[str, tuple[str, str]]]:
    return (
        _read_source_rows(root / "source-catalog.md"),
        _read_item_rows(root / "source-coverage.md"),
        _entry_markers(root),
    )


def _validate_date(value: str) -> str:
    if not DATE_RE.fullmatch(value):
        raise CatalogError(f"invalid_checked_at:{value}")
    return value


def _render_reference(path: str, entries: list[dict[str, Any]], item_ref_by_key: dict[str, str], existing_ref_by_name: dict[tuple[str, str], str], next_ref: list[int]) -> tuple[str, list[dict[str, str]]]:
    normalized_entries = sorted(entries, key=lambda entry: (path, _need(entry.get("name"), "reference.name")))
    out = ["# Reference index\n"]
    entry_rows: list[dict[str, str]] = []
    for entry in normalized_entries:
        name = _need(entry.get("name"), "reference.name")
        key = _need(entry.get("key"), "reference.key")
        provided_id = entry.get("existing_reference_id")
        if provided_id is not None:
            if not isinstance(provided_id, str) or not REF_RE.fullmatch(provided_id):
                raise CatalogError("invalid_existing_reference_id")
            ref_id = provided_id
        else:
            ref_id = f"REF-{next_ref[0]:04d}"
            next_ref[0] += 1
        body = entry.get("body", "")
        if not isinstance(body, str):
            raise CatalogError("invalid_reference_body")
        source_rows = []
        source_items = entry.get("source_items", [])
        if not isinstance(source_items, list):
            raise CatalogError(f"invalid_reference_source_items:{key}")
        for item in source_items:
            if not isinstance(item, dict):
                raise CatalogError(f"reference_source_item_not_object:{key}")
            item_key = _need(item.get("item_key"), "reference.source_item.item_key")
            if item_key not in item_ref_by_key:
                raise CatalogError(f"unresolved_reference_item:{item_key}")
            source_rows.append({
                "Source Item Ref": item_ref_by_key[item_key],
                "Source Position": _enum(item.get("source_position"), SOURCE_POSITIONS, "reference.source_position"),
                "Source Status / Maturity": _need(item.get("source_status_maturity"), "reference.source_status_maturity"),
                "Applicability": _need(item.get("applicability"), "reference.applicability"),
            })
        if not source_rows:
            raise CatalogError(f"reference_without_source_item:{key}")
        out.extend([f"## {name}", f"<!-- reference-entry-id: {ref_id} -->", "", body.strip(), "", "### Source Items", _render_table(ENTRY_SOURCE_COLUMNS, source_rows), ""])
        entry_rows.append({"key": key, "name": name, "id": ref_id, "path": path})
    return "\n".join(out).rstrip() + "\n", entry_rows


def materialize(input_value: dict[str, Any], root: Path = REFERENCES_ROOT) -> dict[str, Any]:
    allowed = {"sources", "candidates", "discovery_runs", "coverage", "source_items", "references"}
    unknown = set(input_value) - allowed
    if unknown:
        raise CatalogError(f"unknown_materialize_fields:{','.join(sorted(unknown))}")
    old_sources, old_items, old_entries = _load_existing(root)
    old_source_by_url = {normalize_url(row["Canonical URL"]): row["Source ID"] for row in old_sources}
    old_item_by_identity = {
        (row["Source ID"], normalize_url(row["Document Canonical URL"]), row["Locator Type"], row["Locator"]): row["Source Item Ref"]
        for row in old_items
    }
    old_ref_ids = list(old_entries)
    source_rows_in = input_value.get("sources", [])
    item_rows_in = input_value.get("source_items", [])
    refs_in = input_value.get("references", [])
    for field, data in (("sources", source_rows_in), ("source_items", item_rows_in), ("references", refs_in), ("candidates", input_value.get("candidates", [])), ("discovery_runs", input_value.get("discovery_runs", [])), ("coverage", input_value.get("coverage", []))):
        if not isinstance(data, list):
            raise CatalogError(f"expected_array:{field}")

    sources: list[dict[str, Any]] = []
    source_ids = {key: value for key, value in old_source_by_url.items()}
    used_source_ids = set(source_ids.values())
    source_by_key: dict[str, dict[str, Any]] = {}
    initial_sources = []
    input_url_to_key: dict[str, str] = {}
    for source in source_rows_in:
        if not isinstance(source, dict):
            raise CatalogError("source_not_object")
        key = _need(source.get("key"), "source.key")
        if key in source_by_key:
            raise CatalogError(f"duplicate_source_key:{key}")
        url = normalize_url(source.get("canonical_url"))
        if url in input_url_to_key:
            raise CatalogError(f"duplicate_source_url:{url}")
        input_url_to_key[url] = key
        source_by_key[key] = {**source, "canonical_url": url}
        if url in source_ids:
            source_by_key[key]["source_id"] = source_ids[url]
        elif source.get("existing_source_id"):
            existing_id = _need(source["existing_source_id"], "existing_source_id")
            if not SOURCE_RE.fullmatch(existing_id) or existing_id not in used_source_ids:
                raise CatalogError(f"unknown_existing_source_id:{existing_id}")
            source_by_key[key]["source_id"] = existing_id
        else:
            initial_sources.append((key, url))
    next_source = _max_id(SOURCE_RE, list(used_source_ids), "source_id") + 1
    for key, url in sorted(initial_sources, key=lambda item: item[1]):
        source_by_key[key]["source_id"] = f"SRC-{next_source:03d}"
        used_source_ids.add(source_by_key[key]["source_id"])
        next_source += 1
    for key, source in source_by_key.items():
        source_id = source["source_id"]
        if source_id not in used_source_ids:
            used_source_ids.add(source_id)
        adoption = _enum(source.get("adoption_status"), ADOPTION_STATUSES, f"source.{key}.adoption_status")
        status = _enum(source.get("source_status"), SOURCE_STATUSES, f"source.{key}.source_status")
        access = _enum(source.get("access_state"), ACCESS_STATES, f"source.{key}.access_state")
        position = _enum(source.get("source_position"), SOURCE_POSITIONS, f"source.{key}.source_position")
        if adoption in {"adopted", "reference-only", "replaced"} and not SOURCE_RE.fullmatch(source_id):
            raise CatalogError(f"invalid_source_id:{source_id}")
        row = {
            "Source ID": source_id if adoption in {"adopted", "reference-only", "replaced"} else "-",
            "Name": _need(source.get("name"), f"source.{key}.name"),
            "Canonical URL": source["canonical_url"],
            "Publisher / Owner": _need(source.get("publisher"), f"source.{key}.publisher"),
            "Category": _need(source.get("category"), f"source.{key}.category"),
            "Source Position": position,
            "Platform / Product Scope": _need(source.get("scope"), f"source.{key}.scope"),
            "Source Status / Lifecycle": status,
            "Access State": access,
            "Checked At": _validate_date(_need(source.get("checked_at"), f"source.{key}.checked_at")),
            "Adoption Status": adoption,
            "License / Terms": _need(source.get("license_terms"), f"source.{key}.license_terms"),
            "Coverage Axes": source.get("coverage_axes", []),
            "Note": source.get("note", "-"),
        }
        sources.append(row)
    sources.sort(key=lambda row: (row["Canonical URL"], row["Source ID"]))
    id_by_source_key = {
        key: value.get("source_id") if value.get("adoption_status") in {"adopted", "reference-only", "replaced"} else "-"
        for key, value in source_by_key.items()
    }
    # Existing source IDs and newly assigned IDs must never alias different URLs.
    ids_seen: dict[str, str] = {}
    for key, value in source_by_key.items():
        sid = value.get("source_id")
        if sid and sid != "-":
            if sid in ids_seen and ids_seen[sid] != value["canonical_url"]:
                raise CatalogError(f"source_id_reused:{sid}")
            ids_seen[sid] = value["canonical_url"]
    for sid, url in ids_seen.items():
        old_url = next((known_url for known_url, known_id in old_source_by_url.items() if known_id == sid), None)
        if old_url is not None and old_url != url and old_url in input_url_to_key:
            raise CatalogError(f"source_id_reassigned_while_original_present:{sid}")

    item_ref_by_key: dict[str, str] = {}
    item_rows: list[dict[str, Any]] = []
    new_items: list[tuple[str, str, dict[str, Any]]] = []
    item_identity_to_key: dict[tuple[str, str, str, str], str] = {}
    for item in item_rows_in:
        if not isinstance(item, dict):
            raise CatalogError("source_item_not_object")
        key = _need(item.get("key"), "source_item.key")
        if key in item_ref_by_key:
            raise CatalogError(f"duplicate_source_item_key:{key}")
        source_key = _need(item.get("source_key"), "source_item.source_key")
        if source_key not in source_by_key or id_by_source_key[source_key] == "-":
            raise CatalogError(f"unresolved_source_item_source:{source_key}")
        sid = id_by_source_key[source_key]
        doc_url = normalize_url(item.get("document_url"))
        locator_type = _enum(item.get("locator_type"), LOCATOR_TYPES, f"item.{key}.locator_type")
        locator = "-" if locator_type == "none" else _need(item.get("locator"), f"item.{key}.locator")
        if locator_type == "none" and item.get("locator") not in (None, "", "-"):
            raise CatalogError(f"locator_must_be_empty:{key}")
        identity = (sid, doc_url, locator_type, locator)
        if identity in item_identity_to_key:
            raise CatalogError(f"duplicate_source_item_identity:{key}:{item_identity_to_key[identity]}")
        item_identity_to_key[identity] = key
        if identity in old_item_by_identity:
            item_ref_by_key[key] = old_item_by_identity[identity]
        else:
            new_items.append((key, sid, {**item, "document_url": doc_url, "locator_type": locator_type, "locator": locator}))
    max_item_by_source: dict[str, int] = {}
    for row in old_items:
        m = ITEM_RE.fullmatch(row["Source Item Ref"])
        if not m:
            raise CatalogError(f"malformed_source_item_ref:{row['Source Item Ref']}")
        max_item_by_source[m.group(1)] = max(max_item_by_source.get(m.group(1), 0), int(m.group(2)))
    # Initial items sort within source by canonical document URL, locator, and item name.
    for key, sid, item in sorted(new_items, key=lambda item: (item[1], item[2]["document_url"], item[2]["locator_type"], item[2]["locator"], _need(item[2].get("name"), "source_item.name"))):
        max_item_by_source[sid] = max_item_by_source.get(sid, 0) + 1
        item_ref_by_key[key] = f"{sid}-ITEM-{max_item_by_source[sid]:04d}"
    item_key_by_ref = {ref: key for key, ref in item_ref_by_key.items()}
    for item in item_rows_in:
        key = item["key"]
        sid = id_by_source_key[item["source_key"]]
        disposition = _enum(item.get("disposition"), DISPOSITIONS, f"item.{key}.disposition")
        validation = _enum(item.get("semantic_validation"), SEMANTIC_VALIDATION, f"item.{key}.semantic_validation")
        available = item.get("available_dimensions", [])
        captured = item.get("captured_dimensions", [])
        for label, dimensions in (("available_dimensions", available), ("captured_dimensions", captured)):
            if not isinstance(dimensions, list) or not all(isinstance(value, str) and value.strip() for value in dimensions):
                raise CatalogError(f"invalid_{label}:{key}")
        if disposition in {"included", "merged-duplicate"} and sorted(set(available)) != sorted(set(captured)):
            raise CatalogError(f"dimension_coverage_mismatch:{key}")
        row = {
            "Source ID": sid,
            "Source Item Ref": item_ref_by_key[key],
            "Name / Section": _need(item.get("name"), f"item.{key}.name"),
            "Document Canonical URL": normalize_url(item["document_url"]),
            "Locator Type": item["locator_type"],
            "Locator": item["locator"],
            "Disposition": disposition,
            "Access State": _enum(item.get("access_state"), ACCESS_STATES, f"item.{key}.access_state"),
            "Source Status / Lifecycle": _enum(item.get("source_status"), SOURCE_STATUSES, f"item.{key}.source_status"),
            "Reference Destination": item.get("reference_destination", "-"),
            "Available Dimensions": available,
            "Captured Dimensions": captured,
            "Semantic Validation": validation,
            "Checked At": _validate_date(_need(item.get("checked_at"), f"item.{key}.checked_at")),
        }
        if row["Locator Type"] == "fragment" and not row["Locator"].startswith("#"):
            raise CatalogError(f"fragment_locator_invalid:{key}")
        if row["Disposition"] in {"included", "merged-duplicate"} and validation != "pass":
            raise CatalogError(f"included_item_not_validated:{key}")
        item_rows.append(row)
    item_rows.sort(key=lambda row: (row["Source ID"], row["Document Canonical URL"], row["Locator Type"], row["Locator"], row["Name / Section"]))

    ref_path_rows: dict[str, list[dict[str, Any]]] = {}
    ref_entry_map: dict[str, dict[str, Any]] = {}
    existing_by_path_name = {(path, name): rid for rid, (path, name) in old_entries.items()}
    used_ref_numbers = [int(match.group(1)) for identity in old_ref_ids if (match := REF_RE.fullmatch(identity))]
    next_ref = [max(used_ref_numbers, default=0) + 1]
    seen_paths: set[str] = set()
    for ref_group in refs_in:
        if not isinstance(ref_group, dict):
            raise CatalogError("references_group_not_object")
        relpath = _need(ref_group.get("path"), "references.path").replace("\\", "/")
        if relpath.startswith("/") or ".." in Path(relpath).parts or not relpath.endswith(".md"):
            raise CatalogError(f"invalid_reference_path:{relpath}")
        if relpath in seen_paths:
            raise CatalogError(f"duplicate_reference_path:{relpath}")
        seen_paths.add(relpath)
        entries = ref_group.get("entries")
        if not isinstance(entries, list):
            raise CatalogError(f"invalid_reference_entries:{relpath}")
        ref_path_rows[relpath] = []
        # Keep stable IDs for an existing path/name pair; allocate initial IDs in path/name order below.
        for entry in entries:
            if not isinstance(entry, dict):
                raise CatalogError("reference_entry_not_object")
            pair = (relpath, _need(entry.get("name"), "reference.name"))
            requested_id = entry.get("existing_reference_id")
            if requested_id is not None:
                if not isinstance(requested_id, str) or not REF_RE.fullmatch(requested_id):
                    raise CatalogError("invalid_existing_reference_id")
                if requested_id not in old_entries:
                    raise CatalogError(f"unknown_existing_reference_id:{requested_id}")
            elif pair in existing_by_path_name:
                entry = {**entry, "existing_reference_id": existing_by_path_name[pair]}
            ref_path_rows[relpath].append(entry)
    # Initial IDs must be assigned by final path then entry name, independent of input order.
    used_ref_ids: dict[str, tuple[str, str]] = {}
    for relpath in sorted(ref_path_rows):
        ref_path_rows[relpath].sort(key=lambda row: _need(row.get("name"), "reference.name"))
        for index, entry in enumerate(ref_path_rows[relpath]):
            key = _need(entry.get("key"), "reference.key")
            if key in ref_entry_map:
                raise CatalogError(f"duplicate_reference_key:{key}")
            if not entry.get("existing_reference_id"):
                entry = {**entry, "existing_reference_id": f"REF-{next_ref[0]:04d}"}
                next_ref[0] += 1
                ref_path_rows[relpath][index] = entry
            ref_id = entry.get("existing_reference_id")
            if not isinstance(ref_id, str) or not REF_RE.fullmatch(ref_id):
                raise CatalogError(f"invalid_existing_reference_id:{key}")
            if ref_id in used_ref_ids:
                raise CatalogError(f"duplicate_reference_id:{ref_id}")
            used_ref_ids[ref_id] = (relpath, _need(entry.get("name"), "reference.name"))
            ref_entry_map[key] = {**entry, "path": relpath}
    ref_id_by_key = {key: entry["existing_reference_id"] for key, entry in ref_entry_map.items()}
    for row in item_rows:
        destinations = {
            f"{ref_id_by_key[entry['key']]}:{ref_entry_map[entry['key']]['path']}"
            for group in refs_in
            for entry in group.get("entries", [])
            if entry.get("key") in ref_id_by_key
            for source_item in entry.get("source_items", [])
            if source_item.get("item_key") in item_ref_by_key
            and item_ref_by_key[source_item["item_key"]] == row["Source Item Ref"]
        }
        if destinations:
            row["Reference Destination"] = ";".join(sorted(destinations))
        if row["Disposition"] in {"included", "merged-duplicate"} and row["Reference Destination"] == "-":
            raise CatalogError(f"included_item_missing_reference:{row['Source Item Ref']}")

    catalog_candidates = []
    candidate_urls: set[str] = set()
    for candidate in input_value.get("candidates", []):
        if not isinstance(candidate, dict):
            raise CatalogError("candidate_not_object")
        source_key = candidate.get("source_key")
        source_id = id_by_source_key.get(source_key, "-") if source_key else "-"
        candidate_url = normalize_url(candidate.get("canonical_url"))
        status = _enum(candidate.get("status"), CANDIDATE_STATUSES, "candidate.status")
        if candidate_url in candidate_urls:
            raise CatalogError(f"duplicate_candidate_url:{candidate_url}")
        candidate_urls.add(candidate_url)
        if status in {"adopted", "reference-only", "replaced"}:
            if source_id == "-" or source_by_key[source_key]["canonical_url"] != candidate_url:
                raise CatalogError(f"candidate_source_mismatch:{candidate.get('name')}")
        elif source_id != "-":
            raise CatalogError(f"untracked_candidate_has_source:{candidate.get('name')}")
        catalog_candidates.append({
            "Candidate Name": _need(candidate.get("name"), "candidate.name"),
            "Canonical URL": candidate_url,
            "Discovery Origin": _enum(candidate.get("origin"), DISCOVERY_ORIGINS, "candidate.origin"),
            "Discovery Detail": _need(candidate.get("discovery_detail"), "candidate.discovery_detail"),
            "Coverage Gap": _need(candidate.get("coverage_gap"), "candidate.coverage_gap"),
            "Status": status,
            "Reason": _need(candidate.get("reason"), "candidate.reason"),
            "Checked At": _validate_date(_need(candidate.get("checked_at"), "candidate.checked_at")),
            "Source ID": source_id,
        })
    catalog_candidates.sort(key=lambda row: row["Canonical URL"])
    discovery_rows = []
    for run in input_value.get("discovery_runs", []):
        if not isinstance(run, dict):
            raise CatalogError("discovery_run_not_object")
        count = run.get("checked_count")
        new_count = run.get("new_candidate_count")
        if not isinstance(count, int) or count < 0 or not isinstance(new_count, int) or new_count < 0:
            raise CatalogError("invalid_discovery_count")
        discovery_rows.append({
            "Discovery Type": _need(run.get("type"), "run.type"),
            "Discovery Target": _need(run.get("target"), "run.target"),
            "Discovery Category": _need(run.get("category"), "run.category"),
            "Checked At": _validate_date(_need(run.get("checked_at"), "run.checked_at")),
            "Checked Scope": _need(run.get("checked_scope"), "run.checked_scope"),
            "Checked Count": count,
            "New Candidate Count": new_count,
            "Retrieval Boundary": _need(run.get("retrieval_boundary"), "run.retrieval_boundary"),
            "Completion": _enum(run.get("completion"), COMPLETIONS, "run.completion"),
            "Block Reason": run.get("block_reason", "-"),
        })
    discovery_rows.sort(key=lambda row: (row["Discovery Category"], row["Discovery Type"], row["Discovery Target"]))
    categories = [row["Discovery Category"] for row in discovery_rows]
    if len(categories) != len(set(categories)):
        raise CatalogError("duplicate_discovery_category")
    for row in discovery_rows:
        if row["Completion"] == "blocked" and row["Block Reason"] in {"", "-"}:
            raise CatalogError(f"blocked_discovery_missing_reason:{row['Discovery Category']}")
        if row["Completion"] == "completed" and row["Block Reason"] not in {"", "-"}:
            raise CatalogError(f"completed_discovery_has_block_reason:{row['Discovery Category']}")

    coverage_rows = []
    for cov in input_value.get("coverage", []):
        if not isinstance(cov, dict):
            raise CatalogError("coverage_not_object")
        status = _enum(cov.get("status"), COVERAGE_STATUSES, "coverage.status")
        source_refs = []
        for key in cov.get("source_keys", []):
            if key not in id_by_source_key or id_by_source_key[key] == "-":
                raise CatalogError(f"unresolved_coverage_source:{key}")
            source_refs.append(id_by_source_key[key])
        entry_refs = []
        for key in cov.get("reference_keys", []):
            if key not in ref_id_by_key:
                raise CatalogError(f"unresolved_coverage_reference:{key}")
            entry_refs.append(ref_id_by_key[key])
        coverage_rows.append({
            "Coverage Axis": _need(cov.get("axis"), "coverage.axis"),
            "Concern / Pattern Family": _need(cov.get("concern"), "coverage.concern"),
            "Required Source Position": _enum(cov.get("required_position"), SOURCE_POSITIONS, "coverage.required_position"),
            "Selected Source Refs": sorted(set(source_refs)),
            "Reference Entry Refs": sorted(set(entry_refs)),
            "Coverage Status": status,
            "Gap / Reason": _need(cov.get("gap_reason"), "coverage.gap_reason"),
            "Checked At": _validate_date(_need(cov.get("checked_at"), "coverage.checked_at")),
        })
    coverage_rows.sort(key=lambda row: (row["Coverage Axis"], row["Concern / Pattern Family"]))

    source_catalog = "\n\n".join([
        "# Source catalog",
        "## Sources\n" + _render_table(SOURCE_COLUMNS, sources, list_fields={"Coverage Axes"}),
        "## Candidates\n" + _render_table(CANDIDATE_COLUMNS, catalog_candidates),
        "## Discovery Runs\n" + _render_table(DISCOVERY_COLUMNS, discovery_rows),
    ]) + "\n"
    source_coverage = "\n\n".join([
        "# Source and capability coverage",
        "## Capability Coverage\n" + _render_table(COVERAGE_COLUMNS, coverage_rows, list_fields={"Selected Source Refs", "Reference Entry Refs"}),
        "## Source Items\n" + _render_table(ITEM_COLUMNS, item_rows, list_fields={"Available Dimensions", "Captured Dimensions"}),
    ]) + "\n"
    rendered: dict[str, str] = {
        "source-catalog.md": source_catalog,
        "source-coverage.md": source_coverage,
    }
    for relpath, entries in sorted(ref_path_rows.items()):
        content, entry_rows = _render_reference(relpath, entries, item_ref_by_key, existing_by_path_name, next_ref)
        rendered[relpath] = content
        for row in entry_rows:
            ref_entry_map[row["key"]].update(row)
    # Rewrite coverage refs after the renderer has finalized entry IDs.
    if coverage_rows:
        for cov_input, cov_row in zip(sorted(input_value.get("coverage", []), key=lambda row: (row["axis"], row["concern"])), coverage_rows):
            cov_row["Reference Entry Refs"] = sorted(ref_id_by_key[key] for key in cov_input.get("reference_keys", []))
        source_coverage = "\n\n".join([
            "# Source and capability coverage",
            "## Capability Coverage\n" + _render_table(COVERAGE_COLUMNS, coverage_rows, list_fields={"Selected Source Refs", "Reference Entry Refs"}),
            "## Source Items\n" + _render_table(ITEM_COLUMNS, item_rows, list_fields={"Available Dimensions", "Captured Dimensions"}),
        ]) + "\n"
        rendered["source-coverage.md"] = source_coverage
    if any(row["Status"] == "pending" for row in catalog_candidates):
        pending = sum(row["Status"] == "pending" for row in catalog_candidates)
    else:
        pending = 0
    return {
        "files": {key: value for key, value in sorted(rendered.items())},
        "allocated": {
            "source_ids": {key: id_by_source_key[key] for key in sorted(id_by_source_key)},
            "source_item_refs": {key: item_ref_by_key[key] for key in sorted(item_ref_by_key)},
            "reference_entry_ids": {key: ref_id_by_key[key] for key in sorted(ref_id_by_key)},
        },
        "summary": {
            "pending_candidates": pending,
            "blocked_coverage": sum(row["Coverage Status"] == "blocked" for row in coverage_rows),
            "source_count": len(sources),
            "source_item_count": len(item_rows),
            "reference_entry_count": len(ref_id_by_key),
            "issues": [],
        },
    }


def summary(catalog: Path, coverage: Path, references_dir: Path) -> dict[str, Any]:
    catalog_lines = catalog.read_text(encoding="utf-8").splitlines()
    coverage_lines = coverage.read_text(encoding="utf-8").splitlines()
    sources = _table_after(catalog_lines, "## Sources", SOURCE_COLUMNS)
    candidates = _table_after(catalog_lines, "## Candidates", CANDIDATE_COLUMNS)
    runs = _table_after(catalog_lines, "## Discovery Runs", DISCOVERY_COLUMNS)
    coverage_rows = _table_after(coverage_lines, "## Capability Coverage", COVERAGE_COLUMNS)
    items = _table_after(coverage_lines, "## Source Items", ITEM_COLUMNS)
    refs = _entry_markers(references_dir)
    source_ids = [row["Source ID"] for row in sources if row["Source ID"] != "-"]
    item_ids = [row["Source Item Ref"] for row in items if row["Source Item Ref"] != "-"]
    if len(source_ids) != len(set(source_ids)) or any(not SOURCE_RE.fullmatch(value) for value in source_ids):
        raise CatalogError("invalid_source_ids")
    if len(item_ids) != len(set(item_ids)) or any(not ITEM_RE.fullmatch(value) for value in item_ids):
        raise CatalogError("invalid_source_item_refs")
    ref_ids = list(refs)
    if len(ref_ids) != len(set(ref_ids)) or any(not REF_RE.fullmatch(value) for value in ref_ids):
        raise CatalogError("invalid_reference_ids")
    known_source_ids = set(source_ids)
    known_item_ids = set(item_ids)
    known_ref_ids = set(ref_ids)
    issues: list[str] = []
    for row in items:
        if row["Source ID"] not in known_source_ids:
            issues.append(f"unresolved_item_source:{row['Source Item Ref']}")
        if row["Disposition"] in {"included", "merged-duplicate"} and row["Reference Destination"] == "-":
            issues.append(f"missing_reference_destination:{row['Source Item Ref']}")
        if row["Disposition"] in {"included", "merged-duplicate"} and row["Available Dimensions"] != row["Captured Dimensions"]:
            issues.append(f"dimension_coverage_mismatch:{row['Source Item Ref']}")
    for row in coverage_rows:
        for value in ([] if row["Selected Source Refs"] == "-" else row["Selected Source Refs"].split(";")):
            if value not in known_source_ids:
                issues.append(f"unresolved_coverage_source:{value}")
        for value in ([] if row["Reference Entry Refs"] == "-" else row["Reference Entry Refs"].split(";")):
            if value not in known_ref_ids:
                issues.append(f"unresolved_coverage_reference:{value}")
    for row in candidates:
        if row["Status"] == "pending":
            continue
        if row["Status"] in {"adopted", "reference-only", "replaced"} and row["Source ID"] not in known_source_ids:
            issues.append(f"candidate_missing_source:{row['Candidate Name']}")
    for run in runs:
        if not run["Retrieval Boundary"] or run["Completion"] not in COMPLETIONS:
            issues.append(f"invalid_discovery_run:{run['Discovery Target']}")
    return {
        "pending_candidates": sum(row["Status"] == "pending" for row in candidates),
        "blocked_coverage": sum(row["Coverage Status"] == "blocked" for row in coverage_rows),
        "source_count": len(sources),
        "source_item_count": len(items),
        "reference_entry_count": len(refs),
        "issues": sorted(issues),
    }


def _emit(value: Any) -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.stdout.write(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    normalize = sub.add_parser("normalize-url")
    normalize.add_argument("--url", required=True)
    source = sub.add_parser("next-source-id")
    source.add_argument("--catalog", type=Path, default=REFERENCES_ROOT / "source-catalog.md")
    item = sub.add_parser("next-item-ref")
    item.add_argument("--coverage", type=Path, default=REFERENCES_ROOT / "source-coverage.md")
    item.add_argument("--source-id", required=True)
    reference = sub.add_parser("next-reference-id")
    reference.add_argument("--references-dir", type=Path, default=REFERENCES_ROOT)
    build = sub.add_parser("materialize")
    build.add_argument("--input", type=Path, required=True)
    build.add_argument("--references-dir", type=Path, default=REFERENCES_ROOT)
    build.add_argument("--write", action="store_true")
    sums = sub.add_parser("summary")
    sums.add_argument("--catalog", type=Path, default=REFERENCES_ROOT / "source-catalog.md")
    sums.add_argument("--coverage", type=Path, default=REFERENCES_ROOT / "source-coverage.md")
    sums.add_argument("--references-dir", type=Path, default=REFERENCES_ROOT)
    args = parser.parse_args(argv)
    try:
        if args.command == "normalize-url":
            result = {"canonical_url": normalize_url(args.url)}
        elif args.command == "next-source-id":
            rows = _read_source_rows(args.catalog)
            value = _max_id(SOURCE_RE, [row["Source ID"] for row in rows if row["Source ID"] != "-"], "source_id") + 1
            result = {"source_id": f"SRC-{value:03d}"}
        elif args.command == "next-item-ref":
            if not SOURCE_RE.fullmatch(args.source_id):
                raise CatalogError("invalid_source_id")
            rows = _read_item_rows(args.coverage)
            refs = [row["Source Item Ref"] for row in rows if row["Source ID"] == args.source_id]
            malformed = [value for value in refs if not ITEM_RE.fullmatch(value)]
            if malformed or len(refs) != len(set(refs)):
                raise CatalogError("malformed_or_duplicate_item_ref")
            max_item = max([int(ITEM_RE.fullmatch(value).group(2)) for value in refs], default=0) + 1
            result = {"source_item_ref": f"{args.source_id}-ITEM-{max_item:04d}"}
        elif args.command == "next-reference-id":
            values = list(_entry_markers(args.references_dir))
            max_ref = _max_id(REF_RE, values, "reference_id") + 1
            result = {"reference_entry_id": f"REF-{max_ref:04d}"}
        elif args.command == "materialize":
            input_value = _json_load(args.input)
            if not isinstance(input_value, dict):
                raise CatalogError("materialize_input_must_be_object")
            result = materialize(input_value, args.references_dir)
            if args.write:
                for relative, content in result["files"].items():
                    target = args.references_dir / relative
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text(content, encoding="utf-8", newline="\n")
                result["written"] = True
        else:
            result = summary(args.catalog, args.coverage, args.references_dir)
        _emit(result)
        return 0
    except (CatalogError, OSError) as exc:
        print(f"reference_catalog:{exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
