"""Standalone deterministic QA knowledge identity, currentness, and create helpers."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any

KINDS = {"test_subject_or_mechanism", "test_focus", "test_environment"}
STATES = {"有効", "要再検証", "置換済み"}
_ENTRY_BLOCK = re.compile(r"```json\s*\n(.*?)\n```", re.DOTALL)
_ENTRY_REF = re.compile(r"^KN-[0-9a-f]{64}$")
_SECRET = re.compile(
    r"(?i)(?:password|access[_-]?token|client[_-]?secret|api[_-]?key)\s*[:=]\s*['\"]?[A-Za-z0-9_./+=-]{8,}"
)


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def canonical_entry_ref(identity: dict[str, Any]) -> str:
    if not isinstance(identity, dict) or not identity:
        raise ValueError("semantic identity must be a non-empty structured object")
    return f"KN-{hashlib.sha256(_canonical(identity)).hexdigest()}"


def _one_of(value: Any, allowed: set[str]) -> bool:
    """Membership test that never raises on JSON arrays or objects."""
    return isinstance(value, str) and value in allowed


def _string_list(value: Any) -> bool:
    return (
        isinstance(value, list)
        and bool(value)
        and all(isinstance(item, str) and item for item in value)
    )


def identity_issues(entry: dict[str, Any]) -> list[str]:
    """Check that the hashed identity and the entry's applicability fields agree.

    The entry_ref hash alone is not enough: the identity names the kind and scope
    the entry was keyed on, and the top-level fields are what lookup applies.
    Arrays are compared as written; their order is never normalized.
    """
    identity = entry.get("identity")
    if not isinstance(identity, dict) or not identity:
        return ["identity_must_be_non_empty_object"]
    issues: list[str] = []
    if not _one_of(identity.get("kind"), KINDS):
        issues.append("identity_kind_invalid")
    elif identity.get("kind") != entry.get("kind"):
        issues.append("identity_kind_mismatch")
    if not _string_list(identity.get("scope_refs")):
        issues.append("identity_scope_refs_required")
    elif identity.get("scope_refs") != entry.get("scope_refs"):
        issues.append("identity_scope_refs_mismatch")
    return issues


def lookup_input(read_result: dict[str, Any]) -> dict[str, Any]:
    """Build the lookup input from a current read_entry() result.

    The stored revision is attached to a copy of the entry; the revision is
    storage metadata and is never written into the entry body.
    """
    if (
        not isinstance(read_result, dict)
        or read_result.get("status") != "current"
        or not isinstance(read_result.get("entry"), dict)
        or not read_result.get("entry_revision")
    ):
        raise ValueError("lookup_input_requires_current_read_with_entry_revision")
    return {
        **read_result["entry"],
        "entry_revision": read_result["entry_revision"],
    }


def scan_knowledge_root(
    root: str | Path, *, max_entries: int | None = None
) -> dict[str, Any]:
    path = Path(root)
    entries: list[Path] = []
    try:
        with os.scandir(path) as listing:
            for item in listing:
                if item.is_file(follow_symlinks=False) and item.name.lower().endswith(
                    ".md"
                ):
                    entries.append(Path(item.path))
    except OSError as exc:
        return {
            "entry_paths": [],
            "complete": False,
            "unresolved": [f"root_listing_failed:{type(exc).__name__}"],
        }
    entries.sort(key=lambda item: item.name)
    truncated = max_entries is not None and len(entries) > max_entries
    if truncated:
        entries = entries[:max_entries]
    return {
        "entry_paths": [str(item) for item in entries],
        "complete": not truncated,
        "unresolved": ["root_listing_truncated"] if truncated else [],
    }


def validate_entry(
    entry: dict[str, Any],
    *,
    current_dependencies: dict[str, str] | None = None,
    entry_revision: str | None = None,
) -> dict[str, Any]:
    if not isinstance(entry, dict):
        return {
            "valid": False,
            "issues": ["entry_must_be_object"],
            "currentness": {
                "status": "unresolved",
                "changed_refs": [],
                "unresolved": ["entry_must_be_object"],
            },
        }
    issues: list[str] = []
    required = (
        "entry_ref",
        "identity",
        "kind",
        "content",
        "scope_refs",
        "applicability",
        "provenance",
        "currentness_dependencies",
        "last_verified",
        "state",
        "related_qa_refs",
    )
    issues.extend(f"missing_field:{key}" for key in required if key not in entry)
    try:
        expected_ref = canonical_entry_ref(entry.get("identity"))
    except (TypeError, ValueError):
        expected_ref = None
    if expected_ref and entry.get("entry_ref") != expected_ref:
        issues.append("entry_ref_does_not_match_identity")
    issues.extend(identity_issues(entry))
    if not _one_of(entry.get("kind"), KINDS):
        issues.append("invalid_kind")
    if not _one_of(entry.get("state"), STATES):
        issues.append("invalid_state")
    if (
        not isinstance(entry.get("content"), str)
        or not entry.get("content", "").strip()
    ):
        issues.append("empty_content")
    elif _SECRET.search(entry["content"]):
        issues.append("secret_value_detected")
    if not _string_list(entry.get("scope_refs")):
        issues.append("scope_required")
    applicability = entry.get("applicability")
    if (
        not isinstance(applicability, dict)
        or not isinstance(applicability.get("environment"), list)
        or not applicability.get("environment")
        or not applicability.get("version")
    ):
        issues.append("applicability_required")
    for field in ("provenance", "currentness_dependencies"):
        refs = entry.get(field)
        if not isinstance(refs, list) or not refs:
            issues.append(f"{field}_must_be_list")
            continue
        for ref in refs:
            if (
                not isinstance(ref, dict)
                or not isinstance(ref.get("ref"), str)
                or not ref["ref"]
                or not isinstance(ref.get("revision"), str)
                or not ref["revision"]
            ):
                issues.append(f"{field}_requires_ref_and_revision")
                break
    currentness = (
        compare_currentness(
            entry.get("currentness_dependencies", []), current_dependencies
        )
        if current_dependencies is not None
        else {
            "status": "unresolved",
            "changed_refs": [],
            "unresolved": ["current_dependencies_not_checked"],
        }
    )
    if entry.get("state") == "有効" and not entry_revision:
        issues.append("entry_storage_revision_unavailable")
    if entry.get("state") == "置換済み" and not entry.get("replacement_ref"):
        issues.append("superseded_entry_requires_replacement_ref")
    if entry.get("state") != "置換済み" and entry.get("replacement_ref"):
        issues.append("replacement_ref_only_valid_for_superseded_entry")
    return {"valid": not issues, "issues": issues, "currentness": currentness}


def compare_currentness(
    stored_dependencies: list[dict[str, Any]],
    current_dependencies: dict[str, str] | None,
) -> dict[str, Any]:
    if current_dependencies is None:
        return {
            "status": "unresolved",
            "changed_refs": [],
            "unresolved": ["current_dependency_snapshot_missing"],
        }
    if not isinstance(stored_dependencies, list) or not isinstance(
        current_dependencies, dict
    ):
        return {
            "status": "unresolved",
            "changed_refs": [],
            "unresolved": ["invalid_dependency_record"],
        }
    changed: list[str] = []
    unresolved: list[str] = []
    for dependency in stored_dependencies:
        if (
            not isinstance(dependency, dict)
            or not isinstance(dependency.get("ref"), str)
            or not dependency.get("ref")
            or not isinstance(dependency.get("revision"), str)
            or not dependency["revision"]
        ):
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
    return {
        "status": status,
        "changed_refs": sorted(changed),
        "unresolved": sorted(unresolved),
    }


def plan_create(
    *,
    identity: dict[str, Any],
    source_verified: bool,
    scope_known: bool,
    applicability_known: bool,
    dependencies_known: bool,
    root_snapshot_complete: bool,
    native_atomic_create_if_absent: bool,
) -> dict[str, Any]:
    missing = [
        name
        for name, value in (
            ("source", source_verified),
            ("scope", scope_known),
            ("applicability", applicability_known),
            ("dependencies", dependencies_known),
            ("root_snapshot", root_snapshot_complete),
        )
        if not value
    ]
    if missing:
        return {
            "status": "blocked",
            "reason": "entry_activation_prerequisites_missing",
            "missing": missing,
        }
    if not native_atomic_create_if_absent:
        return {"status": "blocked", "reason": "atomic_create_if_absent_unavailable"}
    return {
        "status": "create_if_absent_required",
        "entry_ref": canonical_entry_ref(identity),
        "root_snapshot_complete": True,
    }


def _atomic_create(path: Path, content: bytes) -> dict[str, Any]:
    temporary: str | None = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="wb", dir=path.parent, prefix=f".{path.name}.", delete=False
        ) as stream:
            temporary = stream.name
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, path, follow_symlinks=False)
        return {"status": "created", "path": str(path), "atomic": True}
    except FileExistsError:
        if path.exists() and path.is_file() and not path.is_symlink():
            return {"status": "conflict", "path": str(path), "atomic": True}
        return {
            "status": "blocked",
            "path": str(path),
            "atomic": False,
            "reason": "target_parent_unavailable",
        }
    except OSError as exc:
        return {
            "status": "blocked",
            "path": str(path),
            "atomic": False,
            "reason": f"atomic_create_unavailable:{type(exc).__name__}",
        }
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


def create_entry(
    root: str | Path,
    entry: dict[str, Any],
    *,
    complete_root_snapshot: bool,
    atomic_create_if_absent_available: bool,
    current_dependencies: dict[str, str] | None,
) -> dict[str, Any]:
    """Create at the canonical identity path; a conflict is re-read, never forked."""
    if not isinstance(entry, dict):
        return {"status": "blocked", "reason": "semantic_identity_missing"}
    if not complete_root_snapshot:
        return {"status": "blocked", "reason": "identity_snapshot_incomplete"}
    if not atomic_create_if_absent_available:
        return {"status": "blocked", "reason": "atomic_create_if_absent_unavailable"}
    try:
        entry_ref = canonical_entry_ref(entry.get("identity"))
    except (TypeError, ValueError):
        return {"status": "blocked", "reason": "semantic_identity_missing"}
    if entry.get("entry_ref") != entry_ref:
        return {
            "status": "blocked",
            "reason": "entry_ref_does_not_match_identity",
            "expected_entry_ref": entry_ref,
        }
    identity_problems = identity_issues(entry)
    if identity_problems:
        return {
            "status": "blocked",
            "reason": "entry_identity_invalid",
            "issues": identity_problems,
        }
    if "entry_revision" in entry:
        return {"status": "blocked", "reason": "entry_revision_must_not_be_in_body"}
    if entry.get("state") != "有効":
        return {"status": "blocked", "reason": "new_entry_must_be_verified_and_current"}
    path = Path(root) / f"{entry_ref}.md"
    raw = render_entry(entry)
    revision = "sha256:" + hashlib.sha256(raw).hexdigest()
    validation = validate_entry(
        entry, current_dependencies=current_dependencies, entry_revision=revision
    )
    if not validation["valid"]:
        return {
            "status": "blocked",
            "reason": "entry_contract_invalid",
            "issues": validation["issues"],
        }
    if validation["currentness"].get("status") != "current":
        return {
            "status": "blocked",
            "reason": "entry_dependencies_not_current",
            "currentness": validation["currentness"],
        }
    result = _atomic_create(path, raw)
    if result["status"] == "created":
        # Independent readback: the returned revision is the one actually stored.
        readback = read_entry(root, entry_ref)
        if (
            readback["status"] != "current"
            or readback["entry_revision"] != revision
            or readback["entry"] != entry
        ):
            return {
                "status": "blocked",
                "reason": "created_entry_readback_mismatch",
                "entry_ref": entry_ref,
                "created_path": str(path),
            }
        return {
            **result,
            "entry_ref": entry_ref,
            "entry_revision": readback["entry_revision"],
            "readback_verified": True,
            "revision_kind": "local_exact_content_token_not_a_cas_condition",
        }
    if result["status"] == "conflict":
        try:
            existing = _parse_entry(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError):
            return {
                "status": "blocked",
                "reason": "existing_canonical_target_unreadable",
                "entry_ref": entry_ref,
            }
        existing_problems = identity_issues(existing)
        if existing.get("entry_ref") != entry_ref or existing_problems:
            return {
                "status": "blocked",
                "reason": "existing_canonical_target_identity_invalid",
                "entry_ref": entry_ref,
                "issues": existing_problems,
            }
        if existing.get("identity") == entry.get("identity"):
            existing_revision = (
                "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
            )
            return {
                "status": "existing_identity",
                "entry_ref": entry_ref,
                "entry_revision": existing_revision,
                "existing_entry": existing,
                "next": "revalidation_or_expected_revision_update",
            }
        return {
            "status": "blocked",
            "reason": "canonical_identity_collision_requires_review",
            "entry_ref": entry_ref,
        }
    return result


def read_entry(
    root: str | Path, entry_ref: str, *, expected_revision: str | None = None
) -> dict[str, Any]:
    if not isinstance(entry_ref, str) or not _ENTRY_REF.fullmatch(entry_ref):
        return {"status": "blocked", "reason": "invalid_entry_ref"}
    path = Path(root) / f"{entry_ref}.md"
    if path.is_symlink():
        return {"status": "blocked", "reason": "entry_symlink_not_allowed"}
    try:
        raw = path.read_bytes()
        entry = _parse_entry(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError):
        return {"status": "blocked", "reason": "entry_unreadable"}
    try:
        identity_ref = canonical_entry_ref(entry.get("identity"))
    except (TypeError, ValueError):
        return {"status": "blocked", "reason": "entry_identity_mismatch"}
    if entry.get("entry_ref") != entry_ref or identity_ref != entry_ref:
        return {"status": "blocked", "reason": "entry_identity_mismatch"}
    identity_problems = identity_issues(entry)
    if identity_problems:
        return {
            "status": "blocked",
            "reason": "entry_identity_invalid",
            "issues": identity_problems,
        }
    revision = "sha256:" + hashlib.sha256(raw).hexdigest()
    if expected_revision and expected_revision != revision:
        return {
            "status": "blocked",
            "reason": "historical_revision_unavailable",
            "current_revision": revision,
        }
    return {
        "status": "current",
        "entry": entry,
        "entry_revision": revision,
        "historical_revision_available": False,
    }


def plan_update(
    *,
    expected_entry_revision: str | None,
    native_atomic_conditional_write: bool,
    target_entry_identity_unchanged: bool = True,
    current_entry: dict[str, Any] | None = None,
    updated_entry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Plan a same-entry update. Both entries are required and checked.

    The identity invariants cannot be skipped by omitting the entries.
    """
    if not isinstance(current_entry, dict) or not isinstance(updated_entry, dict):
        return {"status": "blocked", "reason": "entry_identity_unverified"}
    problems = sorted(
        {*identity_issues(current_entry), *identity_issues(updated_entry)}
    )
    if problems:
        return {
            "status": "blocked",
            "reason": "entry_identity_invalid",
            "issues": problems,
        }
    if not (
        _ref_matches_identity(current_entry) and _ref_matches_identity(updated_entry)
    ):
        return {"status": "blocked", "reason": "entry_ref_does_not_match_identity"}
    if current_entry.get("identity") != updated_entry.get("identity"):
        target_entry_identity_unchanged = False
    if not isinstance(expected_entry_revision, str) or not expected_entry_revision:
        return {"status": "blocked", "reason": "entry_revision_unavailable"}
    if not target_entry_identity_unchanged:
        return {"status": "replacement_required", "reason": "semantic_identity_changed"}
    if not native_atomic_conditional_write:
        return {"status": "blocked", "reason": "atomic_conditional_write_unavailable"}
    return {
        "status": "conditional_write_required",
        "expected_revision": expected_entry_revision,
    }


def handle_update_conflict(
    *, target_entry_revision_changed: bool, different_entry_only_changed: bool
) -> dict[str, Any]:
    if target_entry_revision_changed:
        return {"status": "reread_and_semantic_reevaluation", "auto_merge": False}
    if different_entry_only_changed:
        return {"status": "target_revision_recheck_required", "auto_merge": False}
    return {"status": "unresolved", "auto_merge": False}


def update_entry(
    root: str | Path,
    updated_entry: dict[str, Any],
    *,
    expected_entry_revision: str,
    conditional_write: Any,
    current_dependencies: dict[str, str] | None,
) -> dict[str, Any]:
    """Update one entry through a storage-native conditional write.

    ``conditional_write(path, content, expected_revision)`` must be the storage
    provider's own atomic compare-and-set and return ``{"status": "written"}``,
    ``{"status": "conflict"}`` or ``{"status": "blocked", "reason": ...}``. This
    helper never performs its own compare-then-write: without a provider the
    update is blocked, and the provider's condition decides. The revision check
    done here is only an early exit. The stored result is read back and its
    revision returned.
    """
    if not callable(conditional_write):
        return {"status": "blocked", "reason": "atomic_conditional_write_unavailable"}
    if not isinstance(updated_entry, dict) or "entry_revision" in updated_entry:
        return {"status": "blocked", "reason": "entry_revision_must_not_be_in_body"}
    entry_ref = updated_entry.get("entry_ref")
    stored = read_entry(root, entry_ref)
    if stored["status"] != "current":
        return {
            "status": "blocked",
            "reason": "stored_entry_unreadable",
            "stored_reason": stored.get("reason"),
        }
    plan = plan_update(
        expected_entry_revision=expected_entry_revision,
        native_atomic_conditional_write=True,
        current_entry=stored["entry"],
        updated_entry=updated_entry,
    )
    if plan["status"] != "conditional_write_required":
        return plan
    if stored["entry_revision"] != expected_entry_revision:
        return {
            **handle_update_conflict(
                target_entry_revision_changed=True,
                different_entry_only_changed=False,
            ),
            "status": "conflict",
            "current_revision": stored["entry_revision"],
        }
    raw = render_entry(updated_entry)
    new_revision = "sha256:" + hashlib.sha256(raw).hexdigest()
    validation = validate_entry(
        updated_entry,
        current_dependencies=current_dependencies,
        entry_revision=new_revision,
    )
    if not validation["valid"]:
        return {
            "status": "blocked",
            "reason": "entry_contract_invalid",
            "issues": validation["issues"],
        }
    if (
        updated_entry.get("state") == "有効"
        and validation["currentness"].get("status") != "current"
    ):
        return {
            "status": "blocked",
            "reason": "entry_dependencies_not_current",
            "currentness": validation["currentness"],
        }
    path = Path(root) / f"{entry_ref}.md"
    outcome = conditional_write(path, raw, expected_entry_revision)
    status = outcome.get("status") if isinstance(outcome, dict) else None
    if status == "conflict":
        return {
            **handle_update_conflict(
                target_entry_revision_changed=True,
                different_entry_only_changed=False,
            ),
            "status": "conflict",
        }
    if status != "written":
        return {
            "status": "blocked",
            "reason": "conditional_write_not_confirmed",
            "provider_reason": outcome.get("reason")
            if isinstance(outcome, dict)
            else None,
        }
    readback = read_entry(root, entry_ref)
    if (
        readback["status"] != "current"
        or readback["entry_revision"] != new_revision
        or readback["entry"] != updated_entry
    ):
        return {
            "status": "blocked",
            "reason": "updated_entry_readback_mismatch",
            "entry_ref": entry_ref,
        }
    return {
        "status": "updated",
        "entry_ref": entry_ref,
        "previous_revision": expected_entry_revision,
        "entry_revision": new_revision,
        "readback_verified": True,
        "historical_revision_available": False,
    }


def plan_replacement(
    *,
    old_entry_ref: str,
    new_entry_ref: str,
    native_atomic_multi_entry_update: bool,
    old_entry: dict[str, Any] | None = None,
    new_entry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not old_entry_ref or not new_entry_ref or old_entry_ref == new_entry_ref:
        return {"status": "blocked", "reason": "replacement_refs_invalid"}
    for ref, entry in ((old_entry_ref, old_entry), (new_entry_ref, new_entry)):
        if not isinstance(entry, dict):
            return {
                "status": "blocked",
                "reason": "entry_identity_unverified",
                "entry_ref": ref,
            }
        problems = identity_issues(entry)
        if not _ref_matches_identity(entry):
            problems.append("entry_ref_does_not_match_identity")
        if problems or entry.get("entry_ref") != ref:
            return {
                "status": "blocked",
                "reason": "entry_identity_invalid",
                "entry_ref": ref,
                "issues": problems or ["entry_ref_differs_from_replacement_ref"],
            }
    if not native_atomic_multi_entry_update:
        return {
            "status": "blocked",
            "reason": "replacement_requires_atomic_old_new_update",
        }
    return {
        "status": "conditional_multi_entry_update_required",
        "old_entry_ref": old_entry_ref,
        "new_entry_ref": new_entry_ref,
    }


def _incomplete(reason: str, **extra: Any) -> dict[str, Any]:
    return {
        "status": "incomplete",
        "entries": [],
        "complete": False,
        "reason": reason,
        **extra,
    }


def _ref_matches_identity(entry: dict[str, Any]) -> bool:
    try:
        return entry.get("entry_ref") == canonical_entry_ref(entry.get("identity"))
    except (TypeError, ValueError):
        return False


def _applicability(
    entry: dict[str, Any],
    *,
    scope_refs: set[str],
    kind: str | None,
    environment: str | None,
    version: str | None,
) -> bool | None:
    """True/False when applicability is certain, None when it cannot be decided.

    Only the structure needed to decide applicability is inspected here. Content,
    provenance and currentness are checked afterwards for applicable entries.
    """
    if identity_issues(entry):
        return None
    if not scope_refs & set(entry["scope_refs"]):
        return False
    if kind is not None and entry.get("kind") != kind:
        return False
    if environment is None and version is None:
        return True
    applicability = entry.get("applicability")
    if not isinstance(applicability, dict):
        return None
    if environment is not None:
        environments = applicability.get("environment")
        if not isinstance(environments, list):
            return None
        if environment not in environments:
            return False
    if version is not None:
        entry_version = applicability.get("version")
        if not isinstance(entry_version, str) or not entry_version:
            return None
        if entry_version not in {version, "*"}:
            return False
    return True


def lookup(
    entries: list[dict[str, Any]],
    *,
    scope_refs: set[str],
    kind: str | None,
    environment: str | None,
    version: str | None,
    current_dependencies: dict[str, str],
    listing_complete: bool,
) -> dict[str, Any]:
    """Return the current entries that apply to the request.

    Each entry is the read_entry() body plus the stored ``entry_revision`` (see
    ``lookup_input``). Entries that certainly do not apply are not validated for
    content or dependencies, so an unrelated entry whose dependency cannot be
    fetched does not stop the search. An entry whose applicability cannot be
    decided (broken identity, unresolved scope, duplicate ref) makes the search
    ``incomplete`` instead of being assumed irrelevant.
    """
    if not listing_complete:
        return _incomplete("knowledge_root_listing_incomplete")
    if not isinstance(entries, list):
        return _incomplete("entry_listing_invalid")
    if any(not isinstance(entry, dict) for entry in entries):
        return _incomplete("entry_parse_failed")
    if not isinstance(scope_refs, set) or any(
        not isinstance(ref, str) for ref in scope_refs
    ):
        return _incomplete("lookup_scope_refs_invalid")
    usable: list[dict[str, Any]] = []
    historical: list[str] = []
    diagnostics: list[str] = []
    issues: list[str] = []
    seen: set[str] = set()
    for entry in sorted(entries, key=lambda item: str(item.get("entry_ref", ""))):
        entry_ref = entry.get("entry_ref")
        if not isinstance(entry_ref, str) or not entry_ref or entry_ref in seen:
            issues.append("entry_ref_missing_or_duplicate")
            continue
        seen.add(entry_ref)
        if not _ref_matches_identity(entry):
            issues.append(f"{entry_ref}:entry_ref_does_not_match_identity")
            continue
        applies = _applicability(
            entry,
            scope_refs=scope_refs,
            kind=kind,
            environment=environment,
            version=version,
        )
        if applies is None:
            problems = identity_issues(entry) or ["applicability_unresolved"]
            issues.extend(f"{entry_ref}:{issue}" for issue in problems)
            continue
        dependencies = entry.get("currentness_dependencies", [])
        currentness = (
            compare_currentness(dependencies, current_dependencies)
            if isinstance(dependencies, list)
            else {"status": "unresolved", "changed_refs": [], "unresolved": []}
        )
        if not applies:
            if currentness.get("status") == "unresolved":
                diagnostics.append(f"{entry_ref}:currentness_unresolved_not_applicable")
            continue
        validation = validate_entry(
            entry,
            current_dependencies=current_dependencies,
            entry_revision=entry.get("entry_revision"),
        )
        if not validation["valid"]:
            issues.extend(f"{entry_ref}:{issue}" for issue in validation["issues"])
        if currentness.get("status") == "unresolved":
            issues.append(f"{entry_ref}:currentness_unresolved")
        if (
            entry.get("state") == "有効"
            and currentness.get("status") == "current"
            and entry.get("entry_revision")
        ):
            usable.append(
                {
                    "entry_ref": entry_ref,
                    "entry_revision": entry.get("entry_revision"),
                    "content": entry.get("content"),
                }
            )
        else:
            historical.append(entry_ref)
    if issues:
        return {
            "status": "incomplete",
            "entries": [],
            "complete": False,
            "unresolved": sorted(set(issues)),
            "out_of_scope_diagnostics": sorted(diagnostics),
        }
    return {
        "status": "complete",
        "entries": usable,
        "historical_excluded_refs": sorted(historical),
        "out_of_scope_diagnostics": sorted(diagnostics),
        "complete": True,
    }


def read_root_entries(
    root: str | Path, *, max_entries: int | None = None
) -> dict[str, Any]:
    """Scan and read every entry of a knowledge root as lookup inputs.

    Every call re-reads the stored bodies and their revisions; nothing from an
    earlier session is reused. A file that cannot be read as a canonical entry is
    reported in ``unresolved`` rather than skipped as irrelevant.
    """
    scan = scan_knowledge_root(root, max_entries=max_entries)
    if not scan["complete"]:
        return {"complete": False, "entries": [], "unresolved": scan["unresolved"]}
    inputs: list[dict[str, Any]] = []
    unresolved: list[str] = []
    for path in scan["entry_paths"]:
        name = Path(path).name
        if not _ENTRY_REF.fullmatch(name[:-3]):
            unresolved.append(f"{name}:entry_filename_not_canonical")
            continue
        read = read_entry(root, name[:-3])
        if read["status"] != "current":
            unresolved.append(f"{name}:{read.get('reason', 'entry_unreadable')}")
            continue
        inputs.append(lookup_input(read))
    return {
        "complete": not unresolved,
        "entries": inputs,
        "unresolved": sorted(unresolved),
    }


def lookup_root(
    root: str | Path,
    *,
    scope_refs: set[str],
    kind: str | None,
    environment: str | None,
    version: str | None,
    current_dependencies: dict[str, str],
    max_entries: int | None = None,
) -> dict[str, Any]:
    """Read a knowledge root and look up the applicable current entries."""
    snapshot = read_root_entries(root, max_entries=max_entries)
    if not snapshot["complete"]:
        return _incomplete(
            "knowledge_root_read_incomplete", unresolved=snapshot["unresolved"]
        )
    return lookup(
        snapshot["entries"],
        scope_refs=scope_refs,
        kind=kind,
        environment=environment,
        version=version,
        current_dependencies=current_dependencies,
        listing_complete=True,
    )


def plan_revalidation(
    entries: list[dict[str, Any]],
    *,
    current_dependencies: dict[str, str],
    scope_refs: set[str] | None = None,
    changed_refs: set[str] | None = None,
) -> dict[str, Any]:
    """Select only the entries whose own dependencies changed or are unresolved.

    ``entries`` are lookup inputs (body plus stored ``entry_revision``). Entries
    outside ``scope_refs`` and entries with unchanged dependencies are left alone;
    a repository HEAD change alone selects nothing. ``changed_refs`` limits the
    selection to entries depending on those refs. Each target carries the stored
    revision read from storage, which is the expected revision of the conditional
    update. An input that cannot be decided (not an object, broken identity,
    unresolved dependencies field, or a target without a stored revision) is
    reported in ``rejected`` and makes the plan ``incomplete``; it is never
    skipped or assumed current.
    """
    for name, value in (("scope_refs", scope_refs), ("changed_refs", changed_refs)):
        if value is not None and (
            not isinstance(value, set) or any(not isinstance(ref, str) for ref in value)
        ):
            return _revalidation_invalid(f"{name}_invalid")
    if not isinstance(entries, list):
        return _revalidation_invalid("entry_listing_invalid")
    if not isinstance(current_dependencies, dict):
        return _revalidation_invalid("current_dependencies_invalid")
    targets: list[dict[str, Any]] = []
    unaffected: list[str] = []
    rejected: list[dict[str, Any]] = []
    for entry in entries:
        if not isinstance(entry, dict):
            rejected.append({"entry_ref": None, "issues": ["entry_must_be_object"]})
            continue
        entry_ref = entry.get("entry_ref")
        problems = identity_issues(entry)
        if not _ref_matches_identity(entry):
            problems.append("entry_ref_does_not_match_identity")
        dependencies = entry.get("currentness_dependencies")
        if not isinstance(dependencies, list):
            problems.append("currentness_dependencies_must_be_list")
        if problems:
            rejected.append({"entry_ref": entry_ref, "issues": problems})
            continue
        if scope_refs is not None and not scope_refs & set(entry["scope_refs"]):
            continue
        dependency_refs = {
            item["ref"]
            for item in dependencies
            if isinstance(item, dict) and isinstance(item.get("ref"), str)
        }
        if changed_refs is not None and not dependency_refs & changed_refs:
            unaffected.append(entry_ref)
            continue
        currentness = compare_currentness(dependencies, current_dependencies)
        if currentness["status"] == "current":
            unaffected.append(entry_ref)
            continue
        revision = entry.get("entry_revision")
        if not isinstance(revision, str) or not revision:
            rejected.append(
                {"entry_ref": entry_ref, "issues": ["entry_revision_unavailable"]}
            )
            continue
        targets.append(
            {
                "entry_ref": entry_ref,
                "expected_entry_revision": revision,
                "reason": "dependency_changed"
                if currentness["status"] == "stale"
                else "dependency_unresolved",
                "changed_refs": currentness["changed_refs"],
                "unresolved": currentness["unresolved"],
            }
        )
    targets.sort(key=lambda item: item["entry_ref"])
    return {
        "status": "incomplete" if rejected else "complete",
        "targets": targets,
        "unaffected_refs": sorted(unaffected),
        "rejected": rejected,
    }


def _revalidation_invalid(reason: str) -> dict[str, Any]:
    return {
        "status": "incomplete",
        "targets": [],
        "unaffected_refs": [],
        "rejected": [{"entry_ref": None, "issues": [reason]}],
    }


def _handoff_state(
    entry: dict[str, Any], current_dependencies: dict[str, str] | None
) -> dict[str, Any]:
    """Map one entry to the shared hand-off state: current / stale / blocked.

    The validation result is returned inline; storing it and obtaining a durable
    result ref is the caller's responsibility (``result_ref`` stays ``None``).
    """
    validation = validate_entry(
        entry,
        current_dependencies=current_dependencies,
        entry_revision=entry.get("entry_revision"),
    )
    runtime = "qa-knowledge/scripts/knowledge_runtime.py:validate_entry"
    result = {
        "runtime": runtime,
        "valid": validation["valid"],
        "issues": validation["issues"],
        "result_ref": None,
    }
    dependencies = entry.get("currentness_dependencies")
    currentness = (
        compare_currentness(dependencies, current_dependencies)
        if isinstance(dependencies, list)
        else {"status": "unresolved", "changed_refs": [], "unresolved": []}
    )
    if not validation["valid"]:
        return {
            "state": "blocked",
            "validation": result,
            "unresolved": sorted(validation["issues"]),
            "resume": {
                "owner_skill": "qa-knowledge",
                "action": "fix_entry_or_return_to_owner",
            },
        }
    if currentness["status"] == "unresolved":
        return {
            "state": "blocked",
            "validation": result,
            "unresolved": sorted(currentness["unresolved"]),
            "resume": {
                "owner_skill": "qa-knowledge",
                "action": "obtain_dependency_revisions",
                "condition": "current revisions of the unresolved dependency refs",
            },
        }
    if entry.get("state") == "置換済み":
        return {
            "state": "stale",
            "validation": result,
            "unresolved": [],
            "resume": {
                "owner_skill": "qa-knowledge",
                "action": "use_replacement",
                "replacement_ref": entry.get("replacement_ref"),
            },
        }
    if currentness["status"] == "stale" or entry.get("state") != "有効":
        return {
            "state": "stale",
            "validation": result,
            "unresolved": [],
            "resume": {
                "owner_skill": "qa-knowledge",
                "action": "revalidation",
                "expected_entry_revision": entry.get("entry_revision"),
                "changed_refs": currentness["changed_refs"],
            },
        }
    return {
        "state": "current",
        "validation": result,
        "unresolved": [],
        "resume": None,
    }


def _as_list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def improvement_reference(
    entry: dict[str, Any], *, current_dependencies: dict[str, str] | None = None
) -> dict[str, Any]:
    """Build a reference-only improvement candidate hand-off for a lookup input.

    The reference names the entry, its stored revision / content hash, scope,
    source refs, validation result, state and resume point so the planning /
    evaluation owners can decide adoption. It does not copy the entry content and
    does not record any adoption or approval: the knowledge entry is not a second
    source of truth for specs, results or the improvement decision. Without a
    dependency snapshot the state is ``blocked``, never ``current``.
    """
    problems = identity_issues(entry) if isinstance(entry, dict) else ["not_object"]
    if problems:
        return {
            "status": "blocked",
            "reason": "entry_identity_invalid",
            "issues": problems,
        }
    if not _ref_matches_identity(entry):
        return {"status": "blocked", "reason": "entry_ref_does_not_match_identity"}
    if not entry.get("entry_revision"):
        return {"status": "blocked", "reason": "entry_revision_unavailable"}
    state = _handoff_state(entry, current_dependencies)
    unverified = []
    if entry.get("state") != "有効":
        unverified.append("entry_state_not_valid")
    if not entry.get("provenance"):
        unverified.append("provenance_missing")
    if current_dependencies is None:
        unverified.append("current_dependencies_not_checked")
    return {
        "status": "ready",
        "reference": {
            "kind": "knowledge_improvement_candidate_reference",
            "owner_skill": "qa-knowledge",
            "artifact_ref": entry["entry_ref"],
            "entry_ref": entry["entry_ref"],
            "entry_revision": entry["entry_revision"],
            "content_hash": entry["entry_revision"],
            "revision_kind": "local_exact_content_token_not_a_cas_condition",
            "entry_kind": entry["kind"],
            "scope_refs": list(entry["scope_refs"]),
            "applicability": entry.get("applicability"),
            "source_refs": _as_list(entry.get("provenance")),
            "currentness_dependencies": _as_list(entry.get("currentness_dependencies")),
            "state": state["state"],
            "validation": state["validation"],
            "unresolved": state["unresolved"],
            "resume": state["resume"],
            "required_approval": {
                "required": True,
                "approval_ref": None,
                "decided_by": "improvement_owner",
            },
            "unverified": unverified,
            "adoption_decision": "owner_pending",
            "authority": "reference_only",
        },
    }


def plan_approved_improvement_update(
    request: dict[str, Any],
    *,
    current_entry: dict[str, Any],
    updated_entry: dict[str, Any],
    native_atomic_conditional_write: bool,
) -> dict[str, Any]:
    """Accept a reusable-knowledge update only when an owner approved the improvement.

    Registering knowledge never completes the improvement: plan revision,
    implementation and effect measurement stay with their owners.
    """
    if not isinstance(request, dict) or (
        not request.get("improvement_ref") or not request.get("approval_ref")
    ):
        return {"status": "blocked", "reason": "approved_improvement_required"}
    sources = request.get("source_refs")
    if not isinstance(sources, list) or not sources:
        return {"status": "blocked", "reason": "improvement_source_refs_required"}
    if any(
        not isinstance(item, dict) or not item.get("ref") or not item.get("revision")
        for item in sources
    ):
        return {"status": "blocked", "reason": "improvement_source_requires_revision"}
    plan = plan_update(
        expected_entry_revision=request.get("expected_entry_revision"),
        native_atomic_conditional_write=native_atomic_conditional_write,
        current_entry=current_entry,
        updated_entry=updated_entry,
    )
    return {
        **plan,
        "improvement_completed": False,
        "improvement_ref": request["improvement_ref"],
        "approval_ref": request["approval_ref"],
        "source_refs": list(sources),
    }
