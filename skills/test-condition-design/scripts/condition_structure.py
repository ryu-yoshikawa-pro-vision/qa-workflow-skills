"""Deterministic TCN and model identity / structure runtime."""

from __future__ import annotations

from pathlib import Path
import re
import sys
from typing import Any

from runtime_contract import (
    InvalidInput,
    MODEL_TYPES,
    TECHNIQUE_SLUGS,
    TCN_ID_RE,
    TR_ID_RE,
    allocate_stable_id,
    canonicalize,
    ensure_int,
    ensure_list,
    ensure_nonempty_string,
    make_machine_entity,
    normalize_machine_entity_disposition,
    reject_unknown,
    resolve_entity_dependencies,
    run_cli,
    seed_legacy_ids,
    validate_upstream_entities,
)


SKILL = "test-condition-design"
GENERATOR = "condition_structure"
GENERATOR_CONTRACT_VERSION = "condition-structure-v1"
SCRIPT_PATH = Path(__file__).resolve()
ADAPTER_TYPES = {"classification", "cause-effect", "schema", "ui"}
MODEL_TECHNIQUE = {
    "ep": "ep",
    "bva": "bva",
    "domain": "domain",
    "decision": "decision",
    "comb": "comb",
    "state": "state",
    "flow": "scenario",
    "crud": "crud",
    "syntax": "syntax",
    "random": "random",
    "metamorphic": "metamorphic",
    "error-guessing": "error-guessing",
}
ID_PATTERNS = {
    "tcn": re.compile(r"^TCN-(\d{3})$"),
    "model": re.compile(r"^([a-z][a-z0-9-]*)-(\d{3,})$"),
}


def _validate_id(value: Any, kind: str, name: str) -> str:
    if not isinstance(value, str) or ID_PATTERNS[kind].fullmatch(value) is None:
        raise InvalidInput(f"{name}の形式が不正です")
    return value


def _unique_strings(value: Any, name: str) -> list[str]:
    rows = ensure_list(value, name)
    if not all(isinstance(row, str) and row for row in rows):
        raise InvalidInput(f"{name}は非空stringのarrayである必要があります")
    if len(set(rows)) != len(rows):
        raise InvalidInput(f"{name}が重複しています")
    return rows


def _validate_state_rows(rows: Any, kind: str) -> list[dict[str, Any]]:
    values = ensure_list(rows, f"previous_{kind}_ids")
    result = []
    seen: set[str] = set()
    if kind == "tcn":
        allowed = {"tcn_id", "status"}
        for index, row in enumerate(values):
            if not isinstance(row, dict):
                raise InvalidInput(f"previous_tcn_ids[{index}]が不正です")
            reject_unknown(row, allowed)
            ref = _validate_id(row["tcn_id"], "tcn", f"previous_tcn_ids[{index}].tcn_id")
            if row["status"] not in {"active", "deleted"} or ref in seen:
                raise InvalidInput("previous_tcn_idsのidentity/statusが不正です")
            seen.add(ref)
            result.append({"tcn_id": ref, "status": row["status"]})
    else:
        allowed = {"model_key", "model_type", "technique_slug", "parent_tcn_id", "selection_source", "selection_key", "derived_from_model_key", "status"}
        for index, row in enumerate(values):
            if not isinstance(row, dict):
                raise InvalidInput(f"previous_model_keys[{index}]が不正です")
            reject_unknown(row, allowed)
            ref = _validate_id(row["model_key"], "model", f"previous_model_keys[{index}].model_key")
            _validate_model_metadata(row, f"previous_model_keys[{index}]")
            _validate_id(row["parent_tcn_id"], "tcn", f"previous_model_keys[{index}].parent_tcn_id")
            if row["status"] not in {"active", "deleted"} or ref in seen:
                raise InvalidInput("previous_model_keysのidentity/statusが不正です")
            seen.add(ref)
            result.append(canonicalize(row))
    return result


def _validate_model_metadata(row: dict[str, Any], name: str) -> None:
    model_key = row.get("model_key")
    model_type = row.get("model_type")
    _validate_id(model_key, "model", f"{name}.model_key")
    if model_type not in MODEL_TYPES or not str(model_key).startswith(model_type + "-"):
        raise InvalidInput(f"{name}.model_type / model_keyが不一致です")
    technique_slug = row.get("technique_slug")
    selection_source = row.get("selection_source")
    selection_key = row.get("selection_key")
    derived = row.get("derived_from_model_key")
    if model_type in ADAPTER_TYPES:
        if any(value is not None for value in (technique_slug, selection_source, selection_key, derived)):
            raise InvalidInput(f"{name}のadapter metadataが不正です")
    else:
        if technique_slug != MODEL_TECHNIQUE.get(model_type) or technique_slug not in TECHNIQUE_SLUGS:
            raise InvalidInput(f"{name}.technique_slugが不正です")
        if selection_source not in {"analysis", "condition_design", "user"}:
            raise InvalidInput(f"{name}.selection_sourceが不正です")
        if selection_source == "analysis":
            ensure_nonempty_string(selection_key, f"{name}.selection_key")
        elif selection_key is not None:
            raise InvalidInput(f"{name}.selection_keyはnullである必要があります")
    if derived is not None:
        _validate_id(derived, "model", f"{name}.derived_from_model_key")


def _validate_tr_rows(rows: Any) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for index, row in enumerate(ensure_list(rows, "test_requirements")):
        if not isinstance(row, dict):
            raise InvalidInput(f"test_requirements[{index}]が不正です")
        reject_unknown(row, {"tr_id", "priority", "authority_refs", "risk_refs"})
        tr_id = row.get("tr_id")
        if not isinstance(tr_id, str) or TR_ID_RE.fullmatch(tr_id) is None:
            raise InvalidInput(f"test_requirements[{index}].tr_idの形式が不正です")
        if tr_id in result:
            raise InvalidInput("test_requirements.tr_idが重複しています")
        for field in ("authority_refs", "risk_refs"):
            _unique_strings(row.get(field), f"test_requirements[{index}].{field}")
        result[tr_id] = canonicalize(row)
    return result


def _validate_selection_rows(rows: Any) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for index, row in enumerate(ensure_list(rows, "technique_selections")):
        if not isinstance(row, dict):
            raise InvalidInput(f"technique_selections[{index}]が不正です")
        required = {"selection_key", "selected_techniques", "undetermined_signal_closures", "status"}
        reject_unknown(row, required)
        key = ensure_nonempty_string(row["selection_key"], f"technique_selections[{index}].selection_key")
        if key in result:
            raise InvalidInput("selection_keyが重複しています")
        selected = _unique_strings(row["selected_techniques"], f"technique_selections[{index}].selected_techniques")
        if any(value not in TECHNIQUE_SLUGS for value in selected):
            raise InvalidInput("selected_techniquesに未知のtechnique slugがあります")
        closures = ensure_list(row["undetermined_signal_closures"], f"technique_selections[{index}].undetermined_signal_closures")
        if row["status"] not in {"active", "blocked", "unresolved"}:
            raise InvalidInput("technique selection statusが不正です")
        if row["status"] == "active":
            for closure in closures:
                if not isinstance(closure, dict) or closure.get("handling") != "selection_not_affected" or not closure.get("reason") or closure.get("question_id") is not None:
                    raise InvalidInput("active technique selectionのsignal closureが不正です")
        result[key] = canonicalize(row)
    return result


def _validate_dispositions(rows: Any, current_entities: list[dict], input_mode: str) -> list[tuple[dict, list[dict[str, str]]]]:
    result: list[tuple[dict, list[dict[str, str]]]] = []
    disposed: set[str] = set()
    for index, row in enumerate(ensure_list(rows, "requirement_dispositions")):
        normalized, dependencies = normalize_machine_entity_disposition(
            row,
            current_entities,
            allowed_handlings={"対象外", "別テストレベル", "残存リスク", "ブロック中", "重複"},
            allowed_upstream_entity_types={"tr"},
            input_mode=input_mode,
        )
        upstream = normalized["upstream_entity"]
        if upstream["skill"] != "test-requirement-design":
            raise InvalidInput("condition structure disposition upstream_entity skill/typeが不一致です")
        tr_id = ensure_nonempty_string(upstream["entity_ref"], "requirement disposition tr_id")
        if tr_id in disposed:
            raise InvalidInput("同じTRへのdispositionが重複しています")
        disposed.add(tr_id)
        result.append((normalized, dependencies))
    return result


def _validate_tcn_drafts(rows: Any) -> list[dict[str, Any]]:
    result = []
    seen: set[str] = set()
    required = {"draft_key", "identity_action", "reuse_id", "tr_refs", "condition", "category", "technique_slugs", "coverage_criterion", "authority_refs", "risk_refs", "priority", "priority_override_reason"}
    for index, row in enumerate(ensure_list(rows, "test_conditions")):
        if not isinstance(row, dict):
            raise InvalidInput(f"test_conditions[{index}]が不正です")
        reject_unknown(row, required)
        key = ensure_nonempty_string(row["draft_key"], f"test_conditions[{index}].draft_key")
        if key in seen:
            raise InvalidInput("TCN draft_keyが重複しています")
        seen.add(key)
        if row["identity_action"] not in {"reuse", "new"}:
            raise InvalidInput("TCN identity_actionが不正です")
        if row["identity_action"] == "reuse":
            _validate_id(row["reuse_id"], "tcn", f"test_conditions[{index}].reuse_id")
        elif row["reuse_id"] is not None:
            raise InvalidInput("new TCNのreuse_idはnullである必要があります")
        _unique_strings(row["tr_refs"], f"test_conditions[{index}].tr_refs")
        ensure_nonempty_string(row["condition"], f"test_conditions[{index}].condition")
        if row["category"] is not None:
            ensure_nonempty_string(row["category"], f"test_conditions[{index}].category")
        techniques = _unique_strings(row["technique_slugs"], f"test_conditions[{index}].technique_slugs")
        if any(value not in TECHNIQUE_SLUGS for value in techniques):
            raise InvalidInput("TCN technique_slugsに未知のslugがあります")
        ensure_nonempty_string(row["coverage_criterion"], f"test_conditions[{index}].coverage_criterion")
        _unique_strings(row["authority_refs"], f"test_conditions[{index}].authority_refs")
        _unique_strings(row["risk_refs"], f"test_conditions[{index}].risk_refs")
        if not isinstance(row["priority"], (str, int)) or isinstance(row["priority"], bool):
            raise InvalidInput("TCN priorityが不正です")
        if row["priority_override_reason"] is not None and not isinstance(row["priority_override_reason"], str):
            raise InvalidInput("TCN priority_override_reasonが不正です")
        result.append(canonicalize(row))
    return result


def _validate_model_drafts(rows: Any) -> list[dict[str, Any]]:
    result = []
    seen: set[str] = set()
    required = {"draft_key", "model_type", "technique_slug", "selection_source", "selection_key", "derived_from_model_draft_key", "identity_action", "reuse_model_key", "parent_tcn_draft_key"}
    for index, row in enumerate(ensure_list(rows, "models")):
        if not isinstance(row, dict):
            raise InvalidInput(f"models[{index}]が不正です")
        reject_unknown(row, required)
        draft_key = ensure_nonempty_string(row["draft_key"], f"models[{index}].draft_key")
        if draft_key in seen:
            raise InvalidInput("model draft_keyが重複しています")
        seen.add(draft_key)
        if row["model_type"] not in MODEL_TYPES:
            raise InvalidInput("model_typeが不正です")
        if row["identity_action"] not in {"reuse", "new"}:
            raise InvalidInput("model identity_actionが不正です")
        if row["identity_action"] == "reuse":
            _validate_id(row["reuse_model_key"], "model", f"models[{index}].reuse_model_key")
        elif row["reuse_model_key"] is not None:
            raise InvalidInput("new modelのreuse_model_keyはnullである必要があります")
        ensure_nonempty_string(row["parent_tcn_draft_key"], f"models[{index}].parent_tcn_draft_key")
        if row["derived_from_model_draft_key"] is not None:
            ensure_nonempty_string(row["derived_from_model_draft_key"], f"models[{index}].derived_from_model_draft_key")
        metadata = {
            "model_key": row["reuse_model_key"] or f"{row['model_type']}-000",
            "model_type": row["model_type"],
            "technique_slug": row["technique_slug"],
            "selection_source": row["selection_source"],
            "selection_key": row["selection_key"],
            "derived_from_model_key": None,
        }
        if row["identity_action"] == "reuse":
            _validate_model_metadata(metadata, f"models[{index}]")
        else:
            if row["model_type"] in ADAPTER_TYPES:
                if any(row[field] is not None for field in ("technique_slug", "selection_source", "selection_key")):
                    raise InvalidInput("adapter draft metadataが不正です")
            else:
                if row["technique_slug"] != MODEL_TECHNIQUE.get(row["model_type"]) or row["technique_slug"] not in TECHNIQUE_SLUGS:
                    raise InvalidInput("Coverage model draftのtechnique_slugが不正です")
                if row["selection_source"] not in {"analysis", "condition_design", "user"}:
                    raise InvalidInput("Coverage model draftのselection_sourceが不正です")
                if row["selection_source"] == "analysis":
                    ensure_nonempty_string(row["selection_key"], f"models[{index}].selection_key")
                elif row["selection_key"] is not None:
                    raise InvalidInput("analysis以外のselection_keyはnullである必要があります")
        result.append(canonicalize(row))
    return result


def _allocate(prefix: str, used: set[str], minimum: int, maximum: int | None = None) -> str:
    candidate = allocate_stable_id(prefix, used, minimum=minimum, maximum=maximum)
    used.add(candidate)
    return candidate


def _build(input_value: dict[str, Any], metadata: dict[str, Any]) -> dict[str, Any]:
    reject_unknown(
        input_value,
        {"test_requirements", "technique_selections", "test_conditions", "requirement_dispositions", "models", "previous_tcn_ids", "previous_model_keys", "update_scope_tcn_ids", "update_scope_model_keys"},
        {"legacy_tcn_ids"},
    )
    current_entities = validate_upstream_entities(metadata)
    tr_rows = _validate_tr_rows(input_value["test_requirements"])
    selections = _validate_selection_rows(input_value["technique_selections"])
    disposition_rows = _validate_dispositions(input_value["requirement_dispositions"], current_entities, metadata["input_mode"])
    disposed_trs = {row["upstream_entity"]["entity_ref"] for row, _deps in disposition_rows}
    tcn_drafts = _validate_tcn_drafts(input_value["test_conditions"])
    model_drafts = _validate_model_drafts(input_value["models"])
    previous_tcn = _validate_state_rows(input_value["previous_tcn_ids"], "tcn")
    previous_models = _validate_state_rows(input_value["previous_model_keys"], "model")
    update_tcn = set(_unique_strings(input_value["update_scope_tcn_ids"], "update_scope_tcn_ids"))
    update_model = set(_unique_strings(input_value["update_scope_model_keys"], "update_scope_model_keys"))
    for ref in update_tcn:
        _validate_id(ref, "tcn", "update_scope_tcn_ids")
    for ref in update_model:
        _validate_id(ref, "model", "update_scope_model_keys")
    previous_tcn_map = {row["tcn_id"]: row for row in previous_tcn}
    previous_model_map = {row["model_key"]: row for row in previous_models}
    legacy = input_value.get("legacy_tcn_ids")
    if legacy is not None:
        seeded = seed_legacy_ids(legacy, TCN_ID_RE, "legacy_tcn_ids")
        legacy_ids = [row["id"] for row in seeded]
        if metadata["input_mode"] != "direct" or previous_tcn or previous_models or update_model or update_tcn:
            raise InvalidInput("legacy_tcn_idsは初回direct昇格でのみ使用できます")
        for row in seeded:
            previous_tcn_map[row["id"]] = {"tcn_id": row["id"], "status": row["status"]}
            update_tcn.add(row["id"])
        previous_tcn = sorted(previous_tcn_map.values(), key=lambda row: row["tcn_id"])
    for ref in update_tcn:
        if ref not in previous_tcn_map or previous_tcn_map[ref]["status"] != "active":
            raise InvalidInput("update_scope_tcn_idsがactive previous stateを参照していません")
    for ref in update_model:
        if ref not in previous_model_map or previous_model_map[ref]["status"] != "active":
            raise InvalidInput("update_scope_model_keysがactive previous stateを参照していません")

    used_tcn = set(previous_tcn_map)
    tcn_mapping: dict[str, str] = {}
    reused_tcn: set[str] = set()
    for draft in sorted(tcn_drafts, key=lambda row: row["draft_key"]):
        if draft["identity_action"] == "reuse":
            ref = draft["reuse_id"]
            if ref not in update_tcn or ref in reused_tcn or previous_tcn_map.get(ref, {}).get("status") != "active":
                raise InvalidInput("TCN reuse対象がscope内activeではありません")
            reused_tcn.add(ref)
        else:
            previous_numbers = [int(match.group(1)) for value in used_tcn if (match := ID_PATTERNS["tcn"].fullmatch(value))]
            ref = _allocate("TCN", used_tcn, max(previous_numbers, default=0) + 1, 999)
        tcn_mapping[draft["draft_key"]] = ref

    model_mapping: dict[str, str] = {}
    model_metadata: dict[str, dict[str, Any]] = {}
    used_models = set(previous_model_map)
    reused_models: set[str] = set()
    for draft in sorted(model_drafts, key=lambda row: (row["parent_tcn_draft_key"], 0 if row["model_type"] in ADAPTER_TYPES else 1, row["model_type"], row["draft_key"])):
        model_type = draft["model_type"]
        parent_tcn = tcn_mapping.get(draft["parent_tcn_draft_key"])
        if parent_tcn is None:
            raise InvalidInput("model draftのparent_tcn_draft_keyが不明です")
        previous = None
        if draft["identity_action"] == "reuse":
            ref = draft["reuse_model_key"]
            if ref not in update_model or ref in reused_models or previous_model_map.get(ref, {}).get("status") != "active":
                raise InvalidInput("model reuse対象がscope内activeではありません")
            previous = previous_model_map[ref]
            if any(previous[field] != draft[field] for field in ("model_type", "technique_slug", "selection_source", "selection_key")):
                raise InvalidInput("reuse model metadataがprevious stateと不一致です")
            if previous["parent_tcn_id"] != parent_tcn:
                raise InvalidInput("reuse modelのparent TCNがprevious stateと不一致です")
            reused_models.add(ref)
        else:
            numbers = [int(match.group(2)) for value in used_models if (match := ID_PATTERNS["model"].fullmatch(value)) and match.group(1) == model_type]
            ref = _allocate(model_type, used_models, max(numbers, default=0) + 1)
        derived_from = None
        if draft["derived_from_model_draft_key"] is not None:
            parent_draft = next((row for row in model_drafts if row["draft_key"] == draft["derived_from_model_draft_key"]), None)
            if parent_draft is None or parent_draft["model_type"] not in ADAPTER_TYPES or parent_draft["parent_tcn_draft_key"] != draft["parent_tcn_draft_key"]:
                raise InvalidInput("derived_from_model_draft_keyが同一TCNのadapterを参照していません")
            if parent_draft["draft_key"] == draft["draft_key"]:
                raise InvalidInput("modelが自己参照しています")
            derived_from = model_mapping.get(parent_draft["draft_key"])
            if derived_from is None:
                raise InvalidInput("adapter modelの確定順序が不正です")
        if previous is not None and previous["derived_from_model_key"] != derived_from:
            raise InvalidInput("reuse modelのderived_from_model_keyがprevious stateと不一致です")
        metadata_row = {
            "model_key": ref,
            "model_type": model_type,
            "technique_slug": draft["technique_slug"],
            "parent_tcn_id": parent_tcn,
            "selection_source": draft["selection_source"],
            "selection_key": draft["selection_key"],
            "derived_from_model_key": derived_from,
            "status": "active",
        }
        model_mapping[draft["draft_key"]] = ref
        model_metadata[ref] = metadata_row

    violations: list[dict[str, Any]] = []
    linked_trs: set[str] = set()
    for draft in tcn_drafts:
        for tr_id in draft["tr_refs"]:
            if tr_id not in tr_rows:
                violations.append({"target_key": f"violation:unknown-tr:{tr_id}", "issue_type": "unknown_reference", "entity_ref": tr_id})
            else:
                linked_trs.add(tr_id)
    for tr_id in sorted(set(tr_rows) | linked_trs | disposed_trs):
        if tr_id in linked_trs and tr_id in disposed_trs:
            violations.append({"target_key": f"violation:linked-disposed:{tr_id}", "issue_type": "linked_and_disposed", "entity_ref": tr_id})
        elif tr_id not in linked_trs and tr_id not in disposed_trs:
            violations.append({"target_key": f"violation:unclosed-tr:{tr_id}", "issue_type": "unclosed_reference", "entity_ref": tr_id})
    tcn_draft_by_key = {row["draft_key"]: row for row in tcn_drafts}
    models_by_tcn: dict[str, set[str]] = {key: set() for key in tcn_draft_by_key}
    for draft in model_drafts:
        if draft["technique_slug"] is not None:
            models_by_tcn[draft["parent_tcn_draft_key"]].add(draft["technique_slug"])
        if draft["selection_source"] == "analysis":
            selection = selections.get(draft["selection_key"])
            if selection is None or draft["technique_slug"] not in selection["selected_techniques"]:
                violations.append({"target_key": f"violation:selection:{draft['draft_key']}", "issue_type": "selection_not_reached", "entity_ref": draft["draft_key"]})
    for draft in tcn_drafts:
        if set(draft["technique_slugs"]) != models_by_tcn[draft["draft_key"]]:
            violations.append({"target_key": f"violation:techniques:{draft['draft_key']}", "issue_type": "technique_set_mismatch", "entity_ref": draft["draft_key"]})
    for selection in selections.values():
        if selection["status"] != "active":
            continue
        reached = {row["technique_slug"] for row in model_metadata.values() if row["selection_source"] == "analysis" and row["selection_key"] == selection["selection_key"]}
        for slug in selection["selected_techniques"]:
            if slug not in reached:
                violations.append({"target_key": f"violation:selection-unreached:{selection['selection_key']}:{slug}", "issue_type": "selection_not_reached", "entity_ref": selection["selection_key"]})

    tcn_entities: dict[str, dict[str, Any]] = {}
    external_entities_by_identity = {
        (row["skill"], row["entity_type"], row["entity_ref"]): row
        for row in current_entities
    }
    for draft in tcn_drafts:
        tcn_id = tcn_mapping[draft["draft_key"]]
        content = {
            "tcn_id": tcn_id,
            "tr_refs": draft["tr_refs"],
            "condition": draft["condition"],
            "category": draft["category"],
            "technique_slugs": draft["technique_slugs"],
            "coverage_criterion": draft["coverage_criterion"],
            "authority_refs": draft["authority_refs"],
            "risk_refs": draft["risk_refs"],
            "priority": draft["priority"],
            "priority_override_reason": draft["priority_override_reason"],
            "status": "active",
        }
        dependency_identities = [
            ("test-requirement-design", "tr", ref)
            for ref in draft["tr_refs"]
            if ref in tr_rows
        ]
        dependency_identities.extend(("spec-analysis", "authority", ref) for ref in draft["authority_refs"])
        dependency_identities.extend(("test-analysis", "product_risk", ref) for ref in draft["risk_refs"])
        dependencies = resolve_entity_dependencies(
            dependency_identities,
            current_entities,
            require_all=metadata["input_mode"] == "artifact",
        )
        tcn_entities[tcn_id] = make_machine_entity(SKILL, "tcn", tcn_id, content, upstream_entity_dependencies=dependencies, runtime_dependencies=[{"skill": SKILL, "runtime_unit_key": "artifact:condition_structure:all", "generation_fingerprint": "__CURRENT__"}])
    entities = list(tcn_entities.values())
    for draft in model_drafts:
        model_key = model_mapping[draft["draft_key"]]
        row = model_metadata[model_key]
        dependency_identities = [(SKILL, "tcn", row["parent_tcn_id"])]
        if row["selection_source"] == "analysis":
            dependency_identities.append(("test-analysis", "technique_selection", row["selection_key"]))
        if row["derived_from_model_key"] is not None:
            dependency_identities.append((SKILL, "model", row["derived_from_model_key"]))
        local_entities = [*tcn_entities.values(), *(entity for entity in entities if entity["entity_type"] == "model")]
        local_identities = [identity for identity in dependency_identities if identity[0] == SKILL]
        external_identities = [identity for identity in dependency_identities if identity[0] != SKILL]
        dependencies = resolve_entity_dependencies(local_identities, local_entities, require_all=True)
        dependencies.extend(resolve_entity_dependencies(
            external_identities,
            current_entities,
            require_all=metadata["input_mode"] == "artifact",
        ))
        dependencies.sort(key=lambda item: (item["skill"], item["entity_type"], item["entity_ref"]))
        content = canonicalize(row)
        entity = make_machine_entity(SKILL, "model", model_key, content, model_key=model_key, upstream_entity_dependencies=dependencies, runtime_dependencies=[{"skill": SKILL, "runtime_unit_key": "artifact:condition_structure:all", "generation_fingerprint": "__CURRENT__"}])
        entities.append(entity)

    for row, deps in disposition_rows:
        upstream = row["upstream_entity"]
        ref = f"{upstream['entity_type']}:{upstream['entity_ref']}"
        entities.append(make_machine_entity(SKILL, "disposition", ref, row, upstream_entity_dependencies=deps, runtime_dependencies=[{"skill": SKILL, "runtime_unit_key": "artifact:condition_structure:all", "generation_fingerprint": "__CURRENT__"}]))

    tcn_state = []
    for row in previous_tcn:
        status = row["status"]
        if row["tcn_id"] in update_tcn:
            status = "active" if row["tcn_id"] in reused_tcn else "deleted"
        tcn_state.append({"tcn_id": row["tcn_id"], "status": status})
    for draft in tcn_drafts:
        tcn_state.append({"tcn_id": tcn_mapping[draft["draft_key"]], "status": "active"})
    tcn_state = _dedupe_state(tcn_state, "tcn_id")
    model_state = []
    for row in previous_models:
        status = row["status"]
        if row["model_key"] in update_model:
            status = "active" if row["model_key"] in reused_models else "deleted"
        model_state.append({**row, "status": status})
    for row in model_metadata.values():
        model_state.append({**row, "status": "active"})
    model_state = _dedupe_state(model_state, "model_key")
    model_entities = {
        entity["entity_ref"]: entity
        for entity in entities
        if entity["entity_type"] == "model"
    }
    active_model_metadata = [
        {
            "model_key": row["model_key"],
            "model_type": row["model_type"],
            "technique_slug": row["technique_slug"],
            "parent_tcn_id": row["parent_tcn_id"],
            "content_fingerprint": model_entities[row["model_key"]]["content_fingerprint"],
        }
        for row in sorted(model_metadata.values(), key=lambda item: item["model_key"])
    ]
    tcn_id_map = [{"draft_key": draft["draft_key"], "tcn_id": tcn_mapping[draft["draft_key"]], "identity_action": draft["identity_action"]} for draft in sorted(tcn_drafts, key=lambda row: row["draft_key"])]
    model_key_map = [{"draft_key": draft["draft_key"], "model_key": model_mapping[draft["draft_key"]], "model_type": draft["model_type"], "technique_slug": draft["technique_slug"], "parent_tcn_id": tcn_mapping[draft["parent_tcn_draft_key"]], "derived_from_model_key": model_metadata[model_mapping[draft["draft_key"]]]["derived_from_model_key"], "identity_action": draft["identity_action"]} for draft in sorted(model_drafts, key=lambda row: (row["parent_tcn_draft_key"], row["model_type"], row["draft_key"]))]
    expected_sources = [("tcn", tcn_mapping[draft["draft_key"]]) for draft in tcn_drafts]
    expected_sources.extend(("model", model_mapping[draft["draft_key"]]) for draft in model_drafts)
    expected_sources.extend(("disposition", f"{row['upstream_entity']['entity_type']}:{row['upstream_entity']['entity_ref']}") for row in ensure_list(input_value["requirement_dispositions"], "requirement_dispositions"))
    violations = sorted(violations, key=lambda row: row["target_key"])
    issues = [{"issue_type": row["issue_type"], "blocking": True, "target_key": row["target_key"], "authority_refs": []} for row in violations]
    return {
        "runtime_status": "ok",
        "result_status": "ready" if not violations else "unresolved",
        "support_status": "supported",
        "deterministic_generated": True,
        "payload": {
            "tcn_id_map": tcn_id_map,
            "model_key_map": model_key_map,
            "tcn_id_state": sorted(tcn_state, key=lambda row: row["tcn_id"]),
            "model_key_state": sorted(model_state, key=lambda row: row["model_key"]),
            "active_model_metadata": active_model_metadata,
            "violations": violations,
            "expected_entity_identities": [{"skill": SKILL, "entity_type": entity_type, "entity_ref": entity_ref} for entity_type, entity_ref in sorted(expected_sources)],
            "derived_values": {"entities": sorted(entities, key=lambda row: (row["entity_type"], row["entity_ref"]))},
            "entities": sorted(entities, key=lambda row: (row["entity_type"], row["entity_ref"])),
        },
        "issues": issues,
    }


def _dedupe_state(rows: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        previous = result.get(row[key])
        if previous is not None and previous != row:
            raise InvalidInput(f"{key} stateが重複しています")
        result[row[key]] = row
    return list(result.values())


def handler(input_value: dict[str, Any], metadata: dict[str, Any]) -> dict[str, Any]:
    if metadata["model_key"] is not None or metadata["runtime_unit_key"] != "artifact:condition_structure:all" or metadata["scope_key"] != "all":
        raise InvalidInput("condition_structureのruntime metadataが不正です")
    return _build(input_value, metadata)


if __name__ == "__main__":
    raise SystemExit(
        run_cli(
            handler,
            skill=SKILL,
            generator=GENERATOR,
            generator_contract_version=GENERATOR_CONTRACT_VERSION,
            generator_path=SCRIPT_PATH,
        )
    )
