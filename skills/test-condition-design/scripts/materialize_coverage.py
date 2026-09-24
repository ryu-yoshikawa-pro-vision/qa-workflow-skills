"""Materialize current coverage targets into stable CI mappings."""

from __future__ import annotations

from pathlib import Path
import re
import sys
from typing import Any

from runtime_contract import (
    CI_ID_RE,
    FULL_DIGEST_RE,
    InvalidInput,
    MODEL_GENERATORS,
    MODEL_TYPES,
    STABLE_COMPONENT_RE,
    TECHNIQUE_SLUGS,
    canonicalize,
    canonical_json_text,
    compare_versions,
    constraint_intersection_compatible,
    ensure_list,
    ensure_key,
    ensure_nonempty_string,
    make_machine_entity,
    resolve_entity_dependencies,
    reject_unknown,
    run_cli,
    seed_legacy_ids,
    sha256_digest,
    unsupported_item_key,
    target_ref,
    typed_value,
    typed_value_compare,
    UnsupportedInput,
    validate_upstream_entities,
)


SKILL = "test-condition-design"
GENERATOR = "materialize_coverage"
GENERATOR_CONTRACT_VERSION = "materialize-coverage-v1"
SCRIPT_PATH = Path(__file__).resolve()
TCN_RE = re.compile(r"^TCN-(\d{3})$")
CI_RE = re.compile(r"^(TCN-\d{3})-CI(\d{2,})$")
HANDLINGS = {"対象外", "別テストレベル", "残存リスク", "ブロック中", "重複"}
PRIORITY_ORDER = {"低": 1, "中": 2, "高": 3}
ADAPTER_TYPES = {"classification", "cause-effect", "schema", "ui"}
MODEL_TECHNIQUE = {
    "ep": "ep", "bva": "bva", "domain": "domain", "decision": "decision", "comb": "comb",
    "state": "state", "flow": "scenario", "crud": "crud", "syntax": "syntax", "random": "random",
    "metamorphic": "metamorphic", "error-guessing": "error-guessing",
}
OPERATORS = {"eq", "enum", "range", "version_range", "boolean"}


def _normalize(row: dict, index: int, current_targets: dict[str, dict]) -> dict:
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
    source_versions = ensure_list(row["source_target_versions"], f"requirements[{index}].source_target_versions")
    normalized = {"requirement_key": key, "environment_key": None, "dimension_key": row["dimension_key"], "operator": row["operator"], "authority_refs": sorted(row["authority_refs"]), "source_model_key": source_model, "source_target_versions": [], "data_ref": f"data:{key}"}
    if row["operator"] == "eq":
        if not isinstance(row.get("value"), dict):
            raise InvalidInput(f"requirements[{index}].valueはtyped valueである必要があります")
        normalized["value"] = typed_value(row["value"])
    elif row["operator"] == "enum":
        values = [typed_value(value) for value in ensure_list(row.get("values"), f"requirements[{index}].values")]
        if not values or len({canonical_json_text(value) for value in values}) != len(values):
            raise InvalidInput("test-data enumが不正です")
        normalized["values"] = values
    elif row["operator"] == "range":
        normalized["minimum"] = typed_value(row.get("minimum"))
        normalized["maximum"] = typed_value(row.get("maximum"))
        normalized["minimum_inclusive"] = row.get("minimum_inclusive")
        normalized["maximum_inclusive"] = row.get("maximum_inclusive")
        if not isinstance(normalized["minimum_inclusive"], bool) or not isinstance(normalized["maximum_inclusive"], bool):
            raise InvalidInput("test-data rangeが不正です")
        if typed_value_compare(normalized["minimum"], normalized["maximum"]) > 0:
            raise InvalidInput("test-data range minimumがmaximumを超えています")
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
    applicable = sorted(ref for ref, target in current_targets.items() if target["source_model_key"] == source_model)
    if normalized["source_target_versions"]:
        selected = [row["target_ref"] for row in normalized["source_target_versions"]]
        if not set(selected).issubset(applicable):
            raise InvalidInput("target-specific requirementのtarget所属が不正です")
        applicable = sorted(selected)
    normalized["applicable_target_refs"] = applicable
    return normalized


def _tcn_id(value: Any) -> str:
    if not isinstance(value, str) or TCN_RE.fullmatch(value) is None:
        raise InvalidInput("tcn_idの形式が不正です")
    return value


def _ci_id(value: Any, tcn_id: str) -> str:
    if not isinstance(value, str):
        raise InvalidInput("ci_idが不正です")
    match = CI_RE.fullmatch(value)
    if match is None or match.group(1) != tcn_id:
        raise InvalidInput("ci_idのTCN prefixが不一致です")
    return value


def _ci_suffix(ci_id: str) -> int:
    match = CI_RE.fullmatch(ci_id)
    assert match is not None
    return int(match.group(2))


def _digest(value: Any, name: str) -> str:
    if not isinstance(value, str) or FULL_DIGEST_RE.fullmatch(value) is None:
        raise InvalidInput(f"{name}はsha256 digestである必要があります")
    return value


def _validate_model_metadata(rows: Any, tcn_id: str) -> list[dict[str, Any]]:
    result = []
    seen: set[str] = set()
    for index, row in enumerate(ensure_list(rows, "active_model_metadata")):
        if not isinstance(row, dict):
            raise InvalidInput(f"active_model_metadata[{index}]が不正です")
        required = {"model_key", "model_type", "technique_slug", "parent_tcn_id", "content_fingerprint"}
        reject_unknown(row, required)
        model_key = ensure_nonempty_string(row["model_key"], f"active_model_metadata[{index}].model_key")
        if model_key in seen:
            raise InvalidInput("active_model_metadataのmodel_keyが重複しています")
        seen.add(model_key)
        if row["parent_tcn_id"] != tcn_id:
            raise InvalidInput("active_model_metadataのparent/statusが不正です")
        model_type = row["model_type"]
        if model_type not in MODEL_TYPES or not model_key.startswith(model_type + "-"):
            raise InvalidInput("active_model_metadataのmodel_type / model_keyが不正です")
        technique_slug = row["technique_slug"]
        if model_type in ADAPTER_TYPES:
            if technique_slug is not None:
                raise InvalidInput("adapter model metadataが不正です")
        else:
            if technique_slug != MODEL_TECHNIQUE.get(model_type) or technique_slug not in TECHNIQUE_SLUGS:
                raise InvalidInput("Coverage model metadataのtechnique_slugが不正です")
        _digest(row["content_fingerprint"], "active_model_metadata.content_fingerprint")
        result.append(canonicalize({
            "model_key": model_key,
            "model_type": row["model_type"],
            "technique_slug": row["technique_slug"],
            "parent_tcn_id": tcn_id,
            "content_fingerprint": row["content_fingerprint"],
        }))
    if not result:
        raise InvalidInput("active Coverage modelが1件以上必要です")
    return result


def _validate_model_results(rows: Any, models: dict[str, dict[str, Any]], tcn_id: str) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for index, row in enumerate(ensure_list(rows, "model_results")):
        if not isinstance(row, dict):
            raise InvalidInput(f"model_results[{index}]が不正です")
        required = {"skill", "model_key", "model_type", "technique_slug", "runtime_unit_key", "input_fingerprint", "model_fingerprint", "generation_fingerprint", "generator_contract_version", "support_status", "runtime_status", "result_status", "deterministic_generated", "freshness_status", "targets", "unsupported_items"}
        optional = {"coverage_summary", "completion_summary"}
        reject_unknown(row, required, optional)
        model_key = ensure_nonempty_string(row["model_key"], f"model_results[{index}].model_key")
        if model_key in result or model_key not in models:
            raise InvalidInput("model_resultsのmodel_keyがactive modelと一致しません")
        if models[model_key]["model_type"] == "error-guessing":
            # Error Guessing is a semantic-only model.  It has no runtime
            # generator and therefore must never be projected as a runtime
            # model result merely to make materialization pass.
            raise InvalidInput("error-guessing modelにはruntime model resultを指定できません")
        if row["skill"] != SKILL or row["runtime_unit_key"] != f"model:{model_key}" or not isinstance(row["generator_contract_version"], str) or not row["generator_contract_version"] or not isinstance(row["generation_fingerprint"], str) or not FULL_DIGEST_RE.fullmatch(row["generation_fingerprint"]):
            raise InvalidInput("model result identityが不正です")
        if row["support_status"] not in {"supported", "partial", "unsupported"} or row["runtime_status"] not in {"ok", "unsupported"} or row["result_status"] != "ready":
            raise InvalidInput("model result statusが不正です")
        if not isinstance(row["deterministic_generated"], bool) or not isinstance(row["targets"], list) or not isinstance(row["unsupported_items"], list):
            raise InvalidInput("model result payloadが不正です")
        expected_generator = MODEL_GENERATORS.get(models[model_key]["model_type"])
        for item in row["unsupported_items"]:
            required_item = {"item_key", "item_type", "source_key", "reason_code", "affected_technique_slug", "authority_refs"}
            if not isinstance(item, dict) or set(item) != required_item or not isinstance(item["item_key"], str) or not isinstance(item["item_type"], str) or not isinstance(item["reason_code"], str) or not item["reason_code"] or not isinstance(item["authority_refs"], list) or len(set(item["authority_refs"])) != len(item["authority_refs"]) or not all(isinstance(ref, str) and ref for ref in item["authority_refs"]):
                raise InvalidInput("model result unsupported_items schemaが不正です")
            if expected_generator is not None and item["item_key"] != unsupported_item_key(expected_generator, item["item_type"], item["source_key"], item["affected_technique_slug"]):
                raise InvalidInput("model result unsupported item_keyが不一致です")
        if row["runtime_status"] == "ok" and row["deterministic_generated"] is not True:
            raise InvalidInput("runtime_required model resultはdeterministic_generated=trueが必要です")
        if row["runtime_status"] == "unsupported" and (row["support_status"] != "unsupported" or row["deterministic_generated"]):
            raise InvalidInput("unsupported model result status projectionが不正です")
        for digest_name in ("generation_fingerprint", "input_fingerprint", "model_fingerprint"):
            _digest(row[digest_name], f"model_results.{digest_name}")
        model_type = models[model_key]["model_type"]
        if row["runtime_status"] == "unsupported":
            if any(not isinstance(target, dict) or target.get("materializable") is not False for target in row["targets"]):
                raise InvalidInput("whole-model unsupported model resultは非materializable targetだけを含める必要があります")
        elif model_type == "crud":
            summary = row.get("coverage_summary")
            if not isinstance(summary, dict) or not isinstance(summary.get("completeness"), dict) or not isinstance(summary.get("consistency"), dict) or summary.get("complete") is not True or summary["completeness"].get("complete") is not True or summary["consistency"].get("complete") is not True:
                raise InvalidInput("CRUD model result coverage_summaryが未完了です")
        elif model_type in {"random", "metamorphic"}:
            if not isinstance(row.get("completion_summary"), dict) or row["completion_summary"].get("complete") is not True:
                raise InvalidInput("Random / Metamorphic model result completion_summaryが未完了です")
        elif model_type not in {"classification", "cause-effect", "schema", "ui", "error-guessing"}:
            if not isinstance(row.get("coverage_summary"), dict) or row["coverage_summary"].get("complete") is not True:
                raise InvalidInput("Coverage model result coverage_summaryが未完了です")
        normalized = dict(row)
        if normalized["freshness_status"] != "current":
            raise InvalidInput("materialize対象modelのfreshness_statusはcurrentである必要があります")
        if model_key in models and (row["model_type"] != models[model_key]["model_type"] or row["technique_slug"] != models[model_key]["technique_slug"]):
            raise InvalidInput("model result metadataがactive model metadataと不一致です")
        result[model_key] = canonicalize(normalized)
    for model_key, model in models.items():
        if model_key not in result and model["model_type"] != "error-guessing":
            raise InvalidInput(f"model resultが不足しています: {model_key}")
    return result


def _validate_targets(model_results: dict[str, dict[str, Any]], models: dict[str, dict[str, Any]], tcn_id: str) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for model_key, model_result in model_results.items():
        for index, target in enumerate(model_result["targets"]):
            if not isinstance(target, dict):
                raise InvalidInput(f"model_results[{model_key}].targets[{index}]が不正です")
            required = {"target_key", "target_ref", "target_content_fingerprint", "execution_fingerprint", "materializable", "execution"}
            if not required.issubset(target):
                raise InvalidInput("target schemaが不正です")
            target_key = ensure_nonempty_string(target["target_key"], "target_key")
            expected_ref = target_ref(model_key, target_key)
            if target["target_ref"] != expected_ref:
                raise InvalidInput("target_refが不一致です")
            _digest(target["target_content_fingerprint"], "target_content_fingerprint")
            if not isinstance(target["materializable"], bool):
                raise InvalidInput("target.materializableが不正です")
            if target["materializable"]:
                if not isinstance(target["execution"], dict) or target["execution_fingerprint"] != sha256_digest(target["execution"]):
                    raise InvalidInput("materializable targetのexecution fingerprintが不一致です")
            elif target["execution"] is not None or target["execution_fingerprint"] is not None:
                raise InvalidInput("non-materializable targetのexecutionが不正です")
            target_content = dict(target)
            target_content.pop("target_ref", None)
            target_content.pop("target_content_fingerprint", None)
            target_content.pop("execution_fingerprint", None)
            if target["target_content_fingerprint"] != sha256_digest(target_content):
                raise InvalidInput("target_content_fingerprintが不一致です")
            row = canonicalize({**target, "model_key": model_key, "generation_fingerprint": model_result["generation_fingerprint"]})
            if target["target_ref"] in result:
                raise InvalidInput("target_refが重複しています")
            result[target["target_ref"]] = row
    return result


def _validate_previous_map(rows: Any, tcn_id: str) -> list[dict[str, Any]]:
    result = []
    seen: set[str] = set()
    allowed = {"target_ref", "model_key", "target_key", "target_content_fingerprint", "ci_id", "mapping_status"}
    for index, row in enumerate(ensure_list(rows, "previous_target_id_map")):
        if not isinstance(row, dict):
            raise InvalidInput(f"previous_target_id_map[{index}]が不正です")
        reject_unknown(row, allowed)
        ref = _digest(row["target_ref"], f"previous_target_id_map[{index}].target_ref")
        if ref in seen:
            raise InvalidInput("previous target_refが重複しています")
        seen.add(ref)
        if row["mapping_status"] not in {"active", "inactive"}:
            raise InvalidInput("previous mapping_statusが不正です")
        _ci_id(row["ci_id"], tcn_id)
        if row["target_ref"] != target_ref(row["model_key"], row["target_key"]):
            raise InvalidInput("previous target_refの再計算結果が不一致です")
        _digest(row["target_content_fingerprint"], "previous target_content_fingerprint")
        result.append(canonicalize(row))
    return result


def _validate_dispositions(rows: Any, targets: dict[str, dict[str, Any]], generation_by_ref: dict[str, str]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for index, row in enumerate(ensure_list(rows, "target_dispositions")):
        if not isinstance(row, dict):
            raise InvalidInput(f"target_dispositions[{index}]が不正です")
        required = {"target_ref", "target_content_fingerprint", "generation_fingerprint", "handling", "reason", "authority_refs", "covered_by_target_version"}
        reject_unknown(row, required)
        if set(row) != required:
            raise InvalidInput("target dispositionの必須fieldが不足しています")
        ref = _digest(row["target_ref"], "target_dispositions.target_ref")
        if ref not in targets or ref in result:
            raise InvalidInput("target disposition target_refが不正です")
        if row["target_content_fingerprint"] != targets[ref]["target_content_fingerprint"] or row["generation_fingerprint"] != generation_by_ref[ref]:
            raise InvalidInput("target disposition versionがcurrent targetと不一致です")
        if row["handling"] not in HANDLINGS:
            raise InvalidInput("target disposition handlingが不正です")
        ensure_nonempty_string(row["reason"], "target disposition reason")
        if not isinstance(row["authority_refs"], list) or not all(isinstance(value, str) for value in row["authority_refs"]):
            raise InvalidInput("target disposition authority_refsが不正です")
        if row["handling"] == "重複":
            covered = row["covered_by_target_version"]
            if not isinstance(covered, dict) or set(covered) != {"target_ref", "target_content_fingerprint", "generation_fingerprint", "execution_fingerprint"}:
                raise InvalidInput("重複 dispositionのcovered_by_target_versionが不正です")
            if covered["target_ref"] == ref:
                raise InvalidInput("target dispositionが自己参照しています")
            covered_ref = covered["target_ref"]
            if covered_ref in targets:
                covered_target = targets[covered_ref]
                if covered["target_content_fingerprint"] != covered_target["target_content_fingerprint"] or covered["generation_fingerprint"] != covered_target["generation_fingerprint"] or covered["execution_fingerprint"] != covered_target["execution_fingerprint"]:
                    raise InvalidInput("重複 dispositionの参照target versionがcurrentと不一致です")
            else:
                _digest(covered["target_content_fingerprint"], "covered target_content_fingerprint")
                _digest(covered["generation_fingerprint"], "covered generation_fingerprint")
                if covered["execution_fingerprint"] is not None:
                    _digest(covered["execution_fingerprint"], "covered execution_fingerprint")
        elif row["covered_by_target_version"] is not None:
            raise InvalidInput("重複以外のcovered_by_target_versionはnullである必要があります")
        result[ref] = canonicalize(row)
    return result


def _validate_annotations(rows: Any, targets: dict[str, dict[str, Any]], generation_by_ref: dict[str, str]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    allowed = {"target_ref", "target_content_fingerprint", "generation_fingerprint", "priority", "priority_override_reason", "expected_result_root", "test_data_requirement_refs"}
    for index, row in enumerate(ensure_list(rows, "target_annotations")):
        if not isinstance(row, dict):
            raise InvalidInput(f"target_annotations[{index}]が不正です")
        reject_unknown(row, allowed)
        if set(row) != allowed:
            raise InvalidInput("target annotationの必須fieldが不足しています")
        ref = _digest(row["target_ref"], "target_annotations.target_ref")
        if ref not in targets or ref in result:
            raise InvalidInput("target annotation target_refが不正です")
        if row["target_content_fingerprint"] != targets[ref]["target_content_fingerprint"] or row["generation_fingerprint"] != generation_by_ref[ref]:
            raise InvalidInput("target annotation versionがcurrent targetと不一致です")
        if row["priority"] not in PRIORITY_ORDER or (row["priority_override_reason"] is not None and (not isinstance(row["priority_override_reason"], str) or not row["priority_override_reason"].strip())):
            raise InvalidInput("target annotation priorityが不正です")
        if row["expected_result_root"] is not None and (not isinstance(row["expected_result_root"], str) or STABLE_COMPONENT_RE.fullmatch(row["expected_result_root"]) is None or ":" in row["expected_result_root"]):
            raise InvalidInput("target annotation expected_result_rootが不正です")
        if not isinstance(row["test_data_requirement_refs"], list) or not all(isinstance(value, str) for value in row["test_data_requirement_refs"]):
            raise InvalidInput("target annotation test_data_requirement_refsが不正です")
        result[ref] = canonicalize(row)
    return result


def _validate_test_data_requirements(rows: Any, targets: dict[str, dict[str, Any]], models: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    current_targets = {
        ref: {
            "source_model_key": target["model_key"],
            "target_ref": ref,
            "target_content_fingerprint": target["target_content_fingerprint"],
            "generation_fingerprint": target["generation_fingerprint"],
        }
        for ref, target in targets.items()
    }
    for index, row in enumerate(ensure_list(rows, "test_data_requirements")):
        if not isinstance(row, dict):
            raise InvalidInput(f"test_data_requirements[{index}]が不正です")
        allowed = {"data_ref", "requirement_key", "environment_key", "dimension_key", "operator", "authority_refs", "source_model_key", "source_target_versions", "value", "values", "minimum", "maximum", "minimum_inclusive", "maximum_inclusive", "applicable_target_refs", "content_fingerprint"}
        reject_unknown(row, {"data_ref", "requirement_key", "environment_key", "dimension_key", "operator", "authority_refs", "source_model_key", "source_target_versions"}, allowed - {"data_ref", "requirement_key", "environment_key", "dimension_key", "operator", "authority_refs", "source_model_key", "source_target_versions"})
        data_ref = ensure_nonempty_string(row["data_ref"], "test_data_requirement.data_ref")
        requirement_key = ensure_nonempty_string(row["requirement_key"], "test_data_requirement.requirement_key")
        if data_ref != f"data:{requirement_key}" or data_ref in result:
            raise InvalidInput("test_data_requirement data_refが不正または重複しています")
        requirement_input = {key: value for key, value in row.items() if key not in {"data_ref", "applicable_target_refs", "content_fingerprint"}}
        normalized = _normalize(requirement_input, index, current_targets)
        source_model = models.get(normalized["source_model_key"])
        if source_model is None:
            raise InvalidInput("test_data_requirement source_model_keyがcurrent model metadataにありません")
        if normalized["source_target_versions"] and source_model["model_type"] in ADAPTER_TYPES:
            raise InvalidInput("target-specific test_data_requirementはCoverage所有modelが必要です")
        if "applicable_target_refs" in row:
            saved_applicable = row["applicable_target_refs"]
            if not isinstance(saved_applicable, list) or saved_applicable != normalized["applicable_target_refs"]:
                raise InvalidInput("test_data_requirement applicable_target_refsがcurrent targetと不一致です")
        normalized["data_ref"] = data_ref
        content = canonicalize(normalized)
        if "content_fingerprint" in row and row["content_fingerprint"] != sha256_digest(content):
            raise InvalidInput("test_data_requirement content_fingerprintが不一致です")
        result[data_ref] = content
    return result


def _validate_semantic_items(rows: Any, models: dict[str, dict[str, Any]], targets: dict[str, dict[str, Any]], dispositions: dict[str, dict[str, Any]], generation_by_ref: dict[str, str], data_requirements: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, row in enumerate(ensure_list(rows, "semantic_coverage_items")):
        if not isinstance(row, dict):
            raise InvalidInput(f"semantic_coverage_items[{index}]が不正です")
        required = {"draft_key", "model_key", "identity_action", "reuse_semantic_item_key", "reuse_ci_id", "source_target_versions", "item_text", "authority_refs", "reference_refs", "priority", "priority_override_reason", "expected_result_root", "test_data_requirement_refs"}
        reject_unknown(row, required)
        if set(row) != required:
            raise InvalidInput("semantic itemの必須fieldが不足しています")
        draft_key = ensure_nonempty_string(row["draft_key"], "semantic item draft_key")
        if draft_key in seen:
            raise InvalidInput("semantic item draft_keyが重複しています")
        seen.add(draft_key)
        model_key = ensure_nonempty_string(row["model_key"], "semantic item model_key")
        if model_key not in models:
            raise InvalidInput("semantic itemがunknown modelを参照しています")
        action = row["identity_action"]
        if action not in {"new", "reuse"}:
            raise InvalidInput("semantic item identity_actionが不正です")
        if action == "new" and (row["reuse_semantic_item_key"] is not None or row["reuse_ci_id"] is not None):
            raise InvalidInput("new semantic itemのreuse fieldはnullである必要があります")
        if action == "reuse" and (not isinstance(row["reuse_semantic_item_key"], str) or not row["reuse_semantic_item_key"] or not isinstance(row["reuse_ci_id"], str)):
            raise InvalidInput("reuse semantic itemのreuse fieldが不正です")
        source_versions: list[dict[str, Any]] = []
        source_seen: set[str] = set()
        for source in ensure_list(row["source_target_versions"], "semantic source_target_versions"):
            if not isinstance(source, dict) or set(source) != {"target_ref", "target_content_fingerprint", "generation_fingerprint"}:
                raise InvalidInput("semantic source_target_versionsが不正です")
            ref = _digest(source["target_ref"], "semantic target_ref")
            if ref in source_seen or ref not in targets:
                raise InvalidInput("semantic source targetがunknownまたは重複しています")
            source_seen.add(ref)
            target = targets[ref]
            if target["model_key"] != model_key or source["target_content_fingerprint"] != target["target_content_fingerprint"] or source["generation_fingerprint"] != generation_by_ref[ref]:
                raise InvalidInput("semantic source target versionがcurrentと不一致です")
            source_versions.append(canonicalize(source))
        if action == "new" and not source_versions and models[model_key]["model_type"] not in {"error-guessing"}:
            # Source-less semantic items are reserved for semantic-only or
            # whole-model fallback models; runtime-backed items must identify
            # the current target(s) they close.
            if any(target["model_key"] == model_key for target in targets.values()):
                raise InvalidInput("runtime-backed semantic itemにはsource targetが必要です")
        if any(ref in dispositions for ref in source_seen):
            raise InvalidInput("Disposition済みtargetをsemantic itemへ同時指定できません")
        if row["priority"] not in PRIORITY_ORDER:
            raise InvalidInput("semantic item priorityが不正です")
        priority_override_reason = row["priority_override_reason"]
        if priority_override_reason is not None and (not isinstance(priority_override_reason, str) or not priority_override_reason.strip()):
            raise InvalidInput("priority_override_reasonが不正です")
        expected_root = row["expected_result_root"]
        if expected_root is not None and (not isinstance(expected_root, str) or STABLE_COMPONENT_RE.fullmatch(expected_root) is None or ":" in expected_root):
            raise InvalidInput("expected_result_rootが不正です")
        data_refs = row["test_data_requirement_refs"]
        if not isinstance(data_refs, list) or len(set(data_refs)) != len(data_refs) or not all(isinstance(item, str) and item for item in data_refs) or any(item not in data_requirements for item in data_refs):
            raise InvalidInput("semantic test_data_requirement_refsがunknownまたは不正です")
        normalized = {
            "draft_key": draft_key, "model_key": model_key, "identity_action": action,
            "reuse_semantic_item_key": row["reuse_semantic_item_key"], "reuse_ci_id": row["reuse_ci_id"],
            "source_target_versions": sorted(source_versions, key=lambda item: item["target_ref"]),
            "item_text": ensure_nonempty_string(row["item_text"], "semantic item_text"),
            "authority_refs": sorted(set(row["authority_refs"])) if isinstance(row["authority_refs"], list) and all(isinstance(item, str) and item for item in row["authority_refs"]) else (_ for _ in ()).throw(InvalidInput("semantic authority_refsが不正です")),
            "reference_refs": sorted(set(row["reference_refs"])) if isinstance(row["reference_refs"], list) and all(isinstance(item, str) and item for item in row["reference_refs"]) else (_ for _ in ()).throw(InvalidInput("semantic reference_refsが不正です")),
            "priority": row["priority"], "priority_override_reason": priority_override_reason,
            "expected_result_root": expected_root, "test_data_requirement_refs": sorted(data_refs),
        }
        normalized["semantic_content_fingerprint"] = sha256_digest({key: normalized[key] for key in ("model_key", "source_target_versions", "item_text", "authority_refs", "reference_refs", "priority", "priority_override_reason", "expected_result_root", "test_data_requirement_refs")})
        result.append(canonicalize(normalized))
    return sorted(result, key=lambda item: (item["model_key"], item["draft_key"]))


def _validate_merge_groups(rows: Any, targets: dict[str, dict[str, Any]], annotations: dict[str, dict[str, Any]], dispositions: dict[str, dict[str, Any]], data_requirements: dict[str, dict[str, Any]], tcn_id: str) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = {}
    for index, row in enumerate(ensure_list(rows, "merge_groups")):
        if not isinstance(row, dict):
            raise InvalidInput(f"merge_groups[{index}]が不正です")
        reject_unknown(row, {"merge_group_key", "model_key", "target_refs", "target_versions"})
        key = ensure_nonempty_string(row["merge_group_key"], "merge_group_key")
        if key in groups:
            raise InvalidInput("merge_group_keyが重複しています")
        refs = ensure_list(row["target_refs"], "merge_group.target_refs")
        if len(refs) < 2 or len(set(refs)) != len(refs):
            raise InvalidInput("merge_group.target_refsは2件以上の一意配列が必要です")
        versions = ensure_list(row["target_versions"], "merge_group.target_versions")
        version_map: dict[str, dict[str, Any]] = {}
        for version in versions:
            if not isinstance(version, dict) or set(version) != {"target_ref", "target_content_fingerprint", "generation_fingerprint", "execution_fingerprint"}:
                raise InvalidInput("merge_group.target_versionsが不正です")
            ref = _digest(version["target_ref"], "merge target_ref")
            if ref in version_map or ref not in targets or ref in dispositions:
                raise InvalidInput("merge group targetが不正です")
            version_map[ref] = version
        if set(refs) != set(version_map) or any(not targets[ref]["materializable"] or targets[ref]["model_key"] != row["model_key"] for ref in refs):
            raise InvalidInput("merge group target version集合が不一致です")
        fingerprints = {version_map[ref]["execution_fingerprint"] for ref in refs}
        roots = {annotations.get(ref, {}).get("expected_result_root") for ref in refs}
        if len(fingerprints) != 1 or len(roots) != 1 or any(version_map[ref]["target_content_fingerprint"] != targets[ref]["target_content_fingerprint"] or version_map[ref]["generation_fingerprint"] != targets[ref]["generation_fingerprint"] or version_map[ref]["execution_fingerprint"] != targets[ref]["execution_fingerprint"] for ref in refs):
            raise InvalidInput("merge groupのcurrent version / execution / expected resultが一致しません")
        requirement_rows_by_ref = {
            data_ref: data_requirements[data_ref]
            for ref in refs
            for data_ref in annotations[ref].get("test_data_requirement_refs", [])
        }
        by_dimension: dict[str, list[dict[str, Any]]] = {}
        for requirement in requirement_rows_by_ref.values():
            by_dimension.setdefault(requirement["dimension_key"], []).append(requirement)
        for dimension_rows in by_dimension.values():
            if not constraint_intersection_compatible(dimension_rows):
                raise InvalidInput("merge groupのtest data requirement intersectionが不成立です")
        groups[key] = sorted(refs)
    return groups


def _build(input_value: dict[str, Any], metadata: dict[str, Any]) -> dict[str, Any]:
    required = {"tcn_id", "active_model_metadata", "models", "semantic_coverage_items", "target_annotations", "target_dispositions", "test_data_requirements", "previous_target_id_map", "previous_semantic_ci_map", "previous_ci_ids", "previous_expected_result_roots", "merge_groups"}
    optional = {"legacy_ci_ids", "legacy_ci_seed"}
    reject_unknown(input_value, required, optional)
    tcn_id = _tcn_id(input_value["tcn_id"])
    models_rows = _validate_model_metadata(input_value["active_model_metadata"], tcn_id)
    current_upstream_entities = validate_upstream_entities(metadata)
    current_model_entities = {
        (entity["skill"], entity["entity_type"], entity["entity_ref"]): entity
        for entity in current_upstream_entities
        if entity["skill"] == SKILL and entity["entity_type"] == "model"
    }
    for model in models_rows:
        entity = current_model_entities.get((SKILL, "model", model["model_key"]))
        if entity is None or entity["content_fingerprint"] != model["content_fingerprint"]:
            raise InvalidInput("active_model_metadataのcontent_fingerprintがcurrent model Entityと不一致です")
        content = entity["content"]
        if (
            entity["entity_ref"] != model["model_key"]
            or content.get("model_key") != model["model_key"]
            or content.get("model_type") != model["model_type"]
            or content.get("technique_slug") != model["technique_slug"]
            or content.get("parent_tcn_id") != tcn_id
        ):
            raise InvalidInput("active_model_metadataがcurrent model Machine Entityと不一致です")
    models = {row["model_key"]: row for row in models_rows}
    model_results = _validate_model_results(input_value["models"], models, tcn_id)
    targets = _validate_targets(model_results, models, tcn_id)
    generation_by_ref = {ref: row["generation_fingerprint"] for ref, row in targets.items()}
    data_requirements = _validate_test_data_requirements(input_value["test_data_requirements"], targets, models)
    annotations = _validate_annotations(input_value["target_annotations"], targets, generation_by_ref)
    for ref, annotation in annotations.items():
        if any(data_ref not in data_requirements for data_ref in annotation["test_data_requirement_refs"]):
            raise InvalidInput("target annotationがunknown test data requirementを参照しています")
    dispositions = _validate_dispositions(input_value["target_dispositions"], targets, generation_by_ref)
    if annotations:
        materializable_refs = {ref for ref, target in targets.items() if target["materializable"] and ref not in dispositions}
        if materializable_refs != set(annotations):
            raise InvalidInput("materializable targetのannotationが不足または余分です")
    for ref, target in targets.items():
        if not target["materializable"] and (ref in annotations or ref in dispositions):
            raise InvalidInput("non-materializable targetはannotation / disposition対象外です")
    semantic_items = _validate_semantic_items(input_value["semantic_coverage_items"], models, targets, dispositions, generation_by_ref, data_requirements)
    merge_groups = _validate_merge_groups(input_value["merge_groups"], targets, annotations, dispositions, data_requirements, tcn_id)
    previous_map = _validate_previous_map(input_value["previous_target_id_map"], tcn_id)
    previous_ci_rows = []
    ci_state_seen: set[str] = set()
    for index, row in enumerate(ensure_list(input_value["previous_ci_ids"], "previous_ci_ids")):
        if not isinstance(row, dict) or set(row) != {"ci_id", "status"} or row["status"] not in {"active", "deleted"}:
            raise InvalidInput(f"previous_ci_ids[{index}]が不正です")
        ci_id = _ci_id(row["ci_id"], tcn_id)
        if ci_id in ci_state_seen:
            raise InvalidInput("previous_ci_idsが重複しています")
        ci_state_seen.add(ci_id)
        previous_ci_rows.append({"ci_id": ci_id, "status": row["status"]})
    previous_roots = ensure_list(input_value["previous_expected_result_roots"], "previous_expected_result_roots")
    previous_root_state: dict[str, str] = {}
    for index, row in enumerate(previous_roots):
        if not isinstance(row, dict) or set(row) != {"expected_result_root", "status"} or row["status"] not in {"active", "deleted"}:
            raise InvalidInput(f"previous_expected_result_roots[{index}]が不正です")
        root = ensure_nonempty_string(row["expected_result_root"], "previous_expected_result_roots.expected_result_root")
        if STABLE_COMPONENT_RE.fullmatch(root) is None or ":" in root:
            raise InvalidInput("previous_expected_result_roots.expected_result_rootが不正です")
        if root in previous_root_state:
            raise InvalidInput("previous_expected_result_rootsが重複しています")
        previous_root_state[root] = row["status"]
    previous_semantic_rows: list[dict[str, Any]] = []
    previous_semantic_seen: set[str] = set()
    for index, row in enumerate(ensure_list(input_value.get("previous_semantic_ci_map", []), "previous_semantic_ci_map")):
        if not isinstance(row, dict) or set(row) != {"semantic_item_key", "model_key", "ci_id", "mapping_status", "semantic_content_fingerprint"}:
            raise InvalidInput(f"previous_semantic_ci_map[{index}]が不正です")
        key = ensure_nonempty_string(row["semantic_item_key"], "semantic_item_key")
        if key in previous_semantic_seen or row["mapping_status"] not in {"active", "inactive"}:
            raise InvalidInput("previous_semantic_ci_mapが不正または重複しています")
        previous_semantic_seen.add(key)
        _ci_id(row["ci_id"], tcn_id)
        _digest(row["semantic_content_fingerprint"], "semantic_content_fingerprint")
        previous_semantic_rows.append(canonicalize(row))
    legacy_ids = input_value.get("legacy_ci_ids")
    legacy_seed = input_value.get("legacy_ci_seed")
    if legacy_ids is not None:
        if input_value["previous_target_id_map"] or previous_semantic_rows or input_value["previous_ci_ids"]:
            raise InvalidInput("legacy初回昇格ではnormal previous stateを併用できません")
        seeded = seed_legacy_ids(legacy_ids, CI_ID_RE, "legacy_ci_ids")
        previous_ci_rows = [{"ci_id": row["id"], "status": row["status"]} for row in seeded]
        ci_state_seen = {row["ci_id"] for row in previous_ci_rows}
        for index, row in enumerate(ensure_list(legacy_seed or [], "legacy_ci_seed")):
            if not isinstance(row, dict) or set(row) != {"ci_id", "model_key", "source_kind", "target_ref", "semantic_item_draft_key"}:
                raise InvalidInput(f"legacy_ci_seed[{index}]が不正です")
            _ci_id(row["ci_id"], tcn_id)
            if row["ci_id"] not in ci_state_seen or row["model_key"] not in models:
                raise InvalidInput("legacy_ci_seedのidentityが不正です")
            if row["source_kind"] == "runtime_target":
                if row["target_ref"] not in targets or row["semantic_item_draft_key"] is not None:
                    raise InvalidInput("legacy runtime target seedが不正です")
            elif row["source_kind"] == "semantic_item":
                if row["target_ref"] is not None or not isinstance(row["semantic_item_draft_key"], str):
                    raise InvalidInput("legacy semantic seedが不正です")
            else:
                raise InvalidInput("legacy_ci_seed source_kindが不正です")
    else:
        if legacy_seed not in (None, []):
            raise InvalidInput("legacy_ci_seedはlegacy_ci_idsと同時に指定します")

    previous_by_ref = {row["target_ref"]: row for row in previous_map}
    used_ci = set(ci_state_seen)
    for row in previous_map:
        if row["ci_id"] in used_ci:
            continue
        used_ci.add(row["ci_id"])
    max_suffix = max((_ci_suffix(ci_id) for ci_id in used_ci), default=0)
    active_mappings: list[dict[str, Any]] = []
    mapping_state: dict[str, dict[str, Any]] = {}
    stale_ci_ids: set[str] = set()
    group_for_ref = {ref: group_key for group_key, refs in merge_groups.items() for ref in refs}
    assigned_ci: dict[str, str] = {}

    def allocate_ci() -> str:
        nonlocal max_suffix
        while True:
            max_suffix += 1
            candidate = f"{tcn_id}-CI{max_suffix:02d}"
            if candidate not in used_ci:
                used_ci.add(candidate)
                return candidate

    def assign_target(ref: str, ci_id: str) -> None:
        target = targets[ref]
        previous = previous_by_ref.get(ref)
        if previous is not None and previous["target_content_fingerprint"] != target["target_content_fingerprint"]:
            stale_ci_ids.add(previous["ci_id"])
        row = {"target_ref": ref, "target_content_fingerprint": target["target_content_fingerprint"], "generation_fingerprint": target["generation_fingerprint"], "execution_fingerprint": target["execution_fingerprint"], "model_key": target["model_key"], "target_key": target["target_key"], "ci_id": ci_id}
        active_mappings.append(row)
        mapping_state[ref] = {**row, "mapping_status": "active"}

    ordered_groups = sorted(
        merge_groups,
        key=lambda group_key: (
            targets[merge_groups[group_key][0]]["model_key"],
            "runtime_target",
            group_key,
        ),
    )
    for group_key in ordered_groups:
        refs = merge_groups[group_key]
        previous_ids = sorted({previous_by_ref[ref]["ci_id"] for ref in refs if ref in previous_by_ref}, key=lambda value: (_ci_suffix(value), value))
        ci_id = previous_ids[0] if previous_ids else allocate_ci()
        stale_ci_ids.update(previous_ids[1:])
        for ref in refs:
            assign_target(ref, ci_id)
            assigned_ci[ref] = ci_id
    for ref in sorted(targets, key=lambda value: (targets[value]["model_key"], targets[value]["target_key"])):
        target = targets[ref]
        if not target["materializable"] or ref in dispositions or ref in group_for_ref:
            continue
        previous = previous_by_ref.get(ref)
        candidate_ci = previous["ci_id"] if previous is not None else None
        if candidate_ci is None or candidate_ci in assigned_ci.values():
            candidate_ci = allocate_ci()
        assign_target(ref, candidate_ci)
        assigned_ci[ref] = candidate_ci
    for previous in previous_map:
        if previous["target_ref"] not in mapping_state:
            mapping_state[previous["target_ref"]] = {**previous, "mapping_status": "inactive"}
            if previous["mapping_status"] == "active":
                stale_ci_ids.add(previous["ci_id"])

    previous_semantic_by_key = {row["semantic_item_key"]: row for row in previous_semantic_rows}
    semantic_mapping_state: dict[str, dict[str, Any]] = {}
    active_semantic: list[dict[str, Any]] = []
    used_identity_ci: dict[str, str] = {row["ci_id"]: f"target:{row['target_ref']}" for row in active_mappings}
    current_semantic_keys: set[str] = set()
    for item in semantic_items:
        previous = previous_semantic_by_key.get(item["reuse_semantic_item_key"]) if item["identity_action"] == "reuse" else None
        if item["identity_action"] == "reuse":
            if previous is None or previous["model_key"] != item["model_key"] or previous["ci_id"] != item["reuse_ci_id"]:
                raise InvalidInput("semantic item reuse identityがprevious stateと不一致です")
            ci_id = previous["ci_id"]
            semantic_item_key = previous["semantic_item_key"]
            if ci_id in used_identity_ci and used_identity_ci[ci_id] != f"semantic:{semantic_item_key}":
                raise InvalidInput("同一CIを別identityへreuseできません")
            if previous["semantic_content_fingerprint"] != item["semantic_content_fingerprint"]:
                stale_ci_ids.add(ci_id)
        else:
            ci_id = allocate_ci()
            semantic_item_key = f"semantic:{ci_id}"
        current_semantic_keys.add(semantic_item_key)
        used_identity_ci[ci_id] = f"semantic:{semantic_item_key}"
        active_row = {**item, "semantic_item_key": semantic_item_key, "ci_id": ci_id, "mapping_status": "active"}
        active_semantic.append(active_row)
        semantic_mapping_state[semantic_item_key] = active_row
    for previous in previous_semantic_rows:
        if previous["semantic_item_key"] not in current_semantic_keys:
            semantic_mapping_state[previous["semantic_item_key"]] = {**previous, "mapping_status": "inactive"}
            if previous["mapping_status"] == "active":
                stale_ci_ids.add(previous["ci_id"])

    active_ci_ids = {row["ci_id"] for row in active_mappings}
    active_ci_ids.update(row["ci_id"] for row in active_semantic)
    ci_state = {row["ci_id"]: row["status"] for row in previous_ci_rows}
    for ci_id in stale_ci_ids:
        if ci_id not in active_ci_ids:
            ci_state[ci_id] = "deleted"
    for ci_id in active_ci_ids:
        ci_state[ci_id] = "active"
    ci_id_state = [{"ci_id": ci_id, "status": status} for ci_id, status in sorted(ci_state.items())]

    current_roots = {row["expected_result_root"] for row in annotations.values() if row["expected_result_root"] is not None}
    current_roots.update(row["expected_result_root"] for row in active_semantic if row["expected_result_root"] is not None)
    for root in current_roots:
        previous_root_state[root] = "active"
    for root, status in list(previous_root_state.items()):
        if status == "active" and root not in current_roots:
            previous_root_state[root] = "deleted"
    expected_result_root_state = [{"expected_result_root": root, "status": status} for root, status in sorted(previous_root_state.items())]

    ci_entities = []
    current_entities_by_identity = {
        (entity["skill"], entity["entity_type"], entity["entity_ref"]): entity
        for entity in current_upstream_entities
    }
    data_refs = sorted(data_requirements)
    data_identities = [(SKILL, "test_data_requirement", data_ref) for data_ref in data_refs]
    resolve_entity_dependencies(
        data_identities,
        current_upstream_entities,
        require_all=metadata["input_mode"] == "artifact",
    )
    for data_ref, expected_content in data_requirements.items():
        current = current_entities_by_identity.get((SKILL, "test_data_requirement", data_ref))
        if current is None:
            continue
        canonical_content = canonicalize(expected_content)
        if current["content"] != canonical_content or current["content_fingerprint"] != sha256_digest(canonical_content):
            raise InvalidInput("current test_data_requirement Machine Entityがnormalized requirementと不一致です")

    def ci_dependencies(model_key: str, requirement_refs: list[str]) -> list[dict[str, str]]:
        identities = [
            (SKILL, "tcn", tcn_id),
            (SKILL, "model", model_key),
            *((SKILL, "test_data_requirement", ref) for ref in requirement_refs),
        ]
        return resolve_entity_dependencies(
            identities,
            current_upstream_entities,
            require_all=metadata["input_mode"] == "artifact",
        )
    targets_by_ci: dict[str, list[dict[str, Any]]] = {}
    for mapping in active_mappings:
        targets_by_ci.setdefault(mapping["ci_id"], []).append(mapping)
    target_by_ref = targets
    for ci_id in sorted(targets_by_ci):
        mappings = sorted(targets_by_ci[ci_id], key=lambda row: row["target_ref"])
        first = mappings[0]
        target = target_by_ref[first["target_ref"]]
        annotation = annotations.get(first["target_ref"], {})
        covered_targets = [
            {
                "target_ref": row["target_ref"],
                "target_key": row["target_key"],
                "target_content_fingerprint": row["target_content_fingerprint"],
                "execution_fingerprint": row["execution_fingerprint"],
            }
            for row in mappings
        ]
        content = {
            "ci_id": ci_id,
            "tcn_id": tcn_id,
            "model_key": first["model_key"],
            "source_kind": "runtime_target",
            "covered_targets": covered_targets,
            "execution": target["execution"],
            "semantic_item_key": None,
            "semantic_item_text": None,
            "semantic_source_targets": [],
            "priority": annotation.get("priority"),
            "priority_override_reason": annotation.get("priority_override_reason"),
            "expected_result_root": annotation.get("expected_result_root"),
            "authority_refs": sorted(set(target.get("authority_refs", []) + annotation.get("authority_refs", []))),
            "reference_refs": annotation.get("reference_refs", []),
            "test_data_requirement_refs": annotation.get("test_data_requirement_refs", []),
            "status": "active",
        }
        target_dependencies = ci_dependencies(first["model_key"], annotation.get("test_data_requirement_refs", []))
        ci_entities.append(
            make_machine_entity(
                SKILL,
                "ci",
                ci_id,
                content,
                model_key=first["model_key"],
                upstream_entity_dependencies=target_dependencies,
                runtime_dependencies=[{"skill": SKILL, "runtime_unit_key": f"artifact:materialize_coverage:{tcn_id}", "generation_fingerprint": "__CURRENT__"}],
            )
        )

    for item in sorted(active_semantic, key=lambda row: row["semantic_item_key"]):
        source_targets = sorted(item["source_target_versions"], key=lambda row: row["target_ref"])
        content = {
            "ci_id": item["ci_id"], "tcn_id": tcn_id, "model_key": item["model_key"], "source_kind": "semantic_item", "covered_targets": [],
            "execution": None, "semantic_item_key": item["semantic_item_key"], "semantic_item_text": item["item_text"], "semantic_source_targets": source_targets,
            "priority": item["priority"], "priority_override_reason": item["priority_override_reason"], "expected_result_root": item["expected_result_root"],
            "authority_refs": item["authority_refs"], "reference_refs": item["reference_refs"], "test_data_requirement_refs": item["test_data_requirement_refs"], "status": "active",
        }
        item_dependencies = ci_dependencies(item["model_key"], item["test_data_requirement_refs"])
        ci_entities.append(make_machine_entity(SKILL, "ci", item["ci_id"], content, model_key=item["model_key"], upstream_entity_dependencies=item_dependencies, runtime_dependencies=[{"skill": SKILL, "runtime_unit_key": f"artifact:materialize_coverage:{tcn_id}", "generation_fingerprint": "__CURRENT__"}]))

    model_completion = []
    for model_key in sorted(models):
        required_refs = sorted(ref for ref, target in targets.items() if target["model_key"] == model_key and target["materializable"])
        closed_refs = sorted(ref for ref in required_refs if ref in mapping_state and mapping_state[ref]["mapping_status"] == "active") + sorted(ref for ref in required_refs if ref in dispositions)
        model_ci_ids = sorted({row["ci_id"] for row in active_mappings if row["model_key"] == model_key})
        semantic_keys = sorted(row["semantic_item_key"] for row in active_semantic if row["model_key"] == model_key)
        model_ci_ids = sorted(set(model_ci_ids) | {row["ci_id"] for row in active_semantic if row["model_key"] == model_key})
        model_type = models[model_key]["model_type"]
        model_result = model_results.get(model_key)
        if model_result is not None and model_result.get("runtime_status") == "unsupported":
            # Whole-model unsupported is closed by workflow-level unsupported
            # evidence, not by a fabricated successful model_completion row.
            continue
        summary_complete = True
        if model_type == "error-guessing":
            # No runtime row exists for semantic-only Error Guessing.  Its
            # closure is represented solely by semantic CI items below.
            summary_complete = True
        elif model_type == "crud":
            summary = model_result.get("coverage_summary", {})
            summary_complete = bool(summary.get("complete") and summary.get("completeness", {}).get("complete") and summary.get("consistency", {}).get("complete"))
        elif model_type in {"random", "metamorphic"}:
            summary_complete = bool(model_result.get("completion_summary", {}).get("complete"))
        elif model_type not in {"classification", "cause-effect", "schema", "ui"}:
            summary_complete = bool(model_result.get("coverage_summary", {}).get("complete", True))
        if model_type == "error-guessing":
            materialize_complete = bool(semantic_keys)
        elif model_type in {"classification", "cause-effect", "schema", "ui"} and not required_refs:
            materialize_complete = True
        else:
            materialize_complete = bool(required_refs) and set(required_refs).issubset(set(closed_refs)) and summary_complete
        if model_result is not None and model_result.get("support_status") == "partial" and model_result.get("unsupported_items"):
            materialize_complete = False
        model_completion.append({"model_key": model_key, "required_target_refs": required_refs, "closed_target_refs": sorted(set(closed_refs)), "active_ci_ids": model_ci_ids, "semantic_item_keys": semantic_keys, "materialize_complete": materialize_complete})

    issues = []
    if stale_ci_ids:
        issues.append({"issue_type": "stale_target_mapping", "blocking": True, "ci_ids": sorted(stale_ci_ids), "authority_refs": []})
    incomplete_models = [row["model_key"] for row in model_completion if not row["materialize_complete"]]
    if incomplete_models:
        issues.append({"issue_type": "model_materialize_incomplete", "blocking": True, "model_keys": sorted(incomplete_models), "authority_refs": []})
    target_mapping_snapshot = [
        {key: row[key] for key in ("target_ref", "model_key", "target_key", "target_content_fingerprint", "ci_id", "mapping_status")}
        for row in sorted(mapping_state.values(), key=lambda item: item["target_ref"])
    ]
    return {
        "runtime_status": "ok",
        "support_status": "supported",
        "result_status": "unresolved" if stale_ci_ids or incomplete_models else "ready",
        "runtime_required": True,
        "deterministic_generated": True,
        "payload": {
            "target_id_map": sorted(active_mappings, key=lambda row: row["target_ref"]),
            "target_mapping_state": target_mapping_snapshot,
            "semantic_ci_mapping_state": sorted([{key: row[key] for key in ("semantic_item_key", "model_key", "ci_id", "mapping_status", "semantic_content_fingerprint")} for row in semantic_mapping_state.values()], key=lambda row: row["semantic_item_key"]),
            "ci_id_state": ci_id_state,
            "expected_result_root_state": expected_result_root_state,
            "test_data_requirements": sorted(data_requirements.values(), key=lambda row: row["data_ref"]),
            "disposed_target_refs": sorted(dispositions.values(), key=lambda row: row["target_ref"]),
            "coverage_item_rows": sorted(ci_entities, key=lambda row: row["entity_ref"]),
            "stale_ci_ids": sorted(stale_ci_ids),
            "model_completion": model_completion,
            "entities": sorted(ci_entities, key=lambda row: row["entity_ref"]),
        },
        "issues": issues,
    }


def handler(input_value: dict[str, Any], metadata: dict[str, Any]) -> dict[str, Any]:
    tcn_id = _tcn_id(input_value.get("tcn_id"))
    if metadata["model_key"] is not None or metadata["runtime_unit_key"] != f"artifact:materialize_coverage:{tcn_id}" or metadata["scope_key"] != tcn_id or metadata["input_mode"] != "artifact":
        raise InvalidInput("materialize_coverageのruntime metadataが不正です")
    return _build(input_value, metadata)


if __name__ == "__main__":
    raise SystemExit(
        run_cli(
            handler,
            skill=SKILL,
            generator=GENERATOR,
            generator_contract_version=GENERATOR_CONTRACT_VERSION,
            generator_path=SCRIPT_PATH,
            aggregate=True,
        )
    )
