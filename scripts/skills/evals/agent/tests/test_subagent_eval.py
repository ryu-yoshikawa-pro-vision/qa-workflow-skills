from __future__ import annotations

import json
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
