from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from .common import (
    AgentEvalError,
    atomic_write_json,
    canonical_fingerprint,
    prepare_run_output_root,
    sanitize_diagnostic,
)
from .tools.codex_wsl2_bwrap_launcher import (
    PROTOCOL as WSL2_LAUNCHER_PROTOCOL,
)
from .tools.codex_wsl2_bwrap_launcher import (
    CodexWsl2LauncherError,
    expected_codex_exec_argv_fingerprint,
    sandbox_smoke,
    timeout_cleanup_smoke,
    verify_runtime,
)
from .workspace import (
    assert_clean_checkout,
    load_execution_profile,
    profile_fingerprint,
    verify_agent_docker_command,
    verify_agent_wsl2_command,
    verify_judge_docker_command,
    verify_judge_wsl2_command,
    verify_repair_wsl2_command,
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
    probe = [
        *prefix,
        "--user",
        f"{os.getuid()}:{os.getgid()}",
        "--name",
        name,
        "--entrypoint",
        "/bin/sh",
        image,
        "-c",
        script,
    ]
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
    diagnostic = sanitize_diagnostic(
        completed.stderr.decode("utf-8", errors="replace"), 1000
    ).strip()
    cleanup_status = "not_required"
    return {
        "status": "verified" if verified else "unverified",
        "return_code": completed.returncode,
        "expected_marker": verified,
        "cleanup_status": cleanup_status,
        "diagnostic": diagnostic if not verified and diagnostic else None,
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


def probe_wsl2_isolation(
    *, profile_path: Path, agent_command_path: Path, output_root: Path
) -> dict[str, Any]:
    profile = load_execution_profile(profile_path)
    output_root = Path(os.path.abspath(output_root))
    evidence_path = prepare_run_output_root(
        output_root,
        repository_root=REPO_ROOT,
        evidence_relative_path=profile["verification"]["evidence_path"],
    )
    command = _read_argv(agent_command_path)
    required = {
        "evaluator_read_denied",
        "authentication_shell_read_denied",
        "host_home_read_denied",
        "other_attempt_home_read_denied",
        "windows_filesystem_read_denied",
        "source_write_denied",
        "output_write_allowed",
        "inherited_fd_denied",
        "symlink_escape_denied",
        "fresh_procfs",
        "nested_namespaces",
        "inner_shell_network_blocked",
        "extra_tools_disabled",
        "mounts_reviewed",
        "agent_judge_separated",
        "timeout_cleanup",
    }
    checks = {key: False for key in required}
    runtime: dict[str, Any] = {}
    details: dict[str, Any] = {
        "protocol": WSL2_LAUNCHER_PROTOCOL,
        "model_api_used": False,
        "authentication_shell_visible_risk": True,
    }
    mode_evidence: dict[str, Any] = {}
    timeout_evidence: dict[str, Any] = {}
    try:
        if profile.get("schema_version") != 2 or command != ["codex"]:
            raise AgentEvalError(
                "WSL2 evidence requires schema 2 and the fixed Codex template"
            )
        agent_contract: dict[str, Any] = {}
        judge_contract = verify_judge_wsl2_command(
            profile["judge"]["command_argv"], evaluator_root=REPO_ROOT
        )
        runtime = verify_runtime()
        with tempfile.TemporaryDirectory(prefix="qa-wsl2-isolation-") as temporary:
            base = Path(temporary)
            smoke_specs: dict[str, dict[str, Any]] = {}
            for mode in ("agent", "repair"):
                workspace = base / mode / "workspace"
                workspace.mkdir(parents=True)
                (workspace / "protected.txt").write_text(
                    "synthetic-source\n", encoding="utf-8"
                )
                (workspace / ".agents" / "skills").mkdir(parents=True)
                (workspace / ".qa-eval-output").mkdir()
                output = (
                    workspace / ".qa-eval-output"
                    if mode == "repair"
                    else base / mode / "output"
                )
                output.mkdir(exist_ok=True)
                skill_root = None
                skill_name = None
                if mode == "agent":
                    agent_contract = verify_agent_wsl2_command(
                        command,
                        workspace=workspace,
                        output_root=output,
                        evaluator_root=REPO_ROOT,
                    )
                else:
                    skill_name = "synthetic-skill"
                    skill_root = workspace / ".agents" / "skills" / skill_name
                    skill_root.mkdir(parents=True)
                    (skill_root / "SKILL.md").write_text(
                        "synthetic skill\n", encoding="utf-8"
                    )
                    verify_repair_wsl2_command(
                        command,
                        workspace=workspace,
                        skill_root=skill_root,
                        output_root=output,
                        skill_name=skill_name,
                    )
                smoke_specs[mode] = {
                    "mode": mode,
                    "workspace_root": workspace,
                    "output_root": output,
                    "skill_root": skill_root,
                    "skill_name": skill_name,
                    "permission_profile": ":workspace",
                }
            smoke_specs["judge"] = {
                "mode": "judge",
                "workspace_root": None,
                "output_root": None,
                "permission_profile": ":read-only",
            }
            with ThreadPoolExecutor(max_workers=3) as pool:
                futures = {
                    pool.submit(sandbox_smoke, **spec): name
                    for name, spec in smoke_specs.items()
                }
                for future in as_completed(futures):
                    name = futures[future]
                    mode_evidence[name] = future.result()
                    mode_evidence[name]["profile_fingerprint"] = profile_fingerprint(
                        profile
                    )
                    command_profile = (
                        profile["judge"] if name == "judge" else profile["agent"]
                    )
                    mode_evidence[name]["codex_exec_argv_fingerprint"] = (
                        expected_codex_exec_argv_fingerprint(
                            mode=name,
                            model=command_profile["model"],
                            reasoning_effort=command_profile["reasoning_effort"],
                            sandbox_policy=command_profile["sandbox_policy"],
                        )
                    )

            timeout_workspace = base / "timeout" / "workspace"
            timeout_workspace.mkdir(parents=True)
            (timeout_workspace / "protected.txt").write_text(
                "synthetic-source\n", encoding="utf-8"
            )
            (timeout_workspace / ".agents" / "skills").mkdir(parents=True)
            (timeout_workspace / ".qa-eval-output").mkdir()
            timeout_output = base / "timeout" / "output"
            timeout_output.mkdir()
            timeout_evidence = timeout_cleanup_smoke(
                workspace_root=timeout_workspace,
                output_root=timeout_output,
            )

        mode_checks = [item.get("checks", {}) for item in mode_evidence.values()]
        agent_checks = mode_evidence["agent"].get("checks", {})
        repair_checks = mode_evidence["repair"].get("checks", {})
        checks.update(
            {
                "evaluator_read_denied": all(
                    c.get("evaluator_sentinel_read_denied") is True
                    and c.get("evaluator_checkout_unmounted") is True
                    for c in mode_checks
                ),
                "authentication_shell_read_denied": all(
                    all(
                        c.get(check) is True
                        for check in (
                            "authentication_store_read_denied",
                            "authentication_store_host_path_hidden",
                            "other_attempt_auth_store_hidden",
                            "authentication_marker_absent_from_environment",
                            "authentication_marker_absent_from_process_fds",
                        )
                    )
                    for c in mode_checks
                ),
                "host_home_read_denied": all(
                    c.get("outer_host_paths_hidden") is True
                    and c.get("inner_host_paths_hidden") is True
                    for c in mode_checks
                ),
                "other_attempt_home_read_denied": all(
                    c.get("outer_host_paths_hidden") is True
                    and c.get("inner_host_paths_hidden") is True
                    for c in mode_checks
                ),
                "windows_filesystem_read_denied": all(
                    c.get("wsl_interop_blocked") is True for c in mode_checks
                ),
                "source_write_denied": agent_checks.get("source_write_denied") is True
                and repair_checks.get("source_write_denied") is True,
                "output_write_allowed": agent_checks.get("output_write_allowed") is True
                and repair_checks.get("output_write_allowed") is True,
                "inherited_fd_denied": all(
                    c.get("fd_noninheritance") is True for c in mode_checks
                ),
                "symlink_escape_denied": agent_checks.get("symlink_escape_denied")
                is True
                and repair_checks.get("symlink_escape_denied") is True,
                "fresh_procfs": all(
                    c.get("outer_procfs") is True and c.get("inner_procfs") is True
                    for c in mode_checks
                ),
                "nested_namespaces": all(
                    c.get("nested_namespaces") is True for c in mode_checks
                ),
                "inner_shell_network_blocked": all(
                    c.get(name) is True
                    for c in mode_checks
                    for name in (
                        "inner_tcp_blocked",
                        "inner_localhost_blocked",
                        "inner_af_unix_blocked",
                        "inner_dns_blocked",
                        "wsl_interop_blocked",
                    )
                ),
                "extra_tools_disabled": (
                    profile["agent"]["tools"] == ["shell"]
                    and profile["agent"]["mcp_servers"] == []
                    and profile["agent"]["launch_options"] == []
                    and profile["judge"]["tools"] == []
                    and profile["judge"]["mcp_servers"] == []
                    and profile["judge"]["skill_roots"] == []
                    and profile["judge"]["launch_options"] == []
                ),
                "mounts_reviewed": agent_contract.get("execution_method")
                == "wsl2-dual-bubblewrap"
                and judge_contract.get("execution_method") == "wsl2-dual-bubblewrap"
                and mode_evidence.get("agent", {})
                .get("effective", {})
                .get("mounts", {})
                .get("workspace", {})
                .get("access")
                == "writable-root-with-read-only-source-children"
                and ".agents"
                in mode_evidence.get("agent", {})
                .get("effective", {})
                .get("mounts", {})
                .get("workspace", {})
                .get("read_only_source_entries", [])
                and mode_evidence.get("agent", {})
                .get("effective", {})
                .get("mounts", {})
                .get("output", {})
                .get("access")
                == "read-write"
                and mode_evidence.get("agent", {})
                .get("effective", {})
                .get("mounts", {})
                .get("codex_scratch", {})
                .get("attempt_local")
                is True
                and mode_evidence.get("repair", {})
                .get("effective", {})
                .get("mounts", {})
                .get("writable_skill")
                == "synthetic-skill"
                and mode_evidence.get("judge", {})
                .get("effective", {})
                .get("mounts", {})
                .get("workspace")
                is None
                and all(
                    item.get("effective", {}).get("mounts", {}).get("host_home")
                    is False
                    and item.get("effective", {})
                    .get("mounts", {})
                    .get("evaluator_checkout")
                    is False
                    and item.get("effective", {}).get("mounts", {}).get("docker_socket")
                    is False
                    for item in mode_evidence.values()
                ),
                "agent_judge_separated": (
                    all(
                        mode_evidence.get(name, {}).get("mode") == name
                        and mode_evidence.get(name, {}).get("status") == "verified"
                        and mode_evidence.get(name, {}).get("profile_fingerprint")
                        == profile_fingerprint(profile)
                        for name in ("agent", "judge", "repair")
                    )
                    and mode_evidence.get("agent", {})
                    .get("effective", {})
                    .get("codex_home_fingerprint")
                    != mode_evidence.get("judge", {})
                    .get("effective", {})
                    .get("codex_home_fingerprint")
                    and all(
                        mode_evidence.get("agent", {})
                        .get("outer", {})
                        .get("namespaces", {})
                        .get(namespace)
                        != mode_evidence.get("judge", {})
                        .get("outer", {})
                        .get("namespaces", {})
                        .get(namespace)
                        for namespace in ("user", "pid", "mnt", "ipc", "uts")
                    )
                ),
                "timeout_cleanup": timeout_evidence.get("status") == "verified"
                and all(timeout_evidence.get("checks", {}).values()),
            }
        )
        details.update(
            {
                "agent_contract": agent_contract,
                "judge_contract": judge_contract,
                "mode_evidence": mode_evidence,
                "timeout_evidence": timeout_evidence,
                "profile_tool_config": {
                    "agent_tools": profile["agent"]["tools"],
                    "agent_mcp_servers": profile["agent"]["mcp_servers"],
                    "judge_tools": profile["judge"]["tools"],
                    "judge_mcp_servers": profile["judge"]["mcp_servers"],
                    "web_search": "disabled by WSL2 launcher config",
                },
                "network_boundary": "outer Codex parent retains host network; inner shell probes are separate",
            }
        )
    except (AgentEvalError, CodexWsl2LauncherError, OSError, KeyError) as exc:
        details["probe_error"] = sanitize_diagnostic(
            f"{type(exc).__name__}: {exc}", 1000
        )
    try:
        evaluator_revision = assert_clean_checkout(REPO_ROOT)
    except AgentEvalError as exc:
        evaluator_revision = None
        details["revision_error"] = sanitize_diagnostic(str(exc), 500)
    evidence = {
        "schema_version": 2,
        "execution_method": "wsl2-dual-bubblewrap",
        "status": "verified"
        if all(checks.values()) and evaluator_revision
        else "unverified",
        "probe": "scripts/skills/evals/agent/isolation_probe.py",
        "probe_version": 2,
        "evaluator_revision": evaluator_revision,
        "profile_fingerprint": profile_fingerprint(profile),
        "agent_command_fingerprint": canonical_fingerprint(command),
        "judge_command_fingerprint": canonical_fingerprint(
            profile["judge"]["command_argv"]
        ),
        "runtime": runtime,
        "checks": checks,
        "mode_evidence": mode_evidence,
        "details": details,
    }
    atomic_write_json(evidence_path, evidence)
    return evidence


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Audit WSL2 dual-bubblewrap isolation and write run evidence."
    )
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--agent-command-json", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        evidence = probe_wsl2_isolation(
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
