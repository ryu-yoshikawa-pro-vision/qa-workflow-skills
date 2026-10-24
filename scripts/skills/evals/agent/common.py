from __future__ import annotations

import hashlib
import json
import os
import re
import shlex
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any

MAX_TEXT_BYTES = 2_000_000
_SECRET_PATTERNS = (
    re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]{12,}"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{16,}"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}"),
    re.compile(
        r"(?i)(api[_-]?key|access[_-]?token|refresh[_-]?token|password)\s*[:=]\s*[^\s,;]+"
    ),
)
_CODEX_JSONL_EVENT_TYPES = {
    "thread.started",
    "turn.started",
    "turn.completed",
    "turn.failed",
    "item.started",
    "item.updated",
    "item.completed",
    "error",
}


class AgentEvalError(RuntimeError):
    """Raised when an evaluation input or saved record is unsafe or invalid."""


def visible_skill_names(cases: list[dict[str, Any]]) -> list[str]:
    """Return the exact Skill packages routed by the selected fixed cases."""
    return sorted({case["skill"] for case in cases})


def sha256_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return "sha256:" + digest.hexdigest()


def canonical_fingerprint(value: Any) -> str:
    rendered = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return sha256_bytes(rendered)


def atomic_write_bytes(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def atomic_write_text(path: Path, content: str) -> None:
    atomic_write_bytes(path, content.encode("utf-8"))


def atomic_write_json(path: Path, value: Any) -> None:
    atomic_write_text(
        path, json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    )


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AgentEvalError(
            f"invalid JSON file: {path.name}: {type(exc).__name__}"
        ) from exc


def bounded_text(value: str, limit: int = MAX_TEXT_BYTES) -> str:
    encoded = value.encode("utf-8", errors="replace")
    if len(encoded) <= limit:
        return value
    return encoded[:limit].decode("utf-8", errors="ignore") + "\n[truncated]"


def sanitize_diagnostic(value: str, limit: int = 64_000) -> str:
    sanitized = value
    for pattern in _SECRET_PATTERNS:
        sanitized = pattern.sub("[redacted]", sanitized)
    return bounded_text(sanitized, limit)


def capture_codex_judge_output(
    stdout: str, *, observations_path: Path | None = None
) -> dict[str, Any]:
    """Keep final Judge JSON on stdout and read safe provenance from its sidecar."""
    envelope = None
    if observations_path is not None:
        try:
            if observations_path.is_symlink():
                raise OSError("symlink observations")
            observations = json.loads(observations_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            observations = None
        response = stdout
        if not isinstance(observations, dict):
            return {
                "response": sanitize_diagnostic(stdout, MAX_TEXT_BYTES),
                "launcher_observations": {"status": "unverified"},
                "redacted": False,
                "status": "unverified",
            }
    else:
        try:
            envelope = json.loads(stdout)
        except json.JSONDecodeError:
            envelope = None
        if not (
            isinstance(envelope, dict)
            and envelope.get("protocol") == "codex_judge_docker_launcher_v1"
        ):
            return {
                "response": stdout,
                "launcher_observations": None,
                "redacted": False,
                "status": "unwrapped",
            }
        observations = envelope.get("observations")
        response = envelope.get("response")
        if not isinstance(observations, dict) or not isinstance(response, str):
            return {
                "response": "",
                "launcher_observations": {"status": "unverified"},
                "redacted": False,
                "status": "unverified",
            }
    safe_response = sanitize_diagnostic(response, MAX_TEXT_BYTES)
    wsl2_launcher = observations.get("protocol") == "codex_wsl2_bwrap_launcher_v1"
    image = observations.get("image")
    safe_image = None
    if isinstance(image, dict):
        safe_image = {
            key: value
            for key, value in image.items()
            if key in {"image_id", "codex_cli_version", "python_version", "ca_bundle"}
            and isinstance(value, str)
        }
    runtime = observations.get("runtime")
    safe_runtime = None
    if wsl2_launcher and isinstance(runtime, dict):
        safe_runtime = {
            key: value
            for key, value in runtime.items()
            if key
            in {
                "package_version",
                "package_sha512",
                "codex_sha256",
                "codex_version",
                "bwrap_sha256",
                "bwrap_version",
                "kernel",
                "machine",
                "python_version",
            }
            and isinstance(value, (str, int, float))
        }
    jsonl = observations.get("jsonl")
    safe_jsonl = None
    if isinstance(jsonl, dict):
        tool_event_count = jsonl.get("tool_event_count", 0)
        command_count = jsonl.get("command_count", 0)
        tool_event_count = (
            tool_event_count
            if isinstance(tool_event_count, int)
            and not isinstance(tool_event_count, bool)
            else 0
        )
        command_count = (
            command_count
            if isinstance(command_count, int) and not isinstance(command_count, bool)
            else 0
        )
        safe_jsonl = {
            "status": jsonl.get("status", "unverified"),
            "event_count": jsonl.get("event_count", 0),
            "event_types": jsonl.get("event_types", {}),
            "item_types": jsonl.get("item_types", {}),
            "tool_use_detected": jsonl.get("tool_use_detected") is True
            or tool_event_count > 0
            or command_count > 0,
            "turn_completed": jsonl.get("turn_completed") is True,
            "turn_failed": jsonl.get("turn_failed") is True,
        }
    launcher_status = observations.get(
        "status",
        envelope.get("status", "unverified")
        if isinstance(envelope, dict)
        else "unverified",
    )
    response_redacted = observations.get("response_redacted") is True or (
        safe_response != response
    )
    if (
        wsl2_launcher
        and launcher_status == "completed"
        and (
            not safe_response
            or safe_jsonl is None
            or safe_jsonl["status"] != "captured"
            or safe_jsonl["tool_use_detected"]
            or observations.get("mode") != "judge"
            or observations.get("web_search_enabled") is not False
            or observations.get("tool_policy") != "no_cli_tools_or_mcp_configured"
            or observations.get("auth_mode")
            not in {"temporary_auth_file", "api_key_environment"}
            or not isinstance(safe_runtime, dict)
            or safe_runtime.get("package_version") != "0.163.0-linux-x64"
            or observations.get("outer_exit_code") != 0
            or response_redacted
        )
    ):
        launcher_status = "evidence_unverified"
    elif (
        not wsl2_launcher
        and launcher_status == "completed"
        and (
            not safe_response
            or safe_jsonl is None
            or safe_jsonl["status"] != "captured"
            or safe_jsonl["tool_use_detected"]
            or observations.get("web_search_enabled") is not False
            or observations.get("tool_policy") != "no_cli_tools_or_mcp_configured"
            or observations.get("auth_mode")
            not in {"temporary_auth_file", "api_key_environment"}
            or safe_image is None
            or observations.get("docker_exit_code") != 0
            or response_redacted
        )
    ):
        launcher_status = "evidence_unverified"
    launcher_observations = {
        "protocol": observations.get("protocol"),
        "status": launcher_status,
        "auth_mode": observations.get("auth_mode", "unverified"),
        "image": safe_image,
        "runtime": safe_runtime,
        "jsonl": safe_jsonl,
        "docker_exit_code": observations.get(
            "outer_exit_code", observations.get("docker_exit_code")
        ),
        "model": observations.get("model"),
        "reasoning_effort": observations.get("reasoning_effort"),
        "sandbox_policy": observations.get("sandbox_policy"),
        "approval_policy": observations.get("approval_policy"),
        "web_search_enabled": observations.get("web_search_enabled")
        if isinstance(observations.get("web_search_enabled"), bool)
        else None,
        "tool_policy": observations.get("tool_policy", "unverified"),
        "response_redacted": response_redacted,
    }
    return {
        "response": safe_response,
        "launcher_observations": launcher_observations,
        "redacted": launcher_observations["response_redacted"],
        "status": launcher_observations["status"],
    }


def capture_codex_jsonl_trace(
    stdout: str, *, skill_names: list[str] | tuple[str, ...] = ()
) -> dict[str, Any]:
    """Extract bounded evidence without retaining Codex's raw JSONL event stream."""
    try:
        launcher = json.loads(stdout)
    except json.JSONDecodeError:
        launcher = None
    if isinstance(launcher, dict) and launcher.get("protocol") in {
        "codex_docker_launcher_v1",
        "codex_wsl2_bwrap_launcher_v1",
    }:
        observations = launcher.get("observations")
        jsonl_summary = (
            observations.get("jsonl") if isinstance(observations, dict) else None
        )
        if (
            not isinstance(observations, dict)
            or not isinstance(jsonl_summary, dict)
            or not isinstance(launcher.get("final_message"), str)
        ):
            return _unavailable_trace(skill_names, str(launcher.get("protocol")))
        safe_commands: list[dict[str, Any]] = []
        for row in jsonl_summary.get("commands", []):
            if not isinstance(row, dict):
                continue
            exit_code = row.get("exit_code")
            if isinstance(exit_code, bool) or not isinstance(exit_code, int):
                exit_code = None
            captures = row.get("verifier_capture_invocations", [])
            safe_captures = (
                [
                    capture
                    for capture in captures
                    if isinstance(capture, dict)
                    and all(
                        isinstance(capture.get(key), str)
                        for key in (
                            "skill",
                            "operation",
                            "request_relative_path",
                            "record_relative_path",
                        )
                    )
                ]
                if isinstance(captures, list)
                else []
            )
            observed_skills = row.get("skill_files_read", [])
            if not isinstance(observed_skills, list):
                observed_skills = []
            safe_commands.append(
                {
                    "exit_code": exit_code,
                    "successful": row.get("successful") is True and exit_code == 0,
                    "skill_files_read": [
                        name for name in observed_skills if isinstance(name, str)
                    ],
                    "verifier_capture_invocations": safe_captures,
                }
            )
        final_message = launcher["final_message"]
        safe_message = sanitize_diagnostic(final_message, MAX_TEXT_BYTES)
        trace_summary = {
            "format": "codex_exec_jsonl",
            "status": jsonl_summary.get("status", "unverified"),
            "event_count": jsonl_summary.get("event_count", 0),
            "event_types": jsonl_summary.get("event_types", {}),
            "command_count": jsonl_summary.get("command_count", len(safe_commands)),
            "commands": safe_commands,
            "turn_completed": jsonl_summary.get("turn_completed") is True,
            "turn_failed": jsonl_summary.get("turn_failed") is True,
        }
        observed = {
            name: any(
                row["successful"] and name in row["skill_files_read"]
                for row in safe_commands
            )
            for name in skill_names
        }
        image = observations.get("image")
        safe_image = None
        if isinstance(image, dict):
            safe_image = {
                key: value
                for key, value in image.items()
                if key
                in {"image_id", "codex_cli_version", "python_version", "ca_bundle"}
                and isinstance(value, str)
            }
        runtime = observations.get("runtime")
        safe_runtime = None
        if isinstance(runtime, dict):
            safe_runtime = {
                key: value
                for key, value in runtime.items()
                if key
                in {
                    "package_version",
                    "package_sha512",
                    "codex_sha256",
                    "codex_version",
                    "bwrap_sha256",
                    "bwrap_version",
                }
                and isinstance(value, str)
            }
        protocol = str(launcher.get("protocol"))
        return {
            "format": protocol,
            "status": jsonl_summary.get("status", "unverified"),
            "execution_status": observations.get("status", "unverified"),
            "final_message": safe_message,
            "trace_jsonl": None,
            "trace_summary": trace_summary,
            "launcher_observations": {
                "status": observations.get("status", "unverified"),
                "auth_mode": observations.get("auth_mode", "unverified"),
                "docker_exit_code": launcher.get(
                    "exit_code", observations.get("outer_exit_code")
                ),
                "image": safe_image,
                "runtime": safe_runtime,
            },
            "redacted": (
                safe_message != final_message
                or observations.get("final_message_redacted") is True
            ),
            "commands": safe_commands,
            "skill_use_observation": {
                name: "observed" if was_observed else "unverified"
                for name, was_observed in observed.items()
            },
        }

    original_lines = [line for line in stdout.splitlines() if line.strip()]
    try:
        events = [json.loads(line) for line in original_lines]
    except json.JSONDecodeError:
        events = []
    if not events or any(
        not isinstance(event, dict) or not isinstance(event.get("type"), str)
        for event in events
    ):
        first_line = original_lines[0] if original_lines else ""
        try:
            first_event = json.loads(first_line)
        except json.JSONDecodeError:
            first_event = None
        jsonl_like = isinstance(first_event, dict) and isinstance(
            first_event.get("type"), str
        )
        if jsonl_like:
            return _unavailable_trace(skill_names, "unrecognized_jsonl")
        safe_message = sanitize_diagnostic(stdout, MAX_TEXT_BYTES)
        return {
            "format": "plain_text",
            "status": "unavailable",
            "final_message": safe_message,
            "trace_jsonl": None,
            "trace_summary": {
                "format": "codex_exec_jsonl",
                "status": "unavailable",
                "event_count": 0,
                "event_types": {},
                "command_count": 0,
                "commands": [],
            },
            "redacted": safe_message != stdout,
            "commands": [],
            "skill_use_observation": {name: "unverified" for name in skill_names},
        }
    if any(event["type"] not in _CODEX_JSONL_EVENT_TYPES for event in events):
        return _unavailable_trace(skill_names, "unrecognized_jsonl")

    event_types = Counter(
        event["type"] for event in events if isinstance(event.get("type"), str)
    )
    messages: list[str] = []
    commands: list[dict[str, Any]] = []
    observed = {name: False for name in skill_names}
    safe_commands: list[dict[str, Any]] = []
    for event in events:
        if event.get("type") != "item.completed":
            continue
        item = event.get("item")
        if not isinstance(item, dict):
            continue
        if item.get("type") == "agent_message" and isinstance(item.get("text"), str):
            messages.append(item["text"])
        if item.get("type") != "command_execution" or not isinstance(
            item.get("command"), str
        ):
            continue
        raw_exit = item.get("exit_code", item.get("exitCode"))
        exit_code = (
            raw_exit
            if isinstance(raw_exit, int) and not isinstance(raw_exit, bool)
            else None
        )
        command = item["command"]
        commands.append(
            {
                "command": command,
                "exit_code": exit_code,
                "completed": True,
                "successful": exit_code == 0,
            }
        )
        observed_skills: list[str] = []
        if exit_code == 0:
            normalized = command.replace("\\", "/").lower()
            reader = re.search(
                r"(?:^|[\s;&|])(?:cat|head|tail|sed|awk|rg|grep|less|more)(?:\s|$)",
                normalized,
            )
            if reader:
                for name in observed:
                    target = f".agents/skills/{name}/skill.md"
                    if target in normalized:
                        observed[name] = True
                        observed_skills.append(name)
        safe_captures: list[dict[str, Any]] = []
        if exit_code == 0:
            invocation = _safe_capture_invocation(command)
            if invocation is not None:
                safe_captures.append(invocation)
        safe_commands.append(
            {
                "exit_code": exit_code,
                "successful": exit_code == 0,
                "skill_files_read": observed_skills,
                "verifier_capture_invocations": safe_captures,
            }
        )

    safe_messages = [
        sanitize_diagnostic(message, MAX_TEXT_BYTES) for message in messages
    ]
    final_message = safe_messages[-1] if safe_messages else ""
    turn_completed = event_types.get("turn.completed", 0) > 0
    turn_failed = event_types.get("turn.failed", 0) > 0
    event_error = event_types.get("error", 0) > 0
    trace_status = (
        "captured"
        if messages and turn_completed and not turn_failed and not event_error
        else "evidence_unverified"
    )
    trace_summary = {
        "format": "codex_exec_jsonl",
        "status": trace_status,
        "event_count": len(events),
        "event_types": dict(sorted(event_types.items())),
        "command_count": len(commands),
        "commands": safe_commands,
        "turn_completed": event_types.get("turn.completed", 0) > 0,
        "turn_failed": event_types.get("turn.failed", 0) > 0,
    }
    return {
        "format": "codex_exec_jsonl",
        "status": trace_status,
        "final_message": final_message,
        "trace_jsonl": None,
        "trace_summary": trace_summary,
        "redacted": bool(messages and final_message != messages[-1]),
        "commands": commands,
        "skill_use_observation": {
            name: "observed" if was_observed else "unverified"
            for name, was_observed in observed.items()
        },
    }


def _unavailable_trace(
    skill_names: list[str] | tuple[str, ...], trace_format: str
) -> dict[str, Any]:
    return {
        "format": trace_format,
        "status": "unverified",
        "final_message": "",
        "trace_jsonl": None,
        "trace_summary": {
            "format": "codex_exec_jsonl",
            "status": "unverified",
            "event_count": 0,
            "event_types": {},
            "command_count": 0,
            "commands": [],
        },
        "redacted": False,
        "commands": [],
        "skill_use_observation": {name: "unverified" for name in skill_names},
    }


def _safe_capture_invocation(command: str) -> dict[str, str] | None:
    try:
        tokens = shlex.split(command, posix=True)
    except ValueError:
        return None
    script_seen = any(
        token.replace("\\", "/").endswith(".qa-eval-tools/verifier_capture.py")
        for token in tokens
    )
    if not script_seen:
        return None
    values: dict[str, str] = {}
    for option in ("--skill", "--operation", "--request", "--record"):
        for index, token in enumerate(tokens):
            if token == option and index + 1 < len(tokens):
                values[option] = tokens[index + 1]
                break
            if token.startswith(option + "="):
                values[option] = token.split("=", 1)[1]
                break

    def relative(path: str) -> str | None:
        normalized = path.replace("\\", "/")
        prefixes = ("/workspace/.qa-eval-output/", ".qa-eval-output/")
        for prefix in prefixes:
            if normalized.startswith(prefix):
                normalized = normalized[len(prefix) :]
                break
        else:
            return None
        candidate = Path(normalized)
        if candidate.is_absolute() or ".." in candidate.parts or not candidate.parts:
            return None
        if candidate.parts[0] != ".runtime-evidence":
            return None
        return candidate.as_posix()

    skill = values.get("--skill", "")
    operation = values.get("--operation", "")
    request_path = relative(values.get("--request", ""))
    record_path = relative(values.get("--record", ""))
    if (
        not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", skill)
        or operation not in {"verify", "generate", "workflow"}
        or request_path is None
        or record_path is None
    ):
        return None
    return {
        "skill": skill,
        "operation": operation,
        "request_relative_path": request_path,
        "record_relative_path": record_path,
    }


def trace_confirms_capture_invocation(
    commands: list[dict[str, Any]], invocation: dict[str, Any]
) -> bool:
    """Match a successful structured command event to a saved runtime invocation."""
    skill = invocation.get("skill")
    operation = invocation.get("operation")
    request_path = invocation.get("request_relative_path")
    record_path = invocation.get("record_relative_path")
    if not all(
        isinstance(item, str) and item
        for item in (skill, operation, request_path, record_path)
    ):
        return False

    def option_matches(command: str, option: str, value: str) -> bool:
        value_pattern = re.escape(value)
        allow_path_prefix = option in {"--request", "--record"}
        prefix = r"(?:[^\s\"']*/)?" if allow_path_prefix else ""
        return bool(
            re.search(
                rf"(?:^|\s){re.escape(option)}(?:=|\s+)[\"']?{prefix}{value_pattern}(?:[\"']?(?:\s|$))",
                command.replace("\\", "/"),
            )
        )

    for row in commands:
        safe_invocations = row.get("verifier_capture_invocations")
        if row.get("successful") is True and isinstance(safe_invocations, list):
            for captured in safe_invocations:
                if not isinstance(captured, dict):
                    continue
                if all(
                    captured.get(key) == expected
                    for key, expected in (
                        ("skill", skill),
                        ("operation", operation),
                        ("request_relative_path", request_path),
                        ("record_relative_path", record_path),
                    )
                ):
                    return True
        command = row.get("command")
        if row.get("successful") is not True or not isinstance(command, str):
            continue
        normalized = command.replace("\\", "/")
        if (
            ".qa-eval-tools/verifier_capture.py" in normalized
            and option_matches(normalized, "--skill", skill)
            and option_matches(normalized, "--operation", operation)
            and option_matches(normalized, "--request", request_path)
            and option_matches(normalized, "--record", record_path)
        ):
            return True
    return False


def safe_relative_path(value: str) -> Path:
    path = Path(value)
    if (
        path.is_absolute()
        or not path.parts
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        raise AgentEvalError("path must be a normalized relative path")
    return path


def ensure_within(path: Path, root: Path) -> Path:
    resolved_root = root.resolve()
    resolved = path.resolve(strict=False)
    try:
        resolved.relative_to(resolved_root)
    except ValueError as exc:
        raise AgentEvalError("path escapes its allowed root") from exc
    return resolved


def prepare_run_output_root(
    output_root: Path,
    *,
    repository_root: Path,
    evidence_relative_path: str | None,
) -> Path:
    """Create a fresh ignored run directory, allowing only its isolation evidence."""
    if evidence_relative_path is None:
        raise AgentEvalError("verified isolation evidence path is required")
    evidence_relative = safe_relative_path(evidence_relative_path)
    repository = Path(os.path.abspath(repository_root))
    root = Path(os.path.abspath(output_root))
    try:
        relative = root.relative_to(repository)
    except ValueError as exc:
        raise AgentEvalError(
            "evaluation output must remain under the Evaluator repository"
        ) from exc
    if len(relative.parts) < 2 or relative.parts[0] != ".agent-eval-runs":
        raise AgentEvalError("evaluation output must be under .agent-eval-runs/")

    current = repository
    for part in relative.parts:
        current /= part
        if current.is_symlink():
            raise AgentEvalError("evaluation output path may not contain symlinks")
    if root.exists() and not root.is_dir():
        raise AgentEvalError("evaluation output root must be a directory")
    root.mkdir(parents=True, exist_ok=True)
    evidence_path = root / evidence_relative
    for path in root.rglob("*"):
        if path.is_symlink():
            raise AgentEvalError("evaluation output root may not contain symlinks")
        if path.is_dir():
            if evidence_path == path or evidence_path.is_relative_to(path):
                continue
            raise AgentEvalError(
                "evaluation output root must be empty except for isolation evidence"
            )
        if path != evidence_path:
            raise AgentEvalError(
                "evaluation output root must be empty except for isolation evidence"
            )
    return evidence_path
