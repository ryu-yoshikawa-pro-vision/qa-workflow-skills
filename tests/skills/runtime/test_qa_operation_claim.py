from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

SCRIPT_DIR = Path(__file__).resolve().parents[3] / "skills" / "qa-workflow" / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))
import artifact_graph  # noqa: E402

WORKFLOW_REF = "00000000-0000-4000-8000-000000000023"


def operation_details() -> dict:
    return {
        "owner_skill": "test-execution",
        "scope_ref": "SCOPE-001",
        "operation_type": "runner_attempt",
        "target_ref": "RUN-001",
        "source_revisions": [{"ref": "git:product", "revision": "commit-001"}],
        "artifact_revisions": [{"ref": "TC-001", "revision": "v3"}],
        "expected_revision": None,
        "approval_ref": "plan-approval:rev-5",
        "permission_scope": "test-runner:execute",
        "resume_owner": "test-execution",
    }


class WorkflowOperationClaimTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name) / "workflow-state"

    def claim(self, details: dict | None = None) -> dict:
        return artifact_graph.claim_mutable_operation(
            self.root,
            WORKFLOW_REF,
            "runner:attempt-001",
            operation_details=details if details is not None else operation_details(),
        )

    def test_claim_persists_scope_revision_and_resume_details(self) -> None:
        first = self.claim()
        self.assertEqual(first["status"], "claim_acquired", first)
        self.assertTrue(first["may_start"])
        stored = Path(first["path"]).read_bytes()
        record = json.loads(stored)
        self.assertEqual(record["workflow_ref"], WORKFLOW_REF)
        self.assertEqual(record["operation_ref"], "runner:attempt-001")
        self.assertEqual(record["operation_details"], operation_details())
        self.assertEqual(
            first["claim_revision"], "sha256:" + hashlib.sha256(stored).hexdigest()
        )
        second = self.claim()
        self.assertEqual(second["status"], "blocked")
        self.assertFalse(second["may_start"])
        self.assertEqual(Path(first["path"]).read_bytes(), stored)

    def test_separate_attempt_cannot_reuse_claim_identity(self) -> None:
        first = self.claim()
        self.assertEqual(first["status"], "claim_acquired")
        changed = operation_details()
        changed["target_ref"] = "RUN-002"
        second = self.claim(changed)
        self.assertEqual(second["status"], "blocked")
        self.assertFalse(second["may_start"])

    def test_concurrent_callers_get_exactly_one_start_permission(self) -> None:
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda _: self.claim(), range(8)))
        self.assertEqual(
            sum(result["status"] == "claim_acquired" for result in results), 1
        )
        self.assertEqual(sum(result["may_start"] for result in results), 1)

    def test_missing_source_revision_blocks_before_creating_claim(self) -> None:
        details = operation_details()
        details["source_revisions"] = []
        result = self.claim(details)
        self.assertEqual(result["status"], "blocked")
        self.assertFalse(result["may_start"])
        self.assertFalse((self.root / "claims").exists())

    def test_duplicate_or_malformed_source_revision_is_rejected(self) -> None:
        details = operation_details()
        details["source_revisions"].append(dict(details["source_revisions"][0]))
        self.assertEqual(self.claim(details)["status"], "blocked")
        details = operation_details()
        details["expected_revision"] = "first\nsecond"
        self.assertEqual(self.claim(details)["status"], "blocked")
        self.assertFalse((self.root / "claims").exists())

    def test_unknown_fields_and_credential_shaped_metadata_not_accepted(
        self,
    ) -> None:
        details = operation_details()
        details["access_token"] = "DO_NOT_PERSIST"
        result = self.claim(details)
        self.assertEqual(result["status"], "blocked")
        self.assertFalse((self.root / "claims").exists())

    def test_unreadable_claim_does_not_authorize_start(self) -> None:
        with patch.object(
            artifact_graph,
            "create_if_absent",
            return_value={"status": "created", "atomic": True, "path": "missing"},
        ):
            result = self.claim()
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["reason"], "claim_readback_failed")
        self.assertFalse(result["may_start"])

    def test_symlink_claim_directory_blocks_before_side_effect(self) -> None:
        self.root.mkdir(parents=True)
        other = self.root.parent / "outside"
        other.mkdir()
        try:
            (self.root / "claims").symlink_to(other, target_is_directory=True)
        except (NotImplementedError, OSError):
            self.skipTest("symlink unsupported")
        result = self.claim()
        self.assertEqual(result["status"], "blocked")
        self.assertFalse(result["may_start"])
        self.assertEqual(list(other.iterdir()), [])

    def test_legacy_claim_remains_readable_and_never_restarts(self) -> None:
        first = artifact_graph.claim_mutable_operation(
            self.root, WORKFLOW_REF, "legacy:operation"
        )
        second = artifact_graph.claim_mutable_operation(
            self.root, WORKFLOW_REF, "legacy:operation"
        )
        self.assertEqual(first["status"], "claim_acquired")
        self.assertEqual(second["status"], "blocked")
        self.assertFalse(second["may_start"])


if __name__ == "__main__":
    unittest.main()
