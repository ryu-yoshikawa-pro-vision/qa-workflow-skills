from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "skills/usability-inspection/scripts/inspection_runtime.py"


def metadata(*, formal: bool = False) -> dict:
    unit = "artifact:inspection_runtime:formal-machine-probe" if formal else "artifact:inspection_runtime:all"
    return {"envelope_version": "1", "skill": "usability-inspection",
        "runtime_contract_version": "runtime-v1", "generator_contract_version": "usability-inspection-runtime-v1",
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


def formal_request() -> dict:
    sys.path.insert(0, str(ROOT / "skills/wcag-conformance-evaluation/scripts"))
    import wcag_criterion_plan
    plan = wcag_criterion_plan.materialize_plan(wcag_version="2.0", level="AA",
        samples=[{"sample_ref": "SAMPLE-001", "identity_fingerprint": "sha256:" + "a" * 64}],
        variations=[{"sample_ref": "SAMPLE-001", "variation_ref": "VAR-001",
                     "identity_fingerprint": "sha256:" + "b" * 64}])
    return next(request for request in plan["requests"] if request["machine_probe_key"] == "mp-resize-text-run")


class InspectionRuntimeContractTests(unittest.TestCase):
    def test_general_runtime_fingerprints_only_general_observation_assets(self):
        output = invoke("plan-probes", {"selected_rule_keys": ["2779a5"], "measurement_kinds": [],
            "aspect_keys": [], "target_refs": []})
        self.assertEqual(output["runtime_status"], "ok")
        self.assertEqual(output["result_status"], "ready")
        self.assertEqual(output["runtime_unit_key"], "artifact:inspection_runtime:all")
        self.assertEqual(set(output["static_data_versions"]), {"browser_observation_catalog", "test_rule_catalog"})

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
        result = {**{field: request[field] for field in identity_fields}, "status": "ok",
            "current_document_identity": "doc-1", "evidence_refs": ["E-1"], "value": {"population_complete": True}}
        normalized = invoke("normalize-wcag-machine-probe-result", {"request": request, "result": result,
            "current_document_identity": "doc-1"}, formal=True)
        self.assertEqual(normalized["runtime_status"], "ok")
        self.assertEqual(normalized["result_status"], "ready")
        self.assertTrue(normalized["payload"]["result"]["normalized"])
        stale = {**result, "sample_ref": "SAMPLE-OTHER"}
        rejected = invoke("normalize-wcag-machine-probe-result", {"request": request, "result": stale,
            "current_document_identity": "doc-1"}, formal=True)
        self.assertEqual(rejected["runtime_status"], "invalid_input")
        injected = invoke("normalize-observation-probe-result", {"probe": {}, "result": {},
            "current_document_identity": "doc-1", "formal": True})
        self.assertEqual(injected["runtime_status"], "invalid_input")


if __name__ == "__main__":
    unittest.main()
