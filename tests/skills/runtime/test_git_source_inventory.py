from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SCRIPT_DIR = (
    Path(__file__).resolve().parents[3] / "skills" / "feature-analysis" / "scripts"
)
sys.path.insert(0, str(SCRIPT_DIR))
import git_source_inventory as inventory  # noqa: E402
from git_source_inventory import handle  # noqa: E402


def git(root: Path, *args: str) -> str:
    process = subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        check=True,
    )
    return process.stdout.strip()


class GitSourceInventoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "product"
        self.root.mkdir()
        git(self.root, "init", "-q")
        (self.root / "api.py").write_text("def call():\n    pass\n", encoding="utf-8")
        git(self.root, "add", ".")
        git(
            self.root,
            "-c",
            "user.email=qa@example.invalid",
            "-c",
            "user.name=QA",
            "commit",
            "-qm",
            "initial",
        )
        self.first = git(self.root, "rev-parse", "HEAD")

    def request(self, base: str | None, head: str) -> dict:
        return {
            "repository_root": str(self.root),
            "authorized_root": str(self.root),
            "base_sha": base,
            "head_sha": head,
        }

    def test_initial_snapshot_has_no_fictitious_diff(self) -> None:
        result = handle(self.request(None, self.first))
        self.assertEqual(result["status"], "complete", result)
        self.assertEqual(result["files"][0]["path"], "api.py")
        self.assertFalse(result["complete_change_listing"])
        self.assertIsNone(result["feature_count"])

    def test_rename_and_added_path_are_enumerated(self) -> None:
        git(self.root, "mv", "api.py", "api renamed.py")
        (self.root / "batch.py").write_text("print('run')\n", encoding="utf-8")
        git(self.root, "add", "-A")
        git(
            self.root,
            "-c",
            "user.email=qa@example.invalid",
            "-c",
            "user.name=QA",
            "commit",
            "-qm",
            "rename and add",
        )
        head = git(self.root, "rev-parse", "HEAD")
        result = handle(self.request(self.first, head))
        self.assertEqual(result["status"], "complete", result)
        self.assertEqual(len(result["files"]), 2)
        self.assertEqual(len(result["changes"]), 2)
        rename = next(c for c in result["changes"] if c["status"].startswith("R"))
        self.assertEqual(rename["before_path"], "api.py")
        self.assertEqual(rename["after_path"], "api renamed.py")
        self.assertTrue(result["complete_change_listing"])

    def test_path_with_newline_is_preserved_as_one_path(self) -> None:
        name = "line\nbreak.txt"
        (self.root / name).write_text("x", encoding="utf-8")
        git(self.root, "add", "--", name)
        git(
            self.root,
            "-c",
            "user.email=qa@example.invalid",
            "-c",
            "user.name=QA",
            "commit",
            "-qm",
            "weird path",
        )
        result = handle(self.request(self.first, git(self.root, "rev-parse", "HEAD")))
        self.assertEqual(result["status"], "complete", result)
        self.assertIn(name, [f["path"] for f in result["files"]])

    def test_rejects_different_authorized_root(self) -> None:
        request = self.request(None, self.first)
        request["authorized_root"] = self.tmp.name
        self.assertEqual(handle(request)["status"], "blocked")

    def test_rejects_untrusted_revision_and_nonexistent_commit(self) -> None:
        request = self.request(None, "HEAD")
        self.assertEqual(handle(request)["status"], "blocked")
        request["head_sha"] = "f" * 40
        self.assertEqual(handle(request)["status"], "blocked")

    def test_cli_requires_trusted_root_from_host(self) -> None:
        request = self.request(None, self.first)
        script = SCRIPT_DIR / "git_source_inventory.py"
        env = dict(os.environ)
        env.pop("QA_FEATURE_AUTHORIZED_ROOT", None)
        command = [sys.executable, str(script)]
        denied = subprocess.run(
            command, input=json.dumps(request), env=env,
            text=True, capture_output=True, check=True
        )
        self.assertEqual(json.loads(denied.stdout)["status"], "blocked")
        env["QA_FEATURE_AUTHORIZED_ROOT"] = str(self.root)
        accepted = subprocess.run(
            command, input=json.dumps(request), env=env,
            text=True, capture_output=True, check=True
        )
        self.assertEqual(json.loads(accepted.stdout)["status"], "complete")

    def test_git_output_limit_blocks_instead_of_reporting_complete(self) -> None:
        with mock.patch.object(inventory, "MAX_OUTPUT", 1):
            result = handle(self.request(None, self.first))
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["reason"], "git_output_too_large")


if __name__ == "__main__":
    unittest.main()
