from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = ROOT / "skills/wcag-conformance-evaluation/scripts"
sys.path.insert(0, str(SCRIPT_DIR))
import wcag_em_structure as structure
from wcag_requirements import load_catalog


def base_inputs() -> dict:
    return {"artifact_ref": "WCAG-EVAL-17", "artifact_revision": "rev-9", "evaluator": "evaluator-ref",
        "evaluation_date": "2026-09-28", "live_web_target": "https://fixture.invalid/", "commissioner": "self-evaluation",
        "wcag_version": "2.2", "level": "AA", "product_scope": "fixture product", "product_enclosure": "scope-ref",
        "accessibility_support_baseline": ["baseline-entry"], "browser_user_agent_baseline": ["browser-ref"],
        "role_permission_environment": ["environment-ref"], "side_effect_scope": "fixture only",
        "cleanup_scope": "reset fixture", "evaluation_period": "2026-09-28"}


def variation(sample: str, *, completeness: str = "complete", required=True, source_ref="AUTH-1") -> dict:
    return {"sample_ref": sample, "draft_key": "draft-" + sample, "source_kind": "project-authority",
        "source_ref": source_ref, "state_identity": "desktop-initial", "variation_description": "Desktop presentation",
        "presentation_condition": "viewport at desktop width", "environment_ref": "ENV-1",
        "viewport_condition_refs": ["VIEWPORT-1"], "responsive_condition_refs": [], "required": required,
        "completeness": completeness, "evidence_refs": ["E-1"]}


def claim_input(version: str = "2.2", level: str = "A") -> tuple[dict, dict]:
    catalog = load_catalog(version)
    pages = ["https://fixture.invalid/", "https://fixture.invalid/cart"]
    scope = {"description": "All fixture pages", "uris": pages,
        "scope_expression": None, "includes_subdomains": False}
    required = {"claim_date": "2026-09-28", "guideline_title": catalog["claim_contract"]["guideline_title"],
        "guideline_version": version, "guideline_uri": catalog["claim_contract"]["guideline_uri"],
        "conformance_level": level, "page_scope": scope, "technologies_relied_upon": ["HTML", "CSS"]}
    level_order = {"A": 1, "AA": 2, "AAA": 3}
    criteria = [row for row in catalog["success_criteria"] if level_order[row["level"]] <= level_order[level]]
    scope_evidence = {"coverage_method": "all-pages-evaluated", "scope_ref": "SCOPE-1",
        "scope_population_complete": True, "covered_page_uris": pages, "claim_level": level,
        "success_criterion_results": [{"page_uri": page, "criterion_ref": row["criterion_ref"],
            "result_ref": f"RESULT-{page.rsplit('/', 1)[-1]}-{row['criterion_ref']}",
            "result": "satisfied", "freshness_status": "current", "evidence_refs": [f"E-{page.rsplit('/', 1)[-1]}-{row['criterion_ref']}"]}
            for page in pages for row in criteria],
        "conformance_requirement_results": [{"page_uri": page, "requirement_key": row["requirement_key"],
            "result_ref": f"REQ-{page.rsplit('/', 1)[-1]}-{row['requirement_key']}",
            "result": "satisfied", "freshness_status": "current", "evidence_refs": [f"E-{page.rsplit('/', 1)[-1]}-{row['requirement_key']}"]}
            for page in pages for row in catalog["conformance_requirements"]],
        "complete_process_evidence_refs": [], "evidence_refs": ["E-SCOPE"]}
    return required, scope_evidence


class WcagEvaluationIdentityTests(unittest.TestCase):
    def test_initialization_preserves_current_artifact_identity_instead_of_minting_a_fixed_id(self):
        result = structure.initialize_evaluation(base_inputs())
        self.assertEqual(result["status"], "ready")
        self.assertEqual((result["evaluation_ref"], result["revision"]), ("WCAG-EVAL-17", "rev-9"))
        self.assertEqual(len(result["scope_coverage"]), len(structure.SCOPE_ROWS))
        missing = base_inputs()
        missing.pop("artifact_revision")
        blocked = structure.initialize_evaluation(missing)
        self.assertEqual(blocked["status"], "unresolved")
        self.assertIn("artifact_revision", blocked["blockers"][0]["fields"])
        invalid_date = {**base_inputs(), "evaluation_date": "not-a-date"}
        self.assertEqual(structure.initialize_evaluation(invalid_date)["status"], "unresolved")


class WcagAdditionalRequirementAndVariationTests(unittest.TestCase):
    def draft(self, *, in_scope=True, reason=None, evidence=None, closure=None, outputs=None):
        return {"draft_key": "request-1", "requester": "commissioner-ref", "request_text": "Report a new required view",
            "purpose_in_scope": in_scope, "out_of_scope_reason": reason, "affected_steps": ["2.3", "5.1"],
            "semantic_completion_condition": "The view and report section are linked",
            "required_evidence_refs": evidence or ["E-REQ"], "closure_evidence_refs": closure or [], "output_refs": outputs or []}

    def test_in_scope_requirement_stays_blocked_until_evidence_and_outputs_close(self):
        pending = structure.materialize_additional_requirements([self.draft()])[0]
        self.assertEqual((pending["additional_requirement_ref"], pending["status"]), ("ADDREQ-001", "blocked"))
        closed = structure.materialize_additional_requirements([self.draft(closure=["E-REQ"], outputs=["REPORT-SECTION-2.3"])])[0]
        self.assertEqual(closed["status"], "applied")
        missing_reason = structure.materialize_additional_requirements([self.draft(in_scope=False)])[0]
        self.assertEqual((missing_reason["status"], missing_reason["blocker"]), ("blocked", "explicit_out_of_scope_reason_required"))
        explicit = structure.materialize_additional_requirements([self.draft(in_scope=False, reason="outside_wcag_em_evaluation_purpose")])[0]
        self.assertEqual(explicit["status"], "out-of-scope")

    def test_variation_rows_keep_identity_and_incomplete_inventory_out_of_success(self):
        rows = structure.materialize_variations([{"sample_ref": "S1"}, {"sample_ref": "S2"}],
            [variation("S1"), variation("S2", completeness="incomplete")])
        self.assertEqual([row["variation_ref"] for row in rows], ["VAR-001", "VAR-002"])
        self.assertTrue(rows[0]["identity_fingerprint"].startswith("sha256:"))
        self.assertEqual([row["coverage_status"] for row in rows], ["required", "undetermined"])
        unreachable = structure.materialize_variations([{"sample_ref": "S1"}], [variation("S1", completeness="unreachable")])
        self.assertEqual(unreachable[0]["coverage_status"], "blocked")
        with self.assertRaises(structure.EvaluationStructureError):
            structure.materialize_variations([{"sample_ref": "S1"}], [variation("S1", required="false")])
        with self.assertRaises(structure.EvaluationStructureError):
            structure.materialize_variations([{"sample_ref": "S1"}, {"sample_ref": "S2"}], [variation("S1")])


class WcagStatementAndClaimTests(unittest.TestCase):
    def test_evaluation_statement_is_target_version_level_date_and_owner_guarded(self):
        args = {"version": "2.2", "status": "full", "all_methodology_complete": True,
            "all_samples_conform": True, "owner_commitment_ref": "OWNER-COMMIT", "product_scope": "scope-ref",
            "technologies": ["HTML", "CSS"], "baseline_ref": "BASELINE-1", "issued_date": "2026-09-28",
            "level": "AA", "scope_ref": "SCOPE-1"}
        full = structure.evaluation_statement(**args)
        self.assertEqual((full["status"], full["statement_type"], full["conformance_level"]), ("generated", "full", "AA"))
        self.assertEqual(structure.evaluation_statement(**{**args, "version": "2.1"})["status"], "not-generated")
        partial = structure.evaluation_statement(**{**args, "status": "partial", "all_samples_conform": False,
            "nonconforming_areas": [{"area_ref": "AREA-1", "description": "uncontrolled comments",
                "reason": "third-party-content", "outside_author_control": True, "user_identifiable": True,
                "rest_conforms": True, "evidence_refs": ["E-AREA"]}]})
        self.assertEqual(partial["status"], "generated")
        unsafe = structure.evaluation_statement(**{**args, "status": "partial", "all_samples_conform": False,
            "nonconforming_areas": [{"area_ref": "AREA-1", "description": "uncontrolled comments",
                "reason": "third-party-content", "outside_author_control": False, "user_identifiable": True,
                "rest_conforms": True, "evidence_refs": ["E-AREA"]}]})
        self.assertEqual(unsafe["status"], "blocked")

    def test_partial_conformance_statement_has_fixed_canonical_language_and_evidence(self):
        case = structure.statement_of_partial_conformance(version="2.2", level="AA", statement_type="third-party-content",
            parts_or_languages=[{"part_ref": "PART-1", "description": "uncontrolled comments",
                "outside_author_control": True, "user_identifiable": True, "would_conform_if_removed": True,
                "supporting_evidence_refs": ["E-PART"]}])
        self.assertEqual(case["status"], "generated")
        self.assertEqual(case["canonical_statement"], "This page does not conform, but would conform to WCAG 2.2 at level AA if the following parts from uncontrolled sources were removed: uncontrolled comments.")
        language = structure.statement_of_partial_conformance(version="2.1", level="A", statement_type="language",
            parts_or_languages=[{"language_ref": "LANG-1", "language_name": "Example language",
                "accessibility_support_missing": True, "would_conform_if_supported": True,
                "supporting_evidence_refs": ["E-LANG"]}])
        self.assertIn("accessibility support existed for the following language(s): Example language.", language["canonical_statement"])
        self.assertEqual(structure.statement_of_partial_conformance(version="2.2", level="AA", statement_type="other",
            parts_or_languages=[])["status"], "blocked")

    def test_claim_requires_exact_version_catalog_coverage_current_results_and_claim_scope(self):
        fields, scope_evidence = claim_input()
        result = structure.conformance_claim(version="2.2", full_scope_evidence=True, required_fields=fields,
            scope_evidence=scope_evidence)
        self.assertEqual(result["status"], "generated")
        missing = structure.conformance_claim(version="2.2", full_scope_evidence=True,
            required_fields={**fields, "page_scope": {**fields["page_scope"], "uris": []}}, scope_evidence=scope_evidence)
        self.assertEqual(missing["status"], "not-generated")
        incomplete = {**scope_evidence, "success_criterion_results": scope_evidence["success_criterion_results"][1:]}
        self.assertEqual(structure.conformance_claim(version="2.2", full_scope_evidence=True, required_fields=fields,
            scope_evidence=incomplete)["status"], "not-generated")
        wrong_page = {**scope_evidence, "success_criterion_results": [
            {**scope_evidence["success_criterion_results"][0], "page_uri": "https://outside.invalid/"},
            *scope_evidence["success_criterion_results"][1:]]}
        self.assertEqual(structure.conformance_claim(version="2.2", full_scope_evidence=True, required_fields=fields,
            scope_evidence=wrong_page)["status"], "not-generated")
        assurance = {**scope_evidence, "coverage_method": "assurance-process",
            "complete_process_evidence_refs": ["PROCESS-COVERAGE-1"]}
        self.assertEqual(structure.conformance_claim(version="2.2", full_scope_evidence=True,
            required_fields=fields, scope_evidence=assurance)["status"], "generated")
        third_party = {"all_affected_pages_identified": True, "affected_page_refs": ["PAGE-3"],
            "monitoring_possible": True, "repair_window_business_days": 2, "repair_evidence_refs": ["E-REPAIR"]}
        self.assertEqual(structure.conformance_claim(version="2.2", full_scope_evidence=True, required_fields=fields,
            third_party_content=third_party, scope_evidence=scope_evidence)["status"], "generated")
        third_party["repair_window_business_days"] = 3
        self.assertEqual(structure.conformance_claim(version="2.2", full_scope_evidence=True, required_fields=fields,
            third_party_content=third_party, scope_evidence=scope_evidence)["status"], "blocked")


class WcagConformanceRequirementTests(unittest.TestCase):
    def fixture(self, *, fail_criterion: str | None = None, variation_complete: bool = True,
                supported_usage: list[str] | None = None, process_complete: bool = True):
        version,level="2.2","A"
        catalog=load_catalog(version)
        target=structure.resolve_target(version,level)
        criteria=target["required_success_criteria"]
        results=[{"sample_result_ref":f"WCAG-RES-{index:03d}","sample_ref":"S1","variation_ref":"V1",
            "sample_kind":"structured","process_ref":"PROC-1" if process_complete else None,
            "requirement_ref":criterion,"criterion_evaluation_ref":f"CRIT-{criterion}",
            "result":"not-satisfied" if criterion==fail_criterion else "satisfied","freshness_status":"current",
            "observation_refs":[],"test_rule_result_refs":[],"evidence_refs":[f"E-{criterion}"],
            "unmet_example_refs":[f"EX-{criterion}"] if criterion==fail_criterion else [],"limitation":None}
            for index,criterion in enumerate(criteria,1)]
        samples=[{"sample_ref":"S1","sample_kind":"structured"}]
        variations=[{"sample_ref":"S1","variation_ref":"V1","required":True,
            "completeness":"complete" if variation_complete else "incomplete",
            "coverage_status":"required" if variation_complete else "undetermined",
            "identity_fingerprint":"sha256:"+"b"*64,"evidence_refs":["E-VARIATION"]}]
        processes=[{"process_ref":"PROC-1","sample_refs":["S1"]}] if process_complete else []
        baseline={"baseline_ref":"BASELINE-1","status":"complete","required_usage_refs":["USAGE-HTML"],
            "supported_usage_refs":supported_usage if supported_usage is not None else ["USAGE-HTML"],"evidence_refs":["E-BASELINE"]}
        return {"version":version,"level":level,"samples":samples,"variations":variations,"sample_results":results,
            "complete_processes":processes,"process_inventory_complete":True if process_complete else False,
            "process_inventory_evidence_refs":["E-PROCESS"] if process_complete else [],
            "accessibility_support_baseline":baseline}

    def run_closure(self, case, alternates=None):
        return structure.materialize_conformance_requirement_results(**case,alternate_version_results=alternates or [])

    def result(self, output, key):
        return next(row for row in output["results"] if row["requirement_ref"]==key)

    def test_five_conformance_requirements_close_from_current_versioned_result_sets(self):
        output=self.run_closure(self.fixture())
        self.assertEqual(output["status"],"ready")
        self.assertEqual(len(output["results"]),5)
        self.assertTrue(all(row["result"]=="satisfied" for row in output["results"]))
        self.assertEqual(self.result(output,"non-interference")["success_criterion_refs"],
            sorted(load_catalog("2.2")["conformance_requirements"][-1]["metadata"]["success_criterion_refs"]))

    def test_missing_or_stale_criterion_and_incomplete_variation_cannot_close(self):
        missing_case=self.fixture()
        missing_case["sample_results"]=missing_case["sample_results"][1:]
        missing=self.run_closure(missing_case)
        self.assertEqual(missing["status"],"unresolved")
        self.assertTrue(missing["missing_sample_criterion_rows"])
        stale_case=self.fixture()
        stale_case["sample_results"][0]["freshness_status"]="stale"
        stale=self.run_closure(stale_case)
        self.assertEqual(self.result(stale,"conformance-level")["result"],"undetermined")
        self.assertTrue(stale["stale_sample_criterion_rows"])
        incomplete=self.run_closure(self.fixture(variation_complete=False))
        self.assertEqual(self.result(incomplete,"full-pages")["result"],"undetermined")

    def test_non_satisfied_target_criterion_fails_level_and_process_and_alternate_can_satisfy(self):
        failed=self.run_closure(self.fixture(fail_criterion="1.1.1"))
        self.assertEqual(self.result(failed,"conformance-level")["result"],"not-satisfied")
        self.assertEqual(self.result(failed,"complete-processes")["result"],"not-satisfied")
        catalog=load_catalog("2.2")
        target=structure.resolve_target("2.2","A")
        conditions=[{"condition_key":key,"result":"satisfied","freshness_status":"current","evidence_refs":[f"E-{key}"]}
            for key in catalog["conforming_alternate_version_contract"]["required_condition_keys"]]
        criteria=[{"criterion_ref":criterion,"result_ref":f"ALT-{criterion}","result":"satisfied",
            "freshness_status":"current","evidence_refs":[f"EA-{criterion}"]} for criterion in target["required_success_criteria"]]
        alternate=structure.close_conforming_alternate_version(version="2.2",level="A",primary_sample_ref="S1",
            alternate_version_ref="ALT-VERSION-1",condition_results=conditions,criterion_results=criteria)
        self.assertEqual(alternate["status"],"satisfied")
        closed=self.run_closure(self.fixture(fail_criterion="1.1.1"),[alternate])
        self.assertEqual(self.result(closed,"conformance-level")["result"],"satisfied")
        self.assertEqual(self.result(closed,"full-pages")["result"],"satisfied")
        forged={"primary_sample_ref":"S1","alternate_version_ref":"ALT-FAKE","status":"satisfied"}
        with self.assertRaisesRegex(structure.EvaluationStructureError,"linked to a current primary sample"):
            self.run_closure(self.fixture(fail_criterion="1.1.1"),[forged])

    def test_accessibility_supported_baseline_and_process_inventory_are_required(self):
        unsupported=self.run_closure(self.fixture(supported_usage=[]))
        self.assertEqual(self.result(unsupported,"accessibility-supported-ways")["result"],"not-satisfied")
        missing_process=self.run_closure(self.fixture(process_complete=False))
        self.assertEqual(self.result(missing_process,"complete-processes")["result"],"undetermined")


class WcagReportClosureTests(unittest.TestCase):
    def closure(self):
        steps = {step: "complete" for step in structure.REPORT_STEPS}
        steps.update({"1.4": "not-applicable", "3.2": "not-applicable", "4.3": "not-applicable"})
        accessible = {key: True for key in structure.ACCESSIBLE_OUTPUT_CHECKS}
        return structure.close_report(required_steps=list(structure.REPORT_STEPS), step_outcomes=steps,
            sample_results=[{"requirement_ref": "1.1.1", "result": "not-satisfied"}],
            example_coverage={"1.1.1": ["EXAMPLE-1"]}, accessible_output_closure=accessible)

    def test_step_5_1_requires_all_fixed_step_outcomes_examples_and_accessible_output_closure(self):
        result = self.closure()
        self.assertEqual(result["status"], "complete")
        self.assertIsNone(result["aggregated_score"])
        missing = self.closure()
        missing["accessible_output_closure"].pop("table_headers", None)
        blocked = structure.close_report(required_steps=list(structure.REPORT_STEPS),
            step_outcomes={key:value for key,value in {step:"complete" for step in structure.REPORT_STEPS}.items() if key!="4.2"},
            sample_results=[{"requirement_ref":"1.1.1","result":"not-satisfied"}], example_coverage={},
            accessible_output_closure={key:True for key in structure.ACCESSIBLE_OUTPUT_CHECKS})
        self.assertEqual(blocked["status"], "blocked")
        self.assertIn("4.2", blocked["missing_step_outcomes"])
        self.assertEqual(blocked["not_satisfied_requirements_without_example"], ["1.1.1"])
        no_accessibility = structure.close_report(required_steps=list(structure.REPORT_STEPS),
            step_outcomes={step:"complete" for step in structure.REPORT_STEPS}, sample_results=[], example_coverage={},
            accessible_output_closure={key:True for key in structure.ACCESSIBLE_OUTPUT_CHECKS if key!="table_headers"})
        self.assertEqual(no_accessibility["status"], "blocked")
        self.assertIn("table_headers", no_accessibility["accessible_output_missing_checks"])

    def test_report_renderer_uses_fixed_order_and_derives_accessible_output_checks(self):
        data={"evaluation_input":{"evaluation_ref":"WCAG-EVAL-1","revision":"r1","evaluator":"person-ref",
            "commissioner":"self-evaluation","issued_date":"2026-09-28","evaluation_period":"2026-09-28",
            "wcag_title":"Web Content Accessibility Guidelines (WCAG) 2.2","wcag_version":"2.2",
            "wcag_uri":"https://www.w3.org/TR/WCAG22/","conformance_level":"AA","product_scope":"fixture",
            "project_authority_refs":[],"release_gate":None,"previous_evaluation_ref":None},
            "scope_rows":[],"exploration_rows":[],"sampling_procedure":[],"structured_samples":[],"random_sample":[],
            "complete_processes":[],"criterion_plan":[],"sample_results":[],"comparisons":[],"evaluation_outcomes":[],
            "handoffs":[],"limitations":[],"report_closure":{"status":"blocked"}}
        output=structure.render_machine_owned_report(data)
        self.assertEqual(output["status"],"generated")
        self.assertEqual(output["accessible_output_closure"],{key:True for key in structure.ACCESSIBLE_OUTPUT_CHECKS})
        markdown=output["machine_owned_markdown"]
        self.assertIn("| report closure | blocked |",markdown)
        self.assertLess(markdown.index("## Step 1:"),markdown.index("## Step 2:"))
        self.assertLess(markdown.index("## Step 2:"),markdown.index("## Step 3:"))
        self.assertLess(markdown.index("## Step 3:"),markdown.index("## Step 4:"))
        self.assertLess(markdown.index("## Step 4:"),markdown.index("## Step 5:"))
        self.assertIsNone(output["summary"]["aggregated_score"])
        data["report_closure"]["status"]="complete"
        data["sample_lineage"]={"status":"ready","previous_sample_refs":["STRUCT-OLD"],
            "current_structured_sample_refs":["SAMPLE-001"],"retained":[],"replaced":[],
            "added":["SAMPLE-001"],"unavailable":[{"previous_sample_ref":"STRUCT-OLD",
                "reason":"previous-identity-not-supplied"}]}
        complete=structure.render_machine_owned_report(data)
        self.assertIn("| report closure | complete |",complete["machine_owned_markdown"])
        self.assertIn("### Rerun Sample Lineage",complete["machine_owned_markdown"])
        self.assertIn("| STRUCT-OLD | unavailable | - | previous-identity-not-supplied |",
                      complete["machine_owned_markdown"])
        self.assertIn("| - | added | SAMPLE-001 | - |",complete["machine_owned_markdown"])
        self.assertEqual(structure.validate_accessible_markdown("# Report\n\n## Section\n\n![ ](image.png)\n")["status"],"blocked")


if __name__ == "__main__":
    unittest.main()
