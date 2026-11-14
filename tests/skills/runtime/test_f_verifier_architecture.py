"""test-architecture-design の保存済みartifact検証入口（owner verifier用script）の検証。

scriptはJSON stdin / JSON stdoutのサブプロセスとして実際に呼び出す。承認の認証主体と
保存先の取得手段は未選定のため、ここでは呼出し側が渡す証拠の束縛と内部整合だけを確認する。
"""

from __future__ import annotations

import ast
import copy
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = (
    REPO_ROOT
    / "skills"
    / "test-architecture-design"
    / "scripts"
    / "architecture_runtime.py"
)
EXAMPLE = (
    REPO_ROOT / "skills" / "test-architecture-design" / "assets" / "packet-example.json"
)

OWNER = "test-architecture-design"
SCOPE = "orders-release-q4"
ART = "artifact:arch-orders-r1"
REV = "arch-r1"
QA_ART = "artifact:qra-orders-r1"
QA_REV = "qra-r3"
QA_REF = f"{QA_ART}#QAR-001@{QA_REV}"
TARGET_CONFIRM = "item:order-confirm"
TARGET_PAYMENT = "item:order-payment"


def canon(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def seal(packet: dict) -> dict:
    body = {key: value for key, value in packet.items() if key != "content_fingerprint"}
    packet["content_fingerprint"] = hashlib.sha256(canon(body)).hexdigest()
    return packet


def run_raw(raw: bytes) -> tuple[int, bytes, bytes]:
    with tempfile.TemporaryDirectory() as cwd:
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        completed = subprocess.run(
            [sys.executable, "-I", "-B", str(SCRIPT)],
            input=raw,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=cwd,
            env=env,
            check=False,
            timeout=60,
        )
        return completed.returncode, completed.stdout, completed.stderr


def call(request: dict) -> dict:
    code, out, err = run_raw(json.dumps(request, ensure_ascii=False).encode("utf-8"))
    self_check = (code, err)
    assert self_check == (0, b""), err
    return json.loads(out)


def codes(result: dict) -> set[str]:
    return {issue["code"] for issue in result.get("issues", [])}


def source(
    sid,
    role,
    owner,
    artifact_ref,
    revision,
    content,
    *,
    acquisition="取得済",
    approval="不要",
    evidence=None,
    local_id=None,
) -> dict:
    return {
        "source_id": sid,
        "role": role,
        "owner": owner,
        "scope": SCOPE,
        "artifact_ref": artifact_ref,
        "revision": revision,
        "content_hash": sha(content),
        "acquisition": acquisition,
        "approval_state": approval,
        "approval_evidence_ref": evidence,
        "local_id": local_id,
    }


def sources() -> list[dict]:
    return [
        source(
            "SRC-001",
            "qa_requirement",
            "test-requirements-analysis",
            QA_ART,
            QA_REV,
            "qra-content",
            approval="承認済み",
            evidence="evidence:qra-approval-r3",
            local_id="QAR-001",
        ),
        source(
            "SRC-002",
            "test_analysis",
            "test-analysis",
            "artifact:ta-orders-r2",
            "ta-r2",
            "ta-content",
        ),
    ]


def assignment(
    aid,
    target,
    level,
    basis,
    *,
    basis_sources=("SRC-002",),
    approval_id=None,
    disposition="確定",
    readiness="準備済み",
    downstream=None,
) -> dict:
    return {
        "assignment_id": aid,
        "target_ref": target,
        "target_kind": "test_item",
        "qa_requirement_ref": QA_REF,
        "level": level,
        "test_type": "業務フロー検証",
        "method": "自動実行",
        "verification_responsibility": "開発QA",
        "environment": "staging-orders",
        "data": "匿名化注文データ",
        "runner_tool": "CI runner",
        "automation": "自動",
        "measurement": "注文完了状態の観測",
        "selection_basis": basis,
        "basis_source_ids": list(basis_sources),
        "source_ids": ["SRC-001"] + [sid for sid in basis_sources if sid != "SRC-001"],
        "approval_id": approval_id,
        "disposition": disposition,
        "readiness": readiness,
        "exclusion_reason": None,
        "downstream_refs": downstream
        if downstream is not None
        else [{"kind": "TC", "ref": "artifact:tc-orders-r1#TC-001@tc-r1"}],
    }


def priority(target, *, explicit=(), approved=(), default=(), conflict=None) -> dict:
    if explicit and approved and set(explicit) != set(approved):
        decision, levels = "未確定", sorted(set(explicit) | set(approved))
        conflict_text = conflict or "明示指定と承認済み割当の差を判断元へ戻す"
    else:
        conflict_text = None
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
        "conflict_resolution": conflict_text,
    }


def coverage_for(packet: dict) -> None:
    ids = sorted(
        row["assignment_id"]
        for row in packet["assignments"]
        if row["qa_requirement_ref"] == QA_REF
    )
    packet["requirement_coverage"] = [
        {
            "qa_requirement_ref": QA_REF,
            "coverage": "割当済み" if ids else "未割当",
            "assignment_ids": ids,
            "exclusion_reason": None,
        }
    ]


def base_packet() -> dict:
    packet = {
        "schema": "test-architecture-v1",
        "owner": OWNER,
        "artifact_ref": ART,
        "scope": SCOPE,
        "content_fingerprint": "0" * 64,
        "sources": sources(),
        "requirement_coverage": [],
        "assignments": [
            assignment("ARCH-001", TARGET_CONFIRM, "システム", "test-analysis既定値")
        ],
        "level_priority": [priority(TARGET_CONFIRM, default=["システム"])],
        "constraints": [],
        "open_items": [],
        "change_impacts": [],
        "history": [],
    }
    coverage_for(packet)
    return seal(packet)


def payment_packet(*, levels=("API", "システム")) -> dict:
    """承認済み割当（同一target・複数level）を含む packet。"""
    packet = base_packet()
    approval_ids = {"API": "APR-001", "システム": "APR-002"}
    rows = [
        assignment(
            f"ARCH-00{index + 2}",
            TARGET_PAYMENT,
            level,
            "承認済みarchitecture",
            basis_sources=("SRC-001",),
            approval_id=approval_ids[level],
        )
        for index, level in enumerate(levels)
    ]
    packet["assignments"].extend(rows)
    packet["level_priority"].append(
        priority(TARGET_PAYMENT, approved=list(levels), default=["システム"])
    )
    coverage_for(packet)
    return seal(packet)


def evidence_for(
    packet: dict, *, revision: str = REV, ids: dict | None = None
) -> list[dict]:
    pairs = ids or {"APR-001": ["ARCH-002"], "APR-002": ["ARCH-003"]}
    rows = []
    for approval_id, assignment_ids in pairs.items():
        rows.append(
            {
                "approval_id": approval_id,
                "artifact_ref": packet["artifact_ref"],
                "scope": packet["scope"],
                "content_fingerprint": packet["content_fingerprint"],
                "revision": revision,
                "assignment_ids": assignment_ids,
                "approver": "品質責任者",
                "approver_role": "approver",
                "evidence_ref": f"evidence:{approval_id.lower()}",
                "state": "承認済み",
            }
        )
    return rows


def readback_for(
    packet: dict, *, revision: str = REV, stored: str | None = None
) -> dict:
    text = stored if stored is not None else canon(packet).decode("utf-8")
    return {
        "owner": OWNER,
        "scope": packet["scope"],
        "artifact_ref": packet["artifact_ref"],
        "revision": revision,
        "content_hash": sha(text),
    }


def current_refs(
    *, skip: set[str] = frozenset(), extra=(), overrides=None
) -> list[dict]:
    rows = []
    for source_row in sources():
        if source_row["source_id"] in skip:
            continue
        row = {
            key: source_row[key]
            for key in ("owner", "scope", "artifact_ref", "revision", "content_hash")
        }
        if overrides and source_row["source_id"] in overrides:
            row.update(overrides[source_row["source_id"]])
        rows.append(row)
    rows.extend(extra)
    return rows


def validate_request(packet: dict, **extra) -> dict:
    return {"operation": "validate", "artifact": packet, **extra}


def completion(packet: dict, **extra) -> dict:
    return {"operation": "completion_check", "artifact": packet, **extra}


class ValidateTests(unittest.TestCase):
    def test_valid_base_packet_validates(self) -> None:
        result = call(validate_request(base_packet()))
        self.assertEqual((result["status"], result["valid"]), ("valid", True))

    def test_example_asset_validates_as_draft_and_stays_incomplete(self) -> None:
        packet = json.loads(EXAMPLE.read_text(encoding="utf-8"))
        self.assertEqual(call(validate_request(packet))["status"], "valid")
        result = call(completion(packet))
        self.assertFalse(result["complete"])
        self.assertIn("approval_missing", codes(result))

    def test_missing_required_field_is_rejected(self) -> None:
        packet = base_packet()
        del packet["assignments"][0]["data"]
        result = call(validate_request(seal(packet)))
        self.assertEqual((result["status"], result["valid"]), ("blocked", False))
        self.assertIn("field_schema_invalid", codes(result))

    def test_unknown_level_and_basis_are_rejected(self) -> None:
        for field, value in (("level", "未確定"), ("selection_basis", "推測")):
            with self.subTest(field=field):
                packet = base_packet()
                packet["assignments"][0][field] = value
                result = call(validate_request(seal(packet)))
                self.assertFalse(result["valid"])

    def test_non_qa_source_with_local_id_and_unknown_key_are_rejected(self) -> None:
        packet = base_packet()
        packet["sources"][1]["local_id"] = "QAR-009"
        self.assertFalse(call(validate_request(seal(packet)))["valid"])
        packet = base_packet()
        packet["unexpected"] = "x"
        self.assertFalse(call(validate_request(seal(packet)))["valid"])

    def test_content_fingerprint_mismatch_is_rejected(self) -> None:
        packet = base_packet()
        packet["scope"] = "other-scope"
        result = call(validate_request(packet))
        self.assertIn("content_fingerprint_mismatch", codes(result))

    def test_same_target_multiple_levels_are_kept_as_separate_rows(self) -> None:
        packet = payment_packet()
        self.assertTrue(call(validate_request(packet))["valid"])
        self.assertEqual(
            sorted(
                row["level"]
                for row in packet["assignments"]
                if row["target_ref"] == TARGET_PAYMENT
            ),
            ["API", "システム"],
        )

    def test_collapsing_multi_level_target_is_rejected_against_previous(self) -> None:
        previous = payment_packet()
        collapsed = payment_packet(levels=("API",))
        result = call(validate_request(collapsed, previous_artifact=previous))
        self.assertEqual(result["status"], "blocked")
        self.assertIn("level_collapsed", codes(result))
        self.assertTrue(call(validate_request(collapsed))["valid"])

    def test_level_priority_row_cannot_drop_a_kept_level_inside_packet(self) -> None:
        packet = payment_packet()
        packet["assignments"] = [
            row
            for row in packet["assignments"]
            if row["level"] != "システム" or row["target_ref"] != TARGET_PAYMENT
        ]
        coverage_for(packet)
        self.assertIn(
            "level_priority_mismatch", codes(call(validate_request(seal(packet))))
        )

    def test_default_and_approved_basis_cannot_mix_with_explicit_priority_rules(
        self,
    ) -> None:
        packet = payment_packet()
        for row in packet["level_priority"]:
            if row["target_ref"] == TARGET_PAYMENT:
                row["decision"] = "test-analysis既定値"
        self.assertIn(
            "level_priority_mismatch", codes(call(validate_request(seal(packet))))
        )

    def test_duplicate_assignment_key_is_rejected(self) -> None:
        packet = base_packet()
        duplicate = copy.deepcopy(packet["assignments"][0])
        duplicate["assignment_id"] = "ARCH-002"
        packet["assignments"].append(duplicate)
        coverage_for(packet)
        packet["level_priority"] = [priority(TARGET_CONFIRM, default=["システム"])]
        self.assertIn(
            "duplicate_assignment", codes(call(validate_request(seal(packet))))
        )

    def test_requirement_coverage_must_match_assignments_both_ways(self) -> None:
        packet = base_packet()
        packet["requirement_coverage"][0]["assignment_ids"] = []
        self.assertIn(
            "requirement_coverage_mismatch", codes(call(validate_request(seal(packet))))
        )
        packet = base_packet()
        packet["requirement_coverage"] = []
        self.assertIn(
            "requirement_coverage_missing", codes(call(validate_request(seal(packet))))
        )

    def test_unassigned_requirement_needs_no_assignment_refs(self) -> None:
        packet = base_packet()
        packet["assignments"] = []
        packet["level_priority"] = []
        coverage_for(packet)
        result = call(validate_request(seal(packet)))
        self.assertTrue(result["valid"])
        self.assertIn("requirement_unassigned", codes(call(completion(seal(packet)))))

    def test_approved_source_needs_concrete_evidence_ref(self) -> None:
        for placeholder in ("未設定", "unknown", "-", "失効"):
            with self.subTest(placeholder=placeholder):
                packet = base_packet()
                packet["sources"][0]["approval_evidence_ref"] = placeholder
                self.assertFalse(call(validate_request(seal(packet)))["valid"])

    def test_invalid_qa_requirement_ref_format_is_rejected(self) -> None:
        packet = base_packet()
        packet["assignments"][0]["qa_requirement_ref"] = "QAR-001"
        self.assertFalse(call(validate_request(seal(packet)))["valid"])

    def test_conflict_assignment_cannot_be_confirmed(self) -> None:
        packet = payment_packet(levels=("API",))
        for row in packet["level_priority"]:
            if row["target_ref"] == TARGET_PAYMENT:
                row["explicit_levels"] = ["受入"]
                row.update(
                    priority(TARGET_PAYMENT, explicit=["受入"], approved=["API"])
                )
        for row in packet["assignments"]:
            if row["target_ref"] == TARGET_PAYMENT:
                row["selection_basis"] = "未確定"
                row["disposition"] = "確定"
        packet["assignments"][1]["level"] = "受入"
        coverage_for(packet)
        self.assertFalse(call(validate_request(seal(packet)))["valid"])


class ReadbackTests(unittest.TestCase):
    def test_matching_readback_is_accepted_without_provider_authenticity(self) -> None:
        packet = base_packet()
        result = call(
            {
                "operation": "validate_readback",
                "candidate_artifact": packet,
                "readback": readback_for(packet),
                "expected_revision": REV,
            }
        )
        self.assertEqual(
            (result["status"], result["valid"]), ("readback_matches", True)
        )
        self.assertEqual(
            result["provider_authenticity"], "not_established_by_this_validator"
        )
        self.assertEqual(result["storage_content_sha256"], sha(canon(packet).decode()))
        self.assertEqual(result["candidate_fingerprint"], packet["content_fingerprint"])

    def test_tampered_stored_text_fails_hash(self) -> None:
        packet = base_packet()
        stored = canon(packet).decode("utf-8")
        tampered = stored.replace("staging-orders", "production-orders")
        result = call(
            {
                "operation": "validate_readback",
                "candidate_artifact": packet,
                "readback": readback_for(packet, stored=tampered),
                "expected_revision": REV,
            }
        )
        self.assertFalse(result["valid"])
        self.assertIn("readback_hash_mismatch", codes(result))

    def test_non_canonical_stored_text_is_not_accepted(self) -> None:
        packet = base_packet()
        pretty = json.dumps(packet, ensure_ascii=False, indent=2)
        result = call(
            {
                "operation": "validate_readback",
                "candidate_artifact": packet,
                "readback": readback_for(packet, stored=pretty),
                "expected_revision": REV,
            }
        )
        self.assertIn("readback_hash_mismatch", codes(result))

    def test_expected_revision_must_be_present_and_match(self) -> None:
        packet = base_packet()
        base = {
            "operation": "validate_readback",
            "candidate_artifact": packet,
            "readback": readback_for(packet),
        }
        for value in (None, "", "   "):
            with self.subTest(value=value):
                code, out, _ = run_raw(
                    json.dumps({**base, "expected_revision": value}).encode()
                )
                self.assertEqual(json.loads(out)["valid"], False)
        result = call({**base, "expected_revision": "arch-r0"})
        self.assertEqual((result["status"], result["valid"]), ("blocked", False))
        self.assertIn("readback_revision_mismatch", codes(result))
        self.assertFalse(call(base)["valid"])

    def test_other_scope_or_artifact_or_owner_is_rejected(self) -> None:
        packet = base_packet()
        for field, value in (
            ("scope", "other-scope"),
            ("artifact_ref", "artifact:other"),
            ("owner", "test-analysis"),
        ):
            with self.subTest(field=field):
                readback = readback_for(packet)
                readback[field] = value
                result = call(
                    {
                        "operation": "validate_readback",
                        "candidate_artifact": packet,
                        "readback": readback,
                        "expected_revision": REV,
                    }
                )
                self.assertIn("readback_identity_mismatch", codes(result))

    def test_other_project_artifact_is_not_accepted_for_scope(self) -> None:
        packet = base_packet()
        other = copy.deepcopy(packet)
        other["scope"] = "other-release"
        seal(other)
        result = call(
            {
                "operation": "validate_readback",
                "candidate_artifact": other,
                "readback": readback_for(packet),
                "expected_revision": REV,
            }
        )
        self.assertIn("readback_identity_mismatch", codes(result))


class ImpactTests(unittest.TestCase):
    def impact(self, packet: dict, refs) -> dict:
        request = {"operation": "impact", "artifact": packet}
        if refs is not None:
            request["current_source_refs"] = refs
        return call(request)

    def test_all_sources_current_is_current(self) -> None:
        result = self.impact(base_packet(), current_refs())
        self.assertEqual((result["status"], result["valid"]), ("current", True))

    def test_unrelated_extra_source_change_keeps_current(self) -> None:
        extra = [
            {
                "owner": "other",
                "scope": "x",
                "artifact_ref": "artifact:x",
                "revision": "r1",
                "content_hash": sha("x"),
            }
        ]
        self.assertEqual(
            self.impact(base_packet(), current_refs(extra=extra))["status"], "current"
        )

    def test_changed_test_analysis_source_impacts_only_dependent_assignments(
        self,
    ) -> None:
        packet = payment_packet()
        overrides = {"SRC-002": {"revision": "ta-r3", "content_hash": sha("ta-new")}}
        result = self.impact(packet, current_refs(overrides=overrides))
        self.assertEqual((result["status"], result["valid"]), ("incomplete", True))
        self.assertEqual(result["stale_source_ids"], ["SRC-002"])
        self.assertEqual(result["impacted_assignment_ids"], ["ARCH-001"])
        self.assertEqual(result["retained_assignment_ids"], ["ARCH-002", "ARCH-003"])
        self.assertIn(
            {"kind": "TC", "ref": "artifact:tc-orders-r1#TC-001@tc-r1"},
            result["reconfirm_refs"],
        )

    def test_missing_source_is_unknown_and_fails_closed(self) -> None:
        result = self.impact(payment_packet(), current_refs(skip={"SRC-002"}))
        self.assertEqual(result["unknown_source_ids"], ["SRC-002"])
        self.assertEqual(result["impacted_assignment_ids"], ["ARCH-001"])
        self.assertNotEqual(result["status"], "current")

    def test_empty_or_missing_or_invalid_current_refs_are_unknown(self) -> None:
        empty = self.impact(base_packet(), [])
        self.assertEqual(empty["unknown_source_ids"], ["SRC-001", "SRC-002"])
        self.assertNotEqual(empty["status"], "current")
        missing = self.impact(base_packet(), None)
        self.assertEqual((missing["status"], missing["valid"]), ("unknown", False))
        invalid = self.impact(base_packet(), "not-a-list")
        self.assertEqual((invalid["status"], invalid["valid"]), ("unknown", False))

    def test_upstream_qa_requirement_stale_impacts_its_dependents(self) -> None:
        packet = payment_packet()
        overrides = {"SRC-001": {"revision": "qra-r4", "content_hash": sha("qra-new")}}
        result = self.impact(packet, current_refs(overrides=overrides))
        self.assertEqual(
            result["impacted_assignment_ids"], ["ARCH-001", "ARCH-002", "ARCH-003"]
        )
        self.assertEqual(result["retained_assignment_ids"], [])

    def test_unapproved_upstream_qa_does_not_confirm_dependents(self) -> None:
        packet = base_packet()
        packet["sources"][0]["approval_state"] = "未承認"
        packet["sources"][0]["approval_evidence_ref"] = None
        seal(packet)
        result = self.impact(packet, current_refs())
        self.assertEqual(result["status"], "incomplete")
        self.assertEqual(result["unconfirmed_assignment_ids"], ["ARCH-001"])

    def test_unacquired_source_is_not_confirmed(self) -> None:
        packet = base_packet()
        packet["sources"][1]["acquisition"] = "未取得"
        seal(packet)
        result = self.impact(packet, current_refs())
        self.assertEqual(result["status"], "incomplete")
        self.assertEqual(result["unconfirmed_assignment_ids"], ["ARCH-001"])


class CompletionTests(unittest.TestCase):
    def test_base_packet_is_complete(self) -> None:
        result = call(completion(base_packet()))
        self.assertEqual((result["status"], result["complete"]), ("complete", True))
        self.assertEqual(
            result["approval_authenticity"], "not_established_by_this_validator"
        )

    def test_bound_approval_completes_approved_assignments(self) -> None:
        packet = payment_packet()
        result = call(
            completion(
                packet, expected_revision=REV, approval_evidence=evidence_for(packet)
            )
        )
        self.assertTrue(result["complete"], result)
        self.assertEqual(result["approved_assignment_ids"], ["ARCH-002", "ARCH-003"])
        self.assertEqual(
            result["approval_authenticity"], "not_established_by_this_validator"
        )

    def test_approval_missing_or_unapproved_or_expired_is_incomplete(self) -> None:
        packet = payment_packet()
        self.assertIn(
            "approval_missing", codes(call(completion(packet, expected_revision=REV)))
        )
        for state in ("未承認", "失効", "未設定"):
            with self.subTest(state=state):
                evidence = evidence_for(packet)
                evidence[0]["state"] = state
                result = call(
                    completion(
                        packet, expected_revision=REV, approval_evidence=evidence
                    )
                )
                self.assertFalse(result["complete"])
                self.assertIn("approval_not_approved", codes(result))

    def test_missing_approver_identity_is_incomplete(self) -> None:
        packet = payment_packet()
        for field in ("approver", "approver_role", "evidence_ref"):
            with self.subTest(field=field):
                evidence = evidence_for(packet)
                evidence[0][field] = "未設定"
                result = call(
                    completion(
                        packet, expected_revision=REV, approval_evidence=evidence
                    )
                )
                self.assertIn("approval_identity_missing", codes(result))

    def test_approval_for_old_content_or_old_revision_is_not_reused(self) -> None:
        packet = payment_packet()
        evidence = evidence_for(packet)
        changed = copy.deepcopy(packet)
        changed["assignments"][1]["measurement"] = "注文決済の観測を追加"
        seal(changed)
        result = call(
            completion(changed, expected_revision=REV, approval_evidence=evidence)
        )
        self.assertIn("approval_revision_mismatch", codes(result))
        result = call(
            completion(packet, expected_revision="arch-r0", approval_evidence=evidence)
        )
        self.assertIn("approval_revision_mismatch", codes(result))
        result = call(completion(packet, approval_evidence=evidence))
        self.assertIn("expected_revision_missing", codes(result))

    def test_approval_for_other_artifact_or_scope_is_rejected(self) -> None:
        packet = payment_packet()
        for field, value in (
            ("artifact_ref", "artifact:other"),
            ("scope", "other-scope"),
        ):
            with self.subTest(field=field):
                evidence = evidence_for(packet)
                evidence[0][field] = value
                result = call(
                    completion(
                        packet, expected_revision=REV, approval_evidence=evidence
                    )
                )
                self.assertIn("approval_identity_mismatch", codes(result))

    def test_approval_for_another_assignment_is_not_reused(self) -> None:
        packet = payment_packet()
        evidence = evidence_for(packet)
        # APR-001 covers ARCH-002 only; ARCH-003 must not be borrowed onto it.
        packet["assignments"][2]["approval_id"] = "APR-001"
        seal(packet)
        result = call(
            completion(packet, expected_revision=REV, approval_evidence=evidence)
        )
        self.assertIn("approval_assignment_mismatch", codes(result))

    def test_explicit_choice_outside_default_still_needs_approval_evidence(
        self,
    ) -> None:
        packet = payment_packet()
        for row in packet["assignments"]:
            if row["target_ref"] == TARGET_PAYMENT:
                row["selection_basis"] = "明示指定"
                row["approval_id"] = None
        packet["level_priority"][1] = priority(
            TARGET_PAYMENT, explicit=["API", "システム"], default=["システム"]
        )
        seal(packet)
        self.assertTrue(call(validate_request(packet))["valid"])
        result = call(completion(packet, expected_revision=REV))
        self.assertFalse(result["complete"])
        self.assertIn("approval_missing", codes(result))
        self.assertEqual(
            [
                issue["subject_id"]
                for issue in result["issues"]
                if issue["code"] == "approval_missing"
            ],
            ["ARCH-002"],
        )

    def test_approved_basis_without_approval_id_is_invalid(self) -> None:
        packet = payment_packet()
        packet["assignments"][1]["approval_id"] = None
        self.assertIn(
            "approval_reference_missing", codes(call(validate_request(seal(packet))))
        )

    def test_blocked_assignment_or_open_item_keeps_packet_incomplete(self) -> None:
        packet = base_packet()
        packet["assignments"][0]["disposition"] = "blocked"
        packet["assignments"][0]["exclusion_reason"] = None
        seal(packet)
        result = call(completion(packet))
        self.assertFalse(result["complete"])
        self.assertIn("assignment_blocked", codes(result))
        packet = base_packet()
        packet["open_items"] = [
            {
                "open_item_id": "OPEN-001",
                "subject_ref": TARGET_CONFIRM,
                "owner": "test-architecture-design",
                "state": "未解決",
                "resume_condition": "環境確定",
                "exclusion_reason": None,
            }
        ]
        result = call(completion(seal(packet)))
        self.assertIn("open_item_unresolved", codes(result))

    def test_unready_environment_or_placeholder_keeps_confirmed_incomplete(
        self,
    ) -> None:
        packet = base_packet()
        packet["assignments"][0]["readiness"] = "未確定"
        self.assertIn("readiness_not_ready", codes(call(completion(seal(packet)))))
        packet = base_packet()
        packet["assignments"][0]["data"] = "未確定"
        self.assertIn("placeholder_value", codes(call(completion(seal(packet)))))

    def test_unapproved_draft_is_separated_and_not_confirmed(self) -> None:
        # 承認済みarchitectureのAPI levelは、確定割当（ARCH-002）が無い限り決定を裏付けない。
        packet = payment_packet()
        packet["assignments"][1]["disposition"] = "未承認案"
        seal(packet)
        result = call(
            completion(
                packet,
                expected_revision=REV,
                approval_evidence=evidence_for(packet, ids={"APR-002": ["ARCH-003"]}),
            )
        )
        self.assertFalse(result["complete"], result)
        self.assertIn("level_unconfirmed", codes(result))
        self.assertEqual(
            [
                issue["subject_id"]
                for issue in result["issues"]
                if issue["code"] == "level_unconfirmed"
            ],
            [TARGET_PAYMENT],
        )
        self.assertNotIn("ARCH-002", result["confirmed_assignment_ids"])
        self.assertIn("ARCH-002", result["unapproved_assignment_ids"])

    def test_qa_requirement_with_only_unapproved_drafts_is_not_complete(self) -> None:
        # B-1: coverage は「割当済み」だが、対応する割当が全て未承認案の要求は完了しない。
        packet = base_packet()
        packet["assignments"][0]["disposition"] = "未承認案"
        seal(packet)
        self.assertTrue(call(validate_request(packet))["valid"])
        result = call(completion(packet))
        self.assertFalse(result["complete"], result)
        self.assertIn("requirement_unconfirmed", codes(result))
        self.assertEqual(result["confirmed_assignment_ids"], [])
        self.assertEqual(result["unapproved_assignment_ids"], ["ARCH-001"])
        subjects = [
            issue["subject_id"]
            for issue in result["issues"]
            if issue["code"] == "requirement_unconfirmed"
        ]
        self.assertEqual(subjects, [QA_REF])

    def test_approved_requirement_with_only_unapproved_drafts_is_not_complete(
        self,
    ) -> None:
        packet = payment_packet()
        for row in packet["assignments"]:
            row["disposition"] = "未承認案"
        seal(packet)
        result = call(
            completion(
                packet,
                expected_revision=REV,
                approval_evidence=evidence_for(packet),
            )
        )
        self.assertFalse(result["complete"], result)
        self.assertIn("requirement_unconfirmed", codes(result))
        self.assertEqual(result["confirmed_assignment_ids"], [])

    def test_confirmed_requirement_with_unrelated_extra_draft_stays_complete(
        self,
    ) -> None:
        # B-2: 決定済みlevelに確定割当があり、同じlevelの別方式の追加案だけが未承認。
        packet = base_packet()
        extra = assignment(
            "ARCH-002",
            TARGET_CONFIRM,
            "システム",
            "test-analysis既定値",
            disposition="未承認案",
        )
        extra["method"] = "手動実行"
        packet["assignments"].append(extra)
        coverage_for(packet)
        seal(packet)
        self.assertTrue(call(validate_request(packet))["valid"])
        result = call(completion(packet))
        self.assertTrue(result["complete"], result)
        self.assertEqual(result["confirmed_assignment_ids"], ["ARCH-001"])
        self.assertEqual(result["unapproved_assignment_ids"], ["ARCH-002"])

    def test_other_scope_draft_does_not_block_current_scope(self) -> None:
        # B-3: 完了対象は確定済み。別scopeの要求に紐づく未承認案は現scopeを止めない。
        packet = base_packet()
        other_source = source(
            "SRC-003",
            "qa_requirement",
            "test-requirements-analysis",
            "artifact:qra-other-r1",
            "qra-other-r1",
            "other-content",
            approval="承認済み",
            evidence="evidence:qra-other-approval",
            local_id="QAR-009",
        )
        other_source["scope"] = "other-scope"
        other_ref = "artifact:qra-other-r1#QAR-009@qra-other-r1"
        draft = assignment(
            "ARCH-002",
            TARGET_PAYMENT,
            "API",
            "test-analysis既定値",
            disposition="未承認案",
        )
        draft["qa_requirement_ref"] = other_ref
        draft["source_ids"] = ["SRC-003", "SRC-002"]
        packet["sources"].append(other_source)
        packet["assignments"].append(draft)
        packet["level_priority"].append(priority(TARGET_PAYMENT, default=["API"]))
        packet["requirement_coverage"].append(
            {
                "qa_requirement_ref": other_ref,
                "coverage": "割当済み",
                "assignment_ids": ["ARCH-002"],
                "exclusion_reason": None,
            }
        )
        seal(packet)
        self.assertTrue(call(validate_request(packet))["valid"])
        result = call(completion(packet))
        self.assertTrue(result["complete"], result)
        self.assertEqual(result["confirmed_assignment_ids"], ["ARCH-001"])
        self.assertEqual(result["unapproved_assignment_ids"], ["ARCH-002"])

    def test_explicit_level_only_as_unapproved_draft_keeps_range_incomplete(
        self,
    ) -> None:
        # 明示指定された必須levelが未承認案だけなら、そのtargetの範囲は完了しない。
        packet = base_packet()
        packet["assignments"] += [
            assignment(
                "ARCH-002", TARGET_PAYMENT, "API", "明示指定", disposition="未承認案"
            ),
            assignment("ARCH-003", TARGET_PAYMENT, "システム", "明示指定"),
        ]
        packet["level_priority"].append(
            priority(TARGET_PAYMENT, explicit=["API", "システム"], default=["システム"])
        )
        coverage_for(packet)
        seal(packet)
        self.assertTrue(call(validate_request(packet))["valid"])
        result = call(completion(packet))
        self.assertFalse(result["complete"], result)
        self.assertIn("level_unconfirmed", codes(result))
        self.assertEqual(result["confirmed_assignment_ids"], ["ARCH-001", "ARCH-003"])
        subjects = [
            issue["subject_id"]
            for issue in result["issues"]
            if issue["code"] == "level_unconfirmed"
        ]
        self.assertEqual(subjects, [TARGET_PAYMENT])

    def test_explicit_levels_all_confirmed_keep_each_level(self) -> None:
        packet = base_packet()
        packet["assignments"] += [
            assignment(
                "ARCH-002",
                TARGET_PAYMENT,
                "API",
                "明示指定",
                approval_id="APR-001",
            ),
            assignment("ARCH-003", TARGET_PAYMENT, "システム", "明示指定"),
        ]
        packet["level_priority"].append(
            priority(TARGET_PAYMENT, explicit=["API", "システム"], default=["システム"])
        )
        coverage_for(packet)
        seal(packet)
        result = call(
            completion(
                packet,
                expected_revision=REV,
                approval_evidence=evidence_for(packet, ids={"APR-001": ["ARCH-002"]}),
            )
        )
        self.assertTrue(result["complete"], result)
        self.assertEqual(
            result["confirmed_assignment_ids"], ["ARCH-001", "ARCH-002", "ARCH-003"]
        )

    def test_unassigned_requirement_is_not_complete(self) -> None:
        packet = base_packet()
        packet["assignments"] = []
        packet["level_priority"] = []
        coverage_for(packet)
        seal(packet)
        self.assertTrue(call(validate_request(packet))["valid"])
        result = call(completion(packet))
        self.assertFalse(result["complete"], result)
        self.assertIn("requirement_unassigned", codes(result))
        self.assertNotIn("requirement_unconfirmed", codes(result))

    def test_assigned_requirement_with_only_excluded_assignment_is_not_complete(
        self,
    ) -> None:
        packet = base_packet()
        packet["assignments"][0]["disposition"] = "対象外"
        packet["assignments"][0]["exclusion_reason"] = "対象外理由"
        seal(packet)
        result = call(completion(packet))
        self.assertFalse(result["complete"], result)
        self.assertIn("requirement_unconfirmed", codes(result))
        self.assertEqual(result["confirmed_assignment_ids"], [])

    def test_requirement_excluded_by_coverage_does_not_block_confirmed_scope(
        self,
    ) -> None:
        # coverage「対象外」は除外根拠（exclusion_reason）付きの既存契約に従い、完了を阻まない。
        packet = base_packet()
        excluded_source = source(
            "SRC-003",
            "qa_requirement",
            "test-requirements-analysis",
            "artifact:qra-excluded-r1",
            "qra-excluded-r1",
            "excluded-content",
            approval="承認済み",
            evidence="evidence:qra-excluded-approval",
            local_id="QAR-002",
        )
        excluded_ref = "artifact:qra-excluded-r1#QAR-002@qra-excluded-r1"
        packet["sources"].append(excluded_source)
        packet["requirement_coverage"].append(
            {
                "qa_requirement_ref": excluded_ref,
                "coverage": "対象外",
                "assignment_ids": [],
                "exclusion_reason": "今回のリリース範囲外",
            }
        )
        seal(packet)
        self.assertTrue(call(validate_request(packet))["valid"])
        result = call(completion(packet))
        self.assertTrue(result["complete"], result)
        self.assertEqual(result["confirmed_assignment_ids"], ["ARCH-001"])

    def test_approved_level_change_draft_beside_confirmed_level_stays_complete(
        self,
    ) -> None:
        # 承認済みlevelに既存の確定割当（承認証拠つき）があり、同levelの変更案だけが未承認。
        packet = payment_packet()
        change = assignment(
            "ARCH-004",
            TARGET_PAYMENT,
            "API",
            "承認済みarchitecture",
            basis_sources=("SRC-001",),
            approval_id="APR-003",
            disposition="未承認案",
        )
        change["method"] = "手動実行"
        packet["assignments"].append(change)
        coverage_for(packet)
        seal(packet)
        evidence = evidence_for(packet)
        result = call(
            completion(packet, expected_revision=REV, approval_evidence=evidence)
        )
        self.assertTrue(result["complete"], result)
        self.assertEqual(
            result["confirmed_assignment_ids"], ["ARCH-001", "ARCH-002", "ARCH-003"]
        )
        self.assertEqual(result["unapproved_assignment_ids"], ["ARCH-004"])

    def test_default_level_only_as_unapproved_draft_is_not_complete(self) -> None:
        # 既定値を採用したlevelが未承認案だけなら、そのtargetの範囲は完了しない。
        packet = base_packet()
        packet["assignments"][0]["disposition"] = "未承認案"
        packet["assignments"].append(
            assignment("ARCH-002", TARGET_PAYMENT, "API", "test-analysis既定値")
        )
        packet["level_priority"].append(priority(TARGET_PAYMENT, default=["API"]))
        coverage_for(packet)
        seal(packet)
        self.assertTrue(call(validate_request(packet))["valid"])
        result = call(completion(packet))
        self.assertFalse(result["complete"], result)
        self.assertNotIn("requirement_unconfirmed", codes(result))
        subjects = [
            issue["subject_id"]
            for issue in result["issues"]
            if issue["code"] == "level_unconfirmed"
        ]
        self.assertEqual(subjects, [TARGET_CONFIRM])

    def test_other_scope_confirmed_assignment_does_not_satisfy_current_level(
        self,
    ) -> None:
        # F3: 別scopeの確定割当が、同targetの現scopeの決定済みlevelを満たしてはならない。
        packet = base_packet()
        other_source = source(
            "SRC-003",
            "qa_requirement",
            "test-requirements-analysis",
            "artifact:qra-other-r1",
            "qra-other-r1",
            "other-content",
            approval="承認済み",
            evidence="evidence:qra-other-approval",
            local_id="QAR-009",
        )
        other_source["scope"] = "other-scope"
        other_ref = "artifact:qra-other-r1#QAR-009@qra-other-r1"
        in_scope_draft = assignment(
            "ARCH-002",
            TARGET_PAYMENT,
            "API",
            "test-analysis既定値",
            disposition="未承認案",
        )
        other_confirmed = assignment(
            "ARCH-003", TARGET_PAYMENT, "API", "test-analysis既定値"
        )
        other_confirmed["method"] = "手動実行"
        other_confirmed["qa_requirement_ref"] = other_ref
        other_confirmed["source_ids"] = ["SRC-003", "SRC-002"]
        packet["sources"].append(other_source)
        packet["assignments"] += [in_scope_draft, other_confirmed]
        packet["level_priority"].append(priority(TARGET_PAYMENT, default=["API"]))
        packet["requirement_coverage"][0]["assignment_ids"] = ["ARCH-001", "ARCH-002"]
        packet["requirement_coverage"].append(
            {
                "qa_requirement_ref": other_ref,
                "coverage": "割当済み",
                "assignment_ids": ["ARCH-003"],
                "exclusion_reason": None,
            }
        )
        seal(packet)
        self.assertTrue(call(validate_request(packet))["valid"])
        result = call(completion(packet))
        self.assertFalse(result["complete"], result)
        self.assertIn("level_unconfirmed", codes(result))
        self.assertNotIn("requirement_unconfirmed", codes(result))

    def test_approver_placeholder_variants_are_not_identity(self) -> None:
        # F2: 状態語・書式文字・全角・大文字小文字の揺れは承認者として採用しない。
        for approver in (
            "承認済み",
            "承\u200b認済み",
            "ｕｎｋｎｏｗｎ",
            "Approved",
            "  APPROVED  ",
        ):
            with self.subTest(approver=approver):
                packet = payment_packet()
                evidence = evidence_for(packet)
                evidence[0]["approver"] = approver
                result = call(
                    completion(
                        packet, expected_revision=REV, approval_evidence=evidence
                    )
                )
                self.assertFalse(result["complete"], result)
                self.assertIn("approval_identity_missing", codes(result))

    def test_level_conflict_is_unresolved_and_not_confirmed(self) -> None:
        packet = base_packet()
        packet["assignments"] = [
            assignment("ARCH-001", TARGET_CONFIRM, "システム", "test-analysis既定値"),
            assignment(
                "ARCH-002",
                TARGET_PAYMENT,
                "API",
                "未確定",
                basis_sources=("SRC-001",),
                disposition="未承認案",
            ),
            assignment(
                "ARCH-003",
                TARGET_PAYMENT,
                "システム",
                "未確定",
                basis_sources=("SRC-001",),
                disposition="未承認案",
            ),
        ]
        packet["level_priority"].append(
            priority(
                TARGET_PAYMENT,
                explicit=["API"],
                approved=["システム"],
                default=[],
                conflict="明示指定と承認済みの差を判断元へ戻す",
            )
        )
        coverage_for(packet)
        seal(packet)
        self.assertTrue(call(validate_request(packet))["valid"])
        result = call(completion(packet))
        self.assertFalse(result["complete"])
        self.assertIn("level_unresolved", codes(result))
        self.assertEqual(result["confirmed_assignment_ids"], ["ARCH-001"])
        self.assertEqual(result["unapproved_assignment_ids"], ["ARCH-002", "ARCH-003"])

    def test_confirmed_assignment_for_conflict_is_rejected(self) -> None:
        packet = base_packet()
        packet["assignments"].append(
            assignment(
                "ARCH-002", TARGET_PAYMENT, "API", "未確定", basis_sources=("SRC-001",)
            )
        )
        packet["level_priority"].append(
            priority(
                TARGET_PAYMENT,
                explicit=["API"],
                approved=["システム"],
                conflict="判断元へ戻す",
            )
        )
        coverage_for(packet)
        self.assertFalse(call(validate_request(seal(packet)))["valid"])

    def test_upstream_unapproved_blocks_completion(self) -> None:
        packet = base_packet()
        packet["sources"][0]["approval_state"] = "未承認"
        packet["sources"][0]["approval_evidence_ref"] = None
        self.assertIn("upstream_not_approved", codes(call(completion(seal(packet)))))

    def test_completion_with_invalid_packet_is_incomplete_not_success(self) -> None:
        packet = base_packet()
        packet["assignments"][0]["selection_basis"] = "推測"
        result = call(completion(packet))
        self.assertEqual((result["valid"], result["complete"]), (False, False))


class FailClosedTests(unittest.TestCase):
    def assert_blocked(self, raw: bytes, code: str | None = None) -> dict:
        returncode, out, err = run_raw(raw)
        self.assertEqual((returncode, err), (0, b""))
        result = json.loads(out)
        self.assertEqual((result["valid"], result["status"]), (False, "blocked"))
        if code is not None:
            self.assertIn(code, codes(result))
        return result

    def test_invalid_json_and_nul_are_rejected(self) -> None:
        self.assert_blocked(b"{not json", "invalid_json")
        self.assert_blocked(
            b'{"operation":"validate","artifact":{"a":"x\x00y"}}', "invalid_json"
        )
        packet = base_packet()
        packet["scope"] = "a\u0000b"
        raw = json.dumps({"operation": "validate", "artifact": packet}).encode()
        self.assert_blocked(raw)

    def test_duplicate_key_and_nonfinite_numbers_are_rejected(self) -> None:
        self.assert_blocked(
            b'{"operation":"validate","operation":"validate","artifact":{}}',
            "duplicate_json_key",
        )
        self.assert_blocked(
            b'{"operation":"validate","artifact":{"x":NaN}}', "invalid_json_constant"
        )

    def test_oversized_input_is_rejected(self) -> None:
        raw = b"{" + b" " * (16 * 1024 * 1024) + b"}"
        self.assert_blocked(raw, "limit_exceeded")

    def test_row_limit_is_enforced(self) -> None:
        packet = base_packet()
        packet["history"] = [
            {
                "content_fingerprint": "0" * 64,
                "replaces": None,
                "change_reason": "x",
                "impact_scope": "x",
                "reconfirm_refs": [],
            }
        ] * 501
        self.assert_blocked(
            json.dumps({"operation": "validate", "artifact": seal(packet)}).encode(),
            "limit_exceeded",
        )

    def test_unknown_operation_and_unknown_request_key_are_rejected(self) -> None:
        self.assert_blocked(
            json.dumps({"operation": "publish"}).encode(), "operation_invalid"
        )
        packet = base_packet()
        self.assert_blocked(
            json.dumps(
                {"operation": "validate", "artifact": packet, "extra": 1}
            ).encode(),
            "request_schema",
        )
        self.assert_blocked(json.dumps([1, 2]).encode(), "request_invalid")

    def test_completion_error_still_reports_incomplete(self) -> None:
        result = self.assert_blocked(
            json.dumps({"operation": "completion_check", "artifact": {}}).encode()
        )
        self.assertFalse(result["complete"])

    def test_script_has_no_network_or_write_capability_and_writes_nothing(self) -> None:
        tree = ast.parse(SCRIPT.read_text(encoding="utf-8"), filename=str(SCRIPT))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        self.assertTrue(
            imported
            <= {"__future__", "hashlib", "json", "re", "sys", "typing", "unicodedata"},
            imported,
        )
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                self.assertNotIn(
                    node.func.id, {"open", "eval", "exec", "compile", "__import__"}
                )
        with tempfile.TemporaryDirectory() as cwd:
            before = sorted(os.listdir(cwd))
            env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
            subprocess.run(
                [sys.executable, "-I", "-B", str(SCRIPT)],
                input=json.dumps(validate_request(base_packet())).encode(),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=cwd,
                env=env,
                check=True,
                timeout=60,
            )
            self.assertEqual(sorted(os.listdir(cwd)), before)

    def test_output_is_canonical_json_with_trailing_newline(self) -> None:
        returncode, out, err = run_raw(
            json.dumps(validate_request(base_packet())).encode()
        )
        self.assertEqual((returncode, err), (0, b""))
        self.assertTrue(out.endswith(b"\n"))
        self.assertEqual(out[:-1], canon(json.loads(out)))


if __name__ == "__main__":
    unittest.main()
