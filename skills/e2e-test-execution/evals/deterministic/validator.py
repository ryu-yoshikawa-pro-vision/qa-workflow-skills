from __future__ import annotations

import re

from scripts.skills.evals.deterministic.common import clean, add_duplicate_assertion, nonempty_rows
from scripts.skills.evals.deterministic.markdown_parser import find_table, parse_bullets, parse_tables
from scripts.skills.evals.deterministic.result import EvalResult

RUN_STATUSES = {"passed", "failed", "timedout", "interrupted", "未確認", "確認不能", "構造化結果不完全"}
TEST_STATUSES = {"passed", "failed", "timedOut", "timedout", "skipped", "interrupted"}
OUTCOMES = {"expected", "unexpected", "flaky", "skipped", "未実行", "確認不能"}
EXECUTION_CLASSES = {"要求primary test", "project dependencyとして付随実行されたtest", "project teardownとして付随実行されたtest", "dependency", "teardown"}
CLEANUP_STATES = {"成功", "失敗", "未確認", "対象なし", "意図的に残した状態", "一部失敗"}


def _as_nonnegative_int(value: str) -> int | None:
    value = clean(value)
    if not re.fullmatch(r"\d+", value):
        return None
    return int(value)


def validate(text: str, expected: dict, eval_id: str) -> EvalResult:
    result = EvalResult("e2e-test-execution", eval_id)
    tables = parse_tables(text)
    bullets = parse_bullets(text)
    conditions = find_table(tables, section_contains="実行条件", required_headers=("項目", "値", "確認元", "raw fact / 導出値"))
    run_table = find_table(tables, section_contains="Playwright run結果", required_headers=("項目", "値", "確認元", "raw fact / 導出値"))
    logical_table = find_table(tables, section_contains="logical primary対象の解決", required_headers=("論理的な要求primary対象", "resolved primary TestCase数", "未実行 / 解決不能理由"))
    resolved_table = find_table(tables, section_contains="resolved primary TestCase結果", required_headers=("resolved primary TestCase参照", "論理要求primary対象", "実行開始", "結果 / 未実行理由"))
    attempt_table = find_table(tables, section_contains="attempt結果", required_headers=("resolved primary TestCase参照", "attempt番号", "実行区分", "status", "expectedStatus", "outcome", "retry番号"))
    worktree_table = find_table(tables, section_contains="working tree・証跡", required_headers=("項目", "実行前", "実行後"))
    cleanup_table = find_table(tables, section_contains="cleanup・残存副作用", required_headers=("cleanup対象 / 実行主体", "状態", "結果 / 残存副作用"))
    missing = [name for name, table in (("実行条件", conditions), ("Playwright run結果", run_table), ("logical primary対象の解決", logical_table), ("resolved primary TestCase結果", resolved_table), ("attempt結果", attempt_table), ("working tree・証跡", worktree_table), ("cleanup・残存副作用", cleanup_table)) if table is None]
    result.add("E2E-EXEC-D001", not missing, "executionの正規テーブルが存在すること", evidence=missing or None)

    condition_rows = nonempty_rows(conditions)
    required_condition_labels = {"対象URL / origin", "実行入口 / command chain", "Playwright project", "retries / repeatEach / workers / parallel", "setup / dependency / webServer / teardown", "branch / HEAD / working tree", "テスト対象version / build ID"}
    missing_condition = sorted(required_condition_labels - {clean(row.get("項目", "")) for row in condition_rows})
    result.add("E2E-EXEC-D002", not missing_condition, "実行入口・実効設定・revision・対象versionを確認すること", evidence=missing_condition or None)

    run_rows = nonempty_rows(run_table)
    run_value_by_item = {clean(row.get("項目", "")): row for row in run_rows}
    required_run_labels = {"Playwright run全体status", "CLI process exit code", "run-level / global error", "result artifactの今回run生成・更新"}
    missing_run_labels = sorted(required_run_labels - set(run_value_by_item))
    run_status = clean(run_value_by_item.get("Playwright run全体status", {}).get("値", ""))
    invalid_run_status = [run_status] if run_status not in RUN_STATUSES else []
    result.add("E2E-EXEC-D003", not missing_run_labels and not invalid_run_status, "Playwright run全体statusとrun-level結果の項目が存在し、statusがraw factまたは確認不能の許可値であること", evidence={"missing": missing_run_labels, "invalid_status": invalid_run_status} if missing_run_labels or invalid_run_status else None)
    raw_missing = []
    for row in run_rows:
        if not clean(row.get("確認元", "")) or not clean(row.get("raw fact / 導出値", "")):
            raw_missing.append(clean(row.get("項目", "")) or "<unknown>")
    result.add("E2E-EXEC-D004", not raw_missing and not missing_run_labels, "run全体結果の確認元とraw fact / 導出値区分があること", evidence={"missing_labels": missing_run_labels, "missing_source_or_kind": raw_missing} if raw_missing or missing_run_labels else None)
    artifact_row = run_value_by_item.get("result artifactの今回run生成・更新", {})
    artifact_value = clean(artifact_row.get("値", ""))
    result.add("E2E-EXEC-D005", artifact_value in {"はい", "生成", "更新"}, "今回runのresult artifactを生成・更新したことを確認すること", evidence=artifact_value or None)

    logical_rows = nonempty_rows(logical_table)
    logical_names = [clean(row.get("論理的な要求primary対象", "")) for row in logical_rows]
    add_duplicate_assertion(result, "E2E-EXEC-D006", logical_names, "logical primary対象")
    resolved_rows = nonempty_rows(resolved_table)
    resolved_refs = [clean(row.get("resolved primary TestCase参照", "")) for row in resolved_rows if clean(row.get("resolved primary TestCase参照", ""))]
    add_duplicate_assertion(result, "E2E-EXEC-D007", resolved_refs, "resolved primary TestCase参照")
    resolved_by_logical: dict[str, list[dict[str, str]]] = {}
    for row in resolved_rows:
        resolved_by_logical.setdefault(clean(row.get("論理要求primary対象", "")), []).append(row)
    logical_issues = []
    for row in logical_rows:
        logical = clean(row.get("論理的な要求primary対象", ""))
        declared = _as_nonnegative_int(row.get("resolved primary TestCase数", ""))
        actual = len(resolved_by_logical.get(logical, []))
        reason = clean(row.get("未実行 / 解決不能理由", ""))
        if declared is None:
            logical_issues.append({"logical": logical, "reason": "resolved count is not a nonnegative integer"})
        elif declared != actual:
            logical_issues.append({"logical": logical, "declared": declared, "actual": actual})
        if declared == 0 and not reason:
            logical_issues.append({"logical": logical, "reason": "zero resolved TestCase requires an unexecuted / resolution reason"})
        if declared and reason and reason not in {"なし", "-"}:
            logical_issues.append({"logical": logical, "reason": "resolved logical target cannot carry only an unexecuted reason"})
    result.add("E2E-EXEC-D008", not logical_issues, "各logical primaryがresolved primaryへ解決され、0件なら理由を持つこと", evidence=logical_issues or None)

    resolved_issues = []
    for row in resolved_rows:
        ref = clean(row.get("resolved primary TestCase参照", ""))
        outcome = clean(row.get("結果 / 未実行理由", ""))
        if not outcome:
            resolved_issues.append({"ref": ref, "reason": "result or unexecuted reason missing"})
    result.add("E2E-EXEC-D009", not resolved_issues, "各resolved primary TestCaseに結果または未実行理由があること", evidence=resolved_issues or None)

    attempts = nonempty_rows(attempt_table)
    attempt_issues = []
    for row in attempts:
        status = clean(row.get("status", ""))
        outcome = clean(row.get("outcome", ""))
        execution_class = clean(row.get("実行区分", ""))
        attempt_no = _as_nonnegative_int(row.get("attempt番号", ""))
        retry_no = _as_nonnegative_int(row.get("retry番号", ""))
        if status not in TEST_STATUSES:
            attempt_issues.append({"field": "status", "value": status})
        if outcome not in OUTCOMES:
            attempt_issues.append({"field": "outcome", "value": outcome})
        if execution_class not in EXECUTION_CLASSES:
            attempt_issues.append({"field": "実行区分", "value": execution_class})
        if attempt_no is None or attempt_no < 1 or retry_no is None:
            attempt_issues.append({"field": "attempt / retry", "value": [row.get("attempt番号"), row.get("retry番号")]})
    result.add("E2E-EXEC-D010", not attempt_issues, "attemptのstatus・outcome・実行区分・retry番号が構造化されていること", evidence=attempt_issues or None)
    primary_attempt_refs = {clean(row.get("resolved primary TestCase参照", "")) for row in attempts if clean(row.get("実行区分", "")) == "要求primary test"}
    unresolved_attempt_refs = sorted(primary_attempt_refs - set(resolved_refs))
    started_refs = {
        clean(row.get("resolved primary TestCase参照", ""))
        for row in resolved_rows
        if clean(row.get("実行開始", "")) not in {"", "未開始", "未実行", "未実施"}
    }
    missing_started_attempts = sorted(started_refs - primary_attempt_refs)
    result.add(
        "E2E-EXEC-D011",
        not unresolved_attempt_refs and not missing_started_attempts,
        "要求primary attemptがresolved primary TestCaseへ対応し、開始済みresolved対象にattemptが存在すること",
        evidence={"unknown_attempt_refs": unresolved_attempt_refs, "missing_started_attempts": missing_started_attempts} if unresolved_attempt_refs or missing_started_attempts else None,
    )

    cleanup_rows = nonempty_rows(cleanup_table)
    invalid_cleanup = sorted({clean(row.get("状態", "")) for row in cleanup_rows if clean(row.get("状態", "")) not in CLEANUP_STATES})
    result.add("E2E-EXEC-D012", bool(cleanup_rows) and not invalid_cleanup, "cleanup状態が成功・失敗・未確認等を区別していること", evidence={"missing_cleanup_rows": not cleanup_rows, "invalid": invalid_cleanup} if not cleanup_rows or invalid_cleanup else None)
    cleanup_unconfirmed = any(clean(row.get("状態", "")) in {"失敗", "未確認", "一部失敗"} for row in cleanup_rows)
    execution_state = clean(bullets.get("実行成果物状態", ""))
    result.add("E2E-EXEC-D013", execution_state in {"完了", "ブロック中", "要再確認"} and not (cleanup_unconfirmed and execution_state == "完了"), "cleanup失敗 / 未確認を安全な完了扱いにせず、実行成果物状態を明示すること", evidence={"cleanup": [row.get("状態") for row in cleanup_rows], "execution_state": execution_state} if execution_state not in {"完了", "ブロック中", "要再確認"} or (cleanup_unconfirmed and execution_state == "完了") else None)

    if expected.get("tc_absent"):
        fabricated = sorted(set(re.findall(r"\bTC-\d{3}\b", text)))
        result.add("E2E-EXEC-D014", not fabricated, "TCなし経路でTC IDを創作しないこと", evidence=fabricated or None)
    if "expected_logical_primary_count" in expected:
        mismatch = len(logical_rows) != int(expected["expected_logical_primary_count"])
        result.add("E2E-EXEC-D015", not mismatch, "logical primary対象数がフィクスチャと一致すること", evidence={"expected": expected["expected_logical_primary_count"], "actual": len(logical_rows)} if mismatch else None)
    if "expected_resolved_primary_count" in expected:
        mismatch = len(resolved_rows) != int(expected["expected_resolved_primary_count"])
        result.add("E2E-EXEC-D016", not mismatch, "resolved primary TestCase数がフィクスチャと一致すること", evidence={"expected": expected["expected_resolved_primary_count"], "actual": len(resolved_rows)} if mismatch else None)
    if "expected_attempts" in expected:
        actual_attempts = {
            (
                clean(row.get("resolved primary TestCase参照", "")),
                _as_nonnegative_int(row.get("attempt番号", "")),
                clean(row.get("status", "")),
                _as_nonnegative_int(row.get("retry番号", "")),
            )
            for row in attempts
        }
        missing_attempts = []
        for item in expected["expected_attempts"]:
            wanted = (
                clean(str(item.get("resolved_ref", ""))),
                int(item["attempt_no"]),
                clean(str(item["status"])),
                int(item["retry_no"]),
            )
            if wanted not in actual_attempts:
                missing_attempts.append(item)
        result.add("E2E-EXEC-D017", not missing_attempts, "retryを含む期待attemptのstatusと番号を失わず保持すること", evidence=missing_attempts or None)
    return result
