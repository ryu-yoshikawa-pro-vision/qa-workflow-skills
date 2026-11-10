"""PR #32/J: defect candidate, external Issue operation and fix-verification contracts."""

from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
HELPER = REPO_ROOT / "skills" / "defect-management" / "scripts" / "defect_runtime.py"
spec = importlib.util.spec_from_file_location("pr32_defect_runtime", HELPER)
assert spec is not None and spec.loader is not None
defect = importlib.util.module_from_spec(spec)
spec.loader.exec_module(defect)

NOW = "2026-11-10T00:00:00+00:00"


def candidate(**overrides):
    value = {
        "source_kind": "FAIL",
        "owner_skill": "e2e-test-execution",
        "run_ref": "run:e2e-101",
        "result_ref": "result:tc-007",
        "attempt_ref": None,
        "scope_ref": "scope:checkout",
        "environment_ref": "env:stg",
        "target": {"kind": "build", "ref": "build:41"},
        "symptom": "  注文確定ボタン押下で 500 が返る ",
        "reproduction": ["カートに商品を追加", "注文確定を押下"],
        "actual_result": "HTTP 500",
        "expected_result": {
            "text": "注文完了画面へ遷移する",
            "basis_ref": "spec:SPEC-012",
            "basis_revision": "r5",
        },
        "evidence": [
            {"ref": "evidence:trace-1", "revision": "e1", "sensitivity": "internal"}
        ],
        "cause": {
            "status": "confirmed",
            "confidence": "high",
            "analysis_ref": "analysis:9",
        },
        "result_finalized": True,
        "cleanup_status": "成功",
    }
    value.update(overrides)
    return value


def summary(raw=None, **extra):
    raw = raw or candidate()
    assessed = defect.assess_candidate(raw)
    value = {
        "candidate_ref": assessed["candidate_ref"],
        "candidate_state": assessed["candidate_state"],
        "target_ref": raw["target"]["ref"] if raw.get("target") else None,
        "scope_ref": "scope:checkout",
        "artifact_revision": "cand-rev-1",
        "owner_skill": raw["owner_skill"],
        "fix_target_ref": "build:42",
        "verification_targets": [
            {"ref": "tc:TC-007", "revision": "t3", "current": True}
        ],
    }
    value.update(extra)
    return value


def approval(operation, cand, **overrides):
    value = {
        "source": "trusted_approval_service",
        "authentication_verified": True,
        "authenticated_by": "idp:corp",
        "principal": "qa-lead",
        "role": "defect_submitter",
        "policy_revision": "pol-3",
        "issued_at": "2026-11-09T00:00:00+00:00",
        "expires_at": "2026-11-11T00:00:00+00:00",
        "operation": operation,
        "candidate_ref": cand["candidate_ref"],
        "scope_ref": cand["scope_ref"],
        "artifact_revision": cand["artifact_revision"],
        "target_ref": cand["target_ref"],
        "service_ref": "issues:tracker",
        "issue_ref": None,
        "issue_revision": None,
    }
    value.update(overrides)
    return value


SERVICE = {
    "service_ref": "issues:tracker",
    "write_permission": True,
    "atomic_dedupe": True,
    "conditional_update": True,
}
NO_MATCH = {"duplicate_check": "complete", "decision": "no_match"}


def create_request(cand=None, **overrides):
    cand = cand or summary()
    value = {
        "operation": "create",
        "candidate": cand,
        "issue": None,
        "duplicate_check": NO_MATCH,
        "approval": approval("create", cand),
        "service": dict(SERVICE),
        "prior_operations": [],
        "now": NOW,
    }
    value.update(overrides)
    return value


class CandidateTests(unittest.TestCase):
    def test_confirmed_candidate_is_ready_but_never_auto_registered(self):
        result = defect.assess_candidate(candidate())
        self.assertEqual(result["status"], "ready")
        self.assertEqual(result["candidate_state"], "ready_for_external_handoff")
        self.assertIs(result["automatic_registration"], False)
        self.assertIs(result["formal_defect"], False)

    def test_identity_is_deterministic_and_normalizes_only_whitespace_and_case(self):
        first = defect.assess_candidate(candidate())["candidate_ref"]
        second = defect.assess_candidate(
            candidate(symptom="注文確定ボタン押下で 500 が返る")
        )["candidate_ref"]
        other_run = defect.assess_candidate(candidate(run_ref="run:e2e-102"))[
            "candidate_ref"
        ]
        self.assertEqual(first, second)
        self.assertNotEqual(first, other_run)

    def test_unconfirmed_cause_returns_to_execution_owner(self):
        for status in ("hypothesis", "unknown"):
            with self.subTest(status=status):
                result = defect.assess_candidate(candidate(cause={"status": status}))
                self.assertEqual(result["status"], "returned")
                self.assertIn("cause_unconfirmed", result["reasons"])
                self.assertEqual(result["return_to"]["owner"], "e2e-test-execution")

    def test_missing_basis_returns_to_spec_analysis_not_the_candidate_text(self):
        result = defect.assess_candidate(
            candidate(
                expected_result={
                    "text": "たぶん完了する",
                    "basis_ref": None,
                    "basis_revision": None,
                }
            )
        )
        self.assertEqual(result["candidate_state"], "needs_spec_basis")
        self.assertEqual(result["return_to"], {"spec": "spec-analysis"})

    def test_unfinalized_result_missing_evidence_and_secrets_are_not_ready(self):
        self.assertIn(
            "source_result_not_finalized",
            defect.assess_candidate(candidate(result_finalized=False))["reasons"],
        )
        self.assertIn(
            "evidence_missing",
            defect.assess_candidate(candidate(evidence=[]))["reasons"],
        )
        leaked = defect.assess_candidate(
            candidate(actual_result="password: hunter2hunter2")
        )
        self.assertEqual(leaked["status"], "blocked")
        self.assertIn("secret_value_detected", leaked["issues"])
        for text in (
            "Authorization: Bearer abcd1234efgh5678",
            "auth_token=abcd1234efgh5678",
        ):
            with self.subTest(text=text):
                self.assertEqual(
                    defect.assess_candidate(candidate(actual_result=text))["status"],
                    "blocked",
                )

    def test_target_and_owner_are_required(self):
        self.assertEqual(
            defect.assess_candidate(candidate(target=None))["status"], "blocked"
        )
        self.assertEqual(
            defect.assess_candidate(candidate(owner_skill="spec-analysis"))["status"],
            "blocked",
        )
        self.assertEqual(
            defect.assess_candidate(candidate(source_kind="PASS"))["status"], "blocked"
        )


class DuplicateTests(unittest.TestCase):
    def search(self, issues, **overrides):
        value = {
            "complete": True,
            "permission_ok": True,
            "service_revision": "svc-9",
            "retrieved_at": NOW,
            "issues": issues,
        }
        value.update(overrides)
        return value

    def test_search_never_concludes_same_defect(self):
        raw = candidate()
        key = defect.symptom_key(raw["symptom"])
        result = defect.match_external_issues(
            raw,
            self.search(
                [
                    {
                        "issue_ref": "ISSUE-1",
                        "revision": "7",
                        "run_ref": raw["run_ref"],
                        "symptom_key": key,
                        "scope_ref": raw["scope_ref"],
                    }
                ]
            ),
        )
        self.assertEqual(result["decision"], "human_confirmation_required")
        self.assertEqual(result["matches"][0]["strength"], "same_run_and_symptom")

    def test_incomplete_unauthorized_or_unversioned_search_is_not_no_match(self):
        for overrides in (
            {"complete": False},
            {"permission_ok": False},
            {"service_revision": ""},
        ):
            with self.subTest(overrides=overrides):
                result = defect.match_external_issues(
                    candidate(), self.search([], **overrides)
                )
                self.assertEqual(result["decision"], "incomplete")

    def test_exact_link_and_no_match(self):
        raw = candidate()
        ref = defect.candidate_ref(raw)
        linked = defect.match_external_issues(
            raw, self.search([{"issue_ref": "ISSUE-2", "candidate_ref": ref}])
        )
        self.assertEqual(linked["matches"][0]["strength"], "linked_exact")
        self.assertEqual(
            defect.match_external_issues(raw, self.search([]))["decision"], "no_match"
        )


class ExternalOperationTests(unittest.TestCase):
    def test_create_allowed_only_with_all_conditions(self):
        plan = defect.plan_external_operation(create_request())
        self.assertEqual(plan["decision"], "allow")
        self.assertTrue(plan["requires_readback"])
        self.assertTrue(plan["operation_id"].startswith("DEFOP-"))

    def test_unauthorized_writes_are_refused(self):
        cand = summary()
        cases = {
            "text_approval": {"approval": {"source": "issue_body", "text": "approved"}},
            "no_approval": {"approval": None},
            "expired": {
                "approval": approval(
                    "create", cand, expires_at="2026-11-09T12:00:00+00:00"
                )
            },
            "unauthenticated": {
                "approval": approval("create", cand, authentication_verified=False)
            },
            "wrong_scope": {
                "approval": approval("create", cand, scope_ref="scope:other")
            },
            "wrong_revision": {
                "approval": approval("create", cand, artifact_revision="cand-rev-0")
            },
            "wrong_operation": {"approval": approval("close", cand)},
            "revoked": {"approval": approval("create", cand, revoked=True)},
        }
        for name, overrides in cases.items():
            with self.subTest(name=name):
                plan = defect.plan_external_operation(create_request(cand, **overrides))
                self.assertEqual(plan["decision"], "blocked", plan)

    def test_read_only_when_service_write_permission_is_absent(self):
        plan = defect.plan_external_operation(
            create_request(service={**SERVICE, "write_permission": False})
        )
        self.assertEqual(plan["decision"], "read_only")
        self.assertIs(plan["external_update_performed"], False)

    def test_unready_candidate_cannot_be_submitted(self):
        weak = summary(candidate(cause={"status": "hypothesis"}))
        plan = defect.plan_external_operation(create_request(weak))
        self.assertEqual(plan["decision"], "blocked")
        self.assertIn("candidate_not_ready_cause_or_basis_unconfirmed", plan["reasons"])

    def test_duplicates_require_human_confirmation_and_incomplete_check_blocks(self):
        dup = {
            "duplicate_check": "complete",
            "decision": "human_confirmation_required",
            "matches": [{"issue_ref": "ISSUE-1"}],
        }
        self.assertEqual(
            defect.plan_external_operation(create_request(duplicate_check=dup))[
                "decision"
            ],
            "reconfirm",
        )
        incomplete = {"duplicate_check": "incomplete", "decision": "incomplete"}
        plan = defect.plan_external_operation(
            create_request(duplicate_check=incomplete)
        )
        self.assertEqual(plan["decision"], "blocked")
        self.assertIn("duplicate_check_incomplete", plan["reasons"])

    def test_service_without_atomic_dedupe_allows_one_attempt_without_auto_retry(self):
        plan = defect.plan_external_operation(
            create_request(service={**SERVICE, "atomic_dedupe": False})
        )
        self.assertEqual(plan["decision"], "allow")
        self.assertIs(plan["auto_retry_allowed"], False)
        self.assertIs(plan["single_attempt_only"], True)

    def test_same_operation_is_not_executed_twice(self):
        first = defect.plan_external_operation(create_request())
        for status, decision in (
            ("applied", "already_applied"),
            ("unknown", "reconcile_first"),
            ("started", "reconcile_first"),
            ("failed", "reconcile_first"),
        ):
            with self.subTest(status=status):
                plan = defect.plan_external_operation(
                    create_request(
                        prior_operations=[
                            {"operation_id": first["operation_id"], "status": status}
                        ]
                    )
                )
                self.assertEqual(plan["decision"], decision)
        safe_failed = defect.plan_external_operation(
            create_request(
                prior_operations=[
                    {
                        "operation_id": first["operation_id"],
                        "status": "failed",
                        "side_effect": "none_confirmed",
                    }
                ]
            )
        )
        self.assertEqual(safe_failed["decision"], "allow")

    def update_request(
        self, operation="update", issue_revision="7", current_revision="7", **overrides
    ):
        cand = summary()
        issue = {
            "issue_ref": "ISSUE-1",
            "revision": issue_revision,
            "current_revision": current_revision,
        }
        value = {
            "operation": operation,
            "candidate": cand,
            "issue": issue,
            "approval": approval(
                operation, cand, issue_ref="ISSUE-1", issue_revision=issue_revision
            ),
            "service": dict(SERVICE),
            "prior_operations": [],
            "now": NOW,
        }
        value.update(overrides)
        return value

    def test_update_requires_conditional_update_and_fresh_revision(self):
        self.assertEqual(
            defect.plan_external_operation(self.update_request())["decision"], "allow"
        )
        stale = defect.plan_external_operation(
            self.update_request(current_revision="8")
        )
        self.assertIn("stale_issue_read_reread_required", stale["reasons"])
        unsupported = defect.plan_external_operation(
            self.update_request(service={**SERVICE, "conditional_update": False})
        )
        self.assertIn("conditional_update_unavailable", unsupported["reasons"])

    def test_close_requires_owner_confirmed_fix_on_the_fix_target_only(self):
        good_fix = {
            "status": "fix_confirmed",
            "verified_target_ref": "build:42",
            "result_finalized": True,
            "cleanup_status": "成功",
        }
        self.assertEqual(
            defect.plan_external_operation(
                self.update_request("close", fix_verification=good_fix)
            )["decision"],
            "allow",
        )
        for name, fix in {
            "none": None,
            "notice_only": {"status": "issue_marked_resolved"},
            "old_build": {**good_fix, "verified_target_ref": "build:41"},
            "other_build": {**good_fix, "verified_target_ref": "build:99"},
            "cleanup_unknown": {**good_fix, "cleanup_status": "未確認"},
            "unfinalized": {**good_fix, "result_finalized": False},
        }.items():
            with self.subTest(name=name):
                plan = defect.plan_external_operation(
                    self.update_request("close", fix_verification=fix)
                )
                self.assertEqual(plan["decision"], "blocked")
                self.assertIn(
                    "close_without_verified_fix_on_fix_target", plan["reasons"]
                )

    def test_reopen_needs_owner_confirmed_failure(self):
        plan = defect.plan_external_operation(
            self.update_request("reopen", fix_verification={"status": "fix_confirmed"})
        )
        self.assertEqual(plan["decision"], "blocked")
        ok = defect.plan_external_operation(
            self.update_request(
                "reopen", fix_verification={"status": "fix_not_confirmed"}
            )
        )
        self.assertEqual(ok["decision"], "allow")

    def test_unsupported_operation_and_missing_issue(self):
        self.assertEqual(
            defect.plan_external_operation(
                {"operation": "delete", "candidate": summary()}
            )["decision"],
            "blocked",
        )
        request = self.update_request()
        request["issue"] = None
        self.assertEqual(defect.plan_external_operation(request)["decision"], "blocked")


class OutcomeTests(unittest.TestCase):
    def test_success_requires_independent_matching_readback(self):
        plan = defect.plan_external_operation(create_request())
        call = {"status": "success", "issue_ref": "ISSUE-9", "returned_revision": "1"}
        readback = {
            "issue_ref": "ISSUE-9",
            "revision": "1",
            "matches_request": True,
            "retrieved_at": NOW,
        }
        applied = defect.record_operation_outcome(plan, call, readback)
        self.assertEqual(applied["status"], "applied")
        self.assertEqual(applied["external_issue"]["revision"], "1")
        for bad in (
            None,
            {**readback, "revision": "2"},
            {**readback, "matches_request": False},
        ):
            with self.subTest(readback=bad):
                self.assertEqual(
                    defect.record_operation_outcome(plan, call, bad)["status"],
                    "unknown",
                )

    def test_timeout_is_unknown_and_never_retried(self):
        plan = defect.plan_external_operation(create_request())
        result = defect.record_operation_outcome(plan, {"status": "timeout"}, None)
        self.assertEqual(result["status"], "unknown")
        self.assertIs(result["auto_retry_allowed"], False)
        self.assertEqual(result["next"], "reconcile_with_external_service")

    def test_conflict_and_not_attempted(self):
        plan = defect.plan_external_operation(create_request())
        self.assertEqual(
            defect.record_operation_outcome(
                plan, {"status": "failure", "error": "conflict"}, None
            )["status"],
            "conflict",
        )
        blocked = defect.plan_external_operation(create_request(approval=None))
        result = defect.record_operation_outcome(blocked, {"status": "success"}, None)
        self.assertEqual(result["status"], "not_attempted")
        self.assertIs(result["external_update_performed"], False)


class FixVerificationTests(unittest.TestCase):
    def notice(self, **overrides):
        value = {
            "issue_ref": "ISSUE-1",
            "issue_revision": "9",
            "fix_target_ref": "build:42",
            "change_refs": ["commit:abc"],
        }
        value.update(overrides)
        return value

    def test_request_goes_to_original_owner_for_the_fixed_target(self):
        request = defect.request_fix_verification(summary(), self.notice())
        self.assertEqual(request["status"], "request_ready")
        self.assertEqual(request["send_to"], "e2e-test-execution")
        self.assertEqual(request["fix_target_ref"], "build:42")
        self.assertIs(request["notice_is_confirmation"], False)
        self.assertEqual(request["regression_selection_owner"], "regression-testing")

    def test_old_unknown_or_unidentified_changes_are_not_fix_claims(self):
        cases = {
            "same_build": self.notice(fix_target_ref="build:41"),
            "no_build": self.notice(fix_target_ref=None),
            "unknown_change": self.notice(change_unknown=True),
            "no_changes": self.notice(change_refs=[]),
        }
        for name, notice in cases.items():
            with self.subTest(name=name):
                result = defect.request_fix_verification(summary(), notice)
                self.assertEqual(result["status"], "blocked")
                self.assertIs(result["rerun_allowed"], False)

    def test_stale_testware_blocks_the_request(self):
        stale = summary(
            verification_targets=[
                {"ref": "tc:TC-007", "revision": "t3", "current": False}
            ]
        )
        self.assertEqual(
            defect.request_fix_verification(stale, self.notice())["status"], "blocked"
        )

    def owner_result(self, request, **overrides):
        value = {
            "request_ref": request["request_ref"],
            "owner_skill": "e2e-test-execution",
            "target_ref": "build:42",
            "state": "PASS",
            "actual_start_confirmed": True,
            "result_finalized": True,
            "cleanup_status": "成功",
        }
        value.update(overrides)
        return value

    def test_only_a_finalized_owner_result_on_the_fix_target_confirms(self):
        request = defect.request_fix_verification(summary(), self.notice())
        self.assertEqual(
            defect.evaluate_fix_result(request, self.owner_result(request))["status"],
            "fix_confirmed",
        )
        self.assertEqual(
            defect.evaluate_fix_result(
                request, self.owner_result(request, state="FAIL")
            )["status"],
            "fix_not_confirmed",
        )
        for name, overrides, status in (
            ("old_build", {"target_ref": "build:41"}, "rejected"),
            ("wrong_owner", {"owner_skill": "test-execution"}, "rejected"),
            ("other_request", {"request_ref": "DEFOP-x"}, "rejected"),
            ("not_started", {"actual_start_confirmed": False}, "pending"),
            ("not_finalized", {"result_finalized": False}, "pending"),
            ("cleanup_unknown", {"cleanup_status": "未確認"}, "pending"),
            ("undecided", {"state": "判定不能"}, "pending"),
        ):
            with self.subTest(name=name):
                result = defect.evaluate_fix_result(
                    request, self.owner_result(request, **overrides)
                )
                self.assertEqual(result["status"], status)
                self.assertIs(result["fix_confirmed"], False)

    def test_blocked_request_cannot_be_evaluated(self):
        blocked = defect.request_fix_verification(
            summary(), self.notice(change_unknown=True)
        )
        self.assertEqual(defect.evaluate_fix_result(blocked, {})["status"], "rejected")

    def test_static_finding_uses_the_changed_source_revision(self):
        static = summary(
            candidate(
                owner_skill="adversarial-review",
                source_kind="Finding",
                target={"kind": "source_revision", "ref": "git:abc"},
            )
        )
        request = defect.request_fix_verification(
            static, {**self.notice(), "fix_target_ref": "git:def"}
        )
        self.assertEqual(request["status"], "request_ready")
        self.assertEqual(request["send_to"], "adversarial-review")
        self.assertEqual(request["observed_target_ref"], "git:abc")


class ClosureTests(unittest.TestCase):
    def registered(self, **overrides):
        value = {
            "submission": {
                "status": "registered",
                "external_issue": {
                    "issue_ref": "ISSUE-1",
                    "revision": "9",
                    "retrieved_at": NOW,
                },
            },
            "external_confirmation": "current",
            "fix_verification": {"status": "fix_confirmed"},
        }
        value.update(overrides)
        return value

    def test_closed_only_when_every_part_is_confirmed(self):
        self.assertTrue(defect.closure_status(self.registered())["closed"])
        for overrides in (
            {"external_confirmation": "stale"},
            {"fix_verification": {"status": "pending"}},
            {"fix_verification": None},
            {
                "submission": {
                    "status": "registered",
                    "external_issue": {"issue_ref": "ISSUE-1"},
                }
            },
            {"submission": {"status": "not_attempted"}},
        ):
            with self.subTest(overrides=overrides):
                self.assertFalse(
                    defect.closure_status(self.registered(**overrides))["closed"]
                )

    def test_withheld_needs_reason_and_decider(self):
        ok = {
            "submission": {
                "status": "withheld",
                "withheld_reason": "原因未確定のため保留",
                "decided_by": "qa-lead",
            }
        }
        self.assertTrue(defect.closure_status(ok)["closed"])
        self.assertFalse(
            defect.closure_status({"submission": {"status": "withheld"}})["closed"]
        )


class CliAndPackagingTests(unittest.TestCase):
    def run_cli(self, command, payload, helper=HELPER, cwd=None):
        return subprocess.run(
            [sys.executable, "-I", str(helper), command],
            input=payload if isinstance(payload, str) else json.dumps(payload),
            capture_output=True,
            text=True,
            cwd=cwd,
            check=False,
        )

    def test_cli_round_trip_and_rejections(self):
        done = self.run_cli("assess-candidate", candidate())
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(json.loads(done.stdout)["status"], "ready")
        for payload in (
            "[]",
            '{"a":1,"a":2}',
            "{bad",
            '{"x":"' + "あ" * (2 * 1024 * 1024) + '"}',
        ):
            with self.subTest(payload=payload[:20]):
                rejected = self.run_cli("assess-candidate", payload)
                self.assertEqual(rejected.returncode, 2)
                self.assertEqual(json.loads(rejected.stdout)["status"], "blocked")
        self.assertEqual(self.run_cli("unknown", {}).returncode, 2)

    def test_copied_skill_package_runs_without_sibling_skills(self):
        import shutil
        import tempfile

        with tempfile.TemporaryDirectory() as temp:
            copied = Path(temp) / "defect-management"
            shutil.copytree(REPO_ROOT / "skills" / "defect-management", copied)
            result = self.run_cli(
                "assess-candidate",
                candidate(),
                helper=copied / "scripts" / "defect_runtime.py",
                cwd=temp,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["status"], "ready")

    def test_inputs_are_not_mutated(self):
        raw = candidate()
        before = copy.deepcopy(raw)
        defect.assess_candidate(raw)
        self.assertEqual(raw, before)


class Utf8StdinTests(unittest.TestCase):
    def test_raw_utf8_stdin_is_decoded_independently_of_the_locale(self):
        payload = json.dumps(candidate(), ensure_ascii=False)
        completed = subprocess.run(
            [sys.executable, "-I", str(HELPER), "assess-candidate"],
            input=payload.encode("utf-8"),
            capture_output=True,
            check=False,
            env={
                "PYTHONIOENCODING": "cp932",
                "SYSTEMROOT": __import__("os").environ.get("SYSTEMROOT", ""),
            },
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        completed = subprocess.run(
            [sys.executable, "-I", str(HELPER), "assess-candidate"],
            input=b"\xff\xfe{}",
            capture_output=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 2)


if __name__ == "__main__":
    unittest.main()
