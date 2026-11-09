"""Reconcile enumerated Git changes with the feature change inventory.

This checks coverage of changed Git paths, not completeness of semantic
product feature discovery. The Git inventory must originate from an authorized
source; a caller-supplied JSON assertion is not independent source evidence.
"""

from __future__ import annotations

import json
import sys
from typing import Any

from feature_registry import handle as validate_feature_registry

MAX_INPUT = 32 * 1024 * 1024


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


def analyze(request: Any) -> dict[str, Any]:
    required = {"git_inventory", "registry_request", "source_id"}
    allowed = required | {"previous_head_git_inventory"}
    if (
        not isinstance(request, dict)
        or not required <= set(request)
        or not set(request) <= allowed
    ):
        raise Invalid("request_schema_invalid")
    source_id = _text(request["source_id"], "source_id")
    git = request["git_inventory"]
    registry_request = request["registry_request"]
    if not isinstance(git, dict) or not isinstance(registry_request, dict):
        raise Invalid("inventory_or_registry_invalid")
    registry = validate_feature_registry(registry_request)
    if registry["status"] not in {"complete", "incomplete"}:
        return {
            "status": registry["status"],
            "reasons": registry.get("reasons", []),
            "coverage": None,
        }
    snapshot = registry_request["snapshot"]
    if git.get("status") != "complete":
        return {
            "status": "incomplete",
            "reasons": ["git_inventory_not_complete"],
            "coverage": None,
        }
    if (
        git.get("complete_file_listing") is not True
        or git.get("complete_change_listing") is not True
        or git.get("base_sha") is None
        or git.get("unretrieved") != []
    ):
        return {
            "status": "incomplete",
            "reasons": ["git_diff_listing_unconfirmed"],
            "coverage": None,
        }
    head_sha = _text(git.get("head_sha"), "git_head_sha")
    event = snapshot.get("event")
    basis = snapshot.get("event_basis")
    previous_inventory = request.get("previous_head_git_inventory")
    if event in {"pr_update", "rebase"}:
        if not isinstance(basis, dict):
            raise Invalid("event_basis_required")
        if git.get("base_sha") != basis["base_sha"] or head_sha != basis["head_sha"]:
            return {
                "status": "stale",
                "reasons": ["pr_base_head_inventory_mismatch"],
                "coverage": None,
            }
        if previous_inventory is None:
            return {
                "status": "incomplete",
                "reasons": ["previous_head_diff_not_enumerated"],
                "coverage": None,
            }
        if not isinstance(previous_inventory, dict):
            raise Invalid("previous_head_inventory_invalid")
        if (
            previous_inventory.get("status") != "complete"
            or previous_inventory.get("complete_change_listing") is not True
            or previous_inventory.get("unretrieved") != []
        ):
            return {
                "status": "incomplete",
                "reasons": ["previous_head_diff_incomplete"],
                "coverage": None,
            }
        if (
            previous_inventory.get("base_sha") != basis["previous_head_sha"]
            or previous_inventory.get("head_sha") != head_sha
        ):
            return {
                "status": "stale",
                "reasons": ["previous_head_diff_revision_mismatch"],
                "coverage": None,
            }
    elif previous_inventory is not None:
        raise Invalid("previous_head_inventory_unexpected")
    source_rows = [
        row
        for row in snapshot["sources"]
        if isinstance(row, dict) and row.get("id") == source_id
    ]
    if len(source_rows) != 1 or source_id not in snapshot["expected_source_ids"]:
        raise Invalid("git_source_not_in_expected_inventory")
    source = source_rows[0]
    if source["kind"] != "code" or source["status"] != "complete":
        raise Invalid("git_source_not_complete_code")
    if source["revision"] != head_sha or snapshot["source_revision"] != head_sha:
        return {
            "status": "stale",
            "reasons": ["git_revision_registry_mismatch"],
            "coverage": None,
        }
    files = git.get("files")
    changes = git.get("changes")
    if not isinstance(files, list) or not isinstance(changes, list):
        raise Invalid("git_manifest_arrays_invalid")
    head_paths: set[str] = set()
    for item in files:
        if not isinstance(item, dict):
            raise Invalid("git_file_invalid")
        path = _text(item.get("path"), "git_file_path")
        if path in head_paths:
            raise Invalid("duplicate_git_file")
        head_paths.add(path)
    git_paths: set[str] = set()
    for item in changes:
        if not isinstance(item, dict):
            raise Invalid("git_change_invalid")
        status = _text(item.get("status"), "git_change_status")
        before = _text(item.get("before_path"), "git_before_path")
        after = _text(item.get("after_path"), "git_after_path")
        if not (
            status in {"A", "M", "D", "T", "U", "X", "B"}
            or (
                status[:1] in {"R", "C"}
                and status[1:].isdigit()
                and len(status[1:]) <= 3
            )
        ):
            raise Invalid("git_change_status_invalid")
        if after in git_paths:
            raise Invalid("duplicate_git_change_path")
        git_paths.add(after)
        if status == "D" and after in head_paths:
            raise Invalid("deleted_path_present_at_head")
        if status != "D" and after not in head_paths:
            raise Invalid("changed_path_missing_at_head")
        if status[:1] not in {"R", "C"} and before != after:
            raise Invalid("non_rename_change_paths_mismatch")
    base_change_paths = set(git_paths)
    previous_head_paths: set[str] = set()
    if isinstance(previous_inventory, dict):
        preceding = previous_inventory.get("changes")
        if not isinstance(preceding, list):
            raise Invalid("previous_head_changes_invalid")
        for row in preceding:
            if not isinstance(row, dict):
                raise Invalid("previous_head_change_invalid")
            status = _text(row.get("status"), "previous_head_status")
            before = _text(row.get("before_path"), "previous_head_before_path")
            after = _text(row.get("after_path"), "previous_head_after_path")
            if not (
                status in {"A", "M", "D", "T", "U", "X", "B"}
                or (
                    status[:1] in {"R", "C"}
                    and status[1:].isdigit()
                    and len(status[1:]) <= 3
                )
            ):
                raise Invalid("previous_head_change_status_invalid")
            if after in previous_head_paths:
                raise Invalid("previous_head_change_duplicate")
            if status == "D" and after in head_paths:
                raise Invalid("previous_head_deleted_path_present")
            if status != "D" and after not in head_paths:
                raise Invalid("previous_head_changed_path_missing_at_head")
            if status[:1] not in {"R", "C"} and before != after:
                raise Invalid("previous_head_paths_mismatch")
            previous_head_paths.add(after)
    git_paths |= previous_head_paths
    registry_paths: set[str] = set()
    unmatched_ids: list[str] = []
    mismatched_revision_ids: list[str] = []
    unclassified_paths: set[str] = set()
    for row in snapshot["changes"]:
        if row["source_id"] != source_id:
            continue
        locator = row["locator"]
        registry_paths.add(locator)
        if locator not in git_paths:
            unmatched_ids.append(row["id"])
        valid_bases: set[str] = set()
        if locator in base_change_paths:
            valid_bases.add(git["base_sha"])
        if locator in previous_head_paths:
            valid_bases.add(basis["previous_head_sha"])
        if (
            row["before_revision"] not in valid_bases
            or row["after_revision"] != head_sha
        ):
            mismatched_revision_ids.append(row["id"])
        if row["classification"] in {"unclassified", "unresolved"}:
            unclassified_paths.add(locator)
    missing = sorted(git_paths - registry_paths)
    reasons = list(registry.get("reasons", []))
    if missing:
        reasons.append("git_changes_not_registered")
    if unmatched_ids:
        reasons.append("registry_changes_not_in_git_diff")
    if mismatched_revision_ids:
        reasons.append("git_change_revisions_mismatch")
    if unclassified_paths:
        reasons.append("git_changes_unclassified")
    return {
        "status": "complete" if not reasons else "incomplete",
        "reasons": sorted(set(reasons)),
        "coverage": {
            "source_id": source_id,
            "git_head_sha": head_sha,
            "git_change_paths": sorted(git_paths),
            "base_change_paths": sorted(base_change_paths),
            "previous_head_change_paths": sorted(previous_head_paths),
            "registered_paths": sorted(registry_paths & git_paths),
            "missing_git_paths": missing,
            "unmatched_registry_change_ids": sorted(unmatched_ids),
            "mismatched_revision_change_ids": sorted(mismatched_revision_ids),
            "unclassified_git_paths": sorted(unclassified_paths),
            "rate": (
                len(git_paths & registry_paths) / len(git_paths) if git_paths else None
            ),
            "candidate_snapshot_sha256": registry["handoff"]["snapshot_sha256"],
        },
    }


def handle(request: Any) -> dict[str, Any]:
    try:
        return analyze(request)
    except (Invalid, KeyError, TypeError, RecursionError) as exc:
        return {"status": "blocked", "reasons": [str(exc)], "coverage": None}


def main() -> int:
    try:
        raw = sys.stdin.buffer.read(MAX_INPUT + 1)
        if len(raw) > MAX_INPUT:
            raise Invalid("input_too_large")
        request = json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs)
        result = handle(request)
    except (Invalid, UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        result = {"status": "blocked", "reasons": [str(exc)], "coverage": None}
    sys.stdout.write(json.dumps(result, ensure_ascii=False, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
