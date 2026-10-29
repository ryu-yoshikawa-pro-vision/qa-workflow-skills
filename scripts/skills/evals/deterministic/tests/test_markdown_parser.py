from __future__ import annotations

import io
import json
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from scripts.skills.evals.deterministic.markdown_parser import (
    MarkdownTableParseError,
    parse_tables,
)
from scripts.skills.evals.deterministic import run


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
            with patch.object(
                sys,
                "argv",
                ["run.py", "--skill", "all", "--output-root", str(output_root)],
            ), redirect_stdout(stdout):
                return_code = run.main()

            payload = json.loads(stdout.getvalue())
            results = {
                (item["skill"], item["eval_id"]): item for item in payload["results"]
            }
            malformed = results[("question-analysis", "QUESTION-OUT-002")]
            self.assertEqual(return_code, 1)
            self.assertEqual(malformed["status"], "fail")
            self.assertEqual(
                malformed["assertions"][0]["id"], "OUTPUT-MD-TABLE-001"
            )
            self.assertIn(("regression-testing", "REG-OUT-002"), results)


if __name__ == "__main__":
    unittest.main()
