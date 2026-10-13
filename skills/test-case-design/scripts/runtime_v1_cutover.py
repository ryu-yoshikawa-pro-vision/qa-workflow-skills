"""Project frozen v1 TC identity into a complete v2 case-structure input."""

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

SKILL = "test-case-design"
GENERATOR = "case_structure"
UNIT = "artifact:case_structure:all"
_RUNTIME_IMPL = (
    "sha256:c8fdccf927085d3a4cfaf76f18cb8b515349ff28988a4a4a8df4c2bf566fb691"
)
_GENERATOR_IMPL = (
    "sha256:ed9b27273306a21f3f522a97e5d8bd4cc3065bacc322a1e64cd240da60e71d8c"
)
_TC_RE = re.compile(r"TC-[0-9]{3}")
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


def _decode(body: str) -> dict[str, Any]:
    raw = body.encode("utf-8")
    if len(raw) > MAX_NORMAL_INPUT_BYTES:
        raise LimitExceeded("v1 Machine Runtime block exceeds 2 MiB")
    value = strict_loads(raw, aggregate=True)
    if not isinstance(value, dict):
        raise InvalidInput("Machine Runtime block must be an object")
    return value


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
    if (
        value.get("operation") != "cutover"
        or value.get("phase") != "all"
        or value.get("current_v2_artifact_markdown") is not None
    ):
        raise InvalidInput("TC cutover accepts phase=all from a v1 artifact")
    if not isinstance(value.get("artifact_markdown"), str):
        raise InvalidInput("artifact_markdown is required")
    if len(value["artifact_markdown"].encode("utf-8")) > MAX_AGGREGATE_INPUT_BYTES:
        raise LimitExceeded("artifact_markdown exceeds 16 MiB")
    return value


def _extract(markdown: str) -> tuple[dict[str, Any], dict[str, Any]]:
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
        raise InvalidInput("TC cutover requires one complete root pair")
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
    v2_metadata = dict(metadata)
    v2_metadata["runtime_contract_version"] = "runtime-v2"
    _validate_metadata(v2_metadata, skill=SKILL)
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
        or result.get("skill") != SKILL
        or result.get("runtime_contract_version") != "runtime-v1"
        or result.get("generator_contract_version") != "case-structure-v1"
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
    expected_model = model_fingerprint(v2_metadata, expected_input)
    upstream = upstream_entity_fingerprints(validate_upstream_entities(v2_metadata))
    if result.get("static_data_versions") != metadata.get("static_data_versions"):
        raise InvalidInput("v1 static data versions differ from input")
    expected_generation = generation_fingerprint(
        generator=GENERATOR,
        input_fp=expected_input,
        model_fp=expected_model,
        runtime_contract_version="runtime-v1",
        generator_contract_version="case-structure-v1",
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
    return input_value, result


def _state(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise InvalidInput("v1 tc_id_state must be an array")
    state: dict[str, str] = {}
    for row in value:
        if (
            not isinstance(row, dict)
            or set(row) != {"tc_id", "status"}
            or not isinstance(row.get("tc_id"), str)
            or not _TC_RE.fullmatch(row["tc_id"])
            or row.get("status") not in {"active", "deleted"}
            or row["tc_id"] in state
        ):
            raise InvalidInput("v1 tc_id_state row is invalid or duplicated")
        state[row["tc_id"]] = row["status"]
    return [
        {"tc_id": ref, "status": state[ref], "scope_refs": []} for ref in sorted(state)
    ]


def cutover(markdown: str) -> dict[str, Any]:
    input_value, result = _extract(markdown)
    source_fields = {
        "test_conditions",
        "coverage_items",
        "environment_requirements",
        "test_data_requirements",
        "test_cases",
        "dispositions",
        "previous_tc_ids",
        "update_scope_tc_ids",
    }
    if frozenset(input_value) not in {
        frozenset(source_fields),
        frozenset(source_fields | {"legacy_tc_ids"}),
    }:
        raise InvalidInput("v1 case-structure input schema is invalid")
    states = _state(result["payload"].get("tc_id_state"))
    state_map = {row["tc_id"]: row["status"] for row in states}
    drafts = input_value["test_cases"]
    mapping = result["payload"].get("tc_id_map")
    if not isinstance(drafts, list) or not isinstance(mapping, list):
        raise InvalidInput("v1 TC drafts or tc_id_map are missing")
    draft_map: dict[str, dict[str, Any]] = {}
    for row in drafts:
        if (
            not isinstance(row, dict)
            or not isinstance(row.get("draft_key"), str)
            or row["draft_key"] in draft_map
        ):
            raise InvalidInput("v1 TC draft_key is invalid or duplicated")
        draft_map[row["draft_key"]] = row
    by_key: dict[str, dict[str, Any]] = {}
    used_ids: set[str] = set()
    for row in mapping:
        if (
            not isinstance(row, dict)
            or set(row) != {"draft_key", "tc_id", "identity_action"}
            or row.get("identity_action") not in {"reuse", "new"}
        ):
            raise InvalidInput("v1 tc_id_map row schema is invalid")
        key, tc_id = row.get("draft_key"), row.get("tc_id")
        if (
            not isinstance(key, str)
            or key not in draft_map
            or key in by_key
            or not isinstance(tc_id, str)
            or not _TC_RE.fullmatch(tc_id)
            or tc_id in used_ids
            or state_map.get(tc_id) != "active"
        ):
            raise InvalidInput(
                "v1 tc_id_map identity is missing, extra, or inconsistent"
            )
        by_key[key] = row
        used_ids.add(tc_id)
    if set(by_key) != set(draft_map):
        raise InvalidInput("v1 draft_key and tc_id_map are not an exact join")
    normalized_drafts = []
    for key in sorted(draft_map):
        draft = dict(draft_map[key])
        draft.update({"identity_action": "reuse", "reuse_id": by_key[key]["tc_id"]})
        normalized_drafts.append(canonicalize(draft))
    normalized = {
        field: input_value[field]
        for field in source_fields
        - {"previous_tc_ids", "update_scope_tc_ids", "test_cases"}
    }
    normalized.update(
        {
            "test_cases": normalized_drafts,
            "previous_tc_ids": states,
            "update_scope_tc_ids": [
                row["tc_id"] for row in states if row["status"] == "active"
            ],
            "inactive_tc_ids": [],
            "inactive_tc_history": [],
            "zero_scope_terminal": False,
        }
    )
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
                "normalized_input": canonicalize(normalized),
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
        response = cutover(request["artifact_markdown"])
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
