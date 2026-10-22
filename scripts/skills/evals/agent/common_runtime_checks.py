from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path, PurePosixPath
from typing import Any

from .common import AgentEvalError, sha256_bytes, trace_confirms_capture_invocation

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
)
_SECRET_RE = re.compile(
    r"(?i)\b(?:Bearer\s+[A-Za-z0-9._~+/=-]{12,}|sk-[A-Za-z0-9_-]{16,}|gh[pousr]_[A-Za-z0-9]{20,}|(?:api[_-]?key|access[_-]?token|refresh[_-]?token|password)\s*[:=]\s*[^\s,;]+)"
)


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
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AgentEvalError(f"{label} returned invalid JSON") from exc
    if not isinstance(value, dict) or not isinstance(value.get("valid"), bool):
        raise AgentEvalError(f"{label} result does not contain a boolean valid field")
    return value


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
    if not trace_confirms_capture_invocation(trace_commands or [], invocation):
        return "tool_trace_does_not_confirm_capture_invocation"
    return None


def _aggregate_capture_status(checks: list[dict[str, Any]]) -> str:
    states = {item["status"] for item in checks}
    if "environment_error" in states:
        return "environment_error"
    if "evidence_unverified" in states:
        return "evidence_unverified"
    if "fail" in states:
        return "fail"
    return "pass"


def evaluate_runtime_captures(
    *,
    capture_root: Path,
    candidate_package_root: Path,
    verifier_image: str,
    fixed_evaluator_root: Path,
    expected_artifacts: list[dict[str, Any]],
    trace_commands: list[dict[str, Any]] | None,
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
        offline = run_candidate_verifier_offline(
            candidate_package_root=candidate_package_root,
            skill=skill,
            request_bytes=request_bytes,
            image=verifier_image,
        )
        if offline["status"] != "verified":
            checks.append(
                {
                    "path": invocation_path.parent.relative_to(capture_root).as_posix(),
                    **offline,
                }
            )
            continue
        fixed_script = (
            fixed_evaluator_root / "skills" / skill / "scripts" / "runtime_contract.py"
        )
        fixed_run = _run(
            [sys.executable, str(fixed_script)], input_bytes=request_bytes, timeout=120
        )
        if fixed_run.returncode != 0:
            checks.append(
                {
                    "path": invocation_path.parent.relative_to(capture_root).as_posix(),
                    "status": "environment_error",
                    "reason": "fixed_runtime_evaluator_failed",
                }
            )
            continue
        fixed = _load_result(fixed_run.stdout, "fixed runtime evaluator")
        candidate = offline["result"]
        mismatched = [
            field
            for field in _SEMANTIC_FIELDS
            if field in fixed
            and field in candidate
            and fixed[field] != candidate[field]
        ]
        captured_mismatched = [
            field
            for field in _SEMANTIC_FIELDS
            if field in captured
            and field in candidate
            and captured[field] != candidate[field]
        ]
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
                "fixed_evaluator_result_sha256": sha256_bytes(fixed_run.stdout),
                "fixed_valid": fixed["valid"],
                "candidate_valid": candidate["valid"],
                "mismatched_semantic_fields": mismatched,
                "captured_mismatched_fields": captured_mismatched,
                "implementation_fingerprint_differences_ignored": True,
                "tool_trace_confirmed": True,
                "network": "none",
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
    verifier_image: str,
    fixed_evaluator_root: Path,
) -> dict[str, Any]:
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
    mismatched = [
        field
        for field in _WORKFLOW_SEMANTIC_FIELDS
        if field in fixed and field in candidate and fixed[field] != candidate[field]
    ]
    captured_mismatched = [
        field
        for field in _WORKFLOW_SEMANTIC_FIELDS
        if field in candidate
        and field in captured
        and candidate[field] != captured[field]
    ]
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
    verifier_image: str,
    fixed_evaluator_root: Path,
    expected_artifacts: list[dict[str, Any]],
    trace_commands: list[dict[str, Any]] | None,
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
        )
        checks.append(
            {
                "path": invocation_path.parent.relative_to(capture_root).as_posix(),
                "skill": "qa-workflow",
                "artifact_path": expected[identity],
                "tool_trace_confirmed": True,
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
