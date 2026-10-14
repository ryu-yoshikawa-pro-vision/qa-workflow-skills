"""Project frozen v1 TCD evidence into complete runtime-v2 generator inputs."""

from __future__ import annotations

import json
import re
import sys
from typing import Any

from runtime_contract import (
    FULL_DIGEST_RE,
    MAX_AGGREGATE_INPUT_BYTES,
    MAX_NORMAL_INPUT_BYTES,
    MAX_STDOUT_BYTES,
    InvalidInput,
    LimitExceeded,
    RuntimeErrorBase,
    _reject_surrogates,
    _scan_json_depth,
    _scan_json_string_limits,
    _validate_runtime_pair,
    canonical_json_text,
    canonicalize,
    current_model_result_row,
    extract_machine_blocks,
    generation_fingerprint,
    input_fingerprint,
    model_fingerprint,
    sha256_digest,
    strict_loads,
)

SKILL = "test-condition-design"
CONDITION_GENERATOR = "condition_structure"
CONDITION_UNIT = "artifact:condition_structure:all"
TDR_GENERATOR = "test_data_requirements"
TDR_UNIT = "artifact:test_data_requirements:all"
MATERIALIZE_GENERATOR = "materialize_coverage"
PHASES = (
    "condition-structure",
    "models",
    "test-data-requirements",
    "materialize-coverage",
)

_RUNTIME_IMPL = (
    "sha256:c8fdccf927085d3a4cfaf76f18cb8b515349ff28988a4a4a8df4c2bf566fb691"
)
_GENERATOR_IMPLS = {
    "condition_structure": "sha256:e30e7323660c8ff21c65614cd8c820c13249bd112aa99349b6b0ecce6549a847",
    "test_data_requirements": "sha256:6c8779ee77b9126971ef5eb5a1f77b66dbf8a94f0bc6618179805330f7c15faa",
    "materialize_coverage": "sha256:e0553cbedd666ef3f218c43490d9c15131e0e020b3bfabdb9d5a5e4ce21fd02d",
    "equivalence_partitions": "sha256:bbc41de9a5937edb386f1c105b75915587f935d6d26f06652466c9b19331be21",
    "bva": "sha256:c84bcf26cc6141bded0f2aff1b0391fcf608a19e20ea7f254454d1f368ae7bfd",
    "domain_testing": "sha256:6cdf5adbb0e8725c2349fc4fc23e1d9eb41ba19ebc528084d57949e815e21eb7",
    "decision_table": "sha256:34a54688798ad3e399289cecf2b8770c12a1c07183c0ddb128cf421c9ae7cd83",
    "combinatorial": "sha256:fc679be61c4b507b55ae4363b713d04eca60ae90bda0dc0d76ff3cfcf028fab3",
    "classification_tree": "sha256:5f9b94943f23dd24bf3ff4b9765dde4fd888fe3c286b93d09c2742c92a093257",
    "state_transition": "sha256:740ab81d2adef8488a478d88a660b528b5e6485fcb05df36ec2e680126d255d6",
    "flow_paths": "sha256:704b807355c8f9f5889e3b67114bd98775053799a94c29f3a1c89ff2e62778ee",
    "crud_matrix": "sha256:8c38b95235360d4cf26eb6310564accc7d995e0aa99fbdf0934447009d372eee",
    "cause_effect": "sha256:534e0b881b9f22e30c8a88c40cb29a240e55f67ab08f9ef1bfbe9096a66a1627",
    "grammar_cases": "sha256:121b096bb3dcd2fc89c85f654fcd4e91bdff65796c572fe381a370ab81529528",
    "schema_cases": "sha256:4f509db4d094b4dadb11e6691de9fc4515d5bbbaa38ef5096f319a69ee74599a",
    "ui_pattern_candidates": "sha256:ebbbd8515a2a392375a70ff614b436e812d7df0b1f19ed0a5d66e9459f538b19",
    "random_testing": "sha256:961edbb3f95333d295f82bb166e759935e5a8853b150cc613e16aedf88c746dc",
    "metamorphic": "sha256:cbb03b314d2c459e15f312f23417e419fa8c33c2400513ab1d0be11995ee5a3a",
}
_MODEL_GENERATORS = {
    "ep": "equivalence_partitions",
    "bva": "bva",
    "domain": "domain_testing",
    "decision": "decision_table",
    "comb": "combinatorial",
    "classification": "classification_tree",
    "state": "state_transition",
    "flow": "flow_paths",
    "crud": "crud_matrix",
    "cause-effect": "cause_effect",
    "syntax": "grammar_cases",
    "schema": "schema_cases",
    "ui": "ui_pattern_candidates",
    "random": "random_testing",
    "metamorphic": "metamorphic",
}
_ID_PATTERNS = {
    "tcn": re.compile(r"^TCN-[0-9]{3}$"),
    "model": re.compile(r"^[a-z][a-z0-9-]*-[0-9]{3,}$"),
    "ci": re.compile(r"^(TCN-[0-9]{3})-CI([0-9]{2,})$"),
    "scope": re.compile(r"^SCOPE-[0-9]{3,}$"),
}
_BLOCK_RE = re.compile(
    r"^### (?P<kind>Machine Runtime Input|Machine Runtime Result): "
    r"(?P<identity>[^\r\n]+)\r?\n\r?\n```json\r?\n(?P<body>.*?)\r?\n```",
    re.MULTILINE | re.DOTALL,
)
_ENTITY_BLOCK_RE = re.compile(
    r"^### Machine Entities: (?P<skill>[^\r\n]+)\r?\n\r?\n```json\r?\n(?P<body>.*?)\r?\n```",
    re.MULTILINE | re.DOTALL,
)
_METADATA_FIELDS = {
    "envelope_version",
    "skill",
    "runtime_contract_version",
    "generator_contract_version",
    "runtime_unit_key",
    "model_key",
    "model_type",
    "technique_slug",
    "selection_source",
    "selection_key",
    "scope_key",
    "input_mode",
    "upstream_entities",
    "upstream_runtime_units",
    "static_data_versions",
    "authority_refs",
    "reference_refs",
}
_RESULT_FIELDS = {
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
_V1_CONDITION_FIELDS = {
    "test_requirements",
    "technique_selections",
    "test_conditions",
    "requirement_dispositions",
    "models",
    "previous_tcn_ids",
    "previous_model_keys",
    "update_scope_tcn_ids",
    "update_scope_model_keys",
}
_V2_TCN_FIELDS = {
    "draft_key",
    "identity_action",
    "reuse_id",
    "tr_refs",
    "condition",
    "category",
    "technique_slugs",
    "coverage_criterion",
    "authority_refs",
    "risk_refs",
    "priority",
    "priority_override_reason",
}
_V2_MODEL_FIELDS = {
    "draft_key",
    "model_type",
    "technique_slug",
    "selection_source",
    "selection_key",
    "derived_from_model_draft_key",
    "identity_action",
    "reuse_model_key",
    "parent_tcn_draft_key",
}


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise InvalidInput(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_number(token: str) -> Any:
    if len(token) > 4096:
        raise LimitExceeded("JSON number token exceeds the runtime limit")
    raise InvalidInput("cutover request fields must be strings or null")


def _request(raw: bytes) -> dict[str, Any]:
    if len(raw) > MAX_AGGREGATE_INPUT_BYTES:
        raise LimitExceeded("stdin exceeds 16 MiB")
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise InvalidInput("stdin must be strict UTF-8 JSON") from exc
    try:
        _scan_json_depth(text)
        _scan_json_string_limits(
            text,
            exempt_top_level_string_keys=frozenset(
                {"artifact_markdown", "current_v2_artifact_markdown"}
            ),
        )
        value = json.loads(
            text,
            object_pairs_hook=_pairs,
            parse_int=_reject_number,
            parse_float=_reject_number,
            parse_constant=_reject_number,
        )
    except RuntimeErrorBase:
        raise
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        raise InvalidInput("stdin must be one strict JSON object") from exc
    _reject_surrogates(value)
    if not isinstance(value, dict) or set(value) != {
        "operation",
        "phase",
        "artifact_markdown",
        "current_v2_artifact_markdown",
    }:
        raise InvalidInput("cutover request fields are invalid")
    phase = value.get("phase")
    if value.get("operation") != "cutover" or phase not in {*PHASES, "resume"}:
        raise InvalidInput("TCD cutover operation or phase is invalid")
    if not isinstance(value.get("artifact_markdown"), str):
        raise InvalidInput("artifact_markdown is required")
    current = value.get("current_v2_artifact_markdown")
    if current is not None and not isinstance(current, str):
        raise InvalidInput("current_v2_artifact_markdown must be a string or null")
    for field in ("artifact_markdown", "current_v2_artifact_markdown"):
        body = value[field]
        if (
            isinstance(body, str)
            and len(body.encode("utf-8")) > MAX_AGGREGATE_INPUT_BYTES
        ):
            raise LimitExceeded(f"{field} exceeds 16 MiB")
    if phase in set(PHASES[1:]) and current is None:
        raise InvalidInput("later TCD phases require current_v2_artifact_markdown")
    return value


def _decode_block(body: str) -> dict[str, Any]:
    raw = body.encode("utf-8")
    if len(raw) > MAX_NORMAL_INPUT_BYTES:
        raise LimitExceeded("v1 Machine Runtime block exceeds 2 MiB")
    value = strict_loads(raw)
    if not isinstance(value, dict):
        raise InvalidInput("Machine Runtime block must be an object")
    return value


def _legacy_blocks(markdown: str) -> tuple[dict[str, dict], dict[str, dict]]:
    inputs: dict[str, dict] = {}
    results: dict[str, dict] = {}
    for match in _BLOCK_RE.finditer(markdown):
        identity = match.group("identity")
        if not identity.startswith(SKILL + "::"):
            raise InvalidInput("TCD cutover source contains a foreign runtime unit")
        target = inputs if match.group("kind") == "Machine Runtime Input" else results
        if identity in target:
            raise InvalidInput(f"duplicate {match.group('kind')} block")
        target[identity] = _decode_block(match.group("body"))
    if not inputs or set(inputs) != set(results):
        raise InvalidInput("TCD v1 source requires complete unique input/result pairs")
    return inputs, results


def _legacy_upstreams(metadata: dict[str, Any]) -> list[dict[str, str]]:
    source = metadata.get("upstream_entities")
    if not isinstance(source, list):
        raise InvalidInput("v1 metadata.upstream_entities must be an array")
    rows = []
    seen = set()
    for row in source:
        if not isinstance(row, dict) or set(row) != {
            "skill",
            "entity_type",
            "entity_ref",
            "content",
        }:
            raise InvalidInput("v1 upstream Entity schema is invalid")
        identity = (row["skill"], row["entity_type"], row["entity_ref"])
        if (
            not all(isinstance(value, str) and value for value in identity)
            or not isinstance(row["content"], dict)
            or identity in seen
        ):
            raise InvalidInput("v1 upstream Entity identity/content is invalid")
        seen.add(identity)
        rows.append(
            {
                "skill": identity[0],
                "entity_type": identity[1],
                "entity_ref": identity[2],
                "content_fingerprint": sha256_digest(row["content"]),
            }
        )
    return sorted(
        rows,
        key=lambda row: (row["skill"], row["entity_type"], row["entity_ref"]),
    )


def _legacy_machine_entities(markdown: str) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    identities = set()
    blocks = 0
    for match in _ENTITY_BLOCK_RE.finditer(markdown):
        blocks += 1
        if match.group("skill") != SKILL:
            raise InvalidInput("TCD source contains a foreign Machine Entities block")
        wrapper = _decode_block(match.group("body"))
        if (
            set(wrapper) != {"schema_version", "skill", "entities"}
            or wrapper.get("schema_version") != "entity-state-v1"
            or wrapper.get("skill") != SKILL
            or not isinstance(wrapper.get("entities"), list)
        ):
            raise InvalidInput("TCD Machine Entities wrapper is not entity-state-v1")
        for entity in wrapper["entities"]:
            required = {
                "schema_version",
                "skill",
                "entity_type",
                "entity_ref",
                "model_key",
                "content",
                "content_fingerprint",
                "upstream_entity_dependencies",
                "runtime_dependencies",
            }
            if (
                not isinstance(entity, dict)
                or set(entity) != required
                or entity.get("schema_version") != "entity-state-v1"
                or entity.get("skill") != SKILL
                or entity.get("entity_type")
                not in {
                    "tcn",
                    "model",
                    "ci",
                    "test_data_requirement",
                    "disposition",
                }
                or not isinstance(entity.get("entity_ref"), str)
                or not entity["entity_ref"]
                or (
                    entity.get("model_key") is not None
                    and not isinstance(entity.get("model_key"), str)
                )
                or not isinstance(entity.get("content"), dict)
                or entity.get("content_fingerprint") != sha256_digest(entity["content"])
                or not isinstance(entity.get("upstream_entity_dependencies"), list)
                or not isinstance(entity.get("runtime_dependencies"), list)
            ):
                raise InvalidInput(
                    "TCD v1 Machine Entity schema/fingerprint is invalid"
                )
            identity = (entity["skill"], entity["entity_type"], entity["entity_ref"])
            if identity in identities:
                raise InvalidInput("TCD v1 Machine Entity identity is duplicated")
            identities.add(identity)
            entity_dependencies = set()
            for dependency in entity["upstream_entity_dependencies"]:
                if (
                    not isinstance(dependency, dict)
                    or set(dependency)
                    != {"skill", "entity_type", "entity_ref", "content_fingerprint"}
                    or not all(
                        isinstance(dependency.get(field), str) and dependency[field]
                        for field in ("skill", "entity_type", "entity_ref")
                    )
                    or not FULL_DIGEST_RE.fullmatch(
                        str(dependency.get("content_fingerprint"))
                    )
                ):
                    raise InvalidInput("TCD v1 entity dependency schema is invalid")
                dependency_identity = (
                    dependency["skill"],
                    dependency["entity_type"],
                    dependency["entity_ref"],
                )
                if (
                    dependency_identity == identity
                    or dependency_identity in entity_dependencies
                ):
                    raise InvalidInput(
                        "TCD v1 entity dependency is duplicate/self-referential"
                    )
                entity_dependencies.add(dependency_identity)
            runtime_dependencies = set()
            for dependency in entity["runtime_dependencies"]:
                if (
                    not isinstance(dependency, dict)
                    or set(dependency)
                    != {"skill", "runtime_unit_key", "generation_fingerprint"}
                    or not isinstance(dependency.get("skill"), str)
                    or not dependency["skill"]
                    or not isinstance(dependency.get("runtime_unit_key"), str)
                    or not dependency["runtime_unit_key"]
                    or not FULL_DIGEST_RE.fullmatch(
                        str(dependency.get("generation_fingerprint"))
                    )
                ):
                    raise InvalidInput("TCD v1 runtime dependency schema is invalid")
                dependency_identity = (
                    dependency["skill"],
                    dependency["runtime_unit_key"],
                )
                if dependency_identity in runtime_dependencies:
                    raise InvalidInput("TCD v1 runtime dependency is duplicated")
                runtime_dependencies.add(dependency_identity)
            result.append(entity)
    if blocks != 1:
        raise InvalidInput("TCD v1 Machine Entities block is missing or duplicated")
    return result


def _validate_legacy_metadata(
    metadata: Any,
    *,
    unit: str,
    model_key: str | None,
    scope_key: str | None,
    generator_contract: str,
) -> dict[str, Any]:
    if not isinstance(metadata, dict) or set(metadata) != _METADATA_FIELDS:
        raise InvalidInput("v1 runtime metadata schema is invalid")
    if (
        metadata.get("envelope_version") != "1"
        or metadata.get("runtime_contract_version") != "runtime-v1"
        or metadata.get("skill") != SKILL
        or metadata.get("runtime_unit_key") != unit
        or metadata.get("model_key") != model_key
        or metadata.get("scope_key") != scope_key
        or metadata.get("generator_contract_version") != generator_contract
        or metadata.get("input_mode") not in {"artifact", "direct"}
    ):
        raise InvalidInput("v1 runtime metadata identity/version is invalid")
    if model_key is None:
        if any(
            metadata.get(field) is not None
            for field in (
                "model_type",
                "technique_slug",
                "selection_source",
                "selection_key",
            )
        ):
            raise InvalidInput("v1 artifact runtime model metadata is invalid")
    elif (
        not _ID_PATTERNS["model"].fullmatch(model_key)
        or metadata.get("model_type") is None
        or not model_key.startswith(str(metadata["model_type"]) + "-")
    ):
        raise InvalidInput("v1 model runtime metadata is invalid")
    for field in ("authority_refs", "reference_refs"):
        rows = metadata.get(field)
        if (
            not isinstance(rows, list)
            or not all(isinstance(row, str) and row for row in rows)
            or len(rows) != len(set(rows))
        ):
            raise InvalidInput(f"v1 metadata.{field} is invalid")
    static = metadata.get("static_data_versions")
    if not isinstance(static, dict) or any(
        not isinstance(key, str)
        or not re.fullmatch(r"[a-z][a-z0-9_]*", key)
        or not isinstance(value, str)
        or not value
        for key, value in static.items()
    ):
        raise InvalidInput("v1 static_data_versions is invalid")
    runtime_dependencies = metadata.get("upstream_runtime_units")
    if not isinstance(runtime_dependencies, list):
        raise InvalidInput("v1 upstream_runtime_units must be an array")
    dependency_keys = set()
    for row in runtime_dependencies:
        if (
            not isinstance(row, dict)
            or set(row) != {"skill", "runtime_unit_key", "generation_fingerprint"}
            or not isinstance(row.get("skill"), str)
            or not isinstance(row.get("runtime_unit_key"), str)
            or not FULL_DIGEST_RE.fullmatch(str(row.get("generation_fingerprint")))
        ):
            raise InvalidInput("v1 upstream_runtime_units row is invalid")
        dependency = (row["skill"], row["runtime_unit_key"])
        if dependency in dependency_keys or dependency == (SKILL, unit):
            raise InvalidInput(
                "v1 upstream_runtime_units is duplicate or self-referential"
            )
        dependency_keys.add(dependency)
    _legacy_upstreams(metadata)
    return metadata


def _validate_v1_pair(
    identity: str,
    input_body: Any,
    result: Any,
    *,
    generator: str,
    generator_contract: str,
    unit: str,
    model_key: str | None = None,
    scope_key: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    expected_identity = f"{SKILL}::{unit}"
    if identity != expected_identity:
        raise InvalidInput("v1 runtime pair identity mismatch")
    if (
        not isinstance(input_body, dict)
        or set(input_body) != {"metadata", "input"}
        or not isinstance(input_body.get("input"), dict)
    ):
        raise InvalidInput("v1 runtime input block schema is invalid")
    metadata = _validate_legacy_metadata(
        input_body["metadata"],
        unit=unit,
        model_key=model_key,
        scope_key=scope_key,
        generator_contract=generator_contract,
    )
    if not isinstance(result, dict) or set(result) != _RESULT_FIELDS:
        raise InvalidInput("v1 runtime result block schema is invalid")
    if (
        result.get("envelope_version") != "1"
        or result.get("skill") != SKILL
        or result.get("runtime_contract_version") != "runtime-v1"
        or result.get("generator_contract_version") != generator_contract
        or result.get("generator") != generator
        or result.get("runtime_unit_key") != unit
        or result.get("model_key") != model_key
        or result.get("runtime_implementation_fingerprint") != _RUNTIME_IMPL
        or result.get("generator_implementation_fingerprint")
        != _GENERATOR_IMPLS.get(generator)
        or not isinstance(result.get("payload"), dict)
        or not isinstance(result.get("issues"), list)
    ):
        raise InvalidInput("v1 result identity/schema/frozen implementation is invalid")
    input_fp = input_fingerprint(
        SKILL,
        unit,
        metadata["input_mode"],
        input_body["input"],
        metadata["authority_refs"],
        metadata["reference_refs"],
        metadata["selection_source"],
    )
    model_fp = model_fingerprint(metadata, input_fp)
    upstream = _legacy_upstreams(metadata)
    static_versions = metadata["static_data_versions"]
    if (
        result.get("input_fingerprint") != input_fp
        or result.get("model_fingerprint") != model_fp
        or result.get("upstream_entity_fingerprints") != upstream
        or result.get("upstream_runtime_units")
        != canonicalize(
            metadata["upstream_runtime_units"], parent_key="upstream_runtime_units"
        )
        or result.get("static_data_versions") != static_versions
    ):
        raise InvalidInput("v1 input/result pair integrity or dependency mismatch")
    for field in ("input_fingerprint", "generation_fingerprint"):
        if not FULL_DIGEST_RE.fullmatch(str(result.get(field))):
            raise InvalidInput(f"v1 result {field} is invalid")
    expected_generation = generation_fingerprint(
        generator=generator,
        input_fp=input_fp,
        model_fp=model_fp,
        runtime_contract_version="runtime-v1",
        generator_contract_version=generator_contract,
        runtime_impl_fp=_RUNTIME_IMPL,
        generator_impl_fp=_GENERATOR_IMPLS[generator],
        upstream=upstream,
        static_data_versions=static_versions,
    )
    if result.get("generation_fingerprint") != expected_generation:
        raise InvalidInput("v1 generation_fingerprint is invalid")
    return metadata, input_body["input"], result


def _state_rows(payload: dict[str, Any], field: str, kind: str) -> list[dict[str, Any]]:
    value = payload.get(field)
    if not isinstance(value, list):
        raise InvalidInput(f"v1 {field} must be an array")
    result = []
    seen = set()
    for row in value:
        if kind == "tcn":
            valid = (
                isinstance(row, dict)
                and set(row) == {"tcn_id", "status"}
                and isinstance(row.get("tcn_id"), str)
                and _ID_PATTERNS["tcn"].fullmatch(row["tcn_id"])
                and row.get("status") in {"active", "deleted"}
            )
            if not valid or row["tcn_id"] in seen:
                raise InvalidInput("v1 tcn_id_state row is invalid or duplicate")
            seen.add(row["tcn_id"])
            result.append({"tcn_id": row["tcn_id"], "status": row["status"]})
            continue
        required = {
            "model_key",
            "model_type",
            "technique_slug",
            "parent_tcn_id",
            "selection_source",
            "selection_key",
            "derived_from_model_key",
            "status",
        }
        valid = (
            isinstance(row, dict)
            and set(row) == required
            and isinstance(row.get("model_key"), str)
            and _ID_PATTERNS["model"].fullmatch(row["model_key"])
            and isinstance(row.get("model_type"), str)
            and row["model_key"].startswith(row["model_type"] + "-")
            and isinstance(row.get("parent_tcn_id"), str)
            and _ID_PATTERNS["tcn"].fullmatch(row["parent_tcn_id"])
            and row.get("status") in {"active", "deleted"}
        )
        if not valid or row["model_key"] in seen:
            raise InvalidInput("v1 model_key_state row is invalid or duplicate")
        seen.add(row["model_key"])
        result.append(canonicalize(row))
    return sorted(
        result, key=lambda row: row["tcn_id" if kind == "tcn" else "model_key"]
    )


def _mapping_rows(
    payload: dict[str, Any], field: str, key_field: str
) -> dict[str, dict]:
    value = payload.get(field)
    if not isinstance(value, list):
        raise InvalidInput(f"v1 {field} must be an array")
    result = {}
    used_ids = set()
    for row in value:
        required = {"draft_key", key_field, "identity_action"}
        if key_field == "model_key":
            required |= {
                "model_type",
                "technique_slug",
                "parent_tcn_id",
                "derived_from_model_key",
            }
        if (
            not isinstance(row, dict)
            or set(row) != required
            or not isinstance(row.get("draft_key"), str)
            or not row["draft_key"]
            or row.get("identity_action") not in {"new", "reuse"}
        ):
            raise InvalidInput(f"v1 {field} row schema is invalid")
        key = row.get(key_field)
        if (
            not isinstance(key, str)
            or not _ID_PATTERNS["tcn" if key_field == "tcn_id" else "model"].fullmatch(
                key
            )
            or row["draft_key"] in result
            or key in used_ids
        ):
            raise InvalidInput(f"v1 {field} identity is invalid or duplicate")
        result[row["draft_key"]] = row
        used_ids.add(key)
    return result


def _condition_input(
    source_input: dict[str, Any], payload: dict[str, Any]
) -> dict[str, Any]:
    if frozenset(source_input) not in {
        frozenset(_V1_CONDITION_FIELDS),
        frozenset(_V1_CONDITION_FIELDS | {"legacy_tcn_ids"}),
    }:
        raise InvalidInput("v1 condition_structure input schema is invalid")
    tcn_states = _state_rows(payload, "tcn_id_state", "tcn")
    model_states = _state_rows(payload, "model_key_state", "model")
    tcn_by_id = {row["tcn_id"]: row for row in tcn_states}
    model_by_id = {row["model_key"]: row for row in model_states}
    tcn_drafts = source_input.get("test_conditions")
    model_drafts = source_input.get("models")
    if not isinstance(tcn_drafts, list) or not isinstance(model_drafts, list):
        raise InvalidInput("v1 condition_structure drafts are missing")
    tcn_draft_by_key = {}
    for row in tcn_drafts:
        if not isinstance(row, dict) or not isinstance(row.get("draft_key"), str):
            raise InvalidInput("v1 test_conditions draft is invalid")
        key = row["draft_key"]
        if key in tcn_draft_by_key:
            raise InvalidInput("v1 test_conditions draft_key is duplicated")
        tcn_draft_by_key[key] = row
    model_draft_by_key = {}
    for row in model_drafts:
        if not isinstance(row, dict) or not isinstance(row.get("draft_key"), str):
            raise InvalidInput("v1 models draft is invalid")
        key = row["draft_key"]
        if key in model_draft_by_key:
            raise InvalidInput("v1 models draft_key is duplicated")
        model_draft_by_key[key] = row
    tcn_map = _mapping_rows(payload, "tcn_id_map", "tcn_id")
    model_map = _mapping_rows(payload, "model_key_map", "model_key")
    if set(tcn_map) != set(tcn_draft_by_key):
        raise InvalidInput("v1 test_conditions and tcn_id_map are not an exact join")
    if set(model_map) != set(model_draft_by_key):
        raise InvalidInput("v1 models and model_key_map are not an exact join")
    active_tcn_ids = {
        ref for ref, row in tcn_by_id.items() if row["status"] == "active"
    }
    active_model_ids = {
        ref for ref, row in model_by_id.items() if row["status"] == "active"
    }
    if {row["tcn_id"] for row in tcn_map.values()} != active_tcn_ids:
        raise InvalidInput("v1 active TCN state and draft mapping differ")
    if {row["model_key"] for row in model_map.values()} != active_model_ids:
        raise InvalidInput("v1 active model state and draft mapping differ")
    tcn_id_for_draft = {key: row["tcn_id"] for key, row in tcn_map.items()}
    model_key_for_draft = {key: row["model_key"] for key, row in model_map.items()}
    source_previous_tcn_ids = {
        row.get("tcn_id")
        for row in source_input.get("previous_tcn_ids", [])
        if isinstance(row, dict)
    }
    source_previous_model_keys = {
        row.get("model_key")
        for row in source_input.get("previous_model_keys", [])
        if isinstance(row, dict)
    }
    normalized_tcn = []
    for key in sorted(tcn_draft_by_key):
        row = tcn_draft_by_key[key]
        mapped = tcn_map[key]
        if tcn_by_id[mapped["tcn_id"]]["status"] != "active":
            raise InvalidInput("v1 tcn_id_map targets a non-active TCN")
        if row.get("identity_action") == "reuse":
            if row.get("reuse_id") != mapped["tcn_id"]:
                raise InvalidInput("v1 TCN reuse mapping differs from saved input")
        elif row.get("identity_action") == "new":
            if mapped["tcn_id"] in source_previous_tcn_ids:
                raise InvalidInput("v1 new TCN reuses a previous identity")
        else:
            raise InvalidInput("v1 TCN identity_action is invalid")
        draft = dict(row)
        draft.update({"identity_action": "reuse", "reuse_id": mapped["tcn_id"]})
        normalized_tcn.append(canonicalize(draft))
    normalized_models = []
    for key in sorted(model_draft_by_key):
        draft = model_draft_by_key[key]
        mapped = model_map[key]
        model_key = mapped["model_key"]
        state = model_by_id[model_key]
        parent_draft = draft.get("parent_tcn_draft_key")
        derived_draft = draft.get("derived_from_model_draft_key")
        parent_id = tcn_id_for_draft.get(parent_draft)
        derived_id = model_key_for_draft.get(derived_draft) if derived_draft else None
        if (
            state["status"] != "active"
            or mapped.get("model_type") != draft.get("model_type")
            or mapped.get("technique_slug") != draft.get("technique_slug")
            or mapped.get("parent_tcn_id") != parent_id
            or mapped.get("derived_from_model_key") != derived_id
            or state.get("model_type") != draft.get("model_type")
            or state.get("technique_slug") != draft.get("technique_slug")
            or state.get("parent_tcn_id") != parent_id
            or state.get("derived_from_model_key") != derived_id
            or state.get("selection_source") != draft.get("selection_source")
            or state.get("selection_key") != draft.get("selection_key")
        ):
            raise InvalidInput("v1 model mapping and saved semantic draft differ")
        if draft.get("identity_action") == "reuse":
            if draft.get("reuse_model_key") != model_key:
                raise InvalidInput("v1 model reuse mapping differs from saved input")
        elif draft.get("identity_action") == "new":
            if model_key in source_previous_model_keys:
                raise InvalidInput("v1 new model reuses a previous identity")
        else:
            raise InvalidInput("v1 model identity_action is invalid")
        projected = dict(draft)
        projected.update({"identity_action": "reuse", "reuse_model_key": model_key})
        normalized_models.append(canonicalize(projected))
    active_model_metadata = payload.get("active_model_metadata")
    if not isinstance(active_model_metadata, list):
        raise InvalidInput("v1 active_model_metadata is missing")
    metadata_by_key = {}
    for row in active_model_metadata:
        expected = {
            "model_key",
            "model_type",
            "technique_slug",
            "parent_tcn_id",
            "content_fingerprint",
        }
        if (
            not isinstance(row, dict)
            or set(row) != expected
            or row.get("model_key") in metadata_by_key
            or not FULL_DIGEST_RE.fullmatch(str(row.get("content_fingerprint")))
        ):
            raise InvalidInput("v1 active_model_metadata row is invalid")
        metadata_by_key[row["model_key"]] = row
    if set(metadata_by_key) != active_model_ids:
        raise InvalidInput("v1 active_model_metadata and model state differ")
    for model_key, row in metadata_by_key.items():
        state = model_by_id[model_key]
        if any(
            row.get(field) != state.get(field)
            for field in ("model_type", "technique_slug", "parent_tcn_id")
        ):
            raise InvalidInput("v1 active_model_metadata identity drift")
    test_requirements = source_input.get("test_requirements")
    if not isinstance(test_requirements, list):
        raise InvalidInput("v1 test_requirements must be an array")
    projected_trs = []
    for row in test_requirements:
        if not isinstance(row, dict) or "scope_refs" in row:
            raise InvalidInput("v1 test_requirements schema is invalid")
        projected_trs.append(canonicalize({**row, "scope_refs": []}))
    normalized = {
        field: source_input[field]
        for field in (
            "technique_selections",
            "requirement_dispositions",
        )
    }
    normalized.update(
        {
            "test_requirements": projected_trs,
            "test_conditions": normalized_tcn,
            "models": normalized_models,
            "previous_tcn_ids": [{**row, "scope_refs": []} for row in tcn_states],
            "previous_model_keys": [{**row, "scope_refs": []} for row in model_states],
            "update_scope_tcn_ids": sorted(active_tcn_ids),
            "update_scope_model_keys": sorted(active_model_ids),
            "inactive_tcn_ids": [],
            "inactive_model_keys": [],
            "inactive_tcn_history": [],
            "inactive_model_history": [],
            "inactive_materialize_history": [],
            "zero_scope_terminal": False,
        }
    )
    return canonicalize(normalized)


def _generator_for_model(row: dict[str, Any]) -> str | None:
    return _MODEL_GENERATORS.get(row.get("model_type"))


def _load_source(markdown: str) -> dict[str, Any]:
    source_entities = _legacy_machine_entities(markdown)
    inputs, results = _legacy_blocks(markdown)
    root_identity = f"{SKILL}::{CONDITION_UNIT}"
    if root_identity not in inputs:
        raise InvalidInput("TCD v1 source is missing condition_structure root pair")
    root_metadata, root_input, root_result = _validate_v1_pair(
        root_identity,
        inputs[root_identity],
        results[root_identity],
        generator=CONDITION_GENERATOR,
        generator_contract="condition-structure-v1",
        unit=CONDITION_UNIT,
        scope_key="all",
    )
    root_payload = root_result["payload"]
    projected_root = _condition_input(root_input, root_payload)
    model_states = _state_rows(root_payload, "model_key_state", "model")
    active_models = {
        row["model_key"]: row for row in model_states if row["status"] == "active"
    }
    active_tcns = {
        row["tcn_id"]
        for row in _state_rows(root_payload, "tcn_id_state", "tcn")
        if row["status"] == "active"
    }
    expected_ids = {root_identity}
    for model_key, row in active_models.items():
        generator = _generator_for_model(row)
        if generator is None:
            continue
        unit = f"model:{model_key}"
        identity = f"{SKILL}::{unit}"
        expected_ids.add(identity)
        _validate_v1_pair(
            identity,
            inputs.get(identity),
            results.get(identity),
            generator=generator,
            generator_contract=generator.replace("_", "-") + "-v1",
            unit=unit,
            model_key=model_key,
        )
        metadata = inputs[identity]["metadata"]
        if any(
            metadata.get(field) != row.get(field)
            for field in (
                "model_type",
                "technique_slug",
                "selection_source",
                "selection_key",
            )
        ):
            raise InvalidInput("v1 model runtime metadata differs from condition state")
    tdr_identity = f"{SKILL}::{TDR_UNIT}"
    tdr = None
    if tdr_identity in inputs or tdr_identity in results:
        expected_ids.add(tdr_identity)
        tdr_metadata, tdr_input, tdr_result = _validate_v1_pair(
            tdr_identity,
            inputs.get(tdr_identity),
            results.get(tdr_identity),
            generator=TDR_GENERATOR,
            generator_contract="test-data-requirements-v1",
            unit=TDR_UNIT,
            scope_key="all",
        )
        if tdr_metadata["model_key"] is not None:
            raise InvalidInput("v1 TDR artifact runtime metadata is invalid")
        tdr = {"metadata": tdr_metadata, "input": tdr_input, "result": tdr_result}
    materialize_by_tcn = {}
    for tcn_id in sorted(active_tcns):
        if not any(
            row["parent_tcn_id"] == tcn_id and row["technique_slug"] is not None
            for row in active_models.values()
        ):
            continue
        unit = f"artifact:materialize_coverage:{tcn_id}"
        identity = f"{SKILL}::{unit}"
        expected_ids.add(identity)
        metadata, materialize_input, result = _validate_v1_pair(
            identity,
            inputs.get(identity),
            results.get(identity),
            generator=MATERIALIZE_GENERATOR,
            generator_contract="materialize-coverage-v1",
            unit=unit,
            scope_key=tcn_id,
        )
        if metadata["model_key"] is not None:
            raise InvalidInput("v1 materialize runtime metadata is invalid")
        materialize_by_tcn[tcn_id] = {
            "metadata": metadata,
            "input": materialize_input,
            "result": result,
        }
    if set(inputs) != expected_ids or set(results) != expected_ids:
        raise InvalidInput("TCD v1 source contains missing or unexpected runtime units")
    return {
        "root_metadata": root_metadata,
        "root_input": root_input,
        "root_result": root_result,
        "root_normalized": projected_root,
        "model_states": model_states,
        "active_models": active_models,
        "active_tcns": active_tcns,
        "inputs": inputs,
        "results": results,
        "tdr": tdr,
        "materialize": materialize_by_tcn,
        "machine_entities": source_entities,
    }


def _current_pairs(markdown: str | None) -> tuple[dict[str, dict], dict[str, dict]]:
    if markdown is None:
        return {}, {}
    input_rows = extract_machine_blocks(markdown, "Machine Runtime Input")
    result_rows = extract_machine_blocks(markdown, "Machine Runtime Result")
    inputs = dict(input_rows)
    results = dict(result_rows)
    if set(inputs) != set(results):
        raise InvalidInput("current v2 TCD artifact has incomplete runtime pairs")
    if any(not identity.startswith(SKILL + "::") for identity in inputs):
        raise InvalidInput("current v2 TCD artifact contains a foreign runtime unit")
    for identity in inputs:
        issues = _validate_runtime_pair(
            SKILL, identity, inputs[identity], results[identity]
        )
        if issues:
            raise InvalidInput(f"current v2 runtime pair is invalid: {identity}")
    return inputs, results


def _current_state_rows(
    payload: dict[str, Any], field: str, kind: str
) -> dict[str, dict]:
    rows = payload.get(field)
    if not isinstance(rows, list):
        raise InvalidInput(f"current v2 {field} is missing")
    result = {}
    for row in rows:
        key_field = "tcn_id" if kind == "tcn" else "model_key"
        allowed = (
            {"tcn_id", "status", "scope_refs"}
            if kind == "tcn"
            else {
                "model_key",
                "model_type",
                "technique_slug",
                "parent_tcn_id",
                "selection_source",
                "selection_key",
                "derived_from_model_key",
                "status",
                "scope_refs",
            }
        )
        if (
            not isinstance(row, dict)
            or set(row) != allowed
            or not isinstance(row.get(key_field), str)
            or row.get("status") not in {"active", "deleted"}
            or row.get("scope_refs") != []
            or row[key_field] in result
        ):
            raise InvalidInput(f"current v2 {field} row is invalid")
        result[row[key_field]] = row
    return result


def _verify_condition_pair(
    source: dict[str, Any], inputs: dict[str, dict], results: dict[str, dict]
) -> bool:
    identity = f"{SKILL}::{CONDITION_UNIT}"
    current = inputs.get(identity)
    if current is None:
        if any(key != identity for key in inputs):
            raise InvalidInput(
                "TCD current v2 downstream exists before condition_structure"
            )
        return False
    if canonicalize(current["input"]) != source["root_normalized"]:
        raise RuntimeErrorBase(
            "current v2 condition_structure input differs from cutover projection",
            issue_type="cutover_semantic_drift",
        )
    payload = results[identity].get("payload")
    if not isinstance(payload, dict):
        raise InvalidInput("current v2 condition_structure payload is invalid")
    old_tcn = {
        row["tcn_id"]: row["status"]
        for row in _state_rows(source["root_result"]["payload"], "tcn_id_state", "tcn")
    }
    old_model = {row["model_key"]: row for row in source["model_states"]}
    current_tcn = _current_state_rows(payload, "tcn_id_state", "tcn")
    current_model = _current_state_rows(payload, "model_key_state", "model")
    if set(current_tcn) != set(old_tcn) or any(
        current_tcn[key]["status"] != status for key, status in old_tcn.items()
    ):
        raise RuntimeErrorBase(
            "current v2 TCN stable identity/state differs from v1",
            issue_type="cutover_semantic_drift",
        )
    if set(current_model) != set(old_model):
        raise RuntimeErrorBase(
            "current v2 model stable identity set differs from v1",
            issue_type="cutover_semantic_drift",
        )
    for key, old in old_model.items():
        current_row = current_model[key]
        for field in (
            "model_type",
            "technique_slug",
            "parent_tcn_id",
            "selection_source",
            "selection_key",
            "derived_from_model_key",
            "status",
        ):
            if current_row.get(field) != old.get(field):
                raise RuntimeErrorBase(
                    "current v2 model stable state differs from v1",
                    issue_type="cutover_semantic_drift",
                )
    if any(
        payload.get(field) != []
        for field in (
            "inactive_tcn_history",
            "inactive_model_history",
            "inactive_materialize_history",
        )
    ):
        raise InvalidInput("v1 cutover must start with empty inactive/history state")
    old_tcn_map = _mapping_rows(
        source["root_result"]["payload"], "tcn_id_map", "tcn_id"
    )
    old_model_map = _mapping_rows(
        source["root_result"]["payload"], "model_key_map", "model_key"
    )
    current_tcn_map = payload.get("tcn_id_map")
    current_model_map = payload.get("model_key_map")
    if not isinstance(current_tcn_map, list) or not isinstance(current_model_map, list):
        raise InvalidInput("current v2 identity mapping payload is invalid")
    normalized_tcn_map = {}
    for row in current_tcn_map:
        if (
            not isinstance(row, dict)
            or set(row) != {"draft_key", "tcn_id", "identity_action"}
            or row.get("draft_key") in normalized_tcn_map
            or row.get("identity_action") != "reuse"
        ):
            raise InvalidInput("current v2 TCN mapping schema is invalid")
        normalized_tcn_map[row["draft_key"]] = row
    if {key: row["tcn_id"] for key, row in normalized_tcn_map.items()} != {
        key: row["tcn_id"] for key, row in old_tcn_map.items()
    }:
        raise RuntimeErrorBase(
            "current v2 TCN mapping differs from cutover identity",
            issue_type="cutover_semantic_drift",
        )
    normalized_model_map = {}
    for row in current_model_map:
        if (
            not isinstance(row, dict)
            or set(row)
            != {
                "draft_key",
                "model_key",
                "model_type",
                "technique_slug",
                "parent_tcn_id",
                "derived_from_model_key",
                "identity_action",
            }
            or row.get("draft_key") in normalized_model_map
            or row.get("identity_action") != "reuse"
        ):
            raise InvalidInput("current v2 model mapping schema is invalid")
        normalized_model_map[row["draft_key"]] = row
    if {key: row["model_key"] for key, row in normalized_model_map.items()} != {
        key: row["model_key"] for key, row in old_model_map.items()
    }:
        raise RuntimeErrorBase(
            "current v2 model mapping differs from cutover identity",
            issue_type="cutover_semantic_drift",
        )
    for key, old in old_model_map.items():
        current_row = normalized_model_map[key]
        for field in (
            "model_type",
            "technique_slug",
            "parent_tcn_id",
            "derived_from_model_key",
        ):
            if current_row.get(field) != old.get(field):
                raise RuntimeErrorBase(
                    "current v2 model map semantic identity differs",
                    issue_type="cutover_semantic_drift",
                )
    active_metadata = payload.get("active_model_metadata")
    if not isinstance(active_metadata, list):
        raise InvalidInput("current v2 active_model_metadata is invalid")
    active_by_key = {}
    for row in active_metadata:
        if not isinstance(row, dict) or row.get("model_key") in active_by_key:
            raise InvalidInput("current v2 active_model_metadata has duplicate rows")
        if (
            set(row)
            != {
                "model_key",
                "model_type",
                "technique_slug",
                "parent_tcn_id",
                "scope_refs",
                "content_fingerprint",
            }
            or row.get("scope_refs") != []
            or not FULL_DIGEST_RE.fullmatch(str(row.get("content_fingerprint")))
        ):
            raise InvalidInput("current v2 active_model_metadata row is invalid")
        active_by_key[row["model_key"]] = row
    expected_active = {
        key for key, row in old_model.items() if row["status"] == "active"
    }
    if set(active_by_key) != expected_active:
        raise RuntimeErrorBase(
            "current v2 active model set differs from v1",
            issue_type="cutover_semantic_drift",
        )
    for key, row in active_by_key.items():
        old = old_model[key]
        if any(
            row.get(field) != old.get(field)
            for field in ("model_type", "technique_slug", "parent_tcn_id")
        ):
            raise RuntimeErrorBase(
                "current v2 active model metadata differs from v1",
                issue_type="cutover_semantic_drift",
            )
    return True


def _derived_child_input(
    parent_result: dict[str, Any],
    child_key: str,
    parent_key: str,
    child_model: dict[str, Any],
) -> dict[str, Any] | None:
    if parent_result.get("result_status") != "ready":
        return None
    payload = parent_result.get("payload")
    rows = payload.get("derived_child_inputs") if isinstance(payload, dict) else None
    if not isinstance(rows, list):
        raise InvalidInput("current parent model derived_child_inputs is invalid")
    matches = []
    for row in rows:
        if not isinstance(row, dict):
            raise InvalidInput("derived_child_inputs row is invalid")
        if row.get("child_model_key") != child_key:
            continue
        if row.get("parent_model_key", parent_key) != parent_key:
            raise InvalidInput("derived child parent identity is invalid")
        if row.get("model_type") != child_model.get("model_type") or not isinstance(
            row.get("input"), dict
        ):
            raise InvalidInput("derived child model type/input is invalid")
        matches.append(row)
    if len(matches) > 1:
        raise InvalidInput("duplicate derived child input")
    return matches[0]["input"] if matches else None


def _model_phase(
    source: dict[str, Any], inputs: dict[str, dict], results: dict[str, dict]
) -> tuple[bool, list[dict[str, Any]], set[str]]:
    condition_identity = f"{SKILL}::{CONDITION_UNIT}"
    if not _verify_condition_pair(source, inputs, results):
        raise RuntimeErrorBase(
            "models phase requires verified condition_structure",
            issue_type="cutover_dependency_incomplete",
        )
    payload = results[condition_identity]["payload"]
    states = _current_state_rows(payload, "model_key_state", "model")
    active_models = {
        key: row
        for key, row in states.items()
        if row["status"] == "active" and _generator_for_model(row)
    }
    model_unit_ids = {
        identity for identity in inputs if identity.startswith(f"{SKILL}::model:")
    }
    expected_ids = {f"{SKILL}::model:{key}" for key in active_models}
    if not model_unit_ids.issubset(expected_ids):
        raise InvalidInput("current v2 artifact contains an unknown model runtime unit")
    old_model_inputs = {}
    for key in active_models:
        identity = f"{SKILL}::model:{key}"
        if identity not in source["inputs"]:
            raise InvalidInput("v1 source is missing active model input")
        old_model_inputs[key] = source["inputs"][identity]["input"]
    depths: dict[str, int] = {}

    def depth(key: str, visiting: set[str]) -> int:
        if key in depths:
            return depths[key]
        if key in visiting:
            raise InvalidInput("v1 model dependency contains a cycle")
        parent = active_models[key].get("derived_from_model_key")
        if parent is None:
            value = 0
        elif parent not in active_models:
            raise RuntimeErrorBase(
                "derived child parent is missing",
                issue_type="cutover_dependency_incomplete",
            )
        else:
            value = depth(parent, visiting | {key}) + 1
        depths[key] = value
        return value

    ready = []
    completed: set[str] = set()
    waiting: set[str] = set()
    for key in sorted(active_models, key=lambda item: (depth(item, set()), item)):
        model = active_models[key]
        identity = f"{SKILL}::model:{key}"
        parent = model.get("derived_from_model_key")
        if parent is None:
            expected_input = canonicalize(old_model_inputs[key])
        else:
            parent_identity = f"{SKILL}::model:{parent}"
            parent_result = results.get(parent_identity)
            if parent_result is None:
                waiting.add(key)
                if identity in inputs:
                    raise RuntimeErrorBase(
                        "derived model exists before its parent",
                        issue_type="cutover_dependency_incomplete",
                    )
                continue
            derived = _derived_child_input(parent_result, key, parent, model)
            if derived is None:
                raise RuntimeErrorBase(
                    "parent result has no matching derived child input",
                    issue_type="cutover_dependency_incomplete",
                )
            expected_input = canonicalize(derived)
            if expected_input != canonicalize(old_model_inputs[key]):
                raise RuntimeErrorBase(
                    "derived child input differs from frozen v1 input",
                    issue_type="cutover_semantic_drift",
                )
        if identity in inputs:
            current_input = inputs[identity]
            if canonicalize(current_input["input"]) != expected_input:
                raise RuntimeErrorBase(
                    "current model input differs from cutover projection",
                    issue_type="cutover_semantic_drift",
                )
            metadata = current_input["metadata"]
            if (
                metadata.get("model_key") != key
                or metadata.get("model_type") != model.get("model_type")
                or metadata.get("technique_slug") != model.get("technique_slug")
                or metadata.get("selection_source") != model.get("selection_source")
                or metadata.get("selection_key") != model.get("selection_key")
            ):
                raise RuntimeErrorBase(
                    "current model metadata differs from stable model state",
                    issue_type="cutover_semantic_drift",
                )
            if results[identity].get("result_status") != "ready":
                raise RuntimeErrorBase(
                    "cutover model result is not ready",
                    issue_type="cutover_dependency_incomplete",
                )
            completed.add(key)
        else:
            ready.append(
                {
                    "generator": _generator_for_model(model),
                    "runtime_unit_key": f"model:{key}",
                    "model_key": key,
                    "normalized_input": expected_input,
                }
            )
    remaining = set(active_models) - completed
    ready_keys = {row["model_key"] for row in ready}
    if remaining and not ready_keys:
        raise RuntimeErrorBase(
            "no ready model unit remains in the dependency graph",
            issue_type="cutover_dependency_incomplete",
        )
    # A model pair may only be present after its exact frozen input was resolved above.
    return not remaining, ready, set(active_models)


def _current_targets(
    source: dict[str, Any],
    inputs: dict[str, dict],
    results: dict[str, dict],
    *,
    require_complete: bool = True,
) -> tuple[dict[str, dict], list[dict[str, Any]]]:
    condition_identity = f"{SKILL}::{CONDITION_UNIT}"
    payload = results[condition_identity]["payload"]
    state_rows = _current_state_rows(payload, "model_key_state", "model")
    active = {
        key: row
        for key, row in state_rows.items()
        if row["status"] == "active" and _generator_for_model(row)
    }
    targets: dict[str, dict] = {}
    model_result_rows = []
    for model_key in sorted(active):
        identity = f"{SKILL}::model:{model_key}"
        pair_input = inputs.get(identity)
        result = results.get(identity)
        if pair_input is None or result is None:
            if require_complete:
                raise RuntimeErrorBase(
                    "current model result is missing",
                    issue_type="cutover_dependency_incomplete",
                )
            continue
        if result.get("result_status") != "ready":
            raise RuntimeErrorBase(
                "current model result is not ready",
                issue_type="cutover_dependency_incomplete",
            )
        row = current_model_result_row(result, pair_input["metadata"])
        model_result_rows.append(row)
        payload = result.get("payload")
        target_rows = payload.get("targets") if isinstance(payload, dict) else None
        if not isinstance(target_rows, list):
            raise InvalidInput("current model targets must be an array")
        for target in target_rows:
            if not isinstance(target, dict) or not {
                "target_key",
                "target_ref",
                "target_content_fingerprint",
                "execution_fingerprint",
                "materializable",
                "execution",
            }.issubset(target):
                raise InvalidInput("current model target schema is invalid")
            ref = target.get("target_ref")
            target_key = target.get("target_key")
            if (
                not isinstance(target_key, str)
                or not target_key
                or ref
                != sha256_digest({"model_key": model_key, "target_key": target_key})
                or ref in targets
                or not FULL_DIGEST_RE.fullmatch(
                    str(target.get("target_content_fingerprint"))
                )
            ):
                raise InvalidInput(
                    "current model target identity/fingerprint is invalid"
                )
            if target["materializable"]:
                if not isinstance(target.get("execution"), dict) or target.get(
                    "execution_fingerprint"
                ) != sha256_digest(target["execution"]):
                    raise InvalidInput(
                        "current materializable target execution is invalid"
                    )
            elif (
                target.get("execution") is not None
                or target.get("execution_fingerprint") is not None
            ):
                raise InvalidInput(
                    "current non-materializable target execution is invalid"
                )
            content = dict(target)
            content.pop("target_ref", None)
            content.pop("target_content_fingerprint", None)
            content.pop("execution_fingerprint", None)
            if target["target_content_fingerprint"] != sha256_digest(content):
                raise InvalidInput("current target content fingerprint is invalid")
            targets[ref] = {
                **canonicalize(target),
                "target_ref": ref,
                "model_key": model_key,
                "generation_fingerprint": result["generation_fingerprint"],
                "source_model_key": model_key,
            }
    return targets, model_result_rows


def _rebase_source_targets(
    rows: Any, current: dict[str, dict], *, name: str, required_fields: set[str]
) -> list[dict[str, Any]]:
    if not isinstance(rows, list):
        raise InvalidInput(f"{name} must be an array")
    result = []
    seen = set()
    for row in rows:
        if not isinstance(row, dict) or set(row) != required_fields:
            raise InvalidInput(f"{name} row schema is invalid")
        ref = row.get("target_ref")
        target = current.get(ref)
        if not isinstance(ref, str) or target is None or ref in seen:
            raise RuntimeErrorBase(
                f"{name} target identity drift", issue_type="cutover_semantic_drift"
            )
        source_model = row.get("source_model_key", row.get("model_key"))
        if source_model is not None and source_model != target["model_key"]:
            raise RuntimeErrorBase(
                f"{name} source model drift", issue_type="cutover_semantic_drift"
            )
        seen.add(ref)
        projected = dict(row)
        if "target_content_fingerprint" in projected:
            projected["target_content_fingerprint"] = target[
                "target_content_fingerprint"
            ]
        if "generation_fingerprint" in projected:
            projected["generation_fingerprint"] = target["generation_fingerprint"]
        if "execution_fingerprint" in projected:
            if projected["execution_fingerprint"] != target["execution_fingerprint"]:
                raise RuntimeErrorBase(
                    f"{name} execution identity drift",
                    issue_type="cutover_semantic_drift",
                )
            projected["execution_fingerprint"] = target["execution_fingerprint"]
        result.append(canonicalize(projected))
    return sorted(result, key=lambda row: row["target_ref"])


def _tdr_projection(
    source: dict[str, Any], targets: dict[str, dict]
) -> dict[str, Any] | None:
    tdr = source["tdr"]
    if tdr is None:
        return None
    input_value = tdr["input"]
    if set(input_value) != {"requirements", "current_source_targets"}:
        raise InvalidInput("v1 test_data_requirements input schema is invalid")
    current_rows = []
    for ref, target in sorted(targets.items()):
        current_rows.append(
            {
                "source_model_key": target["model_key"],
                "target_ref": ref,
                "target_content_fingerprint": target["target_content_fingerprint"],
                "generation_fingerprint": target["generation_fingerprint"],
            }
        )
    old_rows = input_value.get("current_source_targets")
    if not isinstance(old_rows, list):
        raise InvalidInput("v1 TDR current_source_targets is invalid")
    old_by_ref = {}
    for row in old_rows:
        if (
            not isinstance(row, dict)
            or set(row)
            != {
                "source_model_key",
                "target_ref",
                "target_content_fingerprint",
                "generation_fingerprint",
            }
            or row.get("target_ref") in old_by_ref
        ):
            raise InvalidInput("v1 TDR source target row is invalid")
        old_by_ref[row["target_ref"]] = row
    if set(old_by_ref) != set(targets):
        raise RuntimeErrorBase(
            "TDR target set changed during cutover", issue_type="cutover_semantic_drift"
        )
    for ref, old in old_by_ref.items():
        if old.get("source_model_key") != targets[ref]["model_key"]:
            raise RuntimeErrorBase(
                "TDR source model changed during cutover",
                issue_type="cutover_semantic_drift",
            )
    requirements = input_value.get("requirements")
    if not isinstance(requirements, list):
        raise InvalidInput("v1 TDR requirements must be an array")
    projected_requirements = []
    seen_keys = set()
    for row in requirements:
        if not isinstance(row, dict) or not isinstance(row.get("requirement_key"), str):
            raise InvalidInput("v1 TDR requirement row is invalid")
        key = row["requirement_key"]
        if key in seen_keys:
            raise InvalidInput("v1 TDR requirement_key is duplicated")
        seen_keys.add(key)
        source_model_key = row.get("source_model_key")
        if (
            not isinstance(source_model_key, str)
            or source_model_key not in source["active_models"]
        ):
            raise RuntimeErrorBase(
                "TDR source model identity drift", issue_type="cutover_semantic_drift"
            )
        versions = row.get("source_target_versions")
        if not isinstance(versions, list):
            raise InvalidInput("v1 TDR source_target_versions is invalid")
        rebased = _rebase_source_targets(
            versions,
            targets,
            name=f"TDR {key} source_target_versions",
            required_fields={
                "target_ref",
                "target_content_fingerprint",
                "generation_fingerprint",
            },
        )
        for version in rebased:
            old = next(
                (
                    item
                    for item in versions
                    if item.get("target_ref") == version["target_ref"]
                ),
                None,
            )
            if old is None or old_by_ref[version["target_ref"]][
                "source_model_key"
            ] != row.get("source_model_key"):
                raise RuntimeErrorBase(
                    "TDR requirement source identity drift",
                    issue_type="cutover_semantic_drift",
                )
        projected = dict(row)
        projected["source_target_versions"] = rebased
        projected_requirements.append(canonicalize(projected))
    return canonicalize(
        {"requirements": projected_requirements, "current_source_targets": current_rows}
    )


def _old_model_rows_for_tcn(
    source: dict[str, Any], tcn_id: str
) -> list[dict[str, Any]]:
    result = []
    for key, state in sorted(source["active_models"].items()):
        if state["parent_tcn_id"] != tcn_id or _generator_for_model(state) is None:
            continue
        unit = f"model:{key}"
        identity = f"{SKILL}::{unit}"
        metadata = source["inputs"][identity]["metadata"]
        envelope = source["results"][identity]
        row = {
            "skill": SKILL,
            "model_key": key,
            "model_type": metadata["model_type"],
            "technique_slug": metadata["technique_slug"],
            "runtime_unit_key": unit,
            "input_fingerprint": envelope["input_fingerprint"],
            "model_fingerprint": envelope["model_fingerprint"],
            "generation_fingerprint": envelope["generation_fingerprint"],
            "generator_contract_version": envelope["generator_contract_version"],
            "support_status": envelope["support_status"],
            "runtime_status": envelope["runtime_status"],
            "result_status": envelope["result_status"],
            "deterministic_generated": envelope["deterministic_generated"],
            "freshness_status": "current",
            "targets": canonicalize(envelope["payload"].get("targets", [])),
            "unsupported_items": canonicalize(
                envelope["payload"].get("unsupported_items", [])
            ),
        }
        for field in ("coverage_summary", "completion_summary"):
            if field in envelope["payload"]:
                row[field] = canonicalize(envelope["payload"][field])
        result.append(canonicalize(row))
    return result


def _old_targets(model_rows: list[dict[str, Any]]) -> dict[str, dict]:
    result = {}
    for model in model_rows:
        for raw in model.get("targets", []):
            row = dict(raw)
            row["model_key"] = model["model_key"]
            row["generation_fingerprint"] = model["generation_fingerprint"]
            ref = row.get("target_ref")
            if not isinstance(ref, str) or ref in result:
                raise InvalidInput(
                    "v1 materialize target identity is invalid or duplicate"
                )
            result[ref] = row
    return result


def _state_for_tcn(
    payload: dict[str, Any], tcn_id: str, field: str, key_field: str
) -> list[dict]:
    rows = payload.get(field)
    if not isinstance(rows, list):
        raise InvalidInput(f"v1 materialize {field} is missing")
    result = []
    seen = set()
    for row in rows:
        if not isinstance(row, dict) or key_field not in row:
            raise InvalidInput(f"v1 materialize {field} row is invalid")
        key = row[key_field]
        if key in seen:
            raise InvalidInput(f"v1 materialize {field} is duplicate")
        seen.add(key)
        result.append(row)
    return result


def _semantic_fingerprint(row: dict[str, Any], versions: list[dict]) -> str:
    for field in ("authority_refs", "reference_refs", "test_data_requirement_refs"):
        value = row.get(field)
        if (
            not isinstance(value, list)
            or not all(isinstance(item, str) and item for item in value)
            or len(value) != len(set(value))
        ):
            raise InvalidInput(f"v1 semantic {field} is invalid")
    value = {
        "model_key": row["model_key"],
        "source_target_versions": sorted(versions, key=lambda item: item["target_ref"]),
        "item_text": row["item_text"],
        "authority_refs": sorted(row["authority_refs"]),
        "reference_refs": sorted(row["reference_refs"]),
        "priority": row["priority"],
        "priority_override_reason": row["priority_override_reason"],
        "expected_result_root": row["expected_result_root"],
        "test_data_requirement_refs": sorted(row["test_data_requirement_refs"]),
    }
    return sha256_digest(value)


def _materialize_projection(
    source: dict[str, Any],
    tcn_id: str,
    current_targets: dict[str, dict],
    current_models: list[dict],
    current_active_model_metadata: list[dict],
    current_test_data_requirements: list[dict],
) -> dict[str, Any]:
    source_unit = source["materialize"][tcn_id]
    old_input = source_unit["input"]
    source_fields = {
        "tcn_id",
        "active_model_metadata",
        "models",
        "semantic_coverage_items",
        "target_annotations",
        "target_dispositions",
        "test_data_requirements",
        "previous_target_id_map",
        "previous_semantic_ci_map",
        "previous_ci_ids",
        "previous_expected_result_roots",
        "merge_groups",
    }
    optional = {"legacy_ci_ids", "legacy_ci_seed"}
    if (
        set(old_input) - optional != source_fields
        or set(old_input) - source_fields - optional
    ):
        raise InvalidInput("v1 materialize_coverage input schema is invalid")
    if old_input.get("tcn_id") != tcn_id:
        raise InvalidInput("v1 materialize unit TCN identity differs")
    expected_old_metadata = [
        row
        for row in source["root_result"]["payload"]["active_model_metadata"]
        if row["parent_tcn_id"] == tcn_id
    ]
    if canonicalize(old_input.get("active_model_metadata")) != canonicalize(
        expected_old_metadata
    ):
        raise InvalidInput(
            "v1 materialize active model metadata differs from condition result"
        )
    old_model_rows = _old_model_rows_for_tcn(source, tcn_id)
    if canonicalize(old_input.get("models")) != canonicalize(old_model_rows):
        raise InvalidInput("v1 materialize model results differ from saved model units")
    if source["tdr"] is None:
        if (
            old_input.get("test_data_requirements") != []
            or current_test_data_requirements
        ):
            raise RuntimeErrorBase(
                "TDR state changed while materializing cutover",
                issue_type="cutover_semantic_drift",
            )
    else:
        old_tdr_rows = source["tdr"]["result"]["payload"].get("normalized_requirements")
        if not isinstance(old_tdr_rows, list) or canonicalize(
            old_input.get("test_data_requirements")
        ) != canonicalize(old_tdr_rows):
            raise InvalidInput(
                "v1 materialize test data requirements differ from TDR result"
            )
        if [row.get("requirement_key") for row in old_tdr_rows] != [
            row.get("requirement_key") for row in current_test_data_requirements
        ]:
            raise RuntimeErrorBase(
                "TDR requirement identity changed during cutover",
                issue_type="cutover_semantic_drift",
            )
    old_targets = _old_targets(old_model_rows)
    current_for_tcn = {
        ref: row
        for ref, row in current_targets.items()
        if row["model_key"]
        in {item["model_key"] for item in current_active_model_metadata}
    }
    if set(old_targets) != set(current_for_tcn):
        raise RuntimeErrorBase(
            "materialize target set changed during cutover",
            issue_type="cutover_semantic_drift",
        )
    for ref, old in old_targets.items():
        current = current_for_tcn[ref]
        if (
            old.get("model_key") != current.get("model_key")
            or old.get("target_key") != current.get("target_key")
            or old.get("execution") != current.get("execution")
            or old.get("materializable") != current.get("materializable")
        ):
            raise RuntimeErrorBase(
                "materialize target execution identity changed",
                issue_type="cutover_semantic_drift",
            )
    old_versions = {
        ref: {
            "target_ref": ref,
            "target_content_fingerprint": target["target_content_fingerprint"],
            "generation_fingerprint": target["generation_fingerprint"],
            "execution_fingerprint": target["execution_fingerprint"],
        }
        for ref, target in old_targets.items()
    }
    new_versions = {
        ref: {
            "target_ref": ref,
            "target_content_fingerprint": target["target_content_fingerprint"],
            "generation_fingerprint": target["generation_fingerprint"],
            "execution_fingerprint": target["execution_fingerprint"],
        }
        for ref, target in current_for_tcn.items()
    }
    annotations = []
    old_annotations = old_input.get("target_annotations")
    if not isinstance(old_annotations, list):
        raise InvalidInput("v1 target_annotations must be an array")
    for row in old_annotations:
        if not isinstance(row, dict) or row.get("target_ref") not in old_targets:
            raise RuntimeErrorBase(
                "v1 target annotation has unknown target",
                issue_type="cutover_semantic_drift",
            )
        ref = row["target_ref"]
        if (
            row.get("target_content_fingerprint")
            != old_versions[ref]["target_content_fingerprint"]
            or row.get("generation_fingerprint")
            != old_versions[ref]["generation_fingerprint"]
        ):
            raise InvalidInput("v1 target annotation version is inconsistent")
        annotations.append(
            canonicalize(
                {
                    **row,
                    "target_content_fingerprint": new_versions[ref][
                        "target_content_fingerprint"
                    ],
                    "generation_fingerprint": new_versions[ref][
                        "generation_fingerprint"
                    ],
                }
            )
        )
    dispositions = []
    old_dispositions = old_input.get("target_dispositions")
    if not isinstance(old_dispositions, list):
        raise InvalidInput("v1 target_dispositions must be an array")
    for row in old_dispositions:
        if not isinstance(row, dict) or row.get("target_ref") not in old_targets:
            raise RuntimeErrorBase(
                "v1 target disposition has unknown target",
                issue_type="cutover_semantic_drift",
            )
        ref = row["target_ref"]
        if (
            row.get("target_content_fingerprint")
            != old_versions[ref]["target_content_fingerprint"]
            or row.get("generation_fingerprint")
            != old_versions[ref]["generation_fingerprint"]
        ):
            raise InvalidInput("v1 target disposition version is inconsistent")
        projected = dict(row)
        projected["target_content_fingerprint"] = new_versions[ref][
            "target_content_fingerprint"
        ]
        projected["generation_fingerprint"] = new_versions[ref][
            "generation_fingerprint"
        ]
        covered = row.get("covered_by_target_version")
        if covered is not None:
            covered_ref = (
                covered.get("target_ref") if isinstance(covered, dict) else None
            )
            if covered_ref not in old_targets or covered_ref not in current_for_tcn:
                raise RuntimeErrorBase(
                    "duplicate disposition target changed",
                    issue_type="cutover_semantic_drift",
                )
            if any(
                covered.get(field) != old_versions[covered_ref][field]
                for field in (
                    "target_content_fingerprint",
                    "generation_fingerprint",
                    "execution_fingerprint",
                )
            ):
                raise InvalidInput("v1 duplicate disposition version is inconsistent")
            projected["covered_by_target_version"] = new_versions[covered_ref]
        dispositions.append(canonicalize(projected))
    semantic_state = source_unit["result"]["payload"].get("semantic_ci_mapping_state")
    target_state = source_unit["result"]["payload"].get("target_mapping_state")
    ci_state = source_unit["result"]["payload"].get("ci_id_state")
    root_state = source_unit["result"]["payload"].get("expected_result_root_state")
    if not all(
        isinstance(value, list)
        for value in (semantic_state, target_state, ci_state, root_state)
    ):
        raise InvalidInput("v1 materialize identity/history state is incomplete")
    previous_target = []
    target_mapping_seen = set()
    for row in target_state:
        required = {
            "target_ref",
            "model_key",
            "target_key",
            "target_content_fingerprint",
            "ci_id",
            "mapping_status",
        }
        if (
            not isinstance(row, dict)
            or set(row) != required
            or row.get("target_ref") in target_mapping_seen
        ):
            raise InvalidInput("v1 target_mapping_state row is invalid or duplicate")
        target_mapping_seen.add(row["target_ref"])
        if (
            row["target_ref"] not in old_targets
            or row["model_key"] != old_targets[row["target_ref"]]["model_key"]
            or row["target_key"] != old_targets[row["target_ref"]]["target_key"]
        ):
            raise InvalidInput("v1 target mapping identity differs from target set")
        if (
            row["target_content_fingerprint"]
            != old_versions[row["target_ref"]]["target_content_fingerprint"]
        ):
            raise InvalidInput("v1 target mapping fingerprint differs from target set")
        if row["mapping_status"] not in {"active", "deleted"}:
            raise InvalidInput("v1 target mapping status is invalid")
        if row["mapping_status"] == "active":
            previous_target.append(canonicalize(row))
    previous_semantic = []
    semantic_state_by_key = {}
    for row in semantic_state:
        required = {
            "semantic_item_key",
            "model_key",
            "ci_id",
            "mapping_status",
            "semantic_content_fingerprint",
        }
        if (
            not isinstance(row, dict)
            or set(row) != required
            or row.get("semantic_item_key") in semantic_state_by_key
        ):
            raise InvalidInput(
                "v1 semantic_ci_mapping_state row is invalid or duplicate"
            )
        if row.get("mapping_status") not in {
            "active",
            "deleted",
        } or not FULL_DIGEST_RE.fullmatch(str(row.get("semantic_content_fingerprint"))):
            raise InvalidInput("v1 semantic CI mapping state is invalid")
        semantic_state_by_key[row["semantic_item_key"]] = row
        if row["mapping_status"] == "active":
            previous_semantic.append(canonicalize(row))
    previous_ci = []
    ci_status = {}
    for row in ci_state:
        if (
            not isinstance(row, dict)
            or set(row) != {"ci_id", "status"}
            or row.get("status") not in {"active", "deleted"}
        ):
            raise InvalidInput("v1 ci_id_state row is invalid")
        ci_id = row["ci_id"]
        match = _ID_PATTERNS["ci"].fullmatch(str(ci_id))
        if match is None or match.group(1) != tcn_id or ci_id in ci_status:
            raise InvalidInput("v1 ci_id_state identity is invalid or duplicate")
        ci_status[ci_id] = row["status"]
        previous_ci.append({"ci_id": ci_id, "status": row["status"], "scope_refs": []})
    for row in previous_target:
        if ci_status.get(row["ci_id"]) != "active":
            raise InvalidInput("active target mapping references non-active CI")
    for row in previous_semantic:
        if ci_status.get(row["ci_id"]) != "active":
            raise InvalidInput("active semantic mapping references non-active CI")
    previous_roots = []
    roots_seen = set()
    for row in root_state:
        if (
            not isinstance(row, dict)
            or set(row) != {"expected_result_root", "status"}
            or row.get("status") not in {"active", "deleted"}
        ):
            raise InvalidInput("v1 expected_result_root_state row is invalid")
        root = row["expected_result_root"]
        if not isinstance(root, str) or not root or root in roots_seen:
            raise InvalidInput("v1 expected_result_root_state is duplicate or invalid")
        roots_seen.add(root)
        previous_roots.append(canonicalize(row))
    semantic_rows = old_input.get("semantic_coverage_items")
    if not isinstance(semantic_rows, list):
        raise InvalidInput("v1 semantic_coverage_items must be an array")
    projected_semantic = []
    semantic_draft_mappings = {}
    semantic_draft_keys = set()
    for row in semantic_rows:
        if (
            not isinstance(row, dict)
            or not isinstance(row.get("draft_key"), str)
            or row["draft_key"] in semantic_draft_keys
        ):
            raise InvalidInput("v1 semantic coverage draft is invalid or duplicate")
        semantic_draft_keys.add(row["draft_key"])
        versions = row.get("source_target_versions")
        if not isinstance(versions, list):
            raise InvalidInput("v1 semantic source_target_versions is invalid")
        old_rebased = []
        for version in versions:
            if not isinstance(version, dict) or set(version) != {
                "target_ref",
                "target_content_fingerprint",
                "generation_fingerprint",
            }:
                raise InvalidInput("v1 semantic source target row is invalid")
            ref = version["target_ref"]
            if ref not in old_targets or ref not in current_for_tcn:
                raise RuntimeErrorBase(
                    "semantic target identity changed",
                    issue_type="cutover_semantic_drift",
                )
            if (
                version["target_content_fingerprint"]
                != old_versions[ref]["target_content_fingerprint"]
                or version["generation_fingerprint"]
                != old_versions[ref]["generation_fingerprint"]
                or row.get("model_key") != old_targets[ref]["model_key"]
            ):
                raise InvalidInput(
                    "v1 semantic target version/model identity is inconsistent"
                )
            old_rebased.append(canonicalize(version))
        old_fingerprint = _semantic_fingerprint(row, old_rebased)
        candidates = [
            mapping
            for mapping in semantic_state_by_key.values()
            if mapping.get("model_key") == row.get("model_key")
            and mapping.get("semantic_content_fingerprint") == old_fingerprint
            and mapping.get("mapping_status") == "active"
        ]
        if len(candidates) != 1:
            raise RuntimeErrorBase(
                "semantic CI mapping is missing or ambiguous",
                issue_type="cutover_semantic_drift",
            )
        mapping = candidates[0]
        semantic_draft_mappings[row["draft_key"]] = mapping
        new_versions = [
            {
                "target_ref": ref,
                "target_content_fingerprint": current_for_tcn[ref][
                    "target_content_fingerprint"
                ],
                "generation_fingerprint": current_for_tcn[ref][
                    "generation_fingerprint"
                ],
            }
            for ref in sorted(version["target_ref"] for version in old_rebased)
        ]
        projected = dict(row)
        projected.update(
            {
                "identity_action": "reuse",
                "reuse_semantic_item_key": mapping["semantic_item_key"],
                "reuse_ci_id": mapping["ci_id"],
                "source_target_versions": new_versions,
            }
        )
        projected_semantic.append(canonicalize(projected))
    if len({row["ci_id"] for row in semantic_draft_mappings.values()}) != len(
        semantic_draft_mappings
    ):
        raise InvalidInput("semantic drafts ambiguously map to one CI")
    merge_groups = []
    old_groups = old_input.get("merge_groups")
    if not isinstance(old_groups, list):
        raise InvalidInput("v1 merge_groups must be an array")
    group_keys = set()
    grouped_targets = set()
    for row in old_groups:
        if not isinstance(row, dict) or set(row) not in (
            {"merge_group_key", "model_key", "target_refs"},
            {"merge_group_key", "model_key", "target_refs", "target_versions"},
        ):
            raise InvalidInput("v1 merge_group row schema is invalid")
        key = row.get("merge_group_key")
        refs = row.get("target_refs")
        if (
            not isinstance(key, str)
            or key in group_keys
            or not isinstance(refs, list)
            or len(refs) < 2
            or len(set(refs)) != len(refs)
        ):
            raise InvalidInput("v1 merge_group identity/membership is invalid")
        group_keys.add(key)
        for ref in refs:
            if (
                ref not in old_targets
                or ref not in current_for_tcn
                or old_targets[ref]["model_key"] != row.get("model_key")
                or ref in grouped_targets
            ):
                raise RuntimeErrorBase(
                    "merge membership changed during cutover",
                    issue_type="cutover_semantic_drift",
                )
            grouped_targets.add(ref)
        old_group_versions = row.get("target_versions")
        if old_group_versions is not None:
            if not isinstance(old_group_versions, list) or {
                item.get("target_ref")
                for item in old_group_versions
                if isinstance(item, dict)
            } != set(refs):
                raise InvalidInput(
                    "v1 merge_group target version membership is invalid"
                )
            for version in old_group_versions:
                ref = version.get("target_ref")
                if ref not in old_versions or any(
                    version.get(field) != old_versions[ref][field]
                    for field in (
                        "target_content_fingerprint",
                        "generation_fingerprint",
                        "execution_fingerprint",
                    )
                ):
                    raise InvalidInput("v1 merge_group version is inconsistent")
        projected = {
            "merge_group_key": key,
            "model_key": row["model_key"],
            "target_refs": sorted(refs),
            "target_versions": [new_versions[ref] for ref in sorted(refs)],
        }
        merge_groups.append(canonicalize(projected))
    return canonicalize(
        {
            "tcn_id": tcn_id,
            "active_model_metadata": current_active_model_metadata,
            "models": current_models,
            "semantic_coverage_items": projected_semantic,
            "target_annotations": annotations,
            "target_dispositions": dispositions,
            "test_data_requirements": current_test_data_requirements,
            "previous_target_id_map": previous_target,
            "previous_semantic_ci_map": previous_semantic,
            "previous_ci_ids": previous_ci,
            "previous_expected_result_roots": previous_roots,
            "merge_groups": merge_groups,
            "inactive_ci_ids": [],
            "inactive_materialize_history": [],
            "zero_scope_terminal": False,
        }
    )


def _phase_inputs(
    source: dict[str, Any], inputs: dict[str, dict], results: dict[str, dict]
) -> dict[str, Any]:
    condition_ready = _verify_condition_pair(source, inputs, results)
    model_complete = False
    model_inputs = []
    model_keys: set[str] = set()
    if condition_ready:
        model_complete, model_inputs, model_keys = _model_phase(source, inputs, results)
    elif len(inputs) > 0:
        raise InvalidInput(
            "current v2 TCD artifact has units before its condition root"
        )
    all_expected_models = {
        key
        for key, row in source["active_models"].items()
        if _generator_for_model(row) is not None
    }
    current_model_keys = {
        identity.split("::model:", 1)[1]
        for identity in inputs
        if identity.startswith(f"{SKILL}::model:")
    }
    model_complete = condition_ready and current_model_keys == all_expected_models
    if current_model_keys - all_expected_models:
        raise InvalidInput("current v2 TCD artifact contains an unexpected model unit")
    if current_model_keys != all_expected_models and any(
        identity == f"{SKILL}::{TDR_UNIT}"
        or identity.startswith(f"{SKILL}::artifact:materialize_coverage:")
        for identity in inputs
    ):
        raise RuntimeErrorBase(
            "downstream v2 pair exists before model completion",
            issue_type="cutover_dependency_incomplete",
        )
    targets: dict[str, dict] = {}
    model_result_rows = []
    if condition_ready and model_complete:
        targets, model_result_rows = _current_targets(source, inputs, results)
    tdr_input = None
    if condition_ready and model_complete:
        tdr_input = _tdr_projection(source, targets)
    tdr_identity = f"{SKILL}::{TDR_UNIT}"
    if source["tdr"] is None:
        if tdr_identity in inputs:
            raise InvalidInput(
                "current v2 TDR exists but frozen v1 source has no TDR unit"
            )
        tdr_complete = True
        current_tdr_requirements: list[dict] = []
    elif not condition_ready or not model_complete:
        tdr_complete = False
        current_tdr_requirements = []
    else:
        current_tdr = inputs.get(tdr_identity)
        if current_tdr is None:
            tdr_complete = False
            current_tdr_requirements = []
        else:
            if canonicalize(current_tdr["input"]) != tdr_input:
                raise RuntimeErrorBase(
                    "current v2 TDR input differs from cutover projection",
                    issue_type="cutover_semantic_drift",
                )
            payload = results[tdr_identity].get("payload")
            rows = (
                payload.get("normalized_requirements")
                if isinstance(payload, dict)
                else None
            )
            if not isinstance(rows, list):
                raise InvalidInput(
                    "current v2 TDR result normalized requirements are invalid"
                )
            old_rows = source["tdr"]["result"]["payload"].get("normalized_requirements")
            if not isinstance(old_rows, list) or [
                row.get("requirement_key") for row in old_rows
            ] != [row.get("requirement_key") for row in rows]:
                raise RuntimeErrorBase(
                    "current v2 TDR requirement identity differs from v1",
                    issue_type="cutover_semantic_drift",
                )
            raw_by_key = {
                row["requirement_key"]: row
                for row in source["tdr"]["input"]["requirements"]
            }
            projected_by_key = {
                row["requirement_key"]: row for row in tdr_input["requirements"]
            }
            expected_rows = []
            for old_row in old_rows:
                key = old_row.get("requirement_key")
                raw_row = raw_by_key.get(key)
                projected_row = projected_by_key.get(key)
                if raw_row is None or projected_row is None:
                    raise InvalidInput("TDR normalized requirement has no saved input")
                expected_row = dict(old_row)
                expected_row["source_target_versions"] = projected_row[
                    "source_target_versions"
                ]
                if projected_row["source_target_versions"]:
                    expected_row["applicable_target_refs"] = sorted(
                        row["target_ref"]
                        for row in projected_row["source_target_versions"]
                    )
                else:
                    expected_row["applicable_target_refs"] = sorted(
                        ref
                        for ref, target in targets.items()
                        if target["model_key"] == raw_row["source_model_key"]
                    )
                expected_rows.append(canonicalize(expected_row))
            if canonicalize(rows) != canonicalize(expected_rows):
                raise RuntimeErrorBase(
                    "current v2 TDR semantic output differs from v1 projection",
                    issue_type="cutover_semantic_drift",
                )
            current_tdr_requirements = rows
            tdr_complete = True
    if source["tdr"] is not None and tdr_identity in inputs and not condition_ready:
        raise RuntimeErrorBase(
            "current TDR pair exists before condition_structure",
            issue_type="cutover_dependency_incomplete",
        )
    materialize_projection = {}
    current_materialize_ids = {
        identity
        for identity in inputs
        if identity.startswith(f"{SKILL}::artifact:materialize_coverage:")
    }
    expected_materialize_ids = {
        f"{SKILL}::artifact:materialize_coverage:{tcn_id}"
        for tcn_id in source["materialize"]
    }
    if current_materialize_ids - expected_materialize_ids:
        raise InvalidInput("current v2 materialize unit is not in frozen v1 source")
    if current_materialize_ids and (
        not condition_ready or not model_complete or not tdr_complete
    ):
        raise RuntimeErrorBase(
            "materialize v2 pair exists before prerequisites",
            issue_type="cutover_dependency_incomplete",
        )
    if condition_ready and model_complete and tdr_complete:
        condition_payload = results[f"{SKILL}::{CONDITION_UNIT}"]["payload"]
        current_model_states = _current_state_rows(
            condition_payload, "model_key_state", "model"
        )
        for tcn_id in sorted(source["materialize"]):
            current_active_metadata = [
                row
                for row in condition_payload["active_model_metadata"]
                if row["parent_tcn_id"] == tcn_id
            ]
            current_models_for_tcn = [
                row
                for row in model_result_rows
                if current_model_states[row["model_key"]]["parent_tcn_id"] == tcn_id
            ]
            model_keys_for_tcn = {row["model_key"] for row in current_active_metadata}
            current_target_rows = {
                ref: row
                for ref, row in targets.items()
                if row["model_key"] in model_keys_for_tcn
            }
            current_test_data = current_tdr_requirements
            expected_input = _materialize_projection(
                source,
                tcn_id,
                current_target_rows,
                current_models_for_tcn,
                current_active_metadata,
                current_test_data,
            )
            identity = f"{SKILL}::artifact:materialize_coverage:{tcn_id}"
            materialize_projection[identity] = expected_input
            if (
                identity in inputs
                and canonicalize(inputs[identity]["input"]) != expected_input
            ):
                raise RuntimeErrorBase(
                    "current v2 materialize input differs from cutover projection",
                    issue_type="cutover_semantic_drift",
                )
    materialize_complete = current_materialize_ids == expected_materialize_ids
    return {
        "condition_ready": condition_ready,
        "model_complete": model_complete,
        "model_inputs": model_inputs,
        "model_keys": model_keys,
        "targets": targets,
        "model_result_rows": model_result_rows,
        "tdr_input": tdr_input,
        "tdr_complete": tdr_complete,
        "tdr_identity": tdr_identity,
        "current_tdr_requirements": current_tdr_requirements,
        "materialize_projection": materialize_projection,
        "materialize_complete": materialize_complete,
        "current_materialize_ids": current_materialize_ids,
        "expected_materialize_ids": expected_materialize_ids,
    }


def _requested_phase(
    source: dict[str, Any], state: dict[str, Any], phase: str
) -> tuple[str, bool, list[dict[str, Any]]]:
    if phase == "resume":
        if not state["condition_ready"]:
            return (
                PHASES[0],
                False,
                [
                    {
                        "generator": CONDITION_GENERATOR,
                        "runtime_unit_key": CONDITION_UNIT,
                        "model_key": None,
                        "normalized_input": source["root_normalized"],
                    }
                ],
            )
        if not state["model_complete"]:
            return PHASES[1], False, state["model_inputs"]
        if not state["tdr_complete"]:
            return (
                PHASES[2],
                False,
                [
                    {
                        "generator": TDR_GENERATOR,
                        "runtime_unit_key": TDR_UNIT,
                        "model_key": None,
                        "normalized_input": state["tdr_input"],
                    }
                ],
            )
        if not state["materialize_complete"]:
            return (
                PHASES[3],
                False,
                [
                    {
                        "generator": MATERIALIZE_GENERATOR,
                        "runtime_unit_key": identity.split("::", 1)[1],
                        "model_key": None,
                        "normalized_input": state["materialize_projection"][identity],
                    }
                    for identity in sorted(
                        state["expected_materialize_ids"]
                        - state["current_materialize_ids"]
                    )
                ],
            )
        return PHASES[3], True, []
    index = PHASES.index(phase)
    prerequisites = [
        state["condition_ready"],
        state["condition_ready"] and state["model_complete"],
        state["condition_ready"] and state["model_complete"] and state["tdr_complete"],
    ]
    if index and not prerequisites[index - 1]:
        raise RuntimeErrorBase(
            f"{phase} phase has an incomplete predecessor",
            issue_type="cutover_dependency_incomplete",
        )
    if index == 0:
        complete = state["condition_ready"]
        rows = (
            []
            if complete
            else [
                {
                    "generator": CONDITION_GENERATOR,
                    "runtime_unit_key": CONDITION_UNIT,
                    "model_key": None,
                    "normalized_input": source["root_normalized"],
                }
            ]
        )
    elif index == 1:
        complete = state["model_complete"]
        rows = [] if complete else state["model_inputs"]
    elif index == 2:
        complete = state["tdr_complete"]
        rows = (
            []
            if complete or source["tdr"] is None
            else [
                {
                    "generator": TDR_GENERATOR,
                    "runtime_unit_key": TDR_UNIT,
                    "model_key": None,
                    "normalized_input": state["tdr_input"],
                }
            ]
        )
    else:
        complete = state["materialize_complete"]
        rows = (
            []
            if complete
            else [
                {
                    "generator": MATERIALIZE_GENERATOR,
                    "runtime_unit_key": identity.split("::", 1)[1],
                    "model_key": None,
                    "normalized_input": state["materialize_projection"][identity],
                }
                for identity in sorted(
                    state["expected_materialize_ids"] - state["current_materialize_ids"]
                )
            ]
        )
    return phase, complete, rows


def cutover(request: dict[str, Any]) -> dict[str, Any]:
    source = _load_source(request["artifact_markdown"])
    inputs, results = _current_pairs(request["current_v2_artifact_markdown"])
    state = _phase_inputs(source, inputs, results)
    phase, complete, rows = _requested_phase(source, state, request["phase"])
    return {
        "valid": True,
        "phase": phase,
        "phase_complete": complete,
        "source_runtime_contract_version": "runtime-v1",
        "source_entity_schema_version": "entity-state-v1",
        "normalized_runtime_inputs": [
            {
                "generator": row["generator"],
                "runtime_unit_key": row["runtime_unit_key"],
                "model_key": row["model_key"],
                "normalized_input": canonicalize(row["normalized_input"]),
            }
            for row in rows
        ],
        "issues": [],
    }


def _emit(response: dict[str, Any]) -> int:
    output = (canonical_json_text(response) + "\n").encode("utf-8")
    if len(output) > MAX_STDOUT_BYTES:
        raise LimitExceeded("response exceeds 16 MiB")
    sys.stdout.buffer.write(output)
    return 0


def main() -> int:
    raw = sys.stdin.buffer.read(MAX_AGGREGATE_INPUT_BYTES + 1)
    phase = "resume"
    try:
        request = _request(raw)
        phase = request["phase"]
        return _emit(cutover(request))
    except RuntimeErrorBase as exc:
        return _emit(
            {
                "valid": False,
                "phase": phase,
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
    except Exception as exc:  # pragma: no cover
        _emit(
            {
                "valid": False,
                "phase": phase,
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
