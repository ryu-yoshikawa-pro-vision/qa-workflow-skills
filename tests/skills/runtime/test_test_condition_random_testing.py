from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import unittest


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "skills" / "test-condition-design" / "scripts" / "random_testing.py"


def metadata() -> dict:
    return {
        "envelope_version": "1", "skill": "test-condition-design", "runtime_contract_version": "runtime-v1", "generator_contract_version": "random-testing-v1",
        "runtime_unit_key": "model:random-001", "model_key": "random-001", "model_type": "random", "technique_slug": "random", "selection_source": "condition_design", "selection_key": None,
        "scope_key": None, "input_mode": "direct", "upstream_entities": [], "upstream_runtime_units": [], "static_data_versions": {}, "authority_refs": [], "reference_refs": [],
    }


def run(value: dict) -> dict:
    result = subprocess.run([sys.executable, str(SCRIPT)], input=json.dumps({"metadata": metadata(), "input": value}, ensure_ascii=False).encode(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=REPO_ROOT, check=False)
    if result.stderr:
        raise AssertionError(result.stderr.decode())
    return json.loads(result.stdout)


class RandomTestingRuntimeTests(unittest.TestCase):
    def test_pcg32_fixed_raw_and_bounded_vectors(self) -> None:
        sys.path.insert(0, str(SCRIPT.parent))
        from random_testing import Pcg32
        raw = Pcg32(42)
        self.assertEqual([raw.next_uint32() for _ in range(6)], [2707161783, 2068313097, 3122475824, 2211639955, 3215226955, 3421331566])
        bounded = Pcg32(42)
        self.assertEqual([bounded.bounded_uint32(10) for _ in range(4)], [3, 7, 4, 5])
        bounded = Pcg32(42)
        self.assertEqual([bounded.bounded_uint32(2147483649) for _ in range(4)], [559678134, 974992175, 64156306, 1067743306])

    def test_distributions_are_reproducible_and_completion_is_count_based(self) -> None:
        value = {"input_label": "role", "seed": 42, "case_count": 5, "distribution": {"type": "uniform_finite", "values": [{"type": "enum", "value": "admin"}, {"type": "enum", "value": "user"}]}, "authority_refs": ["SPEC-001"], "reference_refs": []}
        first = run(value)
        second = run(value)
        self.assertEqual(first["payload"]["targets"], second["payload"]["targets"])
        self.assertEqual(first["payload"]["completion_summary"], {"required_case_count": 5, "generated_case_count": 5, "complete": True})
        integer = run({**value, "distribution": {"type": "uniform_integer", "minimum": -2, "maximum": 2}})
        self.assertTrue(all(row["value"]["type"] == "integer" for row in integer["payload"]["targets"]))
        categorical = run({**value, "distribution": {"type": "categorical", "entries": [{"value": {"type": "string", "value": "A"}, "weight": 3}, {"value": {"type": "string", "value": "B"}, "weight": 1}]}})
        self.assertEqual(categorical["runtime_status"], "ok")

    def test_distribution_validation_does_not_treat_bad_weight_or_range_as_random(self) -> None:
        base = {"input_label": "x", "seed": 0, "case_count": 1, "distribution": {"type": "categorical", "entries": [{"value": {"type": "string", "value": "A"}, "weight": 0}]}}
        self.assertEqual(run(base)["runtime_status"], "invalid_input")
        base["distribution"] = {"type": "uniform_integer", "minimum": 3, "maximum": 1}
        self.assertEqual(run(base)["runtime_status"], "invalid_input")


if __name__ == "__main__":
    unittest.main()
