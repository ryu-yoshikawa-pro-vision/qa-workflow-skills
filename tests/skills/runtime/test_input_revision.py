from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "skills" / "qa-workflow" / "scripts" / "input_revision.py"
ABC_SHA256 = "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"

_SPEC = importlib.util.spec_from_file_location("input_revision_under_test", SCRIPT)
assert _SPEC is not None and _SPEC.loader is not None
input_revision = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(input_revision)


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def _stdout_json(result: subprocess.CompletedProcess[str]) -> dict:
    return json.loads(result.stdout)


class InputRevisionTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "inputs"
        self.root.mkdir()
        self.state_dir = Path(self._tmp.name) / "state"
        self.state_dir.mkdir()
        self.state = self.state_dir / "input-revisions.json"
        (self.root / "spec.md").write_bytes(b"abc")
        (self.root / "sub").mkdir()
        (self.root / "sub" / "code.txt").write_bytes(b"code")

    def _record(self, *paths: str) -> subprocess.CompletedProcess[str]:
        return _run(
            "record",
            "--root",
            str(self.root),
            "--state",
            str(self.state),
            *paths,
        )

    def _compare(self, *paths: str) -> dict:
        result = _run(
            "compare",
            "--root",
            str(self.root),
            "--state",
            str(self.state),
            *paths,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return _stdout_json(result)

    def test_hash_matches_known_sha256_and_keys_are_sorted(self) -> None:
        result = _run("hash", "--root", str(self.root), "sub/code.txt", "spec.md")
        self.assertEqual(result.returncode, 0, result.stderr)
        document = _stdout_json(result)
        self.assertEqual(document["schema_version"], "input-revision-v1")
        self.assertEqual(document["root"], str(self.root.resolve()))
        self.assertEqual(list(document["revisions"]), ["spec.md", "sub/code.txt"])
        self.assertEqual(document["revisions"]["spec.md"], ABC_SHA256)

    def test_cli_hash_output_is_stable_json(self) -> None:
        first = _run("hash", "--root", str(self.root), "spec.md")
        second = _run("hash", "--root", str(self.root), "spec.md")
        self.assertEqual(first.stdout, second.stdout)
        self.assertEqual(first.returncode, 0)

    def test_record_then_compare_is_same(self) -> None:
        recorded = self._record("spec.md", "sub/code.txt")
        self.assertEqual(recorded.returncode, 0, recorded.stderr)
        self.assertEqual(
            json.loads(self.state.read_text(encoding="utf-8")),
            _stdout_json(recorded),
        )
        result = self._compare("spec.md", "sub/code.txt")
        self.assertEqual(result["status"], "same")
        self.assertEqual(result["changed"], [])
        self.assertEqual(result["added"], [])
        self.assertEqual(result["removed"], [])

    def test_changed_file_is_reported_as_changed(self) -> None:
        self._record("spec.md", "sub/code.txt")
        (self.root / "spec.md").write_bytes(b"changed")
        result = self._compare("spec.md", "sub/code.txt")
        self.assertEqual(result["status"], "changed")
        self.assertEqual(result["changed"], ["spec.md"])
        self.assertEqual(result["added"], [])
        self.assertEqual(result["removed"], [])

    def test_added_and_removed_targets(self) -> None:
        self._record("spec.md")
        added = self._compare("spec.md", "sub/code.txt")
        self.assertEqual(added["status"], "changed")
        self.assertEqual(added["added"], ["sub/code.txt"])
        self.assertEqual(added["removed"], [])

        self._record("spec.md", "sub/code.txt")
        removed = self._compare("spec.md")
        self.assertEqual(removed["status"], "changed")
        self.assertEqual(removed["added"], [])
        self.assertEqual(removed["removed"], ["sub/code.txt"])

    def test_missing_empty_or_broken_state_is_no_record(self) -> None:
        cases = {
            "missing": None,
            "empty": "",
            "broken": "{not json",
            "wrong_schema": json.dumps({"schema_version": "other", "revisions": {}}),
        }
        for label, content in cases.items():
            with self.subTest(label=label):
                if content is None:
                    self.state.unlink(missing_ok=True)
                else:
                    self.state.write_text(content, encoding="utf-8")
                result = self._compare("spec.md")
                self.assertEqual(result["status"], "no_record")
                self.assertEqual(result["changed"], [])
                self.assertEqual(result["added"], [])
                self.assertEqual(result["removed"], [])

    def test_record_replaces_existing_state_atomically(self) -> None:
        self.state.write_text(
            json.dumps(
                {
                    "schema_version": "input-revision-v1",
                    "root": "old",
                    "revisions": {"old.md": "0" * 64},
                }
            ),
            encoding="utf-8",
        )
        result = self._record("spec.md")
        self.assertEqual(result.returncode, 0, result.stderr)
        stored = json.loads(self.state.read_text(encoding="utf-8"))
        self.assertEqual(stored["revisions"], {"spec.md": ABC_SHA256})
        leftovers = [
            entry.name
            for entry in self.state_dir.iterdir()
            if entry.name != self.state.name
        ]
        self.assertEqual(leftovers, [])

    def test_record_fails_without_creating_missing_parent(self) -> None:
        missing_state = self.state_dir / "missing" / "input-revisions.json"
        result = _run(
            "record",
            "--root",
            str(self.root),
            "--state",
            str(missing_state),
            "spec.md",
        )
        self.assertEqual(result.returncode, 2)
        self.assertEqual(
            _stdout_json(result), {"status": "error", "reason": "state_parent_missing"}
        )
        self.assertFalse(missing_state.parent.exists())

    def test_invalid_targets_exit_2_with_error_status(self) -> None:
        outside_file = Path(self._tmp.name) / "outside.txt"
        outside_file.write_bytes(b"outside")
        try:
            (self.root / "link-file").symlink_to(outside_file)
            symlink_ok = True
        except OSError:
            symlink_ok = False
        cases = {
            "parent_traversal": ("../outside.txt", "path_outside_root"),
            "absolute": (str(outside_file), "path_outside_root"),
            "directory": ("sub", "not_a_regular_file"),
            "missing": ("nope.md", "path_not_found"),
            "empty": ("", "invalid_path"),
        }
        if symlink_ok:
            cases["symlink_outside_root"] = ("link-file", "path_outside_root")
        for label, (target, reason) in cases.items():
            with self.subTest(label=label):
                result = _run("hash", "--root", str(self.root), target)
                self.assertEqual(result.returncode, 2, result.stdout)
                self.assertEqual(
                    _stdout_json(result), {"status": "error", "reason": reason}
                )

    def test_compare_with_invalid_target_exits_2(self) -> None:
        self._record("spec.md")
        result = _run(
            "compare",
            "--root",
            str(self.root),
            "--state",
            str(self.state),
            "../outside.txt",
        )
        self.assertEqual(result.returncode, 2)
        self.assertEqual(_stdout_json(result)["status"], "error")

    def test_invalid_arguments_exit_2_with_json_error(self) -> None:
        result = _run("compare", "--root", str(self.root), "spec.md")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(
            _stdout_json(result),
            {"status": "error", "reason": "invalid_arguments"},
        )

    def test_root_must_be_directory(self) -> None:
        result = _run("hash", "--root", str(self.root / "spec.md"), "spec.md")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(
            _stdout_json(result),
            {"status": "error", "reason": "root_not_directory"},
        )

    def test_size_limit_is_32_mib(self) -> None:
        self.assertEqual(input_revision.MAX_FILE_BYTES, 32 * 1024 * 1024)
        big = self.root / "big.bin"
        big.write_bytes(b"x" * 64)
        with patch.object(input_revision, "MAX_FILE_BYTES", 16):
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                code = input_revision.main(
                    ["hash", "--root", str(self.root), "big.bin"]
                )
        self.assertEqual(code, 2)
        self.assertEqual(
            json.loads(stdout.getvalue()),
            {"status": "error", "reason": "file_too_large"},
        )

    def test_symlink_inside_root_is_allowed(self) -> None:
        try:
            os.symlink(self.root / "spec.md", self.root / "alias.md")
        except OSError:
            self.skipTest("symlink creation is not available")
        result = _run("hash", "--root", str(self.root), "alias.md")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(_stdout_json(result)["revisions"]["alias.md"], ABC_SHA256)


if __name__ == "__main__":
    unittest.main()
