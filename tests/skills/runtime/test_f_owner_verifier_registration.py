"""F 3 Skill（test-requirements-analysis / test-architecture-design / test-management）の
owner verifier登録の検証。

登録後の `owner_verifiers.verify()` を通し、各Skillの本番scriptが検証を通した場合だけ
verified になること、改ざん・revision違い・source変更・承認不足・owner失敗などは
verified にならないことを確認する。承認の真正性は確立しないため、verified記録には
`approval_authenticity: "not_established_by_this_validator"` が残ることも確認する。
"""

from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[3]
SKILLS = ROOT / "skills"
sys.path.insert(0, str(SKILLS / "qa-workflow" / "scripts"))

import owner_verifiers  # noqa: E402

AUTHENTICITY = "not_established_by_this_validator"
REF_KEYS = ("owner", "scope", "artifact_ref", "revision", "content_hash")
_UNSET = object()


def canonical(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_example(skill: str, name: str) -> dict:
    return json.loads((SKILLS / skill / "assets" / name).read_text(encoding="utf-8"))


def scope(skill: str, target: str, evidence: object) -> dict:
    return {
        "skill": skill,
        "target": target,
        "execution_range": "plan",
        "input_mode": "artifact",
        "normalized_input": {"owner_verification": evidence},
        "current_structure_state": None,
    }


class StoredOwnerCases:
    """共通の検証ケース（mixin）。Skillごとの差は各サブクラスのhookで与える。"""

    skill = ""
    owner = ""
    script = ""
    example = ""
    # 承認証拠を packet の外で渡す（TA）か
    approval_evidence = False

    # --- Skillごとのhook -------------------------------------------------------
    def packet(self) -> dict:
        return load_example(self.skill, self.example)

    def revision_of(self, packet: dict) -> str:
        raise NotImplementedError

    def other_revision(self) -> str:
        raise NotImplementedError

    def refs_of(self, packet: dict) -> list[dict]:
        return [{key: row[key] for key in REF_KEYS} for row in packet["sources"]]

    def reseal(self, packet: dict) -> None:
        """packetの内容を変えた後に、Skill固有の整合値（fingerprint）を更新する。"""

    def approval_rows(self, packet: dict) -> list[dict]:
        return []

    def approved(self, packet: dict) -> dict:
        raise NotImplementedError

    def unresolved(self, packet: dict) -> None:
        raise NotImplementedError

    # --- 証拠の組立 -----------------------------------------------------------
    def evidence(
        self,
        packet: dict,
        *,
        expected: object = _UNSET,
        readback: dict | None = None,
        current: object = _UNSET,
        approvals: object = _UNSET,
        stored: str | None = None,
    ) -> dict:
        text = stored if stored is not None else canonical(packet)
        revision = self.revision_of(packet)
        claim = {
            "owner": self.owner,
            "scope": packet["scope"],
            "artifact_ref": packet["artifact_ref"],
            "revision": revision,
            "content_hash": sha(text),
        }
        claim.update(readback or {})
        evidence = {
            "stored_content": text,
            "readback": claim,
            "expected_revision": revision if expected is _UNSET else expected,
            "current_source_refs": (
                self.refs_of(packet) if current is _UNSET else current
            ),
        }
        if self.approval_evidence:
            evidence["approval_evidence"] = (
                self.approval_rows(packet) if approvals is _UNSET else approvals
            )
        return evidence

    def run_verify(self, evidence: object, target: str) -> dict:
        return owner_verifiers.verify(self.skill, scope(self.skill, target, evidence))

    def sealed(self, packet: dict) -> dict:
        self.reseal(packet)
        return packet

    def assert_verified(self, outcome: dict) -> dict:
        self.assertEqual(outcome["status"], "verified", outcome)
        return outcome["record"]

    def assert_unverified(self, outcome: dict, reason: str) -> None:
        self.assertEqual(outcome, {"status": "unverified", "reason": reason})

    # --- 共通ケース ----------------------------------------------------------
    def test_complete_stored_artifact_is_verified(self) -> None:
        packet = self.packet()
        record = self.assert_verified(
            self.run_verify(self.evidence(packet), packet["artifact_ref"])
        )
        self.assertEqual(record["skill"], self.skill)
        self.assertEqual(record["target"], packet["artifact_ref"])
        verified = record["verified_artifact"]
        self.assertEqual(verified["artifact_ref"], packet["artifact_ref"])
        self.assertEqual(verified["artifact_revision"], self.revision_of(packet))
        self.assertEqual(verified["content_hash"], sha(canonical(packet)))
        self.assertEqual(verified["approval_authenticity"], AUTHENTICITY)

    def test_tampered_stored_text_is_not_verified(self) -> None:
        packet = self.packet()
        evidence = self.evidence(packet)
        changed = copy.deepcopy(packet)
        self.tamper(changed)
        self.sealed(changed)
        evidence["stored_content"] = canonical(changed)  # readbackは元のhashのまま
        self.assert_unverified(
            self.run_verify(evidence, packet["artifact_ref"]),
            "stored_artifact_readback_not_verified",
        )

    def tamper(self, packet: dict) -> None:
        raise NotImplementedError

    def test_readback_hash_mismatch_is_not_verified(self) -> None:
        packet = self.packet()
        evidence = self.evidence(packet, readback={"content_hash": "0" * 64})
        self.assert_unverified(
            self.run_verify(evidence, packet["artifact_ref"]),
            "stored_artifact_readback_not_verified",
        )

    def test_non_canonical_stored_text_is_refused_with_its_own_reason(self) -> None:
        packet = self.packet()
        pretty = json.dumps(packet, ensure_ascii=False, indent=2)
        # readbackは同じ（非canonical）本文のhashを返す。それでも不可として扱う。
        evidence = self.evidence(packet, stored=pretty)
        self.assert_unverified(
            self.run_verify(evidence, packet["artifact_ref"]),
            "stored_content_not_canonical",
        )

    def test_revision_mismatch_is_not_verified(self) -> None:
        packet = self.packet()
        other = self.other_revision()
        self.assert_unverified(
            self.run_verify(
                self.evidence(packet, expected=other), packet["artifact_ref"]
            ),
            "artifact_revision_mismatch",
        )
        self.assert_unverified(
            self.run_verify(
                self.evidence(packet, readback={"revision": other}),
                packet["artifact_ref"],
            ),
            "artifact_revision_mismatch",
        )

    def test_expected_revision_must_be_a_real_saved_revision(self) -> None:
        packet = self.packet()
        for expected in (None, "", "   ", 1):
            with self.subTest(expected=expected):
                self.assert_unverified(
                    self.run_verify(
                        self.evidence(packet, expected=expected), packet["artifact_ref"]
                    ),
                    "owner_verification_schema_invalid",
                )
        missing = self.evidence(packet)
        del missing["expected_revision"]
        self.assert_unverified(
            self.run_verify(missing, packet["artifact_ref"]),
            "owner_verification_schema_invalid",
        )

    def test_artifact_for_another_scope_target_is_rejected(self) -> None:
        packet = self.packet()
        self.assert_unverified(
            self.run_verify(self.evidence(packet), "other-artifact-ref"),
            "artifact_ref_differs_from_scope_target",
        )

    def test_readback_for_another_case_is_not_verified(self) -> None:
        packet = self.packet()
        for claim in (
            {"owner": "another-owner"},
            {"scope": "another-scope"},
            {"artifact_ref": "another-ref"},
        ):
            with self.subTest(claim=claim):
                self.assert_unverified(
                    self.run_verify(
                        self.evidence(packet, readback=claim), packet["artifact_ref"]
                    ),
                    "stored_artifact_readback_not_verified",
                )

    def test_changed_source_is_not_current(self) -> None:
        packet = self.packet()
        changed = self.refs_of(packet)
        changed[0]["revision"] = "rev-changed"
        changed[0]["content_hash"] = "c" * 64
        self.assert_unverified(
            self.run_verify(
                self.evidence(packet, current=changed), packet["artifact_ref"]
            ),
            "source_not_current",
        )

    def test_source_that_cannot_be_obtained_is_unknown(self) -> None:
        packet = self.packet()
        target = packet["artifact_ref"]
        self.assert_unverified(
            self.run_verify(self.evidence(packet, current=[]), target),
            "source_revision_unknown",
        )
        partial = self.refs_of(packet)[1:]
        self.assert_unverified(
            self.run_verify(self.evidence(packet, current=partial), target),
            "source_revision_unknown",
        )
        malformed = self.refs_of(packet)
        malformed[0]["extra"] = "x"
        self.assert_unverified(
            self.run_verify(self.evidence(packet, current=malformed), target),
            "source_revision_unknown",
        )
        missing = self.evidence(packet)
        del missing["current_source_refs"]
        self.assert_unverified(
            self.run_verify(missing, target), "owner_verification_schema_invalid"
        )

    def test_current_impact_does_not_complete_an_unfinished_artifact(self) -> None:
        packet = self.packet()
        self.unresolved(packet)
        self.sealed(packet)
        self.assert_unverified(
            self.run_verify(self.evidence(packet), packet["artifact_ref"]),
            "completion_not_met",
        )

    def test_approval_required_but_not_approved_is_not_verified(self) -> None:
        packet = self.packet()
        self.unapprove(packet)
        self.sealed(packet)
        self.assert_unverified(
            self.run_verify(
                self.evidence(packet, approvals=[]), packet["artifact_ref"]
            ),
            "approval_not_satisfied",
        )

    def unapprove(self, packet: dict) -> None:
        raise NotImplementedError

    def test_approved_artifact_with_valid_approval_is_verified(self) -> None:
        approved = self.approved(self.packet())
        self.sealed(approved)
        record = self.assert_verified(
            self.run_verify(self.evidence(approved), approved["artifact_ref"])
        )
        self.assertEqual(
            record["verified_artifact"]["approval_authenticity"], AUTHENTICITY
        )

    def test_missing_required_field_is_schema_invalid(self) -> None:
        packet = self.packet()
        del packet[self.required_field]
        self.sealed(packet)
        self.assert_unverified(
            self.run_verify(self.evidence(packet), packet["artifact_ref"]),
            "owner_verification_schema_invalid",
        )

    def test_evidence_keys_must_match_exactly(self) -> None:
        packet = self.packet()
        extra = self.evidence(packet)
        extra["unexpected"] = "x"
        self.assert_unverified(
            self.run_verify(extra, packet["artifact_ref"]),
            "owner_verification_schema_invalid",
        )
        missing = self.evidence(packet)
        del missing["readback"]
        self.assert_unverified(
            self.run_verify(missing, packet["artifact_ref"]),
            "owner_verification_schema_invalid",
        )

    def test_stored_text_must_be_json(self) -> None:
        packet = self.packet()
        for stored, reason in (
            ("not json", "stored_content_is_not_json"),
            ("   ", "stored_content_must_be_the_stored_text"),
        ):
            with self.subTest(stored=stored):
                evidence = self.evidence(packet, stored=stored)
                self.assert_unverified(
                    self.run_verify(evidence, packet["artifact_ref"]), reason
                )

    # --- owner validatorの失敗 -----------------------------------------------
    def test_owner_script_failures_leave_the_scope_unverified(self) -> None:
        packet = self.packet()
        evidence = self.evidence(packet)
        target = packet["artifact_ref"]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            script = root / self.script
            script.parent.mkdir(parents=True, exist_ok=True)
            with mock.patch.object(owner_verifiers, "SKILLS_ROOT", root):
                script.write_text("import sys\nsys.exit(3)\n", encoding="utf-8")
                self.assert_unverified(
                    self.run_verify(evidence, target), "owner_verifier_failed"
                )
                script.write_text("print('not json')\n", encoding="utf-8")
                self.assert_unverified(
                    self.run_verify(evidence, target), "owner_verifier_output_invalid"
                )
        with mock.patch.object(owner_verifiers, "SKILLS_ROOT", Path("/nonexistent")):
            self.assert_unverified(
                self.run_verify(evidence, target), "owner_verifier_unavailable"
            )
        with mock.patch.object(
            owner_verifiers.subprocess,
            "run",
            side_effect=subprocess.TimeoutExpired(cmd="owner", timeout=1),
        ):
            self.assert_unverified(
                self.run_verify(evidence, target), "owner_verifier_unavailable"
            )


class RequirementsRegistrationTests(StoredOwnerCases, unittest.TestCase):
    skill = "test-requirements-analysis"
    owner = "test-requirements-analysis"
    script = "test-requirements-analysis/scripts/qa_requirement_runtime.py"
    example = "packet-example.json"
    required_field = "purpose"

    def revision_of(self, packet: dict) -> str:
        return str(packet["revision"])

    def other_revision(self) -> str:
        return "2"

    def tamper(self, packet: dict) -> None:
        packet["requirements"][0]["statement"] = "改ざん後の文"

    def unresolved(self, packet: dict) -> None:
        # 未解決のQA要求（open requirement）と、その未解決のopen itemを対で置く。
        packet["requirements"][0]["state"] = "未解決"
        packet["requirements"][0]["open_item_id"] = "OI-001"
        packet["open_items"] = [
            {
                "item_id": "OI-001",
                "requirement_id": "QAR-001",
                "impact_scope": ["orders-release-q4"],
                "owner": "test-requirements-analysis",
                "state": "未解決",
                "resume_condition": "QA責任者の確認後",
            }
        ]

    def unapprove(self, packet: dict) -> None:
        packet["approval"] = {
            "not_required_reason": None,
            "record": None,
            "state": "未承認",
        }

    def approved(self, packet: dict) -> dict:
        packet["status"] = "承認済み"
        packet["approval"] = {
            "not_required_reason": None,
            "record": {
                "approver": "QA責任者",
                "artifact_ref": packet["artifact_ref"],
                "evidence_ref": "evidence:ra-approval-r1",
                "expiry_condition": "要件改版まで",
                "revision": packet["revision"],
                "role": "QA責任者",
                "scope": packet["scope"],
            },
            "state": "承認済み",
        }
        return packet

    def test_approved_artifact_without_approver_is_schema_invalid(self) -> None:
        approved = self.approved(self.packet())
        approved["approval"]["record"]["approver"] = ""
        self.sealed(approved)
        self.assert_unverified(
            self.run_verify(self.evidence(approved), approved["artifact_ref"]),
            "owner_verification_schema_invalid",
        )

    def test_old_revision_approval_reuse_is_schema_invalid(self) -> None:
        approved = self.approved(self.packet())
        approved["approval"]["record"]["revision"] = 0
        self.sealed(approved)
        self.assert_unverified(
            self.run_verify(self.evidence(approved), approved["artifact_ref"]),
            "owner_verification_schema_invalid",
        )


class ArchitectureRegistrationTests(StoredOwnerCases, unittest.TestCase):
    skill = "test-architecture-design"
    owner = "test-architecture-design"
    script = "test-architecture-design/scripts/architecture_runtime.py"
    example = "packet-example.json"
    approval_evidence = True
    required_field = "constraints"

    def revision_of(self, packet: dict) -> str:
        return "ta-r1"

    def other_revision(self) -> str:
        return "ta-r2"

    def reseal(self, packet: dict) -> None:
        # architecture_runtime.fingerprint: SHA-256 of canonical JSON of the packet body.
        body = {k: v for k, v in packet.items() if k != "content_fingerprint"}
        packet["content_fingerprint"] = sha(canonical(body))

    def tamper(self, packet: dict) -> None:
        packet["assignments"][0]["measurement"] = "改ざん後の測定"

    def approval_rows(self, packet: dict) -> list[dict]:
        return [
            {
                "approval_id": approval_id,
                "artifact_ref": packet["artifact_ref"],
                "scope": packet["scope"],
                "content_fingerprint": packet["content_fingerprint"],
                "revision": "ta-r1",
                "assignment_ids": [assignment_id],
                "approver": "QA責任者",
                "approver_role": "QA責任者",
                "evidence_ref": f"evidence:{approval_id}",
                "state": "承認済み",
            }
            for approval_id, assignment_id in (
                ("APR-001", "ARCH-002"),
                ("APR-002", "ARCH-003"),
            )
        ]

    def unresolved(self, packet: dict) -> None:
        packet["assignments"][0]["automation"] = "未確定"

    def unapprove(self, packet: dict) -> None:
        # 承認が必要な ARCH-002 / ARCH-003 の証拠が無い状態にする（呼出しで approvals=[]）。
        return None

    def approved(self, packet: dict) -> dict:
        return packet

    def test_approval_evidence_must_be_present_for_each_required_assignment(
        self,
    ) -> None:
        packet = self.packet()
        self.assert_unverified(
            self.run_verify(
                self.evidence(packet, approvals=[]), packet["artifact_ref"]
            ),
            "approval_not_satisfied",
        )
        self.assert_unverified(
            self.run_verify(
                self.evidence(packet, approvals=self.approval_rows(packet)[:1]),
                packet["artifact_ref"],
            ),
            "approval_not_satisfied",
        )

    def test_unapproved_evidence_is_not_verified(self) -> None:
        packet = self.packet()
        rows = self.approval_rows(packet)
        rows[0]["state"] = "未承認"
        self.assert_unverified(
            self.run_verify(
                self.evidence(packet, approvals=rows), packet["artifact_ref"]
            ),
            "approval_not_satisfied",
        )

    def test_approval_for_an_old_revision_or_fingerprint_is_not_reused(self) -> None:
        packet = self.packet()
        old_revision = self.approval_rows(packet)
        for row in old_revision:
            row["revision"] = "ta-r0"
        self.assert_unverified(
            self.run_verify(
                self.evidence(packet, approvals=old_revision), packet["artifact_ref"]
            ),
            "approval_not_satisfied",
        )
        old_fingerprint = self.approval_rows(packet)
        for row in old_fingerprint:
            row["content_fingerprint"] = "0" * 64
        self.assert_unverified(
            self.run_verify(
                self.evidence(packet, approvals=old_fingerprint), packet["artifact_ref"]
            ),
            "approval_not_satisfied",
        )

    def test_approval_without_approver_identity_is_not_verified(self) -> None:
        packet = self.packet()
        rows = self.approval_rows(packet)
        rows[1]["approver"] = ""
        self.assert_unverified(
            self.run_verify(
                self.evidence(packet, approvals=rows), packet["artifact_ref"]
            ),
            "approval_not_satisfied",
        )

    def test_approval_evidence_must_be_a_list(self) -> None:
        packet = self.packet()
        self.assert_unverified(
            self.run_verify(
                self.evidence(packet, approvals={"APR-001": []}), packet["artifact_ref"]
            ),
            "owner_verification_schema_invalid",
        )

    def test_approved_assignments_with_matching_evidence_are_verified(self) -> None:
        packet = self.packet()
        record = self.assert_verified(
            self.run_verify(
                self.evidence(packet, approvals=self.approval_rows(packet)),
                packet["artifact_ref"],
            )
        )
        self.assertIsNotNone(record["verified_artifact"]["candidate_fingerprint"])


class ManagementRegistrationTests(StoredOwnerCases, unittest.TestCase):
    skill = "test-management"
    owner = "test-management"
    script = "test-management/scripts/management_runtime.py"
    example = "plan-packet.example.json"
    required_field = "criteria"

    def revision_of(self, packet: dict) -> str:
        return packet["revision"]

    def other_revision(self) -> str:
        return "tm-rev-0002"

    def reseal(self, packet: dict) -> None:
        # 監視件数は owner の build_snapshot による再計算値に合わせる（fixtureの作成）。
        # 件数不一致を作るテストは reseal を呼ばない。
        if packet.get("monitoring") is None:
            return
        completed = subprocess.run(
            [sys.executable, "-B", str(SKILLS / self.script)],
            input=json.dumps(
                {"operation": "build_snapshot", "artifact": packet}
            ).encode("utf-8"),
            capture_output=True,
            check=True,
        )
        built = json.loads(completed.stdout.decode("utf-8"))
        if "counts" in built:
            packet["monitoring"]["counts"] = built["counts"]

    def refs_of(self, packet: dict) -> list[dict]:
        return [
            {key: row[key] for key in REF_KEYS} for row in packet["planned_sources"]
        ]

    def tamper(self, packet: dict) -> None:
        packet["plan_items"][0]["effort"] = "改ざん後の工数"

    def unresolved(self, packet: dict) -> None:
        # 未取得の母集団: identity・readback参照・0件確認を持たず、currentnessはunknown。
        row = packet["readbacks"][0]
        row.update(
            acquisition_state="未取得",
            actual=None,
            readback_ref=None,
            zero_check=None,
            reason="fixture: 取得できず",
            execution_state="未実行",
            outcome="-",
            currentness="unknown",
        )

    def unapprove(self, packet: dict) -> None:
        packet["approval"] = {"record": None, "state": "未承認"}

    def approved(self, packet: dict) -> dict:
        packet["approval"] = {
            "record": {
                "approver": "QA責任者",
                "artifact_ref": packet["artifact_ref"],
                "evidence_ref": "evidence:tm-approval-r1",
                "revision": packet["revision"],
                "role": "QA責任者",
                "scope": packet["scope"],
            },
            "state": "承認済み",
        }
        return packet

    def test_approved_artifact_without_approver_is_schema_invalid(self) -> None:
        approved = self.approved(self.packet())
        approved["approval"]["record"]["approver"] = ""
        self.sealed(approved)
        self.assert_unverified(
            self.run_verify(self.evidence(approved), approved["artifact_ref"]),
            "owner_verification_schema_invalid",
        )

    def test_old_revision_approval_reuse_is_schema_invalid(self) -> None:
        approved = self.approved(self.packet())
        approved["approval"]["record"]["revision"] = "tm-rev-0000"
        self.sealed(approved)
        self.assert_unverified(
            self.run_verify(self.evidence(approved), approved["artifact_ref"]),
            "owner_verification_schema_invalid",
        )

    def test_unknown_result_blocks_completion(self) -> None:
        # 取得済みだが結果不明（結果不明は理由が必要で outcome を持たない）。
        packet = self.packet()
        packet["readbacks"][0].update(
            execution_state="結果不明",
            outcome="-",
            reason="fixture: 結果を確認できない",
        )
        self.sealed(packet)
        self.assert_unverified(
            self.run_verify(self.evidence(packet), packet["artifact_ref"]),
            "completion_not_met",
        )

    def test_monitoring_count_mismatch_is_not_verified(self) -> None:
        packet = self.packet()
        packet["monitoring"]["counts"]["pass"] = 99
        self.assert_unverified(
            self.run_verify(self.evidence(packet), packet["artifact_ref"]),
            "owner_verification_schema_invalid",
        )


class UnregisteredSkillTests(unittest.TestCase):
    def test_unregistered_skill_stays_fail_closed(self) -> None:
        for skill in ("defect-management", "test-evaluation"):
            with self.subTest(skill=skill):
                self.assertEqual(
                    owner_verifiers.verify(skill, scope(skill, "x", {})),
                    {
                        "status": "unverified",
                        "reason": owner_verifiers.NOT_REGISTERED,
                    },
                )


if __name__ == "__main__":
    unittest.main()
