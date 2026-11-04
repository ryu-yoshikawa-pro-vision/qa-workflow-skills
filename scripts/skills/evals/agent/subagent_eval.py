from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import stat
import sys
import tempfile
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from scripts.skills.evals.agent import run as legacy_run
from scripts.skills.evals.agent.common import (
    MAX_TEXT_BYTES,
    AgentEvalError,
    atomic_write_json,
    atomic_write_text,
    canonical_fingerprint,
    read_regular_file_bytes,
    sanitize_diagnostic,
    sha256_bytes,
)
from scripts.skills.evals.agent.prompt_builder import build_generation_prompt
from scripts.skills.evals.agent.workspace import (
    assert_clean_checkout,
    create_skill_workspace,
    create_skill_workspace_from_root,
    resolve_commit,
)
from scripts.skills.evals.deterministic.run import grade as grade_deterministic
from scripts.skills.evals.semantic.prompt_builder import build_judge_prompt

REPO_ROOT = legacy_run.REPO_ROOT
RUN_SCHEMA_VERSION = 1
HANDOFF_SCHEMA_VERSION = 2
SUPPORTED_HANDOFF_SCHEMA_VERSIONS = {1, HANDOFF_SCHEMA_VERSION}
ATTEMPT_ID_RE = re.compile(r"^[0-9a-f]{32}$")
EXECUTION_STATUSES = {"completed", "failed", "timed_out", "not_started"}
AGENT_SUBMISSION_NAME = "submission.md"


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise AgentEvalError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _read_regular_bytes(path: Path, *, max_bytes: int = MAX_TEXT_BYTES) -> bytes:
    return read_regular_file_bytes(path, max_bytes=max_bytes)


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(
            _read_regular_bytes(path).decode("utf-8"), object_pairs_hook=_strict_object
        )
    except (AgentEvalError, UnicodeError, json.JSONDecodeError) as exc:
        raise AgentEvalError(f"invalid JSON evidence: {path.name}") from exc
    if not isinstance(value, dict):
        raise AgentEvalError(f"JSON evidence must be an object: {path.name}")
    return value


def _assert_keys(value: dict[str, Any], required: set[str], name: str) -> None:
    if set(value) != required:
        raise AgentEvalError(f"{name} has an invalid field set")


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


def _fresh_run_root(path: Path) -> Path:
    repository = REPO_ROOT.resolve()
    root = Path(os.path.abspath(path))
    try:
        relative = root.relative_to(repository)
    except ValueError as exc:
        raise AgentEvalError(
            "subagent run root must be under the Evaluator checkout"
        ) from exc
    if len(relative.parts) < 2 or relative.parts[0] != ".agent-eval-runs":
        raise AgentEvalError("subagent run root must be under .agent-eval-runs/")
    _assert_no_symlink_components(root)
    if root.exists():
        raise AgentEvalError("subagent run root must not already exist")
    else:
        root.mkdir(parents=True, mode=0o700)
        root.chmod(0o700)
    return root


def _safe_run_root(path: Path) -> Path:
    repository = REPO_ROOT.resolve()
    root = Path(os.path.abspath(path))
    try:
        relative = root.relative_to(repository)
    except ValueError as exc:
        raise AgentEvalError(
            "subagent run root is outside the Evaluator checkout"
        ) from exc
    if len(relative.parts) < 2 or relative.parts[0] != ".agent-eval-runs":
        raise AgentEvalError("subagent run root must be under .agent-eval-runs/")
    _assert_no_symlink_components(root)
    if not root.is_dir():
        raise AgentEvalError("subagent run root does not exist")
    return root


@contextmanager
def _run_record_lock(path: Path) -> Iterator[Path]:
    """Serialize a run's full result.json read/validate/update/write transaction."""
    root = _safe_run_root(path)
    lock_path = root / ".result.lock"
    _assert_no_symlink_components(lock_path)
    flags = os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(lock_path, flags, 0o600)
    except OSError as exc:
        raise AgentEvalError("could not open the run-state lock") from exc

    acquired = False
    try:
        info = os.fstat(descriptor)
        current = lock_path.lstat()
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_nlink != 1
            or (info.st_dev, info.st_ino) != (current.st_dev, current.st_ino)
        ):
            raise AgentEvalError("run-state lock is not a private regular file")
        if os.name != "nt" and stat.S_IMODE(info.st_mode) & 0o077:
            raise AgentEvalError("run-state lock permissions are too broad")

        if os.name == "nt":
            import msvcrt

            if info.st_size == 0:
                os.write(descriptor, b"\0")
                os.fsync(descriptor)
            os.lseek(descriptor, 0, os.SEEK_SET)
            try:
                msvcrt.locking(descriptor, msvcrt.LK_LOCK, 1)
            except OSError as exc:
                raise AgentEvalError("could not acquire the run-state lock") from exc

            acquired = True
            try:
                yield root
            finally:
                try:
                    os.lseek(descriptor, 0, os.SEEK_SET)
                    msvcrt.locking(descriptor, msvcrt.LK_UNLCK, 1)
                except OSError as exc:
                    raise AgentEvalError(
                        "could not release the run-state lock"
                    ) from exc
                acquired = False
        else:
            try:
                import fcntl

                fcntl.flock(descriptor, fcntl.LOCK_EX)
            except (ImportError, OSError) as exc:
                raise AgentEvalError("could not acquire the run-state lock") from exc

            acquired = True
            try:
                yield root
            finally:
                try:
                    fcntl.flock(descriptor, fcntl.LOCK_UN)
                except OSError as exc:
                    raise AgentEvalError(
                        "could not release the run-state lock"
                    ) from exc
                acquired = False
    finally:
        if acquired:
            # A failed unlock is surfaced above; closing still releases OS locks.
            os.close(descriptor)
        else:
            os.close(descriptor)


def _regular_file(path: Path, *, max_bytes: int = MAX_TEXT_BYTES) -> bytes:
    return _read_regular_bytes(path, max_bytes=max_bytes)


def _case_for(suite: str, skill: str, eval_id: str) -> dict[str, Any]:
    if suite == "deterministic":
        cases = legacy_run._load_deterministic_cases(skill, eval_id)
    else:
        cases = legacy_run._load_semantic_cases(skill, eval_id)
    matching = [
        case for case in cases if case["skill"] == skill and case["id"] == eval_id
    ]
    if len(matching) != 1:
        raise AgentEvalError("fixed Evaluator must resolve exactly one case")
    case = matching[0]
    case["suite"] = suite
    case["eval_id"] = eval_id
    return case


def _dataset_fingerprint(case: dict[str, Any]) -> str:
    return legacy_run._dataset_fingerprint(case["fingerprint_files"])


def _package_files(root: Path, skill: str) -> list[dict[str, Any]]:
    skill_root = root / skill
    if skill_root.is_symlink() or not skill_root.is_dir():
        raise AgentEvalError("prepared Skill package is missing")
    rows: list[dict[str, Any]] = []
    for path in sorted(skill_root.rglob("*")):
        if path.is_symlink():
            raise AgentEvalError("prepared Skill package contains a symlink")
        if path.is_dir():
            continue
        if not path.is_file():
            raise AgentEvalError("prepared Skill package contains a non-file")
        relative = path.relative_to(root.parent).as_posix()
        if (
            "/evals/" in f"/{relative}/"
            or "__pycache__" in path.parts
            or path.suffix in {".pyc", ".pyo"}
        ):
            raise AgentEvalError(
                "Evaluator data or Python bytecode is in the Skill package"
            )
        data = _regular_file(path)
        rows.append({"path": relative, "size": len(data), "sha256": sha256_bytes(data)})
    rows.sort(key=lambda row: row["path"])
    if not rows or not any(row["path"].endswith(f"/{skill}/SKILL.md") for row in rows):
        raise AgentEvalError("prepared Skill package has no SKILL.md")
    return rows


def _validate_package(
    run_root: Path, attempt_root: Path, attempt: dict[str, Any], record: dict[str, Any]
) -> None:
    skill = attempt["skill"]
    package = record["skill_package"]
    _assert_keys(
        package,
        {"revision", "skills", "files", "package_fingerprint"},
        "Skill package manifest",
    )
    if package["skills"] != [skill] or package["revision"] != record["skill_revision"]:
        raise AgentEvalError("Skill package manifest does not match the fixed attempt")
    files = package["files"]
    if not isinstance(files, list) or not files:
        raise AgentEvalError("Skill package manifest has no files")
    expected = canonical_fingerprint(files)
    if package["package_fingerprint"] != expected:
        raise AgentEvalError("Skill package fingerprint is inconsistent")

    private_root = run_root / "evaluator-private" / "skill-source" / "skills"
    visible_root = attempt_root / "agent-visible" / ".agents" / "skills"
    _assert_no_symlink_components(private_root / skill)
    _assert_no_symlink_components(visible_root / skill)
    private_rows = _package_files(private_root, skill)
    visible_rows = _package_files(visible_root, skill)
    if private_rows != files or visible_rows != files:
        raise AgentEvalError("Skill package files differ from the prepared manifest")

    visible_root = attempt_root / "agent-visible"
    expected_visible = {"task.md"}
    expected_visible.update(
        f".agents/skills/{skill}/{row['path'].split(f'skills/{skill}/', 1)[1]}"
        for row in files
    )
    actual_visible: set[str] = set()
    for path in visible_root.rglob("*"):
        if path.is_symlink():
            raise AgentEvalError("Agent-visible workspace contains a symlink")
        if path.is_file():
            actual_visible.add(path.relative_to(visible_root).as_posix())
        elif not path.is_dir():
            raise AgentEvalError("Agent-visible workspace contains a non-file")
    if actual_visible != expected_visible:
        raise AgentEvalError("Agent-visible workspace has missing or unexpected files")


def _request_path(attempt_root: Path) -> Path:
    return attempt_root / "evaluator-private" / "request.json"


def _load_run(root: Path) -> dict[str, Any]:
    value = _read_json(root / "result.json")
    if (
        value.get("schema_version") != RUN_SCHEMA_VERSION
        or value.get("execution_method") != "codex_subagent_handoff"
    ):
        raise AgentEvalError("run result is not a supported subagent handoff run")
    if not isinstance(value.get("attempts"), list):
        raise AgentEvalError("run result has no attempts array")
    return value


def _attempt(
    root: Path, run: dict[str, Any], attempt_id: str
) -> tuple[dict[str, Any], Path]:
    if not ATTEMPT_ID_RE.fullmatch(attempt_id):
        raise AgentEvalError("attempt ID is invalid")
    rows = [
        row
        for row in run["attempts"]
        if isinstance(row, dict) and row.get("attempt_id") == attempt_id
    ]
    if len(rows) != 1:
        raise AgentEvalError("attempt ID is missing or duplicated")
    attempt_root = root / "attempts" / attempt_id
    _assert_no_symlink_components(attempt_root)
    if not attempt_root.is_dir():
        raise AgentEvalError("attempt directory is missing")
    return rows[0], attempt_root


def _write_new_json(path: Path, value: dict[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise AgentEvalError("refusing to overwrite existing attempt evidence")
    encoded = (
        json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    ).encode("utf-8")
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
        0o600,
    )
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
    except Exception:
        path.unlink(missing_ok=True)
        raise


def _mark_handoff_failure_locked(
    root: Path,
    attempt_id: str,
    reason: str,
    *,
    reported_execution_status: str | None = None,
) -> None:
    record = _load_run(root)
    row, _ = _attempt(root, record, attempt_id)
    if row.get("status") not in {"awaiting_agent", "output_captured"}:
        return
    row["status"] = "needs_review"
    row["handoff_validation"] = "failed"
    row["execution_evidence_status"] = "unverified"
    row["evidence_status"] = "evidence_unverified"
    if reported_execution_status is not None:
        row["reported_execution_status"] = reported_execution_status
    row["reason"] = sanitize_diagnostic(reason, 1000)
    record["intake_validation"] = "failed"
    _update_run_status(record)
    atomic_write_json(root / "result.json", record)


def _discard_sensitive_unsealed_output(attempt_root: Path) -> None:
    output = attempt_root / "handoff" / "output.md"
    try:
        _assert_no_symlink_components(output)
        info = output.lstat()
    except OSError:
        return
    if not stat.S_ISREG(info.st_mode):
        return
    try:
        output.unlink()
        directory_fd = os.open(
            output.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
        )
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    except OSError:
        return


def _capture_agent_output_locked(
    *, run_root: Path, attempt_id: str, content: bytes
) -> dict[str, Any]:
    """Persist returned Markdown only after size, encoding, and secret checks."""
    root = _safe_run_root(run_root)
    record = _load_run(root)
    row, attempt_root = _attempt(root, record, attempt_id)
    if row.get("status") != "awaiting_agent":
        raise AgentEvalError("attempt is not waiting for an Agent result")
    try:
        if (
            not isinstance(content, bytes)
            or not content
            or len(content) > MAX_TEXT_BYTES
        ):
            raise AgentEvalError("Agent output is empty or exceeds the size limit")
        try:
            output = content.decode("utf-8")
        except UnicodeError as exc:
            raise AgentEvalError("Agent output is not valid UTF-8") from exc
        if not output.strip():
            raise AgentEvalError("Agent output is empty")
        if legacy_run.SECRET_TEXT_RE.search(output):
            raise AgentEvalError(
                "Agent output may contain a secret; raw evidence was not imported"
            )

        handoff = attempt_root / "handoff"
        _assert_no_symlink_components(handoff)
        if not handoff.is_dir():
            raise AgentEvalError("handoff directory is missing")
        destination = handoff / "output.md"
        if destination.exists() or destination.is_symlink():
            raise AgentEvalError("refusing to overwrite an existing handoff artifact")
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=".output.", suffix=".tmp", dir=handoff
        )
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            os.link(temporary, destination, follow_symlinks=False)
            temporary.unlink()
            directory_fd = os.open(handoff, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        except Exception:
            temporary.unlink(missing_ok=True)
            raise
        record = _load_run(root)
        row, _ = _attempt(root, record, attempt_id)
        if row.get("status") != "awaiting_agent":
            raise AgentEvalError("attempt changed while Agent output was captured")
        row["captured_output"] = {
            "path": str(destination.relative_to(root)),
            "size_bytes": len(content),
            "sha256": sha256_bytes(content),
        }
        row["status"] = "output_captured"
        _update_run_status(record)
        atomic_write_json(root / "result.json", record)
        return {
            "path": str(destination.relative_to(root)),
            "size_bytes": len(content),
            "sha256": sha256_bytes(content),
        }
    except (AgentEvalError, OSError, ValueError) as exc:
        _mark_handoff_failure_locked(
            root,
            attempt_id,
            f"handoff capture failed: {type(exc).__name__}: {exc}",
        )
        raise


def capture_agent_output(
    *, run_root: Path, attempt_id: str, content: bytes
) -> dict[str, Any]:
    root = _safe_run_root(run_root)
    with _run_record_lock(root):
        return _capture_agent_output_locked(
            run_root=root, attempt_id=attempt_id, content=content
        )


def _read_agent_submission(directory_fd: int) -> tuple[bytes, tuple[int, int]]:
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(AGENT_SUBMISSION_NAME, flags, dir_fd=directory_fd)
    except OSError as exc:
        raise AgentEvalError("Agent-visible submission is unavailable") from exc
    with os.fdopen(descriptor, "rb") as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            raise AgentEvalError(
                "Agent-visible submission must be a singly-linked regular file"
            )
        if before.st_size > MAX_TEXT_BYTES:
            raise AgentEvalError("Agent-visible submission exceeds the size limit")
        content = stream.read(MAX_TEXT_BYTES + 1)
        after = os.fstat(stream.fileno())
    try:
        current = os.stat(
            AGENT_SUBMISSION_NAME, dir_fd=directory_fd, follow_symlinks=False
        )
    except OSError as exc:
        raise AgentEvalError(
            "Agent-visible submission changed while being read"
        ) from exc
    identity = (before.st_dev, before.st_ino)
    if (
        len(content) != before.st_size
        or len(content) > MAX_TEXT_BYTES
        or identity != (after.st_dev, after.st_ino)
        or (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns)
        or identity != (current.st_dev, current.st_ino)
        or not stat.S_ISREG(current.st_mode)
        or current.st_nlink != 1
    ):
        raise AgentEvalError("Agent-visible submission changed while being read")
    return content, identity


def _remove_agent_submission(directory_fd: int, identity: tuple[int, int]) -> None:
    try:
        current = os.stat(
            AGENT_SUBMISSION_NAME, dir_fd=directory_fd, follow_symlinks=False
        )
    except OSError as exc:
        raise AgentEvalError(
            "Agent-visible submission changed before import completed"
        ) from exc
    if (current.st_dev, current.st_ino) != identity or not stat.S_ISREG(
        current.st_mode
    ):
        raise AgentEvalError("Agent-visible submission changed before import completed")
    os.unlink(AGENT_SUBMISSION_NAME, dir_fd=directory_fd)
    os.fsync(directory_fd)


def _capture_agent_visible_output_locked(
    *, run_root: Path, attempt_id: str
) -> dict[str, Any]:
    """Import the fixed Agent-visible file without copying it through a transcript."""
    root = _safe_run_root(run_root)
    record = _load_run(root)
    row, attempt_root = _attempt(root, record, attempt_id)
    if row.get("status") != "awaiting_agent":
        raise AgentEvalError("attempt is not waiting for an Agent result")
    visible = attempt_root / "agent-visible"
    directory_fd: int | None = None
    identity: tuple[int, int] | None = None
    try:
        _assert_no_symlink_components(visible)
        directory_fd = os.open(
            visible,
            os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0),
        )
        content, identity = _read_agent_submission(directory_fd)
        try:
            captured = _capture_agent_output_locked(
                run_root=root, attempt_id=attempt_id, content=content
            )
        finally:
            _remove_agent_submission(directory_fd, identity)
        return captured
    except (AgentEvalError, OSError, ValueError) as exc:
        _mark_handoff_failure_locked(
            root,
            attempt_id,
            f"Agent-visible output import failed: {type(exc).__name__}: {exc}",
            reported_execution_status="completed",
        )
        raise
    finally:
        if directory_fd is not None:
            os.close(directory_fd)


def capture_agent_visible_output(*, run_root: Path, attempt_id: str) -> dict[str, Any]:
    root = _safe_run_root(run_root)
    with _run_record_lock(root):
        return _capture_agent_visible_output_locked(
            run_root=root, attempt_id=attempt_id
        )


def _validate_settings(value: dict[str, Any], name: str) -> None:
    _assert_keys(value, {"model", "reasoning_effort", "fork_turns"}, name)
    if any(
        not isinstance(value[field], str) or not value[field].strip() for field in value
    ):
        raise AgentEvalError(f"{name} values must be non-empty strings")
    if value["fork_turns"] not in {"none", "all"}:
        raise AgentEvalError(f"{name}.fork_turns is invalid")


def prepare_run(
    *,
    suite: str,
    skill: str,
    eval_id: str,
    skill_revision: str,
    output_root: Path,
    requested_settings: dict[str, str],
    repeat: int = 1,
    skill_package_root: Path | None = None,
) -> dict[str, Any]:
    if suite not in {"deterministic", "semantic"}:
        raise AgentEvalError("suite must be deterministic or semantic")
    if (
        isinstance(repeat, bool)
        or not isinstance(repeat, int)
        or not 1 <= repeat <= 100
    ):
        raise AgentEvalError("repeat must be an integer between 1 and 100")
    _validate_settings(requested_settings, "requested_settings")
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", skill):
        raise AgentEvalError("Skill name is invalid")
    if not re.fullmatch(r"[A-Z0-9]+-[A-Z0-9-]+", eval_id):
        raise AgentEvalError("Eval ID is invalid")

    evaluator_revision = assert_clean_checkout(REPO_ROOT)
    resolved_skill_revision = resolve_commit(REPO_ROOT, skill_revision)
    case = _case_for(suite, skill, eval_id)
    dataset_fingerprint = _dataset_fingerprint(case)
    root = _fresh_run_root(output_root)
    private_skill_root = root / "evaluator-private" / "skill-source"
    baseline_export = root / ".baseline-package-export"
    package_manifest_all = create_skill_workspace(
        REPO_ROOT, resolved_skill_revision, baseline_export
    )
    if skill not in package_manifest_all["skills"]:
        shutil.rmtree(baseline_export, ignore_errors=True)
        raise AgentEvalError("requested Skill is absent from the selected revision")

    candidate_status = "git_commit"
    if skill_package_root is None:
        package_source = baseline_export
        files = [
            row
            for row in package_manifest_all["files"]
            if row["path"].startswith(f"skills/{skill}/")
        ]
    else:
        candidate_source = Path(os.path.abspath(skill_package_root))
        _assert_no_symlink_components(candidate_source)
        if not candidate_source.is_dir() or candidate_source.is_symlink():
            raise AgentEvalError("candidate Skill package root must be a directory")
        try:
            candidate_source.relative_to(root)
        except ValueError:
            pass
        else:
            raise AgentEvalError("candidate Skill package must be outside the run root")
        candidate_export = root / ".candidate-package-export"
        candidate_manifest = create_skill_workspace_from_root(
            candidate_source,
            candidate_export,
            expected_skills={skill},
            parent_revision=resolved_skill_revision,
        )
        package_source = candidate_export
        files = candidate_manifest["files"]
        candidate_status = "uncommitted_patch"
    package_manifest = {
        "revision": resolved_skill_revision,
        "skills": [skill],
        "files": files,
        "package_fingerprint": canonical_fingerprint(files),
    }
    if not files:
        shutil.rmtree(baseline_export, ignore_errors=True)
        if package_source != baseline_export:
            shutil.rmtree(package_source, ignore_errors=True)
        raise AgentEvalError("selected Skill package is empty")

    private_skill_dir = private_skill_root / "skills" / skill
    for directory in (
        root / "evaluator-private",
        private_skill_root,
        private_skill_root / "skills",
        private_skill_dir.parent,
    ):
        directory.mkdir(mode=0o700, exist_ok=True)
        directory.chmod(0o700)
    shutil.copytree(package_source / "skills" / skill, private_skill_dir)
    shutil.rmtree(baseline_export)
    if package_source != baseline_export:
        shutil.rmtree(package_source)

    run_id = uuid.uuid4().hex
    attempts: list[dict[str, Any]] = []
    for repeat_index in range(1, repeat + 1):
        attempt_id = uuid.uuid4().hex
        attempt_root = root / "attempts" / attempt_id
        visible = attempt_root / "agent-visible"
        handoff = attempt_root / "handoff"
        private = attempt_root / "evaluator-private"
        for directory in (
            attempt_root,
            visible,
            visible / ".agents",
            visible / ".agents" / "skills",
            handoff,
            private,
        ):
            directory.mkdir(mode=0o700, parents=True, exist_ok=False)
            directory.chmod(0o700)
        shutil.copytree(private_skill_dir, visible / ".agents" / "skills" / skill)

        prompt = build_generation_prompt(skill=skill, eval_input=case["input"])
        prompt += (
            "\n\n# Host handoff\n"
            f"Write the exact requested final QA artifact to `{(visible / AGENT_SUBMISSION_NAME).as_posix()}`. "
            "Do not return a transcript copy of the artifact to the parent host. "
            "Do not claim an evaluation result, grader status, or execution evidence.\n"
        )
        task_path = visible / "task.md"
        atomic_write_text(task_path, prompt)
        input_fingerprint = sha256_bytes(case["input"].encode("utf-8"))
        request = {
            "schema_version": 1,
            "request_id": attempt_id,
            "run_id": run_id,
            "suite": suite,
            "skill": skill,
            "eval_id": eval_id,
            "repeat": repeat_index,
            "evaluator_revision": evaluator_revision,
            "skill_revision": resolved_skill_revision,
            "dataset_fingerprint": dataset_fingerprint,
            "input_fingerprint": input_fingerprint,
            "prompt_sha256": sha256_bytes(prompt.encode("utf-8")),
            "skill_package": package_manifest,
            "requested_settings": requested_settings,
            "effective_settings": {"status": "unverified"},
            "physical_read_denial": "unverified",
        }
        request_path = _request_path(attempt_root)
        _write_new_json(request_path, request)
        attempts.append(
            {
                "attempt_id": attempt_id,
                "suite": suite,
                "skill": skill,
                "eval_id": eval_id,
                "repeat": repeat_index,
                "input_fingerprint": input_fingerprint,
                "status": "awaiting_agent",
                "host_execution": {
                    "status": "not_recorded",
                    "verification": "unverified",
                },
                "effective_settings_status": "unverified",
                "execution_evidence_status": "unverified",
                "skill_use_observation": "unverified",
                "request_sha256": sha256_bytes(request_path.read_bytes()),
            }
        )

    record = {
        "schema_version": RUN_SCHEMA_VERSION,
        "run_id": run_id,
        "execution_method": "codex_subagent_handoff",
        "evaluation_mode": "development",
        "suite": suite,
        "status": "awaiting_agent",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "evaluator": {"revision": evaluator_revision},
        "skill_revision": resolved_skill_revision,
        "skill_candidate_revision_status": candidate_status,
        "skill_package": package_manifest,
        "dataset_fingerprint": dataset_fingerprint,
        "visible_skills": [skill],
        "profile_verification": "unverified",
        "agent": {
            "name": "codex-subagent",
            "model": requested_settings["model"],
            "reasoning_effort": requested_settings["reasoning_effort"],
            "fork_turns": requested_settings["fork_turns"],
            "effective_settings_status": "unverified",
            "version": None,
        },
        "isolation": {
            "method": "shared_codex_parent_session",
            "evaluator_read_blocked": "unverified",
            "physical_read_denial": "unverified",
        },
        "subagent_settings_status": "requested_only",
        "cases_requested": 1,
        "repeat": repeat,
        "attempts": attempts,
        "excluded": [],
    }
    atomic_write_json(root / "result.json", record)
    return {
        "run_root": str(root),
        "result": str(root / "result.json"),
        "run_id": run_id,
        "attempts": attempts,
    }


def host_launch_request(*, run_root: Path, attempt_id: str) -> dict[str, Any]:
    """Validate one prepared attempt and return its host-side launch handoff."""
    root = _safe_run_root(run_root)
    with _run_record_lock(root):
        return _host_launch_request_locked(run_root=root, attempt_id=attempt_id)


def _host_launch_request_locked(*, run_root: Path, attempt_id: str) -> dict[str, Any]:
    root = _safe_run_root(run_root)
    record = _load_run(root)
    row, attempt_root = _attempt(root, record, attempt_id)
    if row.get("status") != "awaiting_agent":
        raise AgentEvalError("attempt is not waiting for an Agent launch")

    visible = attempt_root / "agent-visible"
    _assert_no_symlink_components(visible)
    if not visible.is_dir():
        raise AgentEvalError("Agent-visible workspace is missing")
    submission = visible / AGENT_SUBMISSION_NAME
    if submission.exists() or submission.is_symlink():
        raise AgentEvalError("stale Agent-visible submission already exists")
    handoff = attempt_root / "handoff"
    _assert_no_symlink_components(handoff)
    if not handoff.is_dir():
        raise AgentEvalError("handoff directory is missing")
    if any(handoff.iterdir()):
        raise AgentEvalError("handoff directory is not empty before Agent launch")

    _validate_prepared_inputs(root, record, row, attempt_root)
    request_path = _request_path(attempt_root)
    request_bytes = _regular_file(request_path)
    request_sha = sha256_bytes(request_bytes)
    if row.get("request_sha256") != request_sha:
        raise AgentEvalError("prepared request changed after attempt creation")
    request = _read_json(request_path)
    _assert_keys(
        request,
        {
            "schema_version",
            "request_id",
            "run_id",
            "suite",
            "skill",
            "eval_id",
            "repeat",
            "evaluator_revision",
            "skill_revision",
            "dataset_fingerprint",
            "input_fingerprint",
            "prompt_sha256",
            "skill_package",
            "requested_settings",
            "effective_settings",
            "physical_read_denial",
        },
        "prepared request",
    )
    if (
        request["schema_version"] != 1
        or request["request_id"] != attempt_id
        or request["run_id"] != record.get("run_id")
        or request["suite"] != record.get("suite")
        or request["suite"] != row.get("suite")
        or request["skill"] != row.get("skill")
        or request["eval_id"] != row.get("eval_id")
        or request["repeat"] != row.get("repeat")
        or request["effective_settings"] != {"status": "unverified"}
        or request["physical_read_denial"] != "unverified"
    ):
        raise AgentEvalError("prepared request identity differs from the run")
    _validate_settings(request["requested_settings"], "prepared request settings")

    visible = visible.resolve(strict=True)
    task_path = (visible / "task.md").resolve(strict=True)
    skill_package_root = (visible / ".agents" / "skills" / row["skill"]).resolve(
        strict=True
    )
    skill_entrypoint = (skill_package_root / "SKILL.md").resolve(strict=True)
    submission_path = visible / AGENT_SUBMISSION_NAME
    host_launch_message = (
        f"Work only on prepared attempt {attempt_id}. Use `tools.exec_command()` "
        f"with `workdir` set to the absolute directory `{visible}`. Read only "
        f"`{task_path}` and the complete staged Skill package rooted at "
        f"`{skill_package_root}`. Use the package in full, including its "
        "references, scripts, and assets; do not narrow it to selected files. "
        f"Follow the task and "
        f"write the final Markdown only to `{submission_path}`. The submission "
        "file is expected not to exist before launch; check its parent directory "
        "instead of requiring the output file to pre-exist. Your first tool action "
        f"must verify `pwd`, `{task_path}`, and `{skill_entrypoint}` using "
        f"the exact absolute paths from attempt `{attempt_id}`; if any check fails, stop and report the "
        "check output without guessing a relative path. Do not inspect "
        "expected data, the grader, evaluator-private files, or any other attempt. "
        "Do not return a transcript copy of the artifact."
    )
    return {
        "run_id": record["run_id"],
        "attempt_id": attempt_id,
        "artifact_attempt_id": attempt_id,
        "working_directory": str(visible),
        "task_path": str(task_path),
        "skill_package_root": str(skill_package_root),
        "skill_entrypoint": str(skill_entrypoint),
        "submission_path": str(submission_path),
        "requested_settings": request["requested_settings"],
        "host_launch_message": host_launch_message,
        "request_sha256": request_sha,
    }


def _timestamp(value: str | None, field: str) -> str | None:
    if value is None:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise AgentEvalError(f"{field} must be an ISO timestamp") from exc
    if parsed.tzinfo is None:
        raise AgentEvalError(f"{field} must include a timezone")
    return parsed.astimezone(timezone.utc).isoformat()


def _seal_handoff_impl(
    *,
    run_root: Path,
    attempt_id: str,
    execution_status: str,
    execution_reason: str | None = None,
    artifact_attempt_id: str | None = None,
    started_at: str | None = None,
    finished_at: str | None = None,
) -> dict[str, Any]:
    root = _safe_run_root(run_root)
    record = _load_run(root)
    row, attempt_root = _attempt(root, record, attempt_id)
    if execution_status not in EXECUTION_STATUSES:
        raise AgentEvalError("execution status is invalid")
    if execution_status == "completed":
        if execution_reason is not None:
            raise AgentEvalError("completed execution may not have a failure reason")
        normalized_execution_reason = None
    else:
        if not isinstance(execution_reason, str) or not execution_reason.strip():
            raise AgentEvalError("non-completed execution requires an execution reason")
        normalized_execution_reason = sanitize_diagnostic(
            execution_reason.strip(), 1000
        )
        if not normalized_execution_reason:
            raise AgentEvalError("non-completed execution reason is empty")
    if row.get("status") not in {"awaiting_agent", "output_captured"}:
        raise AgentEvalError("attempt is already sealed or was not prepared")

    handoff = attempt_root / "handoff"
    _assert_no_symlink_components(handoff)
    if not handoff.is_dir():
        raise AgentEvalError("handoff directory is missing")
    manifest_path = handoff / "manifest.json"
    if manifest_path.exists() or manifest_path.is_symlink():
        raise AgentEvalError("handoff manifest already exists")
    output_path = handoff / "output.md"
    artifacts: list[dict[str, Any]] = []
    if output_path.exists() or output_path.is_symlink():
        data = _regular_file(output_path)
        try:
            text = data.decode("utf-8")
        except UnicodeError as exc:
            raise AgentEvalError("Agent output is not valid UTF-8") from exc
        if not text.strip():
            raise AgentEvalError("Agent output is empty")
        if legacy_run.SECRET_TEXT_RE.search(text):
            raise AgentEvalError(
                "Agent output may contain a secret; raw evidence was not imported"
            )
        artifacts.append(
            {"path": "output.md", "size_bytes": len(data), "sha256": sha256_bytes(data)}
        )
    if execution_status == "completed" and not artifacts:
        raise AgentEvalError("completed host execution requires output.md")
    if execution_status == "not_started" and artifacts:
        raise AgentEvalError("not_started execution may not contain an Agent output")
    if artifacts and artifact_attempt_id != attempt_id:
        raise AgentEvalError(
            "artifact origin attempt ID does not match the prepared attempt"
        )
    if not artifacts and artifact_attempt_id is not None:
        raise AgentEvalError("artifact origin ID was supplied without an artifact")
    captured_output = row.get("captured_output")
    if row.get("status") == "output_captured" and not isinstance(captured_output, dict):
        raise AgentEvalError("captured output state has no integrity record")
    if captured_output is not None and not artifacts:
        raise AgentEvalError("captured output is missing from the handoff")
    if captured_output is not None and artifacts:
        if captured_output != {
            "path": str(output_path.relative_to(root)),
            "size_bytes": artifacts[0]["size_bytes"],
            "sha256": artifacts[0]["sha256"],
        }:
            raise AgentEvalError("captured output differs from the sealed artifact")

    request_path = _request_path(attempt_root)
    request = _read_json(request_path)
    request_bytes = _regular_file(request_path)
    request_sha = sha256_bytes(request_bytes)
    manifest = {
        "schema_version": HANDOFF_SCHEMA_VERSION,
        "attempt_id": attempt_id,
        "request_sha256": request_sha,
        "execution_status": execution_status,
        "execution_reason": normalized_execution_reason,
        "artifact_attempt_id": artifact_attempt_id,
        "observation_source": "parent_codex_session_recorded",
        "observation_verification": "unverified",
        "started_at": _timestamp(started_at, "started_at"),
        "finished_at": _timestamp(finished_at, "finished_at"),
        "requested_settings": request["requested_settings"],
        "effective_settings": {"status": "unverified"},
        "skill_use_observation": "unverified",
        "artifacts": artifacts,
    }
    actual_files: set[str] = set()
    for path in handoff.iterdir():
        if path.is_symlink() or not path.is_file():
            raise AgentEvalError("handoff directory contains an unsafe entry")
        actual_files.add(path.relative_to(handoff).as_posix())
    expected_files = {"output.md"} if artifacts else set()
    if actual_files != expected_files:
        raise AgentEvalError("handoff directory contains missing or unexpected files")
    _write_new_json(manifest_path, manifest)
    row["host_execution"] = {
        "status": execution_status,
        "execution_reason": normalized_execution_reason,
        "source": manifest["observation_source"],
        "verification": manifest["observation_verification"],
        "started_at": manifest["started_at"],
        "finished_at": manifest["finished_at"],
    }
    row["effective_settings_status"] = "unverified"
    row["execution_evidence_status"] = "unverified"
    row["skill_use_observation"] = "unverified"
    row["handoff_manifest"] = {
        "path": str(manifest_path.relative_to(root)),
        "sha256": sha256_bytes(manifest_path.read_bytes()),
    }
    if artifacts:
        row["ungraded_output"] = {
            "path": str(output_path.relative_to(root)),
            "sha256": artifacts[0]["sha256"],
        }
    row["status"] = (
        "awaiting_grading"
        if execution_status == "completed"
        else ("not_started" if execution_status == "not_started" else "execution error")
    )
    _update_run_status(record)
    atomic_write_json(root / "result.json", record)
    return manifest


def seal_handoff(
    *,
    run_root: Path,
    attempt_id: str,
    execution_status: str,
    execution_reason: str | None = None,
    artifact_attempt_id: str | None = None,
    started_at: str | None = None,
    finished_at: str | None = None,
) -> dict[str, Any]:
    root = _safe_run_root(run_root)
    with _run_record_lock(root):
        return _seal_handoff_locked(
            run_root=root,
            attempt_id=attempt_id,
            execution_status=execution_status,
            execution_reason=execution_reason,
            artifact_attempt_id=artifact_attempt_id,
            started_at=started_at,
            finished_at=finished_at,
        )


def _seal_handoff_locked(
    *,
    run_root: Path,
    attempt_id: str,
    execution_status: str,
    execution_reason: str | None = None,
    artifact_attempt_id: str | None = None,
    started_at: str | None = None,
    finished_at: str | None = None,
) -> dict[str, Any]:
    try:
        return _seal_handoff_impl(
            run_root=run_root,
            attempt_id=attempt_id,
            execution_status=execution_status,
            execution_reason=execution_reason,
            artifact_attempt_id=artifact_attempt_id,
            started_at=started_at,
            finished_at=finished_at,
        )
    except (AgentEvalError, OSError, ValueError) as exc:
        try:
            root = _safe_run_root(run_root)
            _, attempt_root = _attempt(root, _load_run(root), attempt_id)
            if "may contain a secret" in str(exc):
                _discard_sensitive_unsealed_output(attempt_root)
            _mark_handoff_failure_locked(
                root,
                attempt_id,
                f"handoff intake failed: {type(exc).__name__}: {exc}",
                reported_execution_status=execution_status,
            )
        except (AgentEvalError, OSError, ValueError):
            raise exc
        raise


def _validate_handoff(
    root: Path, record: dict[str, Any], row: dict[str, Any], attempt_root: Path
) -> tuple[dict[str, Any], Path | None]:
    handoff = attempt_root / "handoff"
    manifest_path = handoff / "manifest.json"
    manifest = _read_json(manifest_path)
    schema_version = manifest.get("schema_version")
    base_manifest_keys = {
        "schema_version",
        "attempt_id",
        "request_sha256",
        "execution_status",
        "artifact_attempt_id",
        "observation_source",
        "observation_verification",
        "started_at",
        "finished_at",
        "requested_settings",
        "effective_settings",
        "skill_use_observation",
        "artifacts",
    }
    if (
        type(schema_version) is not int
        or schema_version not in SUPPORTED_HANDOFF_SCHEMA_VERSIONS
    ):
        raise AgentEvalError("handoff manifest schema version is unsupported")
    manifest_keys = (
        base_manifest_keys | {"execution_reason"}
        if schema_version >= HANDOFF_SCHEMA_VERSION
        else base_manifest_keys
    )
    _assert_keys(manifest, manifest_keys, "handoff manifest")
    if manifest["attempt_id"] != row["attempt_id"]:
        raise AgentEvalError("handoff manifest identity does not match the attempt")
    if manifest["execution_status"] not in EXECUTION_STATUSES:
        raise AgentEvalError("handoff execution status is invalid")
    if schema_version == 1:
        execution_reason = None
    else:
        execution_reason = manifest["execution_reason"]
        if manifest["execution_status"] == "completed":
            if execution_reason is not None:
                raise AgentEvalError("completed handoff may not have a failure reason")
        elif (
            not isinstance(execution_reason, str)
            or not execution_reason.strip()
            or sanitize_diagnostic(execution_reason.strip(), 1000) != execution_reason
        ):
            raise AgentEvalError("handoff execution reason is invalid")
    if manifest["artifacts"]:
        if manifest["artifact_attempt_id"] != row["attempt_id"]:
            raise AgentEvalError(
                "artifact origin attempt ID differs from the prepared attempt"
            )
    elif manifest["artifact_attempt_id"] is not None:
        raise AgentEvalError("artifact origin was recorded without an artifact")
    if (
        manifest["observation_source"] != "parent_codex_session_recorded"
        or manifest["observation_verification"] != "unverified"
    ):
        raise AgentEvalError("host observation must remain explicitly unverified")
    if (
        manifest["effective_settings"] != {"status": "unverified"}
        or manifest["skill_use_observation"] != "unverified"
    ):
        raise AgentEvalError("unverified host evidence may not be promoted")
    host_execution = row.get("host_execution")
    if not isinstance(host_execution, dict):
        raise AgentEvalError("recorded host execution evidence is malformed")
    if host_execution.get("status") != manifest["execution_status"]:
        raise AgentEvalError("handoff status differs from the recorded host status")
    if (
        schema_version >= HANDOFF_SCHEMA_VERSION
        and host_execution.get("execution_reason") != execution_reason
    ):
        raise AgentEvalError("handoff execution reason differs from the host record")

    request_path = _request_path(attempt_root)
    request = _read_json(request_path)
    _assert_keys(
        request,
        {
            "schema_version",
            "request_id",
            "run_id",
            "suite",
            "skill",
            "eval_id",
            "repeat",
            "evaluator_revision",
            "skill_revision",
            "dataset_fingerprint",
            "input_fingerprint",
            "prompt_sha256",
            "skill_package",
            "requested_settings",
            "effective_settings",
            "physical_read_denial",
        },
        "prepared request",
    )
    request_bytes = _regular_file(request_path)
    if manifest["request_sha256"] != sha256_bytes(request_bytes):
        raise AgentEvalError("prepared request hash does not match the handoff")
    if row.get("request_sha256") != sha256_bytes(request_bytes):
        raise AgentEvalError("prepared request changed after attempt creation")
    if (
        request["schema_version"] != 1
        or request["effective_settings"] != {"status": "unverified"}
        or request["physical_read_denial"] != "unverified"
        or request["request_id"] != row["attempt_id"]
        or request["run_id"] != record.get("run_id")
        or request["suite"] != row["suite"]
        or request["skill"] != row["skill"]
        or request["eval_id"] != row["eval_id"]
        or request["repeat"] != row["repeat"]
        or request["evaluator_revision"] != record.get("evaluator", {}).get("revision")
        or request["skill_revision"] != record.get("skill_revision")
        or request["dataset_fingerprint"] != record.get("dataset_fingerprint")
        or request["input_fingerprint"] != row.get("input_fingerprint")
    ):
        raise AgentEvalError("prepared request identity differs from the run")
    _validate_settings(manifest["requested_settings"], "handoff.requested_settings")
    _validate_settings(request["requested_settings"], "prepared request settings")
    if manifest["requested_settings"] != request["requested_settings"]:
        raise AgentEvalError("requested Agent settings changed after preparation")

    artifacts = manifest["artifacts"]
    if not isinstance(artifacts, list) or len(artifacts) > 1:
        raise AgentEvalError("handoff manifest must contain at most one artifact")
    if manifest["execution_status"] == "completed" and len(artifacts) != 1:
        raise AgentEvalError(
            "completed execution must contain exactly one output artifact"
        )
    if manifest["execution_status"] == "not_started" and artifacts:
        raise AgentEvalError("not_started handoff may not contain artifacts")

    output_path: Path | None = None
    expected_names: set[str] = {"manifest.json"}
    if artifacts:
        artifact = artifacts[0]
        if not isinstance(artifact, dict) or set(artifact) != {
            "path",
            "size_bytes",
            "sha256",
        }:
            raise AgentEvalError("handoff artifact entry has an invalid shape")
        if artifact["path"] != "output.md":
            raise AgentEvalError("only output.md is accepted in this evaluation stage")
        if (
            isinstance(artifact["size_bytes"], bool)
            or not isinstance(artifact["size_bytes"], int)
            or artifact["size_bytes"] <= 0
        ):
            raise AgentEvalError("handoff artifact size is invalid")
        if not isinstance(artifact["sha256"], str) or not re.fullmatch(
            r"sha256:[0-9a-f]{64}", artifact["sha256"]
        ):
            raise AgentEvalError("handoff artifact hash is invalid")
        output_path = handoff / "output.md"
        data = _regular_file(output_path)
        if (
            len(data) != artifact["size_bytes"]
            or sha256_bytes(data) != artifact["sha256"]
        ):
            raise AgentEvalError("handoff artifact content does not match its manifest")
        try:
            text = data.decode("utf-8")
        except UnicodeError as exc:
            raise AgentEvalError("Agent output is not valid UTF-8") from exc
        if not text.strip() or legacy_run.SECRET_TEXT_RE.search(text):
            raise AgentEvalError("Agent output is empty or contains sensitive content")
        expected_names.add("output.md")
    actual_names = {path.name for path in handoff.iterdir()}
    if actual_names != expected_names:
        raise AgentEvalError("handoff directory has unexpected or duplicate files")

    if row.get("handoff_manifest", {}).get("path") != str(
        manifest_path.relative_to(root)
    ):
        raise AgentEvalError("handoff manifest path does not match the attempt")
    if row.get("handoff_manifest", {}).get("sha256") != sha256_bytes(
        _regular_file(manifest_path)
    ):
        raise AgentEvalError("handoff manifest changed after intake")
    captured_output = row.get("captured_output")
    if captured_output is not None:
        if output_path is None or captured_output != {
            "path": str(output_path.relative_to(root)),
            "size_bytes": manifest["artifacts"][0]["size_bytes"],
            "sha256": manifest["artifacts"][0]["sha256"],
        }:
            raise AgentEvalError("captured output record differs from sealed evidence")
    return manifest, output_path


def _validate_prepared_inputs(
    root: Path, record: dict[str, Any], row: dict[str, Any], attempt_root: Path
) -> dict[str, Any]:
    if assert_clean_checkout(REPO_ROOT) != record.get("evaluator", {}).get("revision"):
        raise AgentEvalError("Evaluator checkout changed after attempt preparation")
    if record.get("skill_candidate_revision_status") not in {
        "git_commit",
        "uncommitted_patch",
    }:
        raise AgentEvalError("Skill candidate revision status is invalid")
    request_path = _request_path(attempt_root)
    request = _read_json(request_path)
    if request.get("request_id") != row.get("attempt_id"):
        raise AgentEvalError("prepared request does not match the attempt ID")
    if request.get("evaluator_revision") != record["evaluator"]["revision"]:
        raise AgentEvalError("prepared request has a different Evaluator revision")
    if request.get("skill_revision") != record.get("skill_revision"):
        raise AgentEvalError("prepared request has a different Skill revision")
    if request.get("dataset_fingerprint") != record.get("dataset_fingerprint"):
        raise AgentEvalError("prepared request has a different dataset fingerprint")

    case = _case_for(record["suite"], row["skill"], row["eval_id"])
    if _dataset_fingerprint(case) != record["dataset_fingerprint"]:
        raise AgentEvalError("fixed Evaluator case changed after attempt preparation")
    if sha256_bytes(case["input"].encode("utf-8")) != row.get("input_fingerprint"):
        raise AgentEvalError("Eval Input changed after attempt preparation")
    task_path = attempt_root / "agent-visible" / "task.md"
    task_bytes = _regular_file(task_path)
    if sha256_bytes(task_bytes) != request.get("prompt_sha256"):
        raise AgentEvalError("Agent-visible prompt changed after preparation")
    if request.get("skill_package") != record.get("skill_package"):
        raise AgentEvalError("prepared package manifest differs from the run manifest")
    if request.get("requested_settings") != {
        "model": record["agent"].get("model"),
        "reasoning_effort": record["agent"].get("reasoning_effort"),
        "fork_turns": record["agent"].get("fork_turns"),
    }:
        raise AgentEvalError("requested settings differ from the prepared run")
    _validate_package(root, attempt_root, row, record)
    return case


def _update_run_status(record: dict[str, Any]) -> None:
    statuses = [row.get("status") for row in record.get("attempts", [])]
    pending_statuses = {"awaiting_agent", "output_captured", "awaiting_grading"}
    if any(status in pending_statuses for status in statuses):
        if "awaiting_agent" in statuses:
            record["status"] = "awaiting_agent"
        elif "awaiting_grading" in statuses:
            record["status"] = "awaiting_grading"
        else:
            record["status"] = "output_captured"
    elif "awaiting_judge" in statuses:
        record["status"] = "needs_review_or_fail"
    elif "execution error" in statuses:
        record["status"] = "execution error"
    elif any(
        status in {"fail", "needs_review", "not_started", "not_comparable"}
        for status in statuses
    ):
        record["status"] = "needs_review_or_fail"
    elif statuses and all(status == "pass" for status in statuses):
        record["status"] = "pass"
    else:
        record["status"] = "needs_review_or_fail"
    record["summary"] = {
        status: statuses.count(status)
        for status in sorted({str(item) for item in statuses})
    }
    record["finished_at"] = (
        datetime.now(timezone.utc).isoformat()
        if not any(status in pending_statuses for status in statuses)
        else None
    )


def _grade_attempt_locked(*, run_root: Path, attempt_id: str) -> dict[str, Any]:
    root = _safe_run_root(run_root)
    record = _load_run(root)
    row, attempt_root = _attempt(root, record, attempt_id)
    if row.get("status") != "awaiting_grading":
        raise AgentEvalError("attempt is not ready for grading")
    try:
        manifest, output_path = _validate_handoff(root, record, row, attempt_root)
        case = _validate_prepared_inputs(root, record, row, attempt_root)
        if manifest["execution_status"] != "completed" or output_path is None:
            raise AgentEvalError("Agent execution was not completed")

        if record["suite"] == "deterministic":
            grade = grade_deterministic(
                row["skill"],
                row["eval_id"],
                output_path,
                runtime_source_root=root / "evaluator-private" / "skill-source",
            )
            grade_path = attempt_root / "grade.json"
            _write_new_json(grade_path, grade)
            row["grade"] = {
                "path": str(grade_path.relative_to(root)),
                "sha256": sha256_bytes(grade_path.read_bytes()),
            }
            row["status"] = grade["status"]
            row["grade_status"] = grade["status"]
        else:
            dataset = case["dataset"]
            eval_case = case["case"]
            criteria = [
                dataset["criteria_by_id"][item] for item in eval_case["criteria"]
            ]
            judge_prompt = build_judge_prompt(
                criteria=criteria,
                eval_input=eval_case["input_text"],
                reference=eval_case["reference_text"],
                candidate_output=output_path.read_text(encoding="utf-8"),
            )
            judge_prompt_path = attempt_root / "evaluator-private" / "judge-request.txt"
            if judge_prompt_path.exists() or judge_prompt_path.is_symlink():
                raise AgentEvalError("refusing to overwrite an existing Judge request")
            atomic_write_text(judge_prompt_path, judge_prompt)
            row["semantic_judge"] = {
                "status": "awaiting_judge",
                "prompt_path": str(judge_prompt_path.relative_to(root)),
                "prompt_sha256": sha256_bytes(judge_prompt.encode("utf-8")),
                "normalizer": "scripts/skills/evals/semantic/result.py:normalize_judge_response",
                "judge_execution": "unverified",
            }
            row["status"] = "awaiting_judge"
            row["reason"] = "independent Judge result has not been imported"
        row["output"] = {
            "path": str(output_path.relative_to(root)),
            "sha256": manifest["artifacts"][0]["sha256"],
        }
        row.pop("ungraded_output", None)
        row["execution_evidence_status"] = "unverified"
        row["effective_settings_status"] = "unverified"
        row["skill_use_observation"] = "unverified"
    except Exception as exc:
        row["status"] = "needs_review"
        row["evidence_status"] = "evidence_unverified"
        row["reason"] = sanitize_diagnostic(f"{type(exc).__name__}: {exc}", 1000)
        record["intake_validation"] = "failed"
        _update_run_status(record)
        atomic_write_json(root / "result.json", record)
        raise AgentEvalError("attempt evidence did not pass import validation") from exc
    record["intake_validation"] = "passed"
    _update_run_status(record)
    atomic_write_json(root / "result.json", record)
    return row


def grade_attempt(*, run_root: Path, attempt_id: str) -> dict[str, Any]:
    root = _safe_run_root(run_root)
    with _run_record_lock(root):
        return _grade_attempt_locked(run_root=root, attempt_id=attempt_id)


def _record_noncompleted_locked(*, run_root: Path, attempt_id: str) -> dict[str, Any]:
    root = _safe_run_root(run_root)
    record = _load_run(root)
    row, attempt_root = _attempt(root, record, attempt_id)
    if row.get("status") not in {"not_started", "execution error"}:
        raise AgentEvalError("attempt is not a non-completed host execution")
    manifest, output_path = _validate_handoff(root, record, row, attempt_root)
    _validate_prepared_inputs(root, record, row, attempt_root)
    if manifest["execution_status"] == "completed":
        raise AgentEvalError("completed attempt must use the grading path")
    row["execution_evidence_status"] = "unverified"
    row["effective_settings_status"] = "unverified"
    if output_path is not None:
        row["partial_output"] = {
            "path": str(output_path.relative_to(root)),
            "sha256": manifest["artifacts"][0]["sha256"],
        }
    record["intake_validation"] = "passed"
    _update_run_status(record)
    atomic_write_json(root / "result.json", record)
    return row


def _record_noncompleted(*, run_root: Path, attempt_id: str) -> dict[str, Any]:
    root = _safe_run_root(run_root)
    with _run_record_lock(root):
        return _record_noncompleted_locked(run_root=root, attempt_id=attempt_id)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare and import Agent-host subagent evaluations."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare = subparsers.add_parser(
        "prepare", help="Prepare one fixed Eval Input and attempt workspace."
    )
    prepare.add_argument(
        "--suite", choices=["deterministic", "semantic"], required=True
    )
    prepare.add_argument("--skill", required=True)
    prepare.add_argument("--eval-id", required=True)
    prepare.add_argument("--skill-revision", required=True)
    prepare.add_argument("--output-root", type=Path, required=True)
    prepare.add_argument(
        "--skill-package-root",
        type=Path,
        help="Optional uncommitted single-Skill candidate package for development comparison.",
    )
    prepare.add_argument("--repeat", type=int, default=1)
    prepare.add_argument("--model", required=True)
    prepare.add_argument("--reasoning-effort", required=True)
    prepare.add_argument("--fork-turns", choices=["none", "all"], required=True)

    host_request = subparsers.add_parser(
        "host-request",
        help="Validate one prepared attempt before manual Codex host launch.",
    )
    host_request.add_argument("--run-root", type=Path, required=True)
    host_request.add_argument("--attempt-id", required=True)

    seal = subparsers.add_parser(
        "seal", help="Record parent-host execution status and seal an attempt handoff."
    )
    seal.add_argument("--run-root", type=Path, required=True)
    seal.add_argument("--attempt-id", required=True)
    seal.add_argument(
        "--execution-status", choices=sorted(EXECUTION_STATUSES), required=True
    )
    seal.add_argument(
        "--execution-reason",
        help="Required host-observed reason when execution did not complete.",
    )
    seal.add_argument("--artifact-attempt-id")
    seal.add_argument("--started-at")
    seal.add_argument("--finished-at")

    capture = subparsers.add_parser(
        "capture", help="Check and save a subagent Markdown artifact."
    )
    capture.add_argument("--run-root", type=Path, required=True)
    capture.add_argument("--attempt-id", required=True)
    capture.add_argument(
        "--from-agent-visible",
        action="store_true",
        help=f"Import the exact {AGENT_SUBMISSION_NAME} file from the prepared workspace.",
    )

    grade = subparsers.add_parser(
        "grade", help="Verify the sealed handoff and run the fixed Evaluator."
    )
    grade.add_argument("--run-root", type=Path, required=True)
    grade.add_argument("--attempt-id", required=True)

    args = parser.parse_args(argv)
    return args


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        if args.command == "prepare":
            result = prepare_run(
                suite=args.suite,
                skill=args.skill,
                eval_id=args.eval_id,
                skill_revision=args.skill_revision,
                output_root=args.output_root,
                requested_settings={
                    "model": args.model,
                    "reasoning_effort": args.reasoning_effort,
                    "fork_turns": args.fork_turns,
                },
                repeat=args.repeat,
                skill_package_root=args.skill_package_root,
            )
        elif args.command == "host-request":
            result = host_launch_request(
                run_root=args.run_root,
                attempt_id=args.attempt_id,
            )
        elif args.command == "seal":
            result = seal_handoff(
                run_root=args.run_root,
                attempt_id=args.attempt_id,
                execution_status=args.execution_status,
                execution_reason=args.execution_reason,
                artifact_attempt_id=args.artifact_attempt_id,
                started_at=args.started_at,
                finished_at=args.finished_at,
            )
        elif args.command == "capture":
            if args.from_agent_visible:
                result = capture_agent_visible_output(
                    run_root=args.run_root, attempt_id=args.attempt_id
                )
            else:
                result = capture_agent_output(
                    run_root=args.run_root,
                    attempt_id=args.attempt_id,
                    content=sys.stdin.buffer.read(MAX_TEXT_BYTES + 1),
                )
        else:
            result = grade_attempt(run_root=args.run_root, attempt_id=args.attempt_id)
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (AgentEvalError, OSError, ValueError, KeyError) as exc:
        print(
            f"subagent evaluation failed: {sanitize_diagnostic(str(exc), 1000)}",
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
