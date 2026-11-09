from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]


def load_validator(skill: str):
    path = ROOT / "skills" / skill / "evals" / "deterministic" / "validator.py"
    spec = importlib.util.spec_from_file_location(
        f"{skill.replace('-', '_')}_d_validator", path
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.validate


def output_case(skill: str, eval_id: str) -> tuple[str, dict]:
    root = ROOT / "skills" / skill / "evals" / "output"
    manifest = json.loads((root / "evals.json").read_text(encoding="utf-8"))
    case = next(row for row in manifest["cases"] if row["id"] == eval_id)
    expected = json.loads((root / case["expected"]).read_text(encoding="utf-8"))
    reference = (root / case["input"]).parent / "reference.md"
    return reference.read_text(encoding="utf-8"), expected


def replace_row_cell(output: str, row_prefix: str, cell_index: int, value: str) -> str:
    lines = output.splitlines()
    for index, line in enumerate(lines):
        if line.startswith(row_prefix):
            cells = line.split("|")
            cells[cell_index + 1] = f" {value} "
            lines[index] = "|".join(cells)
            return "\n".join(lines) + "\n"
    raise AssertionError(f"table row not found: {row_prefix}")


class ItemConditionOutputContractTests(unittest.TestCase):
    def test_item_output_fixture_passes_independent_contract(self):
        validate = load_validator("test-item-analysis")
        output, expected = output_case("test-item-analysis", "ITEM-OUT-001")
        result = validate(output, expected, "ITEM-OUT-001")
        self.assertEqual(result.status, "pass")

    def test_item_output_rejects_zero_denominator_100_percent(self):
        validate = load_validator("test-item-analysis")
        output, expected = output_case("test-item-analysis", "ITEM-OUT-001")
        broken = replace_row_cell(
            output,
            "| Confirmed feature-to-item candidate identification",
            1,
            "not measured",
        )
        broken = replace_row_cell(
            broken,
            "| Confirmed feature-to-item candidate identification",
            2,
            "0",
        )
        broken = replace_row_cell(
            broken,
            "| Confirmed feature-to-item candidate identification",
            3,
            "0",
        )
        result = validate(broken, expected, "ITEM-OUT-001")
        status = next(row.status for row in result.assertions if row.id == "ITEM-D008")
        self.assertEqual(status, "fail")

    def test_condition_output_fixture_passes_and_formal_decision_fails(self):
        validate = load_validator("test-condition-analysis")
        output, expected = output_case("test-condition-analysis", "COND-OUT-001")
        self.assertEqual(validate(output, expected, "COND-OUT-001").status, "pass")
        broken = replace_row_cell(
            output,
            "| 未確定",
            2,
            "adopted",
        )
        result = validate(broken, expected, "COND-OUT-001")
        self.assertEqual(
            next(row.status for row in result.assertions if row.id == "COND-D008"),
            "fail",
        )

    def test_common_support_is_byte_identical_for_isolated_packages(self):
        item_support = (
            ROOT / "skills/test-item-analysis/scripts/candidate_support.py"
        ).read_bytes()
        condition_support = (
            ROOT / "skills/test-condition-analysis/scripts/candidate_support.py"
        ).read_bytes()
        self.assertEqual(item_support, condition_support)


if __name__ == "__main__":
    unittest.main()
