"""Deterministic TCN and model identity / structure runtime."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from runtime_contract import (
    MODEL_TYPES,
    SCOPE_ID_RE,
    TCN_ID_RE,
    TECHNIQUE_SLUGS,
    TR_ID_RE,
    InvalidInput,
    allocate_stable_id,
    canonicalize,
    ensure_list,
    ensure_nonempty_string,
    machine_entity_runtime_dependency,
    make_machine_entity,
    normalize_machine_entity_disposition,
    reject_unknown,
    resolve_entity_dependencies,
    run_cli,
    seed_legacy_ids,
    validate_machine_entity,
    validate_upstream_entities,
)

ITEM_RE = re.compile(r"^TI-\d{3,}$")
CONDITION_RE = re.compile(r"^COND-\d{3,}$")
DESIGN_RE = re.compile(r"^FD-\d{3,}$")
EXPECTED_RESULT_RE = re.compile(r"^ER-\d{3,}$")
DECISIONS = {
    "adopted",
    "not_applicable",
    "out_of_scope",
    "other_test_level",
    "duplicate",
    "unconfirmed",
    "blocked",
}


class FormalDesignError(ValueError):
    pass


def _require_text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise FormalDesignError(f"{name}は空でない文字列が必要です")
    return value.strip()


def _rows(value: Any, name: str) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not all(isinstance(row, dict) for row in value):
        raise FormalDesignError(f"{name}はobject配列が必要です")
    return value


def resolve_test_level(evidence: Any) -> dict[str, str]:
    if not isinstance(evidence, dict) or set(evidence) != {
        "explicit",
        "architecture",
        "default",
    }:
        raise FormalDesignError("test_level_evidence schemaが不正です")
    explicit = evidence["explicit"]
    architecture = evidence["architecture"]
    default = evidence["default"]
    if explicit is not None:
        if not isinstance(explicit, dict) or set(explicit) != {"level", "source_ref"}:
            raise FormalDesignError("explicit test level evidenceが不正です")
        return {
            "level": _require_text(explicit["level"], "explicit level"),
            "source_ref": _require_text(explicit["source_ref"], "explicit source_ref"),
            "source": "explicit",
        }
    if architecture is not None:
        if (
            not isinstance(architecture, dict)
            or set(architecture) != {"level", "source_ref", "approved"}
            or not isinstance(architecture["approved"], bool)
        ):
            raise FormalDesignError("architecture test level evidenceが不正です")
        if architecture["approved"]:
            return {
                "level": _require_text(architecture["level"], "architecture level"),
                "source_ref": _require_text(
                    architecture["source_ref"], "architecture source_ref"
                ),
                "source": "approved_architecture",
            }
    if not isinstance(default, dict) or set(default) != {"level", "source_ref"}:
        raise FormalDesignError("default test level evidenceが不正です")
    if default["level"] != "system":
        raise FormalDesignError("既定テストレベルはsystemである必要があります")
    return {
        "level": "system",
        "source_ref": _require_text(default["source_ref"], "default source_ref"),
        "source": "default",
    }


def resolve_item_test_levels(
    evidence: Any, item_refs: set[str], source_by_ref: dict[str, tuple[str, str]]
) -> dict[str, dict[str, str]]:
    if isinstance(evidence, dict):
        resolved = resolve_test_level(evidence)
        if resolved["source_ref"] not in source_by_ref:
            raise FormalDesignError("test level source_refがsource_refsにありません")
        return {item_ref: resolved for item_ref in item_refs}

    rows = _rows(evidence, "test_level_evidence")
    by_item: dict[str, dict[str, str]] = {}
    for index, row in enumerate(rows):
        if set(row) != {"item_ref", "evidence"}:
            raise FormalDesignError(
                f"test_level_evidence[{index}] schemaが不正です"
            )
        item_ref = _require_text(row["item_ref"], "test_level_evidence.item_ref")
        if item_ref not in item_refs or item_ref in by_item:
            raise FormalDesignError("item別test_level_evidenceが未知または重複しています")
        resolved = resolve_test_level(row["evidence"])
        if resolved["source_ref"] not in source_by_ref:
            raise FormalDesignError("test level source_refがsource_refsにありません")
        by_item[item_ref] = resolved
    if set(by_item) != item_refs:
        raise FormalDesignError(
            "item別test_level_evidenceとformal design itemsの集合が一致しません"
        )
    return by_item


def validate_formal_design(
    packet: Any, tcn_drafts: list[dict[str, Any]]
) -> dict[str, dict[str, Any]]:
    """Validate the full explicit pair population and project adopted pairs to TCN drafts."""
    required = {
        "schema_version",
        "design_ref",
        "revision",
        "change_reason",
        "source_refs",
        "items",
        "items_complete",
        "conditions_complete",
        "condition_candidates",
        "authorities",
        "test_level_evidence",
        "pair_assessments",
        "history",
        "retired_candidate_refs",
    }
    if not isinstance(packet, dict) or set(packet) != required:
        raise FormalDesignError("formal_design schemaが不正です")
    if packet["schema_version"] != "formal-design-v1":
        raise FormalDesignError("formal_design schema_versionが未対応です")
    design_ref = _require_text(packet["design_ref"], "design_ref")
    if not DESIGN_RE.fullmatch(design_ref):
        raise FormalDesignError("design_refの形式が不正です")
    revision = packet["revision"]
    if not isinstance(revision, int) or isinstance(revision, bool) or revision < 1:
        raise FormalDesignError("formal_design revisionは1以上の整数が必要です")
    _require_text(packet["change_reason"], "formal_design change_reason")
    if not isinstance(packet["items_complete"], bool) or not isinstance(
        packet["conditions_complete"], bool
    ):
        raise FormalDesignError(
            "items_complete / conditions_completeはbooleanが必要です"
        )
    history = _rows(packet["history"], "formal_design.history")
    history_revisions: list[int] = []
    historical_candidate_pairs: dict[str, tuple[str, str]] = {}
    historical_retirements: dict[str, str] = {}
    previous_history_candidate_ids: set[str] = set()
    for index, row in enumerate(history):
        if set(row) != {
            "revision",
            "change_reason",
            "pair_decisions",
            "candidate_assignments",
            "retired_candidate_refs",
        }:
            raise FormalDesignError(f"formal_design.history[{index}] schemaが不正です")
        old_revision = row["revision"]
        if (
            not isinstance(old_revision, int)
            or isinstance(old_revision, bool)
            or old_revision < 1
        ):
            raise FormalDesignError("formal_design history revisionが不正です")
        history_revisions.append(old_revision)
        _require_text(row["change_reason"], "formal_design history change_reason")
        old_pairs = _rows(row["pair_decisions"], "history.pair_decisions")
        seen_old_pairs: set[tuple[str, str]] = set()
        old_decision_by_pair: dict[tuple[str, str], str] = {}
        for old_pair in old_pairs:
            if set(old_pair) != {"item_ref", "condition_ref", "decision"}:
                raise FormalDesignError("history pair_decision schemaが不正です")
            pair = (
                _require_text(old_pair["item_ref"], "history item_ref"),
                _require_text(old_pair["condition_ref"], "history condition_ref"),
            )
            old_decision = old_pair["decision"]
            if (
                pair in seen_old_pairs
                or not isinstance(old_decision, str)
                or old_decision not in DECISIONS
            ):
                raise FormalDesignError("history pair decisionが重複または不正です")
            seen_old_pairs.add(pair)
            old_decision_by_pair[pair] = old_decision
        assignments = _rows(
            row["candidate_assignments"], "history.candidate_assignments"
        )
        assignment_ids: list[str] = []
        assigned_pairs: set[tuple[str, str]] = set()
        for assignment in assignments:
            if set(assignment) != {"candidate_ref", "item_ref", "condition_ref"}:
                raise FormalDesignError("history candidate assignment schemaが不正です")
            candidate_ref = _require_text(
                assignment["candidate_ref"], "history candidate_ref"
            )
            if not EXPECTED_RESULT_RE.fullmatch(candidate_ref):
                raise FormalDesignError("history candidate_ref形式が不正です")
            assignment_ids.append(candidate_ref)
            pair = (
                _require_text(assignment["item_ref"], "history assignment item_ref"),
                _require_text(
                    assignment["condition_ref"], "history assignment condition_ref"
                ),
            )
            if old_decision_by_pair.get(pair) != "adopted":
                raise FormalDesignError(
                    "history candidate assignmentは採用済みpairに属する必要があります"
                )
            assigned_pairs.add(pair)
            previous_pair = historical_candidate_pairs.get(candidate_ref)
            if previous_pair is not None and previous_pair != pair:
                raise FormalDesignError(
                    "過去のexpected-result candidate IDを別pairへ再利用しています"
                )
            historical_candidate_pairs[candidate_ref] = pair
        if assignment_ids != sorted(set(assignment_ids)):
            raise FormalDesignError(
                "history candidate_assignmentsはcandidate_ref順が必要です"
            )
        if set(assignment_ids) & set(historical_retirements):
            raise FormalDesignError(
                "過去にretiredとなったexpected-result candidate IDが再利用されています"
            )
        if any(
            decision == "adopted" and pair not in assigned_pairs
            for pair, decision in old_decision_by_pair.items()
        ):
            raise FormalDesignError(
                "historyの採用pairにはcandidate assignmentが必要です"
            )
        old_retirement_rows = _rows(
            row["retired_candidate_refs"], "history.retired_candidate_refs"
        )
        old_retirements: dict[str, str] = {}
        old_retirement_ids: list[str] = []
        for retired in old_retirement_rows:
            if set(retired) != {"candidate_ref", "reason"}:
                raise FormalDesignError(
                    "history retired_candidate_ref schemaが不正です"
                )
            candidate_ref = _require_text(
                retired["candidate_ref"], "history retired candidate_ref"
            )
            if (
                not EXPECTED_RESULT_RE.fullmatch(candidate_ref)
                or candidate_ref in old_retirements
            ):
                raise FormalDesignError(
                    "history retired candidate_ref形式または一意性が不正です"
                )
            old_retirement_ids.append(candidate_ref)
            old_retirements[candidate_ref] = _require_text(
                retired["reason"], "history retired candidate reason"
            )
        if old_retirement_ids != sorted(old_retirement_ids):
            raise FormalDesignError(
                "history retired_candidate_refsはcandidate_ref順が必要です"
            )
        removed_candidate_ids = previous_history_candidate_ids - set(assignment_ids)
        if not removed_candidate_ids <= set(old_retirements):
            raise FormalDesignError(
                "historyで削除されたexpected-result candidateにはretirement reasonが必要です"
            )
        if set(old_retirements) & set(assignment_ids):
            raise FormalDesignError(
                "history内のcurrent candidateを同時にretiredにできません"
            )
        if set(old_retirements) - set(historical_candidate_pairs):
            raise FormalDesignError(
                "未使用のexpected-result candidateをhistoryでretiredにできません"
            )
        if not set(historical_retirements) <= set(old_retirements):
            raise FormalDesignError(
                "historyから過去のcandidate retirementが失われています"
            )
        if any(
            old_retirements[candidate_ref] != reason
            for candidate_ref, reason in historical_retirements.items()
        ):
            raise FormalDesignError(
                "history内のcandidate retirement reasonが変化しています"
            )
        historical_retirements = old_retirements
        previous_history_candidate_ids = set(assignment_ids)
    if history_revisions != list(range(1, revision)):
        raise FormalDesignError("formal_design revision履歴が欠落しています")

    source_by_ref: dict[str, tuple[str, str]] = {}
    for index, row in enumerate(_rows(packet["source_refs"], "source_refs")):
        if set(row) != {"ref", "revision", "currentness"}:
            raise FormalDesignError(f"source_refs[{index}] schemaが不正です")
        ref = _require_text(row["ref"], "source ref")
        source_revision = _require_text(row["revision"], "source revision")
        currentness = row["currentness"]
        if (
            not isinstance(currentness, str)
            or currentness not in {"current", "stale", "unknown"}
            or ref in source_by_ref
        ):
            raise FormalDesignError("source refのcurrentnessまたは一意性が不正です")
        source_by_ref[ref] = (source_revision, currentness)

    items: dict[str, str] = {}
    for index, row in enumerate(_rows(packet["items"], "items")):
        if set(row) != {"item_ref", "source_ref"}:
            raise FormalDesignError(f"items[{index}] schemaが不正です")
        item_ref = _require_text(row["item_ref"], "item_ref")
        source_ref = _require_text(row["source_ref"], "item source_ref")
        if (
            not ITEM_RE.fullmatch(item_ref)
            or item_ref in items
            or source_ref not in source_by_ref
        ):
            raise FormalDesignError("test item refが不正または未知です")
        items[item_ref] = source_ref

    conditions: dict[str, str] = {}
    for index, row in enumerate(
        _rows(packet["condition_candidates"], "condition_candidates")
    ):
        if set(row) != {"condition_ref", "source_ref"}:
            raise FormalDesignError(f"condition_candidates[{index}] schemaが不正です")
        condition_ref = _require_text(row["condition_ref"], "condition_ref")
        source_ref = _require_text(row["source_ref"], "condition source_ref")
        if (
            not CONDITION_RE.fullmatch(condition_ref)
            or condition_ref in conditions
            or source_ref not in source_by_ref
        ):
            raise FormalDesignError("condition candidate refが不正または未知です")
        conditions[condition_ref] = source_ref

    authorities: dict[str, str] = {}
    for index, row in enumerate(_rows(packet["authorities"], "authorities")):
        if set(row) != {"authority_ref", "revision", "currentness"}:
            raise FormalDesignError(f"authorities[{index}] schemaが不正です")
        ref = _require_text(row["authority_ref"], "authority_ref")
        authority_revision = _require_text(row["revision"], "authority revision")
        currentness = row["currentness"]
        if (
            not isinstance(currentness, str)
            or currentness not in {"current", "stale", "unknown"}
            or ref in authorities
        ):
            raise FormalDesignError("Authority currentnessまたは一意性が不正です")
        if ref not in source_by_ref or source_by_ref[ref] != (
            authority_revision,
            currentness,
        ):
            raise FormalDesignError(
                "Authorityのrevision/currentnessがsource refsに一致しません"
            )
        authorities[ref] = currentness

    resolved_levels = resolve_item_test_levels(
        packet["test_level_evidence"], set(items), source_by_ref
    )
    drafts_by_key = {row.get("draft_key"): row for row in tcn_drafts}
    if len(drafts_by_key) != len(tcn_drafts):
        raise FormalDesignError("TCN draft_keyが重複しています")
    expected_pairs = {(item, condition) for item in items for condition in conditions}
    assessments: dict[tuple[str, str], dict[str, Any]] = {}
    projection: dict[str, dict[str, Any]] = {}
    current_candidate_pairs: dict[str, tuple[str, str]] = {}
    for index, row in enumerate(_rows(packet["pair_assessments"], "pair_assessments")):
        allowed = {
            "item_ref",
            "condition_ref",
            "decision",
            "rationale",
            "test_level",
            "tcn_draft_key",
            "expected_result_candidates",
            "covered_by_pair",
            "reopen_condition",
        }
        if set(row) != allowed:
            raise FormalDesignError(f"pair_assessments[{index}] schemaが不正です")
        pair = (
            _require_text(row["item_ref"], f"pair_assessments[{index}].item_ref"),
            _require_text(
                row["condition_ref"], f"pair_assessments[{index}].condition_ref"
            ),
        )
        if pair not in expected_pairs or pair in assessments:
            raise FormalDesignError("item × condition pairが未知または重複しています")
        if not isinstance(row["decision"], str) or row["decision"] not in DECISIONS:
            raise FormalDesignError("pair decisionが不正です")
        _require_text(row["rationale"], "pair rationale")
        level = _require_text(row["test_level"], "pair test_level")
        draft_key = row["tcn_draft_key"]
        candidates = _rows(
            row["expected_result_candidates"], "expected_result_candidates"
        )
        resolved_level = resolved_levels[pair[0]]
        if row["decision"] == "adopted":
            if level != resolved_level["level"]:
                raise FormalDesignError(
                    "採用pairのtest levelが優先順位の解決結果と不一致です"
                )
            draft_key = _require_text(draft_key, "adopted tcn_draft_key")
            if draft_key in projection:
                raise FormalDesignError("採用pairのTCN draft_keyが重複しています")
            if not candidates:
                raise FormalDesignError(
                    "採用pairにexpected result candidateがありません"
                )
            candidate_ids: list[str] = []
            candidate_rows: list[dict[str, Any]] = []
            for candidate_index, candidate in enumerate(candidates):
                candidate_fields = {
                    "candidate_ref",
                    "text",
                    "authority_refs",
                    "observation_method",
                    "side_effects",
                    "revision",
                }
                if set(candidate) != candidate_fields:
                    raise FormalDesignError(
                        f"expected result candidate {candidate_index} schemaが不正です"
                    )
                candidate_ref = _require_text(
                    candidate["candidate_ref"], "candidate_ref"
                )
                if not EXPECTED_RESULT_RE.fullmatch(candidate_ref):
                    raise FormalDesignError(
                        "expected result candidate_ref形式が不正です"
                    )
                if candidate_ref in candidate_ids:
                    raise FormalDesignError(
                        "expected result candidate_refが重複しています"
                    )
                candidate_ids.append(candidate_ref)
                if candidate_ref in current_candidate_pairs:
                    raise FormalDesignError(
                        "expected-result candidate IDを複数pairへ割り当てています"
                    )
                current_candidate_pairs[candidate_ref] = pair
                _require_text(candidate["text"], "expected result text")
                _require_text(candidate["observation_method"], "observation_method")
                _require_text(candidate["side_effects"], "side_effects")
                _require_text(candidate["revision"], "expected result revision")
                refs = candidate["authority_refs"]
                if (
                    not isinstance(refs, list)
                    or not refs
                    or not all(isinstance(ref, str) and ref for ref in refs)
                    or refs != sorted(set(refs))
                ):
                    raise FormalDesignError("expected result authority_refsが必要です")
                if any(ref not in authorities for ref in refs):
                    raise FormalDesignError(
                        "expected resultに未知のAuthority refがあります"
                    )
                candidate_rows.append(dict(candidate))
            if candidate_ids != sorted(candidate_ids):
                raise FormalDesignError(
                    "expected result candidatesはcandidate_ref順が必要です"
                )
            draft = drafts_by_key.get(draft_key)
            if draft is not None:
                if not set(draft["tr_refs"]):
                    raise FormalDesignError("採用pairのTCN draftにTRがありません")
                projection[draft_key] = {
                    "item_ref": pair[0],
                    "condition_ref": pair[1],
                    "formal_design_ref": design_ref,
                    "formal_design_revision": revision,
                    "expected_result_candidate_refs": sorted(candidate_ids),
                    "expected_result_candidates": candidate_rows,
                    "test_level": level,
                    "test_level_source": resolved_level["source"],
                    "test_level_source_ref": resolved_level["source_ref"],
                }
        elif draft_key is not None or candidates:
            raise FormalDesignError(
                "非採用pairがTCN draftまたはexpected resultを生成しています"
            )
        covered_by = row["covered_by_pair"]
        if row["decision"] == "duplicate":
            if not isinstance(covered_by, dict) or set(covered_by) != {
                "item_ref",
                "condition_ref",
            }:
                raise FormalDesignError("duplicate pairにはcovered_by_pairが必要です")
            covered_pair = (
                _require_text(covered_by["item_ref"], "covered_by_pair.item_ref"),
                _require_text(
                    covered_by["condition_ref"], "covered_by_pair.condition_ref"
                ),
            )
            if covered_pair == pair or covered_pair not in expected_pairs:
                raise FormalDesignError("covered_by_pairが別の既知pairではありません")
        elif covered_by is not None:
            raise FormalDesignError(
                "duplicate以外のpairにcovered_by_pairを指定できません"
            )
        if row["decision"] in {"unconfirmed", "blocked"}:
            _require_text(row["reopen_condition"], "reopen_condition")
        elif row["reopen_condition"] is not None:
            raise FormalDesignError(
                "未確認／blocked以外のpairにreopen_conditionを指定できません"
            )
        if row["decision"] == "other_test_level" and level == resolved_level["level"]:
            raise FormalDesignError("other_test_levelが解決済みlevelと同じです")
        assessments[pair] = row

    if set(assessments) != expected_pairs:
        missing = sorted(expected_pairs - set(assessments))
        raise FormalDesignError(
            f"item × condition populationのassessmentが不足しています: {missing}"
        )
    for pair, row in assessments.items():
        if row["decision"] == "duplicate":
            target = tuple(
                row["covered_by_pair"][key] for key in ("item_ref", "condition_ref")
            )
            if assessments[target]["decision"] != "adopted":
                raise FormalDesignError(
                    "duplicate covered_by_pairは採用済みpairを参照する必要があります"
                )
    for candidate_ref, pair in current_candidate_pairs.items():
        if candidate_ref in historical_retirements:
            raise FormalDesignError(
                "過去にretiredとなったexpected-result candidate IDは再利用できません"
            )
        if (
            candidate_ref in historical_candidate_pairs
            and historical_candidate_pairs[candidate_ref] != pair
        ):
            raise FormalDesignError(
                "expected-result candidate IDを別pairへ再利用しています"
            )
    retired_rows = _rows(packet["retired_candidate_refs"], "retired_candidate_refs")
    retired_ids: list[str] = []
    retired_by_id: dict[str, str] = {}
    for row in retired_rows:
        if set(row) != {"candidate_ref", "reason"}:
            raise FormalDesignError("retired_candidate_ref schemaが不正です")
        candidate_ref = _require_text(row["candidate_ref"], "retired candidate_ref")
        if not EXPECTED_RESULT_RE.fullmatch(candidate_ref):
            raise FormalDesignError("retired candidate_ref形式が不正です")
        reason = _require_text(row["reason"], "retired candidate reason")
        retired_ids.append(candidate_ref)
        retired_by_id[candidate_ref] = reason
    if retired_ids != sorted(set(retired_ids)):
        raise FormalDesignError(
            "retired_candidate_refsはcandidate_ref順の一意配列が必要です"
        )
    if set(retired_ids) & set(current_candidate_pairs):
        raise FormalDesignError(
            "current expected-result candidateをretiredにできません"
        )
    if set(retired_ids) - set(historical_candidate_pairs):
        raise FormalDesignError(
            "未使用のexpected-result candidate IDをretiredにできません"
        )
    if not (previous_history_candidate_ids - set(current_candidate_pairs)) <= set(
        retired_by_id
    ):
        raise FormalDesignError(
            "直前revisionから削除されたexpected-result candidateにはretirement reasonが必要です"
        )
    if not set(historical_retirements) <= set(retired_by_id):
        raise FormalDesignError(
            "current formal designから過去のcandidate retirementが失われています"
        )
    if any(
        retired_by_id[candidate_ref] != reason
        for candidate_ref, reason in historical_retirements.items()
    ):
        raise FormalDesignError(
            "current formal designで過去のcandidate retirement reasonが変化しています"
        )
    missing_retirement = sorted(
        set(historical_candidate_pairs)
        - set(current_candidate_pairs)
        - set(retired_ids)
    )
    if missing_retirement:
        raise FormalDesignError(
            "削除された過去expected-result candidateにはretirement reasonが必要です"
        )
    pair_stale_sources: dict[tuple[str, str], list[str]] = {}
    mapped_source_refs = set(items.values()) | set(conditions.values()) | {
        assignment["source_ref"] for assignment in resolved_levels.values()
    }
    for pair, row in assessments.items():
        source_refs = {
            items[pair[0]],
            conditions[pair[1]],
            resolved_levels[pair[0]]["source_ref"],
        }
        if row["decision"] == "adopted":
            authority_refs = {
                ref
                for candidate in row["expected_result_candidates"]
                for ref in candidate["authority_refs"]
            }
            draft = drafts_by_key.get(row["tcn_draft_key"])
            if draft is not None:
                draft_authorities = set(draft.get("authority_refs", []))
                if draft_authorities - set(authorities):
                    raise FormalDesignError(
                        "TCN draftにformal design外のAuthority refがあります"
                    )
                authority_refs.update(draft_authorities)
            mapped_source_refs.update(authority_refs)
            source_refs.update(authority_refs)
        pair_stale_sources[pair] = sorted(
            ref
            for ref in source_refs
            if source_by_ref[ref][1] != "current"
        )
    unmapped_stale_sources = {
        ref
        for ref, (_revision, currentness) in source_by_ref.items()
        if currentness != "current" and ref not in mapped_source_refs
    }
    if unmapped_stale_sources:
        # An unresolved source without a pair link cannot safely be ignored.
        # Conservatively block every pair until its dependency scope is explicit.
        for pair in pair_stale_sources:
            pair_stale_sources[pair] = sorted(
                set(pair_stale_sources[pair]) | unmapped_stale_sources
            )
    stale_pairs = {
        pair for pair, stale_refs in pair_stale_sources.items() if stale_refs
    }
    changed = True
    while changed:
        changed = False
        for pair, row in assessments.items():
            if row["decision"] != "duplicate" or pair in stale_pairs:
                continue
            target = tuple(
                row["covered_by_pair"][key] for key in ("item_ref", "condition_ref")
            )
            if target in stale_pairs:
                stale_pairs.add(pair)
                pair_stale_sources[pair] = sorted(
                    set(pair_stale_sources[pair]) | set(pair_stale_sources[target])
                )
                changed = True

    blocked_draft_keys = {
        row["tcn_draft_key"]
        for pair, row in assessments.items()
        if pair in stale_pairs
        and row["decision"] == "adopted"
        and row["tcn_draft_key"] in drafts_by_key
    }
    # A formal packet covers the full candidate matrix, while test_conditions may
    # be scoped to the current partial rerun. Missing drafts therefore remain
    # outside this generation scope; an in-scope TR without a TCN is still caught
    # by the existing closure check below.
    if set(projection) - blocked_draft_keys != set(drafts_by_key) - blocked_draft_keys:
        raise FormalDesignError("formal_designで対応しないTCN draftがあります")
    for draft_key in blocked_draft_keys:
        projection.pop(draft_key, None)

    unresolved_pairs = []
    for pair, row in sorted(assessments.items()):
        if row["decision"] in {"unconfirmed", "blocked"} or pair in stale_pairs:
            unresolved_pairs.append(
                {
                    "item_ref": pair[0],
                    "condition_ref": pair[1],
                    "decision": (
                        row["decision"]
                        if row["decision"] in {"unconfirmed", "blocked"}
                        else "blocked"
                    ),
                }
            )
    denominator = len(expected_pairs)
    closed = sum(
        row["decision"] not in {"unconfirmed", "blocked"} and pair not in stale_pairs
        for pair, row in assessments.items()
    )
    formal_design_record = dict(packet)
    formal_design_record["source_refs"] = sorted(
        (dict(row) for row in packet["source_refs"]), key=lambda row: row["ref"]
    )
    formal_design_record["items"] = sorted(
        (dict(row) for row in packet["items"]), key=lambda row: row["item_ref"]
    )
    formal_design_record["condition_candidates"] = sorted(
        (dict(row) for row in packet["condition_candidates"]),
        key=lambda row: row["condition_ref"],
    )
    formal_design_record["authorities"] = sorted(
        (dict(row) for row in packet["authorities"]),
        key=lambda row: row["authority_ref"],
    )
    formal_design_record["pair_assessments"] = [
        {
            **row,
            "expected_result_candidates": [
                dict(candidate) for candidate in row["expected_result_candidates"]
            ],
        }
        for _pair, row in sorted(assessments.items())
    ]
    formal_design_record["history"] = [
        {
            "revision": row["revision"],
            "change_reason": row["change_reason"],
            "pair_decisions": sorted(
                (dict(pair) for pair in row["pair_decisions"]),
                key=lambda pair: (pair["item_ref"], pair["condition_ref"]),
            ),
            "candidate_assignments": sorted(
                (dict(candidate) for candidate in row["candidate_assignments"]),
                key=lambda candidate: candidate["candidate_ref"],
            ),
            "retired_candidate_refs": sorted(
                (dict(candidate) for candidate in row["retired_candidate_refs"]),
                key=lambda candidate: candidate["candidate_ref"],
            ),
        }
        for row in history
    ]
    formal_design_record["retired_candidate_refs"] = sorted(
        (dict(row) for row in packet["retired_candidate_refs"]),
        key=lambda row: row["candidate_ref"],
    )
    if isinstance(packet["test_level_evidence"], dict):
        formal_design_record["test_level_evidence"] = {
            key: dict(value) if isinstance(value, dict) else value
            for key, value in packet["test_level_evidence"].items()
        }
    else:
        formal_design_record["test_level_evidence"] = [
            {
                "item_ref": row["item_ref"],
                "evidence": {
                    key: dict(value) if isinstance(value, dict) else value
                    for key, value in row["evidence"].items()
                },
            }
            for row in sorted(packet["test_level_evidence"], key=lambda row: row["item_ref"])
        ]
    projection["__blocked_draft_keys__"] = sorted(blocked_draft_keys)
    projection["__formal_design_record__"] = formal_design_record
    projection["__formal_design_summary__"] = {
        "design_ref": design_ref,
        "revision": revision,
        "pair_denominator": denominator,
        "pair_closed": closed,
        "pair_coverage": (
            f"{closed}/{denominator}"
            if denominator
            and packet["items_complete"]
            and packet["conditions_complete"]
            else None
        ),
        "pair_coverage_status": (
            "unknown_zero_denominator"
            if denominator == 0
            else "incomplete_population"
            if not packet["items_complete"] or not packet["conditions_complete"]
            else "incomplete"
            if unresolved_pairs
            else "complete"
        ),
        "unresolved_pairs": unresolved_pairs,
        "items_complete": packet["items_complete"],
        "conditions_complete": packet["conditions_complete"],
    }
    return projection


SKILL = "test-condition-design"
GENERATOR = "condition_structure"
GENERATOR_CONTRACT_VERSION = "condition-structure-v2"
SCRIPT_PATH = Path(__file__).resolve()
ADAPTER_TYPES = {"classification", "cause-effect", "schema", "ui"}
MODEL_TECHNIQUE = {
    "ep": "ep",
    "bva": "bva",
    "domain": "domain",
    "decision": "decision",
    "comb": "comb",
    "state": "state",
    "flow": "scenario",
    "crud": "crud",
    "syntax": "syntax",
    "random": "random",
    "metamorphic": "metamorphic",
    "error-guessing": "error-guessing",
}
ID_PATTERNS = {
    "tcn": re.compile(r"^TCN-(\d{3})$"),
    "model": re.compile(r"^([a-z][a-z0-9-]*)-(\d{3,})$"),
}


def _validate_id(value: Any, kind: str, name: str) -> str:
    if not isinstance(value, str) or ID_PATTERNS[kind].fullmatch(value) is None:
        raise InvalidInput(f"{name}の形式が不正です")
    return value


def _unique_strings(value: Any, name: str) -> list[str]:
    rows = ensure_list(value, name)
    if not all(isinstance(row, str) and row for row in rows):
        raise InvalidInput(f"{name}は非空stringのarrayである必要があります")
    if len(set(rows)) != len(rows):
        raise InvalidInput(f"{name}が重複しています")
    return rows


def _scope_refs(value: Any, name: str) -> list[str]:
    refs = _unique_strings(value, name)
    if any(SCOPE_ID_RE.fullmatch(ref) is None for ref in refs):
        raise InvalidInput(f"{name}に不正なScope IDがあります")
    if refs != sorted(refs):
        raise InvalidInput(f"{name}はcanonical sort済みである必要があります")
    return refs


def _validate_state_rows(rows: Any, kind: str) -> list[dict[str, Any]]:
    values = ensure_list(rows, f"previous_{kind}_ids")
    result = []
    seen: set[str] = set()
    if kind == "tcn":
        allowed = {"tcn_id", "status", "scope_refs"}
        for index, row in enumerate(values):
            if not isinstance(row, dict):
                raise InvalidInput(f"previous_tcn_ids[{index}]が不正です")
            reject_unknown(row, allowed)
            ref = _validate_id(
                row["tcn_id"], "tcn", f"previous_tcn_ids[{index}].tcn_id"
            )
            scope_refs = _scope_refs(
                row["scope_refs"], f"previous_tcn_ids[{index}].scope_refs"
            )
            if row["status"] not in {"active", "inactive", "deleted"} or ref in seen:
                raise InvalidInput("previous_tcn_idsのidentity/statusが不正です")
            seen.add(ref)
            result.append(
                {"tcn_id": ref, "status": row["status"], "scope_refs": scope_refs}
            )
    else:
        allowed = {
            "model_key",
            "model_type",
            "technique_slug",
            "parent_tcn_id",
            "selection_source",
            "selection_key",
            "derived_from_model_key",
            "status",
            "scope_refs",
        }
        for index, row in enumerate(values):
            if not isinstance(row, dict):
                raise InvalidInput(f"previous_model_keys[{index}]が不正です")
            reject_unknown(row, allowed)
            ref = _validate_id(
                row["model_key"], "model", f"previous_model_keys[{index}].model_key"
            )
            _validate_model_metadata(row, f"previous_model_keys[{index}]")
            scope_refs = _scope_refs(
                row["scope_refs"], f"previous_model_keys[{index}].scope_refs"
            )
            _validate_id(
                row["parent_tcn_id"],
                "tcn",
                f"previous_model_keys[{index}].parent_tcn_id",
            )
            if row["status"] not in {"active", "inactive", "deleted"} or ref in seen:
                raise InvalidInput("previous_model_keysのidentity/statusが不正です")
            seen.add(ref)
            result.append(canonicalize({**row, "scope_refs": scope_refs}))
    return result


def _inactive_ids(rows: Any, name: str, kind: str) -> list[str]:
    refs = _unique_strings(rows, name)
    for ref in refs:
        _validate_id(ref, kind, name)
    if refs != sorted(refs):
        raise InvalidInput(f"{name}はcanonical sort済みである必要があります")
    return refs


def _inactive_entity_history(
    rows: Any, entity_type: str, id_field: str
) -> dict[str, dict[str, Any]]:
    result = {}
    order = []
    for index, raw_entity in enumerate(
        ensure_list(rows, f"inactive_{entity_type}_history")
    ):
        entity = validate_machine_entity(raw_entity, expected_skill=SKILL)
        ref = entity["entity_ref"]
        scope_refs = entity["content"].get("scope_refs")
        if (
            entity["entity_type"] != entity_type
            or ref in result
            or entity["content"].get(id_field) != ref
            or not isinstance(scope_refs, list)
        ):
            raise InvalidInput(f"inactive_{entity_type}_history[{index}]が不正です")
        _scope_refs(scope_refs, f"inactive_{entity_type}_history[{index}].scope_refs")
        result[ref] = entity
        order.append(ref)
    if order != sorted(order):
        raise InvalidInput(
            f"inactive_{entity_type}_historyはidentity順である必要があります"
        )
    return result


def _inactive_materialize_history(rows: Any) -> dict[str, dict[str, Any]]:
    result = {}
    order = []
    required = {
        "tcn_id",
        "ci_entities",
        "ci_id_state",
        "target_mapping_state",
        "semantic_ci_mapping_state",
        "expected_result_root_state",
    }
    for index, row in enumerate(ensure_list(rows, "inactive_materialize_history")):
        if not isinstance(row, dict) or set(row) != required:
            raise InvalidInput(
                f"inactive_materialize_history[{index}] schemaが不正です"
            )
        tcn_id = _validate_id(
            row["tcn_id"], "tcn", "inactive_materialize_history.tcn_id"
        )
        if tcn_id in result:
            raise InvalidInput("inactive_materialize_history.tcn_idが重複しています")
        ci_entities = []
        seen_ci = set()
        for raw_entity in ensure_list(
            row["ci_entities"], "inactive_materialize_history.ci_entities"
        ):
            entity = validate_machine_entity(raw_entity, expected_skill=SKILL)
            if entity["entity_type"] != "ci" or not entity["entity_ref"].startswith(
                tcn_id + "-"
            ):
                raise InvalidInput(
                    "inactive_materialize_history.ci_entities identityが不正です"
                )
            if entity["entity_ref"] in seen_ci:
                raise InvalidInput(
                    "inactive_materialize_history.ci_entitiesが重複しています"
                )
            seen_ci.add(entity["entity_ref"])
            ci_entities.append(entity)
        ci_entities.sort(key=lambda entity: entity["entity_ref"])
        ci_state = ensure_list(
            row["ci_id_state"], "inactive_materialize_history.ci_id_state"
        )
        for state in ci_state:
            if not isinstance(state, dict) or set(state) != {
                "ci_id",
                "status",
                "scope_refs",
            }:
                raise InvalidInput(
                    "inactive_materialize_history.ci_id_state rowが不正です"
                )
            if state["status"] not in {"active", "inactive", "deleted"}:
                raise InvalidInput(
                    "inactive_materialize_history.ci_id_state statusが不正です"
                )
            _scope_refs(
                state["scope_refs"],
                "inactive_materialize_history.ci_id_state.scope_refs",
            )
            ci_id = state["ci_id"]
            if not isinstance(ci_id, str) or not ci_id.startswith(tcn_id + "-"):
                raise InvalidInput(
                    "inactive_materialize_history.ci_id_state ownerが不正です"
                )
        normalized = canonicalize({**row, "ci_entities": ci_entities})
        result[tcn_id] = normalized
        order.append(tcn_id)
    if order != sorted(order):
        raise InvalidInput("inactive_materialize_historyはtcn_id順である必要があります")
    return result


def _validate_model_metadata(row: dict[str, Any], name: str) -> None:
    model_key = row.get("model_key")
    model_type = row.get("model_type")
    _validate_id(model_key, "model", f"{name}.model_key")
    if model_type not in MODEL_TYPES or not str(model_key).startswith(model_type + "-"):
        raise InvalidInput(f"{name}.model_type / model_keyが不一致です")
    technique_slug = row.get("technique_slug")
    selection_source = row.get("selection_source")
    selection_key = row.get("selection_key")
    derived = row.get("derived_from_model_key")
    if model_type in ADAPTER_TYPES:
        if any(
            value is not None
            for value in (technique_slug, selection_source, selection_key, derived)
        ):
            raise InvalidInput(f"{name}のadapter metadataが不正です")
    else:
        if (
            technique_slug != MODEL_TECHNIQUE.get(model_type)
            or technique_slug not in TECHNIQUE_SLUGS
        ):
            raise InvalidInput(f"{name}.technique_slugが不正です")
        if selection_source not in {"analysis", "condition_design", "user"}:
            raise InvalidInput(f"{name}.selection_sourceが不正です")
        if selection_source == "analysis":
            ensure_nonempty_string(selection_key, f"{name}.selection_key")
        elif selection_key is not None:
            raise InvalidInput(f"{name}.selection_keyはnullである必要があります")
    if derived is not None:
        _validate_id(derived, "model", f"{name}.derived_from_model_key")


def _validate_tr_rows(rows: Any) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for index, row in enumerate(ensure_list(rows, "test_requirements")):
        if not isinstance(row, dict):
            raise InvalidInput(f"test_requirements[{index}]が不正です")
        reject_unknown(
            row,
            {"tr_id", "priority", "authority_refs", "risk_refs", "scope_refs"},
            {"test_level", "test_level_source", "test_level_source_ref"},
        )
        tr_id = row.get("tr_id")
        if not isinstance(tr_id, str) or TR_ID_RE.fullmatch(tr_id) is None:
            raise InvalidInput(f"test_requirements[{index}].tr_idの形式が不正です")
        if tr_id in result:
            raise InvalidInput("test_requirements.tr_idが重複しています")
        for field in ("authority_refs", "risk_refs"):
            _unique_strings(row.get(field), f"test_requirements[{index}].{field}")
        _scope_refs(row.get("scope_refs"), f"test_requirements[{index}].scope_refs")
        result[tr_id] = canonicalize(row)
    return result


def _validate_selection_rows(rows: Any) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for index, row in enumerate(ensure_list(rows, "technique_selections")):
        if not isinstance(row, dict):
            raise InvalidInput(f"technique_selections[{index}]が不正です")
        required = {
            "selection_key",
            "selected_techniques",
            "undetermined_signal_closures",
            "status",
        }
        reject_unknown(row, required)
        key = ensure_nonempty_string(
            row["selection_key"], f"technique_selections[{index}].selection_key"
        )
        if key in result:
            raise InvalidInput("selection_keyが重複しています")
        selected = _unique_strings(
            row["selected_techniques"],
            f"technique_selections[{index}].selected_techniques",
        )
        if any(value not in TECHNIQUE_SLUGS for value in selected):
            raise InvalidInput("selected_techniquesに未知のtechnique slugがあります")
        closures = ensure_list(
            row["undetermined_signal_closures"],
            f"technique_selections[{index}].undetermined_signal_closures",
        )
        if row["status"] not in {"active", "blocked", "unresolved"}:
            raise InvalidInput("technique selection statusが不正です")
        if row["status"] == "active":
            for closure in closures:
                if (
                    not isinstance(closure, dict)
                    or closure.get("handling") != "selection_not_affected"
                    or not closure.get("reason")
                    or closure.get("question_id") is not None
                ):
                    raise InvalidInput(
                        "active technique selectionのsignal closureが不正です"
                    )
        result[key] = canonicalize(row)
    return result


def _validate_dispositions(
    rows: Any, current_entities: list[dict], input_mode: str
) -> list[tuple[dict, list[dict[str, str]]]]:
    result: list[tuple[dict, list[dict[str, str]]]] = []
    disposed: set[str] = set()
    for index, row in enumerate(ensure_list(rows, "requirement_dispositions")):
        normalized, dependencies = normalize_machine_entity_disposition(
            row,
            current_entities,
            allowed_handlings={
                "対象外",
                "別テストレベル",
                "残存リスク",
                "ブロック中",
                "重複",
            },
            allowed_upstream_entity_types={"tr"},
            input_mode=input_mode,
        )
        upstream = normalized["upstream_entity"]
        if upstream["skill"] != "test-requirement-design":
            raise InvalidInput(
                "condition structure disposition upstream_entity skill/typeが不一致です"
            )
        tr_id = ensure_nonempty_string(
            upstream["entity_ref"], "requirement disposition tr_id"
        )
        if tr_id in disposed:
            raise InvalidInput("同じTRへのdispositionが重複しています")
        disposed.add(tr_id)
        result.append((normalized, dependencies))
    return result


def _validate_tcn_drafts(rows: Any) -> list[dict[str, Any]]:
    result = []
    seen: set[str] = set()
    required = {
        "draft_key",
        "identity_action",
        "reuse_id",
        "tr_refs",
        "condition",
        "category",
        "technique_slugs",
        "coverage_criterion",
        "authority_refs",
        "risk_refs",
        "priority",
        "priority_override_reason",
    }
    for index, row in enumerate(ensure_list(rows, "test_conditions")):
        if not isinstance(row, dict):
            raise InvalidInput(f"test_conditions[{index}]が不正です")
        reject_unknown(
            row,
            required,
            {
                "item_ref",
                "condition_ref",
                "formal_design_ref",
                "formal_design_revision",
                "expected_result_candidate_refs",
                "test_level",
                "test_level_source",
                "test_level_source_ref",
            },
        )
        key = ensure_nonempty_string(
            row["draft_key"], f"test_conditions[{index}].draft_key"
        )
        if key in seen:
            raise InvalidInput("TCN draft_keyが重複しています")
        seen.add(key)
        if row["identity_action"] not in {"reuse", "new"}:
            raise InvalidInput("TCN identity_actionが不正です")
        if row["identity_action"] == "reuse":
            _validate_id(row["reuse_id"], "tcn", f"test_conditions[{index}].reuse_id")
        elif row["reuse_id"] is not None:
            raise InvalidInput("new TCNのreuse_idはnullである必要があります")
        _unique_strings(row["tr_refs"], f"test_conditions[{index}].tr_refs")
        ensure_nonempty_string(row["condition"], f"test_conditions[{index}].condition")
        if row["category"] is not None:
            ensure_nonempty_string(
                row["category"], f"test_conditions[{index}].category"
            )
        techniques = _unique_strings(
            row["technique_slugs"], f"test_conditions[{index}].technique_slugs"
        )
        if any(value not in TECHNIQUE_SLUGS for value in techniques):
            raise InvalidInput("TCN technique_slugsに未知のslugがあります")
        ensure_nonempty_string(
            row["coverage_criterion"], f"test_conditions[{index}].coverage_criterion"
        )
        _unique_strings(
            row["authority_refs"], f"test_conditions[{index}].authority_refs"
        )
        _unique_strings(row["risk_refs"], f"test_conditions[{index}].risk_refs")
        if not isinstance(row["priority"], (str, int)) or isinstance(
            row["priority"], bool
        ):
            raise InvalidInput("TCN priorityが不正です")
        if row["priority_override_reason"] is not None and not isinstance(
            row["priority_override_reason"], str
        ):
            raise InvalidInput("TCN priority_override_reasonが不正です")
        normalized = canonicalize(row)
        optional_refs = (
            "item_ref",
            "condition_ref",
            "formal_design_ref",
            "test_level",
            "test_level_source",
            "test_level_source_ref",
        )
        for field in optional_refs:
            if field in normalized:
                ensure_nonempty_string(normalized[field], f"test_conditions.{field}")
        if "formal_design_revision" in normalized and (
            not isinstance(normalized["formal_design_revision"], int)
            or isinstance(normalized["formal_design_revision"], bool)
            or normalized["formal_design_revision"] < 1
        ):
            raise InvalidInput("formal_design_revisionが不正です")
        if "expected_result_candidate_refs" in normalized:
            candidate_refs = _unique_strings(
                normalized["expected_result_candidate_refs"],
                "expected_result_candidate_refs",
            )
            if not candidate_refs or candidate_refs != sorted(candidate_refs):
                raise InvalidInput("expected_result_candidate_refsが不正です")
        result.append(normalized)
    return result


def _validate_model_drafts(rows: Any) -> list[dict[str, Any]]:
    result = []
    seen: set[str] = set()
    required = {
        "draft_key",
        "model_type",
        "technique_slug",
        "selection_source",
        "selection_key",
        "derived_from_model_draft_key",
        "identity_action",
        "reuse_model_key",
        "parent_tcn_draft_key",
    }
    for index, row in enumerate(ensure_list(rows, "models")):
        if not isinstance(row, dict):
            raise InvalidInput(f"models[{index}]が不正です")
        reject_unknown(row, required)
        draft_key = ensure_nonempty_string(
            row["draft_key"], f"models[{index}].draft_key"
        )
        if draft_key in seen:
            raise InvalidInput("model draft_keyが重複しています")
        seen.add(draft_key)
        if row["model_type"] not in MODEL_TYPES:
            raise InvalidInput("model_typeが不正です")
        if row["identity_action"] not in {"reuse", "new"}:
            raise InvalidInput("model identity_actionが不正です")
        if row["identity_action"] == "reuse":
            _validate_id(
                row["reuse_model_key"], "model", f"models[{index}].reuse_model_key"
            )
        elif row["reuse_model_key"] is not None:
            raise InvalidInput("new modelのreuse_model_keyはnullである必要があります")
        ensure_nonempty_string(
            row["parent_tcn_draft_key"], f"models[{index}].parent_tcn_draft_key"
        )
        if row["derived_from_model_draft_key"] is not None:
            ensure_nonempty_string(
                row["derived_from_model_draft_key"],
                f"models[{index}].derived_from_model_draft_key",
            )
        metadata = {
            "model_key": row["reuse_model_key"] or f"{row['model_type']}-000",
            "model_type": row["model_type"],
            "technique_slug": row["technique_slug"],
            "selection_source": row["selection_source"],
            "selection_key": row["selection_key"],
            "derived_from_model_key": None,
        }
        if row["identity_action"] == "reuse":
            _validate_model_metadata(metadata, f"models[{index}]")
        else:
            if row["model_type"] in ADAPTER_TYPES:
                if any(
                    row[field] is not None
                    for field in ("technique_slug", "selection_source", "selection_key")
                ):
                    raise InvalidInput("adapter draft metadataが不正です")
            else:
                if (
                    row["technique_slug"] != MODEL_TECHNIQUE.get(row["model_type"])
                    or row["technique_slug"] not in TECHNIQUE_SLUGS
                ):
                    raise InvalidInput("Coverage model draftのtechnique_slugが不正です")
                if row["selection_source"] not in {
                    "analysis",
                    "condition_design",
                    "user",
                }:
                    raise InvalidInput(
                        "Coverage model draftのselection_sourceが不正です"
                    )
                if row["selection_source"] == "analysis":
                    ensure_nonempty_string(
                        row["selection_key"], f"models[{index}].selection_key"
                    )
                elif row["selection_key"] is not None:
                    raise InvalidInput(
                        "analysis以外のselection_keyはnullである必要があります"
                    )
        result.append(canonicalize(row))
    return result


def _allocate(
    prefix: str, used: set[str], minimum: int, maximum: int | None = None
) -> str:
    candidate = allocate_stable_id(prefix, used, minimum=minimum, maximum=maximum)
    used.add(candidate)
    return candidate


def _build(input_value: dict[str, Any], metadata: dict[str, Any]) -> dict[str, Any]:
    reject_unknown(
        input_value,
        {
            "test_requirements",
            "technique_selections",
            "test_conditions",
            "requirement_dispositions",
            "models",
            "previous_tcn_ids",
            "previous_model_keys",
            "update_scope_tcn_ids",
            "update_scope_model_keys",
            "inactive_tcn_ids",
            "inactive_model_keys",
            "inactive_tcn_history",
            "inactive_model_history",
            "inactive_materialize_history",
            "zero_scope_terminal",
        },
        {"legacy_tcn_ids", "formal_design"},
    )
    current_entities = validate_upstream_entities(metadata)
    tr_rows = _validate_tr_rows(input_value["test_requirements"])
    current_tr_entities = {
        entity["entity_ref"]: entity
        for entity in current_entities
        if entity["skill"] == "test-requirement-design"
        and entity["entity_type"] == "tr"
    }
    for tr_id, row in tr_rows.items():
        entity = current_tr_entities.get(tr_id)
        if entity is None:
            if metadata["input_mode"] == "artifact":
                raise InvalidInput(
                    "artifact mode test_requirementsにcurrent TR Entityがありません"
                )
            continue
        if (
            entity["content"].get("tr_id") != tr_id
            or entity["content"].get("scope_refs") != row["scope_refs"]
        ):
            raise InvalidInput(
                "test_requirements.scope_refsがcurrent TR Entityと一致しません"
            )
        for field in ("test_level", "test_level_source", "test_level_source_ref"):
            if field in row and entity["content"].get(field) != row[field]:
                raise InvalidInput(
                    f"test_requirements.{field}がcurrent TR Entityと一致しません"
                )
    selections = _validate_selection_rows(input_value["technique_selections"])
    disposition_rows = _validate_dispositions(
        input_value["requirement_dispositions"],
        current_entities,
        metadata["input_mode"],
    )
    disposed_trs = {
        row["upstream_entity"]["entity_ref"] for row, _deps in disposition_rows
    }
    tcn_drafts = _validate_tcn_drafts(input_value["test_conditions"])
    formal_projection = {}
    formal_design_summary = None
    formal_design_record = None
    if "formal_design" in input_value:
        try:
            formal_projection = validate_formal_design(
                input_value["formal_design"], tcn_drafts
            )
        except ValueError as exc:
            raise InvalidInput(str(exc)) from exc
        formal_design_summary = formal_projection.pop("__formal_design_summary__")
        formal_design_record = formal_projection.pop("__formal_design_record__")
        blocked_tcn_draft_keys = set(
            formal_projection.pop("__blocked_draft_keys__", [])
        )
        for draft in tcn_drafts:
            if draft["draft_key"] in blocked_tcn_draft_keys:
                continue
            draft.update(formal_projection[draft["draft_key"]])
            for tr_ref in draft["tr_refs"]:
                tr_row = tr_rows.get(tr_ref)
                if tr_row is None:
                    continue
                if (
                    tr_row.get("test_level") != draft["test_level"]
                    or tr_row.get("test_level_source")
                    != draft["test_level_source"]
                    or tr_row.get("test_level_source_ref")
                    != draft["test_level_source_ref"]
                ):
                    raise InvalidInput(
                        "formal TCNのtest levelがcurrent TR assignmentと一致しません"
                    )
        tcn_drafts = [
            draft
            for draft in tcn_drafts
            if draft["draft_key"] not in blocked_tcn_draft_keys
        ]
    model_drafts = _validate_model_drafts(input_value["models"])
    if "formal_design" in input_value:
        model_drafts = [
            draft
            for draft in model_drafts
            if draft["parent_tcn_draft_key"] not in blocked_tcn_draft_keys
        ]
    previous_tcn = _validate_state_rows(input_value["previous_tcn_ids"], "tcn")
    previous_models = _validate_state_rows(input_value["previous_model_keys"], "model")
    inactive_tcn_ids = set(
        _inactive_ids(input_value["inactive_tcn_ids"], "inactive_tcn_ids", "tcn")
    )
    inactive_model_keys = set(
        _inactive_ids(
            input_value["inactive_model_keys"], "inactive_model_keys", "model"
        )
    )
    inactive_tcn_history = _inactive_entity_history(
        input_value["inactive_tcn_history"], "tcn", "tcn_id"
    )
    inactive_model_history = _inactive_entity_history(
        input_value["inactive_model_history"], "model", "model_key"
    )
    inactive_materialize_history = _inactive_materialize_history(
        input_value["inactive_materialize_history"]
    )
    if not isinstance(input_value["zero_scope_terminal"], bool):
        raise InvalidInput("zero_scope_terminalはbooleanである必要があります")
    zero_scope_terminal = input_value["zero_scope_terminal"]
    update_tcn = set(
        _unique_strings(input_value["update_scope_tcn_ids"], "update_scope_tcn_ids")
    )
    update_model = set(
        _unique_strings(
            input_value["update_scope_model_keys"], "update_scope_model_keys"
        )
    )
    for ref in update_tcn:
        _validate_id(ref, "tcn", "update_scope_tcn_ids")
    for ref in update_model:
        _validate_id(ref, "model", "update_scope_model_keys")
    previous_tcn_map = {row["tcn_id"]: row for row in previous_tcn}
    previous_model_map = {row["model_key"]: row for row in previous_models}
    legacy = input_value.get("legacy_tcn_ids")
    if legacy is not None:
        seeded = seed_legacy_ids(legacy, TCN_ID_RE, "legacy_tcn_ids")
        _ = [row["id"] for row in seeded]
        if (
            metadata["input_mode"] != "direct"
            or previous_tcn
            or previous_models
            or update_model
            or update_tcn
        ):
            raise InvalidInput("legacy_tcn_idsは初回direct昇格でのみ使用できます")
        for row in seeded:
            previous_tcn_map[row["id"]] = {
                "tcn_id": row["id"],
                "status": row["status"],
                "scope_refs": [],
            }
            update_tcn.add(row["id"])
        previous_tcn = sorted(previous_tcn_map.values(), key=lambda row: row["tcn_id"])
    for ref in update_tcn:
        if ref not in previous_tcn_map or previous_tcn_map[ref]["status"] not in {
            "active",
            "inactive",
        }:
            raise InvalidInput(
                "update_scope_tcn_idsがactive previous stateを参照していません"
            )
    for ref in update_model:
        if ref not in previous_model_map or previous_model_map[ref]["status"] not in {
            "active",
            "inactive",
        }:
            raise InvalidInput(
                "update_scope_model_keysがactive previous stateを参照していません"
            )

    if inactive_tcn_ids & update_tcn or any(
        previous_tcn_map.get(ref, {}).get("status") != "active"
        for ref in inactive_tcn_ids
    ):
        raise InvalidInput(
            "inactive_tcn_idsはupdate scope外のactive previous TCNだけを指定できます"
        )
    if inactive_model_keys & update_model or any(
        previous_model_map.get(ref, {}).get("status") != "active"
        for ref in inactive_model_keys
    ):
        raise InvalidInput(
            "inactive_model_keysはupdate scope外のactive previous modelだけを指定できます"
        )
    expected_inactive_tcn_history = {
        row["tcn_id"] for row in previous_tcn if row["status"] == "inactive"
    } | inactive_tcn_ids
    expected_inactive_model_history = {
        row["model_key"] for row in previous_models if row["status"] == "inactive"
    } | inactive_model_keys
    if set(inactive_tcn_history) != expected_inactive_tcn_history:
        raise InvalidInput(
            "inactive_tcn_historyがprevious inactive stateと一致しません"
        )
    if set(inactive_model_history) != expected_inactive_model_history:
        raise InvalidInput(
            "inactive_model_historyがprevious inactive stateと一致しません"
        )
    if zero_scope_terminal and (
        tcn_drafts
        or model_drafts
        or tr_rows
        or selections
        or disposition_rows
        or inactive_tcn_ids
        or inactive_model_keys
        or update_tcn
        != {
            row["tcn_id"]
            for row in previous_tcn
            if row["status"] in {"active", "inactive"}
        }
        or update_model
        != {
            row["model_key"]
            for row in previous_models
            if row["status"] in {"active", "inactive"}
        }
    ):
        raise InvalidInput(
            "zero_scope_terminalはcurrent inputを空にして全previous active / inactive IDを閉じる場合だけ許可されます"
        )

    used_tcn = set(previous_tcn_map)
    tcn_mapping: dict[str, str] = {}
    reused_tcn: set[str] = set()
    for draft in sorted(tcn_drafts, key=lambda row: row["draft_key"]):
        if draft["identity_action"] == "reuse":
            ref = draft["reuse_id"]
            if (
                ref not in update_tcn
                or ref in reused_tcn
                or previous_tcn_map.get(ref, {}).get("status")
                not in {"active", "inactive"}
            ):
                raise InvalidInput("TCN reuse対象がscope内activeではありません")
            reused_tcn.add(ref)
        else:
            previous_numbers = [
                int(match.group(1))
                for value in used_tcn
                if (match := ID_PATTERNS["tcn"].fullmatch(value))
            ]
            ref = _allocate("TCN", used_tcn, max(previous_numbers, default=0) + 1, 999)
        tcn_mapping[draft["draft_key"]] = ref

    current_scope_by_tcn = {
        tcn_mapping[draft["draft_key"]]: sorted(
            {
                scope_ref
                for tr_id in draft["tr_refs"]
                for scope_ref in tr_rows.get(tr_id, {}).get("scope_refs", [])
            }
        )
        for draft in tcn_drafts
    }

    model_mapping: dict[str, str] = {}
    model_metadata: dict[str, dict[str, Any]] = {}
    used_models = set(previous_model_map)
    reused_models: set[str] = set()
    for draft in sorted(
        model_drafts,
        key=lambda row: (
            row["parent_tcn_draft_key"],
            0 if row["model_type"] in ADAPTER_TYPES else 1,
            row["model_type"],
            row["draft_key"],
        ),
    ):
        model_type = draft["model_type"]
        parent_tcn = tcn_mapping.get(draft["parent_tcn_draft_key"])
        if parent_tcn is None:
            raise InvalidInput("model draftのparent_tcn_draft_keyが不明です")
        previous = None
        if draft["identity_action"] == "reuse":
            ref = draft["reuse_model_key"]
            if (
                ref not in update_model
                or ref in reused_models
                or previous_model_map.get(ref, {}).get("status")
                not in {"active", "inactive"}
            ):
                raise InvalidInput("model reuse対象がscope内activeではありません")
            previous = previous_model_map[ref]
            if any(
                previous[field] != draft[field]
                for field in (
                    "model_type",
                    "technique_slug",
                    "selection_source",
                    "selection_key",
                )
            ):
                raise InvalidInput("reuse model metadataがprevious stateと不一致です")
            if previous["parent_tcn_id"] != parent_tcn:
                raise InvalidInput(
                    "reuse modelのparent TCNがprevious stateと不一致です"
                )
            reused_models.add(ref)
        else:
            numbers = [
                int(match.group(2))
                for value in used_models
                if (match := ID_PATTERNS["model"].fullmatch(value))
                and match.group(1) == model_type
            ]
            ref = _allocate(model_type, used_models, max(numbers, default=0) + 1)
        derived_from = None
        if draft["derived_from_model_draft_key"] is not None:
            parent_draft = next(
                (
                    row
                    for row in model_drafts
                    if row["draft_key"] == draft["derived_from_model_draft_key"]
                ),
                None,
            )
            if (
                parent_draft is None
                or parent_draft["model_type"] not in ADAPTER_TYPES
                or parent_draft["parent_tcn_draft_key"] != draft["parent_tcn_draft_key"]
            ):
                raise InvalidInput(
                    "derived_from_model_draft_keyが同一TCNのadapterを参照していません"
                )
            if parent_draft["draft_key"] == draft["draft_key"]:
                raise InvalidInput("modelが自己参照しています")
            derived_from = model_mapping.get(parent_draft["draft_key"])
            if derived_from is None:
                raise InvalidInput("adapter modelの確定順序が不正です")
        if previous is not None and previous["derived_from_model_key"] != derived_from:
            raise InvalidInput(
                "reuse modelのderived_from_model_keyがprevious stateと不一致です"
            )
        metadata_row = {
            "model_key": ref,
            "model_type": model_type,
            "technique_slug": draft["technique_slug"],
            "parent_tcn_id": parent_tcn,
            "selection_source": draft["selection_source"],
            "selection_key": draft["selection_key"],
            "derived_from_model_key": derived_from,
            "scope_refs": current_scope_by_tcn[parent_tcn],
            "status": "active",
        }
        model_mapping[draft["draft_key"]] = ref
        model_metadata[ref] = metadata_row

    violations: list[dict[str, Any]] = []
    linked_trs: set[str] = set()
    for draft in tcn_drafts:
        for tr_id in draft["tr_refs"]:
            if tr_id not in tr_rows:
                violations.append(
                    {
                        "target_key": f"violation:unknown-tr:{tr_id}",
                        "issue_type": "unknown_reference",
                        "entity_ref": tr_id,
                    }
                )
            else:
                linked_trs.add(tr_id)
    for tr_id in sorted(set(tr_rows) | linked_trs | disposed_trs):
        if tr_id in linked_trs and tr_id in disposed_trs:
            violations.append(
                {
                    "target_key": f"violation:linked-disposed:{tr_id}",
                    "issue_type": "linked_and_disposed",
                    "entity_ref": tr_id,
                }
            )
        elif tr_id not in linked_trs and tr_id not in disposed_trs:
            violations.append(
                {
                    "target_key": f"violation:unclosed-tr:{tr_id}",
                    "issue_type": "unclosed_reference",
                    "entity_ref": tr_id,
                }
            )
    tcn_draft_by_key = {row["draft_key"]: row for row in tcn_drafts}
    models_by_tcn: dict[str, set[str]] = {key: set() for key in tcn_draft_by_key}
    for draft in model_drafts:
        if draft["technique_slug"] is not None:
            models_by_tcn[draft["parent_tcn_draft_key"]].add(draft["technique_slug"])
        if draft["selection_source"] == "analysis":
            selection = selections.get(draft["selection_key"])
            if (
                selection is None
                or draft["technique_slug"] not in selection["selected_techniques"]
            ):
                violations.append(
                    {
                        "target_key": f"violation:selection:{draft['draft_key']}",
                        "issue_type": "selection_not_reached",
                        "entity_ref": draft["draft_key"],
                    }
                )
    for draft in tcn_drafts:
        if set(draft["technique_slugs"]) != models_by_tcn[draft["draft_key"]]:
            violations.append(
                {
                    "target_key": f"violation:techniques:{draft['draft_key']}",
                    "issue_type": "technique_set_mismatch",
                    "entity_ref": draft["draft_key"],
                }
            )
    for selection in selections.values():
        if selection["status"] != "active":
            continue
        reached = {
            row["technique_slug"]
            for row in model_metadata.values()
            if row["selection_source"] == "analysis"
            and row["selection_key"] == selection["selection_key"]
        }
        for slug in selection["selected_techniques"]:
            if slug not in reached:
                violations.append(
                    {
                        "target_key": f"violation:selection-unreached:{selection['selection_key']}:{slug}",
                        "issue_type": "selection_not_reached",
                        "entity_ref": selection["selection_key"],
                    }
                )

    tcn_entities: dict[str, dict[str, Any]] = {}
    _ = {
        (row["skill"], row["entity_type"], row["entity_ref"]): row
        for row in current_entities
    }
    for draft in tcn_drafts:
        tcn_id = tcn_mapping[draft["draft_key"]]
        content = {
            "tcn_id": tcn_id,
            "scope_refs": current_scope_by_tcn[tcn_id],
            "tr_refs": draft["tr_refs"],
            "condition": draft["condition"],
            "category": draft["category"],
            "technique_slugs": draft["technique_slugs"],
            "coverage_criterion": draft["coverage_criterion"],
            "authority_refs": draft["authority_refs"],
            "risk_refs": draft["risk_refs"],
            "priority": draft["priority"],
            "priority_override_reason": draft["priority_override_reason"],
            "status": "active",
        }
        for field in (
            "item_ref",
            "condition_ref",
            "formal_design_ref",
            "formal_design_revision",
            "expected_result_candidate_refs",
            "expected_result_candidates",
            "test_level",
            "test_level_source",
            "test_level_source_ref",
        ):
            if field in draft:
                content[field] = draft[field]
        dependency_identities = [
            ("test-requirement-design", "tr", ref)
            for ref in draft["tr_refs"]
            if ref in tr_rows
        ]
        dependency_identities.extend(
            ("spec-analysis", "authority", ref) for ref in draft["authority_refs"]
        )
        dependency_identities.extend(
            ("spec-analysis", "authority", ref)
            for candidate in draft.get("expected_result_candidates", [])
            for ref in candidate["authority_refs"]
        )
        dependency_identities.extend(
            ("test-analysis", "product_risk", ref) for ref in draft["risk_refs"]
        )
        dependencies = resolve_entity_dependencies(
            dependency_identities,
            current_entities,
            require_all=metadata["input_mode"] == "artifact",
        )
        tcn_entities[tcn_id] = make_machine_entity(
            SKILL,
            "tcn",
            tcn_id,
            content,
            upstream_entity_dependencies=dependencies,
            runtime_dependencies=[
                machine_entity_runtime_dependency(
                    SKILL, "artifact:condition_structure:all"
                )
            ],
        )
    entities = list(tcn_entities.values())
    for draft in model_drafts:
        model_key = model_mapping[draft["draft_key"]]
        row = model_metadata[model_key]
        dependency_identities = [(SKILL, "tcn", row["parent_tcn_id"])]
        if row["selection_source"] == "analysis":
            dependency_identities.append(
                ("test-analysis", "technique_selection", row["selection_key"])
            )
        if row["derived_from_model_key"] is not None:
            dependency_identities.append(
                (SKILL, "model", row["derived_from_model_key"])
            )
        local_entities = [
            *tcn_entities.values(),
            *(entity for entity in entities if entity["entity_type"] == "model"),
        ]
        local_identities = [
            identity for identity in dependency_identities if identity[0] == SKILL
        ]
        external_identities = [
            identity for identity in dependency_identities if identity[0] != SKILL
        ]
        dependencies = resolve_entity_dependencies(
            local_identities, local_entities, require_all=True
        )
        dependencies.extend(
            resolve_entity_dependencies(
                external_identities,
                current_entities,
                require_all=metadata["input_mode"] == "artifact",
            )
        )
        dependencies.sort(
            key=lambda item: (item["skill"], item["entity_type"], item["entity_ref"])
        )
        content = canonicalize(row)
        entity = make_machine_entity(
            SKILL,
            "model",
            model_key,
            content,
            model_key=model_key,
            upstream_entity_dependencies=dependencies,
            runtime_dependencies=[
                machine_entity_runtime_dependency(
                    SKILL, "artifact:condition_structure:all"
                )
            ],
        )
        entities.append(entity)

    for row, deps in disposition_rows:
        upstream = row["upstream_entity"]
        ref = f"{upstream['entity_type']}:{upstream['entity_ref']}"
        entities.append(
            make_machine_entity(
                SKILL,
                "disposition",
                ref,
                row,
                upstream_entity_dependencies=deps,
                runtime_dependencies=[
                    machine_entity_runtime_dependency(
                        SKILL, "artifact:condition_structure:all"
                    )
                ],
            )
        )

    tcn_state = []
    for row in previous_tcn:
        status = row["status"]
        scope_refs = row["scope_refs"]
        if row["tcn_id"] in update_tcn:
            status = "active" if row["tcn_id"] in reused_tcn else "deleted"
            if status == "active":
                scope_refs = current_scope_by_tcn[row["tcn_id"]]
            elif zero_scope_terminal:
                scope_refs = []
        elif row["tcn_id"] in inactive_tcn_ids:
            status = "inactive"
        tcn_state.append(
            {"tcn_id": row["tcn_id"], "status": status, "scope_refs": scope_refs}
        )
    for draft in tcn_drafts:
        tcn_state.append(
            {
                "tcn_id": tcn_mapping[draft["draft_key"]],
                "status": "active",
                "scope_refs": current_scope_by_tcn[tcn_mapping[draft["draft_key"]]],
            }
        )
    tcn_state = _dedupe_state(tcn_state, "tcn_id")
    model_state = []
    for row in previous_models:
        status = row["status"]
        scope_refs = row["scope_refs"]
        if row["model_key"] in update_model:
            status = "active" if row["model_key"] in reused_models else "deleted"
            if status == "active":
                scope_refs = model_metadata[row["model_key"]]["scope_refs"]
            elif zero_scope_terminal:
                scope_refs = []
        elif row["model_key"] in inactive_model_keys:
            status = "inactive"
        model_state.append({**row, "scope_refs": scope_refs, "status": status})
    for row in model_metadata.values():
        model_state.append({**row, "status": "active"})
    model_state = _dedupe_state(model_state, "model_key")
    model_entities = {
        entity["entity_ref"]: entity
        for entity in entities
        if entity["entity_type"] == "model"
    }
    active_model_metadata = [
        {
            "model_key": row["model_key"],
            "model_type": row["model_type"],
            "technique_slug": row["technique_slug"],
            "parent_tcn_id": row["parent_tcn_id"],
            "scope_refs": row["scope_refs"],
            "content_fingerprint": model_entities[row["model_key"]][
                "content_fingerprint"
            ],
        }
        for row in sorted(model_metadata.values(), key=lambda item: item["model_key"])
    ]
    tcn_id_map = [
        {
            "draft_key": draft["draft_key"],
            "tcn_id": tcn_mapping[draft["draft_key"]],
            "identity_action": draft["identity_action"],
        }
        for draft in sorted(tcn_drafts, key=lambda row: row["draft_key"])
    ]
    next_tcn_status = {row["tcn_id"]: row["status"] for row in tcn_state}
    next_model_status = {row["model_key"]: row["status"] for row in model_state}
    current_inactive_tcn_history = [
        inactive_tcn_history[ref]
        for ref in sorted(next_tcn_status)
        if next_tcn_status[ref] == "inactive"
    ]
    current_inactive_model_history = [
        inactive_model_history[ref]
        for ref in sorted(next_model_status)
        if next_model_status[ref] == "inactive"
    ]
    model_key_map = [
        {
            "draft_key": draft["draft_key"],
            "model_key": model_mapping[draft["draft_key"]],
            "model_type": draft["model_type"],
            "technique_slug": draft["technique_slug"],
            "parent_tcn_id": tcn_mapping[draft["parent_tcn_draft_key"]],
            "derived_from_model_key": model_metadata[model_mapping[draft["draft_key"]]][
                "derived_from_model_key"
            ],
            "identity_action": draft["identity_action"],
        }
        for draft in sorted(
            model_drafts,
            key=lambda row: (
                row["parent_tcn_draft_key"],
                row["model_type"],
                row["draft_key"],
            ),
        )
    ]
    expected_sources = [
        ("tcn", tcn_mapping[draft["draft_key"]]) for draft in tcn_drafts
    ]
    expected_sources.extend(
        ("model", model_mapping[draft["draft_key"]]) for draft in model_drafts
    )
    expected_sources.extend(
        (
            "disposition",
            f"{row['upstream_entity']['entity_type']}:{row['upstream_entity']['entity_ref']}",
        )
        for row in ensure_list(
            input_value["requirement_dispositions"], "requirement_dispositions"
        )
    )
    if formal_design_summary is not None:
        for pair in formal_design_summary["unresolved_pairs"]:
            pair_key = f"{pair['item_ref']}:{pair['condition_ref']}"
            violations.append(
                {
                    "target_key": f"violation:formal-pair:{pair_key}",
                    "issue_type": f"formal_pair_{pair['decision']}",
                    "entity_ref": pair_key,
                }
            )
        if formal_design_summary["pair_coverage_status"] != "complete":
            violations.append(
                {
                    "target_key": "violation:formal-pair-population-incomplete",
                    "issue_type": formal_design_summary["pair_coverage_status"],
                    "entity_ref": formal_design_summary["design_ref"],
                }
            )
    violations = sorted(violations, key=lambda row: row["target_key"])
    issues = [
        {
            "issue_type": row["issue_type"],
            "blocking": True,
            "target_key": row["target_key"],
            "authority_refs": [],
        }
        for row in violations
    ]
    result = {
        "runtime_status": "ok",
        "result_status": "ready" if not violations else "unresolved",
        "support_status": "supported",
        "deterministic_generated": True,
        "payload": {
            "tcn_id_map": tcn_id_map,
            "model_key_map": model_key_map,
            "tcn_id_state": sorted(tcn_state, key=lambda row: row["tcn_id"]),
            "model_key_state": sorted(model_state, key=lambda row: row["model_key"]),
            "inactive_tcn_history": current_inactive_tcn_history,
            "inactive_model_history": current_inactive_model_history,
            "inactive_materialize_history": [
                inactive_materialize_history[ref]
                for ref in sorted(inactive_materialize_history)
                if next_tcn_status.get(ref) != "deleted"
            ],
            "active_model_metadata": active_model_metadata,
            "formal_design_summary": formal_design_summary,
            "violations": violations,
            "expected_entity_identities": [
                {"skill": SKILL, "entity_type": entity_type, "entity_ref": entity_ref}
                for entity_type, entity_ref in sorted(expected_sources)
            ],
            "derived_values": {
                "entities": sorted(
                    entities, key=lambda row: (row["entity_type"], row["entity_ref"])
                )
            },
            "entities": sorted(
                entities, key=lambda row: (row["entity_type"], row["entity_ref"])
            ),
        },
        "issues": issues,
    }
    if formal_design_record is not None:
        result["payload"]["formal_design_record"] = formal_design_record
    return result


def _dedupe_state(rows: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        previous = result.get(row[key])
        if previous is not None and previous != row:
            raise InvalidInput(f"{key} stateが重複しています")
        result[row[key]] = row
    return list(result.values())


def handler(input_value: dict[str, Any], metadata: dict[str, Any]) -> dict[str, Any]:
    if (
        metadata["model_key"] is not None
        or metadata["runtime_unit_key"] != "artifact:condition_structure:all"
        or metadata["scope_key"] != "all"
    ):
        raise InvalidInput("condition_structureのruntime metadataが不正です")
    return _build(input_value, metadata)


if __name__ == "__main__":
    raise SystemExit(
        run_cli(
            handler,
            skill=SKILL,
            generator=GENERATOR,
            generator_contract_version=GENERATOR_CONTRACT_VERSION,
            generator_path=SCRIPT_PATH,
        )
    )
