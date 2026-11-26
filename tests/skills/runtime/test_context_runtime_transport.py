from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "skills" / "qa-workflow" / "scripts"
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests" / "skills" / "runtime"))
sys.path.insert(0, str(SCRIPTS))

import context_artifact_store  # noqa: E402
import context_artifacts as contracts  # noqa: E402
import context_workflow_state  # noqa: E402
import downstream_state  # noqa: E402
import runtime_contract as runtime  # noqa: E402
import test_context_artifacts as context_fixtures  # noqa: E402
import test_workflow_runtime as workflow_fixtures  # noqa: E402


def owner_scope(content: str, *, skill: str = "context-rule-synthesis") -> dict:
    return {
        "skill": skill,
        "target": "context-synthesis-run/" + "a" * 64 + ".json",
        "execution_range": "run:identity",
        "input_mode": "artifact",
        "normalized_input": {
            "owner_verification": {
                "stored_content": content,
                "readback": {"content": content},
                "provider_readbacks": [
                    {
                        "artifact_ref": "context-rule-candidate/" + "b" * 64 + ".json",
                        "revision": "r1",
                        "sha256": "b" * 64,
                        "content": content,
                    }
                ],
            }
        },
        "current_structure_state": None,
    }


def workflow_transport(content: str, *, skill: str = "context-rule-synthesis") -> dict:
    return {"workflow_scopes": [owner_scope(content, skill=skill)]}


def _resize_canonical_text(
    artifact: dict,
    target_bytes: int,
    setter,
    finalize,
) -> dict:
    """Set one payload field so the validated canonical artifact has an exact byte size."""
    prefix = '日本語 "quoted" \\ path\n'
    setter(prefix)
    finalize()
    padding = target_bytes - len(contracts.canonical_bytes(artifact))
    if padding < 0:
        raise AssertionError("canonical fixture prefix exceeds target size")
    setter(prefix + ("x" * padding))
    finalize()
    if len(contracts.canonical_bytes(artifact)) != target_bytes:
        raise AssertionError("canonical fixture did not reach the requested size")
    return artifact


def _sized_batch(target_bytes: int, section: str) -> dict:
    batch = context_fixtures.build_batch()
    requested_range = {"kind": "sections", "items": [section]}
    source = batch["source"]
    source["requested_range"] = requested_range
    source["actual_inspected_range"] = requested_range
    batch["batch_identity"] = contracts.batch_identity(
        source["artifact_ref"],
        source["source_content_hash"],
        requested_range,
        source["observation_condition"],
    )
    batch["artifact_ref"] = contracts.artifact_ref(
        "context-signal-batch", batch["batch_identity"]
    )
    signal = batch["signals"][0]
    signal["observation_locator"]["section_id"] = section
    signal["signal_identity"] = contracts.signal_identity(
        source["artifact_ref"],
        signal["observation_locator"],
        source["source_content_hash"],
    )

    def finalize() -> None:
        signal["signal_content_hash"] = contracts.signal_content_hash(signal)

    _resize_canonical_text(
        batch,
        target_bytes,
        lambda value: signal.__setitem__("fact_summary", value),
        finalize,
    )
    contracts.validate_artifact(batch, "context-signal-batch")
    return batch


def _sized_candidate(target_bytes: int, index: int) -> dict:
    candidate = context_fixtures.build_candidate()
    candidate["identity_key"]["normalized_assertion"] = (
        f"eligible purchases are refundable ({index})"
    )
    identity = contracts.candidate_identity(candidate["identity_key"])
    candidate["candidate_identity"] = identity
    candidate["artifact_ref"] = contracts.artifact_ref(
        "context-rule-candidate", identity
    )
    _resize_canonical_text(
        candidate,
        target_bytes,
        lambda value: candidate.__setitem__("rule_statement", value),
        lambda: None,
    )
    contracts.validate_artifact(candidate, "context-rule-candidate")
    return candidate


def _sized_run(
    target_bytes: int,
    candidate: dict,
    candidate_readback: dict,
    index: int,
    workflow_ref: str,
) -> dict:
    run = context_fixtures.build_run()
    requested_scope = context_fixtures.requested_scope()
    operation_input = context_fixtures.operation_input()
    operation_input["input_sources"] = [
        {
            "artifact_ref": candidate["artifact_ref"],
            "content_hash": candidate_readback["sha256"],
            "effective_authority_fingerprint": None,
            "source_revision": candidate_readback["revision"],
        }
    ]
    operation_id = contracts.workflow_operation_id(
        workflow_ref, operation_input, requested_scope
    )
    run.update(
        {
            "workflow_ref": workflow_ref,
            "workflow_operation_id": operation_id,
            "run_identity": contracts.run_identity(operation_id),
            "artifact_ref": contracts.artifact_ref(
                "context-synthesis-run", operation_id
            ),
            "operation_input": operation_input,
            "requested_scope": requested_scope,
        }
    )
    run["snapshot"]["referenced_sources"] = [
        {
            "source_kind": "candidate",
            "artifact_ref": candidate["artifact_ref"],
            "source_revision": candidate_readback["revision"],
            "content_hash": candidate_readback["sha256"],
            "effective_authority_fingerprint": None,
        }
    ]
    operation = {
        "candidate_identity": candidate["candidate_identity"],
        "candidate_ref": candidate["artifact_ref"],
        "action": "reuse",
        "base_content_hash": candidate_readback["sha256"],
        "expected_revision": candidate_readback["revision"],
        "related_preconditions": [],
        "operation_id": f"reuse-{candidate['candidate_identity']}",
        "planned_content_hash": candidate_readback["sha256"],
        "planned_payload": None,
        "write_request_meta": {
            "source_ref": candidate["artifact_ref"],
            "source_revision": candidate_readback["revision"],
            "approval_ref": "no-change",
            "approval_revision": "no-change",
            "change_reason": "verified unchanged candidate",
        },
        "confirmed_result": {
            "artifact_ref": candidate["artifact_ref"],
            "storage_revision": candidate_readback["revision"],
            "content_hash": candidate_readback["sha256"],
        },
    }
    run["triage_plan"]["target_batch_refs"] = []
    run["triage_plan"]["planned_candidate_ops"] = [operation]
    run["result_summary"] = {
        "status": "completed_zero_changes",
        "zero_change_reason": "no_related_candidates",
        "unresolved_and_handoff_refs": [],
    }

    def refresh_snapshot_hash() -> None:
        run["snapshot"]["snapshot_hash"] = contracts.snapshot_hash(run["snapshot"])

    _resize_canonical_text(
        run,
        target_bytes,
        lambda value: run["snapshot"].__setitem__("search_criteria", value),
        refresh_snapshot_hash,
    )
    contracts.validate_artifact(run, "context-synthesis-run")
    return run


def _signal_scope(batch: dict, readback: dict, root_binding: str) -> dict:
    source = batch["source"]
    request = {
        "workflow_ref": "workflow:context-transport-signal",
        "source_artifact_ref": source["artifact_ref"],
        "source_revision": source["source_revision"],
        "source_content_hash": source["source_content_hash"],
        "requested_range": source["requested_range"],
        "assigned_range": source["requested_range"],
        "observation_condition": source["observation_condition"],
    }
    evidence = {
        "stored_content": readback["content"],
        "readback": readback,
        "expected_revision": readback["revision"],
        "root_binding": root_binding,
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
    }
    return {
        "skill": "context-signal-audit",
        "target": batch["artifact_ref"],
        "execution_range": json.dumps(
            request["assigned_range"],
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ),
        "input_mode": "artifact",
        "normalized_input": {
            "owner_verification": evidence,
            "context_request": request,
        },
        "current_structure_state": None,
    }


def _run_scope(
    run: dict,
    run_readback: dict,
    candidate_readback: dict,
    root_binding: str,
    workflow_state_request: dict,
) -> dict:
    evidence = {
        "stored_content": run_readback["content"],
        "readback": run_readback,
        "expected_revision": run_readback["revision"],
        "root_binding": root_binding,
        "provider_readbacks": [candidate_readback, run_readback],
    }
    request = {
        "workflow_ref": run["workflow_ref"],
        "operation_input": run["operation_input"],
        "requested_scope": run["requested_scope"],
        "target_batch_refs": run["triage_plan"]["target_batch_refs"],
    }
    return {
        "skill": "context-rule-synthesis",
        "target": run["artifact_ref"],
        "execution_range": "run:" + run["run_identity"],
        "input_mode": "artifact",
        "normalized_input": {
            "owner_verification": evidence,
            "context_workflow_state": workflow_state_request,
            "context_request": request,
        },
        "current_structure_state": None,
    }


class ContextRuntimeTransportTests(unittest.TestCase):
    def test_64_kib_boundary_is_byte_based_and_narrowly_exempted(self) -> None:
        at_limit = "a" * runtime.MAX_STRING_BYTES
        above_limit = "a" * (runtime.MAX_STRING_BYTES + 1)
        self.assertEqual(
            runtime.strict_loads(json.dumps({"value": at_limit}).encode("utf-8"))[
                "value"
            ],
            at_limit,
        )
        with self.assertRaises(runtime.LimitExceeded):
            runtime.strict_loads(json.dumps({"value": above_limit}).encode("utf-8"))

        accepted = workflow_transport(above_limit)
        self.assertEqual(
            runtime.strict_loads(json.dumps(accepted).encode("utf-8"), aggregate=True),
            accepted,
        )
        # The exception is registered-owner and exact-field scoped. Other fields
        # inside the same owner evidence keep the ordinary limit.
        accepted["workflow_scopes"][0]["normalized_input"]["owner_verification"][
            "diagnostic"
        ] = above_limit
        with self.assertRaises(runtime.LimitExceeded):
            runtime.strict_loads(json.dumps(accepted).encode("utf-8"), aggregate=True)

    def test_unregistered_or_misplaced_large_content_is_rejected(self) -> None:
        too_large = "x" * (runtime.MAX_STRING_BYTES + 1)
        for value in (
            workflow_transport(too_large, skill="qa-workflow"),
            {
                "workflow_scopes": [
                    {
                        "skill": "context-rule-synthesis",
                        "owner_verification": {"stored_content": too_large},
                    }
                ]
            },
            {"stored_content": too_large},
        ):
            with self.subTest(value=value.keys()):
                with self.assertRaises(runtime.LimitExceeded):
                    runtime.strict_loads(
                        json.dumps(value).encode("utf-8"), aggregate=True
                    )

    def test_downstream_frozen_tree_uses_the_same_exact_owner_paths(self) -> None:
        content = "日" * 22_000
        transport = workflow_transport(content)
        allowed = runtime._owner_transport_paths(transport)
        self.assertTrue(allowed)
        downstream_state._check_tree(transport, allowed_large_strings=allowed)
        with self.assertRaises(runtime.LimitExceeded):
            downstream_state._check_tree(transport)
        changed = workflow_transport(content, skill="qa-workflow")
        with self.assertRaises(runtime.LimitExceeded):
            downstream_state._check_tree(
                changed, allowed_large_strings=runtime._owner_transport_paths(changed)
            )

    def test_canonical_artifacts_cross_runtime_completion_and_resume_at_size_boundaries(
        self,
    ) -> None:
        workflow_ref = "00000000-0000-4000-8000-0000000000ab"
        sizes = (
            runtime.MAX_STRING_BYTES - 1,
            runtime.MAX_STRING_BYTES,
            runtime.MAX_STRING_BYTES + 1,
        )
        metadata = workflow_fixtures.metadata()
        scopes: list[dict] = []
        requested: list[dict] = []

        with tempfile.TemporaryDirectory() as root:
            store = context_artifact_store.DirectoryArtifactStore(root)
            workflow_state_root = str(Path(root) / "workflow-state")
            initialized = context_workflow_state.handle(
                {
                    "operation": "initialize",
                    "workflow_state_root": workflow_state_root,
                    "workflow_ref": workflow_ref,
                    "initial_state": {
                        "overall_state": "実行中",
                        "context_signal_attempts": [],
                        "context_synthesis_run_refs": [],
                    },
                }
            )
            self.assertEqual(initialized["status"], "created")
            state_revision = initialized["state_revision"]
            for index, target_bytes in enumerate(sizes, start=1):
                batch = _sized_batch(target_bytes, f"SEC-{index}")
                batch_readback = store.write("context-signal-batch", batch)["readback"]
                self.assertEqual(
                    len(batch_readback["content"].encode("utf-8")), target_bytes
                )
                scopes.append(_signal_scope(batch, batch_readback, store.root_binding))
                requested.append(
                    workflow_fixtures.required_scope(
                        "context-signal-audit",
                        batch["artifact_ref"],
                        scopes[-1]["execution_range"],
                    )
                )

                candidate = _sized_candidate(target_bytes, index)
                candidate_readback = store.write("context-rule-candidate", candidate)[
                    "readback"
                ]
                self.assertEqual(
                    len(candidate_readback["content"].encode("utf-8")), target_bytes
                )
                run = _sized_run(
                    target_bytes,
                    candidate,
                    candidate_readback,
                    index,
                    workflow_ref,
                )
                run_readback = store.write("context-synthesis-run", run)["readback"]
                self.assertEqual(
                    len(run_readback["content"].encode("utf-8")), target_bytes
                )
                workflow_state_request = {
                    "artifact_root": str(root),
                    "workflow_state_root": workflow_state_root,
                    "requested_operation_input": run["operation_input"],
                    "requested_scope": run["requested_scope"],
                }
                state_result = context_workflow_state.handle(
                    {
                        "operation": "record-synthesis-run",
                        "workflow_state_root": workflow_state_root,
                        "workflow_ref": workflow_ref,
                        "expected_revision": state_revision,
                        "artifact_root": str(root),
                        "run_ref": run["artifact_ref"],
                        "run_revision": run_readback["revision"],
                        "requested_operation_input": run["operation_input"],
                        "requested_scope": run["requested_scope"],
                    }
                )
                self.assertEqual(state_result["status"], "written", state_result)
                state_revision = state_result["state_revision"]
                scopes.append(
                    _run_scope(
                        run,
                        run_readback,
                        candidate_readback,
                        store.root_binding,
                        workflow_state_request,
                    )
                )
                requested.append(
                    workflow_fixtures.required_scope(
                        "context-rule-synthesis",
                        run["artifact_ref"],
                        scopes[-1]["execution_range"],
                    )
                )

            value = {
                "workflow_ref": workflow_ref,
                "requested_scopes": requested,
                "workflow_scopes": scopes,
                "runtime_units": [],
                "current_runtime_units": [],
                "current_entities": [],
                "unsupported_item_closures": [],
            }
            result = workflow_fixtures.run({"metadata": metadata, "input": value})
            self.assertEqual(result["runtime_status"], "ok", result)
            self.assertEqual(result["result_status"], "ready", result)
            self.assertTrue(result["payload"]["can_complete"], result)
            self.assertEqual(
                {row["skill"] for row in result["payload"]["verified_owner_scopes"]},
                {"context-signal-audit", "context-rule-synthesis"},
            )

            root_id = "qa-workflow::artifact:workflow_runtime:all"
            markdown = (
                f"### Machine Runtime Input: {root_id}\n\n```json\n"
                + json.dumps({"metadata": metadata, "input": value}, ensure_ascii=False)
                + f"\n```\n\n### Machine Runtime Result: {root_id}\n\n```json\n"
                + json.dumps(result, ensure_ascii=False)
                + "\n```\n"
            )
            frozen_input, frozen_result = downstream_state._validate_frozen_pair(
                markdown, workflow_ref
            )
            self.assertTrue(frozen_result["can_complete"])
            self.assertEqual(frozen_input["requested_scopes"], requested)
            resumed = downstream_state.evaluate(
                {
                    "workflow_ref": workflow_ref,
                    "workflow_state_record": {
                        "workflow_ref": workflow_ref,
                        "schema_version": "1",
                        "state": {
                            "last_completed_qa_workflow_artifact": {
                                "artifact_ref": "artifact:qa-workflow-r1",
                                "artifact_revision": "qa-workflow-r1",
                                "artifact_sha256": hashlib.sha256(
                                    markdown.encode("utf-8")
                                ).hexdigest(),
                            }
                        },
                    },
                    "current_scope_ids": [],
                    "blocked_scope_ids": [],
                    "previous_qa_workflow_artifact_markdown": markdown,
                    "scope_removal_resolutions": [],
                    "scope_removal_applied_states": [],
                }
            )
            self.assertTrue(resumed["valid"], resumed)

    def test_all_skill_runtime_contract_copies_are_synchronized(self) -> None:
        copies = sorted((ROOT / "skills").glob("*/scripts/runtime_contract.py"))
        self.assertEqual(len(copies), 9)
        self.assertEqual(len({path.read_bytes() for path in copies}), 1)


if __name__ == "__main__":
    unittest.main()
