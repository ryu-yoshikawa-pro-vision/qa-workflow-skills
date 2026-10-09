from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[4]
WCAG_SCRIPTS = ROOT / "skills/wcag-conformance-evaluation/scripts"
sys.path.insert(0, str(WCAG_SCRIPTS))


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


renderer = load("wcag_earl_report_contract_test", WCAG_SCRIPTS / "earl_report.py")
validator = load("wcag_earl_validator_contract_test", WCAG_SCRIPTS.parent / "evals/deterministic/earl_validator.py")


def formal_results() -> list[dict]:
    return [
        {"criterion_ref": "1.1.1", "criterion_evaluation_ref": "CRIT-EVAL-000001",
         "result_ref": "SAMPLE-RESULT-000001", "sample_ref": "SAMPLE-001", "variation_ref": "VAR-001",
         "evaluation_ref":"WCAG-EVAL-001", "evaluation_revision":"rev-7", "freshness_status":"current",
         "result": "satisfied", "applicable_population": "present", "execution_status": "complete",
         "procedure_provenance": [{"mode": "automatic"}, {"mode": "manual"}]},
        {"criterion_ref": "3.3.7", "criterion_evaluation_ref": "CRIT-EVAL-000002",
         "result_ref": "SAMPLE-RESULT-000002", "sample_ref": "SAMPLE-001", "variation_ref": "VAR-001",
         "evaluation_ref":"WCAG-EVAL-001", "evaluation_revision":"rev-7", "freshness_status":"current",
         "result": "satisfied", "applicable_population": "none", "execution_status": "complete",
         "procedure_provenance": [{"mode": "manual"}]},
        {"criterion_ref": "2.4.11", "criterion_evaluation_ref": "CRIT-EVAL-000003",
         "result_ref": "SAMPLE-RESULT-000003", "sample_ref": "SAMPLE-002", "variation_ref": "VAR-002",
         "evaluation_ref":"WCAG-EVAL-001", "evaluation_revision":"rev-7", "freshness_status":"current",
         "result": "untested", "execution_status": "not-run", "explicit_untested": True,
         "procedure_provenance": []},
    ]


def identity_inputs() -> tuple[dict[str, str], dict[str, str]]:
    return ({"SAMPLE-001": "sha256:" + "1" * 64, "SAMPLE-002": "sha256:" + "2" * 64},
            {"VAR-001": "sha256:" + "a" * 64, "VAR-002": "sha256:" + "b" * 64})


def render(results: list[dict] | None = None) -> bytes:
    sample_ids, variation_ids = identity_inputs()
    return renderer.serialize_assertions(
        evaluation_ref="WCAG-EVAL-001", evaluation_revision="rev-7", version="2.2",
        results=formal_results() if results is None else results, evaluator_identity="qa-agent",
        tool_identity="qa-workflow-skills", sample_identities=sample_ids,
        variation_identities=variation_ids, issued_at="2026-09-28T12:30:00Z")


class EarlSerializationContractTests(unittest.TestCase):
    def validate(self, raw: bytes, results: list[dict] | None = None) -> list[str]:
        sample_ids, variation_ids = identity_inputs()
        return validator.validate_bytes(
            raw, version="2.2", evaluation_ref="WCAG-EVAL-001", evaluation_revision="rev-7",
            evaluator_identity="qa-agent", tool_identity="qa-workflow-skills",
            results=formal_results() if results is None else results,
            sample_identities=sample_ids, variation_identities=variation_ids,
            issued_at="2026-09-28T12:30:00Z")

    def test_fixed_jsonld_graph_and_human_result_coverage(self):
        raw = render()
        self.assertEqual(self.validate(raw), [])
        document = json.loads(raw)
        self.assertEqual(document["@context"], renderer.CONTEXT)
        self.assertEqual(len([node for node in document["@graph"] if node.get("@type") == "earl:Assertion"]), 3)
        self.assertEqual(len([node for node in document["@graph"] if node.get("@type") == "earl:TestResult"]), 3)
        outcomes = {node["@id"]: node["earl:outcome"]["@id"] for node in document["@graph"]
                    if node.get("@type") == "earl:TestResult"}
        self.assertCountEqual(outcomes.values(), ["earl:passed", "earl:inapplicable", "earl:untested"])
        self.assertNotIn(b"https://fixture.example", raw)

    def test_serialization_is_stable_across_result_input_order(self):
        rows = formal_results()
        self.assertEqual(render(rows), render(list(reversed(rows))))

    def test_validator_rejects_result_mismatch_unresolved_reference_and_noncanonical_bytes(self):
        document = json.loads(render())
        result_node = next(node for node in document["@graph"] if node.get("@type") == "earl:TestResult")
        result_node["earl:outcome"] = {"@id": "earl:failed"}
        tampered = (json.dumps(document, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        self.assertIn("formal_outcome_mismatch", self.validate(tampered))
        self.assertIn("serialization_not_canonical_utf8_lf_indent2", self.validate(render().replace(b"\n", b"\r\n")))

    def test_renderer_rejects_out_of_version_criterion_duplicate_result_and_implicit_untested(self):
        bad_version = [{**formal_results()[0], "criterion_ref": "4.1.1"}]
        with self.assertRaises(renderer.EarlError):
            render(bad_version)
        duplicated = formal_results()[:1] * 2
        with self.assertRaises(renderer.EarlError):
            render(duplicated)
        implicit = [{**formal_results()[0], "result": "untested", "execution_status": "not-run",
                     "explicit_untested": False}]
        with self.assertRaises(renderer.EarlError):
            render(implicit)

    def test_renderer_rejects_invalid_identity_and_unknown_provenance(self):
        sample_ids, variation_ids = identity_inputs()
        sample_ids["SAMPLE-001"] = "sha256:bad"
        with self.assertRaises(renderer.EarlError):
            renderer.serialize_assertions(evaluation_ref="E", evaluation_revision="r", version="2.2",
                results=formal_results()[:1], evaluator_identity="agent", tool_identity="tool",
                sample_identities=sample_ids, variation_identities=variation_ids)
        unknown = [{**formal_results()[0], "procedure_provenance": [{"mode": "invented"}]}]
        with self.assertRaises(renderer.EarlError):
            render(unknown)

    def test_stale_or_wrong_revision_results_cannot_become_current_earl_outcomes(self):
        for changed in ({"freshness_status":"stale"}, {"evaluation_revision":"rev-6"}):
            for outcome in ("satisfied", "not-satisfied"):
                row = {**formal_results()[0], **changed, "result":outcome}
                with self.subTest(changed=changed, outcome=outcome):
                    with self.assertRaises(renderer.EarlError):
                        render([row])
                    self.assertIn("normalized_result_not_current", self.validate(render(), [row]))


if __name__ == "__main__":
    unittest.main()
