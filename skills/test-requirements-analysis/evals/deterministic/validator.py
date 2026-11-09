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
ACQUISITION = {"取得済", "部分取得", "未取得", "取得不能", "0件確認済み"}


def _metadata(table) -> dict[str, str]:
    return {
        clean(row.get("項目", "")): clean(row.get("値", ""))
        for row in nonempty_rows(table, "項目")
    }


def _table(tables, section: str, headers: tuple[str, ...]):
    return find_table(tables, section_contains=section, required_headers=headers)


def _has_value(value: str) -> bool:
    return clean(value) not in {"", "-", "—", "N/A", "n/a"}


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
            ("情報源・取得範囲", source_table),
            ("確認・承認", approval_table),
            ("未決事項", unresolved_table),
        )
        if table is None
    ]
    result.add(
        "QRA-D001",
        not missing_tables,
        "QA要求の正規テーブルが存在すること",
        evidence=missing_tables or None,
    )

    metadata = _metadata(metadata_table)
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

    requirements = nonempty_rows(requirements_table, "QA要求ID")
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

    sources = nonempty_rows(source_table, "source_ref")
    invalid_source_states = []
    source_refs = set()
    for row in sources:
        ref = clean(row.get("source_ref", ""))
        source_refs.add(ref)
        currentness = clean(row.get("currentness", ""))
        acquisition = clean(row.get("取得状態", ""))
        if (
            not clean(row.get("owner", ""))
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
    source_identities = {
        (
            clean(row.get("source_ref", "")),
            clean(row.get("revision", "")),
            clean(row.get("scope", "")),
        )
        for row in sources
    }
    unmatched_requirements = [
        {
            "id": row.get("QA要求ID"),
            "source_ref": row.get("source_ref"),
            "source_revision": row.get("source_revision"),
            "scope": row.get("scope"),
        }
        for row in requirements
        if (
            clean(row.get("source_ref", "")),
            clean(row.get("source_revision", "")),
            clean(row.get("scope", "")),
        )
        not in source_identities
    ]
    result.add(
        "QRA-D015",
        not unmatched_requirements,
        "各QA要求のsource ref・revision・scopeが情報源一覧と一致すること",
        evidence=unmatched_requirements or None,
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
    uncovered = [
        row.get("QA要求ID", "")
        for row in open_rows
        if not any(
            clean(item.get("項目", "")) == clean(row.get("QA要求ID", ""))
            for item in unresolved
        )
    ]
    result.add(
        "QRA-D012",
        not uncovered,
        "未解決QA要求が担当・再開条件を持つ未決事項へ閉じること",
        evidence=uncovered or None,
    )

    approvals = nonempty_rows(approval_table, "状態")
    approved_rows = [
        row for row in approvals if clean(row.get("状態", "")) == "承認済み"
    ]
    approval_mismatch = []
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
