from __future__ import annotations

import os
import signal
import subprocess
import tempfile
import time
from contextlib import nullcontext
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Mapping, Sequence

from .common import MAX_TEXT_BYTES, bounded_text, sanitize_diagnostic


@dataclass(frozen=True)
class ExecutionResult:
    exit_code: int
    stdout: str
    stderr: str | None
    stderr_status: str
    timed_out: bool
    duration_seconds: float
    cleanup_status: str = "not_needed"

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


class AgentExecutionError(RuntimeError):
    pass


def _kill_process_tree(process: subprocess.Popen[bytes], grace_seconds: float) -> None:
    if process.poll() is not None:
        return
    if os.name == "nt":
        try:
            subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
                timeout=max(2.0, grace_seconds),
            )
        except (OSError, subprocess.TimeoutExpired):
            # Fall through to a direct process kill when taskkill stalls or is unavailable.
            pass
    else:
        try:
            os.killpg(process.pid, signal.SIGTERM)
            process.wait(timeout=grace_seconds)
        except (ProcessLookupError, subprocess.TimeoutExpired):
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
    try:
        process.wait(timeout=max(2.0, grace_seconds))
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()


def run_command(
    argv: Sequence[str],
    *,
    input_text: str,
    cwd: Path,
    timeout_seconds: int,
    env: Mapping[str, str] | None = None,
    inherit_environment: bool = True,
    output_limit_bytes: int = MAX_TEXT_BYTES,
    stderr_limit_bytes: int = 64_000,
    timeout_cleanup_argv: Sequence[str] | None = None,
) -> ExecutionResult:
    if not argv or any(not isinstance(item, str) or not item for item in argv):
        raise AgentExecutionError("command argv must contain non-empty strings")
    if (
        isinstance(timeout_seconds, bool)
        or not isinstance(timeout_seconds, int)
        or timeout_seconds <= 0
    ):
        raise AgentExecutionError("timeout_seconds must be a positive integer")
    cwd = cwd.resolve()
    if not cwd.is_dir():
        raise AgentExecutionError("working directory does not exist")
    temp_context = (
        tempfile.TemporaryDirectory(prefix="qa-agent-eval-")
        if os.name == "nt"
        else nullcontext(None)
    )
    with temp_context as execution_temp:
        launch_env = os.environ.copy() if inherit_environment else {}
        launch_env["PYTHONIOENCODING"] = "utf-8"
        if env is not None:
            launch_env.update(env)
        if execution_temp is not None:
            for name in ("TMPDIR", "TEMP", "TMP"):
                launch_env[name] = execution_temp
        flags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
        started = time.monotonic()
        try:
            process = subprocess.Popen(
                list(argv),
                cwd=cwd,
                env=launch_env,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=False,
                close_fds=True,
                start_new_session=os.name != "nt",
                creationflags=flags,
            )
        except OSError as exc:
            raise AgentExecutionError(
                f"could not start external command: {type(exc).__name__}"
            ) from exc

        timed_out = False
        cleanup_status = "not_needed"
        try:
            stdout_bytes, stderr_bytes = process.communicate(
                input=input_text.encode("utf-8"), timeout=timeout_seconds
            )
        except subprocess.TimeoutExpired:
            timed_out = True
            _kill_process_tree(process, grace_seconds=1.0)
            stdout_bytes, stderr_bytes = process.communicate()
            if timeout_cleanup_argv:
                try:
                    cleanup = subprocess.run(
                        list(timeout_cleanup_argv),
                        stdin=subprocess.DEVNULL,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        timeout=15,
                        check=False,
                        shell=False,
                        close_fds=True,
                    )
                    cleanup_status = (
                        "succeeded" if cleanup.returncode == 0 else "failed"
                    )
                except (OSError, subprocess.TimeoutExpired):
                    cleanup_status = "failed"

        duration = round(time.monotonic() - started, 3)
        stdout_text = stdout_bytes.decode("utf-8", errors="strict")
        stderr_text = stderr_bytes.decode("utf-8", errors="replace")
        stderr_safe = sanitize_diagnostic(stderr_text, stderr_limit_bytes)
        if len(stderr_text.encode("utf-8", errors="replace")) > stderr_limit_bytes:
            stderr_status = "redacted_or_truncated"
        elif stderr_safe != stderr_text:
            stderr_status = "sanitized"
        elif stderr_text:
            stderr_status = "saved_sanitized"
        else:
            stderr_safe = None
            stderr_status = "empty"
        return ExecutionResult(
            exit_code=process.returncode if process.returncode is not None else 2,
            stdout=bounded_text(stdout_text, output_limit_bytes),
            stderr=stderr_safe,
            stderr_status=stderr_status,
            timed_out=timed_out,
            duration_seconds=duration,
            cleanup_status=cleanup_status,
        )
