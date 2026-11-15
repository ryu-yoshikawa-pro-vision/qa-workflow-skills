"""owner verifier 完了 scope を含む v2 workflow の再開（downstream_state）の独立負例検証。

既存の owner_scope_resume テストの helper は import しない。保存済み履歴は
workflow_runtime.py（CLI）の実出力から組み、再開は downstream_state.py（CLI と evaluate）で行う。
- owner 側の証拠は skills/<owner>/assets の example 成果物から自前で組む（保存・読戻しは fixture）。
- runtime-v2 root（test-condition-design）の完了 state だけ既存 test_workflow_runtime の
  _request() から取る（fixture 源として使うのみ）。
- 改ざん後の保存済み結果は、構造検査まで到達させるため fingerprint を runtime_contract の
  関数で再計算する（fingerprint 検査で偶然拒否されることを避ける）。
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
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "skills" / "qa-workflow" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import downstream_state as ds  # noqa: E402
import runtime_contract as rc  # noqa: E402

import tests.skills.runtime.test_workflow_runtime as W  # noqa: E402  (fixture 源のみ)

WF_SCRIPT = SCRIPTS / "workflow_runtime.py"
DS_SCRIPT = SCRIPTS / "downstream_state.py"
REF = "00000000-0000-4000-8000-0000000000c2"
OTHER_REF = "00000000-0000-4000-8000-0000000000c3"
ROOT_ID = "qa-workflow::artifact:workflow_runtime:all"
SKILL = "qa-workflow"
RA = "test-requirements-analysis"
TA = "test-architecture-design"
TM = "test-management"
TCD = "test-condition-design"
UNREG = "defect-management"
CHILD_ENV = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
META = {
    "envelope_version": "1",
    "skill": SKILL,
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


# ---------------------------------------------------------------- 共通 helper
def canon(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def cli(script: Path, payload: dict) -> dict:
    proc = subprocess.run(
        [sys.executable, "-B", str(script)],
        input=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=ROOT,
        env=CHILD_ENV,
        check=False,
    )
    if proc.stderr:
        raise AssertionError(proc.stderr.decode("utf-8"))
    return json.loads(proc.stdout)


def wf(scopes: list, requested: list | None, **extra: Any) -> tuple[dict, dict]:
    """workflow_runtime CLI を呼ぶ。(入力, 結果) を返す。"""
    value: dict[str, Any] = {
        "workflow_ref": REF,
        "workflow_scopes": scopes,
        "runtime_units": [],
        "current_runtime_units": [],
        "current_entities": [],
        "unsupported_item_closures": [],
    }
    if requested is not None:
        value["requested_scopes"] = requested
    value.update(extra)
    result = cli(WF_SCRIPT, {"metadata": copy.deepcopy(META), "input": value})
    return value, result


def markdown(metadata: dict, value: dict, result: dict) -> str:
    source = {"metadata": metadata, "input": value}
    return (
        f"### Machine Runtime Input: {ROOT_ID}\n\n```json\n"
        f"{json.dumps(source, ensure_ascii=False)}\n```\n\n"
        f"### Machine Runtime Result: {ROOT_ID}\n\n```json\n"
        f"{json.dumps(result, ensure_ascii=False)}\n```\n"
    )


def resign(metadata: dict, value: dict, result: dict) -> None:
    """改ざん後の入力に合わせて fingerprint を再計算する（構造検査まで到達させるため）。"""
    exp_input = rc.input_fingerprint(
        SKILL,
        metadata["runtime_unit_key"],
        metadata["input_mode"],
        value,
        metadata["authority_refs"],
        metadata["reference_refs"],
        metadata["selection_source"],
    )
    model = rc.model_fingerprint(metadata, exp_input)
    upstream = rc.upstream_entity_fingerprints(rc.validate_upstream_entities(metadata))
    gen = rc.generation_fingerprint(
        generator="workflow_runtime",
        input_fp=exp_input,
        model_fp=model,
        runtime_contract_version="runtime-v2",
        generator_contract_version=result["generator_contract_version"],
        runtime_impl_fp=result["runtime_implementation_fingerprint"],
        generator_impl_fp=result["generator_implementation_fingerprint"],
        upstream=upstream,
        static_data_versions=result.get("static_data_versions", {}),
    )
    result.update(
        input_fingerprint=exp_input,
        model_fingerprint=model,
        generation_fingerprint=gen,
        upstream_entity_fingerprints=upstream,
        upstream_runtime_units=rc.canonicalize(
            metadata["upstream_runtime_units"], parent_key="upstream_runtime_units"
        ),
    )


def resume(
    markdown_text: str, *, current=(), blocked=(), ref=REF, **extra: Any
) -> dict:
    """downstream_state CLI で再開する。binding は保存本文の sha256 と一致させる。"""
    request = {
        "workflow_ref": ref,
        "workflow_state_record": {
            "workflow_ref": ref,
            "schema_version": "1",
            "state": {
                "last_completed_qa_workflow_artifact": {
                    "artifact_ref": f"qa-workflow:{REF}",
                    "artifact_revision": "r1",
                    "artifact_sha256": sha(markdown_text),
                }
            },
        },
        "current_scope_ids": list(current),
        "blocked_scope_ids": list(blocked),
        "previous_qa_workflow_artifact_markdown": markdown_text,
        "scope_removal_resolutions": [],
        "scope_removal_applied_states": [],
    }
    request.update(extra)
    return cli(DS_SCRIPT, request)


def rejected_with(response: dict, fragment: str) -> None:
    """再開が拒否され、理由に fragment を含むことを確認する。"""
    assert response["valid"] is False, response
    messages = " ".join(issue["message"] for issue in response["issues"])
    assert fragment in messages, (fragment, messages)


# ---------------------------------------------------------------- owner 証拠（自前）
def load_example(skill: str, name: str) -> dict:
    return json.loads((ROOT / "skills" / skill / "assets" / name).read_text("utf-8"))


OWNER_EXAMPLES = {
    RA: ("packet-example.json", "sources"),
    TA: ("packet-example.json", "sources"),
    TM: ("plan-packet.example.json", "planned_sources"),
}
REF_KEYS = ("owner", "scope", "artifact_ref", "revision", "content_hash")


class Owner:
    """保存済み owner 成果物と、その読戻し・承認の証拠（fixture。実 provider ではない）。"""

    def __init__(self, skill: str) -> None:
        name, sources_key = OWNER_EXAMPLES[skill]
        self.skill = skill
        self.packet = load_example(skill, name)
        self.ref = self.packet["artifact_ref"]
        self.text = canon(self.packet)
        self.revision = "ta-r1" if skill == TA else str(self.packet["revision"])
        self.sources_key = sources_key
        self.readback_revision = self.revision

    def evidence(self, *, expected_revision: str | None = None) -> dict:
        value: dict[str, Any] = {
            "stored_content": self.text,
            "readback": {
                "owner": self.skill,
                "scope": self.packet["scope"],
                "artifact_ref": self.ref,
                "revision": self.readback_revision,
                "content_hash": sha(self.text),
            },
            "expected_revision": expected_revision or self.revision,
            "current_source_refs": [
                {key: row[key] for key in REF_KEYS}
                for row in self.packet[self.sources_key]
            ],
        }
        if self.skill == TA:
            value["approval_evidence"] = [
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
        return value

    def scope(self, **override: Any) -> dict:
        return {
            "skill": self.skill,
            "target": self.ref,
            "execution_range": "plan",
            "input_mode": "artifact",
            "normalized_input": {"owner_verification": self.evidence(**override)},
            "current_structure_state": None,
        }

    def requested(self) -> dict:
        return {
            "skill": self.skill,
            "target": self.ref,
            "execution_range": "plan",
            "requirement": "required",
        }


def owners_triple() -> tuple[list[Owner], list[dict], list[dict]]:
    owners = [Owner(RA), Owner(TA), Owner(TM)]
    return owners, [o.scope() for o in owners], [o.requested() for o in owners]


def tcd_root() -> dict:
    """既存 test_workflow_runtime の完了済み runtime-v2 root（TCD）を fixture 源として使う。

    W の fixture は nested runtime result の generation_fingerprint が再開検査と一致しないため、
    nested result の fingerprint と runtime unit 行だけを runtime_contract の式で再計算する
    （fixture の作り方であり、実 condition runtime の検証経路ではない）。
    """
    base = W.WorkflowRuntimeTests()._request()
    base["input"]["workflow_ref"] = REF
    scope = base["input"]["workflow_scopes"][0]
    unit_lists = [
        base["input"]["runtime_units"],
        base["input"]["current_runtime_units"],
    ]
    for row in scope["current_structure_state"]["runtime_results"]:
        result = row["result"]
        result["generation_fingerprint"] = rc.generation_fingerprint(
            generator=result["generator"],
            input_fp=result["input_fingerprint"],
            model_fp=result["model_fingerprint"],
            runtime_contract_version=result["runtime_contract_version"],
            generator_contract_version=result["generator_contract_version"],
            runtime_impl_fp=result["runtime_implementation_fingerprint"],
            generator_impl_fp=result["generator_implementation_fingerprint"],
            upstream=result["upstream_entity_fingerprints"],
            static_data_versions=result["static_data_versions"],
        )
        fresh = rc.runtime_unit_row(result)
        for units in unit_lists:
            for index, unit in enumerate(units):
                if (
                    unit.get("skill") == fresh["skill"]
                    and unit.get("runtime_unit_key") == fresh["runtime_unit_key"]
                ):
                    units[index] = fresh
    return base


def owner_only_saved() -> tuple[dict, dict, str]:
    """RA+TA+TM を完了させ、保存本文を作る（期待: can_complete=true）。"""
    _, scopes, requested = owners_triple()
    value, result = wf(scopes, requested)
    assert result["payload"]["can_complete"] is True, result["issues"]
    return value, result, markdown(copy.deepcopy(META), value, result)


# ---------------------------------------------------------------- テスト
class IndependentResumeNegatives(unittest.TestCase):
    # --- 正常系（11）-----------------------------------------------------------

    def test_p1_owner_only_three_scopes_complete_then_resume(self) -> None:
        # 期待: RA/TA/TM の3件だけで can_complete=true、verified_owner_scopes は3件、
        #   unverified_scopes と issues は空。保存本文を current=[] で再開すると valid=true、
        #   payload の履歴・removed は空。
        value, result, md = owner_only_saved()
        self.assertEqual(
            sorted(r["skill"] for r in result["payload"]["verified_owner_scopes"]),
            sorted([RA, TA, TM]),
        )
        self.assertEqual(result["payload"]["unverified_scopes"], [])
        self.assertEqual(result["issues"], [])
        resumed = resume(md)
        self.assertTrue(resumed["valid"], resumed)
        self.assertEqual(resumed["payload"]["removed_scope_ids"], [])
        self.assertEqual(resumed["payload"]["inactive_tc_ids"], [])

    def test_p2_same_inputs_give_same_records_and_result(self) -> None:
        # 期待: 同じ保存済み証拠で2回実行すると verified_owner_scopes と payload が同一。
        _, r1 = wf(owners_triple()[1], owners_triple()[2])
        _, r2 = wf(owners_triple()[1], owners_triple()[2])
        self.assertEqual(r1["payload"], r2["payload"])

    def test_p3_changed_owner_revision_affects_only_that_owner(self) -> None:
        # 期待: TM の expected_revision だけを変えると TM は artifact_revision_mismatch で
        #   unverified（can_complete=false）。RA・TA は verified のまま、記録の内容は変わらない。
        owners, scopes, requested = owners_triple()
        base_value, base = wf(scopes, requested)
        changed = [o.scope() for o in owners[:2]]
        changed.append(owners[2].scope(expected_revision="tm-rev-stale"))
        _, result = wf(changed, requested)
        self.assertFalse(result["payload"]["can_complete"])
        reasons = {
            r["skill"]: r["reason"] for r in result["payload"]["unverified_scopes"]
        }
        self.assertEqual(reasons, {TM: "artifact_revision_mismatch"})
        kept = {r["skill"]: r for r in result["payload"]["verified_owner_scopes"]}
        base_kept = {r["skill"]: r for r in base["payload"]["verified_owner_scopes"]}
        self.assertEqual(kept[RA], base_kept[RA])
        self.assertEqual(kept[TA], base_kept[TA])

    def test_p4_mixed_root_and_owner_completes_and_resume_matches_root_only(
        self,
    ) -> None:
        # 期待: TCD root（完了 state）＋RA/TA/TM の混在が can_complete=true。
        #   同じ root だけの再開と、混在の再開の payload が同一（owner scope は履歴に影響しない）。
        base = tcd_root()
        owners, owner_scopes, owner_requested = owners_triple()
        kw = dict(
            runtime_units=base["input"]["runtime_units"],
            current_runtime_units=base["input"]["current_runtime_units"],
            current_entities=base["input"]["current_entities"],
            unsupported_item_closures=[],
        )
        root_scope = base["input"]["workflow_scopes"][0]
        root_req = base["input"]["requested_scopes"][0]
        root_value, root_result = wf([root_scope], [root_req], **kw)
        self.assertTrue(root_result["payload"]["can_complete"], root_result["issues"])
        mixed_value, mixed_result = wf(
            [root_scope, *owner_scopes], [root_req, *owner_requested], **kw
        )
        self.assertTrue(mixed_result["payload"]["can_complete"], mixed_result["issues"])
        root_md = markdown(copy.deepcopy(META), root_value, root_result)
        mixed_md = markdown(copy.deepcopy(META), mixed_value, mixed_result)
        r_root = resume(root_md, current=[])
        r_mixed = resume(mixed_md, current=[])
        self.assertTrue(r_root["valid"], r_root)
        self.assertTrue(r_mixed["valid"], r_mixed)
        self.assertEqual(r_root, r_mixed)

    def test_p5_stored_v2_root_only_resumes_as_before(self) -> None:
        # 期待: v2 の root だけの保存本文の再開は valid=true（owner 検査を通らない回帰）。
        base = tcd_root()
        kw = dict(
            runtime_units=base["input"]["runtime_units"],
            current_runtime_units=base["input"]["current_runtime_units"],
            current_entities=base["input"]["current_entities"],
            unsupported_item_closures=[],
        )
        value, result = wf(
            base["input"]["workflow_scopes"], base["input"]["requested_scopes"], **kw
        )
        self.assertTrue(result["payload"]["can_complete"], result["issues"])
        response = resume(markdown(copy.deepcopy(META), value, result), current=[])
        self.assertTrue(response["valid"], response)

    # --- 負例（重点 a-c, 1-9）-----------------------------------------------------

    def _mixed_saved(self) -> tuple[dict, dict, dict]:
        _, scopes, requested = owners_triple()
        value, result = wf(scopes, requested)
        self.assertTrue(result["payload"]["can_complete"], result["issues"])
        return copy.deepcopy(META), value, result

    def test_n1_root_scope_null_with_forged_record_is_rejected(self) -> None:
        # 期待: root（TCD）を current_structure_state=null にし、verified_owner_scopes に
        #   TCD の偽記録を付けても、root の null は構造検査で拒否（current_structure_state schema）。
        meta, value, result = self._mixed_saved()
        tcd = copy.deepcopy(tcd_root()["input"]["workflow_scopes"][0])
        tcd["current_structure_state"] = None
        value["workflow_scopes"].append(tcd)
        value["requested_scopes"].append(
            {
                "skill": TCD,
                "target": None,
                "execution_range": None,
                "requirement": "required",
            }
        )
        result["payload"]["verified_owner_scopes"].append(
            {
                "skill": TCD,
                "target": None,
                "execution_range": None,
                "verified_artifact": {},
            }
        )
        sync_requested(value, result)
        resign(meta, value, result)
        md = markdown(meta, value, result)
        rejected_with(
            resume(md, current=[]), "current_structure_state schema is invalid"
        )

    def test_n1b_root_scope_with_state_and_forged_record_is_rejected(self) -> None:
        # 期待: root（TCD）が正当な state を持つのに、owner 記録だけを偽造しても拒否
        #   （記録は非root の identity にだけ対応する。no matching verification record）。
        meta, value, result = self._mixed_saved()
        tcd = copy.deepcopy(tcd_root()["input"]["workflow_scopes"][0])
        value["workflow_scopes"].append(tcd)
        value["requested_scopes"].append(
            {
                "skill": TCD,
                "target": None,
                "execution_range": None,
                "requirement": "required",
            }
        )
        result["payload"]["verified_owner_scopes"].append(
            {
                "skill": TCD,
                "target": None,
                "execution_range": None,
                "verified_artifact": {},
            }
        )
        sync_requested(value, result)
        resign(meta, value, result)
        rejected_with(
            resume(markdown(meta, value, result), current=[]),
            "no matching verification record",
        )

    def test_n2a_owner_scope_with_empty_dict_is_rejected(self) -> None:
        # 期待: owner scope の current_structure_state={}（非null）は拒否（must be null）。
        meta, value, result = self._mixed_saved()
        value["workflow_scopes"][0]["current_structure_state"] = {}
        sync_requested(value, result)
        resign(meta, value, result)
        rejected_with(
            resume(markdown(meta, value, result), current=[]),
            "current_structure_state must be null",
        )

    def test_n2b_owner_scope_with_structured_state_is_rejected(self) -> None:
        # 期待: owner scope に TCD 由来の構造のある state を入れると拒否（must be null）。
        meta, value, result = self._mixed_saved()
        value["workflow_scopes"][0]["current_structure_state"] = copy.deepcopy(
            tcd_root()["input"]["workflow_scopes"][0]["current_structure_state"]
        )
        sync_requested(value, result)
        resign(meta, value, result)
        rejected_with(
            resume(markdown(meta, value, result), current=[]),
            "current_structure_state must be null",
        )

    def test_n3_removed_verification_record_is_rejected(self) -> None:
        # 期待: 保存 result の verified_owner_scopes から1件削除すると、対応の無い null scope として拒否。
        meta, value, result = self._mixed_saved()
        result["payload"]["verified_owner_scopes"].pop()
        md = markdown(meta, value, result)
        rejected_with(resume(md, current=[]), "no matching verification record")

    def test_n4a_duplicated_verification_record_is_rejected(self) -> None:
        # 期待: 同一 identity の記録の重複は拒否（duplicated）。
        meta, value, result = self._mixed_saved()
        result["payload"]["verified_owner_scopes"].append(
            copy.deepcopy(result["payload"]["verified_owner_scopes"][0])
        )
        rejected_with(resume(markdown(meta, value, result), current=[]), "duplicated")

    def test_n4b_extra_record_without_scope_is_rejected(self) -> None:
        # 期待: 対応する scope の無い余分な記録は拒否（no matching verification record）。
        meta, value, result = self._mixed_saved()
        result["payload"]["verified_owner_scopes"].append(
            {
                "skill": UNREG,
                "target": "X-1",
                "execution_range": "plan",
                "verified_artifact": {},
            }
        )
        rejected_with(
            resume(markdown(meta, value, result), current=[]),
            "no matching verification record",
        )

    def test_n5_same_skill_record_with_other_target_is_rejected(self) -> None:
        # 期待: 同じ skill（TM）でも target が異なる記録は identity が一致せず拒否する。
        meta, value, result = self._mixed_saved()
        for record in result["payload"]["verified_owner_scopes"]:
            if record["skill"] == TM:
                record["target"] = "tm-plan:other-target"
        rejected_with(
            resume(markdown(meta, value, result), current=[]),
            "no matching verification record",
        )

    def test_n6_other_workflow_state_is_rejected(self) -> None:
        # 期待: 別 workflow_ref の状態に対して再開すると拒否（workflow_ref mismatch）。
        meta, value, result = self._mixed_saved()
        md = markdown(meta, value, result)
        response = resume(md, current=[], ref=OTHER_REF)
        self.assertFalse(response["valid"], response)
        self.assertEqual(response["issues"][0]["issue_type"], "workflow_ref_mismatch")

    def test_n6b_saved_input_with_other_workflow_ref_is_rejected(self) -> None:
        # 期待: 保存本文の input.workflow_ref が別 workflow のとき拒否（workflow_ref mismatch）。
        meta, value, result = self._mixed_saved()
        value["workflow_ref"] = OTHER_REF
        rejected_with(
            resume(markdown(meta, value, result), current=[]),
            "historical workflow_ref mismatch",
        )

    def test_n7a_tampered_result_fingerprint_is_rejected(self) -> None:
        # 期待: 保存 result の input_fingerprint の改ざんは拒否（fingerprints mismatch）。
        meta, value, result = self._mixed_saved()
        result["input_fingerprint"] = "sha256:" + "0" * 64
        rejected_with(
            resume(markdown(meta, value, result), current=[]),
            "historical runtime fingerprints or dependency projection mismatch",
        )

    def test_n7b_binding_sha_mismatch_is_rejected(self) -> None:
        # 期待: 保存本文（binding の sha256 の元）と提示本文が1文字違うと拒否（SHA does not match）。
        meta, value, result = self._mixed_saved()
        saved = markdown(meta, value, result)
        response = resume_with_binding(saved, saved + " ")
        self.assertFalse(response["valid"], response)
        self.assertEqual(
            response["issues"][0]["issue_type"], "historical_artifact_hash_mismatch"
        )

    def test_n8a_omitted_required_owner_scope_cannot_complete(self) -> None:
        # 期待: 要求集合の TA を workflow_scopes から欠くと can_complete=false、required_scope_missing。
        _, scopes, requested = owners_triple()
        _, result = wf([scopes[0], scopes[2]], requested)
        self.assertFalse(result["payload"]["can_complete"])
        self.assertIn(
            "required_scope_missing",
            {issue["issue_type"] for issue in result["issues"]},
        )

    def test_n8b_forged_complete_with_missing_requested_is_rejected(self) -> None:
        # 期待: 欠落を含む結果の can_complete を true に偽造しても、宣言検査で拒否。
        meta, value, result = self._mixed_saved()
        value["workflow_scopes"] = value["workflow_scopes"][:2]
        result["payload"]["missing_requested_scopes"] = [
            {"skill": TM, "target": None, "execution_range": None}
        ]
        sync_requested(value, result)
        resign(meta, value, result)
        rejected_with(
            resume(markdown(meta, value, result), current=[]),
            "workflow scope declaration is invalid",
        )

    def test_n9_excluded_by_approval_claim_is_rejected(self) -> None:
        # 期待: CLI では承認の照合手段が無いため対象外は確定しない（can_complete=false）。
        # 保存本文に excluded_by_approval を入れて完了扱いにしても拒否（not confirmable）。
        _, scopes, requested = owners_triple()
        requested.append(
            {
                "skill": UNREG,
                "target": None,
                "execution_range": "plan",
                "requirement": "excluded_by_approval",
                "approval_ref": "APR-777",
            }
        )
        _, cli_result = wf(scopes, requested)
        self.assertFalse(cli_result["payload"]["can_complete"])
        meta, value, result = self._mixed_saved()
        value["requested_scopes"].append(
            {
                "skill": UNREG,
                "target": None,
                "execution_range": "plan",
                "requirement": "excluded_by_approval",
                "approval_ref": "APR-777",
            }
        )
        sync_requested(value, result)
        resign(meta, value, result)
        rejected_with(
            resume(markdown(meta, value, result), current=[]),
            "historical excluded scope claim is not confirmable",
        )

    def test_n10_unregistered_skill_null_record_is_rejected(self) -> None:
        # 期待: 未登録 Skill（defect-management）は CLI で完了不可（unverified）。
        # 保存本文に同 identity の偽記録と null scope を入れた再開は拒否されるべき
        #   （未登録の Skill は owner 検証の対象外なので記録を受理しない）。
        meta, value, result = self._mixed_saved()
        value["workflow_scopes"].append(
            {
                "skill": UNREG,
                "target": "DM-1",
                "execution_range": "plan",
                "input_mode": "artifact",
                "normalized_input": {},
                "current_structure_state": None,
            }
        )
        value["requested_scopes"].append(
            {
                "skill": UNREG,
                "target": "DM-1",
                "execution_range": "plan",
                "requirement": "required",
            }
        )
        result["payload"]["verified_owner_scopes"].append(
            {
                "skill": UNREG,
                "target": "DM-1",
                "execution_range": "plan",
                "verified_artifact": {},
            }
        )
        sync_requested(value, result)
        resign(meta, value, result)
        response = resume(markdown(meta, value, result), current=[])
        self.assertFalse(response["valid"], response)

    def test_n10b_unregistered_skill_cli_cannot_complete(self) -> None:
        # 期待: 未登録 Skill を含む入力は CLI で完了不可（unsupported_skill_verifier）。
        _, scopes, requested = owners_triple()
        scopes.append(
            {
                "skill": UNREG,
                "target": "DM-1",
                "execution_range": "plan",
                "input_mode": "artifact",
                "normalized_input": {"owner_verification": {}},
                "current_structure_state": None,
            }
        )
        _, result = wf(scopes, requested)
        self.assertFalse(result["payload"]["can_complete"])
        self.assertIn(
            "unsupported_skill_verifier",
            {issue["issue_type"] for issue in result["issues"]},
        )

    def test_n11_missing_verified_list_is_rejected(self) -> None:
        # 期待: owner scope があるのに verified_owner_scopes が無い保存 result は拒否。
        meta, value, result = self._mixed_saved()
        del result["payload"]["verified_owner_scopes"]
        rejected_with(
            resume(markdown(meta, value, result), current=[]),
            "verified owner scopes are invalid",
        )

    def test_n12_v1_owner_null_scope_is_rejected(self) -> None:
        # 期待: v1 の owner null は従来どおり拒否（v1 は owner 検証の完了 baseline にしない）。
        meta, value, result = self._mixed_saved()
        value["workflow_scopes"][0]["current_structure_state"] = None
        meta = copy.deepcopy(meta)
        meta["generator_contract_version"] = "workflow-runtime-v1"
        value.pop("requested_scopes")
        result["generator_contract_version"] = "workflow-runtime-v1"
        for key in (
            "scope_set_declared",
            "requested_scopes",
            "missing_requested_scopes",
            "excluded_scopes",
            "unrequested_scopes",
            "verified_owner_scopes",
        ):
            result["payload"].pop(key, None)
        sync_requested(value, result)
        resign(meta, value, result)
        rejected_with(
            resume(markdown(meta, value, result), current=[]),
            "current_structure_state schema is invalid",
        )

    # --- 混線・読取専用・失敗時（重点 e-h）----------------------------------------

    def test_h1_evaluate_does_not_mutate_input(self) -> None:
        # 期待: evaluate は入力を変更しない（前後で canonical 形が同一）。
        meta, value, result = self._mixed_saved()
        md = markdown(meta, value, result)
        request = {
            "workflow_ref": REF,
            "workflow_state_record": {
                "workflow_ref": REF,
                "schema_version": "1",
                "state": {
                    "last_completed_qa_workflow_artifact": {
                        "artifact_ref": f"qa-workflow:{REF}",
                        "artifact_revision": "r1",
                        "artifact_sha256": sha(md),
                    }
                },
            },
            "current_scope_ids": [],
            "blocked_scope_ids": [],
            "previous_qa_workflow_artifact_markdown": md,
            "scope_removal_resolutions": [],
            "scope_removal_applied_states": [],
        }
        before = canon(request)
        ds.evaluate(copy.deepcopy(request))
        self.assertEqual(canon(request), before)

    def test_h2_failed_resume_does_not_break_later_valid_resume(self) -> None:
        # 期待: 拒否された再開の後、同じ正常な保存本文の再開結果は変わらない（baseline を壊さない）。
        meta, value, result = self._mixed_saved()
        good = markdown(meta, value, result)
        first = resume(good, current=[])
        bad = copy.deepcopy(result)
        bad["payload"]["verified_owner_scopes"].pop()
        resume(markdown(meta, value, bad), current=[])
        second = resume(good, current=[])
        self.assertEqual(first, second)


# ---------------------------------------------------------------- M1 修正の再レビュー
def seven_owner_cases() -> list[tuple[str, str, dict]]:
    """登録済み7 owner の保存証拠（owner_verifiers の evidence 契約どおり）を組む。

    candidate・selection・report の証拠は既存 owner registry テストの fixture 生成関数を
    fixture 源として呼ぶ（テストケースの判定には使わない）。RA/TA/TM は本ファイルの Owner を使う。
    """
    import tests.skills.runtime.test_owner_verifier_registry as R  # noqa: PLC0415

    reg = R.OwnerVerifierRegistryTests(
        "test_registered_owners_have_an_entry_point_and_others_stay_blocked"
    )
    cases: list[tuple[str, str, dict]] = []
    for kind in ("item", "condition"):
        evidence, owner, ref = reg.candidate_evidence(kind)
        cases.append((owner, ref, evidence))
    evidence, ref = reg.selection_evidence()
    cases.append(("e2e-test-selection", ref, evidence))
    evidence, ref = reg.report_evidence()
    cases.append(("test-reporting", ref, evidence))
    for skill in (RA, TA, TM):
        owner = Owner(skill)
        cases.append((skill, owner.ref, owner.evidence()))
    return cases


TEXT_KEY = {"test-reporting": "stored_snapshot_content"}


def seven_scopes(cases: list[tuple[str, str, dict]]) -> tuple[list[dict], list[dict]]:
    scopes = [
        {
            "skill": skill,
            "target": ref,
            "execution_range": "plan",
            "input_mode": "artifact",
            "normalized_input": {"owner_verification": evidence},
            "current_structure_state": None,
        }
        for skill, ref, evidence in cases
    ]
    requested = [
        {
            "skill": skill,
            "target": ref,
            "execution_range": "plan",
            "requirement": "required",
        }
        for skill, ref, _ in cases
    ]
    return scopes, requested


class SevenOwnerResume(unittest.TestCase):
    """全7 owner（RA・TA・TM・item・condition・e2e・report）を workflow_runtime の実出力から保存・再開する。"""

    def saved_single(
        self, skill: str, ref: str, evidence: dict
    ) -> tuple[dict, dict, str]:
        scopes, requested = seven_scopes([(skill, ref, evidence)])
        value, result = wf(scopes, requested)
        self.assertTrue(result["payload"]["can_complete"], (skill, result["issues"]))
        return copy.deepcopy(META), value, result

    def test_each_owner_completes_saves_and_resumes(self) -> None:
        # 期待: 7 owner それぞれ単独で can_complete=true、verified_owner_scopes に1件、
        #   保存本文の再開は valid=true。記録の identity は scope と一致する。
        for skill, ref, evidence in seven_owner_cases():
            with self.subTest(skill=skill):
                meta, value, result = self.saved_single(skill, ref, evidence)
                [record] = result["payload"]["verified_owner_scopes"]
                self.assertEqual((record["skill"], record["target"]), (skill, ref))
                resumed = resume(markdown(meta, value, result), current=[])
                self.assertTrue(resumed["valid"], (skill, resumed))

    def test_all_seven_together_complete_and_resume(self) -> None:
        # 期待: 7 owner を同時に要求した workflow が完了し、保存・再開が valid=true。
        scopes, requested = seven_scopes(seven_owner_cases())
        value, result = wf(scopes, requested)
        self.assertTrue(result["payload"]["can_complete"], result["issues"])
        self.assertEqual(len(result["payload"]["verified_owner_scopes"]), 7)
        resumed = resume(markdown(copy.deepcopy(META), value, result), current=[])
        self.assertTrue(resumed["valid"], resumed)

    def test_stored_text_altered_after_save_is_rejected_for_each_owner(self) -> None:
        # 期待: 保存本文（証拠）を変えると、記録の content_hash と一致せず拒否（altered）。
        for skill, ref, evidence in seven_owner_cases():
            with self.subTest(skill=skill):
                meta, value, result = self.saved_single(skill, ref, evidence)
                key = TEXT_KEY.get(skill, "stored_content")
                owner_ev = value["workflow_scopes"][0]["normalized_input"][
                    "owner_verification"
                ]
                owner_ev[key] = owner_ev[key] + " "
                sync_requested(value, result)
                resign(meta, value, result)
                rejected_with(
                    resume(markdown(meta, value, result), current=[]),
                    "stored text is altered",
                )

    def test_record_hash_changed_is_rejected_for_each_owner(self) -> None:
        # 期待: 証拠は元のまま、記録の content_hash だけ変えても拒否（altered）。
        for skill, ref, evidence in seven_owner_cases():
            with self.subTest(skill=skill):
                meta, value, result = self.saved_single(skill, ref, evidence)
                result["payload"]["verified_owner_scopes"][0]["verified_artifact"][
                    "content_hash"
                ] = "0" * 64
                rejected_with(
                    resume(markdown(meta, value, result), current=[]),
                    "stored text is altered",
                )

    def test_record_target_mismatch_is_rejected(self) -> None:
        # 期待: 記録の artifact_ref が scope の target と違えば拒否（target mismatch）。
        skill, ref, evidence = seven_owner_cases()[-1]
        meta, value, result = self.saved_single(skill, ref, evidence)
        result["payload"]["verified_owner_scopes"][0]["verified_artifact"][
            "artifact_ref"
        ] = "someone-else"
        rejected_with(
            resume(markdown(meta, value, result), current=[]),
            "verification target mismatch",
        )

    def test_evidence_text_removed_is_rejected(self) -> None:
        # 期待: 保存された証拠の本文が無い null owner は拒否（stored text is missing）。
        skill, ref, evidence = seven_owner_cases()[0]
        meta, value, result = self.saved_single(skill, ref, evidence)
        owner_ev = value["workflow_scopes"][0]["normalized_input"]["owner_verification"]
        del owner_ev["stored_content"]
        sync_requested(value, result)
        resign(meta, value, result)
        rejected_with(
            resume(markdown(meta, value, result), current=[]),
            "stored text is missing",
        )

    def test_residual_full_forgery_is_accepted_documented(self) -> None:
        # 残存リスク（仕様として明示）: 証拠の本文・content_hash・記録を一式で偽造すると、
        #   再開は完了を再計算しないため受理する。完了の再計算は workflow_runtime の新規入力側で行う。
        #   本テストはこの境界を固定して記録する（修正で変わったら本テストを更新する）。
        skill, ref, evidence = seven_owner_cases()[-2]  # e2e-test-selection
        meta, value, result = self.saved_single(skill, ref, evidence)
        owner_ev = value["workflow_scopes"][0]["normalized_input"]["owner_verification"]
        forged_text = owner_ev["stored_content"] + " "
        owner_ev["stored_content"] = forged_text
        sync_requested(value, result)
        resign(meta, value, result)
        result["payload"]["verified_owner_scopes"][0]["verified_artifact"][
            "content_hash"
        ] = sha(forged_text)
        resumed = resume(markdown(meta, value, result), current=[])
        self.assertTrue(resumed["valid"], resumed)

    def test_unregistered_owner_with_full_forged_evidence_is_rejected(self) -> None:
        # 期待: 登録されていない Skill は、証拠・記録が揃っていても拒否（registered 集合で止める）。
        skill, ref, evidence = seven_owner_cases()[0]
        meta, value, result = self.saved_single(skill, ref, evidence)
        value["workflow_scopes"][0]["skill"] = UNREG
        value["requested_scopes"][0]["skill"] = UNREG
        result["payload"]["requested_scopes"][0]["skill"] = UNREG
        result["payload"]["verified_owner_scopes"][0]["skill"] = UNREG
        resign(meta, value, result)
        rejected_with(
            resume(markdown(meta, value, result), current=[]),
            "unregistered owner scope is not allowed",
        )


def sync_requested(value: dict, result: dict) -> None:
    """改ざんで入力の要求集合を変えた場合、保存 result の宣言も同じ集合に揃える（宣言検査を通す）。"""
    if "requested_scopes" in value:
        result["payload"]["requested_scopes"] = copy.deepcopy(value["requested_scopes"])


def resume_with_binding(binding_source: str, presented: str) -> dict:
    request = {
        "workflow_ref": REF,
        "workflow_state_record": {
            "workflow_ref": REF,
            "schema_version": "1",
            "state": {
                "last_completed_qa_workflow_artifact": {
                    "artifact_ref": f"qa-workflow:{REF}",
                    "artifact_revision": "r1",
                    "artifact_sha256": sha(binding_source),
                }
            },
        },
        "current_scope_ids": [],
        "blocked_scope_ids": [],
        "previous_qa_workflow_artifact_markdown": presented,
        "scope_removal_resolutions": [],
        "scope_removal_applied_states": [],
    }
    return cli(DS_SCRIPT, request)


if __name__ == "__main__":
    unittest.main()
