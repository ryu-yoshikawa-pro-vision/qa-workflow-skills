from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import unittest


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "skills" / "test-condition-design" / "scripts" / "schema_cases.py"


def metadata() -> dict:
    return {
        "envelope_version": "1", "skill": "test-condition-design", "runtime_contract_version": "runtime-v1", "generator_contract_version": "schema-cases-v1",
        "runtime_unit_key": "model:schema-001", "model_key": "schema-001", "model_type": "schema", "technique_slug": None, "selection_source": None, "selection_key": None,
        "scope_key": None, "input_mode": "direct", "upstream_entities": [], "upstream_runtime_units": [], "static_data_versions": {}, "authority_refs": [], "reference_refs": [],
    }


def run(value: dict) -> dict:
    result = subprocess.run([sys.executable, str(SCRIPT)], input=json.dumps({"metadata": metadata(), "input": value}, ensure_ascii=False).encode(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=REPO_ROOT, check=False)
    if result.stderr:
        raise AssertionError(result.stderr.decode())
    return json.loads(result.stdout)


class SchemaCasesRuntimeTests(unittest.TestCase):
    def test_json_schema_enum_and_range_create_stable_child_skeletons(self) -> None:
        value = {
            "schema_kind": "json-schema-2020-12", "schema_pointer": "#", "context": "validation",
            "document": {"type": "object", "properties": {"age": {"type": "integer", "minimum": 0, "maximum": 120}, "role": {"enum": ["admin", "user"]}}, "required": ["age"]},
            "child_models": [
                {"child_model_key": "ep-child", "model_type": "ep", "derived_from_model_key": "schema-001", "semantic_parameters": None},
                {"child_model_key": "bva-child", "model_type": "bva", "derived_from_model_key": "schema-001", "semantic_parameters": None},
            ],
        }
        result = run(value)
        self.assertEqual(result["runtime_status"], "ok")
        self.assertEqual(result["result_status"], "unresolved")
        self.assertTrue(result["payload"]["ep_skeletons"])
        self.assertTrue(result["payload"]["bva_skeletons"])
        self.assertTrue(result["payload"]["semantic_parameter_requests"])
        self.assertTrue(result["payload"]["schema_targets"][0]["target_key"].startswith("schema:h"))

    def test_bva_parameters_produce_direct_child_input_and_html_disabled_is_not_fabricated(self) -> None:
        value = {
            "schema_kind": "html-control", "schema_pointer": "#", "context": "form-control",
            "document": {"type": "number", "required": True, "min": "1", "max": "3", "disabled": False, "readonly": False, "multiple": False},
            "child_models": [{"child_model_key": "bva-child", "model_type": "bva", "derived_from_model_key": "schema-001", "semantic_parameters": {"boundaries": []}}],
        }
        first = run({**value, "child_models": [{**value["child_models"][0], "semantic_parameters": None}]})
        boundaries = first["payload"]["bva_skeletons"]
        params = {"boundaries": [{"boundary_key": row["boundary_key"], "mode": "2-value", "coverage_selection_reason": ""} for row in boundaries]}
        value["child_models"][0]["semantic_parameters"] = params
        result = run(value)
        self.assertEqual(result["result_status"], "ready")
        self.assertEqual(len(result["payload"]["derived_child_inputs"]), 1)
        disabled = {**value, "document": {"type": "number", "disabled": True}, "child_models": [{**value["child_models"][0], "semantic_parameters": None}]}
        self.assertEqual(run(disabled)["result_status"], "unresolved")

    def test_external_ref_is_not_silently_treated_as_unconstrained(self) -> None:
        value = {"schema_kind": "json-schema-2020-12", "schema_pointer": "#", "context": "validation", "document": {"$ref": "https://example.invalid/schema"}, "child_models": [{"child_model_key": "ep-child", "model_type": "ep", "derived_from_model_key": "schema-001", "semantic_parameters": None}]}
        result = run(value)
        self.assertIn(result["runtime_status"], {"unsupported", "ok"})
        self.assertTrue(result["payload"].get("unsupported_items") or result["result_status"] == "unresolved")

    def test_schema_multiple_of_and_html_number_step_are_exact_grid_constraints(self) -> None:
        schema = {
            "schema_kind": "json-schema-2020-12", "schema_pointer": "#", "context": "validation",
            "document": {"type": "number", "multipleOf": 0.5, "minLength": 1, "maxLength": 3},
            "child_models": [],
        }
        schema_result = run(schema)
        grid = schema_result["payload"]["grid_constraints"]
        self.assertEqual(grid[0]["operator"], "grid")
        self.assertEqual(grid[0]["step"], {"type": "decimal", "value": "0.5"})
        self.assertEqual({row["keyword"] for row in schema_result["payload"]["bva_skeletons"]}, {"minLength", "maxLength"})

        html = {
            "schema_kind": "html-control", "schema_pointer": "#", "context": "form-control",
            "document": {"type": "number", "min": "1", "max": "3", "value": "1.5", "step": "0.5", "disabled": False, "readonly": False, "multiple": False},
            "child_models": [],
        }
        html_result = run(html)
        html_grid = html_result["payload"]["grid_constraints"][0]
        self.assertEqual(html_grid["base"], {"type": "decimal", "value": "1"})
        self.assertEqual(html_grid["step"], {"type": "decimal", "value": "0.5"})
        self.assertTrue(all(row["threshold"]["type"] == "decimal" for row in html_result["payload"]["bva_skeletons"]))

    def test_schema_cycle_uses_fixed_unsupported_reason_and_pointer_validation(self) -> None:
        cycle = {
            "schema_kind": "json-schema-2020-12", "schema_pointer": "#", "context": "validation",
            "document": {"$defs": {"node": {"$ref": "#/$defs/node"}}, "$ref": "#/$defs/node"}, "child_models": [],
        }
        result = run(cycle)
        self.assertTrue(result["payload"]["unsupported_items"])
        self.assertEqual(result["payload"]["unsupported_items"][0]["reason_code"], "cyclic_local_ref")
        malformed = {**cycle, "document": {"$ref": "#/%ZZ"}}
        invalid = run(malformed)
        self.assertEqual(invalid["runtime_status"], "invalid_input")


if __name__ == "__main__":
    unittest.main()
