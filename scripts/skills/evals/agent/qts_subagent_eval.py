from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
import shutil
import tarfile
import uuid
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

from . import qa_training_store
from .common import (
    MAX_TEXT_BYTES,
    AgentEvalError,
    atomic_write_json,
    atomic_write_text,
    canonical_fingerprint,
    read_regular_file_bytes,
    sha256_bytes,
)
from .common_runtime_checks import (
    _artifact_map,
    _duplicate_invocation_ids,
    _read_invocation,
    _runtime_invocation_files,
    evaluate_runtime_captures,
    evaluate_workflow_runtime_capture,
)
from .prompt_builder import build_qa_training_store_generation_prompt
from .public_artifact_index import validate as validate_public_artifact_index
from .target_workspace import (
    DEFAULT_TARGET_REVISION,
    _is_excluded,
    prepare_sanitized_target,
    verify_workspace_unchanged,
)
from .verifier_capture import RUNTIME_SKILLS
from .workspace import (
    assert_clean_checkout,
    create_skill_workspace,
    resolve_commit,
)

REPO_ROOT = Path(__file__).resolve().parents[4]
RUN_SCHEMA_VERSION = 1
ATTEMPT_ID_RE = re.compile(r"^[0-9a-f]{32}$")
_SECRET_TEXT_RE = qa_training_store._SECRET_TEXT_RE
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_REQUIRED_RUNTIME_SKILLS = frozenset(
    item["skill"]
    for item in qa_training_store.load_scenario()["required_artifacts"]
    if item["skill"] in RUNTIME_SKILLS
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise AgentEvalError("duplicate JSON key")
        value[key] = item
    return value


def _read_json(path: Path, *, max_bytes: int = MAX_TEXT_BYTES) -> Any:
    try:
        return json.loads(
            read_regular_file_bytes(path, max_bytes=max_bytes).decode("utf-8"),
            object_pairs_hook=_strict_object,
        )
    except (AgentEvalError, UnicodeError, json.JSONDecodeError) as exc:
        raise AgentEvalError(f"invalid JSON evidence: {path.name}") from exc


def _assert_no_symlink_components(path: Path) -> None:
    absolute = Path(os.path.abspath(path))
    current = Path(absolute.anchor)
    for part in absolute.parts[1:]:
        current /= part
        try:
            if stat.S_ISLNK(current.lstat().st_mode):
                raise AgentEvalError("evaluation path may not contain symlinks")
        except FileNotFoundError:
            continue


def _run_root(path: Path, *, create: bool = False) -> Path:
    root = Path(os.path.abspath(path))
    repository = REPO_ROOT.resolve()
    try:
        relative = root.relative_to(repository)
    except ValueError as exc:
        raise AgentEvalError(
            "QTS run root must be under the Evaluator checkout"
        ) from exc
    if len(relative.parts) < 2 or relative.parts[0] != ".agent-eval-runs":
        raise AgentEvalError("QTS run root must be under .agent-eval-runs/")
    _assert_no_symlink_components(root)
    if create:
        if root.exists():
            raise AgentEvalError("QTS run root must not already exist")
        root.mkdir(parents=True, mode=0o700)
        root.chmod(0o700)
    elif not root.is_dir():
        raise AgentEvalError("QTS run root does not exist")
    return root


def _git_head(root: Path) -> str:
    completed = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "--verify", "HEAD"],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        shell=False,
        timeout=30,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if completed.returncode != 0:
        raise AgentEvalError("Evaluator revision could not be resolved")
    return completed.stdout.strip()


def _evaluator_source_fingerprints() -> dict[str, str]:
    paths = (
        "scripts/skills/evals/agent/qa_training_store.py",
        "scripts/skills/evals/agent/target_workspace.py",
        "scripts/skills/evals/agent/prompt_builder.py",
        "scripts/skills/evals/agent/public_artifact_index.py",
        "scripts/skills/evals/agent/verifier_capture.py",
        "scripts/skills/evals/agent/common_runtime_checks.py",
        "scripts/skills/evals/agent/common.py",
        "scripts/skills/evals/agent/workspace.py",
        "scripts/skills/evals/agent/qts_subagent_eval.py",
        (
            "scripts/skills/evals/agent/scenarios/"
            "qa-training-store-checkout-payment-web-v1/scenario.json"
        ),
        (
            "scripts/skills/evals/agent/scenarios/"
            "qa-training-store-checkout-payment-web-v1/task.md"
        ),
        (
            "scripts/skills/evals/agent/scenarios/"
            "qa-training-store-checkout-payment-web-v1/rubric.json"
        ),
    )
    fingerprints: dict[str, str] = {}
    for relative in paths:
        path = REPO_ROOT / relative
        fingerprints[relative] = sha256_bytes(
            read_regular_file_bytes(path, max_bytes=10_000_000)
        )
    return fingerprints


def _snapshot_source_from_prior_run(
    *,
    source_run_root: Path,
    source_attempt_id: str,
    destination: Path,
    source_tree_manifest: dict[str, Any],
) -> dict[str, Any]:
    """Rebuild a source snapshot after checking it against the fixed Git tree."""
    source_root = _run_root(source_run_root)
    source_run = _load_run(source_root)
    if (
        source_run.get("target_revision") != DEFAULT_TARGET_REVISION
        or source_run.get("scenario_fingerprint")
        != qa_training_store.load_scenario()["scenario_fingerprint"]
    ):
        raise AgentEvalError("prior QTS target snapshot does not bind the fixed source")
    if (
        not isinstance(source_tree_manifest, dict)
        or source_tree_manifest.get("schema_version") != 1
        or source_tree_manifest.get("commit_sha") != DEFAULT_TARGET_REVISION
        or source_tree_manifest.get("truncated") is not False
        or not isinstance(source_tree_manifest.get("tree_sha"), str)
        or not re.fullmatch(r"[0-9a-f]{40}", source_tree_manifest["tree_sha"])
        or not isinstance(source_tree_manifest.get("files"), list)
    ):
        raise AgentEvalError("fixed QTS Git tree attestation is invalid")
    _source_row, source_attempt_root = _attempt_paths(
        source_root, source_attempt_id, run=source_run
    )
    source_record = _load_attempt_record(source_attempt_root)
    baseline = _read_json(
        source_attempt_root / "evaluator-private" / "target-baseline.json"
    )
    source_target = source_attempt_root / "target"
    integrity = verify_workspace_unchanged(
        source_target,
        baseline,
        expected_synthetic_baseline_revision=source_record.get(
            "synthetic_baseline_revision", ""
        ),
    )
    if not integrity.get("unchanged"):
        raise AgentEvalError("prior QTS source snapshot was modified")
    source_manifest_fingerprint = source_record.get("target_manifest_fingerprint")
    if not isinstance(source_manifest_fingerprint, str) or not _SHA256_RE.fullmatch(
        source_manifest_fingerprint
    ):
        raise AgentEvalError("prior QTS source manifest binding is invalid")

    all_source_fingerprints: set[str] = set()
    for row in source_run["attempts"]:
        if not isinstance(row, dict) or not isinstance(row.get("attempt_id"), str):
            raise AgentEvalError("prior QTS source run has invalid attempt rows")
        _row, attempt_root = _attempt_paths(
            source_root, row["attempt_id"], run=source_run
        )
        record = _load_attempt_record(attempt_root)
        fingerprint = record.get("target_manifest_fingerprint")
        if not isinstance(fingerprint, str) or not _SHA256_RE.fullmatch(fingerprint):
            raise AgentEvalError("prior QTS source attempt manifest is invalid")
        all_source_fingerprints.add(fingerprint)
    if all_source_fingerprints != {source_manifest_fingerprint}:
        raise AgentEvalError("prior QTS attempts do not share one source manifest")

    snapshot_head = source_record.get("synthetic_baseline_revision")
    if not isinstance(snapshot_head, str) or not re.fullmatch(r"[0-9a-f]{40}", snapshot_head):
        raise AgentEvalError("prior QTS synthetic baseline identity is invalid")
    archived = subprocess.run(
        [
            "git",
            "-c",
            f"safe.directory={source_target.resolve()}",
            "-C",
            str(source_target),
            "archive",
            "--format=tar",
            snapshot_head,
        ],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=120,
        check=False,
        shell=False,
    )
    if archived.returncode != 0 or len(archived.stdout) > 1024 * 1024 * 1024:
        raise AgentEvalError("prior QTS source archive is unavailable or too large")

    rows: list[dict[str, Any]] = []
    files: list[tuple[str, bytes, int]] = []
    archived_files: dict[str, tuple[bytes, int]] = {}
    evaluator_injected = (
        "AGENTS.md",
        "docs/PROJECT_CONTEXT.md",
    )
    with tarfile.open(fileobj=io.BytesIO(archived.stdout), mode="r:") as archive:
        for member in archive.getmembers():
            relative = PurePosixPath(member.name)
            if relative.is_absolute() or any(
                part in {"", ".", ".."} for part in relative.parts
            ):
                raise AgentEvalError("prior QTS source archive has an unsafe path")
            path = relative.as_posix()
            if member.isdir():
                continue
            if not member.isfile():
                raise AgentEvalError("prior QTS source archive has a non-regular file")
            if (
                path in evaluator_injected
                or path.startswith((".agents/", ".qa-eval-tools/"))
                or _is_excluded(path)
            ):
                continue
            stream = archive.extractfile(member)
            if stream is None:
                raise AgentEvalError("prior QTS source archive file could not be read")
            content = stream.read()
            archived_files[path] = (content, member.mode)
            rows.append(
                {"path": path, "size": len(content), "sha256": sha256_bytes(content)}
            )
    rows.sort(key=lambda item: item["path"])
    if canonical_fingerprint(rows) != source_manifest_fingerprint:
        raise AgentEvalError("prior QTS snapshot does not match its source manifest")

    tree_rows: dict[str, dict[str, Any]] = {}
    for item in source_tree_manifest["files"]:
        if not isinstance(item, dict):
            raise AgentEvalError("fixed QTS Git tree entry is invalid")
        path = item.get("path")
        if (
            not isinstance(path, str)
            or path in tree_rows
            or not re.fullmatch(r"[0-9a-f]{40}", str(item.get("sha", "")))
            or item.get("mode") not in {"100644", "100755"}
            or isinstance(item.get("size"), bool)
            or not isinstance(item.get("size"), int)
            or item["size"] < 0
        ):
            raise AgentEvalError("fixed QTS Git tree entry is invalid")
        safe_path = PurePosixPath(path)
        if (
            safe_path.is_absolute()
            or "\\" in path
            or any(part in {"", ".", ".."} for part in safe_path.parts)
            or path in evaluator_injected
            or path.startswith((".agents/", ".qa-eval-tools/"))
            or _is_excluded(path)
        ):
            raise AgentEvalError("fixed QTS Git tree entry is outside the target scope")
        tree_rows[path] = item
    if set(tree_rows) != set(archived_files):
        raise AgentEvalError("prior QTS source paths differ from the fixed Git tree")

    for path in sorted(archived_files):
        content, _archived_mode = archived_files[path]
        expected = tree_rows[path]
        git_blob = hashlib.sha1(
            b"blob " + str(len(content)).encode("ascii") + b"\0" + content
        ).hexdigest()
        if len(content) != expected["size"] or git_blob != expected["sha"]:
            raise AgentEvalError("prior QTS file content differs from the fixed Git tree")
        files.append((path, content, 0o755 if expected["mode"] == "100755" else 0o644))

    destination = Path(os.path.abspath(destination))
    _assert_no_symlink_components(destination)
    try:
        relative_destination = destination.relative_to(REPO_ROOT)
    except ValueError as exc:
        raise AgentEvalError("QTS source snapshot must be under .agent-eval-runs") from exc
    if len(relative_destination.parts) < 2 or relative_destination.parts[0] != ".agent-eval-runs":
        raise AgentEvalError("QTS source snapshot must be under .agent-eval-runs")
    if destination.exists() or destination.is_symlink():
        raise AgentEvalError("QTS source snapshot destination must be new")
    destination.mkdir(parents=True)
    for relative, content, mode in files:
        target = destination.joinpath(*PurePosixPath(relative).parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        target.chmod(mode)
    empty_hooks = destination.parent / f".{destination.name}-empty-hooks"
    empty_hooks.mkdir()
    env = {
        **os.environ,
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_AUTHOR_NAME": "Evaluator",
        "GIT_AUTHOR_EMAIL": "evaluator@invalid.local",
        "GIT_COMMITTER_NAME": "Evaluator",
        "GIT_COMMITTER_EMAIL": "evaluator@invalid.local",
    }
    try:
        subprocess.run(
            ["git", "init", "--quiet", str(destination)],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
            check=True,
            shell=False,
            env=env,
        )
        subprocess.run(
            ["git", "-C", str(destination), "config", "core.hooksPath", str(empty_hooks)],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
            check=True,
            shell=False,
            env=env,
        )
        subprocess.run(
            ["git", "-C", str(destination), "add", "--force", "--all"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=60,
            check=True,
            shell=False,
            env=env,
        )
        subprocess.run(
            ["git", "-C", str(destination), "commit", "--quiet", "-m", "Verified QTS source snapshot"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=60,
            check=True,
            shell=False,
            env=env,
        )
        snapshot_revision = subprocess.run(
            ["git", "-C", str(destination), "rev-parse", "HEAD"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
            check=True,
            shell=False,
            env=env,
            text=True,
            encoding="utf-8",
        ).stdout.strip()
        remotes = subprocess.run(
            ["git", "-C", str(destination), "remote"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
            check=True,
            shell=False,
            env=env,
            text=True,
            encoding="utf-8",
        ).stdout.strip()
        if remotes:
            raise AgentEvalError("verified QTS source snapshot must not have remotes")
    finally:
        shutil.rmtree(empty_hooks, ignore_errors=False)
    return {
        "method": "verified_prior_sanitized_target_snapshot",
        "source_run_id": source_run["run_id"],
        "source_attempt_id": source_attempt_id,
        "target_revision": DEFAULT_TARGET_REVISION,
        "source_manifest_fingerprint": source_manifest_fingerprint,
        "source_synthetic_head": snapshot_head,
        "rebuilt_snapshot_head": snapshot_revision,
        "source_file_count": len(rows),
        "source_git_tree_sha": source_tree_manifest["tree_sha"],
        "source_git_tree_fingerprint": canonical_fingerprint(
            sorted(source_tree_manifest["files"], key=lambda item: item["path"])
        ),
        "source_integrity": "verified",
        "host_execution_status": source_record.get("execution", {}).get(
            "status", "unverified"
        ),
        "effective_model_status": "unverified",
        "tool_trace_status": "unverified",
    }


def _selected_skills(scenario: dict[str, Any]) -> list[str]:
    names = {row["skill"] for row in scenario["required_artifacts"]}
    names.add("question-analysis")
    return sorted(names)


def _copy_selected_skill_packages(
    source_root: Path,
    destination: Path,
    selected: list[str],
    package_manifest: dict[str, Any],
) -> dict[str, Any]:
    source_skills = source_root / "skills"
    target_skills = destination / "skills"
    target_skills.mkdir(parents=True, exist_ok=False)
    selected_files: list[dict[str, Any]] = []
    for row in package_manifest["files"]:
        parts = PurePosixPath(row["path"]).parts
        if len(parts) < 3 or parts[0] != "skills" or parts[1] not in selected:
            continue
        source = source_skills.joinpath(*parts[1:])
        content = read_regular_file_bytes(source, max_bytes=MAX_TEXT_BYTES)
        target = target_skills.joinpath(*parts[1:])
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        selected_files.append(dict(row))
    present = {
        PurePosixPath(row["path"]).parts[1]
        for row in selected_files
        if row["path"].endswith("/SKILL.md")
    }
    if present != set(selected):
        raise AgentEvalError("fixed Skill package is missing a required SKILL.md")
    selected_files.sort(key=lambda item: item["path"])
    return {
        "revision": package_manifest["revision"],
        "skills": selected,
        "files": selected_files,
        "package_fingerprint": canonical_fingerprint(selected_files),
    }


def _attempt_paths(
    root: Path,
    attempt_id: str,
    *,
    run: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], Path]:
    if not ATTEMPT_ID_RE.fullmatch(attempt_id):
        raise AgentEvalError("attempt ID is invalid")
    current_run = run if run is not None else _load_run(root)
    matches = [
        row
        for row in current_run["attempts"]
        if isinstance(row, dict) and row.get("attempt_id") == attempt_id
    ]
    if len(matches) != 1:
        raise AgentEvalError("attempt ID is missing or duplicated")
    attempt_root = root / "attempts" / attempt_id
    _assert_no_symlink_components(attempt_root)
    if not attempt_root.is_dir():
        raise AgentEvalError("attempt directory is missing")
    return matches[0], attempt_root


def _load_run(root: Path) -> dict[str, Any]:
    result = _read_json(root / "result.json")
    if (
        not isinstance(result, dict)
        or result.get("schema_version") != RUN_SCHEMA_VERSION
        or result.get("execution_method") != "codex_subagent_handoff"
        or not isinstance(result.get("attempts"), list)
    ):
        raise AgentEvalError("QTS subagent run record has an invalid contract")
    return result


def _load_attempt_record(attempt_root: Path) -> dict[str, Any]:
    value = _read_json(attempt_root / "evaluator-private" / "attempt.json")
    if not isinstance(value, dict) or value.get("schema_version") != 1:
        raise AgentEvalError("QTS attempt record has an invalid contract")
    return value


def _write_run(root: Path, result: dict[str, Any]) -> None:
    atomic_write_json(root / "result.json", result)


def prepare_run(
    *,
    target_source_root: Path,
    skill_revision: str,
    output_root: Path,
    source_provenance_path: Path | None = None,
    repeat: int = 2,
    model: str = "gpt-6-luna",
    reasoning_effort: str = "max",
    fork_turns: str = "none",
) -> dict[str, Any]:
    if isinstance(repeat, bool) or not isinstance(repeat, int) or repeat < 2:
        raise AgentEvalError("QTS subagent evaluation requires at least two attempts")
    requested_settings = {
        "model": model,
        "reasoning_effort": reasoning_effort,
        "fork_turns": fork_turns,
    }
    if requested_settings != {
        "model": "gpt-6-luna",
        "reasoning_effort": "max",
        "fork_turns": "none",
    }:
        raise AgentEvalError(
            "QTS subagent settings must use the fixed requested values"
        )

    root = _run_root(output_root, create=True)
    scenario = qa_training_store.load_scenario()
    source_provenance: dict[str, Any] | None = None
    if source_provenance_path is None:
        target_revision = resolve_commit(target_source_root, DEFAULT_TARGET_REVISION)
        target_head = assert_clean_checkout(
            target_source_root, expected_revision=DEFAULT_TARGET_REVISION
        )
    else:
        provenance_path = Path(os.path.abspath(source_provenance_path))
        _assert_no_symlink_components(provenance_path)
        try:
            provenance_path.relative_to(REPO_ROOT / ".agent-eval-runs")
        except ValueError as exc:
            raise AgentEvalError(
                "QTS source provenance must be under .agent-eval-runs"
            ) from exc
        source_provenance = _read_json(provenance_path)
        if (
            not isinstance(source_provenance, dict)
            or source_provenance.get("target_revision") != DEFAULT_TARGET_REVISION
            or source_provenance.get("source_integrity") != "verified"
            or not isinstance(
                source_provenance.get("source_manifest_fingerprint"), str
            )
            or not _SHA256_RE.fullmatch(
                source_provenance["source_manifest_fingerprint"]
            )
            or not isinstance(source_provenance.get("rebuilt_snapshot_head"), str)
            or not re.fullmatch(
                r"[0-9a-f]{40}", source_provenance["rebuilt_snapshot_head"]
            )
            or not isinstance(source_provenance.get("source_git_tree_sha"), str)
            or not re.fullmatch(r"[0-9a-f]{40}", source_provenance["source_git_tree_sha"])
        ):
            raise AgentEvalError("QTS source provenance does not verify the fixed target")
        target_revision = DEFAULT_TARGET_REVISION
        target_head = assert_clean_checkout(target_source_root)
        if target_head != source_provenance["rebuilt_snapshot_head"]:
            raise AgentEvalError("QTS source snapshot HEAD differs from its attestation")
        remotes = subprocess.run(
            ["git", "-C", str(target_source_root), "remote"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
            check=True,
            shell=False,
            text=True,
            encoding="utf-8",
        ).stdout.strip()
        commit_count = subprocess.run(
            ["git", "-C", str(target_source_root), "rev-list", "--count", "HEAD"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
            check=True,
            shell=False,
            text=True,
            encoding="utf-8",
        ).stdout.strip()
        if remotes or commit_count != "1":
            raise AgentEvalError("QTS source snapshot Git boundary is invalid")
    skill_revision = resolve_commit(REPO_ROOT, skill_revision)
    evaluator_revision = _git_head(REPO_ROOT)
    skills = _selected_skills(scenario)
    selected_package_source = root / "evaluator-private" / "qts-skill-package"
    with tempfile.TemporaryDirectory(prefix="qts-skill-package-") as temporary_package:
        full_manifest = create_skill_workspace(
            REPO_ROOT, skill_revision, Path(temporary_package)
        )
        selected_manifest = _copy_selected_skill_packages(
            Path(temporary_package), selected_package_source, skills, full_manifest
        )
    prompt = build_qa_training_store_generation_prompt(
        eval_input=scenario["task_text"],
        required_artifacts=scenario["required_artifacts"],
        target_revision=target_revision,
    )
    result: dict[str, Any] = {
        "schema_version": RUN_SCHEMA_VERSION,
        "execution_method": "codex_subagent_handoff",
        "run_id": uuid.uuid4().hex,
        "created_at": _now(),
        "scenario_id": scenario["scenario_id"],
        "target_revision": target_revision,
        "target_source_checkout_head": target_head,
        "target_source_provenance": source_provenance
        or {
            "method": "fixed_git_checkout",
            "source_integrity": "verified",
        },
        "skill_revision": skill_revision,
        "evaluator_revision": evaluator_revision,
        "evaluator_source_fingerprints": _evaluator_source_fingerprints(),
        "scenario_fingerprint": scenario["scenario_fingerprint"],
        "prompt_fingerprint": sha256_bytes(prompt.encode("utf-8")),
        "requested_settings": requested_settings,
        "effective_model_status": "unverified",
        "host_tool_trace_status": "unverified",
        "physical_evaluator_read_denial": "unverified",
        "agent_visible_skills": skills,
        "attempts": [],
        "stage2_scope": {
            "judge": "not_run",
            "production_verifier_independent_replay": "evidence_unverified",
            "docker_used": False,
        },
    }
    _write_run(root, result)

    atomic_write_json(
        root / "evaluator-private" / "skill-package-manifest.json", selected_manifest
    )
    atomic_write_text(root / "evaluator-private" / "generation-prompt.md", prompt)
    atomic_write_json(
        root / "evaluator-private" / "scenario-private.json",
        {
            "scenario_fingerprint": scenario["scenario_fingerprint"],
            "rubric_fingerprint": canonical_fingerprint(scenario["rubric"]),
            "reference_paths": scenario["reference_paths"],
        },
    )

    for offset in range(repeat):
        attempt_id = uuid.uuid4().hex
        attempt_root = root / "attempts" / attempt_id
        private_root = attempt_root / "evaluator-private"
        target_root = attempt_root / "target"
        private_root.mkdir(parents=True, mode=0o700)
        row: dict[str, Any] = {
            "attempt_id": attempt_id,
            "attempt_number": offset + 1,
            "status": "preparing",
            "target_relative_path": f"attempts/{attempt_id}/target",
            "requested_settings": requested_settings,
        }
        result["attempts"].append(row)
        _write_run(root, result)
        try:
            per_attempt_package = private_root / "skill-packages"
            per_attempt_manifest = _copy_selected_skill_packages(
                selected_package_source,
                per_attempt_package,
                skills,
                selected_manifest,
            )
            target_result = prepare_sanitized_target(
                source_root=target_source_root,
                source_revision=target_revision,
                source_revision_label=DEFAULT_TARGET_REVISION
                if source_provenance is not None
                else None,
                candidate_skills_root=per_attempt_package / "skills",
                verifier_capture_source=REPO_ROOT
                / "scripts/skills/evals/agent/verifier_capture.py",
                destination=target_root,
            )
            if (
                source_provenance is not None
                and target_result["source_manifest_fingerprint"]
                != source_provenance["source_manifest_fingerprint"]
            ):
                raise AgentEvalError(
                    "prepared target differs from the verified fixed-source manifest"
                )
            baseline_path = private_root / "target-baseline.json"
            atomic_write_json(baseline_path, target_result["baseline_manifest"])
            atomic_write_text(private_root / "generation-prompt.md", prompt)
            private_record = {
                "schema_version": 1,
                "attempt_id": attempt_id,
                "prepared_at": _now(),
                "scenario_id": scenario["scenario_id"],
                "scenario_fingerprint": scenario["scenario_fingerprint"],
                "target_revision": target_revision,
                "target_source_checkout_head": target_head,
                "source_manifest_fingerprint": target_result[
                    "source_manifest_fingerprint"
                ],
                "target_manifest_fingerprint": target_result[
                    "source_manifest_fingerprint"
                ],
                "target_baseline_manifest_fingerprint": target_result[
                    "baseline_manifest_fingerprint"
                ],
                "synthetic_baseline_revision": target_result[
                    "synthetic_baseline_revision"
                ],
                "skill_revision": skill_revision,
                "skill_package": per_attempt_manifest,
                "prompt_fingerprint": sha256_bytes(prompt.encode("utf-8")),
                "requested_settings": requested_settings,
                "effective_model_status": "unverified",
                "physical_evaluator_read_denial": "unverified",
                "target_workspace_preflight": verify_workspace_unchanged(
                    target_root,
                    target_result["baseline_manifest"],
                    expected_synthetic_baseline_revision=target_result[
                        "synthetic_baseline_revision"
                    ],
                ),
            }
            if not private_record["target_workspace_preflight"]["unchanged"]:
                raise AgentEvalError("prepared target failed its integrity preflight")
            atomic_write_json(private_root / "attempt.json", private_record)
            row.update(
                {
                    "status": "prepared",
                    "synthetic_baseline_revision": target_result[
                        "synthetic_baseline_revision"
                    ],
                    "skill_package_fingerprint": per_attempt_manifest[
                        "package_fingerprint"
                    ],
                    "prompt_fingerprint": private_record["prompt_fingerprint"],
                }
            )
            _write_run(root, result)
        except Exception as exc:
            row.update(
                {
                    "status": "preparation_failed",
                    "failure": type(exc).__name__,
                    "failed_at": _now(),
                }
            )
            _write_run(root, result)
            raise
    return result


def record_execution(
    *,
    run_root: Path,
    attempt_id: str,
    execution_status: str,
    started_at: str,
    finished_at: str,
    submitted_prompt_fingerprint: str | None,
    final_response: str | None = None,
    host_observation: str = "codex_subagent_tool_returned",
) -> dict[str, Any]:
    if execution_status not in {"completed", "failed", "not_started"}:
        raise AgentEvalError("execution status is invalid")
    for label, value in (("started_at", started_at), ("finished_at", finished_at)):
        if not isinstance(value, str) or not value:
            raise AgentEvalError(f"{label} must be an ISO-8601 timestamp")
        try:
            datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise AgentEvalError(f"{label} must be an ISO-8601 timestamp") from exc
    if host_observation not in {
        "codex_subagent_tool_returned",
        "codex_subagent_tool_failed",
        "not_observed",
    }:
        raise AgentEvalError("host observation is invalid")
    root = _run_root(run_root)
    run = _load_run(root)
    row, attempt_root = _attempt_paths(root, attempt_id, run=run)
    if row.get("status") != "prepared":
        raise AgentEvalError("only a prepared QTS attempt can be executed")
    record_path = attempt_root / "evaluator-private" / "attempt.json"
    record = _load_attempt_record(attempt_root)
    prepared_prompt_fingerprint = record.get("prompt_fingerprint")
    if submitted_prompt_fingerprint is not None and not re.fullmatch(
        r"sha256:[0-9a-f]{64}", submitted_prompt_fingerprint
    ):
        raise AgentEvalError("submitted prompt fingerprint is invalid")
    prompt_matches_prepared = (
        isinstance(submitted_prompt_fingerprint, str)
        and submitted_prompt_fingerprint == prepared_prompt_fingerprint
    )
    final_response_status = "not_captured"
    final_response_sha256 = None
    if final_response is not None:
        response_bytes = final_response.encode("utf-8")
        if len(response_bytes) > MAX_TEXT_BYTES:
            raise AgentEvalError("host final response exceeds the size limit")
        if _SECRET_TEXT_RE.search(final_response):
            final_response_status = "secret_shaped_not_saved"
        elif final_response:
            final_path = attempt_root / "evaluator-private" / "final-response.md"
            if final_path.exists() or final_path.is_symlink():
                raise AgentEvalError("host final response capture is immutable")
            atomic_write_text(final_path, final_response)
            final_response_status = "captured"
            final_response_sha256 = sha256_bytes(response_bytes)
        else:
            final_response_status = "empty"
    execution = {
        "observed_at": _now(),
        "status": execution_status,
        "observation_source": host_observation,
        "started_at": started_at,
        "finished_at": finished_at,
        "requested_settings": record["requested_settings"],
        "submitted_prompt_fingerprint": submitted_prompt_fingerprint,
        "prepared_prompt_fingerprint": prepared_prompt_fingerprint,
        "prompt_matches_prepared": prompt_matches_prepared,
        "prompt_match_status": "verified_match"
        if prompt_matches_prepared
        else "unverified_or_mismatch",
        "final_response_status": final_response_status,
        "final_response_path": "evaluator-private/final-response.md"
        if final_response_status == "captured"
        else None,
        "final_response_sha256": final_response_sha256,
        "effective_model_status": "unverified",
        "tool_trace_status": "unverified",
        "agent_self_report_used_as_execution_proof": False,
    }
    record["execution"] = execution
    atomic_write_json(record_path, record)
    row.update({"status": "execution_recorded", "execution": execution})
    _write_run(root, run)
    return execution


def _scan_output_tree(output_root: Path, scenario: dict[str, Any]) -> dict[str, Any]:
    _assert_no_symlink_components(output_root)
    if output_root.is_symlink() or not output_root.is_dir():
        raise AgentEvalError("QTS output root is missing or unsafe")
    files: list[dict[str, Any]] = []
    total = 0
    secret_paths: list[str] = []
    for path in sorted(output_root.rglob("*")):
        relative_path = path.relative_to(output_root)
        relative = relative_path.as_posix()
        if path.is_symlink():
            raise AgentEvalError(f"QTS output contains a symlink: {relative}")
        info = path.lstat()
        if stat.S_ISDIR(info.st_mode):
            continue
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise AgentEvalError(f"QTS output contains an unsafe file: {relative}")
        if "\\" in relative or any(
            part in {"", ".", ".."} for part in relative_path.parts
        ):
            raise AgentEvalError("QTS output contains a non-canonical path")
        per_file_limit = (
            scenario["max_artifact_file_bytes"]
            if relative.endswith(".md") or relative == "artifact-index.json"
            else 20_000_000
        )
        raw = read_regular_file_bytes(path, max_bytes=per_file_limit)
        total += len(raw)
        if total > scenario["max_artifact_total_bytes"]:
            raise AgentEvalError("QTS output exceeds the total size limit")
        try:
            decoded = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise AgentEvalError(f"QTS output is not UTF-8: {relative}") from exc
        is_secret_shaped = bool(_SECRET_TEXT_RE.search(decoded))
        if is_secret_shaped:
            secret_paths.append(relative)
        files.append(
            {
                "path": relative,
                "size": len(raw),
                "sha256": None if is_secret_shaped else sha256_bytes(raw),
                "classification": (
                    "runner_internal"
                    if relative == "artifact-index.json"
                    else "runtime_evidence"
                    if relative.startswith(".runtime-evidence/")
                    else "markdown_candidate"
                    if relative.endswith(".md")
                    else "unregistered_or_internal"
                ),
                "secret_shaped": is_secret_shaped,
            }
        )
    return {
        "files": files,
        "total_bytes": total,
        "secret_shaped_paths": secret_paths,
        "safe_to_copy": not secret_paths,
    }


def _verify_captured_output_integrity(
    *,
    attempt_id: str,
    run_row: dict[str, Any],
    capture: dict[str, Any],
    source_output: dict[str, Any] | None,
    captured_root: Path,
    scenario: dict[str, Any],
) -> dict[str, Any]:
    """Verify the immutable capture record and every byte that will be graded."""
    issues: list[dict[str, Any]] = []
    if capture.get("schema_version") != 1 or capture.get("attempt_id") != attempt_id:
        issues.append({"kind": "capture_attempt_binding_mismatch"})
    expected_capture_fingerprint = run_row.get("capture_fingerprint")
    if not isinstance(
        expected_capture_fingerprint, str
    ) or expected_capture_fingerprint != canonical_fingerprint(capture):
        issues.append({"kind": "capture_manifest_fingerprint_mismatch"})

    copy_record = capture.get("copy")
    source_record = capture.get("output")
    if (
        not isinstance(copy_record, dict)
        or not isinstance(copy_record.get("files"), list)
        or not isinstance(source_record, dict)
        or not isinstance(source_record.get("files"), list)
    ):
        return {
            "status": "needs_review",
            "valid": False,
            "files_checked": 0,
            "issues": [*issues, {"kind": "capture_file_manifest_missing"}],
        }

    try:
        saved_scan = _scan_output_tree(captured_root, scenario)
    except (AgentEvalError, OSError) as exc:
        return {
            "status": "needs_review",
            "valid": False,
            "files_checked": 0,
            "issues": [
                *issues,
                {
                    "kind": "captured_output_filesystem_invalid",
                    "reason": type(exc).__name__,
                },
            ],
        }

    source_rows: dict[str, dict[str, Any]] = {}
    for item in source_record["files"]:
        if not isinstance(item, dict) or not isinstance(item.get("path"), str):
            issues.append({"kind": "capture_source_file_manifest_invalid"})
            continue
        path = item["path"]
        if path in source_rows:
            issues.append({"kind": "capture_source_file_duplicate", "path": path})
        source_rows[path] = item

    saved_rows: dict[str, dict[str, Any]] = {}
    for item in copy_record["files"]:
        if not isinstance(item, dict) or not isinstance(item.get("path"), str):
            issues.append({"kind": "capture_saved_file_manifest_invalid"})
            continue
        path = item["path"]
        relative = PurePosixPath(path)
        if (
            relative.is_absolute()
            or "\\" in path
            or any(part in {"", ".", ".."} for part in relative.parts)
        ):
            issues.append({"kind": "capture_saved_file_path_invalid"})
            continue
        if path in saved_rows:
            issues.append({"kind": "capture_saved_file_duplicate", "path": path})
        saved_rows[path] = item

    source_paths = set(source_rows)
    saved_paths = set(saved_rows)
    actual_rows = {item["path"]: item for item in saved_scan["files"]}
    actual_paths = set(actual_rows)
    if source_paths != saved_paths:
        issues.append(
            {
                "kind": "capture_file_list_mismatch",
                "missing_saved_paths": sorted(source_paths - saved_paths),
                "extra_saved_paths": sorted(saved_paths - source_paths),
            }
        )
    if saved_paths != actual_paths:
        issues.append(
            {
                "kind": "captured_output_file_list_mismatch",
                "missing_paths": sorted(saved_paths - actual_paths),
                "extra_paths": sorted(actual_paths - saved_paths),
            }
        )

    for path in sorted(saved_paths & actual_paths & source_paths):
        saved = saved_rows[path]
        source = source_rows[path]
        actual = actual_rows[path]
        saved_digest = saved.get("saved_sha256")
        size = saved.get("size")
        if (
            not isinstance(saved_digest, str)
            or not _SHA256_RE.fullmatch(saved_digest)
            or isinstance(size, bool)
            or not isinstance(size, int)
            or size < 0
        ):
            issues.append({"kind": "capture_saved_file_identity_invalid", "path": path})
            continue
        try:
            actual_bytes = read_regular_file_bytes(
                captured_root / Path(*PurePosixPath(path).parts),
                max_bytes=scenario["max_artifact_total_bytes"],
            )
        except AgentEvalError as exc:
            issues.append(
                {
                    "kind": "captured_output_file_unreadable",
                    "path": path,
                    "reason": type(exc).__name__,
                }
            )
            continue
        actual_digest = sha256_bytes(actual_bytes)
        actual_size = len(actual_bytes)
        if actual_digest != saved_digest or actual_size != size:
            issues.append({"kind": "captured_output_saved_hash_mismatch", "path": path})
        redacted = saved.get("redacted") is True
        if redacted:
            issues.append({"kind": "redacted_capture_not_gradeable", "path": path})
            if (
                source.get("secret_shaped") is not True
                or source.get("sha256") is not None
                or saved.get("status") != "evidence_unverified"
            ):
                issues.append({"kind": "redaction_manifest_inconsistent", "path": path})
        else:
            if (
                saved.get("status") != "saved"
                or source.get("secret_shaped") is True
                or source.get("sha256") != saved.get("sha256")
                or saved.get("sha256") != saved_digest
                or source.get("size") != size
                or actual.get("sha256") != saved_digest
                or actual.get("size") != size
            ):
                issues.append(
                    {"kind": "capture_source_saved_identity_mismatch", "path": path}
                )

    if capture.get("copy", {}).get("status") != "saved":
        issues.append({"kind": "capture_copy_not_gradeable"})
    if source_output is None:
        issues.append({"kind": "source_output_unavailable"})
    else:
        source_fingerprint = canonical_fingerprint(
            [
                {
                    "path": item["path"],
                    "size": item["size"],
                    "sha256": item["sha256"],
                }
                for item in source_output["files"]
            ]
        )
        if source_fingerprint != capture.get("source_output_fingerprint"):
            issues.append({"kind": "source_output_capture_fingerprint_mismatch"})

    return {
        "status": "verified" if not issues else "needs_review",
        "valid": not issues,
        "files_checked": len(actual_paths),
        "issues": issues,
    }


def _validate_runtime_bindings(
    output_root: Path, artifacts: list[dict[str, Any]]
) -> dict[str, Any]:
    capture_root = output_root / ".runtime-evidence"
    if not capture_root.exists():
        return {
            "status": "evidence_unverified",
            "independent_replay": "evidence_unverified",
            "invocations": [],
            "issues": [{"kind": "runtime_evidence_missing"}],
            "required_skills_without_capture": sorted(_REQUIRED_RUNTIME_SKILLS),
        }
    if capture_root.is_symlink() or not capture_root.is_dir():
        return {
            "status": "evidence_unverified",
            "independent_replay": "evidence_unverified",
            "invocations": [],
            "issues": [{"kind": "runtime_capture_root_unsafe"}],
            "required_skills_without_capture": sorted(_REQUIRED_RUNTIME_SKILLS),
        }
    issues: list[dict[str, Any]] = []
    invocations: list[dict[str, Any]] = []
    captured_skills: set[str] = set()
    expected_artifacts = _artifact_map(artifacts)
    duplicate_ids = _duplicate_invocation_ids(capture_root)
    invocation_paths = _runtime_invocation_files(capture_root)
    for path in invocation_paths:
        try:
            invocation = _read_json(path)
            if not isinstance(invocation, dict):
                raise AgentEvalError("invocation must be an object")
            invocation, request_bytes, result_bytes = _read_invocation(
                capture_root, path
            )
            skill = invocation.get("skill")
            identity = (skill, invocation.get("artifact_id"))
            artifact_path = expected_artifacts.get(identity)
            if artifact_path is None:
                raise AgentEvalError(
                    "runtime invocation is not bound to a registered artifact"
                )
            artifact = next(
                row
                for row in artifacts
                if row.get("skill") == skill and row.get("path") == artifact_path
            )
            if invocation.get("invocation_id") in duplicate_ids:
                raise AgentEvalError("duplicate runtime invocation ID")
            request_json = json.loads(
                request_bytes.decode("utf-8"), object_pairs_hook=_strict_object
            )
            result_json = json.loads(
                result_bytes.decode("utf-8"), object_pairs_hook=_strict_object
            )
            if not isinstance(request_json, dict) or not isinstance(result_json, dict):
                raise AgentEvalError("runtime request and result must be JSON objects")
            operation = invocation.get("operation")
            if operation not in {"verify", "workflow-runtime"}:
                raise AgentEvalError("runtime operation is invalid")
            if operation == "verify" and (
                request_json.get("operation") != "verify_runtime_evidence"
                or not isinstance(result_json.get("valid"), bool)
            ):
                raise AgentEvalError(
                    "runtime verifier request/result contract is invalid"
                )
            if operation == "workflow-runtime" and not isinstance(
                result_json.get("payload"), dict
            ):
                raise AgentEvalError("workflow runtime result contract is invalid")
            claimed_valid = result_json.get("valid") if operation == "verify" else None
            can_complete = (
                result_json.get("payload", {}).get("can_complete")
                if operation == "workflow-runtime"
                and isinstance(result_json.get("payload"), dict)
                else None
            )
            captured_skills.add(skill)
            execution_claim_valid = (
                invocation.get("evidence_status") == "captured"
                and invocation.get("exit_code") == 0
                and invocation.get("timed_out") is False
            )
            if not execution_claim_valid:
                issues.append(
                    {
                        "kind": "runtime_capture_claim_not_successful",
                        "path": path.relative_to(output_root).as_posix(),
                    }
                )
            if claimed_valid is False:
                issues.append(
                    {
                        "kind": "runtime_verifier_reported_invalid",
                        "path": path.relative_to(output_root).as_posix(),
                    }
                )
            invocations.append(
                {
                    "skill": skill,
                    "artifact_id": artifact["artifact_id"],
                    "artifact_path": artifact_path,
                    "operation": operation,
                    "request_sha256": invocation["request_sha256"],
                    "result_sha256": invocation["result_sha256"],
                    "capture_record_integrity": "consistent",
                    "execution_claim_consistent": execution_claim_valid,
                    "agent_generated_execution_claim": invocation.get(
                        "evidence_status"
                    ),
                    "tool_trace_status": "unverified",
                    "captured_valid_claim": claimed_valid,
                    "workflow_can_complete_claim": can_complete,
                    "independent_replay": "evidence_unverified",
                }
            )
        except (
            AgentEvalError,
            OSError,
            UnicodeError,
            json.JSONDecodeError,
            ValueError,
        ) as exc:
            issues.append(
                {
                    "kind": "runtime_invocation_unverified",
                    "path": path.relative_to(output_root).as_posix(),
                    "reason": type(exc).__name__,
                }
            )
    found_invocation_paths = {path.parent.resolve() for path in invocation_paths}
    for path in sorted(capture_root.rglob("*")):
        if path.is_dir() or path.is_symlink():
            continue
        if path.name in {
            "request.json",
            "result.json",
            "invocation.json",
            "stderr.txt",
        }:
            parent = path.parent.resolve()
            if parent not in found_invocation_paths:
                issues.append(
                    {
                        "kind": "runtime_file_without_invocation",
                        "path": path.relative_to(output_root).as_posix(),
                    }
                )
    missing_skills = sorted(_REQUIRED_RUNTIME_SKILLS - captured_skills)
    if missing_skills:
        issues.append(
            {"kind": "required_runtime_capture_missing", "skills": missing_skills}
        )
    if not invocations and not issues:
        issues.append({"kind": "runtime_evidence_missing"})
    return {
        "status": "evidence_unverified" if issues else "capture_integrity_consistent",
        "independent_replay": "evidence_unverified",
        "invocations": invocations,
        "issues": issues,
        "required_skills_without_capture": missing_skills,
    }


def _runtime_source_fingerprints(
    run_row: dict[str, Any], attempt_record: dict[str, Any]
) -> tuple[dict[str, str] | None, list[dict[str, str]]]:
    manifest = attempt_record.get("skill_package")
    if (
        not isinstance(manifest, dict)
        or not isinstance(manifest.get("files"), list)
        or not isinstance(manifest.get("package_fingerprint"), str)
        or canonical_fingerprint(manifest["files"]) != manifest["package_fingerprint"]
        or run_row.get("skill_package_fingerprint") != manifest["package_fingerprint"]
    ):
        return None, [{"kind": "candidate_skill_package_manifest_unverified"}]

    result: dict[str, str] = {}
    issues: list[dict[str, str]] = []
    for skill in sorted(_REQUIRED_RUNTIME_SKILLS):
        prefix = f"skills/{skill}/scripts/"
        rows: list[dict[str, Any]] = []
        for item in manifest["files"]:
            if not isinstance(item, dict) or not isinstance(item.get("path"), str):
                issues.append({"kind": "candidate_skill_package_manifest_invalid"})
                continue
            path = item["path"]
            if not path.startswith(prefix):
                continue
            relative_path = path.removeprefix(prefix)
            size = item.get("size")
            digest = item.get("sha256")
            if (
                isinstance(size, bool)
                or not isinstance(size, int)
                or size < 0
                or not isinstance(digest, str)
                or not _SHA256_RE.fullmatch(digest)
            ):
                issues.append(
                    {
                        "kind": "candidate_skill_package_script_identity_invalid",
                        "skill": skill,
                    }
                )
                continue
            rows.append({"path": relative_path, "size": size, "sha256": digest})
        if not any(row["path"] == "runtime_contract.py" for row in rows):
            issues.append(
                {"kind": "candidate_runtime_contract_missing", "skill": skill}
            )
        else:
            result[skill] = canonical_fingerprint(
                sorted(rows, key=lambda row: row["path"])
            )
    return (result if not issues else None), issues


def capture_attempt(*, run_root: Path, attempt_id: str) -> dict[str, Any]:
    root = _run_root(run_root)
    run = _load_run(root)
    row, attempt_root = _attempt_paths(root, attempt_id, run=run)
    record = _load_attempt_record(attempt_root)
    capture_path = attempt_root / "evaluator-private" / "capture.json"
    if capture_path.exists() or capture_path.is_symlink():
        raise AgentEvalError("QTS output capture is immutable and already exists")
    target_root = attempt_root / "target"
    output_root = target_root / ".qa-eval-output"
    if record.get("execution") is None:
        raise AgentEvalError(
            "host execution observation must be recorded before capture"
        )
    baseline = _read_json(attempt_root / "evaluator-private" / "target-baseline.json")
    integrity_before = verify_workspace_unchanged(
        target_root,
        baseline,
        expected_synthetic_baseline_revision=record["synthetic_baseline_revision"],
    )
    capture: dict[str, Any] = {
        "schema_version": 1,
        "attempt_id": attempt_id,
        "captured_at": _now(),
        "host_execution_status": record["execution"]["status"],
        "target_integrity": integrity_before,
        "output": None,
        "copy": None,
        "status": "captured_ungraded",
        "issues": [],
    }
    try:
        output_scan = _scan_output_tree(output_root, qa_training_store.load_scenario())
        capture["output"] = output_scan
        if not output_scan["safe_to_copy"]:
            capture["issues"].append(
                {
                    "kind": "secret_shaped_output",
                    "paths": output_scan["secret_shaped_paths"],
                }
            )
        copied = qa_training_store._copy_safe_agent_output(
            output_root,
            attempt_root / "evaluator-private" / "captured-output",
        )
        capture["copy"] = copied
        if copied["status"] != "saved":
            capture["issues"].append({"kind": "output_copy_unverified"})
        unregistered = [
            row["path"]
            for row in output_scan["files"]
            if row["classification"] == "unregistered_or_internal"
        ]
        if unregistered:
            capture["issues"].append(
                {"kind": "unregistered_output_files", "paths": unregistered}
            )
        if not integrity_before["unchanged"]:
            capture["issues"].append({"kind": "target_integrity_failed"})
        capture["source_output_fingerprint"] = canonical_fingerprint(
            [
                {"path": row["path"], "size": row["size"], "sha256": row["sha256"]}
                for row in output_scan["files"]
            ]
        )
        capture["status"] = (
            "captured" if not capture["issues"] else "captured_needs_review"
        )
    except (AgentEvalError, OSError) as exc:
        capture["status"] = "capture_failed"
        capture["issues"].append(
            {"kind": "output_capture_error", "reason": type(exc).__name__}
        )
    atomic_write_json(capture_path, capture)
    row.update(
        {
            "status": capture["status"],
            "capture_fingerprint": canonical_fingerprint(capture),
        }
    )
    _write_run(root, run)
    return capture


def evaluate_attempt(*, run_root: Path, attempt_id: str) -> dict[str, Any]:
    root = _run_root(run_root)
    run = _load_run(root)
    row, attempt_root = _attempt_paths(root, attempt_id, run=run)
    record = _load_attempt_record(attempt_root)
    capture = _read_json(attempt_root / "evaluator-private" / "capture.json")
    evaluation_path = attempt_root / "evaluator-private" / "evaluation.json"
    if evaluation_path.exists() or evaluation_path.is_symlink():
        raise AgentEvalError("QTS evaluation result already exists")
    scenario = qa_training_store.load_scenario()
    target_root = attempt_root / "target"
    output_root = attempt_root / "evaluator-private" / "captured-output"
    baseline = _read_json(attempt_root / "evaluator-private" / "target-baseline.json")
    integrity = verify_workspace_unchanged(
        target_root,
        baseline,
        expected_synthetic_baseline_revision=record["synthetic_baseline_revision"],
    )
    result: dict[str, Any] = {
        "schema_version": 1,
        "attempt_id": attempt_id,
        "evaluated_at": _now(),
        "execution_status": record.get("execution", {}).get("status", "not_observed"),
        "effective_model_status": "unverified",
        "tool_trace_status": "unverified",
        "target_integrity": integrity,
        "capture_status": capture.get("status"),
        "captured_output_integrity": None,
        "public_artifact_index": None,
        "fixed_artifact_index": None,
        "artifact_manifest": None,
        "runtime_evidence": None,
        "docker_production_verifier_replay": "not_used",
        "production_verifier_independent_replay": {
            "overall_status": "evidence_unverified",
            "verify": {"status": "not_run"},
            "workflow_runtime": {"status": "not_run"},
            "original_agent_execution_proof": "unverified",
        },
        "judge_status": "not_run",
        "semantic_status": "not_evaluated",
        "workflow_completion": {
            "status": "not_semantically_verified",
            "claim": None,
        },
        "traceability_status": "evidence_unverified",
        "machine_checks": {
            "artifact_index": "not_run",
            "output_content_hashes": "not_run",
            "captured_output_integrity": "not_run",
            "runtime_record_binding": "not_run",
            "runtime_independent_replay": "not_run",
            "target_integrity": "pass" if integrity["unchanged"] else "fail",
            "entity_traceability": "evidence_unverified",
        },
        "machine_status": "needs_review",
        "overall_status": "needs_review",
        "issues": [],
    }
    result["issues"].extend(capture.get("issues", []))
    if result["execution_status"] != "completed":
        result["issues"].append({"kind": "host_execution_not_completed"})
    execution = record.get("execution")
    if (
        not isinstance(execution, dict)
        or execution.get("prompt_matches_prepared") is not True
    ):
        result["issues"].append({"kind": "handoff_prompt_not_verified"})
    if not integrity["unchanged"]:
        result["issues"].append({"kind": "target_integrity_failed_after_capture"})
    source_output: dict[str, Any] | None = None
    try:
        source_output = _scan_output_tree(target_root / ".qa-eval-output", scenario)
        current_fingerprint = canonical_fingerprint(
            [
                {"path": item["path"], "size": item["size"], "sha256": item["sha256"]}
                for item in source_output["files"]
            ]
        )
        if current_fingerprint != capture.get("source_output_fingerprint"):
            result["issues"].append({"kind": "output_changed_after_capture"})
    except (AgentEvalError, OSError) as exc:
        source_output = None
        result["issues"].append(
            {
                "kind": "output_integrity_failed_after_capture",
                "reason": type(exc).__name__,
            }
        )
    captured_integrity = _verify_captured_output_integrity(
        attempt_id=attempt_id,
        run_row=row,
        capture=capture,
        source_output=source_output,
        captured_root=output_root,
        scenario=scenario,
    )
    result["captured_output_integrity"] = captured_integrity
    result["machine_checks"]["output_content_hashes"] = (
        "verified" if captured_integrity["valid"] else "needs_review"
    )
    result["issues"].extend(
        {
            "kind": "captured_output_integrity_issue",
            "issue_kind": issue["kind"],
            **{key: value for key, value in issue.items() if key != "kind"},
        }
        for issue in captured_integrity["issues"]
    )
    if capture.get("status") == "capture_failed":
        result["issues"].append({"kind": "capture_not_completed"})
    elif (
        integrity["unchanged"]
        and source_output is not None
        and captured_integrity["valid"]
        and output_root.is_dir()
    ):
        public_contract = (
            target_root / ".qa-eval-tools" / "artifact-index-contract.json"
        )
        try:
            public = validate_public_artifact_index(output_root, public_contract)
            fixed = qa_training_store.validate_artifact_index(output_root, scenario)
            result["public_artifact_index"] = public
            result["fixed_artifact_index"] = fixed
            manifest = qa_training_store.build_artifact_manifest(output_root, fixed)
            result["artifact_manifest"] = manifest
            result["runtime_evidence"] = _validate_runtime_bindings(
                output_root, fixed["artifacts"]
            )
            source_fingerprints, source_manifest_issues = _runtime_source_fingerprints(
                row, record
            )
            if source_fingerprints is None:
                verify_replay: dict[str, Any] = {
                    "status": "evidence_unverified",
                    "captures": [],
                    "issues": source_manifest_issues,
                }
                workflow_replay: dict[str, Any] = {
                    "status": "evidence_unverified",
                    "captures": [],
                    "issues": source_manifest_issues,
                }
            else:
                verify_replay = evaluate_runtime_captures(
                    capture_root=output_root / ".runtime-evidence",
                    candidate_package_root=target_root / ".agents",
                    verifier_image=None,
                    fixed_evaluator_root=REPO_ROOT,
                    expected_artifacts=fixed["artifacts"],
                    trace_commands=None,
                    require_tool_trace=False,
                    expected_candidate_source_fingerprints=source_fingerprints,
                )
                workflow_replay = evaluate_workflow_runtime_capture(
                    capture_root=output_root / ".runtime-evidence",
                    candidate_package_root=target_root / ".agents",
                    verifier_image=None,
                    fixed_evaluator_root=REPO_ROOT,
                    expected_artifacts=fixed["artifacts"],
                    trace_commands=None,
                    require_tool_trace=False,
                    expected_candidate_source_fingerprint=source_fingerprints.get(
                        "qa-workflow"
                    ),
                )
            replay_statuses = {
                "verify": verify_replay.get("status", "evidence_unverified"),
                "workflow_runtime": workflow_replay.get(
                    "status", "evidence_unverified"
                ),
            }
            if "environment_error" in replay_statuses.values():
                replay_overall = "environment_error"
            elif "timeout" in replay_statuses.values():
                replay_overall = "timeout"
            elif "execution_error" in replay_statuses.values():
                replay_overall = "execution_error"
            elif "evidence_unverified" in replay_statuses.values():
                replay_overall = "evidence_unverified"
            elif "fail" in replay_statuses.values():
                replay_overall = "fail"
            elif all(status == "pass" for status in replay_statuses.values()):
                replay_overall = "pass"
            else:
                replay_overall = "evidence_unverified"
            result["production_verifier_independent_replay"] = {
                "execution_method": "bubblewrap_user_namespace"
                if source_fingerprints is not None
                else "not_started",
                "overall_status": replay_overall,
                "verify": verify_replay,
                "workflow_runtime": workflow_replay,
                "verifier_candidate_executed": any(
                    capture_result.get("candidate_execution", {}).get(
                        "candidate_executed"
                    )
                    is True
                    for capture_result in verify_replay.get("captures", [])
                )
                or workflow_replay.get("candidate_executed") is True,
                "replay_actor": "evaluator_subprocess",
                "original_agent_execution_proof": "unverified",
            }
            if replay_overall != "pass":
                result["issues"].append(
                    {
                        "kind": "production_verifier_independent_replay_not_pass",
                        "status": replay_overall,
                    }
                )
            result["issues"].append(
                {"kind": "original_agent_runtime_execution_unverified"}
            )
            result["machine_checks"] = {
                "artifact_index": "pass"
                if fixed.get("status") == "pass" and public.get("valid") is True
                else "needs_review",
                "output_content_hashes": "captured"
                if all(
                    item.get("sha256") is not None
                    for item in result["artifact_manifest"]["files"]
                    if item["classification"] == "qa_artifact"
                )
                else "evidence_unverified",
                "captured_output_integrity": "verified",
                "runtime_record_binding": result["runtime_evidence"]["status"],
                "runtime_independent_replay": replay_overall,
                "target_integrity": "pass" if integrity["unchanged"] else "fail",
                "entity_traceability": "evidence_unverified",
            }
            result["issues"].extend(
                {"kind": "runtime_evidence_issue", **issue}
                for issue in result["runtime_evidence"]["issues"]
            )
            result["issues"].extend(
                {"kind": "public_artifact_index_issue", **issue}
                for issue in public.get("issues", [])
            )
            result["issues"].extend(
                {"kind": "fixed_artifact_index_issue", **issue}
                for issue in fixed.get("issues", [])
            )
            result["issues"].extend(
                {"kind": "artifact_manifest_unclassified", "path": item["path"]}
                for item in manifest["files"]
                if item["classification"]
                in {
                    "unsafe_filesystem_entry",
                    "unsafe_symlink",
                    "unregistered_or_internal",
                }
            )
            workflow_claims = [
                item["workflow_can_complete_claim"]
                for item in result["runtime_evidence"]["invocations"]
                if item["operation"] == "workflow-runtime"
                and isinstance(item.get("workflow_can_complete_claim"), bool)
            ]
            if workflow_claims:
                result["workflow_completion"] = {
                    "status": "claimed_complete_unverified"
                    if any(workflow_claims)
                    else "claimed_incomplete_unverified",
                    "claim": workflow_claims[-1],
                }
            structurally_valid = (
                public.get("valid") is True
                and fixed.get("status") == "pass"
                and result["runtime_evidence"]["status"]
                == "capture_integrity_consistent"
                and replay_overall == "pass"
                and result["tool_trace_status"] == "verified"
                and not result["issues"]
                and capture.get("status") == "captured"
            )
            result["machine_status"] = "pass" if structurally_valid else "needs_review"
            result["overall_status"] = "needs_review"
        except (AgentEvalError, OSError, ValueError, json.JSONDecodeError) as exc:
            result["issues"].append(
                {"kind": "evaluation_error", "reason": type(exc).__name__}
            )
    atomic_write_json(evaluation_path, result)
    row.update(
        {
            "status": result["overall_status"],
            "evaluation_path": (
                f"attempts/{attempt_id}/evaluator-private/evaluation.json"
            ),
            "evaluation_fingerprint": canonical_fingerprint(result),
        }
    )
    _write_run(root, run)
    return result


def _print_json(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Prepare and evaluate host-run QTS subagent attempts."
    )
    commands = parser.add_subparsers(dest="command", required=True)
    prepare = commands.add_parser("prepare")
    prepare.add_argument("--target-source-root", type=Path, required=True)
    prepare.add_argument("--source-provenance", type=Path)
    prepare.add_argument("--skill-revision", required=True)
    prepare.add_argument("--output-root", type=Path, required=True)
    prepare.add_argument("--repeat", type=int, default=2)
    prepare.add_argument("--model", default="gpt-6-luna")
    prepare.add_argument("--reasoning-effort", default="max")
    prepare.add_argument("--fork-turns", default="none")
    record = commands.add_parser("record-execution")
    record.add_argument("--run-root", type=Path, required=True)
    record.add_argument("--attempt-id", required=True)
    record.add_argument(
        "--execution-status",
        choices=("completed", "failed", "not_started"),
        required=True,
    )
    record.add_argument("--started-at", required=True)
    record.add_argument("--finished-at", required=True)
    record.add_argument("--submitted-prompt-fingerprint")
    record.add_argument("--final-response-file", type=Path)
    record.add_argument("--host-observation", default="codex_subagent_tool_returned")
    capture = commands.add_parser("capture")
    capture.add_argument("--run-root", type=Path, required=True)
    capture.add_argument("--attempt-id", required=True)
    evaluate = commands.add_parser("evaluate")
    evaluate.add_argument("--run-root", type=Path, required=True)
    evaluate.add_argument("--attempt-id", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            result = prepare_run(
                target_source_root=args.target_source_root,
                skill_revision=args.skill_revision,
                output_root=args.output_root,
                source_provenance_path=args.source_provenance,
                repeat=args.repeat,
                model=args.model,
                reasoning_effort=args.reasoning_effort,
                fork_turns=args.fork_turns,
            )
        elif args.command == "record-execution":
            result = record_execution(
                run_root=args.run_root,
                attempt_id=args.attempt_id,
                execution_status=args.execution_status,
                started_at=args.started_at,
                finished_at=args.finished_at,
                submitted_prompt_fingerprint=args.submitted_prompt_fingerprint,
                final_response=(
                    read_regular_file_bytes(args.final_response_file).decode("utf-8")
                    if args.final_response_file
                    else None
                ),
                host_observation=args.host_observation,
            )
        elif args.command == "capture":
            result = capture_attempt(run_root=args.run_root, attempt_id=args.attempt_id)
        else:
            result = evaluate_attempt(
                run_root=args.run_root, attempt_id=args.attempt_id
            )
    except (AgentEvalError, OSError, ValueError) as exc:
        print(
            f"QTS subagent evaluation failed: {type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        return 2
    _print_json(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
