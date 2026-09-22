"""Calculate risk levels from an already selected risk scheme."""

from __future__ import annotations

from pathlib import Path
import sys

from runtime_contract import InvalidInput, canonicalize, ensure_list, ensure_object, ensure_int, ensure_nonempty_string, reject_unknown, run_cli


SKILL = "test-analysis"
GENERATOR = "risk_matrix"
GENERATOR_CONTRACT_VERSION = "risk-matrix-v1"
SCRIPT_PATH = Path(__file__).resolve()
DEFAULT_MATRIX = {
    4: {1: "中", 2: "高", 3: "高", 4: "高"},
    3: {1: "中", 2: "中", 3: "高", 4: "高"},
    2: {1: "低", 2: "中", 3: "中", 4: "高"},
    1: {1: "低", 2: "低", 3: "低", 4: "中"},
}
PRIORITIES = {"高", "中", "低"}


def _project_scheme(scheme: dict) -> tuple[dict, dict, dict]:
    reject_unknown(scheme, {"kind", "scheme_key", "dimensions", "matrix", "priority_map"})
    if scheme["kind"] != "project-specific":
        raise InvalidInput("project-specific scheme.kindが不正です")
    ensure_nonempty_string(scheme["scheme_key"], "scheme.scheme_key")
    dimensions = scheme["dimensions"]
    if not isinstance(dimensions, dict) or set(dimensions) != {"impact", "likelihood"}:
        raise InvalidInput("scheme.dimensionsが不正です")
    normalized_dimensions = {}
    for name in ("impact", "likelihood"):
        values = ensure_list(dimensions[name], f"scheme.dimensions.{name}")
        if not values or len(set(values)) != len(values) or not all(isinstance(value, int) and not isinstance(value, bool) for value in values):
            raise InvalidInput("scheme dimension valueが不正です")
        normalized_dimensions[name] = values
    matrix = scheme["matrix"]
    priority_map = scheme["priority_map"]
    if not isinstance(matrix, dict) or not isinstance(priority_map, dict):
        raise InvalidInput("scheme.matrix / priority_mapが不正です")
    expected = {f"{impact},{likelihood}" for impact in normalized_dimensions["impact"] for likelihood in normalized_dimensions["likelihood"]}
    if set(matrix) != expected:
        raise InvalidInput("scheme.matrixの完全性が不正です")
    levels = set(matrix.values())
    if any(not isinstance(level, str) or not level for level in levels) or not levels.issubset(priority_map) or any(priority_map[level] not in PRIORITIES for level in levels):
        raise InvalidInput("scheme.priority_mapが不正です")
    return normalized_dimensions, matrix, priority_map


def generate(input_value: dict, metadata: dict) -> dict:
    if metadata["runtime_unit_key"] != "artifact:risk_matrix:all":
        raise InvalidInput("risk_matrix runtime unitが不正です")
    reject_unknown(input_value, {"scheme", "risks"})
    scheme = input_value["scheme"]
    if not isinstance(scheme, dict):
        raise InvalidInput("schemeはobjectである必要があります")
    kind = scheme.get("kind")
    if kind == "repository-default":
        reject_unknown(scheme, {"kind", "scheme_key"})
        if scheme["scheme_key"] != "risk-scheme-v1":
            raise InvalidInput("repository-default scheme_keyが不正です")
        dimensions = {"impact": [1, 2, 3, 4], "likelihood": [1, 2, 3, 4]}
        matrix = {f"{impact},{likelihood}": DEFAULT_MATRIX[impact][likelihood] for impact in dimensions["impact"] for likelihood in dimensions["likelihood"]}
        priority_map = {"高": "高", "中": "中", "低": "低"}
    elif kind == "project-specific":
        dimensions, matrix, priority_map = _project_scheme(scheme)
    else:
        raise InvalidInput("scheme.kindが不正です")
    risks = ensure_list(input_value["risks"], "risks")
    result = []
    seen: set[str] = set()
    for index, row in enumerate(risks):
        if not isinstance(row, dict):
            raise InvalidInput(f"risks[{index}]が不正です")
        reject_unknown(row, {"risk_id", "impact", "likelihood"})
        risk_id = ensure_nonempty_string(row["risk_id"], f"risks[{index}].risk_id")
        if risk_id in seen:
            raise InvalidInput("risk_idが重複しています")
        seen.add(risk_id)
        impact = ensure_int(row["impact"], f"risks[{index}].impact")
        likelihood = ensure_int(row["likelihood"], f"risks[{index}].likelihood")
        if impact not in dimensions["impact"] or likelihood not in dimensions["likelihood"]:
            raise InvalidInput("risk valueがscheme外です")
        level = matrix[f"{impact},{likelihood}"]
        result.append({"risk_id": risk_id, "level": level, "mapped_priority": priority_map[level]})
    return {"runtime_status": "ok", "support_status": "supported", "result_status": "ready", "runtime_required": True, "deterministic_generated": True, "payload": {"risks": sorted(result, key=lambda row: row["risk_id"]), "scheme_key": scheme["scheme_key"]}, "issues": []}


if __name__ == "__main__":
    raise SystemExit(run_cli(generate, skill=SKILL, generator=GENERATOR, generator_contract_version=GENERATOR_CONTRACT_VERSION, generator_path=SCRIPT_PATH))
