from __future__ import annotations

import sys
import unittest
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[3] / "skills"
sys.path.insert(0, str(SKILL_ROOT / "project-context" / "scripts"))
from project_context import TEMPLATE, handle  # noqa: E402


def context() -> str:
    return TEMPLATE.read_text(encoding="utf-8").replace(
        "- プロジェクト:", "- プロジェクト: Sample"
    )


class ProjectContextOwnerTests(unittest.TestCase):
    def test_reuses_shared_parser_and_preserves_dec_asm(self) -> None:
        output = handle(
            {"operation": "inspect", "markdown": context(), "required_keys": []}
        )
        self.assertEqual(output["status"], "current", output)
        self.assertIn("qa.workflow_state_root", output["fields"])

    def test_blank_template_cannot_be_current(self) -> None:
        result = handle(
            {
                "operation": "inspect",
                "markdown": TEMPLATE.read_text(encoding="utf-8"),
                "required_keys": [],
            }
        )
        self.assertEqual(result["status"], "blocked")

    def test_required_field_is_operation_scoped(self) -> None:
        output = handle(
            {
                "operation": "inspect",
                "markdown": context(),
                "required_keys": ["qa.workflow_state_root"],
            }
        )
        self.assertEqual(output["status"], "incomplete")
        self.assertEqual(output["required"]["missing_keys"], ["qa.workflow_state_root"])

    def test_existing_and_duplicate_candidates(self) -> None:
        row = {
            "ref": "a",
            "status": "readable",
            "markdown": context(),
            "revision": "v1",
        }
        req = {
            "operation": "discover",
            "project_name": "Sample",
            "enumeration_complete": True,
            "candidates": [row],
        }
        self.assertEqual(handle(req)["status"], "existing")
        req["candidates"].append({**row, "ref": "b"})
        self.assertEqual(handle(req)["status"], "ambiguous")

    def test_denied_cannot_prove_absence(self) -> None:
        req = {
            "operation": "discover",
            "project_name": "Sample",
            "enumeration_complete": True,
            "candidates": [{"ref": "a", "status": "denied"}],
        }
        self.assertEqual(handle(req)["status"], "unconfirmed")

    def test_new_project_requires_absence_and_provider(self) -> None:
        data = {
            "operation": "prepare-create",
            "project_name": "Sample",
            "enumeration_complete": True,
            "candidates": [{"ref": "context.md", "status": "absent"}],
        }
        out = handle(data)
        self.assertEqual(out["status"], "draft", out)
        self.assertIn("- プロジェクト: Sample", out["artifact_markdown"])
        self.assertIn("provider", out["reason"])
        data["enumeration_complete"] = False
        self.assertEqual(handle(data)["status"], "blocked")

    def test_update_only_one_stable_key_and_keep_sections(self) -> None:
        original = context()
        result = handle(
            {
                "operation": "prepare-update",
                "markdown": original,
                "artifact_ref": "context.md",
                "expected_revision": "rev-1",
                "source_ref": "issue-1",
                "source_revision": "rev-2",
                "change_reason": "環境更新",
                "updates": {"qa.workflow_state_root": "qa/state"},
            }
        )
        self.assertEqual(result["status"], "draft", result)
        self.assertIn("qa/state", result["artifact_markdown"])
        self.assertEqual(
            original.split("## 12.")[1].split("## 14.")[0],
            result["artifact_markdown"].split("## 12.")[1].split("## 14.")[0],
        )

    def test_unknown_key_and_injected_marker_rejected(self) -> None:
        base = {
            "operation": "prepare-update",
            "markdown": context(),
            "artifact_ref": "context.md",
            "expected_revision": "rev-1",
            "source_ref": "issue-1",
            "source_revision": "rev-2",
            "change_reason": "設定修正",
        }
        self.assertEqual(
            handle({**base, "updates": {"qa.feature_artifact_root": "out"}})["status"],
            "blocked",
        )
        self.assertEqual(
            handle({**base, "updates": {"qa.workflow_state_root": "<!-- fake -->"}})[
                "status"
            ],
            "blocked",
        )

    def test_update_requires_change_provenance(self) -> None:
        result = handle(
            {
                "operation": "prepare-update",
                "markdown": context(),
                "artifact_ref": "context.md",
                "expected_revision": "rev-1",
                "source_ref": "issue/1",
                "source_revision": "rev-2",
                "updates": {"qa.workflow_state_root": "qa/state"},
            }
        )
        self.assertEqual(result["status"], "blocked")

    def test_dec_asm_materialize_preserves_existing_prose(self) -> None:
        original = (
            context()
            .replace("## 13. 仮定", "決定事項の根拠メモ。\n\n## 13. 仮定")
            .replace("## 14. 既存QA成果物", "仮定の注釈。\n\n## 14. 既存QA成果物")
        )
        cells = {
            "確定内容": "承認済み配置",
            "状態": "有効",
            "決定根拠": "approval/1",
            "影響範囲": "QA",
            "関係": "独立",
            "関連仕様根拠ID": "",
            "置換先ID": "",
            "備考": "",
        }
        request = {
            "operation": "prepare-ids",
            "markdown": original,
            "artifact_mode": "create",
            "artifact_ref": "project-context.md",
            "expected_revision": None,
            "source_ref": "issue/1",
            "source_revision": "r1",
            "change_reason": "初期配置",
            "dec_asm_owner": "project-context",
            "decisions": [
                {
                    "draft_key": "placement",
                    "identity_action": "new",
                    "reuse_id": None,
                    "cells": cells,
                }
            ],
            "assumptions": [],
        }
        result = handle(request)
        self.assertEqual(result["status"], "draft", result)
        self.assertEqual(
            result["allocated_ids"],
            [{"draft_key": "placement", "stable_id": "DEC-001"}],
        )
        self.assertIn("決定事項の根拠メモ。", result["artifact_markdown"])
        self.assertIn("仮定の注釈。", result["artifact_markdown"])
        self.assertEqual(
            original.split("## 14.")[1],
            result["artifact_markdown"].split("## 14.")[1],
        )
        self.assertEqual(
            handle(
                {
                    "operation": "inspect",
                    "markdown": result["artifact_markdown"],
                    "required_keys": [],
                }
            )["decision_ids"],
            ["DEC-001"],
        )
        update = dict(request)
        update.update(
            markdown=result["artifact_markdown"],
            artifact_mode="update",
            expected_revision="revision-1",
            decisions=[
                {
                    "draft_key": None,
                    "identity_action": "reuse",
                    "reuse_id": "DEC-001",
                    "cells": cells,
                }
            ],
        )
        self.assertEqual(handle(update)["status"], "draft")

    def test_dec_asm_wrong_owner_or_lost_id_is_blocked(self) -> None:
        data = {
            "operation": "prepare-ids",
            "markdown": context(),
            "artifact_mode": "create",
            "artifact_ref": "context.md",
            "expected_revision": None,
            "source_ref": "issue/1",
            "source_revision": "rev-1",
            "change_reason": "初回",
            "dec_asm_owner": "external",
            "decisions": [],
            "assumptions": [],
        }
        self.assertEqual(handle(data)["status"], "blocked")
        data["dec_asm_owner"] = "project-context"
        draft = handle(data)
        self.assertEqual(draft["status"], "draft", draft)
        data.update(
            artifact_mode="update",
            expected_revision=None,
        )
        self.assertEqual(handle(data)["status"], "blocked")

    def test_existing_placement_is_only_a_reuse_candidate(self) -> None:
        record = {
            "owner": "project-context",
            "scope": "Sample",
            "target_ref": "context.md",
            "revision": "r1",
            "approval_ref": "approval/1",
        }
        request = {
            "operation": "placement",
            "owner": "project-context",
            "scope": "Sample",
            "target_ref": "context.md",
            "existing_policy": record,
        }
        self.assertEqual(handle(request)["status"], "reuse_candidate")
        request["target_ref"] = "moved.md"
        self.assertEqual(handle(request)["status"], "approval_required")


if __name__ == "__main__":
    unittest.main()
