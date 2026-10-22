from __future__ import annotations

import argparse
import atexit
import json
import os
import re
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
import uuid
from collections import Counter
from pathlib import Path, PurePosixPath
from typing import Any, Sequence

REPO_ROOT = Path(__file__).resolve().parents[5]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.skills.evals.agent.common import (  # noqa: E402
    MAX_TEXT_BYTES,
    bounded_text,
    sanitize_diagnostic,
    sha256_bytes,
)
from scripts.skills.evals.agent.workspace import (  # noqa: E402
    verify_agent_docker_command,
    verify_repair_docker_command,
)

PROTOCOL = "codex_docker_launcher_v1"
_ALLOWED_SANDBOXES = {"read-only", "workspace-write"}
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
_SKILL_PATH_RE = re.compile(
    r"(?:^|[\s'\"])(?:/workspace/)?\.agents/skills/([a-z0-9]+(?:-[a-z0-9]+)*)/SKILL\.md(?:$|[\s'\"])",
    re.I,
)
_SKILL_READER_RE = re.compile(
    r"(?:^|[\s;&|])(?:cat|head|tail|sed|awk|rg|grep|less|more)(?:\s|$)",
    re.I,
)


class CodexLauncherError(RuntimeError):
    """Raised when the fixed Codex/Docker launch contract is invalid."""


def _docker_image_index(argv: Sequence[str]) -> int:
    value_options = {
        "--network",
        "--mount",
        "--workdir",
        "-w",
        "--name",
        "--user",
        "--env",
        "--security-opt",
        "--cap-drop",
        "--memory",
        "--cpus",
    }
    flag_options = {"--rm", "--read-only", "-i", "--init"}
    index = 2
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
        if token.startswith("-"):
            raise CodexLauncherError(
                "unsupported Docker run option in launcher command"
            )
        return index
    raise CodexLauncherError("Docker run command has no image")


def _mounts(argv: Sequence[str]) -> list[dict[str, str | bool]]:
    mounts: list[dict[str, str | bool]] = []
    index = 0
    while index < len(argv):
        if argv[index] == "--mount" and index + 1 < len(argv):
            value = argv[index + 1]
            index += 2
        elif argv[index].startswith("--mount="):
            value = argv[index].split("=", 1)[1]
            index += 1
        else:
            index += 1
            continue
        fields: dict[str, str | bool] = {}
        for part in value.split(","):
            key, separator, item = part.partition("=")
            fields[key] = item if separator else True
        mounts.append(fields)
    return mounts


def _safe_runtime_path(value: str) -> str | None:
    normalized = value.replace("\\", "/")
    for prefix in (
        "/workspace/.qa-eval-output/",
        ".qa-eval-output/",
    ):
        if normalized.startswith(prefix):
            normalized = normalized[len(prefix) :]
            break
    else:
        return None
    path = PurePosixPath(normalized)
    if (
        path.is_absolute()
        or not path.parts
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        return None
    if path.parts[0] != ".runtime-evidence":
        return None
    return path.as_posix()


def _capture_invocation(command: str, exit_code: int | None) -> dict[str, Any] | None:
    if exit_code != 0:
        return None
    try:
        tokens = shlex.split(command, posix=True)
    except ValueError:
        return None
    if not any(
        token.replace("\\", "/").endswith(".qa-eval-tools/verifier_capture.py")
        for token in tokens
    ):
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
    skill = values.get("--skill")
    operation = values.get("--operation")
    request_path = _safe_runtime_path(values.get("--request", ""))
    record_path = _safe_runtime_path(values.get("--record", ""))
    if (
        not isinstance(skill, str)
        or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", skill)
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


def summarize_codex_jsonl(
    data: bytes, *, skill_names: Sequence[str] = ()
) -> tuple[dict[str, Any], str | None]:
    """Extract non-secret observations and the final response without retaining JSONL."""
    try:
        raw = data.decode("utf-8", errors="strict")
        events = [json.loads(line) for line in raw.splitlines() if line.strip()]
    except (UnicodeDecodeError, json.JSONDecodeError):
        return (
            {
                "status": "unverified",
                "event_count": 0,
                "event_types": {},
                "command_count": 0,
                "commands": [],
                "skill_use_observation": {name: "unverified" for name in skill_names},
            },
            None,
        )
    if (
        not events
        or any(
            not isinstance(event, dict) or not isinstance(event.get("type"), str)
            for event in events
        )
        or any(event["type"] not in _CODEX_JSONL_EVENT_TYPES for event in events)
    ):
        return (
            {
                "status": "unverified",
                "event_count": len(events),
                "event_types": {},
                "command_count": 0,
                "commands": [],
                "skill_use_observation": {name: "unverified" for name in skill_names},
            },
            None,
        )

    event_types = Counter(event["type"] for event in events)
    final_message: str | None = None
    observed: set[str] = set()
    commands: list[dict[str, Any]] = []
    for event in events:
        if event.get("type") != "item.completed":
            continue
        item = event.get("item")
        if not isinstance(item, dict):
            continue
        if item.get("type") == "agent_message" and isinstance(item.get("text"), str):
            final_message = item["text"]
            continue
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
        normalized = command.replace("\\", "/")
        observed_skills: list[str] = []
        if exit_code == 0 and _SKILL_READER_RE.search(command):
            skill_match = _SKILL_PATH_RE.search(normalized)
            if skill_match:
                name = skill_match.group(1).lower()
                observed.add(name)
                observed_skills.append(name)
        capture = _capture_invocation(command, exit_code)
        commands.append(
            {
                "exit_code": exit_code,
                "successful": exit_code == 0,
                "skill_files_read": observed_skills,
                "verifier_capture_invocations": [capture] if capture else [],
            }
        )
    return (
        {
            "status": "captured"
            if final_message is not None
            and event_types.get("turn.completed", 0) > 0
            and event_types.get("turn.failed", 0) == 0
            and event_types.get("error", 0) == 0
            else "evidence_unverified",
            "event_count": len(events),
            "event_types": dict(sorted(event_types.items())),
            "command_count": len(commands),
            "commands": commands,
            "turn_completed": event_types.get("turn.completed", 0) > 0,
            "turn_failed": event_types.get("turn.failed", 0) > 0,
            "skill_files_read": sorted(observed),
        },
        final_message,
    )


def _auth_material() -> tuple[Path | None, bool, str]:
    configured_home = os.environ.get("CODEX_HOME")
    source_home = (
        Path(configured_home).expanduser()
        if configured_home
        else Path.home() / ".codex"
    )
    source_auth = source_home / "auth.json"
    if source_auth.is_symlink():
        raise CodexLauncherError("Codex authentication source may not be a symlink")
    if source_auth.exists():
        if not source_auth.is_file():
            raise CodexLauncherError(
                "Codex authentication source must be a regular file"
            )
        try:
            if source_auth.stat().st_size > 1_000_000:
                raise CodexLauncherError(
                    "Codex authentication source exceeds the size limit"
                )
        except OSError as exc:
            raise CodexLauncherError(
                "Codex authentication source is unavailable"
            ) from exc
        try:
            source_auth.resolve().relative_to(REPO_ROOT.resolve())
        except ValueError:
            return source_auth, False, "temporary_auth_file"
        raise CodexLauncherError(
            "Codex credentials may not be read from the repository"
        )
    if os.environ.get("OPENAI_API_KEY"):
        return None, True, "api_key_environment"
    return None, False, "unavailable"


def _release_version(value: str) -> str | None:
    match = re.search(r"(?<!\d)(\d+\.\d+\.\d+)(?!\d)", value)
    return match.group(1) if match else None


def _remove_temporary_message(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass


def _probe_image_runtime(
    docker_argv: Sequence[str], expected_cli_version: str
) -> dict[str, str]:
    image_index = _docker_image_index(docker_argv)
    image = docker_argv[image_index]
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", image):
        raise CodexLauncherError(
            "Agent command must pin the Codex image by immutable image ID"
        )
    image_id_result = subprocess.run(
        [docker_argv[0], "image", "inspect", "--format", "{{.Id}}", image],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
        check=False,
        shell=False,
    )
    image_id = image_id_result.stdout.decode("utf-8", errors="strict").strip()
    if image_id_result.returncode != 0 or not re.fullmatch(
        r"sha256:[0-9a-f]{64}", image_id
    ):
        raise CodexLauncherError("Agent image id could not be verified")

    def probe(command: list[str]) -> str:
        result = subprocess.run(
            [
                docker_argv[0],
                "run",
                "--rm",
                "--network",
                "none",
                "--read-only",
                "--cap-drop=ALL",
                "--security-opt=no-new-privileges",
                "--mount",
                "type=tmpfs,target=/tmp",
                "--user",
                f"{os.getuid()}:{os.getgid()}",
                image_id,
                *command,
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
            check=False,
            shell=False,
        )
        output = result.stdout.decode("utf-8", errors="strict").strip()
        if result.returncode != 0:
            raise CodexLauncherError("Agent image runtime probe failed")
        return output

    cli_version = probe(["codex", "--version"])
    python_version = probe(["python3.11", "--version"])
    actual_release = _release_version(cli_version)
    expected_release = _release_version(expected_cli_version)
    if actual_release is None or actual_release != expected_release:
        raise CodexLauncherError(
            "Agent image Codex version does not match the execution profile"
        )
    if not re.fullmatch(r"Python 3\.11\.\d+", python_version):
        raise CodexLauncherError("Agent image must provide Python 3.11")
    return {
        "image_id": image_id,
        "codex_cli_version": cli_version,
        "python_version": python_version,
    }


def _docker_with_codex_runtime(
    docker_argv: Sequence[str],
    *,
    temporary_home: Path,
    model: str,
    reasoning_effort: str,
    sandbox_policy: str,
    output_message_path: str,
    workspace_is_git: bool,
    pass_api_key: bool,
) -> list[str]:
    if (
        len(docker_argv) < 4
        or Path(docker_argv[0]).name.lower() not in {"docker", "docker.exe"}
        or docker_argv[1] != "run"
    ):
        raise CodexLauncherError("launcher requires a direct Docker run argv")
    image_index = _docker_image_index(docker_argv)
    if image_index + 3 != len(docker_argv):
        raise CodexLauncherError("Docker image command must contain only 'codex exec'")
    if (
        Path(docker_argv[image_index + 1]).name.lower() not in {"codex", "codex.exe"}
        or docker_argv[image_index + 2] != "exec"
    ):
        raise CodexLauncherError("Docker image command must end in 'codex exec'")
    if "--user" in docker_argv or any(
        item.startswith("--user=") for item in docker_argv
    ):
        raise CodexLauncherError("container UID/GID is set by the launcher")
    for mount in _mounts(docker_argv):
        if mount.get("target") == "/codex-home":
            raise CodexLauncherError("CODEX_HOME mount is set by the launcher")
    for index, token in enumerate(docker_argv):
        if token in {"-e", "--env", "--env-file"} or token.startswith(
            ("--env=", "--env-file=")
        ):
            raise CodexLauncherError("environment variables are set by the launcher")
    uid = os.getuid()
    gid = os.getgid()
    prefix = list(docker_argv[:image_index])
    prefix.extend(
        [
            "--user",
            f"{uid}:{gid}",
            "--mount",
            f"type=bind,source={temporary_home.resolve()},target=/codex-home",
            "--env",
            "CODEX_HOME=/codex-home",
            "--env",
            "HOME=/tmp",
        ]
    )
    if pass_api_key:
        prefix.extend(["--env", "OPENAI_API_KEY"])
    codex_argv = [
        "codex",
        "--no-daemon",
        "--strict-config",
        "--ask-for-approval",
        "never",
        "exec",
        "--json",
        "--model",
        model,
        "--sandbox",
        sandbox_policy,
        "--config",
        f"model_reasoning_effort={json.dumps(reasoning_effort)}",
        "--cd",
        "/workspace",
    ]
    if not workspace_is_git:
        codex_argv.append("--skip-git-repo-check")
    codex_argv.extend(["--output-last-message", output_message_path, "-"])
    return [*prefix, docker_argv[image_index], *codex_argv]


def _validate_output_mount(docker_argv: Sequence[str], output_root: Path) -> None:
    matches = [
        mount
        for mount in _mounts(docker_argv)
        if mount.get("target") == "/workspace/.qa-eval-output"
        and mount.get("type") == "bind"
        and isinstance(mount.get("source"), str)
    ]
    if (
        len(matches) != 1
        or Path(str(matches[0]["source"])).resolve() != output_root.resolve()
    ):
        raise CodexLauncherError(
            "Docker output mount does not match the attempt output root"
        )
    if matches[0].get("readonly") is True or matches[0].get("ro") is True:
        raise CodexLauncherError("attempt output mount must be writable")


def launch(
    *,
    output_root: Path,
    model: str,
    reasoning_effort: str,
    cli_version: str,
    sandbox_policy: str,
    docker_argv: Sequence[str],
    prompt: str,
    mode: str = "agent",
    skill_name: str | None = None,
) -> int:
    if os.name != "posix":
        raise CodexLauncherError("Codex Docker launcher requires a Linux host")
    if mode not in {"agent", "repair"}:
        raise CodexLauncherError("launcher mode must be agent or repair")
    if (mode == "repair") != (skill_name is not None):
        raise CodexLauncherError("repair mode requires exactly one target Skill name")
    if skill_name is not None and not re.fullmatch(
        r"[a-z0-9]+(?:-[a-z0-9]+)*", skill_name
    ):
        raise CodexLauncherError("repair Skill name is invalid")
    if sandbox_policy not in _ALLOWED_SANDBOXES:
        raise CodexLauncherError(
            "Codex sandbox policy must be read-only or workspace-write"
        )
    if not model.strip() or not reasoning_effort.strip():
        raise CodexLauncherError("Codex model and reasoning effort must be fixed")
    if not cli_version.strip():
        raise CodexLauncherError("Codex CLI version must be fixed")
    output_root = output_root.resolve()
    if not output_root.is_dir():
        raise CodexLauncherError("attempt output root must exist before launch")
    _validate_output_mount(docker_argv, output_root)
    workspace_mounts = [
        mount
        for mount in _mounts(docker_argv)
        if mount.get("target") == "/workspace"
        and mount.get("type") == "bind"
        and isinstance(mount.get("source"), str)
    ]
    if len(workspace_mounts) != 1:
        raise CodexLauncherError(
            "Docker command must contain one /workspace bind mount"
        )
    workspace_root = Path(str(workspace_mounts[0]["source"])).resolve()
    if (
        workspace_mounts[0].get("readonly") is not True
        and workspace_mounts[0].get("ro") is not True
    ):
        raise CodexLauncherError("Agent workspace bind mount must be read-only")
    try:
        if mode == "agent":
            verify_agent_docker_command(
                list(docker_argv),
                workspace=workspace_root,
                output_root=output_root,
                evaluator_root=REPO_ROOT,
            )
        else:
            assert skill_name is not None
            skill_target = f"/workspace/.agents/skills/{skill_name}"
            skill_mounts = [
                mount
                for mount in _mounts(docker_argv)
                if mount.get("type") == "bind"
                and mount.get("target") == skill_target
                and isinstance(mount.get("source"), str)
            ]
            if len(skill_mounts) != 1:
                raise CodexLauncherError(
                    "repair command must expose exactly the requested Skill package"
                )
            verify_repair_docker_command(
                list(docker_argv),
                workspace=workspace_root,
                skill_root=Path(str(skill_mounts[0]["source"])),
                output_root=output_root,
                skill_name=skill_name,
            )
    except Exception as exc:
        raise CodexLauncherError(
            "Docker command does not satisfy the Agent isolation contract"
        ) from exc

    auth_path, pass_api_key, auth_mode = _auth_material()
    final_name = f".codex-final-{uuid.uuid4().hex}.md"
    final_container_path = f"/workspace/.qa-eval-output/{final_name}"
    message_path = output_root / final_name
    atexit.register(_remove_temporary_message, message_path)
    observations: dict[str, Any] = {
        "protocol": PROTOCOL,
        "mode": mode,
        "status": "execution_error",
        "auth_mode": auth_mode,
        "jsonl": None,
        "final_message_sha256": None,
    }
    if auth_mode == "unavailable":
        observations["error"] = "authentication_unavailable"
        sys.stdout.write(
            json.dumps(
                {
                    "protocol": PROTOCOL,
                    "exit_code": 2,
                    "final_message": "",
                    "observations": observations,
                },
                ensure_ascii=False,
                separators=(",", ":"),
            )
            + "\n"
        )
        return 2
    final_message = ""
    with tempfile.TemporaryDirectory(prefix="agent-eval-codex-home-") as temporary:
        temporary_home = Path(temporary)
        os.chmod(temporary_home, 0o700)
        if auth_path is not None:
            copied_auth = temporary_home / "auth.json"
            shutil.copyfile(auth_path, copied_auth)
            os.chmod(copied_auth, 0o600)
        command = _docker_with_codex_runtime(
            docker_argv,
            temporary_home=temporary_home,
            model=model,
            reasoning_effort=reasoning_effort,
            sandbox_policy=sandbox_policy,
            output_message_path=final_container_path,
            workspace_is_git=(workspace_root / ".git").exists()
            or (workspace_root / ".git").is_file(),
            pass_api_key=pass_api_key,
        )
        try:
            observations["image"] = _probe_image_runtime(docker_argv, cli_version)
        except (CodexLauncherError, OSError, subprocess.SubprocessError) as exc:
            observations["error"] = type(exc).__name__
            sys.stdout.write(
                json.dumps(
                    {
                        "protocol": PROTOCOL,
                        "exit_code": 2,
                        "final_message": "",
                        "observations": observations,
                    },
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
                + "\n"
            )
            return 2
        command[_docker_image_index(command)] = observations["image"]["image_id"]
        try:
            completed = subprocess.run(
                command,
                input=prompt.encode("utf-8"),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=None,
                check=False,
                shell=False,
            )
        except OSError as exc:
            observations["status"] = "execution_error"
            observations["error"] = type(exc).__name__
            completed = None
        if completed is not None:
            stdout = completed.stdout
            stderr = completed.stderr.decode("utf-8", errors="replace")
            if stderr:
                sys.stderr.write(sanitize_diagnostic(stderr, 64_000))
                if not stderr.endswith("\n"):
                    sys.stderr.write("\n")
            jsonl, streamed_message = summarize_codex_jsonl(stdout)
            observations["jsonl"] = jsonl
            observations["docker_exit_code"] = completed.returncode
            if message_path.exists() or message_path.is_symlink():
                try:
                    if message_path.is_symlink() or not message_path.is_file():
                        raise CodexLauncherError(
                            "Codex final message must be a regular file"
                        )
                    if message_path.stat().st_size > MAX_TEXT_BYTES:
                        raise CodexLauncherError(
                            "Codex final message exceeds the output limit"
                        )
                    final_message = message_path.read_text(encoding="utf-8")
                finally:
                    message_path.unlink(missing_ok=True)
            elif streamed_message is not None:
                final_message = streamed_message
            observations["status"] = (
                "completed" if completed.returncode == 0 else "execution_error"
            )
            safe_message = sanitize_diagnostic(final_message, MAX_TEXT_BYTES)
            observations["final_message_redacted"] = safe_message != final_message
            if safe_message == final_message:
                observations["final_message_sha256"] = sha256_bytes(
                    safe_message.encode("utf-8")
                )
            else:
                observations["final_message_sha256"] = None
            if jsonl["status"] != "captured":
                observations["status"] = "evidence_unverified"
            if not final_message:
                observations["status"] = "evidence_unverified"
            envelope = {
                "protocol": PROTOCOL,
                "exit_code": completed.returncode,
                "final_message": bounded_text(safe_message, MAX_TEXT_BYTES),
                "observations": observations,
            }
            sys.stdout.write(
                json.dumps(envelope, ensure_ascii=False, separators=(",", ":")) + "\n"
            )
            return completed.returncode
        sys.stdout.write(
            json.dumps(
                {
                    "protocol": PROTOCOL,
                    "exit_code": 2,
                    "final_message": "",
                    "observations": observations,
                },
                ensure_ascii=False,
                separators=(",", ":"),
            )
            + "\n"
        )
        return 2


def launcher_argv(
    *,
    output_root: Path,
    model: str,
    reasoning_effort: str,
    cli_version: str,
    sandbox_policy: str,
    docker_argv: Sequence[str],
    mode: str = "agent",
    skill_name: str | None = None,
) -> list[str]:
    command = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--output-root",
        str(output_root),
        "--model",
        model,
        "--reasoning-effort",
        reasoning_effort,
        "--cli-version",
        cli_version,
        "--sandbox-policy",
        sandbox_policy,
    ]
    if mode != "agent":
        command.extend(["--mode", mode])
    if skill_name is not None:
        command.extend(["--skill-name", skill_name])
    return [*command, "--", *docker_argv]


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Codex in a disposable isolated Docker container."
    )
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--reasoning-effort", required=True)
    parser.add_argument("--cli-version", required=True)
    parser.add_argument(
        "--sandbox-policy", required=True, choices=sorted(_ALLOWED_SANDBOXES)
    )
    parser.add_argument("--mode", choices=("agent", "repair"), default="agent")
    parser.add_argument("--skill-name")
    parser.add_argument("docker_argv", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    if args.docker_argv and args.docker_argv[0] == "--":
        args.docker_argv = args.docker_argv[1:]
    if not args.docker_argv:
        parser.error("a direct docker run argv must follow --")
    return args


def main(argv: list[str] | None = None) -> int:
    if os.name == "posix":
        signal.signal(
            signal.SIGTERM,
            lambda _signum, _frame: (_ for _ in ()).throw(SystemExit(143)),
        )
    args = _parse_args(argv)
    try:
        return launch(
            output_root=args.output_root,
            model=args.model,
            reasoning_effort=args.reasoning_effort,
            cli_version=args.cli_version,
            sandbox_policy=args.sandbox_policy,
            docker_argv=args.docker_argv,
            prompt=sys.stdin.read(),
            mode=args.mode,
            skill_name=args.skill_name,
        )
    except (CodexLauncherError, OSError, UnicodeError, ValueError) as exc:
        print(f"codex docker launcher error: {type(exc).__name__}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
