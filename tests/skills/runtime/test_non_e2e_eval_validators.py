"""Deterministic evaluation regression tests for non-E2E report contracts."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def validate(skill: str, text: str):
    path = ROOT / "skills" / skill / "evals/deterministic/validator.py"
    spec = importlib.util.spec_from_file_location(
        "non_e2e_" + skill.replace("-", "_"), path
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.validate(text, {}, "local-regression")


def fill_template(path: str) -> str:
    """Fill template tables with explicit evidence, not blank placeholder rows."""
    lines = (ROOT / path).read_text(encoding="utf-8").splitlines()
    for index, line in enumerate(lines):
        if line.startswith("|"):
            cells = line.strip("|").split("|")
            if all(not cell.strip() for cell in cells):
                lines[index] = "| " + " | ".join("fixture:根拠" for _ in cells) + " |"
        if line.startswith("- ") and line.rstrip().endswith("："):
            lines[index] = line + "fixture:記録"
    return "\n".join(lines) + "\n"


def status(result, key: str) -> str | None:
    return next(
        (item.status for item in result.assertions if item.id == key),
        None,
    )


class NonE2EOutputValidationTests(unittest.TestCase):
    def test_execution_requires_start_cleanup_and_diagnosis(self):
        report = fill_template("skills/testware-execution/assets/output-template.md")
        self.assertEqual(validate("testware-execution", report).status, "pass")
        incomplete = report.split("## 開始・直接観測／静的解析")[0]
        checked = validate("testware-execution", incomplete)
        self.assertEqual(checked.status, "fail")
        for code in ("TW-EXEC-D005", "TW-EXEC-D007", "TW-EXEC-D009"):
            self.assertEqual(status(checked, code), "fail")
        empty_cleanup = report.replace(
            "| fixture:根拠 | fixture:根拠 | fixture:根拠 | fixture:根拠 | fixture:根拠 |",
            "| fixture:根拠 | fixture:根拠 | | fixture:根拠 | fixture:根拠 |",
            1,
        )
        self.assertEqual(validate("testware-execution", empty_cleanup).status, "fail")

    def test_implementation_requires_testware_and_handoff(self):
        report = fill_template("skills/testware-implementation/assets/output-template.md")
        self.assertEqual(validate("testware-implementation", report).status, "pass")
        incomplete = report.split("## testwareと検証")[0]
        checked = validate("testware-implementation", incomplete)
        self.assertEqual(checked.status, "fail")
        self.assertEqual(status(checked, "TW-IMPL-D005"), "fail")
        self.assertEqual(status(checked, "TW-IMPL-D007"), "fail")
        missing_owner = report.replace(
            "- 実runner実行owner：testware-execution",
            "- 実runner実行owner：",
        )
        self.assertEqual(
            status(validate("testware-implementation", missing_owner), "TW-IMPL-D007"),
            "fail",
        )

    def test_adversarial_non_e2e_requires_provenance_table(self):
        header = "- レビュー種別: 非E2E testware\n"
        complete = (
            header
            + "## 非E2E testware／静的レビュー\n\n"
            + "| 対象source／revision | TCまたは明示対象・仕様Authority | "
            + "testware ref／assertion・fixture | 適用基準／観測根拠 | "
            + "レビュー結果・誤検出候補 | 修正元owner |\n"
            + "| --- | --- | --- | --- | --- | --- |\n"
            + "| src:r1 | TC:1 | case:1 | authority:1 | 未確認 | testware-implementation |\n"
        )
        checked = validate("adversarial-review", complete)
        self.assertEqual(status(checked, "REV-D015"), "pass")
        self.assertEqual(status(checked, "REV-D016"), "pass")
        absent = validate("adversarial-review", header)
        self.assertEqual(status(absent, "REV-D015"), "fail")
        empty_revision = validate(
            "adversarial-review", complete.replace("| src:r1 |", "| |")
        )
        self.assertEqual(status(empty_revision, "REV-D016"), "fail")
        legacy = validate(
            "adversarial-review", "- レビュー種別: テスト設計成果物\n"
        )
        self.assertIsNone(status(legacy, "REV-D015"))


if __name__ == "__main__":
    unittest.main()
