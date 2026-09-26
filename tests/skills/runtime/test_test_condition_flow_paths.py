from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import unittest


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "skills" / "test-condition-design" / "scripts" / "flow_paths.py"


def metadata() -> dict:
    return {
        "envelope_version": "1", "skill": "test-condition-design", "runtime_contract_version": "runtime-v1", "generator_contract_version": "flow-paths-v1",
        "runtime_unit_key": "model:flow-001", "model_key": "flow-001", "model_type": "flow", "technique_slug": "scenario", "selection_source": "condition_design", "selection_key": None,
        "scope_key": None, "input_mode": "direct", "upstream_entities": [], "upstream_runtime_units": [], "static_data_versions": {}, "authority_refs": [], "reference_refs": [],
    }


def run(value: dict) -> dict:
    result = subprocess.run([sys.executable, str(SCRIPT)], input=json.dumps({"metadata": metadata(), "input": value}, ensure_ascii=False).encode(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=REPO_ROOT, check=False)
    if result.stderr:
        raise AssertionError(result.stderr.decode())
    return json.loads(result.stdout)


def simple(mode="bounded-path"):
    return {
        "nodes": [{"node_key": "start", "label": "Start", "kind": "normal", "authority_refs": []}, {"node_key": "end", "label": "End", "kind": "terminal", "authority_refs": []}],
        "edges": [{"edge_key": "E-001", "from": "start", "to": "end", "guard_status": True, "guard_refs": [], "label": "finish", "authority_refs": []}],
        "initial_node_keys": ["start"], "regions": [], "loop_specs": [], "coverage_mode": mode, "max_path_length": 5,
    }


def partial_with_separate_supported_edge(*, uncertain: bool) -> dict:
    nodes = [
        {"node_key": "f", "label": "Fork", "kind": "fork", "authority_refs": []},
        {"node_key": "a", "label": "A", "kind": "normal", "authority_refs": []},
        {"node_key": "b", "label": "B", "kind": "normal", "authority_refs": []},
        {"node_key": "j", "label": "Join", "kind": "join", "authority_refs": []},
        {"node_key": "x", "label": "Other start", "kind": "normal", "authority_refs": []},
        {"node_key": "y", "label": "Other end", "kind": "terminal", "authority_refs": []},
        {"node_key": "z", "label": "Uncertain end", "kind": "terminal", "authority_refs": []},
    ]
    edges = [
        {"edge_key": "A-1", "from": "f", "to": "a", "guard_status": True, "guard_refs": [], "label": "A", "authority_refs": []},
        {"edge_key": "A-2", "from": "a", "to": "j", "guard_status": True, "guard_refs": [], "label": "A join", "authority_refs": []},
        {"edge_key": "B-1", "from": "f", "to": "b", "guard_status": True, "guard_refs": [], "label": "B", "authority_refs": []},
        {"edge_key": "B-2", "from": "b", "to": "j", "guard_status": True, "guard_refs": [], "label": "B join", "authority_refs": []},
        {"edge_key": "X-1", "from": "x", "to": "y", "guard_status": True, "guard_refs": [], "label": "Supported", "authority_refs": []},
    ]
    if uncertain:
        edges.append({"edge_key": "X-2", "from": "x", "to": "z", "guard_status": None, "guard_refs": ["SPEC-001"], "label": "Unknown", "authority_refs": []})
    return {
        "nodes": nodes, "edges": edges, "initial_node_keys": ["f", "x"],
        "regions": [{"region_key": "RG-001", "fork_node_key": "f", "join_node_key": "j", "branches": [{"branch_key": "BR-A", "edge_keys": ["A-1", "A-2"]}, {"branch_key": "BR-B", "edge_keys": ["B-1", "B-2"]}]}],
        "loop_specs": [], "coverage_mode": "edge", "max_path_length": 10,
    }


class FlowPathsRuntimeTests(unittest.TestCase):
    def test_bounded_path_and_node_execution_contains_labels(self) -> None:
        result = run(simple())
        self.assertEqual(result["runtime_status"], "ok")
        self.assertTrue(result["payload"]["coverage_summary"]["complete"])
        self.assertEqual(result["payload"]["targets"][0]["execution"]["edge_sequence"][0]["label"], "finish")
        node = run({**simple("node")})
        self.assertEqual(node["runtime_status"], "ok")
        self.assertEqual(len(node["payload"]["targets"]), 2)

    def test_simple_loop_has_zero_one_typical_and_maximum_targets(self) -> None:
        value = {
            "nodes": [{"node_key": "n1", "label": "Loop entry", "kind": "normal", "authority_refs": []}, {"node_key": "n2", "label": "Loop body", "kind": "normal", "authority_refs": []}, {"node_key": "done", "label": "Done", "kind": "terminal", "authority_refs": []}],
            "edges": [
                {"edge_key": "L-001", "from": "n1", "to": "n2", "guard_status": True, "guard_refs": [], "label": "enter", "authority_refs": []},
                {"edge_key": "L-002", "from": "n2", "to": "n1", "guard_status": True, "guard_refs": [], "label": "repeat", "authority_refs": []},
                {"edge_key": "X-001", "from": "n1", "to": "done", "guard_status": True, "guard_refs": [], "label": "exit", "authority_refs": []},
            ],
            "initial_node_keys": ["n1"], "regions": [], "loop_specs": [{"loop_key": "LP-001", "entry_node_key": "n1", "edge_keys": ["L-001", "L-002"], "exit_edge_keys": ["X-001"], "typical_iterations": 2, "maximum_iterations": 4, "authority_refs": []}], "coverage_mode": "simple-loop", "max_path_length": 10,
        }
        result = run(value)
        self.assertEqual(result["runtime_status"], "ok")
        self.assertEqual({row["target_key"] for row in result["payload"]["targets"]}, {"flow:loop:LP-001:0", "flow:loop:LP-001:1", "flow:loop:LP-001:2", "flow:loop:LP-001:4"})
        zero = next(row for row in result["payload"]["targets"] if row["target_key"].endswith(":0"))
        self.assertEqual(zero["execution"]["edge_sequence"][0]["edge_key"], "X-001")

    def test_fork_join_is_semantic_unsupported_and_not_linearized(self) -> None:
        value = {
            "nodes": [{"node_key": "f", "label": "Fork", "kind": "fork", "authority_refs": []}, {"node_key": "a", "label": "A", "kind": "normal", "authority_refs": []}, {"node_key": "b", "label": "B", "kind": "normal", "authority_refs": []}, {"node_key": "j", "label": "Join", "kind": "join", "authority_refs": []}],
            "edges": [
                {"edge_key": "A-1", "from": "f", "to": "a", "guard_status": True, "guard_refs": [], "label": "A", "authority_refs": []}, {"edge_key": "A-2", "from": "a", "to": "j", "guard_status": True, "guard_refs": [], "label": "A join", "authority_refs": []},
                {"edge_key": "B-1", "from": "f", "to": "b", "guard_status": True, "guard_refs": [], "label": "B", "authority_refs": []}, {"edge_key": "B-2", "from": "b", "to": "j", "guard_status": True, "guard_refs": [], "label": "B join", "authority_refs": []},
            ],
            "initial_node_keys": ["f"], "regions": [{"region_key": "RG-001", "fork_node_key": "f", "join_node_key": "j", "branches": [{"branch_key": "BR-A", "edge_keys": ["A-1", "A-2"]}, {"branch_key": "BR-B", "edge_keys": ["B-1", "B-2"]}]}], "loop_specs": [], "coverage_mode": "fork-join", "max_path_length": 10,
        }
        result = run(value)
        self.assertEqual(result["runtime_status"], "unsupported")
        self.assertEqual(result["support_status"], "unsupported")
        self.assertTrue(result["payload"]["unsupported_items"])
        self.assertTrue(all(not row["materializable"] for row in result["payload"]["targets"]))

    def test_whole_model_unsupported_fallback_does_not_create_unhashed_item_key(self) -> None:
        value = {
            "nodes": [
                {"node_key": "f", "label": "Fork", "kind": "fork", "authority_refs": []},
                {"node_key": "a", "label": "Nested fork", "kind": "fork", "authority_refs": []},
                {"node_key": "j1", "label": "Join 1", "kind": "join", "authority_refs": []},
                {"node_key": "j2", "label": "Join 2", "kind": "join", "authority_refs": []},
            ],
            "edges": [
                {"edge_key": "E-1", "from": "f", "to": "a", "guard_status": True, "guard_refs": [], "label": "enter", "authority_refs": []},
                {"edge_key": "E-2", "from": "a", "to": "j1", "guard_status": True, "guard_refs": [], "label": "left", "authority_refs": []},
                {"edge_key": "E-3", "from": "j1", "to": "j2", "guard_status": True, "guard_refs": [], "label": "continue", "authority_refs": []},
            ],
            "initial_node_keys": ["f"],
            "regions": [
                {"region_key": "RG-1", "fork_node_key": "f", "join_node_key": "j1", "branches": [{"branch_key": "BR-1", "edge_keys": ["E-1", "E-2"]}]},
                {"region_key": "RG-2", "fork_node_key": "a", "join_node_key": "j2", "branches": [{"branch_key": "BR-2", "edge_keys": ["E-2", "E-3"]}]},
            ],
            "loop_specs": [], "coverage_mode": "fork-join", "max_path_length": 10,
        }
        result = run(value)
        self.assertEqual(result["runtime_status"], "unsupported")
        self.assertEqual(result["payload"]["unsupported_items"], [])

    def test_partial_with_only_unsupported_items_can_be_ready(self) -> None:
        result = run(partial_with_separate_supported_edge(uncertain=False))
        self.assertEqual(result["support_status"], "partial")
        self.assertEqual(result["result_status"], "ready")
        self.assertTrue(result["payload"]["unsupported_items"])

    def test_partial_with_blocking_uncertain_guard_is_unresolved(self) -> None:
        result = run(partial_with_separate_supported_edge(uncertain=True))
        self.assertEqual(result["runtime_status"], "ok")
        self.assertEqual(result["support_status"], "partial")
        self.assertEqual(result["result_status"], "unresolved")
        self.assertTrue(any(issue["issue_type"] == "uncertain_edge_guard" and issue["blocking"] for issue in result["issues"]))


if __name__ == "__main__":
    unittest.main()
