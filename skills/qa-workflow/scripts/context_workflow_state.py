"""Persist context workflow references through qa-workflow's local SQLite state provider."""

from __future__ import annotations

import copy
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

import artifact_graph

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import context_artifact_store  # noqa: E402
import context_artifacts  # noqa: E402

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_A_STATUSES = {
    "unexecuted",
    "fetch_failed",
    "partial",
    "extract_failed",
    "persist_failed",
    "completed",
}
_REQUESTED_SCOPE_REQUIREMENTS = {"required", "excluded_by_approval"}
_CONTEXT_SKILLS = {"context-signal-audit", "context-rule-synthesis"}


def _fail(reason: str) -> None:
    raise ValueError(reason)


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        _fail(f"{label}_invalid")
    return value


def _normalize_requested_scopes(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        _fail("requested_scopes_invalid")
    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for row in value:
        if not isinstance(row, dict) or set(row) - {
            "skill",
            "target",
            "execution_range",
            "requirement",
            "approval_ref",
        }:
            _fail("requested_scopes_invalid")
        if not {"skill", "target", "execution_range", "requirement"}.issubset(row):
            _fail("requested_scopes_invalid")
        skill = _text(row["skill"], "requested_scope_skill")
        if skill == "qa-workflow":
            _fail("requested_scope_skill_invalid")
        target = row["target"]
        execution_range = row["execution_range"]
        if target is not None and (not isinstance(target, str) or not target.strip()):
            _fail("requested_scope_target_invalid")
        if execution_range is not None and (
            not isinstance(execution_range, str) or not execution_range.strip()
        ):
            _fail("requested_scope_execution_range_invalid")
        requirement = row["requirement"]
        if requirement not in _REQUESTED_SCOPE_REQUIREMENTS:
            _fail("requested_scope_requirement_invalid")
        approval_ref = row.get("approval_ref")
        if approval_ref is not None and not isinstance(approval_ref, str):
            _fail("requested_scope_approval_ref_invalid")
        if requirement == "required" and approval_ref is not None:
            _fail("required_scope_approval_ref_invalid")
        identity = (skill, str(target), str(execution_range))
        if identity in seen:
            _fail("requested_scope_duplicated")
        seen.add(identity)
        normalized = {
            "skill": skill,
            "target": target,
            "execution_range": execution_range,
            "requirement": requirement,
        }
        if "approval_ref" in row:
            normalized["approval_ref"] = approval_ref
        if skill in _CONTEXT_SKILLS and requirement in _REQUESTED_SCOPE_REQUIREMENTS:
            if not isinstance(target, str) or not target.strip():
                _fail("context_requested_scope_target_required")
            if not isinstance(execution_range, str) or not execution_range.strip():
                _fail("context_requested_scope_execution_range_required")
        rows.append(normalized)
    return sorted(
        rows,
        key=lambda row: (
            row["skill"],
            str(row["target"]),
            str(row["execution_range"]),
        ),
    )


def _scope_identity(scope: Any) -> tuple[str, str, str, str, str | None]:
    normalized = _normalize_requested_scopes([scope])[0]
    return (
        normalized["skill"],
        str(normalized["target"]),
        str(normalized["execution_range"]),
        normalized["requirement"],
        normalized.get("approval_ref"),
    )


def _hash(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        _fail(f"{label}_invalid")
    return value


def _canonical_hash(value: Any) -> str:
    return hashlib.sha256(context_artifacts.canonical_bytes(value)).hexdigest()


def _normalize_signal_record(
    record: Any, artifact_store: context_artifact_store.DirectoryArtifactStore
) -> dict[str, Any]:
    keys = {
        "attempt_id",
        "workflow_operation_id",
        "request_scope",
        "source",
        "requested_range",
        "observation_condition",
        "actual_inspected_range",
        "batch_refs",
        "candidate_check",
        "status",
        "failure_reason",
        "resume_condition",
    }
    if not isinstance(record, dict) or set(record) != keys:
        _fail("signal_attempt_schema_invalid")
    _hash(record["attempt_id"], "attempt_id")
    _hash(record["workflow_operation_id"], "workflow_operation_id")
    request_scope = _normalize_requested_scopes([record["request_scope"]])[0]
    if request_scope["skill"] != "context-signal-audit":
        _fail("signal_attempt_request_scope_invalid")
    source = record["source"]
    if not isinstance(source, dict) or set(source) != {
        "artifact_ref",
        "source_revision",
        "content_hash",
    }:
        _fail("signal_attempt_source_invalid")
    _text(source["artifact_ref"], "source_artifact_ref")
    if source["source_revision"] is not None:
        _text(source["source_revision"], "source_revision")
    if source["content_hash"] is not None:
        _hash(source["content_hash"], "source_content_hash")
    if (source["source_revision"] is None) != (source["content_hash"] is None):
        _fail("signal_attempt_source_version_incomplete")
    requested_range = context_artifacts.normalize_range(record["requested_range"])
    observation = record["observation_condition"]
    if observation is not None and not isinstance(observation, dict):
        _fail("observation_condition_invalid")
    actual_range = record["actual_inspected_range"]
    if actual_range is not None:
        actual_range = context_artifacts.normalize_range(actual_range)
    if not isinstance(record["batch_refs"], list):
        _fail("signal_attempt_batch_refs_invalid")
    candidate_check = record["candidate_check"]
    if not isinstance(candidate_check, dict) or set(candidate_check) != {
        "status",
        "triggered_candidate_identities",
    }:
        _fail("signal_attempt_candidate_check_invalid")
    if candidate_check["status"] not in {
        "checked_with_triggers",
        "checked_no_conflict",
        "not_checked",
    }:
        _fail("signal_attempt_candidate_check_invalid")
    candidates = candidate_check["triggered_candidate_identities"]
    if (
        not isinstance(candidates, list)
        or candidates != sorted(set(candidates))
        or not all(
            isinstance(item, str) and _SHA256.fullmatch(item) for item in candidates
        )
        or (candidate_check["status"] == "checked_with_triggers" and not candidates)
        or (candidate_check["status"] == "checked_no_conflict" and candidates)
    ):
        _fail("signal_attempt_candidate_check_invalid")
    status = record["status"]
    if status not in _A_STATUSES:
        _fail("signal_attempt_status_invalid")
    failure = record["failure_reason"]
    resume = record["resume_condition"]
    if failure is not None:
        _text(failure, "failure_reason")
    if resume is not None:
        _text(resume, "resume_condition")
    if status in {"fetch_failed", "partial", "extract_failed", "persist_failed"}:
        if failure is None or resume is None:
            _fail("signal_attempt_failure_recovery_required")

    batches: list[dict[str, Any]] = []
    refs: set[tuple[str, str]] = set()
    actual_ranges: list[dict[str, Any]] = []
    for row in record["batch_refs"]:
        if not isinstance(row, dict) or set(row) != {
            "artifact_ref",
            "revision",
            "content_hash",
            "assigned_range",
        }:
            _fail("signal_attempt_batch_ref_invalid")
        ref = _text(row["artifact_ref"], "batch_artifact_ref")
        revision = _text(row["revision"], "batch_revision")
        digest = _hash(row["content_hash"], "batch_content_hash")
        key = (ref, revision)
        if key in refs:
            _fail("signal_attempt_batch_ref_duplicated")
        refs.add(key)
        assigned = context_artifacts.normalize_range(row["assigned_range"])
        if not context_artifacts.range_contains(requested_range, assigned):
            _fail("signal_attempt_assigned_range_outside_request")
        readback = artifact_store.read(ref, revision)
        content = readback["content"].encode("utf-8")
        if readback["sha256"] != digest:
            _fail("signal_attempt_batch_readback_mismatch")
        batch = context_artifacts.parse_canonical_json(content)
        context_artifacts.validate_artifact(batch, "context-signal-batch")
        batch_source = batch["source"]
        if (
            batch_source["artifact_ref"] != source["artifact_ref"]
            or batch_source["source_content_hash"] != source["content_hash"]
            or batch_source["observation_condition"] != observation
            or not context_artifacts.batch_covers_request(
                batch,
                source_ref=source["artifact_ref"],
                source_content_hash=source["content_hash"],
                requested_range=assigned,
                observation_condition=observation,
            )
        ):
            _fail("signal_attempt_batch_request_mismatch")
        batches.append(batch)
        actual_ranges.append(batch_source["actual_inspected_range"])
    if batches:
        combined_actual = context_artifacts.range_union(actual_ranges)
        if actual_range != combined_actual:
            _fail("signal_attempt_actual_range_mismatch")
    elif actual_range is not None:
        _fail("signal_attempt_actual_range_without_batch")
    if status == "completed":
        if (
            source["source_revision"] is None
            or source["content_hash"] is None
            or not batches
            or not context_artifacts.batch_union_covers_request(
                batches,
                source_ref=source["artifact_ref"],
                source_content_hash=source["content_hash"],
                requested_range=requested_range,
                observation_condition=observation,
            )
        ):
            _fail("signal_attempt_completion_unverified")
    return copy.deepcopy(record) | {
        "request_scope": request_scope,
        "requested_range": requested_range,
        "actual_inspected_range": actual_range,
    }


def _source_key(source: dict[str, Any]) -> tuple[Any, ...]:
    return (
        source["artifact_ref"],
        source["content_hash"],
        source["effective_authority_fingerprint"],
    )


def _operation_input_identity(operation_input: dict[str, Any]) -> dict[str, Any]:
    return {
        "operation_type": operation_input["operation_type"],
        "input_sources": [
            {
                "artifact_ref": source["artifact_ref"],
                "content_hash": source["content_hash"],
                "effective_authority_fingerprint": source[
                    "effective_authority_fingerprint"
                ],
            }
            for source in operation_input["input_sources"]
        ],
        "investigation_conditions": operation_input["investigation_conditions"],
    }


def _verify_local_run_references(
    run: dict[str, Any],
    store: context_artifact_store.DirectoryArtifactStore,
) -> list[dict[str, Any]]:
    readbacks: dict[tuple[str, str], dict[str, Any]] = {}

    def retain(readback: dict[str, Any], expected_hash: str, reason: str) -> None:
        if readback["sha256"] != expected_hash:
            _fail(reason)
        key = (readback["artifact_ref"], readback["revision"])
        previous = readbacks.get(key)
        if previous is not None and previous != readback:
            _fail("run_local_readback_conflict")
        readbacks[key] = readback

    for source in run["snapshot"]["referenced_sources"]:
        expected_kind = {
            "signal_batch": "context-signal-batch",
            "candidate": "context-rule-candidate",
        }.get(source["source_kind"])
        if expected_kind is None:
            continue
        readback = store.read(source["artifact_ref"], source["source_revision"])
        retain(readback, source["content_hash"], "run_snapshot_readback_mismatch")
        artifact = context_artifacts.parse_canonical_json(readback["content"])
        context_artifacts.validate_artifact(artifact, expected_kind)
    for operation in run["triage_plan"]["planned_candidate_ops"]:
        result = operation["confirmed_result"]
        if result.get("artifact_ref") is not None:
            readback = store.read(result["artifact_ref"], result["storage_revision"])
            retain(
                readback,
                result["content_hash"],
                "run_candidate_result_readback_mismatch",
            )
            context_artifacts.validate_artifact(
                context_artifacts.parse_canonical_json(readback["content"]),
                "context-rule-candidate",
            )
        if operation["expected_revision"] is not None:
            readback = store.read(
                operation["candidate_ref"], operation["expected_revision"]
            )
            retain(
                readback,
                operation["base_content_hash"],
                "run_candidate_base_readback_mismatch",
            )
        for precondition in operation["related_preconditions"]:
            readback = store.read(
                precondition["candidate_ref"], precondition["expected_revision"]
            )
            retain(
                readback,
                precondition["content_hash"],
                "run_related_candidate_readback_mismatch",
            )
    return list(readbacks.values())


def _run_mapping(
    workflow_ref: str,
    requested_operation_input: Any,
    requested_scope: Any,
    run_readback: dict[str, Any],
    store: context_artifact_store.DirectoryArtifactStore,
) -> tuple[str, dict[str, Any], list[dict[str, Any]]]:
    request_id = context_artifacts.workflow_operation_id(
        workflow_ref, requested_operation_input, requested_scope
    )
    run_content = run_readback["content"].encode("utf-8", "strict")
    if hashlib.sha256(run_content).hexdigest() != run_readback["sha256"]:
        _fail("run_readback_hash_mismatch")
    run = context_artifacts.parse_canonical_json(run_content)
    context_artifacts.validate_artifact(run, "context-synthesis-run")
    if run_readback.get("root_binding") != store.root_binding:
        _fail("run_artifact_root_mismatch")
    local_readbacks = _verify_local_run_references(run, store)
    if (
        run["artifact_ref"] != run_readback["artifact_ref"]
        or run["workflow_ref"] != workflow_ref
        or run["workflow_operation_id"]
        != context_artifacts.workflow_operation_id(
            workflow_ref, run["operation_input"], run["requested_scope"]
        )
    ):
        _fail("run_readback_identity_mismatch")
    requested_sources = requested_operation_input["input_sources"]
    actual_sources = run["operation_input"]["input_sources"]
    source_by_key = {_source_key(item): item for item in requested_sources}
    actual_keys = {_source_key(item) for item in actual_sources}
    if (
        run["operation_input"]["operation_type"]
        != requested_operation_input["operation_type"]
        or run["operation_input"]["investigation_conditions"]
        != requested_operation_input["investigation_conditions"]
        or not actual_keys.issubset(source_by_key)
    ):
        _fail("run_start_input_mismatch")
    original_scope = requested_scope
    actual_scope = run["requested_scope"]
    original_scope_refs = set(original_scope["scope_refs"])
    actual_scope_refs = set(actual_scope["scope_refs"])
    if (
        actual_scope["analysis_aspect"] != original_scope["analysis_aspect"]
        or actual_scope["environment_and_versions"]
        != original_scope["environment_and_versions"]
        or not actual_scope_refs.issubset(original_scope_refs)
    ):
        _fail("run_execution_scope_outside_request")
    return (
        request_id,
        {
            "artifact_ref": run_readback["artifact_ref"],
            "revision": run_readback["revision"],
            "content_hash": run_readback["sha256"],
            "workflow_operation_id": run["workflow_operation_id"],
            "operation_input": run["operation_input"],
            "requested_scope": run["requested_scope"],
            "source_refs": sorted(source["artifact_ref"] for source in actual_sources),
            "scope_refs": sorted(actual_scope_refs),
            "target_batch_refs": run["triage_plan"]["target_batch_refs"],
            "run_status": run["result_summary"]["status"],
            "scan_completeness": run["scan_completeness"],
            "current": True,
        },
        local_readbacks,
    )


def _mapping_status(request: dict[str, Any]) -> dict[str, Any]:
    source_refs = sorted(
        source["artifact_ref"]
        for source in request["requested_operation_input"]["input_sources"]
    )
    scope_refs = sorted(request["requested_scope"]["scope_refs"])
    required_pairs = {(source, scope) for source in source_refs for scope in scope_refs}
    covered_pairs: set[tuple[str, str]] = set()
    for run in request["run_refs"]:
        if not run["current"]:
            continue
        covered_pairs.update(
            (source, scope)
            for source in run["source_refs"]
            for scope in run["scope_refs"]
        )
    missing_pairs = sorted(required_pairs - covered_pairs)
    # With no direct source input, run coverage is determined by requested scope.
    if not source_refs:
        covered_scopes = {
            scope
            for run in request["run_refs"]
            if run["current"]
            for scope in run["scope_refs"]
        }
        missing_pairs = [
            ("", scope) for scope in sorted(set(scope_refs) - covered_scopes)
        ]
    return {
        "status": "complete" if not missing_pairs else "incomplete",
        "unmapped_source_scope_pairs": [list(item) for item in missing_pairs],
    }


def _update_state(
    workflow_root: str,
    workflow_ref: str,
    expected_revision: str,
    field: str,
    update: Any,
    artifact_root_binding: str,
) -> dict[str, Any]:
    current = artifact_graph.read_sqlite_workflow_state(workflow_root, workflow_ref)
    if current.get("status") != "current":
        return {
            "status": "blocked",
            "reason": current.get("reason", "workflow_state_unavailable"),
        }
    if current["state_revision"] != expected_revision:
        return {
            "status": "conflict",
            "reason": "state_revision_changed",
            "current_revision": current["state_revision"],
        }
    state = copy.deepcopy(current["state"])
    existing_binding = state.get("context_artifact_root_binding")
    binding_changed = False
    if existing_binding is None:
        existing_rows = [
            state.get("context_signal_attempts", []),
            state.get("context_synthesis_run_refs", []),
        ]
        if any(not isinstance(rows, list) or rows for rows in existing_rows):
            _fail("workflow_artifact_root_binding_missing")
        state["context_artifact_root_binding"] = artifact_root_binding
        binding_changed = True
    elif existing_binding != artifact_root_binding:
        _fail("workflow_artifact_root_mismatch")
    rows = state.setdefault(field, [])
    if not isinstance(rows, list):
        return {"status": "blocked", "reason": f"{field}_state_corrupt"}
    action = update(rows)
    if action == "reused" and not binding_changed:
        return {
            "status": "reused",
            "workflow_ref": workflow_ref,
            "state_revision": current["state_revision"],
            "state": current["state"],
        }
    written = artifact_graph.conditional_write_sqlite_workflow_state(
        workflow_root, workflow_ref, expected_revision, state
    )
    if written.get("status") != "written":
        return written
    reread = artifact_graph.read_sqlite_workflow_state(workflow_root, workflow_ref)
    if reread.get("status") != "current" or reread.get("state") != state:
        return {
            "status": "blocked",
            "reason": "workflow_state_independent_readback_failed",
        }
    return {
        "status": "written",
        "workflow_ref": workflow_ref,
        "state_revision": reread["state_revision"],
        "state": reread["state"],
        "historical_revision_available": reread["historical_revision_available"],
    }


def record_signal_attempt(request: dict[str, Any]) -> dict[str, Any]:
    store = context_artifact_store.DirectoryArtifactStore(request["artifact_root"])
    record = _normalize_signal_record(request["record"], store)
    current = artifact_graph.read_sqlite_workflow_state(
        request["workflow_state_root"], request["workflow_ref"]
    )
    if current.get("status") != "current":
        return {
            "status": "blocked",
            "reason": current.get("reason", "workflow_state_unavailable"),
        }
    requested_scopes = current["state"].get("requested_scopes")
    if not isinstance(requested_scopes, list) or record["request_scope"] not in [
        _normalize_requested_scopes([row])[0] for row in requested_scopes
    ]:
        _fail("signal_attempt_start_request_not_registered")

    def add(rows: list[dict[str, Any]]) -> str | None:
        existing = next(
            (item for item in rows if item.get("attempt_id") == record["attempt_id"]),
            None,
        )
        if existing is not None:
            if existing == record:
                return "reused"
            _fail("signal_attempt_id_conflict")
        rows.append(record)
        return None

    return _update_state(
        request["workflow_state_root"],
        request["workflow_ref"],
        request["expected_revision"],
        "context_signal_attempts",
        add,
        store.root_binding,
    )


def record_synthesis_run(request: dict[str, Any]) -> dict[str, Any]:
    store = context_artifact_store.DirectoryArtifactStore(request["artifact_root"])
    request_scope = _normalize_requested_scopes([request["request_scope"]])[0]
    if request_scope["skill"] != "context-rule-synthesis":
        _fail("synthesis_request_scope_invalid")
    current = artifact_graph.read_sqlite_workflow_state(
        request["workflow_state_root"], request["workflow_ref"]
    )
    if current.get("status") != "current":
        return {
            "status": "blocked",
            "reason": current.get("reason", "workflow_state_unavailable"),
        }
    requested_scopes = current["state"].get("requested_scopes")
    if not isinstance(requested_scopes, list) or request_scope not in [
        _normalize_requested_scopes([row])[0] for row in requested_scopes
    ]:
        _fail("synthesis_start_request_not_registered")
    readback = store.read(request["run_ref"], request["run_revision"])
    request_id, run_entry, _ = _run_mapping(
        request["workflow_ref"],
        request["requested_operation_input"],
        request["requested_scope"],
        readback,
        store,
    )

    def add(rows: list[dict[str, Any]]) -> str | None:
        group = next(
            (item for item in rows if item.get("request_id") == request_id), None
        )
        if group is None:
            group = {
                "request_id": request_id,
                "request_scopes": [request_scope],
                "requested_operation_input": copy.deepcopy(
                    request["requested_operation_input"]
                ),
                "requested_scope": copy.deepcopy(request["requested_scope"]),
                "run_refs": [],
            }
            rows.append(group)
            request_scope_added = True
        elif (
            _operation_input_identity(group.get("requested_operation_input", {}))
            != _operation_input_identity(request["requested_operation_input"])
            or group.get("requested_scope") != request["requested_scope"]
        ):
            _fail("synthesis_request_id_conflict")
        else:
            group_request_scopes = group.get("request_scopes")
            if not isinstance(group_request_scopes, list):
                _fail("synthesis_request_scopes_state_corrupt")
            request_scope_added = request_scope not in group_request_scopes
            if request_scope_added:
                group_request_scopes.append(request_scope)
        previous = next(
            (
                item
                for item in group["run_refs"]
                if item["artifact_ref"] == run_entry["artifact_ref"]
                and item["revision"] == run_entry["revision"]
            ),
            None,
        )
        if previous is not None:
            if {key: value for key, value in previous.items() if key != "current"} != {
                key: value for key, value in run_entry.items() if key != "current"
            }:
                _fail("synthesis_run_revision_conflict")
            return None if request_scope_added else "reused"
        for item in group["run_refs"]:
            if item["artifact_ref"] == run_entry["artifact_ref"]:
                item["current"] = False
        group["run_refs"].append(run_entry)
        group["mapping"] = _mapping_status(group)
        return None

    return _update_state(
        request["workflow_state_root"],
        request["workflow_ref"],
        request["expected_revision"],
        "context_synthesis_run_refs",
        add,
        store.root_binding,
    )


def record_requested_scopes(request: dict[str, Any]) -> dict[str, Any]:
    """Freeze qa-workflow's initial request set in the existing workflow state."""
    store = context_artifact_store.DirectoryArtifactStore(request["artifact_root"])
    requested = _normalize_requested_scopes(request["requested_scopes"])

    def set_once(rows: list[dict[str, Any]]) -> str | None:
        existing = _normalize_requested_scopes(rows)
        if existing == requested:
            return "reused"
        if existing:
            _fail("workflow_requested_scopes_conflict")
        current = artifact_graph.read_sqlite_workflow_state(
            request["workflow_state_root"], request["workflow_ref"]
        )
        state = current.get("state") if current.get("status") == "current" else {}
        if state.get("context_signal_attempts") or state.get(
            "context_synthesis_run_refs"
        ):
            _fail("workflow_requested_scopes_registered_after_context_execution")
        rows.extend(requested)
        return None

    return _update_state(
        request["workflow_state_root"],
        request["workflow_ref"],
        request["expected_revision"],
        "requested_scopes",
        set_once,
        store.root_binding,
    )


def complete_synthesis_request(request: dict[str, Any]) -> dict[str, Any]:
    """Re-read a full request group before qa-workflow accepts its run scopes."""
    store = context_artifact_store.DirectoryArtifactStore(request["artifact_root"])
    workflow_ref = request["workflow_ref"]
    requested_input = request["requested_operation_input"]
    requested_scope = request["requested_scope"]
    request_scopes = _normalize_requested_scopes(
        request.get("request_scopes", [request.get("request_scope")])
    )
    request_id = context_artifacts.workflow_operation_id(
        workflow_ref, requested_input, requested_scope
    )
    current = artifact_graph.read_sqlite_workflow_state(
        request["workflow_state_root"], workflow_ref
    )
    if current.get("status") != "current":
        _fail(current.get("reason", "workflow_state_unavailable"))
    state = current["state"]
    if state.get("context_artifact_root_binding") != store.root_binding:
        _fail("workflow_artifact_root_mismatch")
    groups = state.get("context_synthesis_run_refs")
    if not isinstance(groups, list):
        _fail("context_synthesis_run_refs_state_corrupt")
    if not all(isinstance(item, dict) for item in groups):
        _fail("context_synthesis_run_refs_state_corrupt")
    matching = [item for item in groups if item.get("request_id") == request_id]
    if len(matching) != 1:
        _fail("synthesis_request_state_missing_or_duplicated")
    group = matching[0]
    if (
        _operation_input_identity(group.get("requested_operation_input", {}))
        != _operation_input_identity(requested_input)
        or group.get("requested_scope") != requested_scope
        or not isinstance(group.get("request_scopes"), list)
        or any(item not in group["request_scopes"] for item in request_scopes)
    ):
        _fail("synthesis_request_state_mismatch")
    run_refs = group.get("run_refs")
    if not isinstance(run_refs, list):
        _fail("synthesis_run_refs_state_corrupt")
    if not all(isinstance(item, dict) for item in run_refs):
        _fail("synthesis_run_refs_state_corrupt")
    current_refs = [item for item in run_refs if item.get("current") is True]
    if any(type(item.get("current")) is not bool for item in run_refs):
        _fail("synthesis_run_refs_state_corrupt")
    if not current_refs:
        return {
            "status": "incomplete",
            "complete": False,
            "reason": "synthesis_run_missing",
            "request_id": request_id,
            "checked_run_refs": [],
            "state_revision": current["state_revision"],
        }
    workflow_readbacks = request.get("provider_readbacks", [])
    if not isinstance(workflow_readbacks, list):
        _fail("workflow_provider_readbacks_invalid")

    mapping = _mapping_status(
        {
            "requested_operation_input": requested_input,
            "requested_scope": requested_scope,
            "run_refs": current_refs,
        }
    )
    if mapping["status"] != "complete":
        return {
            "status": "incomplete",
            "complete": False,
            "reason": "requested_run_mapping_incomplete",
            "request_id": request_id,
            "unmapped_source_scope_pairs": mapping["unmapped_source_scope_pairs"],
            "state_revision": current["state_revision"],
        }

    checked: list[dict[str, str]] = []
    for entry in current_refs:
        if not isinstance(entry, dict) or set(entry) != {
            "artifact_ref",
            "revision",
            "content_hash",
            "workflow_operation_id",
            "operation_input",
            "requested_scope",
            "source_refs",
            "scope_refs",
            "target_batch_refs",
            "run_status",
            "scan_completeness",
            "current",
        }:
            _fail("synthesis_run_ref_state_invalid")
        readback = store.read(entry["artifact_ref"], entry["revision"])
        if (
            readback["root_binding"] != store.root_binding
            or readback["artifact_ref"] != entry["artifact_ref"]
            or readback["revision"] != entry["revision"]
            or readback["sha256"] != entry["content_hash"]
        ):
            _fail("synthesis_run_readback_mismatch")
        _, verified_entry, local_readbacks = _run_mapping(
            workflow_ref,
            requested_input,
            requested_scope,
            readback,
            store,
        )
        if any(
            entry.get(key) != value
            for key, value in verified_entry.items()
            if key != "current"
        ):
            _fail("synthesis_run_state_mapping_mismatch")
        if (
            entry["run_status"] not in {"completed", "completed_zero_changes"}
            or entry["scan_completeness"] != "complete"
        ):
            return {
                "status": "incomplete",
                "complete": False,
                "reason": "synthesis_run_not_completed",
                "request_id": request_id,
                "incomplete_run_ref": entry["artifact_ref"],
                "checked_run_refs": checked,
                "state_revision": current["state_revision"],
            }
        all_readbacks: dict[tuple[str, str], dict[str, Any]] = {}
        for value in [*workflow_readbacks, *local_readbacks, readback]:
            if not isinstance(value, dict):
                _fail("workflow_provider_readback_invalid")
            key = (value.get("artifact_ref"), value.get("revision"))
            previous = all_readbacks.get(key)
            if previous is not None and previous != value:
                _fail("workflow_provider_readback_conflict")
            all_readbacks[key] = value
        run = context_artifacts.parse_canonical_json(readback["content"])
        completion = context_artifacts.completion_check(
            run,
            root_binding=store.root_binding,
            provider_readbacks=list(all_readbacks.values()),
            run_readback_revision=readback["revision"],
        )
        if (
            completion.get("complete") is not True
            or completion.get("status") != "complete"
        ):
            return {
                "status": "incomplete",
                "complete": False,
                "reason": completion.get("reason", "run_provider_readbacks_incomplete"),
                "request_id": request_id,
                "incomplete_run_ref": entry["artifact_ref"],
                "checked_run_refs": checked,
                "state_revision": current["state_revision"],
            }
        checked.append(
            {
                "artifact_ref": entry["artifact_ref"],
                "revision": entry["revision"],
                "content_hash": entry["content_hash"],
            }
        )

    latest = artifact_graph.read_sqlite_workflow_state(
        request["workflow_state_root"], workflow_ref
    )
    if (
        latest.get("status") != "current"
        or latest.get("state_revision") != current["state_revision"]
        or latest.get("state") != state
    ):
        _fail("workflow_state_changed_during_completion_check")
    return {
        "status": "complete",
        "complete": True,
        "request_id": request_id,
        "artifact_root_binding": store.root_binding,
        "checked_run_refs": checked,
        "state_revision": current["state_revision"],
    }


def _scope_base_identity(scope: dict[str, Any]) -> tuple[str, str, str]:
    return (scope["skill"], str(scope["target"]), str(scope["execution_range"]))


def _scope_rows_from_context_state(value: dict[str, Any]) -> list[dict[str, Any]]:
    raw = value.get("request_scopes")
    if raw is None:
        raw = [value.get("request_scope")]
    return _normalize_requested_scopes(raw)


def _verified_owner_by_scope(value: Any) -> dict[tuple[str, str, str], dict[str, Any]]:
    if not isinstance(value, list):
        _fail("workflow_verified_owner_scopes_invalid")
    result: dict[tuple[str, str, str], dict[str, Any]] = {}
    for row in value:
        if not isinstance(row, dict) or not isinstance(
            row.get("verified_artifact"), dict
        ):
            _fail("workflow_verified_owner_scope_invalid")
        identity = _scope_base_identity(row)
        if identity in result and result[identity] != row:
            _fail("workflow_verified_owner_scope_conflict")
        result[identity] = row
    return result


def _owner_record_matches(
    owner_by_scope: dict[tuple[str, str, str], dict[str, Any]],
    skill: str,
    target: str,
    execution_range: str,
    revision: str,
    content_hash: str,
) -> bool:
    row = owner_by_scope.get((skill, target, execution_range))
    if row is None:
        return False
    artifact = row["verified_artifact"]
    return (
        artifact.get("artifact_ref") == target
        and artifact.get("artifact_revision") == revision
        and artifact.get("content_hash") == content_hash
    )


def complete_context_workflow(request: dict[str, Any]) -> dict[str, Any]:
    """Reconcile start-time required scopes with current A/B artifacts and readbacks."""
    store = context_artifact_store.DirectoryArtifactStore(request["artifact_root"])
    workflow_ref = _text(request["workflow_ref"], "workflow_ref")
    current = artifact_graph.read_sqlite_workflow_state(
        request["workflow_state_root"], workflow_ref
    )
    if current.get("status") != "current":
        _fail(current.get("reason", "workflow_state_unavailable"))
    state = current["state"]
    if state.get("context_artifact_root_binding") != store.root_binding:
        _fail("workflow_artifact_root_mismatch")
    start_requested = _normalize_requested_scopes(state.get("requested_scopes"))
    runtime_requested = _normalize_requested_scopes(request["requested_scopes"])
    initial_required = [
        row for row in start_requested if row["skill"] in _CONTEXT_SKILLS
    ]
    current_required = [
        row for row in runtime_requested if row["skill"] in _CONTEXT_SKILLS
    ]
    if not initial_required:
        if current_required:
            return {
                "status": "incomplete",
                "complete": False,
                "reason": "context_start_request_snapshot_missing",
                "state_revision": current["state_revision"],
            }
        return {
            "status": "complete",
            "complete": True,
            "state_revision": current["state_revision"],
            "checked_requests": [],
            "mapped_scopes": [],
        }

    context_scopes = request.get("context_scopes")
    if not isinstance(context_scopes, list):
        _fail("workflow_context_scopes_invalid")
    if not context_scopes:
        return {
            "status": "incomplete",
            "complete": False,
            "reason": "context_required_scopes_missing_from_runtime",
            "state_revision": current["state_revision"],
            "missing_request_scopes": initial_required,
        }
    provider_readbacks = request.get("provider_readbacks", [])
    if not isinstance(provider_readbacks, list):
        _fail("workflow_provider_readbacks_invalid")
    owner_by_scope = _verified_owner_by_scope(request.get("verified_owner_scopes", []))

    context_state_by_scope: dict[
        tuple[str, str, str],
        tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]],
    ] = {}
    for scope in context_scopes:
        if not isinstance(scope, dict) or scope.get("skill") not in _CONTEXT_SKILLS:
            _fail("workflow_context_scope_invalid")
        normalized = scope.get("normalized_input")
        context_state = (
            normalized.get("context_workflow_state")
            if isinstance(normalized, dict)
            else None
        )
        if not isinstance(context_state, dict):
            _fail("workflow_context_state_request_missing")
        expected_keys = {"artifact_root", "workflow_state_root"}
        if scope["skill"] == "context-rule-synthesis":
            expected_keys |= {"requested_operation_input", "requested_scope"}
        valid_context_state_keys = {
            frozenset(expected_keys | {"request_scope"}),
            frozenset(expected_keys | {"request_scopes"}),
            frozenset(expected_keys | {"request_scope", "request_scopes"}),
        }
        if frozenset(context_state) not in valid_context_state_keys:
            _fail("workflow_context_state_request_invalid")
        if (
            context_state["artifact_root"] != request["artifact_root"]
            or context_state["workflow_state_root"] != request["workflow_state_root"]
        ):
            _fail("workflow_context_root_mismatch")
        request_rows = _scope_rows_from_context_state(context_state)
        if any(row["skill"] != scope["skill"] for row in request_rows):
            _fail("workflow_context_request_skill_mismatch")
        identity = _scope_base_identity(scope)
        previous = context_state_by_scope.get(identity)
        current_value = (scope, context_state, request_rows)
        if previous is not None and previous != current_value:
            _fail("workflow_context_scope_conflict")
        context_state_by_scope[identity] = current_value

    attempts = state.get("context_signal_attempts")
    groups = state.get("context_synthesis_run_refs")
    if not isinstance(attempts, list) or not isinstance(groups, list):
        _fail("context_workflow_state_corrupt")

    mapped_scope_ids: set[tuple[str, str, str]] = set()
    checked_requests: list[dict[str, Any]] = []
    current_a_batches: dict[str, tuple[str, str]] = {}
    for requested in initial_required:
        requested_identity = _scope_identity(requested)
        if requested["skill"] == "context-signal-audit":
            matching = [
                row
                for row in attempts
                if isinstance(row, dict)
                and isinstance(row.get("request_scope"), dict)
                and _scope_identity(row["request_scope"]) == requested_identity
            ]
            if not matching:
                return {
                    "status": "incomplete",
                    "complete": False,
                    "reason": "signal_required_request_unmapped",
                    "request_scope": requested,
                    "state_revision": current["state_revision"],
                }
            # Attempts stay as history. The latest attempt for this exact start
            # request is the only one allowed to establish current completion.
            attempt = _normalize_signal_record(matching[-1], store)
            if attempt["status"] != "completed":
                return {
                    "status": "incomplete",
                    "complete": False,
                    "reason": "signal_required_request_not_completed",
                    "request_scope": requested,
                    "attempt_status": attempt["status"],
                    "state_revision": current["state_revision"],
                }
            for batch_ref in attempt["batch_refs"]:
                assigned = batch_ref["assigned_range"]
                execution_range = json.dumps(
                    assigned,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                )
                identity = (
                    "context-signal-audit",
                    batch_ref["artifact_ref"],
                    execution_range,
                )
                found = context_state_by_scope.get(identity)
                if found is None:
                    return {
                        "status": "incomplete",
                        "complete": False,
                        "reason": "signal_batch_owner_scope_missing",
                        "request_scope": requested,
                        "artifact_ref": batch_ref["artifact_ref"],
                        "state_revision": current["state_revision"],
                    }
                scope, context_state, request_rows = found
                if requested not in request_rows:
                    _fail("signal_batch_request_mapping_mismatch")
                owner_evidence = scope["normalized_input"].get("owner_verification")
                context_request = scope["normalized_input"].get("context_request")
                if not isinstance(owner_evidence, dict) or not isinstance(
                    context_request, dict
                ):
                    _fail("signal_batch_owner_evidence_missing")
                readback = store.read(batch_ref["artifact_ref"], batch_ref["revision"])
                if (
                    readback["root_binding"] != store.root_binding
                    or readback["sha256"] != batch_ref["content_hash"]
                    or owner_evidence.get("root_binding") != store.root_binding
                    or owner_evidence.get("readback") != readback
                    or context_request.get("workflow_ref") != workflow_ref
                    or context_request.get("source_artifact_ref")
                    != attempt["source"]["artifact_ref"]
                    or context_request.get("source_revision")
                    != attempt["source"]["source_revision"]
                    or context_request.get("source_content_hash")
                    != attempt["source"]["content_hash"]
                    or context_artifacts.normalize_range(
                        context_request.get("requested_range")
                    )
                    != attempt["requested_range"]
                    or context_artifacts.normalize_range(
                        context_request.get("assigned_range")
                    )
                    != assigned
                    or context_request.get("observation_condition")
                    != attempt["observation_condition"]
                    or not _owner_record_matches(
                        owner_by_scope,
                        "context-signal-audit",
                        batch_ref["artifact_ref"],
                        execution_range,
                        batch_ref["revision"],
                        batch_ref["content_hash"],
                    )
                ):
                    _fail("signal_owner_and_state_mapping_mismatch")
                mapped_scope_ids.add(identity)
                current_a_batches[batch_ref["artifact_ref"]] = (
                    batch_ref["revision"],
                    batch_ref["content_hash"],
                )
            checked_requests.append(
                {
                    "request_scope": requested,
                    "status": "completed",
                    "artifact_count": len(attempt["batch_refs"]),
                }
            )
            continue

        matching_groups = [
            row
            for row in groups
            if isinstance(row, dict)
            and isinstance(row.get("request_scopes"), list)
            and any(
                isinstance(item, dict) and _scope_identity(item) == requested_identity
                for item in row["request_scopes"]
            )
        ]
        if not matching_groups:
            return {
                "status": "incomplete",
                "complete": False,
                "reason": "synthesis_required_request_group_missing",
                "request_scope": requested,
                "state_revision": current["state_revision"],
            }
        if len(matching_groups) != 1:
            _fail("synthesis_required_request_group_duplicated")
        group = matching_groups[0]
        operation_input = group.get("requested_operation_input")
        requested_scope = group.get("requested_scope")
        if not isinstance(operation_input, dict) or not isinstance(
            requested_scope, dict
        ):
            _fail("synthesis_request_state_invalid")
        group_scopes = [
            value
            for value in context_scopes
            if value["skill"] == "context-rule-synthesis"
            and requested
            in _scope_rows_from_context_state(
                value["normalized_input"]["context_workflow_state"]
            )
            and _operation_input_identity(
                value["normalized_input"]["context_workflow_state"].get(
                    "requested_operation_input", {}
                )
            )
            == _operation_input_identity(operation_input)
            and value["normalized_input"]["context_workflow_state"].get(
                "requested_scope"
            )
            == requested_scope
        ]
        if not group_scopes:
            return {
                "status": "incomplete",
                "complete": False,
                "reason": "synthesis_required_request_missing_from_runtime",
                "request_scope": requested,
                "state_revision": current["state_revision"],
            }
        complete = complete_synthesis_request(
            {
                "workflow_state_root": request["workflow_state_root"],
                "workflow_ref": workflow_ref,
                "artifact_root": request["artifact_root"],
                "requested_operation_input": operation_input,
                "requested_scope": requested_scope,
                "request_scopes": [requested],
                "provider_readbacks": provider_readbacks,
            }
        )
        if complete.get("complete") is not True or complete.get("status") != "complete":
            return complete
        for run_entry in group.get("run_refs", []):
            if not isinstance(run_entry, dict) or run_entry.get("current") is not True:
                continue
            readback = store.read(run_entry["artifact_ref"], run_entry["revision"])
            run = context_artifacts.parse_canonical_json(readback["content"])
            execution_range = "run:" + run["run_identity"]
            identity = (
                "context-rule-synthesis",
                run_entry["artifact_ref"],
                execution_range,
            )
            found = context_state_by_scope.get(identity)
            if found is None:
                return {
                    "status": "incomplete",
                    "complete": False,
                    "reason": "synthesis_run_owner_scope_missing",
                    "request_scope": requested,
                    "artifact_ref": run_entry["artifact_ref"],
                    "state_revision": current["state_revision"],
                }
            scope, context_state, request_rows = found
            context_input = context_state.get("requested_operation_input")
            context_scope = context_state.get("requested_scope")
            owner_request = scope["normalized_input"].get("context_request")
            if (
                requested not in request_rows
                or _operation_input_identity(context_input or {})
                != _operation_input_identity(operation_input)
                or context_scope != requested_scope
                or not isinstance(owner_request, dict)
                or owner_request.get("workflow_ref") != workflow_ref
                or owner_request.get("operation_input") != run["operation_input"]
                or owner_request.get("requested_scope") != run["requested_scope"]
                or owner_request.get("target_batch_refs")
                != run["triage_plan"]["target_batch_refs"]
                or not _owner_record_matches(
                    owner_by_scope,
                    "context-rule-synthesis",
                    run_entry["artifact_ref"],
                    execution_range,
                    run_entry["revision"],
                    run_entry["content_hash"],
                )
            ):
                _fail("synthesis_owner_and_state_mapping_mismatch")
            for batch_ref in run["triage_plan"]["target_batch_refs"]:
                expected_batch = current_a_batches.get(batch_ref)
                if expected_batch is None:
                    continue
                matching_sources = [
                    source
                    for source in run["snapshot"]["referenced_sources"]
                    if source["source_kind"] == "signal_batch"
                    and source["artifact_ref"] == batch_ref
                ]
                if (
                    len(matching_sources) != 1
                    or (
                        matching_sources[0]["source_revision"],
                        matching_sources[0]["content_hash"],
                    )
                    != expected_batch
                ):
                    _fail("synthesis_target_batch_differs_from_signal_state")
            mapped_scope_ids.add(identity)
        checked_requests.append(
            {
                "request_scope": requested,
                "status": "completed",
                "run_count": len(complete.get("checked_run_refs", [])),
            }
        )

    current_required_ids = {_scope_base_identity(row) for row in current_required}
    if mapped_scope_ids != current_required_ids:
        return {
            "status": "incomplete",
            "complete": False,
            "reason": "context_final_requested_scope_set_mismatch",
            "missing_final_scopes": [
                list(identity)
                for identity in sorted(current_required_ids - mapped_scope_ids)
            ],
            "unrequested_mapped_scopes": [
                list(identity)
                for identity in sorted(mapped_scope_ids - current_required_ids)
            ],
            "state_revision": current["state_revision"],
        }

    latest = artifact_graph.read_sqlite_workflow_state(
        request["workflow_state_root"], workflow_ref
    )
    if (
        latest.get("status") != "current"
        or latest.get("state_revision") != current["state_revision"]
        or latest.get("state") != state
    ):
        _fail("workflow_state_changed_during_completion_check")
    return {
        "status": "complete",
        "complete": True,
        "workflow_ref": workflow_ref,
        "artifact_root_binding": store.root_binding,
        "state_revision": current["state_revision"],
        "checked_requests": checked_requests,
        "mapped_scopes": [list(identity) for identity in sorted(mapped_scope_ids)],
    }


def initialize_state(request: dict[str, Any]) -> dict[str, Any]:
    workflow_root = request["workflow_state_root"]
    workflow_ref = request["workflow_ref"]
    initial_state = request["initial_state"]
    if not isinstance(initial_state, dict):
        _fail("initial_workflow_state_invalid")
    if artifact_graph.canonical_state_path(workflow_root, workflow_ref).exists():
        return {
            "status": "blocked",
            "reason": "legacy_json_workflow_state_update_unavailable",
        }
    current = artifact_graph.read_sqlite_workflow_state(workflow_root, workflow_ref)
    if current.get("status") == "current":
        return current
    if current.get("reason") != "workflow_state_not_found":
        return {
            "status": "blocked",
            "reason": current.get("reason", "workflow_state_unavailable"),
        }
    state = copy.deepcopy(initial_state)
    state.setdefault("context_artifact_root_binding", None)
    for field in ("context_signal_attempts", "context_synthesis_run_refs"):
        existing = state.setdefault(field, [])
        if not isinstance(existing, list):
            _fail(f"{field}_state_corrupt")
    requested_scopes = state.setdefault("requested_scopes", [])
    state["requested_scopes"] = _normalize_requested_scopes(requested_scopes)
    return artifact_graph.create_sqlite_workflow_state(
        workflow_root, workflow_ref, state
    )


def handle(request: Any) -> dict[str, Any]:
    if not isinstance(request, dict):
        return {"status": "blocked", "reason": "request_must_be_object"}
    try:
        operation = request.get("operation")
        if operation == "initialize":
            return initialize_state(request)
        if operation == "read":
            state = artifact_graph.read_sqlite_workflow_state(
                request["workflow_state_root"], request["workflow_ref"]
            )
            return state
        if operation == "record-signal-attempt":
            return record_signal_attempt(request)
        if operation == "record-synthesis-run":
            return record_synthesis_run(request)
        if operation == "register-requested-scopes":
            return record_requested_scopes(request)
        if operation == "completion-check":
            return complete_synthesis_request(request)
        if operation == "completion-check-workflow":
            return complete_context_workflow(request)
        _fail("operation_invalid")
    except (
        KeyError,
        OSError,
        TypeError,
        ValueError,
        UnicodeError,
        context_artifact_store.StoreError,
        context_artifacts.ContractError,
    ) as exc:
        return {"status": "blocked", "reason": str(exc) or type(exc).__name__}


def main() -> int:
    raw = sys.stdin.buffer.read(context_artifacts.MAX_ARTIFACT_BYTES + 1)
    if len(raw) > context_artifacts.MAX_ARTIFACT_BYTES:
        result = {"status": "blocked", "reason": "input_too_large"}
    else:
        try:
            result = handle(json.loads(raw.decode("utf-8", "strict")))
        except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
            result = {
                "status": "blocked",
                "reason": f"invalid_request:{type(exc).__name__}",
            }
    sys.stdout.write(
        json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
