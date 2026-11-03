from __future__ import annotations

import argparse
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

from . import qa_training_store
from .common import (
    MAX_TEXT_BYTES,
    AgentEvalError,
    atomic_write_json,
    atomic_write_text,
    canonical_fingerprint,
    read_regular_file_bytes,
    sha256_bytes,
)
from .common_runtime_checks import (
    _artifact_map,
    _duplicate_invocation_ids,
    _read_invocation,
    _runtime_invocation_files,
)
from .prompt_builder import build_qa_training_store_generation_prompt
from .public_artifact_index import validate as validate_public_artifact_index
from .target_workspace import (
    DEFAULT_TARGET_REVISION,
    _scan_workspace,
    prepare_sanitized_target,
    verify_workspace_unchanged,
)
from .verifier_capture import RUNTIME_SKILLS
from .workspace import (
    assert_clean_checkout,
    create_skill_workspace,
    resolve_commit,
)

REPO_ROOT = Path(__file__).resolve().parents[4]
RUN_SCHEMA_VERSION = 1
ATTEMPT_ID_RE = re.compile(r"^[0-9a-f]{32}$")
_SECRET_TEXT_RE = qa_training_store._SECRET_TEXT_RE
_REQUIRED_RUNTIME_SKILLS = frozenset(
    item["skill"]
    for item in qa_training_store.load_scenario()["required_artifacts"]
    if item["skill"] in RUNTIME_SKILLS
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise AgentEvalError("duplicate JSON key")
        value[key] = item
    return value


def _read_json(path: Path, *, max_bytes: int = MAX_TEXT_BYTES) -> Any:
    try:
        return json.loads(
            read_regular_file_bytes(path, max_bytes=max_bytes).decode("utf-8"),
            object_pairs_hook=_strict_object,
        )
    except (AgentEvalError, UnicodeError, json.JSONDecodeError) as exc:
        raise AgentEvalError(f"invalid JSON evidence: {path.name}") from exc


def _assert_no_symlink_components(path: Path) -> None:
    absolute = Path(os.path.abspath(path))
    current = Path(absolute.anchor)
    for part in absolute.parts[1:]:
        current /= part
        try:
            if stat.S_ISLNK(current.lstat().st_mode):
                raise AgentEvalError("evaluation path may not contain symlinks")
        except FileNotFoundError:
            continue


def _run_root(path: Path, *, create: bool = False) -> Path:
    root = Path(os.path.abspath(path))
    repository = REPO_ROOT.resolve()
    try:
        relative = root.relative_to(repository)
    except ValueError as exc:
        raise AgentEvalError(
            "QTS run root must be under the Evaluator checkout"
        ) from exc
    if len(relative.parts) < 2 or relative.parts[0] != ".agent-eval-runs":
        raise AgentEvalError("QTS run root must be under .agent-eval-runs/")
    _assert_no_symlink_components(root)
    if create:
        if root.exists():
            raise AgentEvalError("QTS run root must not already exist")
        root.mkdir(parents=True, mode=0o700)
        root.chmod(0o700)
    elif not root.is_dir():
        raise AgentEvalError("QTS run root does not exist")
    return root


def _git_head(root: Path) -> str:
    completed = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "--verify", "HEAD"],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        shell=False,
        timeout=30,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if completed.returncode != 0:
        raise AgentEvalError("Evaluator revision could not be resolved")
    return completed.stdout.strip()


def _evaluator_source_fingerprints() -> dict[str, str]:
    paths = (
        "scripts/skills/evals/agent/qa_training_store.py",
        "scripts/skills/evals/agent/target_workspace.py",
        "scripts/skills/evals/agent/prompt_builder.py",
        "scripts/skills/evals/agent/public_artifact_index.py",
        "scripts/skills/evals/agent/verifier_capture.py",
        "scripts/skills/evals/agent/common_runtime_checks.py",
        "scripts/skills/evals/agent/common.py",
        "scripts/skills/evals/agent/workspace.py",
        "scripts/skills/evals/agent/qts_subagent_eval.py",
        (
            "scripts/skills/evals/agent/scenarios/"
            "qa-training-store-checkout-payment-web-v1/scenario.json"
        ),
        (
            "scripts/skills/evals/agent/scenarios/"
            "qa-training-store-checkout-payment-web-v1/task.md"
        ),
        (
            "scripts/skills/evals/agent/scenarios/"
            "qa-training-store-checkout-payment-web-v1/rubric.json"
        ),
    )
    fingerprints: dict[str, str] = {}
    for relative in paths:
        path = REPO_ROOT / relative
        fingerprints[relative] = sha256_bytes(
            read_regular_file_bytes(path, max_bytes=10_000_000)
        )
    return fingerprints


def _selected_skills(scenario: dict[str, Any]) -> list[str]:
    names = {row["skill"] for row in scenario["required_artifacts"]}
    names.add("question-analysis")
    return sorted(names)


def _copy_selected_skill_packages(
    source_root: Path,
    destination: Path,
    selected: list[str],
    package_manifest: dict[str, Any],
) -> dict[str, Any]:
    source_skills = source_root / "skills"
    target_skills = destination / "skills"
    target_skills.mkdir(parents=True, exist_ok=False)
    selected_files: list[dict[str, Any]] = []
    for row in package_manifest["files"]:
        parts = PurePosixPath(row["path"]).parts
        if len(parts) < 3 or parts[0] != "skills" or parts[1] not in selected:
            continue
        source = source_skills.joinpath(*parts[1:])
        content = read_regular_file_bytes(source, max_bytes=MAX_TEXT_BYTES)
        target = target_skills.joinpath(*parts[1:])
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        selected_files.append(dict(row))
    present = {
        PurePosixPath(row["path"]).parts[1]
        for row in selected_files
        if row["path"].endswith("/SKILL.md")
    }
    if present != set(selected):
        raise AgentEvalError("fixed Skill package is missing a required SKILL.md")
    selected_files.sort(key=lambda item: item["path"])
    return {
        "revision": package_manifest["revision"],
        "skills": selected,
        "files": selected_files,
        "package_fingerprint": canonical_fingerprint(selected_files),
    }


def _attempt_paths(
    root: Path,
    attempt_id: str,
    *,
    run: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], Path]:
    if not ATTEMPT_ID_RE.fullmatch(attempt_id):
        raise AgentEvalError("attempt ID is invalid")
    current_run = run if run is not None else _load_run(root)
    matches = [
        row
        for row in current_run["attempts"]
        if isinstance(row, dict) and row.get("attempt_id") == attempt_id
    ]
    if len(matches) != 1:
        raise AgentEvalError("attempt ID is missing or duplicated")
    attempt_root = root / "attempts" / attempt_id
    _assert_no_symlink_components(attempt_root)
    if not attempt_root.is_dir():
        raise AgentEvalError("attempt directory is missing")
    return matches[0], attempt_root


def _load_run(root: Path) -> dict[str, Any]:
    result = _read_json(root / "result.json")
    if (
        not isinstance(result, dict)
        or result.get("schema_version") != RUN_SCHEMA_VERSION
        or result.get("execution_method") != "codex_subagent_handoff"
        or not isinstance(result.get("attempts"), list)
    ):
        raise AgentEvalError("QTS subagent run record has an invalid contract")
    return result


def _load_attempt_record(attempt_root: Path) -> dict[str, Any]:
    value = _read_json(attempt_root / "evaluator-private" / "attempt.json")
    if not isinstance(value, dict) or value.get("schema_version") != 1:
        raise AgentEvalError("QTS attempt record has an invalid contract")
    return value


def _write_run(root: Path, result: dict[str, Any]) -> None:
    atomic_write_json(root / "result.json", result)


def prepare_run(
    *,
    target_source_root: Path,
    skill_revision: str,
    output_root: Path,
    repeat: int = 2,
    model: str = "gpt-6-luna",
    reasoning_effort: str = "max",
    fork_turns: str = "none",
) -> dict[str, Any]:
    if isinstance(repeat, bool) or not isinstance(repeat, int) or repeat < 2:
        raise AgentEvalError("QTS subagent evaluation requires at least two attempts")
    requested_settings = {
        "model": model,
        "reasoning_effort": reasoning_effort,
        "fork_turns": fork_turns,
    }
    if requested_settings != {
        "model": "gpt-6-luna",
        "reasoning_effort": "max",
        "fork_turns": "none",
    }:
        raise AgentEvalError(
            "QTS subagent settings must use the fixed requested values"
        )

    root = _run_root(output_root, create=True)
    scenario = qa_training_store.load_scenario()
    target_revision = resolve_commit(target_source_root, DEFAULT_TARGET_REVISION)
    target_head = assert_clean_checkout(
        target_source_root, expected_revision=DEFAULT_TARGET_REVISION
    )
    skill_revision = resolve_commit(REPO_ROOT, skill_revision)
    evaluator_revision = _git_head(REPO_ROOT)
    skills = _selected_skills(scenario)
    selected_package_source = root / "evaluator-private" / "qts-skill-package"
    with tempfile.TemporaryDirectory(prefix="qts-skill-package-") as temporary_package:
        full_manifest = create_skill_workspace(
            REPO_ROOT, skill_revision, Path(temporary_package)
        )
        selected_manifest = _copy_selected_skill_packages(
            Path(temporary_package), selected_package_source, skills, full_manifest
        )
    prompt = build_qa_training_store_generation_prompt(
        eval_input=scenario["task_text"],
        required_artifacts=scenario["required_artifacts"],
        target_revision=target_revision,
    )
    result: dict[str, Any] = {
        "schema_version": RUN_SCHEMA_VERSION,
        "execution_method": "codex_subagent_handoff",
        "run_id": uuid.uuid4().hex,
        "created_at": _now(),
        "scenario_id": scenario["scenario_id"],
        "target_revision": target_revision,
        "target_source_checkout_head": target_head,
        "skill_revision": skill_revision,
        "evaluator_revision": evaluator_revision,
        "evaluator_source_fingerprints": _evaluator_source_fingerprints(),
        "scenario_fingerprint": scenario["scenario_fingerprint"],
        "prompt_fingerprint": sha256_bytes(prompt.encode("utf-8")),
        "requested_settings": requested_settings,
        "effective_model_status": "unverified",
        "host_tool_trace_status": "unverified",
        "physical_evaluator_read_denial": "unverified",
        "agent_visible_skills": skills,
        "attempts": [],
        "stage2_scope": {
            "judge": "not_run",
            "production_verifier_independent_replay": "evidence_unverified",
            "docker_used": False,
        },
    }
    _write_run(root, result)

    atomic_write_json(
        root / "evaluator-private" / "skill-package-manifest.json", selected_manifest
    )
    atomic_write_text(root / "evaluator-private" / "generation-prompt.md", prompt)
    atomic_write_json(
        root / "evaluator-private" / "scenario-private.json",
        {
            "scenario_fingerprint": scenario["scenario_fingerprint"],
            "rubric_fingerprint": canonical_fingerprint(scenario["rubric"]),
            "reference_paths": scenario["reference_paths"],
        },
    )

    for offset in range(repeat):
        attempt_id = uuid.uuid4().hex
        attempt_root = root / "attempts" / attempt_id
        private_root = attempt_root / "evaluator-private"
        target_root = attempt_root / "target"
        private_root.mkdir(parents=True, mode=0o700)
        row: dict[str, Any] = {
            "attempt_id": attempt_id,
            "attempt_number": offset + 1,
            "status": "preparing",
            "target_relative_path": f"attempts/{attempt_id}/target",
            "requested_settings": requested_settings,
        }
        result["attempts"].append(row)
        _write_run(root, result)
        try:
            per_attempt_package = private_root / "skill-packages"
            per_attempt_manifest = _copy_selected_skill_packages(
                selected_package_source,
                per_attempt_package,
                skills,
                selected_manifest,
            )
            target_result = prepare_sanitized_target(
                source_root=target_source_root,
                source_revision=target_revision,
                candidate_skills_root=per_attempt_package / "skills",
                verifier_capture_source=REPO_ROOT
                / "scripts/skills/evals/agent/verifier_capture.py",
                destination=target_root,
            )
            baseline_path = private_root / "target-baseline.json"
            atomic_write_json(baseline_path, target_result["baseline_manifest"])
            atomic_write_text(private_root / "generation-prompt.md", prompt)
            private_record = {
                "schema_version": 1,
                "attempt_id": attempt_id,
                "prepared_at": _now(),
                "scenario_id": scenario["scenario_id"],
                "scenario_fingerprint": scenario["scenario_fingerprint"],
                "target_revision": target_revision,
                "target_manifest_fingerprint": target_result[
                    "source_manifest_fingerprint"
                ],
                "target_baseline_manifest_fingerprint": target_result[
                    "baseline_manifest_fingerprint"
                ],
                "synthetic_baseline_revision": target_result[
                    "synthetic_baseline_revision"
                ],
                "skill_revision": skill_revision,
                "skill_package": per_attempt_manifest,
                "prompt_fingerprint": sha256_bytes(prompt.encode("utf-8")),
                "requested_settings": requested_settings,
                "effective_model_status": "unverified",
                "physical_evaluator_read_denial": "unverified",
                "target_workspace_preflight": verify_workspace_unchanged(
                    target_root,
                    target_result["baseline_manifest"],
                    expected_synthetic_baseline_revision=target_result[
                        "synthetic_baseline_revision"
                    ],
                ),
            }
            if not private_record["target_workspace_preflight"]["unchanged"]:
                raise AgentEvalError("prepared target failed its integrity preflight")
            atomic_write_json(private_root / "attempt.json", private_record)
            row.update(
                {
                    "status": "prepared",
                    "synthetic_baseline_revision": target_result[
                        "synthetic_baseline_revision"
                    ],
                    "skill_package_fingerprint": per_attempt_manifest[
                        "package_fingerprint"
                    ],
                    "prompt_fingerprint": private_record["prompt_fingerprint"],
                }
            )
            _write_run(root, result)
        except Exception as exc:
            row.update(
                {
                    "status": "preparation_failed",
                    "failure": type(exc).__name__,
                    "failed_at": _now(),
                }
            )
            _write_run(root, result)
            raise
    return result


def record_execution(
    *,
    run_root: Path,
    attempt_id: str,
    execution_status: str,
    started_at: str,
    finished_at: str,
    submitted_prompt_fingerprint: str | None,
    host_observation: str = "codex_subagent_tool_returned",
) -> dict[str, Any]:
    if execution_status not in {"completed", "failed", "not_started"}:
        raise AgentEvalError("execution status is invalid")
    for label, value in (("started_at", started_at), ("finished_at", finished_at)):
        if not isinstance(value, str) or not value:
            raise AgentEvalError(f"{label} must be an ISO-8601 timestamp")
        try:
            datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise AgentEvalError(f"{label} must be an ISO-8601 timestamp") from exc
    if host_observation not in {
        "codex_subagent_tool_returned",
        "codex_subagent_tool_failed",
        "not_observed",
    }:
        raise AgentEvalError("host observation is invalid")
    root = _run_root(run_root)
    run = _load_run(root)
    row, attempt_root = _attempt_paths(root, attempt_id, run=run)
    if row.get("status") != "prepared":
        raise AgentEvalError("only a prepared QTS attempt can be executed")
    record_path = attempt_root / "evaluator-private" / "attempt.json"
    record = _load_attempt_record(attempt_root)
    prepared_prompt_fingerprint = record.get("prompt_fingerprint")
    if submitted_prompt_fingerprint is not None and not re.fullmatch(
        r"sha256:[0-9a-f]{64}", submitted_prompt_fingerprint
    ):
        raise AgentEvalError("submitted prompt fingerprint is invalid")
    prompt_matches_prepared = (
        isinstance(submitted_prompt_fingerprint, str)
        and submitted_prompt_fingerprint == prepared_prompt_fingerprint
    )
    execution = {
        "observed_at": _now(),
        "status": execution_status,
        "observation_source": host_observation,
        "started_at": started_at,
        "finished_at": finished_at,
        "requested_settings": record["requested_settings"],
        "submitted_prompt_fingerprint": submitted_prompt_fingerprint,
        "prepared_prompt_fingerprint": prepared_prompt_fingerprint,
        "prompt_matches_prepared": prompt_matches_prepared,
        "prompt_match_status": "verified_match"
        if prompt_matches_prepared
        else "unverified_or_mismatch",
        "effective_model_status": "unverified",
        "tool_trace_status": "unverified",
        "agent_self_report_used_as_execution_proof": False,
    }
    record["execution"] = execution
    atomic_write_json(record_path, record)
    row.update({"status": "execution_recorded", "execution": execution})
    _write_run(root, run)
    return execution


def _scan_output_tree(output_root: Path, scenario: dict[str, Any]) -> dict[str, Any]:
    _assert_no_symlink_components(output_root)
    if output_root.is_symlink() or not output_root.is_dir():
        raise AgentEvalError("QTS output root is missing or unsafe")
    files: list[dict[str, Any]] = []
    total = 0
    secret_paths: list[str] = []
    for path in sorted(output_root.rglob("*")):
        relative_path = path.relative_to(output_root)
        relative = relative_path.as_posix()
        if path.is_symlink():
            raise AgentEvalError(f"QTS output contains a symlink: {relative}")
        info = path.lstat()
        if stat.S_ISDIR(info.st_mode):
            continue
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise AgentEvalError(f"QTS output contains an unsafe file: {relative}")
        if "\\" in relative or any(
            part in {"", ".", ".."} for part in relative_path.parts
        ):
            raise AgentEvalError("QTS output contains a non-canonical path")
        per_file_limit = (
            scenario["max_artifact_file_bytes"]
            if relative.endswith(".md") or relative == "artifact-index.json"
            else 20_000_000
        )
        raw = read_regular_file_bytes(path, max_bytes=per_file_limit)
        total += len(raw)
        if total > scenario["max_artifact_total_bytes"]:
            raise AgentEvalError("QTS output exceeds the total size limit")
        try:
            decoded = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise AgentEvalError(f"QTS output is not UTF-8: {relative}") from exc
        is_secret_shaped = bool(_SECRET_TEXT_RE.search(decoded))
        if is_secret_shaped:
            secret_paths.append(relative)
        files.append(
            {
                "path": relative,
                "size": len(raw),
                "sha256": None if is_secret_shaped else sha256_bytes(raw),
                "classification": (
                    "runner_internal"
                    if relative == "artifact-index.json"
                    else "runtime_evidence"
                    if relative.startswith(".runtime-evidence/")
                    else "markdown_candidate"
                    if relative.endswith(".md")
                    else "unregistered_or_internal"
                ),
                "secret_shaped": is_secret_shaped,
            }
        )
    return {
        "files": files,
        "total_bytes": total,
        "secret_shaped_paths": secret_paths,
        "safe_to_copy": not secret_paths,
    }


def _validate_runtime_bindings(
    output_root: Path, artifacts: list[dict[str, Any]]
) -> dict[str, Any]:
    capture_root = output_root / ".runtime-evidence"
    if not capture_root.exists():
        return {
            "status": "evidence_unverified",
            "independent_replay": "evidence_unverified",
            "invocations": [],
            "issues": [{"kind": "runtime_evidence_missing"}],
            "required_skills_without_capture": sorted(_REQUIRED_RUNTIME_SKILLS),
        }
    if capture_root.is_symlink() or not capture_root.is_dir():
        return {
            "status": "evidence_unverified",
            "independent_replay": "evidence_unverified",
            "invocations": [],
            "issues": [{"kind": "runtime_capture_root_unsafe"}],
            "required_skills_without_capture": sorted(_REQUIRED_RUNTIME_SKILLS),
        }
    issues: list[dict[str, Any]] = []
    invocations: list[dict[str, Any]] = []
    captured_skills: set[str] = set()
    expected_artifacts = _artifact_map(artifacts)
    duplicate_ids = _duplicate_invocation_ids(capture_root)
    invocation_paths = _runtime_invocation_files(capture_root)
    for path in invocation_paths:
        try:
            invocation = _read_json(path)
            if not isinstance(invocation, dict):
                raise AgentEvalError("invocation must be an object")
            invocation, request_bytes, result_bytes = _read_invocation(
                capture_root, path
            )
            skill = invocation.get("skill")
            identity = (skill, invocation.get("artifact_id"))
            artifact_path = expected_artifacts.get(identity)
            if artifact_path is None:
                raise AgentEvalError(
                    "runtime invocation is not bound to a registered artifact"
                )
            artifact = next(
                row
                for row in artifacts
                if row.get("skill") == skill and row.get("path") == artifact_path
            )
            if invocation.get("invocation_id") in duplicate_ids:
                raise AgentEvalError("duplicate runtime invocation ID")
            request_json = json.loads(
                request_bytes.decode("utf-8"), object_pairs_hook=_strict_object
            )
            result_json = json.loads(
                result_bytes.decode("utf-8"), object_pairs_hook=_strict_object
            )
            if not isinstance(request_json, dict) or not isinstance(result_json, dict):
                raise AgentEvalError("runtime request and result must be JSON objects")
            operation = invocation.get("operation")
            if operation not in {"verify", "workflow-runtime"}:
                raise AgentEvalError("runtime operation is invalid")
            if operation == "verify" and (
                request_json.get("operation") != "verify_runtime_evidence"
                or not isinstance(result_json.get("valid"), bool)
            ):
                raise AgentEvalError(
                    "runtime verifier request/result contract is invalid"
                )
            if operation == "workflow-runtime" and not isinstance(
                result_json.get("payload"), dict
            ):
                raise AgentEvalError("workflow runtime result contract is invalid")
            claimed_valid = result_json.get("valid") if operation == "verify" else None
            can_complete = (
                result_json.get("payload", {}).get("can_complete")
                if operation == "workflow-runtime"
                and isinstance(result_json.get("payload"), dict)
                else None
            )
            captured_skills.add(skill)
            execution_claim_valid = (
                invocation.get("evidence_status") == "captured"
                and invocation.get("exit_code") == 0
                and invocation.get("timed_out") is False
            )
            if not execution_claim_valid:
                issues.append(
                    {
                        "kind": "runtime_capture_claim_not_successful",
                        "path": path.relative_to(output_root).as_posix(),
                    }
                )
            if claimed_valid is False:
                issues.append(
                    {
                        "kind": "runtime_verifier_reported_invalid",
                        "path": path.relative_to(output_root).as_posix(),
                    }
                )
            invocations.append(
                {
                    "skill": skill,
                    "artifact_id": artifact["artifact_id"],
                    "artifact_path": artifact_path,
                    "operation": operation,
                    "request_sha256": invocation["request_sha256"],
                    "result_sha256": invocation["result_sha256"],
                    "capture_record_integrity": "consistent",
                    "execution_claim_consistent": execution_claim_valid,
                    "agent_generated_execution_claim": invocation.get(
                        "evidence_status"
                    ),
                    "tool_trace_status": "unverified",
                    "captured_valid_claim": claimed_valid,
                    "workflow_can_complete_claim": can_complete,
                    "independent_replay": "evidence_unverified",
                }
            )
        except (
            AgentEvalError,
            OSError,
            UnicodeError,
            json.JSONDecodeError,
            ValueError,
        ) as exc:
            issues.append(
                {
                    "kind": "runtime_invocation_unverified",
                    "path": path.relative_to(output_root).as_posix(),
                    "reason": type(exc).__name__,
                }
            )
    found_invocation_paths = {path.parent.resolve() for path in invocation_paths}
    for path in sorted(capture_root.rglob("*")):
        if path.is_dir() or path.is_symlink():
            continue
        if path.name in {
            "request.json",
            "result.json",
            "invocation.json",
            "stderr.txt",
        }:
            parent = path.parent.resolve()
            if parent not in found_invocation_paths:
                issues.append(
                    {
                        "kind": "runtime_file_without_invocation",
                        "path": path.relative_to(output_root).as_posix(),
                    }
                )
    missing_skills = sorted(_REQUIRED_RUNTIME_SKILLS - captured_skills)
    if missing_skills:
        issues.append(
            {"kind": "required_runtime_capture_missing", "skills": missing_skills}
        )
    if not invocations and not issues:
        issues.append({"kind": "runtime_evidence_missing"})
    return {
        "status": "evidence_unverified" if issues else "capture_integrity_consistent",
        "independent_replay": "evidence_unverified",
        "invocations": invocations,
        "issues": issues,
        "required_skills_without_capture": missing_skills,
    }


def capture_attempt(*, run_root: Path, attempt_id: str) -> dict[str, Any]:
    root = _run_root(run_root)
    run = _load_run(root)
    row, attempt_root = _attempt_paths(root, attempt_id, run=run)
    record = _load_attempt_record(attempt_root)
    capture_path = attempt_root / "evaluator-private" / "capture.json"
    if capture_path.exists() or capture_path.is_symlink():
        raise AgentEvalError("QTS output capture is immutable and already exists")
    target_root = attempt_root / "target"
    output_root = target_root / ".qa-eval-output"
    if record.get("execution") is None:
        raise AgentEvalError(
            "host execution observation must be recorded before capture"
        )
    baseline = _read_json(attempt_root / "evaluator-private" / "target-baseline.json")
    integrity_before = verify_workspace_unchanged(
        target_root,
        baseline,
        expected_synthetic_baseline_revision=record["synthetic_baseline_revision"],
    )
    capture: dict[str, Any] = {
        "schema_version": 1,
        "attempt_id": attempt_id,
        "captured_at": _now(),
        "host_execution_status": record["execution"]["status"],
        "target_integrity": integrity_before,
        "output": None,
        "copy": None,
        "status": "captured_ungraded",
        "issues": [],
    }
    try:
        output_scan = _scan_output_tree(
            output_root, qa_training_store.load_scenario()
        )
        capture["output"] = output_scan
        if not output_scan["safe_to_copy"]:
            capture["issues"].append(
                {
                    "kind": "secret_shaped_output",
                    "paths": output_scan["secret_shaped_paths"],
                }
            )
        copied = qa_training_store._copy_safe_agent_output(
            output_root,
            attempt_root / "evaluator-private" / "captured-output",
        )
        capture["copy"] = copied
        if copied["status"] != "saved":
            capture["issues"].append({"kind": "output_copy_unverified"})
        unregistered = [
            row["path"]
            for row in output_scan["files"]
            if row["classification"] == "unregistered_or_internal"
        ]
        if unregistered:
            capture["issues"].append(
                {"kind": "unregistered_output_files", "paths": unregistered}
            )
        if not integrity_before["unchanged"]:
            capture["issues"].append({"kind": "target_integrity_failed"})
        capture["source_output_fingerprint"] = canonical_fingerprint(
            [
                {"path": row["path"], "size": row["size"], "sha256": row["sha256"]}
                for row in output_scan["files"]
            ]
        )
        capture["status"] = (
            "captured" if not capture["issues"] else "captured_needs_review"
        )
    except (AgentEvalError, OSError) as exc:
        capture["status"] = "capture_failed"
        capture["issues"].append(
            {"kind": "output_capture_error", "reason": type(exc).__name__}
        )
    atomic_write_json(capture_path, capture)
    row.update(
        {
            "status": capture["status"],
            "capture_fingerprint": canonical_fingerprint(capture),
        }
    )
    _write_run(root, run)
    return capture


def evaluate_attempt(*, run_root: Path, attempt_id: str) -> dict[str, Any]:
    root = _run_root(run_root)
    run = _load_run(root)
    row, attempt_root = _attempt_paths(root, attempt_id, run=run)
    record = _load_attempt_record(attempt_root)
    capture = _read_json(attempt_root / "evaluator-private" / "capture.json")
    evaluation_path = attempt_root / "evaluator-private" / "evaluation.json"
    if evaluation_path.exists() or evaluation_path.is_symlink():
        raise AgentEvalError("QTS evaluation result already exists")
    scenario = qa_training_store.load_scenario()
    target_root = attempt_root / "target"
    output_root = attempt_root / "evaluator-private" / "captured-output"
    baseline = _read_json(attempt_root / "evaluator-private" / "target-baseline.json")
    integrity = verify_workspace_unchanged(
        target_root,
        baseline,
        expected_synthetic_baseline_revision=record["synthetic_baseline_revision"],
    )
    result: dict[str, Any] = {
        "schema_version": 1,
        "attempt_id": attempt_id,
        "evaluated_at": _now(),
        "execution_status": record.get("execution", {}).get("status", "not_observed"),
        "effective_model_status": "unverified",
        "tool_trace_status": "unverified",
        "target_integrity": integrity,
        "capture_status": capture.get("status"),
        "public_artifact_index": None,
        "fixed_artifact_index": None,
        "artifact_manifest": None,
        "runtime_evidence": None,
        "docker_production_verifier_replay": "evidence_unverified",
        "judge_status": "not_run",
        "semantic_status": "not_evaluated",
        "workflow_completion": {
            "status": "not_semantically_verified",
            "claim": None,
        },
        "traceability_status": "evidence_unverified",
        "machine_checks": {
            "artifact_index": "not_run",
            "output_content_hashes": "not_run",
            "runtime_record_binding": "not_run",
            "target_integrity": "pass" if integrity["unchanged"] else "fail",
            "entity_traceability": "evidence_unverified",
        },
        "machine_status": "needs_review",
        "overall_status": "needs_review",
        "issues": [],
    }
    result["issues"].extend(capture.get("issues", []))
    if result["execution_status"] != "completed":
        result["issues"].append({"kind": "host_execution_not_completed"})
    execution = record.get("execution")
    if not isinstance(execution, dict) or execution.get("prompt_matches_prepared") is not True:
        result["issues"].append({"kind": "handoff_prompt_not_verified"})
    if not integrity["unchanged"]:
        result["issues"].append({"kind": "target_integrity_failed_after_capture"})
    source_output: dict[str, Any] | None = None
    try:
        source_output = _scan_output_tree(target_root / ".qa-eval-output", scenario)
        current_fingerprint = canonical_fingerprint(
            [
                {"path": item["path"], "size": item["size"], "sha256": item["sha256"]}
                for item in source_output["files"]
            ]
        )
        if current_fingerprint != capture.get("source_output_fingerprint"):
            result["issues"].append({"kind": "output_changed_after_capture"})
    except (AgentEvalError, OSError) as exc:
        source_output = None
        result["issues"].append(
            {
                "kind": "output_integrity_failed_after_capture",
                "reason": type(exc).__name__,
            }
        )
    if capture.get("status") == "capture_failed":
        result["issues"].append({"kind": "capture_not_completed"})
    elif integrity["unchanged"] and source_output is not None and output_root.is_dir():
        public_contract = (
            target_root / ".qa-eval-tools" / "artifact-index-contract.json"
        )
        try:
            public = validate_public_artifact_index(output_root, public_contract)
            fixed = qa_training_store.validate_artifact_index(output_root, scenario)
            result["public_artifact_index"] = public
            result["fixed_artifact_index"] = fixed
            manifest = qa_training_store.build_artifact_manifest(output_root, fixed)
            result["artifact_manifest"] = manifest
            result["runtime_evidence"] = _validate_runtime_bindings(
                output_root, fixed["artifacts"]
            )
            result["machine_checks"] = {
                "artifact_index": "pass"
                if fixed.get("status") == "pass" and public.get("valid") is True
                else "needs_review",
                "output_content_hashes": "captured"
                if all(
                    item.get("sha256") is not None
                    for item in result["artifact_manifest"]["files"]
                    if item["classification"] == "qa_artifact"
                )
                else "evidence_unverified",
                "runtime_record_binding": result["runtime_evidence"]["status"],
                "target_integrity": "pass" if integrity["unchanged"] else "fail",
                "entity_traceability": "evidence_unverified",
            }
            result["issues"].extend(
                {"kind": "runtime_evidence_issue", **issue}
                for issue in result["runtime_evidence"]["issues"]
            )
            result["issues"].extend(
                {"kind": "public_artifact_index_issue", **issue}
                for issue in public.get("issues", [])
            )
            result["issues"].extend(
                {"kind": "fixed_artifact_index_issue", **issue}
                for issue in fixed.get("issues", [])
            )
            result["issues"].extend(
                {"kind": "artifact_manifest_unclassified", "path": item["path"]}
                for item in manifest["files"]
                if item["classification"]
                in {
                    "unsafe_filesystem_entry",
                    "unsafe_symlink",
                    "unregistered_or_internal",
                }
            )
            workflow_claims = [
                item["workflow_can_complete_claim"]
                for item in result["runtime_evidence"]["invocations"]
                if item["operation"] == "workflow-runtime"
                and isinstance(item.get("workflow_can_complete_claim"), bool)
            ]
            if workflow_claims:
                result["workflow_completion"] = {
                    "status": "claimed_complete_unverified"
                    if any(workflow_claims)
                    else "claimed_incomplete_unverified",
                    "claim": workflow_claims[-1],
                }
            structurally_valid = (
                public.get("valid") is True
                and fixed.get("status") == "pass"
                and result["runtime_evidence"]["status"]
                == "capture_integrity_consistent"
                and not result["issues"]
                and capture.get("status") == "captured"
            )
            result["machine_status"] = "pass" if structurally_valid else "needs_review"
            result["overall_status"] = "needs_review"
        except (AgentEvalError, OSError, ValueError, json.JSONDecodeError) as exc:
            result["issues"].append(
                {"kind": "evaluation_error", "reason": type(exc).__name__}
            )
    atomic_write_json(evaluation_path, result)
    row.update(
        {
            "status": result["overall_status"],
            "evaluation_path": (
                f"attempts/{attempt_id}/evaluator-private/evaluation.json"
            ),
            "evaluation_fingerprint": canonical_fingerprint(result),
        }
    )
    _write_run(root, run)
    return result


def _print_json(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Prepare and evaluate host-run QTS subagent attempts."
    )
    commands = parser.add_subparsers(dest="command", required=True)
    prepare = commands.add_parser("prepare")
    prepare.add_argument("--target-source-root", type=Path, required=True)
    prepare.add_argument("--skill-revision", required=True)
    prepare.add_argument("--output-root", type=Path, required=True)
    prepare.add_argument("--repeat", type=int, default=2)
    prepare.add_argument("--model", default="gpt-6-luna")
    prepare.add_argument("--reasoning-effort", default="max")
    prepare.add_argument("--fork-turns", default="none")
    record = commands.add_parser("record-execution")
    record.add_argument("--run-root", type=Path, required=True)
    record.add_argument("--attempt-id", required=True)
    record.add_argument(
        "--execution-status",
        choices=("completed", "failed", "not_started"),
        required=True,
    )
    record.add_argument("--started-at", required=True)
    record.add_argument("--finished-at", required=True)
    record.add_argument("--submitted-prompt-fingerprint")
    record.add_argument("--host-observation", default="codex_subagent_tool_returned")
    capture = commands.add_parser("capture")
    capture.add_argument("--run-root", type=Path, required=True)
    capture.add_argument("--attempt-id", required=True)
    evaluate = commands.add_parser("evaluate")
    evaluate.add_argument("--run-root", type=Path, required=True)
    evaluate.add_argument("--attempt-id", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            result = prepare_run(
                target_source_root=args.target_source_root,
                skill_revision=args.skill_revision,
                output_root=args.output_root,
                repeat=args.repeat,
                model=args.model,
                reasoning_effort=args.reasoning_effort,
                fork_turns=args.fork_turns,
            )
        elif args.command == "record-execution":
            result = record_execution(
                run_root=args.run_root,
                attempt_id=args.attempt_id,
                execution_status=args.execution_status,
                started_at=args.started_at,
                finished_at=args.finished_at,
                submitted_prompt_fingerprint=args.submitted_prompt_fingerprint,
                host_observation=args.host_observation,
            )
        elif args.command == "capture":
            result = capture_attempt(run_root=args.run_root, attempt_id=args.attempt_id)
        else:
            result = evaluate_attempt(
                run_root=args.run_root, attempt_id=args.attempt_id
            )
    except (AgentEvalError, OSError, ValueError) as exc:
        print(
            f"QTS subagent evaluation failed: {type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        return 2
    _print_json(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
