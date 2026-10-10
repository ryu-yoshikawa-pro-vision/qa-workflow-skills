"""Versioned WCAG requirement selection and static catalog validation."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any
from runtime_contract import static_data_fingerprint

SUPPORTED_VERSIONS = ("2.0", "2.1", "2.2")
LEVELS = {"A": 1, "AA": 2, "AAA": 3}
CONFORMANCE_REQUIREMENTS = {"conformance-level", "full-pages", "complete-processes", "accessibility-supported-ways", "non-interference"}
ASSETS = Path(__file__).resolve().parents[1] / "assets"


class RequirementError(ValueError):
    pass


def load_catalog(version: str, *, assets_dir: Path = ASSETS) -> dict[str, Any]:
    if version not in SUPPORTED_VERSIONS:
        raise RequirementError(f"unsupported WCAG version: {version}")
    path = assets_dir / f"wcag-{version}-requirements.json"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RequirementError(f"cannot load WCAG {version} requirement catalog") from exc
    validate_catalog(value, version)
    return value


def resolve_target(version: str | None, level: str | None, *, assets_dir: Path = ASSETS) -> dict[str, Any]:
    if not version or not level:
        return {"status": "unresolved", "reason": "wcag_version_or_level_missing", "version": version, "level": level}
    if version not in SUPPORTED_VERSIONS:
        return {"status": "unsupported", "reason": "version_not_supported_or_out_of_scope", "version": version, "level": level}
    if level not in LEVELS:
        return {"status": "unresolved", "reason": "invalid_or_missing_conformance_level", "version": version, "level": level}
    catalog = load_catalog(version, assets_dir=assets_dir)
    max_level = LEVELS[level]
    required = sorted((row["criterion_ref"] for row in catalog["success_criteria"] if LEVELS[row["level"]] <= max_level), key=_criterion_sort)
    return {"status": "supported", "version": version, "level": level,
            "required_success_criteria": required,
            "required_conformance_requirements": sorted(CONFORMANCE_REQUIREMENTS),
            "catalog_fingerprint": static_data_fingerprint(assets_dir / f"wcag-{version}-requirements.json")}


def _criterion_sort(value: str) -> tuple[int, int, int]:
    return tuple(int(part) for part in value.split("."))


def validate_catalog(catalog: dict[str, Any], version: str) -> None:
    if set(catalog) != {"schema_version", "wcag_version", "source", "success_criteria", "conformance_requirements",
                        "conforming_alternate_version_contract", "claim_contract", "evaluation_statement_contract",
                        "statement_of_partial_conformance_contract"}:
        raise RequirementError("requirements catalog top-level schema mismatch")
    if catalog.get("schema_version") != "1" or catalog.get("wcag_version") != version:
        raise RequirementError("catalog version/schema mismatch")
    rows = catalog.get("success_criteria")
    if not isinstance(rows, list) or not rows:
        raise RequirementError("success_criteria must be non-empty")
    refs = [row.get("criterion_ref") for row in rows]
    if len(refs) != len(set(refs)) or any(not isinstance(ref, str) for ref in refs):
        raise RequirementError("criterion refs must be unique strings")
    if version == "2.2" and "4.1.1" in refs:
        raise RequirementError("WCAG 2.2 must not contain 4.1.1")
    if len(rows) != {"2.0":61,"2.1":78,"2.2":86}[version]:
        raise RequirementError("versioned WCAG Success Criterion set is incomplete")
    for row in rows:
        if set(row) != {"criterion_ref", "title", "level", "canonical_uri", "procedure_keys", "external_evidence_allowed"}:
            raise RequirementError(f"criterion schema mismatch: {row.get('criterion_ref')}")
        if row["level"] not in LEVELS or not row["title"] or not row["canonical_uri"]:
            raise RequirementError(f"criterion metadata incomplete: {row['criterion_ref']}")
        if not isinstance(row["procedure_keys"], list) or f"s-wcag-{row['criterion_ref']}" not in row["procedure_keys"]:
            raise RequirementError(f"criterion semantic procedure missing: {row['criterion_ref']}")
        if not isinstance(row["external_evidence_allowed"],bool):
            raise RequirementError(f"external evidence allowance must be explicit: {row['criterion_ref']}")
    conformance = catalog.get("conformance_requirements", [])
    keys = [row.get("requirement_key") for row in conformance]
    if set(keys) != CONFORMANCE_REQUIREMENTS or len(keys) != len(set(keys)):
        raise RequirementError("conformance requirement set mismatch")
    if set(catalog["claim_contract"].get("required_fields", [])) == set():
        raise RequirementError("claim contract has no required fields")
    statement = catalog["evaluation_statement_contract"]
    if version == "2.2" and not statement.get("enabled"):
        raise RequirementError("WCAG 2.2 Evaluation Statement must be available")
    if version != "2.2" and statement.get("enabled"):
        raise RequirementError("WCAG 2.0/2.1 must not create Step 5.3 Evaluation Statement")
