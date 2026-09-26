from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import unittest


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "skills" / "test-analysis" / "scripts" / "risk_matrix.py"


def metadata() -> dict:
    return {
        "envelope_version": "1", "skill": "test-analysis", "runtime_contract_version": "runtime-v1", "generator_contract_version": "risk-matrix-v1",
        "runtime_unit_key": "artifact:risk_matrix:all", "model_key": None, "model_type": None, "technique_slug": None, "selection_source": None, "selection_key": None,
        "scope_key": "all", "input_mode": "direct", "upstream_entities": [], "upstream_runtime_units": [], "static_data_versions": {}, "authority_refs": [], "reference_refs": [],
    }


def run(value: dict) -> dict:
    result = subprocess.run([sys.executable, str(SCRIPT)], input=json.dumps({"metadata": metadata(), "input": value}, ensure_ascii=False).encode(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=REPO_ROOT, check=False)
    if result.stderr:
        raise AssertionError(result.stderr.decode())
    return json.loads(result.stdout)


class RiskMatrixRuntimeTests(unittest.TestCase):
    def test_repository_default_uses_fixed_matrix_and_mapped_priority(self) -> None:
        result = run({"scheme": {"kind": "repository-default", "scheme_key": "risk-scheme-v1"}, "risks": [
            {"risk_id": "R-002", "impact": 1, "likelihood": 4},
            {"risk_id": "R-001", "impact": 4, "likelihood": 4},
        ]})
        self.assertEqual(result["runtime_status"], "ok")
        self.assertEqual(result["payload"]["risks"], [
            {"risk_id": "R-001", "level": "高", "mapped_priority": "高"},
            {"risk_id": "R-002", "level": "中", "mapped_priority": "中"},
        ])

    def test_project_specific_matrix_requires_complete_mapping(self) -> None:
        scheme = {
            "kind": "project-specific", "scheme_key": "customer-risk-v1",
            "dimensions": {"impact": [1, 2], "likelihood": [1, 2]},
            "matrix": {"1,1": "L1", "1,2": "L2", "2,1": "L2", "2,2": "L3"},
            "priority_map": {"L1": "低", "L2": "中", "L3": "高"},
        }
        result = run({"scheme": scheme, "risks": [{"risk_id": "R-001", "impact": 2, "likelihood": 2}]})
        self.assertEqual(result["runtime_status"], "ok")
        self.assertEqual(result["payload"]["risks"][0]["mapped_priority"], "高")
        scheme["matrix"].pop("2,2")
        self.assertEqual(run({"scheme": scheme, "risks": []})["runtime_status"], "invalid_input")

    def test_legacy_string_scheme_is_rejected(self) -> None:
        result = run({"scheme": "repository-default", "risks": []})
        self.assertEqual(result["runtime_status"], "invalid_input")


if __name__ == "__main__":
    unittest.main()
