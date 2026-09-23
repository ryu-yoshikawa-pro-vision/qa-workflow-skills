from __future__ import annotations

import unittest

from tests.skills.runtime.test_ep_vertical_integration import CONDITION_SCRIPT, condition_input, condition_metadata, run_script, runtime


def current_sources():
    return [
        runtime.make_machine_entity("test-requirement-design", "tr", "TR-001", {"tr_id": "TR-001", "text": "current TR"}),
        runtime.make_machine_entity("spec-analysis", "authority", "SPEC-001", {"authority_id": "SPEC-001", "text": "current authority"}),
        runtime.make_machine_entity("test-analysis", "product_risk", "R-001", {"risk_id": "R-001", "text": "current risk"}),
        runtime.make_machine_entity("test-analysis", "technique_selection", "SEL-001", {"selection_key": "SEL-001", "selected_techniques": ["ep"]}),
    ]


def request_for(value: dict, source_entities: list[dict]) -> dict:
    metadata = condition_metadata()
    metadata["input_mode"] = "artifact"
    metadata["upstream_entities"] = [
        {"skill": row["skill"], "entity_type": row["entity_type"], "entity_ref": row["entity_ref"], "content": row["content"]}
        for row in source_entities
    ]
    return {"metadata": metadata, "input": value}


class ConditionStructureRuntimeTests(unittest.TestCase):
    def test_condition_structure_assigns_stable_tcn_and_model_state(self) -> None:
        value = condition_input()
        value["models"][0]["selection_source"] = "user"
        value["models"][0]["selection_key"] = None
        value["technique_selections"] = []
        result = run_script(CONDITION_SCRIPT, {"metadata": condition_metadata(), "input": value})
        self.assertEqual(result["runtime_status"], "ok")
        self.assertEqual(result["result_status"], "ready")
        self.assertEqual(result["payload"]["tcn_id_map"][0]["tcn_id"], "TCN-001")
        self.assertEqual(result["payload"]["active_model_metadata"][0]["model_key"], "ep-001")

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
            {(row["skill"], row["entity_type"], row["entity_ref"]) for row in tcn["upstream_entity_dependencies"]},
            {("test-requirement-design", "tr", "TR-001"), ("spec-analysis", "authority", "SPEC-001"), ("test-analysis", "product_risk", "R-001")},
        )
        self.assertEqual(
            {(row["skill"], row["entity_type"], row["entity_ref"]) for row in model["upstream_entity_dependencies"]},
            {("test-condition-design", "tcn", "TCN-001"), ("test-analysis", "technique_selection", "SEL-001")},
        )

    def test_tcn_disposition_uses_shared_current_entity_dependency_contract(self) -> None:
        sources = current_sources()
        first_tr = next(row for row in sources if row["entity_type"] == "tr")
        second_tr = runtime.make_machine_entity("test-requirement-design", "tr", "TR-002", {"tr_id": "TR-002", "text": "covered by existing TR"})
        sources.append(second_tr)
        value = condition_input()
        value["test_conditions"][0]["tr_refs"] = []
        value["requirement_dispositions"] = [{
            "upstream_entity": {key: first_tr[key] for key in ("skill", "entity_type", "entity_ref", "content_fingerprint")},
            "handling": "重複", "reason": "covered by TR-002", "authority_refs": [],
            "covered_by_entity": {key: second_tr[key] for key in ("skill", "entity_type", "entity_ref", "content_fingerprint")},
        }]
        result = run_script(CONDITION_SCRIPT, request_for(value, sources))
        self.assertEqual(result["runtime_status"], "ok", result)
        disposition = next(row for row in result["payload"]["entities"] if row["entity_type"] == "disposition")
        self.assertEqual(
            {(row["skill"], row["entity_type"], row["entity_ref"]): row["content_fingerprint"] for row in disposition["upstream_entity_dependencies"]},
            {
                ("test-requirement-design", "tr", "TR-001"): first_tr["content_fingerprint"],
                ("test-requirement-design", "tr", "TR-002"): second_tr["content_fingerprint"],
            },
        )

    def test_tcn_and_model_freshness_follows_only_referenced_entities(self) -> None:
        value = condition_input()
        value["test_conditions"][0]["authority_refs"] = ["SPEC-001"]
        value["test_conditions"][0]["risk_refs"] = ["R-001"]
        sources = current_sources()
        old_result = run_script(CONDITION_SCRIPT, request_for(value, sources))
        self.assertEqual(old_result["runtime_status"], "ok", old_result)
        outputs = [{**row, "runtime_dependencies": []} for row in old_result["payload"]["entities"]]
        old_tcn = next(row for row in outputs if row["entity_type"] == "tcn")
        old_model = next(row for row in outputs if row["entity_type"] == "model")

        replacements = [
            (runtime.make_machine_entity("test-requirement-design", "tr", "TR-001", {"tr_id": "TR-001", "text": "changed TR"}), "stale", "stale"),
            (runtime.make_machine_entity("spec-analysis", "authority", "SPEC-001", {"authority_id": "SPEC-001", "text": "changed authority"}), "stale", "stale"),
            (runtime.make_machine_entity("test-analysis", "product_risk", "R-001", {"risk_id": "R-001", "text": "changed risk"}), "stale", "stale"),
            (runtime.make_machine_entity("test-analysis", "technique_selection", "SEL-001", {"selection_key": "SEL-001", "selected_techniques": ["ep"], "text": "changed selection"}), "current", "stale"),
            (runtime.make_machine_entity("test-analysis", "technique_selection", "SEL-UNRELATED", {"selection_key": "SEL-UNRELATED", "text": "unrelated"}), "current", "current"),
        ]
        for replacement, expected_tcn, expected_model in replacements:
            with self.subTest(replacement=replacement["entity_ref"]):
                current_sources_rows = [row for row in sources if (row["skill"], row["entity_type"], row["entity_ref"]) != (replacement["skill"], replacement["entity_type"], replacement["entity_ref"])]
                current_sources_rows.append(replacement)
                freshness = runtime.evaluate_entity_freshness([*current_sources_rows, old_tcn, old_model], {})
                states = {(row["entity_type"], row["entity_ref"]): row["freshness_status"] for row in freshness}
                self.assertEqual(states[("tcn", "TCN-001")], expected_tcn)
                self.assertEqual(states[("model", "ep-001")], expected_model)

    def test_analysis_selection_and_adapter_parent_are_required_dependencies(self) -> None:
        value = condition_input()
        sources = current_sources()
        missing_selection = [row for row in sources if row["entity_type"] != "technique_selection"]
        result = run_script(CONDITION_SCRIPT, request_for(value, missing_selection))
        self.assertEqual(result["runtime_status"], "invalid_input")

        direct = condition_metadata()
        direct_value = condition_input()
        result = run_script(CONDITION_SCRIPT, {"metadata": direct, "input": direct_value})
        self.assertEqual(result["runtime_status"], "invalid_input")

        value["models"].insert(0, {
            "draft_key": "adapter", "model_type": "classification", "technique_slug": None, "selection_source": None, "selection_key": None,
            "derived_from_model_draft_key": None, "identity_action": "new", "reuse_model_key": None, "parent_tcn_draft_key": "tcn-draft",
        })
        value["models"][1]["derived_from_model_draft_key"] = "adapter"
        result = run_script(CONDITION_SCRIPT, request_for(value, sources))
        self.assertEqual(result["runtime_status"], "ok", result)
        models = [row for row in result["payload"]["entities"] if row["entity_type"] == "model"]
        child = next(row for row in models if row["entity_ref"] == "ep-001")
        adapter = next(row for row in models if row["entity_ref"] == "classification-001")
        tcn = next(row for row in result["payload"]["entities"] if row["entity_type"] == "tcn")
        self.assertIn({"skill": adapter["skill"], "entity_type": "model", "entity_ref": adapter["entity_ref"], "content_fingerprint": adapter["content_fingerprint"]}, child["upstream_entity_dependencies"])

        changed_adapter = runtime.make_machine_entity("test-condition-design", "model", adapter["entity_ref"], {**adapter["content"], "derived_from_model_key": "classification-999"}, model_key=adapter["entity_ref"])
        child_without_runtime_deps = {**child, "runtime_dependencies": []}
        freshness = runtime.evaluate_entity_freshness([*sources, {**tcn, "runtime_dependencies": []}, changed_adapter, child_without_runtime_deps], {})
        child_status = next(row["freshness_status"] for row in freshness if row["entity_type"] == "model" and row["entity_ref"] == "ep-001")
        self.assertEqual(child_status, "stale")


if __name__ == "__main__":
    unittest.main()
