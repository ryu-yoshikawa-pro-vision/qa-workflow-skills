from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "skills" / "test-analysis" / "scripts" / "analysis_entities.py"
ENVIRONMENT_SCRIPT = REPO_ROOT / "skills" / "test-analysis" / "scripts" / "environment_requirements.py"
WORKFLOW_SCRIPT = REPO_ROOT / "skills" / "qa-workflow" / "scripts" / "workflow_runtime.py"
RUNTIME_PATH = REPO_ROOT / "skills" / "test-analysis" / "scripts" / "runtime_contract.py"
SPEC = importlib.util.spec_from_file_location("analysis_entity_runtime_contract", RUNTIME_PATH)
assert SPEC is not None and SPEC.loader is not None
runtime = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = runtime
SPEC.loader.exec_module(runtime)


def metadata(upstream_entities: list[dict] | None = None, *, input_mode: str = "direct") -> dict:
    return {
        "envelope_version": "1", "skill": "test-analysis", "runtime_contract_version": "runtime-v1", "generator_contract_version": "analysis-entities-v1",
        "runtime_unit_key": "artifact:analysis_entities:all", "model_key": None, "model_type": None, "technique_slug": None, "selection_source": None, "selection_key": None,
        "scope_key": "all", "input_mode": input_mode, "upstream_entities": upstream_entities or [], "upstream_runtime_units": [], "static_data_versions": {}, "authority_refs": [], "reference_refs": [],
    }


def run(value: dict, upstream_entities: list[dict] | None = None, *, input_mode: str = "direct") -> dict:
    result = subprocess.run([sys.executable, str(SCRIPT)], input=json.dumps({"metadata": metadata(upstream_entities, input_mode=input_mode), "input": value}, ensure_ascii=False).encode(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=REPO_ROOT, check=False)
    if result.stderr:
        raise AssertionError(result.stderr.decode())
    return json.loads(result.stdout)


def run_runtime(script: Path, metadata_value: dict, input_value: dict) -> dict:
    result = subprocess.run([sys.executable, str(script)], input=json.dumps({"metadata": metadata_value, "input": input_value}, ensure_ascii=False).encode(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=REPO_ROOT, check=False)
    if result.stderr:
        raise AssertionError(result.stderr.decode())
    return json.loads(result.stdout)


def environment_metadata() -> dict:
    return {
        "envelope_version": "1", "skill": "test-analysis", "runtime_contract_version": "runtime-v1", "generator_contract_version": "environment-requirements-v1",
        "runtime_unit_key": "artifact:environment_requirements:all", "model_key": None, "model_type": None, "technique_slug": None, "selection_source": None, "selection_key": None,
        "scope_key": "all", "input_mode": "direct", "upstream_entities": [], "upstream_runtime_units": [], "static_data_versions": {}, "authority_refs": [], "reference_refs": [],
    }


def valid_input() -> dict:
    signals = {
        "ordered_domain": True, "explicit_boundaries": False, "equivalence_classes": False, "multiple_discrete_conditions": False,
        "stateful": None, "multiple_factors": False, "explicit_flow": False, "multi_variable_domain": False, "crud_model": False,
        "operational_profile": False, "metamorphic_relation": False, "grammar_model": False,
    }
    return {
        "test_analysis_context": {
            "scope": "checkout", "objectives": ["安全な購入"], "test_levels": ["system"], "environment_constraints": [],
            "exclusions": [], "blockers": [], "test_focus_items": ["境界"], "testability_decisions": ["自動化"], "residual_risks": [], "authority_refs": [], "risk_refs": [],
        },
        "product_risks": [{
            "risk_id": "R-001", "failure": "invalid total", "source_refs": [], "authority_refs": [], "impact": 4, "likelihood": 2,
            "assessment_reason": "high impact", "confidence_note": "reviewed",
        }],
        "technique_selections": [{
            "selection_key": "selection-001", "applicability_scope": "total", "selection_source": "analysis", "signals": signals,
            "selected_techniques": ["bva"], "selection_reason": "boundary", "risk_refs": ["R-001"], "authority_refs": [],
            "condition_design_focus": ["threshold"], "undetermined_signal_closures": [{"signal_key": "stateful", "handling": "selection_not_affected", "reason": "not stateful", "question_id": None}], "status": "active",
        }],
        "change_nodes": [{"node_key": "R-001", "node_type": "Risk", "source_ref": "risk:R-001", "change_kind": None, "expected_impact": None}],
        "change_edges": [],
        "environment_requirements": [{"requirement_key": "env-1", "environment_key": "chrome", "dimension_key": "browser", "operator": "eq", "value": {"type": "string", "value": "120"}, "authority_refs": [], "source_model_key": None, "source_target_versions": []}],
        "risk_matrix_results": [{"risk_id": "R-001", "level": "高", "mapped_priority": "高"}],
        "technique_candidate_results": [{"selection_key": "selection-001", "candidates": ["境界値分析"], "undetermined_signals": ["stateful"]}],
        "current_runtime_units": [
            {"skill": "test-analysis", "runtime_unit_key": "artifact:risk_matrix:all", "generation_fingerprint": "sha256:" + "1" * 64},
            {"skill": "test-analysis", "runtime_unit_key": "artifact:technique_candidates:selection-001", "generation_fingerprint": "sha256:" + "2" * 64},
        ],
    }


class AnalysisEntityRuntimeTests(unittest.TestCase):
    def test_fixed_join_preserves_meaning_fields_and_expected_identities(self) -> None:
        result = run(valid_input())
        self.assertEqual(result["runtime_status"], "ok")
        entities = result["payload"]["machine_entities"]
        risk = next(row for row in entities if row["entity_type"] == "product_risk")
        selection = next(row for row in entities if row["entity_type"] == "technique_selection")
        self.assertEqual(risk["content"]["mapped_priority"], "高")
        self.assertEqual(risk["content"]["assessment_reason"], "high impact")
        self.assertEqual(selection["content"]["candidates"], ["境界値分析"])
        self.assertEqual(selection["content"]["undetermined_signals"], ["stateful"])
        identities = {(row["entity_type"], row["entity_ref"]) for row in result["payload"]["expected_entity_identities"]}
        self.assertIn(("test_analysis_context", "analysis-context:all"), identities)
        self.assertIn(("product_risk", "R-001"), identities)
        self.assertIn(("environment_requirement", "env-1"), identities)

    def test_missing_join_row_is_invalid(self) -> None:
        value = valid_input()
        value["risk_matrix_results"] = []
        self.assertEqual(run(value)["runtime_status"], "invalid_input")

    def test_active_selection_cannot_hide_question_closure(self) -> None:
        value = valid_input()
        value["technique_selections"][0]["undetermined_signal_closures"][0] = {"signal_key": "stateful", "handling": "question", "reason": "need answer", "question_id": "Q-001"}
        self.assertEqual(run(value)["runtime_status"], "invalid_input")

    def test_same_invocation_predecessors_feed_risk_and_selection_dependencies_only_forward(self) -> None:
        value = valid_input()
        value["product_risks"][0]["source_refs"] = ["payment-change", "edge-evidence", "SPEC-001", "TC-001"]
        value["product_risks"][0]["authority_refs"] = ["SPEC-001"]
        value["technique_selections"][0]["authority_refs"] = ["SPEC-001"]
        value["change_nodes"] = [
            {"node_key": "CHANGE-001", "node_type": "TR", "source_ref": "payment-change", "change_kind": "変更", "expected_impact": "payment total"},
            {"node_key": "CHANGE-002", "node_type": "TR", "source_ref": "inventory-change", "change_kind": "変更", "expected_impact": "inventory"},
            {"node_key": "CHANGE-003", "node_type": "Authority", "source_ref": "SPEC-001", "change_kind": "参考", "expected_impact": "authority basis"},
        ]
        value["change_edges"] = [{"edge_key": "EDGE-001", "from": "CHANGE-001", "to": "CHANGE-002", "edge_type": "depends_on", "evidence_refs": ["edge-evidence", "SPEC-001"]}]
        authority = runtime.make_machine_entity("spec-analysis", "authority", "SPEC-001", {"authority_id": "SPEC-001"})
        downstream_tc = runtime.make_machine_entity("test-case-design", "tc", "TC-001", {"tc_id": "TC-001"})
        upstream = [{"skill": entity["skill"], "entity_type": entity["entity_type"], "entity_ref": entity["entity_ref"], "content": entity["content"]} for entity in (authority, downstream_tc)]
        result = run(value, upstream)
        self.assertEqual(result["runtime_status"], "ok")
        entities = result["payload"]["machine_entities"]
        risk = next(row for row in entities if row["entity_type"] == "product_risk")
        selection = next(row for row in entities if row["entity_type"] == "technique_selection")
        risk_deps = {(row["entity_type"], row["entity_ref"]) for row in risk["upstream_entity_dependencies"]}
        self.assertIn(("authority", "SPEC-001"), risk_deps)
        self.assertIn(("change_node", "CHANGE-001"), risk_deps)
        self.assertIn(("change_node", "CHANGE-003"), risk_deps)
        self.assertIn(("change_edge", "EDGE-001"), risk_deps)
        graph_entities = {row["entity_ref"]: row for row in entities if row["entity_type"] in {"change_node", "change_edge"}}
        self.assertEqual([(row["entity_type"], row["entity_ref"]) for row in graph_entities["CHANGE-003"]["upstream_entity_dependencies"]], [("authority", "SPEC-001")])
        self.assertEqual([(row["entity_type"], row["entity_ref"]) for row in graph_entities["EDGE-001"]["upstream_entity_dependencies"]], [("authority", "SPEC-001")])
        self.assertNotIn(("tc", "TC-001"), risk_deps)
        selection_deps = {(row["entity_type"], row["entity_ref"]): row for row in selection["upstream_entity_dependencies"]}
        self.assertEqual(selection_deps[("product_risk", "R-001")]["content_fingerprint"], risk["content_fingerprint"])
        self.assertIn(("authority", "SPEC-001"), selection_deps)
        self.assertNotIn(("tc", "TC-001"), selection_deps)

    def test_risk_and_environment_authority_changes_follow_only_explicit_dependencies(self) -> None:
        value = valid_input()
        value["product_risks"][0]["authority_refs"] = ["SPEC-A"]
        value["environment_requirements"][0]["authority_refs"] = ["SPEC-A"]
        authority_a = runtime.make_machine_entity("spec-analysis", "authority", "SPEC-A", {"authority_id": "SPEC-A", "text": "old A"})
        authority_b = runtime.make_machine_entity("spec-analysis", "authority", "SPEC-B", {"authority_id": "SPEC-B", "text": "stable B"})
        upstream = [{"skill": row["skill"], "entity_type": row["entity_type"], "entity_ref": row["entity_ref"], "content": row["content"]} for row in (authority_a, authority_b)]
        old = run(value, upstream)
        self.assertEqual(old["runtime_status"], "ok")
        old_risk = next(row for row in old["payload"]["machine_entities"] if row["entity_type"] == "product_risk")
        old_environment = next(row for row in old["payload"]["machine_entities"] if row["entity_type"] == "environment_requirement")

        changed_a = runtime.make_machine_entity("spec-analysis", "authority", "SPEC-A", {"authority_id": "SPEC-A", "text": "changed A"})
        changed_b = runtime.make_machine_entity("spec-analysis", "authority", "SPEC-B", {"authority_id": "SPEC-B", "text": "changed unrelated B"})
        for current_a, expected in ((changed_a, "stale"), (authority_a, "current")):
            current_rows = [current_a, changed_b, {**old_risk, "runtime_dependencies": []}, {**old_environment, "runtime_dependencies": []}]
            freshness = runtime.evaluate_entity_freshness(current_rows, {})
            status_by_type = {row["entity_type"]: row["freshness_status"] for row in freshness if row["entity_type"] in {"product_risk", "environment_requirement"}}
            self.assertEqual(status_by_type["product_risk"], expected)
            self.assertEqual(status_by_type["environment_requirement"], expected)

    def test_artifact_risk_and_environment_authority_refs_require_current_entities(self) -> None:
        value = valid_input()
        value["product_risks"][0]["authority_refs"] = ["SPEC-MISSING"]
        self.assertEqual(run(value, input_mode="artifact")["runtime_status"], "invalid_input")

        value = valid_input()
        value["product_risks"] = []
        value["technique_selections"] = []
        value["risk_matrix_results"] = []
        value["technique_candidate_results"] = []
        value["environment_requirements"][0]["authority_refs"] = ["SPEC-MISSING"]
        self.assertEqual(run(value, input_mode="artifact")["runtime_status"], "invalid_input")

    def test_context_does_not_infer_unreferenced_authority_or_risk_dependencies(self) -> None:
        value = valid_input()
        value["product_risks"] = []
        value["technique_selections"] = []
        value["risk_matrix_results"] = []
        value["technique_candidate_results"] = []
        authority = runtime.make_machine_entity("spec-analysis", "authority", "SPEC-UNRELATED", {"authority_id": "SPEC-UNRELATED"})
        risk = runtime.make_machine_entity("test-analysis", "product_risk", "R-UNRELATED", {"risk_id": "R-UNRELATED"})
        upstream = [{"skill": entity["skill"], "entity_type": entity["entity_type"], "entity_ref": entity["entity_ref"], "content": entity["content"]} for entity in (authority, risk)]
        result = run(value, upstream)
        self.assertEqual(result["runtime_status"], "ok")
        context = next(row for row in result["payload"]["machine_entities"] if row["entity_type"] == "test_analysis_context")
        self.assertEqual(context["upstream_entity_dependencies"], [])

    def test_context_dependencies_resolve_only_explicit_authority_and_same_invocation_risks(self) -> None:
        value = valid_input()
        second_risk = {**copy.deepcopy(value["product_risks"][0]), "risk_id": "R-002", "failure": "inventory mismatch"}
        value["product_risks"].append(second_risk)
        value["risk_matrix_results"].append({"risk_id": "R-002", "level": "中", "mapped_priority": "中"})
        value["test_analysis_context"]["authority_refs"] = ["SPEC-002", "SPEC-001"]
        value["test_analysis_context"]["risk_refs"] = ["R-002", "R-001"]
        authorities = [
            runtime.make_machine_entity("spec-analysis", "authority", ref, {"authority_id": ref, "active_content": ref})
            for ref in ("SPEC-001", "SPEC-002")
        ]
        upstream = [{"skill": row["skill"], "entity_type": row["entity_type"], "entity_ref": row["entity_ref"], "content": row["content"]} for row in authorities]

        result = run(value, upstream)
        self.assertEqual(result["runtime_status"], "ok")
        entities = result["payload"]["machine_entities"]
        context = next(row for row in entities if row["entity_type"] == "test_analysis_context")
        risks = {row["entity_ref"]: row for row in entities if row["entity_type"] == "product_risk"}
        deps = {(row["entity_type"], row["entity_ref"]): row for row in context["upstream_entity_dependencies"]}
        self.assertEqual(context["content"]["authority_refs"], ["SPEC-001", "SPEC-002"])
        self.assertEqual(context["content"]["risk_refs"], ["R-001", "R-002"])
        self.assertEqual(set(deps), {("authority", "SPEC-001"), ("authority", "SPEC-002"), ("product_risk", "R-001"), ("product_risk", "R-002")})
        for authority in authorities:
            self.assertEqual(deps[("authority", authority["entity_ref"])]["content_fingerprint"], authority["content_fingerprint"])
        for risk_ref, risk in risks.items():
            self.assertEqual(deps[("product_risk", risk_ref)]["content_fingerprint"], risk["content_fingerprint"])

        reordered = copy.deepcopy(value)
        reordered["test_analysis_context"]["authority_refs"].reverse()
        reordered["test_analysis_context"]["risk_refs"].reverse()
        same = run(reordered, upstream)
        same_context = next(row for row in same["payload"]["machine_entities"] if row["entity_type"] == "test_analysis_context")
        self.assertEqual(same_context["content"], context["content"])
        self.assertEqual(same_context["content_fingerprint"], context["content_fingerprint"])
        self.assertEqual(same_context["upstream_entity_dependencies"], context["upstream_entity_dependencies"])

    def test_context_supports_empty_authority_risk_and_combined_reference_sets(self) -> None:
        authority = runtime.make_machine_entity("spec-analysis", "authority", "SPEC-001", {"authority_id": "SPEC-001"})
        upstream = [{"skill": authority["skill"], "entity_type": authority["entity_type"], "entity_ref": authority["entity_ref"], "content": authority["content"]}]
        cases = [
            ([], [], []),
            (["SPEC-001"], [], upstream),
            ([], ["R-001"], []),
            (["SPEC-001"], ["R-001"], upstream),
        ]
        for authority_refs, risk_refs, rows in cases:
            with self.subTest(authority_refs=authority_refs, risk_refs=risk_refs):
                value = valid_input()
                value["test_analysis_context"]["authority_refs"] = authority_refs
                value["test_analysis_context"]["risk_refs"] = risk_refs
                result = run(value, rows)
                self.assertEqual(result["runtime_status"], "ok")
                context = next(row for row in result["payload"]["machine_entities"] if row["entity_type"] == "test_analysis_context")
                self.assertEqual({(row["entity_type"], row["entity_ref"]) for row in context["upstream_entity_dependencies"]},
                                 ({("authority", "SPEC-001")} if authority_refs else set()) | ({("product_risk", "R-001")} if risk_refs else set()))

    def test_context_duplicate_refs_unknown_risk_and_caller_fingerprint_are_invalid(self) -> None:
        for field in ("authority_refs", "risk_refs"):
            value = valid_input()
            value["test_analysis_context"][field] = ["R-001", "R-001"]
            with self.subTest(field=field):
                self.assertEqual(run(value)["runtime_status"], "invalid_input")

        unknown_risk = valid_input()
        unknown_risk["test_analysis_context"]["risk_refs"] = ["R-404"]
        self.assertEqual(run(unknown_risk)["runtime_status"], "invalid_input")

        injected = valid_input()
        injected["test_analysis_context"]["risk_refs"] = [{"risk_id": "R-001", "content_fingerprint": "sha256:" + "f" * 64}]
        self.assertEqual(run(injected)["runtime_status"], "invalid_input")

    def test_context_artifact_mode_rejects_unknown_or_missing_authority_entities(self) -> None:
        value = valid_input()
        value["test_analysis_context"]["authority_refs"] = ["SPEC-001"]
        other = runtime.make_machine_entity("spec-analysis", "authority", "SPEC-OTHER", {"authority_id": "SPEC-OTHER"})
        upstream = [{"skill": other["skill"], "entity_type": other["entity_type"], "entity_ref": other["entity_ref"], "content": other["content"]}]
        self.assertEqual(run(value, upstream, input_mode="artifact")["runtime_status"], "invalid_input")
        self.assertEqual(run(value, input_mode="artifact")["runtime_status"], "invalid_input")

    def test_context_direct_mode_resolves_authority_refs_to_passed_current_entities(self) -> None:
        value = valid_input()
        value["test_analysis_context"]["authority_refs"] = ["SPEC-001"]
        authority = runtime.make_machine_entity("spec-analysis", "authority", "SPEC-001", {"authority_id": "SPEC-001"})
        upstream = [{"skill": authority["skill"], "entity_type": authority["entity_type"], "entity_ref": authority["entity_ref"], "content": authority["content"]}]
        result = run(value, upstream)
        self.assertEqual(result["runtime_status"], "ok")
        context = next(row for row in result["payload"]["machine_entities"] if row["entity_type"] == "test_analysis_context")
        self.assertEqual([(row["entity_type"], row["entity_ref"]) for row in context["upstream_entity_dependencies"]], [("authority", "SPEC-001")])

    def test_context_direct_mode_rejects_unpassed_authority_ref(self) -> None:
        value = valid_input()
        value["test_analysis_context"]["authority_refs"] = ["SPEC-UNMATERIALIZED"]
        self.assertEqual(run(value)["runtime_status"], "invalid_input")

        value["test_analysis_context"]["authority_refs"] = ["SPEC-001", "SPEC-UNMATERIALIZED"]
        authority = runtime.make_machine_entity("spec-analysis", "authority", "SPEC-001", {"authority_id": "SPEC-001"})
        upstream = [{"skill": authority["skill"], "entity_type": authority["entity_type"], "entity_ref": authority["entity_ref"], "content": authority["content"]}]
        self.assertEqual(run(value, upstream)["runtime_status"], "invalid_input")

    def test_context_freshness_tracks_only_referenced_risk_content(self) -> None:
        old_input = valid_input()
        second = {**copy.deepcopy(old_input["product_risks"][0]), "risk_id": "R-002", "failure": "inventory mismatch"}
        old_input["product_risks"].append(second)
        old_input["risk_matrix_results"].append({"risk_id": "R-002", "level": "中", "mapped_priority": "中"})
        old_input["test_analysis_context"]["risk_refs"] = ["R-001"]
        old = run(old_input)
        old_entities = old["payload"]["machine_entities"]
        old_context = next(row for row in old_entities if row["entity_type"] == "test_analysis_context")

        unrelated_change = copy.deepcopy(old_input)
        unrelated_change["product_risks"][1]["failure"] = "changed unrelated risk"
        current_unrelated = run(unrelated_change)["payload"]["machine_entities"]
        rows = [{**row, "runtime_dependencies": []} for row in current_unrelated if row["entity_type"] != "test_analysis_context"] + [{**old_context, "runtime_dependencies": []}]
        state = {row["entity_ref"]: row["freshness_status"] for row in runtime.evaluate_entity_freshness(rows, {}) if row["entity_type"] == "test_analysis_context"}
        self.assertEqual(state["analysis-context:all"], "current")

        referenced_change = copy.deepcopy(old_input)
        referenced_change["product_risks"][0]["failure"] = "changed referenced risk"
        current_referenced = run(referenced_change)["payload"]["machine_entities"]
        rows = [{**row, "runtime_dependencies": []} for row in current_referenced if row["entity_type"] != "test_analysis_context"] + [{**old_context, "runtime_dependencies": []}]
        state = {row["entity_ref"]: row["freshness_status"] for row in runtime.evaluate_entity_freshness(rows, {}) if row["entity_type"] == "test_analysis_context"}
        self.assertEqual(state["analysis-context:all"], "stale")

    def test_authority_change_stales_only_context_that_references_it(self) -> None:
        authority_a = runtime.make_machine_entity("spec-analysis", "authority", "SPEC-A", {"authority_id": "SPEC-A", "active_content": "old A"})
        authority_b = runtime.make_machine_entity("spec-analysis", "authority", "SPEC-B", {"authority_id": "SPEC-B", "active_content": "stable B"})
        upstream = [{"skill": row["skill"], "entity_type": row["entity_type"], "entity_ref": row["entity_ref"], "content": row["content"]} for row in (authority_a, authority_b)]

        def context_for(ref: str) -> dict:
            value = valid_input()
            value["test_analysis_context"]["authority_refs"] = [ref]
            entities = run(value, upstream)["payload"]["machine_entities"]
            return next(row for row in entities if row["entity_type"] == "test_analysis_context")

        old_a = context_for("SPEC-A")
        old_b = context_for("SPEC-B")
        current_a = runtime.make_machine_entity("spec-analysis", "authority", "SPEC-A", {"authority_id": "SPEC-A", "active_content": "new A"})
        current_b = runtime.make_machine_entity("spec-analysis", "authority", "SPEC-B", {"authority_id": "SPEC-B", "active_content": "stable B"})
        for old_context, expected in ((old_a, "stale"), (old_b, "current")):
            rows = [{**row, "runtime_dependencies": []} for row in (current_a, current_b, old_context)]
            freshness = runtime.evaluate_entity_freshness(rows, {})
            context_status = next(row["freshness_status"] for row in freshness if row["entity_type"] == "test_analysis_context")
            self.assertEqual(context_status, expected)

    def test_environment_conflict_reaches_workflow_completion(self) -> None:
        environment_rows = [
            {"requirement_key": "browser-a", "environment_key": "web", "dimension_key": "browser", "operator": "eq", "authority_refs": [], "source_model_key": None, "source_target_versions": [], "value": {"type": "string", "value": "chromium"}},
            {"requirement_key": "browser-b", "environment_key": "web", "dimension_key": "browser", "operator": "eq", "authority_refs": [], "source_model_key": None, "source_target_versions": [], "value": {"type": "string", "value": "firefox"}},
        ]
        environment = run_runtime(ENVIRONMENT_SCRIPT, environment_metadata(), {"requirements": environment_rows})
        self.assertEqual(environment["result_status"], "unresolved")
        self.assertTrue(any(issue["issue_type"] == "environment_conflict" and issue["blocking"] for issue in environment["issues"]))

        analysis_input = valid_input()
        analysis_input["product_risks"] = []
        analysis_input["technique_selections"] = []
        analysis_input["change_nodes"] = []
        analysis_input["change_edges"] = []
        analysis_input["environment_requirements"] = environment["payload"]["normalized_requirements"]
        analysis_input["risk_matrix_results"] = []
        analysis_input["technique_candidate_results"] = []
        analysis_input["current_runtime_units"] = [{"skill": environment["skill"], "runtime_unit_key": environment["runtime_unit_key"], "generation_fingerprint": environment["generation_fingerprint"]}]
        analysis = run(analysis_input)
        self.assertEqual(analysis["runtime_status"], "ok")
        self.assertTrue(any(row["entity_type"] == "environment_requirement" for row in analysis["payload"]["machine_entities"]))

        workflow_metadata = {
            "envelope_version": "1", "skill": "qa-workflow", "runtime_contract_version": "runtime-v1", "generator_contract_version": "workflow-runtime-v1",
            "runtime_unit_key": "artifact:workflow_runtime:all", "model_key": None, "model_type": None, "technique_slug": None, "selection_source": None, "selection_key": None,
            "scope_key": "all", "input_mode": "artifact", "upstream_entities": [], "upstream_runtime_units": [], "static_data_versions": {}, "authority_refs": [], "reference_refs": [],
        }
        runtime_rows = [runtime.runtime_unit_row(environment), runtime.runtime_unit_row(analysis)]
        workflow = run_runtime(WORKFLOW_SCRIPT, workflow_metadata, {
            "workflow_scopes": [{"skill": "test-analysis", "target": None, "execution_range": None, "input_mode": "direct", "normalized_input": analysis_input, "current_structure_state": {"runtime_results": [], "carry_forward_entities": [], "previous_ci_id_state": []}}],
            "runtime_units": runtime_rows, "current_runtime_units": runtime_rows, "current_entities": analysis["payload"]["machine_entities"], "unsupported_item_closures": [],
        })
        self.assertEqual(workflow["runtime_status"], "ok")
        self.assertEqual(workflow["result_status"], "unresolved")
        self.assertFalse(workflow["payload"]["can_complete"])

    def test_risk_change_stales_only_selection_that_references_that_risk(self) -> None:
        old_input = valid_input()
        old_risk = old_input["product_risks"][0]
        old_risk["risk_id"] = "R-001"
        second_risk = {**old_risk, "risk_id": "R-002", "failure": "inventory mismatch"}
        old_input["product_risks"] = [old_risk, second_risk]
        old_input["risk_matrix_results"] = [{"risk_id": "R-001", "level": "高", "mapped_priority": "高"}, {"risk_id": "R-002", "level": "中", "mapped_priority": "中"}]
        first_selection = old_input["technique_selections"][0]
        second_selection = {**first_selection, "selection_key": "selection-002", "risk_refs": ["R-002"], "selection_reason": "inventory risk"}
        old_input["technique_selections"] = [first_selection, second_selection]
        candidate = old_input["technique_candidate_results"][0]
        old_input["technique_candidate_results"] = [candidate, {**candidate, "selection_key": "selection-002"}]
        old = run(old_input)
        self.assertEqual(old["runtime_status"], "ok")
        old_entities = old["payload"]["machine_entities"]

        new_input = copy.deepcopy(old_input)
        new_input["product_risks"][0]["failure"] = "payment total mismatch after rounding"
        current = run(new_input)
        self.assertEqual(current["runtime_status"], "ok")
        current_entities = [row for row in current["payload"]["machine_entities"] if row["entity_type"] != "technique_selection"]
        current_entities.extend(row for row in old_entities if row["entity_type"] == "technique_selection")
        current_entities = [{**row, "runtime_dependencies": []} for row in current_entities]
        freshness = runtime.evaluate_entity_freshness(current_entities, {})
        status = {row["entity_ref"]: row["freshness_status"] for row in freshness if row["entity_type"] == "technique_selection"}
        self.assertEqual(status["selection-001"], "stale")
        self.assertEqual(status["selection-002"], "current")


if __name__ == "__main__":
    unittest.main()
