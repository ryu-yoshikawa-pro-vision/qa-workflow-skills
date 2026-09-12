from __future__ import annotations

import re

from scripts.skills.evals.deterministic.common import CANONICAL_SKILLS, ID_PATTERNS, clean, has_value, nonempty_rows
from scripts.skills.evals.deterministic.markdown_parser import find_table, parse_tables
from scripts.skills.evals.deterministic.result import EvalResult

JUDGEMENT_STATES = {"判定可能", "判定不能", "未分析", "確認不能"}
REPRODUCIBILITY = {"再現", "再現せず", "断続的", "未確認"}
DIRECT_EXECUTION_PATTERNS = (
    re.compile(r"(?:Playwright|E2E)[^\n]{0,30}直接[^\n]{0,20}(?:実行|再実行|起動)", re.IGNORECASE),
    re.compile(r"直接[^\n]{0,20}(?:Playwright|E2E)[^\n]{0,20}(?:実行|再実行|起動)", re.IGNORECASE),
)
NEGATED_EXECUTION = re.compile(r"(?:しない|しません|せず|行わない|行いません|ありません|禁止|してはいけ|不可)", re.IGNORECASE)
ADDITIONAL_NEEDS = {"不要", "必要", "ブロック中"}


def validate(text: str, expected: dict, eval_id: str) -> EvalResult:
    result = EvalResult("e2e-test-result-analysis", eval_id)
    tables = parse_tables(text)
    fact_table = find_table(tables, section_contains="分析対象・実行事実", required_headers=("項目", "値", "参照"))
    judgement_table = find_table(tables, section_contains="判定", required_headers=("対象参照", "判定状態", "原因", "再現性", "根拠"))
    additional_table = find_table(tables, section_contains="不足証拠・追加実行要求", required_headers=("追加実行の必要性", "取得したい証拠", "検証する仮説", "必要な実行範囲", "実行担当"))
    routing_table = find_table(tables, section_contains="修正routing・要再検証", required_headers=("判定 / 不足", "修正先Skill", "対象 / 実行範囲", "要再検証範囲"))
    missing = [name for name, table in (("分析対象・実行事実", fact_table), ("判定", judgement_table), ("不足証拠・追加実行要求", additional_table), ("修正routing・要再検証", routing_table)) if table is None]
    result.add("E2E-AN-D001", not missing, "result-analysisの正規テーブルが存在すること", evidence=missing or None)

    facts = nonempty_rows(fact_table)
    fact_labels = {clean(row.get("項目", "")) for row in facts}
    required_facts = {"E2E対象 / logical primary", "E2E実装参照", "resolved primary TestCase / 実行結果参照", "Playwright status / outcome / expectedStatus", "run全体status / process exit code / run-level error", "cleanup状態 / 残存副作用"}
    missing_facts = sorted(required_facts - fact_labels)
    result.add("E2E-AN-D002", not missing_facts, "実行事実・参照・cleanupを保持すること", evidence=missing_facts or None)

    judgements = nonempty_rows(judgement_table)
    invalid_states = sorted({clean(row.get("判定状態", "")) for row in judgements if clean(row.get("判定状態", "")) not in JUDGEMENT_STATES})
    invalid_repro = sorted({clean(row.get("再現性", "")) for row in judgements if clean(row.get("再現性", "")) not in REPRODUCIBILITY})
    result.add("E2E-AN-D003", not invalid_states, "判定状態が許可値であること", evidence=invalid_states or None)
    result.add("E2E-AN-D004", not invalid_repro, "再現性が原因と別軸の許可値であること", evidence=invalid_repro or None)

    additional = nonempty_rows(additional_table)
    direct_execution = []
    for line in text.splitlines():
        if NEGATED_EXECUTION.search(line):
            continue
        direct_execution.extend(match.group(0) for pattern in DIRECT_EXECUTION_PATTERNS if (match := pattern.search(line)))
    direct_execution = sorted(set(direct_execution))
    additional_issues = []
    for row in additional:
        need = clean(row.get("追加実行の必要性", ""))
        owner = clean(row.get("実行担当", ""))
        if need not in ADDITIONAL_NEEDS:
            additional_issues.append({"need": need, "reason": "invalid additional execution state"})
            continue
        if need in {"必要", "ブロック中"}:
            missing_fields = [
                field
                for field in ("取得したい証拠", "検証する仮説", "必要な実行範囲")
                if not has_value(row.get(field, ""))
            ]
            if owner != "e2e-test-execution":
                additional_issues.append({"need": need, "reason": "additional execution must route to e2e-test-execution", "owner": owner})
            if missing_fields:
                additional_issues.append({"need": need, "fields": missing_fields})
    result.add("E2E-AN-D005", not direct_execution, "追加実行はe2e-test-executionへroutingし、分析Skill自身はPlaywrightを直接実行しないこと", evidence=direct_execution or None)
    result.add(
        "E2E-AN-D010",
        not additional_issues,
        "追加実行が必要またはブロック中なら、証拠・仮説・実行範囲・担当を必ず明示すること",
        evidence=additional_issues or None,
    )

    routing = nonempty_rows(routing_table)
    invalid_targets = []
    for row in routing:
        target = clean(row.get("修正先Skill", ""))
        if target and target not in CANONICAL_SKILLS and target != "検出事項として保持":
            invalid_targets.append(target)
    result.add("E2E-AN-D006", not invalid_targets, "修正routing先が正規Skillまたは検出事項として保持であること", evidence=sorted(set(invalid_targets)) or None)

    expected_ref = clean(str(expected.get("required_e2e_ref", "")))
    actual_refs = {clean(row.get("値", "")) for row in facts if clean(row.get("項目", "")) == "E2E実装参照"}
    result.add("E2E-AN-D007", not expected_ref or expected_ref in actual_refs, "フィクスチャで必須のE2E実装参照が分析事実に完全一致で存在すること", evidence={"expected": expected_ref, "actual": sorted(actual_refs)} if expected_ref and expected_ref not in actual_refs else None)
    if expected.get("tc_absent"):
        fabricated = sorted(set(re.findall(r"\bTC-\d{3}\b", text)))
        result.add("E2E-AN-D008", not fabricated, "TCなし経路でTC IDを創作しないこと", evidence=fabricated or None)
    if "required_cleanup_text" in expected:
        cleanup_text = " ".join(row.get("値", "") for row in facts)
        cleanup_expected = clean(str(expected["required_cleanup_text"]))
        result.add("E2E-AN-D009", cleanup_expected in cleanup_text, "cleanup未確認等の状態を分析へ伝播すること", evidence=cleanup_expected if cleanup_expected not in cleanup_text else None)
    if expected.get("additional_execution_required"):
        matching = [row for row in additional if clean(row.get("追加実行の必要性", "")) == "必要" and clean(row.get("実行担当", "")) == "e2e-test-execution" and has_value(row.get("取得したい証拠", "")) and has_value(row.get("検証する仮説", "")) and has_value(row.get("必要な実行範囲", ""))]
        result.add("E2E-AN-D011", bool(matching), "fixtureが追加実行を要求する場合、目的・仮説・範囲・execution routingがあること", evidence="追加実行要求なし" if not matching else None)
    return result
