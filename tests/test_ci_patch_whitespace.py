"""Contract tests for event-based whitespace checks in clean checkouts."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / ".github" / "check_patch_whitespace.py"


class PatchWhitespaceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="patch whitespace ")
        self.root = Path(self.temp.name)
        self.repo = self.root / "repository"
        self.repo.mkdir()
        subprocess.run(["git", "init", "-q", "-b", "main"], cwd=self.repo, check=True)
        subprocess.run(
            ["git", "config", "user.name", "Whitespace Test"],
            cwd=self.repo,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "whitespace@example.invalid"],
            cwd=self.repo,
            check=True,
        )
        self.event_path = self.root / "event.json"
        self.write_and_commit("tracked.txt", b"base\n", "base")
        self.base_sha = self.head_sha()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def head_sha(self) -> str:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=self.repo,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

    def write_and_commit(self, name: str, content: bytes, message: str) -> None:
        (self.repo / name).write_bytes(content)
        subprocess.run(["git", "add", name], cwd=self.repo, check=True)
        subprocess.run(["git", "commit", "-qm", message], cwd=self.repo, check=True)

    def run_check(
        self, event_name: str, event: dict[str, object], github_sha: str
    ) -> subprocess.CompletedProcess[str]:
        self.event_path.write_text(json.dumps(event), encoding="utf-8")
        env = os.environ.copy()
        env.update(
            {
                "GITHUB_EVENT_NAME": event_name,
                "GITHUB_EVENT_PATH": str(self.event_path),
                "GITHUB_SHA": github_sha,
            }
        )
        return subprocess.run(
            [sys.executable, str(SCRIPT)],
            cwd=self.repo,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_pull_request_and_push_compare_commits_in_clean_checkout(self) -> None:
        self.write_and_commit("tracked.txt", b"base\nclean change\n", "clean")
        clean_head = self.head_sha()
        self.assertEqual(
            subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=self.repo,
                check=True,
                capture_output=True,
                text=True,
            ).stdout,
            "",
        )

        pull_request = self.run_check(
            "pull_request",
            {
                "pull_request": {
                    "base": {"sha": self.base_sha},
                    "head": {"sha": clean_head},
                }
            },
            clean_head,
        )
        self.assertEqual(pull_request.returncode, 0, pull_request.stderr)

        push = self.run_check("push", {"before": self.base_sha}, clean_head)
        self.assertEqual(push.returncode, 0, push.stderr)

    def test_whitespace_errors_fail_for_pr_push_and_initial_push(self) -> None:
        self.write_and_commit("tracked.txt", b"base\nclean change\n", "clean")
        clean_head = self.head_sha()
        self.write_and_commit("tracked.txt", b"base\nclean change \n", "whitespace")
        dirty_head = self.head_sha()

        cases = (
            (
                "pull_request",
                {
                    "pull_request": {
                        "base": {"sha": self.base_sha},
                        "head": {"sha": dirty_head},
                    }
                },
                dirty_head,
            ),
            ("push", {"before": clean_head}, dirty_head),
            ("push", {"before": "0" * len(self.base_sha)}, dirty_head),
        )
        for event_name, event, github_sha in cases:
            with self.subTest(event_name=event_name, event=event):
                result = self.run_check(event_name, event, github_sha)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("trailing whitespace", result.stdout + result.stderr)

    def test_invalid_event_sha_metadata_fails_closed(self) -> None:
        cases = (
            (
                "pull_request",
                {
                    "pull_request": {
                        "base": {"sha": "a" * 64},
                        "head": {"sha": self.base_sha},
                    }
                },
                self.base_sha,
                "formats do not match",
            ),
            ("push", {"before": "0"}, self.base_sha, "initial push"),
            ("push", {"before": "0" * 64}, self.base_sha, "initial push"),
            (
                "push",
                {"before": "a" * 64},
                self.base_sha,
                "formats do not match",
            ),
        )
        for event_name, event, github_sha, message in cases:
            with self.subTest(event_name=event_name, event=event):
                result = self.run_check(event_name, event, github_sha)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(message, result.stderr)


if __name__ == "__main__":
    unittest.main()
