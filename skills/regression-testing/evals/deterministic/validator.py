from __future__ import annotations

import json
import re
from typing import Any

from scripts.skills.evals.deterministic.result import EvalResult


def _document(text: str) -> tuple[dict[str, Any] | None, list[str]]:
    matches = re.findall(r"```json\s*\n(.*?)\n```", text, flags=re.DOTALL | re.IGNORECASE)
    if len(matches) != 1:
        return None, ["exactly_one_json_artifact_required"]
    try:
        value = json.loads(matches[0])
    except json.JSONDecodeError as exc:
        return None, [f"invalid_json:{exc.msg}"]
    if not isinstance(value, dict):
        return None, ["artifact_root_must_be_object"]
    return value, []


def validate(text: str, expected: dict[str, Any], eval_id: str) -> EvalResult:
    result = EvalResult("regression-testing", eval_id)
    doc, errors = _document(text)
    result.add("REG-D001", doc is not None, "正規JSON artifactが一つだけ整形式で存在すること", evidence=errors or None)
    if doc is None:
        return result

    kind = doc.get("artifact_type")
    result.add("REG-D002", kind in {"baseline", "run", "activity"}, "artifact typeがbaseline / run / activityのいずれかであること", evidence=kind)
    if kind == "baseline":
        evidence = doc.get("completeness_evidence", {})
        derived = all(evidence.get(key) is True for key in ("root_listing_complete", "source_revisions_complete", "lifecycle_resolved", "membership_decisions_complete"))
        result.add("REG-D003", doc.get("complete") is derived, "baseline completeはdiscovery・lifecycle・membershipの各完了根拠から導出されること", evidence={"expected": derived, "actual": doc.get("complete")})
        refs = [item.get("tc_ref") for item in doc.get("memberships", []) if isinstance(item, dict)]
        duplicate_refs = len(refs) != len(set(refs))
        invalid_members = [item.get("tc_ref") for item in doc.get("memberships", []) if item.get("decision") == "member" and item.get("lifecycle_status") != "current"]
        result.add("REG-D004", not duplicate_refs and not invalid_members, "membership refが一意でcurrent logical TCだけをmemberにすること", evidence={"duplicate_refs": duplicate_refs, "invalid_members": invalid_members})
        result.add("REG-D005", doc.get("coverage_gaps") is not None, "traceability coverage gapをinventory / lifecycle不完全と分けて保持すること")
    elif kind == "run":
        scope = doc.get("run_scope")
        baseline = doc.get("baseline", {})
        result.add("REG-D006", scope != "full" or (baseline.get("complete") is True and baseline.get("currentness") == "current"), "full Runはcompleteかつcurrentなbaselineだけから作ること")
        selected = set(doc.get("selected_tc_refs", []))
        members = set(baseline.get("member_tc_refs", []))
        result.add("REG-D007", selected <= members and (scope != "selected" or doc.get("suite_complete") is False), "selected RunはSuite memberのsubsetとして保持し、Suite完了と扱わないこと", evidence=sorted(selected - members))
        routes = doc.get("required_routes", [])
        invalid = [route for route in routes if route.get("route_type") not in {"manual", "e2e"} or (route.get("route_type") == "e2e" and not route.get("e2e_testware_ref"))]
        result.add("REG-D008", not invalid, "required routeをmanualまたはconcrete E2E testware refで表すこと", evidence=invalid or None)
        result.add("REG-D009", doc.get("auxiliary_testware_count") == len(doc.get("auxiliary_testware_refs", [])), "TCなし補助testwareをTC countから分離すること")
    elif kind == "activity":
        routes = doc.get("route_results", [])
        by_tc: dict[str, list[dict[str, Any]]] = {}
        source_mismatches = []
        source = doc.get("source_executions", {})
        for route in routes:
            tc_ref = route.get("tc_ref")
            by_tc.setdefault(str(tc_ref), []).append(route)
            execution = source.get(route.get("execution_ref"), {})
            actual_started = execution.get("start_state") == "開始済み" and execution.get("actual_start_confirmed") is True
            if route.get("executed") is not actual_started:
                source_mismatches.append({"tc_ref": tc_ref, "route_ref": route.get("route_ref")})
            if route.get("source_result") != execution.get("source_result"):
                source_mismatches.append({"tc_ref": tc_ref, "issue": "source_result_reinterpreted"})
            if route.get("result_finalized") is not (execution.get("result_finalized") is True):
                source_mismatches.append({"tc_ref": tc_ref, "issue": "source_result_finalization_not_projected"})
        state_errors = []
        for tc_ref, tc_routes in by_tc.items():
            started = all(route.get("executed") is True for route in tc_routes)
            expected_state = "executed" if started else ("blocked" if any(route.get("blocked") is True for route in tc_routes) else "unexecuted")
            if doc.get("tc_execution_state", {}).get(tc_ref) != expected_state:
                state_errors.append({"tc_ref": tc_ref, "expected": expected_state})
        result.add("REG-D010", not source_mismatches and not state_errors, "source actual start/resultをそのまま投影し、全required route開始後だけlogical TCをexecutedにすること", evidence={"source_mismatches": source_mismatches, "state_errors": state_errors})
        cleanup = doc.get("cleanup_status")
        expected_state = doc.get("activity_state")
        source = doc.get("source_executions", {})
        completion_valid = expected_state != "完了" or (
            bool(routes)
            and all(
                route.get("executed") is True
                and route.get("result_finalized") is True
                and route.get("source_result_projectable") is True
                and isinstance(route.get("source_result"), str)
                and bool(route.get("source_result", "").strip())
                and route.get("source_result") == source.get(route.get("execution_ref"), {}).get("source_result")
                and source.get(route.get("execution_ref"), {}).get("result_finalized") is True
                for route in routes
            )
            and cleanup in {"成功", "対象なし", "意図的に残した状態"}
            and not doc.get("unresolved")
        )
        result.add("REG-D011", completion_valid, "required routeのactual start・owner result確定・source result投影とcleanupが未解決ならActivityを完了にしないこと")
        result.add("REG-D012", not (doc.get("previous_activity_state") == "完了" and doc.get("mutation_applied") is True), "completed Activityをimmutableとして扱うこと")
        result.add("REG-D013", doc.get("activity_ref") and doc.get("snapshot_ref") and doc.get("scope_identity"), "Activityがidentityと固定snapshotを参照すること")
        auxiliary = doc.get("auxiliary_route_results", [])
        aux_issues = [item for item in auxiliary if item.get("tc_ref")]
        if doc.get("counts", {}).get("auxiliary_testware_count") != len(auxiliary):
            aux_issues.append({"issue": "auxiliary_count_mismatch"})
        result.add("REG-D015", not aux_issues, "TCなし補助testwareを別枠に保ち、TC ref / countへ混在させないこと", evidence=aux_issues or None)
    expected_kind = expected.get("artifact_type")
    result.add("REG-D014", not expected_kind or kind == expected_kind, "fixtureが指定したartifact kindと一致すること", evidence={"expected": expected_kind, "actual": kind})
    return result
