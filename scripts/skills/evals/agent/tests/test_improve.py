from __future__ import annotations

import importlib
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from scripts.skills.evals.agent import improve as improve_module
from scripts.skills.evals.agent.common import (
    AgentEvalError,
    canonical_fingerprint,
    sha256_bytes,
    visible_skill_names,
)
from scripts.skills.evals.agent.improve import (
    _analysis_repair_gate,
    _assess_independent_case,
    _freeze_independent_eval_plan,
    _improvement_requirements,
    _judge_verification_map,
    _run_related_contract_tests,
    _skill_use_for_attempt,
    _stable_failures,
    _validate_analysis,
    _validate_repair_diff,
)
from scripts.skills.evals.agent.judge_validation import (
    _artifact_content_fingerprint,
    _fixture_approval_binding,
    _fixture_prompt,
    _prepare_fixture,
    load_fixture_catalogue,
)
from scripts.skills.evals.agent.qa_training_store import (
    build_artifact_manifest,
    load_scenario,
    validate_artifact_index,
)
from scripts.skills.evals.agent.target_workspace import DEFAULT_TARGET_REVISION
from scripts.skills.evals.agent.workspace import profile_fingerprint


def _write_baseline_output(output: Path, scenario: dict) -> None:
    output.mkdir(parents=True)
    artifacts = []
    routing = []
    for index, required in enumerate(scenario["required_artifacts"]):
        artifact_id = f"artifact-{index:02d}"
        name = f"artifact-{index:02d}.md"
        (output / name).write_text(
            f"Evidence for {required['skill']} {required['kind']}\n",
            encoding="utf-8",
        )
        artifacts.append({**required, "artifact_id": artifact_id, "path": name})
        routing.append(
            {
                "skill": required["skill"],
                "scope": required["scope"],
                "status": "executed",
                "reason": "The fixed request requires this artifact.",
                "artifact_ids": [artifact_id],
            }
        )
    (output / "artifact-index.json").write_text(
        json.dumps({"schema_version": 1, "artifacts": artifacts, "routing": routing}),
        encoding="utf-8",
    )
    (output / "final-message.md").write_text(
        "Analysis and design workflow completed.\n", encoding="utf-8"
    )


def _write_independent_run(
    root: Path,
    *,
    case: dict,
    package_fingerprint: str,
    candidate: bool,
    ratings: list[int],
) -> Path:
    root.mkdir(parents=True)
    attempts = []
    for repeat, rating in enumerate(ratings, start=1):
        attempt_root = root / f"repeat-{repeat}"
        attempt_root.mkdir()
        output_path = attempt_root / "output.md"
        output_path.write_text("Independent output\n", encoding="utf-8")
        trace_path = attempt_root / "agent-trace.json"
        trace_path.write_text(
            json.dumps(
                {
                    "status": "captured",
                    "turn_completed": True,
                    "turn_failed": False,
                    "commands": [
                        {
                            "successful": True,
                            "skill_files_read": [case["skill"]],
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        grade = (
            {
                "status": "pass",
                "assertions": [{"id": "assertion-1", "status": "pass"}],
            }
            if case["suite"] == "deterministic"
            else {
                "verdict": "pass",
                "criteria": [{"id": "criterion-1", "rating": rating}],
            }
        )
        grade_path = attempt_root / "grade.json"
        grade_path.write_text(json.dumps(grade), encoding="utf-8")
        attempt = {
            "repeat": repeat,
            "suite": case["suite"],
            "skill": case["skill"],
            "eval_id": case["case_id"],
            "input_fingerprint": case["input_fingerprint"],
            "status": "pass",
            "skill_use_observation": "observed",
            "agent_execution": {
                "exit_code": 0,
                "timed_out": False,
                "container_cleanup_status": "succeeded",
            },
            "agent_isolation": {"status": "verified"},
            "agent_trace": {
                "status": "captured",
                "redacted": False,
                "path": "agent-trace.json",
                "sha256": sha256_bytes(trace_path.read_bytes()),
            },
            "output": {
                "path": f"repeat-{repeat}/output.md",
                "sha256": sha256_bytes(output_path.read_bytes()),
            },
            "grade": {
                "path": f"repeat-{repeat}/grade.json",
                "sha256": sha256_bytes(grade_path.read_bytes()),
            },
        }
        if case["suite"] == "semantic":
            attempt["judge"] = [
                {
                    "exit_code": 0,
                    "timed_out": False,
                    "container_cleanup_status": "succeeded",
                }
            ]
        attempts.append(attempt)
    result_path = root / "result.json"
    result_path.write_text(
        json.dumps(
            {
                "status": "pass",
                "suite": case["suite"],
                "evaluator": {"revision": case["evaluator_revision"]},
                "skill_revision": case["skill_revision"],
                "dataset_fingerprint": case["dataset_fingerprint"],
                "profile_fingerprint": case["profile_fingerprint"],
                "profile_verification": "verified",
                "agent_command_fingerprint": case["agent_command_fingerprint"],
                "judge_command_fingerprint": case["judge_command_fingerprint"],
                "repeat": 2,
                "skill_package": {
                    "package_fingerprint": package_fingerprint,
                    "skills": [case["skill"]],
                },
                "skill_candidate_revision_status": (
                    "uncommitted_patch" if candidate else "git_commit"
                ),
                "workspace_cleanup": "succeeded",
                "attempts": attempts,
            }
        ),
        encoding="utf-8",
    )
    return result_path


def _write_deterministic_baseline(root: Path, *, assertion_status: str = "fail"):
    agent_run = importlib.import_module("scripts.skills.evals.agent.run")
    run_root = root / "deterministic-baseline"
    run_root.mkdir(parents=True)
    input_path = root / "input.md"
    input_path.write_text("Public deterministic evaluation input.\n", encoding="utf-8")
    input_bytes = input_path.read_bytes()
    case = {
        "skill": "test-case-design",
        "id": "TC-DT-TEST",
        "input": input_bytes.decode("utf-8"),
        "input_path": input_path,
        "expected_path": root / "expected.json",
        "fingerprint_files": [
            ("skills/test-case-design/evals/output/input.md", input_bytes),
            (
                "skills/test-case-design/evals/output/expected.json",
                b"{\"hidden\":true}",
            ),
        ],
    }
    template = ["docker", "run", "agent-image"]
    attempts = []
    for repeat in (1, 2):
        attempt_root = (
            run_root
            / "deterministic"
            / case["skill"]
            / case["id"]
            / f"attempt-{repeat:02d}"
        )
        output_root = attempt_root / "agent-output"
        output_root.mkdir(parents=True)
        output_path = output_root / "output.md"
        output_path.write_text(
            "Generated output with a reproducible deterministic defect.\n",
            encoding="utf-8",
        )
        grade = {
            "skill": case["skill"],
            "eval_id": case["id"],
            "status": "fail" if assertion_status == "fail" else "pass",
            "summary": {
                "errors": int(assertion_status == "fail"),
                "warnings": 0,
                "passed": int(assertion_status == "pass"),
                "total": 1,
                "assertion_pass_rate": 0.0 if assertion_status == "fail" else 1.0,
            },
            "assertions": [
                {
                    "id": "DT-ASSERT-001",
                    "status": assertion_status,
                    "severity": "error",
                    "message": "Synthetic fixed grader assertion.",
                    "evidence": {"actual": "visible output"},
                }
            ],
        }
        grade_path = attempt_root / "grade.json"
        grade_path.write_text(json.dumps(grade), encoding="utf-8")
        trace_path = attempt_root / "agent-trace.json"
        trace_path.write_text(
            json.dumps(
                {
                    "status": "captured",
                    "turn_completed": True,
                    "turn_failed": False,
                    "commands": [
                        {
                            "successful": True,
                            "skill_files_read": [case["skill"]],
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        attempts.append(
            {
                "attempt_id": f"attempt-{repeat:02d}",
                "suite": "deterministic",
                "skill": case["skill"],
                "eval_id": case["id"],
                "repeat": repeat,
                "input_fingerprint": sha256_bytes(input_bytes),
                "status": grade["status"],
                "skill_use_observation": "observed",
                "agent_execution": {
                    "exit_code": 0,
                    "timed_out": False,
                    "container_cleanup_status": "succeeded",
                },
                "agent_isolation": {"status": "verified"},
                "agent_trace": {
                    "status": "captured",
                    "redacted": False,
                    "path": "agent-trace.json",
                    "sha256": sha256_bytes(trace_path.read_bytes()),
                },
                "agent_command": {
                    "argv": template,
                    "fingerprint": canonical_fingerprint(template),
                },
                "output": {
                    "path": output_path.relative_to(run_root).as_posix(),
                    "sha256": sha256_bytes(output_path.read_bytes()),
                },
                "grade": {
                    "path": grade_path.relative_to(run_root).as_posix(),
                    "sha256": sha256_bytes(grade_path.read_bytes()),
                },
            }
        )
    dataset_fingerprint = agent_run._dataset_fingerprint(case["fingerprint_files"])
    run = {
        "schema_version": 1,
        "run_id": "deterministic-baseline-run",
        "suite": "deterministic",
        "status": "needs_review_or_fail"
        if assertion_status == "fail"
        else "pass",
        "evaluator": {"revision": "1" * 40},
        "skill_revision": "2" * 40,
        "skill_package": {
            "skills": [case["skill"]],
            "package_fingerprint": "baseline-package-fingerprint",
        },
        "skill_candidate_revision_status": "git_commit",
        "profile_verification": "verified",
        "profile_fingerprint": "profile-fingerprint",
        "agent_command_template": template,
        "agent_command_saved": True,
        "agent_command_fingerprint": canonical_fingerprint(template),
        "judge_command_fingerprint": canonical_fingerprint([]),
        "dataset_fingerprint": dataset_fingerprint,
        "repeat": 2,
        "cases_requested": 1,
        "workspace_cleanup": "succeeded",
        "summary": {"fail": 2} if assertion_status == "fail" else {"pass": 2},
        "exit_code": 1 if assertion_status == "fail" else 0,
        "attempts": attempts,
    }
    result_path = run_root / "result.json"
    result_path.write_text(json.dumps(run), encoding="utf-8")
    return result_path, run, case, run_root


def _complete_validation_fixture(root: Path) -> tuple[Path, str]:
    scenario = load_scenario()
    catalogue = load_fixture_catalogue()
    baseline_output = root / "baseline" / "attempt-01" / "qa-output"
    _write_baseline_output(baseline_output, scenario)
    baseline_fingerprint = _artifact_content_fingerprint(baseline_output)
    references = {
        relative: b"Fixed specification reference.\n"
        for relative in scenario["reference_paths"]
    }
    (root / "fixtures").mkdir()
    cases = []
    for definition in catalogue["cases"]:
        case_root = root / "fixtures" / definition["id"]
        case_root.mkdir()
        fixture_output, validation, final_message = _prepare_fixture(
            definition=definition,
            baseline_output=baseline_output,
            fixture_root=case_root,
            scenario=scenario,
        )
        prompt, criteria = _fixture_prompt(
            definition=definition,
            scenario=scenario,
            references=references,
            output=fixture_output,
            validation=validation,
            final_message=final_message,
            machine_summary={
                "required_artifacts_present": validation["status"] == "pass",
                "workflow_runtime_can_complete": True,
                "workflow_runtime_has_unclosed_issues": False,
            },
        )
        artifact_fingerprint = _artifact_content_fingerprint(fixture_output)
        binding = _fixture_approval_binding(
            catalogue=catalogue,
            definition=definition,
            scenario=scenario,
            references=references,
            baseline_artifact_fingerprint=baseline_fingerprint,
            artifact_content_fingerprint=artifact_fingerprint,
            prompt=prompt,
            criteria=criteria,
            normative_revision=DEFAULT_TARGET_REVISION,
        )
        rating = 3 if definition["expected"] == "rating_at_least_3" else 1
        normalized = {
            "criteria": [
                {
                    "id": criterion,
                    "status": "pass" if rating >= 3 else "fail",
                    "rating": rating,
                }
                for criterion in criteria
            ]
        }
        approval = {
            "case_id": definition["id"],
            "reviewer": "test-only-synthetic-reviewer",
            "approved_at": "2026-10-22T00:00:00Z",
            "evidence": definition["references"][0] + "#synthetic-test",
            "binding": binding,
            "status": "approved",
            "binding_status": "matched",
        }
        cases.append(
            {
                "case_id": definition["id"],
                "criteria": criteria,
                "expected": definition["expected"],
                "status": "verified",
                "approval": approval,
                "approval_binding": binding,
                "fixture_fingerprint": canonical_fingerprint(binding),
                "fixture_content_integrity_status": "verified",
                "judge_runs": [
                    {
                        "status": "pass",
                        "prompt_sha256": binding["judge_input_fingerprint"],
                        "expectation_matched": True,
                        "normalized": normalized,
                    }
                    for _ in range(2)
                ],
            }
        )
    result_path = root / "result.json"
    result_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "dataset_revision": catalogue["dataset_revision"],
                "fixture_catalogue_fingerprint": canonical_fingerprint(catalogue),
                "evaluator_revision": "1" * 40,
                "target_revision": DEFAULT_TARGET_REVISION,
                "judge_profile_fingerprint": "test-profile-fingerprint",
                "repeat": 2,
                "cases": cases,
            }
        ),
        encoding="utf-8",
    )
    return result_path, baseline_fingerprint


class ImprovementGateTests(unittest.TestCase):
    def _validate_deterministic_fixture(
        self,
        run: dict,
        case: dict,
        run_root: Path,
        *,
        grade_error: Exception | None = None,
        grade_override: dict | None = None,
    ):
        agent_run = importlib.import_module("scripts.skills.evals.agent.run")

        def fixed_grade(skill, eval_id, output_path, *, runtime_source_root):
            if grade_error is not None:
                raise grade_error
            if grade_override is not None:
                return grade_override
            return json.loads(
                (output_path.parent.parent / "grade.json").read_text(encoding="utf-8")
            )

        deterministic_module = types.ModuleType(
            "scripts.skills.evals.deterministic.run"
        )
        deterministic_module.grade = fixed_grade
        with (
            patch.object(agent_run, "_load_deterministic_cases", return_value=[case]),
            patch.dict(
                sys.modules,
                {"scripts.skills.evals.deterministic.run": deterministic_module},
            ),
        ):
            return improve_module._deterministic_attempt_data(
                run,
                run_root,
                runtime_source_root=run_root,
                expected_package_fingerprint="baseline-package-fingerprint",
            )

    def test_independent_eval_plan_freezes_all_existing_cases_without_expected_data(
        self,
    ) -> None:
        run_module = importlib.import_module("scripts.skills.evals.agent.run")
        deterministic = [
            {
                "id": "TC-OUT-001",
                "skill": "test-case-design",
                "input": "deterministic input one",
                "fingerprint_files": [],
            },
            {
                "id": "TC-OUT-002",
                "skill": "test-case-design",
                "input": "deterministic input two",
                "fingerprint_files": [],
            },
        ]
        semantic = [
            {
                "id": "TC-SEM-001",
                "skill": "test-case-design",
                "input": "semantic input one",
                "fingerprint_files": [],
            },
            {
                "id": "TC-SEM-002",
                "skill": "test-case-design",
                "input": "semantic input two",
                "fingerprint_files": [],
            },
        ]
        profile = {
            "agent": {"command_argv": ["agent", "--safe"], "skill_roots": []},
            "judge": {
                "command_argv": ["judge", "--safe"],
                "skill_roots": [],
                "cwd": "judge",
            },
            "isolation": {"agent_read_roots": []},
            "verification": {"evidence_path": "evidence.json"},
        }
        with (
            patch.object(
                run_module, "_load_deterministic_cases", return_value=deterministic
            ),
            patch.object(run_module, "_load_semantic_cases", return_value=semantic),
            patch.object(run_module, "_dataset_fingerprint", return_value="d" * 64),
        ):
            plan = _freeze_independent_eval_plan(
                skill="test-case-design",
                evaluator_revision="1" * 40,
                skill_revision="2" * 40,
                baseline_package_fingerprint="baseline-package-fingerprint",
                profile=profile,
                agent_command=["docker", "run", "agent"],
            )
        identities = {(row["suite"], row["case_id"]) for row in plan["cases"]}
        self.assertEqual(
            identities,
            {
                ("deterministic", "TC-OUT-001"),
                ("deterministic", "TC-OUT-002"),
                ("semantic", "TC-SEM-001"),
                ("semantic", "TC-SEM-002"),
            },
        )
        self.assertEqual(plan["status"], "ready")
        for row in plan["cases"]:
            self.assertRegex(row["input_fingerprint"], r"^sha256:[a-f0-9]{64}$")
            self.assertNotIn("input", row)
            self.assertNotIn("expected", row)
            self.assertEqual(row["repeat"], 2)
            self.assertTrue(row["grader"])
        self.assertTrue(plan["contract_tests"])
        self.assertTrue(
            all("sha256" in row and "path" in row for row in plan["contract_tests"])
        )

    def test_independent_eval_plan_fails_closed_when_case_loader_is_unavailable(
        self,
    ) -> None:
        run_module = importlib.import_module("scripts.skills.evals.agent.run")
        with patch.object(
            run_module,
            "_load_deterministic_cases",
            side_effect=ImportError("missing fixed Evaluator dependency"),
        ):
            plan = _freeze_independent_eval_plan(
                skill="test-case-design",
                evaluator_revision="1" * 40,
                skill_revision="2" * 40,
                baseline_package_fingerprint="baseline-package-fingerprint",
                profile={
                    "agent": {"skill_roots": []},
                    "judge": {"skill_roots": [], "cwd": "judge", "command_argv": []},
                    "isolation": {"agent_read_roots": []},
                    "verification": {"evidence_path": "evidence.json"},
                },
                agent_command=["docker", "run", "agent"],
            )
        self.assertEqual(plan["status"], "blocked")
        self.assertEqual(plan["cases"], [])
        self.assertIn("independent_eval_cases_unavailable", plan["block_reason"])

    def test_independent_comparison_checks_stability_evidence_and_no_regression(
        self,
    ) -> None:
        profile = {
            "agent": {"skill_roots": []},
            "judge": {"skill_roots": [], "cwd": "judge"},
            "isolation": {"agent_read_roots": []},
            "verification": {"evidence_path": "evidence.json"},
        }
        case = {
            "suite": "semantic",
            "skill": "test-case-design",
            "case_id": "TC-SEM-001",
            "input_fingerprint": "sha256:" + "a" * 64,
            "dataset_fingerprint": "sha256:" + "b" * 64,
            "evaluator_revision": "1" * 40,
            "skill_revision": "2" * 40,
            "profile_fingerprint": profile_fingerprint(profile),
            "agent_command_fingerprint": "sha256:" + "c" * 64,
            "judge_command_fingerprint": "sha256:" + "d" * 64,
        }
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            baseline = _write_independent_run(
                root / "baseline",
                case=case,
                package_fingerprint="baseline-package",
                candidate=False,
                ratings=[2, 2],
            )
            candidate_equal = _write_independent_run(
                root / "candidate-equal",
                case=case,
                package_fingerprint="candidate-package",
                candidate=True,
                ratings=[2, 2],
            )
            equal_assessment = _assess_independent_case(
                baseline_path=baseline,
                candidate_path=candidate_equal,
                case=case,
                profile=profile,
                baseline_package_fingerprint="baseline-package",
                candidate_package_fingerprint="candidate-package",
                comparison={"comparable": True},
            )
            self.assertEqual(equal_assessment["status"], "pass")
            self.assertTrue(equal_assessment["no_new_regressions"])

            candidate_regressed = _write_independent_run(
                root / "candidate-regressed",
                case=case,
                package_fingerprint="candidate-package-2",
                candidate=True,
                ratings=[1, 1],
            )
            regressed_assessment = _assess_independent_case(
                baseline_path=baseline,
                candidate_path=candidate_regressed,
                case=case,
                profile=profile,
                baseline_package_fingerprint="baseline-package",
                candidate_package_fingerprint="candidate-package-2",
                comparison={"comparable": True},
            )
            self.assertEqual(regressed_assessment["status"], "review_pending")
            self.assertFalse(regressed_assessment["no_new_regressions"])

            candidate_unstable = _write_independent_run(
                root / "candidate-unstable",
                case=case,
                package_fingerprint="candidate-package-3",
                candidate=True,
                ratings=[2, 3],
            )
            unstable_assessment = _assess_independent_case(
                baseline_path=baseline,
                candidate_path=candidate_unstable,
                case=case,
                profile=profile,
                baseline_package_fingerprint="baseline-package",
                candidate_package_fingerprint="candidate-package-3",
                comparison={"comparable": True},
            )
            self.assertEqual(unstable_assessment["status"], "review_pending")
            self.assertEqual(unstable_assessment["candidate_status"], "review_pending")

    def test_deterministic_only_failure_is_valid_without_judge(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            _result_path, run, case, run_root = _write_deterministic_baseline(
                Path(temporary)
            )
            result = self._validate_deterministic_fixture(run, case, run_root)
        self.assertEqual(result["failed_assertion_ids"], ["DT-ASSERT-001"])
        self.assertEqual(len(result["attempts"]), 2)

    def test_deterministic_trace_mutation_invalidates_saved_skill_use(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            _result_path, run, case, run_root = _write_deterministic_baseline(
                Path(temporary)
            )
            trace_path = run_root / "deterministic" / case["skill"] / case["id"]
            trace_path /= Path("attempt-01") / "agent-trace.json"
            trace_path.write_text('{"status":"captured"}\n', encoding="utf-8")
            with self.assertRaisesRegex(AgentEvalError, "trace changed"):
                self._validate_deterministic_fixture(run, case, run_root)

    def test_run_improvements_enters_deterministic_path_without_judge_validation(
        self,
    ) -> None:
        agent_run = importlib.import_module("scripts.skills.evals.agent.run")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            baseline_path, baseline, case, run_root = _write_deterministic_baseline(
                root
            )
            baseline["profile_fingerprint"] = "profile-fingerprint"
            baseline["agent"] = {
                "name": "fake",
                "model": "fake-model",
                "cli_version": "fake-version",
            }
            baseline["isolation"] = {
                "method": "docker",
                "agent_read_roots": [],
                "evaluator_read_blocked": True,
            }
            baseline_path.write_text(json.dumps(baseline), encoding="utf-8")
            (run_root / "isolation.json").write_text("verified\n", encoding="utf-8")
            profile = {
                "agent": {
                    "name": "fake",
                    "model": "fake-model",
                    "cli_version": "fake-version",
                    "timeout_seconds": 30,
                },
                "judge": {"command_argv": []},
                "isolation": {
                    "method": "docker",
                    "agent_read_roots": [],
                    "evaluator_read_blocked": True,
                },
                "verification": {"evidence_path": "isolation.json"},
            }
            output_root = root / "improvement"
            deterministic_module = types.ModuleType(
                "scripts.skills.evals.deterministic.run"
            )
            deterministic_module.grade = (
                lambda _skill, _eval, output, **_kwargs: json.loads(
                    (output.parent.parent / "grade.json").read_text(
                        encoding="utf-8"
                    )
                )
            )

            def prepare_output(output, **_kwargs):
                output.mkdir(parents=True, exist_ok=True)
                return output / "isolation.json"

            def create_workspace(_repo, _revision, destination):
                (destination / "skills" / "test-case-design").mkdir(parents=True)
                (destination / "skills" / "test-case-design" / "SKILL.md").write_text(
                    "Test case design instructions are explicit and reproducible.\n",
                    encoding="utf-8",
                )
                return {
                    "skills": ["test-case-design"],
                    "package_fingerprint": "baseline-package-fingerprint",
                }

            with (
                patch.object(
                    agent_run, "_load_deterministic_cases", return_value=[case]
                ),
                patch.dict(
                    sys.modules,
                    {"scripts.skills.evals.deterministic.run": deterministic_module},
                ),
                patch.object(
                    improve_module, "load_execution_profile", return_value=profile
                ),
                patch.object(
                    improve_module, "assert_clean_checkout", return_value="1" * 40
                ),
                patch.object(
                    improve_module,
                    "profile_fingerprint",
                    return_value="profile-fingerprint",
                ),
                patch.object(
                    improve_module,
                    "prepare_run_output_root",
                    side_effect=prepare_output,
                ),
                patch.object(
                    improve_module, "verify_profile_evidence", return_value=True
                ),
                patch.object(
                    improve_module,
                    "create_skill_workspace",
                    side_effect=create_workspace,
                ),
                patch.object(
                    improve_module,
                    "_freeze_independent_eval_plan",
                    return_value={
                        "status": "blocked",
                        "cases": [],
                        "contract_tests": [
                            {"path": "tests/test_skill.py", "sha256": "a" * 64}
                        ],
                        "block_reason": "independent deterministic case missing",
                    },
                ),
                patch.object(
                    improve_module,
                    "_run_related_contract_tests",
                    return_value={"status": "review_pending", "results": []},
                ),
            ):
                result = improve_module.run_improvements(
                    baseline_result=baseline_path,
                    judge_validation_result=None,
                    target_root=None,
                    profile_path=root / "profile.json",
                    output_root=output_root,
                    verifier_image=None,
                    max_cases=1,
                    max_repairs=1,
                    max_seconds=120,
                    analyze_only=False,
                )
        self.assertEqual(result["evidence_basis"], "deterministic_only")
        self.assertFalse(result["judge_required"])
        self.assertEqual(result["grader_evidence"]["status"], "recomputed_match")
        self.assertEqual(result["cases"][0]["status"], "review_pending")
        self.assertEqual(result["repair_attempts_started"], 0)

    def test_deterministic_grader_failure_and_missing_grade_block(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            _result_path, run, case, run_root = _write_deterministic_baseline(
                Path(temporary)
            )
            with self.assertRaisesRegex(
                AgentEvalError, "fixed deterministic grader failed"
            ):
                self._validate_deterministic_fixture(
                    run, case, run_root, grade_error=RuntimeError("grader crashed")
                )
            mismatch = json.loads(
                (run_root / run["attempts"][0]["grade"]["path"]).read_text(
                    encoding="utf-8"
                )
            )
            mismatch["assertions"][0]["status"] = "pass"
            with self.assertRaisesRegex(AgentEvalError, "does not match"):
                self._validate_deterministic_fixture(
                    run, case, run_root, grade_override=mismatch
                )
            (run_root / run["attempts"][0]["grade"]["path"]).unlink()
            with self.assertRaisesRegex(AgentEvalError, "saved evaluation path"):
                self._validate_deterministic_fixture(run, case, run_root)

    def test_deterministic_candidate_missing_result_is_review_pending(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            evidence_root = root / "evidence"
            evidence_root.mkdir()
            (evidence_root / "isolation.json").write_text(
                "verified\n", encoding="utf-8"
            )
            profile = {
                "agent": {
                    "name": "fake",
                    "model": "fake-model",
                    "cli_version": "fake-version",
                    "timeout_seconds": 30,
                },
                "verification": {"evidence_path": "isolation.json"},
            }
            with patch.object(improve_module, "run_agent_evaluation", return_value=2):
                result = improve_module._run_deterministic_candidate_eval(
                    baseline={
                        "skill_revision": "2" * 40,
                        "agent_command_template": ["docker", "run", "agent"],
                    },
                    skill="test-case-design",
                    eval_id="TC-DT-TEST",
                    profile=profile,
                    profile_path=root / "profile.json",
                    evidence_root=evidence_root,
                    destination=root / "candidate-run",
                    candidate_package=root / "candidate-package",
                    timeout_seconds=240,
                )
            self.assertEqual(result["status"], "review_pending")
            self.assertIn("did_not_save_result", result["reason"])


    def test_deterministic_environment_skill_use_and_mixed_evidence_block(self) -> None:
        mutations = (
            ("environment", lambda row: row["agent_execution"].update(exit_code=1)),
            (
                "skill_unused",
                lambda row: row.update(skill_use_observation="unverified"),
            ),
            ("mixed", lambda row: row.update(judge=[{"status": "pass"}])),
        )
        for label, mutate in mutations:
            with self.subTest(label=label), tempfile.TemporaryDirectory() as temporary:
                _result_path, run, case, run_root = _write_deterministic_baseline(
                    Path(temporary)
                )
                mutate(run["attempts"][0])
                with self.assertRaises(AgentEvalError):
                    self._validate_deterministic_fixture(run, case, run_root)

    def test_semantic_or_mixed_improvement_requires_judge_validation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            baseline_path = Path(temporary) / "semantic-result.json"
            baseline_path.write_text(
                json.dumps({"suite": "semantic", "attempts": []}),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(AgentEvalError, "requires a verified Judge"):
                improve_module.run_improvements(
                    baseline_result=baseline_path,
                    judge_validation_result=None,
                    target_root=None,
                    profile_path=Path(temporary) / "profile.json",
                    output_root=Path(temporary) / "out",
                    verifier_image=None,
                    max_cases=1,
                    max_repairs=1,
                    max_seconds=60,
                    analyze_only=False,
                )

    def test_deterministic_improvement_requires_independent_case_and_contract_pass(
        self,
    ) -> None:
        before = [
            {
                "snapshot": {"DT-ASSERT-001": "fail"},
                "grade": {"status": "fail"},
                "attempt": {"skill_use_observation": "observed"},
            }
            for _ in range(2)
        ]
        after = [
            {
                "snapshot": {"DT-ASSERT-001": "pass"},
                "grade": {"status": "pass"},
                "attempt": {"skill_use_observation": "observed"},
            }
            for _ in range(2)
        ]
        baseline = {
            "skill": "test-case-design",
            "eval_id": "TC-DT-TEST",
            "input_fingerprint": "input-fingerprint",
            "dataset_fingerprint": "dataset-fingerprint",
            "failed_assertion_ids": ["DT-ASSERT-001"],
            "attempts": before,
        }
        candidate = {
            **baseline,
            "failed_assertion_ids": [],
            "attempts": after,
        }
        contract = {
            "status": "pass",
            "planned": 1,
            "completed": 1,
            "conditions_match": True,
            "results": [{"status": "pass"}],
        }
        independent = {
            "status": "pass",
            "planned": 1,
            "cases": [{"status": "pass"}],
            "expected_inputs_disclosed": False,
            "expected_results_disclosed": False,
            "feedback_to_repair_agent": False,
            "candidate_fingerprint_fixed": True,
            "conditions_match": True,
        }
        assessment = improve_module._assess_deterministic_improvement(
            baseline,
            candidate,
            comparison={"comparable": True},
            independent_assessment=independent,
            contract_test_assessment=contract,
        )
        self.assertTrue(assessment["improvement_demonstrated"])
        pending = improve_module._assess_deterministic_improvement(
            baseline,
            candidate,
            comparison={"comparable": True},
            independent_assessment={
                **independent,
                "status": "review_pending",
                "cases": [{"status": "review_pending"}],
            },
            contract_test_assessment=contract,
        )
        self.assertFalse(pending["improvement_demonstrated"])
        self.assertFalse(pending["requirements"]["independent_cases_passed"])

    def test_deterministic_independent_plan_freezes_semantic_case_as_judge_gated(
        self,
    ) -> None:
        agent_run = importlib.import_module("scripts.skills.evals.agent.run")
        profile = {
            "agent": {"skill_roots": []},
            "judge": {"skill_roots": [], "cwd": "judge", "command_argv": []},
            "isolation": {"agent_read_roots": []},
            "verification": {"evidence_path": "evidence.json"},
        }
        cases = [
            {
                "skill": "test-case-design",
                "id": "TC-DT-OTHER",
                "input": "Independent input\n",
                "fingerprint_files": [("input.md", b"Independent input\n")],
            }
        ]
        semantic_cases = [
            {
                "skill": "test-case-design",
                "id": "TC-SEM-OTHER",
                "input": "Semantic input\n",
                "fingerprint_files": [("semantic-input.md", b"Semantic input\n")],
            }
        ]
        with (
            patch.object(agent_run, "_load_deterministic_cases", return_value=cases),
            patch.object(
                agent_run,
                "_load_semantic_cases",
                return_value=semantic_cases,
            ),
            patch.object(
                improve_module,
                "_related_contract_tests",
                return_value=[{"path": "tests/test_skill.py", "sha256": "a" * 64}],
            ),
        ):
            plan = _freeze_independent_eval_plan(
                skill="test-case-design",
                evaluator_revision="1" * 40,
                skill_revision="2" * 40,
                baseline_package_fingerprint="baseline-package-fingerprint",
                profile=profile,
                agent_command=["docker", "run", "agent"],
            )
        self.assertEqual(plan["status"], "ready")
        self.assertEqual(
            [row["suite"] for row in plan["cases"]], ["deterministic", "semantic"]
        )

    def test_deterministic_independent_case_runs_while_semantic_case_stays_pending(
        self,
    ) -> None:
        deterministic_case = {
            "suite": "deterministic",
            "skill": "test-case-design",
            "case_id": "TC-DT-OTHER",
            "baseline_package_fingerprint": "baseline-package",
        }
        semantic_case = {
            "suite": "semantic",
            "skill": "test-case-design",
            "case_id": "TC-SEM-OTHER",
            "verification_status": "judge_unverified",
        }
        baseline_results = [
            {
                "case": deterministic_case,
                "status": "captured",
                "validation": {"status": "pass"},
                "result_path": "baseline-deterministic.json",
            },
            {
                "case": semantic_case,
                "status": "review_pending",
                "reason": "semantic_independent_case_requires_verified_judge",
            },
        ]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)

            def fake_run(**kwargs):
                destination = kwargs["destination"]
                destination.mkdir(parents=True, exist_ok=True)
                result_path = destination / "result.json"
                result_path.write_text("{}\n", encoding="utf-8")
                return {"status": "captured", "result_path": str(result_path)}

            with (
                patch.object(
                    improve_module, "_run_independent_eval", side_effect=fake_run
                ) as run_spy,
                patch.object(
                    improve_module,
                    "_assess_independent_case",
                    return_value={
                        "status": "pass",
                        "conditions_match": True,
                        "no_new_regressions": True,
                        "candidate_package_fingerprint": "candidate-package",
                    },
                ),
            ):
                result = improve_module._run_candidate_independent_assessment(
                    plan={"cases": [deterministic_case, semantic_case]},
                    baseline_results=baseline_results,
                    baseline={"agent_command_template": ["docker", "run", "agent"]},
                    profile={},
                    profile_path=root / "profile.json",
                    evidence_root=root,
                    case_root=root / "case",
                    candidate_package=root / "candidate-package",
                    candidate_package_fingerprint="candidate-package",
                    timeout_seconds=100,
                    compare_runs=lambda *_args: {"comparable": True},
                )
        self.assertEqual(run_spy.call_count, 1)
        self.assertEqual(run_spy.call_args.kwargs["case"]["suite"], "deterministic")
        self.assertEqual(result["status"], "review_pending")
        self.assertEqual(
            [row["status"] for row in result["cases"]],
            ["pass", "review_pending"],
            result,
        )

    def test_independent_deterministic_run_regrades_and_resolves_saved_trace(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            result_path, run, case_data, run_root = _write_deterministic_baseline(
                Path(temporary)
            )
            profile = {
                "agent": {},
                "judge": {},
                "isolation": {},
                "verification": {},
            }
            run["profile_fingerprint"] = "profile-fingerprint"
            run["agent_command_fingerprint"] = canonical_fingerprint(
                run["agent_command_template"]
            )
            case = {
                "suite": "deterministic",
                "skill": case_data["skill"],
                "case_id": case_data["id"],
                "input_fingerprint": run["attempts"][0]["input_fingerprint"],
                "dataset_fingerprint": run["dataset_fingerprint"],
                "evaluator_revision": "1" * 40,
                "skill_revision": "2" * 40,
                "profile_fingerprint": "profile-fingerprint",
                "agent_command_fingerprint": run["agent_command_fingerprint"],
                "judge_command_fingerprint": run["judge_command_fingerprint"],
            }
            fake_module = types.ModuleType("scripts.skills.evals.deterministic.run")
            fake_module.grade = lambda _skill, _eval, output, **_kwargs: json.loads(
                (output.parent.parent / "grade.json").read_text(encoding="utf-8")
            )
            with (
                patch.object(
                    improve_module,
                    "profile_fingerprint",
                    return_value="profile-fingerprint",
                ),
                patch.dict(
                    sys.modules,
                    {"scripts.skills.evals.deterministic.run": fake_module},
                ),
            ):
                assessment = improve_module._validate_independent_run(
                    result_path,
                    case=case,
                    profile=profile,
                    package_fingerprint="baseline-package-fingerprint",
                    candidate=False,
                    runtime_source_root=run_root,
                )
            trace_path = (
                run_root
                / "deterministic"
                / case_data["skill"]
                / case_data["id"]
                / "attempt-01"
                / "agent-trace.json"
            )
            trace_path.write_text('{"status":"captured"}\n', encoding="utf-8")
            with patch.object(
                improve_module,
                "profile_fingerprint",
                return_value="profile-fingerprint",
            ), patch.dict(
                sys.modules,
                {"scripts.skills.evals.deterministic.run": fake_module},
            ):
                tampered_assessment = improve_module._validate_independent_run(
                    result_path,
                    case=case,
                    profile=profile,
                    package_fingerprint="baseline-package-fingerprint",
                    candidate=False,
                    runtime_source_root=run_root,
                )
        self.assertEqual(assessment["status"], "pass")
        self.assertEqual(assessment["grades"][1]["DT-ASSERT-001"], 0)
        self.assertEqual(tampered_assessment["status"], "review_pending")
        self.assertIn("trace changed", tampered_assessment["reason"])

    def test_related_contract_tests_require_the_frozen_candidate_package(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            package = Path(temporary) / "candidate"
            skill_root = package / "skills" / "test-case-design"
            skill_root.mkdir(parents=True)
            (skill_root / "SKILL.md").write_text("candidate\n", encoding="utf-8")
            result = _run_related_contract_tests(
                [],
                timeout_seconds=10,
                evaluator_revision="1" * 40,
                skill="test-case-design",
                skill_revision="2" * 40,
                expected_skills={"test-case-design"},
                candidate_package=package,
                candidate_package_fingerprint="sha256:" + "a" * 64,
            )
        self.assertEqual(result["status"], "review_pending")
        self.assertFalse(result["conditions_match"])
        self.assertIn("candidate Skill package changed", result["results"][0]["reason"])

    def test_improvement_requires_target_independent_and_contract_success(self) -> None:
        passing_independent = {
            "status": "pass",
            "planned": 1,
            "cases": [{"status": "pass"}],
            "expected_inputs_disclosed": False,
            "expected_results_disclosed": False,
            "feedback_to_repair_agent": False,
            "candidate_fingerprint_fixed": True,
            "conditions_match": True,
        }
        passing_contract_tests = {
            "status": "pass",
            "planned": 1,
            "completed": 1,
            "conditions_match": True,
            "results": [{"status": "pass"}],
        }

        def assess(**overrides):
            values = {
                "target_improved": True,
                "no_critical_regressions": True,
                "skill_use_verified": True,
                "target_conditions_match": True,
                "independent_assessment": passing_independent,
                "contract_test_assessment": passing_contract_tests,
            }
            values.update(overrides)
            return _improvement_requirements(**values)

        self.assertTrue(assess()["improvement_demonstrated"])
        self.assertFalse(
            assess(independent_assessment=None)["improvement_demonstrated"]
        )
        self.assertFalse(
            assess(
                independent_assessment={
                    **passing_independent,
                    "status": "review_pending",
                    "cases": [{"status": "review_pending"}],
                }
            )["improvement_demonstrated"]
        )
        self.assertFalse(
            assess(
                independent_assessment={
                    **passing_independent,
                    "cases": [{"status": "fail"}],
                }
            )["improvement_demonstrated"]
        )
        self.assertFalse(
            assess(
                contract_test_assessment={
                    **passing_contract_tests,
                    "status": "review_pending",
                }
            )["improvement_demonstrated"]
        )
        self.assertFalse(
            assess(target_conditions_match=False)["improvement_demonstrated"]
        )
        self.assertFalse(assess(skill_use_verified=False)["improvement_demonstrated"])
        self.assertFalse(
            assess(
                independent_assessment={
                    **passing_independent,
                    "expected_results_disclosed": True,
                }
            )["improvement_demonstrated"]
        )
        self.assertFalse(assess(target_improved=False)["improvement_demonstrated"])

    def test_analysis_evidence_requires_source_text_matching_path_and_hash(
        self,
    ) -> None:
        artifact_text = "The output omits the requested boundary condition.\n"
        skill_text = (
            "Derive cases from each stated boundary and record the rationale.\n"
        )
        sources = {
            "original-artifacts/attempt-01/cases.md": {
                "sha256": sha256_bytes(artifact_text.encode()),
                "kind": "artifact",
                "text": artifact_text,
            },
            ".agents/skills/test-case-design/SKILL.md": {
                "sha256": sha256_bytes(skill_text.encode()),
                "kind": "skill",
                "text": skill_text,
            },
        }
        value = {
            "classification": "skill",
            "skill": "test-case-design",
            "issue": "The source does not require explicit boundary derivation.",
            "evidence": [
                {
                    "path": "original-artifacts/attempt-01/cases.md",
                    "sha256": sources["original-artifacts/attempt-01/cases.md"][
                        "sha256"
                    ],
                    "quote": "The output omits the requested boundary condition.",
                },
                {
                    "path": ".agents/skills/test-case-design/SKILL.md",
                    "sha256": sources[".agents/skills/test-case-design/SKILL.md"][
                        "sha256"
                    ],
                    "quote": "Derive cases from each stated boundary and record the rationale.",
                },
            ],
            "alternative_causes": [],
            "repair_paths": ["SKILL.md"],
            "repair_rationale": "Clarify the existing boundary analysis step.",
        }
        accepted = _validate_analysis(
            json.dumps(value),
            skill_names={"test-case-design"},
            criterion="QTS-SEM-006",
            evidence_sources=sources,
        )
        self.assertEqual(accepted["skill"], "test-case-design")

        path_only = json.loads(json.dumps(value))
        path_only["evidence"] = [
            f"{row['path']} sha256:{row['sha256']}" for row in value["evidence"]
        ]
        with self.assertRaises(AgentEvalError):
            _validate_analysis(
                json.dumps(path_only),
                skill_names={"test-case-design"},
                criterion="QTS-SEM-006",
                evidence_sources=sources,
            )

        changed_quote = json.loads(json.dumps(value))
        changed_quote["evidence"][0]["quote"] = "A fabricated missing requirement."
        with self.assertRaises(AgentEvalError):
            _validate_analysis(
                json.dumps(changed_quote),
                skill_names={"test-case-design"},
                criterion="QTS-SEM-006",
                evidence_sources=sources,
            )

    def test_repair_gate_blocks_unresolved_causes_unobserved_skill_and_other_paths(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            package = Path(temporary) / "package"
            skill_root = package / "skills" / "test-case-design"
            skill_root.mkdir(parents=True)
            (skill_root / "SKILL.md").write_text(
                "Use boundary analysis.\n", encoding="utf-8"
            )
            artifact = {
                "path": "original-artifacts/attempt-01/cases.md",
                "sha256": "sha256:" + "a" * 64,
                "quote": "The observed artifact has a gap.",
            }
            skill = {
                "path": ".agents/skills/test-case-design/SKILL.md",
                "sha256": "sha256:" + "b" * 64,
                "quote": "Use boundary analysis.",
            }
            sources = {
                artifact["path"]: {"kind": "artifact"},
                skill["path"]: {"kind": "skill"},
            }
            attempts = [
                {
                    "attempt": {
                        "skill_use_observation": {"test-case-design": "observed"}
                    }
                },
                {
                    "attempt": {
                        "skill_use_observation": {"test-case-design": "observed"}
                    }
                },
            ]
            analysis = {
                "classification": "skill",
                "skill": "test-case-design",
                "evidence": [artifact, skill],
                "alternative_causes": ["The Agent may have ignored the Skill."],
                "repair_paths": ["SKILL.md"],
            }
            unresolved = _analysis_repair_gate(
                analysis,
                allowed_skills={"test-case-design"},
                attempts=attempts,
                evidence_sources=sources,
                package_root=package,
            )
            self.assertFalse(unresolved["allowed"])
            self.assertIn("alternative_causes_remain_unresolved", unresolved["reasons"])

            resolved = dict(analysis, alternative_causes=[])
            self.assertTrue(
                _analysis_repair_gate(
                    resolved,
                    allowed_skills={"test-case-design"},
                    attempts=attempts,
                    evidence_sources=sources,
                    package_root=package,
                )["allowed"]
            )
            unobserved_attempts = [
                attempts[0],
                {"attempt": {"skill_use_observation": "unverified"}},
            ]
            unobserved = _analysis_repair_gate(
                resolved,
                allowed_skills={"test-case-design"},
                attempts=unobserved_attempts,
                evidence_sources=sources,
                package_root=package,
            )
            self.assertFalse(unobserved["allowed"])
            self.assertIn(
                "selected_skill_use_not_observed_in_every_baseline_attempt",
                unobserved["reasons"],
            )
            other_skill = dict(resolved, repair_paths=["qa-workflow/SKILL.md"])
            rejected_path = _analysis_repair_gate(
                other_skill,
                allowed_skills={"test-case-design"},
                attempts=attempts,
                evidence_sources=sources,
                package_root=package,
            )
            self.assertFalse(rejected_path["allowed"])
            self.assertIn(
                "analysis_requested_path_outside_single_skill_allowlist",
                rejected_path["reasons"],
            )

    def _run_integrated_qts_gate(
        self,
        *,
        skill_observation: str,
        alternative_causes: list[str],
        artifact_state: str = "valid",
        trace_skill_observed: bool | None = None,
    ):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_root = root / "baseline-run"
            target_root = root / "target"
            target_root.mkdir()
            (run_root / "isolation.json").parent.mkdir(parents=True)
            (run_root / "isolation.json").write_text("{}\n", encoding="utf-8")
            scenario = load_scenario()
            required_index = next(
                index
                for index, required in enumerate(scenario["required_artifacts"])
                if required["skill"] == "test-case-design"
            )
            artifact_path = f"artifact-{required_index:02d}.md"
            artifact_text = "Evidence for test-case-design test-case\n"
            skill_text = "Use explicit boundaries when designing test cases.\n"
            attempts = []
            for index in (1, 2):
                attempt_root = run_root / f"attempt-{index:02d}"
                output = attempt_root / "qa-output"
                _write_baseline_output(output, scenario)
                validation = validate_artifact_index(output, scenario)
                self.assertEqual(validation["status"], "pass")
                (attempt_root / "artifact-validation.json").write_text(
                    json.dumps(validation), encoding="utf-8"
                )
                (attempt_root / "runtime-checks.json").write_text(
                    json.dumps(
                        {
                            "verifier": {"status": "pass"},
                            "workflow_runtime": {"status": "pass"},
                        }
                    ),
                    encoding="utf-8",
                )
                (attempt_root / "target-integrity.json").write_text(
                    json.dumps({"unchanged": True}), encoding="utf-8"
                )
                (attempt_root / "output-safety-scan.json").write_text(
                    json.dumps({"status": "clear"}), encoding="utf-8"
                )
                manifest = build_artifact_manifest(output, validation)
                (output / "artifact-manifest.json").write_text(
                    json.dumps(manifest), encoding="utf-8"
                )
                if index == 1 and artifact_state == "missing":
                    (output / artifact_path).unlink()
                elif index == 1 and artifact_state == "modified":
                    (output / artifact_path).write_bytes(b"Changed after evaluation.\n")
                normalized = {
                    "criteria": [
                        {
                            "id": "QTS-SEM-006",
                            "status": "fail",
                            "rating": 1,
                            "evidence": ["private evaluator finding"],
                        }
                    ]
                }
                (attempt_root / "judge-result.json").write_text(
                    json.dumps(
                        {
                            "status": "fail",
                            "normalized": normalized,
                            "runs": [{"status": "pass"}, {"status": "pass"}],
                        }
                    ),
                    encoding="utf-8",
                )
                trace_reads_skill = (
                    skill_observation == "observed"
                    if trace_skill_observed is None
                    else trace_skill_observed
                )
                trace_relative = f"attempt-{index:02d}/agent-trace.json"
                trace = {
                    "format": "codex_exec_jsonl",
                    "status": "captured",
                    "turn_completed": True,
                    "turn_failed": False,
                    "commands": [
                        {
                            "successful": True,
                            "skill_files_read": (
                                ["test-case-design"] if trace_reads_skill else []
                            ),
                        }
                    ],
                }
                (attempt_root / "agent-trace.json").write_text(
                    json.dumps(trace), encoding="utf-8"
                )
                (attempt_root / "agent-execution.json").write_text(
                    json.dumps(
                        {
                            "exit_code": 0,
                            "timed_out": False,
                            "trace_status": "captured",
                            "trace_path": trace_relative,
                            "trace_redacted": False,
                            "container_cleanup_status": "succeeded",
                        }
                    ),
                    encoding="utf-8",
                )
                skill_observations = {
                    skill: "unverified"
                    for skill in {
                        row["skill"] for row in scenario["required_artifacts"]
                    }
                }
                skill_observations["test-case-design"] = skill_observation
                attempt_record = {
                    "attempt_id": f"attempt-{index:02d}",
                    "status": "fail",
                    "agent_exit_code": 0,
                    "agent_timed_out": False,
                    "agent_isolation": {"status": "verified"},
                    "workspace_integrity": {"unchanged": True},
                    "runtime_status": {
                        "verifier": "pass",
                        "workflow_runtime": "pass",
                    },
                    "judge_status": "fail",
                    "agent_trace_path": trace_relative,
                    "agent_trace_status": "captured",
                    "saved_result_root": f"attempt-{index:02d}",
                    "saved_output_root": f"attempt-{index:02d}/qa-output",
                    "artifact_manifest": f"attempt-{index:02d}/qa-output/artifact-manifest.json",
                    "skill_use_observation": skill_observations,
                }
                (attempt_root / "attempt.json").write_text(
                    json.dumps(attempt_record), encoding="utf-8"
                )
                attempts.append(attempt_record)
            baseline = {
                "schema_version": 1,
                "run_id": "baseline-run",
                "status": "needs_review",
                "target_revision": DEFAULT_TARGET_REVISION,
                "profile_verification": "verified",
                "evaluator_revision": "1" * 40,
                "skill_revision": "2" * 40,
                "agent_command_template": ["docker", "run", "image"],
                "skill_package_manifest": {"skills": ["test-case-design"]},
                "attempts": attempts,
            }
            baseline_path = run_root / "result.json"
            baseline_path.write_text(json.dumps(baseline), encoding="utf-8")
            judge_validation_path = root / "judge-validation.json"
            judge_validation_path.write_text(
                json.dumps(
                    {
                        "evaluator_revision": "1" * 40,
                        "target_revision": DEFAULT_TARGET_REVISION,
                        "judge_profile_fingerprint": "test-profile",
                    }
                ),
                encoding="utf-8",
            )
            profile = {
                "agent": {
                    "name": "fake",
                    "model": "fake-model",
                    "cli_version": "fake-version",
                    "timeout_seconds": 30,
                },
                "judge": {"timeout_seconds": 30, "command_argv": ["judge"]},
                "verification": {"evidence_path": "isolation.json"},
            }
            artifact_source = run_root / "attempt-01" / "qa-output" / artifact_path
            artifact_bytes = (
                artifact_source.read_bytes()
                if artifact_source.is_file()
                else artifact_text.encode()
            )
            evidence_rows = [
                {
                    "path": f"original-artifacts/attempt-01/{artifact_path}",
                    "sha256": sha256_bytes(artifact_bytes),
                    "quote": artifact_text.strip(),
                },
                {
                    "path": ".agents/skills/test-case-design/SKILL.md",
                    "sha256": sha256_bytes(skill_text.encode()),
                    "quote": skill_text.strip(),
                },
            ]
            analysis_response = json.dumps(
                {
                    "classification": "skill",
                    "skill": "test-case-design",
                    "issue": "The Skill does not make boundary derivation explicit.",
                    "evidence": evidence_rows,
                    "alternative_causes": alternative_causes,
                    "repair_paths": ["SKILL.md"],
                    "repair_rationale": "Clarify the existing boundary analysis step.",
                }
            )
            output_root = root / "improvement-run"
            public_refs = {
                path: b"Fixed public specification text.\n"
                for path in scenario["reference_paths"]
            }

            def fake_create_skill_workspace(_repo, _revision, destination):
                source = destination / "skills" / "test-case-design" / "SKILL.md"
                source.parent.mkdir(parents=True)
                source.write_bytes(skill_text.encode())
                return {
                    "skills": ["test-case-design"],
                    "package_fingerprint": "baseline-package-fingerprint",
                }

            def fake_trace(*_args, **_kwargs):
                return {
                    "final_message": analysis_response,
                    "redacted": False,
                    "format": "synthetic-test",
                    "status": "unwrapped",
                    "execution_status": "completed",
                    "launcher_observations": None,
                    "trace_summary": {"status": "not_captured"},
                }

            independent_plan = {
                "schema_version": 1,
                "status": "ready",
                "cases": [
                    {
                        "suite": "semantic",
                        "skill": "test-case-design",
                        "case_id": "TC-SEM-001",
                        "input_fingerprint": "e" * 64,
                        "dataset_fingerprint": "d" * 64,
                        "evaluator_revision": "1" * 40,
                        "skill_revision": "2" * 40,
                        "baseline_package_fingerprint": "baseline-package-fingerprint",
                        "profile_fingerprint": "test-profile",
                        "agent_command_fingerprint": "a" * 64,
                        "judge_command_fingerprint": "b" * 64,
                        "grader": "fixed_semantic_judge",
                        "judge_profile_fingerprint": "test-profile",
                        "repeat": 2,
                    }
                ],
                "contract_tests": [{"path": "tests/contract.py", "sha256": "c" * 64}],
                "contract_test_execution": "fixed_evaluator_checkout",
                "block_reason": None,
            }

            with (
                patch.object(
                    improve_module,
                    "_judge_verification_map",
                    return_value={
                        "QTS-SEM-006": {
                            "status": "verified",
                            "verified_fixture_ids": ["fixture-006"],
                        }
                    },
                ),
                patch.object(
                    improve_module, "load_execution_profile", return_value=profile
                ),
                patch.object(
                    improve_module, "profile_fingerprint", return_value="test-profile"
                ),
                patch.object(
                    improve_module,
                    "assert_clean_checkout",
                    side_effect=lambda path: (
                        "1" * 40
                        if Path(path) == improve_module.REPO_ROOT
                        else "target-sha"
                    ),
                ),
                patch.object(
                    improve_module,
                    "prepare_run_output_root",
                    side_effect=lambda output, **_kwargs: (
                        Path(output).mkdir(parents=True, exist_ok=True)
                        or Path(output) / "isolation.json"
                    ),
                ),
                patch.object(
                    improve_module, "verify_profile_evidence", return_value=True
                ),
                patch.object(
                    improve_module,
                    "create_skill_workspace",
                    side_effect=fake_create_skill_workspace,
                ),
                patch.object(
                    improve_module,
                    "_freeze_independent_eval_plan",
                    return_value=independent_plan,
                ),
                patch.object(
                    improve_module, "extract_revision_files", return_value=public_refs
                ),
                patch.object(
                    improve_module,
                    "verify_agent_docker_command",
                    return_value={"status": "verified"},
                ),
                patch.object(
                    improve_module,
                    "named_container_command",
                    return_value=(["docker", "run", "image"], []),
                ),
                patch.object(
                    improve_module, "capture_codex_jsonl_trace", side_effect=fake_trace
                ),
                patch.object(
                    improve_module,
                    "run_agent_evaluation",
                    side_effect=AgentEvalError(
                        "synthetic independent evaluation unavailable"
                    ),
                ),
                patch.object(
                    improve_module,
                    "run_command",
                    return_value=SimpleNamespace(
                        stdout="agent response",
                        timed_out=False,
                        exit_code=0,
                        cleanup_status="succeeded",
                    ),
                ) as run_spy,
            ):
                result = improve_module.run_improvements(
                    baseline_result=baseline_path,
                    judge_validation_result=judge_validation_path,
                    target_root=target_root,
                    profile_path=root / "profile.json",
                    output_root=output_root,
                    verifier_image="verifier-image",
                    max_cases=1,
                    max_repairs=1,
                    max_seconds=600,
                    analyze_only=False,
                )
            prompt = (
                run_spy.call_args.kwargs["input_text"] if run_spy.call_count else None
            )
            return result, run_spy.call_count, output_root, prompt

    def test_run_improvements_never_starts_repair_when_alternative_cause_remains(
        self,
    ) -> None:
        result, run_count, _output_root, prompt = self._run_integrated_qts_gate(
            skill_observation="observed",
            alternative_causes=["The Agent may have ignored the Skill instructions."],
        )
        case = result["cases"][0]
        self.assertEqual(run_count, 1)
        self.assertEqual(result["repair_attempts_started"], 0)
        self.assertEqual(case["status"], "review_pending")
        self.assertIn("alternative_causes_remain_unresolved", case["blocked_reason"])
        self.assertNotIn("private evaluator finding", prompt)
        self.assertNotIn('"rating": 1', prompt)

    def test_run_improvements_does_not_start_agent_when_skill_use_is_unverified(
        self,
    ) -> None:
        result, run_count, _output_root, _prompt = self._run_integrated_qts_gate(
            skill_observation="unverified",
            alternative_causes=[],
        )
        case = result["cases"][0]
        self.assertEqual(run_count, 0)
        self.assertEqual(result["repair_attempts_started"], 0)
        self.assertEqual(case["status"], "review_pending")
        self.assertEqual(
            case["blocked_reason"], "eligible_skill_use_not_observed_in_all_attempts"
        )

    def test_run_improvements_rejects_skill_use_not_supported_by_saved_trace(
        self,
    ) -> None:
        result, run_count, _output_root, _prompt = self._run_integrated_qts_gate(
            skill_observation="observed",
            alternative_causes=[],
            trace_skill_observed=False,
        )
        self.assertEqual(run_count, 0)
        self.assertEqual(result["repair_attempts_started"], 0)
        self.assertEqual(result["status"], "review_pending_or_unmet")
        self.assertIn(
            "Skill-use summary does not match trace",
            result["cases"][0]["blocked_reason"],
        )

    def test_run_improvements_preserves_pending_reason_for_missing_or_changed_artifacts(
        self,
    ) -> None:
        for artifact_state in ("missing", "modified"):
            with self.subTest(artifact_state=artifact_state):
                result, run_count, _output_root, _prompt = (
                    self._run_integrated_qts_gate(
                        skill_observation="observed",
                        alternative_causes=[],
                        artifact_state=artifact_state,
                    )
                )
                self.assertEqual(run_count, 0)
                self.assertEqual(result["repair_attempts_started"], 0)
                self.assertEqual(result["cases"][0]["status"], "review_pending")
                self.assertTrue(result["cases"][0]["blocked_reason"])

    def test_independent_baseline_failure_is_persisted_and_blocks_repair(self) -> None:
        result, run_count, _output_root, prompt = self._run_integrated_qts_gate(
            skill_observation="observed",
            alternative_causes=[],
        )
        case = result["cases"][0]
        self.assertEqual(run_count, 1)
        self.assertEqual(result["repair_attempts_started"], 0)
        self.assertEqual(case["status"], "review_pending")
        self.assertEqual(
            case["blocked_reason"],
            "independent_baseline_evaluation_unavailable_or_invalid",
        )
        self.assertEqual(case["independent_regression_plan"]["status"], "ready")
        self.assertEqual(
            case["independent_evaluation_isolation"][
                "repair_agent_received_expected_results"
            ],
            False,
        )
        self.assertEqual(
            case["independent_baseline_results"][0]["reason"],
            "synthetic independent evaluation unavailable",
        )
        self.assertNotIn("TC-SEM-001", prompt)

    def test_agent_workspace_exposes_only_skills_routed_by_selected_cases(self) -> None:
        self.assertEqual(
            visible_skill_names(
                [
                    {"skill": "qa-workflow"},
                    {"skill": "test-case-design"},
                    {"skill": "qa-workflow"},
                ]
            ),
            ["qa-workflow", "test-case-design"],
        )

    def test_skill_use_observation_is_read_from_the_specific_routed_skill(self) -> None:
        attempt = {
            "skill_use_observation": {
                "qa-workflow": "observed",
                "test-case-design": "unverified",
            }
        }
        self.assertEqual(_skill_use_for_attempt(attempt, "qa-workflow"), "observed")
        self.assertEqual(
            _skill_use_for_attempt(attempt, "test-case-design"), "unverified"
        )
        self.assertEqual(_skill_use_for_attempt({}, "qa-workflow"), "unverified")

    def test_reproducible_approved_critical_failure_is_selected(self) -> None:
        attempts = [
            {
                "attempt": {"attempt_id": f"attempt-{index}"},
                "criteria": {"QTS-SEM-006": {"rating": 1, "status": "fail"}},
            }
            for index in (1, 2)
        ]
        verified = {
            "QTS-SEM-006": {"status": "verified", "case_id": "major-violation-006"}
        }
        self.assertEqual(
            _stable_failures(attempts, verified)[0]["criterion"], "QTS-SEM-006"
        )

    def test_judge_jitter_or_unverified_fixture_blocks_repair(self) -> None:
        attempts = [
            {"criteria": {"QTS-SEM-006": {"rating": rating, "status": status}}}
            for rating, status in ((1, "fail"), (2, "needs_review"))
        ]
        self.assertEqual(
            _stable_failures(attempts, {"QTS-SEM-006": {"status": "verified"}}), []
        )
        stable = [
            {"criteria": {"QTS-SEM-006": {"rating": 1, "status": "fail"}}},
            {"criteria": {"QTS-SEM-006": {"rating": 1, "status": "fail"}}},
        ]
        self.assertEqual(_stable_failures(stable, {}), [])

    def test_judge_verification_aggregates_fixture_coverage_per_criterion(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result_path, baseline_fingerprint = _complete_validation_fixture(root)
            original = json.loads(result_path.read_text(encoding="utf-8"))

            def evaluate(value: dict, **expected) -> dict:
                evaluator_expected = expected.pop(
                    "expected_evaluator_revision", "1" * 40
                )
                target_expected = expected.pop(
                    "expected_target_revision", DEFAULT_TARGET_REVISION
                )
                profile_expected = expected.pop(
                    "expected_profile_fingerprint", "test-profile-fingerprint"
                )
                baseline_expected = expected.pop(
                    "expected_baseline_artifact_fingerprint", baseline_fingerprint
                )
                target_root = expected.pop("target_root", None)
                result_path.write_text(json.dumps(value), encoding="utf-8")
                return _judge_verification_map(
                    result_path,
                    expected_evaluator_revision=evaluator_expected,
                    expected_target_revision=target_expected,
                    expected_profile_fingerprint=profile_expected,
                    expected_baseline_artifact_fingerprint=baseline_expected,
                    target_root=target_root,
                    **expected,
                )

            complete = evaluate(json.loads(json.dumps(original)))
            self.assertEqual(complete["QTS-SEM-006"]["status"], "verified")
            self.assertEqual(complete["QTS-SEM-005"]["status"], "verified")
            self.assertEqual(complete["QTS-SEM-008"]["status"], "judge_unverified")
            self.assertIn(
                "missing_major_violation_fixture",
                complete["QTS-SEM-008"]["reason"],
            )

            cases = original["cases"]

            missing_violation = json.loads(json.dumps(original))
            missing_violation["cases"] = [
                row for row in cases if row["case_id"] != "major-violation-006"
            ]
            result = evaluate(missing_violation)
            self.assertEqual(result["QTS-SEM-006"]["status"], "judge_unverified")
            self.assertEqual(result["QTS-SEM-005"]["status"], "verified")

            missing_normal = json.loads(json.dumps(original))
            missing_normal["cases"] = [
                row for row in cases if row["case_id"] != "normal-artifacts"
            ]
            result = evaluate(missing_normal)
            self.assertEqual(result["QTS-SEM-006"]["status"], "judge_unverified")
            self.assertEqual(result["QTS-SEM-001"]["status"], "verified")

            normal_mismatch = json.loads(json.dumps(original))
            next(
                row
                for row in normal_mismatch["cases"]
                if row["case_id"] == "normal-artifacts"
            )["status"] = "label_or_judge_mismatch"
            self.assertEqual(
                evaluate(normal_mismatch)["QTS-SEM-006"]["status"],
                "judge_unverified",
            )

            violation_mismatch = json.loads(json.dumps(original))
            next(
                row
                for row in violation_mismatch["cases"]
                if row["case_id"] == "major-violation-006"
            )["status"] = "label_or_judge_mismatch"
            self.assertEqual(
                evaluate(violation_mismatch)["QTS-SEM-006"]["status"],
                "judge_unverified",
            )

            pending_approval = json.loads(json.dumps(original))
            approval_case = next(
                row
                for row in pending_approval["cases"]
                if row["case_id"] == "major-violation-006"
            )
            approval_case["approval"]["status"] = "review_pending"
            self.assertEqual(
                evaluate(pending_approval)["QTS-SEM-006"]["status"],
                "judge_unverified",
            )

            binding_mismatch = json.loads(json.dumps(original))
            binding_case = next(
                row
                for row in binding_mismatch["cases"]
                if row["case_id"] == "major-violation-006"
            )
            binding_case["approval_binding"]["expected"] = "rating_at_least_3"
            self.assertEqual(
                evaluate(binding_mismatch)["QTS-SEM-006"]["status"],
                "judge_unverified",
            )

            binding_version_mismatch = json.loads(json.dumps(original))
            version_case = next(
                row
                for row in binding_version_mismatch["cases"]
                if row["case_id"] == "major-violation-006"
            )
            version_case["approval_binding"]["binding_version"] = True
            version_case["approval"]["binding"]["binding_version"] = True
            version_case["fixture_fingerprint"] = canonical_fingerprint(
                version_case["approval_binding"]
            )
            self.assertEqual(
                evaluate(binding_version_mismatch)["QTS-SEM-006"]["status"],
                "judge_unverified",
            )

            jitter = json.loads(json.dumps(original))
            normal_case = next(
                row for row in jitter["cases"] if row["case_id"] == "normal-artifacts"
            )
            normal_case["judge_runs"][1]["normalized"]["criteria"][0]["rating"] = 4
            self.assertEqual(
                evaluate(jitter)["QTS-SEM-006"]["status"], "judge_unverified"
            )

            not_evaluable = json.loads(json.dumps(original))
            not_evaluable_case = next(
                row
                for row in not_evaluable["cases"]
                if row["case_id"] == "major-violation-006"
            )
            not_evaluable_case["judge_runs"][0]["normalized"]["criteria"][0] = {
                "id": "QTS-SEM-006",
                "status": "not_evaluable",
                "rating": None,
            }
            not_evaluable_case["judge_runs"][0]["expectation_matched"] = False
            self.assertEqual(
                evaluate(not_evaluable)["QTS-SEM-006"]["status"],
                "judge_unverified",
            )

            execution_error = json.loads(json.dumps(original))
            execution_case = next(
                row
                for row in execution_error["cases"]
                if row["case_id"] == "major-violation-006"
            )
            execution_case["judge_runs"][0]["status"] = "execution_error"
            self.assertEqual(
                evaluate(execution_error)["QTS-SEM-006"]["status"],
                "judge_unverified",
            )

            one_unverified = json.loads(json.dumps(original))
            next(
                row
                for row in one_unverified["cases"]
                if row["case_id"] == "major-violation-006"
            )["status"] = "review_pending"
            result = evaluate(one_unverified)
            attempts = [
                {
                    "attempt": {"attempt_id": f"attempt-{index}"},
                    "criteria": {
                        criterion: {"rating": 1, "status": "fail"}
                        for criterion in ("QTS-SEM-005", "QTS-SEM-006")
                    },
                }
                for index in (1, 2)
            ]
            failures = _stable_failures(attempts, result)
            self.assertEqual([row["criterion"] for row in failures], ["QTS-SEM-005"])

            all_unverified = json.loads(json.dumps(original))
            for row in all_unverified["cases"]:
                row["status"] = "review_pending"
            result = evaluate(all_unverified)
            self.assertTrue(
                all(row["status"] == "judge_unverified" for row in result.values())
            )
            self.assertEqual(_stable_failures(attempts, result), [])

            provenance_mismatch = evaluate(
                json.loads(json.dumps(original)),
                expected_profile_fingerprint="different-profile",
            )
            self.assertTrue(
                all(
                    row["status"] == "judge_unverified"
                    for row in provenance_mismatch.values()
                )
            )
            evaluator_mismatch = evaluate(
                json.loads(json.dumps(original)),
                expected_evaluator_revision="9" * 40,
            )
            self.assertTrue(
                all(
                    row["status"] == "judge_unverified"
                    for row in evaluator_mismatch.values()
                )
            )
            baseline_mismatch = evaluate(
                json.loads(json.dumps(original)),
                expected_baseline_artifact_fingerprint="sha256:" + "0" * 64,
            )
            self.assertEqual(
                baseline_mismatch["QTS-SEM-006"]["status"], "judge_unverified"
            )

            scenario = load_scenario()
            references = {
                relative: b"Fixed specification reference.\n"
                for relative in scenario["reference_paths"]
            }
            with patch.object(
                improve_module, "extract_revision_files", return_value=references
            ):
                normative_match = evaluate(
                    json.loads(json.dumps(original)), target_root=root
                )
            self.assertEqual(normative_match["QTS-SEM-003"]["status"], "verified")
            changed_references = dict(references)
            changed_references["docs/spec/unresolved-specifications.md"] = (
                b"Changed normative specification.\n"
            )
            with patch.object(
                improve_module,
                "extract_revision_files",
                return_value=changed_references,
            ):
                normative_mismatch = evaluate(
                    json.loads(json.dumps(original)), target_root=root
                )
            self.assertEqual(
                normative_mismatch["QTS-SEM-003"]["status"], "judge_unverified"
            )
            self.assertEqual(normative_mismatch["QTS-SEM-005"]["status"], "verified")

            changed_fixture = root / "fixtures" / "major-violation-006" / "qa-output"
            old_approval_case = next(
                row
                for row in original["cases"]
                if row["case_id"] == "major-violation-006"
            )
            self.assertTrue(
                all(
                    run["expectation_matched"] is True
                    for run in old_approval_case["judge_runs"]
                )
            )
            self.assertEqual(old_approval_case["approval"]["binding_status"], "matched")
            old_approval_fingerprint = old_approval_case["approval_binding"][
                "artifact_content_fingerprint"
            ]
            artifact_index = json.loads(
                (changed_fixture / "artifact-index.json").read_text(encoding="utf-8")
            )
            changed_artifact = changed_fixture / artifact_index["artifacts"][0]["path"]
            changed_artifact.write_text(
                changed_artifact.read_text(encoding="utf-8")
                + "Changed after approval.\n",
                encoding="utf-8",
            )
            result = evaluate(json.loads(json.dumps(original)))
            self.assertEqual(result["QTS-SEM-006"]["status"], "judge_unverified")
            self.assertEqual(result["QTS-SEM-005"]["status"], "verified")
            self.assertNotEqual(
                old_approval_fingerprint,
                _artifact_content_fingerprint(changed_fixture),
            )
            failures = _stable_failures(attempts, result)
            self.assertEqual([row["criterion"] for row in failures], ["QTS-SEM-005"])

    def test_repair_diff_accepts_only_requested_skill_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            skills = Path(temporary) / ".agents" / "skills"
            skill = skills / "qa-workflow"
            skill.mkdir(parents=True)
            source = skill / "SKILL.md"
            source.write_text("before\n", encoding="utf-8")
            before = {"qa-workflow/SKILL.md": "old"}
            source.write_text("after\n", encoding="utf-8")
            changes, _ = _validate_repair_diff(
                before, skills, "qa-workflow", {"SKILL.md"}
            )
        self.assertEqual(changes[0]["path"], "SKILL.md")

    def test_repair_diff_rejects_unrequested_path(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            skills = Path(temporary)
            skill = skills / "qa-workflow"
            skill.mkdir()
            (skill / "SKILL.md").write_text("changed", encoding="utf-8")
            with self.assertRaises(AgentEvalError):
                _validate_repair_diff(
                    {"qa-workflow/SKILL.md": "old"},
                    skills,
                    "qa-workflow",
                    {"references/guide.md"},
                )


if __name__ == "__main__":
    unittest.main()
