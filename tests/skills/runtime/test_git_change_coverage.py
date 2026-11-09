"""Git-source enumeration and registry crosswalk integration tests."""

from __future__ import annotations

import copy
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_ROOT = (
    Path(__file__).resolve().parents[3] / "skills" / "feature-analysis" / "scripts"
)
sys.path.insert(0, str(SCRIPT_ROOT))

from git_source_inventory import handle as git_inventory  # noqa: E402
from reconcile_git_coverage import handle as reconcile  # noqa: E402
from test_feature_registry import fixture  # noqa: E402


def git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


class GitChangeCoverageTests(unittest.TestCase):
    def setUp(self) -> None:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name) / "repo"
        self.root.mkdir()
        git(self.root, "init", "-q")
        (self.root / "initial.md").write_text("first\n", encoding="utf-8")
        git(self.root, "add", ".")
        self.commit("baseline")
        base = git(self.root, "rev-parse", "HEAD")
        self.base = base
        for path in ("alpha.py", "beta.py"):
            (self.root / path).write_text("print('changed')\n", encoding="utf-8")
        git(self.root, "add", "-A")
        self.commit("two files")
        head = git(self.root, "rev-parse", "HEAD")
        self.inventory = git_inventory(
            {
                "repository_root": str(self.root),
                "authorized_root": str(self.root),
                "base_sha": base,
                "head_sha": head,
            }
        )
        self.assertEqual(self.inventory["status"], "complete")
        self.assertEqual(len(self.inventory["changes"]), 2)
        self.feature = fixture()
        snapshot = self.feature["snapshot"]
        snapshot["source_revision"] = head
        snapshot["sources"][0]["revision"] = head
        snapshot["changes"][0]["before_revision"] = base
        snapshot["changes"][0]["after_revision"] = head
        snapshot["changes"][0]["locator"] = "alpha.py"
        self.feature["observed_head_revision"] = head

    def commit(self, message: str) -> None:
        git(
            self.root,
            "-c",
            "user.email=qa@example.invalid",
            "-c",
            "user.name=QA",
            "commit",
            "-qm",
            message,
        )

    def request(self) -> dict:
        return {
            "git_inventory": self.inventory,
            "registry_request": self.feature,
            "source_id": "SRC-001",
        }

    def test_missing_change_cannot_report_complete(self) -> None:
        result = reconcile(self.request())
        self.assertEqual(result["status"], "incomplete", result)
        self.assertEqual(result["coverage"]["missing_git_paths"], ["beta.py"])
        self.assertEqual(result["coverage"]["rate"], 0.5)
        self.assertIn("git_changes_not_registered", result["reasons"])

    def test_all_changed_paths_have_classification_and_handoff_hash(self) -> None:
        snapshot = self.feature["snapshot"]
        extra = copy.deepcopy(snapshot["changes"][0])
        extra.update(
            id="DIF-002",
            locator="beta.py",
            classification="no_impact",
            feature_ids=[],
            reason="Documentation of independent coverage",
            approval_ref="approval/reviewed-no-impact",
        )
        snapshot["changes"].append(extra)
        result = reconcile(self.request())
        self.assertEqual(result["status"], "complete", result)
        self.assertEqual(result["coverage"]["rate"], 1.0)
        self.assertRegex(
            result["coverage"]["candidate_snapshot_sha256"], r"^[0-9a-f]{64}$"
        )
        snapshot["changes"][1]["classification"] = "unclassified"
        self.assertEqual(reconcile(self.request())["status"], "incomplete")

    def test_stale_and_unconfirmed_git_are_not_complete(self) -> None:
        self.feature["snapshot"]["sources"][0]["revision"] = "other-revision"
        self.assertEqual(reconcile(self.request())["status"], "stale")
        self.feature["snapshot"]["sources"][0]["revision"] = self.inventory["head_sha"]
        self.inventory["complete_change_listing"] = False
        self.assertEqual(reconcile(self.request())["status"], "incomplete")

    def test_untracked_locator_is_detected(self) -> None:
        self.feature["snapshot"]["changes"][0]["locator"] = "missing.py"
        result = reconcile(self.request())
        self.assertEqual(result["status"], "incomplete")
        self.assertEqual(
            result["coverage"]["unmatched_registry_change_ids"], ["DIF-001"]
        )

    def test_change_revision_must_match_git_base_and_head(self) -> None:
        self.feature["snapshot"]["changes"][0]["before_revision"] = "unrelated-base"
        result = reconcile(self.request())
        self.assertEqual(result["status"], "incomplete")
        self.assertEqual(
            result["coverage"]["mismatched_revision_change_ids"], ["DIF-001"]
        )

    def test_malformed_git_manifest_rejected(self) -> None:
        self.inventory["changes"][0]["after_path"] = "missing-from-tree.py"
        result = reconcile(self.request())
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["reasons"], ["changed_path_missing_at_head"])


if __name__ == "__main__":
    unittest.main()
