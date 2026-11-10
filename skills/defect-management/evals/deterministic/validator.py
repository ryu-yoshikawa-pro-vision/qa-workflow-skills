from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any

from scripts.skills.evals.deterministic.result import EvalResult

CLEANUP_CLOSED = {"成功", "対象なし", "意図的に残した状態"}
OPERATIONS = {"create", "comment", "update", "link", "close", "reopen"}
CONDITIONAL = {"update", "link", "close", "reopen"}
_SECRET = re.compile(
    r"(?i)(?:password|passwd|(?:access[_-]?|auth[_-]?|refresh[_-]?)?token|client[_-]?secret|api[_-]?key|cookie|storage[_-]?state|authorization)\s*[:=]\s*['\"]?(?:bearer\s+)?[A-Za-z0-9_./+=-]{8,}"
)


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


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _instant(value: Any) -> datetime | None:
    if not _text(value):
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _strings(value: Any):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _strings(item)


def _candidate(doc: dict[str, Any], result: EvalResult) -> None:
    candidate = doc.get("candidate") if isinstance(doc.get("candidate"), dict) else {}
    facts = (
        doc.get("candidate_input")
        if isinstance(doc.get("candidate_input"), dict)
        else {}
    )
    ready_facts = (
        facts.get("cause_status") == "confirmed"
        and _text(facts.get("basis_ref"))
        and _text(facts.get("basis_revision"))
        and bool(facts.get("evidence_refs"))
        and facts.get("result_finalized") is True
    )
    state = candidate.get("candidate_state")
    result.add(
        "DEF-D003",
        state
        in {"ready_for_external_handoff", "needs_owner_analysis", "needs_spec_basis"}
        and (state == "ready_for_external_handoff") == bool(ready_facts),
        "原因確定・期待結果根拠・証拠・元結果の確定が揃う場合だけ外部引継ぎ可能な候補にすること",
        evidence={"state": state, "ready_by_input_facts": bool(ready_facts)},
    )
    result.add(
        "DEF-D004",
        candidate.get("automatic_registration") is False
        and candidate.get("formal_defect") is False
        and str(candidate.get("candidate_ref", "")).startswith("DEFC-"),
        "FAIL / Finding / Observationを自動的に正式Defectへ登録せず、候補refを持つこと",
    )
    returned_ok = state == "ready_for_external_handoff" or (
        isinstance(candidate.get("return_to"), dict)
        and bool(candidate["return_to"])
        and bool(candidate.get("reasons"))
        and (
            state != "needs_owner_analysis"
            or candidate["return_to"].get("owner") == facts.get("owner_skill")
        )
        and (
            state != "needs_spec_basis"
            or candidate["return_to"].get("spec") == "spec-analysis"
        )
    )
    result.add(
        "DEF-D005",
        returned_ok,
        "未成熟な候補は理由と戻し先（元の実行ownerまたはspec-analysis）を持つこと",
    )


def _operation(doc: dict[str, Any], result: EvalResult) -> None:
    plan = doc.get("plan") if isinstance(doc.get("plan"), dict) else {}
    ctx = doc.get("context") if isinstance(doc.get("context"), dict) else {}
    outcome = doc.get("outcome") if isinstance(doc.get("outcome"), dict) else None
    operation = plan.get("operation")
    decision = plan.get("decision")
    approval = ctx.get("approval") if isinstance(ctx.get("approval"), dict) else {}
    fix = (
        ctx.get("fix_verification")
        if isinstance(ctx.get("fix_verification"), dict)
        else {}
    )
    now, expires = _instant(ctx.get("now")), _instant(approval.get("expires_at"))
    issued = _instant(approval.get("issued_at"))
    authorized = (
        approval.get("source") == "trusted_approval_service"
        and approval.get("authentication_verified") is True
        and approval.get("binding_matches") is True
        and approval.get("revoked") is not True
        and all(
            _text(approval.get(k)) for k in ("principal", "role", "policy_revision")
        )
        and now is not None
        and expires is not None
        and issued is not None
        and issued <= now < expires
    )
    result.add(
        "DEF-D006",
        operation in OPERATIONS
        and decision
        in {
            "allow",
            "blocked",
            "read_only",
            "reconfirm",
            "reconcile_first",
            "already_applied",
        }
        and str(plan.get("operation_id", "")).startswith("DEFOP-"),
        "外部操作が既知のoperation・decisionとoperation identityを持つこと",
    )
    allowed_ok = decision != "allow" or (
        authorized
        and ctx.get("write_permission") is True
        and ctx.get("candidate_state") == "ready_for_external_handoff"
        and plan.get("requires_readback") is True
    )
    result.add(
        "DEF-D007",
        allowed_ok,
        "外部更新のallowは、信頼できるサービスで認証・対象束縛・有効期間内の承認、書込み権限、成熟した候補、readback要件が揃う場合だけであること",
    )
    create_ok = (
        decision != "allow"
        or operation != "create"
        or ctx.get("duplicate_check") == "no_match"
    )
    conditional_ok = (
        decision != "allow"
        or operation not in CONDITIONAL
        or (
            ctx.get("conditional_update") is True
            and ctx.get("issue_revision_fresh") is True
        )
    )
    result.add(
        "DEF-D008",
        create_ok and conditional_ok,
        "登録は完全な重複照合の結果が重複なし、更新はexpected revisionが最新の条件付き更新でだけ許可すること",
    )
    close_ok = (
        decision != "allow"
        or operation != "close"
        or (
            fix.get("status") == "fix_confirmed"
            and _text(plan.get("candidate_ref"))
            and fix.get("candidate_ref") == plan.get("candidate_ref")
            and _text(fix.get("verified_target_ref"))
            and fix.get("verified_target_ref") == ctx.get("fix_target_ref")
            and fix.get("verified_target_ref") != ctx.get("observed_target_ref")
            and fix.get("result_finalized") is True
            and fix.get("cleanup_status") in CLEANUP_CLOSED
        )
    )
    result.add(
        "DEF-D009",
        close_ok,
        "closeは元ownerが修正対象buildで確定したfix_confirmedとcleanup確認がある場合だけ許可すること",
    )
    retry_ok = not (
        decision == "allow"
        and operation in {"create", "comment"}
        and ctx.get("atomic_dedupe") is not True
        and plan.get("auto_retry_allowed") is not False
    )
    result.add(
        "DEF-D010",
        retry_ok,
        "原子的な重複防止がない登録・コメントを自動再試行させないこと",
    )
    outcome_ok = True
    if outcome is not None:
        applied = outcome.get("status") == "applied"
        outcome_ok = (
            outcome.get("external_update_performed") is applied
            and (
                not applied
                or (outcome.get("readback_verified") is True and decision == "allow")
            )
            and (decision == "allow" or outcome.get("status") == "not_attempted")
            and (
                ctx.get("write_permission") is True
                or outcome.get("external_update_performed") is False
            )
        )
    result.add(
        "DEF-D011",
        outcome_ok,
        "外部更新の成功表示は独立readbackとallowを伴い、許可のない操作を実施済みと報告しないこと",
    )


def _fix(doc: dict[str, Any], result: EvalResult) -> None:
    request = doc.get("request") if isinstance(doc.get("request"), dict) else {}
    outcome = doc.get("result") if isinstance(doc.get("result"), dict) else None
    ready = request.get("status") == "request_ready"
    request_ok = request.get("status") in {"request_ready", "blocked"} and (
        not ready
        or (
            _text(request.get("fix_target_ref"))
            and request.get("fix_target_ref") != request.get("observed_target_ref")
            and request.get("send_to") == request.get("original_owner_skill")
            and bool(request.get("change_refs"))
            and request.get("notice_is_confirmation") is False
            and request.get("regression_selection_owner") == "regression-testing"
        )
    )
    result.add(
        "DEF-D012",
        request_ok,
        "修正確認依頼は、観測時と異なる特定済みの修正対象と変更refを持ち、元の実行ownerへ向け、通知を確認扱いにしないこと",
    )
    result_ok = True
    if outcome is not None:
        confirmed = outcome.get("status") == "fix_confirmed"
        required = {
            (t.get("ref"), t.get("revision"))
            for t in request.get("verification_targets", [])
            if isinstance(t, dict)
        }
        executed = outcome.get("executed_targets")
        executed_set = (
            {(t.get("ref"), t.get("revision")) for t in executed if isinstance(t, dict)}
            if isinstance(executed, list)
            else set()
        )
        result_ok = ready and (
            not confirmed
            or (
                bool(required)
                and executed_set == required
                and outcome.get("candidate_ref") == request.get("candidate_ref")
                and outcome.get("target_ref") == request.get("fix_target_ref")
                and outcome.get("owner_skill") == request.get("send_to")
                and outcome.get("actual_start_confirmed") is True
                and outcome.get("result_finalized") is True
                and outcome.get("cleanup_status") in CLEANUP_CLOSED
            )
        )
    result.add(
        "DEF-D013",
        result_ok,
        "fix_confirmedは依頼対象のbuildで、依頼した全testwareを指定revisionで、ownerが開始・確定・cleanup確認した結果だけであること",
    )


def _tracking(doc: dict[str, Any], result: EvalResult) -> None:
    record = doc.get("record") if isinstance(doc.get("record"), dict) else {}
    closure = doc.get("closure") if isinstance(doc.get("closure"), dict) else {}
    submission = (
        record.get("submission") if isinstance(record.get("submission"), dict) else {}
    )
    issue = (
        submission.get("external_issue")
        if isinstance(submission.get("external_issue"), dict)
        else {}
    )
    fix = (
        record.get("fix_verification")
        if isinstance(record.get("fix_verification"), dict)
        else {}
    )
    if submission.get("status") == "withheld":
        expected = _text(submission.get("withheld_reason")) and _text(
            submission.get("decided_by")
        )
    elif submission.get("status") == "registered":
        expected = (
            all(_text(issue.get(k)) for k in ("issue_ref", "revision", "retrieved_at"))
            and record.get("external_confirmation") == "current"
            and fix.get("status") == "fix_confirmed"
        )
    else:
        expected = False
    result.add(
        "DEF-D014",
        closure.get("closed") is bool(expected)
        and (bool(expected) or bool(closure.get("open_items"))),
        "追跡の閉鎖は、保留の理由・決定者、または登録済みIssueの参照・現在性・修正確認から導出され、未完了項目を列挙すること",
    )


def validate(text: str, expected: dict[str, Any], eval_id: str) -> EvalResult:
    result = EvalResult("defect-management", eval_id)
    doc, errors = _document(text)
    result.add(
        "DEF-D001",
        doc is not None,
        "正規JSON artifactが一つだけ整形式で存在すること",
        evidence=errors or None,
    )
    if doc is None:
        return result
    kind = doc.get("artifact_type")
    result.add(
        "DEF-D002",
        kind
        in {
            "candidate_assessment",
            "external_operation",
            "fix_verification",
            "tracking",
        }
        and doc.get("schema_version") == "1"
        and (not expected.get("artifact_type") or kind == expected["artifact_type"]),
        "artifact typeがdata contractの種別であり、fixtureの期待種別と一致すること",
        evidence={"actual": kind, "expected": expected.get("artifact_type")},
    )
    if kind == "candidate_assessment":
        _candidate(doc, result)
    elif kind == "external_operation":
        _operation(doc, result)
    elif kind == "fix_verification":
        _fix(doc, result)
    elif kind == "tracking":
        _tracking(doc, result)
    result.add(
        "DEF-D015",
        not any(_SECRET.search(item) for item in _strings(doc)),
        "secret・cookie・token等の実値を成果物へ転載しないこと",
    )
    for key, assertion_id, message in (
        ("expected_decision", "DEF-D016", "fixtureが期待するdecisionと一致すること"),
        (
            "expected_candidate_state",
            "DEF-D017",
            "fixtureが期待する候補stateと一致すること",
        ),
        (
            "expected_request_status",
            "DEF-D018",
            "fixtureが期待する修正確認依頼のstatusと一致すること",
        ),
    ):
        if key in expected:
            actual = (
                (doc.get("plan") or {}).get("decision")
                if key == "expected_decision"
                else (doc.get("candidate") or {}).get("candidate_state")
                if key == "expected_candidate_state"
                else (doc.get("request") or {}).get("status")
            )
            result.add(
                assertion_id,
                actual == expected[key],
                message,
                evidence={"expected": expected[key], "actual": actual},
            )
    return result
