from __future__ import annotations

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

    def test_incomplete_population_with_blocker_remains_blocked(self) -> None:
        value = selection()
        value["population_complete"] = False
        value["blockers"] = ["ownerから全item一覧を取得する"]
        result = contract.validate(value)
        self.assertEqual(result["selection_status"], "blocked")

    def test_revision_history_preserves_candidate_id_and_key(self) -> None:
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
                "change_reason": "TI-001 source update",
                "retired_candidates": [],
            }
        ]
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

    def test_candidate_id_cannot_be_reassigned_to_new_key(self) -> None:
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
                "change_reason": "rename attempt",
                "retired_candidates": [],
            }
        ]
        value["candidates"][0]["candidate_key"] = "different-candidate"
        with self.assertRaises(contract.ContractError):
            contract.validate(value)

    def test_removed_candidate_requires_explicit_retirement_reason(self) -> None:
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
                "change_reason": "candidate population review",
                "retired_candidates": [],
            }
        ]
        value["candidates"] = value["candidates"][:1]
        with self.assertRaises(contract.ContractError):
            contract.validate(value)
        value["retired_candidates"] = [
            {
                "candidate_id": "E2E-CAND-002",
                "reason": "current source confirms duplicate path",
            }
        ]
        self.assertEqual(contract.validate(value)["selection_status"], "ready")

    def test_retired_candidate_cannot_be_reintroduced_after_a_later_revision(
        self,
    ) -> None:
        value = selection()
        value["revision"] = 3
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
                "change_reason": "初回選定",
                "retired_candidates": [],
            },
            {
                "revision": 2,
                "candidate_ids": [
                    {
                        "candidate_id": "E2E-CAND-001",
                        "candidate_key": "checkout-primary",
                    },
                ],
                "change_reason": "既存E2Eとの重複を確認",
                "retired_candidates": [
                    {
                        "candidate_id": "E2E-CAND-002",
                        "reason": "currentな既存E2Eと重複するためretire",
                    }
                ],
            },
        ]
        with self.assertRaises(contract.ContractError):
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
                "change_reason": "初回選定",
                "retired_candidates": [],
            },
            {
                "revision": 2,
                "candidate_ids": [
                    {
                        "candidate_id": "E2E-CAND-001",
                        "candidate_key": "checkout-primary",
                    },
                ],
                "change_reason": "既存E2Eとの重複を確認",
                "retired_candidates": [],
            },
        ]
        with self.assertRaises(contract.ContractError):
            contract.validate(value)

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
        result = subprocess.run(
            [sys.executable, str(SCRIPT)],
            input=json.dumps({"input": value}).encode(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=REPO_ROOT,
            check=False,
        )
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stderr, b"")
        self.assertEqual(json.loads(result.stdout)["result_status"], "blocked")

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
