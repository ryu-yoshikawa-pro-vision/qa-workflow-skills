from __future__ import annotations

import re

from scripts.skills.evals.deterministic.common import (
    add_duplicate_assertion,
    clean,
    nonempty_rows,
)
from scripts.skills.evals.deterministic.markdown_parser import find_table, parse_tables
from scripts.skills.evals.deterministic.result import EvalResult

ID_PATTERN = re.compile(r"^QAR-\d{3}$")
ARTIFACT_STATES = {"草案", "承認済み", "要再確認", "blocked", "置換"}
REQUIREMENT_STATES = {
    "提案",
    "確認待ち",
    "合意済み",
    "対象外",
    "要再確認",
    "未解決",
    "置換",
}
CURRENTNESS = {"current", "stale", "unknown"}
ACQUISITION = {"取得済", "部分取得", "未取得", "取得不能", "0件確認済み", "不明"}
APPROVAL_STATES = {"承認済み", "未承認", "失効", "不要", "未設定", "未取得", "unknown"}
UNRESOLVED_ITEM_STATES = {"未取得", "確認待ち", "未解決", "要再確認", "blocked"}
PURPOSE_FIELDS = ("QA目的", "品質目標", "対象・対象外", "活動の成功条件", "根拠")
CONTENT_PLACEHOLDERS = {"", "-", "—", "n/a", "na"}
VALUE_PLACEHOLDERS = CONTENT_PLACEHOLDERS | {
    "unknown",
    "未取得",
    "未設定",
    "未確定",
    "未確認",
    "取得不能",
    "失効",
    "expired",
    "未承認",
    "unapproved",
    "不要",
    "not required",
    "not retrieved",
}
UNRESOLVED_PURPOSE_MARKERS = (
    "unknown",
    "未取得",
    "未設定",
    "未確定",
    "未確認",
    "取得不能",
    "stale",
    "blocked",
    "expired",
    "失効",
)


def _metadata(table) -> dict[str, str]:
    return {
        clean(row.get("項目", "")): clean(row.get("値", ""))
        for row in nonempty_rows(table, "項目")
    }


def _table(tables, section: str, headers: tuple[str, ...]):
    return find_table(tables, section_contains=section, required_headers=headers)


def _has_value(value: str) -> bool:
    return clean(value).casefold() not in VALUE_PLACEHOLDERS


def _has_content(value: str) -> bool:
    return clean(value).casefold() not in CONTENT_PLACEHOLDERS


def _contains_unresolved_marker(value: str) -> bool:
    normalized = clean(value).casefold()
    for marker in UNRESOLVED_PURPOSE_MARKERS:
        marker = marker.casefold()
        if normalized == marker or re.fullmatch(
            re.escape(marker) + r"\s*[:：;；(（—–-].*", normalized
        ):
            return True
    return False


def _has_unresolved_reason(value: str) -> bool:
    normalized = clean(value).casefold()
    if not _has_value(normalized):
        return False

    for marker in UNRESOLVED_PURPOSE_MARKERS:
        marker = marker.casefold()
        if normalized == marker:
            return False
        match = re.fullmatch(re.escape(marker) + r"\s*[:：;；(（—–-](.*)", normalized)
        if match is not None:
            reason = re.sub(
                r"^[\s:：;；()（）—–-]+|[\s:：;；()（）—–-]+$",
                "",
                clean(match.group(1)),
            )
            normalized_reason = clean(reason).casefold()
            return _has_value(normalized_reason) and all(
                normalized_reason != unresolved_marker.casefold()
                for unresolved_marker in UNRESOLVED_PURPOSE_MARKERS
            )
    return True


def _scope_covers(scope_value: str, target_scope: str) -> bool:
    scopes = {clean(value) for value in re.split(r"[,、;]", clean(scope_value))}
    return bool(clean(target_scope)) and clean(target_scope) in scopes


def validate(text: str, expected: dict, eval_id: str) -> EvalResult:
    result = EvalResult("test-requirements-analysis", eval_id)
    tables = parse_tables(text)
    metadata_table = _table(tables, "成果物メタデータ", ("項目", "値"))
    requirements_table = _table(
        tables,
        "QA要求",
        (
            "QA要求ID",
            "QA活動上の要求",
            "要求元",
            "source_ref",
            "source_revision",
            "scope",
            "状態",
        ),
    )
    purpose_table = _table(tables, "QA目的・成功条件", PURPOSE_FIELDS)
    source_table = _table(
        tables,
        "情報源・取得範囲",
        ("owner", "source_ref", "revision", "scope", "currentness", "取得状態"),
    )
    approval_table = _table(
        tables,
        "確認・承認",
        (
            "対象scope",
            "artifact_ref",
            "revision",
            "承認主体・role",
            "承認証拠ref",
            "状態",
        ),
    )
    unresolved_table = _table(
        tables, "未決事項", ("項目", "影響scope", "担当", "状態", "再開条件")
    )
    missing_tables = [
        name
        for name, table in (
            ("成果物メタデータ", metadata_table),
            ("QA要求", requirements_table),
            ("QA目的・成功条件", purpose_table),
            ("情報源・取得範囲", source_table),
            ("確認・承認", approval_table),
            ("未決事項", unresolved_table),
        )
        if table is None
    ]
    metadata = _metadata(metadata_table)
    purpose_errors = []
    if purpose_table is not None:
        if not purpose_table.rows:
            purpose_errors.append({"reason": "QA目的・成功条件 row is missing"})
        for index, row in enumerate(purpose_table.rows, start=1):
            missing_fields = [
                field
                for field in PURPOSE_FIELDS
                if not _has_content(row.get(field, ""))
            ]
            unresolved_fields = [
                field
                for field in PURPOSE_FIELDS
                if _contains_unresolved_marker(row.get(field, ""))
            ]
            unresolved_reason = clean(row.get("根拠", ""))
            unresolved_reason_missing = bool(unresolved_fields) and not (
                _has_unresolved_reason(unresolved_reason)
            )
            approved_with_unresolved_fields = metadata.get(
                "状態"
            ) == "承認済み" and bool(unresolved_fields)
            if (
                missing_fields
                or approved_with_unresolved_fields
                or unresolved_reason_missing
            ):
                purpose_errors.append(
                    {
                        "row": index,
                        "missing_fields": missing_fields,
                        "unresolved_fields": unresolved_fields,
                        "unresolved_reason_missing": unresolved_reason_missing,
                    }
                )
    result.add(
        "QRA-D001",
        not missing_tables and not purpose_errors,
        "正規テーブルとQA目的・成功条件の必須項目が存在し、承認済みでは未確定表示がないこと",
        evidence=(
            {"missing_tables": missing_tables, "purpose_errors": purpose_errors}
            if missing_tables or purpose_errors
            else None
        ),
    )

    required_metadata = ("owner", "artifact_ref", "revision", "scope", "状態")
    missing_metadata = [key for key in required_metadata if not metadata.get(key)]
    result.add(
        "QRA-D002",
        not missing_metadata and metadata.get("owner") == "test-requirements-analysis",
        "owner・artifact ref・revision・scope・状態が明示されること",
        evidence=missing_metadata or None,
    )
    result.add(
        "QRA-D003",
        metadata.get("状態", "") in ARTIFACT_STATES,
        "artifact状態が許可値であること",
        evidence=metadata.get("状態")
        if metadata.get("状態") not in ARTIFACT_STATES
        else None,
    )

    requirements = nonempty_rows(requirements_table)
    ids = [clean(row.get("QA要求ID", "")) for row in requirements]
    invalid_ids = [value for value in ids if not ID_PATTERN.fullmatch(value)]
    add_duplicate_assertion(result, "QRA-D004", ids, "QA要求ID")
    result.add(
        "QRA-D005",
        not invalid_ids,
        "QA要求IDがartifact-local QAR-001形式であること",
        evidence=invalid_ids or None,
    )
    missing_fields = []
    for row in requirements:
        absent = [
            field
            for field in (
                "QA活動上の要求",
                "要求元",
                "source_ref",
                "source_revision",
                "scope",
                "優先度",
                "状態",
                "根拠・成功条件",
            )
            if not clean(row.get(field, ""))
        ]
        if absent:
            missing_fields.append({"id": row.get("QA要求ID"), "fields": absent})
    result.add(
        "QRA-D006",
        not missing_fields,
        "QA要求の要求元・revision・scope・根拠を保持すること",
        evidence=missing_fields or None,
    )
    invalid_states = sorted(
        {
            clean(row.get("状態", ""))
            for row in requirements
            if clean(row.get("状態", "")) not in REQUIREMENT_STATES
        }
    )
    result.add(
        "QRA-D007",
        not invalid_states,
        "QA要求状態が許可値であること",
        evidence=invalid_states or None,
    )
    required_ids = set(expected.get("required_qa_requirement_ids", []))
    missing_required = sorted(required_ids - set(ids))
    result.add(
        "QRA-D008",
        not missing_required,
        "fixtureで必要なQA要求が存在すること",
        evidence=missing_required or None,
    )
    wrong_owner_ids = [value for value in ids if re.fullmatch(r"TR-\d{3}", value)]
    result.add(
        "QRA-D009",
        not wrong_owner_ids,
        "製品テスト要求のTR IDをQA要求IDとして使わないこと",
        evidence=wrong_owner_ids or None,
    )

    sources = nonempty_rows(source_table)
    invalid_source_states = []
    source_refs = set()
    for row in sources:
        ref = clean(row.get("source_ref", ""))
        source_refs.add(ref)
        currentness = clean(row.get("currentness", ""))
        acquisition = clean(row.get("取得状態", ""))
        if (
            not clean(row.get("owner", ""))
            or not ref
            or not clean(row.get("revision", ""))
            or not clean(row.get("scope", ""))
        ):
            invalid_source_states.append(
                {"ref": ref, "reason": "owner/revision/scope missing"}
            )
        if currentness not in CURRENTNESS or acquisition not in ACQUISITION:
            invalid_source_states.append(
                {"ref": ref, "currentness": currentness, "acquisition": acquisition}
            )
    result.add(
        "QRA-D010",
        not invalid_source_states,
        "source owner・revision・scope・currentness・取得状態が区別されること",
        evidence=invalid_source_states or None,
    )
    sources_by_identity: dict[tuple[str, str, str], list[dict[str, str]]] = {}
    for source in sources:
        identity = (
            clean(source.get("source_ref", "")),
            clean(source.get("revision", "")),
            clean(source.get("scope", "")),
        )
        sources_by_identity.setdefault(identity, []).append(source)
    unmatched_requirements = []
    stale_final_requirements = []
    for row in requirements:
        identity = (
            clean(row.get("source_ref", "")),
            clean(row.get("source_revision", "")),
            clean(row.get("scope", "")),
        )
        matching_sources = sources_by_identity.get(identity, [])
        if len(matching_sources) != 1:
            unmatched_requirements.append(
                {
                    "id": row.get("QA要求ID"),
                    "source_ref": row.get("source_ref"),
                    "source_revision": row.get("source_revision"),
                    "scope": row.get("scope"),
                    "matching_source_rows": len(matching_sources),
                }
            )
            continue
        source = matching_sources[0]
        if clean(row.get("状態", "")) in {"合意済み", "対象外"} and (
            clean(source.get("currentness", "")) != "current"
            or clean(source.get("取得状態", "")) != "取得済"
        ):
            stale_final_requirements.append(
                {
                    "id": row.get("QA要求ID"),
                    "source_ref": identity[0],
                    "revision": identity[1],
                    "scope": identity[2],
                    "owner": clean(source.get("owner", "")),
                    "currentness": clean(source.get("currentness", "")),
                    "取得状態": clean(source.get("取得状態", "")),
                }
            )
    result.add(
        "QRA-D015",
        not unmatched_requirements and not stale_final_requirements,
        "確定QA要求のsource owner・ref・revision・scope・currentness・取得状態が一致すること",
        evidence=(
            {
                "unmatched_requirements": unmatched_requirements,
                "stale_final_requirements": stale_final_requirements,
            }
            if unmatched_requirements or stale_final_requirements
            else None
        ),
    )
    known_sources = set(expected.get("known_sources", []))
    unknown_refs = (
        sorted(
            {clean(row.get("source_ref", "")) for row in requirements} - known_sources
        )
        if "known_sources" in expected
        else []
    )
    result.add(
        "QRA-D011",
        not unknown_refs,
        "QA要求のsource refがfixtureの既知sourceに存在すること",
        evidence=unknown_refs or None,
    )

    unresolved = nonempty_rows(unresolved_table, "項目")
    open_rows = [row for row in requirements if clean(row.get("状態", "")) == "未解決"]
    uncovered = []
    for requirement in open_rows:
        requirement_id = clean(requirement.get("QA要求ID", ""))
        matching_items = [
            item for item in unresolved if clean(item.get("項目", "")) == requirement_id
        ]
        if len(matching_items) != 1:
            uncovered.append(
                {
                    "id": requirement_id,
                    "reason": "matching unresolved item must exist exactly once",
                    "matching_rows": len(matching_items),
                }
            )
            continue
        item = matching_items[0]
        scope = clean(item.get("影響scope", ""))
        state = clean(item.get("状態", ""))
        missing_fields = [
            field
            for field in ("影響scope", "担当", "再開条件")
            if not _has_value(item.get(field, ""))
        ]
        invalid = {
            "id": requirement_id,
            "missing_fields": missing_fields,
            "scope_mismatch": not _scope_covers(
                scope, clean(requirement.get("scope", ""))
            ),
            "invalid_state": state not in UNRESOLVED_ITEM_STATES,
        }
        if missing_fields or invalid["scope_mismatch"] or invalid["invalid_state"]:
            uncovered.append(invalid)
    result.add(
        "QRA-D012",
        not uncovered,
        "未解決QA要求がscope・担当・許可状態・再開条件を持つ一意な未決事項へ閉じること",
        evidence=uncovered or None,
    )

    approval_rows = nonempty_rows(approval_table)
    invalid_approval_states = [
        row
        for row in approval_rows
        if clean(row.get("状態", "")) not in APPROVAL_STATES
    ]
    approvals = approval_rows
    approved_rows = [
        row for row in approvals if clean(row.get("状態", "")) == "承認済み"
    ]
    approval_mismatch = list(invalid_approval_states)
    for row in approved_rows:
        if (
            clean(row.get("artifact_ref", "")) != metadata.get("artifact_ref")
            or clean(row.get("revision", "")) != metadata.get("revision")
            or clean(row.get("対象scope", "")) != metadata.get("scope")
            or not _has_value(row.get("承認主体・role", ""))
            or not _has_value(row.get("承認証拠ref", ""))
            or metadata.get("状態") != "承認済み"
        ):
            approval_mismatch.append(row)
    if metadata.get("状態") == "承認済み" and not approved_rows:
        approval_mismatch.append(
            {"reason": "approved artifact without matching approval evidence"}
        )
    unresolved_approved_requirements = []
    if metadata.get("状態") == "承認済み":
        for row in requirements:
            requirement_scope = clean(row.get("scope", ""))
            if clean(row.get("状態", "")) == "未解決" and _scope_covers(
                metadata.get("scope", ""), requirement_scope
            ):
                unresolved_approved_requirements.append(
                    {
                        "id": clean(row.get("QA要求ID", "")),
                        "scope": requirement_scope,
                        "state": clean(row.get("状態", "")),
                        "reason": "unresolved QA requirement remains within approved artifact scope",
                    }
                )
    finalized_without_approval = [
        {"id": row.get("QA要求ID"), "state": row.get("状態")}
        for row in requirements
        if clean(row.get("状態", "")) in {"合意済み", "対象外"}
        and metadata.get("状態") != "承認済み"
    ]
    stale_dependencies = []
    if metadata.get("状態") == "承認済み":
        for row in requirements:
            identity = (
                clean(row.get("source_ref", "")),
                clean(row.get("source_revision", "")),
                clean(row.get("scope", "")),
            )
            if clean(row.get("状態", "")) not in {"合意済み", "対象外"}:
                continue
            matching_sources = sources_by_identity.get(identity, [])
            if len(matching_sources) != 1:
                continue
            source = matching_sources[0]
            if (
                clean(source.get("currentness", "")) != "current"
                or clean(source.get("取得状態", "")) != "取得済"
            ):
                stale_dependencies.append(
                    {
                        "id": row.get("QA要求ID"),
                        "source_ref": identity[0],
                        "revision": identity[1],
                        "scope": identity[2],
                        "currentness": clean(source.get("currentness", "")),
                        "取得状態": clean(source.get("取得状態", "")),
                    }
                )
    approval_mismatch.extend(finalized_without_approval)
    approval_mismatch.extend(stale_dependencies)
    approval_mismatch.extend(unresolved_approved_requirements)
    result.add(
        "QRA-D013",
        not approval_mismatch,
        "承認済み表示が同一scope・artifact ref・revisionの証拠に結び付くこと",
        evidence=approval_mismatch or None,
    )
    if expected.get("must_not_claim_approved"):
        result.add(
            "QRA-D014",
            metadata.get("状態") != "承認済み",
            "fixtureの未承認要求を承認済みと扱わないこと",
            evidence=metadata.get("状態"),
        )
    return result
