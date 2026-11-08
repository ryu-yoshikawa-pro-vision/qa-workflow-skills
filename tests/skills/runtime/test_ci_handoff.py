from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

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
            "artifacts": [dict(artifact)],
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
            "artifacts": [dict(artifact, path="artifact.md")],
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

    def test_duplicate_changes_are_rejected(self) -> None:
        self.manifest["changes"].append(dict(self.manifest["changes"][0]))
        with self.assertRaises(ValueError):
            self.result()

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
