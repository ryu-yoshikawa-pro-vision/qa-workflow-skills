from __future__ import annotations

import re

from scripts.skills.evals.deterministic.common import ID_PATTERNS, clean, add_duplicate_assertion, nonempty_rows
from scripts.skills.evals.deterministic.markdown_parser import find_table, parse_tables
from scripts.skills.evals.deterministic.result import EvalResult

HANDLINGS = {"新規E2E実装", "既存E2E再利用", "既存E2E拡張", "E2E対象外", "ブロック中", "要再判断"}
SOURCE_TOKENS = {"repo", "実対象", "ユーザー提供情報", "未確認", "確認不能"}


def _has_named_rows(rows: list[dict[str, str]], labels: set[str], field: str) -> list[str]:
    actual = {clean(row.get(field, "")) for row in rows}
    return sorted(labels - actual)


def validate(text: str, expected: dict, eval_id: str) -> EvalResult:
    result = EvalResult("e2e-test-inspection", eval_id)
    tables = parse_tables(text)
    target_table = find_table(tables, section_contains="対象決定", required_headers=("E2E対象 / 識別子", "TC ID（存在時のみ）", "E2E実装参照", "扱い"))
    freshness_table = find_table(tables, section_contains="確認元・鮮度", required_headers=("項目", "値", "確認元"))
    fact_table = find_table(tables, section_contains="実装・実行に影響する事実", required_headers=("事実", "内容", "確認元"))
    safety_table = find_table(tables, section_contains="安全条件・準備・cleanup", required_headers=("条件", "状態", "根拠 / 許可"))
    relation_table = find_table(tables, section_contains="既存E2Eとの関係", required_headers=("対象", "扱い", "既存E2E実装参照"))
    feasibility_table = find_table(tables, section_contains="実装可否・未確認・ブロック", required_headers=("範囲", "実装可否 / 状態", "理由", "次の担当"))
    required = {
        "対象決定": target_table,
        "確認元・鮮度": freshness_table,
        "実装・実行に影響する事実": fact_table,
        "安全条件・準備・cleanup": safety_table,
        "既存E2Eとの関係": relation_table,
        "実装可否・未確認・ブロック": feasibility_table,
    }
    missing = sorted(name for name, table in required.items() if table is None)
    result.add("E2E-INSP-D001", not missing, "inspectionの正規テーブルが存在すること", evidence=missing or None)

    targets = nonempty_rows(target_table)
    invalid_handling = sorted({clean(row.get("扱い", "")) for row in targets if clean(row.get("扱い", "")) not in HANDLINGS})
    result.add("E2E-INSP-D002", not invalid_handling, "E2E対象の扱いが許可値であること", evidence=invalid_handling or None)
    tc_ids = [clean(row.get("TC ID（存在時のみ）", "")) for row in targets if clean(row.get("TC ID（存在時のみ）", ""))]
    invalid_tc = [value for value in tc_ids if not ID_PATTERNS["TC"].fullmatch(value)]
    result.add("E2E-INSP-D003", not invalid_tc, "存在するTC IDが既存TC形式であること", evidence=invalid_tc or None)
    refs = [clean(row.get("E2E実装参照", "")) for row in targets if clean(row.get("E2E実装参照", ""))]
    add_duplicate_assertion(result, "E2E-INSP-D004", refs, "E2E対象の実装参照")

    freshness = nonempty_rows(freshness_table)
    required_freshness = {"branch", "commit", "working tree", "テスト環境URL / origin", "実対象確認日時", "version / build ID"}
    missing_freshness = _has_named_rows(freshness, required_freshness, "項目")
    result.add("E2E-INSP-D005", not missing_freshness, "branch・commit・working tree・URL・確認日時・versionの鮮度情報があること", evidence=missing_freshness or None)

    safety = nonempty_rows(safety_table)
    required_safety = {"URL / origin", "副作用", "run外の準備", "runner管理setup / cleanup", "証跡・認証状態"}
    missing_safety = _has_named_rows(safety, required_safety, "条件")
    result.add("E2E-INSP-D006", not missing_safety, "安全条件・準備・cleanup・証跡の確認行があること", evidence=missing_safety or None)

    relations = nonempty_rows(relation_table)
    relation_bad = sorted({clean(row.get("扱い", "")) for row in relations if clean(row.get("扱い", "")) and clean(row.get("扱い", "")) not in HANDLINGS | {"既存E2Eで十分にカバー済み"}})
    result.add("E2E-INSP-D007", not relation_bad, "既存E2Eとの関係が許可された扱いであること", evidence=relation_bad or None)

    facts = nonempty_rows(fact_table)
    missing_fact_labels = _has_named_rows(facts, set(expected.get("required_fact_labels", [])), "事実")
    result.add("E2E-INSP-D008", not missing_fact_labels, "フィクスチャで必須のinspection事実が存在すること", evidence=missing_fact_labels or None)

    expected_refs = {clean(str(ref)) for ref in expected.get("required_e2e_refs", [])}
    actual_refs = {clean(row.get("E2E実装参照", "")) for row in targets if clean(row.get("E2E実装参照", ""))}
    missing_refs = sorted(expected_refs - actual_refs)
    result.add("E2E-INSP-D009", not missing_refs, "フィクスチャで必須のE2E実装参照が対象決定に存在すること", evidence=missing_refs or None)

    required_tc_ids = {clean(str(tc)) for tc in expected.get("required_tc_ids", [])}
    missing_required_tc = sorted(required_tc_ids - set(tc_ids))
    result.add("E2E-INSP-D010", not missing_required_tc, "TCあり経路で指定TC IDが保持されること", evidence=missing_required_tc or None)

    if expected.get("tc_absent"):
        fabricated = sorted(set(re.findall(r"\bTC-\d{3}\b", text)))
        result.add("E2E-INSP-D011", not fabricated, "TCなし経路でTC IDを創作しないこと", evidence=fabricated or None)

    source_values = []
    for row in freshness + facts:
        source_values.extend(part.strip() for part in clean(row.get("確認元", "")).split("/") if part.strip())
    invalid_sources = sorted({value for value in source_values if value not in SOURCE_TOKENS and not any(token in value for token in SOURCE_TOKENS)})
    result.add("E2E-INSP-D012", not invalid_sources, "主要事実の確認元がrepo・実対象・ユーザー提供情報・未確認のいずれかであること", severity="warning", evidence=invalid_sources or None)
    return result
