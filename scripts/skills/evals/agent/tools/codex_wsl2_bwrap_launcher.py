from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import signal
import socket
import stat
import subprocess
import sys
import tempfile
import tomllib
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Iterator, Sequence

REPO_ROOT = Path(__file__).resolve().parents[5]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.skills.evals.agent.tools.codex_docker_launcher import (  # noqa: E402
    summarize_codex_jsonl,
)

PACKAGE_NAME = "@openai/codex"
PACKAGE_VERSION = "0.163.0-linux-x64"
PACKAGE_URL = "https://registry.npmjs.org/@openai/codex/-/codex-0.163.0-linux-x64.tgz"
PACKAGE_SHA512 = "bb045a3acad8a202d085cc4033f1a8796af0d1021610c468edcf6033cb0a02f89591940796ef6444b2793e4b9f6d5f800468f2660230885749d0b089d0de9ef3"
CODEX_RELATIVE_PATH = PurePosixPath(
    "package/vendor/x86_64-unknown-linux-musl/bin/codex"
)
BWRAP_RELATIVE_PATH = PurePosixPath(
    "package/vendor/x86_64-unknown-linux-musl/codex-resources/bwrap"
)
PROTOCOL = "codex_wsl2_bwrap_launcher_v1"
RUNTIME_ENV = "QAEVAL_CODEX_RUNTIME_ROOT"
CODEX_HOME_PREFIX = ".qa-codex-home-"
EVALUATION_SERVICE_ACCOUNT = "qa-agent-eval"
AUTH_STATE_RELATIVE = Path(".local/state/qa-workflow-skills")
AUTH_STORE_LOCK_NAME = "codex-auth.lock"
AUTH_STATE_UNCERTAIN_NAME = "codex-auth-state-uncertain"
AUTH_STATUS_TIMEOUT_SECONDS = 15
# Named Codex permission profiles deny the authentication file in the inner
# sandbox while preserving the outer mode-specific filesystem boundary.
AUTHENTICATION_SHELL_VISIBLE_RISK = True
# The persistent-store path is implemented, but the dedicated OS identity and
# its process-start boundary have not been provisioned and verified.
AUTHENTICATION_REFRESH_PERSISTENCE_UNRESOLVED = True
AUTHENTICATION_PROCESS_CONCURRENCY_UNRESOLVED = True
_SAFE_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}$")
_PERMISSION_PROFILE_BY_MODE = {
    "agent": "qa_eval_agent",
    "judge": "qa_eval_judge",
    "repair": "qa_eval_repair",
}


class CodexWsl2LauncherError(RuntimeError):
    pass


def _permission_profile_for_mode(mode: str) -> str:
    try:
        return _PERMISSION_PROFILE_BY_MODE[mode]
    except KeyError:
        raise CodexWsl2LauncherError("execution mode is invalid") from None


def _authentication_execution_blockers() -> list[str]:
    blockers: list[str] = []
    if AUTHENTICATION_SHELL_VISIBLE_RISK:
        blockers.append("authentication_shell_visible_risk")
    if AUTHENTICATION_REFRESH_PERSISTENCE_UNRESOLVED:
        blockers.append("authentication_refresh_persistence_unresolved")
    if AUTHENTICATION_PROCESS_CONCURRENCY_UNRESOLVED:
        blockers.append("authentication_process_concurrency_unresolved")
    return blockers


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _is_wsl2() -> bool:
    release = platform.release().lower()
    return platform.system() == "Linux" and "microsoft-standard-wsl2" in release


def _require_wsl2() -> None:
    if not _is_wsl2():
        raise CodexWsl2LauncherError("live Codex evaluation requires WSL2 Ubuntu")
    if os.geteuid() == 0:
        raise CodexWsl2LauncherError("Codex evaluation must run as a non-root user")


def _reject_symlink_components(path: Path, *, allow_leaf: bool = False) -> Path:
    absolute = Path(os.path.abspath(path.expanduser()))
    current = Path(absolute.anchor)
    parts = absolute.parts[1:]
    for index, part in enumerate(parts):
        current = current / part
        if allow_leaf and index == len(parts) - 1 and not current.exists():
            break
        try:
            mode = current.lstat().st_mode
        except FileNotFoundError:
            if allow_leaf and index == len(parts) - 1:
                break
            raise CodexWsl2LauncherError("required path does not exist") from None
        if stat.S_ISLNK(mode):
            raise CodexWsl2LauncherError("sandbox paths may not contain symlinks")
    return absolute


def _regular_file(path: Path) -> bool:
    try:
        return stat.S_ISREG(path.lstat().st_mode)
    except OSError:
        return False


def _reject_workspace_symlinks(workspace: Path) -> None:
    if any(path.is_symlink() for path in workspace.rglob("*")):
        raise CodexWsl2LauncherError("workspace source may not contain symlinks")


def _directory(path: Path, *, writable: bool | None = None) -> Path:
    path = _reject_symlink_components(path)
    try:
        metadata = path.stat()
    except OSError as exc:
        raise CodexWsl2LauncherError("sandbox directory is unavailable") from exc
    if not stat.S_ISDIR(metadata.st_mode):
        raise CodexWsl2LauncherError("sandbox path must be a directory")
    if writable is True and not os.access(path, os.W_OK):
        raise CodexWsl2LauncherError("sandbox directory must be writable")
    if writable is False and os.access(path, os.W_OK):
        # A writable host source is acceptable only because it is bind-mounted read-only.
        return path
    return path


def _private_temp_root() -> Path:
    base = Path(tempfile.gettempdir())
    if os.name == "posix" and hasattr(os, "getuid"):
        base = base / f"qa-workflow-skills-codex-homes-{os.getuid()}"
        if base.exists():
            if base.is_symlink() or not base.is_dir():
                raise CodexWsl2LauncherError("temporary Codex home root is invalid")
            metadata = base.stat()
            if metadata.st_uid != os.getuid() or stat.S_IMODE(metadata.st_mode) & 0o077:
                raise CodexWsl2LauncherError("temporary Codex home root is not private")
        else:
            base.mkdir(mode=0o700)
        os.chmod(base, 0o700)
    return base


@dataclass(frozen=True)
class AuthExecutionPaths:
    uid: int
    home: Path
    codex_home: Path
    auth_file: Path
    state_dir: Path
    lock_file: Path
    uncertain_file: Path


class AuthExecutionBlocked(CodexWsl2LauncherError):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def _owned_private_path(path: Path, *, uid: int, mode: int, directory: bool) -> bool:
    try:
        metadata = path.lstat()
    except OSError:
        return False
    return (
        not stat.S_ISLNK(metadata.st_mode)
        and (
            stat.S_ISDIR(metadata.st_mode)
            if directory
            else stat.S_ISREG(metadata.st_mode)
        )
        and metadata.st_uid == uid
        and stat.S_IMODE(metadata.st_mode) == mode
    )


def _evaluation_auth_paths() -> AuthExecutionPaths:
    if os.name != "posix" or not _is_wsl2():
        raise AuthExecutionBlocked("authentication_execution_requires_wsl2")
    try:
        import pwd

        account = pwd.getpwnam(EVALUATION_SERVICE_ACCOUNT)
    except (ImportError, KeyError, OSError):
        raise AuthExecutionBlocked("evaluation_service_account_unavailable") from None
    uid = account.pw_uid
    if (
        uid == 0
        or os.geteuid() != uid
        or os.getgid() != account.pw_gid
        or any(group != account.pw_gid for group in os.getgroups())
        or account.pw_shell not in {"/usr/sbin/nologin", "/sbin/nologin"}
    ):
        raise AuthExecutionBlocked("evaluation_service_identity_invalid")
    home = Path(account.pw_dir)
    codex_home = home / ".codex"
    configured_home = os.environ.get("HOME")
    configured_codex_home = os.environ.get("CODEX_HOME")
    if (
        not home.is_absolute()
        or configured_home != str(home)
        or configured_codex_home != str(codex_home)
    ):
        raise AuthExecutionBlocked("evaluation_auth_home_mismatch")
    try:
        _reject_symlink_components(home)
        _reject_symlink_components(codex_home)
    except CodexWsl2LauncherError:
        raise AuthExecutionBlocked("evaluation_auth_home_path_invalid") from None
    if not _owned_private_path(home, uid=uid, mode=0o700, directory=True):
        raise AuthExecutionBlocked("evaluation_auth_home_permissions_invalid")
    if not _owned_private_path(codex_home, uid=uid, mode=0o700, directory=True):
        raise AuthExecutionBlocked("evaluation_codex_home_permissions_invalid")
    config_path = codex_home / "config.toml"
    if not _owned_private_path(config_path, uid=uid, mode=0o600, directory=False):
        raise AuthExecutionBlocked("evaluation_codex_config_permissions_invalid")
    try:
        with config_path.open("rb") as stream:
            config = tomllib.load(stream)
    except (OSError, tomllib.TOMLDecodeError):
        raise AuthExecutionBlocked("evaluation_codex_config_invalid") from None
    if config.get("cli_auth_credentials_store") != "file":
        raise AuthExecutionBlocked("evaluation_auth_store_mode_invalid")
    if config.get("forced_login_method") not in {None, "chatgpt"}:
        raise AuthExecutionBlocked("evaluation_login_method_invalid")
    auth_file = codex_home / "auth.json"
    if auth_file.exists() or auth_file.is_symlink():
        if not _owned_private_path(auth_file, uid=uid, mode=0o600, directory=False):
            raise AuthExecutionBlocked("evaluation_auth_file_permissions_invalid")
    state_dir = home / AUTH_STATE_RELATIVE
    for directory in (state_dir.parents[1], state_dir.parent, state_dir):
        if directory.exists() or directory.is_symlink():
            if not _owned_private_path(directory, uid=uid, mode=0o700, directory=True):
                raise AuthExecutionBlocked("evaluation_auth_state_permissions_invalid")
        else:
            try:
                directory.mkdir(mode=0o700)
            except FileExistsError:
                pass
            except OSError:
                raise AuthExecutionBlocked(
                    "evaluation_auth_state_unavailable"
                ) from None
            if not _owned_private_path(directory, uid=uid, mode=0o700, directory=True):
                raise AuthExecutionBlocked("evaluation_auth_state_permissions_invalid")
    return AuthExecutionPaths(
        uid=uid,
        home=home,
        codex_home=codex_home,
        auth_file=auth_file,
        state_dir=state_dir,
        lock_file=state_dir / AUTH_STORE_LOCK_NAME,
        uncertain_file=state_dir / AUTH_STATE_UNCERTAIN_NAME,
    )


def _assert_no_other_service_processes(
    uid: int, *, proc_root: Path = Path("/proc")
) -> None:
    allowed: set[int] = set()
    current = os.getpid()
    while current > 1 and current not in allowed:
        allowed.add(current)
        try:
            status = (proc_root / str(current) / "status").read_text(encoding="ascii")
        except OSError:
            break
        parent_line = next(
            (line for line in status.splitlines() if line.startswith("PPid:")), None
        )
        if parent_line is None:
            break
        try:
            current = int(parent_line.split()[1])
        except (IndexError, ValueError):
            break
    try:
        entries = tuple(proc_root.iterdir())
    except OSError:
        raise AuthExecutionBlocked("service_process_list_unavailable") from None
    for entry in entries:
        if not entry.name.isdecimal():
            continue
        try:
            pid = int(entry.name)
            status = (entry / "status").read_text(encoding="ascii")
        except FileNotFoundError:
            continue
        except (OSError, ValueError):
            raise AuthExecutionBlocked("service_process_identity_unavailable") from None
        uid_line = next(
            (line for line in status.splitlines() if line.startswith("Uid:")), None
        )
        if uid_line is None:
            raise AuthExecutionBlocked("service_process_identity_unavailable")
        try:
            process_uids = {int(value) for value in uid_line.split()[1:]}
        except ValueError:
            raise AuthExecutionBlocked("service_process_identity_unavailable") from None
        if uid in process_uids and pid not in allowed:
            raise AuthExecutionBlocked("unexpected_service_identity_process")


@contextmanager
def _authentication_execution_context(
    *, allow_uncertain_state: bool = False
) -> Iterator[AuthExecutionPaths]:
    try:
        import fcntl
    except ImportError:
        raise AuthExecutionBlocked("authentication_process_lock_unavailable") from None
    paths = _evaluation_auth_paths()
    flags = os.O_CREAT | os.O_RDWR
    flags |= getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        lock_fd = os.open(paths.lock_file, flags, 0o600)
    except OSError:
        raise AuthExecutionBlocked("authentication_process_lock_unavailable") from None
    try:
        if not _owned_private_path(
            paths.lock_file, uid=paths.uid, mode=0o600, directory=False
        ):
            raise AuthExecutionBlocked(
                "authentication_process_lock_permissions_invalid"
            )
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            raise AuthExecutionBlocked("authentication_process_lock_busy") from None
        _assert_no_other_service_processes(paths.uid)
        if paths.uncertain_file.exists() or paths.uncertain_file.is_symlink():
            if not allow_uncertain_state:
                raise AuthExecutionBlocked("authentication_state_uncertain")
            if not _owned_private_path(
                paths.uncertain_file, uid=paths.uid, mode=0o600, directory=False
            ):
                raise AuthExecutionBlocked("authentication_state_marker_invalid")
        yield paths
    finally:
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
        except OSError:
            pass
        os.close(lock_fd)


def _mark_auth_state_uncertain(paths: AuthExecutionPaths) -> None:
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    flags |= getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(paths.uncertain_file, flags, 0o600)
    except OSError:
        raise AuthExecutionBlocked(
            "authentication_state_marker_create_failed"
        ) from None
    try:
        if not _owned_private_path(
            paths.uncertain_file, uid=paths.uid, mode=0o600, directory=False
        ):
            raise AuthExecutionBlocked(
                "authentication_state_marker_permissions_invalid"
            )
        marker = memoryview(b"codex_attempt_incomplete\n")
        while marker:
            written = os.write(fd, marker)
            if written <= 0:
                raise OSError("authentication state marker write failed")
            marker = marker[written:]
        os.fsync(fd)
        directory_fd = os.open(
            paths.state_dir, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
        )
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        os.close(fd)


def _clear_auth_state_uncertain(paths: AuthExecutionPaths) -> None:
    if not paths.uncertain_file.exists() and not paths.uncertain_file.is_symlink():
        return
    if not _owned_private_path(
        paths.uncertain_file, uid=paths.uid, mode=0o600, directory=False
    ):
        raise AuthExecutionBlocked("authentication_state_marker_invalid")
    paths.uncertain_file.unlink()
    directory_fd = os.open(paths.state_dir, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        try:
            os.fsync(directory_fd)
        except OSError:
            try:
                _mark_auth_state_uncertain(paths)
            except (OSError, AuthExecutionBlocked):
                raise AuthExecutionBlocked(
                    "authentication_state_marker_restore_failed"
                ) from None
            raise AuthExecutionBlocked(
                "authentication_state_marker_clear_failed"
            ) from None
    finally:
        os.close(directory_fd)


def _sync_auth_store(paths: AuthExecutionPaths) -> None:
    """Durably sync the opaque Codex store without reading its contents."""
    try:
        auth_file = _reject_symlink_components(paths.auth_file)
        if not _owned_private_path(
            auth_file, uid=paths.uid, mode=0o600, directory=False
        ):
            raise AuthExecutionBlocked("authentication_auth_file_permissions_invalid")
        flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
        auth_fd = os.open(auth_file, flags)
    except (OSError, CodexWsl2LauncherError) as exc:
        if isinstance(exc, AuthExecutionBlocked):
            raise
        raise AuthExecutionBlocked("authentication_store_sync_failed") from None
    try:
        metadata = os.fstat(auth_fd)
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_uid != paths.uid
            or stat.S_IMODE(metadata.st_mode) != 0o600
        ):
            raise AuthExecutionBlocked("authentication_auth_file_permissions_invalid")
        os.fsync(auth_fd)
        if not _owned_private_path(
            paths.codex_home, uid=paths.uid, mode=0o700, directory=True
        ):
            raise AuthExecutionBlocked("evaluation_codex_home_permissions_invalid")
        directory_fd = os.open(
            paths.codex_home,
            os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_CLOEXEC", 0),
        )
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    except OSError:
        raise AuthExecutionBlocked("authentication_store_sync_failed") from None
    finally:
        os.close(auth_fd)


def _finalize_auth_state(paths: AuthExecutionPaths) -> None:
    """Clear the uncertainty marker only after the child identity has exited."""
    _assert_no_other_service_processes(paths.uid)
    _sync_auth_store(paths)
    _clear_auth_state_uncertain(paths)


def runtime_root_from_environment() -> Path:
    configured = os.environ.get(RUNTIME_ENV)
    if configured:
        return Path(configured)
    default = (
        Path.home()
        / ".cache"
        / "qa-workflow-skills"
        / f"codex-{PACKAGE_VERSION}-{PACKAGE_SHA512[:12]}"
    )
    return default


def verify_runtime(runtime_root: Path | None = None) -> dict[str, Any]:
    _require_wsl2()
    root = _directory(runtime_root or runtime_root_from_environment())
    manifest_path = root / "runtime-manifest.json"
    if not _regular_file(manifest_path):
        raise CodexWsl2LauncherError("verified Codex runtime manifest is missing")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CodexWsl2LauncherError("Codex runtime manifest is invalid") from exc
    if not isinstance(manifest, dict) or (
        manifest.get("schema_version") != 1
        or manifest.get("package_name") != PACKAGE_NAME
        or manifest.get("package_version") != PACKAGE_VERSION
        or manifest.get("package_url") != PACKAGE_URL
        or manifest.get("package_sha512") != PACKAGE_SHA512
        or manifest.get("codex_relative_path") != CODEX_RELATIVE_PATH.as_posix()
        or manifest.get("bwrap_relative_path") != BWRAP_RELATIVE_PATH.as_posix()
    ):
        raise CodexWsl2LauncherError("Codex runtime manifest does not match the pin")
    codex_path = _reject_symlink_components(root.joinpath(*CODEX_RELATIVE_PATH.parts))
    bwrap_path = _reject_symlink_components(root.joinpath(*BWRAP_RELATIVE_PATH.parts))
    for binary in (codex_path, bwrap_path):
        if (
            binary.is_symlink()
            or not _regular_file(binary)
            or not os.access(binary, os.X_OK)
        ):
            raise CodexWsl2LauncherError(
                "Codex runtime binary is not a regular executable"
            )
    codex_digest = _sha256(codex_path)
    bwrap_digest = _sha256(bwrap_path)
    if (
        manifest.get("codex_sha256") != codex_digest
        or manifest.get("bwrap_sha256") != bwrap_digest
    ):
        raise CodexWsl2LauncherError("Codex or bundled bubblewrap digest mismatch")
    codex_version = _version_probe(codex_path, ["--version"])
    if not re.search(r"\b0\.163\.0\b", codex_version):
        raise CodexWsl2LauncherError("Codex CLI version does not match 0.163.0")
    bwrap_version = _version_probe(bwrap_path, ["--version"])
    if "bubblewrap" not in bwrap_version.lower():
        raise CodexWsl2LauncherError("bundled bubblewrap version probe mismatch")
    return {
        "package_name": PACKAGE_NAME,
        "package_version": PACKAGE_VERSION,
        "package_url": PACKAGE_URL,
        "package_sha512": PACKAGE_SHA512,
        "codex_path": str(codex_path),
        "codex_sha256": codex_digest,
        "codex_version": codex_version,
        "bwrap_path": str(bwrap_path),
        "bwrap_sha256": bwrap_digest,
        "bwrap_version": bwrap_version,
        "kernel": platform.release(),
        "machine": platform.machine(),
        "python_version": platform.python_version(),
    }


def _version_probe(binary: Path, argv: list[str]) -> str:
    try:
        result = subprocess.run(
            [str(binary), *argv],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=15,
            check=False,
            shell=False,
            close_fds=True,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise CodexWsl2LauncherError("runtime binary version probe failed") from exc
    output = (result.stdout + result.stderr).decode("utf-8", errors="replace")[:500]
    if result.returncode != 0:
        raise CodexWsl2LauncherError("runtime binary version probe failed")
    return output.strip()


def _system_mounts() -> list[tuple[Path, str]]:
    mounts: list[tuple[Path, str]] = []
    usr = Path("/usr")
    if not usr.is_dir():
        raise CodexWsl2LauncherError("WSL2 /usr runtime is unavailable")
    mounts.append((usr.resolve(), "/usr"))
    for source, target in ((Path("/etc/ssl/certs"), "/etc/ssl/certs"),):
        if source.exists():
            mounts.append((source.resolve(), target))
    resolv = Path("/etc/resolv.conf")
    if resolv.exists():
        mounts.append((resolv.resolve(), "/etc/resolv.conf"))
    return mounts


def _validate_workspace_mounts(
    *,
    mode: str,
    workspace_root: Path | None,
    output_root: Path | None,
    skill_root: Path | None,
    skill_name: str | None,
) -> tuple[Path | None, Path | None, Path | None]:
    if mode == "judge":
        if (
            workspace_root is not None
            or output_root is not None
            or skill_root is not None
        ):
            raise CodexWsl2LauncherError("Judge mode may not receive Agent mounts")
        return None, None, None
    if workspace_root is None or output_root is None:
        raise CodexWsl2LauncherError("Agent mode requires workspace and output roots")
    workspace = _directory(workspace_root)
    _reject_workspace_symlinks(workspace)
    _directory(workspace / ".agents" / "skills")
    output = _directory(output_root, writable=True)
    nested_output = output == workspace / ".qa-eval-output"
    if (
        output.is_symlink()
        or output == workspace
        or (workspace in output.parents and not nested_output)
    ):
        raise CodexWsl2LauncherError(
            "output root must be separate or the named output directory"
        )
    if any(output.iterdir()):
        raise CodexWsl2LauncherError("attempt output root must be empty before launch")
    output_mountpoint = workspace / ".qa-eval-output"
    if output_mountpoint.is_symlink() or not output_mountpoint.is_dir():
        raise CodexWsl2LauncherError("workspace output mountpoint is invalid")
    if any(output_mountpoint.iterdir()):
        raise CodexWsl2LauncherError("workspace output mountpoint must be empty")
    git_mountpoint = workspace / ".git"
    if git_mountpoint.is_symlink() or git_mountpoint.exists():
        raise CodexWsl2LauncherError("workspace may not contain an existing .git entry")
    codex_mountpoint = workspace / ".codex"
    if codex_mountpoint.is_symlink() or codex_mountpoint.exists():
        raise CodexWsl2LauncherError(
            "workspace may not contain an existing .codex entry"
        )
    if mode == "repair":
        if (
            skill_root is None
            or skill_name is None
            or not _SAFE_NAME_RE.fullmatch(skill_name)
        ):
            raise CodexWsl2LauncherError("repair mode requires one fixed Skill root")
        skill = _directory(skill_root, writable=True)
        skill_target = workspace / ".agents" / "skills" / skill_name
        if skill_target.is_symlink() or not skill_target.is_dir():
            raise CodexWsl2LauncherError("repair Skill mountpoint is invalid")
        git_mountpoint.mkdir(mode=0o700)
        codex_mountpoint.mkdir(mode=0o700)
        return workspace, output, skill
    if skill_root is not None or skill_name is not None:
        raise CodexWsl2LauncherError("only repair mode may receive a writable Skill")
    git_mountpoint.mkdir(mode=0o700)
    codex_mountpoint.mkdir(mode=0o700)
    return workspace, output, None


def _mount_tree(
    *,
    runtime_root: Path,
    mode: str,
    workspace_root: Path | None,
    output_root: Path | None,
    skill_root: Path | None,
    skill_name: str | None,
    codex_home: Path,
    auth_store_path: Path | None = None,
) -> tuple[list[str], dict[str, Any]]:
    mounts = [
        "--tmpfs",
        "/",
        "--dir",
        "/usr",
        "--dir",
        "/etc",
        "--dir",
        "/opt",
        "--dir",
        "/opt/codex-runtime",
        "--dir",
        "/var",
        "--dir",
        "/tmp",
        "--dir",
        "/codex-home",
        "--ro-bind",
        "/usr",
        "/usr",
        "--symlink",
        "usr/bin",
        "/bin",
        "--symlink",
        "usr/lib",
        "/lib",
        "--symlink",
        "usr/lib64",
        "/lib64",
        "--ro-bind",
        str(runtime_root),
        "/opt/codex-runtime",
        "--bind",
        str(codex_home),
        "/codex-home",
        "--dev",
        "/dev",
        "--proc",
        "/proc",
    ]
    mount_summary: dict[str, Any] = {
        "root": "tmpfs",
        "system": [
            "/usr",
            "/bin",
            "/lib",
            "/lib64",
            "/etc/ssl/certs",
            "/etc/resolv.conf",
        ],
        "runtime": "/opt/codex-runtime",
        "codex_home": "/codex-home",
        "workspace": None,
        "output": None,
        "writable_skill": None,
        "host_home": False,
        "windows_filesystem": False,
        "evaluator_checkout": False,
        "docker_socket": False,
    }
    if auth_store_path is not None:
        auth_store_path = _reject_symlink_components(auth_store_path)
        if not _regular_file(auth_store_path) or not _regular_file(
            codex_home / "auth.json"
        ):
            raise CodexWsl2LauncherError("persistent Codex auth mount is invalid")
        mounts.extend(["--bind", str(auth_store_path), "/codex-home/auth.json"])
        mount_summary["auth_store"] = {
            "path": "/codex-home/auth.json",
            "access": "read-write-codex-parent-only",
            "persistent": True,
            "inner_shell_read": "denied-by-named-permission-profile",
        }
    for source, target in _system_mounts():
        if target == "/etc/resolv.conf":
            mounts.extend(["--ro-bind", str(source), target])
        else:
            parent = str(PurePosixPath(target).parent)
            if parent != "/":
                mounts.extend(["--dir", parent])
            mounts.extend(["--dir", target])
            mounts.extend(["--ro-bind", str(source), target])
    if mode == "judge":
        mounts.extend(["--tmpfs", "/var/tmp"])
    else:
        assert workspace_root is not None and output_root is not None
        workspace = workspace_root.resolve()
        output = output_root.resolve()
        mounts.extend(["--bind", str(workspace), "/workspace"])
        mounts.extend(["--bind", str(output), "/workspace/.qa-eval-output"])
        git_scratch = Path(str(codex_home) + ".git")
        if git_scratch.exists() or git_scratch.is_symlink():
            raise CodexWsl2LauncherError(
                "workspace contains an unexpected scratch entry"
            )
        git_scratch.mkdir(mode=0o700)
        codex_scratch = Path(str(codex_home) + ".workspace-codex")
        if codex_scratch.exists() or codex_scratch.is_symlink():
            raise CodexWsl2LauncherError(
                "workspace contains an unexpected Codex scratch entry"
            )
        codex_scratch.mkdir(mode=0o700)
        # Codex's workspace-write sandbox prepares .git; the only writable Git metadata
        # is this empty attempt-local scratch directory, mounted over an empty mountpoint.
        mounts.extend(["--bind", str(git_scratch), "/workspace/.git"])
        mounts.extend(["--bind", str(codex_scratch), "/workspace/.codex"])
        read_only_entries: list[str] = []
        for source in sorted(workspace.iterdir(), key=lambda item: item.name):
            if source.name in {".qa-eval-output", ".git", ".codex"}:
                continue
            mounts.extend(["--ro-bind", str(source), f"/workspace/{source.name}"])
            read_only_entries.append(source.name)
        mount_summary["workspace"] = {
            "path": "/workspace",
            "access": "writable-root-with-read-only-source-children",
            "read_only_source_entries": read_only_entries,
        }
        mount_summary["output"] = {
            "path": "/workspace/.qa-eval-output",
            "access": "read-write",
        }
        mount_summary["codex_scratch"] = {
            "path": "/workspace/.codex",
            "access": "read-write",
            "attempt_local": True,
        }
        if mode == "repair":
            assert skill_root is not None and skill_name is not None
            mounts.extend(
                [
                    "--bind",
                    str(skill_root.resolve()),
                    f"/workspace/.agents/skills/{skill_name}",
                ]
            )
            mount_summary["writable_skill"] = skill_name
    env = [
        "--setenv",
        "HOME",
        "/tmp",
        "--setenv",
        "CODEX_HOME",
        "/codex-home",
        "--setenv",
        "TMPDIR",
        "/tmp",
        "--setenv",
        "PATH",
        "/usr/local/bin:/usr/bin:/bin",
        "--setenv",
        "LANG",
        "C.UTF-8",
        "--setenv",
        "LC_ALL",
        "C.UTF-8",
    ]
    return [*mounts, *env], mount_summary


def _outer_argv(
    *,
    runtime: dict[str, Any],
    runtime_root: Path,
    mode: str,
    workspace_root: Path | None,
    output_root: Path | None,
    skill_root: Path | None,
    skill_name: str | None,
    codex_home: Path,
    codex_argv: Sequence[str],
    outer_binary: str | None = None,
    auth_store_path: Path | None = None,
) -> tuple[list[str], dict[str, Any]]:
    workspace, output, skill = _validate_workspace_mounts(
        mode=mode,
        workspace_root=workspace_root,
        output_root=output_root,
        skill_root=skill_root,
        skill_name=skill_name,
    )
    mounts, mount_summary = _mount_tree(
        runtime_root=runtime_root,
        mode=mode,
        workspace_root=workspace,
        output_root=output,
        skill_root=skill,
        skill_name=skill_name,
        codex_home=codex_home,
        auth_store_path=auth_store_path,
    )
    bwrap = runtime["bwrap_path"]
    codex = "/opt/codex-runtime/" + CODEX_RELATIVE_PATH.as_posix()
    executable = codex
    if outer_binary is not None:
        if (
            outer_binary != "/usr/bin/python3"
            or not codex_argv
            or codex_argv[0] != outer_binary
        ):
            raise CodexWsl2LauncherError("outer diagnostic binary is not allowed")
        executable = outer_binary
    prefix = [
        bwrap,
        "--unshare-user",
        "--unshare-pid",
        "--unshare-ipc",
        "--unshare-uts",
        "--die-with-parent",
        "--new-session",
        *mounts,
        "--chdir",
        "/workspace" if mode in {"agent", "repair"} else "/tmp",
    ]
    command = (
        list(codex_argv) if outer_binary is not None else [executable, *codex_argv]
    )
    result = [*prefix, "--", *command]
    effective = {
        "protocol": PROTOCOL,
        "mode": mode,
        "outer_argv_fingerprint": _fingerprint(result),
        "mounts": mount_summary,
        "outer_network": "inherited_for_codex_parent_model_api",
        "inner_network": "codex_sandbox_default_restricted",
        "inner_writable_roots": (
            [f"/workspace/.agents/skills/{skill_name}"]
            if mode == "repair" and skill_name is not None
            else []
        ),
        "inner_sandbox_argv": list(codex_argv) if outer_binary is None else None,
        "outer_diagnostic_argv_fingerprint": (
            _fingerprint(list(codex_argv)) if outer_binary is not None else None
        ),
        "outer_program": executable,
        "codex_path": codex,
        "codex_home_fingerprint": _fingerprint({"temporary_home": str(codex_home)}),
        "runtime": runtime,
    }
    return result, effective


def sandbox_smoke(
    *,
    mode: str,
    workspace_root: Path | None,
    output_root: Path | None,
    skill_root: Path | None = None,
    skill_name: str | None = None,
    runtime_root: Path | None = None,
    permission_profile: str | None = None,
) -> dict[str, Any]:
    """Run the pinned Codex sandbox without a prompt, credentials, or model API."""
    if mode not in {"agent", "judge", "repair"}:
        raise CodexWsl2LauncherError("sandbox smoke mode is invalid")
    expected_permission_profile = _permission_profile_for_mode(mode)
    if (
        permission_profile is not None
        and permission_profile != expected_permission_profile
    ):
        raise CodexWsl2LauncherError("sandbox smoke profile does not match its mode")
    permission_profile = expected_permission_profile
    if workspace_root is not None:
        escape = workspace_root / "synthetic-escape"
        if escape.exists() or escape.is_symlink():
            raise CodexWsl2LauncherError("synthetic symlink path already exists")
    _require_wsl2()
    runtime_root = runtime_root or runtime_root_from_environment()
    runtime = verify_runtime(runtime_root)
    host_namespaces = {
        name: os.readlink(f"/proc/self/ns/{name}")
        for name in ("user", "pid", "mnt", "net", "ipc", "uts")
    }
    home_parent = _private_temp_root()
    home = home_parent / f"{CODEX_HOME_PREFIX}{mode}-{uuid.uuid4().hex}"
    auth_source = home_parent / f"{CODEX_HOME_PREFIX}source-{uuid.uuid4().hex}"
    outside_root: Path | None = None
    other_home: Path | None = None
    unix_server: socket.socket | None = None
    fd_marker = "synthetic-fd-sentinel-" + uuid.uuid4().hex

    def cleanup_setup_failure() -> None:
        cleanup_errors: list[BaseException] = []
        if unix_server is not None:
            try:
                unix_server.close()
            except BaseException as exc:
                cleanup_errors.append(exc)
        for path in (auth_source, other_home, outside_root):
            if path is None:
                continue
            try:
                if path.is_symlink():
                    path.unlink()
                elif path.exists():
                    shutil.rmtree(path)
            except BaseException as exc:
                cleanup_errors.append(exc)
        if home.exists():
            try:
                cleanup_codex_home(
                    home,
                    allowed_parent=home_parent,
                    workspace_root=workspace_root,
                )
            except BaseException as exc:
                cleanup_errors.append(exc)
        if workspace_root is not None:
            escape = workspace_root / "synthetic-escape"
            if escape.is_symlink():
                try:
                    escape.unlink()
                except BaseException as exc:
                    cleanup_errors.append(exc)
        if cleanup_errors:
            raise CodexWsl2LauncherError(
                "synthetic isolation setup cleanup failed"
            ) from cleanup_errors[0]

    try:
        auth_source.mkdir(mode=0o700)
        auth_file = auth_source / "auth.json"
        auth_file.write_text("SYNTHETIC_AUTH_MARKER", encoding="utf-8")
        os.chmod(auth_file, 0o600)
        _prepare_codex_home(
            home,
            mode=mode,
            reasoning_effort="medium",
            auth=auth_file,
            skill_name=skill_name,
        )
        (home / "auth-alias.json").symlink_to("auth.json")
    except BaseException:
        cleanup_setup_failure()
        raise
    try:
        outside_root = Path(tempfile.mkdtemp(prefix="qa-wsl2-probe-outside-"))
    except BaseException:
        cleanup_setup_failure()
        raise
    outside_sentinel = outside_root / "evaluator-only.txt"
    other_home = home_parent / f"{CODEX_HOME_PREFIX}other-{uuid.uuid4().hex}"
    try:
        other_home.mkdir(mode=0o700)
        other_sentinel = other_home / "synthetic-other-attempt.txt"
        other_sentinel.write_text("other-attempt-sentinel", encoding="utf-8")
        other_auth = other_home / "auth.json"
        other_auth.write_text("SYNTHETIC_AUTH_MARKER", encoding="utf-8")
        os.chmod(other_home, 0o700)
        os.chmod(other_sentinel, 0o600)
        os.chmod(other_auth, 0o600)
        host_unix_socket = outside_root / "host-only.sock"
        outside_sentinel.write_text(fd_marker, encoding="utf-8")
        os.chmod(outside_root, 0o700)
        os.chmod(outside_sentinel, 0o600)
        unix_server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        unix_server.bind(str(host_unix_socket))
        unix_server.listen(1)
    except BaseException:
        cleanup_setup_failure()
        raise
    assert unix_server is not None
    assert other_home is not None
    assert outside_root is not None
    codex = "/opt/codex-runtime/" + CODEX_RELATIVE_PATH.as_posix()
    inner_script = r"""import errno,json,os,socket,stat,subprocess,sys,threading
mode,outer_ns_json,host_sentinel,fd_marker,evaluator_root,other_home,unix_socket_path,auth_store_path,auth_host_path,other_auth_path = sys.argv[1:11]
outer_ns=json.loads(outer_ns_json)
r={"mode":mode,"pid":os.getpid(),"procfs":os.path.ismount("/proc"),"namespaces":{},"nested_namespaces":{},"paths":{},"fd_marker_absent":True,"authentication_store_read_denied":None,"authentication_store_symlink_read_denied":None,"authentication_store_proc_root_read_denied":None,"authentication_store_proc1_root_read_denied":None,"authentication_store_host_path_hidden":None,"other_attempt_auth_store_hidden":None,"authentication_marker_absent_from_environment":None,"authentication_marker_absent_from_process_fds":None,"source_write_denied":None,"output_write_allowed":None,"repair_skill_write_allowed":None,"network":{}}
def read_denied(path):
 try:
  with open(path,"rb") as auth_store: auth_store.read(1)
  return False
 except OSError:
  return True
r["authentication_store_read_denied"]=read_denied(auth_store_path)
r["authentication_store_symlink_read_denied"]=read_denied("/codex-home/auth-alias.json")
r["authentication_store_proc_root_read_denied"]=read_denied("/proc/self/root/codex-home/auth.json")
r["authentication_store_proc1_root_read_denied"]=read_denied("/proc/1/root/codex-home/auth.json")
r["authentication_store_host_path_hidden"]=read_denied(auth_host_path)
r["other_attempt_auth_store_hidden"]=read_denied(other_auth_path)
marker=b"SYNTHETIC_AUTH_MARKER"
environment_marker_visible=False
try:
 for process in os.listdir("/proc"):
  if not process.isdigit(): continue
  try:
   if marker in open("/proc/"+process+"/environ","rb").read(): environment_marker_visible=True
  except OSError: pass
except OSError: pass
r["authentication_marker_absent_from_environment"]=not environment_marker_visible
auth_targets={auth_store_path,"/codex-home/auth-alias.json",auth_host_path,auth_host_path+" (deleted)",other_auth_path,other_auth_path+" (deleted)"}
auth_fd_visible=False
try:
 for process in os.listdir("/proc"):
  if not process.isdigit(): continue
  try: descriptors=os.listdir("/proc/"+process+"/fd")
  except OSError: continue
  for descriptor in descriptors:
   try:
    if os.readlink("/proc/"+process+"/fd/"+descriptor) in auth_targets: auth_fd_visible=True
   except OSError: pass
except OSError: pass
r["authentication_marker_absent_from_process_fds"]=not auth_fd_visible
for name in ("user","pid","mnt","net","ipc","uts"):
 try:r["namespaces"][name]=os.readlink("/proc/self/ns/"+name)
 except OSError:r["namespaces"][name]=None
 r["nested_namespaces"][name]=r["namespaces"].get(name)!=outer_ns.get(name)
for path in ("/home","/root","/mnt","/run/docker.sock","/var/run/docker.sock"):
 r["paths"][path]=not os.path.exists(path)
try:open(other_home+"/synthetic-other-attempt.txt","rb").read(); r["paths"]["other_attempt_home_absent"]=False
except OSError:r["paths"]["other_attempt_home_absent"]=True
try:open(host_sentinel,"rb").read(); r["paths"]["evaluator_sentinel_absent"]=False
except OSError:r["paths"]["evaluator_sentinel_absent"]=True
try:os.stat(evaluator_root); r["paths"]["evaluator_checkout_absent"]=False
except OSError:r["paths"]["evaluator_checkout_absent"]=True
r["paths"][unix_socket_path]=not os.path.exists(unix_socket_path)
try:os.symlink(host_sentinel,"/workspace/synthetic-escape"); open("/workspace/synthetic-escape","rb").read(); r["paths"]["symlink_escape_denied"]=False
except OSError:r["paths"]["symlink_escape_denied"]=True
if os.path.isdir("/proc/self/fd"):
 for item in os.listdir("/proc/self/fd"):
  try:
   fd_path="/proc/self/fd/"+item
   if stat.S_ISREG(os.stat(fd_path).st_mode) and fd_marker.encode() in open(fd_path,"rb").read(4096):r["fd_marker_absent"]=False
  except OSError:pass
if os.path.isdir("/dev/fd"):
 for item in os.listdir("/dev/fd"):
  try:
   fd_path="/dev/fd/"+item
   if stat.S_ISREG(os.stat(fd_path).st_mode) and fd_marker.encode() in open(fd_path,"rb").read(4096):r["fd_marker_absent"]=False
  except OSError:pass
if mode in ("agent","repair"):
 try:open("/workspace/protected.txt","w").write("changed"); r["source_write_denied"]=False
 except OSError:r["source_write_denied"]=True
 try:open("/workspace/.qa-eval-output/probe-output.txt","w").write("allowed"); r["output_write_allowed"]=True
 except OSError:r["output_write_allowed"]=False
 if mode=="repair":
  try:open("/workspace/.agents/skills/synthetic-skill/SKILL.md","a").write("\nsynthetic repair\n"); r["repair_skill_write_allowed"]=True
  except OSError:r["repair_skill_write_allowed"]=False
def probe_socket(family,kind,host=None):
 try:
  s=socket.socket(family,kind); s.settimeout(1)
  if host is not None:
   try:s.connect(host); result={"socket_created":True,"connect":"connected"}
   except OSError as e:result={"socket_created":True,"connect_errno":e.errno}
  else:result={"socket_created":True}
  s.close(); return result
 except OSError as e:return {"socket_created":False,"errno":e.errno}
r["network"]["tcp_socket"]=probe_socket(socket.AF_INET,socket.SOCK_STREAM,("203.0.113.1",443))
r["network"]["localhost"]=probe_socket(socket.AF_INET,socket.SOCK_STREAM,("127.0.0.1",9))
r["network"]["af_unix"]=probe_socket(socket.AF_UNIX,socket.SOCK_STREAM,unix_socket_path)
dns_result={}
def resolve_dns():
 try:socket.getaddrinfo("api.openai.com",443); dns_result["value"]={"resolved":True}
 except OSError as e:dns_result["value"]={"resolved":False,"errno":getattr(e,"errno",None)}
dns_thread=threading.Thread(target=resolve_dns,daemon=True); dns_thread.start(); dns_thread.join(3)
r["network"]["dns"]=dns_result.get("value",{"resolved":False,"timed_out":True})
r["network"]["outer_net_namespace_changed"]=r["nested_namespaces"].get("net") is True
r["network"]["wsl_interop_absent"]=not os.environ.get("WSL_INTEROP") and not os.path.exists("/mnt/c/Windows/System32/cmd.exe")
try:
 subprocess.run(["/mnt/c/Windows/System32/cmd.exe","/c","ver"],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=2,check=False,close_fds=True)
 r["network"]["windows_command_denied"]=False
except OSError:r["network"]["windows_command_denied"]=True
print(json.dumps(r,separators=(",",":")))
""".replace("synthetic-skill", skill_name or "synthetic-skill")
    outer_script = r"""import json,os,subprocess,sys
codex,host_ns_json,inner_script,host_sentinel,fd_marker,mode,evaluator_root,other_home,unix_socket_path,auth_host_path,other_auth_path=sys.argv[1:12]
host=json.loads(host_ns_json)
outer={"pid":os.getpid(),"uid":os.getuid(),"gid":os.getgid(),"uid_map":open("/proc/self/uid_map").read().strip(),"gid_map":open("/proc/self/gid_map").read().strip(),"procfs":os.path.ismount("/proc"),"namespaces":{},"paths":{}}
try:
 with open("/codex-home/auth.json","rb") as auth_store: auth_store.read(1)
 outer["codex_home_readable_by_outer_process"]=True
except OSError:outer["codex_home_readable_by_outer_process"]=False
for name in ("user","pid","mnt","net","ipc","uts"):
 try:outer["namespaces"][name]=os.readlink("/proc/self/ns/"+name)
 except OSError:outer["namespaces"][name]=None
for path in ("/home","/root","/mnt","/run/docker.sock","/var/run/docker.sock"):
 outer["paths"][path]=not os.path.exists(path)
try:open(other_home+"/synthetic-other-attempt.txt","rb").read(); outer["paths"]["other_attempt_home_absent"]=False
except OSError:outer["paths"]["other_attempt_home_absent"]=True
outer["paths"][unix_socket_path]=not os.path.exists(unix_socket_path)
try:open(host_sentinel,"rb").read(); outer["paths"]["evaluator_sentinel_absent"]=False
except OSError:outer["paths"]["evaluator_sentinel_absent"]=True
try:os.stat(evaluator_root); outer["paths"]["evaluator_checkout_absent"]=False
except OSError:outer["paths"]["evaluator_checkout_absent"]=True
outer["network_parent_in_host_namespace"]=outer["namespaces"].get("net")==host.get("net")
profile_args=["--permission-profile",{"agent":"qa_eval_agent","judge":"qa_eval_judge","repair":"qa_eval_repair"}[mode],"--config",'default_permissions="'+{"agent":"qa_eval_agent","judge":"qa_eval_judge","repair":"qa_eval_repair"}[mode]+'"']
smoke=subprocess.run([codex,"sandbox","--permission-profile",":read-only","--","/bin/echo","sandbox-ok"],stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=30,check=False,close_fds=True)
invalid_profile=subprocess.run([codex,"sandbox","--permission-profile","qa_eval_unapproved","--","/bin/true"],stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=30,check=False,close_fds=True)
probe=subprocess.run([codex,"sandbox",*profile_args,"--","/usr/bin/python3","-I","-S","-c",inner_script,mode,json.dumps(outer["namespaces"],separators=(",",":")),host_sentinel,fd_marker,evaluator_root,other_home,unix_socket_path,"/codex-home/auth.json",auth_host_path,other_auth_path],stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=30,check=False,close_fds=True)
try:inner=json.loads(probe.stdout.decode("utf-8",errors="strict").splitlines()[-1])
except (UnicodeDecodeError,ValueError,IndexError):inner={"parse_error":True}
result={"smoke_exit_code":smoke.returncode,"smoke_stdout":smoke.stdout.decode("utf-8",errors="replace").strip()[:1000],"smoke_stderr":smoke.stderr.decode("utf-8",errors="replace")[:1000],"invalid_profile_exit_code":invalid_profile.returncode,"invalid_profile_rejected":invalid_profile.returncode != 0 and b"undefined profile" in invalid_profile.stderr,"probe_exit_code":probe.returncode,"probe_stdout":probe.stdout.decode("utf-8",errors="replace")[-4000:],"probe_stderr":probe.stderr.decode("utf-8",errors="replace")[:1000],"outer":outer,"inner":inner}
print(json.dumps(result,separators=(",",":")))
"""
    host_ns_json = json.dumps(host_namespaces, separators=(",", ":"))
    outer_argv = [
        "/usr/bin/python3",
        "-I",
        "-S",
        "-c",
        outer_script,
        codex,
        host_ns_json,
        inner_script,
        str(outside_sentinel),
        fd_marker,
        mode,
        str(REPO_ROOT),
        str(other_home),
        str(host_unix_socket),
        str(auth_file),
        str(other_home / "auth.json"),
    ]
    try:
        command, effective = _outer_argv(
            runtime=runtime,
            runtime_root=runtime_root.resolve(),
            mode=mode,
            workspace_root=workspace_root,
            output_root=output_root,
            skill_root=skill_root,
            skill_name=skill_name,
            codex_home=home,
            codex_argv=outer_argv,
            outer_binary="/usr/bin/python3",
            auth_store_path=auth_file,
        )
    except BaseException:
        cleanup_codex_home(
            home,
            allowed_parent=home_parent,
            workspace_root=workspace_root,
        )
        shutil.rmtree(auth_source, ignore_errors=True)
        unix_server.close()
        shutil.rmtree(other_home, ignore_errors=True)
        shutil.rmtree(outside_root, ignore_errors=True)
        if workspace_root is not None:
            escape = workspace_root / "synthetic-escape"
            if escape.is_symlink():
                escape.unlink()
        raise
    env = {
        "PATH": "/usr/local/bin:/usr/bin:/bin",
        "HOME": "/tmp",
        "CODEX_HOME": "/codex-home",
        "TMPDIR": "/tmp",
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
    }
    try:
        with outside_sentinel.open("rb") as sentinel_fd:
            os.set_inheritable(sentinel_fd.fileno(), True)
            completed = subprocess.run(
                command,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                timeout=60,
                check=False,
                shell=False,
                close_fds=True,
            )
        try:
            result = json.loads(
                completed.stdout.decode("utf-8", errors="strict").splitlines()[-1]
            )
        except (UnicodeDecodeError, json.JSONDecodeError, IndexError):
            result = {"outer": {}, "inner": {}, "parse_error": True}
        outer = result.get("outer", {})
        inner = result.get("inner", {})
        namespace_checks = {
            name: outer.get("namespaces", {}).get(name) != host_namespaces.get(name)
            for name in ("user", "pid", "mnt", "ipc", "uts")
        }
        namespace_checks["outer_net_inherited"] = (
            outer.get("network_parent_in_host_namespace") is True
        )
        namespace_checks["inner_namespaces_unshared"] = all(
            inner.get("nested_namespaces", {}).get(name) is True
            for name in ("user", "pid", "mnt", "net", "ipc")
        )
        namespace_checks["inner_uts_matches_outer"] = inner.get("namespaces", {}).get(
            "uts"
        ) == outer.get("namespaces", {}).get("uts")
        source_expected = mode == "judge" or inner.get("source_write_denied") is True
        output_expected = mode == "judge" or inner.get("output_write_allowed") is True
        repair_expected = (
            mode != "repair" or inner.get("repair_skill_write_allowed") is True
        )
        network = inner.get("network", {})
        tcp = network.get("tcp_socket", {})
        local = network.get("localhost", {})
        unix = network.get("af_unix", {})
        checks = {
            "inner_smoke": result.get("smoke_exit_code") == 0
            and result.get("smoke_stdout") == "sandbox-ok",
            "unknown_permission_profile_rejected": result.get(
                "invalid_profile_rejected"
            )
            is True,
            "outer_procfs": outer.get("procfs") is True,
            "inner_procfs": inner.get("procfs") is True,
            "outer_host_paths_hidden": all(
                outer.get("paths", {}).get(path) is True
                for path in (
                    "/home",
                    "/root",
                    "/mnt",
                    "/run/docker.sock",
                    "/var/run/docker.sock",
                )
            )
            and outer.get("paths", {}).get("other_attempt_home_absent") is True,
            "inner_host_paths_hidden": all(
                inner.get("paths", {}).get(path) is True
                for path in (
                    "/home",
                    "/root",
                    "/mnt",
                    "/run/docker.sock",
                    "/var/run/docker.sock",
                )
            )
            and inner.get("paths", {}).get("other_attempt_home_absent") is True,
            "evaluator_sentinel_read_denied": outer.get("paths", {}).get(
                "evaluator_sentinel_absent"
            )
            is True
            and inner.get("paths", {}).get("evaluator_sentinel_absent") is True,
            "evaluator_checkout_unmounted": outer.get("paths", {}).get(
                "evaluator_checkout_absent"
            )
            is True
            and inner.get("paths", {}).get("evaluator_checkout_absent") is True,
            "authentication_store_read_denied": inner.get(
                "authentication_store_read_denied"
            )
            is True
            and outer.get("codex_home_readable_by_outer_process") is True,
            "authentication_store_aliases_denied": inner.get(
                "authentication_store_symlink_read_denied"
            )
            is True
            and inner.get("authentication_store_proc_root_read_denied") is True
            and inner.get("authentication_store_proc1_root_read_denied") is True,
            "authentication_store_host_path_hidden": inner.get(
                "authentication_store_host_path_hidden"
            )
            is True,
            "other_attempt_auth_store_hidden": inner.get(
                "other_attempt_auth_store_hidden"
            )
            is True,
            "authentication_marker_absent_from_environment": inner.get(
                "authentication_marker_absent_from_environment"
            )
            is True,
            "authentication_marker_absent_from_process_fds": inner.get(
                "authentication_marker_absent_from_process_fds"
            )
            is True,
            "fd_noninheritance": inner.get("fd_marker_absent") is True,
            "symlink_escape_denied": mode == "judge"
            or inner.get("paths", {}).get("symlink_escape_denied") is True,
            "source_write_denied": source_expected,
            "output_write_allowed": output_expected,
            "repair_skill_write_allowed": repair_expected,
            "nested_namespaces": all(namespace_checks.values()),
            "inner_tcp_blocked": tcp.get("connect") != "connected",
            "inner_localhost_blocked": local.get("connect") != "connected",
            "inner_af_unix_blocked": unix.get("connect") != "connected",
            "unmounted_unix_path_hidden": outer.get("paths", {}).get(
                str(host_unix_socket)
            )
            is True
            and inner.get("paths", {}).get(str(host_unix_socket)) is True,
            "inner_dns_blocked": network.get("dns", {}).get("resolved") is False,
            "wsl_interop_blocked": network.get("wsl_interop_absent") is True
            and network.get("windows_command_denied") is True,
        }
        return {
            "protocol": PROTOCOL,
            "mode": mode,
            "permission_profile": permission_profile,
            "exit_code": completed.returncode,
            "effective": effective,
            "outer": outer,
            "inner": inner,
            "diagnostics": {
                "smoke_exit_code": result.get("smoke_exit_code"),
                "smoke_stdout": _sanitize(str(result.get("smoke_stdout", "")))[:1000],
                "smoke_stderr": _sanitize(str(result.get("smoke_stderr", "")))[:1000],
                "probe_exit_code": result.get("probe_exit_code"),
                "probe_stdout": _sanitize(str(result.get("probe_stdout", "")))[-4000:],
                "probe_stderr": _sanitize(str(result.get("probe_stderr", "")))[:1000],
            },
            "checks": checks,
            "status": "verified"
            if completed.returncode == 0 and all(checks.values())
            else "unverified",
            "stderr": _sanitize(completed.stderr.decode("utf-8", errors="replace"))[
                :4096
            ],
        }
    except (OSError, subprocess.SubprocessError) as exc:
        return {
            "protocol": PROTOCOL,
            "mode": mode,
            "permission_profile": permission_profile,
            "status": "unverified",
            "error": type(exc).__name__,
            "effective": effective,
        }
    finally:
        try:
            cleanup_codex_home(
                home,
                allowed_parent=home_parent,
                workspace_root=workspace_root,
            )
        finally:
            shutil.rmtree(auth_source, ignore_errors=True)
            unix_server.close()
            shutil.rmtree(other_home, ignore_errors=True)
            shutil.rmtree(outside_root, ignore_errors=True)
            if workspace_root is not None:
                escape = workspace_root / "synthetic-escape"
                if escape.is_symlink():
                    escape.unlink()


def timeout_cleanup_smoke(
    *,
    workspace_root: Path,
    output_root: Path,
    runtime_root: Path | None = None,
    timeout_seconds: int = 2,
) -> dict[str, Any]:
    """Exercise the regular process-group timeout and Codex-home cleanup path."""
    _require_wsl2()
    if timeout_seconds < 1 or timeout_seconds > 10:
        raise CodexWsl2LauncherError(
            "timeout smoke duration is outside the allowed range"
        )
    runtime_root = runtime_root or runtime_root_from_environment()
    runtime = verify_runtime(runtime_root)
    home_parent = _private_temp_root()
    home = home_parent / f"{CODEX_HOME_PREFIX}timeout-{uuid.uuid4().hex}"
    final_name = f".codex-final-{uuid.uuid4().hex}.md"
    final_path = f"/workspace/.qa-eval-output/{final_name}"
    _prepare_codex_home(
        home,
        mode="agent",
        reasoning_effort="medium",
        auth=None,
    )
    cleanup = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--cleanup-home",
        str(home),
        "--allowed-parent",
        str(home_parent),
        "--workspace-root",
        str(workspace_root),
        "--cleanup-final-messages",
        str(output_root),
    ]
    try:
        command, effective = _outer_argv(
            runtime=runtime,
            runtime_root=runtime_root.resolve(),
            mode="agent",
            workspace_root=workspace_root,
            output_root=output_root,
            skill_root=None,
            skill_name=None,
            codex_home=home,
            codex_argv=[
                "sandbox",
                "--permission-profile",
                ":workspace",
                "--",
                "/bin/sh",
                "-c",
                f"printf synthetic-final-message > {final_path}; exec /bin/sleep 30",
            ],
        )
        from scripts.skills.evals.agent.executor import run_command

        execution = run_command(
            command,
            input_text="",
            cwd=workspace_root,
            timeout_seconds=timeout_seconds,
            env={
                "PATH": "/usr/local/bin:/usr/bin:/bin",
                "HOME": "/tmp",
                "CODEX_HOME": "/codex-home",
                "TMPDIR": "/tmp",
                "LANG": "C.UTF-8",
                "LC_ALL": "C.UTF-8",
                "TERM": "dumb",
            },
            inherit_environment=False,
            timeout_cleanup_argv=cleanup,
        )
        home_removed = not home.exists()
        scratch_removed = not Path(str(home) + ".git").exists()
        workspace_git_removed = not (workspace_root / ".git").exists()
        final_message_removed = not (output_root / final_name).exists()
        checks = {
            "timed_out": execution.timed_out,
            "cleanup_succeeded": execution.cleanup_status == "succeeded",
            "codex_home_removed": home_removed,
            "git_scratch_removed": scratch_removed,
            "workspace_git_mountpoint_removed": workspace_git_removed,
            "final_message_removed": final_message_removed,
        }
        return {
            "protocol": PROTOCOL,
            "status": "verified" if all(checks.values()) else "unverified",
            "exit_code": execution.exit_code,
            "duration_seconds": execution.duration_seconds,
            "cleanup_status": execution.cleanup_status,
            "checks": checks,
            "effective": effective,
        }
    finally:
        cleanup_codex_home(
            home,
            allowed_parent=home_parent,
            workspace_root=workspace_root,
        )


def _fingerprint(value: Any) -> str:
    encoded = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return "sha256:" + hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _windows_mount_contains(path: Path) -> bool:
    absolute = Path(os.path.abspath(path))
    if absolute == Path("/mnt") or Path("/mnt") in absolute.parents:
        return True
    try:
        mountinfo = Path("/proc/self/mountinfo").read_text(encoding="utf-8")
    except OSError:
        return False
    for line in mountinfo.splitlines():
        try:
            before, after = line.split(" - ", 1)
            fields = before.split()
            mountpoint = Path(
                re.sub(
                    r"\\([0-7]{3})",
                    lambda match: chr(int(match.group(1), 8)),
                    fields[4],
                )
            )
            filesystem, source, *options = after.split()
        except (IndexError, ValueError):
            continue
        is_windows_mount = filesystem.lower() == "drvfs" or (
            filesystem.lower() == "9p"
            and (
                "drvfs" in " ".join(options).lower()
                or re.match(r"^[a-z]:\\", source, re.I)
            )
        )
        if is_windows_mount and (
            absolute == mountpoint or mountpoint in absolute.parents
        ):
            return True
    return False


def _codex_login_status(runtime: dict[str, Any], source_home: Path) -> str:
    version = str(runtime.get("codex_version", ""))
    if not re.search(r"\b0\.163\.0\b", version):
        return "cli_version_mismatch"
    codex_path = runtime.get("codex_path")
    if not isinstance(codex_path, str) or not codex_path:
        return "check_failed"
    environment = {
        "PATH": "/usr/local/bin:/usr/bin:/bin",
        "HOME": "/tmp",
        "CODEX_HOME": str(source_home),
        "TMPDIR": "/tmp",
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
    }
    try:
        result = subprocess.run(
            [codex_path, "login", "status"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=environment,
            timeout=AUTH_STATUS_TIMEOUT_SECONDS,
            check=False,
            shell=False,
            close_fds=True,
        )
    except (OSError, subprocess.SubprocessError):
        return "check_failed"
    output = (result.stdout + result.stderr).decode("utf-8", errors="replace")
    markers = [
        method
        for method, phrase in (
            ("chatgpt_login", "Logged in using ChatGPT"),
            ("api_key", "Logged in using an API key"),
            ("not_logged_in", "Not logged in"),
        )
        if phrase in output
    ]
    if len(markers) != 1:
        return "unknown" if result.returncode == 0 else "check_failed"
    if markers[0] == "chatgpt_login" and result.returncode == 0:
        return "chatgpt_login"
    if markers[0] == "chatgpt_login":
        return "check_failed"
    return markers[0]


def _auth_material(runtime: dict[str, Any]) -> tuple[Path | None, str]:
    configured_home = os.environ.get("CODEX_HOME")
    if (
        _is_wsl2()
        and configured_home
        and re.match(r"^[a-z]:[\\/]", configured_home, re.I)
    ):
        return None, "unsupported_auth_store"
    source_home = (
        Path(configured_home).expanduser()
        if configured_home
        else Path.home() / ".codex"
    )
    try:
        source_home = _reject_symlink_components(source_home, allow_leaf=True)
    except CodexWsl2LauncherError:
        return None, "invalid_auth_store"
    if (
        _is_wsl2() and _windows_mount_contains(source_home)
    ) or source_home.is_relative_to(REPO_ROOT.resolve()):
        return None, "unsupported_auth_store"
    if source_home.exists() and not source_home.is_dir():
        return None, "invalid_auth_store"
    auth = source_home / "auth.json"
    if auth.exists() or auth.is_symlink():
        try:
            _reject_symlink_components(auth)
        except CodexWsl2LauncherError:
            return None, "invalid_auth_file"
        if not _regular_file(auth) or auth.stat().st_size > 1_000_000:
            return None, "invalid_auth_file"
    auth_status = _codex_login_status(runtime, source_home)
    if auth_status != "chatgpt_login":
        return None, auth_status
    if not _regular_file(auth):
        return None, "unsupported_auth_store"
    return auth, "chatgpt_login"


def _prepare_codex_home(
    path: Path,
    *,
    mode: str,
    reasoning_effort: str,
    auth: Path | None,
    skill_name: str | None = None,
) -> None:
    parent = _reject_symlink_components(path.parent)
    if not parent.is_dir() or not os.access(parent, os.W_OK):
        raise CodexWsl2LauncherError("Codex home parent must be a writable directory")
    if (
        not path.name.startswith(CODEX_HOME_PREFIX)
        or path.exists()
        or path.is_symlink()
    ):
        raise CodexWsl2LauncherError("Codex home path is invalid or already exists")
    if mode == "repair":
        if skill_name is None or not _SAFE_NAME_RE.fullmatch(skill_name):
            raise CodexWsl2LauncherError("repair Codex home requires one fixed Skill")
    elif skill_name is not None:
        raise CodexWsl2LauncherError("only Repair may add a writable Skill root")
    permission_profile = _permission_profile_for_mode(mode)
    path.mkdir(mode=0o700)
    try:
        os.chmod(path, 0o700)
        config = (
            'approval_policy = "never"\n'
            'cli_auth_credentials_store = "file"\n'
            f"default_permissions = {json.dumps(permission_profile)}\n"
            'web_search = "disabled"\n'
            f"model_reasoning_effort = {json.dumps(reasoning_effort)}\n"
            f"[permissions.{permission_profile}]\n"
            f'extends = "{":read-only" if mode == "judge" else ":workspace"}"\n'
            f"[permissions.{permission_profile}.network]\n"
            "enabled = false\n"
            f"[permissions.{permission_profile}.filesystem]\n"
            '"/codex-home/auth.json" = "deny"\n'
            + (
                "[permissions.qa_eval_repair.workspace_roots]\n"
                f'"/workspace/.agents/skills/{skill_name}" = true\n'
                if mode == "repair"
                else ""
            )
            + "[features]\n"
            + f"shell_tool = {'false' if mode == 'judge' else 'true'}\n"
            + "code_mode = false\n"
        )
        config_path = path / "config.toml"
        config_path.write_text(config, encoding="utf-8")
        os.chmod(config_path, 0o600)
        if auth is not None:
            if not _regular_file(auth) or auth.is_symlink():
                raise CodexWsl2LauncherError("persistent Codex auth file is invalid")
            mountpoint = path / "auth.json"
            mountpoint.touch(mode=0o600, exist_ok=False)
            os.chmod(mountpoint, 0o600)
    except BaseException:
        shutil.rmtree(path, ignore_errors=True)
        raise


def cleanup_codex_home(
    path: Path,
    *,
    allowed_parent: Path,
    workspace_root: Path | None = None,
) -> None:
    absolute = _reject_symlink_components(path, allow_leaf=True)
    parent = _directory(allowed_parent)
    if absolute.parent != parent or not absolute.name.startswith(CODEX_HOME_PREFIX):
        raise CodexWsl2LauncherError("refusing to clean an untrusted Codex home path")
    if absolute.is_symlink():
        absolute.unlink()
    elif absolute.exists():
        if not stat.S_ISDIR(absolute.lstat().st_mode):
            raise CodexWsl2LauncherError("Codex home cleanup target is not a directory")
        shutil.rmtree(absolute)
    for suffix in (".git", ".workspace-codex"):
        scratch = Path(str(absolute) + suffix)
        if scratch.is_symlink():
            scratch.unlink()
        elif scratch.exists():
            if not stat.S_ISDIR(scratch.lstat().st_mode):
                raise CodexWsl2LauncherError(
                    "Codex scratch cleanup target is not a directory"
                )
            shutil.rmtree(scratch)
    if workspace_root is not None:
        workspace = _directory(workspace_root)
        for name in (".git", ".codex"):
            mountpoint = workspace / name
            if mountpoint.is_symlink():
                raise CodexWsl2LauncherError(
                    f"refusing to clean a symlinked workspace {name}"
                )
            if mountpoint.exists():
                if not stat.S_ISDIR(mountpoint.lstat().st_mode):
                    raise CodexWsl2LauncherError(
                        f"workspace {name} cleanup target is not a directory"
                    )
                if any(mountpoint.iterdir()):
                    raise CodexWsl2LauncherError(
                        f"workspace {name} mountpoint is unexpectedly non-empty"
                    )
                mountpoint.rmdir()


def cleanup_argv(execution_argv: Sequence[str]) -> list[str] | None:
    try:
        index = execution_argv.index("--codex-home")
        home = execution_argv[index + 1]
    except (ValueError, IndexError):
        return None
    command = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--cleanup-home",
        str(Path(home).resolve()),
        "--allowed-parent",
        str(Path(home).resolve().parent),
    ]
    try:
        index = execution_argv.index("--workspace-root")
        workspace = execution_argv[index + 1]
    except (ValueError, IndexError):
        workspace = None
    if workspace is not None:
        command.extend(["--workspace-root", workspace])
    try:
        mode_index = execution_argv.index("--mode")
        mode = execution_argv[mode_index + 1]
        output_index = execution_argv.index("--output-root")
        output_root = execution_argv[output_index + 1]
    except (ValueError, IndexError):
        mode = None
        output_root = None
    if mode in {"agent", "repair"} and output_root is not None:
        command.extend(["--cleanup-final-messages", output_root])
    return command


def _codex_exec_argv(
    *,
    mode: str,
    model: str,
    reasoning_effort: str,
    sandbox_policy: str,
    output_message_path: str,
) -> list[str]:
    expected_sandbox_policy = "read-only" if mode == "judge" else "workspace-write"
    if (
        mode not in _PERMISSION_PROFILE_BY_MODE
        or sandbox_policy != expected_sandbox_policy
    ):
        raise CodexWsl2LauncherError("Codex sandbox policy does not match its mode")
    command = [
        "--no-daemon",
        "--strict-config",
        "--ask-for-approval",
        "never",
        "exec",
        "--json",
        "--model",
        model,
        "--config",
        f"default_permissions={json.dumps(_permission_profile_for_mode(mode))}",
        "--config",
        f"model_reasoning_effort={json.dumps(reasoning_effort)}",
        "--config",
        'web_search="disabled"',
    ]
    if mode == "judge":
        command.extend(["--cd", "/tmp", "--skip-git-repo-check"])
    else:
        command.extend(["--cd", "/workspace", "--skip-git-repo-check"])
    command.extend(["--output-last-message", output_message_path, "-"])
    return command


def codex_exec_argv_fingerprint(argv: Sequence[str], *, mode: str) -> str:
    """Fingerprint the fixed exec argv while normalizing its attempt-local output path."""
    if mode not in {"agent", "repair", "judge"}:
        raise CodexWsl2LauncherError("Codex exec mode is invalid")
    command = list(argv)
    expected_cwd = "/tmp" if mode == "judge" else "/workspace"
    output_root = "/tmp" if mode == "judge" else "/workspace/.qa-eval-output"
    if command.count("--cd") != 1 or command.count("--output-last-message") != 1:
        raise CodexWsl2LauncherError("Codex exec argv is missing fixed path options")
    if command[command.index("--cd") + 1] != expected_cwd:
        raise CodexWsl2LauncherError("Codex exec cwd does not match its mode")
    output_index = command.index("--output-last-message") + 1
    if PurePosixPath(command[output_index]).parent.as_posix() != output_root:
        raise CodexWsl2LauncherError("Codex exec output path does not match its mode")
    command[output_index] = f"{output_root}/<attempt-final-message>"
    return _fingerprint(command)


def expected_codex_exec_argv_fingerprint(
    *, mode: str, model: str, reasoning_effort: str, sandbox_policy: str
) -> str:
    """Return the normalized argv fingerprint production launch will use for a profile."""
    output_root = "/tmp" if mode == "judge" else "/workspace/.qa-eval-output"
    argv = _codex_exec_argv(
        mode=mode,
        model=model,
        reasoning_effort=reasoning_effort,
        sandbox_policy=sandbox_policy,
        output_message_path=f"{output_root}/.codex-final-template.md",
    )
    return codex_exec_argv_fingerprint(argv, mode=mode)


def _launch_locked(
    *,
    mode: str,
    output_root: Path,
    prompt: str,
    observations_path: Path,
    model: str,
    reasoning_effort: str,
    sandbox_policy: str,
    workspace_root: Path | None,
    skill_root: Path | None = None,
    skill_name: str | None = None,
    codex_home: Path,
    runtime_root: Path | None = None,
    auth_execution: AuthExecutionPaths | None = None,
) -> int:
    _require_wsl2()
    if mode not in {"agent", "judge", "repair"}:
        raise CodexWsl2LauncherError("execution mode is invalid")
    if not model.strip() or not reasoning_effort.strip():
        raise CodexWsl2LauncherError("model and reasoning effort must be fixed")
    if mode == "judge" and sandbox_policy != "read-only":
        raise CodexWsl2LauncherError("Judge sandbox must be read-only")
    if mode != "judge" and sandbox_policy != "workspace-write":
        raise CodexWsl2LauncherError("Agent and Repair sandbox must be workspace-write")
    if output_root.is_symlink() or not output_root.is_dir():
        raise CodexWsl2LauncherError("output root must be a regular directory")
    if observations_path.is_symlink():
        raise CodexWsl2LauncherError("observations path may not be a symlink")
    blockers = _authentication_execution_blockers()
    if blockers:
        error = (
            "authentication_shell_visible_risk"
            if AUTHENTICATION_SHELL_VISIBLE_RISK
            else "authentication_execution_safety_unresolved"
        )
        _write_observations(
            observations_path,
            {
                "protocol": PROTOCOL,
                "status": "execution_error",
                "error": error,
                "authentication_method": "not_checked",
                "authentication_check_status": "blocked",
                "codex_cli_version": "0.163.0",
                "authentication_shell_visible_risk": AUTHENTICATION_SHELL_VISIBLE_RISK,
                "authentication_refresh_persistence_unresolved": (
                    AUTHENTICATION_REFRESH_PERSISTENCE_UNRESOLVED
                ),
                "authentication_process_concurrency_unresolved": (
                    AUTHENTICATION_PROCESS_CONCURRENCY_UNRESOLVED
                ),
                "authentication_execution_blockers": blockers,
                "mode": mode,
            },
        )
        return 2
    if auth_execution is None:
        raise AuthExecutionBlocked("authentication_execution_lease_required")
    runtime_root = runtime_root or runtime_root_from_environment()
    runtime = verify_runtime(runtime_root)
    auth_path, auth_mode = _auth_material(runtime)
    if auth_mode != "chatgpt_login":
        _write_observations(
            observations_path,
            {
                "protocol": PROTOCOL,
                "status": "execution_error",
                "error": "authentication_rejected",
                "authentication_method": auth_mode,
                "authentication_check_status": "rejected",
                "codex_cli_version": "0.163.0",
                "mode": mode,
            },
        )
        return 2
    if auth_path != auth_execution.auth_file:
        raise AuthExecutionBlocked("evaluation_auth_store_mismatch")
    home_path = codex_home
    _prepare_codex_home(
        home_path,
        mode=mode,
        reasoning_effort=reasoning_effort,
        auth=auth_path,
        skill_name=skill_name,
    )
    final_name = f".codex-final-{uuid.uuid4().hex}.md"
    output_message = (
        "/tmp/" + final_name
        if mode == "judge"
        else "/workspace/.qa-eval-output/" + final_name
    )
    codex_argv = _codex_exec_argv(
        mode=mode,
        model=model,
        reasoning_effort=reasoning_effort,
        sandbox_policy=sandbox_policy,
        output_message_path=output_message,
    )
    try:
        command, effective = _outer_argv(
            runtime=runtime,
            runtime_root=runtime_root.resolve(),
            mode=mode,
            workspace_root=workspace_root,
            output_root=None if mode == "judge" else output_root,
            skill_root=skill_root,
            skill_name=skill_name,
            codex_home=home_path,
            codex_argv=codex_argv,
            auth_store_path=auth_path,
        )
    except BaseException:
        cleanup_codex_home(
            home_path,
            allowed_parent=home_path.parent,
            workspace_root=workspace_root,
        )
        raise
    child_env = {
        "PATH": "/usr/local/bin:/usr/bin:/bin",
        "HOME": "/tmp",
        "CODEX_HOME": "/codex-home",
        "TMPDIR": "/tmp",
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "TERM": "dumb",
    }
    status = "execution_error"
    response = ""
    completed_returncode = 2
    auth_state_marker_created = False
    observations: dict[str, Any] = {
        "protocol": PROTOCOL,
        "mode": mode,
        "model": model,
        "reasoning_effort": reasoning_effort,
        "auth_mode": "chatgpt_login",
        "authentication_method": "chatgpt_login",
        "authentication_check_status": "verified",
        "codex_cli_version": "0.163.0",
        "runtime": runtime,
        "effective": effective,
        "codex_exec_argv_fingerprint": codex_exec_argv_fingerprint(
            codex_argv, mode=mode
        ),
        "status": status,
        "jsonl": None,
        "response_sha256": None,
        "final_message_redacted": False,
        "final_message_cleanup_status": (
            "isolated_tmpfs" if mode == "judge" else "pending"
        ),
        "codex_home_cleanup_status": "pending",
        "authentication_shell_visible_risk": AUTHENTICATION_SHELL_VISIBLE_RISK,
        "authentication_refresh_persistence_unresolved": (
            AUTHENTICATION_REFRESH_PERSISTENCE_UNRESOLVED
        ),
        "authentication_process_concurrency_unresolved": (
            AUTHENTICATION_PROCESS_CONCURRENCY_UNRESOLVED
        ),
        "web_search_enabled": False,
        "tool_policy": "no_cli_tools_or_mcp_configured",
        "sandbox_policy": sandbox_policy,
        "approval_policy": "never",
    }
    try:
        if auth_path is not None:
            mountpoint = home_path / "auth.json"
            if (
                not _regular_file(auth_path)
                or not _regular_file(mountpoint)
                or (os.name == "posix" and mountpoint.stat().st_mode & 0o077)
            ):
                raise CodexWsl2LauncherError(
                    "persistent Codex authentication mount is insecure"
                )
        if auth_execution is not None:
            _mark_auth_state_uncertain(auth_execution)
            auth_state_marker_created = True
        completed = subprocess.run(
            command,
            input=prompt.encode("utf-8"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=child_env,
            timeout=None,
            check=False,
            shell=False,
            close_fds=True,
        )
        stdout = completed.stdout
        stderr = completed.stderr.decode("utf-8", errors="replace")
        if stderr:
            sys.stderr.write(
                _sanitize(stderr) + ("" if stderr.endswith("\n") else "\n")
            )
        jsonl, response = _summarize_jsonl(stdout)
        observations["jsonl"] = jsonl
        observations["outer_exit_code"] = completed.returncode
        observations["docker_exit_code"] = completed.returncode
        completed_returncode = completed.returncode
        observations["status"] = (
            "completed" if completed.returncode == 0 else "execution_error"
        )
        if mode == "judge" and jsonl.get("tool_event_count", 0) > 0:
            observations["status"] = "evidence_unverified"
        if jsonl.get("status") != "captured" or not response:
            observations["status"] = "evidence_unverified"
        raw_response = response
        response = _sanitize(raw_response)
        response_redacted = response != raw_response
        observations["final_message_redacted"] = response_redacted
        if response_redacted:
            observations["status"] = "evidence_unverified"
        status = observations["status"]
        observations["response_sha256"] = (
            hashlib.sha256(response.encode("utf-8")).hexdigest()
            if response and not response_redacted
            else None
        )
    except (CodexWsl2LauncherError, OSError, subprocess.SubprocessError) as exc:
        status = "execution_error"
        observations["status"] = status
        observations["error"] = type(exc).__name__
    finally:
        if mode != "judge":
            try:
                removed = _cleanup_final_message_file(output_root, final_name)
                observations["final_message_cleanup_status"] = (
                    "removed" if removed else "not_present"
                )
            except (OSError, CodexWsl2LauncherError):
                observations["final_message_cleanup_status"] = "failed"
                observations["error"] = "final_message_cleanup_failed"
                status = "execution_error"
        try:
            cleanup_codex_home(
                home_path,
                allowed_parent=home_path.parent,
                workspace_root=workspace_root,
            )
            observations["codex_home_cleanup_status"] = "succeeded"
        except (OSError, CodexWsl2LauncherError):
            observations["codex_home_cleanup_status"] = "failed"
            observations["error"] = "codex_home_cleanup_failed"
            status = "execution_error"

    if (
        auth_execution is not None
        and auth_state_marker_created
        and completed_returncode == 0
        and observations.get("codex_home_cleanup_status") == "succeeded"
    ):
        try:
            _finalize_auth_state(auth_execution)
            observations["authentication_state_persistence"] = "fsynced"
        except (OSError, AuthExecutionBlocked):
            observations["authentication_state_persistence"] = "uncertain"
            observations["error"] = "authentication_state_cleanup_failed"
            status = "execution_error"

    observations["status"] = status or observations.get("status", "execution_error")
    if mode == "judge":
        try:
            _write_observations(observations_path, observations)
        except (OSError, CodexWsl2LauncherError):
            sys.stderr.write("Codex WSL2 launcher could not save observations\n")
            return 2
        sys.stdout.write(response)
        if response and not response.endswith("\n"):
            sys.stdout.write("\n")
    else:
        envelope = {
            "protocol": PROTOCOL,
            "exit_code": completed_returncode,
            "final_message": response,
            "observations": observations,
        }
        sys.stdout.write(
            json.dumps(envelope, ensure_ascii=False, separators=(",", ":")) + "\n"
        )
    return 0 if observations["status"] == "completed" else 2


def launch(
    *,
    mode: str,
    output_root: Path,
    prompt: str,
    observations_path: Path,
    model: str,
    reasoning_effort: str,
    sandbox_policy: str,
    workspace_root: Path | None,
    skill_root: Path | None = None,
    skill_name: str | None = None,
    codex_home: Path,
    runtime_root: Path | None = None,
) -> int:
    blockers = _authentication_execution_blockers()
    if blockers:
        return _launch_locked(
            mode=mode,
            output_root=output_root,
            prompt=prompt,
            observations_path=observations_path,
            model=model,
            reasoning_effort=reasoning_effort,
            sandbox_policy=sandbox_policy,
            workspace_root=workspace_root,
            skill_root=skill_root,
            skill_name=skill_name,
            codex_home=codex_home,
            runtime_root=runtime_root,
        )
    try:
        with _authentication_execution_context() as auth_execution:
            return _launch_locked(
                mode=mode,
                output_root=output_root,
                prompt=prompt,
                observations_path=observations_path,
                model=model,
                reasoning_effort=reasoning_effort,
                sandbox_policy=sandbox_policy,
                workspace_root=workspace_root,
                skill_root=skill_root,
                skill_name=skill_name,
                codex_home=codex_home,
                runtime_root=runtime_root,
                auth_execution=auth_execution,
            )
    except AuthExecutionBlocked as exc:
        _write_observations(
            observations_path,
            {
                "protocol": PROTOCOL,
                "status": "execution_error",
                "error": exc.reason,
                "authentication_method": "not_checked",
                "authentication_check_status": "blocked",
                "authentication_shell_visible_risk": AUTHENTICATION_SHELL_VISIBLE_RISK,
                "authentication_refresh_persistence_unresolved": (
                    AUTHENTICATION_REFRESH_PERSISTENCE_UNRESOLVED
                ),
                "authentication_process_concurrency_unresolved": (
                    AUTHENTICATION_PROCESS_CONCURRENCY_UNRESOLVED
                ),
                "authentication_execution_blockers": [exc.reason],
                "mode": mode,
            },
        )
        return 2


def _cleanup_final_message_file(output_root: Path, final_name: str) -> bool:
    """Remove Codex's temporary final-message file without following links."""
    if not re.fullmatch(r"\.codex-final-[0-9a-f]{32}\.md", final_name):
        raise CodexWsl2LauncherError("temporary final-message name is invalid")
    root = Path(output_root)
    if root.is_symlink() or not root.is_dir():
        raise CodexWsl2LauncherError("temporary final-message root is invalid")
    path = root / final_name
    if path.parent.resolve(strict=True) != root.resolve(strict=True):
        raise CodexWsl2LauncherError("temporary final-message path escaped output root")
    try:
        mode = path.lstat().st_mode
    except FileNotFoundError:
        return False
    if not (stat.S_ISREG(mode) or stat.S_ISLNK(mode)):
        raise CodexWsl2LauncherError("temporary final-message is not a regular file")
    path.unlink()
    return True


def _cleanup_temporary_final_messages(output_root: Path) -> None:
    """Remove only launcher-reserved final-message files from an attempt output."""
    root = Path(output_root)
    if root.is_symlink() or not root.is_dir():
        raise CodexWsl2LauncherError("temporary final-message root is invalid")
    for path in root.iterdir():
        if re.fullmatch(r"\.codex-final-[0-9a-f]{32}\.md", path.name):
            _cleanup_final_message_file(root, path.name)


def _sanitize(value: str) -> str:
    try:
        from scripts.skills.evals.agent.common import sanitize_diagnostic

        sanitized = sanitize_diagnostic(value, 2_000_000)
    except (ImportError, ValueError):
        sanitized = value[:2_000_000]
    return sanitized.replace("SYNTHETIC_AUTH_MARKER", "<synthetic-marker-redacted>")


def _summarize_jsonl(data: bytes) -> tuple[dict[str, Any], str]:
    observations, message = summarize_codex_jsonl(data)
    try:
        events = [
            json.loads(line)
            for line in data.decode("utf-8", errors="strict").splitlines()
            if line.strip()
        ]
    except (UnicodeDecodeError, json.JSONDecodeError):
        events = []
    non_tool = {
        "agent_message",
        "reasoning",
        "plan_update",
        "todo_list",
        "entered_review_mode",
        "exited_review_mode",
        "context_compaction",
    }
    tool_count = 0
    for event in events:
        if not isinstance(event, dict) or event.get("type") != "item.completed":
            continue
        item = event.get("item")
        if isinstance(item, dict) and item.get("type") not in non_tool:
            tool_count += 1
    observations["tool_event_count"] = tool_count
    observations["tool_use_detected"] = tool_count > 0
    return observations, message or ""


def _write_observations(path: Path, value: dict[str, Any]) -> None:
    path = _reject_symlink_components(path, allow_leaf=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise CodexWsl2LauncherError("observations path may not be a symlink")
    temporary = path.with_name(path.name + f".tmp-{uuid.uuid4().hex}")
    try:
        temporary.write_text(
            json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def launcher_argv(
    *,
    mode: str,
    output_root: Path,
    observations_path: Path,
    model: str,
    reasoning_effort: str,
    sandbox_policy: str,
    workspace_root: Path | None = None,
    skill_root: Path | None = None,
    skill_name: str | None = None,
    runtime_root: Path | None = None,
    cli_version: str | None = None,
    docker_argv: Sequence[str] | None = None,
) -> list[str]:
    if docker_argv is not None and list(docker_argv) != ["codex"]:
        raise CodexWsl2LauncherError(
            "schema 2 launch accepts only the fixed codex command template"
        )
    if cli_version is not None and not re.search(r"\b0\.163\.0\b", cli_version):
        raise CodexWsl2LauncherError("Codex CLI version must be 0.163.0")
    output = _reject_symlink_components(Path(output_root), allow_leaf=False)
    observations = _reject_symlink_components(Path(observations_path), allow_leaf=True)
    if workspace_root is not None:
        workspace_root = _reject_symlink_components(Path(workspace_root))
    if skill_root is not None:
        skill_root = _reject_symlink_components(Path(skill_root))
    if mode in {"agent", "repair"} and workspace_root is None:
        if output.name != ".qa-eval-output":
            raise CodexWsl2LauncherError(
                "workspace root is required for this output path"
            )
        workspace_root = output.parent
    if mode == "repair" and skill_root is None and skill_name:
        assert workspace_root is not None
        skill_root = Path(workspace_root) / ".agents" / "skills" / skill_name
    home_parent = _private_temp_root()
    home_path = home_parent / f"{CODEX_HOME_PREFIX}{mode}-{uuid.uuid4().hex}"
    command = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--mode",
        mode,
        "--output-root",
        str(output),
        "--observations-path",
        str(observations),
        "--model",
        model,
        "--reasoning-effort",
        reasoning_effort,
        "--sandbox-policy",
        sandbox_policy,
        "--codex-home",
        str(home_path),
    ]
    if workspace_root is not None:
        command.extend(["--workspace-root", str(workspace_root)])
    if skill_root is not None:
        command.extend(["--skill-root", str(skill_root)])
    if skill_name is not None:
        command.extend(["--skill-name", skill_name])
    if runtime_root is not None:
        command.extend(
            ["--runtime-root", str(_reject_symlink_components(Path(runtime_root)))]
        )
    return command


def judge_launcher_argv_for_profile(
    judge_profile: dict[str, Any], *, observations_path: Path
) -> list[str]:
    if (
        judge_profile.get("sandbox_policy") != "read-only"
        or judge_profile.get("approval_policy") != "never"
        or judge_profile.get("launch_options") != []
        or judge_profile.get("tools") != []
        or judge_profile.get("mcp_servers") != []
        or judge_profile.get("skill_roots") != []
        or str(judge_profile.get("global_config", "")).strip().lower()
        not in {"none", "disabled", "no-global-config"}
        or str(judge_profile.get("external_instructions", "")).strip().lower()
        not in {"none", "disabled", "no-external-instructions"}
    ):
        raise CodexWsl2LauncherError(
            "Judge profile enables an unapproved tool or config source"
        )
    output_root = observations_path.parent
    return launcher_argv(
        mode="judge",
        output_root=output_root,
        observations_path=observations_path,
        model=str(judge_profile["model"]),
        reasoning_effort=str(judge_profile["reasoning_effort"]),
        sandbox_policy="read-only",
        workspace_root=None,
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run Codex through the WSL2 dual-bubblewrap contract."
    )
    parser.add_argument(
        "--auth-status-only",
        action="store_true",
        help="verify ChatGPT login with the pinned Codex CLI without launching a model",
    )
    parser.add_argument(
        "--operator-login",
        action="store_true",
        help="run the fixed Codex CLI ChatGPT device login under the dedicated-store lock",
    )
    parser.add_argument("--mode", choices=("agent", "judge", "repair"))
    parser.add_argument("--output-root", type=Path)
    parser.add_argument("--observations-path", type=Path)
    parser.add_argument("--model")
    parser.add_argument("--reasoning-effort")
    parser.add_argument("--sandbox-policy", choices=("read-only", "workspace-write"))
    parser.add_argument("--workspace-root", type=Path)
    parser.add_argument("--skill-root", type=Path)
    parser.add_argument("--skill-name")
    parser.add_argument("--runtime-root", type=Path)
    parser.add_argument("--codex-home", type=Path)
    parser.add_argument("--cleanup-home", type=Path)
    parser.add_argument("--allowed-parent", type=Path)
    parser.add_argument("--cleanup-final-messages", type=Path)
    return parser


def _authentication_status(runtime_root: Path | None) -> tuple[dict[str, str], int]:
    try:
        with _authentication_execution_context(allow_uncertain_state=True) as paths:
            result, exit_code = _authentication_status_locked(runtime_root)
            result["authentication_store"] = "dedicated_persistent_file"
            state_uncertain = paths.uncertain_file.exists()
            result["authentication_state_uncertain"] = state_uncertain
            if state_uncertain:
                result["status"] = "state_uncertain"
                result["authentication_check_status"] = "blocked"
                exit_code = 2
            return result, exit_code
    except AuthExecutionBlocked as exc:
        return (
            {
                "status": "check_failed",
                "authentication_method": "unknown",
                "authentication_check_status": "blocked",
                "runtime_digest_status": "unverified",
                "codex_cli_version": "unknown",
                "error": exc.reason,
            },
            2,
        )


def _authentication_status_locked(
    runtime_root: Path | None,
) -> tuple[dict[str, str], int]:
    try:
        runtime = verify_runtime(runtime_root or runtime_root_from_environment())
    except (CodexWsl2LauncherError, OSError, ValueError) as exc:
        return (
            {
                "status": "check_failed",
                "authentication_method": "unknown",
                "authentication_check_status": "failed",
                "runtime_digest_status": "unverified",
                "codex_cli_version": "unknown",
                "error_class": type(exc).__name__,
            },
            2,
        )
    try:
        _auth_path, auth_method = _auth_material(runtime)
    except (CodexWsl2LauncherError, OSError, ValueError) as exc:
        auth_method = "check_failed"
        error_class = type(exc).__name__
    else:
        error_class = ""
    verified = auth_method == "chatgpt_login"
    result = {
        "status": "verified" if verified else "rejected",
        "authentication_method": auth_method,
        "authentication_check_status": "verified" if verified else "rejected",
        "runtime_digest_status": "verified",
        "codex_cli_version": "0.163.0",
    }
    if error_class:
        result["error_class"] = error_class
    return result, 0 if verified else 1


def _operator_login(runtime_root: Path | None) -> tuple[dict[str, Any], int]:
    try:
        with _authentication_execution_context() as paths:
            try:
                runtime = verify_runtime(
                    runtime_root or runtime_root_from_environment()
                )
            except (CodexWsl2LauncherError, OSError, ValueError) as exc:
                return (
                    {
                        "status": "check_failed",
                        "authentication_method": "unknown",
                        "authentication_check_status": "blocked",
                        "runtime_digest_status": "unverified",
                        "codex_cli_version": "unknown",
                        "error_class": type(exc).__name__,
                    },
                    2,
                )
            if paths.auth_file.exists() or paths.auth_file.is_symlink():
                return (
                    {
                        "status": "login_blocked",
                        "authentication_method": "not_checked",
                        "authentication_check_status": "blocked",
                        "authentication_state_uncertain": False,
                        "error": "operator_login_requires_empty_auth_store",
                    },
                    2,
                )
            _mark_auth_state_uncertain(paths)
            environment = {
                "PATH": "/usr/local/bin:/usr/bin:/bin",
                "HOME": str(paths.home),
                "CODEX_HOME": str(paths.codex_home),
                "TMPDIR": "/tmp",
                "LANG": "C.UTF-8",
                "LC_ALL": "C.UTF-8",
            }
            try:
                login = subprocess.run(
                    [runtime["codex_path"], "login", "--device-auth"],
                    stdin=None,
                    stdout=None,
                    stderr=None,
                    env=environment,
                    check=False,
                    shell=False,
                    close_fds=True,
                )
            except (OSError, subprocess.SubprocessError) as exc:
                return (
                    {
                        "status": "login_failed",
                        "authentication_method": "not_verified",
                        "authentication_check_status": "uncertain",
                        "authentication_state_uncertain": True,
                        "error_class": type(exc).__name__,
                    },
                    2,
                )
            if login.returncode != 0:
                return (
                    {
                        "status": "login_failed",
                        "authentication_method": "not_verified",
                        "authentication_check_status": "uncertain",
                        "authentication_state_uncertain": True,
                        "codex_cli_exit_code": login.returncode,
                    },
                    1,
                )
            result, exit_code = _authentication_status_locked(runtime_root)
            if exit_code != 0 or result.get("authentication_method") != "chatgpt_login":
                result["authentication_state_uncertain"] = True
                return result, 1
            _sync_auth_store(paths)
            _clear_auth_state_uncertain(paths)
            return (
                {
                    "status": "verified",
                    "authentication_method": "chatgpt_login",
                    "authentication_check_status": "verified",
                    "authentication_store": "dedicated_persistent_file",
                    "authentication_state_uncertain": False,
                    "runtime_digest_status": "verified",
                    "codex_cli_version": "0.163.0",
                },
                0,
            )
    except (AuthExecutionBlocked, OSError) as exc:
        reason = (
            exc.reason if isinstance(exc, AuthExecutionBlocked) else type(exc).__name__
        )
        return (
            {
                "status": "check_failed",
                "authentication_method": "unknown",
                "authentication_check_status": "blocked",
                "authentication_state_uncertain": True,
                "error": reason,
            },
            2,
        )


def main(argv: list[str] | None = None) -> int:
    if os.name == "posix":
        signal.signal(
            signal.SIGTERM,
            lambda _signum, _frame: (_ for _ in ()).throw(SystemExit(143)),
        )
    args, remainder = _parser().parse_known_args(argv)
    if args.cleanup_home is not None:
        if args.allowed_parent is None:
            print("cleanup requires --allowed-parent", file=sys.stderr)
            return 2
        cleanup_error = None
        try:
            cleanup_codex_home(
                args.cleanup_home,
                allowed_parent=args.allowed_parent,
                workspace_root=args.workspace_root,
            )
        except (OSError, CodexWsl2LauncherError) as exc:
            cleanup_error = type(exc).__name__
        if args.cleanup_final_messages is not None:
            try:
                _cleanup_temporary_final_messages(args.cleanup_final_messages)
            except (OSError, CodexWsl2LauncherError) as exc:
                cleanup_error = cleanup_error or type(exc).__name__
        if cleanup_error is not None:
            print(f"Codex launcher cleanup failed: {cleanup_error}", file=sys.stderr)
            return 2
        return 0
    if args.auth_status_only:
        result, exit_code = _authentication_status(args.runtime_root)
        print(json.dumps(result, ensure_ascii=True, sort_keys=True))
        return exit_code
    if args.operator_login:
        result, exit_code = _operator_login(args.runtime_root)
        print(json.dumps(result, ensure_ascii=True, sort_keys=True))
        return exit_code
    if (
        args.codex_home is None
        or args.mode is None
        or args.output_root is None
        or args.observations_path is None
        or args.model is None
        or args.reasoning_effort is None
        or args.sandbox_policy is None
    ):
        _parser().error(
            "launcher requires mode, output, observations, model, reasoning, sandbox, and home"
        )
    prompt = sys.stdin.read()
    try:
        return launch(
            mode=args.mode,
            output_root=args.output_root,
            prompt=prompt,
            observations_path=args.observations_path,
            model=args.model,
            reasoning_effort=args.reasoning_effort,
            sandbox_policy=args.sandbox_policy,
            workspace_root=args.workspace_root,
            skill_root=args.skill_root,
            skill_name=args.skill_name,
            codex_home=args.codex_home,
            runtime_root=args.runtime_root,
        )
    except (CodexWsl2LauncherError, OSError, ValueError) as exc:
        print(f"Codex WSL2 launcher error: {type(exc).__name__}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
