from __future__ import annotations

import unittest

from scripts.skills.evals.deterministic.markdown_parser import parse_tables


class MarkdownParserTests(unittest.TestCase):
    def test_parser_supports_escaped_pipe(self) -> None:
        tables = parse_tables("""## T
| A | B |
| --- | --- |
| x\\|y | z |
""")
        self.assertEqual(tables[0].rows[0]["A"], "x|y")

    def test_parser_rejects_column_mismatch(self) -> None:
        with self.assertRaises(ValueError):
            parse_tables("""## T
| A | B |
| --- | --- |
| 1 | 2 | 3 |
""")


if __name__ == "__main__":
    unittest.main()
