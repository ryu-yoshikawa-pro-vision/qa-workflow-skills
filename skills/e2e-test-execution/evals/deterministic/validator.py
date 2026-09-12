from __future__ import annotations

import re

from scripts.skills.evals.deterministic.common import add_duplicate_assertion, clean, has_value, nonempty_rows
from scripts.skills.evals.deterministic.markdown_parser import find_table, parse_bullets, parse_tables
from scripts.skills.evals.deterministic.result import EvalResult

FULL_RESULT_STATUSES = {"passed", "failed", "timedout", "interrupted"}
RUN_UNAVAILABLE_STATES = {"未確認", "確認不能", "構造化結果不完全"}
RUN_STATUSES = FULL_RESULT_STATUSES | RUN_UNAVAILABLE_STATES
TEST_STATUSES = {"passed", "failed", "timedOut", "skipped", "interrupted"}
EXPECTED_STATUSES = TEST_STATUSES
OUTCOMES = {"skipped", "expected", "unexpected", "flaky"}
EXECUTION_CLASSES = {"要求primary test", "project dependencyとして付随実行されたtest", "project teardownとして付随実行されたtest", "dependency", "teardown"}
CLEANUP_STATES = {"成功", "失敗", "未確認", "対象なし", "意図的に残した状態", "一部失敗"}
STARTED_MARKERS = {"開始", "開始済み", "実行済み", "はい"}
NOT_STARTED_MARKERS = {"", "未開始", "未実行", "未実施", "いいえ", "対象なし"}


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
    worktree_table = find_table(tables, section_contains="working tree・証跡", required_headers=("項目", "実行前", "実行後", "今回runの変更 / 安全確認"))
    cleanup_table = find_table(tables, section_contains="cleanup・残存副作用", required_headers=("cleanup対象 / 実行主体", "状態", "結果 / 残存副作用"))
    missing = [name for name, table in (("実行条件", conditions), ("Playwright run結果", run_table), ("logical primary対象の解決", logical_table), ("resolved primary TestCase結果", resolved_table), ("attempt結果", attempt_table), ("working tree・証跡", worktree_table), ("cleanup・残存副作用", cleanup_table)) if table is None]
    result.add("E2E-EXEC-D001", not missing, "executionの正規テーブルが存在すること", evidence=missing or None)

    condition_rows = nonempty_rows(conditions)
    required_condition_labels = {"対象URL / origin", "実行入口 / command chain", "Playwright project", "retries / repeatEach / workers / parallel", "setup / dependency / webServer / teardown", "branch / HEAD / working tree", "テスト対象version / build ID"}
    missing_condition = sorted(required_condition_labels - {clean(row.get("項目", "")) for row in condition_rows})
    result.add("E2E-EXEC-D002", not missing_condition, "実行入口・実効設定・revision・対象versionを確認すること", evidence=missing_condition or None)
    condition_by_item = {clean(row.get("項目", "")): row for row in condition_rows}
    condition_value_issues = []
    for label in sorted(required_condition_labels):
        row = condition_by_item.get(label)
        if row is None:
            continue
        missing_fields = [
            field
            for field in ("値", "確認元", "raw fact / 導出値")
            if not has_value(row.get(field, ""))
        ]
        if missing_fields:
            condition_value_issues.append({"項目": label, "fields": missing_fields})
    result.add(
        "E2E-EXEC-D018",
        not missing_condition and not condition_value_issues,
        "preflightの必須項目が空欄ではなく、値または明示状態と確認元を持つこと",
        evidence={"missing_items": missing_condition, "missing_values": condition_value_issues}
        if missing_condition or condition_value_issues
        else None,
    )

    run_rows = nonempty_rows(run_table)
    run_value_by_item = {clean(row.get("項目", "")): row for row in run_rows}
    required_run_labels = {"Playwright run全体status", "CLI process exit code", "run-level / global error", "runner開始", "result artifactの今回run生成・更新"}
    missing_run_labels = sorted(required_run_labels - set(run_value_by_item))
    run_status = clean(run_value_by_item.get("Playwright run全体status", {}).get("値", ""))
    invalid_run_status = [run_status] if run_status not in RUN_STATUSES else []
    run_status_row = run_value_by_item.get("Playwright run全体status", {})
    run_status_kind = clean(run_status_row.get("raw fact / 導出値", ""))
    run_status_source = clean(run_status_row.get("確認元", ""))
    raw_status_issues = []
    if run_status in FULL_RESULT_STATUSES and run_status_kind != "raw fact":
        raw_status_issues.append({"reason": "FullResult.status must be directly reported as raw fact", "kind": run_status_kind})
    if run_status in FULL_RESULT_STATUSES and any(token in run_status_source.lower() for token in ("process", "exit code", "終了コード")):
        raw_status_issues.append({"reason": "process exit code cannot be used as Playwright run status", "source": run_status_source})
    result.add(
        "E2E-EXEC-D003",
        not missing_run_labels and not invalid_run_status and not raw_status_issues,
        "Playwright run全体statusとrun-level結果の項目が存在し、FullResult.statusとworkflow上の確認不能を分離すること",
        evidence={"missing": missing_run_labels, "invalid_status": invalid_run_status, "raw_status_issues": raw_status_issues}
        if missing_run_labels or invalid_run_status or raw_status_issues
        else None,
    )
    raw_missing = []
    for row in run_rows:
        if not has_value(row.get("値", "")) or not has_value(row.get("確認元", "")) or not has_value(row.get("raw fact / 導出値", "")):
            raw_missing.append(clean(row.get("項目", "")) or "<unknown>")
    result.add("E2E-EXEC-D004", not raw_missing and not missing_run_labels, "run全体結果の確認元とraw fact / 導出値区分があること", evidence={"missing_labels": missing_run_labels, "missing_source_or_kind": raw_missing} if raw_missing or missing_run_labels else None)
    artifact_row = run_value_by_item.get("result artifactの今回run生成・更新", {})
    artifact_value = clean(artifact_row.get("値", ""))
    runner_value = clean(run_value_by_item.get("runner開始", {}).get("値", ""))
    execution_state = clean(bullets.get("実行成果物状態", ""))
    runner_started = runner_value in STARTED_MARKERS
    preflight_block = execution_state == "ブロック中" and runner_value in NOT_STARTED_MARKERS
    artifact_current = artifact_value in {"はい", "生成", "更新"}
    artifact_not_generated = artifact_value in {"いいえ", "未生成", "未更新", "対象なし", "未確認", "確認不能"}
    artifact_ok = artifact_current if runner_started else preflight_block and artifact_not_generated
    result.add(
        "E2E-EXEC-D005",
        artifact_ok,
        "runner開始済みなら今回runで生成・更新したartifactを要求し、preflight blockならrunner未開始・artifact未生成を許容すること",
        evidence={"runner": runner_value, "execution_state": execution_state, "artifact": artifact_value}
        if not artifact_ok
        else None,
    )
    setup_value = clean(condition_by_item.get("setup / dependency / webServer / teardown", {}).get("値", ""))
    ownership_issues = []
    if "reuseExistingServer" in setup_value or "既存processを再利用" in setup_value or "既存プロセスを再利用" in setup_value:
        if not any(token in setup_value for token in ("終了対象外", "終了しない", "cleanup対象外", "所有しない")):
            ownership_issues.append("reuseExistingServerで再利用した既存processをcleanup終了対象外としていない")
    result.add(
        "E2E-EXEC-D020",
        not ownership_issues,
        "webServerの今回run所有processと既存再利用processを区別し、非所有processをcleanup終了しないこと",
        evidence=ownership_issues or None,
    )

    worktree_rows = nonempty_rows(worktree_table)
    required_worktree_labels = {"working tree", "output / report / snapshot / source", "trace / screenshot / video / HTML report / network / storageState", "stale artifactの今回結果利用"}
    missing_worktree = sorted(required_worktree_labels - {clean(row.get("項目", "")) for row in worktree_rows})
    worktree_issues = []
    worktree_by_item = {clean(row.get("項目", "")): row for row in worktree_rows}
    for label in sorted(required_worktree_labels):
        row = worktree_by_item.get(label)
        if row is None:
            continue
        missing_fields = [
            field
            for field in ("実行前", "実行後", "今回runの変更 / 安全確認")
            if not has_value(row.get(field, ""))
        ]
        if missing_fields:
            worktree_issues.append({"項目": label, "fields": missing_fields})
    result.add(
        "E2E-EXEC-D019",
        not missing_worktree and not worktree_issues,
        "working tree・証跡・stale artifact利用の前後状態と安全確認を記録すること",
        evidence={"missing_items": missing_worktree, "issues": worktree_issues}
        if missing_worktree or worktree_issues
        else None,
    )
    output_evidence = " ".join(worktree_by_item.get("output / report / snapshot / source", {}).values())
    stale_evidence = " ".join(worktree_by_item.get("stale artifactの今回結果利用", {}).values())
    current_artifact_markers = ("今回run", "今回生成", "今回更新")
    stale_not_used_markers = ("利用していない", "未利用", "対象なし", "なし")
    artifact_evidence_issue = runner_started and not any(marker in output_evidence for marker in current_artifact_markers)
    stale_evidence_issue = not any(marker in stale_evidence for marker in stale_not_used_markers)
    result.add(
        "E2E-EXEC-D021",
        not artifact_evidence_issue and not stale_evidence_issue,
        "runner開始時はartifactの今回run生成・更新根拠を示し、stale artifactを今回結果として利用しないこと",
        evidence={"artifact_evidence": output_evidence, "stale_evidence": stale_evidence}
        if artifact_evidence_issue or stale_evidence_issue
        else None,
    )
    result.add(
        "E2E-EXEC-D022",
        not preflight_block or (has_value(bullets.get("ブロック中", "")) and clean(bullets.get("ブロック中", "")) not in {"なし", "対象なし", "不要"}),
        "preflight block時にrunner未開始・artifact未生成の理由を明示すること",
        evidence=bullets.get("ブロック中", "") if preflight_block and not has_value(bullets.get("ブロック中", "")) else None,
    )

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
        expected_status = clean(row.get("expectedStatus", ""))
        if expected_status not in EXPECTED_STATUSES:
            attempt_issues.append({"field": "expectedStatus", "value": expected_status})
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
        if clean(row.get("実行開始", "")) in STARTED_MARKERS
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
