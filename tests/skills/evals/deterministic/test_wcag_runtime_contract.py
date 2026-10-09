from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "skills/wcag-conformance-evaluation/scripts/wcag_runtime.py"
RUNTIME = ROOT / "skills/wcag-conformance-evaluation/scripts/runtime_contract.py"
DOCUMENT_IDENTITY = "hmac-sha256:" + "a" * 64


def load_runtime():
    spec = importlib.util.spec_from_file_location("wcag_runtime_contract_freshness_test", RUNTIME)
    if spec is None or spec.loader is None:
        raise ImportError(RUNTIME)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


runtime_contract = load_runtime()
sys.path.insert(0, str(SCRIPT.parent))
import wcag_em_structure


def metadata() -> dict:
    return {"envelope_version": "1", "skill": "wcag-conformance-evaluation",
        "runtime_contract_version": "runtime-v1", "generator_contract_version": "wcag-em-runtime-v1",
        "runtime_unit_key": "artifact:wcag_runtime:all", "model_key": None, "model_type": None,
        "technique_slug": None, "selection_source": None, "selection_key": None, "scope_key": "all",
        "input_mode": "direct", "upstream_entities": [], "upstream_runtime_units": [],
        "static_data_versions": {}, "authority_refs": [], "reference_refs": []}


def request(level: str) -> dict:
    return {"metadata": metadata(), "input": {"operation": "materialize-criterion-plan", "arguments": {
        "wcag_version": "2.0", "level": level,
        "samples": [{"sample_ref": "SAMPLE-001", "identity_fingerprint": "sha256:" + "a" * 64,
                     "target_identity": DOCUMENT_IDENTITY}],
        "variations": [{"sample_ref": "SAMPLE-001", "variation_ref": "VAR-001",
                        "identity_fingerprint": "sha256:" + "b" * 64}]}}}


def close_input() -> dict:
    sys.path.insert(0, str(SCRIPT.parent))
    import wcag_criterion_plan
    plan = wcag_criterion_plan.materialize_plan(wcag_version="2.0", level="A",
        samples=[{"sample_ref": "SAMPLE-001", "identity_fingerprint": "sha256:" + "a" * 64,
                  "target_identity": DOCUMENT_IDENTITY}],
        variations=[{"sample_ref": "SAMPLE-001", "variation_ref": "VAR-001",
                     "identity_fingerprint": "sha256:" + "b" * 64}])
    criterion = next(row for row in plan["criteria"] if row["criterion_ref"] == "1.1.1")
    procedure_results = {}
    machine_evidence = []
    semantic_execution = next(row for row in criterion["procedure_executions"] if row["procedure_key"].startswith("s-wcag-"))
    for execution in criterion["procedure_executions"]:
        if execution is semantic_execution:
            continue
        evidence_ref = "E-" + execution["procedure_execution_ref"]
        machine_evidence.append(evidence_ref)
        procedure_results[execution["procedure_execution_ref"]] = {"status": "complete", "applicability": "applicable",
            "result": "fixed probe observation complete", "evidence_refs": [evidence_ref]}
    procedure_results[semantic_execution["procedure_execution_ref"]] = {"status": "complete", "applicability": "applicable",
        "result": "semantic judgment complete", "evidence_refs": machine_evidence + ["E-SEMANTIC"]}
    return {"operation": "close-criterion", "arguments": {"result": criterion,
        "procedure_results": procedure_results, "applicable_population": "present", "semantic_result": "satisfied",
        "reason": "required current procedure evidence supports this fixture judgment", "evidence_refs": ["E-POP"]}}


def invoke(body: dict) -> dict:
    result = subprocess.run([sys.executable, str(SCRIPT)], input=json.dumps(body), text=True,
        cwd=ROOT, capture_output=True, check=False)
    if result.returncode not in {0, 1}:
        raise AssertionError(result.stdout + result.stderr)
    return json.loads(result.stdout)


class WcagRuntimeContractTests(unittest.TestCase):
    def test_close_report_runtime_keeps_required_steps_and_results_fail_closed(self):
        outcomes = {step: "complete" for step in wcag_em_structure.REPORT_STEPS}
        outcomes.update({"1.4": "not-applicable", "3.2": "not-applicable", "4.3": "not-applicable"})
        accessible = {key: True for key in wcag_em_structure.ACCESSIBLE_OUTPUT_CHECKS}
        args = {
            "required_steps": list(wcag_em_structure.REPORT_STEPS),
            "step_outcomes": {step: "not-applicable" for step in wcag_em_structure.REPORT_STEPS},
            "sample_results": [],
            "required_criterion_evaluation_refs": [],
            "example_coverage": {},
            "accessible_output_closure": accessible,
        }
        body = request("A")
        body["input"] = {"operation": "close-report", "arguments": args}
        forged = invoke(body)
        self.assertEqual(forged["runtime_status"], "ok")
        self.assertEqual(forged["payload"]["result"]["status"], "blocked")
        self.assertEqual(forged["payload"]["result"]["incomplete_required_steps"],
                         list(wcag_em_structure.REPORT_STEPS))

        args["required_steps"] = [step for step in wcag_em_structure.REPORT_STEPS
                                  if outcomes[step] == "complete"]
        args["step_outcomes"] = outcomes
        args["sample_results"] = [{"sample_result_ref": "WCAG-RES-1",
            "criterion_evaluation_ref": "CE-1", "requirement_ref": "1.1.1",
            "result": "satisfied", "freshness_status": "current"}]
        args["required_criterion_evaluation_refs"] = ["CE-1"]
        valid_not_applicable = invoke(body)
        self.assertEqual(valid_not_applicable["runtime_status"], "ok")
        self.assertEqual(valid_not_applicable["payload"]["result"]["status"], "complete")

    def test_runtime_allocates_monotonic_artifact_local_handoff_refs(self):
        body = request("A")
        body["input"] = {"operation": "allocate-observation-handoff-ref", "arguments": {
            "existing_handoffs": []}}
        first = invoke(body)
        self.assertEqual(first["runtime_status"], "ok")
        self.assertEqual(first["payload"]["result"]["handoff_ref"], "HANDOFF-001")

        body["input"]["arguments"]["existing_handoffs"] = [
            {"handoff_ref": "HANDOFF-001", "status": "closed"},
            {"handoff_ref": "HANDOFF-003", "status": "closed"},
        ]
        after_gap = invoke(body)
        self.assertEqual(after_gap["payload"]["result"]["handoff_ref"], "HANDOFF-004")

        for rows in ([{"handoff_ref": "HANDOFF-001"}, {"handoff_ref": "HANDOFF-001"}],
                     [{"handoff_ref": "HANDOFF-x"}], [None]):
            body["input"]["arguments"]["existing_handoffs"] = rows
            invalid = invoke(body)
            self.assertEqual(invalid["runtime_status"], "invalid_input")

    def test_runtime_exposes_scope_process_reuse_and_step_4_3_contracts(self):
        body=request("A")
        body["input"]={"operation":"materialize-scope-coverage","arguments":{"drafts":[
            {"scope_key":key,"decision":"out-of-product","reason":"No such product area is present",
             "evidence_refs":["E-"+key]} for key in
            ("third-party-content","language-versions","responsive-device-variations",
             "separately-hosted-product-areas","authenticated-restricted-views")]}}
        scope=invoke(body)
        self.assertEqual(scope["result_status"],"ready")
        self.assertEqual(len(scope["payload"]["result"]["scope_coverage"]),5)

        body["input"]={"operation":"materialize-complete-processes","arguments":{
            "samples":[{"sample_ref":"SAMPLE-001"},{"sample_ref":"SAMPLE-002"}],
            "selected_sample_refs":["SAMPLE-001"],"process_drafts":[{"process_key":"flow",
                "starting_point_ref":"SAMPLE-001","start_condition":"Visitor opens the landing page.",
                "default_sequence_refs":["SAMPLE-001","SAMPLE-002"],"critical_branch_sequences":[],
                "completion_condition":"The destination page is displayed.","evidence_refs":["E-PROCESS"]}]}}
        process=invoke(body)
        self.assertEqual(process["result_status"],"ready")
        self.assertEqual(process["payload"]["result"]["process_added_sample_refs"],["SAMPLE-002"])

        body["input"]={"operation":"evaluate-step-4-2-reuse","arguments":{
            "evaluation_items":[{"item_ref":"CONTENT-1","item_kind":"unchanged-content",
                "identity_fingerprint":"sha256:"+"a"*64,"evidence_fingerprint":"sha256:"+"b"*64}],
            "existing_results":[]}}
        reuse=invoke(body)
        self.assertEqual(reuse["result_status"],"ready")
        self.assertEqual(reuse["payload"]["result"]["reevaluate_item_refs"],["CONTENT-1"])

        sys.path.insert(0,str(SCRIPT.parent))
        from sampling import candidate_population_fingerprint
        candidates=[{"sample_ref":f"SAMPLE-{index:03d}","sample_identity":f"identity-{index:03d}"}
                    for index in range(1,31)]
        provenance={"inventory":"all-target","revision":1}
        prior={"structured_revision":1,"structured_sample_refs":[f"SAMPLE-{index:03d}" for index in range(1,11)],
            "random_samples":[{"sample_ref":"SAMPLE-012","freshness_status":"current"}],
            "candidate_population_fingerprint":candidate_population_fingerprint(candidates,provenance),
            "selection_method":"system-random finite inventory selection"}
        body["input"]={"operation":"reconcile-sampling-revision","arguments":{
            "previous_iteration":prior,"current_structured_revision":2,
            "current_structured_sample_refs":[f"SAMPLE-{index:03d}" for index in range(1,12)],
            "candidates":candidates,"provenance":provenance}}
        reconciliation=invoke(body)
        self.assertEqual(reconciliation["runtime_status"],"ok")
        self.assertEqual(reconciliation["result_status"],"unresolved")
        self.assertEqual(reconciliation["payload"]["result"]["random_selection_required_count"],1)

    def test_runtime_materializes_previous_structured_sample_lineage(self):
        body=request("A")
        body["input"]={"operation":"materialize-sample-identities","arguments":{"drafts":[
            {"draft_key":"new-view","target_ref":"TARGET-NEW","state_key":"default",
             "target_identity":"hmac-sha256:"+"a"*64,
             "source_evidence_refs":["E-CURRENT"]}]}}
        current=invoke(body)
        self.assertEqual(current["result_status"],"ready")
        registry=current["payload"]["result"]
        body["input"]={"operation":"materialize-sample-lineage","arguments":{
            "previous_sample_refs":["STRUCT-OLD"],"previous_identity_rows":[],
            "current_identity_registry":registry,
            "current_structured_sample_refs":[registry["samples"][0]["sample_ref"]]}}
        lineage=invoke(body)
        self.assertEqual(lineage["runtime_status"],"ok")
        self.assertEqual(lineage["result_status"],"ready")
        self.assertEqual(lineage["payload"]["result"]["unavailable"],[
            {"previous_sample_ref":"STRUCT-OLD","reason":"previous-identity-not-supplied"}])
        self.assertEqual(lineage["payload"]["result"]["added"],[registry["samples"][0]["sample_ref"]])

    def test_formal_baseline_extension_is_revisioned_but_diagnostic_environment_is_not_added(self):
        body = request("A")
        body["input"] = {"operation": "extend-accessibility-support-baseline", "arguments": {
            "baseline_ref": "BASELINE-1", "revision": 2,
            "environment_refs": ["ENV-BASE"],
            "formal_evidence_environment_refs": ["ENV-BASE", "ENV-FORMAL"],
            "diagnostic_only_environment_refs": ["ENV-DIAGNOSTIC"],
            "extension_reason": "Used for an adopted formal result",
            "sample_results":[
                {"sample_result_ref":"RESULT-FORMAL","baseline_revision":2,"environment_refs":["ENV-FORMAL"],"freshness_status":"current"},
                {"sample_result_ref":"RESULT-BASE","baseline_revision":2,"environment_refs":["ENV-BASE"],"freshness_status":"current"},
                {"sample_result_ref":"RESULT-DIAGNOSTIC","baseline_revision":2,"environment_refs":["ENV-DIAGNOSTIC"],"freshness_status":"current"}]}}
        extended = invoke(body)
        self.assertEqual(extended["result_status"], "ready")
        result = extended["payload"]["result"]
        self.assertEqual(result["status"], "extended")
        self.assertEqual(result["revision"], 3)
        self.assertEqual(result["previous_baseline_ref"], "BASELINE-1")
        self.assertEqual(result["environment_refs"], ["ENV-BASE", "ENV-FORMAL"])
        self.assertNotIn("ENV-DIAGNOSTIC", result["environment_refs"])
        self.assertEqual(result["stale_sample_result_refs"],["RESULT-FORMAL"])

    def test_formal_baseline_extension_requires_reason_and_never_promotes_diagnostic_only(self):
        body = request("A")
        arguments = {"baseline_ref": "BASELINE-1", "revision": 2,
            "environment_refs": ["ENV-BASE"],
            "formal_evidence_environment_refs": ["ENV-BASE"],
            "diagnostic_only_environment_refs": ["ENV-DIAGNOSTIC"],
            "extension_reason": None,"sample_results":[]}
        body["input"] = {"operation": "extend-accessibility-support-baseline", "arguments": arguments}
        unchanged = invoke(body)
        self.assertEqual(unchanged["result_status"], "ready")
        unchanged_result = unchanged["payload"]["result"]
        self.assertEqual(unchanged_result["status"], "unchanged")
        self.assertEqual(unchanged_result["revision"], 2)
        self.assertNotIn("ENV-DIAGNOSTIC", unchanged_result["environment_refs"])

        arguments["formal_evidence_environment_refs"] = ["ENV-BASE", "ENV-NEW"]
        blocked = invoke(body)
        self.assertEqual(blocked["result_status"], "blocked")
        self.assertEqual(blocked["payload"]["result"]["status"], "blocked")
        self.assertEqual(blocked["payload"]["result"]["blocker"], "formal_baseline_extension_reason_required")

    def test_formal_baseline_extension_rejects_environment_role_overlap(self):
        body = request("A")
        body["input"] = {"operation": "extend-accessibility-support-baseline", "arguments": {
            "baseline_ref": "BASELINE-1", "revision": 1,
            "environment_refs": [], "formal_evidence_environment_refs": ["ENV-1"],
            "diagnostic_only_environment_refs": ["ENV-1"], "extension_reason": "formal", "sample_results":[]}}
        output = invoke(body)
        self.assertEqual(output["runtime_status"], "invalid_input")

    def test_runtime_materializes_plan_with_pr11_fingerprints_and_approved_static_inputs(self):
        output = invoke(request("A"))
        self.assertEqual(output["runtime_status"], "ok")
        self.assertEqual(output["result_status"], "ready")
        self.assertTrue(output["deterministic_generated"])
        self.assertEqual(output["runtime_unit_key"], "artifact:wcag_runtime:all")
        self.assertTrue(output["input_fingerprint"].startswith("sha256:"))
        self.assertTrue(output["generation_fingerprint"].startswith("sha256:"))
        self.assertEqual(set(output["static_data_versions"]), {"wcag_requirements_2_0", "wcag_requirements_2_1",
            "wcag_requirements_2_2", "wcag_evaluation_procedures", "wcag_semantic_contracts"})
        self.assertNotIn("wcag_machine_probes", output["static_data_versions"])
        payload = output["payload"]["result"]
        self.assertEqual(payload["wcag_version"], "2.0")
        self.assertEqual(payload["level"], "A")
        self.assertEqual(len(payload["criteria"]), payload["expected_row_count"])

    def test_multi_probe_procedure_rows_retain_every_fixed_request(self):
        body = request("AAA")
        body["input"]["arguments"].update({"wcag_version": "2.2"})
        output = invoke(body)
        self.assertEqual(output["runtime_status"], "ok")
        plan = output["payload"]["result"]
        expected = {
            "1.4.11": ["mp-target-geometry", "mp-computed-color-context"],
            "2.4.13": ["mp-focus-appearance-evidence", "mp-target-geometry", "mp-computed-color-context"],
        }
        for criterion_ref, probe_keys in expected.items():
            criterion = next(row for row in plan["criteria"] if row["criterion_ref"] == criterion_ref)
            machine = next(row for row in criterion["procedure_executions"] if row["procedure_kind"] == "machine")
            requests = {row["observation_request_ref"]: row for row in plan["requests"]}
            linked_requests = [requests[ref] for ref in machine["observation_request_refs"]]
            self.assertEqual(sorted(row["machine_probe_key"] for row in linked_requests), sorted(probe_keys))
            self.assertEqual({row["procedure_execution_ref"] for row in linked_requests},
                             {machine["procedure_execution_ref"]})

    def test_runtime_generation_changes_make_saved_formal_result_stale(self):
        saved = invoke(request("A"))
        same = invoke(request("A"))
        changed = invoke(request("AA"))
        saved_row = runtime_contract.runtime_unit_row(saved)
        same_row = runtime_contract.runtime_unit_row(same)
        current_row = runtime_contract.runtime_unit_row(changed)
        current, issues = runtime_contract.evaluate_runtime_unit_freshness(
            [saved_row], [same_row], [], recursive_upstream_skills=set())
        self.assertEqual(current[0]["freshness_status"], "current")
        self.assertEqual(issues, [])
        stale, stale_issues = runtime_contract.evaluate_runtime_unit_freshness(
            [saved_row], [current_row], [], recursive_upstream_skills=set())
        self.assertEqual(stale[0]["freshness_status"], "stale")
        self.assertTrue(any(row["issue_type"] == "current_runtime_generation_mismatch" for row in stale_issues))

    def test_formal_probe_consumer_requires_inspection_runtime_dependency(self):
        body = request("A")
        row = {"skill": "usability-inspection", "runtime_unit_key": "artifact:inspection_runtime:formal-machine-probe",
               "generation_fingerprint": "sha256:" + "c" * 64}
        body["metadata"]["upstream_runtime_units"] = [row]
        body["input"] = close_input()
        output = invoke(body)
        self.assertEqual(output["runtime_status"], "ok")
        self.assertEqual(output["result_status"], "ready")
        self.assertNotIn("wcag_machine_probes", output.get("static_data_versions", {}))
        missing = request("A")
        missing["input"] = body["input"]
        missing_output = invoke(missing)
        self.assertEqual(missing_output["runtime_status"], "invalid_input")

    def test_sample_results_json_boundary_accepts_ref_arrays_and_discards_untrusted_rows(self):
        close_metadata = metadata()
        close_metadata["upstream_runtime_units"] = [{"skill": "usability-inspection",
            "runtime_unit_key": "artifact:inspection_runtime:formal-machine-probe",
            "generation_fingerprint": "sha256:" + "c" * 64}]
        closed = invoke({"metadata": close_metadata, "input": close_input()})
        self.assertEqual(closed["runtime_status"], "ok")
        criterion_result = closed["payload"]["result"]
        criterion_ref = criterion_result["criterion_evaluation_ref"]

        body = request("A")
        body["input"] = {"operation": "materialize-sample-results", "arguments": {
            "criterion_rows": [criterion_result, {
                "criterion_evaluation_ref": "LLM-SUPPLIED-ROW",
                "sample_ref": "SAMPLE-001",
                "variation_ref": "VAR-001",
                "criterion_ref": "1.1.1",
                "execution_status": "complete",
                "result": "satisfied",
                "evidence_refs": ["E-UNTRUSTED"],
            }],
            "current_criterion_evaluation_refs": [criterion_ref],
            "sample_kinds": {"SAMPLE-001": "structured"},
        }}
        output = invoke(body)
        self.assertEqual(output["runtime_status"], "ok")
        self.assertEqual(output["result_status"], "ready")
        materialized = output["payload"]["result"]
        self.assertEqual(len(materialized), 1)
        self.assertEqual(materialized[0]["criterion_evaluation_ref"], criterion_ref)
        self.assertNotIn("LLM-SUPPLIED-ROW", {row["criterion_evaluation_ref"] for row in materialized})

        body["input"]["arguments"]["current_criterion_evaluation_refs"] = [criterion_ref, criterion_ref]
        duplicate_refs = invoke(body)
        self.assertEqual(duplicate_refs["runtime_status"], "invalid_input")

        body["input"]["arguments"]["current_criterion_evaluation_refs"] = []
        body["input"]["arguments"]["sample_kinds"] = {}
        untrusted_only = invoke(body)
        self.assertEqual(untrusted_only["runtime_status"], "ok")
        self.assertEqual(untrusted_only["payload"]["result"], [])


if __name__ == "__main__":
    unittest.main()
