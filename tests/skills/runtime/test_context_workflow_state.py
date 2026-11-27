from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "skills" / "qa-workflow" / "scripts"))
sys.path.insert(0, str(ROOT / "tests" / "skills" / "runtime"))

import artifact_graph  # noqa: E402
import context_artifact_store  # noqa: E402
import context_artifacts as contracts  # noqa: E402
import context_workflow_state  # noqa: E402
import owner_verifiers  # noqa: E402
import test_context_artifacts as fixtures  # noqa: E402
import test_workflow_runtime as workflow_fixtures  # noqa: E402
import workflow_runtime  # noqa: E402


class ContextWorkflowStateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.workflow_root = self.base / "workflow-state"
        self.artifact_root = self.base / "context-artifacts"
        self.artifact_root.mkdir()
        self.workflow_ref = str(uuid.uuid4())
        self.signal_request_contract = {
            "skill": "context-signal-audit",
            "source": {
                "artifact_ref": fixtures.SOURCE_REF,
                "source_revision": "r3",
                "content_hash": fixtures.SOURCE_HASH,
            },
            "requested_range": {"kind": "sections", "items": ["SEC-1"]},
            "observation_condition": {"locale": "ja"},
        }
        signal_request = context_workflow_state.build_request_scope(
            {
                "workflow_ref": self.workflow_ref,
                "contract": self.signal_request_contract,
            }
        )
        self.signal_scope_request = signal_request["request_scope"]
        self.signal_request_contract = signal_request["contract"]
        self.synthesis_request_contract = {
            "skill": "context-rule-synthesis",
            "requested_operation_input": fixtures.operation_input(),
            "requested_scope": fixtures.requested_scope(),
            "target_batch_refs": [],
        }
        synthesis_request = context_workflow_state.build_request_scope(
            {
                "workflow_ref": self.workflow_ref,
                "contract": self.synthesis_request_contract,
            }
        )
        self.synthesis_scope_request = synthesis_request["request_scope"]
        self.synthesis_request_contract = synthesis_request["contract"]
        created = artifact_graph.create_sqlite_workflow_state(
            self.workflow_root,
            self.workflow_ref,
            {
                "overall_state": "実行中",
                "started_source_refs": [fixtures.SOURCE_REF],
                "existing_owner_data": {"preserve": True},
                "context_signal_attempts": [],
                "context_synthesis_run_refs": [],
                "context_request_contracts": [
                    self.signal_request_contract,
                    self.synthesis_request_contract,
                ],
                "requested_scopes": [
                    self.signal_scope_request,
                    self.synthesis_scope_request,
                ],
            },
        )
        self.revision = created["state_revision"]
        self.store = context_artifact_store.DirectoryArtifactStore(self.artifact_root)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def signal_record(
        self,
        batch_readback: dict,
        workflow_ref: str | None = None,
        request_scope: dict | None = None,
    ) -> dict:
        workflow_ref = workflow_ref or self.workflow_ref
        operation_id = contracts.workflow_operation_id(
            workflow_ref, fixtures.operation_input(), fixtures.requested_scope()
        )
        return {
            "attempt_id": "1" * 64,
            "workflow_operation_id": operation_id,
            "request_scope": copy.deepcopy(request_scope or self.signal_scope_request),
            "source": {
                "artifact_ref": fixtures.SOURCE_REF,
                "source_revision": "r3",
                "content_hash": fixtures.SOURCE_HASH,
            },
            "requested_range": {"kind": "sections", "items": ["SEC-1"]},
            "observation_condition": {"locale": "ja"},
            "actual_inspected_range": {"kind": "sections", "items": ["SEC-1"]},
            "batch_refs": [
                {
                    "artifact_ref": batch_readback["artifact_ref"],
                    "revision": batch_readback["revision"],
                    "content_hash": batch_readback["sha256"],
                    "assigned_range": {"kind": "sections", "items": ["SEC-1"]},
                }
            ],
            "candidate_check": {
                "status": "checked_no_conflict",
                "triggered_candidate_identities": [],
            },
            "status": "completed",
            "failure_reason": None,
            "resume_condition": None,
        }

    def signal_batch_variant(
        self,
        *,
        source_ref: str = fixtures.SOURCE_REF,
        requested_range: dict | None = None,
        observation_condition: dict | None = None,
    ) -> dict:
        value = fixtures.build_batch()
        source = value["source"]
        actual_range = requested_range or source["actual_inspected_range"]
        observation = observation_condition or source["observation_condition"]
        source["artifact_ref"] = source_ref
        source["requested_range"] = copy.deepcopy(actual_range)
        source["actual_inspected_range"] = copy.deepcopy(actual_range)
        source["observation_condition"] = copy.deepcopy(observation)
        for signal in value["signals"]:
            signal["signal_identity"] = contracts.signal_identity(
                source_ref,
                signal["observation_locator"],
                source["source_content_hash"],
            )
            signal["signal_content_hash"] = contracts.signal_content_hash(signal)
        identity = contracts.batch_identity(
            source_ref,
            source["source_content_hash"],
            actual_range,
            observation,
        )
        value["batch_identity"] = identity
        value["artifact_ref"] = contracts.artifact_ref("context-signal-batch", identity)
        return contracts.validate_artifact(value, "context-signal-batch")

    def run_for_current_workflow(
        self, scope: dict | None = None, workflow_ref: str | None = None
    ) -> dict:
        run = fixtures.build_run()
        run["workflow_ref"] = workflow_ref or self.workflow_ref
        if scope is not None:
            run["requested_scope"] = copy.deepcopy(scope)
        operation_id = contracts.workflow_operation_id(
            run["workflow_ref"], run["operation_input"], run["requested_scope"]
        )
        run["workflow_operation_id"] = operation_id
        run["run_identity"] = contracts.run_identity(operation_id)
        run["artifact_ref"] = contracts.artifact_ref(
            "context-synthesis-run", run["run_identity"]
        )
        contracts.validate_artifact(run, "context-synthesis-run")
        return run

    def synthesis_request(
        self,
        run: dict,
        revision: str,
        workflow_ref: str | None = None,
        workflow_state_root: str | Path | None = None,
        expected_revision: str | None = None,
        request_scope: dict | None = None,
    ) -> dict:
        return {
            "operation": "record-synthesis-run",
            "workflow_state_root": str(workflow_state_root or self.workflow_root),
            "workflow_ref": workflow_ref or self.workflow_ref,
            "expected_revision": expected_revision or self.revision,
            "artifact_root": str(self.artifact_root),
            "run_ref": run["artifact_ref"],
            "run_revision": revision,
            "requested_operation_input": copy.deepcopy(run["operation_input"]),
            "requested_scope": copy.deepcopy(run["requested_scope"]),
            "request_scope": copy.deepcopy(
                request_scope or self.synthesis_scope_request
            ),
        }

    def _new_registered_state(
        self,
        requested_scopes: list[dict],
        context_request_contracts: list[dict] | None = None,
    ) -> tuple[Path, str, str]:
        workflow_root = self.base / f"workflow-{uuid.uuid4()}"
        workflow_ref = self.workflow_ref
        initialized = context_workflow_state.handle(
            {
                "operation": "initialize",
                "workflow_state_root": str(workflow_root),
                "workflow_ref": workflow_ref,
                "initial_state": {
                    "overall_state": "実行中",
                    "context_signal_attempts": [],
                    "context_synthesis_run_refs": [],
                },
            }
        )
        self.assertEqual(initialized["status"], "created", initialized)
        registered = context_workflow_state.handle(
            {
                "operation": "register-requested-scopes",
                "workflow_state_root": str(workflow_root),
                "workflow_ref": workflow_ref,
                "expected_revision": initialized["state_revision"],
                "artifact_root": str(self.artifact_root),
                "requested_scopes": requested_scopes,
                "context_request_contracts": copy.deepcopy(
                    context_request_contracts
                    if context_request_contracts is not None
                    else [
                        contract
                        for contract in (
                            self.signal_request_contract,
                            self.synthesis_request_contract,
                        )
                        if contract["request_scope"] in requested_scopes
                    ]
                ),
            }
        )
        self.assertEqual(registered["status"], "written", registered)
        return workflow_root, workflow_ref, registered["state_revision"]

    def _signal_owner_scope(
        self,
        batch: dict,
        readback: dict,
        workflow_ref: str,
        workflow_root: Path,
        request_scopes: list[dict],
    ) -> tuple[dict, dict]:
        source = batch["source"]
        assigned_range = source["requested_range"]
        execution_range = json.dumps(
            assigned_range,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        scope = {
            "skill": "context-signal-audit",
            "target": batch["artifact_ref"],
            "execution_range": execution_range,
            "normalized_input": {
                "context_workflow_state": {
                    "artifact_root": str(self.artifact_root),
                    "workflow_state_root": str(workflow_root),
                    "request_scope": copy.deepcopy(request_scopes[0]),
                    "request_scopes": copy.deepcopy(request_scopes),
                },
                "context_request": {
                    "workflow_ref": workflow_ref,
                    "source_artifact_ref": source["artifact_ref"],
                    "source_revision": source["source_revision"],
                    "source_content_hash": source["source_content_hash"],
                    "requested_range": source["requested_range"],
                    "assigned_range": assigned_range,
                    "observation_condition": source["observation_condition"],
                },
                "owner_verification": {
                    "stored_content": readback["content"],
                    "readback": readback,
                    "expected_revision": readback["revision"],
                    "root_binding": self.store.root_binding,
                    "requested_source_ref": source["artifact_ref"],
                    "requested_source_content_hash": source["source_content_hash"],
                    "requested_range": source["requested_range"],
                    "observation_condition": source["observation_condition"],
                    "current_source": {
                        "artifact_ref": source["artifact_ref"],
                        "source_revision": source["source_revision"],
                        "content_hash": source["source_content_hash"],
                    },
                    "batch_readbacks": [readback],
                },
            },
        }
        result = owner_verifiers.verify("context-signal-audit", scope)
        self.assertEqual(result["status"], "verified", result)
        return scope, result["record"]

    def _synthesis_owner_scope(
        self,
        run: dict,
        readback: dict,
        provider_readbacks: list[dict],
        workflow_root: Path,
        request_scopes: list[dict],
    ) -> tuple[dict, dict]:
        scope = {
            "skill": "context-rule-synthesis",
            "target": run["artifact_ref"],
            "execution_range": "run:" + run["run_identity"],
            "normalized_input": {
                "context_workflow_state": {
                    "artifact_root": str(self.artifact_root),
                    "workflow_state_root": str(workflow_root),
                    "requested_operation_input": copy.deepcopy(run["operation_input"]),
                    "requested_scope": copy.deepcopy(run["requested_scope"]),
                    "request_scope": copy.deepcopy(request_scopes[0]),
                    "request_scopes": copy.deepcopy(request_scopes),
                },
                "context_request": {
                    "workflow_ref": run["workflow_ref"],
                    "operation_input": copy.deepcopy(run["operation_input"]),
                    "requested_scope": copy.deepcopy(run["requested_scope"]),
                    "target_batch_refs": copy.deepcopy(
                        run["triage_plan"]["target_batch_refs"]
                    ),
                },
                "owner_verification": {
                    "stored_content": readback["content"],
                    "readback": readback,
                    "expected_revision": readback["revision"],
                    "root_binding": self.store.root_binding,
                    "provider_readbacks": provider_readbacks,
                },
            },
        }
        result = owner_verifiers.verify("context-rule-synthesis", scope)
        self.assertEqual(result["status"], "verified", result)
        return scope, result["record"]

    def _attach_signal_batch(self, run: dict, batch: dict, readback: dict) -> None:
        run["operation_input"]["input_sources"].append(
            {
                "artifact_ref": batch["artifact_ref"],
                "content_hash": readback["sha256"],
                "effective_authority_fingerprint": None,
                "source_revision": readback["revision"],
            }
        )
        run["operation_input"]["input_sources"].sort(
            key=lambda row: row["artifact_ref"]
        )
        run["snapshot"]["referenced_sources"].append(
            {
                "source_kind": "signal_batch",
                "artifact_ref": batch["artifact_ref"],
                "source_revision": readback["revision"],
                "content_hash": readback["sha256"],
                "effective_authority_fingerprint": None,
            }
        )
        run["snapshot"]["referenced_sources"].sort(
            key=lambda row: (row["artifact_ref"], row["source_revision"])
        )
        run["snapshot"]["snapshot_hash"] = contracts.snapshot_hash(run["snapshot"])
        run["triage_plan"]["target_batch_refs"] = [batch["artifact_ref"]]
        operation_id = contracts.workflow_operation_id(
            run["workflow_ref"], run["operation_input"], run["requested_scope"]
        )
        run["workflow_operation_id"] = operation_id
        run["run_identity"] = contracts.run_identity(operation_id)
        run["artifact_ref"] = contracts.artifact_ref(
            "context-synthesis-run", run["run_identity"]
        )
        contracts.validate_artifact(run, "context-synthesis-run")

    def _pending_candidate_op(self, run: dict) -> tuple[dict, dict]:
        candidate = fixtures.build_candidate()
        intent = {"question": "Does the rule apply after settlement?"}
        candidate["handoff_records"] = [
            {
                "semantic_handoff_key": contracts.semantic_handoff_key(
                    "question-analysis", "feature:refund", intent
                ),
                "workflow_operation_id": run["workflow_operation_id"],
                "target_owner": "question-analysis",
                "target_scope": "feature:refund",
                "normalized_intent": intent,
                "reason": "The applicability boundary needs owner review.",
                "status": "pending",
                "confirmed_target_ref": {
                    "artifact_ref": None,
                    "artifact_revision": None,
                    "artifact_content_hash": None,
                },
            }
        ]
        contracts.validate_artifact(candidate, "context-rule-candidate")
        digest = hashlib.sha256(contracts.canonical_bytes(candidate)).hexdigest()
        operation = {
            "candidate_identity": candidate["candidate_identity"],
            "candidate_ref": candidate["artifact_ref"],
            "action": "create",
            "base_content_hash": None,
            "expected_revision": None,
            "related_preconditions": [],
            "operation_id": "provider-op-pending",
            "planned_content_hash": digest,
            "planned_payload": copy.deepcopy(candidate),
            "write_request_meta": {
                "source_ref": fixtures.SOURCE_REF,
                "source_revision": "r3",
                "approval_ref": "approval:qa-write",
                "approval_revision": "r1",
                "change_reason": "Persist the planned candidate before handoff.",
            },
            "confirmed_result": {
                "artifact_ref": None,
                "storage_revision": None,
                "content_hash": None,
            },
        }
        return candidate, operation

    def _runtime_context_scope(
        self,
        run: dict,
        run_readback: dict,
        provider_readbacks: list[dict],
        request_scope: dict | None = None,
    ) -> dict:
        return {
            "skill": "context-rule-synthesis",
            "target": run["artifact_ref"],
            "execution_range": "run:" + run["run_identity"],
            "normalized_input": {
                "context_workflow_state": {
                    "artifact_root": str(self.artifact_root),
                    "workflow_state_root": str(self.workflow_root),
                    "requested_operation_input": copy.deepcopy(run["operation_input"]),
                    "requested_scope": copy.deepcopy(run["requested_scope"]),
                    "request_scope": copy.deepcopy(
                        request_scope or self.synthesis_scope_request
                    ),
                },
                "owner_verification": {
                    "readback": run_readback,
                    "provider_readbacks": provider_readbacks,
                },
            },
        }

    def _complete_synthesis_group(self, scope: dict) -> dict:
        normalized = scope["normalized_input"]
        state_request = normalized["context_workflow_state"]
        evidence = normalized.get("owner_verification", {})
        return context_workflow_state.handle(
            {
                "operation": "completion-check",
                "workflow_state_root": state_request["workflow_state_root"],
                "workflow_ref": self.workflow_ref,
                "artifact_root": state_request["artifact_root"],
                "requested_operation_input": state_request["requested_operation_input"],
                "requested_scope": state_request["requested_scope"],
                "request_scopes": state_request.get(
                    "request_scopes", [state_request["request_scope"]]
                ),
                "provider_readbacks": evidence.get("provider_readbacks", []),
            }
        )

    def _state_cli(self, request: dict) -> dict:
        completed = subprocess.run(
            [
                sys.executable,
                str(
                    ROOT
                    / "skills"
                    / "qa-workflow"
                    / "scripts"
                    / "context_workflow_state.py"
                ),
            ],
            input=json.dumps(request, ensure_ascii=False).encode("utf-8"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=ROOT,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr.decode("utf-8"))
        self.assertEqual(completed.stderr, b"")
        return json.loads(completed.stdout)

    def test_signal_attempt_is_saved_with_actual_batch_readback_and_reopens(
        self,
    ) -> None:
        batch = fixtures.build_batch()
        stored = self.store.write("context-signal-batch", batch)["readback"]
        request = {
            "operation": "record-signal-attempt",
            "workflow_state_root": str(self.workflow_root),
            "workflow_ref": self.workflow_ref,
            "expected_revision": self.revision,
            "artifact_root": str(self.artifact_root),
            "record": self.signal_record(stored),
        }

        result = context_workflow_state.handle(request)

        self.assertEqual(result["status"], "written")
        saved = artifact_graph.read_sqlite_workflow_state(
            self.workflow_root, self.workflow_ref
        )
        self.assertEqual(saved["state"]["existing_owner_data"], {"preserve": True})
        self.assertEqual(
            saved["state"]["context_signal_attempts"][0]["status"], "completed"
        )
        self.assertEqual(
            saved["state"]["context_signal_attempts"][0]["batch_refs"][0]["revision"],
            stored["revision"],
        )
        reopened = context_workflow_state.handle(
            {
                "operation": "read",
                "workflow_state_root": str(self.workflow_root),
                "workflow_ref": self.workflow_ref,
            }
        )
        self.assertEqual(reopened["state"], saved["state"])
        self.assertEqual(reopened["state_revision"], result["state_revision"])

        replay = context_workflow_state.handle(
            {**request, "expected_revision": result["state_revision"]}
        )
        self.assertEqual(replay["status"], "reused")
        self.assertEqual(replay["state_revision"], result["state_revision"])

    def test_synthesis_run_refs_preserve_request_mapping_and_conflict_on_stale_state(
        self,
    ) -> None:
        run = self.run_for_current_workflow()
        stored = self.store.write("context-synthesis-run", run)["readback"]
        request = self.synthesis_request(run, stored["revision"])

        result = context_workflow_state.handle(request)

        self.assertEqual(result["status"], "written")
        group = result["state"]["context_synthesis_run_refs"][0]
        self.assertEqual(group["requested_scope"], run["requested_scope"])
        self.assertEqual(group["requested_operation_input"], run["operation_input"])
        self.assertEqual(group["mapping"]["status"], "complete")
        self.assertEqual(group["run_refs"][0]["artifact_ref"], run["artifact_ref"])
        self.assertEqual(group["run_refs"][0]["revision"], stored["revision"])

        stale = context_workflow_state.handle(
            {**request, "expected_revision": self.revision}
        )
        self.assertEqual(stale["status"], "conflict")

    def test_in_progress_candidate_handoff_can_resume_through_synthesis_completion_check(
        self,
    ) -> None:
        run = self.run_for_current_workflow()
        candidate, operation = self._pending_candidate_op(run)
        run["triage_plan"]["planned_candidate_ops"] = [operation]
        run["result_summary"].update(
            {"status": "in_progress", "zero_change_reason": None}
        )
        run["scan_completeness"] = "partial"
        contracts.validate_artifact(run, "context-synthesis-run")

        first_run = self.store.write("context-synthesis-run", run)["readback"]
        recorded = context_workflow_state.handle(
            self.synthesis_request(run, first_run["revision"])
        )
        self.assertEqual(recorded["status"], "written")
        self.revision = recorded["state_revision"]

        source_readback = {
            "kind": "spec",
            "root_binding": self.store.root_binding,
            "artifact_ref": fixtures.SOURCE_REF,
            "revision": "r3",
            "sha256": fixtures.SOURCE_HASH,
            "content": fixtures.SOURCE_CONTENT,
        }
        pending_completion = self._complete_synthesis_group(
            self._runtime_context_scope(run, first_run, [source_readback])
        )
        self.assertEqual(pending_completion["status"], "incomplete")
        self.assertEqual(pending_completion["reason"], "synthesis_run_not_completed")

        with mock.patch.object(
            self.store,
            "read",
            side_effect=context_artifact_store.StoreError(
                "simulated_independent_readback_failure"
            ),
        ):
            with self.assertRaisesRegex(
                context_artifact_store.StoreError,
                "simulated_independent_readback_failure",
            ):
                self.store.write("context-rule-candidate", candidate)
        pending_candidate = self.store.read(candidate["artifact_ref"])
        self.assertEqual(pending_candidate["sha256"], operation["planned_content_hash"])
        self.assertEqual(
            self.store.write("context-rule-candidate", candidate)["status"],
            "reused",
        )
        operation["confirmed_result"] = {
            "artifact_ref": candidate["artifact_ref"],
            "storage_revision": pending_candidate["revision"],
            "content_hash": pending_candidate["sha256"],
        }
        second_run = self.store.write(
            "context-synthesis-run",
            run,
            expected_revision=first_run["revision"],
            expected_content_hash=first_run["sha256"],
        )["readback"]
        recorded = context_workflow_state.handle(
            {
                **self.synthesis_request(run, second_run["revision"]),
                "expected_revision": self.revision,
            }
        )
        self.assertEqual(recorded["status"], "written")
        self.revision = recorded["state_revision"]

        target_content = '{"question_id":"Q-1","status":"returned"}'
        target_hash = hashlib.sha256(target_content.encode("utf-8")).hexdigest()
        candidate["handoff_records"][0].update(
            {
                "status": "returned",
                "confirmed_target_ref": {
                    "artifact_ref": "qa/questions/Q-1",
                    "artifact_revision": "q1",
                    "artifact_content_hash": target_hash,
                },
            }
        )
        contracts.validate_artifact(candidate, "context-rule-candidate")
        returned_candidate = self.store.write(
            "context-rule-candidate",
            candidate,
            expected_revision=pending_candidate["revision"],
            expected_content_hash=pending_candidate["sha256"],
        )["readback"]
        operation.update(
            {
                "operation_id": "provider-op-returned",
                "planned_content_hash": returned_candidate["sha256"],
                "planned_payload": copy.deepcopy(candidate),
                "confirmed_result": {
                    "artifact_ref": candidate["artifact_ref"],
                    "storage_revision": returned_candidate["revision"],
                    "content_hash": returned_candidate["sha256"],
                },
            }
        )
        third_run = self.store.write(
            "context-synthesis-run",
            run,
            expected_revision=second_run["revision"],
            expected_content_hash=second_run["sha256"],
        )["readback"]
        recorded = context_workflow_state.handle(
            {
                **self.synthesis_request(run, third_run["revision"]),
                "expected_revision": self.revision,
            }
        )
        self.assertEqual(recorded["status"], "written")
        self.revision = recorded["state_revision"]

        run["scan_completeness"] = "complete"
        run["result_summary"]["status"] = "completed"
        completed_run = self.store.write(
            "context-synthesis-run",
            run,
            expected_revision=third_run["revision"],
            expected_content_hash=third_run["sha256"],
        )["readback"]
        recorded = context_workflow_state.handle(
            {
                **self.synthesis_request(run, completed_run["revision"]),
                "expected_revision": self.revision,
            }
        )
        self.assertEqual(recorded["status"], "written")
        self.revision = recorded["state_revision"]

        missing_handoff_readback = self._runtime_context_scope(
            run, completed_run, [source_readback]
        )
        missing_handoff = self._complete_synthesis_group(missing_handoff_readback)
        self.assertEqual(
            missing_handoff["reason"], "handoff_provider_readback_mismatch"
        )

        target_readback = {
            "kind": "question",
            "artifact_ref": "qa/questions/Q-1",
            "revision": "q1",
            "sha256": target_hash,
            "content": target_content,
        }
        scope = self._runtime_context_scope(
            run, completed_run, [source_readback, target_readback]
        )
        completed = self._complete_synthesis_group(scope)
        self.assertEqual(completed["status"], "complete")
        self.assertEqual(len(completed["checked_run_refs"]), 1)

    def test_workflow_state_rejects_evidence_from_a_different_artifact_root(
        self,
    ) -> None:
        run = self.run_for_current_workflow()
        first = self.store.write("context-synthesis-run", run)["readback"]
        recorded = context_workflow_state.handle(
            self.synthesis_request(run, first["revision"])
        )
        self.assertEqual(recorded["status"], "written")

        other_root = self.base / "other-context-artifacts"
        other_root.mkdir()
        other_store = context_artifact_store.DirectoryArtifactStore(other_root)
        other_readback = other_store.write("context-synthesis-run", run)["readback"]
        request = {
            **self.synthesis_request(run, other_readback["revision"]),
            "expected_revision": recorded["state_revision"],
            "artifact_root": str(other_root),
        }
        blocked = context_workflow_state.handle(request)

        self.assertEqual(blocked["status"], "blocked")
        self.assertEqual(blocked["reason"], "workflow_artifact_root_mismatch")

    def test_unavailable_context_helper_blocks_only_context_completion(self) -> None:
        scope = {
            "skill": "context-rule-synthesis",
            "target": "context-synthesis-run:unavailable",
            "execution_range": "run:unavailable",
            "normalized_input": {
                "context_workflow_state": {
                    "artifact_root": str(self.artifact_root),
                    "workflow_state_root": str(self.workflow_root),
                    "requested_operation_input": {},
                    "requested_scope": {},
                    "request_scope": self.synthesis_scope_request,
                }
            },
        }

        for missing_module in (
            "context_workflow_state",
            "context_artifact_store",
            "context_artifacts",
        ):
            with self.subTest(missing_module=missing_module):
                with mock.patch.dict(sys.modules):
                    for module_name in (
                        "context_workflow_state",
                        "context_artifact_store",
                        "context_artifacts",
                    ):
                        sys.modules.pop(module_name, None)
                    sys.modules[missing_module] = None
                    issues, completions = (
                        workflow_runtime._verify_context_synthesis_workflow_state(
                            [scope],
                            self.workflow_ref,
                            [],
                            requested_scopes=[self.synthesis_scope_request],
                            verified_owner_scopes=[],
                        )
                    )

                self.assertEqual(completions, [])
                self.assertEqual(
                    issues,
                    [
                        {
                            "issue_type": "context_workflow_state_unavailable",
                            "blocking": True,
                            "reason": "context_workflow_state_dependencies_unavailable",
                            "target": scope["target"],
                        }
                    ],
                )

    def test_synthesis_completion_requires_every_split_run_to_be_completed(
        self,
    ) -> None:
        full_scope = {
            **fixtures.requested_scope(),
            "scope_refs": ["feature:cancel", "feature:refund"],
        }
        built_request = context_workflow_state.build_request_scope(
            {
                "workflow_ref": self.workflow_ref,
                "contract": {
                    "skill": "context-rule-synthesis",
                    "requested_operation_input": fixtures.operation_input(),
                    "requested_scope": full_scope,
                    "target_batch_refs": [],
                },
            }
        )
        request_scope = built_request["request_scope"]
        self.workflow_root, self.workflow_ref, self.revision = (
            self._new_registered_state([request_scope], [built_request["contract"]])
        )
        refund_run = self.run_for_current_workflow(
            {**full_scope, "scope_refs": ["feature:refund"]}
        )
        refund_readback = self.store.write("context-synthesis-run", refund_run)[
            "readback"
        ]
        first_request = self.synthesis_request(
            refund_run,
            refund_readback["revision"],
            workflow_ref=self.workflow_ref,
            workflow_state_root=self.workflow_root,
            expected_revision=self.revision,
            request_scope=request_scope,
        )
        first_request["requested_scope"] = full_scope
        first = context_workflow_state.handle(first_request)
        self.assertEqual(first["status"], "written")

        cancel_run = self.run_for_current_workflow(
            {**full_scope, "scope_refs": ["feature:cancel"]}
        )
        cancel_run["scan_completeness"] = "partial"
        cancel_run["result_summary"].update(
            {"status": "in_progress", "zero_change_reason": None}
        )
        contracts.validate_artifact(cancel_run, "context-synthesis-run")
        cancel_readback = self.store.write("context-synthesis-run", cancel_run)[
            "readback"
        ]
        second_request = self.synthesis_request(
            cancel_run,
            cancel_readback["revision"],
            workflow_ref=self.workflow_ref,
            workflow_state_root=self.workflow_root,
            expected_revision=first["state_revision"],
            request_scope=request_scope,
        )
        second_request.update(
            {
                "requested_scope": full_scope,
            }
        )
        second = context_workflow_state.handle(second_request)
        self.assertEqual(second["status"], "written")

        source_readback = {
            "kind": "spec",
            "root_binding": self.store.root_binding,
            "artifact_ref": fixtures.SOURCE_REF,
            "revision": "r3",
            "sha256": fixtures.SOURCE_HASH,
            "content": fixtures.SOURCE_CONTENT,
        }
        refund_scope = self._runtime_context_scope(
            refund_run, refund_readback, [source_readback], request_scope
        )
        cancel_scope = self._runtime_context_scope(
            cancel_run, cancel_readback, [source_readback], request_scope
        )
        for scope in (refund_scope, cancel_scope):
            scope["normalized_input"]["context_workflow_state"]["requested_scope"] = (
                copy.deepcopy(full_scope)
            )

        incomplete = self._complete_synthesis_group(refund_scope)

        self.assertEqual(incomplete["status"], "incomplete")
        self.assertEqual(incomplete["reason"], "synthesis_run_not_completed")
        self.assertEqual(incomplete["incomplete_run_ref"], cancel_run["artifact_ref"])

    def test_synthesis_reuses_run_when_only_source_revision_changes(self) -> None:
        run = self.run_for_current_workflow()
        stored = self.store.write("context-synthesis-run", run)["readback"]
        request = self.synthesis_request(run, stored["revision"])
        first = context_workflow_state.handle(request)
        self.assertEqual(first["status"], "written")

        revised_input = copy.deepcopy(run["operation_input"])
        revised_input["input_sources"][0]["source_revision"] = "r4"
        replay = context_workflow_state.handle(
            {
                **request,
                "expected_revision": first["state_revision"],
                "requested_operation_input": revised_input,
            }
        )

        self.assertEqual(replay["status"], "reused")
        self.assertEqual(replay["state_revision"], first["state_revision"])
        self.assertEqual(
            replay["state"]["context_synthesis_run_refs"][0][
                "requested_operation_input"
            ],
            run["operation_input"],
        )

    def test_split_runs_keep_full_request_and_mark_mapping_incomplete_until_covered(
        self,
    ) -> None:
        full_scope = {
            **fixtures.requested_scope(),
            "scope_refs": ["feature:cancel", "feature:refund"],
        }
        built_request = context_workflow_state.build_request_scope(
            {
                "workflow_ref": self.workflow_ref,
                "contract": {
                    "skill": "context-rule-synthesis",
                    "requested_operation_input": fixtures.operation_input(),
                    "requested_scope": full_scope,
                    "target_batch_refs": [],
                },
            }
        )
        request_scope = built_request["request_scope"]
        self.workflow_root, self.workflow_ref, self.revision = (
            self._new_registered_state([request_scope], [built_request["contract"]])
        )
        first_run = self.run_for_current_workflow(
            {**full_scope, "scope_refs": ["feature:refund"]}
        )
        first = self.store.write("context-synthesis-run", first_run)["readback"]
        first_request = self.synthesis_request(
            first_run,
            first["revision"],
            workflow_ref=self.workflow_ref,
            workflow_state_root=self.workflow_root,
            expected_revision=self.revision,
            request_scope=request_scope,
        )
        first_request["requested_scope"] = full_scope

        partial = context_workflow_state.handle(first_request)

        self.assertEqual(partial["status"], "written")
        group = partial["state"]["context_synthesis_run_refs"][0]
        self.assertEqual(group["requested_scope"], full_scope)
        self.assertEqual(group["mapping"]["status"], "incomplete")
        self.assertEqual(
            group["mapping"]["unmapped_source_scope_pairs"],
            [[fixtures.SOURCE_REF, "feature:cancel"]],
        )
        partial_scope = self._runtime_context_scope(first_run, first, [], request_scope)
        partial_scope["normalized_input"]["context_workflow_state"][
            "requested_scope"
        ] = copy.deepcopy(full_scope)
        incomplete = self._complete_synthesis_group(partial_scope)
        self.assertEqual(incomplete["status"], "incomplete")
        self.assertEqual(incomplete["reason"], "requested_run_mapping_incomplete")

        second_run = self.run_for_current_workflow(
            {**full_scope, "scope_refs": ["feature:cancel"]}
        )
        second = self.store.write("context-synthesis-run", second_run)["readback"]
        second_request = self.synthesis_request(
            second_run,
            second["revision"],
            workflow_ref=self.workflow_ref,
            workflow_state_root=self.workflow_root,
            expected_revision=partial["state_revision"],
            request_scope=request_scope,
        )
        second_request["expected_revision"] = partial["state_revision"]
        second_request["requested_scope"] = full_scope

        complete = context_workflow_state.handle(second_request)

        self.assertEqual(complete["status"], "written")
        self.assertEqual(
            complete["state"]["context_synthesis_run_refs"][0]["mapping"]["status"],
            "complete",
        )

    def test_synthesis_state_rejects_a_run_for_another_starting_request(self) -> None:
        run = self.run_for_current_workflow()
        stored = self.store.write("context-synthesis-run", run)["readback"]
        wrong_input = copy.deepcopy(run["operation_input"])
        wrong_input["investigation_conditions"]["environment"] = "production"
        request = self.synthesis_request(run, stored["revision"])
        request["requested_operation_input"] = wrong_input
        result = context_workflow_state.handle(request)
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["reason"], "synthesis_start_request_contract_mismatch")

    def test_synthesis_request_and_run_reject_scope_or_source_substitution(
        self,
    ) -> None:
        full_scope = {
            **fixtures.requested_scope(),
            "scope_refs": ["feature:cancel", "feature:refund"],
        }
        operation_input = fixtures.operation_input()
        built_request = context_workflow_state.build_request_scope(
            {
                "workflow_ref": self.workflow_ref,
                "contract": {
                    "skill": "context-rule-synthesis",
                    "requested_operation_input": operation_input,
                    "requested_scope": full_scope,
                    "target_batch_refs": [],
                },
            }
        )
        request_scope = built_request["request_scope"]
        self.workflow_root, self.workflow_ref, self.revision = (
            self._new_registered_state([request_scope], [built_request["contract"]])
        )

        substituted_source_run = self.run_for_current_workflow(full_scope)
        changed_source = substituted_source_run["operation_input"]["input_sources"][0]
        changed_source["artifact_ref"] = "project/specifications/other.md"
        snapshot_source = substituted_source_run["snapshot"]["referenced_sources"][0]
        snapshot_source["artifact_ref"] = changed_source["artifact_ref"]
        substituted_source_run["snapshot"]["snapshot_hash"] = contracts.snapshot_hash(
            substituted_source_run["snapshot"]
        )
        operation_id = contracts.workflow_operation_id(
            self.workflow_ref,
            substituted_source_run["operation_input"],
            substituted_source_run["requested_scope"],
        )
        substituted_source_run["workflow_operation_id"] = operation_id
        substituted_source_run["run_identity"] = contracts.run_identity(operation_id)
        substituted_source_run["artifact_ref"] = contracts.artifact_ref(
            "context-synthesis-run", substituted_source_run["run_identity"]
        )
        contracts.validate_artifact(substituted_source_run, "context-synthesis-run")
        substituted_readback = self.store.write(
            "context-synthesis-run", substituted_source_run
        )["readback"]
        source_request = self.synthesis_request(
            substituted_source_run,
            substituted_readback["revision"],
            workflow_state_root=self.workflow_root,
            expected_revision=self.revision,
            request_scope=request_scope,
        )
        source_request["requested_operation_input"] = operation_input
        source_request["requested_scope"] = full_scope
        source_result = context_workflow_state.handle(source_request)
        self.assertEqual(source_result["status"], "blocked")
        self.assertEqual(source_result["reason"], "run_start_input_mismatch")

        changed_condition_run = self.run_for_current_workflow(full_scope)
        changed_condition_run["operation_input"]["investigation_conditions"][
            "environment"
        ] = "production"
        condition_operation_id = contracts.workflow_operation_id(
            self.workflow_ref,
            changed_condition_run["operation_input"],
            changed_condition_run["requested_scope"],
        )
        changed_condition_run["workflow_operation_id"] = condition_operation_id
        changed_condition_run["run_identity"] = contracts.run_identity(
            condition_operation_id
        )
        changed_condition_run["artifact_ref"] = contracts.artifact_ref(
            "context-synthesis-run", changed_condition_run["run_identity"]
        )
        contracts.validate_artifact(changed_condition_run, "context-synthesis-run")
        condition_readback = self.store.write(
            "context-synthesis-run", changed_condition_run
        )["readback"]
        condition_request = self.synthesis_request(
            changed_condition_run,
            condition_readback["revision"],
            workflow_state_root=self.workflow_root,
            expected_revision=self.revision,
            request_scope=request_scope,
        )
        condition_request["requested_operation_input"] = operation_input
        condition_request["requested_scope"] = full_scope
        condition_result = context_workflow_state.handle(condition_request)
        self.assertEqual(condition_result["status"], "blocked")
        self.assertEqual(condition_result["reason"], "run_start_input_mismatch")

        narrower_scope = {**full_scope, "scope_refs": ["feature:refund"]}
        narrow_run = self.run_for_current_workflow(narrower_scope)
        narrow_readback = self.store.write("context-synthesis-run", narrow_run)[
            "readback"
        ]
        narrow_request = self.synthesis_request(
            narrow_run,
            narrow_readback["revision"],
            workflow_state_root=self.workflow_root,
            expected_revision=self.revision,
            request_scope=request_scope,
        )
        narrow_request["requested_scope"] = narrower_scope
        narrow_result = context_workflow_state.handle(narrow_request)
        self.assertEqual(narrow_result["status"], "blocked")
        self.assertEqual(
            narrow_result["reason"], "synthesis_start_request_contract_mismatch"
        )

    def test_required_b_request_missing_entirely_from_runtime_is_blocked(self) -> None:
        workflow_root, workflow_ref, _ = self._new_registered_state(
            [self.synthesis_scope_request]
        )
        self.workflow_root = workflow_root
        self.workflow_ref = workflow_ref

        issues, completions = workflow_runtime._verify_context_synthesis_workflow_state(
            [],
            workflow_ref,
            [],
            requested_scopes=[self.synthesis_scope_request],
            verified_owner_scopes=[],
        )

        self.assertEqual(completions, [])
        self.assertEqual(
            issues[0]["issue_type"],
            "context_required_scopes_missing_from_runtime",
        )

    def test_persisted_a_and_b_requests_cannot_be_hidden_from_final_gate(self) -> None:
        workflow_root, workflow_ref, _ = self._new_registered_state(
            [self.signal_scope_request, self.synthesis_scope_request]
        )

        issues, completions = workflow_runtime._verify_context_synthesis_workflow_state(
            scopes=[],
            workflow_ref=workflow_ref,
            unverified_scopes=[],
            requested_scopes=[],
            verified_owner_scopes=[],
            context_workflow_state_root=str(workflow_root),
        )

        self.assertEqual(completions, [])
        self.assertEqual(
            issues[0]["issue_type"],
            "context_required_scopes_missing_from_runtime",
        )
        self.assertEqual(
            {row["skill"] for row in issues[0]["requested_scopes"]},
            {"context-signal-audit", "context-rule-synthesis"},
        )

        # A standalone or auxiliary invocation without a persisted context
        # anchor keeps the existing no-context path.
        self.assertEqual(
            workflow_runtime._verify_context_synthesis_workflow_state(
                [], workflow_ref, [], requested_scopes=[], verified_owner_scopes=[]
            ),
            ([], []),
        )

    def test_runtime_keeps_persisted_context_requests_when_final_context_is_dropped(
        self,
    ) -> None:
        workflow_root, workflow_ref, _ = self._new_registered_state(
            [self.signal_scope_request, self.synthesis_scope_request]
        )
        request = workflow_fixtures.WorkflowRuntimeTests()._request()
        request["input"]["workflow_ref"] = workflow_ref
        request["input"]["context_workflow_state_root"] = str(workflow_root)
        # The runtime input retains an unrelated normal scope, but drops all A/B
        # request scopes and owner scopes. The independent root anchor must still
        # make the final gate read the persisted request set.
        request["input"]["requested_scopes"] = [
            workflow_fixtures.required_scope("test-condition-design")
        ]
        result = workflow_fixtures.run(request)
        self.assertEqual(result["runtime_status"], "ok", result)
        self.assertFalse(result["payload"]["can_complete"], result)
        self.assertIn(
            "context_required_scopes_missing_from_runtime",
            {issue["issue_type"] for issue in result["issues"]},
        )

    def test_signal_attempt_must_match_registered_source_range_and_condition(
        self,
    ) -> None:
        original_contract = {
            key: value
            for key, value in self.signal_request_contract.items()
            if key != "request_scope"
        }
        broad_contract = copy.deepcopy(original_contract)
        broad_contract["requested_range"] = {
            "kind": "sections",
            "items": ["SEC-1", "SEC-2"],
        }
        cases = [
            (
                "narrower_range",
                broad_contract,
                fixtures.SOURCE_REF,
                {"kind": "sections", "items": ["SEC-1"]},
                {"locale": "ja"},
            ),
            (
                "different_source",
                original_contract,
                "project/specifications/other.md",
                {"kind": "sections", "items": ["SEC-1"]},
                {"locale": "ja"},
            ),
            (
                "different_observation_condition",
                original_contract,
                fixtures.SOURCE_REF,
                {"kind": "sections", "items": ["SEC-1"]},
                {"locale": "en"},
            ),
        ]

        for name, contract, actual_source, actual_range, observation in cases:
            with self.subTest(name=name):
                built = context_workflow_state.build_request_scope(
                    {"workflow_ref": self.workflow_ref, "contract": contract}
                )
                workflow_root, workflow_ref, state_revision = (
                    self._new_registered_state(
                        [built["request_scope"]], [built["contract"]]
                    )
                )
                batch = self.signal_batch_variant(
                    source_ref=actual_source,
                    requested_range=actual_range,
                    observation_condition=observation,
                )
                batch_readback = self.store.write("context-signal-batch", batch)[
                    "readback"
                ]
                record = self.signal_record(
                    batch_readback,
                    workflow_ref=workflow_ref,
                    request_scope=built["request_scope"],
                )
                record["source"]["artifact_ref"] = actual_source
                record["requested_range"] = actual_range
                record["actual_inspected_range"] = actual_range
                record["observation_condition"] = observation
                result = context_workflow_state.handle(
                    {
                        "operation": "record-signal-attempt",
                        "workflow_state_root": str(workflow_root),
                        "workflow_ref": workflow_ref,
                        "expected_revision": state_revision,
                        "artifact_root": str(self.artifact_root),
                        "record": record,
                    }
                )
                self.assertEqual(result["status"], "blocked", result)
                self.assertEqual(
                    result["reason"], "signal_attempt_start_request_mismatch"
                )

    def test_auxiliary_context_scope_without_state_does_not_block_required_a(
        self,
    ) -> None:
        workflow_root, workflow_ref, state_revision = self._new_registered_state(
            [self.signal_scope_request]
        )
        batch = fixtures.build_batch()
        batch_readback = self.store.write("context-signal-batch", batch)["readback"]
        recorded = context_workflow_state.handle(
            {
                "operation": "record-signal-attempt",
                "workflow_state_root": str(workflow_root),
                "workflow_ref": workflow_ref,
                "expected_revision": state_revision,
                "artifact_root": str(self.artifact_root),
                "record": self.signal_record(
                    batch_readback,
                    workflow_ref=workflow_ref,
                    request_scope=self.signal_scope_request,
                ),
            }
        )
        self.assertEqual(recorded["status"], "written", recorded)
        signal_scope, signal_owner = self._signal_owner_scope(
            batch,
            batch_readback,
            workflow_ref,
            workflow_root,
            [self.signal_scope_request],
        )
        required_scope = {
            "skill": signal_scope["skill"],
            "target": signal_scope["target"],
            "execution_range": signal_scope["execution_range"],
            "requirement": "required",
        }
        auxiliary_scope = {
            "skill": "context-rule-synthesis",
            "target": "candidate:auxiliary",
            "execution_range": "auxiliary",
            "normalized_input": {"mode": "auxiliary"},
        }

        issues, completions = workflow_runtime._verify_context_synthesis_workflow_state(
            [signal_scope, auxiliary_scope],
            workflow_ref,
            [],
            requested_scopes=[required_scope],
            verified_owner_scopes=[signal_owner],
        )
        self.assertEqual(issues, [])
        self.assertEqual(completions[0]["verified_request_count"], 1)

        missing_state_scope = copy.deepcopy(signal_scope)
        del missing_state_scope["normalized_input"]["context_workflow_state"]
        issues, _ = workflow_runtime._verify_context_synthesis_workflow_state(
            [missing_state_scope],
            workflow_ref,
            [],
            requested_scopes=[required_scope],
            verified_owner_scopes=[signal_owner],
        )
        self.assertEqual(
            issues[0]["issue_type"], "context_workflow_state_request_missing"
        )

    def test_final_gate_reconciles_all_a_and_b_requests_across_resume(self) -> None:
        batch = fixtures.build_batch()
        batch_readback = self.store.write("context-signal-batch", batch)["readback"]
        requested_operation_input = fixtures.operation_input()
        requested_operation_input["input_sources"].append(
            {
                "artifact_ref": batch["artifact_ref"],
                "content_hash": batch_readback["sha256"],
                "effective_authority_fingerprint": None,
                "source_revision": batch_readback["revision"],
            }
        )
        requested_operation_input["input_sources"].sort(
            key=lambda row: row["artifact_ref"]
        )
        synthesis_contract = context_workflow_state.build_request_scope(
            {
                "workflow_ref": self.workflow_ref,
                "contract": {
                    "skill": "context-rule-synthesis",
                    "requested_operation_input": requested_operation_input,
                    "requested_scope": fixtures.requested_scope(),
                    "target_batch_refs": [batch["artifact_ref"]],
                },
            }
        )
        synthesis_request_scope = synthesis_contract["request_scope"]
        workflow_root, workflow_ref, state_revision = self._new_registered_state(
            [self.signal_scope_request, synthesis_request_scope],
            [self.signal_request_contract, synthesis_contract["contract"]],
        )
        signal_result = context_workflow_state.handle(
            {
                "operation": "record-signal-attempt",
                "workflow_state_root": str(workflow_root),
                "workflow_ref": workflow_ref,
                "expected_revision": state_revision,
                "artifact_root": str(self.artifact_root),
                "record": self.signal_record(
                    batch_readback,
                    workflow_ref=workflow_ref,
                    request_scope=self.signal_scope_request,
                ),
            }
        )
        self.assertEqual(signal_result["status"], "written", signal_result)
        state_revision = signal_result["state_revision"]
        signal_scope, signal_owner = self._signal_owner_scope(
            batch,
            batch_readback,
            workflow_ref,
            workflow_root,
            [self.signal_scope_request],
        )
        signal_final_scope = {
            "skill": signal_scope["skill"],
            "target": signal_scope["target"],
            "execution_range": signal_scope["execution_range"],
            "requirement": "required",
        }

        run = self.run_for_current_workflow(workflow_ref=workflow_ref)
        self._attach_signal_batch(run, batch, batch_readback)
        run["scan_completeness"] = "partial"
        run["result_summary"].update(
            {"status": "in_progress", "zero_change_reason": None}
        )
        contracts.validate_artifact(run, "context-synthesis-run")
        pending_run = self.store.write("context-synthesis-run", run)["readback"]
        recorded = context_workflow_state.handle(
            self.synthesis_request(
                run,
                pending_run["revision"],
                workflow_ref=workflow_ref,
                workflow_state_root=workflow_root,
                expected_revision=state_revision,
                request_scope=synthesis_request_scope,
            )
        )
        self.assertEqual(recorded["status"], "written", recorded)
        state_revision = recorded["state_revision"]

        source_readback = {
            "kind": "spec",
            "root_binding": self.store.root_binding,
            "artifact_ref": fixtures.SOURCE_REF,
            "revision": "r3",
            "sha256": fixtures.SOURCE_HASH,
            "content": fixtures.SOURCE_CONTENT,
        }
        pending_provider_readbacks = [source_readback, batch_readback, pending_run]
        pending_scope = {
            "skill": "context-rule-synthesis",
            "target": run["artifact_ref"],
            "execution_range": "run:" + run["run_identity"],
            "normalized_input": {
                "context_workflow_state": {
                    "artifact_root": str(self.artifact_root),
                    "workflow_state_root": str(workflow_root),
                    "requested_operation_input": copy.deepcopy(run["operation_input"]),
                    "requested_scope": copy.deepcopy(run["requested_scope"]),
                    "request_scope": synthesis_request_scope,
                    "request_scopes": [synthesis_request_scope],
                },
                "context_request": {
                    "workflow_ref": workflow_ref,
                    "operation_input": copy.deepcopy(run["operation_input"]),
                    "requested_scope": copy.deepcopy(run["requested_scope"]),
                    "target_batch_refs": copy.deepcopy(
                        run["triage_plan"]["target_batch_refs"]
                    ),
                },
                "owner_verification": {
                    "readback": pending_run,
                    "provider_readbacks": pending_provider_readbacks,
                },
            },
        }
        pending_final_scope = {
            "skill": pending_scope["skill"],
            "target": pending_scope["target"],
            "execution_range": pending_scope["execution_range"],
            "requirement": "required",
        }
        pending_issues, pending_completions = (
            workflow_runtime._verify_context_synthesis_workflow_state(
                [signal_scope, pending_scope],
                workflow_ref,
                [],
                requested_scopes=[signal_final_scope, pending_final_scope],
                verified_owner_scopes=[signal_owner],
            )
        )
        self.assertEqual(pending_completions, [])
        self.assertEqual(pending_issues[0]["reason"], "synthesis_run_not_completed")

        runtime_without_b_issues, _ = (
            workflow_runtime._verify_context_synthesis_workflow_state(
                [signal_scope],
                workflow_ref,
                [],
                requested_scopes=[signal_final_scope],
                verified_owner_scopes=[signal_owner],
            )
        )
        self.assertEqual(
            runtime_without_b_issues[0]["reason"],
            "synthesis_required_request_missing_from_runtime",
        )

        run["scan_completeness"] = "complete"
        run["result_summary"].update(
            {
                "status": "completed_zero_changes",
                "zero_change_reason": "no_related_candidates",
            }
        )
        contracts.validate_artifact(run, "context-synthesis-run")
        completed_run = self.store.write(
            "context-synthesis-run",
            run,
            expected_revision=pending_run["revision"],
            expected_content_hash=pending_run["sha256"],
        )["readback"]
        recorded = context_workflow_state.handle(
            self.synthesis_request(
                run,
                completed_run["revision"],
                workflow_ref=workflow_ref,
                workflow_state_root=workflow_root,
                expected_revision=state_revision,
                request_scope=synthesis_request_scope,
            )
        )
        self.assertEqual(recorded["status"], "written", recorded)

        provider_readbacks = [source_readback, batch_readback, completed_run]
        synthesis_scope, synthesis_owner = self._synthesis_owner_scope(
            run,
            completed_run,
            provider_readbacks,
            workflow_root,
            [synthesis_request_scope],
        )
        synthesis_final_scope = {
            "skill": synthesis_scope["skill"],
            "target": synthesis_scope["target"],
            "execution_range": synthesis_scope["execution_range"],
            "requirement": "required",
        }

        issues, completions = workflow_runtime._verify_context_synthesis_workflow_state(
            [signal_scope, synthesis_scope],
            workflow_ref,
            [],
            requested_scopes=[signal_final_scope, synthesis_final_scope],
            verified_owner_scopes=[signal_owner, synthesis_owner],
        )

        self.assertEqual(issues, [])
        self.assertEqual(completions[0]["verified_request_count"], 2)
        self.assertEqual(completions[0]["verified_scope_count"], 2)

        for final_requested_scopes in (
            [synthesis_final_scope],
            [
                signal_final_scope,
                synthesis_final_scope,
                {
                    "skill": "context-rule-synthesis",
                    "target": "context-synthesis-run:unmapped",
                    "execution_range": "run:unmapped",
                    "requirement": "required",
                },
            ],
        ):
            with self.subTest(final_requested_scopes=final_requested_scopes):
                mismatch_issues, _ = (
                    workflow_runtime._verify_context_synthesis_workflow_state(
                        [signal_scope, synthesis_scope],
                        workflow_ref,
                        [],
                        requested_scopes=final_requested_scopes,
                        verified_owner_scopes=[signal_owner, synthesis_owner],
                    )
                )
                self.assertEqual(
                    mismatch_issues[0]["reason"],
                    "context_final_requested_scope_set_mismatch",
                )

        missing_a_scope, _ = workflow_runtime._verify_context_synthesis_workflow_state(
            [synthesis_scope],
            workflow_ref,
            [],
            requested_scopes=[synthesis_final_scope],
            verified_owner_scopes=[synthesis_owner],
        )
        self.assertEqual(
            missing_a_scope[0]["reason"], "signal_batch_owner_scope_missing"
        )

        mismatched_owner = copy.deepcopy(signal_owner)
        mismatched_owner["verified_artifact"]["content_hash"] = "f" * 64
        bad_owner_issues, _ = workflow_runtime._verify_context_synthesis_workflow_state(
            [signal_scope, synthesis_scope],
            workflow_ref,
            [],
            requested_scopes=[signal_final_scope, synthesis_final_scope],
            verified_owner_scopes=[mismatched_owner, synthesis_owner],
        )
        self.assertEqual(
            bad_owner_issues[0]["reason"],
            "signal_owner_and_state_mapping_mismatch",
        )

    def test_requested_scope_snapshot_is_saved_once_in_existing_state(self) -> None:
        workflow_root = self.base / "request-snapshot-workflow"
        workflow_ref = self.workflow_ref
        initialized = context_workflow_state.handle(
            {
                "operation": "initialize",
                "workflow_state_root": str(workflow_root),
                "workflow_ref": workflow_ref,
                "initial_state": {"overall_state": "実行中"},
            }
        )
        registered = context_workflow_state.handle(
            {
                "operation": "register-requested-scopes",
                "workflow_state_root": str(workflow_root),
                "workflow_ref": workflow_ref,
                "expected_revision": initialized["state_revision"],
                "artifact_root": str(self.artifact_root),
                "requested_scopes": [self.signal_scope_request],
                "context_request_contracts": [self.signal_request_contract],
            }
        )
        self.assertEqual(registered["status"], "written", registered)
        self.assertEqual(
            registered["state"]["requested_scopes"], [self.signal_scope_request]
        )
        self.assertEqual(
            registered["state"]["context_artifact_root_binding"],
            self.store.root_binding,
        )
        replay = context_workflow_state.handle(
            {
                "operation": "register-requested-scopes",
                "workflow_state_root": str(workflow_root),
                "workflow_ref": workflow_ref,
                "expected_revision": registered["state_revision"],
                "artifact_root": str(self.artifact_root),
                "requested_scopes": [self.signal_scope_request],
                "context_request_contracts": [self.signal_request_contract],
            }
        )
        self.assertEqual(replay["status"], "reused")

    def test_started_signal_request_can_be_concretized_after_another_attempt(
        self,
    ) -> None:
        unresolved_source = "project/specifications/future.md"
        unresolved_contract = {
            "skill": "context-signal-audit",
            "source": {
                "artifact_ref": unresolved_source,
                "source_revision": None,
                "content_hash": None,
            },
            "requested_range": {"kind": "sections", "items": ["SEC-1"]},
            "observation_condition": {"locale": "ja"},
        }
        unresolved = context_workflow_state.build_request_scope(
            {
                "workflow_ref": self.workflow_ref,
                "contract": unresolved_contract,
            }
        )
        requested_scopes = [self.signal_scope_request, unresolved["request_scope"]]
        workflow_root, workflow_ref, revision = self._new_registered_state(
            requested_scopes,
            [self.signal_request_contract, unresolved["contract"]],
        )

        first_batch = fixtures.build_batch()
        first_readback = self.store.write("context-signal-batch", first_batch)[
            "readback"
        ]
        first_attempt = context_workflow_state.handle(
            {
                "operation": "record-signal-attempt",
                "workflow_state_root": str(workflow_root),
                "workflow_ref": workflow_ref,
                "expected_revision": revision,
                "artifact_root": str(self.artifact_root),
                "record": self.signal_record(
                    first_readback,
                    workflow_ref=workflow_ref,
                    request_scope=self.signal_scope_request,
                ),
            }
        )
        self.assertEqual(first_attempt["status"], "written", first_attempt)

        replay = context_workflow_state.handle(
            {
                "operation": "register-requested-scopes",
                "workflow_state_root": str(workflow_root),
                "workflow_ref": workflow_ref,
                "expected_revision": first_attempt["state_revision"],
                "artifact_root": str(self.artifact_root),
                "requested_scopes": requested_scopes,
                "context_request_contracts": [
                    self.signal_request_contract,
                    unresolved["contract"],
                ],
            }
        )
        self.assertEqual(replay["status"], "reused", replay)

        resolved_contract = copy.deepcopy(unresolved_contract)
        resolved_contract["source"].update(
            {"source_revision": "r3", "content_hash": fixtures.SOURCE_HASH}
        )
        resolved = context_workflow_state.build_request_scope(
            {
                "workflow_ref": workflow_ref,
                "contract": resolved_contract,
                "request_scope": unresolved["request_scope"],
            }
        )
        concretized = context_workflow_state.handle(
            {
                "operation": "register-requested-scopes",
                "workflow_state_root": str(workflow_root),
                "workflow_ref": workflow_ref,
                "expected_revision": first_attempt["state_revision"],
                "artifact_root": str(self.artifact_root),
                "requested_scopes": requested_scopes,
                "context_request_contracts": [
                    self.signal_request_contract,
                    resolved["contract"],
                ],
            }
        )
        self.assertEqual(concretized["status"], "written", concretized)
        stored_contract = next(
            row
            for row in concretized["state"]["context_request_contracts"]
            if row["request_scope"] == unresolved["request_scope"]
        )
        self.assertEqual(stored_contract["request_scope"], unresolved["request_scope"])
        self.assertEqual(stored_contract["source"], resolved_contract["source"])
        self.assertEqual(
            stored_contract["start_contract"]["source"], unresolved_contract["source"]
        )

        stale_replay = context_workflow_state.handle(
            {
                "operation": "register-requested-scopes",
                "workflow_state_root": str(workflow_root),
                "workflow_ref": workflow_ref,
                "expected_revision": concretized["state_revision"],
                "artifact_root": str(self.artifact_root),
                "requested_scopes": requested_scopes,
                "context_request_contracts": [
                    self.signal_request_contract,
                    unresolved["contract"],
                ],
            }
        )
        self.assertEqual(stale_replay["status"], "reused", stale_replay)
        self.assertEqual(
            next(
                row
                for row in stale_replay["state"]["context_request_contracts"]
                if row["request_scope"] == unresolved["request_scope"]
            )["source"],
            resolved_contract["source"],
        )

        resumed = context_workflow_state.handle(
            {
                "operation": "read-context-requests",
                "workflow_state_root": str(workflow_root),
                "workflow_ref": workflow_ref,
            }
        )
        self.assertEqual(resumed["status"], "current", resumed)
        self.assertEqual(
            next(
                row
                for row in resumed["context_request_contracts"]
                if row["request_scope"] == unresolved["request_scope"]
            )["source"],
            resolved_contract["source"],
        )

        resolved_batch = self.signal_batch_variant(source_ref=unresolved_source)
        resolved_readback = self.store.write("context-signal-batch", resolved_batch)[
            "readback"
        ]
        second_record = self.signal_record(
            resolved_readback,
            workflow_ref=workflow_ref,
            request_scope=unresolved["request_scope"],
        )
        second_record.update(
            {
                "attempt_id": "2" * 64,
                "source": resolved_contract["source"],
            }
        )
        second = context_workflow_state.handle(
            {
                "operation": "record-signal-attempt",
                "workflow_state_root": str(workflow_root),
                "workflow_ref": workflow_ref,
                "expected_revision": resumed["state_revision"],
                "artifact_root": str(self.artifact_root),
                "record": second_record,
            }
        )
        self.assertEqual(second["status"], "written", second)

    def test_late_signal_concretization_rejects_changed_source_range_or_condition(
        self,
    ) -> None:
        unresolved = context_workflow_state.build_request_scope(
            {
                "workflow_ref": self.workflow_ref,
                "contract": {
                    "skill": "context-signal-audit",
                    "source": {
                        "artifact_ref": "project/specifications/future.md",
                        "source_revision": None,
                        "content_hash": None,
                    },
                    "requested_range": {
                        "kind": "sections",
                        "items": ["SEC-1", "SEC-2"],
                    },
                    "observation_condition": {"locale": "ja"},
                },
            }
        )
        requested_scopes = [self.signal_scope_request, unresolved["request_scope"]]
        workflow_root, workflow_ref, revision = self._new_registered_state(
            requested_scopes,
            [self.signal_request_contract, unresolved["contract"]],
        )
        batch = self.store.write("context-signal-batch", fixtures.build_batch())[
            "readback"
        ]
        first = context_workflow_state.handle(
            {
                "operation": "record-signal-attempt",
                "workflow_state_root": str(workflow_root),
                "workflow_ref": workflow_ref,
                "expected_revision": revision,
                "artifact_root": str(self.artifact_root),
                "record": self.signal_record(
                    batch,
                    workflow_ref=workflow_ref,
                    request_scope=self.signal_scope_request,
                ),
            }
        )
        self.assertEqual(first["status"], "written", first)

        cases = [
            (
                "different_source",
                lambda value: value["source"].update(
                    {"artifact_ref": "project/specifications/other.md"}
                ),
            ),
            (
                "narrower_range",
                lambda value: value.update(
                    {"requested_range": {"kind": "sections", "items": ["SEC-1"]}}
                ),
            ),
            (
                "changed_observation_condition",
                lambda value: value.update({"observation_condition": {"locale": "en"}}),
            ),
        ]
        for name, change in cases:
            with self.subTest(name=name):
                changed = {
                    key: copy.deepcopy(value)
                    for key, value in unresolved["contract"].items()
                    if key != "request_scope"
                }
                changed["source"].update(
                    {"source_revision": "r3", "content_hash": fixtures.SOURCE_HASH}
                )
                change(changed)
                built = context_workflow_state.build_request_scope(
                    {
                        "workflow_ref": workflow_ref,
                        "contract": changed,
                        "request_scope": unresolved["request_scope"],
                    }
                )
                result = context_workflow_state.handle(
                    {
                        "operation": "register-requested-scopes",
                        "workflow_state_root": str(workflow_root),
                        "workflow_ref": workflow_ref,
                        "expected_revision": first["state_revision"],
                        "artifact_root": str(self.artifact_root),
                        "requested_scopes": requested_scopes,
                        "context_request_contracts": [
                            self.signal_request_contract,
                            built["contract"],
                        ],
                    }
                )
                self.assertEqual(result["status"], "blocked", result)
                state_after = artifact_graph.read_sqlite_workflow_state(
                    workflow_root, workflow_ref
                )
                self.assertEqual(state_after["state_revision"], first["state_revision"])

    def test_synthesis_request_can_add_a_readback_batch_after_an_earlier_run(
        self,
    ) -> None:
        base_input = fixtures.operation_input()
        base_scope = fixtures.requested_scope()
        base_scope["scope_refs"].append("feature:cancel")
        base_scope["scope_refs"].sort()
        synthesis_start = context_workflow_state.build_request_scope(
            {
                "workflow_ref": self.workflow_ref,
                "contract": {
                    "skill": "context-rule-synthesis",
                    "requested_operation_input": base_input,
                    "requested_scope": base_scope,
                    "target_batch_refs": [],
                },
            }
        )
        requested_scopes = [self.signal_scope_request, synthesis_start["request_scope"]]
        workflow_root, workflow_ref, revision = self._new_registered_state(
            requested_scopes,
            [self.signal_request_contract, synthesis_start["contract"]],
        )

        first_run = self.run_for_current_workflow(workflow_ref=workflow_ref)
        first_readback = self.store.write("context-synthesis-run", first_run)[
            "readback"
        ]
        first_run_request = self.synthesis_request(
            first_run,
            first_readback["revision"],
            workflow_ref=workflow_ref,
            workflow_state_root=workflow_root,
            expected_revision=revision,
            request_scope=synthesis_start["request_scope"],
        )
        first_run_request["requested_scope"] = copy.deepcopy(base_scope)
        first_registered = context_workflow_state.handle(first_run_request)
        self.assertEqual(first_registered["status"], "written", first_registered)

        batch = fixtures.build_batch()
        batch_readback = self.store.write("context-signal-batch", batch)["readback"]
        signal_attempt = context_workflow_state.handle(
            {
                "operation": "record-signal-attempt",
                "workflow_state_root": str(workflow_root),
                "workflow_ref": workflow_ref,
                "expected_revision": first_registered["state_revision"],
                "artifact_root": str(self.artifact_root),
                "record": self.signal_record(
                    batch_readback,
                    workflow_ref=workflow_ref,
                    request_scope=self.signal_scope_request,
                ),
            }
        )
        self.assertEqual(signal_attempt["status"], "written", signal_attempt)

        resolved_input = copy.deepcopy(base_input)
        resolved_input["input_sources"].append(
            {
                "artifact_ref": batch["artifact_ref"],
                "content_hash": batch_readback["sha256"],
                "effective_authority_fingerprint": None,
                "source_revision": batch_readback["revision"],
            }
        )
        resolved_input["input_sources"].sort(key=lambda row: row["artifact_ref"])

        def registration(candidate_input: dict, candidate_scope: dict) -> dict:
            candidate = context_workflow_state.build_request_scope(
                {
                    "workflow_ref": workflow_ref,
                    "request_scope": synthesis_start["request_scope"],
                    "contract": {
                        "skill": "context-rule-synthesis",
                        "requested_operation_input": candidate_input,
                        "requested_scope": candidate_scope,
                        "target_batch_refs": [batch["artifact_ref"]],
                    },
                }
            )
            return context_workflow_state.handle(
                {
                    "operation": "register-requested-scopes",
                    "workflow_state_root": str(workflow_root),
                    "workflow_ref": workflow_ref,
                    "expected_revision": signal_attempt["state_revision"],
                    "artifact_root": str(self.artifact_root),
                    "requested_scopes": requested_scopes,
                    "context_request_contracts": [
                        self.signal_request_contract,
                        candidate["contract"],
                    ],
                }
            )

        changed_source_input = copy.deepcopy(resolved_input)
        next(
            row
            for row in changed_source_input["input_sources"]
            if row["artifact_ref"] == fixtures.SOURCE_REF
        )["artifact_ref"] = "project/specifications/other.md"
        changed_source_input["input_sources"].sort(key=lambda row: row["artifact_ref"])
        narrowed_scope = copy.deepcopy(base_scope)
        narrowed_scope["scope_refs"] = ["feature:refund"]
        changed_conditions_input = copy.deepcopy(resolved_input)
        changed_conditions_input["investigation_conditions"] = {
            "environment": "production"
        }
        foreign_input = copy.deepcopy(resolved_input)
        foreign_input["input_sources"].append(
            {
                "artifact_ref": "project/specifications/unrelated.md",
                "content_hash": fixtures.SOURCE_HASH,
                "effective_authority_fingerprint": None,
                "source_revision": "r3",
            }
        )
        foreign_input["input_sources"].sort(key=lambda row: row["artifact_ref"])
        invalid_expansions = {
            "changed_source": (changed_source_input, base_scope),
            "narrowed_analysis_scope": (resolved_input, narrowed_scope),
            "changed_investigation_conditions": (
                changed_conditions_input,
                base_scope,
            ),
            "foreign_batch_source": (foreign_input, base_scope),
        }
        for name, (candidate_input, candidate_scope) in invalid_expansions.items():
            with self.subTest(name=name):
                result = registration(candidate_input, candidate_scope)
                self.assertEqual(result["status"], "blocked", result)
                current = artifact_graph.read_sqlite_workflow_state(
                    workflow_root, workflow_ref
                )
                self.assertEqual(
                    current["state_revision"], signal_attempt["state_revision"]
                )

        synthesis_resolved = context_workflow_state.build_request_scope(
            {
                "workflow_ref": workflow_ref,
                "request_scope": synthesis_start["request_scope"],
                "contract": {
                    "skill": "context-rule-synthesis",
                    "requested_operation_input": resolved_input,
                    "requested_scope": base_scope,
                    "target_batch_refs": [batch["artifact_ref"]],
                },
            }
        )
        concretized = context_workflow_state.handle(
            {
                "operation": "register-requested-scopes",
                "workflow_state_root": str(workflow_root),
                "workflow_ref": workflow_ref,
                "expected_revision": signal_attempt["state_revision"],
                "artifact_root": str(self.artifact_root),
                "requested_scopes": requested_scopes,
                "context_request_contracts": [
                    self.signal_request_contract,
                    synthesis_resolved["contract"],
                ],
            }
        )
        self.assertEqual(concretized["status"], "written", concretized)
        self.assertEqual(
            next(
                row
                for row in concretized["state"]["context_request_contracts"]
                if row["request_scope"] == synthesis_start["request_scope"]
            )["start_contract"]["requested_operation_input"],
            base_input,
        )

        resumed = context_workflow_state.handle(
            {
                "operation": "read-context-requests",
                "workflow_state_root": str(workflow_root),
                "workflow_ref": workflow_ref,
            }
        )
        self.assertEqual(resumed["status"], "current", resumed)
        resumed_contract = next(
            row
            for row in resumed["context_request_contracts"]
            if row["request_scope"] == synthesis_start["request_scope"]
        )
        self.assertEqual(resumed_contract["requested_operation_input"], resolved_input)
        self.assertEqual(
            resumed_contract["start_contract"]["requested_operation_input"],
            base_input,
        )

        second_run = self.run_for_current_workflow(
            scope=base_scope, workflow_ref=workflow_ref
        )
        self._attach_signal_batch(second_run, batch, batch_readback)
        second_readback = self.store.write("context-synthesis-run", second_run)[
            "readback"
        ]
        completed_group = context_workflow_state.handle(
            self.synthesis_request(
                second_run,
                second_readback["revision"],
                workflow_ref=workflow_ref,
                workflow_state_root=workflow_root,
                expected_revision=resumed["state_revision"],
                request_scope=synthesis_start["request_scope"],
            )
        )
        self.assertEqual(completed_group["status"], "written", completed_group)
        group = completed_group["state"]["context_synthesis_run_refs"][0]
        self.assertEqual(
            group["request_id"],
            contracts.workflow_operation_id(workflow_ref, base_input, base_scope),
        )
        self.assertEqual(group["requested_operation_input"], resolved_input)
        self.assertEqual(group["mapping"]["status"], "complete")
        self.assertEqual(len(group["run_refs"]), 2)

        source_readback = {
            "kind": "spec",
            "root_binding": self.store.root_binding,
            "artifact_ref": fixtures.SOURCE_REF,
            "revision": "r3",
            "sha256": fixtures.SOURCE_HASH,
            "content": fixtures.SOURCE_CONTENT,
        }
        completion = context_workflow_state.handle(
            {
                "operation": "completion-check",
                "workflow_state_root": str(workflow_root),
                "workflow_ref": workflow_ref,
                "artifact_root": str(self.artifact_root),
                "requested_operation_input": resolved_input,
                "requested_scope": base_scope,
                "request_scopes": [synthesis_start["request_scope"]],
                "target_batch_refs": [batch["artifact_ref"]],
                "provider_readbacks": [source_readback, batch_readback],
            }
        )
        self.assertEqual(completion["status"], "complete", completion)

        signal_scope, signal_owner = self._signal_owner_scope(
            batch,
            batch_readback,
            workflow_ref,
            workflow_root,
            [self.signal_scope_request],
        )
        first_scope, first_owner = self._synthesis_owner_scope(
            first_run,
            first_readback,
            [source_readback],
            workflow_root,
            [synthesis_start["request_scope"]],
        )
        first_scope["normalized_input"]["context_workflow_state"]["requested_scope"] = (
            copy.deepcopy(base_scope)
        )
        second_scope, second_owner = self._synthesis_owner_scope(
            second_run,
            second_readback,
            [source_readback, batch_readback],
            workflow_root,
            [synthesis_start["request_scope"]],
        )
        second_scope["normalized_input"]["context_workflow_state"][
            "requested_operation_input"
        ] = copy.deepcopy(resolved_input)
        second_scope["normalized_input"]["context_workflow_state"][
            "requested_scope"
        ] = copy.deepcopy(base_scope)
        final_scopes = [
            {
                "skill": signal_scope["skill"],
                "target": signal_scope["target"],
                "execution_range": signal_scope["execution_range"],
                "requirement": "required",
            },
            {
                "skill": first_scope["skill"],
                "target": first_scope["target"],
                "execution_range": first_scope["execution_range"],
                "requirement": "required",
            },
            {
                "skill": second_scope["skill"],
                "target": second_scope["target"],
                "execution_range": second_scope["execution_range"],
                "requirement": "required",
            },
        ]
        final = context_workflow_state.handle(
            {
                "operation": "completion-check-workflow",
                "workflow_state_root": str(workflow_root),
                "workflow_ref": workflow_ref,
                "artifact_root": str(self.artifact_root),
                "requested_scopes": final_scopes,
                "context_scopes": [signal_scope, first_scope, second_scope],
                "verified_owner_scopes": [
                    signal_owner,
                    first_owner,
                    second_owner,
                ],
                "provider_readbacks": [
                    source_readback,
                    batch_readback,
                    first_readback,
                    second_readback,
                ],
            }
        )
        self.assertEqual(final["status"], "complete", final)

    def test_requested_scope_snapshot_matches_runtime_scope_contract(self) -> None:
        workflow_root = self.base / "strict-request-scope-workflow"
        workflow_ref = self.workflow_ref
        initialized = context_workflow_state.handle(
            {
                "operation": "initialize",
                "workflow_state_root": str(workflow_root),
                "workflow_ref": workflow_ref,
                "initial_state": {"overall_state": "実行中"},
            }
        )
        invalid_rows = [
            {
                "skill": "qa-workflow",
                "target": "target",
                "execution_range": "range",
                "requirement": "required",
            },
            {
                "skill": "test-analysis",
                "target": " ",
                "execution_range": "range",
                "requirement": "required",
            },
            {
                "skill": "test-analysis",
                "target": "target",
                "execution_range": "",
                "requirement": "required",
            },
        ]

        for row in invalid_rows:
            with self.subTest(row=row):
                result = context_workflow_state.handle(
                    {
                        "operation": "register-requested-scopes",
                        "workflow_state_root": str(workflow_root),
                        "workflow_ref": workflow_ref,
                        "expected_revision": initialized["state_revision"],
                        "artifact_root": str(self.artifact_root),
                        "requested_scopes": [row],
                    }
                )
                self.assertEqual(result["status"], "blocked")
                current = context_workflow_state.handle(
                    {
                        "operation": "read",
                        "workflow_state_root": str(workflow_root),
                        "workflow_ref": workflow_ref,
                    }
                )
                self.assertEqual(
                    current["state_revision"], initialized["state_revision"]
                )

    def test_initialize_uses_existing_sqlite_state_provider_and_refuses_json_migration(
        self,
    ) -> None:
        new_root = self.base / "new-workflow-state"
        new_ref = str(uuid.uuid4())
        initial = {"overall_state": "実行中", "started_source_refs": []}
        created = context_workflow_state.handle(
            {
                "operation": "initialize",
                "workflow_state_root": str(new_root),
                "workflow_ref": new_ref,
                "initial_state": initial,
            }
        )
        self.assertEqual(created["status"], "created")
        self.assertEqual(created["state"]["context_signal_attempts"], [])
        self.assertEqual(created["state"]["context_synthesis_run_refs"], [])

        legacy_root = self.base / "legacy-workflow-state"
        legacy_ref = str(uuid.uuid4())
        legacy = artifact_graph.create_workflow_state(
            legacy_root, legacy_ref, {"overall_state": "実行中"}
        )
        blocked = context_workflow_state.handle(
            {
                "operation": "initialize",
                "workflow_state_root": str(legacy_root),
                "workflow_ref": legacy_ref,
                "initial_state": {"overall_state": "実行中"},
            }
        )
        self.assertEqual(blocked["status"], "blocked")
        self.assertEqual(
            blocked["reason"], "legacy_json_workflow_state_update_unavailable"
        )
        self.assertEqual(
            artifact_graph.read_workflow_state(legacy_root, legacy_ref)[
                "state_revision"
            ],
            legacy["state_revision"],
        )

    def test_cli_persists_and_reopens_signal_attempt_and_targeted_synthesis_run(
        self,
    ) -> None:
        workflow_root = self.base / "cli-workflow-state"
        artifact_root = self.base / "cli-context-artifacts"
        artifact_root.mkdir()
        store = context_artifact_store.DirectoryArtifactStore(artifact_root)
        batch = fixtures.build_batch()
        batch_readback = store.write("context-signal-batch", batch)["readback"]

        run = self.run_for_current_workflow()
        run_source = {
            "artifact_ref": batch["artifact_ref"],
            "content_hash": batch_readback["sha256"],
            "effective_authority_fingerprint": None,
            "source_revision": batch_readback["revision"],
        }
        run["operation_input"]["input_sources"].append(run_source)
        run["operation_input"]["input_sources"].sort(
            key=lambda item: item["artifact_ref"]
        )
        run["snapshot"]["referenced_sources"].append(
            {
                "source_kind": "signal_batch",
                "artifact_ref": batch["artifact_ref"],
                "source_revision": batch_readback["revision"],
                "content_hash": batch_readback["sha256"],
                "effective_authority_fingerprint": None,
            }
        )
        run["snapshot"]["snapshot_hash"] = contracts.snapshot_hash(run["snapshot"])
        run["triage_plan"]["target_batch_refs"] = [batch["artifact_ref"]]
        operation_id = contracts.workflow_operation_id(
            self.workflow_ref, run["operation_input"], run["requested_scope"]
        )
        run["workflow_operation_id"] = operation_id
        run["run_identity"] = contracts.run_identity(operation_id)
        run["artifact_ref"] = contracts.artifact_ref(
            "context-synthesis-run", run["run_identity"]
        )
        contracts.validate_artifact(run, "context-synthesis-run")
        synthesis_request_contract = context_workflow_state.build_request_scope(
            {
                "workflow_ref": self.workflow_ref,
                "contract": {
                    "skill": "context-rule-synthesis",
                    "requested_operation_input": run["operation_input"],
                    "requested_scope": run["requested_scope"],
                    "target_batch_refs": [batch["artifact_ref"]],
                },
            }
        )
        synthesis_request_scope = synthesis_request_contract["request_scope"]
        initialized = self._state_cli(
            {
                "operation": "initialize",
                "workflow_state_root": str(workflow_root),
                "workflow_ref": self.workflow_ref,
                "initial_state": {
                    "overall_state": "実行中",
                    "context_signal_attempts": [],
                    "context_synthesis_run_refs": [],
                    "context_request_contracts": [
                        self.signal_request_contract,
                        synthesis_request_contract["contract"],
                    ],
                    "requested_scopes": [
                        self.signal_scope_request,
                        synthesis_request_scope,
                    ],
                },
            }
        )
        self.assertEqual(initialized["status"], "created")

        after_signal = self._state_cli(
            {
                "operation": "record-signal-attempt",
                "workflow_state_root": str(workflow_root),
                "workflow_ref": self.workflow_ref,
                "expected_revision": initialized["state_revision"],
                "artifact_root": str(artifact_root),
                "record": self.signal_record(batch_readback),
            }
        )
        self.assertEqual(after_signal["status"], "written")

        run_readback = store.write("context-synthesis-run", run)["readback"]
        synthesis_request = self.synthesis_request(
            run,
            run_readback["revision"],
            request_scope=synthesis_request_scope,
        )
        synthesis_request.update(
            {
                "workflow_state_root": str(workflow_root),
                "expected_revision": after_signal["state_revision"],
                "artifact_root": str(artifact_root),
            }
        )
        after_run = self._state_cli(synthesis_request)
        self.assertEqual(after_run["status"], "written")

        reopened = self._state_cli(
            {
                "operation": "read",
                "workflow_state_root": str(workflow_root),
                "workflow_ref": self.workflow_ref,
            }
        )
        self.assertEqual(reopened["state_revision"], after_run["state_revision"])
        self.assertEqual(len(reopened["state"]["context_signal_attempts"]), 1)
        run_group = reopened["state"]["context_synthesis_run_refs"][0]
        self.assertEqual(run_group["mapping"]["status"], "complete")
        self.assertEqual(
            run_group["run_refs"][0]["target_batch_refs"], [batch["artifact_ref"]]
        )

    def test_local_store_readbacks_pass_registered_context_owner_verifiers(
        self,
    ) -> None:
        batch = fixtures.build_batch()
        batch_readback = self.store.write("context-signal-batch", batch)["readback"]
        source = batch["source"]
        requested_range = source["requested_range"]
        signal_scope = {
            "skill": "context-signal-audit",
            "target": batch["artifact_ref"],
            "execution_range": json.dumps(
                requested_range, sort_keys=True, separators=(",", ":")
            ),
            "normalized_input": {
                "owner_verification": {
                    "stored_content": batch_readback["content"],
                    "readback": batch_readback,
                    "expected_revision": batch_readback["revision"],
                    "root_binding": self.store.root_binding,
                    "requested_source_ref": source["artifact_ref"],
                    "requested_source_content_hash": source["source_content_hash"],
                    "requested_range": requested_range,
                    "observation_condition": source["observation_condition"],
                    "current_source": {
                        "artifact_ref": source["artifact_ref"],
                        "source_revision": source["source_revision"],
                        "content_hash": source["source_content_hash"],
                    },
                    "batch_readbacks": [batch_readback],
                },
                "context_request": {
                    "workflow_ref": "workflow:ctx-001",
                    "source_artifact_ref": source["artifact_ref"],
                    "source_revision": source["source_revision"],
                    "source_content_hash": source["source_content_hash"],
                    "requested_range": requested_range,
                    "assigned_range": requested_range,
                    "observation_condition": source["observation_condition"],
                },
            },
        }
        signal_result = owner_verifiers.verify("context-signal-audit", signal_scope)
        self.assertEqual(signal_result["status"], "verified", signal_result)

        run = fixtures.build_run()
        run["workflow_ref"] = self.workflow_ref
        run["operation_input"]["input_sources"].append(
            {
                "artifact_ref": batch["artifact_ref"],
                "content_hash": batch_readback["sha256"],
                "effective_authority_fingerprint": None,
                "source_revision": batch_readback["revision"],
            }
        )
        run["operation_input"]["input_sources"].sort(
            key=lambda item: item["artifact_ref"]
        )
        run["snapshot"]["referenced_sources"].append(
            {
                "source_kind": "signal_batch",
                "artifact_ref": batch["artifact_ref"],
                "source_revision": batch_readback["revision"],
                "content_hash": batch_readback["sha256"],
                "effective_authority_fingerprint": None,
            }
        )
        run["snapshot"]["referenced_sources"].sort(
            key=lambda item: (item["artifact_ref"], item["source_revision"])
        )
        run["snapshot"]["snapshot_hash"] = contracts.snapshot_hash(run["snapshot"])
        run["triage_plan"]["target_batch_refs"] = [batch["artifact_ref"]]
        operation_id = contracts.workflow_operation_id(
            run["workflow_ref"], run["operation_input"], run["requested_scope"]
        )
        run["workflow_operation_id"] = operation_id
        run["run_identity"] = contracts.run_identity(operation_id)
        run["artifact_ref"] = contracts.artifact_ref(
            "context-synthesis-run", run["run_identity"]
        )
        contracts.validate_artifact(run, "context-synthesis-run")
        run_readback = self.store.write("context-synthesis-run", run)["readback"]
        source_readback = {
            "kind": "spec",
            "root_binding": self.store.root_binding,
            "artifact_ref": fixtures.SOURCE_REF,
            "revision": "r3",
            "sha256": fixtures.SOURCE_HASH,
            "content": fixtures.SOURCE_CONTENT,
        }
        provider_readbacks = [source_readback, batch_readback, run_readback]
        run_scope = {
            "skill": "context-rule-synthesis",
            "target": run["artifact_ref"],
            "execution_range": "run:" + run["run_identity"],
            "normalized_input": {
                "owner_verification": {
                    "stored_content": run_readback["content"],
                    "readback": run_readback,
                    "expected_revision": run_readback["revision"],
                    "root_binding": self.store.root_binding,
                    "provider_readbacks": provider_readbacks,
                },
                "context_request": {
                    "workflow_ref": run["workflow_ref"],
                    "operation_input": run["operation_input"],
                    "requested_scope": run["requested_scope"],
                    "target_batch_refs": run["triage_plan"]["target_batch_refs"],
                },
            },
        }
        run_result = owner_verifiers.verify("context-rule-synthesis", run_scope)

        self.assertEqual(run_result["status"], "verified", run_result)
        self.assertEqual(len(self.store.list("context-signal-batch")["artifacts"]), 1)
        self.assertEqual(len(self.store.list("context-synthesis-run")["artifacts"]), 1)


if __name__ == "__main__":
    unittest.main()
