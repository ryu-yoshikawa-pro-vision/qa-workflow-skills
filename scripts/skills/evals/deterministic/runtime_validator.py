"""Validate runtime evidence embedded in deterministic Markdown outputs.

The product runtime owns generation.  This module only validates the evidence
boundary: exact runtime identity pairs, envelope projections, target identity,
and Machine Entity fingerprints.  It never derives expected units from the
observed output.
"""

from __future__ import annotations

import hashlib
import json
from decimal import Decimal, InvalidOperation
from pathlib import Path
import re
from typing import Any

from .result import EvalResult


BLOCK_RE = re.compile(
    r"^### (?P<kind>Machine Runtime Input|Machine Runtime Result|Machine Entities): (?P<identity>[^\r\n]+)\r?\n\r?\n```json\r?\n(?P<body>.*?)\r?\n```",
    re.MULTILINE | re.DOTALL,
)
RUNTIME_FIELDS = {
    "envelope_version", "skill", "runtime_contract_version", "generator_contract_version", "generator",
    "runtime_unit_key", "model_key", "input_fingerprint", "model_fingerprint", "generation_fingerprint",
    "runtime_implementation_fingerprint", "generator_implementation_fingerprint", "upstream_entity_fingerprints",
    "upstream_runtime_units", "support_status", "static_data_versions", "runtime_status", "result_status",
    "runtime_required", "deterministic_generated", "fallback_reason", "payload", "issues",
}
ENTITY_FIELDS = {
    "schema_version", "skill", "entity_type", "entity_ref", "model_key", "content", "content_fingerprint",
    "upstream_entity_dependencies", "runtime_dependencies",
}
ENTITY_TYPES = {
    "authority", "test_analysis_context", "product_risk", "technique_selection", "change_node", "change_edge",
    "environment_requirement", "test_data_requirement", "tr", "tcn", "model", "ci", "tc", "disposition",
}
RECORD_SORT_FIELDS = {
    "upstream_entities": ("skill", "entity_type", "entity_ref"),
    "upstream_runtime_units": ("skill", "runtime_unit_key"),
    "previous_tr_ids": ("tr_id",),
    "previous_tcn_ids": ("tcn_id",),
    "previous_tc_ids": ("tc_id",),
    "previous_model_keys": ("model_key",),
    "previous_ci_ids": ("ci_id",),
    "models": ("parent_tcn_draft_key", "model_type", "draft_key"),
    "sets": ("set_key",),
    "partitions": ("partition_key",),
    "technique_selections": ("selection_key",),
    "test_requirements": ("tr_id",),
    "test_conditions": ("draft_key",),
    "source_target_versions": ("target_ref",),
    "target_annotations": ("target_ref",),
    "target_dispositions": ("target_ref",),
    "merge_groups": ("merge_group_key",),
    "upstream_entity_dependencies": ("skill", "entity_type", "entity_ref"),
    "runtime_dependencies": ("skill", "runtime_unit_key"),
}
SET_ARRAY_KEYS = {
    "authority_refs", "reference_refs", "risk_refs", "tr_refs", "ci_refs", "source_refs",
    "related_authority_refs", "selected_techniques", "changed_node_keys", "initial_states", "initial_node_keys",
}
FULL_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
REPO_ROOT = Path(__file__).resolve().parents[4]


class _DuplicateKey(ValueError):
    pass


def _object_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateKey(key)
        result[key] = value
    return result


def _parse_json(text: str) -> Any:
    try:
        return json.loads(
            text,
            object_pairs_hook=_object_pairs,
            parse_int=int,
            parse_float=Decimal,
            parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)),
        )
    except (TypeError, ValueError, InvalidOperation) as exc:
        raise ValueError(str(exc)) from exc


def _number_text(value: Decimal) -> str:
    if not value.is_finite():
        raise ValueError("non-finite number")
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    if text in {"", "-0"} or Decimal(text) == 0:
        return "0"
    return text


def _canonical_text(value: Any) -> str:
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    if isinstance(value, Decimal):
        return _number_text(value)
    if isinstance(value, list):
        return "[" + ",".join(_canonical_text(child) for child in value) + "]"
    if isinstance(value, dict):
        return "{" + ",".join(
            _canonical_text(key) + ":" + _canonical_text(value[key]) for key in sorted(value)
        ) + "}"
    raise ValueError(type(value).__name__)


def _canonicalize(value: Any, parent_key: str | None = None) -> Any:
    if isinstance(value, dict):
        normalized = {key: _canonicalize(child, parent_key=key) for key, child in value.items()}
        return {key: normalized[key] for key in sorted(normalized)}
    if isinstance(value, list):
        normalized = [_canonicalize(child, parent_key=parent_key) for child in value]
        if parent_key in SET_ARRAY_KEYS:
            unique = {_canonical_text(item): item for item in normalized}
            return [unique[key] for key in sorted(unique)]
        fields = RECORD_SORT_FIELDS.get(parent_key or "")
        if fields and all(isinstance(item, dict) for item in normalized):
            return sorted(normalized, key=lambda item: tuple(str(item.get(field, "")) for field in fields))
        return normalized
    return value


def _digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(_canonical_text(_canonicalize(value)).encode("utf-8")).hexdigest()


def _implementation_fingerprint(path: Path) -> str:
    raw = path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _source_constant(path: Path, name: str) -> str | None:
    if not path.is_file():
        return None
    match = re.search(rf"^\s*{re.escape(name)}\s*=\s*['\"]([^'\"]+)['\"]", path.read_text(encoding="utf-8"), re.MULTILINE)
    return match.group(1) if match else None


def _source_paths(skill: str, generator: str) -> tuple[Path, Path]:
    scripts = REPO_ROOT / "skills" / skill / "scripts"
    return scripts / "runtime_contract.py", scripts / f"{generator}.py"


def _upstream_fingerprints(metadata: dict[str, Any]) -> list[dict[str, str]]:
    rows = metadata.get("upstream_entities")
    if not isinstance(rows, list):
        raise ValueError("upstream_entities is not a list")
    result: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"skill", "entity_type", "entity_ref", "content"}:
            raise ValueError("invalid upstream entity")
        key = (row["skill"], row["entity_type"], row["entity_ref"])
        if not all(isinstance(value, str) for value in key) or key in seen or not isinstance(row["content"], dict):
            raise ValueError("invalid or duplicate upstream entity")
        seen.add(key)
        result.append({"skill": key[0], "entity_type": key[1], "entity_ref": key[2], "content_fingerprint": _digest(row["content"])})
    return sorted(result, key=lambda row: (row["skill"], row["entity_type"], row["entity_ref"]))


def _input_fingerprint(skill: str, metadata: dict[str, Any], input_value: Any) -> str:
    value: dict[str, Any] = {
        "skill": skill,
        "runtime_unit_key": metadata["runtime_unit_key"],
        "input_mode": metadata["input_mode"],
        "input": _canonicalize(input_value),
        "authority_refs": sorted(set(metadata.get("authority_refs", []))),
        "reference_refs": sorted(set(metadata.get("reference_refs", []))),
    }
    if metadata.get("selection_source") is not None:
        value["selection_source"] = metadata["selection_source"]
    return _digest(value)


def _model_fingerprint(metadata: dict[str, Any], input_fp: str) -> str | None:
    if metadata.get("model_key") is None:
        return None
    return _digest({
        "model_key": metadata.get("model_key"),
        "model_type": metadata.get("model_type"),
        "technique_slug": metadata.get("technique_slug"),
        "selection_source": metadata.get("selection_source"),
        "selection_key": metadata.get("selection_key"),
        "input_fingerprint": input_fp,
    })


def _generation_fingerprint(result: dict[str, Any], input_fp: str, model_fp: str | None, upstream: list[dict[str, str]]) -> str:
    return _digest({
        "generator": result["generator"],
        "envelope_version": result["envelope_version"],
        "input_fingerprint": input_fp,
        "model_fingerprint": model_fp,
        "runtime_contract_version": result["runtime_contract_version"],
        "generator_contract_version": result["generator_contract_version"],
        "runtime_implementation_fingerprint": result["runtime_implementation_fingerprint"],
        "generator_implementation_fingerprint": result["generator_implementation_fingerprint"],
        "upstream_entity_fingerprints": upstream,
        "static_data_versions": _canonicalize(result.get("static_data_versions", {})),
    })


def _catalog_static_version(generator_path: Path) -> dict[str, str] | None:
    if generator_path.name != "ui_pattern_candidates.py":
        return None
    catalog_path = generator_path.parent.parent / "assets" / "ui-pattern-catalog.json"
    if not catalog_path.is_file():
        return None
    catalog = _parse_json(catalog_path.read_text(encoding="utf-8"))
    if not isinstance(catalog, list):
        return None
    normalized: list[dict[str, Any]] = []
    for row in catalog:
        if not isinstance(row, dict):
            return None
        candidates = []
        for candidate in row.get("candidates", []):
            if not isinstance(candidate, dict):
                return None
            candidate = dict(candidate)
            candidate["reference_refs"] = sorted(set(candidate.get("reference_refs", [])))
            candidates.append(candidate)
        normalized.append({
            "pattern_key": row.get("pattern_key"),
            "name": row.get("name"),
            "aliases": sorted(row.get("aliases", [])),
            "identifiers": sorted(row.get("identifiers", [])),
            "candidates": sorted(candidates, key=lambda item: item.get("candidate_key", "")),
        })
    normalized.sort(key=lambda row: row.get("pattern_key", ""))
    return {"ui_pattern_catalog": _digest(normalized)}


def _blocks(text: str, kind: str, result: EvalResult, assertion_id: str) -> tuple[list[tuple[str, Any]], list[str]]:
    rows: list[tuple[str, Any]] = []
    invalid: list[str] = []
    for match in BLOCK_RE.finditer(text):
        if match.group("kind") != kind:
            continue
        identity = match.group("identity")
        try:
            body = _parse_json(match.group("body"))
        except (TypeError, ValueError) as exc:
            invalid.append(identity + ":" + type(exc).__name__)
            continue
        rows.append((identity, body))
    result.add(assertion_id, not invalid, f"{kind}のJSONが読み取り可能であること", evidence={"invalid": invalid} if invalid else None)
    return rows, invalid


def _identity(row: Any) -> str | None:
    if isinstance(row, dict) and isinstance(row.get("skill"), str) and isinstance(row.get("runtime_unit_key"), str):
        return f"{row['skill']}::{row['runtime_unit_key']}"
    return None


def _expected_units(expected: dict[str, Any]) -> list[str]:
    contract = expected.get("runtime_contract") if isinstance(expected.get("runtime_contract"), dict) else expected
    rows = contract.get("expected_runtime_units", []) if isinstance(contract, dict) else []
    result: list[str] = []
    for row in rows if isinstance(rows, list) else []:
        if isinstance(row, str):
            result.append(row)
        elif isinstance(row, dict) and isinstance(row.get("skill"), str) and isinstance(row.get("runtime_unit_key"), str):
            result.append(f"{row['skill']}::{row['runtime_unit_key']}")
    return sorted(result)


def _expected_entities(expected: dict[str, Any]) -> list[tuple[str, str, str]]:
    config = expected.get("machine_entities") if isinstance(expected.get("machine_entities"), dict) else expected
    rows = config.get("expected_entities", []) if isinstance(config, dict) else []
    result: list[tuple[str, str, str]] = []
    for row in rows if isinstance(rows, list) else []:
        if isinstance(row, dict) and all(isinstance(row.get(key), str) for key in ("skill", "entity_type", "entity_ref")):
            result.append((row["skill"], row["entity_type"], row["entity_ref"]))
        elif isinstance(row, str) and row.count(":") >= 2:
            skill, entity_type, entity_ref = row.split(":", 2)
            result.append((skill, entity_type, entity_ref))
    return sorted(result)


def _assert_runtime_pair(result: EvalResult, identity: str, input_body: Any, result_body: Any, expected: dict[str, Any]) -> None:
    prefix = "RUNTIME-PAIR-" + re.sub(r"[^A-Za-z0-9]+", "-", identity).strip("-")[:80]
    ok_input = isinstance(input_body, dict) and set(input_body) == {"metadata", "input"} and isinstance(input_body.get("metadata"), dict) and isinstance(input_body.get("input"), dict)
    result.add(prefix + "-INPUT", ok_input, "runtime inputがmetadata/inputの固定schemaであること")
    ok_result = isinstance(result_body, dict) and set(result_body) == RUNTIME_FIELDS
    result.add(prefix + "-SCHEMA", ok_result, "runtime result envelopeが固定field集合であること")
    if not ok_input or not ok_result:
        return
    metadata = input_body["metadata"]
    expected_identity = f"{metadata.get('skill')}::{metadata.get('runtime_unit_key')}"
    result.add(prefix + "-IDENTITY", expected_identity == identity and result_body.get("skill") == metadata.get("skill") and result_body.get("runtime_unit_key") == metadata.get("runtime_unit_key") and result_body.get("model_key") == metadata.get("model_key"), "runtime input/result/heading identityが一致すること")
    result.add(prefix + "-FLAGS", isinstance(result_body.get("runtime_required"), bool) and isinstance(result_body.get("deterministic_generated"), bool), "runtime status flagがbooleanであること")
    digest_fields_valid = True
    for key in ("input_fingerprint", "generation_fingerprint", "runtime_implementation_fingerprint", "generator_implementation_fingerprint"):
        digest_fields_valid = digest_fields_valid and bool(FULL_DIGEST_RE.fullmatch(str(result_body.get(key))))
    model_fp_value = result_body.get("model_fingerprint")
    digest_fields_valid = digest_fields_valid and (model_fp_value is None or bool(FULL_DIGEST_RE.fullmatch(str(model_fp_value))))
    result.add(prefix + "-DIGESTS", digest_fields_valid, "runtime fingerprint fieldが存在すること")
    try:
        runtime_path, generator_path = _source_paths(str(metadata.get("skill")), str(result_body.get("generator")))
        expected_runtime_contract = _source_constant(runtime_path, "RUNTIME_CONTRACT_VERSION")
        expected_envelope = _source_constant(runtime_path, "ENVELOPE_VERSION")
        expected_generator = _source_constant(generator_path, "GENERATOR")
        expected_generator_contract = _source_constant(generator_path, "GENERATOR_CONTRACT_VERSION")
        result.add(prefix + "-SOURCE", runtime_path.is_file() and generator_path.is_file(), "runtime/generator sourceがSkill-localに存在すること")
        if expected_runtime_contract is not None:
            result.add(prefix + "-CONTRACT", result_body.get("runtime_contract_version") == expected_runtime_contract, "runtime contract versionがsourceと一致すること")
        if expected_envelope is not None:
            result.add(prefix + "-ENVELOPE", result_body.get("envelope_version") == expected_envelope, "envelope versionがsourceと一致すること")
        if expected_generator is not None:
            result.add(prefix + "-GENERATOR-SOURCE", result_body.get("generator") == expected_generator, "generator名がsourceと一致すること")
        if expected_generator_contract is not None:
            result.add(prefix + "-GENERATOR-CONTRACT", result_body.get("generator_contract_version") == expected_generator_contract, "generator contract versionがsourceと一致すること")
        if runtime_path.is_file():
            result.add(prefix + "-RUNTIME-IMPLEMENTATION", result_body.get("runtime_implementation_fingerprint") == _implementation_fingerprint(runtime_path), "runtime implementation fingerprintをsourceから再計算できること")
        if generator_path.is_file():
            result.add(prefix + "-GENERATOR-IMPLEMENTATION", result_body.get("generator_implementation_fingerprint") == _implementation_fingerprint(generator_path), "generator implementation fingerprintをsourceから再計算できること")
        expected_input_fp = _input_fingerprint(str(metadata["skill"]), metadata, input_body["input"])
        expected_model_fp = _model_fingerprint(metadata, expected_input_fp)
        expected_upstream = _upstream_fingerprints(metadata)
        expected_static = _catalog_static_version(generator_path) or _canonicalize(metadata.get("static_data_versions", {}))
        result.add(prefix + "-INPUT-FINGERPRINT", result_body.get("input_fingerprint") == expected_input_fp, "input fingerprintを保存済みruntime inputから独立再計算できること")
        result.add(prefix + "-MODEL-FINGERPRINT", result_body.get("model_fingerprint") == expected_model_fp, "model fingerprintをmetadataとinputから独立再計算できること")
        result.add(prefix + "-UPSTREAM-FINGERPRINT", result_body.get("upstream_entity_fingerprints") == expected_upstream, "upstream Entity fingerprintをcontentから独立再計算できること")
        expected_runtime_dependencies = _canonicalize(metadata.get("upstream_runtime_units", []), parent_key="upstream_runtime_units")
        runtime_dependencies = result_body.get("upstream_runtime_units")
        runtime_dependency_schema = isinstance(runtime_dependencies, list)
        if runtime_dependency_schema:
            seen_runtime_dependencies: set[tuple[str, str]] = set()
            for dependency in runtime_dependencies:
                if not isinstance(dependency, dict) or set(dependency) != {"skill", "runtime_unit_key", "generation_fingerprint"} or not isinstance(dependency.get("skill"), str) or not isinstance(dependency.get("runtime_unit_key"), str) or not FULL_DIGEST_RE.fullmatch(str(dependency.get("generation_fingerprint"))):
                    runtime_dependency_schema = False
                    break
                dependency_key = (dependency["skill"], dependency["runtime_unit_key"])
                if dependency_key in seen_runtime_dependencies:
                    runtime_dependency_schema = False
                    break
                seen_runtime_dependencies.add(dependency_key)
        result.add(prefix + "-UPSTREAM-RUNTIME", runtime_dependency_schema and runtime_dependencies == expected_runtime_dependencies, "upstream runtime dependencyをmetadataから独立照合できること")
        result.add(prefix + "-STATIC-DATA", result_body.get("static_data_versions") == expected_static, "static data versionをsourceまたはmetadataから独立確認できること")
        expected_generation_fp = _generation_fingerprint(result_body, expected_input_fp, expected_model_fp, expected_upstream)
        result.add(prefix + "-GENERATION-FINGERPRINT", result_body.get("generation_fingerprint") == expected_generation_fp, "generation fingerprintを全依存から独立再計算できること")
        status = result_body.get("runtime_status")
        status_rules = {
            "unsupported": ("unsupported", False, False, "ready", "outside_supported_subset"),
            "not_run": ("unknown", True, False, "blocked", "python_unavailable"),
        }
        if status in status_rules:
            result.add(prefix + "-STATUS-PROJECTION", tuple(result_body.get(field) for field in ("support_status", "runtime_required", "deterministic_generated", "result_status", "fallback_reason")) == status_rules[status], "runtime unsupported/not_run status projectionが契約どおりであること")
        elif status in {"invalid_input", "limit_exceeded", "internal_error"}:
            result.add(prefix + "-STATUS-PROJECTION", result_body.get("runtime_required") is True and result_body.get("deterministic_generated") is False and result_body.get("result_status") == "blocked", "runtime error status projectionが契約どおりであること")
        _assert_targets(result, prefix, result_body)
    except (KeyError, TypeError, ValueError, OSError) as exc:
        result.add(prefix + "-FINGERPRINT-RECALC", False, "runtime fingerprintを独立再計算できること", evidence={"error": type(exc).__name__})
    contract = expected.get("runtime_contract") if isinstance(expected.get("runtime_contract"), dict) else expected
    expected_generator = contract.get("expected_generators", {}).get(identity) if isinstance(contract, dict) and isinstance(contract.get("expected_generators"), dict) else None
    if expected_generator is not None:
        result.add(prefix + "-GENERATOR", result_body.get("generator") == expected_generator, "runtime generatorが期待値と一致すること", evidence={"expected": expected_generator, "actual": result_body.get("generator")})
    expected_status = contract.get("expected_status", {}).get(identity) if isinstance(contract, dict) and isinstance(contract.get("expected_status"), dict) else None
    if isinstance(expected_status, dict):
        mismatches = {key: {"expected": value, "actual": result_body.get(key)} for key, value in expected_status.items() if result_body.get(key) != value}
        result.add(prefix + "-STATUS", not mismatches, "runtime status projectionが期待値と一致すること", evidence=mismatches or None)
    target_expectations = contract.get("expected_targets", {}).get(identity) if isinstance(contract, dict) and isinstance(contract.get("expected_targets"), dict) else None
    if isinstance(target_expectations, list):
        actual_targets = result_body.get("payload", {}).get("targets", []) if isinstance(result_body.get("payload"), dict) else []
        actual_keys = sorted(row.get("target_key") for row in actual_targets if isinstance(row, dict) and isinstance(row.get("target_key"), str))
        result.add(prefix + "-TARGETS", actual_keys == sorted(target_expectations), "runtime target stable ID集合が期待値と一致すること", evidence={"expected": sorted(target_expectations), "actual": actual_keys})


def _assert_targets(result: EvalResult, prefix: str, result_body: dict[str, Any]) -> None:
    payload = result_body.get("payload")
    targets = payload.get("targets", []) if isinstance(payload, dict) else []
    if not isinstance(targets, list):
        result.add(prefix + "-TARGET-SCHEMA", False, "runtime targetがarrayであること")
        return
    seen_keys: set[str] = set()
    seen_refs: set[str] = set()
    invalid: list[str] = []
    for index, target in enumerate(targets):
        if not isinstance(target, dict) or not isinstance(target.get("target_key"), str) or not isinstance(target.get("target_ref"), str):
            invalid.append(str(index))
            continue
        target_key = target["target_key"]
        if target_key in seen_keys or target["target_ref"] in seen_refs:
            invalid.append(f"{index}:duplicate")
        seen_keys.add(target_key)
        seen_refs.add(target["target_ref"])
        if result_body.get("model_key") is not None and target["target_ref"] != _digest({"model_key": result_body["model_key"], "target_key": target_key}):
            invalid.append(f"{index}:target_ref")
        materializable = target.get("materializable")
        if not isinstance(materializable, bool):
            invalid.append(f"{index}:materializable")
            continue
        if materializable:
            execution = target.get("execution")
            if not isinstance(execution, dict) or target.get("execution_fingerprint") != _digest(execution):
                invalid.append(f"{index}:execution")
        elif target.get("execution") is not None or target.get("execution_fingerprint") is not None:
            invalid.append(f"{index}:non_materializable_execution")
        content = dict(target)
        content.pop("target_ref", None)
        content.pop("target_content_fingerprint", None)
        content.pop("execution_fingerprint", None)
        if target.get("target_content_fingerprint") != _digest(content):
            invalid.append(f"{index}:target_content_fingerprint")
    result.add(prefix + "-TARGET-SCHEMA", not invalid, "runtime targetのstable ID・execution・content fingerprintを独立検査できること", evidence={"invalid": invalid} if invalid else None)


def validate_runtime_evidence(text: str, expected: dict[str, Any], result: EvalResult) -> None:
    """Append runtime/Machine Entity assertions when the eval declares them."""
    declared = any(key in expected for key in ("runtime_contract", "expected_runtime_units", "machine_entities", "expected_entities"))
    if not declared:
        return
    input_rows, _ = _blocks(text, "Machine Runtime Input", result, "RUNTIME-JSON-INPUT")
    result_rows, _ = _blocks(text, "Machine Runtime Result", result, "RUNTIME-JSON-RESULT")
    input_ids = [identity for identity, _ in input_rows]
    result_ids = [identity for identity, _ in result_rows]
    actual_ids = sorted(set(input_ids) | set(result_ids))
    expected_ids = _expected_units(expected)
    duplicates = sorted({identity for identity in input_ids if input_ids.count(identity) > 1} | {identity for identity in result_ids if result_ids.count(identity) > 1})
    result.add("RUNTIME-UNITS-EXACT", actual_ids == expected_ids, "runtime unit identity集合が期待値と完全一致すること", evidence={"expected": expected_ids, "actual": actual_ids})
    result.add("RUNTIME-PAIRS-COMPLETE", sorted(set(input_ids)) == sorted(set(result_ids)) and not duplicates, "runtime input/resultが一対一で重複しないこと", evidence={"input_only": sorted(set(input_ids) - set(result_ids)), "result_only": sorted(set(result_ids) - set(input_ids)), "duplicates": duplicates})
    input_map = {identity: body for identity, body in input_rows}
    result_map = {identity: body for identity, body in result_rows}
    for identity in sorted(set(input_map) & set(result_map)):
        _assert_runtime_pair(result, identity, input_map[identity], result_map[identity], expected)

    entity_rows, _ = _blocks(text, "Machine Entities", result, "ENTITY-JSON")
    entity_block_ids = [identity for identity, _ in entity_rows]
    entity_block_duplicates = sorted({identity for identity in entity_block_ids if entity_block_ids.count(identity) > 1})
    if isinstance(expected.get("machine_entities"), dict) or "expected_entities" in expected:
        result.add("ENTITY-BLOCK-PRESENT", bool(entity_rows), "宣言されたMachine Entity契約に対応するblockが存在すること")
    actual_entities: list[tuple[str, str, str]] = []
    invalid_entities: list[str] = []
    for identity, body in entity_rows:
        if not isinstance(body, dict) or not isinstance(body.get("entities"), list):
            invalid_entities.append(identity)
            continue
        for index, entity in enumerate(body["entities"]):
            if not isinstance(entity, dict) or set(entity) != ENTITY_FIELDS:
                invalid_entities.append(f"{identity}[{index}]")
                continue
            if entity.get("schema_version") != "entity-state-v1" or entity.get("skill") != identity or entity.get("entity_type") not in ENTITY_TYPES or not isinstance(entity.get("entity_ref"), str) or not entity.get("entity_ref") or (entity.get("model_key") is not None and (not isinstance(entity.get("model_key"), str) or not entity.get("model_key"))):
                invalid_entities.append(f"{identity}[{index}]:identity_schema")
                continue
            if not isinstance(entity.get("content"), dict):
                invalid_entities.append(f"{identity}[{index}]:content_schema")
                continue
            if entity.get("content_fingerprint") != _digest(entity.get("content")):
                invalid_entities.append(f"{identity}[{index}]:content_fingerprint")
                continue
            if not isinstance(entity.get("upstream_entity_dependencies"), list) or not isinstance(entity.get("runtime_dependencies"), list):
                invalid_entities.append(f"{identity}[{index}]:dependency_schema")
                continue
            key = (entity.get("skill"), entity.get("entity_type"), entity.get("entity_ref"))
            upstream_seen: set[tuple[str, str, str]] = set()
            runtime_seen: set[tuple[str, str]] = set()
            dependency_invalid = False
            for dependency in entity["upstream_entity_dependencies"]:
                if not isinstance(dependency, dict) or set(dependency) != {"skill", "entity_type", "entity_ref", "content_fingerprint"} or not FULL_DIGEST_RE.fullmatch(str(dependency.get("content_fingerprint"))):
                    dependency_invalid = True
                    break
                dependency_key = (dependency["skill"], dependency["entity_type"], dependency["entity_ref"])
                if not all(isinstance(value, str) and value for value in dependency_key) or dependency_key in upstream_seen or dependency_key == key:
                    dependency_invalid = True
                    break
                upstream_seen.add(dependency_key)
            if not dependency_invalid:
                for dependency in entity["runtime_dependencies"]:
                    if not isinstance(dependency, dict) or set(dependency) != {"skill", "runtime_unit_key", "generation_fingerprint"} or not FULL_DIGEST_RE.fullmatch(str(dependency.get("generation_fingerprint"))):
                        dependency_invalid = True
                        break
                    dependency_key = (dependency["skill"], dependency["runtime_unit_key"])
                    if not all(isinstance(value, str) and value for value in dependency_key) or dependency_key in runtime_seen:
                        dependency_invalid = True
                        break
                    runtime_seen.add(dependency_key)
            if dependency_invalid:
                invalid_entities.append(f"{identity}[{index}]:dependency_schema")
                continue
            if all(isinstance(value, str) for value in key):
                actual_entities.append(key)
    expected_entities = _expected_entities(expected)
    duplicate_entities = sorted({key for key in actual_entities if actual_entities.count(key) > 1})
    actual_entity_set = sorted(set(actual_entities))
    result.add("ENTITY-SCHEMA", not invalid_entities, "Machine Entity schemaとcontent fingerprintが正しいこと", evidence={"invalid": invalid_entities} if invalid_entities else None)
    result.add("ENTITY-BLOCK-DUPLICATES", not entity_block_duplicates, "Machine Entities block identityが重複しないこと", evidence={"duplicates": entity_block_duplicates} if entity_block_duplicates else None)
    result.add("ENTITY-IDENTITIES-EXACT", actual_entity_set == expected_entities and not duplicate_entities, "Machine Entity identity集合が期待値と完全一致すること", evidence={"expected": expected_entities, "actual": actual_entity_set, "duplicates": duplicate_entities})
    entity_map: dict[tuple[str, str, str], dict[str, Any]] = {}
    for identity, body in entity_rows:
        if not isinstance(body, dict) or not isinstance(body.get("entities"), list):
            continue
        for entity in body["entities"]:
            if isinstance(entity, dict) and all(isinstance(entity.get(field), str) for field in ("skill", "entity_type", "entity_ref")):
                entity_map[(entity["skill"], entity["entity_type"], entity["entity_ref"])] = entity
    dependency_mismatches: list[str] = []
    for key, entity in entity_map.items():
        for dependency in entity.get("upstream_entity_dependencies", []):
            dependency_key = (dependency.get("skill"), dependency.get("entity_type"), dependency.get("entity_ref"))
            current = entity_map.get(dependency_key)
            if current is not None and current.get("content_fingerprint") != dependency.get("content_fingerprint"):
                dependency_mismatches.append("entity:" + ":".join(str(value) for value in key))
        for dependency in entity.get("runtime_dependencies", []):
            dependency_key = f"{dependency.get('skill')}::{dependency.get('runtime_unit_key')}"
            current_runtime = result_map.get(dependency_key)
            if current_runtime is not None and current_runtime.get("generation_fingerprint") != dependency.get("generation_fingerprint"):
                dependency_mismatches.append("runtime:" + dependency_key)
    result.add("ENTITY-DEPENDENCIES", not dependency_mismatches, "Machine Entity dependency fingerprintが保存済みcurrent evidenceと一致すること", evidence={"mismatches": sorted(set(dependency_mismatches))} if dependency_mismatches else None)
