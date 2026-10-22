from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.skills.evals.agent.judge_validation import (
    load_fixture_catalogue,
    run_validation,
)
from scripts.skills.evals.agent.qa_training_store import load_scenario
from scripts.skills.evals.agent.target_workspace import DEFAULT_TARGET_REVISION
from scripts.skills.evals.agent import judge_validation


def _profile() -> dict:
    return {
        "schema_version": 1,
        "agent": {
            "name": "fake-agent", "model": "fake-model", "timeout_seconds": 30,
            "cli_version": "test", "reasoning_effort": "low", "launch_options": [],
            "sandbox_policy": "isolated", "approval_policy": "never", "network_policy": "model API only",
            "tools": [], "mcp_servers": [], "skill_roots": ["/workspace/.agents/skills"],
            "external_instructions": "disabled", "global_config": "disabled",
        },
        "judge": {
            "model": "fake-judge", "command_argv": ["docker", "run", "--rm", "--read-only", "python:3.11", "judge"],
            "cwd": "isolated", "timeout_seconds": 30, "cli_version": "test", "reasoning_effort": "low",
            "launch_options": [], "sandbox_policy": "isolated", "approval_policy": "never",
            "network_policy": "model API only", "skill_roots": [], "global_config": "disabled",
            "tools": [], "mcp_servers": [], "external_instructions": "disabled",
        },
        "isolation": {"method": "fake-test", "agent_read_roots": ["/workspace"], "evaluator_read_blocked": True},
        "verification": {"status": "verified", "method": "fake-test", "evidence_path": "isolation.json"},
    }


class JudgeValidationTests(unittest.TestCase):
    def _baseline_output(self, output: Path, scenario: dict) -> None:
        output.mkdir(parents=True)
        artifacts = []
        routing = []
        for index, required in enumerate(scenario["required_artifacts"]):
            artifact_id = f"artifact-{index:02d}"
            name = f"artifact-{index:02d}.md"
            (output / name).write_text(f"Evidence for {required['skill']} {required['kind']}\n", encoding="utf-8")
            artifacts.append({**required, "artifact_id": artifact_id, "path": name})
            routing.append({
                "skill": required["skill"],
                "scope": required["scope"],
                "status": "executed",
                "reason": "The fixed request requires this artifact.",
                "artifact_ids": [artifact_id],
            })
        (output / "artifact-index.json").write_text(
            json.dumps({"schema_version": 1, "artifacts": artifacts, "routing": routing}),
            encoding="utf-8",
        )
        (output / "final-message.md").write_text("Analysis and design workflow completed.\n", encoding="utf-8")

    def _run(self, *, approved: bool, candidate: bool) -> dict:
        scenario = load_scenario()
        run_parent = judge_validation.REPO_ROOT / ".agent-eval-runs"
        created_parent = not run_parent.exists()
        run_parent.mkdir(exist_ok=True)
        try:
            with tempfile.TemporaryDirectory(dir=run_parent) as temporary:
                root = Path(temporary)
                baseline_root = root / "baseline"
                baseline_output = baseline_root / "attempt-01" / "qa-output"
                self._baseline_output(baseline_output, scenario)
                runtime_root = baseline_root / "attempt-01"
                (runtime_root / "runtime-checks.json").write_text(
                    json.dumps({"workflow_runtime": {
                        "workflow_runtime_can_complete": True,
                        "workflow_runtime_has_unclosed_issues": False,
                    }}),
                    encoding="utf-8",
                )
                second_output = baseline_root / "attempt-02" / "qa-output"
                self._baseline_output(second_output, scenario)
                second_runtime = baseline_root / "attempt-02"
                (second_runtime / "runtime-checks.json").write_text(
                    json.dumps({"workflow_runtime": {
                        "workflow_runtime_can_complete": True,
                        "workflow_runtime_has_unclosed_issues": False,
                    }}),
                    encoding="utf-8",
                )
                baseline_result = baseline_root / "result.json"
                baseline_result.write_text(json.dumps({
                    "profile_verification": "verified",
                    "evaluator_revision": "1" * 40,
                    "target_revision": DEFAULT_TARGET_REVISION,
                    "scenario_fingerprint": scenario["scenario_fingerprint"],
                    "attempts": [
                        {
                            "status": "pass",
                            "saved_result_root": "attempt-01",
                            "saved_output_root": "attempt-01/qa-output",
                        },
                        {
                            "status": "pass",
                            "saved_result_root": "attempt-02",
                            "saved_output_root": "attempt-02/qa-output",
                        },
                    ],
                }), encoding="utf-8")
                target = root / "target"
                target.mkdir()
                output = root / "judge-output"
                output.mkdir()
                (output / "isolation.json").write_text("{}\n", encoding="utf-8")
                catalogue = load_fixture_catalogue()
                approval = root / "approval.json"
                approval_path = None
                if approved:
                    approval.write_text(json.dumps({
                        "dataset_revision": catalogue["dataset_revision"],
                        "approvals": [{
                            "case_id": "normal-workflow",
                            "reviewer": "test-only-fixture-reviewer",
                            "approved_at": "2026-10-22T00:00:00Z",
                            "evidence": "docs/spec/features/checkout-and-payment.md#workflow",
                        }],
                    }), encoding="utf-8")
                    approval_path = approval
                profile_path = root / "profile.json"
                profile_path.write_text(json.dumps(_profile()), encoding="utf-8")

                def fake_judge(**kwargs):
                    criteria = kwargs["criteria"]
                    return {
                        "status": "pass",
                        "normalized": {"criteria": [
                            {"id": criterion, "evaluable": True, "rating": 3}
                            for criterion in criteria
                        ]},
                    }

                with (
                    patch.object(judge_validation, "assert_clean_checkout", return_value="2" * 40),
                    patch.object(judge_validation, "resolve_commit", return_value=DEFAULT_TARGET_REVISION),
                    patch.object(judge_validation, "extract_revision_files", return_value={
                        relative: b"Fixed specification reference.\n"
                        for relative in scenario["reference_paths"]
                    }),
                    patch.object(judge_validation, "verify_profile_evidence", return_value=True),
                    patch.object(judge_validation, "_run_judge_case", side_effect=fake_judge),
                ):
                    result = run_validation(
                        baseline_result=baseline_result,
                        target_root=target,
                        profile_path=profile_path,
                        output_root=output,
                        approval_path=approval_path,
                        proposal_command=None,
                        candidate_judge_command=["docker", "run", "--rm", "--read-only", "python:3.11", "candidate-judge"] if candidate else None,
                        max_cases=1,
                        max_seconds=60,
                        repeat=2,
                    )
                self.assertTrue((output / "result.json").is_file())
                return result
        finally:
            if created_parent:
                try:
                    run_parent.rmdir()
                except OSError:
                    pass

    def test_approved_fixture_and_candidate_judge_are_checked_on_independent_repeats(self) -> None:
        result = self._run(approved=True, candidate=True)
        self.assertEqual(result["status"], "verified")
        self.assertEqual(result["candidate_judge_validation_status"], "verified")
        self.assertEqual(result["cases"][0]["candidate_judge_status"], "verified")
        self.assertTrue(result["cases"][0]["candidate_matches_baseline"])

    def test_unapproved_fixture_remains_pending_even_when_fake_judge_matches(self) -> None:
        result = self._run(approved=False, candidate=False)
        self.assertEqual(result["status"], "review_pending")
        self.assertEqual(result["cases"][0]["status"], "review_pending")


if __name__ == "__main__":
    unittest.main()
