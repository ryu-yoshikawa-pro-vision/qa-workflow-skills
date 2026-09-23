"""Normalize test-data requirements and check simultaneous target intersections."""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Any

from runtime_contract import FULL_DIGEST_RE, MODEL_GENERATORS, MODEL_TYPES, InvalidInput, UnsupportedInput, canonical_json_text, canonicalize, compare_versions, constraint_intersection_compatible, ensure_key, ensure_list, ensure_nonempty_string, make_machine_entity, reject_unknown, resolve_entity_dependencies, run_cli, typed_value, typed_value_compare, validate_upstream_entities


SKILL = "test-condition-design"
GENERATOR = "test_data_requirements"
GENERATOR_CONTRACT_VERSION = "test-data-requirements-v1"
SCRIPT_PATH = Path(__file__).resolve()
OPERATORS = {"eq", "enum", "range", "version_range", "boolean"}


def _typed(value: Any, name: str) -> dict:
    if not isinstance(value, dict):
        raise InvalidInput(f"{name}はtyped valueである必要があります")
    return typed_value(value)


def _normalize(row: dict, index: int, current_targets: dict[str, dict], current_models: dict[str, dict]) -> dict:
    required = {"requirement_key", "environment_key", "dimension_key", "operator", "authority_refs", "source_model_key", "source_target_versions"}
    reject_unknown(row, required, {"value", "values", "minimum", "maximum", "minimum_inclusive", "maximum_inclusive"})
    key = ensure_key(row["requirement_key"], f"requirements[{index}].requirement_key")
    if row["environment_key"] is not None or not ensure_key(row["dimension_key"], f"requirements[{index}].dimension_key") or row["operator"] not in OPERATORS:
        raise InvalidInput("test-data requirement identity/operatorが不正です")
    if not isinstance(row["authority_refs"], list) or len(set(row["authority_refs"])) != len(row["authority_refs"]) or not all(isinstance(value, str) and value for value in row["authority_refs"]):
        raise InvalidInput("test-data authority_refsが不正です")
    source_model = row["source_model_key"]
    if not isinstance(source_model, str) or not source_model:
        raise InvalidInput("source_model_keyが不正です")
    source_model_entity = current_models.get(source_model)
    if source_model_entity is None:
        raise InvalidInput("source_model_keyはcurrent model Machine Entityへ解決する必要があります")
    source_model_content = source_model_entity["content"]
    if (
        source_model_entity["entity_ref"] != source_model
        or source_model_content.get("model_key") != source_model
        or source_model_content.get("model_type") not in MODEL_TYPES
    ):
        raise InvalidInput("source_model_keyとcurrent model metadataが一致しません")
    source_versions = ensure_list(row["source_target_versions"], f"requirements[{index}].source_target_versions")
    source_model_type = source_model_content["model_type"]
    if source_versions and (source_model_type in {"classification", "cause-effect", "schema", "ui"} or source_model_content.get("technique_slug") is None):
        raise InvalidInput("target-specific requirementはCoverage所有modelを参照する必要があります")
    normalized = {"requirement_key": key, "environment_key": None, "dimension_key": row["dimension_key"], "operator": row["operator"], "authority_refs": sorted(row["authority_refs"]), "source_model_key": source_model, "source_target_versions": [], "data_ref": f"data:{key}"}
    if row["operator"] == "eq":
        normalized["value"] = _typed(row.get("value"), f"requirements[{index}].value")
    elif row["operator"] == "enum":
        values = [_typed(value, f"requirements[{index}].values") for value in ensure_list(row.get("values"), f"requirements[{index}].values")]
        if not values or len({canonical_json_text(value) for value in values}) != len(values):
            raise InvalidInput("test-data enumが不正です")
        normalized["values"] = values
    elif row["operator"] == "range":
        normalized["minimum"] = _typed(row.get("minimum"), f"requirements[{index}].minimum")
        normalized["maximum"] = _typed(row.get("maximum"), f"requirements[{index}].maximum")
        normalized["minimum_inclusive"] = row.get("minimum_inclusive")
        normalized["maximum_inclusive"] = row.get("maximum_inclusive")
        if not isinstance(normalized["minimum_inclusive"], bool) or not isinstance(normalized["maximum_inclusive"], bool):
            raise InvalidInput("test-data rangeが不正です")
        if typed_value_compare(normalized["minimum"], normalized["maximum"]) > 0:
            raise InvalidInput("test-data range minimumがmaximumを超えています")
        # The range may itself be empty; the target-scoped intersection below
        # reports that as an unresolved requirement conflict.
        constraint_intersection_compatible([normalized])
    elif row["operator"] == "version_range":
        normalized["minimum"], normalized["maximum"] = row.get("minimum"), row.get("maximum")
        normalized["minimum_inclusive"], normalized["maximum_inclusive"] = row.get("minimum_inclusive"), row.get("maximum_inclusive")
        if not isinstance(normalized["minimum_inclusive"], bool) or not isinstance(normalized["maximum_inclusive"], bool) or compare_versions(normalized["minimum"], normalized["maximum"]) > 0:
            raise InvalidInput("test-data version rangeが不正です")
    else:
        if not isinstance(row.get("value"), bool):
            raise InvalidInput("test-data booleanが不正です")
        normalized["value"] = row["value"]
    if source_versions:
        seen = set()
        for version in source_versions:
            if not isinstance(version, dict) or set(version) != {"target_ref", "target_content_fingerprint", "generation_fingerprint"} or version["target_ref"] in seen:
                raise InvalidInput("source_target_versionsが不正です")
            seen.add(version["target_ref"])
            if version["target_ref"] not in current_targets or not FULL_DIGEST_RE.fullmatch(str(version["target_content_fingerprint"])) or not FULL_DIGEST_RE.fullmatch(str(version["generation_fingerprint"])):
                raise InvalidInput("source_target_versionsがcurrent targetと不一致です")
            current = current_targets[version["target_ref"]]
            if current["source_model_key"] != source_model:
                raise InvalidInput("source_target_versionsがsource_model_keyと不一致です")
            if (
                version["target_ref"] != current["target_ref"]
                or version["target_content_fingerprint"] != current["target_content_fingerprint"]
                or version["generation_fingerprint"] != current["generation_fingerprint"]
            ):
                raise InvalidInput("source_target_versionsはcurrent target versionと完全一致する必要があります")
        normalized["source_target_versions"] = sorted(canonicalize(source_versions), key=lambda value: value["target_ref"])
    return normalized


def generate(input_value: dict, metadata: dict) -> dict:
    if metadata["runtime_unit_key"] != "artifact:test_data_requirements:all":
        raise InvalidInput("test_data_requirements runtime unitが不正です")
    reject_unknown(input_value, {"requirements", "current_source_targets"})
    target_rows = ensure_list(input_value["current_source_targets"], "current_source_targets")
    current_entities = validate_upstream_entities(metadata)
    current_models = {
        entity["entity_ref"]: entity
        for entity in current_entities
        if entity["skill"] == SKILL and entity["entity_type"] == "model"
    }
    source_runtimes = {
        (row["skill"], row["runtime_unit_key"]): row
        for row in metadata["upstream_runtime_units"]
    }
    current_targets: dict[str, dict] = {}
    for index, row in enumerate(target_rows):
        if not isinstance(row, dict) or set(row) != {"source_model_key", "target_ref", "target_content_fingerprint", "generation_fingerprint"} or row["target_ref"] in current_targets:
            raise InvalidInput(f"current_source_targets[{index}]が不正です")
        if not ensure_nonempty_string(row["source_model_key"], "source_model_key") or not FULL_DIGEST_RE.fullmatch(str(row["target_ref"])) or not FULL_DIGEST_RE.fullmatch(str(row["target_content_fingerprint"])) or not FULL_DIGEST_RE.fullmatch(str(row["generation_fingerprint"])):
            raise InvalidInput("current_source_targetsのdigestが不正です")
        current_targets[row["target_ref"]] = canonicalize(row)
    requirements = []
    seen = set()
    for index, row in enumerate(ensure_list(input_value["requirements"], "requirements")):
        if not isinstance(row, dict):
            raise InvalidInput("requirement rowが不正です")
        try:
            normalized = _normalize(row, index, current_targets, current_models)
        except UnsupportedInput as exc:
            requirement_key = row.get("requirement_key")
            if isinstance(requirement_key, str) and requirement_key:
                raise UnsupportedInput(
                    exc.message,
                    item_type="test_data_requirement",
                    source_key=requirement_key,
                    reason_code=exc.reason_code or "unsupported_intersection",
                    affected_technique_slug=exc.affected_technique_slug,
                ) from exc
            raise
        if normalized["requirement_key"] in seen:
            raise InvalidInput("requirement_keyが重複しています")
        seen.add(normalized["requirement_key"])
        source_model = normalized["source_model_key"]
        refs = [ref for ref, target in current_targets.items() if target["source_model_key"] == source_model]
        if normalized["source_target_versions"]:
            selected = {row["target_ref"] for row in normalized["source_target_versions"]}
            if not selected.issubset(set(refs)):
                raise InvalidInput("target-specific requirementのtarget所属が不正です")
            refs = sorted(selected)
        normalized["applicable_target_refs"] = sorted(refs)
        requirements.append(normalized)
    conflicts = []
    for target_ref, target in sorted(current_targets.items()):
        active = [row for row in requirements if target_ref in row["applicable_target_refs"]]
        grouped: dict[str, list[dict]] = {}
        for row in active:
            grouped.setdefault(row["dimension_key"], []).append(row)
        for dimension, rows in sorted(grouped.items()):
            try:
                compatible = constraint_intersection_compatible(rows)
            except UnsupportedInput as exc:
                source_key = sorted(row["requirement_key"] for row in rows)[0]
                raise UnsupportedInput(
                    exc.message,
                    item_type="test_data_requirement",
                    source_key=source_key,
                    reason_code=exc.reason_code or "unsupported_intersection",
                ) from exc
            if not compatible:
                conflicts.append({"target_ref": target_ref, "dimension_key": dimension, "requirement_keys": sorted(row["requirement_key"] for row in rows)})
    conflicts.sort(key=lambda row: (row["target_ref"], row["dimension_key"], row["requirement_keys"]))
    entities = []
    for row in requirements:
        source_model = current_models[row["source_model_key"]]
        source_identity = (source_model["skill"], source_model["entity_type"], source_model["entity_ref"])
        authority_identities = [("spec-analysis", "authority", ref) for ref in row["authority_refs"]]
        dependencies = resolve_entity_dependencies(
            [source_identity, *authority_identities],
            current_entities,
            require_all=metadata["input_mode"] == "artifact",
        )
        runtime_dependencies = [{"skill": SKILL, "runtime_unit_key": "artifact:test_data_requirements:all", "generation_fingerprint": "__CURRENT__"}]
        model_runtime_key = (SKILL, f"model:{source_model['entity_ref']}")
        if source_model["content"].get("model_type") in MODEL_GENERATORS:
            model_runtime = source_runtimes.get(model_runtime_key)
            if model_runtime is None:
                raise InvalidInput("runtime generatorを持つsource modelのcurrent runtime dependencyが必要です")
            runtime_dependencies.append({
                "skill": model_runtime["skill"],
                "runtime_unit_key": model_runtime["runtime_unit_key"],
                "generation_fingerprint": model_runtime["generation_fingerprint"],
            })
        entities.append(make_machine_entity(
            SKILL,
            "test_data_requirement",
            row["data_ref"],
            row,
            upstream_entity_dependencies=dependencies,
            runtime_dependencies=runtime_dependencies,
        ))
    return {"runtime_status": "ok", "support_status": "supported", "result_status": "unresolved" if conflicts else "ready", "runtime_required": True, "deterministic_generated": True, "payload": {"normalized_requirements": sorted(requirements, key=lambda row: row["requirement_key"]), "conflicts": conflicts, "entities": sorted(entities, key=lambda row: row["entity_ref"]), "expected_entity_identities": [{"skill": SKILL, "entity_type": "test_data_requirement", "entity_ref": row["data_ref"]} for row in sorted(requirements, key=lambda row: row["requirement_key"])]}, "issues": [{"issue_type": "test_data_conflict", "blocking": True, "target_key": row["target_ref"], "authority_refs": []} for row in conflicts]}


if __name__ == "__main__":
    raise SystemExit(run_cli(generate, skill=SKILL, generator=GENERATOR, generator_contract_version=GENERATOR_CONTRACT_VERSION, generator_path=SCRIPT_PATH))
