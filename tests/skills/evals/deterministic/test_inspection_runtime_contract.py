from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "skills/usability-inspection/scripts/inspection_runtime.py"
DOCUMENT_IDENTITY_A = "hmac-sha256:" + "a" * 64
DOCUMENT_IDENTITY_B = "hmac-sha256:" + "b" * 64


def metadata(*, formal: bool = False) -> dict:
    unit = "artifact:inspection_runtime:formal-machine-probe" if formal else "artifact:inspection_runtime:all"
    return {"envelope_version": "1", "skill": "usability-inspection",
        "runtime_contract_version": "runtime-v1", "generator_contract_version": "usability-inspection-runtime-v2",
        "runtime_unit_key": unit, "model_key": None, "model_type": None,
        "technique_slug": None, "selection_source": None, "selection_key": None,
        "scope_key": "all", "input_mode": "direct", "upstream_entities": [],
        "upstream_runtime_units": [], "static_data_versions": {}, "authority_refs": [], "reference_refs": []}


def invoke(operation: str, arguments: dict, *, formal: bool = False) -> dict:
    body = {"metadata": metadata(formal=formal), "input": {"operation": operation, "arguments": arguments}}
    result = subprocess.run([sys.executable, str(SCRIPT)], input=json.dumps(body), text=True,
        cwd=ROOT, capture_output=True, check=False)
    if result.returncode not in {0, 1}:
        raise AssertionError(result.stdout + result.stderr)
    return json.loads(result.stdout)


def formal_request(probe_key: str = "mp-resize-text-run", *, level: str = "AA") -> dict:
    sys.path.insert(0, str(ROOT / "skills/wcag-conformance-evaluation/scripts"))
    import wcag_criterion_plan
    plan = wcag_criterion_plan.materialize_plan(wcag_version="2.2", level=level,
        samples=[{"sample_ref": "SAMPLE-001", "identity_fingerprint": "sha256:" + "a" * 64,
                  "target_identity": DOCUMENT_IDENTITY_A}],
        variations=[{"sample_ref": "SAMPLE-001", "variation_ref": "VAR-001",
                     "identity_fingerprint": "sha256:" + "b" * 64}])
    return next(request for request in plan["requests"] if request["machine_probe_key"] == probe_key)


def formal_request_for_contract(probe_key: str) -> dict:
    try:
        return formal_request(probe_key)
    except StopIteration:
        request = formal_request("mp-moving-updating-inventory")
        request["machine_probe_key"] = probe_key
        request["required_browser_capability"] = probe_key
        unsigned = {key: value for key, value in request.items() if key != "request_signature"}
        canonical = json.dumps(unsigned, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        request["request_signature"] = "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        return request


def resize_text_result(request: dict, *, disappeared_final: bool = False) -> dict:
    identity_fields = ("observation_request_ref", "request_signature", "criterion_evaluation_ref",
        "procedure_execution_ref", "machine_probe_key", "sample_ref", "variation_ref", "process_ref",
        "requirement_ref", "target_identity", "currentness_dependency")
    refs = ("dom-text:body > p:nth-of-type(1)/text[1]", "dom-text:body > p:nth-of-type(2)/text[1]")
    sizes = (("16", "20"), ("24", "30"), ("32", "40"))
    sequence = []
    for index, control_value in enumerate(("100", "150", "200")):
        candidates = []
        for candidate_index, target_ref in enumerate(refs):
            present = not (disappeared_final and index == 2 and candidate_index == 1)
            candidates.append({"target_ref": target_ref, "present": present,
                "used_font_size_css_px": sizes[index][candidate_index] if present else None,
                "rects": ([{"left": 1, "top": 2, "width": 30, "height": 18}] if present else []),
                "clipped": False, "obscured": False})
        sequence.append({"state_index": index, "control_value": control_value,
            "document_identity": request["target_identity"],
            "viewport": {"width_css_px": 1280, "height_css_px": 800},
            "overflow": {"scroll_width_css_px": 1280, "client_width_css_px": 1280,
                "scroll_height_css_px": 800, "client_height_css_px": 800},
            "text_candidates": candidates,
            "interactive_controls": [{"target_ref": "dom-control:body > button:nth-of-type(1)",
                "role": "button", "enabled": True}],
            "population_complete": True, "unmeasurable_target_refs": [],
            "unsupported_visible_canvas": False, "inaccessible_visible_frame": False,
            "content_loss_refs": [refs[1]] if disappeared_final and index == 2 else [],
            "newly_clipped_target_refs": [], "newly_obscured_target_refs": [], "functionality_loss_refs": []})
    return {**{field: request[field] for field in identity_fields}, "status": "ok",
        "current_document_identity": request["target_identity"], "evidence_refs": ["E-1"],
        "value": {"schema": "wcag-resize-text-observation-v1",
            "resize_mechanism": "author-provided-resize-control",
            "control": {"target_ref": "accessible-control:slider:Text size", "role": "slider",
                "accessible_name": "Text size", "input_type": "range", "minimum_value": "100",
                "maximum_value": "200", "step_value": "50", "baseline_value": "100"},
            "mechanism_state_sequence": sequence, "text_population_complete": True,
            "mechanism_state_sequence_complete": True,
            "cleanup": {"status": "restored", "baseline_control_value": "100", "current_control_value": "100"}}}


class InspectionRuntimeContractTests(unittest.TestCase):
    def test_exact_decimal_browser_geometry_crosses_runtime_cli(self):
        output = invoke("target-geometry", {"box": {
            "x_css_px": 16, "y_css_px": 775.78125,
            "width_css_px": 216.1875, "height_css_px": 44,
        }})
        self.assertEqual(output["runtime_status"], "ok")
        self.assertEqual(output["result_status"], "ready")
        self.assertEqual(output["payload"]["result"]["area_css_px2"], "9512.2500")

    def test_authority_threshold_result_deterministically_closes_requirement(self):
        over = invoke("requirement-result", {"applicability": "applicable", "semantic_result": None,
            "population_complete": False, "required_checks_complete": False, "evidence_refs": ["OBS-1"],
            "threshold_result": "over-threshold", "authority_ref": "AUTH-1"})
        self.assertEqual(over["payload"]["result"]["result"], "not-satisfied")
        within_incomplete = invoke("requirement-result", {"applicability": "applicable", "semantic_result": None,
            "population_complete": False, "required_checks_complete": True, "evidence_refs": ["OBS-1"],
            "threshold_result": "within-threshold", "authority_ref": "AUTH-1"})
        self.assertEqual(within_incomplete["payload"]["result"]["result"], "undetermined")
        within_complete = invoke("requirement-result", {"applicability": "applicable", "semantic_result": None,
            "population_complete": True, "required_checks_complete": True, "evidence_refs": ["OBS-1"],
            "threshold_result": "within-threshold", "authority_ref": "AUTH-1"})
        self.assertEqual(within_complete["payload"]["result"]["result"], "satisfied")
        advisory = invoke("requirement-result", {"applicability": "applicable", "semantic_result": None,
            "population_complete": True, "required_checks_complete": True, "evidence_refs": ["OBS-1"],
            "threshold_result": "over-threshold"})
        self.assertEqual(advisory["runtime_status"], "invalid_input")

    def test_general_runtime_fingerprints_only_general_observation_assets(self):
        output = invoke("plan-probes", {"selected_rule_keys": ["2779a5"], "measurement_kinds": [],
            "aspect_keys": [], "target_refs": []})
        self.assertEqual(output["runtime_status"], "ok")
        self.assertEqual(output["result_status"], "ready")
        self.assertEqual(output["runtime_unit_key"], "artifact:inspection_runtime:all")
        self.assertEqual(set(output["static_data_versions"]), {"browser_observation_catalog", "test_rule_catalog"})
        self.assertEqual(output["payload"]["result"]["probes"][0]["observation_field"], "document.title")
        self.assertEqual(output["payload"]["result"]["probes"][0]["probe_key"], "document-title")
        self.assertIn("has_non_whitespace_text", output["payload"]["result"]["probes"][0]["required_result_fields"])

    def test_general_observation_statuses_do_not_promote_unfinished_probes_to_ready(self):
        planned = invoke("plan-probes", {"selected_rule_keys": ["2779a5"], "measurement_kinds": [],
            "aspect_keys": [], "target_refs": []})
        probe = planned["payload"]["result"]["probes"][0]
        value = {
            "is_html_document": True, "has_html_title_descendant": True,
            "first_title_children_are_text": True, "has_non_whitespace_text": True,
            "status": "ok", "limitation": None,
        }
        expected = {
            "ok": ("ready", "supported", False),
            "incomplete": ("unresolved", "partial", True),
            "unavailable": ("blocked", "unsupported", True),
            "unsupported": ("blocked", "unsupported", True),
            "blocked": ("blocked", "unsupported", True),
        }

        for status, (result_status, support_status, blocking) in expected.items():
            with self.subTest(status=status):
                result = {
                    "probe_key": probe["probe_key"], "document_identity": DOCUMENT_IDENTITY_A,
                    "status": status, "limitation": None if status == "ok" else f"synthetic {status} limitation",
                    "evidence_refs": ["E-OBS-1"],
                }
                if status == "ok":
                    result["value"] = value
                normalized = invoke("normalize-observation-probe-result", {
                    "probe": probe, "result": result,
                    "current_document_identity": DOCUMENT_IDENTITY_A,
                })

                self.assertEqual(normalized["runtime_status"], "ok")
                self.assertEqual(normalized["result_status"], result_status)
                self.assertEqual(normalized["support_status"], support_status)
                self.assertEqual(bool(normalized["issues"]), blocking)
                if blocking:
                    self.assertTrue(normalized["issues"][0]["blocking"])
                    self.assertEqual(normalized["issues"][0]["status"], status)
                    self.assertEqual(normalized["payload"]["result"]["status"], status)
                    self.assertIsNone(normalized["payload"]["result"]["value"])
                    self.assertEqual(normalized["payload"]["result"]["limitation"], result["limitation"])
                else:
                    self.assertEqual(normalized["issues"], [])
                    self.assertEqual(normalized["payload"]["result"]["value"], value)

    def test_formal_runtime_validates_typed_request_and_fingerprints_probe_catalog(self):
        request = formal_request()
        output = invoke("validate-wcag-machine-probe-request", {"request": request}, formal=True)
        self.assertEqual(output["runtime_status"], "ok")
        self.assertEqual(output["result_status"], "ready")
        self.assertEqual(set(output["static_data_versions"]),
            {"browser_observation_catalog", "test_rule_catalog", "wcag_machine_probes"})
        self.assertEqual(output["payload"]["result"]["request_ref"], request["observation_request_ref"])

    def test_formal_result_echoes_all_currentness_identity_and_fixed_args_reject_injection(self):
        request = formal_request()
        identity_fields = ("observation_request_ref", "request_signature", "criterion_evaluation_ref",
            "procedure_execution_ref", "machine_probe_key", "sample_ref", "variation_ref", "process_ref",
            "requirement_ref", "target_identity", "currentness_dependency")
        result = resize_text_result(request)
        normalized = invoke("normalize-wcag-machine-probe-result", {"request": request, "result": result,
            "current_document_identity": request["target_identity"]}, formal=True)
        self.assertEqual(normalized["runtime_status"], "ok")
        self.assertEqual(normalized["result_status"], "ready")
        self.assertTrue(normalized["payload"]["result"]["normalized"])
        candidates = normalized["payload"]["result"]["value"]["mechanism_state_sequence"]
        self.assertEqual([row["rendered_scale_ratio"] for row in candidates[1]["text_candidates"]], ["1.5", "1.5"])
        self.assertEqual([row["rendered_scale_ratio"] for row in candidates[2]["text_candidates"]], ["2", "2"])
        stale = {**result, "sample_ref": "SAMPLE-OTHER"}
        rejected = invoke("normalize-wcag-machine-probe-result", {"request": request, "result": stale,
            "current_document_identity": request["target_identity"]}, formal=True)
        self.assertEqual(rejected["runtime_status"], "invalid_input")
        injected = invoke("normalize-observation-probe-result", {"probe": {}, "result": {},
            "current_document_identity": DOCUMENT_IDENTITY_A, "formal": True})
        self.assertEqual(injected["runtime_status"], "invalid_input")

    def test_unavailable_webcrypto_stays_blocked_without_fabricating_document_identity(self):
        request = formal_request()
        identity_fields = ("observation_request_ref", "request_signature", "criterion_evaluation_ref",
            "procedure_execution_ref", "machine_probe_key", "sample_ref", "variation_ref", "process_ref",
            "requirement_ref", "target_identity", "currentness_dependency")
        limitation = "browser cannot create an in-memory keyed current-document identity"
        result = {**{field: request[field] for field in identity_fields}, "status": "blocked",
            "current_document_identity": None, "evidence_refs": [], "limitation": limitation}

        normalized = invoke("normalize-wcag-machine-probe-result", {"request": request, "result": result,
            "current_document_identity": None}, formal=True)
        self.assertEqual(normalized["runtime_status"], "ok")
        self.assertEqual(normalized["result_status"], "blocked")
        self.assertEqual(normalized["payload"]["result"]["status"], "blocked")
        self.assertIsNone(normalized["payload"]["result"]["current_document_identity"])
        self.assertNotIn("value", normalized["payload"]["result"])

        forged = {**result, "status": "ok", "value": {}}
        rejected = invoke("normalize-wcag-machine-probe-result", {"request": request, "result": forged,
            "current_document_identity": None}, formal=True)
        self.assertEqual(rejected["runtime_status"], "invalid_input")

    def test_resize_text_machine_observation_preserves_content_loss_without_inference(self):
        request = formal_request()
        result = resize_text_result(request, disappeared_final=True)
        normalized = invoke("normalize-wcag-machine-probe-result", {"request": request, "result": result,
            "current_document_identity": request["target_identity"]}, formal=True)
        self.assertEqual(normalized["runtime_status"], "ok")
        final = normalized["payload"]["result"]["value"]["mechanism_state_sequence"][-1]
        self.assertEqual(final["content_loss_refs"], ["dom-text:body > p:nth-of-type(2)/text[1]"])
        self.assertIsNone(final["text_candidates"][1]["rendered_scale_ratio"])

    def test_formal_machine_limitation_completes_observation_for_conditional_fallback(self):
        request = formal_request()
        identity_fields = ("observation_request_ref", "request_signature", "criterion_evaluation_ref",
            "procedure_execution_ref", "machine_probe_key", "sample_ref", "variation_ref", "process_ref",
            "requirement_ref", "target_identity", "currentness_dependency")
        result = {**{field: request[field] for field in identity_fields}, "status": "unsupported",
            "current_document_identity": request["target_identity"], "evidence_refs": ["E-1"],
            "limitation": "The current browser owner cannot operate the documented browser zoom control.",
            "limitation_code": "text-scaling-mechanism-not-machine-executable"}
        completed = invoke("normalize-wcag-machine-probe-result", {"request": request, "result": result,
            "current_document_identity": request["target_identity"]}, formal=True)
        self.assertEqual(completed["runtime_status"], "ok")
        self.assertEqual(completed["result_status"], "ready")
        self.assertEqual(completed["payload"]["result"]["status"], "unsupported")
        self.assertEqual(completed["payload"]["result"]["limitation_code"], "text-scaling-mechanism-not-machine-executable")
        missing_code = invoke("normalize-wcag-machine-probe-result", {"request": request,
            "result": {key: value for key, value in result.items() if key != "limitation_code"},
            "current_document_identity": request["target_identity"]}, formal=True)
        self.assertEqual(missing_code["result_status"], "blocked")
        wrong_pair = {**result, "limitation_code": "text-scaling-state-not-machine-readable"}
        rejected = invoke("normalize-wcag-machine-probe-result", {"request": request, "result": wrong_pair,
            "current_document_identity": request["target_identity"]}, formal=True)
        self.assertEqual(rejected["runtime_status"], "invalid_input")

    def test_current_typed_partial_wcag_observation_is_semantic_evidence_not_blocked(self):
        request = formal_request("mp-hover-focus-content-run")
        identity_fields = ("observation_request_ref", "request_signature", "criterion_evaluation_ref",
            "procedure_execution_ref", "machine_probe_key", "sample_ref", "variation_ref", "process_ref",
            "requirement_ref", "target_identity", "currentness_dependency")
        partial = {field: request[field] for field in identity_fields}
        partial.update({"status": "incomplete", "current_document_identity": request["target_identity"],
            "evidence_refs": ["WCAG-OBS-001"],
            "limitation": "the fixed probe lacks a declared operation input",
            "value": {"schema": "wcag-test-partial-v1", "observation_completeness": {
                "state": "partial", "reason": "target-not-materialized"}}})
        normalized = invoke("normalize-wcag-machine-probe-result", {"request": request, "result": partial,
            "current_document_identity": request["target_identity"]}, formal=True)
        self.assertEqual(normalized["runtime_status"], "ok")
        self.assertEqual(normalized["result_status"], "ready")
        self.assertEqual(normalized["support_status"], "partial")
        self.assertEqual(len(normalized["issues"]), 1)
        self.assertFalse(normalized["issues"][0]["blocking"])
        self.assertEqual(normalized["issues"][0]["issue_type"], "wcag_machine_observation_incomplete")
        self.assertEqual(normalized["issues"][0]["reason"], "target-not-materialized")
        self.assertEqual(normalized["payload"]["result"]["status"], "incomplete")

        stale = invoke("normalize-wcag-machine-probe-result", {"request": request,
            "result": {**partial, "current_document_identity": DOCUMENT_IDENTITY_B},
            "current_document_identity": request["target_identity"]}, formal=True)
        self.assertEqual(stale["result_status"], "blocked")
        self.assertEqual(stale["payload"]["result"]["status"], "blocked")

    def test_focus_limit_and_population_change_remain_typed_partial_evidence(self):
        for probe_key, reason in (
            ("mp-focus-sequence-run", "focus-observation-limit-reached"),
            ("mp-focus-sequence-run", "focus-loop-detected"),
            ("mp-focus-sequence-run", "focus-cycle-not-complete"),
            ("mp-focus-sequence-run", "focus-left-document"),
            ("mp-focus-sequence-run", "focus-target-removed"),
            ("mp-target-geometry", "population-changed-during-observation"),
            ("mp-audio-autoplay-run", "media-playback-origin-not-instrumented"),
            ("mp-moving-updating-inventory", "probe-result-limit-reached"),
            ("mp-neighbor-geometry", "probe-result-limit-reached"),
            ("mp-text-presentation-values", "probe-result-limit-reached"),
            ("mp-computed-color-context", "probe-result-limit-reached"),
            ("mp-reflow-run", "probe-result-limit-reached"),
            ("mp-text-spacing-run", "text-spacing-override-not-applied"),
        ):
            request = formal_request_for_contract(probe_key)
            identity_fields = ("observation_request_ref", "request_signature", "criterion_evaluation_ref",
                "procedure_execution_ref", "machine_probe_key", "sample_ref", "variation_ref", "process_ref",
                "requirement_ref", "target_identity", "currentness_dependency")
            partial = {field: request[field] for field in identity_fields}
            partial.update({"status": "incomplete", "current_document_identity": request["target_identity"],
                "evidence_refs": ["WCAG-PARTIAL-001"], "limitation": "bounded observation was not complete",
                "value": {"schema": "wcag-bounded-observation-v1",
                    "observation_completeness": {"state": "partial", "reason": reason}}})
            with self.subTest(probe_key=probe_key, reason=reason):
                normalized = invoke("normalize-wcag-machine-probe-result", {"request": request,
                    "result": partial, "current_document_identity": request["target_identity"]}, formal=True)
                self.assertEqual(normalized["runtime_status"], "ok")
                self.assertEqual(normalized["result_status"], "ready")
                self.assertEqual(normalized["support_status"], "partial")
                self.assertEqual(normalized["payload"]["result"]["status"], "incomplete")
                self.assertEqual(normalized["issues"][0]["reason"], reason)
                self.assertFalse(normalized["issues"][0]["blocking"])

    def test_catalogued_incomplete_focus_limitation_closes_for_manual_fallback(self):
        request = formal_request("mp-focus-appearance-evidence", level="AAA")
        identity_fields = ("observation_request_ref", "request_signature", "criterion_evaluation_ref",
            "procedure_execution_ref", "machine_probe_key", "sample_ref", "variation_ref", "process_ref",
            "requirement_ref", "target_identity", "currentness_dependency")
        limitation = {field: request[field] for field in identity_fields}
        limitation.update({"status": "incomplete", "current_document_identity": request["target_identity"],
            "evidence_refs": ["OBS-FOCUS"],
            "limitation": "The focus appearance contains layered styling that the machine probe cannot resolve.",
            "limitation_code": "focus-indicator-not-machine-resolvable",
            "value": {"schema": "wcag-focus-appearance-observation-v1", "visual_screenshot_required": True}})
        normalized = invoke("normalize-wcag-machine-probe-result", {"request": request, "result": limitation,
            "current_document_identity": request["target_identity"]}, formal=True)
        self.assertEqual(normalized["runtime_status"], "ok")
        self.assertEqual(normalized["result_status"], "ready")
        self.assertEqual(normalized["support_status"], "supported")
        self.assertEqual(normalized["issues"], [])
        self.assertEqual(normalized["payload"]["result"]["limitation_code"],
            "focus-indicator-not-machine-resolvable")

    def test_untyped_formal_partial_result_is_rejected(self):
        request = formal_request("mp-hover-focus-content-run")
        identity_fields = ("observation_request_ref", "request_signature", "criterion_evaluation_ref",
            "procedure_execution_ref", "machine_probe_key", "sample_ref", "variation_ref", "process_ref",
            "requirement_ref", "target_identity", "currentness_dependency")
        partial = {field: request[field] for field in identity_fields}
        partial.update({"status": "incomplete", "current_document_identity": request["target_identity"],
            "evidence_refs": ["WCAG-OBS-001"], "limitation": "missing typed reason", "value": {}})
        normalized = invoke("normalize-wcag-machine-probe-result", {"request": request, "result": partial,
            "current_document_identity": request["target_identity"]}, formal=True)
        self.assertEqual(normalized["runtime_status"], "invalid_input")

    def test_partial_candidate_summaries_reject_accessible_name_text(self):
        marker = "ZXQ_PRIVATE_LABEL_UNMATCHED_9f17c3b1d204"
        cases = (
            ("mp-hover-focus-content-run", "target-not-materialized",
             {"schema": "wcag-hover-focus-content-run-v1", "candidate_targets": [
                 {"target_ref": "dom-target:body > button:nth-of-type(1)", "role": "button",
                  "accessible_name_present": True, "focused": False}], "transition_observed": False}),
            ("mp-pointer-interaction-run", "pointer-action-not-materialized",
             {"schema": "wcag-pointer-interaction-run-v1", "candidate_targets": [
                 {"target_ref": "dom-target:body > button:nth-of-type(1)", "role": "button",
                  "accessible_name_present": True, "draggable": False, "input_type": None}],
              "pointer_action_executed": False}),
            ("mp-multipage-signature", "page-set-not-materialized",
             {"schema": "wcag-multipage-signature-v1", "current_page_signature": {
                 "title_present": True, "language_present": True, "controls": [
                     {"target_ref": "dom-target:body > button:nth-of-type(1)", "role": "button",
                      "accessible_name_present": True, "has_help_relationship": False}]},
              "selected_page_set_available": False}),
        )
        identity_fields = ("observation_request_ref", "request_signature", "criterion_evaluation_ref",
            "procedure_execution_ref", "machine_probe_key", "sample_ref", "variation_ref", "process_ref",
            "requirement_ref", "target_identity", "currentness_dependency")

        for probe_key, reason, value in cases:
            request = formal_request(probe_key)
            value["observation_completeness"] = {"state": "partial", "reason": reason}
            candidate_rows = (value["current_page_signature"]["controls"] if probe_key == "mp-multipage-signature"
                              else value["candidate_targets"])
            candidate_rows[0]["accessible_name"] = marker
            result = {field: request[field] for field in identity_fields}
            result.update({"status": "incomplete", "current_document_identity": request["target_identity"],
                "evidence_refs": ["WCAG-PARTIAL-NAME-001"], "limitation": "candidate identity only",
                "value": value})

            rejected = invoke("normalize-wcag-machine-probe-result", {"request": request, "result": result,
                "current_document_identity": request["target_identity"]}, formal=True)
            self.assertEqual(rejected["runtime_status"], "invalid_input")
            self.assertNotIn(marker, json.dumps(rejected))

            del candidate_rows[0]["accessible_name"]
            normalized = invoke("normalize-wcag-machine-probe-result", {"request": request, "result": result,
                "current_document_identity": request["target_identity"]}, formal=True)
            self.assertEqual(normalized["runtime_status"], "ok")
            self.assertEqual(normalized["result_status"], "ready")
            self.assertEqual(normalized["support_status"], "partial")
            self.assertNotIn(marker, json.dumps(normalized))
            normalized_value = normalized["payload"]["result"]["value"]
            normalized_rows = (normalized_value["current_page_signature"]["controls"]
                               if probe_key == "mp-multipage-signature"
                               else normalized_value["candidate_targets"])
            self.assertTrue(all("accessible_name" not in row for row in normalized_rows))


if __name__ == "__main__":
    unittest.main()
