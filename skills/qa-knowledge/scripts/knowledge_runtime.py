"""Standalone deterministic QA knowledge identity, currentness, and create helpers."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Any


KINDS = {"test_subject_or_mechanism", "test_focus", "test_environment"}
STATES = {"有効", "要再検証", "置換済み"}
_ENTRY_BLOCK = re.compile(r"```json\s*\n(.*?)\n```", re.DOTALL)
_SECRET = re.compile(r"(?i)(?:password|access[_-]?token|client[_-]?secret|api[_-]?key)\s*[:=]\s*['\"]?[A-Za-z0-9_./+=-]{8,}")


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def canonical_entry_ref(identity: dict[str, Any]) -> str:
    if not isinstance(identity, dict) or not identity:
        raise ValueError("semantic identity must be a non-empty structured object")
    return f"KN-{hashlib.sha256(_canonical(identity)).hexdigest()}"


def scan_knowledge_root(root: str | Path, *, max_entries: int | None = None) -> dict[str, Any]:
    path = Path(root)
    entries: list[Path] = []
    try:
        with os.scandir(path) as listing:
            for item in listing:
                if item.is_file(follow_symlinks=False) and item.name.lower().endswith(".md"):
                    entries.append(Path(item.path))
    except OSError as exc:
        return {"entry_paths": [], "complete": False, "unresolved": [f"root_listing_failed:{type(exc).__name__}"]}
    entries.sort(key=lambda item: item.name)
    truncated = max_entries is not None and len(entries) > max_entries
    if truncated:
        entries = entries[:max_entries]
    return {"entry_paths": [str(item) for item in entries], "complete": not truncated, "unresolved": ["root_listing_truncated"] if truncated else []}


def validate_entry(entry: dict[str, Any], *, current_dependencies: dict[str, str] | None = None, entry_revision: str | None = None) -> dict[str, Any]:
    issues: list[str] = []
    required = ("entry_ref", "identity", "kind", "content", "scope_refs", "applicability", "provenance", "currentness_dependencies", "last_verified", "state", "related_qa_refs")
    issues.extend(f"missing_field:{key}" for key in required if key not in entry)
    try:
        expected_ref = canonical_entry_ref(entry.get("identity"))
    except (TypeError, ValueError):
        expected_ref = None
    if expected_ref and entry.get("entry_ref") != expected_ref:
        issues.append("entry_ref_does_not_match_identity")
    if entry.get("kind") not in KINDS:
        issues.append("invalid_kind")
    if entry.get("state") not in STATES:
        issues.append("invalid_state")
    if not isinstance(entry.get("content"), str) or not entry.get("content", "").strip():
        issues.append("empty_content")
    elif _SECRET.search(entry["content"]):
        issues.append("secret_value_detected")
    if not isinstance(entry.get("scope_refs"), list) or not entry.get("scope_refs"):
        issues.append("scope_required")
    applicability = entry.get("applicability")
    if not isinstance(applicability, dict) or not isinstance(applicability.get("environment"), list) or not applicability.get("environment") or not applicability.get("version"):
        issues.append("applicability_required")
    for field in ("provenance", "currentness_dependencies"):
        refs = entry.get(field)
        if not isinstance(refs, list) or not refs:
            issues.append(f"{field}_must_be_list")
            continue
        for ref in refs:
            if not isinstance(ref, dict) or not ref.get("ref") or not ref.get("revision"):
                issues.append(f"{field}_requires_ref_and_revision")
                break
    currentness = compare_currentness(entry.get("currentness_dependencies", []), current_dependencies) if current_dependencies is not None else {"status": "unresolved", "changed_refs": [], "unresolved": ["current_dependencies_not_checked"]}
    if entry.get("state") == "有効" and not entry_revision:
        issues.append("entry_storage_revision_unavailable")
    if entry.get("state") == "置換済み" and not entry.get("replacement_ref"):
        issues.append("superseded_entry_requires_replacement_ref")
    if entry.get("state") != "置換済み" and entry.get("replacement_ref"):
        issues.append("replacement_ref_only_valid_for_superseded_entry")
    return {"valid": not issues, "issues": issues, "currentness": currentness}


def compare_currentness(stored_dependencies: list[dict[str, Any]], current_dependencies: dict[str, str] | None) -> dict[str, Any]:
    if current_dependencies is None:
        return {"status": "unresolved", "changed_refs": [], "unresolved": ["current_dependency_snapshot_missing"]}
    changed: list[str] = []
    unresolved: list[str] = []
    for dependency in stored_dependencies:
        if not isinstance(dependency, dict) or not dependency.get("ref") or not dependency.get("revision"):
            unresolved.append("invalid_dependency_record")
            continue
        ref = dependency["ref"]
        if ref not in current_dependencies:
            unresolved.append(ref)
        elif current_dependencies[ref] != dependency["revision"]:
            changed.append(ref)
    if unresolved:
        status = "unresolved"
    elif changed:
        status = "stale"
    else:
        status = "current"
    return {"status": status, "changed_refs": sorted(changed), "unresolved": sorted(unresolved)}


def plan_create(*, identity: dict[str, Any], source_verified: bool, scope_known: bool, applicability_known: bool, dependencies_known: bool, root_snapshot_complete: bool, native_atomic_create_if_absent: bool) -> dict[str, Any]:
    missing = [name for name, value in (("source", source_verified), ("scope", scope_known), ("applicability", applicability_known), ("dependencies", dependencies_known), ("root_snapshot", root_snapshot_complete)) if not value]
    if missing:
        return {"status": "blocked", "reason": "entry_activation_prerequisites_missing", "missing": missing}
    if not native_atomic_create_if_absent:
        return {"status": "blocked", "reason": "atomic_create_if_absent_unavailable"}
    return {"status": "create_if_absent_required", "entry_ref": canonical_entry_ref(identity), "root_snapshot_complete": True}


def _atomic_create(path: Path, content: bytes) -> dict[str, Any]:
    temporary: str | None = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(mode="wb", dir=path.parent, prefix=f".{path.name}.", delete=False) as stream:
            temporary = stream.name
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, path, follow_symlinks=False)
        return {"status": "created", "path": str(path), "atomic": True}
    except FileExistsError:
        if path.exists() and path.is_file() and not path.is_symlink():
            return {"status": "conflict", "path": str(path), "atomic": True}
        return {"status": "blocked", "path": str(path), "atomic": False, "reason": "target_parent_unavailable"}
    except OSError as exc:
        return {"status": "blocked", "path": str(path), "atomic": False, "reason": f"atomic_create_unavailable:{type(exc).__name__}"}
    finally:
        if temporary:
            try:
                os.unlink(temporary)
            except OSError:
                pass


def render_entry(entry: dict[str, Any]) -> bytes:
    body = json.dumps(entry, ensure_ascii=False, indent=2, sort_keys=True)
    return ("# QA Knowledge entry\n\n```json\n" + body + "\n```\n").encode("utf-8")


def _parse_entry(markdown: str) -> dict[str, Any]:
    matches = _ENTRY_BLOCK.findall(markdown)
    if len(matches) != 1:
        raise ValueError("entry_requires_exactly_one_json_block")
    value = json.loads(matches[0])
    if not isinstance(value, dict):
        raise ValueError("entry_json_root_must_be_object")
    return value


def create_entry(root: str | Path, entry: dict[str, Any], *, complete_root_snapshot: bool, atomic_create_if_absent_available: bool, current_dependencies: dict[str, str] | None) -> dict[str, Any]:
    """Create at the canonical identity path; a conflict is re-read, never forked."""
    if not complete_root_snapshot:
        return {"status": "blocked", "reason": "identity_snapshot_incomplete"}
    if not atomic_create_if_absent_available:
        return {"status": "blocked", "reason": "atomic_create_if_absent_unavailable"}
    try:
        entry_ref = canonical_entry_ref(entry.get("identity"))
    except (TypeError, ValueError):
        return {"status": "blocked", "reason": "semantic_identity_missing"}
    if entry.get("entry_ref") != entry_ref:
        return {"status": "blocked", "reason": "entry_ref_does_not_match_identity", "expected_entry_ref": entry_ref}
    if entry.get("state") != "有効":
        return {"status": "blocked", "reason": "new_entry_must_be_verified_and_current"}
    path = Path(root) / f"{entry_ref}.md"
    raw = render_entry(entry)
    revision = "sha256:" + hashlib.sha256(raw).hexdigest()
    validation = validate_entry(entry, current_dependencies=current_dependencies, entry_revision=revision)
    if not validation["valid"]:
        return {"status": "blocked", "reason": "entry_contract_invalid", "issues": validation["issues"]}
    if validation["currentness"].get("status") != "current":
        return {"status": "blocked", "reason": "entry_dependencies_not_current", "currentness": validation["currentness"]}
    result = _atomic_create(path, raw)
    if result["status"] == "created":
        return {**result, "entry_ref": entry_ref, "entry_revision": revision, "revision_kind": "local_exact_content_token_not_a_cas_condition"}
    if result["status"] == "conflict":
        try:
            existing = _parse_entry(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError):
            return {"status": "blocked", "reason": "existing_canonical_target_unreadable", "entry_ref": entry_ref}
        if existing.get("identity") == entry.get("identity"):
            existing_revision = "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
            return {"status": "existing_identity", "entry_ref": entry_ref, "entry_revision": existing_revision, "existing_entry": existing, "next": "revalidation_or_expected_revision_update"}
        return {"status": "blocked", "reason": "canonical_identity_collision_requires_review", "entry_ref": entry_ref}
    return result


def read_entry(root: str | Path, entry_ref: str, *, expected_revision: str | None = None) -> dict[str, Any]:
    if not entry_ref.startswith("KN-"):
        return {"status": "blocked", "reason": "invalid_entry_ref"}
    path = Path(root) / f"{entry_ref}.md"
    if path.is_symlink():
        return {"status": "blocked", "reason": "entry_symlink_not_allowed"}
    try:
        raw = path.read_bytes()
        entry = _parse_entry(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError):
        return {"status": "blocked", "reason": "entry_unreadable"}
    revision = "sha256:" + hashlib.sha256(raw).hexdigest()
    if expected_revision and expected_revision != revision:
        return {"status": "blocked", "reason": "historical_revision_unavailable", "current_revision": revision}
    return {"status": "current", "entry": entry, "entry_revision": revision, "historical_revision_available": False}


def plan_update(*, expected_entry_revision: str | None, native_atomic_conditional_write: bool, target_entry_identity_unchanged: bool = True) -> dict[str, Any]:
    if not expected_entry_revision:
        return {"status": "blocked", "reason": "entry_revision_unavailable"}
    if not target_entry_identity_unchanged:
        return {"status": "replacement_required", "reason": "semantic_identity_changed"}
    if not native_atomic_conditional_write:
        return {"status": "blocked", "reason": "atomic_conditional_write_unavailable"}
    return {"status": "conditional_write_required", "expected_revision": expected_entry_revision}


def handle_update_conflict(*, target_entry_revision_changed: bool, different_entry_only_changed: bool) -> dict[str, Any]:
    if target_entry_revision_changed:
        return {"status": "reread_and_semantic_reevaluation", "auto_merge": False}
    if different_entry_only_changed:
        return {"status": "target_revision_recheck_required", "auto_merge": False}
    return {"status": "unresolved", "auto_merge": False}


def plan_replacement(*, old_entry_ref: str, new_entry_ref: str, native_atomic_multi_entry_update: bool) -> dict[str, Any]:
    if not old_entry_ref or not new_entry_ref or old_entry_ref == new_entry_ref:
        return {"status": "blocked", "reason": "replacement_refs_invalid"}
    if not native_atomic_multi_entry_update:
        return {"status": "blocked", "reason": "replacement_requires_atomic_old_new_update"}
    return {"status": "conditional_multi_entry_update_required", "old_entry_ref": old_entry_ref, "new_entry_ref": new_entry_ref}


def lookup(entries: list[dict[str, Any]], *, scope_refs: set[str], kind: str | None, environment: str | None, version: str | None, current_dependencies: dict[str, str], listing_complete: bool) -> dict[str, Any]:
    if not listing_complete:
        return {"status": "incomplete", "entries": [], "complete": False, "reason": "knowledge_root_listing_incomplete"}
    usable: list[dict[str, Any]] = []
    historical: list[str] = []
    issues: list[str] = []
    seen: set[str] = set()
    if not isinstance(entries, list):
        return {"status": "incomplete", "entries": [], "complete": False, "reason": "entry_listing_invalid"}
    if any(not isinstance(entry, dict) for entry in entries):
        return {"status": "incomplete", "entries": [], "complete": False, "reason": "entry_parse_failed"}
    for entry in sorted(entries, key=lambda item: str(item.get("entry_ref", ""))):
        entry_ref = entry.get("entry_ref")
        if not isinstance(entry_ref, str) or not entry_ref or entry_ref in seen:
            issues.append("entry_ref_missing_or_duplicate")
            continue
        seen.add(entry_ref)
        validation = validate_entry(entry, current_dependencies=current_dependencies, entry_revision=entry.get("entry_revision"))
        if not validation["valid"]:
            issues.extend(f"{entry_ref}:{issue}" for issue in validation["issues"])
        currentness = compare_currentness(entry.get("currentness_dependencies", []), current_dependencies)
        if currentness.get("status") == "unresolved":
            issues.append(f"{entry_ref}:currentness_unresolved")
        applicability = entry.get("applicability", {})
        applies = bool(scope_refs & set(entry.get("scope_refs", [])))
        applies = applies and (kind is None or entry.get("kind") == kind)
        applies = applies and (environment is None or environment in applicability.get("environment", []))
        applies = applies and (version is None or applicability.get("version") in {version, "*"})
        if not applies:
            continue
        if entry.get("state") == "有効" and currentness.get("status") == "current" and entry.get("entry_revision"):
            usable.append({"entry_ref": entry.get("entry_ref"), "entry_revision": entry.get("entry_revision"), "content": entry.get("content")})
        else:
            historical.append(entry.get("entry_ref", ""))
    if issues:
        return {"status": "incomplete", "entries": [], "complete": False, "unresolved": sorted(set(issues))}
    return {"status": "complete", "entries": usable, "historical_excluded_refs": sorted(ref for ref in historical if ref), "complete": True}
