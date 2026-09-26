from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import unittest


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "skills" / "test-analysis" / "scripts" / "technique_candidates.py"
SIGNALS = [
    "ordered_domain", "explicit_boundaries", "equivalence_classes", "multiple_discrete_conditions", "stateful", "multiple_factors",
    "explicit_flow", "multi_variable_domain", "crud_model", "operational_profile", "metamorphic_relation", "grammar_model",
]


def metadata(key: str = "selection-001") -> dict:
    return {
        "envelope_version": "1", "skill": "test-analysis", "runtime_contract_version": "runtime-v1", "generator_contract_version": "technique-candidates-v1",
        "runtime_unit_key": f"artifact:technique_candidates:{key}", "model_key": None, "model_type": None, "technique_slug": None, "selection_source": None, "selection_key": None,
        "scope_key": key, "input_mode": "direct", "upstream_entities": [], "upstream_runtime_units": [], "static_data_versions": {}, "authority_refs": [], "reference_refs": [],
    }


def run(value: dict, key: str = "selection-001") -> dict:
    result = subprocess.run([sys.executable, str(SCRIPT)], input=json.dumps({"metadata": metadata(key), "input": value}, ensure_ascii=False).encode(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=REPO_ROOT, check=False)
    if result.stderr:
        raise AssertionError(result.stderr.decode())
    return json.loads(result.stdout)


class TechniqueCandidateRuntimeTests(unittest.TestCase):
    def test_all_signal_values_map_in_fixed_order_and_null_is_undetermined(self) -> None:
        signals = {key: False for key in SIGNALS}
        signals["ordered_domain"] = True
        signals["multi_variable_domain"] = True
        signals["stateful"] = None
        signals["grammar_model"] = None
        result = run({"selection_key": "selection-001", "signals": signals})
        self.assertEqual(result["runtime_status"], "ok")
        self.assertEqual(result["payload"]["candidates"], ["境界値分析", "Domain Testing"])
        self.assertEqual(result["payload"]["undetermined_signals"], ["stateful", "grammar_model"])
        self.assertFalse(result["payload"]["complete"])

    def test_missing_signal_and_colon_key_are_invalid(self) -> None:
        signals = {key: False for key in SIGNALS}
        signals.pop("grammar_model")
        self.assertEqual(run({"selection_key": "selection-001", "signals": signals})["runtime_status"], "invalid_input")
        self.assertEqual(run({"selection_key": "bad:key", "signals": {key: False for key in SIGNALS}}, "bad:key")["runtime_status"], "invalid_input")

    def test_resolving_signal_removes_it_from_undetermined(self) -> None:
        signals = {key: False for key in SIGNALS}
        signals["stateful"] = None
        unresolved = run({"selection_key": "selection-001", "signals": signals})
        signals["stateful"] = False
        resolved = run({"selection_key": "selection-001", "signals": signals})
        self.assertEqual(unresolved["payload"]["undetermined_signals"], ["stateful"])
        self.assertEqual(resolved["payload"]["undetermined_signals"], [])
        self.assertTrue(resolved["payload"]["complete"])


if __name__ == "__main__":
    unittest.main()
