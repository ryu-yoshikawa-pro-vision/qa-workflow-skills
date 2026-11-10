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
ACQUISITION = {"取得済", "部分取得", "未取得", "取得不能", "0件確認済み", "不明"}
APPROVAL_STATES = {"承認済み", "未承認", "失効", "不要", "unknown"}


def _metadata(table) -> dict[str, str]:
    return {
        clean(row.get("項目", "")): clean(row.get("値", ""))
        for row in nonempty_rows(table, "項目")
    }


def _table(tables, section: str, headers: tuple[str, ...]):
    return find_table(tables, section_contains=section, required_headers=headers)


def _has_value(value: str) -> bool:
    return clean(value) not in {"", "-", "—", "unknown", "未取得"}


def _source_parts(value: str) -> tuple[str, str] | None:
    if "@" not in clean(value):
        return None
    source_ref, revision = clean(value).rsplit("@", 1)
    if not source_ref or not revision:
        return None
    return source_ref, revision


def _is_held(assignment: dict[str, str]) -> bool:
    details = clean(assignment.get("状態・準備条件", "")).lower()
    return any(word in details for word in ("未確定", "保留", "blocked", "要再確認"))


def _levels(value: str) -> set[str]:
    return {
        level
        for level in re.split(r"[、・,;/\s]+", clean(value))
        if level in {"コンポーネント", "API", "システム", "受入", "別レベル"}
    }


def _level_tokens(value: str) -> set[str]:
    normalized = clean(value)
    if normalized in {"", "-"}:
        return set()
    return {token for token in re.split(r"[、・,;/\s]+", normalized) if token}


def _mentions_level(text: str, level: str) -> bool:
    if level in {"API"}:
        return re.search(r"(?<![A-Za-z0-9])API(?![A-Za-z0-9])", text) is not None
    return level in text


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

    assignments = nonempty_rows(assignments_table)
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

    sources = nonempty_rows(sources_table)
    invalid_sources = []
    source_by_ref_revision: dict[tuple[str, str], list[dict[str, str]]] = {}
    for source in sources:
        source_ref = clean(source.get("source_ref", ""))
        revision = clean(source.get("revision", ""))
        embedded_revision = source_ref.rsplit("@", 1)[1] if "@" in source_ref else ""
        if embedded_revision == revision:
            source_ref = source_ref.rsplit("@", 1)[0]
        approval_state = clean(source.get("承認状態", ""))
        approval_evidence = clean(source.get("承認証拠ref", ""))
        if (
            not clean(source.get("owner", ""))
            or not source_ref
            or not revision
            or (embedded_revision and embedded_revision != revision)
            or not clean(source.get("scope", ""))
            or clean(source.get("currentness", "")) not in CURRENTNESS
            or clean(source.get("取得状態", "")) not in ACQUISITION
            or approval_state not in APPROVAL_STATES
            or (approval_state == "承認済み" and not _has_value(approval_evidence))
        ):
            invalid_sources.append(source)
        source_by_ref_revision.setdefault((source_ref, revision), []).append(source)
    result.add(
        "TAD-D009",
        not invalid_sources,
        "source owner・revision・scope・currentness・取得状態・承認状態を記録すること",
        evidence=invalid_sources or None,
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
        parts = _source_parts(ref)
        if parts is None or not source_by_ref_revision.get(parts):
            unknown_sources.append(ref)
    unknown_sources = sorted(set(unknown_sources))
    result.add(
        "TAD-D010",
        not unknown_sources,
        "assignment根拠refが利用可能なsource inventoryに存在すること",
        evidence=unknown_sources or None,
    )

    source_problems_by_assignment = {}
    unresolved_sources = []
    unresolved_requirements = []
    known_requirement_ids = expected.get("known_qa_requirement_ids", {})
    for assignment in assignments:
        assignment_id = clean(assignment.get("割当ID", ""))
        target = clean(assignment.get("target_ref", ""))
        held = _is_held(assignment)
        problems = []

        root_parts = _source_parts(assignment.get("根拠ref / revision", ""))
        root_matches = (
            source_by_ref_revision.get(root_parts, []) if root_parts is not None else []
        )
        root_matches = [
            source
            for source in root_matches
            if clean(source.get("scope", "")) in {metadata.get("scope", ""), target}
        ]
        if len(root_matches) != 1:
            problems.append(
                {
                    "dependency": "assignment basis",
                    "ref": assignment.get("根拠ref / revision"),
                    "reason": "owner ref/revision/scope is missing or ambiguous",
                }
            )
        else:
            root_source = root_matches[0]
            if (
                clean(root_source.get("currentness", "")) != "current"
                or clean(root_source.get("取得状態", "")) != "取得済"
            ):
                problems.append(
                    {
                        "dependency": "assignment basis",
                        "ref": assignment.get("根拠ref / revision"),
                        "currentness": root_source.get("currentness"),
                        "取得状態": root_source.get("取得状態"),
                    }
                )
            if clean(assignment.get("選択根拠", "")) == "承認済みarchitecture" and (
                clean(root_source.get("承認状態", "")) != "承認済み"
                or not _has_value(root_source.get("承認証拠ref", ""))
            ):
                problems.append(
                    {
                        "dependency": "approved architecture assignment",
                        "ref": assignment.get("根拠ref / revision"),
                        "approval_state": root_source.get("承認状態"),
                        "approval_evidence_ref": root_source.get("承認証拠ref"),
                    }
                )

        requirement_ref = clean(assignment.get("QA要求ref / revision", ""))
        requirement_match = QA_REQUIREMENT_REF.fullmatch(requirement_ref)
        requirement_sources = []
        if requirement_match is not None:
            requirement_sources = source_by_ref_revision.get(
                (
                    requirement_match.group("artifact_ref"),
                    requirement_match.group("revision"),
                ),
                [],
            )
            requirement_sources = [
                source
                for source in requirement_sources
                if clean(source.get("owner", "")) == "test-requirements-analysis"
                and clean(source.get("scope", "")) == clean(metadata.get("scope", ""))
            ]
        if requirement_match is None or len(requirement_sources) != 1:
            problems.append(
                {
                    "dependency": "QA requirement",
                    "ref": requirement_ref,
                    "reason": "QA requirement owner/ref/revision/scope is missing or ambiguous",
                }
            )
        else:
            requirement_source = requirement_sources[0]
            if (
                clean(requirement_source.get("currentness", "")) != "current"
                or clean(requirement_source.get("取得状態", "")) != "取得済"
                or clean(requirement_source.get("承認状態", "")) != "承認済み"
                or not _has_value(requirement_source.get("承認証拠ref", ""))
            ):
                problems.append(
                    {
                        "dependency": "QA requirement",
                        "ref": requirement_ref,
                        "currentness": requirement_source.get("currentness"),
                        "取得状態": requirement_source.get("取得状態"),
                        "approval_state": requirement_source.get("承認状態"),
                        "approval_evidence_ref": requirement_source.get("承認証拠ref"),
                    }
                )

        source_problems_by_assignment[assignment_id] = problems
        if problems and (not held or clean(metadata.get("状態", "")) == "承認済み"):
            unresolved_sources.append(
                {"id": assignment_id, "target_ref": target, "dependencies": problems}
            )

        if requirement_match is None:
            unresolved_requirements.append(
                {"id": assignment_id, "qa_requirement_ref": requirement_ref}
            )
            continue
        local_id = requirement_match.group("requirement_id")
        local_key = f"{requirement_match.group('artifact_ref')}@{requirement_match.group('revision')}"
        known_ids = known_requirement_ids.get(local_key)
        if local_id == "QAR-UNKNOWN" and held:
            continue
        if not requirement_sources and held:
            continue
        if not isinstance(known_ids, list) or local_id not in known_ids:
            unresolved_requirements.append(
                {
                    "id": assignment_id,
                    "qa_requirement_ref": requirement_ref,
                    "reason": "local ID existence is not established by the available fixture",
                }
            )
    result.add(
        "TAD-D015",
        not unresolved_sources,
        "確定割当がcurrent・取得済み・必要承認済みの依存sourceだけを使用すること",
        evidence=unresolved_sources or None,
    )
    result.add(
        "TAD-D016",
        not unresolved_requirements,
        "QA要求refのartifact local ID・owner・scope・revisionを確認すること",
        evidence=unresolved_requirements or None,
    )

    precedence = nonempty_rows(precedence_table)
    priority_violations = []
    assignment_targets = {
        clean(assignment.get("target_ref", "")) for assignment in assignments
    }
    precedence_targets = [clean(row.get("target_ref", "")) for row in precedence]
    duplicate_precedence_targets = sorted(
        {
            target
            for target in precedence_targets
            if precedence_targets.count(target) > 1
        }
    )
    missing_precedence_targets = sorted(assignment_targets - set(precedence_targets))
    for target in duplicate_precedence_targets:
        priority_violations.append(
            {"target_ref": target, "reason": "precedence target is duplicated"}
        )
    for target in missing_precedence_targets:
        priority_violations.append(
            {"target_ref": target, "reason": "assignment target has no precedence row"}
        )
    for row in precedence:
        target = clean(row.get("target_ref", ""))
        explicit = clean(row.get("明示指定", ""))
        approved = clean(row.get("承認済み割当", ""))
        default = clean(row.get("既定値", ""))
        decision = clean(row.get("適用判断", ""))
        conflict = clean(row.get("競合・判断元", ""))
        target_assignments = [
            assignment
            for assignment in assignments
            if clean(assignment.get("target_ref", "")) == target
        ]
        explicit_levels = _levels(explicit)
        approved_levels = _levels(approved)
        default_levels = _levels(default)
        if default in {"", "-"}:
            default_levels = {"システム"}
        valid_level_tokens = {
            "コンポーネント",
            "API",
            "システム",
            "受入",
            "別レベル",
            "未確定",
        }
        invalid_level_fields = {
            field: sorted(_level_tokens(value) - valid_level_tokens)
            for field, value in (
                ("明示指定", explicit),
                ("承認済み割当", approved),
                ("既定値", default),
            )
            if _level_tokens(value) - valid_level_tokens
        }
        unresolved_level_input = any(
            "未確定" in _level_tokens(value) for value in (explicit, approved, default)
        )
        has_conflict = bool(
            explicit_levels
            and approved_levels
            and not explicit_levels <= approved_levels
        )
        dependencies_stale = any(
            source_problems_by_assignment.get(clean(assignment.get("割当ID", "")), [])
            for assignment in target_assignments
        )
        needs_hold = has_conflict or dependencies_stale or unresolved_level_input
        if explicit_levels and approved_levels:
            expected_target_levels = explicit_levels | approved_levels
            decision_basis = "明示指定"
        elif explicit_levels:
            expected_target_levels = explicit_levels
            decision_basis = "明示指定"
        elif approved_levels:
            expected_target_levels = approved_levels
            decision_basis = "承認済みarchitecture"
        else:
            expected_target_levels = default_levels or {"システム"}
            decision_basis = "test-analysis既定値"
        expected_basis_by_level = {
            level: (
                "明示指定"
                if level in explicit_levels
                else "承認済みarchitecture"
                if level in approved_levels
                else "test-analysis既定値"
            )
            for level in expected_target_levels
        }
        if needs_hold:
            dependency_broken_assignments = [
                assignment
                for assignment in target_assignments
                if source_problems_by_assignment.get(
                    clean(assignment.get("割当ID", "")), []
                )
            ]
            if has_conflict or unresolved_level_input:
                held_assignments_valid = bool(target_assignments) and all(
                    _is_held(assignment)
                    and clean(assignment.get("level", "")) == "未確定"
                    and clean(assignment.get("選択根拠", "")) == "未確定"
                    for assignment in target_assignments
                )
            else:
                current_assignments = [
                    assignment
                    for assignment in target_assignments
                    if assignment not in dependency_broken_assignments
                ]
                held_assignments_valid = bool(dependency_broken_assignments) and all(
                    _is_held(assignment)
                    and clean(assignment.get("level", "")) == "未確定"
                    and clean(assignment.get("選択根拠", "")) == "未確定"
                    for assignment in dependency_broken_assignments
                )
                current_levels = set()
                for assignment in current_assignments:
                    level = clean(assignment.get("level", ""))
                    if (
                        _is_held(assignment)
                        or level not in expected_target_levels
                        or clean(assignment.get("選択根拠", ""))
                        != expected_basis_by_level.get(level)
                    ):
                        held_assignments_valid = False
                    current_levels.add(level)
                if len(expected_target_levels - current_levels) > len(
                    dependency_broken_assignments
                ):
                    held_assignments_valid = False
            valid = (
                "未確定" in decision
                and "採用しない" in decision
                and held_assignments_valid
                and ("判断元" in conflict or "差戻" in conflict)
                and ("再取得" in conflict or "revision" in conflict.lower())
            )
            if not valid:
                priority_violations.append(
                    {
                        "target_ref": target,
                        "scope": metadata.get("scope"),
                        "reason": "conflicting or stale target dependency must remain unresolved and return to its source",
                        "decision": decision,
                        "conflict": conflict,
                        "assignments": target_assignments,
                    }
                )
            continue

        if invalid_level_fields:
            priority_violations.append(
                {
                    "target_ref": target,
                    "reason": "precedence contains an unrecognized level value",
                    "invalid_fields": invalid_level_fields,
                }
            )
            continue

        if not target_assignments:
            priority_violations.append(
                {"target_ref": target, "reason": "precedence target has no assignment"}
            )
            continue

        actual_target_levels = {
            clean(assignment.get("level", "")) for assignment in target_assignments
        }
        actual_basis_by_level = {
            clean(assignment.get("level", "")): clean(assignment.get("選択根拠", ""))
            for assignment in target_assignments
        }
        required_decision_labels = all(
            _mentions_level(decision, level) for level in expected_target_levels
        )
        if decision_basis == "明示指定":
            required_decision_labels = (
                required_decision_labels and "明示指定" in decision
            )
        elif decision_basis == "承認済みarchitecture":
            required_decision_labels = (
                required_decision_labels and "承認済みarchitecture" in decision
            )
        elif decision_basis == "test-analysis既定値":
            required_decision_labels = (
                required_decision_labels and "システム" in decision
            )
        valid = (
            actual_target_levels == expected_target_levels
            and actual_basis_by_level == expected_basis_by_level
            and required_decision_labels
        )
        if not valid:
            priority_violations.append(
                {
                    "target_ref": target,
                    "scope": metadata.get("scope"),
                    "expected_levels": sorted(expected_target_levels),
                    "actual_levels": sorted(actual_target_levels),
                    "expected_basis": expected_basis_by_level,
                    "actual_basis": actual_basis_by_level,
                    "decision": decision,
                }
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
        or not _has_value(row.get("承認主体・role", ""))
        or not _has_value(row.get("承認証拠ref", ""))
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
