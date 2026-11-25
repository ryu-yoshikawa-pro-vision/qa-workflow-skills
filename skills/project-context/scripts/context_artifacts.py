"""Pure contracts for cross-workflow context signal, candidate, and run artifacts.

This module never selects a provider, grants access, or persists an artifact. A
trusted host must supply those capabilities and pass provider readback to the
workflow owner verifier.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any

SCHEMA_VERSION = "1.0"
KINDS = frozenset(
    {"context-signal-batch", "context-rule-candidate", "context-synthesis-run"}
)
MAX_ARTIFACT_BYTES = 16 * 1024 * 1024
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
STATES = frozenset(
    {
        "uninvestigated",
        "investigating",
        "resolved",
        "rejected",
        "deferred",
        "superseded",
        "blocked",
    }
)
RELATIONS = frozenset(
    {"competing_hypothesis", "alternative", "replaced_by", "merged_into", "split_into"}
)
SUCCESSOR_RELATIONS = frozenset({"replaced_by", "merged_into", "split_into"})
EVIDENCE_TYPES = frozenset(
    {
        "spec",
        "decision",
        "approved_asm",
        "unapproved_user_response",
        "impl_observation",
        "exploratory_finding",
    }
)
EVALUATIONS = frozenset({"supports", "counterexample", "indeterminate", "out_of_scope"})
COUNTEREXAMPLE_CLASSES = frozenset(
    {
        "scope_difference",
        "impl_bug_candidate",
        "spec_change",
        "observation_condition",
        "hypothesis_error",
        "unclassified",
    }
)
RUN_STATUSES = frozenset(
    {"in_progress", "completed", "completed_zero_changes", "blocked_incomplete"}
)
ZERO_CHANGE_REASONS = frozenset(
    {
        "no_related_candidates",
        "existing_candidates_sufficient",
        "all_evidence_known",
        "empty_search",
    }
)
_SECRET = re.compile(
    r"(?i)(?:password|passwd|access[_-]?token|client[_-]?secret|api[_-]?key|authorization)\s*[:=]\s*['\"]?(?:bearer\s+)?[A-Za-z0-9_./+=-]{8,}"
)


class ContractError(ValueError):
    """A deterministic artifact contract failed."""


def _fail(code: str) -> None:
    raise ContractError(code)


def _object(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        _fail(f"{name}_must_be_object")
    return value


def _text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        _fail(f"{name}_must_be_nonempty_trimmed_string")
    try:
        value.encode("utf-8", "strict")
    except UnicodeError as exc:
        raise ContractError(f"{name}_must_be_utf8") from exc
    return value


def _choice(value: Any, allowed: frozenset[str], name: str) -> str:
    if not isinstance(value, str) or value not in allowed:
        _fail(f"{name}_invalid")
    return value


def _keys(
    value: Mapping[str, Any], required: set[str], optional: set[str], name: str
) -> None:
    keys = set(value)
    if not required <= keys or keys - required - optional:
        _fail(f"{name}_schema_invalid")


def _digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def canonical_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8", "strict")
    except (TypeError, ValueError, UnicodeError) as exc:
        raise ContractError("canonical_json_invalid") from exc


def parse_canonical_json(raw: bytes | str) -> dict[str, Any]:
    data = raw.encode("utf-8") if isinstance(raw, str) else raw
    if not isinstance(data, bytes) or len(data) > MAX_ARTIFACT_BYTES:
        _fail("artifact_content_too_large_or_invalid")

    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                _fail("duplicate_json_key")
            result[key] = value
        return result

    def constant(_: str) -> Any:
        _fail("nonfinite_json_value")

    try:
        value = json.loads(
            data.decode("utf-8", "strict"),
            object_pairs_hook=pairs,
            parse_constant=constant,
        )
    except ContractError:
        raise
    except (UnicodeError, json.JSONDecodeError, RecursionError, TypeError) as exc:
        raise ContractError("artifact_json_invalid") from exc
    result = _object(value, "artifact")
    if canonical_bytes(result) != data:
        _fail("artifact_json_not_canonical")
    return result


def artifact_ref(kind: str, identity: str) -> str:
    """Return a root-relative ref; root selection is an external host concern."""
    if (
        kind not in KINDS
        or not isinstance(identity, str)
        or not SHA256_RE.fullmatch(identity)
    ):
        _fail("artifact_identity_invalid")
    return f"{kind}/{identity}.json"


def _validate_ref(
    ref: Any, kind: str, identity: str, name: str = "artifact_ref"
) -> str:
    value = _text(ref, name)
    if value != artifact_ref(kind, identity):
        _fail(f"{name}_identity_mismatch")
    return value


def normalize_range(value: Any, name: str = "range") -> dict[str, Any]:
    row = _object(value, name)
    if row == {"kind": "all"}:
        return {"kind": "all"}
    if set(row) != {"kind", "items"}:
        _fail(f"{name}_schema_invalid")
    kind = _text(row.get("kind"), f"{name}.kind")
    items = row.get("items")
    if not isinstance(items, list) or not all(
        isinstance(item, str) and item.strip() == item and item for item in items
    ):
        _fail(f"{name}.items_invalid")
    normalized = sorted(set(items))
    if not normalized:
        _fail(f"{name}.items_empty")
    return {"kind": kind, "items": normalized}


def range_contains(outer: dict[str, Any], inner: dict[str, Any]) -> bool:
    outer = normalize_range(outer, "outer_range")
    inner = normalize_range(inner, "inner_range")
    if outer["kind"] == "all":
        return True
    if inner["kind"] == "all" or outer["kind"] != inner["kind"]:
        return False
    return set(inner["items"]) <= set(outer["items"])


def range_union(ranges: Iterable[dict[str, Any]]) -> dict[str, Any] | None:
    rows = [normalize_range(row) for row in ranges]
    if not rows:
        return None
    if any(row["kind"] == "all" for row in rows):
        return {"kind": "all"}
    kinds = {row["kind"] for row in rows}
    if len(kinds) != 1:
        return None
    return {
        "kind": next(iter(kinds)),
        "items": sorted({item for row in rows for item in row["items"]}),
    }


def batch_union_covers_request(
    batches: Iterable[dict[str, Any]],
    *,
    source_ref: str,
    source_content_hash: str,
    requested_range: dict[str, Any],
    observation_condition: Any,
) -> bool:
    """Return true only when matching, successfully extracted ranges cover a request."""
    rows: list[dict[str, Any]] = []
    refs: dict[str, dict[str, Any]] = {}
    for batch in batches:
        if not isinstance(batch, dict):
            return False
        source = batch.get("source")
        if not isinstance(source, dict):
            return False
        if (
            source.get("artifact_ref") != source_ref
            or source.get("source_content_hash") != source_content_hash
            or source.get("observation_condition") != observation_condition
            or batch.get("scan_completeness") not in {"complete", "partial"}
        ):
            continue
        try:
            normalize_range(source.get("actual_inspected_range"))
            ref = batch.get("artifact_ref")
            if not isinstance(ref, str) or ref in refs:
                return False
            refs[ref] = batch
            rows.append(batch)
        except ContractError:
            return False

    superseded_refs: set[str] = set()
    terminal_corrections: dict[str, list[str]] = {}
    for batch in rows:
        correction = batch.get("correction")
        if correction is None:
            continue
        targets = (
            correction.get("corrected_batch_targets")
            if isinstance(correction, dict)
            else None
        )
        if not isinstance(targets, list):
            return False
        target_refs: list[str] = []
        for target in targets:
            if not isinstance(target, dict) or target.get("artifact_ref") not in refs:
                return False
            referenced = refs[target["artifact_ref"]]
            referenced_source = referenced.get("source", {})
            if (
                referenced.get("batch_identity") != target.get("batch_identity")
                or referenced_source.get("artifact_ref")
                != target.get("source_artifact_ref")
                or referenced_source.get("source_content_hash")
                != target.get("source_content_hash")
                or referenced_source.get("actual_inspected_range")
                != target.get("actual_inspected_range")
                or referenced_source.get("observation_condition")
                != target.get("observation_condition")
            ):
                return False
            target_refs.append(target["artifact_ref"])
        superseded_refs.update(target_refs)
        terminal_corrections.setdefault(
            correction["original_batch_identity"], []
        ).append(batch["artifact_ref"])
    for original, corrections in terminal_corrections.items():
        active = [ref for ref in corrections if ref not in superseded_refs]
        if len(active) != 1:
            return False

    active_ranges: list[dict[str, Any]] = []
    for batch in rows:
        if batch["artifact_ref"] in superseded_refs:
            continue
        try:
            active_ranges.append(
                normalize_range(batch["source"]["actual_inspected_range"])
            )
        except (ContractError, KeyError, TypeError):
            return False
    combined = range_union(active_ranges)
    if combined is None:
        return False
    return range_contains(combined, requested_range)


def batch_identity(
    source_artifact_ref: str,
    source_content_hash: str,
    actual_inspected_range: dict[str, Any],
    observation_condition: Any = None,
) -> str:
    if not SHA256_RE.fullmatch(source_content_hash):
        _fail("source_content_hash_invalid")
    key = {
        "source_artifact_ref": _text(source_artifact_ref, "source_artifact_ref"),
        "source_content_hash": source_content_hash,
        "actual_inspected_range": normalize_range(
            actual_inspected_range, "actual_inspected_range"
        ),
        "observation_condition": observation_condition,
    }
    return _digest(key)


def correction_batch_identity(
    original_batch_identity: str,
    corrected_batch_targets: list[dict[str, Any]],
    corrected_signals: list[dict[str, Any]],
) -> str:
    if not SHA256_RE.fullmatch(original_batch_identity):
        _fail("original_batch_identity_invalid")
    if not isinstance(corrected_batch_targets, list) or not isinstance(
        corrected_signals, list
    ):
        _fail("correction_identity_inputs_invalid")
    if not all(
        isinstance(target, dict) and isinstance(target.get("artifact_ref"), str)
        for target in corrected_batch_targets
    ):
        _fail("correction_identity_targets_invalid")
    target_refs = [target["artifact_ref"] for target in corrected_batch_targets]
    if not target_refs or target_refs != sorted(set(target_refs)):
        _fail("correction_identity_targets_not_canonical")
    return _digest(
        {
            "original_batch_identity": original_batch_identity,
            "corrected_batch_targets": corrected_batch_targets,
            "corrected_signals_hash": _digest(corrected_signals),
        }
    )


def signal_identity(
    source_artifact_ref: str, observation_locator: Any, source_content_hash: str
) -> str:
    if not SHA256_RE.fullmatch(source_content_hash):
        _fail("source_content_hash_invalid")
    return _digest(
        {
            "source_artifact_ref": _text(source_artifact_ref, "source_artifact_ref"),
            "observation_locator": observation_locator,
            "source_content_hash": source_content_hash,
        }
    )


def signal_content_hash(signal: dict[str, Any]) -> str:
    return _digest(
        {
            key: value
            for key, value in signal.items()
            if key not in {"signal_identity", "signal_content_hash"}
        }
    )


def candidate_identity(identity_key: dict[str, Any]) -> str:
    return _digest(_validate_identity_key(identity_key))


def workflow_operation_id(
    workflow_ref: str,
    operation_input: dict[str, Any],
    requested_scope: dict[str, Any],
) -> str:
    row = _object(operation_input, "operation_input")
    if set(row) != {"operation_type", "input_sources", "investigation_conditions"}:
        _fail("operation_input_identity_sources_missing")
    if row["operation_type"] != "synthesize_context":
        _fail("operation_type_invalid")
    sources = row["input_sources"]
    if not isinstance(sources, list):
        _fail("operation_input_sources_invalid")
    normalized_sources: list[dict[str, Any]] = []
    for source in sources:
        source = _object(source, "operation_input_source")
        if set(source) != {
            "artifact_ref",
            "content_hash",
            "effective_authority_fingerprint",
        }:
            _fail("operation_input_source_schema_invalid")
        artifact_ref_value = _text(
            source["artifact_ref"], "operation_input_source.artifact_ref"
        )
        content_hash = source["content_hash"]
        authority = source["effective_authority_fingerprint"]
        if not isinstance(content_hash, str) or not SHA256_RE.fullmatch(content_hash):
            _fail("operation_input_source_hash_invalid")
        if authority is not None and (
            not isinstance(authority, str) or not SHA256_RE.fullmatch(authority)
        ):
            _fail("operation_input_authority_fingerprint_invalid")
        normalized_sources.append(
            {
                "artifact_ref": artifact_ref_value,
                "content_hash": content_hash,
                "effective_authority_fingerprint": authority,
            }
        )
    source_refs = [source["artifact_ref"] for source in normalized_sources]
    if source_refs != sorted(set(source_refs)):
        _fail("operation_input_sources_not_canonical")
    conditions = _object(row["investigation_conditions"], "investigation_conditions")
    requested = _object(requested_scope, "requested_scope")
    if set(requested) != {"scope_refs", "analysis_aspect", "environment_and_versions"}:
        _fail("requested_scope_schema_invalid")
    scope_refs = requested["scope_refs"]
    if (
        not isinstance(scope_refs, list)
        or not scope_refs
        or not all(
            isinstance(item, str) and item.strip() == item and item
            for item in scope_refs
        )
        or scope_refs != sorted(set(scope_refs))
    ):
        _fail("requested_scope_refs_invalid")
    _text(requested["analysis_aspect"], "analysis_aspect")
    if not isinstance(requested["environment_and_versions"], list):
        _fail("environment_and_versions_invalid")
    for environment in requested["environment_and_versions"]:
        _object(environment, "environment_and_version")
    return _digest(
        {
            "workflow_ref": _text(workflow_ref, "workflow_ref"),
            "operation_input": {
                "operation_type": row["operation_type"],
                "input_sources": normalized_sources,
                "investigation_conditions": conditions,
            },
            "requested_scope": requested,
        }
    )


def run_identity(operation_id: str) -> str:
    if not SHA256_RE.fullmatch(operation_id):
        _fail("workflow_operation_id_invalid")
    return operation_id


def semantic_handoff_key(
    target_owner: str, target_scope: str, normalized_intent: Any
) -> str:
    return _digest(
        {
            "target_owner": _text(target_owner, "target_owner"),
            "target_scope": _text(target_scope, "target_scope"),
            "normalized_intent": normalized_intent,
        }
    )


def _validate_identity_key(value: Any) -> dict[str, Any]:
    row = _object(value, "identity_key")
    required = {
        "domain",
        "operation_axis",
        "rule_kind",
        "target_scope_kind",
        "governing_conditions",
        "assertion_polarity",
        "normalized_assertion",
    }
    if set(row) != required:
        _fail("identity_key_schema_invalid")
    for field in required - {"governing_conditions"}:
        _text(row[field], f"identity_key.{field}")
    _object(row["governing_conditions"], "governing_conditions")
    canonical_bytes(row["governing_conditions"])
    return row


def _no_secret(value: Any, path: str = "artifact") -> None:
    if isinstance(value, str):
        if _SECRET.search(value):
            _fail(f"secret_like_value_rejected:{path}")
    elif isinstance(value, dict):
        for key, child in value.items():
            _no_secret(key, path)
            _no_secret(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _no_secret(child, f"{path}[{index}]")


def validate_signal(signal: Any, source_ref: str, source_content_hash: str) -> None:
    row = _object(signal, "signal")
    required = {
        "signal_identity",
        "signal_content_hash",
        "observation_locator",
        "evidence_type",
        "fact_summary",
        "independence_group",
        "cross_cutting_attributes",
        "environment_and_versions",
    }
    _keys(row, required, {"unapproved_response_meta"}, "signal")
    _text(row["fact_summary"], "fact_summary")
    _text(row["independence_group"], "independence_group")
    if (
        not isinstance(row["evidence_type"], str)
        or row["evidence_type"] not in EVIDENCE_TYPES
    ):
        _fail("evidence_type_invalid")
    if row["signal_identity"] != signal_identity(
        source_ref, row["observation_locator"], source_content_hash
    ):
        _fail("signal_identity_mismatch")
    if row["signal_content_hash"] != signal_content_hash(row):
        _fail("signal_content_hash_mismatch")
    _object(row["cross_cutting_attributes"], "cross_cutting_attributes")
    if not isinstance(row["environment_and_versions"], list) or not all(
        isinstance(item, dict) for item in row["environment_and_versions"]
    ):
        _fail("environment_and_versions_invalid")
    response = row.get("unapproved_response_meta")
    if row["evidence_type"] == "unapproved_user_response":
        response = _object(response, "unapproved_response_meta")
        if set(response) != {
            "responder_role",
            "approval_status",
            "question_ref",
            "question_revision",
            "scope_ref",
        }:
            _fail("unapproved_response_schema_invalid")
        if response.get("approval_status") != "unapproved":
            _fail("unapproved_response_status_invalid")
        for field in (
            "responder_role",
            "question_ref",
            "question_revision",
            "scope_ref",
        ):
            _text(response.get(field), f"unapproved_response_meta.{field}")
    elif response is not None:
        _fail("unapproved_response_meta_unexpected")


def _validate_batch(batch: dict[str, Any]) -> None:
    required = {
        "schema_version",
        "artifact_ref",
        "batch_identity",
        "workflow_operation_id",
        "source",
        "scan_completeness",
        "candidate_check",
        "signals",
    }
    _keys(batch, required, {"correction"}, "context_signal_batch")
    if batch["schema_version"] != SCHEMA_VERSION:
        _fail("schema_version_unsupported")
    identity = _text(batch["batch_identity"], "batch_identity")
    if not SHA256_RE.fullmatch(identity):
        _fail("batch_identity_invalid")
    _validate_ref(batch["artifact_ref"], "context-signal-batch", identity)
    operation_id = _text(batch["workflow_operation_id"], "workflow_operation_id")
    if not SHA256_RE.fullmatch(operation_id):
        _fail("workflow_operation_id_invalid")
    source = _object(batch["source"], "source")
    if set(source) != {
        "artifact_ref",
        "source_revision",
        "source_content_hash",
        "requested_range",
        "actual_inspected_range",
        "observation_condition",
    }:
        _fail("batch_source_schema_invalid")
    source_ref = _text(source["artifact_ref"], "source.artifact_ref")
    _text(source["source_revision"], "source.source_revision")
    source_hash = _text(source["source_content_hash"], "source.source_content_hash")
    if not SHA256_RE.fullmatch(source_hash):
        _fail("source_content_hash_invalid")
    actual = normalize_range(source["actual_inspected_range"], "actual_inspected_range")
    requested = normalize_range(source["requested_range"], "requested_range")
    if (
        actual != source["actual_inspected_range"]
        or requested != source["requested_range"]
    ):
        _fail("batch_range_not_canonical")
    if batch["scan_completeness"] not in {"complete", "partial"}:
        _fail("scan_completeness_invalid")
    expected_identity = batch_identity(
        source_ref, source_hash, actual, source["observation_condition"]
    )
    correction = batch.get("correction")
    if correction is None:
        if identity != expected_identity:
            _fail("batch_identity_mismatch")
    else:
        correction = _object(correction, "correction")
        if set(correction) != {
            "original_batch_identity",
            "corrected_batch_targets",
            "reason",
            "source_evidence_refs",
        }:
            _fail("batch_correction_schema_invalid")
        original = _text(
            correction["original_batch_identity"], "correction.original_batch_identity"
        )
        if not SHA256_RE.fullmatch(original) or not isinstance(
            correction["corrected_batch_targets"], list
        ):
            _fail("batch_correction_target_invalid")
        target_fields = {
            "batch_identity",
            "artifact_ref",
            "revision",
            "content_hash",
            "source_artifact_ref",
            "source_content_hash",
            "actual_inspected_range",
            "observation_condition",
        }
        targets = correction["corrected_batch_targets"]
        for target in targets:
            target = _object(target, "corrected_batch_target")
            if set(target) != target_fields:
                _fail("batch_correction_target_schema_invalid")
            target_identity = _text(
                target["batch_identity"], "corrected_batch_identity"
            )
            if not SHA256_RE.fullmatch(target_identity):
                _fail("batch_correction_target_identity_invalid")
            _validate_ref(
                target["artifact_ref"],
                "context-signal-batch",
                target_identity,
                "corrected_batch_ref",
            )
            _text(target["revision"], "corrected_batch_revision")
            if not SHA256_RE.fullmatch(
                _text(target["content_hash"], "corrected_batch_content_hash")
            ):
                _fail("batch_correction_target_hash_invalid")
            if (
                target["source_artifact_ref"] != source_ref
                or target["source_content_hash"] != source_hash
            ):
                _fail("batch_correction_source_mismatch")
            if normalize_range(target["actual_inspected_range"]) != actual:
                _fail("batch_correction_range_mismatch")
            if target["observation_condition"] != source["observation_condition"]:
                _fail("batch_correction_condition_mismatch")
            for value in (
                target["batch_identity"],
                target["artifact_ref"],
                target["revision"],
                target["content_hash"],
            ):
                _text(value, "corrected_batch_target")
        target_keys = [target["artifact_ref"] for target in targets]
        if not targets or target_keys != sorted(set(target_keys)):
            _fail("batch_correction_targets_not_canonical")
        if original != expected_identity or not any(
            target["batch_identity"] == original for target in targets
        ):
            _fail("batch_correction_original_mismatch")
        _text(correction["reason"], "correction.reason")
        evidence_refs = correction["source_evidence_refs"]
        if not isinstance(evidence_refs, list) or not all(
            isinstance(ref, str) for ref in evidence_refs
        ):
            _fail("batch_correction_evidence_invalid")
        if not evidence_refs or evidence_refs != sorted(set(evidence_refs)):
            _fail("batch_correction_evidence_not_canonical")
        for ref in evidence_refs:
            _text(ref, "correction.source_evidence_ref")
        expected_identity = correction_batch_identity(
            original, targets, batch["signals"]
        )
        if expected_identity != identity:
            _fail("batch_correction_identity_mismatch")
    check = _object(batch["candidate_check"], "candidate_check")
    if set(check) != {"status", "triggered_candidate_identities"}:
        _fail("candidate_check_schema_invalid")
    if not isinstance(check["status"], str) or check["status"] not in {
        "checked_with_triggers",
        "checked_no_conflict",
        "not_checked",
    }:
        _fail("candidate_check_status_invalid")
    if not isinstance(check["triggered_candidate_identities"], list):
        _fail("candidate_check_candidates_invalid")
    candidate_values = check["triggered_candidate_identities"]
    if not all(
        isinstance(item, str) and SHA256_RE.fullmatch(item) for item in candidate_values
    ):
        _fail("candidate_check_candidate_identity_invalid")
    candidate_ids = sorted(set(candidate_values))
    if candidate_ids != check["triggered_candidate_identities"]:
        _fail("candidate_check_candidates_not_canonical")
    if check["status"] == "checked_with_triggers" and not candidate_ids:
        _fail("candidate_check_trigger_missing")
    if check["status"] == "checked_no_conflict" and candidate_ids:
        _fail("candidate_check_no_conflict_has_candidates")
    if not isinstance(batch["signals"], list):
        _fail("signals_must_be_array")
    signal_ids: list[str] = []
    for signal in batch["signals"]:
        validate_signal(signal, source_ref, source_hash)
        signal_ids.append(signal["signal_identity"])
    if len(signal_ids) != len(set(signal_ids)):
        _fail("duplicate_signal_identity")
    _no_secret(batch)
    if batch["scan_completeness"] == "complete" and not range_contains(
        actual, requested
    ):
        _fail("complete_batch_does_not_cover_requested_range")


def _validate_evidence_link(link: Any) -> None:
    row = _object(link, "evidence_link")
    required = {
        "link_kind",
        "signal_batch_ref",
        "signal_identity",
        "signal_content_hash",
        "direct_source_ref",
        "direct_source_revision",
        "source_content_hash",
        "evaluation",
        "counterexample_classification",
    }
    if set(row) != required:
        _fail("evidence_link_schema_invalid")
    _choice(row["evaluation"], EVALUATIONS, "evidence_evaluation")
    classification = row["counterexample_classification"]
    if classification is not None:
        _choice(classification, COUNTEREXAMPLE_CLASSES, "counterexample_classification")
    if row["evaluation"] == "counterexample" and classification is None:
        _fail("counterexample_classification_required")
    if row["evaluation"] != "counterexample" and classification is not None:
        _fail("counterexample_classification_unexpected")
    if row["link_kind"] == "signal_ref":
        _text(row["signal_batch_ref"], "signal_batch_ref")
        if not SHA256_RE.fullmatch(_text(row["signal_identity"], "signal_identity")):
            _fail("signal_identity_invalid")
        if not SHA256_RE.fullmatch(
            _text(row["signal_content_hash"], "signal_content_hash")
        ):
            _fail("signal_content_hash_invalid")
        if (
            row["direct_source_ref"] is not None
            or row["direct_source_revision"] is not None
        ):
            _fail("signal_evidence_has_direct_source")
    elif row["link_kind"] == "direct_source_ref":
        _text(row["direct_source_ref"], "direct_source_ref")
        _text(row["direct_source_revision"], "direct_source_revision")
        if (
            row["signal_batch_ref"] is not None
            or row["signal_identity"] is not None
            or row["signal_content_hash"] is not None
        ):
            _fail("direct_evidence_has_signal_ref")
    else:
        _fail("evidence_link_kind_invalid")
    if not SHA256_RE.fullmatch(
        _text(row["source_content_hash"], "source_content_hash")
    ):
        _fail("source_content_hash_invalid")


def _validate_candidate(candidate: dict[str, Any]) -> None:
    required = {
        "schema_version",
        "artifact_ref",
        "candidate_identity",
        "identity_key",
        "rule_statement",
        "applicability",
        "related_candidate_refs",
        "evidence_links",
        "unobserved_ranges",
        "currentness_dependencies",
        "evaluation_status",
        "resolution_state",
        "resolution_links",
        "implementation_conformance_refs",
        "question_refs",
        "handoff_records",
        "rejection_or_deferral_detail",
        "investigation_history",
    }
    _keys(candidate, required, {"search_tags"}, "context_rule_candidate")
    if candidate["schema_version"] != SCHEMA_VERSION:
        _fail("schema_version_unsupported")
    identity_key = _validate_identity_key(candidate["identity_key"])
    identity = candidate_identity(identity_key)
    if candidate["candidate_identity"] != identity:
        _fail("candidate_identity_mismatch")
    _validate_ref(candidate["artifact_ref"], "context-rule-candidate", identity)
    _text(candidate["rule_statement"], "rule_statement")
    if "search_tags" in candidate:
        tags = candidate["search_tags"]
        if (
            not isinstance(tags, list)
            or not all(
                isinstance(tag, str) and tag.strip() == tag and tag for tag in tags
            )
            or tags != sorted(set(tags))
        ):
            _fail("search_tags_not_canonical")
    applicability = _object(candidate["applicability"], "applicability")
    if set(applicability) != {
        "scope_summary",
        "cross_cutting_attributes",
        "invalidation_conditions",
    }:
        _fail("applicability_schema_invalid")
    _text(applicability["scope_summary"], "scope_summary")
    _object(applicability["cross_cutting_attributes"], "cross_cutting_attributes")
    if not isinstance(applicability["invalidation_conditions"], list):
        _fail("invalidation_conditions_invalid")
    for key, value in identity_key["governing_conditions"].items():
        if (
            key in applicability["cross_cutting_attributes"]
            and applicability["cross_cutting_attributes"][key] != value
        ):
            _fail("governing_conditions_applicability_mismatch")
    related = candidate["related_candidate_refs"]
    if not isinstance(related, list):
        _fail("related_candidate_refs_invalid")
    for relation in related:
        relation = _object(relation, "related_candidate_ref")
        if set(relation) != {"candidate_identity", "relation"}:
            _fail("related_candidate_ref_schema_invalid")
        ref_id = _text(relation["candidate_identity"], "related_candidate_identity")
        if (
            not SHA256_RE.fullmatch(ref_id)
            or ref_id == identity
            or not isinstance(relation["relation"], str)
            or relation["relation"] not in RELATIONS
        ):
            _fail("related_candidate_ref_invalid")
    related_keys = [(row["candidate_identity"], row["relation"]) for row in related]
    if related_keys != sorted(set(related_keys)):
        _fail("related_candidate_refs_not_canonical")
    if not isinstance(candidate["evidence_links"], list) or not isinstance(
        candidate["unobserved_ranges"], list
    ):
        _fail("candidate_evidence_or_unobserved_invalid")
    for link in candidate["evidence_links"]:
        _validate_evidence_link(link)
    for item in candidate["unobserved_ranges"]:
        _text(item, "unobserved_range")
    dependencies = candidate["currentness_dependencies"]
    if not isinstance(dependencies, list):
        _fail("currentness_dependencies_invalid")
    for dependency in dependencies:
        dep = _object(dependency, "currentness_dependency")
        if set(dep) != {
            "target_ref",
            "dependency_content_hash",
            "effective_authority_fingerprint",
            "source_revision",
            "dependency_freshness",
        }:
            _fail("currentness_dependency_schema_invalid")
        _text(dep["target_ref"], "dependency.target_ref")
        _text(dep["source_revision"], "dependency.source_revision")
        if not SHA256_RE.fullmatch(
            _text(dep["dependency_content_hash"], "dependency_content_hash")
        ):
            _fail("dependency_content_hash_invalid")
        fingerprint = dep["effective_authority_fingerprint"]
        if fingerprint is not None and (
            not isinstance(fingerprint, str) or not SHA256_RE.fullmatch(fingerprint)
        ):
            _fail("authority_fingerprint_invalid")
        _choice(
            dep["dependency_freshness"],
            frozenset({"current", "changed", "unverifiable", "deleted"}),
            "dependency_freshness",
        )
    evaluation = _object(candidate["evaluation_status"], "evaluation_status")
    if set(evaluation) != {
        "scan_completeness",
        "revalidation_required",
        "revalidation_reasons",
        "last_synthesis_run_ref",
    }:
        _fail("evaluation_status_schema_invalid")
    if (
        not isinstance(evaluation["scan_completeness"], str)
        or evaluation["scan_completeness"] not in {"complete", "partial", "failed"}
        or not isinstance(evaluation["revalidation_required"], bool)
        or not isinstance(evaluation["revalidation_reasons"], list)
    ):
        _fail("evaluation_status_invalid")
    if evaluation["last_synthesis_run_ref"] is not None:
        _text(evaluation["last_synthesis_run_ref"], "last_synthesis_run_ref")
    for reason in evaluation["revalidation_reasons"]:
        _text(reason, "revalidation_reason")
    _choice(candidate["resolution_state"], STATES, "resolution_state")
    for collection_key in (
        "resolution_links",
        "implementation_conformance_refs",
        "question_refs",
        "handoff_records",
        "investigation_history",
    ):
        if not isinstance(candidate[collection_key], list):
            _fail(f"{collection_key}_invalid")
    for item in candidate["resolution_links"]:
        link = _object(item, "resolution_link")
        if set(link) != {
            "owner",
            "artifact_kind",
            "artifact_ref",
            "artifact_revision",
            "artifact_content_hash",
            "coverage",
        }:
            _fail("resolution_link_schema_invalid")
        for key in ("owner", "artifact_kind", "artifact_ref", "artifact_revision"):
            _text(link[key], f"resolution_link.{key}")
        if (
            not SHA256_RE.fullmatch(
                _text(link["artifact_content_hash"], "resolution_link_hash")
            )
            or not isinstance(link["coverage"], str)
            or link["coverage"] not in {"full", "partial"}
        ):
            _fail("resolution_link_invalid")
    for item in candidate["implementation_conformance_refs"]:
        conf = _object(item, "implementation_conformance_ref")
        if set(conf) != {
            "scope_ref",
            "environment",
            "build_ref",
            "status",
            "ref",
            "revision",
            "verified",
        }:
            _fail("implementation_conformance_schema_invalid")
        for key in ("scope_ref", "environment", "build_ref", "ref", "revision"):
            _text(conf[key], f"implementation_conformance.{key}")
        if (
            not isinstance(conf["status"], str)
            or conf["status"] not in {"conforms", "confirmed_mismatch", "unverified"}
            or not isinstance(conf["verified"], bool)
        ):
            _fail("implementation_conformance_invalid")
        if conf["verified"] and conf["status"] == "unverified":
            _fail("unverified_conformance_cannot_be_verified")
    for item in candidate["question_refs"]:
        question = _object(item, "question_ref")
        if set(question) != {
            "unknown_ref",
            "question_id",
            "question_artifact_ref",
            "question_revision",
        }:
            _fail("question_ref_schema_invalid")
        if question["unknown_ref"] is not None:
            _text(question["unknown_ref"], "unknown_ref")
        for key in ("question_id", "question_artifact_ref", "question_revision"):
            _text(question[key], f"question.{key}")
    for item in candidate["handoff_records"]:
        handoff = _object(item, "handoff_record")
        if set(handoff) != {
            "semantic_handoff_key",
            "workflow_operation_id",
            "target_owner",
            "target_scope",
            "normalized_intent",
            "reason",
            "status",
            "confirmed_target_ref",
        }:
            _fail("handoff_record_schema_invalid")
        for key in ("workflow_operation_id", "target_owner", "target_scope", "reason"):
            _text(handoff[key], f"handoff.{key}")
        if not SHA256_RE.fullmatch(handoff["workflow_operation_id"]):
            _fail("handoff_operation_id_invalid")
        if handoff["semantic_handoff_key"] != semantic_handoff_key(
            handoff["target_owner"],
            handoff["target_scope"],
            handoff["normalized_intent"],
        ):
            _fail("semantic_handoff_key_mismatch")
        _choice(
            handoff["status"],
            frozenset(
                {"pending", "confirmed_by_readback", "returned", "blocked_unverifiable"}
            ),
            "handoff_status",
        )
        confirmed = _object(handoff["confirmed_target_ref"], "confirmed_target_ref")
        if set(confirmed) != {
            "artifact_ref",
            "artifact_revision",
            "artifact_content_hash",
        }:
            _fail("confirmed_target_ref_schema_invalid")
        if handoff["status"] == "confirmed_by_readback":
            for key in ("artifact_ref", "artifact_revision"):
                _text(confirmed[key], f"confirmed_target_ref.{key}")
            if not SHA256_RE.fullmatch(
                _text(
                    confirmed["artifact_content_hash"], "confirmed_target_content_hash"
                )
            ):
                _fail("confirmed_target_content_hash_invalid")
        elif any(confirmed[key] is not None for key in confirmed):
            _fail("unconfirmed_handoff_has_readback")
    detail = candidate["rejection_or_deferral_detail"]
    if detail is not None:
        detail = _object(detail, "rejection_or_deferral_detail")
        if set(detail) != {
            "reason",
            "authority_basis_ref",
            "negated_conditions",
            "non_negated_conditions",
            "scope_at_decision",
        }:
            _fail("rejection_or_deferral_detail_schema_invalid")
        for key in ("reason", "authority_basis_ref", "scope_at_decision"):
            _text(detail[key], f"rejection_or_deferral_detail.{key}")
        for key in ("negated_conditions", "non_negated_conditions"):
            if not isinstance(detail[key], list) or not all(
                isinstance(item, str) and item.strip() == item and item
                for item in detail[key]
            ):
                _fail("rejection_or_deferral_conditions_invalid")
    for item in candidate["investigation_history"]:
        history = _object(item, "investigation_history")
        if set(history) != {
            "target_skill",
            "source_ref",
            "source_content_hash",
            "condition_hash",
            "outcome",
            "resume_condition",
        }:
            _fail("investigation_history_schema_invalid")
        for key in ("target_skill", "source_ref", "condition_hash", "resume_condition"):
            _text(history[key], f"investigation_history.{key}")
        for key in ("source_content_hash",):
            if not SHA256_RE.fullmatch(history[key]):
                _fail("investigation_history_hash_invalid")
        if history["outcome"] not in {
            "resolved",
            "no_new_info",
            "blocked_transient",
            "blocked_permission",
            "blocked_env",
            "blocked_safety",
        }:
            _fail("investigation_history_outcome_invalid")
    _no_secret(candidate)
    if candidate["resolution_state"] == "rejected":
        if detail is None or not detail["authority_basis_ref"]:
            _fail("rejected_candidate_requires_authority_basis")
    if candidate["resolution_state"] == "deferred" and detail is None:
        _fail("deferred_candidate_requires_detail")
    if (
        candidate["resolution_state"] == "resolved"
        and not candidate["resolution_links"]
    ):
        _fail("resolved_candidate_requires_owner_resolution")
    if candidate["resolution_state"] == "superseded" and not any(
        item["relation"] in SUCCESSOR_RELATIONS for item in related
    ):
        _fail("superseded_candidate_requires_successor")


def _validate_kind_ref(ref: Any, kind: str, name: str) -> str:
    value = _text(ref, name)
    prefix = f"{kind}/"
    if not value.startswith(prefix) or not value.endswith(".json"):
        _fail(f"{name}_invalid")
    identity = value[len(prefix) : -5]
    if not SHA256_RE.fullmatch(identity) or value != artifact_ref(kind, identity):
        _fail(f"{name}_invalid")
    return value


def validate_candidate_relations(candidates: Iterable[dict[str, Any]]) -> None:
    items = list(candidates)
    rows = {
        _text(row.get("candidate_identity"), "candidate_identity"): row for row in items
    }
    if len(rows) != len(items):
        _fail("duplicate_candidate_identity")
    graph: dict[str, set[str]] = {identity: set() for identity in rows}
    for identity, row in rows.items():
        for relation in row.get("related_candidate_refs", []):
            target = relation["candidate_identity"]
            if target in rows and relation["relation"] in SUCCESSOR_RELATIONS:
                graph[identity].add(target)
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> None:
        if node in visiting:
            _fail("successor_relation_cycle")
        if node in visited:
            return
        visiting.add(node)
        for child in graph[node]:
            visit(child)
        visiting.remove(node)
        visited.add(node)

    for node in graph:
        visit(node)


def _validate_run(run: dict[str, Any]) -> None:
    required = {
        "schema_version",
        "artifact_ref",
        "run_identity",
        "workflow_ref",
        "workflow_operation_id",
        "operation_input",
        "requested_scope",
        "inspected_scope",
        "scan_completeness",
        "snapshot",
        "triage_plan",
        "result_summary",
    }
    _keys(run, required, set(), "context_synthesis_run")
    if run["schema_version"] != SCHEMA_VERSION:
        _fail("schema_version_unsupported")
    workflow_ref = _text(run["workflow_ref"], "workflow_ref")
    requested = _object(run["requested_scope"], "requested_scope")
    if set(requested) != {"scope_refs", "analysis_aspect", "environment_and_versions"}:
        _fail("requested_scope_schema_invalid")
    if not isinstance(requested["scope_refs"], list) or not isinstance(
        requested["environment_and_versions"], list
    ):
        _fail("requested_scope_invalid")
    for scope_ref in requested["scope_refs"]:
        _text(scope_ref, "requested_scope.scope_ref")
    _text(requested["analysis_aspect"], "analysis_aspect")
    op_id = workflow_operation_id(workflow_ref, run["operation_input"], requested)
    if run["workflow_operation_id"] != op_id or run["run_identity"] != run_identity(
        op_id
    ):
        _fail("run_identity_mismatch")
    _validate_ref(run["artifact_ref"], "context-synthesis-run", run["run_identity"])
    _text(run["inspected_scope"], "inspected_scope")
    _choice(
        run["scan_completeness"],
        frozenset({"complete", "partial", "failed"}),
        "scan_completeness",
    )
    snapshot = _object(run["snapshot"], "snapshot")
    if set(snapshot) != {
        "snapshot_hash",
        "search_roots_and_scopes",
        "search_criteria",
        "referenced_sources",
        "unverifiable_sources",
        "excluded_scope_notes",
    }:
        _fail("snapshot_schema_invalid")
    snapshot_value = {
        key: value for key, value in snapshot.items() if key != "snapshot_hash"
    }
    if snapshot["snapshot_hash"] != _digest(snapshot_value):
        _fail("snapshot_hash_mismatch")
    if (
        not isinstance(snapshot["search_roots_and_scopes"], list)
        or not all(
            isinstance(item, str) and item.strip() == item and item
            for item in snapshot["search_roots_and_scopes"]
        )
        or not isinstance(snapshot["referenced_sources"], list)
        or not isinstance(snapshot["unverifiable_sources"], list)
        or not all(
            isinstance(item, str) and item.strip() == item and item
            for item in snapshot["unverifiable_sources"]
        )
    ):
        _fail("snapshot_collections_invalid")
    _text(snapshot["search_criteria"], "search_criteria")
    _text(snapshot["excluded_scope_notes"], "excluded_scope_notes")
    for source in snapshot["referenced_sources"]:
        source = _object(source, "referenced_source")
        if set(source) != {
            "source_kind",
            "artifact_ref",
            "source_revision",
            "content_hash",
            "effective_authority_fingerprint",
        }:
            _fail("referenced_source_schema_invalid")
        if source["source_kind"] not in {
            "signal_batch",
            "candidate",
            "spec",
            "decision",
            "asm",
            "question_answer",
            "knowledge",
            "inspection_or_finding",
            "authority_resolution",
        }:
            _fail("referenced_source_kind_invalid")
        for key in ("artifact_ref", "source_revision"):
            _text(source[key], f"referenced_source.{key}")
        if not SHA256_RE.fullmatch(source["content_hash"]):
            _fail("referenced_source_hash_invalid")
        auth = source["effective_authority_fingerprint"]
        if auth is not None and not SHA256_RE.fullmatch(auth):
            _fail("effective_authority_fingerprint_invalid")
    plan = _object(run["triage_plan"], "triage_plan")
    if set(plan) != {"target_batch_refs", "planned_candidate_ops"}:
        _fail("triage_plan_schema_invalid")
    if not isinstance(plan["target_batch_refs"], list) or not isinstance(
        plan["planned_candidate_ops"], list
    ):
        _fail("triage_plan_collections_invalid")
    for ref in plan["target_batch_refs"]:
        _validate_kind_ref(ref, "context-signal-batch", "target_batch_ref")
    if plan["target_batch_refs"] != sorted(set(plan["target_batch_refs"])):
        _fail("target_batch_refs_not_canonical")
    operation_identities: list[str] = []
    for operation in plan["planned_candidate_ops"]:
        operation = _object(operation, "planned_candidate_op")
        fields = {
            "candidate_identity",
            "candidate_ref",
            "action",
            "base_content_hash",
            "expected_revision",
            "related_preconditions",
            "operation_id",
            "planned_content_hash",
            "planned_payload",
            "write_request_meta",
            "confirmed_result",
        }
        if set(operation) != fields:
            _fail("planned_candidate_op_schema_invalid")
        identity = _text(operation["candidate_identity"], "planned_candidate_identity")
        if (
            not SHA256_RE.fullmatch(identity)
            or not isinstance(operation["action"], str)
            or operation["action"]
            not in {"create", "update", "merge_into", "split_into", "reuse"}
        ):
            _fail("planned_candidate_op_identity_or_action_invalid")
        _validate_ref(
            operation["candidate_ref"],
            "context-rule-candidate",
            identity,
            "candidate_ref",
        )
        operation_identities.append(identity)
        for key in ("base_content_hash", "planned_content_hash"):
            if operation[key] is not None and (
                not isinstance(operation[key], str)
                or not SHA256_RE.fullmatch(operation[key])
            ):
                _fail(f"{key}_invalid")
        if operation["expected_revision"] is not None:
            _text(operation["expected_revision"], "expected_revision")
        if operation["action"] == "reuse":
            if (
                operation["planned_payload"] is not None
                or operation["base_content_hash"] is None
            ):
                _fail("reuse_plan_invalid")
            if operation["planned_content_hash"] != operation["base_content_hash"]:
                _fail("reuse_plan_hash_mismatch")
        else:
            payload = _object(operation["planned_payload"], "planned_payload")
            _validate_candidate(payload)
            if (
                payload.get("candidate_identity") != identity
                or payload.get("artifact_ref") != operation["candidate_ref"]
                or operation["planned_content_hash"]
                != hashlib.sha256(canonical_bytes(payload)).hexdigest()
            ):
                _fail("planned_payload_hash_or_identity_mismatch")
        _text(operation["operation_id"], "provider_operation_id")
        meta = _object(operation["write_request_meta"], "write_request_meta")
        if set(meta) != {
            "source_ref",
            "source_revision",
            "approval_ref",
            "approval_revision",
            "change_reason",
        }:
            _fail("write_request_meta_schema_invalid")
        for key, value in meta.items():
            _text(value, f"write_request_meta.{key}")
        if not isinstance(operation["related_preconditions"], list):
            _fail("related_preconditions_invalid")
        precondition_refs: list[str] = []
        for precondition in operation["related_preconditions"]:
            precondition = _object(precondition, "related_precondition")
            if set(precondition) != {
                "candidate_ref",
                "expected_revision",
                "content_hash",
            }:
                _fail("related_precondition_schema_invalid")
            ref = _validate_kind_ref(
                precondition["candidate_ref"],
                "context-rule-candidate",
                "related_precondition_ref",
            )
            precondition_refs.append(ref)
            _text(
                precondition["expected_revision"],
                "related_precondition.expected_revision",
            )
            if not isinstance(
                precondition["content_hash"], str
            ) or not SHA256_RE.fullmatch(precondition["content_hash"]):
                _fail("related_precondition_hash_invalid")
        if precondition_refs != sorted(set(precondition_refs)):
            _fail("related_preconditions_not_canonical")
        result = _object(operation["confirmed_result"], "confirmed_result")
        if set(result) != {"artifact_ref", "storage_revision", "content_hash"}:
            _fail("confirmed_result_schema_invalid")
        if any(result[key] is not None for key in result) and not all(
            isinstance(result[key], str) and result[key].strip() for key in result
        ):
            _fail("confirmed_result_incomplete")
        if result["artifact_ref"] is not None and (
            result["artifact_ref"] != operation["candidate_ref"]
            or result["content_hash"] != operation["planned_content_hash"]
        ):
            _fail("confirmed_result_plan_mismatch")
    if len(operation_identities) != len(set(operation_identities)):
        _fail("duplicate_planned_candidate_identity")
    summary = _object(run["result_summary"], "result_summary")
    if set(summary) != {"status", "zero_change_reason", "unresolved_and_handoff_refs"}:
        _fail("result_summary_schema_invalid")
    if (
        not isinstance(summary["status"], str)
        or summary["status"] not in RUN_STATUSES
        or not isinstance(summary["unresolved_and_handoff_refs"], list)
    ):
        _fail("result_summary_invalid")
    if not all(
        isinstance(item, str) and item.strip() == item and item
        for item in summary["unresolved_and_handoff_refs"]
    ):
        _fail("unresolved_and_handoff_refs_invalid")
    if summary["status"] == "completed_zero_changes":
        if (
            run["scan_completeness"] != "complete"
            or summary["zero_change_reason"] not in ZERO_CHANGE_REASONS
            or any(op["action"] != "reuse" for op in plan["planned_candidate_ops"])
        ):
            _fail("zero_change_reason_invalid")
    elif summary["zero_change_reason"] is not None:
        _fail("zero_change_reason_unexpected")
    if summary["status"] == "completed" and run["scan_completeness"] != "complete":
        _fail("incomplete_scan_cannot_complete")
    if summary["status"] in {"completed", "completed_zero_changes"}:
        if any(
            not all(
                operation["confirmed_result"].get(key)
                for key in ("artifact_ref", "storage_revision", "content_hash")
            )
            for operation in plan["planned_candidate_ops"]
        ):
            _fail("completed_run_has_unconfirmed_candidate_op")
        if any(
            operation["confirmed_result"].get("content_hash")
            != operation["planned_content_hash"]
            for operation in plan["planned_candidate_ops"]
        ):
            _fail("completed_run_candidate_hash_mismatch")
        for operation in plan["planned_candidate_ops"]:
            payload = operation["planned_payload"]
            if isinstance(payload, dict) and any(
                handoff["status"] in {"pending", "blocked_unverifiable"}
                for handoff in payload["handoff_records"]
            ):
                _fail("completed_run_has_unresolved_required_handoff")
    if summary["status"] == "completed" and not plan["planned_candidate_ops"]:
        _fail("zero_candidate_run_requires_zero_change_status")
    if summary["status"] == "in_progress" and run["scan_completeness"] == "failed":
        _fail("failed_scan_cannot_be_in_progress")
    _no_secret(run)


def validate_artifact(artifact: Any, kind: str) -> dict[str, Any]:
    row = _object(artifact, "artifact")
    if kind not in KINDS:
        _fail("artifact_kind_invalid")
    if kind == "context-signal-batch":
        _validate_batch(row)
    elif kind == "context-rule-candidate":
        _validate_candidate(row)
    else:
        _validate_run(row)
    return row


def snapshot_hash(snapshot: dict[str, Any]) -> str:
    row = _object(snapshot, "snapshot")
    return _digest({key: value for key, value in row.items() if key != "snapshot_hash"})


def impact(
    current_sources: Iterable[dict[str, Any]], saved_sources: Iterable[dict[str, Any]]
) -> dict[str, Any]:
    """Compare current source projections with the source set used by a run."""

    def key(row: dict[str, Any]) -> tuple[Any, Any]:
        return row.get("source_kind"), row.get("artifact_ref")

    current = {key(row): row for row in current_sources}
    saved = {key(row): row for row in saved_sources}
    changed: list[str] = []
    unverifiable: list[str] = []
    added: list[str] = []
    removed: list[str] = []
    for identity, row in saved.items():
        now = current.get(identity)
        label = str(identity[1])
        if now is None:
            removed.append(label)
        elif now.get("content_hash") != row.get("content_hash") or now.get(
            "effective_authority_fingerprint"
        ) != row.get("effective_authority_fingerprint"):
            changed.append(label)
        elif now.get("source_revision") is None:
            unverifiable.append(label)
    for identity in current.keys() - saved.keys():
        added.append(str(identity[1]))
    return {
        "status": "changed"
        if changed or added or removed
        else "unverifiable"
        if unverifiable
        else "current",
        "changed_refs": sorted(set(changed + added + removed)),
        "unverifiable_refs": sorted(set(unverifiable)),
    }


def batch_covers_request(
    batch: dict[str, Any],
    *,
    source_ref: str,
    source_content_hash: str,
    requested_range: dict[str, Any],
    observation_condition: Any,
) -> bool:
    source = batch.get("source", {})
    return (
        source.get("artifact_ref") == source_ref
        and source.get("source_content_hash") == source_content_hash
        and source.get("observation_condition") == observation_condition
        and range_contains(source.get("actual_inspected_range"), requested_range)
        and batch.get("scan_completeness") in {"complete", "partial"}
    )


def transition_allowed(
    previous: str,
    current: str,
    *,
    owner_readback_confirmed: bool = False,
    authority_basis_ref: str | None = None,
    revalidation_required: bool = False,
    resume_condition_met: bool = False,
    successor_readback_confirmed: bool = False,
    predecessor_unchanged: bool = False,
    successor_retains_evidence: bool = False,
) -> bool:
    if previous not in STATES or current not in STATES:
        return False
    if previous == current:
        return True
    if previous in {"uninvestigated", "investigating"} and current == "resolved":
        return owner_readback_confirmed
    if current == "rejected":
        return (
            previous == "investigating"
            and owner_readback_confirmed
            and bool(authority_basis_ref)
        )
    if current == "superseded":
        return (
            successor_readback_confirmed
            and predecessor_unchanged
            and successor_retains_evidence
        )
    if current == "deferred":
        return previous in {"uninvestigated", "investigating"}
    if current == "blocked":
        return previous == "investigating"
    if current == "investigating":
        return previous in {
            "uninvestigated",
            "resolved",
            "rejected",
            "deferred",
            "blocked",
        } and (
            previous in {"uninvestigated", "blocked"}
            or revalidation_required
            or resume_condition_met
        )
    return previous == "uninvestigated" and current == "investigating"


def completion_check(
    run: dict[str, Any],
    *,
    root_binding: str,
    provider_readbacks: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Check persisted evidence against readbacks bound to the supplied root context."""
    try:
        validate_artifact(run, "context-synthesis-run")
        root_binding = _text(root_binding, "root_binding")
    except ContractError as exc:
        return {"complete": False, "status": "invalid", "reason": str(exc)}
    summary = run["result_summary"]
    if summary["status"] in {"blocked_incomplete", "in_progress"}:
        return {"complete": False, "status": "incomplete", "reason": summary["status"]}
    if run["scan_completeness"] != "complete":
        return {"complete": False, "status": "incomplete", "reason": "scan_incomplete"}
    if provider_readbacks is None:
        return {
            "complete": False,
            "status": "unverifiable",
            "reason": "provider_readbacks_required",
        }

    def exact_readback(
        ref: str,
        revision: str,
        expected_hash: str | None = None,
        *,
        context_artifact: bool = False,
    ) -> dict[str, Any] | None:
        value = provider_readbacks.get(ref)
        if (
            not isinstance(value, dict)
            or value.get("artifact_ref") != ref
            or value.get("revision") != revision
            or (context_artifact and value.get("root_binding") != root_binding)
            or not isinstance(value.get("sha256"), str)
            or not SHA256_RE.fullmatch(value["sha256"])
            or not isinstance(value.get("content"), str)
            or hashlib.sha256(value["content"].encode("utf-8")).hexdigest()
            != value["sha256"]
            or (expected_hash is not None and value["sha256"] != expected_hash)
        ):
            return None
        return value

    for source in run["snapshot"]["referenced_sources"]:
        if (
            exact_readback(
                source["artifact_ref"],
                source["source_revision"],
                source["content_hash"],
                context_artifact=source["source_kind"] in {"signal_batch", "candidate"},
            )
            is None
        ):
            return {
                "complete": False,
                "status": "unverifiable",
                "reason": "snapshot_source_provider_readback_mismatch",
            }
    for operation in run["triage_plan"]["planned_candidate_ops"]:
        result = operation["confirmed_result"]
        if not all(
            result.get(key)
            for key in ("artifact_ref", "storage_revision", "content_hash")
        ):
            return {
                "complete": False,
                "status": "incomplete",
                "reason": "candidate_readback_missing",
            }
        if result["content_hash"] != operation["planned_content_hash"]:
            return {
                "complete": False,
                "status": "incomplete",
                "reason": "candidate_readback_hash_mismatch",
            }
        readback = provider_readbacks.get(result["artifact_ref"])
        if (
            not isinstance(readback, dict)
            or readback.get("kind") != "context-rule-candidate"
            or readback.get("root_binding") != root_binding
            or readback.get("artifact_ref") != result["artifact_ref"]
            or readback.get("revision") != result["storage_revision"]
            or readback.get("sha256") != result["content_hash"]
            or not isinstance(readback.get("content"), str)
        ):
            return {
                "complete": False,
                "status": "unverifiable",
                "reason": "candidate_provider_readback_mismatch",
            }
        try:
            candidate = parse_canonical_json(
                readback["content"].encode("utf-8", "strict")
            )
            validate_artifact(candidate, "context-rule-candidate")
        except (ContractError, UnicodeError):
            return {
                "complete": False,
                "status": "unverifiable",
                "reason": "candidate_readback_content_invalid",
            }
        if (
            candidate["artifact_ref"] != operation["candidate_ref"]
            or candidate["candidate_identity"] != operation["candidate_identity"]
            or hashlib.sha256(readback["content"].encode("utf-8")).hexdigest()
            != result["content_hash"]
        ):
            return {
                "complete": False,
                "status": "unverifiable",
                "reason": "candidate_readback_content_mismatch",
            }
        if operation["planned_payload"] is not None and readback[
            "content"
        ] != canonical_bytes(operation["planned_payload"]).decode("utf-8"):
            return {
                "complete": False,
                "status": "incomplete",
                "reason": "candidate_readback_differs_from_plan",
            }
        for link in candidate["evidence_links"]:
            if link["link_kind"] == "direct_source_ref":
                if (
                    exact_readback(
                        link["direct_source_ref"],
                        link["direct_source_revision"],
                        link["source_content_hash"],
                    )
                    is None
                ):
                    return {
                        "complete": False,
                        "status": "unverifiable",
                        "reason": "direct_evidence_readback_mismatch",
                    }
            else:
                signal_batch_evidence = provider_readbacks.get(link["signal_batch_ref"])
                signal_batch_readback = (
                    exact_readback(
                        link["signal_batch_ref"],
                        signal_batch_evidence.get("revision", ""),
                        context_artifact=True,
                    )
                    if isinstance(signal_batch_evidence, dict)
                    else None
                )
                if (
                    not isinstance(signal_batch_readback, dict)
                    or not isinstance(signal_batch_readback.get("content"), str)
                    or signal_batch_readback.get("artifact_ref")
                    != link["signal_batch_ref"]
                    or hashlib.sha256(
                        signal_batch_readback["content"].encode("utf-8")
                    ).hexdigest()
                    != signal_batch_readback.get("sha256")
                ):
                    return {
                        "complete": False,
                        "status": "unverifiable",
                        "reason": "signal_batch_readback_mismatch",
                    }
                try:
                    signal_batch = parse_canonical_json(
                        signal_batch_readback["content"]
                    )
                    validate_artifact(signal_batch, "context-signal-batch")
                except ContractError:
                    return {
                        "complete": False,
                        "status": "unverifiable",
                        "reason": "signal_batch_readback_invalid",
                    }
                signal = next(
                    (
                        item
                        for item in signal_batch["signals"]
                        if item["signal_identity"] == link["signal_identity"]
                    ),
                    None,
                )
                if (
                    signal is None
                    or signal["signal_content_hash"] != link["signal_content_hash"]
                    or signal_batch["source"]["source_content_hash"]
                    != link["source_content_hash"]
                ):
                    return {
                        "complete": False,
                        "status": "unverifiable",
                        "reason": "signal_evidence_readback_mismatch",
                    }
        for resolution in candidate["resolution_links"]:
            if (
                exact_readback(
                    resolution["artifact_ref"],
                    resolution["artifact_revision"],
                    resolution["artifact_content_hash"],
                )
                is None
            ):
                return {
                    "complete": False,
                    "status": "unverifiable",
                    "reason": "resolution_owner_readback_mismatch",
                }
        for dependency in candidate["currentness_dependencies"]:
            if (
                exact_readback(
                    dependency["target_ref"],
                    dependency["source_revision"],
                    dependency["dependency_content_hash"],
                )
                is None
            ):
                return {
                    "complete": False,
                    "status": "unverifiable",
                    "reason": "candidate_dependency_readback_mismatch",
                }
        for question in candidate["question_refs"]:
            if (
                exact_readback(
                    question["question_artifact_ref"], question["question_revision"]
                )
                is None
            ):
                return {
                    "complete": False,
                    "status": "unverifiable",
                    "reason": "question_readback_mismatch",
                }
        for conformance in candidate["implementation_conformance_refs"]:
            if conformance["verified"]:
                evidence_readback = provider_readbacks.get(conformance["ref"])
                if (
                    not isinstance(evidence_readback, dict)
                    or evidence_readback.get("artifact_ref") != conformance["ref"]
                    or evidence_readback.get("revision") != conformance["revision"]
                    or not isinstance(evidence_readback.get("sha256"), str)
                    or not SHA256_RE.fullmatch(evidence_readback["sha256"])
                    or not isinstance(evidence_readback.get("content"), str)
                    or hashlib.sha256(
                        evidence_readback["content"].encode("utf-8")
                    ).hexdigest()
                    != evidence_readback["sha256"]
                ):
                    return {
                        "complete": False,
                        "status": "unverifiable",
                        "reason": "implementation_conformance_readback_mismatch",
                    }
        for handoff in candidate["handoff_records"]:
            if handoff["status"] in {"pending", "blocked_unverifiable"}:
                return {
                    "complete": False,
                    "status": "incomplete",
                    "reason": "required_handoff_unresolved",
                }
            if handoff["status"] == "confirmed_by_readback":
                target = handoff["confirmed_target_ref"]
                target_readback = provider_readbacks.get(target["artifact_ref"])
                if (
                    not isinstance(target_readback, dict)
                    or target_readback.get("artifact_ref") != target["artifact_ref"]
                    or target_readback.get("revision") != target["artifact_revision"]
                    or target_readback.get("sha256") != target["artifact_content_hash"]
                    or not isinstance(target_readback.get("content"), str)
                    or hashlib.sha256(
                        target_readback["content"].encode("utf-8")
                    ).hexdigest()
                    != target["artifact_content_hash"]
                ):
                    return {
                        "complete": False,
                        "status": "unverifiable",
                        "reason": "handoff_provider_readback_mismatch",
                    }
    run_readback = provider_readbacks.get(run["artifact_ref"])
    expected_run_hash = hashlib.sha256(canonical_bytes(run)).hexdigest()
    if (
        not isinstance(run_readback, dict)
        or run_readback.get("kind") != "context-synthesis-run"
        or run_readback.get("root_binding") != root_binding
        or run_readback.get("artifact_ref") != run["artifact_ref"]
        or not run_readback.get("revision")
        or run_readback.get("sha256") != expected_run_hash
        or run_readback.get("content") != canonical_bytes(run).decode("utf-8")
    ):
        return {
            "complete": False,
            "status": "unverifiable",
            "reason": "run_provider_readback_mismatch",
        }
    return {
        "complete": True,
        "status": "complete",
        "readback_required": True,
        "reason": "run_contract_valid_host_readback_required",
    }


def project_artifact(
    artifact: dict[str, Any],
    *,
    kind: str,
    revision: str | None = None,
    item_limit: int = 24,
    excerpt_chars: int = 240,
) -> dict[str, Any]:
    """Return a compact search/read projection without planned or source bodies."""
    if (
        not isinstance(item_limit, int)
        or isinstance(item_limit, bool)
        or not 1 <= item_limit <= 100
    ):
        _fail("projection_item_limit_invalid")
    if (
        not isinstance(excerpt_chars, int)
        or isinstance(excerpt_chars, bool)
        or not 40 <= excerpt_chars <= 2000
    ):
        _fail("projection_excerpt_limit_invalid")
    row = validate_artifact(artifact, kind)
    projection: dict[str, Any] = {
        "kind": kind,
        "artifact_ref": row["artifact_ref"],
        "identity": row.get(
            "batch_identity", row.get("candidate_identity", row.get("run_identity"))
        ),
        "revision": revision,
        "content_hash": hashlib.sha256(canonical_bytes(row)).hexdigest(),
    }
    if kind == "context-signal-batch":
        source = row["source"]
        projection.update(
            {
                "source_ref": source["artifact_ref"],
                "source_content_hash": source["source_content_hash"],
                "actual_inspected_range": source["actual_inspected_range"],
                "observation_condition": source["observation_condition"],
                "scan_completeness": row["scan_completeness"],
                "candidate_check": row["candidate_check"],
                "signal_count": len(row["signals"]),
                "signals": [
                    {
                        "signal_identity": signal["signal_identity"],
                        "signal_content_hash": signal["signal_content_hash"],
                        "evidence_type": signal["evidence_type"],
                        "fact_summary": signal["fact_summary"][:excerpt_chars],
                        "summary_truncated": len(signal["fact_summary"])
                        > excerpt_chars,
                        "attribute_keys": sorted(signal["cross_cutting_attributes"]),
                        "independence_group": signal["independence_group"],
                    }
                    for signal in row["signals"][:item_limit]
                ],
                "signals_omitted": max(0, len(row["signals"]) - item_limit),
            }
        )
    elif kind == "context-rule-candidate":
        projection.update(
            {
                "identity_key": row["identity_key"],
                "rule_statement_excerpt": row["rule_statement"][:excerpt_chars],
                "rule_statement_truncated": len(row["rule_statement"]) > excerpt_chars,
                "scope_summary_excerpt": row["applicability"]["scope_summary"][
                    :excerpt_chars
                ],
                "cross_cutting_attribute_keys": sorted(
                    row["applicability"]["cross_cutting_attributes"]
                ),
                "related_candidate_refs": row["related_candidate_refs"][:item_limit],
                "related_candidates_omitted": max(
                    0, len(row["related_candidate_refs"]) - item_limit
                ),
                "evidence_links": row["evidence_links"][:item_limit],
                "evidence_links_omitted": max(
                    0, len(row["evidence_links"]) - item_limit
                ),
                "unobserved_ranges": row["unobserved_ranges"][:item_limit],
                "unobserved_ranges_omitted": max(
                    0, len(row["unobserved_ranges"]) - item_limit
                ),
                "currentness_dependencies": row["currentness_dependencies"][
                    :item_limit
                ],
                "dependencies_omitted": max(
                    0, len(row["currentness_dependencies"]) - item_limit
                ),
                "evaluation_status": row["evaluation_status"],
                "resolution_state": row["resolution_state"],
                "resolution_link_count": len(row["resolution_links"]),
                "question_ref_count": len(row["question_refs"]),
                "handoff_statuses": [item["status"] for item in row["handoff_records"]],
            }
        )
    else:
        plan = row["triage_plan"]
        projection.update(
            {
                "workflow_ref": row["workflow_ref"],
                "workflow_operation_id": row["workflow_operation_id"],
                "requested_scope": row["requested_scope"],
                "scan_completeness": row["scan_completeness"],
                "snapshot_hash": row["snapshot"]["snapshot_hash"],
                "target_batch_refs": plan["target_batch_refs"],
                "planned_candidate_ops": [
                    {
                        "candidate_identity": operation["candidate_identity"],
                        "candidate_ref": operation["candidate_ref"],
                        "action": operation["action"],
                        "base_content_hash": operation["base_content_hash"],
                        "planned_content_hash": operation["planned_content_hash"],
                        "confirmed_result": operation["confirmed_result"],
                    }
                    for operation in plan["planned_candidate_ops"][:item_limit]
                ],
                "planned_candidate_ops_omitted": max(
                    0, len(plan["planned_candidate_ops"]) - item_limit
                ),
                "result_summary": row["result_summary"],
            }
        )
    return projection


def select_run_operations(
    run: dict[str, Any], candidate_identities: Iterable[str]
) -> list[dict[str, Any]]:
    """Return only requested planned operations and their payloads from a validated run."""
    requested = list(candidate_identities)
    if not requested or not all(
        isinstance(item, str) and SHA256_RE.fullmatch(item) for item in requested
    ):
        _fail("candidate_identities_invalid")
    if len(requested) != len(set(requested)):
        _fail("candidate_identities_duplicated")
    operations = {
        item["candidate_identity"]: item
        for item in run.get("triage_plan", {}).get("planned_candidate_ops", [])
    }
    missing = sorted(set(requested) - set(operations))
    if missing:
        _fail("planned_candidate_operations_missing")
    return [operations[identity] for identity in requested]


def select_batch_signals(
    batch: dict[str, Any], signal_identities: Iterable[str]
) -> list[dict[str, Any]]:
    """Return only explicitly requested signal bodies from a validated batch."""
    requested = list(signal_identities)
    if not requested or not all(
        isinstance(item, str) and SHA256_RE.fullmatch(item) for item in requested
    ):
        _fail("signal_identities_invalid")
    if len(requested) != len(set(requested)):
        _fail("signal_identities_duplicated")
    signals = {item["signal_identity"]: item for item in batch.get("signals", [])}
    missing = sorted(set(requested) - set(signals))
    if missing:
        _fail("signals_missing")
    return [signals[identity] for identity in requested]


def handle(request: Any) -> dict[str, Any]:
    """Small JSON interface for pure identity and validation operations only."""
    if not isinstance(request, dict):
        return {"status": "blocked", "reason": "request_must_be_object"}
    try:
        operation = request.get("operation")
        if operation == "identity":
            if request.get("kind") == "context-signal-batch":
                if "corrected_batch_targets" in request:
                    result = correction_batch_identity(
                        request["original_batch_identity"],
                        request["corrected_batch_targets"],
                        request["signals"],
                    )
                else:
                    result = batch_identity(
                        request["source_artifact_ref"],
                        request["source_content_hash"],
                        request["actual_inspected_range"],
                        request.get("observation_condition"),
                    )
            elif request.get("kind") == "context-rule-candidate":
                result = candidate_identity(request["identity_key"])
            elif request.get("kind") == "context-synthesis-run":
                op_id = workflow_operation_id(
                    request["workflow_ref"],
                    request["operation_input"],
                    request["requested_scope"],
                )
                result = run_identity(op_id)
            else:
                _fail("artifact_kind_invalid")
            return {"status": "ok", "identity": result}
        if operation == "validate":
            artifact = validate_artifact(request.get("artifact"), request.get("kind"))
            return {
                "status": "valid",
                "artifact_ref": artifact["artifact_ref"],
                "canonical_content_hash": hashlib.sha256(
                    canonical_bytes(artifact)
                ).hexdigest(),
            }
        if operation == "impact":
            return {
                "status": "ok",
                **impact(
                    request.get("current_sources", []), request.get("saved_sources", [])
                ),
            }
        if operation == "batch_covers":
            complete = batch_covers_request(
                request.get("batch", {}),
                source_ref=request.get("source_ref"),
                source_content_hash=request.get("source_content_hash"),
                requested_range=request.get("requested_range"),
                observation_condition=request.get("observation_condition"),
            )
            return {"status": "ok", "covers_request": complete}
        if operation == "batch_union_covers":
            complete = batch_union_covers_request(
                request.get("batches", []),
                source_ref=request.get("source_ref"),
                source_content_hash=request.get("source_content_hash"),
                requested_range=request.get("requested_range"),
                observation_condition=request.get("observation_condition"),
            )
            return {"status": "ok", "covers_request": complete}
        if operation == "project":
            return {
                "status": "ok",
                "projection": project_artifact(
                    request.get("artifact"),
                    kind=request.get("kind"),
                    revision=request.get("revision"),
                    item_limit=request.get("item_limit", 24),
                    excerpt_chars=request.get("excerpt_chars", 240),
                ),
            }
        if operation == "select_run_operations":
            run = validate_artifact(request.get("run"), "context-synthesis-run")
            return {
                "status": "ok",
                "operations": select_run_operations(
                    run, request.get("candidate_identities", [])
                ),
            }
        if operation == "select_batch_signals":
            batch = validate_artifact(request.get("batch"), "context-signal-batch")
            return {
                "status": "ok",
                "signals": select_batch_signals(
                    batch, request.get("signal_identities", [])
                ),
            }
        if operation == "completion_check":
            return completion_check(
                request.get("run"),
                root_binding=request.get("root_binding"),
                provider_readbacks=request.get("provider_readbacks"),
            )
        _fail("operation_invalid")
    except (ContractError, KeyError, TypeError, ValueError) as exc:
        return {"status": "blocked", "reason": str(exc)}


def main() -> int:
    raw = sys.stdin.buffer.read(MAX_ARTIFACT_BYTES + 1)
    if len(raw) > MAX_ARTIFACT_BYTES:
        result = {"status": "blocked", "reason": "input_too_large"}
    else:
        try:
            request = json.loads(raw.decode("utf-8", "strict"))
            result = handle(request)
        except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
            result = {
                "status": "blocked",
                "reason": f"invalid_json:{type(exc).__name__}",
            }
    sys.stdout.write(
        json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
