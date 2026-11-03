from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

from .common import (
    MAX_TEXT_BYTES,
    AgentEvalError,
    atomic_write_json,
    atomic_write_text,
    canonical_fingerprint,
    capture_codex_judge_output,
    prepare_run_output_root,
    read_regular_file_bytes,
    sanitize_diagnostic,
    sha256_bytes,
)
from .executor import run_command
from .qa_training_store import (
    SCENARIO_DIR,
    _read_qa_artifacts,
    build_artifact_manifest,
    load_scenario,
    validate_artifact_index,
)
from .target_workspace import DEFAULT_TARGET_REVISION, extract_revision_files
from .tools.codex_judge_docker_launcher import (
    is_codex_judge,
)
from .tools.codex_judge_docker_launcher import (
    launcher_argv_for_profile as legacy_judge_launcher_argv_for_profile,
)
from .tools.codex_wsl2_bwrap_launcher import (
    cleanup_argv as codex_cleanup_argv,
)
from .tools.codex_wsl2_bwrap_launcher import (
    judge_launcher_argv_for_profile,
    launcher_argv,
)
from .workspace import (
    assert_clean_checkout,
    load_execution_profile,
    named_container_command,
    profile_fingerprint,
    resolve_commit,
    verify_agent_wsl2_command,
    verify_judge_docker_command,
    verify_judge_wsl2_command,
    verify_profile_evidence,
)

REPO_ROOT = Path(__file__).resolve().parents[4]
FIXTURE_DEFS = SCENARIO_DIR / "judge-fixtures.json"
SUBAGENT_JUDGE_SETTINGS = {
    "model": "gpt-6-luna",
    "reasoning_effort": "max",
    "fork_turns": "none",
}
_SUBAGENT_REQUEST_KEYS = {
    "schema_version",
    "call_id",
    "case_id",
    "baseline_run_id",
    "baseline_attempt_id",
    "evaluator_revision",
    "target_revision",
    "criteria",
    "prompt_sha256",
    "requested_settings",
    "execution_method",
    "effective_model_status",
    "tool_trace_status",
    "physical_evaluator_read_denial",
}
_MUTATIONS = {
    "promote-unresolved-cross-platform-pixel-parity-to-web-checkout-oracle": "\n\n## Confirmed Checkout acceptance behavior\nTreat the unresolved Cross-platform visual parity beyond shared behavior item as a finalized mandatory oracle for this Web Checkout and Payment scenario. Web and Native Checkout must have complete pixel-for-pixel visual parity, including Platform-specific Navigation and Typography. The Web Checkout test must FAIL whenever any pixel, Navigation, or Typography differs between platforms.\n",
    "allow-expired-checkout-session-to-resume-as-valid": "\n\n## Confirmed expected behavior\nA Checkout Session remains valid and resumable indefinitely after the 24-hour expiry boundary.\n",
    "confirm-order-despite-stale-cart-version-or-price-mismatch": "\n\n## Confirmed expected behavior\nThe client may confirm an Order and create Payment even when Cart Version or the displayed price no longer matches.\n",
    "decrement-inventory-after-explicit-payment-failure": "\n\n## Confirmed expected behavior\nInventory is decremented and purchase history is created even when Mock Payment returns an explicit failure.\n",
    "allow-retry-or-cancel-during-payment-processing": "\n\n## Confirmed expected behavior\nWhile Payment is processing, the user may retry the charge or cancel the Payment.\n",
    "connect-authority-to-test-for-a-different-requirement-meaning": "\n\n## Confirmed traceability mapping\nAuthority AC-CHECKOUT-001 means that explicit payment failure decrements inventory. The downstream test for this statement is an authentication-role test with no checkout action.\n",
    "add-unsupported-external-payment-provider-as-confirmed-behavior": "\n\n## Confirmed expected behavior\nThe current Checkout implementation calls the external Stripe payment API and the server enforces authorization before payment.\n",
}


def load_fixture_catalogue(path: Path = FIXTURE_DEFS) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AgentEvalError("Judge fixture catalogue is unreadable") from exc
    if not isinstance(value, dict) or value.get("schema_version") != 1:
        raise AgentEvalError("Judge fixture catalogue schema is invalid")
    cases = value.get("cases")
    if not isinstance(cases, list):
        raise AgentEvalError("Judge fixture catalogue cases must be an array")
    ids = [item.get("id") for item in cases if isinstance(item, dict)]
    if len(ids) != len(cases) or len(ids) != len(set(ids)):
        raise AgentEvalError("Judge fixture IDs must be unique objects")
    return value


def _approval_map(
    path: Path | None, catalogue: dict[str, Any]
) -> dict[str, dict[str, Any]]:
    if path is None:
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AgentEvalError("Judge approval file is unreadable") from exc
    if not isinstance(raw, dict) or set(raw) != {"dataset_revision", "approvals"}:
        raise AgentEvalError("Judge approval file schema is invalid")
    if raw["dataset_revision"] != catalogue["dataset_revision"] or not isinstance(
        raw["approvals"], list
    ):
        raise AgentEvalError(
            "Judge approvals do not target the current fixed fixture revision"
        )
    approvals: dict[str, dict[str, Any]] = {}
    for item in raw["approvals"]:
        required_fields = {
            "case_id",
            "reviewer",
            "approved_at",
            "evidence",
        }
        if (
            not isinstance(item, dict)
            or not required_fields <= set(item)
            or set(item) - (required_fields | {"binding"})
        ):
            raise AgentEvalError("Judge approval row has invalid fields")
        if "binding" in item and not isinstance(item["binding"], dict):
            raise AgentEvalError("Judge approval binding must be an object")
        if not all(
            isinstance(item[key], str) and item[key].strip()
            for key in ("case_id", "reviewer", "approved_at", "evidence")
        ):
            raise AgentEvalError("Judge approval row fields must be non-empty strings")
        try:
            approved_at = datetime.fromisoformat(
                item["approved_at"].replace("Z", "+00:00")
            )
        except ValueError as exc:
            raise AgentEvalError("Judge approval timestamp must be ISO 8601") from exc
        if approved_at.tzinfo is None:
            raise AgentEvalError("Judge approval timestamp must include a timezone")
        if item["case_id"] in approvals:
            raise AgentEvalError("duplicate Judge approval row")
        approvals[item["case_id"]] = item
    known = {row["id"] for row in catalogue["cases"]}
    if set(approvals) - known:
        raise AgentEvalError("Judge approval contains an unknown fixture")
    definitions = {row["id"]: row for row in catalogue["cases"]}
    for case_id, approval in approvals.items():
        evidence_path = approval["evidence"].split("#", 1)[0]
        if evidence_path not in definitions[case_id]["references"]:
            raise AgentEvalError(
                "Judge approval evidence must cite a fixed normative reference for that fixture"
            )
    return approvals


def _artifact_content_fingerprint(root: Path) -> str:
    if root.is_symlink() or not root.is_dir():
        raise AgentEvalError("Judge fixture artifact directory is missing or unsafe")
    files: list[dict[str, Any]] = []
    try:
        for path in sorted(root.rglob("*")):
            if path.is_symlink():
                raise AgentEvalError("Judge fixture artifacts may not contain symlinks")
            if not path.is_file():
                continue
            content = path.read_bytes()
            files.append(
                {
                    "path": path.relative_to(root).as_posix(),
                    "size": len(content),
                    "sha256": sha256_bytes(content),
                }
            )
    except OSError as exc:
        raise AgentEvalError(
            "Judge fixture artifacts could not be fingerprinted"
        ) from exc
    return canonical_fingerprint(files)


def _read_evidence_object(path: Path) -> dict[str, Any] | None:
    if path.is_symlink() or not path.is_file():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _run_relative_path(run_root: Path, value: Any) -> Path | None:
    if not isinstance(value, str) or not value:
        return None
    relative = PurePosixPath(value)
    if (
        not relative.parts
        or relative.is_absolute()
        or any(part in {"", ".", ".."} for part in relative.parts)
    ):
        return None
    candidate = run_root
    for part in relative.parts:
        candidate = candidate / part
        if candidate.is_symlink():
            return None
    try:
        candidate.resolve().relative_to(run_root.resolve())
    except (OSError, ValueError):
        return None
    return candidate


def _baseline_attempt_eligibility(
    attempt: dict[str, Any], *, run_root: Path, scenario: dict[str, Any]
) -> tuple[bool, str, Path | None]:
    """Accept intact Agent output and valid needs_review incomplete routing."""
    status = attempt.get("status")
    if status not in {"pass", "needs_review"}:
        return False, "attempt_status_not_eligible", None
    if (
        attempt.get("agent_exit_code") != 0
        or attempt.get("agent_timed_out") is not False
    ):
        return False, "agent_execution_not_successful", None
    isolation = attempt.get("agent_isolation")
    if not isinstance(isolation, dict) or isolation.get("status") != "verified":
        return False, "agent_isolation_not_verified", None
    workspace = attempt.get("workspace_integrity")
    if not isinstance(workspace, dict) or workspace.get("unchanged") is not True:
        return False, "target_workspace_integrity_not_verified", None
    runtime_status = attempt.get("runtime_status")
    if not isinstance(runtime_status, dict) or any(
        runtime_status.get(key) != "pass" for key in ("verifier", "workflow_runtime")
    ):
        return False, "runtime_evidence_not_verified", None

    output = _run_relative_path(run_root, attempt.get("saved_output_root"))
    attempt_root = _run_relative_path(run_root, attempt.get("saved_result_root"))
    attempt_id = attempt.get("attempt_id")
    if (
        output is None
        or attempt_root is None
        or not output.is_dir()
        or not attempt_root.is_dir()
        or output.parent != attempt_root
        or not isinstance(attempt_id, str)
        or not attempt_id
        or attempt_root.name != attempt_id
    ):
        return False, "saved_attempt_paths_not_verified", None
    attempt_record = _read_evidence_object(attempt_root / "attempt.json")
    agent_execution = _read_evidence_object(attempt_root / "agent-execution.json")
    persisted_validation = _read_evidence_object(
        attempt_root / "artifact-validation.json"
    )
    target_integrity = _read_evidence_object(attempt_root / "target-integrity.json")
    safety_scan = _read_evidence_object(attempt_root / "output-safety-scan.json")
    runtime_checks = _read_evidence_object(attempt_root / "runtime-checks.json")
    saved_output = _read_evidence_object(attempt_root / "saved-agent-output.json")
    manifest = _read_evidence_object(output / "artifact-manifest.json")
    if (
        attempt_record is None
        or agent_execution is None
        or persisted_validation is None
        or target_integrity is None
        or safety_scan is None
        or runtime_checks is None
        or saved_output is None
        or manifest is None
    ):
        return False, "required_attempt_evidence_missing", None
    if canonical_fingerprint(attempt_record) != canonical_fingerprint(attempt):
        return False, "attempt_record_mismatch", None
    trace_path_value = attempt.get("agent_trace_path")
    trace_path = _run_relative_path(run_root, trace_path_value)
    trace_summary = (
        _read_evidence_object(trace_path) if trace_path is not None else None
    )
    final_message_path = output / "final-message.md"
    try:
        final_message = (
            final_message_path.read_bytes()
            if final_message_path.is_file() and not final_message_path.is_symlink()
            else None
        )
    except OSError:
        final_message = None
    if (
        agent_execution.get("exit_code") != 0
        or agent_execution.get("timed_out") is not False
        or agent_execution.get("container_cleanup_status")
        not in {"succeeded", "not_needed"}
        or agent_execution.get("trace_status") != "captured"
        or agent_execution.get("trace_redacted") is not False
        or final_message is None
        or agent_execution.get("final_message_sha256") != sha256_bytes(final_message)
        or attempt.get("agent_trace_status") != "captured"
        or agent_execution.get("trace_path") != trace_path_value
        or trace_summary is None
        or trace_summary.get("status") != "captured"
        or trace_summary.get("format") != "codex_exec_jsonl"
        or trace_summary.get("turn_completed") is not True
        or trace_summary.get("turn_failed") is not False
        or not isinstance(trace_summary.get("commands"), list)
    ):
        return False, "agent_trace_not_verified", None
    trace_skills = {
        skill
        for command in trace_summary["commands"]
        if isinstance(command, dict) and command.get("successful") is True
        for skill in command.get("skill_files_read", [])
        if isinstance(skill, str)
    }
    required_skills = {row["skill"] for row in scenario["required_artifacts"]}
    if not required_skills <= trace_skills:
        return False, "required_skill_use_not_verified", None
    if (
        target_integrity.get("unchanged") is not True
        or safety_scan.get("status") != "clear"
        or safety_scan.get("secret_shaped_or_unreadable_paths") != []
        or saved_output.get("status") != "saved"
        or not isinstance(saved_output.get("files"), list)
        or any(
            not isinstance(row, dict) or row.get("status") != "saved"
            for row in saved_output["files"]
        )
    ):
        return False, "target_or_output_safety_not_verified", None
    verifier_check = runtime_checks.get("verifier")
    workflow_check = runtime_checks.get("workflow_runtime")
    if (
        not isinstance(verifier_check, dict)
        or verifier_check.get("status") != "pass"
        or not isinstance(workflow_check, dict)
        or workflow_check.get("status") != "pass"
    ):
        return False, "saved_runtime_checks_not_verified", None
    manifest_files = manifest.get("files")
    schema_version = manifest.get("schema_version")
    if (
        not isinstance(schema_version, int)
        or isinstance(schema_version, bool)
        or schema_version != 1
        or not isinstance(manifest_files, list)
    ):
        return False, "saved_output_manifest_not_verified", None
    validation = validate_artifact_index(output, scenario)
    if canonical_fingerprint(validation) != canonical_fingerprint(persisted_validation):
        return False, "artifact_validation_record_mismatch", None
    artifact_rows = {row["path"]: row for row in validation["artifacts"]}
    manifest_artifact_ids = manifest.get("artifact_ids")
    if manifest_artifact_ids != sorted(
        row["artifact_id"] for row in validation["artifacts"]
    ):
        return False, "saved_output_manifest_not_verified", None
    seen_manifest_paths: set[str] = set()
    for row in manifest_files:
        if not isinstance(row, dict):
            return False, "saved_output_manifest_not_verified", None
        relative = row.get("path")
        if (
            not isinstance(relative, str)
            or relative in seen_manifest_paths
            or row.get("classification")
            not in {"qa_artifact", "runtime_evidence", "runner_internal"}
        ):
            return False, "saved_output_manifest_not_verified", None
        seen_manifest_paths.add(relative)
        path = _run_relative_path(output, relative)
        try:
            content = path.read_bytes() if path is not None and path.is_file() else None
        except OSError:
            content = None
        if (
            path is None
            or content is None
            or not isinstance(row.get("size"), int)
            or isinstance(row.get("size"), bool)
            or row["size"] != len(content)
            or not isinstance(row.get("sha256"), str)
            or row["sha256"] != sha256_bytes(content)
        ):
            return False, "saved_output_manifest_not_verified", None
        if row["classification"] == "qa_artifact":
            artifact = artifact_rows.get(relative)
            if (
                artifact is None
                or row.get("artifact_id") != artifact["artifact_id"]
                or row["sha256"] != artifact["sha256"]
                or row["size"] != artifact["size"]
            ):
                return False, "saved_output_manifest_not_verified", None
        elif row["classification"] == "runtime_evidence":
            if not relative.startswith(".runtime-evidence/"):
                return False, "saved_output_manifest_not_verified", None
        elif relative != "artifact-index.json":
            return False, "saved_output_manifest_not_verified", None
    actual_manifest_paths: set[str] = set()
    try:
        for path in output.rglob("*"):
            if path.is_symlink():
                return False, "saved_output_manifest_not_verified", None
            if path.is_file():
                relative = path.relative_to(output).as_posix()
                if relative not in {"artifact-manifest.json", "final-message.md"}:
                    actual_manifest_paths.add(relative)
    except OSError:
        return False, "saved_output_manifest_not_verified", None
    if actual_manifest_paths != seen_manifest_paths:
        return False, "saved_output_manifest_not_verified", None
    issue_kinds = {
        item.get("kind") for item in validation["issues"] if isinstance(item, dict)
    }
    if issue_kinds - {"noncompleted_routing"}:
        return False, "baseline_artifact_contract_not_satisfied", None
    if attempt.get("artifact_index_status") != validation["status"]:
        return False, "artifact_index_status_mismatch", None
    if status == "pass" and validation["status"] != "pass":
        return False, "passing_attempt_has_incomplete_artifact_index", None
    if status == "pass" and attempt.get("judge_status") not in {"pass", "not_run"}:
        return False, "passing_attempt_has_nonpassing_judge_status", None
    if status == "needs_review" and validation["status"] != "needs_review":
        return False, "needs_review_reason_not_classified", None
    if status == "needs_review" and attempt.get("judge_status") not in {
        "not_run",
        "pass",
    }:
        return False, "needs_review_has_unresolved_judge_result", None
    return (
        True,
        "passed_machine_checks_with_incomplete_routing"
        if validation["issues"]
        else "passed_machine_checks",
        output,
    )


def _select_baseline_attempt(
    run: dict[str, Any], *, run_root: Path, scenario: dict[str, Any]
) -> tuple[dict[str, Any], Path, str, list[dict[str, Any]]]:
    attempts = run.get("attempts")
    if not isinstance(attempts, list):
        raise AgentEvalError("baseline run has no attempt list")
    candidates = [
        (index, attempt)
        for index, attempt in enumerate(attempts)
        if isinstance(attempt, dict)
    ]
    eligible_attempts: list[tuple[int, dict[str, Any], Path, str]] = []
    selection: list[dict[str, Any]] = []
    eligible_ids: set[str] = set()
    eligible_roots: set[Path] = set()
    for index, attempt in candidates:
        eligible, reason, output = _baseline_attempt_eligibility(
            attempt, run_root=run_root, scenario=scenario
        )
        if eligible and output is not None:
            attempt_id = attempt.get("attempt_id")
            result_root = _run_relative_path(run_root, attempt.get("saved_result_root"))
            if (
                not isinstance(attempt_id, str)
                or not attempt_id
                or result_root is None
                or attempt_id in eligible_ids
                or result_root in eligible_roots
            ):
                raise AgentEvalError("baseline attempts are not independent")
            eligible_ids.add(attempt_id)
            eligible_roots.add(result_root)
            eligible_attempts.append((index, attempt, output, reason))
            selection.append(
                {
                    "attempt_id": attempt_id,
                    "status": attempt.get("status"),
                    "eligible": True,
                    "reason": reason,
                }
            )
        else:
            selection.append(
                {
                    "attempt_id": attempt.get("attempt_id", "unknown"),
                    "status": attempt.get("status"),
                    "eligible": False,
                    "reason": reason,
                }
            )
    if not eligible_attempts:
        summary = (
            ", ".join(
                f"{row['attempt_id']}:{row['reason']}"
                for row in selection
                if not row["eligible"]
            )
            or "no candidate attempts"
        )
        raise AgentEvalError(
            "baseline run has no eligible saved Agent attempt (" + summary + ")"
        )
    eligible_attempts.sort(key=lambda item: (item[1].get("status") != "pass", item[0]))
    _index, selected, output, reason = eligible_attempts[0]
    return selected, output, reason, selection


def _baseline_fixture_precondition(
    definition: dict[str, Any],
    *,
    prior_cases: list[dict[str, Any]],
    baseline_fingerprint: str,
) -> dict[str, Any]:
    if definition.get("mutation") == "none":
        return {"status": "not_required", "reason": "normal_fixture"}
    normal_fixture_id = (
        "normal-workflow"
        if definition.get("group") == "workflow"
        else "normal-artifacts"
    )
    normal_case = next(
        (row for row in prior_cases if row.get("case_id") == normal_fixture_id), None
    )
    if normal_case is None:
        return {
            "status": "not_evaluated",
            "reason": "normal_baseline_fixture_not_evaluated",
            "normal_fixture_id": normal_fixture_id,
        }
    binding = normal_case.get("approval_binding")
    if (
        not isinstance(binding, dict)
        or binding.get("baseline_artifact_fingerprint") != baseline_fingerprint
    ):
        return {
            "status": "review_pending",
            "reason": "normal_baseline_binding_mismatch",
            "normal_fixture_id": normal_fixture_id,
        }
    approval = normal_case.get("approval")
    if (
        normal_case.get("status") != "verified"
        or not isinstance(approval, dict)
        or approval.get("binding_status") != "matched"
        or normal_case.get("fixture_content_integrity_status") != "verified"
    ):
        return {
            "status": "review_pending",
            "reason": "normal_baseline_not_verified",
            "normal_fixture_id": normal_fixture_id,
            "normal_fixture_status": normal_case.get("status"),
        }
    if not set(definition.get("criteria", [])) <= set(normal_case.get("criteria", [])):
        return {
            "status": "review_pending",
            "reason": "normal_baseline_does_not_cover_mutation_criteria",
            "normal_fixture_id": normal_fixture_id,
        }
    return {
        "status": "verified",
        "reason": "approved_normal_baseline_passes_mutation_criteria",
        "normal_fixture_id": normal_fixture_id,
    }


def _approval_binding_status(
    approval: dict[str, Any] | None, current_binding: dict[str, Any]
) -> str:
    if approval is None:
        return "missing"
    if "binding" not in approval:
        return "legacy_unbound"
    try:
        matches = canonical_fingerprint(approval["binding"]) == canonical_fingerprint(
            current_binding
        )
    except (TypeError, ValueError):
        matches = False
    return "matched" if matches else "mismatch"


def _copy_baseline_artifacts(source: Path, destination: Path) -> None:
    if destination.exists():
        raise AgentEvalError("fixture destination already exists")
    shutil.copytree(source, destination)
    for path in destination.rglob("*"):
        if path.is_symlink():
            raise AgentEvalError("baseline artifact set contains a symlink")


def _prepare_fixture(
    *,
    definition: dict[str, Any],
    baseline_output: Path,
    fixture_root: Path,
    scenario: dict[str, Any],
) -> tuple[Path, dict[str, Any], str]:
    output = fixture_root / "qa-output"
    _copy_baseline_artifacts(baseline_output, output)
    final_path = output / "final-message.md"
    final = final_path.read_text(encoding="utf-8") if final_path.is_file() else ""
    mutation = definition["mutation"]
    if mutation == "skip-required-test-case-design-routing":
        index_path = output / "artifact-index.json"
        index = json.loads(index_path.read_text(encoding="utf-8"))
        row = next(
            (
                item
                for item in index["routing"]
                if item.get("skill") == "test-case-design"
            ),
            None,
        )
        if row is None:
            raise AgentEvalError("normal baseline has no test-case-design routing row")
        if row.get("status") == "skipped":
            raise AgentEvalError(
                "major-violation-001 mutation does not change an already skipped route"
            )
        routed_artifact_ids = row.get("artifact_ids")
        if not isinstance(routed_artifact_ids, list) or any(
            not isinstance(artifact_id, str) for artifact_id in routed_artifact_ids
        ):
            raise AgentEvalError(
                "test-case-design routing artifact_ids are invalid in the baseline"
            )
        skipped_ids = {
            artifact["artifact_id"]
            for artifact in index["artifacts"]
            if isinstance(artifact, dict)
            and artifact.get("skill") == row.get("skill")
            and artifact.get("scope") == row.get("scope")
            and artifact.get("artifact_id") in routed_artifact_ids
        }
        if not skipped_ids:
            raise AgentEvalError(
                "major-violation-001 baseline has no linked test-case artifact to remove"
            )
        row.update(
            {
                "status": "skipped",
                "reason": "No test cases are required.",
                "artifact_ids": [],
            }
        )
        index["artifacts"] = [
            item
            for item in index["artifacts"]
            if not (
                isinstance(item, dict)
                and item.get("skill") == row.get("skill")
                and item.get("scope") == row.get("scope")
                and item.get("artifact_id") in skipped_ids
            )
        ]
        index_path.write_text(
            json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    elif mutation == "claim-complete-with-required-incomplete-stage":
        index_path = output / "artifact-index.json"
        index = json.loads(index_path.read_text(encoding="utf-8"))
        row = next(
            (item for item in index["routing"] if item.get("skill") == "qa-workflow"),
            None,
        )
        if row is None:
            raise AgentEvalError("normal baseline has no qa-workflow routing row")
        row.update(
            {"status": "incomplete", "reason": "Required closure remains unverified."}
        )
        index_path.write_text(
            json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        final = "全工程は完了し、重大な未解決事項はありません。\n"
        final_path.write_text(final, encoding="utf-8")
    elif mutation in _MUTATIONS:
        index = json.loads((output / "artifact-index.json").read_text(encoding="utf-8"))
        criterion = definition["criteria"][0]
        preferred = {
            "QTS-SEM-003": {"test-requirement", "spec-analysis"},
            "QTS-SEM-004": {"test-condition-and-ci", "test-case"},
            "QTS-SEM-005": {"test-condition-and-ci", "test-case"},
            "QTS-SEM-006": {"test-case"},
            "QTS-SEM-007": {"test-case", "test-condition-and-ci"},
            "QTS-SEM-009": {"coverage-analysis"},
            "QTS-SEM-010": {"test-requirement", "test-case"},
        }[criterion]
        row = next(
            (item for item in index["artifacts"] if item.get("kind") in preferred), None
        )
        if row is None:
            raise AgentEvalError(
                f"normal baseline lacks an artifact to mutate for {criterion}"
            )
        target = output / row["path"]
        target.write_text(
            target.read_text(encoding="utf-8") + _MUTATIONS[mutation], encoding="utf-8"
        )
    validation = validate_artifact_index(output, scenario)
    manifest = build_artifact_manifest(output, validation)
    atomic_write_json(output / "artifact-manifest.json", manifest)
    return output, validation, final


def _fixture_prompt(
    *,
    definition: dict[str, Any],
    scenario: dict[str, Any],
    references: dict[str, bytes],
    output: Path,
    validation: dict[str, Any],
    final_message: str,
    machine_summary: dict[str, Any],
) -> tuple[str, list[str]]:
    from ..semantic.prompt_builder import build_judge_prompt

    criteria_by_id = {item["id"]: item for item in scenario["rubric"]}
    criteria = [criteria_by_id[item] for item in definition["criteria"]]
    task = scenario["task_text"]
    if definition["group"] == "workflow":
        routing = json.dumps(validation["routing"], ensure_ascii=False, indent=2)
        candidate = (
            _read_qa_artifacts(output, validation)
            + "\n\n## Workflow Routing / Final Response (untrusted)\n### routing[]\n```json\n"
            + routing
            + "\n```\n\n### Final response\n"
            + sanitize_diagnostic(final_message, 20_000)
        )
        task += (
            "\n\n# Fixed machine summary\n```json\n"
            + json.dumps(
                {
                    key: machine_summary.get(key)
                    for key in (
                        "workflow_runtime_can_complete",
                        "workflow_runtime_has_unclosed_issues",
                        "required_artifacts_present",
                    )
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n```"
        )
    else:
        candidate = _read_qa_artifacts(output, validation)
        actual = {
            (item["skill"], item["kind"], item["scope"])
            for item in validation["artifacts"]
        }
        missing = [
            item
            for item in scenario["required_artifacts"]
            if (item["skill"], item["kind"], item["scope"]) not in actual
        ]
        if missing:
            candidate += "\n\n" + "\n".join(
                f"## Missing required artifact: {item['skill']} / {item['kind']} ({item['scope']})"
                for item in missing
            )
    reference_parts = []
    allowed = set(definition["references"])
    for relative in scenario["reference_paths"]:
        if relative in allowed:
            reference_parts.append(
                f"# {relative}\n\n{references[relative].decode('utf-8')}"
            )
    prompt = build_judge_prompt(
        criteria=criteria,
        eval_input=task,
        reference="\n\n---\n\n".join(reference_parts),
        candidate_output=candidate,
    )
    if definition["group"] == "artifacts":
        routing_blob = json.dumps(validation["routing"], ensure_ascii=False, indent=2)
        if routing_blob and routing_blob in prompt:
            raise AgentEvalError("artifact Judge fixture prompt leaks routing rows")
    return prompt, definition["criteria"]


def prepare_subagent_judge_call(
    *,
    call_root: Path,
    call_id: str,
    case_id: str,
    prompt: str,
    criteria: list[str],
    baseline_run_id: str,
    baseline_attempt_id: str,
    evaluator_revision: str,
    target_revision: str,
) -> dict[str, Any]:
    """Persist a Judge-only prompt for a separate host-managed subagent call."""
    import re

    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,95}", call_id):
        raise AgentEvalError("Judge subagent call ID is invalid")
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,95}", case_id):
        raise AgentEvalError("Judge fixture ID is invalid")
    if not re.fullmatch(r"[0-9a-f]{40}", evaluator_revision):
        raise AgentEvalError("Evaluator revision must be a full Git SHA")
    if not all(
        isinstance(value, str) and value
        for value in (baseline_run_id, baseline_attempt_id)
    ):
        raise AgentEvalError("Judge baseline identity is incomplete")
    if target_revision != DEFAULT_TARGET_REVISION:
        raise AgentEvalError("Judge target revision is not the fixed QTS revision")
    if (
        not isinstance(criteria, list)
        or not criteria
        or any(not isinstance(item, str) or not item for item in criteria)
        or len(criteria) != len(set(criteria))
    ):
        raise AgentEvalError("Judge criteria must be unique non-empty IDs")
    fixture = next(
        (row for row in load_fixture_catalogue()["cases"] if row["id"] == case_id),
        None,
    )
    if fixture is None or fixture["criteria"] != criteria:
        raise AgentEvalError("Judge fixture criteria do not match the fixed catalogue")
    if not isinstance(prompt, str) or not prompt.strip():
        raise AgentEvalError("Judge prompt is empty")
    prompt_bytes = prompt.encode("utf-8")
    if len(prompt_bytes) > MAX_TEXT_BYTES:
        raise AgentEvalError("Judge prompt exceeds the size limit")
    if sanitize_diagnostic(prompt, MAX_TEXT_BYTES) != prompt:
        raise AgentEvalError("Judge prompt contains secret-shaped content")

    root = _validate_subagent_call_root(call_root)
    if root.exists():
        raise AgentEvalError("Judge call output must be new")
    root.mkdir(parents=True, mode=0o700)
    root.chmod(0o700)
    prompt_hash = sha256_bytes(prompt_bytes)
    request: dict[str, Any] = {
        "schema_version": 1,
        "call_id": call_id,
        "case_id": case_id,
        "baseline_run_id": baseline_run_id,
        "baseline_attempt_id": baseline_attempt_id,
        "evaluator_revision": evaluator_revision,
        "target_revision": target_revision,
        "criteria": criteria,
        "prompt_sha256": prompt_hash,
        "requested_settings": dict(SUBAGENT_JUDGE_SETTINGS),
        "execution_method": "codex_subagent",
        "effective_model_status": "unverified",
        "tool_trace_status": "unverified",
        "physical_evaluator_read_denial": "unverified",
    }
    atomic_write_text(root / "judge-prompt.md", prompt)
    atomic_write_json(root / "request.json", request)
    atomic_write_json(
        root / "call-status.json",
        {
            "schema_version": 1,
            "call_id": call_id,
            "status": "prepared",
            "request_fingerprint": canonical_fingerprint(request),
            "requested_settings": dict(SUBAGENT_JUDGE_SETTINGS),
            "effective_model_status": "unverified",
            "tool_trace_status": "unverified",
            "physical_evaluator_read_denial": "unverified",
        },
    )
    return {**request, "prompt": prompt, "call_root": str(root)}


def _validate_subagent_call_root(call_root: Path) -> Path:
    root = Path(os.path.abspath(call_root))
    try:
        relative = root.relative_to(REPO_ROOT / ".agent-eval-runs")
    except ValueError as exc:
        raise AgentEvalError(
            "Judge call output must be under .agent-eval-runs"
        ) from exc
    if not relative.parts or any(part in {".", ".."} for part in relative.parts):
        raise AgentEvalError("Judge call output path is invalid")
    current = REPO_ROOT
    for part in root.relative_to(REPO_ROOT).parts:
        current = current / part
        if current.is_symlink():
            raise AgentEvalError("Judge call output path may not contain symlinks")
    return root


def _reject_duplicate_json_fields(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON object field")
        result[key] = value
    return result


def record_subagent_judge_response(
    *,
    call_root: Path,
    raw_response: str,
    host_call_status: str,
) -> dict[str, Any]:
    """Import one host-returned Judge response without claiming runtime telemetry."""
    from ..semantic.result import normalize_judge_response

    root = _validate_subagent_call_root(call_root)
    request_path = root / "request.json"
    prompt_path = root / "judge-prompt.md"
    try:
        request = json.loads(
            read_regular_file_bytes(request_path).decode("utf-8"),
            object_pairs_hook=_reject_duplicate_json_fields,
        )
        prompt_bytes = read_regular_file_bytes(prompt_path, max_bytes=MAX_TEXT_BYTES)
    except (AgentEvalError, UnicodeError, ValueError) as exc:
        raise AgentEvalError("Judge subagent handoff is missing or invalid") from exc
    if (
        not isinstance(request, dict)
        or set(request) != _SUBAGENT_REQUEST_KEYS
        or request.get("schema_version") != 1
        or request.get("execution_method") != "codex_subagent"
        or request.get("requested_settings") != SUBAGENT_JUDGE_SETTINGS
        or request.get("prompt_sha256") != sha256_bytes(prompt_bytes)
        or request.get("call_id") != root.name
    ):
        raise AgentEvalError("Judge subagent request binding is invalid")
    if host_call_status not in {"response_received", "execution_failed", "not_started"}:
        raise AgentEvalError("Judge host-call status is invalid")
    status_path = root / "call-status.json"
    response_path = root / "response.json"
    if response_path.exists() or response_path.is_symlink():
        raise AgentEvalError("Judge subagent response already exists")
    if not status_path.exists() or status_path.is_symlink():
        raise AgentEvalError("Judge subagent prepared status is missing or unsafe")
    try:
        existing = json.loads(
            read_regular_file_bytes(status_path).decode("utf-8"),
            object_pairs_hook=_reject_duplicate_json_fields,
        )
    except (AgentEvalError, UnicodeError, ValueError) as exc:
        raise AgentEvalError("Judge subagent prepared status is invalid") from exc
    if (
        not isinstance(existing, dict)
        or existing.get("schema_version") != 1
        or existing.get("call_id") != request.get("call_id")
        or existing.get("status") != "prepared"
        or existing.get("request_fingerprint") != canonical_fingerprint(request)
    ):
        raise AgentEvalError("Judge subagent call has already been recorded")
    if (
        not isinstance(raw_response, str)
        or len(raw_response.encode("utf-8")) > MAX_TEXT_BYTES
    ):
        raise AgentEvalError("Judge response is invalid or exceeds the size limit")

    safe_response = sanitize_diagnostic(raw_response, MAX_TEXT_BYTES)
    redacted = safe_response != raw_response
    row: dict[str, Any] = {
        "schema_version": 1,
        "call_id": request["call_id"],
        "case_id": request["case_id"],
        "host_call_status": host_call_status,
        "requested_settings": dict(SUBAGENT_JUDGE_SETTINGS),
        "effective_model_status": "unverified",
        "tool_trace_status": "unverified",
        "physical_evaluator_read_denial": "unverified",
        "prompt_sha256": request["prompt_sha256"],
        "response": safe_response,
        "response_sha256": None
        if redacted or not raw_response
        else sha256_bytes(raw_response.encode("utf-8")),
        "response_redacted": redacted,
        "normalization_status": "not_run",
        "normalized": None,
    }
    if host_call_status != "response_received":
        row["status"] = "execution_error"
        row["normalization_status"] = "not_run"
    elif redacted:
        row["status"] = "evidence_unverified"
        row["normalization_status"] = "not_run"
    else:
        scenario = load_scenario()
        criteria_by_id = {item["id"]: item for item in scenario["rubric"]}
        try:
            json.loads(raw_response, object_pairs_hook=_reject_duplicate_json_fields)
            row["normalized"] = normalize_judge_response(
                raw_response,
                skill="qa-training-store",
                eval_id="qa-training-store-checkout-payment-web-v1",
                requested_criteria=request["criteria"],
                criteria_by_id=criteria_by_id,
            )
        except (ValueError, json.JSONDecodeError) as exc:
            row["status"] = "invalid_response"
            row["normalization_status"] = "invalid"
            row["normalization_error"] = sanitize_diagnostic(str(exc), 1000)
        else:
            row["status"] = "diagnostic_response_valid"
            row["normalization_status"] = "valid"
    atomic_write_json(response_path, row)
    atomic_write_json(
        status_path,
        {
            "schema_version": 1,
            "call_id": request["call_id"],
            "status": row["status"],
            "host_call_status": host_call_status,
            "requested_settings": dict(SUBAGENT_JUDGE_SETTINGS),
            "effective_model_status": "unverified",
            "tool_trace_status": "unverified",
            "physical_evaluator_read_denial": "unverified",
            "response_sha256": row["response_sha256"],
        },
    )
    return row


def _fixture_approval_binding(
    *,
    catalogue: dict[str, Any],
    definition: dict[str, Any],
    scenario: dict[str, Any],
    references: dict[str, bytes],
    baseline_artifact_fingerprint: str,
    artifact_content_fingerprint: str,
    prompt: str,
    criteria: list[str],
    normative_revision: str,
) -> dict[str, Any]:
    scenario_references = set(scenario["reference_paths"])
    if not set(definition["references"]) <= scenario_references:
        raise AgentEvalError("Judge fixture references are outside the fixed scenario")
    reference_hashes = {
        relative: sha256_bytes(references[relative])
        for relative in sorted(set(definition["references"]))
    }
    return {
        "binding_version": 1,
        "fixture_id": definition["id"],
        "dataset_revision": catalogue["dataset_revision"],
        "fixture_definition_fingerprint": canonical_fingerprint(definition),
        "baseline_artifact_fingerprint": baseline_artifact_fingerprint,
        "artifact_content_fingerprint": artifact_content_fingerprint,
        "judge_input_fingerprint": sha256_bytes(prompt.encode("utf-8")),
        "criteria": list(criteria),
        "expected": definition["expected"],
        "normative_revision": normative_revision,
        "normative_reference_fingerprints": reference_hashes,
        "normative_content_fingerprint": canonical_fingerprint(reference_hashes),
    }


def _expected_matches(definition: dict[str, Any], normalized: dict[str, Any]) -> bool:
    criteria = normalized.get("criteria") if isinstance(normalized, dict) else None
    if not isinstance(criteria, list) or not criteria:
        return False
    if definition["expected"] == "rating_at_least_3":
        return all(
            isinstance(item, dict)
            and item.get("status") == "pass"
            and isinstance(item.get("rating"), int)
            and not isinstance(item.get("rating"), bool)
            and item["rating"] >= 3
            for item in criteria
        )
    if definition["expected"] == "rating_1":
        return (
            len(criteria) == 1
            and isinstance(criteria[0], dict)
            and criteria[0].get("status") == "fail"
            and criteria[0].get("rating") == 1
            and not isinstance(criteria[0].get("rating"), bool)
        )
    raise AgentEvalError("unknown Judge fixture expectation")


def _run_judge_case(
    *,
    command_argv: list[str],
    judge_profile: dict[str, Any],
    prompt: str,
    cwd: Path,
    timeout: int,
    run_tag: str,
    criteria: list[str],
    scenario: dict[str, Any],
) -> dict[str, Any]:
    from ..semantic.result import normalize_judge_response

    observations_path = cwd / "launcher-observations.json"
    codex_judge = is_codex_judge(judge_profile)
    if command_argv == ["codex"]:
        isolation = verify_judge_wsl2_command(command_argv, evaluator_root=REPO_ROOT)
        codex_judge = True
        execution_command = judge_launcher_argv_for_profile(
            judge_profile, observations_path=observations_path
        )
        cleanup = codex_cleanup_argv(execution_command)
    else:
        isolation = verify_judge_docker_command(command_argv, evaluator_root=REPO_ROOT)
        named, cleanup = named_container_command(
            command_argv, name="agent-eval-judge-validation-" + run_tag
        )
        execution_command = (
            legacy_judge_launcher_argv_for_profile(
                judge_profile,
                docker_argv=named,
                observations_path=observations_path,
            )
            if codex_judge
            else named
        )
    execution = run_command(
        execution_command,
        input_text=prompt,
        cwd=cwd,
        timeout_seconds=timeout,
        timeout_cleanup_argv=cleanup,
    )
    judge_capture = capture_codex_judge_output(
        execution.stdout,
        observations_path=observations_path if codex_judge else None,
    )
    safe = judge_capture["response"]
    row: dict[str, Any] = {
        "prompt_sha256": sha256_bytes(prompt.encode("utf-8")),
        "response_sha256": None
        if judge_capture["redacted"]
        else sha256_bytes(safe.encode("utf-8")),
        "exit_code": execution.exit_code,
        "timed_out": execution.timed_out,
        "duration_seconds": execution.duration_seconds,
        "container_cleanup_status": execution.cleanup_status,
        "isolation": isolation,
        "evidence_status": "captured"
        if safe == execution.stdout
        and judge_capture["status"] in {"unwrapped", "completed"}
        and not judge_capture["redacted"]
        else "evidence_unverified",
        "response": safe,
        "launcher_observations": judge_capture["launcher_observations"],
    }
    if (
        execution.exit_code != 0
        or execution.timed_out
        or execution.cleanup_status == "failed"
    ):
        row["status"] = "execution_error"
        return row
    if row["evidence_status"] != "captured":
        row["status"] = "evidence_unverified"
        return row
    criteria_by_id = {item["id"]: item for item in scenario["rubric"]}
    try:
        row["normalized"] = normalize_judge_response(
            safe,
            skill="qa-training-store",
            eval_id="qa-training-store-checkout-payment-web-v1",
            requested_criteria=criteria,
            criteria_by_id=criteria_by_id,
        )
    except ValueError as exc:
        row["status"] = "invalid_response"
        row["reason"] = sanitize_diagnostic(str(exc), 1000)
        return row
    row["status"] = (
        "pass" if row["evidence_status"] == "captured" else "evidence_unverified"
    )
    return row


def run_validation(
    *,
    baseline_result: Path,
    target_root: Path,
    profile_path: Path,
    output_root: Path,
    approval_path: Path | None,
    proposal_command: list[str] | None,
    candidate_judge_command: list[str] | None,
    max_cases: int,
    max_seconds: int,
    repeat: int,
) -> dict[str, Any]:
    from .compare import _load_result

    catalogue = load_fixture_catalogue()
    approvals = _approval_map(approval_path, catalogue)
    run, run_root = _load_result(baseline_result)
    if run.get("profile_verification") != "verified":
        raise AgentEvalError("Judge validation requires a run with verified isolation")
    profile = load_execution_profile(profile_path)
    baseline_agent_command = run.get("agent_command_template")
    if (
        run.get("execution_profile_fingerprint") != profile_fingerprint(profile)
        or not isinstance(baseline_agent_command, list)
        or any(not isinstance(item, str) for item in baseline_agent_command)
        or not verify_profile_evidence(
            profile, run_root, agent_command_argv=baseline_agent_command
        )
    ):
        raise AgentEvalError(
            "Judge validation requires matching verified baseline profile evidence"
        )
    if profile.get("schema_version", 1) == 2:
        if candidate_judge_command is not None and candidate_judge_command != ["codex"]:
            raise AgentEvalError(
                "schema 2 candidate Judge must use the fixed codex command template"
            )
        if proposal_command is not None and proposal_command != ["codex"]:
            raise AgentEvalError(
                "schema 2 proposal Agent must use the fixed codex command template"
            )
    output_root = Path(os.path.abspath(output_root))
    prepare_run_output_root(
        output_root,
        repository_root=REPO_ROOT,
        evidence_relative_path=profile["verification"]["evidence_path"],
    )
    run_root = run_root.resolve()
    if output_root == run_root or output_root.is_relative_to(run_root):
        raise AgentEvalError("Judge validation output may not modify the baseline run")
    if not verify_profile_evidence(
        profile, output_root, judge_command_argv=profile["judge"]["command_argv"]
    ):
        raise AgentEvalError("Judge validation requires verified isolation evidence")
    target_source_sha = assert_clean_checkout(target_root)
    fixed_target_sha = resolve_commit(target_root, DEFAULT_TARGET_REVISION)
    if fixed_target_sha != DEFAULT_TARGET_REVISION:
        raise AgentEvalError("fixed qa-training-store source revision is unavailable")
    scenario = load_scenario()
    references = extract_revision_files(
        source_root=target_root,
        revision=fixed_target_sha,
        paths=scenario["reference_paths"],
    )
    (
        baseline_attempt,
        baseline_output,
        baseline_eligibility,
        baseline_attempt_selection,
    ) = _select_baseline_attempt(run, run_root=run_root, scenario=scenario)
    baseline_artifact_fingerprint = _artifact_content_fingerprint(baseline_output)
    if run.get("scenario_fingerprint") != scenario["scenario_fingerprint"]:
        raise AgentEvalError("baseline uses a different fixed scenario revision")
    if (
        run.get("target_revision") != fixed_target_sha
        or len(run.get("attempts", [])) < 2
    ):
        raise AgentEvalError(
            "Judge validation requires the fixed target and at least two baseline attempts"
        )
    start = time.monotonic()
    result: dict[str, Any] = {
        "schema_version": 1,
        "status": "running",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "dataset_revision": catalogue["dataset_revision"],
        "fixture_catalogue_fingerprint": canonical_fingerprint(catalogue),
        "evaluator_revision": run.get("evaluator_revision"),
        "target_revision": fixed_target_sha,
        "target_source_checkout_revision": target_source_sha,
        "baseline_result": str(baseline_result),
        "baseline_execution_profile_fingerprint": run.get(
            "execution_profile_fingerprint"
        ),
        "baseline_agent_command_fingerprint": canonical_fingerprint(
            baseline_agent_command
        ),
        "baseline_attempt_id": baseline_attempt.get("attempt_id"),
        "baseline_attempt_status": baseline_attempt.get("status"),
        "baseline_attempt_eligibility": baseline_eligibility,
        "baseline_attempt_selection": baseline_attempt_selection,
        "judge_profile_fingerprint": profile_fingerprint(profile),
        "repeat": repeat,
        "cases": [],
        "proposals": [],
        "candidate_judge_validation_status": "not_run"
        if candidate_judge_command is None
        else "running",
        "limits": {"max_cases": max_cases, "max_seconds": max_seconds},
    }
    atomic_write_json(output_root / "result.json", result)
    definitions = catalogue["cases"][:max_cases]
    result["unprocessed_case_ids"] = [
        row["id"] for row in catalogue["cases"][max_cases:]
    ]
    for number, definition in enumerate(definitions, start=1):
        if time.monotonic() - start >= max_seconds:
            result["stopped_reason"] = "time_budget_exhausted"
            break
        case_root = output_root / "fixtures" / definition["id"]
        case_root.mkdir(parents=True, exist_ok=False)
        fixture_output, validation, final_message = _prepare_fixture(
            definition=definition,
            baseline_output=baseline_output,
            fixture_root=case_root,
            scenario=scenario,
        )
        attempt_root = run_root / baseline_attempt["saved_result_root"]
        machine: dict[str, Any] = {
            "required_artifacts_present": validation["status"] == "pass"
        }
        try:
            runtime = json.loads(
                (attempt_root / "runtime-checks.json").read_text(encoding="utf-8")
            )
            workflow = runtime.get("workflow_runtime", {})
            machine["workflow_runtime_can_complete"] = workflow.get(
                "workflow_runtime_can_complete"
            )
            machine["workflow_runtime_has_unclosed_issues"] = workflow.get(
                "workflow_runtime_has_unclosed_issues"
            )
        except (OSError, json.JSONDecodeError):
            machine.update(
                {
                    "workflow_runtime_can_complete": None,
                    "workflow_runtime_has_unclosed_issues": None,
                }
            )
        prompt, criteria = _fixture_prompt(
            definition=definition,
            scenario=scenario,
            references=references,
            output=fixture_output,
            validation=validation,
            final_message=final_message,
            machine_summary=machine,
        )
        artifact_content_fingerprint = _artifact_content_fingerprint(fixture_output)
        approval_binding = _fixture_approval_binding(
            catalogue=catalogue,
            definition=definition,
            scenario=scenario,
            references=references,
            baseline_artifact_fingerprint=baseline_artifact_fingerprint,
            artifact_content_fingerprint=artifact_content_fingerprint,
            prompt=prompt,
            criteria=criteria,
            normative_revision=fixed_target_sha,
        )
        saved_approval = approvals.get(definition["id"])
        binding_status = _approval_binding_status(saved_approval, approval_binding)
        approval_record = dict(saved_approval) if saved_approval is not None else {}
        approval_record.update(
            {
                "status": "approved"
                if binding_status == "matched"
                else definition["approval_status"]
                if saved_approval is None
                else "review_pending",
                "binding_status": binding_status,
            }
        )
        fixture_record: dict[str, Any] = {
            "case_id": definition["id"],
            "split": "tune"
            if definition["id"] in catalogue["splits"]["tune"]
            else "independent",
            "criteria": criteria,
            "expected": definition["expected"],
            "approval": approval_record,
            "approval_binding": approval_binding,
            "fixture_fingerprint": canonical_fingerprint(approval_binding),
            "fixture_content_integrity_status": "verified",
            "judge_runs": [],
        }
        baseline_precondition = _baseline_fixture_precondition(
            definition,
            prior_cases=result["cases"],
            baseline_fingerprint=baseline_artifact_fingerprint,
        )
        fixture_record["baseline_precondition"] = baseline_precondition
        for repeat_index in range(1, repeat + 1):
            if time.monotonic() - start >= max_seconds:
                fixture_record["status"] = "review_pending"
                fixture_record["stop_reason"] = "time_budget_exhausted"
                break
            cwd = case_root / f"judge-{repeat_index:02d}"
            cwd.mkdir()
            remaining_seconds = max(1, int(max_seconds - (time.monotonic() - start)))
            baseline_judge = _run_judge_case(
                command_argv=profile["judge"]["command_argv"],
                judge_profile=profile["judge"],
                prompt=prompt,
                cwd=cwd,
                timeout=min(profile["judge"]["timeout_seconds"], remaining_seconds),
                run_tag=f"{number:02d}-{repeat_index:02d}",
                criteria=criteria,
                scenario=scenario,
            )
            observed = None
            if baseline_judge.get("normalized"):
                observed = _expected_matches(definition, baseline_judge["normalized"])
            baseline_judge["expectation_matched"] = observed
            fixture_record["judge_runs"].append(baseline_judge)
            if candidate_judge_command:
                candidate_cwd = case_root / f"candidate-judge-{repeat_index:02d}"
                candidate_cwd.mkdir()
                candidate_command_result = _run_judge_case(
                    command_argv=candidate_judge_command,
                    judge_profile=profile["judge"],
                    prompt=prompt,
                    cwd=candidate_cwd,
                    timeout=min(
                        profile["judge"]["timeout_seconds"],
                        max(1, int(max_seconds - (time.monotonic() - start))),
                    ),
                    run_tag=f"candidate-{number:02d}-{repeat_index:02d}",
                    criteria=criteria,
                    scenario=scenario,
                )
                candidate_observed = None
                if candidate_command_result.get("normalized"):
                    candidate_observed = _expected_matches(
                        definition, candidate_command_result["normalized"]
                    )
                candidate_command_result["expectation_matched"] = candidate_observed
                fixture_record.setdefault("candidate_judge_runs", []).append(
                    candidate_command_result
                )
        run_states = [row.get("status") for row in fixture_record["judge_runs"]]
        matched = [
            row.get("expectation_matched") for row in fixture_record["judge_runs"]
        ]
        ratings = {
            json.dumps(
                [
                    (item.get("id"), item.get("status"), item.get("rating"))
                    for item in row.get("normalized", {}).get("criteria", [])
                ],
                sort_keys=True,
            )
            for row in fixture_record["judge_runs"]
        }
        inconsistent = len(ratings) > 1
        try:
            fixture_record["fixture_content_integrity_status"] = (
                "verified"
                if _artifact_content_fingerprint(fixture_output)
                == artifact_content_fingerprint
                else "mismatch"
            )
        except AgentEvalError:
            fixture_record["fixture_content_integrity_status"] = "unverified"
        approved = (
            binding_status == "matched"
            and fixture_record["fixture_content_integrity_status"] == "verified"
            and baseline_precondition["status"] in {"not_required", "verified"}
        )
        if candidate_judge_command is not None:
            candidate_runs = fixture_record.get("candidate_judge_runs", [])
            candidate_states = [row.get("status") for row in candidate_runs]
            candidate_matched = [
                row.get("expectation_matched") for row in candidate_runs
            ]
            candidate_ratings = {
                json.dumps(
                    [
                        (item.get("id"), item.get("status"), item.get("rating"))
                        for item in row.get("normalized", {}).get("criteria", [])
                    ],
                    sort_keys=True,
                )
                for row in candidate_runs
            }
            candidate_inconsistent = len(candidate_ratings) > 1
            if any(state == "execution_error" for state in candidate_states):
                fixture_record["candidate_judge_status"] = "execution_error"
            elif any(state != "pass" for state in candidate_states):
                fixture_record["candidate_judge_status"] = "review_pending"
            elif (
                approved
                and len(candidate_matched) == repeat
                and all(value is True for value in candidate_matched)
                and not candidate_inconsistent
            ):
                fixture_record["candidate_judge_status"] = "verified"
            elif approved and any(value is False for value in candidate_matched):
                fixture_record["candidate_judge_status"] = "label_or_judge_mismatch"
            else:
                fixture_record["candidate_judge_status"] = "review_pending"
            fixture_record["candidate_judge_stable"] = not candidate_inconsistent
            fixture_record["candidate_judge_matches_approved_labels"] = len(
                candidate_matched
            ) == repeat and all(value is True for value in candidate_matched)
            fixture_record["candidate_matches_baseline"] = (
                candidate_ratings == ratings
                if len(candidate_runs) == repeat
                and len(candidate_ratings) == 1
                and len(ratings) == 1
                else None
            )
        if any(state == "execution_error" for state in run_states):
            fixture_record["status"] = "execution_error"
        elif any(state != "pass" for state in run_states):
            fixture_record["status"] = "review_pending"
        elif (
            approved
            and len(matched) == repeat
            and all(value is True for value in matched)
            and not inconsistent
        ):
            fixture_record["status"] = "verified"
        elif approved and any(value is False for value in matched):
            fixture_record["status"] = "label_or_judge_mismatch"
        else:
            fixture_record["status"] = "review_pending"
        result["cases"].append(fixture_record)
        atomic_write_json(output_root / "result.json", result)

    if proposal_command:
        tune_results = [row for row in result["cases"] if row["split"] == "tune"]
        proposal_prompt = (
            """Judge tuning proposal only. Do not change fixed rubric, References, or expected labels. Return proposed prompt guidance and rationale as JSON. Independent validation cases and labels are not included.\n\n"""
            + json.dumps(
                [
                    {
                        "case_id": row["case_id"],
                        "criteria": row["criteria"],
                        "observed_ratings": [
                            {
                                "criteria": [
                                    {
                                        key: item.get(key)
                                        for key in (
                                            "id",
                                            "status",
                                            "rating",
                                            "reason",
                                            "evidence",
                                        )
                                    }
                                    for item in judge_run.get("normalized", {}).get(
                                        "criteria", []
                                    )
                                ]
                            }
                            for judge_run in row["judge_runs"]
                        ],
                    }
                    for row in tune_results
                ],
                ensure_ascii=False,
            )
        )
        if profile.get("schema_version", 1) == 2 and proposal_command == ["codex"]:
            cwd = output_root / "proposal-agent"
            cwd.mkdir()
            proposal_output = cwd / ".qa-eval-output"
            proposal_output.mkdir()
            isolation = verify_agent_wsl2_command(
                proposal_command,
                workspace=cwd,
                output_root=proposal_output,
                evaluator_root=REPO_ROOT,
            )
            proposal_execution_command = launcher_argv(
                mode="agent",
                output_root=proposal_output,
                observations_path=cwd / "launcher-observations.json",
                model=profile["agent"]["model"],
                reasoning_effort=profile["agent"]["reasoning_effort"],
                sandbox_policy=profile["agent"]["sandbox_policy"],
                workspace_root=cwd,
                cli_version=profile["agent"]["cli_version"],
                docker_argv=proposal_command,
            )
            cleanup = codex_cleanup_argv(proposal_execution_command)
        elif proposal_command[0] == "docker":
            isolation = verify_judge_docker_command(
                proposal_command, evaluator_root=REPO_ROOT
            )
            named, cleanup = named_container_command(
                proposal_command,
                name="agent-eval-judge-proposal-" + os.urandom(4).hex(),
            )
            proposal_execution_command = named
        else:
            raise AgentEvalError("Judge proposal Agent must use the verified launcher")
        proposal_timeout = min(
            profile["agent"]["timeout_seconds"],
            max(1, int(max_seconds - (time.monotonic() - start))),
        )
        proposal = run_command(
            proposal_execution_command,
            input_text=proposal_prompt,
            cwd=cwd,
            timeout_seconds=proposal_timeout,
            timeout_cleanup_argv=cleanup,
        )
        safe = sanitize_diagnostic(proposal.stdout)
        proposal_record = {
            "status": "saved_for_review"
            if not proposal.timed_out and proposal.exit_code == 0
            else "execution_error",
            "response": safe,
            "response_sha256": sha256_bytes(proposal.stdout.encode("utf-8")),
            "prompt_sha256": sha256_bytes(proposal_prompt.encode("utf-8")),
            "isolation": isolation,
            "container_cleanup_status": proposal.cleanup_status,
        }
        result["proposals"].append(proposal_record)
        atomic_write_json(
            output_root / "proposals" / "judge-improvement-candidate.json",
            proposal_record,
        )

    case_states = [row["status"] for row in result["cases"]]
    result["status"] = (
        "verified"
        if case_states and all(state == "verified" for state in case_states)
        else "review_pending"
    )
    if candidate_judge_command is not None:
        candidate_states = [
            row.get("candidate_judge_status") for row in result["cases"]
        ]
        result["candidate_judge_validation_status"] = (
            "verified"
            if candidate_states
            and all(state == "verified" for state in candidate_states)
            else "review_pending"
        )
    result["finished_at"] = datetime.now(timezone.utc).isoformat()
    result["elapsed_seconds"] = round(time.monotonic() - start, 3)
    atomic_write_json(output_root / "result.json", result)
    return result


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if arguments and arguments[0] in {
        "prepare-subagent-call",
        "record-subagent-response",
    }:
        subagent_parser = argparse.ArgumentParser(
            description="Prepare or import a host-managed Codex Judge subagent call."
        )
        subcommands = subagent_parser.add_subparsers(dest="subcommand", required=True)
        prepare = subcommands.add_parser("prepare-subagent-call")
        prepare.add_argument("--call-root", type=Path, required=True)
        prepare.add_argument("--call-id", required=True)
        prepare.add_argument("--case-id", required=True)
        prepare.add_argument("--prompt-file", type=Path, required=True)
        prepare.add_argument("--criterion", action="append", required=True)
        prepare.add_argument("--baseline-run-id", required=True)
        prepare.add_argument("--baseline-attempt-id", required=True)
        prepare.add_argument("--evaluator-revision", required=True)
        prepare.add_argument("--target-revision", required=True)
        record = subcommands.add_parser("record-subagent-response")
        record.add_argument("--call-root", type=Path, required=True)
        record.add_argument(
            "--host-call-status",
            choices=("response_received", "execution_failed", "not_started"),
            required=True,
        )
        args = subagent_parser.parse_args(arguments)
        try:
            if args.subcommand == "prepare-subagent-call":
                prompt = read_regular_file_bytes(
                    args.prompt_file, max_bytes=MAX_TEXT_BYTES
                ).decode("utf-8")
                request = prepare_subagent_judge_call(
                    call_root=args.call_root,
                    call_id=args.call_id,
                    case_id=args.case_id,
                    prompt=prompt,
                    criteria=args.criterion,
                    baseline_run_id=args.baseline_run_id,
                    baseline_attempt_id=args.baseline_attempt_id,
                    evaluator_revision=args.evaluator_revision,
                    target_revision=args.target_revision,
                )
                print(
                    json.dumps(
                        {
                            "call_root": request["call_root"],
                            "call_id": request["call_id"],
                            "prompt_sha256": request["prompt_sha256"],
                            "status": "prepared",
                        },
                        ensure_ascii=True,
                    )
                )
                return 0
            response = sys.stdin.read(MAX_TEXT_BYTES + 1)
            if len(response.encode("utf-8")) > MAX_TEXT_BYTES:
                raise AgentEvalError("Judge response exceeds the size limit")
            recorded = record_subagent_judge_response(
                call_root=args.call_root,
                raw_response=response,
                host_call_status=args.host_call_status,
            )
            print(
                json.dumps(
                    {
                        "call_id": recorded["call_id"],
                        "status": recorded["status"],
                        "normalization_status": recorded["normalization_status"],
                        "response_sha256": recorded["response_sha256"],
                        "effective_model_status": recorded["effective_model_status"],
                        "tool_trace_status": recorded["tool_trace_status"],
                    },
                    ensure_ascii=True,
                )
            )
            return 0 if recorded["status"] == "diagnostic_response_valid" else 1
        except (AgentEvalError, OSError, UnicodeError, ValueError) as exc:
            print(
                f"Judge subagent import error: {sanitize_diagnostic(str(exc), 1000)}",
                file=sys.stderr,
            )
            return 2

    parser = argparse.ArgumentParser(
        description="Independently validate and propose improvements to the fixed QTS Judge."
    )
    parser.add_argument("--baseline-result", type=Path, required=True)
    parser.add_argument("--target-root", type=Path, required=True)
    parser.add_argument("--execution-profile", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--approval-file", type=Path)
    parser.add_argument(
        "--proposal-command",
        nargs="+",
        help="Optional isolated Agent command for tuning-only proposals",
    )
    parser.add_argument(
        "--candidate-judge-command",
        nargs="+",
        help="Optional candidate Judge command; never auto-adopted",
    )
    parser.add_argument("--max-cases", type=int, required=True)
    parser.add_argument("--max-seconds", type=int, required=True)
    parser.add_argument("--repeat", type=int, default=2)
    args = parser.parse_args(arguments)
    if args.max_cases <= 0 or args.max_seconds <= 0 or not 1 <= args.repeat <= 10:
        parser.error("max-cases, max-seconds, and repeat must be positive and bounded")
    if args.max_cases > 30 or args.max_seconds > 3600:
        parser.error("requested Judge validation exceeds the fixed safety cap")
    try:
        result = run_validation(
            baseline_result=args.baseline_result,
            target_root=args.target_root,
            profile_path=args.execution_profile,
            output_root=Path(os.path.abspath(args.output_root)),
            approval_path=args.approval_file,
            proposal_command=args.proposal_command,
            candidate_judge_command=args.candidate_judge_command,
            max_cases=args.max_cases,
            max_seconds=args.max_seconds,
            repeat=args.repeat,
        )
    except (AgentEvalError, OSError, ValueError, KeyError) as exc:
        print(
            f"Judge validation error: {sanitize_diagnostic(str(exc), 2000)}",
            file=sys.stderr,
        )
        return 2
    print(
        json.dumps(
            {
                "result": str(args.output_root / "result.json"),
                "status": result["status"],
            },
            ensure_ascii=True,
        )
    )
    return 0 if result["status"] == "verified" else 1


if __name__ == "__main__":
    raise SystemExit(main())
