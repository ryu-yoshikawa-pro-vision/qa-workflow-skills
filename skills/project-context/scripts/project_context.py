"""Project Context discovery and read-only create/update preparation.

This owner uses the existing QA workflow stable-field parser and DEC/ASM lifecycle.
A draft is not a provider write; native CAS, approval and readback are external.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any

SHARED = Path(__file__).resolve().parents[2] / "qa-workflow"
sys.path.insert(0, str(SHARED / "scripts"))

from artifact_graph import (  # noqa: E402
    parse_project_context,
    validate_required_context_fields,
)
from artifact_store import LocalArtifactStore, StoreError  # noqa: E402
from project_context_ids import handle as identity_handle  # noqa: E402

MAX_BYTES = 16 * 1024 * 1024
TEMPLATE = SHARED / "assets" / "project-context-template.md"
HEADING = re.compile(r"^## (\d+)\.\s", re.MULTILINE)
PROJECT = re.compile(r"(?m)^- プロジェクト:[^\n]*$")
START = re.compile(
    r"<!-- qa-context-field:start key=([a-zA-Z0-9_.-]+) "
    r"type=(scalar|path|ordered_text|ordered_lines) -->"
)
END = "<!-- qa-context-field:end -->"


class Invalid(ValueError):
    pass


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise Invalid("duplicate_json_key")
        result[key] = value
    return result


def _text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip() or "\x00" in value:
        raise Invalid(f"{name}_invalid")
    return value


def _single_line(value: Any, name: str) -> str:
    value = _text(value, name)
    if "\n" in value or "\r" in value:
        raise Invalid(f"{name}_multiline")
    return value


def _structure(markdown: str) -> None:
    sections = [int(match.group(1)) for match in HEADING.finditer(markdown)]
    if sections != list(range(1, 17)):
        raise Invalid("project_context_16_sections_required")
    if len(PROJECT.findall(markdown)) != 1:
        raise Invalid("project_identity_ambiguous")
    parsed = parse_project_context(markdown)
    if not parsed["complete"]:
        raise Invalid("stable_key_parse_unresolved")


def _project_name(markdown: str) -> str:
    row = PROJECT.findall(markdown)
    if len(row) != 1:
        raise Invalid("project_identity_ambiguous")
    return row[0].split(":", 1)[1].strip()


def _identity_compat(markdown: str) -> str:
    """Adapt legacy two-dash table separators for existing ID validation.

    Validation reads a normalized copy; existing document bytes stay unchanged.
    """
    return re.sub(r"(?m)^(\|\s*)--(\s*\|)", r"\1---\2", markdown)


def _inspection(markdown: str, required_keys: list[str]) -> dict[str, Any]:
    _structure(markdown)
    if not _project_name(markdown):
        raise Invalid("project_identity_missing")
    if not isinstance(required_keys, list) or any(
        not isinstance(v, str) or not v for v in required_keys
    ):
        raise Invalid("required_keys_invalid")
    if len(required_keys) != len(set(required_keys)):
        raise Invalid("required_keys_duplicated")
    parsed = parse_project_context(markdown)
    validation = validate_required_context_fields(parsed, required_keys)
    decisions = identity_handle(
        {
            "operation": "validate-history",
            "previous_artifact_markdown": None,
            "artifact_markdown": _identity_compat(markdown),
        }
    )
    if not decisions["valid"]:
        raise Invalid("dec_asm_structure_invalid")
    return {
        "required": validation,
        "fields": parsed["fields"],
        "decision_ids": decisions["payload"]["decision_ids"],
        "assumption_ids": decisions["payload"]["assumption_ids"],
    }


def inspect(request: dict[str, Any]) -> dict[str, Any]:
    markdown = _text(request.get("markdown"), "markdown")
    required = request.get("required_keys")
    view = _inspection(markdown, required)
    return {
        "status": "current"
        if view["required"]["status"] == "resolved"
        else "incomplete",
        "project_name": _project_name(markdown),
        "required": view["required"],
        "fields": view["fields"],
        "decision_ids": view["decision_ids"],
        "assumption_ids": view["assumption_ids"],
        "artifact_ref": request.get("artifact_ref"),
        "artifact_revision": request.get("artifact_revision"),
    }


def discover(request: dict[str, Any]) -> dict[str, Any]:
    """Use only explicitly enumerated allowed candidate refs, never scan a host."""
    project = _single_line(request.get("project_name"), "project_name")
    if request.get("enumeration_complete") is not True:
        return {"status": "unconfirmed", "reasons": ["authorized_scope_not_exhausted"]}
    candidates = request.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        raise Invalid("candidate_scope_required")
    paths: set[str] = set()
    current: list[dict[str, str]] = []
    issues: list[str] = []
    for row in candidates:
        if not isinstance(row, dict):
            raise Invalid("candidate_row_invalid")
        ref = _text(row.get("ref"), "candidate_ref")
        if ref in paths:
            raise Invalid("duplicate_candidate_ref")
        paths.add(ref)
        status = row.get("status")
        if status not in {"readable", "absent", "denied", "unavailable"}:
            raise Invalid("candidate_status_invalid")
        if status != "readable":
            if status != "absent":
                issues.append(f"cannot_confirm:{ref}")
            continue
        markdown = _text(row.get("markdown"), "candidate_markdown")
        revision = _text(row.get("revision"), "candidate_revision")
        _inspection(markdown, [])
        if _project_name(markdown) != project:
            issues.append(f"project_identity_mismatch:{ref}")
            continue
        current.append({"ref": ref, "revision": revision})
    if len(current) > 1:
        return {
            "status": "ambiguous",
            "reasons": ["multiple_canonical_candidates"],
            "candidates": current,
        }
    if issues:
        return {"status": "unconfirmed", "reasons": issues, "candidates": current}
    if current:
        return {"status": "existing", "reasons": [], "candidate": current[0]}
    return {
        "status": "absent",
        "reasons": [],
        "authorized_candidate_refs": sorted(paths),
    }


def _apply_sections(markdown: str, updates: Any) -> str:
    """Replace only named human-readable sections, preserving DEC/ASM and graph."""
    if not isinstance(updates, dict) or not updates:
        raise Invalid("section_updates_required")
    numbers: dict[int, str] = {}
    for raw_number, body in updates.items():
        if not isinstance(raw_number, str) or not raw_number.isdigit():
            raise Invalid("section_key_invalid")
        number = int(raw_number)
        if number not in {*range(1, 12), 15} or number in numbers:
            raise Invalid("section_not_editable")
        if not isinstance(body, str) or not body.strip():
            raise Invalid("section_content_invalid")
        if (
            "<!--" in body
            or "-->" in body
            or "\x00" in body
            or re.search(r"(?m)^## \d+\.\s", body)
        ):
            raise Invalid("section_content_unsafe")
        numbers[number] = body.strip("\n")
    original_project = _project_name(markdown)
    lines = markdown.splitlines(keepends=True)
    for number in sorted(numbers, reverse=True):
        heading = re.compile(rf"^## {number}\.\s")
        start = next((i for i, line in enumerate(lines) if heading.match(line)), None)
        if start is None:
            raise Invalid("section_missing")
        following = next(
            (i for i in range(start + 1, len(lines)) if HEADING.match(lines[i])),
            len(lines),
        )
        body_lines = [value + "\n" for value in numbers[number].split("\n")]
        lines[start + 1 : following] = ["\n", *body_lines, "\n"]
    edited = "".join(lines)
    _inspection(edited, [])
    if _project_name(edited) != original_project:
        raise Invalid("project_identity_changed")
    return edited


def prepare_sections(request: dict[str, Any]) -> dict[str, Any]:
    """Prepare scoped human-readable field edits without rewriting unrelated data."""
    markdown = _text(request.get("markdown"), "markdown")
    _inspection(markdown, [])
    artifact_ref = _single_line(request.get("artifact_ref"), "artifact_ref")
    expected_revision = _single_line(
        request.get("expected_revision"), "expected_revision"
    )
    source_ref = _single_line(request.get("source_ref"), "source_ref")
    source_revision = _single_line(request.get("source_revision"), "source_revision")
    change_reason = _single_line(request.get("change_reason"), "change_reason")
    candidate = _apply_sections(markdown, request.get("section_updates"))
    history = identity_handle(
        {
            "operation": "validate-history",
            "previous_artifact_markdown": _identity_compat(markdown),
            "artifact_markdown": _identity_compat(candidate),
        }
    )
    if not history["valid"]:
        raise Invalid("dec_asm_history_invalid")
    return {
        "status": "draft",
        "artifact_ref": artifact_ref,
        "expected_revision": expected_revision,
        "artifact_markdown": candidate,
        "source_ref": source_ref,
        "source_revision": source_revision,
        "change_reason": change_reason,
        "reason": "provider_native_cas_and_approval_required",
    }


def prepare_create(request: dict[str, Any]) -> dict[str, Any]:
    project = _single_line(request.get("project_name"), "project_name")
    discovery = discover(
        {
            "project_name": project,
            "enumeration_complete": request.get("enumeration_complete"),
            "candidates": request.get("candidates"),
        }
    )
    if discovery["status"] != "absent":
        return {
            "status": "blocked",
            "reason": "existing_or_unconfirmed_context",
            "discovery": discovery,
        }
    artifact_ref = request.get("artifact_ref")
    if artifact_ref is not None and artifact_ref not in discovery["authorized_candidate_refs"]:
        raise Invalid("artifact_ref_absence_not_confirmed")
    template = TEMPLATE.read_text(encoding="utf-8")
    if len(PROJECT.findall(template)) != 1:
        raise Invalid("shared_template_identity_invalid")
    markdown = _identity_compat(
        PROJECT.sub(lambda _: "- プロジェクト: " + project, template)
    )
    _inspection(markdown, [])
    if request.get("section_updates") is not None:
        markdown = _apply_sections(markdown, request["section_updates"])
    return {
        "status": "draft",
        "artifact_markdown": markdown,
        "reason": "provider_create_if_absent_and_placement_approval_required",
        "resume_skill": "project-context",
    }


def prepare_update(request: dict[str, Any]) -> dict[str, Any]:
    markdown = _text(request.get("markdown"), "markdown")
    _inspection(markdown, [])
    _text(request.get("artifact_ref"), "artifact_ref")
    _text(request.get("expected_revision"), "expected_revision")
    _text(request.get("source_ref"), "source_ref")
    _text(request.get("source_revision"), "source_revision")
    change_reason = _text(request.get("change_reason"), "change_reason")
    updates = request.get("updates")
    if not isinstance(updates, dict) or not updates:
        raise Invalid("updates_required")
    modified = markdown
    parsed = parse_project_context(markdown)["fields"]
    for key, value in updates.items():
        if key not in parsed:
            raise Invalid(f"unknown_stable_field:{key}")
        if not isinstance(value, str) or "<!--" in value or "-->" in value:
            raise Invalid(f"unsafe_field_value:{key}")
        if any(ord(char) < 32 and char not in "\r\n\t" for char in value):
            raise Invalid(f"control_character_in_field:{key}")
        kind = parsed[key]["type"]
        if kind in {"scalar", "path"} and ("\n" in value or "\r" in value):
            raise Invalid(f"single_line_field_required:{key}")
        if kind == "path" and value.strip() not in {"", "UNKNOWN", "N/A", "（未設定）"}:
            if (
                PurePosixPath(value).is_absolute()
                or PureWindowsPath(value).drive
                or PureWindowsPath(value).is_absolute()
                or value.startswith("~")
                or re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", value)
                or ".." in re.split(r"[/\\\\]", value)
            ):
                raise Invalid(f"project_local_path_required:{key}")
        start = f"<!-- qa-context-field:start key={key} type={kind} -->"
        if modified.count(start) != 1:
            raise Invalid(f"ambiguous_field:{key}")
        open_at = modified.index(start) + len(start)
        close_at = modified.find(END, open_at)
        if close_at < 0:
            raise Invalid(f"missing_field_end:{key}")
        if START.search(modified, open_at, close_at):
            raise Invalid(f"nested_field:{key}")
        modified = modified[:open_at] + "\n\n" + value + "\n\n" + modified[close_at:]
    _inspection(modified, [])
    historic = identity_handle(
        {
            "operation": "validate-history",
            "previous_artifact_markdown": _identity_compat(markdown),
            "artifact_markdown": _identity_compat(modified),
        }
    )
    if not historic["valid"]:
        raise Invalid("dec_asm_history_invalid")
    return {
        "status": "draft",
        "artifact_markdown": modified,
        "changed_keys": sorted(updates),
        "expected_revision": request["expected_revision"],
        "artifact_ref": request["artifact_ref"],
        "change_reason": change_reason,
        "source_ref": request["source_ref"],
        "source_revision": request["source_revision"],
        "reason": "provider_native_cas_history_and_readback_required",
        "resume_skill": "project-context",
    }


def _id_table_lines(markdown: str, section: int) -> tuple[list[str], int, int]:
    """Locate the single DEC/ASM ID table without discarding surrounding prose."""
    lines = markdown.splitlines(keepends=True)
    heading = re.compile(rf"^## {section}\.\s")
    next_heading = re.compile(rf"^## {section + 1}\.\s")
    starts = [i for i, line in enumerate(lines) if heading.match(line)]
    if len(starts) != 1:
        raise Invalid("id_table_section_ambiguous")
    start = starts[0]
    end = next(
        (i for i in range(start + 1, len(lines)) if next_heading.match(lines[i])),
        len(lines),
    )
    indices = [
        i for i in range(start + 1, end) if lines[i].lstrip().startswith("| ID |")
    ]
    if len(indices) != 1:
        raise Invalid("id_table_ambiguous")
    first = indices[0]
    last = first
    while last < end and lines[last].lstrip().startswith("|"):
        last += 1
    if last <= first + 1:
        raise Invalid("id_table_missing_separator")
    return lines, first, last


def _overlay_id_tables(original: str, materialized: str) -> str:
    """Retain existing narratives and other sections, replacing only ID rows."""
    merged = original
    for section in (13, 12):
        base_lines, first, last = _id_table_lines(merged, section)
        new_lines, new_first, new_last = _id_table_lines(materialized, section)
        merged = "".join(
            base_lines[:first] + new_lines[new_first:new_last] + base_lines[last:]
        )
    return merged


def prepare_ids(request: dict[str, Any]) -> dict[str, Any]:
    """Delegate DEC/ASM allocation to the legacy owner helper; return a draft."""
    markdown = _text(request.get("markdown"), "markdown")
    _inspection(markdown, [])
    if request.get("dec_asm_owner") != "project-context":
        raise Invalid("dec_asm_owner_not_confirmed")
    mode = request.get("artifact_mode")
    if mode not in {"create", "update"}:
        raise Invalid("artifact_mode_invalid")
    artifact_ref = _text(request.get("artifact_ref"), "artifact_ref")
    source_ref = _text(request.get("source_ref"), "source_ref")
    source_revision = _text(request.get("source_revision"), "source_revision")
    reason = _text(request.get("change_reason"), "change_reason")
    expected = request.get("expected_revision")
    if mode == "update":
        _text(expected, "expected_revision")
    elif expected is not None:
        raise Invalid("create_must_not_have_expected_revision")
    decisions = request.get("decisions")
    assumptions = request.get("assumptions")
    result = identity_handle(
        {
            "operation": "materialize",
            "artifact_mode": mode,
            "previous_artifact_markdown": (
                _identity_compat(markdown) if mode == "update" else None
            ),
            "artifact_markdown": _identity_compat(markdown),
            "decisions": decisions,
            "assumptions": assumptions,
        }
    )
    if not result["valid"]:
        raise Invalid("dec_asm_materialize_invalid")
    merged = _overlay_id_tables(markdown, result["payload"]["artifact_markdown"])
    _inspection(merged, [])
    check = identity_handle(
        {
            "operation": "validate-history",
            "previous_artifact_markdown": (
                _identity_compat(markdown) if mode == "update" else None
            ),
            "artifact_markdown": _identity_compat(merged),
        }
    )
    if not check["valid"]:
        raise Invalid("dec_asm_history_invalid")
    return {
        "status": "draft",
        "artifact_ref": artifact_ref,
        "artifact_mode": mode,
        "expected_revision": expected,
        "artifact_markdown": merged,
        "allocated_ids": result["payload"]["allocated_ids"],
        "decision_ids": check["payload"]["decision_ids"],
        "assumption_ids": check["payload"]["assumption_ids"],
        "source_ref": source_ref,
        "source_revision": source_revision,
        "change_reason": reason,
        "reason": "provider_atomic_write_history_and_readback_required",
    }


def placement(request: dict[str, Any]) -> dict[str, Any]:
    """Identify reuse vs approval; trust is established by a separate provider."""
    owner = _single_line(request.get("owner"), "owner")
    scope = _single_line(request.get("scope"), "scope")
    target = _single_line(request.get("target_ref"), "target_ref")
    existing = request.get("existing_policy")
    if not isinstance(existing, dict):
        return {"status": "approval_required", "reason": "placement_policy_missing"}
    if (
        existing.get("owner") != owner
        or existing.get("scope") != scope
        or existing.get("target_ref") != target
    ):
        return {"status": "approval_required", "reason": "placement_policy_changed"}
    _text(existing.get("revision"), "policy_revision")
    _text(existing.get("approval_ref"), "policy_approval_ref")
    return {
        "status": "reuse_candidate",
        "policy_revision": existing["revision"],
        "approval_ref": existing["approval_ref"],
        "reason": "trusted_approval_and_current_scope_must_be_verified",
    }


def _active_placement_decisions(markdown: str, scope: str) -> list[str]:
    lines, first, last = _id_table_lines(markdown, 12)
    active: list[str] = []
    for raw in lines[first + 2 : last]:
        cells = [cell.strip() for cell in raw.strip().strip("|").split("|")]
        if (
            len(cells) == 9
            and cells[1] == "QA成果物配置・人間編集方針"
            and cells[2] == "有効"
            and cells[4] == scope
        ):
            active.append(cells[0])
    if len(active) > 1:
        raise Invalid("multiple_active_placement_decisions")
    return active


def _placement_reference(markdown: str, scope: str) -> str | None:
    lines = markdown.splitlines()
    start = next(
        (i for i, line in enumerate(lines) if line.startswith("## 14. ")), None
    )
    end = next(
        (i for i, line in enumerate(lines) if line.startswith("## 15. ")), None
    )
    if start is None or end is None:
        raise Invalid("section_14_missing")
    relevant = [
        [cell.strip() for cell in line.strip().strip("|").split("|")]
        for line in lines[start + 1 : end]
        if line.startswith("| QA成果物配置 |")
    ]
    matching = [cells for cells in relevant if len(cells) == 5 and cells[2] == scope]
    if len(matching) > 1:
        raise Invalid("multiple_placement_references")
    if not matching:
        return None
    return matching[0][1] + "|" + matching[0][4]


def prepare_placement(request: dict[str, Any]) -> dict[str, Any]:
    """Draft one approved placement decision and its Section 14 reference."""
    markdown = _text(request.get("markdown"), "markdown")
    _inspection(markdown, [])
    if request.get("dec_asm_owner") != "project-context":
        raise Invalid("dec_asm_owner_not_confirmed")
    policy = request.get("policy")
    if not isinstance(policy, dict):
        raise Invalid("placement_policy_required")
    required = (
        "owner",
        "scope",
        "target_ref",
        "revision",
        "approval_ref",
        "approval_revision",
        "editable_scope",
        "feature_index_ref",
    )
    if set(policy) != set(required):
        raise Invalid("placement_policy_schema_invalid")
    safe: dict[str, str] = {}
    for key in required:
        value = _single_line(policy[key], key)
        if "|" in value or "<!--" in value or "-->" in value:
            raise Invalid(f"unsafe_placement_field:{key}")
        safe[key] = value
    if safe["scope"] != _project_name(markdown):
        raise Invalid("placement_project_scope_mismatch")
    active = _active_placement_decisions(markdown, safe["scope"])
    original_reference = _placement_reference(markdown, safe["scope"])
    existing = request.get("existing_policy")
    active_id = active[0] if active else None
    if bool(active_id) != bool(original_reference):
        raise Invalid("placement_decision_reference_inconsistent")
    if active_id is not None:
        if not isinstance(existing, dict) or existing.get("decision_id") != active_id:
            raise Invalid("existing_placement_policy_unconfirmed")
        if not original_reference.endswith(";" + active_id):
            # The Section 14 text contains the DEC ID before owner metadata.
            if f"{active_id};" not in original_reference:
                raise Invalid("existing_placement_reference_mismatch")
    elif existing is not None:
        raise Invalid("placement_reuse_not_backed_by_context")
    if existing is not None:
        reused = placement(
            {
                "owner": safe["owner"],
                "scope": safe["scope"],
                "target_ref": safe["target_ref"],
                "existing_policy": existing,
            }
        )
        if reused["status"] == "reuse_candidate" and all(
            existing.get(key) == safe[key] for key in required
        ):
            if not original_reference.startswith(safe["target_ref"] + "|"):
                raise Invalid("placement_reference_mismatch")
            return reused
    mode = "update"
    revision = _text(request.get("expected_revision"), "expected_revision")
    decision = {
        "draft_key": "placement-policy",
        "identity_action": "new",
        "reuse_id": None,
        "cells": {
            "確定内容": "QA成果物配置・人間編集方針",
            "状態": "有効",
            "決定根拠": safe["approval_ref"],
            "影響範囲": safe["scope"],
            "関係": "独立",
            "関連仕様根拠ID": "",
            "置換先ID": "",
            "備考": (
                f"owner={safe['owner']}; target={safe['target_ref']}; "
                f"policy={safe['revision']}; editable={safe['editable_scope']}; "
                f"index={safe['feature_index_ref']}"
            ),
        },
    }
    previous_decisions = request.get("existing_decisions", [])
    previous_assumptions = request.get("existing_assumptions", [])
    if not isinstance(previous_decisions, list) or not isinstance(
        previous_assumptions, list
    ):
        raise Invalid("existing_dec_asm_rows_invalid")
    prepare_request = {
        "markdown": markdown,
        "artifact_mode": mode,
        "artifact_ref": request.get("artifact_ref"),
        "expected_revision": revision,
        "source_ref": request.get("source_ref"),
        "source_revision": request.get("source_revision"),
        "change_reason": request.get("change_reason"),
        "dec_asm_owner": "project-context",
        "decisions": [*previous_decisions, decision],
        "assumptions": previous_assumptions,
    }
    ids = prepare_ids(prepare_request)
    if ids["status"] != "draft":
        return ids
    decision_id = next(
        row["stable_id"]
        for row in ids["allocated_ids"]
        if row["draft_key"] == "placement-policy"
    )
    if active_id is not None:
        old_decisions = [
            row
            for row in previous_decisions
            if isinstance(row, dict)
            and row.get("identity_action") == "reuse"
            and row.get("reuse_id") == active_id
        ]
        if len(old_decisions) != 1:
            raise Invalid("previous_placement_decision_missing")
        old_decision = old_decisions[0]
        cells = old_decision.get("cells")
        if not isinstance(cells, dict) or cells.get("状態") != "有効":
            raise Invalid("previous_placement_decision_not_active")
        if cells.get("確定内容") != "QA成果物配置・人間編集方針":
            raise Invalid("previous_placement_decision_type_mismatch")
        retired = {
            **old_decision,
            "cells": {**cells, "状態": "置換済み", "置換先ID": decision_id},
        }
        prepare_request["decisions"] = [
            retired if row is old_decision else row for row in previous_decisions
        ] + [decision]
        ids = prepare_ids(prepare_request)
        if ids["status"] != "draft":
            return ids
        if not any(
            row["draft_key"] == "placement-policy"
            and row["stable_id"] == decision_id
            for row in ids["allocated_ids"]
        ):
            raise Invalid("placement_decision_id_changed")
    result = ids["artifact_markdown"]
    lines = result.splitlines(keepends=True)
    section_start = next(
        (i for i, line in enumerate(lines) if line.startswith("## 14. ")), None
    )
    section_end = next(
        (i for i, line in enumerate(lines) if line.startswith("## 15. ")), None
    )
    if section_start is None or section_end is None:
        raise Invalid("section_14_missing")
    header = "| 成果物 | 場所 | 範囲 | 鮮度 / バージョン | 備考 |"
    locations = [
        i for i in range(section_start, section_end) if lines[i].strip() == header
    ]
    if len(locations) != 1:
        raise Invalid("section_14_table_invalid")
    row = (
        f"| QA成果物配置 | {safe['target_ref']} | {safe['scope']} | "
        f"{safe['revision']} | {decision_id}; "
        f"owner={safe['owner']}; edit={safe['editable_scope']}; "
        f"index={safe['feature_index_ref']} |"
    )
    matching = [
        i
        for i in range(locations[0] + 2, section_end)
        if lines[i].startswith("| QA成果物配置 |")
        and f"| {safe['scope']} |" in lines[i]
    ]
    if len(matching) > 1:
        raise Invalid("multiple_placement_references")
    if matching:
        lines[matching[0]] = row + "\n"
    else:
        lines.insert(locations[0] + 2, row + "\n")
    candidate = "".join(lines)
    _inspection(candidate, [])
    return {
        "status": "draft",
        "artifact_mode": "update",
        "artifact_ref": request["artifact_ref"],
        "expected_revision": revision,
        "artifact_markdown": candidate,
        "decision_id": decision_id,
        "policy_revision": safe["revision"],
        "approval_ref": safe["approval_ref"],
        "approval_revision": safe["approval_revision"],
        "source_ref": request["source_ref"],
        "source_revision": request["source_revision"],
        "change_reason": request["change_reason"],
        "reason": "trusted_approval_and_provider_cas_required",
    }


def persist_prepared(
    store: LocalArtifactStore,
    preparation: dict[str, Any],
    *,
    project_ref: str,
    operation_id: str,
    approval_ref: str,
    approval_revision: str,
) -> dict[str, Any]:
    """Persist only a freshly prepared candidate through an authorized store.

    The caller must be a trusted application; the public JSON CLI cannot
    grant itself approval by attaching an arbitrary approval_ref.
    """
    try:
        operation = preparation.get("operation")
        if operation not in {
            "prepare-create",
            "prepare-update",
            "prepare-ids",
            "prepare-placement",
            "prepare-sections",
        }:
            raise Invalid("unsupported_persistence_operation")
        draft = handle(preparation)
        if operation == "prepare-create":
            target = _single_line(preparation.get("artifact_ref"), "artifact_ref")
            candidates = preparation.get("candidates")
            if not isinstance(candidates, list) or not any(
                isinstance(row, dict)
                and row.get("ref") == target
                and row.get("status") == "absent"
                for row in candidates
            ):
                raise Invalid("artifact_ref_absence_not_confirmed")
        if operation == "prepare-placement" and draft["status"] == "draft":
            if (
                draft["approval_ref"] != approval_ref
                or draft["approval_revision"] != approval_revision
            ):
                raise Invalid("placement_approval_mismatch")
        if draft["status"] != "draft":
            return draft
        markdown = draft["artifact_markdown"]
        project_ref = _single_line(project_ref, "project_ref")
        if _project_name(markdown) != project_ref:
            raise Invalid("project_scope_mismatch")
        artifact_ref = _single_line(preparation.get("artifact_ref"), "artifact_ref")
        expected = draft.get("expected_revision")
        if expected is not None:
            previous = store.read_revision(
                "project-context", project_ref, artifact_ref, expected
            )
            if previous is None or previous["content"] != preparation.get("markdown"):
                raise Invalid("previous_document_mismatch")
        result = store.write(
            kind="project-context",
            project_ref=project_ref,
            artifact_ref=artifact_ref,
            content=markdown,
            expected_revision=expected,
            operation_id=operation_id,
            source_ref=preparation.get("source_ref"),
            source_revision=preparation.get("source_revision"),
            approval_ref=approval_ref,
            approval_revision=approval_revision,
            change_reason=preparation.get("change_reason"),
        )
        result["project_ref"] = project_ref
        return result
    except (Invalid, StoreError, KeyError, TypeError, ValueError) as exc:
        return {"status": "blocked", "reason": str(exc)}


def handle(request: Any) -> dict[str, Any]:
    try:
        if not isinstance(request, dict):
            raise Invalid("request_invalid")
        op = request.get("operation")
        if op == "inspect":
            return inspect(request)
        if op == "discover":
            return discover(request)
        if op == "prepare-create":
            return prepare_create(request)
        if op == "prepare-update":
            return prepare_update(request)
        if op == "prepare-ids":
            return prepare_ids(request)
        if op == "placement":
            return placement(request)
        if op == "prepare-placement":
            return prepare_placement(request)
        if op == "prepare-sections":
            return prepare_sections(request)
        raise Invalid("operation_invalid")
    except (Invalid, KeyError, ValueError, TypeError, RecursionError) as exc:
        return {"status": "blocked", "reason": str(exc)}


def main() -> int:
    try:
        raw = sys.stdin.buffer.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise Invalid("input_too_large")
        result = handle(json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs))
    except (Invalid, UnicodeDecodeError, json.JSONDecodeError, RecursionError) as exc:
        result = {"status": "blocked", "reason": str(exc)}
    sys.stdout.write(json.dumps(result, ensure_ascii=False, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
