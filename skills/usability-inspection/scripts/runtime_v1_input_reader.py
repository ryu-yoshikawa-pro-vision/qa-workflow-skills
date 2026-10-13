"""Read the frozen v1 inspection runtime input without claiming currentness."""

from __future__ import annotations

import json
import re
import sys
from typing import Any

from runtime_contract import (
    FULL_DIGEST_RE,
    MAX_AGGREGATE_INPUT_BYTES,
    MAX_DEPTH,
    MAX_EXPLORATION_NODES,
    MAX_NORMAL_INPUT_BYTES,
    MAX_NUMERIC_CHARS,
    MAX_STRING_BYTES,
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

SKILL = "usability-inspection"
_RUNTIME_IMPL = (
    "sha256:c8fdccf927085d3a4cfaf76f18cb8b515349ff28988a4a4a8df4c2bf566fb691"
)
_GENERATOR_IMPL = (
    "sha256:f0e85e6489986f75f20f922ccded81457721887e92e6927da6e626218a1a9fe1"
)
_GENERATOR = "inspection_runtime"
_ROOT_UNIT = "artifact:inspection_runtime:all"
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


def _reject_number(token: str) -> Any:
    if len(token) > MAX_NUMERIC_CHARS:
        raise LimitExceeded("JSON number exceeds the frozen runtime limit")
    raise InvalidInput("unexpected numeric field in reader request")


def _check_tree(value: Any, *, depth: int = 0, nodes: list[int] | None = None) -> None:
    nodes = nodes if nodes is not None else [0]
    nodes[0] += 1
    if nodes[0] > MAX_EXPLORATION_NODES or depth > MAX_DEPTH:
        raise LimitExceeded("JSON depth or item limit exceeded")
    if isinstance(value, str) and len(value.encode("utf-8")) > MAX_STRING_BYTES:
        raise LimitExceeded("JSON string exceeds 64 KiB")
    if isinstance(value, dict):
        for key, child in value.items():
            if len(key.encode("utf-8")) > MAX_STRING_BYTES:
                raise LimitExceeded("JSON key exceeds 64 KiB")
            _check_tree(child, depth=depth + 1, nodes=nodes)
    elif isinstance(value, list):
        for child in value:
            _check_tree(child, depth=depth + 1, nodes=nodes)


def _load_request(raw: bytes) -> dict[str, Any]:
    if len(raw) > MAX_AGGREGATE_INPUT_BYTES:
        raise LimitExceeded("stdin exceeds 16 MiB")
    try:
        request = json.loads(
            raw.decode("utf-8", errors="strict"),
            object_pairs_hook=_pairs,
            parse_int=_reject_number,
            parse_float=_reject_number,
            parse_constant=lambda _: (_ for _ in ()).throw(
                InvalidInput("invalid JSON number")
            ),
        )
    except RuntimeErrorBase:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
        raise InvalidInput("stdin must contain one strict JSON object") from exc
    if not isinstance(request, dict) or set(request) != {
        "operation",
        "artifact_markdown",
    }:
        raise InvalidInput(
            "request must contain exactly operation and artifact_markdown"
        )
    if request["operation"] != "extract-validated-inputs" or not isinstance(
        request["artifact_markdown"], str
    ):
        raise InvalidInput("operation or artifact_markdown is invalid")
    if len(request["artifact_markdown"].encode("utf-8")) > MAX_AGGREGATE_INPUT_BYTES:
        raise LimitExceeded("artifact_markdown exceeds 16 MiB")
    _check_tree({"operation": request["operation"]})
    return request


def _decode(body: str) -> dict[str, Any]:
    raw = body.encode("utf-8")
    if len(raw) > MAX_NORMAL_INPUT_BYTES:
        raise LimitExceeded("v1 runtime block exceeds 2 MiB")
    value = strict_loads(raw, aggregate=True)
    if not isinstance(value, dict):
        raise InvalidInput("runtime block must be an object")
    return value


def _validate_pair(
    identity: str, source: dict[str, Any], result: dict[str, Any]
) -> dict[str, Any]:
    if set(source) != {"metadata", "input"} or not isinstance(
        source.get("input"), dict
    ):
        raise InvalidInput("v1 runtime input block schema is invalid")
    metadata = source["metadata"]
    if (
        not isinstance(metadata, dict)
        or metadata.get("runtime_contract_version") != "runtime-v1"
    ):
        raise InvalidInput("source runtime is not frozen runtime-v1")
    unit = metadata.get("runtime_unit_key")
    if metadata.get("skill") != SKILL or identity != f"{SKILL}::{unit}":
        raise InvalidInput("runtime input identity mismatch")
    current_metadata = dict(metadata)
    current_metadata["runtime_contract_version"] = "runtime-v2"
    _validate_metadata(current_metadata, skill=SKILL)
    required = {
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
    if set(result) != required:
        raise InvalidInput("v1 runtime result block schema is invalid")
    if (
        result.get("envelope_version") != "1"
        or result.get("skill") != SKILL
        or result.get("runtime_contract_version") != "runtime-v1"
        or result.get("generator_contract_version")
        != metadata["generator_contract_version"]
        or result.get("generator") != _GENERATOR
        or result.get("runtime_unit_key") != unit
        or result.get("model_key") != metadata["model_key"]
        or result.get("runtime_implementation_fingerprint") != _RUNTIME_IMPL
        or result.get("generator_implementation_fingerprint") != _GENERATOR_IMPL
    ):
        raise InvalidInput(
            "v1 result identity or frozen implementation fingerprint mismatch"
        )
    for field in ("input_fingerprint", "generation_fingerprint"):
        if not isinstance(result.get(field), str) or not FULL_DIGEST_RE.fullmatch(
            result[field]
        ):
            raise InvalidInput(f"{field} is invalid")
    if not isinstance(result.get("payload"), dict) or not isinstance(
        result.get("issues"), list
    ):
        raise InvalidInput("v1 result payload is invalid")
    if not isinstance(result.get("runtime_required"), bool) or not isinstance(
        result.get("deterministic_generated"), bool
    ):
        raise InvalidInput("v1 result flags are invalid")
    input_fp = input_fingerprint(
        SKILL,
        unit,
        metadata["input_mode"],
        source["input"],
        metadata["authority_refs"],
        metadata["reference_refs"],
        metadata["selection_source"],
    )
    expected_model = model_fingerprint(current_metadata, input_fp)
    upstream = upstream_entity_fingerprints(
        validate_upstream_entities(current_metadata)
    )
    if result.get("static_data_versions") != metadata["static_data_versions"]:
        raise InvalidInput("static data version mismatch")
    expected_generation = generation_fingerprint(
        generator=_GENERATOR,
        input_fp=input_fp,
        model_fp=expected_model,
        runtime_contract_version="runtime-v1",
        generator_contract_version=metadata["generator_contract_version"],
        runtime_impl_fp=_RUNTIME_IMPL,
        generator_impl_fp=_GENERATOR_IMPL,
        upstream=upstream,
        static_data_versions=result["static_data_versions"],
    )
    if (
        result["input_fingerprint"] != input_fp
        or result["model_fingerprint"] != expected_model
        or result["generation_fingerprint"] != expected_generation
        or result["upstream_entity_fingerprints"] != upstream
        or result["upstream_runtime_units"]
        != canonicalize(
            metadata["upstream_runtime_units"], parent_key="upstream_runtime_units"
        )
    ):
        raise InvalidInput("v1 runtime fingerprint or dependency projection mismatch")
    return source["input"]


def extract_validated_inputs(markdown: str) -> dict[str, Any]:
    inputs: dict[str, dict[str, Any]] = {}
    results: dict[str, dict[str, Any]] = {}
    for match in _BLOCK_RE.finditer(markdown):
        kind, identity = match.group("kind"), match.group("identity")
        target = inputs if kind == "Machine Runtime Input" else results
        if identity in target:
            raise InvalidInput(f"duplicate {kind} block")
        target[identity] = _decode(match.group("body"))
    if not inputs or set(inputs) != set(results):
        raise InvalidInput("v1 runtime input/result pair is missing or incomplete")
    rows = []
    root_found = False
    for identity in sorted(inputs):
        source = inputs[identity]
        metadata = source.get("metadata") if isinstance(source, dict) else None
        if not isinstance(metadata, dict):
            raise InvalidInput("runtime metadata is missing")
        normalized = _validate_pair(identity, source, results[identity])
        unit = metadata["runtime_unit_key"]
        if unit == _ROOT_UNIT:
            root_found = True
        rows.append(
            {
                "generator": _GENERATOR,
                "runtime_unit_key": unit,
                "model_key": metadata["model_key"],
                "normalized_input": canonicalize(normalized),
            }
        )
    if not root_found:
        raise InvalidInput("inspection root runtime pair is missing")
    return {
        "valid": True,
        "source_runtime_contract_version": "runtime-v1",
        "normalized_runtime_inputs": rows,
        "issues": [],
    }


def main() -> int:
    raw = sys.stdin.buffer.read(MAX_AGGREGATE_INPUT_BYTES + 1)
    try:
        response = extract_validated_inputs(_load_request(raw)["artifact_markdown"])
        output = (canonical_json_text(response) + "\n").encode("utf-8")
        if len(output) > MAX_AGGREGATE_INPUT_BYTES:
            raise LimitExceeded("response exceeds 16 MiB")
        sys.stdout.buffer.write(output)
        return 0
    except RuntimeErrorBase as exc:
        sys.stdout.buffer.write(
            (
                canonical_json_text(
                    {
                        "valid": False,
                        "source_runtime_contract_version": "runtime-v1",
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
                + "\n"
            ).encode("utf-8")
        )
        return 0
    except Exception as exc:  # pragma: no cover
        sys.stdout.buffer.write(
            (
                canonical_json_text(
                    {
                        "valid": False,
                        "source_runtime_contract_version": "runtime-v1",
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
                + "\n"
            ).encode("utf-8")
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
