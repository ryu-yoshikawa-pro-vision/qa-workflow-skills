from __future__ import annotations

import io
import json
import re
import subprocess
import tarfile
from pathlib import Path, PurePosixPath
from typing import Any

from .common import AgentEvalError, canonical_fingerprint, sha256_bytes

REPO_ROOT = Path(__file__).resolve().parents[4]
FULL_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
ALLOWED_PACKAGE_AREAS = {"references", "scripts", "assets"}
_SENSITIVE_ARG_RE = re.compile(
    r"(?i)(?:^|[=:_-])(token|secret|password|api[_-]?key|credential)(?:$|[=:_-])"
)


def _git(root: Path, *args: str, timeout: int = 30) -> str:
    completed = subprocess.run(
        ["git", "-c", f"safe.directory={root.resolve()}", "-C", str(root), *args],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
        shell=False,
    )
    if completed.returncode != 0:
        raise AgentEvalError(f"git {args[0]} failed: {completed.stderr.strip()[:500]}")
    return completed.stdout


def resolve_commit(root: Path, revision: str) -> str:
    if not FULL_SHA_RE.fullmatch(revision):
        raise AgentEvalError("revision must be a full 40-character lowercase Git SHA")
    resolved = _git(root, "rev-parse", "--verify", f"{revision}^{{commit}}").strip()
    if resolved != revision:
        raise AgentEvalError("revision did not resolve to the requested full SHA")
    return resolved


def assert_clean_checkout(root: Path, *, expected_revision: str | None = None) -> str:
    root = root.resolve()
    if not (root / ".git").exists() and not (root / ".git").is_file():
        raise AgentEvalError("repository root must be a Git working tree")
    head = _git(root, "rev-parse", "--verify", "HEAD").strip()
    if expected_revision is not None and head != expected_revision:
        raise AgentEvalError("Git working tree HEAD does not match the required revision")
    status = _git(root, "status", "--porcelain=v1", "--untracked-files=all")
    if status.strip():
        raise AgentEvalError("Git working tree and index must be clean")
    return head


def load_execution_profile(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AgentEvalError(f"execution profile is unreadable: {type(exc).__name__}") from exc
    _validate_profile(value)
    return value


def _required_object(value: Any, keys: set[str], name: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise AgentEvalError(f"execution profile {name} has invalid fields")
    return value


def _nonempty(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise AgentEvalError(f"execution profile {name} must be a non-empty string")
    return value


def _positive_int(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise AgentEvalError(f"execution profile {name} must be a positive integer")
    return value


def _string_list(value: Any, name: str, *, allow_empty: bool = True) -> list[str]:
    if not isinstance(value, list) or (not allow_empty and not value):
        raise AgentEvalError(f"execution profile {name} must be a string array")
    if any(not isinstance(item, str) or not item for item in value):
        raise AgentEvalError(f"execution profile {name} must contain non-empty strings")
    return value


def _assert_no_sensitive_argv(value: list[str], name: str) -> None:
    for argument in value:
        if _SENSITIVE_ARG_RE.search(argument):
            raise AgentEvalError(f"execution profile {name} may not include credentials")


def _validate_profile(value: Any) -> None:
    root = _required_object(
        value, {"schema_version", "agent", "judge", "isolation", "verification"}, "root"
    )
    if root["schema_version"] != 1:
        raise AgentEvalError("execution profile schema_version must be 1")
    agent = _required_object(
        root["agent"],
        {
            "name", "model", "timeout_seconds", "cli_version", "reasoning_effort",
            "launch_options", "sandbox_policy", "approval_policy", "network_policy",
            "tools", "mcp_servers", "skill_roots", "external_instructions", "global_config",
        },
        "agent",
    )
    for field in (
        "name", "model", "cli_version", "reasoning_effort", "sandbox_policy",
        "approval_policy", "network_policy", "external_instructions", "global_config",
    ):
        _nonempty(agent[field], f"agent.{field}")
    _positive_int(agent["timeout_seconds"], "agent.timeout_seconds")
    for field in ("launch_options", "tools", "mcp_servers", "skill_roots"):
        _string_list(agent[field], f"agent.{field}")

    judge = _required_object(
        root["judge"],
        {
            "model", "command_argv", "cwd", "timeout_seconds", "cli_version",
            "reasoning_effort", "launch_options", "sandbox_policy", "approval_policy",
            "network_policy", "skill_roots", "global_config", "tools", "mcp_servers",
            "external_instructions",
        },
        "judge",
    )
    for field in (
        "model", "cwd", "cli_version", "reasoning_effort", "sandbox_policy",
        "approval_policy", "network_policy", "global_config", "external_instructions",
    ):
        _nonempty(judge[field], f"judge.{field}")
    _positive_int(judge["timeout_seconds"], "judge.timeout_seconds")
    argv = _string_list(judge["command_argv"], "judge.command_argv", allow_empty=False)
    _assert_no_sensitive_argv(argv, "judge.command_argv")
    for field in ("launch_options", "skill_roots", "tools", "mcp_servers"):
        _string_list(judge[field], f"judge.{field}")

    isolation = _required_object(
        root["isolation"], {"method", "agent_read_roots", "evaluator_read_blocked"}, "isolation"
    )
    _nonempty(isolation["method"], "isolation.method")
    _string_list(isolation["agent_read_roots"], "isolation.agent_read_roots", allow_empty=False)
    if isolation["evaluator_read_blocked"] is not True:
        raise AgentEvalError("execution profile must declare evaluator read access blocked")

    verification = _required_object(
        root["verification"], {"status", "method", "evidence_path"}, "verification"
    )
    if verification["status"] not in {"verified", "unverified"}:
        raise AgentEvalError("verification.status must be verified or unverified")
    _nonempty(verification["method"], "verification.method")
    if verification["status"] == "verified":
        _nonempty(verification["evidence_path"], "verification.evidence_path")
    elif verification["evidence_path"] is not None and not isinstance(
        verification["evidence_path"], str
    ):
        raise AgentEvalError("verification.evidence_path must be a string or null")


def verify_profile_evidence(
    profile: dict[str, Any],
    output_root: Path,
    *,
    agent_command_argv: list[str] | None = None,
) -> bool:
    verification = profile["verification"]
    if verification["status"] != "verified":
        return False
    evidence_path = Path(verification["evidence_path"])
    if evidence_path.is_absolute() or ".." in evidence_path.parts:
        raise AgentEvalError("verification evidence path must stay under output root")
    evidence_path = (output_root / evidence_path).resolve()
    try:
        evidence_path.relative_to(output_root.resolve())
    except ValueError as exc:
        raise AgentEvalError("verification evidence path escapes output root") from exc
    try:
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AgentEvalError("verified profile evidence is missing or invalid") from exc
    if not isinstance(evidence, dict):
        raise AgentEvalError("profile evidence must be a JSON object")
    checks = evidence.get("checks")
    required = {
        "evaluator_read_denied",
        "source_write_denied",
        "extra_tools_disabled",
        "mounts_reviewed",
    }
    if (
        evidence.get("status") != "verified"
        or evidence.get("probe") != "scripts/skills/evals/agent/isolation_probe.py"
        or evidence.get("profile_fingerprint") != profile_fingerprint(profile)
        or evidence.get("judge_command_fingerprint")
        != canonical_fingerprint(profile["judge"]["command_argv"])
        or (
            agent_command_argv is not None
            and evidence.get("agent_command_fingerprint")
            != canonical_fingerprint(agent_command_argv)
        )
        or not isinstance(checks, dict)
        or not required.issubset(checks)
        or any(checks[key] is not True for key in required)
    ):
        raise AgentEvalError("profile evidence does not verify required isolation checks")
    if evidence.get("evaluator_revision") != assert_clean_checkout(REPO_ROOT):
        raise AgentEvalError("profile evidence belongs to a different Evaluator revision")
    return True


def _codex_home_from_argv(argv: list[str]) -> str | None:
    index = 0
    while index < len(argv):
        token = argv[index]
        if token in {"-e", "--env"} and index + 1 < len(argv):
            item = argv[index + 1]
            index += 2
        elif token.startswith("--env="):
            item = token.split("=", 1)[1]
            index += 1
        elif token.startswith("-e") and len(token) > 2:
            item = token[2:]
            index += 1
        else:
            index += 1
            continue
        name, separator, value = item.partition("=")
        if name == "CODEX_HOME" and separator:
            return value
    return None


def _approved_agent_tmpfs(target: Any, codex_home: str | None) -> bool:
    return target == "/tmp" or (
        target in {"/codex-home", "/tmp/codex-home"} and codex_home == target
    )


def verify_agent_docker_command(
    argv: list[str],
    *,
    workspace: Path,
    output_root: Path,
    evaluator_root: Path,
) -> dict[str, Any]:
    """Require a direct Docker argv with a read-only Agent workspace and one output mount."""
    if len(argv) < 3 or Path(argv[0]).name.lower() not in {"docker", "docker.exe"} or argv[1] != "run":
        raise AgentEvalError("live Agent command must start with direct 'docker run'")
    if "--rm" not in argv or "--read-only" not in argv:
        raise AgentEvalError("Agent container must be disposable with a read-only root filesystem")
    workdir = _option_value(argv, "--workdir") or _option_value(argv, "-w")
    if workdir != "/workspace":
        raise AgentEvalError("Agent container working directory must be /workspace")
    if "--privileged" in argv or "host" in (_option_value(argv, "--network") or ""):
        raise AgentEvalError("Agent container may not use privileged or host-network access")
    if any(item in {"-v", "--volume"} or item.startswith("--volume=") for item in argv):
        raise AgentEvalError("Agent container must use auditable --mount entries, not volume aliases")
    if any(item in {"--device", "--devices", "--volumes-from", "--cap-add"} or item.startswith(("--device=", "--volumes-from=", "--cap-add=")) for item in argv):
        raise AgentEvalError("Agent container may not add host devices, volumes, or capabilities")
    if any(_option_value(argv, option) == "host" for option in ("--pid", "--ipc", "--uts", "--cgroupns")):
        raise AgentEvalError("Agent container may not join host namespaces")
    if any(item == "--tmpfs" or item.startswith("--tmpfs=") for item in argv):
        raise AgentEvalError("Agent tmpfs mounts must use auditable --mount entries")
    codex_home = _codex_home_from_argv(argv)
    mounts: list[dict[str, str | bool]] = []
    index = 0
    while index < len(argv):
        token = argv[index]
        if token == "--mount" and index + 1 < len(argv):
            value = argv[index + 1]
            index += 2
        elif token.startswith("--mount="):
            value = token.split("=", 1)[1]
            index += 1
        else:
            index += 1
            continue
        parts = value.split(",")
        fields: dict[str, str | bool] = {}
        for part in parts:
            key, separator, content = part.partition("=")
            if separator:
                fields[key] = content
            else:
                fields[key] = True
        mount_type = fields.get("type")
        if mount_type == "tmpfs":
            target = fields.get("target")
            if _approved_agent_tmpfs(target, codex_home):
                continue
            raise AgentEvalError("Agent tmpfs mounts may cover only /tmp or the explicitly configured temporary CODEX_HOME")
        if mount_type != "bind":
            raise AgentEvalError("Agent container may use only approved bind and tmpfs mounts")
        if not isinstance(fields.get("source"), str) or not isinstance(fields.get("target"), str):
            raise AgentEvalError("Agent bind mount is missing source or target")
        mounts.append(fields)
    workspace_path = workspace.resolve()
    output_path = output_root.resolve()
    evaluator_path = evaluator_root.resolve()
    read_only_workspace = False
    writable_output = False
    for mount in mounts:
        source = Path(str(mount["source"])).resolve()
        target = str(mount["target"])
        read_only = mount.get("readonly") is True or mount.get("ro") is True
        if source == workspace_path and target == "/workspace" and read_only:
            read_only_workspace = True
            continue
        if source == output_path and target == "/workspace/.qa-eval-output" and not read_only:
            writable_output = True
            continue
        if source == evaluator_path or evaluator_path in source.parents:
            raise AgentEvalError("Agent command mounts evaluator-owned files outside the output root")
        raise AgentEvalError("Agent command contains an unapproved bind mount")
    if len(mounts) != 2 or not read_only_workspace or not writable_output:
        raise AgentEvalError("Agent command must mount only a read-only workspace and writable .qa-eval-output")
    network = _option_value(argv, "--network")
    if network == "host":
        raise AgentEvalError("Agent container may not use host networking")
    return {
        "status": "verified",
        "workspace_read_only": True,
        "output_only_writable_bind": True,
        "evaluator_bind_mounts": 0,
        "root_filesystem_read_only": True,
        "network": network or "docker-default",
        "public_egress_control": "not_verified_by_container_mount_check",
    }


def verify_judge_docker_command(argv: list[str], *, evaluator_root: Path) -> dict[str, Any]:
    """Require a fresh Judge container that receives only the prompt over stdin."""
    if len(argv) < 3 or Path(argv[0]).name.lower() not in {"docker", "docker.exe"} or argv[1] != "run":
        raise AgentEvalError("live Judge command must start with direct 'docker run'")
    if "--rm" not in argv or "--read-only" not in argv:
        raise AgentEvalError("Judge container must be disposable with a read-only root filesystem")
    if "--privileged" in argv or "host" in (_option_value(argv, "--network") or "") or any(
        _option_value(argv, option) == "host" for option in ("--pid", "--ipc", "--uts", "--cgroupns")
    ):
        raise AgentEvalError("Judge container may not use privileged or host-network access")
    if any(item in {"-v", "--volume"} or item.startswith("--volume=") for item in argv):
        raise AgentEvalError("Judge container may not mount host volumes")
    if any(item in {"--device", "--devices", "--volumes-from", "--cap-add"} or item.startswith(("--device=", "--volumes-from=", "--cap-add=")) for item in argv):
        raise AgentEvalError("Judge container may not add host devices, volumes, or capabilities")
    if any(item in {"--pid=host", "--ipc=host", "--uts=host"} for item in argv):
        raise AgentEvalError("Judge container may not join host namespaces")
    mounts: list[str] = []
    index = 0
    while index < len(argv):
        token = argv[index]
        if token == "--mount" and index + 1 < len(argv):
            mounts.append(argv[index + 1])
            index += 2
        elif token.startswith("--mount="):
            mounts.append(token.split("=", 1)[1])
            index += 1
        else:
            index += 1
    if any("type=bind" in item or "type=volume" in item for item in mounts):
        raise AgentEvalError("Judge receives evaluator or source data only through its prompt")
    if any(str(evaluator_root.resolve()).lower() in item.lower() for item in argv):
        raise AgentEvalError("Judge command contains an Evaluator path")
    return {
        "status": "verified",
        "fresh_container": True,
        "host_bind_mounts": 0,
        "root_filesystem_read_only": True,
        "prompt_transport": "stdin",
        "network": _option_value(argv, "--network") or "docker-default",
        "public_egress_control": "not_verified_by_container_mount_check",
    }


def verify_repair_docker_command(
    argv: list[str],
    *,
    workspace: Path,
    skill_root: Path,
    output_root: Path,
    skill_name: str,
) -> dict[str, Any]:
    if len(argv) < 3 or Path(argv[0]).name.lower() not in {"docker", "docker.exe"} or argv[1] != "run":
        raise AgentEvalError("repair command must start with direct 'docker run'")
    if "--rm" not in argv or "--read-only" not in argv:
        raise AgentEvalError("repair container must be disposable with a read-only root filesystem")
    if (_option_value(argv, "--workdir") or _option_value(argv, "-w")) != "/workspace":
        raise AgentEvalError("repair container working directory must be /workspace")
    if "--privileged" in argv or "host" in (_option_value(argv, "--network") or "") or any(
        _option_value(argv, option) == "host" for option in ("--pid", "--ipc", "--uts", "--cgroupns")
    ):
        raise AgentEvalError("repair container may not use privileged or host-network access")
    if any(item in {"-v", "--volume", "--device", "--volumes-from", "--cap-add"} for item in argv):
        raise AgentEvalError("repair container may not use volume aliases, host devices, or added capabilities")
    if any(item == "--tmpfs" or item.startswith("--tmpfs=") for item in argv):
        raise AgentEvalError("repair tmpfs mounts must use auditable --mount entries")
    codex_home = _codex_home_from_argv(argv)
    expected = {
        (workspace.resolve(), "/workspace", True): False,
        (skill_root.resolve(), f"/workspace/.agents/skills/{skill_name}", False): False,
        (output_root.resolve(), "/workspace/.qa-eval-output", False): False,
    }
    index = 0
    bind_count = 0
    while index < len(argv):
        token = argv[index]
        if token == "--mount" and index + 1 < len(argv):
            value = argv[index + 1]
            index += 2
        elif token.startswith("--mount="):
            value = token.split("=", 1)[1]
            index += 1
        else:
            index += 1
            continue
        fields: dict[str, str | bool] = {}
        for part in value.split(","):
            key, separator, content = part.partition("=")
            fields[key] = content if separator else True
        if fields.get("type") == "tmpfs":
            if not _approved_agent_tmpfs(fields.get("target"), codex_home):
                raise AgentEvalError("repair tmpfs mounts may cover only /tmp or the explicitly configured temporary CODEX_HOME")
            continue
        if fields.get("type") != "bind" or not isinstance(fields.get("source"), str) or not isinstance(fields.get("target"), str):
            raise AgentEvalError("repair container may use only approved bind and tmpfs mounts")
        readonly = fields.get("readonly") is True or fields.get("ro") is True
        item = (Path(str(fields["source"])).resolve(), str(fields["target"]), readonly)
        if item not in expected:
            raise AgentEvalError("repair container contains an unapproved bind mount")
        expected[item] = True
        bind_count += 1
    if bind_count != 3 or not all(expected.values()):
        raise AgentEvalError("repair command must mount only read-only workspace, one Skill package, and output root")
    return {
        "status": "verified",
        "workspace_read_only": True,
        "single_skill_writable": skill_name,
        "output_only_additional_writable_root": True,
        "root_filesystem_read_only": True,
        "network": _option_value(argv, "--network") or "docker-default",
        "public_egress_control": "not_verified_by_container_mount_check",
    }


def named_container_command(argv: list[str], *, name: str) -> tuple[list[str], list[str]]:
    if any(item == "--name" or item.startswith("--name=") for item in argv):
        raise AgentEvalError("runner owns the temporary Docker container name")
    if len(argv) < 3 or argv[1] != "run":
        raise AgentEvalError("container command is not a direct docker run")
    command = list(argv)
    command[2:2] = ["--name", name]
    return command, [argv[0], "rm", "-f", name]


def _option_value(argv: list[str], name: str) -> str | None:
    for index, value in enumerate(argv):
        if value == name and index + 1 < len(argv):
            return argv[index + 1]
        if value.startswith(name + "="):
            return value.split("=", 1)[1]
    return None


def profile_fingerprint(profile: dict[str, Any]) -> str:
    normalized = json.loads(json.dumps(profile))
    normalized["agent"].pop("skill_roots", None)
    normalized["judge"].pop("skill_roots", None)
    normalized["judge"]["cwd"] = "<evaluator-judge-workspace>"
    normalized["isolation"]["agent_read_roots"] = ["<agent-visible-roots>"]
    normalized["verification"]["evidence_path"] = "<evidence>"
    return canonical_fingerprint(normalized)


def create_skill_workspace(
    evaluator_root: Path, revision: str, destination: Path
) -> dict[str, Any]:
    revision = resolve_commit(evaluator_root, revision)
    if destination.exists() and any(destination.iterdir()):
        raise AgentEvalError("skill workspace destination must be empty")
    destination.mkdir(parents=True, exist_ok=True)
    entries = _git(evaluator_root, "ls-tree", "-r", "-z", revision, "--", "skills")
    rows: list[tuple[str, str, str, str]] = []
    for entry in entries.split("\0"):
        if not entry:
            continue
        metadata, relative = entry.split("\t", 1)
        mode, object_type, object_sha = metadata.split(" ")
        if mode == "120000" or object_type != "blob":
            raise AgentEvalError("Skill package may not contain symlinks or non-file entries")
        rows.append((mode, object_type, object_sha, relative))

    skill_names = sorted(
        PurePosixPath(relative).parts[1]
        for _, _, _, relative in rows
        if len(PurePosixPath(relative).parts) == 3
        and PurePosixPath(relative).parts[0] == "skills"
        and PurePosixPath(relative).parts[2] == "SKILL.md"
    )
    if not skill_names or len(skill_names) != len(set(skill_names)):
        raise AgentEvalError("candidate revision must contain a unique tracked Skill set")
    manifest_files: list[dict[str, Any]] = []
    archive = subprocess.run(
        ["git", "-C", str(evaluator_root), "archive", "--format=tar", revision, "skills"],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=60,
        check=False,
        shell=False,
    )
    if archive.returncode != 0:
        raise AgentEvalError("could not read candidate tracked Skill package")
    if len(archive.stdout) > 256 * 1024 * 1024:
        raise AgentEvalError("candidate Skill archive exceeds the allowed size")

    allowed_skills = set(skill_names)
    with tarfile.open(fileobj=io.BytesIO(archive.stdout), mode="r:") as package:
        for member in package.getmembers():
            raw_path = PurePosixPath(member.name)
            if raw_path.is_absolute() or any(part in {"", ".", ".."} for part in raw_path.parts):
                raise AgentEvalError("candidate archive contains an unsafe path")
            parts = raw_path.parts
            if len(parts) < 3 or parts[0] != "skills" or parts[1] not in allowed_skills:
                continue
            if member.isdir():
                continue
            if not member.isfile():
                raise AgentEvalError("candidate Skill package contains a non-regular file")
            if parts[2] != "SKILL.md" and parts[2] not in ALLOWED_PACKAGE_AREAS:
                continue
            if len(parts) > 3 and parts[2] not in ALLOWED_PACKAGE_AREAS:
                continue
            relative = PurePosixPath(*parts).as_posix()
            target = destination.joinpath(*parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            stream = package.extractfile(member)
            if stream is None:
                raise AgentEvalError("candidate archive file could not be read")
            content = stream.read()
            target.write_bytes(content)
            manifest_files.append(
                {"path": relative, "size": len(content), "sha256": sha256_bytes(content)}
            )

    seen_skills = {
        item["path"].split("/")[1]
        for item in manifest_files
        if item["path"].endswith("/SKILL.md")
    }
    if seen_skills != allowed_skills:
        raise AgentEvalError("tracked Skill set did not match the extracted package")
    manifest_files.sort(key=lambda item: item["path"])
    return {
        "revision": revision,
        "skills": skill_names,
        "files": manifest_files,
        "package_fingerprint": canonical_fingerprint(manifest_files),
    }


def create_skill_workspace_from_root(
    source_root: Path,
    destination: Path,
    *,
    expected_skills: set[str],
    parent_revision: str,
) -> dict[str, Any]:
    """Copy a review candidate package without eval data or non-package files."""
    source_root = source_root.resolve()
    source_skills = source_root / "skills"
    if not source_skills.is_dir() or source_skills.is_symlink():
        raise AgentEvalError("candidate package root must contain a regular skills directory")
    if destination.exists() and any(destination.iterdir()):
        raise AgentEvalError("candidate Skill workspace destination must be empty")
    destination.mkdir(parents=True, exist_ok=True)
    manifest_files: list[dict[str, Any]] = []
    present: set[str] = set()
    for path in sorted(source_skills.rglob("*")):
        if path.is_symlink():
            raise AgentEvalError("candidate Skill package may not contain symlinks")
        if not path.is_file():
            continue
        relative = path.relative_to(source_skills).as_posix()
        parts = PurePosixPath(relative).parts
        if len(parts) < 2:
            continue
        skill = parts[0]
        if skill not in expected_skills:
            raise AgentEvalError("candidate package changes the fixed Skill set")
        if parts[1] != "SKILL.md" and parts[1] not in ALLOWED_PACKAGE_AREAS:
            continue
        if len(parts) > 2 and parts[1] not in ALLOWED_PACKAGE_AREAS:
            continue
        if parts[1] == "SKILL.md":
            present.add(skill)
        content = path.read_bytes()
        target = destination / "skills" / skill / Path(*parts[1:])
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        manifest_files.append({"path": f"skills/{relative}", "size": len(content), "sha256": sha256_bytes(content)})
    if present != expected_skills:
        raise AgentEvalError("candidate package Skill set differs from the fixed parent revision")
    manifest_files.sort(key=lambda item: item["path"])
    return {
        "revision": parent_revision,
        "candidate_revision_status": "uncommitted_patch",
        "skills": sorted(present),
        "files": manifest_files,
        "package_fingerprint": canonical_fingerprint(manifest_files),
    }
