"""Validate source inventory, feature IDs, change classification and history.

The caller owns semantic decisions. This validator never fetches sources or writes
artifacts, and never claims that all product functions have been discovered.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from typing import Any

MAX_INPUT = 16 * 1024 * 1024
ID = re.compile(r"^(SRC|CAND|FEAT|DIF)-[0-9]{3,}$")
EVENTS = {"initial", "pr_update", "merge", "release", "external_revision"}
SOURCE_STATES = {"complete", "partial", "denied", "unavailable"}
FEATURE_KINDS = {"ui", "api", "batch", "integration", "authorization", "data", "other"}
FEATURE_STATES = {"planned", "implemented", "retired", "unknown"}
CHANGE_STATES = {"impact", "no_impact", "out_of_scope", "unclassified", "unresolved"}
HISTORY_KINDS = {"added", "changed", "renamed", "split", "merged", "retired"}


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
            if cls == "out_of_scope":
                _text(row.get("approval_ref"), f"{did}_approval_ref")
        else:
            issues.append(f"change_unclassified:{did}")
    return changes, issues


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
    old_features = _rows(previous.get("features"), "previous_features", "FEAT")
    old_history = _list(previous.get("history"), "previous_history")
    if events[: len(old_history)] != old_history:
        raise ContractError("history_rewritten")
    for fid, old in old_features.items():
        if fid not in features:
            raise ContractError(f"historical_feature_removed:{fid}")
        if old.get("identity") != features[fid]["identity"]:
            raise ContractError(f"historical_identity_reused:{fid}")
        if old.get("status") == "retired" and features[fid]["status"] != "retired":
            raise ContractError(f"retired_identity_reactivated:{fid}")
        if old.get("status") != "retired" and features[fid]["status"] == "retired":
            if not any(
                e["kind"] in {"retired", "split", "merged"} and fid in e["from_ids"]
                for e in events[len(old_history) :]
            ):
                raise ContractError(f"retirement_evidence_missing:{fid}")


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
    _history(snapshot, previous, features, idempotent=idempotent)
    unknown = _refs(snapshot.get("unknown_areas"), "unknown_areas")
    if unknown:
        issues.append("unknown_areas_present")
    classified = sorted(
        did
        for did, row in changes.items()
        if row["classification"] in {"impact", "no_impact", "out_of_scope"}
    )
    mapped = sorted(cid for cid, row in candidates.items() if row["status"] == "mapped")
    if not changes:
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
                "denominator_ids": sorted(changes),
                "rate": len(classified) / len(changes) if changes else None,
            },
            "observed_candidate_mapping": {
                "numerator_ids": mapped,
                "denominator_ids": sorted(candidates),
                "rate": len(mapped) / len(candidates) if candidates else None,
            },
            "source_boundary_complete": not any(
                v.startswith("source_") for v in issues
            ),
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
            "unclassified_change_ids": sorted(set(changes) - set(classified)),
            "expected_source_ids": snapshot["expected_source_ids"],
        },
    }


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
