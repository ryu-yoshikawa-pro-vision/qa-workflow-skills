"""Build stable test-case IDs from current CI Machine Entities and semantic drafts."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from runtime_contract import (
    CI_ID_RE,
    TC_ID_RE,
    InvalidInput,
    UnsupportedInput,
    allocate_stable_id,
    canonicalize,
    constraint_intersection_compatible,
    ensure_list,
    ensure_nonempty_string,
    make_machine_entity,
    normalize_machine_entity_disposition,
    reject_unknown,
    resolve_entity_dependencies,
    run_cli,
    seed_legacy_ids,
    validate_machine_entity,
    validate_upstream_entities,
)


SKILL = "test-case-design"
GENERATOR = "case_structure"
GENERATOR_CONTRACT_VERSION = "case-structure-v1"
SCRIPT_PATH = Path(__file__).resolve()
TC_RE = re.compile(r"^TC-(\d{3})$")
HANDLINGS = {"対象外", "別テストレベル", "残存リスク", "ブロック中", "重複"}
PRIORITY_ORDER = {"低": 1, "中": 2, "高": 3}


def _tc_id(value: Any, name: str = "tc_id") -> str:
    if not isinstance(value, str) or TC_RE.fullmatch(value) is None:
        raise InvalidInput(f"{name}の形式が不正です")
    return value


def _refs(value: Any, name: str) -> list[str]:
    if not isinstance(value, list) or len(set(value)) != len(value) or not all(isinstance(item, str) and item for item in value):
        raise InvalidInput(f"{name}が不正です")
    return sorted(value)


def _normalize_current_rows(rows: Any, *, kind: str) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for index, row in enumerate(ensure_list(rows, kind)):
        if isinstance(row, dict) and row.get("schema_version") == "entity-state-v1":
            entity = validate_machine_entity(row)
            if entity["entity_type"] != kind:
                raise InvalidInput(f"{kind} Machine Entity typeが不一致です")
            expected_skill = {"ci": "test-condition-design", "environment_requirement": "test-analysis", "test_data_requirement": "test-condition-design"}[kind]
            if entity["skill"] != expected_skill:
                raise InvalidInput(f"{kind} Machine Entity skillが不一致です")
            if entity["entity_ref"] in result:
                raise InvalidInput(f"{kind} identityが重複しています")
            result[entity["entity_ref"]] = entity
            continue
        if not isinstance(row, dict):
            raise InvalidInput(f"{kind}[{index}]が不正です")
        ref_key = {"ci": "ci_id", "environment_requirement": "requirement_key", "test_data_requirement": "data_ref"}[kind]
        ref = ensure_nonempty_string(row.get(ref_key), f"{kind}.{ref_key}")
        if ref in result:
            raise InvalidInput(f"{kind} identityが重複しています")
        content = {key: value for key, value in row.items() if key != ref_key}
        if kind == "environment_requirement":
            content.setdefault("requirement_key", ref)
            content.setdefault("environment_key", ref)
        if kind == "ci":
            content.setdefault("ci_id", ref)
        if kind == "test_data_requirement":
            content.setdefault("data_ref", ref)
        owner_skill = {"ci": "test-condition-design", "environment_requirement": "test-analysis", "test_data_requirement": "test-condition-design"}[kind]
        result[ref] = make_machine_entity(owner_skill, kind, ref, content)
    return result


def _validate_ci_entities(ci_map: dict[str, dict[str, Any]]) -> None:
    required = {"tcn_id", "model_key", "priority", "authority_refs", "source_kind", "execution", "semantic_item_key", "semantic_item_text", "semantic_source_targets", "test_data_requirement_refs"}
    for ci_id, entity in ci_map.items():
        content = entity["content"]
        if not required.issubset(content):
            raise InvalidInput(f"CI {ci_id}のcanonical contentが不足しています")
        if not isinstance(content["tcn_id"], str) or not isinstance(content["model_key"], str) or content["priority"] not in PRIORITY_ORDER:
            raise InvalidInput(f"CI {ci_id}のidentity/priorityが不正です")
        if not isinstance(content["authority_refs"], list) or len(set(content["authority_refs"])) != len(content["authority_refs"]):
            raise InvalidInput(f"CI {ci_id}のauthority_refsが不正です")
        if not isinstance(content["test_data_requirement_refs"], list) or len(set(content["test_data_requirement_refs"])) != len(content["test_data_requirement_refs"]):
            raise InvalidInput(f"CI {ci_id}のtest_data_requirement_refsが不正です")
        if content["source_kind"] == "runtime_target":
            if not isinstance(content["execution"], dict) or content["semantic_item_key"] is not None or content["semantic_item_text"] is not None or content["semantic_source_targets"] != []:
                raise InvalidInput(f"runtime target CI {ci_id}のcanonical contentが不正です")
        elif content["source_kind"] == "semantic_item":
            if content["execution"] is not None or not isinstance(content["semantic_item_key"], str) or not isinstance(content["semantic_item_text"], str) or not content["semantic_item_text"].strip() or not isinstance(content["semantic_source_targets"], list):
                raise InvalidInput(f"semantic CI {ci_id}のcanonical contentが不正です")
        else:
            raise InvalidInput(f"CI {ci_id}のsource_kindが不正です")


def _normalize_tcn(rows: Any) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for index, row in enumerate(ensure_list(rows, "test_conditions")):
        if not isinstance(row, dict):
            raise InvalidInput(f"test_conditions[{index}]が不正です")
        reject_unknown(row, {"tcn_id", "tr_refs", "priority"})
        tcn_id = row["tcn_id"]
        if not isinstance(tcn_id, str) or not re.fullmatch(r"TCN-\d{3}", tcn_id) or tcn_id in result:
            raise InvalidInput("TCN identityが不正または重複しています")
        result[tcn_id] = canonicalize({"tcn_id": tcn_id, "tr_refs": _refs(row["tr_refs"], "TCN tr_refs"), "priority": row["priority"]})
    return result


def _normalize_steps(value: Any, name: str, *, expected: bool = False) -> list[dict[str, Any]]:
    rows = ensure_list(value, name)
    result: list[dict[str, Any]] = []
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            raise InvalidInput(f"{name}[{index}]が不正です")
        if expected:
            reject_unknown(row, {"number", "text", "authority_refs"})
            refs = _refs(row["authority_refs"], "expected result authority_refs")
        else:
            reject_unknown(row, {"number", "text"})
            refs = None
        if row["number"] != index or not isinstance(row["text"], str) or not row["text"].strip():
            raise InvalidInput(f"{name}のnumber/textが不正です")
        normalized = {"number": index, "text": row["text"]}
        if refs is not None:
            normalized["authority_refs"] = refs
        result.append(normalized)
    return result


def _normalize_draft(row: Any, ci_map: dict[str, dict[str, Any]], tcn_map: dict[str, dict[str, Any]], env_map: dict[str, dict[str, Any]], data_map: dict[str, dict[str, Any]]) -> dict[str, Any]:
    if not isinstance(row, dict):
        raise InvalidInput("test case draftが不正です")
    required = {"draft_key", "identity_action", "reuse_id", "title_or_purpose", "tr_refs", "tcn_refs", "ci_refs", "environment_requirement_refs", "test_data_requirement_refs", "priority", "priority_override_reason", "preconditions", "test_data", "steps", "expected_results", "postconditions_or_cleanup"}
    reject_unknown(row, required)
    draft_key = ensure_nonempty_string(row["draft_key"], "draft_key")
    action = row["identity_action"]
    if action not in {"new", "reuse"}:
        raise InvalidInput("test case identity_actionが不正です")
    if action == "new" and row["reuse_id"] is not None:
        raise InvalidInput("new test caseのreuse_idはnullである必要があります")
    if action == "reuse":
        _tc_id(row["reuse_id"], "reuse_id")
    ci_refs = _refs(row["ci_refs"], "ci_refs")
    if not ci_refs:
        raise InvalidInput("test caseはCIを1件以上参照する必要があります")
    if any(ref not in ci_map for ref in ci_refs):
        raise InvalidInput("test caseがunknown CIを参照しています")
    tcn_refs = _refs(row["tcn_refs"], "tcn_refs")
    if not tcn_refs or any(ref not in tcn_map for ref in tcn_refs):
        raise InvalidInput("test caseのTCN参照が不正です")
    ci_tcn_refs = {ci_map[ref]["content"].get("tcn_id") for ref in ci_refs}
    if ci_tcn_refs != set(tcn_refs):
        raise InvalidInput("CIの親TCNとtcn_refsが一致しません")
    tr_refs = _refs(row["tr_refs"], "test case tr_refs")
    expected_tr_refs = sorted({tr for tcn in tcn_refs for tr in tcn_map[tcn]["tr_refs"]})
    if tr_refs != expected_tr_refs:
        raise InvalidInput("test case tr_refsが参照TCNのunionと一致しません")
    env_refs = _refs(row["environment_requirement_refs"], "environment_requirement_refs")
    data_refs = _refs(row["test_data_requirement_refs"], "test_data_requirement_refs")
    if any(ref not in env_map for ref in env_refs) or any(ref not in data_map for ref in data_refs):
        raise InvalidInput("test case requirement referenceが不正です")
    if row["priority"] not in PRIORITY_ORDER:
        raise InvalidInput("test case priorityが不正です")
    override = row["priority_override_reason"]
    if override is not None and (not isinstance(override, str) or not override.strip()):
        raise InvalidInput("priority_override_reasonが不正です")
    return canonicalize({
        "draft_key": draft_key, "identity_action": action, "reuse_id": row["reuse_id"], "title_or_purpose": ensure_nonempty_string(row["title_or_purpose"], "title_or_purpose"),
        "tr_refs": tr_refs, "tcn_refs": tcn_refs, "ci_refs": ci_refs, "environment_requirement_refs": env_refs, "test_data_requirement_refs": data_refs,
        "priority": row["priority"], "priority_override_reason": override, "preconditions": ensure_list(row["preconditions"], "preconditions"), "test_data": ensure_list(row["test_data"], "test_data"),
        "steps": _normalize_steps(row["steps"], "steps"), "expected_results": _normalize_steps(row["expected_results"], "expected_results", expected=True), "postconditions_or_cleanup": ensure_list(row["postconditions_or_cleanup"], "postconditions_or_cleanup"),
    })


def _validate_dispositions(rows: Any, current_entities: list[dict[str, Any]], input_mode: str) -> list[tuple[dict[str, Any], list[dict[str, str]]]]:
    result: list[tuple[dict[str, Any], list[dict[str, str]]]] = []
    seen: set[tuple[str, str, str]] = set()
    for index, row in enumerate(ensure_list(rows, "dispositions")):
        normalized, dependencies = normalize_machine_entity_disposition(
            row,
            current_entities,
            allowed_handlings=HANDLINGS,
            allowed_upstream_entity_types={"tcn", "ci", "environment_requirement", "test_data_requirement"},
            input_mode=input_mode,
        )
        upstream = normalized["upstream_entity"]
        key = (upstream["skill"], upstream["entity_type"], upstream["entity_ref"])
        if key in seen:
            raise InvalidInput("disposition upstream entityが重複しています")
        expected_skills = {"tcn": "test-condition-design", "ci": "test-condition-design", "environment_requirement": "test-analysis", "test_data_requirement": "test-condition-design"}
        if upstream["skill"] != expected_skills[upstream["entity_type"]]:
            raise InvalidInput("disposition upstream_entity skill/typeが不一致です")
        seen.add(key)
        result.append((normalized, dependencies))
    return result


def _current_machine_entities(metadata: dict[str, Any], input_value: dict[str, Any]) -> list[dict[str, Any]]:
    current = {
        (row["skill"], row["entity_type"], row["entity_ref"]): row
        for row in validate_upstream_entities(metadata)
    }
    for field in ("coverage_items", "environment_requirements", "test_data_requirements"):
        for row in ensure_list(input_value[field], field):
            if not isinstance(row, dict) or row.get("schema_version") != "entity-state-v1":
                continue
            entity = validate_machine_entity(row)
            identity = (entity["skill"], entity["entity_type"], entity["entity_ref"])
            previous = current.get(identity)
            if previous is not None and previous["content_fingerprint"] != entity["content_fingerprint"]:
                raise InvalidInput("同一current Machine Entityがmetadataとinputで不一致です")
            current[identity] = entity
    return [current[key] for key in sorted(current)]


def _collect_requirement_violations(draft: dict[str, Any], ci_map: dict[str, dict[str, Any]], env_map: dict[str, dict[str, Any]], data_map: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    violations: list[dict[str, Any]] = []
    data_refs = set(draft["test_data_requirement_refs"])
    data_refs.update(ref for ci_ref in draft["ci_refs"] for ref in ci_map[ci_ref]["content"].get("test_data_requirement_refs", []))
    requirements = [data_map[ref]["content"] for ref in sorted(data_refs)]
    data_by_dimension: dict[str, list[dict[str, Any]]] = {}
    for requirement in requirements:
        data_by_dimension.setdefault(requirement["dimension_key"], []).append(requirement)
    for dimension, group in sorted(data_by_dimension.items()):
        keys = sorted(row.get("requirement_key", row.get("data_ref")) for row in group)
        try:
            if not constraint_intersection_compatible(group):
                violations.append({"violation_type": "test_data_conflict", "draft_key": draft["draft_key"], "dimension_key": dimension, "requirement_keys": keys, "blocking": True})
        except UnsupportedInput:
            violations.append({"violation_type": "test_data_intersection_unsupported", "draft_key": draft["draft_key"], "dimension_key": dimension, "requirement_keys": keys, "blocking": True})
    selected_env_refs = set(draft["environment_requirement_refs"])
    selected_by_key: dict[str, set[str]] = {}
    for ref in selected_env_refs:
        content = env_map[ref]["content"]
        selected_by_key.setdefault(content.get("environment_key", ref), set()).add(ref)
    for environment_key, refs in selected_by_key.items():
        required = {ref for ref, entity in env_map.items() if entity["content"].get("environment_key", ref) == environment_key}
        if refs != required:
            violations.append({"violation_type": "environment_requirement_incomplete", "draft_key": draft["draft_key"], "environment_key": environment_key, "missing_refs": sorted(required - refs), "blocking": True})
            continue
        env_by_dimension: dict[str, list[dict[str, Any]]] = {}
        for ref in sorted(refs):
            content = env_map[ref]["content"]
            env_by_dimension.setdefault(content["dimension_key"], []).append(content)
        for dimension, group in sorted(env_by_dimension.items()):
            keys = sorted(row["requirement_key"] for row in group)
            try:
                if not constraint_intersection_compatible(group):
                    violations.append({"violation_type": "environment_requirement_conflict", "draft_key": draft["draft_key"], "environment_key": environment_key, "dimension_key": dimension, "requirement_keys": keys, "blocking": True})
            except UnsupportedInput:
                violations.append({"violation_type": "environment_requirement_unsupported", "draft_key": draft["draft_key"], "environment_key": environment_key, "dimension_key": dimension, "requirement_keys": keys, "blocking": True})
    return violations


def generate(input_value: dict, metadata: dict) -> dict:
    if metadata["model_key"] is not None or metadata["runtime_unit_key"] != "artifact:case_structure:all" or metadata["scope_key"] is not None:
        raise InvalidInput("case_structureのruntime metadataが不正です")
    required = {"test_conditions", "coverage_items", "environment_requirements", "test_data_requirements", "test_cases", "dispositions", "previous_tc_ids", "update_scope_tc_ids"}
    reject_unknown(input_value, required, {"legacy_tc_ids"})
    current_entities = _current_machine_entities(metadata, input_value)
    tcn_map = _normalize_tcn(input_value["test_conditions"])
    ci_map = _normalize_current_rows(input_value["coverage_items"], kind="ci")
    _validate_ci_entities(ci_map)
    env_map = _normalize_current_rows(input_value["environment_requirements"], kind="environment_requirement")
    data_map = _normalize_current_rows(input_value["test_data_requirements"], kind="test_data_requirement")
    previous_raw = ensure_list(input_value["previous_tc_ids"], "previous_tc_ids")
    previous: dict[str, str] = {}
    previous_status: dict[str, str] = {}
    for row in previous_raw:
        if not isinstance(row, dict) or set(row) != {"tc_id", "status"} or row["status"] not in {"active", "deleted"}:
            raise InvalidInput("previous_tc_idsが不正です")
        tc_id = _tc_id(row["tc_id"])
        if tc_id in previous_status:
            raise InvalidInput("previous_tc_idsが重複しています")
        previous_status[tc_id] = row["status"]
    legacy_ids = input_value.get("legacy_tc_ids")
    if legacy_ids is not None:
        if metadata["input_mode"] != "direct" or previous_status:
            raise InvalidInput("legacy_tc_idsはdirectかつ空previousでのみ使用できます")
        seeded = seed_legacy_ids(legacy_ids, TC_ID_RE, "legacy_tc_ids")
        previous_status = {row["id"]: row["status"] for row in seeded}
    update_scope = _refs(input_value["update_scope_tc_ids"], "update_scope_tc_ids")
    if any(tc_id not in previous_status or previous_status[tc_id] != "active" for tc_id in update_scope):
        raise InvalidInput("update_scope_tc_idsはprevious active TCだけを列挙する必要があります")
    drafts: list[dict[str, Any]] = []
    seen_drafts: set[str] = set()
    for row in ensure_list(input_value["test_cases"], "test_cases"):
        draft = _normalize_draft(row, ci_map, tcn_map, env_map, data_map)
        if draft["draft_key"] in seen_drafts:
            raise InvalidInput("draft_keyが重複しています")
        seen_drafts.add(draft["draft_key"])
        drafts.append(draft)
    drafts.sort(key=lambda row: row["draft_key"])
    reused: set[str] = set()
    tc_id_map: list[dict[str, Any]] = []
    assignments: dict[str, str] = {}
    used_ids = set(previous_status)
    for draft in drafts:
        if draft["identity_action"] == "reuse":
            tc_id = draft["reuse_id"]
            if tc_id not in update_scope or tc_id in reused or previous_status.get(tc_id) != "active":
                raise InvalidInput("test case reuse_idがscope / active stateと不一致です")
            reused.add(tc_id)
        else:
            tc_id = allocate_stable_id("TC", used_ids, minimum=1, maximum=999, width=3)
            used_ids.add(tc_id)
        assignments[draft["draft_key"]] = tc_id
        tc_id_map.append({"draft_key": draft["draft_key"], "tc_id": tc_id, "identity_action": draft["identity_action"]})
    tc_state = dict(previous_status)
    for tc_id in update_scope:
        if tc_id not in reused:
            tc_state[tc_id] = "deleted"
    for tc_id in assignments.values():
        tc_state[tc_id] = "active"
    violations: list[dict[str, Any]] = []
    for draft in drafts:
        referenced_priorities = [ci_map[ref]["content"].get("priority") for ref in draft["ci_refs"] if ci_map[ref]["content"].get("priority") in PRIORITY_ORDER]
        if referenced_priorities and PRIORITY_ORDER[draft["priority"]] < max(PRIORITY_ORDER[value] for value in referenced_priorities) and not draft["priority_override_reason"]:
            violations.append({"violation_type": "priority_override_reason_missing", "draft_key": draft["draft_key"], "blocking": True})
        violations.extend(_collect_requirement_violations(draft, ci_map, env_map, data_map))
    entities: list[dict[str, Any]] = []
    for draft in drafts:
        tc_id = assignments[draft["draft_key"]]
        dependency_identities = [("test-requirement-design", "tr", ref) for ref in draft["tr_refs"]]
        dependency_identities.extend(("test-condition-design", "tcn", ref) for ref in draft["tcn_refs"])
        dependency_identities.extend((ci_map[ref]["skill"], "ci", ci_map[ref]["entity_ref"]) for ref in draft["ci_refs"])
        dependency_identities.extend(("test-analysis", "environment_requirement", ref) for ref in draft["environment_requirement_refs"])
        dependency_identities.extend(("test-condition-design", "test_data_requirement", ref) for ref in draft["test_data_requirement_refs"])
        authority_refs = sorted({ref for result in draft["expected_results"] for ref in result["authority_refs"]})
        dependency_identities.extend(("spec-analysis", "authority", ref) for ref in authority_refs)
        upstream = resolve_entity_dependencies(
            dependency_identities,
            current_entities,
            require_all=metadata["input_mode"] == "artifact",
        )
        content = {**draft, "tc_id": tc_id, "status": "active"}
        entities.append(make_machine_entity(SKILL, "tc", tc_id, content, upstream_entity_dependencies=upstream, runtime_dependencies=[{"skill": SKILL, "runtime_unit_key": "artifact:case_structure:all", "generation_fingerprint": "__CURRENT__"}]))
    disposition_rows = _validate_dispositions(input_value["dispositions"], current_entities, metadata["input_mode"])
    for disposition, dependencies in disposition_rows:
        upstream = disposition["upstream_entity"]
        entities.append(make_machine_entity(
            SKILL,
            "disposition",
            f"{upstream['entity_type']}:{upstream['entity_ref']}",
            disposition,
            upstream_entity_dependencies=dependencies,
            runtime_dependencies=[{"skill": SKILL, "runtime_unit_key": "artifact:case_structure:all", "generation_fingerprint": "__CURRENT__"}],
        ))
    return {
        "runtime_status": "ok", "support_status": "supported", "result_status": "ready" if not violations else "unresolved", "runtime_required": True, "deterministic_generated": True,
        "payload": {"test_conditions": list(tcn_map.values()), "coverage_items": list(ci_map.values()), "environment_requirements": list(env_map.values()), "test_data_requirements": list(data_map.values()), "test_cases": [{**draft, "tc_id": assignments[draft["draft_key"]]} for draft in drafts], "dispositions": [row for row, _deps in disposition_rows], "tc_id_map": tc_id_map, "tc_id_state": [{"tc_id": tc_id, "status": status} for tc_id, status in sorted(tc_state.items())], "violations": violations, "entities": sorted(entities, key=lambda row: (row["entity_type"], row["entity_ref"])), "expected_entity_identities": [{"skill": row["skill"], "entity_type": row["entity_type"], "entity_ref": row["entity_ref"]} for row in sorted(entities, key=lambda row: (row["entity_type"], row["entity_ref"]))]},
        "issues": violations,
    }


if __name__ == "__main__":
    raise SystemExit(run_cli(generate, skill=SKILL, generator=GENERATOR, generator_contract_version=GENERATOR_CONTRACT_VERSION, generator_path=SCRIPT_PATH))
