"""Non-E2E result reconciliation; no runner or storage authority is implied.

The source reporter is immutable input. The output is a derived, non-authoritative
projection. Callers must retain the raw reporter and proof of its provenance.
"""

from __future__ import annotations

from collections import Counter
from pathlib import PurePosixPath, PureWindowsPath
from typing import Any


class ContractError(ValueError):
    """The requested reconciliation is unsafe or structurally ambiguous."""


def _required_str(value: Any, name: str) -> str:
    if (
        not isinstance(value, str)
        or not value.strip()
        or any(ord(c) < 32 for c in value)
    ):
        raise ContractError(f"invalid_{name}")
    return value


def _relative(path: Any) -> str:
    value = _required_str(path, "path").replace("\\", "/")
    parsed = PurePosixPath(value)
    if (
        parsed.is_absolute()
        or ":" in value.split("/")[0]
        or any(part in {".", ".."} for part in value.split("/"))
    ):
        raise ContractError("non_relative_test_path")
    return value


def classify_owner(
    *, activity: str, tool: str, browser: bool = False, persistent: bool = False
) -> str:
    """Classification uses requested activity, not a runner brand alone."""
    if activity == "meaning_review":
        return "adversarial-review"
    if activity == "static_tool":
        return "testware-execution"
    if activity == "direct_tc":
        return "test-execution" if browser else "testware-execution"
    if activity == "implement":
        return "e2e-test-implementation" if browser else "testware-implementation"
    if activity == "run":
        if tool == "playwright" and browser:
            return "e2e-test-execution" if persistent else "test-execution"
        if browser:
            raise ContractError("browser_runner_unclassified")
        return "testware-execution"
    raise ContractError("unknown_activity")


def preflight(request: dict[str, Any]) -> dict[str, Any]:
    """Fail closed when evidence needed to *start* an operation is absent.

    This does not authenticate approvals or guarantee script safety; the caller
    must independently inspect the actual script chain and provider readback.
    """
    required = (
        "source_ref",
        "source_revision",
        "build_revision",
        "environment_ref",
        "operation_ref",
        "runner_ref",
    )
    missing = [
        key
        for key in required
        if not isinstance(request.get(key), str) or not request[key].strip()
    ]
    if missing:
        return {
            "may_start": False,
            "reason": "missing_run_identity",
            "missing": missing,
        }
    if request.get("script_chain_reviewed") is not True:
        return {"may_start": False, "reason": "script_chain_unverified"}
    if request.get("permissions_verified") is not True:
        return {"may_start": False, "reason": "permissions_unverified"}
    side_effects = request.get("side_effects")
    if not isinstance(side_effects, list):
        return {"may_start": False, "reason": "side_effect_scope_unverified"}
    for effect in side_effects:
        if (
            not isinstance(effect, dict)
            or not isinstance(effect.get("scope"), str)
            or not effect["scope"]
        ):
            return {"may_start": False, "reason": "invalid_side_effect_scope"}
        if type(effect.get("max_count")) is not int or effect["max_count"] < 1:
            return {"may_start": False, "reason": "invalid_side_effect_limit"}
        if not effect.get("cleanup_ref"):
            return {"may_start": False, "reason": "cleanup_unverified"}
    if request.get("shared_resource") is True:
        # An asserted reservation is not an authenticated native provider readback.
        return {"may_start": False, "reason": "shared_reservation_provider_required"}
    if request.get("isolated_environment") is not True:
        return {"may_start": False, "reason": "isolation_unverified"}
    if request.get("external_side_effects") is True and not request.get("approval_ref"):
        return {"may_start": False, "reason": "external_approval_required"}
    return {
        "may_start": True,
        "reason": "local_preflight_only",
        "requires_runtime_recheck": True,
    }


def _test_key(path: Any, title_path: Any) -> tuple[str, tuple[str, ...]]:
    path = _relative(path)
    if not isinstance(title_path, list) or not title_path:
        raise ContractError("invalid_title_path")
    return path, tuple(_required_str(x, "title") for x in title_path)


def _report_path(value: Any, repo_root: str | None) -> str:
    """Normalize reporter paths only within a verified absolute repo root."""
    candidate = _required_str(value, "report_path").replace("\\", "/")
    if candidate.startswith("/") or PureWindowsPath(candidate).is_absolute():
        if not repo_root:
            raise ContractError("reporter_root_required")
        root = _required_str(repo_root, "repo_root").replace("\\", "/").rstrip("/")
        if not (root.startswith("/") or PureWindowsPath(root).is_absolute()):
            raise ContractError("invalid_reporter_root")
        windows = bool(PureWindowsPath(root).drive)
        actual_parts = candidate.split("/")
        root_parts = root.split("/")
        if windows:
            compare_actual = [part.casefold() for part in actual_parts]
            compare_root = [part.casefold() for part in root_parts]
        else:
            compare_actual, compare_root = actual_parts, root_parts
        if (
            len(actual_parts) <= len(root_parts)
            or compare_actual[: len(root_parts)] != compare_root
        ):
            raise ContractError("reporter_path_outside_root")
        candidate = "/".join(actual_parts[len(root_parts) :])
    return _relative(candidate)


def reconcile_vitest(
    *,
    selected: list[dict[str, Any]],
    report: dict[str, Any],
    source_revision: str,
    raw_ref: str,
    selection_verified: bool = False,
    repo_root: str | None = None,
) -> dict[str, Any]:
    """Compare an exact selected test population to Vitest JSON reporter output.

    This does not attest to the actual run, retry history, or a TC PASS.
    """
    _required_str(source_revision, "source_revision")
    _required_str(raw_ref, "raw_ref")
    if not isinstance(selected, list) or not selected:
        raise ContractError("empty_selected_test_set")
    if not isinstance(report, dict) or not isinstance(report.get("testResults"), list):
        raise ContractError("invalid_vitest_report")
    wanted = Counter(_test_key(t.get("path"), t.get("title_path")) for t in selected)
    raw: list[dict[str, Any]] = []
    failed_suites_without_tests: list[str] = []
    for file in report["testResults"]:
        if not isinstance(file, dict) or not isinstance(
            file.get("assertionResults"), list
        ):
            raise ContractError("invalid_report_file")
        path = _report_path(file.get("name"), repo_root)
        if file.get("status") == "failed" and not file["assertionResults"]:
            failed_suites_without_tests.append(path)
        for case in file["assertionResults"]:
            if not isinstance(case, dict) or not isinstance(
                case.get("ancestorTitles"), list
            ):
                raise ContractError("invalid_report_assertion")
            key = _test_key(path, [*case["ancestorTitles"], case.get("title")])
            status = case.get("status")
            if status not in {"passed", "failed", "pending", "todo", "disabled"}:
                raise ContractError("unknown_vitest_status")
            raw.append({"key": key, "raw_status": status})
    seen = Counter(r["key"] for r in raw)
    statuses = Counter(r["raw_status"] for r in raw)
    counters = {
        "numTotalTests": len(raw),
        "numPassedTests": statuses["passed"],
        "numFailedTests": statuses["failed"],
        "numPendingTests": statuses["pending"] + statuses["disabled"],
        "numTodoTests": statuses["todo"],
    }
    reporter_consistent = all(
        key not in report or (type(report[key]) is int and report[key] == val)
        for key, val in counters.items()
    )
    if report.get("success") is True and statuses["failed"]:
        reporter_consistent = False
    if "success" in report and type(report["success"]) is not bool:
        reporter_consistent = False
    results = []
    for (path, titles), count in wanted.items():
        matches = [r for r in raw if r["key"] == (path, titles)]
        if count > 1 or len(matches) > 1:
            status = "ambiguous"
        elif not matches:
            status = "not_collected"
        else:
            status = matches[0]["raw_status"]
        results.append(
            {
                "path": path,
                "title_path": list(titles),
                "expected_instances": count,
                "collected_instances": len(matches),
                "runner_status": status,
                "tc_verdict": None,
            }
        )
    unplanned = [
        {"path": path, "title_path": list(titles), "count": count}
        for (path, titles), count in seen.items()
        if (path, titles) not in wanted
    ]
    complete = (
        selection_verified is True
        and reporter_consistent
        and not failed_suites_without_tests
        and not unplanned
        and wanted == seen
        and all(
            x["runner_status"] not in {"ambiguous", "not_collected"} for x in results
        )
    )
    return {
        "source_revision": source_revision,
        "raw_ref": raw_ref,
        "raw_assertion_count": len(raw),
        "selected_count": sum(wanted.values()),
        "results": results,
        "unexpected": unplanned,
        "failed_suites_without_tests": failed_suites_without_tests,
        "reporter_consistent": reporter_consistent,
        "reporter_success": report.get("success"),
        "collection_complete": complete,
        "tc_verdicts_assessed": False,
        "attempt_completeness": "not_provided_by_reporter",
    }


def compare_direct(
    *, started: bool, expectations: list[dict[str, Any]], observations: dict[str, Any]
) -> dict[str, Any]:
    """Expected/observed JSON value equality; missing observations stay unknown."""
    if (
        type(started) is not bool
        or not isinstance(expectations, list)
        or not expectations
    ):
        raise ContractError("invalid_direct_execution")
    if not isinstance(observations, dict):
        raise ContractError("invalid_observations")
    ids = [_required_str(item.get("id"), "expectation_id") for item in expectations]
    if len(set(ids)) != len(ids) or any(
        "expected" not in item for item in expectations
    ):
        raise ContractError("invalid_expectations")
    details = []
    for item in expectations:
        ref = item["id"]
        observed = ref in observations if started else False
        same = (
            observed
            and type(item["expected"]) is type(observations[ref])
            and item["expected"] == observations[ref]
        )
        details.append(
            {
                "expectation_ref": ref,
                "observed": observed,
                "matches": same if observed else None,
            }
        )
    if not started:
        result = "未実行"
    elif any(x["matches"] is False for x in details):
        result = "FAIL"
    elif any(not x["observed"] for x in details):
        result = "判定不能"
    else:
        result = "PASS"
    return {"result": result, "details": details, "cleanup_status": "未確認"}


def interpret_static(
    *,
    started: bool,
    exit_code: int | None,
    raw_ref: str | None,
    findings_count: int | None,
) -> dict[str, Any]:
    """Never infer no findings from exit 0 or from missing tool output."""
    if type(started) is not bool:
        raise ContractError("invalid_start_state")
    if not started:
        if exit_code is not None or raw_ref is not None or findings_count is not None:
            raise ContractError("unstarted_with_tool_results")
        return {"state": "未実行", "complete": False}
    if (
        type(exit_code) is not int
        or not raw_ref
        or type(findings_count) is not int
        or findings_count < 0
    ):
        return {"state": "取得不完全", "complete": False}
    return {
        "state": "実行済み",
        "complete": True,
        "exit_code": exit_code,
        "raw_ref": raw_ref,
        "findings_count": findings_count,
    }


def diagnosis(*, run_ref: str, hypotheses: list[dict[str, Any]]) -> dict[str, Any]:
    _required_str(run_ref, "run_ref")
    allowed = {"SUT", "testware", "fixture", "environment", "runner", "spec_unknown"}
    if not isinstance(hypotheses, list):
        raise ContractError("invalid_hypotheses")
    for h in hypotheses:
        if (
            h.get("cause") not in allowed
            or not h.get("evidence_ref")
            or h.get("confidence") not in {"high", "medium", "low", "unknown"}
            or not h.get("next_owner")
        ):
            raise ContractError("invalid_diagnosis")
    return {
        "original_run_ref": run_ref,
        "hypotheses": hypotheses,
        "original_result_modified": False,
        "defect_confirmed": False,
    }
