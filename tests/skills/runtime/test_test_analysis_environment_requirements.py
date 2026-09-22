from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import unittest


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "skills" / "test-analysis" / "scripts" / "environment_requirements.py"


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
        self.assertEqual(result["result_status"], "ready")
        self.assertEqual(result["payload"]["conflicts"][0]["requirement_keys"], ["r-1", "r-2"])

    def test_unsupported_operator_is_explicit_and_wrong_fields_are_invalid(self) -> None:
        unsupported = base("r-1", "chrome", "regex", value={"type": "string", "value": "120"})
        self.assertEqual(run({"requirements": [unsupported]})["runtime_status"], "unsupported")
        invalid = base("r-1", "chrome", "eq", value={"type": "string", "value": "120"}, values=[{"type": "string", "value": "120"}])
        self.assertEqual(run({"requirements": [invalid]})["runtime_status"], "invalid_input")


if __name__ == "__main__":
    unittest.main()
