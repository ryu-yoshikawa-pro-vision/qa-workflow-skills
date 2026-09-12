from __future__ import annotations

import re

from scripts.skills.evals.deterministic.common import ID_PATTERNS, add_duplicate_assertion, clean, has_value, nonempty_rows
from scripts.skills.evals.deterministic.markdown_parser import find_table, parse_tables
from scripts.skills.evals.deterministic.result import EvalResult

IMPLEMENTATION_HANDLINGS = {"新規実装", "既存E2E再利用", "既存E2E拡張", "ブロック中"}
COMPLETED_HANDLINGS = {"新規実装", "既存E2E再利用", "既存E2E拡張"}
VALID_RESULTS = {"PASS", "FAIL", "未実施", "ブロック中", "確認不能"}
UNCONFIRMED_EXPECTED_BEHAVIOR_MARKERS = (
    "未確認",
    "確認不能",
    "不明",
    "未確定",
    "確認待ち",
    "未取得",
    "未指定",
    "未実施",
)
EXECUTION_PATTERNS = (
    re.compile(r"(?:Playwright|E2E)[^\n]{0,20}(?:実行|再実行|起動)", re.IGNORECASE),
    re.compile(r"(?:実行|再実行|起動)[^\n]{0,20}(?:Playwright|E2E)", re.IGNORECASE),
)
NEGATED_EXECUTION = re.compile(r"(?:しない|しません|せず|行わない|行いません|ありません|ではない|ではありません|禁止|してはいけ|不可)", re.IGNORECASE)


def _is_relative_reference(value: str) -> bool:
    value = clean(value)
    return bool(value) and not re.match(r"^(?:[A-Za-z]:[\\/]|/|https?://)", value) and ".." not in value.split(" > ")[0].split("/")


def _is_unconfirmed_expected_behavior(value: str) -> bool:
    value = clean(value)
    return bool(value) and any(marker in value for marker in UNCONFIRMED_EXPECTED_BEHAVIOR_MARKERS)


def validate(text: str, expected: dict, eval_id: str) -> EvalResult:
    result = EvalResult("e2e-test-implementation", eval_id)
    tables = parse_tables(text)
    target_table = find_table(tables, section_contains="実装対象", required_headers=("E2E対象 / 識別子", "TC ID（存在時のみ）", "明示対象 / 既存E2E参照", "扱い"))
    state_table = find_table(tables, section_contains="実装前の状態", required_headers=("項目", "値", "確認元"))
    ref_table = find_table(tables, section_contains="E2E実装参照", required_headers=("E2E実装参照", "test file", "Playwright title path", "扱い"))
    files_table = find_table(tables, section_contains="変更・再利用したファイル", required_headers=("ファイル", "変更内容 / 再利用理由"))
    validation_table = find_table(tables, section_contains="静的・軽量検証", required_headers=("検証", "実行command / 条件", "結果", "非破壊確認 / 未実施理由"))
    diff_table = find_table(tables, section_contains="inspection差分・ブロック・要再検証", required_headers=("範囲", "状態", "理由 / 影響", "次の担当"))
    missing = [name for name, table in (("実装対象", target_table), ("実装前の状態", state_table), ("E2E実装参照", ref_table), ("変更・再利用したファイル", files_table), ("静的・軽量検証", validation_table), ("inspection差分・ブロック・要再検証", diff_table)) if table is None]
    result.add("E2E-IMPL-D001", not missing, "implementationの正規テーブルが存在すること", evidence=missing or None)

    targets = nonempty_rows(target_table)
    target_issues = []
    for row in targets:
        handling = clean(row.get("扱い", ""))
        has_input_source = any(
            has_value(row.get(field, ""))
            for field in ("TC ID（存在時のみ）", "明示対象 / 既存E2E参照")
        )
        missing_fields = [
            field
            for field in ("E2E対象 / 識別子", "確認済み期待挙動", "扱い")
            if not has_value(row.get(field, ""))
        ]
        if not has_input_source:
            missing_fields.append("入力元（TC ID / 明示対象 / 既存E2E参照のいずれか）")
        if missing_fields:
            target_issues.append({"target": clean(row.get("E2E対象 / 識別子", "")) or "<unknown>", "fields": missing_fields})
    completed_targets = [row for row in targets if clean(row.get("扱い", "")) in COMPLETED_HANDLINGS]
    result.add(
        "E2E-IMPL-D018",
        bool(targets) and not target_issues,
        "実装対象を最低1件、TC / 明示対象 / 既存E2E参照のいずれか、識別子・確認済み期待挙動付きで記録すること",
        evidence={"missing_rows": not targets, "issues": target_issues}
        if not targets or target_issues
        else None,
    )
    unconfirmed_completed_targets = [
        {
            "target": clean(row.get("E2E対象 / 識別子", "")) or "<unknown>",
            "expected_behavior": clean(row.get("確認済み期待挙動", "")),
        }
        for row in completed_targets
        if _is_unconfirmed_expected_behavior(row.get("確認済み期待挙動", ""))
    ]
    result.add(
        "E2E-IMPL-D021",
        not unconfirmed_completed_targets,
        "実装・再利用・拡張が成立した対象は、確認済み期待挙動を未確認・不明のまま完了扱いにしないこと",
        evidence=unconfirmed_completed_targets or None,
    )
    target_handling_bad = sorted({clean(row.get("扱い", "")) for row in targets if clean(row.get("扱い", "")) not in IMPLEMENTATION_HANDLINGS})
    result.add("E2E-IMPL-D002", not target_handling_bad, "実装対象の扱いが許可値であること", evidence=target_handling_bad or None)
    tc_ids = [clean(row.get("TC ID（存在時のみ）", "")) for row in targets if clean(row.get("TC ID（存在時のみ）", ""))]
    invalid_tc = [tc_id for tc_id in tc_ids if not ID_PATTERNS["TC"].fullmatch(tc_id)]
    result.add("E2E-IMPL-D003", not invalid_tc, "存在するTC IDが既存TC形式であること", evidence=invalid_tc or None)

    refs = nonempty_rows(ref_table)
    ref_contract_issues = []
    for row in refs:
        missing_fields = [
            field
            for field in ("E2E実装参照", "test file", "Playwright title path", "扱い")
            if not has_value(row.get(field, ""))
        ]
        if missing_fields:
            ref_contract_issues.append({"ref": clean(row.get("E2E実装参照", "")) or "<unknown>", "fields": missing_fields})
    result.add(
        "E2E-IMPL-D019",
        (not completed_targets) or (bool(refs) and not ref_contract_issues),
        "実装・再利用・拡張が成立した場合はE2E実装参照を最低1件、repo-relative pathとtitle path付きで記録し、実装前blockでは0件を許容すること",
        evidence={"missing_rows": not refs, "issues": ref_contract_issues, "refs_required": bool(completed_targets)}
        if (completed_targets and (not refs or ref_contract_issues))
        else None,
    )
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
    state_by_item = {clean(row.get("項目", "")): row for row in state_rows}
    state_value_issues = []
    for label in sorted(required_state):
        row = state_by_item.get(label)
        if row is None:
            continue
        missing_fields = [field for field in ("値", "確認元") if not has_value(row.get(field, ""))]
        if missing_fields:
            state_value_issues.append({"項目": label, "fields": missing_fields})
    result.add(
        "E2E-IMPL-D016",
        not missing_state and not state_value_issues,
        "実装前のbranch・HEAD・working tree・競合・inspection差分に値または明示状態と確認元があること",
        evidence={"missing_items": missing_state, "missing_values": state_value_issues}
        if missing_state or state_value_issues
        else None,
    )

    validation_rows = nonempty_rows(validation_table)
    invalid_results = sorted({clean(row.get("結果", "")) for row in validation_rows if clean(row.get("結果", "")) not in VALID_RESULTS})
    result.add("E2E-IMPL-D008", not invalid_results, "静的・軽量検証結果が許可値であること", evidence=invalid_results or None)
    failed_without_reason = [clean(row.get("検証", "")) for row in validation_rows if clean(row.get("結果", "")) in {"FAIL", "ブロック中"} and not has_value(row.get("非破壊確認 / 未実施理由", ""))]
    result.add("E2E-IMPL-D009", not failed_without_reason, "検証FAIL / ブロック中に理由があること", evidence=failed_without_reason or None)
    validation_issues = []
    for row in validation_rows:
        check = clean(row.get("検証", ""))
        outcome = clean(row.get("結果", ""))
        missing_fields = []
        if not has_value(check):
            missing_fields.append("検証")
        if not has_value(outcome):
            missing_fields.append("結果")
        if outcome == "PASS":
            if not has_value(row.get("実行command / 条件", "")):
                missing_fields.append("実行command / 条件")
            if not has_value(row.get("非破壊確認 / 未実施理由", "")):
                missing_fields.append("非破壊確認 / 未実施理由")
        elif outcome in {"FAIL", "未実施", "ブロック中", "確認不能"} and not has_value(row.get("非破壊確認 / 未実施理由", "")):
            missing_fields.append("非破壊確認 / 未実施理由")
        if missing_fields:
            validation_issues.append({"検証": check or "<unknown>", "fields": missing_fields})
    result.add(
        "E2E-IMPL-D014",
        bool(validation_rows) and not validation_issues,
        "静的・軽量検証が1行以上あり、実施結果または未実施理由を持つこと",
        evidence={"missing_rows": not validation_rows, "issues": validation_issues}
        if not validation_rows or validation_issues
        else None,
    )
    failed_checks = [clean(row.get("検証", "")) for row in validation_rows if clean(row.get("結果", "")) == "FAIL"]
    diff_rows = nonempty_rows(diff_table)
    unresolved_statuses = {"要再検証", "ブロック中"}
    failed_marked_complete = bool(failed_checks) and not any(clean(row.get("状態", "")) in unresolved_statuses for row in diff_rows)
    result.add(
        "E2E-IMPL-D015",
        not failed_marked_complete,
        "静的検証FAILを完了扱いせず、要再検証またはブロック中へ閉じること",
        evidence={"failed_checks": failed_checks, "states": [clean(row.get("状態", "")) for row in diff_rows]}
        if failed_marked_complete
        else None,
    )
    block_target_rows = [row for row in targets if clean(row.get("扱い", "")) == "ブロック中"]
    block_issues = []
    if block_target_rows:
        blocked_rows = [row for row in diff_rows if clean(row.get("状態", "")) == "ブロック中"]
        if not blocked_rows:
            block_issues.append("ブロック対象に対応するブロック中の理由・次の担当がない")
        for row in blocked_rows:
            missing_fields = [
                field
                for field in ("範囲", "理由 / 影響", "次の担当")
                if not has_value(row.get(field, ""))
            ]
            if missing_fields:
                block_issues.append({"範囲": clean(row.get("範囲", "")) or "<unknown>", "fields": missing_fields})
    result.add(
        "E2E-IMPL-D020",
        not block_issues,
        "実装前blockでは架空のE2E実装参照を要求せず、block理由・不足範囲・次の担当を記録すること",
        evidence=block_issues or None,
    )
    block_only = bool(targets) and all(clean(row.get("扱い", "")) == "ブロック中" for row in targets)
    block_only_artifact_issues = []
    if block_only:
        no_change_file_markers = {"", "なし", "対象なし", "未実施", "-"}
        for row in nonempty_rows(files_table):
            file_value = clean(row.get("ファイル", ""))
            if file_value not in no_change_file_markers:
                block_only_artifact_issues.append({"ファイル": file_value, "reason": "実装前blockなのに変更・再利用ファイルがある"})
        passed_validations = [clean(row.get("検証", "")) for row in validation_rows if clean(row.get("結果", "")) == "PASS"]
        if passed_validations:
            block_only_artifact_issues.append({"検証": passed_validations, "reason": "実装前blockなのに実装成果物のPASS検証がある"})
    result.add(
        "E2E-IMPL-D022",
        not block_only_artifact_issues,
        "全対象が実装前blockの場合、実装済みを示す変更ファイルやPASS検証を残さないこと。成立対象との混在は対象単位で許容すること",
        evidence=block_only_artifact_issues or None,
    )

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
