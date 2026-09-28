from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest


ROOT=Path(__file__).resolve().parents[4]
SCRIPTS=ROOT/"skills/wcag-conformance-evaluation/scripts"
sys.path.insert(0,str(SCRIPTS))
from sampling import (SamplingError, candidate_population_fingerprint, evaluate_step_4_2_reuse,
                      materialize_processes, reconcile_sampling_revision, select_random_candidates)
from wcag_em_structure import (EvaluationStructureError, SCOPE_ROWS, extend_accessibility_support_baseline,
                               materialize_scope_coverage)

VALIDATOR_PATH=ROOT/"skills/wcag-conformance-evaluation/evals/deterministic/validator.py"
_validator_spec=importlib.util.spec_from_file_location("wcag_independent_step_validator",VALIDATOR_PATH)
if _validator_spec is None or _validator_spec.loader is None: raise ImportError(VALIDATOR_PATH)
independent_validator=importlib.util.module_from_spec(_validator_spec)
sys.modules[_validator_spec.name]=independent_validator
_validator_spec.loader.exec_module(independent_validator)


def fp(label: str) -> str:
    return "sha256:"+hashlib.sha256(label.encode("utf-8")).hexdigest()


def inventory(count: int=30) -> list[dict[str,str]]:
    return [{"sample_ref":f"SAMPLE-{index:03d}","sample_identity":f"identity-{index:03d}"}
            for index in range(1,count+1)]


class WcagSamplingStepContractTests(unittest.TestCase):
    def test_scope_coverage_materializes_all_fixed_rows_and_keeps_unresolved_visible(self):
        drafts=[{"scope_key":key,"decision":"out-of-product","reason":"No product area exists in this category",
                 "evidence_refs":[f"E-{key}"]} for key in SCOPE_ROWS]
        drafts[2]={"scope_key":SCOPE_ROWS[2],"decision":"unresolved","reason":None,"evidence_refs":[]}
        result=materialize_scope_coverage(drafts)
        self.assertEqual(result["status"],"unresolved")
        self.assertEqual([row["scope_key"] for row in result["scope_coverage"]],list(SCOPE_ROWS))
        self.assertEqual(len(result["scope_coverage"]),5)
        self.assertEqual(result["unresolved_scope_refs"],["SCOPE-003"])
        incomplete=materialize_scope_coverage(drafts[:-1])
        self.assertEqual(incomplete["missing_scope_keys"],[SCOPE_ROWS[-1]])
        self.assertEqual(independent_validator.validate_scope_coverage(incomplete),[])

    def test_scope_coverage_requires_evidence_for_closed_boundaries(self):
        drafts=[{"scope_key":key,"decision":"in-scope","reason":None,"evidence_refs":["E-1"]}
                for key in SCOPE_ROWS]
        drafts[0]["evidence_refs"]=[]
        with self.assertRaises(EvaluationStructureError): materialize_scope_coverage(drafts)

    def test_independent_scope_validator_detects_forged_closure(self):
        drafts=[{"scope_key":key,"decision":"out-of-product","reason":"No such area",
                 "evidence_refs":[f"E-{key}"]} for key in SCOPE_ROWS]
        output=materialize_scope_coverage(drafts)
        self.assertEqual(independent_validator.validate_scope_coverage(output),[])
        output["scope_coverage"][0]["evidence_refs"]=[]
        self.assertIn("scope_coverage_closed_without_evidence:1",independent_validator.validate_scope_coverage(output))

    def test_baseline_revision_and_related_freshness_have_independent_validation(self):
        arguments={"baseline_ref":"BASELINE-1","revision":2,"environment_refs":["ENV-BASE"],
            "formal_evidence_environment_refs":["ENV-BASE","ENV-NEW"],
            "diagnostic_only_environment_refs":["ENV-DIAGNOSTIC"],"extension_reason":"Formal evidence used this environment",
            "sample_results":[{"sample_result_ref":"RESULT-1","baseline_revision":2,
                "environment_refs":["ENV-NEW"],"freshness_status":"current"}]}
        result=extend_accessibility_support_baseline(**arguments)
        self.assertEqual(independent_validator.validate_baseline_extension(arguments,result),[])
        forged={**result,"stale_sample_result_refs":[]}
        self.assertIn("baseline_related_result_freshness",
                      independent_validator.validate_baseline_extension(arguments,forged))

    def test_finite_random_selector_uses_unique_non_overlapping_refs_without_a_fixed_seed(self):
        result=select_random_candidates(candidates=inventory(),structured_refs=["SAMPLE-001","SAMPLE-002"],
            target_count=5,excluded_refs=["SAMPLE-003"])
        self.assertEqual(result["selection_status"],"target-met")
        self.assertEqual(len(result["selected_sample_refs"]),5)
        self.assertEqual(len(set(result["selected_sample_refs"])),5)
        self.assertFalse({"SAMPLE-001","SAMPLE-002","SAMPLE-003"}&set(result["selected_sample_refs"]))
        self.assertFalse(result["fixed_seed_used"])
        short=select_random_candidates(candidates=inventory(3),structured_refs=["SAMPLE-001"],target_count=5)
        self.assertEqual(short["selection_status"],"selection-incomplete")

    def test_non_deterministic_random_selection_production_cli(self):
        script=SCRIPTS/"select_random_samples.py"
        completed=subprocess.run([sys.executable,str(script)],input=json.dumps({
            "candidates":inventory(12),"structured_refs":["SAMPLE-001","SAMPLE-002"],
            "target_count":2,"excluded_refs":["SAMPLE-003"]}),text=True,cwd=ROOT,
            capture_output=True,check=False)
        self.assertEqual(completed.returncode,0,completed.stderr)
        result=json.loads(completed.stdout)
        self.assertEqual(result["selection_status"],"target-met")
        self.assertEqual(len(result["selected_sample_refs"]),2)
        self.assertFalse({"SAMPLE-001","SAMPLE-002","SAMPLE-003"}&set(result["selected_sample_refs"]))

    def test_process_sequences_derive_union_membership_and_process_added_samples(self):
        samples=[{"sample_ref":f"SAMPLE-{i:03d}"} for i in range(1,5)]
        result=materialize_processes(samples=samples,selected_sample_refs=["SAMPLE-001"],process_drafts=[{
            "process_key":"purchase","starting_point_ref":"SAMPLE-001",
            "default_sequence_refs":["SAMPLE-001","SAMPLE-002"],
            "critical_branch_sequences":[["SAMPLE-002","SAMPLE-003"],["SAMPLE-001","SAMPLE-004"]],
            "evidence_refs":["E-PROCESS"]}])
        process_arguments={"samples":samples,"selected_sample_refs":["SAMPLE-001"],
            "process_drafts":[{"process_key":"purchase","starting_point_ref":"SAMPLE-001",
                "default_sequence_refs":["SAMPLE-001","SAMPLE-002"],
                "critical_branch_sequences":[["SAMPLE-002","SAMPLE-003"],["SAMPLE-001","SAMPLE-004"]],
                "evidence_refs":["E-PROCESS"]}]}
        self.assertEqual(independent_validator.validate_process_materialization(process_arguments,result),[])
        self.assertEqual(result["status"],"ready")
        self.assertEqual(result["processes"][0]["sample_refs"],
                         ["SAMPLE-001","SAMPLE-002","SAMPLE-003","SAMPLE-004"])
        self.assertEqual(result["process_added_sample_refs"],["SAMPLE-002","SAMPLE-003","SAMPLE-004"])
        self.assertEqual(result["selected_sample_refs"],
                         ["SAMPLE-001","SAMPLE-002","SAMPLE-003","SAMPLE-004"])
        self.assertEqual(result["process_sample_memberships"]["SAMPLE-002"],["PROCESS-001"])
        forged={**result,"process_added_sample_refs":["SAMPLE-003"]}
        self.assertNotEqual(independent_validator.validate_process_materialization(process_arguments,forged),[])

    def test_step_4_2_reuses_only_current_unchanged_content_with_matching_identity_and_evidence(self):
        items=[]; prior=[]
        for name,kind,identity,evidence,freshness in [
            ("unchanged","unchanged-content",fp("same"),fp("evidence"),"current"),
            ("changed","changed-content",fp("new"),fp("evidence"),"current"),
            ("unknown","unknown-content",None,None,"current"),
            ("interaction","interaction",fp("action"),fp("action evidence"),"current"),
            ("stale","unchanged-content",fp("stale"),fp("stale evidence"),"stale"),
            ("evidence-change","unchanged-content",fp("same identity"),fp("new evidence"),"current")]:
            items.append({"item_ref":name,"item_kind":kind,"identity_fingerprint":identity,
                          "evidence_fingerprint":evidence})
            if name!="unknown":
                prior.append({"item_ref":name,"result_ref":f"RESULT-{name}",
                    "identity_fingerprint":fp("same") if name=="evidence-change" else identity,
                    "evidence_fingerprint":fp("evidence") if name=="evidence-change" else evidence,
                    "freshness_status":freshness})
        result=evaluate_step_4_2_reuse(evaluation_items=items,existing_results=prior)
        arguments={"evaluation_items":items,"existing_results":prior}
        self.assertEqual(independent_validator.validate_step_4_2_reuse(arguments,result),[])
        self.assertEqual(result["reusable_result_refs"],["RESULT-unchanged"])
        self.assertEqual(set(result["reevaluate_item_refs"]),{"changed","unknown","interaction","stale","evidence-change"})
        forged={**result,"reusable_result_refs":["RESULT-unchanged","RESULT-interaction"]}
        self.assertIn("step_4_2_reuse_set",independent_validator.validate_step_4_2_reuse(arguments,forged))

    def test_step_4_3_same_population_retains_only_current_nonoverlap_and_tops_up(self):
        candidates=inventory()
        provenance={"source":"complete-target-inventory","revision":4}
        population=candidate_population_fingerprint(candidates,provenance)
        prior={"structured_revision":1,"structured_sample_refs":[f"SAMPLE-{i:03d}" for i in range(1,11)],
            "random_samples":[{"sample_ref":"SAMPLE-012","freshness_status":"current"},
                              {"sample_ref":"SAMPLE-013","freshness_status":"stale"}],
            "candidate_population_fingerprint":population,"selection_method":"system-random finite inventory selection"}
        structured=[f"SAMPLE-{i:03d}" for i in range(1,12)]
        pending=reconcile_sampling_revision(previous_iteration=prior,current_structured_revision=2,
            current_structured_sample_refs=structured,candidates=candidates,provenance=provenance)
        pending_arguments={"previous_iteration":prior,"current_structured_revision":2,
            "current_structured_sample_refs":structured,"candidates":candidates,"provenance":provenance}
        self.assertEqual(independent_validator.validate_step_4_3_reconciliation(pending_arguments,pending),[])
        self.assertEqual(pending["status"],"selection-required")
        self.assertTrue(pending["population_unchanged"])
        self.assertEqual(pending["retained_random_sample_refs"],["SAMPLE-012"])
        self.assertEqual(pending["discarded_random_sample_refs"],["SAMPLE-013"])
        self.assertEqual(pending["random_selection_required_count"],1)
        closed=reconcile_sampling_revision(previous_iteration=prior,current_structured_revision=2,
            current_structured_sample_refs=structured,candidates=candidates,provenance=provenance,
            new_random_selection_refs=["SAMPLE-014"],selection_method="system-random finite inventory selection")
        closed_arguments={**pending_arguments,"new_random_selection_refs":["SAMPLE-014"],
            "selection_method":"system-random finite inventory selection"}
        self.assertEqual(independent_validator.validate_step_4_3_reconciliation(closed_arguments,closed),[])
        self.assertEqual(closed["status"],"target-met")
        self.assertEqual(closed["random_sample_refs"],["SAMPLE-012","SAMPLE-014"])

    def test_step_4_3_population_change_discards_old_random_set_and_requires_full_reselection(self):
        candidates=inventory()
        prior_provenance={"source":"complete-target-inventory","revision":4}
        changed_provenance={"source":"complete-target-inventory","revision":5}
        prior={"structured_revision":1,"structured_sample_refs":[f"SAMPLE-{i:03d}" for i in range(1,11)],
            "random_samples":[{"sample_ref":"SAMPLE-012","freshness_status":"current"}],
            "candidate_population_fingerprint":candidate_population_fingerprint(candidates,prior_provenance),
            "selection_method":"system-random finite inventory selection"}
        structured=[f"SAMPLE-{i:03d}" for i in range(1,12)]
        pending=reconcile_sampling_revision(previous_iteration=prior,current_structured_revision=2,
            current_structured_sample_refs=structured,candidates=candidates,provenance=changed_provenance)
        self.assertFalse(pending["population_unchanged"])
        self.assertEqual(pending["retained_random_sample_refs"],[])
        self.assertEqual(pending["discarded_random_sample_refs"],["SAMPLE-012"])
        self.assertEqual(pending["random_selection_required_count"],2)
        closed=reconcile_sampling_revision(previous_iteration=prior,current_structured_revision=2,
            current_structured_sample_refs=structured,candidates=candidates,provenance=changed_provenance,
            new_random_selection_refs=["SAMPLE-012","SAMPLE-013"],
            selection_method="system-random finite inventory selection")
        self.assertEqual(closed["status"],"target-met")
        self.assertEqual(closed["random_sample_refs"],["SAMPLE-012","SAMPLE-013"])


if __name__=="__main__":
    unittest.main()
