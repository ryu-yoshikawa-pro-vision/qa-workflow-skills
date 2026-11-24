"""Read-only validator tests for the spec-analysis document (kind spec-analysis)."""

from __future__ import annotations

import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[3] / "skills"
sys.path.insert(0, str(SKILL_ROOT / "spec-analysis" / "scripts"))
sys.path.insert(0, str(SKILL_ROOT / "project-context" / "scripts"))

import artifact_store  # noqa: E402
import spec_document  # noqa: E402

REVISION = "source-1"

VALID = """# 仕様分析

## 分析範囲

- 対象機能: example-feature
- 対象画面 / ロール: example-role
- 対象情報源: requirements
- 対象とする正本一覧: requirements
- 対象外: none
- 制約: none

## 情報源 / 正本参照一覧

| 参照ID | 情報源 / 正本一覧 | 権威 / 優先順位 | 鮮度 / バージョン | 対象範囲 | 参照 / 備考 |
| ------- | ----------------- | --------------- | ----------------- | -------- | ----------- |
| SRC-001 | requirements | primary | rev:source-1 | scope-1 | file:docs/spec.md:10-12 |

## 分析項目

| 項目ID   | カテゴリ | 内容 | 分類      | 情報源 / 正本参照 | 現在有効か | 補足 / 上書き / 置換関係 | 備考 |
| -------- | -------- | ---- | --------- | ----------------- | ---------- | ------------------------ | ---- |
| SPEC-001 | rule | item one | SPEC | SRC-001 | yes | none | none |
| DEC-001 | decision | item two | DECISION | SRC-001 | yes | none | none |
| INF-001 | inference | item three | INFERENCE | SRC-001 | yes | none | none |
| UNK-001 | open | item four | UNKNOWN |  | yes | none | reason not yet known |

## 現在有効な仕様根拠

| 仕様根拠ID | 種別 | 現在有効な内容 | 適用範囲 | 情報源 / 正本一覧 | 関係 | 関連仕様根拠ID |
| ---------- | ---- | -------------- | -------- | ----------------- | ---- | -------------- |
| AUTH-001 | SPEC | authority text | scope-1 | SRC-001 | 独立 |  |
| AUTH-002 | DECISION | decision text | scope-1 | SRC-001 | 補足 | AUTH-001 |

## 業務ルール

| ルールID / 名称 | 関連項目ID | 情報源 / 備考 |
| --------------- | ---------- | ------------- |
| RULE-001 | SPEC-001 | SRC-001 |

## 状態 / 遷移

| 現在状態 | イベント / 操作 | 条件 | 遷移後状態 | 関連項目ID |
| -------- | --------------- | ---- | ---------- | ---------- |
| idle | submit | valid | done | DEC-001 |

## 処理 / 業務フロー

| 手順 | 実行者 | 操作 / イベント | 結果 | 関連項目ID |
| ---: | ------ | --------------- | ---- | ---------- |
|    1 | user | submit | saved | SPEC-001 |

## 制約 / 明示的境界

| 制約 | 値 / ルール | 関連項目ID | 情報源 |
| ---- | ----------- | ---------- | ------ |
| max | 10 | SPEC-001 | SRC-001 |

## 矛盾 / 不明点 / 質問候補

| 項目 | 根拠 | 影響範囲 | 推奨する次の扱い |
| ---- | ---- | -------- | ---------------- |
| none | none | none | none |

## 後続Skillへの補足

| 項目 | 関連項目ID | 後続Skillへの関連 / 備考 |
| ---- | ---------- | ------------------------ |
| note | INF-001 | note |

## Machine Entity（機械証拠）

placeholder for machine evidence block
"""


def reasons_of(
    markdown: str, scope_id: str = "scope-1", revision: str = REVISION
) -> list[str]:
    report = spec_document.validate(markdown, scope_id, revision)
    return report["reasons"]


def codes_of(markdown: str, **kwargs: str) -> list[str]:
    return [reason.split(":", 1)[1] for reason in reasons_of(markdown, **kwargs)]


def without_section(markdown: str, heading: str) -> str:
    lines = markdown.split("\n")
    out: list[str] = []
    skipping = False
    for line in lines:
        if line.startswith("## "):
            skipping = line[3:].strip() == heading
        if not skipping:
            out.append(line)
    return "\n".join(out)


class SpecDocumentValidatorTests(unittest.TestCase):
    def test_minimal_valid_document_passes(self) -> None:
        report = spec_document.validate(VALID, "scope-1", REVISION)
        self.assertEqual(report["status"], "valid", report["reasons"])
        self.assertEqual(report["reasons"], [])
        self.assertEqual(report["metrics"]["items"], 4)
        self.assertEqual(report["metrics"]["sources"], 1)
        self.assertEqual(report["metrics"]["authorities"], 2)

    def test_missing_section_is_reported(self) -> None:
        text = without_section(VALID, "制約 / 明示的境界")
        self.assertIn("section_missing:制約 / 明示的境界", codes_of(text))

    def test_section_order_is_checked(self) -> None:
        first = "## 分析範囲"
        second = "## 情報源 / 正本参照一覧"
        swapped = VALID.replace(first, "@@A@@", 1).replace(second, first, 1)
        swapped = swapped.replace("@@A@@", second, 1)
        self.assertIn("section_order_invalid", codes_of(swapped))

    def test_item_id_format_is_checked(self) -> None:
        text = VALID.replace("| SPEC-001 | rule", "| SPEC-1 | rule", 1)
        self.assertIn("item_id_invalid:SPEC-1", codes_of(text))

    def test_item_id_duplicate_is_checked(self) -> None:
        text = VALID.replace("| DEC-001 | decision", "| SPEC-001 | decision", 1)
        self.assertIn("item_id_duplicate:SPEC-001", codes_of(text))

    def test_invalid_classification_is_checked(self) -> None:
        text = VALID.replace(
            "| SPEC-001 | rule | item one | SPEC |",
            "| SPEC-001 | rule | item one | GUESS |",
            1,
        )
        self.assertIn("classification_invalid:SPEC-001", codes_of(text))

    def test_classification_prefix_mismatch_is_checked(self) -> None:
        text = VALID.replace(
            "| SPEC-001 | rule | item one | SPEC |",
            "| SPEC-001 | rule | item one | INFERENCE |",
            1,
        )
        self.assertIn("classification_id_mismatch:SPEC-001", codes_of(text))

    def test_spec_without_source_is_reported(self) -> None:
        text = VALID.replace(
            "| SPEC-001 | rule | item one | SPEC | SRC-001 |",
            "| SPEC-001 | rule | item one | SPEC |  |",
            1,
        )
        self.assertIn("source_ref_missing:SPEC-001", codes_of(text))

    def test_unknown_source_reference_is_reported(self) -> None:
        text = VALID.replace(
            "| SRC-001 | requirements | primary | rev:source-1 | scope-1 | file:docs/spec.md:10-12 |",
            "| SRC-001 | requirements | primary | rev:source-1 | scope-1 | file:docs/spec.md:10-12 |",
            1,
        )
        text = text.replace(
            "| DEC-001 | decision | item two | DECISION | SRC-001",
            "| DEC-001 | decision | item two | DECISION | SRC-009",
            1,
        )
        self.assertIn("source_ref_unknown:DEC-001:SRC-009", codes_of(text))

    def test_unknown_without_reason_is_reported(self) -> None:
        text = VALID.replace(
            "| UNK-001 | open | item four | UNKNOWN |  | yes | none | reason not yet known |",
            "| UNK-001 | open | item four | UNKNOWN |  | yes | none |  |",
            1,
        )
        self.assertIn("unknown_reason_missing:UNK-001", codes_of(text))

    def test_downstream_test_identifier_is_forbidden(self) -> None:
        text = VALID.replace(
            "| none | none | none | none |", "| TC-001 | none | none | none |", 1
        )
        self.assertIn("forbidden_downstream_id:TC-001", codes_of(text))

    def test_source_revision_format_and_locator_are_checked(self) -> None:
        no_rev = VALID.replace(
            "rev:source-1 | scope-1 | file:docs/spec.md:10-12",
            "source-1 | scope-1 | file:docs/spec.md:10-12",
            1,
        )
        self.assertIn("src_revision_missing:SRC-001", codes_of(no_rev))
        bad_locator = VALID.replace("file:docs/spec.md:10-12", "file:docs/spec.md", 1)
        self.assertIn("src_locator_invalid:SRC-001", codes_of(bad_locator))
        absolute = VALID.replace("file:docs/spec.md:10-12", "file:/abs/spec.md:1", 1)
        self.assertIn("src_locator_invalid:SRC-001", codes_of(absolute))

    def test_scope_fields_and_scope_id_are_checked(self) -> None:
        empty_feature = VALID.replace("- 対象機能: example-feature", "- 対象機能:", 1)
        self.assertIn("scope_field_missing:対象機能", codes_of(empty_feature))
        no_exclusion = VALID.replace("- 対象外: none\n", "", 1)
        self.assertIn("scope_field_missing:対象外", codes_of(no_exclusion))
        self.assertIn("scope_id_invalid", codes_of(VALID, scope_id="Scope 1"))

    def test_table_header_and_row_width_are_checked(self) -> None:
        short_header = VALID.replace(
            "| 参照ID | 情報源 / 正本一覧 | 権威 / 優先順位 | 鮮度 / バージョン | 対象範囲 | 参照 / 備考 |",
            "| 参照ID | 情報源 / 正本一覧 | 権威 / 優先順位 | 鮮度 / バージョン | 参照 / 備考 |",
            1,
        )
        self.assertIn(
            "table_header_mismatch:情報源 / 正本参照一覧", codes_of(short_header)
        )
        width = VALID.replace(
            "| SRC-001 | requirements | primary | rev:source-1 | scope-1 | file:docs/spec.md:10-12 |",
            "| SRC-001 | requirements | primary | rev:source-1 | scope-1 |",
            1,
        )
        self.assertIn("table_row_width:情報源 / 正本参照一覧", codes_of(width))

    def test_authority_relation_and_item_reference_are_checked(self) -> None:
        bad_relation = VALID.replace(
            "| AUTH-002 | DECISION | decision text | scope-1 | SRC-001 | 補足 | AUTH-001 |",
            "| AUTH-002 | DECISION | decision text | scope-1 | SRC-001 | 補足 | AUTH-009 |",
            1,
        )
        self.assertIn(
            "authority_relation_unknown:AUTH-002:AUTH-009", codes_of(bad_relation)
        )
        bad_item = VALID.replace(
            "| 1 | user | submit | saved | SPEC-001 |",
            "| 1 | user | submit | saved | SPEC-099 |",
            1,
        ).replace(
            "|    1 | user | submit | saved | SPEC-001 |",
            "|    1 | user | submit | saved | SPEC-099 |",
            1,
        )
        self.assertIn("item_ref_unknown:処理 / 業務フロー:SPEC-099", codes_of(bad_item))

    def test_input_encoding_and_size_are_checked(self) -> None:
        self.assertEqual(codes_of(VALID + "\x00"), ["encoding_invalid"])
        self.assertEqual(codes_of("\ud800"), ["encoding_invalid"])
        too_large = VALID + "x" * (spec_document.MAX_BYTES + 1)
        self.assertEqual(codes_of(too_large), ["too_large"])

    def test_source_revision_must_appear_in_document(self) -> None:
        self.assertIn(
            "source_revision_not_in_document",
            codes_of(VALID, revision="source-missing"),
        )

    def test_size_limit_matches_the_store(self) -> None:
        self.assertEqual(spec_document.MAX_BYTES, artifact_store.MAX_BYTES)

    def test_artifact_ref_is_derived_from_scope(self) -> None:
        self.assertEqual(
            spec_document.artifact_ref_for("scope-1"), "spec-analysis/scope-1.md"
        )
        self.assertIsNone(spec_document.artifact_ref_for("../x"))
        self.assertIsNone(spec_document.artifact_ref_for("Scope"))

    def test_template_headers_match_validator_constants(self) -> None:
        template = (
            SKILL_ROOT / "spec-analysis" / "assets" / "output-template.md"
        ).read_text(encoding="utf-8")
        sections: dict[str, str] = {}
        current = ""
        for line in template.split("\n"):
            if line.startswith("## "):
                current = line[3:].strip()
                sections[current] = ""
            elif current:
                sections[current] += line + "\n"
        self.assertEqual(tuple(sections), spec_document.SECTIONS)
        for heading, header in spec_document.TABLE_HEADERS.items():
            table_line = next(
                line for line in sections[heading].split("\n") if line.startswith("|")
            )
            self.assertEqual(
                tuple(
                    cell.strip() for cell in table_line.strip().strip("|").split("|")
                ),
                header,
                heading,
            )


class SpecDocumentCliTests(unittest.TestCase):
    def run_validate(self, text: str, scope_id: str = "scope-1") -> tuple[int, str]:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "document.md"
            path.write_bytes(text.encode("utf-8"))
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = spec_document.main(
                    [
                        "validate",
                        "--document-file",
                        str(path),
                        "--scope-id",
                        scope_id,
                        "--source-revision",
                        REVISION,
                    ]
                )
        return code, out.getvalue()

    def test_validate_command_reports_valid_and_blocked(self) -> None:
        code, out = self.run_validate(VALID)
        self.assertEqual(code, 0)
        self.assertIn('"status": "valid"', out)
        code, out = self.run_validate(VALID.replace("## 後続Skillへの補足", "## 後続"))
        self.assertEqual(code, 1)
        self.assertIn("spec_document_invalid:section_missing:後続Skillへの補足", out)

    def test_validate_command_rejects_invalid_utf8(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "document.md"
            path.write_bytes(b"\xff\xfe")
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = spec_document.main(
                    [
                        "validate",
                        "--document-file",
                        str(path),
                        "--scope-id",
                        "scope-1",
                        "--source-revision",
                        REVISION,
                    ]
                )
        self.assertEqual(code, 1)
        self.assertIn("encoding_invalid", out.getvalue())


if __name__ == "__main__":
    unittest.main()
