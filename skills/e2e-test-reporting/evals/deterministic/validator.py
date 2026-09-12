from __future__ import annotations

import re

from scripts.skills.evals.deterministic.common import add_duplicate_assertion, clean, has_value, nonempty_rows
from scripts.skills.evals.deterministic.markdown_parser import find_table, parse_tables
from scripts.skills.evals.deterministic.result import EvalResult

FULL_RESULT_STATUSES = {"passed", "failed", "timedout", "interrupted"}
RUN_UNAVAILABLE_STATES = {"未確認", "確認不能", "構造化結果不完全"}
TEST_STATUSES = {"passed", "failed", "timedOut", "skipped", "interrupted"}
EXPECTED_STATUSES = {"passed", "failed", "timedOut", "skipped", "interrupted"}
OUTCOMES = {"skipped", "expected", "unexpected", "flaky"}
CLEANUP_STATES = {"成功", "失敗", "未確認", "対象なし", "意図的に残した状態", "一部失敗"}
STARTED_MARKERS = {"開始", "開始済み", "実行済み", "はい"}


def _has_unexecuted_reason(value: str) -> bool:
    return has_value(value) and clean(value) not in {"なし", "対象なし", "不要"}


def _int(value: str) -> int | None:
    value = clean(value)
    return int(value) if re.fullmatch(r"\d+", value) else None


def validate(text: str, expected: dict, eval_id: str) -> EvalResult:
    result = EvalResult("e2e-test-reporting", eval_id)
    tables = parse_tables(text)
    env = find_table(tables, section_contains="対象・環境", required_headers=("項目", "値", "参照 / 確認元"))
    run = find_table(tables, section_contains="run全体結果", required_headers=("項目", "値", "確認元", "raw fact / 導出値"))
    primary = find_table(tables, section_contains="primary対象集計", required_headers=("論理的な要求primary対象", "E2E実装参照", "TC ID（存在時のみ）", "resolved primary TestCase数", "実際に開始したresolved primary TestCase数", "未実行logical理由", "未実行resolved理由"))
    resolved = find_table(tables, section_contains="resolved primary結果 / attempt結果", required_headers=("論理的な要求primary対象", "resolved primary TestCase参照", "実行開始", "結果", "未実行理由", "expectedStatus", "outcome", "retry attempt数（別集計）", "初回 / retry履歴", "実行結果参照"))
    trace = find_table(tables, section_contains="TC・E2E・実行・分析追跡", required_headers=("E2E実装参照", "resolved primary TestCase / 実行結果参照", "分析結果参照"))
    cleanup = find_table(tables, section_contains="cleanup・証跡・残存リスク", required_headers=("項目", "状態 / 内容", "安全な参照"))
    missing = [name for name, table in (("対象・環境", env), ("run全体結果", run), ("primary対象集計", primary), ("resolved primary結果 / attempt結果", resolved), ("TC・E2E・実行・分析追跡", trace), ("cleanup・証跡・残存リスク", cleanup)) if table is None]
    result.add("E2E-REPORT-D001", not missing, "reportingの正規テーブルが存在すること", evidence=missing or None)

    env_rows = nonempty_rows(env)
    env_labels = {clean(row.get("項目", "")) for row in env_rows}
    required_env = {"対象機能 / 範囲", "テスト環境URL / origin", "テスト対象version / build ID", "E2Eコードbranch / commit / working tree", "実行日時 / Playwright project"}
    env_by_item = {clean(row.get("項目", "")): row for row in env_rows}
    env_value_issues = []
    for label in sorted(required_env):
        row = env_by_item.get(label)
        if row is None:
            continue
        if not has_value(row.get("値", "")) or not has_value(row.get("参照 / 確認元", "")):
            env_value_issues.append(label)
    result.add(
        "E2E-REPORT-D002",
        required_env.issubset(env_labels) and not env_value_issues,
        "対象・URL・version・コードrevision・実行日時を値または明示状態と参照元付きで報告すること",
        evidence={"missing_labels": sorted(required_env - env_labels), "missing_values": env_value_issues}
        if not required_env.issubset(env_labels) or env_value_issues
        else None,
    )

    run_rows = nonempty_rows(run)
    required_run_labels = {"Playwright run全体status", "process exit code", "run-level / global error"}
    run_labels = {clean(row.get("項目", "")) for row in run_rows}
    missing_run_labels = sorted(required_run_labels - run_labels)
    run_by_item = {clean(row.get("項目", "")): row for row in run_rows}
    run_raw_missing = [clean(row.get("項目", "")) or "<unknown>" for row in run_rows if not has_value(row.get("値", "")) or not has_value(row.get("確認元", "")) or not has_value(row.get("raw fact / 導出値", ""))]
    run_status = clean(run_by_item.get("Playwright run全体status", {}).get("値", ""))
    invalid_run_status = run_status not in FULL_RESULT_STATUSES | RUN_UNAVAILABLE_STATES
    run_status_row = run_by_item.get("Playwright run全体status", {})
    raw_run_status_issue = (
        run_status in FULL_RESULT_STATUSES
        and (
            clean(run_status_row.get("raw fact / 導出値", "")) != "raw fact"
            or any(token in clean(run_status_row.get("確認元", "")).lower() for token in ("process", "exit code", "終了コード"))
        )
    )
    result.add(
        "E2E-REPORT-D003",
        not run_raw_missing and not missing_run_labels and not invalid_run_status and not raw_run_status_issue,
        "run全体status・process exit・run-level errorを確認元とraw / 導出区分付きで報告し、process exit codeをPlaywright raw statusへ代用しないこと",
        evidence={"missing_labels": missing_run_labels, "missing_source_or_kind": run_raw_missing, "invalid_status": run_status, "raw_status_issue": raw_run_status_issue}
        if run_raw_missing or missing_run_labels or invalid_run_status or raw_run_status_issue
        else None,
    )

    primary_rows = nonempty_rows(primary)
    primary_names = [clean(row.get("論理的な要求primary対象", "")) for row in primary_rows]
    add_duplicate_assertion(result, "E2E-REPORT-D004", primary_names, "論理的な要求primary対象")
    primary_field_issues = []
    for row in primary_rows:
        missing_fields = [
            field
            for field in ("論理的な要求primary対象", "E2E実装参照", "resolved primary TestCase数", "実際に開始したresolved primary TestCase数")
            if not has_value(row.get(field, ""))
        ]
        if missing_fields:
            primary_field_issues.append({"logical": clean(row.get("論理的な要求primary対象", "")) or "<unknown>", "fields": missing_fields})
    result.add(
        "E2E-REPORT-D019",
        bool(primary_rows) and not primary_field_issues,
        "reporting対象として開始したlogical primaryを最低1件、対象・E2E実装参照・件数付きで記録すること",
        evidence={"missing_rows": not primary_rows, "issues": primary_field_issues}
        if not primary_rows or primary_field_issues
        else None,
    )
    resolved_rows = nonempty_rows(resolved)
    resolved_by_logical: dict[str, list[dict[str, str]]] = {}
    for row in resolved_rows:
        resolved_by_logical.setdefault(clean(row.get("論理的な要求primary対象", "")), []).append(row)
    primary_issues = []
    for row in primary_rows:
        logical = clean(row.get("論理的な要求primary対象", ""))
        resolved_count = _int(row.get("resolved primary TestCase数", ""))
        started_count = _int(row.get("実際に開始したresolved primary TestCase数", ""))
        logical_rows = resolved_by_logical.get(logical, [])
        actual_started_count = sum(clean(item.get("実行開始", "")) in STARTED_MARKERS for item in logical_rows)
        logical_reason = clean(row.get("未実行logical理由", ""))
        resolved_reason = clean(row.get("未実行resolved理由", ""))
        if resolved_count is None or started_count is None or started_count > resolved_count:
            primary_issues.append({"logical": logical, "resolved": row.get("resolved primary TestCase数"), "started": row.get("実際に開始したresolved primary TestCase数")})
        if resolved_count is not None and len(logical_rows) != resolved_count:
            primary_issues.append({"logical": logical, "reason": "resolved count does not match resolved result rows", "declared": resolved_count, "actual": len(logical_rows)})
        if started_count is not None and actual_started_count != started_count:
            primary_issues.append({"logical": logical, "reason": "started count does not match resolved result rows", "declared": started_count, "actual": actual_started_count})
        if resolved_count == 0 and not _has_unexecuted_reason(logical_reason):
            primary_issues.append({"logical": logical, "reason": "zero resolved requires logical unexecuted reason"})
        if resolved_count is not None and resolved_count > (started_count or 0) and not _has_unexecuted_reason(resolved_reason):
            primary_issues.append({"logical": logical, "reason": "resolved > started requires resolved unexecuted reason"})
        if resolved_count and _has_unexecuted_reason(logical_reason):
            primary_issues.append({"logical": logical, "reason": "resolved logical target cannot carry an unexecuted logical reason"})
    result.add("E2E-REPORT-D005", not primary_issues, "logical primary・resolved primary・開始済み数と未実行理由が整合すること", evidence=primary_issues or None)

    result_refs = [clean(row.get("resolved primary TestCase参照", "")) for row in resolved_rows if clean(row.get("resolved primary TestCase参照", ""))]
    add_duplicate_assertion(result, "E2E-REPORT-D006", result_refs, "resolved primary TestCase参照")
    resolved_field_issues = []
    for row in resolved_rows:
        missing_fields = [
            field
            for field in ("論理的な要求primary対象", "resolved primary TestCase参照", "実行開始")
            if not has_value(row.get(field, ""))
        ]
        expected_status = clean(row.get("expectedStatus", ""))
        outcome = clean(row.get("outcome", ""))
        started = clean(row.get("実行開始", "")) in STARTED_MARKERS
        if started:
            if not has_value(row.get("結果", "")):
                missing_fields.append("結果")
            if not has_value(row.get("実行結果参照", "")):
                missing_fields.append("実行結果参照")
            if not expected_status or expected_status not in EXPECTED_STATUSES:
                missing_fields.append("expectedStatus(許可値)")
            if not outcome or outcome not in OUTCOMES:
                missing_fields.append("outcome(許可値)")
            if clean(row.get("結果", "")) not in TEST_STATUSES:
                missing_fields.append("結果(TestResult.status許可値)")
        else:
            if not _has_unexecuted_reason(row.get("未実行理由", "")):
                missing_fields.append("未実行理由")
            if has_value(row.get("結果", "")):
                missing_fields.append("結果(未開始では空欄)")
            if has_value(row.get("実行結果参照", "")):
                missing_fields.append("実行結果参照(未開始では空欄)")
            if expected_status and expected_status not in EXPECTED_STATUSES:
                missing_fields.append("expectedStatus(許可値)")
            if outcome and outcome not in OUTCOMES:
                missing_fields.append("outcome(許可値)")
        if missing_fields:
            resolved_field_issues.append({"ref": clean(row.get("resolved primary TestCase参照", "")) or "<unknown>", "fields": missing_fields})
    result.add(
        "E2E-REPORT-D017",
        not resolved_field_issues,
        "resolved primary結果がlogical対象・開始状態・expectedStatus・outcome・実行結果参照を持つこと",
        evidence=resolved_field_issues or None,
    )
    invalid_expected_status = sorted({clean(row.get("expectedStatus", "")) for row in resolved_rows if clean(row.get("expectedStatus", "")) and clean(row.get("expectedStatus", "")) not in EXPECTED_STATUSES})
    invalid_outcomes = sorted({clean(row.get("outcome", "")) for row in resolved_rows if clean(row.get("outcome", "")) and clean(row.get("outcome", "")) not in OUTCOMES})
    result.add("E2E-REPORT-D007", not invalid_outcomes and not invalid_expected_status, "resolved primaryのexpectedStatusとoutcomeを別のPlaywright値域として保持すること", evidence={"invalid_expectedStatus": invalid_expected_status, "invalid_outcome": invalid_outcomes} if invalid_outcomes or invalid_expected_status else None)
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
    primary_refs = {
        clean(row.get("論理的な要求primary対象", "")): clean(row.get("E2E実装参照", ""))
        for row in primary_rows
        if clean(row.get("論理的な要求primary対象", "")) and clean(row.get("E2E実装参照", ""))
    }
    expected_trace_pairs: set[tuple[str, str]] = set()
    for row in primary_rows:
        logical = clean(row.get("論理的な要求primary対象", ""))
        implementation_ref = clean(row.get("E2E実装参照", ""))
        if not logical or not implementation_ref:
            continue
        logical_resolved = resolved_by_logical.get(logical, [])
        if not logical_resolved:
            expected_trace_pairs.add((implementation_ref, logical))
            continue
        for resolved_row in logical_resolved:
            resolved_ref = clean(resolved_row.get("resolved primary TestCase参照", ""))
            result_ref = clean(resolved_row.get("実行結果参照", ""))
            trace_ref = result_ref if clean(resolved_row.get("実行開始", "")) in STARTED_MARKERS else resolved_ref
            if trace_ref:
                expected_trace_pairs.add((implementation_ref, trace_ref))
    trace_pairs: set[tuple[str, str]] = set()
    trace_issues = []
    for row in trace_rows:
        implementation_ref = clean(row.get("E2E実装参照", ""))
        execution_ref = clean(row.get("resolved primary TestCase / 実行結果参照", ""))
        pair = (implementation_ref, execution_ref)
        if not implementation_ref or not execution_ref:
            trace_issues.append({"implementation_ref": implementation_ref or "<unknown>", "reason": "implementation and execution references are required"})
            continue
        if implementation_ref not in set(primary_refs.values()):
            trace_issues.append({"implementation_ref": implementation_ref, "reason": "implementation reference is not a reporting target"})
        allowed_execution_refs = {expected_ref for expected_impl, expected_ref in expected_trace_pairs if expected_impl == implementation_ref}
        if execution_ref not in allowed_execution_refs:
            trace_issues.append({"implementation_ref": implementation_ref, "execution_ref": execution_ref, "reason": "execution reference is not linked to a resolved/logical target"})
        trace_pairs.add(pair)
    missing_trace_pairs = sorted(expected_trace_pairs - trace_pairs)
    result.add("E2E-REPORT-D009", not trace_issues and not missing_trace_pairs, "E2E実装参照から実際のresolved / logical追跡参照へ完全一致で辿れること", evidence={"invalid": trace_issues, "missing": missing_trace_pairs} if trace_issues or missing_trace_pairs else None)
    trace_required = bool(primary_rows or resolved_rows)
    result.add(
        "E2E-REPORT-D018",
        not trace_required or bool(trace_rows),
        "E2E対象・resolved結果が存在する経路では追跡表に1件以上の有効行があること",
        evidence={"trace_required": trace_required, "trace_rows": len(trace_rows)} if trace_required and not trace_rows else None,
    )

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
