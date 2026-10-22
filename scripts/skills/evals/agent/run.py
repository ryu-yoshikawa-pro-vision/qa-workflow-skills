from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
    from scripts.skills.evals.agent.common import (
        AgentEvalError,
        atomic_write_json,
        canonical_fingerprint,
        capture_codex_jsonl_trace,
        capture_codex_judge_output,
        prepare_run_output_root,
        sanitize_diagnostic,
        sha256_bytes,
        visible_skill_names,
    )
    from scripts.skills.evals.agent.executor import AgentExecutionError, run_command
    from scripts.skills.evals.agent.prompt_builder import build_generation_prompt
    from scripts.skills.evals.agent.tools.codex_docker_launcher import launcher_argv
    from scripts.skills.evals.agent.tools.codex_judge_docker_launcher import (
        is_codex_judge,
    )
    from scripts.skills.evals.agent.tools.codex_judge_docker_launcher import (
        launcher_argv_for_profile as judge_launcher_argv_for_profile,
    )
    from scripts.skills.evals.agent.workspace import (
        assert_clean_checkout,
        create_skill_workspace,
        load_execution_profile,
        named_container_command,
        prepare_agent_output_mountpoint,
        profile_fingerprint,
        resolve_commit,
        verify_agent_docker_command,
        verify_judge_docker_command,
        verify_profile_evidence,
    )
    from scripts.skills.evals.semantic.loader import (
        REPO_ROOT,
        SKILLS_ROOT,
        discover_semantic_skills,
        load_semantic_skill,
    )
    from scripts.skills.evals.semantic.prompt_builder import build_judge_prompt
    from scripts.skills.evals.semantic.result import normalize_judge_response
else:
    from ..semantic.loader import (
        REPO_ROOT,
        SKILLS_ROOT,
        discover_semantic_skills,
        load_semantic_skill,
    )
    from ..semantic.prompt_builder import build_judge_prompt
    from ..semantic.result import normalize_judge_response
    from .common import (
        AgentEvalError,
        atomic_write_json,
        canonical_fingerprint,
        capture_codex_jsonl_trace,
        capture_codex_judge_output,
        prepare_run_output_root,
        sanitize_diagnostic,
        sha256_bytes,
        visible_skill_names,
    )
    from .executor import AgentExecutionError, run_command
    from .prompt_builder import build_generation_prompt
    from .tools.codex_docker_launcher import launcher_argv
    from .tools.codex_judge_docker_launcher import (
        is_codex_judge,
    )
    from .tools.codex_judge_docker_launcher import (
        launcher_argv_for_profile as judge_launcher_argv_for_profile,
    )
    from .workspace import (
        assert_clean_checkout,
        create_skill_workspace,
        load_execution_profile,
        named_container_command,
        prepare_agent_output_mountpoint,
        profile_fingerprint,
        resolve_commit,
        verify_agent_docker_command,
        verify_judge_docker_command,
        verify_profile_evidence,
    )

MAX_CASES = 10_000
SECRET_TEXT_RE = re.compile(
    r"(?i)\b(?:Bearer\s+[A-Za-z0-9._~+/=-]{12,}|sk-[A-Za-z0-9_-]{16,}|gh[pousr]_[A-Za-z0-9]{20,}|(?:api[_-]?key|access[_-]?token|refresh[_-]?token|password)\s*[:=]\s*[^\s,;]+)"
)


def _dataset_fingerprint(files: list[tuple[str, bytes]]) -> str:
    return canonical_fingerprint(
        [{"path": name, "sha256": sha256_bytes(content)} for name, content in files]
    )


def _load_deterministic_cases(skill: str, eval_id: str | None) -> list[dict[str, Any]]:
    from scripts.skills.evals.deterministic.run import VALIDATORS

    selected = sorted(VALIDATORS) if skill == "all" else [skill]
    cases: list[dict[str, Any]] = []
    for name in selected:
        manifest_path = SKILLS_ROOT / name / "evals" / "output" / "evals.json"
        if not manifest_path.is_file():
            continue
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        for raw in manifest.get("cases", []):
            if eval_id is not None and raw.get("id") != eval_id:
                continue
            input_path = manifest_path.parent / raw["input"]
            expected_path = manifest_path.parent / raw["expected"]
            cases.append(
                {
                    "skill": name,
                    "id": raw["id"],
                    "input": input_path.read_text(encoding="utf-8"),
                    "input_path": input_path,
                    "expected_path": expected_path,
                    "fingerprint_files": [
                        (
                            str(input_path.relative_to(REPO_ROOT)),
                            input_path.read_bytes(),
                        ),
                        (
                            str(expected_path.relative_to(REPO_ROOT)),
                            expected_path.read_bytes(),
                        ),
                        (
                            str(manifest_path.relative_to(REPO_ROOT)),
                            manifest_path.read_bytes(),
                        ),
                    ],
                }
            )
    return cases


def _load_semantic_cases(skill: str, eval_id: str | None) -> list[dict[str, Any]]:
    selected = discover_semantic_skills() if skill == "all" else [skill]
    cases: list[dict[str, Any]] = []
    for name in selected:
        dataset = load_semantic_skill(name)
        for case in dataset["cases"]:
            if eval_id is not None and case["id"] != eval_id:
                continue
            rubric_path = dataset["semantic_root"] / "rubric.json"
            evals_path = dataset["semantic_root"] / "evals.json"
            cases.append(
                {
                    "skill": name,
                    "id": case["id"],
                    "input": case["input_text"],
                    "case": case,
                    "dataset": dataset,
                    "fingerprint_files": [
                        (
                            str(case["input_path"].relative_to(REPO_ROOT)),
                            case["input_path"].read_bytes(),
                        ),
                        (
                            str(case["reference_path"].relative_to(REPO_ROOT)),
                            case["reference_path"].read_bytes(),
                        ),
                        (
                            str(rubric_path.relative_to(REPO_ROOT)),
                            rubric_path.read_bytes(),
                        ),
                        (
                            str(evals_path.relative_to(REPO_ROOT)),
                            evals_path.read_bytes(),
                        ),
                    ],
                }
            )
    return cases


def _render_grade(
    *,
    case: dict[str, Any],
    output_path: Path,
    runtime_source_root: Path,
    profile: dict[str, Any],
    output_root: Path,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if case["suite"] == "deterministic":
        from scripts.skills.evals.deterministic.run import grade as deterministic_grade

        grade = deterministic_grade(
            case["skill"],
            case["eval_id"],
            output_path,
            runtime_source_root=runtime_source_root,
        )
        status = grade["status"]
        return {"status": status, "grade": grade}, []

    dataset = case["dataset"]
    eval_case = case["case"]
    selected_criteria = [
        dataset["criteria_by_id"][criterion_id]
        for criterion_id in eval_case["criteria"]
    ]
    prompt = build_judge_prompt(
        criteria=selected_criteria,
        eval_input=eval_case["input_text"],
        reference=eval_case["reference_text"],
        candidate_output=output_path.read_text(encoding="utf-8"),
    )
    judge_workspace = (
        output_root
        / "judge-workspaces"
        / case["suite"]
        / case["skill"]
        / case["eval_id"]
        / f"attempt-{case.get('repeat_index', 1):02d}"
    )
    judge_workspace.mkdir(parents=True, exist_ok=False)
    judge_isolation = verify_judge_docker_command(
        profile["judge"]["command_argv"], evaluator_root=REPO_ROOT
    )
    judge_name = (
        "agent-eval-judge-" + sha256_bytes(str(judge_workspace).encode("utf-8"))[7:23]
    )
    judge_command, judge_cleanup = named_container_command(
        profile["judge"]["command_argv"], name=judge_name
    )
    judge_observations_path = judge_workspace / "launcher-observations.json"
    codex_judge = is_codex_judge(profile["judge"])
    judge_execution_command = (
        judge_launcher_argv_for_profile(
            profile["judge"],
            docker_argv=judge_command,
            observations_path=judge_observations_path,
        )
        if codex_judge
        else judge_command
    )
    result = run_command(
        judge_execution_command,
        input_text=prompt,
        cwd=judge_workspace,
        timeout_seconds=profile["judge"]["timeout_seconds"],
        timeout_cleanup_argv=judge_cleanup,
    )
    if result.timed_out:
        raise AgentExecutionError("Judge timed out")
    if result.cleanup_status == "failed":
        raise AgentExecutionError("Judge container cleanup failed")
    if result.exit_code != 0:
        raise AgentExecutionError(f"Judge exited with code {result.exit_code}")
    judge_capture = capture_codex_judge_output(
        result.stdout,
        observations_path=judge_observations_path if codex_judge else None,
    )
    safe_judge_output = judge_capture["response"]
    if codex_judge and (
        judge_capture["status"] != "completed" or judge_capture["redacted"]
    ):
        return {"status": "needs_review", "reason": "judge_evidence_unverified"}, [
            {
                "stdout": safe_judge_output,
                "stderr": result.stderr,
                "stderr_status": result.stderr_status,
                "exit_code": result.exit_code,
                "timed_out": result.timed_out,
                "duration_seconds": result.duration_seconds,
                "prompt_sha256": sha256_bytes(prompt.encode("utf-8")),
                "isolation": judge_isolation,
                "container_cleanup_status": result.cleanup_status,
                "launcher_observations": judge_capture["launcher_observations"],
            }
        ]
    normalized = normalize_judge_response(
        safe_judge_output,
        skill=case["skill"],
        eval_id=case["eval_id"],
        requested_criteria=eval_case["criteria"],
        criteria_by_id=dataset["criteria_by_id"],
    )
    status = normalized["verdict"]
    if safe_judge_output != result.stdout:
        status = "needs_review"
    return {"status": status, "grade": normalized}, [
        {
            "stdout": safe_judge_output,
            "stderr": result.stderr,
            "stderr_status": result.stderr_status,
            "exit_code": result.exit_code,
            "timed_out": result.timed_out,
            "duration_seconds": result.duration_seconds,
            "prompt_sha256": sha256_bytes(prompt.encode("utf-8")),
            "isolation": judge_isolation,
            "container_cleanup_status": result.cleanup_status,
            "launcher_observations": judge_capture["launcher_observations"],
        }
    ]


def _substitute_command(
    argv: list[str], *, workspace: Path, output_root: Path
) -> list[str]:
    replacements = {
        "{workspace}": str(workspace),
        "{output_root}": str(output_root),
        "{agent_output_root}": str(output_root),
    }
    return [
        argument.replace("{workspace}", replacements["{workspace}"])
        .replace("{output_root}", replacements["{output_root}"])
        .replace("{agent_output_root}", replacements["{agent_output_root}"])
        for argument in argv
    ]


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate and grade Skill eval outputs with an injected external Agent command."
    )
    parser.add_argument("--suite", choices=["deterministic", "semantic"], required=True)
    parser.add_argument("--skill", required=True, help="Skill name or explicit 'all'")
    parser.add_argument("--eval-id")
    parser.add_argument("--skill-revision", required=True)
    parser.add_argument("--execution-profile", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--agent-name", required=True)
    parser.add_argument("--agent-model", required=True)
    parser.add_argument("--agent-version")
    parser.add_argument(
        "--agent-command",
        nargs=argparse.REMAINDER,
        required=True,
        help="External Agent command argv; must be the final option.",
    )
    args = parser.parse_args(argv)
    if not args.agent_command:
        parser.error("--agent-command requires at least one argv entry")
    if args.repeat <= 0:
        parser.error("--repeat must be a positive integer")
    if args.repeat > 100 or args.repeat * 100 > MAX_CASES:
        parser.error("requested run exceeds the fixed case limit")
    if args.skill != "all" and not re.fullmatch(
        r"[a-z0-9]+(?:-[a-z0-9]+)*", args.skill
    ):
        parser.error("--skill must be a normalized Skill name or 'all'")
    if args.skill == "all" and args.eval_id:
        parser.error("--eval-id cannot be combined with --skill all")
    if any(SECRET_TEXT_RE.search(argument) for argument in args.agent_command):
        parser.error("--agent-command must not contain secrets")
    return args


def run(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    output_root = Path(os.path.abspath(args.output_root))
    result_path = output_root / "result.json"
    output_ready = False
    skill_root = output_root / ".skill-workspace"
    run_id = (
        f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{os.urandom(4).hex()}"
    )
    record: dict[str, Any] = {
        "schema_version": 1,
        "run_id": run_id,
        "suite": args.suite,
        "status": "running",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "skill_revision": args.skill_revision,
        "profile_fingerprint": None,
        "profile_verification": "unverified",
        "agent": {
            "name": args.agent_name,
            "model": args.agent_model,
            "version": args.agent_version,
        },
        "attempts": [],
        "excluded": [],
    }
    try:
        evaluator_sha = assert_clean_checkout(REPO_ROOT)
        skill_sha = resolve_commit(REPO_ROOT, args.skill_revision)
        profile = load_execution_profile(args.execution_profile)
        prepare_run_output_root(
            output_root,
            repository_root=REPO_ROOT,
            evidence_relative_path=profile["verification"]["evidence_path"],
        )
        output_ready = True
        if (
            profile["agent"]["name"] != args.agent_name
            or profile["agent"]["model"] != args.agent_model
        ):
            raise AgentEvalError(
                "agent name/model does not match the execution profile"
            )
        if args.suite == "semantic" and not profile["judge"]["command_argv"]:
            raise AgentEvalError("semantic suite requires an independent Judge command")
        profile_verified = verify_profile_evidence(
            profile, output_root, agent_command_argv=args.agent_command
        )
        if not profile_verified:
            raise AgentEvalError("live run requires verified isolation evidence")

        package_manifest = create_skill_workspace(REPO_ROOT, skill_sha, skill_root)
        skill_names = package_manifest["skills"]
        cases = (
            _load_deterministic_cases(args.skill, args.eval_id)
            if args.suite == "deterministic"
            else _load_semantic_cases(args.skill, args.eval_id)
        )
        if args.skill == "all":
            present = {case["skill"] for case in cases}
            candidate_skill_names = set(skill_names)
            if args.suite == "semantic":
                evaluator_skill_names = set(discover_semantic_skills())
            else:
                from scripts.skills.evals.deterministic.run import VALIDATORS

                evaluator_skill_names = set(VALIDATORS)
            record["excluded"] = [
                {
                    "skill": name,
                    "reason": f"no {args.suite} eval case in fixed Evaluator",
                }
                for name in skill_names
                if name not in present
            ] + [
                {
                    "skill": name,
                    "reason": f"Skill is absent from candidate revision {skill_sha}",
                }
                for name in sorted(evaluator_skill_names - candidate_skill_names)
            ]
            cases = [case for case in cases if case["skill"] in set(skill_names)]
        elif args.skill not in skill_names:
            raise AgentEvalError(
                "requested Skill is absent from the candidate revision"
            )
        if not cases:
            raise AgentEvalError("no matching fixed Evaluator cases were found")
        if len(cases) * args.repeat > MAX_CASES:
            raise AgentEvalError("requested batch exceeds the fixed case limit")
        routed_skill_names = visible_skill_names(cases)

        dataset_fp = _dataset_fingerprint(
            [item for case in cases for item in case["fingerprint_files"]]
        )
        record.update(
            {
                "status": "running",
                "evaluator": {"revision": evaluator_sha},
                "skill_package": package_manifest,
                "visible_skills": routed_skill_names,
                "dataset_fingerprint": dataset_fp,
                "profile_fingerprint": profile_fingerprint(profile),
                "profile_verification": "verified",
                "isolation_evidence": profile["verification"]["evidence_path"],
                "agent_command_fingerprint": canonical_fingerprint(args.agent_command),
                "judge_command_fingerprint": canonical_fingerprint(
                    profile["judge"]["command_argv"]
                ),
                "agent": {
                    key: profile["agent"].get(key)
                    for key in (
                        "name",
                        "model",
                        "cli_version",
                        "reasoning_effort",
                        "timeout_seconds",
                        "sandbox_policy",
                        "approval_policy",
                        "network_policy",
                        "tools",
                        "mcp_servers",
                        "external_instructions",
                        "global_config",
                    )
                },
                "judge": {
                    key: profile["judge"].get(key)
                    for key in (
                        "model",
                        "cli_version",
                        "reasoning_effort",
                        "timeout_seconds",
                        "sandbox_policy",
                        "approval_policy",
                        "network_policy",
                        "tools",
                        "mcp_servers",
                        "external_instructions",
                        "global_config",
                    )
                },
                "isolation": {
                    "method": profile["isolation"]["method"],
                    "agent_read_roots": profile["isolation"]["agent_read_roots"],
                    "evaluator_read_blocked": profile["isolation"][
                        "evaluator_read_blocked"
                    ],
                },
                "timeout_seconds": profile["agent"]["timeout_seconds"],
                "cases_requested": len(cases),
                "repeat": args.repeat,
                "agent_command_saved": False,
            }
        )
        atomic_write_json(result_path, record)

        attempt_number = 0
        for case in cases:
            for repeat_index in range(1, args.repeat + 1):
                attempt_number += 1
                attempt_id = f"{attempt_number:04d}"
                case_dir = (
                    output_root
                    / args.suite
                    / case["skill"]
                    / case["id"]
                    / f"attempt-{repeat_index:02d}"
                )
                case_dir.mkdir(parents=True, exist_ok=True)
                attempt: dict[str, Any] = {
                    "attempt_id": attempt_id,
                    "suite": args.suite,
                    "skill": case["skill"],
                    "eval_id": case["id"],
                    "repeat": repeat_index,
                    "input_fingerprint": sha256_bytes(case["input"].encode("utf-8")),
                    "status": "execution error",
                }
                with tempfile.TemporaryDirectory(prefix="agent-eval-") as temporary:
                    agent_workspace = Path(temporary)
                    prepare_agent_output_mountpoint(agent_workspace)
                    visible_skill_root = agent_workspace / ".agents" / "skills"
                    visible_skill_root.mkdir(parents=True)
                    for visible_skill in routed_skill_names:
                        shutil.copytree(
                            skill_root / "skills" / visible_skill,
                            visible_skill_root / visible_skill,
                        )
                    prompt = build_generation_prompt(
                        skill=case["skill"], eval_input=case["input"]
                    )
                    command = _substitute_command(
                        args.agent_command,
                        workspace=agent_workspace,
                        output_root=case_dir,
                    )
                    try:
                        attempt["agent_isolation"] = verify_agent_docker_command(
                            command,
                            workspace=agent_workspace,
                            output_root=case_dir,
                            evaluator_root=REPO_ROOT,
                        )
                        container_name = f"agent-eval-{run_id[-8:]}-{attempt_id}"
                        command, cleanup_command = named_container_command(
                            command, name=container_name
                        )
                        attempt["agent_command"] = {
                            "argv": command,
                            "fingerprint": canonical_fingerprint(command),
                        }
                        execution_command = command
                        if profile["agent"]["name"].lower() == "codex":
                            execution_command = launcher_argv(
                                output_root=case_dir,
                                model=profile["agent"]["model"],
                                reasoning_effort=profile["agent"]["reasoning_effort"],
                                cli_version=profile["agent"]["cli_version"],
                                sandbox_policy=profile["agent"]["sandbox_policy"],
                                docker_argv=command,
                            )
                            attempt["codex_launcher"] = {
                                "protocol": "codex_docker_launcher_v1",
                                "status": "used",
                            }
                        execution = run_command(
                            execution_command,
                            input_text=prompt,
                            cwd=agent_workspace,
                            timeout_seconds=profile["agent"]["timeout_seconds"],
                            timeout_cleanup_argv=cleanup_command,
                        )
                        attempt["agent_execution"] = {
                            "exit_code": execution.exit_code,
                            "timed_out": execution.timed_out,
                            "duration_seconds": execution.duration_seconds,
                            "stderr_status": execution.stderr_status,
                            "container_cleanup_status": execution.cleanup_status,
                        }
                        if execution.stderr is not None:
                            (case_dir / "agent.stderr.log").write_text(
                                execution.stderr, encoding="utf-8"
                            )
                        if (
                            execution.timed_out
                            or execution.exit_code != 0
                            or execution.cleanup_status == "failed"
                        ):
                            attempt["status"] = "execution error"
                            attempt["reason"] = (
                                "agent_timeout"
                                if execution.timed_out
                                else "agent_container_cleanup_failed"
                                if execution.cleanup_status == "failed"
                                else "agent_nonzero_exit"
                            )
                        else:
                            trace = capture_codex_jsonl_trace(
                                execution.stdout, skill_names=[case["skill"]]
                            )
                            output_text = trace["final_message"]
                            if trace.get("launcher_observations") is not None:
                                attempt["codex_launcher_evidence"] = trace[
                                    "launcher_observations"
                                ]
                                if trace.get("execution_status") != "completed":
                                    attempt["status"] = "needs_review"
                                    attempt["evidence_status"] = "evidence_unverified"
                                    attempt["evidence_reason"] = (
                                        "codex_launcher_evidence_unverified"
                                    )
                            if SECRET_TEXT_RE.search(output_text):
                                output_text = sanitize_diagnostic(output_text)
                                attempt["evidence_status"] = "evidence_unverified"
                                attempt["evidence_reason"] = (
                                    "secret_redaction_changed_candidate_output"
                                )
                                attempt["status"] = "needs_review"
                            trace_path = None
                            if trace["trace_summary"].get("status") == "captured":
                                trace_path = "agent-trace.json"
                                atomic_write_json(
                                    case_dir / trace_path, trace["trace_summary"]
                                )
                            attempt["agent_trace"] = {
                                "format": trace["format"],
                                "status": trace["status"],
                                "redacted": trace["redacted"],
                                "path": trace_path,
                            }
                            attempt["skill_use_observation"] = trace[
                                "skill_use_observation"
                            ].get(case["skill"], "unverified")
                            if trace["redacted"]:
                                attempt["status"] = "needs_review"
                                attempt["evidence_status"] = "evidence_unverified"
                                attempt["evidence_reason"] = "agent_trace_was_redacted"
                            (case_dir / "output.md").write_text(
                                output_text, encoding="utf-8"
                            )
                            attempt["output"] = {
                                "path": str(
                                    (case_dir / "output.md").relative_to(output_root)
                                ),
                                "sha256": sha256_bytes(output_text.encode("utf-8")),
                            }
                            if attempt["status"] != "needs_review":
                                case_record = {
                                    **case,
                                    "suite": args.suite,
                                    "eval_id": case["id"],
                                    "repeat_index": repeat_index,
                                }
                                grade, judge_runs = _render_grade(
                                    case=case_record,
                                    output_path=case_dir / "output.md",
                                    runtime_source_root=skill_root,
                                    profile=profile,
                                    output_root=output_root,
                                )
                                atomic_write_json(
                                    case_dir / "grade.json", grade["grade"]
                                )
                                attempt["grade"] = {
                                    "path": str(
                                        (case_dir / "grade.json").relative_to(
                                            output_root
                                        )
                                    ),
                                    "sha256": sha256_bytes(
                                        (case_dir / "grade.json").read_bytes()
                                    ),
                                }
                                attempt["status"] = grade["status"]
                                if judge_runs:
                                    attempt["judge"] = judge_runs
                    except (AgentExecutionError, OSError, ValueError, KeyError) as exc:
                        attempt["status"] = "execution error"
                        attempt["reason"] = sanitize_diagnostic(
                            f"{type(exc).__name__}: {exc}", 2000
                        )
                record["attempts"].append(attempt)
                atomic_write_json(result_path, record)

        shutil.rmtree(skill_root)
        record["workspace_cleanup"] = "succeeded"
        statuses = [item["status"] for item in record["attempts"]]
        if any(status == "execution error" for status in statuses):
            record["status"] = "execution error"
            exit_code = 2
        elif any(
            status in {"fail", "needs_review", "not_comparable"} for status in statuses
        ):
            record["status"] = "needs_review_or_fail"
            exit_code = 1
        elif all(status == "pass" for status in statuses):
            record["status"] = "pass"
            exit_code = 0
        else:
            record["status"] = "needs_review_or_fail"
            exit_code = 1
        record["summary"] = {
            status: statuses.count(status) for status in sorted(set(statuses))
        }
        record["exit_code"] = exit_code
        record["finished_at"] = datetime.now(timezone.utc).isoformat()
        atomic_write_json(result_path, record)
        print(
            json.dumps(
                {
                    "run_id": run_id,
                    "result": str(result_path),
                    "status": record["status"],
                },
                ensure_ascii=True,
            )
        )
        return exit_code
    except Exception as exc:
        record["status"] = "execution error"
        record["error"] = sanitize_diagnostic(f"{type(exc).__name__}: {exc}", 2000)
        record["exit_code"] = 2
        record["finished_at"] = datetime.now(timezone.utc).isoformat()
        if output_ready:
            atomic_write_json(result_path, record)
        print(f"agent evaluation error: {record['error']}", file=sys.stderr)
        return 2
    finally:
        if skill_root.exists():
            try:
                shutil.rmtree(skill_root)
            except OSError as cleanup_error:
                record["workspace_cleanup"] = "failed"
                record["cleanup_error"] = type(cleanup_error).__name__
                record["status"] = "execution error"
                record["exit_code"] = 2
                atomic_write_json(result_path, record)


def main() -> int:
    return run()


if __name__ == "__main__":
    raise SystemExit(main())
