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
_HANDOFF_REF = re.compile(r"^HANDOFF-\d{3,}$")
_WCAG_REQUEST_KINDS = {"wcag-machine-probe", "semantic-observation"}


def _json_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def content_identity(value: Any) -> str:
    return hashlib.sha256(_json_bytes(value)).hexdigest()


def wcag_observation_key(value: dict[str, Any]) -> dict[str, Any]:
    """Validate and canonicalize the request identity carried by a handoff."""
    required = {
        "sample_ref", "variation_ref", "process_ref", "requirement_ref",
        "request_kind", "observation_request_ref",
    }
    if not isinstance(value, dict) or set(value) != required:
        raise ValueError("wcag_observation_key_schema_mismatch")
    for field in ("sample_ref", "variation_ref", "requirement_ref", "observation_request_ref"):
        if not isinstance(value[field], str) or not value[field].strip():
            raise ValueError(f"wcag_observation_key_missing:{field}")
    if value["process_ref"] is not None and (not isinstance(value["process_ref"], str) or not value["process_ref"].strip()):
        raise ValueError("wcag_observation_key_invalid:process_ref")
    if value["request_kind"] not in _WCAG_REQUEST_KINDS:
        raise ValueError("wcag_observation_key_invalid:request_kind")
    return {field: value[field] for field in sorted(required)}


def wcag_observation_key_identity(value: dict[str, Any]) -> str:
    return content_identity(wcag_observation_key(value))


def wcag_observation_operation_ref(origin_artifact_ref: str, origin_artifact_revision: str,
                                  handoff_ref: str) -> str:
    if not all(isinstance(item, str) and item.strip() for item in
               (origin_artifact_ref, origin_artifact_revision, handoff_ref)):
        raise ValueError("wcag_handoff_identity_incomplete")
    if not _HANDOFF_REF.fullmatch(handoff_ref):
        raise ValueError("wcag_handoff_ref_invalid")
    digest = content_identity({
        "origin_artifact_ref": origin_artifact_ref,
        "origin_artifact_revision": origin_artifact_revision,
        "handoff_ref": handoff_ref,
    })
    return "wcag-observation:sha256" + digest


def materialize_wcag_observation_handoff(*, handoff_ref: str, origin: dict[str, Any],
                                          expected_observations: list[dict[str, Any]],
                                          retry_of_handoff_ref: str | None = None,
                                          existing_handoffs: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Create the fixed qa-workflow handoff row; persistence remains provider-owned."""
    if not _HANDOFF_REF.fullmatch(handoff_ref):
        raise ValueError("wcag_handoff_ref_invalid")
    origin_fields = {"skill", "artifact_ref", "artifact_revision", "resume_operation"}
    if not isinstance(origin, dict) or set(origin) != origin_fields or origin.get("skill") != "wcag-conformance-evaluation":
        raise ValueError("wcag_handoff_origin_schema_mismatch")
    if not all(isinstance(origin.get(field), str) and origin[field].strip()
               for field in ("artifact_ref", "artifact_revision", "resume_operation")):
        raise ValueError("wcag_handoff_origin_incomplete")
    if not isinstance(expected_observations, list) or not expected_observations:
        raise ValueError("wcag_handoff_expected_observations_empty")
    keyed: dict[str, dict[str, Any]] = {}
    for raw in expected_observations:
        key = wcag_observation_key(raw)
        identity = content_identity(key)
        if identity in keyed:
            raise ValueError("wcag_handoff_duplicate_expected_observation")
        keyed[identity] = key
    expected = [keyed[key] for key in sorted(keyed)]
    rows = list(existing_handoffs or [])
    identity = (origin["artifact_ref"], origin["artifact_revision"], handoff_ref)
    for row in rows:
        row_origin = row.get("origin", {})
        row_identity = (row_origin.get("artifact_ref"), row_origin.get("artifact_revision"), row.get("handoff_ref"))
        if row_identity == identity:
            if row_origin != origin or row.get("expected_observations") != expected:
                return {"status": "conflict", "reason": "handoff_identity_expected_set_mismatch"}
            return {"status": "existing", "handoff": row}
    if retry_of_handoff_ref is not None:
        if not _HANDOFF_REF.fullmatch(retry_of_handoff_ref):
            raise ValueError("wcag_retry_handoff_ref_invalid")
        old = next((row for row in rows if row.get("handoff_ref") == retry_of_handoff_ref), None)
        if (old is None or old.get("origin", {}).get("artifact_ref") != origin["artifact_ref"]
                or old.get("origin", {}).get("artifact_revision") != origin["artifact_revision"]):
            raise ValueError("wcag_retry_origin_unresolved")
        for row in rows:
            same_retry_origin = row.get("origin", {}).get("artifact_ref") == origin["artifact_ref"]
            same_retry_revision = row.get("origin", {}).get("artifact_revision") == origin["artifact_revision"]
            if (row.get("retry_of_handoff_ref") == retry_of_handoff_ref and same_retry_origin and same_retry_revision
                    and row.get("expected_observations") == expected
                    and row.get("status") in {"pending", "in-progress", "returned"}):
                return {"status": "existing_open_retry", "handoff": row}
    operation_ref = wcag_observation_operation_ref(origin["artifact_ref"], origin["artifact_revision"], handoff_ref)
    handoff = {
        "handoff_ref": handoff_ref,
        "handoff_kind": "wcag-observation",
        "retry_of_handoff_ref": retry_of_handoff_ref,
        "origin": dict(origin),
        "owner_skill": "usability-inspection",
        "operation_ref": operation_ref,
        "expected_observations": expected,
        "returned_results": [],
        "operation_claim_ref": None,
        "operation_claim_revision": None,
        "resource_reservations": [],
        "status": "pending",
        "blocked_reason": None,
    }
    return {"status": "created", "handoff": handoff}


def record_wcag_observation_results(handoff: dict[str, Any], results: list[dict[str, Any]]) -> dict[str, Any]:
    """Apply immutable owner results idempotently without starting browser work."""
    required = {"handoff_ref", "origin_artifact_ref", "origin_artifact_revision", "observation_key",
                "result_ref", "result_revision", "previous_result_ref", "supersedes_result_ref"}
    current = list(handoff.get("returned_results", []))
    known_exact = {(row.get("result_ref"), row.get("result_revision")) for row in current}
    appended = []
    unexpected = []
    expected_ids = {wcag_observation_key_identity(row) for row in handoff.get("expected_observations", [])}
    for result in results:
        if not isinstance(result, dict) or required - set(result):
            raise ValueError("wcag_observation_result_schema_mismatch")
        origin = handoff.get("origin", {})
        if (result["handoff_ref"] != handoff.get("handoff_ref")
                or result["origin_artifact_ref"] != origin.get("artifact_ref")
                or result["origin_artifact_revision"] != origin.get("artifact_revision")):
            raise ValueError("wcag_observation_result_origin_mismatch")
        if not all(isinstance(result[field], str) and result[field].strip()
                   for field in ("result_ref", "result_revision")):
            raise ValueError("wcag_observation_result_identity_missing")
        for field in ("previous_result_ref", "supersedes_result_ref"):
            if result[field] is not None and (not isinstance(result[field], str) or not result[field].strip()):
                raise ValueError(f"wcag_observation_result_invalid:{field}")
        if result["previous_result_ref"] != result["supersedes_result_ref"]:
            raise ValueError("wcag_observation_result_lineage_mismatch")
        key = wcag_observation_key(result["observation_key"])
        key_id = content_identity(key)
        if key_id not in expected_ids:
            unexpected.append(key)
        exact = (result["result_ref"], result["result_revision"])
        if exact in known_exact:
            continue
        same_ref = [row for row in current + appended if row.get("result_ref") == result["result_ref"]]
        if same_ref:
            raise ValueError("wcag_result_ref_revision_conflict")
        group = [row for row in current + appended if content_identity(row["observation_key"]) == key_id]
        if group:
            open_heads = {row["result_ref"] for row in group} - {
                row.get("supersedes_result_ref") for row in group if row.get("supersedes_result_ref")
            }
            if len(open_heads) != 1 or result.get("supersedes_result_ref") not in open_heads:
                raise ValueError("wcag_observation_current_result_requires_explicit_supersedes")
        row = {"observation_key": key, "result_ref": result["result_ref"],
               "result_revision": result["result_revision"],
               "previous_result_ref": result["previous_result_ref"],
               "supersedes_result_ref": result["supersedes_result_ref"]}
        appended.append(row)
        known_exact.add(exact)
    return {"status": "applied" if appended else "idempotent_noop",
            "handoff": {**handoff, "returned_results": current + appended},
            "unexpected_observation_keys": unexpected}


def wcag_handoff_closure(handoff: dict[str, Any], *, current_origin_revision: str,
                         result_currentness: dict[str, str], owner_execution_state: str,
                         cleanup_status: str, required_reservations: list[dict[str, Any]]) -> dict[str, Any]:
    """Derive expected/returned closure and safety gates from current immutable refs."""
    origin = handoff.get("origin", {})
    origin_current = current_origin_revision == origin.get("artifact_revision")
    expected: dict[str, dict[str, Any]] = {}
    for row in handoff.get("expected_observations", []):
        key = wcag_observation_key(row)
        expected[content_identity(key)] = key
    returned: dict[str, list[dict[str, Any]]] = {}
    for row in handoff.get("returned_results", []):
        key = wcag_observation_key(row.get("observation_key", {}))
        returned.setdefault(content_identity(key), []).append(row)
    missing = sorted(expected.keys() - returned.keys())
    unexpected = sorted(returned.keys() - expected.keys())
    current_result_refs: list[str] = []
    ambiguous: list[str] = []
    stale_results: list[str] = []
    for key_id in sorted(expected.keys() & returned.keys()):
        group = returned[key_id]
        superseded = {row.get("supersedes_result_ref") for row in group if row.get("supersedes_result_ref")}
        heads = [row for row in group if row.get("result_ref") not in superseded]
        if len(heads) != 1:
            ambiguous.append(key_id)
            continue
        head = heads[0]
        if result_currentness.get(head["result_ref"]) != "current":
            stale_results.append(head["result_ref"])
        else:
            current_result_refs.append(head["result_ref"])
    cleanup_ok = cleanup_status in {"success", "not-required"}
    reservations_ok = all(row.get("status") == "released" for row in required_reservations)
    owner_complete = owner_execution_state == "complete"
    close_ready = (origin_current and not missing and not unexpected and not ambiguous and not stale_results
                   and owner_complete and cleanup_ok and reservations_ok)
    unsafe = bool(unexpected or ambiguous or stale_results or (owner_execution_state == "complete" and not cleanup_ok)
                  or (owner_execution_state == "complete" and not reservations_ok))
    if not origin_current:
        status = "stale"
    elif close_ready:
        status = "closed"
    elif unsafe:
        status = "blocked"
    elif current_result_refs:
        status = "returned"
    elif owner_execution_state == "in-progress":
        status = "in-progress"
    else:
        status = "pending"
    return {"status": status, "close_ready": close_ready, "origin_current": origin_current,
            "expected_count": len(expected), "returned_key_count": len(returned),
            "unfulfilled_observation_keys": missing, "unexpected_observation_keys": unexpected,
            "lineage_ambiguities": ambiguous, "stale_result_refs": stale_results,
            "current_result_refs": sorted(current_result_refs), "cleanup_ok": cleanup_ok,
            "required_reservations_released": reservations_ok, "owner_execution_complete": owner_complete}


def wcag_handoff_resume_decision(handoff: dict[str, Any], closure: dict[str, Any], *,
                                 current_origin_revision: str) -> dict[str, Any]:
    """Recheck resume only after the caller has persisted closed by native CAS and reread."""
    origin = handoff.get("origin", {})
    same_origin = current_origin_revision == origin.get("artifact_revision")
    may_resume = (handoff.get("status") == "closed" and closure.get("status") == "closed"
                  and closure.get("close_ready") is True and same_origin
                  and closure.get("origin_current") is True)
    if not may_resume:
        return {"may_resume": False, "reason": "handoff_not_closed_or_origin_stale" if same_origin else "origin_revision_stale"}
    return {"may_resume": True, "origin_artifact_ref": origin["artifact_ref"],
            "origin_artifact_revision": origin["artifact_revision"],
            "resume_operation": origin["resume_operation"],
            "result_refs": closure["current_result_refs"]}


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


def _claim_path(workflow_state_root: str | Path, workflow_ref: str, operation_ref: str) -> Path:
    digest = content_identity({"workflow_ref": workflow_ref, "operation_ref": operation_ref})
    return Path(workflow_state_root) / "claims" / f"{digest}.json"


def claim_mutable_operation(workflow_state_root: str | Path, workflow_ref: str, operation_ref: str) -> dict[str, Any]:
    """Claim before browser/API mutation; an existing claim never implies safe retry."""
    claim = {"workflow_ref": workflow_ref, "operation_ref": operation_ref, "status": "claimed"}
    raw = _json_bytes(claim)
    result = create_if_absent(_claim_path(workflow_state_root, workflow_ref, operation_ref), raw)
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


def reserve_shared_resource(reservation_root: str | Path, resource_ref: str, workflow_ref: str, *, native_atomic_conditional_release: bool, isolated: bool = False, external_reservation: str | None = None, external_reservation_acquired: bool = False, external_reservation_revision: str | None = None) -> dict[str, Any]:
    if isolated:
        return {"status": "not_required", "reason": "isolated_resource"}
    if external_reservation and external_reservation_acquired:
        if not isinstance(external_reservation_revision, str) or not external_reservation_revision.strip():
            return {"status": "blocked", "reason": "external_reservation_revision_missing"}
        return {"status": "reserved", "reservation_ref": external_reservation, "owner_workflow_ref": workflow_ref, "provider": "existing_external_reservation", "reservation_revision": external_reservation_revision}
    if external_reservation:
        return {"status": "blocked", "reason": "external_reservation_not_confirmed"}
    if not native_atomic_conditional_release:
        return {"status": "blocked", "reason": "atomic_conditional_release_unavailable"}
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
