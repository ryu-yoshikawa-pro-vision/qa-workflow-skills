"""Validate source inventory, feature IDs, change classification and history.

The caller owns semantic decisions. This validator never fetches sources or writes
artifacts, and never claims that all product functions have been discovered.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

PROJECT_CONTEXT_SCRIPT = (
    Path(__file__).resolve().parents[2] / "project-context" / "scripts"
)
sys.path.insert(0, str(PROJECT_CONTEXT_SCRIPT))
from artifact_store import LocalArtifactStore, StoreError  # noqa: E402
from git_artifact_store import GitArtifactStore  # noqa: E402

MAX_INPUT = 16 * 1024 * 1024
ID = re.compile(r"^(SRC|CAND|FEAT|DIF)-[0-9]{3,}$")
EVENTS = {
    "initial",
    "analysis_update",
    "pr_update",
    "rebase",
    "merge",
    "release",
    "external_revision",
}
SOURCE_STATES = {"complete", "partial", "denied", "unavailable"}
FEATURE_KINDS = {"ui", "api", "batch", "integration", "authorization", "data", "other"}
FEATURE_STATES = {"planned", "implemented", "retired", "unknown"}
CHANGE_STATES = {"impact", "no_impact", "out_of_scope", "unclassified", "unresolved"}
HISTORY_KINDS = {"added", "changed", "renamed", "split", "merged", "retired"}
COMMIT = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")


class ContractError(ValueError):
    pass


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ContractError("duplicate_json_key")
        result[key] = value
    return result


def _text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip() or "\x00" in value:
        raise ContractError(f"{name}_invalid")
    return value


def _list(value: Any, name: str) -> list[Any]:
    if not isinstance(value, list):
        raise ContractError(f"{name}_invalid")
    return value


def _refs(value: Any, name: str, required: bool = False) -> list[str]:
    values = _list(value, name)
    if any(not isinstance(v, str) or not v.strip() for v in values):
        raise ContractError(f"{name}_invalid_ref")
    if len(values) != len(set(values)) or (required and not values):
        raise ContractError(f"{name}_duplicate_or_empty")
    return values


def _rows(value: Any, name: str, prefix: str) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for row in _list(value, name):
        if not isinstance(row, dict):
            raise ContractError(f"{name}_invalid_row")
        rid = _text(row.get("id"), f"{name}_id")
        if not ID.fullmatch(rid) or not rid.startswith(prefix + "-"):
            raise ContractError(f"{name}_invalid_id")
        if rid in rows:
            raise ContractError(f"{name}_duplicate_id")
        rows[rid] = row
    return rows


def _source_inventory(snapshot: dict[str, Any]) -> tuple[dict, list[str]]:
    sources = _rows(snapshot.get("sources"), "sources", "SRC")
    issues: list[str] = []
    for sid, row in sources.items():
        _text(row.get("kind"), f"{sid}_kind")
        _text(row.get("ref"), f"{sid}_ref")
        _text(row.get("scope"), f"{sid}_scope")
        _refs(row.get("unretrieved"), f"{sid}_unretrieved")
        if row.get("status") not in SOURCE_STATES:
            raise ContractError(f"{sid}_status_invalid")
        if row["status"] == "complete":
            _text(row.get("revision"), f"{sid}_revision")
            _text(row.get("evidence_ref"), f"{sid}_evidence")
            if row.get("enumeration_complete") is not True or row["unretrieved"]:
                raise ContractError(f"{sid}_false_completion")
        else:
            _text(row.get("reason"), f"{sid}_reason")
            issues.append(f"source_incomplete:{sid}")
    expected = _refs(snapshot.get("expected_source_ids"), "expected_source_ids")
    if not expected:
        issues.append("source_boundary_unconfirmed")
    for sid in expected:
        if not ID.fullmatch(sid) or not sid.startswith("SRC-"):
            raise ContractError("expected_source_id_invalid")
        if sid not in sources:
            issues.append(f"source_missing:{sid}")
    return sources, issues


def _features(snapshot: dict[str, Any], sources: dict) -> tuple[dict, list[str]]:
    features = _rows(snapshot.get("features"), "features", "FEAT")
    issues: list[str] = []
    identities: set[str] = set()
    for fid, row in features.items():
        identity = _text(row.get("identity"), f"{fid}_identity")
        if identity in identities:
            raise ContractError("duplicate_semantic_identity")
        identities.add(identity)
        _text(row.get("name"), f"{fid}_name")
        if (
            row.get("kind") not in FEATURE_KINDS
            or row.get("status") not in FEATURE_STATES
        ):
            raise ContractError(f"{fid}_kind_or_status_invalid")
        parent = row.get("parent_id")
        if parent is not None and parent not in features:
            raise ContractError(f"{fid}_missing_parent")
        source_ids = _refs(row.get("source_ids"), f"{fid}_source_ids")
        if any(sid not in sources for sid in source_ids):
            raise ContractError(f"{fid}_unknown_source")
        for field in ("implementation_refs", "spec_refs", "qa_refs"):
            _refs(row.get(field), f"{fid}_{field}")
        if row["status"] != "retired" and not source_ids:
            issues.append(f"feature_unverified:{fid}")
    visited: set[str] = set()
    visiting: set[str] = set()

    def check(fid: str) -> None:
        if fid in visiting:
            raise ContractError("feature_parent_cycle")
        if fid in visited:
            return
        visiting.add(fid)
        parent = features[fid].get("parent_id")
        if parent is not None:
            check(parent)
        visiting.remove(fid)
        visited.add(fid)

    for fid in features:
        check(fid)
    return features, issues


def _candidates(
    snapshot: dict[str, Any], sources: dict, features: dict
) -> tuple[dict, list[str]]:
    candidates = _rows(snapshot.get("candidates"), "candidates", "CAND")
    issues: list[str] = []
    for cid, row in candidates.items():
        ids = _refs(row.get("source_ids"), f"{cid}_sources", required=True)
        if any(sid not in sources for sid in ids):
            raise ContractError(f"{cid}_unknown_source")
        _text(row.get("evidence_ref"), f"{cid}_evidence")
        status = row.get("status")
        if status not in {"mapped", "unresolved", "excluded"}:
            raise ContractError(f"{cid}_status_invalid")
        if status == "mapped" and row.get("feature_id") not in features:
            raise ContractError(f"{cid}_missing_feature")
        if status != "mapped" and row.get("feature_id") is not None:
            raise ContractError(f"{cid}_unexpected_feature")
        if status == "excluded":
            _text(row.get("reason"), f"{cid}_reason")
            _text(row.get("approval_ref"), f"{cid}_approval_ref")
        if status == "unresolved":
            issues.append(f"candidate_unresolved:{cid}")
    return candidates, issues


def _changes(
    snapshot: dict[str, Any], sources: dict, features: dict
) -> tuple[dict, list[str]]:
    changes = _rows(snapshot.get("changes"), "changes", "DIF")
    issues: list[str] = []
    superseded = {
        row.get("supersedes_id")
        for row in changes.values()
        if row.get("supersedes_id") is not None
    }
    for did, row in changes.items():
        if row.get("source_id") not in sources:
            raise ContractError(f"{did}_unknown_source")
        for field in ("before_revision", "after_revision", "locator", "evidence_ref"):
            _text(row.get(field), f"{did}_{field}")
        cls = row.get("classification")
        if cls not in CHANGE_STATES:
            raise ContractError(f"{did}_classification_invalid")
        ids = _refs(row.get("feature_ids"), f"{did}_feature_ids")
        if any(fid not in features for fid in ids):
            raise ContractError(f"{did}_unknown_feature")
        if cls in {"impact", "no_impact", "out_of_scope"}:
            _text(row.get("reason"), f"{did}_reason")
            if cls == "impact" and not ids:
                raise ContractError(f"{did}_impact_feature_missing")
            if cls in {"out_of_scope", "no_impact"}:
                _text(row.get("approval_ref"), f"{did}_approval_ref")
        elif did not in superseded:
            issues.append(f"change_unclassified:{did}")
    seen: dict[tuple[str, str, str, str], str] = {}
    for did, row in changes.items():
        if did in superseded:
            continue
        identity = (
            row["source_id"],
            row["before_revision"],
            row["after_revision"],
            row["locator"],
        )
        if identity in seen:
            raise ContractError(f"duplicate_active_change:{seen[identity]}:{did}")
        seen[identity] = did
    return changes, issues


def _primary_code_source_id(snapshot: dict[str, Any]) -> str | None:
    """Identify the event's owning source, not just a shared Git SHA."""
    if snapshot["event"] not in {"pr_update", "rebase", "merge", "release"}:
        return None
    matching = [
        row
        for row in snapshot["sources"]
        if row["kind"] == "code" and row.get("revision") == snapshot["source_revision"]
    ]
    chosen = snapshot["event_basis"].get("primary_source_id")
    if chosen is not None:
        if not any(row.get("id") == chosen for row in matching):
            raise ContractError("event_primary_source_invalid")
        return chosen
    if len(matching) != 1:
        raise ContractError("event_primary_source_ambiguous")
    return matching[0]["id"]


def _current_changes(
    snapshot: dict[str, Any],
    previous: dict | None,
    changes: dict[str, dict[str, Any]],
    sources: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Scope current QA impact to this event, preserving append-only history."""
    superseded = {
        row["supersedes_id"]
        for row in changes.values()
        if row.get("supersedes_id") is not None
    }
    previous_ids = (
        set(_rows(previous.get("changes"), "previous_changes", "DIF"))
        if previous is not None
        else set()
    )
    current: dict[str, dict[str, Any]] = {}
    for did, row in changes.items():
        if did in superseded:
            continue
        # A correction of a saved DIF is not a new Git change. Only a
        # same-revision analysis update can include it in current QA impact.
        if row.get("supersedes_id") is not None and (
            snapshot["event"] != "analysis_update"
            or row["after_revision"] != sources[row["source_id"]]["revision"]
        ):
            continue
        if previous is None or snapshot["event"] == "initial":
            current[did] = row
        elif did not in previous_ids:
            current[did] = row
        elif snapshot["event"] == "analysis_update" and row[
            "after_revision"
        ] == sources[row["source_id"]].get("revision"):
            current[did] = row
    return current


def _change_revisions(
    snapshot: dict[str, Any],
    previous: dict | None,
    sources: dict,
    changes: dict,
) -> list[str]:
    """Check only newly observed differences against the current source revision.

    Historical differences are append-only and retain their original revisions.
    """
    prior = (
        _rows(previous.get("changes"), "previous_changes", "DIF")
        if previous is not None
        else {}
    )
    issues: list[str] = []
    basis = snapshot.get("event_basis") or {}
    primary = _primary_code_source_id(snapshot)
    for did, row in changes.items():
        if did in prior or row.get("supersedes_id") is not None:
            continue
        source = sources[row["source_id"]]
        if source["status"] != "complete":
            issues.append(f"change_source_incomplete:{did}")
            continue
        if row["after_revision"] != source["revision"]:
            raise ContractError(f"change_source_revision_mismatch:{did}")
        if snapshot["event"] in {"pr_update", "rebase"} and source["kind"] == "code":
            if row["source_id"] == primary:
                permitted = {basis["base_sha"], basis["previous_head_sha"]}
                if row["before_revision"] not in permitted:
                    raise ContractError(f"change_before_revision_mismatch:{did}")
            elif not COMMIT.fullmatch(row["before_revision"]):
                # For a second repository the actual base/previous HEAD are
                # validated against its own Git diff at persistence time.
                raise ContractError(f"change_before_revision_not_sha:{did}")
        elif (
            snapshot["event"] == "external_revision"
            and source["ref"] == basis["document_ref"]
        ):
            if row["before_revision"] != basis["before_revision"]:
                raise ContractError(f"document_change_before_revision_mismatch:{did}")
    return issues


def _history(
    snapshot: dict[str, Any],
    previous: dict | None,
    features: dict,
    *,
    idempotent: bool = False,
) -> None:
    events = _list(snapshot.get("history"), "history")
    event_ids: set[str] = set()
    for event in events:
        if not isinstance(event, dict):
            raise ContractError("history_event_invalid")
        eid = _text(event.get("event_id"), "history_event_id")
        if eid in event_ids:
            raise ContractError("history_event_duplicated")
        event_ids.add(eid)
        if event.get("kind") not in HISTORY_KINDS:
            raise ContractError("history_kind_invalid")
        _text(event.get("revision"), "history_revision")
        _text(event.get("evidence_ref"), "history_evidence")
        from_ids = _refs(event.get("from_ids"), "history_from_ids")
        to_ids = _refs(event.get("to_ids"), "history_to_ids")
        if any(fid not in features for fid in from_ids + to_ids):
            raise ContractError("history_unknown_feature")
        if event["kind"] == "split" and (not from_ids or len(to_ids) < 2):
            raise ContractError("split_requires_multiple_descendants")
        if event["kind"] == "merged" and (len(from_ids) < 2 or not to_ids):
            raise ContractError("merge_requires_multiple_ancestors")
    if previous is None:
        if any(row.get("supersedes_id") for row in snapshot["changes"]):
            raise ContractError("change_supersession_without_predecessor")
        if snapshot.get("previous_artifact_revision") is not None:
            raise ContractError("unexpected_previous_artifact_revision")
        new_features = set(features)
    else:
        new_features = set(features) - set(
            _rows(previous.get("features"), "previous_features", "FEAT")
        )
    for fid in new_features:
        if not any(
            event["kind"] in {"added", "split", "merged"} and fid in event["to_ids"]
            for event in events
        ):
            raise ContractError(f"feature_creation_evidence_missing:{fid}")
    if previous is None:
        return
    if snapshot.get("project_ref") != previous.get("project_ref"):
        raise ContractError("project_changed")
    if snapshot.get("artifact_ref") != previous.get("artifact_ref"):
        raise ContractError("artifact_changed")
    if not idempotent and snapshot.get("previous_artifact_revision") != previous.get(
        "artifact_revision"
    ):
        raise ContractError("previous_artifact_revision_conflict")
    if (
        not idempotent
        and snapshot["artifact_revision"] == previous["artifact_revision"]
    ):
        raise ContractError("artifact_revision_reused")
    old_sources = _rows(previous.get("sources"), "previous_sources", "SRC")
    new_sources = _rows(snapshot.get("sources"), "sources", "SRC")
    for sid in old_sources.keys() & new_sources.keys():
        if any(
            old_sources[sid].get(field) != new_sources[sid].get(field)
            for field in ("kind", "ref", "scope")
        ):
            raise ContractError(f"source_identity_reused:{sid}")
    old_candidates = _rows(previous.get("candidates"), "previous_candidates", "CAND")
    new_candidates = _rows(snapshot.get("candidates"), "candidates", "CAND")
    for cid in old_candidates.keys() & new_candidates.keys():
        if any(
            old_candidates[cid].get(field) != new_candidates[cid].get(field)
            for field in ("source_ids", "evidence_ref")
        ):
            raise ContractError(f"candidate_identity_reused:{cid}")
    old_changes = _rows(previous.get("changes"), "previous_changes", "DIF")
    new_changes = _rows(snapshot.get("changes"), "changes", "DIF")
    if set(old_changes) - set(new_changes):
        raise ContractError("historical_changes_removed")
    for did in old_changes.keys() & new_changes.keys():
        if old_changes[did] != new_changes[did]:
            raise ContractError(f"change_history_rewritten:{did}")
    replaced: set[str] = {
        row["supersedes_id"]
        for row in old_changes.values()
        if row.get("supersedes_id") is not None
    }
    for did in new_changes.keys() - old_changes.keys():
        row = new_changes[did]
        parent = row.get("supersedes_id")
        if parent is None:
            continue
        if parent not in old_changes or parent in replaced:
            raise ContractError(f"change_supersession_invalid:{did}")
        prior = old_changes[parent]
        fields = ("source_id", "before_revision", "after_revision", "locator")
        if any(row.get(key) != prior.get(key) for key in fields):
            raise ContractError(f"change_supersession_target_mismatch:{did}")
        if row.get("classification") == prior.get("classification") or row.get(
            "classification"
        ) not in {"impact", "no_impact", "out_of_scope"}:
            raise ContractError(f"change_supersession_classification_invalid:{did}")
        if row.get("evidence_ref") == prior.get("evidence_ref"):
            raise ContractError(f"change_supersession_evidence_not_new:{did}")
        _text(row.get("approval_ref"), f"{did}_approval_ref")
        _text(row.get("approval_revision"), f"{did}_approval_revision")
        _text(row.get("reason"), f"{did}_change_reason")
        replaced.add(parent)
    old_features = _rows(previous.get("features"), "previous_features", "FEAT")
    old_history = _list(previous.get("history"), "previous_history")
    if events[: len(old_history)] != old_history:
        raise ContractError("history_rewritten")
    new_events = events[len(old_history) :]
    for fid, old in old_features.items():
        if fid not in features:
            raise ContractError(f"historical_feature_removed:{fid}")
        if old.get("identity") != features[fid]["identity"]:
            raise ContractError(f"historical_identity_reused:{fid}")
        changed_fields = {
            key
            for key in (
                "name",
                "kind",
                "status",
                "parent_id",
                "source_ids",
                "implementation_refs",
                "spec_refs",
                "qa_refs",
            )
            if old.get(key) != features[fid].get(key)
        }
        if changed_fields and not (
            changed_fields == {"status"} and features[fid]["status"] == "retired"
        ):
            acceptable_kinds = (
                {"renamed", "changed"} if changed_fields == {"name"} else {"changed"}
            )
            if not any(
                event["kind"] in acceptable_kinds
                and fid in event["from_ids"]
                and fid in event["to_ids"]
                and event["revision"] == snapshot["source_revision"]
                for event in new_events
            ):
                raise ContractError(f"feature_change_history_missing:{fid}")
        if old.get("status") == "retired" and features[fid]["status"] != "retired":
            raise ContractError(f"retired_identity_reactivated:{fid}")
        if old.get("status") != "retired" and features[fid]["status"] == "retired":
            if not any(
                e["kind"] in {"retired", "split", "merged"} and fid in e["from_ids"]
                for e in events[len(old_history) :]
            ):
                raise ContractError(f"retirement_evidence_missing:{fid}")


def _event_basis(snapshot: dict[str, Any], previous: dict | None) -> None:
    """Require actual event-bound revisions before calling a snapshot current."""
    event = snapshot["event"]
    basis = snapshot.get("event_basis")
    if event == "initial":
        if previous is not None and snapshot != previous:
            raise ContractError("initial_event_with_previous_snapshot")
        if basis not in (None, {}):
            raise ContractError("initial_event_basis_unexpected")
        return
    if not isinstance(basis, dict):
        raise ContractError("event_basis_required")
    if not isinstance(snapshot.get("sources"), list) or any(
        not isinstance(row, dict) for row in snapshot["sources"]
    ):
        raise ContractError("event_sources_invalid")
    if previous is not None and (
        not isinstance(previous.get("sources"), list)
        or any(not isinstance(row, dict) for row in previous["sources"])
    ):
        raise ContractError("event_previous_sources_invalid")
    keys: dict[str, set[str]] = {
        "analysis_update": {"source_revision", "evidence_ref"},
        "pr_update": {"base_sha", "head_sha", "previous_head_sha"},
        "rebase": {"base_sha", "head_sha", "previous_head_sha", "previous_base_sha"},
        "merge": {"merge_commit_sha", "target_ref", "previous_head_sha"},
        "release": {"commit_sha", "build_ref", "target_ref"},
        "external_revision": {
            "document_ref",
            "before_revision",
            "after_revision",
            "evidence_ref",
        },
    }
    allowed = keys[event].copy()
    if event in {"pr_update", "rebase", "merge", "release"}:
        allowed.add("primary_source_id")
    if not keys[event] <= set(basis) or not set(basis) <= allowed:
        raise ContractError("event_basis_schema_invalid")
    for name, value in basis.items():
        _text(value, f"event_basis_{name}")
        if name.endswith("_sha") and not COMMIT.fullmatch(value):
            raise ContractError(f"event_basis_{name}_not_full_sha")
    if event == "analysis_update":
        if previous is None:
            raise ContractError("analysis_update_requires_previous_snapshot")
        if (
            basis["source_revision"] != snapshot["source_revision"]
            or previous.get("source_revision") != snapshot["source_revision"]
        ):
            raise ContractError("analysis_update_source_revision_changed")
        return
    if event in {"pr_update", "rebase", "merge", "release"}:
        if previous is None:
            raise ContractError("event_previous_snapshot_required")
        head = basis.get(
            "head_sha", basis.get("merge_commit_sha", basis.get("commit_sha"))
        )
        if snapshot["source_revision"] != head:
            raise ContractError("event_source_revision_mismatch")
        if event in {"pr_update", "rebase", "merge"}:
            if previous.get("source_revision") != basis["previous_head_sha"]:
                raise ContractError("event_previous_head_mismatch")
        code_sources = [row for row in snapshot["sources"] if row.get("kind") == "code"]
        if not code_sources or not any(
            row.get("revision") == head for row in code_sources
        ):
            raise ContractError("event_code_source_revision_mismatch")
        _primary_code_source_id(snapshot)
        if event == "rebase" and basis["base_sha"] == basis["previous_base_sha"]:
            raise ContractError("rebase_base_unchanged")
    else:
        if basis["before_revision"] == basis["after_revision"]:
            raise ContractError("document_revision_unchanged")
        target = [
            row
            for row in snapshot["sources"]
            if row.get("ref") == basis["document_ref"]
        ]
        if len(target) != 1 or target[0].get("revision") != basis["after_revision"]:
            raise ContractError("document_current_revision_mismatch")
        if previous is None:
            raise ContractError("document_previous_snapshot_required")
        old = [
            row
            for row in previous.get("sources", [])
            if row.get("ref") == basis["document_ref"]
        ]
        if len(old) != 1 or old[0].get("revision") != basis["before_revision"]:
            raise ContractError("document_previous_revision_mismatch")


def analyze(request: Any) -> dict[str, Any]:
    if not isinstance(request, dict) or set(request) != {
        "snapshot",
        "previous_snapshot",
        "observed_head_revision",
    }:
        raise ContractError("request_schema_mismatch")
    snapshot = request["snapshot"]
    previous = request["previous_snapshot"]
    if not isinstance(snapshot, dict) or (
        previous is not None and not isinstance(previous, dict)
    ):
        raise ContractError("snapshot_invalid")
    if snapshot.get("schema_version") != "feature-inventory-v1":
        raise ContractError("schema_version_invalid")
    for field in (
        "project_ref",
        "artifact_ref",
        "artifact_revision",
        "source_revision",
        "operation_id",
    ):
        _text(snapshot.get(field), field)
    if snapshot.get("event") not in EVENTS:
        raise ContractError("event_invalid")
    _event_basis(snapshot, previous)
    if (
        _text(request["observed_head_revision"], "observed_head_revision")
        != snapshot["source_revision"]
    ):
        return {"status": "stale", "reasons": ["source_head_changed"], "metrics": None}
    idempotent = previous is not None and snapshot["operation_id"] == previous.get(
        "operation_id"
    )
    if idempotent and snapshot != previous:
        raise ContractError("operation_id_reused")
    sources, issues = _source_inventory(snapshot)
    features, more = _features(snapshot, sources)
    issues.extend(more)
    candidates, more = _candidates(snapshot, sources, features)
    issues.extend(more)
    changes, more = _changes(snapshot, sources, features)
    issues.extend(more)
    issues.extend(_change_revisions(snapshot, previous, sources, changes))
    _history(snapshot, previous, features, idempotent=idempotent)
    unknown = _refs(snapshot.get("unknown_areas"), "unknown_areas")
    if unknown:
        issues.append("unknown_areas_present")
    current_changes = _current_changes(snapshot, previous, changes, sources)
    classified = sorted(
        did
        for did, row in current_changes.items()
        if row["classification"] in {"impact", "no_impact", "out_of_scope"}
    )
    mapped = sorted(cid for cid, row in candidates.items() if row["status"] == "mapped")
    if not current_changes:
        issues.append("change_denominator_zero")
    if not candidates:
        issues.append("candidate_denominator_zero")
    if idempotent:
        return {
            "status": "idempotent",
            "reasons": sorted(set(issues)),
            "metrics": None,
        }
    snapshot_sha256 = hashlib.sha256(
        json.dumps(
            snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()
    return {
        "status": "complete" if not issues else "incomplete",
        "reasons": sorted(set(issues)),
        "metrics": {
            "change_classification": {
                "numerator_ids": classified,
                "denominator_ids": sorted(current_changes),
                "rate": (
                    len(classified) / len(current_changes) if current_changes else None
                ),
            },
            "observed_candidate_mapping": {
                "numerator_ids": mapped,
                "denominator_ids": sorted(candidates),
                "rate": len(mapped) / len(candidates) if candidates else None,
            },
            "source_boundary_complete": not unknown
            and not any(v.startswith("source_") for v in issues),
            "unknown_areas": unknown,
            "excluded_candidate_ids": sorted(
                cid for cid, row in candidates.items() if row["status"] == "excluded"
            ),
            "all_product_features_discovered": None,
        },
        "handoff": {
            "snapshot_sha256": snapshot_sha256,
            "source_inventory": [
                {
                    "id": sid,
                    "ref": row["ref"],
                    "status": row["status"],
                    "revision": row.get("revision"),
                    "unretrieved": row["unretrieved"],
                }
                for sid, row in sorted(sources.items())
            ],
            "artifact_ref": snapshot["artifact_ref"],
            "artifact_revision": snapshot["artifact_revision"],
            "source_revision": snapshot["source_revision"],
            "feature_ids": sorted(features),
            "feature_refs": [
                {
                    "id": fid,
                    "kind": row["kind"],
                    "status": row["status"],
                    "parent_id": row["parent_id"],
                    "source_ids": row["source_ids"],
                    "implementation_refs": row["implementation_refs"],
                    "spec_refs": row["spec_refs"],
                    "qa_refs": row["qa_refs"],
                }
                for fid, row in sorted(features.items())
            ],
            "impacted_feature_ids": sorted(
                {
                    fid
                    for row in current_changes.values()
                    if row["classification"] == "impact"
                    for fid in row["feature_ids"]
                }
            ),
            "approval_required_change_ids": sorted(
                did
                for did, row in current_changes.items()
                if row["classification"] in {"no_impact", "out_of_scope"}
            ),
            "unknown_areas": unknown,
            "unclassified_change_ids": sorted(set(current_changes) - set(classified)),
            "expected_source_ids": snapshot["expected_source_ids"],
        },
    }


def _verify_git_evidence(
    request: dict[str, Any],
    report: dict[str, Any],
    inputs: list[dict[str, Any]] | None,
) -> None:
    """Reread the authorized Git tree before accepting a code-backed write.

    Paths in these requests must be chosen by the trusted caller, not the
    feature inventory or an untrusted PR description.
    """
    snapshot = request["snapshot"]
    code_sources = {
        row["id"]: row for row in snapshot["sources"] if row.get("kind") == "code"
    }
    if not code_sources:
        if inputs is not None:
            raise ContractError("git_evidence_without_code_source")
        return
    if not isinstance(inputs, list) or len(inputs) != len(code_sources):
        raise ContractError("git_coverage_required")
    event = snapshot["event"]
    primary_id = _primary_code_source_id(snapshot)
    if event != "external_revision" and not any(
        row["revision"] == snapshot["source_revision"] for row in code_sources.values()
    ):
        raise ContractError("event_primary_code_source_missing")
    if event in {"pr_update", "rebase"}:
        event_basis = snapshot["event_basis"]
        if not any(
            entry.get("source_id") == primary_id
            and entry.get("head_sha") == snapshot["source_revision"]
            and entry.get("base_sha") == event_basis["base_sha"]
            and entry.get("previous_head_base_sha") == event_basis["previous_head_sha"]
            for entry in inputs
            if isinstance(entry, dict)
        ):
            raise ContractError("event_primary_git_evidence_missing")
    from git_source_inventory import handle as read_git  # noqa: PLC0415
    from reconcile_git_coverage import handle as reconcile  # noqa: PLC0415

    verified: set[str] = set()
    for entry in inputs:
        keys = {
            "source_id",
            "repository_root",
            "authorized_root",
            "base_sha",
            "head_sha",
        }
        optional = {"previous_head_base_sha"}
        if (
            not isinstance(entry, dict)
            or not keys <= set(entry)
            or not set(entry) <= keys | optional
        ):
            raise ContractError("git_evidence_schema_invalid")
        sid = entry["source_id"]
        if sid not in code_sources or sid in verified:
            raise ContractError("git_source_evidence_duplicate_or_unknown")
        verified.add(sid)
        if sid not in snapshot["expected_source_ids"]:
            raise ContractError("git_source_not_in_expected_inventory")
        if (
            code_sources[sid]["status"] != "complete"
            or entry["head_sha"] != code_sources[sid]["revision"]
        ):
            raise ContractError("git_evidence_source_revision_mismatch")
        tree_request = {key: entry[key] for key in keys if key != "source_id"}
        tree = read_git(tree_request)
        if tree["status"] != "complete":
            raise ContractError("git_source_listing_incomplete")
        if entry["base_sha"] is None:
            if any(row["source_id"] == sid for row in snapshot["changes"]):
                raise ContractError("git_change_diff_not_enumerated")
            if snapshot["event"] in {"pr_update", "rebase", "merge", "release"}:
                raise ContractError("event_git_base_required")
            continue
        coverage_request: dict[str, Any] = {
            "git_inventory": tree,
            "registry_request": request,
            "source_id": sid,
        }
        if snapshot["event"] in {"pr_update", "rebase"}:
            primary = sid == primary_id
            if primary:
                previous_head = snapshot["event_basis"]["previous_head_sha"]
            else:
                prior_source = next(
                    (
                        row
                        for row in (request.get("previous_snapshot") or {}).get(
                            "sources", []
                        )
                        if row.get("id") == sid
                    ),
                    None,
                )
                if prior_source is None:
                    raise ContractError("secondary_git_source_previous_missing")
                previous_head = prior_source["revision"]
                coverage_request["source_event_basis"] = {
                    "base_sha": entry["base_sha"],
                    "head_sha": entry["head_sha"],
                    "previous_head_sha": previous_head,
                }
            if entry.get("previous_head_base_sha") != previous_head:
                raise ContractError("previous_head_git_base_required")
            previous_request = dict(tree_request)
            previous_request["base_sha"] = previous_head
            previous_diff = read_git(previous_request)
            if previous_diff["status"] != "complete":
                raise ContractError("previous_head_git_listing_incomplete")
            coverage_request["previous_head_git_inventory"] = previous_diff
        elif "previous_head_base_sha" in entry:
            raise ContractError("previous_head_git_base_unexpected")
        coverage = reconcile(coverage_request)
        extra = set(coverage.get("reasons", [])) - set(report.get("reasons", []))
        if coverage["coverage"] is None or extra:
            raise ContractError("git_coverage_not_verified:" + ",".join(sorted(extra)))


def _authorize_reclassifications(
    store: LocalArtifactStore | GitArtifactStore,
    request: dict[str, Any],
    expected_revision: str | None,
) -> None:
    """Check each new classification override with the trusted approval owner."""
    prior = request.get("previous_snapshot")
    if prior is None:
        if any(row.get("supersedes_id") for row in request["snapshot"]["changes"]):
            raise ContractError("change_supersession_without_predecessor")
        return
    old = _rows(prior.get("changes"), "previous_changes", "DIF")
    snapshot = request["snapshot"]
    for row in snapshot["changes"]:
        if row["id"] in old or not row.get("supersedes_id"):
            continue
        replaced = old[row["supersedes_id"]]
        decision = {
            "operation": "reclassify",
            "kind": "feature-inventory",
            "project_ref": snapshot["project_ref"],
            "artifact_ref": snapshot["artifact_ref"],
            "expected_revision": expected_revision,
            "operation_id": snapshot["operation_id"],
            "change_id": row["id"],
            "supersedes_id": row["supersedes_id"],
            "old_classification": replaced["classification"],
            "classification": row["classification"],
            "source_id": row["source_id"],
            "source_ref": next(
                source["ref"]
                for source in snapshot["sources"]
                if source["id"] == row["source_id"]
            ),
            "source_scope": next(
                source["scope"]
                for source in snapshot["sources"]
                if source["id"] == row["source_id"]
            ),
            "source_revision": row["after_revision"],
            "before_revision": row["before_revision"],
            "locator": row["locator"],
            "old_feature_ids": list(replaced["feature_ids"]),
            "feature_ids": list(row["feature_ids"]),
            "old_evidence_ref": replaced["evidence_ref"],
            "evidence_ref": row["evidence_ref"],
            "approval_ref": row["approval_ref"],
            "approval_revision": row["approval_revision"],
            "reason": row["reason"],
        }
        try:
            verified = store.authorize(decision)
        except Exception as exc:
            raise ContractError("change_approval_provider_unavailable") from exc
        if verified is not True:
            raise ContractError(
                f"change_reclassification_approval_unverified:{row['id']}"
            )


def persist_snapshot(
    store: LocalArtifactStore | GitArtifactStore,
    request: dict[str, Any],
    *,
    expected_revision: str | None,
    approval_ref: str,
    approval_revision: str,
    change_reason: str,
    git_inventory_requests: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Persist a validated inventory using actual saved and Git source revisions."""
    try:
        report = handle(request)
        if report["status"] not in {"complete", "incomplete"}:
            return report
        _verify_git_evidence(request, report, git_inventory_requests)
        _authorize_reclassifications(store, request, expected_revision)
        snapshot = request["snapshot"]
        project_ref = snapshot["project_ref"]
        artifact_ref = snapshot["artifact_ref"]
        if expected_revision is not None:
            previous = store.read_revision(
                "feature-inventory", project_ref, artifact_ref, expected_revision
            )
            if previous is None:
                raise ContractError("previous_snapshot_missing")
            if json.loads(previous["content"]) != request["previous_snapshot"]:
                raise ContractError("previous_snapshot_not_current")
        elif request["previous_snapshot"] is not None:
            raise ContractError("previous_snapshot_without_expected_revision")
        content = json.dumps(
            snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
        written = store.write(
            kind="feature-inventory",
            project_ref=project_ref,
            artifact_ref=artifact_ref,
            content=content,
            expected_revision=expected_revision,
            operation_id=snapshot["operation_id"],
            source_ref=project_ref,
            source_revision=snapshot["source_revision"],
            approval_ref=approval_ref,
            approval_revision=approval_revision,
            change_reason=change_reason,
        )
        written["analysis_status"] = report["status"]
        written["snapshot_sha256"] = report["handoff"]["snapshot_sha256"]
        return written
    except (ContractError, StoreError, KeyError, TypeError, ValueError) as exc:
        return {"status": "blocked", "reasons": [str(exc)], "metrics": None}


def handle(request: Any) -> dict[str, Any]:
    try:
        return analyze(request)
    except (ContractError, KeyError, TypeError, RecursionError) as exc:
        return {"status": "blocked", "reasons": [str(exc)], "metrics": None}


def main() -> int:
    try:
        raw = sys.stdin.buffer.read(MAX_INPUT + 1)
        if len(raw) > MAX_INPUT:
            raise ContractError("input_too_large")
        request = json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs)
        result = handle(request)
    except (
        ContractError,
        UnicodeDecodeError,
        json.JSONDecodeError,
        RecursionError,
    ) as exc:
        result = {"status": "blocked", "reasons": [str(exc)], "metrics": None}
    sys.stdout.write(json.dumps(result, ensure_ascii=False, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
