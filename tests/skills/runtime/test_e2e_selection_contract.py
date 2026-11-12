from __future__ import annotations

import copy
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = (
    REPO_ROOT / "skills" / "e2e-test-selection" / "scripts" / "selection_contract.py"
)
SPEC = importlib.util.spec_from_file_location("e2e_selection_contract", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
contract = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(contract)


def selection() -> dict:
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


def history_snapshot(value: dict | None = None) -> dict:
    packet = selection() if value is None else value
    return {
        "scope_refs": list(packet["scope_refs"]),
        "automation_goal": packet["automation_goal"],
        "population_complete": packet["population_complete"],
        "source_refs": copy.deepcopy(packet["source_refs"]),
        "candidates": [copy.deepcopy(row) for row in packet["candidates"]],
        "blockers": list(packet["blockers"]),
    }


def history_row(
    value: dict,
    revision: int,
    change_reason: str,
    retired_candidates: list[dict] | None = None,
) -> dict:
    retired = copy.deepcopy(retired_candidates or [])
    snapshot = history_snapshot(value)
    candidate_ids = [
        {
            "candidate_id": row["candidate_id"],
            "candidate_key": row["candidate_key"],
        }
        for row in value["candidates"]
    ]
    revision_digest = contract._revision_digest(
        value["selection_ref"],
        revision,
        change_reason,
        candidate_ids,
        retired,
        contract._selection_snapshot(snapshot, "test selection snapshot"),
    )
    return {
        "revision": revision,
        "candidate_ids": candidate_ids,
        "change_reason": change_reason,
        "retired_candidates": retired,
        "selection_snapshot": snapshot,
        "revision_digest": revision_digest,
    }


def run_cli_bytes(raw: bytes) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        [sys.executable, str(SCRIPT)],
        input=raw,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=REPO_ROOT,
        check=False,
    )


class E2ESelectionContractTests(unittest.TestCase):
    def test_ready_requires_complete_current_sources_and_closed_candidates(
        self,
    ) -> None:
        result = contract.validate(selection())
        self.assertEqual(result["selection_status"], "ready")
        self.assertEqual(result["selected_candidate_ids"], ["E2E-CAND-001"])

    def test_unknown_source_cannot_become_ready(self) -> None:
        value = selection()
        value["source_refs"][1]["currentness"] = "unknown"
        result = contract.validate(value)
        self.assertEqual(result["selection_status"], "unresolved")
        self.assertEqual(result["unresolved_source_refs"], ["TI-001"])

    def test_stale_source_only_invalidates_candidates_that_depend_on_it(self) -> None:
        value = selection()
        value["scope_refs"] = ["SPEC-001"]
        value["source_refs"][1]["currentness"] = "stale"
        value["candidates"][0]["source_refs"] = ["SPEC-001"]
        value["candidates"][1]["source_refs"] = ["TI-001"]
        value["candidates"][1]["decision"] = "selected"
        result = contract.validate(value)
        self.assertEqual(result["selection_status"], "unresolved")
        self.assertEqual(result["selected_candidate_ids"], ["E2E-CAND-001"])
        self.assertEqual(result["unresolved_candidate_ids"], ["E2E-CAND-002"])

    def test_incomplete_population_with_blocker_remains_blocked(self) -> None:
        value = selection()
        value["population_complete"] = False
        value["blockers"] = ["ownerから全item一覧を取得する"]
        result = contract.validate(value)
        self.assertEqual(result["selection_status"], "blocked")

    def test_empty_incomplete_population_with_blocker_is_recordable(self) -> None:
        value = selection()
        value["population_complete"] = False
        value["candidates"] = []
        value["blockers"] = ["候補母集団を確定する仕様情報が不足"]

        result = contract.validate(value)

        self.assertTrue(result["valid"])
        self.assertEqual(result["selection_status"], "blocked")
        self.assertEqual(result["candidate_count"], 0)
        self.assertEqual(result["selected_candidate_ids"], [])
        self.assertEqual(result["selection_record"]["blockers"], value["blockers"])

        completed = run_cli_bytes(
            json.dumps({"input": value}, ensure_ascii=False).encode("utf-8")
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stderr, b"")
        envelope = json.loads(completed.stdout)
        self.assertEqual(envelope["runtime_status"], "ok")
        self.assertEqual(envelope["result_status"], "blocked")
        self.assertEqual(envelope["payload"]["candidate_count"], 0)

    def test_empty_population_without_blocker_is_rejected(self) -> None:
        value = selection()
        value["population_complete"] = False
        value["candidates"] = []
        value["blockers"] = []

        with self.assertRaises(contract.ContractError):
            contract.validate(value)

    def test_complete_empty_population_is_not_ready(self) -> None:
        value = selection()
        value["candidates"] = []
        value["blockers"] = []

        with self.assertRaises(contract.ContractError):
            contract.validate(value)

    def test_empty_population_snapshot_is_retained_when_candidates_are_added(
        self,
    ) -> None:
        first = selection()
        first["population_complete"] = False
        first["candidates"] = []
        first["blockers"] = ["候補母集団を確定する仕様情報が不足"]
        first_result = contract.validate(first)

        second = selection()
        second["revision"] = 2
        second["change_reason"] = "source追加後に候補母集団を確定"
        second["history"] = [history_row(first, 1, first["change_reason"])]
        result = contract.validate(second)

        self.assertEqual(result["selection_status"], "ready")
        self.assertTrue(result["history_complete"])
        self.assertEqual(result["selected_candidate_ids"], ["E2E-CAND-001"])
        self.assertEqual(
            result["selection_record"]["history"][0]["revision_digest"],
            first_result["current_revision_digest"],
        )
        snapshot = result["selection_record"]["history"][0]["selection_snapshot"]
        self.assertEqual(snapshot["candidates"], [])
        self.assertFalse(snapshot["population_complete"])
        self.assertEqual(snapshot["blockers"], first["blockers"])

    def test_historical_incomplete_population_with_candidates_requires_blocker(
        self,
    ) -> None:
        prior = selection()
        snapshot = history_snapshot(prior)
        snapshot["population_complete"] = False
        snapshot["blockers"] = []
        candidate_ids = [
            {
                "candidate_id": row["candidate_id"],
                "candidate_key": row["candidate_key"],
            }
            for row in prior["candidates"]
        ]
        historical = {
            "revision": 1,
            "candidate_ids": candidate_ids,
            "change_reason": prior["change_reason"],
            "retired_candidates": [],
            "selection_snapshot": snapshot,
            "revision_digest": contract._revision_digest(
                prior["selection_ref"],
                1,
                prior["change_reason"],
                candidate_ids,
                [],
                snapshot,
            ),
        }
        current = selection()
        current["revision"] = 2
        current["change_reason"] = "候補母集団の再確認"
        current["history"] = [historical]

        with self.assertRaisesRegex(contract.ContractError, "blockerまたは再開条件"):
            contract.validate(current)

    def test_historical_incomplete_population_with_candidates_accepts_blocker(
        self,
    ) -> None:
        prior = selection()
        prior["population_complete"] = False
        prior["blockers"] = ["候補母集団の残りをownerへ確認する"]
        historical = history_row(prior, 1, prior["change_reason"])
        current = selection()
        current["revision"] = 2
        current["change_reason"] = "候補母集団の確認を継続"
        current["history"] = [historical]

        result = contract.validate(current)

        self.assertTrue(result["history_complete"])
        self.assertEqual(
            result["selection_record"]["history"][0]["selection_snapshot"]["blockers"],
            prior["blockers"],
        )

    def test_revision_history_preserves_candidate_id_and_key(self) -> None:
        value = selection()
        value["revision"] = 2
        prior_revision = selection()
        prior_result = contract.validate(prior_revision)
        prior_history = history_row(prior_revision, 1, "初回のE2E自動化価値判断")
        self.assertEqual(
            prior_history["revision_digest"],
            prior_result["current_revision_digest"],
        )
        value["history"] = [prior_history]
        value["candidates"].append(
            {
                "candidate_id": "E2E-CAND-003",
                "candidate_key": "receipt-view",
                "source_refs": ["SPEC-001", "TI-001"],
                "decision": "deferred",
                "rationale": "個別の利用頻度が未確認",
            }
        )
        result = contract.validate(value)
        self.assertEqual(result["selection_status"], "unresolved")
        self.assertEqual(
            result["selection_record"]["history"][0]["candidate_ids"][0][
                "candidate_id"
            ],
            "E2E-CAND-001",
        )
        self.assertTrue(result["history_complete"])

    def test_candidate_id_cannot_be_reassigned_to_new_key(self) -> None:
        value = selection()
        value["revision"] = 2
        value["history"] = [history_row(selection(), 1, "rename attempt")]
        value["candidates"][0]["candidate_key"] = "different-candidate"
        with self.assertRaises(contract.ContractError):
            contract.validate(value)

    def test_removed_candidate_requires_explicit_retirement_reason(self) -> None:
        value = selection()
        value["revision"] = 2
        value["history"] = [history_row(selection(), 1, "candidate population review")]
        value["candidates"] = value["candidates"][:1]
        with self.assertRaises(contract.ContractError):
            contract.validate(value)
        value["retired_candidates"] = [
            {
                "candidate_id": "E2E-CAND-002",
                "reason": "current source confirms duplicate path",
            }
        ]
        result = contract.validate(value)
        self.assertEqual(result["selection_status"], "ready")
        self.assertTrue(result["history_complete"])

    def test_retired_candidate_cannot_be_reintroduced_after_a_later_revision(
        self,
    ) -> None:
        value = selection()
        value["revision"] = 3
        rev1 = selection()
        rev2 = selection()
        rev2["candidates"] = rev2["candidates"][:1]
        retirement = [
            {
                "candidate_id": "E2E-CAND-002",
                "reason": "currentな既存E2Eと重複するためretire",
            }
        ]
        value["history"] = [
            history_row(rev1, 1, "初回選定"),
            history_row(rev2, 2, "既存E2Eとの重複を確認", retirement),
        ]
        with self.assertRaises(contract.ContractError):
            contract.validate(value)

    def test_revision_snapshots_restore_decisions_rationales_sources_and_retirement(
        self,
    ) -> None:
        revision_one = selection()
        revision_two = copy.deepcopy(revision_one)
        revision_two["revision"] = 2
        revision_two["change_reason"] = "SPEC改版で選定価値を再評価"
        revision_two["source_refs"][0]["revision"] = "s9"
        revision_two["candidates"] = revision_two["candidates"][:1]
        revision_two["candidates"][0].update(
            {
                "decision": "not_selected",
                "rationale": "改訂仕様ではcurrentな既存E2Eによる確認が優先される",
            }
        )
        retirement = {
            "candidate_id": "E2E-CAND-002",
            "reason": "currentな既存E2Eと重複するためretire",
        }
        revision_two["retired_candidates"] = [retirement]

        revision_three = copy.deepcopy(revision_two)
        revision_three["revision"] = 3
        revision_three["change_reason"] = "SPEC再改版でcheckout価値を再選定"
        revision_three["source_refs"][0]["revision"] = "s10"
        revision_three["candidates"][0].update(
            {
                "decision": "selected",
                "rationale": "checkoutが高リスク経路となり反復確認が必要",
            }
        )
        revision_three["history"] = [
            history_row(revision_one, 1, revision_one["change_reason"]),
            history_row(revision_two, 2, revision_two["change_reason"], [retirement]),
        ]

        result = contract.validate(revision_three)
        self.assertEqual(result["selection_status"], "ready")
        self.assertTrue(result["history_complete"])
        history = result["selection_record"]["history"]
        first_snapshot = history[0]["selection_snapshot"]
        second_snapshot = history[1]["selection_snapshot"]
        self.assertEqual(first_snapshot["candidates"][0]["decision"], "selected")
        self.assertEqual(first_snapshot["source_refs"][0]["revision"], "s8")
        self.assertEqual(second_snapshot["candidates"][0]["decision"], "not_selected")
        self.assertEqual(
            second_snapshot["candidates"][0]["rationale"],
            "改訂仕様ではcurrentな既存E2Eによる確認が優先される",
        )
        self.assertEqual(second_snapshot["source_refs"][0]["revision"], "s9")
        self.assertEqual(
            history[1]["retired_candidates"][0]["reason"], retirement["reason"]
        )

    def test_legacy_history_remains_readable_but_is_blocked_without_snapshots(
        self,
    ) -> None:
        value = selection()
        value["revision"] = 2
        value["history"] = [
            {
                "revision": 1,
                "candidate_ids": [
                    {
                        "candidate_id": "E2E-CAND-001",
                        "candidate_key": "checkout-primary",
                    },
                    {"candidate_id": "E2E-CAND-002", "candidate_key": "non-payment"},
                ],
                "change_reason": "legacy row without decision and source snapshots",
                "retired_candidates": [],
            }
        ]
        result = contract.validate(value)
        self.assertEqual(result["selection_status"], "blocked")
        self.assertFalse(result["history_complete"])
        self.assertEqual(result["unresolved_history_revisions"], [1])
        self.assertEqual(result["selection_record"]["history"][0]["revision"], 1)

    def test_missing_history_digest_blocks_the_record_without_guessing(self) -> None:
        value = selection()
        value["revision"] = 2
        history = history_row(selection(), 1, "spec update")
        history.pop("revision_digest")
        value["history"] = [history]

        result = contract.validate(value)

        self.assertEqual(result["selection_status"], "blocked")
        self.assertFalse(result["history_complete"])
        self.assertEqual(result["unresolved_history_revisions"], [1])
        self.assertNotIn("revision_digest", result["selection_record"]["history"][0])

    def test_history_snapshot_decision_rationale_and_source_revision_are_bound(
        self,
    ) -> None:
        mutations = {
            "decision": lambda snapshot: snapshot["candidates"][0].update(
                {"decision": "not_selected"}
            ),
            "rationale": lambda snapshot: snapshot["candidates"][0].update(
                {"rationale": "tampered rationale"}
            ),
            "source revision": lambda snapshot: snapshot["source_refs"][0].update(
                {"revision": "tampered-revision"}
            ),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name):
                value = selection()
                value["revision"] = 2
                value["history"] = [history_row(selection(), 1, "spec update")]
                mutate(value["history"][0]["selection_snapshot"])
                with self.assertRaisesRegex(contract.ContractError, "改変されています"):
                    contract.validate(value)

    def test_history_cannot_drop_a_previously_recorded_retirement(self) -> None:
        value = selection()
        value["revision"] = 3
        value["candidates"] = value["candidates"][:1]
        value["retired_candidates"] = [
            {
                "candidate_id": "E2E-CAND-002",
                "reason": "currentな既存E2Eと重複するためretire",
            }
        ]
        rev1 = selection()
        rev2 = selection()
        rev2["candidates"] = rev2["candidates"][:1]
        value["history"] = [
            history_row(rev1, 1, "初回選定"),
            history_row(rev2, 2, "既存E2Eとの重複を確認"),
        ]
        with self.assertRaises(contract.ContractError):
            contract.validate(value)

    def test_history_cannot_change_a_recorded_retirement_reason(self) -> None:
        revision_one = selection()
        revision_two = copy.deepcopy(revision_one)
        revision_two["revision"] = 2
        revision_two["candidates"] = revision_two["candidates"][:1]
        retirement = {
            "candidate_id": "E2E-CAND-002",
            "reason": "currentな既存E2Eと重複するためretire",
        }
        revision_two["retired_candidates"] = [retirement]
        current = copy.deepcopy(revision_two)
        current["revision"] = 3
        current["retired_candidates"] = [
            {**retirement, "reason": "retirement reason changed"}
        ]
        current["history"] = [
            history_row(revision_one, 1, "初回選定"),
            history_row(revision_two, 2, "重複が確認された", [retirement]),
        ]

        with self.assertRaises(contract.ContractError):
            contract.validate(current)

    def test_zero_or_missing_source_rows_are_rejected(self) -> None:
        value = selection()
        value["source_refs"] = []
        with self.assertRaises(contract.ContractError):
            contract.validate(value)

    def test_scope_requires_a_known_source_and_candidate_keys_are_unique(self) -> None:
        unknown_scope = selection()
        unknown_scope["scope_refs"] = ["TI-999"]
        with self.assertRaises(contract.ContractError):
            contract.validate(unknown_scope)

        duplicate_key = selection()
        duplicate_key["candidates"][1]["candidate_key"] = "checkout-primary"
        with self.assertRaises(contract.ContractError):
            contract.validate(duplicate_key)

    def test_cli_emits_one_json_envelope_for_blocked_selection(self) -> None:
        value = selection()
        value["blockers"] = ["owner source is unavailable"]
        result = run_cli_bytes(json.dumps({"input": value}).encode())
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stderr, b"")
        self.assertEqual(json.loads(result.stdout)["result_status"], "blocked")

    def test_cli_rejects_duplicate_keys_with_structured_output(self) -> None:
        encoded = json.dumps(selection()).encode()
        encoded = encoded.replace(b'"revision": 1', b'"revision": 1, "revision": 1', 1)
        result = run_cli_bytes(b'{"input":' + encoded + b"}")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stderr, b"")
        envelope = json.loads(result.stdout)
        self.assertEqual(envelope["runtime_status"], "invalid_input")

    def test_cli_rejects_oversized_input_before_parsing(self) -> None:
        result = run_cli_bytes(b" " * (contract.MAX_INPUT_BYTES + 1))
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stderr, b"")
        self.assertEqual(json.loads(result.stdout)["runtime_status"], "limit_exceeded")

    def test_cli_enforces_shared_per_string_and_numeric_limits(self) -> None:
        large_string = selection()
        large_string["automation_goal"] = "x" * (contract.MAX_JSON_STRING_BYTES + 1)
        large_string_request = json.dumps({"input": large_string}).encode()
        oversized_integer = (
            json.dumps({"input": selection()})
            .encode()
            .replace(
                b'"revision": 1',
                b'"revision": ' + b"9" * (contract.MAX_JSON_NUMBER_CHARS + 1),
                1,
            )
        )
        oversized_expansion = (
            json.dumps({"input": selection()})
            .encode()
            .replace(b'"revision": 1', b'"revision": 1e4096', 1)
        )

        for raw in (
            large_string_request,
            oversized_integer,
            oversized_expansion,
        ):
            with self.subTest(input_bytes=len(raw)):
                result = run_cli_bytes(raw)
                self.assertEqual(result.returncode, 0)
                self.assertEqual(result.stderr, b"")
                self.assertEqual(
                    json.loads(result.stdout)["runtime_status"], "limit_exceeded"
                )

    def test_cli_rejects_excessive_json_depth(self) -> None:
        raw = b'{"input":' + b"[" * 70 + b"null" + b"]" * 70 + b"}"
        result = run_cli_bytes(raw)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stderr, b"")
        self.assertEqual(json.loads(result.stdout)["runtime_status"], "limit_exceeded")

    def test_cli_handles_invalid_utf8_and_json_without_traceback(self) -> None:
        for raw in (b"\xff", b'{"input":'):
            with self.subTest(raw=raw):
                result = run_cli_bytes(raw)
                self.assertEqual(result.returncode, 0)
                self.assertEqual(result.stderr, b"")
                self.assertEqual(
                    json.loads(result.stdout)["runtime_status"], "invalid_input"
                )

    def test_cli_rejects_non_finite_number_and_unpaired_surrogate(self) -> None:
        non_finite = (
            json.dumps(selection())
            .encode()
            .replace(b'"revision": 1', b'"revision": NaN', 1)
        )
        surrogate_value = selection()
        surrogate_value["automation_goal"] = "\ud800"
        surrogate = json.dumps(surrogate_value).encode()
        for raw in (b'{"input":' + non_finite + b"}", b'{"input":' + surrogate + b"}"):
            with self.subTest(raw=raw[:80]):
                result = run_cli_bytes(raw)
                self.assertEqual(result.returncode, 0)
                self.assertEqual(result.stderr, b"")
                self.assertEqual(
                    json.loads(result.stdout)["runtime_status"], "invalid_input"
                )

    def test_cli_rejects_invalid_top_level_schema(self) -> None:
        result = run_cli_bytes(b'{"input":[]}')
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stderr, b"")
        envelope = json.loads(result.stdout)
        self.assertEqual(envelope["runtime_status"], "invalid_input")
        self.assertEqual(envelope["result_status"], "blocked")

    def test_cli_enforces_stdout_limit(self) -> None:
        previous = contract.MAX_OUTPUT_BYTES
        try:
            contract.MAX_OUTPUT_BYTES = 256
            output = contract._encode_output({"payload": "x" * 300})
        finally:
            contract.MAX_OUTPUT_BYTES = previous
        envelope = json.loads(output)
        self.assertEqual(envelope["runtime_status"], "limit_exceeded")
        self.assertLessEqual(len(output), 256)

    def test_runtime_runs_from_an_isolated_skill_copy(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            copied_skill = Path(temp_dir) / "e2e-test-selection"
            shutil.copytree(SCRIPT.parent.parent, copied_skill)
            copied_script = copied_skill / "scripts" / "selection_contract.py"
            result = subprocess.run(
                [sys.executable, str(copied_script)],
                input=json.dumps({"input": selection()}, ensure_ascii=False).encode(),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=copied_skill,
                check=False,
            )
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stderr, b"")
        envelope = json.loads(result.stdout)
        self.assertEqual(envelope["runtime_status"], "ok")
        self.assertEqual(envelope["result_status"], "ready")
        self.assertEqual(
            envelope["payload"]["selection_record"]["selection_ref"], "E2ESEL-001"
        )


if __name__ == "__main__":
    unittest.main()
