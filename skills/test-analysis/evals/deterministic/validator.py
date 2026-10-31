from __future__ import annotations

import importlib.util
import re
import sys
from functools import lru_cache
from pathlib import Path

from scripts.skills.evals.deterministic.common import (
    ID_PATTERNS,
    add_duplicate_assertion,
    add_required_fields_assertion,
    clean,
    ids_in,
    nonempty_rows,
)
from scripts.skills.evals.deterministic.markdown_parser import find_table, parse_tables
from scripts.skills.evals.deterministic.result import EvalResult

RISK_MATRIX = {
    4: {1: "中", 2: "高", 3: "高", 4: "高"},
    3: {1: "中", 2: "中", 3: "高", 4: "高"},
    2: {1: "低", 2: "中", 3: "中", 4: "高"},
    1: {1: "低", 2: "低", 3: "低", 4: "中"},
}
TESTABILITY = {"可", "不可", "一部"}
TECHNIQUES = {
    "同値分割",
    "境界値分析",
    "Domain Testing",
    "デシジョンテーブル",
    "状態遷移",
    "CRUD Testing",
    "Pairwise",
    "組合せ",
    "Pairwise / 組合せ",
    "エラー推測",
    "シナリオ",
    "ユースケース",
    "シナリオ / ユースケース",
    "Random Testing",
    "Metamorphic Testing",
    "Syntax-Based Testing",
}
TECHNIQUE_LABEL_BY_SLUG = {
    "ep": "同値分割",
    "bva": "境界値分析",
    "domain": "Domain Testing",
    "decision": "デシジョンテーブル",
    "comb": "Pairwise / 組合せ",
    "state": "状態遷移",
    "error-guessing": "エラー推測",
    "scenario": "シナリオ / ユースケース",
    "crud": "CRUD Testing",
    "syntax": "Syntax-Based Testing",
    "random": "Random Testing",
    "metamorphic": "Metamorphic Testing",
}


@lru_cache(maxsize=1)
def _runtime_contract_module():
    path = Path(__file__).resolve().parents[2] / "scripts" / "runtime_contract.py"
    name = "_test_analysis_runtime_contract_for_eval"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load test-analysis runtime contract: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _has_explicit_gate_state(text: str, valid: bool) -> bool:
    status = "true" if valid else "false"
    artifact_state = "完成" if valid else "未完成（ブロック中）"

    def has_value(label: str, expected: str) -> bool:
        label_pattern = re.compile(rf"{label}\s*[:=：]\s*(.*?)\s*$", re.IGNORECASE)
        for line in text.splitlines():
            candidate = line.strip()
            if candidate.startswith(("-", "*")):
                candidate = candidate[1:].strip()
            candidate = _strip_markdown_wrapper(candidate)
            match = label_pattern.fullmatch(candidate)
            if match and _strip_markdown_wrapper(match.group(1).strip()) == expected:
                return True
        return False

    return has_value(r"verify_runtime_evidence\s+valid", status) and has_value(
        re.escape("成果物状態"), artifact_state
    )


def _strip_markdown_wrapper(value: str) -> str:
    """Remove one balanced Markdown code/emphasis wrapper around an exact value."""
    for marker in ("**", "__", "`", "*", "_"):
        if (
            len(value) > 2 * len(marker)
            and value.startswith(marker)
            and value.endswith(marker)
        ):
            return value[len(marker) : -len(marker)].strip()
    return value


def _is_expected_blocked_gate_outcome(
    gate: dict,
    blocked_units: list[str],
    expected_status: dict,
    entity_blocks: list[tuple[str, dict]],
    text: str,
) -> bool:
    analysis_identity = "test-analysis::artifact:analysis_entities:all"
    gate_issue_types = {
        issue.get("issue_type")
        for issue in gate.get("issues", [])
        if isinstance(issue, dict)
    }
    all_gate_issues_blocking = bool(gate.get("issues")) and all(
        isinstance(issue, dict) and issue.get("blocking") is True
        for issue in gate.get("issues", [])
    )
    entity_map_is_empty = (
        len(entity_blocks) == 1
        and entity_blocks[0][0] == "test-analysis"
        and isinstance(entity_blocks[0][1].get("entities"), list)
        and not entity_blocks[0][1]["entities"]
    )
    blocked_output_is_explicit = _has_explicit_gate_state(text, valid=False)
    expected_block_is_materialization_block = (
        blocked_units == [analysis_identity]
        and expected_status.get(analysis_identity, {}).get("runtime_status")
        == "invalid_input"
        and expected_status.get(analysis_identity, {}).get("result_status") == "blocked"
    )
    return bool(
        expected_block_is_materialization_block
        and gate.get("valid") is False
        and gate_issue_types == {"missing_entity"}
        and all_gate_issues_blocking
        and entity_map_is_empty
        and blocked_output_is_explicit
    )


def _add_runtime_evidence_assertion(
    result, text: str, expected: dict, risks: list[dict], techniques: list[dict]
) -> None:
    runtime_spec = expected.get("runtime_contract")
    failures: list[dict[str, str]] = []
    if not isinstance(runtime_spec, dict):
        failures.append({"reason": "missing_expected_runtime_contract"})
        result.add(
            "RISK-D018",
            False,
            "runtime evidenceがfixtureの実行契約と最終gateに適合すること",
            evidence=failures,
        )
        return

    expected_units = runtime_spec.get("expected_runtime_units")
    expected_generators = runtime_spec.get("expected_generators")
    expected_status = runtime_spec.get("expected_status")
    if (
        not isinstance(expected_units, list)
        or not all(isinstance(unit, str) for unit in expected_units)
        or not isinstance(expected_generators, dict)
        or not isinstance(expected_status, dict)
        or set(expected_generators) != set(expected_units)
        or set(expected_status) != set(expected_units)
    ):
        failures.append({"reason": "invalid_expected_runtime_contract"})
        result.add(
            "RISK-D018",
            False,
            "runtime evidenceがfixtureの実行契約と最終gateに適合すること",
            evidence=failures,
        )
        return

    module = _runtime_contract_module()
    try:
        inputs = module.extract_machine_blocks(
            text, "Machine Runtime Input", allow_duplicates=True
        )
        results = module.extract_machine_blocks(
            text, "Machine Runtime Result", allow_duplicates=True
        )
        entity_blocks = module.extract_machine_blocks(
            text, "Machine Entities", allow_duplicates=True
        )
    except module.RuntimeErrorBase as exc:
        failures.append({"reason": exc.issue_type})
        inputs, results, entity_blocks = [], [], []

    input_ids = [identity for identity, _ in inputs]
    result_ids = [identity for identity, _ in results]
    if (
        len(input_ids) != len(set(input_ids))
        or len(result_ids) != len(set(result_ids))
        or sorted(input_ids) != sorted(expected_units)
        or sorted(result_ids) != sorted(expected_units)
    ):
        failures.append({"reason": "runtime_unit_set_mismatch"})

    input_map = dict(inputs)
    result_map = dict(results)
    normalized_input = None
    analysis_identity = "test-analysis::artifact:analysis_entities:all"
    analysis_block = input_map.get(analysis_identity)
    if (
        not isinstance(analysis_block, dict)
        or set(analysis_block) != {"metadata", "input"}
        or not isinstance(analysis_block.get("metadata"), dict)
        or not isinstance(analysis_block.get("input"), dict)
    ):
        failures.append({"reason": "invalid_analysis_entities_input"})
    else:
        normalized_input = dict(analysis_block["input"])
        upstream = analysis_block["metadata"].get("upstream_entities", [])
        if isinstance(upstream, list):
            normalized_input["upstream_entities"] = upstream
        else:
            failures.append({"reason": "invalid_upstream_entities"})

        visible_risks = {
            (
                clean(row.get("リスクID", "")),
                _int_1_4(row.get("影響度", "")),
                _int_1_4(row.get("発生可能性", "")),
            )
            for row in risks
        }
        normalized_risks = normalized_input.get("product_risks")
        if not isinstance(normalized_risks, list) or any(
            not isinstance(row, dict)
            or not isinstance(row.get("risk_id"), str)
            or not isinstance(row.get("impact"), int)
            or isinstance(row.get("impact"), bool)
            or not isinstance(row.get("likelihood"), int)
            or isinstance(row.get("likelihood"), bool)
            for row in normalized_risks
        ):
            failures.append({"reason": "invalid_normalized_product_risks"})
        else:
            machine_risks = {
                (row["risk_id"], row["impact"], row["likelihood"])
                for row in normalized_risks
            }
            if machine_risks != visible_risks:
                failures.append({"reason": "runtime_product_risks_mismatch"})

        selections = normalized_input.get("technique_selections")
        if not isinstance(selections, list) or any(
            not isinstance(row, dict)
            or not isinstance(row.get("selected_techniques"), list)
            or any(
                not isinstance(value, str) or value not in TECHNIQUE_LABEL_BY_SLUG
                for value in row["selected_techniques"]
            )
            for row in selections
        ):
            failures.append({"reason": "invalid_normalized_technique_selections"})
        else:
            machine_techniques = {
                TECHNIQUE_LABEL_BY_SLUG[value]
                for row in selections
                for value in row["selected_techniques"]
            }
            visible_techniques = {
                clean(row.get("テスト技法", ""))
                for row in techniques
                if clean(row.get("テスト技法", ""))
            }
            if machine_techniques != visible_techniques:
                failures.append({"reason": "runtime_techniques_mismatch"})

    for identity in expected_units:
        runtime_result = result_map.get(identity)
        if not isinstance(runtime_result, dict):
            continue
        if runtime_result.get("generator") != expected_generators.get(identity):
            failures.append({"reason": "runtime_generator_mismatch"})
        expected_fields = expected_status.get(identity)
        if not isinstance(expected_fields, dict) or any(
            runtime_result.get(field) != value
            for field, value in expected_fields.items()
        ):
            failures.append({"reason": "runtime_status_mismatch"})

    gate = None
    if normalized_input is not None and not failures:
        try:
            gate = module.verify_runtime_evidence(
                {
                    "operation": "verify_runtime_evidence",
                    "skill": "test-analysis",
                    "normalized_skill_input": normalized_input,
                    "artifact_markdown": text,
                    "previous_artifact_markdown": None,
                    "partial_rerun": False,
                }
            )
        except module.RuntimeErrorBase as exc:
            failures.append({"reason": exc.issue_type})

    blocked_units = [
        identity
        for identity, fields in expected_status.items()
        if isinstance(fields, dict)
        and (
            fields.get("runtime_status") != "ok"
            or fields.get("result_status") in {"blocked", "unresolved"}
        )
    ]
    gate_is_valid = isinstance(gate, dict) and gate.get("valid") is True
    if gate is None:
        failures.append({"reason": "runtime_gate_not_evaluated"})
    elif gate_is_valid and not _has_explicit_gate_state(text, valid=True):
        failures.append({"reason": "complete_gate_state_not_reported"})
    elif not gate_is_valid:
        if not _is_expected_blocked_gate_outcome(
            gate, blocked_units, expected_status, entity_blocks, text
        ):
            failures.append({"reason": "unexpected_invalid_runtime_gate"})
    elif blocked_units:
        failures.append({"reason": "blocked_fixture_marked_complete"})

    result.add(
        "RISK-D018",
        not failures,
        "runtime evidenceがfixtureの実行契約と最終gateに適合すること",
        evidence=failures or None,
    )


def _int_1_4(value: str) -> int | None:
    try:
        parsed = int(clean(value))
    except ValueError:
        return None
    return parsed if 1 <= parsed <= 4 else None


def validate(text: str, expected: dict, eval_id: str) -> EvalResult:
    result = EvalResult("test-analysis", eval_id)
    tables = parse_tables(text)
    risk_table = find_table(
        tables,
        section_contains="プロダクトリスク一覧",
        required_headers=("リスクID", "影響度", "発生可能性", "レベル"),
    )
    testability_table = find_table(
        tables,
        section_contains="テスト可能性",
        required_headers=("要件 / 懸念", "操作可能か", "観測可能か", "合否判定可能か"),
    )
    technique_table = find_table(
        tables, section_contains="選択したテスト技法", required_headers=("テスト技法",)
    )
    missing_tables = [
        label
        for label, table in (
            ("プロダクトリスク一覧", risk_table),
            ("選択したテスト技法", technique_table),
            ("テスト可能性 / テストレベル判断", testability_table),
        )
        if table is None
    ]
    result.add(
        "RISK-D010",
        not missing_tables,
        "テスト分析の正規テーブルが存在すること",
        evidence=missing_tables or None,
    )

    risks = nonempty_rows(risk_table)
    testability = nonempty_rows(testability_table)
    techniques = nonempty_rows(technique_table)
    ids = [clean(r.get("リスクID", "")) for r in risks]
    bad = [v for v in ids if not ID_PATTERNS["RISK"].fullmatch(v)]
    result.add(
        "RISK-D001", not bad, "リスクIDがRISK-xxx形式であること", evidence=bad or None
    )
    add_duplicate_assertion(result, "RISK-D002", ids, "リスクID")

    missing, ranges, matrix = [], [], []
    for row in risks:
        rid = clean(row.get("リスクID", ""))
        req = [
            "製品上のリスク / 失敗",
            "関連する現在有効な仕様根拠 / 変更 / 依存",
            "影響度",
            "発生可能性",
            "レベル",
            "根拠",
        ]
        absent = [f for f in req if not clean(row.get(f, ""))]
        if absent:
            missing.append({"id": rid, "fields": absent})
        impact = _int_1_4(row.get("影響度", ""))
        likelihood = _int_1_4(row.get("発生可能性", ""))
        if impact is None or likelihood is None:
            ranges.append(
                {
                    "id": rid,
                    "impact": row.get("影響度"),
                    "likelihood": row.get("発生可能性"),
                }
            )
        else:
            exp = RISK_MATRIX[impact][likelihood]
            actual = clean(row.get("レベル", ""))
            if actual != exp:
                matrix.append({"id": rid, "expected": exp, "actual": actual})
    result.add(
        "RISK-D003",
        not missing,
        "リスクの必須項目が存在すること",
        evidence=missing or None,
    )
    result.add(
        "RISK-D004",
        not ranges,
        "影響度と発生可能性が1〜4の整数であること",
        evidence=ranges or None,
    )
    result.add(
        "RISK-D005",
        not matrix,
        "リスクレベルが正規の4×4マトリクスと一致すること",
        evidence=matrix or None,
    )

    unknown = []
    auth_spec = "known_authorities" in expected
    change_spec = "known_changes" in expected
    dep_spec = "known_dependencies" in expected
    known_auth = set(expected.get("known_authorities", []))
    known_changes = set(expected.get("known_changes", []))
    known_deps = set(expected.get("known_dependencies", []))
    for row in risks:
        for ref in ids_in(row.get("関連する現在有効な仕様根拠 / 変更 / 依存", "")):
            if (
                ref.startswith(("SPEC-", "DEC-", "ASM-"))
                and auth_spec
                and ref not in known_auth
            ):
                unknown.append({"risk": row.get("リスクID"), "reference": ref})
            elif ref.startswith("CHG-") and change_spec and ref not in known_changes:
                unknown.append({"risk": row.get("リスクID"), "reference": ref})
            elif ref.startswith("DEP-") and dep_spec and ref not in known_deps:
                unknown.append({"risk": row.get("リスクID"), "reference": ref})
    result.add(
        "RISK-D006",
        not unknown,
        "リスク参照がフィクスチャデータに存在すること",
        evidence=unknown or None,
    )

    add_required_fields_assertion(
        result,
        "RISK-D012",
        techniques,
        ("テスト技法", "適用領域", "選択理由"),
        "テスト技法",
        "選択したテスト技法",
    )
    add_required_fields_assertion(
        result,
        "RISK-D013",
        testability,
        (
            "要件 / 懸念",
            "操作可能か",
            "観測可能か",
            "合否判定可能か",
            "選択テストレベル",
        ),
        "要件 / 懸念",
        "テスト可能性",
    )

    invalid = []
    for row in testability:
        for f in ("操作可能か", "観測可能か", "合否判定可能か"):
            v = clean(row.get(f, ""))
            if v and v not in TESTABILITY:
                invalid.append({"field": f, "value": v})
    result.add(
        "RISK-D007",
        not invalid,
        "テスト可能性の値が許可値であること",
        evidence=invalid or None,
    )

    invalid_tech = sorted(
        {
            clean(r.get("テスト技法", ""))
            for r in techniques
            if clean(r.get("テスト技法", ""))
            and clean(r.get("テスト技法", "")) not in TECHNIQUES
        }
    )
    result.add(
        "RISK-D008",
        not invalid_tech,
        "選択したテスト技法が許可された正規値であること",
        evidence=invalid_tech or None,
    )

    terms = ("納期", "予算", "人員", "スケジュール")
    suspicious = [
        clean(r.get("リスクID", ""))
        for r in risks
        if any(t in " ".join(r.values()) for t in terms)
    ]
    result.add(
        "RISK-D009",
        not suspicious,
        "リスク行にプロジェクトリスク概念が含まれる可能性があるため意味レビューが必要",
        severity="warning",
        evidence=suspicious or None,
    )

    required_issues = []
    if "required_risks" in expected:
        by_id = {clean(r.get("リスクID", "")): r for r in risks}
        for rid, spec in expected["required_risks"].items():
            row = by_id.get(rid)
            if row is None:
                required_issues.append({"id": rid, "reason": "missing"})
                continue
            actual = {
                "impact": _int_1_4(row.get("影響度", "")),
                "likelihood": _int_1_4(row.get("発生可能性", "")),
                "risk_level": clean(row.get("レベル", "")),
            }
            expected_values = {
                "impact": spec.get("impact"),
                "likelihood": spec.get("likelihood"),
                "risk_level": spec.get("risk_level"),
            }
            if actual != expected_values:
                required_issues.append(
                    {"id": rid, "expected": expected_values, "actual": actual}
                )
    result.add(
        "RISK-D011",
        not required_issues,
        "フィクスチャで必須のプロダクトリスクが期待するマトリクス値で存在すること",
        evidence=required_issues or None,
    )

    required_techniques = set(expected.get("required_techniques", []))
    actual_techniques = {
        clean(r.get("テスト技法", ""))
        for r in techniques
        if clean(r.get("テスト技法", ""))
    }
    missing_techniques = sorted(required_techniques - actual_techniques)
    result.add(
        "RISK-D014",
        not missing_techniques,
        "フィクスチャで必須のテスト技法が選択されていること",
        evidence=missing_techniques or None,
    )

    testability_mismatch = None
    if "required_testability" in expected:
        required_values = expected["required_testability"]
        matched = any(
            all(
                clean(row.get(field, "")) == clean(str(value))
                for field, value in required_values.items()
            )
            for row in testability
        )
        if not matched:
            testability_mismatch = {
                "expected": required_values,
                "actual": [
                    {field: clean(row.get(field, "")) for field in required_values}
                    for row in testability
                ],
            }
    result.add(
        "RISK-D015",
        testability_mismatch is None,
        "フィクスチャで必須のテスト可能性値がテスト可能性行に存在すること",
        evidence=testability_mismatch,
    )

    selection_table = find_table(
        tables,
        section_contains="E2E対象選定",
        required_headers=("自動化目的", "候補範囲", "技術非依存の判断基準 / 根拠"),
    )
    selection_requested = bool(
        expected.get("require_e2e_selection") or "対象 / 実行範囲: E2E対象選定" in text
    )
    result.add(
        "RISK-D016",
        not selection_requested or selection_table is not None,
        "E2E対象選定時に自動化目的・候補範囲・技術非依存の判断基準 / 根拠が存在すること",
        evidence={"missing_table": "E2E対象選定"}
        if selection_requested and selection_table is None
        else None,
    )
    if selection_requested:
        selection_rows = nonempty_rows(selection_table)
        missing_selection = []
        for row in selection_rows:
            fields = ["自動化目的", "候補範囲", "技術非依存の判断基準 / 根拠"]
            absent = [field for field in fields if not clean(row.get(field, ""))]
            if absent:
                missing_selection.append({"fields": absent})
        result.add(
            "RISK-D017",
            bool(selection_rows) and not missing_selection,
            "E2E対象選定に自動化目的・候補範囲・技術非依存の判断基準 / 根拠を持つ有効行があること",
            evidence={
                "missing_rows": not selection_rows,
                "invalid_rows": missing_selection,
            }
            if not selection_rows or missing_selection
            else None,
        )
    if "runtime_contract" in expected:
        _add_runtime_evidence_assertion(result, text, expected, risks, techniques)
    return result
