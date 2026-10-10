from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import importlib.util
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[4]


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


graph = load("qa_workflow_artifact_graph_handoff", ROOT / "skills/qa-workflow/scripts/artifact_graph.py")
provider_module = load("wcag_test_cas_provider", Path(__file__).with_name("wcag_handoff_cas_provider.py"))


def expected_key(request_ref: str = "OBS-001") -> dict:
    return {
        "sample_ref": "SAMPLE-001", "variation_ref": "VAR-001", "process_ref": None,
        "requirement_ref": "1.1.1", "request_kind": "wcag-machine-probe",
        "observation_request_ref": request_ref,
    }


def origin(revision: str = "rev-a") -> dict:
    return {"skill": "wcag-conformance-evaluation", "artifact_ref": "WCAG-EVAL-001",
            "artifact_revision": revision, "resume_operation": "resume-formal-evaluation"}


def result_row(handoff: dict, *, result_ref: str = "OBS-RESULT-001", result_revision: str = "r1",
               key: dict | None = None, supersedes: str | None = None) -> dict:
    return {"handoff_ref": handoff["handoff_ref"], "origin_artifact_ref": handoff["origin"]["artifact_ref"],
            "origin_artifact_revision": handoff["origin"]["artifact_revision"],
            "observation_key": key or expected_key(), "result_ref": result_ref,
            "result_revision": result_revision, "previous_result_ref": supersedes,
            "supersedes_result_ref": supersedes}


class WcagObservationHandoffTests(unittest.TestCase):
    def create(self, *, ref: str = "HANDOFF-001", origin_revision: str = "rev-a", existing=None,
               retry=None, expected=None):
        return graph.materialize_wcag_observation_handoff(
            handoff_ref=ref, origin=origin(origin_revision),
            expected_observations=expected or [expected_key()], retry_of_handoff_ref=retry,
            existing_handoffs=existing or [],
        )

    def test_operation_identity_includes_origin_revision_and_local_handoff_ref(self):
        first = graph.wcag_observation_operation_ref("EVAL-001", "r1", "HANDOFF-001")
        self.assertEqual(first, graph.wcag_observation_operation_ref("EVAL-001", "r1", "HANDOFF-001"))
        self.assertNotEqual(first, graph.wcag_observation_operation_ref("EVAL-001", "r2", "HANDOFF-001"))
        self.assertNotEqual(first, graph.wcag_observation_operation_ref("EVAL-001", "r1", "HANDOFF-002"))

    def test_expected_keys_are_typed_unique_and_canonical(self):
        created = self.create()
        self.assertEqual(created["status"], "created")
        self.assertEqual(created["handoff"]["status"], "pending")
        with self.assertRaisesRegex(ValueError, "duplicate_expected"):
            self.create(expected=[expected_key(), expected_key()])

    def test_exact_handoff_retry_is_idempotent_and_conflicting_expected_set_is_rejected(self):
        first = self.create()["handoff"]
        self.assertEqual(self.create(existing=[first])["status"], "existing")
        changed = expected_key("OBS-002")
        conflict = self.create(existing=[first], expected=[changed])
        self.assertEqual((conflict["status"], conflict["reason"]), ("conflict", "handoff_identity_expected_set_mismatch"))

    def test_retry_reuses_same_open_retry_and_creates_new_operation_after_started_handoff(self):
        first = self.create()["handoff"]
        retry = self.create(ref="HANDOFF-002", existing=[first], retry="HANDOFF-001")["handoff"]
        retry["status"] = "in-progress"
        retry["operation_claim_ref"] = "claim-ref"
        retry["operation_claim_revision"] = "claim-rev"
        duplicate = self.create(ref="HANDOFF-003", existing=[first, retry], retry="HANDOFF-001")
        self.assertEqual(duplicate["status"], "existing_open_retry")
        self.assertEqual(retry["operation_ref"], graph.wcag_observation_operation_ref(
            "WCAG-EVAL-001", "rev-a", "HANDOFF-002"))
        with self.assertRaisesRegex(ValueError, "retry_origin_unresolved"):
            self.create(ref="HANDOFF-003", origin_revision="rev-b", existing=[first], retry="HANDOFF-001")

    def test_result_return_is_immutable_idempotent_and_requires_supersedes_for_conflict(self):
        handoff = self.create()["handoff"]
        first = result_row(handoff)
        applied = graph.record_wcag_observation_results(handoff, [first])
        self.assertEqual(applied["status"], "applied")
        duplicate = graph.record_wcag_observation_results(applied["handoff"], [first])
        self.assertEqual(duplicate["status"], "idempotent_noop")
        with self.assertRaisesRegex(ValueError, "requires_explicit_supersedes"):
            graph.record_wcag_observation_results(applied["handoff"], [
                result_row(handoff, result_ref="OBS-RESULT-002", result_revision="r2")])
        next_result = result_row(handoff, result_ref="OBS-RESULT-002", result_revision="r2",
                                 supersedes="OBS-RESULT-001")
        closed = graph.record_wcag_observation_results(applied["handoff"], [next_result])
        self.assertEqual(len(closed["handoff"]["returned_results"]), 2)
        inconsistent_lineage = result_row(handoff, result_ref="OBS-RESULT-003", result_revision="r3",
                                           supersedes="OBS-RESULT-002")
        inconsistent_lineage["previous_result_ref"] = "OBS-RESULT-001"
        with self.assertRaisesRegex(ValueError, "lineage_mismatch"):
            graph.record_wcag_observation_results(closed["handoff"], [inconsistent_lineage])

    def test_closure_rechecks_currentness_cleanup_reservations_and_expected_set(self):
        handoff = self.create()["handoff"]
        handoff = graph.record_wcag_observation_results(handoff, [result_row(handoff)])["handoff"]
        closure = graph.wcag_handoff_closure(
            handoff, current_origin_revision="rev-a", result_currentness={"OBS-RESULT-001": "current"},
            owner_execution_state="complete", cleanup_status="success", required_reservations=[],
        )
        self.assertTrue(closure["close_ready"])
        self.assertEqual(closure["status"], "closed")
        stale = graph.wcag_handoff_closure(
            handoff, current_origin_revision="rev-b", result_currentness={"OBS-RESULT-001": "current"},
            owner_execution_state="complete", cleanup_status="success", required_reservations=[],
        )
        self.assertEqual(stale["status"], "stale")
        blocked = graph.wcag_handoff_closure(
            handoff, current_origin_revision="rev-a", result_currentness={"OBS-RESULT-001": "current"},
            owner_execution_state="complete", cleanup_status="failed",
            required_reservations=[{"status": "reserved"}],
        )
        self.assertEqual(blocked["status"], "blocked")
        self.assertFalse(blocked["close_ready"])

    def test_resume_only_after_closed_state_and_current_closure(self):
        handoff = self.create()["handoff"]
        handoff = graph.record_wcag_observation_results(handoff, [result_row(handoff)])["handoff"]
        closure = graph.wcag_handoff_closure(
            handoff, current_origin_revision="rev-a", result_currentness={"OBS-RESULT-001": "current"},
            owner_execution_state="complete", cleanup_status="not-required", required_reservations=[],
        )
        self.assertFalse(graph.wcag_handoff_resume_decision(handoff, closure, current_origin_revision="rev-a")["may_resume"])
        handoff["status"] = "closed"  # represents the state reread after successful native CAS
        decision = graph.wcag_handoff_resume_decision(handoff, closure, current_origin_revision="rev-a")
        self.assertTrue(decision["may_resume"])
        self.assertEqual(decision["resume_operation"], "resume-formal-evaluation")
        self.assertFalse(graph.wcag_handoff_resume_decision(handoff, closure, current_origin_revision="rev-b")["may_resume"])

    def test_external_reservation_revision_is_required_and_propagated(self):
        missing = graph.reserve_shared_resource("unused", "resource", "workflow", native_atomic_conditional_release=False,
                                                external_reservation="sqlite:r1", external_reservation_acquired=True)
        self.assertEqual((missing["status"], missing["reason"]), ("blocked", "external_reservation_revision_missing"))
        reserved = graph.reserve_shared_resource("unused", "resource", "workflow", native_atomic_conditional_release=False,
                                                 external_reservation="sqlite:r1", external_reservation_acquired=True,
                                                 external_reservation_revision="sqlite:7")
        self.assertEqual(reserved["reservation_revision"], "sqlite:7")


class SQLiteTestCASProviderTests(unittest.TestCase):
    def test_state_create_read_successful_cas_and_stale_revision_conflict(self):
        with tempfile.TemporaryDirectory() as temporary:
            provider = provider_module.SQLiteHandoffCASProvider(Path(temporary) / "handoff.db")
            created = provider.create_state("workflow-1", {"handoffs": []})
            self.assertEqual(created["status"], "created")
            self.assertEqual(provider.read_state("workflow-1")["revision"], 1)
            written = provider.compare_and_set_state("workflow-1", 1, {"handoffs": ["one"]})
            self.assertEqual(written["status"], "written")
            stale = provider.compare_and_set_state("workflow-1", 1, {"handoffs": ["stale"]})
            self.assertEqual(stale["status"], "conflict")

    def test_concurrent_same_revision_writes_have_one_winner(self):
        with tempfile.TemporaryDirectory() as temporary:
            provider = provider_module.SQLiteHandoffCASProvider(Path(temporary) / "handoff.db")
            provider.create_state("workflow-1", {"handoffs": []})
            with ThreadPoolExecutor(max_workers=2) as executor:
                results = list(executor.map(
                    lambda value: provider.compare_and_set_state("workflow-1", 1, {"winner": value}),
                    ("a", "b"),
                ))
            self.assertEqual(sum(row["status"] == "written" for row in results), 1)
            self.assertEqual(sum(row["status"] == "conflict" for row in results), 1)

    def test_reservation_conflict_owner_and_revision_checks_and_release(self):
        with tempfile.TemporaryDirectory() as temporary:
            provider = provider_module.SQLiteHandoffCASProvider(Path(temporary) / "handoff.db")
            reservation = provider.acquire_reservation("browser-session", "workflow-1")
            self.assertEqual(reservation["status"], "reserved")
            self.assertEqual(provider.acquire_reservation("browser-session", "workflow-2")["status"], "conflict")
            self.assertEqual(provider.release_reservation("browser-session", "workflow-2", 1)["status"], "conflict")
            self.assertEqual(provider.release_reservation("browser-session", "workflow-1", 99)["status"], "conflict")
            released = provider.release_reservation("browser-session", "workflow-1", reservation["revision"])
            self.assertEqual(released["status"], "released")
            self.assertEqual(provider.acquire_reservation("browser-session", "workflow-2")["status"], "reserved")

    def test_canonical_handoff_lifecycle_uses_physical_envelope_external_cas_and_reread(self):
        with tempfile.TemporaryDirectory() as temporary:
            provider = provider_module.SQLiteHandoffCASProvider(Path(temporary) / "canonical.db")
            workflow_ref = graph.new_workflow_ref()
            envelope = {"workflow_ref": workflow_ref, "schema_version": "1", "state": {"handoffs": []}}
            created = provider.create_state(workflow_ref, envelope)
            self.assertEqual(created["status"], "created")

            handoff = graph.materialize_wcag_observation_handoff(
                handoff_ref="HANDOFF-001", origin=origin(), expected_observations=[expected_key()]) ["handoff"]
            self.assertEqual(handoff["handoff_kind"], "wcag-observation")
            envelope["state"]["handoffs"].append(handoff)
            pending = provider.compare_and_set_state(workflow_ref, created["revision"], envelope)
            self.assertEqual(pending["status"], "written")
            self.assertEqual(provider.read_state(workflow_ref)["state"]["state"]["handoffs"][0]["status"], "pending")

            claim = graph.claim_mutable_operation(Path(temporary) / "claims", workflow_ref, handoff["operation_ref"])
            self.assertTrue(claim["may_start"])
            acquired = provider.acquire_reservation("fixture-browser-session", workflow_ref)
            reserved = graph.reserve_shared_resource(
                "unused", "fixture-browser-session", workflow_ref,
                native_atomic_conditional_release=False,
                external_reservation=acquired["reservation_ref"], external_reservation_acquired=True,
                external_reservation_revision=f"sqlite:{acquired['revision']}")
            handoff["operation_claim_ref"] = claim["path"]
            handoff["operation_claim_revision"] = claim["claim_revision"]
            reservation_row = {"resource_ref": "fixture-browser-session",
                "reservation_ref": reserved["reservation_ref"], "provider": reserved["provider"],
                "reservation_revision": reserved["reservation_revision"], "status": "reserved"}
            handoff["resource_reservations"] = [reservation_row]
            handoff["status"] = "in-progress"
            before_browser = provider.read_state(workflow_ref)
            self.assertEqual(before_browser["state"]["state"]["handoffs"][0]["status"], "pending")
            in_progress = {**before_browser["state"], "state": {"handoffs": [handoff]}}
            saved = provider.compare_and_set_state(workflow_ref, before_browser["revision"], in_progress)
            self.assertEqual(saved["status"], "written")
            browser_may_start = provider.read_state(workflow_ref)["state"]["state"]["handoffs"][0]["status"] == "in-progress"
            self.assertTrue(browser_may_start)

            # The immutable result payload is the returned owner evidence link.
            result = result_row(handoff)
            result.update({"evidence_refs": ["EVIDENCE-FIXTURE-001"], "currentness_dependency": "fixture-document-r1"})
            applied = graph.record_wcag_observation_results(handoff, [result])
            handoff = applied["handoff"]
            handoff["status"] = "returned"
            after_owner = provider.read_state(workflow_ref)
            returned_envelope = {**after_owner["state"], "state": {"handoffs": [handoff]}}
            returned_write = provider.compare_and_set_state(workflow_ref, after_owner["revision"], returned_envelope)
            self.assertEqual(returned_write["status"], "written")
            self.assertEqual(graph.record_wcag_observation_results(handoff, [result])["status"], "idempotent_noop")

            release_decision = graph.release_shared_resource(
                current_workflow_ref=workflow_ref, expected_workflow_ref=workflow_ref,
                expected_reservation_revision=reserved["reservation_revision"],
                current_reservation_revision=reserved["reservation_revision"],
                native_atomic_conditional_release=True, owner_state_verified=True,
                owner_execution_state="complete", cleanup_confirmed=True)
            self.assertEqual(release_decision["status"], "conditional_release_required")
            released = provider.release_reservation("fixture-browser-session", workflow_ref, acquired["revision"])
            self.assertEqual(released["status"], "released")
            reservation_row["status"] = "released"
            handoff["resource_reservations"] = [reservation_row]
            returned_current = provider.read_state(workflow_ref)
            released_envelope = {**returned_current["state"], "state": {"handoffs": [handoff]}}
            release_write = provider.compare_and_set_state(workflow_ref, returned_current["revision"], released_envelope)
            self.assertEqual(release_write["status"], "written")

            closure = graph.wcag_handoff_closure(
                handoff, current_origin_revision="rev-a", result_currentness={"OBS-RESULT-001": "current"},
                owner_execution_state="complete", cleanup_status="success",
                required_reservations=handoff["resource_reservations"])
            self.assertTrue(closure["close_ready"])
            handoff["status"] = "closed"
            current = provider.read_state(workflow_ref)
            closed_envelope = {**current["state"], "state": {"handoffs": [handoff]}}
            closed_write = provider.compare_and_set_state(workflow_ref, current["revision"], closed_envelope)
            self.assertEqual(closed_write["status"], "written")
            reread = provider.read_state(workflow_ref)
            self.assertEqual(reread["state"]["state"]["handoffs"][0]["status"], "closed")
            may_resume = graph.wcag_handoff_resume_decision(
                reread["state"]["state"]["handoffs"][0], closure, current_origin_revision="rev-a")
            self.assertTrue(may_resume["may_resume"])
            self.assertEqual(may_resume["result_refs"], ["OBS-RESULT-001"])


if __name__ == "__main__":
    unittest.main()
