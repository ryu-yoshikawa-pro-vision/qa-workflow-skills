from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from .common import (
    AgentEvalError,
    atomic_write_json,
    canonical_fingerprint,
    prepare_run_output_root,
    sanitize_diagnostic,
)
from .workspace import (
    assert_clean_checkout,
    load_execution_profile,
    profile_fingerprint,
    verify_agent_docker_command,
    verify_judge_docker_command,
)

REPO_ROOT = Path(__file__).resolve().parents[4]
_FORBIDDEN_TOOL_RE = re.compile(r"(?i)(web|browser|search|mcp)")


def _read_argv(path: Path) -> list[str]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AgentEvalError(
            "container command template must be a JSON argv array"
        ) from exc
    if (
        not isinstance(value, list)
        or not value
        or any(not isinstance(item, str) or not item for item in value)
    ):
        raise AgentEvalError(
            "container command template must contain non-empty strings"
        )
    return value


def _docker_image_index(argv: list[str]) -> int:
    value_options = {
        "--network",
        "--mount",
        "--workdir",
        "-w",
        "-e",
        "--env",
        "--env-file",
        "--name",
        "--user",
        "--entrypoint",
        "--memory",
        "--cpus",
        "--security-opt",
        "--cap-drop",
    }
    flag_options = {"--rm", "--read-only", "-i", "-t", "-d", "--init"}
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
            raise AgentEvalError("cannot identify Docker image from command template")
        return index
    raise AgentEvalError("Docker run template has no image")


def _docker_image(argv: list[str]) -> str:
    return argv[_docker_image_index(argv)]


def _live_mount_probe(argv: list[str], *, evaluator_sentinel: Path) -> dict[str, Any]:
    image_index = _docker_image_index(argv)
    image = argv[image_index]
    prefix: list[str] = []
    index = 0
    while index < image_index:
        token = argv[index]
        if token == "--entrypoint":
            index += 2
            continue
        if token.startswith("--entrypoint="):
            index += 1
            continue
        prefix.append(token)
        index += 1
    sentinel_target = "/.qa-eval-sentinel-" + os.urandom(8).hex()
    control_name = "agent-eval-sentinel-control-" + os.urandom(4).hex()
    control_script = f'test -r {sentinel_target} && test "$(cat {sentinel_target})" = isolation-sentinel'
    control = [
        argv[0],
        "run",
        "--rm",
        "--read-only",
        "--network",
        "none",
        "--mount",
        f"type=bind,source={evaluator_sentinel},target={sentinel_target},readonly",
        "--name",
        control_name,
        "--entrypoint",
        "/bin/sh",
        image,
        "-c",
        control_script,
    ]
    control_cleanup = [argv[0], "rm", "-f", control_name]
    try:
        control_result = subprocess.run(
            control,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=30,
            check=False,
            shell=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        try:
            subprocess.run(
                control_cleanup,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=10,
                check=False,
                shell=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            pass
        return {
            "status": "unverified",
            "reason": f"sentinel_control_{type(exc).__name__}",
        }
    if control_result.returncode != 0:
        return {"status": "unverified", "reason": "sentinel_control_failed"}

    name = "agent-eval-isolation-" + os.urandom(4).hex()
    script = (
        "set -eu; "
        f"if test -r {sentinel_target}; then exit 21; fi; "
        "if (printf probe > /workspace/.agent-eval-source-write-probe) 2>/dev/null; then exit 22; fi; "
        "printf probe > /workspace/.qa-eval-output/.isolation-probe; "
        "test -s /workspace/.qa-eval-output/.isolation-probe; "
        "rm -f /workspace/.qa-eval-output/.isolation-probe; "
        "printf 'isolation-probe:ok\\n'"
    )
    probe = [*prefix, "--name", name, "--entrypoint", "/bin/sh", image, "-c", script]
    cleanup = [argv[0], "rm", "-f", name]
    try:
        completed = subprocess.run(
            probe,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
            check=False,
            shell=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        try:
            subprocess.run(
                cleanup,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=10,
                check=False,
                shell=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            pass
        return {"status": "unverified", "reason": type(exc).__name__}
    output = completed.stdout.decode("utf-8", errors="replace").strip()
    verified = completed.returncode == 0 and output == "isolation-probe:ok"
    cleanup_status = "not_required"
    return {
        "status": "verified" if verified else "unverified",
        "return_code": completed.returncode,
        "expected_marker": verified,
        "cleanup_status": cleanup_status,
        "checks": {
            "evaluator_sentinel_unreadable": verified
            and control_result.returncode == 0,
            "sentinel_control_readable": control_result.returncode == 0,
            "workspace_write_denied": verified,
            "output_write_allowed": verified,
        },
    }


def _check_docker_runtime(images: set[str]) -> dict[str, Any]:
    try:
        server = subprocess.run(
            ["docker", "info", "--format", "{{.ServerVersion}}"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=15,
            check=False,
            shell=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"available": False, "reason": type(exc).__name__, "images": {}}
    if server.returncode != 0:
        return {"available": False, "reason": "docker_server_unavailable", "images": {}}
    image_results: dict[str, bool] = {}
    for image in sorted(images):
        try:
            inspected = subprocess.run(
                ["docker", "image", "inspect", image],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=15,
                check=False,
                shell=False,
            )
            image_results[canonical_fingerprint(image)] = inspected.returncode == 0
        except (OSError, subprocess.TimeoutExpired):
            image_results[canonical_fingerprint(image)] = False
    return {
        "available": all(image_results.values()),
        "server_available": True,
        "images": image_results,
    }


def probe_isolation(
    *, profile_path: Path, agent_command_path: Path, output_root: Path
) -> dict[str, Any]:
    profile = load_execution_profile(profile_path)
    output_root = Path(os.path.abspath(output_root))
    evidence_path = prepare_run_output_root(
        output_root,
        repository_root=REPO_ROOT,
        evidence_relative_path=profile["verification"]["evidence_path"],
    )

    checks: dict[str, bool] = {
        "evaluator_read_denied": False,
        "source_write_denied": False,
        "extra_tools_disabled": False,
        "mounts_reviewed": False,
    }
    details: dict[str, Any] = {}
    try:
        agent_template = _read_argv(agent_command_path)
        with tempfile.TemporaryDirectory(prefix="qa-agent-isolation-") as temporary:
            base = Path(temporary)
            workspace = base / "workspace"
            output = base / "output"
            workspace.mkdir()
            output.mkdir()
            (workspace / ".agents" / "skills").mkdir(parents=True)
            (workspace / ".qa-eval-output").mkdir()
            replacements = {
                "{workspace}": str(workspace),
                "{output_root}": str(output),
                "{agent_output_root}": str(output),
            }
            agent_command = [
                item.replace("{workspace}", replacements["{workspace}"])
                .replace("{output_root}", replacements["{output_root}"])
                .replace("{agent_output_root}", replacements["{agent_output_root}"])
                for item in agent_template
            ]
            agent_isolation = verify_agent_docker_command(
                agent_command,
                workspace=workspace,
                output_root=output,
                evaluator_root=REPO_ROOT,
            )
            judge_isolation = verify_judge_docker_command(
                profile["judge"]["command_argv"], evaluator_root=REPO_ROOT
            )
            docker_runtime = _check_docker_runtime(
                {
                    _docker_image(agent_command),
                    _docker_image(profile["judge"]["command_argv"]),
                }
            )
            if docker_runtime["available"]:
                sentinel_root = REPO_ROOT / ".agent-eval-runs"
                sentinel_root.mkdir(parents=True, exist_ok=True)
                with tempfile.TemporaryDirectory(
                    prefix="agent-eval-sentinel-", dir=sentinel_root
                ) as sentinel_dir:
                    evaluator_sentinel = Path(sentinel_dir) / "sentinel.txt"
                    evaluator_sentinel.write_text(
                        "isolation-sentinel", encoding="utf-8"
                    )
                    live_mounts = _live_mount_probe(
                        agent_command, evaluator_sentinel=evaluator_sentinel
                    )
            else:
                live_mounts = {
                    "status": "unverified",
                    "reason": "docker_engine_or_required_image_unavailable",
                    "checks": {},
                }
        no_host_config = profile["agent"]["global_config"].strip().lower() in {
            "none",
            "disabled",
            "no-global-config",
        }
        no_external_instruction = profile["agent"][
            "external_instructions"
        ].strip().lower() in {"none", "disabled", "no-external-instructions"}
        agent_skill_roots = profile["agent"]["skill_roots"] == [
            "/workspace/.agents/skills"
        ]
        safe_tools = not any(
            _FORBIDDEN_TOOL_RE.search(item) for item in profile["agent"]["tools"]
        )
        judge_disabled = (
            profile["judge"]["tools"] == []
            and profile["judge"]["mcp_servers"] == []
            and profile["judge"]["skill_roots"] == []
            and profile["judge"]["global_config"].strip().lower()
            in {"none", "disabled", "no-global-config"}
            and profile["judge"]["external_instructions"].strip().lower()
            in {"none", "disabled", "no-external-instructions"}
        )
        checks = {
            "evaluator_read_denied": agent_isolation["evaluator_bind_mounts"] == 0
            and judge_isolation["host_bind_mounts"] == 0
            and live_mounts["checks"].get("evaluator_sentinel_unreadable") is True,
            "source_write_denied": agent_isolation["workspace_read_only"]
            and agent_isolation["root_filesystem_read_only"]
            and live_mounts["checks"].get("workspace_write_denied") is True,
            "extra_tools_disabled": safe_tools
            and not profile["agent"]["mcp_servers"]
            and agent_skill_roots
            and judge_disabled,
            "mounts_reviewed": agent_isolation["output_only_writable_bind"]
            and agent_isolation["evaluator_bind_mounts"] == 0
            and judge_isolation["host_bind_mounts"] == 0
            and no_host_config
            and no_external_instruction
            and docker_runtime["available"]
            and live_mounts["status"] == "verified",
        }
        details = {
            "agent_mount_check": agent_isolation,
            "judge_mount_check": judge_isolation,
            "docker_runtime_check": docker_runtime,
            "live_mount_probe": live_mounts,
            "candidate_skill_root_only": agent_skill_roots,
            "agent_global_config_disabled": no_host_config,
            "agent_external_instructions_disabled": no_external_instruction,
            "network_policy": profile["agent"]["network_policy"],
            "public_egress_control": "not_verified; model API network access may allow public egress",
        }
    except (AgentEvalError, OSError, KeyError) as exc:
        details = {
            "probe_error": sanitize_diagnostic(f"{type(exc).__name__}: {exc}", 1000)
        }

    evidence: dict[str, Any] = {
        "schema_version": 1,
        "status": "verified" if all(checks.values()) else "unverified",
        "probe": "scripts/skills/evals/agent/isolation_probe.py",
        "probe_version": 1,
        "evaluator_revision": None,
        "profile_fingerprint": profile_fingerprint(profile),
        "agent_command_fingerprint": None,
        "judge_command_fingerprint": canonical_fingerprint(
            profile["judge"]["command_argv"]
        ),
        "checks": checks,
        "details": details,
    }
    try:
        evidence["evaluator_revision"] = assert_clean_checkout(REPO_ROOT)
        evidence["agent_command_fingerprint"] = canonical_fingerprint(
            _read_argv(agent_command_path)
        )
    except AgentEvalError as exc:
        evidence["status"] = "unverified"
        evidence["checks"]["mounts_reviewed"] = False
        evidence["details"]["revision_error"] = sanitize_diagnostic(str(exc), 500)
    atomic_write_json(evidence_path, evidence)
    return evidence


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Audit Agent and Judge container mount isolation and write run evidence."
    )
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--agent-command-json", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        evidence = probe_isolation(
            profile_path=args.profile,
            agent_command_path=args.agent_command_json,
            output_root=args.output_root,
        )
    except (AgentEvalError, OSError, ValueError) as exc:
        print(
            f"isolation probe failed: {sanitize_diagnostic(str(exc), 1000)}",
            file=sys.stderr,
        )
        return 2
    print(
        json.dumps(
            {
                "status": evidence["status"],
                "profile_fingerprint": evidence["profile_fingerprint"],
            },
            ensure_ascii=True,
        )
    )
    return 0 if evidence["status"] == "verified" else 1


if __name__ == "__main__":
    raise SystemExit(main())
