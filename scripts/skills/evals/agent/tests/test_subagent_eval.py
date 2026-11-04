from __future__ import annotations

import json
import multiprocessing
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.skills.evals.agent import improve, subagent_eval
from scripts.skills.evals.agent.common import (
    AgentEvalError,
    canonical_fingerprint,
    sha256_bytes,
)

SKILL = "test-requirement-design"
EVAL_ID = "TR-OUT-001"
SKILL_SHA = "a" * 40
EVALUATOR_SHA = "b" * 40


def _seal_attempt_process(repository: str, run_root: str, attempt_id: str, start, results):
    from scripts.skills.evals.agent import subagent_eval

    subagent_eval.REPO_ROOT = Path(repository)
    start.wait(10)
    try:
        subagent_eval.seal_handoff(
            run_root=Path(run_root),
            attempt_id=attempt_id,
            execution_status="completed",
            artifact_attempt_id=attempt_id,
            started_at="2026-11-05T10:00:00Z",
            finished_at="2026-11-05T10:00:01Z",
        )
        results.put((attempt_id, "sealed"))
    except Exception as exc:  # Test transport: retain only the error class/message.
        results.put((attempt_id, f"error:{type(exc).__name__}:{exc}"))


def _capture_or_seal_process(
    repository: str, run_root: str, attempt_id: str, operation: str, start, results
):
    from scripts.skills.evals.agent import subagent_eval

    subagent_eval.REPO_ROOT = Path(repository)
    start.wait(10)
    try:
        if operation == "capture":
            subagent_eval.capture_agent_visible_output(
                run_root=Path(run_root), attempt_id=attempt_id
            )
        else:
            subagent_eval.seal_handoff(
                run_root=Path(run_root),
                attempt_id=attempt_id,
                execution_status="completed",
                artifact_attempt_id=attempt_id,
                started_at="2026-11-05T10:00:00Z",
                finished_at="2026-11-05T10:00:01Z",
            )
        results.put((operation, "ok"))
    except Exception as exc:
        results.put((operation, f"error:{type(exc).__name__}:{exc}"))


def _grade_attempt_process(repository: str, run_root: str, attempt_id: str, start, results):
    from scripts.skills.evals.agent import subagent_eval

    root = Path(run_root)
    subagent_eval.REPO_ROOT = Path(repository)
    record = json.loads((root / "result.json").read_text(encoding="utf-8"))
    evaluator_revision = record["evaluator"]["revision"]
    input_text = "Create test requirements from the supplied QA specification."
    subagent_eval.assert_clean_checkout = lambda _root: evaluator_revision
    subagent_eval._case_for = lambda *_args: {"input": input_text}
    subagent_eval._dataset_fingerprint = lambda _case: record["dataset_fingerprint"]
    subagent_eval.grade_deterministic = lambda *_args, **_kwargs: {
        "skill": SKILL,
        "eval_id": EVAL_ID,
        "status": "pass",
        "assertions": [],
    }
    start.wait(10)
    try:
        subagent_eval.grade_attempt(run_root=root, attempt_id=attempt_id)
        results.put((attempt_id, "graded"))
    except Exception as exc:
        results.put((attempt_id, f"error:{type(exc).__name__}:{exc}"))


class SubagentEvalTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.repository = Path(self.temporary.name)
        self.case = {
            "skill": SKILL,
            "id": EVAL_ID,
            "input": "Create test requirements from the supplied QA specification.",
            "fingerprint_files": [
                (
                    "input.md",
                    b"Create test requirements from the supplied QA specification.",
                ),
                ("expected.json", b'{"private":"expected fixture"}'),
                ("evals.json", b'{"cases":["TR-OUT-001"]}'),
            ],
            "case": {
                "criteria": ["SEM-001"],
                "input_text": "Create test requirements from the supplied QA specification.",
                "reference_text": "Private reference text.",
            },
            "dataset": {
                "criteria_by_id": {
                    "SEM-001": {
                        "id": "SEM-001",
                        "title": "Traceability",
                        "description": "Preserve source traceability.",
                        "critical": True,
                    }
                }
            },
        }
        self.stack = __import__("contextlib").ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(
            patch.object(subagent_eval, "REPO_ROOT", self.repository)
        )
        self.stack.enter_context(
            patch.object(subagent_eval.legacy_run, "REPO_ROOT", self.repository)
        )
        self.stack.enter_context(
            patch.object(
                subagent_eval, "assert_clean_checkout", return_value=EVALUATOR_SHA
            )
        )
        self.stack.enter_context(
            patch.object(subagent_eval, "resolve_commit", return_value=SKILL_SHA)
        )
        self.stack.enter_context(
            patch.object(subagent_eval, "_case_for", return_value=self.case)
        )
        self.stack.enter_context(
            patch.object(
                subagent_eval,
                "create_skill_workspace",
                side_effect=self._create_package,
            )
        )
        self.stack.enter_context(
            patch.object(
                subagent_eval,
                "grade_deterministic",
                return_value={
                    "skill": SKILL,
                    "eval_id": EVAL_ID,
                    "status": "pass",
                    "assertions": [],
                },
            )
        )

    @staticmethod
    def _create_package(_repo: Path, revision: str, destination: Path) -> dict:
        files = []
        for relative, content in (
            (
                f"skills/{SKILL}/SKILL.md",
                b"# Test Requirement Design\nUse the Skill contract.\n",
            ),
            (
                f"skills/{SKILL}/scripts/runtime_contract.py",
                b"RUNTIME_IMPLEMENTATION = 'test'\n",
            ),
        ):
            path = destination / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
            files.append(
                {
                    "path": relative,
                    "size": len(content),
                    "sha256": sha256_bytes(content),
                }
            )
        return {
            "revision": revision,
            "skills": [SKILL],
            "files": files,
            "package_fingerprint": canonical_fingerprint(files),
        }

    def _prepare(
        self,
        *,
        suite: str = "deterministic",
        repeat: int = 1,
        skill_package_root: Path | None = None,
    ) -> tuple[Path, dict]:
        result = subagent_eval.prepare_run(
            suite=suite,
            skill=SKILL,
            eval_id=EVAL_ID,
            skill_revision=SKILL_SHA,
            output_root=self.repository
            / ".agent-eval-runs"
            / f"run-{len(list((self.repository / '.agent-eval-runs').glob('*')))}",
            requested_settings={
                "model": "gpt-6-luna",
                "reasoning_effort": "max",
                "fork_turns": "none",
            },
            repeat=repeat,
            skill_package_root=skill_package_root,
        )
        return Path(result["run_root"]), result

    def _candidate_package(self) -> Path:
        root = self.repository / "candidate-package"
        skill_root = root / "skills" / SKILL
        (skill_root / "scripts").mkdir(parents=True)
        (skill_root / "SKILL.md").write_text(
            "# Candidate Skill\nClarify blocked runtime evidence.\n",
            encoding="utf-8",
        )
        (skill_root / "scripts" / "runtime_contract.py").write_text(
            "RUNTIME_IMPLEMENTATION = 'candidate'\n", encoding="utf-8"
        )
        (skill_root / "evals" / "output").mkdir(parents=True)
        (skill_root / "evals" / "output" / "expected.json").write_text(
            '{"private":"must not enter package"}', encoding="utf-8"
        )
        return root

    @staticmethod
    def _write_output(
        run_root: Path, attempt_id: str, value: str = "# Generated requirements\n"
    ) -> Path:
        path = run_root / "attempts" / attempt_id / "handoff" / "output.md"
        path.write_text(value, encoding="utf-8")
        return path

    @staticmethod
    def _write_agent_submission(
        run_root: Path, attempt_id: str, value: str = "# Generated requirements\n"
    ) -> Path:
        path = run_root / "attempts" / attempt_id / "agent-visible" / "submission.md"
        path.write_text(value, encoding="utf-8")
        return path

    def _seal(
        self, run_root: Path, attempt_id: str, *, status: str = "completed"
    ) -> dict:
        artifact_attempt_id = (
            attempt_id
            if (run_root / "attempts" / attempt_id / "handoff" / "output.md").exists()
            else None
        )
        return subagent_eval.seal_handoff(
            run_root=run_root,
            attempt_id=attempt_id,
            execution_status=status,
            artifact_attempt_id=artifact_attempt_id,
            started_at="2026-11-03T10:00:00Z",
            finished_at="2026-11-03T10:00:01Z",
        )

    def _join_processes(self, processes, start, results):
        for process in processes:
            process.start()
        start.set()
        for process in processes:
            process.join(20)
            self.assertFalse(process.is_alive(), "worker did not release the run lock")
            self.assertEqual(process.exitcode, 0)
        return [results.get(timeout=2) for _ in processes]

    def test_prepare_stages_only_input_and_package_and_records_unverified_host_fields(
        self,
    ) -> None:
        root, result = self._prepare()
        attempt = result["attempts"][0]
        attempt_root = root / "attempts" / attempt["attempt_id"]
        visible = attempt_root / "agent-visible"
        self.assertTrue((visible / "task.md").is_file())
        self.assertTrue((visible / ".agents" / "skills" / SKILL / "SKILL.md").is_file())
        self.assertFalse((visible / "evaluator-private").exists())
        self.assertIn(
            "PYTHONDONTWRITEBYTECODE=1 python -B",
            (visible / "task.md").read_text(encoding="utf-8"),
        )
        self.assertNotIn(
            "private expected fixture",
            (visible / "task.md").read_text(encoding="utf-8"),
        )
        self.assertNotIn(
            "Private reference text", (visible / "task.md").read_text(encoding="utf-8")
        )
        self.assertIn(
            "/agent-visible/submission.md",
            (visible / "task.md").read_text(encoding="utf-8"),
        )
        request = json.loads(
            (attempt_root / "evaluator-private" / "request.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(request["effective_settings"], {"status": "unverified"})
        self.assertEqual(request["physical_read_denial"], "unverified")
        self.assertEqual(result["attempts"][0]["status"], "awaiting_agent")
        self.assertEqual(result["attempts"][0]["skill_use_observation"], "unverified")

    def test_prepare_records_uncommitted_candidate_package_without_eval_data(self):
        candidate = self._candidate_package()
        root, result = self._prepare(skill_package_root=candidate)
        record = json.loads((root / "result.json").read_text(encoding="utf-8"))
        package = record["skill_package"]
        self.assertEqual(record["skill_revision"], SKILL_SHA)
        self.assertEqual(record["skill_candidate_revision_status"], "uncommitted_patch")
        self.assertEqual(package["revision"], SKILL_SHA)
        self.assertEqual(package["skills"], [SKILL])
        self.assertEqual(
            package["package_fingerprint"], canonical_fingerprint(package["files"])
        )
        self.assertFalse(any("/evals/" in item["path"] for item in package["files"]))
        attempt_id = result["attempts"][0]["attempt_id"]
        visible_skill = (
            root
            / "attempts"
            / attempt_id
            / "agent-visible"
            / ".agents"
            / "skills"
            / SKILL
        )
        self.assertEqual(
            (visible_skill / "SKILL.md").read_text(encoding="utf-8"),
            "# Candidate Skill\nClarify blocked runtime evidence.\n",
        )
        self.assertFalse((visible_skill / "evals").exists())

    def test_host_launch_request_uses_absolute_paths_and_excludes_private_content(self):
        root, prepared = self._prepare()
        attempt_id = prepared["attempts"][0]["attempt_id"]
        original_cwd = Path.cwd()
        with tempfile.TemporaryDirectory() as unrelated_cwd:
            try:
                os.chdir(unrelated_cwd)
                request = subagent_eval.host_launch_request(
                    run_root=root, attempt_id=attempt_id
                )
            finally:
                os.chdir(original_cwd)

        for field in (
            "working_directory",
            "task_path",
            "skill_entrypoint",
            "submission_path",
        ):
            self.assertTrue(Path(request[field]).is_absolute(), field)
        visible = root / "attempts" / attempt_id / "agent-visible"
        self.assertEqual(Path(request["working_directory"]), visible)
        self.assertEqual(request["task_path"], str(visible / "task.md"))
        self.assertEqual(
            request["skill_entrypoint"],
            str(visible / ".agents" / "skills" / SKILL / "SKILL.md"),
        )
        self.assertEqual(request["submission_path"], str(visible / "submission.md"))
        self.assertEqual(request["attempt_id"], attempt_id)
        self.assertEqual(request["artifact_attempt_id"], attempt_id)
        self.assertEqual(
            request["requested_settings"],
            {"model": "gpt-6-luna", "reasoning_effort": "max", "fork_turns": "none"},
        )
        launch_message = request["host_launch_message"]
        self.assertIn("tools.exec_command()", launch_message)
        self.assertIn(
            f"workdir` set to the absolute directory `{visible}`", launch_message
        )
        self.assertIn(str(visible / "task.md"), launch_message)
        self.assertIn(str(visible / ".agents" / "skills" / SKILL), launch_message)
        self.assertIn(str(visible / "submission.md"), launch_message)
        self.assertIn("Your first tool action must verify `pwd`", launch_message)
        self.assertIn("without guessing a relative path", launch_message)
        self.assertIn("Do not inspect expected data", launch_message)
        self.assertIn("the grader", launch_message)
        self.assertIn("evaluator-private files", launch_message)
        self.assertIn("any other attempt", launch_message)
        serialized = json.dumps(request)
        self.assertNotIn("private expected fixture", serialized)
        self.assertNotIn("Private reference text.", serialized)
        record = json.loads((root / "result.json").read_text(encoding="utf-8"))
        self.assertEqual(record["attempts"][0]["status"], "awaiting_agent")

    def test_host_launch_request_rejects_unknown_attempt(self):
        root, _prepared = self._prepare()
        with self.assertRaisesRegex(AgentEvalError, "missing or duplicated"):
            subagent_eval.host_launch_request(run_root=root, attempt_id="f" * 32)

    def test_host_launch_request_rejects_tampered_prepared_request_prompt_and_package(
        self,
    ):
        root, prepared = self._prepare()
        attempt_id = prepared["attempts"][0]["attempt_id"]
        request_path = (
            root / "attempts" / attempt_id / "evaluator-private" / "request.json"
        )
        request = json.loads(request_path.read_text(encoding="utf-8"))
        request["run_id"] = "changed-run-id"
        request_path.write_text(json.dumps(request), encoding="utf-8")
        with self.assertRaisesRegex(AgentEvalError, "request changed"):
            subagent_eval.host_launch_request(run_root=root, attempt_id=attempt_id)

        root, prepared = self._prepare()
        attempt_id = prepared["attempts"][0]["attempt_id"]
        task = root / "attempts" / attempt_id / "agent-visible" / "task.md"
        task.write_text("changed prepared prompt", encoding="utf-8")
        with self.assertRaisesRegex(AgentEvalError, "prompt changed"):
            subagent_eval.host_launch_request(run_root=root, attempt_id=attempt_id)

        root, prepared = self._prepare()
        attempt_id = prepared["attempts"][0]["attempt_id"]
        skill_file = (
            root
            / "attempts"
            / attempt_id
            / "agent-visible"
            / ".agents"
            / "skills"
            / SKILL
            / "SKILL.md"
        )
        skill_file.write_text("changed prepared package", encoding="utf-8")
        with self.assertRaisesRegex(AgentEvalError, "package files differ"):
            subagent_eval.host_launch_request(run_root=root, attempt_id=attempt_id)

    def test_host_launch_request_rejects_stale_submission_and_nonempty_handoff(self):
        root, prepared = self._prepare()
        attempt_id = prepared["attempts"][0]["attempt_id"]
        stale_submission = self._write_agent_submission(root, attempt_id)
        with self.assertRaisesRegex(AgentEvalError, "stale Agent-visible submission"):
            subagent_eval.host_launch_request(run_root=root, attempt_id=attempt_id)
        self.assertTrue(stale_submission.is_file())

        root, prepared = self._prepare()
        attempt_id = prepared["attempts"][0]["attempt_id"]
        stale_handoff = self._write_output(root, attempt_id)
        with self.assertRaisesRegex(AgentEvalError, "handoff directory is not empty"):
            subagent_eval.host_launch_request(run_root=root, attempt_id=attempt_id)
        self.assertTrue(stale_handoff.is_file())
        record = json.loads((root / "result.json").read_text(encoding="utf-8"))
        self.assertEqual(record["attempts"][0]["status"], "awaiting_agent")

    def test_prepare_rejects_candidate_package_with_an_extra_skill(self):
        candidate = self._candidate_package()
        extra = candidate / "skills" / "other-skill"
        extra.mkdir(parents=True)
        (extra / "SKILL.md").write_text("# Extra\n", encoding="utf-8")
        with self.assertRaisesRegex(AgentEvalError, "fixed Skill set"):
            self._prepare(skill_package_root=candidate)

    def test_improve_compares_development_handoff_runs_without_formal_promotion(self):
        baseline_root, baseline = self._prepare(repeat=2)
        candidate_package = self._candidate_package()
        candidate_root, candidate = self._prepare(
            repeat=2, skill_package_root=candidate_package
        )
        for run_root, prepared in (
            (baseline_root, baseline),
            (candidate_root, candidate),
        ):
            for row in prepared["attempts"]:
                subagent_eval.capture_agent_output(
                    run_root=run_root,
                    attempt_id=row["attempt_id"],
                    content=b"# generated artifact\n",
                )
                self._seal(run_root, row["attempt_id"])
                graded = subagent_eval.grade_attempt(
                    run_root=run_root, attempt_id=row["attempt_id"]
                )
                self.assertEqual(graded["status"], "pass")

        comparison = improve.compare_development_handoff_runs(
            baseline_root / "result.json", candidate_root / "result.json"
        )
        self.assertTrue(comparison["comparable"], comparison["condition_mismatches"])
        self.assertEqual(comparison["status"], "comparable_development_handoff")
        self.assertEqual(comparison["formal_acceptance"], "unverified")
        self.assertEqual(comparison["effective_model_status"], "unverified")
        self.assertEqual(len(comparison["paired_comparison"]), 2)
        self.assertFalse(comparison["improvement_demonstrated"])
        saved_path = self.repository / "handoff-comparison.json"
        exit_code = improve.main(
            [
                "compare-handoff",
                "--baseline-result",
                str(baseline_root / "result.json"),
                "--candidate-result",
                str(candidate_root / "result.json"),
                "--output",
                str(saved_path),
            ]
        )
        self.assertEqual(exit_code, 0)
        saved = json.loads(saved_path.read_text(encoding="utf-8"))
        self.assertEqual(saved["status"], "comparable_development_handoff")

    def test_handoff_comparison_rejects_missing_recorded_repeat(self):
        baseline_root, baseline = self._prepare(repeat=2)
        candidate_package = self._candidate_package()
        candidate_root, candidate = self._prepare(
            repeat=2, skill_package_root=candidate_package
        )
        for run_root, prepared in (
            (baseline_root, baseline),
            (candidate_root, candidate),
        ):
            for row in prepared["attempts"]:
                subagent_eval.capture_agent_output(
                    run_root=run_root,
                    attempt_id=row["attempt_id"],
                    content=b"# generated artifact\n",
                )
                self._seal(run_root, row["attempt_id"])
                subagent_eval.grade_attempt(
                    run_root=run_root, attempt_id=row["attempt_id"]
                )

        candidate_result_path = candidate_root / "result.json"
        candidate_record = json.loads(candidate_result_path.read_text(encoding="utf-8"))
        candidate_record["attempts"].pop()
        candidate_result_path.write_text(json.dumps(candidate_record), encoding="utf-8")

        comparison = improve.compare_development_handoff_runs(
            baseline_root / "result.json", candidate_result_path
        )
        self.assertFalse(comparison["comparable"])
        self.assertIn(
            "attempt_record_count_does_not_match_declared_repeat",
            comparison["condition_mismatches"]["candidate_attempt_inventory"],
        )
        self.assertIn(
            "attempt_directories_do_not_match_recorded_attempts",
            comparison["condition_mismatches"]["candidate_attempt_inventory"],
        )
        self.assertEqual(comparison["fixed_common_failures"], [])

    def test_handoff_comparison_reports_candidate_only_assertion_failure(self):
        baseline_root, baseline = self._prepare(repeat=2)
        candidate_package = self._candidate_package()
        candidate_root, candidate = self._prepare(
            repeat=2, skill_package_root=candidate_package
        )

        def grade_by_output(_skill, _eval_id, output_path, **_kwargs):
            is_candidate = output_path.read_text(encoding="utf-8").startswith(
                "candidate"
            )
            assertions = [
                {"id": "ASSERT-SHARED", "status": "pass"},
                {
                    "id": "ASSERT-CANDIDATE-ONLY",
                    "status": "fail" if is_candidate else "skip",
                },
            ]
            return {
                "skill": SKILL,
                "eval_id": EVAL_ID,
                "status": "fail" if is_candidate else "pass",
                "assertions": assertions,
            }

        with patch.object(
            subagent_eval, "grade_deterministic", side_effect=grade_by_output
        ):
            for run_root, prepared, prefix in (
                (baseline_root, baseline, b"baseline output\n"),
                (candidate_root, candidate, b"candidate output\n"),
            ):
                for row in prepared["attempts"]:
                    subagent_eval.capture_agent_output(
                        run_root=run_root,
                        attempt_id=row["attempt_id"],
                        content=prefix,
                    )
                    self._seal(run_root, row["attempt_id"])
                    subagent_eval.grade_attempt(
                        run_root=run_root, attempt_id=row["attempt_id"]
                    )

            comparison = improve.compare_development_handoff_runs(
                baseline_root / "result.json", candidate_root / "result.json"
            )

        self.assertTrue(comparison["comparable"], comparison["condition_mismatches"])
        self.assertEqual(
            comparison["paired_comparison"][0]["new_failures"],
            ["ASSERT-CANDIDATE-ONLY"],
        )

    def test_handoff_comparison_handles_null_host_execution_as_unverified_input(self):
        baseline_root, baseline = self._prepare(repeat=2)
        candidate_package = self._candidate_package()
        candidate_root, candidate = self._prepare(
            repeat=2, skill_package_root=candidate_package
        )
        for run_root, prepared in (
            (baseline_root, baseline),
            (candidate_root, candidate),
        ):
            for row in prepared["attempts"]:
                subagent_eval.capture_agent_output(
                    run_root=run_root,
                    attempt_id=row["attempt_id"],
                    content=b"# generated artifact\n",
                )
                self._seal(run_root, row["attempt_id"])
                subagent_eval.grade_attempt(
                    run_root=run_root, attempt_id=row["attempt_id"]
                )
        candidate_result_path = candidate_root / "result.json"
        candidate_record = json.loads(candidate_result_path.read_text(encoding="utf-8"))
        candidate_record["attempts"][0]["host_execution"] = None
        candidate_result_path.write_text(json.dumps(candidate_record), encoding="utf-8")

        comparison = improve.compare_development_handoff_runs(
            baseline_root / "result.json", candidate_result_path
        )
        self.assertFalse(comparison["comparable"])
        self.assertEqual(
            comparison["candidate_attempts"][0]["integrity_status"], "invalid"
        )
        self.assertIn(
            "recorded host execution evidence is malformed",
            comparison["candidate_attempts"][0]["reason"],
        )

    def test_completed_deterministic_handoff_is_integrity_checked_and_graded(
        self,
    ) -> None:
        root, prepared = self._prepare()
        attempt_id = prepared["attempts"][0]["attempt_id"]
        output = "# Test Requirements\n\n| TR ID | Source | Requirement |\n| --- | --- | --- |\n| TR-001 | SPEC-001 | Validate checkout |\n"
        captured = subagent_eval.capture_agent_output(
            run_root=root,
            attempt_id=attempt_id,
            content=output.encode("utf-8"),
        )
        self.assertEqual(captured["size_bytes"], len(output.encode("utf-8")))
        manifest = self._seal(root, attempt_id)
        self.assertEqual(manifest["artifact_attempt_id"], attempt_id)
        self.assertEqual(manifest["effective_settings"], {"status": "unverified"})

        result = subagent_eval.grade_attempt(run_root=root, attempt_id=attempt_id)
        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["execution_evidence_status"], "unverified")
        self.assertEqual(result["effective_settings_status"], "unverified")
        saved = json.loads((root / "result.json").read_text(encoding="utf-8"))
        self.assertEqual(saved["execution_method"], "codex_subagent_handoff")
        self.assertEqual(saved["profile_verification"], "unverified")
        saved_output = root / result["output"]["path"]
        self.assertEqual(saved_output.read_text(encoding="utf-8"), output)
        self.assertTrue(result["grade"]["sha256"].startswith("sha256:"))

    def test_captured_output_removed_before_seal_is_not_recorded_as_execution_error(
        self,
    ) -> None:
        root, prepared = self._prepare()
        attempt_id = prepared["attempts"][0]["attempt_id"]
        captured = subagent_eval.capture_agent_output(
            run_root=root,
            attempt_id=attempt_id,
            content=b"# Captured artifact\n",
        )
        output = root / captured["path"]
        output.unlink()

        with self.assertRaisesRegex(AgentEvalError, "captured output is missing"):
            subagent_eval.seal_handoff(
                run_root=root,
                attempt_id=attempt_id,
                execution_status="failed",
            )

        record = json.loads((root / "result.json").read_text(encoding="utf-8"))
        self.assertEqual(record["attempts"][0]["status"], "needs_review")
        self.assertEqual(record["summary"], {"needs_review": 1})
        self.assertFalse((output.parent / "manifest.json").exists())

    def test_agent_visible_file_is_imported_exactly_then_removed_before_grading(
        self,
    ) -> None:
        root, prepared = self._prepare()
        attempt_id = prepared["attempts"][0]["attempt_id"]
        output = (
            "# Test Requirements\n\n"
            "| TR ID | Source | Requirement |\n"
            "| --- | --- | --- |\n"
            "| TR-001 | SPEC-001 | Validate checkout |\n"
        )
        source = self._write_agent_submission(root, attempt_id, output)

        captured = subagent_eval.capture_agent_visible_output(
            run_root=root, attempt_id=attempt_id
        )

        self.assertEqual(captured["size_bytes"], len(output.encode("utf-8")))
        self.assertEqual(captured["sha256"], sha256_bytes(output.encode("utf-8")))
        self.assertFalse(source.exists())
        visible_files = {
            path.relative_to(source.parents[1]).as_posix()
            for path in source.parents[1].rglob("*")
            if path.is_file()
        }
        self.assertNotIn("submission.md", visible_files)
        self._seal(root, attempt_id)
        graded = subagent_eval.grade_attempt(run_root=root, attempt_id=attempt_id)
        saved_output = root / graded["output"]["path"]
        self.assertEqual(saved_output.read_bytes(), output.encode("utf-8"))
        self.assertEqual(graded["status"], "pass")

    def test_agent_visible_file_capture_rejects_symlink_and_hardlink(self) -> None:
        root, prepared = self._prepare(repeat=2)
        first, second = [row["attempt_id"] for row in prepared["attempts"]]
        outside = self.repository / "outside.md"
        outside.write_text("not an artifact", encoding="utf-8")
        self._write_agent_submission(root, first).unlink()
        (root / "attempts" / first / "agent-visible" / "submission.md").symlink_to(
            outside
        )
        with self.assertRaisesRegex(AgentEvalError, "submission is unavailable"):
            subagent_eval.capture_agent_visible_output(run_root=root, attempt_id=first)

        source = self._write_agent_submission(root, second)
        hardlink = self.repository / "submission-link.md"
        hardlink.hardlink_to(source)
        with self.assertRaisesRegex(AgentEvalError, "singly-linked"):
            subagent_eval.capture_agent_visible_output(run_root=root, attempt_id=second)
        saved = json.loads((root / "result.json").read_text(encoding="utf-8"))
        self.assertEqual(saved["attempts"][0]["status"], "needs_review")
        self.assertEqual(saved["attempts"][1]["status"], "needs_review")
        self.assertFalse(
            (root / "attempts" / second / "handoff" / "output.md").exists()
        )

    def test_agent_visible_secret_is_discarded_and_recorded_as_ungradeable(
        self,
    ) -> None:
        root, prepared = self._prepare()
        attempt_id = prepared["attempts"][0]["attempt_id"]
        source = self._write_agent_submission(
            root, attempt_id, "token=not-a-real-but-long-secret-value\n"
        )
        with self.assertRaisesRegex(AgentEvalError, "may contain a secret"):
            subagent_eval.capture_agent_visible_output(
                run_root=root, attempt_id=attempt_id
            )
        self.assertFalse(source.exists())
        self.assertFalse(
            (root / "attempts" / attempt_id / "handoff" / "output.md").exists()
        )
        saved = json.loads((root / "result.json").read_text(encoding="utf-8"))
        self.assertEqual(saved["attempts"][0]["status"], "needs_review")
        self.assertNotIn("sha256", saved["attempts"][0])

    def test_missing_output_is_saved_as_ungradeable_handoff(self) -> None:
        root, prepared = self._prepare()
        attempt_id = prepared["attempts"][0]["attempt_id"]
        with self.assertRaisesRegex(AgentEvalError, "requires output.md"):
            self._seal(root, attempt_id)
        saved = json.loads((root / "result.json").read_text(encoding="utf-8"))
        self.assertEqual(saved["attempts"][0]["status"], "needs_review")
        self.assertIn("requires output.md", saved["attempts"][0]["reason"])

    def test_nonstarted_attempt_is_saved_without_grading(self) -> None:
        root, prepared = self._prepare()
        attempt_id = prepared["attempts"][0]["attempt_id"]
        manifest = self._seal(root, attempt_id, status="not_started")
        self.assertEqual(manifest["artifacts"], [])
        saved = json.loads((root / "result.json").read_text(encoding="utf-8"))
        self.assertEqual(saved["attempts"][0]["status"], "not_started")
        with self.assertRaisesRegex(AgentEvalError, "not ready for grading"):
            subagent_eval.grade_attempt(run_root=root, attempt_id=attempt_id)

    def test_failed_host_execution_is_saved_without_grading(self) -> None:
        root, prepared = self._prepare()
        attempt_id = prepared["attempts"][0]["attempt_id"]
        manifest = subagent_eval.seal_handoff(
            run_root=root,
            attempt_id=attempt_id,
            execution_status="timed_out",
            started_at="2026-11-03T10:00:00Z",
            finished_at="2026-11-03T10:01:00Z",
        )
        self.assertEqual(manifest["execution_status"], "timed_out")
        saved = json.loads((root / "result.json").read_text(encoding="utf-8"))
        self.assertEqual(saved["attempts"][0]["status"], "execution error")
        with self.assertRaisesRegex(AgentEvalError, "not ready for grading"):
            subagent_eval.grade_attempt(run_root=root, attempt_id=attempt_id)

    def test_wrong_attempt_origin_and_duplicate_seal_are_rejected(self) -> None:
        root, prepared = self._prepare(repeat=2)
        first, second = [row["attempt_id"] for row in prepared["attempts"]]
        self._write_output(root, first)
        with self.assertRaisesRegex(AgentEvalError, "origin attempt ID"):
            subagent_eval.seal_handoff(
                run_root=root,
                attempt_id=first,
                execution_status="completed",
                artifact_attempt_id=second,
            )
        saved = json.loads((root / "result.json").read_text(encoding="utf-8"))
        self.assertEqual(saved["attempts"][0]["status"], "needs_review")
        self.assertEqual(saved["attempts"][0]["reported_execution_status"], "completed")

        root2, prepared2 = self._prepare()
        duplicate_attempt = prepared2["attempts"][0]["attempt_id"]
        self._write_output(root2, duplicate_attempt)
        self._seal(root2, duplicate_attempt)
        with self.assertRaisesRegex(AgentEvalError, "already sealed"):
            self._seal(root2, duplicate_attempt)

    def test_concurrent_seals_preserve_both_attempts_and_run_summary(self) -> None:
        root, prepared = self._prepare(repeat=2)
        attempts = prepared["attempts"]
        for attempt in attempts:
            self._write_output(root, attempt["attempt_id"])

        context = multiprocessing.get_context("spawn")
        start = context.Event()
        results = context.Queue()
        processes = [
            context.Process(
                target=_seal_attempt_process,
                args=(
                    str(self.repository),
                    str(root),
                    attempt["attempt_id"],
                    start,
                    results,
                ),
            )
            for attempt in attempts
        ]
        outcomes = self._join_processes(processes, start, results)

        self.assertCountEqual(outcomes, [(item["attempt_id"], "sealed") for item in attempts])
        record = json.loads((root / "result.json").read_text(encoding="utf-8"))
        self.assertEqual(
            {row["attempt_id"]: row["status"] for row in record["attempts"]},
            {item["attempt_id"]: "awaiting_grading" for item in attempts},
        )
        self.assertEqual(record["summary"], {"awaiting_grading": 2})
        for row in record["attempts"]:
            self.assertTrue((root / row["handoff_manifest"]["path"]).is_file())

    def test_concurrent_duplicate_seals_do_not_replace_the_winner(self) -> None:
        root, prepared = self._prepare()
        attempt_id = prepared["attempts"][0]["attempt_id"]
        self._write_output(root, attempt_id)

        context = multiprocessing.get_context("spawn")
        start = context.Event()
        results = context.Queue()
        processes = [
            context.Process(
                target=_seal_attempt_process,
                args=(str(self.repository), str(root), attempt_id, start, results),
            )
            for _ in range(2)
        ]
        outcomes = self._join_processes(processes, start, results)

        self.assertEqual(sum(value == "sealed" for _attempt, value in outcomes), 1)
        self.assertEqual(sum(value.startswith("error:") for _attempt, value in outcomes), 1)
        record = json.loads((root / "result.json").read_text(encoding="utf-8"))
        self.assertEqual(record["attempts"][0]["status"], "awaiting_grading")
        self.assertEqual(record["summary"], {"awaiting_grading": 1})
        self.assertTrue(
            (root / "attempts" / attempt_id / "handoff" / "manifest.json").is_file()
        )

    def test_capture_and_seal_race_is_atomic_and_keeps_a_coherent_attempt(self) -> None:
        root, prepared = self._prepare()
        attempt_id = prepared["attempts"][0]["attempt_id"]
        self._write_agent_submission(root, attempt_id)

        context = multiprocessing.get_context("spawn")
        start = context.Event()
        results = context.Queue()
        processes = [
            context.Process(
                target=_capture_or_seal_process,
                args=(str(self.repository), str(root), attempt_id, operation, start, results),
            )
            for operation in ("capture", "seal")
        ]
        self._join_processes(processes, start, results)

        record = json.loads((root / "result.json").read_text(encoding="utf-8"))
        row = record["attempts"][0]
        handoff = root / "attempts" / attempt_id / "handoff"
        if row["status"] == "awaiting_grading":
            self.assertTrue((handoff / "manifest.json").is_file())
            self.assertEqual(record["summary"], {"awaiting_grading": 1})
            self.assertEqual(
                row["captured_output"]["sha256"], row["ungraded_output"]["sha256"]
            )
        else:
            self.assertEqual(row["status"], "needs_review")
            self.assertEqual(record["summary"], {"needs_review": 1})
            self.assertFalse((handoff / "manifest.json").exists())
            self.assertNotIn("grade", row)

    def test_concurrent_duplicate_grades_preserve_the_first_grade(self) -> None:
        root, prepared = self._prepare()
        attempt_id = prepared["attempts"][0]["attempt_id"]
        self._write_output(root, attempt_id)
        self._seal(root, attempt_id)

        context = multiprocessing.get_context("spawn")
        start = context.Event()
        results = context.Queue()
        processes = [
            context.Process(
                target=_grade_attempt_process,
                args=(str(self.repository), str(root), attempt_id, start, results),
            )
            for _ in range(2)
        ]
        outcomes = self._join_processes(processes, start, results)

        self.assertEqual(sum(value == "graded" for _attempt, value in outcomes), 1)
        self.assertEqual(sum(value.startswith("error:") for _attempt, value in outcomes), 1)
        record = json.loads((root / "result.json").read_text(encoding="utf-8"))
        self.assertEqual(record["attempts"][0]["status"], "pass")
        self.assertEqual(record["summary"], {"pass": 1})

    def test_run_state_lock_rejects_symlink(self) -> None:
        root, prepared = self._prepare()
        attempt_id = prepared["attempts"][0]["attempt_id"]
        outside = self.repository / "outside-lock"
        outside.write_text("", encoding="utf-8")
        (root / ".result.lock").symlink_to(outside)
        with self.assertRaisesRegex(AgentEvalError, "may not contain symlinks"):
            subagent_eval.host_launch_request(run_root=root, attempt_id=attempt_id)
        self.assertEqual(outside.read_text(encoding="utf-8"), "")

    def test_symlink_and_extra_handoff_files_are_rejected(self) -> None:
        root, prepared = self._prepare()
        attempt_id = prepared["attempts"][0]["attempt_id"]
        outside = self.repository / "outside.md"
        outside.write_text("outside", encoding="utf-8")
        output = root / "attempts" / attempt_id / "handoff" / "output.md"
        output.symlink_to(outside)
        with self.assertRaisesRegex(AgentEvalError, "symlinks"):
            self._seal(root, attempt_id)

        root2, prepared2 = self._prepare()
        attempt_id2 = prepared2["attempts"][0]["attempt_id"]
        self._write_output(root2, attempt_id2)
        (root2 / "attempts" / attempt_id2 / "handoff" / "duplicate.md").write_text(
            "extra", encoding="utf-8"
        )
        with self.assertRaisesRegex(AgentEvalError, "unexpected files"):
            self._seal(root2, attempt_id2)

    def test_hardlinked_handoff_artifact_is_rejected(self) -> None:
        root, prepared = self._prepare()
        attempt_id = prepared["attempts"][0]["attempt_id"]
        output = self._write_output(root, attempt_id)
        link = output.with_name("output-copy.md")
        link.hardlink_to(output)
        with self.assertRaisesRegex(AgentEvalError, "singly-linked"):
            self._seal(root, attempt_id)

    def test_request_schema_and_unverified_fields_are_fixed(self) -> None:
        root, prepared = self._prepare()
        attempt_id = prepared["attempts"][0]["attempt_id"]
        request_path = (
            root / "attempts" / attempt_id / "evaluator-private" / "request.json"
        )
        request = json.loads(request_path.read_text(encoding="utf-8"))
        request["schema_version"] = 2
        request_path.write_text(json.dumps(request), encoding="utf-8")
        self._write_output(root, attempt_id)
        self._seal(root, attempt_id)
        with self.assertRaisesRegex(AgentEvalError, "did not pass import validation"):
            subagent_eval.grade_attempt(run_root=root, attempt_id=attempt_id)
        saved = json.loads((root / "result.json").read_text(encoding="utf-8"))
        self.assertEqual(saved["attempts"][0]["status"], "needs_review")
        self.assertEqual(saved["summary"], {"needs_review": 1})
        self.assertEqual(saved["status"], "needs_review_or_fail")

    def test_modified_artifact_and_malformed_manifest_do_not_receive_a_grade(
        self,
    ) -> None:
        root, prepared = self._prepare()
        attempt_id = prepared["attempts"][0]["attempt_id"]
        output = self._write_output(root, attempt_id)
        self._seal(root, attempt_id)
        output.write_text("changed after sealing", encoding="utf-8")
        with self.assertRaisesRegex(AgentEvalError, "did not pass import validation"):
            subagent_eval.grade_attempt(run_root=root, attempt_id=attempt_id)
        record = json.loads((root / "result.json").read_text(encoding="utf-8"))
        self.assertEqual(record["attempts"][0]["status"], "needs_review")
        self.assertNotIn("grade", record["attempts"][0])

        root2, prepared2 = self._prepare()
        attempt_id2 = prepared2["attempts"][0]["attempt_id"]
        self._write_output(root2, attempt_id2)
        self._seal(root2, attempt_id2)
        manifest_path = root2 / "attempts" / attempt_id2 / "handoff" / "manifest.json"
        manifest_path.write_text(
            '{"attempt_id":"x","attempt_id":"y"}', encoding="utf-8"
        )
        with self.assertRaisesRegex(AgentEvalError, "did not pass import validation"):
            subagent_eval.grade_attempt(run_root=root2, attempt_id=attempt_id2)
        record2 = json.loads((root2 / "result.json").read_text(encoding="utf-8"))
        self.assertEqual(record2["attempts"][0]["status"], "needs_review")

    def test_modified_prompt_or_skill_package_is_rejected(self) -> None:
        root, prepared = self._prepare()
        attempt_id = prepared["attempts"][0]["attempt_id"]
        self._write_output(root, attempt_id)
        self._seal(root, attempt_id)
        task = root / "attempts" / attempt_id / "agent-visible" / "task.md"
        task.write_text("changed prompt", encoding="utf-8")
        with self.assertRaisesRegex(AgentEvalError, "did not pass import validation"):
            subagent_eval.grade_attempt(run_root=root, attempt_id=attempt_id)
        saved = json.loads((root / "result.json").read_text(encoding="utf-8"))
        self.assertEqual(saved["attempts"][0]["evidence_status"], "evidence_unverified")

    def test_changed_skill_package_and_evaluator_revision_are_rejected(self) -> None:
        root, prepared = self._prepare()
        attempt_id = prepared["attempts"][0]["attempt_id"]
        self._write_output(root, attempt_id)
        self._seal(root, attempt_id)
        skill_file = (
            root
            / "attempts"
            / attempt_id
            / "agent-visible"
            / ".agents"
            / "skills"
            / SKILL
            / "SKILL.md"
        )
        skill_file.write_text("changed Skill package", encoding="utf-8")
        with self.assertRaisesRegex(AgentEvalError, "did not pass import validation"):
            subagent_eval.grade_attempt(run_root=root, attempt_id=attempt_id)
        saved = json.loads((root / "result.json").read_text(encoding="utf-8"))
        self.assertNotIn("grade", saved["attempts"][0])

        root2, prepared2 = self._prepare()
        attempt_id2 = prepared2["attempts"][0]["attempt_id"]
        self._write_output(root2, attempt_id2)
        self._seal(root2, attempt_id2)
        with patch.object(
            subagent_eval, "assert_clean_checkout", return_value="c" * 40
        ):
            with self.assertRaisesRegex(
                AgentEvalError, "did not pass import validation"
            ):
                subagent_eval.grade_attempt(run_root=root2, attempt_id=attempt_id2)
        saved2 = json.loads((root2 / "result.json").read_text(encoding="utf-8"))
        self.assertNotIn("grade", saved2["attempts"][0])

    def test_semantic_output_waits_for_judge_and_uses_existing_judge_prompt(
        self,
    ) -> None:
        root, prepared = self._prepare(suite="semantic")
        attempt_id = prepared["attempts"][0]["attempt_id"]
        self._write_output(root, attempt_id)
        self._seal(root, attempt_id)
        row = subagent_eval.grade_attempt(run_root=root, attempt_id=attempt_id)
        self.assertEqual(row["status"], "awaiting_judge")
        self.assertEqual(row["semantic_judge"]["judge_execution"], "unverified")
        judge_prompt = root / row["semantic_judge"]["prompt_path"]
        self.assertTrue(judge_prompt.is_file())
        self.assertIn(
            "Private reference text", judge_prompt.read_text(encoding="utf-8")
        )
        agent_visible = root / "attempts" / attempt_id / "agent-visible"
        self.assertFalse(
            any("judge-request" in path.name for path in agent_visible.rglob("*"))
        )
        self.assertNotIn("grade", row)

    def test_capture_rejects_secret_without_persisting_raw_output(self) -> None:
        root, prepared = self._prepare()
        attempt_id = prepared["attempts"][0]["attempt_id"]
        output = root / "attempts" / attempt_id / "handoff" / "output.md"
        with self.assertRaisesRegex(AgentEvalError, "may contain a secret"):
            subagent_eval.capture_agent_output(
                run_root=root,
                attempt_id=attempt_id,
                content=b"token=not-a-real-but-long-secret-value\n",
            )
        self.assertFalse(output.exists())
        saved = json.loads((root / "result.json").read_text(encoding="utf-8"))
        self.assertNotIn("sha256", saved["attempts"][0])
        self.assertEqual(saved["attempts"][0]["status"], "needs_review")
        self.assertEqual(saved["intake_validation"], "failed")

    def test_seal_rejects_secret_in_a_direct_handoff_file(self) -> None:
        root, prepared = self._prepare()
        attempt_id = prepared["attempts"][0]["attempt_id"]
        self._write_output(root, attempt_id, "token=not-a-real-but-long-secret-value\n")
        with self.assertRaisesRegex(AgentEvalError, "may contain a secret"):
            self._seal(root, attempt_id)
        output = root / "attempts" / attempt_id / "handoff" / "output.md"
        self.assertFalse(output.exists())
        saved = json.loads((root / "result.json").read_text(encoding="utf-8"))
        self.assertEqual(saved["attempts"][0]["status"], "needs_review")

    def test_run_root_outside_ignored_area_is_rejected(self) -> None:
        with self.assertRaisesRegex(AgentEvalError, "under .agent-eval-runs"):
            subagent_eval.prepare_run(
                suite="deterministic",
                skill=SKILL,
                eval_id=EVAL_ID,
                skill_revision=SKILL_SHA,
                output_root=self.repository / "not-ignored",
                requested_settings={
                    "model": "gpt-6-luna",
                    "reasoning_effort": "max",
                    "fork_turns": "none",
                },
            )


if __name__ == "__main__":
    unittest.main()
