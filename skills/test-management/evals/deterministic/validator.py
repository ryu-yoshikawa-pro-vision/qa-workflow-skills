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
DIFFERENCE_ID = re.compile(r"^DIFF-\d{3}$")
ARTIFACT_LOCAL_REF = re.compile(
    r"^(?P<artifact_ref>.+)#(?P<local_id>QAR-\d{3}|ARCH-\d{3})@(?P<revision>[^@]+)$"
)
ARTIFACT_STATES = {"草案", "承認済み", "進行中", "要再確認", "blocked", "完了", "置換"}
ACQUISITION = {"取得済", "部分取得", "未取得", "取得不能", "0件確認済み", "不明"}
EXECUTION = {"実行済み", "実行中", "未実行", "取消", "実行失敗", "結果不明", "対象なし"}
OUTCOME = {"PASS", "FAIL", "判定不能", "未判定", "-"}
CURRENTNESS = {"current", "stale", "unknown"}
APPROVAL_STATES = {"承認済み", "未承認", "失効", "不要", "unknown"}
RISK_STATES = {"対応中", "blocked", "解決済み", "受容済み", "未判定", "unknown"}
ACTION_STATES = {"対応中", "blocked", "完了", "対応不要", "未判定", "unknown"}
FINAL_DISPOSITIONS = {"解決済み", "受容済み"}
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
        row.get("取得状態") == "取得済" for row in actual
    ),
    "部分取得数": lambda planned, actual: sum(
        row.get("取得状態") == "部分取得" for row in actual
    ),
    "未取得数": lambda planned, actual: sum(
        row.get("取得状態") == "未取得" for row in actual
    ),
    "取得不能数": lambda planned, actual: sum(
        row.get("取得状態") == "取得不能" for row in actual
    ),
    "0件確認済み数": lambda planned, actual: sum(
        row.get("取得状態") == "0件確認済み" for row in actual
    ),
    "取得不明数": lambda planned, actual: sum(
        row.get("取得状態") == "不明" for row in actual
    ),
    "実行済み数": lambda planned, actual: sum(
        row.get("実行状態") == "実行済み" for row in actual
    ),
    "実行中数": lambda planned, actual: sum(
        row.get("実行状態") == "実行中" for row in actual
    ),
    "未実行数": lambda planned, actual: sum(
        row.get("実行状態") == "未実行" for row in actual
    ),
    "取消数": lambda planned, actual: sum(
        row.get("実行状態") == "取消" for row in actual
    ),
    "実行失敗数": lambda planned, actual: sum(
        row.get("実行状態") == "実行失敗" for row in actual
    ),
    "結果不明数": lambda planned, actual: sum(
        row.get("実行状態") == "結果不明" for row in actual
    ),
    "PASS数": lambda planned, actual: sum(
        row.get("結果状態") == "PASS" for row in actual
    ),
    "FAIL数": lambda planned, actual: sum(
        row.get("結果状態") == "FAIL" for row in actual
    ),
    "判定不能数": lambda planned, actual: sum(
        row.get("結果状態") == "判定不能" for row in actual
    ),
    "未判定数": lambda planned, actual: sum(
        row.get("結果状態") == "未判定" for row in actual
    ),
    "対象なし数": lambda planned, actual: sum(
        row.get("実行状態") == "対象なし" for row in actual
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


def _scope_includes(scope_value: str, target_scope: str) -> bool:
    scopes = {clean(value) for value in re.split(r"[,、;]", clean(scope_value))}
    return clean(target_scope) in scopes


def _action_state(value: str) -> str:
    return clean(value).rsplit("/", 1)[-1].strip()


def _plan_input_status(source: dict[str, str] | None) -> list[str]:
    if source is None:
        return ["source ref/revision/scope/owner not acquired"]
    problems = []
    if source.get("currentness") != "current":
        problems.append(f"currentness={source.get('currentness', '')}")
    if source.get("取得状態") != "取得済":
        problems.append(f"取得状態={source.get('取得状態', '')}")
    if source.get("承認状態") != "承認済み" or not _is_present(
        source.get("承認証拠ref", "")
    ):
        problems.append("approval state/evidence is not current and approved")
    return problems


def validate(text: str, expected: dict, eval_id: str) -> EvalResult:
    result = EvalResult("test-management", eval_id)
    tables = parse_tables(text)
    metadata_table = _table(tables, "成果物メタデータ", ("項目", "値"))
    sources_table = _table(
        tables,
        "入力source",
        (
            "owner",
            "source_ref",
            "revision",
            "scope",
            "currentness",
            "取得状態",
            "承認状態",
            "承認証拠ref",
        ),
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
            "状態証拠ref",
            "承認主体・role",
        ),
    )
    action_table = _table(
        tables,
        "是正処置",
        (
            "action ID",
            "差異 / risk ref",
            "影響scope",
            "action",
            "owner",
            "期限 / 状態",
            "結果ref",
            "承認主体・role",
        ),
    )
    difference_table = _table(
        tables,
        "差異・未処理事項",
        (
            "差異ID",
            "影響scope",
            "差異",
            "根拠ref / revision",
            "対応",
            "owner",
            "状態",
            "状態証拠ref",
            "承認主体・role",
        ),
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
        ("差異・未処理事項", difference_table),
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

    plans = nonempty_rows(plan_table)
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

    planned = nonempty_rows(planned_table)
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

    actual_rows = nonempty_rows(readback_table)
    actual_ids = [clean(row.get("population ID", "")) for row in actual_rows]
    add_duplicate_assertion(result, "TMG-D012", actual_ids, "actual population ID")
    planned_by_id = {clean(row.get("population ID", "")): row for row in planned}
    invalid_actual_rows = []
    identity_mismatches = []
    status_candidates: dict[str, list[dict[str, str]]] = {}
    for row in actual_rows:
        population_id = clean(row.get("population ID", ""))
        plan = planned_by_id.get(population_id)
        acquisition = clean(row.get("取得状態", ""))
        execution = clean(row.get("実行状態", ""))
        outcome = clean(row.get("結果状態", ""))
        currentness = clean(row.get("currentness", ""))
        readback_ref = clean(row.get("source owner readback ref", ""))
        reason = clean(row.get("未取得 / 未実行理由", ""))
        state = {
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

        status_candidates.setdefault(population_id, []).append(state)

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

    ambiguous_actual = sorted(
        population_id
        for population_id, rows in status_candidates.items()
        if len(rows) != 1
    )
    status_by_id = {
        population_id: rows[0]
        for population_id, rows in status_candidates.items()
        if len(rows) == 1
    }
    missing_actual = sorted(set(population_ids) - set(actual_ids))
    unexpected_actual = sorted(set(actual_ids) - set(population_ids))
    unusable_actual = sorted(set(population_ids) & (set(actual_ids) - set(status_by_id)))
    if missing_actual or unexpected_actual or ambiguous_actual or unusable_actual:
        invalid_actual_rows.append(
            {
                "missing_readbacks": missing_actual,
                "unexpected_readbacks": unexpected_actual,
                "ambiguous_readbacks": ambiguous_actual,
                "unusable_readbacks": unusable_actual,
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

    monitoring = nonempty_rows(monitoring_table)
    monitoring_errors = []
    completion_errors = []
    risk_rows_for_closure = nonempty_rows(project_risk_table)
    action_rows_for_closure = nonempty_rows(action_table)
    difference_rows_for_closure = nonempty_rows(difference_table)
    criteria_rows = nonempty_rows(criteria_table)
    for snapshot in monitoring:
        snapshot_scope = clean(snapshot.get("scope", ""))
        if not _is_present(snapshot.get("snapshot_ref", "")):
            missing_snapshot_ref = {
                "reason": "monitoring snapshot requires a readable snapshot_ref",
                "scope": snapshot_scope,
            }
            monitoring_errors.append(missing_snapshot_ref)
            completion_errors.append(missing_snapshot_ref)
        group = [
            row
            for row in planned
            if clean(row.get("scope", "")) == snapshot_scope
            and clean(row.get("target build", ""))
            == clean(snapshot.get("target build", ""))
            and clean(row.get("environment", ""))
            == clean(snapshot.get("environment", ""))
        ]
        group_ids = [clean(row.get("population ID", "")) for row in group]
        group_actual = [status_by_id.get(population_id) for population_id in group_ids]
        missing_status = [
            population_id
            for population_id, state in zip(group_ids, group_actual, strict=True)
            if state is None
        ]
        values = {field: _integer(snapshot.get(field, "")) for field in MONITOR_COUNTS}
        invalid_counts = {field: value for field, value in values.items() if value is None}
        if invalid_counts:
            monitoring_errors.append(
                {
                    "snapshot_ref": snapshot.get("snapshot_ref"),
                    "reason": "counts must be nonnegative integers",
                    "values": invalid_counts,
                }
            )
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
        if missing_status:
            monitoring_errors.append(
                {
                    "snapshot_ref": snapshot.get("snapshot_ref"),
                    "reason": "cannot calculate monitoring state counts without every population readback",
                    "missing_readbacks": missing_status,
                }
            )
        if values.get("計画population数") is not None and values["計画population数"] != len(group):
            monitoring_errors.append(
                {
                    "snapshot_ref": snapshot.get("snapshot_ref"),
                    "reason": "planned population count does not match the identified group",
                    "expected": len(group),
                    "actual": values["計画population数"],
                }
            )
        if not missing_status and not invalid_counts:
            expected_counts = {
                field: count(group, group_actual)
                for field, count in MONITOR_COUNTS.items()
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
                population_id = clean(planned_row.get("population ID", ""))
                if actual_state is None:
                    completion_errors.append(
                        {
                            "snapshot_ref": snapshot.get("snapshot_ref"),
                            "population_id": population_id,
                            "reason": "population readback is absent or unusable; state is unknown",
                        }
                    )
                    continue
                acquisition = actual_state.get("取得状態", "")
                execution = actual_state.get("実行状態", "")
                outcome = actual_state.get("結果状態", "")
                if clean(planned_row.get("必須 / 任意", "")) == "必須":
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
                                "population_id": population_id,
                                "acquisition": acquisition,
                                "execution": execution,
                                "outcome": outcome,
                            }
                        )
            end_criteria = [
                row
                for row in criteria_rows
                if clean(row.get("種別", "")) == "終了"
                and clean(row.get("対象scope", "")) == snapshot_scope
            ]
            unresolved_criteria = [
                row
                for row in end_criteria
                if clean(row.get("判定状態", "")) not in {"満たす", "未達"}
                or not _is_present(row.get("evidence source / revision", ""))
            ]
            if not end_criteria or unresolved_criteria:
                completion_errors.append(
                    {
                        "snapshot_ref": snapshot.get("snapshot_ref"),
                        "reason": "all end criteria in this scope need a final evidence-backed decision; unmet is distinct from activity closure",
                        "unresolved": unresolved_criteria,
                    }
                )

            for risk in risk_rows_for_closure:
                risk_scope = risk.get("影響scope", "")
                if not _is_present(risk_scope):
                    completion_errors.append(
                        {
                            "snapshot_ref": snapshot.get("snapshot_ref"),
                            "project_risk_id": risk.get("project risk ID"),
                            "reason": "risk scope is unknown and cannot be excluded from this snapshot",
                        }
                    )
                    continue
                if not _scope_includes(risk_scope, snapshot_scope):
                    continue
                state = clean(risk.get("状態", ""))
                evidence = risk.get("状態証拠ref", "")
                authority = risk.get("承認主体・role", "")
                if (
                    state not in FINAL_DISPOSITIONS
                    or not _is_present(evidence)
                    or (state == "受容済み" and not _is_present(authority))
                ):
                    completion_errors.append(
                        {
                            "snapshot_ref": snapshot.get("snapshot_ref"),
                            "project_risk_id": risk.get("project risk ID"),
                            "scope": risk.get("影響scope"),
                            "state": state or "unknown",
                            "state_evidence_ref": evidence,
                            "approval_authority": authority,
                        }
                    )

            for action in action_rows_for_closure:
                action_scope = action.get("影響scope", "")
                if not _is_present(action_scope):
                    completion_errors.append(
                        {
                            "snapshot_ref": snapshot.get("snapshot_ref"),
                            "action_id": action.get("action ID"),
                            "reason": "action scope is unknown and cannot be excluded from this snapshot",
                        }
                    )
                    continue
                if not _scope_includes(action_scope, snapshot_scope):
                    continue
                state = _action_state(action.get("期限 / 状態", ""))
                evidence = action.get("結果ref", "")
                authority = action.get("承認主体・role", "")
                if (
                    state not in {"完了", "対応不要"}
                    or not _is_present(evidence)
                    or (state == "対応不要" and not _is_present(authority))
                ):
                    completion_errors.append(
                        {
                            "snapshot_ref": snapshot.get("snapshot_ref"),
                            "action_id": action.get("action ID"),
                            "scope": action.get("影響scope"),
                            "state": state or "unknown",
                            "result_ref": evidence,
                            "approval_authority": authority,
                        }
                    )

            scope_differences = [
                row
                for row in difference_rows_for_closure
                if not _is_present(row.get("影響scope", ""))
                or _scope_includes(row.get("影響scope", ""), snapshot_scope)
            ]
            expected_difference_ids = {
                clean(row.get("差異ID", "")) for row in scope_differences
            }
            summary = clean(snapshot.get("差異・未確定", ""))
            summary_ids = set(re.findall(r"DIFF-\d{3}", summary))
            if (scope_differences and summary_ids != expected_difference_ids) or (
                not scope_differences and summary not in {"-", "差異なし"}
            ):
                completion_errors.append(
                    {
                        "snapshot_ref": snapshot.get("snapshot_ref"),
                        "reason": "snapshot difference summary must identify every in-scope difference or state that none remain",
                        "expected_difference_ids": sorted(expected_difference_ids),
                        "actual_summary": summary,
                    }
                )
            for difference in scope_differences:
                if not _is_present(difference.get("影響scope", "")):
                    completion_errors.append(
                        {
                            "snapshot_ref": snapshot.get("snapshot_ref"),
                            "difference_id": difference.get("差異ID"),
                            "reason": "difference scope is unknown and cannot be excluded from this snapshot",
                        }
                    )
                    continue
                state = clean(difference.get("状態", ""))
                evidence = difference.get("状態証拠ref", "")
                authority = difference.get("承認主体・role", "")
                if (
                    state not in FINAL_DISPOSITIONS
                    or not _is_present(evidence)
                    or (state == "受容済み" and not _is_present(authority))
                ):
                    completion_errors.append(
                        {
                            "snapshot_ref": snapshot.get("snapshot_ref"),
                            "difference_id": difference.get("差異ID"),
                            "scope": difference.get("影響scope"),
                            "state": state or "unknown",
                            "state_evidence_ref": evidence,
                            "approval_authority": authority,
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
        if not required_groups:
            completion_errors.append(
                {"reason": "completed plan has no required population group"}
            )
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

    source_rows = nonempty_rows(sources_table)
    source_by_identity: dict[tuple[str, str, str, str], list[dict[str, str]]] = {}
    invalid_source_rows = []
    for source in source_rows:
        owner = clean(source.get("owner", ""))
        source_ref = clean(source.get("source_ref", ""))
        revision = clean(source.get("revision", ""))
        scope = clean(source.get("scope", ""))
        embedded_revision = source_ref.rsplit("@", 1)[1] if "@" in source_ref else ""
        if embedded_revision == revision:
            source_ref = source_ref.rsplit("@", 1)[0]
        approval_state = clean(source.get("承認状態", ""))
        approval_evidence = clean(source.get("承認証拠ref", ""))
        if (
            not owner
            or not source_ref
            or not revision
            or not scope
            or clean(source.get("currentness", "")) not in CURRENTNESS
            or clean(source.get("取得状態", "")) not in ACQUISITION
            or approval_state not in APPROVAL_STATES
            or (approval_state == "承認済み" and not _is_present(approval_evidence))
        ):
            invalid_source_rows.append(source)
        source_by_identity.setdefault((owner, source_ref, revision, scope), []).append(
            source
        )

    unresolved_plan_inputs = []
    for row in plans:
        for field, owner, local_id_prefix in (
            ("QA要求ref / revision", "test-requirements-analysis", "QAR"),
            ("architecture ref / revision", "test-architecture-design", "ARCH"),
        ):
            value = clean(row.get(field, ""))
            match = ARTIFACT_LOCAL_REF.fullmatch(value)
            if match is None or not match.group("local_id").startswith(
                f"{local_id_prefix}-"
            ):
                unresolved_plan_inputs.append(
                    {
                        "plan_id": row.get("計画ID"),
                        "field": field,
                        "value": value,
                        "reason": "reference must include artifact_ref#local_id@revision",
                    }
                )
                continue
            artifact_ref = match.group("artifact_ref")
            local_id = match.group("local_id")
            revision = match.group("revision")
            scope = clean(row.get("対象scope", ""))
            identity = (owner, artifact_ref, revision, scope)
            source_matches = source_by_identity.get(identity, [])
            known_key = f"{owner}|{artifact_ref}@{revision}|{scope}"
            known_local_ids = expected.get("known_local_ids", {}).get(known_key)
            if len(source_matches) != 1:
                unresolved_plan_inputs.append(
                    {
                        "plan_id": row.get("計画ID"),
                        "field": field,
                        "value": value,
                        "reason": "owner, artifact ref, revision, and scope must match one source row",
                    }
                )
            if not isinstance(known_local_ids, list) or local_id not in known_local_ids:
                unresolved_plan_inputs.append(
                    {
                        "plan_id": row.get("計画ID"),
                        "field": field,
                        "value": value,
                        "reason": "local ID existence is absent from the fixed artifact fixture",
                    }
                )
    result.add(
        "TMG-D019",
        not invalid_source_rows and not unresolved_plan_inputs,
        "計画のQA要求・architecture refがowner・artifact・local ID・revision・scopeと利用可能なfixtureに一致すること",
        evidence=(
            {"invalid_source_rows": invalid_source_rows, "unresolved_refs": unresolved_plan_inputs}
            if invalid_source_rows or unresolved_plan_inputs
            else None
        ),
    )
    stale_plan_inputs = []
    for plan in plans:
        if metadata.get("状態") not in {"承認済み", "進行中", "完了"}:
            continue
        for field, owner, local_id_prefix in (
            ("QA要求ref / revision", "test-requirements-analysis", "QAR"),
            ("architecture ref / revision", "test-architecture-design", "ARCH"),
        ):
            match = ARTIFACT_LOCAL_REF.fullmatch(clean(plan.get(field, "")))
            if match is None or not match.group("local_id").startswith(
                f"{local_id_prefix}-"
            ):
                stale_plan_inputs.append(
                    {"plan_id": plan.get("計画ID"), "field": field, "reason": "invalid ref"}
                )
                continue
            source_matches = source_by_identity.get(
                (
                    owner,
                    match.group("artifact_ref"),
                    match.group("revision"),
                    clean(plan.get("対象scope", "")),
                ),
                [],
            )
            problems = (
                _plan_input_status(source_matches[0])
                if len(source_matches) == 1
                else ["source identity is missing or ambiguous"]
            )
            if problems:
                stale_plan_inputs.append(
                    {
                        "plan_id": plan.get("計画ID"),
                        "field": field,
                        "value": plan.get(field),
                        "problems": problems,
                    }
                )
    result.add(
        "TMG-D020",
        not stale_plan_inputs,
        "対象計画のQA要求・architecture sourceがcurrent・取得済み・必要承認済みであること",
        evidence=stale_plan_inputs or None,
    )

    criteria = nonempty_rows(criteria_table)
    invalid_criteria = [
        row
        for row in criteria
        if clean(row.get("種別", "")) not in {"開始", "終了"}
        or not clean(row.get("基準", ""))
        or not clean(row.get("対象scope", ""))
        or not _is_present(row.get("evidence source / revision", ""))
        or clean(row.get("判定状態", ""))
        not in {"満たす", "未達", "未判定", "blocked", "未設定"}
    ]
    result.add(
        "TMG-D016",
        not invalid_criteria,
        "開始／終了基準にscope・evidence・明示状態があること",
        evidence=invalid_criteria or None,
    )

    risks = risk_rows_for_closure
    invalid_risks = [
        row
        for row in risk_rows_for_closure
        if not PROJECT_RISK_ID.fullmatch(clean(row.get("project risk ID", "")))
        or not clean(row.get("計画遂行上のrisk", ""))
        or not clean(row.get("影響scope", ""))
        or not _is_present(row.get("根拠ref / revision", ""))
        or not clean(row.get("owner", ""))
        or clean(row.get("状態", "")) not in RISK_STATES
        or (
            clean(row.get("状態", "")) == "解決済み"
            and not _is_present(row.get("状態証拠ref", ""))
        )
        or (
            clean(row.get("状態", "")) == "受容済み"
            and (
                not _is_present(row.get("状態証拠ref", ""))
                or not _is_present(row.get("承認主体・role", ""))
            )
        )
    ]
    result.add(
        "TMG-D017",
        not invalid_risks,
        "project riskの状態と、解決・正式受容に必要な根拠を記録すること",
        evidence=invalid_risks or None,
    )
    invalid_actions = [
        row
        for row in action_rows_for_closure
        if not ACTION_ID.fullmatch(clean(row.get("action ID", "")))
        or not clean(row.get("差異 / risk ref", ""))
        or not clean(row.get("影響scope", ""))
        or not clean(row.get("action", ""))
        or not clean(row.get("owner", ""))
        or not clean(row.get("期限 / 状態", ""))
        or _action_state(row.get("期限 / 状態", "")) not in ACTION_STATES
        or (
            _action_state(row.get("期限 / 状態", "")) == "完了"
            and not _is_present(row.get("結果ref", ""))
        )
        or (
            _action_state(row.get("期限 / 状態", "")) == "対応不要"
            and (
                not _is_present(row.get("結果ref", ""))
                or not _is_present(row.get("承認主体・role", ""))
            )
        )
    ]
    result.add(
        "TMG-D022",
        not invalid_actions,
        "是正処置のscope・状態・完了または正式判断の証拠を記録すること",
        evidence=invalid_actions or None,
    )

    differences = difference_rows_for_closure
    difference_ids = [clean(row.get("差異ID", "")) for row in differences]
    duplicate_differences = sorted(
        {value for value in difference_ids if difference_ids.count(value) > 1}
    )
    invalid_differences = [
        row
        for row in differences
        if not DIFFERENCE_ID.fullmatch(clean(row.get("差異ID", "")))
        or not clean(row.get("影響scope", ""))
        or not clean(row.get("差異", ""))
        or not _is_present(row.get("根拠ref / revision", ""))
        or not clean(row.get("対応", ""))
        or not clean(row.get("owner", ""))
        or clean(row.get("状態", "")) not in RISK_STATES
        or (
            clean(row.get("状態", "")) == "解決済み"
            and not _is_present(row.get("状態証拠ref", ""))
        )
        or (
            clean(row.get("状態", "")) == "受容済み"
            and (
                not _is_present(row.get("状態証拠ref", ""))
                or not _is_present(row.get("承認主体・role", ""))
            )
        )
    ]
    result.add(
        "TMG-D024",
        not duplicate_differences and not invalid_differences,
        "差異をscope・根拠・状態と処理証拠へ結び付けること",
        evidence=(
            {"duplicate_ids": duplicate_differences, "invalid_rows": invalid_differences}
            if duplicate_differences or invalid_differences
            else None
        ),
    )

    approval_rows = nonempty_rows(approval_table, "状態")
    approvals = [row for row in approval_rows if clean(row.get("状態", "")) == "承認済み"]
    approval_errors = [
        row
        for row in approvals
        if clean(row.get("artifact_ref", "")) != metadata.get("artifact_ref")
        or clean(row.get("revision", "")) != metadata.get("revision")
        or clean(row.get("対象scope", "")) != metadata.get("scope")
        or not clean(row.get("承認主体・role", ""))
        or not _is_present(row.get("承認証拠ref", ""))
        or metadata.get("状態") not in {"承認済み", "進行中", "完了"}
    ]
    invalid_approval_states = [
        row
        for row in approval_rows
        if clean(row.get("状態", "")) not in {"承認済み", "未承認", "失効", "unknown"}
    ]
    if metadata.get("状態") in {"承認済み", "進行中", "完了"} and not any(
        clean(row.get("artifact_ref", "")) == metadata.get("artifact_ref")
        and clean(row.get("revision", "")) == metadata.get("revision")
        and clean(row.get("対象scope", "")) == metadata.get("scope")
        and clean(row.get("承認主体・role", ""))
        and _is_present(row.get("承認証拠ref", ""))
        for row in approvals
    ):
        approval_errors.append(
            {
                "reason": "active plan requires approval for this scope, artifact ref, and revision",
                "artifact_ref": metadata.get("artifact_ref"),
                "revision": metadata.get("revision"),
                "scope": metadata.get("scope"),
            }
        )
    result.add(
        "TMG-D023",
        not approval_errors and not invalid_approval_states,
        "承認済み・進行中・完了の計画に同一scope・artifact ref・revisionの承認証拠があること",
        evidence=(
            {"approval_errors": approval_errors, "invalid_states": invalid_approval_states}
            if approval_errors or invalid_approval_states
            else None
        ),
    )
    return result
