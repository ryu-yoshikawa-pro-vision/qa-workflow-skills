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
    # Absent/ambiguous effect flags must never be treated as a verified
    # non-shared, local-only operation.
    for field in ("shared_resource", "external_side_effects"):
        if type(request.get(field)) is not bool:
            return {"may_start": False, "reason": field + "_unverified"}
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
    inconsistent_suites: list[str] = []
    for file in report["testResults"]:
        if not isinstance(file, dict) or not isinstance(
            file.get("assertionResults"), list
        ):
            raise ContractError("invalid_report_file")
        path = _report_path(file.get("name"), repo_root)
        status = file.get("status")
        if status not in {"passed", "failed", "pending", "todo", "skipped"}:
            inconsistent_suites.append(path)
        case_statuses = [
            case.get("status")
            for case in file["assertionResults"]
            if isinstance(case, dict)
        ]
        if status == "failed" and not file["assertionResults"]:
            failed_suites_without_tests.append(path)
        if (status == "failed" and "failed" not in case_statuses) or (
            status == "passed" and "failed" in case_statuses
        ):
            inconsistent_suites.append(path)
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
    if report.get("success") is False and not statuses["failed"]:
        # A failed run with no failing assertion may have a suite/global error.
        reporter_consistent = False
    if "success" in report and type(report["success"]) is not bool:
        reporter_consistent = False
    if inconsistent_suites:
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
        "inconsistent_suites": sorted(set(inconsistent_suites)),
        "reporter_consistent": reporter_consistent,
        "reporter_success": report.get("success"),
        "collection_complete": complete,
        "tc_verdicts_assessed": False,
        "attempt_completeness": "not_provided_by_reporter",
    }


def _reconcile_individual_results(
    *,
    selected: list[dict[str, Any]],
    actual: list[dict[str, Any]],
    source_revision: str,
    raw_ref: str,
    selection_verified: bool,
    reporter_consistent: bool,
) -> dict[str, Any]:
    """Match complete per-test identities, never file-only or internal IDs."""
    _required_str(source_revision, "source_revision")
    _required_str(raw_ref, "raw_ref")
    if not isinstance(selected, list) or not selected:
        raise ContractError("empty_selected_test_set")
    wanted = Counter(
        (
            *_test_key(item.get("path"), item.get("title_path")),
            _required_str(item.get("project_name", "default"), "project_name"),
        )
        for item in selected
        if isinstance(item, dict)
    )
    if sum(wanted.values()) != len(selected):
        raise ContractError("invalid_selected_test")
    seen = Counter()
    rows: dict[tuple[str, tuple[str, ...], str], list[dict[str, Any]]] = {}
    allowed = {
        "passed",
        "failed",
        "pending",
        "todo",
        "skipped",
        "timedOut",
        "interrupted",
        "expected",
        "unexpected",
        "flaky",
    }
    for item in actual:
        if not isinstance(item, dict):
            raise ContractError("invalid_report_case")
        key = (
            *_test_key(item.get("path"), item.get("title_path")),
            _required_str(item.get("project_name", "default"), "project_name"),
        )
        if item.get("status") not in allowed:
            raise ContractError("unknown_report_case_status")
        attempts = item.get("attempt_results")
        if not isinstance(attempts, list):
            raise ContractError("missing_attempt_results")
        seen[key] += 1
        rows.setdefault(key, []).append(item)
    results = []
    for (path, titles, project), count in wanted.items():
        matches = rows.get((path, titles, project), [])
        status = (
            "ambiguous"
            if count != 1 or len(matches) > 1
            else "not_collected"
            if not matches
            else matches[0]["status"]
        )
        results.append(
            {
                "path": path,
                "title_path": list(titles),
                "project_name": project,
                "expected_instances": count,
                "collected_instances": len(matches),
                "runner_status": status,
                "attempt_results": matches[0]["attempt_results"]
                if len(matches) == 1
                else [],
                "tc_verdict": None,
            }
        )
    unexpected = [
        {
            "path": path,
            "title_path": list(titles),
            "project_name": project,
            "count": count,
        }
        for (path, titles, project), count in seen.items()
        if (path, titles, project) not in wanted
    ]
    return {
        "source_revision": source_revision,
        "raw_ref": raw_ref,
        "results": results,
        "unexpected": unexpected,
        "reporter_consistent": reporter_consistent,
        "collection_complete": (
            selection_verified is True
            and reporter_consistent
            and wanted == seen
            and all(
                result["runner_status"] not in {"ambiguous", "not_collected"}
                for result in results
            )
        ),
        "selected_count": sum(wanted.values()),
        "collected_count": sum(seen.values()),
        "tc_verdicts_assessed": False,
    }


def reconcile_case_report(
    *,
    selected: list[dict[str, Any]],
    report: dict[str, Any],
    source_revision: str,
    testware_revision: str,
    runner_version: str,
    raw_ref: str,
    selection_verified: bool = False,
) -> dict[str, Any]:
    """Validate a versioned case-level result from an inspected batch/event adapter."""
    if (
        not isinstance(report, dict)
        or report.get("schema") != "non-e2e-cases/v1"
        or report.get("source_revision") != source_revision
        or report.get("testware_revision") != testware_revision
        or report.get("runner_version") != runner_version
        or not isinstance(report.get("results"), list)
    ):
        raise ContractError("invalid_case_report")
    raw = report["results"]
    for item in raw:
        if not isinstance(item, dict) or item.get("status") not in {
            "passed",
            "failed",
            "pending",
            "todo",
            "skipped",
            "timedOut",
            "interrupted",
        }:
            raise ContractError("invalid_case_status")
        attempts = item.get("attempt_results")
        if not isinstance(attempts, list) or (
            item["status"] not in {"skipped", "pending", "todo"} and not attempts
        ):
            raise ContractError("invalid_case_attempts")
        for index, attempt in enumerate(attempts):
            if (
                not isinstance(attempt, dict)
                or attempt.get("status")
                not in {"passed", "failed", "timedOut", "interrupted", "skipped"}
                or type(attempt.get("retry")) is not int
                or attempt["retry"] != index
            ):
                raise ContractError("invalid_case_attempt_status")
        if (
            attempts
            and attempts[-1]["status"] != item["status"]
            or item["status"] in {"pending", "todo"}
            and attempts
        ):
            raise ContractError("case_status_attempt_mismatch")
    return _reconcile_individual_results(
        selected=selected,
        actual=raw,
        source_revision=source_revision,
        raw_ref=raw_ref,
        selection_verified=selection_verified,
        reporter_consistent=(report.get("complete") is True),
    )


def reconcile_playwright(
    *,
    selected: list[dict[str, Any]],
    report: dict[str, Any],
    source_revision: str,
    runner_version: str,
    raw_ref: str,
    selection_verified: bool = False,
    repo_root: str | None = None,
) -> dict[str, Any]:
    """Parse native Playwright JSON suites/specs/projects and retain retry results."""
    if (
        not isinstance(report, dict)
        or not isinstance(report.get("suites"), list)
        or not isinstance(report.get("errors"), list)
        or not isinstance(report.get("stats"), dict)
        or not isinstance(report.get("config"), dict)
    ):
        raise ContractError("invalid_playwright_report")
    _required_str(runner_version, "runner_version")
    observed: list[dict[str, Any]] = []

    def visit(suite: dict[str, Any], parents: list[str], depth: int) -> None:
        if not isinstance(suite, dict):
            raise ContractError("invalid_playwright_suite")
        title = suite.get("title")
        if title is not None and not isinstance(title, str):
            raise ContractError("invalid_playwright_suite_title")
        titles = [*parents, title] if depth > 0 and title else parents
        specs = suite.get("specs")
        children = suite.get("suites", [])
        if not isinstance(specs, list) or not isinstance(children, list):
            raise ContractError("invalid_playwright_suite")
        for spec in specs:
            if not isinstance(spec, dict) or not isinstance(spec.get("tests"), list):
                raise ContractError("invalid_playwright_spec")
            path = _report_path(spec.get("file"), repo_root)
            title_path = [*titles, _required_str(spec.get("title"), "spec_title")]
            for test in spec["tests"]:
                if not isinstance(test, dict) or test.get("status") not in {
                    "expected",
                    "unexpected",
                    "flaky",
                    "skipped",
                }:
                    raise ContractError("invalid_playwright_test")
                attempts = test.get("results")
                if (
                    test.get("expectedStatus")
                    not in {"passed", "failed", "skipped", "timedOut", "interrupted"}
                    or not isinstance(attempts, list)
                    or (test["status"] != "skipped" and not attempts)
                ):
                    raise ContractError("missing_playwright_attempts")
                attempt_rows = []
                for index, entry in enumerate(attempts):
                    if (
                        not isinstance(entry, dict)
                        or entry.get("status")
                        not in {
                            "passed",
                            "failed",
                            "timedOut",
                            "interrupted",
                            "skipped",
                        }
                        or type(entry.get("retry")) is not int
                        or entry["retry"] != index
                    ):
                        raise ContractError("invalid_playwright_attempt")
                    attempt_rows.append(
                        {"status": entry["status"], "retry": entry.get("retry")}
                    )
                expected = test["expectedStatus"]
                statuses = [row["status"] for row in attempt_rows]
                outcome = test["status"]
                if (
                    outcome == "expected"
                    and any(status != expected for status in statuses)
                    or outcome == "unexpected"
                    and statuses[-1] == expected
                    or outcome == "flaky"
                    and (
                        len(statuses) < 2
                        or statuses[-1] != expected
                        or all(status == expected for status in statuses)
                    )
                    or outcome == "skipped"
                    and statuses
                    and statuses[-1] != "skipped"
                ):
                    raise ContractError("playwright_status_attempt_mismatch")
                observed.append(
                    {
                        "path": path,
                        "title_path": title_path,
                        "project_name": _required_str(
                            test.get("projectName", "default") or "default",
                            "project_name",
                        ),
                        "status": test["status"],
                        "attempt_results": attempt_rows,
                    }
                )
        for nested in children:
            visit(nested, titles, depth + 1)

    for top in report["suites"]:
        visit(top, [], 0)
    stats = report["stats"]
    totals = Counter(item["status"] for item in observed)
    consistent = (
        report["errors"] == []
        and report["config"].get("version") == runner_version
        and all(
            type(stats.get(name)) is int and stats[name] == totals[status]
            for name, status in [
                ("expected", "expected"),
                ("unexpected", "unexpected"),
                ("flaky", "flaky"),
                ("skipped", "skipped"),
            ]
        )
    )
    return _reconcile_individual_results(
        selected=selected,
        actual=observed,
        source_revision=source_revision,
        raw_ref=raw_ref,
        selection_verified=selection_verified,
        reporter_consistent=consistent,
    )


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
            not isinstance(h, dict)
            or h.get("cause") not in allowed
            or not isinstance(h.get("evidence_ref"), str)
            or not h["evidence_ref"].strip()
            or h.get("confidence") not in {"high", "medium", "low", "unknown"}
            or not isinstance(h.get("next_owner"), str)
            or not h["next_owner"].strip()
        ):
            raise ContractError("invalid_diagnosis")
    return {
        "original_run_ref": run_ref,
        "hypotheses": hypotheses,
        "original_result_modified": False,
        "defect_confirmed": False,
    }


def compare_metrics(
    *,
    started: bool,
    criteria: list[dict[str, Any]],
    measurements: dict[str, Any],
    condition_ref: str,
    authority_ref: str,
) -> dict[str, Any]:
    """Evaluate measured numeric quantities only against adopted thresholds."""
    import math

    _required_str(condition_ref, "measurement_condition")
    _required_str(authority_ref, "threshold_authority")
    if type(started) is not bool or not isinstance(criteria, list) or not criteria:
        raise ContractError("invalid_metric_criteria")
    if not isinstance(measurements, dict):
        raise ContractError("invalid_measurements")
    seen: set[str] = set()
    results = []
    for entry in criteria:
        if not isinstance(entry, dict):
            raise ContractError("invalid_metric_entry")
        key = _required_str(entry.get("id"), "metric_id")
        characteristic = _required_str(entry.get("characteristic"), "characteristic")
        unit = _required_str(entry.get("unit"), "unit")
        if key in seen or ("minimum" not in entry and "maximum" not in entry):
            raise ContractError("invalid_metric_threshold")
        seen.add(key)
        for field in ("minimum", "maximum"):
            if field in entry and (
                type(entry[field]) not in {int, float}
                or not math.isfinite(entry[field])
            ):
                raise ContractError("invalid_metric_bound")
        if (
            "minimum" in entry
            and "maximum" in entry
            and entry["minimum"] > entry["maximum"]
        ):
            raise ContractError("contradictory_metric_bounds")
        actual = measurements.get(key) if started else None
        observed = type(actual) in {int, float} and math.isfinite(actual)
        matches = (
            observed
            and ("minimum" not in entry or actual >= entry["minimum"])
            and ("maximum" not in entry or actual <= entry["maximum"])
        )
        results.append(
            {
                "metric_ref": key,
                "characteristic": characteristic,
                "unit": unit,
                "observed": observed,
                "value": actual if observed else None,
                "matches": matches if observed else None,
            }
        )
    if not started:
        verdict = "未実行"
    elif any(x["matches"] is False for x in results):
        verdict = "FAIL"
    elif any(x["matches"] is None for x in results):
        verdict = "判定不能"
    else:
        verdict = "PASS"
    return {
        "verdict": verdict,
        "condition_ref": condition_ref,
        "authority_ref": authority_ref,
        "results": results,
    }
