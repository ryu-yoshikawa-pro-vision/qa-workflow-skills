from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tests.skills.runtime.test_qa_operation_claim import WORKFLOW_REF, artifact_graph


class SharedResourceProviderSelectionTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name) / "reservations"

    def test_missing_provider_does_not_create_sqlite_or_legacy_file(self) -> None:
        for native in (False, True):
            result = artifact_graph.reserve_shared_resource(
                self.root,
                "shared-user",
                WORKFLOW_REF,
                native_atomic_conditional_release=native,
            )
            self.assertEqual(result["status"], "blocked")
            self.assertEqual(
                result["reason"],
                "reservation_provider_not_selected"
                if native
                else "atomic_conditional_release_unavailable",
            )
        self.assertFalse(self.root.exists())

    def test_existing_legacy_claim_remains_untouched(self) -> None:
        self.root.mkdir(parents=True)
        old = self.root / (
            artifact_graph.content_identity({"resource_ref": "shared-user"}) + ".json"
        )
        old.write_text('{"status":"reserved"}', encoding="utf-8")
        result = artifact_graph.reserve_shared_resource(
            self.root,
            "shared-user",
            WORKFLOW_REF,
            native_atomic_conditional_release=True,
        )
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(old.read_text(encoding="utf-8"), '{"status":"reserved"}')
        self.assertFalse((self.root / "resource-reservations.sqlite3").exists())

    def test_isolated_resource_does_not_require_reservation(self) -> None:
        result = artifact_graph.reserve_shared_resource(
            self.root,
            "isolated",
            WORKFLOW_REF,
            isolated=True,
            native_atomic_conditional_release=False,
        )
        self.assertEqual(result["status"], "not_required")
        self.assertFalse(self.root.exists())

    def test_external_handoff_requires_claim_and_revision(self) -> None:
        result = artifact_graph.reserve_shared_resource(
            self.root,
            "shared-user",
            WORKFLOW_REF,
            native_atomic_conditional_release=False,
            external_reservation="provider:claim",
        )
        self.assertEqual(result["reason"], "external_reservation_not_confirmed")
        result = artifact_graph.reserve_shared_resource(
            self.root,
            "shared-user",
            WORKFLOW_REF,
            native_atomic_conditional_release=False,
            external_reservation="provider:claim",
            external_reservation_acquired=True,
        )
        self.assertEqual(result["reason"], "external_reservation_revision_missing")
        handoff = artifact_graph.reserve_shared_resource(
            self.root,
            "shared-user",
            WORKFLOW_REF,
            native_atomic_conditional_release=False,
            external_reservation="provider:claim",
            external_reservation_acquired=True,
            external_reservation_revision="provider:r1",
        )
        self.assertEqual(handoff["status"], "blocked")
        self.assertEqual(handoff["reason"], "external_reservation_readback_required")
        self.assertEqual(handoff["provider"], "unverified_external_reservation")
        self.assertEqual(handoff["reservation_revision"], "provider:r1")
        self.assertFalse(self.root.exists())

    def test_owner_assertion_does_not_release_shared_resource(self) -> None:
        state = dict(
            current_workflow_ref=WORKFLOW_REF,
            expected_workflow_ref=WORKFLOW_REF,
            expected_reservation_revision="provider:r1",
            current_reservation_revision="provider:r1",
            native_atomic_conditional_release=True,
            owner_state_verified=True,
            owner_execution_state="complete",
            cleanup_confirmed=True,
        )
        result = artifact_graph.release_shared_resource(**state)
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["reason"], "reservation_release_provider_not_connected")
        self.assertEqual(
            artifact_graph.release_shared_resource(
                **{**state, "current_workflow_ref": "other"}
            )["reason"],
            "reservation_owner_mismatch",
        )
        self.assertEqual(
            artifact_graph.release_shared_resource(
                **{**state, "cleanup_confirmed": False}
            )["reason"],
            "owner_execution_or_cleanup_unverified",
        )


if __name__ == "__main__":
    unittest.main()
