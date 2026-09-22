from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "skills" / "qa-workflow" / "scripts" / "workflow_runtime.py"
RUNTIME_PATH = REPO_ROOT / "skills" / "qa-workflow" / "scripts" / "runtime_contract.py"
SPEC = importlib.util.spec_from_file_location("qa_workflow_runtime_contract", RUNTIME_PATH)
assert SPEC is not None and SPEC.loader is not None
runtime = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = runtime
SPEC.loader.exec_module(runtime)


def metadata() -> dict:
    return {
        "envelope_version": "1", "skill": "qa-workflow", "runtime_contract_version": "runtime-v1",
        "generator_contract_version": "workflow-runtime-v1", "runtime_unit_key": "artifact:workflow_runtime:all", "model_key": None,
        "model_type": None, "technique_slug": None, "selection_source": None, "selection_key": None, "scope_key": "all",
        "input_mode": "artifact", "upstream_entities": [], "upstream_runtime_units": [], "static_data_versions": {},
        "authority_refs": [], "reference_refs": [],
    }


def runtime_row(skill: str, unit: str, model_key: str | None = None, *, materialize: bool = False, active_ci_ids: list[str] | None = None, materialize_model_key: str | None = None) -> dict:
    return {
        "skill": skill, "runtime_unit_key": unit, "model_key": model_key, "support_status": "supported", "result_status": "ready",
        "runtime_status": "ok", "runtime_required": True, "deterministic_generated": True, "generation_fingerprint": f"sha256:{unit.encode().hex()[:64].ljust(64, '0')}",
        "upstream_entity_fingerprints": [], "upstream_runtime_units": [], "unsupported_items": [], "freshness_status": "current",
        "model_completion": [{
            "model_key": materialize_model_key or model_key,
            "required_target_refs": [f"target:{materialize_model_key or model_key}"],
            "closed_target_refs": [f"target:{materialize_model_key or model_key}"],
            "active_ci_ids": sorted(active_ci_ids or []),
            "semantic_item_keys": [],
            "materialize_complete": True,
        }] if materialize else [],
        "target_mappings": [], "target_dispositions": [],
    }


def run(request: dict) -> dict:
    result = subprocess.run([sys.executable, str(SCRIPT)], input=json.dumps(request).encode(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=REPO_ROOT, check=False)
    if result.stderr:
        raise AssertionError(result.stderr.decode())
    return json.loads(result.stdout)


class WorkflowRuntimeTests(unittest.TestCase):
    def _request(self) -> dict:
        tcn = runtime.make_machine_entity("test-condition-design", "tcn", "TCN-001", {"tcn_id": "TCN-001"})
        model = runtime.make_machine_entity("test-condition-design", "model", "ep-001", {"model_key": "ep-001", "model_type": "ep"}, model_key="ep-001")
        ci_one = runtime.make_machine_entity("test-condition-design", "ci", "TCN-001-CI01", {"ci_id": "TCN-001-CI01", "tcn_id": "TCN-001", "model_key": "ep-001"}, model_key="ep-001")
        ci_two = runtime.make_machine_entity("test-condition-design", "ci", "TCN-001-CI02", {"ci_id": "TCN-001-CI02", "tcn_id": "TCN-001", "model_key": "ep-001"}, model_key="ep-001")
        authority = runtime.make_machine_entity("spec-analysis", "authority", "SPEC-001", {"authority_id": "SPEC-001"})
        units = [
            runtime_row("test-condition-design", "artifact:condition_structure:all"),
            runtime_row("test-condition-design", "model:ep-001", "ep-001"),
            runtime_row("test-condition-design", "artifact:materialize_coverage:TCN-001", materialize=True, active_ci_ids=["TCN-001-CI01", "TCN-001-CI02"], materialize_model_key="ep-001"),
        ]
        normalized = {
            "tcn_id": "TCN-001", "test_conditions": [{"tcn_id": "TCN-001"}],
            "models": [{"model_key": "ep-001", "model_type": "ep"}], "ci_ids": ["TCN-001-CI01", "TCN-001-CI02"],
            "upstream_entities": [{"skill": "spec-analysis", "entity_type": "authority", "entity_ref": "SPEC-001"}],
        }
        return {
            "metadata": metadata(),
            "input": {
                "workflow_scopes": [{"skill": "test-condition-design", "target": None, "execution_range": None, "input_mode": "artifact", "normalized_input": normalized, "current_structure_state": {"tcn_id": "TCN-001"}}],
                "runtime_units": units, "current_entities": [tcn, model, ci_one, ci_two, authority], "current_runtime_units": units,
                "unsupported_item_closures": [],
            },
        }

    def test_expected_runtime_and_entity_sets_are_derived_and_complete(self) -> None:
        result = run(self._request())
        self.assertEqual(result["runtime_status"], "ok")
        self.assertEqual(result["result_status"], "ready")
        self.assertTrue(result["payload"]["can_complete"])
        self.assertEqual(result["issues"], [])
        self.assertEqual(len(result["payload"]["expected_runtime_units"]), 3)
        self.assertEqual(len(result["payload"]["expected_entities"]), 5)

    def test_missing_root_is_a_blocker_and_does_not_hide_other_expected_units(self) -> None:
        request = self._request()
        request["input"]["runtime_units"] = request["input"]["runtime_units"][1:]
        result = run(request)
        self.assertEqual(result["result_status"], "unresolved")
        self.assertFalse(result["payload"]["can_complete"])
        self.assertIn(["test-condition-design", "artifact:condition_structure:all"], result["payload"]["missing_runtime_units"])
        self.assertIn("model:ep-001", [row["runtime_unit_key"] for row in result["payload"]["expected_runtime_units"]])

    def test_changed_entity_fingerprint_propagates_stale_to_runtime_completion(self) -> None:
        request = self._request()
        request["input"]["runtime_units"][1]["upstream_entity_fingerprints"] = [{
            "skill": "spec-analysis", "entity_type": "authority", "entity_ref": "SPEC-001", "content_fingerprint": "sha256:" + "0" * 64,
        }]
        request["input"]["current_runtime_units"] = request["input"]["runtime_units"]
        result = run(request)
        self.assertEqual(result["result_status"], "unresolved")
        self.assertFalse(result["payload"]["can_complete"])
        self.assertTrue(any(issue["issue_type"] == "stale_entity_dependency" for issue in result["issues"]))


if __name__ == "__main__":
    unittest.main()
