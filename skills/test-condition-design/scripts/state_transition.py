"""Generate deterministic state-transition coverage with canonical setup prefixes."""

from __future__ import annotations

import hashlib
import heapq
from pathlib import Path
from typing import Any

from runtime_contract import (
    InvalidInput,
    LimitExceeded,
    MAX_EXPLORATION_NODES,
    canonical_json_bytes,
    canonicalize,
    ensure_int,
    ensure_key,
    ensure_list,
    ensure_nonempty_string,
    post_process_targets,
    reject_unknown,
    run_cli,
)


SKILL = "test-condition-design"
GENERATOR = "state_transition"
GENERATOR_CONTRACT_VERSION = "state-transition-v1"
SCRIPT_PATH = Path(__file__).resolve()


def _refs(value: Any, name: str) -> list[str]:
    if not isinstance(value, list) or len(set(value)) != len(value) or not all(isinstance(item, str) and item for item in value):
        raise InvalidInput(f"{name}が不正です")
    return sorted(value)


def _hash_component(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(canonicalize(value))).hexdigest()


def _edge_execution(edge: dict[str, Any], state_map: dict[str, dict[str, Any]]) -> dict[str, Any]:
    return {"transition_key": edge["transition_key"], "from": {"state_key": edge["from"], "label": state_map[edge["from"]]["label"]}, "event": edge["event"], "to": {"state_key": edge["to"], "label": state_map[edge["to"]]["label"]}}


def _shortest_paths(start: str, target: str, outgoing: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    queue: list[tuple[int, str, tuple[str, ...], str, list[dict[str, Any]]]] = [(0, start, (), start, [])]
    best: dict[str, tuple[int, tuple[str, ...]]] = {start: (0, ())}
    while queue:
        length, _initial, sequence, node, path = heapq.heappop(queue)
        if node == target:
            return path
        for edge in outgoing.get(node, []):
            if edge["to"] in {item["from"] for item in path} | {node}:
                continue
            next_sequence = sequence + (edge["transition_key"],)
            score = (length + 1, next_sequence)
            previous = best.get(edge["to"])
            if previous is not None and score >= previous:
                continue
            best[edge["to"]] = score
            heapq.heappush(queue, (length + 1, _initial, next_sequence, edge["to"], path + [edge]))
    return [] if start == target else []


def _enumerate_sequences(state_keys: list[str], outgoing: dict[str, list[dict[str, Any]]], length: int) -> list[list[dict[str, Any]]]:
    sequences: list[list[dict[str, Any]]] = []
    explored = 0

    def walk(start: str, node: str, path: list[dict[str, Any]]) -> None:
        nonlocal explored
        explored += 1
        if explored > MAX_EXPLORATION_NODES:
            raise LimitExceeded("n-switch sequence exploration nodeがhard limitを超えています")
        if len(path) == length:
            sequences.append(list(path))
            return
        for edge in outgoing.get(node, []):
            walk(start, edge["to"], path + [edge])

    for state_key in state_keys:
        walk(state_key, state_key, [])
    sequences.sort(key=lambda path: tuple(edge["transition_key"] for edge in path))
    return sequences


def _cycles(state_keys: list[str], outgoing: dict[str, list[dict[str, Any]]]) -> list[tuple[str, list[dict[str, Any]]]]:
    result: list[tuple[str, list[dict[str, Any]]]] = []
    seen: set[tuple[str, tuple[str, ...]]] = set()

    def walk(start: str, node: str, path: list[dict[str, Any]], visited: set[str]) -> None:
        for edge in outgoing.get(node, []):
            if edge["to"] == start:
                candidate = path + [edge]
                identity = (start, tuple(item["transition_key"] for item in candidate))
                if identity not in seen:
                    seen.add(identity)
                    result.append((start, candidate))
                continue
            if edge["to"] in visited:
                continue
            walk(start, edge["to"], path + [edge], visited | {edge["to"]})

    for start in state_keys:
        walk(start, start, [], {start})
    result.sort(key=lambda item: (item[0], tuple(edge["transition_key"] for edge in item[1])))
    return result


def generate(input_value: dict, metadata: dict) -> dict:
    if metadata["model_key"] is None or metadata["model_type"] != "state" or metadata["runtime_unit_key"] != f"model:{metadata['model_key']}":
        raise InvalidInput("state transitionのruntime metadataが不正です")
    reject_unknown(input_value, {"states", "initial_states", "terminal_states", "transitions", "reset_options", "invalid_transition_candidates", "coverage_mode"}, {"switch_count", "coverage_selection_reason"})
    states_raw = ensure_list(input_value["states"], "states")
    states: list[dict[str, Any]] = []
    state_map: dict[str, dict[str, Any]] = {}
    for index, row in enumerate(states_raw):
        if not isinstance(row, dict):
            raise InvalidInput(f"states[{index}]が不正です")
        reject_unknown(row, {"state_key", "label", "authority_refs"})
        key = ensure_key(row["state_key"], "state_key")
        if key in state_map:
            raise InvalidInput("state_keyが重複しています")
        normalized = {"state_key": key, "label": ensure_nonempty_string(row["label"], "state label"), "authority_refs": _refs(row["authority_refs"], "state authority_refs")}
        state_map[key] = normalized
        states.append(normalized)
    states.sort(key=lambda row: row["state_key"])
    state_keys = [row["state_key"] for row in states]

    def state_refs(value: Any, name: str, *, nonempty: bool = True) -> list[str]:
        values = ensure_list(value, name)
        if nonempty and not values:
            raise InvalidInput(f"{name}は1件以上必要です")
        if len(set(values)) != len(values) or any(value not in state_map for value in values):
            raise InvalidInput(f"{name}が不正です")
        return sorted(values)

    initial_states = state_refs(input_value["initial_states"], "initial_states")
    terminal_states = state_refs(input_value["terminal_states"], "terminal_states", nonempty=False)
    transitions_raw = ensure_list(input_value["transitions"], "transitions")
    transitions: list[dict[str, Any]] = []
    transition_map: dict[str, dict[str, Any]] = {}
    for index, row in enumerate(transitions_raw):
        if not isinstance(row, dict):
            raise InvalidInput(f"transitions[{index}]が不正です")
        reject_unknown(row, {"transition_key", "from", "event", "guard_status", "guard_refs", "to", "authority_refs"})
        key = ensure_key(row["transition_key"], "transition_key")
        if key in transition_map:
            raise InvalidInput("transition_keyが重複しています")
        if row["from"] not in state_map or row["to"] not in state_map or row["guard_status"] not in {True, False, None}:
            raise InvalidInput("transition reference/statusが不正です")
        guard_refs = _refs(row["guard_refs"], "guard_refs")
        if row["guard_status"] is False and not guard_refs:
            raise InvalidInput("guard_status=falseにはguard_refsが必要です")
        normalized = {"transition_key": key, "from": row["from"], "event": ensure_nonempty_string(row["event"], "transition event"), "guard_status": row["guard_status"], "guard_refs": guard_refs, "to": row["to"], "authority_refs": _refs(row["authority_refs"], "transition authority_refs")}
        transition_map[key] = normalized
        transitions.append(normalized)
    transitions.sort(key=lambda row: row["transition_key"])
    outgoing = {key: [] for key in state_keys}
    for edge in transitions:
        if edge["guard_status"] is True:
            outgoing[edge["from"]].append(edge)
    for key in outgoing:
        outgoing[key].sort(key=lambda row: row["transition_key"])

    reset_raw = ensure_list(input_value["reset_options"], "reset_options")
    resets: list[dict[str, Any]] = []
    reset_keys: set[str] = set()
    for index, row in enumerate(reset_raw):
        if not isinstance(row, dict):
            raise InvalidInput(f"reset_options[{index}]が不正です")
        reject_unknown(row, {"reset_key", "from_states", "to_state", "action", "authority_refs"})
        reset_key = ensure_key(row["reset_key"], "reset_key")
        if reset_key in reset_keys:
            raise InvalidInput("reset_keyが重複しています")
        reset_keys.add(reset_key)
        from_states = ensure_list(row["from_states"], "reset.from_states")
        if not from_states or len(set(from_states)) != len(from_states) or any(value != "*" and value not in state_map for value in from_states):
            raise InvalidInput("reset.from_statesが不正です")
        if row["to_state"] not in state_map:
            raise InvalidInput("reset.to_stateが不正です")
        resets.append({"reset_key": reset_key, "from_states": sorted(from_states), "to_state": row["to_state"], "action": ensure_nonempty_string(row["action"], "reset action"), "authority_refs": _refs(row["authority_refs"], "reset authority_refs")})
    resets.sort(key=lambda row: row["reset_key"])

    invalid_raw = ensure_list(input_value["invalid_transition_candidates"], "invalid_transition_candidates")
    invalid_candidates: list[dict[str, Any]] = []
    invalid_keys: set[str] = set()
    for index, row in enumerate(invalid_raw):
        if not isinstance(row, dict):
            raise InvalidInput(f"invalid_transition_candidates[{index}]が不正です")
        reject_unknown(row, {"candidate_key", "from", "event", "authority_refs"})
        key = ensure_key(row["candidate_key"], "candidate_key")
        if key in invalid_keys:
            raise InvalidInput("candidate_keyが重複しています")
        invalid_keys.add(key)
        if row["from"] not in state_map:
            raise InvalidInput("invalid candidate fromが不正です")
        invalid_candidates.append({"candidate_key": key, "from": row["from"], "event": ensure_nonempty_string(row["event"], "invalid event"), "authority_refs": _refs(row["authority_refs"], "invalid authority_refs")})
    invalid_candidates.sort(key=lambda row: row["candidate_key"])

    mode = input_value["coverage_mode"]
    if mode not in {"all-states", "valid-transitions", "n-switch", "round-trip", "invalid-transitions"}:
        raise InvalidInput("coverage_modeが不正です")
    switch_count = input_value.get("switch_count")
    reason = input_value.get("coverage_selection_reason")
    if mode == "n-switch":
        switch_count = ensure_int(switch_count, "switch_count", minimum=0, maximum=10)
        if switch_count >= 2 and (not isinstance(reason, str) or not reason.strip()):
            raise InvalidInput("n-switch>=2ではcoverage_selection_reasonが必要です")
    elif "switch_count" in input_value or "coverage_selection_reason" in input_value:
        raise InvalidInput("switch_count / coverage_selection_reasonはn-switchだけで使用します")

    reachable = set(initial_states)
    pending = list(initial_states)
    while pending:
        node = pending.pop(0)
        for edge in outgoing[node]:
            if edge["to"] not in reachable:
                reachable.add(edge["to"])
                pending.append(edge["to"])
    uncertain = [edge for edge in transitions if edge["guard_status"] is None and edge["from"] in reachable]
    issues: list[dict[str, Any]] = []
    if uncertain:
        issues.append({"issue_type": "uncertain_transition_guard", "blocking": True, "target_key": None, "authority_refs": sorted({ref for edge in uncertain for ref in set(edge["guard_refs"]) | set(edge["authority_refs"])})})

    def setup(target_state: str) -> dict[str, Any] | None:
        candidates: list[tuple[tuple[Any, ...], dict[str, Any]]] = []
        for initial in initial_states:
            path = _shortest_paths(initial, target_state, outgoing)
            if initial == target_state or path:
                candidates.append(((len(path), initial, 0, "", tuple(edge["transition_key"] for edge in path)), {"initial": initial, "reset": None, "path": path}))
            for reset in resets:
                if "*" not in reset["from_states"] and initial not in reset["from_states"]:
                    continue
                reset_path = _shortest_paths(reset["to_state"], target_state, outgoing)
                if reset["to_state"] == target_state or reset_path:
                    candidates.append(((len(reset_path), initial, 1, reset["reset_key"], tuple(edge["transition_key"] for edge in reset_path)), {"initial": initial, "reset": reset, "path": reset_path}))
        if not candidates:
            return None
        candidates.sort(key=lambda item: item[0])
        return candidates[0][1]

    def execution(start_state: str, coverage: list[dict[str, Any]], *, attempted: dict[str, Any] | None = None) -> dict[str, Any] | None:
        context = setup(start_state)
        if context is None:
            return None
        reset = context["reset"]
        return {
            "initial_state_key": context["initial"], "initial_state_label": state_map[context["initial"]]["label"],
            "reset_key": reset["reset_key"] if reset else None,
            "reset_execution": {"reset_key": reset["reset_key"], "action": reset["action"], "from_state_key": context["initial"], "to_state": {"state_key": reset["to_state"], "label": state_map[reset["to_state"]]["label"]}} if reset else None,
            "setup_prefix": [_edge_execution(edge, state_map) for edge in context["path"]],
            "coverage_sequence": [_edge_execution(edge, state_map) for edge in coverage],
            "attempted_transition": attempted,
        }

    target_specs: list[tuple[str, str, list[dict[str, Any]], dict[str, Any]]] = []
    if mode == "all-states":
        for key in state_keys:
            target_specs.append((f"state:node:{key}", key, [], {"target_state": key, "state_key": key}))
    elif mode == "valid-transitions":
        for edge in transitions:
            if edge["guard_status"] is True:
                target_specs.append((f"state:transition:{edge['transition_key']}", edge["from"], [edge], {"transition_key": edge["transition_key"]}))
    elif mode == "n-switch":
        sequences = _enumerate_sequences(state_keys, outgoing, switch_count + 1)
        for sequence in sequences:
            if not sequence:
                continue
            sequence_keys = [edge["transition_key"] for edge in sequence]
            target_specs.append((f"state:n-switch:{switch_count}:h" + _hash_component(sequence_keys), sequence[0]["from"], sequence, {"transition_key_sequence": sequence_keys}))
    elif mode == "round-trip":
        for start, cycle in _cycles(state_keys, outgoing):
            sequence_keys = [edge["transition_key"] for edge in cycle]
            target_specs.append((f"state:round-trip:{start}:h" + _hash_component(sequence_keys), start, cycle, {"start_state_key": start, "transition_key_sequence": sequence_keys}))
    else:
        for candidate in invalid_candidates:
            target_specs.append((f"state:invalid:{candidate['candidate_key']}", candidate["from"], [], {"candidate_key": candidate["candidate_key"], "attempted": {"candidate_key": candidate["candidate_key"], "from": {"state_key": candidate["from"], "label": state_map[candidate["from"]]["label"]}, "event": candidate["event"]}}))

    targets: list[dict[str, Any]] = []
    for target_key, start_state, coverage, info in target_specs:
        attempted = info.get("attempted")
        exec_value = execution(start_state, coverage, attempted=attempted)
        if exec_value is None:
            issues.append({"issue_type": "unreachable_required_item", "blocking": True, "target_key": target_key, "authority_refs": []})
        target_node = state_map[start_state]
        targets.append({"target_key": target_key, "coverage_mode": mode, "state_key": start_state, "target_node": {"state_key": target_node["state_key"], "label": target_node["label"]}, "materializable": exec_value is not None, "execution": exec_value, "authority_refs": target_node["authority_refs"]})
    targets = post_process_targets(metadata["model_key"], sorted(targets, key=lambda row: row["target_key"]))
    covered = sum(1 for row in targets if row["materializable"])
    return {
        "runtime_status": "ok", "support_status": "supported", "result_status": "ready" if not issues else "unresolved", "runtime_required": True, "deterministic_generated": True,
        "payload": {"states": states, "initial_states": initial_states, "terminal_states": terminal_states, "transitions": transitions, "reset_options": resets, "invalid_transition_candidates": invalid_candidates, "coverage_mode": mode, "switch_count": switch_count if mode == "n-switch" else None, "targets": targets, "uncertain_transitions": uncertain, "coverage_summary": {"criterion": mode, "required": len(targets), "covered": covered, "complete": bool(targets) and covered == len(targets) and not issues}},
        "issues": issues,
    }


if __name__ == "__main__":
    raise SystemExit(run_cli(generate, skill=SKILL, generator=GENERATOR, generator_contract_version=GENERATOR_CONTRACT_VERSION, generator_path=SCRIPT_PATH))
