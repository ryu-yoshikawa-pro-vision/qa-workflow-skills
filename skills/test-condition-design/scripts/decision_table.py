"""Generate deterministic Decision Table rules and don't-care candidates."""

from __future__ import annotations

import hashlib
from itertools import product
from pathlib import Path
from typing import Any

from runtime_contract import (
    InvalidInput,
    LimitExceeded,
    MAX_EXPLORATION_NODES,
    canonical_json_bytes,
    canonical_json_text,
    canonicalize,
    ensure_int,
    ensure_list,
    ensure_nonempty_string,
    post_process_targets,
    reject_unknown,
    run_cli,
    typed_sort_key,
    typed_value,
)


SKILL = "test-condition-design"
GENERATOR = "decision_table"
GENERATOR_CONTRACT_VERSION = "decision-table-v1"
SCRIPT_PATH = Path(__file__).resolve()
MAX_RULES = 65_536


def _key(value: Any, name: str) -> str:
    return ensure_nonempty_string(value, name)


def _refs(value: Any, name: str) -> list[str]:
    if not isinstance(value, list) or len(set(value)) != len(value) or not all(isinstance(item, str) and item for item in value):
        raise InvalidInput(f"{name}が不正です")
    return sorted(value)


def _value_in(values: list[dict[str, Any]], value: dict[str, Any]) -> bool:
    return canonical_json_text(value) in {canonical_json_text(item) for item in values}


def _hash_component(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(canonicalize(value))).hexdigest()


def _assignment_key(assignment: dict[str, dict[str, Any]]) -> str:
    return canonical_json_text(assignment)


def _constraint_matches(assignment: dict[str, dict[str, Any]], constraint: dict[str, Any]) -> bool:
    return all(assignment[key] == value for key, value in constraint["assignment"].items())


def _issue(issue_type: str, blocking: bool, *, target_key: str | None = None, authority_refs: list[str] | None = None, required_information: str | None = None) -> dict[str, Any]:
    row: dict[str, Any] = {
        "issue_type": issue_type,
        "blocking": blocking,
        "target_key": target_key,
        "authority_refs": sorted(set(authority_refs or [])),
    }
    if required_information is not None:
        row["required_information"] = required_information
    return row


def _normalize(input_value: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    reject_unknown(input_value, {"conditions", "actions", "known_rules", "constraints", "accepted_merges"})
    conditions_raw = ensure_list(input_value["conditions"], "conditions")
    actions_raw = ensure_list(input_value["actions"], "actions")
    rules_raw = ensure_list(input_value["known_rules"], "known_rules")
    constraints_raw = ensure_list(input_value["constraints"], "constraints")
    merges_raw = ensure_list(input_value["accepted_merges"], "accepted_merges")

    conditions: list[dict[str, Any]] = []
    condition_keys: set[str] = set()
    for index, row in enumerate(conditions_raw):
        if not isinstance(row, dict):
            raise InvalidInput(f"conditions[{index}]が不正です")
        reject_unknown(row, {"condition_key", "label", "values", "authority_refs"})
        key = _key(row["condition_key"], f"conditions[{index}].condition_key")
        if key in condition_keys:
            raise InvalidInput("condition_keyが重複しています")
        condition_keys.add(key)
        values = ensure_list(row["values"], f"conditions[{index}].values")
        if not values:
            raise InvalidInput("condition valuesは1件以上必要です")
        normalized_values = [typed_value(item) for item in values]
        if len({canonical_json_text(item) for item in normalized_values}) != len(normalized_values):
            raise InvalidInput("condition valueが重複しています")
        conditions.append({"condition_key": key, "label": ensure_nonempty_string(row["label"], "condition label"), "values": sorted(normalized_values, key=typed_sort_key), "authority_refs": _refs(row["authority_refs"], "condition authority_refs")})
    conditions.sort(key=lambda row: row["condition_key"])

    actions: list[dict[str, Any]] = []
    action_keys: set[str] = set()
    for index, row in enumerate(actions_raw):
        if not isinstance(row, dict):
            raise InvalidInput(f"actions[{index}]が不正です")
        reject_unknown(row, {"action_key", "label", "values", "authority_refs"})
        key = _key(row["action_key"], f"actions[{index}].action_key")
        if key in action_keys:
            raise InvalidInput("action_keyが重複しています")
        action_keys.add(key)
        values = ensure_list(row["values"], f"actions[{index}].values")
        if not values:
            raise InvalidInput("action valuesは1件以上必要です")
        normalized_values = [typed_value(item) for item in values]
        if len({canonical_json_text(item) for item in normalized_values}) != len(normalized_values):
            raise InvalidInput("action valueが重複しています")
        actions.append({"action_key": key, "label": ensure_nonempty_string(row["label"], "action label"), "values": sorted(normalized_values, key=typed_sort_key), "authority_refs": _refs(row["authority_refs"], "action authority_refs")})
    actions.sort(key=lambda row: row["action_key"])

    condition_map = {row["condition_key"]: row for row in conditions}
    action_map = {row["action_key"]: row for row in actions}
    constraints: list[dict[str, Any]] = []
    constraint_keys: set[str] = set()
    for index, row in enumerate(constraints_raw):
        if not isinstance(row, dict):
            raise InvalidInput(f"constraints[{index}]が不正です")
        reject_unknown(row, {"constraint_key", "assignment", "authority_refs"})
        key = _key(row["constraint_key"], f"constraints[{index}].constraint_key")
        if key in constraint_keys:
            raise InvalidInput("constraint_keyが重複しています")
        constraint_keys.add(key)
        assignment = row["assignment"]
        if not isinstance(assignment, dict) or not assignment:
            raise InvalidInput("constraint assignmentは1件以上必要です")
        normalized_assignment: dict[str, dict[str, Any]] = {}
        for condition_key, raw_value in assignment.items():
            if condition_key not in condition_map:
                raise InvalidInput("constraintがunknown conditionを参照しています")
            value = typed_value(raw_value)
            if not _value_in(condition_map[condition_key]["values"], value):
                raise InvalidInput("constraint valueがcondition domainにありません")
            normalized_assignment[condition_key] = value
        constraints.append({"constraint_key": key, "assignment": {item: normalized_assignment[item] for item in sorted(normalized_assignment)}, "authority_refs": _refs(row["authority_refs"], "constraint authority_refs")})
    constraints.sort(key=lambda row: row["constraint_key"])

    rules: list[dict[str, Any]] = []
    rule_keys: set[str] = set()
    for index, row in enumerate(rules_raw):
        if not isinstance(row, dict):
            raise InvalidInput(f"known_rules[{index}]が不正です")
        reject_unknown(row, {"rule_key", "when", "then", "authority_refs"})
        rule_key = _key(row["rule_key"], f"known_rules[{index}].rule_key")
        if rule_key in rule_keys:
            raise InvalidInput("rule_keyが重複しています")
        rule_keys.add(rule_key)
        when = row["when"]
        then = row["then"]
        if not isinstance(when, dict) or set(when) != condition_keys:
            raise InvalidInput("known rule whenは全condition keyを各1件持つ必要があります")
        if not isinstance(then, dict) or set(then) != action_keys:
            raise InvalidInput("known rule thenは全action keyを各1件持つ必要があります")
        normalized_when: dict[str, dict[str, Any]] = {}
        for condition_key in sorted(condition_keys):
            value = typed_value(when[condition_key])
            if not _value_in(condition_map[condition_key]["values"], value):
                raise InvalidInput("known rule when valueがcondition domainにありません")
            normalized_when[condition_key] = value
        normalized_then: dict[str, dict[str, Any]] = {}
        for action_key in sorted(action_keys):
            value = typed_value(then[action_key])
            if not _value_in(action_map[action_key]["values"], value):
                raise InvalidInput("known rule then valueがaction domainにありません")
            normalized_then[action_key] = value
        rules.append({"rule_key": rule_key, "when": normalized_when, "then": normalized_then, "authority_refs": _refs(row["authority_refs"], "rule authority_refs")})
    rules.sort(key=lambda row: row["rule_key"])

    accepted: list[str] = []
    for value in merges_raw:
        if not isinstance(value, str) or not value:
            raise InvalidInput("accepted_mergesはmerge_key stringのarrayである必要があります")
        if value in accepted:
            raise InvalidInput("accepted_mergesが重複しています")
        accepted.append(value)
    return conditions, actions, rules, constraints, sorted(accepted)


def _candidate_merges(conditions: list[dict[str, Any]], feasible: list[dict[str, Any]], known_by_assignment: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    condition_keys = [row["condition_key"] for row in conditions]
    for condition in condition_keys:
        groups: dict[str, list[dict[str, Any]]] = {}
        for row in feasible:
            remaining = {key: row["assignment"][key] for key in condition_keys if key != condition}
            groups.setdefault(_assignment_key(remaining), []).append(row)
        for remaining_key, rows in sorted(groups.items()):
            values = {canonical_json_text(row["assignment"][condition]) for row in rows}
            domain = {canonical_json_text(value) for value in next(item for item in conditions if item["condition_key"] == condition)["values"]}
            if values != domain:
                continue
            rule_rows: list[dict[str, Any]] = []
            for row in rows:
                matches = known_by_assignment.get(_assignment_key(row["assignment"]), [])
                if len(matches) != 1:
                    rule_rows = []
                    break
                rule_rows.append(matches[0])
            if not rule_rows:
                continue
            action_vector = canonical_json_text(rule_rows[0]["then"])
            if any(canonical_json_text(row["then"]) != action_vector for row in rule_rows):
                continue
            rule_keys = sorted(row["rule_key"] for row in rule_rows)
            merge_key = "dm:h" + _hash_component(rule_keys)
            candidates.append({
                "merge_key": merge_key,
                "condition_key": condition,
                "remaining_assignment": canonicalize(json_loads(remaining_key)),
                "rule_keys": rule_keys,
                "dont_care": True,
                "then": rule_rows[0]["then"],
                "authority_refs": sorted({ref for row in rule_rows for ref in row["authority_refs"]}),
            })
    candidates.sort(key=lambda row: row["merge_key"])
    return candidates


def json_loads(value: str) -> Any:
    # The key is produced by canonical_json_text and therefore is strict JSON.
    import json

    return json.loads(value)


def generate(input_value: dict, metadata: dict) -> dict:
    if metadata["model_key"] is None or metadata["model_type"] != "decision" or metadata["runtime_unit_key"] != f"model:{metadata['model_key']}":
        raise InvalidInput("decision tableのruntime metadataが不正です")
    conditions, actions, rules, constraints, accepted_merges = _normalize(input_value)
    domain_sizes = 1
    for condition in conditions:
        domain_sizes *= len(condition["values"])
        if domain_sizes > MAX_RULES:
            raise LimitExceeded("Decision Table rule spaceがhard limitを超えています")
    if domain_sizes > MAX_EXPLORATION_NODES:
        raise LimitExceeded("Decision Table exploration nodeがhard limitを超えています")

    assignments: list[dict[str, dict[str, Any]]] = []
    condition_values = [condition["values"] for condition in conditions]
    condition_keys = [condition["condition_key"] for condition in conditions]
    for values in product(*condition_values) if condition_values else [()]:
        assignments.append({key: value for key, value in zip(condition_keys, values)})
    constraints_by_key = {row["constraint_key"]: row for row in constraints}
    feasible = [
        {"assignment": assignment}
        for assignment in assignments
        if not any(_constraint_matches(assignment, constraint) for constraint in constraints)
    ]
    feasible.sort(key=lambda row: _assignment_key(row["assignment"]))
    known_by_assignment: dict[str, list[dict[str, Any]]] = {}
    for rule in rules:
        key = _assignment_key(rule["when"])
        known_by_assignment.setdefault(key, []).append(rule)

    issues: list[dict[str, Any]] = []
    valid_rules: list[dict[str, Any]] = []
    contradictions: list[dict[str, Any]] = []
    for assignment_row in feasible:
        assignment = assignment_row["assignment"]
        key = _assignment_key(assignment)
        matches = known_by_assignment.get(key, [])
        if not matches:
            continue
        if any(_constraint_matches(assignment, constraint) for constraint in constraints):
            # This branch is unreachable by construction, retained for defensive clarity.
            continue
        vectors = {canonical_json_text(rule["then"]) for rule in matches}
        if len(vectors) > 1:
            contradictions.append({"assignment": assignment, "rule_keys": sorted(rule["rule_key"] for rule in matches)})
            issues.append(_issue("contradictory_rules", True, authority_refs=[ref for rule in matches for ref in rule["authority_refs"]]))
        else:
            valid_rules.append(matches[0])

    for rule in rules:
        assignment = rule["when"]
        if any(_constraint_matches(assignment, constraint) for constraint in constraints):
            issues.append(_issue("rule_conflicts_with_constraint", True, authority_refs=rule["authority_refs"]))

    feasible_keys = {_assignment_key(row["assignment"]) for row in feasible}
    known_keys = set(known_by_assignment)
    unspecified_keys = sorted(feasible_keys - known_keys)
    for key in unspecified_keys:
        issues.append(_issue("unspecified_assignment", True, required_information="Decision Tableの成立可能assignmentに対するaction vector"))
    if contradictions:
        issues.append(_issue("contradictory_assignment", True))

    targets: list[dict[str, Any]] = []
    for rule in valid_rules:
        assignment_key = _assignment_key(rule["when"])
        target_key = "dt:h" + _hash_component({"assignment": rule["when"]})
        targets.append({
            "target_key": target_key,
            "rule_key": rule["rule_key"],
            "assignment": rule["when"],
            "action_vector": rule["then"],
            "authority_refs": rule["authority_refs"],
            "materializable": True,
            "execution": {"assignment": rule["when"], "action_vector": rule["then"], "rule_key": rule["rule_key"], "authority_refs": rule["authority_refs"]},
        })
    for key in unspecified_keys:
        assignment = next(row["assignment"] for row in feasible if _assignment_key(row["assignment"]) == key)
        targets.append({
            "target_key": "dt:h" + _hash_component({"assignment": assignment}),
            "assignment": assignment,
            "action_vector": None,
            "materializable": False,
            "execution": None,
            "disposition": "unspecified",
            "authority_refs": [],
        })
    for item in contradictions:
        target_key = "dt:h" + _hash_component({"assignment": item["assignment"]})
        if not any(row["target_key"] == target_key for row in targets):
            targets.append({"target_key": target_key, "assignment": item["assignment"], "action_vector": None, "materializable": False, "execution": None, "disposition": "contradiction", "authority_refs": []})

    candidates = _candidate_merges(conditions, feasible, known_by_assignment)
    candidate_map = {row["merge_key"]: row for row in candidates}
    for merge_key in accepted_merges:
        if merge_key not in candidate_map:
            issues.append(_issue("invalid_accepted_merge", True))
    accepted_rules = [candidate_map[key] for key in accepted_merges if key in candidate_map]
    accepted_rules.sort(key=lambda row: row["merge_key"])
    targets = post_process_targets(metadata["model_key"], sorted(targets, key=lambda row: row["target_key"]))
    complete = bool(feasible) and len(valid_rules) == len(feasible) and not issues
    result_status = "ready" if not issues else "unresolved"
    return {
        "runtime_status": "ok",
        "support_status": "supported",
        "result_status": result_status,
        "runtime_required": True,
        "deterministic_generated": True,
        "payload": {
            "conditions": conditions,
            "actions": actions,
            "known_rules": rules,
            "constraints": constraints,
            "accepted_merges": accepted_merges,
            "targets": targets,
            "dont_care_candidates": candidates,
            "dont_care_rules": accepted_rules,
            "unspecified_assignments": [row["assignment"] for row in feasible if _assignment_key(row["assignment"]) in set(unspecified_keys)],
            "contradictions": contradictions,
            "coverage_summary": {"criterion": "decision-rules", "required": len(feasible), "covered": len(valid_rules), "complete": complete},
        },
        "issues": issues,
    }


if __name__ == "__main__":
    raise SystemExit(run_cli(generate, skill=SKILL, generator=GENERATOR, generator_contract_version=GENERATOR_CONTRACT_VERSION, generator_path=SCRIPT_PATH))
