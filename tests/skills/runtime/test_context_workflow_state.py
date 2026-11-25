from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
import uuid
from pathlib import Path

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


class ContextWorkflowStateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.workflow_root = self.base / "workflow-state"
        self.artifact_root = self.base / "context-artifacts"
        self.artifact_root.mkdir()
        self.workflow_ref = str(uuid.uuid4())
        created = artifact_graph.create_sqlite_workflow_state(
            self.workflow_root,
            self.workflow_ref,
            {
                "overall_state": "実行中",
                "started_source_refs": [fixtures.SOURCE_REF],
                "existing_owner_data": {"preserve": True},
                "context_signal_attempts": [],
                "context_synthesis_run_refs": [],
            },
        )
        self.revision = created["state_revision"]
        self.store = context_artifact_store.DirectoryArtifactStore(self.artifact_root)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def signal_record(self, batch_readback: dict) -> dict:
        operation_id = contracts.workflow_operation_id(
            self.workflow_ref, fixtures.operation_input(), fixtures.requested_scope()
        )
        return {
            "attempt_id": "1" * 64,
            "workflow_operation_id": operation_id,
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

    def run_for_current_workflow(self, scope: dict | None = None) -> dict:
        run = fixtures.build_run()
        run["workflow_ref"] = self.workflow_ref
        if scope is not None:
            run["requested_scope"] = copy.deepcopy(scope)
        operation_id = contracts.workflow_operation_id(
            self.workflow_ref, run["operation_input"], run["requested_scope"]
        )
        run["workflow_operation_id"] = operation_id
        run["run_identity"] = contracts.run_identity(operation_id)
        run["artifact_ref"] = contracts.artifact_ref(
            "context-synthesis-run", run["run_identity"]
        )
        contracts.validate_artifact(run, "context-synthesis-run")
        return run

    def synthesis_request(self, run: dict, revision: str) -> dict:
        return {
            "operation": "record-synthesis-run",
            "workflow_state_root": str(self.workflow_root),
            "workflow_ref": self.workflow_ref,
            "expected_revision": self.revision,
            "artifact_root": str(self.artifact_root),
            "run_ref": run["artifact_ref"],
            "run_revision": revision,
            "requested_operation_input": copy.deepcopy(run["operation_input"]),
            "requested_scope": copy.deepcopy(run["requested_scope"]),
        }

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
        first_run = self.run_for_current_workflow(
            {**full_scope, "scope_refs": ["feature:refund"]}
        )
        first = self.store.write("context-synthesis-run", first_run)["readback"]
        first_request = self.synthesis_request(first_run, first["revision"])
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

        second_run = self.run_for_current_workflow(
            {**full_scope, "scope_refs": ["feature:cancel"]}
        )
        second = self.store.write("context-synthesis-run", second_run)["readback"]
        second_request = self.synthesis_request(second_run, second["revision"])
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
        self.assertEqual(result["reason"], "run_start_input_mismatch")

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
        initialized = self._state_cli(
            {
                "operation": "initialize",
                "workflow_state_root": str(workflow_root),
                "workflow_ref": self.workflow_ref,
                "initial_state": {
                    "overall_state": "実行中",
                    "context_signal_attempts": [],
                    "context_synthesis_run_refs": [],
                },
            }
        )
        self.assertEqual(initialized["status"], "created")

        store = context_artifact_store.DirectoryArtifactStore(artifact_root)
        batch = fixtures.build_batch()
        batch_readback = store.write("context-signal-batch", batch)["readback"]
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
        run_readback = store.write("context-synthesis-run", run)["readback"]
        synthesis_request = self.synthesis_request(run, run_readback["revision"])
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
