"""Project Context discovery and read-only create/update preparation.

This owner uses the existing QA workflow stable-field parser and DEC/ASM lifecycle.
A draft is not a provider write; native CAS, approval and readback are external.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

SHARED = Path(__file__).resolve().parents[2] / "qa-workflow"
sys.path.insert(0, str(SHARED / "scripts"))

from artifact_graph import (  # noqa: E402
    parse_project_context,
    validate_required_context_fields,
)
from project_context_ids import handle as identity_handle  # noqa: E402

MAX_BYTES = 16 * 1024 * 1024
TEMPLATE = SHARED / "assets" / "project-context-template.md"
HEADING = re.compile(r"^## ([1-9]|1[0-6])\.\s", re.MULTILINE)
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
        _structure(markdown)
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
    template = TEMPLATE.read_text(encoding="utf-8")
    if len(PROJECT.findall(template)) != 1:
        raise Invalid("shared_template_identity_invalid")
    markdown = _identity_compat(
        PROJECT.sub(lambda _: "- プロジェクト: " + project, template)
    )
    _inspection(markdown, [])
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
        kind = parsed[key]["type"]
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
        "source_ref": request["source_ref"],
        "source_revision": request["source_revision"],
        "reason": "provider_native_cas_history_and_readback_required",
        "resume_skill": "project-context",
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
        if op == "placement":
            return placement(request)
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
