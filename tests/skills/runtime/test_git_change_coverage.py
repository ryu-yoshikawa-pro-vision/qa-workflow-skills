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
        self.assertEqual(reconcile(self.request())["status"], "blocked")
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

    def test_pr_update_checks_new_base_and_previous_head_diffs(self) -> None:
        snapshot = self.feature["snapshot"]
        prior = copy.deepcopy(snapshot)
        prior["source_revision"] = self.base
        prior["sources"][0]["revision"] = self.base
        prior["changes"][0].update(
            before_revision="historical-base",
            after_revision=self.base,
        )
        snapshot["changes"][0] = copy.deepcopy(prior["changes"][0])
        self.feature["previous_snapshot"] = prior
        snapshot["event"] = "pr_update"
        snapshot["event_basis"] = {
            "base_sha": self.base,
            "head_sha": self.inventory["head_sha"],
            "previous_head_sha": self.base,
        }
        snapshot["artifact_revision"] = "art-v2"
        snapshot["previous_artifact_revision"] = "art-v1"
        snapshot["operation_id"] = "op-v2"
        current = copy.deepcopy(snapshot["changes"][0])
        current.update(
            id="DIF-002",
            before_revision=self.base,
            after_revision=self.inventory["head_sha"],
        )
        snapshot["changes"].append(current)
        second = copy.deepcopy(current)
        second.update(
            id="DIF-003",
            locator="beta.py",
            classification="no_impact",
            feature_ids=[],
            reason="Reviewed independent change",
            approval_ref="approval/qa",
        )
        snapshot["changes"].append(second)
        req = self.request()
        result = reconcile(req)
        self.assertEqual(result["status"], "incomplete", result)
        self.assertIn("previous_head_diff_not_enumerated", result["reasons"])
        req["previous_head_git_inventory"] = copy.deepcopy(self.inventory)
        result = reconcile(req)
        self.assertEqual(result["status"], "complete", result)
        self.assertEqual(len(result["coverage"]["previous_head_change_paths"]), 2)
        req["previous_head_git_inventory"]["changes"].append(
            {"status": "D", "before_path": "transient.py", "after_path": "transient.py"}
        )
        result = reconcile(req)
        self.assertEqual(result["status"], "incomplete", result)
        self.assertIn("transient.py", result["coverage"]["missing_git_paths"])
        req["previous_head_git_inventory"]["base_sha"] = "f" * 40
        self.assertEqual(reconcile(req)["status"], "stale")

    def test_previous_head_only_change_uses_its_actual_before_sha(self) -> None:
        previous_head = self.inventory["head_sha"]
        git(self.root, "checkout", "-q", "-b", "intermediate", self.base)
        (self.root / "temporary.py").write_text("temporary\n", encoding="utf-8")
        git(self.root, "add", "temporary.py")
        self.commit("previous PR head")
        middle_sha = git(self.root, "rev-parse", "HEAD")
        git(self.root, "checkout", "-q", "--detach", previous_head)
        earlier_diff = git_inventory(
            {
                "repository_root": str(self.root),
                "authorized_root": str(self.root),
                "base_sha": middle_sha,
                "head_sha": previous_head,
            }
        )
        self.assertEqual(earlier_diff["status"], "complete", earlier_diff)
        data = self.feature
        old = copy.deepcopy(data["snapshot"])
        old["source_revision"] = middle_sha
        old["sources"][0]["revision"] = middle_sha
        old["changes"][0].update(
            before_revision="historical-base",
            after_revision=middle_sha,
        )
        data["snapshot"]["changes"][0] = copy.deepcopy(old["changes"][0])
        data["previous_snapshot"] = old
        snapshot = data["snapshot"]
        snapshot["event"] = "pr_update"
        snapshot["event_basis"] = {
            "base_sha": self.base,
            "head_sha": previous_head,
            "previous_head_sha": middle_sha,
        }
        snapshot["artifact_revision"] = "art-v2"
        snapshot["previous_artifact_revision"] = "art-v1"
        snapshot["operation_id"] = "op-v2"
        pairs = [
            (self.base, "alpha.py"),
            (self.base, "beta.py"),
            (middle_sha, "alpha.py"),
            (middle_sha, "beta.py"),
            (middle_sha, "temporary.py"),
        ]
        for i, (before, path) in enumerate(pairs):
            row = copy.deepcopy(snapshot["changes"][0])
            row.update(
                id=f"DIF-{i + 2:03d}",
                locator=path,
                before_revision=before,
                after_revision=previous_head,
                classification="impact",
            )
            snapshot["changes"].append(row)
        result = reconcile(
            {
                **self.request(),
                "previous_head_git_inventory": earlier_diff,
            }
        )
        self.assertEqual(result["status"], "complete", result)
        self.assertEqual(result["coverage"]["rate"], 1.0)
        self.assertIn("temporary.py", result["coverage"]["previous_head_change_paths"])
        snapshot["changes"].pop(2)
        missing_one = reconcile(
            {
                **self.request(),
                "previous_head_git_inventory": earlier_diff,
            }
        )
        self.assertEqual(missing_one["status"], "incomplete")
        self.assertEqual(missing_one["coverage"]["rate"], 0.8)
        self.assertIn(
            "git_change_revision_pairs_not_registered", missing_one["reasons"]
        )

    def test_consecutive_pr_updates_keep_historical_dif_revision(self) -> None:
        first_head = self.inventory["head_sha"]
        historical = copy.deepcopy(self.feature["snapshot"])
        (self.root / "gamma.py").write_text("print('gamma')\n", encoding="utf-8")
        git(self.root, "add", "gamma.py")
        self.commit("second PR update")
        new_head = git(self.root, "rev-parse", "HEAD")
        self.inventory = git_inventory(
            {
                "repository_root": str(self.root),
                "authorized_root": str(self.root),
                "base_sha": self.base,
                "head_sha": new_head,
            }
        )
        previous_diff = git_inventory(
            {
                "repository_root": str(self.root),
                "authorized_root": str(self.root),
                "base_sha": first_head,
                "head_sha": new_head,
            }
        )
        snapshot = self.feature["snapshot"]
        self.feature["previous_snapshot"] = historical
        snapshot["event"] = "pr_update"
        snapshot["event_basis"] = {
            "base_sha": self.base,
            "head_sha": new_head,
            "previous_head_sha": first_head,
        }
        snapshot["source_revision"] = new_head
        snapshot["sources"][0]["revision"] = new_head
        self.feature["observed_head_revision"] = new_head
        snapshot["operation_id"] = "op-v2"
        snapshot["artifact_revision"] = "art-v2"
        snapshot["previous_artifact_revision"] = "art-v1"
        pairs = [
            (self.base, "alpha.py"),
            (self.base, "beta.py"),
            (self.base, "gamma.py"),
            (first_head, "gamma.py"),
        ]
        for i, (before, path) in enumerate(pairs, start=2):
            row = copy.deepcopy(snapshot["changes"][0])
            row.update(
                id=f"DIF-{i:03d}",
                locator=path,
                before_revision=before,
                after_revision=new_head,
            )
            snapshot["changes"].append(row)
        result = reconcile(
            {**self.request(), "previous_head_git_inventory": previous_diff}
        )
        self.assertEqual(result["status"], "complete", result)
        self.assertEqual(result["coverage"]["rate"], 1.0)
        self.assertEqual(snapshot["changes"][0]["after_revision"], first_head)
        snapshot["changes"].pop()
        report = reconcile(
            {**self.request(), "previous_head_git_inventory": previous_diff}
        )
        self.assertEqual(report["status"], "incomplete", report)
        self.assertEqual(report["coverage"]["rate"], 0.75)

    def test_malformed_git_manifest_rejected(self) -> None:
        self.inventory["changes"][0]["after_path"] = "missing-from-tree.py"
        result = reconcile(self.request())
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["reasons"], ["changed_path_missing_at_head"])


if __name__ == "__main__":
    unittest.main()
