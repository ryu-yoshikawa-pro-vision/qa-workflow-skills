"""Run an inspected non-E2E command in an isolated Git checkout.

This module does not authenticate provider approvals or reserve shared state.
It refuses shared/external effects and records runner evidence locally. The
caller must inspect the full command/package-script/fixture chain beforehand.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import signal
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

from contract import ContractError, compare_direct, preflight, reconcile_vitest

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


def _argv(value: Any, name: str) -> list[str]:
    if (
        not isinstance(value, list)
        or not value
        or any(not isinstance(arg, str) or not arg or "\x00" in arg for arg in value)
    ):
        raise RunnerError(f"invalid_{name}")
    if os.path.basename(value[0]) in {"sh", "bash", "cmd", "powershell", "pwsh"}:
        raise RunnerError("shell_interpreter_not_supported")
    if shutil.which(value[0]) is None and not Path(value[0]).is_file():
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


def _run_command(
    argv: list[str], cwd: Path, stdout: Path, stderr: Path, timeout: int
) -> dict[str, Any]:
    started_at = time.time()
    started = False
    pid = None
    timed_out = False
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
                start_new_session=os.name == "posix",
            )
            started, pid = True, proc.pid
            try:
                return_code = proc.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                timed_out = True
                if os.name == "posix":
                    os.killpg(proc.pid, signal.SIGKILL)
                else:
                    proc.kill()
                proc.wait()
                return_code = proc.returncode
        except OSError as exc:
            # Do not serialize potentially sensitive environment values.
            return {
                "started": started,
                "pid": pid,
                "return_code": return_code,
                "timeout": timed_out,
                "launch_error": type(exc).__name__,
                "started_at": started_at,
                "finished_at": time.time(),
            }
    return {
        "started": started,
        "pid": pid,
        "return_code": return_code,
        "timeout": timed_out,
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
    if scope.get("external_side_effects") or scope.get("shared_resource"):
        raise RunnerError("native_provider_authorization_required")
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
    command = _argv(plan.get("argv"), "argv")
    if command != plan.get("reviewed_argv"):
        raise RunnerError("argv_not_reviewed")
    cleanup = plan.get("cleanup_argv")
    if cleanup is not None:
        cleanup = _argv(cleanup, "cleanup")
        if cleanup != plan.get("reviewed_cleanup_argv"):
            raise RunnerError("cleanup_not_reviewed")
    if scope.get("side_effects") and cleanup is None:
        raise RunnerError("effect_cleanup_required")
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
    limit = plan.get("timeout_seconds", 60)
    attempts = plan.get("attempts", 1)
    if type(limit) is not int or not 1 <= limit <= 3600:
        raise RunnerError("invalid_timeout")
    if type(attempts) is not int or not 1 <= attempts <= 3:
        raise RunnerError("invalid_attempt_count")
    if scope.get("side_effects") and attempts > 1:
        raise RunnerError("effect_retry_requires_state_readback")
    root = artifacts_root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    if repo == root or repo in root.parents or root in repo.parents:
        raise RunnerError("artifacts_must_be_outside_repo")
    folder = Path(tempfile.mkdtemp(prefix="non-e2e-", dir=root))
    records: list[dict[str, Any]] = []
    for number in range(1, attempts + 1):
        attempt = folder / f"attempt-{number}"
        attempt.mkdir(mode=0o700)
        reporter = attempt / "reporter.json"
        argv = [part.replace("{reporter_file}", str(reporter)) for part in command]
        run = _run_command(
            argv, repo, attempt / "stdout.log", attempt / "stderr.log", limit
        )
        run.update(
            {
                "number": number,
                "stdout_ref": str(attempt / "stdout.log"),
                "stderr_ref": str(attempt / "stderr.log"),
                "raw_report_ref": None,
                "result_collection": "not_applicable",
                "cleanup_state": "not_required" if cleanup is None else "not_started",
            }
        )
        if kind == "vitest":
            run["result_collection"] = "missing"
            if reporter.is_file() and run["started"]:
                run["raw_report_ref"] = str(reporter)
                try:
                    raw = json.loads(reporter.read_text(encoding="utf-8"))
                    run["reconciliation"] = reconcile_vitest(
                        selected=plan.get("selected", []),
                        report=raw,
                        source_revision=expected_sha,
                        raw_ref=str(reporter),
                        selection_verified=plan.get("selection_verified") is True,
                        repo_root=str(repo),
                    )
                    run["result_collection"] = (
                        "complete"
                        if run["reconciliation"]["collection_complete"]
                        else "incomplete"
                    )
                except (ValueError, ContractError, UnicodeError):
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
                        observations["stdout_json"] = json.loads(content)
                    except (UnicodeError, ValueError):
                        pass
            run["direct_comparison"] = compare_direct(
                started=run["started"],
                expectations=direct_expectations,
                observations=observations,
            )
        if cleanup is not None and run["started"]:
            clean = _run_command(
                cleanup,
                repo,
                attempt / "cleanup.stdout.log",
                attempt / "cleanup.stderr.log",
                limit,
            )
            run["cleanup"] = clean
            run["cleanup_state"] = (
                "success"
                if clean["started"]
                and not clean["timeout"]
                and clean["return_code"] == 0
                else "failed_or_unknown"
            )
        records.append(run)
        # Retrying an ambiguous state can repeat a side effect; never do it.
        if (
            run["cleanup_state"] == "failed_or_unknown"
            or run["timeout"]
            or scope.get("side_effects")
        ):
            break
        if (
            direct_expectations is not None
            and run["direct_comparison"]["result"] != "PASS"
        ):
            break
        if run["return_code"] == 0 and run["result_collection"] in {
            "complete",
            "not_applicable",
        }:
            break
    outcome = "unknown"
    last = records[-1]
    if last["cleanup_state"] == "failed_or_unknown" or last["timeout"]:
        outcome = "blocked_cleanup_or_timeout"
    elif not last["started"] or last["result_collection"] in {
        "invalid",
        "missing",
        "incomplete",
    }:
        outcome = "incomplete"
    elif last["return_code"] == 0:
        outcome = "runner_pass"
    elif last["return_code"] is not None:
        outcome = "runner_fail"
    result = {
        "runner_kind": kind,
        "source_revision": expected_sha,
        "run_ref": scope["operation_ref"],
        "artifact_directory": str(folder),
        "attempts": records,
        "outcome": outcome,
        "tc_verdict": last.get("direct_comparison", {}).get("result"),
        "evidence_is_fixture": bool(plan.get("fixture_only", False)),
        "provider_readback": "not_connected",
    }
    if result["tc_verdict"] == "FAIL" and outcome == "runner_pass":
        result["outcome"] = "observed_FAIL"
    elif result["tc_verdict"] == "判定不能" and outcome == "runner_pass":
        result["outcome"] = "observations_incomplete"
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
        plan = json.loads(args.plan.read_text(encoding="utf-8"))
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
    except (RunnerError, ContractError, ValueError, OSError) as error:
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
