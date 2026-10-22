from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
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


def capture_codex_jsonl_trace(
    stdout: str, *, skill_names: list[str] | tuple[str, ...] = ()
) -> dict[str, Any]:
    """Extract a final message and auditable command observations from codex exec --json."""
    original_lines = [line for line in stdout.splitlines() if line.strip()]
    try:
        events = [json.loads(line) for line in original_lines]
    except json.JSONDecodeError:
        events = []
    event_types = {
        "thread.started",
        "turn.started",
        "turn.completed",
        "turn.failed",
        "item.started",
        "item.completed",
        "item.updated",
        "error",
    }
    if not events or any(
        not isinstance(event, dict) or event.get("type") not in event_types
        for event in events
    ):
        return {
            "format": "plain_text_or_unrecognized",
            "status": "unavailable",
            "final_message": stdout,
            "trace_jsonl": None,
            "redacted": False,
            "commands": [],
            "skill_use_observation": {name: "unverified" for name in skill_names},
        }

    safe_trace = sanitize_diagnostic(stdout, MAX_TEXT_BYTES)
    try:
        safe_events = [
            json.loads(line) for line in safe_trace.splitlines() if line.strip()
        ]
    except json.JSONDecodeError:
        safe_events = []
    if len(safe_events) != len(events):
        safe_events = []

    messages: list[str] = []
    commands: list[dict[str, Any]] = []
    observed = {name: False for name in skill_names}
    for event in safe_events:
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
                "event_id": item.get("id"),
                "command": command,
                "exit_code": exit_code,
                "completed": True,
                "successful": exit_code == 0,
            }
        )
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

    return {
        "format": "codex_exec_jsonl",
        "status": "captured" if safe_events else "evidence_unverified",
        "final_message": messages[-1] if messages else "",
        "trace_jsonl": safe_trace if safe_events else None,
        "redacted": safe_trace != stdout,
        "commands": commands,
        "skill_use_observation": {
            name: "observed" if was_observed else "unverified"
            for name, was_observed in observed.items()
        },
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
