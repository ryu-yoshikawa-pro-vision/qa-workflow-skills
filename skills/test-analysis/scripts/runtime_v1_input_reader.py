"""Read integrity-checked runtime-v1 test-analysis inputs for a v2 rebuild."""

from __future__ import annotations

import json
import re
import sys
from typing import Any

from runtime_contract import (
    ENVELOPE_VERSION,
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

SKILL = "test-analysis"
_RUNTIME_IMPL = (
    "sha256:c8fdccf927085d3a4cfaf76f18cb8b515349ff28988a4a4a8df4c2bf566fb691"
)
_GENERATOR_IMPLS = {
    "analysis_entities": "sha256:4dda5ca7d9856947aeb2acb9cb0b64dcc4e6ebf58d9ee4d21e5fd11734483190",
    "risk_matrix": "sha256:55b2789ba1ff67be8de30577665a6f5d414d792c07fc3569a5ce62da61348e3c",
    "technique_candidates": "sha256:48937114ecf991a11c5e6671bffe816ef5e1425654f3ff3a4e80a23dd197529d",
    "environment_requirements": "sha256:3ae40f063d195f72dd50c939eee0a97b3dd64aa003f5781b17d451513d197cd6",
    "change_impact": "sha256:ddbf56550a965288b573d69c2cf40febba7136f6b79f4d535d7d9e09cb3caa32",
}
_GENERATOR_CONTRACTS = {
    "analysis_entities": "analysis-entities-v1",
    "risk_matrix": "risk-matrix-v1",
    "technique_candidates": "technique-candidates-v1",
    "environment_requirements": "environment-requirements-v1",
    "change_impact": "change-impact-v1",
}
_ROOT_GENERATOR = "analysis_entities"
_ROOT_UNIT = "artifact:analysis_entities:all"
_SEMANTIC_FIELDS = (
    "test_analysis_context",
    "product_risks",
    "technique_selections",
    "change_nodes",
    "change_edges",
    "environment_requirements",
)
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


def _parse_number(token: str) -> int | float:
    if len(token) > MAX_NUMERIC_CHARS:
        raise LimitExceeded("JSON number token exceeds the frozen runtime limit")
    raise InvalidInput("unexpected numeric field in reader request")


def _validate_transport_tree(
    value: Any, *, depth: int = 0, nodes: list[int] | None = None
) -> None:
    if nodes is None:
        nodes = [0]
    nodes[0] += 1
    if nodes[0] > MAX_EXPLORATION_NODES or depth > MAX_DEPTH:
        raise LimitExceeded("JSON depth or item limit exceeded")
    if isinstance(value, str):
        if len(value.encode("utf-8")) > MAX_STRING_BYTES:
            raise LimitExceeded("JSON string exceeds the frozen runtime limit")
    elif isinstance(value, dict):
        for key, child in value.items():
            if len(key.encode("utf-8")) > MAX_STRING_BYTES:
                raise LimitExceeded("JSON key exceeds the frozen runtime limit")
            _validate_transport_tree(child, depth=depth + 1, nodes=nodes)
    elif isinstance(value, list):
        for child in value:
            _validate_transport_tree(child, depth=depth + 1, nodes=nodes)


def _load_request(raw: bytes) -> dict[str, Any]:
    if len(raw) > MAX_AGGREGATE_INPUT_BYTES:
        raise LimitExceeded("stdin exceeds 16 MiB")
    try:
        text = raw.decode("utf-8", errors="strict")
        request = json.loads(
            text,
            object_pairs_hook=_pairs,
            parse_int=_parse_number,
            parse_float=_parse_number,
            parse_constant=lambda _: (_ for _ in ()).throw(
                InvalidInput("non-finite JSON number is not allowed")
            ),
        )
    except RuntimeErrorBase:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
        raise InvalidInput("stdin must contain one strict UTF-8 JSON object") from exc
    if not isinstance(request, dict) or set(request) != {
        "operation",
        "artifact_markdown",
    }:
        raise InvalidInput(
            "request must contain exactly operation and artifact_markdown"
        )
    if request.get("operation") != "extract-validated-inputs":
        raise InvalidInput("unsupported operation")
    markdown = request.get("artifact_markdown")
    if not isinstance(markdown, str):
        raise InvalidInput("artifact_markdown must be a string")
    if len(markdown.encode("utf-8")) > MAX_AGGREGATE_INPUT_BYTES:
        raise LimitExceeded("artifact_markdown exceeds 16 MiB")
    # The artifact is the sole transport string exempt from 64 KiB. Rebuild
    # the rest of the request tree without that one value for scalar checks.
    _validate_transport_tree({"operation": request["operation"]})
    return request


def _decode_block(body: str) -> dict[str, Any]:
    raw = body.encode("utf-8")
    if len(raw) > MAX_NORMAL_INPUT_BYTES:
        raise LimitExceeded("v1 runtime block exceeds 2 MiB")
    value = strict_loads(raw, aggregate=True)
    if not isinstance(value, dict):
        raise InvalidInput("runtime block must be an object")
    return value


def _blocks(
    markdown: str,
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    inputs: dict[str, dict[str, Any]] = {}
    results: dict[str, dict[str, Any]] = {}
    for match in _BLOCK_RE.finditer(markdown):
        kind = match.group("kind")
        identity = match.group("identity")
        target = inputs if kind == "Machine Runtime Input" else results
        if identity in target:
            raise InvalidInput(f"duplicate {kind} block: {identity}")
        target[identity] = _decode_block(match.group("body"))
    return inputs, results


def _validate_pair(
    identity: str, source: dict[str, Any], result: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
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
    if (
        metadata.get("skill") != SKILL
        or identity != f"{SKILL}::{metadata.get('runtime_unit_key')}"
    ):
        raise InvalidInput("runtime input identity mismatch")
    current_metadata = dict(metadata)
    current_metadata["runtime_contract_version"] = "runtime-v2"
    _validate_metadata(current_metadata, skill=SKILL)

    required_result = {
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
    if set(result) != required_result:
        raise InvalidInput("v1 runtime result block schema is invalid")
    if (
        result.get("envelope_version") != ENVELOPE_VERSION
        or result.get("skill") != SKILL
        or result.get("runtime_contract_version") != "runtime-v1"
        or result.get("runtime_unit_key") != metadata["runtime_unit_key"]
        or result.get("model_key") != metadata["model_key"]
        or result.get("generator_contract_version")
        != metadata["generator_contract_version"]
        or not isinstance(result.get("generator"), str)
        or result.get("generator") not in _GENERATOR_IMPLS
        or result.get("generator_contract_version")
        != _GENERATOR_CONTRACTS.get(result.get("generator"))
        or result.get("runtime_implementation_fingerprint") != _RUNTIME_IMPL
        or result.get("generator_implementation_fingerprint")
        != _GENERATOR_IMPLS.get(result.get("generator"))
    ):
        raise InvalidInput("v1 runtime result identity or frozen fingerprint mismatch")
    for field in ("input_fingerprint", "generation_fingerprint"):
        if not isinstance(result.get(field), str) or not FULL_DIGEST_RE.fullmatch(
            result[field]
        ):
            raise InvalidInput(f"{field} is invalid")
    model_fp = result.get("model_fingerprint")
    if model_fp is not None and (
        not isinstance(model_fp, str) or not FULL_DIGEST_RE.fullmatch(model_fp)
    ):
        raise InvalidInput("model_fingerprint is invalid")
    for field in ("support_status", "runtime_status", "result_status"):
        if not isinstance(result.get(field), str):
            raise InvalidInput(f"{field} is invalid")
    if not isinstance(result.get("payload"), dict) or not isinstance(
        result.get("issues"), list
    ):
        raise InvalidInput("v1 result payload or issues is invalid")
    if not isinstance(result.get("runtime_required"), bool) or not isinstance(
        result.get("deterministic_generated"), bool
    ):
        raise InvalidInput("v1 result runtime flags are invalid")
    input_fp = input_fingerprint(
        SKILL,
        metadata["runtime_unit_key"],
        metadata["input_mode"],
        source["input"],
        metadata["authority_refs"],
        metadata["reference_refs"],
        metadata["selection_source"],
    )
    expected_model_fp = model_fingerprint(current_metadata, input_fp)
    upstream = upstream_entity_fingerprints(
        validate_upstream_entities(current_metadata)
    )
    if result.get("static_data_versions") != metadata["static_data_versions"]:
        raise InvalidInput("v1 static data versions do not match saved input")
    generation_fp = generation_fingerprint(
        generator=result["generator"],
        input_fp=input_fp,
        model_fp=expected_model_fp,
        runtime_contract_version="runtime-v1",
        generator_contract_version=metadata["generator_contract_version"],
        runtime_impl_fp=_RUNTIME_IMPL,
        generator_impl_fp=_GENERATOR_IMPLS[result["generator"]],
        upstream=upstream,
        static_data_versions=result["static_data_versions"],
    )
    if (
        result["input_fingerprint"] != input_fp
        or result["model_fingerprint"] != expected_model_fp
        or result["generation_fingerprint"] != generation_fp
        or result["upstream_entity_fingerprints"] != upstream
        or result["upstream_runtime_units"]
        != canonicalize(
            metadata["upstream_runtime_units"], parent_key="upstream_runtime_units"
        )
    ):
        raise InvalidInput(
            "v1 runtime fingerprints or dependency projection are inconsistent"
        )
    return metadata, source["input"]


def extract_validated_inputs(markdown: str) -> dict[str, Any]:
    inputs, results = _blocks(markdown)
    if not inputs or set(inputs) != set(results):
        raise InvalidInput("v1 runtime input/result pairs are missing or incomplete")
    rows: list[dict[str, Any]] = []
    root_found = False
    for identity in sorted(inputs):
        metadata, input_value = _validate_pair(
            identity, inputs[identity], results[identity]
        )
        unit = metadata["runtime_unit_key"]
        generator = results[identity]["generator"]
        if unit == _ROOT_UNIT:
            if generator != _ROOT_GENERATOR:
                raise InvalidInput("test-analysis root runtime generator is invalid")
            root_found = True
            semantic = {
                field: input_value[field]
                for field in _SEMANTIC_FIELDS
                if field in input_value
            }
            if set(semantic) != set(_SEMANTIC_FIELDS):
                raise InvalidInput("root v1 semantic input is incomplete")
            normalized = semantic
        else:
            normalized = input_value
        rows.append(
            {
                "generator": generator,
                "runtime_unit_key": unit,
                "model_key": metadata["model_key"],
                "normalized_input": canonicalize(normalized),
            }
        )
    if not root_found:
        raise InvalidInput("test-analysis root runtime pair is missing")
    return {
        "valid": True,
        "source_runtime_contract_version": "runtime-v1",
        "normalized_runtime_inputs": rows,
        "issues": [],
    }


def _emit(response: dict[str, Any]) -> None:
    sys.stdout.buffer.write((canonical_json_text(response) + "\n").encode("utf-8"))


def main() -> int:
    raw = sys.stdin.buffer.read(MAX_AGGREGATE_INPUT_BYTES + 1)
    try:
        request = _load_request(raw)
        response = extract_validated_inputs(request["artifact_markdown"])
        output = (canonical_json_text(response) + "\n").encode("utf-8")
        encoded = output
        if len(encoded) > MAX_AGGREGATE_INPUT_BYTES:
            raise LimitExceeded("response exceeds 16 MiB")
        sys.stdout.buffer.write(output)
        return 0
    except RuntimeErrorBase as exc:
        _emit(
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
        return 0
    except Exception as exc:  # pragma: no cover - defensive CLI boundary
        _emit(
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
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
