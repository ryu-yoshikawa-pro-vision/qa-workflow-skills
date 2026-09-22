from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import unittest


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "skills" / "test-condition-design" / "scripts" / "grammar_cases.py"


def metadata() -> dict:
    return {
        "envelope_version": "1", "skill": "test-condition-design", "runtime_contract_version": "runtime-v1", "generator_contract_version": "grammar-cases-v1",
        "runtime_unit_key": "model:syntax-001", "model_key": "syntax-001", "model_type": "syntax", "technique_slug": "syntax", "selection_source": "condition_design", "selection_key": None,
        "scope_key": None, "input_mode": "direct", "upstream_entities": [], "upstream_runtime_units": [], "static_data_versions": {}, "authority_refs": [], "reference_refs": [],
    }


def run(value: dict) -> dict:
    result = subprocess.run([sys.executable, str(SCRIPT)], input=json.dumps({"metadata": metadata(), "input": value}, ensure_ascii=False).encode(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=REPO_ROOT, check=False)
    if result.stderr:
        raise AssertionError(result.stderr.decode())
    return json.loads(result.stdout)


def grammar(mutations=None, max_depth=2):
    return {
        "input_label": "command",
        "start": "S",
        "productions": [
            {"production_key": "P-001", "lhs": "S", "rhs": [{"nonterminal": "A"}]},
            {"production_key": "P-002", "lhs": "A", "rhs": [{"terminal": "a"}]},
            {"production_key": "P-003", "lhs": "A", "rhs": [{"terminal": "b"}]},
        ],
        "max_depth": max_depth,
        "mutations": mutations or [],
    }


class GrammarCasesRuntimeTests(unittest.TestCase):
    def test_leftmost_shortest_production_cases_and_explicit_mutation(self) -> None:
        value = grammar([{"mutation_key": "M-001", "op": "replace_terminal", "production_key": "P-002", "symbol_index": 0, "value": "x"}])
        result = run(value)
        self.assertEqual(result["runtime_status"], "ok")
        self.assertEqual(result["result_status"], "ready")
        self.assertEqual(result["payload"]["coverage_summary"], {"criterion": "production-coverage", "required": 3, "covered": 3, "complete": True})
        prod_targets = [row for row in result["payload"]["targets"] if row["target_key"].startswith("syntax:prod:")]
        self.assertEqual([row["execution"]["input_text"] for row in prod_targets], ["a", "a", "b"])
        mutation = next(row for row in result["payload"]["targets"] if row["target_key"] == "syntax:mutation:M-001")
        self.assertTrue(mutation["invalid_candidate"])
        self.assertEqual(mutation["execution"]["input_text"], "x")

    def test_unreachable_production_is_an_unresolved_blocking_issue_and_not_silently_dropped(self) -> None:
        value = grammar()
        value["productions"].append({"production_key": "P-004", "lhs": "Z", "rhs": [{"terminal": "z"}]})
        result = run(value)
        self.assertEqual(result["result_status"], "unresolved")
        self.assertEqual(result["payload"]["coverage_summary"]["required"], 4)
        self.assertEqual(result["payload"]["coverage_summary"]["covered"], 3)
        self.assertEqual(result["issues"][-1]["issue_type"], "unreachable_production")
        target = next(row for row in result["payload"]["targets"] if row["target_key"] == "syntax:prod:P-004")
        self.assertFalse(target["materializable"])

    def test_delete_or_replace_nonterminal_is_invalid_input(self) -> None:
        value = grammar([{"mutation_key": "M-001", "op": "delete_terminal", "production_key": "P-001", "symbol_index": 0}])
        self.assertEqual(run(value)["runtime_status"], "invalid_input")


if __name__ == "__main__":
    unittest.main()
