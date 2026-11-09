from __future__ import annotations

import json
import re
from typing import Any

from scripts.skills.evals.deterministic.result import EvalResult


def _document(text: str) -> tuple[dict[str, Any] | None, list[str]]:
    matches = re.findall(
        r"```json\s*\n(.*?)\n```", text, flags=re.DOTALL | re.IGNORECASE
    )
    if len(matches) != 1:
        return None, ["exactly_one_json_artifact_required"]
    try:
        value = json.loads(matches[0])
    except json.JSONDecodeError as exc:
        return None, [f"invalid_json:{exc.msg}"]
    if not isinstance(value, dict):
        return None, ["artifact_root_must_be_object"]
    return value, []


ROUTE_CONTRACT_VERSION = "2"
CLEANUP_CLOSED = {"成功", "対象なし", "意図的に残した状態"}
AUXILIARY_OWNERS = {"e2e-test-execution", "testware-execution"}
AUXILIARY_REQUIRED_BASES = {"user_explicit", "policy"}
AUXILIARY_BASES = AUXILIARY_REQUIRED_BASES | {"reference_only"}


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _source_started(source: dict[str, Any], declared_revision: Any) -> bool:
    """owner sourceだけからactual startと対象実装revisionの一致を再計算する。"""
    return (
        source.get("start_state") == "開始済み"
        and source.get("actual_start_confirmed") is True
        and (
            not _text(declared_revision)
            or source.get("implementation_revision") == declared_revision
        )
    )


def _auxiliary_run_issues(doc: dict[str, Any]) -> list[str]:
    v2 = doc.get("route_contract_version") == ROUTE_CONTRACT_VERSION
    entries = doc.get("auxiliary_routes", [])
    refs = doc.get("auxiliary_testware_refs", [])
    issues: list[str] = []
    if not isinstance(entries, list) or not isinstance(refs, list):
        return ["auxiliary_routes_or_refs_not_list"]
    tc_testware = {
        route.get("testware_ref")
        for route in doc.get("required_routes", [])
        if route.get("route_type") == "testware"
    }
    seen: set[Any] = set()
    for entry in entries:
        if not isinstance(entry, dict):
            issues.append("invalid_auxiliary_route")
            continue
        ref = entry.get("testware_ref")
        if not _text(ref) or ref in seen:
            issues.append(f"missing_or_duplicate_auxiliary_testware_ref:{ref}")
        seen.add(ref)
        if entry.get("tc_ref"):
            issues.append(f"auxiliary_route_has_tc_ref:{ref}")
        if ref in tc_testware:
            issues.append(f"auxiliary_ref_also_tc_route:{ref}")
        required = entry.get("completion_required")
        if not v2:
            if "completion_required" in entry:
                issues.append(f"completion_required_needs_contract_version:{ref}")
            continue
        basis = entry.get("selection_basis")
        if (
            type(required) is not bool
            or entry.get("executor_owner") not in AUXILIARY_OWNERS
            or not _text(entry.get("implementation_revision"))
            or basis not in AUXILIARY_BASES
            or required is not (basis in AUXILIARY_REQUIRED_BASES)
        ):
            issues.append(f"invalid_auxiliary_obligation:{ref}")
    if v2 and set(refs) != seen:
        issues.append("auxiliary_refs_routes_mismatch")
    return issues


def validate(text: str, expected: dict[str, Any], eval_id: str) -> EvalResult:
    result = EvalResult("regression-testing", eval_id)
    doc, errors = _document(text)
    result.add(
        "REG-D001",
        doc is not None,
        "正規JSON artifactが一つだけ整形式で存在すること",
        evidence=errors or None,
    )
    if doc is None:
        return result

    kind = doc.get("artifact_type")
    result.add(
        "REG-D002",
        kind in {"baseline", "run", "activity"},
        "artifact typeがbaseline / run / activityのいずれかであること",
        evidence=kind,
    )
    if kind == "baseline":
        evidence = doc.get("completeness_evidence", {})
        evidence_keys = (
            "root_listing_complete",
            "source_revisions_complete",
            "lifecycle_resolved",
            "membership_decisions_complete",
        )
        evidence_valid = isinstance(evidence, dict) and all(
            type(evidence.get(key)) is bool for key in evidence_keys
        )
        derived = evidence_valid and all(evidence[key] is True for key in evidence_keys)
        memberships = doc.get("memberships")
        membership_shape_valid = isinstance(memberships, list)
        refs: list[str] = []
        invalid_members = []
        if membership_shape_valid:
            for item in memberships:
                if not isinstance(item, dict):
                    membership_shape_valid = False
                    continue
                tc_ref = item.get("tc_ref")
                if not isinstance(tc_ref, str) or not tc_ref.strip():
                    membership_shape_valid = False
                else:
                    refs.append(tc_ref)
                if (
                    item.get("decision") == "member"
                    and item.get("lifecycle_status") != "current"
                ):
                    invalid_members.append(tc_ref)
        duplicate_refs = len(refs) != len(set(refs))
        expected_current_refs = expected.get("expected_current_tc_refs")
        population_valid = True
        if "expected_current_tc_refs" in expected:
            population_valid = (
                isinstance(expected_current_refs, list)
                and all(
                    isinstance(ref, str) and bool(ref.strip())
                    for ref in expected_current_refs
                )
                and len(expected_current_refs) == len(set(expected_current_refs))
                and membership_shape_valid
                and set(refs) == set(expected_current_refs)
            )
        unresolved_memberships = membership_shape_valid and any(
            item.get("decision") == "unresolved"
            for item in memberships
            if isinstance(item, dict)
        )
        derived = derived and not unresolved_memberships
        result.add(
            "REG-D003",
            evidence_valid and doc.get("complete") is derived and population_valid,
            "baseline completeはdiscovery・lifecycle・解決済みmembershipの各完了根拠と期待されたcurrent TC全件のmembershipから導出されること",
            evidence={
                "expected": derived,
                "actual": doc.get("complete"),
                "unresolved_memberships": unresolved_memberships,
                "expected_current_tc_refs": expected_current_refs,
                "actual_membership_refs": refs,
            },
        )
        result.add(
            "REG-D004",
            membership_shape_valid and not duplicate_refs and not invalid_members,
            "membership refが一意でcurrent logical TCだけをmemberにすること",
            evidence={
                "duplicate_refs": duplicate_refs,
                "invalid_members": invalid_members,
            },
        )
        result.add(
            "REG-D005",
            doc.get("coverage_gaps") is not None,
            "traceability coverage gapをinventory / lifecycle不完全と分けて保持すること",
        )
        valid_decisions = {"member", "one_off", "out_of_scope", "unresolved"}
        decisions_valid = membership_shape_valid and all(
            item.get("decision") in valid_decisions
            for item in memberships
            if isinstance(item, dict)
        )
        scope_identity = doc.get("scope_identity")
        source_revisions = doc.get("source_revisions")
        revisions_valid = isinstance(source_revisions, list) and bool(source_revisions)
        revision_refs: set[str] = set()
        revision_map: dict[str, str] = {}
        if revisions_valid:
            for item in source_revisions:
                if not isinstance(item, dict):
                    revisions_valid = False
                    continue
                source_ref, revision = item.get("source_ref"), item.get("revision")
                if (
                    not isinstance(source_ref, str)
                    or not source_ref.strip()
                    or not isinstance(revision, str)
                    or not revision.strip()
                    or source_ref in revision_refs
                ):
                    revisions_valid = False
                elif isinstance(source_ref, str):
                    revision_refs.add(source_ref)
                    revision_map[source_ref] = revision

        provenance_valid = membership_shape_valid
        membership_revision_map: dict[str, str] = {}
        if membership_shape_valid:
            for item in memberships:
                if not isinstance(item, dict):
                    provenance_valid = False
                    continue
                source_refs = item.get("source_refs")
                source_revisions = item.get("source_revisions")
                if (
                    not isinstance(source_refs, list)
                    or not source_refs
                    or any(
                        not isinstance(ref, str) or not ref.strip()
                        for ref in source_refs
                    )
                    or len(source_refs) != len(set(source_refs))
                    or not isinstance(source_revisions, list)
                    or not source_revisions
                ):
                    provenance_valid = False
                    continue
                item_revisions: dict[str, str] = {}
                for revision_item in source_revisions:
                    if not isinstance(revision_item, dict):
                        provenance_valid = False
                        continue
                    source_ref, revision = (
                        revision_item.get("source_ref"),
                        revision_item.get("revision"),
                    )
                    if (
                        not isinstance(source_ref, str)
                        or not source_ref.strip()
                        or not isinstance(revision, str)
                        or not revision.strip()
                        or source_ref in item_revisions
                    ):
                        provenance_valid = False
                        continue
                    item_revisions[source_ref] = revision
                if set(source_refs) != set(item_revisions):
                    provenance_valid = False
                for source_ref, revision in item_revisions.items():
                    if (
                        source_ref in membership_revision_map
                        and membership_revision_map[source_ref] != revision
                    ):
                        provenance_valid = False
                    if revision_map.get(source_ref) != revision:
                        provenance_valid = False
                    membership_revision_map[source_ref] = revision

        def projection_matches(field: str, expected_refs: list[str]) -> bool:
            values = doc.get(field)
            return (
                isinstance(values, list)
                and all(
                    isinstance(value, str) and bool(value.strip()) for value in values
                )
                and len(values) == len(set(values))
                and set(values) == set(expected_refs)
            )

        expected_members = (
            [
                item["tc_ref"]
                for item in memberships
                if isinstance(item, dict)
                and item.get("decision") == "member"
                and item.get("lifecycle_status") == "current"
            ]
            if membership_shape_valid
            else []
        )
        expected_one_off = (
            [
                item["tc_ref"]
                for item in memberships
                if isinstance(item, dict) and item.get("decision") == "one_off"
            ]
            if membership_shape_valid
            else []
        )
        canonical_projection = (
            isinstance(scope_identity, str)
            and bool(scope_identity.strip())
            and revisions_valid
            and provenance_valid
            and decisions_valid
            and projection_matches("member_tc_refs", expected_members)
            and projection_matches("one_off_tc_refs", expected_one_off)
        )
        result.add(
            "REG-D016",
            canonical_projection,
            "Baselineのscope identity / source revisionsとmembership provenance / member・one_off projectionがcurrentness / Run planning用に一致すること",
        )
        unresolved_refs = doc.get("unresolved_tc_refs")
        undecided_refs = doc.get("undecided_tc_refs")
        shape_valid = (
            doc.get("schema_version") == "1"
            and isinstance(doc.get("baseline_ref"), str)
            and bool(doc.get("baseline_ref", "").strip())
            and isinstance(doc.get("discovery_snapshot_ref"), str)
            and bool(doc.get("discovery_snapshot_ref", "").strip())
            and isinstance(doc.get("scope_refs"), list)
            and isinstance(unresolved_refs, list)
            and isinstance(undecided_refs, list)
            and (
                doc.get("complete") is not True
                or (not unresolved_refs and not undecided_refs)
            )
        )
        result.add(
            "REG-D017",
            shape_valid,
            "Baselineがtemplateのschema / identity / list fieldとcomplete時の未解決refなしを満たすこと",
        )
    elif kind == "run":
        scope = doc.get("run_scope")
        baseline = doc.get("baseline", {})
        result.add(
            "REG-D006",
            scope != "full"
            or (
                baseline.get("complete") is True
                and baseline.get("currentness") == "current"
            ),
            "full Runはcompleteかつcurrentなbaselineだけから作ること",
        )
        selected = set(doc.get("selected_tc_refs", []))
        members = set(baseline.get("member_tc_refs", []))
        result.add(
            "REG-D007",
            selected <= members
            and (scope != "selected" or doc.get("suite_complete") is False),
            "selected RunはSuite memberのsubsetとして保持し、Suite完了と扱わないこと",
            evidence=sorted(selected - members),
        )
        routes = doc.get("required_routes", [])
        invalid = [
            route
            for route in routes
            if route.get("route_type") not in {"manual", "e2e", "testware"}
            or (route.get("route_type") == "e2e" and not route.get("e2e_testware_ref"))
            or (
                route.get("route_type") == "testware"
                and (
                    not _text(route.get("testware_ref"))
                    or route.get("executor_owner") != "testware-execution"
                    or not _text(route.get("implementation_revision"))
                    or not _text(route.get("selection_basis"))
                )
            )
        ]
        result.add(
            "REG-D008",
            not invalid,
            "required routeをmanual・concrete E2E testware ref・実行owner / 実装revision付きtestwareで表すこと",
            evidence=invalid or None,
        )
        auxiliary_issues = _auxiliary_run_issues(doc)
        result.add(
            "REG-D009",
            doc.get("auxiliary_testware_count")
            == len(doc.get("auxiliary_testware_refs", []))
            and not auxiliary_issues,
            "TCなし補助testwareをTC countから分離し、今回Runの実施義務と選定根拠を保持すること",
            evidence=auxiliary_issues or None,
        )
    elif kind == "activity":
        v2 = doc.get("route_contract_version") == ROUTE_CONTRACT_VERSION
        routes = doc.get("route_results", [])
        by_tc: dict[str, list[dict[str, Any]]] = {}
        source_mismatches = []
        source = doc.get("source_executions", {})
        for route in routes:
            tc_ref = route.get("tc_ref")
            by_tc.setdefault(str(tc_ref), []).append(route)
            execution = source.get(route.get("execution_ref"), {})
            actual_started = _source_started(
                execution, route.get("implementation_revision")
            )
            if route.get("executed") is not actual_started:
                source_mismatches.append(
                    {"tc_ref": tc_ref, "route_ref": route.get("route_ref")}
                )
            if route.get("source_result") != execution.get("source_result"):
                source_mismatches.append(
                    {"tc_ref": tc_ref, "issue": "source_result_reinterpreted"}
                )
            if route.get("result_finalized") is not (
                execution.get("result_finalized") is True
            ):
                source_mismatches.append(
                    {
                        "tc_ref": tc_ref,
                        "issue": "source_result_finalization_not_projected",
                    }
                )
        state_errors = []
        for tc_ref, tc_routes in by_tc.items():
            started = all(route.get("executed") is True for route in tc_routes)
            expected_state = (
                "executed"
                if started
                else (
                    "blocked"
                    if any(route.get("blocked") is True for route in tc_routes)
                    else "unexecuted"
                )
            )
            if doc.get("tc_execution_state", {}).get(tc_ref) != expected_state:
                state_errors.append({"tc_ref": tc_ref, "expected": expected_state})
        result.add(
            "REG-D010",
            not source_mismatches and not state_errors,
            "source actual start/resultをそのまま投影し、全required route開始後だけlogical TCをexecutedにすること",
            evidence={
                "source_mismatches": source_mismatches,
                "state_errors": state_errors,
            },
        )
        cleanup = doc.get("cleanup_status")
        expected_state = doc.get("activity_state")
        source = doc.get("source_executions", {})
        auxiliary = doc.get("auxiliary_route_results", [])
        if not isinstance(auxiliary, list):
            auxiliary = []
        tc_execution_refs = {
            route.get("execution_ref") for route in routes if route.get("execution_ref")
        }

        def route_complete(route: dict[str, Any]) -> bool:
            execution = source.get(route.get("execution_ref"), {})
            return bool(
                _source_started(execution, route.get("implementation_revision"))
                and route.get("executed") is True
                and route.get("result_finalized") is True
                and route.get("source_result_projectable") is True
                and isinstance(route.get("source_result"), str)
                and bool(route.get("source_result", "").strip())
                and route.get("source_result") == execution.get("source_result")
                and execution.get("result_finalized") is True
            )

        def auxiliary_complete(item: dict[str, Any]) -> bool:
            execution = source.get(item.get("execution_ref"), {})
            return bool(
                item.get("execution_ref") not in tc_execution_refs
                and _source_started(execution, item.get("implementation_revision"))
                and execution.get("result_finalized") is True
                and _text(execution.get("source_result"))
                and item.get("source_result") == execution.get("source_result")
                and execution.get("raw_capture_complete") is True
                and _text(execution.get("attempt_ref"))
                and item.get("attempt_ref") == execution.get("attempt_ref")
                and execution.get("cleanup_status", "対象なし") in CLEANUP_CLOSED
            )

        if v2:
            required_auxiliary = [
                item for item in auxiliary if item.get("completion_required") is True
            ]
            obligation_unknown = [
                item.get("testware_ref")
                for item in auxiliary
                if type(item.get("completion_required")) is not bool
            ]
            started_cleanups = [
                source.get(route.get("execution_ref"), {}).get(
                    "cleanup_status", "対象なし"
                )
                for route in [*routes, *auxiliary]
                if route.get("executed") is True
            ]
            completion_valid = expected_state != "完了" or (
                (bool(routes) or bool(required_auxiliary))
                and all(route_complete(route) for route in routes)
                and all(auxiliary_complete(item) for item in required_auxiliary)
                and not obligation_unknown
                and cleanup in CLEANUP_CLOSED
                and all(value in CLEANUP_CLOSED for value in started_cleanups)
                and not doc.get("unresolved")
            )
        else:
            # 旧Activityは読取互換のため、TC routeだけを根拠にした従来規則で検証する。
            completion_valid = expected_state != "完了" or (
                bool(routes)
                and all(
                    route.get("executed") is True
                    and route.get("result_finalized") is True
                    and route.get("source_result_projectable") is True
                    and isinstance(route.get("source_result"), str)
                    and bool(route.get("source_result", "").strip())
                    and route.get("source_result")
                    == source.get(route.get("execution_ref"), {}).get("source_result")
                    and source.get(route.get("execution_ref"), {}).get(
                        "result_finalized"
                    )
                    is True
                    for route in routes
                )
                and cleanup in CLEANUP_CLOSED
                and not doc.get("unresolved")
            )
        result.add(
            "REG-D011",
            completion_valid,
            "required TC routeと実施義務のある補助routeの実開始・owner result確定・raw結果投影・cleanup・義務不明なしをsourceから確認できない限りActivityを完了にしないこと",
        )
        result.add(
            "REG-D012",
            not (
                doc.get("previous_activity_state") == "完了"
                and doc.get("mutation_applied") is True
            ),
            "completed Activityをimmutableとして扱うこと",
        )
        result.add(
            "REG-D013",
            doc.get("activity_ref")
            and doc.get("snapshot_ref")
            and doc.get("scope_identity"),
            "Activityがidentityと固定snapshotを参照すること",
        )
        aux_issues: list[dict[str, Any]] = [
            item for item in auxiliary if item.get("tc_ref")
        ]
        counts = doc.get("counts", {})
        if counts.get("auxiliary_testware_count") != len(auxiliary):
            aux_issues.append({"issue": "auxiliary_count_mismatch"})
        if v2:
            for item in auxiliary:
                execution = source.get(item.get("execution_ref"), {})
                ref = item.get("testware_ref")
                if item.get("execution_ref") in tc_execution_refs:
                    aux_issues.append(
                        {"testware_ref": ref, "issue": "execution_shared_with_tc"}
                    )
                expected_projection = {
                    "executed": _source_started(
                        execution, item.get("implementation_revision")
                    )
                    and item.get("execution_ref") not in tc_execution_refs,
                    "result_finalized": execution.get("result_finalized") is True,
                    "raw_capture_complete": execution.get("raw_capture_complete")
                    is True,
                    "attempt_ref": execution.get("attempt_ref"),
                    "source_result": execution.get("source_result"),
                    "cleanup_status": execution.get("cleanup_status", "対象なし"),
                }
                for field, value in expected_projection.items():
                    if item.get(field) != value:
                        aux_issues.append(
                            {"testware_ref": ref, "issue": f"{field}_not_projected"}
                        )
            tc_result_counts: dict[str, int] = {}
            for route in routes:
                value = route.get("source_result")
                if route.get("executed") is True and _text(value):
                    tc_result_counts[value] = tc_result_counts.get(value, 0) + 1
            expected_counts = {
                "tc_member_count": len(by_tc),
                "executed_tc_count": sum(
                    state == "executed"
                    for state in doc.get("tc_execution_state", {}).values()
                ),
                "source_result_counts": tc_result_counts,
                "auxiliary_executed_count": sum(
                    item.get("executed") is True for item in auxiliary
                ),
                "auxiliary_required_count": sum(
                    item.get("completion_required") is True for item in auxiliary
                ),
            }
            for field, value in expected_counts.items():
                if counts.get(field) != value:
                    aux_issues.append({"issue": f"{field}_mismatch"})
        result.add(
            "REG-D015",
            not aux_issues,
            "TCなし補助testwareを別枠に保ち、TC ref / countへ混在させず、補助結果の取得完全性をsourceと照合すること",
            evidence=aux_issues or None,
        )
    expected_kind = expected.get("artifact_type")
    result.add(
        "REG-D014",
        not expected_kind or kind == expected_kind,
        "fixtureが指定したartifact kindと一致すること",
        evidence={"expected": expected_kind, "actual": kind},
    )
    return result
