from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "skills" / "qa-workflow" / "scripts" / "ci_handoff.py"
SPEC = importlib.util.spec_from_file_location("qa_ci_handoff", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
handoff = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(handoff)

BASE = "1" * 40
HEAD = "2" * 40
SOURCE = {
    "repository": "owner/product",
    "base_sha": BASE,
    "head_sha": HEAD,
    "build_ref": "build-12",
}


class CiHandoffTests(unittest.TestCase):
    def setUp(self) -> None:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.content = b"artifact-current\n"
        (self.root / "artifact.md").write_bytes(self.content)
        digest = "sha256:" + hashlib.sha256(self.content).hexdigest()
        artifact = {
            "owner": "feature-analysis",
            "scope": "SCOPE-001",
            "artifact_ref": "feature-1",
            "revision": "rev-5",
            "sha256": digest,
            "source_refs": [{"ref": "repo-source", "revision": HEAD}],
        }
        self.expected = {
            "schema_version": handoff.SCHEMA,
            "source": dict(SOURCE),
            "source_inventory": [{"ref": "repo-source", "revision": HEAD}],
            "changed_paths": ["src/a.ts", "docs/spec.md"],
            "allowed_classifications": ["implementation", "specification"],
            "artifacts": [copy.deepcopy(artifact)],
            "required_approvals": [],
        }
        self.manifest = {
            "schema_version": handoff.SCHEMA,
            "source": dict(SOURCE),
            "source_inventory": {
                "complete": True,
                "entries": [{"ref": "repo-source", "revision": HEAD}],
            },
            "changes": [
                {"path": "src/a.ts", "classification": "implementation"},
                {"path": "docs/spec.md", "classification": "specification"},
            ],
            "artifacts": [dict(copy.deepcopy(artifact), path="artifact.md")],
        }

    def result(self) -> dict:
        return handoff.verify(self.expected, self.manifest, self.root)

    def assert_rejects(self, code: str) -> None:
        result = self.result()
        self.assertNotEqual(result["status"], "pass", result)
        self.assertIn(code, [item["code"] for item in result["issues"]], result)

    def test_complete_integrity_transport_passes(self) -> None:
        result = self.result()
        self.assertEqual(result["status"], "pass", result)
        self.assertEqual(len(result["verified_artifacts"]), 1)

    def test_old_head_is_rejected(self) -> None:
        self.manifest["source"]["head_sha"] = BASE
        self.assert_rejects("source_revision_mismatch")

    def test_missing_change_is_rejected(self) -> None:
        self.manifest["changes"].pop()
        self.assert_rejects("unclassified_change")

    def test_unclassified_change_is_rejected(self) -> None:
        self.manifest["changes"][0]["classification"] = "unknown"
        self.assert_rejects("unclassified_change")

    def test_missing_inventory_is_rejected(self) -> None:
        self.manifest["source_inventory"]["complete"] = False
        self.assert_rejects("source_inventory_incomplete")

    def test_stale_artifact_is_rejected(self) -> None:
        self.manifest["artifacts"][0]["source_refs"][0]["revision"] = BASE
        self.assert_rejects("artifact_revision_mismatch")

    def test_both_expected_and_manifest_artifact_sources_stale(self) -> None:
        self.expected["artifacts"][0]["source_refs"][0]["revision"] = BASE
        self.manifest["artifacts"][0]["source_refs"][0]["revision"] = BASE
        self.assert_rejects("stale_artifact_source")

    def test_artifact_hash_mismatch_is_rejected(self) -> None:
        (self.root / "artifact.md").write_bytes(b"tampered\n")
        self.assert_rejects("artifact_hash_mismatch")

    def test_required_artifact_missing_is_rejected(self) -> None:
        self.manifest["artifacts"] = []
        self.assert_rejects("missing_artifact")

    def test_unknown_approval_provider_is_blocked(self) -> None:
        self.expected["required_approvals"] = ["plan-approval:rev-5"]
        result = self.result()
        self.assertEqual(result["status"], "blocked")
        self.assert_rejects("approval_provider_unconfigured")

    def test_path_traversal_is_rejected(self) -> None:
        self.manifest["artifacts"][0]["path"] = "../artifact.md"
        with self.assertRaises(ValueError):
            self.result()

    def test_symlink_readback_is_rejected(self) -> None:
        target = self.root / "artifact.md"
        alias = self.root / "alias.md"
        try:
            alias.symlink_to(target)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks are unavailable")
        self.manifest["artifacts"][0]["path"] = "alias.md"
        self.assert_rejects("artifact_readback_failed")

    def test_backslash_in_posix_changed_filename_is_a_valid_comparison_key(
        self,
    ) -> None:
        path = r"src/back\slash.ts"
        self.expected["changed_paths"] = [path]
        self.manifest["changes"] = [{"path": path, "classification": "implementation"}]
        self.assertEqual(self.result()["status"], "pass")

    def test_fifo_is_never_opened_in_blocking_mode(self) -> None:
        if os.name != "posix" or not hasattr(os, "mkfifo"):
            self.skipTest("FIFO is POSIX-specific")
        target = self.root / "artifact.md"
        target.unlink()
        os.mkfifo(target)
        self.assert_rejects("artifact_readback_failed")

    def test_no_unsafe_readback_fallback_when_secure_open_is_unavailable(self) -> None:
        with patch.object(handoff, "os", SimpleNamespace(name="nt")):
            self.assert_rejects("artifact_readback_failed")

    def test_duplicate_changes_are_rejected(self) -> None:
        self.manifest["changes"].append(dict(self.manifest["changes"][0]))
        with self.assertRaises(ValueError):
            self.result()

    def test_required_artifact_must_identify_current_source(self) -> None:
        self.expected["artifacts"][0]["source_refs"] = []
        with self.assertRaises(ValueError):
            self.result()
        self.expected["artifacts"][0]["source_refs"] = [
            {"ref": "repo-source", "revision": HEAD}
        ]
        self.manifest["artifacts"][0]["source_refs"] = []
        with self.assertRaises(ValueError):
            self.result()

    def test_corrupt_artifact_does_not_hide_behind_missing_approval(self) -> None:
        self.expected["required_approvals"] = ["plan-approval:rev-5"]
        self.manifest["source"]["head_sha"] = BASE
        result = self.result()
        self.assertEqual(result["status"], "fail", result)
        self.assertIn(
            "approval_provider_unconfigured",
            {row["code"] for row in result["issues"]},
        )
        self.assertIn(
            "source_revision_mismatch", {row["code"] for row in result["issues"]}
        )

    def test_noncanonical_artifact_path_is_rejected(self) -> None:
        self.manifest["artifacts"][0]["path"] = "subdir//artifact.md"
        with self.assertRaises(ValueError):
            self.result()

    def test_nested_symlink_directory_is_rejected(self) -> None:
        external = self.root / "external"
        external.mkdir()
        (external / "artifact.md").write_bytes(self.content)
        link = self.root / "alias"
        try:
            link.symlink_to(external, target_is_directory=True)
        except (NotImplementedError, OSError):
            self.skipTest("symlink unsupported")
        self.manifest["artifacts"][0]["path"] = "alias/artifact.md"
        self.assert_rejects("artifact_readback_failed")

    def test_artifact_read_enforces_limit(self) -> None:
        with patch.object(handoff, "MAX_ARTIFACT_BYTES", 4):
            self.assert_rejects("artifact_readback_failed")

    def test_json_input_is_bounded_and_duplicate_keys_rejected(self) -> None:
        candidate = self.root / "duplicate.json"
        candidate.write_text('{"a":1,"a":2}', encoding="utf-8")
        with self.assertRaises(ValueError):
            handoff._read_json(candidate)
        with patch.object(handoff, "MAX_JSON_BYTES", 5):
            with self.assertRaises(ValueError):
                handoff._read_json(candidate)

    def test_json_nesting_failure_is_a_structured_input_error(self) -> None:
        input_path = self.root / "deep.json"
        input_path.write_bytes(b"[" * 1100 + b"0" + b"]" * 1100)
        with self.assertRaisesRegex(ValueError, "nesting"):
            handoff._read_json(input_path)

    def test_cli_output_escapes_invalid_unicode_in_failure_report(self) -> None:
        expected = self.root / "expected.json"
        manifest = self.root / "manifest.json"
        self.manifest["changes"][0]["path"] = "src/\ud800.py"
        expected.write_text(json.dumps(self.expected), encoding="utf-8")
        manifest.write_text(json.dumps(self.manifest), encoding="utf-8")
        response = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--expected",
                str(expected),
                "--manifest",
                str(manifest),
                "--artifacts-root",
                str(self.root),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(response.returncode, 1, response.stderr)
        self.assertEqual(json.loads(response.stdout)["status"], "fail")
        self.assertIn("\\ud800", response.stdout)

    def test_cli_output_and_fail_closed_exit_code(self) -> None:
        expected = self.root / "expected.json"
        manifest = self.root / "manifest.json"
        expected.write_text(json.dumps(self.expected), encoding="utf-8")
        manifest.write_text(json.dumps(self.manifest), encoding="utf-8")
        command = [
            sys.executable,
            str(SCRIPT),
            "--expected",
            str(expected),
            "--manifest",
            str(manifest),
            "--artifacts-root",
            str(self.root),
        ]
        response = subprocess.run(command, capture_output=True, text=True, check=False)
        self.assertEqual(response.returncode, 0, response.stderr)
        self.manifest["source"]["head_sha"] = BASE
        manifest.write_text(json.dumps(self.manifest), encoding="utf-8")
        response = subprocess.run(command, capture_output=True, text=True, check=False)
        self.assertEqual(response.returncode, 1)
        self.assertEqual(json.loads(response.stdout)["status"], "fail")


if __name__ == "__main__":
    unittest.main()
