from __future__ import annotations

import re

from scripts.skills.evals.deterministic.common import (
    add_duplicate_assertion,
    clean,
    nonempty_rows,
)
from scripts.skills.evals.deterministic.markdown_parser import find_table, parse_tables
from scripts.skills.evals.deterministic.result import EvalResult

ID_PATTERN = re.compile(r"^ARCH-\d{3}$")
QA_REQUIREMENT_REF = re.compile(
    r"^(?P<artifact_ref>.+)#(?P<requirement_id>QAR-\d{3}|QAR-UNKNOWN)@(?P<revision>[^@]+)$"
)
ARTIFACT_STATES = {"草案", "承認済み", "要再確認", "blocked", "置換"}
LEVELS = {"コンポーネント", "API", "システム", "受入", "別レベル", "未確定"}
BASES = {"明示指定", "承認済みarchitecture", "test-analysis既定値", "未確定"}
CURRENTNESS = {"current", "stale", "unknown"}


def _metadata(table) -> dict[str, str]:
    return {
        clean(row.get("項目", "")): clean(row.get("値", ""))
        for row in nonempty_rows(table, "項目")
    }


def _table(tables, section: str, headers: tuple[str, ...]):
    return find_table(tables, section_contains=section, required_headers=headers)


def validate(text: str, expected: dict, eval_id: str) -> EvalResult:
    result = EvalResult("test-architecture-design", eval_id)
    tables = parse_tables(text)
    metadata_table = _table(tables, "成果物メタデータ", ("項目", "値"))
    sources_table = _table(
        tables,
        "入力source・依存",
        ("owner", "source_ref", "revision", "scope", "currentness", "取得状態"),
    )
    assignments_table = _table(
        tables,
        "テストアーキテクチャ割当",
        (
            "割当ID",
            "target_ref",
            "target種別",
            "QA要求ref / revision",
            "level",
            "type",
            "方式・検証分担",
            "選択根拠",
            "根拠ref / revision",
            "状態・準備条件",
            "owner",
        ),
    )
    precedence_table = _table(
        tables,
        "レベル優先・競合",
        (
            "target_ref",
            "明示指定",
            "承認済み割当",
            "既定値",
            "適用判断",
            "競合・判断元",
        ),
    )
    approvals_table = _table(
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
    impact_table = _table(
        tables,
        "変更影響・handoff",
        (
            "変更ref / revision",
            "影響scope",
            "要再確認のowner / ref",
            "保持するcurrent成果物",
            "resume owner",
            "理由",
        ),
    )
    missing_tables = [
        name
        for name, table in (
            ("成果物メタデータ", metadata_table),
            ("入力source・依存", sources_table),
            ("テストアーキテクチャ割当", assignments_table),
            ("レベル優先・競合", precedence_table),
            ("承認", approvals_table),
            ("変更影響・handoff", impact_table),
        )
        if table is None
    ]
    result.add(
        "TAD-D001",
        not missing_tables,
        "architectureの正規テーブルが存在すること",
        evidence=missing_tables or None,
    )

    metadata = _metadata(metadata_table)
    required_metadata = ("owner", "artifact_ref", "revision", "scope", "状態")
    missing_metadata = [key for key in required_metadata if not metadata.get(key)]
    result.add(
        "TAD-D002",
        not missing_metadata and metadata.get("owner") == "test-architecture-design",
        "owner・artifact ref・revision・scope・状態が明示されること",
        evidence=missing_metadata or None,
    )
    result.add(
        "TAD-D003",
        metadata.get("状態", "") in ARTIFACT_STATES,
        "artifact状態が許可値であること",
        evidence=metadata.get("状態")
        if metadata.get("状態") not in ARTIFACT_STATES
        else None,
    )

    assignments = nonempty_rows(assignments_table, "割当ID")
    ids = [clean(row.get("割当ID", "")) for row in assignments]
    add_duplicate_assertion(result, "TAD-D004", ids, "割当ID")
    invalid_ids = [value for value in ids if not ID_PATTERN.fullmatch(value)]
    result.add(
        "TAD-D005",
        not invalid_ids,
        "割当IDがartifact-local ARCH-001形式であること",
        evidence=invalid_ids or None,
    )
    missing_fields = []
    for row in assignments:
        absent = [
            field
            for field in (
                "target_ref",
                "target種別",
                "QA要求ref / revision",
                "level",
                "type",
                "方式・検証分担",
                "environment / data",
                "runner / tool",
                "選択根拠",
                "根拠ref / revision",
                "状態・準備条件",
                "owner",
            )
            if not clean(row.get(field, ""))
        ]
        if absent:
            missing_fields.append({"id": row.get("割当ID"), "fields": absent})
    result.add(
        "TAD-D006",
        not missing_fields,
        "割当に対象・方式・環境・根拠・ownerがあること",
        evidence=missing_fields or None,
    )

    invalid = []
    duplicate_assignment_keys = []
    seen: set[tuple[str, str, str, str]] = set()
    for row in assignments:
        level = clean(row.get("level", ""))
        basis = clean(row.get("選択根拠", ""))
        key = (
            clean(row.get("target_ref", "")),
            level,
            clean(row.get("type", "")),
            clean(row.get("方式・検証分担", "")),
        )
        if level not in LEVELS or basis not in BASES:
            invalid.append({"id": row.get("割当ID"), "level": level, "basis": basis})
        if key in seen:
            duplicate_assignment_keys.append(key)
        seen.add(key)
        if basis == "test-analysis既定値" and level != "システム":
            invalid.append(
                {"id": row.get("割当ID"), "reason": "default level must be system"}
            )
    result.add(
        "TAD-D007",
        not invalid,
        "level・割当根拠が許可され、既定値はsystem testであること",
        evidence=invalid or None,
    )
    result.add(
        "TAD-D008",
        not duplicate_assignment_keys,
        "同じtarget・level・type・責務を重複登録しないこと",
        evidence=duplicate_assignment_keys or None,
    )

    sources = nonempty_rows(sources_table, "source_ref")
    invalid_sources = []
    for row in sources:
        source_ref = clean(row.get("source_ref", ""))
        revision = clean(row.get("revision", ""))
        embedded_revision = source_ref.rsplit("@", 1)[1] if "@" in source_ref else ""
        if (
            not clean(row.get("owner", ""))
            or not revision
            or (embedded_revision and embedded_revision != revision)
            or not clean(row.get("scope", ""))
            or clean(row.get("currentness", "")) not in CURRENTNESS
            or not clean(row.get("取得状態", ""))
        ):
            invalid_sources.append(row)
    result.add(
        "TAD-D009",
        not invalid_sources,
        "source currentness・取得状態とowner revisionを記録すること",
        evidence=invalid_sources or None,
    )
    source_status = {}
    for row in sources:
        source_ref = clean(row.get("source_ref", ""))
        revision = clean(row.get("revision", ""))
        if "@" in source_ref and source_ref.rsplit("@", 1)[1] == revision:
            source_ref = source_ref.rsplit("@", 1)[0]
        source_status[(source_ref, revision)] = (
            clean(row.get("currentness", "")),
            clean(row.get("取得状態", "")),
        )
    known_sources = set(expected.get("known_sources", []))
    assignment_sources = {
        clean(row.get("根拠ref / revision", "")) for row in assignments
    }
    unknown_sources = (
        sorted(assignment_sources - known_sources)
        if "known_sources" in expected
        else []
    )
    for ref in assignment_sources:
        if "@" not in ref:
            unknown_sources.append(ref)
            continue
        source_ref, revision = ref.rsplit("@", 1)
        if (source_ref, revision) not in source_status:
            unknown_sources.append(ref)
    unknown_sources = sorted(set(unknown_sources))
    result.add(
        "TAD-D010",
        not unknown_sources,
        "assignmentの根拠refがfixtureの既知sourceに存在すること",
        evidence=unknown_sources or None,
    )
    unresolved_sources = []
    for row in assignments:
        ref = clean(row.get("根拠ref / revision", ""))
        source = None
        if "@" in ref:
            source_ref, revision = ref.rsplit("@", 1)
            source = source_status.get((source_ref, revision))
        if source is None:
            continue
        currentness, acquisition = source
        hold = any(
            word in clean(row.get("状態・準備条件", ""))
            for word in ("未確定", "保留", "blocked", "要再確認")
        )
        if (currentness != "current" or acquisition != "取得済") and (
            clean(row.get("level", "")) != "未確定" or not hold
        ):
            unresolved_sources.append({"id": row.get("割当ID"), "source_ref": ref})
    result.add(
        "TAD-D015",
        not unresolved_sources,
        "staleまたは未取得のassignment根拠から確定割当を作らないこと",
        evidence=unresolved_sources or None,
    )
    unresolved_requirements = []
    for row in assignments:
        value = clean(row.get("QA要求ref / revision", ""))
        match = QA_REQUIREMENT_REF.fullmatch(value)
        if match is None:
            unresolved_requirements.append(
                {"id": row.get("割当ID"), "qa_requirement_ref": value}
            )
            continue
        artifact_ref = match.group("artifact_ref")
        revision = match.group("revision")
        if (artifact_ref, revision) not in source_status:
            unresolved_requirements.append(
                {"id": row.get("割当ID"), "qa_requirement_ref": value}
            )
    result.add(
        "TAD-D016",
        not unresolved_requirements,
        "QA要求refがartifact-local IDとsource revisionに固定されること",
        evidence=unresolved_requirements or None,
    )

    precedence = nonempty_rows(precedence_table, "target_ref")
    priority_violations = []
    for row in precedence:
        explicit = clean(row.get("明示指定", ""))
        approved = clean(row.get("承認済み割当", ""))
        default = clean(row.get("既定値", ""))
        decision = clean(row.get("適用判断", ""))
        if "未確定" in decision and any(
            clean(source.get("currentness", "")) in {"stale", "unknown"}
            for source in sources
        ):
            valid = True
        elif explicit and explicit != "-":
            valid = explicit in decision and "明示指定" in decision
        elif approved and approved != "-":
            valid = approved in decision and "承認済みarchitecture" in decision
        else:
            valid = (default in {"", "-", "システム"}) and "システム" in decision
        if not valid:
            priority_violations.append(
                {"target_ref": row.get("target_ref"), "decision": decision}
            )
    result.add(
        "TAD-D011",
        not priority_violations,
        "明示指定＞承認済み割当＞既定system testの優先を守ること",
        evidence=priority_violations or None,
    )

    expected_levels = expected.get("expected_levels", {})
    actual_levels = {}
    for row in assignments:
        actual_levels.setdefault(clean(row.get("target_ref", "")), set()).add(
            clean(row.get("level", ""))
        )
    level_mismatches = [
        {
            "target_ref": target,
            "expected": sorted(levels),
            "actual": sorted(actual_levels.get(target, set())),
        }
        for target, levels in expected_levels.items()
        if set(levels) != actual_levels.get(target, set())
    ]
    result.add(
        "TAD-D012",
        not level_mismatches,
        "fixtureで指定された複数levelを維持すること",
        evidence=level_mismatches or None,
    )

    approvals = [
        row
        for row in nonempty_rows(approvals_table, "状態")
        if clean(row.get("状態", "")) == "承認済み"
    ]
    mismatched_approvals = [
        row
        for row in approvals
        if clean(row.get("artifact_ref", "")) != metadata.get("artifact_ref")
        or clean(row.get("revision", "")) != metadata.get("revision")
        or clean(row.get("対象scope", "")) != metadata.get("scope")
        or not clean(row.get("承認主体・role", ""))
        or not clean(row.get("承認証拠ref", ""))
        or metadata.get("状態") != "承認済み"
    ]
    if metadata.get("状態") == "承認済み" and not approvals:
        mismatched_approvals.append(
            {"reason": "approved architecture without approval evidence"}
        )
    result.add(
        "TAD-D013",
        not mismatched_approvals,
        "承認が同一scope・artifact ref・revisionへ結び付くこと",
        evidence=mismatched_approvals or None,
    )

    impacts = nonempty_rows(impact_table, "変更ref / revision")
    missing_impact = [
        row
        for row in impacts
        if not clean(row.get("影響scope", ""))
        or not clean(row.get("要再確認のowner / ref", ""))
        or not clean(row.get("保持するcurrent成果物", ""))
        or not clean(row.get("resume owner", ""))
        or not clean(row.get("理由", ""))
    ]
    result.add(
        "TAD-D014",
        not missing_impact,
        "変更影響・保持するcurrent成果物・resume ownerを記録すること",
        evidence=missing_impact or None,
    )
    return result
