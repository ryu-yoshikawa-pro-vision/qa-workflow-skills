"""Validator tests for question-analysis documents (kind question-analysis).

Fixtures use example identifiers only. The tests also fix the mirrored constants equal to
the question-analysis helper (question_ids.py) and to the store (artifact_store.py).
"""

from __future__ import annotations

import io
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[3] / "skills"
sys.path.insert(0, str(SKILL_ROOT / "question-analysis" / "scripts"))
sys.path.insert(0, str(SKILL_ROOT / "project-context" / "scripts"))

import question_document  # noqa: E402
import question_ids  # noqa: E402
from artifact_store import MAX_BYTES as STORE_MAX_BYTES  # noqa: E402

SCOPE = "scope-1"
REVISION = "rev-source-1"
REASON_PREFIX = "question_document_invalid:"

QUESTION_TABLE_HEADER = (
    "| ID | 問題 / 質問 | 根拠 | 分類 | 影響範囲 / 成果物 | 関連UNKNOWN ID | "
    "Runtime Skill | Runtime Unit Key | Model Key | Target Key | Generation Fingerprint | "
    "回答なしの場合の扱い | 回答後の正規化先 | 再開Skill | 再開対象 / 実行範囲 |"
)
QUESTION_SEPARATOR = "| " + " | ".join(["---"] * 15) + " |"
HISTORY_TABLE = "| ID |\n| --- |\n| Q-001 |\n| Q-002 |"
ASSUMPTION_TABLE = (
    "| 仮定候補 | 状態 | 根拠 / 理由 | 影響範囲 | 正式ASM ID |\n"
    "| --- | --- | --- | --- | --- |\n"
    "|  | 提案 |  |  |  |"
)
BLOCK_TABLE = (
    "| ブロッカーID | ブロック中成果物 / 範囲 | 必要な決定 / 情報源 | Runtime Skill | "
    "Runtime Unit Key | Model Key | Target Key | Generation Fingerprint | 再開Skill | "
    "再開対象 / 実行範囲 |\n"
    "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
    "|  |  |  |  |  |  |  |  |  |  |"
)


def question_row(
    identifier: str = "Q-001",
    *,
    question: str = "通知の既定値は何か",
    basis: str = "SRC-001 の 3 章",
    classification: str = "要確認",
    impact: str = "通知設定画面",
    unknown: str = "UNK-001",
    unanswered: str = "未確定として明示して継続",
) -> str:
    cells = [
        identifier,
        question,
        basis,
        classification,
        impact,
        unknown,
        "",
        "",
        "",
        "",
        "",
        unanswered,
        "spec-analysis",
        "spec-analysis",
        "area-1",
    ]
    return "| " + " | ".join(cells) + " |"


def document(
    *,
    rows: list[str] | None = None,
    history: str = HISTORY_TABLE,
    extra: str = "",
    header: str = QUESTION_TABLE_HEADER,
    skip: tuple[str, ...] = (),
) -> str:
    if rows is None:
        rows = [
            question_row("Q-001"),
            question_row(
                "Q-002",
                question="表示順の既定値は何か",
                classification="提案・任意",
                unknown="UNK-002<br>UNK-003",
                unanswered="提案のみ",
            ),
        ]
    sections = {
        "概要": (
            "- ブロッカー: 0 件\n- 要確認: 2 件\n"
            f"- 入力: spec-analysis の revision `{REVISION}`"
        ),
        "不明点 / 質問一覧": "\n".join([header, QUESTION_SEPARATOR, *rows]),
        "質問ID履歴": history,
        "仮定候補": ASSUMPTION_TABLE,
        "ブロック中範囲": BLOCK_TABLE,
    }
    parts = ["# 不明点・矛盾分析", ""]
    for heading, body in sections.items():
        if heading in skip:
            continue
        parts += [f"## {heading}", "", body, ""]
    parts.append(extra)
    return "\n".join(parts)


VALID = document()


def check(markdown: str, scope: str = SCOPE, revision: str = REVISION) -> dict:
    return question_document.validate(markdown, scope, revision)


def codes(report: dict) -> list[str]:
    return [reason.removeprefix(REASON_PREFIX) for reason in report["reasons"]]


class QuestionDocumentValidatorTests(unittest.TestCase):
    def test_minimal_valid_document_passes(self) -> None:
        report = check(VALID)
        self.assertEqual(report["status"], "valid", report)
        self.assertEqual(report["reasons"], [])
        self.assertEqual(report["metrics"]["questions"], 2)
        self.assertEqual(report["metrics"]["history"], 2)

    def test_each_required_section_is_reported_when_missing(self) -> None:
        for heading in question_document.SECTIONS:
            with self.subTest(heading=heading):
                report = check(document(skip=(heading,)))
                self.assertIn(f"section_missing:{heading}", codes(report))

    def test_duplicate_required_section_is_reported(self) -> None:
        report = check(VALID + "\n## 概要\n\n- 重複\n")
        self.assertIn("section_duplicate:概要", codes(report))

    def test_extra_heading_and_its_position_are_allowed(self) -> None:
        extra = "## 作業メモ\n\n自由記述。\n"
        self.assertEqual(check(VALID + "\n" + extra)["status"], "valid")
        reordered = document().replace(
            "## 仮定候補", "## 作業メモ\n\nメモ\n\n## 仮定候補"
        )
        self.assertEqual(check(reordered)["status"], "valid")

    def test_scope_id_format_is_checked(self) -> None:
        self.assertIn("scope_id_invalid", codes(check(VALID, scope="Scope_1")))
        self.assertIn("scope_id_invalid", codes(check(VALID, scope="x" * 65)))

    def test_source_revision_must_appear_in_document(self) -> None:
        self.assertIn(
            "source_revision_not_in_document", codes(check(VALID, revision="rev-other"))
        )

    def test_question_table_header_must_match_the_template(self) -> None:
        renamed = document(header=QUESTION_TABLE_HEADER.replace("根拠", "根拠等"))
        self.assertIn("table_header_mismatch:不明点 / 質問一覧", codes(check(renamed)))

    def test_row_width_mismatch_is_reported(self) -> None:
        report = check(document(rows=["| Q-001 | 問 |"]))
        self.assertIn("table_row_width:不明点 / 質問一覧", codes(report))

    def test_missing_assumption_table_is_reported(self) -> None:
        markdown = VALID.replace(ASSUMPTION_TABLE, "（表なし）")
        self.assertIn("table_missing:仮定候補", codes(check(markdown)))

    def test_question_id_format_and_duplicate_are_checked(self) -> None:
        bad = document(rows=[question_row("Q-1")])
        self.assertIn("question_id_invalid:Q-1", codes(check(bad)))
        dup = document(rows=[question_row("Q-001"), question_row("Q-001")])
        self.assertIn("question_id_duplicate:Q-001", codes(check(dup)))

    def test_question_text_and_required_cells_are_checked(self) -> None:
        empty_question = document(rows=[question_row("Q-001", question="")])
        self.assertIn("question_text_missing:Q-001", codes(check(empty_question)))
        no_basis = document(rows=[question_row("Q-001", basis="")])
        self.assertIn("basis_missing:Q-001", codes(check(no_basis)))
        no_impact = document(rows=[question_row("Q-001", impact="")])
        self.assertIn("impact_missing:Q-001", codes(check(no_impact)))
        no_unanswered = document(rows=[question_row("Q-001", unanswered="")])
        self.assertIn("unanswered_handling_missing:Q-001", codes(check(no_unanswered)))

    def test_classification_must_be_one_of_the_four_values(self) -> None:
        for value in ("ブロッカー", "要確認", "仮定可能", "提案・任意"):
            with self.subTest(value=value):
                report = check(
                    document(rows=[question_row("Q-001", classification=value)])
                )
                self.assertNotIn("classification_invalid:Q-001", codes(report))
        decorated = document(
            rows=[question_row("Q-001", classification="仮定可能（提案）")]
        )
        self.assertIn("classification_invalid:Q-001", codes(check(decorated)))

    def test_unknown_references_are_format_and_duplicate_checked(self) -> None:
        invalid = document(rows=[question_row("Q-001", unknown="UNK-1")])
        self.assertIn("unknown_ref_invalid:Q-001:UNK-1", codes(check(invalid)))
        duplicate = document(rows=[question_row("Q-001", unknown="UNK-001<br>UNK-001")])
        self.assertIn("unknown_ref_duplicate:Q-001:UNK-001", codes(check(duplicate)))
        multiple = document(rows=[question_row("Q-001", unknown="UNK-001<br>UNK-002")])
        self.assertEqual(check(multiple)["status"], "valid")

    def test_history_format_order_and_coverage_are_checked(self) -> None:
        bad_id = document(history="| ID |\n| --- |\n| Q-1 |\n| Q-001 |")
        self.assertIn("history_id_invalid:Q-1", codes(check(bad_id)))
        unsorted = document(history="| ID |\n| --- |\n| Q-002 |\n| Q-001 |")
        self.assertIn("history_order_invalid", codes(check(unsorted)))
        missing = document(history="| ID |\n| --- |\n| Q-001 |")
        self.assertIn("history_missing_question:Q-002", codes(check(missing)))

    def test_downstream_test_identifier_is_forbidden(self) -> None:
        markdown = VALID + "\nTC-001 に影響する。\n"
        self.assertIn("forbidden_downstream_id:TC-001", codes(check(markdown)))

    def test_escaped_pipe_stays_inside_its_cell(self) -> None:
        row = question_row("Q-001", question="A \\| B")
        report = check(document(rows=[row]))
        self.assertEqual(report["status"], "valid", report)

    def test_heading_inside_a_fenced_block_is_not_a_section(self) -> None:
        markdown = VALID + "\n```\n## 概要\n```\n"
        report = check(markdown)
        self.assertNotIn("section_duplicate:概要", codes(report))
        self.assertEqual(report["status"], "valid", report)

    def test_encoding_and_size_are_checked(self) -> None:
        self.assertEqual(
            codes(question_document.validate("bad\x00", SCOPE, REVISION)),
            ["encoding_invalid"],
        )
        big = "a" * (question_document.MAX_BYTES + 1)
        self.assertEqual(
            codes(question_document.validate(big, SCOPE, REVISION)), ["too_large"]
        )

    def test_constants_match_the_helper_and_the_store(self) -> None:
        self.assertEqual(question_document.MAX_BYTES, STORE_MAX_BYTES)
        self.assertEqual(
            question_document.QUESTION_HEADERS, tuple(question_ids.QUESTION_HEADERS)
        )
        self.assertEqual(question_document.QUESTION_HEADING, "不明点 / 質問一覧")
        self.assertEqual(question_document.HISTORY_HEADING, "質問ID履歴")
        self.assertEqual(
            question_document.HISTORY_HEADING,
            question_ids.HISTORY_HEADING.removeprefix("## "),
        )
        self.assertEqual(
            question_document.QUESTION_HEADING,
            question_ids.QUESTION_HEADING.removeprefix("## "),
        )
        for sample in ("Q-001", "Q-1", "Q-0010", "q-001", "Q-00a"):
            self.assertEqual(
                bool(question_document.Q_ID.fullmatch(sample)),
                bool(question_ids.Q_ID_RE.fullmatch(sample)),
                sample,
            )
        for sample in ("UNK-001", "UNK-1", "UNK-0010", "unk-001"):
            self.assertEqual(
                bool(question_document.UNK_ID.fullmatch(sample)),
                bool(question_ids.UNK_ID_RE.fullmatch(sample)),
                sample,
            )

    def test_artifact_ref_is_derived_from_scope(self) -> None:
        self.assertEqual(
            question_document.artifact_ref_for("scope-1"),
            "question-analysis/scope-1.md",
        )
        self.assertIsNone(question_document.artifact_ref_for("../scope"))
        self.assertIsNone(question_document.artifact_ref_for(None))


class QuestionDocumentCliTests(unittest.TestCase):
    def run_cli(self, data: bytes, scope: str = SCOPE) -> tuple[int, dict]:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "document.md"
            path.write_bytes(data)
            out = io.StringIO()
            with redirect_stdout(out):
                code = question_document.main(
                    [
                        "validate",
                        "--document-file",
                        str(path),
                        "--scope-id",
                        scope,
                        "--source-revision",
                        REVISION,
                    ]
                )
        return code, json.loads(out.getvalue())

    def test_validate_command_reports_valid_and_blocked(self) -> None:
        code, payload = self.run_cli(VALID.encode("utf-8"))
        self.assertEqual((code, payload["status"]), (0, "valid"))
        code, payload = self.run_cli(
            VALID.replace("## 仮定候補", "## 別").encode("utf-8")
        )
        self.assertEqual(code, 1)
        self.assertIn(f"{REASON_PREFIX}section_missing:仮定候補", payload["reasons"])

    def test_validate_command_rejects_invalid_utf8(self) -> None:
        code, payload = self.run_cli(b"\xff\xfe")
        self.assertEqual(
            (code, payload["reasons"]), (1, [f"{REASON_PREFIX}encoding_invalid"])
        )

    def test_validate_command_reports_unreadable_file(self) -> None:
        out = io.StringIO()
        with redirect_stdout(out):
            code = question_document.main(
                [
                    "validate",
                    "--document-file",
                    "/nonexistent/none.md",
                    "--scope-id",
                    SCOPE,
                    "--source-revision",
                    REVISION,
                ]
            )
        self.assertEqual(code, 1)
        self.assertEqual(
            json.loads(out.getvalue())["reasons"], [f"{REASON_PREFIX}unavailable"]
        )

    def test_validate_runs_as_a_script_without_repo_imports(self) -> None:
        script = SKILL_ROOT / "question-analysis" / "scripts" / "question_document.py"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "document.md"
            path.write_text(VALID, encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    "-I",
                    str(script),
                    "validate",
                    "--document-file",
                    str(path),
                    "--scope-id",
                    SCOPE,
                    "--source-revision",
                    REVISION,
                ],
                capture_output=True,
                text=True,
                check=False,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
