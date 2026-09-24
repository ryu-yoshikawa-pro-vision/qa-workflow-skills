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


def runtime_row(skill: str, unit: str, model_key: str | None = None, *, materialize: bool = False, active_ci_ids: list[str] | None = None, materialize_model_key: str | None = None, materialize_complete: bool = True) -> dict:
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
            "materialize_complete": materialize_complete,
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
                "workflow_scopes": [{"skill": "test-condition-design", "target": None, "execution_range": None, "input_mode": "artifact", "normalized_input": normalized, "current_structure_state": {"runtime_results": [], "carry_forward_entities": []}}],
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

    def _multi_scope_request(self, *, scope_b_complete: bool = True) -> dict:
        tcn_a = runtime.make_machine_entity("test-condition-design", "tcn", "TCN-001", {"tcn_id": "TCN-001"})
        tcn_b = runtime.make_machine_entity("test-condition-design", "tcn", "TCN-002", {"tcn_id": "TCN-002"})
        model_a = runtime.make_machine_entity("test-condition-design", "model", "ep-001", {"model_key": "ep-001", "model_type": "ep"}, model_key="ep-001")
        model_b = runtime.make_machine_entity("test-condition-design", "model", "ep-002", {"model_key": "ep-002", "model_type": "ep"}, model_key="ep-002")
        ci_a = runtime.make_machine_entity("test-condition-design", "ci", "TCN-001-CI01", {"ci_id": "TCN-001-CI01", "tcn_id": "TCN-001", "model_key": "ep-001"}, model_key="ep-001")
        ci_b = runtime.make_machine_entity("test-condition-design", "ci", "TCN-002-CI01", {"ci_id": "TCN-002-CI01", "tcn_id": "TCN-002", "model_key": "ep-002"}, model_key="ep-002")
        normalized_a = {"tcn_id": "TCN-001", "test_conditions": [{"tcn_id": "TCN-001"}], "models": [{"model_key": "ep-001", "model_type": "ep"}], "ci_ids": ["TCN-001-CI01"]}
        normalized_b = {"tcn_id": "TCN-002", "test_conditions": [{"tcn_id": "TCN-002"}], "models": [{"model_key": "ep-002", "model_type": "ep"}], "ci_ids": ["TCN-002-CI01"]}
        units = [
            runtime_row("test-condition-design", "artifact:condition_structure:all"),
            runtime_row("test-condition-design", "model:ep-001", "ep-001"),
            runtime_row("test-condition-design", "model:ep-002", "ep-002"),
            runtime_row("test-condition-design", "artifact:materialize_coverage:TCN-001", materialize=True, active_ci_ids=["TCN-001-CI01"], materialize_model_key="ep-001"),
            runtime_row("test-condition-design", "artifact:materialize_coverage:TCN-002", materialize=True, active_ci_ids=["TCN-002-CI01"], materialize_model_key="ep-002", materialize_complete=scope_b_complete),
        ]
        return {
            "metadata": metadata(),
            "input": {
                "workflow_scopes": [
                    {"skill": "test-condition-design", "target": "TCN-001", "execution_range": None, "input_mode": "artifact", "normalized_input": normalized_a, "current_structure_state": {"runtime_results": [], "carry_forward_entities": []}},
                    {"skill": "test-condition-design", "target": "TCN-002", "execution_range": None, "input_mode": "artifact", "normalized_input": normalized_b, "current_structure_state": {"runtime_results": [], "carry_forward_entities": []}},
                ],
                "runtime_units": units, "current_runtime_units": units, "current_entities": [tcn_a, tcn_b, model_a, model_b, ci_a, ci_b], "unsupported_item_closures": [],
            },
        }

    def test_two_complete_scopes_are_checked_independently(self) -> None:
        result = run(self._multi_scope_request())
        self.assertEqual(result["runtime_status"], "ok")
        self.assertTrue(result["payload"]["can_complete"], result)

    def test_incomplete_scope_cannot_be_hidden_by_other_scope_ci(self) -> None:
        result = run(self._multi_scope_request(scope_b_complete=False))
        self.assertEqual(result["runtime_status"], "ok")
        self.assertEqual(result["result_status"], "unresolved")
        self.assertFalse(result["payload"]["can_complete"])
        self.assertTrue(any(issue["issue_type"] == "model_materialize_incomplete" and issue.get("model_key") == "ep-002" for issue in result["issues"]))

    def test_missing_runtime_and_entity_in_scope_b_are_not_filled_from_scope_a(self) -> None:
        request = self._multi_scope_request()
        request["input"]["runtime_units"] = [row for row in request["input"]["runtime_units"] if row["runtime_unit_key"] != "model:ep-002"]
        request["input"]["current_entities"] = [entity for entity in request["input"]["current_entities"] if entity["entity_ref"] not in {"ep-002", "TCN-002-CI01"}]
        result = run(request)
        self.assertEqual(result["result_status"], "unresolved")
        self.assertIn(["test-condition-design", "model:ep-002"], result["payload"]["missing_runtime_units"])
        self.assertIn(["test-condition-design", "model", "ep-002"], result["payload"]["missing_entities"])

    def _partial_scope_request(self) -> tuple[dict, dict[str, object]]:
        tcn_one = runtime.make_machine_entity("test-condition-design", "tcn", "TCN-001", {"tcn_id": "TCN-001"})
        tcn_two = runtime.make_machine_entity("test-condition-design", "tcn", "TCN-002", {"tcn_id": "TCN-002"})
        model_one = runtime.make_machine_entity("test-condition-design", "model", "ep-001", {"model_key": "ep-001", "model_type": "ep"}, model_key="ep-001")
        model_two = runtime.make_machine_entity("test-condition-design", "model", "ep-002", {"model_key": "ep-002", "model_type": "ep"}, model_key="ep-002")
        ci = runtime.make_machine_entity("test-condition-design", "ci", "TCN-001-CI01", {"ci_id": "TCN-001-CI01", "tcn_id": "TCN-001", "model_key": "ep-001"}, model_key="ep-001")
        ci_two = runtime.make_machine_entity("test-condition-design", "ci", "TCN-002-CI01", {"ci_id": "TCN-002-CI01", "tcn_id": "TCN-002", "model_key": "ep-002"}, model_key="ep-002")
        tdr_two = runtime.make_machine_entity("test-condition-design", "test_data_requirement", "data:REQ-002", {"data_ref": "data:REQ-002", "requirement_key": "REQ-002", "source_model_key": "ep-002"}, model_key="ep-002")
        tr_two = runtime.make_machine_entity("test-requirement-design", "tr", "TR-002", {"tr_id": "TR-002"})
        tr_dependency = runtime.machine_entity_dependency(tr_two)
        tr_disposition = runtime.make_machine_entity(
            "test-condition-design", "disposition", "tr:TR-002",
            {"upstream_entity": tr_dependency, "handling": "対象外", "reason": "scope-out requirement", "authority_refs": [], "covered_by_entity": None},
            upstream_entity_dependencies=[tr_dependency],
        )
        normalized = {
            "tcn_id": "TCN-001", "test_conditions": [{"tcn_id": "TCN-001"}],
            "models": [{"model_key": "ep-001", "model_type": "ep"}], "ci_ids": ["TCN-001-CI01"],
            "upstream_entities": [{"skill": "test-requirement-design", "entity_type": "tr", "entity_ref": "TR-002"}],
            "previous_tcn_ids": [{"tcn_id": "TCN-001", "status": "active"}, {"tcn_id": "TCN-002", "status": "active"}],
            "previous_model_keys": [
                {"model_key": "ep-001", "model_type": "ep", "status": "active"},
                {"model_key": "ep-002", "model_type": "ep", "status": "active"},
            ],
            "update_scope_tcn_ids": ["TCN-001"], "update_scope_model_keys": ["ep-001"],
        }
        units = [
            runtime_row("test-condition-design", "artifact:condition_structure:all"),
            runtime_row("test-condition-design", "model:ep-001", "ep-001"),
            runtime_row("test-condition-design", "artifact:materialize_coverage:TCN-001", materialize=True, active_ci_ids=["TCN-001-CI01"], materialize_model_key="ep-001"),
        ]
        state = {"runtime_results": [], "carry_forward_entities": [tcn_two, model_two, ci_two, tdr_two, tr_disposition]}
        request = {
            "metadata": metadata(),
            "input": {
                "workflow_scopes": [{"skill": "test-condition-design", "target": "TCN-001", "execution_range": None, "input_mode": "artifact", "normalized_input": normalized, "current_structure_state": state}],
                "runtime_units": units, "current_runtime_units": units,
                "current_entities": [tcn_one, tcn_two, model_one, model_two, ci, ci_two, tdr_two, tr_two, tr_disposition],
                "unsupported_item_closures": [],
            },
        }
        return request, {"entities": [tcn_one, tcn_two, model_one, model_two, ci, ci_two, tdr_two, tr_two, tr_disposition], "state": state, "units": units}

    def test_partial_rerun_uses_normalized_scope_and_current_structure_projection(self) -> None:
        request, parts = self._partial_scope_request()
        result = run(request)
        self.assertEqual(result["result_status"], "ready", result)
        self.assertTrue(result["payload"]["can_complete"])
        expected = {(row["entity_type"], row["entity_ref"]) for row in result["payload"]["expected_entities"]}
        self.assertTrue({("tcn", "TCN-001"), ("tcn", "TCN-002"), ("model", "ep-001"), ("model", "ep-002")}.issubset(expected))
        self.assertIn(("test_data_requirement", "data:REQ-002"), expected)
        self.assertIn(("disposition", "tr:TR-002"), expected)

        missing = json.loads(json.dumps(request))
        missing["input"]["current_entities"] = [row for row in missing["input"]["current_entities"] if row["entity_ref"] != "ep-002"]
        missing_result = run(missing)
        self.assertEqual(missing_result["result_status"], "unresolved")
        self.assertIn(["test-condition-design", "model", "ep-002"], missing_result["payload"]["missing_entities"])

        for ref in ("data:REQ-002", "tr:TR-002"):
            with self.subTest(missing=ref):
                missing_owner = json.loads(json.dumps(request))
                missing_owner["input"]["current_entities"] = [row for row in missing_owner["input"]["current_entities"] if row["entity_ref"] != ref]
                result_missing_owner = run(missing_owner)
                self.assertEqual(result_missing_owner["result_status"], "unresolved")
                self.assertIn(["test-condition-design", "test_data_requirement" if ref == "data:REQ-002" else "disposition", ref], result_missing_owner["payload"]["missing_entities"])

        no_projection = json.loads(json.dumps(request))
        del no_projection["input"]["workflow_scopes"][0]["current_structure_state"]["carry_forward_entities"]
        rejected_projection = run(no_projection)
        self.assertEqual(rejected_projection["runtime_status"], "invalid_input")

    def test_current_structure_state_rejects_extra_or_in_scope_carry_rows(self) -> None:
        request, _parts = self._partial_scope_request()
        unknown_tcn = runtime.make_machine_entity("test-condition-design", "tcn", "TCN-999", {"tcn_id": "TCN-999"})
        in_scope_tcn = runtime.make_machine_entity("test-condition-design", "tcn", "TCN-001", {"tcn_id": "TCN-001"})
        in_scope_tdr = runtime.make_machine_entity("test-condition-design", "test_data_requirement", "data:REQ-001", {"data_ref": "data:REQ-001", "requirement_key": "REQ-001", "source_model_key": "ep-001"}, model_key="ep-001")
        unknown_owner = {"skill": "test-requirement-design", "entity_type": "tr", "entity_ref": "TR-999", "content_fingerprint": "sha256:" + ("0" * 64)}
        ownerless_disposition = runtime.make_machine_entity(
            "test-condition-design", "disposition", "tr:TR-999",
            {"upstream_entity": unknown_owner, "handling": "対象外", "reason": "scope-out", "authority_refs": [], "covered_by_entity": None},
            upstream_entity_dependencies=[unknown_owner],
        )
        for label, entity in (
            ("unknown TCN", unknown_tcn),
            ("in-scope TCN", in_scope_tcn),
            ("TDR owned by in-scope model", in_scope_tdr),
            ("disposition with unknown owner", ownerless_disposition),
        ):
            with self.subTest(label=label):
                tampered = json.loads(json.dumps(request))
                tampered["input"]["workflow_scopes"][0]["current_structure_state"]["carry_forward_entities"].append(entity)
                result = run(tampered)
                self.assertEqual(result["runtime_status"], "invalid_input", result)

        for label, edit in (
            ("unknown projection field", lambda state: state.update({"expected_entities": []})),
            ("duplicate carry identity", lambda state: state["carry_forward_entities"].append(state["carry_forward_entities"][0])),
            ("missing required scope-out TCN", lambda state: state["carry_forward_entities"].remove(next(row for row in state["carry_forward_entities"] if row["entity_type"] == "tcn"))),
            ("tampered content fingerprint", lambda state: state["carry_forward_entities"][0]["content"].update({"tcn_id": "TCN-099"})),
            ("duplicate runtime result identity", lambda state: state.update({"runtime_results": [{"identity": "test-condition-design::artifact:condition_structure:all", "result": {}}, {"identity": "test-condition-design::artifact:condition_structure:all", "result": {}}]})),
        ):
            with self.subTest(label=label):
                tampered = json.loads(json.dumps(request))
                edit(tampered["input"]["workflow_scopes"][0]["current_structure_state"])
                result = run(tampered)
                self.assertEqual(result["runtime_status"], "invalid_input", result)

    def test_partial_rerun_rejects_deleted_scope_entity_left_in_current_entities(self) -> None:
        request, parts = self._partial_scope_request()
        scope = request["input"]["workflow_scopes"][0]
        scope["normalized_input"]["test_conditions"] = []
        scope["normalized_input"]["models"] = []
        scope["normalized_input"]["ci_ids"] = []
        scope["normalized_input"]["update_scope_tcn_ids"] = ["TCN-001"]
        scope["current_structure_state"] = {
            "runtime_results": [],
            "carry_forward_entities": parts["state"]["carry_forward_entities"],
        }
        request["input"]["runtime_units"] = [request["input"]["runtime_units"][0]]
        request["input"]["current_runtime_units"] = request["input"]["runtime_units"]
        result = run(request)
        self.assertEqual(result["result_status"], "unresolved")
        self.assertIn(["test-condition-design", "tcn", "TCN-001"], result["payload"]["extra_entities"])

    def test_stale_scope_out_entity_blocks_partial_workflow_completion(self) -> None:
        request, parts = self._partial_scope_request()
        old_context = {
            "runtime_contract_version": runtime.RUNTIME_CONTRACT_VERSION,
            "generator_contract_version": "condition-structure-v1",
            "runtime_implementation_fingerprint": runtime.implementation_fingerprint(RUNTIME_PATH),
            "generator_implementation_fingerprint": "sha256:" + "1" * 64,
            "static_data_versions": {},
        }
        stale_tcn = runtime.make_machine_entity(
            "test-condition-design", "tcn", "TCN-002", {"tcn_id": "TCN-002"},
            runtime_dependencies=[runtime.machine_entity_runtime_dependency("test-condition-design", "artifact:condition_structure:all")],
        )
        stale_tcn = runtime.bind_current_entity_runtime_dependencies(
            {"entities": [stale_tcn]}, "sha256:" + "2" * 64, runtime_context=old_context,
        )["entities"][0]
        request["input"]["current_entities"] = [
            stale_tcn if row["entity_type"] == "tcn" and row["entity_ref"] == "TCN-002" else row
            for row in request["input"]["current_entities"]
        ]
        root_runtime = request["input"]["current_runtime_units"][0]
        root_runtime.update({
            "runtime_contract_version": runtime.RUNTIME_CONTRACT_VERSION,
            "generator_contract_version": "condition-structure-v1",
            "runtime_implementation_fingerprint": runtime.implementation_fingerprint(RUNTIME_PATH),
            "generator_implementation_fingerprint": "sha256:" + "3" * 64,
            "static_data_versions": {},
        })
        request["input"]["runtime_units"][0].update({key: value for key, value in root_runtime.items() if key not in {"model_completion", "target_mappings", "target_dispositions"}})
        result = run(request)
        self.assertEqual(result["result_status"], "unresolved")
        self.assertFalse(result["payload"]["can_complete"])
        self.assertTrue(any(issue["issue_type"] == "stale_entity" and issue.get("entity_ref") == "TCN-002" for issue in result["issues"]))


if __name__ == "__main__":
    unittest.main()
