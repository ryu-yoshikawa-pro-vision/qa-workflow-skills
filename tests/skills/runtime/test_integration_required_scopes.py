"""統合・回帰シナリオ: qa-workflow の必須scope宣言（requested_scopes）と owner verifier。

対象は F 3 Skill（test-requirements-analysis / test-architecture-design / test-management）の
保存→読戻し→検証、e2e-test-selection の currentness、test-reporting の部分開始、
未登録Skillの fail-closed である。`workflow_runtime.py` は CLI として subprocess で呼び、
`owner_verifiers.verify` も直接使う。他のテストモジュールの helper は import しない。

注意: 本ファイルの「保存・読戻し」は呼出し側の fixture（FixtureProvider）であり、実providerの
読戻しではない。fixture の成功を実providerの読戻し成功として扱わない。承認の真正性は
owner validator が確立しないため、`approval_authenticity` は常に
`not_established_by_this_validator` のままである。
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
REPORTING_SCRIPT = SKILLS / "test-reporting" / "scripts" / "reporting_runtime.py"
sys.path.insert(0, str(SKILLS / "qa-workflow" / "scripts"))

import owner_verifiers  # noqa: E402

WORKFLOW_REF = "00000000-0000-4000-8000-0000000000a1"
RA = "test-requirements-analysis"
TA = "test-architecture-design"
TM = "test-management"
RPT = "test-reporting"
E2E = "e2e-test-selection"
UNREGISTERED = "defect-management"
APPROVAL_AUTHENTICITY = "not_established_by_this_validator"
REF_KEYS = ("owner", "scope", "artifact_ref", "revision", "content_hash")
CHILD_ENV = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}

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

# owner ごとの保存成果物: (example の所属Skill, example ファイル, source refs のキー)。
EXAMPLES = {
    RA: (RA, "packet-example.json", "sources"),
    TA: (TA, "packet-example.json", "sources"),
    TM: (TM, "plan-packet.example.json", "planned_sources"),
}


def canonical(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def flip_last_char(text: str) -> str:
    return text[:-1] + ("Z" if text[-1] != "Z" else "Y")


def load_example(skill: str, name: str) -> dict:
    return json.loads((SKILLS / skill / "assets" / name).read_text(encoding="utf-8"))


def revision_of(skill: str, packet: dict) -> str:
    # TA の packet は revision を持たないため、保存時のrevisionラベルを固定値にする。
    if skill == TA:
        return "ta-r1"
    return str(packet["revision"])


class FixtureProvider:
    """呼出し側の保存・読戻しを模した fixture（実providerではない）。

    save は本文の sha256 と owner / scope / artifact_ref / revision を記録し、readback は
    その時点の記録から読戻し証拠を作る。別writerの save で revision が進んだ状態は、
    後から save し直した読戻しとして再現する（保存基盤のCASそのものは対象外）。
    """

    def __init__(self) -> None:
        self.rows: dict[str, dict] = {}

    def save(
        self, ref: str, text: str, *, owner: str, scope: str, revision: str
    ) -> None:
        self.rows[ref] = {
            "text": text,
            "owner": owner,
            "scope": scope,
            "artifact_ref": ref,
            "revision": revision,
        }

    def readback(self, ref: str) -> dict:
        row = self.rows[ref]
        return {
            "owner": row["owner"],
            "scope": row["scope"],
            "artifact_ref": row["artifact_ref"],
            "revision": row["revision"],
            "content_hash": sha(row["text"]),
        }


class Stored:
    """保存済みのF 3 Skill成果物（canonical JSON）と、その検証証拠の組立。"""

    def __init__(self, skill: str, store: FixtureProvider, packet: dict | None = None):
        self.skill = skill
        self.store = store
        owner, example, sources_key = EXAMPLES[skill]
        self.packet = packet if packet is not None else load_example(owner, example)
        self.ref = self.packet["artifact_ref"]
        self.text = canonical(self.packet)
        self.revision = revision_of(skill, self.packet)
        self.sources_key = sources_key
        store.save(
            self.ref,
            self.text,
            owner=skill,
            scope=self.packet["scope"],
            revision=self.revision,
        )

    def refs(self) -> list[dict]:
        return [
            {key: row[key] for key in REF_KEYS} for row in self.packet[self.sources_key]
        ]

    def approval_rows(self) -> list[dict]:
        # test-architecture-design の承認証拠（承認が必要な ARCH-002 / ARCH-003）。
        return [
            {
                "approval_id": approval_id,
                "artifact_ref": self.packet["artifact_ref"],
                "scope": self.packet["scope"],
                "content_fingerprint": self.packet["content_fingerprint"],
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

    def evidence(self) -> dict:
        """保存本文・読戻し（fixture）・expected_revision・current source refs の証拠。"""
        value = {
            "stored_content": self.text,
            "readback": self.store.readback(self.ref),
            "expected_revision": self.revision,
            "current_source_refs": self.refs(),
        }
        if self.skill == TA:
            value["approval_evidence"] = self.approval_rows()
        return value


def owner_scope(skill: str, target: str, evidence: object) -> dict:
    return {
        "skill": skill,
        "target": target,
        "execution_range": "plan",
        "input_mode": "artifact",
        "normalized_input": {"owner_verification": evidence},
        "current_structure_state": None,
    }


def required(skill: str, target: str | None = None) -> dict:
    return {
        "skill": skill,
        "target": target,
        "execution_range": "plan",
        "requirement": "required",
    }


def excluded(skill: str, approval_ref: str | None = "APPROVAL-001") -> dict:
    row = {
        "skill": skill,
        "target": None,
        "execution_range": "plan",
        "requirement": "excluded_by_approval",
    }
    if approval_ref is not None:
        row["approval_ref"] = approval_ref
    return row


def run_workflow(
    requested: object,
    scopes: list[dict],
    *,
    input_extra: dict | None = None,
) -> dict:
    """workflow_runtime.py をCLIとして呼ぶ（既存テストと同じ stdin/stdout 契約）。

    requested が None の場合は requested_scopes を入力から省く（未宣言の再現）。
    """
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
    value.update(input_extra or {})
    payload = {"metadata": copy.deepcopy(METADATA), "input": value}
    completed = subprocess.run(
        [sys.executable, "-B", str(WORKFLOW_SCRIPT)],
        input=json.dumps(payload).encode("utf-8"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=ROOT,
        env=CHILD_ENV,
        check=False,
    )
    if completed.stderr:
        raise AssertionError(completed.stderr.decode("utf-8"))
    return json.loads(completed.stdout)


def unverified_reasons(result: dict) -> dict[str, str]:
    return {
        row["skill"]: row["reason"] for row in result["payload"]["unverified_scopes"]
    }


def verified_skills(result: dict) -> list[str]:
    return [row["skill"] for row in result["payload"]["verified_owner_scopes"]]


def issue_types(result: dict) -> set[str]:
    return {issue["issue_type"] for issue in result["issues"]}


def blocked(result: dict) -> bool:
    payload = result.get("payload") or {}
    return payload.get("can_complete") is not True


# --- e2e-test-selection の最小 packet（test_e2e_selection_contract の selection() と同形を自前で組む）
def selection_packet() -> dict:
    return {
        "schema_version": "e2e-selection-v1",
        "selection_ref": "E2ESEL-001",
        "revision": 1,
        "change_reason": "初回のE2E自動化価値判断",
        "scope_refs": ["TI-001"],
        "automation_goal": "checkout経路の反復回帰確認",
        "population_complete": True,
        "source_refs": [
            {"ref": "SPEC-001", "revision": "s8", "currentness": "current"},
            {"ref": "TI-001", "revision": "i4", "currentness": "current"},
        ],
        "candidates": [
            {
                "candidate_id": "E2E-CAND-001",
                "candidate_key": "checkout-primary",
                "source_refs": ["SPEC-001", "TI-001"],
                "decision": "selected",
                "rationale": "主要業務経路で繰り返し確認する価値がある",
            },
            {
                "candidate_id": "E2E-CAND-002",
                "candidate_key": "non-payment",
                "source_refs": ["SPEC-001", "TI-001"],
                "decision": "not_selected",
                "rationale": "currentな既存E2Eで同じ経路を確認済み",
            },
        ],
        "history": [],
        "retired_candidates": [],
        "blockers": [],
    }


class SelectionStored:
    """保存済みの E2E selection（fixture の保存・読戻し経由）。"""

    def __init__(self, store: FixtureProvider, packet: dict | None = None) -> None:
        self.packet = packet if packet is not None else selection_packet()
        self.ref = self.packet["selection_ref"]
        self.text = canonical(self.packet)
        self.revision = "git:" + "a" * 40
        store.save(
            self.ref, self.text, owner=E2E, scope="selection", revision=self.revision
        )
        self.store = store

    def evidence(self, current: dict[str, str] | None = None) -> dict:
        current_map = current or {
            row["ref"]: row["revision"] for row in self.packet["source_refs"]
        }
        return {
            "stored_content": self.text,
            "readback": {"revision": self.revision, "content_hash": sha(self.text)},
            "current_source_revisions": current_map,
        }


# --- test-reporting の最小 build input（test_pr32_test_reporting の base_input と同形を自前で組む）
def _record(unit: str, ref: str) -> dict:
    return {
        "result_ref": f"res:{unit}:{ref}",
        "unit_ref": ref,
        "unit": unit,
        "state": "PASS",
        "build_ref": "build:41",
        "environment_ref": "env:stg",
        "result_finalized": True,
        "cleanup_status": "成功",
    }


def _retrieval(source_id: str, records: list[dict]) -> dict:
    return {
        "source_id": source_id,
        "status": "complete",
        "pagination_complete": True,
        "permission_ok": True,
        "source_revision": "rev1",
        "retrieved_at": "2026-11-10T00:00:00+00:00",
        "records": records,
    }


def _planned(source_id: str, kind: str, unit: str, refs: list[str]) -> dict:
    return {
        "source_id": source_id,
        "owner_skill": "owner",
        "kind": kind,
        "unit": unit,
        "expected_refs": refs,
    }


def report_build_input() -> dict:
    return {
        "plan": {
            "plan_ref": "plan:qa-1",
            "plan_revision": "p3",
            "approval_state": "approved",
            "scope_ref": "scope:checkout",
            "build_ref": "build:41",
            "environment_ref": "env:stg",
            "planned_sources": [
                _planned("e2e", "e2e", "logical_primary", ["T1", "T2"]),
                _planned("api", "api", "test", ["A1", "A2", "A3"]),
            ],
            "exit_criteria": [
                {
                    "criterion_id": "EX-1",
                    "metric": "pass_rate",
                    "operator": ">=",
                    "threshold": 1.0,
                    "source_ids": ["e2e"],
                },
                {
                    "criterion_id": "EX-2",
                    "metric": "fail_count",
                    "operator": "<=",
                    "threshold": 0,
                    "source_ids": ["e2e"],
                },
            ],
        },
        "retrievals": [
            _retrieval(
                "e2e",
                [_record("logical_primary", "T1"), _record("logical_primary", "T2")],
            ),
            _retrieval(
                "api",
                [_record("test", "A1"), _record("test", "A2"), _record("test", "A3")],
            ),
        ],
        "current_source_revisions": {"e2e": "rev1", "api": "rev1"},
        "current_plan_revision": "p3",
    }


def report_evidence() -> tuple[dict, str]:
    build_input = report_build_input()
    completed = subprocess.run(
        [sys.executable, "-B", str(REPORTING_SCRIPT), "build-snapshot"],
        input=json.dumps(build_input).encode("utf-8"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=CHILD_ENV,
        check=True,
    )
    snapshot = json.loads(completed.stdout)
    return {
        "build_input_content": canonical(build_input),
        "stored_snapshot_content": canonical(snapshot),
        "current": {
            "plan_revision": "p3",
            "source_revisions": {"e2e": "rev1", "api": "rev1"},
        },
    }, snapshot["snapshot_ref"]


class IntegrationScenarioTests(unittest.TestCase):
    """qa-workflow（workflow_runtime CLI）と owner_verifiers.verify の統合シナリオ。"""

    def setUp(self) -> None:
        self.store = FixtureProvider()
        self.arts = {skill: Stored(skill, self.store) for skill in (RA, TA, TM)}

    def scopes_for(self, *skills: str) -> list[dict]:
        return [
            owner_scope(skill, self.arts[skill].ref, self.arts[skill].evidence())
            for skill in skills
        ]

    def requested_for(self, *skills: str) -> list[dict]:
        return [required(skill, self.arts[skill].ref) for skill in skills]

    def assert_complete(self, result: dict) -> None:
        self.assertEqual(result["runtime_status"], "ok", result)
        self.assertTrue(result["payload"]["can_complete"], result)
        self.assertEqual(result["result_status"], "ready", result)

    # --- 正常系 -------------------------------------------------------------------

    def test_n1_three_f_scopes_complete_only_when_all_are_verified(self) -> None:
        # 期待結果: RA/TA/TM の3 scope を要求集合に宣言し、保存→読戻し→検証の証拠を渡すと、
        #   各 owner_verifiers.verify が verified、workflow は can_complete=true、
        #   verified_owner_scopes は3件、unverified_scopes と issues は空。
        #   TA の記録は approval_authenticity = not_established_by_this_validator。
        for skill in (RA, TA, TM):
            with self.subTest(skill=skill):
                art = self.arts[skill]
                outcome = owner_verifiers.verify(
                    skill, owner_scope(skill, art.ref, art.evidence())
                )
                self.assertEqual(outcome["status"], "verified", outcome)
        result = run_workflow(
            self.requested_for(RA, TA, TM), self.scopes_for(RA, TA, TM)
        )
        self.assert_complete(result)
        self.assertEqual(sorted(verified_skills(result)), sorted([RA, TA, TM]))
        self.assertEqual(result["payload"]["unverified_scopes"], [])
        self.assertEqual(result["payload"]["missing_requested_scopes"], [])
        self.assertEqual(result["issues"], [])
        ta_record = next(
            row
            for row in result["payload"]["verified_owner_scopes"]
            if row["skill"] == TA
        )
        self.assertEqual(
            ta_record["verified_artifact"]["approval_authenticity"],
            APPROVAL_AUTHENTICITY,
        )

    def test_n2_current_artifacts_are_reused_with_the_same_result(self) -> None:
        # 期待結果: 同じ保存済み成果物を再検証すると、verified の記録が同一になり、
        #   workflow の判定も同じ（can_complete=true）。current な成果物の再利用に副作用がない。
        for skill in (RA, TA, TM):
            art = self.arts[skill]
            first = owner_verifiers.verify(
                skill, owner_scope(skill, art.ref, art.evidence())
            )
            second = owner_verifiers.verify(
                skill, owner_scope(skill, art.ref, art.evidence())
            )
            with self.subTest(skill=skill):
                self.assertEqual(first, second)
                self.assertEqual(first["status"], "verified", first)
        first_run = run_workflow(
            self.requested_for(RA, TA, TM), self.scopes_for(RA, TA, TM)
        )
        second_run = run_workflow(
            self.requested_for(RA, TA, TM), self.scopes_for(RA, TA, TM)
        )
        self.assert_complete(first_run)
        self.assertEqual(
            first_run["payload"]["verified_owner_scopes"],
            second_run["payload"]["verified_owner_scopes"],
        )
        self.assertEqual(first_run["payload"], second_run["payload"])

    def test_n3_each_required_f_scope_is_needed_for_completion(self) -> None:
        # 期待結果: 3 scope のどれか1つを workflow_scopes から欠くと、要求集合にあるため
        #   can_complete=false、missing_requested_scopes に欠けたSkillが入り、
        #   required_scope_missing が出る。3つ揃えたときだけ完了する（N1 と対）。
        for missing in (RA, TA, TM):
            with self.subTest(missing=missing):
                present = [skill for skill in (RA, TA, TM) if skill != missing]
                result = run_workflow(
                    self.requested_for(RA, TA, TM), self.scopes_for(*present)
                )
                self.assertFalse(result["payload"]["can_complete"], result)
                self.assertEqual(
                    [
                        row["skill"]
                        for row in result["payload"]["missing_requested_scopes"]
                    ],
                    [missing],
                )
                self.assertIn("required_scope_missing", issue_types(result))

    # --- 部分開始 -----------------------------------------------------------------

    def test_p1_architecture_only_start_does_not_force_other_skills(self) -> None:
        # 期待結果: 既存QA要求から architecture だけを要求集合に宣言して開始すると、
        #   RA / TM を強制せず、TA が verified なら can_complete=true。
        #   missing_requested_scopes と unrequested_scopes は空。
        result = run_workflow(self.requested_for(TA), self.scopes_for(TA))
        self.assert_complete(result)
        self.assertEqual(verified_skills(result), [TA])
        self.assertEqual(result["payload"]["missing_requested_scopes"], [])
        self.assertEqual(result["payload"]["unrequested_scopes"], [])

    def test_p2_plan_only_start_from_existing_architecture(self) -> None:
        # 期待結果: 既存 architecture を前提に、計画（test-management）だけを要求して開始すると、
        #   TM が verified で can_complete=true。RA / TA の不在は不足として扱わない。
        result = run_workflow(self.requested_for(TM), self.scopes_for(TM))
        self.assert_complete(result)
        self.assertEqual(verified_skills(result), [TM])
        self.assertEqual(result["payload"]["missing_requested_scopes"], [])

    def test_p3_report_only_request_does_not_force_upstream_steps(self) -> None:
        # 期待結果: test-reporting だけを要求すると、上流の要求分析・設計・計画を強制せず、
        #   報告 snapshot が verified なら can_complete=true。
        evidence, ref = report_evidence()
        scope = owner_scope(RPT, ref, evidence)
        requested = [required(RPT, ref)]
        result = run_workflow(requested, [scope])
        self.assert_complete(result)
        self.assertEqual(verified_skills(result), [RPT])
        self.assertEqual(result["payload"]["missing_requested_scopes"], [])

    def test_p4_unregistered_or_blocked_scope_keeps_independent_verified_scopes(
        self,
    ) -> None:
        # 期待結果: TA は verified、TM は source 変更で局所 blocked、DM は未登録で
        #   fail-closed。workflow は can_complete=false だが、TA の verified 記録は失われない。
        #   unverified の理由は TM=source_not_current、DM=owner_verifier_not_registered。
        tm_refs = self.arts[TM].refs()
        tm_refs[0]["revision"] = "rev-changed"
        tm_refs[0]["content_hash"] = "c" * 64
        tm_scope = owner_scope(
            TM,
            self.arts[TM].ref,
            {**self.arts[TM].evidence(), "current_source_refs": tm_refs},
        )
        dm_scope = {
            "skill": UNREGISTERED,
            "target": "dm-target",
            "execution_range": "plan",
            "input_mode": "artifact",
            "normalized_input": {},
            "current_structure_state": None,
        }
        requested = [
            required(TA, self.arts[TA].ref),
            required(TM, self.arts[TM].ref),
            required(UNREGISTERED, "dm-target"),
        ]
        result = run_workflow(requested, [self.scopes_for(TA)[0], tm_scope, dm_scope])
        self.assertFalse(result["payload"]["can_complete"], result)
        self.assertEqual(verified_skills(result), [TA])
        self.assertEqual(
            unverified_reasons(result),
            {TM: "source_not_current", UNREGISTERED: "owner_verifier_not_registered"},
        )
        ta_record = result["payload"]["verified_owner_scopes"][0]
        self.assertEqual(
            ta_record["verified_artifact"]["content_hash"],
            self.store.readback(self.arts[TA].ref)["content_hash"],
        )

    # --- 異常系 -------------------------------------------------------------------

    def test_a1_omitted_required_skill_blocks_completion(self) -> None:
        # 期待結果: 要求集合に RA / TA / TM の3つを宣言し、workflow_scopes に2つだけ入れると
        #   can_complete=false、missing_requested_scopes=[TM]、required_scope_missing。
        result = run_workflow(self.requested_for(RA, TA, TM), self.scopes_for(RA, TA))
        self.assertFalse(result["payload"]["can_complete"], result)
        self.assertEqual(
            result["payload"]["missing_requested_scopes"],
            [
                {
                    "skill": TM,
                    "target": self.arts[TM].ref,
                    "execution_range": "plan",
                }
            ],
        )
        self.assertIn("required_scope_missing", issue_types(result))

    def test_a2_unverified_artifact_does_not_complete_or_hide_others(self) -> None:
        # 期待結果: TA の readback hash が保存本文と一致しない（未検証の成果物の混入）と、
        #   TA は stored_artifact_readback_not_verified で未検証、RA / TM は verified のまま。
        #   can_complete=false。
        ta_art = self.arts[TA]
        ta_evidence = ta_art.evidence()
        ta_evidence["readback"] = {**ta_evidence["readback"], "content_hash": "0" * 64}
        result = run_workflow(
            self.requested_for(RA, TA, TM),
            [
                owner_scope(RA, self.arts[RA].ref, self.arts[RA].evidence()),
                owner_scope(TA, ta_art.ref, ta_evidence),
                owner_scope(TM, self.arts[TM].ref, self.arts[TM].evidence()),
            ],
        )
        self.assertFalse(result["payload"]["can_complete"], result)
        self.assertEqual(
            unverified_reasons(result),
            {TA: "stored_artifact_readback_not_verified"},
        )
        self.assertEqual(sorted(verified_skills(result)), sorted([RA, TM]))

    def test_a2_owner_validation_failure_is_not_verified(self) -> None:
        # 期待結果: 必須項目（criteria）を欠く TM 成果物は、読戻し hash が一致していても
        #   owner の validate で owner_verification_schema_invalid となり、完了しない。
        packet = load_example(TM, "plan-packet.example.json")
        del packet["criteria"]
        broken = Stored(TM, self.store, packet=packet)
        outcome = owner_verifiers.verify(
            TM, owner_scope(TM, broken.ref, broken.evidence())
        )
        self.assertEqual(
            outcome,
            {"status": "unverified", "reason": "owner_verification_schema_invalid"},
        )
        result = run_workflow(
            self.requested_for(TM),
            [owner_scope(TM, broken.ref, broken.evidence())],
        )
        self.assertFalse(result["payload"]["can_complete"], result)
        self.assertEqual(
            unverified_reasons(result),
            {TM: "owner_verification_schema_invalid"},
        )

    def test_a3_changed_or_unknown_source_is_not_current_for_each_f_artifact(
        self,
    ) -> None:
        # 期待結果: RA / TA / TM それぞれで、保存時の source の revision が変わると
        #   source_not_current、current map から source が欠けると source_revision_unknown。
        #   どちらも can_complete=false。
        for skill in (RA, TA, TM):
            art = self.arts[skill]
            changed = art.refs()
            changed[0]["revision"] = "rev-changed"
            changed[0]["content_hash"] = "c" * 64
            missing = art.refs()[1:]
            for label, refs, reason in (
                ("changed", changed, "source_not_current"),
                ("unknown", missing, "source_revision_unknown"),
            ):
                with self.subTest(skill=skill, case=label):
                    evidence = {**art.evidence(), "current_source_refs": refs}
                    result = run_workflow(
                        self.requested_for(skill),
                        [owner_scope(skill, art.ref, evidence)],
                    )
                    self.assertFalse(result["payload"]["can_complete"], result)
                    self.assertEqual(unverified_reasons(result), {skill: reason})

    def test_a4_artifact_of_another_case_is_not_referenced(self) -> None:
        # 期待結果: readback の owner / scope / artifact_ref が保存先の案件と違うと
        #   stored_artifact_readback_not_verified。scope target と成果物の artifact_ref が
        #   違うと artifact_ref_differs_from_scope_target。どちらも完了しない。
        for skill in (RA, TM):
            art = self.arts[skill]
            for claim in (
                {"owner": "another-owner"},
                {"scope": "another-scope"},
                {"artifact_ref": "another-ref"},
            ):
                with self.subTest(skill=skill, claim=claim):
                    evidence = art.evidence()
                    evidence["readback"] = {**evidence["readback"], **claim}
                    result = run_workflow(
                        self.requested_for(skill),
                        [owner_scope(skill, art.ref, evidence)],
                    )
                    self.assertFalse(result["payload"]["can_complete"], result)
                    self.assertEqual(
                        unverified_reasons(result),
                        {skill: "stored_artifact_readback_not_verified"},
                    )
        ra = self.arts[RA]
        result = run_workflow(
            [required(RA, "other-ref")],
            [owner_scope(RA, "other-ref", ra.evidence())],
        )
        self.assertFalse(result["payload"]["can_complete"], result)
        self.assertEqual(
            unverified_reasons(result),
            {RA: "artifact_ref_differs_from_scope_target"},
        )

    def test_a5_approval_required_but_not_confirmed_does_not_complete(self) -> None:
        # 期待結果: (a) RA の承認状態が未承認 → approval_not_satisfied。
        #   (b) TA の approval_evidence が空 → approval_not_satisfied。
        #   (c) TA の承認証拠の1件が未承認 → approval_not_satisfied。
        #   (d) TA の approval_evidence キー自体が無い → owner_verification_schema_invalid。
        #   いずれも完了しない。承認の真正性は確立されない（authenticity は固定値）。
        packet = load_example(RA, "packet-example.json")
        packet["approval"] = {
            "not_required_reason": None,
            "record": None,
            "state": "未承認",
        }
        unapproved_ra = Stored(RA, self.store, packet=packet)
        result = run_workflow(
            self.requested_for(RA),
            [owner_scope(RA, unapproved_ra.ref, unapproved_ra.evidence())],
        )
        self.assertEqual(
            unverified_reasons(result), {RA: "approval_not_satisfied"}, result
        )

        ta = self.arts[TA]
        no_approval = {**ta.evidence(), "approval_evidence": []}
        result = run_workflow(
            self.requested_for(TA), [owner_scope(TA, ta.ref, no_approval)]
        )
        self.assertEqual(unverified_reasons(result), {TA: "approval_not_satisfied"})

        one_pending = ta.approval_rows()
        one_pending[0]["state"] = "未承認"
        partly = {**ta.evidence(), "approval_evidence": one_pending}
        result = run_workflow(self.requested_for(TA), [owner_scope(TA, ta.ref, partly)])
        self.assertEqual(unverified_reasons(result), {TA: "approval_not_satisfied"})

        without_key = ta.evidence()
        del without_key["approval_evidence"]
        result = run_workflow(
            self.requested_for(TA), [owner_scope(TA, ta.ref, without_key)]
        )
        self.assertEqual(
            unverified_reasons(result),
            {TA: "owner_verification_schema_invalid"},
        )

        # 対の正の対照: 承認証拠が揃えば TA は verified（authenticity は固定値）。
        result = run_workflow(self.requested_for(TA), self.scopes_for(TA))
        self.assert_complete(result)
        self.assertEqual(
            result["payload"]["verified_owner_scopes"][0]["verified_artifact"][
                "approval_authenticity"
            ],
            APPROVAL_AUTHENTICITY,
        )

    def test_a6_one_character_change_in_stored_text_is_refused(self) -> None:
        # 期待結果: 保存本文の1文字（承認対象外の値を含む）を変えると、読戻し hash と一致しないため
        #   stored_artifact_readback_not_verified。元の readback を使うため完了しない。
        field_paths = {
            RA: ("requirements", 0, "statement"),
            TA: ("assignments", 0, "measurement"),
            TM: ("plan_items", 0, "effort"),
        }
        for skill, path in field_paths.items():
            with self.subTest(skill=skill):
                art = self.arts[skill]
                changed = copy.deepcopy(art.packet)
                target = changed
                for key in path[:-1]:
                    target = target[key]
                target[path[-1]] = flip_last_char(target[path[-1]])
                evidence = art.evidence()
                evidence["stored_content"] = canonical(changed)
                self.assertNotEqual(evidence["stored_content"], art.text)
                result = run_workflow(
                    self.requested_for(skill),
                    [owner_scope(skill, art.ref, evidence)],
                )
                self.assertFalse(result["payload"]["can_complete"], result)
                self.assertEqual(
                    unverified_reasons(result),
                    {skill: "stored_artifact_readback_not_verified"},
                )

    def test_a7_stale_e2e_selection_is_not_reused(self) -> None:
        # 期待結果: (a) 保存時 current の selection を、現在の SPEC-001 revision が変わった後に
        #   再利用すると source_not_current。保存側の currentness=current は信用しない。
        #   (b) 保存側 currentness=stale（検証前に既に古い）は selection_not_ready。
        #   (c) 現在 revision が保存時と同じなら完了する（対照）。
        selection = SelectionStored(self.store)
        ref = selection.ref
        changed = selection.evidence({"SPEC-001": "s9", "TI-001": "i4"})
        self.assertEqual(
            json.loads(changed["stored_content"])["source_refs"][0]["currentness"],
            "current",
        )
        result = run_workflow([required(E2E, ref)], [owner_scope(E2E, ref, changed)])
        self.assertFalse(result["payload"]["can_complete"], result)
        self.assertEqual(unverified_reasons(result), {E2E: "source_not_current"})

        stale_packet = selection_packet()
        stale_packet["source_refs"][1]["currentness"] = "stale"
        stale = SelectionStored(self.store, packet=stale_packet)
        result = run_workflow(
            [required(E2E, ref)], [owner_scope(E2E, ref, stale.evidence())]
        )
        self.assertEqual(unverified_reasons(result), {E2E: "selection_not_ready"})

        current = selection.evidence()
        result = run_workflow([required(E2E, ref)], [owner_scope(E2E, ref, current)])
        self.assert_complete(result)
        self.assertEqual(verified_skills(result), [E2E])

    def test_a8_readback_failures_are_refused(self) -> None:
        # 期待結果: readback が欠落 → owner_verification_schema_invalid。
        #   readback が null / 文字列 / content_hash 欠落 → stored_artifact_readback_not_verified。
        #   いずれも完了しない。
        for skill in (RA, TM):
            art = self.arts[skill]
            cases = []
            missing = art.evidence()
            del missing["readback"]
            cases.append((missing, "owner_verification_schema_invalid"))
            for value in (None, "ok"):
                evidence = art.evidence()
                evidence["readback"] = value
                cases.append((evidence, "stored_artifact_readback_not_verified"))
            no_hash = art.evidence()
            del no_hash["readback"]["content_hash"]
            cases.append((no_hash, "stored_artifact_readback_not_verified"))
            for evidence, reason in cases:
                with self.subTest(skill=skill, reason=reason):
                    outcome = owner_verifiers.verify(
                        skill, owner_scope(skill, art.ref, evidence)
                    )
                    self.assertEqual(
                        outcome, {"status": "unverified", "reason": reason}
                    )
                    result = run_workflow(
                        self.requested_for(skill),
                        [owner_scope(skill, art.ref, evidence)],
                    )
                    self.assertFalse(result["payload"]["can_complete"], result)

    def test_a9_revision_conflict_in_readback_is_refused(self) -> None:
        # 期待結果: 別writerが revision を進めた（readback は新 revision を返す）後に、
        #   古い expected_revision で検証すると、F 3 Skill は artifact_revision_mismatch で
        #   完了しない。競合を示す readback を verifier が拒否することの確認（CAS 本体は対象外）。
        concurrent = {RA: "2", TA: "ta-r2", TM: "tm-rev-0002"}
        for skill in (RA, TA, TM):
            art = self.arts[skill]
            expected_old = art.revision
            self.store.save(
                art.ref,
                art.text,
                owner=skill,
                scope=art.packet["scope"],
                revision=concurrent[skill],
            )
            evidence = {**art.evidence(), "expected_revision": expected_old}
            with self.subTest(skill=skill):
                outcome = owner_verifiers.verify(
                    skill, owner_scope(skill, art.ref, evidence)
                )
                self.assertEqual(
                    outcome,
                    {"status": "unverified", "reason": "artifact_revision_mismatch"},
                )
                result = run_workflow(
                    self.requested_for(skill),
                    [owner_scope(skill, art.ref, evidence)],
                )
                self.assertFalse(result["payload"]["can_complete"], result)
                self.assertEqual(
                    unverified_reasons(result),
                    {skill: "artifact_revision_mismatch"},
                )

    def test_a10_resumed_session_with_old_expected_revision_is_refused(self) -> None:
        # 期待結果: 中断前の expected_revision（"1"）で再開すると、保存先は revision 2 の本文に
        #   進んでいるため、現在の readback（2）と本文（2）に対して artifact_revision_mismatch。
        #   再開時に現在の revision（"2"）で証拠を組み直した場合だけ verified（対照）。
        newer = load_example(RA, "packet-example.json")
        newer["revision"] = 2
        newer["history"].append(
            {
                "change_reason": "改版（fixture）",
                "impact_scope": ["orders-release-q4"],
                "rechecks": [],
                "replaces_ref": newer["artifact_ref"],
                "replaces_revision": 1,
                "revision": 2,
            }
        )
        current = Stored(RA, self.store, packet=newer)
        resumed_with_old = {**current.evidence(), "expected_revision": "1"}
        outcome = owner_verifiers.verify(
            RA, owner_scope(RA, current.ref, resumed_with_old)
        )
        self.assertEqual(
            outcome, {"status": "unverified", "reason": "artifact_revision_mismatch"}
        )
        result = run_workflow(
            self.requested_for(RA),
            [owner_scope(RA, current.ref, resumed_with_old)],
        )
        self.assertFalse(result["payload"]["can_complete"], result)
        self.assertEqual(unverified_reasons(result), {RA: "artifact_revision_mismatch"})
        result = run_workflow(
            self.requested_for(RA),
            [owner_scope(RA, current.ref, current.evidence())],
        )
        self.assert_complete(result)
        self.assertEqual(verified_skills(result), [RA])

    # --- qa-workflow の入力契約（X） -----------------------------------------------

    def test_x1_undeclared_requested_scopes_never_complete(self) -> None:
        # 期待結果: requested_scopes が無い・空・null のときは、全 scope が verified でも
        #   can_complete=false、scope_set_declared=false、required_scopes_undeclared。
        scopes = self.scopes_for(RA, TA, TM)
        cases = (
            ("absent", None, None),
            ("empty", [], None),
            ("null", None, {"requested_scopes": None}),
        )
        for label, requested, extra in cases:
            with self.subTest(case=label):
                result = run_workflow(requested, scopes, input_extra=extra)
                self.assertFalse(result["payload"]["can_complete"], result)
                self.assertFalse(result["payload"]["scope_set_declared"], result)
                self.assertIn("required_scopes_undeclared", issue_types(result))
                self.assertEqual(sorted(verified_skills(result)), sorted([RA, TA, TM]))

    def test_x2_approved_exclusion_requires_a_reference(self) -> None:
        # 期待結果: excluded_by_approval に approval_ref が無い（欠落・空白）と、
        #   approval_ref_missing で完了しない。approval_ref があれば、その scope は除外されて
        #   完了する（対照）。
        scopes = self.scopes_for(RA, TA)
        base = [required(RA, self.arts[RA].ref), required(TA, self.arts[TA].ref)]
        for approval in (None, "   "):
            with self.subTest(approval=approval):
                result = run_workflow(base + [excluded(TM, approval)], scopes)
                self.assertFalse(result["payload"]["can_complete"], result)
                self.assertIn("approval_ref_missing", issue_types(result))
        result = run_workflow(base + [excluded(TM, "APPROVAL-001")], scopes)
        self.assert_complete(result)
        self.assertEqual(
            [row["skill"] for row in result["payload"]["excluded_scopes"]], [TM]
        )

    def test_x3_self_declared_or_unknown_keys_are_rejected(self) -> None:
        # 期待結果: 入力に未知のキー（「全工程確認済み」等の自己申告）を入れると、
        #   入力全体が invalid_input で拒否され、can_complete=true にならない。
        #   要求行・scope 行の未知キーも同様。
        scopes = self.scopes_for(RA, TA, TM)
        requested = self.requested_for(RA, TA, TM)
        result = run_workflow(
            requested, scopes, input_extra={"all_steps_confirmed": True}
        )
        self.assertEqual(result["runtime_status"], "invalid_input", result)
        self.assertTrue(blocked(result))

        bad_requested = copy.deepcopy(requested)
        bad_requested[0]["self_declared"] = "complete"
        result = run_workflow(bad_requested, scopes)
        self.assertEqual(result["runtime_status"], "invalid_input", result)
        self.assertTrue(blocked(result))

        bad_scopes = copy.deepcopy(scopes)
        bad_scopes[0]["verified"] = True
        result = run_workflow(requested, bad_scopes)
        self.assertEqual(result["runtime_status"], "invalid_input", result)
        self.assertTrue(blocked(result))

    def test_x4_unregistered_skill_stays_fail_closed(self) -> None:
        # 期待結果: F 3 Skill 以外の未登録 Skill（defect-management / test-evaluation）を
        #   required で宣言すると、登録が無いため unverified（owner_verifier_not_registered）。
        #   その他の scope が verified でも完了しない。承認済み除外（approval_ref あり）なら、
        #   その scope は完了判定から外れる（対照）。
        for skill in (UNREGISTERED, "test-evaluation"):
            with self.subTest(skill=skill):
                dm_scope = {
                    "skill": skill,
                    "target": "unregistered-target",
                    "execution_range": "plan",
                    "input_mode": "artifact",
                    "normalized_input": {},
                    "current_structure_state": None,
                }
                requested = self.requested_for(RA, TA, TM) + [
                    required(skill, "unregistered-target")
                ]
                result = run_workflow(
                    requested, self.scopes_for(RA, TA, TM) + [dm_scope]
                )
                self.assertFalse(result["payload"]["can_complete"], result)
                self.assertEqual(
                    unverified_reasons(result),
                    {skill: "owner_verifier_not_registered"},
                )
                self.assertIn("unsupported_skill_verifier", issue_types(result))
        excluded_result = run_workflow(
            self.requested_for(RA, TA, TM) + [excluded(UNREGISTERED)],
            self.scopes_for(RA, TA, TM),
        )
        self.assert_complete(excluded_result)


if __name__ == "__main__":
    unittest.main()
