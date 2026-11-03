"""Run fixed runtime scripts behind a probed, unprivileged bubblewrap boundary."""

from __future__ import annotations

import ctypes
import fcntl
import hashlib
import json
import os
import re
import resource
import shutil
import signal
import socket
import stat
import struct
import subprocess
import sys
import tempfile
import time
from pathlib import Path, PurePosixPath
from typing import Any

from .common import (
    AgentEvalError,
    canonical_fingerprint,
    read_regular_file_bytes,
    sanitize_diagnostic,
)

MAX_SOURCE_BYTES = 40_000_000
MAX_SOURCE_ENTRIES = 256
MAX_SOURCE_DEPTH = 16
MAX_REQUEST_BYTES = 16_000_000
MAX_OUTPUT_BYTES = 16_000_000
TMPFS_BYTES = 16_777_216
_F_ADD_SEALS = 1033
_F_SEAL_SEAL = 0x0001
_F_SEAL_SHRINK = 0x0002
_F_SEAL_GROW = 0x0004
_F_SEAL_WRITE = 0x0008
_SECRET_RE = re.compile(
    r"(?i)\b(?:Bearer\s+[A-Za-z0-9._~+/=-]{12,}|sk-[A-Za-z0-9_-]{16,}|gh[pousr]_[A-Za-z0-9]{20,}|(?:api[_-]?key|access[_-]?token|refresh[_-]?token|password)\s*[:=]\s*[^\s,;]+)"
)
_REQUIRED_BWRAP_OPTIONS = (
    "--unshare-user",
    "--unshare-pid",
    "--unshare-ipc",
    "--unshare-uts",
    "--disable-userns",
    "--assert-userns-disabled",
    "--die-with-parent",
    "--cap-drop",
    "--ro-bind",
    "--ro-bind-data",
    "--dir",
    "--remount-ro",
    "--size",
    "--tmpfs",
    "--proc",
    "--dev",
    "--clearenv",
    "--setenv",
    "--chdir",
    "--new-session",
    "--seccomp",
)
_AUDIT_ARCH_X86_64 = 0xC000003E
_SECCOMP_RET_KILL_PROCESS = 0x80000000
_SECCOMP_RET_ERRNO = 0x00050000
_SECCOMP_RET_ALLOW = 0x7FFF0000
_X32_SYSCALL_BIT = 0x40000000
_SECCOMP_BLOCKED_X86_64_SYSCALLS = (
    41,  # socket
    42,  # connect
    43,  # accept
    44,  # sendto
    45,  # recvfrom
    46,  # sendmsg
    47,  # recvmsg
    48,  # shutdown
    49,  # bind
    50,  # listen
    51,  # getsockname
    52,  # getpeername
    53,  # socketpair
    54,  # setsockopt
    55,  # getsockopt
    288,  # accept4
    299,  # recvmmsg
    307,  # sendmmsg
    425,  # io_uring_setup
    426,  # io_uring_enter
    427,  # io_uring_register
)


def _sha256(raw: bytes) -> str:
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _network_seccomp_filter_bytes() -> bytes:
    """Build an x86_64 seccomp filter that denies socket and io_uring syscalls."""
    if not sys.platform.startswith("linux") or os.uname().machine not in {
        "x86_64",
        "amd64",
    }:
        raise AgentEvalError("network seccomp policy is unavailable for this runtime")
    instructions = [
        (0x20, 0, 0, 4),  # load seccomp_data.arch
        (0x15, 1, 0, _AUDIT_ARCH_X86_64),  # continue only on x86_64
        (0x06, 0, 0, _SECCOMP_RET_KILL_PROCESS),
        (0x20, 0, 0, 0),  # load seccomp_data.nr
        # Reject the x32 syscall ABI as well; it shares AUDIT_ARCH_X86_64.
        (0x45, 0, 1, _X32_SYSCALL_BIT),
        (0x06, 0, 0, _SECCOMP_RET_ERRNO | 1),
    ]
    for syscall_number in _SECCOMP_BLOCKED_X86_64_SYSCALLS:
        instructions.extend(
            (
                (0x15, 0, 1, syscall_number),
                (0x06, 0, 0, _SECCOMP_RET_ERRNO | 1),  # EPERM
            )
        )
    instructions.append((0x06, 0, 0, _SECCOMP_RET_ALLOW))
    return b"".join(struct.pack("=HBBI", *instruction) for instruction in instructions)


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate verifier JSON key")
        result[key] = value
    return result


def _no_new_privs_and_limits() -> None:
    for key, requested in (
        (resource.RLIMIT_CPU, 60),
        (resource.RLIMIT_AS, 2_000_000_000),
        (resource.RLIMIT_FSIZE, MAX_OUTPUT_BYTES),
        (resource.RLIMIT_NOFILE, 64),
        (resource.RLIMIT_NPROC, 128),
        (resource.RLIMIT_CORE, 0),
    ):
        _, hard = resource.getrlimit(key)
        limit = requested if hard == resource.RLIM_INFINITY else min(requested, hard)
        resource.setrlimit(key, (limit, limit))
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(38, 1, 0, 0, 0) != 0:  # PR_SET_NO_NEW_PRIVS
        os._exit(126)


def _safe_tree(root: Path) -> list[dict[str, Any]]:
    root = Path(os.path.abspath(root))
    if root.is_symlink() or not root.is_dir():
        raise AgentEvalError("verifier source directory is not a regular directory")
    current = Path(root.anchor)
    for component in root.parts[1:]:
        current /= component
        if stat.S_ISLNK(current.lstat().st_mode):
            raise AgentEvalError("verifier source path contains a symlink")
    rows: list[dict[str, Any]] = []
    total = 0
    entry_count = 0
    for current, directories, filenames in os.walk(root, followlinks=False):
        current_path = Path(current)
        if len(current_path.relative_to(root).parts) > MAX_SOURCE_DEPTH:
            raise AgentEvalError("verifier source tree exceeds the depth limit")
        for name in directories:
            child = current_path / name
            if child.is_symlink() or not stat.S_ISDIR(child.lstat().st_mode):
                raise AgentEvalError("verifier source contains an unsafe directory")
            entry_count += 1
            if entry_count > MAX_SOURCE_ENTRIES:
                raise AgentEvalError("verifier source tree exceeds the entry limit")
            if len(child.relative_to(root).parts) > MAX_SOURCE_DEPTH:
                raise AgentEvalError("verifier source tree exceeds the depth limit")
        for name in filenames:
            child = current_path / name
            relative = child.relative_to(root).as_posix()
            entry_count += 1
            if entry_count > MAX_SOURCE_ENTRIES:
                raise AgentEvalError("verifier source tree exceeds the entry limit")
            info = child.lstat()
            if len(PurePosixPath(relative).parts) > MAX_SOURCE_DEPTH:
                raise AgentEvalError("verifier source tree exceeds the depth limit")
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                raise AgentEvalError("verifier source contains an unsafe file")
            if "__pycache__" in PurePosixPath(relative).parts or relative.endswith(
                ".pyc"
            ):
                raise AgentEvalError("verifier source contains Python bytecode")
            raw = read_regular_file_bytes(child, max_bytes=MAX_SOURCE_BYTES)
            total += len(raw)
            if total > MAX_SOURCE_BYTES:
                raise AgentEvalError("verifier source exceeds the size limit")
            rows.append({"path": relative, "size": len(raw), "sha256": _sha256(raw)})
        if entry_count > MAX_SOURCE_ENTRIES:
            raise AgentEvalError("verifier source tree exceeds the entry limit")
    return sorted(rows, key=lambda row: row["path"])


def source_tree_fingerprint(root: Path) -> str:
    return canonical_fingerprint(_safe_tree(root))


def _trusted_root_owned_file(path: Path) -> bool:
    current = Path(path.anchor)
    parts = path.parts[1:]
    for index, part in enumerate(parts):
        current /= part
        try:
            info = current.lstat()
        except OSError:
            return False
        if stat.S_ISLNK(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o022:
            return False
        if index == len(parts) - 1:
            return stat.S_ISREG(info.st_mode)
        if not stat.S_ISDIR(info.st_mode):
            return False
    return False


def _sealed_script_fd(script_bytes: bytes) -> int:
    if not hasattr(os, "memfd_create"):
        raise AgentEvalError("sealed in-memory script files are unavailable")
    descriptor = os.memfd_create(
        "pr17-runtime-verifier",
        os.MFD_CLOEXEC | getattr(os, "MFD_ALLOW_SEALING", 0x0002),
    )
    try:
        with os.fdopen(os.dup(descriptor), "wb") as stream:
            stream.write(script_bytes)
            stream.flush()
        seals = _F_SEAL_SEAL | _F_SEAL_SHRINK | _F_SEAL_GROW | _F_SEAL_WRITE
        fcntl.fcntl(descriptor, _F_ADD_SEALS, seals)
        os.lseek(descriptor, 0, os.SEEK_SET)
        return descriptor
    except Exception:
        os.close(descriptor)
        raise


def _host_tools() -> tuple[Path, Path, dict[str, Any]] | None:
    bwrap_name = shutil.which("bwrap")
    if not bwrap_name:
        return None
    bwrap = Path(bwrap_name).resolve(strict=True)
    if not _trusted_root_owned_file(bwrap):
        return None
    try:
        help_result = subprocess.run(
            [str(bwrap), "--help"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=5,
            check=False,
            shell=False,
        )
        version_result = subprocess.run(
            [str(bwrap), "--version"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=5,
            check=False,
            shell=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    help_text = (help_result.stdout + help_result.stderr).decode(
        "utf-8", errors="replace"
    )
    if (
        help_result.returncode != 0
        or version_result.returncode != 0
        or any(option not in help_text for option in _REQUIRED_BWRAP_OPTIONS)
    ):
        return None

    try:
        network_filter = _network_seccomp_filter_bytes()
    except AgentEvalError:
        return None

    usr = Path("/usr").resolve(strict=True)
    python_candidates = [Path(sys.executable).resolve(strict=True)]
    system_python = Path("/usr/bin/python3")
    if system_python.exists():
        python_candidates.append(system_python.resolve(strict=True))
    python = next(
        (candidate for candidate in python_candidates if candidate.is_relative_to(usr)),
        None,
    )
    if python is None:
        return None
    if not _trusted_root_owned_file(python):
        return None
    return (
        bwrap,
        python,
        {
            "bwrap_version": version_result.stdout.decode(
                "utf-8", errors="replace"
            ).strip(),
            "bwrap_sha256": _sha256(
                read_regular_file_bytes(bwrap, max_bytes=50_000_000)
            ),
            "network_enforcement": "seccomp-deny-socket-and-io-uring",
            "network_policy_sha256": _sha256(network_filter),
            "python_path": python.as_posix(),
            "python_sha256": _sha256(
                read_regular_file_bytes(python, max_bytes=50_000_000)
            ),
        },
    )


def _base_argv(
    *,
    bwrap: Path,
    python: Path,
    seccomp_fd: int,
    script_fds: list[tuple[int, str]],
    in_sandbox_source: str,
    script_name: str,
    inner_argv: list[str],
) -> list[str]:
    usr = Path("/usr").resolve(strict=True)
    python_in_sandbox = "/" + python.relative_to(usr).as_posix()
    command = [
        str(bwrap),
        "--die-with-parent",
        "--new-session",
        "--unshare-user",
        "--unshare-pid",
        "--unshare-ipc",
        "--unshare-uts",
        "--disable-userns",
        "--assert-userns-disabled",
        "--cap-drop",
        "ALL",
        "--seccomp",
        str(seccomp_fd),
        "--ro-bind",
        str(usr),
        "/usr",
        "--symlink",
        "usr/lib",
        "/lib",
        "--symlink",
        "usr/lib64",
        "/lib64",
        "--symlink",
        "usr/bin",
        "/bin",
        "--symlink",
        "usr/sbin",
        "/sbin",
        "--proc",
        "/proc",
        "--dev",
        "/dev",
        "--size",
        str(TMPFS_BYTES),
        "--tmpfs",
        "/tmp",
        "--size",
        str(TMPFS_BYTES),
        "--tmpfs",
        "/workspace",
        "--dir",
        in_sandbox_source,
        *[
            token
            for descriptor, relative in script_fds
            for token in (
                "--ro-bind-data",
                str(descriptor),
                (PurePosixPath(in_sandbox_source) / relative).as_posix(),
            )
        ],
        "--remount-ro",
        "/",
        "--remount-ro",
        "/proc",
        "--remount-ro",
        "/dev",
        "--chdir",
        "/workspace",
        "--clearenv",
        "--setenv",
        "HOME",
        "/tmp",
        "--setenv",
        "TMPDIR",
        "/tmp",
        "--setenv",
        "PATH",
        "/usr/bin:/bin",
        "--setenv",
        "PYTHONDONTWRITEBYTECODE",
        "1",
        "--setenv",
        "PYTHONNOUSERSITE",
        "1",
        "--setenv",
        "LC_ALL",
        "C",
        "--",
        python_in_sandbox,
        "-E",
        "-s",
        "-S",
        "-B",
        (PurePosixPath(in_sandbox_source) / script_name).as_posix(),
        *inner_argv,
    ]
    return command


def _run_bwrap(
    *,
    bwrap: Path,
    python: Path,
    source_dir: Path,
    in_sandbox_source: str,
    script_name: str,
    inner_argv: list[str],
    input_bytes: bytes,
    timeout_seconds: float,
    expected_source_fingerprint: str | None = None,
    post_exit_wait_seconds: float = 0.0,
) -> dict[str, Any]:
    try:
        source_before = _safe_tree(source_dir)
    except (AgentEvalError, OSError) as exc:
        return {
            "status": "evidence_unverified",
            "reason": "verifier_snapshot_invalid",
            "reason_type": type(exc).__name__,
            "sandbox_process_started": False,
            "verifier_executed": False,
        }
    source_fingerprint = canonical_fingerprint(source_before)
    if (
        expected_source_fingerprint is not None
        and source_fingerprint != expected_source_fingerprint
    ):
        return {
            "status": "evidence_unverified",
            "reason": "candidate_source_fingerprint_mismatch",
            "sandbox_process_started": False,
            "verifier_executed": False,
            "source_fingerprint_before": source_fingerprint,
        }
    if len(source_before) > 32:
        return {
            "status": "evidence_unverified",
            "reason": "candidate_source_file_count_exceeded",
            "sandbox_process_started": False,
            "verifier_executed": False,
            "source_fingerprint_before": source_fingerprint,
        }
    script_fds: list[tuple[int, str]] = []
    entrypoint_sha256: str | None = None
    try:
        for item in source_before:
            relative = item["path"]
            script_bytes = read_regular_file_bytes(
                source_dir / Path(*PurePosixPath(relative).parts),
                max_bytes=MAX_SOURCE_BYTES,
            )
            if _sha256(script_bytes) != item["sha256"]:
                raise AgentEvalError("verifier source changed while snapshotting")
            script_fds.append((_sealed_script_fd(script_bytes), relative))
            if relative == script_name:
                entrypoint_sha256 = item["sha256"]
        source_after_snapshot = canonical_fingerprint(_safe_tree(source_dir))
        if source_after_snapshot != source_fingerprint:
            raise AgentEvalError("verifier source changed while snapshotting")
        if script_name not in {relative for _, relative in script_fds}:
            raise AgentEvalError("verifier entrypoint is missing from the snapshot")
        if entrypoint_sha256 is None:
            raise AgentEvalError("verifier entrypoint identity is missing")
        if len(input_bytes) > MAX_REQUEST_BYTES:
            raise AgentEvalError("verifier request exceeds the size limit")
    except (AgentEvalError, OSError) as exc:
        for descriptor, _ in script_fds:
            os.close(descriptor)
        return {
            "status": "evidence_unverified",
            "reason": "verifier_snapshot_invalid",
            "reason_type": type(exc).__name__,
            "sandbox_process_started": False,
            "verifier_executed": False,
            "source_fingerprint_before": source_fingerprint,
        }
    request_digest = _sha256(input_bytes)
    try:
        network_filter = _network_seccomp_filter_bytes()
        network_policy_sha256 = _sha256(network_filter)
        seccomp_fd = _sealed_script_fd(network_filter)
    except (AgentEvalError, OSError) as exc:
        for descriptor, _ in script_fds:
            os.close(descriptor)
        return {
            "status": "evidence_unverified",
            "reason": "network_seccomp_snapshot_unavailable",
            "reason_type": type(exc).__name__,
            "sandbox_process_started": False,
            "verifier_executed": False,
            "source_fingerprint_before": source_fingerprint,
        }
    bwrap_command = _base_argv(
        bwrap=bwrap,
        python=python,
        seccomp_fd=seccomp_fd,
        script_fds=script_fds,
        in_sandbox_source=in_sandbox_source,
        script_name=script_name,
        inner_argv=inner_argv,
    )
    command = bwrap_command
    # The bwrap launcher itself must not inherit CI, user, or auth credentials.
    host_env = {"PATH": "/usr/bin:/bin", "LC_ALL": "C"}
    stdout_file = tempfile.TemporaryFile(mode="w+b")
    stderr_file = tempfile.TemporaryFile(mode="w+b")
    started = time.monotonic()
    try:
        process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=stdout_file,
            stderr=stderr_file,
            env=host_env,
            close_fds=True,
            pass_fds=(
                seccomp_fd,
                *(descriptor for descriptor, _ in script_fds),
            ),
            start_new_session=True,
            preexec_fn=_no_new_privs_and_limits,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        os.close(seccomp_fd)
        for descriptor, _ in script_fds:
            os.close(descriptor)
        stdout_file.close()
        stderr_file.close()
        return {
            "status": "evidence_unverified",
            "reason": "bubblewrap_start_failed",
            "reason_type": type(exc).__name__,
            "sandbox_process_started": False,
            "verifier_executed": False,
        }
    for descriptor, _ in script_fds:
        os.close(descriptor)
    os.close(seccomp_fd)
    timed_out = False
    cleanup_verified = True
    try:
        process.communicate(input=input_bytes, timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        timed_out = True
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            process.wait(timeout=1.0)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            try:
                process.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                cleanup_verified = False
        time.sleep(0.05)
        try:
            os.killpg(process.pid, 0)
        except ProcessLookupError:
            cleanup_verified = True
        except PermissionError:
            cleanup_verified = False
        else:
            cleanup_verified = False
    if post_exit_wait_seconds > 0:
        time.sleep(post_exit_wait_seconds)
    elapsed = time.monotonic() - started
    stdout_file.flush()
    stderr_file.flush()
    stdout_size = os.fstat(stdout_file.fileno()).st_size
    stderr_size = os.fstat(stderr_file.fileno()).st_size
    stdout_file.seek(0)
    stderr_file.seek(0)
    stdout_bytes = stdout_file.read(MAX_OUTPUT_BYTES + 1)
    stderr_bytes = stderr_file.read(MAX_OUTPUT_BYTES + 1)
    stdout_file.close()
    stderr_file.close()
    try:
        source_after = _safe_tree(source_dir)
        source_after_fingerprint = canonical_fingerprint(source_after)
    except (AgentEvalError, OSError):
        source_after_fingerprint = None
    output_secret_shaped = bool(
        _SECRET_RE.search(stdout_bytes.decode("utf-8", errors="replace"))
        or _SECRET_RE.search(stderr_bytes.decode("utf-8", errors="replace"))
    )
    safe = (
        stdout_size <= MAX_OUTPUT_BYTES
        and stderr_size <= MAX_OUTPUT_BYTES
        and source_after_fingerprint == source_fingerprint
        and _sha256(input_bytes) == request_digest
        and cleanup_verified
        and not output_secret_shaped
    )
    if timed_out:
        status = "timeout" if safe else "environment_error"
        reason = "execution_timeout" if safe else "timeout_cleanup_or_integrity_failed"
    elif output_secret_shaped:
        status = "evidence_unverified"
        reason = "secret_shaped_verifier_output_redacted"
    elif not safe:
        status = "environment_error"
        reason = "resource_limit_or_input_integrity_failed"
    elif process.returncode != 0:
        status = "execution_error"
        reason = "sandboxed_verifier_exit_nonzero"
    else:
        status = "completed"
        reason = None
    return {
        "status": status,
        "reason": reason,
        "exit_code": process.returncode,
        "timed_out": timed_out,
        "timeout_cleanup_verified": cleanup_verified,
        "elapsed_seconds": round(elapsed, 3),
        "source_fingerprint_before": source_fingerprint,
        "source_fingerprint_after": source_after_fingerprint,
        "source_unchanged": source_after_fingerprint == source_fingerprint,
        "request_sha256": request_digest,
        "request_unchanged": _sha256(input_bytes) == request_digest,
        "network_enforcement": "seccomp-deny-socket-and-io-uring",
        "network_policy_sha256": network_policy_sha256,
        "script_sha256": entrypoint_sha256,
        "stdout_sha256": None if output_secret_shaped else _sha256(stdout_bytes),
        "stderr_sha256": None if output_secret_shaped else _sha256(stderr_bytes),
        "stdout_bytes": stdout_size,
        "stderr_bytes": stderr_size,
        "stdout": sanitize_diagnostic(
            stdout_bytes.decode("utf-8", errors="replace"), MAX_OUTPUT_BYTES
        ),
        "stderr": sanitize_diagnostic(
            stderr_bytes.decode("utf-8", errors="replace"), MAX_OUTPUT_BYTES
        ),
        "sandbox_process_started": True,
        # bubblewrap can exit nonzero before starting Python. A zero exit proves
        # the requested verifier returned; a nonzero exit alone cannot distinguish
        # sandbox setup failure from a verifier failure.
        "verifier_executed": True if process.returncode == 0 else None,
    }


def probe_isolation() -> dict[str, Any]:
    """Probe the OS boundary with harmless synthetic files before supplied code."""
    host_tools = _host_tools()
    if host_tools is None:
        return {
            "status": "evidence_unverified",
            "reason": "required_bubblewrap_capabilities_unavailable",
            "candidate_executed": False,
        }
    bwrap, python, runtime = host_tools
    with tempfile.TemporaryDirectory(prefix="pr17-verifier-probe-") as temporary:
        root = Path(temporary)
        source = root / "probe"
        source.mkdir()
        marker = root / "evaluator-only.txt"
        marker.write_text("synthetic-evaluator-marker", encoding="utf-8")
        synthetic_credential = root / "synthetic-ci-credential.txt"
        synthetic_credential.write_text("synthetic-ci-credential", encoding="utf-8")
        probe_path = source / "probe.py"
        script = r"""import ctypes, errno, json, os, socket, stat, sys
from pathlib import Path
import resource

status = Path("/proc/self/status").read_text()
status_fields = {
    line.split(":", 1)[0]: line.split(":", 1)[1].strip()
    for line in status.splitlines()
    if ":" in line
}
no_new_privs = status_fields.get("NoNewPrivs", "0")
seccomp_mode = status_fields.get("Seccomp", "0")
cap_eff = status_fields.get("CapEff", "-1")
nspid = status_fields.get("NSpid", "").split()
namespace_names = ("user", "pid", "mnt", "ipc", "uts")
sandbox_namespace_ids = {
    name: os.stat(f"/proc/self/ns/{name}").st_ino for name in namespace_names
}
host_namespace_ids = {
    name: int(value) for name, value in zip(namespace_names, sys.argv[3:8], strict=True)
}
host_pid = int(sys.argv[8])
host_socket_fd = int(sys.argv[9])

protected_environment_names = (
    b"GITHUB_TOKEN=",
    b"ACTIONS_ID_TOKEN_REQUEST_TOKEN=",
    b"CODEX_HOME=",
    b"OPENAI_API_KEY=",
)
try:
    sandbox_pid1_environment = Path("/proc/1/environ").read_bytes()
    sandbox_pid1_environment_secret_unavailable = not any(
        name in sandbox_pid1_environment for name in protected_environment_names
    )
except OSError:
    sandbox_pid1_environment_secret_unavailable = True
try:
    Path(f"/proc/{host_pid}/environ").read_bytes()
    host_process_environment_unreadable = False
except OSError:
    host_process_environment_unreadable = True
required_environment_names = {
    "HOME",
    "TMPDIR",
    "PATH",
    "PYTHONDONTWRITEBYTECODE",
    "PYTHONNOUSERSITE",
    "LC_ALL",
}
allowed_environment_names = {
    "HOME",
    "TMPDIR",
    "PATH",
    "PYTHONDONTWRITEBYTECODE",
    "PYTHONNOUSERSITE",
    "LC_ALL",
    "LC_CTYPE",
}
runtime_environment_missing_required = sorted(
    required_environment_names - set(os.environ)
)
runtime_environment_unexpected_count = len(
    set(os.environ) - allowed_environment_names
)
runtime_environment_sanitized = (
    not runtime_environment_missing_required
    and runtime_environment_unexpected_count == 0
)

try:
    Path(sys.argv[1]).read_text()
    marker_read_denied = False
except OSError:
    marker_read_denied = True
try:
    Path(sys.argv[2]).read_text()
    synthetic_ci_credential_unreadable = False
except OSError:
    synthetic_ci_credential_unreadable = True
try:
    Path(f"/proc/{host_pid}/fd/{host_socket_fd}").readlink()
    host_socket_fd_unreadable = False
except OSError:
    host_socket_fd_unreadable = True

def write_denied(path):
    try:
        Path(path).write_text("no")
        return False
    except OSError:
        return True

root_write_denied = write_denied("/pr17-outside-write")
proc_write_denied = write_denied("/proc/self/comm")
dev_write_denied = write_denied("/dev/pr17-outside-write")
try:
    Path(__file__).write_text("tampered")
    source_write_denied = False
except OSError:
    source_write_denied = True

libc = ctypes.CDLL(None, use_errno=True)
ctypes.set_errno(0)
userns_result = libc.unshare(0x10000000)
userns_errno = ctypes.get_errno() if userns_result == -1 else 0
user_namespace_denied = userns_result == -1 and userns_errno in (
    errno.EPERM,
    errno.EACCES,
)

def socket_creation_denied(family, socktype):
    try:
        descriptor = socket.socket(family, socktype)
    except OSError as exc:
        return exc.errno == errno.EPERM
    else:
        descriptor.close()
        return False

socket_checks = {
    "inet": socket_creation_denied(socket.AF_INET, socket.SOCK_STREAM),
    "inet6": socket_creation_denied(socket.AF_INET6, socket.SOCK_DGRAM),
    "unix": socket_creation_denied(socket.AF_UNIX, socket.SOCK_STREAM),
}

def syscall_denied(number, *args):
    ctypes.set_errno(0)
    result = libc.syscall(number, *args)
    return result == -1 and ctypes.get_errno() == errno.EPERM

io_uring_checks = {number: syscall_denied(number, 0, 0, 0) for number in (425, 426, 427)}
x32_socket_denied = syscall_denied(
    0x40000000 | 41, socket.AF_INET, socket.SOCK_STREAM, 0
)
socket_fds = []
for entry in Path("/proc/self/fd").iterdir():
    try:
        if stat.S_ISSOCK(entry.stat().st_mode):
            socket_fds.append(entry.name)
    except FileNotFoundError:
        continue

try:
    Path("/tmp/probe-scratch").write_text("scratch")
    scratch_write_allowed = True
except OSError:
    scratch_write_allowed = False

request = sys.stdin.buffer.read()
limits = {
    name: list(resource.getrlimit(key))
    for name, key in (
        ("cpu_seconds", resource.RLIMIT_CPU),
        ("address_space_bytes", resource.RLIMIT_AS),
        ("file_size_bytes", resource.RLIMIT_FSIZE),
        ("open_files", resource.RLIMIT_NOFILE),
        ("processes", resource.RLIMIT_NPROC),
        ("core_bytes", resource.RLIMIT_CORE),
    )
}
scratch_limits = {
    path: os.statvfs(path).f_frsize * os.statvfs(path).f_blocks
    for path in ("/tmp", "/workspace")
}
print(json.dumps({
    "pid": os.getpid(),
    "no_new_privs": no_new_privs,
    "seccomp_mode": seccomp_mode,
    "cap_eff": cap_eff,
    "nspid": nspid,
    "sandbox_namespace_ids": sandbox_namespace_ids,
    "host_namespace_ids": host_namespace_ids,
    "sandbox_pid1_environment_secret_unavailable": sandbox_pid1_environment_secret_unavailable,
    "host_process_environment_unreadable": host_process_environment_unreadable,
    "synthetic_ci_credential_unreadable": synthetic_ci_credential_unreadable,
    "host_socket_fd_unreadable": host_socket_fd_unreadable,
    "marker_read_denied": marker_read_denied,
    "root_write_denied": root_write_denied,
    "proc_write_denied": proc_write_denied,
    "dev_write_denied": dev_write_denied,
    "source_write_denied": source_write_denied,
    "user_namespace_denied": user_namespace_denied,
    "user_namespace_errno": userns_errno,
    "socket_checks": socket_checks,
    "io_uring_checks": io_uring_checks,
    "x32_socket_denied": x32_socket_denied,
    "inherited_socket_fds": socket_fds,
    "scratch_write_allowed": scratch_write_allowed,
    "runtime_environment_sanitized": runtime_environment_sanitized,
    "runtime_environment_missing_required": runtime_environment_missing_required,
    "runtime_environment_unexpected_count": runtime_environment_unexpected_count,
    "request": request.decode(),
    "limits": limits,
    "scratch_limits": scratch_limits,
}))
"""
        probe_path.write_text(script, encoding="utf-8")
        source_fingerprint = canonical_fingerprint(_safe_tree(source))
        namespace_names = ("user", "pid", "mnt", "ipc", "uts")
        host_namespace_ids = [
            str(os.stat(f"/proc/self/ns/{name}").st_ino) for name in namespace_names
        ]
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as parent_socket:
            try:
                result = _run_bwrap(
                    bwrap=bwrap,
                    python=python,
                    source_dir=source,
                    in_sandbox_source="/probe",
                    script_name="probe.py",
                    inner_argv=[
                        marker.as_posix(),
                        synthetic_credential.as_posix(),
                        *host_namespace_ids,
                        str(os.getpid()),
                        str(parent_socket.fileno()),
                    ],
                    input_bytes=b"pr17-synthetic-fixed-request",
                    timeout_seconds=10,
                    expected_source_fingerprint=source_fingerprint,
                )
            except OSError as exc:
                return {
                    "status": "evidence_unverified",
                    "reason": "boundary_probe_unavailable",
                    "reason_type": type(exc).__name__,
                    "candidate_executed": False,
                    **runtime,
                }
        try:
            parsed = json.loads(result.pop("stdout", ""))
        except json.JSONDecodeError:
            parsed = None

        socket_checks = (
            parsed.get("socket_checks") if isinstance(parsed, dict) else None
        )
        io_uring_checks = (
            parsed.get("io_uring_checks") if isinstance(parsed, dict) else None
        )
        checks = {
            "unprivileged_no_new_privs": isinstance(parsed, dict)
            and parsed.get("no_new_privs") == "1",
            "seccomp_filter_active": isinstance(parsed, dict)
            and parsed.get("seccomp_mode") == "2",
            "pid_namespace_active": isinstance(parsed, dict)
            and isinstance(parsed.get("pid"), int)
            and 1 < parsed["pid"] < 16
            and parsed.get("nspid") == [str(parsed["pid"])],
            "user_namespace_isolated": isinstance(parsed, dict)
            and parsed.get("sandbox_namespace_ids", {}).get("user")
            != parsed.get("host_namespace_ids", {}).get("user"),
            "mount_namespace_isolated": isinstance(parsed, dict)
            and parsed.get("sandbox_namespace_ids", {}).get("mnt")
            != parsed.get("host_namespace_ids", {}).get("mnt"),
            "ipc_namespace_isolated": isinstance(parsed, dict)
            and parsed.get("sandbox_namespace_ids", {}).get("ipc")
            != parsed.get("host_namespace_ids", {}).get("ipc"),
            "uts_namespace_isolated": isinstance(parsed, dict)
            and parsed.get("sandbox_namespace_ids", {}).get("uts")
            != parsed.get("host_namespace_ids", {}).get("uts"),
            "no_effective_capabilities": isinstance(parsed, dict)
            and parsed.get("cap_eff") == "0000000000000000",
            "nested_user_namespace_denied": isinstance(parsed, dict)
            and parsed.get("user_namespace_denied") is True,
            "evaluator_marker_unreadable": isinstance(parsed, dict)
            and parsed.get("marker_read_denied") is True,
            "runtime_environment_is_allowlisted": isinstance(parsed, dict)
            and parsed.get("runtime_environment_sanitized") is True,
            "sandbox_pid1_environment_secret_unavailable": isinstance(parsed, dict)
            and parsed.get("sandbox_pid1_environment_secret_unavailable") is True,
            "host_process_environment_unreadable": isinstance(parsed, dict)
            and parsed.get("host_process_environment_unreadable") is True,
            "synthetic_ci_credential_unreadable": isinstance(parsed, dict)
            and parsed.get("synthetic_ci_credential_unreadable") is True,
            "host_socket_fd_unreadable": isinstance(parsed, dict)
            and parsed.get("host_socket_fd_unreadable") is True,
            "root_filesystem_read_only": isinstance(parsed, dict)
            and parsed.get("root_write_denied") is True,
            "proc_filesystem_read_only": isinstance(parsed, dict)
            and parsed.get("proc_write_denied") is True,
            "dev_filesystem_read_only": isinstance(parsed, dict)
            and parsed.get("dev_write_denied") is True,
            "source_read_only": isinstance(parsed, dict)
            and parsed.get("source_write_denied") is True,
            "network_socket_syscalls_denied": isinstance(socket_checks, dict)
            and {"inet", "inet6", "unix"}.issubset(socket_checks)
            and all(socket_checks.values()),
            "io_uring_syscalls_denied": isinstance(io_uring_checks, dict)
            and io_uring_checks == {"425": True, "426": True, "427": True},
            "x32_syscall_abi_denied": isinstance(parsed, dict)
            and parsed.get("x32_socket_denied") is True,
            "no_inherited_socket_descriptors": isinstance(parsed, dict)
            and parsed.get("inherited_socket_fds") == [],
            "bounded_scratch_available": isinstance(parsed, dict)
            and parsed.get("scratch_write_allowed") is True,
            "fixed_request_delivered": isinstance(parsed, dict)
            and parsed.get("request") == "pr17-synthetic-fixed-request",
            "limits_applied": isinstance(parsed, dict)
            and isinstance(parsed.get("limits"), dict)
            and all(
                isinstance(parsed["limits"].get(name), list)
                and len(parsed["limits"][name]) == 2
                and parsed["limits"][name][0] <= maximum
                and parsed["limits"][name][0] <= parsed["limits"][name][1]
                for name, maximum in {
                    "cpu_seconds": 60,
                    "address_space_bytes": 2_000_000_000,
                    "file_size_bytes": MAX_OUTPUT_BYTES,
                    "open_files": 64,
                    "processes": 128,
                    "core_bytes": 0,
                }.items()
            )
            and len(parsed["limits"]) == 6,
            "tmpfs_limits_applied": isinstance(parsed, dict)
            and isinstance(parsed.get("scratch_limits"), dict)
            and 0 < parsed["scratch_limits"].get("/tmp", 0) <= TMPFS_BYTES
            and 0 < parsed["scratch_limits"].get("/workspace", 0) <= TMPFS_BYTES,
            "source_unchanged": result.get("source_unchanged") is True
            and result.get("source_fingerprint_before") == source_fingerprint,
            "request_unchanged": result.get("request_unchanged") is True,
            "exit_success": result.get("status") == "completed",
        }
        diagnostics = {
            "nested_user_namespace_errno": (
                parsed.get("user_namespace_errno") if isinstance(parsed, dict) else None
            ),
            "runtime_environment_missing_required": (
                parsed.get("runtime_environment_missing_required")
                if isinstance(parsed, dict)
                else None
            ),
            "runtime_environment_unexpected_count": (
                parsed.get("runtime_environment_unexpected_count")
                if isinstance(parsed, dict)
                else None
            ),
        }

        timeout_path = source / "timeout.py"
        timeout_path.write_text(
            '''import subprocess, sys, time
child = """import os, time
time.sleep(1.5)
os.write(1, b'DETACHED_CHILD_SURVIVED\\\\n')
"""
subprocess.Popen([sys.executable, '-E', '-s', '-S', '-B', '-c', child], start_new_session=True, close_fds=False)
time.sleep(30)
''',
            encoding="utf-8",
        )
        timeout_execution = _run_bwrap(
            bwrap=bwrap,
            python=python,
            source_dir=source,
            in_sandbox_source="/probe",
            script_name="timeout.py",
            inner_argv=[],
            input_bytes=b"",
            timeout_seconds=1,
            expected_source_fingerprint=canonical_fingerprint(_safe_tree(source)),
            post_exit_wait_seconds=2,
        )
        checks["detached_child_killed_with_pid_namespace"] = timeout_execution.get(
            "status"
        ) == "timeout" and "DETACHED_CHILD_SURVIVED" not in timeout_execution.get(
            "stdout", ""
        )
        checks["timeout_cleanup_verified"] = (
            timeout_execution.get("timeout_cleanup_verified") is True
        )
        return {
            "status": "verified" if all(checks.values()) else "evidence_unverified",
            "reason": None if all(checks.values()) else "isolation_probe_failed",
            "checks": checks,
            "diagnostics": diagnostics,
            "probe_execution": result,
            "candidate_executed": False,
            **runtime,
        }


def run_isolated_python(
    *,
    source_dir: Path,
    script_name: str,
    request_bytes: bytes,
    timeout_seconds: float = 60,
    expected_source_fingerprint: str | None = None,
) -> dict[str, Any]:
    """Run a verifier only after the local OS boundary passes its synthetic probe."""
    relative = PurePosixPath(script_name)
    if (
        relative.is_absolute()
        or ".." in relative.parts
        or len(relative.parts) != 1
        or not script_name.endswith(".py")
    ):
        raise AgentEvalError("isolated verifier script name is unsafe")
    try:
        source_files = _safe_tree(source_dir)
    except (AgentEvalError, OSError) as exc:
        return {
            "status": "evidence_unverified",
            "reason": "candidate_source_invalid",
            "reason_type": type(exc).__name__,
            "sandbox_process_started": False,
            "verifier_executed": False,
        }
    if script_name not in {row["path"] for row in source_files}:
        return {
            "status": "evidence_unverified",
            "reason": "candidate_source_script_missing",
            "sandbox_process_started": False,
            "verifier_executed": False,
            "source_fingerprint": canonical_fingerprint(source_files),
        }
    source_fingerprint = canonical_fingerprint(source_files)
    if (
        expected_source_fingerprint is not None
        and source_fingerprint != expected_source_fingerprint
    ):
        return {
            "status": "evidence_unverified",
            "reason": "candidate_source_fingerprint_mismatch",
            "sandbox_process_started": False,
            "verifier_executed": False,
            "source_fingerprint": source_fingerprint,
        }
    if len(request_bytes) > MAX_REQUEST_BYTES:
        return {
            "status": "evidence_unverified",
            "reason": "request_exceeds_size_limit",
            "sandbox_process_started": False,
            "verifier_executed": False,
            "source_fingerprint": source_fingerprint,
        }
    probe = probe_isolation()
    if probe.get("status") != "verified":
        return {
            "status": "evidence_unverified",
            "reason": probe.get("reason", "isolation_not_verified"),
            "sandbox_process_started": False,
            "verifier_executed": False,
            "source_fingerprint": source_fingerprint,
            "isolation_probe": probe,
        }
    host_tools = _host_tools()
    if host_tools is None:
        return {
            "status": "evidence_unverified",
            "reason": "bubblewrap_capabilities_changed_after_probe",
            "sandbox_process_started": False,
            "verifier_executed": False,
            "isolation_probe": probe,
        }
    bwrap, python, runtime = host_tools
    result = _run_bwrap(
        bwrap=bwrap,
        python=python,
        source_dir=source_dir,
        in_sandbox_source="/candidate",
        script_name=script_name,
        inner_argv=[],
        input_bytes=request_bytes,
        timeout_seconds=timeout_seconds,
        expected_source_fingerprint=expected_source_fingerprint,
    )
    stdout = result.pop("stdout", "")
    stderr = result.pop("stderr", "")
    if (
        result.get("status") == "completed"
        and result.get("verifier_executed") is not True
    ):
        result.update(
            status="evidence_unverified",
            reason="verifier_execution_not_proven",
        )
    if result.get("status") == "completed":
        try:
            parsed = json.loads(stdout, object_pairs_hook=_strict_object)
        except ValueError:
            result.update(status="execution_error", reason="invalid_verifier_json")
        else:
            if not isinstance(parsed, dict):
                result.update(status="execution_error", reason="invalid_verifier_shape")
            else:
                result["result"] = parsed
                result["result_sha256"] = result.get("stdout_sha256")
                result["parsed_result_sha256"] = _sha256(stdout.encode("utf-8"))
                result["status"] = "verified"
    result["stdout"] = stdout
    result["stderr"] = stderr
    result["source_fingerprint"] = source_fingerprint
    result["isolation_probe"] = probe
    result["runtime"] = runtime
    return result
