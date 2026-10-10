from __future__ import annotations

import importlib.util
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "skills/wcag-conformance-evaluation/scripts/wcag_runtime.py"
WORKFLOW_SCRIPT = ROOT / "skills/qa-workflow/scripts/workflow_runtime.py"
RUNTIME = ROOT / "skills/wcag-conformance-evaluation/scripts/runtime_contract.py"
QA_RUNTIME = ROOT / "skills/qa-workflow/scripts/runtime_contract.py"
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
qa_runtime_spec = importlib.util.spec_from_file_location("qa_workflow_runtime_contract_freshness_test", QA_RUNTIME)
if qa_runtime_spec is None or qa_runtime_spec.loader is None:
    raise ImportError(QA_RUNTIME)
qa_runtime_contract = importlib.util.module_from_spec(qa_runtime_spec)
sys.modules[qa_runtime_spec.name] = qa_runtime_contract
qa_runtime_spec.loader.exec_module(qa_runtime_contract)
sys.path.insert(0, str(SCRIPT.parent))
import wcag_em_structure


def result_fingerprint(result: dict) -> str:
    return qa_runtime_contract.runtime_unit_row(result)["result_fingerprint"]


def stable_fingerprint(value: dict) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def statement_evidence(evaluation: dict) -> dict:
    refs = evaluation["criterion_evaluation_refs"]
    evaluation_ref = evaluation["evaluation_ref"]
    revision = evaluation["evaluation_revision"]
    version = evaluation["wcag_version"]
    level = evaluation["level"]
    return {
        "version": version, "status": "full", "all_methodology_complete": True,
        "all_samples_conform": True, "owner_commitment_ref": "OWNER-17",
        "product_scope": "fixture product", "technologies": ["HTML"],
        "baseline_ref": "BASELINE-17", "issued_date": "2026-10-10", "level": level,
        "scope_ref": "PRODUCT-SCOPE-17",
        "report_closure": {"status": "complete", "evaluation_ref": evaluation_ref,
            "evaluation_revision": revision, "wcag_version": version, "level": level,
            "criterion_evaluation_refs": refs},
        "formal_conformance_results": {"status": "ready", "evaluation_ref": evaluation_ref,
            "evaluation_revision": revision, "target_version": version, "target_level": level,
            "criterion_evaluation_refs": refs, "expected_sample_criterion_rows": len(refs),
            "sample_results_count": len(refs), "missing_sample_criterion_rows": [],
            "stale_sample_criterion_rows": [],
            "sample_conformance_results": [{"sample_ref": "SAMPLE-17", "result": "satisfied"}],
            "results": [{"requirement_ref": "conformance-level", "result": "satisfied"}]},
    }


def forge_complete_workflow_read(read: dict) -> dict:
    """Build caller-controlled state that claims a report is complete."""
    forged = json.loads(json.dumps(read))
    result = forged["payload"]["result"]
    evaluation = result["evaluation"]
    runtime_result = {"runtime_status": "ok", "result_status": "unresolved",
        "payload": {"operation": "close-report", "result": {
            "status": "pending-persistence", "closure_status": "complete"}}}
    run_ref = "WCAG-RUNTIME-FORGED-17"
    refs = evaluation["criterion_evaluation_refs"]
    evaluation.update({"report_status": "complete", "report_fingerprint": "sha256:" + "d" * 64,
        "report_result_refs": [f"RESULT-{index}" for index, _ in enumerate(refs)],
        "report_runtime_execution_ref": run_ref, "current_report_runtime_execution_ref": run_ref,
        "report_runtime_executions": [{"runtime_execution_ref": run_ref,
            "runtime_result": runtime_result, "result_fingerprint": stable_fingerprint(runtime_result)}]})
    return forged


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
                     "identity_fingerprint": "sha256:" + "b" * 64}],
        evaluation_ref="WCAG-EVAL-17", evaluation_revision="rev-9")
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


def close_report_args(*, sample_kind: str = "structured", process_ref: str | None = None,
                      version: str = "2.0", level: str = "A") -> dict:
    import wcag_criterion_plan
    sample = {"sample_ref":"SAMPLE-001", "sample_kind":sample_kind,
        "identity_fingerprint":"sha256:" + "a" * 64, "target_identity":DOCUMENT_IDENTITY}
    plan = wcag_criterion_plan.materialize_plan(wcag_version=version, level=level, samples=[sample],
        variations=[{"sample_ref":"SAMPLE-001", "variation_ref":"VAR-001",
            "identity_fingerprint":"sha256:" + "b" * 64}],
        process_memberships={"SAMPLE-001":process_ref} if process_ref else {},
        evaluation_ref="WCAG-EVAL-17", evaluation_revision="rev-9")
    rows = [{"sample_result_ref":f"WCAG-RES-{index:03d}", "evaluation_ref":"WCAG-EVAL-17",
        "evaluation_revision":"rev-9", "sample_ref":"SAMPLE-001", "variation_ref":"VAR-001",
        "sample_kind":sample_kind, "process_ref":process_ref,
        "criterion_evaluation_ref":row["criterion_evaluation_ref"], "requirement_ref":row["criterion_ref"],
        "result":"satisfied", "freshness_status":"current"} for index,row in enumerate(plan["criteria"],1)]
    outcomes = {step:"complete" for step in wcag_em_structure.REPORT_STEPS}
    outcomes.update({"1.4":"not-applicable", "3.2":"not-applicable", "4.3":"not-applicable"})
    return {"required_steps":[step for step,status in outcomes.items() if status=="complete"],
        "step_outcomes":outcomes, "sample_results":rows,
        "required_criterion_evaluation_refs":[row["criterion_evaluation_ref"] for row in plan["criteria"]],
        "canonical_criterion_plan":plan, "example_coverage":{},
        "accessible_output_closure":{key:True for key in wcag_em_structure.ACCESSIBLE_OUTPUT_CHECKS}}


def invoke(body: dict) -> dict:
    result = subprocess.run([sys.executable, str(SCRIPT)], input=json.dumps(body), text=True,
        cwd=ROOT, capture_output=True, check=False)
    if result.returncode not in {0, 1}:
        raise AssertionError(result.stdout + result.stderr)
    return json.loads(result.stdout)


def workflow_metadata(*, reference_refs: list[str], upstream_runtime_units: list[dict] | None = None) -> dict:
    return {"envelope_version": "1", "skill": "qa-workflow", "runtime_contract_version": "runtime-v1",
        "generator_contract_version": "workflow-runtime-v1", "runtime_unit_key": "artifact:workflow_runtime:all",
        "model_key": None, "model_type": None, "technique_slug": None, "selection_source": None,
        "selection_key": None, "scope_key": "all", "input_mode": "artifact", "upstream_entities": [],
        "upstream_runtime_units": upstream_runtime_units or [], "static_data_versions": {},
        "authority_refs": [], "reference_refs": reference_refs}


def invoke_workflow(body: dict) -> dict:
    result = subprocess.run([sys.executable, str(WORKFLOW_SCRIPT)], input=json.dumps(body), text=True,
        cwd=ROOT, capture_output=True, check=False)
    if result.returncode not in {0, 1}:
        raise AssertionError(result.stdout + result.stderr)
    return json.loads(result.stdout)


class WcagRuntimeContractTests(unittest.TestCase):
    def test_runtime_rejects_a_criterion_plan_with_required_machine_procedures_removed(self):
        body = request("A")
        close = close_input()
        args = close["arguments"]
        executions = args["result"]["procedure_executions"]
        removed = [row for row in executions if row["procedure_kind"] == "machine"]
        args["result"]["procedure_executions"] = [row for row in executions if row["procedure_kind"] != "machine"]
        for row in removed:
            args["procedure_results"].pop(row["procedure_execution_ref"], None)
        body["input"] = close
        result = invoke(body)
        self.assertEqual(result["runtime_status"], "invalid_input")
        self.assertIn("execution set differs", result["issues"][0]["message"])

    def test_runtime_keeps_unfinished_statement_claim_and_random_selection_unresolved(self):
        body = request("A")
        body["input"] = {"operation":"evaluation-statement", "arguments":{
            "version":"2.2", "status":"full", "all_methodology_complete":True,
            "all_samples_conform":True, "owner_commitment_ref":"OWNER-1", "product_scope":"SCOPE-1",
            "technologies":["HTML"], "baseline_ref":"BASELINE-1", "issued_date":"2026-10-09",
            "level":"AA", "scope_ref":"SCOPE-1"}}
        statement = invoke(body)
        self.assertEqual(statement["payload"]["result"]["status"], "blocked")
        self.assertEqual(statement["result_status"], "blocked")

        body["input"]["arguments"].update({
            "report_closure": {"status": "complete", "evaluation_ref": "WCAG-EVAL-1",
                "evaluation_revision": "rev-1", "wcag_version": "2.2", "level": "AA",
                "criterion_evaluation_refs": ["CRIT-EVAL-1"]},
            "formal_conformance_results": {"status": "ready", "evaluation_ref": "WCAG-EVAL-1",
                "evaluation_revision": "rev-1", "target_version": "2.2", "target_level": "AA",
                "criterion_evaluation_refs": ["CRIT-EVAL-1"], "expected_sample_criterion_rows": 1,
                "sample_results_count": 1, "missing_sample_criterion_rows": [], "stale_sample_criterion_rows": [],
                "sample_conformance_results": [{"sample_ref": "SAMPLE-1", "result": "satisfied"}],
                "results": [{"requirement_ref": "conformance-level", "result": "satisfied"}]},
        })
        fabricated = invoke(body)
        self.assertEqual(fabricated["payload"]["result"]["status"], "blocked")
        self.assertEqual(fabricated["payload"]["result"]["reason"], "current_saved_wcag_report_required")
        self.assertEqual(fabricated["result_status"], "blocked")

        body["input"] = {"operation":"conformance-claim", "arguments":{
            "version":"2.2", "full_scope_evidence":True, "required_fields":{}, "scope_evidence":None}}
        claim = invoke(body)
        self.assertEqual(claim["payload"]["result"]["status"], "not-generated")
        self.assertEqual(claim["result_status"], "unresolved")

        body["input"] = {"operation":"validate-random-selection", "arguments":{
            "structured_refs":["S1","S2","S3"], "selected_refs":[], "target_count":0,
            "complete_inventory":False, "selection_method":"finite-random"}}
        random = invoke(body)
        self.assertEqual(random["runtime_status"], "invalid_input")

    def test_runtime_rejects_stale_earl_result_before_serialization(self):
        body = request("A")
        body["input"] = {"operation":"serialize-earl", "arguments":{
            "evaluation_ref":"WCAG-EVAL-1", "evaluation_revision":"rev-2", "version":"2.2",
            "results":[{"evaluation_ref":"WCAG-EVAL-1", "evaluation_revision":"rev-1",
                "freshness_status":"stale", "result":"satisfied"}],
            "evaluator_identity":"qa-agent", "tool_identity":"qa-workflow-skills",
            "sample_identities":{}, "variation_identities":{}}}
        output = invoke(body)
        self.assertEqual(output["runtime_status"], "invalid_input")

    def test_close_report_runtime_keeps_required_steps_and_results_fail_closed(self):
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
        self.assertEqual(forged["payload"]["result"]["reason"], "current_saved_wcag_evaluation_required")

        args.update(close_report_args())
        body["input"]["arguments"] = args
        valid_not_applicable = invoke(body)
        self.assertEqual(valid_not_applicable["runtime_status"], "ok")
        self.assertEqual(valid_not_applicable["result_status"], "blocked")
        self.assertEqual(valid_not_applicable["payload"]["result"]["status"], "blocked")

    def test_close_report_runtime_does_not_let_step_4_2_na_skip_step_4_1_results(self):
        args = close_report_args()
        args["required_steps"] = [step for step in args["required_steps"] if step != "4.1"]
        args["step_outcomes"]["4.2"] = "not-applicable"
        args["required_steps"] = [step for step in args["required_steps"] if step != "4.2"]
        args["sample_results"] = []
        args["required_criterion_evaluation_refs"] = None
        body = request("A")
        body["input"] = {"operation": "close-report", "arguments": args}
        blocked = invoke(body)
        self.assertEqual(blocked["runtime_status"], "ok")
        self.assertEqual(blocked["result_status"], "blocked")
        self.assertEqual(blocked["payload"]["result"]["status"], "blocked")
        self.assertEqual(blocked["payload"]["result"]["reason"], "current_saved_wcag_evaluation_required")

        narrowed = close_report_args()
        narrowed["required_steps"] = args["required_steps"]
        narrowed["step_outcomes"]["4.2"] = "not-applicable"
        narrowed["required_steps"] = [step for step in narrowed["required_steps"] if step != "4.2"]
        narrowed["sample_results"] = [narrowed["sample_results"][0]]
        narrowed["required_criterion_evaluation_refs"] = [narrowed["sample_results"][0]["criterion_evaluation_ref"]]
        body["input"]["arguments"] = narrowed
        narrowed_result = invoke(body)
        self.assertEqual(narrowed_result["payload"]["result"]["status"], "blocked")
        self.assertEqual(narrowed_result["payload"]["result"]["reason"], "current_saved_wcag_evaluation_required")

        complete_args = close_report_args()
        complete_args["required_steps"] = args["required_steps"]
        complete_args["step_outcomes"]["4.2"] = "not-applicable"
        complete_args["required_steps"] = [step for step in complete_args["required_steps"] if step != "4.2"]
        args = complete_args
        body["input"]["arguments"] = args
        complete = invoke(body)
        self.assertEqual(complete["runtime_status"], "ok")
        self.assertEqual(complete["result_status"], "blocked")
        self.assertEqual(complete["payload"]["result"]["reason"], "current_saved_wcag_evaluation_required")

        args = close_report_args(sample_kind="process-added", process_ref="PROC-1")
        args["step_outcomes"]["4.1"] = "not-applicable"
        args["required_steps"] = [step for step in args["required_steps"] if step != "4.1"]
        args["step_outcomes"]["4.2"] = "complete"
        if "4.2" not in args["required_steps"]:
            args["required_steps"].append("4.2")
        body["input"]["arguments"] = args
        process_complete = invoke(body)
        self.assertEqual(process_complete["runtime_status"], "ok")
        self.assertEqual(process_complete["result_status"], "blocked")
        self.assertEqual(process_complete["payload"]["result"]["reason"], "current_saved_wcag_evaluation_required")

    def test_saved_current_wcag_plan_closes_only_after_qa_workflow_cas_and_reread(self):
        import uuid
        workflow_ref = str(uuid.uuid4())
        with tempfile.TemporaryDirectory() as temp:
            state_root = Path(temp) / "qa-state"
            project_context = (
                "# Project Context\n\n"
                "<!-- qa-context-field:start key=qa.workflow_state_root type=path -->\n"
                f"{state_root}\n"
                "<!-- qa-context-field:end -->\n"
            )
            context_refs = ["PROJECT-CONTEXT-17"]
            close_args = close_report_args(version="2.2", level="AA")
            plan = close_args["canonical_criterion_plan"]
            evaluation_inputs = {
                "artifact_ref": "WCAG-EVAL-17", "artifact_revision": "rev-9",
                "evaluator": "EVALUATOR-17", "evaluation_date": "2026-10-10",
                "live_web_target": "https://fixture.invalid/", "commissioner": "COMMISSIONER-17",
                "wcag_version": "2.2", "level": "AA", "product_scope": "fixture product",
                "product_enclosure": "PRODUCT-SCOPE-17", "accessibility_support_baseline": ["BASELINE-17"],
                "browser_user_agent_baseline": ["BROWSER-17"], "role_permission_environment": ["ENV-17"],
                "side_effect_scope": "fixture only", "cleanup_scope": "reset fixture",
                "evaluation_period": "2026-10-10",
            }
            initialization = wcag_em_structure.initialize_evaluation(evaluation_inputs)
            scope_coverage = wcag_em_structure.materialize_scope_coverage([
                {"scope_key": key, "decision": "out-of-product", "reason": "not present in fixture",
                 "evidence_refs": [f"E-SCOPE-{index}"]}
                for index, key in enumerate(wcag_em_structure.SCOPE_ROWS, 1)
            ])
            source_artifacts = [
                {"artifact_ref": "WCAG-EVAL-17", "artifact_revision": "rev-9", "purpose": "evaluation"},
                {"artifact_ref": "PRODUCT-SCOPE-17", "artifact_revision": "scope-r1", "purpose": "scope"},
                {"artifact_ref": "SAMPLE-SET-17", "artifact_revision": "samples-r1", "purpose": "sample-selection"},
                {"artifact_ref": "VARIATION-SET-17", "artifact_revision": "variation-r1", "purpose": "variation"},
            ]
            registration = invoke_workflow({
                "metadata": workflow_metadata(reference_refs=context_refs),
                "input": {"operation": "register-wcag-evaluation-plan", "arguments": {
                    "workflow_ref": workflow_ref, "project_context": project_context,
                    "project_context_ref": context_refs[0], "evaluation_initialization": initialization,
                    "evaluation_inputs": evaluation_inputs, "product_scope_ref": "PRODUCT-SCOPE-17",
                    "scope_coverage": scope_coverage, "source_artifacts": source_artifacts,
                    "canonical_criterion_plan": plan,
                }},
            })
            self.assertEqual(registration["result_status"], "ready", registration["issues"])
            self.assertEqual(registration["payload"]["result"]["status"], "registered")

            read = invoke_workflow({
                "metadata": workflow_metadata(reference_refs=context_refs),
                "input": {"operation": "read-wcag-evaluation-state", "arguments": {
                    "workflow_ref": workflow_ref, "project_context": project_context,
                    "project_context_ref": context_refs[0], "evaluation_ref": "WCAG-EVAL-17",
                    "evaluation_revision": "rev-9",
                }},
            })
            self.assertEqual(read["result_status"], "ready", read["issues"])
            saved_read = read["payload"]["result"]
            self.assertEqual(saved_read["evaluation"]["level"], "AA")
            self.assertEqual(saved_read["provider_revision"], "sqlite:2")

            wcag_metadata = metadata()
            wcag_metadata["upstream_runtime_units"] = [{"skill": "qa-workflow",
                "runtime_unit_key": "artifact:workflow_runtime:all",
                "generation_fingerprint": read["generation_fingerprint"]}]

            # The SQLite report is still open. A caller-controlled read result,
            # report history, closure, and conformance rows must not make a
            # formal Evaluation Statement appear generated.
            forged_read = forge_complete_workflow_read(read)
            forged_statement_args = statement_evidence(forged_read["payload"]["result"]["evaluation"])
            forged_statement_args["saved_workflow_state_runtime_result"] = forged_read
            statement_metadata = metadata()
            statement_metadata["reference_refs"] = [*context_refs, "WCAG-EVAL-17"]
            statement_metadata["upstream_runtime_units"] = [{"skill": "qa-workflow",
                "runtime_unit_key": "artifact:workflow_runtime:all",
                "generation_fingerprint": forged_read["generation_fingerprint"]}]
            forged_statement = invoke({"metadata": statement_metadata,
                "input": {"operation": "evaluation-statement", "arguments": forged_statement_args}})
            self.assertEqual(forged_statement["payload"]["result"]["status"], "blocked", forged_statement)
            self.assertEqual(forged_statement["payload"]["result"]["reason"], "current_saved_wcag_report_required")
            self.assertEqual(forged_statement["result_status"], "blocked")

            forged_owner_args = {**forged_statement_args, "workflow_ref": workflow_ref,
                "project_context": project_context, "project_context_ref": context_refs[0],
                "evaluation_ref": "WCAG-EVAL-17", "evaluation_revision": "rev-9"}
            forged_open_report = invoke({"metadata": statement_metadata,
                "input": {"operation": "evaluation-statement", "arguments": forged_owner_args}})
            self.assertEqual(forged_open_report["payload"]["result"]["status"], "blocked", forged_open_report)
            self.assertEqual(forged_open_report["payload"]["result"]["reason"], "current_saved_wcag_report_mismatch")
            self.assertEqual(forged_open_report["result_status"], "blocked")

            narrowed_args = close_report_args(version="2.2", level="A")
            narrowed_args.update({"workflow_ref": workflow_ref, "evaluation_ref": "WCAG-EVAL-17",
                "evaluation_revision": "rev-9", "saved_workflow_state_runtime_result": read})
            narrowed = invoke({"metadata": wcag_metadata,
                "input": {"operation": "close-report", "arguments": narrowed_args}})
            self.assertNotEqual(narrowed["result_status"], "ready", narrowed)
            self.assertEqual(narrowed["payload"]["result"]["status"], "conflict")

            close_args.update({"workflow_ref": workflow_ref, "evaluation_ref": "WCAG-EVAL-17",
                "evaluation_revision": "rev-9", "saved_workflow_state_runtime_result": read})
            wcag_close = invoke({"metadata": wcag_metadata,
                "input": {"operation": "close-report", "arguments": close_args}})
            self.assertEqual(wcag_close["runtime_status"], "ok")
            self.assertEqual(wcag_close["result_status"], "unresolved", wcag_close)
            self.assertEqual(wcag_close["payload"]["result"]["status"], "pending-persistence")

            incomplete_close_args = dict(close_args)
            incomplete_close_args["step_outcomes"] = {**close_args["step_outcomes"], "4.1": "incomplete"}
            incomplete_close_args.update({"workflow_ref": workflow_ref, "evaluation_ref": "WCAG-EVAL-17",
                "evaluation_revision": "rev-9", "saved_workflow_state_runtime_result": read})
            incomplete_runtime = invoke({"metadata": wcag_metadata,
                "input": {"operation": "close-report", "arguments": incomplete_close_args}})
            self.assertEqual(incomplete_runtime["payload"]["result"]["status"], "blocked")
            closure_keys = ("required_steps", "step_outcomes", "example_coverage",
                            "required_criterion_evaluation_refs", "accessible_output_closure")
            incomplete_closure_inputs = {key: incomplete_close_args[key] for key in closure_keys}

            # Case A: qa-workflow itself runs the official WCAG runtime with the
            # incomplete Step 4.1 input, then stores that exact blocked result.
            incomplete_finalize = invoke_workflow({
                "metadata": workflow_metadata(reference_refs=context_refs),
                "input": {"operation": "finalize-wcag-report", "arguments": {
                    "workflow_ref": workflow_ref, "project_context": project_context,
                    "project_context_ref": context_refs[0], "expected_provider_revision": saved_read["provider_revision"],
                    "evaluation_ref": "WCAG-EVAL-17", "evaluation_revision": "rev-9",
                    "canonical_criterion_plan": plan, "sample_results": close_args["sample_results"],
                    "report_closure_inputs": incomplete_closure_inputs,
                }},
            })
            self.assertEqual(incomplete_finalize["result_status"], "blocked", incomplete_finalize)
            self.assertEqual(incomplete_finalize["payload"]["result"]["status"], "blocked")
            after_incomplete = invoke_workflow({
                "metadata": workflow_metadata(reference_refs=context_refs),
                "input": {"operation": "read-wcag-evaluation-state", "arguments": {
                    "workflow_ref": workflow_ref, "project_context": project_context,
                    "project_context_ref": context_refs[0], "evaluation_ref": "WCAG-EVAL-17",
                    "evaluation_revision": "rev-9",
                }},
            })
            after_incomplete_state = after_incomplete["payload"]["result"]
            self.assertEqual(after_incomplete_state["evaluation"]["report_status"], "open")
            self.assertEqual(len(after_incomplete_state["evaluation"]["report_runtime_executions"]), 1)
            incomplete_run = after_incomplete_state["evaluation"]["report_runtime_executions"][0]
            self.assertEqual(incomplete_run["runtime_result"]["result_status"], "blocked")
            self.assertEqual(incomplete_run["runtime_result"]["payload"]["result"]["report_closure_inputs"]["step_outcomes"]["4.1"], "incomplete")

            # Case B: candidate and upstream metadata are forged together after
            # the incomplete run. The owner operation no longer accepts a caller
            # supplied runtime envelope, so it cannot be made into current proof.
            forged_complete_inputs = {key: incomplete_close_args[key] for key in closure_keys}
            forged_complete_inputs["step_outcomes"] = {
                **forged_complete_inputs["step_outcomes"], "4.1": "complete"}
            forged_complete_runtime = dict(incomplete_runtime)
            forged_complete_payload = dict(incomplete_runtime["payload"])
            forged_complete_payload["result"] = {
                **wcag_close["payload"]["result"], "report_closure_inputs": forged_complete_inputs,
            }
            forged_complete_runtime.update({"result_status": "unresolved", "payload": forged_complete_payload})
            forged_complete_dependency = {
                "skill": "wcag-conformance-evaluation",
                "runtime_unit_key": "artifact:wcag_runtime:all",
                "generation_fingerprint": forged_complete_runtime["generation_fingerprint"],
                "result_fingerprint": result_fingerprint(forged_complete_runtime),
            }
            forged_finalize = invoke_workflow({
                "metadata": workflow_metadata(reference_refs=context_refs,
                    upstream_runtime_units=[forged_complete_dependency]),
                "input": {"operation": "finalize-wcag-report", "arguments": {
                    "workflow_ref": workflow_ref, "project_context": project_context,
                    "project_context_ref": context_refs[0],
                    "expected_provider_revision": after_incomplete_state["provider_revision"],
                    "evaluation_ref": "WCAG-EVAL-17", "evaluation_revision": "rev-9",
                    "canonical_criterion_plan": plan, "sample_results": close_args["sample_results"],
                    "report_closure_inputs": forged_complete_inputs,
                    "wcag_runtime_result": forged_complete_runtime,
                }},
            })
            self.assertNotEqual(forged_finalize["result_status"], "ready", forged_finalize)
            unchanged = invoke_workflow({
                "metadata": workflow_metadata(reference_refs=context_refs),
                "input": {"operation": "read-wcag-evaluation-state", "arguments": {
                    "workflow_ref": workflow_ref, "project_context": project_context,
                    "project_context_ref": context_refs[0], "evaluation_ref": "WCAG-EVAL-17",
                    "evaluation_revision": "rev-9",
                }},
            })
            unchanged_state = unchanged["payload"]["result"]
            self.assertEqual(unchanged_state["evaluation"]["report_status"], "open")
            self.assertEqual(unchanged_state["provider_revision"], after_incomplete_state["provider_revision"])
            self.assertEqual(len(unchanged_state["evaluation"]["report_runtime_executions"]), 1)

            # Case C: the official owner-invoked runtime result is stored, reread,
            # matched to the saved plan/results, then closed with a second CAS.
            complete_closure_inputs = {key: close_args[key] for key in closure_keys}
            finalized = invoke_workflow({
                "metadata": workflow_metadata(reference_refs=context_refs,
                    upstream_runtime_units=[forged_complete_dependency]),
                "input": {"operation": "finalize-wcag-report", "arguments": {
                    "workflow_ref": workflow_ref, "project_context": project_context,
                    "project_context_ref": context_refs[0],
                    "expected_provider_revision": unchanged_state["provider_revision"],
                    "evaluation_ref": "WCAG-EVAL-17", "evaluation_revision": "rev-9",
                    "canonical_criterion_plan": plan, "sample_results": close_args["sample_results"],
                    "report_closure_inputs": complete_closure_inputs,
                }},
            })
            self.assertEqual(finalized["result_status"], "ready", finalized)
            self.assertEqual(finalized["payload"]["result"]["status"], "complete")
            reread = invoke_workflow({
                "metadata": workflow_metadata(reference_refs=context_refs),
                "input": {"operation": "read-wcag-evaluation-state", "arguments": {
                    "workflow_ref": workflow_ref, "project_context": project_context,
                    "project_context_ref": context_refs[0], "evaluation_ref": "WCAG-EVAL-17",
                    "evaluation_revision": "rev-9",
                }},
            })
            final_state = reread["payload"]["result"]
            final_evaluation = final_state["evaluation"]
            self.assertEqual(final_evaluation["report_status"], "complete")
            self.assertEqual(final_state["provider_revision"], finalized["payload"]["result"]["provider_revision"])
            self.assertEqual(len(final_evaluation["report_runtime_executions"]), 2)
            current_run = final_evaluation["report_runtime_executions"][-1]
            self.assertEqual(final_evaluation["current_report_runtime_execution_ref"], current_run["runtime_execution_ref"])
            self.assertEqual(final_evaluation["report_runtime_execution_ref"], current_run["runtime_execution_ref"])
            self.assertEqual(current_run["runtime_result"]["payload"]["result"]["status"], "pending-persistence")
            self.assertEqual(current_run["runtime_result"]["payload"]["result"]["report_closure_inputs"]["step_outcomes"]["4.1"], "complete")
            self.assertEqual(current_run["result_fingerprint"], result_fingerprint(current_run["runtime_result"]))
            self.assertEqual(current_run["source_provider_revision"], after_incomplete_state["provider_revision"])

            statement_args = statement_evidence(final_evaluation)
            statement_args.update({"workflow_ref": workflow_ref, "project_context": project_context,
                "project_context_ref": context_refs[0], "evaluation_ref": "WCAG-EVAL-17",
                "evaluation_revision": "rev-9"})
            current_statement = invoke({"metadata": statement_metadata,
                "input": {"operation": "evaluation-statement", "arguments": statement_args}})
            self.assertEqual(current_statement["runtime_status"], "ok", current_statement)
            self.assertEqual(current_statement["result_status"], "ready", current_statement)
            self.assertEqual(current_statement["payload"]["result"]["status"], "generated")

    def test_runtime_dependency_freshness_checks_full_current_result_fingerprint(self):
        upstream = invoke(request("A"))
        upstream_row = qa_runtime_contract.runtime_unit_row(upstream)
        dependency = {
            "skill": upstream["skill"],
            "runtime_unit_key": upstream["runtime_unit_key"],
            "generation_fingerprint": upstream["generation_fingerprint"],
            "result_fingerprint": upstream_row["result_fingerprint"],
        }
        current_runtime_map = {(upstream["skill"], upstream["runtime_unit_key"]): upstream_row}
        self.assertEqual(qa_runtime_contract.compare_runtime_dependencies(
            {"upstream_runtime_units": [dependency]}, current_runtime_map), "current")
        self.assertEqual(qa_runtime_contract.compare_runtime_dependencies(
            {"upstream_runtime_units": [{key: value for key, value in dependency.items()
                                         if key != "result_fingerprint"}]}, current_runtime_map), "current")
        consumer = {
            "skill": "qa-workflow", "runtime_unit_key": "artifact:workflow_runtime:all",
            "runtime_status": "ok", "result_status": "ready", "support_status": "supported",
            "runtime_required": True, "deterministic_generated": True,
            "generation_fingerprint": "sha256:" + "d" * 64,
            "upstream_runtime_units": [dependency], "upstream_entity_fingerprints": [],
            "unsupported_items": [],
        }
        consumer_row = qa_runtime_contract.runtime_unit_row(consumer)
        current, issues = qa_runtime_contract.evaluate_runtime_unit_freshness(
            [consumer_row], [consumer_row, upstream_row], [], recursive_upstream_skills=set())
        self.assertEqual(current[0]["freshness_status"], "current")
        self.assertEqual(issues, [])

        changed_upstream = dict(upstream)
        changed_upstream["payload"] = {**upstream["payload"], "caller_tampered": True}
        changed_row = qa_runtime_contract.runtime_unit_row(changed_upstream)
        forged_dependency = {
            **dependency,
            "result_fingerprint": result_fingerprint(changed_upstream),
        }
        forged_consumer = {
            **consumer,
            "upstream_runtime_units": [forged_dependency],
        }
        forged_consumer_row = qa_runtime_contract.runtime_unit_row(forged_consumer)
        forged_stale, forged_issues = qa_runtime_contract.evaluate_runtime_unit_freshness(
            [forged_consumer_row], [forged_consumer_row, upstream_row], [], recursive_upstream_skills=set())
        self.assertEqual(forged_stale[0]["freshness_status"], "stale")
        self.assertTrue(any(issue["issue_type"] == "runtime_result_mismatch" for issue in forged_issues))
        changed_runtime_map = {(changed_upstream["skill"], changed_upstream["runtime_unit_key"]): changed_row}
        self.assertEqual(qa_runtime_contract.compare_runtime_dependencies(
            {"upstream_runtime_units": [dependency]}, changed_runtime_map), "stale")
        stale, stale_issues = qa_runtime_contract.evaluate_runtime_unit_freshness(
            [consumer_row], [consumer_row, changed_row], [], recursive_upstream_skills=set())
        self.assertEqual(stale[0]["freshness_status"], "stale")
        self.assertTrue(any(issue["issue_type"] == "runtime_result_mismatch" for issue in stale_issues))

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
