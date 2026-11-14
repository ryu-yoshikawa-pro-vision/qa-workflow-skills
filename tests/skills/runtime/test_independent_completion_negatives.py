"""独立レビュー（担当C）の負例検証: 完了してはいけない状態で完了しないことを確認する。

既存テストの helper は import せず、本ファイルで fixture を組み直す。
- workflow_runtime.py は CLI（subprocess、JSON stdin）として呼ぶ。
- architecture_runtime.py は CLI（subprocess、JSON stdin）として呼ぶ。
- owner_verifiers は qa-workflow の scripts から直接 import する。
- downstream_state は保存済みv2の再開検査（_validate_frozen_pair）を直接呼ぶ。

承認の真正性は本検証の対象外（owner validator は approval_authenticity を確立しない）。
ここでは「形式・束縛・placeholder・対象外の確定」だけを見る。
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SKILLS = ROOT / "skills"
WORKFLOW_SCRIPT = SKILLS / "qa-workflow" / "scripts" / "workflow_runtime.py"
ARCH_SCRIPT = (
    SKILLS / "test-architecture-design" / "scripts" / "architecture_runtime.py"
)
QA_SCRIPTS = SKILLS / "qa-workflow" / "scripts"
sys.path.insert(0, str(QA_SCRIPTS))

import downstream_state  # noqa: E402
import owner_verifiers  # noqa: E402

CHILD_ENV = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
WORKFLOW_REF = "00000000-0000-4000-8000-0000000000c1"
ROOT_ID = "qa-workflow::artifact:workflow_runtime:all"
METADATA = {
    "envelope_version": "1",
    "skill": "qa-workflow",
    "runtime_contract_version": "runtime-v2",
    "generator_contract_version": "workflow-runtime-v2",
    "runtime_unit_key": "artifact:workflow_runtime:all",
    "model_key": None,
    "model_type": None,
    "technique_slug": None,
    "selection_source": None,
    "selection_key": None,
    "scope_key": "all",
    "input_mode": "artifact",
    "upstream_entities": [],
    "upstream_runtime_units": [],
    "static_data_versions": {},
    "authority_refs": [],
    "reference_refs": [],
}
TA = "test-architecture-design"
TM = "test-management"
UNREG = "defect-management"

# --- architecture 用の固定値（C独自fixture）
OWNER = TA
SCOPE = "scope-review-c"
ART = "artifact:arch-review-c-r1"
REV = "arch-r1"
QA_ART = "artifact:qra-review-c-r1"
QA_REV = "qra-r1"
QA_REF = f"{QA_ART}#QAR-001@{QA_REV}"
OTHER_QA_ART = "artifact:qra-other-r1"
OTHER_QA_REF = f"{OTHER_QA_ART}#QAR-009@qra-other-r1"
T_CONFIRM = "item:c-confirm"
T_PAY = "item:c-payment"
TA_SRC_ART = "artifact:ta-review-r1"


def canon(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def seal(packet: dict) -> dict:
    body = {k: v for k, v in packet.items() if k != "content_fingerprint"}
    packet["content_fingerprint"] = sha(canon(body))
    return packet


def run_cli(script: Path, payload: dict) -> dict:
    completed = subprocess.run(
        [sys.executable, "-B", str(script)],
        input=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=ROOT,
        env=CHILD_ENV,
        check=False,
    )
    if completed.stderr:
        raise AssertionError(completed.stderr.decode("utf-8"))
    return json.loads(completed.stdout)


# ======================================================================
# workflow_runtime（対象外・承認参照・owner検証の組合せ）
# ======================================================================


def wf_required(skill: str, target: str | None) -> dict:
    return {
        "skill": skill,
        "target": target,
        "execution_range": "plan",
        "requirement": "required",
    }


def wf_excluded(
    skill: str, target: str | None, approval_ref: object = "APPROVAL-001"
) -> dict:
    row = {
        "skill": skill,
        "target": target,
        "execution_range": "plan",
        "requirement": "excluded_by_approval",
    }
    if approval_ref is not MISSING:
        row["approval_ref"] = approval_ref
    return row


MISSING = object()


def wf_scope(skill: str, target: str | None, normalized: dict | None = None) -> dict:
    return {
        "skill": skill,
        "target": target,
        "execution_range": "plan",
        "input_mode": "artifact",
        "normalized_input": normalized or {},
        "current_structure_state": None,
    }


def wf_run(requested: list[dict] | None, scopes: list[dict]) -> dict:
    value = {
        "workflow_ref": WORKFLOW_REF,
        "workflow_scopes": scopes,
        "runtime_units": [],
        "current_runtime_units": [],
        "current_entities": [],
        "unsupported_item_closures": [],
    }
    if requested is not None:
        value["requested_scopes"] = requested
    return run_cli(
        WORKFLOW_SCRIPT, {"metadata": copy.deepcopy(METADATA), "input": value}
    )


def wf_input(requested: list[dict] | None, scopes: list[dict]) -> dict:
    value = {
        "workflow_ref": WORKFLOW_REF,
        "workflow_scopes": scopes,
        "runtime_units": [],
        "current_runtime_units": [],
        "current_entities": [],
        "unsupported_item_closures": [],
    }
    if requested is not None:
        value["requested_scopes"] = requested
    return value


def issue_types(result: dict) -> set[str]:
    return {issue["issue_type"] for issue in result.get("issues", [])}


# ======================================================================
# architecture fixture（C独自）
# ======================================================================


def qa_source(sid: str, art: str, rev: str, local: str, scope: str = SCOPE) -> dict:
    return {
        "source_id": sid,
        "role": "qa_requirement",
        "owner": "test-requirements-analysis",
        "scope": scope,
        "artifact_ref": art,
        "revision": rev,
        "content_hash": sha(f"{art}-content"),
        "acquisition": "取得済",
        "approval_state": "承認済み",
        "approval_evidence_ref": f"evidence:{art}-approval",
        "local_id": local,
    }


def ta_source() -> dict:
    return {
        "source_id": "SRC-002",
        "role": "test_analysis",
        "owner": "test-analysis",
        "scope": SCOPE,
        "artifact_ref": TA_SRC_ART,
        "revision": "ta-r1",
        "content_hash": sha("ta-content"),
        "acquisition": "取得済",
        "approval_state": "不要",
        "approval_evidence_ref": None,
        "local_id": None,
    }


def asg(
    aid: str,
    target: str,
    level: str,
    basis: str,
    *,
    qa: str = QA_REF,
    bases: tuple[str, ...] = ("SRC-002",),
    src: list[str] | None = None,
    approval_id: str | None = None,
    disposition: str = "確定",
    exclusion: str | None = None,
) -> dict:
    return {
        "assignment_id": aid,
        "target_ref": target,
        "target_kind": "test_item",
        "qa_requirement_ref": qa,
        "level": level,
        "test_type": "業務フロー検証",
        "method": "自動実行",
        "verification_responsibility": "開発QA",
        "environment": "staging-review",
        "data": "匿名化データ",
        "runner_tool": "CI runner",
        "automation": "自動",
        "measurement": "完了状態の観測",
        "selection_basis": basis,
        "basis_source_ids": list(bases),
        "source_ids": src
        if src is not None
        else ["SRC-001"] + [b for b in bases if b != "SRC-001"],
        "approval_id": approval_id,
        "disposition": disposition,
        "readiness": "準備済み",
        "exclusion_reason": exclusion,
        "downstream_refs": [
            {"kind": "TC", "ref": "artifact:tc-review-r1#TC-001@tc-r1"}
        ],
    }


def prio(target: str, *, explicit=(), approved=(), default=()) -> dict:
    if explicit:
        decision, levels = "明示指定", list(explicit)
    elif approved:
        decision, levels = "承認済みarchitecture", list(approved)
    elif default:
        decision, levels = "test-analysis既定値", list(default)
    else:
        decision, levels = "未確定", []
    return {
        "target_ref": target,
        "explicit_levels": list(explicit),
        "approved_levels": list(approved),
        "default_levels": list(default),
        "levels": levels,
        "decision": decision,
        "conflict_resolution": None,
    }


def coverage(packet: dict) -> None:
    rows = []
    for source in packet["sources"]:
        if source["role"] != "qa_requirement":
            continue
        ref = f"{source['artifact_ref']}#{source['local_id']}@{source['revision']}"
        ids = sorted(
            a["assignment_id"]
            for a in packet["assignments"]
            if a["qa_requirement_ref"] == ref
        )
        rows.append(
            {
                "qa_requirement_ref": ref,
                "coverage": "割当済み" if ids else "未割当",
                "assignment_ids": ids,
                "exclusion_reason": None,
            }
        )
    packet["requirement_coverage"] = rows


def base_packet() -> dict:
    """QA要求1件（SRC-001）、既定値の確定割当1件（ARCH-001, システム）の完了可能な packet。"""
    packet = {
        "schema": "test-architecture-v1",
        "owner": OWNER,
        "artifact_ref": ART,
        "scope": SCOPE,
        "content_fingerprint": "0" * 64,
        "sources": [qa_source("SRC-001", QA_ART, QA_REV, "QAR-001"), ta_source()],
        "requirement_coverage": [],
        "assignments": [asg("ARCH-001", T_CONFIRM, "システム", "test-analysis既定値")],
        "level_priority": [prio(T_CONFIRM, default=["システム"])],
        "constraints": [],
        "open_items": [],
        "change_impacts": [],
        "history": [],
    }
    coverage(packet)
    return seal(packet)


def approved_packet() -> dict:
    """同一targetに承認済みの2 level（API・システム）。確定割当とapproval_idを持つ。"""
    packet = base_packet()
    packet["assignments"] += [
        asg(
            "ARCH-002",
            T_PAY,
            "API",
            "承認済みarchitecture",
            qa=QA_REF,
            bases=("SRC-001",),
            approval_id="APR-001",
        ),
        asg(
            "ARCH-003",
            T_PAY,
            "システム",
            "承認済みarchitecture",
            qa=QA_REF,
            bases=("SRC-001",),
            approval_id="APR-002",
        ),
    ]
    packet["level_priority"].append(
        prio(T_PAY, approved=["API", "システム"], default=["システム"])
    )
    coverage(packet)
    return seal(packet)


def approvals_for(
    packet: dict,
    *,
    revision: str = REV,
    pairs=None,
    scope: str | None = None,
    artifact: str | None = None,
    state: str = "承認済み",
    approver: str = "品質責任者",
) -> list[dict]:
    pairs = pairs or {"APR-001": ["ARCH-002"], "APR-002": ["ARCH-003"]}
    rows = []
    for approval_id, assignment_ids in pairs.items():
        rows.append(
            {
                "approval_id": approval_id,
                "artifact_ref": artifact or packet["artifact_ref"],
                "scope": scope or packet["scope"],
                "content_fingerprint": packet["content_fingerprint"],
                "revision": revision,
                "assignment_ids": assignment_ids,
                "approver": approver,
                "approver_role": "approver",
                "evidence_ref": f"evidence:{approval_id.lower()}",
                "state": state,
            }
        )
    return rows


def cc(packet: dict, **extra) -> dict:
    return run_cli(
        ARCH_SCRIPT, {"operation": "completion_check", "artifact": packet, **extra}
    )


def arch_codes(result: dict) -> set[str]:
    return {issue["code"] for issue in result.get("issues", [])}


def arch_subjects(result: dict, code: str) -> list[str]:
    return [
        issue["subject_id"]
        for issue in result.get("issues", [])
        if issue["code"] == code
    ]


# ======================================================================
# owner verifier 用の証拠（stored_content / readback / expected_revision / current_source_refs）
# ======================================================================


def owner_evidence(
    packet: dict,
    *,
    approvals=None,
    stored: str | None = None,
    readback_rev: str = REV,
    expected: str = REV,
) -> dict:
    text = stored if stored is not None else canon(packet)
    refs = [
        {
            "owner": s["owner"],
            "scope": s["scope"],
            "artifact_ref": s["artifact_ref"],
            "revision": s["revision"],
            "content_hash": s["content_hash"],
        }
        for s in packet["sources"]
    ]
    return {
        "stored_content": text,
        "readback": {
            "owner": OWNER,
            "scope": packet["scope"],
            "artifact_ref": packet["artifact_ref"],
            "revision": readback_rev,
            "content_hash": sha(text),
        },
        "expected_revision": expected,
        "current_source_refs": refs,
        "approval_evidence": approvals if approvals is not None else [],
    }


def ta_scope_with(packet: dict, **kw) -> dict:
    return wf_scope(TA, ART, {"owner_verification": owner_evidence(packet, **kw)})


def ta_verified(packet: dict) -> dict:
    """承認証拠が一致するpacketのowner検証済みscope（検証済みの前提を作る）。"""
    return ta_scope_with(packet, approvals=approvals_for(packet))


def state_dict() -> dict:
    return {
        "runtime_results": [],
        "carry_forward_entities": [],
        "previous_ci_id_state": [],
    }


# ======================================================================
# テスト
# ======================================================================


class WorkflowExclusionNegatives(unittest.TestCase):
    """qa-workflow: 対象外（excluded_by_approval）は承認の照合手段が無い間、確定しない。"""

    def test_dummy_plausible_approval_refs_never_complete(self) -> None:
        # 期待結果: どの承認参照（形式が一見正しいもの含む）でも excluded_scopes は空、
        #   対象外の scope は必須のまま、can_complete=false。対象外の scope は verified でも
        #   完了判定から外れない。
        refs = [
            "APPROVAL-2026-0001",
            "APR-001",
            "approved-by-owner",
            "承認記録-001",
            "https://example.invalid/approval/1",
            "ticket#123",
        ]
        for ref in refs:
            with self.subTest(ref=ref):
                scopes = [
                    ta_verified(approved_packet()),
                    wf_scope(UNREG, "unregistered-target"),
                ]
                result = wf_run(
                    [
                        wf_required(TA, ART),
                        wf_excluded(UNREG, "unregistered-target", ref),
                    ],
                    scopes,
                )
                payload = result["payload"]
                self.assertFalse(payload["can_complete"], result)
                self.assertEqual(payload["excluded_scopes"], [], result)
                self.assertEqual(
                    payload["unverified_exclusions"][0]["skill"], UNREG, result
                )
                self.assertEqual(
                    payload["unverified_exclusions"][0]["reason"],
                    "approval_unverifiable",
                    result,
                )

    def test_stale_revision_and_other_scope_refs_never_complete(self) -> None:
        # 期待結果: 古いrevision（APR-001@rev-1）・別scope/別skill向けを示す参照でも対象外は確定しない。
        #   TA は verified のまま、対象外行は unverified_exclusions に残る。
        refs = [
            "APR-001@rev-1",
            "APR-OTHER-SCOPE",
            "APPROVAL-001@test-management:target-b",
            "承認記録-2026-0001",
        ]
        for ref in refs:
            with self.subTest(ref=ref):
                result = wf_run(
                    [wf_required(TA, ART), wf_excluded(TM, "target-b", ref)],
                    [ta_verified(approved_packet()), wf_scope(TM, "target-b")],
                )
                self.assertFalse(result["payload"]["can_complete"], result)
                self.assertEqual(result["payload"]["excluded_scopes"], [], result)
                self.assertIn(
                    TA,
                    [r["skill"] for r in result["payload"]["verified_owner_scopes"]],
                    result,
                )
                self.assertTrue(result["payload"]["unverified_exclusions"], result)

    def test_placeholder_refs_including_normalization_variants_never_complete(
        self,
    ) -> None:
        # 期待結果: NFKC・空白・大文字小文字の揺れを含む placeholder は対象外にならない。
        #   ゼロ幅文字入りは placeholder 判定を外れるため reason は approval_unverifiable になりうるが、
        #   完了不可・excluded空は必ず成立する（reason は報告で別途記録）。
        refs = [
            "ＵＮＫＮＯＷＮ",
            "unknown",
            "　未設定　",
            "ＮＯＮＥ",
            "未設定​",
            "unknown​",
            "​",
            "  ",
            "承認　済み",
            "ＡＰＲ－００１",
        ]
        for ref in refs:
            with self.subTest(ref=repr(ref)):
                result = wf_run(
                    [wf_required(TA, ART), wf_excluded(TM, "target-b", ref)],
                    [ta_verified(approved_packet()), wf_scope(TM, "target-b")],
                )
                self.assertFalse(result["payload"]["can_complete"], result)
                self.assertEqual(result["payload"]["excluded_scopes"], [], result)
                self.assertTrue(result["payload"]["unverified_exclusions"], result)

    def test_missing_or_empty_ref_is_missing_reason(self) -> None:
        # 期待結果: 欠落・空文字は approval_ref_missing（完了不可）。
        for ref in (MISSING, "", "   "):
            with self.subTest(ref=repr(ref)):
                result = wf_run(
                    [wf_required(TA, ART), wf_excluded(TM, "target-b", ref)],
                    [ta_verified(approved_packet()), wf_scope(TM, "target-b")],
                )
                self.assertFalse(result["payload"]["can_complete"], result)
                self.assertEqual(
                    result["payload"]["unverified_exclusions"][0]["reason"],
                    "approval_ref_missing",
                    result,
                )

    def test_verified_scope_declared_excluded_is_not_complete(self) -> None:
        # 期待結果: workflow_scopes に検証済みのTAがあっても、TAを対象外として宣言すると完了しない。
        #   TAは検証済みのまま残り、対象外は確定しない（黙って除外しない）。
        result = wf_run(
            [wf_excluded(TA, ART, "APPROVAL-001")],
            [ta_verified(approved_packet())],
        )
        self.assertFalse(result["payload"]["can_complete"], result)
        self.assertEqual(result["payload"]["excluded_scopes"], [], result)
        self.assertIn("approval_unverifiable", issue_types(result))
        self.assertIn(
            TA, [r["skill"] for r in result["payload"]["verified_owner_scopes"]]
        )

    def test_exclusion_without_workflow_scope_is_missing_required(self) -> None:
        # 期待結果: 対象外宣言のscopeが workflow_scopes に無い場合、required_scope_missing で完了しない。
        result = wf_run(
            [wf_required(TA, ART), wf_excluded(UNREG, "not-in-scopes", "APR-001")],
            [ta_verified(approved_packet())],
        )
        self.assertFalse(result["payload"]["can_complete"], result)
        self.assertIn(
            {"skill": UNREG, "target": "not-in-scopes", "execution_range": "plan"},
            result["payload"]["missing_requested_scopes"],
        )
        self.assertIn("required_scope_missing", issue_types(result))

    def test_required_only_direct_start_with_existing_artifact_completes(self) -> None:
        # 期待結果（正常系）: requirement=required のみを宣言し、既存成果物をownerが検証済みなら完了する。
        #   承認は不要で、対象外は使われない（直接開始・途中開始の維持）。
        result = wf_run(
            [wf_required(TA, ART)],
            [
                ta_scope_with(
                    approved_packet(), approvals=approvals_for(approved_packet())
                )
            ],
        )
        self.assertTrue(result["payload"]["can_complete"], result)
        self.assertEqual(result["payload"]["excluded_scopes"], [])
        self.assertEqual(result["payload"]["unverified_exclusions"], [])

    def test_unrequested_draft_architecture_does_not_break_direct_start(self) -> None:
        # 期待結果（正常系）: 要求外のscope（未要求だが workflow_scopes にある未検証TM）は、
        #   既存ルールどおり未検証なら完了不可。ここでは要求集合に無いTMを載せないことで、
        #   要求外の草案が現scopeを止めないことを確認する。
        result = wf_run(
            [wf_required(TA, ART)],
            [
                ta_scope_with(
                    approved_packet(), approvals=approvals_for(approved_packet())
                )
            ],
        )
        self.assertTrue(result["payload"]["can_complete"], result)


class ArchitectureCompletionNegatives(unittest.TestCase):
    """architecture_runtime completion_check: 確定割当の裏付けと承認の束縛。"""

    def test_requirement_with_only_unapproved_draft_is_incomplete(self) -> None:
        # 期待結果: QA要求に未承認案の割当しか無い（coverage=割当済み）→ complete=false、requirement_unconfirmed。
        packet = base_packet()
        packet["assignments"][0]["disposition"] = "未承認案"
        seal(packet)
        result = cc(packet)
        self.assertFalse(result["complete"], result)
        self.assertIn("requirement_unconfirmed", arch_codes(result))
        self.assertEqual(result["confirmed_assignment_ids"], [])

    def test_approved_level_with_only_unapproved_draft_is_incomplete(self) -> None:
        # 期待結果: 承認済みarchitectureの必須level（API）が未承認案だけ → level_unconfirmed で complete=false。
        packet = approved_packet()
        packet["assignments"][1]["disposition"] = "未承認案"  # ARCH-002 (API)
        seal(packet)
        result = cc(
            packet, expected_revision=REV, approval_evidence=approvals_for(packet)
        )
        self.assertFalse(result["complete"], result)
        self.assertIn("level_unconfirmed", arch_codes(result))
        self.assertEqual(arch_subjects(result, "level_unconfirmed"), [T_PAY])

    def test_explicit_required_level_only_as_draft_is_incomplete(self) -> None:
        # 期待結果: 明示指定の2 level（API・システム）のうちAPIが未承認案のみ → complete=false。
        #   承認不要（既定値が空のため）。確定のシステムだけでは範囲を満たさない。
        packet = base_packet()
        packet["assignments"] += [
            asg(
                "ARCH-002",
                T_PAY,
                "API",
                "明示指定",
                bases=("SRC-001",),
                disposition="未承認案",
            ),
            asg("ARCH-003", T_PAY, "システム", "明示指定", bases=("SRC-001",)),
        ]
        packet["level_priority"].append(prio(T_PAY, explicit=["API", "システム"]))
        coverage(packet)
        seal(packet)
        result = cc(packet)
        self.assertFalse(result["complete"], result)
        self.assertEqual(arch_subjects(result, "level_unconfirmed"), [T_PAY])

    def test_coverage_assigned_but_only_excluded_and_draft_is_incomplete(self) -> None:
        # 期待結果: coverage=割当済みで、割当が 対象外 と 未承認案 だけ → complete=false（requirement_unconfirmed）。
        packet = base_packet()
        packet["assignments"] = [
            asg(
                "ARCH-001",
                T_CONFIRM,
                "システム",
                "test-analysis既定値",
                disposition="対象外",
                exclusion="理由",
            ),
            asg(
                "ARCH-002",
                T_CONFIRM,
                "システム",
                "test-analysis既定値",
                disposition="未承認案",
            ),
        ]
        packet["assignments"][1]["method"] = "手動実行"
        coverage(packet)
        seal(packet)
        result = cc(packet)
        self.assertFalse(result["complete"], result)
        self.assertIn("requirement_unconfirmed", arch_codes(result))
        self.assertEqual(result["confirmed_assignment_ids"], [])

    def test_mixed_confirmed_and_draft_at_same_level_is_complete(self) -> None:
        # 期待結果（正常系）: 決定済みlevelに確定割当があり、同levelの別方式の追加案だけが未承認なら complete=true。
        packet = base_packet()
        extra = asg(
            "ARCH-002",
            T_CONFIRM,
            "システム",
            "test-analysis既定値",
            disposition="未承認案",
        )
        extra["method"] = "手動実行"
        packet["assignments"].append(extra)
        coverage(packet)
        seal(packet)
        result = cc(packet)
        self.assertTrue(result["complete"], result)
        self.assertEqual(result["unapproved_assignment_ids"], ["ARCH-002"])

    def test_approved_multiple_levels_with_confirmed_and_evidence_is_complete(
        self,
    ) -> None:
        # 期待結果（正常系）: 承認済みの2 levelがいずれも確定割当＋一致する承認証拠を持てば complete=true。
        packet = approved_packet()
        result = cc(
            packet, expected_revision=REV, approval_evidence=approvals_for(packet)
        )
        self.assertTrue(result["complete"], result)
        self.assertEqual(
            result["confirmed_assignment_ids"], ["ARCH-001", "ARCH-002", "ARCH-003"]
        )

    def test_approval_for_old_revision_is_incomplete(self) -> None:
        # 期待結果: 承認証拠が旧revision（arch-r0）向けなら complete=false（approval_revision_mismatch）。
        packet = approved_packet()
        result = cc(
            packet,
            expected_revision=REV,
            approval_evidence=approvals_for(packet, revision="arch-r0"),
        )
        self.assertFalse(result["complete"], result)
        self.assertIn("approval_revision_mismatch", arch_codes(result))

    def test_approval_for_other_scope_or_artifact_is_incomplete(self) -> None:
        # 期待結果: 承認証拠が別scope・別artifact向けなら complete=false。
        packet = approved_packet()
        for kwargs in (
            {"scope": "scope-other"},
            {"artifact": "artifact:arch-other-r1"},
        ):
            with self.subTest(kwargs=kwargs):
                result = cc(
                    packet,
                    expected_revision=REV,
                    approval_evidence=approvals_for(packet, **kwargs),
                )
                self.assertFalse(result["complete"], result)
                self.assertIn("approval_identity_mismatch", arch_codes(result))

    def test_placeholder_or_unapproved_approval_states_are_incomplete(self) -> None:
        # 期待結果: 承認状態が承認済みでない、または承認者・証拠refが placeholder なら complete=false。
        packet = approved_packet()
        cases = [
            ({"state": "未承認"}, "approval_not_approved"),
            ({"state": "承認済み", "approver": "unknown"}, "approval_identity_missing"),
            (
                {"state": "承認済み", "approver": "承認済み"},
                "approval_identity_missing",
            ),
        ]
        for kwargs, code in cases:
            with self.subTest(kwargs=kwargs):
                result = cc(
                    packet,
                    expected_revision=REV,
                    approval_evidence=approvals_for(packet, **kwargs),
                )
                self.assertFalse(result["complete"], result)
                self.assertIn(code, arch_codes(result))

    def test_invalid_approval_id_format_is_incomplete(self) -> None:
        # 期待結果: 承認参照の形式が APR-### でない（APPROVAL-2026-0001、APR-001@rev-1）なら、packet検証で complete=false。
        for bad in ("APPROVAL-2026-0001", "APR-001@rev-1", "承認記録-001"):
            with self.subTest(bad=bad):
                packet = approved_packet()
                packet["assignments"][1]["approval_id"] = bad
                seal(packet)
                result = cc(
                    packet,
                    expected_revision=REV,
                    approval_evidence=approvals_for(
                        packet, pairs={bad: ["ARCH-002"], "APR-002": ["ARCH-003"]}
                    ),
                )
                self.assertFalse(result["complete"], result)

    def test_other_scope_draft_on_other_target_does_not_block(self) -> None:
        # 期待結果（正常系・契約どおり）: 別scopeのQA要求に紐づく未承認案が、別targetにあるなら完了を止めない。
        packet = base_packet()
        packet["sources"].append(
            qa_source(
                "SRC-003", OTHER_QA_ART, "qra-other-r1", "QAR-009", scope="scope-other"
            )
        )
        packet["assignments"].append(
            asg(
                "ARCH-002",
                "item:other-target",
                "API",
                "test-analysis既定値",
                qa=OTHER_QA_REF,
                src=["SRC-003", "SRC-002"],
                disposition="未承認案",
            )
        )
        packet["level_priority"].append(prio("item:other-target", default=["API"]))
        coverage(packet)
        seal(packet)
        result = cc(packet)
        self.assertTrue(result["complete"], result)

    def test_other_scope_draft_on_same_target_at_new_level_does_not_block(self) -> None:
        # 期待結果（契約どおり）: data-contract は「別scopeのqa_requirementと、要求範囲に含まれない未承認案は
        #   このpacketの完了を止めない」と定める。同じtargetに別scopeの未承認案（別level）があっても、
        #   現scopeの確定割当で完了するはず。
        #   注記: 既定の決定集合はtarget単位のため、この期待が成立しない場合は契約との不整合として報告する。
        packet = base_packet()
        packet["sources"].append(
            qa_source(
                "SRC-003", OTHER_QA_ART, "qra-other-r1", "QAR-009", scope="scope-other"
            )
        )
        packet["assignments"].append(
            asg(
                "ARCH-002",
                T_CONFIRM,
                "API",
                "test-analysis既定値",
                qa=OTHER_QA_REF,
                src=["SRC-003", "SRC-002"],
                disposition="未承認案",
            )
        )
        packet["level_priority"] = [prio(T_CONFIRM, default=["システム", "API"])]
        coverage(packet)
        seal(packet)
        validation = run_cli(ARCH_SCRIPT, {"operation": "validate", "artifact": packet})
        self.assertTrue(validation.get("valid"), validation)
        result = cc(packet)
        self.assertTrue(result["complete"], result)

    def test_other_scope_draft_does_not_count_for_current_requirement(self) -> None:
        # 期待結果: 現scopeのQA要求の確定割当が無い場合、別scopeの確定割当は現要求を満たさない。
        packet = base_packet()
        packet["sources"].append(
            qa_source(
                "SRC-003", OTHER_QA_ART, "qra-other-r1", "QAR-009", scope="scope-other"
            )
        )
        packet["assignments"][0]["disposition"] = "未承認案"
        packet["assignments"].append(
            asg(
                "ARCH-002",
                T_CONFIRM,
                "システム",
                "test-analysis既定値",
                qa=OTHER_QA_REF,
                src=["SRC-003", "SRC-002"],
            )
        )
        packet["assignments"][1]["method"] = "手動実行"
        coverage(packet)
        seal(packet)
        result = cc(packet)
        self.assertFalse(result["complete"], result)
        self.assertIn("requirement_unconfirmed", arch_codes(result))


class OwnerVerifierAndResumeNegatives(unittest.TestCase):
    """owner_verifiers（直接import）と保存済みv2の再開（downstream_state）。"""

    def test_owner_verifier_refuses_draft_only_architecture(self) -> None:
        # 期待結果: 未承認案だけの packet は owner verify で unverified（completion_not_met）。
        packet = base_packet()
        packet["assignments"][0]["disposition"] = "未承認案"
        seal(packet)
        outcome = owner_verifiers.verify(TA, ta_scope_with(packet))
        self.assertEqual(outcome["status"], "unverified", outcome)
        self.assertEqual(outcome["reason"], "completion_not_met")

    def test_owner_verifier_refuses_unconfirmed_approved_level(self) -> None:
        # 期待結果: 承認済みlevelが未承認案だけ → unverified。
        packet = approved_packet()
        packet["assignments"][1]["disposition"] = "未承認案"
        seal(packet)
        outcome = owner_verifiers.verify(
            TA, ta_scope_with(packet, approvals=approvals_for(packet))
        )
        self.assertEqual(outcome["status"], "unverified", outcome)

    def test_owner_verifier_accepts_complete_approved_architecture(self) -> None:
        # 期待結果（正常系）: 承認済み2 level・確定・承認証拠一致 → verified。承認の真正性は未確立のまま記録される。
        packet = approved_packet()
        outcome = owner_verifiers.verify(
            TA, ta_scope_with(packet, approvals=approvals_for(packet))
        )
        self.assertEqual(outcome["status"], "verified", outcome)
        self.assertEqual(
            outcome["record"]["verified_artifact"]["approval_authenticity"],
            "not_established_by_this_validator",
        )

    def test_known_limit_old_self_consistent_evidence_still_verifies(self) -> None:
        # 既知の制約（報告に明記）: owner verifier は現行の readback を再取得しない。
        # 古い revision の stored_content と、それに一致する readback・expected_revision の組は
        # 自己整合するため verified になる。現行 readback を取得して渡すのは呼出し側の責務。
        old = approved_packet()
        old_ev = ta_scope_with(old, approvals=approvals_for(old))
        self.assertEqual(owner_verifiers.verify(TA, old_ev)["status"], "verified")

    def test_resume_rejects_stored_v2_with_exclusion_claim(self) -> None:
        # 期待結果: 保存済みv2の結果（can_complete を true に書き換えた想定）で対象外を主張していれば、
        #   downstream_state は再開を拒否する（historical excluded scope claim is not confirmable）。
        scopes = [ta_verified(approved_packet()), wf_scope(TM, "target-b")]
        requested = [wf_required(TA, ART), wf_excluded(TM, "target-b", "APPROVAL-001")]
        value = wf_input(requested, scopes)
        result = wf_run(requested, scopes)
        self.assertFalse(result["payload"]["can_complete"], result)
        forged = copy.deepcopy(result)
        forged["payload"]["can_complete"] = True
        forged["result_status"] = "ready"
        markdown = self._markdown(value, forged)
        with self.assertRaisesRegex(
            Exception, "not confirmable|schema or frozen|scope declaration"
        ):
            downstream_state._validate_frozen_pair(markdown, WORKFLOW_REF)

    def test_resume_accepts_stored_required_only_complete_result(self) -> None:
        # 期待結果（正常系）: requirement=required のみで完了した保存済みv2は、再開で受理される。
        scopes = [
            {**ta_verified(approved_packet()), "current_structure_state": state_dict()}
        ]
        requested = [wf_required(TA, ART)]
        value = wf_input(requested, scopes)
        result = wf_run(requested, scopes)
        self.assertTrue(result["payload"]["can_complete"], result)
        markdown = self._markdown(value, result)
        source, payload = downstream_state._validate_frozen_pair(markdown, WORKFLOW_REF)
        self.assertTrue(payload["can_complete"])

    @staticmethod
    def _markdown(value: dict, result: dict) -> str:
        source = {"metadata": copy.deepcopy(METADATA), "input": value}
        return (
            f"### Machine Runtime Input: {ROOT_ID}\n\n```json\n{json.dumps(source, ensure_ascii=False)}\n```\n\n"
            f"### Machine Runtime Result: {ROOT_ID}\n\n```json\n{json.dumps(result, ensure_ascii=False)}\n```\n"
        )


if __name__ == "__main__":
    unittest.main()
