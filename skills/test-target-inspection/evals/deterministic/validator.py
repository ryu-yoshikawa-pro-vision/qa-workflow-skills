from __future__ import annotations

import json
import re
from typing import Any

from scripts.skills.evals.deterministic.markdown_parser import find_table, parse_tables
from scripts.skills.evals.deterministic.result import EvalResult


CONFIRM_STATES = {"確認済み", "未確認", "確認不能"}
UPDATE_STATES = {"変更なし", "更新", "追加", "削除確認"}
CLEANUP_STATES = {"成功", "失敗", "未確認", "対象なし", "意図的に残した状態", "一部失敗"}
SAVE_STATES = {"保存済み", "保存中止", "保存失敗"}
NONE = {"", "なし", "-", "—", "N/A", "n/a", "対象なし"}


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


def _freshness_key(section: str, row: dict[str, str]) -> str:
    fields = {
        "画面 / 領域": ("対象キー",),
        "UI要素": ("要素キー",),
        "状態": ("状態キー",),
        "操作・ふるまい": ("対象キー", "要素キー", "開始状態", "操作"),
        "視覚情報": ("対象キー", "要素キー / 状態キー", "確認観点"),
        "データ・権限依存": ("対象キー", "要素キー / 状態キー", "条件"),
    }
    return json.dumps((section, *(_value(row, field) for field in fields[section])), ensure_ascii=False)


def validate(text: str, expected: dict[str, Any], eval_id: str) -> EvalResult:
    result = EvalResult("test-target-inspection", eval_id)
    try:
        tables = parse_tables(text)
    except Exception as exc:
        result.add("TTI-D001", False, "出力Markdownの表構造が正しいこと", evidence=str(exc))
        tables = []

    required = {
        "確認情報": ("項目", "値", "確認元"),
        "画面 / 領域": ("対象キー", "確認状態"),
        "UI要素": ("要素キー", "対象キー", "確認状態"),
        "状態": ("状態キー", "対象キー", "確認状態"),
        "操作・ふるまい": ("対象キー", "要素キー", "確認状態"),
        "未確認 / 確認不能": ("対象", "状態", "理由"),
    }
    required_tables = {section: _table(tables, section, headers) for section, headers in required.items()}
    missing = [section for section, table in required_tables.items() if table is None]
    required_confirm_items = {
        "対象",
        "対象URL / origin",
        "version / build",
        "確認日時",
        "role / 権限",
        "viewport",
        "locale",
        "feature flag",
        "テストデータ条件",
        "既存成果物参照",
        "更新元revision / content identity",
        "永続保存要求",
    }
    confirm_rows = _rows(required_tables["確認情報"])
    confirm_items = {_value(row, "項目") for row in confirm_rows}
    missing_confirm_items = sorted(required_confirm_items - confirm_items)
    result.add(
        "TTI-D001",
        not missing and not missing_confirm_items,
        "正規の必須セクション表と確認情報項目が存在すること",
        evidence={"missing_tables": missing, "missing_confirm_items": missing_confirm_items}
        if missing or missing_confirm_items
        else None,
    )

    confirm = {_value(row, "項目"): _value(row, "値") for row in confirm_rows}
    screen = _rows(required_tables["画面 / 領域"])
    elements = _rows(required_tables["UI要素"])
    states = _rows(required_tables["状態"])
    behaviors = _rows(required_tables["操作・ふるまい"])
    visual = _rows(find_table(tables, section_contains="視覚情報"))
    deps = _rows(find_table(tables, section_contains="データ・権限依存"))
    target_keys = [_value(row, "対象キー") for row in screen if _nonempty(_value(row, "対象キー"))]
    element_keys = [_value(row, "要素キー") for row in elements if _nonempty(_value(row, "要素キー"))]
    state_keys = [_value(row, "状態キー") for row in states if _nonempty(_value(row, "状態キー"))]
    element_targets = {
        _value(row, "要素キー"): _value(row, "対象キー")
        for row in elements
        if _nonempty(_value(row, "要素キー"))
    }
    state_targets = {
        _value(row, "状態キー"): _value(row, "対象キー")
        for row in states
        if _nonempty(_value(row, "状態キー"))
    }

    unique_issues = {}
    for label, values in (("対象キー", target_keys), ("要素キー", element_keys), ("状態キー", state_keys)):
        duplicates = sorted(value for value in set(values) if values.count(value) > 1)
        if duplicates:
            unique_issues[label] = duplicates
    result.add("TTI-D002", not unique_issues, "対象 / 要素 / 状態キーが成果物内で一意であること", evidence=unique_issues or None)

    key_issues = []
    for field, values, pattern in (
        ("対象キー", target_keys, r"target-\d{3}"),
        ("要素キー", element_keys, r"element-\d{3}"),
        ("状態キー", state_keys, r"state-\d{3}"),
    ):
        if expected.get("new_artifact"):
            key_issues.extend({"field": field, "value": value} for value in values if not re.fullmatch(pattern, value))
    result.add("TTI-D003", not key_issues, "新規成果物が正規の文書ローカルキー形式を使うこと", evidence=key_issues or None)

    status_issues = []
    for table in (screen, elements, states, behaviors, visual, deps):
        for row in table:
            state = _value(row, "確認状態")
            if state not in CONFIRM_STATES:
                status_issues.append({"section": "観測行", "key": _value(row, "対象キー") or _value(row, "要素キー") or _value(row, "状態キー"), "state": state})
    result.add("TTI-D004", not status_issues, "確認状態が正規値へ閉じていること", evidence=status_issues or None)

    reference_issues = []
    current_targets = set(target_keys)
    current_elements = set(element_keys)
    current_states = set(state_keys)
    for row in elements:
        key = _value(row, "対象キー")
        if key and key not in current_targets:
            reference_issues.append({"section": "UI要素", "target": key})
    for row in states:
        key = _value(row, "対象キー")
        if key and key not in current_targets:
            reference_issues.append({"section": "状態", "target": key})
    for row in behaviors:
        target, element = _value(row, "対象キー"), _value(row, "要素キー")
        if target and target not in current_targets:
            reference_issues.append({"section": "操作・ふるまい", "target": target})
        if _nonempty(element):
            if element not in current_elements:
                reference_issues.append({"section": "操作・ふるまい", "element": element})
            elif element_targets[element] != target:
                reference_issues.append(
                    {"section": "操作・ふるまい", "target": target, "element": element, "issue": "element parent target mismatch"}
                )
    for row in visual:
        target = _value(row, "対象キー")
        subkey = _value(row, "要素キー / 状態キー")
        if target and target not in current_targets:
            reference_issues.append({"section": "視覚情報", "target": target})
        if subkey not in NONE:
            if subkey in element_targets:
                if element_targets[subkey] != target:
                    reference_issues.append(
                        {"section": "視覚情報", "target": target, "subkey": subkey, "issue": "parent target mismatch"}
                    )
            elif subkey in state_targets:
                if state_targets[subkey] != target:
                    reference_issues.append(
                        {"section": "視覚情報", "target": target, "subkey": subkey, "issue": "parent target mismatch"}
                    )
            else:
                reference_issues.append({"section": "視覚情報", "subkey": subkey})
    for row in deps:
        target = _value(row, "対象キー")
        subkey = _value(row, "要素キー / 状態キー")
        if target and target not in current_targets:
            reference_issues.append({"section": "データ・権限依存", "target": target})
        if subkey not in NONE:
            if subkey in element_targets:
                if element_targets[subkey] != target:
                    reference_issues.append(
                        {"section": "データ・権限依存", "target": target, "subkey": subkey, "issue": "parent target mismatch"}
                    )
            elif subkey in state_targets:
                if state_targets[subkey] != target:
                    reference_issues.append(
                        {"section": "データ・権限依存", "target": target, "subkey": subkey, "issue": "parent target mismatch"}
                    )
            else:
                reference_issues.append({"section": "データ・権限依存", "subkey": subkey})
    implementation_table = find_table(tables, section_contains="既存テスト実装との対応")
    implementation_rows = _rows(implementation_table)
    if implementation_table is not None:
        missing_headers = sorted({"対象キー", "要素キー"} - set(implementation_table.headers))
        if missing_headers:
            reference_issues.append(
                {"section": "既存テスト実装との対応", "missing_headers": missing_headers}
            )
    for row in implementation_rows:
        target = _value(row, "対象キー")
        element = _value(row, "要素キー")
        if _nonempty(target) and target not in current_targets:
            reference_issues.append({"section": "既存テスト実装との対応", "target": target})
        if _nonempty(element):
            if element not in current_elements:
                reference_issues.append({"section": "既存テスト実装との対応", "element": element})
            elif element_targets[element] != target:
                reference_issues.append(
                    {"section": "既存テスト実装との対応", "target": target, "element": element, "issue": "element parent target mismatch"}
                )
    evidence_table = _table(tables, "構造証跡", ("対象キー", "証跡参照", "証跡revision / content identity"))
    for row in _rows(evidence_table):
        target, state = _value(row, "対象キー"), _value(row, "状態キー")
        if state not in NONE and state in state_targets and state_targets[state] != target:
            reference_issues.append(
                {"section": "構造証跡", "target": target, "state": state, "issue": "state parent target mismatch"}
            )
    result.add("TTI-D005", not reference_issues, "current行と任意repo対応表の参照先および親対象キーが整合すること", evidence=reference_issues or None)

    freshness_issues = []
    for section, rows in (("画面 / 領域", screen), ("UI要素", elements), ("状態", states), ("操作・ふるまい", behaviors), ("視覚情報", visual), ("データ・権限依存", deps)):
        for row in rows:
            if _value(row, "確認状態") != "確認済み":
                continue
            for field in ("確認条件", "確認version / build", "確認日時"):
                if not _nonempty(_value(row, field)):
                    freshness_issues.append({"section": section, "key": _value(row, "対象キー") or _value(row, "要素キー") or _value(row, "状態キー"), "missing": field})
    result.add("TTI-D006", not freshness_issues, "今回確認した行に確認条件・version / build・確認日時があること", evidence=freshness_issues or None)

    unconfirmed_issues = []
    prior_facts = expected.get("unconfirmed_facts", {})
    for section, rows in (
        ("画面 / 領域", screen),
        ("UI要素", elements),
        ("状態", states),
        ("操作・ふるまい", behaviors),
        ("視覚情報", visual),
        ("データ・権限依存", deps),
    ):
        for row in rows:
            key = _freshness_key(section, row)
            if _value(row, "確認状態") == "未確認" and key in prior_facts:
                actual = {field: _value(row, field) for field in ("確認条件", "確認version / build", "確認日時")}
                if actual != prior_facts[key]:
                    unconfirmed_issues.append({"key": key, "expected_old_facts": prior_facts[key], "actual": actual})
    result.add("TTI-D007", not unconfirmed_issues, "未確認の鮮度管理行単位で旧確認条件・version / build・日時を維持すること", evidence=unconfirmed_issues or None)

    update_table = _table(tables, "今回の更新", ("対象種別", "対象キー", "更新区分"))
    update_rows = _rows(update_table)
    existing_artifact = _nonempty(confirm.get("既存成果物参照", ""))
    update_missing = existing_artifact and update_table is None
    update_values = [_value(row, "更新区分") for row in update_rows]
    invalid_updates = [value for value in update_values if value not in UPDATE_STATES]
    unexpected_new_artifact_updates = not existing_artifact and bool(update_rows)
    update_issues = {
        "missing_table": update_missing,
        "invalid": invalid_updates,
        "new_artifact_records": unexpected_new_artifact_updates,
    }
    result.add(
        "TTI-D008",
        not update_missing and not invalid_updates and not unexpected_new_artifact_updates,
        "既存資料更新時だけ更新recordを持ち、新規成果物は更新recordを持たず、更新区分が正規値であること",
        evidence=update_issues if any(update_issues.values()) else None,
    )

    deleted = [row for row in update_rows if _value(row, "更新区分") == "削除確認"]
    deleted_issues = []
    deleted_screen_keys = set()
    for row in deleted:
        kind = _value(row, "対象種別")
        if kind in {"画面", "画面 / 領域"}:
            key = _value(row, "対象キー")
            current_keys = current_targets
            deleted_screen_keys.add(key)
        elif kind == "UI要素":
            key = _value(row, "要素キー / 状態キー")
            current_keys = current_elements
        elif kind == "状態":
            key = _value(row, "要素キー / 状態キー")
            current_keys = current_states
        else:
            deleted_issues.append({"kind": kind, "issue": "削除確認の対象種別が不正"})
            continue
        if not _nonempty(key):
            deleted_issues.append({"kind": kind, "issue": "削除確認の対象キーがない"})
        elif key in current_keys:
            deleted_issues.append({"kind": kind, "key": key, "issue": "削除対象がcurrent本体テーブルに残っている"})
        for field in ("確認条件", "確認version / build", "確認日時"):
            if not _nonempty(_value(row, field)):
                deleted_issues.append({"kind": kind, "key": key, "missing": field})
        if _value(row, "確認version / build") != "取得不能" and not _nonempty(_value(row, "確認version / build")):
            deleted_issues.append({"kind": kind, "key": key, "missing": "version / build"})
    for key in expected.get("deleted_target_keys", []):
        if key not in deleted_screen_keys:
            deleted_issues.append({"key": key, "issue": "期待された削除確認行がない"})
    result.add("TTI-D009", not deleted_issues, "対象種別ごとの削除キーが対応するcurrent本体表から除外され、比較条件があること", evidence=deleted_issues or None)

    evidence_issues = []
    for row in _rows(evidence_table):
        target, state = _value(row, "対象キー"), _value(row, "状態キー")
        ref, identity = _value(row, "証跡参照"), _value(row, "証跡revision / content identity")
        previous_ref = _value(row, "前回証跡参照")
        previous_identity = _value(row, "前回証跡revision / content identity")
        if not target or target not in current_targets:
            evidence_issues.append({"target": target, "issue": "構造証跡の対象キー参照がない"})
        if state not in NONE and state not in current_states:
            evidence_issues.append({"target": target, "state": state, "issue": "状態キー参照がない"})
        if _nonempty(ref) and not _nonempty(identity):
            evidence_issues.append({"target": target, "ref": ref, "issue": "今回証跡identityがない"})
        if _nonempty(previous_ref) and not _nonempty(previous_identity):
            evidence_issues.append({"target": target, "ref": previous_ref, "issue": "前回証跡identityがない"})
    result.add("TTI-D010", not evidence_issues, "任意ARIA snapshot証跡が対象キーと再取得可能なidentityへ追跡すること", evidence=evidence_issues or None)

    save_requirement = confirm.get("永続保存要求", "").strip()
    save_table = _table(tables, "保存結果", ("保存先", "更新元revision / content identity", "更新方式", "保存状態"))
    save_rows = [
        row for row in _rows(save_table) if any(value.strip() for value in row.values())
    ]
    save_issues = []
    if save_requirement not in {"はい", "いいえ"}:
        save_issues.append({"value": save_requirement, "issue": "永続保存要求が正規値ではない"})
    if save_requirement == "はい" and not save_rows:
        save_issues.append({"issue": "保存要求に対する保存結果がない"})
    elif save_requirement == "いいえ" and save_rows:
        save_issues.append({"issue": "保存要求なしに保存結果recordがある"})
    conditional_update_required = expected.get("conditional_update_required", False)
    for row in save_rows:
        status = _value(row, "保存状態")
        if status not in SAVE_STATES:
            save_issues.append({"status": status, "issue": "保存状態が不正"})
        if status == "保存済み":
            for field in ("保存先", "更新方式", "保存後revision / content identity"):
                if not _nonempty(_value(row, field)):
                    save_issues.append({"status": status, "missing": field})
            source_revision = _value(row, "更新元revision / content identity")
            confirmed_source_revision = confirm.get("更新元revision / content identity", "")
            if existing_artifact and not _nonempty(source_revision):
                save_issues.append({"status": status, "missing": "更新元revision / content identity"})
            if (
                _nonempty(source_revision)
                and _nonempty(confirmed_source_revision)
                and source_revision != confirmed_source_revision
            ):
                save_issues.append(
                    {
                        "status": status,
                        "save_source_revision": source_revision,
                        "confirmed_source_revision": confirmed_source_revision,
                        "issue": "更新元revisionが確認情報と一致しない",
                    }
                )
            if conditional_update_required and not re.search(r"if[- ]?match|etag|revision|sha", _value(row, "更新方式"), re.IGNORECASE):
                save_issues.append({"status": status, "method": _value(row, "更新方式"), "issue": "共有保存先の条件付き更新方式が確認できない"})
        if status in {"保存中止", "保存失敗"} and not _nonempty(_value(row, "競合・制約 / 理由")):
            save_issues.append({"status": status, "issue": "制約 / 理由がない"})
    result.add("TTI-D011", not save_issues, "保存要求の有無と保存recordが整合し、要求時は競合安全な更新方式・revision・制約が対応すること", evidence=save_issues or None)

    side_table = _table(tables, "副作用・cleanup", ("副作用scope", "1回の定義", "最大回数", "累計実施回数"))
    side_issues = []
    side_rows = _rows(side_table)
    scope_values = [_value(row, "副作用scope") for row in side_rows]
    duplicate_scopes = sorted(scope for scope in set(scope_values) if scope and scope_values.count(scope) > 1)
    side_issues.extend({"scope": scope, "issue": "scopeの正本行が重複"} for scope in duplicate_scopes)
    for row in side_rows:
        scope = _value(row, "副作用scope")
        definition = _value(row, "1回の定義")
        maximum = _integer(_value(row, "最大回数"))
        preparation = _integer(_value(row, "準備回数"))
        observation = _integer(_value(row, "観測操作回数"))
        cleanup_count = _integer(_value(row, "cleanup回数"))
        total = _integer(_value(row, "累計実施回数"))
        cleanup_state = _value(row, "cleanup結果")
        if not scope or not definition or maximum is None or None in (preparation, observation, cleanup_count, total):
            side_issues.append({"scope": scope, "issue": "scope・定義・回数が不足または不正"})
            continue
        if total != preparation + observation + cleanup_count or total > maximum:
            side_issues.append({"scope": scope, "issue": "工程別回数・累計・上限が不整合"})
        if cleanup_state not in CLEANUP_STATES:
            side_issues.append({"scope": scope, "cleanup": cleanup_state})
        residual = _value(row, "残存状態")
        if cleanup_state == "成功" and not any(marker in residual for marker in ("なし", "元に戻", "復元", "解消")):
            side_issues.append({"scope": scope, "issue": "cleanup成功と残存状態が不整合"})
    result.add("TTI-D012", not side_issues, "副作用scopeの定義・回数・cleanupが整合すること", evidence=side_issues or None)

    secret_issues = [value for value in expected.get("forbidden_output_values", []) if isinstance(value, str) and value and value in text]
    result.add("TTI-D013", not secret_issues, "既知dummy secret等の禁止実値が成果物へ漏れていないこと", evidence=secret_issues or None)

    old_version = expected.get("expected_old_version")
    current_version = expected.get("expected_current_version")
    if old_version or current_version:
        version_issues = []
        if old_version and old_version not in text:
            version_issues.append({"missing_old_observed_value": old_version})
        if current_version and current_version not in confirm.get("version / build", ""):
            version_issues.append({"missing_current_value": current_version})
        result.add("TTI-D014", not version_issues, "旧値・今回値を保持し、version / build差だけで比較を拒否しないこと", evidence=version_issues or None)

    required_key_issues = []
    for field, actual in (
        ("required_target_keys", set(target_keys)),
        ("required_element_keys", set(element_keys)),
        ("required_state_keys", set(state_keys)),
    ):
        missing_keys = sorted(set(expected.get(field, [])) - actual)
        if missing_keys:
            required_key_issues.append({"field": field, "missing": missing_keys})
    result.add("TTI-D015", not required_key_issues, "fixtureで必須の対象・要素・状態キーが成果物に存在すること", evidence=required_key_issues or None)

    return result
