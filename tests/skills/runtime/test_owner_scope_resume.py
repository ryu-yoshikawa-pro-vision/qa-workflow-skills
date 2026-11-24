"""owner verifier で完了した scope を含む保存済み v2 workflow の保存・再開の回帰テスト。

不具合の再現: owner verifier で完了した scope（runtime-v2 root を持たない Skill）は
current_structure_state=null を持つ。その結果を保存して再開すると、旧実装は null を
構造検査で拒否していた。本ファイルは workflow_runtime.py の実出力から保存済み履歴を組み、
downstream_state の再開検査（_validate_frozen_pair / evaluate）で受理されることを確認する。

- owner 側の証拠（保存本文・読戻し・承認証拠）は test_integration_required_scopes の fixture を使う。
- runtime-v2 root（TCD）の完了した state は test_workflow_runtime の _request() を基にする。
  その state の runtime result の fingerprint は既存の downstream テストと同じ方法で再計算する。
  これは実 condition runtime の検証経路（verify_runtime_evidence）から構成したものではない。
- v1 の履歴は、v2 の実結果から要求集合を外して版を戻した fixture で再現する（v1 は現行の CLI が
  生成しない過去契約）。
- 保存本文・読戻しは呼出し側の fixture であり、実 provider の読戻しではない。承認の真正性は
  owner validator が確立しないため、本テストでは扱わない。
"""

from __future__ import annotations

import copy
import hashlib
import json
import sys
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "skills" / "qa-workflow" / "scripts"))

import downstream_state as ds  # noqa: E402
import owner_verifiers  # noqa: E402
from runtime_contract import OWNER_VERIFIED_SKILLS, InvalidInput  # noqa: E402

import tests.skills.runtime.test_integration_required_scopes as I  # noqa: E402
import tests.skills.runtime.test_workflow_runtime as W  # noqa: E402

REF = I.WORKFLOW_REF
OTHER_REF = "00000000-0000-4000-8000-0000000000ff"
ROOT_ID = "qa-workflow::artifact:workflow_runtime:all"
OWNER_SKILLS = (I.RA, I.TA, I.TM)
UNREGISTERED = "defect-management"
TCD = "test-condition-design"


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _refresh_runtime_fingerprints(state: dict, unit_lists: list[list[dict]]) -> None:
    """TCD fixture の runtime result の fingerprint を、既存の downstream テストと同じ式で再計算する。"""
    for row in state["runtime_results"]:
        result = row["result"]
        result["runtime_implementation_fingerprint"] = "sha256:" + "a" * 64
        result["generator_implementation_fingerprint"] = "sha256:" + "b" * 64
        result["generation_fingerprint"] = W.runtime.generation_fingerprint(
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
        fresh = W.runtime.runtime_unit_row(result)
        for units in unit_lists:
            for index, unit in enumerate(units):
                if (
                    unit.get("skill") == fresh["skill"]
                    and unit.get("runtime_unit_key") == fresh["runtime_unit_key"]
                ):
                    units[index] = fresh


def tcd_base() -> dict:
    """runtime-v2 root（TCD）だけを持つ完了済みの入力（参照ワークフローを REF に合わせる）。"""
    base = W.WorkflowRuntimeTests()._request()
    input_value = base["input"]
    scope = input_value["workflow_scopes"][0]
    _refresh_runtime_fingerprints(
        scope["current_structure_state"],
        [input_value["runtime_units"], input_value["current_runtime_units"]],
    )
    input_value["workflow_ref"] = REF
    return {"metadata": copy.deepcopy(base["metadata"]), "input": input_value}


def run_workflow(
    metadata: dict, scopes: list[dict], requested: list[dict] | None, **extra: Any
) -> tuple[dict, dict]:
    """workflow_runtime を CLI として呼ぶ。入力と結果の組を返す（保存時に同じ入力を使うため）。"""
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
    result = W.run({"metadata": copy.deepcopy(metadata), "input": value})
    return value, result


def tcd_with_owners(fx: "OwnerFixture") -> tuple[dict, dict, list[dict]]:
    """TCD の完了 state に owner の3 scope を加えた入力（混在）。"""
    base = tcd_base()
    scopes = [base["input"]["workflow_scopes"][0], *fx.scopes()]
    requested = [
        base["input"]["requested_scopes"][0],
        *fx.requested(),
    ]
    value, result = run_workflow(
        base["metadata"],
        scopes,
        requested,
        runtime_units=base["input"]["runtime_units"],
        current_runtime_units=base["input"]["current_runtime_units"],
        current_entities=base["input"]["current_entities"],
        unsupported_item_closures=[],
    )
    return {"metadata": base["metadata"], "input": value}, result, requested


def saved_markdown(metadata: dict, value: dict, result: dict) -> str:
    """Machine Runtime Input / Result の保存形（既存テストと同じ見出しと JSON 本文）。"""
    source = {"metadata": metadata, "input": value}
    return (
        f"### Machine Runtime Input: {ROOT_ID}\n\n```json\n"
        f"{json.dumps(source, ensure_ascii=False)}\n```\n\n"
        f"### Machine Runtime Result: {ROOT_ID}\n\n```json\n"
        f"{json.dumps(result, ensure_ascii=False)}\n```\n"
    )


def binding_request(markdown: str | None, *, ref: str = REF) -> dict:
    state: dict[str, Any] = {"last_completed_qa_workflow_artifact": None}
    if markdown is not None:
        state["last_completed_qa_workflow_artifact"] = {
            "artifact_ref": "artifact:qa-workflow-r1",
            "artifact_revision": "qa-workflow-r1",
            "artifact_sha256": _sha(markdown),
        }
    return {
        "workflow_ref": ref,
        "workflow_state_record": {
            "workflow_ref": ref,
            "schema_version": "1",
            "state": state,
        },
        "current_scope_ids": [],
        "blocked_scope_ids": [],
        "previous_qa_workflow_artifact_markdown": markdown,
        "scope_removal_resolutions": [],
        "scope_removal_applied_states": [],
    }


def _refresh_identity(source: dict, envelope: dict, version: str) -> None:
    """版と入力を変えた後、保存済みのフィンガープリントを同じ式で再計算する（v1 downgrade 用）。"""
    metadata = source["metadata"]
    metadata["generator_contract_version"] = version
    envelope["generator_contract_version"] = version
    input_fp = ds.input_fingerprint(
        "qa-workflow",
        metadata["runtime_unit_key"],
        metadata["input_mode"],
        source["input"],
        metadata["authority_refs"],
        metadata["reference_refs"],
        metadata["selection_source"],
    )
    model_fp = ds.model_fingerprint(metadata, input_fp)
    upstream = ds.upstream_entity_fingerprints(ds.validate_upstream_entities(metadata))
    envelope["input_fingerprint"] = input_fp
    envelope["model_fingerprint"] = model_fp
    envelope["upstream_entity_fingerprints"] = upstream
    envelope["generation_fingerprint"] = ds.generation_fingerprint(
        generator="workflow_runtime",
        input_fp=input_fp,
        model_fp=model_fp,
        runtime_contract_version="runtime-v2",
        generator_contract_version=version,
        runtime_impl_fp=envelope["runtime_implementation_fingerprint"],
        generator_impl_fp=envelope["generator_implementation_fingerprint"],
        upstream=upstream,
        static_data_versions=envelope["static_data_versions"],
    )


V2_ONLY_PAYLOAD_KEYS = (
    "scope_set_declared",
    "requested_scopes",
    "missing_requested_scopes",
    "excluded_scopes",
    "unrequested_scopes",
    "verified_owner_scopes",
)


class OwnerFixture:
    """owner 3 Skill（RA/TA/TM）の保存成果物と、検証に使う証拠。"""

    def __init__(self) -> None:
        self.store = I.FixtureProvider()
        self.arts = {skill: I.Stored(skill, self.store) for skill in OWNER_SKILLS}

    def scopes(self, skills: tuple[str, ...] = OWNER_SKILLS) -> list[dict]:
        return [
            I.owner_scope(skill, self.arts[skill].ref, self.arts[skill].evidence())
            for skill in skills
        ]

    def requested(self, skills: tuple[str, ...] = OWNER_SKILLS) -> list[dict]:
        return [I.required(skill, self.arts[skill].ref) for skill in skills]


def verified_skills(result: dict) -> set[str]:
    return {row["skill"] for row in result["payload"]["verified_owner_scopes"]}


class OwnerScopeResumeTests(unittest.TestCase):
    """保存・再開の正常系（N1-N9）。"""

    def test_n1_owner_only_scopes_complete_and_resume(self) -> None:
        fx = OwnerFixture()
        meta = W.metadata()
        requested = fx.requested()
        value, result = run_workflow(meta, fx.scopes(), requested)
        self.assertEqual(result["runtime_status"], "ok", result)
        self.assertTrue(result["payload"]["can_complete"], result)
        self.assertEqual(verified_skills(result), set(OWNER_SKILLS))
        # N8: v2 の要求集合は結果に維持される。
        self.assertEqual(result["payload"]["requested_scopes"], requested)
        markdown = saved_markdown(meta, value, result)
        _, payload = ds._validate_frozen_pair(markdown, REF)
        self.assertTrue(payload["can_complete"])
        evaluated = ds.evaluate(binding_request(markdown))
        self.assertTrue(evaluated["valid"], evaluated)
        for key in (
            "inactive_tr_ids",
            "inactive_tcn_ids",
            "inactive_model_keys",
            "inactive_ci_ids",
            "inactive_tc_ids",
        ):
            self.assertEqual(evaluated["payload"][key], [], key)

    def test_n2_runtime_v2_only_scope_resumes_as_before(self) -> None:
        base = tcd_base()
        value, result = run_workflow(
            base["metadata"],
            base["input"]["workflow_scopes"],
            base["input"]["requested_scopes"],
            runtime_units=base["input"]["runtime_units"],
            current_runtime_units=base["input"]["current_runtime_units"],
            current_entities=base["input"]["current_entities"],
            unsupported_item_closures=[],
        )
        self.assertTrue(result["payload"]["can_complete"], result)
        self.assertEqual(result["payload"]["verified_owner_scopes"], [])
        _, payload = ds._validate_frozen_pair(
            saved_markdown(base["metadata"], value, result), REF
        )
        self.assertTrue(payload["can_complete"])

    def test_n3_mixed_runtime_v2_and_owner_scopes_resume(self) -> None:
        fx = OwnerFixture()
        source, result, _requested = tcd_with_owners(fx)
        self.assertTrue(result["payload"]["can_complete"], result)
        self.assertEqual(verified_skills(result), set(OWNER_SKILLS))
        markdown = saved_markdown(source["metadata"], source["input"], result)
        _, payload = ds._validate_frozen_pair(markdown, REF)
        self.assertTrue(payload["can_complete"])
        evaluated = ds.evaluate(binding_request(markdown))
        self.assertTrue(evaluated["valid"], evaluated)

    def test_n4_unchanged_inputs_reuse_the_same_verified_records(self) -> None:
        fx = OwnerFixture()
        meta = W.metadata()
        value, first = run_workflow(meta, fx.scopes(), fx.requested())
        _, second = run_workflow(meta, fx.scopes(), fx.requested())
        self.assertEqual(
            first["payload"]["verified_owner_scopes"],
            second["payload"]["verified_owner_scopes"],
        )
        self.assertEqual(first["payload"], second["payload"])

    def test_n5_only_the_changed_owner_scope_becomes_unverified(self) -> None:
        fx = OwnerFixture()
        meta = W.metadata()
        scopes = fx.scopes()
        # TM の revision だけを古い値に変える（保存後に revision が進んだ想定）。
        scopes[2]["normalized_input"]["owner_verification"]["expected_revision"] = (
            "tm-stale-rev"
        )
        _, result = run_workflow(meta, scopes, fx.requested())
        self.assertFalse(result["payload"]["can_complete"], result)
        self.assertEqual(verified_skills(result), {I.RA, I.TA})
        self.assertEqual(
            [row["skill"] for row in result["payload"]["unverified_scopes"]], [I.TM]
        )

    def test_n6_completed_workflow_resume_is_stable(self) -> None:
        fx = OwnerFixture()
        source, result, _requested = tcd_with_owners(fx)
        markdown = saved_markdown(source["metadata"], source["input"], result)
        first = ds.evaluate(binding_request(markdown))
        second = ds.evaluate(binding_request(markdown))
        self.assertEqual(first, second)

    def test_n7_v1_root_history_still_reads(self) -> None:
        # v1 は過去契約（要求集合・検証記録を持たない）。v2 の実結果から版を戻した fixture で確認する。
        base = tcd_base()
        value, result = run_workflow(
            base["metadata"],
            base["input"]["workflow_scopes"],
            base["input"]["requested_scopes"],
            runtime_units=base["input"]["runtime_units"],
            current_runtime_units=base["input"]["current_runtime_units"],
            current_entities=base["input"]["current_entities"],
            unsupported_item_closures=[],
        )
        source = {
            "metadata": copy.deepcopy(base["metadata"]),
            "input": copy.deepcopy(value),
        }
        envelope = copy.deepcopy(result)
        del source["input"]["requested_scopes"]
        for key in V2_ONLY_PAYLOAD_KEYS:
            envelope["payload"].pop(key, None)
        _refresh_identity(source, envelope, "workflow-runtime-v1")
        markdown = (
            f"### Machine Runtime Input: {ROOT_ID}\n\n```json\n"
            f"{json.dumps(source, ensure_ascii=False)}\n```\n\n"
            f"### Machine Runtime Result: {ROOT_ID}\n\n```json\n"
            f"{json.dumps(envelope, ensure_ascii=False)}\n```\n"
        )
        _, payload = ds._validate_frozen_pair(markdown, REF)
        self.assertTrue(payload["can_complete"])

    def test_n7_v1_owner_null_scope_keeps_the_old_rejection(self) -> None:
        # v1 の検査は変えない。null の owner scope は従来どおり v1 の構造検査で拒否される。
        fx = OwnerFixture()
        source, result, _requested = tcd_with_owners(fx)
        source = copy.deepcopy(source)
        envelope = copy.deepcopy(result)
        del source["input"]["requested_scopes"]
        for key in V2_ONLY_PAYLOAD_KEYS:
            envelope["payload"].pop(key, None)
        _refresh_identity(source, envelope, "workflow-runtime-v1")
        markdown = (
            f"### Machine Runtime Input: {ROOT_ID}\n\n```json\n"
            f"{json.dumps(source, ensure_ascii=False)}\n```\n\n"
            f"### Machine Runtime Result: {ROOT_ID}\n\n```json\n"
            f"{json.dumps(envelope, ensure_ascii=False)}\n```\n"
        )
        with self.assertRaises(InvalidInput):
            ds._validate_frozen_pair(markdown, REF)

    def test_n8_requested_scopes_are_kept_in_the_saved_result(self) -> None:
        fx = OwnerFixture()
        meta = W.metadata()
        requested = fx.requested((I.RA, I.TA))
        value, result = run_workflow(meta, fx.scopes((I.RA, I.TA)), requested)
        self.assertTrue(result["payload"]["can_complete"], result)
        self.assertEqual(result["payload"]["requested_scopes"], requested)
        self.assertEqual(result["payload"]["missing_requested_scopes"], [])
        ds._validate_frozen_pair(saved_markdown(meta, value, result), REF)

    def test_n9_zero_scopes_is_not_complete(self) -> None:
        # 既存動作: 対象 scope が0件の workflow は dispatch されず invalid_input になる（完了しない）。
        meta = W.metadata()
        _value, result = run_workflow(meta, [], [])
        self.assertEqual(result["runtime_status"], "invalid_input", result)
        self.assertFalse(result.get("payload", {}).get("can_complete", False), result)


class OwnerScopeRejectionTests(unittest.TestCase):
    """異常系（E1-E17）と scope 遷移の一部。"""

    def test_e1_runtime_v2_root_null_state_is_refused_by_workflow(self) -> None:
        base = tcd_base()
        scopes = copy.deepcopy(base["input"]["workflow_scopes"])
        scopes[0]["current_structure_state"] = None
        _value, result = run_workflow(
            base["metadata"],
            scopes,
            base["input"]["requested_scopes"],
            runtime_units=base["input"]["runtime_units"],
            current_runtime_units=base["input"]["current_runtime_units"],
            current_entities=base["input"]["current_entities"],
        )
        self.assertEqual(result["runtime_status"], "invalid_input", result)
        self.assertFalse(result.get("payload", {}).get("can_complete", False))

    def test_e1_runtime_v2_root_null_state_is_refused_by_resume(self) -> None:
        base = tcd_base()
        value, result = run_workflow(
            base["metadata"],
            base["input"]["workflow_scopes"],
            base["input"]["requested_scopes"],
            runtime_units=base["input"]["runtime_units"],
            current_runtime_units=base["input"]["current_runtime_units"],
            current_entities=base["input"]["current_entities"],
        )
        value = copy.deepcopy(value)
        value["workflow_scopes"][0]["current_structure_state"] = None
        with self.assertRaises(InvalidInput):
            ds._validate_frozen_pair(
                saved_markdown(base["metadata"], value, result), REF
            )

    def test_e2_owner_scope_with_non_null_state_fails_at_completion(self) -> None:
        # 空 dict・不正構造・TCD の完了 state の流用を、完了時点で invalid_input にする。
        fx = OwnerFixture()
        meta = W.metadata()
        forged_states = [
            {
                "runtime_results": [],
                "carry_forward_entities": [],
                "previous_ci_id_state": [],
            },
            {"foo": 1},
            tcd_base()["input"]["workflow_scopes"][0]["current_structure_state"],
        ]
        for state in forged_states:
            with self.subTest(state=str(state)[:60]):
                scopes = fx.scopes()
                scopes[0]["current_structure_state"] = copy.deepcopy(state)
                _value, result = run_workflow(meta, scopes, fx.requested())
                self.assertEqual(result["runtime_status"], "invalid_input", result)
                self.assertFalse(result.get("payload", {}).get("can_complete", False))

    def test_e3_saved_owner_scope_without_verification_record_is_refused(self) -> None:
        fx = OwnerFixture()
        meta = W.metadata()
        value, result = run_workflow(meta, fx.scopes(), fx.requested())
        self.assertTrue(result["payload"]["can_complete"], result)
        # 検証記録の欠落（空）と、1件だけ欠落、の forged 結果はどちらも拒否する。
        for kept in ([], [I.RA, I.TA]):
            with self.subTest(kept=kept):
                forged = copy.deepcopy(result)
                forged["payload"]["verified_owner_scopes"] = [
                    row
                    for row in forged["payload"]["verified_owner_scopes"]
                    if row["skill"] in kept
                ]
                with self.assertRaises(InvalidInput):
                    ds._validate_frozen_pair(saved_markdown(meta, value, forged), REF)

    def test_e3_saved_owner_record_for_another_identity_is_refused(self) -> None:
        fx = OwnerFixture()
        meta = W.metadata()
        value, result = run_workflow(meta, fx.scopes(), fx.requested())
        forged = copy.deepcopy(result)
        forged["payload"]["verified_owner_scopes"][0]["target"] = "other-target"
        with self.assertRaises(InvalidInput):
            ds._validate_frozen_pair(saved_markdown(meta, value, forged), REF)

    def test_e4_another_workflow_result_is_refused(self) -> None:
        fx = OwnerFixture()
        meta = W.metadata()
        value, result = run_workflow(meta, fx.scopes(), fx.requested())
        markdown = saved_markdown(meta, value, result)
        with self.assertRaises(InvalidInput):
            ds._validate_frozen_pair(markdown, OTHER_REF)
        with self.assertRaises(InvalidInput):
            ds.evaluate(binding_request(markdown, ref=OTHER_REF))

    def test_e5_artifact_of_another_case_is_not_verified(self) -> None:
        fx = OwnerFixture()
        scopes = fx.scopes()
        # TM の証拠を RA の target に当てる（別案件の成果物を当てた状態）。
        scopes[2]["target"] = fx.arts[I.RA].ref
        _value, result = run_workflow(W.metadata(), scopes, fx.requested())
        self.assertFalse(result["payload"]["can_complete"], result)
        self.assertNotIn(I.TM, verified_skills(result))

    def test_e6_hash_mismatch_is_not_verified(self) -> None:
        fx = OwnerFixture()
        scopes = fx.scopes()
        evidence = scopes[1]["normalized_input"]["owner_verification"]
        evidence["stored_content"] = I.flip_last_char(evidence["stored_content"])
        _value, result = run_workflow(W.metadata(), scopes, fx.requested())
        self.assertFalse(result["payload"]["can_complete"], result)
        self.assertNotIn(I.TA, verified_skills(result))

    def test_e7_invalid_fingerprint_in_saved_result_is_refused(self) -> None:
        fx = OwnerFixture()
        meta = W.metadata()
        value, result = run_workflow(meta, fx.scopes(), fx.requested())
        bad_input = copy.deepcopy(result)
        bad_input["input_fingerprint"] = "sha256:" + "0" * 64
        with self.assertRaises(InvalidInput):
            ds._validate_frozen_pair(saved_markdown(meta, value, bad_input), REF)
        bad_format = copy.deepcopy(result)
        bad_format["runtime_implementation_fingerprint"] = "not-a-digest"
        with self.assertRaises(InvalidInput):
            ds._validate_frozen_pair(saved_markdown(meta, value, bad_format), REF)

    def test_e8_omitted_required_scope_is_not_complete(self) -> None:
        fx = OwnerFixture()
        meta = W.metadata()
        value, result = run_workflow(
            meta, fx.scopes((I.RA, I.TA)), fx.requested(OWNER_SKILLS)
        )
        self.assertFalse(result["payload"]["can_complete"], result)
        self.assertIn(
            I.TM,
            {row["skill"] for row in result["payload"]["missing_requested_scopes"]},
        )
        with self.assertRaises(InvalidInput):
            ds._validate_frozen_pair(saved_markdown(meta, value, result), REF)

    def test_e9_excluded_by_approval_is_not_confirmed(self) -> None:
        fx = OwnerFixture()
        meta = W.metadata()
        requested = fx.requested((I.RA, I.TA)) + [I.excluded(I.TM)]
        value, result = run_workflow(meta, fx.scopes((I.RA, I.TA)), requested)
        self.assertEqual(result["payload"]["excluded_scopes"], [], result)
        self.assertFalse(result["payload"]["can_complete"], result)
        forged = copy.deepcopy(result)
        forged["payload"]["can_complete"] = True
        forged["result_status"] = "ready"
        with self.assertRaises(InvalidInput):
            ds._validate_frozen_pair(saved_markdown(meta, value, forged), REF)

    def test_e10_unregistered_skill_is_not_completed_by_null_state(self) -> None:
        fx = OwnerFixture()
        meta = W.metadata()
        unregistered = I.owner_scope(UNREGISTERED, "unregistered-target", {})
        requested = fx.requested() + [I.required(UNREGISTERED, "unregistered-target")]
        value, result = run_workflow(meta, fx.scopes() + [unregistered], requested)
        self.assertFalse(result["payload"]["can_complete"], result)
        self.assertEqual(
            result["payload"]["unverified_scopes"][0]["skill"], UNREGISTERED
        )
        with self.assertRaises(InvalidInput):
            ds._validate_frozen_pair(saved_markdown(meta, value, result), REF)

    def test_e11_owner_verifier_failure_is_not_completed(self) -> None:
        fx = OwnerFixture()
        scopes = fx.scopes()
        scopes[0]["normalized_input"] = {}
        _value, result = run_workflow(W.metadata(), scopes, fx.requested())
        self.assertFalse(result["payload"]["can_complete"], result)
        self.assertNotIn(I.RA, verified_skills(result))

    def test_e12_stale_or_unknown_source_is_not_current(self) -> None:
        fx = OwnerFixture()
        for case in ("stale", "unknown"):
            with self.subTest(case=case):
                scopes = fx.scopes()
                evidence = scopes[1]["normalized_input"]["owner_verification"]
                if case == "stale":
                    evidence["current_source_refs"][0]["content_hash"] = _sha("changed")
                else:
                    evidence["current_source_refs"] = []
                _value, result = run_workflow(W.metadata(), scopes, fx.requested())
                self.assertFalse(result["payload"]["can_complete"], result)
                self.assertNotIn(I.TA, verified_skills(result))

    def test_e13_revision_change_after_save_is_not_the_latest_readback(self) -> None:
        fx = OwnerFixture()
        scopes = fx.scopes()
        # 保存後に expected_revision が進んだ場合、古い readback を最新として扱わない。
        scopes[1]["normalized_input"]["owner_verification"]["expected_revision"] = (
            "ta-r2"
        )
        _value, result = run_workflow(W.metadata(), scopes, fx.requested())
        self.assertFalse(result["payload"]["can_complete"], result)
        self.assertNotIn(I.TA, verified_skills(result))

    def test_e14_duplicate_scope_identity_is_refused(self) -> None:
        fx = OwnerFixture()
        scopes = fx.scopes()
        _value, result = run_workflow(
            W.metadata(), scopes + [copy.deepcopy(scopes[0])], fx.requested()
        )
        self.assertEqual(result["runtime_status"], "invalid_input", result)

    def test_e15_malformed_machine_blocks_are_refused(self) -> None:
        fx = OwnerFixture()
        meta = W.metadata()
        value, result = run_workflow(meta, fx.scopes(), fx.requested())
        markdown = saved_markdown(meta, value, result)
        missing_result = markdown.split("### Machine Runtime Result")[0]
        with self.assertRaises(InvalidInput):
            ds._validate_frozen_pair(missing_result, REF)
        broken_json = markdown.replace('"requested_scopes"', '"requested_scopes"]', 1)
        with self.assertRaises(InvalidInput):
            ds._validate_frozen_pair(broken_json, REF)

    def test_e16_unapproved_architecture_is_not_confirmed(self) -> None:
        fx = OwnerFixture()
        scopes = fx.scopes()
        scopes[1]["normalized_input"]["owner_verification"]["approval_evidence"] = []
        meta = W.metadata()
        value, result = run_workflow(meta, scopes, fx.requested())
        self.assertFalse(result["payload"]["can_complete"], result)
        self.assertNotIn(I.TA, verified_skills(result))
        forged = copy.deepcopy(result)
        forged["payload"]["can_complete"] = True
        with self.assertRaises(InvalidInput):
            ds._validate_frozen_pair(saved_markdown(meta, value, forged), REF)

    def test_e17_failed_resume_does_not_change_the_baseline(self) -> None:
        fx = OwnerFixture()
        source, result, _requested = tcd_with_owners(fx)
        markdown = saved_markdown(source["metadata"], source["input"], result)
        baseline_request = binding_request(markdown)
        before = copy.deepcopy(baseline_request)
        # 束縛の sha は正常な保存本文のもの。渡す本文を改変すると、再開は失敗する。
        tampered = copy.deepcopy(baseline_request)
        tampered["previous_qa_workflow_artifact_markdown"] = markdown + "\n"
        with self.assertRaises(InvalidInput):
            ds.evaluate(tampered)
        self.assertEqual(baseline_request, before)
        self.assertTrue(ds.evaluate(baseline_request)["valid"])
        self.assertEqual(baseline_request, before)

    def test_owner_add_and_remove_do_not_change_entity_history(self) -> None:
        # owner scope の追加・削除で、履歴 Entity（TR・TCN・CI・TC）の増減を起こさない。
        base = tcd_base()
        tcd_only_value, tcd_only = run_workflow(
            base["metadata"],
            base["input"]["workflow_scopes"],
            base["input"]["requested_scopes"],
            runtime_units=base["input"]["runtime_units"],
            current_runtime_units=base["input"]["current_runtime_units"],
            current_entities=base["input"]["current_entities"],
        )
        tcd_only_md = saved_markdown(base["metadata"], tcd_only_value, tcd_only)
        fx = OwnerFixture()
        mixed_source, mixed, _requested = tcd_with_owners(fx)
        mixed_md = saved_markdown(
            mixed_source["metadata"], mixed_source["input"], mixed
        )
        only = ds.evaluate(binding_request(tcd_only_md))["payload"]
        both = ds.evaluate(binding_request(mixed_md))["payload"]
        for key in (
            "inactive_tr_ids",
            "inactive_tcn_ids",
            "inactive_model_keys",
            "inactive_ci_ids",
            "inactive_tc_ids",
            "inactive_tr_history",
            "inactive_tcn_history",
            "inactive_model_history",
            "inactive_materialize_history",
            "inactive_tc_history",
        ):
            self.assertEqual(both[key], only[key], key)


class RuntimeV2RootConsistencyTests(unittest.TestCase):
    """runtime-v2 root の正本（runtime_contract）と、評価側の集合（common）の一致を検査する。"""

    def test_eval_verified_skills_match_runtime_contract_roots(self) -> None:
        from runtime_contract import RUNTIME_V2_SKILL_ROOTS

        from scripts.skills.evals.deterministic.common import WORKFLOW_VERIFIED_SKILLS

        self.assertEqual(set(WORKFLOW_VERIFIED_SKILLS), set(RUNTIME_V2_SKILL_ROOTS))


class OwnerRecordEvidenceTests(unittest.TestCase):
    """null の owner scope の検証記録は、登録・保存済み証拠・target と照合して初めて受理される。"""

    def _saved(self) -> tuple[dict, dict, dict]:
        fx = OwnerFixture()
        meta = W.metadata()
        value, result = run_workflow(meta, fx.scopes(), fx.requested())
        self.assertTrue(result["payload"]["can_complete"], result)
        return meta, value, result

    def _reject(self, mutate) -> None:
        meta, value, result = self._saved()
        value = copy.deepcopy(value)
        result = copy.deepcopy(result)
        mutate(value, result)
        source = {"metadata": copy.deepcopy(meta), "input": value}
        _refresh_identity(source, result, "workflow-runtime-v2")
        markdown = saved_markdown(meta, value, result)
        with self.assertRaises(InvalidInput):
            ds._validate_frozen_pair(markdown, REF)

    @staticmethod
    def _scope(value: dict, skill: str) -> dict:
        return next(row for row in value["workflow_scopes"] if row["skill"] == skill)

    @staticmethod
    def _record(result: dict, skill: str) -> dict:
        return next(
            row
            for row in result["payload"]["verified_owner_scopes"]
            if row["skill"] == skill
        )

    def test_positive_saved_owner_triple_is_accepted_with_consistent_records(
        self,
    ) -> None:
        meta, value, result = self._saved()
        ds._validate_frozen_pair(saved_markdown(meta, value, result), REF)

    def test_n10_unregistered_skill_with_forged_empty_record_is_rejected(self) -> None:
        def mutate(value, result):
            value["workflow_scopes"].append(
                {
                    "skill": UNREGISTERED,
                    "target": "DM-1",
                    "execution_range": "plan",
                    "input_mode": "artifact",
                    "normalized_input": {},
                    "current_structure_state": None,
                }
            )
            value["requested_scopes"].append(
                {
                    "skill": UNREGISTERED,
                    "target": "DM-1",
                    "execution_range": "plan",
                    "requirement": "required",
                }
            )
            result["payload"]["requested_scopes"] = copy.deepcopy(
                value["requested_scopes"]
            )
            result["payload"]["verified_owner_scopes"].append(
                {
                    "skill": UNREGISTERED,
                    "target": "DM-1",
                    "execution_range": "plan",
                    "verified_artifact": {},
                }
            )

        self._reject(mutate)

    def test_n10_unregistered_skill_with_plausible_evidence_is_still_rejected(
        self,
    ) -> None:
        # 証拠・識別子が一見正しくても、登録されていない Skill の null は受理しない。
        def mutate(value, result):
            text = '{"artifact_ref":"DM-1"}'
            value["workflow_scopes"].append(
                {
                    "skill": UNREGISTERED,
                    "target": "DM-1",
                    "execution_range": "plan",
                    "input_mode": "artifact",
                    "normalized_input": {
                        "owner_verification": {"stored_content": text}
                    },
                    "current_structure_state": None,
                }
            )
            value["requested_scopes"].append(
                {
                    "skill": UNREGISTERED,
                    "target": "DM-1",
                    "execution_range": "plan",
                    "requirement": "required",
                }
            )
            result["payload"]["requested_scopes"] = copy.deepcopy(
                value["requested_scopes"]
            )
            result["payload"]["verified_owner_scopes"].append(
                {
                    "skill": UNREGISTERED,
                    "target": "DM-1",
                    "execution_range": "plan",
                    "verified_artifact": {
                        "artifact_ref": "DM-1",
                        "artifact_revision": "r1",
                        "content_hash": _sha(text),
                    },
                }
            )

        self._reject(mutate)

    def test_probe_missing_evidence_with_record_is_rejected(self) -> None:
        # 証拠なし（owner_verification を {} にして記録だけ残す）。
        self._reject(
            lambda value, result: self._scope(value, I.RA)["normalized_input"].update(
                owner_verification={}
            )
        )

    def test_probe_missing_evidence_key_with_record_is_rejected(self) -> None:
        self._reject(
            lambda value, result: self._scope(value, I.RA)["normalized_input"].pop(
                "owner_verification"
            )
        )

    def test_probe_altered_stored_text_with_record_is_rejected(self) -> None:
        # 証拠改ざん（保存本文を書き換え、記録の content_hash は元のまま）。
        def mutate(value, result):
            evidence = self._scope(value, I.RA)["normalized_input"][
                "owner_verification"
            ]
            evidence["stored_content"] = I.flip_last_char(evidence["stored_content"])

        self._reject(mutate)

    def test_record_artifact_ref_must_match_scope_target(self) -> None:
        self._reject(
            lambda value, result: self._record(result, I.TM)[
                "verified_artifact"
            ].update(artifact_ref="artifact:other-case-r1")
        )

    def test_record_identity_fields_must_be_non_empty_strings(self) -> None:
        for key in ("artifact_revision", "content_hash"):
            with self.subTest(key=key):
                self._reject(
                    lambda value, result, key=key: self._record(result, I.TA)[
                        "verified_artifact"
                    ].pop(key)
                )

    def test_c1_swapped_records_between_two_targets_of_one_skill_are_rejected(
        self,
    ) -> None:
        # 同一 skill の2 target（RA）を追加し、記録を入れ替える。どちらの入替えも target 不一致で拒否。
        def add_second_target(value, result, *, swap: bool):
            base_scope = copy.deepcopy(self._scope(value, I.RA))
            base_scope["target"] = "artifact:ra-second-target-r1"
            value["workflow_scopes"].append(base_scope)
            value["requested_scopes"].append(
                {
                    "skill": I.RA,
                    "target": base_scope["target"],
                    "execution_range": "plan",
                    "requirement": "required",
                }
            )
            ra_record = copy.deepcopy(self._record(result, I.RA))
            second = copy.deepcopy(ra_record)
            second["target"] = base_scope["target"]
            if swap:
                # 2つの記録の検証結果（verified_artifact）を入れ替える。
                first_art = ra_record["verified_artifact"]
                ra_record["verified_artifact"] = second["verified_artifact"]
                second["verified_artifact"] = first_art
            result["payload"]["verified_owner_scopes"].append(second)
            result["payload"]["requested_scopes"] = copy.deepcopy(
                value["requested_scopes"]
            )

        for swap in (False, True):
            with self.subTest(swap=swap):
                self._reject(lambda v, r, swap=swap: add_second_target(v, r, swap=swap))

    def test_owner_verified_skills_match_owner_verifier_registry(self) -> None:
        self.assertEqual(set(owner_verifiers.VERIFIERS), set(OWNER_VERIFIED_SKILLS))


if __name__ == "__main__":
    unittest.main()
