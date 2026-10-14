from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

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

    def test_competing_processes_commit_at_most_one_expected_revision(self) -> None:
        script = (
            "import json, sys; "
            "sys.path.insert(0, sys.argv[1]); import artifact_graph; "
            "result = artifact_graph.commit_qa_workflow_baseline_local("
            "sys.argv[2], sys.argv[3], sys.argv[4], "
            "{'last_completed_qa_workflow_artifact': None, 'marker': sys.argv[5]}, "
            "'# ' + sys.argv[5] + '\\n'); print(json.dumps(result))"
        )

        def invoke(marker: str) -> dict:
            result = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    script,
                    str(SCRIPT_DIR),
                    str(self.root),
                    WORKFLOW_REF,
                    self.initial_revision,
                    marker,
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=20,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            return json.loads(result.stdout)

        markers = ("winner-a", "winner-b")
        processes = [
            subprocess.Popen(
                [
                    sys.executable,
                    "-c",
                    script,
                    str(SCRIPT_DIR),
                    str(self.root),
                    WORKFLOW_REF,
                    self.initial_revision,
                    marker,
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
            )
            for marker in markers
        ]
        first_results = []
        for process in processes:
            stdout, stderr = process.communicate(timeout=20)
            self.assertEqual(process.returncode, 0, stderr)
            first_results.append(json.loads(stdout))

        self.assertEqual(
            sum(result["status"] == "committed" for result in first_results),
            1,
            msg=json.dumps(first_results, ensure_ascii=False),
        )
        results = []
        for marker, result in zip(markers, first_results, strict=True):
            if result["status"] == "blocked":
                self.assertEqual(result.get("reason"), "workflow_state_lock_busy")
                result = invoke(marker)
            results.append(result)
        self.assertCountEqual(
            [result["status"] for result in results],
            ["committed", "conflict"],
            msg=json.dumps(results, ensure_ascii=False),
        )
        winner = next(result for result in results if result["status"] == "committed")
        state = artifact_graph.read_workflow_state(self.root, WORKFLOW_REF)
        self.assertEqual(state["status"], "current")
        binding = state["state"]["last_completed_qa_workflow_artifact"]
        self.assertEqual(binding["artifact_revision"], winner["artifact_revision"])
        historical = artifact_graph.read_qa_workflow_artifact_revision_local(
            self.root,
            WORKFLOW_REF,
            binding["artifact_ref"],
            binding["artifact_revision"],
        )
        self.assertEqual(historical["status"], "current")

    def test_historical_read_rejects_revision_digest_mismatch(self) -> None:
        result = self.commit()
        mismatch = artifact_graph.read_qa_workflow_artifact_revision_local(
            self.root,
            WORKFLOW_REF,
            result["artifact_ref"],
            "sha256:" + "0" * 64,
        )
        self.assertEqual(mismatch["status"], "blocked")

    def test_snapshot_publish_then_state_replace_failure_keeps_old_binding(
        self,
    ) -> None:
        first = self.commit()
        state_path = artifact_graph.canonical_state_path(self.root, WORKFLOW_REF)
        before = json.loads(state_path.read_text(encoding="utf-8"))
        old_binding = before["state"]["last_completed_qa_workflow_artifact"]
        candidate_markdown = "# Candidate after committed baseline\n"
        candidate_digest = hashlib.sha256(
            candidate_markdown.encode("utf-8")
        ).hexdigest()

        with patch(
            "artifact_graph.os.replace",
            side_effect=OSError("injected state replace failure"),
        ):
            failed = artifact_graph.commit_qa_workflow_baseline_local(
                self.root,
                WORKFLOW_REF,
                first["state_revision"],
                {
                    "last_completed_qa_workflow_artifact": None,
                    "marker": "new candidate",
                },
                candidate_markdown,
            )

        self.assertEqual(
            failed, {"status": "blocked", "reason": "workflow_state_replace_failed"}
        )
        candidate_snapshot = (
            self.root
            / "artifacts"
            / WORKFLOW_REF
            / "qa-workflow"
            / f"{candidate_digest}.md"
        )
        self.assertEqual(
            candidate_snapshot.read_text(encoding="utf-8"), candidate_markdown
        )
        after = artifact_graph.read_workflow_state(self.root, WORKFLOW_REF)
        self.assertEqual(after["status"], "current")
        self.assertEqual(
            after["state"]["last_completed_qa_workflow_artifact"], old_binding
        )

    def test_provider_native_baseline_fails_closed_without_history_or_cas(self) -> None:
        revision = "sha256:" + "a" * 64
        historical = artifact_graph.verify_historical_revision(
            revision_token=revision, provider_can_refetch=False
        )
        update = artifact_graph.state_update_decision(
            expected_revision=revision,
            current_revision=revision,
            native_atomic_conditional_write=False,
        )

        self.assertEqual(
            historical,
            {
                "status": "blocked",
                "reason": "historical_artifact_revision_unavailable",
            },
        )
        self.assertEqual(
            update,
            {"status": "blocked", "reason": "atomic_conditional_write_unavailable"},
        )

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
