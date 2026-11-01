from __future__ import annotations

import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from scripts.skills.evals.deterministic import run
from scripts.skills.evals.deterministic.markdown_parser import (
    MarkdownTableParseError,
    parse_tables,
)


def _valid_requirement_structure_evidence() -> str:
    skill = "test-requirement-design"
    runtime_unit_key = "artifact:requirement_structure:all"
    metadata = {
        "envelope_version": "1",
        "skill": skill,
        "runtime_contract_version": "runtime-v2",
        "generator_contract_version": "requirement-structure-v2",
        "runtime_unit_key": runtime_unit_key,
        "model_key": None,
        "model_type": None,
        "technique_slug": None,
        "selection_source": None,
        "selection_key": None,
        "scope_key": "all",
        "input_mode": "direct",
        "upstream_entities": [],
        "upstream_runtime_units": [],
        "static_data_versions": {},
        "authority_refs": [],
        "reference_refs": [],
    }
    input_value = {
        "authorities": [],
        "risks": [],
        "acceptance_criteria": [],
        "scope_ids": [],
        "test_requirements": [],
        "dispositions": [],
        "previous_tr_ids": [],
        "update_scope_tr_ids": [],
        "inactive_tr_ids": [],
        "inactive_tr_history": [],
        "zero_scope_terminal": False,
    }
    repo_root = run.REPO_ROOT
    script = repo_root / "skills" / skill / "scripts" / "requirement_structure.py"
    completed = subprocess.run(
        [sys.executable, str(script)],
        input=json.dumps({"metadata": metadata, "input": input_value}).encode(),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=repo_root,
        check=False,
    )
    if completed.returncode != 0 or completed.stderr:
        raise AssertionError(completed.stderr.decode("utf-8", errors="replace"))
    runtime_result = json.loads(completed.stdout)

    def fence(value: object) -> str:
        rendered = json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
        return f"```json\n{rendered}\n```"

    identity = f"{skill}::{runtime_unit_key}"
    entities = {
        "schema_version": "entity-state-v2",
        "skill": skill,
        "entities": runtime_result["payload"]["entities"],
    }
    return "\n".join(
        [
            f"### Machine Runtime Input: {identity}",
            "",
            fence({"metadata": metadata, "input": input_value}),
            f"### Machine Runtime Result: {identity}",
            "",
            fence(runtime_result),
            f"### Machine Entities: {skill}",
            "",
            fence(entities),
            "",
        ]
    )


class MarkdownParserTests(unittest.TestCase):
    def test_parser_supports_escaped_pipe(self) -> None:
        tables = parse_tables("""## T
| A | B |
| --- | --- |
| x\\|y | z |
""")
        self.assertEqual(tables[0].rows[0]["A"], "x|y")

    def test_parser_rejects_column_mismatch(self) -> None:
        with self.assertRaisesRegex(
            MarkdownTableParseError,
            "section 'T' row 1: headers=2 cells=3",
        ):
            parse_tables("""## T
| A | B |
| --- | --- |
| 1 | 2 | 3 |
""")

    def test_parser_rejects_separator_column_mismatch(self) -> None:
        with self.assertRaisesRegex(
            MarkdownTableParseError, "separator column count mismatch"
        ):
            parse_tables("""## T
| A | B |
| --- |
""")

    def test_parser_rejects_blank_line_between_header_and_separator(self) -> None:
        with self.assertRaisesRegex(
            MarkdownTableParseError,
            "header and separator rows must be adjacent in section 'T'",
        ):
            parse_tables("""## T
| A | B |

| --- | --- |
| 1 | 2 |
""")

    def test_parser_accepts_dprint_short_separator_cells(self) -> None:
        tables = parse_tables("""## T
| A | B |
| -- | --- |
| 1 | 2 |
""")
        self.assertEqual(tables[0].rows[0], {"A": "1", "B": "2"})

    def test_malformed_case_fails_without_stopping_batch(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_root = Path(temp_dir)
            question_path = output_root / "question-analysis/QUESTION-OUT-002.md"
            question_path.parent.mkdir(parents=True)
            question_path.write_text(
                """## 仮定候補
| 仮定候補 | 状態 | 根拠 / 理由 | 影響範囲 | 正式ASM ID |
| --- | --- | --- | --- | --- |
| 候補 | 提案 | 根拠 | 範囲 |
""",
                encoding="utf-8",
            )
            regression_path = output_root / "regression-testing/REG-OUT-002.md"
            regression_path.parent.mkdir(parents=True)
            canonical_regression_output = (
                run.REPO_ROOT
                / "skills/regression-testing/evals/output/cases/reg-out-002/output.md"
            )
            shutil.copyfile(canonical_regression_output, regression_path)

            stdout = io.StringIO()
            with (
                patch.object(
                    sys,
                    "argv",
                    ["run.py", "--skill", "all", "--output-root", str(output_root)],
                ),
                redirect_stdout(stdout),
            ):
                return_code = run.main()

            payload = json.loads(stdout.getvalue())
            results = {
                (item["skill"], item["eval_id"]): item for item in payload["results"]
            }
            malformed = results[("question-analysis", "QUESTION-OUT-002")]
            self.assertEqual(return_code, 1)
            self.assertEqual(malformed["status"], "fail")
            self.assertEqual(malformed["assertions"][0]["id"], "OUTPUT-MD-TABLE-001")
            self.assertIn(("regression-testing", "REG-OUT-002"), results)

    def test_private_expected_json_grades_a_held_out_single_case(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            output = root / "output.md"
            output.write_text(
                """# テスト要求
## テスト要求一覧
| テスト要求ID | 関連AC ID | テスト要求 | 現在有効な仕様根拠 | 関連プロダクトリスク | 優先度 | テストレベル / 観測方法 | 備考 |
| --- | --- | --- | --- | --- | --- | --- | --- |
## テスト要求を作らない上流項目
| 上流ID | 種別 | 扱い | 理由 / 根拠 |
| --- | --- | --- | --- |
"""
                + _valid_requirement_structure_evidence(),
                encoding="utf-8",
            )
            expected = root / "expected.json"
            expected.write_text(
                json.dumps(
                    {
                        "known_authorities": [],
                        "known_acceptance_criteria": [],
                        "known_product_risks": [],
                        "expected_no_test_requirements": True,
                    }
                ),
                encoding="utf-8",
            )
            result_path = root / "result.json"
            stdout = io.StringIO()
            with (
                patch.object(
                    sys,
                    "argv",
                    [
                        "run.py",
                        "--skill",
                        "test-requirement-design",
                        "--eval-id",
                        "TR-HELDOUT-006",
                        "--output",
                        str(output),
                        "--expected-json",
                        str(expected),
                        "--result",
                        str(result_path),
                    ],
                ),
                redirect_stdout(stdout),
            ):
                return_code = run.main()

            payload = json.loads(stdout.getvalue())
            assertion = next(
                item for item in payload["assertions"] if item["id"] == "TR-D019"
            )
            self.assertEqual(return_code, 0)
            self.assertEqual(assertion["status"], "pass")
            self.assertEqual(
                json.loads(result_path.read_text(encoding="utf-8")), payload
            )


if __name__ == "__main__":
    unittest.main()
