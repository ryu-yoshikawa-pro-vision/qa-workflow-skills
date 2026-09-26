from __future__ import annotations

import re
from typing import Any

import yaml

from scripts.skills.evals.deterministic.markdown_parser import find_table, parse_tables
from scripts.skills.evals.deterministic.result import EvalResult


RESULT_STATES = {"PASS", "FAIL", "未実行", "判定不能"}
START_STATES = {"未開始", "開始済み"}
CLEANUP_STATES = {"成功", "失敗", "未確認", "対象なし", "意図的に残した状態", "一部失敗"}
EXECUTION_METHODS = {"Playwright MCP", "Playwright CLI", "独立した今回run用Playwright Libraryコード", "未実行"}
NONE = {"", "なし", "-", "—", "N/A", "n/a", "null"}
TC_CLEANUP_NONE = NONE | {"対象なし"}


def _value(row: dict[str, str], field: str) -> str:
    return (row.get(field) or "").strip().strip(chr(96))


def _table(tables, section: str, headers: tuple[str, ...]):
    return find_table(tables, section_contains=section, required_headers=headers)


def _rows(table) -> list[dict[str, str]]:
    return table.rows if table else []


def _nonempty(value: str) -> bool:
    return value.strip() not in NONE


def _integer(value: str) -> int | None:
    return int(value) if re.fullmatch(r"\d+", value.strip()) else None


def _yaml_fences(text: str) -> tuple[list[Any], list[str]]:
    lines = text.splitlines()
    documents: list[Any] = []
    errors: list[str] = []
    in_yaml = False
    buffer: list[str] = []
    fences = 0
    for line_number, line in enumerate(lines, 1):
        stripped = line.strip()
        if not in_yaml and stripped.lower().startswith(chr(96) * 3 + "yaml"):
            in_yaml = True
            buffer = []
            continue
        if in_yaml and stripped.startswith(chr(96) * 3):
            fences += 1
            try:
                documents.append(yaml.safe_load("\n".join(buffer)))
            except yaml.YAMLError as exc:
                errors.append(f"line {line_number}: {exc}")
            in_yaml = False
            buffer = []
            continue
        if in_yaml:
            buffer.append(line)
    if in_yaml:
        errors.append("YAML fenced block is not closed")
    if fences == 0:
        errors.append("no fenced YAML execution plans")
    return documents, errors


def validate(text: str, expected: dict[str, Any], eval_id: str) -> EvalResult:
    result = EvalResult("test-execution", eval_id)
    parse_errors: list[str] = []
    try:
        tables = parse_tables(text)
    except Exception as exc:
        tables = []
        parse_errors.append(str(exc))

    required = {
        "実行情報": ("項目", "値", "確認元"),
        "run固定条件": ("条件", "値", "確認元"),
        "TC参照対応": ("TC参照", "入力順", "前回TC参照"),
        "TC実行条件": ("TC参照", "開始状態", "確認結果"),
        "実行前条件": ("TC参照", "副作用scope", "確認結果"),
        "副作用上限・実行時cleanup": ("副作用scope", "1回の定義", "最大回数"),
        "手順・観測結果": ("TC参照", "手順 / 観測点 (step_ref)", "期待結果"),
        "TC実行結果": ("TC参照", "実行開始", "状態"),
        "未実行・判定不能": ("TC参照", "状態", "理由"),
        "TC事後状態・後処理": ("TC参照", "事後状態 / 後処理", "実施結果"),
        "実行時cleanup・残存状態": ("対象", "状態", "内容"),
        "集計": ("状態", "件数"),
    }
    required_tables = {section: _table(tables, section, headers) for section, headers in required.items()}
    missing = [section for section, table in required_tables.items() if table is None]
    report_present = "## 実行結果報告" in text
    result.add("TEX-D001", not parse_errors and not missing and report_present, "正規実行報告セクション・表が存在し、Markdown表が整形式であること", evidence={"parse_errors": parse_errors, "missing": missing, "report": report_present} if parse_errors or missing or not report_present else None)

    info = {_value(row, "項目"): _value(row, "値") for row in _rows(required_tables["実行情報"])}
    mappings = _rows(required_tables["TC参照対応"])
    conditions = _rows(required_tables["TC実行条件"])
    preconditions = _rows(required_tables["実行前条件"])
    results = _rows(required_tables["TC実行結果"])
    ids = [_value(row, "TC参照") for row in mappings]
    result_ids = [_value(row, "TC参照") for row in results]
    order_values = [_integer(_value(row, "入力順")) for row in mappings]
    local_issues = []
    if not ids or len(ids) != len(set(ids)):
        local_issues.append({"issue": "TC参照が空または重複"})
    if any(not re.fullmatch(r"input-\d{3}", value) for value in ids):
        local_issues.append({"refs": ids, "issue": "input-NNN形式ではない"})
    if any(value is None for value in order_values) or order_values != list(range(1, len(ids) + 1)):
        local_issues.append({"input_order": order_values, "issue": "入力順が連番でない"})
    expected_local_refs = [f"input-{index:03d}" for index in range(1, len(ids) + 1)]
    if ids != expected_local_refs:
        local_issues.append({"expected_local_refs": expected_local_refs, "actual_refs": ids})
    if result_ids != ids or len(result_ids) != len(set(result_ids)):
        local_issues.append({"snapshot_refs": ids, "result_refs": result_ids})
    result.add("TEX-D002", not local_issues, "snapshotのtest_case_refが一意な成果物ローカル参照であり、入力順・結果表と一致すること", evidence=local_issues or None)

    yaml_docs, yaml_errors = _yaml_fences(text)
    yaml_issues = []
    plans: dict[str, dict[str, Any]] = {}
    if yaml_errors:
        yaml_issues.extend(yaml_errors)
    for index, doc in enumerate(yaml_docs):
        if not isinstance(doc, dict):
            yaml_issues.append({"document": index, "issue": "YAML root is not a mapping"})
            continue
        ref = doc.get("test_case_ref")
        if not isinstance(ref, str) or not re.fullmatch(r"input-\d{3}", ref):
            yaml_issues.append({"document": index, "issue": "invalid test_case_ref", "value": ref})
            continue
        if ref in plans:
            yaml_issues.append({"document": index, "issue": "duplicate test_case_ref", "value": ref})
        plans[ref] = doc
        missing_fields = [field for field in ("source_test_case_id", "title", "scenario", "unresolved", "cleanup") if field not in doc]
        if missing_fields:
            yaml_issues.append({"ref": ref, "missing": missing_fields})
            continue
        scenario = doc.get("scenario")
        if not isinstance(scenario, dict) or not all(isinstance(scenario.get(field), list) for field in ("given", "when", "then")):
            yaml_issues.append({"ref": ref, "issue": "scenario.given/when/then must be arrays"})
            continue
        when_rows = scenario["when"]
        then_rows = scenario["then"]
        step_refs = [row.get("step_ref") for row in when_rows if isinstance(row, dict)]
        if not when_rows or len(step_refs) != len(when_rows) or any(not isinstance(step, str) or not step.strip() for step in step_refs) or len(step_refs) != len(set(step_refs)):
            yaml_issues.append({"ref": ref, "issue": "scenario.when step_ref must be nonempty and unique"})
        if not then_rows:
            yaml_issues.append({"ref": ref, "issue": "scenario.then is empty"})
        for row in then_rows:
            if not isinstance(row, dict) or row.get("after_step_ref") not in step_refs or not isinstance(row.get("expected"), str) or not row["expected"].strip() or not isinstance(row.get("observation"), list) or not row["observation"]:
                yaml_issues.append({"ref": ref, "issue": "then must map expected result and observation to a when step"})
        if not isinstance(doc.get("unresolved"), list) or not isinstance(doc.get("cleanup"), list):
            yaml_issues.append({"ref": ref, "issue": "unresolved and cleanup must be arrays"})
    if list(plans) != ids:
        yaml_issues.append({"mapping_refs": ids, "yaml_refs": list(plans), "issue": "snapshot YAML order differs from input order"})
    result.add("TEX-D003", not yaml_issues, "実行前YAMLをyaml.safe_loadでparseし、必須構造・多段step参照・TC集合を検証すること", evidence=yaml_issues or None)

    source_issues = []
    source_field = "元TC ID (source_test_case_id)"
    for row in mappings:
        ref = _value(row, "TC参照")
        raw_id = _value(row, source_field)
        plan = plans.get(ref)
        if plan is None:
            continue
        expected_id = None if raw_id in NONE | {"なし"} else raw_id
        if plan.get("source_test_case_id") != expected_id:
            source_issues.append({"ref": ref, "table_id": expected_id, "yaml_id": plan.get("source_test_case_id")})
        if plan.get("source_test_case_id") == ref:
            source_issues.append({"ref": ref, "issue": "source_test_case_id reused as test_case_ref"})
    result.add("TEX-D004", not source_issues, "source_test_case_idをnullまたは入力値のまま保持し、成果物ローカル参照へ再利用しないこと", evidence=source_issues or None)

    snapshot_issues = []
    input_identity = _value(info, "TC revision / content identity")
    snapshot_method = _value(info, "snapshot固定方法")
    identity_expected = expected.get("source_identity_present")
    if identity_expected is False or (identity_expected is None and not _nonempty(input_identity)):
        if snapshot_method != expected.get("expected_snapshot_method", "成果物内TC集合・実行前YAML"):
            snapshot_issues.append({"expected": "成果物内TC集合・実行前YAML", "actual": snapshot_method})
    elif identity_expected is True or _nonempty(input_identity):
        if snapshot_method != expected.get("expected_snapshot_method", "入力元identity"):
            snapshot_issues.append({"expected": "入力元identity", "actual": snapshot_method})
        if not _nonempty(input_identity):
            snapshot_issues.append({"issue": "input identity expected but absent"})
    result.add("TEX-D005", not snapshot_issues, "入力元identityがあれば記録し、なければ独自hashを要求せず成果物内snapshotを正本にすること", evidence=snapshot_issues or None)

    previous = _value(info, "前回実行成果物参照")
    previous_issues = []
    prior_map = {_value(row, "TC参照"): _value(row, "前回TC参照") for row in mappings}
    if not _nonempty(previous) or previous in {"なし", "初回"}:
        invalid_prior = [{"ref": ref, "previous_ref": prior} for ref, prior in prior_map.items() if _nonempty(prior) and prior not in {"なし", "初回"}]
        previous_issues.extend(invalid_prior)
    expected_previous = expected.get("expected_previous_artifact")
    if expected_previous and previous != expected_previous:
        previous_issues.append({"expected_previous_artifact": expected_previous, "actual": previous})
    if "expected_previous_refs" in expected:
        expected_previous_refs = expected["expected_previous_refs"]
        if not isinstance(expected_previous_refs, dict):
            previous_issues.append({"issue": "expected_previous_refs must be a mapping"})
        else:
            expected_ref_set = set(expected_previous_refs)
            if not expected_ref_set <= set(ids):
                previous_issues.append({"unknown_expected_refs": sorted(expected_ref_set - set(ids))})
            actual_previous_refs = {
                ref: value
                for ref, value in prior_map.items()
                if _nonempty(value) and value not in {"なし", "初回"}
            }
            if actual_previous_refs != expected_previous_refs:
                previous_issues.append(
                    {
                        "expected_previous_refs": expected_previous_refs,
                        "actual_previous_refs": actual_previous_refs,
                    }
                )
    result.add("TEX-D006", not previous_issues, "再実行時に前回成果物参照と前回TC参照の組で元TCを追跡すること", evidence=previous_issues or None)

    method = _value(info, "使用した実行手段")
    method_issues = []
    if method not in EXECUTION_METHODS:
        method_issues.append({"method": method})
    result.add("TEX-D007", not method_issues, "使用したbrowser実行手段が正規値で記録されること", evidence=method_issues or None)

    result_by_ref = {_value(row, "TC参照"): row for row in results}
    state_issues = []
    for ref, row in result_by_ref.items():
        status = _value(row, "状態")
        start = _value(row, "実行開始")
        if status not in RESULT_STATES:
            state_issues.append({"ref": ref, "status": status})
        if start not in START_STATES:
            state_issues.append({"ref": ref, "start": start})
        if (status == "未実行" and start != "未開始") or (status in {"PASS", "FAIL", "判定不能"} and start != "開始済み"):
            state_issues.append({"ref": ref, "status": status, "start": start})
        if status in {"PASS", "FAIL"} and any(not _nonempty(_value(row, field)) for field in ("期待結果", "実測結果", "判定根拠")):
            state_issues.append({"ref": ref, "issue": "PASS/FAIL evidence missing"})
        if status in {"未実行", "判定不能"}:
            reason = next((item for item in _rows(required_tables["未実行・判定不能"]) if _value(item, "TC参照") == ref), None)
            if reason is None or not _nonempty(_value(reason, "理由")):
                state_issues.append({"ref": ref, "issue": "unrun/indeterminate reason missing"})
        plan = plans.get(ref)
        if plan is not None and plan.get("unresolved"):
            if status != "未実行" or start != "未開始":
                state_issues.append({"ref": ref, "issue": "unresolved TC was started"})
    result.add("TEX-D008", not state_issues, "TC結果・開始境界・unresolved・理由が整合すること", evidence=state_issues or None)

    condition_refs = [_value(row, "TC参照") for row in conditions]
    condition_issues = []
    if condition_refs != ids or len(condition_refs) != len(set(condition_refs)):
        condition_issues.append({"mapping_refs": ids, "condition_refs": condition_refs})
    precondition_refs = [_value(row, "TC参照") for row in preconditions]
    if set(precondition_refs) != set(ids) or len(precondition_refs) != len(set(precondition_refs)):
        condition_issues.append({"mapping_refs": ids, "precondition_refs": precondition_refs})
    run_fixed_rows = _rows(required_tables["run固定条件"])
    run_fixed_items = [_value(row, "条件") for row in run_fixed_rows]
    required_run_fixed_items = {"対象環境", "許可origin", "version / build"}
    missing_run_fixed_items = sorted(required_run_fixed_items - set(run_fixed_items))
    if missing_run_fixed_items:
        condition_issues.append({"missing_run_fixed_conditions": missing_run_fixed_items})
    result.add("TEX-D009", not condition_issues, "run固定条件の安全項目とTC実行条件・実行前条件の参照整合を検証すること", evidence=condition_issues or None)

    procedure_rows = _rows(required_tables["手順・観測結果"])
    procedure_issues = []
    visual_rows = _rows(_table(tables, "視覚確認", ("TC参照", "手順 / 観測点", "画像で観測した事実")))
    for row in procedure_rows:
        ref = _value(row, "TC参照")
        if ref not in plans:
            procedure_issues.append({"ref": ref, "issue": "unknown TC"})
            continue
        observed_step = _value(row, "手順 / 観測点 (step_ref)")
        valid_steps = {step.get("step_ref") for step in plans[ref].get("scenario", {}).get("when", []) if isinstance(step, dict)}
        if observed_step not in valid_steps:
            procedure_issues.append({"ref": ref, "step": observed_step, "issue": "step_ref is not in YAML"})
    for row in visual_rows:
        ref = _value(row, "TC参照")
        if ref not in plans:
            procedure_issues.append({"visual_ref": ref, "issue": "unknown TC"})
            continue
        if _value(row, "手順 / 観測点") not in {_value(item, "手順 / 観測点 (step_ref)") for item in procedure_rows if _value(item, "TC参照") == ref}:
            procedure_issues.append({"visual_ref": ref, "step": _value(row, "手順 / 観測点"), "issue": "visual observation is not traceable"})
    procedure_by_ref: dict[str, list[dict[str, str]]] = {}
    for row in procedure_rows:
        ref = _value(row, "TC参照")
        procedure_by_ref.setdefault(ref, []).append(row)
        for field in ("観測方法", "期待結果", "実測結果"):
            if not _nonempty(_value(row, field)):
                procedure_issues.append({"ref": ref, "step": _value(row, "手順 / 観測点 (step_ref)"), "missing": field})
    for result_row in results:
        ref = _value(result_row, "TC参照")
        status = _value(result_row, "状態")
        steps = { _value(row, "手順 / 観測点 (step_ref)") for row in procedure_by_ref.get(ref, []) }
        plan = plans.get(ref, {})
        expected_steps = {
            item.get("after_step_ref")
            for item in plan.get("scenario", {}).get("then", [])
            if isinstance(item, dict) and isinstance(item.get("after_step_ref"), str)
        }
        if status == "未実行" and procedure_by_ref.get(ref):
            procedure_issues.append({"ref": ref, "issue": "未開始TCに操作・観測結果がある"})
        elif status in {"PASS", "FAIL", "判定不能"} and not procedure_by_ref.get(ref):
            procedure_issues.append({"ref": ref, "issue": "開始済みTCの操作・観測結果がない"})
        if status == "PASS" and not expected_steps <= steps:
            procedure_issues.append({"ref": ref, "missing_expected_steps": sorted(expected_steps - steps)})
    result.add("TEX-D010", not procedure_issues, "操作・観測と画像判断をTC・stepへ追跡できること", evidence=procedure_issues or None)

    side_rows = _rows(required_tables["副作用上限・実行時cleanup"])
    side_issues = []
    post_rows = _rows(required_tables["TC事後状態・後処理"])
    post_rows_by_ref: dict[str, list[dict[str, str]]] = {}
    for row in post_rows:
        post_rows_by_ref.setdefault(_value(row, "TC参照"), []).append(row)
    preconditions_by_ref = {_value(row, "TC参照"): row for row in preconditions}
    for ref, plan in plans.items():
        tc_cleanup = plan.get("cleanup")
        if not isinstance(tc_cleanup, list):
            continue
        precondition = preconditions_by_ref.get(ref)
        claimed_cleanup = _value(precondition, "TC事後状態 / 後処理") if precondition else ""
        recorded_post_rows = post_rows_by_ref.get(ref, [])
        if tc_cleanup:
            if claimed_cleanup in TC_CLEANUP_NONE:
                side_issues.append({"ref": ref, "issue": "YAML cleanupに対する実行前条件のTC事後処理記録がない"})
            if not any(
                _value(row, "事後状態 / 後処理") not in TC_CLEANUP_NONE
                for row in recorded_post_rows
            ):
                side_issues.append({"ref": ref, "issue": "YAML cleanupに対応するTC事後状態・後処理の記録がない"})
        else:
            if claimed_cleanup not in TC_CLEANUP_NONE:
                side_issues.append({"ref": ref, "issue": "空のYAML cleanupと実行前条件のTC事後処理記録が矛盾"})
            for row in recorded_post_rows:
                post_values = {
                    field: _value(row, field)
                    for field in ("事後状態 / 後処理", "実施結果", "残存状態")
                }
                if any(value not in TC_CLEANUP_NONE for value in post_values.values()):
                    side_issues.append(
                        {
                            "ref": ref,
                            "issue": "空のYAML cleanupとTC事後状態・後処理記録が矛盾",
                            "record": post_values,
                        }
                    )
    scope_values = [_value(row, "副作用scope") for row in side_rows]
    duplicate_scopes = sorted(scope for scope in set(scope_values) if scope and scope_values.count(scope) > 1)
    side_issues.extend({"scope": scope, "issue": "scopeの正本行が重複"} for scope in duplicate_scopes)
    defined_scopes = {scope for scope in scope_values if _nonempty(scope)}
    for row in preconditions:
        scope = _value(row, "副作用scope")
        if _nonempty(scope) and scope not in defined_scopes:
            side_issues.append(
                {
                    "ref": _value(row, "TC参照"),
                    "scope": scope,
                    "issue": "TCが参照する副作用scopeの正本行がない",
                }
            )
    for row in side_rows:
        scope = _value(row, "副作用scope")
        definition = _value(row, "1回の定義")
        maximum = _integer(_value(row, "最大回数"))
        names = ("準備回数", "TC操作回数", "TC事後処理回数", "実行時cleanup回数")
        counts = [_integer(_value(row, name)) for name in names]
        total = _integer(_value(row, "累計実施回数"))
        cleanup_state = _value(row, "cleanup結果")
        if not scope or not definition or maximum is None or any(count is None for count in counts) or total is None:
            side_issues.append({"scope": scope, "issue": "定義・上限・回数が不足"})
            continue
        if total != sum(counts) or total > maximum:
            side_issues.append({"scope": scope, "total": total, "counts": counts, "maximum": maximum})
        if cleanup_state not in CLEANUP_STATES:
            side_issues.append({"scope": scope, "cleanup_state": cleanup_state})
        if cleanup_state == "成功" and not any(token in _value(row, "残存状態") for token in ("なし", "元に戻", "復元", "解消")):
            side_issues.append({"scope": scope, "issue": "cleanup result conflicts with remaining state"})
    result.add("TEX-D011", not side_issues, "TC事後cleanupと実行時cleanupを分け、副作用scopeの定義・回数・cleanupを整合させること", evidence=side_issues or None)

    aggregate_table = required_tables["集計"]
    totals = {_value(row, "状態"): _integer(_value(row, "件数")) for row in _rows(aggregate_table)}
    aggregate_issues = []
    for status in RESULT_STATES:
        actual = sum(_value(row, "状態") == status for row in results)
        if totals.get(status) != actual:
            aggregate_issues.append({"status": status, "expected": actual, "actual": totals.get(status)})
    result.add("TEX-D012", not aggregate_issues, "集計がTC結果表と一致すること", evidence=aggregate_issues or None)

    secret_issues = [value for value in expected.get("forbidden_output_values", []) if isinstance(value, str) and value and value in text]
    result.add("TEX-D013", not secret_issues, "dummy secret等の既知実値が最終Markdownへ漏れていないこと", evidence=secret_issues or None)

    expected_refs = expected.get("expected_refs")
    expected_issues = []
    if expected_refs is not None and ids != expected_refs:
        expected_issues.append({"expected_refs": expected_refs, "actual_refs": ids})
    result.add("TEX-D014", not expected_issues, "fixtureで固定したsnapshot参照集合を保持すること", evidence=expected_issues or None)

    return result
