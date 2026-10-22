from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Sequence

REPO_ROOT = Path(__file__).resolve().parents[5]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.skills.evals.agent.common import (  # noqa: E402
    MAX_TEXT_BYTES,
    atomic_write_json,
    bounded_text,
    sanitize_diagnostic,
    sha256_bytes,
)
from scripts.skills.evals.agent.workspace import (  # noqa: E402
    verify_judge_docker_command,
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
_NON_TOOL_ITEM_TYPES = {"agent_message", "reasoning"}


class CodexJudgeLauncherError(RuntimeError):
    """Raised when the isolated Judge launch contract is invalid."""


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
            raise CodexJudgeLauncherError(
                "unsupported Docker run option in Judge command"
            )
        return index
    raise CodexJudgeLauncherError("Judge Docker command has no image")


def _release_version(value: str) -> str | None:
    match = re.search(r"(?<!\d)(\d+\.\d+\.\d+)(?!\d)", value)
    return match.group(1) if match else None


def is_codex_judge(judge_profile: dict[str, Any]) -> bool:
    version = str(judge_profile.get("cli_version", ""))
    return "codex" in version.lower() and _release_version(version) is not None


def _auth_material() -> tuple[Path | None, bool, str]:
    configured_home = os.environ.get("CODEX_HOME")
    source_home = (
        Path(configured_home).expanduser()
        if configured_home
        else Path.home() / ".codex"
    )
    source_auth = source_home / "auth.json"
    if source_auth.is_symlink():
        raise CodexJudgeLauncherError(
            "Codex authentication source may not be a symlink"
        )
    if source_auth.exists():
        if not source_auth.is_file():
            raise CodexJudgeLauncherError(
                "Codex authentication source must be a regular file"
            )
        try:
            if source_auth.stat().st_size > 1_000_000:
                raise CodexJudgeLauncherError(
                    "Codex authentication source exceeds the size limit"
                )
            source_auth.resolve().relative_to(REPO_ROOT.resolve())
        except ValueError:
            return source_auth, False, "temporary_auth_file"
        except OSError as exc:
            raise CodexJudgeLauncherError(
                "Codex authentication source is unavailable"
            ) from exc
        raise CodexJudgeLauncherError(
            "Codex credentials may not be read from the repository"
        )
    if os.environ.get("OPENAI_API_KEY"):
        return None, True, "api_key_environment"
    return None, False, "unavailable"


def _summarize_jsonl(data: bytes) -> tuple[dict[str, Any], str | None]:
    try:
        raw = data.decode("utf-8", errors="strict")
        events = [json.loads(line) for line in raw.splitlines() if line.strip()]
    except (UnicodeDecodeError, json.JSONDecodeError):
        events = []
    if (
        not events
        or any(
            not isinstance(event, dict) or not isinstance(event.get("type"), str)
            for event in events
        )
        or any(event["type"] not in _CODEX_JSONL_EVENT_TYPES for event in events)
        or any(
            event["type"].startswith("item.")
            and (
                not isinstance(event.get("item"), dict)
                or not isinstance(event["item"].get("type"), str)
            )
            for event in events
        )
    ):
        return (
            {
                "status": "unverified",
                "event_count": len(events),
                "event_types": {},
            },
            None,
        )
    event_types = Counter(event["type"] for event in events)
    item_types = Counter(
        item["type"]
        for event in events
        if event["type"].startswith("item.")
        and isinstance((item := event.get("item")), dict)
        and isinstance(item.get("type"), str)
    )
    tool_use_detected = any(
        item_type not in _NON_TOOL_ITEM_TYPES for item_type in item_types
    )
    messages = [
        item["text"]
        for event in events
        if event["type"] == "item.completed"
        and isinstance((item := event.get("item")), dict)
        and item.get("type") == "agent_message"
        and isinstance(item.get("text"), str)
    ]
    message = messages[-1] if messages and not tool_use_detected else None
    complete = (
        message is not None
        and event_types.get("turn.completed", 0) > 0
        and event_types.get("turn.failed", 0) == 0
        and event_types.get("error", 0) == 0
        and not tool_use_detected
    )
    return (
        {
            "status": "captured" if complete else "evidence_unverified",
            "event_count": len(events),
            "event_types": dict(sorted(event_types.items())),
            "item_types": dict(sorted(item_types.items())),
            "tool_use_detected": tool_use_detected,
            "turn_completed": event_types.get("turn.completed", 0) > 0,
            "turn_failed": event_types.get("turn.failed", 0) > 0,
        },
        message,
    )


def _probe_image(
    docker_argv: Sequence[str], expected_cli_version: str
) -> dict[str, str]:
    image = docker_argv[_docker_image_index(docker_argv)]
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", image):
        raise CodexJudgeLauncherError(
            "Judge command must pin the Codex image by immutable image ID"
        )
    inspected = subprocess.run(
        [docker_argv[0], "image", "inspect", "--format", "{{.Id}}", image],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
        check=False,
        shell=False,
    )
    image_id = inspected.stdout.decode("utf-8", errors="strict").strip()
    if inspected.returncode != 0 or not re.fullmatch(r"sha256:[0-9a-f]{64}", image_id):
        raise CodexJudgeLauncherError("Judge image id could not be verified")

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
            raise CodexJudgeLauncherError("Judge image runtime probe failed")
        return output

    cli_version = probe(["codex", "--version"])
    python_version = probe(["python3.11", "--version"])
    if _release_version(cli_version) != _release_version(expected_cli_version):
        raise CodexJudgeLauncherError(
            "Judge image Codex version does not match the profile"
        )
    if not re.fullmatch(r"Python 3\.11\.\d+", python_version):
        raise CodexJudgeLauncherError("Judge image must provide Python 3.11")
    return {
        "image_id": image_id,
        "codex_cli_version": cli_version,
        "python_version": python_version,
    }


def _docker_with_codex_runtime(
    docker_argv: Sequence[str],
    *,
    temporary_home: Path,
    image_id: str,
    model: str,
    reasoning_effort: str,
) -> list[str]:
    if (
        len(docker_argv) < 4
        or Path(docker_argv[0]).name.lower() not in {"docker", "docker.exe"}
        or docker_argv[1] != "run"
    ):
        raise CodexJudgeLauncherError("Judge launcher requires direct docker run argv")
    image_index = _docker_image_index(docker_argv)
    if image_index + 3 != len(docker_argv):
        raise CodexJudgeLauncherError(
            "Judge image command must contain only 'codex exec'"
        )
    if (
        Path(docker_argv[image_index + 1]).name.lower() not in {"codex", "codex.exe"}
        or docker_argv[image_index + 2] != "exec"
    ):
        raise CodexJudgeLauncherError("Judge image command must end in 'codex exec'")
    if any(
        token in {"--user", "--env", "-e", "--env-file", "-w", "--workdir"}
        or token.startswith(("--user=", "--env=", "--env-file="))
        for token in docker_argv
    ):
        raise CodexJudgeLauncherError(
            "Judge user, environment, and workdir are launcher-owned"
        )
    prefix = list(docker_argv[:image_index])
    prefix.extend(
        [
            "--user",
            f"{os.getuid()}:{os.getgid()}",
            "--workdir",
            "/tmp",
            "--mount",
            f"type=bind,source={temporary_home.resolve()},target=/codex-home",
            "--env",
            "CODEX_HOME=/codex-home",
            "--env",
            "HOME=/tmp",
        ]
    )
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
        "read-only",
        "--config",
        f"model_reasoning_effort={json.dumps(reasoning_effort)}",
        "--cd",
        "/tmp",
        "--skip-git-repo-check",
        "-",
    ]
    return [*prefix, image_id, *codex_argv]


def _write_observations(path: Path, value: dict[str, Any]) -> None:
    cwd = Path.cwd().resolve()
    resolved = path.resolve()
    try:
        resolved.relative_to(cwd)
    except ValueError as exc:
        raise CodexJudgeLauncherError(
            "Judge observations must stay inside its isolated host workspace"
        ) from exc
    if path.is_symlink():
        raise CodexJudgeLauncherError("Judge observations path may not be a symlink")
    atomic_write_json(resolved, value)
    os.chmod(resolved, 0o600)


def launch(
    *,
    model: str,
    reasoning_effort: str,
    cli_version: str,
    sandbox_policy: str,
    approval_policy: str,
    docker_argv: Sequence[str],
    prompt: str,
    observations_path: Path,
) -> int:
    if os.name != "posix":
        raise CodexJudgeLauncherError(
            "Codex Judge Docker launcher requires a Linux host"
        )
    if sandbox_policy != "read-only" or approval_policy != "never":
        raise CodexJudgeLauncherError(
            "Codex Judge must use read-only sandbox and no approvals"
        )
    if not model.strip() or not reasoning_effort.strip() or not cli_version.strip():
        raise CodexJudgeLauncherError(
            "Judge model, reasoning, and CLI version must be fixed"
        )
    verify_judge_docker_command(list(docker_argv), evaluator_root=REPO_ROOT)
    try:
        image = _probe_image(docker_argv, cli_version)
    except (CodexJudgeLauncherError, OSError, subprocess.SubprocessError) as exc:
        _write_observations(
            observations_path,
            {
                "status": "execution_error",
                "error": type(exc).__name__,
                "model": model,
                "reasoning_effort": reasoning_effort,
                "sandbox_policy": sandbox_policy,
                "approval_policy": approval_policy,
            },
        )
        return 2
    auth_path, pass_api_key, auth_mode = _auth_material()
    if auth_mode == "unavailable":
        _write_observations(
            observations_path,
            {
                "status": "execution_error",
                "auth_mode": auth_mode,
                "image": image,
                "error": "authentication_unavailable",
                "model": model,
                "reasoning_effort": reasoning_effort,
                "sandbox_policy": sandbox_policy,
                "approval_policy": approval_policy,
            },
        )
        return 2
    with tempfile.TemporaryDirectory(
        prefix="agent-eval-codex-judge-home-"
    ) as temporary:
        temporary_home = Path(temporary)
        os.chmod(temporary_home, 0o700)
        config = (
            'approval_policy = "never"\n'
            'sandbox_mode = "read-only"\n'
            f"model_reasoning_effort = {json.dumps(reasoning_effort)}\n"
        )
        config_path = temporary_home / "config.toml"
        config_path.write_text(config, encoding="utf-8")
        os.chmod(config_path, 0o600)
        if auth_path is not None:
            copied_auth = temporary_home / "auth.json"
            shutil.copyfile(auth_path, copied_auth)
            os.chmod(copied_auth, 0o600)
        command = _docker_with_codex_runtime(
            docker_argv,
            temporary_home=temporary_home,
            image_id=image["image_id"],
            model=model,
            reasoning_effort=reasoning_effort,
        )
        if pass_api_key:
            image_index = _docker_image_index(command)
            command[image_index:image_index] = ["--env", "OPENAI_API_KEY"]
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
            observations = {
                "status": "execution_error",
                "auth_mode": auth_mode,
                "image": image,
                "error": type(exc).__name__,
                "model": model,
                "reasoning_effort": reasoning_effort,
                "sandbox_policy": sandbox_policy,
                "approval_policy": approval_policy,
            }
            _write_observations(observations_path, observations)
            return 2
        stderr = completed.stderr.decode("utf-8", errors="replace")
        if stderr:
            sys.stderr.write(sanitize_diagnostic(stderr, 64_000))
            if not stderr.endswith("\n"):
                sys.stderr.write("\n")
        jsonl, response = _summarize_jsonl(completed.stdout)
        final_response = response or ""
        safe_response = sanitize_diagnostic(final_response, MAX_TEXT_BYTES)
        redacted = safe_response != final_response
        status = "completed"
        if completed.returncode != 0:
            status = "execution_error"
        elif jsonl["status"] != "captured" or redacted:
            status = "evidence_unverified"
        observations: dict[str, Any] = {
            "model": model,
            "reasoning_effort": reasoning_effort,
            "sandbox_policy": sandbox_policy,
            "approval_policy": approval_policy,
            "web_search_enabled": False,
            "tool_policy": "no_cli_tools_or_mcp_configured",
            "auth_mode": auth_mode,
            "image": image,
            "jsonl": jsonl,
            "docker_exit_code": completed.returncode,
            "response_redacted": redacted,
            "response_sha256": sha256_bytes(safe_response.encode("utf-8"))
            if not redacted
            else None,
            "status": status,
        }
        _write_observations(observations_path, observations)
        sys.stdout.write(bounded_text(safe_response, MAX_TEXT_BYTES))
        if safe_response and not safe_response.endswith("\n"):
            sys.stdout.write("\n")
        return 0 if status == "completed" else 2


def launcher_argv(
    *,
    model: str,
    reasoning_effort: str,
    cli_version: str,
    sandbox_policy: str,
    approval_policy: str,
    docker_argv: Sequence[str],
    observations_path: Path,
) -> list[str]:
    return [
        sys.executable,
        str(Path(__file__).resolve()),
        "--model",
        model,
        "--reasoning-effort",
        reasoning_effort,
        "--cli-version",
        cli_version,
        "--sandbox-policy",
        sandbox_policy,
        "--approval-policy",
        approval_policy,
        "--observations-path",
        str(observations_path.resolve()),
        "--",
        *docker_argv,
    ]


def launcher_argv_for_profile(
    judge_profile: dict[str, Any],
    *,
    docker_argv: Sequence[str],
    observations_path: Path,
) -> list[str]:
    """Use the dedicated Codex launcher only for an explicitly pinned Codex Judge."""
    if not is_codex_judge(judge_profile):
        return list(docker_argv)
    disabled = {"none", "disabled", "no-global-config", "no-external-instructions"}
    if (
        judge_profile.get("sandbox_policy") != "read-only"
        or judge_profile.get("approval_policy") != "never"
        or judge_profile.get("launch_options") != []
        or judge_profile.get("tools") != []
        or judge_profile.get("mcp_servers") != []
        or judge_profile.get("skill_roots") != []
        or str(judge_profile.get("global_config", "")).strip().lower() not in disabled
        or str(judge_profile.get("external_instructions", "")).strip().lower()
        not in disabled
    ):
        raise CodexJudgeLauncherError(
            "Codex Judge profile must disable user tools, MCP, Skills, and external configuration"
        )
    return launcher_argv(
        model=str(judge_profile["model"]),
        reasoning_effort=str(judge_profile["reasoning_effort"]),
        cli_version=str(judge_profile["cli_version"]),
        sandbox_policy=str(judge_profile["sandbox_policy"]),
        approval_policy=str(judge_profile["approval_policy"]),
        docker_argv=docker_argv,
        observations_path=observations_path,
    )


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Codex as an isolated Docker Judge."
    )
    parser.add_argument("--model", required=True)
    parser.add_argument("--reasoning-effort", required=True)
    parser.add_argument("--cli-version", required=True)
    parser.add_argument("--sandbox-policy", required=True)
    parser.add_argument("--approval-policy", required=True)
    parser.add_argument("--observations-path", type=Path, required=True)
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
            model=args.model,
            reasoning_effort=args.reasoning_effort,
            cli_version=args.cli_version,
            sandbox_policy=args.sandbox_policy,
            approval_policy=args.approval_policy,
            docker_argv=args.docker_argv,
            prompt=sys.stdin.read(),
            observations_path=args.observations_path,
        )
    except (CodexJudgeLauncherError, OSError, UnicodeError, ValueError) as exc:
        print(f"codex Judge launcher error: {type(exc).__name__}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
