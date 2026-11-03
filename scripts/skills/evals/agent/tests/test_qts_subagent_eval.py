from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.skills.evals.agent import qts_subagent_eval as qts
from scripts.skills.evals.agent.common import AgentEvalError, sha256_bytes
from scripts.skills.evals.agent.qa_training_store import load_scenario
from scripts.skills.evals.agent.target_workspace import _scan_workspace


class QTSSubagentEvalTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.repository = Path(self.temporary.name)
        self.run_root = self.repository / ".agent-eval-runs" / "qts-test"
        self.run_root.mkdir(parents=True)
        self.attempt_id = "a" * 32
        self.attempt_root = self.run_root / "attempts" / self.attempt_id
        self.private_root = self.attempt_root / "evaluator-private"
        self.target_root = self.attempt_root / "target"
        self.private_root.mkdir(parents=True)
        self.target_root.mkdir()
        (self.target_root / ".qa-eval-output").mkdir()
        tools = self.target_root / ".qa-eval-tools"
        tools.mkdir()
        self.scenario = load_scenario()
        contract = {
            "schema_version": 1,
            "required_artifacts": self.scenario["required_artifacts"],
            "optional_artifacts": [
                {
                    "skill": "question-analysis",
                    "kind": "question-analysis",
                    "scope": "checkout-payment-web",
                }
            ],
            "max_artifact_file_bytes": self.scenario["max_artifact_file_bytes"],
            "max_artifact_total_bytes": self.scenario["max_artifact_total_bytes"],
        }
        (tools / "artifact-index-contract.json").write_text(
            json.dumps(contract), encoding="utf-8"
        )
        baseline = _scan_workspace(self.target_root)
        self._init_git(self.target_root)
        head = subprocess.run(
            ["git", "-C", str(self.target_root), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        (self.private_root / "target-baseline.json").write_text(
            json.dumps(baseline), encoding="utf-8"
        )
        attempt_record = {
            "schema_version": 1,
            "attempt_id": self.attempt_id,
            "synthetic_baseline_revision": head,
            "prompt_fingerprint": sha256_bytes(b"fixed test prompt"),
            "requested_settings": {
                "model": "gpt-6-luna",
                "reasoning_effort": "max",
                "fork_turns": "none",
            },
        }
        (self.private_root / "attempt.json").write_text(
            json.dumps(attempt_record), encoding="utf-8"
        )
        self.run = {
            "schema_version": 1,
            "execution_method": "codex_subagent_handoff",
            "attempts": [
                {
                    "attempt_id": self.attempt_id,
                    "status": "prepared",
                }
            ],
        }
        (self.run_root / "result.json").write_text(
            json.dumps(self.run), encoding="utf-8"
        )
        self.stack = __import__("contextlib").ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.object(qts, "REPO_ROOT", self.repository))
        self._valid_output()
        qts.record_execution(
            run_root=self.run_root,
            attempt_id=self.attempt_id,
            execution_status="completed",
            started_at="2026-11-03T00:00:00Z",
            finished_at="2026-11-03T00:01:00Z",
            submitted_prompt_fingerprint=sha256_bytes(b"fixed test prompt"),
        )

    @staticmethod
    def _init_git(root: Path) -> None:
        env = {
            **os.environ,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_AUTHOR_NAME": "Evaluator",
            "GIT_AUTHOR_EMAIL": "evaluator@invalid.local",
            "GIT_COMMITTER_NAME": "Evaluator",
            "GIT_COMMITTER_EMAIL": "evaluator@invalid.local",
        }
        subprocess.run(
            ["git", "init", "--quiet", str(root)],
            check=True,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        subprocess.run(
            ["git", "-C", str(root), "add", "--all"],
            check=True,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        subprocess.run(
            ["git", "-C", str(root), "commit", "--quiet", "-m", "baseline"],
            check=True,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def _valid_output(self) -> None:
        output = self.target_root / ".qa-eval-output"
        artifacts = []
        routing = []
        for index, required in enumerate(self.scenario["required_artifacts"]):
            artifact_id = f"qts-artifact-{index:02d}"
            name = f"artifact-{index:02d}.md"
            (output / name).write_text(
                f"QA artifact for {required['skill']}\n", encoding="utf-8"
            )
            artifacts.append({**required, "artifact_id": artifact_id, "path": name})
            routing.append(
                {
                    "skill": required["skill"],
                    "scope": required["scope"],
                    "status": "executed",
                    "reason": "The required analysis artifact was generated.",
                    "artifact_ids": [artifact_id],
                }
            )
        (output / "artifact-index.json").write_text(
            json.dumps(
                {"schema_version": 1, "artifacts": artifacts, "routing": routing}
            ),
            encoding="utf-8",
        )

    def test_two_attempts_and_fixed_requested_settings_are_required(self) -> None:
        with self.assertRaisesRegex(AgentEvalError, "at least two"):
            qts.prepare_run(
                target_source_root=self.repository,
                skill_revision="a" * 40,
                output_root=self.repository / ".agent-eval-runs" / "not-run",
                repeat=1,
            )
        with self.assertRaisesRegex(AgentEvalError, "fixed requested values"):
            qts.prepare_run(
                target_source_root=self.repository,
                skill_revision="a" * 40,
                output_root=self.repository / ".agent-eval-runs" / "not-run",
                model="other-model",
            )

    def test_capture_and_evaluate_keep_runtime_and_semantic_unverified(self) -> None:
        run_index_path = self.run_root / "result.json"
        run_index = json.loads(run_index_path.read_text(encoding="utf-8"))
        self.assertEqual(run_index["attempts"][0]["status"], "execution_recorded")

        capture = qts.capture_attempt(
            run_root=self.run_root, attempt_id=self.attempt_id
        )
        run_index = json.loads(run_index_path.read_text(encoding="utf-8"))
        self.assertEqual(run_index["attempts"][0]["status"], capture["status"])
        self.assertEqual(
            run_index["attempts"][0]["capture_fingerprint"],
            qts.canonical_fingerprint(capture),
        )

        evaluated = qts.evaluate_attempt(
            run_root=self.run_root, attempt_id=self.attempt_id
        )
        run_index = json.loads(run_index_path.read_text(encoding="utf-8"))
        self.assertEqual(
            run_index["attempts"][0]["status"], evaluated["overall_status"]
        )
        self.assertEqual(
            run_index["attempts"][0]["evaluation_fingerprint"],
            qts.canonical_fingerprint(evaluated),
        )
        self.assertEqual(capture["status"], "captured")
        self.assertTrue(evaluated["public_artifact_index"]["valid"])
        self.assertEqual(evaluated["fixed_artifact_index"]["status"], "pass")
        self.assertEqual(evaluated["judge_status"], "not_run")
        self.assertEqual(
            evaluated["docker_production_verifier_replay"], "evidence_unverified"
        )
        self.assertEqual(evaluated["overall_status"], "needs_review")
        self.assertFalse(evaluated["workflow_completion"]["claim"] is True)

    def test_handoff_prompt_mismatch_is_preserved_as_needs_review(self) -> None:
        record = qts._load_attempt_record(self.attempt_root)
        record.pop("execution")
        (self.private_root / "attempt.json").write_text(
            json.dumps(record), encoding="utf-8"
        )
        run = qts._load_run(self.run_root)
        run["attempts"][0]["status"] = "prepared"
        run["attempts"][0].pop("execution", None)
        qts._write_run(self.run_root, run)
        execution = qts.record_execution(
            run_root=self.run_root,
            attempt_id=self.attempt_id,
            execution_status="completed",
            started_at="2026-11-03T00:00:00Z",
            finished_at="2026-11-03T00:01:00Z",
            submitted_prompt_fingerprint=sha256_bytes(b"different prompt"),
        )
        self.assertFalse(execution["prompt_matches_prepared"])
        capture = qts.capture_attempt(
            run_root=self.run_root, attempt_id=self.attempt_id
        )
        evaluated = qts.evaluate_attempt(
            run_root=self.run_root, attempt_id=self.attempt_id
        )
        self.assertEqual(capture["status"], "captured")
        self.assertIn(
            "handoff_prompt_not_verified",
            {row["kind"] for row in evaluated["issues"]},
        )
        self.assertEqual(evaluated["overall_status"], "needs_review")

    def test_output_change_after_capture_is_not_accepted(self) -> None:
        qts.capture_attempt(run_root=self.run_root, attempt_id=self.attempt_id)
        artifact = self.target_root / ".qa-eval-output" / "artifact-00.md"
        artifact.write_text("changed after capture\n", encoding="utf-8")
        evaluated = qts.evaluate_attempt(
            run_root=self.run_root, attempt_id=self.attempt_id
        )
        self.assertIn(
            "output_changed_after_capture",
            {row["kind"] for row in evaluated["issues"]},
        )
        self.assertEqual(evaluated["overall_status"], "needs_review")

    def test_symlink_and_hardlink_outputs_are_rejected(self) -> None:
        output = self.target_root / ".qa-eval-output"
        external = self.repository / "external.md"
        external.write_text("outside", encoding="utf-8")
        link = output / "linked.md"
        link.symlink_to(external)
        with self.assertRaisesRegex(AgentEvalError, "symlink"):
            qts._scan_output_tree(output, self.scenario)
        link.unlink()
        hardlink = output / "hardlinked.md"
        hardlink.hardlink_to(external)
        with self.assertRaisesRegex(AgentEvalError, "unsafe file"):
            qts._scan_output_tree(output, self.scenario)
        alias = self.repository / "target-alias"
        alias.symlink_to(self.target_root, target_is_directory=True)
        with self.assertRaisesRegex(AgentEvalError, "symlink"):
            qts._scan_output_tree(alias / ".qa-eval-output", self.scenario)

    def test_duplicate_json_key_is_rejected_by_public_validator(self) -> None:
        output = self.target_root / ".qa-eval-output"
        index = output / "artifact-index.json"
        index.write_text(
            index.read_text(encoding="utf-8").replace("{", '{"schema_version":1,', 1),
            encoding="utf-8",
        )
        capture = qts.capture_attempt(
            run_root=self.run_root, attempt_id=self.attempt_id
        )
        evaluated = qts.evaluate_attempt(
            run_root=self.run_root, attempt_id=self.attempt_id
        )
        self.assertEqual(capture["status"], "captured")
        self.assertFalse(evaluated["public_artifact_index"]["valid"])
        self.assertEqual(evaluated["overall_status"], "needs_review")

    def test_skill_package_selection_excludes_other_skills_and_evaluator_data(
        self,
    ) -> None:
        selected = qts._selected_skills(self.scenario)
        self.assertEqual(len(selected), len(self.scenario["required_artifacts"]) + 1)
        self.assertIn("question-analysis", selected)
        self.assertNotIn("spec-compliance-analysis", selected)

    def test_runtime_capture_binds_path_digest_and_keeps_incomplete_claim(self) -> None:
        output = self.target_root / ".qa-eval-output"
        artifact_path = "artifact-07.md"
        path_digest = sha256_bytes(artifact_path.encode("utf-8")).removeprefix(
            "sha256:"
        )
        invocation_id = "invocation-1"
        relative_dir = Path(".runtime-evidence") / "qa-workflow" / path_digest / invocation_id
        record = output / relative_dir
        record.mkdir(parents=True)
        request_bytes = b'{"operation":"workflow-runtime"}\n'
        result_bytes = b'{"payload":{"can_complete":false}}\n'
        (record / "request.json").write_bytes(request_bytes)
        (record / "result.json").write_bytes(result_bytes)
        invocation = {
            "schema_version": 1,
            "skill": "qa-workflow",
            "operation": "workflow-runtime",
            "artifact_id": path_digest,
            "invocation_id": invocation_id,
            "request_relative_path": f"{relative_dir.as_posix()}/request.json",
            "record_relative_path": relative_dir.as_posix(),
            "result_relative_path": f"{relative_dir.as_posix()}/result.json",
            "request_sha256": sha256_bytes(request_bytes),
            "result_sha256": sha256_bytes(result_bytes),
            "evidence_status": "captured",
        }
        (record / "invocation.json").write_text(
            json.dumps(invocation), encoding="utf-8"
        )
        artifacts = [
            {
                "skill": "qa-workflow",
                "artifact_id": "qts-artifact-07",
                "path": artifact_path,
                "sha256": sha256_bytes(b"different content hash"),
            }
        ]
        checked = qts._validate_runtime_bindings(output, artifacts)
        self.assertEqual(len(checked["invocations"]), 1)
        self.assertEqual(
            checked["invocations"][0]["capture_record_integrity"], "consistent"
        )
        self.assertFalse(checked["invocations"][0]["workflow_can_complete_claim"])
        self.assertEqual(checked["independent_replay"], "evidence_unverified")


if __name__ == "__main__":
    unittest.main()
