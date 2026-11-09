from __future__ import annotations

import unittest

from tests.skills.runtime.test_ep_vertical_integration import (
    CONDITION_SCRIPT,
    condition_input,
    condition_metadata,
    run_script,
    runtime,
)


def current_sources():
    return [
        runtime.make_machine_entity(
            "test-requirement-design",
            "tr",
            "TR-001",
            {"tr_id": "TR-001", "text": "current TR", "scope_refs": []},
        ),
        runtime.make_machine_entity(
            "spec-analysis",
            "authority",
            "SPEC-001",
            {"authority_id": "SPEC-001", "text": "current authority"},
        ),
        runtime.make_machine_entity(
            "test-analysis",
            "product_risk",
            "R-001",
            {"risk_id": "R-001", "text": "current risk"},
        ),
        runtime.make_machine_entity(
            "test-analysis",
            "technique_selection",
            "SEL-001",
            {"selection_key": "SEL-001", "selected_techniques": ["ep"]},
        ),
    ]


def request_for(value: dict, source_entities: list[dict]) -> dict:
    metadata = condition_metadata()
    metadata["input_mode"] = "artifact"
    metadata["upstream_entities"] = [
        {
            "skill": row["skill"],
            "entity_type": row["entity_type"],
            "entity_ref": row["entity_ref"],
            "content": row["content"],
        }
        for row in source_entities
    ]
    return {"metadata": metadata, "input": value}


def formal_design_packet(
    item_refs: tuple[str, ...] = ("TI-001",),
    *,
    revision: int = 1,
    history: list[dict] | None = None,
) -> dict:
    return {
        "schema_version": "formal-design-v1",
        "design_ref": "FD-001",
        "revision": revision,
        "change_reason": "正式設計の更新",
        "history": [] if history is None else history,
        "retired_candidate_refs": [],
        "items_complete": True,
        "conditions_complete": True,
        "source_refs": [
            {"ref": "ARCH-001", "revision": "a7", "currentness": "current"},
            {"ref": "COND-001", "revision": "c3", "currentness": "current"},
            {"ref": "SPEC-001", "revision": "s9", "currentness": "current"},
            *[
                {
                    "ref": item_ref,
                    "revision": f"{item_ref.lower()}-r1",
                    "currentness": "current",
                }
                for item_ref in item_refs
            ],
        ],
        "items": [
            {"item_ref": item_ref, "source_ref": item_ref} for item_ref in item_refs
        ],
        "condition_candidates": [
            {"condition_ref": "COND-001", "source_ref": "COND-001"}
        ],
        "authorities": [
            {"authority_ref": "SPEC-001", "revision": "s9", "currentness": "current"}
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
                "item_ref": item_ref,
                "condition_ref": "COND-001",
                "decision": "adopted",
                "rationale": "item固有の統合経路を確認する",
                "test_level": "integration",
                "tcn_draft_key": "tcn-draft" if index == 1 else f"tcn-draft-{index}",
                "covered_by_pair": None,
                "reopen_condition": None,
                "expected_result_candidates": [
                    {
                        "candidate_ref": f"ER-{index:03}",
                        "text": f"{item_ref}の状態が確定済みになる",
                        "authority_refs": ["SPEC-001"],
                        "observation_method": "current order readback",
                        "side_effects": "在庫確保イベントを1件発行",
                        "revision": f"fd{revision}.{index}",
                    }
                ],
            }
            for index, item_ref in enumerate(item_refs, start=1)
        ],
    }


class ConditionStructureRuntimeTests(unittest.TestCase):
    def test_formal_item_condition_packet_projects_to_formal_tcn(self) -> None:
        value = condition_input()
        value["test_requirements"][0].update(
            {
                "test_level": "integration",
                "test_level_source": "approved_architecture",
                "test_level_source_ref": "ARCH-001",
            }
        )
        value["formal_design"] = formal_design_packet()
        sources = current_sources()
        sources[0] = runtime.make_machine_entity(
            "test-requirement-design",
            "tr",
            "TR-001",
            {
                "tr_id": "TR-001",
                "text": "current TR",
                "scope_refs": [],
                "test_level": "integration",
                "test_level_source": "approved_architecture",
                "test_level_source_ref": "ARCH-001",
            },
        )
        result = run_script(CONDITION_SCRIPT, request_for(value, sources))
        self.assertEqual(result["runtime_status"], "ok", result)
        self.assertEqual(result["result_status"], "ready", result)
        tcn = next(
            row for row in result["payload"]["entities"] if row["entity_type"] == "tcn"
        )
        self.assertEqual(tcn["content"]["item_ref"], "TI-001")
        self.assertEqual(tcn["content"]["condition_ref"], "COND-001")
        self.assertEqual(tcn["content"]["expected_result_candidate_refs"], ["ER-001"])
        self.assertEqual(tcn["content"]["test_level"], "integration")
        record = result["payload"]["formal_design_record"]
        self.assertEqual(record["design_ref"], "FD-001")
        self.assertEqual(
            record["pair_assessments"][0]["rationale"], "item固有の統合経路を確認する"
        )

    def test_formal_record_retains_non_adopted_decisions_and_history(self) -> None:
        value = condition_input()
        value["test_requirements"][0].update(
            {
                "test_level": "integration",
                "test_level_source": "approved_architecture",
                "test_level_source_ref": "ARCH-001",
            }
        )
        packet = formal_design_packet(("TI-001", "TI-002"), revision=2)
        packet["history"] = [
            {
                "revision": 1,
                "change_reason": "item population reviewed",
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
                    }
                ],
                "retired_candidate_refs": [],
            }
        ]
        packet["pair_assessments"][1].update(
            {
                "decision": "not_applicable",
                "rationale": "このitemは共通条件の対象外である",
                "tcn_draft_key": None,
                "expected_result_candidates": [],
            }
        )
        value["formal_design"] = packet
        sources = current_sources()
        sources[0] = runtime.make_machine_entity(
            "test-requirement-design",
            "tr",
            "TR-001",
            {
                "tr_id": "TR-001",
                "text": "current TR",
                "scope_refs": [],
                "test_level": "integration",
                "test_level_source": "approved_architecture",
                "test_level_source_ref": "ARCH-001",
            },
        )

        result = run_script(CONDITION_SCRIPT, request_for(value, sources))
        self.assertEqual(result["runtime_status"], "ok", result)
        self.assertEqual(result["result_status"], "ready", result)
        self.assertEqual(
            result["payload"]["formal_design_summary"]["pair_coverage"], "2/2"
        )
        record = result["payload"]["formal_design_record"]
        self.assertEqual(record["revision"], 2)
        self.assertEqual(
            [row["decision"] for row in record["pair_assessments"]],
            ["adopted", "not_applicable"],
        )
        self.assertEqual(record["history"][0]["revision"], 1)

    def test_formal_multiple_items_receive_distinct_tcn_ids(self) -> None:
        value = condition_input()
        value["test_requirements"][0].update(
            {
                "test_level": "integration",
                "test_level_source": "approved_architecture",
                "test_level_source_ref": "ARCH-001",
            }
        )
        second_tcn = dict(value["test_conditions"][0])
        second_tcn["draft_key"] = "tcn-draft-2"
        value["test_conditions"].append(second_tcn)
        second_model = dict(value["models"][0])
        second_model["draft_key"] = "model-draft-2"
        second_model["parent_tcn_draft_key"] = "tcn-draft-2"
        value["models"].append(second_model)
        value["formal_design"] = formal_design_packet(("TI-001", "TI-002"))

        sources = current_sources()
        sources[0] = runtime.make_machine_entity(
            "test-requirement-design",
            "tr",
            "TR-001",
            {
                "tr_id": "TR-001",
                "text": "current TR",
                "scope_refs": [],
                "test_level": "integration",
                "test_level_source": "approved_architecture",
                "test_level_source_ref": "ARCH-001",
            },
        )
        result = run_script(CONDITION_SCRIPT, request_for(value, sources))
        self.assertEqual(result["runtime_status"], "ok", result)
        self.assertEqual(result["result_status"], "ready", result)
        tcns = [
            row for row in result["payload"]["entities"] if row["entity_type"] == "tcn"
        ]
        self.assertEqual(
            {row["content"]["item_ref"]: row["entity_ref"] for row in tcns},
            {"TI-001": "TCN-001", "TI-002": "TCN-002"},
        )
        self.assertEqual(
            {
                row["content"]["item_ref"]: row["content"]["condition_ref"]
                for row in tcns
            },
            {"TI-001": "COND-001", "TI-002": "COND-001"},
        )
        self.assertEqual(
            {
                row["content"]["item_ref"]: row["content"][
                    "expected_result_candidate_refs"
                ]
                for row in tcns
            },
            {"TI-001": ["ER-001"], "TI-002": ["ER-002"]},
        )

    def test_formal_revision_reuses_existing_tcn_id(self) -> None:
        first_value = condition_input()
        first_value["test_requirements"][0].update(
            {
                "test_level": "integration",
                "test_level_source": "approved_architecture",
                "test_level_source_ref": "ARCH-001",
            }
        )
        first_value["formal_design"] = formal_design_packet()
        sources = current_sources()
        sources[0] = runtime.make_machine_entity(
            "test-requirement-design",
            "tr",
            "TR-001",
            {
                "tr_id": "TR-001",
                "text": "current TR",
                "scope_refs": [],
                "test_level": "integration",
                "test_level_source": "approved_architecture",
                "test_level_source_ref": "ARCH-001",
            },
        )
        first = run_script(CONDITION_SCRIPT, request_for(first_value, sources))
        self.assertEqual(first["runtime_status"], "ok", first)
        self.assertEqual(first["payload"]["tcn_id_map"][0]["tcn_id"], "TCN-001")

        second_value = condition_input()
        second_value["test_requirements"][0].update(first_value["test_requirements"][0])
        second_value["test_conditions"][0].update(
            {"identity_action": "reuse", "reuse_id": "TCN-001"}
        )
        second_value["models"][0].update(
            {"identity_action": "reuse", "reuse_model_key": "ep-001"}
        )
        second_value.update(
            {
                "previous_tcn_ids": first["payload"]["tcn_id_state"],
                "previous_model_keys": first["payload"]["model_key_state"],
                "update_scope_tcn_ids": ["TCN-001"],
                "update_scope_model_keys": ["ep-001"],
            }
        )
        second_value["formal_design"] = formal_design_packet(
            revision=2,
            history=[
                {
                    "revision": 1,
                    "change_reason": "expected result candidate revision updated",
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
                        }
                    ],
                    "retired_candidate_refs": [],
                }
            ],
        )
        second = run_script(CONDITION_SCRIPT, request_for(second_value, sources))
        self.assertEqual(second["runtime_status"], "ok", second)
        self.assertEqual(second["result_status"], "ready", second)
        self.assertEqual(second["payload"]["tcn_id_map"][0]["tcn_id"], "TCN-001")
        tcn = next(
            row for row in second["payload"]["entities"] if row["entity_type"] == "tcn"
        )
        self.assertEqual(tcn["content"]["formal_design_revision"], 2)
        self.assertEqual(
            tcn["content"]["expected_result_candidates"][0]["revision"], "fd2.1"
        )

    def test_scope_ownership_propagates_and_inactive_identity_reactivates(self) -> None:
        value = condition_input()
        value["test_requirements"][0]["scope_refs"] = ["SCOPE-001"]
        first = run_script(
            CONDITION_SCRIPT, {"metadata": condition_metadata(), "input": value}
        )
        self.assertEqual(first["runtime_status"], "ok", first)
        tcn = next(
            row for row in first["payload"]["entities"] if row["entity_type"] == "tcn"
        )
        model = next(
            row for row in first["payload"]["entities"] if row["entity_type"] == "model"
        )
        self.assertEqual(tcn["content"]["scope_refs"], ["SCOPE-001"])
        self.assertEqual(model["content"]["scope_refs"], ["SCOPE-001"])
        self.assertEqual(
            first["payload"]["tcn_id_state"][0]["scope_refs"], ["SCOPE-001"]
        )

        blocked_value = condition_input()
        blocked_value.update(
            {
                "test_requirements": [],
                "technique_selections": [],
                "test_conditions": [],
                "models": [],
                "previous_tcn_ids": first["payload"]["tcn_id_state"],
                "previous_model_keys": first["payload"]["model_key_state"],
                "inactive_tcn_ids": ["TCN-001"],
                "inactive_model_keys": ["ep-001"],
                "inactive_tcn_history": [tcn],
                "inactive_model_history": [model],
            }
        )
        blocked = run_script(
            CONDITION_SCRIPT,
            {"metadata": condition_metadata(), "input": blocked_value},
        )
        self.assertEqual(blocked["runtime_status"], "ok", blocked)
        self.assertEqual(blocked["payload"]["tcn_id_state"][0]["status"], "inactive")
        self.assertEqual(blocked["payload"]["model_key_state"][0]["status"], "inactive")
        self.assertEqual(blocked["payload"]["entities"], [])
        self.assertEqual(len(blocked["payload"]["inactive_tcn_history"]), 1)

        active_value = condition_input()
        active_value["test_requirements"][0]["scope_refs"] = ["SCOPE-001"]
        active_value["test_conditions"][0].update(
            {"identity_action": "reuse", "reuse_id": "TCN-001"}
        )
        active_value["models"][0].update(
            {"identity_action": "reuse", "reuse_model_key": "ep-001"}
        )
        active_value.update(
            {
                "previous_tcn_ids": blocked["payload"]["tcn_id_state"],
                "previous_model_keys": blocked["payload"]["model_key_state"],
                "update_scope_tcn_ids": ["TCN-001"],
                "update_scope_model_keys": ["ep-001"],
                "inactive_tcn_history": blocked["payload"]["inactive_tcn_history"],
                "inactive_model_history": blocked["payload"]["inactive_model_history"],
            }
        )
        reactivated = run_script(
            CONDITION_SCRIPT,
            {"metadata": condition_metadata(), "input": active_value},
        )
        self.assertEqual(reactivated["runtime_status"], "ok", reactivated)
        self.assertEqual(reactivated["payload"]["tcn_id_map"][0]["tcn_id"], "TCN-001")
        self.assertEqual(reactivated["payload"]["inactive_tcn_history"], [])

    def test_zero_scope_terminal_closes_inactive_ids_without_current_entities(
        self,
    ) -> None:
        value = condition_input()
        value.update(
            {
                "test_requirements": [],
                "technique_selections": [],
                "test_conditions": [],
                "models": [],
                "previous_tcn_ids": [
                    {
                        "tcn_id": "TCN-001",
                        "status": "inactive",
                        "scope_refs": ["SCOPE-001"],
                    }
                ],
                "previous_model_keys": [
                    {
                        "model_key": "ep-001",
                        "model_type": "ep",
                        "technique_slug": "ep",
                        "parent_tcn_id": "TCN-001",
                        "selection_source": "user",
                        "selection_key": None,
                        "derived_from_model_key": None,
                        "status": "inactive",
                        "scope_refs": ["SCOPE-001"],
                    }
                ],
                "update_scope_tcn_ids": ["TCN-001"],
                "update_scope_model_keys": ["ep-001"],
                "inactive_tcn_history": [],
                "inactive_model_history": [],
                "zero_scope_terminal": True,
            }
        )
        # A terminal run still validates and carries the last active snapshots as input.
        tcn = runtime.make_machine_entity(
            "test-condition-design",
            "tcn",
            "TCN-001",
            {"tcn_id": "TCN-001", "scope_refs": ["SCOPE-001"]},
        )
        model = runtime.make_machine_entity(
            "test-condition-design",
            "model",
            "ep-001",
            {"model_key": "ep-001", "scope_refs": ["SCOPE-001"]},
            model_key="ep-001",
        )
        value["inactive_tcn_history"] = [tcn]
        value["inactive_model_history"] = [model]
        result = run_script(
            CONDITION_SCRIPT, {"metadata": condition_metadata(), "input": value}
        )
        self.assertEqual(result["runtime_status"], "ok", result)
        self.assertEqual(result["payload"]["tcn_id_state"][0]["status"], "deleted")
        self.assertEqual(result["payload"]["tcn_id_state"][0]["scope_refs"], [])
        self.assertEqual(result["payload"]["model_key_state"][0]["status"], "deleted")
        self.assertEqual(result["payload"]["model_key_state"][0]["scope_refs"], [])
        self.assertEqual(result["payload"]["entities"], [])
        self.assertEqual(result["payload"]["inactive_tcn_history"], [])

    def test_condition_structure_assigns_stable_tcn_and_model_state(self) -> None:
        value = condition_input()
        value["models"][0]["selection_source"] = "user"
        value["models"][0]["selection_key"] = None
        value["technique_selections"] = []
        result = run_script(
            CONDITION_SCRIPT, {"metadata": condition_metadata(), "input": value}
        )
        self.assertEqual(result["runtime_status"], "ok")
        self.assertEqual(result["result_status"], "ready")
        self.assertEqual(result["payload"]["tcn_id_map"][0]["tcn_id"], "TCN-001")
        self.assertEqual(
            result["payload"]["active_model_metadata"][0]["model_key"], "ep-001"
        )

    def test_tcn_and_analysis_model_resolve_current_semantic_dependencies(self) -> None:
        value = condition_input()
        value["test_conditions"][0]["authority_refs"] = ["SPEC-001"]
        value["test_conditions"][0]["risk_refs"] = ["R-001"]
        sources = current_sources()
        result = run_script(CONDITION_SCRIPT, request_for(value, sources))
        self.assertEqual(result["runtime_status"], "ok", result)
        entities = result["payload"]["entities"]
        tcn = next(row for row in entities if row["entity_type"] == "tcn")
        model = next(row for row in entities if row["entity_type"] == "model")
        self.assertEqual(
            {
                (row["skill"], row["entity_type"], row["entity_ref"])
                for row in tcn["upstream_entity_dependencies"]
            },
            {
                ("test-requirement-design", "tr", "TR-001"),
                ("spec-analysis", "authority", "SPEC-001"),
                ("test-analysis", "product_risk", "R-001"),
            },
        )
        self.assertEqual(
            {
                (row["skill"], row["entity_type"], row["entity_ref"])
                for row in model["upstream_entity_dependencies"]
            },
            {
                ("test-condition-design", "tcn", "TCN-001"),
                ("test-analysis", "technique_selection", "SEL-001"),
            },
        )

    def test_tcn_disposition_uses_shared_current_entity_dependency_contract(
        self,
    ) -> None:
        sources = current_sources()
        first_tr = next(row for row in sources if row["entity_type"] == "tr")
        second_tr = runtime.make_machine_entity(
            "test-requirement-design",
            "tr",
            "TR-002",
            {"tr_id": "TR-002", "text": "covered by existing TR", "scope_refs": []},
        )
        sources.append(second_tr)
        value = condition_input()
        value["test_conditions"][0]["tr_refs"] = []
        value["requirement_dispositions"] = [
            {
                "upstream_entity": {
                    key: first_tr[key]
                    for key in (
                        "skill",
                        "entity_type",
                        "entity_ref",
                        "content_fingerprint",
                    )
                },
                "handling": "重複",
                "reason": "covered by TR-002",
                "authority_refs": [],
                "covered_by_entity": {
                    key: second_tr[key]
                    for key in (
                        "skill",
                        "entity_type",
                        "entity_ref",
                        "content_fingerprint",
                    )
                },
            }
        ]
        result = run_script(CONDITION_SCRIPT, request_for(value, sources))
        self.assertEqual(result["runtime_status"], "ok", result)
        disposition = next(
            row
            for row in result["payload"]["entities"]
            if row["entity_type"] == "disposition"
        )
        self.assertEqual(
            {
                (row["skill"], row["entity_type"], row["entity_ref"]): row[
                    "content_fingerprint"
                ]
                for row in disposition["upstream_entity_dependencies"]
            },
            {
                ("test-requirement-design", "tr", "TR-001"): first_tr[
                    "content_fingerprint"
                ],
                ("test-requirement-design", "tr", "TR-002"): second_tr[
                    "content_fingerprint"
                ],
            },
        )

    def test_tcn_and_model_freshness_follows_only_referenced_entities(self) -> None:
        value = condition_input()
        value["test_conditions"][0]["authority_refs"] = ["SPEC-001"]
        value["test_conditions"][0]["risk_refs"] = ["R-001"]
        sources = current_sources()
        old_result = run_script(CONDITION_SCRIPT, request_for(value, sources))
        self.assertEqual(old_result["runtime_status"], "ok", old_result)
        outputs = [
            {**row, "runtime_dependencies": []}
            for row in old_result["payload"]["entities"]
        ]
        old_tcn = next(row for row in outputs if row["entity_type"] == "tcn")
        old_model = next(row for row in outputs if row["entity_type"] == "model")

        replacements = [
            (
                runtime.make_machine_entity(
                    "test-requirement-design",
                    "tr",
                    "TR-001",
                    {"tr_id": "TR-001", "text": "changed TR"},
                ),
                "stale",
                "stale",
            ),
            (
                runtime.make_machine_entity(
                    "spec-analysis",
                    "authority",
                    "SPEC-001",
                    {"authority_id": "SPEC-001", "text": "changed authority"},
                ),
                "stale",
                "stale",
            ),
            (
                runtime.make_machine_entity(
                    "test-analysis",
                    "product_risk",
                    "R-001",
                    {"risk_id": "R-001", "text": "changed risk"},
                ),
                "stale",
                "stale",
            ),
            (
                runtime.make_machine_entity(
                    "test-analysis",
                    "technique_selection",
                    "SEL-001",
                    {
                        "selection_key": "SEL-001",
                        "selected_techniques": ["ep"],
                        "text": "changed selection",
                    },
                ),
                "current",
                "stale",
            ),
            (
                runtime.make_machine_entity(
                    "test-analysis",
                    "technique_selection",
                    "SEL-UNRELATED",
                    {"selection_key": "SEL-UNRELATED", "text": "unrelated"},
                ),
                "current",
                "current",
            ),
        ]
        for replacement, expected_tcn, expected_model in replacements:
            with self.subTest(replacement=replacement["entity_ref"]):
                current_sources_rows = [
                    row
                    for row in sources
                    if (row["skill"], row["entity_type"], row["entity_ref"])
                    != (
                        replacement["skill"],
                        replacement["entity_type"],
                        replacement["entity_ref"],
                    )
                ]
                current_sources_rows.append(replacement)
                freshness = runtime.evaluate_entity_freshness(
                    [*current_sources_rows, old_tcn, old_model], {}
                )
                states = {
                    (row["entity_type"], row["entity_ref"]): row["freshness_status"]
                    for row in freshness
                }
                self.assertEqual(states[("tcn", "TCN-001")], expected_tcn)
                self.assertEqual(states[("model", "ep-001")], expected_model)

    def test_direct_analysis_selection_is_optional_and_current_selection_is_recorded(
        self,
    ) -> None:
        value = condition_input()
        sources = current_sources()
        missing_selection = [
            row for row in sources if row["entity_type"] != "technique_selection"
        ]
        direct = condition_metadata()
        direct["upstream_entities"] = [
            {
                "skill": row["skill"],
                "entity_type": row["entity_type"],
                "entity_ref": row["entity_ref"],
                "content": row["content"],
            }
            for row in missing_selection
        ]
        result = run_script(CONDITION_SCRIPT, {"metadata": direct, "input": value})
        self.assertEqual(result["runtime_status"], "ok", result)
        model = next(
            row
            for row in result["payload"]["entities"]
            if row["entity_type"] == "model"
        )
        self.assertNotIn(
            ("test-analysis", "technique_selection", "SEL-001"),
            {
                (row["skill"], row["entity_type"], row["entity_ref"])
                for row in model["upstream_entity_dependencies"]
            },
        )

        direct_value = condition_input()
        direct = condition_metadata()
        result = run_script(
            CONDITION_SCRIPT, {"metadata": direct, "input": direct_value}
        )
        self.assertEqual(result["runtime_status"], "ok", result)

        selection = next(
            row for row in sources if row["entity_type"] == "technique_selection"
        )
        direct["upstream_entities"] = [
            {
                "skill": selection["skill"],
                "entity_type": selection["entity_type"],
                "entity_ref": selection["entity_ref"],
                "content": selection["content"],
            }
        ]
        result = run_script(
            CONDITION_SCRIPT, {"metadata": direct, "input": direct_value}
        )
        self.assertEqual(result["runtime_status"], "ok", result)
        model = next(
            row
            for row in result["payload"]["entities"]
            if row["entity_type"] == "model"
        )
        self.assertIn(
            {
                "skill": selection["skill"],
                "entity_type": selection["entity_type"],
                "entity_ref": selection["entity_ref"],
                "content_fingerprint": selection["content_fingerprint"],
            },
            model["upstream_entity_dependencies"],
        )

        artifact = request_for(condition_input(), missing_selection)
        self.assertEqual(
            run_script(CONDITION_SCRIPT, artifact)["runtime_status"], "invalid_input"
        )
        artifact = request_for(condition_input(), sources)
        self.assertEqual(run_script(CONDITION_SCRIPT, artifact)["runtime_status"], "ok")

        value["models"].insert(
            0,
            {
                "draft_key": "adapter",
                "model_type": "classification",
                "technique_slug": None,
                "selection_source": None,
                "selection_key": None,
                "derived_from_model_draft_key": None,
                "identity_action": "new",
                "reuse_model_key": None,
                "parent_tcn_draft_key": "tcn-draft",
            },
        )
        value["models"][1]["derived_from_model_draft_key"] = "adapter"
        result = run_script(CONDITION_SCRIPT, request_for(value, sources))
        self.assertEqual(result["runtime_status"], "ok", result)
        models = [
            row
            for row in result["payload"]["entities"]
            if row["entity_type"] == "model"
        ]
        child = next(row for row in models if row["entity_ref"] == "ep-001")
        adapter = next(
            row for row in models if row["entity_ref"] == "classification-001"
        )
        tcn = next(
            row for row in result["payload"]["entities"] if row["entity_type"] == "tcn"
        )
        self.assertIn(
            {
                "skill": adapter["skill"],
                "entity_type": "model",
                "entity_ref": adapter["entity_ref"],
                "content_fingerprint": adapter["content_fingerprint"],
            },
            child["upstream_entity_dependencies"],
        )

        changed_adapter = runtime.make_machine_entity(
            "test-condition-design",
            "model",
            adapter["entity_ref"],
            {**adapter["content"], "derived_from_model_key": "classification-999"},
            model_key=adapter["entity_ref"],
        )
        child_without_runtime_deps = {**child, "runtime_dependencies": []}
        freshness = runtime.evaluate_entity_freshness(
            [
                *sources,
                {**tcn, "runtime_dependencies": []},
                changed_adapter,
                child_without_runtime_deps,
            ],
            {},
        )
        child_status = next(
            row["freshness_status"]
            for row in freshness
            if row["entity_type"] == "model" and row["entity_ref"] == "ep-001"
        )
        self.assertEqual(child_status, "stale")


if __name__ == "__main__":
    unittest.main()
