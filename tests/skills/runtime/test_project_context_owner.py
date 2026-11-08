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
