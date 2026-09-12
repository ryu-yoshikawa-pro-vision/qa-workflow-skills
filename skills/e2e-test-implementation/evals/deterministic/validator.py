from __future__ import annotations

import re

from scripts.skills.evals.deterministic.common import ID_PATTERNS, clean, add_duplicate_assertion, nonempty_rows
from scripts.skills.evals.deterministic.markdown_parser import find_table, parse_tables
from scripts.skills.evals.deterministic.result import EvalResult

IMPLEMENTATION_HANDLINGS = {"新規実装", "既存E2E再利用", "既存E2E拡張", "ブロック中"}
VALID_RESULTS = {"PASS", "FAIL", "未実施", "ブロック中", "確認不能"}
EXECUTION_PATTERNS = (
    re.compile(r"(?:Playwright|E2E)[^\n]{0,20}(?:実行|再実行|起動)", re.IGNORECASE),
    re.compile(r"(?:実行|再実行|起動)[^\n]{0,20}(?:Playwright|E2E)", re.IGNORECASE),
)
NEGATED_EXECUTION = re.compile(r"(?:しない|しません|せず|行わない|行いません|ありません|ではない|ではありません|禁止|してはいけ|不可)", re.IGNORECASE)


def _is_relative_reference(value: str) -> bool:
    value = clean(value)
    return bool(value) and not re.match(r"^(?:[A-Za-z]:[\\/]|/|https?://)", value) and ".." not in value.split(" > ")[0].split("/")


def validate(text: str, expected: dict, eval_id: str) -> EvalResult:
    result = EvalResult("e2e-test-implementation", eval_id)
    tables = parse_tables(text)
    target_table = find_table(tables, section_contains="実装対象", required_headers=("E2E対象 / 識別子", "TC ID（存在時のみ）", "明示対象 / 既存E2E参照", "扱い"))
    state_table = find_table(tables, section_contains="実装前の状態", required_headers=("項目", "値", "確認元"))
    ref_table = find_table(tables, section_contains="E2E実装参照", required_headers=("E2E実装参照", "test file", "Playwright title path", "扱い"))
    files_table = find_table(tables, section_contains="変更・再利用したファイル", required_headers=("ファイル", "変更内容 / 再利用理由"))
    validation_table = find_table(tables, section_contains="静的・軽量検証", required_headers=("検証", "実行command / 条件", "結果", "非破壊確認 / 未実施理由"))
    missing = [name for name, table in (("実装対象", target_table), ("実装前の状態", state_table), ("E2E実装参照", ref_table), ("変更・再利用したファイル", files_table), ("静的・軽量検証", validation_table)) if table is None]
    result.add("E2E-IMPL-D001", not missing, "implementationの正規テーブルが存在すること", evidence=missing or None)

    targets = nonempty_rows(target_table)
    target_handling_bad = sorted({clean(row.get("扱い", "")) for row in targets if clean(row.get("扱い", "")) not in IMPLEMENTATION_HANDLINGS})
    result.add("E2E-IMPL-D002", not target_handling_bad, "実装対象の扱いが許可値であること", evidence=target_handling_bad or None)
    tc_ids = [clean(row.get("TC ID（存在時のみ）", "")) for row in targets if clean(row.get("TC ID（存在時のみ）", ""))]
    invalid_tc = [tc_id for tc_id in tc_ids if not ID_PATTERNS["TC"].fullmatch(tc_id)]
    result.add("E2E-IMPL-D003", not invalid_tc, "存在するTC IDが既存TC形式であること", evidence=invalid_tc or None)

    refs = nonempty_rows(ref_table)
    ref_values = [clean(row.get("E2E実装参照", "")) for row in refs if clean(row.get("E2E実装参照", ""))]
    add_duplicate_assertion(result, "E2E-IMPL-D004", ref_values, "E2E実装参照")
    invalid_refs = [ref for ref in ref_values if not _is_relative_reference(ref)]
    result.add("E2E-IMPL-D005", not invalid_refs, "E2E実装参照がrepo-relativeであること", evidence=invalid_refs or None)
    missing_ref_parts = []
    for row in refs:
        if not clean(row.get("test file", "")) or not clean(row.get("Playwright title path", "")):
            missing_ref_parts.append(clean(row.get("E2E実装参照", "")) or "<unknown>")
    result.add("E2E-IMPL-D006", not missing_ref_parts, "E2E実装参照にtest fileとtitle pathがあること", evidence=missing_ref_parts or None)

    state_rows = nonempty_rows(state_table)
    required_state = {"branch", "HEAD commit", "working tree", "変更予定ファイルとの競合", "inspectionからの差分"}
    actual_state = {clean(row.get("項目", "")) for row in state_rows}
    missing_state = sorted(required_state - actual_state)
    result.add("E2E-IMPL-D007", not missing_state, "実装前のbranch・HEAD・working tree・競合・inspection差分を確認すること", evidence=missing_state or None)

    validation_rows = nonempty_rows(validation_table)
    invalid_results = sorted({clean(row.get("結果", "")) for row in validation_rows if clean(row.get("結果", "")) not in VALID_RESULTS})
    result.add("E2E-IMPL-D008", not invalid_results, "静的・軽量検証結果が許可値であること", evidence=invalid_results or None)
    failed_without_reason = [clean(row.get("検証", "")) for row in validation_rows if clean(row.get("結果", "")) in {"FAIL", "ブロック中"} and not clean(row.get("非破壊確認 / 未実施理由", ""))]
    result.add("E2E-IMPL-D009", not failed_without_reason, "検証FAIL / ブロック中に理由があること", evidence=failed_without_reason or None)

    expected_refs = {clean(str(ref)) for ref in expected.get("required_e2e_refs", [])}
    missing_refs = sorted(expected_refs - set(ref_values))
    result.add("E2E-IMPL-D010", not missing_refs, "フィクスチャで必須のE2E実装参照が存在すること", evidence=missing_refs or None)
    required_tc = {clean(str(tc)) for tc in expected.get("required_tc_ids", [])}
    missing_tc = sorted(required_tc - set(tc_ids))
    result.add("E2E-IMPL-D011", not missing_tc, "TCあり経路で指定TC IDとの対応を保持すること", evidence=missing_tc or None)
    if expected.get("tc_absent"):
        fabricated = sorted(set(re.findall(r"\bTC-\d{3}\b", text)))
        result.add("E2E-IMPL-D012", not fabricated, "TCなし経路でTC IDを創作しないこと", evidence=fabricated or None)
    if expected.get("require_no_e2e_execution"):
        execution_terms = []
        for line in text.splitlines():
            if NEGATED_EXECUTION.search(line):
                continue
            execution_terms.extend(match.group(0) for pattern in EXECUTION_PATTERNS if (match := pattern.search(line)))
        execution_terms = sorted(set(execution_terms))
        result.add("E2E-IMPL-D013", not execution_terms, "implementation出力で本E2E実行を完了扱いにしないこと", evidence=execution_terms or None)
    return result
