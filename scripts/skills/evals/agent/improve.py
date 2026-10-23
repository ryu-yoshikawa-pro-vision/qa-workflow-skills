from __future__ import annotations

import argparse
import difflib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import zipfile
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

from .common import (
    AgentEvalError,
    atomic_write_bytes,
    atomic_write_json,
    canonical_fingerprint,
    capture_codex_jsonl_trace,
    ensure_within,
    prepare_run_output_root,
    safe_relative_path,
    sanitize_diagnostic,
    sha256_bytes,
)
from .executor import AgentExecutionError, run_command
from .judge_validation import (
    _artifact_content_fingerprint,
    _expected_matches,
    load_fixture_catalogue,
)
from .prompt_builder import build_analysis_prompt, build_repair_prompt
from .qa_training_store import (
    build_artifact_manifest,
    load_scenario,
    validate_artifact_index,
)
from .run import _has_secret_command_argument
from .run import run as run_agent_evaluation
from .target_workspace import DEFAULT_TARGET_REVISION, extract_revision_files
from .tools.codex_docker_launcher import launcher_argv
from .workspace import (
    assert_clean_checkout,
    create_skill_workspace,
    create_skill_workspace_from_root,
    load_execution_profile,
    named_container_command,
    profile_fingerprint,
    verify_agent_docker_command,
    verify_profile_evidence,
    verify_repair_docker_command,
)

REPO_ROOT = Path(__file__).resolve().parents[4]
_CRITERION_SKILLS = {
    "QTS-SEM-001": {"qa-workflow"},
    "QTS-SEM-002": {"qa-workflow"},
    "QTS-SEM-003": {"spec-analysis", "test-requirement-design"},
    "QTS-SEM-004": {"test-condition-design", "test-case-design"},
    "QTS-SEM-005": {"test-condition-design", "test-case-design"},
    "QTS-SEM-006": {"test-case-design"},
    "QTS-SEM-007": {"test-condition-design", "test-case-design"},
    "QTS-SEM-008": {
        "test-requirement-design",
        "test-condition-design",
        "test-case-design",
    },
    "QTS-SEM-009": {"coverage-analysis", "test-case-design"},
    "QTS-SEM-010": {"test-requirement-design", "test-case-design"},
}
_SECRET_RE = re.compile(
    r"(?i)\b(?:Bearer\s+\S{12,}|sk-[A-Za-z0-9_-]{16,}|gh[pousr]_[A-Za-z0-9]{20,}|(?:api[_-]?key|access[_-]?token|password)\s*[:=]\s*\S+)"
)
_MAX_ANALYSIS_SOURCE_BYTES = 250_000


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AgentEvalError(
            f"saved evaluation record is unreadable: {path.name}"
        ) from exc
    if not isinstance(value, dict):
        raise AgentEvalError(f"saved evaluation record must be an object: {path.name}")
    return value


def _judge_verification_map(
    path: Path,
    *,
    expected_evaluator_revision: str | None = None,
    expected_target_revision: str | None = None,
    expected_profile_fingerprint: str | None = None,
    expected_baseline_artifact_fingerprint: str | None = None,
    target_root: Path | None = None,
) -> dict[str, dict[str, Any]]:
    value = _load_json(path)
    if value.get("dataset_revision") is None or not isinstance(
        value.get("cases"), list
    ):
        raise AgentEvalError("Judge validation result schema is invalid")
    catalogue = load_fixture_catalogue()
    definitions = catalogue["cases"]
    criteria = sorted(
        {criterion for row in definitions for criterion in row["criteria"]}
    )
    result = {
        criterion: {"status": "judge_unverified", "reason": "not_checked"}
        for criterion in criteria
    }

    def unverified_all(reason: str) -> dict[str, dict[str, Any]]:
        return {
            criterion: {"status": "judge_unverified", "reason": reason}
            for criterion in criteria
        }

    if value.get("dataset_revision") != catalogue["dataset_revision"] or value.get(
        "fixture_catalogue_fingerprint"
    ) != canonical_fingerprint(catalogue):
        return unverified_all("fixture_catalogue_mismatch")
    if value.get("target_revision") != DEFAULT_TARGET_REVISION:
        return unverified_all("target_revision_mismatch")
    if (
        expected_evaluator_revision is not None
        and value.get("evaluator_revision") != expected_evaluator_revision
    ):
        return unverified_all("evaluator_revision_mismatch")
    if (
        expected_target_revision is not None
        and value.get("target_revision") != expected_target_revision
    ):
        return unverified_all("target_revision_mismatch")
    if (
        expected_profile_fingerprint is not None
        and value.get("judge_profile_fingerprint") != expected_profile_fingerprint
    ):
        return unverified_all("judge_profile_mismatch")
    if not isinstance(value.get("evaluator_revision"), str) or not isinstance(
        value.get("judge_profile_fingerprint"), str
    ):
        return unverified_all("missing_provenance")
    repeat = value.get("repeat")
    if isinstance(repeat, bool) or not isinstance(repeat, int) or repeat < 2:
        return unverified_all("repeat_policy_not_satisfied")

    scenario = load_scenario()
    reference_hashes: dict[str, str] | None = None
    if target_root is not None:
        references = extract_revision_files(
            source_root=target_root,
            revision=DEFAULT_TARGET_REVISION,
            paths=scenario["reference_paths"],
        )
        reference_hashes = {
            relative: sha256_bytes(references[relative])
            for relative in sorted(scenario["reference_paths"])
        }

    case_rows: dict[str, dict[str, Any]] = {}
    duplicate_ids: set[str] = set()
    for row in value["cases"]:
        if not isinstance(row, dict) or not isinstance(row.get("case_id"), str):
            continue
        case_id = row["case_id"]
        if case_id in case_rows:
            duplicate_ids.add(case_id)
        case_rows[case_id] = row
    for case_id in duplicate_ids:
        case_rows.pop(case_id, None)

    def case_verified(definition: dict[str, Any]) -> tuple[bool, str | None]:
        case_id = definition["id"]
        case = case_rows.get(case_id)
        if case is None:
            return False, f"missing_fixture:{case_id}"
        if (
            case.get("status") != "verified"
            or case.get("criteria") != definition["criteria"]
            or case.get("expected") != definition["expected"]
        ):
            return False, f"fixture_not_verified:{case_id}"
        approval = case.get("approval")
        binding = case.get("approval_binding")
        if (
            not isinstance(approval, dict)
            or approval.get("status") != "approved"
            or approval.get("binding_status") != "matched"
            or not isinstance(binding, dict)
            or not all(
                isinstance(approval.get(field), str) and approval[field].strip()
                for field in ("reviewer", "approved_at", "evidence")
            )
        ):
            return False, f"approval_unverified:{case_id}"
        try:
            approval_binding_matches = canonical_fingerprint(
                approval.get("binding")
            ) == canonical_fingerprint(binding)
        except (TypeError, ValueError):
            approval_binding_matches = False
        if not approval_binding_matches:
            return False, f"approval_unverified:{case_id}"
        if (
            case.get("fixture_content_integrity_status") != "verified"
            or isinstance(binding.get("binding_version"), bool)
            or not isinstance(binding.get("binding_version"), int)
            or binding.get("binding_version") != 1
            or binding.get("fixture_id") != case_id
            or binding.get("dataset_revision") != catalogue["dataset_revision"]
            or binding.get("fixture_definition_fingerprint")
            != canonical_fingerprint(definition)
            or binding.get("criteria") != definition["criteria"]
            or binding.get("expected") != definition["expected"]
            or binding.get("normative_revision") != value.get("target_revision")
            or binding.get("normative_content_fingerprint")
            != canonical_fingerprint(binding.get("normative_reference_fingerprints"))
            or case.get("fixture_fingerprint") != canonical_fingerprint(binding)
        ):
            return False, f"fixture_binding_mismatch:{case_id}"
        if (
            expected_baseline_artifact_fingerprint is not None
            and binding.get("baseline_artifact_fingerprint")
            != expected_baseline_artifact_fingerprint
        ):
            return False, f"baseline_artifacts_changed:{case_id}"
        if reference_hashes is not None:
            expected_references = {
                relative: reference_hashes[relative]
                for relative in sorted(set(definition["references"]))
                if relative in reference_hashes
            }
            if (
                set(definition["references"]) - set(expected_references)
                or binding.get("normative_reference_fingerprints")
                != expected_references
            ):
                return False, f"normative_reference_mismatch:{case_id}"
        fixture_output = (
            Path(path).resolve().parent / "fixtures" / case_id / "qa-output"
        )
        try:
            current_fingerprint = _artifact_content_fingerprint(fixture_output)
            if binding.get("artifact_content_fingerprint") != current_fingerprint:
                return False, f"fixture_artifacts_changed:{case_id}"
            manifest_path = fixture_output / "artifact-manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            validation = validate_artifact_index(fixture_output, scenario)
            if manifest != build_artifact_manifest(fixture_output, validation):
                return False, f"fixture_manifest_stale:{case_id}"
        except (OSError, ValueError, AgentEvalError):
            return False, f"fixture_artifacts_unavailable:{case_id}"
        judge_runs = case.get("judge_runs")
        if not isinstance(judge_runs, list) or len(judge_runs) != repeat:
            return False, f"fixture_repeat_incomplete:{case_id}"
        signatures = set()
        for judge_run in judge_runs:
            if not isinstance(judge_run, dict) or judge_run.get("status") != "pass":
                return False, f"fixture_run_error:{case_id}"
            normalized = judge_run.get("normalized")
            normalized_criteria = (
                normalized.get("criteria") if isinstance(normalized, dict) else None
            )
            if (
                not isinstance(normalized_criteria, list)
                or [
                    item.get("id")
                    for item in normalized_criteria
                    if isinstance(item, dict)
                ]
                != definition["criteria"]
                or judge_run.get("prompt_sha256")
                != binding.get("judge_input_fingerprint")
                or judge_run.get("expectation_matched") is not True
                or not _expected_matches(definition, normalized)
            ):
                return False, f"fixture_expectation_mismatch:{case_id}"
            signatures.add(
                canonical_fingerprint(
                    [
                        {
                            "id": item.get("id"),
                            "status": item.get("status"),
                            "rating": item.get("rating"),
                        }
                        for item in normalized_criteria
                    ]
                )
            )
        if len(signatures) != 1:
            return False, f"fixture_judge_jitter:{case_id}"
        return True, None

    for criterion in criteria:
        required = [row for row in definitions if criterion in row["criteria"]]
        normal_cases = [
            row for row in required if row["expected"] == "rating_at_least_3"
        ]
        violation_cases = [row for row in required if row["expected"] == "rating_1"]
        required_ids = [row["id"] for row in required]
        reasons: list[str] = []
        if not normal_cases:
            reasons.append("missing_normal_fixture")
        if not violation_cases:
            reasons.append("missing_major_violation_fixture")
        if not reasons:
            for definition in required:
                passed, reason = case_verified(definition)
                if not passed and reason is not None:
                    reasons.append(reason)
        if reasons:
            result[criterion] = {
                "status": "judge_unverified",
                "reason": ";".join(reasons),
                "required_fixture_ids": required_ids,
                "verified_fixture_ids": [],
            }
        else:
            result[criterion] = {
                "status": "verified",
                "required_fixture_ids": required_ids,
                "verified_fixture_ids": required_ids,
            }
    return result


def _resolve_run_path(run_root: Path, relative: str) -> Path:
    try:
        safe = safe_relative_path(relative)
    except (AgentEvalError, TypeError) as exc:
        raise AgentEvalError("saved evaluation path is unsafe") from exc
    root = run_root.resolve(strict=True)
    candidate = run_root
    for component in safe.parts:
        candidate = candidate / component
        if candidate.is_symlink():
            raise AgentEvalError("saved evaluation path contains a symlink")
    try:
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(root)
    except (OSError, ValueError) as exc:
        raise AgentEvalError(
            "saved evaluation path is missing or escapes its run"
        ) from exc
    return resolved


def _attempt_data(run: dict[str, Any], run_root: Path) -> list[dict[str, Any]]:
    if not isinstance(run.get("attempts"), list) or len(run["attempts"]) < 2:
        raise AgentEvalError(
            "Skill repair requires at least two independent baseline attempts"
        )
    collected = []
    scenario = load_scenario()
    attempt_ids: set[str] = set()
    result_roots: set[Path] = set()
    for attempt in run["attempts"]:
        if not isinstance(attempt, dict):
            raise AgentEvalError("baseline attempt record is invalid")
        relative = attempt.get("saved_result_root")
        if not isinstance(relative, str):
            raise AgentEvalError("baseline attempt has no preserved run root")
        root = _resolve_run_path(run_root, relative)
        saved_attempt = _load_json(root / "attempt.json")
        if canonical_fingerprint(saved_attempt) != canonical_fingerprint(attempt):
            raise AgentEvalError(
                "baseline attempt summary differs from its saved record"
            )
        attempt_id = attempt.get("attempt_id")
        if (
            not isinstance(attempt_id, str)
            or not attempt_id
            or attempt_id in attempt_ids
        ):
            raise AgentEvalError("baseline attempts are not independent")
        if root in result_roots:
            raise AgentEvalError("baseline attempts reuse a saved result directory")
        attempt_ids.add(attempt_id)
        result_roots.add(root)
        judge = _load_json(root / "judge-result.json")
        validation = _load_json(root / "artifact-validation.json")
        runtime = _load_json(root / "runtime-checks.json")
        integrity = _load_json(root / "target-integrity.json")
        if (
            attempt.get("status") not in {"pass", "fail", "needs_review"}
            or validation.get("status") != "pass"
        ):
            raise AgentEvalError(
                "baseline has runner, evidence, or artifact-contract errors"
            )
        agent_isolation = attempt.get("agent_isolation")
        agent_exit_code = attempt.get("agent_exit_code")
        workspace_integrity = attempt.get("workspace_integrity")
        if (
            not isinstance(agent_isolation, dict)
            or agent_isolation.get("status") != "verified"
            or isinstance(agent_exit_code, bool)
            or agent_exit_code != 0
            or attempt.get("agent_timed_out") is not False
            or not isinstance(workspace_integrity, dict)
            or workspace_integrity.get("unchanged") is not True
        ):
            raise AgentEvalError(
                "baseline Agent execution or isolation evidence is incomplete"
            )
        agent_execution = _load_json(root / "agent-execution.json")
        trace_relative = attempt.get("agent_trace_path")
        if (
            attempt.get("agent_trace_status") != "captured"
            or not isinstance(trace_relative, str)
            or agent_execution.get("exit_code") != agent_exit_code
            or agent_execution.get("timed_out") is not False
            or agent_execution.get("trace_status") != "captured"
            or agent_execution.get("trace_path") != trace_relative
            or agent_execution.get("trace_redacted") is not False
            or agent_execution.get("container_cleanup_status") != "succeeded"
        ):
            raise AgentEvalError("baseline Agent trace evidence is incomplete")
        trace_path = _resolve_run_path(run_root, trace_relative)
        if trace_path.parent != root or trace_path.name != "agent-trace.json":
            raise AgentEvalError("baseline Agent trace path does not match its attempt")
        trace = _load_json(trace_path)
        trace_commands = trace.get("commands")
        if (
            trace.get("format") != "codex_exec_jsonl"
            or trace.get("status") != "captured"
            or trace.get("turn_completed") is not True
            or trace.get("turn_failed") is not False
            or not isinstance(trace_commands, list)
        ):
            raise AgentEvalError("baseline Agent trace is not a complete execution")
        runtime_verifier = runtime.get("verifier")
        workflow_runtime = runtime.get("workflow_runtime")
        if (
            not isinstance(runtime_verifier, dict)
            or runtime_verifier.get("status") != "pass"
            or not isinstance(workflow_runtime, dict)
            or workflow_runtime.get("status") != "pass"
        ):
            raise AgentEvalError(
                "baseline has runtime evidence that is missing, failing, or unverified"
            )
        if attempt.get("runtime_status") != {
            "verifier": "pass",
            "workflow_runtime": "pass",
        }:
            raise AgentEvalError(
                "baseline runtime status summary does not match its evidence"
            )
        if not integrity.get("unchanged"):
            raise AgentEvalError("baseline target workspace integrity check failed")
        safety = _load_json(root / "output-safety-scan.json")
        if safety.get("status") != "clear":
            raise AgentEvalError("baseline output safety evidence is incomplete")
        saved_output = attempt.get("saved_output_root")
        manifest_relative = attempt.get("artifact_manifest")
        if not isinstance(saved_output, str) or not isinstance(manifest_relative, str):
            raise AgentEvalError("baseline attempt has no preserved artifact root")
        output_root = _resolve_run_path(run_root, saved_output)
        current_validation = validate_artifact_index(output_root, scenario)
        if current_validation.get("status") != "pass" or canonical_fingerprint(
            current_validation
        ) != canonical_fingerprint(validation):
            raise AgentEvalError("baseline artifacts changed after evaluation")
        current_manifest = build_artifact_manifest(output_root, current_validation)
        stored_manifest_path = _resolve_run_path(run_root, manifest_relative)
        stored_manifest = _load_json(stored_manifest_path)
        if current_manifest != stored_manifest or any(
            row.get("classification") == "unsafe_symlink"
            for row in current_manifest.get("files", [])
        ):
            raise AgentEvalError("baseline artifact manifest is stale or unsafe")
        skill_observations = attempt.get("skill_use_observation")
        if not isinstance(skill_observations, dict):
            raise AgentEvalError("baseline Skill-use observations are missing")
        routed_skills = {
            row.get("skill")
            for row in current_validation.get("routing", [])
            if isinstance(row, dict) and row.get("status") == "executed"
        }
        trace_skills = {
            skill
            for command in trace_commands
            if isinstance(command, dict) and command.get("successful") is True
            for skill in command.get("skill_files_read", [])
            if isinstance(skill, str)
        }
        expected_skills = {row["skill"] for row in scenario["required_artifacts"]}
        if set(skill_observations) != expected_skills or any(
            skill_observations[skill]
            != ("observed" if skill in routed_skills & trace_skills else "unverified")
            for skill in expected_skills
        ):
            raise AgentEvalError(
                "baseline Skill-use summary does not match trace and routing evidence"
            )
        normalized = judge.get("normalized")
        if (
            not isinstance(normalized, dict)
            or not isinstance(normalized.get("criteria"), list)
            or any(not isinstance(item, dict) for item in normalized["criteria"])
        ):
            raise AgentEvalError("baseline has no normalized fixed-Judge criteria")
        judge_runs = judge.get("runs")
        if (
            attempt.get("judge_status") != judge.get("status")
            or not isinstance(judge_runs, list)
            or len(judge_runs) < 2
            or any(
                not isinstance(row, dict) or row.get("status") != "pass"
                for row in judge_runs
            )
        ):
            raise AgentEvalError("baseline Judge execution evidence is incomplete")
        criteria = {
            item.get("id"): item
            for item in normalized["criteria"]
            if isinstance(item, dict)
        }
        collected.append(
            {
                "attempt": attempt,
                "root": root,
                "criteria": criteria,
                "artifacts": validation.get("artifacts", []),
                "artifact_validation": validation,
                "output_root": output_root,
                "artifact_manifest": current_manifest,
                "skill_use_observation": attempt.get(
                    "skill_use_observation", "unverified"
                ),
                "agent_output_root": attempt.get("saved_output_root"),
            }
        )
    return collected


def _stable_failures(
    attempts: list[dict[str, Any]], verified: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    if not attempts:
        return []
    common = set(attempts[0]["criteria"])
    for attempt in attempts[1:]:
        common &= set(attempt["criteria"])
    failures = []
    for criterion in sorted(common):
        if (
            criterion not in _CRITERION_SKILLS
            or verified.get(criterion, {}).get("status") != "verified"
        ):
            continue
        rows = [attempt["criteria"][criterion] for attempt in attempts]
        if all(row.get("rating") == 1 and row.get("status") == "fail" for row in rows):
            failures.append(
                {
                    "criterion": criterion,
                    "verified_fixture": verified[criterion],
                    "observations": [
                        {
                            "attempt_id": attempt["attempt"].get("attempt_id"),
                            "rating": row.get("rating"),
                            "status": row.get("status"),
                            "evidence": row.get("evidence", []),
                        }
                        for attempt, row in zip(attempts, rows, strict=True)
                    ],
                }
            )
    return failures


def _deterministic_grade_snapshot(
    grade: dict[str, Any], *, skill: str, eval_id: str
) -> dict[str, str]:
    assertions = grade.get("assertions")
    summary = grade.get("summary")
    if (
        grade.get("skill") != skill
        or grade.get("eval_id") != eval_id
        or grade.get("status") not in {"pass", "fail"}
        or not isinstance(assertions, list)
        or not assertions
        or not isinstance(summary, dict)
    ):
        raise AgentEvalError("fixed deterministic grade schema is invalid")
    scores = {"fail": 0, "warning": 1, "pass": 2}
    snapshot: dict[str, str] = {}
    for row in assertions:
        if (
            not isinstance(row, dict)
            or not isinstance(row.get("id"), str)
            or not row["id"]
            or row.get("status") not in scores
            or row.get("severity") not in {"error", "warning"}
            or not isinstance(row.get("message"), str)
            or row["id"] in snapshot
        ):
            raise AgentEvalError("fixed deterministic assertion record is invalid")
        snapshot[row["id"]] = row["status"]
    counts = {
        "errors": sum(status == "fail" for status in snapshot.values()),
        "warnings": sum(status == "warning" for status in snapshot.values()),
        "passed": sum(status == "pass" for status in snapshot.values()),
        "total": len(snapshot),
    }
    if any(summary.get(key) != value for key, value in counts.items()):
        raise AgentEvalError("fixed deterministic grade summary is inconsistent")
    expected_rate = counts["passed"] / counts["total"]
    if summary.get("assertion_pass_rate") != expected_rate:
        raise AgentEvalError("fixed deterministic grade rate is inconsistent")
    expected_status = "fail" if counts["errors"] else "pass"
    if grade["status"] != expected_status:
        raise AgentEvalError("fixed deterministic grade status is inconsistent")
    return snapshot


def _deterministic_attempt_data(
    run: dict[str, Any],
    run_root: Path,
    *,
    runtime_source_root: Path,
    expected_package_fingerprint: str | None = None,
    expected_candidate_status: str = "git_commit",
) -> dict[str, Any]:
    from scripts.skills.evals.deterministic.run import grade as deterministic_grade

    from .run import _dataset_fingerprint, _load_deterministic_cases

    evaluator = run.get("evaluator")
    package = run.get("skill_package")
    template = run.get("agent_command_template")
    attempts = run.get("attempts")
    if (
        run.get("suite") != "deterministic"
        or run.get("target_revision") is not None
        or run.get("evidence_basis") not in {None, "deterministic_only"}
        or run.get("judge_validation_result") is not None
        or run.get("profile_verification") != "verified"
        or run.get("workspace_cleanup") != "succeeded"
        or run.get("skill_candidate_revision_status") != expected_candidate_status
        or run.get("repeat") != 2
        or run.get("cases_requested") != 1
        or not isinstance(evaluator, dict)
        or not isinstance(evaluator.get("revision"), str)
        or not isinstance(run.get("skill_revision"), str)
        or not isinstance(package, dict)
        or not isinstance(package.get("skills"), list)
        or any(not isinstance(name, str) or not name for name in package["skills"])
        or len(set(package["skills"])) != len(package["skills"])
        or not isinstance(package.get("package_fingerprint"), str)
        or (
            expected_package_fingerprint is not None
            and package["package_fingerprint"] != expected_package_fingerprint
        )
        or not isinstance(run.get("profile_fingerprint"), str)
        or not isinstance(run.get("agent_command_fingerprint"), str)
        or not isinstance(run.get("judge_command_fingerprint"), str)
        or not isinstance(template, list)
        or not template
        or run.get("agent_command_saved") is not True
        or _has_secret_command_argument(template)
        or run.get("agent_command_fingerprint") != canonical_fingerprint(template)
        or not isinstance(attempts, list)
        or len(attempts) != 2
    ):
        raise AgentEvalError("deterministic baseline run provenance is incomplete")

    identities: set[tuple[str, str, int]] = set()
    attempt_ids: set[str] = set()
    attempt_roots: set[Path] = set()
    collected: list[dict[str, Any]] = []
    skill: str | None = None
    eval_id: str | None = None
    for attempt in attempts:
        if not isinstance(attempt, dict):
            raise AgentEvalError("deterministic attempt record is invalid")
        repeat = attempt.get("repeat")
        current_skill = attempt.get("skill")
        current_eval_id = attempt.get("eval_id")
        attempt_id = attempt.get("attempt_id")
        if (
            attempt.get("suite") != "deterministic"
            or not isinstance(current_skill, str)
            or not isinstance(current_eval_id, str)
            or isinstance(repeat, bool)
            or repeat not in {1, 2}
            or not isinstance(attempt_id, str)
            or not attempt_id
            or attempt_id in attempt_ids
            or (skill is not None and skill != current_skill)
            or (eval_id is not None and eval_id != current_eval_id)
            or "judge" in attempt
        ):
            raise AgentEvalError(
                "deterministic run contains mixed, duplicate, or unsupported attempts"
            )
        skill = current_skill
        eval_id = current_eval_id
        attempt_ids.add(attempt_id)
        identity = (current_skill, current_eval_id, repeat)
        if identity in identities:
            raise AgentEvalError("deterministic attempts are not independent")
        identities.add(identity)

        output = attempt.get("output")
        grade_ref = attempt.get("grade")
        trace = attempt.get("agent_trace")
        execution = attempt.get("agent_execution")
        isolation = attempt.get("agent_isolation")
        command = attempt.get("agent_command")
        if (
            attempt.get("status") not in {"pass", "fail"}
            or attempt.get("skill_use_observation") != "observed"
            or not isinstance(output, dict)
            or not isinstance(grade_ref, dict)
            or not isinstance(trace, dict)
            or trace.get("status") != "captured"
            or trace.get("redacted") is not False
            or trace.get("path") != "agent-trace.json"
            or not isinstance(execution, dict)
            or isinstance(execution.get("exit_code"), bool)
            or execution.get("exit_code") != 0
            or execution.get("timed_out") is not False
            or execution.get("container_cleanup_status") != "succeeded"
            or not isinstance(isolation, dict)
            or isolation.get("status") != "verified"
            or not isinstance(command, dict)
            or not isinstance(command.get("argv"), list)
            or command.get("fingerprint") != canonical_fingerprint(command.get("argv"))
            or _has_secret_command_argument(command.get("argv", []))
        ):
            raise AgentEvalError(
                "deterministic Agent execution, Skill-use, or isolation evidence "
                "is incomplete"
            )

        output_relative = output.get("path")
        grade_relative = grade_ref.get("path")
        expected_case_root = PurePosixPath(
            "deterministic", current_skill, current_eval_id, f"attempt-{repeat:02d}"
        )
        if (
            output_relative
            != (expected_case_root / "agent-output" / "output.md").as_posix()
            or grade_relative != (expected_case_root / "grade.json").as_posix()
        ):
            raise AgentEvalError("deterministic output paths do not match the attempt")
        output_path = _resolve_run_path(run_root, output_relative)
        grade_path = _resolve_run_path(run_root, grade_relative)
        output_bytes = output_path.read_bytes()
        grade_bytes = grade_path.read_bytes()
        if sha256_bytes(output_bytes) != output.get("sha256") or sha256_bytes(
            grade_bytes
        ) != grade_ref.get("sha256"):
            raise AgentEvalError(
                "deterministic output or grade changed after evaluation"
            )
        attempt_root = grade_path.parent.resolve()
        if attempt_root in attempt_roots:
            raise AgentEvalError("deterministic attempts reuse an output directory")
        attempt_roots.add(attempt_root)

        trace_path = _resolve_run_path(
            run_root, (expected_case_root / "agent-trace.json").as_posix()
        )
        trace_bytes = trace_path.read_bytes()
        if sha256_bytes(trace_bytes) != trace.get("sha256"):
            raise AgentEvalError("deterministic Agent trace changed after evaluation")
        trace_value = _load_json(trace_path)
        trace_commands = trace_value.get("commands")
        if (
            trace_value.get("status") != "captured"
            or trace_value.get("turn_completed") is not True
            or trace_value.get("turn_failed") is not False
            or not isinstance(trace_commands, list)
            or not any(
                isinstance(row, dict)
                and row.get("successful") is True
                and isinstance(row.get("skill_files_read"), list)
                and current_skill in row.get("skill_files_read", [])
                for row in trace_commands
            )
        ):
            raise AgentEvalError("deterministic trace does not prove Skill use")
        try:
            saved_grade = json.loads(grade_bytes)
        except json.JSONDecodeError as exc:
            raise AgentEvalError("deterministic grade is not valid JSON") from exc
        if not isinstance(saved_grade, dict):
            raise AgentEvalError("deterministic grade must be an object")
        snapshot = _deterministic_grade_snapshot(
            saved_grade, skill=current_skill, eval_id=current_eval_id
        )
        if saved_grade.get("status") != attempt.get("status"):
            raise AgentEvalError("deterministic attempt and grade statuses differ")
        try:
            recomputed = deterministic_grade(
                current_skill,
                current_eval_id,
                output_path,
                runtime_source_root=runtime_source_root,
            )
        except Exception as exc:
            raise AgentEvalError(
                "fixed deterministic grader failed on saved output"
            ) from exc
        if canonical_fingerprint(recomputed) != canonical_fingerprint(saved_grade):
            raise AgentEvalError(
                "saved deterministic grade does not match the fixed grader output"
            )
        collected.append(
            {
                "attempt": attempt,
                "root": attempt_root,
                "output_path": output_path,
                "grade_path": grade_path,
                "grade": saved_grade,
                "snapshot": snapshot,
                "trace_path": trace_path,
            }
        )

    if (
        skill is None
        or eval_id is None
        or {row["attempt"]["repeat"] for row in collected} != {1, 2}
    ):
        raise AgentEvalError(
            "deterministic baseline must contain two repeated attempts"
        )
    if skill not in package["skills"]:
        raise AgentEvalError("deterministic baseline package omits the target Skill")
    cases = _load_deterministic_cases(skill, eval_id)
    if len(cases) != 1:
        raise AgentEvalError("fixed deterministic case is missing or ambiguous")
    case = cases[0]
    input_fingerprint = sha256_bytes(case["input"].encode("utf-8"))
    dataset_fingerprint = _dataset_fingerprint(case["fingerprint_files"])
    if run.get("dataset_fingerprint") != dataset_fingerprint or any(
        row["attempt"].get("input_fingerprint") != input_fingerprint
        for row in collected
    ):
        raise AgentEvalError("deterministic input or dataset fingerprint changed")
    if collected[0]["snapshot"] != collected[1]["snapshot"]:
        raise AgentEvalError("deterministic repeated grades are unstable")
    expected_run_status = (
        "needs_review_or_fail"
        if any(row["attempt"]["status"] == "fail" for row in collected)
        else "pass"
    )
    if run.get("status") != expected_run_status:
        raise AgentEvalError("deterministic run summary status is inconsistent")
    expected_summary = {
        status: sum(row["attempt"]["status"] == status for row in collected)
        for status in sorted({row["attempt"]["status"] for row in collected})
    }
    if run.get("summary") != expected_summary or run.get("exit_code") != (
        1 if expected_run_status == "needs_review_or_fail" else 0
    ):
        raise AgentEvalError(
            "deterministic run summary counts or exit code are inconsistent"
        )
    failures = sorted(
        assertion_id
        for assertion_id, status in collected[0]["snapshot"].items()
        if status == "fail"
    )
    return {
        "skill": skill,
        "eval_id": eval_id,
        "case": case,
        "input_fingerprint": input_fingerprint,
        "dataset_fingerprint": dataset_fingerprint,
        "attempts": collected,
        "failed_assertion_ids": failures,
    }


def _prepare_deterministic_analysis_workspace(
    *,
    workspace: Path,
    failure: dict[str, Any],
    package_root: Path,
) -> tuple[dict[str, dict[str, Any]], str, list[dict[str, str]]]:
    skill = failure["skill"]
    source_map: dict[str, dict[str, Any]] = {}
    prompt_parts: list[str] = []
    manifest: list[dict[str, str]] = []
    total_bytes = 0
    input_path = failure["case"].get("input_path")
    if not isinstance(input_path, Path) or input_path.is_symlink():
        raise AgentEvalError("deterministic public input is unavailable or unsafe")
    try:
        input_relative = input_path.relative_to(REPO_ROOT).as_posix()
    except ValueError as exc:
        raise AgentEvalError(
            "deterministic public input is outside the Evaluator"
        ) from exc
    input_bytes = _safe_child_file(REPO_ROOT, input_relative).read_bytes()
    if sha256_bytes(input_bytes) != failure["input_fingerprint"]:
        raise AgentEvalError("deterministic public input changed after grading")
    total_bytes = _add_analysis_source(
        workspace=workspace,
        source_path="public-input/eval-input.md",
        data=input_bytes,
        kind="public_input",
        sources=source_map,
        prompt_parts=prompt_parts,
        total_bytes=total_bytes,
    )
    manifest.append(
        {
            "path": "public-input/eval-input.md",
            "sha256": source_map["public-input/eval-input.md"]["sha256"],
        }
    )
    for index, attempt in enumerate(failure["attempts"], start=1):
        output_bytes = attempt["output_path"].read_bytes()
        if sha256_bytes(output_bytes) != attempt["attempt"].get("output", {}).get(
            "sha256"
        ):
            raise AgentEvalError(
                "original deterministic output changed before analysis"
            )
        grade_bytes = attempt["grade_path"].read_bytes()
        if sha256_bytes(grade_bytes) != attempt["attempt"].get("grade", {}).get(
            "sha256"
        ):
            raise AgentEvalError("original deterministic grade changed before analysis")
        output_alias = f"original-artifacts/attempt-{index:02d}/output.md"
        total_bytes = _add_analysis_source(
            workspace=workspace,
            source_path=output_alias,
            data=output_bytes,
            kind="artifact",
            sources=source_map,
            prompt_parts=prompt_parts,
            total_bytes=total_bytes,
        )
        manifest.append(
            {"path": output_alias, "sha256": source_map[output_alias]["sha256"]}
        )
        summary = {
            "suite": "deterministic",
            "skill": skill,
            "eval_id": failure["eval_id"],
            "repeat": attempt["attempt"]["repeat"],
            "status": "fail",
            "failed_assertion_ids": failure["failed_assertion_ids"],
        }
        summary_bytes = (
            json.dumps(summary, ensure_ascii=False, indent=2) + "\n"
        ).encode()
        summary_alias = f"original-artifacts/attempt-{index:02d}/grader-findings.json"
        total_bytes = _add_analysis_source(
            workspace=workspace,
            source_path=summary_alias,
            data=summary_bytes,
            kind="artifact",
            sources=source_map,
            prompt_parts=prompt_parts,
            total_bytes=total_bytes,
        )
        manifest.append(
            {"path": summary_alias, "sha256": source_map[summary_alias]["sha256"]}
        )

    skills_root = package_root / "skills"
    (workspace / ".agents" / "skills").mkdir(parents=True, exist_ok=True)
    skill_root = skills_root / skill
    if skill_root.is_symlink() or not skill_root.is_dir():
        raise AgentEvalError("deterministic analysis Skill source is missing or unsafe")
    visible_root = workspace / ".agents" / "skills" / skill
    for relative in _allowed_repair_paths(skill, package_root):
        source = _safe_child_file(skill_root, relative)
        data = source.read_bytes()
        try:
            data.decode("utf-8", errors="strict")
        except UnicodeDecodeError:
            continue
        alias = f".agents/skills/{skill}/{relative}"
        total_bytes = _add_analysis_source(
            workspace=workspace,
            source_path=alias,
            data=data,
            kind="skill",
            sources=source_map,
            prompt_parts=prompt_parts,
            total_bytes=total_bytes,
        )
        destination = visible_root / safe_relative_path(relative)
        destination.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_bytes(destination, data)
        manifest.append({"path": alias, "sha256": source_map[alias]["sha256"]})
    return source_map, "\n".join(prompt_parts), manifest


def _source_paths(package_root: Path, skill: str) -> dict[str, str]:
    manifest: dict[str, str] = {}
    root = package_root / "skills" / skill
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise AgentEvalError("baseline Skill package contains a symlink")
        if path.is_file():
            manifest[path.relative_to(package_root / "skills").as_posix()] = (
                sha256_bytes(path.read_bytes())
            )
    return manifest


def _validate_analysis(
    raw: str,
    *,
    skill_names: set[str],
    criterion: str,
    evidence_sources: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    safe = sanitize_diagnostic(raw)
    try:
        value = json.loads(safe)
    except json.JSONDecodeError as exc:
        raise AgentEvalError("analysis Agent response is not JSON") from exc
    required = {
        "classification",
        "skill",
        "issue",
        "evidence",
        "alternative_causes",
        "repair_paths",
        "repair_rationale",
    }
    if not isinstance(value, dict) or set(value) != required:
        raise AgentEvalError("analysis Agent response schema is invalid")
    if value["classification"] not in {
        "skill",
        "agent",
        "evaluator",
        "input",
        "environment",
        "evidence",
        "unknown",
    }:
        raise AgentEvalError("analysis Agent classification is invalid")
    if value["skill"] is not None and value["skill"] not in skill_names:
        raise AgentEvalError("analysis Agent selected an unknown Skill")
    for field in ("issue", "repair_rationale"):
        if not isinstance(value[field], str) or not value[field].strip():
            raise AgentEvalError(f"analysis Agent {field} is missing")
    for field in ("alternative_causes", "repair_paths"):
        if not isinstance(value[field], list) or any(
            not isinstance(item, str) or not item.strip() for item in value[field]
        ):
            raise AgentEvalError(f"analysis Agent {field} must be a string array")
    if not isinstance(value["evidence"], list) or len(value["evidence"]) < 2:
        raise AgentEvalError("analysis Agent evidence must cite source text")
    evidence_kinds: set[str] = set()
    seen_evidence: set[tuple[str, str, str]] = set()
    for item in value["evidence"]:
        if not isinstance(item, dict) or set(item) != {"path", "sha256", "quote"}:
            raise AgentEvalError("analysis Agent evidence entry schema is invalid")
        path = item["path"]
        digest = item["sha256"]
        quote = item["quote"]
        if not all(
            isinstance(item[field], str) for field in ("path", "sha256", "quote")
        ):
            raise AgentEvalError("analysis Agent evidence fields must be strings")
        try:
            normalized_path = safe_relative_path(path).as_posix()
        except AgentEvalError as exc:
            raise AgentEvalError("analysis Agent cited an unsafe source path") from exc
        source = evidence_sources.get(normalized_path)
        if source is None:
            raise AgentEvalError("analysis Agent cited a source that was not inspected")
        if digest != source.get("sha256"):
            raise AgentEvalError(
                "analysis Agent source hash does not match inspected source"
            )
        if len(quote.strip()) < 16 or quote not in source.get("text", ""):
            raise AgentEvalError(
                "analysis Agent quote does not match inspected source text"
            )
        identity = (normalized_path, digest, quote)
        if identity in seen_evidence:
            raise AgentEvalError("analysis Agent repeated an evidence citation")
        seen_evidence.add(identity)
        evidence_kinds.add(source.get("kind", ""))
    if not {"artifact", "skill"}.issubset(evidence_kinds):
        raise AgentEvalError(
            "analysis Agent must cite both an original artifact and Skill source"
        )
    if value["classification"] == "skill" and value["skill"] is None:
        raise AgentEvalError("Skill classification requires one selected Skill")
    value["target_criterion"] = criterion
    return value


def _analysis_repair_gate(
    analysis: dict[str, Any],
    *,
    allowed_skills: set[str],
    attempts: list[dict[str, Any]],
    evidence_sources: dict[str, dict[str, Any]],
    package_root: Path,
) -> dict[str, Any]:
    reasons: list[str] = []
    skill = analysis.get("skill")
    if analysis.get("classification") != "skill" or skill not in allowed_skills:
        reasons.append("analysis_does_not_attribute_failure_to_one_allowed_skill")
    if analysis.get("alternative_causes"):
        reasons.append("alternative_causes_remain_unresolved")
    if not isinstance(skill, str) or skill not in allowed_skills:
        skill_evidence = False
    else:
        skill_evidence = any(
            evidence_sources.get(row.get("path"), {}).get("kind") == "skill"
            and row.get("path", "").startswith(f".agents/skills/{skill}/")
            for row in analysis.get("evidence", [])
            if isinstance(row, dict)
        )
    artifact_evidence = any(
        evidence_sources.get(row.get("path"), {}).get("kind") == "artifact"
        for row in analysis.get("evidence", [])
        if isinstance(row, dict)
    )
    if not skill_evidence or not artifact_evidence:
        reasons.append("root_cause_is_not_tied_to_verified_artifact_and_skill_text")
    usage = (
        [_skill_use_for_attempt(row["attempt"], skill) for row in attempts]
        if isinstance(skill, str)
        else []
    )
    if len(usage) < 2 or any(value != "observed" for value in usage):
        reasons.append("selected_skill_use_not_observed_in_every_baseline_attempt")
    base_allowed_paths = (
        set(_allowed_repair_paths(skill, package_root))
        if isinstance(skill, str) and skill in allowed_skills
        else set()
    )
    requested_paths: set[str] = set()
    raw_paths = analysis.get("repair_paths", [])
    if not isinstance(raw_paths, list) or not raw_paths:
        reasons.append("analysis_requested_no_repair_path")
    else:
        for raw_path in raw_paths:
            if not isinstance(raw_path, str):
                reasons.append("analysis_requested_invalid_repair_path")
                continue
            path = PurePosixPath(raw_path)
            if (
                path.is_absolute()
                or not path.parts
                or ".." in path.parts
                or "\\" in raw_path
            ):
                reasons.append("analysis_requested_path_outside_single_skill_allowlist")
                continue
            candidate = path.as_posix()
            if isinstance(skill, str) and candidate.startswith(skill + "/"):
                candidate = candidate[len(skill) + 1 :]
            if candidate not in base_allowed_paths:
                reasons.append("analysis_requested_path_outside_single_skill_allowlist")
                continue
            requested_paths.add(candidate)
    return {
        "allowed": not reasons,
        "reasons": sorted(set(reasons)),
        "skill": skill,
        "skill_use_observations": usage,
        "requested_paths": sorted(requested_paths),
        "artifact_evidence_verified": artifact_evidence,
        "skill_source_evidence_verified": skill_evidence,
        "alternative_causes_clear": not analysis.get("alternative_causes"),
    }


def _allowed_repair_paths(skill: str, package_root: Path) -> list[str]:
    root = package_root / "skills" / skill
    return sorted(
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file()
        and not path.is_symlink()
        and (
            path.name == "SKILL.md"
            or path.relative_to(root).parts[0] in {"references", "scripts", "assets"}
        )
    )


def _safe_child_file(root: Path, relative: str) -> Path:
    try:
        safe = safe_relative_path(relative)
    except (AgentEvalError, TypeError) as exc:
        raise AgentEvalError("analysis evidence path is unsafe") from exc
    candidate = root
    for part in safe.parts:
        candidate = candidate / part
        if candidate.is_symlink():
            raise AgentEvalError("analysis evidence may not contain symlinks")
    try:
        resolved = ensure_within(candidate, root)
    except AgentEvalError as exc:
        raise AgentEvalError("analysis evidence path escapes its root") from exc
    if not resolved.is_file():
        raise AgentEvalError("analysis evidence file is missing")
    return resolved


def _add_analysis_source(
    *,
    workspace: Path,
    source_path: str,
    data: bytes,
    kind: str,
    sources: dict[str, dict[str, Any]],
    prompt_parts: list[str],
    total_bytes: int,
) -> int:
    try:
        relative = safe_relative_path(source_path).as_posix()
        text = data.decode("utf-8", errors="strict")
    except (AgentEvalError, UnicodeDecodeError) as exc:
        raise AgentEvalError("analysis evidence is not safe UTF-8 text") from exc
    safe_text = sanitize_diagnostic(text, _MAX_ANALYSIS_SOURCE_BYTES)
    if safe_text != text or len(data) > _MAX_ANALYSIS_SOURCE_BYTES:
        raise AgentEvalError("analysis evidence contains secrets or exceeds its limit")
    next_total = total_bytes + len(data)
    if next_total > _MAX_ANALYSIS_SOURCE_BYTES:
        raise AgentEvalError("analysis evidence exceeds the fixed total size limit")
    digest = sha256_bytes(data)
    destination = workspace / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_bytes(destination, data)
    sources[relative] = {"sha256": digest, "kind": kind, "text": text}
    prompt_parts.extend([f"## {relative} ({digest})", "", text, ""])
    return next_total


def _prepare_analysis_workspace(
    *,
    workspace: Path,
    attempts: list[dict[str, Any]],
    allowed_skills: set[str],
    package_root: Path,
    target_root: Path,
) -> tuple[dict[str, dict[str, Any]], str, list[dict[str, str]]]:
    scenario = load_scenario()
    source_map: dict[str, dict[str, Any]] = {}
    prompt_parts: list[str] = []
    source_manifest: list[dict[str, str]] = []
    total_bytes = 0
    for index, attempt in enumerate(attempts, start=1):
        output_root = attempt["output_root"]
        attempt_artifacts = [
            row for row in attempt["artifacts"] if row.get("skill") in allowed_skills
        ]
        final_relative = "final-message.md"
        final_path = output_root / final_relative
        if final_path.is_file() and not final_path.is_symlink():
            if final_path.stat().st_size > _MAX_ANALYSIS_SOURCE_BYTES:
                raise AgentEvalError("final Agent message exceeds its evidence limit")
            if final_relative not in {row.get("path") for row in attempt_artifacts}:
                attempt_artifacts.append(
                    {
                        "path": final_relative,
                        "sha256": sha256_bytes(final_path.read_bytes()),
                        "skill": "agent",
                        "kind": "final-message",
                    }
                )
        for artifact in sorted(
            attempt_artifacts, key=lambda row: (row["skill"], row["kind"], row["path"])
        ):
            relative = artifact.get("path")
            if not isinstance(relative, str):
                raise AgentEvalError("validated artifact has no canonical path")
            source = _safe_child_file(output_root, relative)
            data = source.read_bytes()
            digest = sha256_bytes(data)
            if digest != artifact.get("sha256"):
                raise AgentEvalError("original Agent artifact changed after validation")
            alias = f"original-artifacts/attempt-{index:02d}/{relative}"
            total_bytes = _add_analysis_source(
                workspace=workspace,
                source_path=alias,
                data=data,
                kind="artifact",
                sources=source_map,
                prompt_parts=prompt_parts,
                total_bytes=total_bytes,
            )
            source_manifest.append({"path": alias, "sha256": digest})

    skills_root = package_root / "skills"
    (workspace / ".agents" / "skills").mkdir(parents=True, exist_ok=True)
    for skill in sorted(allowed_skills):
        skill_root = skills_root / skill
        if skill_root.is_symlink() or not skill_root.is_dir():
            raise AgentEvalError("analysis Skill source is missing or unsafe")
        visible_root = workspace / ".agents" / "skills" / skill
        for relative in _allowed_repair_paths(skill, package_root):
            source = _safe_child_file(skill_root, relative)
            if source.stat().st_size > _MAX_ANALYSIS_SOURCE_BYTES:
                raise AgentEvalError("Skill source exceeds the analysis evidence limit")
            data = source.read_bytes()
            try:
                data.decode("utf-8", errors="strict")
            except UnicodeDecodeError:
                continue
            alias = f".agents/skills/{skill}/{relative}"
            total_bytes = _add_analysis_source(
                workspace=workspace,
                source_path=alias,
                data=data,
                kind="skill",
                sources=source_map,
                prompt_parts=prompt_parts,
                total_bytes=total_bytes,
            )
            destination = visible_root / safe_relative_path(relative)
            destination.parent.mkdir(parents=True, exist_ok=True)
            atomic_write_bytes(destination, data)
            source_manifest.append(
                {"path": alias, "sha256": source_map[alias]["sha256"]}
            )

    scenario_dir = (
        Path(__file__).resolve().parent / "scenarios" / scenario["scenario_id"]
    )
    task_file = scenario_dir / scenario["task"]
    if task_file.is_file() and not task_file.is_symlink():
        data = task_file.read_bytes()
        total_bytes = _add_analysis_source(
            workspace=workspace,
            source_path="public-input/task.md",
            data=data,
            kind="public_input",
            sources=source_map,
            prompt_parts=prompt_parts,
            total_bytes=total_bytes,
        )
        source_manifest.append(
            {
                "path": "public-input/task.md",
                "sha256": source_map["public-input/task.md"]["sha256"],
            }
        )
    references = extract_revision_files(
        source_root=target_root,
        revision=DEFAULT_TARGET_REVISION,
        paths=scenario["reference_paths"],
    )
    for relative in sorted(references):
        alias = f"public-references/{relative}"
        total_bytes = _add_analysis_source(
            workspace=workspace,
            source_path=alias,
            data=references[relative],
            kind="public_reference",
            sources=source_map,
            prompt_parts=prompt_parts,
            total_bytes=total_bytes,
        )
        source_manifest.append({"path": alias, "sha256": source_map[alias]["sha256"]})
    return source_map, "\n".join(prompt_parts), source_manifest


def _copy_allowed_skill_files(
    source_package: Path, destination_skills_root: Path, skill: str
) -> set[str]:
    source_root = source_package / "skills" / skill
    destination_root = destination_skills_root / skill
    visible_paths: set[str] = set()
    for relative in _allowed_repair_paths(skill, source_package):
        source = _safe_child_file(source_root, relative)
        destination = destination_root / safe_relative_path(relative)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
        visible_paths.add(relative)
    return visible_paths


def _validate_repair_diff(
    before: dict[str, str],
    skill_root: Path,
    skill: str,
    allowed: set[str],
    *,
    visible_paths: set[str] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, str]]:
    after: dict[str, str] = {}
    root = skill_root / skill
    changes: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise AgentEvalError("repair Agent created a symlink")
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        if relative != "SKILL.md" and (
            not PurePosixPath(relative).parts
            or PurePosixPath(relative).parts[0]
            not in {"references", "scripts", "assets"}
        ):
            raise AgentEvalError(
                f"repair Agent changed a forbidden Skill path: {relative}"
            )
        raw = path.read_bytes()
        text = raw.decode("utf-8", errors="strict")
        if _SECRET_RE.search(text):
            raise AgentEvalError("repair Agent output contains secret-shaped text")
        digest = sha256_bytes(raw)
        after[relative] = digest
        old_digest = before.get(f"{skill}/{relative}")
        if digest != old_digest:
            changes.append(
                {
                    "path": relative,
                    "before_sha256": old_digest,
                    "after_sha256": digest,
                    "size": len(raw),
                }
            )
    for source_path, old_digest in before.items():
        if not source_path.startswith(skill + "/"):
            continue
        relative = source_path[len(skill) + 1 :]
        if (
            visible_paths is None or relative in visible_paths
        ) and relative not in after:
            raise AgentEvalError("repair Agent deleted an existing Skill file")
    changed_paths = {item["path"] for item in changes}
    if not changed_paths:
        raise AgentEvalError("repair Agent produced no source changes")
    if not changed_paths.issubset(allowed):
        raise AgentEvalError(
            "repair Agent changed a path it did not request permission to edit"
        )
    return changes, after


def _insert_mount_before_image(argv: list[str], mount: str) -> list[str]:
    index = 2
    value_options = {
        "--network",
        "--mount",
        "--workdir",
        "-w",
        "-e",
        "--env",
        "--env-file",
        "--name",
        "--user",
        "--entrypoint",
        "--memory",
        "--cpus",
        "--security-opt",
    }
    flag_options = {"--rm", "--read-only", "-i", "-t", "-d", "--init"}
    while index < len(argv):
        token = argv[index]
        if token in flag_options:
            index += 1
            continue
        if token in value_options:
            index += 2
            continue
        if any(token.startswith(option + "=") for option in value_options):
            index += 1
            continue
        break
    return [*argv[:index], "--mount", mount, *argv[index:]]


def _skill_use_for_attempt(attempt: dict[str, Any], skill: str) -> str:
    observation = attempt.get("skill_use_observation", "unverified")
    if isinstance(observation, dict):
        return observation.get(skill, "unverified")
    return observation if isinstance(observation, str) else "unverified"


def _related_contract_tests(skill: str) -> list[dict[str, str]]:
    roots = (
        REPO_ROOT / "scripts" / "skills" / "evals" / "deterministic" / "tests",
        REPO_ROOT / "scripts" / "skills" / "evals" / "semantic" / "tests",
        REPO_ROOT / "tests" / "skills" / "evals" / "deterministic",
        REPO_ROOT / "tests" / "skills" / "evals" / "semantic",
        REPO_ROOT / "tests" / "skills" / "runtime",
    )
    needle = skill.encode("utf-8").lower()
    selected = []
    for root in roots:
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("test_*.py")):
            if path.is_symlink() or not path.is_file():
                continue
            data = path.read_bytes()
            if needle in data.lower():
                selected.append(
                    {
                        "path": path.relative_to(REPO_ROOT).as_posix(),
                        "sha256": sha256_bytes(data),
                    }
                )
    return selected


def _freeze_independent_eval_plan(
    *,
    skill: str,
    evaluator_revision: str,
    skill_revision: str,
    baseline_package_fingerprint: str,
    profile: dict[str, Any],
    agent_command: list[str],
    suites: set[str] | None = None,
) -> dict[str, Any]:
    cases = []
    try:
        from .run import (
            _dataset_fingerprint,
            _load_deterministic_cases,
            _load_semantic_cases,
        )

        suite_values = []
        if suites is None or "deterministic" in suites:
            suite_values.append(
                ("deterministic", _load_deterministic_cases(skill, None))
            )
        if suites is None or "semantic" in suites:
            suite_values.append(("semantic", _load_semantic_cases(skill, None)))
        for suite, values in suite_values:
            for case in values:
                input_fingerprint = sha256_bytes(case["input"].encode("utf-8"))
                cases.append(
                    {
                        "suite": suite,
                        "skill": skill,
                        "case_id": case["id"],
                        "input_fingerprint": input_fingerprint,
                        "dataset_fingerprint": _dataset_fingerprint(
                            case["fingerprint_files"]
                        ),
                        "evaluator_revision": evaluator_revision,
                        "skill_revision": skill_revision,
                        "baseline_package_fingerprint": baseline_package_fingerprint,
                        "profile_fingerprint": profile_fingerprint(profile),
                        "agent_command_fingerprint": canonical_fingerprint(
                            agent_command
                        ),
                        "judge_command_fingerprint": canonical_fingerprint(
                            profile["judge"]["command_argv"]
                        ),
                        "grader": (
                            "fixed_deterministic_grader"
                            if suite == "deterministic"
                            else "fixed_semantic_judge"
                        ),
                        "judge_profile_fingerprint": (
                            profile_fingerprint(profile)
                            if suite == "semantic"
                            else None
                        ),
                        "repeat": 2,
                    }
                )
    except (
        AgentEvalError,
        ImportError,
        KeyError,
        OSError,
        TypeError,
        ValueError,
    ) as exc:
        return {
            "schema_version": 1,
            "status": "blocked",
            "cases": [],
            "contract_tests": _related_contract_tests(skill),
            "contract_test_execution": "fixed_evaluator_checkout",
            "block_reason": sanitize_diagnostic(
                f"independent_eval_cases_unavailable: {exc}", 500
            ),
        }
    cases.sort(key=lambda row: (row["suite"], row["case_id"]))
    tests = _related_contract_tests(skill)
    return {
        "schema_version": 1,
        "status": "ready" if cases and tests else "blocked",
        "cases": cases,
        "contract_tests": tests,
        "contract_test_execution": "fixed_evaluator_checkout",
        "block_reason": None
        if cases and tests
        else "no_independent_eval_cases_or_related_contract_tests_found",
    }


def _run_related_contract_tests(
    plan: list[dict[str, str]],
    *,
    timeout_seconds: int,
    evaluator_revision: str,
    skill: str,
    skill_revision: str,
    expected_skills: set[str],
    candidate_package: Path,
    candidate_package_fingerprint: str,
) -> dict[str, Any]:
    if timeout_seconds <= 0:
        return {
            "status": "review_pending",
            "planned": len(plan),
            "completed": 0,
            "results": [{"status": "timeout", "reason": "time_budget_exhausted"}],
            "conditions_match": False,
            "evaluator_revision": evaluator_revision,
            "candidate_package_fingerprint": candidate_package_fingerprint,
        }
    results = []
    deadline = time.monotonic() + max(0, timeout_seconds)
    workspace_owner = tempfile.TemporaryDirectory(prefix="agent-eval-contract-")
    candidate_owner = tempfile.TemporaryDirectory(prefix="agent-eval-candidate-")
    workspace = Path(workspace_owner.name)
    try:
        candidate_workspace = Path(candidate_owner.name)
        candidate_manifest = create_skill_workspace_from_root(
            candidate_package,
            candidate_workspace,
            expected_skills=expected_skills,
            parent_revision=skill_revision,
        )
        if candidate_manifest["package_fingerprint"] != candidate_package_fingerprint:
            raise AgentEvalError(
                "candidate Skill package changed before contract tests"
            )
        archive = subprocess.run(
            ["git", "archive", "--format=tar", evaluator_revision],
            cwd=REPO_ROOT,
            capture_output=True,
            timeout=min(30, max(1, int(deadline - time.monotonic()))),
            check=False,
            shell=False,
        )
        if archive.returncode != 0:
            raise AgentEvalError("fixed Evaluator snapshot could not be prepared")
        with tarfile.open(fileobj=io.BytesIO(archive.stdout), mode="r:") as snapshot:
            for member in snapshot.getmembers():
                relative = PurePosixPath(member.name)
                if (
                    relative.is_absolute()
                    or ".." in relative.parts
                    or not relative.parts
                    or not (member.isdir() or member.isfile())
                ):
                    raise AgentEvalError("fixed Evaluator archive has an unsafe member")
                destination = workspace.joinpath(*relative.parts)
                if member.isdir():
                    destination.mkdir(parents=True, exist_ok=True)
                    continue
                source = snapshot.extractfile(member)
                if source is None:
                    raise AgentEvalError("fixed Evaluator archive is incomplete")
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(source.read())

        source_root = candidate_workspace / "skills" / skill
        if source_root.is_symlink() or not source_root.is_dir():
            raise AgentEvalError("candidate Skill package is unavailable")
        for source in source_root.rglob("*"):
            if source.is_symlink() or not source.is_file():
                if source.is_dir() and not source.is_symlink():
                    continue
                raise AgentEvalError("candidate Skill package contains an unsafe path")
        destination_root = workspace / "skills" / skill
        if destination_root.exists():
            shutil.rmtree(destination_root)
        shutil.copytree(source_root, destination_root)
        candidate_owner.cleanup()
    except (
        AgentEvalError,
        OSError,
        subprocess.SubprocessError,
        tarfile.TarError,
    ) as exc:
        workspace_owner.cleanup()
        candidate_owner.cleanup()
        reason = sanitize_diagnostic(str(exc), 500)
        return {
            "status": "review_pending",
            "planned": len(plan),
            "completed": 0,
            "results": [{"status": "evidence_unverified", "reason": reason}],
            "conditions_match": False,
            "evaluator_revision": evaluator_revision,
            "candidate_package_fingerprint": candidate_package_fingerprint,
        }

    for row in plan:
        relative = row.get("path")
        if not isinstance(relative, str):
            results.append(
                {"status": "evidence_unverified", "reason": "invalid_test_path"}
            )
            continue
        try:
            remaining = int(deadline - time.monotonic())
            if remaining <= 0:
                results.append({"path": relative, "status": "timeout"})
                continue
            path = _resolve_run_path(workspace, relative)
            raw = path.read_bytes()
            if sha256_bytes(raw) != row.get("sha256"):
                raise AgentEvalError(
                    "related contract test changed after it was frozen"
                )
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "unittest",
                    "discover",
                    "-s",
                    path.parent.relative_to(workspace).as_posix(),
                    "-p",
                    path.name,
                    "-q",
                ],
                cwd=workspace,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=remaining,
                check=False,
                shell=False,
            )
            output = result.stdout + result.stderr
            match = re.search(r"Ran (\d+) tests?", output)
            tests_run = int(match.group(1)) if match else 0
            passed = result.returncode == 0 and tests_run > 0 and "OK" in output
            dependency_unavailable = (
                "ModuleNotFoundError" in output
                or "ImportError: Failed to import test module" in output
            )
            results.append(
                {
                    "path": relative,
                    "sha256": row["sha256"],
                    "status": (
                        "pass"
                        if passed
                        else "evidence_unverified"
                        if dependency_unavailable
                        else "fail"
                    ),
                    "reason": None
                    if passed
                    else "contract_test_dependency_unavailable"
                    if dependency_unavailable
                    else "contract_test_failed",
                    "exit_code": result.returncode,
                    "tests_run": tests_run,
                    "output_sha256": sha256_bytes(output.encode("utf-8")),
                }
            )
        except subprocess.TimeoutExpired as exc:
            results.append(
                {
                    "path": relative,
                    "sha256": row.get("sha256"),
                    "status": "timeout",
                    "reason": "contract_test_timeout",
                    "timeout_seconds": max(1, timeout_seconds),
                    "output_sha256": sha256_bytes(
                        repr((exc.stdout, exc.stderr)).encode("utf-8")
                    ),
                }
            )
        except (AgentEvalError, OSError, ValueError) as exc:
            results.append(
                {
                    "path": relative,
                    "sha256": row.get("sha256"),
                    "status": "evidence_unverified",
                    "reason": sanitize_diagnostic(str(exc), 500),
                }
            )
    status = (
        "pass"
        if results
        and len(results) == len(plan)
        and all(row["status"] == "pass" for row in results)
        else "review_pending"
    )
    workspace_owner.cleanup()
    return {
        "status": status,
        "planned": len(plan),
        "completed": sum(row["status"] in {"pass", "fail"} for row in results),
        "results": results,
        "conditions_match": True,
        "evaluator_revision": evaluator_revision,
        "candidate_package_fingerprint": candidate_package_fingerprint,
    }


def _run_independent_eval(
    *,
    case: dict[str, Any],
    baseline: dict[str, Any],
    profile: dict[str, Any],
    profile_path: Path,
    evidence_root: Path,
    destination: Path,
    candidate_package: Path | None = None,
    timeout_seconds: int,
) -> dict[str, Any]:
    evidence_relative = safe_relative_path(profile["verification"]["evidence_path"])
    if timeout_seconds <= 0:
        return {"status": "review_pending", "reason": "time_budget_exhausted"}
    worst_case_seconds = 2 * (
        profile["agent"]["timeout_seconds"]
        + (profile["judge"]["timeout_seconds"] if case["suite"] == "semantic" else 0)
        + 60
    )
    if timeout_seconds < worst_case_seconds:
        return {
            "status": "review_pending",
            "reason": "insufficient_budget_for_independent_repeats",
            "required_seconds": worst_case_seconds,
            "available_seconds": timeout_seconds,
        }
    source_evidence = evidence_root / evidence_relative
    if source_evidence.is_symlink() or not source_evidence.is_file():
        return {"status": "review_pending", "reason": "isolation_evidence_missing"}
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.mkdir(parents=True, exist_ok=False)
        evidence_destination = destination / evidence_relative
        evidence_destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source_evidence, evidence_destination)
    except OSError as exc:
        return {
            "status": "review_pending",
            "reason": sanitize_diagnostic(str(exc), 500),
        }
    args = [
        "--suite",
        case["suite"],
        "--skill",
        case["skill"],
        "--eval-id",
        case["case_id"],
        "--skill-revision",
        baseline["skill_revision"],
        "--execution-profile",
        str(profile_path),
        "--output-root",
        str(destination),
        "--repeat",
        "2",
        "--agent-name",
        profile["agent"]["name"],
        "--agent-model",
        profile["agent"]["model"],
        "--agent-version",
        profile["agent"]["cli_version"],
    ]
    if candidate_package is not None:
        args.extend(["--skill-package-root", str(candidate_package)])
    args.extend(["--agent-command", *baseline["agent_command_template"]])
    stdout = io.StringIO()
    stderr = io.StringIO()
    try:
        if timeout_seconds <= 0:
            return {"status": "review_pending", "reason": "time_budget_exhausted"}
        with redirect_stdout(stdout), redirect_stderr(stderr):
            exit_code = run_agent_evaluation(args)
        result_path = destination / "result.json"
        if not result_path.is_file():
            return {
                "status": "review_pending",
                "reason": sanitize_diagnostic(
                    stderr.getvalue()
                    or stdout.getvalue()
                    or f"independent_eval_did_not_save_result_exit_{exit_code}",
                    500,
                ),
                "runner_output_sha256": sha256_bytes(
                    (stdout.getvalue() + stderr.getvalue()).encode("utf-8")
                ),
            }
        return {
            "status": "captured",
            "exit_code": exit_code,
            "result_path": str(result_path),
            "runner_output_sha256": sha256_bytes(
                (stdout.getvalue() + stderr.getvalue()).encode("utf-8")
            ),
        }
    except (AgentEvalError, OSError, TypeError, ValueError, KeyError) as exc:
        return {
            "status": "review_pending",
            "reason": sanitize_diagnostic(str(exc), 500),
            "runner_output_sha256": sha256_bytes(
                (stdout.getvalue() + stderr.getvalue()).encode("utf-8")
            ),
        }


def _run_deterministic_candidate_eval(
    *,
    baseline: dict[str, Any],
    skill: str,
    eval_id: str,
    profile: dict[str, Any],
    profile_path: Path,
    evidence_root: Path,
    destination: Path,
    candidate_package: Path,
    timeout_seconds: int,
) -> dict[str, Any]:
    evidence_relative = safe_relative_path(profile["verification"]["evidence_path"])
    required_seconds = 2 * (profile["agent"]["timeout_seconds"] + 60)
    if timeout_seconds < required_seconds:
        return {
            "status": "review_pending",
            "reason": "insufficient_budget_for_deterministic_candidate_repeats",
            "required_seconds": required_seconds,
            "available_seconds": timeout_seconds,
        }
    source_evidence = evidence_root / evidence_relative
    if source_evidence.is_symlink() or not source_evidence.is_file():
        return {"status": "review_pending", "reason": "isolation_evidence_missing"}
    try:
        destination.mkdir(parents=True, exist_ok=False)
        evidence_destination = destination / evidence_relative
        evidence_destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source_evidence, evidence_destination)
    except OSError as exc:
        return {
            "status": "review_pending",
            "reason": sanitize_diagnostic(str(exc), 500),
        }
    args = [
        "--suite",
        "deterministic",
        "--skill",
        skill,
        "--eval-id",
        eval_id,
        "--skill-revision",
        baseline["skill_revision"],
        "--skill-package-root",
        str(candidate_package),
        "--execution-profile",
        str(profile_path),
        "--output-root",
        str(destination),
        "--repeat",
        "2",
        "--agent-name",
        profile["agent"]["name"],
        "--agent-model",
        profile["agent"]["model"],
        "--agent-version",
        profile["agent"]["cli_version"],
        "--agent-command",
        *baseline["agent_command_template"],
    ]
    stdout = io.StringIO()
    stderr = io.StringIO()
    try:
        with redirect_stdout(stdout), redirect_stderr(stderr):
            exit_code = run_agent_evaluation(args)
        result_path = destination / "result.json"
        if not result_path.is_file():
            return {
                "status": "review_pending",
                "reason": sanitize_diagnostic(
                    stderr.getvalue()
                    or stdout.getvalue()
                    or "candidate_deterministic_eval_did_not_save_result_"
                    f"exit_{exit_code}",
                    500,
                ),
                "runner_output_sha256": sha256_bytes(
                    (stdout.getvalue() + stderr.getvalue()).encode("utf-8")
                ),
            }
        return {
            "status": "captured",
            "exit_code": exit_code,
            "result_path": str(result_path),
            "runner_output_sha256": sha256_bytes(
                (stdout.getvalue() + stderr.getvalue()).encode("utf-8")
            ),
        }
    except (AgentEvalError, OSError, TypeError, ValueError, KeyError) as exc:
        return {
            "status": "review_pending",
            "reason": sanitize_diagnostic(str(exc), 500),
            "runner_output_sha256": sha256_bytes(
                (stdout.getvalue() + stderr.getvalue()).encode("utf-8")
            ),
        }


def _grade_snapshot(suite: str, grade: dict[str, Any]) -> dict[str, int] | None:
    if suite == "deterministic":
        rows = grade.get("assertions")
        if not isinstance(rows, list) or not rows:
            return None
        score = {"fail": 0, "warning": 1, "pass": 2}
        result = {}
        for row in rows:
            if (
                not isinstance(row, dict)
                or not isinstance(row.get("id"), str)
                or row.get("status") not in score
                or row["id"] in result
            ):
                return None
            result[row["id"]] = score[row["status"]]
        return result
    rows = grade.get("criteria")
    if not isinstance(rows, list) or not rows:
        return None
    result = {}
    for row in rows:
        rating = row.get("rating") if isinstance(row, dict) else None
        if (
            not isinstance(row, dict)
            or not isinstance(row.get("id"), str)
            or isinstance(rating, bool)
            or not isinstance(rating, int)
            or rating not in {1, 2, 3, 4}
            or row["id"] in result
        ):
            return None
        result[row["id"]] = rating
    return result


def _validate_independent_run(
    result_path: Path,
    *,
    case: dict[str, Any],
    profile: dict[str, Any],
    package_fingerprint: str,
    candidate: bool,
    runtime_source_root: Path | None = None,
) -> dict[str, Any]:
    try:
        run = _load_json(result_path)
        root = result_path.parent.resolve(strict=True)
        evaluator = run.get("evaluator")
        skill_package = run.get("skill_package")
        if (
            run.get("status") not in {"pass", "needs_review_or_fail"}
            or run.get("suite") != case["suite"]
            or not isinstance(evaluator, dict)
            or evaluator.get("revision") != case["evaluator_revision"]
            or run.get("skill_revision") != case["skill_revision"]
            or run.get("dataset_fingerprint") != case["dataset_fingerprint"]
            or run.get("profile_fingerprint") != case["profile_fingerprint"]
            or run.get("profile_verification") != "verified"
            or run.get("agent_command_fingerprint") != case["agent_command_fingerprint"]
            or run.get("judge_command_fingerprint") != case["judge_command_fingerprint"]
            or run.get("repeat") != 2
            or not isinstance(skill_package, dict)
            or skill_package.get("package_fingerprint") != package_fingerprint
            or case["skill"] not in skill_package.get("skills", [])
            or run.get("workspace_cleanup") != "succeeded"
            or run.get("skill_candidate_revision_status")
            != ("uncommitted_patch" if candidate else "git_commit")
        ):
            raise AgentEvalError(
                "independent evaluation conditions do not match the frozen plan"
            )
        if profile_fingerprint(profile) != case["profile_fingerprint"]:
            raise AgentEvalError(
                "independent evaluation profile changed after freezing"
            )
        attempts = run.get("attempts")
        if not isinstance(attempts, list) or len(attempts) != 2:
            raise AgentEvalError(
                "independent evaluation did not save exactly two attempts"
            )
        by_repeat: dict[int, dict[str, Any]] = {}
        for attempt in attempts:
            repeat = attempt.get("repeat") if isinstance(attempt, dict) else None
            if (
                not isinstance(attempt, dict)
                or isinstance(repeat, bool)
                or repeat not in {1, 2}
                or repeat in by_repeat
                or attempt.get("suite") != case["suite"]
                or attempt.get("skill") != case["skill"]
                or attempt.get("eval_id") != case["case_id"]
                or attempt.get("input_fingerprint") != case["input_fingerprint"]
                or attempt.get("status") not in {"pass", "fail"}
                or attempt.get("skill_use_observation") != "observed"
            ):
                raise AgentEvalError(
                    "independent attempt identity or Skill-use evidence is invalid"
                )
            execution = attempt.get("agent_execution")
            isolation = attempt.get("agent_isolation")
            trace = attempt.get("agent_trace")
            output = attempt.get("output")
            grade_ref = attempt.get("grade")
            if (
                not isinstance(execution, dict)
                or isinstance(execution.get("exit_code"), bool)
                or execution.get("exit_code") != 0
                or execution.get("timed_out") is not False
                or execution.get("container_cleanup_status") != "succeeded"
                or not isinstance(isolation, dict)
                or isolation.get("status") != "verified"
                or not isinstance(trace, dict)
                or trace.get("status") != "captured"
                or trace.get("redacted") is not False
                or not isinstance(trace.get("path"), str)
                or not isinstance(output, dict)
                or not isinstance(grade_ref, dict)
            ):
                raise AgentEvalError(
                    "independent attempt runtime evidence is incomplete"
                )
            output_path = _resolve_run_path(root, output.get("path"))
            output_bytes = output_path.read_bytes()
            if sha256_bytes(output_bytes) != output.get("sha256"):
                raise AgentEvalError("independent output changed after evaluation")
            trace_relative = safe_relative_path(trace["path"])
            output_parent = PurePosixPath(output["path"]).parent
            trace_candidates = [
                (output_parent / trace_relative).as_posix(),
                (output_parent.parent / trace_relative).as_posix(),
            ]
            existing_trace_paths = []
            for relative in dict.fromkeys(trace_candidates):
                try:
                    existing_trace_paths.append(_resolve_run_path(root, relative))
                except AgentEvalError:
                    continue
            if len(existing_trace_paths) != 1:
                raise AgentEvalError(
                    "independent Agent trace path is missing or ambiguous"
                )
            trace_path = existing_trace_paths[0]
            trace_bytes = trace_path.read_bytes()
            if sha256_bytes(trace_bytes) != trace.get("sha256"):
                raise AgentEvalError("independent Agent trace changed after evaluation")
            trace_summary = _load_json(trace_path)
            commands = trace_summary.get("commands")
            if (
                trace_summary.get("status") != "captured"
                or not isinstance(commands, list)
                or not any(
                    isinstance(command, dict)
                    and command.get("successful") is True
                    and isinstance(command.get("skill_files_read"), list)
                    and case["skill"] in command["skill_files_read"]
                    for command in commands
                )
                or trace_summary.get("turn_completed") is not True
                or trace_summary.get("turn_failed") is not False
            ):
                raise AgentEvalError(
                    "independent Agent trace does not confirm Skill use"
                )
            if case["suite"] == "semantic":
                judges = attempt.get("judge")
                if (
                    not isinstance(judges, list)
                    or not judges
                    or any(
                        not isinstance(judge, dict)
                        or isinstance(judge.get("exit_code"), bool)
                        or judge.get("exit_code") != 0
                        or judge.get("timed_out") is not False
                        or judge.get("container_cleanup_status") != "succeeded"
                        for judge in judges
                    )
                ):
                    raise AgentEvalError("independent Judge evidence is incomplete")
            grade_path = _resolve_run_path(root, grade_ref.get("path"))
            grade_bytes = grade_path.read_bytes()
            if sha256_bytes(grade_bytes) != grade_ref.get("sha256"):
                raise AgentEvalError("independent grade changed after evaluation")
            try:
                grade = json.loads(grade_bytes)
            except json.JSONDecodeError as exc:
                raise AgentEvalError("independent grade is not valid JSON") from exc
            if not isinstance(grade, dict):
                raise AgentEvalError("independent grade must be a JSON object")
            grade_status = (
                grade.get("status")
                if case["suite"] == "deterministic"
                else grade.get("verdict")
            )
            snapshot = _grade_snapshot(case["suite"], grade)
            if grade_status != attempt["status"] or snapshot is None:
                raise AgentEvalError(
                    "independent grade evidence is missing or inconsistent"
                )
            if case["suite"] == "deterministic" and runtime_source_root is not None:
                from scripts.skills.evals.deterministic.run import (
                    grade as deterministic_grade,
                )

                recomputed = deterministic_grade(
                    case["skill"],
                    case["case_id"],
                    output_path,
                    runtime_source_root=runtime_source_root,
                )
                if canonical_fingerprint(recomputed) != canonical_fingerprint(grade):
                    raise AgentEvalError(
                        "independent grade does not match the fixed "
                        "deterministic grader"
                    )
            by_repeat[repeat] = snapshot
        if set(by_repeat) != {1, 2} or by_repeat[1] != by_repeat[2]:
            raise AgentEvalError("independent repeated grades are unstable")
        return {"status": "pass", "run": run, "grades": by_repeat}
    except (AgentEvalError, OSError, TypeError, ValueError, KeyError) as exc:
        return {
            "status": "review_pending",
            "reason": sanitize_diagnostic(str(exc), 500),
        }


def _assess_independent_case(
    *,
    baseline_path: Path,
    candidate_path: Path,
    case: dict[str, Any],
    profile: dict[str, Any],
    baseline_package_fingerprint: str,
    candidate_package_fingerprint: str,
    comparison: dict[str, Any],
    baseline_runtime_source_root: Path | None = None,
    candidate_runtime_source_root: Path | None = None,
) -> dict[str, Any]:
    if not comparison.get("comparable"):
        return {
            "status": "review_pending",
            "conditions_match": False,
            "no_new_regressions": False,
            "reason": "independent baseline and candidate conditions differ",
        }
    baseline = _validate_independent_run(
        baseline_path,
        case=case,
        profile=profile,
        package_fingerprint=baseline_package_fingerprint,
        candidate=False,
        runtime_source_root=baseline_runtime_source_root,
    )
    candidate = _validate_independent_run(
        candidate_path,
        case=case,
        profile=profile,
        package_fingerprint=candidate_package_fingerprint,
        candidate=True,
        runtime_source_root=candidate_runtime_source_root,
    )
    if baseline["status"] != "pass" or candidate["status"] != "pass":
        return {
            "status": "review_pending",
            "conditions_match": True,
            "no_new_regressions": False,
            "baseline_status": baseline["status"],
            "candidate_status": candidate["status"],
            "baseline_reason": baseline.get("reason"),
            "candidate_reason": candidate.get("reason"),
        }
    before = baseline["grades"]
    after = candidate["grades"]
    keys = set(before[1])
    no_new_regressions = keys == set(after[1]) and all(
        after[repeat][key] >= before[repeat][key] for repeat in (1, 2) for key in keys
    )
    return {
        "status": "pass" if no_new_regressions else "review_pending",
        "conditions_match": True,
        "no_new_regressions": no_new_regressions,
        "repeat_count": 2,
        "candidate_package_fingerprint": candidate["run"]["skill_package"][
            "package_fingerprint"
        ],
        "reason": None
        if no_new_regressions
        else "candidate has a new or worse independent grade",
    }


def _run_candidate_independent_assessment(
    *,
    plan: dict[str, Any],
    baseline_results: list[dict[str, Any]],
    baseline: dict[str, Any],
    profile: dict[str, Any],
    profile_path: Path,
    evidence_root: Path,
    case_root: Path,
    candidate_package: Path,
    candidate_package_fingerprint: str,
    baseline_runtime_source_root: Path | None = None,
    timeout_seconds: int,
    compare_runs: Any,
) -> dict[str, Any]:
    deadline = time.monotonic() + max(0, timeout_seconds)
    baseline_by_key = {
        (row.get("case", {}).get("suite"), row.get("case", {}).get("case_id")): row
        for row in baseline_results
        if isinstance(row, dict) and isinstance(row.get("case"), dict)
    }
    cases = []
    conditions_match = True
    fixed_candidate_fingerprint = True
    for independent_case in plan.get("cases", []):
        key = (independent_case.get("suite"), independent_case.get("case_id"))
        baseline_entry = baseline_by_key.get(key)
        case_key = f"{key[0]}:{key[1]}"
        safe_case_key = sha256_bytes(case_key.encode("utf-8")).removeprefix("sha256:")[
            :16
        ]
        candidate_root = case_root / "independent-candidate" / safe_case_key
        entry: dict[str, Any] = {
            "suite": key[0],
            "case_id": key[1],
            "status": "review_pending",
            "candidate_package_fingerprint": candidate_package_fingerprint,
        }
        if (
            key[0] == "semantic"
            and independent_case.get("verification_status") != "verified"
        ):
            entry["reason"] = "semantic_independent_case_requires_verified_judge"
            entry["judge_validation_status"] = "judge_unverified"
            conditions_match = False
            fixed_candidate_fingerprint = False
            cases.append(entry)
            continue
        if (
            not isinstance(baseline_entry, dict)
            or baseline_entry.get("status") != "captured"
            or baseline_entry.get("validation", {}).get("status") != "pass"
            or not isinstance(baseline_entry.get("result_path"), str)
        ):
            entry["reason"] = "frozen_independent_baseline_is_unavailable"
            conditions_match = False
            cases.append(entry)
            continue
        run_status = _run_independent_eval(
            case=independent_case,
            baseline=baseline,
            profile=profile,
            profile_path=profile_path,
            evidence_root=evidence_root,
            destination=candidate_root,
            candidate_package=candidate_package,
            timeout_seconds=max(0, int(deadline - time.monotonic())),
        )
        entry["run"] = run_status
        if run_status.get("status") != "captured":
            entry["reason"] = run_status.get(
                "reason", "candidate_independent_eval_unavailable"
            )
            conditions_match = False
            fixed_candidate_fingerprint = False
            cases.append(entry)
            continue
        candidate_path = Path(run_status["result_path"])
        baseline_path = Path(baseline_entry["result_path"])
        comparison_path = candidate_root / "comparison.json"
        try:
            comparison = compare_runs(baseline_path, candidate_path)
            atomic_write_json(comparison_path, comparison)
            assessment = _assess_independent_case(
                baseline_path=baseline_path,
                candidate_path=candidate_path,
                case=independent_case,
                profile=profile,
                baseline_package_fingerprint=independent_case[
                    "baseline_package_fingerprint"
                ],
                candidate_package_fingerprint=candidate_package_fingerprint,
                comparison=comparison,
                baseline_runtime_source_root=baseline_runtime_source_root,
                candidate_runtime_source_root=(
                    candidate_package
                    if baseline_runtime_source_root is not None
                    else None
                ),
            )
        except (AgentEvalError, OSError, TypeError, ValueError, KeyError) as exc:
            assessment = {
                "status": "review_pending",
                "conditions_match": False,
                "no_new_regressions": False,
                "reason": sanitize_diagnostic(str(exc), 500),
            }
        entry.update(
            {
                "status": assessment.get("status", "review_pending"),
                "candidate_result_path": str(candidate_path),
                "comparison_path": str(comparison_path),
                "conditions_match": assessment.get("conditions_match") is True,
                "no_new_regressions": assessment.get("no_new_regressions") is True,
                "reason": assessment.get("reason"),
            }
        )
        conditions_match = conditions_match and entry["conditions_match"]
        case_fingerprint_fixed = (
            assessment.get("candidate_package_fingerprint")
            == candidate_package_fingerprint
        )
        fixed_candidate_fingerprint = (
            fixed_candidate_fingerprint and case_fingerprint_fixed
        )
        if not case_fingerprint_fixed:
            entry["status"] = "review_pending"
            entry["reason"] = "candidate_package_fingerprint_changed"
        cases.append(entry)
    all_pass = (
        bool(cases)
        and len(cases) == len(plan.get("cases", []))
        and all(row.get("status") == "pass" for row in cases)
    )
    return {
        "status": "pass" if all_pass else "review_pending",
        "planned": len(plan.get("cases", [])),
        "cases": cases,
        "conditions_match": conditions_match
        and len(cases) == len(plan.get("cases", [])),
        "candidate_fingerprint_fixed": fixed_candidate_fingerprint and all_pass,
        "expected_inputs_disclosed": False,
        "expected_results_disclosed": False,
        "feedback_to_repair_agent": False,
    }


def _improvement_requirements(
    *,
    target_improved: bool,
    no_critical_regressions: bool,
    skill_use_verified: bool,
    target_conditions_match: bool,
    independent_assessment: dict[str, Any] | None,
    contract_test_assessment: dict[str, Any] | None,
) -> dict[str, Any]:
    independent_cases = (
        independent_assessment.get("cases")
        if isinstance(independent_assessment, dict)
        else None
    )
    independent_passed = bool(
        isinstance(independent_assessment, dict)
        and independent_assessment.get("status") == "pass"
        and isinstance(independent_cases, list)
        and independent_cases
        and independent_assessment.get("planned") == len(independent_cases)
        and all(
            isinstance(row, dict) and row.get("status") == "pass"
            for row in independent_cases
        )
    )
    independent_isolated = bool(
        isinstance(independent_assessment, dict)
        and independent_assessment.get("expected_inputs_disclosed") is False
        and independent_assessment.get("expected_results_disclosed") is False
        and independent_assessment.get("feedback_to_repair_agent") is False
        and independent_assessment.get("candidate_fingerprint_fixed") is True
        and independent_assessment.get("conditions_match") is True
    )
    contract_tests_passed = bool(
        isinstance(contract_test_assessment, dict)
        and contract_test_assessment.get("status") == "pass"
        and isinstance(contract_test_assessment.get("results"), list)
        and contract_test_assessment.get("planned", 0) > 0
        and contract_test_assessment.get("conditions_match") is True
        and contract_test_assessment.get("completed")
        == contract_test_assessment.get("planned")
        and len(contract_test_assessment["results"])
        == contract_test_assessment.get("planned")
        and all(
            isinstance(row, dict) and row.get("status") == "pass"
            for row in contract_test_assessment.get("results", [])
        )
    )
    return {
        "target_improved": target_improved,
        "no_critical_regressions": no_critical_regressions,
        "skill_use_verified": skill_use_verified,
        "target_conditions_match": target_conditions_match,
        "independent_cases_passed": independent_passed,
        "independent_information_isolated": independent_isolated,
        "contract_tests_passed": contract_tests_passed,
        "improvement_demonstrated": all(
            (
                target_improved,
                no_critical_regressions,
                skill_use_verified,
                target_conditions_match,
                independent_passed,
                independent_isolated,
                contract_tests_passed,
            )
        ),
    }


def _assess_improvement(
    baseline: Path,
    candidate: Path,
    skill: str,
    criterion: str,
    *,
    comparison: dict[str, Any],
    independent_assessment: dict[str, Any] | None = None,
    contract_test_assessment: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not comparison.get("comparable"):
        return {
            "target_criterion_ratings": [],
            "target_progress_consistently": False,
            "target_improved_consistently": False,
            "no_critical_regressions": False,
            "skill_use_observation": {"baseline": [], "candidate": []},
            "improvement_demonstrated": False,
            "reason": "baseline and candidate do not have matching evaluation conditions",
        }
    before = _load_json(baseline)
    after = _load_json(candidate)
    left_attempts = _attempt_data(before, baseline.parent)
    right_attempts = _attempt_data(after, candidate.parent)
    left_rows = [row["attempt"] for row in left_attempts]
    right_rows = [row["attempt"] for row in right_attempts]
    if len(left_rows) != len(right_rows):
        return {
            "target_criterion_ratings": [],
            "target_progress_consistently": False,
            "target_improved_consistently": False,
            "no_critical_regressions": False,
            "skill_use_observation": {"baseline": [], "candidate": []},
            "improvement_demonstrated": False,
            "reason": "baseline and candidate repeat counts differ",
        }
    criterion_statuses = []
    no_critical_regressions = True
    for left, right in zip(left_attempts, right_attempts, strict=True):
        left_judge = _load_json(left["root"] / "judge-result.json").get(
            "normalized", {}
        )
        right_judge = _load_json(right["root"] / "judge-result.json").get(
            "normalized", {}
        )
        left_criteria = {row["id"]: row for row in left_judge.get("criteria", [])}
        right_criteria = {row["id"]: row for row in right_judge.get("criteria", [])}
        target_left = left_criteria.get(criterion, {}).get("rating")
        target_right = right_criteria.get(criterion, {}).get("rating")
        criterion_statuses.append({"baseline": target_left, "candidate": target_right})
        for criterion_id, row in left_criteria.items():
            if row.get("critical"):
                if criterion_id not in right_criteria or right_criteria[
                    criterion_id
                ].get("rating", 0) < row.get("rating", 0):
                    no_critical_regressions = False
    target_progress = len(criterion_statuses) >= 2 and all(
        row["baseline"] == 1 and row["candidate"] is not None and row["candidate"] > 1
        for row in criterion_statuses
    )
    target_improved = target_progress and all(
        row["candidate"] >= 3 for row in criterion_statuses
    )
    baseline_use = [_skill_use_for_attempt(row, skill) for row in left_rows]
    candidate_use = [_skill_use_for_attempt(row, skill) for row in right_rows]
    usage_verified = bool(
        baseline_use
        and candidate_use
        and all(value == "observed" for value in baseline_use + candidate_use)
    )
    requirements = _improvement_requirements(
        target_improved=target_improved,
        no_critical_regressions=no_critical_regressions,
        skill_use_verified=usage_verified,
        target_conditions_match=comparison.get("comparable") is True,
        independent_assessment=independent_assessment,
        contract_test_assessment=contract_test_assessment,
    )
    unmet = [key for key, value in requirements.items() if value is False]
    return {
        "target_criterion_ratings": criterion_statuses,
        "target_progress_consistently": target_progress,
        "target_improved_consistently": target_improved,
        "no_critical_regressions": no_critical_regressions,
        "skill_use_observation": {"baseline": baseline_use, "candidate": candidate_use},
        "independent_regression_status": (
            independent_assessment.get("status", "review_pending")
            if isinstance(independent_assessment, dict)
            else "not_run"
        ),
        "contract_test_status": (
            contract_test_assessment.get("status", "review_pending")
            if isinstance(contract_test_assessment, dict)
            else "not_run"
        ),
        "requirements": requirements,
        "improvement_demonstrated": requirements["improvement_demonstrated"],
        "reason": None
        if requirements["improvement_demonstrated"]
        else "unmet_improvement_requirements:" + ",".join(unmet),
    }


def _assess_deterministic_improvement(
    baseline: dict[str, Any],
    candidate: dict[str, Any],
    *,
    comparison: dict[str, Any],
    independent_assessment: dict[str, Any] | None = None,
    contract_test_assessment: dict[str, Any] | None = None,
) -> dict[str, Any]:
    target_ids = baseline.get("failed_assertion_ids")
    before = baseline.get("attempts")
    after = candidate.get("attempts")
    if (
        not comparison.get("comparable")
        or not isinstance(target_ids, list)
        or not target_ids
        or not isinstance(before, list)
        or not isinstance(after, list)
        or len(before) != 2
        or len(after) != 2
        or candidate.get("skill") != baseline.get("skill")
        or candidate.get("eval_id") != baseline.get("eval_id")
        or candidate.get("input_fingerprint") != baseline.get("input_fingerprint")
        or candidate.get("dataset_fingerprint") != baseline.get("dataset_fingerprint")
    ):
        return {
            "target_assertion_statuses": [],
            "target_progress_consistently": False,
            "target_improved_consistently": False,
            "no_critical_regressions": False,
            "skill_use_observation": {"baseline": [], "candidate": []},
            "improvement_demonstrated": False,
            "reason": "deterministic baseline and candidate evidence is not comparable",
        }
    target_statuses = []
    no_regressions = True
    score = {"fail": 0, "warning": 1, "pass": 2}
    for left, right in zip(before, after, strict=True):
        left_snapshot = left["snapshot"]
        right_snapshot = right["snapshot"]
        if set(left_snapshot) != set(right_snapshot):
            no_regressions = False
            continue
        if any(
            score[right_snapshot[key]] < score[left_snapshot[key]]
            for key in left_snapshot
        ):
            no_regressions = False
        target_statuses.append(
            {
                assertion_id: right_snapshot.get(assertion_id)
                for assertion_id in target_ids
            }
        )
    target_progress = bool(target_statuses) and all(
        all(
            isinstance(status, str) and score[status] > score["fail"]
            for status in row.values()
        )
        for row in target_statuses
    )
    target_improved = target_progress and all(
        all(status == "pass" for status in row.values()) for row in target_statuses
    )
    target_improved = target_improved and all(
        row["grade"].get("status") == "pass" for row in after
    )
    baseline_use = [row["attempt"]["skill_use_observation"] for row in before]
    candidate_use = [row["attempt"]["skill_use_observation"] for row in after]
    skill_use_verified = bool(
        baseline_use
        and candidate_use
        and all(value == "observed" for value in baseline_use + candidate_use)
    )
    requirements = _improvement_requirements(
        target_improved=target_improved,
        no_critical_regressions=no_regressions,
        skill_use_verified=skill_use_verified,
        target_conditions_match=comparison.get("comparable") is True,
        independent_assessment=independent_assessment,
        contract_test_assessment=contract_test_assessment,
    )
    unmet = [key for key, value in requirements.items() if value is False]
    return {
        "target_assertion_ids": target_ids,
        "target_assertion_statuses": target_statuses,
        "target_progress_consistently": target_progress,
        "target_improved_consistently": target_improved,
        "no_critical_regressions": no_regressions,
        "skill_use_observation": {"baseline": baseline_use, "candidate": candidate_use},
        "independent_regression_status": (
            independent_assessment.get("status", "review_pending")
            if isinstance(independent_assessment, dict)
            else "not_run"
        ),
        "contract_test_status": (
            contract_test_assessment.get("status", "review_pending")
            if isinstance(contract_test_assessment, dict)
            else "not_run"
        ),
        "requirements": requirements,
        "improvement_demonstrated": requirements["improvement_demonstrated"],
        "reason": None
        if requirements["improvement_demonstrated"]
        else "unmet_improvement_requirements:" + ",".join(unmet),
    }


def _write_analysis_artifacts(case_root: Path, case_record: dict[str, Any]) -> None:
    analysis = case_record.get("analysis", {})
    decision = case_record.get("analysis_decision", {})
    verified_fixture = case_record.get("verified_judge_fixture")
    saved = {
        "schema_version": 1,
        "criterion": case_record.get("criterion"),
        "status": case_record.get("status"),
        "blocked_reason": case_record.get("blocked_reason"),
        "verified_judge_fixture": verified_fixture,
        "observations": case_record.get("observations", []),
        "analysis_status": analysis.get("status"),
        "analysis_prompt_sha256": analysis.get("prompt_sha256"),
        "analysis_response_sha256": analysis.get("response_sha256"),
        "analysis_response": analysis.get("response"),
        "decision": decision,
        "repair_trials": case_record.get("repair_trials", []),
    }
    atomic_write_json(case_root / "analysis.json", saved)
    lines = [
        f"# 改善分析: {case_record.get('criterion', 'unknown')}",
        "",
        f"- 状態: {case_record.get('status', 'unknown')}",
        "- Judge検証fixture: "
        + (
            str(verified_fixture.get("case_id", "未指定"))
            if isinstance(verified_fixture, dict)
            else "不要（deterministic-only）"
            if case_record.get("evidence_basis") == "deterministic_only"
            else "未指定"
        ),
        f"- 停止理由: {case_record.get('blocked_reason', 'なし')}",
        "",
        "## 分析Agentの判定",
        "",
        f"- 分類: {decision.get('classification', '未確定')}",
        f"- 対象Skill: {decision.get('skill', '未確定')}",
        f"- 問題: {decision.get('issue', '分析結果なし')}",
        f"- 修正方針: {decision.get('repair_rationale', '未確定')}",
        "",
        "### 根拠",
        "",
        *[f"- {item}" for item in decision.get("evidence", [])],
        "",
        "### 他の原因候補",
        "",
        *[f"- {item}" for item in decision.get("alternative_causes", [])],
        "",
        "### 許可path候補",
        "",
        *[f"- `{item}`" for item in decision.get("repair_paths", [])],
        "",
        "原判定、artifact、固定Referenceはこの記録から変更していません。"
        "Agent responseはJSON側に安全化済みで保存します。",
    ]
    (case_root / "analysis.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _run_deterministic_improvements(
    *,
    baseline_result: Path,
    baseline: dict[str, Any],
    profile_path: Path,
    output_root: Path,
    max_cases: int,
    max_repairs: int,
    max_seconds: int,
    analyze_only: bool,
) -> dict[str, Any]:
    from .compare import compare_runs

    started = time.monotonic()
    run_root = baseline_result.parent.resolve()
    output_root = Path(os.path.abspath(output_root))
    profile = load_execution_profile(profile_path)
    evidence_relative = safe_relative_path(profile["verification"]["evidence_path"])
    evidence_destination = prepare_run_output_root(
        output_root,
        repository_root=REPO_ROOT,
        evidence_relative_path=profile["verification"]["evidence_path"],
    )
    result: dict[str, Any] = {
        "schema_version": 1,
        "status": "running",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "baseline_result": str(baseline_result),
        "suite": "deterministic",
        "evidence_basis": "deterministic_only",
        "judge_required": False,
        "judge_validation_result": None,
        "evaluator_revision": None,
        "skill_revision": baseline.get("skill_revision"),
        "baseline_package_fingerprint": None,
        "limits": {
            "max_cases": max_cases,
            "max_repairs": max_repairs,
            "max_seconds": max_seconds,
        },
        "analyze_only": analyze_only,
        "repair_attempts_started": 0,
        "cases": [],
    }

    def finish_pending(
        reason: str, *, case_id: str = "baseline-evidence"
    ) -> dict[str, Any]:
        result["cases"].append(
            {
                "criterion": case_id,
                "status": "review_pending",
                "blocked_reason": sanitize_diagnostic(reason, 500),
                "repair_attempts_started": 0,
            }
        )
        result["status"] = "review_pending_or_unmet"
        result["finished_at"] = datetime.now(timezone.utc).isoformat()
        result["elapsed_seconds"] = round(time.monotonic() - started, 3)
        atomic_write_json(output_root / "result.json", result)
        return result

    try:
        evaluator_revision = assert_clean_checkout(REPO_ROOT)
        evaluator = baseline.get("evaluator")
        template = baseline.get("agent_command_template")
        if (
            not isinstance(evaluator, dict)
            or evaluator.get("revision") != evaluator_revision
            or baseline.get("profile_verification") != "verified"
            or baseline.get("profile_fingerprint") != profile_fingerprint(profile)
            or not isinstance(baseline.get("agent"), dict)
            or baseline["agent"].get("name") != profile["agent"].get("name")
            or baseline["agent"].get("model") != profile["agent"].get("model")
            or baseline["agent"].get("cli_version")
            != profile["agent"].get("cli_version")
            or baseline.get("judge_command_fingerprint")
            != canonical_fingerprint(profile["judge"].get("command_argv", []))
            or not isinstance(baseline.get("isolation"), dict)
            or baseline["isolation"].get("method") != profile["isolation"].get("method")
            or baseline["isolation"].get("agent_read_roots")
            != profile["isolation"].get("agent_read_roots")
            or baseline["isolation"].get("evaluator_read_blocked")
            != profile["isolation"].get("evaluator_read_blocked")
            or not isinstance(baseline.get("skill_revision"), str)
            or not isinstance(template, list)
            or not template
            or baseline.get("agent_command_fingerprint")
            != canonical_fingerprint(template)
            or _has_secret_command_argument(template)
        ):
            raise AgentEvalError(
                "deterministic baseline provenance is incomplete or mixed"
            )
        evidence_source = _resolve_run_path(run_root, evidence_relative.as_posix())
        if not evidence_source.is_file():
            raise AgentEvalError("deterministic baseline isolation evidence is missing")
        if not evidence_destination.exists():
            evidence_destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(evidence_source, evidence_destination)
        if not verify_profile_evidence(
            profile, output_root, agent_command_argv=template
        ):
            raise AgentEvalError("deterministic baseline isolation is unverified")
        with tempfile.TemporaryDirectory(
            prefix="agent-eval-deterministic-baseline-"
        ) as temporary:
            trusted_baseline_package = Path(temporary)
            trusted_manifest = create_skill_workspace(
                REPO_ROOT, baseline["skill_revision"], trusted_baseline_package
            )
            if baseline.get("skill_package", {}).get(
                "package_fingerprint"
            ) != trusted_manifest.get("package_fingerprint") or baseline.get(
                "skill_package", {}
            ).get("skills") != trusted_manifest.get("skills"):
                raise AgentEvalError("deterministic baseline Skill package changed")
            failure = _deterministic_attempt_data(
                baseline,
                run_root,
                runtime_source_root=trusted_baseline_package,
                expected_package_fingerprint=trusted_manifest["package_fingerprint"],
            )
        result["evaluator_revision"] = evaluator_revision
        result["baseline_package_fingerprint"] = trusted_manifest["package_fingerprint"]
        result["profile_fingerprint"] = profile_fingerprint(profile)
        result["grader_evidence"] = {
            "status": "recomputed_match",
            "recomputed_from_preserved_outputs": True,
            "input_fingerprint": failure["input_fingerprint"],
            "dataset_fingerprint": failure["dataset_fingerprint"],
            "judge_used": False,
        }
    except (
        AgentEvalError,
        ImportError,
        OSError,
        ValueError,
        KeyError,
        TypeError,
    ) as exc:
        return finish_pending(str(exc))

    if not failure["failed_assertion_ids"]:
        return finish_pending(
            "deterministic grader did not reproduce a failing assertion",
            case_id=f"{failure['skill']}:{failure['eval_id']}",
        )

    experiment_id = (
        f"improve-deterministic-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
        f"-{os.urandom(4).hex()}"
    )
    experiment_root = output_root / "experiments" / experiment_id
    experiment_root.mkdir(parents=True, exist_ok=False)
    case_key = f"{failure['skill']}:{failure['eval_id']}"
    case_root = experiment_root / sha256_bytes(case_key.encode("utf-8"))[7:23]
    case_root.mkdir()
    result["experiment_id"] = experiment_id
    result["cases"] = []
    case_record: dict[str, Any] = {
        "criterion": case_key,
        "suite": "deterministic",
        "skill": failure["skill"],
        "eval_id": failure["eval_id"],
        "failed_assertion_ids": failure["failed_assertion_ids"],
        "input_fingerprint": failure["input_fingerprint"],
        "dataset_fingerprint": failure["dataset_fingerprint"],
        "evidence_basis": "deterministic_only",
        "judge_required": False,
        "verified_judge_fixture": None,
        "observations": [
            {
                "attempt_id": row["attempt"].get("attempt_id"),
                "repeat": row["attempt"].get("repeat"),
                "failed_assertion_ids": failure["failed_assertion_ids"],
            }
            for row in failure["attempts"]
        ],
        "status": "analysis_pending",
        "repair_trials": [],
        "skill_use_observation": [
            row["attempt"]["skill_use_observation"] for row in failure["attempts"]
        ],
    }
    baseline_package = case_root / "baseline-package"
    try:
        baseline_manifest = create_skill_workspace(
            REPO_ROOT, baseline["skill_revision"], baseline_package
        )
        if (
            baseline_manifest["package_fingerprint"]
            != result["baseline_package_fingerprint"]
        ):
            raise AgentEvalError(
                "deterministic baseline package changed before analysis"
            )
        independent_plan = _freeze_independent_eval_plan(
            skill=failure["skill"],
            evaluator_revision=evaluator_revision,
            skill_revision=baseline["skill_revision"],
            baseline_package_fingerprint=baseline_manifest["package_fingerprint"],
            profile=profile,
            agent_command=template,
        )
        independent_plan["cases"] = [
            row
            for row in independent_plan.get("cases", [])
            if not (
                row.get("suite") == "deterministic"
                and row.get("case_id") == failure["eval_id"]
            )
            and row.get("input_fingerprint") != failure["input_fingerprint"]
        ]
        deterministic_independent_cases = [
            row
            for row in independent_plan["cases"]
            if row.get("suite") == "deterministic"
        ]
        independent_plan["status"] = (
            "ready"
            if deterministic_independent_cases and independent_plan["contract_tests"]
            else "blocked"
        )
        independent_plan["block_reason"] = (
            None
            if independent_plan["status"] == "ready"
            else "no_independent_deterministic_case_or_related_contract_test"
        )
        for row in independent_plan["cases"]:
            if row.get("suite") == "semantic":
                row["verification_status"] = "judge_unverified"
                row["block_reason"] = (
                    "semantic_independent_case_requires_verified_judge"
                )
        case_record["independent_regression_plan"] = independent_plan
        case_record["independent_evaluation_isolation"] = {
            "repair_agent_received_independent_inputs": False,
            "repair_agent_received_expected_results": False,
            "independent_results_returned_for_repair": False,
        }
        case_record["fixed_evaluator_baseline_package_fingerprint"] = baseline_manifest[
            "package_fingerprint"
        ]
        baseline_contract_assessment = _run_related_contract_tests(
            independent_plan["contract_tests"],
            timeout_seconds=max(0, int(max_seconds - (time.monotonic() - started))),
            evaluator_revision=evaluator_revision,
            skill=failure["skill"],
            skill_revision=baseline["skill_revision"],
            expected_skills=set(baseline_manifest["skills"]),
            candidate_package=baseline_package,
            candidate_package_fingerprint=baseline_manifest["package_fingerprint"],
        )
        case_record["baseline_contract_test_assessment"] = baseline_contract_assessment
        if baseline_contract_assessment.get("status") != "pass":
            raise AgentEvalError(
                "fixed deterministic grader or related baseline contract test failed"
            )
        result["grader_evidence"]["status"] = "verified"
    except (
        AgentEvalError,
        ImportError,
        OSError,
        ValueError,
        KeyError,
        TypeError,
    ) as exc:
        case_record["status"] = "review_pending"
        case_record["blocked_reason"] = sanitize_diagnostic(str(exc), 500)
        result["cases"].append(case_record)
        _write_analysis_artifacts(case_root, case_record)
        atomic_write_json(case_root / "case.json", case_record)
        result["status"] = "review_pending_or_unmet"
        result["finished_at"] = datetime.now(timezone.utc).isoformat()
        result["elapsed_seconds"] = round(time.monotonic() - started, 3)
        atomic_write_json(output_root / "result.json", result)
        return result

    analysis_workspace = case_root / "analysis-workspace"
    analysis_workspace.mkdir()
    (analysis_workspace / ".qa-eval-output").mkdir()
    try:
        evidence_sources, inspected_sources, source_manifest = (
            _prepare_deterministic_analysis_workspace(
                workspace=analysis_workspace,
                failure=failure,
                package_root=baseline_package,
            )
        )
    except (AgentEvalError, OSError, UnicodeDecodeError) as exc:
        case_record["status"] = "review_pending"
        case_record["blocked_reason"] = sanitize_diagnostic(str(exc), 500)
        result["cases"].append(case_record)
        _write_analysis_artifacts(case_root, case_record)
        atomic_write_json(case_root / "case.json", case_record)
        result["status"] = "review_pending_or_unmet"
        result["finished_at"] = datetime.now(timezone.utc).isoformat()
        result["elapsed_seconds"] = round(time.monotonic() - started, 3)
        atomic_write_json(output_root / "result.json", result)
        return result

    prompt_evidence = {
        "baseline_run_id": baseline.get("run_id"),
        "attempt_ids": [
            row["attempt"].get("attempt_id") for row in failure["attempts"]
        ],
        "suite": "deterministic",
        "failed_assertion_ids": failure["failed_assertion_ids"],
        "evaluator_revision": evaluator_revision,
        "skill_revision": baseline["skill_revision"],
        "grader_status": "fixed_grader_recomputed_and_matched_saved_results",
        "grader_contract_tests": "pass",
        "agent_execution_status": "pass",
        "isolation_status": "verified",
        "attempt_runtime_evidence": [
            {
                "attempt_id": row["attempt"].get("attempt_id"),
                "exit_code": row["attempt"].get("agent_execution", {}).get("exit_code"),
                "timed_out": row["attempt"].get("agent_execution", {}).get("timed_out"),
                "container_cleanup_status": row["attempt"]
                .get("agent_execution", {})
                .get("container_cleanup_status"),
                "trace_status": row["attempt"].get("agent_trace", {}).get("status"),
                "trace_skill_files_read": [
                    skill
                    for command in _load_json(row["trace_path"]).get("commands", [])
                    if isinstance(command, dict) and command.get("successful") is True
                    for skill in command.get("skill_files_read", [])
                    if isinstance(skill, str)
                ],
            }
            for row in failure["attempts"]
        ],
        "skill_use_observations": {
            failure["skill"]: [
                row["attempt"]["skill_use_observation"] for row in failure["attempts"]
            ]
        },
        "inspected_sources": source_manifest,
        "evaluator_only_expected_data": "withheld",
        "semantic_or_mixed_evidence": "not_used",
        "judge_validation": "not_required_for_deterministic_only_basis",
    }
    analysis_prompt = build_analysis_prompt(
        case_id=case_key,
        evidence=json.dumps(prompt_evidence, ensure_ascii=False),
        skill_excerpt=inspected_sources,
    )
    analysis_command = [
        item.replace("{workspace}", str(analysis_workspace)).replace(
            "{output_root}", str(analysis_workspace / ".qa-eval-output")
        )
        for item in template
    ]
    analysis_isolation = verify_agent_docker_command(
        analysis_command,
        workspace=analysis_workspace,
        output_root=analysis_workspace / ".qa-eval-output",
        evaluator_root=REPO_ROOT,
    )
    if analysis_isolation.get("status") != "verified":
        case_record["status"] = "review_pending"
        case_record["blocked_reason"] = "analysis_agent_isolation_unverified"
        result["cases"].append(case_record)
        _write_analysis_artifacts(case_root, case_record)
        atomic_write_json(case_root / "case.json", case_record)
        result["status"] = "review_pending_or_unmet"
        atomic_write_json(output_root / "result.json", result)
        return result
    analysis_named, analysis_cleanup = named_container_command(
        analysis_command,
        name=f"agent-eval-analysis-{experiment_id[-8:]}-deterministic",
    )
    analysis_execution_command = analysis_named
    if profile["agent"]["name"].lower() == "codex":
        analysis_execution_command = launcher_argv(
            output_root=analysis_workspace / ".qa-eval-output",
            model=profile["agent"]["model"],
            reasoning_effort=profile["agent"]["reasoning_effort"],
            cli_version=profile["agent"]["cli_version"],
            sandbox_policy=profile["agent"]["sandbox_policy"],
            docker_argv=analysis_named,
        )
    try:
        analysis_run = run_command(
            analysis_execution_command,
            input_text=analysis_prompt,
            cwd=analysis_workspace,
            timeout_seconds=min(
                profile["agent"]["timeout_seconds"],
                max(1, int(max_seconds - (time.monotonic() - started))),
            ),
            timeout_cleanup_argv=analysis_cleanup,
        )
    except (AgentExecutionError, AgentEvalError, OSError) as exc:
        case_record["status"] = "review_pending"
        case_record["blocked_reason"] = sanitize_diagnostic(
            f"analysis_environment_error: {exc}", 500
        )
        result["cases"].append(case_record)
        _write_analysis_artifacts(case_root, case_record)
        atomic_write_json(case_root / "case.json", case_record)
        result["status"] = "review_pending_or_unmet"
        result["finished_at"] = datetime.now(timezone.utc).isoformat()
        result["elapsed_seconds"] = round(time.monotonic() - started, 3)
        atomic_write_json(output_root / "result.json", result)
        return result
    analysis_trace = capture_codex_jsonl_trace(
        analysis_run.stdout, skill_names=[failure["skill"]]
    )
    analysis_safe = sanitize_diagnostic(analysis_trace["final_message"])
    launcher_unverified = (
        analysis_trace.get("launcher_observations") is not None
        and analysis_trace.get("execution_status") != "completed"
    )
    analysis_trace_path = None
    if analysis_trace["trace_summary"].get("status") == "captured":
        analysis_trace_path = "analysis-trace.json"
        atomic_write_json(
            case_root / analysis_trace_path, analysis_trace["trace_summary"]
        )
    case_record["analysis"] = {
        "status": "captured"
        if not analysis_run.timed_out
        and analysis_run.exit_code == 0
        and analysis_run.cleanup_status == "succeeded"
        and not analysis_trace["redacted"]
        and not launcher_unverified
        else "execution_error",
        "response": analysis_safe,
        "response_sha256": sha256_bytes(analysis_safe.encode("utf-8")),
        "trace_format": analysis_trace["format"],
        "trace_status": analysis_trace["status"],
        "trace_path": analysis_trace_path,
        "codex_launcher_evidence": analysis_trace.get("launcher_observations"),
        "prompt_sha256": sha256_bytes(analysis_prompt.encode("utf-8")),
        "isolation": analysis_isolation,
        "container_cleanup_status": analysis_run.cleanup_status,
    }
    if case_record["analysis"]["status"] != "captured":
        case_record["status"] = "review_pending"
        case_record["blocked_reason"] = "analysis_execution_or_trace_unverified"
        result["cases"].append(case_record)
        _write_analysis_artifacts(case_root, case_record)
        atomic_write_json(case_root / "case.json", case_record)
        result["status"] = "review_pending_or_unmet"
        atomic_write_json(output_root / "result.json", result)
        return result
    try:
        analysis = _validate_analysis(
            analysis_safe,
            skill_names={failure["skill"]},
            criterion=case_key,
            evidence_sources=evidence_sources,
        )
        repair_gate = _analysis_repair_gate(
            analysis,
            allowed_skills={failure["skill"]},
            attempts=failure["attempts"],
            evidence_sources=evidence_sources,
            package_root=baseline_package,
        )
    except (AgentEvalError, TypeError, ValueError) as exc:
        case_record["status"] = "review_pending"
        case_record["blocked_reason"] = sanitize_diagnostic(str(exc), 500)
        result["cases"].append(case_record)
        _write_analysis_artifacts(case_root, case_record)
        atomic_write_json(case_root / "case.json", case_record)
        result["status"] = "review_pending_or_unmet"
        atomic_write_json(output_root / "result.json", result)
        return result
    case_record["analysis_decision"] = repair_gate
    if not repair_gate["allowed"]:
        case_record["status"] = "review_pending"
        case_record["blocked_reason"] = ";".join(repair_gate["reasons"])
    elif analyze_only:
        case_record["status"] = "analysis_complete_review_pending"
        case_record["blocked_reason"] = "analyze_only_requested"
    elif independent_plan.get("status") != "ready":
        case_record["status"] = "review_pending"
        case_record["blocked_reason"] = independent_plan.get("block_reason")
    else:
        chosen_skill = repair_gate["skill"]
        requested_paths = set(repair_gate["requested_paths"])
        independent_baseline_results: list[dict[str, Any]] = []
        independent_baseline_failed = False
        for independent_case in independent_plan["cases"]:
            if independent_case.get("suite") == "semantic":
                independent_baseline_results.append(
                    {
                        "case": independent_case,
                        "status": "review_pending",
                        "reason": "semantic_independent_case_requires_verified_judge",
                        "judge_validation_status": "judge_unverified",
                    }
                )
                case_record["independent_baseline_results"] = (
                    independent_baseline_results
                )
                atomic_write_json(case_root / "case.json", case_record)
                continue
            key = f"{independent_case['suite']}:{independent_case['case_id']}"
            safe_key = sha256_bytes(key.encode("utf-8"))[7:23]
            destination = case_root / "independent-baseline" / safe_key
            run_status = _run_independent_eval(
                case=independent_case,
                baseline=baseline,
                profile=profile,
                profile_path=profile_path,
                evidence_root=output_root,
                destination=destination,
                timeout_seconds=max(0, int(max_seconds - (time.monotonic() - started))),
            )
            entry = {"case": independent_case, **run_status}
            if run_status.get("status") == "captured":
                validation = _validate_independent_run(
                    Path(run_status["result_path"]),
                    case=independent_case,
                    profile=profile,
                    package_fingerprint=baseline_manifest["package_fingerprint"],
                    candidate=False,
                    runtime_source_root=baseline_package,
                )
                entry["validation"] = {
                    "status": validation["status"],
                    "reason": validation.get("reason"),
                }
                if validation["status"] != "pass":
                    entry["status"] = "review_pending"
                    entry["reason"] = validation.get("reason")
            if entry.get("status") != "captured":
                independent_baseline_failed = True
            independent_baseline_results.append(entry)
            case_record["independent_baseline_results"] = independent_baseline_results
            atomic_write_json(case_root / "case.json", case_record)
            if independent_baseline_failed:
                break
        if independent_baseline_failed:
            case_record["status"] = "review_pending"
            case_record["blocked_reason"] = (
                "independent_deterministic_baseline_evaluation_unavailable_or_invalid"
            )
        elif not requested_paths:
            case_record["status"] = "review_pending"
            case_record["blocked_reason"] = "analysis_requested_no_repair_path"
        else:
            package_path = baseline_package
            package_manifest = baseline_manifest
            for repair_index in range(1, max_repairs + 1):
                if time.monotonic() - started >= max_seconds:
                    case_record["status"] = "stopped_by_time_limit"
                    case_record["blocked_reason"] = "time_budget_exhausted"
                    break
                required_seconds = 2 * (profile["agent"]["timeout_seconds"] + 60)
                if max_seconds - (time.monotonic() - started) < required_seconds:
                    case_record["status"] = "stopped_by_time_limit"
                    case_record["blocked_reason"] = (
                        "insufficient_budget_for_two_candidate_attempts"
                    )
                    break
                trial_root = case_root / "repair-trials" / f"trial-{repair_index:02d}"
                trial_root.mkdir(parents=True)
                repair_workspace = trial_root / "workspace"
                (repair_workspace / ".agents" / "skills").mkdir(parents=True)
                visible_paths = _copy_allowed_skill_files(
                    package_path, repair_workspace / ".agents" / "skills", chosen_skill
                )
                repair_output = repair_workspace / ".qa-eval-output"
                repair_output.mkdir()
                skill_root = repair_workspace / ".agents" / "skills" / chosen_skill
                before = _source_paths(package_path, chosen_skill)
                allowed_for_prompt = [
                    f"{chosen_skill}/{path}" for path in sorted(requested_paths)
                ]
                repair_prompt = build_repair_prompt(
                    analysis=json.dumps(analysis, ensure_ascii=False),
                    allowed_paths=allowed_for_prompt,
                    baseline_sha=baseline["skill_revision"],
                )
                repair_command = [
                    item.replace("{workspace}", str(repair_workspace)).replace(
                        "{output_root}", str(repair_output)
                    )
                    for item in template
                ]
                repair_mount = (
                    "type=bind,source="
                    f"{skill_root},target=/workspace/.agents/skills/{chosen_skill}"
                )
                repair_command = _insert_mount_before_image(
                    repair_command, repair_mount
                )
                repair_isolation = verify_repair_docker_command(
                    repair_command,
                    workspace=repair_workspace,
                    skill_root=skill_root,
                    output_root=repair_output,
                    skill_name=chosen_skill,
                )
                trial: dict[str, Any] = {
                    "trial": repair_index,
                    "status": "repair_pending",
                    "allowed_paths": sorted(requested_paths),
                    "isolation": repair_isolation,
                    "candidate_evaluation_feedback_to_repair_agent": False,
                }
                if repair_isolation.get("status") != "verified":
                    trial["stop_reason"] = "repair_agent_isolation_unverified"
                    case_record["repair_trials"].append(trial)
                    atomic_write_json(trial_root / "trial.json", trial)
                    case_record["status"] = "review_pending"
                    case_record["blocked_reason"] = trial["stop_reason"]
                    break
                repair_named, repair_cleanup = named_container_command(
                    repair_command,
                    name=(
                        f"agent-eval-repair-{experiment_id[-8:]}-det-{repair_index:02d}"
                    ),
                )
                repair_attempt_number = result["repair_attempts_started"] + 1
                result["repair_attempts_started"] = repair_attempt_number
                case_record["repair_attempts_started"] = repair_attempt_number
                result["active_case"] = {
                    "criterion": case_key,
                    "trial": repair_index,
                    "global_repair_attempt": repair_attempt_number,
                    "status": "repair_agent_running",
                }
                atomic_write_json(output_root / "result.json", result)
                repair_execution_command = repair_named
                if profile["agent"]["name"].lower() == "codex":
                    repair_execution_command = launcher_argv(
                        output_root=repair_output,
                        model=profile["agent"]["model"],
                        reasoning_effort=profile["agent"]["reasoning_effort"],
                        cli_version=profile["agent"]["cli_version"],
                        sandbox_policy=profile["agent"]["sandbox_policy"],
                        docker_argv=repair_named,
                        mode="repair",
                        skill_name=chosen_skill,
                    )
                try:
                    repair_execution = run_command(
                        repair_execution_command,
                        input_text=repair_prompt,
                        cwd=repair_workspace,
                        timeout_seconds=min(
                            profile["agent"]["timeout_seconds"],
                            max(1, int(max_seconds - (time.monotonic() - started))),
                        ),
                        timeout_cleanup_argv=repair_cleanup,
                    )
                except (AgentExecutionError, AgentEvalError, OSError) as exc:
                    trial["status"] = "execution_error"
                    trial["stop_reason"] = sanitize_diagnostic(
                        f"repair_environment_error: {exc}", 500
                    )
                    case_record["repair_trials"].append(trial)
                    atomic_write_json(trial_root / "trial.json", trial)
                    case_record["status"] = "review_pending"
                    case_record["blocked_reason"] = trial["stop_reason"]
                    break
                repair_trace = capture_codex_jsonl_trace(repair_execution.stdout)
                repair_unverified = repair_trace["redacted"] or (
                    repair_trace.get("launcher_observations") is not None
                    and repair_trace.get("execution_status") != "completed"
                )
                if (
                    repair_execution.timed_out
                    or repair_execution.exit_code != 0
                    or repair_execution.cleanup_status != "succeeded"
                    or repair_unverified
                ):
                    trial["status"] = "execution_error"
                    trial["stop_reason"] = "repair_agent_execution_or_trace_unverified"
                    case_record["repair_trials"].append(trial)
                    atomic_write_json(trial_root / "trial.json", trial)
                    case_record["status"] = "review_pending"
                    case_record["blocked_reason"] = trial["stop_reason"]
                    break
                try:
                    changes, _after = _validate_repair_diff(
                        before,
                        repair_workspace / ".agents" / "skills",
                        chosen_skill,
                        requested_paths,
                        visible_paths=visible_paths,
                    )
                except (AgentEvalError, OSError, UnicodeDecodeError) as exc:
                    trial["status"] = "invalid_candidate"
                    trial["stop_reason"] = sanitize_diagnostic(str(exc), 500)
                    case_record["repair_trials"].append(trial)
                    atomic_write_json(trial_root / "trial.json", trial)
                    case_record["status"] = "review_pending"
                    case_record["blocked_reason"] = trial["stop_reason"]
                    break
                patch_text = "".join(
                    difflib.unified_diff(
                        (package_path / "skills" / chosen_skill / change["path"])
                        .read_text(encoding="utf-8")
                        .splitlines(keepends=True),
                        (skill_root / change["path"])
                        .read_text(encoding="utf-8")
                        .splitlines(keepends=True),
                        fromfile=f"a/skills/{chosen_skill}/{change['path']}",
                        tofile=f"b/skills/{chosen_skill}/{change['path']}",
                    )
                    for change in changes
                )
                (trial_root / "patch.diff").write_text(patch_text, encoding="utf-8")
                with zipfile.ZipFile(
                    trial_root / "changed-files.zip",
                    "w",
                    compression=zipfile.ZIP_DEFLATED,
                ) as archive:
                    for change in changes:
                        archive.write(
                            skill_root / change["path"],
                            arcname=f"skills/{chosen_skill}/{change['path']}",
                        )
                trial.update(
                    {
                        "status": "candidate_saved",
                        "candidate_revision_status": "uncommitted_patch",
                        "candidate_package_parent_revision": baseline["skill_revision"],
                        "changes": changes,
                        "patch_path": "patch.diff",
                        "changed_files_archive": "changed-files.zip",
                    }
                )
                candidate_package = trial_root / "candidate-package"
                candidate_manifest_root = trial_root / "candidate-manifest-check"
                try:
                    shutil.copytree(package_path, candidate_package)
                    for change in changes:
                        destination = (
                            candidate_package / "skills" / chosen_skill / change["path"]
                        )
                        destination.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copyfile(skill_root / change["path"], destination)
                    candidate_manifest = create_skill_workspace_from_root(
                        candidate_package,
                        candidate_manifest_root,
                        expected_skills=set(baseline_manifest["skills"]),
                        parent_revision=baseline["skill_revision"],
                    )
                except (
                    AgentEvalError,
                    OSError,
                    ValueError,
                    KeyError,
                    TypeError,
                ) as exc:
                    trial["status"] = "evidence_unverified"
                    trial["stop_reason"] = sanitize_diagnostic(str(exc), 500)
                    case_record["repair_trials"].append(trial)
                    atomic_write_json(trial_root / "trial.json", trial)
                    case_record["status"] = "review_pending"
                    case_record["blocked_reason"] = trial["stop_reason"]
                    break
                finally:
                    shutil.rmtree(candidate_manifest_root, ignore_errors=True)
                trial["candidate_package_fingerprint"] = candidate_manifest[
                    "package_fingerprint"
                ]
                if (
                    candidate_manifest["package_fingerprint"]
                    == package_manifest["package_fingerprint"]
                ):
                    trial["status"] = "invalid_candidate"
                    trial["stop_reason"] = (
                        "candidate_package_fingerprint_did_not_change"
                    )
                    case_record["repair_trials"].append(trial)
                    atomic_write_json(trial_root / "trial.json", trial)
                    case_record["status"] = "review_pending"
                    case_record["blocked_reason"] = trial["stop_reason"]
                    break

                result["active_case"]["status"] = "candidate_evaluation_running"
                result["active_case"]["candidate_package_fingerprint"] = (
                    candidate_manifest["package_fingerprint"]
                )
                atomic_write_json(output_root / "result.json", result)
                evaluation = _run_deterministic_candidate_eval(
                    baseline=baseline,
                    skill=chosen_skill,
                    eval_id=failure["eval_id"],
                    profile=profile,
                    profile_path=profile_path,
                    evidence_root=output_root,
                    destination=trial_root / "re-evaluation",
                    candidate_package=candidate_package,
                    timeout_seconds=max(
                        0, int(max_seconds - (time.monotonic() - started))
                    ),
                )
                trial["candidate_run"] = evaluation
                if evaluation.get("status") != "captured":
                    trial["status"] = "execution_error"
                    trial["stop_reason"] = evaluation.get(
                        "reason", "candidate_deterministic_evaluation_unavailable"
                    )
                    case_record["repair_trials"].append(trial)
                    atomic_write_json(trial_root / "trial.json", trial)
                    case_record["status"] = "review_pending"
                    case_record["blocked_reason"] = trial["stop_reason"]
                    break
                candidate_result_path = Path(evaluation["result_path"])
                try:
                    candidate_run = _load_json(candidate_result_path)
                    candidate_failure = _deterministic_attempt_data(
                        candidate_run,
                        candidate_result_path.parent,
                        runtime_source_root=candidate_package,
                        expected_package_fingerprint=candidate_manifest[
                            "package_fingerprint"
                        ],
                        expected_candidate_status="uncommitted_patch",
                    )
                    comparison = compare_runs(baseline_result, candidate_result_path)
                    comparison_path = trial_root / "comparison.json"
                    atomic_write_json(comparison_path, comparison)
                    target_assessment = _assess_deterministic_improvement(
                        failure, candidate_failure, comparison=comparison
                    )
                except (
                    AgentEvalError,
                    OSError,
                    TypeError,
                    ValueError,
                    KeyError,
                ) as exc:
                    trial["status"] = "evidence_unverified"
                    trial["stop_reason"] = sanitize_diagnostic(str(exc), 500)
                    case_record["repair_trials"].append(trial)
                    atomic_write_json(trial_root / "trial.json", trial)
                    case_record["status"] = "review_pending"
                    case_record["blocked_reason"] = trial["stop_reason"]
                    break
                contract_assessment = None
                independent_assessment = None
                contract_path = None
                independent_path = None
                assessment = target_assessment
                if target_assessment["target_progress_consistently"]:
                    contract_assessment = _run_related_contract_tests(
                        independent_plan["contract_tests"],
                        timeout_seconds=max(
                            0, int(max_seconds - (time.monotonic() - started))
                        ),
                        evaluator_revision=evaluator_revision,
                        skill=chosen_skill,
                        skill_revision=baseline["skill_revision"],
                        expected_skills=set(candidate_manifest["skills"]),
                        candidate_package=candidate_package,
                        candidate_package_fingerprint=candidate_manifest[
                            "package_fingerprint"
                        ],
                    )
                    contract_path = trial_root / "contract-tests.json"
                    atomic_write_json(contract_path, contract_assessment)
                    if target_assessment["target_improved_consistently"]:
                        if contract_assessment["status"] == "pass":
                            independent_assessment = (
                                _run_candidate_independent_assessment(
                                    plan=independent_plan,
                                    baseline_results=independent_baseline_results,
                                    baseline=baseline,
                                    profile=profile,
                                    profile_path=profile_path,
                                    evidence_root=output_root,
                                    case_root=trial_root,
                                    candidate_package=candidate_package,
                                    candidate_package_fingerprint=candidate_manifest[
                                        "package_fingerprint"
                                    ],
                                    baseline_runtime_source_root=baseline_package,
                                    timeout_seconds=max(
                                        0,
                                        int(max_seconds - (time.monotonic() - started)),
                                    ),
                                    compare_runs=compare_runs,
                                )
                            )
                        else:
                            independent_assessment = {
                                "status": "review_pending",
                                "planned": len(independent_plan["cases"]),
                                "cases": [
                                    {
                                        "suite": row["suite"],
                                        "case_id": row["case_id"],
                                        "status": "review_pending",
                                        "reason": (
                                            "candidate_contract_tests_did_not_pass"
                                        ),
                                    }
                                    for row in independent_plan["cases"]
                                ],
                                "conditions_match": False,
                                "candidate_fingerprint_fixed": False,
                                "expected_inputs_disclosed": False,
                                "expected_results_disclosed": False,
                                "feedback_to_repair_agent": False,
                            }
                        independent_path = trial_root / "independent-assessment.json"
                        atomic_write_json(independent_path, independent_assessment)
                    assessment = _assess_deterministic_improvement(
                        failure,
                        candidate_failure,
                        comparison=comparison,
                        independent_assessment=independent_assessment,
                        contract_test_assessment=contract_assessment,
                    )
                trial.update(
                    {
                        "status": "improvement_demonstrated"
                        if assessment["improvement_demonstrated"]
                        else "intermediate_candidate_forward_progress"
                        if assessment["target_progress_consistently"]
                        and not assessment["target_improved_consistently"]
                        and contract_assessment is not None
                        and contract_assessment.get("status") == "pass"
                        else "reevaluated_review_pending",
                        "candidate_result_path": str(candidate_result_path),
                        "comparison_path": str(comparison_path),
                        "assessment": assessment,
                        "target_assessment": target_assessment,
                        "contract_test_assessment_path": (
                            str(contract_path) if contract_path else None
                        ),
                        "independent_assessment_path": (
                            str(independent_path) if independent_path else None
                        ),
                        "progress_observed": assessment["target_progress_consistently"],
                        "candidate_evaluation_feedback_to_repair_agent": False,
                    }
                )
                case_record["repair_trials"].append(trial)
                atomic_write_json(trial_root / "trial.json", trial)
                package_path = candidate_package
                package_manifest = candidate_manifest
                if assessment["improvement_demonstrated"]:
                    case_record["status"] = "improvement_demonstrated"
                    break
                if not assessment["target_progress_consistently"]:
                    case_record["status"] = "review_pending"
                    case_record["blocked_reason"] = (
                        "no_verified_deterministic_forward_progress"
                    )
                    break
                if (
                    contract_assessment is None
                    or contract_assessment.get("status") != "pass"
                ):
                    case_record["status"] = "review_pending"
                    case_record["blocked_reason"] = (
                        "candidate_related_contract_tests_failed_or_unavailable"
                    )
                    break
                if assessment["target_improved_consistently"]:
                    case_record["status"] = "review_pending"
                    case_record["blocked_reason"] = (
                        "target_improved_but_independent_regression_evidence_"
                        "is_incomplete"
                    )
                    break
                case_record["status"] = "repair_in_progress"
            if case_record.get("status") == "repair_in_progress":
                case_record["status"] = "stopped_by_repair_limit"
                case_record["blocked_reason"] = "global_repair_attempt_limit_reached"

    result["cases"].append(case_record)
    result.pop("active_case", None)
    _write_analysis_artifacts(case_root, case_record)
    atomic_write_json(case_root / "case.json", case_record)
    result["status"] = (
        "improvement_demonstrated"
        if case_record.get("status") == "improvement_demonstrated"
        else "review_pending_or_unmet"
    )
    result["finished_at"] = datetime.now(timezone.utc).isoformat()
    result["elapsed_seconds"] = round(time.monotonic() - started, 3)
    atomic_write_json(output_root / "result.json", result)
    return result


def run_improvements(
    *,
    baseline_result: Path,
    judge_validation_result: Path | None,
    target_root: Path | None,
    profile_path: Path,
    output_root: Path,
    verifier_image: str | None,
    max_cases: int,
    max_repairs: int,
    max_seconds: int,
    analyze_only: bool,
) -> dict[str, Any]:
    from .compare import compare_runs

    baseline = _load_json(baseline_result)
    if baseline.get("suite") == "deterministic":
        return _run_deterministic_improvements(
            baseline_result=baseline_result,
            baseline=baseline,
            profile_path=profile_path,
            output_root=output_root,
            max_cases=max_cases,
            max_repairs=max_repairs,
            max_seconds=max_seconds,
            analyze_only=analyze_only,
        )
    if judge_validation_result is None:
        raise AgentEvalError(
            "semantic or mixed improvement evidence requires a verified Judge "
            "validation result"
        )
    if target_root is None or verifier_image is None:
        raise AgentEvalError(
            "QTS semantic improvement requires its fixed target root and verifier image"
        )
    from .qa_training_store import run as run_qts_evaluation

    run_root = baseline_result.parent.resolve()
    if baseline.get("target_revision") != DEFAULT_TARGET_REVISION:
        raise AgentEvalError(
            "improvement input is not the fixed qa-training-store scenario"
        )
    if baseline.get("profile_verification") != "verified":
        raise AgentEvalError("improvement requires verified baseline isolation")
    judge_validation = _load_json(judge_validation_result)
    if judge_validation.get("evaluator_revision") != baseline.get(
        "evaluator_revision"
    ) or judge_validation.get("target_revision") != baseline.get("target_revision"):
        raise AgentEvalError(
            "Judge validation uses a different Evaluator or target revision"
        )
    profile = load_execution_profile(profile_path)
    if (
        baseline.get("evaluator_revision") is None
        or baseline.get("skill_revision") is None
    ):
        raise AgentEvalError(
            "baseline provenance lacks fixed evaluator or Skill revision"
        )
    if not baseline.get("agent_command_template"):
        raise AgentEvalError(
            "baseline run does not preserve the Agent command template"
        )
    if judge_validation.get("judge_profile_fingerprint") != profile_fingerprint(
        profile
    ):
        raise AgentEvalError(
            "Judge validation uses a different Judge execution profile"
        )
    evaluator_sha = assert_clean_checkout(REPO_ROOT)
    if evaluator_sha != baseline["evaluator_revision"]:
        raise AgentEvalError("baseline run uses a different Evaluator revision")
    target_source_sha = assert_clean_checkout(target_root)
    evidence_rel = Path(profile["verification"]["evidence_path"])
    if evidence_rel.is_absolute() or ".." in evidence_rel.parts:
        raise AgentEvalError("execution profile evidence path is unsafe")
    output_root = Path(os.path.abspath(output_root))
    evidence_destination = prepare_run_output_root(
        output_root,
        repository_root=REPO_ROOT,
        evidence_relative_path=profile["verification"]["evidence_path"],
    )
    evidence_source = run_root / evidence_rel
    if not evidence_destination.exists() and evidence_source.is_file():
        evidence_destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(evidence_source, evidence_destination)
    if not verify_profile_evidence(
        profile,
        output_root,
        agent_command_argv=baseline.get("agent_command_template"),
    ):
        raise AgentEvalError("improvement requires verified isolation evidence")
    try:
        attempts = _attempt_data(baseline, run_root)
    except (AgentEvalError, OSError, ValueError, KeyError) as exc:
        pending = {
            "schema_version": 1,
            "status": "review_pending_or_unmet",
            "baseline_result": str(baseline_result),
            "evaluator_revision": baseline.get("evaluator_revision"),
            "target_revision": baseline.get("target_revision"),
            "baseline_skill_revision": baseline.get("skill_revision"),
            "cases": [
                {
                    "criterion": "baseline-evidence",
                    "status": "review_pending",
                    "blocked_reason": sanitize_diagnostic(str(exc), 500),
                    "repair_attempts_started": 0,
                }
            ],
            "repair_attempts_started": 0,
            "finished_at": datetime.now(timezone.utc).isoformat(),
        }
        atomic_write_json(output_root / "result.json", pending)
        return pending
    baseline_artifact_fingerprint = _artifact_content_fingerprint(
        attempts[0]["output_root"]
    )
    judge_verified = _judge_verification_map(
        judge_validation_result,
        expected_evaluator_revision=evaluator_sha,
        expected_target_revision=baseline.get("target_revision"),
        expected_profile_fingerprint=profile_fingerprint(profile),
        expected_baseline_artifact_fingerprint=baseline_artifact_fingerprint,
        target_root=target_root,
    )
    failures = _stable_failures(attempts, judge_verified)
    experiment_id = f"improve-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{os.urandom(4).hex()}"
    experiments_root = output_root / "experiments" / experiment_id
    experiments_root.mkdir(parents=True, exist_ok=False)
    result: dict[str, Any] = {
        "schema_version": 1,
        "status": "running",
        "experiment_id": experiment_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "baseline_result": str(baseline_result),
        "judge_validation_result": str(judge_validation_result),
        "evaluator_revision": baseline["evaluator_revision"],
        "target_revision": baseline["target_revision"],
        "target_source_checkout_revision": target_source_sha,
        "baseline_skill_revision": baseline["skill_revision"],
        "judge_criterion_verification": judge_verified,
        "baseline_package_fingerprint": baseline.get("skill_package_manifest", {}).get(
            "package_fingerprint"
        ),
        "limits": {
            "max_cases": max_cases,
            "max_repairs": max_repairs,
            "max_seconds": max_seconds,
        },
        "analyze_only": analyze_only,
        "repair_attempts_started": 0,
        "cases": [],
    }
    atomic_write_json(output_root / "result.json", result)
    start = time.monotonic()
    repair_attempts_started = 0
    selected = failures[:max_cases]
    result["unprocessed_criteria"] = [row["criterion"] for row in failures[max_cases:]]
    for case_index, failure in enumerate(selected, start=1):
        if time.monotonic() - start >= max_seconds:
            result["stopped_reason"] = "time_budget_exhausted"
            break
        criterion = failure["criterion"]
        case_root = experiments_root / criterion
        case_root.mkdir()
        skills = set(baseline.get("skill_package_manifest", {}).get("skills", []))
        parent_package = case_root / "baseline-package"
        baseline_manifest = create_skill_workspace(
            REPO_ROOT, baseline["skill_revision"], parent_package
        )
        allowed_skills = _CRITERION_SKILLS[criterion]
        case_record: dict[str, Any] = {
            "criterion": criterion,
            "verified_judge_fixture": failure["verified_fixture"],
            "observations": failure["observations"],
            "status": "analysis_pending",
            "repair_trials": [],
            "baseline_package_fingerprint": baseline_manifest["package_fingerprint"],
            "skill_use_observation": [row["skill_use_observation"] for row in attempts],
        }
        excerpt_candidates = sorted(
            skill
            for skill in allowed_skills & skills
            if all(
                _skill_use_for_attempt(row["attempt"], skill) == "observed"
                for row in attempts
            )
        )
        if not excerpt_candidates:
            case_record["status"] = "review_pending"
            case_record["blocked_reason"] = (
                "eligible_skill_use_not_observed_in_all_attempts"
            )
            case_record["analysis_preconditions"] = {
                "independent_attempts": len(attempts) >= 2,
                "runtime_and_artifact_evidence": "verified",
                "judge_criterion": judge_verified.get(criterion, {}).get("status"),
                "skill_use": "unobserved_or_incomplete",
            }
            result["cases"].append(case_record)
            _write_analysis_artifacts(case_root, case_record)
            atomic_write_json(case_root / "case.json", case_record)
            continue
        analysis_workspace = case_root / "analysis-workspace"
        analysis_workspace.mkdir()
        (analysis_workspace / ".qa-eval-output").mkdir()
        try:
            evidence_sources, inspected_sources, source_manifest = (
                _prepare_analysis_workspace(
                    workspace=analysis_workspace,
                    attempts=attempts,
                    allowed_skills=set(excerpt_candidates),
                    package_root=parent_package,
                    target_root=target_root,
                )
            )
        except (AgentEvalError, OSError, UnicodeDecodeError) as exc:
            case_record["status"] = "review_pending"
            case_record["blocked_reason"] = sanitize_diagnostic(str(exc), 500)
            result["cases"].append(case_record)
            _write_analysis_artifacts(case_root, case_record)
            atomic_write_json(case_root / "case.json", case_record)
            atomic_write_json(output_root / "result.json", result)
            continue
        prompt_evidence = {
            "baseline_run_id": baseline.get("run_id"),
            "attempt_ids": [row["attempt"].get("attempt_id") for row in attempts],
            "evaluator_revision": baseline.get("evaluator_revision"),
            "target_revision": baseline.get("target_revision"),
            "runtime_status": "pass",
            "artifact_contract_status": "pass",
            "target_integrity_status": "unchanged",
            "skill_use_observations": {
                skill: [
                    _skill_use_for_attempt(row["attempt"], skill) for row in attempts
                ]
                for skill in excerpt_candidates
            },
            "inspected_sources": source_manifest,
            "evaluator_only_expected_and_rubric": "withheld",
        }
        analysis_prompt = build_analysis_prompt(
            case_id=criterion,
            evidence=json.dumps(prompt_evidence, ensure_ascii=False),
            skill_excerpt=inspected_sources,
        )
        analysis_command = [
            item.replace("{workspace}", str(analysis_workspace)).replace(
                "{output_root}", str(analysis_workspace / ".qa-eval-output")
            )
            for item in baseline["agent_command_template"]
        ]
        analysis_isolation = verify_agent_docker_command(
            analysis_command,
            workspace=analysis_workspace,
            output_root=analysis_workspace / ".qa-eval-output",
            evaluator_root=REPO_ROOT,
        )
        analysis_named, analysis_cleanup = named_container_command(
            analysis_command,
            name=f"agent-eval-analysis-{experiment_id[-8:]}-{case_index:02d}",
        )
        analysis_execution_command = analysis_named
        if profile["agent"]["name"].lower() == "codex":
            analysis_execution_command = launcher_argv(
                output_root=analysis_workspace / ".qa-eval-output",
                model=profile["agent"]["model"],
                reasoning_effort=profile["agent"]["reasoning_effort"],
                cli_version=profile["agent"]["cli_version"],
                sandbox_policy=profile["agent"]["sandbox_policy"],
                docker_argv=analysis_named,
            )
        analysis_run = run_command(
            analysis_execution_command,
            input_text=analysis_prompt,
            cwd=analysis_workspace,
            timeout_seconds=min(
                profile["agent"]["timeout_seconds"],
                max(1, int(max_seconds - (time.monotonic() - start))),
            ),
            timeout_cleanup_argv=analysis_cleanup,
        )
        analysis_trace = capture_codex_jsonl_trace(
            analysis_run.stdout, skill_names=excerpt_candidates
        )
        analysis_safe = sanitize_diagnostic(analysis_trace["final_message"])
        analysis_launcher_unverified = (
            analysis_trace.get("launcher_observations") is not None
            and analysis_trace.get("execution_status") != "completed"
        )
        analysis_trace_path = None
        if analysis_trace["trace_summary"].get("status") == "captured":
            analysis_trace_path = "analysis-trace.json"
            atomic_write_json(
                case_root / analysis_trace_path, analysis_trace["trace_summary"]
            )
        case_record["analysis"] = {
            "status": "captured"
            if not analysis_run.timed_out
            and analysis_run.exit_code == 0
            and not analysis_trace["redacted"]
            and not analysis_launcher_unverified
            else "execution_error",
            "response": analysis_safe,
            "response_sha256": sha256_bytes(analysis_safe.encode("utf-8")),
            "trace_format": analysis_trace["format"],
            "trace_status": analysis_trace["status"],
            "trace_path": analysis_trace_path,
            "codex_launcher_evidence": analysis_trace.get("launcher_observations"),
            "prompt_sha256": sha256_bytes(analysis_prompt.encode("utf-8")),
            "isolation": analysis_isolation,
            "container_cleanup_status": analysis_run.cleanup_status,
        }
        if (
            analysis_run.timed_out
            or analysis_run.exit_code != 0
            or analysis_run.cleanup_status == "failed"
            or analysis_trace["redacted"]
            or analysis_launcher_unverified
        ):
            case_record["status"] = "review_pending"
            case_record["blocked_reason"] = (
                "analysis_output_redacted"
                if analysis_trace["redacted"]
                else "codex_launcher_evidence_unverified"
                if analysis_launcher_unverified
                else "analysis_agent_execution_error"
            )
            result["cases"].append(case_record)
            _write_analysis_artifacts(case_root, case_record)
            atomic_write_json(case_root / "case.json", case_record)
            continue
        try:
            analysis = _validate_analysis(
                analysis_safe,
                skill_names=set(excerpt_candidates),
                criterion=criterion,
                evidence_sources=evidence_sources,
            )
        except AgentEvalError as exc:
            case_record["status"] = "review_pending"
            case_record["blocked_reason"] = sanitize_diagnostic(str(exc), 500)
            result["cases"].append(case_record)
            _write_analysis_artifacts(case_root, case_record)
            atomic_write_json(case_root / "case.json", case_record)
            continue
        case_record["analysis_decision"] = analysis
        case_record["analysis_sources"] = source_manifest
        _write_analysis_artifacts(case_root, case_record)
        atomic_write_json(case_root / "case.json", case_record)
        chosen_skill = analysis.get("skill")
        repair_gate = _analysis_repair_gate(
            analysis,
            allowed_skills=set(excerpt_candidates),
            attempts=attempts,
            evidence_sources=evidence_sources,
            package_root=parent_package,
        )
        case_record["repair_gate"] = repair_gate
        mechanically_allowed = repair_gate["allowed"]
        if not mechanically_allowed:
            case_record["status"] = "review_pending"
            case_record["blocked_reason"] = ";".join(repair_gate["reasons"])
        elif analyze_only:
            case_record["status"] = "analysis_complete_review_pending"
            case_record["blocked_reason"] = "analyze_only_requested"
        elif repair_attempts_started >= max_repairs:
            case_record["status"] = "stopped_by_repair_limit"
            case_record["blocked_reason"] = "global_repair_attempt_limit_reached"
        else:
            independent_plan = _freeze_independent_eval_plan(
                skill=chosen_skill,
                evaluator_revision=baseline["evaluator_revision"],
                skill_revision=baseline["skill_revision"],
                baseline_package_fingerprint=baseline_manifest["package_fingerprint"],
                profile=profile,
                agent_command=baseline["agent_command_template"],
            )
            case_record["independent_regression_plan"] = independent_plan
            case_record["independent_evaluation_isolation"] = {
                "repair_agent_received_independent_inputs": False,
                "repair_agent_received_expected_results": False,
                "independent_results_returned_for_repair": False,
            }
            if independent_plan["status"] != "ready":
                case_record["status"] = "review_pending"
                case_record["blocked_reason"] = independent_plan["block_reason"]
                result["cases"].append(case_record)
                _write_analysis_artifacts(case_root, case_record)
                atomic_write_json(case_root / "case.json", case_record)
                atomic_write_json(output_root / "result.json", result)
                continue
            independent_baseline_results = []
            independent_baseline_failed = False
            for independent_case in independent_plan["cases"]:
                case_key = f"{independent_case['suite']}:{independent_case['case_id']}"
                safe_case_key = sha256_bytes(case_key.encode("utf-8")).removeprefix(
                    "sha256:"
                )[:16]
                baseline_independent_root = (
                    case_root / "independent-baseline" / safe_case_key
                )
                run_status = _run_independent_eval(
                    case=independent_case,
                    baseline=baseline,
                    profile=profile,
                    profile_path=profile_path,
                    evidence_root=output_root,
                    destination=baseline_independent_root,
                    timeout_seconds=int(max_seconds - (time.monotonic() - start)),
                )
                entry = {"case": independent_case, **run_status}
                if run_status.get("status") == "captured":
                    validation = _validate_independent_run(
                        Path(run_status["result_path"]),
                        case=independent_case,
                        profile=profile,
                        package_fingerprint=baseline_manifest["package_fingerprint"],
                        candidate=False,
                    )
                    entry["validation"] = {
                        "status": validation["status"],
                        "reason": validation.get("reason"),
                    }
                    if validation["status"] != "pass":
                        entry["status"] = "review_pending"
                        entry["reason"] = validation.get("reason")
                if entry.get("status") != "captured":
                    independent_baseline_failed = True
                independent_baseline_results.append(entry)
                case_record["independent_baseline_results"] = (
                    independent_baseline_results
                )
                atomic_write_json(case_root / "case.json", case_record)
                if independent_baseline_failed:
                    break
            if independent_baseline_failed:
                case_record["status"] = "review_pending"
                case_record["blocked_reason"] = (
                    "independent_baseline_evaluation_unavailable_or_invalid"
                )
                result["cases"].append(case_record)
                _write_analysis_artifacts(case_root, case_record)
                atomic_write_json(case_root / "case.json", case_record)
                atomic_write_json(output_root / "result.json", result)
                continue
            requested_paths = set(repair_gate["requested_paths"])
            if not requested_paths:
                case_record["status"] = "review_pending"
                case_record["blocked_reason"] = "analysis_requested_no_repair_path"
            else:
                package_path = parent_package
                package_manifest = baseline_manifest
                for repair_index in range(1, max_repairs + 1):
                    if repair_attempts_started >= max_repairs:
                        case_record["status"] = "stopped_by_repair_limit"
                        case_record["blocked_reason"] = (
                            "global_repair_attempt_limit_reached"
                        )
                        break
                    if time.monotonic() - start >= max_seconds:
                        case_record["status"] = "stopped_by_time_limit"
                        break
                    qts_worst_case = 2 * (
                        profile["agent"]["timeout_seconds"]
                        + 2 * profile["judge"]["timeout_seconds"]
                        + 480
                    )
                    if max_seconds - (time.monotonic() - start) < qts_worst_case:
                        case_record["status"] = "stopped_by_time_limit"
                        case_record["blocked_reason"] = (
                            "insufficient_budget_for_two_candidate_attempts"
                        )
                        break
                    trial_root = (
                        case_root / "repair-trials" / f"trial-{repair_index:02d}"
                    )
                    trial_root.mkdir(parents=True)
                    repair_workspace = trial_root / "workspace"
                    (repair_workspace / ".agents").mkdir(parents=True)
                    (repair_workspace / ".agents" / "skills").mkdir()
                    visible_paths = _copy_allowed_skill_files(
                        package_path,
                        repair_workspace / ".agents" / "skills",
                        chosen_skill,
                    )
                    repair_output = repair_workspace / ".qa-eval-output"
                    repair_output.mkdir()
                    skill_root = repair_workspace / ".agents" / "skills" / chosen_skill
                    before = _source_paths(package_path, chosen_skill)
                    allowed_for_prompt = [
                        f"{chosen_skill}/{item}" for item in sorted(requested_paths)
                    ]
                    repair_prompt = build_repair_prompt(
                        analysis=json.dumps(analysis, ensure_ascii=False),
                        allowed_paths=allowed_for_prompt,
                        baseline_sha=baseline["skill_revision"],
                    )
                    repair_command = [
                        item.replace("{workspace}", str(repair_workspace)).replace(
                            "{output_root}", str(repair_output)
                        )
                        for item in baseline["agent_command_template"]
                    ]
                    repair_mount = f"type=bind,source={skill_root},target=/workspace/.agents/skills/{chosen_skill}"
                    repair_command = _insert_mount_before_image(
                        repair_command, repair_mount
                    )
                    repair_isolation = verify_repair_docker_command(
                        repair_command,
                        workspace=repair_workspace,
                        skill_root=skill_root,
                        output_root=repair_output,
                        skill_name=chosen_skill,
                    )
                    repair_named, repair_cleanup = named_container_command(
                        repair_command,
                        name=f"agent-eval-repair-{experiment_id[-8:]}-{case_index:02d}-{repair_index:02d}",
                    )
                    repair_attempts_started += 1
                    result["repair_attempts_started"] = repair_attempts_started
                    result["active_case"] = {
                        "criterion": criterion,
                        "trial": repair_index,
                        "global_repair_attempt": repair_attempts_started,
                        "status": "repair_agent_running",
                    }
                    atomic_write_json(output_root / "result.json", result)
                    repair_execution_command = repair_named
                    if profile["agent"]["name"].lower() == "codex":
                        repair_execution_command = launcher_argv(
                            output_root=repair_output,
                            model=profile["agent"]["model"],
                            reasoning_effort=profile["agent"]["reasoning_effort"],
                            cli_version=profile["agent"]["cli_version"],
                            sandbox_policy=profile["agent"]["sandbox_policy"],
                            docker_argv=repair_named,
                            mode="repair",
                            skill_name=chosen_skill,
                        )
                    repair_execution = run_command(
                        repair_execution_command,
                        input_text=repair_prompt,
                        cwd=repair_workspace,
                        timeout_seconds=min(
                            profile["agent"]["timeout_seconds"],
                            max(1, int(max_seconds - (time.monotonic() - start))),
                        ),
                        timeout_cleanup_argv=repair_cleanup,
                    )
                    repair_trace = capture_codex_jsonl_trace(repair_execution.stdout)
                    repair_output_unverified = repair_trace["redacted"] or (
                        repair_trace.get("launcher_observations") is not None
                        and repair_trace.get("execution_status") != "completed"
                    )
                    trial: dict[str, Any] = {
                        "trial": repair_index,
                        "status": "execution_error"
                        if repair_execution.timed_out
                        or repair_execution.exit_code != 0
                        or repair_execution.cleanup_status == "failed"
                        else "review_pending"
                        if repair_output_unverified
                        else "running",
                        "repair_response_sha256": sha256_bytes(
                            sanitize_diagnostic(repair_trace["final_message"]).encode(
                                "utf-8"
                            )
                        ),
                        "repair_response": sanitize_diagnostic(
                            repair_trace["final_message"]
                        ),
                        "trace_format": repair_trace["format"],
                        "trace_status": repair_trace["status"],
                        "trace_path": "repair-trace.json"
                        if repair_trace["trace_summary"].get("status") == "captured"
                        else None,
                        "codex_launcher_evidence": repair_trace.get(
                            "launcher_observations"
                        ),
                        "isolation": repair_isolation,
                        "container_cleanup_status": repair_execution.cleanup_status,
                        "allowed_paths": sorted(requested_paths),
                        "baseline_package_fingerprint": package_manifest[
                            "package_fingerprint"
                        ],
                    }
                    if repair_trace["trace_summary"].get("status") == "captured":
                        atomic_write_json(
                            trial_root / "repair-trace.json",
                            repair_trace["trace_summary"],
                        )
                    trial_root.mkdir(exist_ok=True)
                    if trial["status"] == "execution_error":
                        trial["stop_reason"] = "repair_agent_execution_error"
                        case_record["repair_trials"].append(trial)
                        atomic_write_json(trial_root / "trial.json", trial)
                        case_record["status"] = "review_pending"
                        break
                    if repair_output_unverified:
                        trial["stop_reason"] = (
                            "repair_output_redacted"
                            if repair_trace["redacted"]
                            else "codex_launcher_evidence_unverified"
                        )
                        case_record["repair_trials"].append(trial)
                        atomic_write_json(trial_root / "trial.json", trial)
                        case_record["status"] = "review_pending"
                        break
                    try:
                        changes, _ = _validate_repair_diff(
                            before,
                            repair_workspace / ".agents" / "skills",
                            chosen_skill,
                            requested_paths,
                            visible_paths=visible_paths,
                        )
                    except (AgentEvalError, UnicodeDecodeError) as exc:
                        trial["status"] = "review_pending"
                        trial["stop_reason"] = sanitize_diagnostic(str(exc), 500)
                        case_record["repair_trials"].append(trial)
                        atomic_write_json(trial_root / "trial.json", trial)
                        case_record["status"] = "review_pending"
                        break
                    candidate_package = trial_root / "candidate-package"
                    shutil.copytree(package_path, candidate_package)
                    candidate_skill_root = candidate_package / "skills" / chosen_skill
                    repaired_skill_root = (
                        repair_workspace / ".agents" / "skills" / chosen_skill
                    )
                    for change in changes:
                        relative = safe_relative_path(change["path"])
                        destination = candidate_skill_root / relative
                        destination.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copyfile(repaired_skill_root / relative, destination)
                    candidate_manifest = create_skill_workspace_from_root(
                        candidate_package,
                        trial_root / "candidate-manifest-workspace",
                        expected_skills=skills,
                        parent_revision=baseline["skill_revision"],
                    )
                    shutil.rmtree(trial_root / "candidate-manifest-workspace")
                    diff_lines: list[str] = []
                    original_root = parent_package / "skills" / chosen_skill
                    revised_root = candidate_package / "skills" / chosen_skill
                    for change in changes:
                        relative = change["path"]
                        old_path = original_root / relative
                        new_path = revised_root / relative
                        try:
                            old_text = (
                                old_path.read_text(encoding="utf-8").splitlines(
                                    keepends=True
                                )
                                if old_path.is_file()
                                else []
                            )
                            new_text = new_path.read_text(encoding="utf-8").splitlines(
                                keepends=True
                            )
                            diff_lines.extend(
                                difflib.unified_diff(
                                    old_text,
                                    new_text,
                                    fromfile=f"a/{chosen_skill}/{relative}",
                                    tofile=f"b/{chosen_skill}/{relative}",
                                )
                            )
                        except UnicodeDecodeError:
                            diff_lines.append(
                                f"Binary change: {chosen_skill}/{relative} {change['before_sha256']} -> {change['after_sha256']}\n"
                            )
                    patch_text = "".join(diff_lines)
                    if _SECRET_RE.search(patch_text):
                        raise AgentEvalError("repair patch contains secret-shaped text")
                    (trial_root / "patch.diff").write_text(patch_text, encoding="utf-8")
                    with zipfile.ZipFile(
                        trial_root / "changed-files.zip",
                        "w",
                        compression=zipfile.ZIP_DEFLATED,
                    ) as archive:
                        for change in changes:
                            path = revised_root / change["path"]
                            archive.write(
                                path, arcname=f"skills/{chosen_skill}/{change['path']}"
                            )
                    trial.update(
                        {
                            "status": "candidate_saved",
                            "candidate_revision_status": "uncommitted_patch",
                            "candidate_package_fingerprint": candidate_manifest[
                                "package_fingerprint"
                            ],
                            "candidate_package_parent_revision": baseline[
                                "skill_revision"
                            ],
                            "changes": changes,
                            "patch_path": "patch.diff",
                            "changed_files_archive": "changed-files.zip",
                        }
                    )
                    result["active_case"]["status"] = "candidate_evaluation_running"
                    result["active_case"]["candidate_package_fingerprint"] = (
                        candidate_manifest["package_fingerprint"]
                    )
                    atomic_write_json(output_root / "result.json", result)
                    candidate_run_root = trial_root / "re-evaluation"
                    candidate_run_root.mkdir()
                    profile_evidence_source = output_root / evidence_rel
                    profile_evidence_destination = candidate_run_root / evidence_rel
                    profile_evidence_destination.parent.mkdir(
                        parents=True, exist_ok=True
                    )
                    shutil.copyfile(
                        profile_evidence_source, profile_evidence_destination
                    )
                    qts_args = [
                        "--target-root",
                        str(target_root),
                        "--skill-revision",
                        baseline["skill_revision"],
                        "--skill-package-root",
                        str(candidate_package),
                        "--execution-profile",
                        str(profile_path),
                        "--verifier-image",
                        verifier_image,
                        "--output-root",
                        str(candidate_run_root),
                        "--repeat",
                        "2",
                        "--agent-command",
                        *baseline["agent_command_template"],
                    ]
                    qts_exit = run_qts_evaluation(qts_args)
                    candidate_result_path = candidate_run_root / "result.json"
                    if not candidate_result_path.is_file():
                        trial["status"] = "execution_error"
                        trial["stop_reason"] = (
                            f"candidate_evaluation_did_not_save_result_exit_{qts_exit}"
                        )
                        case_record["repair_trials"].append(trial)
                        atomic_write_json(trial_root / "trial.json", trial)
                        case_record["status"] = "review_pending"
                        break
                    comparison_path = trial_root / "comparison.json"
                    comparison = compare_runs(baseline_result, candidate_result_path)
                    atomic_write_json(comparison_path, comparison)
                    target_assessment = _assess_improvement(
                        baseline_result,
                        candidate_result_path,
                        chosen_skill,
                        criterion,
                        comparison=comparison,
                    )
                    assessment = target_assessment
                    contract_test_assessment = None
                    contract_test_path = None
                    if target_assessment["target_progress_consistently"]:
                        contract_test_assessment = _run_related_contract_tests(
                            independent_plan["contract_tests"],
                            timeout_seconds=max(
                                0, int(max_seconds - (time.monotonic() - start))
                            ),
                            evaluator_revision=baseline["evaluator_revision"],
                            skill=chosen_skill,
                            skill_revision=baseline["skill_revision"],
                            expected_skills=set(candidate_manifest["skills"]),
                            candidate_package=candidate_package,
                            candidate_package_fingerprint=candidate_manifest[
                                "package_fingerprint"
                            ],
                        )
                        contract_test_path = trial_root / "contract-tests.json"
                        atomic_write_json(contract_test_path, contract_test_assessment)
                        if target_assessment["target_improved_consistently"]:
                            if contract_test_assessment["status"] == "pass":
                                independent_assessment = _run_candidate_independent_assessment(
                                    plan=independent_plan,
                                    baseline_results=independent_baseline_results,
                                    baseline=baseline,
                                    profile=profile,
                                    profile_path=profile_path,
                                    evidence_root=output_root,
                                    case_root=trial_root,
                                    candidate_package=candidate_package,
                                    candidate_package_fingerprint=candidate_manifest[
                                        "package_fingerprint"
                                    ],
                                    timeout_seconds=max(
                                        0,
                                        int(max_seconds - (time.monotonic() - start)),
                                    ),
                                    compare_runs=compare_runs,
                                )
                            else:
                                independent_assessment = {
                                    "status": "review_pending",
                                    "planned": len(independent_plan["cases"]),
                                    "cases": [
                                        {
                                            "suite": row["suite"],
                                            "case_id": row["case_id"],
                                            "status": "review_pending",
                                            "reason": "candidate_contract_tests_did_not_pass",
                                        }
                                        for row in independent_plan["cases"]
                                    ],
                                    "conditions_match": False,
                                    "candidate_fingerprint_fixed": False,
                                    "expected_inputs_disclosed": False,
                                    "expected_results_disclosed": False,
                                    "feedback_to_repair_agent": False,
                                }
                            independent_assessment_path = (
                                trial_root / "independent-assessment.json"
                            )
                            atomic_write_json(
                                independent_assessment_path, independent_assessment
                            )
                            assessment = _assess_improvement(
                                baseline_result,
                                candidate_result_path,
                                chosen_skill,
                                criterion,
                                comparison=comparison,
                                independent_assessment=independent_assessment,
                                contract_test_assessment=contract_test_assessment,
                            )
                        else:
                            assessment = _assess_improvement(
                                baseline_result,
                                candidate_result_path,
                                chosen_skill,
                                criterion,
                                comparison=comparison,
                                contract_test_assessment=contract_test_assessment,
                            )
                    trial["candidate_run_result"] = str(candidate_result_path)
                    trial["comparison"] = str(comparison_path)
                    trial["assessment"] = assessment
                    if target_assessment["target_progress_consistently"]:
                        trial["target_assessment"] = target_assessment
                        trial["contract_test_assessment"] = str(contract_test_path)
                    if target_assessment["target_improved_consistently"]:
                        trial["independent_assessment"] = str(
                            independent_assessment_path
                        )
                    can_continue_repair = bool(
                        assessment["target_progress_consistently"]
                        and not assessment["target_improved_consistently"]
                        and contract_test_assessment is not None
                        and contract_test_assessment["status"] == "pass"
                    )
                    trial["status"] = (
                        "improvement_demonstrated"
                        if assessment["improvement_demonstrated"]
                        else "intermediate_candidate_forward_progress"
                        if can_continue_repair
                        else "reevaluated_review_pending"
                    )
                    trial["progress_observed"] = assessment[
                        "target_progress_consistently"
                    ]
                    case_record["repair_trials"].append(trial)
                    atomic_write_json(trial_root / "trial.json", trial)
                    package_path = candidate_package
                    package_manifest = candidate_manifest
                    if assessment["improvement_demonstrated"]:
                        case_record["status"] = "improvement_demonstrated"
                        break
                    if not assessment["target_progress_consistently"]:
                        case_record["status"] = "review_pending"
                        case_record["blocked_reason"] = "no_verified_forward_progress"
                        break
                    if (
                        contract_test_assessment is not None
                        and contract_test_assessment["status"] != "pass"
                    ):
                        case_record["status"] = "review_pending"
                        case_record["blocked_reason"] = (
                            "candidate_related_contract_tests_failed_or_unavailable"
                        )
                        break
                    if assessment["target_improved_consistently"]:
                        case_record["status"] = "review_pending"
                        case_record["blocked_reason"] = (
                            "candidate_target_improved_but_full_independent_or_contract_evidence_is_incomplete"
                        )
                        break
                    case_record["status"] = "repair_in_progress"
        if case_record.get("status") == "repair_in_progress":
            case_record["status"] = "stopped_by_repair_limit"
            case_record["blocked_reason"] = "global_repair_attempt_limit_reached"
        result["cases"].append(case_record)
        result.pop("active_case", None)
        result["repair_attempts_started"] = repair_attempts_started
        _write_analysis_artifacts(case_root, case_record)
        atomic_write_json(case_root / "case.json", case_record)
        atomic_write_json(output_root / "result.json", result)
    case_states = [row.get("status") for row in result["cases"]]
    if not failures:
        result["stopped_reason"] = "no_reproducible_judge_verified_skill_defect"
    result["status"] = (
        "improvement_demonstrated"
        if case_states
        and all(state == "improvement_demonstrated" for state in case_states)
        else "review_pending_or_unmet"
    )
    result["finished_at"] = datetime.now(timezone.utc).isoformat()
    result["elapsed_seconds"] = round(time.monotonic() - start, 3)
    atomic_write_json(output_root / "result.json", result)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Analyze saved Agent evaluations and make bounded, isolated Skill repair attempts."
    )
    parser.add_argument("--baseline-result", type=Path, required=True)
    parser.add_argument("--judge-validation-result", type=Path)
    parser.add_argument("--target-root", type=Path)
    parser.add_argument("--execution-profile", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--verifier-image")
    parser.add_argument("--max-cases", type=int, required=True)
    parser.add_argument("--max-repairs", type=int, required=True)
    parser.add_argument("--max-seconds", type=int, required=True)
    parser.add_argument("--analyze-only", action="store_true")
    args = parser.parse_args(argv)
    if (
        min(args.max_cases, args.max_repairs, args.max_seconds) <= 0
        or args.max_cases > 100
        or args.max_repairs > 10
        or args.max_seconds > 3600
    ):
        parser.error("case, repair, and time limits are invalid or exceed fixed caps")
    try:
        result = run_improvements(
            baseline_result=args.baseline_result,
            judge_validation_result=args.judge_validation_result,
            target_root=args.target_root,
            profile_path=args.execution_profile,
            output_root=args.output_root.resolve(),
            verifier_image=args.verifier_image,
            max_cases=args.max_cases,
            max_repairs=args.max_repairs,
            max_seconds=args.max_seconds,
            analyze_only=args.analyze_only,
        )
    except (AgentEvalError, OSError, ValueError, KeyError) as exc:
        print(
            f"improvement run failed: {sanitize_diagnostic(str(exc), 2000)}",
            file=sys.stderr,
        )
        return 2
    print(
        json.dumps(
            {
                "result": str(args.output_root / "result.json"),
                "status": result["status"],
            },
            ensure_ascii=True,
        )
    )
    return 0 if result["status"] == "improvement_demonstrated" else 1


if __name__ == "__main__":
    raise SystemExit(main())
