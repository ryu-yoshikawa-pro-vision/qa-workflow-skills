from __future__ import annotations

import copy
import importlib.util
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
CONTRACT_PATH = (
    REPO_ROOT
    / "skills"
    / "test-condition-design"
    / "scripts"
    / "condition_structure.py"
)
sys.path.insert(0, str(CONTRACT_PATH.parent))
SPEC = importlib.util.spec_from_file_location(
    "condition_structure_formal_design_contract", CONTRACT_PATH
)
assert SPEC is not None and SPEC.loader is not None
contract = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(contract)


def packet() -> dict:
    return {
        "schema_version": "formal-design-v1",
        "design_ref": "FD-001",
        "revision": 1,
        "change_reason": "初回の正式設計",
        "history": [],
        "retired_candidate_refs": [],
        "items_complete": True,
        "conditions_complete": True,
        "source_refs": [
            {"ref": "ARCH-001", "revision": "a7", "currentness": "current"},
            {"ref": "COND-001", "revision": "c3", "currentness": "current"},
            {"ref": "SPEC-001", "revision": "s9", "currentness": "current"},
            {"ref": "TI-001", "revision": "i4", "currentness": "current"},
        ],
        "items": [{"item_ref": "TI-001", "source_ref": "TI-001"}],
        "condition_candidates": [
            {"condition_ref": "COND-001", "source_ref": "COND-001"}
        ],
        "authorities": [
            {
                "authority_ref": "SPEC-001",
                "revision": "s9",
                "currentness": "current",
            }
        ],
        "test_level_evidence": {
            "explicit": None,
            "architecture": {
                "level": "integration",
                "source_ref": "ARCH-001",
                "approved": True,
            },
            "default": {"level": "system", "source_ref": "SPEC-001"},
        },
        "pair_assessments": [
            {
                "item_ref": "TI-001",
                "condition_ref": "COND-001",
                "decision": "adopted",
                "rationale": "このitemの統合責務を検証する",
                "test_level": "integration",
                "tcn_draft_key": "formal-ti1-cond1",
                "covered_by_pair": None,
                "reopen_condition": None,
                "expected_result_candidates": [
                    {
                        "candidate_ref": "ER-001",
                        "text": "注文状態が確定済みになる",
                        "authority_refs": ["SPEC-001"],
                        "observation_method": "current order readback",
                        "side_effects": "在庫確保イベントを1件発行",
                        "revision": "fd1.1",
                    },
                    {
                        "candidate_ref": "ER-002",
                        "text": "注文状態が保留になる",
                        "authority_refs": ["SPEC-001"],
                        "observation_method": "current order readback",
                        "side_effects": "在庫確保イベントを発行しない",
                        "revision": "fd1.1",
                    },
                ],
            }
        ],
    }


def drafts() -> list[dict]:
    return [
        {
            "draft_key": "formal-ti1-cond1",
            "tr_refs": ["TR-001"],
            "authority_refs": [],
        }
    ]


class FormalDesignContractTests(unittest.TestCase):
    def test_adopted_pair_projects_distinct_item_and_candidate_refs(self) -> None:
        result = contract.validate_formal_design(packet(), drafts())
        projected = result["formal-ti1-cond1"]
        self.assertEqual(projected["item_ref"], "TI-001")
        self.assertEqual(projected["condition_ref"], "COND-001")
        self.assertEqual(projected["test_level"], "integration")
        self.assertEqual(
            projected["expected_result_candidate_refs"], ["ER-001", "ER-002"]
        )
        self.assertEqual(result["__formal_design_summary__"]["pair_coverage"], "1/1")

    def test_explicit_test_level_precedes_approved_architecture_and_default(
        self,
    ) -> None:
        resolved = contract.resolve_test_level(
            {
                "explicit": {"level": "acceptance", "source_ref": "REQ-001"},
                "architecture": {
                    "level": "integration",
                    "source_ref": "ARCH-001",
                    "approved": True,
                },
                "default": {"level": "system", "source_ref": "SPEC-001"},
            }
        )
        self.assertEqual(resolved["level"], "acceptance")
        self.assertEqual(resolved["source"], "explicit")

    def test_full_pair_population_requires_explicit_disposition(self) -> None:
        value = packet()
        value["items"].append({"item_ref": "TI-002", "source_ref": "TI-001"})
        with self.assertRaises(contract.FormalDesignError):
            contract.validate_formal_design(value, drafts())

    def test_expected_result_without_current_authority_is_rejected(self) -> None:
        value = packet()
        value["pair_assessments"][0]["expected_result_candidates"][0][
            "authority_refs"
        ] = []
        with self.assertRaises(contract.FormalDesignError):
            contract.validate_formal_design(value, drafts())

    def test_stale_authority_blocks_only_pairs_that_depend_on_it(self) -> None:
        value = packet()
        value["source_refs"].extend(
            [
                {"ref": "SPEC-002", "revision": "s3", "currentness": "current"},
                {"ref": "TI-002", "revision": "i2", "currentness": "current"},
            ]
        )
        value["items"].append({"item_ref": "TI-002", "source_ref": "TI-002"})
        value["authorities"].append(
            {
                "authority_ref": "SPEC-002",
                "revision": "s3",
                "currentness": "current",
            }
        )
        second_assessment = copy.deepcopy(value["pair_assessments"][0])
        second_assessment.update(
            {
                "item_ref": "TI-002",
                "tcn_draft_key": "formal-ti2-cond1",
                "expected_result_candidates": [
                    {
                        **second_assessment["expected_result_candidates"][0],
                        "candidate_ref": "ER-003",
                        "authority_refs": ["SPEC-002"],
                    }
                ],
            }
        )
        value["pair_assessments"].append(second_assessment)
        value["authorities"][0]["currentness"] = "stale"
        value["source_refs"][2]["currentness"] = "stale"

        result = contract.validate_formal_design(
            value,
            [
                *drafts(),
                {
                    "draft_key": "formal-ti2-cond1",
                    "tr_refs": ["TR-002"],
                    "authority_refs": [],
                },
            ],
        )
        summary = result["__formal_design_summary__"]
        self.assertEqual(summary["pair_coverage"], "1/2")
        self.assertEqual(
            summary["unresolved_pairs"],
            [
                {
                    "item_ref": "TI-001",
                    "condition_ref": "COND-001",
                    "decision": "blocked",
                }
            ],
        )
        self.assertNotIn("formal-ti1-cond1", result)
        self.assertEqual(result["formal-ti2-cond1"]["item_ref"], "TI-002")

        shared_condition = packet()
        shared_condition["source_refs"].extend(
            [
                {"ref": "TI-002", "revision": "i2", "currentness": "current"},
            ]
        )
        shared_condition["items"].append({"item_ref": "TI-002", "source_ref": "TI-002"})
        shared_assessment = copy.deepcopy(shared_condition["pair_assessments"][0])
        shared_assessment.update(
            {
                "item_ref": "TI-002",
                "tcn_draft_key": "formal-ti2-cond1",
                "expected_result_candidates": [
                    {
                        **shared_assessment["expected_result_candidates"][0],
                        "candidate_ref": "ER-003",
                    }
                ],
            }
        )
        shared_condition["pair_assessments"].append(shared_assessment)
        shared_condition["source_refs"][1]["currentness"] = "stale"
        shared_result = contract.validate_formal_design(
            shared_condition,
            [
                *drafts(),
                {
                    "draft_key": "formal-ti2-cond1",
                    "tr_refs": ["TR-002"],
                    "authority_refs": [],
                },
            ],
        )
        self.assertEqual(
            shared_result["__formal_design_summary__"]["unresolved_pairs"],
            [
                {
                    "item_ref": "TI-001",
                    "condition_ref": "COND-001",
                    "decision": "blocked",
                },
                {
                    "item_ref": "TI-002",
                    "condition_ref": "COND-001",
                    "decision": "blocked",
                },
            ],
        )

    def test_tcn_draft_authorities_are_preserved_in_pair_record_and_scope_staleness(
        self,
    ) -> None:
        value = packet()
        value["source_refs"].extend(
            [
                {"ref": "SPEC-002", "revision": "s3", "currentness": "stale"},
                {"ref": "TI-002", "revision": "i2", "currentness": "current"},
            ]
        )
        value["items"].append({"item_ref": "TI-002", "source_ref": "TI-002"})
        value["authorities"].append(
            {
                "authority_ref": "SPEC-002",
                "revision": "s3",
                "currentness": "stale",
            }
        )
        second_assessment = copy.deepcopy(value["pair_assessments"][0])
        second_assessment.update(
            {
                "item_ref": "TI-002",
                "tcn_draft_key": "formal-ti2-cond1",
                "expected_result_candidates": [
                    {
                        **second_assessment["expected_result_candidates"][0],
                        "candidate_ref": "ER-003",
                    }
                ],
            }
        )
        value["pair_assessments"].append(second_assessment)
        tcn_drafts = [
            {**drafts()[0], "authority_refs": ["SPEC-002"]},
            {
                "draft_key": "formal-ti2-cond1",
                "tr_refs": ["TR-002"],
                "authority_refs": [],
            },
        ]

        result = contract.validate_formal_design(value, tcn_drafts)

        summary = result["__formal_design_summary__"]
        self.assertEqual(summary["pair_coverage"], "1/2")
        self.assertEqual(summary["pair_coverage_status"], "incomplete")
        self.assertEqual(
            summary["unresolved_pairs"],
            [
                {
                    "item_ref": "TI-001",
                    "condition_ref": "COND-001",
                    "decision": "blocked",
                }
            ],
        )
        record_rows = result["__formal_design_record__"]["pair_assessments"]
        self.assertEqual(record_rows[0]["tcn_authority_refs"], ["SPEC-002"])
        self.assertEqual(record_rows[1]["tcn_authority_refs"], [])

    def test_tcn_authority_must_match_input_and_registered_currentness(self) -> None:
        value = packet()
        value["source_refs"].append(
            {"ref": "SPEC-002", "revision": "s3", "currentness": "current"}
        )
        value["authorities"].append(
            {
                "authority_ref": "SPEC-002",
                "revision": "s3",
                "currentness": "current",
            }
        )
        value["pair_assessments"][0]["tcn_authority_refs"] = ["SPEC-002"]
        matching_draft = {**drafts()[0], "authority_refs": ["SPEC-002"]}
        result = contract.validate_formal_design(value, [matching_draft])
        self.assertEqual(
            result["__formal_design_record__"]["pair_assessments"][0][
                "tcn_authority_refs"
            ],
            ["SPEC-002"],
        )

        value["pair_assessments"][0]["tcn_authority_refs"] = ["SPEC-001"]
        with self.assertRaises(contract.FormalDesignError):
            contract.validate_formal_design(value, [matching_draft])

        value["pair_assessments"][0].pop("tcn_authority_refs")
        value["pair_assessments"][0]["tcn_authority_refs"] = ["UNKNOWN-001"]
        with self.assertRaises(contract.FormalDesignError):
            contract.validate_formal_design(value, [matching_draft])

        value["pair_assessments"][0]["tcn_authority_refs"] = ["SPEC-002"]
        value["authorities"][1]["revision"] = "s4"
        with self.assertRaises(contract.FormalDesignError):
            contract.validate_formal_design(value, [matching_draft])

        invalid_refs = [None, [""], ["SPEC-002", "SPEC-002"], ["SPEC-002", "SPEC-001"]]
        for refs in invalid_refs:
            with self.subTest(tcn_authority_refs=refs):
                invalid = packet()
                invalid["source_refs"].append(
                    {"ref": "SPEC-002", "revision": "s3", "currentness": "current"}
                )
                invalid["authorities"].append(
                    {
                        "authority_ref": "SPEC-002",
                        "revision": "s3",
                        "currentness": "current",
                    }
                )
                invalid["pair_assessments"][0]["tcn_authority_refs"] = refs
                with self.assertRaises(contract.FormalDesignError):
                    contract.validate_formal_design(
                        invalid,
                        [{**drafts()[0], "authority_refs": ["SPEC-002"]}],
                    )

    def test_unknown_tcn_authority_blocks_only_its_adopted_pair(self) -> None:
        value = packet()
        value["source_refs"].append(
            {"ref": "SPEC-002", "revision": "s3", "currentness": "unknown"}
        )
        value["authorities"].append(
            {
                "authority_ref": "SPEC-002",
                "revision": "s3",
                "currentness": "unknown",
            }
        )

        result = contract.validate_formal_design(
            value,
            [{**drafts()[0], "authority_refs": ["SPEC-002"]}],
        )

        summary = result["__formal_design_summary__"]
        self.assertEqual(summary["pair_coverage"], "0/1")
        self.assertEqual(summary["unresolved_pairs"][0]["decision"], "blocked")

    def test_adopted_pair_without_draft_or_explicit_tcn_authorities_stays_blocked(
        self,
    ) -> None:
        value = packet()

        result = contract.validate_formal_design(value, [])

        summary = result["__formal_design_summary__"]
        self.assertEqual(summary["pair_coverage_status"], "incomplete")
        self.assertEqual(summary["unresolved_pairs"][0]["decision"], "blocked")
        assessment = result["__formal_design_record__"]["pair_assessments"][0]
        self.assertNotIn("tcn_authority_refs", assessment)

    def test_explicit_tcn_authorities_are_retained_when_partial_rerun_has_no_draft(
        self,
    ) -> None:
        value = packet()
        value["pair_assessments"][0]["tcn_authority_refs"] = ["SPEC-001"]

        result = contract.validate_formal_design(value, [])

        self.assertEqual(result["__formal_design_summary__"]["pair_coverage"], "1/1")
        self.assertEqual(
            result["__formal_design_record__"]["pair_assessments"][0][
                "tcn_authority_refs"
            ],
            ["SPEC-001"],
        )

    def test_unmapped_stale_source_blocks_all_pairs_safely(self) -> None:
        value = packet()
        value["source_refs"].extend(
            [
                {"ref": "TI-002", "revision": "i2", "currentness": "current"},
                {"ref": "UNMAPPED-001", "revision": "u3", "currentness": "stale"},
            ]
        )
        value["items"].append({"item_ref": "TI-002", "source_ref": "TI-002"})
        second_assessment = copy.deepcopy(value["pair_assessments"][0])
        second_assessment.update(
            {
                "item_ref": "TI-002",
                "tcn_draft_key": "formal-ti2-cond1",
                "expected_result_candidates": [
                    {
                        **second_assessment["expected_result_candidates"][0],
                        "candidate_ref": "ER-003",
                    }
                ],
            }
        )
        value["pair_assessments"].append(second_assessment)

        result = contract.validate_formal_design(
            value,
            [
                *drafts(),
                {
                    "draft_key": "formal-ti2-cond1",
                    "tr_refs": ["TR-002"],
                    "authority_refs": [],
                },
            ],
        )

        summary = result["__formal_design_summary__"]
        self.assertEqual(summary["pair_coverage"], "0/2")
        self.assertEqual(summary["pair_coverage_status"], "incomplete")
        self.assertEqual(
            summary["unresolved_pairs"],
            [
                {
                    "item_ref": item_ref,
                    "condition_ref": "COND-001",
                    "decision": "blocked",
                }
                for item_ref in ("TI-001", "TI-002")
            ],
        )

    def test_item_scoped_test_levels_resolve_independently(self) -> None:
        value = packet()
        value["source_refs"].append(
            {"ref": "TI-002", "revision": "i2", "currentness": "current"}
        )
        value["items"].append({"item_ref": "TI-002", "source_ref": "TI-002"})
        value["test_level_evidence"] = [
            {
                "item_ref": "TI-001",
                "evidence": copy.deepcopy(packet()["test_level_evidence"]),
            },
            {
                "item_ref": "TI-002",
                "evidence": {
                    "explicit": None,
                    "architecture": {
                        "level": "acceptance",
                        "source_ref": "ARCH-001",
                        "approved": False,
                    },
                    "default": {"level": "system", "source_ref": "SPEC-001"},
                },
            },
        ]
        second_assessment = copy.deepcopy(value["pair_assessments"][0])
        second_assessment.update(
            {
                "item_ref": "TI-002",
                "test_level": "system",
                "tcn_draft_key": "formal-ti2-cond1",
                "expected_result_candidates": [
                    {
                        **second_assessment["expected_result_candidates"][0],
                        "candidate_ref": "ER-003",
                    }
                ],
            }
        )
        value["pair_assessments"].append(second_assessment)

        result = contract.validate_formal_design(
            value,
            [
                *drafts(),
                {
                    "draft_key": "formal-ti2-cond1",
                    "tr_refs": ["TR-002"],
                    "authority_refs": [],
                },
            ],
        )

        self.assertEqual(result["formal-ti1-cond1"]["test_level"], "integration")
        self.assertEqual(result["formal-ti2-cond1"]["test_level"], "system")
        self.assertEqual(result["formal-ti2-cond1"]["test_level_source"], "default")
        self.assertEqual(result["__formal_design_summary__"]["pair_coverage"], "2/2")

    def test_authority_revision_must_match_its_source_revision(self) -> None:
        value = packet()
        value["authorities"][0]["revision"] = "s8"
        with self.assertRaises(contract.FormalDesignError):
            contract.validate_formal_design(value, drafts())

    def test_other_test_level_is_a_disposition_and_not_an_adopted_tcn(self) -> None:
        value = packet()
        value["items"].append({"item_ref": "TI-002", "source_ref": "TI-001"})
        value["pair_assessments"].append(
            {
                "item_ref": "TI-002",
                "condition_ref": "COND-001",
                "decision": "other_test_level",
                "rationale": "別レベルのTCで確認する",
                "test_level": "system",
                "tcn_draft_key": None,
                "expected_result_candidates": [],
                "covered_by_pair": None,
                "reopen_condition": None,
            }
        )
        result = contract.validate_formal_design(value, drafts())
        self.assertEqual(result["__formal_design_summary__"]["pair_denominator"], 2)
        self.assertEqual(result["__formal_design_summary__"]["pair_closed"], 2)
        invalid_non_adopted = copy.deepcopy(value)
        invalid_non_adopted["pair_assessments"][1]["tcn_authority_refs"] = []
        with self.assertRaises(contract.FormalDesignError):
            contract.validate_formal_design(invalid_non_adopted, drafts())
        self.assertEqual(
            {key for key in result if not key.startswith("__")},
            {"formal-ti1-cond1"},
        )

        invalid = copy.deepcopy(value)
        invalid["pair_assessments"][1]["test_level"] = "integration"
        with self.assertRaises(contract.FormalDesignError):
            contract.validate_formal_design(invalid, drafts())

    def test_duplicate_pair_closes_only_with_adopted_cover_target(self) -> None:
        value = packet()
        value["items"].append({"item_ref": "TI-002", "source_ref": "TI-001"})
        value["pair_assessments"].append(
            {
                "item_ref": "TI-002",
                "condition_ref": "COND-001",
                "decision": "duplicate",
                "rationale": "TI-001の採用pairが同じ検証責務を担う",
                "test_level": "integration",
                "tcn_draft_key": None,
                "expected_result_candidates": [],
                "covered_by_pair": {"item_ref": "TI-001", "condition_ref": "COND-001"},
                "reopen_condition": None,
            }
        )
        result = contract.validate_formal_design(value, drafts())
        self.assertEqual(result["__formal_design_summary__"]["pair_coverage"], "2/2")

        invalid = copy.deepcopy(value)
        invalid["pair_assessments"][0].update(
            {
                "decision": "duplicate",
                "tcn_draft_key": None,
                "expected_result_candidates": [],
                "covered_by_pair": {"item_ref": "TI-002", "condition_ref": "COND-001"},
            }
        )
        invalid["pair_assessments"][1].update(
            {
                "decision": "out_of_scope",
                "covered_by_pair": None,
            }
        )
        with self.assertRaises(contract.FormalDesignError):
            contract.validate_formal_design(invalid, [])

    def test_retiring_expected_result_candidate_requires_reason(self) -> None:
        value = packet()
        value["revision"] = 2
        value["history"] = [
            {
                "revision": 1,
                "change_reason": "期待結果候補の見直し",
                "pair_decisions": [
                    {
                        "item_ref": "TI-001",
                        "condition_ref": "COND-001",
                        "decision": "adopted",
                    }
                ],
                "candidate_assignments": [
                    {
                        "candidate_ref": "ER-001",
                        "item_ref": "TI-001",
                        "condition_ref": "COND-001",
                    },
                    {
                        "candidate_ref": "ER-002",
                        "item_ref": "TI-001",
                        "condition_ref": "COND-001",
                    },
                ],
                "retired_candidate_refs": [],
            }
        ]
        value["pair_assessments"][0]["expected_result_candidates"] = value[
            "pair_assessments"
        ][0]["expected_result_candidates"][:1]
        with self.assertRaises(contract.FormalDesignError):
            contract.validate_formal_design(value, drafts())
        value["retired_candidate_refs"] = [
            {
                "candidate_ref": "ER-002",
                "reason": "current Authority disambiguates the outcome",
            }
        ]
        result = contract.validate_formal_design(value, drafts())
        self.assertEqual(result["formal-ti1-cond1"]["item_ref"], "TI-001")

    def test_history_candidate_assignment_requires_an_adopted_pair(self) -> None:
        value = packet()
        value["revision"] = 2
        value["history"] = [
            {
                "revision": 1,
                "change_reason": "decision changed",
                "pair_decisions": [
                    {
                        "item_ref": "TI-001",
                        "condition_ref": "COND-001",
                        "decision": "not_applicable",
                    }
                ],
                "candidate_assignments": [
                    {
                        "candidate_ref": "ER-001",
                        "item_ref": "TI-001",
                        "condition_ref": "COND-001",
                    }
                ],
                "retired_candidate_refs": [],
            }
        ]
        with self.assertRaises(contract.FormalDesignError):
            contract.validate_formal_design(value, drafts())
        value["history"][0]["pair_decisions"][0]["decision"] = "adopted"
        value["history"][0]["candidate_assignments"] = []
        with self.assertRaises(contract.FormalDesignError):
            contract.validate_formal_design(value, drafts())

    def test_retired_expected_result_candidate_cannot_be_reintroduced(self) -> None:
        revision_one = {
            "revision": 1,
            "change_reason": "初回の正式設計",
            "pair_decisions": [
                {
                    "item_ref": "TI-001",
                    "condition_ref": "COND-001",
                    "decision": "adopted",
                }
            ],
            "candidate_assignments": [
                {
                    "candidate_ref": "ER-001",
                    "item_ref": "TI-001",
                    "condition_ref": "COND-001",
                },
                {
                    "candidate_ref": "ER-002",
                    "item_ref": "TI-001",
                    "condition_ref": "COND-001",
                },
            ],
            "retired_candidate_refs": [],
        }
        revision_two = copy.deepcopy(revision_one)
        revision_two.update(
            {
                "revision": 2,
                "change_reason": "重複候補をretire",
                "candidate_assignments": revision_one["candidate_assignments"][:1],
                "retired_candidate_refs": [
                    {
                        "candidate_ref": "ER-002",
                        "reason": "現在のAuthorityで重複が確定した",
                    }
                ],
            }
        )
        value = packet()
        value["revision"] = 3
        value["history"] = [revision_one, revision_two]
        with self.assertRaises(contract.FormalDesignError):
            contract.validate_formal_design(value, drafts())

    def test_history_must_record_candidate_retirement_at_removal_revision(self) -> None:
        revision_one = {
            "revision": 1,
            "change_reason": "初回の正式設計",
            "pair_decisions": [
                {
                    "item_ref": "TI-001",
                    "condition_ref": "COND-001",
                    "decision": "adopted",
                }
            ],
            "candidate_assignments": [
                {
                    "candidate_ref": "ER-001",
                    "item_ref": "TI-001",
                    "condition_ref": "COND-001",
                },
                {
                    "candidate_ref": "ER-002",
                    "item_ref": "TI-001",
                    "condition_ref": "COND-001",
                },
            ],
            "retired_candidate_refs": [],
        }
        revision_two = copy.deepcopy(revision_one)
        revision_two.update(
            {
                "revision": 2,
                "change_reason": "候補母集団を更新",
                "candidate_assignments": revision_one["candidate_assignments"][:1],
            }
        )
        value = packet()
        value["revision"] = 3
        value["history"] = [revision_one, revision_two]
        value["pair_assessments"][0]["expected_result_candidates"] = value[
            "pair_assessments"
        ][0]["expected_result_candidates"][:1]
        value["retired_candidate_refs"] = [
            {"candidate_ref": "ER-002", "reason": "現在のAuthorityで重複が確定した"}
        ]
        with self.assertRaises(contract.FormalDesignError):
            contract.validate_formal_design(value, drafts())

    def test_candidate_id_cannot_be_assigned_to_multiple_current_pairs(self) -> None:
        value = packet()
        value["items"].append({"item_ref": "TI-002", "source_ref": "TI-001"})
        second_pair = copy.deepcopy(value["pair_assessments"][0])
        second_pair["item_ref"] = "TI-002"
        second_pair["tcn_draft_key"] = "formal-ti2-cond1"
        value["pair_assessments"].append(second_pair)
        with self.assertRaises(contract.FormalDesignError):
            contract.validate_formal_design(
                value,
                drafts()
                + [
                    {
                        "draft_key": "formal-ti2-cond1",
                        "tr_refs": ["TR-001"],
                        "authority_refs": [],
                    }
                ],
            )

    def test_zero_pair_denominator_is_unknown_not_complete(self) -> None:
        value = packet()
        value["items"] = []
        value["condition_candidates"] = []
        value["pair_assessments"] = []
        result = contract.validate_formal_design(value, [])
        summary = result["__formal_design_summary__"]
        self.assertIsNone(summary["pair_coverage"])
        self.assertEqual(summary["pair_coverage_status"], "unknown_zero_denominator")

    def test_unconfirmed_pair_does_not_count_as_closed(self) -> None:
        value = packet()
        row = value["pair_assessments"][0]
        row.update(
            {
                "decision": "unconfirmed",
                "tcn_draft_key": None,
                "expected_result_candidates": [],
                "covered_by_pair": None,
                "reopen_condition": "ownerから実itemの適用仕様を取得する",
            }
        )
        result = contract.validate_formal_design(value, [])
        summary = result["__formal_design_summary__"]
        self.assertEqual(summary["pair_coverage"], "0/1")
        self.assertEqual(summary["pair_coverage_status"], "incomplete")


if __name__ == "__main__":
    unittest.main()
