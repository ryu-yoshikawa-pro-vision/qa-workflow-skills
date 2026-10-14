from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
import unittest
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "skills" / "qa-workflow" / "scripts" / "downstream_state.py"
WORKFLOW_REF = "11111111-1111-4111-8111-111111111111"
_SPEC = importlib.util.spec_from_file_location("downstream_state_under_test", SCRIPT)
assert _SPEC is not None and _SPEC.loader is not None
sys.path.insert(0, str(SCRIPT.parent))
downstream_state = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(downstream_state)


def _scoped_downstream_input() -> dict[str, Any]:
    scopes = ["SCOPE-001", "SCOPE-002"]
    tcn = {
        "skill": "test-condition-design",
        "entity_type": "tcn",
        "entity_ref": "TCN-001",
        "content": {"tcn_id": "TCN-001", "scope_refs": scopes},
    }
    model = {
        "skill": "test-condition-design",
        "entity_type": "model",
        "entity_ref": "ep-001",
        "content": {
            "model_key": "ep-001",
            "model_type": "ep",
            "technique_slug": "ep",
            "parent_tcn_id": "TCN-001",
            "scope_refs": scopes,
        },
    }
    ci = {
        "skill": "test-condition-design",
        "entity_type": "ci",
        "entity_ref": "TCN-001-CI01",
        "content": {
            "ci_id": "TCN-001-CI01",
            "tcn_id": "TCN-001",
            "model_key": "ep-001",
            "scope_refs": scopes,
        },
    }
    tcn_state = [{"tcn_id": "TCN-001", "status": "active", "scope_refs": scopes}]
    model_state = [
        {
            "model_key": "ep-001",
            "model_type": "ep",
            "technique_slug": "ep",
            "parent_tcn_id": "TCN-001",
            "selection_source": "condition_design",
            "selection_key": None,
            "derived_from_model_key": None,
            "status": "active",
            "scope_refs": scopes,
        }
    ]
    ci_state = [{"ci_id": "TCN-001-CI01", "status": "active", "scope_refs": scopes}]
    materialize_history = {
        "tcn_id": "TCN-001",
        "ci_entities": [ci],
        "ci_id_state": ci_state,
        "target_mapping_state": [],
        "semantic_ci_mapping_state": [],
        "expected_result_root_state": [],
    }
    return {
        "current_entities": [tcn, model, ci],
        "workflow_scopes": [
            {
                "skill": "test-condition-design",
                "current_structure_state": {
                    "runtime_results": [
                        {
                            "identity": "test-condition-design::artifact:condition_structure:all",
                            "result": {
                                "runtime_unit_key": "artifact:condition_structure:all",
                                "payload": {
                                    "tcn_id_state": tcn_state,
                                    "model_key_state": model_state,
                                    "inactive_materialize_history": [
                                        materialize_history
                                    ],
                                },
                            },
                        }
                    ],
                    "carry_forward_entities": [],
                    "previous_ci_id_state": ci_state,
                },
            }
        ],
    }


def _resolution(entity_type: str, entity_ref: str) -> dict[str, object]:
    return {
        "skill": "test-condition-design",
        "entity_type": entity_type,
        "entity_ref": entity_ref,
        "resolution": "reuse",
        "resolved_scope_refs": ["SCOPE-001"],
    }


def _request(**overrides: object) -> dict[str, object]:
    value: dict[str, object] = {
        "workflow_ref": WORKFLOW_REF,
        "workflow_state_record": {
            "workflow_ref": WORKFLOW_REF,
            "schema_version": "1",
            "state": {"last_completed_qa_workflow_artifact": None},
        },
        "current_scope_ids": [],
        "blocked_scope_ids": [],
        "previous_qa_workflow_artifact_markdown": None,
        "scope_removal_resolutions": [],
        "scope_removal_applied_states": [],
    }
    value.update(overrides)
    return value


def _run(payload: str) -> tuple[int, dict[str, object]]:
    completed = subprocess.run(
        [sys.executable, str(SCRIPT)],
        input=payload,
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
        timeout=15,
    )
    return completed.returncode, json.loads(completed.stdout)


def _test_unbound_first_run_returns_empty_canonical_state() -> None:
    code, result = _run(json.dumps(_request()))
    assert code == 0
    assert result["valid"] is True
    assert result["payload"]["inactive_tr_ids"] == []
    assert result["payload"]["requires_semantic_resolution"] is False
    assert result["payload"]["requires_materialization"] is False


def _test_binding_null_and_markdown_are_rejected() -> None:
    code, result = _run(json.dumps(_request(previous_qa_workflow_artifact_markdown="")))
    assert code == 0, result
    assert result["valid"] is False
    assert result["payload"] is None
    assert result["issues"][0]["issue_type"] == "historical_artifact_unexpected"


def _test_workflow_ref_and_current_scope_partition_contracts_are_enforced() -> None:
    bad_state = {
        "workflow_ref": "22222222-2222-4222-8222-222222222222",
        "schema_version": "1",
        "state": {"last_completed_qa_workflow_artifact": None},
    }
    code, result = _run(json.dumps(_request(workflow_state_record=bad_state)))
    assert code == 0
    assert result["valid"] is False
    assert result["issues"][0]["issue_type"] == "invalid_input"

    code, result = _run(
        json.dumps(
            _request(current_scope_ids=["SCOPE-001"], blocked_scope_ids=["SCOPE-002"])
        )
    )
    assert code == 0
    assert result["valid"] is False
    assert result["issues"][0]["issue_type"] == "invalid_input"


def _test_duplicate_json_key_is_handled_as_invalid_input() -> None:
    code, result = _run(
        '{"workflow_ref":"x","workflow_ref":"y","workflow_state_record":{},'
        '"current_scope_ids":[],"blocked_scope_ids":[],'
        '"previous_qa_workflow_artifact_markdown":null,'
        '"scope_removal_resolutions":[],"scope_removal_applied_states":[]}'
    )
    assert code == 0
    assert result["valid"] is False
    assert result["issues"][0]["issue_type"] == "invalid_input"


def _test_cli_enforces_size_limits_and_historical_binding_contracts() -> None:
    from runtime_contract import MAX_AGGREGATE_INPUT_BYTES

    code, result = _run(json.dumps({**_request(), "unexpected": True}))
    assert code == 0
    assert result["valid"] is False
    assert result["issues"][0]["issue_type"] == "invalid_input"

    oversized = _run(" " * (MAX_AGGREGATE_INPUT_BYTES + 1))
    assert oversized[0] == 0
    assert oversized[1]["valid"] is False
    assert oversized[1]["payload"] is None
    assert oversized[1]["issues"][0]["issue_type"] == "limit_exceeded"

    too_large_field = _request(workflow_ref="x" * (64 * 1024 + 1))
    code, result = _run(json.dumps(too_large_field))
    assert code == 0
    assert result["valid"] is False
    assert result["issues"][0]["issue_type"] == "limit_exceeded"

    large_markdown_without_binding = _request(
        previous_qa_workflow_artifact_markdown="x" * (64 * 1024 + 1)
    )
    code, result = _run(json.dumps(large_markdown_without_binding))
    assert code == 0
    assert result["valid"] is False
    assert result["issues"][0]["issue_type"] == "historical_artifact_unexpected"

    binding = {
        "artifact_ref": "artifact:qa-workflow:test",
        "artifact_revision": "revision-001",
        "artifact_sha256": "0" * 64,
    }
    state_record = {
        "workflow_ref": WORKFLOW_REF,
        "schema_version": "1",
        "state": {"last_completed_qa_workflow_artifact": binding},
    }
    code, result = _run(json.dumps(_request(workflow_state_record=state_record)))
    assert code == 0
    assert result["valid"] is False
    assert result["issues"][0]["issue_type"] == "historical_artifact_required"

    markdown = "# Not a historical QA workflow artifact\n" + ("x" * (64 * 1024 + 1))
    code, result = _run(
        json.dumps(
            _request(
                workflow_state_record=state_record,
                previous_qa_workflow_artifact_markdown=markdown,
            )
        )
    )
    assert code == 0
    assert result["valid"] is False
    assert result["issues"][0]["issue_type"] == "historical_artifact_hash_mismatch"

    digest = hashlib.sha256(markdown.encode("utf-8")).hexdigest()
    state_record["state"]["last_completed_qa_workflow_artifact"]["artifact_sha256"] = (
        digest
    )
    code, result = _run(
        json.dumps(
            _request(
                workflow_state_record=state_record,
                previous_qa_workflow_artifact_markdown=markdown,
            )
        )
    )
    assert code == 0
    assert result["valid"] is False
    assert result["issues"][0]["issue_type"] == "historical_runtime_invalid"


def _test_cli_maps_scope_history_failures_and_internal_errors() -> None:
    raw_request = json.dumps(_request()).encode("utf-8")
    cases = [
        (
            downstream_state.InvalidInput("scope ownership unavailable"),
            "scope_ownership_unavailable",
            0,
        ),
        (
            downstream_state.InvalidInput("inactive materialize history is missing"),
            "inactive_materialize_history_missing",
            0,
        ),
        (
            downstream_state.InvalidInput("last-active Entity snapshot is missing"),
            "scope_removal_history_missing",
            0,
        ),
        (RuntimeError("unexpected failure"), "internal_error", 1),
    ]
    for error, issue_type, expected_exit_code in cases:
        output = BytesIO()
        with (
            patch.object(
                downstream_state.sys,
                "stdin",
                SimpleNamespace(buffer=BytesIO(raw_request)),
            ),
            patch.object(
                downstream_state.sys,
                "stdout",
                SimpleNamespace(buffer=output),
            ),
            patch.object(downstream_state, "evaluate", side_effect=error),
        ):
            exit_code = downstream_state.main()
        result = json.loads(output.getvalue())
        assert exit_code == expected_exit_code, result
        assert result["valid"] is False, result
        assert result["payload"] is None, result
        assert len(result["issues"]) == 1, result
        assert result["issues"][0]["issue_type"] == issue_type, result
        assert result["issues"][0]["blocking"] is True, result


def _test_historical_v2_pair_is_checked_before_unscoped_active_state_fails_closed() -> (
    None
):
    workflow_test_path = (
        ROOT / "tests" / "skills" / "runtime" / "test_workflow_runtime.py"
    )
    spec = importlib.util.spec_from_file_location(
        "workflow_runtime_test_fixtures", workflow_test_path
    )
    assert spec is not None and spec.loader is not None
    fixture_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fixture_module)
    source, _parts = fixture_module.WorkflowRuntimeTests()._partial_scope_request()
    module_runtime = fixture_module.runtime
    for scope in source["input"]["workflow_scopes"]:
        for row in scope["current_structure_state"]["runtime_results"]:
            result = row["result"]
            result["generation_fingerprint"] = module_runtime.generation_fingerprint(
                generator=result["generator"],
                input_fp=result["input_fingerprint"],
                model_fp=result["model_fingerprint"],
                runtime_contract_version=result["runtime_contract_version"],
                generator_contract_version=result["generator_contract_version"],
                runtime_impl_fp=result["runtime_implementation_fingerprint"],
                generator_impl_fp=result["generator_implementation_fingerprint"],
                upstream=result["upstream_entity_fingerprints"],
                static_data_versions=result["static_data_versions"],
            )
            result["payload"]["tcn_id_state"] = [
                {"tcn_id": "TCN-001", "status": "active", "scope_refs": []},
                {"tcn_id": "TCN-002", "status": "active", "scope_refs": []},
            ]
            result["payload"]["model_key_state"] = [
                {"model_key": "ep-001", "status": "active", "scope_refs": []},
                {"model_key": "ep-002", "status": "active", "scope_refs": []},
            ]
            refreshed_row = module_runtime.runtime_unit_row(result)
            for field in ("runtime_units", "current_runtime_units"):
                source_rows = source["input"][field]
                for index, unit in enumerate(source_rows):
                    if (
                        unit.get("skill") == refreshed_row["skill"]
                        and unit.get("runtime_unit_key")
                        == refreshed_row["runtime_unit_key"]
                    ):
                        source_rows[index] = refreshed_row
    workflow_cli = ROOT / "skills" / "qa-workflow" / "scripts" / "workflow_runtime.py"
    runtime = subprocess.run(
        [sys.executable, str(workflow_cli)],
        input=json.dumps(source, ensure_ascii=False),
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
        timeout=20,
    )
    assert runtime.returncode == 0, runtime.stdout + runtime.stderr
    envelope = json.loads(runtime.stdout)
    markdown = (
        module_runtime.render_runtime_input(
            "qa-workflow", source["metadata"], source["input"]
        )
        + module_runtime.render_runtime_result("qa-workflow", envelope)
        + module_runtime.render_machine_entities("qa-workflow", [])
    )
    sha = hashlib.sha256(markdown.encode("utf-8")).hexdigest()
    state_record = {
        "workflow_ref": source["input"]["workflow_ref"],
        "schema_version": "1",
        "state": {
            "last_completed_qa_workflow_artifact": {
                "artifact_ref": "artifact:qa-workflow:test",
                "artifact_revision": "revision-001",
                "artifact_sha256": sha,
            }
        },
    }
    request = _request(
        workflow_ref=source["input"]["workflow_ref"],
        workflow_state_record=state_record,
        current_scope_ids=["SCOPE-001"],
        blocked_scope_ids=[],
        previous_qa_workflow_artifact_markdown=markdown,
    )
    code, result = _run(json.dumps(request, ensure_ascii=False))
    assert code == 0, result
    assert result["valid"] is False
    assert result["issues"][0]["issue_type"] == "scope_ownership_unavailable", result


class TestDownstreamState(unittest.TestCase):
    def test_unbound_first_run_returns_empty_canonical_state(self) -> None:
        _test_unbound_first_run_returns_empty_canonical_state()

    def test_binding_null_and_markdown_are_rejected(self) -> None:
        _test_binding_null_and_markdown_are_rejected()

    def test_workflow_ref_and_current_scope_partition_contracts_are_enforced(
        self,
    ) -> None:
        _test_workflow_ref_and_current_scope_partition_contracts_are_enforced()

    def test_duplicate_json_key_is_handled_as_invalid_input(self) -> None:
        _test_duplicate_json_key_is_handled_as_invalid_input()

    def test_cli_enforces_size_limits_and_historical_binding_contracts(self) -> None:
        _test_cli_enforces_size_limits_and_historical_binding_contracts()

    def test_cli_maps_scope_history_failures_and_internal_errors(self) -> None:
        _test_cli_maps_scope_history_failures_and_internal_errors()

    def test_historical_v2_pair_is_checked_before_unscoped_active_state_fails_closed(
        self,
    ) -> None:
        _test_historical_v2_pair_is_checked_before_unscoped_active_state_fails_closed()

    def test_blocked_scope_projects_inactive_identity_and_materialize_history(
        self,
    ) -> None:
        result = downstream_state._scope_impact(
            _scoped_downstream_input(),
            ["SCOPE-001", "SCOPE-002"],
            ["SCOPE-002"],
            [],
            [],
        )
        self.assertEqual(result["inactive_tcn_ids"], ["TCN-001"])
        self.assertEqual(result["inactive_model_keys"], ["ep-001"])
        self.assertEqual(result["inactive_ci_ids"], ["TCN-001-CI01"])
        self.assertEqual(
            result["inactive_materialize_history"],
            _scoped_downstream_input()["workflow_scopes"][0]["current_structure_state"][
                "runtime_results"
            ][0]["result"]["payload"]["inactive_materialize_history"],
        )

    def test_blocked_scope_fails_closed_when_materialize_history_is_missing(
        self,
    ) -> None:
        source = _scoped_downstream_input()
        source["workflow_scopes"][0]["current_structure_state"]["runtime_results"][0][
            "result"
        ]["payload"]["inactive_materialize_history"] = []
        with self.assertRaisesRegex(
            downstream_state.InvalidInput, "inactive materialize history is missing"
        ):
            downstream_state._scope_impact(
                source,
                ["SCOPE-001", "SCOPE-002"],
                ["SCOPE-002"],
                [],
                [],
            )

    def test_scope_removal_rejects_split_as_a_resolution(self) -> None:
        resolution = _resolution("tcn", "TCN-001")
        resolution["resolution"] = "split"
        with self.assertRaisesRegex(
            downstream_state.InvalidInput, "resolution is duplicated or invalid"
        ):
            downstream_state._validate_resolution_rows([resolution], ["SCOPE-001"])

    def test_retired_scope_resolution_waits_for_applied_state_and_zero_scope_deletes(
        self,
    ) -> None:
        source = _scoped_downstream_input()
        resolutions = [
            _resolution("tcn", "TCN-001"),
            _resolution("model", "ep-001"),
        ]
        pending = downstream_state._scope_impact(
            source, ["SCOPE-001"], [], resolutions, []
        )
        self.assertEqual(pending["removed_scope_ids"], ["SCOPE-002"])
        self.assertEqual(
            pending["scope_removal_affected_entities"][0]["last_active_content"][
                "scope_refs"
            ],
            ["SCOPE-001", "SCOPE-002"],
        )
        self.assertEqual(
            pending["scope_removal_state_transitions"],
            [
                {
                    "skill": "test-condition-design",
                    "entity_type": "ci",
                    "entity_ref": "TCN-001-CI01",
                    "resolved_scope_refs": ["SCOPE-001"],
                    "status": "active",
                },
                {
                    "skill": "test-condition-design",
                    "entity_type": "model",
                    "entity_ref": "ep-001",
                    "resolved_scope_refs": ["SCOPE-001"],
                    "status": "active",
                },
                {
                    "skill": "test-condition-design",
                    "entity_type": "tcn",
                    "entity_ref": "TCN-001",
                    "resolved_scope_refs": ["SCOPE-001"],
                    "status": "active",
                },
            ],
        )
        self.assertIs(pending["requires_semantic_resolution"], False)
        self.assertIs(pending["requires_materialization"], True)

        applied = [
            {
                "skill": row["skill"],
                "entity_type": row["entity_type"],
                "entity_ref": row["entity_ref"],
                "status": row["status"],
                "scope_refs": row["resolved_scope_refs"],
            }
            for row in pending["scope_removal_state_transitions"]
        ]
        complete = downstream_state._scope_impact(
            source, ["SCOPE-001"], [], resolutions, applied
        )
        self.assertIs(complete["requires_materialization"], False)

        terminal = downstream_state._scope_impact(source, [], [], [], [])
        self.assertIs(terminal["zero_scope_terminal"], True)
        self.assertEqual(terminal["inactive_tcn_ids"], [])
        self.assertEqual(terminal["inactive_model_keys"], [])
        self.assertEqual(terminal["inactive_ci_ids"], [])
        self.assertEqual(
            {row["status"] for row in terminal["scope_removal_state_transitions"]},
            {"deleted"},
        )

    def test_ci_state_is_processed_once_for_a_scope_with_multiple_runtime_results(
        self,
    ) -> None:
        source = _scoped_downstream_input()
        source["workflow_scopes"][0]["current_structure_state"][
            "runtime_results"
        ].append(
            {
                "identity": "test-condition-design::model:ep-001",
                "result": {
                    "runtime_unit_key": "model:ep-001",
                    "payload": {},
                },
            }
        )
        result = downstream_state._scope_impact(
            source,
            ["SCOPE-001", "SCOPE-002"],
            ["SCOPE-002"],
            [],
            [],
        )
        self.assertEqual(result["inactive_ci_ids"], ["TCN-001-CI01"])
        self.assertEqual(result["inactive_tcn_ids"], ["TCN-001"])
        self.assertEqual(result["inactive_model_keys"], ["ep-001"])
