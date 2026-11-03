from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path, PurePosixPath
from typing import Any

from . import isolated_verifier
from .common import (
    AgentEvalError,
    sanitize_diagnostic,
    sha256_bytes,
    trace_confirms_capture_invocation,
)

_IMAGE_RE = re.compile(r"^(?:[A-Za-z0-9./_-]+@)?sha256:[0-9a-f]{64}$")
_RUNTIME_SKILLS = frozenset(
    {
        "coverage-analysis",
        "qa-workflow",
        "spec-analysis",
        "test-analysis",
        "test-case-design",
        "test-condition-design",
        "test-requirement-design",
        "usability-inspection",
        "wcag-conformance-evaluation",
    }
)
_SEMANTIC_FIELDS = (
    "valid",
    "result_status",
    "missing",
    "extra",
    "incomplete_pairs",
    "duplicates",
    "expected_runtime_units",
    "actual_runtime_units",
    "missing_entities",
    "extra_entities",
    "duplicate_entities",
    "current_structure_state",
)
_WORKFLOW_SEMANTIC_FIELDS = (
    "runtime_status",
    "support_status",
    "result_status",
    "issues",
    "expected_runtime_units",
    "runtime_units",
    "missing_runtime_units",
    "extra_runtime_units",
    "missing_entities",
    "extra_entities",
    "payload.can_complete",
)
_SECRET_RE = re.compile(
    r"(?i)\b(?:Bearer\s+[A-Za-z0-9._~+/=-]{12,}|sk-[A-Za-z0-9_-]{16,}|gh[pousr]_[A-Za-z0-9]{20,}|(?:api[_-]?key|access[_-]?token|refresh[_-]?token|password)\s*[:=]\s*[^\s,;]+)"
)
_MAX_REPLAY_DIAGNOSTIC_BYTES = 16_000


def _run(
    argv: list[str],
    *,
    input_bytes: bytes | None = None,
    timeout: int = 120,
    timeout_cleanup_argv: list[str] | None = None,
) -> subprocess.CompletedProcess[bytes]:
    try:
        return subprocess.run(
            argv,
            input=input_bytes,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
            shell=False,
        )
    except subprocess.TimeoutExpired:
        cleanup_status = "not_required"
        if timeout_cleanup_argv:
            try:
                cleanup = subprocess.run(
                    timeout_cleanup_argv,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=15,
                    check=False,
                    shell=False,
                )
                cleanup_status = "succeeded" if cleanup.returncode == 0 else "failed"
            except (OSError, subprocess.TimeoutExpired):
                cleanup_status = "failed"
        result = subprocess.CompletedProcess(argv, 124, b"", b"timed out")
        result.cleanup_status = cleanup_status
        return result


def _contains_secret_bytes(raw: bytes) -> bool:
    return bool(_SECRET_RE.search(raw.decode("utf-8", errors="replace")))


def _load_result(raw: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_strict_object)
    except (UnicodeDecodeError, ValueError) as exc:
        raise AgentEvalError(f"{label} returned invalid JSON") from exc
    if not isinstance(value, dict) or not isinstance(value.get("valid"), bool):
        raise AgentEvalError(f"{label} result does not contain a boolean valid field")
    return value


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("duplicate JSON object key")
        value[key] = item
    return value


def _field_value(value: dict[str, Any], path: str) -> tuple[bool, Any]:
    current: Any = value
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return False, None
        current = current[part]
    return True, current


def _semantic_mismatches(
    reference: dict[str, Any], candidate: dict[str, Any], fields: tuple[str, ...]
) -> list[str]:
    mismatches: list[str] = []
    for field in fields:
        reference_has, reference_value = _field_value(reference, field)
        candidate_has, candidate_value = _field_value(candidate, field)
        if reference_has != candidate_has or (
            reference_has and reference_value != candidate_value
        ):
            mismatches.append(field)
    return mismatches


def _workflow_result_shape_valid(value: dict[str, Any]) -> bool:
    payload = value.get("payload")
    return (
        all(
            isinstance(value.get(field), str)
            for field in ("runtime_status", "support_status", "result_status")
        )
        and isinstance(value.get("issues"), list)
        and isinstance(payload, dict)
        and isinstance(payload.get("can_complete"), bool)
    )


def _isolated_execution_evidence(value: dict[str, Any]) -> dict[str, Any]:
    """Keep bounded diagnostics and identity for one isolated process."""
    return {
        key: value.get(key)
        for key in (
            "status",
            "reason",
            "exit_code",
            "timed_out",
            "timeout_cleanup_verified",
            "elapsed_seconds",
            "source_fingerprint_before",
            "source_fingerprint_after",
            "source_fingerprint",
            "source_unchanged",
            "candidate_executed",
            "verifier_executed",
            "sandbox_process_started",
            "request_sha256",
            "request_unchanged",
            "script_sha256",
            "stdout_sha256",
            "stderr_sha256",
            "stdout_bytes",
            "stderr_bytes",
            "result_sha256",
            "parsed_result_sha256",
            "network_enforcement",
            "network_policy_sha256",
            "runtime",
            "isolation_probe",
        )
        if key in value
    } | {
        key: sanitize_diagnostic(
            str(value.get(key, "")),
            _MAX_REPLAY_DIAGNOSTIC_BYTES - len("\n[truncated]"),
        )
        for key in ("stdout", "stderr")
        if key in value
    }


def _skill_script_root(package_root: Path, skill: str) -> Path:
    if skill not in _RUNTIME_SKILLS:
        raise AgentEvalError("runtime verifier Skill is not allow-listed")
    return package_root / "skills" / skill / "scripts"


def run_candidate_verifier_isolated(
    *,
    candidate_package_root: Path,
    skill: str,
    request_bytes: bytes,
    expected_source_fingerprint: str | None = None,
) -> dict[str, Any]:
    """Replay a candidate verifier only after an OS boundary probe succeeds."""
    script_root = _skill_script_root(candidate_package_root, skill)
    try:
        source_fingerprint = isolated_verifier.source_tree_fingerprint(script_root)
    except (AgentEvalError, OSError) as exc:
        return {
            "status": "evidence_unverified",
            "reason": "candidate_source_invalid",
            "reason_type": type(exc).__name__,
            "candidate_executed": False,
        }
    if (
        expected_source_fingerprint is not None
        and source_fingerprint != expected_source_fingerprint
    ):
        return {
            "status": "evidence_unverified",
            "reason": "candidate_source_fingerprint_mismatch",
            "source_fingerprint": source_fingerprint,
            "candidate_executed": False,
        }
    result = isolated_verifier.run_isolated_python(
        source_dir=script_root,
        script_name="runtime_contract.py",
        request_bytes=request_bytes,
        expected_source_fingerprint=expected_source_fingerprint,
    )
    result["candidate_executed"] = result.get("verifier_executed")
    if result.get("status") == "verified" and (
        not isinstance(result.get("result"), dict)
        or not isinstance(result["result"].get("valid"), bool)
    ):
        result.update(status="execution_error", reason="invalid_verifier_shape")
    if (
        result.get("status") == "verified"
        and expected_source_fingerprint is not None
        and result.get("source_fingerprint") != expected_source_fingerprint
    ):
        result.update(
            status="evidence_unverified",
            reason="candidate_source_fingerprint_changed_during_replay",
        )
    return result


def run_candidate_verifier_offline(
    *, candidate_package_root: Path, skill: str, request_bytes: bytes, image: str
) -> dict[str, Any]:
    if skill not in _RUNTIME_SKILLS:
        raise AgentEvalError("runtime verifier Skill is not allow-listed")
    if not _IMAGE_RE.fullmatch(image):
        raise AgentEvalError("runtime verifier image must be pinned by sha256 digest")
    candidate_package_root = candidate_package_root.resolve()
    script = (
        candidate_package_root / "skills" / skill / "scripts" / "runtime_contract.py"
    )
    if not script.is_file():
        raise AgentEvalError("candidate verifier source is missing")
    inspected = _run(["docker", "image", "inspect", image], timeout=30)
    if inspected.returncode != 0:
        return {
            "status": "environment_error",
            "reason": "pinned_verifier_image_unavailable",
        }
    mount_source = candidate_package_root.as_posix()
    container_name = (
        "qa-eval-verifier-"
        + sha256_bytes((skill + "\0").encode() + request_bytes)[7:19]
    )
    command = [
        "docker",
        "run",
        "--name",
        container_name,
        "--rm",
        "--network",
        "none",
        "--read-only",
        "--tmpfs",
        "/tmp:rw,noexec,nosuid,size=64m",
        "--mount",
        f"type=bind,source={mount_source},target=/candidate,readonly",
        "-i",
        image,
        "python",
        f"/candidate/skills/{skill}/scripts/runtime_contract.py",
    ]
    completed = _run(
        command,
        input_bytes=request_bytes,
        timeout=120,
        timeout_cleanup_argv=["docker", "rm", "-f", container_name],
    )
    if completed.returncode != 0:
        return {
            "status": "environment_error",
            "reason": "candidate_verifier_docker_failed",
            "exit_code": completed.returncode,
            "container_cleanup_status": getattr(
                completed, "cleanup_status", "not_needed"
            ),
        }
    candidate = _load_result(completed.stdout, "candidate verifier")
    return {
        "status": "verified",
        "result": candidate,
        "result_sha256": sha256_bytes(completed.stdout),
        "image": image,
        "network": "none",
        "source_mount": "read_only",
        "root_filesystem": "read_only",
        "command": ["docker", "run", "--rm", "--network", "none", "--read-only", "..."],
        "container_cleanup_status": getattr(completed, "cleanup_status", "not_needed"),
    }


def _runtime_invocation_files(capture_root: Path) -> list[Path]:
    if not capture_root.is_dir():
        return []
    return sorted(
        path
        for path in capture_root.rglob("invocation.json")
        if path.is_file() and not path.is_symlink()
    )


def _capture_file(capture_root: Path, invocation: dict[str, Any], field: str) -> Path:
    raw = invocation.get(field)
    if not isinstance(raw, str):
        raise AgentEvalError("runtime invocation is missing a saved evidence path")
    relative = PurePosixPath(raw)
    if relative.is_absolute() or ".." in relative.parts or len(relative.parts) != 5:
        raise AgentEvalError("runtime invocation evidence path is unsafe")
    if relative.parts[0] != ".runtime-evidence":
        raise AgentEvalError(
            "runtime invocation evidence path is outside its capture root"
        )
    path = capture_root.joinpath(*relative.parts[1:])
    if path.is_symlink():
        raise AgentEvalError("runtime invocation evidence path may not be a symlink")
    resolved_root = capture_root.resolve()
    resolved = path.resolve(strict=True)
    try:
        resolved.relative_to(resolved_root)
    except ValueError as exc:
        raise AgentEvalError(
            "runtime invocation evidence path escapes its capture root"
        ) from exc
    return resolved


def _read_invocation(
    capture_root: Path, invocation_path: Path
) -> tuple[dict[str, Any], bytes, bytes]:
    try:
        invocation = json.loads(invocation_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AgentEvalError("runtime invocation record is missing or invalid") from exc
    if not isinstance(invocation, dict) or invocation.get("schema_version") != 1:
        raise AgentEvalError("runtime invocation record has an invalid schema")
    record_relative_path = invocation.get("record_relative_path")
    if not isinstance(record_relative_path, str):
        raise AgentEvalError("runtime invocation record path is missing")
    expected_record = (
        PurePosixPath(".runtime-evidence")
        / invocation_path.parent.relative_to(capture_root).as_posix()
    )
    if PurePosixPath(record_relative_path) != expected_record:
        raise AgentEvalError(
            "runtime invocation record path does not match its directory"
        )
    record_identity = expected_record.parts[1:]
    if (
        len(record_identity) != 3
        or record_identity[0] != invocation.get("skill")
        or record_identity[1] != invocation.get("artifact_id")
        or record_identity[2] != invocation.get("invocation_id")
    ):
        raise AgentEvalError("runtime invocation identity does not match its directory")
    request_path = _capture_file(capture_root, invocation, "request_relative_path")
    result_path = _capture_file(capture_root, invocation, "result_relative_path")
    if request_path != (invocation_path.parent / "request.json").resolve():
        raise AgentEvalError("runtime invocation references another request directory")
    if result_path != (invocation_path.parent / "result.json").resolve():
        raise AgentEvalError("runtime invocation references another result directory")
    request_bytes = request_path.read_bytes()
    result_bytes = result_path.read_bytes()
    if invocation.get("request_sha256") != sha256_bytes(request_bytes):
        raise AgentEvalError(
            "runtime request hash does not match the invocation record"
        )
    if invocation.get("result_sha256") != sha256_bytes(result_bytes):
        raise AgentEvalError("runtime result hash does not match the invocation record")
    return invocation, request_bytes, result_bytes


def _duplicate_invocation_ids(capture_root: Path) -> set[str]:
    counts: dict[str, int] = {}
    for path in _runtime_invocation_files(capture_root):
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            continue
        if isinstance(value, dict) and isinstance(value.get("invocation_id"), str):
            invocation_id = value["invocation_id"]
            counts[invocation_id] = counts.get(invocation_id, 0) + 1
    return {invocation_id for invocation_id, count in counts.items() if count > 1}


def _artifact_map(
    expected_artifacts: list[dict[str, Any]],
) -> dict[tuple[str, str], str]:
    result: dict[tuple[str, str], str] = {}
    for artifact in expected_artifacts:
        skill = artifact.get("skill")
        path = artifact.get("path")
        if skill not in _RUNTIME_SKILLS or not isinstance(path, str):
            continue
        digest = hashlib.sha256(
            PurePosixPath(path).as_posix().encode("utf-8")
        ).hexdigest()
        result[(skill, digest)] = PurePosixPath(path).as_posix()
    return result


def _capture_issue(
    *,
    invocation: dict[str, Any],
    expected: dict[tuple[str, str], str],
    operation: str,
    trace_commands: list[dict[str, Any]] | None,
    require_tool_trace: bool = True,
) -> str | None:
    identity = (invocation.get("skill"), invocation.get("artifact_id"))
    if not all(isinstance(value, str) for value in identity):
        return "invocation_identity_missing"
    if invocation.get("operation") != operation:
        return "invocation_operation_mismatch"
    if identity not in expected:
        return "invocation_does_not_match_registered_artifact"
    if (
        invocation.get("evidence_status") != "captured"
        or invocation.get("exit_code") != 0
        or invocation.get("timed_out") is not False
    ):
        return "capture_was_unverified_or_failed"
    if require_tool_trace and not trace_confirms_capture_invocation(
        trace_commands or [], invocation
    ):
        return "tool_trace_does_not_confirm_capture_invocation"
    return None


def _aggregate_capture_status(checks: list[dict[str, Any]]) -> str:
    states = {item["status"] for item in checks}
    if "environment_error" in states:
        return "environment_error"
    if "timeout" in states:
        return "timeout"
    if "execution_error" in states:
        return "execution_error"
    if "evidence_unverified" in states:
        return "evidence_unverified"
    if "fail" in states:
        return "fail"
    return "pass"


def evaluate_runtime_captures(
    *,
    capture_root: Path,
    candidate_package_root: Path,
    verifier_image: str | None,
    fixed_evaluator_root: Path,
    expected_artifacts: list[dict[str, Any]],
    trace_commands: list[dict[str, Any]] | None,
    require_tool_trace: bool = True,
    expected_candidate_source_fingerprints: dict[str, str] | None = None,
) -> dict[str, Any]:
    expected = _artifact_map(expected_artifacts)
    checks: list[dict[str, Any]] = []
    observed: set[tuple[str, str]] = set()
    duplicate_ids = _duplicate_invocation_ids(capture_root)
    for invocation_path in _runtime_invocation_files(capture_root):
        try:
            raw_invocation = json.loads(invocation_path.read_text(encoding="utf-8"))
            if (
                not isinstance(raw_invocation, dict)
                or raw_invocation.get("operation") != "verify"
            ):
                continue
            invocation, request_bytes, result_bytes = _read_invocation(
                capture_root, invocation_path
            )
        except (
            OSError,
            UnicodeDecodeError,
            json.JSONDecodeError,
            AgentEvalError,
        ) as exc:
            checks.append(
                {
                    "path": invocation_path.parent.relative_to(capture_root).as_posix(),
                    "status": "evidence_unverified",
                    "reason": type(exc).__name__,
                }
            )
            continue
        identity = (invocation.get("skill"), invocation.get("artifact_id"))
        observed.add(identity)
        if invocation.get("invocation_id") in duplicate_ids:
            checks.append(
                {
                    "path": invocation_path.parent.relative_to(capture_root).as_posix(),
                    "status": "evidence_unverified",
                    "reason": "duplicate_invocation_id",
                }
            )
            continue
        issue = _capture_issue(
            invocation=invocation,
            expected=expected,
            operation="verify",
            trace_commands=trace_commands,
            require_tool_trace=require_tool_trace,
        )
        if issue:
            checks.append(
                {
                    "path": invocation_path.parent.relative_to(capture_root).as_posix(),
                    "status": "evidence_unverified",
                    "reason": issue,
                }
            )
            continue
        if _contains_secret_bytes(request_bytes) or _contains_secret_bytes(
            result_bytes
        ):
            checks.append(
                {
                    "path": invocation_path.parent.relative_to(capture_root).as_posix(),
                    "status": "evidence_unverified",
                    "reason": "secret_shaped_verifier_evidence_not_replayed",
                }
            )
            continue
        try:
            request = json.loads(request_bytes.decode("utf-8"))
            captured = _load_result(result_bytes, "captured verifier")
        except (UnicodeDecodeError, json.JSONDecodeError, AgentEvalError) as exc:
            checks.append(
                {
                    "path": invocation_path.parent.relative_to(capture_root).as_posix(),
                    "status": "evidence_unverified",
                    "reason": type(exc).__name__,
                }
            )
            continue
        if (
            not isinstance(request, dict)
            or request.get("operation") != "verify_runtime_evidence"
        ):
            checks.append(
                {
                    "path": invocation_path.parent.relative_to(capture_root).as_posix(),
                    "status": "evidence_unverified",
                    "reason": "invalid_request_operation",
                }
            )
            continue
        skill = str(invocation["skill"])
        expected_source_fingerprint = (
            expected_candidate_source_fingerprints.get(skill)
            if expected_candidate_source_fingerprints is not None
            else None
        )
        offline = (
            run_candidate_verifier_offline(
                candidate_package_root=candidate_package_root,
                skill=skill,
                request_bytes=request_bytes,
                image=verifier_image,
            )
            if verifier_image is not None
            else run_candidate_verifier_isolated(
                candidate_package_root=candidate_package_root,
                skill=skill,
                request_bytes=request_bytes,
                expected_source_fingerprint=expected_source_fingerprint,
            )
        )
        if offline["status"] != "verified":
            checks.append(
                {
                    "path": invocation_path.parent.relative_to(capture_root).as_posix(),
                    **offline,
                    "candidate_execution": _isolated_execution_evidence(offline),
                }
            )
            continue
        fixed_script = (
            fixed_evaluator_root / "skills" / skill / "scripts" / "runtime_contract.py"
        )
        if verifier_image is None:
            fixed_isolated = isolated_verifier.run_isolated_python(
                source_dir=fixed_script.parent,
                script_name="runtime_contract.py",
                request_bytes=request_bytes,
                timeout_seconds=120,
            )
            if fixed_isolated.get("status") != "verified":
                checks.append(
                    {
                        "path": invocation_path.parent.relative_to(
                            capture_root
                        ).as_posix(),
                        "status": fixed_isolated.get("status", "evidence_unverified"),
                        "reason": fixed_isolated.get(
                            "reason", "fixed_runtime_isolation_unverified"
                        ),
                        "exit_code": fixed_isolated.get("exit_code"),
                        "stdout_sha256": fixed_isolated.get("stdout_sha256"),
                        "stderr_sha256": fixed_isolated.get("stderr_sha256"),
                        "elapsed_seconds": fixed_isolated.get("elapsed_seconds"),
                        "timeout_cleanup_verified": fixed_isolated.get(
                            "timeout_cleanup_verified"
                        ),
                        "isolation_probe": fixed_isolated.get("isolation_probe"),
                        "candidate_executed": offline.get("candidate_executed"),
                        "fixed_execution": _isolated_execution_evidence(fixed_isolated),
                    }
                )
                continue
            fixed = fixed_isolated["result"]
            fixed_result_sha256 = fixed_isolated["result_sha256"]
            fixed_execution = _isolated_execution_evidence(fixed_isolated)
        else:
            fixed_run = _run(
                [sys.executable, str(fixed_script)],
                input_bytes=request_bytes,
                timeout=120,
            )
            if fixed_run.returncode != 0:
                checks.append(
                    {
                        "path": invocation_path.parent.relative_to(
                            capture_root
                        ).as_posix(),
                        "status": "environment_error",
                        "reason": "fixed_runtime_evaluator_failed",
                    }
                )
                continue
            fixed = _load_result(fixed_run.stdout, "fixed runtime evaluator")
            fixed_result_sha256 = sha256_bytes(fixed_run.stdout)
            fixed_execution = {
                "status": "completed",
                "exit_code": fixed_run.returncode,
                "result_sha256": fixed_result_sha256,
            }
        if not isinstance(fixed.get("valid"), bool):
            checks.append(
                {
                    "path": invocation_path.parent.relative_to(capture_root).as_posix(),
                    "status": "evidence_unverified",
                    "reason": "fixed_runtime_evaluator_result_invalid",
                }
            )
            continue
        candidate = offline["result"]
        mismatched = _semantic_mismatches(fixed, candidate, _SEMANTIC_FIELDS)
        captured_mismatched = _semantic_mismatches(
            captured, candidate, _SEMANTIC_FIELDS
        )
        status = (
            "fail"
            if fixed["valid"] is False
            or candidate["valid"] is False
            or mismatched
            or captured_mismatched
            else "pass"
        )
        checks.append(
            {
                "path": invocation_path.parent.relative_to(capture_root).as_posix(),
                "skill": skill,
                "artifact_path": expected[identity],
                "status": status,
                "captured_result_sha256": sha256_bytes(result_bytes),
                "candidate_replay_sha256": offline["result_sha256"],
                "fixed_evaluator_result_sha256": fixed_result_sha256,
                "candidate_execution": _isolated_execution_evidence(offline),
                "fixed_execution": fixed_execution,
                "fixed_valid": fixed["valid"],
                "candidate_valid": candidate["valid"],
                "mismatched_semantic_fields": mismatched,
                "captured_mismatched_fields": captured_mismatched,
                "implementation_fingerprint_differences_ignored": True,
                "tool_trace_confirmed": trace_confirms_capture_invocation(
                    trace_commands or [], invocation
                ),
                "original_agent_execution_proven": trace_confirms_capture_invocation(
                    trace_commands or [], invocation
                ),
                "candidate_source_fingerprint": offline.get("source_fingerprint"),
                "fixed_isolation_probe": fixed_isolated.get("isolation_probe")
                if verifier_image is None
                else None,
                "candidate_isolation_probe": offline.get("isolation_probe"),
                "network": "blocked_by_seccomp" if verifier_image is None else "none",
                "network_enforcement": offline.get("network_enforcement")
                if verifier_image is None
                else None,
                "network_policy_sha256": offline.get("network_policy_sha256")
                if verifier_image is None
                else None,
                "source_mount": "read_only",
            }
        )
    for identity, artifact_path in sorted(expected.items()):
        if identity not in observed:
            checks.append(
                {
                    "skill": identity[0],
                    "artifact_path": artifact_path,
                    "status": "evidence_unverified",
                    "reason": "runtime_verifier_capture_missing",
                }
            )
    if not expected:
        return {
            "status": "pass",
            "captures": [],
            "reason": "no_runtime_enabled_artifacts",
        }
    return {"status": _aggregate_capture_status(checks), "captures": checks}


def _workflow_replay(
    *,
    request_bytes: bytes,
    captured_bytes: bytes,
    candidate_package_root: Path,
    verifier_image: str | None,
    fixed_evaluator_root: Path,
    expected_candidate_source_fingerprint: str | None = None,
) -> dict[str, Any]:
    if verifier_image is None:
        if _contains_secret_bytes(request_bytes) or _contains_secret_bytes(
            captured_bytes
        ):
            return {
                "status": "evidence_unverified",
                "reason": "secret_shaped_workflow_runtime_evidence_not_replayed",
                "candidate_executed": False,
            }
        candidate_source = _skill_script_root(candidate_package_root, "qa-workflow")
        try:
            candidate_fingerprint = isolated_verifier.source_tree_fingerprint(
                candidate_source
            )
        except (AgentEvalError, OSError) as exc:
            return {
                "status": "evidence_unverified",
                "reason": "candidate_workflow_source_invalid",
                "reason_type": type(exc).__name__,
                "candidate_executed": False,
            }
        if (
            expected_candidate_source_fingerprint is not None
            and candidate_fingerprint != expected_candidate_source_fingerprint
        ):
            return {
                "status": "evidence_unverified",
                "reason": "candidate_source_fingerprint_mismatch",
                "source_fingerprint": candidate_fingerprint,
                "candidate_executed": False,
            }
        candidate_run = isolated_verifier.run_isolated_python(
            source_dir=candidate_source,
            script_name="workflow_runtime.py",
            request_bytes=request_bytes,
            expected_source_fingerprint=expected_candidate_source_fingerprint,
        )
        if (
            candidate_run.get("status") == "verified"
            and expected_candidate_source_fingerprint is not None
            and candidate_run.get("source_fingerprint")
            != expected_candidate_source_fingerprint
        ):
            return {
                "status": "evidence_unverified",
                "reason": "candidate_source_fingerprint_changed_during_replay",
                "candidate_executed": True,
                "candidate_source_fingerprint": candidate_run.get("source_fingerprint"),
                "candidate_isolation_probe": candidate_run.get("isolation_probe"),
            }
        if candidate_run.get("status") != "verified":
            return {
                **candidate_run,
                "candidate_source_fingerprint": candidate_fingerprint,
                "candidate_execution": _isolated_execution_evidence(candidate_run),
                "candidate_executed": candidate_run.get("verifier_executed"),
            }
        fixed_script = (
            fixed_evaluator_root
            / "skills"
            / "qa-workflow"
            / "scripts"
            / "workflow_runtime.py"
        )
        fixed_run = isolated_verifier.run_isolated_python(
            source_dir=fixed_script.parent,
            script_name="workflow_runtime.py",
            request_bytes=request_bytes,
            timeout_seconds=120,
        )
        if fixed_run.get("status") != "verified":
            return {
                "status": fixed_run.get("status", "evidence_unverified"),
                "reason": fixed_run.get(
                    "reason", "fixed_workflow_runtime_isolation_unverified"
                ),
                "candidate_executed": True,
                "candidate_source_fingerprint": candidate_fingerprint,
                "candidate_replay_sha256": candidate_run.get("result_sha256"),
                "fixed_exit_code": fixed_run.get("exit_code"),
                "fixed_stdout_sha256": fixed_run.get("stdout_sha256"),
                "fixed_stderr_sha256": fixed_run.get("stderr_sha256"),
                "fixed_elapsed_seconds": fixed_run.get("elapsed_seconds"),
                "fixed_timeout_cleanup_verified": fixed_run.get(
                    "timeout_cleanup_verified"
                ),
                "isolation_probe": fixed_run.get("isolation_probe"),
                "candidate_execution": _isolated_execution_evidence(candidate_run),
                "fixed_execution": _isolated_execution_evidence(fixed_run),
            }
        candidate = candidate_run["result"]
        fixed = fixed_run["result"]
        try:
            captured = json.loads(
                captured_bytes.decode("utf-8"), object_pairs_hook=_strict_object
            )
        except (UnicodeDecodeError, ValueError):
            return {
                "status": "evidence_unverified",
                "reason": "workflow_runtime_replay_invalid_json",
                "candidate_executed": True,
                "candidate_execution": _isolated_execution_evidence(candidate_run),
                "fixed_execution": _isolated_execution_evidence(fixed_run),
            }
        if not isinstance(captured, dict):
            return {
                "status": "evidence_unverified",
                "reason": "workflow_runtime_replay_invalid_shape",
                "candidate_executed": True,
                "candidate_execution": _isolated_execution_evidence(candidate_run),
                "fixed_execution": _isolated_execution_evidence(fixed_run),
            }
        if not all(
            _workflow_result_shape_valid(value)
            for value in (candidate, fixed, captured)
        ):
            return {
                "status": "evidence_unverified",
                "reason": "workflow_runtime_result_contract_invalid",
                "candidate_executed": True,
                "candidate_execution": _isolated_execution_evidence(candidate_run),
                "fixed_execution": _isolated_execution_evidence(fixed_run),
            }
        mismatched = _semantic_mismatches(fixed, candidate, _WORKFLOW_SEMANTIC_FIELDS)
        captured_mismatched = _semantic_mismatches(
            captured, candidate, _WORKFLOW_SEMANTIC_FIELDS
        )
        return {
            "status": "fail" if mismatched or captured_mismatched else "pass",
            "request_sha256": candidate_run["request_sha256"],
            "captured_result_sha256": sha256_bytes(captured_bytes),
            "candidate_replay_sha256": candidate_run["result_sha256"],
            "fixed_evaluator_sha256": fixed_run["result_sha256"],
            "candidate_source_fingerprint": candidate_fingerprint,
            "fixed_source_fingerprint": fixed_run.get("source_fingerprint_before"),
            "candidate_source_unchanged": candidate_run.get("source_unchanged"),
            "fixed_source_unchanged": fixed_run.get("source_unchanged"),
            "candidate_execution": _isolated_execution_evidence(candidate_run),
            "fixed_execution": _isolated_execution_evidence(fixed_run),
            "mismatched_semantic_fields": mismatched,
            "captured_mismatched_fields": captured_mismatched,
            "candidate_isolation_probe": candidate_run.get("isolation_probe"),
            "fixed_isolation_probe": fixed_run.get("isolation_probe"),
            "network": "blocked_by_seccomp",
            "network_enforcement": candidate_run.get("network_enforcement"),
            "network_policy_sha256": candidate_run.get("network_policy_sha256"),
            "fixed_network_policy_sha256": fixed_run.get("network_policy_sha256"),
            "source_mount": "read_only",
            "root_filesystem": "read_only",
            "candidate_executed": True,
            "workflow_runtime_can_complete": fixed.get("payload", {}).get(
                "can_complete"
            )
            if isinstance(fixed.get("payload"), dict)
            else None,
            "workflow_runtime_has_unclosed_issues": bool(fixed.get("issues")),
        }
    if not _IMAGE_RE.fullmatch(verifier_image):
        return {"status": "environment_error", "reason": "verifier_image_not_pinned"}
    if _run(["docker", "image", "inspect", verifier_image], timeout=30).returncode != 0:
        return {
            "status": "environment_error",
            "reason": "pinned_verifier_image_unavailable",
        }
    if _contains_secret_bytes(request_bytes) or _contains_secret_bytes(captured_bytes):
        return {
            "status": "evidence_unverified",
            "reason": "secret_shaped_workflow_runtime_evidence_not_replayed",
        }
    candidate_root = candidate_package_root.resolve().as_posix()
    container_name = "qa-eval-workflow-" + sha256_bytes(request_bytes)[7:19]
    command = [
        "docker",
        "run",
        "--name",
        container_name,
        "--rm",
        "--network",
        "none",
        "--read-only",
        "--tmpfs",
        "/tmp:rw,noexec,nosuid,size=64m",
        "--tmpfs",
        "/workspace:rw,nosuid,size=128m",
        "--mount",
        f"type=bind,source={candidate_root},target=/candidate,readonly",
        "-i",
        verifier_image,
        "python",
        "/candidate/skills/qa-workflow/scripts/workflow_runtime.py",
    ]
    candidate_run = _run(
        command,
        input_bytes=request_bytes,
        timeout=120,
        timeout_cleanup_argv=["docker", "rm", "-f", container_name],
    )
    if candidate_run.returncode != 0:
        return {
            "status": "environment_error",
            "reason": "candidate_workflow_runtime_replay_failed",
            "exit_code": candidate_run.returncode,
            "container_cleanup_status": getattr(
                candidate_run, "cleanup_status", "not_needed"
            ),
        }
    fixed_script = (
        fixed_evaluator_root
        / "skills"
        / "qa-workflow"
        / "scripts"
        / "workflow_runtime.py"
    )
    fixed_run = _run(
        [sys.executable, str(fixed_script)], input_bytes=request_bytes, timeout=120
    )
    if fixed_run.returncode != 0:
        return {
            "status": "environment_error",
            "reason": "fixed_workflow_runtime_evaluator_failed",
            "exit_code": fixed_run.returncode,
        }
    try:
        candidate = json.loads(candidate_run.stdout.decode("utf-8"))
        fixed = json.loads(fixed_run.stdout.decode("utf-8"))
        captured = json.loads(captured_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {
            "status": "evidence_unverified",
            "reason": "workflow_runtime_replay_invalid_json",
        }
    if not all(isinstance(item, dict) for item in (candidate, fixed, captured)):
        return {
            "status": "evidence_unverified",
            "reason": "workflow_runtime_replay_invalid_shape",
        }
    if not all(
        _workflow_result_shape_valid(value) for value in (candidate, fixed, captured)
    ):
        return {
            "status": "evidence_unverified",
            "reason": "workflow_runtime_result_contract_invalid",
        }
    mismatched = _semantic_mismatches(fixed, candidate, _WORKFLOW_SEMANTIC_FIELDS)
    captured_mismatched = _semantic_mismatches(
        captured, candidate, _WORKFLOW_SEMANTIC_FIELDS
    )
    return {
        "status": "fail" if mismatched or captured_mismatched else "pass",
        "request_sha256": sha256_bytes(request_bytes),
        "captured_result_sha256": sha256_bytes(captured_bytes),
        "candidate_replay_sha256": sha256_bytes(candidate_run.stdout),
        "fixed_evaluator_sha256": sha256_bytes(fixed_run.stdout),
        "mismatched_semantic_fields": mismatched,
        "captured_mismatched_fields": captured_mismatched,
        "network": "none",
        "source_mount": "read_only",
        "root_filesystem": "read_only",
        "workflow_runtime_can_complete": fixed.get("payload", {}).get("can_complete")
        if isinstance(fixed.get("payload"), dict)
        else None,
        "workflow_runtime_has_unclosed_issues": bool(fixed.get("issues")),
    }


def evaluate_workflow_runtime_capture(
    *,
    capture_root: Path,
    candidate_package_root: Path,
    verifier_image: str | None,
    fixed_evaluator_root: Path,
    expected_artifacts: list[dict[str, Any]],
    trace_commands: list[dict[str, Any]] | None,
    require_tool_trace: bool = True,
    expected_candidate_source_fingerprint: str | None = None,
) -> dict[str, Any]:
    expected = {
        identity: path
        for identity, path in _artifact_map(expected_artifacts).items()
        if identity[0] == "qa-workflow"
    }
    checks: list[dict[str, Any]] = []
    observed: set[tuple[str, str]] = set()
    duplicate_ids = _duplicate_invocation_ids(capture_root)
    for invocation_path in _runtime_invocation_files(capture_root):
        try:
            raw_invocation = json.loads(invocation_path.read_text(encoding="utf-8"))
            if (
                not isinstance(raw_invocation, dict)
                or raw_invocation.get("operation") != "workflow-runtime"
            ):
                continue
            invocation, request_bytes, result_bytes = _read_invocation(
                capture_root, invocation_path
            )
        except (
            OSError,
            UnicodeDecodeError,
            json.JSONDecodeError,
            AgentEvalError,
        ) as exc:
            checks.append(
                {
                    "path": invocation_path.parent.relative_to(capture_root).as_posix(),
                    "status": "evidence_unverified",
                    "reason": type(exc).__name__,
                }
            )
            continue
        identity = (invocation.get("skill"), invocation.get("artifact_id"))
        observed.add(identity)
        if invocation.get("invocation_id") in duplicate_ids:
            checks.append(
                {
                    "path": invocation_path.parent.relative_to(capture_root).as_posix(),
                    "status": "evidence_unverified",
                    "reason": "duplicate_invocation_id",
                }
            )
            continue
        issue = _capture_issue(
            invocation=invocation,
            expected=expected,
            operation="workflow-runtime",
            trace_commands=trace_commands,
            require_tool_trace=require_tool_trace,
        )
        if issue:
            checks.append(
                {
                    "path": invocation_path.parent.relative_to(capture_root).as_posix(),
                    "status": "evidence_unverified",
                    "reason": issue,
                }
            )
            continue
        replay = _workflow_replay(
            request_bytes=request_bytes,
            captured_bytes=result_bytes,
            candidate_package_root=candidate_package_root,
            verifier_image=verifier_image,
            fixed_evaluator_root=fixed_evaluator_root,
            expected_candidate_source_fingerprint=expected_candidate_source_fingerprint,
        )
        checks.append(
            {
                "path": invocation_path.parent.relative_to(capture_root).as_posix(),
                "skill": "qa-workflow",
                "artifact_path": expected[identity],
                "tool_trace_confirmed": trace_confirms_capture_invocation(
                    trace_commands or [], invocation
                ),
                "original_agent_execution_proven": trace_confirms_capture_invocation(
                    trace_commands or [], invocation
                ),
                **replay,
            }
        )
    for identity, artifact_path in sorted(expected.items()):
        if identity not in observed:
            checks.append(
                {
                    "skill": identity[0],
                    "artifact_path": artifact_path,
                    "status": "evidence_unverified",
                    "reason": "workflow_runtime_capture_missing",
                }
            )
    if not expected:
        return {
            "status": "pass",
            "reason": "qa_workflow_artifact_not_required",
            "captures": [],
        }
    return {"status": _aggregate_capture_status(checks), "captures": checks}
