"""Extract shortest deterministic impact paths from an explicit change graph."""

from __future__ import annotations

from collections import deque
from pathlib import Path
import sys

from runtime_contract import InvalidInput, canonicalize, ensure_list, ensure_nonempty_string, reject_unknown, run_cli


SKILL = "test-analysis"
GENERATOR = "change_impact"
GENERATOR_CONTRACT_VERSION = "change-impact-v1"
SCRIPT_PATH = Path(__file__).resolve()
NODE_TYPES = {"Authority", "Risk", "TR", "TCN", "CI", "TC"}
CHANGE_KINDS = {"新規", "変更", "削除", "回帰影響", "参考", None}
EDGE_TYPES = {"depends_on", "traces_to", "derived_from"}


def generate(input_value: dict, metadata: dict) -> dict:
    if metadata["runtime_unit_key"] != "artifact:change_impact:all":
        raise InvalidInput("change_impact runtime unitが不正です")
    reject_unknown(input_value, {"changed_node_keys", "nodes", "edges"})
    nodes = ensure_list(input_value["nodes"], "nodes")
    node_map = {}
    for index, row in enumerate(nodes):
        if not isinstance(row, dict):
            raise InvalidInput(f"nodes[{index}]が不正です")
        reject_unknown(row, {"node_key", "node_type", "source_ref", "change_kind", "expected_impact"})
        key = ensure_nonempty_string(row["node_key"], f"nodes[{index}].node_key")
        if key in node_map or row["node_type"] not in NODE_TYPES or row["change_kind"] not in CHANGE_KINDS or (row["expected_impact"] is not None and not isinstance(row["expected_impact"], str)):
            raise InvalidInput("change graph nodeが不正です")
        node_map[key] = canonicalize(row)
    changed = input_value["changed_node_keys"]
    if not isinstance(changed, list) or len(set(changed)) != len(changed) or any(key not in node_map for key in changed):
        raise InvalidInput("changed_node_keysが不正です")
    adjacency: dict[str, list[tuple[str, str]]] = {key: [] for key in node_map}
    edge_seen: set[str] = set()
    for index, row in enumerate(ensure_list(input_value["edges"], "edges")):
        if not isinstance(row, dict):
            raise InvalidInput(f"edges[{index}]が不正です")
        reject_unknown(row, {"edge_key", "from", "to", "edge_type", "evidence_refs"})
        edge_key = ensure_nonempty_string(row["edge_key"], f"edges[{index}].edge_key")
        if edge_key in edge_seen or row["from"] not in node_map or row["to"] not in node_map or row["edge_type"] not in EDGE_TYPES or not isinstance(row["evidence_refs"], list) or not all(isinstance(value, str) for value in row["evidence_refs"]):
            raise InvalidInput("change graph edgeが不正です")
        edge_seen.add(edge_key)
        # depends_on is defined as "from depends on to".  A change to the
        # dependency therefore propagates in the reverse direction, while
        # traces_to / derived_from already point from upstream to downstream.
        if row["edge_type"] == "depends_on":
            adjacency[row["to"]].append((row["from"], edge_key))
        else:
            adjacency[row["from"]].append((row["to"], edge_key))
    for key in adjacency:
        adjacency[key].sort(key=lambda row: (row[1], row[0]))
    paths = []
    impacted: set[str] = set()
    for start in sorted(changed):
        queue = deque([(start, [start], [])])
        best: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {}
        while queue:
            node, node_path, edge_path = queue.popleft()
            signature = (tuple(edge_path), tuple(node_path))
            previous = best.get(node)
            if previous is not None and (len(edge_path), signature) >= (len(previous[0]), previous):
                continue
            best[node] = signature
            impacted.add(node)
            paths.append({"target_node_key": node, "node_keys": node_path, "edge_keys": edge_path, "source_node_key": start})
            for target, edge_key in adjacency[node]:
                if target in node_path:
                    continue
                queue.append((target, node_path + [target], edge_path + [edge_key]))
    paths.sort(key=lambda row: (row["target_node_key"], row["edge_keys"], row["node_keys"], row["source_node_key"]))
    unique_paths = {}
    for path in paths:
        unique_paths.setdefault((path["source_node_key"], path["target_node_key"]), path)
    return {"runtime_status": "ok", "support_status": "supported", "result_status": "ready", "runtime_required": True, "deterministic_generated": True, "payload": {"impacted_nodes": [node_map[key] for key in sorted(impacted)], "paths": list(unique_paths.values())}, "issues": []}


if __name__ == "__main__":
    raise SystemExit(run_cli(generate, skill=SKILL, generator=GENERATOR, generator_contract_version=GENERATOR_CONTRACT_VERSION, generator_path=SCRIPT_PATH))
