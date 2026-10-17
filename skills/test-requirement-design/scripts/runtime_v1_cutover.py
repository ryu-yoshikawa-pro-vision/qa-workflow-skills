"""Project frozen v1 TR identity into one complete v2 requirement input."""

from __future__ import annotations

import json
import re
import sys
from typing import Any

from runtime_contract import (
    FULL_DIGEST_RE,
    MAX_AGGREGATE_INPUT_BYTES,
    MAX_NORMAL_INPUT_BYTES,
    InvalidInput,
    LimitExceeded,
    RuntimeErrorBase,
    _validate_metadata,
    canonical_json_text,
    canonicalize,
    generation_fingerprint,
    input_fingerprint,
    model_fingerprint,
    strict_loads,
    upstream_entity_fingerprints,
    validate_upstream_entities,
)

SKILL = "test-requirement-design"
GENERATOR = "requirement_structure"
UNIT = "artifact:requirement_structure:all"
_RUNTIME_IMPL = (
    "sha256:c8fdccf927085d3a4cfaf76f18cb8b515349ff28988a4a4a8df4c2bf566fb691"
)
_GENERATOR_IMPL = (
    "sha256:1f58df5515e09c69b2670bcbc7375fe8d87e5ca10c6638d3898603c956702318"
)
_TR_RE = re.compile(r"TR-[0-9]{3}")
_BLOCK_RE = re.compile(
    r"^### (?P<kind>Machine Runtime Input|Machine Runtime Result): "
    r"(?P<identity>[^\r\n]+)\r?\n\r?\n```json\r?\n(?P<body>.*?)\r?\n```",
    re.MULTILINE | re.DOTALL,
)


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise InvalidInput(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _request(raw: bytes) -> dict[str, Any]:
    if len(raw) > MAX_AGGREGATE_INPUT_BYTES:
        raise LimitExceeded("stdin exceeds 16 MiB")
    try:
        value = json.loads(
            raw.decode("utf-8", errors="strict"), object_pairs_hook=_pairs
        )
    except RuntimeErrorBase:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
        raise InvalidInput("stdin must be one strict UTF-8 JSON object") from exc
    if not isinstance(value, dict) or set(value) != {
        "operation",
        "phase",
        "artifact_markdown",
        "current_v2_artifact_markdown",
    }:
        raise InvalidInput("cutover request fields are invalid")
    if value.get("operation") != "cutover" or value.get("phase") != "all":
        raise InvalidInput("TRD cutover accepts operation=cutover and phase=all only")
    for field in ("artifact_markdown", "current_v2_artifact_markdown"):
        if value[field] is not None and not isinstance(value[field], str):
            raise InvalidInput(f"{field} must be a string or null")
    if value["current_v2_artifact_markdown"] is not None:
        raise InvalidInput("TRD cutover must start from the frozen v1 artifact")
    if not isinstance(value["artifact_markdown"], str):
        raise InvalidInput("artifact_markdown is required")
    if len(value["artifact_markdown"].encode("utf-8")) > MAX_AGGREGATE_INPUT_BYTES:
        raise LimitExceeded("artifact_markdown exceeds 16 MiB")
    return value


def _decode(body: str) -> dict[str, Any]:
    raw = body.encode("utf-8")
    if len(raw) > MAX_NORMAL_INPUT_BYTES:
        raise LimitExceeded("v1 Machine Runtime block exceeds 2 MiB")
    value = strict_loads(raw, aggregate=True)
    if not isinstance(value, dict):
        raise InvalidInput("Machine Runtime block must be an object")
    return value


def _source_pair(markdown: str) -> tuple[dict[str, Any], dict[str, Any]]:
    blocks: dict[str, dict[str, Any]] = {}
    for match in _BLOCK_RE.finditer(markdown):
        identity = match.group("identity")
        if identity in blocks:
            raise InvalidInput("runtime pair contains duplicate identity")
        blocks[identity] = _decode(match.group("body"))
    identity = f"{SKILL}::{UNIT}"
    if set(blocks) != {identity}:
        raise InvalidInput("TRD v1 cutover requires exactly one root input/result pair")
    source = blocks[identity]
    if set(source) != {"metadata", "input"} or not isinstance(source["input"], dict):
        raise InvalidInput("v1 runtime input block schema is invalid")
    metadata = source["metadata"]
    if (
        not isinstance(metadata, dict)
        or metadata.get("runtime_contract_version") != "runtime-v1"
    ):
        raise InvalidInput("cutover source is not runtime-v1")
    if metadata.get("skill") != SKILL or metadata.get("runtime_unit_key") != UNIT:
        raise InvalidInput("cutover source pair identity mismatch")
    v2_metadata = dict(metadata)
    v2_metadata["runtime_contract_version"] = "runtime-v2"
    _validate_metadata(v2_metadata, skill=SKILL)
    result = blocks[identity]
    input_body = source["input"]
    # The input block was overwritten in blocks above; the sibling is recovered
    # directly from the artifact by the caller-specific parser below.
    return metadata, {"input_body": input_body, "result": result}


def _extract(markdown: str) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    inputs: dict[str, dict[str, Any]] = {}
    results: dict[str, dict[str, Any]] = {}
    for match in _BLOCK_RE.finditer(markdown):
        kind, identity = match.group("kind"), match.group("identity")
        target = inputs if kind == "Machine Runtime Input" else results
        if identity in target:
            raise InvalidInput(f"duplicate {kind} block")
        target[identity] = _decode(match.group("body"))
    identity = f"{SKILL}::{UNIT}"
    if set(inputs) != {identity} or set(results) != {identity}:
        raise InvalidInput("TRD v1 cutover requires one complete root pair")
    source, result = inputs[identity], results[identity]
    if set(source) != {"metadata", "input"} or not isinstance(
        source.get("input"), dict
    ):
        raise InvalidInput("v1 runtime input block schema is invalid")
    metadata = source["metadata"]
    if (
        not isinstance(metadata, dict)
        or metadata.get("runtime_contract_version") != "runtime-v1"
        or metadata.get("skill") != SKILL
        or metadata.get("runtime_unit_key") != UNIT
    ):
        raise InvalidInput("v1 source metadata identity/version is invalid")
    current_metadata = dict(metadata)
    current_metadata["runtime_contract_version"] = "runtime-v2"
    _validate_metadata(current_metadata, skill=SKILL)
    expected_fields = {
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
    if set(result) != expected_fields or (
        result.get("envelope_version") != "1"
        or result.get("skill") != SKILL
        or result.get("runtime_contract_version") != "runtime-v1"
        or result.get("generator_contract_version") != "requirement-structure-v1"
        or result.get("generator") != GENERATOR
        or result.get("runtime_unit_key") != UNIT
        or result.get("runtime_implementation_fingerprint") != _RUNTIME_IMPL
        or result.get("generator_implementation_fingerprint") != _GENERATOR_IMPL
        or not isinstance(result.get("payload"), dict)
    ):
        raise InvalidInput(
            "v1 result identity, schema, or frozen implementation fingerprint is invalid"
        )
    for field in ("input_fingerprint", "generation_fingerprint"):
        if not isinstance(result.get(field), str) or not FULL_DIGEST_RE.fullmatch(
            result[field]
        ):
            raise InvalidInput(f"{field} is invalid")
    input_value = source["input"]
    expected_input = input_fingerprint(
        SKILL,
        UNIT,
        metadata["input_mode"],
        input_value,
        metadata["authority_refs"],
        metadata["reference_refs"],
        metadata["selection_source"],
    )
    expected_model = model_fingerprint(current_metadata, expected_input)
    upstream = upstream_entity_fingerprints(
        validate_upstream_entities(current_metadata)
    )
    if result.get("static_data_versions") != metadata.get("static_data_versions"):
        raise InvalidInput("v1 static data versions differ from input")
    expected_generation = generation_fingerprint(
        generator=GENERATOR,
        input_fp=expected_input,
        model_fp=expected_model,
        runtime_contract_version="runtime-v1",
        generator_contract_version="requirement-structure-v1",
        runtime_impl_fp=_RUNTIME_IMPL,
        generator_impl_fp=_GENERATOR_IMPL,
        upstream=upstream,
        static_data_versions=result["static_data_versions"],
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
    ):
        raise InvalidInput("v1 input/result fingerprint or dependency mismatch")
    return metadata, input_value, result


def _state_rows(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list):
        raise InvalidInput("v1 tr_id_state must be an array")
    rows: dict[str, str] = {}
    for row in value:
        if (
            not isinstance(row, dict)
            or set(row) != {"tr_id", "status"}
            or not isinstance(row.get("tr_id"), str)
            or not _TR_RE.fullmatch(row["tr_id"])
            or row.get("status") not in {"active", "deleted"}
            or row["tr_id"] in rows
        ):
            raise InvalidInput("v1 tr_id_state row is invalid or duplicated")
        rows[row["tr_id"]] = row["status"]
    return [
        {"tr_id": ref, "status": rows[ref], "scope_refs": []} for ref in sorted(rows)
    ]


def cutover(request: dict[str, Any]) -> dict[str, Any]:
    metadata, input_value, result = _extract(request["artifact_markdown"])
    payload = result["payload"]
    source_fields = {
        "authorities",
        "risks",
        "test_requirements",
        "dispositions",
        "previous_tr_ids",
        "update_scope_tr_ids",
    }
    if frozenset(input_value) not in {
        frozenset(source_fields),
        frozenset(source_fields | {"legacy_tr_ids"}),
    }:
        raise InvalidInput("v1 requirement-structure input schema is invalid")
    state = _state_rows(payload.get("tr_id_state"))
    state_map = {row["tr_id"]: row["status"] for row in state}
    drafts = input_value.get("test_requirements")
    mapping = payload.get("tr_id_map")
    if not isinstance(drafts, list) or not isinstance(mapping, list):
        raise InvalidInput("v1 TR drafts or tr_id_map are missing")
    draft_map: dict[str, dict[str, Any]] = {}
    for row in drafts:
        if (
            not isinstance(row, dict)
            or not isinstance(row.get("draft_key"), str)
            or row["draft_key"] in draft_map
        ):
            raise InvalidInput("v1 TR draft_key is invalid or duplicated")
        draft_map[row["draft_key"]] = row
    by_key: dict[str, dict[str, Any]] = {}
    used_ids: set[str] = set()
    for row in mapping:
        if (
            not isinstance(row, dict)
            or set(row) != {"draft_key", "tr_id", "identity_action"}
            or row.get("identity_action") not in {"reuse", "new"}
        ):
            raise InvalidInput("v1 tr_id_map row schema is invalid")
        key, tr_id = row.get("draft_key"), row.get("tr_id")
        if (
            not isinstance(key, str)
            or key not in draft_map
            or key in by_key
            or not isinstance(tr_id, str)
            or not _TR_RE.fullmatch(tr_id)
            or tr_id in used_ids
            or state_map.get(tr_id) != "active"
        ):
            raise InvalidInput(
                "v1 tr_id_map identity is missing, extra, or inconsistent"
            )
        prior = draft_map[key]
        if row["identity_action"] == "reuse" and prior.get("reuse_id") not in {
            None,
            tr_id,
        }:
            raise InvalidInput("v1 reused TR mapping differs from saved input")
        if row["identity_action"] == "new" and prior.get("reuse_id") not in {None, ""}:
            raise InvalidInput("v1 new TR unexpectedly has a reuse_id")
        by_key[key] = row
        used_ids.add(tr_id)
    if set(by_key) != set(draft_map):
        raise InvalidInput("v1 draft_key and tr_id_map are not an exact join")
    normalized_drafts = []
    for key in sorted(draft_map):
        row = dict(draft_map[key])
        row.update(
            {
                "identity_action": "reuse",
                "reuse_id": by_key[key]["tr_id"],
                "acceptance_refs": [],
                "scope_refs": [],
            }
        )
        normalized_drafts.append(canonicalize(row))
    active_ids = [row["tr_id"] for row in state if row["status"] == "active"]
    normalized_input = {
        "authorities": input_value["authorities"],
        "risks": input_value["risks"],
        "acceptance_criteria": [],
        "scope_ids": [],
        "test_requirements": normalized_drafts,
        "dispositions": input_value["dispositions"],
        "previous_tr_ids": state,
        "update_scope_tr_ids": active_ids,
        "inactive_tr_ids": [],
        "inactive_tr_history": [],
        "zero_scope_terminal": False,
    }
    return {
        "valid": True,
        "phase": "all",
        "phase_complete": True,
        "source_runtime_contract_version": "runtime-v1",
        "source_entity_schema_version": "entity-state-v1",
        "normalized_runtime_inputs": [
            {
                "generator": GENERATOR,
                "runtime_unit_key": UNIT,
                "model_key": None,
                "normalized_input": canonicalize(normalized_input),
            }
        ],
        "issues": [],
    }


def _emit(response: dict[str, Any]) -> None:
    sys.stdout.buffer.write((canonical_json_text(response) + "\n").encode("utf-8"))


def main() -> int:
    raw = sys.stdin.buffer.read(MAX_AGGREGATE_INPUT_BYTES + 1)
    try:
        request = _request(raw)
        response = cutover(request)
        output = (canonical_json_text(response) + "\n").encode("utf-8")
        if len(output) > MAX_AGGREGATE_INPUT_BYTES:
            raise LimitExceeded("response exceeds 16 MiB")
        sys.stdout.buffer.write(output)
        return 0
    except RuntimeErrorBase as exc:
        _emit(
            {
                "valid": False,
                "phase": "all",
                "phase_complete": False,
                "source_runtime_contract_version": "runtime-v1",
                "source_entity_schema_version": "entity-state-v1",
                "normalized_runtime_inputs": [],
                "issues": [
                    {
                        "issue_type": exc.issue_type,
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
                "phase": "all",
                "phase_complete": False,
                "source_runtime_contract_version": "runtime-v1",
                "source_entity_schema_version": "entity-state-v1",
                "normalized_runtime_inputs": [],
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
