from __future__ import annotations

import argparse
import difflib
import json
import os
import re
import shutil
import sys
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

from .common import (
    AgentEvalError,
    atomic_write_json,
    capture_codex_jsonl_trace,
    canonical_fingerprint,
    prepare_run_output_root,
    sanitize_diagnostic,
    sha256_bytes,
)
from .executor import run_command
from .prompt_builder import build_analysis_prompt, build_repair_prompt
from .target_workspace import DEFAULT_TARGET_REVISION
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
    "QTS-SEM-008": {"test-requirement-design", "test-condition-design", "test-case-design"},
    "QTS-SEM-009": {"coverage-analysis", "test-case-design"},
    "QTS-SEM-010": {"test-requirement-design", "test-case-design"},
}
_SECRET_RE = re.compile(r"(?i)\b(?:Bearer\s+\S{12,}|sk-[A-Za-z0-9_-]{16,}|gh[pousr]_[A-Za-z0-9]{20,}|(?:api[_-]?key|access[_-]?token|password)\s*[:=]\s*\S+)")


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AgentEvalError(f"saved evaluation record is unreadable: {path.name}") from exc
    if not isinstance(value, dict):
        raise AgentEvalError(f"saved evaluation record must be an object: {path.name}")
    return value


def _judge_verification_map(path: Path) -> dict[str, dict[str, Any]]:
    value = _load_json(path)
    if value.get("dataset_revision") is None or not isinstance(value.get("cases"), list):
        raise AgentEvalError("Judge validation result schema is invalid")
    result: dict[str, dict[str, Any]] = {}
    for case in value["cases"]:
        if not isinstance(case, dict) or not isinstance(case.get("criteria"), list):
            continue
        if case.get("status") != "verified":
            continue
        for criterion in case["criteria"]:
            result[criterion] = {"status": "verified", "case_id": case.get("case_id")}
    return result


def _attempt_data(run: dict[str, Any], run_root: Path) -> list[dict[str, Any]]:
    if not isinstance(run.get("attempts"), list) or len(run["attempts"]) < 2:
        raise AgentEvalError("Skill repair requires at least two independent baseline attempts")
    collected = []
    for attempt in run["attempts"]:
        relative = attempt.get("saved_result_root")
        if not isinstance(relative, str):
            raise AgentEvalError("baseline attempt has no preserved run root")
        root = (run_root / relative).resolve()
        try:
            root.relative_to(run_root.resolve())
        except ValueError as exc:
            raise AgentEvalError("baseline attempt path escapes its run root") from exc
        judge = _load_json(root / "judge-result.json")
        validation = _load_json(root / "artifact-validation.json")
        runtime = _load_json(root / "runtime-checks.json")
        integrity = _load_json(root / "target-integrity.json")
        if attempt.get("status") == "execution_error" or validation.get("status") != "pass":
            raise AgentEvalError("baseline has runner, evidence, or artifact-contract errors")
        if runtime.get("verifier", {}).get("status") != "pass" or runtime.get("workflow_runtime", {}).get("status") != "pass":
            raise AgentEvalError("baseline has runtime evidence that is missing, failing, or unverified")
        if not integrity.get("unchanged"):
            raise AgentEvalError("baseline target workspace integrity check failed")
        normalized = judge.get("normalized")
        if not isinstance(normalized, dict) or not isinstance(normalized.get("criteria"), list):
            raise AgentEvalError("baseline has no normalized fixed-Judge criteria")
        criteria = {item.get("id"): item for item in normalized["criteria"] if isinstance(item, dict)}
        collected.append({
            "attempt": attempt,
            "root": root,
            "criteria": criteria,
            "artifacts": validation.get("artifacts", []),
            "skill_use_observation": attempt.get("skill_use_observation", "unverified"),
            "agent_output_root": attempt.get("saved_output_root"),
        })
    return collected


def _stable_failures(attempts: list[dict[str, Any]], verified: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    if not attempts:
        return []
    common = set(attempts[0]["criteria"])
    for attempt in attempts[1:]:
        common &= set(attempt["criteria"])
    failures = []
    for criterion in sorted(common):
        if criterion not in _CRITERION_SKILLS or criterion not in verified:
            continue
        rows = [attempt["criteria"][criterion] for attempt in attempts]
        if all(row.get("rating") == 1 and row.get("status") == "fail" for row in rows):
            failures.append({
                "criterion": criterion,
                "verified_fixture": verified[criterion],
                "observations": [
                    {"attempt_id": attempt["attempt"].get("attempt_id"), "rating": row.get("rating"), "status": row.get("status"), "evidence": row.get("evidence", [])}
                    for attempt, row in zip(attempts, rows, strict=True)
                ],
            })
    return failures


def _skill_excerpt(package_root: Path, skill: str, limit: int = 20_000) -> str:
    path = package_root / "skills" / skill / "SKILL.md"
    text = path.read_text(encoding="utf-8")
    return text[:limit]


def _source_paths(package_root: Path, skill: str) -> dict[str, str]:
    manifest: dict[str, str] = {}
    root = package_root / "skills" / skill
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise AgentEvalError("baseline Skill package contains a symlink")
        if path.is_file():
            manifest[path.relative_to(package_root / "skills").as_posix()] = sha256_bytes(path.read_bytes())
    return manifest


def _validate_analysis(raw: str, *, skill_names: set[str], criterion: str) -> dict[str, Any]:
    safe = sanitize_diagnostic(raw)
    try:
        value = json.loads(safe)
    except json.JSONDecodeError as exc:
        raise AgentEvalError("analysis Agent response is not JSON") from exc
    required = {"classification", "skill", "issue", "evidence", "alternative_causes", "repair_paths", "repair_rationale"}
    if not isinstance(value, dict) or set(value) != required:
        raise AgentEvalError("analysis Agent response schema is invalid")
    if value["classification"] not in {"skill", "agent", "evaluator", "input", "environment", "evidence", "unknown"}:
        raise AgentEvalError("analysis Agent classification is invalid")
    if value["skill"] is not None and value["skill"] not in skill_names:
        raise AgentEvalError("analysis Agent selected an unknown Skill")
    for field in ("issue", "repair_rationale"):
        if not isinstance(value[field], str) or not value[field].strip():
            raise AgentEvalError(f"analysis Agent {field} is missing")
    for field in ("evidence", "alternative_causes", "repair_paths"):
        if not isinstance(value[field], list) or any(not isinstance(item, str) for item in value[field]):
            raise AgentEvalError(f"analysis Agent {field} must be a string array")
    value["target_criterion"] = criterion
    return value


def _allowed_repair_paths(skill: str, package_root: Path) -> list[str]:
    root = package_root / "skills" / skill
    return sorted(
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() and not path.is_symlink()
        and (path.name == "SKILL.md" or path.relative_to(root).parts[0] in {"references", "scripts", "assets"})
    )


def _validate_repair_diff(before: dict[str, str], skill_root: Path, skill: str, allowed: set[str]) -> tuple[list[dict[str, Any]], dict[str, str]]:
    after: dict[str, str] = {}
    root = skill_root / skill
    changes: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise AgentEvalError("repair Agent created a symlink")
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        if relative != "SKILL.md" and (not PurePosixPath(relative).parts or PurePosixPath(relative).parts[0] not in {"references", "scripts", "assets"}):
            raise AgentEvalError(f"repair Agent changed a forbidden Skill path: {relative}")
        raw = path.read_bytes()
        text = raw.decode("utf-8", errors="strict")
        if _SECRET_RE.search(text):
            raise AgentEvalError("repair Agent output contains secret-shaped text")
        digest = sha256_bytes(raw)
        after[relative] = digest
        old_digest = before.get(f"{skill}/{relative}")
        if digest != old_digest:
            changes.append({"path": relative, "before_sha256": old_digest, "after_sha256": digest, "size": len(raw)})
    for source_path, old_digest in before.items():
        if not source_path.startswith(skill + "/"):
            continue
        relative = source_path[len(skill) + 1:]
        if relative not in after:
            raise AgentEvalError("repair Agent deleted an existing Skill file")
    changed_paths = {item["path"] for item in changes}
    if not changed_paths:
        raise AgentEvalError("repair Agent produced no source changes")
    if not changed_paths.issubset(allowed):
        raise AgentEvalError("repair Agent changed a path it did not request permission to edit")
    return changes, after


def _insert_mount_before_image(argv: list[str], mount: str) -> list[str]:
    index = 2
    value_options = {"--network", "--mount", "--workdir", "-w", "-e", "--env", "--env-file", "--name", "--user", "--entrypoint", "--memory", "--cpus", "--security-opt"}
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


def _assess_improvement(
    baseline: Path,
    candidate: Path,
    skill: str,
    criterion: str,
    *,
    comparison: dict[str, Any],
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
        left_judge = _load_json(left["root"] / "judge-result.json").get("normalized", {})
        right_judge = _load_json(right["root"] / "judge-result.json").get("normalized", {})
        left_criteria = {row["id"]: row for row in left_judge.get("criteria", [])}
        right_criteria = {row["id"]: row for row in right_judge.get("criteria", [])}
        target_left = left_criteria.get(criterion, {}).get("rating")
        target_right = right_criteria.get(criterion, {}).get("rating")
        criterion_statuses.append({"baseline": target_left, "candidate": target_right})
        for criterion_id, row in left_criteria.items():
            if row.get("critical"):
                if criterion_id not in right_criteria or right_criteria[criterion_id].get("rating", 0) < row.get("rating", 0):
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
    usage_verified = bool(baseline_use and candidate_use and all(value == "observed" for value in baseline_use + candidate_use))
    return {
        "target_criterion_ratings": criterion_statuses,
        "target_progress_consistently": target_progress,
        "target_improved_consistently": target_improved,
        "no_critical_regressions": no_critical_regressions,
        "skill_use_observation": {"baseline": baseline_use, "candidate": candidate_use},
        "improvement_demonstrated": target_improved and no_critical_regressions and usage_verified,
        "reason": None if target_improved and no_critical_regressions and usage_verified else "criterion, regression, or Skill-use evidence requirements are not all met",
    }


def _write_analysis_artifacts(case_root: Path, case_record: dict[str, Any]) -> None:
    analysis = case_record.get("analysis", {})
    decision = case_record.get("analysis_decision", {})
    saved = {
        "schema_version": 1,
        "criterion": case_record.get("criterion"),
        "status": case_record.get("status"),
        "blocked_reason": case_record.get("blocked_reason"),
        "verified_judge_fixture": case_record.get("verified_judge_fixture"),
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
        f"- Judge検証fixture: {case_record.get('verified_judge_fixture', {}).get('case_id', '未指定')}",
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
        "原判定、artifact、固定Referenceはこの記録から変更していません。Agent responseはJSON側に安全化済みで保存します。",
    ]
    (case_root / "analysis.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_improvements(
    *,
    baseline_result: Path,
    judge_validation_result: Path,
    target_root: Path,
    profile_path: Path,
    output_root: Path,
    verifier_image: str,
    max_cases: int,
    max_repairs: int,
    max_seconds: int,
    analyze_only: bool,
) -> dict[str, Any]:
    from .compare import compare_runs
    from .qa_training_store import run as run_qts_evaluation

    baseline = _load_json(baseline_result)
    run_root = baseline_result.parent.resolve()
    if baseline.get("target_revision") != DEFAULT_TARGET_REVISION:
        raise AgentEvalError("improvement input is not the fixed qa-training-store scenario")
    if baseline.get("profile_verification") != "verified":
        raise AgentEvalError("improvement requires verified baseline isolation")
    attempts = _attempt_data(baseline, run_root)
    judge_validation = _load_json(judge_validation_result)
    if (
        judge_validation.get("evaluator_revision") != baseline.get("evaluator_revision")
        or judge_validation.get("target_revision") != baseline.get("target_revision")
    ):
        raise AgentEvalError("Judge validation uses a different Evaluator or target revision")
    judge_verified = _judge_verification_map(judge_validation_result)
    failures = _stable_failures(attempts, judge_verified)
    profile = load_execution_profile(profile_path)
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
    if judge_validation.get("judge_profile_fingerprint") != profile_fingerprint(profile):
        raise AgentEvalError("Judge validation uses a different Judge execution profile")
    if baseline.get("evaluator_revision") is None or baseline.get("skill_revision") is None:
        raise AgentEvalError("baseline provenance lacks fixed evaluator or Skill revision")
    evaluator_sha = assert_clean_checkout(REPO_ROOT)
    if evaluator_sha != baseline["evaluator_revision"]:
        raise AgentEvalError("baseline run uses a different Evaluator revision")
    target_source_sha = assert_clean_checkout(target_root)
    if not baseline.get("agent_command_template"):
        raise AgentEvalError("baseline run does not preserve the Agent command template")

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
        "baseline_package_fingerprint": baseline.get("skill_package_manifest", {}).get("package_fingerprint"),
        "limits": {"max_cases": max_cases, "max_repairs": max_repairs, "max_seconds": max_seconds},
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
        baseline_manifest = create_skill_workspace(REPO_ROOT, baseline["skill_revision"], parent_package)
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
        prompt_evidence = {
            "criterion": criterion,
            "repeated_fixed_judge_observations": failure["observations"],
            "baseline_run_id": baseline.get("run_id"),
            "attempt_ids": [row["attempt"].get("attempt_id") for row in attempts],
            "runtime_status": "pass",
            "artifact_contract_status": "pass",
            "target_integrity_status": "unchanged",
            "artifacts": sorted(
                {
                    (row.get("path"), row.get("sha256"))
                    for attempt in attempts
                    for row in attempt["artifacts"]
                }
            ),
        }
        excerpt_candidates = sorted(allowed_skills & skills)
        analysis_workspace = case_root / "analysis-workspace"
        analysis_workspace.mkdir()
        (analysis_workspace / ".agents" / "skills").mkdir(parents=True)
        (analysis_workspace / ".qa-eval-output").mkdir()
        excerpt_parts = []
        for skill_name in excerpt_candidates:
            shutil.copytree(parent_package / "skills" / skill_name, analysis_workspace / ".agents" / "skills" / skill_name)
            excerpt_parts.append(f"## {skill_name}\n{_skill_excerpt(parent_package, skill_name, 8_000)}")
        analysis_prompt = build_analysis_prompt(
            case_id=criterion,
            evidence=json.dumps(prompt_evidence, ensure_ascii=False),
            skill_excerpt="\n\n".join(excerpt_parts),
        )
        analysis_command = [
            item.replace("{workspace}", str(analysis_workspace)).replace("{output_root}", str(analysis_workspace / ".qa-eval-output"))
            for item in baseline["agent_command_template"]
        ]
        analysis_isolation = verify_agent_docker_command(
            analysis_command,
            workspace=analysis_workspace,
            output_root=analysis_workspace / ".qa-eval-output",
            evaluator_root=REPO_ROOT,
        )
        analysis_named, analysis_cleanup = named_container_command(analysis_command, name=f"agent-eval-analysis-{experiment_id[-8:]}-{case_index:02d}")
        analysis_run = run_command(
            analysis_named,
            input_text=analysis_prompt,
            cwd=analysis_workspace,
            timeout_seconds=min(profile["agent"]["timeout_seconds"], max(1, int(max_seconds - (time.monotonic() - start)))),
            timeout_cleanup_argv=analysis_cleanup,
        )
        analysis_trace = capture_codex_jsonl_trace(
            analysis_run.stdout, skill_names=excerpt_candidates
        )
        analysis_safe = sanitize_diagnostic(analysis_trace["final_message"])
        if analysis_trace["trace_jsonl"] is not None:
            (case_root / "analysis-trace.jsonl").write_text(
                analysis_trace["trace_jsonl"], encoding="utf-8"
            )
        case_record["analysis"] = {
            "status": "captured" if not analysis_run.timed_out and analysis_run.exit_code == 0 else "execution_error",
            "response": analysis_safe,
            "response_sha256": sha256_bytes(analysis_safe.encode("utf-8")),
            "trace_format": analysis_trace["format"],
            "trace_status": analysis_trace["status"],
            "trace_path": "analysis-trace.jsonl" if analysis_trace["trace_jsonl"] is not None else None,
            "prompt_sha256": sha256_bytes(analysis_prompt.encode("utf-8")),
            "isolation": analysis_isolation,
            "container_cleanup_status": analysis_run.cleanup_status,
        }
        if analysis_run.timed_out or analysis_run.exit_code != 0 or analysis_run.cleanup_status == "failed":
            case_record["status"] = "review_pending"
            case_record["blocked_reason"] = "analysis_agent_execution_error"
            result["cases"].append(case_record)
            _write_analysis_artifacts(case_root, case_record)
            atomic_write_json(case_root / "case.json", case_record)
            continue
        try:
            analysis = _validate_analysis(analysis_safe, skill_names=skills, criterion=criterion)
        except AgentEvalError as exc:
            case_record["status"] = "review_pending"
            case_record["blocked_reason"] = sanitize_diagnostic(str(exc), 500)
            result["cases"].append(case_record)
            _write_analysis_artifacts(case_root, case_record)
            atomic_write_json(case_root / "case.json", case_record)
            continue
        case_record["analysis_decision"] = analysis
        _write_analysis_artifacts(case_root, case_record)
        atomic_write_json(case_root / "case.json", case_record)
        chosen_skill = analysis.get("skill")
        mechanically_allowed = (
            analysis["classification"] == "skill"
            and chosen_skill in allowed_skills
            and bool(analysis["repair_paths"])
            and bool(analysis["evidence"])
            and all(
                "sha256:" in item
                and any(path and digest and path in item and digest in item for path, digest in prompt_evidence["artifacts"])
                for item in analysis["evidence"]
            )
        )
        if not mechanically_allowed:
            case_record["status"] = "review_pending"
            case_record["blocked_reason"] = "analysis_does_not_meet_fixed_skill_repair_gate"
        elif analyze_only:
            case_record["status"] = "analysis_complete_review_pending"
            case_record["blocked_reason"] = "analyze_only_requested"
        elif repair_attempts_started >= max_repairs:
            case_record["status"] = "stopped_by_repair_limit"
            case_record["blocked_reason"] = "global_repair_attempt_limit_reached"
        else:
            base_allowed_paths = _allowed_repair_paths(chosen_skill, parent_package)
            requested_paths = set()
            for raw_path in analysis["repair_paths"]:
                path = PurePosixPath(raw_path)
                if path.is_absolute() or ".." in path.parts:
                    mechanically_allowed = False
                    break
                candidate = path.as_posix()
                if candidate.startswith(chosen_skill + "/"):
                    candidate = candidate[len(chosen_skill) + 1:]
                if candidate not in base_allowed_paths:
                    mechanically_allowed = False
                    break
                requested_paths.add(candidate)
            if not mechanically_allowed:
                case_record["status"] = "review_pending"
                case_record["blocked_reason"] = "analysis_requested_path_outside_single_skill_allowlist"
            else:
                package_path = parent_package
                package_manifest = baseline_manifest
                for repair_index in range(1, max_repairs + 1):
                    if repair_attempts_started >= max_repairs:
                        case_record["status"] = "stopped_by_repair_limit"
                        case_record["blocked_reason"] = "global_repair_attempt_limit_reached"
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
                        case_record["blocked_reason"] = "insufficient_budget_for_two_candidate_attempts"
                        break
                    trial_root = case_root / "repair-trials" / f"trial-{repair_index:02d}"
                    trial_root.mkdir(parents=True)
                    repair_workspace = trial_root / "workspace"
                    (repair_workspace / ".agents").mkdir(parents=True)
                    shutil.copytree(package_path / "skills", repair_workspace / ".agents" / "skills")
                    repair_output = repair_workspace / ".qa-eval-output"
                    repair_output.mkdir()
                    skill_root = repair_workspace / ".agents" / "skills" / chosen_skill
                    before = _source_paths(package_path, chosen_skill)
                    allowed_for_prompt = [f"{chosen_skill}/{item}" for item in sorted(requested_paths)]
                    repair_prompt = build_repair_prompt(
                        analysis=json.dumps(analysis, ensure_ascii=False),
                        allowed_paths=allowed_for_prompt,
                        baseline_sha=baseline["skill_revision"],
                    )
                    repair_command = [
                        item.replace("{workspace}", str(repair_workspace)).replace("{output_root}", str(repair_output))
                        for item in baseline["agent_command_template"]
                    ]
                    repair_mount = f"type=bind,source={skill_root},target=/workspace/.agents/skills/{chosen_skill}"
                    repair_command = _insert_mount_before_image(repair_command, repair_mount)
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
                    repair_execution = run_command(
                        repair_named,
                        input_text=repair_prompt,
                        cwd=repair_workspace,
                        timeout_seconds=min(profile["agent"]["timeout_seconds"], max(1, int(max_seconds - (time.monotonic() - start)))),
                        timeout_cleanup_argv=repair_cleanup,
                    )
                    repair_trace = capture_codex_jsonl_trace(repair_execution.stdout)
                    trial: dict[str, Any] = {
                        "trial": repair_index,
                        "status": "execution_error" if repair_execution.timed_out or repair_execution.exit_code != 0 or repair_execution.cleanup_status == "failed" else "running",
                        "repair_response_sha256": sha256_bytes(repair_trace["final_message"].encode("utf-8")),
                        "repair_response": sanitize_diagnostic(repair_trace["final_message"]),
                        "trace_format": repair_trace["format"],
                        "trace_status": repair_trace["status"],
                        "trace_path": "repair-trace.jsonl" if repair_trace["trace_jsonl"] is not None else None,
                        "isolation": repair_isolation,
                        "container_cleanup_status": repair_execution.cleanup_status,
                        "allowed_paths": sorted(requested_paths),
                        "baseline_package_fingerprint": package_manifest["package_fingerprint"],
                    }
                    if repair_trace["trace_jsonl"] is not None:
                        (trial_root / "repair-trace.jsonl").write_text(
                            repair_trace["trace_jsonl"], encoding="utf-8"
                        )
                    trial_root.mkdir(exist_ok=True)
                    if trial["status"] == "execution_error":
                        trial["stop_reason"] = "repair_agent_execution_error"
                        case_record["repair_trials"].append(trial)
                        atomic_write_json(trial_root / "trial.json", trial)
                        case_record["status"] = "review_pending"
                        break
                    try:
                        changes, _ = _validate_repair_diff(before, repair_workspace / ".agents" / "skills", chosen_skill, requested_paths)
                    except (AgentEvalError, UnicodeDecodeError) as exc:
                        trial["status"] = "review_pending"
                        trial["stop_reason"] = sanitize_diagnostic(str(exc), 500)
                        case_record["repair_trials"].append(trial)
                        atomic_write_json(trial_root / "trial.json", trial)
                        case_record["status"] = "review_pending"
                        break
                    candidate_package = trial_root / "candidate-package"
                    shutil.copytree(repair_workspace / ".agents" / "skills", candidate_package / "skills")
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
                            old_text = old_path.read_text(encoding="utf-8").splitlines(keepends=True) if old_path.is_file() else []
                            new_text = new_path.read_text(encoding="utf-8").splitlines(keepends=True)
                            diff_lines.extend(difflib.unified_diff(old_text, new_text, fromfile=f"a/{chosen_skill}/{relative}", tofile=f"b/{chosen_skill}/{relative}"))
                        except UnicodeDecodeError:
                            diff_lines.append(f"Binary change: {chosen_skill}/{relative} {change['before_sha256']} -> {change['after_sha256']}\n")
                    patch_text = "".join(diff_lines)
                    if _SECRET_RE.search(patch_text):
                        raise AgentEvalError("repair patch contains secret-shaped text")
                    (trial_root / "patch.diff").write_text(patch_text, encoding="utf-8")
                    with zipfile.ZipFile(trial_root / "changed-files.zip", "w", compression=zipfile.ZIP_DEFLATED) as archive:
                        for change in changes:
                            path = revised_root / change["path"]
                            archive.write(path, arcname=f"skills/{chosen_skill}/{change['path']}")
                    trial.update({
                        "status": "candidate_saved",
                        "candidate_revision_status": "uncommitted_patch",
                        "candidate_package_fingerprint": candidate_manifest["package_fingerprint"],
                        "candidate_package_parent_revision": baseline["skill_revision"],
                        "changes": changes,
                        "patch_path": "patch.diff",
                        "changed_files_archive": "changed-files.zip",
                    })
                    result["active_case"]["status"] = "candidate_evaluation_running"
                    result["active_case"]["candidate_package_fingerprint"] = candidate_manifest["package_fingerprint"]
                    atomic_write_json(output_root / "result.json", result)
                    candidate_run_root = trial_root / "re-evaluation"
                    candidate_run_root.mkdir()
                    profile_evidence_source = output_root / evidence_rel
                    profile_evidence_destination = candidate_run_root / evidence_rel
                    profile_evidence_destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(profile_evidence_source, profile_evidence_destination)
                    qts_args = [
                        "--target-root", str(target_root),
                        "--skill-revision", baseline["skill_revision"],
                        "--skill-package-root", str(candidate_package),
                        "--execution-profile", str(profile_path),
                        "--verifier-image", verifier_image,
                        "--output-root", str(candidate_run_root),
                        "--repeat", "2",
                        "--agent-command", *baseline["agent_command_template"],
                    ]
                    qts_exit = run_qts_evaluation(qts_args)
                    candidate_result_path = candidate_run_root / "result.json"
                    if not candidate_result_path.is_file():
                        trial["status"] = "execution_error"
                        trial["stop_reason"] = f"candidate_evaluation_did_not_save_result_exit_{qts_exit}"
                        case_record["repair_trials"].append(trial)
                        atomic_write_json(trial_root / "trial.json", trial)
                        case_record["status"] = "review_pending"
                        break
                    comparison_path = trial_root / "comparison.json"
                    comparison = compare_runs(baseline_result, candidate_result_path)
                    atomic_write_json(comparison_path, comparison)
                    assessment = _assess_improvement(
                        baseline_result,
                        candidate_result_path,
                        chosen_skill,
                        criterion,
                        comparison=comparison,
                    )
                    trial["candidate_run_result"] = str(candidate_result_path)
                    trial["comparison"] = str(comparison_path)
                    trial["assessment"] = assessment
                    trial["status"] = "improvement_demonstrated" if assessment["improvement_demonstrated"] else "reevaluated_review_pending"
                    trial["progress_observed"] = assessment["target_improved_consistently"]
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
                    if assessment["target_improved_consistently"]:
                        case_record["status"] = "review_pending"
                        case_record["blocked_reason"] = "candidate_quality_improved_but_skill_use_or_regression_evidence_is_incomplete"
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
    result["status"] = "improvement_demonstrated" if case_states and all(state == "improvement_demonstrated" for state in case_states) else "review_pending_or_unmet"
    result["finished_at"] = datetime.now(timezone.utc).isoformat()
    result["elapsed_seconds"] = round(time.monotonic() - start, 3)
    atomic_write_json(output_root / "result.json", result)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Analyze saved Agent evaluations and make bounded, isolated Skill repair attempts.")
    parser.add_argument("--baseline-result", type=Path, required=True)
    parser.add_argument("--judge-validation-result", type=Path, required=True)
    parser.add_argument("--target-root", type=Path, required=True)
    parser.add_argument("--execution-profile", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--verifier-image", required=True)
    parser.add_argument("--max-cases", type=int, required=True)
    parser.add_argument("--max-repairs", type=int, required=True)
    parser.add_argument("--max-seconds", type=int, required=True)
    parser.add_argument("--analyze-only", action="store_true")
    args = parser.parse_args(argv)
    if min(args.max_cases, args.max_repairs, args.max_seconds) <= 0 or args.max_cases > 100 or args.max_repairs > 10 or args.max_seconds > 3600:
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
        print(f"improvement run failed: {sanitize_diagnostic(str(exc), 2000)}", file=sys.stderr)
        return 2
    print(json.dumps({"result": str(args.output_root / "result.json"), "status": result["status"]}, ensure_ascii=True))
    return 0 if result["status"] == "improvement_demonstrated" else 1


if __name__ == "__main__":
    raise SystemExit(main())
