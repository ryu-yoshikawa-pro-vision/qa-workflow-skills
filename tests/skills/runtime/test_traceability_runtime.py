from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import unittest

from importlib.util import module_from_spec, spec_from_file_location


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "skills" / "coverage-analysis" / "scripts" / "traceability.py"
RUNTIME_PATH = REPO_ROOT / "skills" / "coverage-analysis" / "scripts" / "runtime_contract.py"
SPEC = spec_from_file_location("coverage_runtime_contract", RUNTIME_PATH)
assert SPEC is not None and SPEC.loader is not None
runtime = module_from_spec(SPEC)
sys.modules[SPEC.name] = runtime
SPEC.loader.exec_module(runtime)


def metadata() -> dict:
    return {
        "envelope_version": "1", "skill": "coverage-analysis", "runtime_contract_version": "runtime-v1", "generator_contract_version": "traceability-v1",
        "runtime_unit_key": "artifact:traceability:all", "model_key": None, "model_type": None, "technique_slug": None, "selection_source": None, "selection_key": None,
        "scope_key": "all", "input_mode": "artifact", "upstream_entities": [], "upstream_runtime_units": [], "static_data_versions": {}, "authority_refs": [], "reference_refs": [],
    }


def runtime_row(skill: str, unit: str, model_key: str | None = None, *, materialize: bool = False, materialize_model_key: str | None = None, active_ci_ids: list[str] | None = None, materialize_complete: bool = True) -> dict:
    return {
        "skill": skill, "runtime_unit_key": unit, "model_key": model_key, "support_status": "supported", "result_status": "ready", "runtime_status": "ok",
        "runtime_required": True, "deterministic_generated": True, "generation_fingerprint": "sha256:" + (unit.encode().hex() * 64)[:64],
        "upstream_entity_fingerprints": [], "upstream_runtime_units": [], "unsupported_items": [], "freshness_status": "current",
        "model_completion": [{
            "model_key": materialize_model_key or model_key,
            "required_target_refs": [f"target:{materialize_model_key or model_key}"],
            "closed_target_refs": [f"target:{materialize_model_key or model_key}"],
            "active_ci_ids": sorted(active_ci_ids or []) if materialize else [],
            "semantic_item_keys": [],
            "materialize_complete": materialize_complete,
        }] if materialize else [], "target_mappings": [], "target_dispositions": [],
    }


def base_request() -> dict:
    tcn = runtime.make_machine_entity("test-condition-design", "tcn", "TCN-001", {"tcn_id": "TCN-001"})
    model = runtime.make_machine_entity("test-condition-design", "model", "ep-001", {"model_key": "ep-001", "model_type": "ep"}, model_key="ep-001")
    ci = runtime.make_machine_entity("test-condition-design", "ci", "TCN-001-CI01", {"ci_id": "TCN-001-CI01", "tcn_id": "TCN-001", "model_key": "ep-001"}, model_key="ep-001")
    units = [runtime_row("test-condition-design", "artifact:condition_structure:all"), runtime_row("test-condition-design", "model:ep-001", "ep-001"), runtime_row("test-condition-design", "artifact:materialize_coverage:TCN-001", materialize=True, materialize_model_key="ep-001", active_ci_ids=["TCN-001-CI01"])]
    return {
        "metadata": metadata(),
        "input": {
            "analysis_scopes": [{"skill": "test-condition-design", "target": None, "execution_range": None, "input_mode": "artifact", "normalized_input": {"tcn_id": "TCN-001", "test_conditions": [{"tcn_id": "TCN-001"}], "models": [{"model_key": "ep-001", "model_type": "ep"}], "ci_ids": ["TCN-001-CI01"]}, "current_structure_state": {"tcn_id": "TCN-001"}}],
            "nodes": [{"node_key": "SPEC-001", "node_type": "Authority"}, {"node_key": "TR-001", "node_type": "TR"}, {"node_key": "TCN-001", "node_type": "TCN"}, {"node_key": "TCN-001-CI01", "node_type": "CI"}, {"node_key": "TC-001", "node_type": "TC"}],
            "edges": [{"from": "SPEC-001", "to": "TR-001"}, {"from": "TR-001", "to": "TCN-001"}, {"from": "TCN-001", "to": "TCN-001-CI01"}, {"from": "TCN-001-CI01", "to": "TC-001"}],
            "dispositions": [], "runtime_units": units, "current_entities": [tcn, model, ci], "current_runtime_units": units, "unsupported_item_closures": [],
        },
    }


def run(request: dict) -> dict:
    result = subprocess.run([sys.executable, str(SCRIPT)], input=json.dumps(request).encode(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=REPO_ROOT, check=False)
    if result.stderr:
        raise AssertionError(result.stderr.decode())
    return json.loads(result.stdout)


class TraceabilityRuntimeTests(unittest.TestCase):
    def test_expected_sets_and_graph_are_complete(self) -> None:
        result = run(base_request())
        self.assertEqual(result["runtime_status"], "ok")
        self.assertEqual(result["result_status"], "ready")
        self.assertTrue(result["payload"]["can_complete"])
        self.assertEqual(result["payload"]["missing_runtime_units"], [])
        self.assertEqual(result["payload"]["missing_entities"], [])

    def test_missing_runtime_root_does_not_shrink_expected_set(self) -> None:
        request = base_request()
        request["input"]["runtime_units"] = request["input"]["runtime_units"][1:]
        result = run(request)
        self.assertEqual(result["runtime_status"], "ok")
        self.assertEqual(result["result_status"], "unresolved")
        self.assertIn(["test-condition-design", "artifact:condition_structure:all"], result["payload"]["missing_runtime_units"])
        self.assertIn("model:ep-001", [row["runtime_unit_key"] for row in result["payload"]["expected_runtime_units"]])

    def test_self_runtime_is_rejected(self) -> None:
        request = base_request()
        request["input"]["runtime_units"].append(runtime_row("coverage-analysis", "artifact:traceability:all"))
        result = run(request)
        self.assertEqual(result["runtime_status"], "invalid_input")

    def _multi_scope_request(self, *, scope_b_complete: bool = True) -> dict:
        entities = [
            runtime.make_machine_entity("test-condition-design", "tcn", "TCN-001", {"tcn_id": "TCN-001"}),
            runtime.make_machine_entity("test-condition-design", "tcn", "TCN-002", {"tcn_id": "TCN-002"}),
            runtime.make_machine_entity("test-condition-design", "model", "ep-001", {"model_key": "ep-001", "model_type": "ep"}, model_key="ep-001"),
            runtime.make_machine_entity("test-condition-design", "model", "ep-002", {"model_key": "ep-002", "model_type": "ep"}, model_key="ep-002"),
            runtime.make_machine_entity("test-condition-design", "ci", "TCN-001-CI01", {"ci_id": "TCN-001-CI01", "tcn_id": "TCN-001", "model_key": "ep-001"}, model_key="ep-001"),
            runtime.make_machine_entity("test-condition-design", "ci", "TCN-002-CI01", {"ci_id": "TCN-002-CI01", "tcn_id": "TCN-002", "model_key": "ep-002"}, model_key="ep-002"),
        ]
        normalized_a = {"tcn_id": "TCN-001", "test_conditions": [{"tcn_id": "TCN-001"}], "models": [{"model_key": "ep-001", "model_type": "ep"}], "ci_ids": ["TCN-001-CI01"]}
        normalized_b = {"tcn_id": "TCN-002", "test_conditions": [{"tcn_id": "TCN-002"}], "models": [{"model_key": "ep-002", "model_type": "ep"}], "ci_ids": ["TCN-002-CI01"]}
        units = [
            runtime_row("test-condition-design", "artifact:condition_structure:all"),
            runtime_row("test-condition-design", "model:ep-001", "ep-001"),
            runtime_row("test-condition-design", "model:ep-002", "ep-002"),
            runtime_row("test-condition-design", "artifact:materialize_coverage:TCN-001", materialize=True, materialize_model_key="ep-001", active_ci_ids=["TCN-001-CI01"]),
            runtime_row("test-condition-design", "artifact:materialize_coverage:TCN-002", materialize=True, materialize_model_key="ep-002", active_ci_ids=["TCN-002-CI01"], materialize_complete=scope_b_complete),
        ]
        return {
            "metadata": metadata(),
            "input": {
                "analysis_scopes": [
                    {"skill": "test-condition-design", "target": "TCN-001", "execution_range": None, "input_mode": "artifact", "normalized_input": normalized_a, "current_structure_state": {"tcn_id": "TCN-001"}},
                    {"skill": "test-condition-design", "target": "TCN-002", "execution_range": None, "input_mode": "artifact", "normalized_input": normalized_b, "current_structure_state": {"tcn_id": "TCN-002"}},
                ],
                "nodes": [
                    {"node_key": "SPEC-001", "node_type": "Authority"}, {"node_key": "TR-001", "node_type": "TR"}, {"node_key": "TR-002", "node_type": "TR"},
                    {"node_key": "TCN-001", "node_type": "TCN"}, {"node_key": "TCN-002", "node_type": "TCN"},
                    {"node_key": "TCN-001-CI01", "node_type": "CI"}, {"node_key": "TCN-002-CI01", "node_type": "CI"},
                    {"node_key": "TC-001", "node_type": "TC"}, {"node_key": "TC-002", "node_type": "TC"},
                ],
                "edges": [
                    {"from": "SPEC-001", "to": "TR-001"}, {"from": "SPEC-001", "to": "TR-002"},
                    {"from": "TR-001", "to": "TCN-001"}, {"from": "TR-002", "to": "TCN-002"},
                    {"from": "TCN-001", "to": "TCN-001-CI01"}, {"from": "TCN-002", "to": "TCN-002-CI01"},
                    {"from": "TCN-001-CI01", "to": "TC-001"}, {"from": "TCN-002-CI01", "to": "TC-002"},
                ],
                "dispositions": [], "runtime_units": units, "current_entities": entities, "current_runtime_units": units, "unsupported_item_closures": [],
            },
        }

    def test_two_complete_scopes_pass_independent_completion(self) -> None:
        result = run(self._multi_scope_request())
        self.assertEqual(result["runtime_status"], "ok")
        self.assertEqual(result["result_status"], "ready")
        self.assertTrue(result["payload"]["can_complete"], result)

    def test_one_incomplete_scope_remains_unresolved_despite_other_scope_ci(self) -> None:
        result = run(self._multi_scope_request(scope_b_complete=False))
        self.assertEqual(result["runtime_status"], "ok")
        self.assertEqual(result["result_status"], "unresolved")
        self.assertFalse(result["payload"]["can_complete"])
        self.assertTrue(any(issue["issue_type"] == "model_materialize_incomplete" and issue.get("model_key") == "ep-002" for issue in result["issues"]))


if __name__ == "__main__":
    unittest.main()
