from __future__ import annotations

import copy
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
    row = {
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
    row["result_fingerprint"] = runtime.sha256_digest(row)
    return row


def model_content(model_key: str, parent_tcn_id: str, *, technique_slug: str | None = "ep", model_type: str = "ep") -> dict:
    return {
        "model_key": model_key, "model_type": model_type, "technique_slug": technique_slug,
        "parent_tcn_id": parent_tcn_id, "selection_source": "condition_design" if technique_slug else None,
        "selection_key": None, "derived_from_model_key": None,
    }


def base_request() -> dict:
    tcn = runtime.make_machine_entity("test-condition-design", "tcn", "TCN-001", {"tcn_id": "TCN-001"})
    model = runtime.make_machine_entity("test-condition-design", "model", "ep-001", model_content("ep-001", "TCN-001"), model_key="ep-001")
    ci = runtime.make_machine_entity("test-condition-design", "ci", "TCN-001-CI01", {"ci_id": "TCN-001-CI01", "tcn_id": "TCN-001", "model_key": "ep-001"}, model_key="ep-001")
    units = [runtime_row("test-condition-design", "artifact:condition_structure:all"), runtime_row("test-condition-design", "model:ep-001", "ep-001"), runtime_row("test-condition-design", "artifact:materialize_coverage:TCN-001", materialize=True, materialize_model_key="ep-001", active_ci_ids=["TCN-001-CI01"])]
    return {
        "metadata": metadata(),
        "input": {
            "analysis_scopes": [{"skill": "test-condition-design", "target": None, "execution_range": None, "input_mode": "artifact", "normalized_input": {"tcn_id": "TCN-001", "test_conditions": [{"tcn_id": "TCN-001"}], "models": [{"model_key": "ep-001", "model_type": "ep"}], "ci_ids": ["TCN-001-CI01"]}, "current_structure_state": {"runtime_results": [], "carry_forward_entities": [], "previous_ci_id_state": []}}],
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
    def test_coverage_model_tcn_cannot_use_direct_tc_edge_as_closure(self) -> None:
        request = base_request()
        for row_set in ("runtime_units", "current_runtime_units"):
            unsupported_model = next(row for row in request["input"][row_set] if row["runtime_unit_key"] == "model:ep-001")
            unsupported_model["support_status"] = "unsupported"
            unsupported_model["runtime_status"] = "unsupported"
            materialize = next(row for row in request["input"][row_set] if row["runtime_unit_key"] == "artifact:materialize_coverage:TCN-001")
            materialize["model_completion"] = []
        request["input"]["edges"] = [
            {"from": "SPEC-001", "to": "TR-001"},
            {"from": "TR-001", "to": "TCN-001"},
            {"from": "TCN-001", "to": "TC-001"},
        ]
        result = run(request)
        self.assertEqual(result["runtime_status"], "invalid_input", result)

    def test_coverage_model_tcn_rejects_extra_direct_tc_edge_even_with_ci_path(self) -> None:
        request = base_request()
        request["input"]["edges"].append({"from": "TCN-001", "to": "TC-001"})
        result = run(request)
        self.assertEqual(result["runtime_status"], "invalid_input", result)

    def test_coverage_model_closure_is_scoped_to_its_parent_tcn(self) -> None:
        request = base_request()
        tcn_two = runtime.make_machine_entity("test-condition-design", "tcn", "TCN-002", {"tcn_id": "TCN-002"})
        request["input"]["current_entities"].append(tcn_two)
        scope = request["input"]["analysis_scopes"][0]
        scope["normalized_input"]["test_conditions"].append({"tcn_id": "TCN-002"})
        request["input"]["nodes"].append({"node_key": "TCN-002", "node_type": "TCN"})
        request["input"]["edges"].append({"from": "TR-001", "to": "TCN-002"})

        result = run(request)

        self.assertEqual(result["runtime_status"], "ok", result)
        self.assertTrue(result["payload"]["can_complete"], result["issues"])
        self.assertFalse(any(
            issue["issue_type"] == "coverage_model_closure_missing" and issue.get("node_key") == "TCN-002"
            for issue in result["issues"]
        ), result["issues"])

    def test_runtime_row_model_identity_is_validated_for_saved_and_current_rows(self) -> None:
        for row_set in ("runtime_units", "current_runtime_units"):
            with self.subTest(row_set=row_set, case="model key mismatch"):
                request = base_request()
                model = next(row for row in request["input"][row_set] if row["runtime_unit_key"] == "model:ep-001")
                model["model_key"] = "ep-999"
                self.assertEqual(run(request)["runtime_status"], "invalid_input")

            with self.subTest(row_set=row_set, case="artifact model key"):
                request = base_request()
                artifact = next(row for row in request["input"][row_set] if row["runtime_unit_key"] == "artifact:condition_structure:all")
                artifact["model_key"] = "ep-001"
                self.assertEqual(run(request)["runtime_status"], "invalid_input")

    def test_non_materialize_runtime_rejects_coverage_projections(self) -> None:
        cases = (
            ("model:ep-001", "model_completion"),
            ("artifact:condition_structure:all", "target_mappings"),
            ("model:ep-001", "target_dispositions"),
        )
        for row_set in ("runtime_units", "current_runtime_units"):
            for unit, field in cases:
                with self.subTest(row_set=row_set, unit=unit, field=field):
                    request = base_request()
                    row = next(row for row in request["input"][row_set] if row["runtime_unit_key"] == unit)
                    row[field] = [{"tampered": True}]
                    self.assertEqual(run(request)["runtime_status"], "invalid_input")

    def test_saved_result_projection_mismatch_is_stale_while_semantics_use_current_rows(self) -> None:
        request = base_request()
        request["input"]["runtime_units"] = copy.deepcopy(request["input"]["runtime_units"])
        request["input"]["current_runtime_units"] = copy.deepcopy(request["input"]["current_runtime_units"])
        saved = next(row for row in request["input"]["runtime_units"] if row["runtime_unit_key"] == "artifact:materialize_coverage:TCN-001")
        current = next(row for row in request["input"]["current_runtime_units"] if row["runtime_unit_key"] == "artifact:materialize_coverage:TCN-001")
        saved["model_completion"][0]["materialize_complete"] = False
        result = run(request)
        self.assertEqual(saved["generation_fingerprint"], current["generation_fingerprint"])
        self.assertEqual(result["result_status"], "unresolved")
        self.assertTrue(any(issue["issue_type"] == "current_runtime_result_mismatch" for issue in result["issues"]), result["issues"])
        self.assertTrue(any(issue["issue_type"] == "runtime_not_complete" for issue in result["issues"]), result["issues"])

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

    def test_partial_rerun_projects_scope_out_entities_from_fixed_structure_state(self) -> None:
        request = base_request()
        tcn_two = runtime.make_machine_entity("test-condition-design", "tcn", "TCN-002", {"tcn_id": "TCN-002"})
        model_two = runtime.make_machine_entity("test-condition-design", "model", "ep-002", {"model_key": "ep-002", "model_type": "ep"}, model_key="ep-002")
        ci_two = runtime.make_machine_entity("test-condition-design", "ci", "TCN-002-CI01", {"ci_id": "TCN-002-CI01", "tcn_id": "TCN-002", "model_key": "ep-002"}, model_key="ep-002")
        tdr_two = runtime.make_machine_entity("test-condition-design", "test_data_requirement", "data:REQ-002", {"data_ref": "data:REQ-002", "requirement_key": "REQ-002", "source_model_key": "ep-002"}, model_key="ep-002")
        tr_two = runtime.make_machine_entity("test-requirement-design", "tr", "TR-002", {"tr_id": "TR-002"})
        tr_dependency = runtime.machine_entity_dependency(tr_two)
        tr_disposition = runtime.make_machine_entity(
            "test-condition-design", "disposition", "tr:TR-002",
            {"upstream_entity": tr_dependency, "handling": "対象外", "reason": "scope-out requirement", "authority_refs": [], "covered_by_entity": None},
            upstream_entity_dependencies=[tr_dependency],
        )
        request["input"]["current_entities"].extend([tcn_two, model_two, ci_two, tdr_two, tr_two, tr_disposition])
        request["input"]["nodes"].extend([
            {"node_key": "TCN-002", "node_type": "TCN"},
            {"node_key": "TCN-002-CI01", "node_type": "CI"},
        ])
        normalized = {
            "tcn_id": "TCN-001", "test_conditions": [{"tcn_id": "TCN-001"}],
            "models": [{"model_key": "ep-001", "model_type": "ep"}], "ci_ids": ["TCN-001-CI01"],
            "previous_tcn_ids": [{"tcn_id": "TCN-001", "status": "active"}, {"tcn_id": "TCN-002", "status": "active"}],
            "previous_model_keys": [{"model_key": "ep-001", "model_type": "ep", "status": "active"}, {"model_key": "ep-002", "model_type": "ep", "status": "active"}],
            "previous_ci_ids": [{"ci_id": "TCN-001-CI01", "status": "active"}],
            "update_scope_tcn_ids": ["TCN-001"], "update_scope_model_keys": ["ep-001"],
            "upstream_entities": [{"skill": "test-requirement-design", "entity_type": "tr", "entity_ref": "TR-002"}],
        }
        scope = request["input"]["analysis_scopes"][0]
        scope["normalized_input"] = normalized
        scope["current_structure_state"] = {
            "runtime_results": [],
            "carry_forward_entities": [tcn_two, model_two, ci_two, tdr_two, tr_disposition],
            "previous_ci_id_state": [
                {"ci_id": "TCN-001-CI01", "status": "active"},
                {"ci_id": "TCN-002-CI01", "status": "active"},
            ],
        }
        result = run(request)
        self.assertEqual(result["runtime_status"], "ok", result)
        self.assertEqual(result["payload"]["missing_entities"], [])
        self.assertEqual(result["payload"]["extra_entities"], [])
        expected = {(row["entity_type"], row["entity_ref"]) for row in result["payload"]["expected_entities"]}
        self.assertTrue({("tcn", "TCN-002"), ("model", "ep-002"), ("ci", "TCN-002-CI01")}.issubset(expected))
        self.assertIn(("test_data_requirement", "data:REQ-002"), expected)
        self.assertIn(("disposition", "tr:TR-002"), expected)

        for ref, entity_type in (("data:REQ-002", "test_data_requirement"), ("tr:TR-002", "disposition")):
            with self.subTest(missing=ref):
                missing = json.loads(json.dumps(request))
                missing["input"]["current_entities"] = [row for row in missing["input"]["current_entities"] if row["entity_ref"] != ref]
                missing_result = run(missing)
                self.assertEqual(missing_result["result_status"], "unresolved")
                self.assertIn(["test-condition-design", entity_type, ref], missing_result["payload"]["missing_entities"])

        no_projection = json.loads(json.dumps(request))
        del no_projection["input"]["analysis_scopes"][0]["current_structure_state"]["carry_forward_entities"]
        rejected_projection = run(no_projection)
        self.assertEqual(rejected_projection["runtime_status"], "invalid_input")

        unknown_tcn = runtime.make_machine_entity("test-condition-design", "tcn", "TCN-999", {"tcn_id": "TCN-999"})
        in_scope_tcn = runtime.make_machine_entity("test-condition-design", "tcn", "TCN-001", {"tcn_id": "TCN-001"})
        in_scope_tdr = runtime.make_machine_entity("test-condition-design", "test_data_requirement", "data:REQ-001", {"data_ref": "data:REQ-001", "requirement_key": "REQ-001", "source_model_key": "ep-001"}, model_key="ep-001")
        extra_ci = runtime.make_machine_entity("test-condition-design", "ci", "TCN-002-CI99", {"ci_id": "TCN-002-CI99", "tcn_id": "TCN-002", "model_key": "ep-002"}, model_key="ep-002")
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
            ("CI absent from previous CI state", extra_ci),
            ("disposition with unknown owner", ownerless_disposition),
        ):
            with self.subTest(label=label):
                tampered = json.loads(json.dumps(request))
                tampered["input"]["analysis_scopes"][0]["current_structure_state"]["carry_forward_entities"].append(entity)
                result = run(tampered)
                self.assertEqual(result["runtime_status"], "invalid_input", result)

        tampered_projection = json.loads(json.dumps(request))
        unknown_tcn = runtime.make_machine_entity("test-condition-design", "tcn", "TCN-999", {"tcn_id": "TCN-999"})
        tampered_projection["input"]["analysis_scopes"][0]["current_structure_state"]["carry_forward_entities"].append(unknown_tcn)
        self.assertEqual(run(tampered_projection)["runtime_status"], "invalid_input")

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
                    {"skill": "test-condition-design", "target": "TCN-001", "execution_range": None, "input_mode": "artifact", "normalized_input": normalized_a, "current_structure_state": {"runtime_results": [], "carry_forward_entities": [], "previous_ci_id_state": []}},
                    {"skill": "test-condition-design", "target": "TCN-002", "execution_range": None, "input_mode": "artifact", "normalized_input": normalized_b, "current_structure_state": {"runtime_results": [], "carry_forward_entities": [], "previous_ci_id_state": []}},
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
