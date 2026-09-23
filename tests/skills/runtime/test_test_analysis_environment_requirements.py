from __future__ import annotations

import json
import importlib.util
from pathlib import Path
import re
import subprocess
import sys
import unittest


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "skills" / "test-analysis" / "scripts" / "environment_requirements.py"
RUNTIME_PATH = REPO_ROOT / "skills" / "test-analysis" / "scripts" / "runtime_contract.py"
SPEC = importlib.util.spec_from_file_location("environment_runtime_contract", RUNTIME_PATH)
assert SPEC is not None and SPEC.loader is not None
runtime = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = runtime
SPEC.loader.exec_module(runtime)


def metadata() -> dict:
    return {
        "envelope_version": "1", "skill": "test-analysis", "runtime_contract_version": "runtime-v1", "generator_contract_version": "environment-requirements-v1",
        "runtime_unit_key": "artifact:environment_requirements:all", "model_key": None, "model_type": None, "technique_slug": None, "selection_source": None, "selection_key": None,
        "scope_key": "all", "input_mode": "direct", "upstream_entities": [], "upstream_runtime_units": [], "static_data_versions": {}, "authority_refs": [], "reference_refs": [],
    }


def run(value: dict) -> dict:
    result = subprocess.run([sys.executable, str(SCRIPT)], input=json.dumps({"metadata": metadata(), "input": value}, ensure_ascii=False).encode(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=REPO_ROOT, check=False)
    if result.stderr:
        raise AssertionError(result.stderr.decode())
    return json.loads(result.stdout)


def base(key: str, environment: str, operator: str, **fields: object) -> dict:
    return {
        "requirement_key": key, "environment_key": environment, "dimension_key": "browser",
        "operator": operator, "authority_refs": [], "source_model_key": None, "source_target_versions": [], **fields,
    }


class EnvironmentRequirementRuntimeTests(unittest.TestCase):
    def test_same_environment_intersects_eq_and_enum_but_alternatives_do_not_conflict(self) -> None:
        rows = [
            base("r-1", "chrome", "eq", value={"type": "string", "value": "120"}),
            base("r-2", "chrome", "enum", values=[{"type": "string", "value": "119"}, {"type": "string", "value": "120"}]),
            base("r-3", "safari", "eq", value={"type": "string", "value": "17"}),
        ]
        result = run({"requirements": rows})
        self.assertEqual(result["runtime_status"], "ok")
        self.assertEqual(result["payload"]["conflicts"], [])
        self.assertEqual([row["requirement_key"] for row in result["payload"]["normalized_requirements"]], ["r-1", "r-2", "r-3"])

    def test_empty_intersection_is_reported_for_same_environment(self) -> None:
        rows = [
            base("r-1", "chrome", "eq", value={"type": "string", "value": "120"}),
            base("r-2", "chrome", "eq", value={"type": "string", "value": "121"}),
        ]
        result = run({"requirements": rows})
        self.assertEqual(result["runtime_status"], "ok")
        self.assertEqual(result["result_status"], "unresolved")
        self.assertTrue(any(issue["issue_type"] == "environment_conflict" and issue["blocking"] for issue in result["issues"]))
        self.assertEqual(result["payload"]["conflicts"][0]["requirement_keys"], ["r-1", "r-2"])

    def test_shared_range_and_version_intersection_rules(self) -> None:
        base_range = {"operator": "range", "minimum": {"type": "integer", "value": 1}, "maximum": {"type": "integer", "value": 5}, "minimum_inclusive": True, "maximum_inclusive": True}
        touching_exclusive = {**base_range, "minimum": {"type": "integer", "value": 5}, "maximum": {"type": "integer", "value": 8}, "minimum_inclusive": False}
        touching_inclusive = {**touching_exclusive, "minimum_inclusive": True}
        value = {"requirements": [base("r1", "chrome", "range", **{key: value for key, value in base_range.items() if key != "operator"}), base("r2", "chrome", "range", **{key: value for key, value in touching_exclusive.items() if key != "operator"})]}
        self.assertEqual(run(value)["result_status"], "unresolved")
        value["requirements"][1]["minimum_inclusive"] = True
        self.assertEqual(run(value)["payload"]["conflicts"], [])

        version_a = base("v1", "chrome", "version_range", minimum="1.0", maximum="2.0", minimum_inclusive=True, maximum_inclusive=True)
        version_b = base("v2", "chrome", "version_range", minimum="2.1", maximum="3.0", minimum_inclusive=True, maximum_inclusive=True)
        self.assertEqual(run({"requirements": [version_a, version_b]})["result_status"], "unresolved")

    def test_unsupported_operator_is_explicit_and_wrong_fields_are_invalid(self) -> None:
        unsupported = base("r-1", "chrome", "regex", value={"type": "string", "value": "120"})
        result = run({"requirements": [unsupported]})
        self.assertEqual(result["runtime_status"], "unsupported")
        item = result["payload"]["unsupported_items"][0]
        self.assertRegex(item["item_key"], r"^unsupported:environment_requirements:h[0-9a-f]{64}$")
        self.assertNotIn("sha256:", item["item_key"])
        self.assertEqual(run({"requirements": [unsupported]})["payload"]["unsupported_items"][0]["item_key"], item["item_key"])
        changed_source = {**unsupported, "requirement_key": "r-2"}
        changed = run({"requirements": [changed_source]})["payload"]["unsupported_items"][0]
        self.assertNotEqual(changed["item_key"], item["item_key"])
        changed_reason = runtime.make_unsupported_item(
            generator="environment_requirements", item_type="environment_requirement", source_key="r-1", reason_code="different_reason",
        )
        self.assertEqual(changed_reason["item_key"], item["item_key"])
        invalid = base("r-1", "chrome", "eq", value={"type": "string", "value": "120"}, values=[{"type": "string", "value": "120"}])
        self.assertEqual(run({"requirements": [invalid]})["runtime_status"], "invalid_input")


if __name__ == "__main__":
    unittest.main()
