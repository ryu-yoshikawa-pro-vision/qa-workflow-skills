"""test-requirements-analysis の保存済み成果物検証入口（qa_requirement_runtime.py）の検証。

scriptはサブプロセスでJSON stdin / JSON stdoutとして呼び、owner verifierと同じ入出力境界を確認する。
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

ROOT = Path(__file__).resolve().parents[3]
SKILL = ROOT / "skills" / "test-requirements-analysis"
SCRIPT = SKILL / "scripts" / "qa_requirement_runtime.py"
EXAMPLE = SKILL / "assets" / "packet-example.json"
OWNER = "test-requirements-analysis"
AUTHENTICITY = "not_established_by_this_validator"
MAX_INPUT_BYTES = 16 * 1024 * 1024
ENV = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}


def _canonical(value) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _sha(value) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def call_raw(raw: bytes) -> dict:
    completed = subprocess.run(
        [sys.executable, "-B", str(SCRIPT)],
        input=raw,
        capture_output=True,
        check=False,
        env=ENV,
    )
    if completed.returncode != 0:
        raise AssertionError(completed.stderr.decode("utf-8", "replace"))
    return json.loads(completed.stdout.decode("utf-8"))


def call(request) -> dict:
    return call_raw(json.dumps(request, ensure_ascii=False).encode("utf-8"))


def codes(result: dict) -> set[str]:
    return {row["code"] for row in result["issues"]}


def base_packet() -> dict:
    return json.loads(EXAMPLE.read_text(encoding="utf-8"))


def current_refs(packet: dict) -> list[dict]:
    return [
        {
            "owner": s["owner"],
            "scope": s["scope"],
            "artifact_ref": s["artifact_ref"],
            "revision": s["revision"],
            "content_hash": s["content_hash"],
        }
        for s in packet["sources"]
    ]


def readback_for(packet: dict, **overrides) -> dict:
    row = {
        "owner": OWNER,
        "scope": packet["scope"],
        "artifact_ref": packet["artifact_ref"],
        "revision": str(packet["revision"]),
        "content_hash": _sha(packet),
    }
    row.update(overrides)
    return row


def approved(packet: dict) -> dict:
    """Approved packet bound to the packet's own scope, artifact_ref and revision."""
    packet = copy.deepcopy(packet)
    packet["status"] = "承認済み"
    packet["approval"] = {
        "state": "承認済み",
        "not_required_reason": None,
        "record": {
            "scope": packet["scope"],
            "artifact_ref": packet["artifact_ref"],
            "revision": packet["revision"],
            "approver": "承認者（fixture）",
            "role": "QA承認者",
            "evidence_ref": "fixture://approval/orders-q4/1",
            "expiry_condition": "要求scopeまたは根拠sourceが変わったとき",
        },
    }
    return packet


def with_open_requirement(packet: dict) -> dict:
    """QAR-002 becomes unresolved, with a matching open item."""
    packet = copy.deepcopy(packet)
    req = packet["requirements"][1]
    req["state"] = "未解決"
    req["open_item_id"] = "OPEN-001"
    packet["open_items"] = [
        {
            "item_id": "OPEN-001",
            "requirement_id": req["requirement_id"],
            "impact_scope": [req["scope"]],
            "owner": "QA責任者（fixture）",
            "state": "未解決",
            "resume_condition": "対象外かどうかを利用者が判断したとき",
        }
    ]
    return packet


def bump_revision(packet: dict, revision: int) -> dict:
    packet = copy.deepcopy(packet)
    packet["revision"] = revision
    packet["history"].append(
        {
            "revision": revision,
            "replaces_ref": packet["artifact_ref"],
            "replaces_revision": revision - 1,
            "change_reason": "改版（fixture）",
            "impact_scope": [packet["scope"]],
            "rechecks": [],
        }
    )
    return packet


class RequirementPacketScriptTests(unittest.TestCase):
    def setUp(self) -> None:
        self.packet = base_packet()

    # ---- validate / readback / impact / completion on a valid packet -------

    def test_valid_packet_passes_validate(self) -> None:
        result = call({"operation": "validate", "artifact": self.packet})
        self.assertTrue(result["valid"], result)
        self.assertEqual(result["status"], "valid")
        self.assertEqual(result["issues"], [])

    def test_readback_matches_stored_canonical_bytes(self) -> None:
        result = call(
            {
                "operation": "validate_readback",
                "candidate_artifact": self.packet,
                "readback": readback_for(self.packet),
                "expected_revision": "1",
            }
        )
        self.assertEqual(result["status"], "readback_matches", result)
        self.assertTrue(result["valid"])
        self.assertEqual(result["storage_content_sha256"], _sha(self.packet))
        self.assertEqual(result["provider_authenticity"], AUTHENTICITY)

    def test_readback_accepts_integer_expected_revision(self) -> None:
        result = call(
            {
                "operation": "validate_readback",
                "candidate_artifact": self.packet,
                "readback": readback_for(self.packet),
                "expected_revision": 1,
            }
        )
        self.assertEqual(result["status"], "readback_matches", result)

    def test_impact_is_current_when_all_sources_match(self) -> None:
        result = call(
            {
                "operation": "impact",
                "artifact": self.packet,
                "current_source_refs": current_refs(self.packet),
            }
        )
        self.assertEqual(result["status"], "current", result)
        self.assertTrue(result["valid"])
        self.assertEqual(result["impacted_requirement_ids"], [])

    def test_completion_is_complete_without_approval_when_not_required(self) -> None:
        result = call(
            {
                "operation": "completion_check",
                "artifact": self.packet,
                "current_source_refs": current_refs(self.packet),
            }
        )
        self.assertTrue(result["complete"], result)
        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["issues"], [])
        self.assertNotIn("approval_authenticity", result)

    def test_approved_packet_with_bound_record_completes_without_authenticating(
        self,
    ) -> None:
        packet = approved(self.packet)
        result = call(
            {
                "operation": "completion_check",
                "artifact": packet,
                "current_source_refs": current_refs(packet),
            }
        )
        self.assertTrue(result["complete"], result)
        self.assertEqual(result["approval_state"], "承認済み")
        self.assertEqual(result["approval_authenticity"], AUTHENTICITY)

    # ---- readback tamper / binding -----------------------------------------

    def test_tampered_stored_content_fails_readback(self) -> None:
        stored_hash = readback_for(self.packet)["content_hash"]
        tampered = copy.deepcopy(self.packet)
        tampered["purpose"]["qa_purpose"] = "改ざんされた目的"
        result = call(
            {
                "operation": "validate_readback",
                "candidate_artifact": tampered,
                "readback": readback_for(self.packet, content_hash=stored_hash),
                "expected_revision": "1",
            }
        )
        self.assertEqual(result["status"], "blocked")
        self.assertIn("readback_hash_mismatch", codes(result))

    def test_expected_revision_mismatch_blocks(self) -> None:
        result = call(
            {
                "operation": "validate_readback",
                "candidate_artifact": self.packet,
                "readback": readback_for(self.packet),
                "expected_revision": "2",
            }
        )
        self.assertFalse(result["valid"])
        self.assertIn("expected_revision_mismatch", codes(result))

    def test_readback_revision_mismatch_blocks(self) -> None:
        result = call(
            {
                "operation": "validate_readback",
                "candidate_artifact": self.packet,
                "readback": readback_for(self.packet, revision="3"),
                "expected_revision": "1",
            }
        )
        self.assertFalse(result["valid"])
        self.assertIn("readback_revision_mismatch", codes(result))

    def test_expected_revision_none_empty_or_missing_is_refused(self) -> None:
        base = {
            "operation": "validate_readback",
            "candidate_artifact": self.packet,
            "readback": readback_for(self.packet),
        }
        for label, extra in (
            ("none", {"expected_revision": None}),
            ("empty", {"expected_revision": ""}),
            ("blank", {"expected_revision": "   "}),
            ("missing", {}),
        ):
            with self.subTest(label=label):
                result = call({**base, **extra})
                self.assertEqual(result["status"], "blocked")
                self.assertFalse(result["valid"])
                self.assertIn("issues", result)

    def test_other_scope_artifact_fails_readback(self) -> None:
        result = call(
            {
                "operation": "validate_readback",
                "candidate_artifact": self.packet,
                "readback": readback_for(self.packet, scope="another-scope"),
                "expected_revision": "1",
            }
        )
        self.assertFalse(result["valid"])
        self.assertIn("readback_identity_mismatch", codes(result))

    def test_other_artifact_ref_fails_readback(self) -> None:
        result = call(
            {
                "operation": "validate_readback",
                "candidate_artifact": self.packet,
                "readback": readback_for(
                    self.packet, artifact_ref="fixture://requirements/other"
                ),
                "expected_revision": "1",
            }
        )
        self.assertFalse(result["valid"])
        self.assertIn("readback_identity_mismatch", codes(result))

    def test_other_owner_case_fails_readback(self) -> None:
        result = call(
            {
                "operation": "validate_readback",
                "candidate_artifact": self.packet,
                "readback": readback_for(self.packet, owner="test-architecture-design"),
                "expected_revision": "1",
            }
        )
        self.assertFalse(result["valid"])
        self.assertIn("readback_identity_mismatch", codes(result))

    def test_readback_hash_must_be_sha256_hex(self) -> None:
        result = call_raw(
            json.dumps(
                {
                    "operation": "validate_readback",
                    "candidate_artifact": self.packet,
                    "readback": readback_for(self.packet, content_hash="ABC"),
                    "expected_revision": "1",
                },
                ensure_ascii=False,
            ).encode("utf-8")
        )
        self.assertEqual(result["status"], "blocked")
        self.assertIn("readback_hash_invalid", codes(result))

    # ---- impact / source currentness ----------------------------------------

    def test_changed_source_marks_only_dependent_requirements(self) -> None:
        refs = current_refs(self.packet)
        refs[0] = {**refs[0], "revision": "spec-r4", "content_hash": "1" * 64}
        result = call(
            {
                "operation": "impact",
                "artifact": self.packet,
                "current_source_refs": refs,
            }
        )
        self.assertEqual(result["status"], "stale", result)
        self.assertEqual(
            result["stale_source_refs"], ["fixture://spec/orders/authority"]
        )
        self.assertEqual(result["impacted_requirement_ids"], ["QAR-001"])
        self.assertEqual(result["unaffected_requirement_ids"], ["QAR-002"])

    def test_changed_content_hash_alone_is_stale(self) -> None:
        refs = current_refs(self.packet)
        refs[1] = {**refs[1], "content_hash": "2" * 64}
        result = call(
            {
                "operation": "impact",
                "artifact": self.packet,
                "current_source_refs": refs,
            }
        )
        self.assertEqual(result["status"], "stale")
        self.assertEqual(result["impacted_requirement_ids"], ["QAR-002"])

    def test_unrelated_source_change_keeps_packet_current(self) -> None:
        refs = current_refs(self.packet)
        refs.append(
            {
                "owner": "spec-analysis",
                "scope": "other-scope",
                "artifact_ref": "fixture://spec/other",
                "revision": "other-r9",
                "content_hash": "3" * 64,
            }
        )
        result = call(
            {
                "operation": "impact",
                "artifact": self.packet,
                "current_source_refs": refs,
            }
        )
        self.assertEqual(result["status"], "current", result)
        self.assertEqual(result["impacted_requirement_ids"], [])

    def test_missing_current_sources_are_unknown(self) -> None:
        cases = {
            "omitted": {"operation": "impact", "artifact": self.packet},
            "null": {
                "operation": "impact",
                "artifact": self.packet,
                "current_source_refs": None,
            },
            "empty": {
                "operation": "impact",
                "artifact": self.packet,
                "current_source_refs": [],
            },
            "not_list": {
                "operation": "impact",
                "artifact": self.packet,
                "current_source_refs": {},
            },
        }
        for label, request in cases.items():
            with self.subTest(label=label):
                result = call(request)
                self.assertTrue(result["valid"])
                self.assertEqual(result["status"], "unknown")
                self.assertNotEqual(result["status"], "current")

    def test_conflicting_or_malformed_current_sources_are_unknown(self) -> None:
        refs = current_refs(self.packet)
        conflicting = refs + [
            {**refs[0], "revision": "spec-r9", "content_hash": "4" * 64}
        ]
        malformed = [{**refs[0], "extra": "x"}, refs[1]]
        for label, value in (("conflict", conflicting), ("malformed", malformed)):
            with self.subTest(label=label):
                result = call(
                    {
                        "operation": "impact",
                        "artifact": self.packet,
                        "current_source_refs": value,
                    }
                )
                self.assertNotEqual(result["status"], "current")
                self.assertEqual(result["status"], "unknown")

    def test_unacquired_source_is_unknown_even_with_matching_refs(self) -> None:
        packet = copy.deepcopy(self.packet)
        packet["sources"][0]["acquisition"] = "未取得"
        packet["sources"][0]["content_hash"] = None
        packet["sources"][0]["unacquired_reason"] = (
            "spec-analysis の取得手段が未接続（fixture）"
        )
        result = call(
            {
                "operation": "impact",
                "artifact": packet,
                "current_source_refs": current_refs(self.packet),
            }
        )
        self.assertEqual(result["status"], "unknown")
        self.assertEqual(result["impacted_requirement_ids"], ["QAR-001"])

    # ---- completion gating --------------------------------------------------

    def test_completion_fails_closed_without_current_sources(self) -> None:
        result = call({"operation": "completion_check", "artifact": self.packet})
        self.assertFalse(result["complete"])
        self.assertEqual(result["source_currentness"], "unknown")

    def test_each_non_approved_state_blocks_completion(self) -> None:
        for state in ("未承認", "失効", "未設定", "未取得", "unknown"):
            with self.subTest(state=state):
                packet = copy.deepcopy(self.packet)
                packet["approval"] = {
                    "state": state,
                    "not_required_reason": None,
                    "record": None,
                }
                result = call(
                    {
                        "operation": "completion_check",
                        "artifact": packet,
                        "current_source_refs": current_refs(packet),
                    }
                )
                self.assertFalse(result["complete"], result)
                self.assertNotEqual(result["status"], "complete")

    def test_approval_state_codes_are_reported(self) -> None:
        expected = {
            "未承認": "approval_not_approved",
            "失効": "approval_expired",
            "未設定": "approval_not_configured",
            "未取得": "approval_not_retrieved",
            "unknown": "approval_unknown",
        }
        for state, code in expected.items():
            with self.subTest(state=state):
                packet = copy.deepcopy(self.packet)
                packet["approval"] = {
                    "state": state,
                    "not_required_reason": None,
                    "record": None,
                }
                result = call(
                    {
                        "operation": "completion_check",
                        "artifact": packet,
                        "current_source_refs": current_refs(packet),
                    }
                )
                self.assertIn(code, codes(result))

    def test_approved_record_missing_or_approver_missing_is_refused(self) -> None:
        packet = approved(self.packet)
        packet["approval"]["record"] = None
        self.assertIn(
            "approval_record_missing",
            codes(call({"operation": "validate", "artifact": packet})),
        )

        for field, code in (
            ("approver", "approval_approver_missing"),
            ("role", "approval_role_missing"),
            ("evidence_ref", "approval_evidence_ref_missing"),
            ("expiry_condition", "approval_expiry_condition_missing"),
        ):
            with self.subTest(field=field):
                packet = approved(self.packet)
                packet["approval"]["record"][field] = ""
                result = call(
                    {
                        "operation": "completion_check",
                        "artifact": packet,
                        "current_source_refs": current_refs(packet),
                    }
                )
                self.assertFalse(result["complete"])
                self.assertIn(code, codes(result))

    def test_approval_from_old_revision_is_not_reused(self) -> None:
        packet = bump_revision(approved(self.packet), 2)
        packet["approval"]["record"]["revision"] = 1
        result = call(
            {
                "operation": "completion_check",
                "artifact": packet,
                "current_source_refs": current_refs(packet),
            }
        )
        self.assertFalse(result["complete"])
        self.assertIn("approval_revision_mismatch", codes(result))

    def test_approval_for_other_artifact_or_scope_is_not_reused(self) -> None:
        packet = approved(self.packet)
        packet["approval"]["record"]["artifact_ref"] = "fixture://requirements/other"
        result = call({"operation": "validate", "artifact": packet})
        self.assertIn("approval_artifact_ref_mismatch", codes(result))

        packet = approved(self.packet)
        packet["approval"]["record"]["scope"] = "another-scope"
        result = call({"operation": "validate", "artifact": packet})
        self.assertIn("approval_scope_mismatch", codes(result))

    def test_llm_text_cannot_stand_in_for_approval(self) -> None:
        packet = copy.deepcopy(self.packet)
        packet["status"] = "承認済み"
        packet["approval"] = {
            "state": "未承認",
            "not_required_reason": None,
            "record": None,
        }
        result = call({"operation": "validate", "artifact": packet})
        self.assertIn("status_approval_mismatch", codes(result))

    def test_unresolved_requirement_blocks_completion(self) -> None:
        packet = with_open_requirement(self.packet)
        validation = call({"operation": "validate", "artifact": packet})
        self.assertTrue(validation["valid"], validation)
        result = call(
            {
                "operation": "completion_check",
                "artifact": packet,
                "current_source_refs": current_refs(packet),
            }
        )
        self.assertFalse(result["complete"])
        self.assertIn("requirement_not_closed", codes(result))
        self.assertIn("open_items_remaining", codes(result))

    def test_approved_with_unresolved_requirement_is_refused(self) -> None:
        packet = approved(with_open_requirement(self.packet))
        result = call({"operation": "validate", "artifact": packet})
        self.assertFalse(result["valid"])
        self.assertIn("approved_with_unresolved_requirement", codes(result))

    def test_open_requirement_needs_exactly_one_open_item(self) -> None:
        packet = with_open_requirement(self.packet)
        packet["open_items"] = []
        self.assertIn(
            "open_item_missing",
            codes(call({"operation": "validate", "artifact": packet})),
        )

        packet = with_open_requirement(self.packet)
        packet["open_items"][0]["requirement_id"] = "QAR-001"
        self.assertIn(
            "open_item_requirement_mismatch",
            codes(call({"operation": "validate", "artifact": packet})),
        )

    def test_open_item_scope_must_include_requirement_scope(self) -> None:
        packet = with_open_requirement(self.packet)
        packet["open_items"][0]["impact_scope"] = ["another-scope"]
        self.assertIn(
            "open_item_scope_excludes_requirement",
            codes(call({"operation": "validate", "artifact": packet})),
        )

    def test_unacquired_source_blocks_completion(self) -> None:
        packet = copy.deepcopy(self.packet)
        packet["sources"][1]["acquisition"] = "取得不能"
        packet["sources"][1]["content_hash"] = None
        packet["sources"][1]["unacquired_reason"] = "取得手段が未選定（fixture）"
        result = call(
            {
                "operation": "completion_check",
                "artifact": packet,
                "current_source_refs": current_refs(self.packet),
            }
        )
        self.assertFalse(result["complete"])
        self.assertEqual(result["source_currentness"], "unknown")

    def test_unresolved_marker_in_approved_purpose_is_refused(self) -> None:
        packet = approved(self.packet)
        packet["purpose"]["success_conditions"] = ["主要経路の結果（未確定）"]
        result = call({"operation": "validate", "artifact": packet})
        self.assertIn("purpose_unresolved_value", codes(result))
        result = call(
            {
                "operation": "completion_check",
                "artifact": packet,
                "current_source_refs": current_refs(packet),
            }
        )
        self.assertFalse(result["complete"])

    # ---- structure and required fields --------------------------------------

    def test_missing_required_fields_are_refused(self) -> None:
        cases = {}
        packet = copy.deepcopy(self.packet)
        del packet["purpose"]
        cases["purpose_missing"] = packet
        packet = copy.deepcopy(self.packet)
        packet["purpose"]["quality_goals"] = []
        cases["quality_goals_empty"] = packet
        packet = copy.deepcopy(self.packet)
        packet["purpose"]["success_conditions"] = ["-"]
        cases["success_condition_placeholder"] = packet
        packet = copy.deepcopy(self.packet)
        packet["sources"] = []
        cases["sources_empty"] = packet
        packet = copy.deepcopy(self.packet)
        packet["owner"] = ""
        cases["owner_empty"] = packet
        packet = copy.deepcopy(self.packet)
        packet["requirements"][0]["statement"] = ""
        cases["statement_empty"] = packet
        for label, value in cases.items():
            with self.subTest(label=label):
                result = call({"operation": "validate", "artifact": value})
                self.assertEqual(result["status"], "blocked")
                self.assertFalse(result["valid"])

    def test_missing_requirement_fields_and_source_refs_are_refused(self) -> None:
        packet = copy.deepcopy(self.packet)
        packet["requirements"][0]["source_ref"] = "fixture://spec/missing"
        self.assertIn(
            "requirement_source_missing",
            codes(call({"operation": "validate", "artifact": packet})),
        )
        packet = copy.deepcopy(self.packet)
        packet["requirements"][0]["source_revision"] = "spec-r2"
        self.assertIn(
            "requirement_source_revision_mismatch",
            codes(call({"operation": "validate", "artifact": packet})),
        )
        packet = copy.deepcopy(self.packet)
        packet["requirements"][0]["scope"] = "another-scope"
        self.assertIn(
            "requirement_scope_mismatch",
            codes(call({"operation": "validate", "artifact": packet})),
        )

    def test_invalid_requirement_id_and_duplicate_are_refused(self) -> None:
        packet = copy.deepcopy(self.packet)
        packet["requirements"][0]["requirement_id"] = "TR-001"
        self.assertIn(
            "requirement_id_invalid",
            codes(call({"operation": "validate", "artifact": packet})),
        )
        packet = copy.deepcopy(self.packet)
        packet["requirements"][1]["requirement_id"] = "QAR-001"
        self.assertIn(
            "duplicate_requirement_id",
            codes(call({"operation": "validate", "artifact": packet})),
        )

    def test_history_must_end_at_packet_revision(self) -> None:
        packet = copy.deepcopy(self.packet)
        packet["revision"] = 2
        self.assertIn(
            "history_revision_invalid",
            codes(call({"operation": "validate", "artifact": packet})),
        )

    def test_downstream_owner_must_not_be_self(self) -> None:
        packet = copy.deepcopy(self.packet)
        packet["downstream"][0]["owner"] = OWNER
        self.assertIn(
            "downstream_owner_is_self",
            codes(call({"operation": "validate", "artifact": packet})),
        )

    def test_revision_must_be_positive_integer(self) -> None:
        for value in (0, -1, "1", 1.5, True, None):
            with self.subTest(value=value):
                packet = copy.deepcopy(self.packet)
                packet["revision"] = value
                result = call({"operation": "validate", "artifact": packet})
                self.assertEqual(result["status"], "blocked")

    def test_unknown_packet_key_is_refused(self) -> None:
        packet = copy.deepcopy(self.packet)
        packet["currentness"] = "current"
        result = call({"operation": "validate", "artifact": packet})
        self.assertEqual(result["status"], "blocked")
        self.assertIn("packet_schema", codes(result))

    def test_unknown_request_key_and_operation_are_refused(self) -> None:
        result = call({"operation": "validate", "artifact": self.packet, "extra": 1})
        self.assertIn("request_schema", codes(result))
        result = call({"operation": "render", "artifact": self.packet})
        self.assertIn("operation_invalid", codes(result))
        result = call([{"operation": "validate"}])
        self.assertIn("request_invalid", codes(result))

    def test_invalid_json_inputs_fail_closed(self) -> None:
        cases = {
            "not_json": b"{",
            "raw_nul": json.dumps(
                {"operation": "validate", "artifact": self.packet}, ensure_ascii=False
            ).encode("utf-8")[:-1]
            + b"\x00}",
            "duplicate_key": b'{"operation":"validate","operation":"validate","artifact":{}}',
            "nan": b'{"operation":"validate","artifact":{"revision":NaN}}',
            "invalid_utf8": b'{"operation":"validate","artifact":"\xff"}',
        }
        for label, raw in cases.items():
            with self.subTest(label=label):
                result = call_raw(raw)
                self.assertEqual(result["status"], "blocked")
                self.assertFalse(result["valid"])

    def test_escaped_nul_inside_text_is_refused(self) -> None:
        packet = copy.deepcopy(self.packet)
        packet["purpose"]["qa_purpose"] = "目的\x00"
        result = call({"operation": "validate", "artifact": packet})
        self.assertEqual(result["status"], "blocked")
        self.assertIn("invalid_field", codes(result))

    def test_oversized_input_is_refused(self) -> None:
        raw = b" " * (MAX_INPUT_BYTES + 1)
        result = call_raw(raw)
        self.assertEqual(result["status"], "blocked")
        self.assertIn("limit_exceeded", codes(result))

    # ---- determinism and no side effects -----------------------------------

    def test_output_is_deterministic(self) -> None:
        request = {
            "operation": "completion_check",
            "artifact": self.packet,
            "current_source_refs": current_refs(self.packet),
        }
        raw = json.dumps(request, ensure_ascii=False).encode("utf-8")
        self.assertEqual(
            subprocess.run(
                [sys.executable, "-B", str(SCRIPT)],
                input=raw,
                capture_output=True,
                env=ENV,
                check=True,
            ).stdout,
            subprocess.run(
                [sys.executable, "-B", str(SCRIPT)],
                input=raw,
                capture_output=True,
                env=ENV,
                check=True,
            ).stdout,
        )

    def test_script_writes_no_files_and_imports_only_stdlib(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            before = sorted(str(p) for p in Path(temp).rglob("*"))
            completed = subprocess.run(
                [sys.executable, "-B", str(SCRIPT)],
                input=json.dumps(
                    {"operation": "validate", "artifact": self.packet}
                ).encode("utf-8"),
                capture_output=True,
                check=True,
                cwd=temp,
                env=ENV,
            )
            self.assertEqual(sorted(str(p) for p in Path(temp).rglob("*")), before)
            self.assertTrue(json.loads(completed.stdout)["valid"])

        tree = ast.parse(SCRIPT.read_text(encoding="utf-8"), filename=str(SCRIPT))
        allowed = {"__future__", "hashlib", "json", "re", "sys", "typing"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name.split(".", 1)[0] for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module.split(".", 1)[0]]
            else:
                continue
            for name in names:
                self.assertIn(name, allowed)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                self.assertNotIn(node.func.id, {"open", "eval", "exec", "compile"})


if __name__ == "__main__":
    unittest.main()
