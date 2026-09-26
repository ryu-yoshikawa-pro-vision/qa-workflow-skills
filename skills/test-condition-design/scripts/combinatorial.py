"""Deterministic exhaustive, Base Choice, and N-wise combinatorial coverage."""

from __future__ import annotations

import hashlib
from itertools import combinations, product
from pathlib import Path
from typing import Any, Callable

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
GENERATOR = "combinatorial"
GENERATOR_CONTRACT_VERSION = "combinatorial-v1"
SCRIPT_PATH = Path(__file__).resolve()
MAX_FULL_ASSIGNMENTS = 65_536


def _refs(value: Any, name: str) -> list[str]:
    if not isinstance(value, list) or len(set(value)) != len(value) or not all(isinstance(item, str) and item for item in value):
        raise InvalidInput(f"{name}が不正です")
    return sorted(value)


def _key(value: Any, name: str) -> str:
    return ensure_nonempty_string(value, name)


def _hash_component(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(canonicalize(value))).hexdigest()


def _same(left: dict[str, Any], right: dict[str, Any]) -> bool:
    return canonical_json_text(left) == canonical_json_text(right)


def _normalize(input_value: dict[str, Any]) -> tuple[str, list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    reject_unknown(input_value, {"mode", "factors", "constraints"}, {"base_assignment", "strength", "global_strength", "subsets", "coverage_selection_reason"})
    mode = input_value["mode"]
    if mode not in {"exhaustive", "base-choice", "t-wise", "mixed-strength"}:
        raise InvalidInput("combinatorial modeが不正です")
    factors_raw = ensure_list(input_value["factors"], "factors")
    if not factors_raw:
        raise InvalidInput("factorsは1件以上必要です")
    factors: list[dict[str, Any]] = []
    factor_map: dict[str, dict[str, Any]] = {}
    for index, row in enumerate(factors_raw):
        if not isinstance(row, dict):
            raise InvalidInput(f"factors[{index}]が不正です")
        reject_unknown(row, {"factor_key", "label", "values", "authority_refs"})
        key = _key(row["factor_key"], "factor_key")
        if key in factor_map:
            raise InvalidInput("factor_keyが重複しています")
        values = ensure_list(row["values"], "factor.values")
        if not values:
            raise InvalidInput("factor valuesは1件以上必要です")
        normalized_values = [typed_value(value) for value in values]
        if len({canonical_json_text(value) for value in normalized_values}) != len(normalized_values):
            raise InvalidInput("factor valueが重複しています")
        normalized = {"factor_key": key, "label": ensure_nonempty_string(row["label"], "factor label"), "values": sorted(normalized_values, key=typed_sort_key), "authority_refs": _refs(row["authority_refs"], "factor authority_refs")}
        factor_map[key] = normalized
        factors.append(normalized)
    factors.sort(key=lambda row: row["factor_key"])
    factor_map = {row["factor_key"]: row for row in factors}

    constraints_raw = ensure_list(input_value["constraints"], "constraints")
    constraints: list[dict[str, Any]] = []
    constraint_keys: set[str] = set()
    for index, row in enumerate(constraints_raw):
        if not isinstance(row, dict):
            raise InvalidInput(f"constraints[{index}]が不正です")
        reject_unknown(row, {"constraint_key", "assignment", "authority_refs"})
        key = _key(row["constraint_key"], "constraint_key")
        if key in constraint_keys:
            raise InvalidInput("constraint_keyが重複しています")
        constraint_keys.add(key)
        if not isinstance(row["assignment"], dict) or not row["assignment"]:
            raise InvalidInput("constraint assignmentは1件以上必要です")
        assignment: dict[str, dict[str, Any]] = {}
        for factor_key, raw_value in row["assignment"].items():
            if factor_key not in factor_map:
                raise InvalidInput("constraintがunknown factorを参照しています")
            value = typed_value(raw_value)
            if canonical_json_text(value) not in {canonical_json_text(candidate) for candidate in factor_map[factor_key]["values"]}:
                raise InvalidInput("constraint valueがfactor domainにありません")
            assignment[factor_key] = value
        constraints.append({"constraint_key": key, "assignment": {item: assignment[item] for item in sorted(assignment)}, "authority_refs": _refs(row["authority_refs"], "constraint authority_refs")})
    constraints.sort(key=lambda row: row["constraint_key"])

    allowed_by_mode = {
        "exhaustive": {"mode", "factors", "constraints"},
        "base-choice": {"mode", "factors", "constraints", "base_assignment"},
        "t-wise": {"mode", "factors", "constraints", "strength", "coverage_selection_reason"},
        "mixed-strength": {"mode", "factors", "constraints", "global_strength", "subsets", "coverage_selection_reason"},
    }[mode]
    unknown = set(input_value) - allowed_by_mode
    if unknown:
        raise InvalidInput("combinatorial modeに不要なfieldがあります")
    factor_count = len(factors)
    strategy: dict[str, Any] = {"mode": mode}
    if mode == "base-choice":
        if not isinstance(input_value.get("base_assignment"), dict) or set(input_value["base_assignment"]) != set(factor_map):
            raise InvalidInput("base_assignmentは全factorを持つ必要があります")
        base: dict[str, dict[str, Any]] = {}
        for key in sorted(factor_map):
            value = typed_value(input_value["base_assignment"][key])
            if canonical_json_text(value) not in {canonical_json_text(candidate) for candidate in factor_map[key]["values"]}:
                raise InvalidInput("base_assignment valueがfactor domainにありません")
            base[key] = value
        strategy["base_assignment"] = base
    elif mode == "t-wise":
        strength = ensure_int(input_value.get("strength"), "strength", minimum=2, maximum=factor_count)
        reason = input_value.get("coverage_selection_reason")
        if strength > 2 and (not isinstance(reason, str) or not reason.strip()):
            raise InvalidInput("strength>2ではcoverage_selection_reasonが必要です")
        if not isinstance(reason, str):
            reason = ""
        strategy.update({"strength": strength, "coverage_selection_reason": reason})
    elif mode == "mixed-strength":
        global_strength = ensure_int(input_value.get("global_strength"), "global_strength", minimum=2, maximum=factor_count)
        subsets_raw = ensure_list(input_value.get("subsets"), "subsets")
        if not subsets_raw:
            raise InvalidInput("mixed-strength subsetsは1件以上必要です")
        subsets: list[dict[str, Any]] = []
        seen_subsets: set[tuple[str, ...]] = set()
        max_strength = global_strength
        for row in subsets_raw:
            if not isinstance(row, dict):
                raise InvalidInput("subsetが不正です")
            reject_unknown(row, {"factor_keys", "strength"})
            keys = ensure_list(row["factor_keys"], "subset.factor_keys")
            if len(keys) < 2 or len(set(keys)) != len(keys) or any(key not in factor_map for key in keys):
                raise InvalidInput("subset.factor_keysが不正です")
            sorted_keys = tuple(sorted(keys))
            if sorted_keys in seen_subsets:
                raise InvalidInput("subsetが重複しています")
            seen_subsets.add(sorted_keys)
            strength = ensure_int(row["strength"], "subset.strength", minimum=2, maximum=len(sorted_keys))
            max_strength = max(max_strength, strength)
            subsets.append({"factor_keys": list(sorted_keys), "strength": strength})
        reason = input_value.get("coverage_selection_reason")
        if max_strength > 2 and (not isinstance(reason, str) or not reason.strip()):
            raise InvalidInput("strength>2ではcoverage_selection_reasonが必要です")
        if not isinstance(reason, str):
            reason = ""
        strategy.update({"global_strength": global_strength, "subsets": sorted(subsets, key=lambda row: (row["factor_keys"], row["strength"])), "coverage_selection_reason": reason})
    return mode, factors, constraints, strategy


def _matches(assignment: dict[str, dict[str, Any]], constraint: dict[str, Any]) -> bool:
    return all(assignment[key] == value for key, value in constraint["assignment"].items())


def _tuple_key(factor_keys: list[str], assignment: dict[str, dict[str, Any]]) -> str:
    return canonical_json_text({"factor_keys": factor_keys, "assignment": {key: assignment[key] for key in factor_keys}})


def _full_product(factors: list[dict[str, Any]]) -> list[dict[str, dict[str, Any]]]:
    count = 1
    for factor in factors:
        count *= len(factor["values"])
    if count > MAX_FULL_ASSIGNMENTS:
        raise LimitExceeded("combinatorial exhaustive assignmentがhard limitを超えています")
    keys = [factor["factor_key"] for factor in factors]
    return [{key: value for key, value in zip(keys, values)} for values in product(*(factor["values"] for factor in factors))]


def _satisfies(assignment: dict[str, dict[str, Any]], constraints: list[dict[str, Any]]) -> bool:
    return not any(_matches(assignment, constraint) for constraint in constraints)


def _completion_search(factors: list[dict[str, Any]], constraints: list[dict[str, Any]], partial: dict[str, dict[str, Any]], *, collect: bool, exploration_budget: list[int]) -> tuple[str, list[dict[str, dict[str, Any]]]]:
    factor_map = {row["factor_key"]: row for row in factors}
    keys = [row["factor_key"] for row in factors]
    completions: list[dict[str, dict[str, Any]]] = []

    def walk(index: int, assignment: dict[str, dict[str, Any]]) -> str:
        exploration_budget[0] += 1
        if exploration_budget[0] > MAX_EXPLORATION_NODES:
            return "limit_exceeded"
        if any(all(key in assignment for key in constraint["assignment"]) and _matches(assignment, constraint) for constraint in constraints):
            return "unsat"
        if index == len(keys):
            if _satisfies(assignment, constraints):
                completions.append(dict(assignment))
                return "sat"
            return "unsat"
        key = keys[index]
        if key in assignment:
            return walk(index + 1, assignment)
        found = "unsat"
        for value in factor_map[key]["values"]:
            status = walk(index + 1, {**assignment, key: value})
            if status == "limit_exceeded":
                return status
            if status == "sat":
                found = "sat"
                if not collect:
                    return found
        return found

    status = walk(0, dict(partial))
    if not collect and completions:
        return "sat", [completions[0]]
    return status, sorted(completions, key=lambda row: tuple(canonical_json_text(row[key]) for key in keys))


def _tuple_targets(factors: list[dict[str, Any]], constraints: list[dict[str, Any]], requests: list[tuple[list[str], int]], exploration_budget: list[int]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    factor_map = {row["factor_key"]: row for row in factors}
    sat_targets: list[dict[str, Any]] = []
    diagnostics: list[dict[str, Any]] = []
    seen: set[str] = set()
    for factor_keys, strength in requests:
        for selected in combinations(factor_keys, strength):
            selected = tuple(sorted(selected))
            domains = [factor_map[key]["values"] for key in selected]
            for values in product(*domains):
                assignment = {key: value for key, value in zip(selected, values)}
                tuple_key = _tuple_key(list(selected), assignment)
                if tuple_key in seen:
                    continue
                seen.add(tuple_key)
                status, _ = _completion_search(factors, constraints, assignment, collect=False, exploration_budget=exploration_budget)
                diagnostics.append({"tuple": {"factor_keys": list(selected), "assignment": assignment}, "status": status})
                if status == "sat":
                    sat_targets.append({"factor_keys": list(selected), "assignment": assignment, "tuple_key": tuple_key})
                elif status == "limit_exceeded":
                    raise LimitExceeded("combinatorial tuple completionがhard limitを超えています")
    sat_targets.sort(key=lambda row: row["tuple_key"])
    diagnostics.sort(key=lambda row: _tuple_key(row["tuple"]["factor_keys"], row["tuple"]["assignment"]))
    return sat_targets, diagnostics


def _covers(row: dict[str, dict[str, Any]], target: dict[str, Any]) -> bool:
    return all(row[key] == value for key, value in target["assignment"].items())


def _greedy_rows(factors: list[dict[str, Any]], constraints: list[dict[str, Any]], targets: list[dict[str, Any]], exploration_budget: list[int]) -> list[dict[str, dict[str, Any]]]:
    if not targets:
        return []
    factor_count = 1
    for factor in factors:
        factor_count *= len(factor["values"])
    if factor_count <= MAX_FULL_ASSIGNMENTS:
        feasible_rows = [row for row in _full_product(factors) if _satisfies(row, constraints)]
    else:
        # N-wise selection does not require the full Cartesian product to be
        # materialized. Collect only deterministic completions of SAT tuples.
        by_row: dict[str, dict[str, dict[str, Any]]] = {}
        completion_count = 0
        for target in targets:
            status, completions = _completion_search(factors, constraints, target["assignment"], collect=True, exploration_budget=exploration_budget)
            if status == "limit_exceeded":
                raise LimitExceeded("combinatorial row completionがhard limitを超えています")
            for completion in completions:
                completion_count += 1
                if completion_count > MAX_EXPLORATION_NODES:
                    raise LimitExceeded("combinatorial row candidateがhard limitを超えています")
                by_row[canonical_json_text(completion)] = completion
        feasible_rows = sorted(by_row.values(), key=lambda row: tuple(canonical_json_text(row[key]) for key in [item["factor_key"] for item in factors]))
    uncovered = {row["tuple_key"]: row for row in targets}
    selected_rows: list[dict[str, dict[str, Any]]] = []
    factor_keys = [row["factor_key"] for row in factors]
    while uncovered:
        first_key = sorted(uncovered)[0]
        candidates = [row for row in feasible_rows if _covers(row, uncovered[first_key])]
        if not candidates:
            raise InvalidInput("SAT tupleのcompletionが見つかりません")
        scored: list[tuple[int, tuple[str, ...], dict[str, dict[str, Any]]]] = []
        for candidate in candidates:
            new_count = sum(1 for target in uncovered.values() if _covers(candidate, target))
            tie = tuple(canonical_json_text(candidate[key]) for key in factor_keys)
            scored.append((-new_count, tie, candidate))
        scored.sort(key=lambda item: (item[0], item[1]))
        chosen = scored[0][2]
        selected_rows.append(chosen)
        for key in list(uncovered):
            if _covers(chosen, uncovered[key]):
                del uncovered[key]
    return selected_rows


def generate(input_value: dict, metadata: dict) -> dict:
    if metadata["model_key"] is None or metadata["model_type"] != "comb" or metadata["runtime_unit_key"] != f"model:{metadata['model_key']}":
        raise InvalidInput("combinatorialのruntime metadataが不正です")
    mode, factors, constraints, strategy = _normalize(input_value)
    exploration_budget = [0]
    factor_keys = [row["factor_key"] for row in factors]
    all_assignments: list[dict[str, dict[str, Any]]] = []
    feasible: list[dict[str, dict[str, Any]]] = []
    infeasible: list[dict[str, Any]] = []
    if mode in {"exhaustive", "base-choice"}:
        all_assignments = _full_product(factors)
        feasible = [row for row in all_assignments if _satisfies(row, constraints)]
        infeasible = [{"assignment": row, "constraint_refs": [constraint["constraint_key"] for constraint in constraints if _matches(row, constraint)], "authority_refs": sorted({ref for constraint in constraints if _matches(row, constraint) for ref in constraint["authority_refs"]})} for row in all_assignments if not _satisfies(row, constraints)]
    target_rows: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []
    if mode == "exhaustive":
        rows = sorted(feasible, key=lambda row: tuple(canonical_json_text(row[key]) for key in factor_keys))
        for assignment in rows:
            target_rows.append({"factor_keys": factor_keys, "assignment": assignment})
    elif mode == "base-choice":
        base = strategy["base_assignment"]
        if not _satisfies(base, constraints):
            raise InvalidInput("base_assignmentがconstraintにより成立不能です")
        assignments = [base]
        for key in factor_keys:
            factor = next(row for row in factors if row["factor_key"] == key)
            for value in factor["values"]:
                if value != base[key]:
                    assignments.append({**base, key: value})
        for assignment in assignments:
            if _satisfies(assignment, constraints):
                target_rows.append({"factor_keys": factor_keys, "assignment": assignment})
            else:
                infeasible.append({"assignment": assignment, "constraint_refs": [constraint["constraint_key"] for constraint in constraints if _matches(assignment, constraint)], "authority_refs": sorted({ref for constraint in constraints if _matches(assignment, constraint) for ref in constraint["authority_refs"]}), "base_choice": True})
        rows = [row["assignment"] for row in target_rows]
    else:
        if mode == "t-wise":
            requests = [(factor_keys, strategy["strength"])]
        else:
            requests = [(factor_keys, strategy["global_strength"])] + [(row["factor_keys"], row["strength"]) for row in strategy["subsets"]]
        tuple_targets, diagnostics = _tuple_targets(factors, constraints, requests, exploration_budget)
        rows = _greedy_rows(factors, constraints, tuple_targets, exploration_budget)
        for target in tuple_targets:
            target_rows.append({"factor_keys": target["factor_keys"], "assignment": target["assignment"], "tuple_status": "sat"})
    rows = sorted(rows, key=lambda row: tuple(canonical_json_text(row[key]) for key in factor_keys))
    row_index = {canonical_json_text(row): index + 1 for index, row in enumerate(rows)}
    targets: list[dict[str, Any]] = []
    for target in target_rows:
        assignment = target["assignment"]
        factor_subset = target["factor_keys"]
        key_material = {"factor_keys": factor_subset, "assignment": {key: assignment[key] for key in factor_subset}}
        target_key = f"comb:{mode}:h" + _hash_component(key_material)
        witness = next((row for row in rows if _covers(row, target)), None)
        if witness is None:
            raise InvalidInput("combinatorial targetのwitness rowがありません")
        targets.append({"target_key": target_key, "factor_keys": factor_subset, "assignment": assignment, "row_index": row_index[canonical_json_text(witness)], "materializable": True, "execution": {"factor_assignment": assignment, "row": witness, "row_index": row_index[canonical_json_text(witness)]}})
    targets = post_process_targets(metadata["model_key"], sorted(targets, key=lambda row: row["target_key"]))
    required = len(target_rows)
    covered = len(targets)
    payload = {"mode": mode, "factors": factors, "constraints": constraints, "strategy": strategy, "rows": [{"row_index": index + 1, "assignment": row} for index, row in enumerate(rows)], "targets": targets, "infeasible_assignments": infeasible, "coverage_summary": {"criterion": "combinatorial-tuples" if mode in {"t-wise", "mixed-strength"} else "combinatorial-rows", "required": required, "covered": covered, "complete": required == covered}}
    if mode in {"t-wise", "mixed-strength"}:
        payload["tuple_diagnostics"] = diagnostics
    return {"runtime_status": "ok", "support_status": "supported", "result_status": "ready", "runtime_required": True, "deterministic_generated": True, "payload": payload, "issues": []}


if __name__ == "__main__":
    raise SystemExit(run_cli(generate, skill=SKILL, generator=GENERATOR, generator_contract_version=GENERATOR_CONTRACT_VERSION, generator_path=SCRIPT_PATH))
