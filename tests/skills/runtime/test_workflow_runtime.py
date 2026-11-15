from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "skills" / "qa-workflow" / "scripts" / "workflow_runtime.py"
RUNTIME_PATH = REPO_ROOT / "skills" / "qa-workflow" / "scripts" / "runtime_contract.py"
SPEC = importlib.util.spec_from_file_location(
    "qa_workflow_runtime_contract", RUNTIME_PATH
)
assert SPEC is not None and SPEC.loader is not None
runtime = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = runtime
SPEC.loader.exec_module(runtime)

_make_machine_entity = runtime.make_machine_entity


def _make_v2_machine_entity(
    skill: str, entity_type: str, entity_ref: str, content: dict, **kwargs: object
) -> dict:
    if entity_type in {"tr", "tcn", "model", "ci", "tc"}:
        content = {**content}
        content.setdefault("scope_refs", [])
    return _make_machine_entity(skill, entity_type, entity_ref, content, **kwargs)


runtime.make_machine_entity = _make_v2_machine_entity


def metadata() -> dict:
    return {
        "envelope_version": "1",
        "skill": "qa-workflow",
        "runtime_contract_version": "runtime-v2",
        "generator_contract_version": "workflow-runtime-v2",
        "runtime_unit_key": "artifact:workflow_runtime:all",
        "model_key": None,
        "model_type": None,
        "technique_slug": None,
        "selection_source": None,
        "selection_key": None,
        "scope_key": "all",
        "input_mode": "artifact",
        "upstream_entities": [],
        "upstream_runtime_units": [],
        "static_data_versions": {},
        "authority_refs": [],
        "reference_refs": [],
    }


def runtime_row(
    skill: str,
    unit: str,
    model_key: str | None = None,
    *,
    materialize: bool = False,
    active_ci_ids: list[str] | None = None,
    materialize_model_key: str | None = None,
    materialize_complete: bool = True,
) -> dict:
    row = {
        "skill": skill,
        "runtime_unit_key": unit,
        "model_key": model_key,
        "support_status": "supported",
        "result_status": "ready",
        "runtime_status": "ok",
        "runtime_required": True,
        "deterministic_generated": True,
        "generation_fingerprint": f"sha256:{unit.encode().hex()[:64].ljust(64, '0')}",
        "upstream_entity_fingerprints": [],
        "upstream_runtime_units": [],
        "unsupported_items": [],
        "freshness_status": "current",
        "model_completion": [
            {
                "model_key": materialize_model_key or model_key,
                "required_target_refs": [
                    f"target:{materialize_model_key or model_key}"
                ],
                "closed_target_refs": [f"target:{materialize_model_key or model_key}"],
                "active_ci_ids": sorted(active_ci_ids or []),
                "semantic_item_keys": [],
                "materialize_complete": materialize_complete,
            }
        ]
        if materialize
        else [],
        "target_mappings": [],
        "target_dispositions": [],
    }
    row["result_fingerprint"] = runtime.sha256_digest(row)
    return row


def structure_state(entities: list[dict]) -> tuple[dict, dict]:
    model_entities = [row for row in entities if row["entity_type"] == "model"]
    active_models = [
        {
            "model_key": row["entity_ref"],
            "model_type": row["content"]["model_type"],
            "technique_slug": row["content"].get("technique_slug"),
            "parent_tcn_id": row["content"]["parent_tcn_id"],
            "scope_refs": row["content"].get("scope_refs", []),
            "content_fingerprint": row["content_fingerprint"],
        }
        for row in model_entities
    ]
    result = {
        "envelope_version": "1",
        "skill": "test-condition-design",
        "runtime_contract_version": runtime.RUNTIME_CONTRACT_VERSION,
        "generator_contract_version": "condition-structure-v2",
        "generator": "condition_structure",
        "runtime_unit_key": "artifact:condition_structure:all",
        "model_key": None,
        "input_fingerprint": runtime.sha256_digest({"input": "condition_structure"}),
        "model_fingerprint": None,
        "generation_fingerprint": runtime.sha256_digest(
            {"generation": "condition_structure"}
        ),
        "runtime_implementation_fingerprint": "sha256:" + "1" * 64,
        "generator_implementation_fingerprint": "sha256:" + "2" * 64,
        "upstream_entity_fingerprints": [],
        "upstream_runtime_units": [],
        "support_status": "supported",
        "static_data_versions": {},
        "runtime_status": "ok",
        "result_status": "ready",
        "runtime_required": True,
        "deterministic_generated": True,
        "fallback_reason": None,
        "payload": {"active_model_metadata": active_models, "entities": entities},
        "issues": [],
    }
    row = runtime.runtime_unit_row(result)
    state = {
        "runtime_results": [
            {
                "identity": "test-condition-design::artifact:condition_structure:all",
                "result": result,
            }
        ],
        "carry_forward_entities": [],
        "previous_ci_id_state": [],
    }
    return state, row


def required_scope(
    skill: str, target: str | None = None, execution_range: str | None = None
) -> dict:
    return {
        "skill": skill,
        "target": target,
        "execution_range": execution_range,
        "requirement": "required",
    }


def run(request: dict) -> dict:
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        input=json.dumps(request).encode(),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=REPO_ROOT,
        check=False,
    )
    if result.stderr:
        raise AssertionError(result.stderr.decode())
    return json.loads(result.stdout)


class WorkflowRuntimeTests(unittest.TestCase):
    def _request(self) -> dict:
        tcn = runtime.make_machine_entity(
            "test-condition-design", "tcn", "TCN-001", {"tcn_id": "TCN-001"}
        )
        model = runtime.make_machine_entity(
            "test-condition-design",
            "model",
            "ep-001",
            {
                "model_key": "ep-001",
                "model_type": "ep",
                "technique_slug": "ep",
                "parent_tcn_id": "TCN-001",
            },
            model_key="ep-001",
        )
        ci_one = runtime.make_machine_entity(
            "test-condition-design",
            "ci",
            "TCN-001-CI01",
            {"ci_id": "TCN-001-CI01", "tcn_id": "TCN-001", "model_key": "ep-001"},
            model_key="ep-001",
        )
        ci_two = runtime.make_machine_entity(
            "test-condition-design",
            "ci",
            "TCN-001-CI02",
            {"ci_id": "TCN-001-CI02", "tcn_id": "TCN-001", "model_key": "ep-001"},
            model_key="ep-001",
        )
        authority = runtime.make_machine_entity(
            "spec-analysis", "authority", "SPEC-001", {"authority_id": "SPEC-001"}
        )
        condition_state, condition_row = structure_state([tcn, model])
        units = [
            condition_row,
            runtime_row("test-condition-design", "model:ep-001", "ep-001"),
            runtime_row(
                "test-condition-design",
                "artifact:materialize_coverage:TCN-001",
                materialize=True,
                active_ci_ids=["TCN-001-CI01", "TCN-001-CI02"],
                materialize_model_key="ep-001",
            ),
        ]
        normalized = {
            "tcn_id": "TCN-001",
            "test_conditions": [{"tcn_id": "TCN-001"}],
            "models": [{"model_key": "ep-001", "model_type": "ep"}],
            "ci_ids": ["TCN-001-CI01", "TCN-001-CI02"],
            "upstream_entities": [
                {
                    "skill": "spec-analysis",
                    "entity_type": "authority",
                    "entity_ref": "SPEC-001",
                }
            ],
        }
        return {
            "metadata": metadata(),
            "input": {
                "workflow_ref": "00000000-0000-4000-8000-000000000016",
                "requested_scopes": [required_scope("test-condition-design")],
                "workflow_scopes": [
                    {
                        "skill": "test-condition-design",
                        "target": None,
                        "execution_range": None,
                        "input_mode": "artifact",
                        "normalized_input": normalized,
                        "current_structure_state": condition_state,
                    }
                ],
                "runtime_units": units,
                "current_entities": [tcn, model, ci_one, ci_two, authority],
                "current_runtime_units": units,
                "unsupported_item_closures": [],
            },
        }

    def test_expected_runtime_and_entity_sets_are_derived_and_complete(self) -> None:
        result = run(self._request())
        self.assertEqual(result["runtime_status"], "ok")
        self.assertEqual(result["result_status"], "ready")
        self.assertTrue(result["payload"]["can_complete"])
        self.assertEqual(result["issues"], [])
        self.assertEqual(len(result["payload"]["expected_runtime_units"]), 3)
        self.assertEqual(len(result["payload"]["expected_entities"]), 5)
        self.assertEqual(
            result["payload"]["workflow_ref"],
            "00000000-0000-4000-8000-000000000016",
        )

    def test_workflow_ref_must_be_a_canonical_uuid(self) -> None:
        request = self._request()
        request["input"]["workflow_ref"] = "workflow-16"
        result = run(request)
        self.assertEqual(result["runtime_status"], "invalid_input")

    def test_missing_root_is_a_blocker_and_does_not_hide_other_expected_units(
        self,
    ) -> None:
        request = self._request()
        request["input"]["runtime_units"] = request["input"]["runtime_units"][1:]
        result = run(request)
        self.assertEqual(result["result_status"], "unresolved")
        self.assertFalse(result["payload"]["can_complete"])
        self.assertIn(
            ["test-condition-design", "artifact:condition_structure:all"],
            result["payload"]["missing_runtime_units"],
        )
        self.assertIn(
            "model:ep-001",
            [
                row["runtime_unit_key"]
                for row in result["payload"]["expected_runtime_units"]
            ],
        )

    def test_changed_entity_fingerprint_propagates_stale_to_runtime_completion(
        self,
    ) -> None:
        request = self._request()
        request["input"]["runtime_units"][1]["upstream_entity_fingerprints"] = [
            {
                "skill": "spec-analysis",
                "entity_type": "authority",
                "entity_ref": "SPEC-001",
                "content_fingerprint": "sha256:" + "0" * 64,
            }
        ]
        request["input"]["current_runtime_units"] = request["input"]["runtime_units"]
        result = run(request)
        self.assertEqual(result["result_status"], "unresolved")
        self.assertFalse(result["payload"]["can_complete"])
        self.assertTrue(
            any(
                issue["issue_type"] == "stale_entity_dependency"
                for issue in result["issues"]
            )
        )

    def test_current_runtime_result_is_authoritative_for_completion_and_closures(
        self,
    ) -> None:
        baseline = self._request()
        cases = (
            (
                "model_completion",
                [
                    {
                        "model_key": "ep-001",
                        "required_target_refs": ["target:ep-001"],
                        "closed_target_refs": [],
                        "active_ci_ids": ["TCN-001-CI01", "TCN-001-CI02"],
                        "semantic_item_keys": [],
                        "materialize_complete": False,
                    }
                ],
                "current_runtime_result_mismatch",
            ),
            (
                "target_mappings",
                [
                    {
                        "target_ref": "sha256:" + "1" * 64,
                        "target_content_fingerprint": "sha256:" + "2" * 64,
                        "generation_fingerprint": "sha256:" + "3" * 64,
                        "execution_fingerprint": "sha256:" + "4" * 64,
                        "model_key": "ep-001",
                        "target_key": "case",
                        "ci_id": "TCN-001-CI01",
                    }
                ],
                "current_runtime_result_mismatch",
            ),
            (
                "target_dispositions",
                [
                    {
                        "target_ref": "sha256:" + "1" * 64,
                        "target_content_fingerprint": "sha256:" + "2" * 64,
                        "generation_fingerprint": "sha256:" + "3" * 64,
                        "handling": "対象外",
                        "covered_by_target_version": None,
                    }
                ],
                "current_runtime_result_mismatch",
            ),
            (
                "unsupported_items",
                [
                    {
                        "item_key": "unsupported:generator:h" + "a" * 64,
                        "item_type": "schema",
                        "source_key": "field",
                        "reason_code": "unsupported_schema",
                        "affected_technique_slug": None,
                        "authority_refs": [],
                    }
                ],
                "current_runtime_result_mismatch",
            ),
        )
        for field, changed_value, expected_issue in cases:
            with self.subTest(field=field):
                request = json.loads(json.dumps(baseline))
                saved = next(
                    row
                    for row in request["input"]["runtime_units"]
                    if row["runtime_unit_key"]
                    == "artifact:materialize_coverage:TCN-001"
                )
                current = next(
                    row
                    for row in request["input"]["current_runtime_units"]
                    if row["runtime_unit_key"]
                    == "artifact:materialize_coverage:TCN-001"
                )
                saved[field] = changed_value
                # Keep the producer generation identical; only saved result evidence changed.
                result = run(request)
                self.assertEqual(result["result_status"], "unresolved")
                self.assertFalse(result["payload"]["can_complete"])
                self.assertTrue(
                    any(
                        issue["issue_type"] == expected_issue
                        for issue in result["issues"]
                    ),
                    result["issues"],
                )
                self.assertEqual(
                    saved["generation_fingerprint"], current["generation_fingerprint"]
                )
                if field == "unsupported_items":
                    self.assertFalse(
                        any(
                            issue["issue_type"]
                            == "whole_model_unsupported_closure_missing"
                            for issue in result["issues"]
                        )
                    )

    def test_current_materialize_completion_wins_over_saved_complete_projection(
        self,
    ) -> None:
        request = self._request()
        saved = next(
            row
            for row in request["input"]["runtime_units"]
            if row["runtime_unit_key"] == "artifact:materialize_coverage:TCN-001"
        )
        current = next(
            row
            for row in request["input"]["current_runtime_units"]
            if row["runtime_unit_key"] == "artifact:materialize_coverage:TCN-001"
        )
        current["model_completion"][0]["materialize_complete"] = False
        current["result_fingerprint"] = runtime.sha256_digest(
            {
                key: value
                for key, value in current.items()
                if key != "result_fingerprint"
            }
        )
        result = run(request)
        self.assertEqual(
            saved["generation_fingerprint"], current["generation_fingerprint"]
        )
        self.assertEqual(result["result_status"], "unresolved")
        self.assertTrue(
            any(
                issue["issue_type"] == "model_materialize_incomplete"
                for issue in result["issues"]
            ),
            result["issues"],
        )

    def _multi_scope_request(self, *, scope_b_complete: bool = True) -> dict:
        tcn_a = runtime.make_machine_entity(
            "test-condition-design", "tcn", "TCN-001", {"tcn_id": "TCN-001"}
        )
        tcn_b = runtime.make_machine_entity(
            "test-condition-design", "tcn", "TCN-002", {"tcn_id": "TCN-002"}
        )
        model_a = runtime.make_machine_entity(
            "test-condition-design",
            "model",
            "ep-001",
            {
                "model_key": "ep-001",
                "model_type": "ep",
                "technique_slug": "ep",
                "parent_tcn_id": "TCN-001",
            },
            model_key="ep-001",
        )
        model_b = runtime.make_machine_entity(
            "test-condition-design",
            "model",
            "ep-002",
            {
                "model_key": "ep-002",
                "model_type": "ep",
                "technique_slug": "ep",
                "parent_tcn_id": "TCN-002",
            },
            model_key="ep-002",
        )
        ci_a = runtime.make_machine_entity(
            "test-condition-design",
            "ci",
            "TCN-001-CI01",
            {"ci_id": "TCN-001-CI01", "tcn_id": "TCN-001", "model_key": "ep-001"},
            model_key="ep-001",
        )
        ci_b = runtime.make_machine_entity(
            "test-condition-design",
            "ci",
            "TCN-002-CI01",
            {"ci_id": "TCN-002-CI01", "tcn_id": "TCN-002", "model_key": "ep-002"},
            model_key="ep-002",
        )
        normalized_a = {
            "tcn_id": "TCN-001",
            "test_conditions": [{"tcn_id": "TCN-001"}],
            "models": [{"model_key": "ep-001", "model_type": "ep"}],
            "ci_ids": ["TCN-001-CI01"],
        }
        normalized_b = {
            "tcn_id": "TCN-002",
            "test_conditions": [{"tcn_id": "TCN-002"}],
            "models": [{"model_key": "ep-002", "model_type": "ep"}],
            "ci_ids": ["TCN-002-CI01"],
        }
        condition_state, condition_row = structure_state(
            [tcn_a, tcn_b, model_a, model_b]
        )
        units = [
            condition_row,
            runtime_row("test-condition-design", "model:ep-001", "ep-001"),
            runtime_row("test-condition-design", "model:ep-002", "ep-002"),
            runtime_row(
                "test-condition-design",
                "artifact:materialize_coverage:TCN-001",
                materialize=True,
                active_ci_ids=["TCN-001-CI01"],
                materialize_model_key="ep-001",
            ),
            runtime_row(
                "test-condition-design",
                "artifact:materialize_coverage:TCN-002",
                materialize=True,
                active_ci_ids=["TCN-002-CI01"],
                materialize_model_key="ep-002",
                materialize_complete=scope_b_complete,
            ),
        ]
        return {
            "metadata": metadata(),
            "input": {
                "workflow_ref": "00000000-0000-4000-8000-000000000016",
                "requested_scopes": [
                    required_scope("test-condition-design", "TCN-001"),
                    required_scope("test-condition-design", "TCN-002"),
                ],
                "workflow_scopes": [
                    {
                        "skill": "test-condition-design",
                        "target": "TCN-001",
                        "execution_range": None,
                        "input_mode": "artifact",
                        "normalized_input": normalized_a,
                        "current_structure_state": condition_state,
                    },
                    {
                        "skill": "test-condition-design",
                        "target": "TCN-002",
                        "execution_range": None,
                        "input_mode": "artifact",
                        "normalized_input": normalized_b,
                        "current_structure_state": condition_state,
                    },
                ],
                "runtime_units": units,
                "current_runtime_units": units,
                "current_entities": [tcn_a, tcn_b, model_a, model_b, ci_a, ci_b],
                "unsupported_item_closures": [],
            },
        }

    def test_two_complete_scopes_are_checked_independently(self) -> None:
        result = run(self._multi_scope_request())
        self.assertEqual(result["runtime_status"], "ok")
        self.assertTrue(result["payload"]["can_complete"], result)

    def test_incomplete_scope_cannot_be_hidden_by_other_scope_ci(self) -> None:
        result = run(self._multi_scope_request(scope_b_complete=False))
        self.assertEqual(result["runtime_status"], "ok")
        self.assertEqual(result["result_status"], "unresolved")
        self.assertFalse(result["payload"]["can_complete"])
        self.assertTrue(
            any(
                issue["issue_type"] == "model_materialize_incomplete"
                and issue.get("model_key") == "ep-002"
                for issue in result["issues"]
            )
        )

    def test_missing_runtime_and_entity_in_scope_b_are_not_filled_from_scope_a(
        self,
    ) -> None:
        request = self._multi_scope_request()
        request["input"]["runtime_units"] = [
            row
            for row in request["input"]["runtime_units"]
            if row["runtime_unit_key"] != "model:ep-002"
        ]
        request["input"]["current_entities"] = [
            entity
            for entity in request["input"]["current_entities"]
            if entity["entity_ref"] not in {"ep-002", "TCN-002-CI01"}
        ]
        result = run(request)
        self.assertEqual(result["result_status"], "unresolved")
        self.assertIn(
            ["test-condition-design", "model:ep-002"],
            result["payload"]["missing_runtime_units"],
        )
        self.assertIn(
            ["test-condition-design", "model", "ep-002"],
            result["payload"]["missing_entities"],
        )

    def _partial_scope_request(self) -> tuple[dict, dict[str, object]]:
        tcn_one = runtime.make_machine_entity(
            "test-condition-design", "tcn", "TCN-001", {"tcn_id": "TCN-001"}
        )
        tcn_two = runtime.make_machine_entity(
            "test-condition-design", "tcn", "TCN-002", {"tcn_id": "TCN-002"}
        )
        model_one = runtime.make_machine_entity(
            "test-condition-design",
            "model",
            "ep-001",
            {
                "model_key": "ep-001",
                "model_type": "ep",
                "technique_slug": "ep",
                "parent_tcn_id": "TCN-001",
            },
            model_key="ep-001",
        )
        model_two = runtime.make_machine_entity(
            "test-condition-design",
            "model",
            "ep-002",
            {
                "model_key": "ep-002",
                "model_type": "ep",
                "technique_slug": "ep",
                "parent_tcn_id": "TCN-002",
            },
            model_key="ep-002",
        )
        ci = runtime.make_machine_entity(
            "test-condition-design",
            "ci",
            "TCN-001-CI01",
            {"ci_id": "TCN-001-CI01", "tcn_id": "TCN-001", "model_key": "ep-001"},
            model_key="ep-001",
        )
        ci_two = runtime.make_machine_entity(
            "test-condition-design",
            "ci",
            "TCN-002-CI01",
            {"ci_id": "TCN-002-CI01", "tcn_id": "TCN-002", "model_key": "ep-002"},
            model_key="ep-002",
        )
        tdr_two = runtime.make_machine_entity(
            "test-condition-design",
            "test_data_requirement",
            "data:REQ-002",
            {
                "data_ref": "data:REQ-002",
                "requirement_key": "REQ-002",
                "source_model_key": "ep-002",
            },
            model_key="ep-002",
        )
        tr_two = runtime.make_machine_entity(
            "test-requirement-design", "tr", "TR-002", {"tr_id": "TR-002"}
        )
        tr_dependency = runtime.machine_entity_dependency(tr_two)
        tr_disposition = runtime.make_machine_entity(
            "test-condition-design",
            "disposition",
            "tr:TR-002",
            {
                "upstream_entity": tr_dependency,
                "handling": "対象外",
                "reason": "scope-out requirement",
                "authority_refs": [],
                "covered_by_entity": None,
            },
            upstream_entity_dependencies=[tr_dependency],
        )
        normalized = {
            "tcn_id": "TCN-001",
            "test_conditions": [{"tcn_id": "TCN-001"}],
            "models": [{"model_key": "ep-001", "model_type": "ep"}],
            "ci_ids": ["TCN-001-CI01"],
            "upstream_entities": [
                {
                    "skill": "test-requirement-design",
                    "entity_type": "tr",
                    "entity_ref": "TR-002",
                }
            ],
            "previous_tcn_ids": [
                {"tcn_id": "TCN-001", "status": "active", "scope_refs": []},
                {"tcn_id": "TCN-002", "status": "active", "scope_refs": []},
            ],
            "previous_model_keys": [
                {
                    "model_key": ref,
                    "model_type": "ep",
                    "technique_slug": "ep",
                    "parent_tcn_id": parent,
                    "selection_source": "user",
                    "selection_key": None,
                    "derived_from_model_key": None,
                    "status": "active",
                    "scope_refs": [],
                }
                for ref, parent in (("ep-001", "TCN-001"), ("ep-002", "TCN-002"))
            ],
            "previous_ci_ids": [
                {"ci_id": "TCN-001-CI01", "status": "active", "scope_refs": []}
            ],
            "update_scope_tcn_ids": ["TCN-001"],
            "update_scope_model_keys": ["ep-001"],
        }
        condition_state, condition_row = structure_state([tcn_one, model_one])
        condition_state["carry_forward_entities"] = [tcn_two, model_two]
        units = [
            condition_row,
            runtime_row("test-condition-design", "model:ep-001", "ep-001"),
            runtime_row(
                "test-condition-design",
                "artifact:materialize_coverage:TCN-001",
                materialize=True,
                active_ci_ids=["TCN-001-CI01"],
                materialize_model_key="ep-001",
            ),
        ]
        state = {
            "runtime_results": condition_state["runtime_results"],
            "carry_forward_entities": [
                tcn_two,
                model_two,
                ci_two,
                tdr_two,
                tr_disposition,
            ],
            "previous_ci_id_state": [
                {"ci_id": "TCN-001-CI01", "status": "active", "scope_refs": []},
                {"ci_id": "TCN-002-CI01", "status": "active", "scope_refs": []},
            ],
        }
        request = {
            "metadata": metadata(),
            "input": {
                "workflow_ref": "00000000-0000-4000-8000-000000000016",
                "requested_scopes": [
                    required_scope("test-condition-design", "TCN-001"),
                ],
                "workflow_scopes": [
                    {
                        "skill": "test-condition-design",
                        "target": "TCN-001",
                        "execution_range": None,
                        "input_mode": "artifact",
                        "normalized_input": normalized,
                        "current_structure_state": state,
                    }
                ],
                "runtime_units": units,
                "current_runtime_units": units,
                "current_entities": [
                    tcn_one,
                    tcn_two,
                    model_one,
                    model_two,
                    ci,
                    ci_two,
                    tdr_two,
                    tr_two,
                    tr_disposition,
                ],
                "unsupported_item_closures": [],
            },
        }
        return request, {
            "entities": [
                tcn_one,
                tcn_two,
                model_one,
                model_two,
                ci,
                ci_two,
                tdr_two,
                tr_two,
                tr_disposition,
            ],
            "state": state,
            "units": units,
        }

    def test_partial_rerun_uses_normalized_scope_and_current_structure_projection(
        self,
    ) -> None:
        request, parts = self._partial_scope_request()
        result = run(request)
        self.assertEqual(result["result_status"], "ready", result)
        self.assertTrue(result["payload"]["can_complete"])
        expected = {
            (row["entity_type"], row["entity_ref"])
            for row in result["payload"]["expected_entities"]
        }
        self.assertTrue(
            {
                ("tcn", "TCN-001"),
                ("tcn", "TCN-002"),
                ("model", "ep-001"),
                ("model", "ep-002"),
            }.issubset(expected)
        )
        self.assertIn(("test_data_requirement", "data:REQ-002"), expected)
        self.assertIn(("disposition", "tr:TR-002"), expected)

        missing = json.loads(json.dumps(request))
        missing["input"]["current_entities"] = [
            row
            for row in missing["input"]["current_entities"]
            if row["entity_ref"] != "ep-002"
        ]
        missing_result = run(missing)
        self.assertEqual(missing_result["result_status"], "unresolved")
        self.assertIn(
            ["test-condition-design", "model", "ep-002"],
            missing_result["payload"]["missing_entities"],
        )

        for ref in ("data:REQ-002", "tr:TR-002"):
            with self.subTest(missing=ref):
                missing_owner = json.loads(json.dumps(request))
                missing_owner["input"]["current_entities"] = [
                    row
                    for row in missing_owner["input"]["current_entities"]
                    if row["entity_ref"] != ref
                ]
                result_missing_owner = run(missing_owner)
                self.assertEqual(result_missing_owner["result_status"], "unresolved")
                self.assertIn(
                    [
                        "test-condition-design",
                        "test_data_requirement"
                        if ref == "data:REQ-002"
                        else "disposition",
                        ref,
                    ],
                    result_missing_owner["payload"]["missing_entities"],
                )

        no_projection = json.loads(json.dumps(request))
        del no_projection["input"]["workflow_scopes"][0]["current_structure_state"][
            "carry_forward_entities"
        ]
        rejected_projection = run(no_projection)
        self.assertEqual(rejected_projection["runtime_status"], "invalid_input")

    def test_current_structure_state_rejects_extra_or_in_scope_carry_rows(self) -> None:
        request, _parts = self._partial_scope_request()
        unknown_tcn = runtime.make_machine_entity(
            "test-condition-design", "tcn", "TCN-999", {"tcn_id": "TCN-999"}
        )
        in_scope_tcn = runtime.make_machine_entity(
            "test-condition-design", "tcn", "TCN-001", {"tcn_id": "TCN-001"}
        )
        in_scope_tdr = runtime.make_machine_entity(
            "test-condition-design",
            "test_data_requirement",
            "data:REQ-001",
            {
                "data_ref": "data:REQ-001",
                "requirement_key": "REQ-001",
                "source_model_key": "ep-001",
            },
            model_key="ep-001",
        )
        extra_ci = runtime.make_machine_entity(
            "test-condition-design",
            "ci",
            "TCN-002-CI99",
            {"ci_id": "TCN-002-CI99", "tcn_id": "TCN-002", "model_key": "ep-002"},
            model_key="ep-002",
        )
        unknown_owner = {
            "skill": "test-requirement-design",
            "entity_type": "tr",
            "entity_ref": "TR-999",
            "content_fingerprint": "sha256:" + ("0" * 64),
        }
        ownerless_disposition = runtime.make_machine_entity(
            "test-condition-design",
            "disposition",
            "tr:TR-999",
            {
                "upstream_entity": unknown_owner,
                "handling": "対象外",
                "reason": "scope-out",
                "authority_refs": [],
                "covered_by_entity": None,
            },
            upstream_entity_dependencies=[unknown_owner],
        )
        for label, entity in (
            ("unknown TCN", unknown_tcn),
            ("in-scope TCN", in_scope_tcn),
            ("TDR owned by in-scope model", in_scope_tdr),
            ("CI absent from previous CI state", extra_ci),
            ("disposition with unknown owner", ownerless_disposition),
        ):
            with self.subTest(label=label):
                tampered = json.loads(json.dumps(request))
                tampered["input"]["workflow_scopes"][0]["current_structure_state"][
                    "carry_forward_entities"
                ].append(entity)
                result = run(tampered)
                self.assertEqual(result["runtime_status"], "invalid_input", result)

        for label, edit in (
            (
                "unknown projection field",
                lambda state: state.update({"expected_entities": []}),
            ),
            (
                "duplicate carry identity",
                lambda state: state["carry_forward_entities"].append(
                    state["carry_forward_entities"][0]
                ),
            ),
            (
                "missing required scope-out TCN",
                lambda state: state["carry_forward_entities"].remove(
                    next(
                        row
                        for row in state["carry_forward_entities"]
                        if row["entity_type"] == "tcn"
                    )
                ),
            ),
            (
                "tampered content fingerprint",
                lambda state: state["carry_forward_entities"][0]["content"].update(
                    {"tcn_id": "TCN-099"}
                ),
            ),
            (
                "duplicate runtime result identity",
                lambda state: state.update(
                    {
                        "runtime_results": [
                            {
                                "identity": "test-condition-design::artifact:condition_structure:all",
                                "result": {},
                            },
                            {
                                "identity": "test-condition-design::artifact:condition_structure:all",
                                "result": {},
                            },
                        ]
                    }
                ),
            ),
        ):
            with self.subTest(label=label):
                tampered = json.loads(json.dumps(request))
                edit(tampered["input"]["workflow_scopes"][0]["current_structure_state"])
                result = run(tampered)
                self.assertEqual(result["runtime_status"], "invalid_input", result)

    def test_partial_rerun_rejects_deleted_scope_entity_left_in_current_entities(
        self,
    ) -> None:
        request, parts = self._partial_scope_request()
        scope = request["input"]["workflow_scopes"][0]
        scope["normalized_input"]["test_conditions"] = []
        scope["normalized_input"]["models"] = []
        scope["normalized_input"]["ci_ids"] = []
        scope["normalized_input"]["update_scope_tcn_ids"] = ["TCN-001"]
        deleted_state, deleted_root = structure_state([])
        scope["current_structure_state"] = {
            "runtime_results": deleted_state["runtime_results"],
            "carry_forward_entities": parts["state"]["carry_forward_entities"],
            "previous_ci_id_state": parts["state"]["previous_ci_id_state"],
        }
        request["input"]["runtime_units"] = [deleted_root]
        request["input"]["current_runtime_units"] = request["input"]["runtime_units"]
        result = run(request)
        self.assertEqual(result["result_status"], "unresolved")
        self.assertIn(
            ["test-condition-design", "tcn", "TCN-001"],
            result["payload"]["extra_entities"],
        )

    def test_stale_scope_out_entity_blocks_partial_workflow_completion(self) -> None:
        request, parts = self._partial_scope_request()
        old_context = {
            "runtime_contract_version": runtime.RUNTIME_CONTRACT_VERSION,
            "generator_contract_version": "condition-structure-v2",
            "runtime_implementation_fingerprint": runtime.implementation_fingerprint(
                RUNTIME_PATH
            ),
            "generator_implementation_fingerprint": "sha256:" + "1" * 64,
            "static_data_versions": {},
        }
        stale_tcn = runtime.make_machine_entity(
            "test-condition-design",
            "tcn",
            "TCN-002",
            {"tcn_id": "TCN-002"},
            runtime_dependencies=[
                runtime.machine_entity_runtime_dependency(
                    "test-condition-design", "artifact:condition_structure:all"
                )
            ],
        )
        stale_tcn = runtime.bind_current_entity_runtime_dependencies(
            {"entities": [stale_tcn]},
            "sha256:" + "2" * 64,
            runtime_context=old_context,
        )["entities"][0]
        request["input"]["current_entities"] = [
            stale_tcn
            if row["entity_type"] == "tcn" and row["entity_ref"] == "TCN-002"
            else row
            for row in request["input"]["current_entities"]
        ]
        condition_result = request["input"]["workflow_scopes"][0][
            "current_structure_state"
        ]["runtime_results"][0]["result"]
        condition_result.update(
            {
                "runtime_contract_version": runtime.RUNTIME_CONTRACT_VERSION,
                "generator_contract_version": "condition-structure-v2",
                "runtime_implementation_fingerprint": runtime.implementation_fingerprint(
                    RUNTIME_PATH
                ),
                "generator_implementation_fingerprint": "sha256:" + "3" * 64,
                "static_data_versions": {},
            }
        )
        root_runtime = runtime.runtime_unit_row(condition_result)
        request["input"]["current_runtime_units"][0] = root_runtime
        request["input"]["runtime_units"][0] = root_runtime
        result = run(request)
        self.assertEqual(result["result_status"], "unresolved")
        self.assertFalse(result["payload"]["can_complete"])
        self.assertTrue(
            any(
                issue["issue_type"] == "stale_entity"
                and issue.get("entity_ref") == "TCN-002"
                for issue in result["issues"]
            )
        )


class RequestedScopeContractTests(unittest.TestCase):
    """工程開始時の要求集合（requested_scopes）による完了判定の契約。"""

    def _base(self) -> dict:
        return WorkflowRuntimeTests()._request()

    def _set_requested(self, request: dict, rows: list[dict]) -> None:
        request["input"]["requested_scopes"] = rows

    def test_all_requested_scopes_verified_completes(self) -> None:
        request = self._base()
        result = run(request)
        self.assertEqual(result["runtime_status"], "ok", result)
        self.assertTrue(result["payload"]["can_complete"], result)
        self.assertTrue(result["payload"]["scope_set_declared"])
        self.assertEqual(result["payload"]["missing_requested_scopes"], [])
        self.assertEqual(result["payload"]["unrequested_scopes"], [])

    def test_missing_required_scope_blocks_completion(self) -> None:
        request = self._base()
        self._set_requested(
            request,
            [
                required_scope("test-condition-design"),
                required_scope("test-management"),
            ],
        )
        result = run(request)
        self.assertEqual(result["runtime_status"], "ok", result)
        self.assertFalse(result["payload"]["can_complete"])
        self.assertEqual(
            result["payload"]["missing_requested_scopes"],
            [{"skill": "test-management", "target": None, "execution_range": None}],
        )
        self.assertIn(
            "required_scope_missing",
            {issue["issue_type"] for issue in result["issues"]},
        )

    def test_required_scope_present_but_unregistered_blocks_completion(self) -> None:
        request = self._base()
        request["input"]["workflow_scopes"].append(
            {
                "skill": "test-management",
                "target": None,
                "execution_range": None,
                "input_mode": "artifact",
                "normalized_input": {},
                "current_structure_state": None,
            }
        )
        self._set_requested(
            request,
            [
                required_scope("test-condition-design"),
                required_scope("test-management"),
            ],
        )
        result = run(request)
        self.assertFalse(result["payload"]["can_complete"])
        self.assertEqual(
            [row["skill"] for row in result["payload"]["unverified_scopes"]],
            ["test-management"],
        )
        self.assertEqual(result["payload"]["missing_requested_scopes"], [])

    def test_approved_exclusion_is_not_confirmed_and_keeps_scope_required(self) -> None:
        # 旧期待値: 形式上の承認参照があれば対象外として除外し、完了する。
        # 新期待値: 承認の照合手段が無いため対象外は確定しない（excluded_scopes は空）。
        #   scope は必須のまま残り、完了しない。理由は利用者要求 4.4（照合手段がない場合は
        #   対象外を確定しない）。
        request = self._base()
        self._set_requested(
            request,
            [
                required_scope("test-condition-design"),
                {
                    "skill": "test-management",
                    "target": None,
                    "execution_range": None,
                    "requirement": "excluded_by_approval",
                    "approval_ref": "APPROVAL-001",
                },
            ],
        )
        result = run(request)
        payload = result["payload"]
        self.assertEqual(result["runtime_status"], "ok", result)
        self.assertFalse(payload["can_complete"], result)
        self.assertEqual(payload["excluded_scopes"], [], result)
        self.assertEqual(
            payload["unverified_exclusions"],
            [
                {
                    "skill": "test-management",
                    "target": None,
                    "execution_range": None,
                    "reason": "approval_unverifiable",
                }
            ],
            result,
        )
        self.assertEqual(
            payload["missing_requested_scopes"],
            [{"skill": "test-management", "target": None, "execution_range": None}],
            result,
        )
        self.assertIn(
            "approval_unverifiable", {i["issue_type"] for i in result["issues"]}
        )

    def test_approval_exclusion_without_reference_blocks_completion(self) -> None:
        for label, approval in (
            ("missing", None),
            ("blank", "  "),
        ):
            with self.subTest(label=label):
                request = self._base()
                row = {
                    "skill": "test-management",
                    "target": None,
                    "execution_range": None,
                    "requirement": "excluded_by_approval",
                }
                if approval is not None:
                    row["approval_ref"] = approval
                self._set_requested(
                    request, [required_scope("test-condition-design"), row]
                )
                result = run(request)
                self.assertFalse(result["payload"]["can_complete"], result)
                self.assertIn(
                    "approval_ref_missing",
                    {issue["issue_type"] for issue in result["issues"]},
                )

    def test_unrequested_skill_omission_is_not_a_blocker(self) -> None:
        request = self._base()
        self._set_requested(request, [required_scope("test-condition-design")])
        result = run(request)
        self.assertTrue(result["payload"]["can_complete"], result)
        self.assertEqual(result["payload"]["unrequested_scopes"], [])

    def test_self_declaration_cannot_hide_required_scopes(self) -> None:
        request = self._base()
        del request["input"]["requested_scopes"]
        result = run(request)
        self.assertEqual(result["runtime_status"], "ok", result)
        self.assertFalse(result["payload"]["can_complete"])
        self.assertFalse(result["payload"]["scope_set_declared"])
        self.assertIn(
            "required_scopes_undeclared",
            {issue["issue_type"] for issue in result["issues"]},
        )

        empty = self._base()
        self._set_requested(empty, [])
        result_empty = run(empty)
        self.assertFalse(result_empty["payload"]["can_complete"])
        self.assertIn(
            "required_scopes_undeclared",
            {issue["issue_type"] for issue in result_empty["issues"]},
        )

        unknown = self._base()
        unknown["input"]["all_scopes_confirmed"] = True
        self.assertEqual(run(unknown)["runtime_status"], "invalid_input")

    def test_invalid_requested_scope_rows_are_rejected(self) -> None:
        invalid_rows = (
            [
                required_scope("test-condition-design"),
                required_scope("test-condition-design"),
            ],
            [{**required_scope("test-condition-design"), "requirement": "optional"}],
            [
                {
                    **required_scope("test-condition-design"),
                    "approval_ref": "APPROVAL-001",
                }
            ],
            [{**required_scope("qa-workflow")}],
            [
                {
                    "skill": "test-condition-design",
                    "target": None,
                    "execution_range": None,
                }
            ],
            [{**required_scope("test-condition-design"), "unknown": 1}],
        )
        for rows in invalid_rows:
            with self.subTest(rows=rows):
                request = self._base()
                self._set_requested(request, rows)
                self.assertEqual(run(request)["runtime_status"], "invalid_input")

    PLACEHOLDER_APPROVAL_REFS = (
        "未設定",
        "未取得",
        "未確認",
        "未承認",
        "失効",
        "unknown",
        "N/A",
        "-",
        "—",
        "dummy",
        "approved",
        "承認済み",
        "TODO",
        "pending",
        "null",
        "none",
        "  Unknown  ",
        "ｎ／ａ",
        "－",
        "placeholder",
    )

    def _exclusion_request(
        self, row_extra: dict, *, scope_present: bool = True
    ) -> dict:
        """test-management（未登録）を承認済み対象外として宣言する入力。"""
        request = self._base()
        if scope_present:
            request["input"]["workflow_scopes"].append(
                {
                    "skill": "test-management",
                    "target": None,
                    "execution_range": None,
                    "input_mode": "artifact",
                    "normalized_input": {},
                    "current_structure_state": None,
                }
            )
        row = {
            "skill": "test-management",
            "target": None,
            "execution_range": None,
            "requirement": "excluded_by_approval",
            **row_extra,
        }
        self._set_requested(request, [required_scope("test-condition-design"), row])
        return request

    def test_placeholder_approval_ref_never_excludes_scope(self) -> None:
        # 期待結果: 承認参照がplaceholder（未設定・unknown・N/A・dummy・状態語など）なら、
        #   対象外は確定せず、scopeは workflow_scopes から除かれず未検証のまま残る。
        #   他scopeが検証済みでも完了しない。
        for approval in self.PLACEHOLDER_APPROVAL_REFS:
            with self.subTest(approval=approval):
                result = run(self._exclusion_request({"approval_ref": approval}))
                payload = result["payload"]
                self.assertEqual(result["runtime_status"], "ok", result)
                self.assertFalse(payload["can_complete"], result)
                self.assertEqual(payload["excluded_scopes"], [], result)
                self.assertEqual(
                    [row["skill"] for row in payload["unverified_exclusions"]],
                    ["test-management"],
                    result,
                )
                self.assertEqual(
                    payload["unverified_exclusions"][0]["reason"],
                    "approval_ref_missing",
                    result,
                )
                self.assertEqual(
                    [row["skill"] for row in payload["unverified_scopes"]],
                    ["test-management"],
                    result,
                )
                self.assertIn(
                    "approval_ref_missing",
                    {issue["issue_type"] for issue in result["issues"]},
                )

    def test_concrete_approval_ref_is_unverifiable_and_keeps_scope_unverified(
        self,
    ) -> None:
        # 旧期待値: 形式上の参照がある承認済み対象外は除外され、完了する。
        # 新期待値: 対象外は確定せず、scope は未検証のまま残る。完了しない（理由は上と同じ）。
        result = run(self._exclusion_request({"approval_ref": "APPROVAL-001"}))
        payload = result["payload"]
        self.assertFalse(payload["can_complete"], result)
        self.assertEqual(payload["excluded_scopes"], [], result)
        self.assertEqual(
            [row["reason"] for row in payload["unverified_exclusions"]],
            ["approval_unverifiable"],
            result,
        )
        self.assertEqual(
            [row["skill"] for row in payload["unverified_scopes"]],
            ["test-management"],
            result,
        )

    def test_no_exclusion_is_confirmed_for_any_reference_form(self) -> None:
        # 形式が正しい参照・別scope向け・別revision向けを示す文字列でも対象外は確定しない。
        for approval in (
            "APR-999",
            "APPROVAL-001",
            "APR-OTHER-SCOPE",
            "APPROVAL-001@rev-0",
            "承認記録-2026-0001",
        ):
            with self.subTest(approval=approval):
                result = run(self._exclusion_request({"approval_ref": approval}))
                payload = result["payload"]
                self.assertFalse(payload["can_complete"], result)
                self.assertEqual(payload["excluded_scopes"], [], result)
                self.assertEqual(
                    payload["unverified_exclusions"][0]["reason"],
                    "approval_unverifiable",
                    result,
                )

    def test_placeholder_exclusion_leaves_required_scope_missing(self) -> None:
        # placeholderの対象外は、scopeが無い場合も必須欠落として完了を止める。
        result = run(
            self._exclusion_request({"approval_ref": "未設定"}, scope_present=False)
        )
        payload = result["payload"]
        self.assertFalse(payload["can_complete"], result)
        self.assertEqual(
            payload["missing_requested_scopes"],
            [{"skill": "test-management", "target": None, "execution_range": None}],
        )
        self.assertEqual(payload["excluded_scopes"], [])
        self.assertIn(
            "required_scope_missing",
            {issue["issue_type"] for issue in result["issues"]},
        )

    def test_non_requested_scope_is_recorded_but_not_required(self) -> None:
        # 未要求scopeは記録されるが必須扱いしない。ただし既存の未検証ルールは従う。
        request = self._base()
        request["input"]["workflow_scopes"].append(
            {
                "skill": "defect-management",
                "target": "project-1",
                "execution_range": "plan",
                "input_mode": "artifact",
                "normalized_input": {},
                "current_structure_state": None,
            }
        )
        result = run(request)
        self.assertEqual(result["runtime_status"], "ok", result)
        self.assertEqual(
            [row["skill"] for row in result["payload"]["unrequested_scopes"]],
            ["defect-management"],
        )
        self.assertEqual(result["payload"]["missing_requested_scopes"], [])
        self.assertFalse(result["payload"]["can_complete"])
        self.assertEqual(
            [row["skill"] for row in result["payload"]["unverified_scopes"]],
            ["defect-management"],
        )


if __name__ == "__main__":
    unittest.main()
