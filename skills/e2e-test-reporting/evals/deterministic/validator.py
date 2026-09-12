from __future__ import annotations

import re

from scripts.skills.evals.deterministic.common import clean, add_duplicate_assertion, nonempty_rows
from scripts.skills.evals.deterministic.markdown_parser import find_table, parse_tables
from scripts.skills.evals.deterministic.result import EvalResult

OUTCOMES = {"expected", "unexpected", "flaky", "skipped", "timedOut", "interrupted", "未実行", "確認不能"}
CLEANUP_STATES = {"成功", "失敗", "未確認", "対象なし", "意図的に残した状態", "一部失敗"}


def _int(value: str) -> int | None:
    value = clean(value)
    return int(value) if re.fullmatch(r"\d+", value) else None


def validate(text: str, expected: dict, eval_id: str) -> EvalResult:
    result = EvalResult("e2e-test-reporting", eval_id)
    tables = parse_tables(text)
    env = find_table(tables, section_contains="対象・環境", required_headers=("項目", "値", "参照 / 確認元"))
    run = find_table(tables, section_contains="run全体結果", required_headers=("項目", "値", "確認元", "raw fact / 導出値"))
    primary = find_table(tables, section_contains="primary対象集計", required_headers=("論理的な要求primary対象", "resolved primary TestCase数", "実際に開始したresolved primary TestCase数", "未実行logical理由", "未実行resolved理由"))
    resolved = find_table(tables, section_contains="resolved primary結果 / attempt結果", required_headers=("resolved primary TestCase参照", "結果", "expectedStatus", "outcome", "retry attempt数（別集計）", "初回 / retry履歴", "実行結果参照"))
    trace = find_table(tables, section_contains="TC・E2E・実行・分析追跡", required_headers=("E2E実装参照", "resolved primary TestCase / 実行結果参照", "分析結果参照"))
    cleanup = find_table(tables, section_contains="cleanup・証跡・残存リスク", required_headers=("項目", "状態 / 内容", "安全な参照"))
    missing = [name for name, table in (("対象・環境", env), ("run全体結果", run), ("primary対象集計", primary), ("resolved primary結果 / attempt結果", resolved), ("TC・E2E・実行・分析追跡", trace), ("cleanup・証跡・残存リスク", cleanup)) if table is None]
    result.add("E2E-REPORT-D001", not missing, "reportingの正規テーブルが存在すること", evidence=missing or None)

    env_rows = nonempty_rows(env)
    env_labels = {clean(row.get("項目", "")) for row in env_rows}
    required_env = {"対象機能 / 範囲", "テスト環境URL / origin", "テスト対象version / build ID", "E2Eコードbranch / commit / working tree", "実行日時 / Playwright project"}
    result.add("E2E-REPORT-D002", required_env.issubset(env_labels), "対象・URL・version・コードrevision・実行日時を報告すること", evidence=sorted(required_env - env_labels) or None)

    run_rows = nonempty_rows(run)
    required_run_labels = {"Playwright run全体status", "process exit code", "run-level / global error"}
    run_labels = {clean(row.get("項目", "")) for row in run_rows}
    missing_run_labels = sorted(required_run_labels - run_labels)
    run_raw_missing = [clean(row.get("項目", "")) or "<unknown>" for row in run_rows if not clean(row.get("確認元", "")) or not clean(row.get("raw fact / 導出値", ""))]
    result.add("E2E-REPORT-D003", not run_raw_missing and not missing_run_labels, "run全体status・process exit・run-level errorの確認元とraw / 導出区分があること", evidence={"missing_labels": missing_run_labels, "missing_source_or_kind": run_raw_missing} if run_raw_missing or missing_run_labels else None)

    primary_rows = nonempty_rows(primary)
    primary_names = [clean(row.get("論理的な要求primary対象", "")) for row in primary_rows]
    add_duplicate_assertion(result, "E2E-REPORT-D004", primary_names, "論理的な要求primary対象")
    primary_issues = []
    for row in primary_rows:
        logical = clean(row.get("論理的な要求primary対象", ""))
        resolved_count = _int(row.get("resolved primary TestCase数", ""))
        started_count = _int(row.get("実際に開始したresolved primary TestCase数", ""))
        if resolved_count is None or started_count is None or started_count > resolved_count:
            primary_issues.append({"logical": logical, "resolved": row.get("resolved primary TestCase数"), "started": row.get("実際に開始したresolved primary TestCase数")})
        if resolved_count == 0 and not clean(row.get("未実行logical理由", "")):
            primary_issues.append({"logical": logical, "reason": "zero resolved requires logical unexecuted reason"})
        if resolved_count and not clean(row.get("未実行logical理由", "")) and clean(row.get("未実行logical理由", "")) not in {"", "なし", "-"}:
            primary_issues.append({"logical": logical, "reason": "unexpected logical unexecuted reason"})
    result.add("E2E-REPORT-D005", not primary_issues, "logical primary・resolved primary・開始済み数と未実行理由が整合すること", evidence=primary_issues or None)

    resolved_rows = nonempty_rows(resolved)
    result_refs = [clean(row.get("resolved primary TestCase参照", "")) for row in resolved_rows if clean(row.get("resolved primary TestCase参照", ""))]
    add_duplicate_assertion(result, "E2E-REPORT-D006", result_refs, "resolved primary TestCase参照")
    invalid_outcomes = sorted({clean(row.get("outcome", "")) for row in resolved_rows if clean(row.get("outcome", "")) not in OUTCOMES})
    result.add("E2E-REPORT-D007", not invalid_outcomes, "resolved primary結果のoutcomeがretryと別に保持されていること", evidence=invalid_outcomes or None)
    missing_attempt_separation = [clean(row.get("resolved primary TestCase参照", "")) for row in resolved_rows if _int(row.get("retry attempt数（別集計）", "")) is None]
    result.add("E2E-REPORT-D008", not missing_attempt_separation, "retry attempt数がresolved primary件数と別列で報告されること", evidence=missing_attempt_separation or None)
    retry_history_issues = []
    for row in resolved_rows:
        attempt_count = _int(row.get("retry attempt数（別集計）", ""))
        history = clean(row.get("初回 / retry履歴", ""))
        if attempt_count is not None and attempt_count > 1 and not history:
            retry_history_issues.append(clean(row.get("resolved primary TestCase参照", "")) or "<unknown>")
    result.add("E2E-REPORT-D015", not retry_history_issues, "retry発生時に初回 / retry履歴を保持すること", evidence=retry_history_issues or None)

    trace_rows = nonempty_rows(trace)
    trace_issues = []
    for row in trace_rows:
        if not clean(row.get("E2E実装参照", "")) or not clean(row.get("resolved primary TestCase / 実行結果参照", "")):
            trace_issues.append(clean(row.get("E2E実装参照", "")) or "<unknown>")
    result.add("E2E-REPORT-D009", not trace_issues, "E2E実装参照から実行結果参照へ追跡できること", evidence=trace_issues or None)

    cleanup_rows = nonempty_rows(cleanup)
    cleanup_text = " ".join(row.get("状態 / 内容", "") for row in cleanup_rows)
    invalid_cleanup = []
    for row in cleanup_rows:
        item = clean(row.get("項目", ""))
        value = clean(row.get("状態 / 内容", ""))
        # cleanup行は許可された状態を要求するが、証跡・残存副作用などの
        # 補足行は自由記述であり、cleanup状態として誤検出しない。
        if item == "cleanup" and value and not any(state in value for state in CLEANUP_STATES):
            invalid_cleanup.append(value.split(" / ")[0])
    cleanup_rows_present = any(clean(row.get("項目", "")) == "cleanup" for row in cleanup_rows)
    result.add("E2E-REPORT-D010", cleanup_rows_present and not invalid_cleanup, "cleanup成功・失敗・未確認・対象なし等を区別すること", evidence={"missing_cleanup_row": not cleanup_rows_present, "invalid": invalid_cleanup} if not cleanup_rows_present or invalid_cleanup else None)

    if expected.get("tc_absent"):
        fabricated = sorted(set(re.findall(r"\bTC-\d{3}\b", text)))
        result.add("E2E-REPORT-D011", not fabricated, "TCなし経路でTC IDを創作しないこと", evidence=fabricated or None)
    if "expected_logical_primary_count" in expected:
        mismatch = len(primary_rows) != int(expected["expected_logical_primary_count"])
        result.add("E2E-REPORT-D012", not mismatch, "logical primary対象数がフィクスチャと一致すること", evidence={"expected": expected["expected_logical_primary_count"], "actual": len(primary_rows)} if mismatch else None)
    if "expected_resolved_primary_count" in expected:
        mismatch = len(resolved_rows) != int(expected["expected_resolved_primary_count"])
        result.add("E2E-REPORT-D013", not mismatch, "resolved primary TestCase数がフィクスチャと一致すること", evidence={"expected": expected["expected_resolved_primary_count"], "actual": len(resolved_rows)} if mismatch else None)
    if "required_cleanup_text" in expected:
        cleanup_expected = clean(str(expected["required_cleanup_text"]))
        result.add("E2E-REPORT-D014", cleanup_expected in cleanup_text, "フィクスチャで指定したcleanup状態を失わず報告すること", evidence=cleanup_expected if cleanup_expected not in cleanup_text else None)
    if "required_retry_history" in expected:
        history_text = " ".join(row.get("初回 / retry履歴", "") for row in resolved_rows)
        required_history = clean(str(expected["required_retry_history"]))
        result.add("E2E-REPORT-D016", required_history in history_text, "フィクスチャで指定した初回 / retry履歴を失わず報告すること", evidence=required_history if required_history not in history_text else None)
    return result
