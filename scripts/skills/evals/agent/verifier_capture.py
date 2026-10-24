from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

_SECRET_RE = re.compile(
    r"(?i)\b(?:Bearer\s+[A-Za-z0-9._~+/=-]{12,}|sk-[A-Za-z0-9_-]{16,}|gh[pousr]_[A-Za-z0-9]{20,}|(?:api[_-]?key|access[_-]?token|refresh[_-]?token|password)\s*[:=]\s*[^\s,;]+)"
)
_ARTIFACT_ID_RE = re.compile(r"^[0-9a-f]{64}$")
_INVOCATION_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,80}$")
RUNTIME_SKILLS = frozenset(
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


def _sanitize(value: str, limit: int = 64_000) -> str:
    cleaned = _SECRET_RE.sub("[redacted]", value)
    encoded = cleaned.encode("utf-8", errors="replace")
    if len(encoded) > limit:
        cleaned = encoded[:limit].decode("utf-8", errors="ignore") + "\n[truncated]"
    return cleaned


def _digest(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def _without_symlinks(path: Path) -> Path:
    absolute = Path(os.path.abspath(path))
    current = Path(absolute.anchor)
    for part in absolute.parts[1:]:
        current /= part
        if current.is_symlink():
            raise ValueError("capture paths may not contain symlinks")
    return absolute.resolve(strict=False)


def _contained(path: Path, root: Path, label: str) -> Path:
    try:
        return path.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"{label} must stay inside .qa-eval-output") from exc


def _expected_script(*, skills_root: Path, skill: str, operation: str) -> Path:
    if skill not in RUNTIME_SKILLS:
        raise ValueError("capture Skill is not allow-listed")
    if operation not in {"verify", "workflow-runtime"}:
        raise ValueError("capture operation is not allow-listed")
    if operation == "workflow-runtime" and skill != "qa-workflow":
        raise ValueError("workflow-runtime is available only for qa-workflow")
    filename = (
        "workflow_runtime.py"
        if operation == "workflow-runtime"
        else "runtime_contract.py"
    )
    skill_root = skills_root / skill
    script = _without_symlinks(skill_root / "scripts" / filename)
    try:
        script.relative_to(_without_symlinks(skill_root))
    except ValueError as exc:
        raise ValueError("candidate runtime script escapes the Skill package") from exc
    if not script.is_file():
        raise FileNotFoundError("candidate Skill runtime script is missing")
    return script


def capture_invocation(
    *, skill: str, operation: str, request_path: Path, record_path: Path
) -> dict[str, Any]:
    cwd = Path.cwd().resolve()
    output_root = _without_symlinks(cwd / ".qa-eval-output")
    evidence_root = _without_symlinks(output_root / ".runtime-evidence")
    request = _without_symlinks(
        request_path if request_path.is_absolute() else cwd / request_path
    )
    record = _without_symlinks(
        record_path if record_path.is_absolute() else cwd / record_path
    )
    relative_request = _contained(request, output_root, "request path").as_posix()
    relative_record = _contained(record, evidence_root, "record path").as_posix()
    record_parts = Path(relative_record).parts
    if (
        len(record_parts) != 3
        or record_parts[0] != skill
        or not _ARTIFACT_ID_RE.fullmatch(record_parts[1])
        or not _INVOCATION_ID_RE.fullmatch(record_parts[2])
    ):
        raise ValueError(
            "record path must be .runtime-evidence/<skill>/<artifact-sha256>/<invocation-id>"
        )
    if request != record / "request.json":
        raise ValueError(
            "request.json must be stored in its invocation record directory"
        )
    if not request.is_file():
        raise FileNotFoundError("saved runtime request is missing")

    record.mkdir(parents=True, exist_ok=True)
    for child in record.iterdir():
        if child != request or child.is_symlink() or not child.is_file():
            raise ValueError(
                "invocation directory may contain only its request.json before capture"
            )
    if any(
        (record / name).exists()
        for name in ("result.json", "invocation.json", "stderr.txt")
    ):
        raise ValueError("invocation id has already been used")

    request_bytes = request.read_bytes()
    if len(request_bytes) > 20_000_000:
        raise ValueError("runtime request exceeds the capture size limit")
    request_text = request_bytes.decode("utf-8")
    request_value = json.loads(request_text)
    if not isinstance(request_value, dict):
        raise ValueError("runtime request must be a JSON object")
    if (
        operation == "verify"
        and request_value.get("operation") != "verify_runtime_evidence"
    ):
        raise ValueError("verify capture accepts only verify_runtime_evidence requests")

    skills_root = _without_symlinks(cwd / ".agents" / "skills")
    script = _expected_script(skills_root=skills_root, skill=skill, operation=operation)
    started = time.monotonic()
    timed_out = False
    try:
        execution = subprocess.run(
            [sys.executable, str(script)],
            input=request_bytes,
            cwd=script.parent.parent,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=90,
            check=False,
            shell=False,
        )
        exit_code = execution.returncode
        stdout_bytes = execution.stdout
        stderr_bytes = execution.stderr
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        exit_code = 124
        stdout_bytes = exc.stdout or b""
        stderr_bytes = exc.stderr or b""

    raw_result = stdout_bytes
    raw_stderr = stderr_bytes.decode("utf-8", errors="replace")
    safe_request = _SECRET_RE.sub("[redacted]", request_text)
    raw_result_text = raw_result.decode("utf-8", errors="replace")
    safe_result = _SECRET_RE.sub("[redacted]", raw_result_text)
    safe_stderr = _sanitize(raw_stderr, 64_000)
    valid_shape = False
    try:
        parsed_result = json.loads(safe_result)
        if operation == "verify":
            valid_shape = isinstance(parsed_result, dict) and isinstance(
                parsed_result.get("valid"), bool
            )
        else:
            valid_shape = isinstance(parsed_result, dict) and isinstance(
                parsed_result.get("payload"), dict
            )
    except json.JSONDecodeError:
        pass
    captured = (
        not timed_out
        and exit_code == 0
        and valid_shape
        and safe_request.encode("utf-8") == request_bytes
        and safe_result == raw_result_text
    )
    _atomic_write(record / "result.json", safe_result.encode("utf-8"))
    if safe_stderr:
        _atomic_write(record / "stderr.txt", safe_stderr.encode("utf-8"))
    invocation = {
        "schema_version": 1,
        "skill": skill,
        "operation": operation,
        "artifact_id": record_parts[1],
        "invocation_id": record_parts[2],
        "request_relative_path": Path(relative_request).as_posix(),
        "record_relative_path": (
            Path(".runtime-evidence") / relative_record
        ).as_posix(),
        "result_relative_path": (
            Path(".runtime-evidence") / relative_record / "result.json"
        ).as_posix(),
        "command": ["python", f".agents/skills/{skill}/scripts/{script.name}"],
        "exit_code": exit_code,
        "timed_out": timed_out,
        "duration_seconds": round(time.monotonic() - started, 3),
        "request_sha256": _digest(request_bytes),
        "result_sha256": _digest(raw_result),
        "stderr_status": "sanitized"
        if safe_stderr != raw_stderr
        else "captured"
        if safe_stderr
        else "empty",
        "stderr": safe_stderr,
        "evidence_status": "captured" if captured else "evidence_unverified",
    }
    serialized = json.dumps(invocation, ensure_ascii=False, indent=2) + "\n"
    _atomic_write(record / "invocation.json", serialized.encode("utf-8"))
    return invocation


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Capture a fixed Skill runtime verifier invocation."
    )
    parser.add_argument("--skill", choices=sorted(RUNTIME_SKILLS), required=True)
    parser.add_argument(
        "--operation", choices=("verify", "workflow-runtime"), required=True
    )
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--record", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        invocation = capture_invocation(
            skill=args.skill,
            operation=args.operation,
            request_path=args.request,
            record_path=args.record,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"runtime capture failed: {type(exc).__name__}", file=sys.stderr)
        return 2
    print(
        json.dumps(
            {"evidence_status": invocation["evidence_status"]}, ensure_ascii=True
        )
    )
    return 0 if invocation["evidence_status"] == "captured" else 2


if __name__ == "__main__":
    raise SystemExit(main())
