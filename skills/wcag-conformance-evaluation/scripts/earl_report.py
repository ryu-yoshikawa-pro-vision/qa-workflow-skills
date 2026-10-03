"""Deterministic EARL 1.0 / JSON-LD 1.1 sidecar serialization."""
from __future__ import annotations

from datetime import datetime
import hashlib
import json
import re
from typing import Any

from wcag_requirements import load_catalog


CONTEXT = {
    "earl": "http://www.w3.org/ns/earl#",
    "dct": "http://purl.org/dc/terms/",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
}
OUTCOMES = {
    "satisfied": "earl:passed",
    "not-satisfied": "earl:failed",
    "undetermined": "earl:cantTell",
}
MODES = {"automatic", "manual", "semiAuto", "undisclosed", "unknownMode"}
FINGERPRINT = re.compile(r"^sha256:[0-9a-f]{64}$")


class EarlError(ValueError):
    pass


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def stable_iri(kind: str, identity: dict[str, Any]) -> str:
    if kind not in {"assertor", "subject", "assertion", "result"} or not identity:
        raise EarlError("EARL node kind and canonical identity are required")
    digest = hashlib.sha256(canonical_json(identity)).hexdigest()
    return f"urn:qa-workflow-skills:earl:{kind}:{digest}"


def _mode_from_provenance(result: dict[str, Any]) -> str:
    provenance = result.get("procedure_provenance")
    if not isinstance(provenance, list) or not provenance:
        return "earl:unknownMode"
    values: set[str] = set()
    for row in provenance:
        if not isinstance(row, dict):
            raise EarlError("procedure provenance row must be an object")
        value = row.get("mode")
        if value in {"automatic", "earl:automatic"}:
            values.add("earl:automatic")
        elif value in {"manual", "assistive-technology", "earl:manual"}:
            values.add("earl:manual")
        elif value in {"semiAuto", "semi-automatic", "earl:semiAuto"}:
            values.add("earl:semiAuto")
        elif value in {"undisclosed", "earl:undisclosed"}:
            values.add("earl:undisclosed")
        elif value in {"unknown", "unknownMode", "external-evidence", "earl:unknownMode"}:
            values.add("earl:unknownMode")
        else:
            raise EarlError(f"unknown procedure provenance mode: {value}")
    return next(iter(values)) if len(values) == 1 else "earl:unknownMode"


def _test_uri(catalog: dict[str, Any], result: dict[str, Any]) -> str:
    requirement = result.get("requirement_ref") or result.get("criterion_ref")
    if not isinstance(requirement, str) or not requirement:
        raise EarlError("formal requirement ref is required")
    criteria = {row["criterion_ref"]: row["canonical_uri"] for row in catalog["success_criteria"]}
    requirements = {row["requirement_key"]: row["canonical_uri"] for row in catalog["conformance_requirements"]}
    uri = criteria.get(requirement) or requirements.get(requirement)
    if uri is None:
        raise EarlError(f"requirement is not in the selected WCAG version: {requirement}")
    return uri


def _issued_date(value: str | None) -> dict[str, str] | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise EarlError("issued date must be a non-empty RFC 3339 string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise EarlError("issued date must be RFC 3339") from exc
    if parsed.tzinfo is None:
        raise EarlError("issued date must include an offset")
    return {"@value": value, "@type": "xsd:dateTime"}


def _ordered_node(node: dict[str, Any]) -> dict[str, Any]:
    ordered: dict[str, Any] = {"@id": node["@id"]}
    if "@type" in node:
        ordered["@type"] = node["@type"]
    ordered.update({key: node[key] for key in sorted(set(node) - {"@id", "@type"})})
    return ordered


def serialize_assertions(*, evaluation_ref: str, evaluation_revision: str, version: str,
                         results: list[dict[str, Any]], evaluator_identity: str,
                         tool_identity: str, sample_identities: dict[str, str],
                         variation_identities: dict[str, str], issued_at: str | None = None) -> bytes:
    """Render one EARL Assertion/TestResult pair for every closed formal result."""
    if not all(isinstance(value, str) and value.strip() for value in
               (evaluation_ref, evaluation_revision, evaluator_identity, tool_identity)):
        raise EarlError("evaluation, revision, evaluator, and tool identities are required")
    catalog = load_catalog(version)
    assertor_identity = {"evaluator_identity": evaluator_identity, "tool_identity": tool_identity,
                         "evaluation_revision": evaluation_revision}
    assertor_id = stable_iri("assertor", assertor_identity)
    graph: list[dict[str, Any]] = [{"@id": assertor_id, "@type": ["earl:Assertor", "earl:Software"]}]
    result_refs: set[str] = set()
    assertion_ids: set[str] = set()
    subject_ids: set[str] = set()
    date_value = _issued_date(issued_at)
    for result in results:
        status = result.get("result")
        population = result.get("applicable_population")
        execution = result.get("execution_status")
        explicit_untested = result.get("explicit_untested") is True
        if status == "untested":
            if execution != "not-run" or not explicit_untested:
                raise EarlError("earl:untested requires an explicit not-run result")
            outcome = "earl:untested"
        else:
            if status not in OUTCOMES or population not in {"present", "none", "unknown"} or execution != "complete":
                raise EarlError("EARL requires a closed current criterion result")
            if population == "unknown" and status != "undetermined":
                raise EarlError("unknown population cannot be serialized as passed or failed")
            if population == "none":
                if status != "satisfied":
                    raise EarlError("complete empty Success Criterion population must remain satisfied in the report")
                outcome = "earl:inapplicable"
            else:
                outcome = OUTCOMES[status]
        evaluation_item_ref = result.get("criterion_evaluation_ref") or result.get("requirement_evaluation_ref")
        result_ref = result.get("result_ref") or result.get("sample_result_ref")
        sample_ref = result.get("sample_ref")
        variation_ref = result.get("variation_ref")
        if not all(isinstance(value, str) and value.strip() for value in
                   (evaluation_item_ref, result_ref, sample_ref, variation_ref)):
            raise EarlError("result, sample, variation, and evaluation refs are required")
        if result_ref in result_refs:
            raise EarlError("duplicate formal result identity")
        result_refs.add(result_ref)
        sample_identity = sample_identities.get(sample_ref)
        variation_identity = variation_identities.get(variation_ref)
        if not isinstance(sample_identity, str) or not FINGERPRINT.fullmatch(sample_identity) or not isinstance(variation_identity, str) or not FINGERPRINT.fullmatch(variation_identity):
            raise EarlError("canonical sample and presentation variation identities are required")
        subject_id = stable_iri("subject", {"evaluation_ref": evaluation_ref,
            "sample_identity": sample_identity, "variation_identity": variation_identity})
        if subject_id not in subject_ids:
            graph.append({"@id": subject_id, "@type": "earl:TestSubject"})
            subject_ids.add(subject_id)
        test_uri = _test_uri(catalog, result)
        assertion_identity = {"evaluation_ref": evaluation_ref, "evaluation_revision": evaluation_revision,
                              "subject_iri": subject_id, "test_uri": test_uri,
                              "result_identity": {"evaluation_item_ref": evaluation_item_ref, "result_ref": result_ref}}
        assertion_id = stable_iri("assertion", assertion_identity)
        result_id = stable_iri("result", {"assertion_identity": assertion_identity,
                                           "evaluation_item_ref": evaluation_item_ref, "result_ref": result_ref})
        if assertion_id in assertion_ids:
            raise EarlError("duplicate EARL assertion identity")
        assertion_ids.add(assertion_id)
        result_node: dict[str, Any] = {"@id": result_id, "@type": "earl:TestResult",
                                       "earl:outcome": {"@id": outcome}}
        if date_value is not None:
            result_node["dct:date"] = date_value
        graph.append(result_node)
        graph.append({"@id": assertion_id, "@type": "earl:Assertion",
                      "earl:assertedBy": {"@id": assertor_id}, "earl:subject": {"@id": subject_id},
                      "earl:test": {"@id": test_uri}, "earl:result": {"@id": result_id},
                      "earl:mode": {"@id": _mode_from_provenance(result)}})
    graph = [_ordered_node(node) for node in graph]
    graph.sort(key=lambda node: node["@id"])
    document = {"@context": CONTEXT, "@graph": graph}
    return (json.dumps(document, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
