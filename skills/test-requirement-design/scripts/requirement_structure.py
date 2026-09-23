"""Deterministic TR structure validation and stable ID materialization."""

from __future__ import annotations

from pathlib import Path
import re
import sys

from runtime_contract import InvalidInput, TR_ID_RE, canonicalize, ensure_list, ensure_nonempty_string, make_machine_entity, normalize_machine_entity_disposition, reject_unknown, resolve_entity_dependencies, run_cli, seed_legacy_ids, validate_upstream_entities


SKILL = "test-requirement-design"
GENERATOR = "requirement_structure"
GENERATOR_CONTRACT_VERSION = "requirement-structure-v1"
SCRIPT_PATH = Path(__file__).resolve()
TR_RE = re.compile(r"^TR-(\d{3})$")
PRIORITY_ORDER = {"低": 1, "中": 2, "高": 3}


def _id(value: object, name: str) -> str:
    if not isinstance(value, str) or TR_RE.fullmatch(value) is None:
        raise InvalidInput(f"{name}の形式が不正です")
    return value


def _state(rows: object) -> list[dict]:
    result = []
    seen = set()
    for index, row in enumerate(ensure_list(rows, "previous_tr_ids")):
        if not isinstance(row, dict) or set(row) != {"tr_id", "status"}:
            raise InvalidInput(f"previous_tr_ids[{index}]が不正です")
        ref = _id(row["tr_id"], f"previous_tr_ids[{index}].tr_id")
        if ref in seen or row["status"] not in {"active", "deleted"}:
            raise InvalidInput("previous_tr_idsが重複または不正です")
        seen.add(ref)
        result.append({"tr_id": ref, "status": row["status"]})
    return result


def _disposition_refs(rows: object, current_entities: list[dict], input_mode: str) -> tuple[set[tuple[str, str]], list[tuple[dict, list[dict[str, str]]]]]:
    result = set()
    normalized_rows = []
    for index, row in enumerate(ensure_list(rows, "dispositions")):
        normalized, dependencies = normalize_machine_entity_disposition(
            row,
            current_entities,
            allowed_handlings={"対象外", "別テストレベル", "残存リスク", "ブロック中", "重複"},
            allowed_upstream_entity_types={"authority", "product_risk"},
            input_mode=input_mode,
        )
        upstream = normalized["upstream_entity"]
        expected_skill = {"authority": "spec-analysis", "product_risk": "test-analysis"}[upstream["entity_type"]]
        if upstream["skill"] != expected_skill:
            raise InvalidInput("TR disposition upstream_entity skill/typeが不一致です")
        ref = ensure_nonempty_string(upstream["entity_ref"], "disposition.entity_ref")
        key = (upstream["entity_type"], ref)
        if key in result:
            raise InvalidInput("dispositionが重複しています")
        result.add(key)
        normalized_rows.append((normalized, dependencies))
    return result, normalized_rows


def generate(input_value: dict, metadata: dict) -> dict:
    if metadata["runtime_unit_key"] != "artifact:requirement_structure:all":
        raise InvalidInput("requirement_structure runtime unitが不正です")
    required = {"authorities", "risks", "test_requirements", "dispositions", "previous_tr_ids", "update_scope_tr_ids"}
    reject_unknown(input_value, required, {"legacy_tr_ids"})
    authority_ids = set()
    for row in ensure_list(input_value["authorities"], "authorities"):
        if not isinstance(row, dict) or set(row) != {"authority_id"}:
            raise InvalidInput("authorities schemaが不正です")
        ref = ensure_nonempty_string(row["authority_id"], "authority_id")
        if ref in authority_ids:
            raise InvalidInput("authority_idが重複しています")
        authority_ids.add(ref)
    risk_priorities = {}
    for row in ensure_list(input_value["risks"], "risks"):
        if not isinstance(row, dict) or set(row) != {"risk_id", "mapped_priority"} or row["mapped_priority"] not in PRIORITY_ORDER:
            raise InvalidInput("risks schemaが不正です")
        if row["risk_id"] in risk_priorities:
            raise InvalidInput("risk_idが重複しています")
        risk_priorities[row["risk_id"]] = row["mapped_priority"]
    current_entities = validate_upstream_entities(metadata)
    dispositions, disposition_rows = _disposition_refs(input_value["dispositions"], current_entities, metadata["input_mode"])
    previous = _state(input_value["previous_tr_ids"])
    previous_map = {row["tr_id"]: row for row in previous}
    update_scope = input_value["update_scope_tr_ids"]
    if not isinstance(update_scope, list) or len(set(update_scope)) != len(update_scope):
        raise InvalidInput("update_scope_tr_idsが不正です")
    update_scope_set = {_id(value, "update_scope_tr_ids") for value in update_scope}
    legacy = input_value.get("legacy_tr_ids")
    if legacy is not None:
        if metadata["input_mode"] != "direct" or previous or update_scope_set:
            raise InvalidInput("legacy_tr_idsは初回direct昇格でのみ使用できます")
        seeded = seed_legacy_ids(legacy, TR_ID_RE, "legacy_tr_ids")
        for value in seeded:
            previous_map[value["id"]] = {"tr_id": value["id"], "status": value["status"]}
            update_scope_set.add(value["id"])
        previous = sorted(previous_map.values(), key=lambda row: row["tr_id"])
    for ref in update_scope_set:
        if previous_map.get(ref, {}).get("status") != "active":
            raise InvalidInput("update_scope_tr_idsがactive previous stateを参照していません")
    drafts = []
    seen_drafts = set()
    for index, row in enumerate(ensure_list(input_value["test_requirements"], "test_requirements")):
        if not isinstance(row, dict):
            raise InvalidInput("TR draftが不正です")
        fields = {"draft_key", "identity_action", "reuse_id", "text", "authority_refs", "risk_refs", "priority", "priority_override_reason", "test_level", "observation_method"}
        reject_unknown(row, fields)
        key = ensure_nonempty_string(row["draft_key"], f"test_requirements[{index}].draft_key")
        if key in seen_drafts or row["identity_action"] not in {"reuse", "new"}:
            raise InvalidInput("TR draft identityが不正です")
        seen_drafts.add(key)
        if row["identity_action"] == "reuse":
            _id(row["reuse_id"], "TR reuse_id")
        elif row["reuse_id"] is not None:
            raise InvalidInput("new TRのreuse_idはnullである必要があります")
        ensure_nonempty_string(row["text"], "TR text")
        for field in ("authority_refs", "risk_refs"):
            if not isinstance(row[field], list) or len(set(row[field])) != len(row[field]) or not all(isinstance(value, str) and value for value in row[field]):
                raise InvalidInput(f"TR {field}が不正です")
        if row["priority"] not in PRIORITY_ORDER or (row["priority_override_reason"] is not None and (not isinstance(row["priority_override_reason"], str) or not row["priority_override_reason"])):
            raise InvalidInput("TR priorityが不正です")
        drafts.append(canonicalize(row))
    used = set(previous_map)
    mapping = {}
    reused = set()
    violations = []
    for draft in sorted(drafts, key=lambda row: row["draft_key"]):
        if draft["identity_action"] == "reuse":
            ref = draft["reuse_id"]
            if ref not in update_scope_set or ref in reused:
                raise InvalidInput("TR reuse対象がscope内activeではありません")
            reused.add(ref)
        else:
            numbers = [int(match.group(1)) for value in used if (match := TR_RE.fullmatch(value))]
            number = max(numbers, default=0) + 1
            if number > 999:
                raise InvalidInput("id_space_exhausted")
            ref = f"TR-{number:03d}"
            used.add(ref)
        mapping[draft["draft_key"]] = ref
        unknown_authorities = sorted(set(draft["authority_refs"]) - authority_ids)
        unknown_risks = sorted(set(draft["risk_refs"]) - set(risk_priorities))
        if unknown_authorities or unknown_risks:
            violations.append({"target_key": f"violation:unknown:{draft['draft_key']}", "issue_type": "unknown_reference", "entity_ref": draft["draft_key"], "unknown_authorities": unknown_authorities, "unknown_risks": unknown_risks})
        minimum = max((PRIORITY_ORDER[risk_priorities[risk]] for risk in draft["risk_refs"] if risk in risk_priorities), default=0)
        if minimum and PRIORITY_ORDER[draft["priority"]] < minimum and not draft["priority_override_reason"]:
            violations.append({"target_key": f"violation:priority:{draft['draft_key']}", "issue_type": "priority_override_reason_required", "entity_ref": draft["draft_key"]})
    linked = {(kind, ref) for draft in drafts for kind, refs in (("authority", draft["authority_refs"]), ("product_risk", draft["risk_refs"])) for ref in refs}
    expected = {("authority", ref) for ref in authority_ids} | {("product_risk", ref) for ref in risk_priorities}
    for key in sorted(expected):
        if key in linked and key in dispositions:
            violations.append({"target_key": f"violation:linked-disposed:{key[0]}:{key[1]}", "issue_type": "linked_and_disposed", "entity_ref": key[1]})
        elif key not in linked and key not in dispositions:
            violations.append({"target_key": f"violation:unclosed:{key[0]}:{key[1]}", "issue_type": "unclosed_reference", "entity_ref": key[1]})
    entities = []
    for draft in drafts:
        tr_id = mapping[draft["draft_key"]]
        content = {key: draft[key] for key in ("text", "authority_refs", "risk_refs", "priority", "priority_override_reason", "test_level", "observation_method")}
        ref_identities = [
            ("spec-analysis", "authority", ref)
            for ref in draft["authority_refs"]
            if ref in authority_ids
        ]
        ref_identities.extend(
            ("test-analysis", "product_risk", ref)
            for ref in draft["risk_refs"]
            if ref in risk_priorities
        )
        deps = resolve_entity_dependencies(ref_identities, current_entities, require_all=metadata["input_mode"] == "artifact")
        entities.append(make_machine_entity(SKILL, "tr", tr_id, {"tr_id": tr_id, **content}, upstream_entity_dependencies=deps, runtime_dependencies=[{"skill": SKILL, "runtime_unit_key": "artifact:requirement_structure:all", "generation_fingerprint": "__CURRENT__"}]))
    for row, deps in disposition_rows:
        upstream_ref = row["upstream_entity"]
        ref = f"{upstream_ref['entity_type']}:{upstream_ref['entity_ref']}"
        entities.append(make_machine_entity(SKILL, "disposition", ref, row, upstream_entity_dependencies=deps, runtime_dependencies=[{"skill": SKILL, "runtime_unit_key": "artifact:requirement_structure:all", "generation_fingerprint": "__CURRENT__"}]))
    states = []
    for row in previous:
        status = row["status"]
        if row["tr_id"] in update_scope_set:
            status = "active" if row["tr_id"] in reused else "deleted"
        states.append({"tr_id": row["tr_id"], "status": status})
    states.extend({"tr_id": ref, "status": "active"} for ref in mapping.values())
    state_map = {row["tr_id"]: row for row in states}
    violations.sort(key=lambda row: row["target_key"])
    return {"runtime_status": "ok", "support_status": "supported", "result_status": "ready" if not violations else "unresolved", "runtime_required": True, "deterministic_generated": True, "payload": {"tr_id_map": [{"draft_key": draft["draft_key"], "tr_id": mapping[draft["draft_key"]], "identity_action": draft["identity_action"]} for draft in sorted(drafts, key=lambda row: row["draft_key"])], "tr_id_state": [state_map[key] for key in sorted(state_map)], "violations": violations, "entities": sorted(entities, key=lambda row: row["entity_ref"])}, "issues": [{"issue_type": row["issue_type"], "blocking": True, "target_key": row["target_key"], "authority_refs": []} for row in violations]}


if __name__ == "__main__":
    raise SystemExit(run_cli(generate, skill=SKILL, generator=GENERATOR, generator_contract_version=GENERATOR_CONTRACT_VERSION, generator_path=SCRIPT_PATH))
