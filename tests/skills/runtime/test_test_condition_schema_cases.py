from __future__ import annotations

import json
import hashlib
import re
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

    def test_derived_test_data_requirements_come_from_same_parameterized_schema_run(self) -> None:
        value = {
            "schema_kind": "json-schema-2020-12", "schema_pointer": "#", "context": "validation",
            "document": {"type": "object", "properties": {"role": {"enum": ["admin", "user"]}, "age": {"type": "integer", "minimum": 1, "maximum": 5}}, "required": ["role"]},
            "child_models": [{"child_model_key": "bva-child", "model_type": "bva", "derived_from_model_key": "schema-001", "semantic_parameters": None}],
        }
        first = run(value)
        boundaries = first["payload"]["bva_skeletons"]
        value["child_models"][0]["semantic_parameters"] = {"boundaries": [{"boundary_key": row["boundary_key"], "mode": "2-value", "coverage_selection_reason": ""} for row in boundaries]}
        rerun = run(value)
        self.assertEqual(rerun["result_status"], "ready")
        self.assertEqual(len(rerun["payload"]["derived_child_inputs"]), 1)
        requirements = rerun["payload"]["derived"]["test_data_requirements"]
        self.assertEqual({row["operator"] for row in requirements}, {"enum", "range", "boolean"})
        self.assertTrue(all(row["source_model_key"] == "schema-001" and row["source_target_versions"] == [] for row in requirements))
        self.assertTrue(all(re.fullmatch(r"h[0-9a-f]{64}", row["requirement_key"]) for row in requirements))
        self.assertTrue(all(re.fullmatch(r"h[0-9a-f]{64}", row["dimension_key"]) for row in requirements))
        self.assertTrue(any(row["operator"] == "enum" and row["values"] == [{"type": "string", "value": "admin"}, {"type": "string", "value": "user"}] for row in requirements))
        self.assertTrue(any(row["operator"] == "range" and row["minimum"] == {"type": "integer", "value": 1} and row["maximum"] == {"type": "integer", "value": 5} for row in requirements))
        self.assertTrue(any(row["operator"] == "boolean" and row["value"] is True for row in requirements))

    def test_min_max_properties_are_supported_and_reversed_range_is_invalid(self) -> None:
        base = {"schema_kind": "json-schema-2020-12", "schema_pointer": "#", "context": "validation", "child_models": []}
        for document, keywords in (({"type": "object", "minProperties": 1}, {"minProperties"}), ({"type": "object", "maxProperties": 3}, {"maxProperties"}), ({"type": "object", "minProperties": 1, "maxProperties": 3}, {"minProperties", "maxProperties"})):
            with self.subTest(keywords=keywords):
                result = run({**base, "document": document})
                self.assertEqual(result["runtime_status"], "ok")
                self.assertFalse(result["payload"]["unsupported_items"])
                self.assertEqual({row["keyword"] for row in result["payload"]["bva_skeletons"]}, keywords)
        invalid = run({**base, "document": {"type": "object", "minProperties": 4, "maxProperties": 2}})
        self.assertEqual(invalid["runtime_status"], "invalid_input")

    def test_openapi_read_only_and_write_only_filter_by_request_or_response_context(self) -> None:
        document = {"type": "object", "required": ["read", "write"], "properties": {"read": {"type": "string", "readOnly": True}, "write": {"type": "string", "writeOnly": True}}}
        request = run({"schema_kind": "openapi-3.0", "schema_pointer": "#", "context": "request", "document": document, "child_models": []})
        response = run({"schema_kind": "openapi-3.0", "schema_pointer": "#", "context": "response", "document": document, "child_models": []})
        request_refs = {row["requirement_key"] for row in request["payload"]["derived"]["test_data_requirements"]}
        response_refs = {row["requirement_key"] for row in response["payload"]["derived"]["test_data_requirements"]}
        read_key = "h" + hashlib.sha256(json.dumps({"schema_kind": "openapi-3.0", "schema_pointer": "#/properties/read", "keyword": "required", "role": "test-data-requirement"}, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        write_key = "h" + hashlib.sha256(json.dumps({"schema_kind": "openapi-3.0", "schema_pointer": "#/properties/write", "keyword": "required", "role": "test-data-requirement"}, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        self.assertNotIn(read_key, request_refs)
        self.assertIn(write_key, request_refs)
        self.assertIn(read_key, response_refs)
        self.assertNotIn(write_key, response_refs)

    def test_unsupported_property_does_not_erase_independent_supported_property(self) -> None:
        result = run({
            "schema_kind": "json-schema-2020-12", "schema_pointer": "#", "context": "validation",
            "document": {"type": "object", "properties": {"external": {"$ref": "https://example.invalid/schema"}, "role": {"enum": ["admin", "user"]}}},
            "child_models": [],
        })
        self.assertEqual(result["runtime_status"], "ok")
        self.assertEqual(result["support_status"], "partial")
        self.assertTrue(result["payload"]["unsupported_items"])
        self.assertEqual(len(result["payload"]["ep_skeletons"]), 1)
        self.assertTrue(any(row["operator"] == "enum" for row in result["payload"]["derived"]["test_data_requirements"]))


if __name__ == "__main__":
    unittest.main()
