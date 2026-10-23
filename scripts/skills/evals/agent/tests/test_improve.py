from __future__ import annotations

import json
import tempfile
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
    _judge_verification_map,
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
                "agent": {"name": "fake", "model": "fake-model", "timeout_seconds": 30},
                "judge": {"timeout_seconds": 30},
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
                    max_seconds=120,
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
