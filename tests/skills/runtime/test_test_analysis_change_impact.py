from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import unittest


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "skills" / "test-analysis" / "scripts" / "change_impact.py"


def metadata() -> dict:
    return {
        "envelope_version": "1", "skill": "test-analysis", "runtime_contract_version": "runtime-v1", "generator_contract_version": "change-impact-v1",
        "runtime_unit_key": "artifact:change_impact:all", "model_key": None, "model_type": None, "technique_slug": None, "selection_source": None, "selection_key": None,
        "scope_key": "all", "input_mode": "direct", "upstream_entities": [], "upstream_runtime_units": [], "static_data_versions": {}, "authority_refs": [], "reference_refs": [],
    }


def run(value: dict) -> dict:
    result = subprocess.run([sys.executable, str(SCRIPT)], input=json.dumps({"metadata": metadata(), "input": value}, ensure_ascii=False).encode(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=REPO_ROOT, check=False)
    if result.stderr:
        raise AssertionError(result.stderr.decode())
    return json.loads(result.stdout)


def node(key: str, kind: str = "Risk") -> dict:
    return {"node_key": key, "node_type": kind, "source_ref": f"SPEC-{key}", "change_kind": "変更", "expected_impact": f"impact-{key}"}


class ChangeImpactRuntimeTests(unittest.TestCase):
    def test_depends_on_is_reversed_and_trace_is_forward(self) -> None:
        value = {
            "changed_node_keys": ["B"],
            "nodes": [node("A"), node("B"), node("C")],
            "edges": [
                {"edge_key": "depends", "from": "A", "to": "B", "edge_type": "depends_on", "evidence_refs": ["SPEC-1"]},
                {"edge_key": "trace", "from": "B", "to": "C", "edge_type": "traces_to", "evidence_refs": ["SPEC-2"]},
            ],
        }
        result = run(value)
        self.assertEqual(result["runtime_status"], "ok")
        self.assertEqual({row["node_key"] for row in result["payload"]["impacted_nodes"]}, {"A", "B", "C"})
        paths = {(row["source_node_key"], row["target_node_key"]): row["edge_keys"] for row in result["payload"]["paths"]}
        self.assertEqual(paths[("B", "A")], ["depends"])
        self.assertEqual(paths[("B", "C")], ["trace"])

    def test_dangling_edge_and_unknown_changed_node_are_invalid(self) -> None:
        base = {"changed_node_keys": ["A"], "nodes": [node("A")], "edges": []}
        bad_changed = dict(base, changed_node_keys=["X"])
        self.assertEqual(run(bad_changed)["runtime_status"], "invalid_input")
        bad_edge = dict(base, edges=[{"edge_key": "e", "from": "A", "to": "X", "edge_type": "traces_to", "evidence_refs": []}])
        self.assertEqual(run(bad_edge)["runtime_status"], "invalid_input")


if __name__ == "__main__":
    unittest.main()
