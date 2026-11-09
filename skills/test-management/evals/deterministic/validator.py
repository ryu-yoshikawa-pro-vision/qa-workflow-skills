from __future__ import annotations

import re

from scripts.skills.evals.deterministic.common import (
    add_duplicate_assertion,
    clean,
    nonempty_rows,
)
from scripts.skills.evals.deterministic.markdown_parser import find_table, parse_tables
from scripts.skills.evals.deterministic.result import EvalResult

PLAN_ID = re.compile(r"^PLAN-\d{3}$")
POPULATION_ID = re.compile(r"^POP-\d{3}$")
PROJECT_RISK_ID = re.compile(r"^PROJ-RISK-\d{3}$")
ACTION_ID = re.compile(r"^CA-\d{3}$")
ARTIFACT_STATES = {"草案", "承認済み", "進行中", "要再確認", "blocked", "完了", "置換"}
ACQUISITION = {"取得済", "部分取得", "未取得", "取得不能", "0件確認済み", "不明"}
EXECUTION = {"実行済み", "実行中", "未実行", "取消", "実行失敗", "結果不明", "対象なし"}
OUTCOME = {"PASS", "FAIL", "判定不能", "未判定", "-"}
CURRENTNESS = {"current", "stale", "unknown"}
PLACEHOLDERS = {"", "-", "—", "unknown", "未取得"}
ACTUAL_IDENTITY_FIELDS = (
    "actual source owner",
    "actual source_ref",
    "actual revision",
    "actual scope",
    "acquired range",
    "actual execution unit",
    "actual build",
    "actual environment",
)
MONITOR_COUNTS = {
    "計画population数": lambda planned, actual: len(planned),
    "取得済数": lambda planned, actual: sum(
        row["取得状態"] == "取得済" for row in actual
    ),
    "部分取得数": lambda planned, actual: sum(
        row["取得状態"] == "部分取得" for row in actual
    ),
    "未取得数": lambda planned, actual: sum(
        row["取得状態"] == "未取得" for row in actual
    ),
    "取得不能数": lambda planned, actual: sum(
        row["取得状態"] == "取得不能" for row in actual
    ),
    "0件確認済み数": lambda planned, actual: sum(
        row["取得状態"] == "0件確認済み" for row in actual
    ),
    "取得不明数": lambda planned, actual: sum(
        row["取得状態"] == "不明" for row in actual
    ),
    "実行済み数": lambda planned, actual: sum(
        row["実行状態"] == "実行済み" for row in actual
    ),
    "実行中数": lambda planned, actual: sum(
        row["実行状態"] == "実行中" for row in actual
    ),
    "未実行数": lambda planned, actual: sum(
        row["実行状態"] == "未実行" for row in actual
    ),
    "取消数": lambda planned, actual: sum(row["実行状態"] == "取消" for row in actual),
    "実行失敗数": lambda planned, actual: sum(
        row["実行状態"] == "実行失敗" for row in actual
    ),
    "結果不明数": lambda planned, actual: sum(
        row["実行状態"] == "結果不明" for row in actual
    ),
    "PASS数": lambda planned, actual: sum(row["結果状態"] == "PASS" for row in actual),
    "FAIL数": lambda planned, actual: sum(row["結果状態"] == "FAIL" for row in actual),
    "判定不能数": lambda planned, actual: sum(
        row["結果状態"] == "判定不能" for row in actual
    ),
    "未判定数": lambda planned, actual: sum(
        row["結果状態"] == "未判定" for row in actual
    ),
    "対象なし数": lambda planned, actual: sum(
        row["実行状態"] == "対象なし" for row in actual
    ),
}


def _metadata(table) -> dict[str, str]:
    return {
        clean(row.get("項目", "")): clean(row.get("値", ""))
        for row in nonempty_rows(table, "項目")
    }


def _table(tables, section: str, headers: tuple[str, ...]):
    return find_table(tables, section_contains=section, required_headers=headers)


def _integer(value: str) -> int | None:
    try:
        parsed = int(clean(value))
    except (TypeError, ValueError):
        return None
    return parsed if parsed >= 0 else None


def _is_present(value: str) -> bool:
    return clean(value) not in PLACEHOLDERS


def validate(text: str, expected: dict, eval_id: str) -> EvalResult:
    result = EvalResult("test-management", eval_id)
    tables = parse_tables(text)
    metadata_table = _table(tables, "成果物メタデータ", ("項目", "値"))
    sources_table = _table(
        tables,
        "入力source",
        ("owner", "source_ref", "revision", "scope", "currentness", "取得状態"),
    )
    plan_table = _table(
        tables,
        "計画・資源",
        (
            "計画ID",
            "QA要求ref / revision",
            "architecture ref / revision",
            "対象scope",
            "level / type",
            "担当",
            "見積工数",
        ),
    )
    criteria_table = _table(
        tables,
        "開始・終了基準",
        ("種別", "基準", "対象scope", "evidence source / revision", "判定状態"),
    )
    planned_table = _table(
        tables,
        "予定source inventory",
        (
            "population ID",
            "source owner",
            "planned source_ref",
            "planned revision",
            "scope",
            "query / acquisition range",
            "execution unit",
            "target build",
            "environment",
            "必須 / 任意",
        ),
    )
    readback_table = _table(
        tables,
        "source owner readback",
        (
            "population ID",
            "actual source owner",
            "actual source_ref",
            "actual revision",
            "actual scope",
            "acquired range",
            "actual execution unit",
            "actual build",
            "actual environment",
            "currentness",
            "取得状態",
            "実行状態",
            "結果状態",
            "source owner readback ref",
            "未取得 / 未実行理由",
        ),
    )
    monitoring_table = _table(
        tables,
        "Monitoring snapshot",
        (
            "snapshot_ref",
            "plan_ref / revision",
            "scope",
            "target build",
            "environment",
            *MONITOR_COUNTS.keys(),
            "全体判定",
        ),
    )
    project_risk_table = _table(
        tables,
        "Project risk",
        (
            "project risk ID",
            "計画遂行上のrisk",
            "影響scope",
            "根拠ref / revision",
            "対応",
            "owner",
            "状態",
        ),
    )
    action_table = _table(
        tables,
        "是正処置",
        ("action ID", "差異 / risk ref", "action", "owner", "期限 / 状態", "結果ref"),
    )
    approval_table = _table(
        tables,
        "承認",
        (
            "対象scope",
            "artifact_ref",
            "revision",
            "承認主体・role",
            "承認証拠ref",
            "状態",
        ),
    )
    required_tables = (
        ("成果物メタデータ", metadata_table),
        ("入力source", sources_table),
        ("計画・資源", plan_table),
        ("開始・終了基準", criteria_table),
        ("予定source inventory", planned_table),
        ("source owner readback", readback_table),
        ("Monitoring snapshot", monitoring_table),
        ("Project risk", project_risk_table),
        ("是正処置", action_table),
        ("承認", approval_table),
    )
    missing_tables = [name for name, table in required_tables if table is None]
    result.add(
        "TMG-D001",
        not missing_tables,
        "計画母集団・readback ledger・monitoringの正規テーブルが存在すること",
        evidence=missing_tables or None,
    )

    metadata = _metadata(metadata_table)
    missing_metadata = [
        key
        for key in (
            "owner",
            "artifact_ref",
            "revision",
            "scope",
            "plan_version",
            "状態",
        )
        if not metadata.get(key)
    ]
    result.add(
        "TMG-D002",
        not missing_metadata and metadata.get("owner") == "test-management",
        "owner・artifact ref・revision・scope・version・状態が明示されること",
        evidence=missing_metadata or None,
    )
    result.add(
        "TMG-D003",
        metadata.get("状態", "") in ARTIFACT_STATES,
        "plan状態が許可値であること",
        evidence=metadata.get("状態")
        if metadata.get("状態") not in ARTIFACT_STATES
        else None,
    )

    plans = nonempty_rows(plan_table, "計画ID")
    plan_ids = [clean(row.get("計画ID", "")) for row in plans]
    add_duplicate_assertion(result, "TMG-D004", plan_ids, "計画ID")
    invalid_plan_ids = [value for value in plan_ids if not PLAN_ID.fullmatch(value)]
    result.add(
        "TMG-D005",
        not invalid_plan_ids,
        "plan IDがartifact-local PLAN-001形式であること",
        evidence=invalid_plan_ids or None,
    )
    invalid_plan_rows = [
        row
        for row in plans
        if not clean(row.get("対象scope", ""))
        or not clean(row.get("担当", ""))
        or not clean(row.get("見積工数", ""))
    ]
    result.add(
        "TMG-D006",
        not invalid_plan_rows,
        "計画scope・担当・見積が分かること",
        evidence=invalid_plan_rows or None,
    )

    planned = nonempty_rows(planned_table, "population ID")
    population_ids = [clean(row.get("population ID", "")) for row in planned]
    add_duplicate_assertion(result, "TMG-D007", population_ids, "planned population ID")
    invalid_population_ids = [
        value for value in population_ids if not POPULATION_ID.fullmatch(value)
    ]
    result.add(
        "TMG-D008",
        not invalid_population_ids,
        "planned population IDがartifact-local POP-001形式であること",
        evidence=invalid_population_ids or None,
    )
    required_population = set(expected.get("required_population_ids", []))
    missing_population = sorted(required_population - set(population_ids))
    result.add(
        "TMG-D009",
        not missing_population,
        "fixtureで必要なsource／実行母集団を列挙すること",
        evidence=missing_population or None,
    )
    invalid_planned_rows = [
        row
        for row in planned
        if any(
            not clean(row.get(field, ""))
            for field in (
                "source owner",
                "planned source_ref",
                "planned revision",
                "scope",
                "query / acquisition range",
                "execution unit",
                "target build",
                "environment",
                "必須 / 任意",
            )
        )
        or clean(row.get("必須 / 任意", "")) not in {"必須", "任意"}
    ]
    planned_keys = [
        tuple(
            clean(row.get(field, ""))
            for field in (
                "planned source_ref",
                "planned revision",
                "scope",
                "execution unit",
                "target build",
                "environment",
            )
        )
        for row in planned
    ]
    duplicate_planned_keys = sorted(
        {key for key in planned_keys if planned_keys.count(key) > 1}
    )
    result.add(
        "TMG-D010",
        not invalid_planned_rows,
        "予定source inventoryがowner・revision・scope・range・unit・build・environmentを保持すること",
        evidence=invalid_planned_rows or None,
    )
    result.add(
        "TMG-D011",
        not duplicate_planned_keys,
        "同一source／revision／scope／unit／build／environmentを二重計上しないこと",
        evidence=duplicate_planned_keys or None,
    )

    actual_rows = nonempty_rows(readback_table, "population ID")
    actual_ids = [clean(row.get("population ID", "")) for row in actual_rows]
    add_duplicate_assertion(result, "TMG-D012", actual_ids, "actual population ID")
    planned_by_id = {clean(row.get("population ID", "")): row for row in planned}
    invalid_actual_rows = []
    identity_mismatches = []
    status_by_id: dict[str, dict[str, str]] = {}
    for row in actual_rows:
        population_id = clean(row.get("population ID", ""))
        plan = planned_by_id.get(population_id)
        acquisition = clean(row.get("取得状態", ""))
        execution = clean(row.get("実行状態", ""))
        outcome = clean(row.get("結果状態", ""))
        currentness = clean(row.get("currentness", ""))
        readback_ref = clean(row.get("source owner readback ref", ""))
        reason = clean(row.get("未取得 / 未実行理由", ""))
        status_by_id[population_id] = {
            "取得状態": acquisition,
            "実行状態": execution,
            "結果状態": outcome,
            "currentness": currentness,
        }
        absent_state_fields = [
            field
            for field in ("取得状態", "実行状態", "結果状態", "currentness")
            if not clean(row.get(field, ""))
        ]
        if (
            plan is None
            or absent_state_fields
            or acquisition not in ACQUISITION
            or execution not in EXECUTION
            or outcome not in OUTCOME
            or currentness not in CURRENTNESS
        ):
            invalid_actual_rows.append(
                {
                    "population_id": population_id,
                    "missing_state_fields": absent_state_fields,
                    "acquisition": acquisition,
                    "execution": execution,
                    "outcome": outcome,
                    "currentness": currentness,
                }
            )
            continue

        identity_values = {
            field: clean(row.get(field, "")) for field in ACTUAL_IDENTITY_FIELDS
        }
        has_actual_identity = any(
            _is_present(value) for value in identity_values.values()
        )
        has_readback = _is_present(readback_ref)
        if acquisition in {"取得済", "部分取得", "0件確認済み"}:
            absent_identity = [
                field
                for field, value in identity_values.items()
                if not _is_present(value)
            ]
            if (
                absent_identity
                or not has_readback
                or currentness != "current"
                or clean(row.get("actual source owner", ""))
                != clean(plan.get("source owner", ""))
            ):
                invalid_actual_rows.append(
                    {
                        "population_id": population_id,
                        "reason": "acquired source requires matching owner identity and readback",
                        "missing_identity": absent_identity,
                        "readback_ref": readback_ref,
                        "currentness": currentness,
                    }
                )
            else:
                identity_fields = {
                    "actual source_ref": "planned source_ref",
                    "actual revision": "planned revision",
                    "actual scope": "scope",
                    "actual execution unit": "execution unit",
                    "actual build": "target build",
                    "actual environment": "environment",
                }
                mismatches = {
                    actual_field: {
                        "planned": clean(plan.get(planned_field, "")),
                        "actual": clean(row.get(actual_field, "")),
                    }
                    for actual_field, planned_field in identity_fields.items()
                    if clean(row.get(actual_field, ""))
                    != clean(plan.get(planned_field, ""))
                }
                if mismatches:
                    identity_mismatches.append(
                        {"population_id": population_id, "mismatches": mismatches}
                    )
                if acquisition in {"取得済", "0件確認済み"} and clean(
                    row.get("acquired range", "")
                ) != clean(plan.get("query / acquisition range", "")):
                    identity_mismatches.append(
                        {
                            "population_id": population_id,
                            "planned_range": clean(
                                plan.get("query / acquisition range", "")
                            ),
                            "actual_range": clean(row.get("acquired range", "")),
                        }
                    )
        else:
            if (
                has_actual_identity
                or has_readback
                or currentness != "unknown"
                or reason in PLACEHOLDERS
            ):
                invalid_actual_rows.append(
                    {
                        "population_id": population_id,
                        "reason": "unavailable source must not invent a readback identity",
                        "actual_identity": identity_values,
                        "readback_ref": readback_ref,
                        "currentness": currentness,
                    }
                )

        if (
            execution in {"実行中", "未実行", "取消", "実行失敗", "結果不明"}
            and reason in PLACEHOLDERS
        ):
            invalid_actual_rows.append(
                {
                    "population_id": population_id,
                    "reason": "execution state requires explanation",
                }
            )
        if (
            acquisition in {"部分取得", "未取得", "取得不能", "不明"}
            and reason in PLACEHOLDERS
        ):
            invalid_actual_rows.append(
                {
                    "population_id": population_id,
                    "reason": "incomplete acquisition requires explanation",
                }
            )
        if execution == "実行済み" and outcome not in {"PASS", "FAIL", "判定不能"}:
            invalid_actual_rows.append(
                {
                    "population_id": population_id,
                    "reason": "completed run has no result state",
                }
            )
        if execution == "実行済み" and acquisition not in {"取得済", "部分取得"}:
            invalid_actual_rows.append(
                {
                    "population_id": population_id,
                    "reason": "completed run lacks acquired source",
                }
            )
        if execution == "実行失敗" and (
            outcome != "判定不能"
            or acquisition not in {"取得済", "部分取得"}
            or not has_readback
        ):
            invalid_actual_rows.append(
                {
                    "population_id": population_id,
                    "reason": "execution failure is distinct from test FAIL and requires readback",
                }
            )
        if execution in {"未実行", "実行中", "取消", "対象なし"} and outcome not in {
            "未判定",
            "-",
        }:
            invalid_actual_rows.append(
                {
                    "population_id": population_id,
                    "reason": "non-completed execution cannot have a test result",
                    "execution": execution,
                    "outcome": outcome,
                }
            )
        if execution == "結果不明" and outcome not in {"判定不能", "未判定"}:
            invalid_actual_rows.append(
                {
                    "population_id": population_id,
                    "reason": "unknown execution result is misclassified",
                }
            )
        if execution == "対象なし" and acquisition != "0件確認済み":
            invalid_actual_rows.append(
                {
                    "population_id": population_id,
                    "reason": "no-target execution requires confirmed zero",
                }
            )
        if acquisition == "0件確認済み" and (execution != "対象なし" or outcome != "-"):
            invalid_actual_rows.append(
                {
                    "population_id": population_id,
                    "reason": "confirmed zero is not an execution result",
                }
            )

    missing_actual = sorted(set(population_ids) - set(actual_ids))
    unexpected_actual = sorted(set(actual_ids) - set(population_ids))
    if missing_actual or unexpected_actual:
        invalid_actual_rows.append(
            {
                "missing_readbacks": missing_actual,
                "unexpected_readbacks": unexpected_actual,
            }
        )
    result.add(
        "TMG-D013",
        not invalid_actual_rows,
        "取得状態・readback・実行失敗・未実行・取消・0件と結果状態を混同しないこと",
        evidence=invalid_actual_rows or None,
    )
    expected_acquisition = expected.get("expected_acquisition", {})
    acquisition_mismatches = [
        {
            "id": population_id,
            "expected": expected_acquisition[population_id],
            "actual": status_by_id.get(population_id, {}).get("取得状態"),
        }
        for population_id in population_ids
        if population_id in expected_acquisition
        and status_by_id.get(population_id, {}).get("取得状態")
        != expected_acquisition[population_id]
    ]
    result.add(
        "TMG-D014",
        not acquisition_mismatches,
        "source取得状態をfixtureどおり区別すること",
        evidence=acquisition_mismatches or None,
    )
    result.add(
        "TMG-D021",
        not identity_mismatches,
        "source owner readbackのrevision・scope・range・unit・buildが予定値と一致すること",
        evidence=identity_mismatches or None,
    )

    monitoring = nonempty_rows(monitoring_table, "snapshot_ref")
    monitoring_errors = []
    completion_errors = []
    for snapshot in monitoring:
        group = [
            row
            for row in planned
            if clean(row.get("scope", "")) == clean(snapshot.get("scope", ""))
            and clean(row.get("target build", ""))
            == clean(snapshot.get("target build", ""))
            and clean(row.get("environment", ""))
            == clean(snapshot.get("environment", ""))
        ]
        group_actual = [
            status_by_id.get(clean(row.get("population ID", "")), {}) for row in group
        ]
        values = {field: _integer(snapshot.get(field, "")) for field in MONITOR_COUNTS}
        if any(value is None for value in values.values()):
            monitoring_errors.append(
                {
                    "snapshot_ref": snapshot.get("snapshot_ref"),
                    "reason": "counts must be nonnegative integers",
                    "values": values,
                }
            )
            continue
        plan_ref = clean(snapshot.get("plan_ref / revision", ""))
        expected_plan_ref = (
            f"{metadata.get('artifact_ref', '')}@{metadata.get('revision', '')}"
        )
        if plan_ref != expected_plan_ref:
            monitoring_errors.append(
                {
                    "snapshot_ref": snapshot.get("snapshot_ref"),
                    "expected_plan_ref": expected_plan_ref,
                    "actual_plan_ref": plan_ref,
                }
            )
        if not group:
            monitoring_errors.append(
                {
                    "snapshot_ref": snapshot.get("snapshot_ref"),
                    "reason": "snapshot group does not identify planned population",
                }
            )
        expected_counts = {
            field: count(group, group_actual) for field, count in MONITOR_COUNTS.items()
        }
        mismatched_counts = {
            field: {"expected": count, "actual": values[field]}
            for field, count in expected_counts.items()
            if values[field] != count
        }
        if mismatched_counts:
            monitoring_errors.append(
                {
                    "snapshot_ref": snapshot.get("snapshot_ref"),
                    "reason": "monitoring counts do not match the plan/build/environment group",
                    "counts": mismatched_counts,
                }
            )

        if clean(snapshot.get("全体判定", "")) == "完了":
            for planned_row, actual_state in zip(group, group_actual, strict=True):
                if clean(planned_row.get("必須 / 任意", "")) != "必須":
                    continue
                acquisition = actual_state.get("取得状態", "")
                execution = actual_state.get("実行状態", "")
                outcome = actual_state.get("結果状態", "")
                valid_zero = (
                    acquisition == "0件確認済み"
                    and execution == "対象なし"
                    and outcome == "-"
                )
                valid_run = (
                    acquisition == "取得済"
                    and execution == "実行済み"
                    and outcome in {"PASS", "FAIL"}
                )
                if not (valid_zero or valid_run):
                    completion_errors.append(
                        {
                            "snapshot_ref": snapshot.get("snapshot_ref"),
                            "population_id": planned_row.get("population ID"),
                            "acquisition": acquisition,
                            "execution": execution,
                            "outcome": outcome,
                        }
                    )
            end_criteria = [
                row
                for row in nonempty_rows(criteria_table, "種別")
                if clean(row.get("種別", "")) == "終了"
                and clean(row.get("対象scope", "")) == clean(snapshot.get("scope", ""))
            ]
            unresolved_criteria = [
                row
                for row in end_criteria
                if clean(row.get("判定状態", "")) not in {"満たす", "未達"}
            ]
            if not end_criteria or unresolved_criteria:
                completion_errors.append(
                    {
                        "snapshot_ref": snapshot.get("snapshot_ref"),
                        "reason": "all end criteria in this scope must have a final evidence-backed decision",
                        "unresolved": unresolved_criteria,
                    }
                )

    if metadata.get("状態") == "完了":
        required_groups = {
            (
                clean(row.get("scope", "")),
                clean(row.get("target build", "")),
                clean(row.get("environment", "")),
            )
            for row in planned
            if clean(row.get("必須 / 任意", "")) == "必須"
        }
        completed_groups = {
            (
                clean(snapshot.get("scope", "")),
                clean(snapshot.get("target build", "")),
                clean(snapshot.get("environment", "")),
            )
            for snapshot in monitoring
            if clean(snapshot.get("全体判定", "")) == "完了"
        }
        for group in sorted(required_groups - completed_groups):
            completion_errors.append(
                {
                    "reason": "completed plan has no completed monitoring snapshot for a required group",
                    "scope_build_environment": group,
                }
            )

    result.add(
        "TMG-D015",
        not monitoring_errors,
        "計画revision・scope・build・environment単位のmonitoring件数が母集団に一致すること",
        evidence=monitoring_errors or None,
    )
    result.add(
        "TMG-D018",
        not completion_errors,
        "必要source／実行結果／終了基準が欠落した計画・snapshotを完了扱いしないこと",
        evidence=completion_errors or None,
    )

    source_identities = {
        (
            clean(row.get("source_ref", "")),
            clean(row.get("revision", "")),
            clean(row.get("scope", "")),
        )
        for row in nonempty_rows(sources_table, "source_ref")
    }
    unresolved_plan_inputs = []
    for row in plans:
        for field in ("QA要求ref / revision", "architecture ref / revision"):
            value = clean(row.get(field, ""))
            if "@" not in value:
                unresolved_plan_inputs.append(
                    {"plan_id": row.get("計画ID"), "field": field, "value": value}
                )
                continue
            source_ref, revision = value.rsplit("@", 1)
            source_ref = source_ref.split("#", 1)[0]
            identity = (source_ref, revision, clean(row.get("対象scope", "")))
            if identity not in source_identities:
                unresolved_plan_inputs.append(
                    {"plan_id": row.get("計画ID"), "field": field, "value": value}
                )
    result.add(
        "TMG-D019",
        not unresolved_plan_inputs,
        "計画のQA要求・architecture refとrevisionが入力source一覧に一致すること",
        evidence=unresolved_plan_inputs or None,
    )
    stale_plan_inputs = [
        row
        for row in nonempty_rows(sources_table, "source_ref")
        if clean(row.get("currentness", "")) != "current"
        or clean(row.get("取得状態", "")) not in {"取得済", "0件確認済み"}
    ]
    result.add(
        "TMG-D020",
        not stale_plan_inputs
        or metadata.get("状態") not in {"承認済み", "進行中", "完了"},
        "stale・未取得の入力が残る計画を承認済み・進行中・完了扱いしないこと",
        evidence=stale_plan_inputs or None,
    )

    criteria = nonempty_rows(criteria_table, "種別")
    invalid_criteria = [
        row
        for row in criteria
        if not clean(row.get("基準", ""))
        or not clean(row.get("対象scope", ""))
        or not clean(row.get("evidence source / revision", ""))
        or clean(row.get("判定状態", ""))
        not in {"満たす", "未達", "未判定", "blocked", "未設定"}
    ]
    result.add(
        "TMG-D016",
        not invalid_criteria,
        "開始／終了基準にscope・evidence・明示状態があること",
        evidence=invalid_criteria or None,
    )

    risks = nonempty_rows(project_risk_table, "project risk ID")
    invalid_risks = [
        row
        for row in risks
        if not PROJECT_RISK_ID.fullmatch(clean(row.get("project risk ID", "")))
        or not clean(row.get("計画遂行上のrisk", ""))
        or not clean(row.get("影響scope", ""))
        or not clean(row.get("根拠ref / revision", ""))
        or not clean(row.get("owner", ""))
        or not clean(row.get("状態", ""))
    ]
    result.add(
        "TMG-D017",
        not invalid_risks,
        "project riskをProduct Riskと別のartifact-local ID・根拠で管理すること",
        evidence=invalid_risks or None,
    )
    actions = nonempty_rows(action_table, "action ID")
    invalid_actions = [
        row
        for row in actions
        if not ACTION_ID.fullmatch(clean(row.get("action ID", "")))
        or not clean(row.get("差異 / risk ref", ""))
        or not clean(row.get("action", ""))
        or not clean(row.get("owner", ""))
        or not clean(row.get("期限 / 状態", ""))
    ]
    result.add(
        "TMG-D022",
        not invalid_actions,
        "是正処置が根拠・担当・期限または未設定状態を持つこと",
        evidence=invalid_actions or None,
    )

    approvals = [
        row
        for row in nonempty_rows(approval_table, "状態")
        if clean(row.get("状態", "")) == "承認済み"
    ]
    approval_errors = [
        row
        for row in approvals
        if clean(row.get("artifact_ref", "")) != metadata.get("artifact_ref")
        or clean(row.get("revision", "")) != metadata.get("revision")
        or clean(row.get("対象scope", "")) != metadata.get("scope")
        or not clean(row.get("承認主体・role", ""))
        or not clean(row.get("承認証拠ref", ""))
    ]
    if metadata.get("状態") in {"承認済み", "完了"} and not approvals:
        approval_errors.append(
            {"reason": "approved plan without matching approval evidence"}
        )
    result.add(
        "TMG-D023",
        not approval_errors,
        "承認済み計画が同一scope・artifact ref・revisionへ結び付くこと",
        evidence=approval_errors or None,
    )
    return result
