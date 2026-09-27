"""Deterministic QA workflow identity and project-local coordination helpers.

This module is intentionally skill-local and uses only the Python standard
library. Conditional updates are delegated to a storage provider that can
perform them atomically; this module never simulates CAS with read-then-write.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import uuid
from typing import Any


_FIELD_START = re.compile(
    r"<!--\s*qa-context-field:start\s+key=([a-zA-Z0-9_.-]+)\s+type=(scalar|path|ordered_text|ordered_lines)\s*-->",
    re.IGNORECASE,
)
_FIELD_END = "<!-- qa-context-field:end -->"
_UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")


def _json_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def content_identity(value: Any) -> str:
    return hashlib.sha256(_json_bytes(value)).hexdigest()


def _normalize(value: str, kind: str) -> Any:
    value = value.replace("\r\n", "\n").replace("\r", "\n")
    if kind in {"scalar", "path"}:
        return value.strip()
    if kind == "ordered_text":
        return value.strip()
    if kind == "ordered_lines":
        return [line.strip() for line in value.strip().split("\n") if line.strip()]
    raise ValueError(f"unsupported Project Context field type: {kind}")


def parse_project_context(text: str) -> dict[str, Any]:
    """Resolve explicit stable-key blocks without relying on labels or line numbers."""
    fields: dict[str, dict[str, Any]] = {}
    unresolved: list[dict[str, str]] = []
    cursor = 0
    starts = list(_FIELD_START.finditer(text))
    for match in starts:
        key, kind = match.group(1), match.group(2).lower()
        end = text.find(_FIELD_END, match.end())
        next_start = _FIELD_START.search(text, match.end())
        if end < 0 or (next_start is not None and next_start.start() < end):
            unresolved.append({"key": key, "reason": "missing_or_ambiguous_end_marker"})
            continue
        if key in fields:
            unresolved.append({"key": key, "reason": "duplicate_key"})
            fields.pop(key, None)
            continue
        if any(item["key"] == key and item["reason"] == "duplicate_key" for item in unresolved):
            continue
        normalized = _normalize(text[match.end():end], kind)
        fields[key] = {"type": kind, "value": normalized, "content_identity": content_identity({"type": kind, "value": normalized})}
        cursor = end + len(_FIELD_END)

    if text.count("<!-- qa-context-field:end -->") > len(starts):
        unresolved.append({"key": "<unknown>", "reason": "orphan_end_marker"})
    return {"fields": fields, "unresolved": unresolved, "complete": not unresolved}


def validate_required_context_fields(parsed: dict[str, Any], required_keys: list[str]) -> dict[str, Any]:
    fields = parsed.get("fields", {})
    missing: list[str] = []
    unresolved = list(parsed.get("unresolved", []))
    for key in required_keys:
        item = fields.get(key)
        if item is None:
            missing.append(key)
            continue
        value = item.get("value")
        empty = value in (None, "", [], "UNKNOWN", "N/A", "（未設定）")
        if empty:
            missing.append(key)
    return {"status": "resolved" if not missing and not unresolved else "unresolved", "missing_keys": missing, "unresolved": unresolved}


def compare_used_context(snapshot: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
    """Compare only keys used by a workflow; unrelated field changes do not stale it."""
    unresolved = list(snapshot.get("unresolved", [])) + list(current.get("unresolved", []))
    changed: list[str] = []
    used = snapshot.get("used_fields", [])
    old_fields = snapshot.get("fields", {})
    new_fields = current.get("fields", {})
    for key in used:
        if key not in old_fields or key not in new_fields:
            unresolved.append({"key": str(key), "reason": "missing_or_ambiguous_key"})
            continue
        if old_fields[key].get("content_identity") != new_fields[key].get("content_identity"):
            changed.append(str(key))
    return {"status": "unresolved" if unresolved else ("stale" if changed else "current"), "changed_keys": sorted(set(changed)), "unresolved": unresolved}


def new_workflow_ref() -> str:
    """Return an opaque identifier for a workflow; never a global counter."""
    return str(uuid.uuid4())


def canonical_state_path(workflow_root: str | Path, workflow_ref: str) -> Path:
    value = workflow_ref.lower()
    if not _UUID.fullmatch(value):
        raise ValueError("workflow_ref must be a canonical UUID")
    return Path(workflow_root) / f"{value}.json"


def scan_fixed_root(root: str | Path, *, max_entries: int | None = None) -> dict[str, Any]:
    """List a fixed local root deterministically; any I/O/truncation is incomplete."""
    path = Path(root)
    try:
        entries = sorted((item for item in path.iterdir() if item.is_file() and not item.is_symlink()), key=lambda p: p.name)
    except OSError as exc:
        return {"entries": [], "complete": False, "unresolved": [f"listing_failed:{type(exc).__name__}"]}
    truncated = max_entries is not None and len(entries) > max_entries
    if truncated:
        entries = entries[:max_entries]
    return {"entries": [str(item) for item in entries], "complete": not truncated, "unresolved": ["listing_truncated"] if truncated else []}


def create_if_absent(path: str | Path, content: bytes) -> dict[str, Any]:
    """Publish a complete local file with an atomic same-filesystem hard-link create."""
    target = Path(path)
    temporary: str | None = None
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(mode="wb", dir=target.parent, prefix=f".{target.name}.", delete=False) as stream:
            temporary = stream.name
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, target, follow_symlinks=False)
        return {"status": "created", "path": str(target), "atomic": True}
    except FileExistsError:
        if target.exists() and target.is_file() and not target.is_symlink():
            return {"status": "conflict", "path": str(target), "atomic": True}
        return {"status": "blocked", "path": str(target), "atomic": False, "reason": "target_parent_unavailable"}
    except OSError as exc:
        return {"status": "blocked", "path": str(target), "atomic": False, "reason": f"atomic_create_unavailable:{type(exc).__name__}"}
    finally:
        if temporary is not None:
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass
            except OSError:
                pass


def create_workflow_state(workflow_root: str | Path, workflow_ref: str, state: dict[str, Any]) -> dict[str, Any]:
    path = canonical_state_path(workflow_root, workflow_ref)
    document = {"workflow_ref": workflow_ref.lower(), "schema_version": "1", "state": state}
    raw = _json_bytes(document)
    result = create_if_absent(path, raw)
    if result["status"] == "created":
        result["state_revision"] = "sha256:" + hashlib.sha256(raw).hexdigest()
        result["revision_kind"] = "local_exact_content_token_not_a_cas_condition"
    return result


def read_workflow_state(workflow_root: str | Path, workflow_ref: str, *, expected_revision: str | None = None) -> dict[str, Any]:
    path = canonical_state_path(workflow_root, workflow_ref)
    try:
        raw = path.read_bytes()
        document = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return {"status": "blocked", "reason": "workflow_state_unreadable"}
    revision = "sha256:" + hashlib.sha256(raw).hexdigest()
    if expected_revision and expected_revision != revision:
        return {"status": "blocked", "reason": "historical_state_revision_unavailable", "current_revision": revision}
    if document.get("workflow_ref") != workflow_ref.lower():
        return {"status": "blocked", "reason": "workflow_state_identity_mismatch"}
    return {"status": "current", "state": document.get("state"), "state_revision": revision, "historical_revision_available": False}


def state_update_decision(expected_revision: str | None, current_revision: str | None, native_atomic_conditional_write: bool) -> dict[str, Any]:
    if not expected_revision or not current_revision:
        return {"status": "blocked", "reason": "revision_unavailable"}
    if expected_revision != current_revision:
        return {"status": "conflict", "reason": "state_revision_changed"}
    if not native_atomic_conditional_write:
        return {"status": "blocked", "reason": "atomic_conditional_write_unavailable"}
    return {"status": "conditional_write_required", "expected_revision": expected_revision}


def verify_historical_revision(revision_token: str | None, provider_can_refetch: bool) -> dict[str, Any]:
    if not revision_token or not provider_can_refetch:
        return {"status": "blocked", "reason": "historical_artifact_revision_unavailable"}
    return {"status": "available", "revision": revision_token}


def _claim_path(claim_root: str | Path, workflow_ref: str, operation_ref: str) -> Path:
    digest = content_identity({"workflow_ref": workflow_ref, "operation_ref": operation_ref})
    return Path(claim_root) / f"{digest}.json"


def claim_mutable_operation(claim_root: str | Path, workflow_ref: str, operation_ref: str) -> dict[str, Any]:
    """Claim before browser/API mutation; an existing claim never implies safe retry."""
    claim = {"workflow_ref": workflow_ref, "operation_ref": operation_ref, "status": "claimed"}
    raw = _json_bytes(claim)
    result = create_if_absent(_claim_path(claim_root, workflow_ref, operation_ref), raw)
    if result["status"] == "created":
        return {**result, "status": "claim_acquired", "may_start": True, "claim_revision": "sha256:" + hashlib.sha256(raw).hexdigest()}
    if result["status"] == "conflict":
        return {**result, "status": "blocked", "may_start": False, "reason": "operation_already_claimed; inspect_owner_execution_and_cleanup"}
    return {**result, "may_start": False}


def recover_claim(*, owner_source_state: str | None, cleanup_confirmed: bool, expected_claim_revision: str | None, native_atomic_conditional_release: bool) -> dict[str, Any]:
    if owner_source_state != "not_started" or not cleanup_confirmed or not expected_claim_revision:
        return {"status": "blocked", "reason": "owner_execution_or_cleanup_unverified"}
    if not native_atomic_conditional_release:
        return {"status": "blocked", "reason": "atomic_claim_release_unavailable"}
    return {"status": "conditional_release_required", "expected_revision": expected_claim_revision}


def reserve_shared_resource(reservation_root: str | Path, resource_ref: str, workflow_ref: str, *, isolated: bool = False, external_reservation: str | None = None, external_reservation_acquired: bool = False) -> dict[str, Any]:
    if isolated:
        return {"status": "not_required", "reason": "isolated_resource"}
    if external_reservation and external_reservation_acquired:
        return {"status": "reserved", "reservation_ref": external_reservation, "owner_workflow_ref": workflow_ref, "provider": "existing_external_reservation"}
    if external_reservation:
        return {"status": "blocked", "reason": "external_reservation_not_confirmed"}
    target_ref = content_identity({"resource_ref": resource_ref})
    target = Path(reservation_root) / f"{target_ref}.json"
    reservation = {"resource_ref": resource_ref, "workflow_ref": workflow_ref, "status": "reserved"}
    result = create_if_absent(target, _json_bytes(reservation))
    if result["status"] == "created":
        return {**result, "status": "reserved", "reservation_ref": str(target), "reservation_revision": "sha256:" + hashlib.sha256(_json_bytes(reservation)).hexdigest(), "revision_kind": "local_exact_content_token_not_a_cas_condition"}
    return {**result, "status": "blocked", "reason": "reservation_conflict_or_atomic_create_unavailable"}


def release_shared_resource(*, current_workflow_ref: str, expected_workflow_ref: str, expected_reservation_revision: str | None, current_reservation_revision: str | None, native_atomic_conditional_release: bool, owner_state_verified: bool = False, owner_execution_state: str | None = None, cleanup_confirmed: bool = False) -> dict[str, Any]:
    if current_workflow_ref != expected_workflow_ref:
        return {"status": "blocked", "reason": "reservation_owner_mismatch"}
    if not owner_state_verified or owner_execution_state not in {"not_started", "complete"} or not cleanup_confirmed:
        return {"status": "blocked", "reason": "owner_execution_or_cleanup_unverified"}
    if not expected_reservation_revision or expected_reservation_revision != current_reservation_revision:
        return {"status": "conflict", "reason": "reservation_revision_mismatch"}
    if not native_atomic_conditional_release:
        return {"status": "blocked", "reason": "atomic_conditional_release_unavailable"}
    return {"status": "conditional_release_required", "expected_revision": expected_reservation_revision}


def partial_update_decision(*, owner_boundary_defined: bool, same_target_identity: bool, update_scopes_disjoint: bool, upstream_dependencies_unchanged: bool, native_atomic_conditional_write: bool, expected_revision: str | None) -> dict[str, Any]:
    if not all((owner_boundary_defined, same_target_identity, update_scopes_disjoint, upstream_dependencies_unchanged, native_atomic_conditional_write, expected_revision)):
        return {"status": "blocked", "reason": "partial_update_contract_not_proven"}
    return {"status": "conditional_write_required", "expected_revision": expected_revision}
