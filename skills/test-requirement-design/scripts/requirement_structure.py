"""Deterministic TR structure validation and stable ID materialization."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from runtime_contract import (
    TR_ID_RE,
    InvalidInput,
    canonicalize,
    ensure_list,
    ensure_nonempty_string,
    machine_entity_runtime_dependency,
    make_machine_entity,
    normalize_machine_entity_disposition,
    reject_unknown,
    resolve_entity_dependencies,
    run_cli,
    seed_legacy_ids,
    validate_machine_entity,
    validate_upstream_entities,
)

SKILL = "test-requirement-design"
GENERATOR = "requirement_structure"
GENERATOR_CONTRACT_VERSION = "requirement-structure-v2"
SCRIPT_PATH = Path(__file__).resolve()
TR_RE = re.compile(r"^TR-(\d{3})$")
AC_RE = re.compile(r"^AC-(?:[A-Z0-9]+-)*\d{3,}$")
SCOPE_RE = re.compile(r"^SCOPE-\d{3,}$")
PRIORITY_ORDER = {"低": 1, "中": 2, "高": 3}


def _id(value: object, name: str) -> str:
    if not isinstance(value, str) or TR_RE.fullmatch(value) is None:
        raise InvalidInput(f"{name}の形式が不正です")
    return value


def _refs(value: object, name: str) -> list[str]:
    if (
        not isinstance(value, list)
        or not all(isinstance(item, str) and item for item in value)
        or len(set(value)) != len(value)
    ):
        raise InvalidInput(f"{name}が不正です")
    return sorted(value)


def _state(rows: object) -> list[dict]:
    result = []
    seen = set()
    for index, row in enumerate(ensure_list(rows, "previous_tr_ids")):
        if not isinstance(row, dict) or set(row) != {"tr_id", "status", "scope_refs"}:
            raise InvalidInput(f"previous_tr_ids[{index}]が不正です")
        ref = _id(row["tr_id"], f"previous_tr_ids[{index}].tr_id")
        scope_refs = _refs(row["scope_refs"], f"previous_tr_ids[{index}].scope_refs")
        if any(SCOPE_RE.fullmatch(value) is None for value in scope_refs):
            raise InvalidInput("previous_tr_ids.scope_refsが不正です")
        if (
            ref in seen
            or not isinstance(row["status"], str)
            or row["status"] not in {"active", "inactive", "deleted"}
        ):
            raise InvalidInput("previous_tr_idsが重複または不正です")
        seen.add(ref)
        result.append({"tr_id": ref, "status": row["status"], "scope_refs": scope_refs})
    return result


def _disposition_refs(
    rows: object, current_entities: list[dict], input_mode: str
) -> tuple[set[tuple[str, str]], list[tuple[dict, list[dict[str, str]]]]]:
    result = set()
    normalized_rows = []
    for index, row in enumerate(ensure_list(rows, "dispositions")):
        normalized, dependencies = normalize_machine_entity_disposition(
            row,
            current_entities,
            allowed_handlings={
                "対象外",
                "別テストレベル",
                "残存リスク",
                "ブロック中",
                "重複",
            },
            allowed_upstream_entity_types={
                "authority",
                "product_risk",
                "acceptance_criterion",
            },
            input_mode=input_mode,
        )
        upstream = normalized["upstream_entity"]
        expected_skill = {
            "authority": "spec-analysis",
            "product_risk": "test-analysis",
            "acceptance_criterion": "spec-analysis",
        }[upstream["entity_type"]]
        if upstream["skill"] != expected_skill:
            raise InvalidInput("TR disposition upstream_entity skill/typeが不一致です")
        if (
            upstream["entity_type"] == "acceptance_criterion"
            and normalized["handling"] == "重複"
        ):
            raise InvalidInput("Acceptance Criterion dispositionでは重複を許可しません")
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
    required = {
        "authorities",
        "risks",
        "acceptance_criteria",
        "scope_ids",
        "test_requirements",
        "dispositions",
        "previous_tr_ids",
        "update_scope_tr_ids",
        "inactive_tr_ids",
        "inactive_tr_history",
        "zero_scope_terminal",
    }
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
        if (
            not isinstance(row, dict)
            or set(row) != {"risk_id", "mapped_priority"}
            or row["mapped_priority"] not in PRIORITY_ORDER
        ):
            raise InvalidInput("risks schemaが不正です")
        if row["risk_id"] in risk_priorities:
            raise InvalidInput("risk_idが重複しています")
        risk_priorities[row["risk_id"]] = row["mapped_priority"]
    current_entities = validate_upstream_entities(metadata)
    acceptance_rows: list[dict[str, Any]] = []
    acceptance_by_id: dict[str, dict[str, Any]] = {}
    for index, row in enumerate(
        ensure_list(input_value["acceptance_criteria"], "acceptance_criteria")
    ):
        if not isinstance(row, dict) or set(row) != {"ac_id", "authority_refs"}:
            raise InvalidInput(f"acceptance_criteria[{index}] schemaが不正です")
        ac_id = row["ac_id"]
        if not isinstance(ac_id, str) or AC_RE.fullmatch(ac_id) is None:
            raise InvalidInput(f"acceptance_criteria[{index}].ac_idが不正です")
        refs = _refs(
            row["authority_refs"], f"acceptance_criteria[{index}].authority_refs"
        )
        if not refs or set(refs) - authority_ids:
            raise InvalidInput(
                f"acceptance_criteria[{index}].authority_refsが既知Authority集合外です"
            )
        if ac_id in acceptance_by_id:
            raise InvalidInput("acceptance_criteria ac_idが重複しています")
        normalized = {"ac_id": ac_id, "authority_refs": refs}
        acceptance_rows.append(normalized)
        acceptance_by_id[ac_id] = normalized
    if [row["ac_id"] for row in acceptance_rows] != sorted(acceptance_by_id):
        raise InvalidInput("acceptance_criteriaはac_id順である必要があります")
    scope_ids = input_value["scope_ids"]
    if (
        not isinstance(scope_ids, list)
        or not all(
            isinstance(value, str) and SCOPE_RE.fullmatch(value) for value in scope_ids
        )
        or len(scope_ids) != len(set(scope_ids))
        or scope_ids != sorted(scope_ids)
    ):
        raise InvalidInput(
            "scope_idsは重複なしのcanonical SCOPE ID配列である必要があります"
        )
    scope_id_set = set(scope_ids)
    upstream_ac_entities = {
        entity["entity_ref"]: entity
        for entity in current_entities
        if entity["skill"] == "spec-analysis"
        and entity["entity_type"] == "acceptance_criterion"
    }
    if metadata["input_mode"] == "artifact":
        upstream_ac_map = {
            ac_id: sorted(entity["content"].get("authority_refs", []))
            for ac_id, entity in upstream_ac_entities.items()
        }
        semantic_ac_map = {
            ac_id: row["authority_refs"] for ac_id, row in acceptance_by_id.items()
        }
        if upstream_ac_map != semantic_ac_map:
            raise InvalidInput(
                "artifact mode acceptance_criteriaがcurrent AC Entity集合と一致しません"
            )
    dispositions, disposition_rows = _disposition_refs(
        input_value["dispositions"], current_entities, metadata["input_mode"]
    )
    previous = _state(input_value["previous_tr_ids"])
    previous_map = {row["tr_id"]: row for row in previous}
    update_scope = input_value["update_scope_tr_ids"]
    if (
        not isinstance(update_scope, list)
        or not all(isinstance(value, str) for value in update_scope)
        or len(set(update_scope)) != len(update_scope)
    ):
        raise InvalidInput("update_scope_tr_idsが不正です")
    update_scope_set = {_id(value, "update_scope_tr_ids") for value in update_scope}
    if any(
        previous_map.get(ref, {}).get("status") not in {"active", "inactive"}
        for ref in update_scope_set
    ):
        raise InvalidInput(
            "update_scope_tr_idsはactive / inactive previous stateを参照する必要があります"
        )
    inactive_ids = input_value["inactive_tr_ids"]
    if (
        not isinstance(inactive_ids, list)
        or not all(
            isinstance(value, str) and TR_RE.fullmatch(value) for value in inactive_ids
        )
        or len(set(inactive_ids)) != len(inactive_ids)
        or inactive_ids != sorted(inactive_ids)
    ):
        raise InvalidInput("inactive_tr_idsが不正です")
    inactive_set = set(inactive_ids)
    if inactive_set & update_scope_set or any(
        previous_map.get(ref, {}).get("status") != "active" for ref in inactive_set
    ):
        raise InvalidInput(
            "inactive_tr_idsはupdate scope外のactive previous TRだけを指定できます"
        )
    if not isinstance(input_value["zero_scope_terminal"], bool):
        raise InvalidInput("zero_scope_terminalはbooleanである必要があります")
    zero_scope_terminal = input_value["zero_scope_terminal"]
    if zero_scope_terminal and (
        scope_ids
        or input_value["acceptance_criteria"]
        or input_value["test_requirements"]
        or input_value["dispositions"]
        or input_value["authorities"]
        or input_value["risks"]
        or inactive_set
        or update_scope_set
        != {row["tr_id"] for row in previous if row["status"] in {"active", "inactive"}}
    ):
        raise InvalidInput(
            "zero_scope_terminalは全current inputが空で全previous active / inactive TRを閉じる場合だけ許可されます"
        )
    history_by_id: dict[str, dict[str, Any]] = {}
    history_order = []
    for index, raw_entity in enumerate(
        ensure_list(input_value["inactive_tr_history"], "inactive_tr_history")
    ):
        entity = validate_machine_entity(raw_entity, expected_skill=SKILL)
        content = entity["content"]
        history_scope_refs = content.get("scope_refs")
        if (
            entity["entity_type"] != "tr"
            or entity["entity_ref"] in history_by_id
            or content.get("tr_id") != entity["entity_ref"]
            or not isinstance(history_scope_refs, list)
            or not all(
                isinstance(ref, str) and SCOPE_RE.fullmatch(ref)
                for ref in history_scope_refs
            )
            or len(set(history_scope_refs)) != len(history_scope_refs)
            or history_scope_refs != sorted(history_scope_refs)
        ):
            raise InvalidInput(
                "inactive_tr_historyは重複なしのTR Entity snapshotが必要です"
            )
        history_by_id[entity["entity_ref"]] = entity
        history_order.append(entity["entity_ref"])
    if history_order != sorted(history_order):
        raise InvalidInput("inactive_tr_historyはtr_id順である必要があります")
    expected_inactive_ids = {
        row["tr_id"]
        for row in previous
        if row["status"] == "inactive" or row["tr_id"] in inactive_set
    }
    if set(history_by_id) != expected_inactive_ids:
        raise InvalidInput(
            "inactive_tr_historyがcurrent inactive TR stateと一致しません"
        )
    if zero_scope_terminal and (
        inactive_set or history_order != sorted(expected_inactive_ids)
    ):
        raise InvalidInput("zero_scope_terminalではinactive transitionを開始できません")
    legacy = input_value.get("legacy_tr_ids")
    if legacy is not None:
        if metadata["input_mode"] != "direct" or previous or update_scope_set:
            raise InvalidInput("legacy_tr_idsは初回direct昇格でのみ使用できます")
        seeded = seed_legacy_ids(legacy, TR_ID_RE, "legacy_tr_ids")
        for value in seeded:
            previous_map[value["id"]] = {
                "tr_id": value["id"],
                "status": value["status"],
                "scope_refs": [],
            }
            update_scope_set.add(value["id"])
        previous = sorted(previous_map.values(), key=lambda row: row["tr_id"])
    drafts = []
    seen_drafts = set()
    for index, row in enumerate(
        ensure_list(input_value["test_requirements"], "test_requirements")
    ):
        if not isinstance(row, dict):
            raise InvalidInput("TR draftが不正です")
        fields = {
            "draft_key",
            "identity_action",
            "reuse_id",
            "text",
            "acceptance_refs",
            "scope_refs",
            "authority_refs",
            "risk_refs",
            "priority",
            "priority_override_reason",
            "test_level",
            "observation_method",
        }
        reject_unknown(row, fields)
        key = ensure_nonempty_string(
            row["draft_key"], f"test_requirements[{index}].draft_key"
        )
        if key in seen_drafts or row["identity_action"] not in {"reuse", "new"}:
            raise InvalidInput("TR draft identityが不正です")
        seen_drafts.add(key)
        if row["identity_action"] == "reuse":
            _id(row["reuse_id"], "TR reuse_id")
        elif row["reuse_id"] is not None:
            raise InvalidInput("new TRのreuse_idはnullである必要があります")
        ensure_nonempty_string(row["text"], "TR text")
        for field in ("acceptance_refs", "scope_refs", "authority_refs", "risk_refs"):
            if (
                not isinstance(row[field], list)
                or not all(isinstance(value, str) and value for value in row[field])
                or len(set(row[field])) != len(row[field])
            ):
                raise InvalidInput(f"TR {field}が不正です")
        if set(row["acceptance_refs"]) - set(acceptance_by_id):
            raise InvalidInput("TR acceptance_refsにunknown ACがあります")
        if set(row["scope_refs"]) - scope_id_set:
            raise InvalidInput("TR scope_refsにunknown Scopeがあります")
        if metadata["input_mode"] == "artifact" and scope_ids and not row["scope_refs"]:
            raise InvalidInput(
                "UI target artifact modeのcurrent TRにはscope_refsが必要です"
            )
        if metadata["input_mode"] == "artifact":
            required_scope_refs = {
                upstream_ac_entities[ac_id]["content"].get("scope", {}).get("scope_id")
                for ac_id in row["acceptance_refs"]
            }
            if None in required_scope_refs or not required_scope_refs.issubset(
                row["scope_refs"]
            ):
                raise InvalidInput("TR scope_refsから参照ACのScopeが欠落しています")
        if row["priority"] not in PRIORITY_ORDER or (
            row["priority_override_reason"] is not None
            and (
                not isinstance(row["priority_override_reason"], str)
                or not row["priority_override_reason"]
            )
        ):
            raise InvalidInput("TR priorityが不正です")
        drafts.append(canonicalize(row))
    if metadata["input_mode"] == "direct":
        referenced_ac_ids = {
            ac_id for draft in drafts for ac_id in draft["acceptance_refs"]
        } | {
            row["upstream_entity"]["entity_ref"]
            for row, _dependencies in disposition_rows
            if row["upstream_entity"]["entity_type"] == "acceptance_criterion"
        }
        for ac_id in referenced_ac_ids:
            entity = upstream_ac_entities.get(ac_id)
            if entity is None:
                continue
            semantic = acceptance_by_id.get(ac_id)
            content = entity["content"]
            if (
                semantic is None
                or content.get("ac_id") != ac_id
                or sorted(content.get("authority_refs", []))
                != semantic["authority_refs"]
            ):
                raise InvalidInput(
                    "direct modeの参照AC Entityがsemantic acceptance_criteriaと一致しません"
                )
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
            numbers = [
                int(match.group(1))
                for value in used
                if (match := TR_RE.fullmatch(value))
            ]
            number = max(numbers, default=0) + 1
            if number > 999:
                raise InvalidInput("id_space_exhausted")
            ref = f"TR-{number:03d}"
            used.add(ref)
        mapping[draft["draft_key"]] = ref
        unknown_authorities = sorted(set(draft["authority_refs"]) - authority_ids)
        unknown_risks = sorted(set(draft["risk_refs"]) - set(risk_priorities))
        if unknown_authorities or unknown_risks:
            violations.append(
                {
                    "target_key": f"violation:unknown:{draft['draft_key']}",
                    "issue_type": "unknown_reference",
                    "entity_ref": draft["draft_key"],
                    "unknown_authorities": unknown_authorities,
                    "unknown_risks": unknown_risks,
                }
            )
        minimum = max(
            (
                PRIORITY_ORDER[risk_priorities[risk]]
                for risk in draft["risk_refs"]
                if risk in risk_priorities
            ),
            default=0,
        )
        if (
            minimum
            and PRIORITY_ORDER[draft["priority"]] < minimum
            and not draft["priority_override_reason"]
        ):
            violations.append(
                {
                    "target_key": f"violation:priority:{draft['draft_key']}",
                    "issue_type": "priority_override_reason_required",
                    "entity_ref": draft["draft_key"],
                }
            )
    linked = {
        (kind, ref)
        for draft in drafts
        for kind, refs in (
            ("authority", draft["authority_refs"]),
            ("product_risk", draft["risk_refs"]),
            ("acceptance_criterion", draft["acceptance_refs"]),
        )
        for ref in refs
    }
    expected = (
        {("authority", ref) for ref in authority_ids}
        | {("product_risk", ref) for ref in risk_priorities}
        | {("acceptance_criterion", ref) for ref in acceptance_by_id}
    )
    for key in sorted(expected):
        if key in linked and key in dispositions:
            violations.append(
                {
                    "target_key": f"violation:linked-disposed:{key[0]}:{key[1]}",
                    "issue_type": "linked_and_disposed",
                    "entity_ref": key[1],
                }
            )
        elif key not in linked and key not in dispositions:
            violations.append(
                {
                    "target_key": f"violation:unclosed:{key[0]}:{key[1]}",
                    "issue_type": "unclosed_reference",
                    "entity_ref": key[1],
                }
            )
    entities = []
    for draft in drafts:
        tr_id = mapping[draft["draft_key"]]
        content = {
            key: draft[key]
            for key in (
                "text",
                "acceptance_refs",
                "scope_refs",
                "authority_refs",
                "risk_refs",
                "priority",
                "priority_override_reason",
                "test_level",
                "observation_method",
            )
        }
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
        for ac_id in draft["acceptance_refs"]:
            ac_entity = upstream_ac_entities.get(ac_id)
            if ac_entity is not None:
                ref_identities.append(("spec-analysis", "acceptance_criterion", ac_id))
                if metadata["input_mode"] == "artifact":
                    ref_identities.extend(
                        (
                            dependency["skill"],
                            dependency["entity_type"],
                            dependency["entity_ref"],
                        )
                        for dependency in ac_entity["upstream_entity_dependencies"]
                        if dependency["skill"] == "spec-analysis"
                        and dependency["entity_type"] == "authority"
                    )
        deps = resolve_entity_dependencies(
            ref_identities,
            current_entities,
            require_all=metadata["input_mode"] == "artifact",
        )
        entities.append(
            make_machine_entity(
                SKILL,
                "tr",
                tr_id,
                {"tr_id": tr_id, **content},
                upstream_entity_dependencies=deps,
                runtime_dependencies=[
                    machine_entity_runtime_dependency(
                        SKILL, "artifact:requirement_structure:all"
                    )
                ],
            )
        )
    for row, deps in disposition_rows:
        upstream_ref = row["upstream_entity"]
        ref = f"{upstream_ref['entity_type']}:{upstream_ref['entity_ref']}"
        entities.append(
            make_machine_entity(
                SKILL,
                "disposition",
                ref,
                row,
                upstream_entity_dependencies=deps,
                runtime_dependencies=[
                    machine_entity_runtime_dependency(
                        SKILL, "artifact:requirement_structure:all"
                    )
                ],
            )
        )
    states = []
    for row in previous:
        status = row["status"]
        scope_refs = row["scope_refs"]
        if row["tr_id"] in update_scope_set:
            status = "active" if row["tr_id"] in reused else "deleted"
            if status == "active":
                scope_refs = next(
                    draft["scope_refs"]
                    for draft in drafts
                    if mapping[draft["draft_key"]] == row["tr_id"]
                )
            elif zero_scope_terminal:
                scope_refs = []
        elif row["tr_id"] in inactive_set:
            status = "inactive"
        states.append(
            {"tr_id": row["tr_id"], "status": status, "scope_refs": scope_refs}
        )
    states.extend(
        {
            "tr_id": ref,
            "status": "active",
            "scope_refs": next(
                draft["scope_refs"]
                for draft in drafts
                if mapping[draft["draft_key"]] == ref
            ),
        }
        for ref in mapping.values()
    )
    state_map = {row["tr_id"]: row for row in states}
    inactive_history = [
        history_by_id[ref]
        for ref in sorted(state_map)
        if state_map[ref]["status"] == "inactive"
    ]
    violations.sort(key=lambda row: row["target_key"])
    return {
        "runtime_status": "ok",
        "support_status": "supported",
        "result_status": "ready" if not violations else "unresolved",
        "runtime_required": True,
        "deterministic_generated": True,
        "payload": {
            "tr_id_map": [
                {
                    "draft_key": draft["draft_key"],
                    "tr_id": mapping[draft["draft_key"]],
                    "identity_action": draft["identity_action"],
                }
                for draft in sorted(drafts, key=lambda row: row["draft_key"])
            ],
            "tr_id_state": [state_map[key] for key in sorted(state_map)],
            "inactive_tr_history": inactive_history,
            "violations": violations,
            "entities": sorted(entities, key=lambda row: row["entity_ref"]),
        },
        "issues": [
            {
                "issue_type": row["issue_type"],
                "blocking": True,
                "target_key": row["target_key"],
                "authority_refs": [],
            }
            for row in violations
        ],
    }


if __name__ == "__main__":
    raise SystemExit(
        run_cli(
            generate,
            skill=SKILL,
            generator=GENERATOR,
            generator_contract_version=GENERATOR_CONTRACT_VERSION,
            generator_path=SCRIPT_PATH,
            aggregate=True,
        )
    )
