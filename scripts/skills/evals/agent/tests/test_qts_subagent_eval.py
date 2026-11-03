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

    def test_prepared_target_uses_attested_synthetic_head_not_upstream_object_id(
        self,
    ) -> None:
        source = self.repository / "target-source"
        source.mkdir()
        (source / "README.md").write_text("fixed sanitized source\n", encoding="utf-8")
        env = {
            **os.environ,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_AUTHOR_NAME": "Evaluator",
            "GIT_AUTHOR_EMAIL": "evaluator@invalid.local",
            "GIT_COMMITTER_NAME": "Evaluator",
            "GIT_COMMITTER_EMAIL": "evaluator@invalid.local",
        }
        subprocess.run(["git", "init", "--quiet", str(source)], check=True, env=env)
        subprocess.run(
            ["git", "-C", str(source), "add", "--all"], check=True, env=env
        )
        subprocess.run(
            ["git", "-C", str(source), "commit", "--quiet", "-m", "snapshot"],
            check=True,
            env=env,
        )
        target_head = subprocess.run(
            ["git", "-C", str(source), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        manifest_fingerprint = "sha256:" + "a" * 64
        provenance = self.repository / ".agent-eval-runs" / "source-provenance.json"
        provenance.write_text(
            json.dumps(
                {
                    "target_revision": qts.DEFAULT_TARGET_REVISION,
                    "source_integrity": "verified",
                    "source_manifest_fingerprint": manifest_fingerprint,
                    "rebuilt_snapshot_head": target_head,
                    "source_git_tree_sha": "b" * 40,
                }
            ),
            encoding="utf-8",
        )
        prepared_target_arguments: list[dict] = []

        def fake_create_skill_workspace(_repo, revision, destination):
            skills = set(qts._selected_skills(load_scenario()))
            files = []
            for skill in sorted(skills):
                path = destination / "skills" / skill / "SKILL.md"
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(f"# {skill}\n", encoding="utf-8")
                files.append(
                    {
                        "path": f"skills/{skill}/SKILL.md",
                        "size": path.stat().st_size,
                        "sha256": sha256_bytes(path.read_bytes()),
                    }
                )
            return {"revision": revision, "files": files}

        def fake_prepare_target(**kwargs):
            prepared_target_arguments.append(kwargs)
            kwargs["destination"].mkdir(parents=True)
            return {
                "source_revision": kwargs["source_revision_label"],
                "source_git_revision": kwargs["source_revision"],
                "source_manifest_fingerprint": manifest_fingerprint,
                "baseline_manifest": {},
                "baseline_manifest_fingerprint": "sha256:" + "c" * 64,
                "synthetic_baseline_revision": "d" * 40,
            }

        with patch.object(qts, "REPO_ROOT", self.repository):
            with (
                patch.object(qts, "resolve_commit", return_value="e" * 40),
                patch.object(qts, "_git_head", return_value="f" * 40),
                patch.object(qts, "_evaluator_source_fingerprints", return_value={}),
                patch.object(qts, "create_skill_workspace", side_effect=fake_create_skill_workspace),
                patch.object(qts, "prepare_sanitized_target", side_effect=fake_prepare_target),
                patch.object(qts, "verify_workspace_unchanged", return_value={"unchanged": True}),
            ):
                prepared = qts.prepare_run(
                    target_source_root=source,
                    source_provenance_path=provenance,
                    skill_revision="e" * 40,
                    output_root=self.repository / ".agent-eval-runs" / "prepared-run",
                    repeat=2,
                )

        self.assertEqual(prepared["target_source_checkout_head"], target_head)
        self.assertEqual(len(prepared_target_arguments), 2)
        for arguments in prepared_target_arguments:
            self.assertEqual(arguments["source_revision"], target_head)
            self.assertEqual(
                arguments["source_revision_label"], qts.DEFAULT_TARGET_REVISION
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
        self.assertEqual(evaluated["docker_production_verifier_replay"], "not_used")
        self.assertEqual(
            evaluated["production_verifier_independent_replay"]["overall_status"],
            "evidence_unverified",
        )
        self.assertEqual(
            evaluated["production_verifier_independent_replay"][
                "original_agent_execution_proof"
            ],
            "unverified",
        )
        self.assertFalse(
            evaluated["production_verifier_independent_replay"][
                "verifier_candidate_executed"
            ]
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

    def test_captured_copy_only_change_is_rejected_before_grading(self) -> None:
        qts.capture_attempt(run_root=self.run_root, attempt_id=self.attempt_id)
        captured = self.private_root / "captured-output" / "artifact-00.md"
        original = captured.read_bytes()
        changed = original.replace(b"QA artifact", b"QB artifact", 1)
        self.assertEqual(len(changed), len(original))
        captured.write_bytes(changed)

        with (
            patch.object(qts, "validate_public_artifact_index") as public_validator,
            patch.object(
                qts.qa_training_store, "validate_artifact_index"
            ) as fixed_validator,
        ):
            evaluated = qts.evaluate_attempt(
                run_root=self.run_root, attempt_id=self.attempt_id
            )

        issue_kinds = {row["kind"] for row in evaluated["issues"]}
        self.assertIn("captured_output_integrity_issue", issue_kinds)
        self.assertTrue(
            any(
                row.get("kind") == "captured_output_saved_hash_mismatch"
                for row in evaluated["captured_output_integrity"]["issues"]
            )
        )
        self.assertFalse(evaluated["captured_output_integrity"]["valid"])
        self.assertIsNone(evaluated["public_artifact_index"])
        self.assertIsNone(evaluated["fixed_artifact_index"])
        self.assertEqual(evaluated["overall_status"], "needs_review")
        public_validator.assert_not_called()
        fixed_validator.assert_not_called()

    def test_captured_copy_addition_and_deletion_are_rejected_before_grading(
        self,
    ) -> None:
        qts.capture_attempt(run_root=self.run_root, attempt_id=self.attempt_id)
        captured = self.private_root / "captured-output"
        (captured / "extra.md").write_text("unregistered\n", encoding="utf-8")
        (captured / "artifact-01.md").unlink()

        evaluated = qts.evaluate_attempt(
            run_root=self.run_root, attempt_id=self.attempt_id
        )

        kinds = {
            row["kind"] for row in evaluated["captured_output_integrity"]["issues"]
        }
        self.assertIn("captured_output_file_list_mismatch", kinds)
        self.assertIsNone(evaluated["fixed_artifact_index"])
        self.assertEqual(evaluated["overall_status"], "needs_review")

    def test_captured_copy_symlink_is_rejected_before_grading(self) -> None:
        qts.capture_attempt(run_root=self.run_root, attempt_id=self.attempt_id)
        captured = self.private_root / "captured-output"
        artifact = captured / "artifact-00.md"
        outside = self.repository / "outside.md"
        outside.write_text("outside\n", encoding="utf-8")
        artifact.unlink()
        artifact.symlink_to(outside)

        symlink_result = qts.evaluate_attempt(
            run_root=self.run_root, attempt_id=self.attempt_id
        )
        self.assertFalse(symlink_result["captured_output_integrity"]["valid"])
        self.assertIsNone(symlink_result["fixed_artifact_index"])

    def test_captured_copy_hardlink_is_rejected_before_grading(self) -> None:
        qts.capture_attempt(run_root=self.run_root, attempt_id=self.attempt_id)
        captured = self.private_root / "captured-output"
        artifact = captured / "artifact-00.md"
        outside = self.repository / "outside.md"
        outside.write_text("outside\n", encoding="utf-8")
        artifact.unlink()
        artifact.hardlink_to(outside)
        hardlink_result = qts.evaluate_attempt(
            run_root=self.run_root, attempt_id=self.attempt_id
        )
        self.assertFalse(hardlink_result["captured_output_integrity"]["valid"])
        self.assertIsNone(hardlink_result["fixed_artifact_index"])

    def test_capture_manifest_change_is_rejected_before_grading(self) -> None:
        qts.capture_attempt(run_root=self.run_root, attempt_id=self.attempt_id)
        capture_path = self.private_root / "capture.json"
        capture = json.loads(capture_path.read_text(encoding="utf-8"))
        capture["copy"]["total_source_bytes"] += 1
        capture_path.write_text(json.dumps(capture), encoding="utf-8")

        evaluated = qts.evaluate_attempt(
            run_root=self.run_root, attempt_id=self.attempt_id
        )

        self.assertIn(
            "capture_manifest_fingerprint_mismatch",
            {row["kind"] for row in evaluated["captured_output_integrity"]["issues"]},
        )
        self.assertIsNone(evaluated["public_artifact_index"])
        self.assertEqual(evaluated["overall_status"], "needs_review")

    def test_redacted_capture_is_never_graded(self) -> None:
        artifact = self.target_root / ".qa-eval-output" / "artifact-00.md"
        artifact.write_text("access_token=synthetic-marker\n", encoding="utf-8")
        capture = qts.capture_attempt(
            run_root=self.run_root, attempt_id=self.attempt_id
        )
        self.assertEqual(capture["status"], "captured_needs_review")

        with patch.object(
            qts.qa_training_store, "validate_artifact_index"
        ) as fixed_validator:
            evaluated = qts.evaluate_attempt(
                run_root=self.run_root, attempt_id=self.attempt_id
            )

        kinds = {
            row.get("issue_kind")
            for row in evaluated["issues"]
            if row.get("kind") == "captured_output_integrity_issue"
        }
        self.assertIn("redacted_capture_not_gradeable", kinds)
        self.assertIsNone(evaluated["fixed_artifact_index"])
        self.assertEqual(evaluated["overall_status"], "needs_review")
        fixed_validator.assert_not_called()

    def test_qts_replay_uses_pinned_script_hashes_without_agent_trace_claim(
        self,
    ) -> None:
        package_files = [
            {
                "path": f"skills/{skill}/scripts/runtime_contract.py",
                "size": 1,
                "sha256": sha256_bytes(b"x"),
            }
            for skill in sorted(qts._REQUIRED_RUNTIME_SKILLS)
        ]
        package_manifest = {
            "revision": "a" * 40,
            "skills": sorted(qts._REQUIRED_RUNTIME_SKILLS),
            "files": package_files,
            "package_fingerprint": qts.canonical_fingerprint(package_files),
        }
        attempt_record = qts._load_attempt_record(self.attempt_root)
        attempt_record["skill_package"] = package_manifest
        (self.private_root / "attempt.json").write_text(
            json.dumps(attempt_record), encoding="utf-8"
        )
        run = qts._load_run(self.run_root)
        run["attempts"][0]["skill_package_fingerprint"] = package_manifest[
            "package_fingerprint"
        ]
        qts._write_run(self.run_root, run)

        with (
            patch.object(
                qts,
                "evaluate_runtime_captures",
                return_value={"status": "evidence_unverified", "captures": []},
            ) as verify_replay,
            patch.object(
                qts,
                "evaluate_workflow_runtime_capture",
                return_value={"status": "evidence_unverified", "captures": []},
            ) as workflow_replay,
        ):
            qts.capture_attempt(run_root=self.run_root, attempt_id=self.attempt_id)
            evaluated = qts.evaluate_attempt(
                run_root=self.run_root, attempt_id=self.attempt_id
            )

        self.assertIsNone(verify_replay.call_args.kwargs["verifier_image"])
        self.assertFalse(verify_replay.call_args.kwargs["require_tool_trace"])
        self.assertIsNone(workflow_replay.call_args.kwargs["verifier_image"])
        self.assertFalse(workflow_replay.call_args.kwargs["require_tool_trace"])
        self.assertEqual(
            evaluated["production_verifier_independent_replay"][
                "original_agent_execution_proof"
            ],
            "unverified",
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
        relative_dir = (
            Path(".runtime-evidence") / "qa-workflow" / path_digest / invocation_id
        )
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
