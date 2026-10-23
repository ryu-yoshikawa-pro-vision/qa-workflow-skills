from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .common import (
    AgentEvalError,
    atomic_write_json,
    canonical_fingerprint,
    capture_codex_judge_output,
    prepare_run_output_root,
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
    launcher_argv_for_profile as judge_launcher_argv_for_profile,
)
from .workspace import (
    assert_clean_checkout,
    load_execution_profile,
    named_container_command,
    profile_fingerprint,
    resolve_commit,
    verify_judge_docker_command,
    verify_profile_evidence,
)

REPO_ROOT = Path(__file__).resolve().parents[4]
FIXTURE_DEFS = SCENARIO_DIR / "judge-fixtures.json"
_MUTATIONS = {
    "promote-unresolved-specification-to-confirmed-oracle": "\n\n## Confirmed expected behavior\nThe unresolved specification is now treated as final authority: checkout must succeed and create an Order after the cart version becomes stale.\n",
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
        skipped_ids = set(row.get("artifact_ids", []))
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
            if item.get("artifact_id") not in skipped_ids
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

    isolation = verify_judge_docker_command(command_argv, evaluator_root=REPO_ROOT)
    named, cleanup = named_container_command(
        command_argv, name="agent-eval-judge-validation-" + run_tag
    )
    observations_path = cwd / "launcher-observations.json"
    codex_judge = is_codex_judge(judge_profile)
    execution_command = (
        judge_launcher_argv_for_profile(
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
        "response_sha256": sha256_bytes(safe.encode("utf-8")),
        "exit_code": execution.exit_code,
        "timed_out": execution.timed_out,
        "duration_seconds": execution.duration_seconds,
        "container_cleanup_status": execution.cleanup_status,
        "isolation": isolation,
        "evidence_status": "captured"
        if safe == execution.stdout
        and judge_capture["status"] in {"unwrapped", "completed"}
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
    baseline_attempt = next(
        (
            row
            for row in run["attempts"]
            if row.get("status") in {"pass", "fail", "needs_review"}
        ),
        None,
    )
    if baseline_attempt is None:
        raise AgentEvalError("baseline run has no saved Agent attempt")
    baseline_output = (run_root / baseline_attempt["saved_output_root"]).resolve()
    try:
        baseline_output.relative_to(run_root.resolve())
    except ValueError as exc:
        raise AgentEvalError("baseline output path escapes the run root") from exc
    if not baseline_output.is_dir():
        raise AgentEvalError("baseline QA artifacts were not preserved")
    profile = load_execution_profile(profile_path)
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
        if proposal_command[0] == "docker":
            isolation = verify_judge_docker_command(
                proposal_command, evaluator_root=REPO_ROOT
            )
        else:
            raise AgentEvalError("Judge proposal Agent must use isolated docker run")
        cwd = output_root / "proposal-agent"
        cwd.mkdir()
        named, cleanup = named_container_command(
            proposal_command, name="agent-eval-judge-proposal-" + os.urandom(4).hex()
        )
        proposal_timeout = min(
            profile["agent"]["timeout_seconds"],
            max(1, int(max_seconds - (time.monotonic() - start))),
        )
        proposal = run_command(
            named,
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
    args = parser.parse_args(argv)
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
