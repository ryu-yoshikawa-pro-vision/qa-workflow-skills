from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

from .common import (
    AgentEvalError,
    atomic_write_json,
    atomic_write_text,
    canonical_fingerprint,
    capture_codex_jsonl_trace,
    capture_codex_judge_output,
    ensure_within,
    prepare_run_output_root,
    safe_relative_path,
    sanitize_diagnostic,
    sha256_bytes,
)
from .common_runtime_checks import (
    evaluate_runtime_captures,
    evaluate_workflow_runtime_capture,
)
from .executor import AgentExecutionError, run_command
from .prompt_builder import build_generation_prompt
from .target_workspace import (
    DEFAULT_TARGET_REVISION,
    SCENARIO_DIR,
    prepare_sanitized_target,
    verify_workspace_unchanged,
)
from .tools.codex_docker_launcher import launcher_argv as legacy_agent_launcher_argv
from .tools.codex_wsl2_bwrap_launcher import (
    cleanup_argv as codex_cleanup_argv,
    judge_launcher_argv_for_profile,
    launcher_argv,
)
from .tools.codex_judge_docker_launcher import (
    is_codex_judge,
)
from .tools.codex_judge_docker_launcher import (
    launcher_argv_for_profile as legacy_judge_launcher_argv_for_profile,
)
from .workspace import (
    assert_clean_checkout,
    create_skill_workspace,
    create_skill_workspace_from_root,
    load_execution_profile,
    named_container_command,
    profile_fingerprint,
    resolve_commit,
    verify_agent_docker_command,
    verify_judge_docker_command,
    verify_agent_wsl2_command,
    verify_judge_wsl2_command,
    verify_profile_evidence,
)

REPO_ROOT = Path(__file__).resolve().parents[4]
_ARTIFACT_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_STATUSES = {"executed", "reused", "skipped", "blocked", "incomplete"}
_JUDGE_GROUPS = ("workflow", "artifacts")


def load_scenario(scenario_dir: Path = SCENARIO_DIR) -> dict[str, Any]:
    try:
        scenario = json.loads(
            (scenario_dir / "scenario.json").read_text(encoding="utf-8")
        )
        task = (scenario_dir / "task.md").read_text(encoding="utf-8")
        rubric = json.loads((scenario_dir / "rubric.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AgentEvalError("fixed qa-training-store scenario is invalid") from exc
    if (
        not isinstance(scenario, dict)
        or scenario.get("schema_version") != 1
        or scenario.get("target_revision") != DEFAULT_TARGET_REVISION
        or not isinstance(scenario.get("required_artifacts"), list)
        or not isinstance(rubric, dict)
        or not isinstance(rubric.get("criteria"), list)
    ):
        raise AgentEvalError("fixed scenario contract is invalid")
    scenario["task_text"] = task
    scenario["rubric"] = rubric["criteria"]
    scenario["scenario_fingerprint"] = canonical_fingerprint(
        {
            "scenario": scenario,
            "task": task,
            "rubric": rubric,
        }
    )
    return scenario


def validate_artifact_index(
    output_root: Path, scenario: dict[str, Any]
) -> dict[str, Any]:
    index_path = output_root / "artifact-index.json"
    if not index_path.is_file() or index_path.is_symlink():
        return {
            "status": "needs_review",
            "reason": "artifact_index_missing_or_unsafe",
            "artifacts": [],
            "routing": [],
            "issues": [{"kind": "artifact_index_missing"}],
        }
    try:
        payload = json.loads(index_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {
            "status": "needs_review",
            "reason": "artifact_index_invalid_json",
            "artifacts": [],
            "routing": [],
            "issues": [{"kind": "artifact_index_invalid_json"}],
        }
    issues: list[dict[str, Any]] = []
    if not isinstance(payload, dict) or set(payload) != {
        "schema_version",
        "artifacts",
        "routing",
    }:
        return {
            "status": "needs_review",
            "reason": "artifact_index_schema_mismatch",
            "artifacts": [],
            "routing": [],
            "issues": [{"kind": "artifact_index_schema_mismatch"}],
        }
    if (
        payload["schema_version"] != 1
        or not isinstance(payload["artifacts"], list)
        or not isinstance(payload["routing"], list)
    ):
        return {
            "status": "needs_review",
            "reason": "artifact_index_schema_mismatch",
            "artifacts": [],
            "routing": [],
            "issues": [{"kind": "artifact_index_schema_mismatch"}],
        }

    artifact_rows: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    seen_paths: set[str] = set()
    seen_contracts: set[tuple[str, str, str]] = set()
    for index, row in enumerate(payload["artifacts"]):
        if not isinstance(row, dict) or set(row) != {
            "skill",
            "kind",
            "scope",
            "artifact_id",
            "path",
        }:
            issues.append({"kind": "invalid_artifact_row", "index": index})
            continue
        if any(
            not isinstance(row[field], str) or not row[field].strip()
            for field in ("skill", "kind", "scope", "artifact_id", "path")
        ):
            issues.append({"kind": "invalid_artifact_field", "index": index})
            continue
        artifact_id = row["artifact_id"]
        if not _ARTIFACT_ID_RE.fullmatch(artifact_id) or artifact_id in seen_ids:
            issues.append(
                {"kind": "invalid_or_duplicate_artifact_id", "artifact_id": artifact_id}
            )
            continue
        seen_ids.add(artifact_id)
        try:
            relative = safe_relative_path(row["path"])
            artifact_path = ensure_within(output_root / relative, output_root)
        except AgentEvalError:
            issues.append({"kind": "unsafe_artifact_path", "artifact_id": artifact_id})
            continue
        if PurePosixPath(row["path"]).is_absolute() or row["path"].replace(
            "\\", "/"
        ).startswith("."):
            issues.append(
                {"kind": "noncanonical_artifact_path", "artifact_id": artifact_id}
            )
            continue
        if artifact_path.is_symlink() or not artifact_path.is_file():
            issues.append(
                {
                    "kind": "artifact_missing_or_symlink",
                    "artifact_id": artifact_id,
                    "path": row["path"],
                }
            )
            continue
        if artifact_path.stat().st_size > scenario["max_artifact_file_bytes"]:
            issues.append(
                {"kind": "artifact_exceeds_size_limit", "artifact_id": artifact_id}
            )
            continue
        if row["path"] in seen_paths:
            issues.append({"kind": "duplicate_artifact_path", "path": row["path"]})
            continue
        seen_paths.add(row["path"])
        contract = (row["skill"], row["kind"], row["scope"])
        if contract in seen_contracts:
            issues.append(
                {"kind": "duplicate_artifact_contract", "artifact": list(contract)}
            )
        seen_contracts.add(contract)
        artifact_rows.append(
            {
                **row,
                "sha256": _file_hash(artifact_path),
                "size": artifact_path.stat().st_size,
            }
        )

    routing_rows: list[dict[str, Any]] = []
    routed_skills: set[tuple[str, str]] = set()
    for index, row in enumerate(payload["routing"]):
        if not isinstance(row, dict) or set(row) != {
            "skill",
            "scope",
            "status",
            "reason",
            "artifact_ids",
        }:
            issues.append({"kind": "invalid_routing_row", "index": index})
            continue
        if (
            not isinstance(row["skill"], str)
            or not isinstance(row["scope"], str)
            or row["status"] not in _STATUSES
            or not isinstance(row["reason"], str)
            or not row["reason"].strip()
            or not isinstance(row["artifact_ids"], list)
            or any(not isinstance(item, str) for item in row["artifact_ids"])
        ):
            issues.append({"kind": "invalid_routing_field", "index": index})
            continue
        key = (row["skill"], row["scope"])
        if key in routed_skills:
            issues.append(
                {
                    "kind": "duplicate_routing_row",
                    "skill": row["skill"],
                    "scope": row["scope"],
                }
            )
        routed_skills.add(key)
        unknown_ids = sorted(set(row["artifact_ids"]) - seen_ids)
        if unknown_ids:
            issues.append(
                {
                    "kind": "routing_references_unknown_artifacts",
                    "unknown_ids": unknown_ids,
                }
            )
        if row["status"] in {"executed", "reused"} and not row["artifact_ids"]:
            issues.append(
                {"kind": "completed_routing_without_artifact", "skill": row["skill"]}
            )
        if row["status"] in {"blocked", "incomplete", "skipped"}:
            issues.append(
                {
                    "kind": "noncompleted_routing",
                    "skill": row["skill"],
                    "status": row["status"],
                    "reason": sanitize_diagnostic(row["reason"], 500),
                }
            )
        routing_rows.append(dict(row))

    expected = {
        (item["skill"], item["kind"], item["scope"])
        for item in scenario["required_artifacts"]
    }
    actual = {(item["skill"], item["kind"], item["scope"]) for item in artifact_rows}
    for missing in sorted(expected - actual):
        issues.append(
            {"kind": "required_artifact_not_registered", "artifact": list(missing)}
        )
    for extra in sorted(actual - expected):
        if extra[0:2] != ("question-analysis", "question-analysis"):
            issues.append({"kind": "unexpected_artifact_kind", "artifact": list(extra)})
    expected_routes = {
        (item["skill"], item["scope"]) for item in scenario["required_artifacts"]
    }
    for missing in sorted(expected_routes - routed_skills):
        issues.append(
            {
                "kind": "required_routing_missing",
                "skill": missing[0],
                "scope": missing[1],
            }
        )
    routes_by_key = {(row["skill"], row["scope"]): row for row in routing_rows}
    for artifact in artifact_rows:
        route = routes_by_key.get((artifact["skill"], artifact["scope"]))
        if route is None or artifact["artifact_id"] not in route["artifact_ids"]:
            issues.append(
                {
                    "kind": "artifact_not_linked_from_routing",
                    "artifact_id": artifact["artifact_id"],
                }
            )
    total_size = sum(item["size"] for item in artifact_rows)
    if total_size > scenario["max_artifact_total_bytes"]:
        issues.append({"kind": "artifacts_exceed_total_size_limit", "size": total_size})
    return {
        "status": "pass" if not issues else "needs_review",
        "reason": None if not issues else "artifact_or_routing_contract_failed",
        "artifacts": artifact_rows,
        "routing": routing_rows,
        "issues": issues,
        "registered_total_bytes": total_size,
    }


def _file_hash(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return "sha256:" + digest.hexdigest()


_SECRET_TEXT_RE = re.compile(
    r"(?i)\b(?:Bearer\s+[A-Za-z0-9._~+/=-]{12,}|sk-[A-Za-z0-9_-]{16,}|gh[pousr]_[A-Za-z0-9]{20,}|(?:api[_-]?key|access[_-]?token|refresh[_-]?token|password)\s*[:=]\s*[^\s,;]+)"
)


def _copy_safe_agent_output(
    source: Path,
    destination: Path,
    *,
    reserved_paths: frozenset[str] = frozenset(),
) -> dict[str, Any]:
    destination.mkdir(parents=True, exist_ok=False)
    entries: list[dict[str, Any]] = []
    total = 0
    for path in sorted(source.rglob("*")):
        relative = path.relative_to(source)
        if path.is_symlink():
            entries.append(
                {
                    "path": relative.as_posix(),
                    "status": "evidence_unverified",
                    "reason": "symlink_output",
                }
            )
            continue
        if relative.as_posix() in reserved_paths:
            entries.append(
                {
                    "path": relative.as_posix(),
                    "status": "evidence_unverified",
                    "reason": "reserved_evaluator_output",
                }
            )
            continue
        if not path.is_file():
            continue
        size = path.stat().st_size
        total += size
        if total > 100_000_000:
            raise AgentEvalError("Agent output exceeds the saved artifact size limit")
        raw = path.read_bytes()
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            entries.append(
                {
                    "path": relative.as_posix(),
                    "status": "evidence_unverified",
                    "reason": "non_utf8_output_not_saved",
                }
            )
            continue
        safe_text = _SECRET_TEXT_RE.sub("[redacted]", text)
        safe = safe_text.encode("utf-8")
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(safe)
        entries.append(
            {
                "path": relative.as_posix(),
                "sha256": None if safe != raw else sha256_bytes(raw),
                "saved_sha256": sha256_bytes(safe),
                "status": "evidence_unverified" if safe != raw else "saved",
                "redacted": safe != raw,
                "size": len(safe),
            }
        )
    return {
        "status": "evidence_unverified"
        if any(item["status"] == "evidence_unverified" for item in entries)
        else "saved",
        "files": entries,
        "total_source_bytes": total,
    }


def _scan_secret_shaped_output(root: Path) -> list[str]:
    matches: list[str] = []
    if not root.is_dir():
        return matches
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            matches.append(path.relative_to(root).as_posix())
            continue
        if not path.is_file():
            continue
        try:
            value = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            matches.append(path.relative_to(root).as_posix())
            continue
        if _SECRET_TEXT_RE.search(value):
            matches.append(path.relative_to(root).as_posix())
    return matches


def build_artifact_manifest(
    output_root: Path, validation: dict[str, Any]
) -> dict[str, Any]:
    registered = {row["path"]: row for row in validation["artifacts"]}
    files: list[dict[str, Any]] = []
    if output_root.is_dir():
        for path in sorted(output_root.rglob("*")):
            if path.is_symlink():
                files.append(
                    {
                        "path": path.relative_to(output_root).as_posix(),
                        "classification": "unsafe_symlink",
                    }
                )
                continue
            if not path.is_file():
                continue
            relative = path.relative_to(output_root).as_posix()
            if relative == "artifact-manifest.json":
                continue
            if relative in registered:
                classification = "qa_artifact"
                artifact_id = registered[relative]["artifact_id"]
            elif relative.startswith(".runtime-evidence/"):
                classification = "runtime_evidence"
                artifact_id = None
            elif relative == "artifact-index.json":
                classification = "runner_internal"
                artifact_id = None
            else:
                classification = "unregistered_or_internal"
                artifact_id = None
            files.append(
                {
                    "path": relative,
                    "sha256": (
                        None
                        if _SECRET_TEXT_RE.search(
                            path.read_text(encoding="utf-8", errors="replace")
                        )
                        else _file_hash(path)
                    ),
                    "size": path.stat().st_size,
                    "classification": classification,
                    "artifact_id": artifact_id,
                }
            )
    return {
        "schema_version": 1,
        "files": files,
        "artifact_ids": sorted(row["artifact_id"] for row in validation["artifacts"]),
    }


def _read_qa_artifacts(output_root: Path, validation: dict[str, Any]) -> str:
    parts: list[str] = []
    for artifact in sorted(
        validation["artifacts"],
        key=lambda item: (item["skill"], item["kind"], item["path"]),
    ):
        path = ensure_within(
            output_root / safe_relative_path(artifact["path"]), output_root
        )
        text = path.read_text(encoding="utf-8")
        parts.append(
            f"## {artifact['skill']} / {artifact['kind']} ({artifact['artifact_id']})\n\n{text}"
        )
    return "\n\n---\n\n".join(parts)


def _judge_prompt(
    *,
    group: str,
    scenario: dict[str, Any],
    target_root: Path,
    output_root: Path,
    validation: dict[str, Any],
    final_message: str,
    machine_summary: dict[str, Any],
) -> tuple[str, list[str]]:
    from ..semantic.prompt_builder import build_judge_prompt

    criteria_all = scenario["rubric"]
    canonical_artifacts = _read_qa_artifacts(output_root, validation)
    if group == "workflow":
        requested = ["QTS-SEM-001", "QTS-SEM-002"]
        canonical = json.dumps(validation["routing"], ensure_ascii=False, indent=2)
        candidate = (
            canonical_artifacts
            + "\n\n## Workflow Routing / Final Response (untrusted)\n"
            + "### routing[]\n```json\n"
            + canonical
            + "\n```\n\n"
            + "### Final response\n"
            + sanitize_diagnostic(final_message, 20_000)
        )
        task_text = (
            scenario["task_text"]
            + "\n\n# Fixed machine summary\n```json\n"
            + json.dumps(
                {
                    "workflow_runtime_can_complete": machine_summary.get(
                        "workflow_runtime_can_complete"
                    ),
                    "workflow_runtime_has_unclosed_issues": machine_summary.get(
                        "workflow_runtime_has_unclosed_issues"
                    ),
                    "required_artifacts_present": machine_summary.get(
                        "required_artifacts_present"
                    ),
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n```"
        )
    else:
        requested = [f"QTS-SEM-{number:03d}" for number in range(3, 11)]
        candidate = canonical_artifacts
        actual_contracts = {
            (row["skill"], row["kind"], row["scope"]) for row in validation["artifacts"]
        }
        missing = [
            (item["skill"], item["kind"], item["scope"])
            for item in scenario["required_artifacts"]
            if (item["skill"], item["kind"], item["scope"]) not in actual_contracts
        ]
        if missing:
            candidate += "\n\n" + "\n".join(
                f"## Missing required artifact: {skill} / {kind} ({scope})"
                for skill, kind, scope in missing
            )
        task_text = scenario["task_text"]
    criteria = [row for row in criteria_all if row["id"] in requested]
    reference_parts: list[str] = []
    for relative in scenario["reference_paths"]:
        path = target_root / safe_relative_path(relative)
        reference_parts.append(f"# {relative}\n\n{path.read_text(encoding='utf-8')}")
    prompt = build_judge_prompt(
        criteria=criteria,
        eval_input=task_text,
        reference="\n\n---\n\n".join(reference_parts),
        candidate_output=candidate,
    )
    if group == "artifacts":
        routing_blob = json.dumps(validation["routing"], ensure_ascii=False, indent=2)
        final_blob = sanitize_diagnostic(final_message, 20_000)
        if (routing_blob and routing_blob in prompt) or (
            final_blob and final_blob in prompt
        ):
            raise AgentEvalError(
                "artifact Judge prompt contains workflow-only evidence"
            )
    return prompt, requested


def run_independent_judges(
    *,
    scenario: dict[str, Any],
    target_root: Path,
    output_root: Path,
    validation: dict[str, Any],
    final_message: str,
    machine_summary: dict[str, Any],
    profile: dict[str, Any],
    judge_root: Path,
) -> dict[str, Any]:
    from ..semantic.result import normalize_judge_response

    runs: list[dict[str, Any]] = []
    normalized_criteria: list[dict[str, Any]] = []
    criteria_by_id = {row["id"]: row for row in scenario["rubric"]}
    for group in _JUDGE_GROUPS:
        prompt, requested = _judge_prompt(
            group=group,
            scenario=scenario,
            target_root=target_root,
            output_root=output_root,
            validation=validation,
            final_message=final_message,
            machine_summary=machine_summary,
        )
        cwd = judge_root / group
        cwd.mkdir(parents=True, exist_ok=False)
        judge_observations_path = cwd / "launcher-observations.json"
        if profile.get("schema_version", 1) == 2:
            isolation = verify_judge_wsl2_command(
                profile["judge"]["command_argv"], evaluator_root=REPO_ROOT
            )
            codex_judge = True
            judge_execution_command = judge_launcher_argv_for_profile(
                profile["judge"], observations_path=judge_observations_path
            )
            judge_cleanup = codex_cleanup_argv(judge_execution_command)
        else:
            isolation = verify_judge_docker_command(
                profile["judge"]["command_argv"], evaluator_root=REPO_ROOT
            )
            judge_command, judge_cleanup = named_container_command(
                profile["judge"]["command_argv"],
                name="agent-eval-qts-judge-"
                + group
                + "-"
                + sha256_bytes(str(cwd).encode("utf-8"))[7:17],
            )
            codex_judge = is_codex_judge(profile["judge"])
            judge_execution_command = (
                legacy_judge_launcher_argv_for_profile(
                    profile["judge"],
                    docker_argv=judge_command,
                    observations_path=judge_observations_path,
                )
                if codex_judge
                else judge_command
            )
        execution = run_command(
            judge_execution_command,
            input_text=prompt,
            cwd=cwd,
            timeout_seconds=profile["judge"]["timeout_seconds"],
            timeout_cleanup_argv=judge_cleanup,
        )
        judge_capture = capture_codex_judge_output(
            execution.stdout,
            observations_path=judge_observations_path if codex_judge else None,
        )
        safe_stdout = judge_capture["response"]
        run_record: dict[str, Any] = {
            "group": group,
            "criteria": requested,
            "prompt_sha256": sha256_bytes(prompt.encode("utf-8")),
            "exit_code": execution.exit_code,
            "timed_out": execution.timed_out,
            "duration_seconds": execution.duration_seconds,
            "stderr_status": execution.stderr_status,
            "response_sha256": sha256_bytes(safe_stdout.encode("utf-8")),
            "evidence_status": "captured"
            if safe_stdout == execution.stdout
            and judge_capture["status"] in {"unwrapped", "completed"}
            else "evidence_unverified",
            "isolation": isolation,
            "container_cleanup_status": execution.cleanup_status,
            "response": safe_stdout,
            "launcher_observations": judge_capture["launcher_observations"],
        }
        if (
            execution.timed_out
            or execution.exit_code != 0
            or execution.cleanup_status == "failed"
        ):
            run_record["status"] = "execution_error"
            if execution.cleanup_status == "failed":
                run_record["error"] = "judge_container_cleanup_failed"
            runs.append(run_record)
            continue
        if run_record["evidence_status"] != "captured":
            run_record["status"] = "evidence_unverified"
            runs.append(run_record)
            continue
        try:
            normalized = normalize_judge_response(
                safe_stdout,
                skill="qa-training-store",
                eval_id="qa-training-store-checkout-payment-web-v1",
                requested_criteria=requested,
                criteria_by_id=criteria_by_id,
            )
        except ValueError as exc:
            run_record["status"] = "invalid_response"
            run_record["reason"] = sanitize_diagnostic(str(exc), 1000)
            runs.append(run_record)
            continue
        run_record["status"] = (
            "pass"
            if run_record["evidence_status"] == "captured"
            else "evidence_unverified"
        )
        normalized_criteria.extend(normalized["criteria"])
        runs.append(run_record)
    if any(item["status"] == "execution_error" for item in runs):
        return {"status": "execution_error", "runs": runs, "normalized": None}
    if len(normalized_criteria) != 10 or any(item["status"] != "pass" for item in runs):
        return {"status": "needs_review", "runs": runs, "normalized": None}
    merged = normalize_judge_response(
        json.dumps(
            {
                "criteria": [
                    {
                        "id": item["id"],
                        "evaluable": item["rating"] is not None,
                        "rating": item["rating"],
                        "reason": item["reason"],
                        "evidence": item["evidence"],
                    }
                    for item in normalized_criteria
                ]
            },
            ensure_ascii=False,
        ),
        skill="qa-training-store",
        eval_id="qa-training-store-checkout-payment-web-v1",
        requested_criteria=[row["id"] for row in scenario["rubric"]],
        criteria_by_id=criteria_by_id,
    )
    return {"status": merged["verdict"], "runs": runs, "normalized": merged}


def _substitute(argv: list[str], *, workspace: Path, output_root: Path) -> list[str]:
    replace = {"{workspace}": str(workspace), "{output_root}": str(output_root)}
    return [
        argument.replace("{workspace}", replace["{workspace}"]).replace(
            "{output_root}", replace["{output_root}"]
        )
        for argument in argv
    ]


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the fixed qa-training-store Checkout/Payment Agent evaluation."
    )
    parser.add_argument("--target-root", type=Path, required=True)
    parser.add_argument("--skill-revision", required=True)
    parser.add_argument(
        "--skill-package-root",
        type=Path,
        help="Optional uncommitted review candidate package; it is identified by content fingerprint and never committed by this runner",
    )
    parser.add_argument("--execution-profile", type=Path, required=True)
    parser.add_argument("--verifier-image", required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--repeat", type=int, default=2)
    parser.add_argument("--agent-command", nargs=argparse.REMAINDER, required=True)
    args = parser.parse_args(argv)
    if not args.agent_command:
        parser.error("--agent-command requires an argv command")
    if any(
        re.search(
            r"(?i)(?:bearer\s+\S{12,}|sk-[A-Za-z0-9_-]{16,}|gh[pousr]_[A-Za-z0-9]{20,}|(?:api[_-]?key|access[_-]?token|password)\s*[:=]\s*\S+)",
            item,
        )
        for item in args.agent_command
    ):
        parser.error("--agent-command must not contain secrets")
    if args.repeat < 2 or args.repeat > 10:
        parser.error("phase 2 requires 2-10 independent repeats")
    if len(args.skill_revision) != 40 or any(
        char not in "0123456789abcdef" for char in args.skill_revision
    ):
        parser.error("--skill-revision must be a full lowercase Git SHA")
    if not args.verifier_image:
        parser.error(
            "--verifier-image is required for network-isolated verifier replay"
        )
    return args


def run(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    run_id = f"qts-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{os.urandom(4).hex()}"
    output_root = Path(os.path.abspath(args.output_root))
    result_path = output_root / "result.json"
    output_ready = False
    scenario = load_scenario()
    record: dict[str, Any] = {
        "schema_version": 1,
        "run_id": run_id,
        "status": "running",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "scenario_id": scenario["scenario_id"],
        "scenario_fingerprint": scenario["scenario_fingerprint"],
        "target_repository": scenario["target_repository"],
        "target_revision": scenario["target_revision"],
        "skill_revision": args.skill_revision,
        "repeat": args.repeat,
        "attempts": [],
        "errors": [],
    }
    try:
        evaluator_sha = assert_clean_checkout(REPO_ROOT)
        skill_revision = resolve_commit(REPO_ROOT, args.skill_revision)
        target_source_checkout_sha = assert_clean_checkout(args.target_root)
        target_sha = resolve_commit(args.target_root, DEFAULT_TARGET_REVISION)
        if target_sha != scenario["target_revision"]:
            raise AgentEvalError(
                "fixed target revision did not resolve to the scenario SHA"
            )
        profile = load_execution_profile(args.execution_profile)
        prepare_run_output_root(
            output_root,
            repository_root=REPO_ROOT,
            evidence_relative_path=profile["verification"]["evidence_path"],
        )
        output_ready = True
        if args.agent_command == profile["judge"]["command_argv"]:
            raise AgentEvalError("Agent and Judge must use separate commands")
        if (
            profile["judge"]["tools"]
            or profile["judge"]["mcp_servers"]
            or profile["judge"]["skill_roots"]
        ):
            raise AgentEvalError(
                "Judge tools, MCP servers, and Skill roots must be disabled"
            )
        if set(profile["agent"]["skill_roots"]) != {"/workspace/.agents/skills"}:
            raise AgentEvalError(
                "Agent-visible Skill root must be exactly the candidate package"
            )
        if not verify_profile_evidence(
            profile, output_root, agent_command_argv=args.agent_command
        ):
            raise AgentEvalError(
                "live target evaluation requires verified isolation evidence"
            )
        candidate_package = output_root / ".candidate-package"
        if args.skill_package_root:
            base_manifest = create_skill_workspace(
                REPO_ROOT, skill_revision, output_root / ".candidate-base-package"
            )
            package_manifest = create_skill_workspace_from_root(
                args.skill_package_root,
                candidate_package,
                expected_skills=set(base_manifest["skills"]),
                parent_revision=skill_revision,
            )
            shutil.rmtree(output_root / ".candidate-base-package")
        else:
            package_manifest = create_skill_workspace(
                REPO_ROOT, skill_revision, candidate_package
            )
        record.update(
            {
                "evaluator_revision": evaluator_sha,
                "target_source_revision": target_sha,
                "target_source_checkout_revision": target_source_checkout_sha,
                "execution_profile_fingerprint": profile_fingerprint(profile),
                "profile_verification": "verified",
                "profile_evidence_path": profile["verification"]["evidence_path"],
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
                "skill_package_manifest": package_manifest,
                "skill_candidate_revision_status": package_manifest.get(
                    "candidate_revision_status", "git_commit"
                ),
                "judge_reference_fingerprint": canonical_fingerprint(
                    {
                        relative: _file_hash(args.target_root / relative)
                        for relative in scenario["reference_paths"]
                    }
                ),
                "verifier_image": args.verifier_image,
                "agent_command_template": args.agent_command,
                "agent_command_fingerprint": canonical_fingerprint(args.agent_command),
                "judge_command_template": profile["judge"]["command_argv"],
                "judge_command_fingerprint": canonical_fingerprint(
                    profile["judge"]["command_argv"]
                ),
                "isolation": {
                    "method": profile["isolation"]["method"],
                    "agent_read_roots": profile["isolation"]["agent_read_roots"],
                    "evaluator_read_blocked": profile["isolation"][
                        "evaluator_read_blocked"
                    ],
                    "evidence": "verified",
                },
            }
        )
        if output_ready:
            atomic_write_json(result_path, record)
        for attempt_index in range(1, args.repeat + 1):
            attempt_id = f"attempt-{attempt_index:02d}"
            attempt_root = output_root / attempt_id
            attempt_root.mkdir()
            with tempfile.TemporaryDirectory(
                prefix=f"{run_id}-{attempt_index}-"
            ) as temporary:
                temp_root = Path(temporary)
                target = temp_root / "target"
                prepare = prepare_sanitized_target(
                    source_root=args.target_root,
                    source_revision=target_sha,
                    candidate_skills_root=candidate_package / "skills",
                    verifier_capture_source=Path(__file__).with_name(
                        "verifier_capture.py"
                    ),
                    destination=target,
                )
                prompt = build_generation_prompt(
                    skill="qa-workflow", eval_input=scenario["task_text"]
                )
                agent_execution_evidence = None
                agent_execution_path = attempt_root / "agent-execution.json"
                try:
                    agent_command = _substitute(
                        args.agent_command,
                        workspace=target,
                        output_root=target / ".qa-eval-output",
                    )
                    if profile.get("schema_version", 1) == 2:
                        agent_isolation = verify_agent_wsl2_command(
                            agent_command,
                            workspace=target,
                            output_root=target / ".qa-eval-output",
                            evaluator_root=REPO_ROOT,
                        )
                        cleanup_command = None
                    else:
                        agent_isolation = verify_agent_docker_command(
                            agent_command,
                            workspace=target,
                            output_root=target / ".qa-eval-output",
                            evaluator_root=REPO_ROOT,
                        )
                        agent_command, cleanup_command = named_container_command(
                            agent_command,
                            name=f"agent-eval-{run_id[-8:]}-{attempt_index:02d}",
                        )
                    execution_command = agent_command
                    if profile.get("schema_version", 1) == 2:
                        execution_command = launcher_argv(
                            mode="agent",
                            output_root=target / ".qa-eval-output",
                            observations_path=attempt_root / "agent-launcher-observations.json",
                            model=profile["agent"]["model"],
                            reasoning_effort=profile["agent"]["reasoning_effort"],
                            sandbox_policy=profile["agent"]["sandbox_policy"],
                            workspace_root=target,
                        )
                        cleanup_command = codex_cleanup_argv(execution_command)
                    elif profile["agent"]["name"].lower() == "codex":
                        execution_command = legacy_agent_launcher_argv(
                            output_root=target / ".qa-eval-output",
                            model=profile["agent"]["model"],
                            reasoning_effort=profile["agent"]["reasoning_effort"],
                            cli_version=profile["agent"]["cli_version"],
                            sandbox_policy=profile["agent"]["sandbox_policy"],
                            docker_argv=agent_command,
                        )
                    agent = run_command(
                        execution_command,
                        input_text=prompt,
                        cwd=target,
                        timeout_seconds=profile["agent"]["timeout_seconds"],
                        timeout_cleanup_argv=cleanup_command,
                    )
                    agent_execution_evidence = {
                        "exit_code": agent.exit_code,
                        "timed_out": agent.timed_out,
                        "duration_seconds": agent.duration_seconds,
                        "stderr_status": agent.stderr_status,
                        "container_cleanup_status": agent.cleanup_status,
                    }
                    atomic_write_json(
                        agent_execution_path,
                        {
                            **agent_execution_evidence,
                            "record_status": "execution_metadata_only",
                        },
                    )
                    if agent.cleanup_status == "failed":
                        raise AgentExecutionError("agent_container_cleanup_failed")
                    trace = capture_codex_jsonl_trace(
                        agent.stdout,
                        skill_names=[
                            item["skill"] for item in scenario["required_artifacts"]
                        ],
                    )
                    final_message = sanitize_diagnostic(trace["final_message"])
                    trace_path = None
                    if trace["trace_summary"].get("status") == "captured":
                        trace_file = attempt_root / "agent-trace.json"
                        atomic_write_json(trace_file, trace["trace_summary"])
                        trace_path = str(trace_file.relative_to(output_root))
                    atomic_write_json(
                        agent_execution_path,
                        {
                            "exit_code": agent.exit_code,
                            "timed_out": agent.timed_out,
                            "duration_seconds": agent.duration_seconds,
                            "stderr_status": agent.stderr_status,
                            "container_cleanup_status": agent.cleanup_status,
                            "command_argv": agent_command,
                            "command_fingerprint": canonical_fingerprint(agent_command),
                            "stderr": agent.stderr,
                            "stdout_sha256": sha256_bytes(
                                sanitize_diagnostic(agent.stdout).encode("utf-8")
                            ),
                            "final_message_sha256": sha256_bytes(
                                final_message.encode("utf-8")
                            ),
                            "trace_format": trace["format"],
                            "trace_status": trace["status"],
                            "trace_path": trace_path,
                            "trace_redacted": trace["redacted"],
                            "codex_launcher_evidence": trace.get(
                                "launcher_observations"
                            ),
                        },
                    )
                    workspace_integrity = verify_workspace_unchanged(
                        target, prepare["baseline_manifest"]
                    )
                    atomic_write_json(
                        attempt_root / "target-integrity.json", workspace_integrity
                    )
                    qa_root = target / ".qa-eval-output"
                    validation = validate_artifact_index(qa_root, scenario)
                    manifest = build_artifact_manifest(qa_root, validation)
                    secret_paths = _scan_secret_shaped_output(qa_root)
                    atomic_write_json(
                        attempt_root / "output-safety-scan.json",
                        {
                            "status": "evidence_unverified"
                            if secret_paths
                            else "clear",
                            "secret_shaped_or_unreadable_paths": secret_paths,
                        },
                    )
                    machine_summary = {
                        "artifact_index_status": validation["status"],
                        "issues": validation["issues"],
                        "workspace_unchanged": workspace_integrity["unchanged"],
                        "agent_exit_code": agent.exit_code,
                        "agent_timed_out": agent.timed_out,
                        "required_artifacts_present": validation["status"] == "pass",
                    }
                    atomic_write_json(
                        attempt_root / "artifact-validation.json", validation
                    )
                    runtime = evaluate_runtime_captures(
                        capture_root=qa_root / ".runtime-evidence",
                        candidate_package_root=candidate_package,
                        verifier_image=args.verifier_image,
                        fixed_evaluator_root=REPO_ROOT,
                        expected_artifacts=validation["artifacts"],
                        trace_commands=trace["commands"]
                        if trace["status"] == "captured"
                        else None,
                    )
                    workflow_runtime = evaluate_workflow_runtime_capture(
                        capture_root=qa_root / ".runtime-evidence",
                        candidate_package_root=candidate_package,
                        verifier_image=args.verifier_image,
                        fixed_evaluator_root=REPO_ROOT,
                        expected_artifacts=validation["artifacts"],
                        trace_commands=trace["commands"]
                        if trace["status"] == "captured"
                        else None,
                    )
                    machine_summary["workflow_runtime_can_complete"] = (
                        workflow_runtime.get("workflow_runtime_can_complete")
                    )
                    machine_summary["workflow_runtime_has_unclosed_issues"] = (
                        workflow_runtime.get("workflow_runtime_has_unclosed_issues")
                    )
                    atomic_write_json(
                        attempt_root / "runtime-checks.json",
                        {"verifier": runtime, "workflow_runtime": workflow_runtime},
                    )
                    judges: dict[str, Any]
                    if (
                        agent.timed_out
                        or agent.exit_code != 0
                        or agent.cleanup_status == "failed"
                    ):
                        judges = {
                            "status": "not_run",
                            "reason": "agent_execution_failed",
                            "runs": [],
                        }
                    elif (
                        trace.get("launcher_observations") is not None
                        and trace.get("execution_status") != "completed"
                    ):
                        judges = {
                            "status": "not_run",
                            "reason": "codex_launcher_evidence_unverified",
                            "runs": [],
                        }
                    elif trace["redacted"]:
                        judges = {
                            "status": "not_run",
                            "reason": "agent_output_redacted",
                            "runs": [],
                        }
                    elif secret_paths:
                        judges = {
                            "status": "not_run",
                            "reason": "output_safety_scan_requires_review",
                            "runs": [],
                        }
                    elif validation["status"] != "pass":
                        # Keep a complete diagnosis even when the machine contract is incomplete.
                        judges = (
                            run_independent_judges(
                                scenario=scenario,
                                target_root=target,
                                output_root=qa_root,
                                validation=validation,
                                final_message=final_message,
                                machine_summary=machine_summary,
                                profile=profile,
                                judge_root=attempt_root / "judge-workspaces",
                            )
                            if validation["artifacts"]
                            else {
                                "status": "not_run",
                                "reason": "no_canonical_qa_artifacts",
                                "runs": [],
                            }
                        )
                    else:
                        judges = run_independent_judges(
                            scenario=scenario,
                            target_root=target,
                            output_root=qa_root,
                            validation=validation,
                            final_message=final_message,
                            machine_summary=machine_summary,
                            profile=profile,
                            judge_root=attempt_root / "judge-workspaces",
                        )
                    atomic_write_json(attempt_root / "judge-result.json", judges)
                    saved_output_root = attempt_root / "qa-output"
                    saved_output = _copy_safe_agent_output(
                        qa_root,
                        saved_output_root,
                        reserved_paths=frozenset(
                            {"artifact-manifest.json", "final-message.md"}
                        ),
                    )
                    atomic_write_text(
                        saved_output_root / "final-message.md", final_message
                    )
                    atomic_write_json(
                        saved_output_root / "artifact-manifest.json", manifest
                    )
                    atomic_write_json(
                        attempt_root / "saved-agent-output.json", saved_output
                    )
                    safe_final = sanitize_diagnostic(final_message)
                    attempt_status = "pass"
                    if (
                        safe_final != final_message
                        or trace["redacted"]
                        or (
                            trace.get("launcher_observations") is not None
                            and trace.get("execution_status") != "completed"
                        )
                        or secret_paths
                        or not workspace_integrity["unchanged"]
                    ):
                        attempt_status = "needs_review"
                    elif (
                        agent.timed_out
                        or agent.exit_code != 0
                        or agent.cleanup_status == "failed"
                    ):
                        attempt_status = "execution_error"
                    elif validation["status"] != "pass":
                        attempt_status = "needs_review"
                    if (
                        runtime["status"] == "environment_error"
                        or workflow_runtime["status"] == "environment_error"
                    ):
                        attempt_status = "execution_error"
                    elif (
                        runtime["status"] == "fail"
                        or workflow_runtime["status"] == "fail"
                    ):
                        attempt_status = "fail"
                    elif (
                        runtime["status"] == "evidence_unverified"
                        or workflow_runtime["status"] == "evidence_unverified"
                    ):
                        if attempt_status == "pass":
                            attempt_status = "needs_review"
                    if judges["status"] == "fail":
                        attempt_status = "fail"
                    elif (
                        judges["status"] == "needs_review" and attempt_status == "pass"
                    ):
                        attempt_status = "needs_review"
                    if judges["status"] == "execution_error":
                        attempt_status = "execution_error"
                    if (
                        saved_output["status"] == "evidence_unverified"
                        and attempt_status == "pass"
                    ):
                        attempt_status = "needs_review"
                    attempt_record = {
                        "attempt_id": attempt_id,
                        "status": attempt_status,
                        "synthetic_target_baseline_revision": prepare[
                            "synthetic_baseline_revision"
                        ],
                        "target_source_manifest_fingerprint": prepare[
                            "source_manifest_fingerprint"
                        ],
                        "sanitized_target_manifest_fingerprint": prepare[
                            "baseline_manifest_fingerprint"
                        ],
                        "agent_exit_code": agent.exit_code,
                        "agent_timed_out": agent.timed_out,
                        "workspace_integrity": workspace_integrity,
                        "agent_isolation": agent_isolation,
                        "codex_launcher_evidence": trace.get("launcher_observations"),
                        "skill_use_observation": {
                            artifact["skill"]: (
                                "observed"
                                if trace["skill_use_observation"].get(artifact["skill"])
                                == "observed"
                                and any(
                                    route.get("skill") == artifact["skill"]
                                    and route.get("status") == "executed"
                                    for route in validation["routing"]
                                )
                                else "unverified"
                            )
                            for artifact in scenario["required_artifacts"]
                        },
                        "agent_trace_path": trace_path,
                        "agent_trace_status": trace["status"],
                        "artifact_index_status": validation["status"],
                        "artifact_manifest": str(
                            (
                                attempt_root / "qa-output" / "artifact-manifest.json"
                            ).relative_to(output_root)
                        ),
                        "saved_output_root": str(
                            (attempt_root / "qa-output").relative_to(output_root)
                        ),
                        "runtime_status": {
                            "verifier": runtime["status"],
                            "workflow_runtime": workflow_runtime["status"],
                        },
                        "judge_status": judges["status"],
                        "saved_result_root": str(attempt_root.relative_to(output_root)),
                    }
                    atomic_write_json(attempt_root / "attempt.json", attempt_record)
                    record["attempts"].append(attempt_record)
                    atomic_write_json(result_path, record)
                except (
                    AgentExecutionError,
                    OSError,
                    ValueError,
                    KeyError,
                    AgentEvalError,
                ) as exc:
                    attempt_record = {
                        "attempt_id": attempt_id,
                        "status": "execution_error",
                        "error": sanitize_diagnostic(
                            f"{type(exc).__name__}: {exc}", 2000
                        ),
                    }
                    if agent_execution_evidence is not None:
                        attempt_record["agent_execution"] = {
                            **agent_execution_evidence,
                            "path": str(agent_execution_path.relative_to(output_root)),
                        }
                    atomic_write_json(attempt_root / "attempt.json", attempt_record)
                    record["attempts"].append(attempt_record)
                    atomic_write_json(result_path, record)
            # Each attempt has an independent target and process tree; no state is carried forward.
        statuses = [item["status"] for item in record["attempts"]]
        if "execution_error" in statuses:
            record["status"] = "execution_error"
            exit_code = 2
        elif len(statuses) != args.repeat or any(
            status != "pass" for status in statuses
        ):
            record["status"] = "needs_review"
            exit_code = 1
        else:
            record["status"] = "pass"
            exit_code = 0
        record["summary"] = {
            status: statuses.count(status) for status in sorted(set(statuses))
        }
        record["exit_code"] = exit_code
        record["finished_at"] = datetime.now(timezone.utc).isoformat()
        shutil.rmtree(candidate_package)
        if args.skill_package_root:
            candidate_recheck = output_root / ".candidate-package-recheck"
            rechecked = create_skill_workspace_from_root(
                args.skill_package_root,
                candidate_recheck,
                expected_skills=set(package_manifest["skills"]),
                parent_revision=skill_revision,
            )
            shutil.rmtree(candidate_recheck)
            if (
                rechecked["package_fingerprint"]
                != package_manifest["package_fingerprint"]
            ):
                raise AgentEvalError(
                    "candidate package changed during the evaluation run"
                )
        record["candidate_workspace_cleanup"] = "succeeded"
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
        record["status"] = "execution_error"
        record["error"] = sanitize_diagnostic(f"{type(exc).__name__}: {exc}", 2000)
        record["exit_code"] = 2
        record["finished_at"] = datetime.now(timezone.utc).isoformat()
        if output_ready:
            atomic_write_json(result_path, record)
        print(f"qa-training-store evaluation error: {record['error']}", file=sys.stderr)
        return 2


def main() -> int:
    return run()


if __name__ == "__main__":
    raise SystemExit(main())
