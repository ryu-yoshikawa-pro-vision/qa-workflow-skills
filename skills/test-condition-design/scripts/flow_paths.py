"""Generate deterministic flow paths, loops, and explicit concurrency fallbacks."""

from __future__ import annotations

import hashlib
import heapq
from pathlib import Path
from typing import Any

from runtime_contract import (
    InvalidInput,
    LimitExceeded,
    MAX_EXPLORATION_NODES,
    UnsupportedInput,
    canonical_json_bytes,
    canonicalize,
    ensure_int,
    ensure_key,
    ensure_list,
    ensure_nonempty_string,
    make_unsupported_item,
    post_process_targets,
    reject_unknown,
    run_cli,
)


SKILL = "test-condition-design"
GENERATOR = "flow_paths"
GENERATOR_CONTRACT_VERSION = "flow-paths-v1"
SCRIPT_PATH = Path(__file__).resolve()


def _refs(value: Any, name: str) -> list[str]:
    if not isinstance(value, list) or len(set(value)) != len(value) or not all(isinstance(item, str) and item for item in value):
        raise InvalidInput(f"{name}が不正です")
    return sorted(value)


def _hash_component(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(canonicalize(value))).hexdigest()


def _edge_exec(edge: dict[str, Any], node_map: dict[str, dict[str, Any]]) -> dict[str, Any]:
    return {"edge_key": edge["edge_key"], "from": {"node_key": edge["from"], "label": node_map[edge["from"]]["label"]}, "label": edge["label"], "to": {"node_key": edge["to"], "label": node_map[edge["to"]]["label"]}}


def _shortest(start: str, target: str, outgoing: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]] | None:
    queue: list[tuple[int, tuple[str, ...], str, list[dict[str, Any]]]] = [(0, (), start, [])]
    best: dict[str, tuple[int, tuple[str, ...]]] = {start: (0, ())}
    while queue:
        length, sequence, node, path = heapq.heappop(queue)
        if node == target:
            return path
        visited = {edge["from"] for edge in path} | {node}
        for edge in outgoing.get(node, []):
            if edge["to"] in visited:
                continue
            next_sequence = sequence + (edge["edge_key"],)
            score = (length + 1, next_sequence)
            if edge["to"] in best and score >= best[edge["to"]]:
                continue
            best[edge["to"]] = score
            heapq.heappush(queue, (length + 1, next_sequence, edge["to"], path + [edge]))
    return None


def _all_terminal_paths(initial_nodes: list[str], terminal_nodes: set[str], outgoing: dict[str, list[dict[str, Any]]], max_length: int) -> list[list[dict[str, Any]]]:
    paths: list[list[dict[str, Any]]] = []
    explored = 0

    def walk(node: str, path: list[dict[str, Any]]) -> None:
        nonlocal explored
        explored += 1
        if explored > MAX_EXPLORATION_NODES:
            raise LimitExceeded("bounded-path exploration nodeがhard limitを超えています")
        if node in terminal_nodes:
            paths.append(list(path))
            return
        if len(path) >= max_length:
            return
        for edge in outgoing.get(node, []):
            walk(edge["to"], path + [edge])

    for initial in initial_nodes:
        walk(initial, [])
    paths.sort(key=lambda path: tuple(edge["edge_key"] for edge in path))
    return paths


def generate(input_value: dict, metadata: dict) -> dict:
    if metadata["model_key"] is None or metadata["model_type"] != "flow" or metadata["runtime_unit_key"] != f"model:{metadata['model_key']}":
        raise InvalidInput("flow pathsのruntime metadataが不正です")
    reject_unknown(input_value, {"nodes", "edges", "initial_node_keys", "regions", "loop_specs", "coverage_mode", "max_path_length"})
    nodes_raw = ensure_list(input_value["nodes"], "nodes")
    node_map: dict[str, dict[str, Any]] = {}
    nodes: list[dict[str, Any]] = []
    for index, row in enumerate(nodes_raw):
        if not isinstance(row, dict):
            raise InvalidInput(f"nodes[{index}]が不正です")
        reject_unknown(row, {"node_key", "label", "kind", "authority_refs"})
        key = ensure_key(row["node_key"], "node_key")
        if key in node_map:
            raise InvalidInput("node_keyが重複しています")
        if row["kind"] not in {"normal", "fork", "join", "terminal"}:
            raise InvalidInput("node kindが不正です")
        normalized = {"node_key": key, "label": ensure_nonempty_string(row["label"], "node label"), "kind": row["kind"], "authority_refs": _refs(row["authority_refs"], "node authority_refs")}
        node_map[key] = normalized
        nodes.append(normalized)
    nodes.sort(key=lambda row: row["node_key"])
    node_keys = [row["node_key"] for row in nodes]

    edges_raw = ensure_list(input_value["edges"], "edges")
    edge_map: dict[str, dict[str, Any]] = {}
    edges: list[dict[str, Any]] = []
    for index, row in enumerate(edges_raw):
        if not isinstance(row, dict):
            raise InvalidInput(f"edges[{index}]が不正です")
        reject_unknown(row, {"edge_key", "from", "to", "guard_status", "guard_refs", "label", "authority_refs"})
        key = ensure_key(row["edge_key"], "edge_key")
        if key in edge_map or row["from"] not in node_map or row["to"] not in node_map or row["guard_status"] not in {True, False, None}:
            raise InvalidInput("edge identity/reference/statusが不正です")
        guard_refs = _refs(row["guard_refs"], "edge guard_refs")
        if row["guard_status"] is False and not guard_refs:
            raise InvalidInput("guard_status=falseにはguard_refsが必要です")
        normalized = {"edge_key": key, "from": row["from"], "to": row["to"], "guard_status": row["guard_status"], "guard_refs": guard_refs, "label": ensure_nonempty_string(row["label"], "edge label"), "authority_refs": _refs(row["authority_refs"], "edge authority_refs")}
        edge_map[key] = normalized
        edges.append(normalized)
    edges.sort(key=lambda row: row["edge_key"])
    outgoing = {key: [] for key in node_keys}
    for edge in edges:
        if edge["guard_status"] is True:
            outgoing[edge["from"]].append(edge)
    for key in outgoing:
        outgoing[key].sort(key=lambda row: row["edge_key"])

    initial_nodes = ensure_list(input_value["initial_node_keys"], "initial_node_keys")
    if not initial_nodes or len(set(initial_nodes)) != len(initial_nodes) or any(key not in node_map for key in initial_nodes):
        raise InvalidInput("initial_node_keysが不正です")
    initial_nodes = sorted(initial_nodes)
    regions_raw = ensure_list(input_value["regions"], "regions")
    regions: list[dict[str, Any]] = []
    region_edge_sets: dict[str, set[str]] = {}
    region_keys: set[str] = set()
    for index, row in enumerate(regions_raw):
        if not isinstance(row, dict):
            raise InvalidInput(f"regions[{index}]が不正です")
        reject_unknown(row, {"region_key", "fork_node_key", "join_node_key", "branches"})
        region_key = ensure_key(row["region_key"], "region_key")
        if region_key in region_keys or row["fork_node_key"] not in node_map or row["join_node_key"] not in node_map or node_map[row["fork_node_key"]]["kind"] != "fork" or node_map[row["join_node_key"]]["kind"] != "join":
            raise InvalidInput("region identity/referenceが不正です")
        branch_rows = ensure_list(row["branches"], "region.branches")
        if not branch_rows:
            raise InvalidInput("region.branchesは1件以上必要です")
        branches: list[dict[str, Any]] = []
        branch_keys: set[str] = set()
        all_edges: set[str] = set()
        for branch in branch_rows:
            if not isinstance(branch, dict):
                raise InvalidInput("region branchが不正です")
            reject_unknown(branch, {"branch_key", "edge_keys"})
            branch_key = ensure_key(branch["branch_key"], "branch_key")
            if branch_key in branch_keys:
                raise InvalidInput("branch_keyが重複しています")
            branch_keys.add(branch_key)
            edge_keys = ensure_list(branch["edge_keys"], "branch.edge_keys")
            if not edge_keys or len(set(edge_keys)) != len(edge_keys) or any(key not in edge_map for key in edge_keys):
                raise InvalidInput("branch.edge_keysが不正です")
            branch_edges = [edge_map[key] for key in edge_keys]
            if branch_edges[0]["from"] != row["fork_node_key"] or branch_edges[-1]["to"] != row["join_node_key"] or any(left["to"] != right["from"] for left, right in zip(branch_edges, branch_edges[1:])) or any(edge["guard_status"] is not True for edge in branch_edges):
                raise InvalidInput("branch edge pathがforkからjoinまで連続していません")
            all_edges.update(edge_keys)
            branches.append({"branch_key": branch_key, "edge_keys": edge_keys})
        branches.sort(key=lambda item: item["branch_key"])
        regions.append({"region_key": region_key, "fork_node_key": row["fork_node_key"], "join_node_key": row["join_node_key"], "branches": branches})
        region_edge_sets[region_key] = all_edges
        region_keys.add(region_key)
    regions.sort(key=lambda row: row["region_key"])
    for index, left in enumerate(regions):
        for right in regions[index + 1:]:
            left_edges = region_edge_sets[left["region_key"]]
            right_edges = region_edge_sets[right["region_key"]]
            if left_edges & right_edges and not (left_edges <= right_edges or right_edges <= left_edges):
                # Crossing regions cannot be represented by the explicit
                # branch witness contract.  Keep this a whole-model
                # unsupported result; do not linearize only one side.
                raise UnsupportedInput(
                    "crossing regionはruntime-v1でunsupportedです",
                    item_key="unsupported:flow:crossing-region",
                    reason_code="crossing_concurrency_region",
                    affected_technique_slug="scenario",
                )

    loops_raw = ensure_list(input_value["loop_specs"], "loop_specs")
    loops: list[dict[str, Any]] = []
    loop_keys: set[str] = set()
    for index, row in enumerate(loops_raw):
        if not isinstance(row, dict):
            raise InvalidInput(f"loop_specs[{index}]が不正です")
        reject_unknown(row, {"loop_key", "entry_node_key", "edge_keys", "exit_edge_keys", "typical_iterations", "maximum_iterations", "authority_refs"})
        loop_key = ensure_key(row["loop_key"], "loop_key")
        if loop_key in loop_keys or row["entry_node_key"] not in node_map:
            raise InvalidInput("loop identityが不正です")
        loop_keys.add(loop_key)
        edge_keys = ensure_list(row["edge_keys"], "loop.edge_keys")
        exit_keys = ensure_list(row["exit_edge_keys"], "loop.exit_edge_keys")
        if not edge_keys or not exit_keys or len(set(edge_keys)) != len(edge_keys) or len(set(exit_keys)) != len(exit_keys) or any(key not in edge_map for key in edge_keys + exit_keys):
            raise InvalidInput("loop edge keysが不正です")
        cycle = [edge_map[key] for key in edge_keys]
        if cycle[0]["from"] != row["entry_node_key"] or cycle[-1]["to"] != row["entry_node_key"] or any(left["to"] != right["from"] for left, right in zip(cycle, cycle[1:])) or any(edge["guard_status"] is not True for edge in cycle) or len({edge["from"] for edge in cycle}) != len(cycle):
            raise InvalidInput("loop edge_keysがsimple cycleではありません")
        exits = [edge_map[key] for key in exit_keys]
        if any(edge["from"] != row["entry_node_key"] or edge["guard_status"] is not True or edge["edge_key"] == edge_keys[0] for edge in exits):
            raise InvalidInput("loop exit edgeが不正です")
        typical = ensure_int(row["typical_iterations"], "typical_iterations", minimum=2)
        maximum = row["maximum_iterations"]
        if maximum is not None:
            maximum = ensure_int(maximum, "maximum_iterations", minimum=typical)
        loops.append({"loop_key": loop_key, "entry_node_key": row["entry_node_key"], "edge_keys": edge_keys, "exit_edge_keys": sorted(exit_keys), "typical_iterations": typical, "maximum_iterations": maximum, "authority_refs": _refs(row["authority_refs"], "loop authority_refs")})
    loops.sort(key=lambda row: row["loop_key"])

    mode = input_value["coverage_mode"]
    if mode not in {"node", "edge", "bounded-path", "simple-loop", "fork-join"}:
        raise InvalidInput("flow coverage_modeが不正です")
    max_path_length = ensure_int(input_value["max_path_length"], "max_path_length", minimum=1, maximum=1000)
    reachable = set(initial_nodes)
    queue = list(initial_nodes)
    while queue:
        node = queue.pop(0)
        for edge in outgoing[node]:
            if edge["to"] not in reachable:
                reachable.add(edge["to"])
                queue.append(edge["to"])
    uncertain = [edge for edge in edges if edge["guard_status"] is None and edge["from"] in reachable]
    issues: list[dict[str, Any]] = []
    if uncertain:
        issues.append({"issue_type": "uncertain_edge_guard", "blocking": True, "target_key": None, "authority_refs": sorted({ref for edge in uncertain for ref in set(edge["guard_refs"]) | set(edge["authority_refs"])})})

    def prefix(target: str) -> tuple[str, list[dict[str, Any]]] | None:
        candidates: list[tuple[tuple[Any, ...], str, list[dict[str, Any]]]] = []
        for initial in initial_nodes:
            path = _shortest(initial, target, outgoing)
            if path is not None:
                candidates.append(((len(path), initial, tuple(edge["edge_key"] for edge in path)), initial, path))
        if not candidates:
            return None
        candidates.sort(key=lambda item: item[0])
        return candidates[0][1], candidates[0][2]

    target_specs: list[dict[str, Any]] = []
    if mode == "node":
        for key in sorted(reachable):
            target_specs.append({"target_key": f"flow:node:{key}", "start": key, "coverage": [], "target_node": key})
    elif mode == "edge":
        for edge in edges:
            if edge["guard_status"] is True and edge["from"] in reachable:
                target_specs.append({"target_key": f"flow:edge:{edge['edge_key']}", "start": edge["from"], "coverage": [edge], "target_node": edge["to"]})
    elif mode == "bounded-path":
        for path in _all_terminal_paths(initial_nodes, {key for key in node_keys if node_map[key]["kind"] == "terminal"}, outgoing, max_path_length):
            sequence = [edge["edge_key"] for edge in path]
            target_specs.append({"target_key": "flow:path:h" + _hash_component(sequence), "start": path[0]["from"] if path else next(initial for initial in initial_nodes if initial in {key for key in node_keys if node_map[key]["kind"] == "terminal"}), "coverage": path, "target_node": path[-1]["to"] if path else next(initial for initial in initial_nodes if initial in {key for key in node_keys if node_map[key]["kind"] == "terminal"})})
    elif mode == "simple-loop":
        for loop in loops:
            cycle = [edge_map[key] for key in loop["edge_keys"]]
            exit_edge = edge_map[sorted(loop["exit_edge_keys"])[0]]
            iterations = [0, 1, loop["typical_iterations"]]
            if loop["maximum_iterations"] is not None:
                iterations.append(loop["maximum_iterations"])
            for count in sorted(set(iterations)):
                coverage = cycle * count + [exit_edge]
                target_specs.append({"target_key": f"flow:loop:{loop['loop_key']}:{count}", "start": loop["entry_node_key"], "coverage": coverage, "target_node": exit_edge["to"], "loop_key": loop["loop_key"], "iterations": count})
    else:
        for region in regions:
            for branch in region["branches"]:
                target_specs.append({"target_key": f"flow:branch:{region['region_key']}:{branch['branch_key']}", "start": region["fork_node_key"], "coverage": [edge_map[key] for key in branch["edge_keys"]], "target_node": region["join_node_key"], "region_key": region["region_key"], "branch_key": branch["branch_key"]})

    unsupported_items: list[dict[str, Any]] = []
    targets: list[dict[str, Any]] = []
    region_edges = set().union(*region_edge_sets.values()) if region_edge_sets else set()
    for spec in sorted(target_specs, key=lambda row: row["target_key"]):
        if mode == "fork-join":
            target_execution = None
            unsupported_items.append(make_unsupported_item(generator=GENERATOR, item_type="concurrent-flow-target", source_key=spec["target_key"], reason_code="concurrent_flow_requires_semantic_execution", affected_technique_slug=None))
        else:
            pre = prefix(spec["start"])
            if pre is None:
                target_execution = None
                issues.append({"issue_type": "unreachable_required_item", "blocking": True, "target_key": spec["target_key"], "authority_refs": []})
            else:
                initial, setup_path = pre
                all_edges = setup_path + spec["coverage"]
                target_execution = {"initial_node_key": initial, "initial_node_label": node_map[initial]["label"], "target_node": {"node_key": spec["target_node"], "label": node_map[spec["target_node"]]["label"]}, "edge_sequence": [_edge_exec(edge, node_map) for edge in all_edges]}
                if region_edges and any(edge["edge_key"] in region_edges for edge in all_edges):
                    target_execution = None
                    unsupported_items.append(make_unsupported_item(generator=GENERATOR, item_type="concurrent-flow-target", source_key=spec["target_key"], reason_code="concurrent_flow_requires_semantic_execution", affected_technique_slug=None))
        targets.append({**{key: value for key, value in spec.items() if key not in {"start", "coverage", "target_node"}}, "target_key": spec["target_key"], "materializable": target_execution is not None, "execution": target_execution, "authority_refs": node_map[spec["start"]]["authority_refs"]})
    targets = post_process_targets(metadata["model_key"], targets)
    supported_targets = sum(1 for target in targets if target["materializable"])
    all_concurrency_unsupported = bool(targets) and not supported_targets and bool(unsupported_items)
    partial = bool(unsupported_items) and supported_targets > 0
    runtime_status = "unsupported" if all_concurrency_unsupported else "ok"
    support_status = "unsupported" if all_concurrency_unsupported else ("partial" if partial else "supported")
    has_blocking_issue = any(issue.get("blocking") is True for issue in issues)
    result_status = "unresolved" if has_blocking_issue else "ready"
    return {
        "runtime_status": runtime_status, "support_status": support_status, "result_status": result_status, "runtime_required": not all_concurrency_unsupported, "deterministic_generated": not all_concurrency_unsupported,
        "payload": {"nodes": nodes, "edges": edges, "initial_node_keys": initial_nodes, "regions": regions, "loop_specs": loops, "coverage_mode": mode, "max_path_length": max_path_length, "targets": targets, "unsupported_items": unsupported_items, "uncertain_edges": uncertain, "coverage_summary": {"criterion": mode, "required": supported_targets if partial else len(targets), "covered": supported_targets, "complete": (all_concurrency_unsupported or partial or (bool(targets) and supported_targets == len(targets) and not issues))}},
        "issues": issues,
    }


if __name__ == "__main__":
    raise SystemExit(run_cli(generate, skill=SKILL, generator=GENERATOR, generator_contract_version=GENERATOR_CONTRACT_VERSION, generator_path=SCRIPT_PATH))
