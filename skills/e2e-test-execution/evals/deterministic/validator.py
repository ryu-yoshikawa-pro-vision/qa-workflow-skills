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
RESOLVED_NOT_STARTED_MARKERS = NOT_STARTED_MARKERS - {""}
NON_OWNER_MARKERS = {"今回runは所有しない", "今回runが所有しない", "所有しない", "非所有", "今回runの所有ではない"}
NOT_CLEANUP_MARKERS = {"対象外", "対象なし", "cleanup対象外", "終了対象外", "終了しない", "しない"}
ACTUAL_REUSE_NON_CLEANUP_MARKERS = {"対象外", "対象なし", "cleanup対象外", "終了対象外"}
RUN_NOT_STARTED_ERROR_STATES = {"未実施", "未確認", "確認不能", "対象なし"}
UNKNOWN_SAFETY_MARKERS = ("未確認", "確認不能", "不明", "未取得", "未指定", "確認待ち", "未実施")
SETUP_CONTRACT_LABELS = ("setup", "dependency", "webServer", "teardown")
SETUP_COMPONENT_LABELS = (
    "setup",
    "globalSetup",
    "dependency",
    "dependencies",
    "webServer",
    "teardown",
    "globalTeardown",
)
SIDE_EFFECT_COMPONENT_LABELS = ("scope", "許可範囲")
CLEANUP_COMPONENT_LABELS = ("対象", "cleanup対象", "方法")
STRUCTURED_SEPARATOR_RE = re.compile(r"\s+[/／]\s+")
EXTERNAL_PREPARATION_NOT_NEEDED = {"対象なし", "なし", "不要", "none", "n/a", "-"}
WEBSERVER_STARTED_BEFORE_RUN = "実行前から存在"
WEBSERVER_STARTED_BY_RUN = "今回runが起動"
NO_CLEANUP_METHOD_RE = re.compile(r"^(?:cleanup不要|対象なし|不要)(?:\s*[（(].*[）)])?$")
RAW_WEBSERVER_CONFIG_ONLY_RE = re.compile(
    r"^(?:(?:playwright\.config\.ts(?:の|で|:)|config(?:上の|の|で|:))?reuseexistingserver)(?:[=:：](?:true|false|!process\.env\.ci))?(?:(?:の設定)?を確認(?:済み|した|しました)?)?$",
    re.IGNORECASE,
)
RUN_START_REQUIRED_CONDITIONS = {
    "対象URL / origin",
    "実行入口 / command chain",
    "Playwright project",
    "retries / repeatEach / workers / parallel",
    "setup / dependency / webServer / teardown",
    "必要な認証 / テストデータ / 開始状態",
    "副作用の許可範囲 / 最大回数",
    "run外準備",
    "runner管理cleanup対象 / 方法",
    "run外cleanup対象 / 方法",
}
REQUIRED_EXECUTION_CONDITIONS = RUN_START_REQUIRED_CONDITIONS | {"run外準備"}


def _setup_contract_parts(setup_value: str) -> tuple[str, ...] | None:
    value = clean(setup_value)
    parts = [clean(part) for part in STRUCTURED_SEPARATOR_RE.split(value)]
    if len(parts) != len(SETUP_CONTRACT_LABELS) or any(not part for part in parts):
        return None
    return tuple(parts)


def _webserver_candidate(setup_value: str) -> str:
    parts = _setup_contract_parts(setup_value)
    return parts[2] if parts else ""


def _webserver_state(setup_value: str) -> str:
    candidate = _webserver_candidate(setup_value)
    lowered = candidate.lower()
    if not candidate or lowered in {"none", "n/a", "対象なし", "未使用", "なし", "-"}:
        return "none"
    if _is_explicit_unavailable(candidate, set(UNKNOWN_SAFETY_MARKERS)):
        return "unknown"
    webserver_value = re.fullmatch(r"webserver\s*=\s*(.+)", candidate, re.IGNORECASE)
    if webserver_value and _is_explicit_unavailable(webserver_value.group(1), set(UNKNOWN_SAFETY_MARKERS)):
        return "unknown"
    if "webserver" in lowered and any(token in lowered for token in ("none", "なし", "対象なし", "未使用")):
        return "none"
    return "configured"


def _teardown_candidate(setup_value: str) -> str:
    parts = _setup_contract_parts(setup_value)
    return parts[3] if parts else ""


def _has_explicit_runner_cleanup_target(setup_value: str) -> bool:
    candidate = _teardown_candidate(setup_value)
    if not candidate or _is_unresolved_component(candidate, set(SETUP_COMPONENT_LABELS)):
        return False
    return candidate.lower() not in {"none", "n/a", "なし", "対象なし", "未使用", "-"}


def _as_nonnegative_int(value: str) -> int | None:
    value = clean(value)
    if not re.fullmatch(r"\d+", value):
        return None
    return int(value)


def _is_run_owned(value: str) -> bool:
    value = clean(value)
    return value not in NON_OWNER_MARKERS and any(token in value for token in ("今回runが所有", "今回run所有"))


def _is_cleanup_target(value: str) -> bool:
    value = clean(value)
    if not value or any(marker in value for marker in NOT_CLEANUP_MARKERS):
        return False
    return any(marker in value for marker in ("対象", "cleanup対象", "終了対象"))


def _cleanup_subject(value: str) -> str | None:
    value = clean(value)
    if any(marker in value for marker in ("runner管理", "Playwright runner", "runner cleanup")):
        return "runner"
    if any(marker in value for marker in ("run外", "外部cleanup", "run外処理")):
        return "external"
    return None


def _is_explicit_unavailable(value: str, allowed: set[str]) -> bool:
    value = clean(value)
    return value in allowed or any(
        value.startswith(f"{state}{delimiter}")
        for state in allowed
        for delimiter in ("（", "(", ":", "：")
    )


def _component_value_without_known_label(value: str, labels: tuple[str, ...] | set[str]) -> str:
    value = clean(value)
    for label in labels:
        match = re.fullmatch(rf"{re.escape(label)}\s*[=＝:：]\s*(.*)", value, re.IGNORECASE)
        if match:
            return clean(match.group(1))
    return value


def _is_unresolved_component(value: str, labels: tuple[str, ...] | set[str]) -> bool:
    component = _component_value_without_known_label(value, labels)
    return _is_explicit_unavailable(component, set(UNKNOWN_SAFETY_MARKERS))


def _is_raw_test_status(value: str) -> bool:
    return clean(value) in TEST_STATUSES


def _has_concrete_url_or_origin(value: str) -> bool:
    return re.search(r"https?://[^\s|]+", clean(value), re.IGNORECASE) is not None


def _has_concrete_side_effect_limit(value: str) -> bool:
    value = clean(value)
    if not value or value.lower() in {"確認済み", "確認完了", "ok", "checked", "問題なし"}:
        return False
    parts = STRUCTURED_SEPARATOR_RE.split(value, maxsplit=1)
    if len(parts) != 2:
        return False
    scope, count = (part.strip() for part in parts)
    if (
        not scope
        or scope.lower() in {"確認済み", "確認完了", "ok", "checked", "問題なし"}
        or _is_unresolved_component(scope, SIDE_EFFECT_COMPONENT_LABELS)
        or _is_unresolved_component(count, SIDE_EFFECT_COMPONENT_LABELS)
    ):
        return False
    return re.search(r"(?:max(?:imum)?\s*\d+|最大\s*\d+|\d+\s*(?:回|times)(?:まで)?)", count, re.IGNORECASE) is not None


def _has_concrete_cleanup_method(value: str) -> bool:
    value = clean(value)
    lowered = value.lower()
    if not value or lowered in {"確認済み", "確認完了", "ok", "checked", "問題なし"}:
        return False
    if _is_explicit_unavailable(value, set(UNKNOWN_SAFETY_MARKERS)):
        return False
    components = STRUCTURED_SEPARATOR_RE.split(value)
    if len(components) > 1 and any(
        _is_unresolved_component(component, CLEANUP_COMPONENT_LABELS) for component in components
    ):
        return False
    # no-cleanup is a valid state; its consistency with known targets is checked
    # separately from this safety-field concreteness check.
    if NO_CLEANUP_METHOD_RE.fullmatch(value):
        return True
    # Do not maintain a natural-language allow-list here.  A non-empty value
    # that is not merely a confirmation/unavailable marker is the recorded
    # method description and may be written in ordinary domain language.
    return True


def _cleanup_target_none_has_evidence(row: dict[str, str]) -> bool:
    value = clean(row.get("結果 / 残存副作用", ""))
    if value in {"", "なし", "対象なし", "run外準備なし", "cleanup不要", "不要"}:
        return False
    return bool(re.search(r"(?:cleanup不要|対象なし|不要).*(?:根拠|理由|確認|準備|副作用)|(?:根拠|理由|確認|準備|副作用).*(?:cleanup不要|対象なし|不要)", value))


def _is_raw_webserver_config_only(value: str) -> bool:
    normalized = re.sub(r"\s+", "", clean(value)).lower()
    return RAW_WEBSERVER_CONFIG_ONLY_RE.fullmatch(normalized) is not None


def _external_preparation_value_performed(value: str) -> bool:
    value = clean(value)
    return value in {"実施", "実施済み"} or value.startswith(("実施（", "実施(", "実施:", "実施："))


def _external_preparation_not_needed(value: str) -> bool:
    return clean(value).lower() in EXTERNAL_PREPARATION_NOT_NEEDED


def _external_preparation_confirmed(value: str) -> bool:
    value = clean(value)
    return bool(value) and not _is_explicit_unavailable(value, set(UNKNOWN_SAFETY_MARKERS)) and (
        _external_preparation_value_performed(value) or _external_preparation_not_needed(value)
    )


def _external_preparation_performed(condition_by_item: dict[str, dict[str, str]]) -> bool:
    value = clean(condition_by_item.get("run外準備", {}).get("値", ""))
    return _external_preparation_value_performed(value)


def _compute_expected_testcase_outcome(expected_status: str, attempt_statuses: list[str]) -> str:
    skipped = 0
    did_not_run = 0
    expected = 0
    interrupted = 0
    unexpected = 0
    for status in attempt_statuses:
        if status == "interrupted":
            interrupted += 1
        elif status == "skipped" and expected_status == "skipped":
            skipped += 1
        elif status == "skipped":
            did_not_run += 1
        elif status == expected_status:
            expected += 1
        else:
            unexpected += 1

    if expected == 0 and unexpected == 0:
        return "skipped"
    if unexpected == 0:
        return "expected"
    if expected == 0 and skipped == 0:
        return "unexpected"
    return "flaky"


def _attempt_sequence_issues(
    rows: list[dict[str, str]],
    group_key,
) -> tuple[list[dict], list[dict]]:
    grouped: dict[object, list[dict[str, str]]] = {}
    for row in rows:
        grouped.setdefault(group_key(row), []).append(row)

    duplicate_keys = []
    order_issues = []
    for group, group_rows in grouped.items():
        seen = set()
        for row in group_rows:
            key = (
                _as_nonnegative_int(row.get("attempt番号", "")),
                _as_nonnegative_int(row.get("retry番号", "")),
            )
            if key in seen:
                duplicate_keys.append({"group": group, "attempt": key})
            seen.add(key)
        ordered = sorted(
            group_rows,
            key=lambda row: (
                _as_nonnegative_int(row.get("attempt番号", ""))
                if _as_nonnegative_int(row.get("attempt番号", "")) is not None
                else -1,
                _as_nonnegative_int(row.get("retry番号", ""))
                if _as_nonnegative_int(row.get("retry番号", "")) is not None
                else -1,
            ),
        )
        attempt_numbers = [_as_nonnegative_int(row.get("attempt番号", "")) for row in ordered]
        retry_numbers = [_as_nonnegative_int(row.get("retry番号", "")) for row in ordered]
        if attempt_numbers != list(range(1, len(ordered) + 1)) or retry_numbers != list(range(len(ordered))):
            order_issues.append(
                {
                    "group": group,
                    "attempt_numbers": attempt_numbers,
                    "retry_numbers": retry_numbers,
                }
            )
    return duplicate_keys, order_issues


def validate(text: str, expected: dict, eval_id: str) -> EvalResult:
    result = EvalResult("e2e-test-execution", eval_id)
    tables = parse_tables(text)
    bullets = parse_bullets(text)
    conditions = find_table(tables, section_contains="実行条件", required_headers=("項目", "値", "確認元", "raw fact / 導出値"))
    run_table = find_table(tables, section_contains="Playwright run結果", required_headers=("項目", "値", "確認元", "raw fact / 導出値"))
    webserver_table = find_table(tables, section_contains="webServer process ownership", required_headers=("server識別子", "起動状態", "今回run所有か", "既存 / 再利用か", "cleanup対象か", "根拠"))
    logical_table = find_table(tables, section_contains="logical primary対象の解決", required_headers=("論理的な要求primary対象", "resolved primary TestCase数", "未実行 / 解決不能理由"))
    resolved_table = find_table(
        tables,
        section_contains="resolved primary TestCase結果",
        required_headers=("resolved primary TestCase参照", "論理要求primary対象", "実行開始", "結果 / 未実行理由", "expectedStatus", "outcome"),
    )
    attempt_table = find_table(
        tables,
        section_contains="attempt結果",
        required_headers=(
            "resolved primary TestCase参照",
            "attempt番号",
            "実行区分",
            "test file / title path",
            "project",
            "repeatEachIndex",
            "status",
            "retry番号",
            "duration",
            "error / errors",
        ),
    )
    worktree_table = find_table(tables, section_contains="working tree・証跡", required_headers=("項目", "実行前", "実行後", "今回runの変更 / 安全確認"))
    cleanup_table = find_table(tables, section_contains="cleanup・残存副作用", required_headers=("cleanup対象 / 実行主体", "状態", "結果 / 残存副作用"))
    missing = [name for name, table in (("実行条件", conditions), ("Playwright run結果", run_table), ("logical primary対象の解決", logical_table), ("resolved primary TestCase結果", resolved_table), ("attempt結果", attempt_table), ("working tree・証跡", worktree_table), ("cleanup・残存副作用", cleanup_table)) if table is None]
    result.add("E2E-EXEC-D001", not missing, "executionの正規テーブルが存在すること", evidence=missing or None)

    condition_rows = nonempty_rows(conditions)
    required_condition_labels = REQUIRED_EXECUTION_CONDITIONS | {"branch / HEAD / working tree", "テスト対象version / build ID"}
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
            and not (field == "値" and label == "run外準備" and _external_preparation_not_needed(row.get(field, "")))
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
    webserver_rows = nonempty_rows(webserver_table)
    setup_value = clean(condition_by_item.get("setup / dependency / webServer / teardown", {}).get("値", ""))
    started_safety_issues = []
    if runner_started:
        for label in sorted(RUN_START_REQUIRED_CONDITIONS):
            row = condition_by_item.get(label)
            value = clean(row.get("値", "")) if row else ""
            if label == "setup / dependency / webServer / teardown":
                setup_parts = _setup_contract_parts(value)
                if setup_parts is None:
                    started_safety_issues.append(
                        {
                            "項目": label,
                            "値": value,
                            "reason": "setup / dependency / webServer / teardownは空欄なしの4要素が必要",
                        }
                    )
                else:
                    unresolved_parts = [
                        {"要素": component, "値": component_value}
                        for component, component_value in zip(SETUP_CONTRACT_LABELS, setup_parts)
                        if _is_unresolved_component(component_value, set(SETUP_COMPONENT_LABELS))
                    ]
                    if unresolved_parts:
                        started_safety_issues.append(
                            {
                                "項目": label,
                                "値": value,
                                "reason": "4要素それぞれの状態が未確定",
                                "未確定要素": unresolved_parts,
                            }
                        )
                continue
            if label == "run外準備" and not _external_preparation_confirmed(value):
                started_safety_issues.append(
                    {
                        "項目": label,
                        "値": value,
                        "reason": "runner開始時はrun外準備を実施または実施不要として確定する必要がある",
                    }
                )
                continue
            if _is_explicit_unavailable(value, set(UNKNOWN_SAFETY_MARKERS)):
                started_safety_issues.append({"項目": label, "値": value})
                continue
            if label == "対象URL / origin" and not _has_concrete_url_or_origin(value):
                started_safety_issues.append({"項目": label, "値": value, "reason": "対象URL / originの具体値がない"})
            elif label == "副作用の許可範囲 / 最大回数" and not _has_concrete_side_effect_limit(value):
                started_safety_issues.append({"項目": label, "値": value, "reason": "許可する副作用と最大回数の具体値がない"})
            elif label in {"runner管理cleanup対象 / 方法", "run外cleanup対象 / 方法"} and not _has_concrete_cleanup_method(value):
                started_safety_issues.append({"項目": label, "値": value, "reason": "cleanupの対象または方法の具体値がない"})
            elif label == "runner管理cleanup対象 / 方法" and NO_CLEANUP_METHOD_RE.fullmatch(value):
                runner_owned_cleanup_targets = [
                    clean(server.get("server識別子", ""))
                    for server in webserver_rows
                    if _is_run_owned(server.get("今回run所有か", ""))
                    and _is_cleanup_target(server.get("cleanup対象か", ""))
                ]
                if _has_explicit_runner_cleanup_target(setup_value):
                    runner_owned_cleanup_targets.append(f"teardown:{_teardown_candidate(setup_value)}")
                if runner_owned_cleanup_targets:
                    started_safety_issues.append(
                        {
                            "項目": label,
                            "値": value,
                            "reason": "既知の今回run所有・cleanup対象webServerがあるためcleanup不要系の方法と矛盾する",
                            "servers": runner_owned_cleanup_targets,
                        }
                    )
    result.add(
        "E2E-EXEC-D026",
        not started_safety_issues,
        "runner開始済みなら実行開始前に確定が必要な安全情報を未確認のまま実行しないこと",
        evidence=started_safety_issues or None,
    )
    webserver_state = _webserver_state(setup_value)
    webserver_issues = []
    actual_webserver_ids = [clean(row.get("server識別子", "")) for row in webserver_rows if clean(row.get("server識別子", ""))]
    expected_webserver_ids = {
        clean(str(server_id))
        for server_id in expected.get("expected_webserver_ids", [])
        if clean(str(server_id))
    }
    if webserver_state == "configured" and not webserver_rows:
        webserver_issues.append("webServerごとのownership / cleanup表がない")
    if webserver_state == "unknown":
        if runner_started:
            webserver_issues.append("webServerが未確認 / 確認不能なのにrunnerを開始している")
        if webserver_rows:
            webserver_issues.append("webServer未確認時に架空または未確認のownership行を作成している")
    if webserver_state == "none" and webserver_rows:
        webserver_issues.append("webServerなしなのにownership行がある")
    if expected.get("expected_webserver_ids") is not None and set(actual_webserver_ids) != expected_webserver_ids:
        webserver_issues.append(
            {
                "reason": "実効webServer集合とownership表のserver集合が一致しない",
                "expected": sorted(expected_webserver_ids),
                "actual": sorted(actual_webserver_ids),
            }
        )
    if len(actual_webserver_ids) != len(set(actual_webserver_ids)):
        webserver_issues.append({"reason": "ownership表のserver識別子が重複している", "actual": actual_webserver_ids})
    expected_reuse = {
        clean(str(server_id)): bool(reuse)
        for server_id, reuse in expected.get("expected_webserver_reuse", {}).items()
    }
    for row in webserver_rows:
        missing_fields = [
            field
            for field in ("server識別子", "起動状態", "今回run所有か", "既存 / 再利用か", "cleanup対象か", "根拠")
            if not has_value(row.get(field, ""))
        ]
        if missing_fields:
            webserver_issues.append({"server": clean(row.get("server識別子", "")) or "<unknown>", "fields": missing_fields})
            continue
        owner = clean(row.get("今回run所有か", ""))
        existing = clean(row.get("既存 / 再利用か", ""))
        cleanup = clean(row.get("cleanup対象か", ""))
        startup = clean(row.get("起動状態", ""))
        if runner_value in NOT_STARTED_MARKERS and any(marker in f"{startup} {existing}" for marker in ("起動なし", "未開始", "対象なし")):
            continue
        existing_process = existing == "既存process再利用"
        new_process = existing == "新規起動"
        if not existing_process and not new_process:
            webserver_issues.append({"server": row.get("server識別子"), "reason": "既存 / 再利用かが新規または既存 / 再利用として閉じていない"})
        if existing_process and startup != WEBSERVER_STARTED_BEFORE_RUN:
            webserver_issues.append({"server": row.get("server識別子"), "reason": "既存 / 再利用processは実行前から存在である必要がある"})
        if existing_process and owner not in NON_OWNER_MARKERS:
            webserver_issues.append({"server": row.get("server識別子"), "reason": "既存 / 再利用processは明示的な今回run非所有である必要がある"})
        if existing_process and cleanup not in ACTUAL_REUSE_NON_CLEANUP_MARKERS:
            webserver_issues.append({"server": row.get("server識別子"), "reason": "既存 / 再利用processは明示的なcleanup対象外である必要がある"})
        if new_process:
            if startup != WEBSERVER_STARTED_BY_RUN:
                webserver_issues.append({"server": row.get("server識別子"), "reason": "新規serverは今回run起動である必要がある"})
            if not _is_run_owned(owner):
                webserver_issues.append({"server": row.get("server識別子"), "reason": "今回runが起動したprocessは今回run所有である必要がある"})
            if not _is_cleanup_target(cleanup):
                webserver_issues.append({"server": row.get("server識別子"), "reason": "今回runが起動したprocessはcleanup対象である必要がある"})
        if (existing_process or new_process) and _is_raw_webserver_config_only(row.get("根拠", "")):
            webserver_issues.append({"server": row.get("server識別子"), "reason": "actual process stateの根拠をraw configだけで記録している"})
        server_id = clean(row.get("server識別子", ""))
        if server_id in expected_reuse and expected_reuse[server_id] != existing_process:
            webserver_issues.append({"server": server_id, "reason": "setup / fixtureが示すreuse状態とownership表が一致しない"})
    result.add(
        "E2E-EXEC-D025",
        not webserver_issues,
        "webServerがある場合、各processの起動状態・ownership・再利用状態・cleanup対象を個別に記録すること",
        evidence=webserver_issues or None,
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
    resolved_by_ref: dict[str, list[dict[str, str]]] = {}
    for row in resolved_rows:
        resolved_by_logical.setdefault(clean(row.get("論理要求primary対象", "")), []).append(row)
        ref = clean(row.get("resolved primary TestCase参照", ""))
        if ref:
            resolved_by_ref.setdefault(ref, []).append(row)
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

    orphan_resolved = [
        {
            "resolved_ref": clean(row.get("resolved primary TestCase参照", "")),
            "logical": clean(row.get("論理要求primary対象", "")),
        }
        for row in resolved_rows
        if clean(row.get("論理要求primary対象", "")) not in set(logical_names)
    ]
    result.add(
        "E2E-EXEC-D032",
        not orphan_resolved,
        "各resolved primary TestCaseが既存logical primary対象へ逆参照できること",
        evidence=orphan_resolved or None,
    )

    start_state_issues = []
    resolved_issues = []
    for row in resolved_rows:
        ref = clean(row.get("resolved primary TestCase参照", ""))
        start_state = clean(row.get("実行開始", ""))
        result_or_reason = clean(row.get("結果 / 未実行理由", ""))
        expected_status = clean(row.get("expectedStatus", ""))
        outcome = clean(row.get("outcome", ""))
        started = start_state in STARTED_MARKERS
        not_started = start_state in RESOLVED_NOT_STARTED_MARKERS
        if not started and not not_started:
            start_state_issues.append({"ref": ref, "value": start_state, "reason": "開始済み / 未開始の既存markerで閉じていない"})
        resolved_identity_fields = ("resolved primary TestCase参照", "論理要求primary対象", "test file / title path", "project", "repeatEachIndex")
        missing_identity = [field for field in resolved_identity_fields if not has_value(row.get(field, ""))]
        if _as_nonnegative_int(row.get("repeatEachIndex", "")) is None:
            missing_identity.append("repeatEachIndex(非負整数)")
        if missing_identity:
            resolved_issues.append({"ref": ref, "field": "resolved primary identity", "fields": missing_identity})
        if started:
            if result_or_reason not in TEST_STATUSES:
                resolved_issues.append({"ref": ref, "field": "結果", "value": result_or_reason})
            if expected_status not in EXPECTED_STATUSES:
                resolved_issues.append({"ref": ref, "field": "expectedStatus", "value": expected_status})
            if outcome not in OUTCOMES:
                resolved_issues.append({"ref": ref, "field": "outcome", "value": outcome})
        elif not_started:
            if not result_or_reason:
                resolved_issues.append({"ref": ref, "reason": "未開始resolvedには未実行理由が必要"})
            elif _is_raw_test_status(result_or_reason):
                resolved_issues.append({"ref": ref, "field": "未実行理由", "value": result_or_reason, "reason": "Playwright TestResult.statusを未実行理由として使用している"})
            if expected_status or outcome:
                resolved_issues.append({"ref": ref, "reason": "未開始resolvedはPlaywrightのexpectedStatus / outcomeを持たない"})
    result.add(
        "E2E-EXEC-D030",
        not start_state_issues,
        "resolved primaryの実行開始を開始済み / 未開始の既存markerで分類すること",
        evidence=start_state_issues or None,
    )
    result.add(
        "E2E-EXEC-D009",
        not resolved_issues,
        "開始済みresolvedはTestResult.status・TestCase expectedStatus / outcomeを持ち、未開始resolvedは未実行理由だけを持つこと",
        evidence=resolved_issues or None,
    )

    attempts = nonempty_rows(attempt_table)
    attempt_issues = []
    for row in attempts:
        status = clean(row.get("status", ""))
        execution_class = clean(row.get("実行区分", ""))
        resolved_ref = clean(row.get("resolved primary TestCase参照", ""))
        attempt_no = _as_nonnegative_int(row.get("attempt番号", ""))
        retry_no = _as_nonnegative_int(row.get("retry番号", ""))
        if status not in TEST_STATUSES:
            attempt_issues.append({"field": "status", "value": status})
        if execution_class not in EXECUTION_CLASSES:
            attempt_issues.append({"field": "実行区分", "value": execution_class})
        if attempt_no is None or attempt_no < 1 or retry_no is None or not has_value(row.get("duration", "")):
            attempt_issues.append({"field": "attempt / retry", "value": [row.get("attempt番号"), row.get("retry番号")]})
        identity_fields = ("test file / title path", "project", "repeatEachIndex")
        dependency_or_teardown = execution_class in {"project dependencyとして付随実行されたtest", "project teardownとして付随実行されたtest", "dependency", "teardown"}
        missing_identity = [field for field in identity_fields if not has_value(row.get(field, ""))]
        if missing_identity:
            attempt_issues.append({"field": "dependency / teardown identity" if dependency_or_teardown else "primary identity", "fields": missing_identity, "resolved_ref": resolved_ref})
        if _as_nonnegative_int(row.get("repeatEachIndex", "")) is None:
            attempt_issues.append({"field": "repeatEachIndex", "value": row.get("repeatEachIndex", ""), "resolved_ref": resolved_ref})
        if dependency_or_teardown and resolved_ref:
            attempt_issues.append({"field": "resolved primary TestCase参照", "value": resolved_ref, "reason": "dependency / teardownはresolved primary参照を持たない"})
        if execution_class == "要求primary test" and not resolved_ref:
            attempt_issues.append({"field": "resolved primary TestCase参照", "reason": "primary attemptのresolved参照が空欄"})
    result.add(
        "E2E-EXEC-D010",
        not attempt_issues,
        "attemptはTestResult.status・retry・duration・errorと実行区分別識別情報を保持し、TestCase outcomeを重複保持しないこと",
        evidence=attempt_issues or None,
    )
    duplicate_testcase_fields = sorted({field for field in ("expectedStatus", "outcome") if attempt_table and field in attempt_table.headers})
    result.add(
        "E2E-EXEC-D035",
        not duplicate_testcase_fields,
        "attempt表へTestCase単位のexpectedStatus / outcomeを重複保持しないこと",
        evidence=duplicate_testcase_fields or None,
    )
    primary_attempt_rows = [row for row in attempts if clean(row.get("実行区分", "")) == "要求primary test"]
    primary_attempt_refs = {clean(row.get("resolved primary TestCase参照", "")) for row in primary_attempt_rows if clean(row.get("resolved primary TestCase参照", ""))}
    unresolved_attempt_refs = sorted(primary_attempt_refs - set(resolved_refs))
    started_refs = {
        clean(row.get("resolved primary TestCase参照", ""))
        for row in resolved_rows
        if clean(row.get("実行開始", "")) in STARTED_MARKERS
    }
    unstarted_refs = {
        clean(row.get("resolved primary TestCase参照", ""))
        for row in resolved_rows
        if clean(row.get("実行開始", "")) in RESOLVED_NOT_STARTED_MARKERS
    }
    missing_started_attempts = sorted(started_refs - primary_attempt_refs)
    unstarted_attempt_refs = sorted(primary_attempt_refs & unstarted_refs)
    result.add(
        "E2E-EXEC-D011",
        not unresolved_attempt_refs and not missing_started_attempts and not unstarted_attempt_refs,
        "要求primary attemptがstarted resolved primary TestCaseだけへ対応し、開始済みresolved対象にattemptが存在すること",
        evidence={"unknown_attempt_refs": unresolved_attempt_refs, "missing_started_attempts": missing_started_attempts, "unstarted_attempt_refs": unstarted_attempt_refs}
        if unresolved_attempt_refs or missing_started_attempts or unstarted_attempt_refs
        else None,
    )

    primary_identity_issues = []
    for row in primary_attempt_rows:
        resolved_ref = clean(row.get("resolved primary TestCase参照", ""))
        resolved_matches = resolved_by_ref.get(resolved_ref, [])
        if len(resolved_matches) != 1:
            continue
        resolved_row = resolved_matches[0]
        mismatches = {
            field: {
                "resolved": clean(resolved_row.get(field, "")),
                "attempt": clean(row.get(field, "")),
            }
            for field in ("test file / title path", "project", "repeatEachIndex")
            if clean(resolved_row.get(field, "")) != clean(row.get(field, ""))
        }
        if mismatches:
            primary_identity_issues.append({"resolved_ref": resolved_ref, "fields": mismatches})
    result.add(
        "E2E-EXEC-D036",
        not primary_identity_issues,
        "要求primary attemptのfile / title / project / repeatEachIndexが参照先resolved primary TestCaseと一致すること",
        evidence=primary_identity_issues or None,
    )

    primary_attempts_by_ref: dict[str, list[dict[str, str]]] = {}
    for row in primary_attempt_rows:
        primary_attempts_by_ref.setdefault(clean(row.get("resolved primary TestCase参照", "")), []).append(row)
    dependency_or_teardown_classes = {
        "project dependencyとして付随実行されたtest",
        "project teardownとして付随実行されたtest",
        "dependency",
        "teardown",
    }
    dependency_or_teardown_attempt_rows = [
        row for row in attempts if clean(row.get("実行区分", "")) in dependency_or_teardown_classes
    ]
    sequence_rows = primary_attempt_rows + dependency_or_teardown_attempt_rows
    duplicate_attempt_keys, attempt_order_issues = _attempt_sequence_issues(
        sequence_rows,
        lambda row: (
            "要求primary test",
            clean(row.get("resolved primary TestCase参照", "")),
        )
        if clean(row.get("実行区分", "")) == "要求primary test"
        else (
            clean(row.get("実行区分", "")),
            clean(row.get("test file / title path", "")),
            clean(row.get("project", "")),
            _as_nonnegative_int(row.get("repeatEachIndex", "")),
        ),
    )
    result.add(
        "E2E-EXEC-D033",
        not duplicate_attempt_keys and not attempt_order_issues,
        "primary / dependency / teardown attemptの番号・retry番号がTestCase単位で一意かつ初回から連番であること",
        evidence={"duplicates": duplicate_attempt_keys, "order": attempt_order_issues} if duplicate_attempt_keys or attempt_order_issues else None,
    )

    result_attempt_issues = []
    for row in resolved_rows:
        ref = clean(row.get("resolved primary TestCase参照", ""))
        if clean(row.get("実行開始", "")) not in STARTED_MARKERS:
            continue
        candidate_attempts = primary_attempts_by_ref.get(ref, [])
        if not candidate_attempts:
            continue
        last_attempt = max(
            candidate_attempts,
            key=lambda attempt: (_as_nonnegative_int(attempt.get("attempt番号", "")) or -1, _as_nonnegative_int(attempt.get("retry番号", "")) or -1),
        )
        resolved_status = clean(row.get("結果 / 未実行理由", ""))
        last_status = clean(last_attempt.get("status", ""))
        if resolved_status != last_status:
            result_attempt_issues.append({"resolved_ref": ref, "resolved_status": resolved_status, "last_attempt_status": last_status})
        expected_status = clean(row.get("expectedStatus", ""))
        outcome = clean(row.get("outcome", ""))
        if expected_status in EXPECTED_STATUSES and outcome in OUTCOMES:
            attempt_statuses = [clean(attempt.get("status", "")) for attempt in candidate_attempts]
            expected_outcome = _compute_expected_testcase_outcome(expected_status, attempt_statuses)
            if outcome != expected_outcome:
                result_attempt_issues.append(
                    {
                        "resolved_ref": ref,
                        "attempt_statuses": attempt_statuses,
                        "expectedStatus": expected_status,
                        "outcome": outcome,
                        "expected_outcome": expected_outcome,
                    }
                )
    result.add(
        "E2E-EXEC-D034",
        not result_attempt_issues,
        "resolved primaryの結果statusが最後のprimary attemptと一致し、TestCase.outcome()がPlaywright公式集計と整合すること",
        evidence=result_attempt_issues or None,
    )

    cleanup_rows = nonempty_rows(cleanup_table)
    invalid_cleanup = sorted({clean(row.get("状態", "")) for row in cleanup_rows if clean(row.get("状態", "")) not in CLEANUP_STATES})
    cleanup_contract_issues = []
    for row in cleanup_rows:
        missing_fields = [
            field
            for field in ("cleanup対象 / 実行主体", "状態", "結果 / 残存副作用", "確認元")
            if not has_value(row.get(field, ""))
        ]
        if _cleanup_subject(row.get("cleanup対象 / 実行主体", "")) is None:
            missing_fields.append("cleanup実行主体( runner管理 / run外処理 )")
        if missing_fields:
            cleanup_contract_issues.append({"fields": missing_fields})
    result.add("E2E-EXEC-D012", bool(cleanup_rows) and not invalid_cleanup and not cleanup_contract_issues, "cleanup状態と実行主体を区別し、結果・確認元を記録すること", evidence={"missing_cleanup_rows": not cleanup_rows, "invalid": invalid_cleanup, "contract": cleanup_contract_issues} if not cleanup_rows or invalid_cleanup or cleanup_contract_issues else None)
    cleanup_unconfirmed = any(clean(row.get("状態", "")) in {"失敗", "未確認", "一部失敗"} for row in cleanup_rows)
    result.add("E2E-EXEC-D013", execution_state in {"完了", "ブロック中", "要再確認"} and not (cleanup_unconfirmed and execution_state == "完了"), "cleanup失敗 / 未確認を安全な完了扱いにせず、実行成果物状態を明示すること", evidence={"cleanup": [row.get("状態") for row in cleanup_rows], "execution_state": execution_state} if execution_state not in {"完了", "ブロック中", "要再確認"} or (cleanup_unconfirmed and execution_state == "完了") else None)
    external_cleanup_rows = [
        row for row in cleanup_rows if _cleanup_subject(row.get("cleanup対象 / 実行主体", "")) == "external"
    ]
    external_cleanup_with_contract_gap = [
        {
            "cleanup": row.get("cleanup対象 / 実行主体", ""),
            "state": clean(row.get("状態", "")),
            "contract": condition_by_item.get("run外cleanup対象 / 方法", {}).get("値", ""),
        }
        for row in external_cleanup_rows
        if clean(row.get("状態", "")) in {"成功", "失敗", "未確認", "一部失敗", "意図的に残した状態"}
        and (
            not _has_concrete_cleanup_method(condition_by_item.get("run外cleanup対象 / 方法", {}).get("値", ""))
            or NO_CLEANUP_METHOD_RE.fullmatch(clean(condition_by_item.get("run外cleanup対象 / 方法", {}).get("値", "")))
        )
    ]
    result.add(
        "E2E-EXEC-D027",
        not external_cleanup_with_contract_gap,
        "run外cleanupの実績がある場合、run外準備の有無ではなく事前のrun外cleanup契約と対応すること",
        evidence=external_cleanup_with_contract_gap
        if external_cleanup_with_contract_gap
        else None,
    )

    external_cleanup_issues = []
    if _external_preparation_performed(condition_by_item):
        if not external_cleanup_rows:
            external_cleanup_issues.append("run外準備に対応するrun外cleanup行がない")
        elif any(
            clean(row.get("状態", "")) == "対象なし" and not _cleanup_target_none_has_evidence(row)
            for row in external_cleanup_rows
        ):
            external_cleanup_issues.append("run外cleanup対象なしの根拠がない")
    result.add(
        "E2E-EXEC-D028",
        not external_cleanup_issues,
        "run外準備を実施した場合、対応するrun外cleanup行を必須とし、対象なしなら不要の根拠を記録すること",
        evidence=external_cleanup_issues or None,
    )

    runner_owned_cleanup_issues = []
    runner_owned_servers = [
        clean(row.get("server識別子", ""))
        for row in webserver_rows
        if clean(row.get("既存 / 再利用か", "")) == "新規起動"
        and _is_run_owned(row.get("今回run所有か", ""))
        and _is_cleanup_target(row.get("cleanup対象か", ""))
    ]
    known_runner_cleanup_targets = list(runner_owned_servers)
    if runner_started and _has_explicit_runner_cleanup_target(setup_value):
        known_runner_cleanup_targets.append(f"teardown:{_teardown_candidate(setup_value)}")
    runner_cleanup_rows = [row for row in cleanup_rows if _cleanup_subject(row.get("cleanup対象 / 実行主体", "")) == "runner"]
    if known_runner_cleanup_targets:
        if not runner_cleanup_rows:
            runner_owned_cleanup_issues.append({"targets": known_runner_cleanup_targets, "reason": "runner管理cleanup行がない"})
        elif any(clean(row.get("状態", "")) == "対象なし" for row in runner_cleanup_rows):
            runner_owned_cleanup_issues.append({"targets": known_runner_cleanup_targets, "reason": "既知のrunner管理cleanup対象に対してcleanup結果が対象なし"})
    result.add(
        "E2E-EXEC-D029",
        not runner_owned_cleanup_issues,
        "既知のrunner管理cleanup対象（今回run所有webServerまたは明示teardown）がある場合、runner管理cleanup行を対応付け、対象なしにしないこと",
        evidence=runner_owned_cleanup_issues or None,
    )

    runner_not_started_issues = []
    if runner_value in NOT_STARTED_MARKERS:
        if run_status in FULL_RESULT_STATUSES:
            runner_not_started_issues.append({"field": "Playwright run全体status", "value": run_status})
        process_exit = clean(run_value_by_item.get("CLI process exit code", {}).get("値", ""))
        if re.fullmatch(r"-?\d+", process_exit):
            runner_not_started_issues.append({"field": "CLI process exit code", "value": process_exit})
        run_error = clean(run_value_by_item.get("run-level / global error", {}).get("値", ""))
        if run_error.lower() in {"none", "no error", "なし", "無"}:
            runner_not_started_issues.append({"field": "run-level / global error", "value": run_error})
        if not _is_explicit_unavailable(run_error, RUN_NOT_STARTED_ERROR_STATES):
            runner_not_started_issues.append({"field": "run-level / global error", "value": run_error, "reason": "runner未開始時はPlaywright由来の具体的errorを記録できない"})
        if resolved_rows:
            runner_not_started_issues.append({"field": "resolved primary TestCase", "count": len(resolved_rows)})
        if attempts:
            runner_not_started_issues.append({"field": "attempt", "count": len(attempts)})
        successful_cleanup = []
        ambiguous_cleanup = []
        for row in cleanup_rows:
            if clean(row.get("状態", "")) != "成功":
                continue
            subject = _cleanup_subject(row.get("cleanup対象 / 実行主体", ""))
            if subject == "runner":
                successful_cleanup.append(row.get("cleanup対象 / 実行主体", ""))
            elif subject is None:
                ambiguous_cleanup.append(row.get("cleanup対象 / 実行主体", ""))
        if successful_cleanup:
            runner_not_started_issues.append({"field": "runner管理cleanup", "value": successful_cleanup})
        if ambiguous_cleanup:
            runner_not_started_issues.append({"field": "cleanup実行主体不明", "value": ambiguous_cleanup})
        for row in webserver_rows:
            server = clean(row.get("server識別子", "")) or "<unknown>"
            startup = clean(row.get("起動状態", ""))
            owner = clean(row.get("今回run所有か", ""))
            cleanup = clean(row.get("cleanup対象か", ""))
            if any(marker in startup for marker in ("今回runが起動", "今回run起動", "起動済み")):
                runner_not_started_issues.append({"field": "webServer起動", "server": server, "value": startup})
            if _is_run_owned(owner):
                runner_not_started_issues.append({"field": "webServer ownership", "server": server, "value": owner})
            if _is_cleanup_target(cleanup):
                runner_not_started_issues.append({"field": "webServer cleanup", "server": server, "value": cleanup})
    result.add(
        "E2E-EXEC-D024",
        not runner_not_started_issues,
        "runner未開始時にPlaywright run由来のraw fact・結果・成功cleanupを保持しないこと",
        evidence=runner_not_started_issues or None,
    )

    if expected.get("tc_absent"):
        fabricated = sorted(set(re.findall(r"\bTC-\d{3}\b", text)))
        result.add("E2E-EXEC-D014", not fabricated, "TCなし経路でTC IDを創作しないこと", evidence=fabricated or None)
    if "expected_logical_primary_count" in expected:
        mismatch = len(logical_rows) != int(expected["expected_logical_primary_count"])
        result.add("E2E-EXEC-D015", not mismatch, "logical primary対象数がフィクスチャと一致すること", evidence={"expected": expected["expected_logical_primary_count"], "actual": len(logical_rows)} if mismatch else None)
    result.add(
        "E2E-EXEC-D023",
        bool(logical_rows),
        "execution対象として開始した成果物にはlogical primary対象を最低1件記録すること",
        evidence="logical primary対象なし" if not logical_rows else None,
    )
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
