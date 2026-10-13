from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "skills" / "qa-workflow" / "scripts" / "downstream_state.py"
WORKFLOW_REF = "11111111-1111-4111-8111-111111111111"


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


def test_unbound_first_run_returns_empty_canonical_state() -> None:
    code, result = _run(json.dumps(_request()))
    assert code == 0
    assert result["valid"] is True
    assert result["payload"]["inactive_tr_ids"] == []
    assert result["payload"]["requires_semantic_resolution"] is False
    assert result["payload"]["requires_materialization"] is False


def test_binding_null_and_markdown_are_rejected() -> None:
    code, result = _run(json.dumps(_request(previous_qa_workflow_artifact_markdown="")))
    assert code == 0, result
    assert result["valid"] is False
    assert result["payload"] is None
    assert result["issues"][0]["issue_type"] == "historical_artifact_unexpected"


def test_workflow_ref_and_current_scope_partition_contracts_are_enforced() -> None:
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


def test_duplicate_json_key_is_handled_as_invalid_input() -> None:
    code, result = _run(
        '{"workflow_ref":"x","workflow_ref":"y","workflow_state_record":{},'
        '"current_scope_ids":[],"blocked_scope_ids":[],'
        '"previous_qa_workflow_artifact_markdown":null,'
        '"scope_removal_resolutions":[],"scope_removal_applied_states":[]}'
    )
    assert code == 0
    assert result["valid"] is False
    assert result["issues"][0]["issue_type"] == "invalid_input"


def test_historical_v2_pair_is_checked_before_unscoped_active_state_fails_closed() -> (
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
