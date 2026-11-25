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


def _fail(reason: str) -> None:
    raise ValueError(reason)


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        _fail(f"{label}_invalid")
    return value


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
) -> None:
    for source in run["snapshot"]["referenced_sources"]:
        expected_kind = {
            "signal_batch": "context-signal-batch",
            "candidate": "context-rule-candidate",
        }.get(source["source_kind"])
        if expected_kind is None:
            continue
        readback = store.read(source["artifact_ref"], source["source_revision"])
        if readback["sha256"] != source["content_hash"]:
            _fail("run_snapshot_readback_mismatch")
        artifact = context_artifacts.parse_canonical_json(readback["content"])
        context_artifacts.validate_artifact(artifact, expected_kind)
    for operation in run["triage_plan"]["planned_candidate_ops"]:
        result = operation["confirmed_result"]
        if isinstance(result, dict):
            readback = store.read(result["artifact_ref"], result["storage_revision"])
            if readback["sha256"] != result["content_hash"]:
                _fail("run_candidate_result_readback_mismatch")
            context_artifacts.validate_artifact(
                context_artifacts.parse_canonical_json(readback["content"]),
                "context-rule-candidate",
            )
        if operation["expected_revision"] is not None:
            readback = store.read(
                operation["candidate_ref"], operation["expected_revision"]
            )
            if readback["sha256"] != operation["base_content_hash"]:
                _fail("run_candidate_base_readback_mismatch")
        for precondition in operation["related_preconditions"]:
            readback = store.read(
                precondition["candidate_ref"], precondition["expected_revision"]
            )
            if readback["sha256"] != precondition["content_hash"]:
                _fail("run_related_candidate_readback_mismatch")


def _run_mapping(
    workflow_ref: str,
    requested_operation_input: Any,
    requested_scope: Any,
    run_readback: dict[str, Any],
    store: context_artifact_store.DirectoryArtifactStore,
) -> tuple[str, dict[str, Any]]:
    request_id = context_artifacts.workflow_operation_id(
        workflow_ref, requested_operation_input, requested_scope
    )
    run_content = run_readback["content"].encode("utf-8", "strict")
    if hashlib.sha256(run_content).hexdigest() != run_readback["sha256"]:
        _fail("run_readback_hash_mismatch")
    run = context_artifacts.parse_canonical_json(run_content)
    context_artifacts.validate_artifact(run, "context-synthesis-run")
    _verify_local_run_references(run, store)
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
    return request_id, {
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
    }


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
    rows = state.setdefault(field, [])
    if not isinstance(rows, list):
        return {"status": "blocked", "reason": f"{field}_state_corrupt"}
    action = update(rows)
    if action == "reused":
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
    )


def record_synthesis_run(request: dict[str, Any]) -> dict[str, Any]:
    store = context_artifact_store.DirectoryArtifactStore(request["artifact_root"])
    readback = store.read(request["run_ref"], request["run_revision"])
    request_id, run_entry = _run_mapping(
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
                "requested_operation_input": copy.deepcopy(
                    request["requested_operation_input"]
                ),
                "requested_scope": copy.deepcopy(request["requested_scope"]),
                "run_refs": [],
            }
            rows.append(group)
        elif (
            _operation_input_identity(group.get("requested_operation_input", {}))
            != _operation_input_identity(request["requested_operation_input"])
            or group.get("requested_scope") != request["requested_scope"]
        ):
            _fail("synthesis_request_id_conflict")
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
            return "reused"
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
    )


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
    for field in ("context_signal_attempts", "context_synthesis_run_refs"):
        existing = state.setdefault(field, [])
        if not isinstance(existing, list):
            _fail(f"{field}_state_corrupt")
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
