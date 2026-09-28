"""Independent structural and byte validator for the fixed EARL sidecar."""
from __future__ import annotations

from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
from typing import Any


ASSETS = Path(__file__).resolve().parents[2] / "assets"
CONTEXT = {"earl": "http://www.w3.org/ns/earl#", "dct": "http://purl.org/dc/terms/",
           "xsd": "http://www.w3.org/2001/XMLSchema#"}
OUTCOMES = {"earl:passed", "earl:failed", "earl:cantTell", "earl:inapplicable", "earl:untested"}
MODES = {"earl:automatic", "earl:manual", "earl:semiAuto", "earl:undisclosed", "earl:unknownMode"}
IRI_RE = re.compile(r"^urn:qa-workflow-skills:earl:(assertor|subject|assertion|result):[0-9a-f]{64}$")


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _stable_iri(kind: str, identity: dict[str, Any]) -> str:
    return f"urn:qa-workflow-skills:earl:{kind}:{hashlib.sha256(_canonical(identity)).hexdigest()}"


def _catalog(version: str) -> dict[str, Any]:
    return json.loads((ASSETS / f"wcag-{version}-requirements.json").read_text(encoding="utf-8"))


def _mode(result: dict[str, Any]) -> str:
    provenance = result.get("procedure_provenance")
    if not isinstance(provenance, list) or not provenance:
        return "earl:unknownMode"
    mapped = set()
    for row in provenance:
        value = row.get("mode")
        mapped.add({"automatic": "earl:automatic", "earl:automatic": "earl:automatic",
                    "manual": "earl:manual", "assistive-technology": "earl:manual", "earl:manual": "earl:manual",
                    "semiAuto": "earl:semiAuto", "semi-automatic": "earl:semiAuto", "earl:semiAuto": "earl:semiAuto",
                    "undisclosed": "earl:undisclosed", "earl:undisclosed": "earl:undisclosed",
                    "unknown": "earl:unknownMode", "unknownMode": "earl:unknownMode",
                    "external-evidence": "earl:unknownMode", "earl:unknownMode": "earl:unknownMode"}[value])
    return next(iter(mapped)) if len(mapped) == 1 else "earl:unknownMode"


def _test_uri(catalog: dict[str, Any], result: dict[str, Any]) -> str | None:
    ref = result.get("requirement_ref") or result.get("criterion_ref")
    allowed = {row["criterion_ref"]: row["canonical_uri"] for row in catalog["success_criteria"]}
    allowed.update({row["requirement_key"]: row["canonical_uri"] for row in catalog["conformance_requirements"]})
    return allowed.get(ref)


def _outcome(result: dict[str, Any]) -> str | None:
    value, population = result.get("result"), result.get("applicable_population")
    if value == "untested":
        return "earl:untested" if result.get("execution_status") == "not-run" and result.get("explicit_untested") is True else None
    if result.get("execution_status") != "complete" or value not in {"satisfied", "not-satisfied", "undetermined"}:
        return None
    if population == "unknown" and value != "undetermined":
        return None
    if population == "none":
        return "earl:inapplicable" if value == "satisfied" else None
    return {"satisfied": "earl:passed", "not-satisfied": "earl:failed", "undetermined": "earl:cantTell"}.get(value)


def validate_bytes(raw: bytes, *, version: str, evaluation_ref: str, evaluation_revision: str,
                   evaluator_identity: str, tool_identity: str, results: list[dict[str, Any]],
                   sample_identities: dict[str, str], variation_identities: dict[str, str],
                   issued_at: str | None = None) -> list[str]:
    errors: list[str] = []
    try:
        document = json.loads(raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError):
        return ["earl_json_parse"]
    if not isinstance(document, dict) or set(document) != {"@context", "@graph"}:
        errors.append("top_level_keys")
        return errors
    if document.get("@context") != CONTEXT or list(document.get("@context", {})) != ["earl", "dct", "xsd"]:
        errors.append("fixed_context")
    graph = document.get("@graph")
    if not isinstance(graph, list):
        return errors + ["graph_not_array"]
    ids = [node.get("@id") for node in graph if isinstance(node, dict)]
    if len(ids) != len(graph) or len(ids) != len(set(ids)):
        errors.append("graph_node_id_duplicate_or_missing")
    if ids != sorted(ids):
        errors.append("graph_node_order")
    for node in graph:
        if not isinstance(node, dict) or not isinstance(node.get("@id"), str) or not IRI_RE.fullmatch(node["@id"]):
            errors.append("stable_iri_invalid")
            continue
        keys = list(node)
        if keys[:1] != ["@id"] or ("@type" in node and keys[:2] != ["@id", "@type"]):
            errors.append("node_property_prefix_order")
        remainder = keys[2:] if "@type" in node else keys[1:]
        if remainder != sorted(remainder):
            errors.append("node_property_order")
    by_id = {node.get("@id"): node for node in graph if isinstance(node, dict)}
    assertors = [node for node in graph if isinstance(node.get("@type"), list) and "earl:Assertor" in node["@type"]]
    subjects = [node for node in graph if node.get("@type") == "earl:TestSubject"]
    assertions = [node for node in graph if node.get("@type") == "earl:Assertion"]
    results_nodes = [node for node in graph if node.get("@type") == "earl:TestResult"]
    if len(assertors) != 1 or assertors[0].get("@type") != ["earl:Assertor", "earl:Software"]:
        errors.append("assertor_node_contract")
    else:
        expected_assertor = _stable_iri("assertor", {"evaluator_identity": evaluator_identity,
            "tool_identity": tool_identity, "evaluation_revision": evaluation_revision})
        if assertors[0].get("@id") != expected_assertor or set(assertors[0]) != {"@id", "@type"}:
            errors.append("assertor_identity_mismatch")
    if len(assertions) != len(results) or len(results_nodes) != len(results):
        errors.append("human_result_assertion_count")
    if any(set(node) != {"@id", "@type"} for node in subjects):
        errors.append("subject_node_schema")
    catalog = _catalog(version)
    allowed_tests = {row["canonical_uri"] for row in catalog["success_criteria"]}
    allowed_tests.update(row["canonical_uri"] for row in catalog["conformance_requirements"])
    assertion_by_test: dict[str, dict[str, Any]] = {}
    used_result_ids: set[str] = set()
    for assertion in assertions:
        required = {"@id", "@type", "earl:assertedBy", "earl:subject", "earl:test", "earl:result", "earl:mode"}
        if set(assertion) != required or "earl:outcome" in assertion:
            errors.append("assertion_schema_or_outcome_location")
        for field in ("earl:assertedBy", "earl:subject", "earl:test", "earl:result", "earl:mode"):
            item = assertion.get(field)
            if not isinstance(item, dict) or set(item) != {"@id"} or not isinstance(item.get("@id"), str):
                errors.append(f"iri_value_object:{field}")
        asserted_by = assertion.get("earl:assertedBy", {}).get("@id") if isinstance(assertion.get("earl:assertedBy"),dict) else None
        subject = assertion.get("earl:subject", {}).get("@id") if isinstance(assertion.get("earl:subject"),dict) else None
        test = assertion.get("earl:test", {}).get("@id") if isinstance(assertion.get("earl:test"),dict) else None
        result_id = assertion.get("earl:result", {}).get("@id") if isinstance(assertion.get("earl:result"),dict) else None
        mode = assertion.get("earl:mode", {}).get("@id") if isinstance(assertion.get("earl:mode"),dict) else None
        if asserted_by not in by_id or subject not in by_id or result_id not in by_id:
            errors.append("assertion_reference_unresolved")
        if test not in allowed_tests:
            errors.append("versioned_test_uri_invalid")
        if mode not in MODES:
            errors.append("mode_iri_invalid")
        if result_id:
            used_result_ids.add(result_id)
            node = by_id.get(result_id, {})
            if node.get("@type") != "earl:TestResult" or set(node) - {"@id", "@type", "earl:outcome", "dct:date"}:
                errors.append("test_result_schema")
            outcome = node.get("earl:outcome")
            if not isinstance(outcome, dict) or set(outcome) != {"@id"} or outcome.get("@id") not in OUTCOMES:
                errors.append("outcome_iri_invalid")
            date = node.get("dct:date")
            if date is not None and (not isinstance(date, dict) or date.get("@type") != "xsd:dateTime" or not isinstance(date.get("@value"), str)):
                errors.append("result_date_schema")
        if test in assertion_by_test:
            # Same criterion can appear for multiple canonical samples/variations.
            pass
        else:
            assertion_by_test[test] = assertion
    if used_result_ids != {node.get("@id") for node in results_nodes}:
        errors.append("orphan_test_result")
    expected_assertions: dict[str, tuple[str, str, str, str]] = {}
    expected_subjects: set[str] = set()
    expected_result_ids: set[str] = set()
    expected_outcomes: dict[str, tuple[str, str]] = {}
    expected_assertor = _stable_iri("assertor", {"evaluator_identity": evaluator_identity,
        "tool_identity": tool_identity, "evaluation_revision": evaluation_revision})
    for result in results:
        test = _test_uri(catalog, result)
        outcome = _outcome(result)
        item_ref = result.get("criterion_evaluation_ref") or result.get("requirement_evaluation_ref")
        result_ref = result.get("result_ref") or result.get("sample_result_ref")
        sample_ref, variation_ref = result.get("sample_ref"), result.get("variation_ref")
        if not test or not outcome or not all(isinstance(v, str) and v for v in (item_ref, result_ref, sample_ref, variation_ref)):
            errors.append("normalized_human_result_invalid")
            continue
        sample_fp, variation_fp = sample_identities.get(sample_ref), variation_identities.get(variation_ref)
        if not isinstance(sample_fp, str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", sample_fp) or not isinstance(variation_fp, str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", variation_fp):
            errors.append("canonical_subject_identity_missing")
            continue
        subject_id = _stable_iri("subject", {"evaluation_ref": evaluation_ref,
            "sample_identity": sample_fp, "variation_identity": variation_fp})
        expected_subjects.add(subject_id)
        assertion_identity = {"evaluation_ref": evaluation_ref, "evaluation_revision": evaluation_revision,
            "subject_iri": subject_id, "test_uri": test,
            "result_identity": {"evaluation_item_ref": item_ref, "result_ref": result_ref}}
        assertion_id = _stable_iri("assertion", assertion_identity)
        result_id = _stable_iri("result", {"assertion_identity": assertion_identity,
            "evaluation_item_ref": item_ref, "result_ref": result_ref})
        if assertion_id in expected_assertions:
            errors.append("duplicate_normalized_assertion_identity")
            continue
        expected_assertions[assertion_id] = (subject_id, test, result_id, expected_assertor)
        expected_result_ids.add(result_id)
        expected_outcomes[assertion_id] = (outcome, _mode(result))
        expected_outcomes[assertion_id] = (outcome, _mode(result))
    if set(expected_assertions) != {node.get("@id") for node in assertions}:
        errors.append("normalized_result_assertion_identity_mismatch")
    if expected_subjects != {node.get("@id") for node in subjects}:
        errors.append("normalized_result_subject_identity_mismatch")
    if expected_result_ids != {node.get("@id") for node in results_nodes}:
        errors.append("normalized_result_test_result_identity_mismatch")
    assertion_nodes = {node.get("@id"): node for node in assertions}
    for assertion_id, (subject_id, test_uri, result_id, asserted_by) in expected_assertions.items():
        assertion = assertion_nodes.get(assertion_id, {})
        expected_links = {"earl:assertedBy": asserted_by, "earl:subject": subject_id,
                          "earl:test": test_uri, "earl:result": result_id}
        for field, expected_id in expected_links.items():
            actual = assertion.get(field)
            if not isinstance(actual, dict) or actual.get("@id") != expected_id:
                errors.append(f"normalized_result_reference_mismatch:{field}")
        outcome, mode = expected_outcomes[assertion_id]
        actual_mode = assertion.get("earl:mode")
        if not isinstance(actual_mode, dict) or actual_mode.get("@id") != mode:
            errors.append("provenance_mode_mismatch")
        if by_id.get(result_id, {}).get("earl:outcome", {}).get("@id") != outcome:
            errors.append("formal_outcome_mismatch")
        if issued_at is None and "dct:date" in by_id.get(result_id, {}):
            errors.append("unexpected_result_date")
        elif issued_at is not None:
            date = by_id.get(result_id, {}).get("dct:date")
            if not isinstance(date, dict) or date.get("@value") != issued_at:
                errors.append("result_date_mismatch")
    if issued_at is not None:
        try:
            if datetime.fromisoformat(issued_at.replace("Z", "+00:00")).tzinfo is None:
                errors.append("issued_at_timezone_missing")
        except ValueError:
            errors.append("issued_at_invalid")
    rendered = json.dumps(document, ensure_ascii=False, indent=2) + "\n"
    if raw != rendered.encode("utf-8"):
        errors.append("serialization_not_canonical_utf8_lf_indent2")
    if raw.startswith(b"\xef\xbb\xbf") or b"\r\n" in raw:
        errors.append("serialization_bom_or_crlf")
    return sorted(set(errors))
