from __future__ import annotations

import json
from typing import Any

from scripts.skills.evals.deterministic.common import fenced_code_blocks
from scripts.skills.evals.deterministic.result import EvalResult


def _json_documents(text: str) -> tuple[list[Any], list[str]]:
    matches = [
        body
        for info, body in fenced_code_blocks(text)
        if info.casefold().split(maxsplit=1)[:1] == ["json"]
    ]
    values: list[Any] = []
    errors: list[str] = []
    for index, block in enumerate(matches, start=1):
        try:
            values.append(json.loads(block))
        except json.JSONDecodeError as exc:
            errors.append(f"invalid_json[{index}]:{exc.msg}")
    return values, errors


def _document(text: str) -> tuple[dict[str, Any] | None, list[str]]:
    values, errors = _json_documents(text)
    if errors:
        return None, errors
    artifacts = [
        value
        for value in values
        if isinstance(value, dict) and "artifact_type" in value
    ]
    if len(artifacts) != 1:
        return None, ["exactly_one_json_machine_artifact_required"]
    return artifacts[0], []


def _shape_issues(doc: dict[str, Any], kind: str) -> list[dict[str, str]]:
    """Report wrong JSON container shapes before semantic validation uses them."""
    issues: list[dict[str, str]] = []
    if not isinstance(kind, str):
        return [
            {
                "path": "artifact_type",
                "expected": "str",
                "actual": type(kind).__name__,
            }
        ]

    def check(path: str, value: Any, expected: type) -> None:
        if not isinstance(value, expected):
            issues.append(
                {
                    "path": path,
                    "expected": expected.__name__,
                    "actual": type(value).__name__,
                }
            )

    def check_list(path: str, value: Any, item_type: type | None = None) -> None:
        check(path, value, list)
        if isinstance(value, list) and item_type is not None:
            for index, item in enumerate(value):
                check(f"{path}[{index}]", item, item_type)

    def check_map(path: str, value: Any, value_type: type | None = None) -> None:
        check(path, value, dict)
        if isinstance(value, dict) and value_type is not None:
            for key, item in value.items():
                check(f"{path}.{key}", item, value_type)

    if kind == "baseline":
        check("completeness_evidence", doc.get("completeness_evidence"), dict)
        check_list("memberships", doc.get("memberships"), dict)
        check_list("source_revisions", doc.get("source_revisions"), dict)
        memberships = doc.get("memberships")
        if isinstance(memberships, list):
            for index, item in enumerate(memberships):
                if not isinstance(item, dict):
                    continue
                check(f"memberships[{index}].decision", item.get("decision"), str)
                check(
                    f"memberships[{index}].lifecycle_status",
                    item.get("lifecycle_status"),
                    str,
                )
                check_list(
                    f"memberships[{index}].source_refs", item.get("source_refs"), str
                )
                check_list(
                    f"memberships[{index}].source_revisions",
                    item.get("source_revisions"),
                    dict,
                )
        for field in (
            "scope_refs",
            "member_tc_refs",
            "one_off_tc_refs",
            "unresolved_tc_refs",
            "undecided_tc_refs",
        ):
            check_list(field, doc.get(field), str)
        check_list("coverage_gaps", doc.get("coverage_gaps"))
    elif kind == "run":
        check("baseline", doc.get("baseline"), dict)
        check_list("selected_tc_refs", doc.get("selected_tc_refs"), str)
        check_list("required_routes", doc.get("required_routes"), dict)
        check_list("auxiliary_testware_refs", doc.get("auxiliary_testware_refs"), str)
        if type(doc.get("auxiliary_testware_count")) is not int:
            issues.append(
                {
                    "path": "auxiliary_testware_count",
                    "expected": "int",
                    "actual": type(doc.get("auxiliary_testware_count")).__name__,
                }
            )
        baseline = doc.get("baseline")
        if isinstance(baseline, dict):
            check_list("baseline.member_tc_refs", baseline.get("member_tc_refs"), str)
        routes = doc.get("required_routes")
        if isinstance(routes, list):
            for index, route in enumerate(routes):
                if not isinstance(route, dict):
                    continue
                check(
                    f"required_routes[{index}].route_type", route.get("route_type"), str
                )
                if "e2e_testware_ref" in route:
                    check(
                        f"required_routes[{index}].e2e_testware_ref",
                        route.get("e2e_testware_ref"),
                        str,
                    )
    elif kind == "activity":
        check_map("source_executions", doc.get("source_executions"), dict)
        check_list("route_results", doc.get("route_results"), dict)
        check_map("tc_execution_state", doc.get("tc_execution_state"), str)
        check("counts", doc.get("counts"), dict)
        check_list("auxiliary_route_results", doc.get("auxiliary_route_results"), dict)
        check_list("auxiliary_testware_refs", doc.get("auxiliary_testware_refs"), str)
        check_list("unresolved", doc.get("unresolved"), str)
        for field in ("activity_state", "cleanup_status"):
            check(field, doc.get(field), str)
        counts = doc.get("counts")
        if (
            isinstance(counts, dict)
            and type(counts.get("auxiliary_testware_count")) is not int
        ):
            issues.append(
                {
                    "path": "counts.auxiliary_testware_count",
                    "expected": "int",
                    "actual": type(counts.get("auxiliary_testware_count")).__name__,
                }
            )
        routes = doc.get("route_results")
        if isinstance(routes, list):
            for index, route in enumerate(routes):
                if not isinstance(route, dict):
                    continue
                for field in ("tc_ref", "route_ref", "execution_ref"):
                    check(f"route_results[{index}].{field}", route.get(field), str)
    return issues


def validate(text: str, expected: dict[str, Any], eval_id: str) -> EvalResult:
    result = EvalResult("regression-testing", eval_id)
    if expected.get("expect_blocked_output") is True:
        json_values, json_errors = _json_documents(text)
        json_fence_count = len(json_values) + len(json_errors)
        required_tokens = expected.get("required_block_tokens", [])
        missing_tokens = [
            token
            for token in required_tokens
            if not isinstance(token, str) or token.casefold() not in text.casefold()
        ]
        explicit_block = any(
            marker in text.casefold()
            for marker in ("block", "blocked", "ブロック", "materializeできない")
        )
        result.add(
            "REG-D001",
            json_fence_count == 0,
            "必須identity / provenance不足のblock経路でJSON fenced blockを出力しないこと",
            evidence={
                "json_fence_count": json_fence_count,
                "json_errors": json_errors,
            }
            if json_fence_count
            else None,
        )
        block_valid = json_fence_count == 0 and not missing_tokens and explicit_block
        result.add(
            "REG-D019",
            block_valid,
            "必要なActivity identity / source evidence / cleanup情報がない場合にJSON fenced blockを出さず理由を示してblockすること",
            evidence={
                "json_fence_count": json_fence_count,
                "json_errors": json_errors,
                "missing_block_tokens": missing_tokens,
                "explicit_block": explicit_block,
            }
            if not block_valid
            else None,
        )
        return result

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
        isinstance(kind, str) and kind in {"baseline", "run", "activity"},
        "artifact typeがbaseline / run / activityのいずれかであること",
        evidence=kind,
    )
    shape_issues = _shape_issues(doc, kind)
    result.add(
        "REG-D018",
        not shape_issues,
        "artifact fieldのJSON container / value shapeがdata contractに適合すること",
        evidence=shape_issues or None,
    )
    # Continue safe semantic checks where possible so existing assertions retain
    # their diagnostics. Any fallback below is paired with a failing REG-D018;
    # malformed containers can never be accepted as a valid artifact.
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
            isinstance(item.get("decision"), str)
            and item.get("decision") in valid_decisions
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
            and (
                "expected_baseline_ref" not in expected
                or doc.get("baseline_ref") == expected["expected_baseline_ref"]
            )
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
        baseline = doc.get("baseline")
        baseline_current = (
            isinstance(baseline, dict)
            and baseline.get("complete") is True
            and baseline.get("currentness") == "current"
        )
        result.add(
            "REG-D006",
            scope != "full" or baseline_current,
            "full Runはcompleteかつcurrentなbaselineだけから作ること",
        )
        selected_refs = doc.get("selected_tc_refs")
        selected = (
            set(selected_refs)
            if isinstance(selected_refs, list)
            and all(isinstance(ref, str) for ref in selected_refs)
            else None
        )
        member_refs = (
            baseline.get("member_tc_refs") if isinstance(baseline, dict) else None
        )
        members = (
            set(member_refs)
            if isinstance(member_refs, list)
            and all(isinstance(ref, str) for ref in member_refs)
            else None
        )
        subset_valid = (
            selected is not None
            and members is not None
            and selected <= members
            and (scope != "selected" or doc.get("suite_complete") is False)
        )
        result.add(
            "REG-D007",
            subset_valid,
            "selected RunはSuite memberのsubsetとして保持し、Suite完了と扱わないこと",
            evidence=(
                sorted(selected - members)
                if selected is not None and members is not None
                else {
                    "selected_tc_refs_type": type(selected_refs).__name__,
                    "baseline.member_tc_refs_type": type(member_refs).__name__,
                }
            ),
        )
        routes = doc.get("required_routes")
        invalid = (
            [
                route
                for route in routes
                if not isinstance(route, dict)
                or not isinstance(route.get("route_type"), str)
                or route.get("route_type") not in {"manual", "e2e"}
                or (
                    route.get("route_type") == "e2e"
                    and not route.get("e2e_testware_ref")
                )
            ]
            if isinstance(routes, list)
            else [{"field": "required_routes", "actual_type": type(routes).__name__}]
        )
        result.add(
            "REG-D008",
            not invalid,
            "required routeをmanualまたはconcrete E2E testware refで表すこと",
            evidence=invalid or None,
        )
        auxiliary_refs = doc.get("auxiliary_testware_refs")
        auxiliary_ref_count = (
            len(auxiliary_refs) if isinstance(auxiliary_refs, list) else None
        )
        result.add(
            "REG-D009",
            doc.get("auxiliary_testware_count") == auxiliary_ref_count,
            "TCなし補助testwareをTC countから分離すること",
        )
    elif kind == "activity":
        route_results = doc.get("route_results")
        routes = (
            [route for route in route_results if isinstance(route, dict)]
            if isinstance(route_results, list)
            else ()
        )
        by_tc: dict[str, list[dict[str, Any]]] = {}
        source_mismatches = []
        source = doc.get("source_executions")

        def source_execution(route: dict[str, Any]) -> dict[str, Any] | None:
            execution_ref = route.get("execution_ref")
            value = (
                source.get(execution_ref)
                if isinstance(source, dict) and isinstance(execution_ref, str)
                else None
            )
            return value if isinstance(value, dict) else None

        for route in routes:
            tc_ref = route.get("tc_ref")
            by_tc.setdefault(str(tc_ref), []).append(route)
            execution = source_execution(route)
            actual_started = (
                isinstance(execution, dict)
                and execution.get("start_state") == "開始済み"
                and execution.get("actual_start_confirmed") is True
            )
            if route.get("executed") is not actual_started:
                source_mismatches.append(
                    {"tc_ref": tc_ref, "route_ref": route.get("route_ref")}
                )
            source_result = (
                execution.get("source_result") if isinstance(execution, dict) else None
            )
            if route.get("source_result") != source_result:
                source_mismatches.append(
                    {"tc_ref": tc_ref, "issue": "source_result_reinterpreted"}
                )
            if route.get("result_finalized") is not (
                isinstance(execution, dict)
                and execution.get("result_finalized") is True
            ):
                source_mismatches.append(
                    {
                        "tc_ref": tc_ref,
                        "issue": "source_result_finalization_not_projected",
                    }
                )
        state_errors = []
        tc_states = doc.get("tc_execution_state")
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
            actual_state = (
                tc_states.get(tc_ref) if isinstance(tc_states, dict) else None
            )
            if actual_state != expected_state:
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
        completion_valid = expected_state != "完了" or (
            bool(routes)
            and all(
                route.get("executed") is True
                and route.get("result_finalized") is True
                and route.get("source_result_projectable") is True
                and isinstance(route.get("source_result"), str)
                and bool(route.get("source_result", "").strip())
                and isinstance(source_execution(route), dict)
                and route.get("source_result")
                == source_execution(route).get("source_result")
                and source_execution(route).get("result_finalized") is True
                for route in routes
            )
            and isinstance(cleanup, str)
            and cleanup in {"成功", "対象なし", "意図的に残した状態"}
            and not doc.get("unresolved")
        )
        result.add(
            "REG-D011",
            completion_valid,
            "required routeのactual start・owner result確定・source result投影とcleanupが未解決ならActivityを完了にしないこと",
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
        auxiliary = doc.get("auxiliary_route_results")
        auxiliary_rows = (
            [item for item in auxiliary if isinstance(item, dict)]
            if isinstance(auxiliary, list)
            else ()
        )
        aux_issues = [item for item in auxiliary_rows if item.get("tc_ref")]
        counts = doc.get("counts")
        auxiliary_count = (
            counts.get("auxiliary_testware_count") if isinstance(counts, dict) else None
        )
        if auxiliary_count != len(auxiliary_rows) or not isinstance(auxiliary, list):
            aux_issues.append({"issue": "auxiliary_count_mismatch"})
        result.add(
            "REG-D015",
            not aux_issues,
            "TCなし補助testwareを別枠に保ち、TC ref / countへ混在させないこと",
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
