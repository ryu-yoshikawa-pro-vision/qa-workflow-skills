"""Run an inspected non-E2E command in an isolated Git checkout.

This module does not authenticate provider approvals or reserve shared state.
It refuses shared/external effects and records runner evidence locally. The
caller must inspect the full command/package-script/fixture chain beforehand.
"""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import math
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

from contract import (
    ContractError,
    _json_equal_strict,
    _test_key,
    compare_direct,
    compare_metrics,
    diagnosis,
    preflight,
    reconcile_case_report,
    reconcile_playwright,
    reconcile_vitest,
)

KINDS = {
    "vitest",
    "playwright-api",
    "component",
    "batch",
    "event",
    "nonfunctional",
    "static",
}


class RunnerError(ValueError):
    """An operation cannot be started safely."""


def _no_duplicate_json_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """Do not silently overwrite reviewed plan, reporter or Authority values."""
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise RunnerError("duplicate_json_key")
        result[key] = value
    return result


def _no_nonfinite_json_numbers(value: str) -> None:
    raise RunnerError("nonfinite_json_number")


def _finite_json_float(value: str) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise RunnerError("nonfinite_json_number")
    return number


def _strict_json_loads(value: str | bytes) -> Any:
    return json.loads(
        value,
        object_pairs_hook=_no_duplicate_json_keys,
        parse_constant=_no_nonfinite_json_numbers,
        parse_float=_finite_json_float,
    )


def _argv(value: Any, name: str, cwd: Path) -> list[str]:
    if (
        not isinstance(value, list)
        or not value
        or any(not isinstance(arg, str) or not arg or "\x00" in arg for arg in value)
    ):
        raise RunnerError(f"invalid_{name}")
    if os.path.basename(value[0]) in {"sh", "bash", "cmd", "powershell", "pwsh"}:
        raise RunnerError("shell_interpreter_not_supported")
    executable = value[0]
    if os.path.isabs(executable):
        available = Path(executable).is_file()
    elif "/" in executable or "\\" in executable:
        # The subprocess runs with cwd=repo, not the caller's cwd.
        candidate = (cwd / executable).resolve()
        available = candidate.is_relative_to(cwd) and candidate.is_file()
    else:
        available = shutil.which(executable) is not None
    if not available:
        raise RunnerError(f"runner_missing_{name}")
    return value


def _git_head(repo: Path) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "--verify", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    if proc.returncode:
        raise RunnerError("repository_head_unavailable")
    return proc.stdout.strip()


def _verified_tc_expectations(
    plan: dict[str, Any], repo: Path, revision: str
) -> dict[str, str]:
    """Verify the full TC expectation set against a pinned, tracked Git blob.

    A pinned source controls what is being compared, not whether a separate
    approval provider has authenticated the underlying specification.
    """
    relative = plan.get("direct_tc_authority_file")
    if (
        not isinstance(relative, str)
        or not relative
        or "\\" in relative
        or "\x00" in relative
        or any(ord(ch) < 32 for ch in relative)
        or relative.startswith("/")
        or any(part in {"", ".", "..", ".git"} for part in relative.split("/"))
        or ":" in relative
    ):
        raise RunnerError("invalid_direct_tc_authority_file")
    entry = subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "ls-tree",
            "-r",
            "--full-tree",
            revision,
            "--",
            relative,
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    if entry.returncode or not entry.stdout.strip():
        raise RunnerError("direct_tc_authority_not_tracked")
    rows = entry.stdout.strip().splitlines()
    if len(rows) != 1 or "\t" not in rows[0]:
        raise RunnerError("direct_tc_authority_not_regular")
    header, name = rows[0].split("\t", 1)
    details = header.split()
    if (
        name != relative
        or len(details) != 3
        or details[0] not in {"100644", "100755"}
        or details[1] != "blob"
    ):
        raise RunnerError("direct_tc_authority_not_regular")
    blob_sha = details[2]
    size = subprocess.run(
        ["git", "-C", str(repo), "cat-file", "-s", blob_sha],
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    if (
        size.returncode
        or not size.stdout.strip().isdigit()
        or int(size.stdout) > 1_048_576
    ):
        raise RunnerError("direct_tc_authority_too_large_or_unavailable")
    blob = subprocess.run(
        ["git", "-C", str(repo), "cat-file", "blob", blob_sha],
        capture_output=True,
        check=False,
        timeout=10,
    )
    if blob.returncode:
        raise RunnerError("direct_tc_authority_unavailable")
    try:
        source = _strict_json_loads(blob.stdout.decode("utf-8"))
    except (UnicodeError, ValueError):
        raise RunnerError("invalid_direct_tc_authority") from None
    if (
        not isinstance(source, dict)
        or source.get("tc_ref") != plan["tc_ref"]
        or source.get("tc_revision") != plan["tc_revision"]
        or source.get("expected_authority_ref") != plan["expected_authority_ref"]
        or not isinstance(source.get("direct_expectations"), list)
    ):
        raise RunnerError("direct_tc_authority_identity_mismatch")
    compare_direct(
        started=False, expectations=source["direct_expectations"], observations={}
    )
    # Python's == treats True as 1, including inside a nested JSON object.
    # A caller must not replace a committed boolean expectation with a number.
    if not _json_equal_strict(
        source["direct_expectations"], plan["direct_expectations"]
    ):
        raise RunnerError("direct_tc_expectations_incomplete_or_mismatched")
    return {
        "authority_file": relative,
        "authority_blob": blob_sha,
        "authority_repo_revision": revision,
        "authority_review_status": "not_authenticated_by_runner",
    }


def _git_clean(repo: Path) -> bool:
    proc = subprocess.run(
        ["git", "-C", str(repo), "status", "--porcelain", "--untracked-files=all"],
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    if proc.returncode:
        raise RunnerError("repository_status_unavailable")
    return not proc.stdout.strip()


def _procfs_is_mounted(root: Path = Path("/proc")) -> bool:
    """Require a real procfs superblock, not merely an empty /proc directory."""
    try:
        libc = ctypes.CDLL(None, use_errno=True)
        status = ctypes.create_string_buffer(256)
        if libc.statfs(os.fsencode(root), ctypes.byref(status)) != 0:
            return False
        # Linux PROC_SUPER_MAGIC; a plain directory does not meet this check.
        return (
            ctypes.c_long.from_buffer(status).value == 0x9FA0
            and (root / "self" / "stat").is_file()
        )
    except (AttributeError, OSError, ValueError):
        return False


def _enable_descendant_supervision() -> bool:
    """Make escaped-session orphans observable in this dedicated Linux runner."""
    if sys.platform != "linux" or not _procfs_is_mounted():
        return False
    try:
        libc = ctypes.CDLL(None, use_errno=True)
        return libc.prctl(36, 1, 0, 0, 0) == 0  # PR_SET_CHILD_SUBREAPER
    except (AttributeError, OSError):
        return False


def _adopted_children() -> dict[int, str] | None:
    """Enumerate adopted children using procfs; None means proof unavailable."""
    found: dict[int, str] = {}
    try:
        for item in Path("/proc").iterdir():
            if not item.name.isdigit():
                continue
            try:
                fields = (item / "stat").read_text(encoding="utf-8").rsplit(") ", 1)
                if len(fields) != 2:
                    return None
                values = fields[1].split()
                if int(values[1]) == os.getpid():
                    found[int(item.name)] = values[0]
            except FileNotFoundError:
                continue
        return found
    except (OSError, ValueError, IndexError, UnicodeError):
        return None


def _reap_exited_children() -> None:
    while True:
        try:
            pid, _ = os.waitpid(-1, os.WNOHANG)
        except ChildProcessError:
            break
        if pid == 0:
            break


def _process_group_state(pid: int | None) -> str:
    if pid is None:
        return "not_started"
    if os.name != "posix":
        return "unverified"
    try:
        os.killpg(pid, 0)
    except ProcessLookupError:
        return "terminated"
    except OSError:
        return "unverified"
    return "lingering"


def _quiesce_process_scope(pid: int | None, supervision: bool) -> str:
    """Reap/stop original-group and adopted escaped-session descendants."""
    if pid is None:
        return "not_started"
    if not supervision:
        return "unverified"
    _reap_exited_children()
    adopted = _adopted_children()
    group = _process_group_state(pid)
    if adopted is None or group == "unverified":
        return "lingering_unverified"
    if group == "terminated" and not adopted:
        return "terminated"
    had_live = any(state != "Z" for state in adopted.values())
    if group == "lingering":
        try:
            os.killpg(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        except OSError:
            return "lingering_unverified"
        had_live = True
    for child_pid, state in adopted.items():
        if state == "Z":
            continue
        try:
            os.kill(child_pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        except OSError:
            return "lingering_unverified"
    for _ in range(30):
        _reap_exited_children()
        remaining = _adopted_children()
        if remaining is None:
            return "lingering_unverified"
        if not remaining and _process_group_state(pid) == "terminated":
            return "lingering_terminated" if had_live else "terminated"
        time.sleep(0.02)
    return "lingering_unverified"


def _terminate_group(proc: subprocess.Popen[Any]) -> None:
    try:
        if os.name == "posix":
            os.killpg(proc.pid, signal.SIGKILL)
        else:
            proc.kill()
    except ProcessLookupError:
        pass
    finally:
        proc.wait()


def _run_command(
    argv: list[str],
    cwd: Path,
    stdout: Path,
    stderr: Path,
    timeout: int,
    *,
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    started_at = time.time()
    started = False
    pid = None
    timed_out = False
    interrupted = False
    return_code = None
    with stdout.open("xb") as out, stderr.open("xb") as err:
        try:
            proc = subprocess.Popen(
                argv,
                cwd=str(cwd),
                stdin=subprocess.DEVNULL,
                stdout=out,
                stderr=err,
                shell=False,
                env=env,
                start_new_session=os.name == "posix",
            )
            started, pid = True, proc.pid
            try:
                return_code = proc.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                timed_out = True
                _terminate_group(proc)
                return_code = proc.returncode
            except KeyboardInterrupt:
                # Without this handler Ctrl-C can leave a detached test worker
                # running and bypass the manifest/cleanup paths entirely.
                interrupted = True
                _terminate_group(proc)
                return_code = proc.returncode
        except OSError as exc:
            # Do not serialize potentially sensitive environment values.
            return {
                "started": started,
                "pid": pid,
                "return_code": return_code,
                "timeout": timed_out,
                "interrupted": interrupted,
                "launch_error": type(exc).__name__,
                "started_at": started_at,
                "finished_at": time.time(),
            }
    return {
        "started": started,
        "pid": pid,
        "return_code": return_code,
        "timeout": timed_out,
        "interrupted": interrupted,
        "launch_error": None,
        "started_at": started_at,
        "finished_at": time.time(),
    }


def _write_json(path: Path, value: dict[str, Any]) -> None:
    tmp = path.with_suffix(".pending")
    with tmp.open("x", encoding="utf-8") as out:
        json.dump(value, out, ensure_ascii=False, indent=2)
        out.write("\n")
    os.replace(tmp, path)


def execute(plan: dict[str, Any], artifacts_root: Path) -> dict[str, Any]:
    """Execute a confirmed command. Raw logs remain in a private local directory."""
    if not isinstance(plan, dict):
        raise RunnerError("invalid_plan")
    kind = plan.get("runner_kind")
    if kind not in KINDS:
        raise RunnerError("unsupported_runner_kind")
    scope = plan.get("preflight")
    if not isinstance(scope, dict):
        raise RunnerError("missing_preflight")
    checked = preflight(scope)
    if checked["may_start"] is not True:
        raise RunnerError("preflight_" + str(checked["reason"]))
    if scope["external_side_effects"] or scope["shared_resource"]:
        raise RunnerError("native_provider_authorization_required")
    # Arbitrary subprocesses cannot enforce a per-resource effect count. Until
    # an authenticated effect-counting provider exists, refuse declared effects.
    if scope["side_effects"]:
        raise RunnerError("side_effect_limits_unenforceable")
    # Invalid diagnostic metadata must never discard evidence from a launched
    # process. Validate it before any side effect or artifact allocation.
    diagnostic = (
        diagnosis(
            run_ref=scope["operation_ref"],
            hypotheses=plan["diagnosis_hypotheses"],
        )
        if "diagnosis_hypotheses" in plan
        else None
    )
    repo_path = plan.get("repo_path")
    if not isinstance(repo_path, str) or not Path(repo_path).is_absolute():
        raise RunnerError("absolute_repo_path_required")
    repo = Path(repo_path).resolve(strict=True)
    if not repo.is_dir():
        raise RunnerError("repo_not_directory")
    expected_sha = plan.get("repo_revision")
    if not isinstance(expected_sha, str) or _git_head(repo) != expected_sha:
        raise RunnerError("repo_revision_changed")
    if not _git_clean(repo):
        raise RunnerError("repo_not_clean")
    source_revision = scope["source_revision"]
    if source_revision != expected_sha:
        # This adapter executes a pinned checkout. External-source mappings
        # require an authenticated identity bridge, which is not available.
        raise RunnerError("source_revision_not_execution_revision")
    command = _argv(plan.get("argv"), "argv", repo)
    if command != plan.get("reviewed_argv"):
        raise RunnerError("argv_not_reviewed")
    cleanup = plan.get("cleanup_argv")
    if cleanup is not None:
        cleanup = _argv(cleanup, "cleanup", repo)
        if cleanup != plan.get("reviewed_cleanup_argv"):
            raise RunnerError("cleanup_not_reviewed")
    if scope.get("side_effects") and cleanup is None:
        raise RunnerError("effect_cleanup_required")
    if plan.get("direct_tc") is True:
        if not plan.get("direct_expectations"):
            raise RunnerError("direct_tc_expectations_required")
        for field in ("tc_ref", "tc_revision", "expected_authority_ref"):
            if not isinstance(plan.get(field), str) or not plan[field].strip():
                raise RunnerError(field + "_required_for_direct_tc")
    direct_authority = None
    if plan.get("direct_tc") is True:
        direct_authority = _verified_tc_expectations(plan, repo, expected_sha)
    direct_expectations = plan.get("direct_expectations")
    if direct_expectations is not None:
        if (
            kind == "vitest"
            or not isinstance(direct_expectations, list)
            or not direct_expectations
        ):
            raise RunnerError("invalid_direct_expectations")
        # Validate the complete expectation contract before the first operation.
        compare_direct(started=False, expectations=direct_expectations, observations={})
    metric_criteria = plan.get("metric_criteria")
    if kind == "nonfunctional" and not metric_criteria:
        raise RunnerError("missing_nonfunctional_criteria")
    if metric_criteria is not None:
        if (
            kind != "nonfunctional"
            or plan.get("measurement_conditions_verified") is not True
        ):
            raise RunnerError("metric_conditions_unverified")
        compare_metrics(
            started=False,
            criteria=metric_criteria,
            measurements={},
            condition_ref=plan.get("measurement_condition_ref"),
            authority_ref=plan.get("threshold_authority_ref"),
        )
    static_plan = plan.get("static_analysis")
    if kind == "static":
        if not isinstance(static_plan, dict):
            raise RunnerError("static_analysis_contract_required")
        for field in ("tool_ref", "tool_version", "rules_ref", "config_ref"):
            if (
                not isinstance(static_plan.get(field), str)
                or not static_plan[field].strip()
            ):
                raise RunnerError("static_" + field + "_required")
        accepted_exits = static_plan.get("accepted_exit_codes")
        if (
            not isinstance(accepted_exits, list)
            or not accepted_exits
            or any(type(code) is not int for code in accepted_exits)
            or len(accepted_exits) != len(set(accepted_exits))
        ):
            raise RunnerError("static_accepted_exit_codes_required")
        targets = static_plan.get("expected_paths")
        if (
            not isinstance(targets, list)
            or not targets
            or any(not isinstance(x, str) or not x for x in targets)
            or len(targets) != len(set(targets))
        ):
            raise RunnerError("invalid_static_expected_paths")
    elif static_plan is not None:
        raise RunnerError("static_contract_for_non_static_runner")
    reporter_format = plan.get("reporter_format")
    if kind == "vitest" and reporter_format is None:
        reporter_format = "vitest-json"
    supported_formats = {
        "vitest": {"vitest-json"},
        "playwright-api": {"playwright-json"},
        "component": {"vitest-json", "jest-json", "playwright-json"},
        "batch": {"case-json"},
        "event": {"case-json"},
    }
    if reporter_format is not None and reporter_format not in supported_formats.get(
        kind, set()
    ):
        raise RunnerError("unsupported_reporter_format")
    if reporter_format is not None:
        if plan.get("direct_tc") is True:
            raise RunnerError("reporter_not_supported_for_direct_tc")
        selected = plan.get("selected")
        if not isinstance(selected, list) or not selected:
            raise RunnerError("selected_test_population_required")
        identities = []
        for item in selected:
            if not isinstance(item, dict):
                raise RunnerError("invalid_selected_test")
            try:
                identity = _test_key(item.get("path"), item.get("title_path"))
            except ContractError as exc:
                raise RunnerError("invalid_selected_test") from exc
            project = item.get("project_name")
            if project is not None and (
                not isinstance(project, str) or not project.strip()
            ):
                raise RunnerError("invalid_selected_project")
            identities.append((*identity, project or "default"))
        if len(identities) != len(set(identities)):
            raise RunnerError("duplicate_selected_test")
        if reporter_format in {"vitest-json", "jest-json"}:
            named = {item.get("project_name") for item in selected}
            if any(name is not None for name in named):
                if len(named) != 1 or None in named:
                    raise RunnerError("vitest_multi_project_requires_separate_runs")
                project_name = next(iter(named))
                # Even one Vitest project glob can select multiple projects.
                if (
                    any(char in project_name for char in "*?[]{}()|\\")
                    or project_name.startswith("!")
                ):
                    raise RunnerError("vitest_project_filter_unverified")
                declared_projects = []
                for index, arg in enumerate(command):
                    if arg == "--project":
                        declared_projects.append(
                            command[index + 1] if index + 1 < len(command) else None
                        )
                    elif arg.startswith("--project="):
                        declared_projects.append(arg.removeprefix("--project="))
                # Vitest accepts repeated project selectors and globs; merely
                # finding one matching argument does NOT prove a single project.
                if declared_projects != [project_name]:
                    raise RunnerError("vitest_project_filter_unverified")
        for field in (
            "testware_ref",
            "testware_revision",
            "runner_version",
            "selection_evidence_ref",
            "planned_scope_ref",
        ):
            if not isinstance(plan.get(field), str) or not plan[field].strip():
                raise RunnerError(field + "_required_for_reporter")
        if plan.get("selection_verified") is not True:
            raise RunnerError("selection_evidence_unverified")
        if reporter_format != "playwright-json" and not any(
            "{reporter_file}" in item for item in command
        ):
            raise RunnerError("reporter_output_file_not_configured")
    limit = plan.get("timeout_seconds", 60)
    attempts = plan.get("attempts", 1)
    if type(limit) is not int or not 1 <= limit <= 3600:
        raise RunnerError("invalid_timeout")
    if type(attempts) is not int or not 1 <= attempts <= 3:
        raise RunnerError("invalid_attempt_count")
    if scope.get("side_effects") and attempts > 1:
        raise RunnerError("effect_retry_requires_state_readback")
    # POSIX process groups alone cannot prove a detached child exited.
    # Fail closed when this isolated runner cannot supervise all descendants.
    supervision = _enable_descendant_supervision()
    if not supervision:
        raise RunnerError("process_supervision_unavailable")
    # Reject a forbidden destination *before* creating anything. This check
    # also resolves an existing symlink ancestor of a not-yet-created path.
    root = artifacts_root.resolve()
    if repo == root or repo in root.parents or root in repo.parents:
        raise RunnerError("artifacts_must_be_outside_repo")
    root.mkdir(parents=True, exist_ok=True)
    if root.resolve() != root:
        raise RunnerError("artifacts_root_changed")
    folder = Path(tempfile.mkdtemp(prefix="non-e2e-", dir=root))
    records: list[dict[str, Any]] = []
    workspace_changed_before_retry = False
    for number in range(1, attempts + 1):
        # Check again immediately before the launch. This is not a native
        # provider reservation; later changes are detected after cleanup.
        if _git_head(repo) != expected_sha or not _git_clean(repo):
            if not records:
                raise RunnerError("repo_changed_before_start")
            workspace_changed_before_retry = True
            break
        attempt = folder / f"attempt-{number}"
        attempt.mkdir(mode=0o700)
        reporter = attempt / "reporter.json"
        argv = [part.replace("{reporter_file}", str(reporter)) for part in command]
        argv_digest = hashlib.sha256(
            json.dumps(argv, ensure_ascii=False).encode("utf-8")
        ).hexdigest()
        env = None
        if reporter_format == "playwright-json":
            # Official Playwright JSON reporter output location; avoid a
            # persistent repo-local report and stale output from a prior run.
            env = os.environ.copy()
            env["PLAYWRIGHT_JSON_OUTPUT_FILE"] = str(reporter)
        run = _run_command(
            argv,
            repo,
            attempt / "stdout.log",
            attempt / "stderr.log",
            limit,
            env=env,
        )
        run.update(
            {
                "number": number,
                "executed_argv_sha256": argv_digest,
                "stdout_ref": str(attempt / "stdout.log"),
                "stderr_ref": str(attempt / "stderr.log"),
                "raw_report_ref": None,
                "result_collection": "not_provided_by_adapter",
                "cleanup_state": "not_required" if cleanup is None else "not_started",
            }
        )
        # Result interpretation is never permitted to skip cleanup or the
        # attempt manifest. All errors here become evidence of incomplete
        # collection; raw stdout/stderr/report files remain untouched.
        try:
            if reporter_format is not None:
                run["result_collection"] = "missing"
                # Each attempt owns a newly created reporter file. Never read a
                # symlink or a report produced outside this attempt's directory.
                if run["started"] and reporter.is_file() and not reporter.is_symlink():
                    run["raw_report_ref"] = str(reporter)
                    try:
                        if reporter.stat().st_size > 16 * 1024 * 1024:
                            raise RunnerError("reporter_too_large")
                        raw = _strict_json_loads(reporter.read_text(encoding="utf-8"))
                        shared = {
                            "selected": plan["selected"],
                            "report": raw,
                            "source_revision": expected_sha,
                            "raw_ref": str(reporter),
                            "selection_verified": True,
                        }
                        if reporter_format in {"vitest-json", "jest-json"}:
                            named_projects = {
                                item.get("project_name") for item in plan["selected"]
                            }
                            selected_project = (
                                next(iter(named_projects))
                                if None not in named_projects
                                else None
                            )
                            reconciliation = reconcile_vitest(
                                **shared,
                                repo_root=str(repo),
                                project_name=selected_project,
                                project_verified=selected_project is not None,
                            )
                            # A successful process with a missing global JSON
                            # status cannot attest an official Vitest/Jest result.
                            reporter_reports_failure = raw.get("success") is not True
                        elif reporter_format == "playwright-json":
                            reconciliation = reconcile_playwright(
                                **shared,
                                runner_version=plan["runner_version"],
                                repo_root=str(repo),
                            )
                            reporter_reports_failure = (
                                raw.get("stats", {}).get("unexpected", 0) > 0
                            )
                        else:
                            reconciliation = reconcile_case_report(
                                **shared,
                                testware_revision=plan["testware_revision"],
                                runner_version=plan["runner_version"],
                            )
                            reporter_reports_failure = any(
                                item.get("status")
                                in {"failed", "timedOut", "interrupted"}
                                for item in raw["results"]
                            )
                        run["reconciliation"] = reconciliation
                        # A test reporter claiming failures while the process exits 0
                        # is contradictory, not a successful completed collection.
                        run["result_collection"] = (
                            "complete"
                            if reconciliation["collection_complete"]
                            and not (
                                run["return_code"] == 0 and reporter_reports_failure
                            )
                            else "incomplete"
                        )
                    except (ValueError, ContractError, UnicodeError, OSError):
                        run["result_collection"] = "invalid"
            if direct_expectations is not None:
                observations: dict[str, Any] = {}
                if run["started"] and run["return_code"] is not None:
                    observations["exit_code"] = run["return_code"]
                    # Parsing is bounded: malformed, non-UTF8 or excessive output
                    # remains unobserved, never an implicit PASS.
                    stdout = attempt / "stdout.log"
                    if stdout.stat().st_size <= 1_048_576:
                        try:
                            content = stdout.read_text(encoding="utf-8")
                            observations["stdout_text"] = content
                            observations["stdout_json"] = _strict_json_loads(content)
                        except (UnicodeError, ValueError):
                            pass
                run["direct_comparison"] = compare_direct(
                    started=run["started"],
                    expectations=direct_expectations,
                    observations=observations,
                )
                # Arbitrary stdout expectations are useful observations, but
                # only an authority-bound direct TC can replace a per-test reporter.
                if reporter_format is None:
                    run["result_collection"] = (
                        "complete"
                        if plan.get("direct_tc") is True
                        and all(
                            item["observed"]
                            for item in run["direct_comparison"]["details"]
                        )
                        else "incomplete"
                    )
            if metric_criteria is not None:
                metrics: dict[str, Any] = {}
                stdout_file = attempt / "stdout.log"
                if run["started"] and stdout_file.stat().st_size <= 1_048_576:
                    try:
                        parsed = _strict_json_loads(
                            stdout_file.read_text(encoding="utf-8")
                        )
                        if isinstance(parsed, dict):
                            metrics = parsed
                    except (ValueError, UnicodeError):
                        pass
                run["metric_comparison"] = compare_metrics(
                    started=run["started"],
                    criteria=metric_criteria,
                    measurements=metrics,
                    condition_ref=plan["measurement_condition_ref"],
                    authority_ref=plan["threshold_authority_ref"],
                )
                run["result_collection"] = (
                    "complete"
                    if run["metric_comparison"]["verdict"] in {"PASS", "FAIL"}
                    else "incomplete"
                )
            if kind == "static":
                from contract import interpret_static

                report_data: dict[str, Any] = {}
                stdout_file = attempt / "stdout.log"
                if run["started"] and stdout_file.stat().st_size <= 1_048_576:
                    try:
                        parsed = _strict_json_loads(
                            stdout_file.read_text(encoding="utf-8")
                        )
                        if isinstance(parsed, dict):
                            report_data = parsed
                    except (ValueError, UnicodeError):
                        pass
                actual = report_data.get("analyzed_paths")
                omitted = report_data.get("skipped_paths")
                expected_set = set(static_plan["expected_paths"])
                paths_complete = (
                    isinstance(actual, list)
                    and all(isinstance(item, str) for item in actual)
                    and len(actual) == len(set(actual))
                    and set(actual) == expected_set
                    and omitted == []
                    and report_data.get("tool_ref") == static_plan["tool_ref"]
                    and report_data.get("tool_version") == static_plan["tool_version"]
                    and report_data.get("rules_ref") == static_plan["rules_ref"]
                    and report_data.get("config_ref") == static_plan["config_ref"]
                    and run["return_code"] in static_plan["accepted_exit_codes"]
                )
                finding_count = report_data.get("findings_count")
                if type(finding_count) is not int or finding_count < 0:
                    finding_count = None
                assessment = interpret_static(
                    started=run["started"],
                    exit_code=run["return_code"],
                    raw_ref=str(stdout_file) if run["started"] else None,
                    findings_count=finding_count if paths_complete else None,
                )
                run["static_analysis"] = {
                    **assessment,
                    "expected_paths": static_plan["expected_paths"],
                    "analyzed_paths": actual if isinstance(actual, list) else None,
                    "skipped_paths": omitted if isinstance(omitted, list) else None,
                    "selection_complete": paths_complete,
                    "tool_ref": static_plan["tool_ref"],
                    "tool_version": static_plan["tool_version"],
                    "rules_ref": static_plan["rules_ref"],
                    "config_ref": static_plan["config_ref"],
                }
                run["result_collection"] = (
                    "complete" if assessment["complete"] else "incomplete"
                )
        except Exception as error:
            run["result_collection"] = "invalid"
            run["processing_error"] = type(error).__name__
        # Verify the full execution scope before a cleanup can touch state.
        run["process_tree_state"] = _quiesce_process_scope(run["pid"], supervision)
        if cleanup is not None and run["started"]:
            if run["process_tree_state"] not in {"terminated", "lingering_terminated"}:
                run["cleanup_state"] = "failed_or_unknown"
                run["cleanup_error"] = "descendants_not_quiescent_before_cleanup"
            else:
                try:
                    clean = _run_command(
                        cleanup,
                        repo,
                        attempt / "cleanup.stdout.log",
                        attempt / "cleanup.stderr.log",
                        limit,
                    )
                    clean["process_tree_state"] = _quiesce_process_scope(
                        clean["pid"], supervision
                    )
                    run["cleanup"] = clean
                    run["cleanup_state"] = (
                        "success"
                        if clean["started"]
                        and not clean["timeout"]
                        and not clean["interrupted"]
                        and clean["return_code"] == 0
                        and clean["process_tree_state"] == "terminated"
                        else "failed_or_unknown"
                    )
                except Exception as error:
                    run["cleanup_state"] = "failed_or_unknown"
                    run["cleanup_error"] = type(error).__name__
        try:
            run["workspace_head_after_cleanup"] = _git_head(repo)
            run["workspace_state_after_cleanup"] = (
                "clean" if _git_clean(repo) else "dirty"
            )
        except (RunnerError, OSError, subprocess.TimeoutExpired):
            run["workspace_head_after_cleanup"] = None
            run["workspace_state_after_cleanup"] = "unverified"
        records.append(run)
        # Retrying an ambiguous state can repeat a side effect; never do it.
        if (
            run["cleanup_state"] == "failed_or_unknown"
            or run["timeout"]
            or run["interrupted"]
            or run["process_tree_state"] != "terminated"
            or run["result_collection"] != "complete"
            or scope.get("side_effects")
            or run["workspace_state_after_cleanup"] != "clean"
            or run["workspace_head_after_cleanup"] != expected_sha
        ):
            break
        if (
            direct_expectations is not None
            and run["direct_comparison"]["result"] != "PASS"
        ):
            break
        if (
            metric_criteria is not None
            and run["metric_comparison"]["verdict"] != "PASS"
        ):
            break
        if run["return_code"] == 0 and run["result_collection"] == "complete":
            break
    outcome = "unknown"
    last = records[-1]
    if (
        workspace_changed_before_retry
        or last["workspace_head_after_cleanup"] != expected_sha
    ):
        outcome = "blocked_revision_changed"
    elif last["workspace_state_after_cleanup"] != "clean":
        outcome = "blocked_workspace_not_restored"
    elif (
        last["cleanup_state"] == "failed_or_unknown"
        or last["timeout"]
        or last["interrupted"]
        or last["process_tree_state"] != "terminated"
    ):
        outcome = "blocked_cleanup_or_timeout"
    elif not last["started"] or last["result_collection"] != "complete":
        outcome = "incomplete"
    elif last["return_code"] == 0:
        outcome = "runner_pass"
    elif last["return_code"] is not None:
        outcome = "runner_fail"
    result = {
        "runner_kind": kind,
        "reporter_format": reporter_format,
        "result_collection": last["result_collection"],
        "collection_verified": last["result_collection"] == "complete",
        "source_ref": scope["source_ref"],
        "source_revision": scope["source_revision"],
        "build_revision": scope["build_revision"],
        "repo_revision": expected_sha,
        "environment_ref": scope["environment_ref"],
        "runner_ref": scope["runner_ref"],
        "runner_version": plan.get("runner_version"),
        "testware_ref": plan.get("testware_ref"),
        "testware_revision": plan.get("testware_revision"),
        "tc_ref": plan.get("tc_ref"),
        "tc_revision": plan.get("tc_revision"),
        "planned_scope_ref": plan.get("planned_scope_ref"),
        "selection_evidence_ref": plan.get("selection_evidence_ref"),
        "selection_filter": plan.get("selection_filter"),
        "selection_evidence_is_caller_declared": bool(plan.get("selection_verified")),
        "declared_selection_matched_report": False,
        "declared_selected": plan.get("selected", []),
        "run_ref": scope["operation_ref"],
        "artifact_directory": str(folder),
        "attempts": records,
        "outcome": outcome,
        "direct_observation_verdict": last.get("direct_comparison", {}).get("result"),
        # A pinned Git blob verifies the expected content, not an approved
        # Authority. Never promote a local observation to a formal TC verdict.
        "tc_verdict": None,
        "expected_authority_ref": plan.get("expected_authority_ref"),
        "direct_tc_authority_evidence": direct_authority,
        "quality_verdict": last.get("metric_comparison", {}).get("verdict"),
        "evidence_is_fixture": bool(plan.get("fixture_only", False)),
        "provider_readback": "not_connected",
    }
    if diagnostic is not None:
        result["diagnosis"] = diagnostic
    if (
        result["direct_observation_verdict"] == "FAIL"
        and outcome in {"runner_pass", "runner_fail", "incomplete"}
        and last["return_code"] is not None
    ):
        result["outcome"] = "observed_FAIL"
    elif (
        result["direct_observation_verdict"] == "判定不能"
        and outcome in {"runner_pass", "incomplete"}
        and last["return_code"] is not None
    ):
        result["outcome"] = "observations_incomplete"
    if reporter_format is not None:
        result["declared_selection_matched_report"] = bool(
            last.get("reconciliation", {}).get("collection_complete")
        )
    if (
        result["quality_verdict"] == "FAIL"
        and result["outcome"] in {"runner_pass", "incomplete"}
        and last["return_code"] is not None
    ):
        result["outcome"] = "measurement_FAIL"
    elif (
        result["quality_verdict"] == "判定不能"
        and result["outcome"] in {"runner_pass", "incomplete"}
        and last["return_code"] is not None
    ):
        result["outcome"] = "measurements_incomplete"
    _write_json(folder / "manifest.json", result)
    return result


def main() -> int:
    cli = argparse.ArgumentParser(
        description="Execute an inspected non-E2E runner command"
    )
    cli.add_argument("--plan", type=Path, required=True)
    cli.add_argument("--artifacts", type=Path, required=True)
    args = cli.parse_args()
    try:
        plan = _strict_json_loads(args.plan.read_text(encoding="utf-8"))
        result = execute(plan, args.artifacts)
        print(
            json.dumps(
                {
                    "outcome": result["outcome"],
                    "run_ref": result["run_ref"],
                    "artifact_directory": result["artifact_directory"],
                },
                ensure_ascii=False,
            )
        )
        return 0 if result["outcome"] == "runner_pass" else 1
    except (
        RunnerError,
        ContractError,
        ValueError,
        OSError,
        TypeError,
        AttributeError,
        subprocess.TimeoutExpired,
    ) as error:
        print(
            json.dumps(
                {
                    "outcome": "blocked",
                    "reason": str(error)
                    if isinstance(error, (RunnerError, ContractError))
                    else type(error).__name__,
                },
                ensure_ascii=False,
            )
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
