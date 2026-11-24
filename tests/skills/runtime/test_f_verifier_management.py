"""Owner verifier contract for saved test-management plan packets.

Every case runs ``skills/test-management/scripts/management_runtime.py`` as a
subprocess over JSON stdin/stdout, from an isolated copy of the skill package.
"""

from __future__ import annotations

import ast
import copy
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SKILL = REPO_ROOT / "skills" / "test-management"
EXAMPLE = SKILL / "assets" / "plan-packet.example.json"
ALLOWED_IMPORTS = {"__future__", "hashlib", "json", "re", "sys", "typing"}
FORBIDDEN_CALLS = {"open", "eval", "exec", "compile", "__import__"}
MAX_INPUT = 8 * 1024 * 1024
UNCHANGED_EXAMPLE_COUNTS = {
    "planned_total": 4,
    "required_total": 4,
    "readback_missing": 0,
    "acquired": 3,
    "partial": 0,
    "not_acquired": 0,
    "unavailable": 0,
    "zero_confirmed": 1,
    "acquisition_unknown": 0,
    "executed": 3,
    "running": 0,
    "not_run": 0,
    "cancelled": 0,
    "execution_failed": 0,
    "result_unknown": 0,
    "not_applicable": 1,
    "pass": 2,
    "fail": 1,
    "undetermined": 0,
    "unjudged": 0,
}


class ManagementRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        cls.copied = Path(cls._tmp.name) / "skills" / "test-management"
        shutil.copytree(
            SKILL,
            cls.copied,
            ignore=shutil.ignore_patterns("__pycache__", "evals"),
        )
        cls.script = cls.copied / "scripts" / "management_runtime.py"
        cls.example = json.loads(EXAMPLE.read_text(encoding="utf-8"))

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def call_raw(self, raw: bytes) -> tuple[int, bytes, dict]:
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        completed = subprocess.run(
            [sys.executable, "-B", str(self.script)],
            input=raw,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=self.copied,
            env=env,
            check=False,
        )
        return completed.returncode, completed.stderr, json.loads(completed.stdout)

    def call(self, request: dict) -> dict:
        code, stderr, result = self.call_raw(
            json.dumps(request, ensure_ascii=False).encode("utf-8")
        )
        self.assertEqual(code, 0)
        self.assertEqual(stderr, b"")
        return result

    def packet(self) -> dict:
        return copy.deepcopy(self.example)

    def current_refs(self, packet: dict) -> list[dict]:
        return [
            {
                key: row[key]
                for key in (
                    "owner",
                    "scope",
                    "artifact_ref",
                    "revision",
                    "content_hash",
                )
            }
            for row in packet["planned_sources"]
        ]

    def readback_request(self, packet: dict, **overrides: object) -> dict:
        readback = {
            "owner": "test-management",
            "scope": packet["scope"],
            "artifact_ref": packet["artifact_ref"],
            "revision": packet["revision"],
            "content_hash": self.stored_hash(packet),
        }
        request = {
            "operation": "validate_readback",
            "candidate_artifact": packet,
            "readback": readback,
            "expected_revision": packet["revision"],
        }
        request.update(overrides)
        return request

    def stored_hash(self, packet: dict) -> str:
        import hashlib

        raw = json.dumps(
            packet,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    def refresh_monitoring(self, packet: dict) -> dict:
        counts = self.call({"operation": "build_snapshot", "artifact": packet})[
            "counts"
        ]
        packet["monitoring"]["counts"] = counts
        return packet

    def codes(self, result: dict) -> set[str]:
        return {issue["code"] for issue in result["issues"]}

    def completion(self, packet: dict) -> dict:
        return self.call({"operation": "completion_check", "artifact": packet})

    def readback_row(self, packet: dict, population_id: str) -> dict:
        return next(
            row for row in packet["readbacks"] if row["population_id"] == population_id
        )

    # Positive path.

    def test_valid_packet_validates_builds_and_completes(self) -> None:
        packet = self.packet()
        validated = self.call({"operation": "validate", "artifact": packet})
        self.assertEqual((validated["status"], validated["valid"]), ("valid", True))
        self.assertEqual(validated["counts"], UNCHANGED_EXAMPLE_COUNTS)
        built = self.call({"operation": "build_snapshot", "artifact": packet})
        self.assertIs(built["matches_stored"], True)
        self.assertEqual(built["counts"], UNCHANGED_EXAMPLE_COUNTS)
        completed = self.completion(packet)
        self.assertIs(completed["complete"], True)
        self.assertEqual(completed["status"], "complete")
        self.assertIsNone(completed["approval_authenticity"])

    def test_readback_matches_canonical_storage_hash(self) -> None:
        packet = self.packet()
        result = self.call(self.readback_request(packet))
        self.assertEqual(
            (result["status"], result["valid"]), ("readback_matches", True)
        )
        self.assertEqual(result["storage_content_sha256"], self.stored_hash(packet))
        self.assertEqual(
            result["provider_authenticity"], "not_established_by_this_validator"
        )

    def test_impact_is_current_when_every_planned_source_matches(self) -> None:
        packet = self.packet()
        result = self.call(
            {
                "operation": "impact",
                "artifact": packet,
                "current_source_refs": self.current_refs(packet),
            }
        )
        self.assertEqual((result["status"], result["valid"]), ("current", True))
        self.assertEqual(result["stale_source_ids"], [])

    # Tampering, revision and provider readback.

    def test_tampered_stored_content_fails_readback(self) -> None:
        packet = self.packet()
        request = self.readback_request(packet)
        self.readback_row(request["candidate_artifact"], "POP-001")["outcome"] = "FAIL"
        result = self.call(request)
        self.assertEqual((result["status"], result["valid"]), ("blocked", False))
        self.assertIn("readback_hash_mismatch", self.codes(result))

    def test_expected_revision_mismatch_none_empty_and_missing_are_refused(
        self,
    ) -> None:
        packet = self.packet()
        mismatch = self.call(
            self.readback_request(packet, expected_revision="tm-rev-9999")
        )
        self.assertEqual(mismatch["valid"], False)
        self.assertIn("readback_revision_mismatch", self.codes(mismatch))
        for value in (None, "", "   "):
            with self.subTest(expected_revision=value):
                code, _, result = self.call_raw(
                    json.dumps(
                        self.readback_request(packet, expected_revision=value)
                    ).encode()
                )
                self.assertEqual(code, 0)
                self.assertEqual(result["valid"], False)
                self.assertEqual(result["status"], "blocked")
        missing = self.readback_request(packet)
        del missing["expected_revision"]
        result = self.call(missing)
        self.assertEqual((result["valid"], result["status"]), (False, "blocked"))

    def test_readback_from_other_scope_artifact_or_owner_is_refused(self) -> None:
        packet = self.packet()
        cases = {
            "scope": {"scope": "scope:other-release"},
            "artifact_ref": {"artifact_ref": "tm-plan:other-project"},
            "owner": {"owner": "test-reporting"},
        }
        for name, change in cases.items():
            with self.subTest(field=name):
                request = self.readback_request(packet)
                request["readback"].update(change)
                result = self.call(request)
                self.assertEqual(
                    (result["valid"], result["status"]), (False, "blocked")
                )
                self.assertIn("readback_identity_mismatch", self.codes(result))

    def test_artifact_from_another_project_is_not_accepted_with_this_readback(
        self,
    ) -> None:
        packet = self.packet()
        other = copy.deepcopy(packet)
        other["artifact_ref"] = "tm-plan:other-project"
        other["scope"] = "scope:other-project"
        other["history"][0]["scope"] = "scope:other-project"
        request = self.readback_request(packet)
        request["candidate_artifact"] = other
        result = self.call(request)
        self.assertEqual((result["valid"], result["status"]), (False, "blocked"))
        self.assertIn("readback_identity_mismatch", self.codes(result))

    # Currentness of the planned inventory.

    def test_source_change_marks_only_its_populations_and_plans(self) -> None:
        packet = self.packet()
        refs = self.current_refs(packet)
        for ref in refs:
            if ref["artifact_ref"] == "e2e-selection-release-2026-11":
                ref["revision"] = "sel-rev-2"
                ref["content_hash"] = "9" * 64
        result = self.call(
            {"operation": "impact", "artifact": packet, "current_source_refs": refs}
        )
        self.assertEqual((result["status"], result["valid"]), ("incomplete", True))
        self.assertEqual(result["stale_source_ids"], ["SRC-004"])
        self.assertEqual(result["impacted_population_ids"], ["POP-004"])
        self.assertEqual(
            result["unaffected_population_ids"], ["POP-001", "POP-002", "POP-003"]
        )
        self.assertEqual(result["impacted_plan_ids"], ["PLAN-002"])
        self.assertEqual(result["unaffected_plan_ids"], ["PLAN-001"])

    def test_unrelated_source_change_keeps_plan_current(self) -> None:
        packet = self.packet()
        refs = self.current_refs(packet)
        refs.append(
            {
                "owner": "test-defect-management",
                "scope": "scope:unrelated",
                "artifact_ref": "defect-set-unrelated",
                "revision": "d-rev-7",
                "content_hash": "e" * 64,
            }
        )
        result = self.call(
            {"operation": "impact", "artifact": packet, "current_source_refs": refs}
        )
        self.assertEqual((result["status"], result["valid"]), ("current", True))

    def test_unavailable_source_evidence_is_unknown_not_current(self) -> None:
        packet = self.packet()
        cases = [[], None, "bad", [{"owner": "test-case-design"}]]
        for refs in cases:
            with self.subTest(refs=refs):
                result = self.call(
                    {
                        "operation": "impact",
                        "artifact": packet,
                        "current_source_refs": refs,
                    }
                )
                self.assertEqual(
                    (result["status"], result["valid"]), ("incomplete", True)
                )
                self.assertEqual(
                    result["unknown_source_ids"],
                    ["SRC-001", "SRC-002", "SRC-003", "SRC-004"],
                )
        without_key = {"operation": "impact", "artifact": packet}
        code, _, result = self.call_raw(json.dumps(without_key).encode())
        self.assertEqual(result["valid"], False)

    # Acquisition, execution and count rules.

    def test_missing_source_cannot_become_zero_confirmed(self) -> None:
        packet = self.packet()
        row = self.readback_row(packet, "POP-003")
        row.update(
            acquisition_state="未取得",
            execution_state="対象なし",
            outcome="-",
            currentness="unknown",
            actual=None,
            readback_ref=None,
            zero_check=None,
            reason="source owner読戻し不能",
        )
        result = self.call({"operation": "validate", "artifact": packet})
        self.assertEqual(result["valid"], False)
        self.assertIn("unacquired_state_invalid", self.codes(result))

        packet = self.packet()
        row = self.readback_row(packet, "POP-003")
        row["zero_check"] = None
        result = self.call({"operation": "validate", "artifact": packet})
        self.assertIn("zero_check_required", self.codes(result))

        packet = self.packet()
        self.readback_row(packet, "POP-003")["zero_check"]["query"] = "suite:other"
        result = self.call({"operation": "validate", "artifact": packet})
        self.assertIn("readback_identity_mismatch", self.codes(result))

    def test_unacquired_row_cannot_carry_identity(self) -> None:
        packet = self.packet()
        row = self.readback_row(packet, "POP-002")
        row.update(
            acquisition_state="取得不能",
            execution_state="結果不明",
            outcome="-",
            currentness="unknown",
            reason="取得先が応答しない",
        )
        result = self.call({"operation": "validate", "artifact": packet})
        self.assertIn("unacquired_identity_present", self.codes(result))

    def test_partial_and_unknown_acquisition_block_completion(self) -> None:
        for state in ("部分取得", "不明"):
            with self.subTest(state=state):
                packet = self.packet()
                row = self.readback_row(packet, "POP-001")
                if state == "部分取得":
                    row["acquisition_state"] = "部分取得"
                    row["actual"]["range"] = "suite:login-part"
                    row["reason"] = "一部ページのみ取得"
                else:
                    row.update(
                        acquisition_state="不明",
                        execution_state="結果不明",
                        outcome="-",
                        currentness="unknown",
                        actual=None,
                        readback_ref=None,
                        reason="取得結果が不明",
                    )
                self.refresh_monitoring(packet)
                result = self.completion(packet)
                self.assertIsNot(result.get("complete"), True)
                self.assertIn("acquisition_incomplete", result["open"])
                self.assertEqual(result["open"]["acquisition_incomplete"], ["POP-001"])

    def test_non_final_execution_blocks_completion(self) -> None:
        states = {
            "結果不明": ("結果不明", "-", "結果が確定できない"),
            "実行失敗": ("実行失敗", "判定不能", "runner起動失敗"),
            "未実行": ("未実行", "-", None),
            "実行中": ("実行中", "-", None),
            "取消": ("取消", "-", "計画外で中止"),
            "判定不能": ("実行済み", "判定不能", "期待値を決定できない"),
            "未判定": ("実行済み", "未判定", None),
        }
        for label, (execution, outcome, reason) in states.items():
            with self.subTest(state=label):
                packet = self.packet()
                row = self.readback_row(packet, "POP-001")
                row.update(execution_state=execution, outcome=outcome, reason=reason)
                self.refresh_monitoring(packet)
                result = self.completion(packet)
                self.assertIsNot(result.get("complete"), True)
                self.assertIn("execution_unconfirmed", result["open"])

    def test_stale_or_unknown_readback_blocks_completion(self) -> None:
        packet = self.packet()
        self.readback_row(packet, "POP-002")["currentness"] = "stale"
        result = self.completion(packet)
        self.assertIsNot(result.get("complete"), True)
        self.assertEqual(result["open"]["readback_not_current"], ["POP-002"])

    def test_missing_readback_is_not_filled_as_zero_or_not_run(self) -> None:
        packet = self.packet()
        packet["readbacks"] = [
            row for row in packet["readbacks"] if row["population_id"] != "POP-004"
        ]
        self.refresh_monitoring(packet)
        validated = self.call({"operation": "validate", "artifact": packet})
        self.assertEqual(validated["valid"], True)
        self.assertEqual(validated["counts"]["readback_missing"], 1)
        self.assertEqual(validated["counts"]["zero_confirmed"], 1)
        self.assertEqual(validated["counts"]["not_applicable"], 1)
        self.assertIn("readback_missing", self.codes(validated))
        self.refresh_monitoring(packet)
        result = self.completion(packet)
        self.assertIsNot(result.get("complete"), True)
        self.assertEqual(result["open"]["readback_missing"], ["POP-004"])

    def test_optional_population_open_does_not_block_completion(self) -> None:
        packet = self.packet()
        packet["planned_populations"][3]["required"] = False
        packet["readbacks"] = [
            row for row in packet["readbacks"] if row["population_id"] != "POP-004"
        ]
        self.refresh_monitoring(packet)
        result = self.completion(packet)
        self.assertIs(result["complete"], True)

    def test_declared_denominator_mismatch_is_refused(self) -> None:
        packet = self.packet()
        packet["monitoring"]["counts"]["planned_total"] = 5
        validated = self.call({"operation": "validate", "artifact": packet})
        self.assertEqual(validated["valid"], False)
        self.assertIn("monitoring_mismatch", self.codes(validated))
        built = self.call({"operation": "build_snapshot", "artifact": packet})
        self.assertIs(built["matches_stored"], False)
        self.assertEqual(built["mismatched_count_keys"], ["planned_total"])
        completed = self.completion(packet)
        self.assertIsNot(completed.get("complete"), True)
        self.assertEqual(completed["status"], "blocked")

    def test_orphan_and_duplicate_readbacks_are_refused(self) -> None:
        packet = self.packet()
        packet["readbacks"].append(copy.deepcopy(packet["readbacks"][0]))
        self.assertIn(
            "readback_duplicate",
            self.codes(self.call({"operation": "validate", "artifact": packet})),
        )
        packet = self.packet()
        orphan = copy.deepcopy(packet["readbacks"][0])
        orphan["population_id"] = "POP-999"
        packet["readbacks"].append(orphan)
        self.assertIn(
            "readback_orphan",
            self.codes(self.call({"operation": "validate", "artifact": packet})),
        )

    def test_plan_identity_mismatch_is_refused(self) -> None:
        packet = self.packet()
        self.readback_row(packet, "POP-001")["actual"]["build"] = "build-2026.11.01"
        result = self.call({"operation": "validate", "artifact": packet})
        self.assertEqual(result["valid"], False)
        self.assertIn("readback_identity_mismatch", self.codes(result))

    # Risk, corrective action, criteria and approval.

    def test_unresolved_project_risk_and_action_block_completion(self) -> None:
        packet = self.packet()
        packet["project_risks"][0]["state"] = "対応中"
        packet["project_risks"][0]["state_evidence_ref"] = None
        result = self.completion(packet)
        self.assertEqual(result["open"]["project_risk_open"], ["PROJ-RISK-001"])
        packet = self.packet()
        packet["corrective_actions"][0]["state"] = "対応中"
        packet["corrective_actions"][0]["result_ref"] = None
        result = self.completion(packet)
        self.assertEqual(result["open"]["corrective_action_open"], ["CA-001"])

    def test_resolved_risk_requires_processing_evidence(self) -> None:
        packet = self.packet()
        packet["project_risks"][0]["state_evidence_ref"] = None
        result = self.call({"operation": "validate", "artifact": packet})
        self.assertEqual(result["valid"], False)
        self.assertEqual(result["status"], "blocked")
        self.assertIn("state_evidence_required", self.codes(result))

    def test_unmet_or_unjudged_start_and_end_criteria_block_completion(self) -> None:
        for index, criterion_id in ((0, "CRIT-001"), (1, "CRIT-002")):
            for judgment in ("未達", "評価不能"):
                with self.subTest(criterion=criterion_id, judgment=judgment):
                    packet = self.packet()
                    packet["criteria"][index]["judgment"] = judgment
                    if judgment == "評価不能":
                        packet["criteria"][index]["evidence_ref"] = None
                    result = self.completion(packet)
                    self.assertIsNot(result.get("complete"), True)
                    self.assertEqual(result["open"]["criteria_unmet"], [criterion_id])

    def test_approval_states_block_completion_when_not_effective(self) -> None:
        packet = self.packet()
        packet["approval"] = {"state": "未承認", "record": None}
        result = self.completion(packet)
        self.assertIsNot(result.get("complete"), True)
        self.assertIn("approval_not_effective", result["open"])
        packet["approval"] = {"state": "失効", "record": None}
        self.assertIsNot(self.completion(packet).get("complete"), True)

    def approved_packet(self) -> dict:
        packet = self.packet()
        packet["approval"] = {
            "state": "承認済み",
            "record": {
                "artifact_ref": packet["artifact_ref"],
                "scope": packet["scope"],
                "revision": packet["revision"],
                "approver": "QA責任者 A",
                "role": "test-manager",
                "evidence_ref": "approval:tm-rev-0001",
            },
        }
        return packet

    def test_bound_approval_completes_with_authenticity_marker(self) -> None:
        packet = self.approved_packet()
        result = self.completion(packet)
        self.assertIs(result["complete"], True)
        self.assertEqual(
            result["approval_authenticity"], "not_established_by_this_validator"
        )

    def test_approval_for_previous_revision_or_other_scope_is_refused(self) -> None:
        for field, value in (
            ("revision", "tm-rev-0000"),
            ("scope", "scope:other-release"),
            ("artifact_ref", "tm-plan:other-project"),
        ):
            with self.subTest(field=field):
                packet = self.approved_packet()
                packet["approval"]["record"][field] = value
                result = self.completion(packet)
                self.assertIsNot(result.get("complete"), True)
                self.assertEqual(result["status"], "blocked")
                self.assertIn("approval_binding_mismatch", self.codes(result))

    def test_approval_without_approver_or_with_placeholder_is_refused(self) -> None:
        for field, value in (
            ("approver", None),
            ("approver", "未設定"),
            ("evidence_ref", "unknown"),
        ):
            with self.subTest(field=field, value=value):
                packet = self.approved_packet()
                packet["approval"]["record"][field] = value
                result = self.completion(packet)
                self.assertIsNot(result.get("complete"), True)
                self.assertEqual(result["status"], "blocked")

    def test_approval_record_on_non_approved_state_is_refused(self) -> None:
        packet = self.approved_packet()
        packet["approval"]["state"] = "未承認"
        result = self.completion(packet)
        self.assertEqual(result["status"], "blocked")
        self.assertIn("approval_record_unexpected", self.codes(result))

    # Structure: required fields, history and unknown keys.

    def test_missing_or_extra_fields_are_refused(self) -> None:
        packet = self.packet()
        del packet["target"]
        self.assertIn(
            "field_set_invalid",
            self.codes(self.call({"operation": "validate", "artifact": packet})),
        )
        packet = self.packet()
        packet["extra"] = True
        self.assertIn(
            "field_set_invalid",
            self.codes(self.call({"operation": "validate", "artifact": packet})),
        )
        packet = self.packet()
        del packet["planned_populations"][0]["query_range"]
        self.assertIn(
            "field_set_invalid",
            self.codes(self.call({"operation": "validate", "artifact": packet})),
        )

    def test_history_chain_must_end_at_current_revision(self) -> None:
        packet = self.packet()
        packet["history"].append(
            {
                "revision": "tm-rev-0002",
                "replaces_revision": "tm-rev-0001",
                "reason": "改版",
                "scope": packet["scope"],
            }
        )
        result = self.call({"operation": "validate", "artifact": packet})
        self.assertIn("history_current_missing", self.codes(result))

    def test_wrong_schema_owner_or_operation_is_refused(self) -> None:
        packet = self.packet()
        packet["schema"] = "test-management-plan-v0"
        self.assertIn(
            "schema_invalid",
            self.codes(self.call({"operation": "validate", "artifact": packet})),
        )
        packet = self.packet()
        packet["owner"] = "test-reporting"
        self.assertIn(
            "owner_invalid",
            self.codes(self.call({"operation": "validate", "artifact": packet})),
        )
        result = self.call({"operation": "approve", "artifact": self.packet()})
        self.assertIn("operation_invalid", self.codes(result))

    # Raw input handling.

    def test_malformed_raw_input_fails_closed(self) -> None:
        packet = json.dumps(
            {"operation": "validate", "artifact": self.packet()}
        ).encode("utf-8")
        cases = {
            "not_json": b"{not json",
            "raw_nul": packet[:-1] + b"\x00}",
            "duplicate_key": b'{"operation":"validate","operation":"validate","artifact":{}}',
            "nan_constant": b'{"operation":"validate","artifact":{"x":NaN}}',
            "oversize": b'{"operation":"validate","pad":"'
            + b"a" * (MAX_INPUT + 1)
            + b'"}',
        }
        for name, raw in cases.items():
            with self.subTest(case=name):
                code, stderr, result = self.call_raw(raw)
                self.assertEqual(code, 0)
                self.assertEqual(stderr, b"")
                self.assertEqual(
                    (result["valid"], result["status"]), (False, "blocked")
                )

    def test_escaped_nul_inside_packet_text_is_refused(self) -> None:
        packet = self.packet()
        packet["scope"] = "scope:a\x00b"
        result = self.call({"operation": "validate", "artifact": packet})
        self.assertEqual((result["valid"], result["status"]), (False, "blocked"))

    def test_unknown_request_key_is_refused(self) -> None:
        result = self.call(
            {"operation": "validate", "artifact": self.packet(), "approve": True}
        )
        self.assertIn("request_schema", self.codes(result))

    # Script isolation.

    def test_script_uses_stdlib_only_and_does_not_write_or_call_out(self) -> None:
        tree = ast.parse(
            self.script.read_text(encoding="utf-8"), filename=str(self.script)
        )
        imported: set[str] = set()
        called: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".", 1)[0])
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                called.add(node.func.id)
        self.assertLessEqual(imported, ALLOWED_IMPORTS)
        self.assertFalse(called & FORBIDDEN_CALLS)

    def test_run_leaves_no_files_behind(self) -> None:
        before = sorted(
            str(path.relative_to(self.copied)) for path in self.copied.rglob("*")
        )
        self.call({"operation": "validate", "artifact": self.packet()})
        after = sorted(
            str(path.relative_to(self.copied)) for path in self.copied.rglob("*")
        )
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
