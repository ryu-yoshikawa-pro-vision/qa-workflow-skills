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
import sqlite3
import tempfile
import uuid
from contextlib import closing
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


_SQLITE_WORKFLOW_DB = "workflow-state.sqlite3"
_SQLITE_BUSY_TIMEOUT_MS = 5000
_SHA256_REF = re.compile(r"^sha256:[0-9a-f]{64}$")
_CONTENT_IDENTITY = re.compile(r"^[0-9a-f]{64}$")
_SAFE_STORED_REF = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,199}$")
_HMAC_DOCUMENT_IDENTITY = re.compile(r"^hmac-sha256:[0-9a-f]{64}$")


def workflow_state_root_from_project_context(project_context: str) -> Path:
    """Resolve only the existing qa.workflow_state_root Project Context key."""
    if not isinstance(project_context, str) or not project_context.strip():
        raise ValueError("workflow_state_root_unavailable")
    parsed = parse_project_context(project_context)
    required = validate_required_context_fields(parsed, ["qa.workflow_state_root"])
    if required["status"] != "resolved":
        raise ValueError("workflow_state_root_unavailable")
    value = parsed["fields"]["qa.workflow_state_root"]["value"]
    root = Path(value).expanduser()
    if not root.is_absolute():
        raise ValueError("workflow_state_root_must_be_absolute")
    return root


def workflow_state_context_from_project_context(project_context: str, project_context_ref: str,
                                                reference_refs: list[str]) -> dict[str, Any]:
    """Resolve the Project Context stable key and bind it to its current source ref."""
    if not _safe_stored_ref(project_context_ref) or not isinstance(reference_refs, list):
        raise ValueError("workflow_project_context_source_invalid")
    if project_context_ref not in reference_refs:
        raise ValueError("workflow_project_context_source_ref_missing")
    root = workflow_state_root_from_project_context(project_context)
    parsed = parse_project_context(project_context)
    field_identity = parsed["fields"]["qa.workflow_state_root"]["content_identity"]
    fingerprint = "sha256:" + content_identity({
        "project_context_ref": project_context_ref,
        "stable_key": "qa.workflow_state_root",
        "content_identity": field_identity,
    })
    database_path = _local_sqlite_path(root)
    return {"workflow_state_root": str(root.resolve(strict=False)),
            "workflow_state_root_content_identity": field_identity,
            "project_context_ref": project_context_ref,
            "project_context_revision": field_identity,
            "project_context_fingerprint": fingerprint,
            "database_path": str(database_path)}


def _local_sqlite_path(workflow_root: str | Path) -> Path:
    root = Path(workflow_root).expanduser()
    if not root.is_absolute():
        raise ValueError("workflow_state_root_must_be_absolute")
    root = root.resolve(strict=False)
    raw = str(root)
    if raw.startswith(("\\\\", "//")):
        raise ValueError("workflow_state_network_filesystem_unsupported")
    if os.name == "nt":
        try:
            import ctypes

            drive_type = ctypes.windll.kernel32.GetDriveTypeW(root.anchor)
        except (AttributeError, OSError):
            raise ValueError("workflow_state_filesystem_type_unavailable") from None
        # DRIVE_FIXED only. Removable and remote drives are outside the provider contract.
        if drive_type != 3:
            raise ValueError("workflow_state_nonlocal_filesystem_unsupported")
    else:
        mount_table = Path("/proc/self/mounts")
        if mount_table.is_file():
            candidates: list[tuple[int, Path, str]] = []
            for line in mount_table.read_text(encoding="utf-8", errors="replace").splitlines():
                fields = line.split()
                if len(fields) < 3:
                    continue
                mount = Path(fields[1].replace("\\040", " ").replace("\\011", "\t"))
                try:
                    root.relative_to(mount)
                except ValueError:
                    continue
                candidates.append((len(str(mount)), mount, fields[2].lower()))
            if candidates:
                filesystem = max(candidates, key=lambda row: row[0])[2]
                local_filesystems = {"ext2", "ext3", "ext4", "xfs", "btrfs", "zfs", "tmpfs", "overlay", "f2fs"}
                if filesystem not in local_filesystems:
                    raise ValueError("workflow_state_network_filesystem_unsupported")
            else:
                raise ValueError("workflow_state_filesystem_type_unavailable")
        else:
            raise ValueError("workflow_state_filesystem_type_unavailable")
    path = root / _SQLITE_WORKFLOW_DB
    if path.is_symlink():
        raise ValueError("workflow_state_database_symlink_unsupported")
    if any((parent / ".git").exists() for parent in (root, *root.parents)):
        raise ValueError("workflow_state_database_must_be_outside_git_worktree")
    return path


def _sqlite_connection(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(str(path), timeout=_SQLITE_BUSY_TIMEOUT_MS / 1000, isolation_level=None)
    try:
        connection.execute(f"PRAGMA busy_timeout={_SQLITE_BUSY_TIMEOUT_MS}")
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA synchronous=FULL")
        return connection
    except sqlite3.Error:
        connection.close()
        raise


def _initialize_sqlite_workflow_table(connection: sqlite3.Connection) -> None:
    mode = connection.execute("PRAGMA journal_mode=DELETE").fetchone()
    if not mode or str(mode[0]).lower() != "delete":
        raise sqlite3.OperationalError("local journal mode unavailable")
    connection.execute(
        "CREATE TABLE IF NOT EXISTS workflow_state ("
        "workflow_ref TEXT PRIMARY KEY, envelope_json TEXT NOT NULL, "
        "provider_revision INTEGER NOT NULL CHECK(provider_revision > 0))"
    )


def _provider_revision_token(revision: int) -> str:
    return f"sqlite:{revision}"


def _provider_revision_number(token: str | None) -> int | None:
    match = re.fullmatch(r"sqlite:([1-9][0-9]*)", token or "")
    return int(match.group(1)) if match else None


def _workflow_envelope(workflow_ref: str, state: dict[str, Any]) -> dict[str, Any]:
    ref = workflow_ref.lower() if isinstance(workflow_ref, str) else ""
    if not _UUID.fullmatch(ref) or not isinstance(state, dict):
        raise ValueError("workflow_state_identity_invalid")
    return {"workflow_ref": ref, "schema_version": "1", "state": state}


def create_sqlite_workflow_state(workflow_root: str | Path, workflow_ref: str,
                                 state: dict[str, Any]) -> dict[str, Any]:
    """Create the unchanged workflow envelope with a native SQLite revision."""
    try:
        envelope = _workflow_envelope(workflow_ref, state)
        path = _local_sqlite_path(workflow_root)
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_RDWR, 0o600)
        except FileExistsError:
            descriptor = None
        if descriptor is not None:
            os.close(descriptor)
        encoded = _json_bytes(envelope).decode("utf-8")
        with closing(_sqlite_connection(path)) as connection:
            _initialize_sqlite_workflow_table(connection)
            connection.execute("BEGIN IMMEDIATE")
            current = connection.execute(
                "SELECT provider_revision FROM workflow_state WHERE workflow_ref=?", (envelope["workflow_ref"],)
            ).fetchone()
            if current:
                connection.execute("ROLLBACK")
                return {"status": "conflict", "reason": "workflow_state_already_exists"}
            connection.execute(
                "INSERT INTO workflow_state(workflow_ref,envelope_json,provider_revision) VALUES(?,?,1)",
                (envelope["workflow_ref"], encoded),
            )
            connection.execute("COMMIT")
        result = read_sqlite_workflow_state(workflow_root, envelope["workflow_ref"])
        if result.get("status") != "current" or result.get("state") != state:
            return {"status": "blocked", "reason": "workflow_state_create_reread_failed"}
        return {**result, "status": "created"}
    except (OSError, sqlite3.Error, TypeError, ValueError):
        return {"status": "blocked", "reason": "workflow_state_provider_unavailable"}


def read_sqlite_workflow_state(workflow_root: str | Path, workflow_ref: str,
                               *, expected_revision: str | None = None) -> dict[str, Any]:
    """Read the current envelope from a new connection; the token is provider-owned."""
    ref = workflow_ref.lower() if isinstance(workflow_ref, str) else ""
    if not _UUID.fullmatch(ref):
        return {"status": "blocked", "reason": "workflow_state_identity_invalid"}
    try:
        path = _local_sqlite_path(workflow_root)
        if not path.is_file():
            return {"status": "blocked", "reason": "workflow_state_not_found"}
        with closing(_sqlite_connection(path)) as connection:
            row = connection.execute(
                "SELECT envelope_json,provider_revision FROM workflow_state WHERE workflow_ref=?", (ref,)
            ).fetchone()
        if row is None:
            return {"status": "blocked", "reason": "workflow_state_not_found"}
        envelope = json.loads(row[0])
        if (not isinstance(envelope, dict) or set(envelope) != {"workflow_ref", "schema_version", "state"}
                or envelope.get("workflow_ref") != ref or envelope.get("schema_version") != "1"
                or not isinstance(envelope.get("state"), dict) or not isinstance(row[1], int) or row[1] < 1):
            return {"status": "blocked", "reason": "workflow_state_corrupt"}
        token = _provider_revision_token(row[1])
        if expected_revision is not None and expected_revision != token:
            return {"status": "conflict", "reason": "state_revision_changed", "current_revision": token}
        return {"status": "current", "state": envelope["state"], "workflow_ref": ref,
                "schema_version": "1", "state_revision": token,
                "revision_kind": "sqlite_atomic_provider_revision", "historical_revision_available": False}
    except (OSError, sqlite3.Error, UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError):
        return {"status": "blocked", "reason": "workflow_state_unreadable"}


def conditional_write_sqlite_workflow_state(workflow_root: str | Path, workflow_ref: str,
                                            expected_revision: str, state: dict[str, Any]) -> dict[str, Any]:
    """Atomically compare-and-write, then reread through an independent connection."""
    revision = _provider_revision_number(expected_revision)
    try:
        envelope = _workflow_envelope(workflow_ref, state)
        path = _local_sqlite_path(workflow_root)
        if revision is None or not path.is_file():
            return {"status": "blocked", "reason": "workflow_state_revision_unavailable"}
        encoded = _json_bytes(envelope).decode("utf-8")
        with closing(_sqlite_connection(path)) as connection:
            connection.execute("BEGIN IMMEDIATE")
            cursor = connection.execute(
                "UPDATE workflow_state SET envelope_json=?,provider_revision=provider_revision+1 "
                "WHERE workflow_ref=? AND provider_revision=?",
                (encoded, envelope["workflow_ref"], revision),
            )
            if cursor.rowcount != 1:
                connection.execute("ROLLBACK")
                current = connection.execute(
                    "SELECT provider_revision FROM workflow_state WHERE workflow_ref=?", (envelope["workflow_ref"],)
                ).fetchone()
                return {"status": "conflict", "reason": "state_revision_changed",
                        "current_revision": _provider_revision_token(current[0]) if current else None}
            connection.execute("COMMIT")
        reread = read_sqlite_workflow_state(workflow_root, envelope["workflow_ref"])
        expected_new = _provider_revision_token(revision + 1)
        if (reread.get("status") != "current" or reread.get("state_revision") != expected_new
                or reread.get("state") != state):
            return {"status": "blocked", "reason": "workflow_state_write_reread_failed"}
        return {**reread, "status": "written"}
    except (OSError, sqlite3.Error, TypeError, ValueError):
        return {"status": "blocked", "reason": "workflow_state_provider_unavailable"}


def _safe_stored_ref(value: Any) -> bool:
    return (isinstance(value, str) and bool(_SAFE_STORED_REF.fullmatch(value))
            and "://" not in value and "?" not in value and "#" not in value)


def _unique_ref_rows(value: Any, label: str, *, fields: tuple[str, ...]) -> list[dict[str, str]]:
    if not isinstance(value, list) or not value:
        raise ValueError(f"{label}_missing")
    result: list[dict[str, str]] = []
    seen: set[tuple[str, ...]] = set()
    for row in value:
        if not isinstance(row, dict) or any(not _safe_stored_ref(row.get(key)) for key in fields):
            raise ValueError(f"{label}_invalid")
        identity = tuple(row[key] for key in fields)
        if identity in seen:
            raise ValueError(f"{label}_duplicate")
        seen.add(identity)
        result.append({key: row[key] for key in fields})
    return sorted(result, key=lambda row: tuple(row[key] for key in fields))


def _canonical_wcag_basis(plan: Any) -> dict[str, Any]:
    if not isinstance(plan, dict) or plan.get("status") != "ready":
        raise ValueError("canonical_wcag_plan_unavailable")
    basis = plan.get("plan_basis")
    expected = {"wcag_version", "level", "samples", "variations", "process_memberships",
                "evaluation_ref", "evaluation_revision"}
    if not isinstance(basis, dict) or set(basis) != expected:
        raise ValueError("canonical_wcag_plan_basis_invalid")
    if basis.get("wcag_version") not in {"2.0", "2.1", "2.2"} or basis.get("level") not in {"A", "AA", "AAA"}:
        raise ValueError("canonical_wcag_target_invalid")
    if not _safe_stored_ref(basis.get("evaluation_ref")) or not _safe_stored_ref(basis.get("evaluation_revision")):
        raise ValueError("canonical_wcag_evaluation_identity_invalid")
    samples = basis.get("samples")
    variations = basis.get("variations")
    memberships = basis.get("process_memberships")
    if not isinstance(samples, list) or not samples or not isinstance(variations, list) or not variations or not isinstance(memberships, dict):
        raise ValueError("canonical_wcag_selection_invalid")
    normalized_samples: list[dict[str, str]] = []
    sample_refs: set[str] = set()
    for row in samples:
        if not isinstance(row, dict) or set(row) - {"sample_ref", "identity_fingerprint", "target_identity", "sample_kind"}:
            raise ValueError("canonical_wcag_sample_invalid")
        sample_ref = row.get("sample_ref")
        identity = row.get("identity_fingerprint")
        target = row.get("target_identity")
        sample_kind = row.get("sample_kind")
        if (not _safe_stored_ref(sample_ref) or not isinstance(identity, str) or not _SHA256_REF.fullmatch(identity)
                or not isinstance(target, str) or not _HMAC_DOCUMENT_IDENTITY.fullmatch(target)
                or (sample_kind is not None and not _safe_stored_ref(sample_kind)) or sample_ref in sample_refs):
            raise ValueError("canonical_wcag_sample_invalid")
        sample_refs.add(sample_ref)
        normalized_samples.append({"sample_ref": sample_ref, "identity_fingerprint": identity,
                                   "target_identity": target, **({"sample_kind": sample_kind} if sample_kind is not None else {})})
    normalized_samples.sort(key=lambda row: row["sample_ref"])
    normalized_variations: list[dict[str, str]] = []
    variation_identities: set[tuple[str, str]] = set()
    variations_by_sample: dict[str, int] = {ref: 0 for ref in sample_refs}
    for row in variations:
        if not isinstance(row, dict) or set(row) != {"sample_ref", "variation_ref", "identity_fingerprint"}:
            raise ValueError("canonical_wcag_variation_invalid")
        sample_ref, variation_ref, identity = row.get("sample_ref"), row.get("variation_ref"), row.get("identity_fingerprint")
        pair = (sample_ref, variation_ref)
        if (sample_ref not in sample_refs or not _safe_stored_ref(variation_ref)
                or not isinstance(identity, str) or not _SHA256_REF.fullmatch(identity) or pair in variation_identities):
            raise ValueError("canonical_wcag_variation_invalid")
        variation_identities.add(pair)
        variations_by_sample[sample_ref] += 1
        normalized_variations.append({"sample_ref": sample_ref, "variation_ref": variation_ref,
                                      "identity_fingerprint": identity})
    if any(count == 0 for count in variations_by_sample.values()):
        raise ValueError("canonical_wcag_sample_variation_missing")
    normalized_variations.sort(key=lambda row: (row["sample_ref"], row["variation_ref"]))
    normalized_memberships: dict[str, str] = {}
    for sample_ref, process_ref in memberships.items():
        if sample_ref not in sample_refs or not _safe_stored_ref(process_ref):
            raise ValueError("canonical_wcag_process_membership_invalid")
        normalized_memberships[sample_ref] = process_ref
    criterion_rows = plan.get("criteria")
    if not isinstance(criterion_rows, list) or not criterion_rows:
        raise ValueError("canonical_wcag_criterion_rows_missing")
    normalized_criteria: list[dict[str, Any]] = []
    criterion_refs: set[str] = set()
    for row in criterion_rows:
        if not isinstance(row, dict):
            raise ValueError("canonical_wcag_criterion_row_invalid")
        fields = ("criterion_evaluation_ref", "evaluation_ref", "evaluation_revision", "sample_ref",
                  "variation_ref", "criterion_ref")
        if any(not _safe_stored_ref(row.get(key)) for key in fields):
            raise ValueError("canonical_wcag_criterion_row_invalid")
        process_ref = row.get("process_ref")
        if process_ref is not None and not _safe_stored_ref(process_ref):
            raise ValueError("canonical_wcag_criterion_row_invalid")
        ref = row["criterion_evaluation_ref"]
        if ref in criterion_refs or row["evaluation_ref"] != basis["evaluation_ref"] or row["evaluation_revision"] != basis["evaluation_revision"]:
            raise ValueError("canonical_wcag_criterion_row_duplicate_or_mismatched")
        if row["sample_ref"] not in sample_refs or (row["sample_ref"], row["variation_ref"]) not in variation_identities:
            raise ValueError("canonical_wcag_criterion_row_selection_mismatch")
        if row["process_ref"] != normalized_memberships.get(row["sample_ref"]):
            raise ValueError("canonical_wcag_criterion_row_process_mismatch")
        criterion_refs.add(ref)
        normalized_criteria.append({key: row[key] for key in fields} | {"process_ref": process_ref})
    normalized_criteria.sort(key=lambda row: row["criterion_evaluation_ref"])
    normalized_basis = {"wcag_version": basis["wcag_version"], "level": basis["level"],
                        "samples": normalized_samples, "variations": normalized_variations,
                        "process_memberships": dict(sorted(normalized_memberships.items())),
                        "evaluation_ref": basis["evaluation_ref"], "evaluation_revision": basis["evaluation_revision"]}
    return {"basis": normalized_basis, "criteria": normalized_criteria,
            "criterion_evaluation_refs": sorted(criterion_refs)}


def _build_wcag_evaluation_record(*, evaluation_initialization: dict[str, Any], evaluation_inputs: dict[str, Any],
                                  product_scope_ref: str,
                                  project_context_ref: str, project_context_revision: str,
                                  project_context_fingerprint: str,
                                  workflow_state_root_content_identity: str,
                                  scope_coverage: dict[str, Any], source_artifacts: list[dict[str, Any]],
                                  canonical_criterion_plan: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(evaluation_initialization, dict) or evaluation_initialization.get("status") != "ready":
        raise ValueError("wcag_evaluation_initialization_not_ready")
    target = evaluation_initialization.get("target")
    if not isinstance(target, dict) or target.get("status") != "supported":
        raise ValueError("wcag_evaluation_target_unavailable")
    evaluation_ref = evaluation_initialization.get("evaluation_ref")
    evaluation_revision = evaluation_initialization.get("revision")
    input_fingerprint_value = evaluation_initialization.get("input_fingerprint")
    required_initialization_fields = {
        "artifact_ref", "artifact_revision", "evaluator", "evaluation_date", "live_web_target",
        "commissioner", "wcag_version", "level", "product_scope", "product_enclosure",
        "accessibility_support_baseline", "browser_user_agent_baseline", "role_permission_environment",
        "side_effect_scope", "cleanup_scope", "evaluation_period",
    }
    version, level = target.get("version"), target.get("level")
    if (not _safe_stored_ref(evaluation_ref) or not _safe_stored_ref(evaluation_revision)
            or not isinstance(input_fingerprint_value, str) or not _SHA256_REF.fullmatch(input_fingerprint_value)
            or version not in {"2.0", "2.1", "2.2"} or level not in {"A", "AA", "AAA"}
            or not _safe_stored_ref(product_scope_ref) or not _safe_stored_ref(project_context_ref)
            or not _CONTENT_IDENTITY.fullmatch(project_context_revision)
            or not _SHA256_REF.fullmatch(project_context_fingerprint)
            or not _CONTENT_IDENTITY.fullmatch(workflow_state_root_content_identity)):
        raise ValueError("wcag_evaluation_source_invalid")
    if (not isinstance(evaluation_inputs, dict) or set(evaluation_inputs) != required_initialization_fields
            or "sha256:" + content_identity(evaluation_inputs) != input_fingerprint_value
            or evaluation_inputs.get("artifact_ref") != evaluation_ref
            or evaluation_inputs.get("artifact_revision") != evaluation_revision
            or evaluation_inputs.get("wcag_version") != version or evaluation_inputs.get("level") != level
            or evaluation_inputs.get("product_enclosure") != product_scope_ref
            or not _safe_stored_ref(evaluation_inputs.get("evaluator"))
            or not _safe_stored_ref(evaluation_inputs.get("commissioner"))):
        raise ValueError("wcag_evaluation_initialization_source_mismatch")
    if not isinstance(scope_coverage, dict) or scope_coverage.get("status") != "ready":
        raise ValueError("wcag_scope_not_confirmed")
    scope_rows = scope_coverage.get("scope_coverage")
    if not isinstance(scope_rows, list) or not scope_rows:
        raise ValueError("wcag_scope_evidence_missing")
    compact_scope: list[dict[str, Any]] = []
    scope_refs: set[str] = set()
    scope_keys: set[str] = set()
    scope_evidence: set[str] = set()
    for row in scope_rows:
        if not isinstance(row, dict) or row.get("decision") not in {"in-scope", "out-of-product"}:
            raise ValueError("wcag_scope_unresolved")
        scope_ref, scope_key = row.get("scope_ref"), row.get("scope_key")
        evidence_refs = row.get("evidence_refs")
        if (not _safe_stored_ref(scope_ref) or not _safe_stored_ref(scope_key) or scope_ref in scope_refs
                or scope_key in scope_keys or not isinstance(evidence_refs, list) or not evidence_refs
                or any(not _safe_stored_ref(ref) for ref in evidence_refs)
                or len(evidence_refs) != len(set(evidence_refs))
                or (row["decision"] == "out-of-product" and not isinstance(row.get("reason"), str))):
            raise ValueError("wcag_scope_evidence_invalid")
        scope_refs.add(scope_ref)
        scope_keys.add(scope_key)
        scope_evidence.update(evidence_refs)
        compact_scope.append({"scope_ref": scope_ref, "scope_key": scope_key,
                              "decision": row["decision"], "evidence_refs": sorted(evidence_refs)})
    compact_scope.sort(key=lambda row: row["scope_key"])
    sources = _unique_ref_rows(source_artifacts, "wcag_source_artifacts",
                               fields=("artifact_ref", "artifact_revision", "purpose"))
    if (any(row["purpose"] not in {"evaluation", "scope", "sample-selection", "variation", "process"}
            for row in sources)
            or not any(row["artifact_ref"] == evaluation_ref and row["artifact_revision"] == evaluation_revision
                       and row["purpose"] == "evaluation" for row in sources)
            or not any(row["artifact_ref"] == product_scope_ref and row["purpose"] == "scope" for row in sources)
            or not any(row["purpose"] == "sample-selection" for row in sources)):
        raise ValueError("wcag_evaluation_source_artifact_mismatch")
    plan = _canonical_wcag_basis(canonical_criterion_plan)
    basis = plan["basis"]
    if (basis["evaluation_ref"] != evaluation_ref or basis["evaluation_revision"] != evaluation_revision
            or basis["wcag_version"] != version or basis["level"] != level):
        raise ValueError("wcag_plan_does_not_match_initialized_evaluation")
    plan_fingerprint = "sha256:" + content_identity(canonical_criterion_plan)
    record = {
        "evaluation_ref": evaluation_ref,
        "evaluation_revision": evaluation_revision,
        "wcag_version": version,
        "level": level,
        "initialization_fingerprint": input_fingerprint_value,
        "evaluator_ref": evaluation_inputs["evaluator"],
        "commissioner_ref": evaluation_inputs["commissioner"],
        "product_enclosure_ref": evaluation_inputs["product_enclosure"],
        "project_context_ref": project_context_ref,
        "project_context_revision": project_context_revision,
        "project_context_fingerprint": project_context_fingerprint,
        "workflow_state_root_content_identity": workflow_state_root_content_identity,
        "product_scope_ref": product_scope_ref,
        "scope_coverage": compact_scope,
        "scope_evidence_refs": sorted(scope_evidence),
        "source_artifacts": sources,
        "selected_samples": basis["samples"],
        "presentation_variations": basis["variations"],
        "process_memberships": basis["process_memberships"],
        "canonical_plan_basis": basis,
        "canonical_plan_fingerprint": plan_fingerprint,
        "criterion_rows": plan["criteria"],
        "criterion_evaluation_refs": plan["criterion_evaluation_refs"],
        "previous_evaluation_revision": None,
        "record_status": "plan-finalized",
        "report_status": "open",
        "report_fingerprint": None,
        "report_result_refs": [],
        "report_criterion_evaluation_refs": [],
    }
    return record


def _ensure_sqlite_workflow_state(workflow_root: str | Path, workflow_ref: str, *,
                                  project_context_ref: str, project_context_revision: str,
                                  project_context_fingerprint: str,
                                  workflow_state_root_content_identity: str) -> dict[str, Any]:
    current = read_sqlite_workflow_state(workflow_root, workflow_ref)
    if current.get("status") == "current":
        return current
    if current.get("reason") != "workflow_state_not_found":
        return current
    try:
        legacy_path = canonical_state_path(workflow_root, workflow_ref)
        if legacy_path.is_file():
            legacy = read_workflow_state(workflow_root, workflow_ref)
            if legacy.get("status") != "current" or not isinstance(legacy.get("state"), dict):
                return {"status": "blocked", "reason": "workflow_state_migration_source_unavailable"}
            state = legacy["state"]
        else:
            state = {"overall_state": "実行中", "started_source_refs": []}
        context_fields = {"project_context_ref": project_context_ref,
                          "project_context_revision": project_context_revision,
                          "project_context_fingerprint": project_context_fingerprint,
                          "workflow_state_root_content_identity": workflow_state_root_content_identity,
                          "used_project_context_fields": [{
                              "stable_key": "qa.workflow_state_root",
                              "content_identity": workflow_state_root_content_identity,
                              "affected_scope": "WCAG workflow state storage",
                              "operation": "WCAG evaluation state",
                          }]}
        existing_context = {key: state.get(key) for key in context_fields if key in state}
        if existing_context and existing_context != context_fields:
            return {"status": "blocked", "reason": "workflow_project_context_changed"}
        state.update(context_fields)
        created = create_sqlite_workflow_state(workflow_root, workflow_ref, state)
        if created.get("status") == "created":
            return read_sqlite_workflow_state(workflow_root, workflow_ref)
        return read_sqlite_workflow_state(workflow_root, workflow_ref)
    except (OSError, ValueError):
        return {"status": "blocked", "reason": "workflow_state_initialization_failed"}


def register_wcag_evaluation_plan(workflow_root: str | Path, workflow_ref: str, *,
                                  evaluation_initialization: dict[str, Any], evaluation_inputs: dict[str, Any],
                                  product_scope_ref: str,
                                  project_context_ref: str, project_context_revision: str,
                                  project_context_fingerprint: str,
                                  workflow_state_root_content_identity: str,
                                  scope_coverage: dict[str, Any], source_artifacts: list[dict[str, Any]],
                                  canonical_criterion_plan: dict[str, Any],
                                  previous_evaluation_revision: str | None = None) -> dict[str, Any]:
    """Persist the owner-confirmed WCAG scope and finalized selected-set plan."""
    try:
        record = _build_wcag_evaluation_record(
            evaluation_initialization=evaluation_initialization,
            evaluation_inputs=evaluation_inputs,
            product_scope_ref=product_scope_ref,
            project_context_ref=project_context_ref,
            project_context_revision=project_context_revision,
            project_context_fingerprint=project_context_fingerprint,
            workflow_state_root_content_identity=workflow_state_root_content_identity,
            scope_coverage=scope_coverage,
            source_artifacts=source_artifacts,
            canonical_criterion_plan=canonical_criterion_plan,
        )
        ref = workflow_ref.lower()
        if not _UUID.fullmatch(ref):
            raise ValueError("workflow_state_identity_invalid")
    except (AttributeError, TypeError, ValueError):
        return {"status": "blocked", "reason": "wcag_evaluation_registration_invalid"}
    current = _ensure_sqlite_workflow_state(
        workflow_root, ref, project_context_ref=project_context_ref,
        project_context_revision=project_context_revision,
        project_context_fingerprint=project_context_fingerprint,
        workflow_state_root_content_identity=workflow_state_root_content_identity,
    )
    if current.get("status") != "current":
        return {"status": "blocked", "reason": current.get("reason", "workflow_state_unavailable")}
    state = current.get("state")
    if not isinstance(state, dict):
        return {"status": "blocked", "reason": "workflow_state_corrupt"}
    context_values = {
        "project_context_ref": project_context_ref,
        "project_context_revision": project_context_revision,
        "project_context_fingerprint": project_context_fingerprint,
        "workflow_state_root_content_identity": workflow_state_root_content_identity,
    }
    existing_context = {key: state.get(key) for key in context_values if key in state}
    if existing_context and existing_context != context_values:
        return {"status": "conflict", "reason": "workflow_project_context_changed"}
    evaluations = state.get("wcag_evaluations", {})
    if not isinstance(evaluations, dict):
        return {"status": "blocked", "reason": "wcag_evaluation_state_corrupt"}
    if not existing_context and evaluations:
        return {"status": "blocked", "reason": "workflow_project_context_provenance_missing"}
    state.update(context_values)
    state["used_project_context_fields"] = [{
        "stable_key": "qa.workflow_state_root",
        "content_identity": workflow_state_root_content_identity,
        "affected_scope": "WCAG workflow state storage",
        "operation": "WCAG evaluation state",
    }]
    old = evaluations.get(record["evaluation_ref"])
    if old is not None:
        if not isinstance(old, dict):
            return {"status": "blocked", "reason": "wcag_evaluation_state_corrupt"}
        if old.get("evaluation_revision") == record["evaluation_revision"]:
            if old.get("canonical_plan_fingerprint") != record["canonical_plan_fingerprint"] or any(
                    old.get(key) != record.get(key) for key in (
                        "wcag_version", "level", "initialization_fingerprint", "product_scope_ref",
                        "evaluator_ref", "commissioner_ref", "product_enclosure_ref",
                        "project_context_ref", "project_context_revision", "project_context_fingerprint",
                        "workflow_state_root_content_identity",
                        "scope_coverage", "scope_evidence_refs", "source_artifacts", "selected_samples",
                        "presentation_variations", "process_memberships", "canonical_plan_basis", "criterion_rows")):
                return {"status": "conflict", "reason": "evaluation_revision_scope_or_plan_is_immutable"}
            return {"status": "current", "evaluation_ref": record["evaluation_ref"],
                    "evaluation_revision": record["evaluation_revision"],
                    "provider_revision": current["state_revision"], "idempotent": True}
        if (not _safe_stored_ref(previous_evaluation_revision)
                or previous_evaluation_revision != old.get("evaluation_revision")
                or record["evaluation_revision"] == old.get("evaluation_revision")
                or record["source_artifacts"] == old.get("source_artifacts")):
            return {"status": "conflict", "reason": "evaluation_revision_update_not_proven"}
        record["previous_evaluation_revision"] = old["evaluation_revision"]
    elif previous_evaluation_revision is not None:
        return {"status": "conflict", "reason": "previous_evaluation_revision_not_current"}
    evaluations[record["evaluation_ref"]] = record
    state["wcag_evaluations"] = evaluations
    written = conditional_write_sqlite_workflow_state(
        workflow_root, ref, current["state_revision"], state
    )
    if written.get("status") != "written":
        return {"status": written.get("status", "blocked"), "reason": written.get("reason", "workflow_state_write_failed")}
    verified = read_wcag_evaluation_state(
        workflow_root, ref, record["evaluation_ref"], evaluation_revision=record["evaluation_revision"],
        project_context_ref=project_context_ref, project_context_revision=project_context_revision,
        project_context_fingerprint=project_context_fingerprint,
        workflow_state_root_content_identity=workflow_state_root_content_identity,
    )
    if verified.get("status") != "current" or verified.get("evaluation") != record:
        return {"status": "blocked", "reason": "wcag_evaluation_registration_reread_failed"}
    return {"status": "registered", "evaluation_ref": record["evaluation_ref"],
            "evaluation_revision": record["evaluation_revision"],
            "provider_revision": verified["provider_revision"], "idempotent": False}


def read_wcag_evaluation_state(workflow_root: str | Path, workflow_ref: str, evaluation_ref: str,
                               *, evaluation_revision: str | None = None,
                               project_context_ref: str, project_context_revision: str,
                               project_context_fingerprint: str,
                               workflow_state_root_content_identity: str) -> dict[str, Any]:
    state_result = read_sqlite_workflow_state(workflow_root, workflow_ref)
    if state_result.get("status") != "current":
        return state_result
    evaluations = state_result["state"].get("wcag_evaluations")
    if not isinstance(evaluations, dict):
        return {"status": "blocked", "reason": "wcag_evaluation_state_missing"}
    record = evaluations.get(evaluation_ref)
    if not isinstance(record, dict):
        return {"status": "blocked", "reason": "wcag_evaluation_not_registered"}
    if evaluation_revision is not None and record.get("evaluation_revision") != evaluation_revision:
        return {"status": "conflict", "reason": "wcag_evaluation_revision_changed",
                "current_evaluation_revision": record.get("evaluation_revision")}
    if any(record.get(key) != value for key, value in (
            ("project_context_ref", project_context_ref),
            ("project_context_revision", project_context_revision),
            ("project_context_fingerprint", project_context_fingerprint),
            ("workflow_state_root_content_identity", workflow_state_root_content_identity))):
        return {"status": "conflict", "reason": "workflow_project_context_changed"}
    if any(state_result["state"].get(key) != value for key, value in (
            ("project_context_ref", project_context_ref),
            ("project_context_revision", project_context_revision),
            ("project_context_fingerprint", project_context_fingerprint),
            ("workflow_state_root_content_identity", workflow_state_root_content_identity))):
        return {"status": "conflict", "reason": "workflow_project_context_changed"}
    required = {"evaluation_ref", "evaluation_revision", "wcag_version", "level", "initialization_fingerprint",
                "evaluator_ref", "commissioner_ref", "product_enclosure_ref",
                "project_context_ref", "project_context_revision", "project_context_fingerprint",
                "workflow_state_root_content_identity",
                "product_scope_ref", "scope_coverage", "scope_evidence_refs", "source_artifacts",
                "selected_samples", "presentation_variations", "process_memberships", "canonical_plan_basis",
                "canonical_plan_fingerprint", "criterion_rows", "criterion_evaluation_refs",
                "previous_evaluation_revision", "record_status", "report_status", "report_fingerprint",
                "report_result_refs", "report_criterion_evaluation_refs"}
    if set(record) != required or record.get("record_status") != "plan-finalized":
        return {"status": "blocked", "reason": "wcag_evaluation_state_corrupt"}
    if (not isinstance(record.get("canonical_plan_fingerprint"), str)
            or not _SHA256_REF.fullmatch(record["canonical_plan_fingerprint"])
            or not isinstance(record.get("criterion_rows"), list)
            or not isinstance(record.get("criterion_evaluation_refs"), list)):
        return {"status": "blocked", "reason": "wcag_evaluation_state_corrupt"}
    return {"status": "current", "evaluation_ref": evaluation_ref,
            "evaluation_revision": record["evaluation_revision"], "evaluation": record,
            "provider_revision": state_result["state_revision"], "workflow_ref": state_result["workflow_ref"]}


def validate_wcag_plan_against_state(evaluation: dict[str, Any], canonical_criterion_plan: dict[str, Any]) -> dict[str, Any]:
    try:
        normalized = _canonical_wcag_basis(canonical_criterion_plan)
        record_basis = evaluation.get("canonical_plan_basis")
        if (normalized["basis"] != record_basis
                or normalized["criterion_evaluation_refs"] != evaluation.get("criterion_evaluation_refs")
                or normalized["criteria"] != evaluation.get("criterion_rows")
                or "sha256:" + content_identity(canonical_criterion_plan) != evaluation.get("canonical_plan_fingerprint")):
            return {"status": "conflict", "reason": "canonical_wcag_plan_does_not_match_saved_current_scope"}
        if (canonical_criterion_plan.get("evaluation_ref") != evaluation.get("evaluation_ref")
                or canonical_criterion_plan.get("evaluation_revision") != evaluation.get("evaluation_revision")
                or canonical_criterion_plan.get("wcag_version") != evaluation.get("wcag_version")
                or canonical_criterion_plan.get("level") != evaluation.get("level")):
            return {"status": "conflict", "reason": "canonical_wcag_plan_target_or_revision_mismatch"}
    except (AttributeError, TypeError, ValueError):
        return {"status": "blocked", "reason": "canonical_wcag_plan_invalid"}
    return {"status": "current", "plan_fingerprint": evaluation["canonical_plan_fingerprint"]}


def _wcag_report_result_summary(evaluation: dict[str, Any], sample_results: Any) -> dict[str, Any]:
    if not isinstance(sample_results, list):
        raise ValueError("wcag_report_results_invalid")
    expected = {row["criterion_evaluation_ref"]: row for row in evaluation["criterion_rows"]}
    actual: dict[str, dict[str, Any]] = {}
    for row in sample_results:
        if not isinstance(row, dict):
            raise ValueError("wcag_report_result_invalid")
        ref = row.get("criterion_evaluation_ref")
        if not _safe_stored_ref(ref) or ref in actual:
            raise ValueError("wcag_report_result_duplicate_or_invalid")
        planned = expected.get(ref)
        if planned is None:
            raise ValueError("wcag_report_result_extra")
        identity_fields = ("evaluation_ref", "evaluation_revision", "sample_ref", "variation_ref", "process_ref")
        if any(row.get(key) != planned.get(key) for key in identity_fields):
            raise ValueError("wcag_report_result_identity_mismatch")
        if (row.get("requirement_ref") != planned.get("criterion_ref")
                or row.get("freshness_status") != "current"
                or row.get("result") not in {"satisfied", "not-satisfied"}
                or not _safe_stored_ref(row.get("sample_result_ref"))):
            raise ValueError("wcag_report_result_not_current_complete")
        actual[ref] = {"sample_result_ref": row["sample_result_ref"],
                       "criterion_evaluation_ref": ref,
                       "evaluation_ref": row["evaluation_ref"],
                       "evaluation_revision": row["evaluation_revision"],
                       "sample_ref": row["sample_ref"], "variation_ref": row["variation_ref"],
                       "process_ref": row.get("process_ref"), "requirement_ref": row["requirement_ref"],
                       "result": row["result"], "freshness_status": row["freshness_status"]}
    if set(actual) != set(expected):
        raise ValueError("wcag_report_result_set_incomplete")
    summary = [actual[key] for key in sorted(actual)]
    return {"results": summary, "fingerprint": "sha256:" + content_identity(summary)}


def finalize_wcag_report(workflow_root: str | Path, workflow_ref: str, *, expected_provider_revision: str,
                         evaluation_ref: str, evaluation_revision: str, canonical_criterion_plan: dict[str, Any],
                         sample_results: list[dict[str, Any]], closure_status: str,
                         project_context_ref: str, project_context_revision: str,
                         project_context_fingerprint: str,
                         workflow_state_root_content_identity: str) -> dict[str, Any]:
    """Persist report completion only for a current, fully matched canonical result set."""
    if closure_status != "complete":
        return {"status": "blocked", "reason": "wcag_report_closure_not_complete"}
    current = read_sqlite_workflow_state(workflow_root, workflow_ref, expected_revision=expected_provider_revision)
    if current.get("status") != "current":
        return {"status": current.get("status", "blocked"), "reason": current.get("reason", "workflow_state_revision_changed")}
    evaluation = read_wcag_evaluation_state(workflow_root, workflow_ref, evaluation_ref,
                                            evaluation_revision=evaluation_revision,
                                            project_context_ref=project_context_ref,
                                            project_context_revision=project_context_revision,
                                            project_context_fingerprint=project_context_fingerprint,
                                            workflow_state_root_content_identity=workflow_state_root_content_identity)
    if evaluation.get("status") != "current" or evaluation.get("provider_revision") != expected_provider_revision:
        return {"status": "conflict", "reason": "wcag_evaluation_state_changed_before_report_close"}
    plan_check = validate_wcag_plan_against_state(evaluation["evaluation"], canonical_criterion_plan)
    if plan_check.get("status") != "current":
        return {"status": plan_check.get("status", "blocked"), "reason": plan_check.get("reason", "canonical_wcag_plan_invalid")}
    try:
        result_summary = _wcag_report_result_summary(evaluation["evaluation"], sample_results)
    except (KeyError, TypeError, ValueError):
        return {"status": "blocked", "reason": "wcag_report_result_set_incomplete_or_stale"}
    report_fingerprint = "sha256:" + content_identity({
        "evaluation_ref": evaluation_ref,
        "evaluation_revision": evaluation_revision,
        "canonical_plan_fingerprint": evaluation["evaluation"]["canonical_plan_fingerprint"],
        "results_fingerprint": result_summary["fingerprint"],
    })
    state = current["state"]
    record = state["wcag_evaluations"][evaluation_ref]
    if record.get("report_status") == "complete":
        if record.get("report_fingerprint") == report_fingerprint:
            return {"status": "complete", "provider_revision": expected_provider_revision,
                    "evaluation_ref": evaluation_ref, "evaluation_revision": evaluation_revision,
                    "report_fingerprint": report_fingerprint, "idempotent": True}
        return {"status": "conflict", "reason": "completed_wcag_report_is_immutable"}
    if record.get("report_status") != "open":
        return {"status": "blocked", "reason": "wcag_report_state_invalid"}
    record["report_status"] = "complete"
    record["report_fingerprint"] = report_fingerprint
    record["report_result_refs"] = [row["sample_result_ref"] for row in result_summary["results"]]
    record["report_criterion_evaluation_refs"] = [row["criterion_evaluation_ref"] for row in result_summary["results"]]
    # Keep the saved record finite: no result narrative, DOM text, URL, or semantic prose is persisted.
    state["wcag_evaluations"][evaluation_ref] = record
    written = conditional_write_sqlite_workflow_state(workflow_root, workflow_ref,
                                                      expected_provider_revision, state)
    if written.get("status") != "written":
        return {"status": written.get("status", "blocked"),
                "reason": written.get("reason", "workflow_state_conditional_write_failed")}
    reread = read_wcag_evaluation_state(workflow_root, workflow_ref, evaluation_ref,
                                        evaluation_revision=evaluation_revision,
                                        project_context_ref=project_context_ref,
                                        project_context_revision=project_context_revision,
                                        project_context_fingerprint=project_context_fingerprint,
                                        workflow_state_root_content_identity=workflow_state_root_content_identity)
    verified = reread.get("status") == "current" and reread.get("evaluation", {}).get("report_status") == "complete"
    verified = verified and reread.get("evaluation", {}).get("report_fingerprint") == report_fingerprint
    verified = verified and reread.get("provider_revision") == written.get("state_revision")
    if not verified:
        return {"status": "blocked", "reason": "wcag_report_close_reread_failed"}
    return {"status": "complete", "provider_revision": reread["provider_revision"],
            "evaluation_ref": evaluation_ref, "evaluation_revision": evaluation_revision,
            "report_fingerprint": report_fingerprint, "idempotent": False}


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
