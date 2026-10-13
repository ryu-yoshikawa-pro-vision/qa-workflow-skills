from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[3] / "skills" / "qa-workflow" / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))
import artifact_graph  # noqa: E402

WORKFLOW_REF = "00000000-0000-4000-8000-000000000016"


class QaWorkflowBaselineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        initial = artifact_graph.create_workflow_state(
            self.root,
            WORKFLOW_REF,
            {"last_completed_qa_workflow_artifact": None, "marker": "before"},
        )
        self.assertEqual(initial["status"], "created")
        self.initial_revision = initial["state_revision"]

    def commit(self, markdown: str = "# QA workflow\n") -> dict:
        return artifact_graph.commit_qa_workflow_baseline_local(
            self.root,
            WORKFLOW_REF,
            self.initial_revision,
            {"last_completed_qa_workflow_artifact": None, "marker": "after"},
            markdown,
        )

    def test_commit_snapshot_binding_and_exact_historical_read(self) -> None:
        result = self.commit()
        self.assertEqual(result["status"], "committed")
        self.assertEqual(result["artifact_ref"], f"qa-workflow-local:{WORKFLOW_REF}")
        digest = hashlib.sha256(b"# QA workflow\n").hexdigest()
        self.assertEqual(result["artifact_revision"], f"sha256:{digest}")

        state_path = artifact_graph.canonical_state_path(self.root, WORKFLOW_REF)
        document = json.loads(state_path.read_text(encoding="utf-8"))
        self.assertEqual(
            document["state"]["last_completed_qa_workflow_artifact"],
            {
                "artifact_ref": f"qa-workflow-local:{WORKFLOW_REF}",
                "artifact_revision": f"sha256:{digest}",
                "artifact_sha256": digest,
            },
        )
        historical = artifact_graph.read_qa_workflow_artifact_revision_local(
            self.root,
            WORKFLOW_REF,
            result["artifact_ref"],
            result["artifact_revision"],
        )
        self.assertEqual(historical["status"], "current")
        self.assertEqual(historical["artifact_markdown"], "# QA workflow\n")

    def test_retry_after_committed_update_is_idempotent(self) -> None:
        first = self.commit()
        replay = self.commit()
        self.assertEqual(first["status"], "committed")
        self.assertEqual(replay["status"], "committed_replay")
        self.assertEqual(first["state_revision"], replay["state_revision"])

    def test_changed_state_revision_conflicts_and_does_not_replace_binding(
        self,
    ) -> None:
        first = self.commit()
        self.assertEqual(first["status"], "committed")
        current = artifact_graph.canonical_state_path(self.root, WORKFLOW_REF)
        document = json.loads(current.read_text(encoding="utf-8"))
        document["state"]["marker"] = "raced update"
        current.write_text(
            json.dumps(
                document, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            ),
            encoding="utf-8",
            newline="",
        )
        conflict = self.commit("# A later candidate\n")
        self.assertEqual(conflict["status"], "conflict")
        stored = json.loads(current.read_text(encoding="utf-8"))
        self.assertEqual(stored["state"]["marker"], "raced update")
        self.assertEqual(
            stored["state"]["last_completed_qa_workflow_artifact"],
            document["state"]["last_completed_qa_workflow_artifact"],
        )

    def test_historical_read_rejects_revision_digest_mismatch(self) -> None:
        result = self.commit()
        mismatch = artifact_graph.read_qa_workflow_artifact_revision_local(
            self.root,
            WORKFLOW_REF,
            result["artifact_ref"],
            "sha256:" + "0" * 64,
        )
        self.assertEqual(mismatch["status"], "blocked")

    def test_commit_rejects_symlink_root_and_symlink_ancestor(self) -> None:
        root_link = self.root / "root-link"
        parent = self.root / "linked-parent"
        nested_root = parent / "workflow-state"
        try:
            root_link.symlink_to(self.root, target_is_directory=True)
            parent.symlink_to(self.root, target_is_directory=True)
        except OSError as exc:
            self.skipTest(f"directory symlink is unavailable: {exc}")

        for candidate in (root_link, nested_root):
            with self.subTest(root=candidate):
                result = artifact_graph.commit_qa_workflow_baseline_local(
                    candidate,
                    WORKFLOW_REF,
                    self.initial_revision,
                    {"last_completed_qa_workflow_artifact": None},
                    "# Candidate\n",
                )
                self.assertEqual(result["status"], "blocked")

    def test_commit_rejects_symlink_lock_and_state_paths(self) -> None:
        state_path = artifact_graph.canonical_state_path(self.root, WORKFLOW_REF)
        lock_path = self.root / f".{WORKFLOW_REF}.workflow-state.lock"
        try:
            lock_path.symlink_to(state_path)
        except OSError as exc:
            self.skipTest(f"file symlink is unavailable: {exc}")
        lock_result = self.commit()
        self.assertEqual(lock_result["status"], "blocked")
        lock_path.unlink()

        target = self.root / "state-target.json"
        target.write_bytes(state_path.read_bytes())
        state_path.unlink()
        try:
            state_path.symlink_to(target)
        except OSError as exc:
            self.skipTest(f"file symlink is unavailable: {exc}")
        state_result = self.commit()
        self.assertEqual(state_result["status"], "blocked")


if __name__ == "__main__":
    unittest.main()
