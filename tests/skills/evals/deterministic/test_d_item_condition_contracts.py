from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

from scripts.skills.evals.deterministic.markdown_parser import parse_tables
from scripts.skills.evals.deterministic.run import grade

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


def drop_last_cell_of_first_table_row(output: str) -> str:
    """Make the first table's first data row one column short."""
    lines = output.splitlines()
    for index in range(len(lines) - 2):
        if lines[index].lstrip().startswith("|") and set(
            lines[index + 1].replace("|", "").replace(":", "").replace(" ", "")
        ) == {"-"}:
            cells = lines[index + 2].rstrip().rstrip("|").rsplit("|", 1)[0]
            lines[index + 2] = cells + "|"
            return "\n".join(lines) + "\n"
    raise AssertionError("no table found")


def assertion_status(result, assertion_id: str) -> str:
    return next(row.status for row in result.assertions if row.id == assertion_id)


class ItemConditionOutputContractTests(unittest.TestCase):
    def test_malformed_markdown_table_is_a_failed_evaluation_not_an_exception(self):
        for skill, eval_id, assertion_id in (
            ("test-item-analysis", "ITEM-OUT-001", "ITEM-D010"),
            ("test-condition-analysis", "COND-OUT-001", "COND-D010"),
        ):
            with self.subTest(skill=skill):
                validate = load_validator(skill)
                output, expected = output_case(skill, eval_id)
                self.assertEqual(validate(output, expected, eval_id).status, "pass")
                broken = drop_last_cell_of_first_table_row(output)
                with self.assertRaises(ValueError):
                    parse_tables(broken)
                result = validate(broken, expected, eval_id)
                self.assertEqual(result.status, "fail")
                self.assertEqual(assertion_status(result, assertion_id), "fail")
                failed = next(
                    row for row in result.assertions if row.id == assertion_id
                )
                self.assertIn("column count mismatch", failed.evidence)

    def test_common_runner_reports_malformed_table_as_fail(self):
        for skill, eval_id in (
            ("test-item-analysis", "ITEM-OUT-001"),
            ("test-condition-analysis", "COND-OUT-001"),
        ):
            with self.subTest(skill=skill):
                output, _ = output_case(skill, eval_id)
                with tempfile.TemporaryDirectory() as directory:
                    path = Path(directory) / "output.md"
                    path.write_text(
                        drop_last_cell_of_first_table_row(output), encoding="utf-8"
                    )
                    graded = grade(skill, eval_id, path)
                self.assertEqual(graded["status"], "fail")

    def test_item_output_checks_expected_status_per_item(self):
        validate = load_validator("test-item-analysis")
        output, expected = output_case("test-item-analysis", "ITEM-OUT-001")
        self.assertEqual(expected["expected_status"]["ITEM-002"], "planned")

        # ITEM-002 drifting from planned to another *allowed* status is caught.
        drifted = replace_row_cell(output, "| ITEM-002 | 注文CSV", 5, "implemented")
        result = validate(drifted, expected, "ITEM-OUT-001")
        self.assertEqual(assertion_status(result, "ITEM-D004"), "fail")
        failed = next(row for row in result.assertions if row.id == "ITEM-D004")
        self.assertEqual(
            failed.evidence["expected_mismatch"],
            [{"item_id": "ITEM-002", "expected": "planned", "actual": "implemented"}],
        )
        self.assertEqual(failed.evidence["invalid"], [])

        # A status outside the allowed set still fails as before.
        invalid = replace_row_cell(output, "| ITEM-002 | 注文CSV", 5, "done")
        invalid_result = validate(invalid, expected, "ITEM-OUT-001")
        self.assertEqual(assertion_status(invalid_result, "ITEM-D004"), "fail")
        self.assertEqual(
            next(
                row for row in invalid_result.assertions if row.id == "ITEM-D004"
            ).evidence["invalid"],
            ["ITEM-002"],
        )

        # Items without an expected status keep the existing allowed-set contract.
        relaxed = {**expected, "expected_status": {"ITEM-001": "implemented"}}
        self.assertEqual(
            assertion_status(validate(drifted, relaxed, "ITEM-OUT-001"), "ITEM-D004"),
            "pass",
        )
        without = {k: v for k, v in expected.items() if k != "expected_status"}
        self.assertEqual(
            assertion_status(validate(drifted, without, "ITEM-OUT-001"), "ITEM-D004"),
            "pass",
        )

        # An expected item that is missing from the output is a mismatch, not a pass.
        missing = {**expected, "expected_status": {"ITEM-009": "planned"}}
        missing_result = validate(output, missing, "ITEM-OUT-001")
        self.assertEqual(assertion_status(missing_result, "ITEM-D004"), "fail")

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
