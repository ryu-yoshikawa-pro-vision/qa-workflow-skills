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


def _source_started(
    source: dict[str, Any], declared_revision: Any, *, require_revision: bool = False
) -> bool:
    """owner sourceだけからactual startと対象実装revisionの一致を再計算する。

    `require_revision`（testware route・実施義務のある補助）では、宣言revisionの
    欠落を一致として扱わない。
    """
    if _text(declared_revision):
        revision_ok = source.get("implementation_revision") == declared_revision
    else:
        revision_ok = not require_revision
    return (
        source.get("start_state") == "開始済み"
        and source.get("actual_start_confirmed") is True
        and revision_ok
    )


def _execution(sources: dict[str, Any], ref: Any) -> dict[str, Any]:
    """型が不正なexecution_ref・sourceでも例外にせず、空sourceとして扱う。"""
    value = sources.get(ref) if isinstance(ref, str) else None
    return value if isinstance(value, dict) else {}


def _object_list(value: Any, name: str, issues: list[dict[str, Any]]) -> list[Any]:
    if isinstance(value, list) and all(isinstance(item, dict) for item in value):
        return value
    issues.append({"issue": f"{name}_not_list_of_objects"})
    return []


def _auxiliary_run_issues(doc: dict[str, Any]) -> list[str]:
    version_present = "route_contract_version" in doc
    v2 = doc.get("route_contract_version") == ROUTE_CONTRACT_VERSION
    entries = doc.get("auxiliary_routes", [])
    refs = doc.get("auxiliary_testware_refs", [])
    required_routes = doc.get("required_routes", [])
    issues: list[str] = []
    if version_present and not v2:
        issues.append("unsupported_route_contract_version")
    if (
        not isinstance(entries, list)
        or not isinstance(refs, list)
        or not isinstance(required_routes, list)
    ):
        return [*issues, "auxiliary_routes_or_refs_not_list"]
    tc_testware = {
        route.get("testware_ref")
        for route in required_routes
        if isinstance(route, dict)
        and route.get("route_type") == "testware"
        and _text(route.get("testware_ref"))
    }
    seen: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict):
            issues.append("invalid_auxiliary_route")
            continue
        ref = entry.get("testware_ref")
        if not _text(ref):
            issues.append("missing_or_invalid_auxiliary_testware_ref")
            continue
        if ref in seen:
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
            or not _in(entry.get("executor_owner"), AUXILIARY_OWNERS)
            or not _text(entry.get("implementation_revision"))
            or not _in(basis, AUXILIARY_BASES)
            or required is not _in(basis, AUXILIARY_REQUIRED_BASES)
        ):
            issues.append(f"invalid_auxiliary_obligation:{ref}")
    ref_set = {ref for ref in refs if _text(ref)}
    # refs一覧は省略できる。フィールドが存在する場合だけ、補助routeとの集合一致と重複を検査する
    # （省略と空配列は区別する）。
    if (
        v2
        and "auxiliary_testware_refs" in doc
        and (ref_set != seen or len(ref_set) != len(refs))
    ):
        issues.append("auxiliary_refs_routes_mismatch")
    return issues


def _auxiliary_count_issues(doc: dict[str, Any], *, v2: bool) -> list[str]:
    """`auxiliary_testware_count`は型を厳密に確認し、実際の補助数と照合する。

    boolや小数・文字列・負数を件数へ変換しない。refs一覧を宣言していれば
    その長さと、v2 Runでは`auxiliary_routes`の件数とも一致しなければならない。
    """
    count = doc.get("auxiliary_testware_count")
    if type(count) is not int or count < 0:
        return ["invalid_auxiliary_testware_count"]
    actual: list[int] = []
    refs = doc.get("auxiliary_testware_refs", [])
    # v2 Runのrefs一覧は省略でき、省略時は`auxiliary_routes`の件数とだけ照合する。
    # 旧形式はrefs一覧だけが補助の根拠であり、省略は空一覧として従来どおり扱う。
    if isinstance(refs, list) and (not v2 or "auxiliary_testware_refs" in doc):
        actual.append(len(refs))
    entries = doc.get("auxiliary_routes", [])
    if v2 and isinstance(entries, list):
        actual.append(len(entries))
    return (
        ["auxiliary_testware_count_mismatch"]
        if any(count != value for value in actual)
        else []
    )


def _ref_set(value: Any) -> set[str] | None:
    """TC refのlistをsetにする。listでない・空でない文字列以外を含む場合はNone。"""
    if not isinstance(value, list) or not all(_text(item) for item in value):
        return None
    return set(value)


def _in(value: Any, allowed: set[str]) -> bool:
    """型不正の値（list・dict等）を集合照会へ渡さず不一致として扱う。"""
    return isinstance(value, str) and value in allowed


# TC付きtestware routeの選定情報（testware_ref・executor_owner・selection_basis）も
# 識別子に含める。manual・e2e routeはこれらを持たず、双方Noneとして比較される。
_ROUTE_IDENTITY = (
    "tc_ref",
    "route_ref",
    "route_type",
    "execution_ref",
    "implementation_revision",
    "e2e_testware_ref",
    "testware_ref",
    "executor_owner",
    "selection_basis",
)
_AUXILIARY_IDENTITY = (
    "testware_ref",
    "executor_owner",
    "implementation_revision",
    "selection_basis",
    "completion_required",
    "execution_ref",
)


def _identity_key(entry: dict[str, Any], fields: tuple[str, ...]) -> str:
    values = [entry.get(field) for field in fields]
    try:
        return json.dumps(values, ensure_ascii=False, sort_keys=True, default=str)
    except (TypeError, ValueError):
        # 比較不能な値は例外にせず、文字列表現で別の識別子として扱う。
        return repr(values)


def _identity_counts(entries: list[dict[str, Any]], fields: tuple[str, ...]):
    counts: dict[str, int] = {}
    for entry in entries:
        key = _identity_key(entry, fields)
        counts[key] = counts.get(key, 0) + 1
    return counts


def _required_route_issues(routes: Any) -> list[str]:
    """Runのrequired routeの妥当性。D008とD018が同じ規則を使う。"""
    if not isinstance(routes, list) or not all(isinstance(r, dict) for r in routes):
        return ["required_routes_not_list_of_objects"]
    issues: list[str] = []
    seen: set[str] = set()
    for route in routes:
        kind = route.get("route_type")
        tc_ref = route.get("tc_ref")
        route_ref = route.get("route_ref")
        if not _in(kind, {"manual", "e2e", "testware"}):
            issues.append(f"invalid_required_route_type:{tc_ref}")
        if not _text(tc_ref) or not _text(route_ref):
            issues.append("missing_tc_or_route_ref")
        if kind == "e2e" and not _text(route.get("e2e_testware_ref")):
            issues.append(f"missing_e2e_testware_ref:{tc_ref}")
        if kind == "testware" and (
            not _text(route.get("testware_ref"))
            or route.get("executor_owner") != "testware-execution"
            or not _text(route.get("implementation_revision"))
            or not _text(route.get("selection_basis"))
        ):
            issues.append(f"invalid_testware_route:{tc_ref}")
        execution_ref = route.get("execution_ref")
        if execution_ref is not None and not _text(execution_ref):
            issues.append(f"invalid_execution_ref:{route_ref}")
        key = f"{tc_ref}|{route_ref}"
        if key in seen:
            issues.append(f"duplicate_required_route:{key}")
        seen.add(key)
    return issues


def _run_contract_issues(run: dict[str, Any]) -> list[str]:
    """保存済みRun自体の妥当性。不正なRunを正当な実施義務として受け入れない。"""
    issues = _required_route_issues(run.get("required_routes", []))
    issues += _auxiliary_run_issues(run)
    refs = run.get("auxiliary_testware_refs", [])
    if isinstance(refs, list):
        issues += [
            f"invalid_auxiliary_testware_ref:{index}"
            for index, ref in enumerate(refs)
            if not _text(ref)
        ]
    if run.get("route_contract_version") == ROUTE_CONTRACT_VERSION:
        issues += _auxiliary_count_issues(run, v2=True)
    return issues


def _start_flags(
    execution: dict[str, Any], declared: Any, *, require_revision: bool
) -> tuple[bool, bool]:
    """(sourceが開始済みと申告, 宣言revisionの確認を含めた実開始)を返す。"""
    raw = (
        execution.get("start_state") == "開始済み"
        and execution.get("actual_start_confirmed") is True
    )
    return raw, _source_started(execution, declared, require_revision=require_revision)


def _derive_activity_state(
    routes: list[dict[str, Any]],
    auxiliary: list[dict[str, Any]],
    source: dict[str, Any],
    cleanup: Any,
    *,
    unresolved: bool,
) -> str:
    """route・補助route・owner sourceからActivity状態を独立に再計算する。

    Activityが申告した`executed`・`blocked`・件数・状態は使わず、識別子（route種別・
    execution_ref・revision・実施義務）とownerのsourceだけから導く。`unresolved`は、
    Activityが申告した未解決項目の有無か、呼び出し側が確認したRun自体の不正の有無。
    """
    tc_exec_refs = {
        r.get("execution_ref") for r in routes if _text(r.get("execution_ref"))
    }
    seen: set[str] = set()
    # TCごとに(実開始, blocked, 結果確定・投影済み)のrouteを集める。
    by_tc: dict[str, list[tuple[bool, bool, bool]]] = {}
    started_cleanups: list[Any] = []
    route_executed = 0
    for route in routes:
        key = f"{route.get('tc_ref')}|{route.get('route_ref')}"
        if (
            key in seen
            or not _in(route.get("route_type"), {"manual", "e2e", "testware"})
            or not _text(route.get("tc_ref"))
            or not _text(route.get("route_ref"))
        ):
            unresolved = True
        seen.add(key)
        execution = _execution(source, route.get("execution_ref"))
        testware = route.get("route_type") == "testware"
        raw_started, executed = _start_flags(
            execution, route.get("implementation_revision"), require_revision=testware
        )
        if raw_started and not executed:
            unresolved = True
        blocked = not executed and (execution.get("blocked") is True or raw_started)
        done = bool(
            execution.get("result_finalized") is True
            and _text(execution.get("source_result"))
            and (
                not testware
                or (
                    execution.get("raw_capture_complete") is True
                    and _text(execution.get("attempt_ref"))
                )
            )
        )
        by_tc.setdefault(str(route.get("tc_ref")), []).append((executed, blocked, done))
        if executed:
            route_executed += 1
            started_cleanups.append(
                execution.get("cleanup_status", "未確認" if testware else "対象なし")
            )
    tc_states = [
        "executed"
        if all(executed for executed, _, _ in items)
        else ("blocked" if any(blocked for _, blocked, _ in items) else "unexecuted")
        for items in by_tc.values()
    ]
    # 実施義務のある補助だけを状態判定へ使う: (実開始, blocked, 完了)。
    required_aux: list[tuple[bool, bool, bool]] = []
    seen_aux: set[str] = set()
    for item in auxiliary:
        ref = item.get("testware_ref")
        if (
            not _text(ref)
            or ref in seen_aux
            or type(item.get("completion_required")) is not bool
        ):
            unresolved = True
        seen_aux.add(str(ref))
        execution = _execution(source, item.get("execution_ref"))
        required = item.get("completion_required") is True
        raw_started, executed = _start_flags(
            execution, item.get("implementation_revision"), require_revision=required
        )
        shared = _text(item.get("execution_ref")) and (
            item["execution_ref"] in tc_exec_refs
        )
        if shared or (raw_started and not executed):
            unresolved = True
        executed = executed and not shared
        if executed:
            started_cleanups.append(execution.get("cleanup_status", "未確認"))
        if required:
            blocked = not executed and (
                execution.get("blocked") is True or shared or raw_started
            )
            completed = bool(
                executed
                and execution.get("result_finalized") is True
                and _text(execution.get("source_result"))
                and execution.get("raw_capture_complete") is True
                and _text(execution.get("attempt_ref"))
                and _in(execution.get("cleanup_status", "未確認"), CLEANUP_CLOSED)
            )
            required_aux.append((executed, blocked, completed))
    started_units = route_executed + sum(executed for executed, _, _ in required_aux)
    bad_cleanup = any(
        not _in(value, CLEANUP_CLOSED) for value in [cleanup, *started_cleanups]
    )
    blocked_state = "部分完了（ブロック中あり）" if started_units else "ブロック中"
    if bad_cleanup or unresolved:
        return blocked_state
    if any(state != "executed" for state in tc_states) or any(
        not executed for executed, _, _ in required_aux
    ):
        if (
            not routes
            and not started_units
            and not any(blocked for _, blocked, _ in required_aux)
        ):
            return "未開始"
        return blocked_state
    if any(not done for items in by_tc.values() for _, _, done in items) or any(
        not completed for _, _, completed in required_aux
    ):
        return "実行中"
    return "完了" if routes or required_aux else "未開始"


def validate_activity_against_run(
    activity: dict[str, Any], run: Any
) -> list[dict[str, Any]]:
    """保存済みRunを正本として、Activityのroute集合と実施義務を照合する。

    Activity自身の`completion_required`や件数の申告は、Runのrequired route・
    `auxiliary_routes`と一致しない限り検証済みにしない。欠落・追加・重複・
    義務（`completion_required`・選定根拠・owner・revision）の変更を検出する。
    """
    if not isinstance(run, dict) or run.get("artifact_type") != "run":
        return [{"issue": "run_artifact_required"}]
    issues: list[dict[str, Any]] = []
    if run.get("route_contract_version") != ROUTE_CONTRACT_VERSION:
        issues.append({"issue": "run_not_contract_v2"})
    if (
        _text(activity.get("run_ref"))
        and _text(run.get("run_ref"))
        and activity["run_ref"] != run["run_ref"]
    ):
        issues.append({"issue": "run_ref_mismatch"})
    shapes = {
        "run_required_routes": run.get("required_routes", []),
        "run_auxiliary_routes": run.get("auxiliary_routes", []),
        "activity_route_results": activity.get("route_results", []),
        "activity_auxiliary_route_results": activity.get("auxiliary_route_results", []),
    }
    for name, value in shapes.items():
        if not isinstance(value, list) or not all(isinstance(v, dict) for v in value):
            issues.append({"issue": f"{name}_not_list_of_objects"})
    if issues and any(i["issue"].endswith("_not_list_of_objects") for i in issues):
        return issues
    # 保存済みRun自体が不正（未知のroute種別・識別子欠落・不正なowner等）なら、
    # 再投影が一致しても正当な実施義務としては受け入れない。
    run_issues = _run_contract_issues(run)
    if run_issues:
        issues.append({"issue": "run_contract_invalid", "detail": run_issues})
    run_refs = run.get("auxiliary_testware_refs", [])
    # 不正な補助ref（list・dict等）は集合へ入れず、上のRun不正として報告済みとする。
    covered = {
        e["testware_ref"]
        for e in shapes["run_auxiliary_routes"]
        if _text(e.get("testware_ref"))
    }
    # 旧形式のref（義務不明）もRunの補助として扱い、Activityが落とせないようにする。
    legacy_refs = [
        {"testware_ref": ref}
        for ref in (run_refs if isinstance(run_refs, list) else [])
        if _text(ref) and ref not in covered
    ]
    pairs = (
        (
            "required_route",
            shapes["run_required_routes"],
            shapes["activity_route_results"],
            _ROUTE_IDENTITY,
        ),
        (
            "auxiliary_route",
            [*shapes["run_auxiliary_routes"], *legacy_refs],
            shapes["activity_auxiliary_route_results"],
            _AUXILIARY_IDENTITY,
        ),
    )
    for kind, from_run, from_activity, fields in pairs:
        expected_counts = _identity_counts(from_run, fields)
        actual_counts = _identity_counts(from_activity, fields)
        for key, count in expected_counts.items():
            if actual_counts.get(key, 0) < count:
                issues.append(
                    {"issue": f"{kind}_missing_from_activity", "identity": key}
                )
        for key, count in actual_counts.items():
            if expected_counts.get(key, 0) < count:
                issues.append({"issue": f"{kind}_not_in_run", "identity": key})
        if any(c > 1 for c in [*expected_counts.values(), *actual_counts.values()]):
            issues.append({"issue": f"{kind}_duplicate"})
    # Activity状態は、Runのrouteと実施義務・activityのowner sourceだけから再計算する。
    source = activity.get("source_executions", {})
    source = source if isinstance(source, dict) else {}
    expected_state = _derive_activity_state(
        shapes["run_required_routes"],
        [*shapes["run_auxiliary_routes"], *legacy_refs],
        source,
        activity.get("cleanup_status"),
        unresolved=bool(run_issues) or bool(activity.get("unresolved")),
    )
    if activity.get("activity_state") != expected_state:
        issues.append(
            {
                "issue": "activity_state_mismatch",
                "expected": expected_state,
                "actual": activity.get("activity_state"),
            }
        )
    return issues


def validate(
    text: str,
    expected: dict[str, Any],
    eval_id: str,
    run: dict[str, Any] | None = None,
) -> EvalResult:
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
        _in(kind, {"baseline", "run", "activity"}),
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
            _in(item.get("decision"), valid_decisions)
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
        if not isinstance(baseline, dict):
            baseline = {}
        result.add(
            "REG-D006",
            scope != "full"
            or (
                baseline.get("complete") is True
                and baseline.get("currentness") == "current"
            ),
            "full Runはcompleteかつcurrentなbaselineだけから作ること",
        )
        selected = _ref_set(doc.get("selected_tc_refs", []))
        members = _ref_set(baseline.get("member_tc_refs", []))
        refs_valid = selected is not None and members is not None
        selected = selected or set()
        members = members or set()
        result.add(
            "REG-D007",
            refs_valid
            and selected <= members
            and (scope != "selected" or doc.get("suite_complete") is False),
            "selected RunはSuite memberのsubsetとして保持し、Suite完了と扱わないこと",
            evidence=sorted(selected - members)
            if refs_valid
            else "invalid_tc_ref_list",
        )
        route_issues = _required_route_issues(doc.get("required_routes", []))
        result.add(
            "REG-D008",
            not route_issues,
            "required routeをmanual・concrete E2E testware ref・実行owner / 実装revision付きtestwareで表すこと",
            evidence=route_issues or None,
        )
        auxiliary_issues = _auxiliary_run_issues(doc)
        auxiliary_issues += _auxiliary_count_issues(
            doc, v2=doc.get("route_contract_version") == ROUTE_CONTRACT_VERSION
        )
        result.add(
            "REG-D009",
            not auxiliary_issues,
            "TCなし補助testwareをTC countから分離し、今回Runの実施義務と選定根拠を保持すること",
            evidence=auxiliary_issues or None,
        )
    elif kind == "activity":
        v2 = doc.get("route_contract_version") == ROUTE_CONTRACT_VERSION
        unsupported_version = "route_contract_version" in doc and not v2
        shape_issues: list[dict[str, Any]] = []
        routes = _object_list(
            doc.get("route_results", []), "route_results", shape_issues
        )
        auxiliary = _object_list(
            doc.get("auxiliary_route_results", []),
            "auxiliary_route_results",
            shape_issues,
        )
        source = doc.get("source_executions", {})
        if not isinstance(source, dict):
            shape_issues.append({"issue": "source_executions_not_object"})
            source = {}
        tc_state = doc.get("tc_execution_state", {})
        if not isinstance(tc_state, dict):
            shape_issues.append({"issue": "tc_execution_state_not_object"})
            tc_state = {}
        counts = doc.get("counts", {})
        if not isinstance(counts, dict):
            shape_issues.append({"issue": "counts_not_object"})
            counts = {}
        by_tc: dict[str, list[dict[str, Any]]] = {}
        source_mismatches = []
        for route in routes:
            tc_ref = route.get("tc_ref")
            by_tc.setdefault(str(tc_ref), []).append(route)
            execution = _execution(source, route.get("execution_ref"))
            is_testware = route.get("route_type") == "testware"
            actual_started = _source_started(
                execution,
                route.get("implementation_revision"),
                require_revision=is_testware,
            )
            if route.get("executed") is not actual_started:
                source_mismatches.append(
                    {"tc_ref": tc_ref, "route_ref": route.get("route_ref")}
                )
            if v2:
                raw_started, _ = _start_flags(
                    execution,
                    route.get("implementation_revision"),
                    require_revision=is_testware,
                )
                expected_blocked = not actual_started and (
                    execution.get("blocked") is True or raw_started
                )
                if route.get("blocked") is not expected_blocked:
                    source_mismatches.append(
                        {"tc_ref": tc_ref, "issue": "blocked_not_projected"}
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
            if v2 and route.get("route_type") == "e2e":
                # E2E routeは実行対象のtestware参照をRunから保持する。
                if not _text(route.get("e2e_testware_ref")):
                    source_mismatches.append(
                        {"tc_ref": tc_ref, "issue": "e2e_testware_ref_missing"}
                    )
            if v2 and is_testware:
                # testware routeはRunの選定情報（testware・owner・選定根拠）を保持する。
                if (
                    not _text(route.get("testware_ref"))
                    or route.get("executor_owner") != "testware-execution"
                    or not _text(route.get("selection_basis"))
                ):
                    source_mismatches.append(
                        {"tc_ref": tc_ref, "issue": "testware_selection_missing"}
                    )
                # testware routeはattempt・raw取得・cleanupもownerのsourceから投影する。
                for field, value in (
                    ("attempt_ref", execution.get("attempt_ref")),
                    (
                        "raw_capture_complete",
                        execution.get("raw_capture_complete") is True,
                    ),
                    ("cleanup_status", execution.get("cleanup_status", "未確認")),
                ):
                    if route.get(field) != value:
                        source_mismatches.append(
                            {"tc_ref": tc_ref, "issue": f"{field}_not_projected"}
                        )
        state_errors = []
        derived_states: dict[str, str] = {}
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
            derived_states[tc_ref] = expected_state
            if tc_state.get(tc_ref) != expected_state:
                state_errors.append({"tc_ref": tc_ref, "expected": expected_state})
        if v2:
            # routeを持たないTCの状態を足して件数だけ増やす改ざんを検出する。
            state_errors += [
                {"tc_ref": tc_ref, "issue": "state_without_route"}
                for tc_ref in tc_state
                if tc_ref not in by_tc
            ]
        result.add(
            "REG-D010",
            not source_mismatches and not state_errors and not shape_issues,
            "source actual start/resultをそのまま投影し、全required route開始後だけlogical TCをexecutedにすること",
            evidence={
                "source_mismatches": source_mismatches,
                "state_errors": state_errors,
                "shape_issues": shape_issues,
            },
        )
        cleanup = doc.get("cleanup_status")
        expected_state = doc.get("activity_state")
        tc_execution_refs = {
            route.get("execution_ref")
            for route in routes
            if _text(route.get("execution_ref"))
        }

        def shared_with_tc(item: dict[str, Any]) -> bool:
            ref = item.get("execution_ref")
            return _text(ref) and ref in tc_execution_refs

        def route_complete(route: dict[str, Any]) -> bool:
            execution = _execution(source, route.get("execution_ref"))
            is_testware = route.get("route_type") == "testware"
            return bool(
                _source_started(
                    execution,
                    route.get("implementation_revision"),
                    require_revision=is_testware,
                )
                and route.get("executed") is True
                and route.get("result_finalized") is True
                and route.get("source_result_projectable") is True
                and isinstance(route.get("source_result"), str)
                and bool(route.get("source_result", "").strip())
                and route.get("source_result") == execution.get("source_result")
                and execution.get("result_finalized") is True
                and (
                    not is_testware
                    or (
                        execution.get("raw_capture_complete") is True
                        and _text(execution.get("attempt_ref"))
                        and route.get("raw_capture_complete") is True
                        and route.get("attempt_ref") == execution.get("attempt_ref")
                    )
                )
            )

        def auxiliary_complete(item: dict[str, Any]) -> bool:
            execution = _execution(source, item.get("execution_ref"))
            return bool(
                not shared_with_tc(item)
                and _source_started(
                    execution,
                    item.get("implementation_revision"),
                    require_revision=True,
                )
                and execution.get("result_finalized") is True
                and _text(execution.get("source_result"))
                and item.get("source_result") == execution.get("source_result")
                and execution.get("raw_capture_complete") is True
                and _text(execution.get("attempt_ref"))
                and item.get("attempt_ref") == execution.get("attempt_ref")
                and _in(execution.get("cleanup_status", "未確認"), CLEANUP_CLOSED)
            )

        required_auxiliary = [
            item for item in auxiliary if item.get("completion_required") is True
        ]
        obligation_unknown = [
            item.get("testware_ref")
            for item in auxiliary
            if type(item.get("completion_required")) is not bool
        ]
        if v2:
            started_cleanups = [
                _execution(source, route.get("execution_ref")).get(
                    "cleanup_status",
                    "未確認" if route.get("route_type") == "testware" else "対象なし",
                )
                for route in routes
                if route.get("executed") is True
            ] + [
                _execution(source, item.get("execution_ref")).get(
                    "cleanup_status", "未確認"
                )
                for item in auxiliary
                if item.get("executed") is True
            ]
            completion_valid = expected_state != "完了" or (
                (bool(routes) or bool(required_auxiliary))
                and all(route_complete(route) for route in routes)
                and all(auxiliary_complete(item) for item in required_auxiliary)
                and not obligation_unknown
                and _in(cleanup, CLEANUP_CLOSED)
                and all(_in(value, CLEANUP_CLOSED) for value in started_cleanups)
                and not doc.get("unresolved")
                and not shape_issues
            )
        else:
            # 旧Activityは読取互換のため、TC routeだけを根拠にした従来規則で検証する。
            # route_contract_versionが存在するのに未対応の値の場合は旧形式と見なさず拒否する。
            completion_valid = expected_state != "完了" or (
                not unsupported_version
                and not shape_issues
                and bool(routes)
                and all(
                    route.get("executed") is True
                    and route.get("result_finalized") is True
                    and route.get("source_result_projectable") is True
                    and isinstance(route.get("source_result"), str)
                    and bool(route.get("source_result", "").strip())
                    and route.get("source_result")
                    == _execution(source, route.get("execution_ref")).get(
                        "source_result"
                    )
                    and _execution(source, route.get("execution_ref")).get(
                        "result_finalized"
                    )
                    is True
                    for route in routes
                )
                and _in(cleanup, CLEANUP_CLOSED)
                and not doc.get("unresolved")
            )
        state_evidence: dict[str, Any] | None = None
        if v2:
            # 申告された状態は、sourceから独立に再計算した状態と一致しなければならない。
            # 完了以外の状態でも、実際は完了済みのActivityを実行中等へ改ざんできない。
            derived_state = _derive_activity_state(
                routes,
                auxiliary,
                source,
                cleanup,
                unresolved=bool(doc.get("unresolved")) or bool(shape_issues),
            )
            state_evidence = {"expected": derived_state, "actual": expected_state}
            completion_valid = completion_valid and derived_state == expected_state
        result.add(
            "REG-D011",
            completion_valid,
            "required TC routeと実施義務のある補助routeの実開始・owner result確定・raw結果投影・cleanup・義務不明なしをsourceから確認できない限りActivityを完了にせず、申告された状態がsourceから再計算した状態と一致すること",
            evidence=state_evidence,
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
        aux_issues += shape_issues
        if unsupported_version:
            aux_issues.append({"issue": "unsupported_route_contract_version"})
        if counts.get("auxiliary_testware_count") != len(auxiliary):
            aux_issues.append({"issue": "auxiliary_count_mismatch"})
        if v2:
            for item in auxiliary:
                execution = _execution(source, item.get("execution_ref"))
                ref = item.get("testware_ref")
                if shared_with_tc(item):
                    aux_issues.append(
                        {"testware_ref": ref, "issue": "execution_shared_with_tc"}
                    )
                raw_started, base_executed = _start_flags(
                    execution,
                    item.get("implementation_revision"),
                    require_revision=item.get("completion_required") is True,
                )
                aux_executed = base_executed and not shared_with_tc(item)
                expected_projection = {
                    "executed": aux_executed,
                    "blocked": not aux_executed
                    and (
                        execution.get("blocked") is True
                        or shared_with_tc(item)
                        or raw_started
                    ),
                    "result_finalized": execution.get("result_finalized") is True,
                    "raw_capture_complete": execution.get("raw_capture_complete")
                    is True,
                    "attempt_ref": execution.get("attempt_ref"),
                    "source_result": execution.get("source_result"),
                    "cleanup_status": execution.get("cleanup_status", "未確認"),
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
            auxiliary_result_counts: dict[str, int] = {}
            for item in auxiliary:
                value = item.get("source_result")
                if item.get("executed") is True and _text(value):
                    auxiliary_result_counts[value] = (
                        auxiliary_result_counts.get(value, 0) + 1
                    )
            # 件数は元のrouteとsourceから独立に再計算し、公開された全件数と照合する。
            expected_counts = {
                "tc_member_count": len(by_tc),
                "executed_tc_count": sum(
                    all(route.get("executed") is True for route in tc_routes)
                    for tc_routes in by_tc.values()
                ),
                "unexecuted_tc_count": sum(
                    state == "unexecuted" for state in derived_states.values()
                ),
                "blocked_tc_count": sum(
                    state == "blocked" for state in derived_states.values()
                ),
                "source_result_counts": tc_result_counts,
                "auxiliary_executed_count": sum(
                    item.get("executed") is True for item in auxiliary
                ),
                "auxiliary_source_result_counts": auxiliary_result_counts,
                "auxiliary_required_count": len(required_auxiliary),
                "auxiliary_required_completed_count": sum(
                    auxiliary_complete(item) for item in required_auxiliary
                ),
                "auxiliary_obligation_unknown_count": len(obligation_unknown),
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
        # 保存済みRunを正本として、route集合・実施義務をActivityと照合する。
        run_artifact = run if run is not None else expected.get("run")
        if not v2:
            result.add(
                "REG-D018",
                True,
                "v2 Activityのrouteと実施義務を保存済みRunと照合すること（旧形式は対象外）",
                evidence="legacy_activity",
            )
        elif run_artifact is None:
            # Run無しではActivity自身の申告を検証済みとしない。完了の主張は拒否する。
            result.add(
                "REG-D018",
                False,
                "v2 Activityのrouteと実施義務を保存済みRunと照合すること",
                severity="error" if expected_state == "完了" else "warning",
                evidence=["run_not_supplied_activity_obligations_unverified"],
            )
        else:
            run_issues = validate_activity_against_run(doc, run_artifact)
            result.add(
                "REG-D018",
                not run_issues,
                "v2 Activityのrouteと実施義務を保存済みRunと照合すること",
                evidence=run_issues or None,
            )
    expected_kind = expected.get("artifact_type")
    fixture_ok = not expected_kind or kind == expected_kind
    fixture_evidence: dict[str, Any] = {"expected": expected_kind, "actual": kind}
    if kind == "activity":
        # fixtureが指定した場合だけ、期待するActivity状態と実施義務のある補助refを照合する。
        if "activity_state" in expected:
            fixture_evidence["expected_activity_state"] = expected["activity_state"]
            fixture_evidence["actual_activity_state"] = doc.get("activity_state")
            fixture_ok = fixture_ok and (
                doc.get("activity_state") == expected["activity_state"]
            )
        if "required_auxiliary_refs" in expected:
            aux_items = doc.get("auxiliary_route_results", [])
            actual_required = (
                sorted(
                    str(item.get("testware_ref"))
                    for item in aux_items
                    if isinstance(item, dict)
                    and item.get("completion_required") is True
                )
                if isinstance(aux_items, list)
                else []
            )
            expected_required = sorted(map(str, expected["required_auxiliary_refs"]))
            fixture_evidence["expected_required_auxiliary_refs"] = expected_required
            fixture_evidence["actual_required_auxiliary_refs"] = actual_required
            fixture_ok = fixture_ok and actual_required == expected_required
    result.add(
        "REG-D014",
        fixture_ok,
        "fixtureが指定したartifact kind・Activity状態・実施義務のある補助refと一致すること",
        evidence=fixture_evidence,
    )
    return result
