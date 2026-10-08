from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[4]
WCAG = ROOT / "skills/wcag-conformance-evaluation"
INSPECTION = ROOT / "skills/usability-inspection"
sys.path.insert(0, str(WCAG / "scripts"))
DOCUMENT_IDENTITY_A = "hmac-sha256:" + "a" * 64
DOCUMENT_IDENTITY_B = "hmac-sha256:" + "b" * 64


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


requirements = load("wcag_formal_requirements_contract_test", WCAG / "scripts/wcag_requirements.py")
sampling = load("wcag_formal_sampling_contract_test", WCAG / "scripts/sampling.py")
criterion_plan = load("wcag_formal_criterion_plan_contract_test", WCAG / "scripts/wcag_criterion_plan.py")
em_structure = load("wcag_formal_em_structure_contract_test", WCAG / "scripts/wcag_em_structure.py")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sample(ref: str, digit: str) -> dict:
    return {"sample_ref": ref, "identity_fingerprint": "sha256:" + digit * 64,
            "target_identity": "hmac-sha256:" + digit * 64}


def variation(sample_ref: str, ref: str, digit: str) -> dict:
    return {"sample_ref": sample_ref, "variation_ref": ref,
            "identity_fingerprint": "sha256:" + digit * 64}


class WcagRequirementAndSamplingTests(unittest.TestCase):
    def test_target_selection_is_derived_from_versioned_catalog_and_level(self):
        for version in requirements.SUPPORTED_VERSIONS:
            catalog = requirements.load_catalog(version)
            all_refs = {row["criterion_ref"] for row in catalog["success_criteria"]}
            for level in requirements.LEVELS:
                target = requirements.resolve_target(version, level)
                self.assertEqual(target["status"], "supported")
                self.assertTrue(set(target["required_success_criteria"]) <= all_refs)
                self.assertEqual(len(target["required_success_criteria"]), len(set(target["required_success_criteria"])))
                selected = {row["criterion_ref"] for row in catalog["success_criteria"]
                            if requirements.LEVELS[row["level"]] <= requirements.LEVELS[level]}
                self.assertEqual(set(target["required_success_criteria"]), selected)
            if version == "2.2":
                self.assertNotIn("4.1.1", all_refs)
        self.assertEqual(requirements.resolve_target(None, "AA")["status"], "unresolved")
        self.assertEqual(requirements.resolve_target("3.0", "AA")["status"], "unsupported")

    def test_every_formal_machine_probe_is_mapped_once_to_inspection_catalog(self):
        procedure_catalog = read_json(WCAG / "assets/wcag-evaluation-procedure-catalog.json")["procedures"]
        inspection_catalog = read_json(INSPECTION / "assets/wcag-machine-probe-catalog.json")["probes"]
        required = [key for row in procedure_catalog if row["procedure_kind"] == "machine"
                    for key in row["machine_probe_keys"]]
        provided = [row["machine_probe_key"] for row in inspection_catalog]
        self.assertEqual(set(required), set(provided))
        self.assertEqual(len(provided), len(set(provided)))
        self.assertTrue(all(len(row["machine_probe_keys"]) == len(set(row["machine_probe_keys"]))
                            for row in procedure_catalog if row["procedure_kind"] == "machine"))
        self.assertEqual({row["procedure_key"] for row in procedure_catalog
                          if row["procedure_kind"] == "machine" and not row["machine_probe_keys"]},
                         {"m-parsing-version-rule"})
        for probe in inspection_catalog:
            self.assertTrue({"request_kind", "request_signature", "criterion_evaluation_ref",
                             "procedure_execution_ref", "sample_ref", "variation_ref",
                             "requirement_ref", "currentness_dependency", "required_browser_capability"}
                            <= set(probe["required_request_fields"]))
        for procedure in procedure_catalog:
            contract = procedure.get("result_contract", {})
            if contract.get("contract_kind") == "typed-machine-probe-results":
                self.assertIn("incomplete", contract["allowed_statuses"])

    def test_random_sampling_boundaries_and_expected_blocked_are_distinct(self):
        for structured_count, expected in ((0, 0), (1, 1), (9, 1), (10, 1), (11, 2)):
            self.assertEqual(sampling.random_target_count(structured_count), expected)
        target_met = sampling.validate_random_selection(structured_refs=["S1"], selected_refs=["R1"],
            target_count=1, complete_inventory=False, selection_method="finite-random")
        self.assertEqual(target_met["selection_status"], "target-met")
        exhausted = sampling.validate_random_selection(structured_refs=["S1"], selected_refs=[], target_count=1,
            complete_inventory=True, selection_method="finite-random", exhaustion_evidence_refs=["INV-1"])
        self.assertEqual(exhausted["selection_status"], "exhausted-no-new-view")
        blocked = sampling.validate_random_selection(structured_refs=["S1"], selected_refs=[], target_count=1,
            complete_inventory=False, selection_method="finite-random", blocked_reason="candidate-inventory-incomplete")
        self.assertEqual(blocked["selection_status"], "blocked")
        with self.assertRaises(sampling.SamplingError):
            sampling.validate_random_selection(structured_refs=["S1"], selected_refs=["S1"], target_count=1,
                complete_inventory=False, selection_method="finite-random")
        skipped = em_structure.validate_sampling_skip(complete_inventory=True, inventory_refs=["S1", "S2"],
            all_in_scope_selected=["S1", "S2"], rationale="complete product inventory")
        self.assertEqual(skipped["procedure_status"], "skipped")
        with self.assertRaises(em_structure.EvaluationStructureError):
            em_structure.validate_sampling_skip(complete_inventory=False, inventory_refs=["S1"],
                all_in_scope_selected=["S1"], rationale="")

    def test_sample_identity_preserves_route_and_in_memory_state_without_url_values(self):
        drafts = [
            {"draft_key": "route-a", "target_ref": "TARGET-1", "state_key": "details-open",
             "target_identity": DOCUMENT_IDENTITY_A,
             "source_evidence_refs": ["BROWSER-1"]},
            {"draft_key": "route-b", "target_ref": "TARGET-1", "state_key": "details-open",
             "target_identity": DOCUMENT_IDENTITY_B,
             "source_evidence_refs": ["BROWSER-2"]},
            {"draft_key": "state-b", "target_ref": "TARGET-1", "state_key": "details-closed",
             "target_identity": DOCUMENT_IDENTITY_A,
             "source_evidence_refs": ["BROWSER-3"]},
            {"draft_key": "same-route-alternate-locator", "target_ref": "TARGET-1", "state_key": "details-open",
             "target_identity": DOCUMENT_IDENTITY_A,
             "source_evidence_refs": ["BROWSER-4"]},
        ]
        registry = sampling.sample_identity_registry(drafts)
        self.assertNotEqual(registry["draft_to_sample_ref"]["route-a"], registry["draft_to_sample_ref"]["route-b"])
        self.assertNotEqual(registry["draft_to_sample_ref"]["route-a"], registry["draft_to_sample_ref"]["state-b"])
        self.assertEqual(registry["draft_to_sample_ref"]["route-a"],
                         registry["draft_to_sample_ref"]["same-route-alternate-locator"])
        self.assertEqual(len(registry["samples"]), 3)
        self.assertTrue(all(row["target_identity"].startswith("hmac-sha256:") for row in registry["samples"]))
        self.assertTrue(all(row["source_locators"] == [row["target_identity"]] for row in registry["samples"]))
        self.assertNotIn("fixture.test", json.dumps(registry))
        self.assertNotIn("SENSITIVE_TEST_VALUE", json.dumps(registry))

        with self.assertRaises(sampling.SamplingError) as error:
            sampling.sample_identity_registry([{**drafts[0],
                "target_identity": "https://fixture.test/callback?code=SENSITIVE_TEST_VALUE"}])
        self.assertNotIn("SENSITIVE_TEST_VALUE", str(error.exception))
        with self.assertRaises(sampling.SamplingError) as error:
            sampling.sample_identity_registry([{**drafts[0], "locator": "/session/SENSITIVE_TEST_VALUE"}])
        self.assertNotIn("SENSITIVE_TEST_VALUE", str(error.exception))

        unsafe_row = {"sample_ref": "SAMPLE-001", "target_ref": "TARGET-1", "state_key": "details-open",
                      "source_locators": ["https://fixture.test/session/SENSITIVE_TEST_VALUE"],
                      "target_identity": DOCUMENT_IDENTITY_A,
                      "identity_fingerprint": sampling.fingerprint({"target_ref": "TARGET-1",
                          "state_key": "details-open", "document_identity": DOCUMENT_IDENTITY_A}),
                      "source_evidence_refs": ["BROWSER-1"]}
        with self.assertRaises(sampling.SamplingError) as error:
            sampling.materialize_sample_lineage(previous_sample_refs=["SAMPLE-001"],
                previous_identity_rows=[unsafe_row], current_identity_registry={"samples": [], "draft_to_sample_ref": {}},
                current_structured_sample_refs=[])
        self.assertNotIn("SENSITIVE_TEST_VALUE", str(error.exception))

    def test_criterion_plan_materializes_only_each_samples_required_variations(self):
        plan = criterion_plan.materialize_plan(wcag_version="2.2", level="A",
            samples=[sample("SAMPLE-001", "a"), sample("SAMPLE-002", "b")],
            variations=[variation("SAMPLE-001", "VAR-001", "c"), variation("SAMPLE-001", "VAR-002", "d"),
                       variation("SAMPLE-002", "VAR-003", "e")],
            process_memberships={"SAMPLE-001": "PROCESS-001"})
        required_count = len(requirements.resolve_target("2.2", "A")["required_success_criteria"])
        self.assertEqual(plan["expected_row_count"], 3 * required_count)
        self.assertEqual(len(plan["criteria"]), plan["expected_row_count"])
        self.assertEqual({row["sample_ref"] for row in plan["criteria"] if row["variation_ref"] == "VAR-003"}, {"SAMPLE-002"})
        self.assertTrue(all(row["process_ref"] == "PROCESS-001" for row in plan["criteria"] if row["sample_ref"] == "SAMPLE-001"))
        refs = [row["procedure_execution_ref"] for criterion in plan["criteria"] for row in criterion["procedure_executions"]]
        self.assertEqual(len(refs), len(set(refs)))
        self.assertEqual(len(plan["requests"]), len({row["observation_request_ref"] for row in plan["requests"]}))
        for request in plan["requests"]:
            signed = {key: value for key, value in request.items() if key != "request_signature"}
            expected = "sha256:" + hashlib.sha256(json.dumps(signed, ensure_ascii=False, sort_keys=True,
                                                               separators=(",", ":")).encode("utf-8")).hexdigest()
            self.assertEqual(request["request_signature"], expected)
            self.assertEqual(request["currentness_dependency"]["sample_identity_fingerprint"], "sha256:" + ("a" if request["sample_ref"] == "SAMPLE-001" else "b") * 64)
            expected_ref = request["sample_ref"]
            expected_digit = "a" if expected_ref == "SAMPLE-001" else "b"
            self.assertEqual(request["target_identity"], sample(expected_ref, expected_digit)["target_identity"])
        with self.assertRaises(criterion_plan.CriterionPlanError):
            criterion_plan.materialize_plan(wcag_version="2.2", level="A",
                samples=[{"sample_ref": "SAMPLE-001", "identity_fingerprint": "sha256:" + "a" * 64}],
                variations=[variation("SAMPLE-001", "VAR-001", "c")])
        with self.assertRaises(criterion_plan.CriterionPlanError):
            criterion_plan.materialize_plan(wcag_version="2.2", level="A",
                samples=[{**sample("SAMPLE-001", "a"), "target_identity": "SAMPLE-001"}],
                variations=[variation("SAMPLE-001", "VAR-001", "c")])
        with self.assertRaises(criterion_plan.CriterionPlanError):
            criterion_plan.materialize_plan(wcag_version="2.2", level="A", samples=[sample("SAMPLE-001", "a")],
                variations=[variation("SAMPLE-999", "VAR-001", "c")])


class WcagProcedureClosureTests(unittest.TestCase):
    def plan_row(self, criterion_ref: str, version: str = "2.2", level: str = "A") -> dict:
        plan = criterion_plan.materialize_plan(wcag_version=version, level=level,
            samples=[sample("SAMPLE-001", "a")], variations=[variation("SAMPLE-001", "VAR-001", "b")])
        return next(row for row in plan["criteria"] if row["criterion_ref"] == criterion_ref)

    @staticmethod
    def completed_procedures(row: dict, *, limitation: str | None = None,
                             at_applicability: str = "applicable") -> dict[str, dict]:
        values = {}
        for execution in row["procedure_executions"]:
            key = execution["procedure_key"]
            if execution["procedure_kind"] == "assistive-technology":
                if at_applicability == "unknown":
                    values[execution["procedure_execution_ref"]] = {"status": "pending", "applicability": "unknown",
                        "applicability_basis_refs": ["AT-DECISION-001"], "applicability_dependency_refs": []}
                elif at_applicability == "blocked":
                    values[execution["procedure_execution_ref"]] = {"status": "blocked", "applicability": "applicable",
                        "applicability_basis_refs": ["AT-DECISION-001"], "blocker": "assistive-technology-unavailable"}
                elif at_applicability == "not-applicable":
                    values[execution["procedure_execution_ref"]] = {"status": "complete", "applicability": "not-applicable",
                        "applicability_basis_refs": ["AT-DECISION-001"], "result": None, "evidence_refs": []}
                else:
                    values[execution["procedure_execution_ref"]] = {"status": "complete", "applicability": "applicable",
                        "applicability_basis_refs": ["AT-DECISION-001"], "result": "AT observation complete",
                        "evidence_refs": [f"E-{key}"]}
            elif execution["procedure_kind"] == "manual" and execution["applicability_mode"] == "machine-limitation":
                values[execution["procedure_execution_ref"]] = {"status": "complete", "result": "manual evidence reviewed",
                    "evidence_refs": [f"E-{key}"], "reason": "manual evidence supports the check"}
            else:
                values[execution["procedure_execution_ref"]] = {"status": "complete", "applicability": "applicable",
                    "result": "procedure evidence complete", "evidence_refs": [f"E-{key}"],
                    **({"limitation_code": limitation} if execution["procedure_kind"] == "machine" and limitation else {})}
        semantic = next(item for item in row["procedure_executions"] if item["procedure_key"].startswith("s-wcag-"))
        non_semantic_refs = [ref for exec_ref, value in values.items() if exec_ref != semantic["procedure_execution_ref"]
                             for ref in value.get("evidence_refs", [])]
        values[semantic["procedure_execution_ref"]] = {"status": "complete", "applicability": "applicable",
            "result": "semantic judgment complete", "evidence_refs": sorted(set(non_semantic_refs + ["E-SEMANTIC"]))}
        return values

    def test_conditional_manual_fallback_is_derived_only_from_machine_limitation(self):
        row = self.plan_row("1.4.3", "2.0", "AA")
        procedures = self.completed_procedures(row, limitation="background-not-machine-resolvable")
        closed = criterion_plan.close_criterion(row, procedure_results=procedures, applicable_population="present",
            semantic_result="satisfied", reason="all applicable evidence supports conformance", evidence_refs=["E-POP"])
        self.assertEqual(closed["execution_status"], "complete")
        fallback = next(item for item in closed["procedure_executions"] if item["applicability_mode"] == "machine-limitation")
        source = next(item for item in closed["procedure_executions"] if item["procedure_key"] == "m-text-contrast")
        self.assertEqual(fallback["applicability"], "applicable")
        self.assertEqual(fallback["applicability_basis_refs"], [source["procedure_execution_ref"]])
        no_limitation = self.completed_procedures(row)
        fallback_exec = next(item for item in row["procedure_executions"] if item["applicability_mode"] == "machine-limitation")
        no_limitation[fallback_exec["procedure_execution_ref"]] = {"status": "complete", "result": None,
            "evidence_refs": []}
        semantic_exec = next(item for item in row["procedure_executions"] if item["procedure_key"].startswith("s-wcag-"))
        source_exec = next(item for item in row["procedure_executions"] if item["procedure_key"] == "m-text-contrast")
        no_limitation[semantic_exec["procedure_execution_ref"]]["evidence_refs"] = sorted(
            {ref for exec_ref, value in no_limitation.items() if exec_ref != semantic_exec["procedure_execution_ref"]
             for ref in value.get("evidence_refs", [])} | {source_exec["procedure_execution_ref"], "E-SEMANTIC"})
        closed_without_fallback = criterion_plan.close_criterion(row, procedure_results=no_limitation,
            applicable_population="present", semantic_result="satisfied", reason="machine result was conclusive",
            evidence_refs=["E-POP"])
        fallback_row = next(item for item in closed_without_fallback["procedure_executions"] if item["applicability_mode"] == "machine-limitation")
        self.assertEqual(fallback_row["applicability"], "not-applicable")
        self.assertIsNone(fallback_row["result"])

    def test_resize_text_machine_limitations_activate_only_the_fixed_manual_fallback(self):
        row = self.plan_row("1.4.4", "2.0", "AA")
        for limitation in ("text-scaling-mechanism-not-machine-executable", "text-scaling-state-not-machine-readable"):
            with self.subTest(limitation=limitation):
                results = self.completed_procedures(row, limitation=limitation)
                closed = criterion_plan.close_criterion(row, procedure_results=results,
                    applicable_population="present", semantic_result="satisfied",
                    reason="manual review closed the author-provided and user-agent mechanism evidence",
                    evidence_refs=["E-POP"])
                source = next(item for item in closed["procedure_executions"] if item["procedure_key"] == "m-resize-text")
                fallback = next(item for item in closed["procedure_executions"] if item["procedure_key"] == "manual-wcag-1.4.4")
                self.assertEqual(closed["execution_status"], "complete")
                self.assertEqual(fallback["applicability"], "applicable")
                self.assertEqual(fallback["applicability_basis_refs"], [source["procedure_execution_ref"]])
        conclusive = self.completed_procedures(row)
        fallback_execution = next(item for item in row["procedure_executions"]
            if item["procedure_key"] == "manual-wcag-1.4.4")
        resize_execution = next(item for item in row["procedure_executions"]
            if item["procedure_key"] == "m-resize-text")
        conclusive[fallback_execution["procedure_execution_ref"]] = {"status": "complete", "result": None,
            "evidence_refs": []}
        semantic_execution = next(item for item in row["procedure_executions"]
            if item["procedure_key"].startswith("s-wcag-"))
        conclusive[semantic_execution["procedure_execution_ref"]]["evidence_refs"] = sorted(
            {ref for exec_ref, value in conclusive.items() if exec_ref != semantic_execution["procedure_execution_ref"]
             for ref in value.get("evidence_refs", [])} | {resize_execution["procedure_execution_ref"], "E-SEMANTIC"})
        closed_without_fallback = criterion_plan.close_criterion(row, procedure_results=conclusive,
            applicable_population="present", semantic_result="satisfied",
            reason="current fixed resize observation and semantic review are conclusive", evidence_refs=["E-POP"])
        fallback = next(item for item in closed_without_fallback["procedure_executions"]
            if item["procedure_key"] == "manual-wcag-1.4.4")
        self.assertEqual(fallback["applicability"], "not-applicable")

    def test_missing_violation_evidence_cannot_be_reported_as_not_satisfied(self):
        row = self.plan_row("1.1.1")
        closed = criterion_plan.close_criterion(row, procedure_results=self.completed_procedures(row),
            applicable_population="present", semantic_result="not-satisfied", reason="a required alternative is missing",
            evidence_refs=["E-POP"])
        self.assertEqual((closed["execution_status"], closed["result"], closed["limitation"]),
                         ("complete", "undetermined", "violation_evidence_missing"))

    def test_at_applicability_unknown_blocks_final_semantic_and_environment_failure_is_blocked(self):
        row = self.plan_row("1.3.1")
        results = self.completed_procedures(row, at_applicability="unknown")
        semantic = next(item for item in row["procedure_executions"] if item["procedure_key"].startswith("s-wcag-"))
        results[semantic["procedure_execution_ref"]] = {"status": "pending"}
        pending = criterion_plan.close_criterion(row, procedure_results=results, applicable_population="present",
            semantic_result="satisfied", reason="pending AT decision", evidence_refs=["E-POP"])
        self.assertEqual(pending["execution_status"], "in-progress")
        results = self.completed_procedures(row, at_applicability="blocked")
        results[semantic["procedure_execution_ref"]] = {"status": "pending"}
        blocked = criterion_plan.close_criterion(row, procedure_results=results, applicable_population="present",
            semantic_result="satisfied", reason="AT cannot run", evidence_refs=["E-POP"])
        self.assertEqual(blocked["execution_status"], "blocked")

    def test_external_evidence_current_scope_revision_and_rejection_trace_are_deterministic(self):
        current = {"evidence_ref": "EXT-1", "source_id": "SRC-1", "source_revision": "r2",
            "environment_fingerprint": "sha256:" + "a" * 64, "scope_fingerprint": "sha256:" + "b" * 64,
            "freshness_status": "current", "evidence_kind": "external-evidence"}
        rejected = {**current, "evidence_ref": "EXT-2", "source_revision": "r1", "scope_fingerprint": "sha256:" + "c" * 64}
        decision = criterion_plan.resolve_external_evidence_candidates([current, rejected],
            allowed_source_ids={"SRC-1"}, current_source_revisions={"SRC-1": "r2"},
            environment_fingerprint="sha256:" + "a" * 64, scope_fingerprint="sha256:" + "b" * 64)
        self.assertEqual(decision["current_evidence_refs"], ["EXT-1"])
        self.assertEqual({"source-revision-mismatch", "scope-mismatch"}, set(decision["rejected_candidates"][0]["reasons"]))
        none = criterion_plan.resolve_external_evidence_candidates([rejected], allowed_source_ids={"SRC-1"},
            current_source_revisions={"SRC-1": "r2"}, environment_fingerprint="sha256:" + "a" * 64,
            scope_fingerprint="sha256:" + "b" * 64)
        self.assertEqual(none["applicability"], "not-applicable")

    def test_sample_results_are_materialized_from_current_complete_criterion_refs_only(self):
        row = self.plan_row("1.1.1")
        complete = {**row, "execution_status": "complete", "result": "satisfied"}
        stale = {**self.plan_row("1.2.1"), "execution_status": "complete", "result": "not-satisfied"}
        results = criterion_plan.materialize_sample_results([complete, stale],
            current_criterion_evaluation_refs={complete["criterion_evaluation_ref"]}, sample_kinds={complete["sample_ref"]:"structured"})
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["sample_result_ref"], "WCAG-RES-001")
        self.assertEqual(results[0]["sample_kind"], "structured")
        self.assertEqual(results[0]["criterion_evaluation_ref"], complete["criterion_evaluation_ref"])
        with self.assertRaises(criterion_plan.CriterionPlanError):
            criterion_plan.materialize_sample_results([complete, stale], current_criterion_evaluation_refs={"CRIT-EVAL-STALE"},
                sample_kinds={complete["sample_ref"]:"structured"})


if __name__ == "__main__":
    unittest.main()
