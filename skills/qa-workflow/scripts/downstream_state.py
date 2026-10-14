"""Project qa-workflow's committed downstream scope state without LLM filtering."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from decimal import Decimal
from typing import Any

from runtime_contract import (
    FULL_DIGEST_RE,
    MAX_AGGREGATE_INPUT_BYTES,
    MAX_DEPTH,
    MAX_EXPLORATION_NODES,
    MAX_STRING_BYTES,
    InvalidInput,
    LimitExceeded,
    RuntimeErrorBase,
    _state_row_map,
    _validate_metadata,
    canonical_json_text,
    canonicalize,
    extract_machine_blocks,
    generation_fingerprint,
    input_fingerprint,
    model_fingerprint,
    upstream_entity_fingerprints,
    validate_entity_collection,
    validate_upstream_entities,
)

_SKILL = "qa-workflow"
_ROOT_ID = "qa-workflow::artifact:workflow_runtime:all"
_ALLOWED_FIELDS = {
    "workflow_ref",
    "workflow_state_record",
    "current_scope_ids",
    "blocked_scope_ids",
    "previous_qa_workflow_artifact_markdown",
    "scope_removal_resolutions",
    "scope_removal_applied_states",
}
_SCOPE_RE = re.compile(r"SCOPE-[0-9]{3,}")
_ENTITY_SKILLS = {
    "test-requirement-design": {"tr"},
    "test-condition-design": {"tcn", "model", "ci"},
    "test-case-design": {"tc"},
}
_IDENTITY_RE = {
    "tr": re.compile(r"TR-[0-9]{3}"),
    "tcn": re.compile(r"TCN-[0-9]{3}"),
    "model": re.compile(r"[a-z][a-z0-9-]*-[0-9]{3,}"),
    "ci": re.compile(r"TCN-[0-9]{3}-CI[0-9]{2,}"),
    "tc": re.compile(r"TC-[0-9]{3}"),
}
_ID_FIELD = {
    "tr": "tr_id",
    "tcn": "tcn_id",
    "model": "model_key",
    "ci": "ci_id",
    "tc": "tc_id",
}
_HISTORY_FIELD = {
    "tr": "inactive_tr_history",
    "tcn": "inactive_tcn_history",
    "model": "inactive_model_history",
    "ci": "inactive_materialize_history",
    "tc": "inactive_tc_history",
}


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise InvalidInput(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _number(token: str) -> int | Decimal:
    if len(token) > 4096:
        raise LimitExceeded("JSON number token exceeds the input limit")
    return int(token) if re.fullmatch(r"-?(?:0|[1-9][0-9]*)", token) else Decimal(token)


def _check_tree(value: Any, *, depth: int = 0, count: list[int] | None = None) -> None:
    count = count if count is not None else [0]
    count[0] += 1
    if count[0] > MAX_EXPLORATION_NODES or depth > MAX_DEPTH:
        raise LimitExceeded("JSON depth or item limit exceeded")
    if isinstance(value, str) and len(value.encode("utf-8")) > MAX_STRING_BYTES:
        raise LimitExceeded("JSON string exceeds 64 KiB")
    if isinstance(value, dict):
        for key, child in value.items():
            if len(key.encode("utf-8")) > MAX_STRING_BYTES:
                raise LimitExceeded("JSON key exceeds 64 KiB")
            _check_tree(child, depth=depth + 1, count=count)
    elif isinstance(value, list):
        for child in value:
            _check_tree(child, depth=depth + 1, count=count)


def _load_request(raw: bytes) -> dict[str, Any]:
    if len(raw) > MAX_AGGREGATE_INPUT_BYTES:
        raise LimitExceeded("stdin exceeds 16 MiB")
    try:
        request = json.loads(
            raw.decode("utf-8", errors="strict"),
            object_pairs_hook=_pairs,
            parse_int=_number,
            parse_float=_number,
            parse_constant=lambda _: (_ for _ in ()).throw(
                InvalidInput("invalid JSON number")
            ),
        )
    except RuntimeErrorBase:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
        raise InvalidInput("stdin must contain one strict UTF-8 JSON object") from exc
    if not isinstance(request, dict) or set(request) != _ALLOWED_FIELDS:
        raise InvalidInput("top-level fields are missing or unknown")
    markdown = request.get("previous_qa_workflow_artifact_markdown")
    if markdown is not None and not isinstance(markdown, str):
        raise InvalidInput("previous artifact markdown must be string or null")
    if (
        markdown is not None
        and len(markdown.encode("utf-8")) > MAX_AGGREGATE_INPUT_BYTES
    ):
        raise LimitExceeded("previous artifact exceeds 16 MiB")
    transport = {
        key: value
        for key, value in request.items()
        if key != "previous_qa_workflow_artifact_markdown"
    }
    _check_tree(transport)
    return request


def _sorted_ids(value: Any, name: str, pattern: re.Pattern[str]) -> list[str]:
    if not isinstance(value, list) or any(
        not isinstance(row, str) or not pattern.fullmatch(row) for row in value
    ):
        raise InvalidInput(f"{name} contains an invalid identifier")
    if value != sorted(set(value)):
        raise InvalidInput(f"{name} must be sorted and unique")
    return value


def _validate_state_record(value: Any, workflow_ref: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != {
        "workflow_ref",
        "schema_version",
        "state",
    }:
        raise InvalidInput("workflow_state_record schema is invalid")
    if (
        value.get("workflow_ref") != workflow_ref
        or value.get("schema_version") != "1"
        or not isinstance(value.get("state"), dict)
    ):
        raise InvalidInput("workflow_state_record identity or version mismatch")
    state = value["state"]
    binding = state.get("last_completed_qa_workflow_artifact")
    if binding is None:
        return {
            "workflow_ref": workflow_ref,
            "schema_version": "1",
            "state": state,
            "binding": None,
        }
    if not isinstance(binding, dict) or set(binding) != {
        "artifact_ref",
        "artifact_revision",
        "artifact_sha256",
    }:
        raise InvalidInput("last completed artifact binding schema is invalid")
    if (
        not isinstance(binding["artifact_ref"], str)
        or not binding["artifact_ref"].strip()
        or not isinstance(binding["artifact_revision"], str)
        or not binding["artifact_revision"].strip()
        or not isinstance(binding["artifact_sha256"], str)
        or not re.fullmatch(r"[0-9a-f]{64}", binding["artifact_sha256"])
    ):
        raise InvalidInput("last completed artifact binding is invalid")
    return {
        "workflow_ref": workflow_ref,
        "schema_version": "1",
        "state": state,
        "binding": binding,
    }


def _validate_frozen_pair(
    markdown: str, workflow_ref: str
) -> tuple[dict[str, Any], dict[str, Any]]:
    try:
        inputs = extract_machine_blocks(markdown, "Machine Runtime Input")
        results = extract_machine_blocks(markdown, "Machine Runtime Result")
        entity_blocks = extract_machine_blocks(markdown, "Machine Entities")
    except RuntimeErrorBase as exc:
        raise InvalidInput("historical runtime blocks are invalid") from exc
    if (
        len(inputs) != 1
        or len(results) != 1
        or inputs[0][0] != _ROOT_ID
        or results[0][0] != _ROOT_ID
    ):
        raise InvalidInput("historical qa-workflow root pair is missing or duplicated")
    source, result = inputs[0][1], results[0][1]
    if set(source) != {"metadata", "input"} or not isinstance(
        source.get("input"), dict
    ):
        raise InvalidInput("historical input block schema is invalid")
    metadata = source["metadata"]
    if (
        not isinstance(metadata, dict)
        or metadata.get("runtime_contract_version") != "runtime-v2"
    ):
        raise InvalidInput("historical runtime is not runtime-v2")
    current_metadata = dict(metadata)
    _validate_metadata(current_metadata, skill=_SKILL)
    input_value = source["input"]
    if input_value.get("workflow_ref") != workflow_ref:
        raise InvalidInput("historical workflow_ref mismatch")
    result_fields = {
        "envelope_version",
        "skill",
        "runtime_contract_version",
        "generator_contract_version",
        "generator",
        "runtime_unit_key",
        "model_key",
        "input_fingerprint",
        "model_fingerprint",
        "generation_fingerprint",
        "runtime_implementation_fingerprint",
        "generator_implementation_fingerprint",
        "upstream_entity_fingerprints",
        "upstream_runtime_units",
        "support_status",
        "static_data_versions",
        "runtime_status",
        "result_status",
        "runtime_required",
        "deterministic_generated",
        "fallback_reason",
        "payload",
        "issues",
    }
    if set(result) != result_fields or (
        result.get("envelope_version") != "1"
        or result.get("skill") != _SKILL
        or result.get("runtime_contract_version") != "runtime-v2"
        or result.get("generator_contract_version") != "workflow-runtime-v1"
        or result.get("generator") != "workflow_runtime"
        or result.get("runtime_unit_key") != "artifact:workflow_runtime:all"
        or result.get("model_key") is not None
        or not isinstance(result.get("runtime_implementation_fingerprint"), str)
        or FULL_DIGEST_RE.fullmatch(result["runtime_implementation_fingerprint"])
        is None
        or not isinstance(result.get("generator_implementation_fingerprint"), str)
        or FULL_DIGEST_RE.fullmatch(result["generator_implementation_fingerprint"])
        is None
        or result.get("result_status") != "ready"
        or result.get("runtime_status") != "ok"
        or not isinstance(result.get("payload"), dict)
        or result["payload"].get("can_complete") is not True
    ):
        raise InvalidInput(
            "historical result schema or frozen runtime identity is invalid"
        )
    expected_input = input_fingerprint(
        _SKILL,
        metadata["runtime_unit_key"],
        metadata["input_mode"],
        input_value,
        metadata["authority_refs"],
        metadata["reference_refs"],
        metadata["selection_source"],
    )
    expected_model = model_fingerprint(metadata, expected_input)
    upstream = upstream_entity_fingerprints(validate_upstream_entities(metadata))
    expected_generation = generation_fingerprint(
        generator="workflow_runtime",
        input_fp=expected_input,
        model_fp=expected_model,
        runtime_contract_version="runtime-v2",
        generator_contract_version="workflow-runtime-v1",
        runtime_impl_fp=result["runtime_implementation_fingerprint"],
        generator_impl_fp=result["generator_implementation_fingerprint"],
        upstream=upstream,
        static_data_versions=result.get("static_data_versions", {}),
    )
    if (
        result.get("input_fingerprint") != expected_input
        or result.get("model_fingerprint") != expected_model
        or result.get("generation_fingerprint") != expected_generation
        or result.get("upstream_entity_fingerprints") != upstream
        or result.get("upstream_runtime_units")
        != canonicalize(
            metadata["upstream_runtime_units"], parent_key="upstream_runtime_units"
        )
        or result.get("static_data_versions") != metadata["static_data_versions"]
    ):
        raise InvalidInput(
            "historical runtime fingerprints or dependency projection mismatch"
        )
    required_input = {
        "workflow_ref",
        "workflow_scopes",
        "runtime_units",
        "current_entities",
        "current_runtime_units",
        "unsupported_item_closures",
    }
    if set(input_value) != required_input:
        raise InvalidInput("historical workflow input schema is invalid")
    entities = input_value["current_entities"]
    if not isinstance(entities, list):
        raise InvalidInput("historical current_entities is invalid")
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in entities:
        if not isinstance(row, dict) or not isinstance(row.get("skill"), str):
            raise InvalidInput("historical entity row is invalid")
        grouped.setdefault(row["skill"], []).append(row)
    checked_entities = []
    for skill, rows in grouped.items():
        checked_entities.extend(validate_entity_collection(rows, expected_skill=skill))
    checked_entities.sort(
        key=lambda row: (row["skill"], row["entity_type"], row["entity_ref"])
    )
    payload_entities = result["payload"].get("current_entities")
    if canonical_json_text(payload_entities) != canonical_json_text(checked_entities):
        raise InvalidInput("historical result Entity projection mismatch")
    if len(entity_blocks) > 1:
        raise InvalidInput("historical Machine Entities block is duplicated")
    if entity_blocks:
        wrapper = entity_blocks[0][1]
        if (
            set(wrapper) != {"schema_version", "skill", "entities"}
            or wrapper.get("schema_version") != "entity-state-v2"
            or wrapper.get("skill") != _SKILL
        ):
            raise InvalidInput("historical Machine Entities wrapper is invalid")
        validate_entity_collection(wrapper["entities"], expected_skill=_SKILL)
    scopes = input_value["workflow_scopes"]
    if not isinstance(scopes, list) or not scopes:
        raise InvalidInput("historical workflow scopes are missing")
    seen_scopes: set[tuple[str, str | None, str | None]] = set()
    for row in scopes:
        if not isinstance(row, dict) or set(row) != {
            "skill",
            "target",
            "execution_range",
            "input_mode",
            "normalized_input",
            "current_structure_state",
        }:
            raise InvalidInput("historical workflow scope schema is invalid")
        identity = (row["skill"], row["target"], row["execution_range"])
        if identity in seen_scopes or not isinstance(row["normalized_input"], dict):
            raise InvalidInput("historical workflow scope is duplicated or invalid")
        seen_scopes.add(identity)
        _validate_structure_state(row["skill"], row["current_structure_state"])
    return input_value, result["payload"]


def _validate_structure_state(skill: str, state: Any) -> None:
    if not isinstance(state, dict) or set(state) != {
        "runtime_results",
        "carry_forward_entities",
        "previous_ci_id_state",
    }:
        raise InvalidInput("historical current_structure_state schema is invalid")
    if (
        not isinstance(state["runtime_results"], list)
        or not isinstance(state["carry_forward_entities"], list)
        or not isinstance(state["previous_ci_id_state"], list)
    ):
        raise InvalidInput("historical current_structure_state values are invalid")
    validate_entity_collection(state["carry_forward_entities"], expected_skill=skill)
    seen: set[str] = set()
    for row in state["runtime_results"]:
        if (
            not isinstance(row, dict)
            or set(row) != {"identity", "result"}
            or not isinstance(row["identity"], str)
            or not row["identity"].startswith(skill + "::")
            or row["identity"] in seen
            or not isinstance(row["result"], dict)
        ):
            raise InvalidInput("historical nested runtime identity is invalid")
        seen.add(row["identity"])
        result = row["result"]
        for field in (
            "input_fingerprint",
            "generation_fingerprint",
            "runtime_implementation_fingerprint",
            "generator_implementation_fingerprint",
        ):
            if not isinstance(result.get(field), str) or not FULL_DIGEST_RE.fullmatch(
                result[field]
            ):
                raise InvalidInput("historical nested runtime fingerprint is invalid")
        if (
            result.get("envelope_version") != "1"
            or result.get("runtime_contract_version") != "runtime-v2"
            or not isinstance(result.get("payload"), dict)
        ):
            raise InvalidInput("historical nested runtime result is invalid")
        expected = generation_fingerprint(
            generator=result.get("generator"),
            input_fp=result["input_fingerprint"],
            model_fp=result.get("model_fingerprint"),
            runtime_contract_version="runtime-v2",
            generator_contract_version=result.get("generator_contract_version"),
            runtime_impl_fp=result["runtime_implementation_fingerprint"],
            generator_impl_fp=result["generator_implementation_fingerprint"],
            upstream=result.get("upstream_entity_fingerprints"),
            static_data_versions=result.get("static_data_versions"),
        )
        if expected != result.get("generation_fingerprint"):
            raise InvalidInput(
                "historical nested runtime generation fingerprint mismatch"
            )
    if skill == "test-condition-design":
        for row in state["previous_ci_id_state"]:
            if (
                not isinstance(row, dict)
                or set(row) != {"ci_id", "status", "scope_refs"}
                or row["status"] not in {"active", "inactive", "deleted"}
            ):
                raise InvalidInput("historical CI state is invalid")
            if not isinstance(row["scope_refs"], list) or row["scope_refs"] != sorted(
                set(row["scope_refs"])
            ):
                raise InvalidInput("historical CI scope refs are invalid")
    elif state["previous_ci_id_state"]:
        raise InvalidInput("non-TCD structure state contains CI state")


def _entity_maps(
    input_value: dict[str, Any], payload: dict[str, Any]
) -> tuple[
    dict[tuple[str, str, str], dict[str, Any]],
    dict[tuple[str, str, str], dict[str, Any]],
]:
    current: dict[tuple[str, str, str], dict[str, Any]] = {}
    for row in input_value["current_entities"]:
        identity = (row["skill"], row["entity_type"], row["entity_ref"])
        if identity in current:
            raise InvalidInput("historical entity identity is duplicated")
        current[identity] = row
    histories: dict[tuple[str, str, str], dict[str, Any]] = {}
    for scope in input_value["workflow_scopes"]:
        state = scope["current_structure_state"]
        for runtime in state["runtime_results"]:
            result_payload = runtime["result"]["payload"]
            for field, skill, entity_type, id_field in (
                ("inactive_tr_history", "test-requirement-design", "tr", "tr_id"),
                ("inactive_tcn_history", "test-condition-design", "tcn", "tcn_id"),
                (
                    "inactive_model_history",
                    "test-condition-design",
                    "model",
                    "model_key",
                ),
                ("inactive_tc_history", "test-case-design", "tc", "tc_id"),
            ):
                rows = result_payload.get(field, [])
                if not isinstance(rows, list):
                    raise InvalidInput("historical inactive history is invalid")
                for entity in rows:
                    if (
                        not isinstance(entity, dict)
                        or entity.get("skill") != skill
                        or entity.get("entity_type") != entity_type
                    ):
                        raise InvalidInput(
                            "historical inactive Entity snapshot is invalid"
                        )
                    identity = (skill, entity_type, entity.get("entity_ref"))
                    if entity.get("content", {}).get(id_field) != identity[2]:
                        raise InvalidInput(
                            "historical inactive Entity identity mismatch"
                        )
                    if identity in histories and canonical_json_text(
                        histories[identity]
                    ) != canonical_json_text(entity):
                        raise InvalidInput(
                            "historical inactive Entity history conflicts"
                        )
                    histories[identity] = entity
    return current, histories


def _entity_rows_by_type(
    entities: dict[tuple[str, str, str], dict[str, Any]], skill: str, entity_type: str
) -> list[dict[str, Any]]:
    return [
        row
        for key, row in entities.items()
        if key[0] == skill and key[1] == entity_type
    ]


def _scope_impact(
    input_value: dict[str, Any],
    current_scope_ids: list[str],
    blocked_scope_ids: list[str],
    resolutions: list[dict[str, Any]],
    applied: list[dict[str, Any]],
) -> dict[str, Any]:
    current, histories = _entity_maps(
        input_value, {"current_entities": input_value["current_entities"]}
    )
    rows_by_identity: dict[tuple[str, str, str], dict[str, Any]] = {}
    state_rows: dict[tuple[str, str, str], dict[str, Any]] = {}
    materialize_histories: dict[str, dict[str, Any]] = {}
    for scope in input_value["workflow_scopes"]:
        skill = scope["skill"]
        state = scope["current_structure_state"]
        for runtime in state["runtime_results"]:
            result = runtime["result"]
            unit = result.get("runtime_unit_key")
            payload = result["payload"]
            for entity_type, field, id_field in (
                ("tr", "tr_id_state", "tr_id"),
                ("tcn", "tcn_id_state", "tcn_id"),
                ("model", "model_key_state", "model_key"),
                ("tc", "tc_id_state", "tc_id"),
            ):
                owner_skill = (
                    "test-requirement-design"
                    if entity_type == "tr"
                    else "test-case-design"
                    if entity_type == "tc"
                    else "test-condition-design"
                )
                if skill != owner_skill or field not in payload:
                    continue
                value = payload[field]
                if not isinstance(value, list):
                    raise InvalidInput("historical state rows are invalid")
                # TCD model_key_state preserves the full model identity
                # metadata alongside status and scope ownership. Reuse the
                # shared previous-state validator so scope removal accepts
                # the production runtime shape and still rejects malformed
                # or unknown state fields.
                for row in _state_row_map(value, id_field).values():
                    if not isinstance(row, dict) or row["status"] not in {
                        "active",
                        "inactive",
                        "deleted",
                    }:
                        raise InvalidInput("historical downstream state row is invalid")
                    identity = (owner_skill, entity_type, row[id_field])
                    if (
                        not _IDENTITY_RE[entity_type].fullmatch(str(identity[2]))
                        or identity in state_rows
                    ):
                        raise InvalidInput(
                            "historical downstream identity is invalid or duplicated"
                        )
                    refs = row["scope_refs"]
                    if (
                        not isinstance(refs, list)
                        or any(
                            not isinstance(ref, str) or not _SCOPE_RE.fullmatch(ref)
                            for ref in refs
                        )
                        or refs != sorted(set(refs))
                    ):
                        raise InvalidInput("historical scope ownership is invalid")
                    if row["status"] == "active" and not refs:
                        raise InvalidInput(
                            "scope ownership unavailable for active downstream Entity"
                        )
                    state_rows[identity] = row
                    entity = (
                        current.get(identity)
                        if row["status"] == "active"
                        else histories.get(identity)
                        if row["status"] == "inactive"
                        else None
                    )
                    if row["status"] == "active" and entity is None:
                        raise InvalidInput(
                            "active historical state has no current Entity"
                        )
                    if row["status"] == "inactive" and entity is None:
                        raise InvalidInput(
                            "inactive historical state has no validated history"
                        )
                    if (
                        entity is not None
                        and entity.get("content", {}).get("scope_refs")
                        != row["scope_refs"]
                        and not (
                            row["status"] == "inactive"
                            and isinstance(
                                entity.get("content", {}).get("scope_refs"), list
                            )
                        )
                    ):
                        raise InvalidInput(
                            "historical Entity ownership does not match state"
                        )
                    rows_by_identity[identity] = entity or {
                        "skill": owner_skill,
                        "entity_type": entity_type,
                        "entity_ref": identity[2],
                        "content": {id_field: identity[2], "scope_refs": refs},
                    }
            if (
                skill == "test-condition-design"
                and unit == "artifact:condition_structure:all"
            ):
                values = payload.get("inactive_materialize_history", [])
                if not isinstance(values, list):
                    raise InvalidInput("inactive materialize history is invalid")
                for entry in values:
                    if not isinstance(entry, dict) or not isinstance(
                        entry.get("tcn_id"), str
                    ):
                        raise InvalidInput("inactive materialize entry is invalid")
                    materialize_histories[entry["tcn_id"]] = entry
        if skill == "test-condition-design":
            for ci in _state_row_map(state["previous_ci_id_state"], "ci_id").values():
                identity = (skill, "ci", ci["ci_id"])
                if identity in state_rows:
                    raise InvalidInput("duplicate CI state")
                state_rows[identity] = ci
                active_entity = (
                    current.get(identity) if ci["status"] == "active" else None
                )
                inactive_entity = None
                if ci["status"] == "inactive":
                    owner = re.match(r"(TCN-[0-9]{3})-CI", ci["ci_id"])
                    entry = materialize_histories.get(owner.group(1)) if owner else None
                    if isinstance(entry, dict):
                        inactive_entity = next(
                            (
                                row
                                for row in entry.get("ci_entities", [])
                                if isinstance(row, dict)
                                and row.get("entity_ref") == ci["ci_id"]
                            ),
                            None,
                        )
                entity = active_entity or inactive_entity
                if ci["status"] == "active" and entity is None:
                    raise InvalidInput("active CI has no current Entity")
                if ci["status"] == "inactive" and entity is None:
                    raise InvalidInput("inactive CI materialize history is missing")
                if entity is not None:
                    rows_by_identity[identity] = entity
    removed = sorted(
        {
            scope
            for row in state_rows.values()
            for scope in row["scope_refs"]
            if scope not in set(current_scope_ids)
        }
    )
    affected: list[dict[str, Any]] = []
    transition_candidates: dict[tuple[str, str, str], dict[str, Any]] = {}
    inactive_ids = {
        name: []
        for name in (
            "inactive_tr_ids",
            "inactive_tcn_ids",
            "inactive_model_keys",
            "inactive_ci_ids",
            "inactive_tc_ids",
        )
    }
    histories_out = {
        name: {}
        for name in (
            "inactive_tr_history",
            "inactive_tcn_history",
            "inactive_model_history",
            "inactive_materialize_history",
            "inactive_tc_history",
        )
    }
    status_id_field = {
        "tr": "inactive_tr_ids",
        "tcn": "inactive_tcn_ids",
        "model": "inactive_model_keys",
        "ci": "inactive_ci_ids",
        "tc": "inactive_tc_ids",
    }

    def entity_fingerprint(entity: dict[str, Any]) -> str:
        return (
            "sha256:"
            + hashlib.sha256(
                canonical_json_text(entity["content"]).encode("utf-8")
            ).hexdigest()
        )

    resolution_map = {}
    for row in resolutions:
        key = (row["skill"], row["entity_type"], row["entity_ref"])
        if key in resolution_map:
            raise InvalidInput("scope removal resolution is duplicated")
        resolution_map[key] = row
    for identity, state_row in state_rows.items():
        skill, entity_type, entity_ref = identity
        status = state_row["status"]
        if status == "deleted":
            continue
        refs = state_row["scope_refs"]
        entity = rows_by_identity.get(identity)
        removed_refs = sorted(set(refs) - set(current_scope_ids))
        if removed_refs:
            if entity is None:
                raise InvalidInput(
                    "scope removal last-active Entity snapshot is missing"
                )
            content = entity.get("content")
            if not isinstance(content, dict) or content.get("scope_refs") != refs:
                if status != "inactive":
                    raise InvalidInput(
                        "scope removal last-active ownership is inconsistent"
                    )
            affected.append(
                {
                    "skill": skill,
                    "entity_type": entity_type,
                    "entity_ref": entity_ref,
                    "previous_status": status,
                    "previous_scope_refs": refs,
                    "removed_scope_refs": removed_refs,
                    "last_active_content": content,
                    "last_active_content_fingerprint": entity_fingerprint(entity),
                }
            )
            if not current_scope_ids:
                transition_candidates[identity] = {
                    "skill": skill,
                    "entity_type": entity_type,
                    "entity_ref": entity_ref,
                    "resolved_scope_refs": [],
                    "status": "deleted",
                }
                continue
            resolution = resolution_map.get(identity)
            if resolution is None:
                continue
            if resolution["resolution"] == "deleted":
                transition_candidates[identity] = {
                    "skill": skill,
                    "entity_type": entity_type,
                    "entity_ref": entity_ref,
                    "resolved_scope_refs": [],
                    "status": "deleted",
                }
            else:
                resolved = resolution["resolved_scope_refs"]
                next_status = (
                    "inactive" if set(resolved) & set(blocked_scope_ids) else "active"
                )
                transition_candidates[identity] = {
                    "skill": skill,
                    "entity_type": entity_type,
                    "entity_ref": entity_ref,
                    "resolved_scope_refs": resolved,
                    "status": next_status,
                }
            continue
        if status == "active" and set(refs) & set(blocked_scope_ids):
            transition_candidates[identity] = {
                "skill": skill,
                "entity_type": entity_type,
                "entity_ref": entity_ref,
                "resolved_scope_refs": refs,
                "status": "inactive",
            }
        if status == "inactive" and not (set(refs) & set(blocked_scope_ids)):
            # An inactive identity remains inactive until its owner explicitly
            # reuses it in a current generator result.
            pass
        final_status = transition_candidates.get(identity, {}).get("status", status)
        if final_status == "inactive":
            id_field = _ID_FIELD[entity_type]
            inactive_ids[status_id_field[entity_type]].append(entity_ref)
            if entity_type == "ci":
                owner = re.match(r"(TCN-[0-9]{3})-CI", entity_ref)
                if owner and owner.group(1) in materialize_histories:
                    histories_out["inactive_materialize_history"][owner.group(1)] = (
                        materialize_histories[owner.group(1)]
                    )
            elif entity is not None:
                histories_out[_HISTORY_FIELD[entity_type]][entity_ref] = entity
    # CI ownership is derived from its TCN and model owners. The helper never
    # asks the semantic owner LLM to assign CI scope refs.
    for identity, state_row in state_rows.items():
        if identity[1] != "ci" or state_row["status"] == "deleted":
            continue
        refs = state_row["scope_refs"]
        if not (set(refs) - set(current_scope_ids)):
            continue
        ci = rows_by_identity.get(identity)
        if ci is None or not isinstance(ci.get("content"), dict):
            raise InvalidInput(
                "scope removal last-active Entity snapshot is missing for CI"
            )
        if not current_scope_ids:
            transition_candidates[identity] = {
                "skill": identity[0],
                "entity_type": "ci",
                "entity_ref": identity[2],
                "resolved_scope_refs": [],
                "status": "deleted",
            }
            continue
        content = ci["content"]
        owner_ids = [
            ("test-condition-design", "tcn", content.get("tcn_id")),
            ("test-condition-design", "model", content.get("model_key")),
        ]
        owner_refs: set[str] = set()
        owner_statuses: list[str] = []
        for owner in owner_ids:
            owner_state = state_rows.get(owner)
            if owner_state is None:
                raise InvalidInput(
                    "inactive materialize history owner state is missing"
                )
            projection = transition_candidates.get(owner)
            owner_statuses.append(
                projection["status"] if projection else owner_state["status"]
            )
            owner_refs.update(
                projection["resolved_scope_refs"]
                if projection
                else owner_state["scope_refs"]
            )
        if any(status == "deleted" for status in owner_statuses):
            next_status = "deleted"
            owner_refs = set()
        else:
            next_status = (
                "inactive"
                if set(owner_refs) & set(blocked_scope_ids)
                or any(status == "inactive" for status in owner_statuses)
                else "active"
            )
        transition_candidates[identity] = {
            "skill": identity[0],
            "entity_type": "ci",
            "entity_ref": identity[2],
            "resolved_scope_refs": sorted(owner_refs),
            "status": next_status,
        }
    # A TCN becoming inactive carries forward its last validated CI mapping
    # state. Existing inactive materialization history is preserved verbatim.
    for identity, projection in transition_candidates.items():
        if identity[1] != "tcn" or projection["status"] != "inactive":
            continue
        tcn_id = identity[2]
        if tcn_id not in materialize_histories:
            owner_scope = next(
                (
                    row
                    for row in input_value["workflow_scopes"]
                    if row["skill"] == "test-condition-design"
                ),
                None,
            )
            if owner_scope is None:
                raise InvalidInput("inactive materialize history is missing")
            found = None
            for runtime in owner_scope["current_structure_state"]["runtime_results"]:
                identity_text = runtime["identity"]
                if (
                    identity_text
                    != f"test-condition-design::artifact:materialize_coverage:{tcn_id}"
                ):
                    continue
                result_payload = runtime["result"].get("payload")
                if isinstance(result_payload, dict):
                    found = {
                        "tcn_id": tcn_id,
                        "ci_entities": result_payload.get("entities"),
                        "ci_id_state": result_payload.get("ci_id_state"),
                        "target_mapping_state": result_payload.get(
                            "target_mapping_state"
                        ),
                        "semantic_ci_mapping_state": result_payload.get(
                            "semantic_ci_mapping_state"
                        ),
                        "expected_result_root_state": result_payload.get(
                            "expected_result_root_state"
                        ),
                    }
                    break
            owner_ci_rows = [
                row
                for key, row in rows_by_identity.items()
                if key[1] == "ci"
                and isinstance(row.get("content"), dict)
                and row["content"].get("tcn_id") == tcn_id
            ]
            if owner_ci_rows and (
                not isinstance(found, dict)
                or any(
                    not isinstance(found.get(field), list)
                    for field in (
                        "ci_entities",
                        "ci_id_state",
                        "target_mapping_state",
                        "semantic_ci_mapping_state",
                        "expected_result_root_state",
                    )
                )
            ):
                raise InvalidInput("inactive materialize history is missing")
            if isinstance(found, dict):
                materialize_histories[tcn_id] = found
        if tcn_id in materialize_histories:
            histories_out["inactive_materialize_history"][tcn_id] = (
                materialize_histories[tcn_id]
            )
    for identity, projection in transition_candidates.items():
        if identity[1] == "tcn" and projection["status"] == "deleted":
            histories_out["inactive_materialize_history"].pop(identity[2], None)
    # CI history output is indexed by its parent TCN, matching the generator
    # input contract, and includes state/mapping rows for inactive as well as
    # previously deleted CI IDs.
    for identity, projection in transition_candidates.items():
        if identity[1] != "ci" or projection["status"] != "inactive":
            continue
        owner = re.match(r"(TCN-[0-9]{3})-CI", identity[2])
        if owner and owner.group(1) in materialize_histories:
            histories_out["inactive_materialize_history"][owner.group(1)] = (
                materialize_histories[owner.group(1)]
            )
    expected_transitions = sorted(
        transition_candidates.values(),
        key=lambda row: (row["skill"], row["entity_type"], row["entity_ref"]),
    )
    required_resolution_keys = {
        (row["skill"], row["entity_type"], row["entity_ref"])
        for row in affected
        if row["entity_type"] != "ci"
    }
    missing_resolution = (
        required_resolution_keys - set(resolution_map) if current_scope_ids else set()
    )
    if set(resolution_map) - required_resolution_keys:
        raise InvalidInput("scope removal resolution targets a non-affected identity")
    resolution_pending = bool(missing_resolution)
    pending = expected_transitions if not resolution_pending else []
    applied_map = {}
    for row in applied:
        key = (row["skill"], row["entity_type"], row["entity_ref"])
        if key in applied_map:
            raise InvalidInput("applied scope state is duplicated")
        applied_map[key] = row
    expected_by_key = {
        (row["skill"], row["entity_type"], row["entity_ref"]): row
        for row in expected_transitions
    }
    materialization_pending = bool(expected_transitions)
    if expected_transitions and applied_map:
        materialization_pending = any(
            key not in applied_map
            or applied_map[key].get("status") != row["status"]
            or applied_map[key].get("scope_refs") != row["resolved_scope_refs"]
            for key, row in expected_by_key.items()
        )
        if set(applied_map) - set(expected_by_key):
            materialization_pending = True
    for field in inactive_ids:
        inactive_ids[field] = sorted(set(inactive_ids[field]))
    for field in histories_out:
        histories_out[field] = [
            histories_out[field][key] for key in sorted(histories_out[field])
        ]
    return {
        **inactive_ids,
        "removed_scope_ids": removed,
        "scope_removal_affected_entities": sorted(
            affected,
            key=lambda row: (row["skill"], row["entity_type"], row["entity_ref"]),
        ),
        "scope_removal_state_transitions": expected_transitions,
        "scope_removal_pending_applications": pending,
        "zero_scope_terminal": not current_scope_ids and bool(state_rows),
        "requires_semantic_resolution": resolution_pending,
        "requires_materialization": materialization_pending,
        **histories_out,
    }


def _validate_resolution_rows(
    value: Any, current_scopes: list[str]
) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise InvalidInput("scope_removal_resolutions must be an array")
    result = []
    seen = set()
    for row in value:
        if not isinstance(row, dict) or set(row) != {
            "skill",
            "entity_type",
            "entity_ref",
            "resolution",
            "resolved_scope_refs",
        }:
            raise InvalidInput("scope removal resolution schema is invalid")
        skill, entity_type, entity_ref = (
            row["skill"],
            row["entity_type"],
            row["entity_ref"],
        )
        if (
            skill not in _ENTITY_SKILLS
            or entity_type not in _ENTITY_SKILLS[skill]
            or not isinstance(entity_ref, str)
            or not _IDENTITY_RE[entity_type].fullmatch(entity_ref)
        ):
            raise InvalidInput("scope removal resolution identity is invalid")
        key = (skill, entity_type, entity_ref)
        if key in seen or row["resolution"] not in {"reuse", "deleted"}:
            raise InvalidInput("scope removal resolution is duplicated or invalid")
        seen.add(key)
        refs = _sorted_ids(row["resolved_scope_refs"], "resolved_scope_refs", _SCOPE_RE)
        if row["resolution"] == "reuse" and (
            not refs or set(refs) - set(current_scopes)
        ):
            raise InvalidInput("reuse resolution must use known current scopes")
        if row["resolution"] == "deleted" and refs:
            raise InvalidInput("deleted resolution must have no scope refs")
        result.append(dict(row))
    return result


def _validate_applied_rows(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise InvalidInput("scope_removal_applied_states must be an array")
    result = []
    seen = set()
    for row in value:
        if not isinstance(row, dict) or set(row) != {
            "skill",
            "entity_type",
            "entity_ref",
            "status",
            "scope_refs",
        }:
            raise InvalidInput("scope removal applied-state schema is invalid")
        skill, entity_type, entity_ref = (
            row["skill"],
            row["entity_type"],
            row["entity_ref"],
        )
        if (
            skill not in _ENTITY_SKILLS
            or entity_type not in _ENTITY_SKILLS[skill]
            or not isinstance(entity_ref, str)
            or not _IDENTITY_RE[entity_type].fullmatch(entity_ref)
            or row["status"] not in {"active", "inactive", "deleted"}
        ):
            raise InvalidInput("scope removal applied-state identity is invalid")
        key = (skill, entity_type, entity_ref)
        if key in seen:
            raise InvalidInput("scope removal applied-state is duplicated")
        seen.add(key)
        refs = _sorted_ids(row["scope_refs"], "scope_refs", _SCOPE_RE)
        result.append({**row, "scope_refs": refs})
    return result


def evaluate(request: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(request, dict) or set(request) != _ALLOWED_FIELDS:
        raise InvalidInput("top-level fields are missing or unknown")
    workflow_ref = request.get("workflow_ref")
    if not isinstance(workflow_ref, str) or not workflow_ref.strip():
        raise InvalidInput("workflow_ref must be non-empty")
    state_record = _validate_state_record(
        request.get("workflow_state_record"), workflow_ref
    )
    current_scopes = _sorted_ids(
        request.get("current_scope_ids"), "current_scope_ids", _SCOPE_RE
    )
    blocked_scopes = _sorted_ids(
        request.get("blocked_scope_ids"), "blocked_scope_ids", _SCOPE_RE
    )
    if set(blocked_scopes) - set(current_scopes):
        raise InvalidInput("blocked scopes must be a subset of current scopes")
    markdown = request.get("previous_qa_workflow_artifact_markdown")
    binding = state_record["binding"]
    if binding is None:
        if markdown is not None:
            raise InvalidInput("historical artifact is unexpected without a binding")
        if (
            request["scope_removal_resolutions"]
            or request["scope_removal_applied_states"]
        ):
            raise InvalidInput("scope removal rows require a committed baseline")
        return {
            "valid": True,
            "payload": {
                "inactive_tr_ids": [],
                "inactive_tcn_ids": [],
                "inactive_model_keys": [],
                "inactive_ci_ids": [],
                "inactive_tc_ids": [],
                "removed_scope_ids": [],
                "scope_removal_affected_entities": [],
                "scope_removal_state_transitions": [],
                "scope_removal_pending_applications": [],
                "zero_scope_terminal": False,
                "requires_semantic_resolution": False,
                "requires_materialization": False,
                "inactive_tr_history": [],
                "inactive_tcn_history": [],
                "inactive_model_history": [],
                "inactive_materialize_history": [],
                "inactive_tc_history": [],
            },
            "issues": [],
        }
    if markdown is None:
        raise InvalidInput("historical artifact is required by binding")
    sha = hashlib.sha256(markdown.encode("utf-8")).hexdigest()
    if sha != binding["artifact_sha256"]:
        raise InvalidInput("historical artifact SHA does not match binding")
    input_value, payload = _validate_frozen_pair(markdown, workflow_ref)
    if not isinstance(payload, dict):
        raise InvalidInput("historical workflow payload is invalid")
    resolutions = _validate_resolution_rows(
        request["scope_removal_resolutions"], current_scopes
    )
    applied = _validate_applied_rows(request["scope_removal_applied_states"])
    result = _scope_impact(
        input_value, current_scopes, blocked_scopes, resolutions, applied
    )
    return {"valid": True, "payload": result, "issues": []}


def _emit(response: dict[str, Any]) -> None:
    sys.stdout.buffer.write((canonical_json_text(response) + "\n").encode("utf-8"))


def main() -> int:
    raw = sys.stdin.buffer.read(MAX_AGGREGATE_INPUT_BYTES + 1)
    try:
        request = _load_request(raw)
        try:
            response = evaluate(request)
        except InvalidInput as exc:
            issue_type = (
                "workflow_ref_mismatch"
                if "workflow_ref" in exc.message
                else "historical_artifact_required"
                if "required by binding" in exc.message
                else "historical_artifact_unexpected"
                if "unexpected without a binding" in exc.message
                else "historical_artifact_hash_mismatch"
                if "SHA" in exc.message
                else "scope_ownership_unavailable"
                if "scope ownership unavailable" in exc.message
                else "inactive_materialize_history_missing"
                if "materialize history" in exc.message
                else "scope_removal_history_missing"
                if "last-active Entity snapshot is missing" in exc.message
                else "historical_runtime_invalid"
                if request.get("workflow_state_record", {})
                .get("state", {})
                .get("last_completed_qa_workflow_artifact")
                is not None
                else "invalid_input"
            )
            response = {
                "valid": False,
                "payload": None,
                "issues": [
                    {"issue_type": issue_type, "blocking": True, "message": exc.message}
                ],
            }
        output = (canonical_json_text(response) + "\n").encode("utf-8")
        if len(output) > MAX_AGGREGATE_INPUT_BYTES:
            response = {
                "valid": False,
                "payload": None,
                "issues": [
                    {
                        "issue_type": "limit_exceeded",
                        "blocking": True,
                        "message": "output exceeds 16 MiB",
                    }
                ],
            }
            output = (canonical_json_text(response) + "\n").encode("utf-8")
        sys.stdout.buffer.write(output)
        return 0
    except RuntimeErrorBase as exc:
        _emit(
            {
                "valid": False,
                "payload": None,
                "issues": [
                    {
                        "issue_type": exc.issue_type
                        if exc.issue_type in {"invalid_input", "limit_exceeded"}
                        else "invalid_input",
                        "blocking": True,
                        "message": exc.message,
                    }
                ],
            }
        )
        return 0
    except Exception as exc:  # pragma: no cover
        _emit(
            {
                "valid": False,
                "payload": None,
                "issues": [
                    {
                        "issue_type": "internal_error",
                        "blocking": True,
                        "message": type(exc).__name__,
                    }
                ],
            }
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
