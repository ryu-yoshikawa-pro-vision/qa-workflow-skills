"""Resolve UI pattern aliases against the repository catalog."""

from __future__ import annotations

import hashlib
from pathlib import Path
import re
from typing import Any

from runtime_contract import (
    InvalidInput,
    canonical_json_bytes,
    canonicalize,
    ensure_nonempty_string,
    make_unsupported_item,
    post_process_targets,
    reject_unknown,
    run_cli,
    strict_loads,
)


SKILL = "test-condition-design"
GENERATOR = "ui_pattern_candidates"
GENERATOR_CONTRACT_VERSION = "ui-pattern-candidates-v1"
SCRIPT_PATH = Path(__file__).resolve()
CATALOG_PATH = Path(__file__).resolve().parents[1] / "assets" / "ui-pattern-catalog.json"
PATTERN_RE = re.compile(r"^[a-z][a-z0-9-]*$")
CATEGORIES = {"interaction", "keyboard", "focus", "state", "value", "validation", "navigation", "lifecycle"}
ATTRIBUTE_KEYS = {"type", "role", "required", "min", "max", "minlength", "maxlength", "step", "disabled", "readonly", "multiple"}


def _refs(value: Any, name: str) -> list[str]:
    if not isinstance(value, list) or len(set(value)) != len(value) or not all(isinstance(item, str) and item for item in value):
        raise InvalidInput(f"{name}が不正です")
    return sorted(value)


def _load_catalog() -> tuple[list[dict[str, Any]], str]:
    try:
        catalog = strict_loads(CATALOG_PATH.read_bytes(), aggregate=True)
    except Exception as exc:
        raise InvalidInput("UI pattern catalogのstrict JSON decodeに失敗しました") from exc
    if not isinstance(catalog, list):
        raise InvalidInput("UI pattern catalogはarrayである必要があります")
    pattern_keys: set[str] = set()
    names_and_aliases: dict[str, str] = {}
    normalized: list[dict[str, Any]] = []
    for pattern in catalog:
        if not isinstance(pattern, dict):
            raise InvalidInput("UI pattern catalog patternが不正です")
        reject_unknown(pattern, {"pattern_key", "name", "aliases", "identifiers", "candidates"})
        pattern_key = pattern["pattern_key"]
        if not isinstance(pattern_key, str) or PATTERN_RE.fullmatch(pattern_key) is None or pattern_key in pattern_keys:
            raise InvalidInput("UI pattern catalog pattern_keyが不正または重複しています")
        pattern_keys.add(pattern_key)
        name = ensure_nonempty_string(pattern["name"], "catalog pattern name")
        aliases = pattern["aliases"]
        identifiers = pattern["identifiers"]
        if not isinstance(aliases, list) or len(set(aliases)) != len(aliases) or not all(isinstance(item, str) and item for item in aliases):
            raise InvalidInput("catalog aliasesが不正です")
        if not isinstance(identifiers, list) or len(set(identifiers)) != len(identifiers) or not all(isinstance(item, str) and item for item in identifiers):
            raise InvalidInput("catalog identifiersが不正です")
        for identity in [pattern_key, name, *aliases]:
            if identity in names_and_aliases and names_and_aliases[identity] != pattern_key:
                raise InvalidInput("catalog pattern name / aliasが衝突しています")
            names_and_aliases[identity] = pattern_key
        candidates_raw = pattern["candidates"]
        if not isinstance(candidates_raw, list):
            raise InvalidInput("catalog candidatesが不正です")
        candidates: list[dict[str, Any]] = []
        candidate_keys: set[str] = set()
        for candidate in candidates_raw:
            if not isinstance(candidate, dict):
                raise InvalidInput("catalog candidateが不正です")
            reject_unknown(candidate, {"candidate_key", "category", "check", "reference_refs", "requires_product_authority"})
            candidate_key = candidate["candidate_key"]
            if not isinstance(candidate_key, str) or PATTERN_RE.fullmatch(candidate_key) is None or candidate_key in candidate_keys or candidate["category"] not in CATEGORIES or not isinstance(candidate["requires_product_authority"], bool):
                raise InvalidInput("catalog candidate metadataが不正です")
            candidate_keys.add(candidate_key)
            candidates.append({"candidate_key": candidate_key, "category": candidate["category"], "check": ensure_nonempty_string(candidate["check"], "catalog candidate check"), "reference_refs": _refs(candidate["reference_refs"], "catalog candidate reference_refs"), "requires_product_authority": candidate["requires_product_authority"]})
        normalized.append({"pattern_key": pattern_key, "name": name, "aliases": sorted(aliases), "identifiers": sorted(identifiers), "candidates": sorted(candidates, key=lambda row: row["candidate_key"])})
    normalized.sort(key=lambda row: row["pattern_key"])
    digest = "sha256:" + hashlib.sha256(canonical_json_bytes(canonicalize(normalized))).hexdigest()
    return normalized, digest


def generate(input_value: dict, metadata: dict) -> dict:
    if metadata["model_key"] is None or metadata["model_type"] != "ui" or metadata["runtime_unit_key"] != f"model:{metadata['model_key']}":
        raise InvalidInput("UI patternのruntime metadataが不正です")
    reject_unknown(input_value, {"pattern", "attributes"})
    catalog, catalog_version = _load_catalog()
    supplied_version = metadata["static_data_versions"].get("ui_pattern_catalog")
    if supplied_version is not None and supplied_version != catalog_version:
        raise InvalidInput("UI pattern catalog versionがcurrent catalogと不一致です")
    pattern_value = ensure_nonempty_string(input_value["pattern"], "pattern")
    attributes = input_value["attributes"]
    if not isinstance(attributes, dict):
        raise InvalidInput("attributesはobjectである必要があります")
    unknown = set(attributes) - ATTRIBUTE_KEYS
    if unknown:
        raise InvalidInput("UI attributesに未知fieldがあります")
    for key in ("type", "role"):
        if key in attributes and not isinstance(attributes[key], str):
            raise InvalidInput(f"attributes.{key}が不正です")
    for key in ("required", "disabled", "readonly", "multiple"):
        if key in attributes and not isinstance(attributes[key], bool):
            raise InvalidInput(f"attributes.{key}が不正です")
    pattern_map = {row["pattern_key"]: row for row in catalog}
    resolver: dict[str, dict[str, Any]] = {}
    for row in catalog:
        resolver[row["pattern_key"]] = row
        resolver[row["name"]] = row
        for alias in row["aliases"]:
            resolver[alias] = row
    pattern = resolver.get(pattern_value)
    if pattern is None:
        unsupported = make_unsupported_item(generator=GENERATOR, item_type="ui-pattern", source_key=pattern_value, reason_code="unknown_pattern", affected_technique_slug=None)
        return {"runtime_status": "unsupported", "support_status": "unsupported", "result_status": "ready", "runtime_required": False, "deterministic_generated": False, "static_data_versions": {"ui_pattern_catalog": catalog_version}, "payload": {"pattern": pattern_value, "attributes": canonicalize(attributes), "candidates": [], "targets": [], "unsupported_items": [unsupported], "catalog_version": catalog_version}, "issues": []}
    targets: list[dict[str, Any]] = []
    for candidate in pattern["candidates"]:
        targets.append({"target_key": f"ui:{pattern['pattern_key']}:{candidate['candidate_key']}", "pattern_key": pattern["pattern_key"], "candidate": candidate, "materializable": False, "execution": None, "authority_refs": [], "reference_refs": candidate["reference_refs"]})
    targets = post_process_targets(metadata["model_key"], targets)
    return {
        "runtime_status": "ok", "support_status": "supported", "result_status": "ready", "runtime_required": True, "deterministic_generated": True, "static_data_versions": {"ui_pattern_catalog": catalog_version},
        "payload": {"pattern": pattern, "resolved_from": pattern_value, "attributes": canonicalize(attributes), "candidates": pattern["candidates"], "targets": targets, "catalog_version": catalog_version, "reference_refs": sorted({reference for candidate in pattern["candidates"] for reference in candidate["reference_refs"]})},
        "issues": [],
    }


if __name__ == "__main__":
    raise SystemExit(run_cli(generate, skill=SKILL, generator=GENERATOR, generator_contract_version=GENERATOR_CONTRACT_VERSION, generator_path=SCRIPT_PATH))
