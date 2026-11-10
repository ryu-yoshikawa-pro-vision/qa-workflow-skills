from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SKILLS_ROOT = REPO_ROOT / "skills"


def normalize_markdown_tables(text: str) -> str:
    normalized_lines = []
    for line in text.splitlines():
        if line.strip().startswith("|"):
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            line = "| " + " | ".join(cells) + " |"
        normalized_lines.append(line)
    return "\n".join(normalized_lines) + ("\n" if text.endswith("\n") else "")


def load_validator(skill: str):
    path = SKILLS_ROOT / skill / "evals" / "deterministic" / "validator.py"
    spec = importlib.util.spec_from_file_location(
        f"{skill.replace('-', '_')}_validator", path
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load validator: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.validate


def eval_case(skill: str, eval_id: str) -> tuple[str, dict]:
    root = SKILLS_ROOT / skill / "evals" / "output"
    manifest = json.loads((root / "evals.json").read_text(encoding="utf-8"))
    case = next(row for row in manifest["cases"] if row["id"] == eval_id)
    expected = json.loads((root / case["expected"]).read_text(encoding="utf-8"))
    reference = (root / case["input"]).parent / "reference.md"
    return normalize_markdown_tables(reference.read_text(encoding="utf-8")), expected


def assertion_status(result, assertion_id: str) -> str:
    return next(item.status for item in result.assertions if item.id == assertion_id)


def update_markdown_row(
    text: str,
    row_id: str,
    updates: dict[str, str],
    section: str | None = None,
) -> str:
    lines = text.splitlines()
    section_start = 0
    section_end = len(lines)
    if section is not None:
        section_start = next(
            (index for index, line in enumerate(lines) if line.strip() == section), -1
        )
        if section_start < 0:
            raise AssertionError(f"could not find table section {section}")
        section_end = next(
            (
                index
                for index in range(section_start + 1, len(lines))
                if lines[index].strip().startswith("## ")
            ),
            len(lines),
        )
    row_index = None
    headers = []
    cells = []
    for index in range(section_start + 1, section_end):
        line = lines[index]
        if not line.strip().startswith(f"| {row_id} |"):
            continue
        for header_index in range(index - 1, -1, -1):
            if lines[header_index].strip().startswith("## "):
                break
            candidate_headers = [
                cell.strip()
                for cell in lines[header_index].strip().strip("|").split("|")
            ]
            if not all(header in candidate_headers for header in updates):
                continue
            row_index = index
            headers = candidate_headers
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            break
        if row_index is not None:
            break
    if row_index is None:
        raise AssertionError(
            f"could not find {row_id} row with columns {sorted(updates)}"
        )
    for header, value in updates.items():
        cells[headers.index(header)] = value
    lines[row_index] = "| " + " | ".join(cells) + " |"
    return "\n".join(lines) + ("\n" if text.endswith("\n") else "")


def completed_plan_fixture() -> tuple[str, dict]:
    text, expected = eval_case("test-management", "TMG-OUT-001")
    text = text.replace("| 状態 | 進行中 |", "| 状態 | 完了 |", 1)
    text = update_markdown_row(
        text,
        "終了",
        {"判定状態": "未達"},
    )
    text = update_markdown_row(
        text,
        "MON-8",
        {"全体判定": "完了", "差異・未確定": "差異なし"},
    )
    text = update_markdown_row(
        text,
        "PROJ-RISK-001",
        {"状態": "解決済み", "状態証拠ref": "RISK-CLOSE-1", "承認主体・role": "-"},
    )
    text = update_markdown_row(
        text,
        "CA-001",
        {
            "期限 / 状態": "2026-11-10 / 完了",
            "結果ref": "ACTION-RESULT-1",
            "承認主体・role": "-",
        },
    )
    return text, expected


def add_difference_row(text: str, row: str) -> str:
    separator = "| ------ | --------- | ---- | ------------------ | ---- | ----- | ---- | ----------- | -------------- |"
    if separator not in text:
        raise AssertionError("could not find difference table separator")
    return text.replace(separator, f"{separator}\n{row}", 1)


def insert_table_row(text: str, section: str, row: str) -> str:
    lines = text.splitlines()
    section_index = next(
        (index for index, line in enumerate(lines) if line.strip() == section), None
    )
    if section_index is None:
        raise AssertionError(f"could not find table section {section}")
    separator_index = None
    for index in range(section_index + 1, len(lines)):
        line = lines[index].strip()
        if line.startswith("|") and all(
            set(cell.strip()) <= {"-", ":"} for cell in line.strip("|").split("|")
        ):
            separator_index = index
            break
        if line.startswith("## "):
            break
    if separator_index is None:
        raise AssertionError(f"could not find table separator in {section}")
    lines.insert(separator_index + 1, row)
    return "\n".join(lines) + ("\n" if text.endswith("\n") else "")


def remove_markdown_row(text: str, row_id: str, section: str | None = None) -> str:
    lines = text.splitlines()
    if section is None:
        section_index = -1
        section_end = len(lines)
    else:
        section_index = next(
            (index for index, line in enumerate(lines) if line.strip() == section), None
        )
        if section_index is None:
            raise AssertionError(f"could not find table section {section}")
        section_end = next(
            (
                index
                for index in range(section_index + 1, len(lines))
                if lines[index].strip().startswith("## ")
            ),
            len(lines),
        )
    row_index = next(
        (
            index
            for index in range(section_index + 1, section_end)
            if lines[index].strip().startswith(f"| {row_id} |")
        ),
        None,
    )
    if row_index is None:
        raise AssertionError(f"could not find row {row_id}")
    retained = [line for index, line in enumerate(lines) if index != row_index]
    return "\n".join(retained) + ("\n" if text.endswith("\n") else "")


def remove_markdown_section(text: str, section: str) -> str:
    lines = text.splitlines()
    section_index = next(
        (index for index, line in enumerate(lines) if line.strip() == section), None
    )
    if section_index is None:
        raise AssertionError(f"could not find section {section}")
    section_end = next(
        (
            index
            for index in range(section_index + 1, len(lines))
            if lines[index].strip().startswith("## ")
        ),
        len(lines),
    )
    retained = lines[:section_index] + lines[section_end:]
    return "\n".join(retained) + ("\n" if text.endswith("\n") else "")


def update_table_header(text: str, section: str, header: str, replacement: str) -> str:
    lines = text.splitlines()
    section_index = next(
        (index for index, line in enumerate(lines) if line.strip() == section), None
    )
    if section_index is None:
        raise AssertionError(f"could not find section {section}")
    section_end = next(
        (
            index
            for index in range(section_index + 1, len(lines))
            if lines[index].strip().startswith("## ")
        ),
        len(lines),
    )
    for index in range(section_index + 1, section_end):
        if not lines[index].strip().startswith("|"):
            continue
        cells = [cell.strip() for cell in lines[index].strip().strip("|").split("|")]
        if header not in cells:
            continue
        cells[cells.index(header)] = replacement
        lines[index] = "| " + " | ".join(cells) + " |"
        return "\n".join(lines) + ("\n" if text.endswith("\n") else "")
    raise AssertionError(f"could not find header {header} in {section}")


class QaPlanningContractTests(unittest.TestCase):
    def test_all_output_fixtures_pass(self):
        for skill, eval_ids in (
            ("test-requirements-analysis", ("QRA-OUT-001", "QRA-OUT-002")),
            ("test-architecture-design", ("TAD-OUT-001", "TAD-OUT-002")),
            ("test-management", ("TMG-OUT-001", "TMG-OUT-002")),
        ):
            validate = load_validator(skill)
            for eval_id in eval_ids:
                with self.subTest(skill=skill, eval_id=eval_id):
                    text, expected = eval_case(skill, eval_id)
                    self.assertEqual(validate(text, expected, eval_id).status, "pass")

    def test_reference_fixtures_form_a_revision_pinned_planning_chain(self):
        requirements, _ = eval_case("test-requirements-analysis", "QRA-OUT-001")
        architecture, _ = eval_case("test-architecture-design", "TAD-OUT-001")
        management, _ = eval_case("test-management", "TMG-OUT-001")

        self.assertIn(
            "| artifact_ref | fixture://qa/requirements/orders-q4 |", requirements
        )
        self.assertIn("| revision | req-r3 |", requirements)
        self.assertIn("| scope | orders-release-q4 |", requirements)
        self.assertIn("| 状態 | 承認済み |", requirements)
        self.assertIn(
            "| test-requirements-analysis | fixture://qa/requirements/orders-q4 | req-r3 | orders-release-q4 | current | 取得済 |",
            architecture,
        )
        self.assertIn(
            "| ARCH-001 | orders.update | API target | fixture://qa/requirements/orders-q4#QAR-001@req-r3 |",
            architecture,
        )
        self.assertIn(
            "| test-architecture-design | fixture://qa/architecture/orders-r1 | arch-r1 | orders-release-q4 | QAR-001 | current / 承認済み |",
            requirements,
        )
        self.assertIn(
            "| test-requirements-analysis | fixture://qa/requirements/orders-q4 | req-r3 | orders-release-q4 | current | 取得済 |",
            management,
        )
        self.assertIn(
            "| test-architecture-design | fixture://qa/architecture/orders-r1 | arch-r1 | orders-release-q4 | current | 取得済 |",
            management,
        )
        self.assertIn(
            "| PLAN-001 | fixture://qa/requirements/orders-q4#QAR-001@req-r3 | fixture://qa/architecture/orders-r1#ARCH-001@arch-r1 | orders-release-q4 |",
            management,
        )
        self.assertIn(
            "| ARCH-SOURCE@arch-4 | orders.persistence | test-analysis/RISK-001、test-requirement-design/TR-001 | orders.updateのcurrent割当 |",
            architecture,
        )

    def test_qa_requirement_requires_source_revision_and_exact_approval(self):
        validate = load_validator("test-requirements-analysis")
        text, expected = eval_case("test-requirements-analysis", "QRA-OUT-001")
        missing_revision = text.replace(
            "| REQUEST-01 | doc-7 |", "| REQUEST-01 |  |", 1
        )
        missing_approval = text.replace(
            "| orders-release-q4 | fixture://qa/requirements/orders-q4 | req-r3 | QA lead | APPROVAL-4 | 承認済み |",
            "| orders-release-q4 | fixture://qa/requirements/orders-q4 | req-r3 | QA lead | - | 承認済み |",
            1,
        )
        for label, broken in (
            ("source revision", missing_revision),
            ("approval evidence", missing_approval),
        ):
            with self.subTest(label=label):
                result = validate(broken, expected, "QRA-OUT-001")
                assertion_id = "QRA-D006" if label == "source revision" else "QRA-D013"
                self.assertEqual(assertion_status(result, assertion_id), "fail")

        source_mismatch = text.replace(
            "| stakeholder | REQUEST-01 | doc-7 | orders-release-q4 | current | 取得済 |",
            "| stakeholder | REQUEST-01 | doc-8 | orders-release-q4 | current | 取得済 |",
            1,
        )
        self.assertEqual(
            assertion_status(
                validate(source_mismatch, expected, "QRA-OUT-001"), "QRA-D015"
            ),
            "fail",
        )

        draft_with_current_approval = text.replace(
            "| 状態 | 承認済み |", "| 状態 | 草案 |", 1
        )
        self.assertEqual(
            assertion_status(
                validate(draft_with_current_approval, expected, "QRA-OUT-001"),
                "QRA-D013",
            ),
            "fail",
        )

    def test_qa_approval_placeholders_and_nonapproved_states_are_rejected(self):
        validate = load_validator("test-requirements-analysis")
        text, expected = eval_case("test-requirements-analysis", "QRA-OUT-001")
        approval_section = "## 確認・承認"

        for field, placeholder in (
            ("承認証拠ref", "unknown"),
            ("承認証拠ref", "未取得"),
            ("承認証拠ref", "-"),
            ("承認主体・role", "-"),
            ("承認主体・role", "unknown"),
            ("承認主体・role", "未取得"),
        ):
            with self.subTest(field=field, placeholder=placeholder):
                broken = update_markdown_row(
                    text,
                    "orders-release-q4",
                    {field: placeholder},
                    approval_section,
                )
                result = validate(broken, expected, "QRA-OUT-001")
                self.assertEqual(assertion_status(result, "QRA-D013"), "fail")
                evidence = next(
                    item.evidence for item in result.assertions if item.id == "QRA-D013"
                )
                self.assertIn(placeholder, json.dumps(evidence, ensure_ascii=False))

        for field, value in (
            ("revision", "req-r2"),
            ("対象scope", "orders-release-q3"),
            ("artifact_ref", "fixture://qa/requirements/other"),
        ):
            with self.subTest(field=field, value=value):
                broken = update_markdown_row(
                    text,
                    "orders-release-q4",
                    {field: value},
                    approval_section,
                )
                self.assertEqual(
                    assertion_status(
                        validate(broken, expected, "QRA-OUT-001"), "QRA-D013"
                    ),
                    "fail",
                )

        self.assertEqual(
            assertion_status(validate(text, expected, "QRA-OUT-001"), "QRA-D013"),
            "pass",
        )

        unresolved_requirement = update_markdown_row(
            text, "QAR-002", {"状態": "未解決"}, "## QA要求"
        )
        unresolved_requirement = insert_table_row(
            unresolved_requirement,
            "## 未決事項",
            "| QAR-002 | orders-release-q4 | QA owner | blocked | REQUEST-01の対象範囲を再確認する |",
        )
        unresolved_result = validate(unresolved_requirement, expected, "QRA-OUT-001")
        self.assertEqual(assertion_status(unresolved_result, "QRA-D012"), "pass")
        self.assertEqual(assertion_status(unresolved_result, "QRA-D013"), "fail")
        approval_evidence = next(
            item.evidence
            for item in unresolved_result.assertions
            if item.id == "QRA-D013"
        )
        self.assertIn(
            {
                "id": "QAR-002",
                "scope": "orders-release-q4",
                "state": "未解決",
                "reason": "unresolved QA requirement remains within approved artifact scope",
            },
            approval_evidence,
        )

        out_of_scope_unresolved = update_markdown_row(
            unresolved_requirement,
            "QAR-002",
            {"scope": "independent-scope"},
            "## QA要求",
        )
        out_of_scope_unresolved = update_markdown_row(
            out_of_scope_unresolved,
            "QAR-002",
            {"影響scope": "independent-scope"},
            "## 未決事項",
        )
        self.assertEqual(
            assertion_status(
                validate(out_of_scope_unresolved, expected, "QRA-OUT-001"),
                "QRA-D013",
            ),
            "pass",
        )

        blocked, blocked_expected = eval_case(
            "test-requirements-analysis", "QRA-OUT-002"
        )
        blocked_result = validate(blocked, blocked_expected, "QRA-OUT-002")
        self.assertEqual(assertion_status(blocked_result, "QRA-D013"), "pass")

    def test_qa_purpose_success_conditions_are_required_and_finalized(self):
        validate = load_validator("test-requirements-analysis")
        text, expected = eval_case("test-requirements-analysis", "QRA-OUT-001")
        purpose_section = "## QA目的・成功条件"

        missing_table = remove_markdown_section(text, purpose_section)
        self.assertEqual(
            assertion_status(
                validate(missing_table, expected, "QRA-OUT-001"), "QRA-D001"
            ),
            "fail",
        )

        missing_column = update_table_header(text, purpose_section, "品質目標", "目標")
        self.assertEqual(
            assertion_status(
                validate(missing_column, expected, "QRA-OUT-001"), "QRA-D001"
            ),
            "fail",
        )

        missing_purpose = update_markdown_row(
            text,
            "Ordersの品質ゲートを準備する",
            {"QA目的": ""},
            purpose_section,
        )
        self.assertEqual(
            assertion_status(
                validate(missing_purpose, expected, "QRA-OUT-001"), "QRA-D001"
            ),
            "fail",
        )

        missing_success = update_markdown_row(
            text,
            "Ordersの品質ゲートを準備する",
            {"活動の成功条件": ""},
            purpose_section,
        )
        self.assertEqual(
            assertion_status(
                validate(missing_success, expected, "QRA-OUT-001"), "QRA-D001"
            ),
            "fail",
        )

        missing_basis = update_markdown_row(
            text,
            "Ordersの品質ゲートを準備する",
            {"根拠": ""},
            purpose_section,
        )
        self.assertEqual(
            assertion_status(
                validate(missing_basis, expected, "QRA-OUT-001"), "QRA-D001"
            ),
            "fail",
        )

        unresolved_approved = update_markdown_row(
            text,
            "Ordersの品質ゲートを準備する",
            {"品質目標": "未確定"},
            purpose_section,
        )
        self.assertEqual(
            assertion_status(
                validate(unresolved_approved, expected, "QRA-OUT-001"), "QRA-D001"
            ),
            "fail",
        )

        descriptive_state_word = update_markdown_row(
            text,
            "Ordersの品質ゲートを準備する",
            {"QA目的": "Prevent stale input from being accepted"},
            purpose_section,
        )
        self.assertEqual(
            assertion_status(
                validate(descriptive_state_word, expected, "QRA-OUT-001"),
                "QRA-D001",
            ),
            "pass",
        )

        blocked, blocked_expected = eval_case(
            "test-requirements-analysis", "QRA-OUT-002"
        )
        blocked_section = "## QA目的・成功条件"
        blocked_row_id = "source確認後にQA要求を確定する"
        all_unresolved = update_markdown_row(
            blocked,
            blocked_row_id,
            {
                field: "未取得"
                for field in (
                    "QA目的",
                    "品質目標",
                    "対象・対象外",
                    "活動の成功条件",
                    "根拠",
                )
            },
            blocked_section,
        )
        all_unresolved_result = validate(
            all_unresolved, blocked_expected, "QRA-OUT-002"
        )
        self.assertEqual(assertion_status(all_unresolved_result, "QRA-D001"), "fail")

        for missing_reason in ("", "-", "unknown", "未確定", "stale"):
            with self.subTest(unresolved_purpose_reason=missing_reason):
                no_reason = update_markdown_row(
                    blocked,
                    blocked_row_id,
                    {"根拠": missing_reason},
                    blocked_section,
                )
                no_reason_result = validate(no_reason, blocked_expected, "QRA-OUT-002")
                self.assertEqual(assertion_status(no_reason_result, "QRA-D001"), "fail")

        stale_word_in_reason = update_markdown_row(
            blocked,
            blocked_row_id,
            {"根拠": "REQUEST-MISSINGがstale revisionで本文を取得できないため"},
            blocked_section,
        )
        self.assertEqual(
            assertion_status(
                validate(stale_word_in_reason, blocked_expected, "QRA-OUT-002"),
                "QRA-D001",
            ),
            "pass",
        )
        unresolved_marker_with_reason = update_markdown_row(
            blocked,
            blocked_row_id,
            {"根拠": "unknown: REQUEST-MISSINGのownerがrevisionを提示していないため"},
            blocked_section,
        )
        self.assertEqual(
            assertion_status(
                validate(
                    unresolved_marker_with_reason,
                    blocked_expected,
                    "QRA-OUT-002",
                ),
                "QRA-D001",
            ),
            "pass",
        )

        missing_requirement_basis = update_markdown_row(
            text, "QAR-001", {"根拠・成功条件": ""}
        )
        self.assertEqual(
            assertion_status(
                validate(missing_requirement_basis, expected, "QRA-OUT-001"),
                "QRA-D006",
            ),
            "fail",
        )

        blocked, blocked_expected = eval_case(
            "test-requirements-analysis", "QRA-OUT-002"
        )
        blocked_result = validate(blocked, blocked_expected, "QRA-OUT-002")
        self.assertEqual(assertion_status(blocked_result, "QRA-D001"), "pass")
        self.assertEqual(assertion_status(blocked_result, "QRA-D013"), "pass")

    def test_unresolved_qa_items_require_scope_owner_state_and_reopen_condition(self):
        validate = load_validator("test-requirements-analysis")
        text, expected = eval_case("test-requirements-analysis", "QRA-OUT-002")
        unresolved_section = "## 未決事項"
        self.assertEqual(
            assertion_status(validate(text, expected, "QRA-OUT-002"), "QRA-D012"),
            "pass",
        )

        malformed_items = (
            remove_markdown_row(text, "QAR-003", unresolved_section),
            update_markdown_row(text, "QAR-003", {"担当": ""}, unresolved_section),
            update_markdown_row(text, "QAR-003", {"担当": "-"}, unresolved_section),
            update_markdown_row(
                text, "QAR-003", {"担当": "unknown"}, unresolved_section
            ),
            update_markdown_row(
                text, "QAR-003", {"担当": "未取得"}, unresolved_section
            ),
            update_markdown_row(text, "QAR-003", {"影響scope": ""}, unresolved_section),
            update_markdown_row(
                text, "QAR-003", {"影響scope": "unknown"}, unresolved_section
            ),
            update_markdown_row(
                text, "QAR-003", {"影響scope": "payments"}, unresolved_section
            ),
            update_markdown_row(text, "QAR-003", {"状態": ""}, unresolved_section),
            update_markdown_row(
                text, "QAR-003", {"状態": "not-a-state"}, unresolved_section
            ),
            update_markdown_row(text, "QAR-003", {"再開条件": ""}, unresolved_section),
            update_markdown_row(text, "QAR-003", {"再開条件": "-"}, unresolved_section),
        )
        for index, broken in enumerate(malformed_items):
            with self.subTest(case=index):
                self.assertEqual(
                    assertion_status(
                        validate(broken, expected, "QRA-OUT-002"), "QRA-D012"
                    ),
                    "fail",
                )

        unacquired = update_markdown_row(
            text, "QAR-003", {"状態": "未取得"}, unresolved_section
        )
        self.assertEqual(
            assertion_status(validate(unacquired, expected, "QRA-OUT-002"), "QRA-D012"),
            "pass",
        )

        unrelated_item = insert_table_row(
            text,
            unresolved_section,
            "| QAR-999 | payments | payments QA owner | blocked | PAYMENT-SOURCEのscopeとrevisionを取得する |",
        )
        self.assertEqual(
            assertion_status(
                validate(unrelated_item, expected, "QRA-OUT-002"), "QRA-D012"
            ),
            "pass",
        )

    def test_unapproved_qa_requirements_cannot_become_approved(self):
        validate = load_validator("test-requirements-analysis")
        text, expected = eval_case("test-requirements-analysis", "QRA-OUT-002")
        broken = text.replace("| 状態 | blocked |", "| 状態 | 承認済み |", 1)
        result = validate(broken, expected, "QRA-OUT-002")
        self.assertEqual(assertion_status(result, "QRA-D014"), "fail")

    def test_approved_qa_requirements_reject_stale_sources_and_allow_draft_recovery(
        self,
    ):
        validate = load_validator("test-requirements-analysis")
        text, expected = eval_case("test-requirements-analysis", "QRA-OUT-001")
        stale_source = text.replace(
            "| stakeholder | REQUEST-01 | doc-7 | orders-release-q4 | current | 取得済 | approval recordを確認 |",
            "| stakeholder | REQUEST-01 | doc-7 | orders-release-q4 | stale | 取得済 | approval recordを確認 |",
            1,
        )
        stale_result = validate(stale_source, expected, "QRA-OUT-001")
        self.assertEqual(assertion_status(stale_result, "QRA-D015"), "fail")
        self.assertEqual(assertion_status(stale_result, "QRA-D013"), "fail")

        unavailable_source = text.replace(
            "| stakeholder | REQUEST-01 | doc-7 | orders-release-q4 | current | 取得済 | approval recordを確認 |",
            "| stakeholder | REQUEST-01 | doc-7 | orders-release-q4 | unknown | 取得不能 | approval recordを確認 |",
            1,
        )
        unavailable_result = validate(unavailable_source, expected, "QRA-OUT-001")
        self.assertEqual(assertion_status(unavailable_result, "QRA-D015"), "fail")

        draft = stale_source.replace("| 状態 | 承認済み |", "| 状態 | blocked |", 1)
        draft = update_markdown_row(draft, "QAR-001", {"状態": "提案"})
        draft = update_markdown_row(draft, "orders-release-q4", {"状態": "失効"})
        draft_result = validate(draft, expected, "QRA-OUT-001")
        self.assertEqual(assertion_status(draft_result, "QRA-D010"), "pass")
        self.assertEqual(assertion_status(draft_result, "QRA-D015"), "pass")
        self.assertEqual(assertion_status(draft_result, "QRA-D013"), "pass")

    def test_qa_requirement_and_source_rows_without_local_ids_or_refs_are_not_ignored(
        self,
    ):
        validate = load_validator("test-requirements-analysis")
        text, expected = eval_case("test-requirements-analysis", "QRA-OUT-001")
        missing_requirement_id = update_markdown_row(text, "QAR-001", {"QA要求ID": ""})
        result = validate(missing_requirement_id, expected, "QRA-OUT-001")
        self.assertEqual(assertion_status(result, "QRA-D005"), "fail")

        missing_source_ref = update_markdown_row(
            text, "stakeholder", {"source_ref": ""}
        )
        result = validate(missing_source_ref, expected, "QRA-OUT-001")
        self.assertEqual(assertion_status(result, "QRA-D010"), "fail")
        self.assertEqual(assertion_status(result, "QRA-D015"), "fail")

    def test_architecture_enforces_priority_and_preserves_multiple_levels(self):
        validate = load_validator("test-architecture-design")
        text, expected = eval_case("test-architecture-design", "TAD-OUT-001")
        bad_priority = text.replace(
            "APIを明示指定で採用し、承認済みarchitectureのシステムlevelも別分担として保持",
            "システムを明示指定で採用し、承認済みarchitectureのシステムlevelも別分担として保持",
            1,
        )
        missing_level = text.replace(
            "| ARCH-002 | orders.update | business flow | fixture://qa/requirements/orders-q4#QAR-001@req-r3 | システム | functional | system levelの別分担を保持 | staging / synthetic-orders | Playwright候補 | 承認済みarchitecture | ARCH-SOURCE@arch-4 | 実装可否は別owner確認 | e2e-test-inspection |\n",
            "",
            1,
        )
        self.assertEqual(
            assertion_status(
                validate(bad_priority, expected, "TAD-OUT-001"), "TAD-D011"
            ),
            "fail",
        )
        self.assertEqual(
            assertion_status(
                validate(missing_level, expected, "TAD-OUT-001"), "TAD-D012"
            ),
            "fail",
        )

        invalid_priority = update_markdown_row(
            text, "orders.persistence", {"明示指定": "unrecognized-level"}
        )
        self.assertEqual(
            assertion_status(
                validate(invalid_priority, expected, "TAD-OUT-001"), "TAD-D011"
            ),
            "fail",
        )

        missing_precedence = remove_markdown_row(
            text, "orders.persistence", "## レベル優先・競合"
        )
        self.assertEqual(
            assertion_status(
                validate(missing_precedence, expected, "TAD-OUT-001"), "TAD-D011"
            ),
            "fail",
        )

    def test_architecture_does_not_ignore_assignment_or_source_rows_without_keys(self):
        validate = load_validator("test-architecture-design")
        text, expected = eval_case("test-architecture-design", "TAD-OUT-001")
        missing_assignment_id = update_markdown_row(text, "ARCH-001", {"割当ID": ""})
        result = validate(missing_assignment_id, expected, "TAD-OUT-001")
        self.assertEqual(assertion_status(result, "TAD-D005"), "fail")

        missing_source_ref = update_markdown_row(
            text, "stakeholder", {"source_ref": ""}
        )
        result = validate(missing_source_ref, expected, "TAD-OUT-001")
        self.assertEqual(assertion_status(result, "TAD-D009"), "fail")

    def test_architecture_approval_must_match_current_revision(self):
        validate = load_validator("test-architecture-design")
        text, expected = eval_case("test-architecture-design", "TAD-OUT-001")
        broken = text.replace(
            "| arch-r1 | QA architecture owner |",
            "| arch-r0 | QA architecture owner |",
            1,
        )
        self.assertEqual(
            assertion_status(validate(broken, expected, "TAD-OUT-001"), "TAD-D013"),
            "fail",
        )

        text, expected = eval_case("test-architecture-design", "TAD-OUT-002")
        false_assignment = text.replace(
            "| ARCH-004 | billing.authorization | API target | fixture://qa/requirements/billing-conflict#QAR-UNKNOWN@unknown | 未確定 | functional | 指定の解決後に分担を決める | 未確定 | 未確定 | 未確定 | REQUEST-UNKNOWN@unknown | 判断保留 | test-architecture-design |",
            "| ARCH-004 | billing.authorization | API target | fixture://qa/requirements/billing-conflict#QAR-UNKNOWN@unknown | API | functional | 指定の解決後に分担を決める | 未確定 | 未確定 | 明示指定 | REQUEST-UNKNOWN@unknown | 準備済み | test-architecture-design |",
            1,
        )
        result = validate(false_assignment, expected, "TAD-OUT-002")
        self.assertEqual(assertion_status(result, "TAD-D015"), "fail")
        self.assertEqual(assertion_status(result, "TAD-D011"), "fail")
        self.assertEqual(assertion_status(result, "TAD-D016"), "fail")

        text, expected = eval_case("test-architecture-design", "TAD-OUT-001")
        stale_source_revision = text.replace(
            "| stakeholder | REQUEST-01@doc-7 | doc-7 | orders-release-q4 | current | 取得済 |",
            "| stakeholder | REQUEST-01@doc-7 | doc-8 | orders-release-q4 | current | 取得済 |",
            1,
        )
        result = validate(stale_source_revision, expected, "TAD-OUT-001")
        self.assertEqual(assertion_status(result, "TAD-D009"), "fail")

        stale_requirement_revision = text.replace(
            "fixture://qa/requirements/orders-q4#QAR-001@req-r3",
            "fixture://qa/requirements/orders-q4#QAR-001@req-r2",
            1,
        )
        self.assertEqual(
            assertion_status(
                validate(stale_requirement_revision, expected, "TAD-OUT-001"),
                "TAD-D016",
            ),
            "fail",
        )

    def test_architecture_requires_current_approved_qa_requirement_source(self):
        validate = load_validator("test-architecture-design")
        text, expected = eval_case("test-architecture-design", "TAD-OUT-001")
        stale_requirement = update_markdown_row(
            text,
            "test-requirements-analysis",
            {"currentness": "stale", "承認状態": "失効"},
        )
        result = validate(stale_requirement, expected, "TAD-OUT-001")
        self.assertEqual(assertion_status(result, "TAD-D015"), "fail")
        self.assertEqual(assertion_status(result, "TAD-D011"), "fail")

    def test_architecture_priority_is_target_local_and_unknown_sources_do_not_bypass_it(
        self,
    ):
        validate = load_validator("test-architecture-design")
        text, expected = eval_case("test-architecture-design", "TAD-OUT-001")
        stale_source_a = update_markdown_row(
            text, "stakeholder", {"currentness": "stale"}
        )
        stale_source_a = update_markdown_row(
            stale_source_a,
            "ARCH-001",
            {
                "level": "未確定",
                "選択根拠": "未確定",
                "状態・準備条件": "blocked: source stale",
            },
        )
        stale_source_a = update_markdown_row(
            stale_source_a,
            "orders.update",
            {
                "適用判断": "未確定、影響する明示指定だけ採用しない。currentなsystem assignmentは保持",
                "競合・判断元": "scopeとrevisionが一致する判断元を再取得する",
            },
        )
        local_result = validate(stale_source_a, expected, "TAD-OUT-001")
        self.assertEqual(assertion_status(local_result, "TAD-D011"), "pass")
        self.assertEqual(assertion_status(local_result, "TAD-D015"), "fail")
        self.assertIn("| ARCH-002 | orders.update", stale_source_a)
        self.assertIn("| システム | functional | system levelの別分担", stale_source_a)

        with_unrelated_unknown = insert_table_row(
            stale_source_a,
            "## 入力source・依存",
            "| other-owner | OTHER-SOURCE@unknown | unknown | payments | unknown | 不明 | unknown | - |",
        )
        bad_current_assignment = update_markdown_row(
            with_unrelated_unknown, "ARCH-003", {"level": "システム"}
        )
        result = validate(bad_current_assignment, expected, "TAD-OUT-001")
        self.assertEqual(assertion_status(result, "TAD-D011"), "fail")

    def test_plan_monitoring_counts_match_population_and_raw_states(self):
        validate = load_validator("test-management")
        text, expected = eval_case("test-management", "TMG-OUT-001")
        mismatched_count = text.replace(
            "| MON-8 | fixture://qa/plan/orders-q4@plan-r8 | orders-release-q4 | build-110 | staging | after-run-2 | 2 | 2 |",
            "| MON-8 | fixture://qa/plan/orders-q4@plan-r8 | orders-release-q4 | build-110 | staging | after-run-2 | 2 | 1 |",
            1,
        )
        self.assertEqual(
            assertion_status(
                validate(mismatched_count, expected, "TMG-OUT-001"), "TMG-D015"
            ),
            "fail",
        )

        text, expected = eval_case("test-management", "TMG-OUT-002")
        wrong_unexecuted_count = text.replace(
            "| MON-2 | fixture://qa/plan/orders-q4@plan-r2 | orders-release-q4 | build-111 | staging | initial | 1 | 0 | 0 | 1 |",
            "| MON-2 | fixture://qa/plan/orders-q4@plan-r2 | orders-release-q4 | build-111 | staging | initial | 1 | 0 | 0 | 0 |",
            1,
        )
        self.assertEqual(
            assertion_status(
                validate(wrong_unexecuted_count, expected, "TMG-OUT-002"), "TMG-D015"
            ),
            "fail",
        )
        false_result = text.replace(
            "| POP-101 | - | - | - | - | - | - | - | - | unknown | 未取得 | 未実行 | 未判定 | - | API source inventoryが未取得 |",
            "| POP-101 | - | - | - | - | - | - | - | - | unknown | 未取得 | 未実行 | PASS | - | API source inventoryが未取得 |",
            1,
        )
        self.assertEqual(
            assertion_status(
                validate(false_result, expected, "TMG-OUT-002"), "TMG-D013"
            ),
            "fail",
        )

        text, expected = eval_case("test-management", "TMG-OUT-001")
        missing_readback = text.replace("| READBACK://e2e/16@run-r1 |", "| - |", 1)
        self.assertEqual(
            assertion_status(
                validate(missing_readback, expected, "TMG-OUT-001"), "TMG-D013"
            ),
            "fail",
        )

    def test_old_plan_approval_and_missing_source_cannot_claim_completion(self):
        validate = load_validator("test-management")
        text, expected = eval_case("test-management", "TMG-OUT-002")
        false_completion = text.replace(
            "| blocked | 未見積 | 未測定 |", "| 完了 | 未見積 | 未測定 |", 1
        )
        result = validate(false_completion, expected, "TMG-OUT-002")
        self.assertEqual(assertion_status(result, "TMG-D015"), "pass")
        self.assertEqual(assertion_status(result, "TMG-D018"), "fail")

        text, expected = eval_case("test-management", "TMG-OUT-001")
        stale_approval = text.replace(
            "| plan-r8 | QA manager | APPROVAL-PLAN-8 | 承認済み |",
            "| plan-r7 | QA manager | APPROVAL-PLAN-8 | 承認済み |",
            1,
        )
        self.assertEqual(
            assertion_status(
                validate(stale_approval, expected, "TMG-OUT-001"), "TMG-D023"
            ),
            "fail",
        )

        stale_input = text.replace(
            "| test-architecture-design | fixture://qa/architecture/orders-r1 | arch-r1 | orders-release-q4 | current | 取得済 |",
            "| test-architecture-design | fixture://qa/architecture/orders-r1 | arch-r1 | orders-release-q4 | stale | 取得済 |",
            1,
        )
        self.assertEqual(
            assertion_status(
                validate(stale_input, expected, "TMG-OUT-001"), "TMG-D020"
            ),
            "fail",
        )

    def test_required_readback_must_match_planned_revision_and_build(self):
        validate = load_validator("test-management")
        text, expected = eval_case("test-management", "TMG-OUT-001")
        stale_result = text.replace(
            "| POP-001 | e2e-test-execution | E2E-16 | run-r1 | orders-release-q4 |",
            "| POP-001 | e2e-test-execution | E2E-16 | run-r0 | orders-release-q4 |",
            1,
        )
        self.assertEqual(
            assertion_status(
                validate(stale_result, expected, "TMG-OUT-001"), "TMG-D021"
            ),
            "fail",
        )

        wrong_build = text.replace(
            "| POP-001 | e2e-test-execution | E2E-16 | run-r1 | orders-release-q4 | logical primary run for release-q4 | logical E2E run | build-110 |",
            "| POP-001 | e2e-test-execution | E2E-16 | run-r1 | orders-release-q4 | logical primary run for release-q4 | logical E2E run | build-109 |",
            1,
        )
        self.assertEqual(
            assertion_status(
                validate(wrong_build, expected, "TMG-OUT-001"), "TMG-D021"
            ),
            "fail",
        )

    def test_uncompleted_required_result_blocks_completion_and_failure_is_distinct(
        self,
    ):
        validate = load_validator("test-management")
        text, expected = eval_case("test-management", "TMG-OUT-001")
        no_final_snapshot = text.replace("| 状態 | 進行中 |", "| 状態 | 完了 |", 1)
        no_final_snapshot_result = validate(no_final_snapshot, expected, "TMG-OUT-001")
        self.assertEqual(assertion_status(no_final_snapshot_result, "TMG-D018"), "fail")

        incomplete = update_markdown_row(
            text,
            "POP-001",
            {
                "実行状態": "未実行",
                "結果状態": "未判定",
                "未取得 / 未実行理由": "required execution not started",
            },
        )
        incomplete = update_markdown_row(
            incomplete,
            "MON-8",
            {
                "実行済み数": "1",
                "未実行数": "1",
                "PASS数": "0",
                "FAIL数": "1",
                "未判定数": "1",
                "全体判定": "完了",
            },
        ).replace("| 状態 | 進行中 |", "| 状態 | 完了 |", 1)
        incomplete_result = validate(incomplete, expected, "TMG-OUT-001")
        self.assertEqual(assertion_status(incomplete_result, "TMG-D015"), "pass")
        self.assertEqual(assertion_status(incomplete_result, "TMG-D018"), "fail")

        execution_failure = update_markdown_row(
            text,
            "POP-002",
            {
                "実行状態": "実行失敗",
                "結果状態": "判定不能",
                "未取得 / 未実行理由": "runner exit error; result unavailable",
            },
        )
        execution_failure = update_markdown_row(
            execution_failure,
            "MON-8",
            {
                "実行済み数": "1",
                "実行失敗数": "1",
                "PASS数": "1",
                "FAIL数": "0",
                "判定不能数": "1",
            },
        )
        self.assertEqual(
            assertion_status(
                validate(execution_failure, expected, "TMG-OUT-001"), "TMG-D013"
            ),
            "pass",
        )
        self.assertEqual(
            assertion_status(
                validate(execution_failure, expected, "TMG-OUT-001"), "TMG-D015"
            ),
            "pass",
        )

        misclassified = execution_failure.replace(
            "実行失敗 | 判定不能 |", "実行失敗 | FAIL |", 1
        )
        self.assertEqual(
            assertion_status(
                validate(misclassified, expected, "TMG-OUT-001"), "TMG-D013"
            ),
            "fail",
        )

    def test_confirmed_zero_is_distinct_from_missing_source(self):
        validate = load_validator("test-management")
        text, expected = eval_case("test-management", "TMG-OUT-002")
        expected["expected_acquisition"]["POP-101"] = "0件確認済み"
        zero = update_markdown_row(
            text, "POP-101", {"planned revision": "inventory-r1"}
        )
        zero = update_markdown_row(
            zero,
            "POP-101",
            {
                "actual source owner": "testware-execution",
                "actual source_ref": "API-SOURCE-V2",
                "actual revision": "inventory-r1",
                "actual scope": "orders-release-q4",
                "acquired range": "API inventory lookup for build-111",
                "actual execution unit": "API logical run",
                "actual build": "build-111",
                "actual environment": "staging",
                "currentness": "current",
                "取得状態": "0件確認済み",
                "実行状態": "対象なし",
                "結果状態": "-",
                "source owner readback ref": "READBACK://api/inventory@inventory-r1",
                "未取得 / 未実行理由": "source owner confirmed zero for requested range",
            },
        )
        zero = update_markdown_row(
            zero,
            "MON-2",
            {
                "未取得数": "0",
                "0件確認済み数": "1",
                "未実行数": "0",
                "未判定数": "0",
                "対象なし数": "1",
            },
        )
        zero_result = validate(zero, expected, "TMG-OUT-002")
        self.assertEqual(
            assertion_status(zero_result, "TMG-D013"), "pass", zero_result.assertions
        )
        self.assertEqual(assertion_status(zero_result, "TMG-D014"), "pass")

    def test_missing_required_readback_is_reported_without_an_exception(self):
        validate = load_validator("test-management")
        text, expected = eval_case("test-management", "TMG-OUT-001")
        missing = remove_markdown_row(
            text, "POP-001", "## source owner readback・取得／実行状態"
        )
        result = validate(missing, expected, "TMG-OUT-001")
        self.assertEqual(assertion_status(result, "TMG-D013"), "fail")
        self.assertEqual(assertion_status(result, "TMG-D015"), "fail")
        self.assertIn(
            "POP-001",
            str(next(a.evidence for a in result.assertions if a.id == "TMG-D013")),
        )
        self.assertIn(
            "POP-001",
            str(next(a.evidence for a in result.assertions if a.id == "TMG-D015")),
        )

    def test_missing_optional_readback_is_unknown_not_zero(self):
        validate = load_validator("test-management")
        text, expected = eval_case("test-management", "TMG-OUT-001")
        optional = update_markdown_row(text, "POP-001", {"必須 / 任意": "任意"})
        optional = remove_markdown_row(
            optional, "POP-001", "## source owner readback・取得／実行状態"
        )
        result = validate(optional, expected, "TMG-OUT-001")
        self.assertEqual(assertion_status(result, "TMG-D013"), "fail")
        self.assertEqual(assertion_status(result, "TMG-D015"), "fail")

    def test_multiple_missing_readbacks_keep_each_population_id_as_evidence(self):
        validate = load_validator("test-management")
        text, expected = eval_case("test-management", "TMG-OUT-001")
        missing = remove_markdown_row(
            remove_markdown_row(
                text, "POP-001", "## source owner readback・取得／実行状態"
            ),
            "POP-002",
            "## source owner readback・取得／実行状態",
        )
        result = validate(missing, expected, "TMG-OUT-001")
        evidence = str(
            next(a.evidence for a in result.assertions if a.id == "TMG-D013")
        )
        self.assertEqual(assertion_status(result, "TMG-D013"), "fail")
        self.assertIn("POP-001", evidence)
        self.assertIn("POP-002", evidence)

    def test_missing_readback_and_completed_monitoring_never_claim_closure(self):
        validate = load_validator("test-management")
        text, expected = completed_plan_fixture()
        missing = remove_markdown_row(
            text, "POP-001", "## source owner readback・取得／実行状態"
        )
        result = validate(missing, expected, "TMG-OUT-001")
        self.assertEqual(assertion_status(result, "TMG-D013"), "fail")
        self.assertEqual(assertion_status(result, "TMG-D015"), "fail")
        self.assertEqual(assertion_status(result, "TMG-D018"), "fail")

    def test_invalid_readback_state_does_not_raise_during_monitoring(self):
        validate = load_validator("test-management")
        text, expected = eval_case("test-management", "TMG-OUT-001")
        malformed = update_markdown_row(
            text,
            "POP-001",
            {"取得状態": "not-a-state"},
            "## source owner readback・取得／実行状態",
        )
        result = validate(malformed, expected, "TMG-OUT-001")
        self.assertEqual(assertion_status(result, "TMG-D013"), "fail")
        self.assertEqual(assertion_status(result, "TMG-D015"), "fail")

    def test_plan_local_ids_must_match_fixture_owner_artifact_revision_and_scope(self):
        validate = load_validator("test-management")
        text, expected = eval_case("test-management", "TMG-OUT-001")
        malformed_refs = (
            update_markdown_row(
                text,
                "PLAN-001",
                {
                    "QA要求ref / revision": "fixture://qa/requirements/orders-q4#QAR-999@req-r3"
                },
            ),
            update_markdown_row(
                text,
                "PLAN-001",
                {
                    "architecture ref / revision": "fixture://qa/architecture/orders-r1#ARCH-999@arch-r1"
                },
            ),
            update_markdown_row(
                text,
                "PLAN-001",
                {"QA要求ref / revision": "fixture://qa/other#QAR-001@req-r3"},
            ),
            update_markdown_row(
                text,
                "PLAN-001",
                {
                    "QA要求ref / revision": "fixture://qa/requirements/orders-q4#QAR-001@req-r2"
                },
            ),
        )
        for broken in malformed_refs:
            with self.subTest(plan_ref=broken.split("PLAN-001", 1)[1][:100]):
                result = validate(broken, expected, "TMG-OUT-001")
                self.assertEqual(assertion_status(result, "TMG-D019"), "fail")

        blocked, blocked_expected = eval_case("test-management", "TMG-OUT-002")
        blocked_result = validate(blocked, blocked_expected, "TMG-OUT-002")
        self.assertEqual(assertion_status(blocked_result, "TMG-D019"), "pass")
        self.assertEqual(assertion_status(blocked_result, "TMG-D020"), "pass")

    def test_in_progress_plan_requires_matching_current_approval(self):
        validate = load_validator("test-management")
        text, expected = eval_case("test-management", "TMG-OUT-001")
        no_approval = update_markdown_row(text, "orders-release-q4", {"状態": "未承認"})
        result = validate(no_approval, expected, "TMG-OUT-001")
        self.assertEqual(assertion_status(result, "TMG-D023"), "fail")

        approval_placeholders = (
            "",
            "-",
            "—",
            "unknown",
            "UNKNOWN",
            "未取得",
            "未設定",
            "未確定",
            "未確認",
            "取得不能",
            "N/A",
            "n/a",
            "失効",
            "未承認",
            "不要",
        )
        for field in ("承認主体・role", "承認証拠ref"):
            for placeholder in approval_placeholders:
                with self.subTest(field=field, placeholder=placeholder):
                    broken = update_markdown_row(
                        text, "orders-release-q4", {field: placeholder}, "## 承認"
                    )
                    result = validate(broken, expected, "TMG-OUT-001")
                    self.assertEqual(
                        assertion_status(result, "TMG-D023"),
                        "fail",
                    )
                    approval_errors = next(
                        item.evidence
                        for item in result.assertions
                        if item.id == "TMG-D023"
                    )["approval_errors"]
                    self.assertTrue(
                        any(
                            error.get("reason")
                            == "active plan requires approval for this scope, artifact ref, and revision"
                            for error in approval_errors
                        )
                    )
                    self.assertTrue(
                        any(
                            error.get(field) == placeholder for error in approval_errors
                        )
                    )

        old_revision = update_markdown_row(
            text, "orders-release-q4", {"revision": "plan-r7"}, "## 承認"
        )
        self.assertEqual(
            assertion_status(
                validate(old_revision, expected, "TMG-OUT-001"), "TMG-D023"
            ),
            "fail",
        )

        wrong_scope = update_markdown_row(
            text,
            "orders-release-q4",
            {"対象scope": "orders-release-q3"},
            "## 承認",
        )
        result = validate(wrong_scope, expected, "TMG-OUT-001")
        self.assertEqual(assertion_status(result, "TMG-D023"), "fail")

        result = validate(text, expected, "TMG-OUT-001")
        self.assertEqual(assertion_status(result, "TMG-D023"), "pass")
        self.assertIn("未設定 / 対応中", text)

        draft, draft_expected = eval_case("test-management", "TMG-OUT-002")
        draft_result = validate(draft, draft_expected, "TMG-OUT-002")
        self.assertEqual(assertion_status(draft_result, "TMG-D023"), "pass")

        blocked = update_markdown_row(
            draft, "状態", {"値": "blocked"}, "## 成果物メタデータ"
        )
        self.assertEqual(
            assertion_status(
                validate(blocked, draft_expected, "TMG-OUT-002"), "TMG-D023"
            ),
            "pass",
        )

    def test_closure_allows_test_fail_and_formal_unmet_criterion(self):
        validate = load_validator("test-management")
        text, expected = completed_plan_fixture()
        result = validate(text, expected, "TMG-OUT-001")
        self.assertEqual(assertion_status(result, "TMG-D013"), "pass")
        self.assertEqual(assertion_status(result, "TMG-D018"), "pass")

    def test_closure_blocks_in_scope_open_risk_blocked_action_and_open_difference(self):
        validate = load_validator("test-management")
        text, expected = completed_plan_fixture()
        open_risk = update_markdown_row(
            text, "PROJ-RISK-001", {"状態": "対応中", "状態証拠ref": "-"}
        )
        self.assertEqual(
            assertion_status(validate(open_risk, expected, "TMG-OUT-001"), "TMG-D018"),
            "fail",
        )

        blocked_action = update_markdown_row(
            text, "CA-001", {"期限 / 状態": "未設定 / blocked", "結果ref": "未取得"}
        )
        self.assertEqual(
            assertion_status(
                validate(blocked_action, expected, "TMG-OUT-001"), "TMG-D018"
            ),
            "fail",
        )

        open_difference = add_difference_row(
            text,
            "| DIFF-001 | orders-release-q4 | API diagnosis is open | API-21@run-r2 | owner is investigating | QA lead | 対応中 | - | - |",
        )
        open_difference = update_markdown_row(
            open_difference, "MON-8", {"差異・未確定": "DIFF-001"}
        )
        result = validate(open_difference, expected, "TMG-OUT-001")
        self.assertEqual(assertion_status(result, "TMG-D024"), "pass")
        self.assertEqual(assertion_status(result, "TMG-D018"), "fail")

    def test_closure_does_not_ignore_missing_ids_or_unknown_scope_rows(self):
        validate = load_validator("test-management")
        text, expected = completed_plan_fixture()

        missing_risk_id = update_markdown_row(
            text,
            "PROJ-RISK-001",
            {"project risk ID": "", "状態": "対応中", "状態証拠ref": "-"},
        )
        risk_result = validate(missing_risk_id, expected, "TMG-OUT-001")
        self.assertEqual(assertion_status(risk_result, "TMG-D017"), "fail")
        self.assertEqual(assertion_status(risk_result, "TMG-D018"), "fail")

        missing_action_id = update_markdown_row(
            text,
            "CA-001",
            {"action ID": "", "期限 / 状態": "未設定 / blocked", "結果ref": "-"},
        )
        action_result = validate(missing_action_id, expected, "TMG-OUT-001")
        self.assertEqual(assertion_status(action_result, "TMG-D022"), "fail")
        self.assertEqual(assertion_status(action_result, "TMG-D018"), "fail")

        missing_difference_id = insert_table_row(
            text,
            "## 差異・未処理事項",
            "|  | orders-release-q4 | open gap | GAP-1@r1 | investigate | QA team | 対応中 | - | - |",
        )
        difference_result = validate(missing_difference_id, expected, "TMG-OUT-001")
        self.assertEqual(assertion_status(difference_result, "TMG-D024"), "fail")
        self.assertEqual(assertion_status(difference_result, "TMG-D018"), "fail")

        unknown_risk_scope = update_markdown_row(
            text,
            "PROJ-RISK-001",
            {
                "影響scope": "unknown",
                "状態": "解決済み",
                "状態証拠ref": "RISK-CLOSE-1",
            },
        )
        unknown_scope_result = validate(unknown_risk_scope, expected, "TMG-OUT-001")
        self.assertEqual(assertion_status(unknown_scope_result, "TMG-D018"), "fail")

    def test_out_of_scope_risk_does_not_block_completed_snapshot(self):
        validate = load_validator("test-management")
        text, expected = completed_plan_fixture()
        unrelated = update_markdown_row(
            text,
            "PROJ-RISK-001",
            {"影響scope": "payments", "状態": "blocked", "状態証拠ref": "-"},
        )
        result = validate(unrelated, expected, "TMG-OUT-001")
        self.assertEqual(assertion_status(result, "TMG-D017"), "pass")
        self.assertEqual(assertion_status(result, "TMG-D018"), "pass")

    def test_terminal_risk_and_action_statuses_need_evidence(self):
        validate = load_validator("test-management")
        text, expected = completed_plan_fixture()
        missing_risk_evidence = update_markdown_row(
            text, "PROJ-RISK-001", {"状態証拠ref": "-"}
        )
        result = validate(missing_risk_evidence, expected, "TMG-OUT-001")
        self.assertEqual(assertion_status(result, "TMG-D017"), "fail")
        self.assertEqual(assertion_status(result, "TMG-D018"), "fail")

        missing_action_result = update_markdown_row(text, "CA-001", {"結果ref": "-"})
        result = validate(missing_action_result, expected, "TMG-OUT-001")
        self.assertEqual(assertion_status(result, "TMG-D022"), "fail")
        self.assertEqual(assertion_status(result, "TMG-D018"), "fail")

    def test_formal_risk_acceptance_and_action_disposition_allow_activity_closure(self):
        validate = load_validator("test-management")
        text, expected = completed_plan_fixture()
        accepted = update_markdown_row(
            text,
            "PROJ-RISK-001",
            {
                "状態": "受容済み",
                "状態証拠ref": "RISK-ACCEPT-1",
                "承認主体・role": "QA director",
            },
        )
        accepted = update_markdown_row(
            accepted,
            "CA-001",
            {
                "期限 / 状態": "未設定 / 対応不要",
                "結果ref": "ACTION-NOT-NEEDED-1",
                "承認主体・role": "QA director",
            },
        )
        result = validate(accepted, expected, "TMG-OUT-001")
        self.assertEqual(assertion_status(result, "TMG-D017"), "pass")
        self.assertEqual(assertion_status(result, "TMG-D022"), "pass")
        self.assertEqual(assertion_status(result, "TMG-D018"), "pass")

    def test_unjudged_end_criterion_blocks_closure(self):
        validate = load_validator("test-management")
        text, expected = completed_plan_fixture()
        unjudged = update_markdown_row(text, "終了", {"判定状態": "未判定"})
        result = validate(unjudged, expected, "TMG-OUT-001")
        self.assertEqual(assertion_status(result, "TMG-D018"), "fail")


if __name__ == "__main__":
    unittest.main()
