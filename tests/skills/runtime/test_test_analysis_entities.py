from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import unittest


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "skills" / "test-analysis" / "scripts" / "analysis_entities.py"


def metadata() -> dict:
    return {
        "envelope_version": "1", "skill": "test-analysis", "runtime_contract_version": "runtime-v1", "generator_contract_version": "analysis-entities-v1",
        "runtime_unit_key": "artifact:analysis_entities:all", "model_key": None, "model_type": None, "technique_slug": None, "selection_source": None, "selection_key": None,
        "scope_key": "all", "input_mode": "direct", "upstream_entities": [], "upstream_runtime_units": [], "static_data_versions": {}, "authority_refs": [], "reference_refs": [],
    }


def run(value: dict) -> dict:
    result = subprocess.run([sys.executable, str(SCRIPT)], input=json.dumps({"metadata": metadata(), "input": value}, ensure_ascii=False).encode(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=REPO_ROOT, check=False)
    if result.stderr:
        raise AssertionError(result.stderr.decode())
    return json.loads(result.stdout)


def valid_input() -> dict:
    signals = {
        "ordered_domain": True, "explicit_boundaries": False, "equivalence_classes": False, "multiple_discrete_conditions": False,
        "stateful": None, "multiple_factors": False, "explicit_flow": False, "multi_variable_domain": False, "crud_model": False,
        "operational_profile": False, "metamorphic_relation": False, "grammar_model": False,
    }
    return {
        "test_analysis_context": {
            "scope": "checkout", "objectives": ["安全な購入"], "test_levels": ["system"], "environment_constraints": [],
            "exclusions": [], "blockers": [], "test_focus_items": ["境界"], "testability_decisions": ["自動化"], "residual_risks": [],
        },
        "product_risks": [{
            "risk_id": "R-001", "failure": "invalid total", "source_refs": [], "authority_refs": [], "impact": 4, "likelihood": 2,
            "assessment_reason": "high impact", "confidence_note": "reviewed",
        }],
        "technique_selections": [{
            "selection_key": "selection-001", "applicability_scope": "total", "selection_source": "analysis", "signals": signals,
            "selected_techniques": ["bva"], "selection_reason": "boundary", "risk_refs": ["R-001"], "authority_refs": [],
            "condition_design_focus": ["threshold"], "undetermined_signal_closures": [{"signal_key": "stateful", "handling": "selection_not_affected", "reason": "not stateful", "question_id": None}], "status": "active",
        }],
        "change_nodes": [{"node_key": "R-001", "node_type": "Risk", "source_ref": "risk:R-001", "change_kind": None, "expected_impact": None}],
        "change_edges": [],
        "environment_requirements": [{"requirement_key": "env-1", "environment_key": "chrome", "dimension_key": "browser", "operator": "eq", "value": {"type": "string", "value": "120"}, "authority_refs": [], "source_model_key": None, "source_target_versions": []}],
        "risk_matrix_results": [{"risk_id": "R-001", "level": "高", "mapped_priority": "高"}],
        "technique_candidate_results": [{"selection_key": "selection-001", "candidates": ["境界値分析"], "undetermined_signals": ["stateful"]}],
        "current_runtime_units": [
            {"skill": "test-analysis", "runtime_unit_key": "artifact:risk_matrix:all", "generation_fingerprint": "sha256:" + "1" * 64},
            {"skill": "test-analysis", "runtime_unit_key": "artifact:technique_candidates:selection-001", "generation_fingerprint": "sha256:" + "2" * 64},
        ],
    }


class AnalysisEntityRuntimeTests(unittest.TestCase):
    def test_fixed_join_preserves_meaning_fields_and_expected_identities(self) -> None:
        result = run(valid_input())
        self.assertEqual(result["runtime_status"], "ok")
        entities = result["payload"]["machine_entities"]
        risk = next(row for row in entities if row["entity_type"] == "product_risk")
        selection = next(row for row in entities if row["entity_type"] == "technique_selection")
        self.assertEqual(risk["content"]["mapped_priority"], "高")
        self.assertEqual(risk["content"]["assessment_reason"], "high impact")
        self.assertEqual(selection["content"]["candidates"], ["境界値分析"])
        self.assertEqual(selection["content"]["undetermined_signals"], ["stateful"])
        identities = {(row["entity_type"], row["entity_ref"]) for row in result["payload"]["expected_entity_identities"]}
        self.assertIn(("test_analysis_context", "analysis-context:all"), identities)
        self.assertIn(("product_risk", "R-001"), identities)
        self.assertIn(("environment_requirement", "env-1"), identities)

    def test_missing_join_row_is_invalid(self) -> None:
        value = valid_input()
        value["risk_matrix_results"] = []
        self.assertEqual(run(value)["runtime_status"], "invalid_input")

    def test_active_selection_cannot_hide_question_closure(self) -> None:
        value = valid_input()
        value["technique_selections"][0]["undetermined_signal_closures"][0] = {"signal_key": "stateful", "handling": "question", "reason": "need answer", "question_id": "Q-001"}
        self.assertEqual(run(value)["runtime_status"], "invalid_input")


if __name__ == "__main__":
    unittest.main()
