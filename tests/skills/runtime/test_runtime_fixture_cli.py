from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import unittest


REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURES = REPO_ROOT / "tests" / "skills" / "runtime" / "fixtures"


# This table is test-only dispatch metadata.  Production runtime dispatch stays
# in the caller-provided metadata contract; the fixtures deliberately contain
# only hand-written normalized inputs.
CONFIG = {
    "analysis_entities": ("test-analysis", "artifact:analysis_entities:all", None, None, "all", "direct", "analysis-entities-v1", "skills/test-analysis/scripts/analysis_entities.py"),
    "risk_matrix": ("test-analysis", "artifact:risk_matrix:all", None, None, "all", "direct", "risk-matrix-v1", "skills/test-analysis/scripts/risk_matrix.py"),
    "technique_candidates": ("test-analysis", "artifact:technique_candidates:selection-001", None, None, "selection-001", "direct", "technique-candidates-v1", "skills/test-analysis/scripts/technique_candidates.py"),
    "change_impact": ("test-analysis", "artifact:change_impact:all", None, None, "all", "direct", "change-impact-v1", "skills/test-analysis/scripts/change_impact.py"),
    "environment_requirements": ("test-analysis", "artifact:environment_requirements:all", None, None, "all", "direct", "environment-requirements-v1", "skills/test-analysis/scripts/environment_requirements.py"),
    "requirement_structure": ("test-requirement-design", "artifact:requirement_structure:all", None, None, "all", "direct", "requirement-structure-v1", "skills/test-requirement-design/scripts/requirement_structure.py"),
    "condition_structure": ("test-condition-design", "artifact:condition_structure:all", None, None, "all", "direct", "condition-structure-v1", "skills/test-condition-design/scripts/condition_structure.py"),
    "equivalence_partitions": ("test-condition-design", "model:ep-001", "ep-001", "ep", None, "direct", "equivalence-partitions-v1", "skills/test-condition-design/scripts/equivalence_partitions.py"),
    "bva": ("test-condition-design", "model:bva-001", "bva-001", "bva", None, "direct", "bva-v1", "skills/test-condition-design/scripts/bva.py"),
    "domain_testing": ("test-condition-design", "model:domain-001", "domain-001", "domain", None, "direct", "domain-testing-v1", "skills/test-condition-design/scripts/domain_testing.py"),
    "decision_table": ("test-condition-design", "model:decision-001", "decision-001", "decision", None, "direct", "decision-table-v1", "skills/test-condition-design/scripts/decision_table.py"),
    "cause_effect": ("test-condition-design", "model:cause-effect-001", "cause-effect-001", "cause-effect", None, "direct", "cause-effect-v1", "skills/test-condition-design/scripts/cause_effect.py"),
    "crud_matrix": ("test-condition-design", "model:crud-001", "crud-001", "crud", None, "direct", "crud-matrix-v1", "skills/test-condition-design/scripts/crud_matrix.py"),
    "grammar_cases": ("test-condition-design", "model:syntax-001", "syntax-001", "syntax", None, "direct", "grammar-cases-v1", "skills/test-condition-design/scripts/grammar_cases.py"),
    "combinatorial": ("test-condition-design", "model:comb-001", "comb-001", "comb", None, "direct", "combinatorial-v1", "skills/test-condition-design/scripts/combinatorial.py"),
    "classification_tree": ("test-condition-design", "model:classification-001", "classification-001", "classification", None, "direct", "classification-tree-v1", "skills/test-condition-design/scripts/classification_tree.py"),
    "state_transition": ("test-condition-design", "model:state-001", "state-001", "state", None, "direct", "state-transition-v1", "skills/test-condition-design/scripts/state_transition.py"),
    "flow_paths": ("test-condition-design", "model:flow-001", "flow-001", "flow", None, "direct", "flow-paths-v1", "skills/test-condition-design/scripts/flow_paths.py"),
    "random_testing": ("test-condition-design", "model:random-001", "random-001", "random", None, "direct", "random-testing-v1", "skills/test-condition-design/scripts/random_testing.py"),
    "metamorphic": ("test-condition-design", "model:metamorphic-001", "metamorphic-001", "metamorphic", None, "direct", "metamorphic-v1", "skills/test-condition-design/scripts/metamorphic.py"),
    "schema_cases": ("test-condition-design", "model:schema-001", "schema-001", "schema", None, "direct", "schema-cases-v1", "skills/test-condition-design/scripts/schema_cases.py"),
    "ui_pattern_candidates": ("test-condition-design", "model:ui-001", "ui-001", "ui", None, "direct", "ui-pattern-candidates-v1", "skills/test-condition-design/scripts/ui_pattern_candidates.py"),
    "test_data_requirements": ("test-condition-design", "artifact:test_data_requirements:all", None, None, "all", "artifact", "test-data-requirements-v1", "skills/test-condition-design/scripts/test_data_requirements.py"),
    "materialize_coverage": ("test-condition-design", "artifact:materialize_coverage:TCN-001", None, None, "TCN-001", "artifact", "materialize-coverage-v1", "skills/test-condition-design/scripts/materialize_coverage.py"),
    "case_structure": ("test-case-design", "artifact:case_structure:all", None, None, None, "direct", "case-structure-v1", "skills/test-case-design/scripts/case_structure.py"),
    "traceability": ("coverage-analysis", "artifact:traceability:all", None, None, "all", "artifact", "traceability-v1", "skills/coverage-analysis/scripts/traceability.py"),
    "workflow_runtime": ("qa-workflow", "artifact:workflow_runtime:all", None, None, "all", "artifact", "workflow-runtime-v1", "skills/qa-workflow/scripts/workflow_runtime.py"),
}


def metadata(config: tuple) -> dict:
    skill, unit, model_key, model_type, scope_key, input_mode, contract, _ = config
    technique = {
        "ep-001": "ep", "bva-001": "bva", "domain-001": "domain", "decision-001": "decision",
        "crud-001": "crud", "syntax-001": "syntax", "comb-001": "comb", "state-001": "state",
        "random-001": "random", "metamorphic-001": "metamorphic", "flow-001": "scenario",
    }.get(model_key)
    adapter = model_type in {"cause-effect", "classification", "schema", "ui"}
    upstream = []
    if unit == "artifact:materialize_coverage:TCN-001":
        model_content = {
            "derived_from_model_key": None, "model_key": "ep-001", "model_type": "ep", "parent_tcn_id": "TCN-001",
            "selection_key": "SEL-001", "selection_source": "analysis", "status": "active", "technique_slug": "ep",
        }
        upstream = [
            {"skill": "test-condition-design", "entity_type": "tcn", "entity_ref": "TCN-001", "content": {"tcn_id": "TCN-001"}},
            {"skill": "test-condition-design", "entity_type": "model", "entity_ref": "ep-001", "content": model_content},
        ]
    return {
        "envelope_version": "1", "skill": skill, "runtime_contract_version": "runtime-v1",
        "generator_contract_version": contract, "runtime_unit_key": unit, "model_key": model_key,
        "model_type": model_type, "technique_slug": None if adapter else technique,
        "selection_source": None if adapter or model_key is None else "condition_design", "selection_key": None,
        "scope_key": scope_key, "input_mode": input_mode, "upstream_entities": upstream,
        "upstream_runtime_units": [], "static_data_versions": {}, "authority_refs": [], "reference_refs": [],
    }


class RuntimeFixtureCliTests(unittest.TestCase):
    def test_all_handwritten_minimal_fixtures_round_trip_through_cli(self) -> None:
        self.assertEqual(set(CONFIG), {path.parent.name for path in FIXTURES.glob("*/valid_minimal.json") if path.parent.name != "authority_entities"})
        for name, config in CONFIG.items():
            fixture = json.loads((FIXTURES / name / "valid_minimal.json").read_text(encoding="utf-8"))
            request = {"metadata": metadata(config), "input": fixture}
            result = subprocess.run(
                [sys.executable, str(REPO_ROOT / config[-1])],
                input=json.dumps(request, ensure_ascii=False).encode("utf-8"),
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=REPO_ROOT, check=False,
            )
            self.assertEqual(result.returncode, 0, name)
            self.assertEqual(result.stderr, b"", name)
            envelope = json.loads(result.stdout)
            self.assertEqual(envelope["skill"], config[0], name)
            self.assertEqual(envelope["runtime_unit_key"], config[1], name)
            if name == "workflow_runtime" or name in {"bva", "domain_testing", "metamorphic"}:
                self.assertEqual(envelope["runtime_status"], "invalid_input", name)
            else:
                self.assertIn(envelope["runtime_status"], {"ok", "unsupported"}, name)
            self.assertIsNotNone(envelope["input_fingerprint"], name)

    def test_spec_authority_helper_has_a_direct_json_cli(self) -> None:
        fixture = (FIXTURES / "authority_entities" / "valid_minimal.json").read_bytes()
        script = REPO_ROOT / "skills/spec-analysis/scripts/authority_entities.py"
        result = subprocess.run([sys.executable, str(script)], input=fixture, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=REPO_ROOT, check=False)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stderr, b"")
        output = json.loads(result.stdout)
        self.assertEqual(output["skill"], "spec-analysis")
        self.assertEqual(output["entities"], [])


if __name__ == "__main__":
    unittest.main()
