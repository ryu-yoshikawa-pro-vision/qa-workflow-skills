from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[4]
INSPECTION = ROOT / "skills/usability-inspection"
WCAG = ROOT / "skills/wcag-conformance-evaluation"
sys.path.insert(0, str(WCAG / "scripts"))


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


structure = load("usability_inspection_structure_contract", INSPECTION / "scripts/inspection_structure.py")
observation = load("usability_inspection_observation_contract", INSPECTION / "scripts/observation_contract.py")
measurement = load("usability_inspection_measurements", INSPECTION / "scripts/measurement.py")
checks = load("usability_inspection_criterion_checks", INSPECTION / "scripts/criterion_checks.py")
criterion_plan = load("wcag_criterion_plan_for_inspection_test", WCAG / "scripts/wcag_criterion_plan.py")


class InspectionStructureTests(unittest.TestCase):
    def test_general_scoped_and_formal_modes_materialize_only_their_closed_scope(self):
        general = structure.scope_skeleton("general")
        self.assertEqual(len(general), len(structure.ASPECTS))
        self.assertEqual([row["scope_ref"] for row in general], [f"SCOPE-{n:03d}" for n in range(1, 8)])
        scoped = structure.scope_skeleton("scoped", requested_aspects=["accessibility", "visual-responsive"])
        self.assertEqual([row["aspect_key"] for row in scoped], ["accessibility", "visual-responsive"])
        formal = structure.scope_skeleton("formal-handoff", formal_scope=[
            {"scope_ref": "FORMAL-REQ-1", "description": "probe scope", "evidence_refs": ["E-1"]}
        ])
        self.assertEqual(formal[0]["aspect_key"], None)
        self.assertEqual(formal[0]["scope_ref"], "SCOPE-001")
        with self.assertRaises(structure.InspectionContractError):
            structure.scope_skeleton("scoped", requested_aspects=["unknown"])

    def test_scope_closure_and_finding_are_derived_from_outcome(self):
        rows = structure.scope_skeleton("scoped", requested_aspects=["accessibility"])
        rows[0].update({"outcome": "問題を確認", "evidence_refs": ["E-1"]})
        self.assertTrue(structure.close_scope(rows)["closed"])
        self.assertTrue(structure.finding_requirement("問題を確認", True))
        self.assertFalse(structure.finding_requirement("問題なし", True))
        self.assertFalse(structure.close_scope([{**rows[0], "evidence_refs": []}])["closed"])

    def test_formal_handoff_is_typed_and_cannot_be_reinterpreted(self):
        request = {"request_kind": "wcag-machine-probe", "observation_request_ref": "REQ-001",
                   "request_signature": "sig", "machine_probe_key": "mp-document-title",
                   "currentness_dependency": {"sample_identity_fingerprint": "sha256:abc"},
                   "target_identity": "SAMPLE-001"}
        self.assertEqual(structure.validate_formal_handoff(request)["request_ref"], "REQ-001")
        with self.assertRaises(structure.InspectionContractError):
            structure.validate_formal_handoff({**request, "request_kind": "arbitrary-probe"})


class ObservationContractTests(unittest.TestCase):
    def test_catalog_has_exact_sixteen_fields_eight_timing_predicates_and_formal_probe_inventory(self):
        browser_catalog = json.loads((INSPECTION / "assets/browser-observation-catalog.json").read_text(encoding="utf-8"))
        formal_catalog = json.loads((INSPECTION / "assets/wcag-machine-probe-catalog.json").read_text(encoding="utf-8"))
        observation.validate_catalog(browser_catalog)
        self.assertEqual(set(observation.FORMAL_PROBES), {row["machine_probe_key"] for row in formal_catalog["probes"]})
        self.assertEqual(len(observation.OBSERVATION_FIELDS), 16)
        self.assertEqual(len(observation.PREDICATES), 8)

    def test_target_parent_resolution_population_fingerprint_and_session_currentness(self):
        drafts = [
            {"draft_target_key": "parent", "scope_ref": "SCOPE-001", "semantic_label": "Dialog",
             "discovery_evidence_refs": ["E-1"], "resolver_kind": "role-name",
             "resolver_payload": {"role": "dialog", "name": "Preferences"}},
            {"draft_target_key": "button", "scope_ref": "SCOPE-001", "semantic_label": "Save",
             "discovery_evidence_refs": ["E-2"], "resolver_kind": "role-name",
             "resolver_payload": {"role": "button", "name": "Save", "within_target_ref": "parent"}},
            {"draft_target_key": "item", "scope_ref": "SCOPE-001", "semantic_label": "third item",
             "discovery_evidence_refs": ["E-3"], "resolver_kind": "machine-population-index",
             "resolver_payload": {"population_ref": "POP-1", "population_revision": "p1", "index": 2,
                                  "identity_fingerprint": "sha256:item"}},
            {"draft_target_key": "session", "scope_ref": "SCOPE-001", "semantic_label": "current target",
             "discovery_evidence_refs": ["E-4"], "resolver_kind": "current-session-ref",
             "resolver_payload": {"session_target_ref": "TARGET-X", "document_identity": "doc-1"}},
        ]
        result = observation.materialize_targets(drafts, document_identity="doc-1", population_revisions={
            "POP-1": {"population_revision": "p1", "identity_fingerprint": "sha256:item"}
        })
        self.assertEqual(result["targets"][1]["resolver_payload"]["within_target_ref"], "TARGET-001")
        self.assertEqual(result["targets"][2]["resolution_status"], "current")
        population_changed = observation.materialize_targets(drafts[2:3], document_identity="doc-1",
            population_revisions={"POP-1": {"population_revision": "p2", "identity_fingerprint": "sha256:item"}})
        self.assertEqual(population_changed["targets"][0]["resolution_status"], "stale")
        unique = observation.normalize_target_resolution(result["targets"][0], {
            "target_ref": "TARGET-001", "match_count": 1, "current_document_identity": "doc-1"
        }, current_document_identity="doc-1")
        self.assertEqual(unique["status"], "unique")
        ambiguous = observation.normalize_target_resolution(result["targets"][0], {
            "target_ref": "TARGET-001", "match_count": 2, "current_document_identity": "doc-1"
        }, current_document_identity="doc-1")
        self.assertEqual(ambiguous["status"], "ambiguous")
        session_stale = observation.normalize_target_resolution(result["targets"][3], {
            "target_ref": "TARGET-004", "match_count": 1, "current_document_identity": "doc-2"
        }, current_document_identity="doc-2")
        self.assertEqual(session_stale["status"], "stale")

    def test_fixed_probe_planning_and_normalization_reject_bad_values(self):
        plan = observation.plan_probes(selected_rule_keys=["97a4e1"], measurement_kinds=["interaction-timing"],
                                       aspect_keys=["accessibility"], target_refs=["TARGET-001"])
        self.assertEqual(plan["required_observation_fields"], ["accessibility.semantics", "focus.state", "interaction.timing"])
        self.assertTrue(next(row for row in plan["probes"] if row["observation_field"] == "interaction.timing")["predicate_key_required"])
        geometry = next(row for row in observation.plan_probes(selected_rule_keys=[], measurement_kinds=["geometry"],
                                                               aspect_keys=[], target_refs=["TARGET-001"])["probes"]
                        if row["observation_field"] == "element.geometry")
        normalized = observation.normalize_probe_result(geometry, {
            "probe_key": "element-geometry", "document_identity": "doc-1", "status": "ok",
            "value": {"x_css_px": 1.5, "y_css_px": 2, "width_css_px": 100, "height_css_px": 20},
            "evidence_refs": ["E-1"],
        }, current_document_identity="doc-1")
        self.assertEqual(normalized["status"], "ok")
        with self.assertRaises(observation.ObservationContractError):
            observation.normalize_probe_result(geometry, {
                "probe_key": "element-geometry", "document_identity": "doc-1", "status": "ok",
                "value": {"x_css_px": float("nan"), "y_css_px": 2, "width_css_px": 100, "height_css_px": 20},
            }, current_document_identity="doc-1")

    def test_fixed_predicates_reject_unknown_code_and_browser_owned_baseline(self):
        observation.validate_predicate({"predicate_key": "text-present", "expected_text": "Saved",
                                         "within_target_ref": "TARGET-001"})
        observation.validate_predicate({"predicate_key": "url-changed", "baseline_url": "capture-at-arm"})
        with self.assertRaises(observation.ObservationContractError):
            observation.validate_predicate({"predicate_key": "text-present", "expected_text": "Saved", "javascript": "alert(1)"})
        with self.assertRaises(observation.ObservationContractError):
            observation.validate_predicate({"predicate_key": "attribute-equals", "target_ref": "TARGET-001",
                                            "attribute_name": "data-anything", "expected_value": "x"})
        with self.assertRaises(observation.ObservationContractError):
            observation.validate_predicate({"predicate_key": "url-changed", "baseline_url": "https://input.example/"})

    def test_additional_request_identity_no_progress_and_terminal_closure(self):
        draft = {"request_draft_key": "obs-1", "requester_kind": "wcag-procedure",
                 "requester_identity": {"criterion_evaluation_ref": "CRIT-1", "procedure_execution_ref": "PROC-1"},
                 "scope_ref": "SCOPE-001", "target_ref": "TARGET-001", "state_description": "Save button",
                 "state_basis_refs": ["ACTION-1"], "current_document_identity": "doc-1",
                 "observation_field": "element.state", "predicate": None, "reason": "Need post-action enabled state",
                 "current_evidence_refs": ["E-1"]}
        request = observation.materialize_additional(draft, prior_requests=[])
        repeated = observation.materialize_additional({**draft, "request_draft_key": "obs-2", "state_description": "Renamed",
                                                       "reason": "Changed prose"}, prior_requests=[request])
        self.assertEqual(repeated["status"], "no-progress")
        closed = observation.close_additional_request(request, {
            "observation_request_ref": request["observation_request_ref"],
            "request_signature": request["request_signature"],
            "input_evidence_fingerprint": request["input_evidence_fingerprint"],
            "status": "ok", "evidence_refs": ["E-2"],
        })
        self.assertEqual(closed["status"], "completed")
        with self.assertRaises(observation.ObservationContractError):
            observation.close_additional_request(request)

    def test_formal_request_signature_is_bound_to_machine_probe_and_identity(self):
        plan = criterion_plan.materialize_plan(
            wcag_version="2.0", level="A",
            samples=[{"sample_ref": "SAMPLE-1", "identity_fingerprint": "sha256:" + "a" * 64}],
            variations=[{"sample_ref": "SAMPLE-1", "variation_ref": "VAR-1", "identity_fingerprint": "sha256:" + "b" * 64}],
        )
        request = plan["requests"][0]
        validated = observation.validate_formal_probe_request(request)
        self.assertEqual(validated["request_ref"], request["observation_request_ref"])
        result = {**{field: request[field] for field in (
                      "observation_request_ref", "request_signature", "criterion_evaluation_ref",
                      "procedure_execution_ref", "machine_probe_key", "sample_ref", "variation_ref",
                      "process_ref", "requirement_ref", "target_identity", "currentness_dependency")},
                  "status": "ok", "current_document_identity": "doc-1", "evidence_refs": ["E-1"], "value": {}}
        self.assertTrue(observation.normalize_probe_result({}, result, current_document_identity="doc-1",
                                                           formal=True, formal_request=request)["normalized"])
        tampered = {**request, "target_identity": "other"}
        with self.assertRaises(observation.ObservationContractError):
            observation.validate_formal_probe_request(tampered)
        with self.assertRaises(observation.ObservationContractError):
            observation.normalize_probe_result({}, {**result, "machine_probe_key": "mp-viewport-state"},
                                               current_document_identity="doc-1", formal=True, formal_request=request)


class DeterministicMeasurementTests(unittest.TestCase):
    def test_numeric_measurements_are_script_owned(self):
        self.assertEqual(measurement.viewport_overflow({"viewport_width_css_px": 100, "viewport_height_css_px": 80,
                                                        "scroll_width_css_px": 120, "scroll_height_css_px": 80})[
            "horizontal_overflow_css_px"], "20")
        self.assertEqual(str(measurement.contrast_ratio("1", "0")), "21.00")
        self.assertEqual(measurement.interaction_elapsed_ms(10, 15, same_page_clock=True,
                                                           start_event_observed=True, end_predicate_observed=True)["elapsed_ms"], "5")
        self.assertEqual(measurement.interaction_elapsed_ms(10, 15, same_page_clock=False,
                                                           start_event_observed=True, end_predicate_observed=True)["status"],
                         "measurement-unavailable")
        self.assertEqual(checks.SUPPORTED_RULES.keys(), {"2779a5", "97a4e1", "23a2a8"})
        self.assertEqual(checks.run_supported_rule("2779a5", {"document.title": "Home"})["outcome"], "passed")
        with self.assertRaises(checks.RuleContractError):
            checks.run_supported_rule("unknown", {})


if __name__ == "__main__":
    unittest.main()
