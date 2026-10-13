from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
SKILL = "test-condition-design"
SCRIPTS = ROOT / "skills" / SKILL / "scripts"
HELPER = SCRIPTS / "runtime_v1_cutover.py"
TDR_UNIT = "artifact:test_data_requirements:all"

RUNTIME_V1 = "sha256:c8fdccf927085d3a4cfaf76f18cb8b515349ff28988a4a4a8df4c2bf566fb691"
V1_GENERATORS = {
    "condition_structure": "sha256:e30e7323660c8ff21c65614cd8c820c13249bd112aa99349b6b0ecce6549a847",
    "equivalence_partitions": "sha256:bbc41de9a5937edb386f1c105b75915587f935d6d26f06652466c9b19331be21",
    "bva": "sha256:c84bcf26cc6141bded0f2aff1b0391fcf608a19e20ea7f254454d1f368ae7bfd",
    "materialize_coverage": "sha256:e0553cbedd666ef3f218c43490d9c15131e0e020b3bfabdb9d5a5e4ce21fd02d",
}


def _canonicalize(value: Any) -> Any:
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    from runtime_contract import canonicalize

    return canonicalize(value)


def _digest(value: Any) -> str:
    data = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(data.encode("utf-8")).hexdigest()


def _implementation(path: Path) -> str:
    data = path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _metadata(
    unit: str,
    generator_contract: str,
    *,
    model_key: str | None = None,
    model_type: str | None = None,
    technique_slug: str | None = None,
    selection_source: str | None = None,
    selection_key: str | None = None,
    scope_key: str | None = None,
    runtime_version: str = "runtime-v1",
) -> dict[str, Any]:
    return {
        "envelope_version": "1",
        "skill": SKILL,
        "runtime_contract_version": runtime_version,
        "generator_contract_version": generator_contract,
        "runtime_unit_key": unit,
        "model_key": model_key,
        "model_type": model_type,
        "technique_slug": technique_slug,
        "selection_source": selection_source,
        "selection_key": selection_key,
        "scope_key": scope_key,
        "input_mode": "direct",
        "upstream_entities": [],
        "upstream_runtime_units": [],
        "static_data_versions": {},
        "authority_refs": [],
        "reference_refs": [],
    }


def _pair(
    unit: str,
    generator: str,
    generator_contract: str,
    generator_fingerprint: str,
    input_value: dict[str, Any],
    payload: dict[str, Any],
    *,
    model_key: str | None = None,
    model_type: str | None = None,
    technique_slug: str | None = None,
    selection_source: str | None = None,
    selection_key: str | None = None,
    scope_key: str | None = None,
    runtime_version: str = "runtime-v1",
) -> tuple[dict[str, Any], dict[str, Any]]:
    normalized_input = _canonicalize(input_value)
    metadata = _metadata(
        unit,
        generator_contract,
        model_key=model_key,
        model_type=model_type,
        technique_slug=technique_slug,
        selection_source=selection_source,
        selection_key=selection_key,
        scope_key=scope_key,
        runtime_version=runtime_version,
    )
    fp_value = {
        "skill": SKILL,
        "runtime_unit_key": unit,
        "input_mode": "direct",
        "input": normalized_input,
        "authority_refs": [],
        "reference_refs": [],
    }
    if selection_source is not None:
        fp_value["selection_source"] = selection_source
    input_fp = _digest(fp_value)
    model_fp = None
    if model_key is not None:
        model_fp = _digest(
            {
                "model_key": model_key,
                "model_type": model_type,
                "technique_slug": technique_slug,
                "selection_source": selection_source,
                "selection_key": selection_key,
                "input_fingerprint": input_fp,
            }
        )
    generation_fp = _digest(
        {
            "generator": generator,
            "envelope_version": "1",
            "input_fingerprint": input_fp,
            "model_fingerprint": model_fp,
            "runtime_contract_version": runtime_version,
            "generator_contract_version": generator_contract,
            "runtime_implementation_fingerprint": RUNTIME_V1
            if runtime_version == "runtime-v1"
            else _implementation(SCRIPTS / "runtime_contract.py"),
            "generator_implementation_fingerprint": generator_fingerprint,
            "upstream_entity_fingerprints": [],
            "static_data_versions": {},
        }
    )
    result = {
        "envelope_version": "1",
        "skill": SKILL,
        "runtime_contract_version": runtime_version,
        "generator_contract_version": generator_contract,
        "generator": generator,
        "runtime_unit_key": unit,
        "model_key": model_key,
        "input_fingerprint": input_fp,
        "model_fingerprint": model_fp,
        "generation_fingerprint": generation_fp,
        "runtime_implementation_fingerprint": RUNTIME_V1
        if runtime_version == "runtime-v1"
        else _implementation(SCRIPTS / "runtime_contract.py"),
        "generator_implementation_fingerprint": generator_fingerprint,
        "upstream_entity_fingerprints": [],
        "upstream_runtime_units": [],
        "support_status": "supported",
        "static_data_versions": {},
        "runtime_status": "ok",
        "result_status": "ready",
        "runtime_required": True,
        "deterministic_generated": True,
        "fallback_reason": None,
        "payload": payload,
        "issues": [],
    }
    return {"metadata": metadata, "input": normalized_input}, result


def _block(kind: str, identity: str, value: dict[str, Any]) -> str:
    body = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    heading = "Machine Entities" if kind == "Entities" else f"Machine Runtime {kind}"
    return f"### {heading}: {identity}\n\n```json\n{body}\n```\n"


def _artifact(
    *,
    with_model: bool = False,
    with_derived_model: bool = False,
    with_tdr: bool = False,
    tamper_root: bool = False,
) -> str:
    source_input = {
        "test_requirements": [],
        "technique_selections": [],
        "test_conditions": [],
        "requirement_dispositions": [],
        "models": [],
        "previous_tcn_ids": [],
        "previous_model_keys": [],
        "update_scope_tcn_ids": [],
        "update_scope_model_keys": [],
    }
    active_metadata: list[dict[str, Any]] = []
    model_state: list[dict[str, Any]] = []
    tcn_state: list[dict[str, Any]] = []
    tcn_map: list[dict[str, Any]] = []
    model_map: list[dict[str, Any]] = []
    model_pair = None
    derived_model_pair = None
    materialize_pair = None
    tdr_pair = None
    if with_model or with_derived_model:
        content_fp = "sha256:" + "a" * 64
        source_input["test_conditions"] = [
            {
                "draft_key": "condition-login",
                "identity_action": "new",
                "reuse_id": None,
                "tr_refs": [],
                "condition": "ログイン状態",
                "category": None,
                "technique_slugs": ["ep"],
                "coverage_criterion": "each-choice",
                "authority_refs": [],
                "risk_refs": [],
                "priority": "中",
                "priority_override_reason": None,
            }
        ]
        source_input["models"] = [
            {
                "draft_key": "model-login-ep",
                "model_type": "ep",
                "technique_slug": "ep",
                "selection_source": "condition_design",
                "selection_key": None,
                "derived_from_model_draft_key": None,
                "identity_action": "new",
                "reuse_model_key": None,
                "parent_tcn_draft_key": "condition-login",
            }
        ]
        derived_input = {"source": "parent-derived"}
        if with_derived_model:
            source_input["models"].append(
                {
                    "draft_key": "model-login-bva",
                    "model_type": "bva",
                    "technique_slug": "bva",
                    "selection_source": "condition_design",
                    "selection_key": None,
                    "derived_from_model_draft_key": "model-login-ep",
                    "identity_action": "new",
                    "reuse_model_key": None,
                    "parent_tcn_draft_key": "condition-login",
                }
            )
        tcn_state = [{"tcn_id": "TCN-001", "status": "active"}]
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
            }
        ]
        tcn_map = [
            {
                "draft_key": "condition-login",
                "tcn_id": "TCN-001",
                "identity_action": "new",
            }
        ]
        model_map = [
            {
                "draft_key": "model-login-ep",
                "model_key": "ep-001",
                "model_type": "ep",
                "technique_slug": "ep",
                "parent_tcn_id": "TCN-001",
                "derived_from_model_key": None,
                "identity_action": "new",
            }
        ]
        active_metadata = [
            {
                "model_key": "ep-001",
                "model_type": "ep",
                "technique_slug": "ep",
                "parent_tcn_id": "TCN-001",
                "content_fingerprint": content_fp,
            }
        ]
        if with_derived_model:
            model_state.append(
                {
                    "model_key": "bva-001",
                    "model_type": "bva",
                    "technique_slug": "bva",
                    "parent_tcn_id": "TCN-001",
                    "selection_source": "condition_design",
                    "selection_key": None,
                    "derived_from_model_key": "ep-001",
                    "status": "active",
                }
            )
            model_map.append(
                {
                    "draft_key": "model-login-bva",
                    "model_key": "bva-001",
                    "model_type": "bva",
                    "technique_slug": "bva",
                    "parent_tcn_id": "TCN-001",
                    "derived_from_model_key": "ep-001",
                    "identity_action": "new",
                }
            )
            active_metadata.append(
                {
                    "model_key": "bva-001",
                    "model_type": "bva",
                    "technique_slug": "bva",
                    "parent_tcn_id": "TCN-001",
                    "content_fingerprint": "sha256:" + "b" * 64,
                }
            )
        model_result_payload = {
            "targets": [],
            "unsupported_items": [],
            "coverage_summary": {"complete": True},
            "derived_child_inputs": (
                [
                    {
                        "child_model_key": "bva-001",
                        "parent_model_key": "ep-001",
                        "model_type": "bva",
                        "input": derived_input,
                    }
                ]
                if with_derived_model
                else []
            ),
        }
        model_pair = _pair(
            "model:ep-001",
            "equivalence_partitions",
            "equivalence-partitions-v1",
            V1_GENERATORS["equivalence_partitions"],
            {},
            model_result_payload,
            model_key="ep-001",
            model_type="ep",
            technique_slug="ep",
            selection_source="condition_design",
        )
        old_model_row = {
            "skill": SKILL,
            "model_key": "ep-001",
            "model_type": "ep",
            "technique_slug": "ep",
            "runtime_unit_key": "model:ep-001",
            "input_fingerprint": model_pair[1]["input_fingerprint"],
            "model_fingerprint": model_pair[1]["model_fingerprint"],
            "generation_fingerprint": model_pair[1]["generation_fingerprint"],
            "generator_contract_version": "equivalence-partitions-v1",
            "support_status": "supported",
            "runtime_status": "ok",
            "result_status": "ready",
            "deterministic_generated": True,
            "freshness_status": "current",
            "targets": [],
            "unsupported_items": [],
            "coverage_summary": {"complete": True},
        }
        old_model_rows = [old_model_row]
        if with_derived_model:
            derived_model_pair = _pair(
                "model:bva-001",
                "bva",
                "bva-v1",
                V1_GENERATORS["bva"],
                derived_input,
                {
                    "targets": [],
                    "unsupported_items": [],
                    "coverage_summary": {"complete": True},
                    "derived_child_inputs": [],
                },
                model_key="bva-001",
                model_type="bva",
                technique_slug="bva",
                selection_source="condition_design",
            )
            derived_result = derived_model_pair[1]
            old_model_rows.append(
                {
                    "skill": SKILL,
                    "model_key": "bva-001",
                    "model_type": "bva",
                    "technique_slug": "bva",
                    "runtime_unit_key": "model:bva-001",
                    "input_fingerprint": derived_result["input_fingerprint"],
                    "model_fingerprint": derived_result["model_fingerprint"],
                    "generation_fingerprint": derived_result["generation_fingerprint"],
                    "generator_contract_version": "bva-v1",
                    "support_status": "supported",
                    "runtime_status": "ok",
                    "result_status": "ready",
                    "deterministic_generated": True,
                    "freshness_status": "current",
                    "targets": [],
                    "unsupported_items": [],
                    "coverage_summary": {"complete": True},
                }
            )
        old_model_rows.sort(key=lambda row: row["model_key"])
        materialize_input = {
            "tcn_id": "TCN-001",
            "active_model_metadata": active_metadata,
            "models": old_model_rows,
            "semantic_coverage_items": [],
            "target_annotations": [],
            "target_dispositions": [],
            "test_data_requirements": [],
            "previous_target_id_map": [],
            "previous_semantic_ci_map": [],
            "previous_ci_ids": [],
            "previous_expected_result_roots": [],
            "merge_groups": [],
        }
        materialize_pair = _pair(
            "artifact:materialize_coverage:TCN-001",
            "materialize_coverage",
            "materialize-coverage-v1",
            V1_GENERATORS["materialize_coverage"],
            materialize_input,
            {
                "target_mapping_state": [],
                "semantic_ci_mapping_state": [],
                "ci_id_state": [],
                "expected_result_root_state": [],
            },
            scope_key="TCN-001",
        )
    root_payload = {
        "tcn_id_map": tcn_map,
        "model_key_map": model_map,
        "tcn_id_state": tcn_state,
        "model_key_state": model_state,
        "active_model_metadata": active_metadata,
        "inactive_tcn_history": [],
        "inactive_model_history": [],
        "inactive_materialize_history": [],
    }
    root_pair = _pair(
        "artifact:condition_structure:all",
        "condition_structure",
        "condition-structure-v1",
        V1_GENERATORS["condition_structure"],
        source_input,
        root_payload,
        scope_key="all",
    )
    if tamper_root:
        root_pair[1]["input_fingerprint"] = "sha256:" + "0" * 64
    if with_tdr:
        tdr_pair = _pair(
            TDR_UNIT,
            "test_data_requirements",
            "test-data-requirements-v1",
            "sha256:6c8779ee77b9126971ef5eb5a1f77b66dbf8a94f0bc6618179805330f7c15faa",
            {"requirements": [], "current_source_targets": []},
            {"normalized_requirements": []},
            scope_key="all",
        )
    blocks = [
        _block(
            "Input",
            f"{SKILL}::artifact:condition_structure:all",
            root_pair[0],
        ),
        _block(
            "Result",
            f"{SKILL}::artifact:condition_structure:all",
            root_pair[1],
        ),
    ]
    if tdr_pair is not None:
        blocks.extend(
            [
                _block("Input", f"{SKILL}::{TDR_UNIT}", tdr_pair[0]),
                _block("Result", f"{SKILL}::{TDR_UNIT}", tdr_pair[1]),
            ]
        )
    if model_pair is not None:
        blocks.extend(
            [
                _block("Input", f"{SKILL}::model:ep-001", model_pair[0]),
                _block("Result", f"{SKILL}::model:ep-001", model_pair[1]),
            ]
        )
    if derived_model_pair is not None:
        blocks.extend(
            [
                _block("Input", f"{SKILL}::model:bva-001", derived_model_pair[0]),
                _block("Result", f"{SKILL}::model:bva-001", derived_model_pair[1]),
            ]
        )
    if materialize_pair is not None:
        blocks.extend(
            [
                _block(
                    "Input",
                    f"{SKILL}::artifact:materialize_coverage:TCN-001",
                    materialize_pair[0],
                ),
                _block(
                    "Result",
                    f"{SKILL}::artifact:materialize_coverage:TCN-001",
                    materialize_pair[1],
                ),
            ]
        )
    entities = {
        "schema_version": "entity-state-v1",
        "skill": SKILL,
        "entities": [],
    }
    return "".join(blocks) + _block("Entities", SKILL, entities)


def _current_pair(
    unit: str,
    generator: str,
    generator_contract: str,
    input_value: dict[str, Any],
    payload: dict[str, Any],
    *,
    model_key: str | None = None,
    model_type: str | None = None,
    technique_slug: str | None = None,
    selection_source: str | None = None,
    selection_key: str | None = None,
    scope_key: str | None = None,
) -> tuple[str, str]:
    normalized_input = _canonicalize(input_value)
    metadata = _metadata(
        unit,
        generator_contract,
        model_key=model_key,
        model_type=model_type,
        technique_slug=technique_slug,
        selection_source=selection_source,
        selection_key=selection_key,
        scope_key=scope_key,
        runtime_version="runtime-v2",
    )
    input_fp = _digest(
        {
            "skill": SKILL,
            "runtime_unit_key": unit,
            "input_mode": "direct",
            "input": normalized_input,
            "authority_refs": [],
            "reference_refs": [],
            **({"selection_source": selection_source} if selection_source else {}),
        }
    )
    model_fp = None
    if model_key is not None:
        model_fp = _digest(
            {
                "model_key": model_key,
                "model_type": model_type,
                "technique_slug": technique_slug,
                "selection_source": selection_source,
                "selection_key": selection_key,
                "input_fingerprint": input_fp,
            }
        )
    runtime_fp = _implementation(SCRIPTS / "runtime_contract.py")
    generator_fp = _implementation(SCRIPTS / f"{generator}.py")
    generation_fp = _digest(
        {
            "generator": generator,
            "envelope_version": "1",
            "input_fingerprint": input_fp,
            "model_fingerprint": model_fp,
            "runtime_contract_version": "runtime-v2",
            "generator_contract_version": generator_contract,
            "runtime_implementation_fingerprint": runtime_fp,
            "generator_implementation_fingerprint": generator_fp,
            "upstream_entity_fingerprints": [],
            "static_data_versions": {},
        }
    )
    result = {
        "envelope_version": "1",
        "skill": SKILL,
        "runtime_contract_version": "runtime-v2",
        "generator_contract_version": generator_contract,
        "generator": generator,
        "runtime_unit_key": unit,
        "model_key": model_key,
        "input_fingerprint": input_fp,
        "model_fingerprint": model_fp,
        "generation_fingerprint": generation_fp,
        "runtime_implementation_fingerprint": runtime_fp,
        "generator_implementation_fingerprint": generator_fp,
        "upstream_entity_fingerprints": [],
        "upstream_runtime_units": [],
        "support_status": "supported",
        "static_data_versions": {},
        "runtime_status": "ok",
        "result_status": "ready",
        "runtime_required": True,
        "deterministic_generated": True,
        "fallback_reason": None,
        "payload": payload,
        "issues": [],
    }
    identity = f"{SKILL}::{unit}"
    return (
        _block("Input", identity, {"metadata": metadata, "input": normalized_input}),
        _block("Result", identity, result),
    )


def _run(artifact: str, current: str | None, phase: str = "resume") -> dict[str, Any]:
    request = {
        "operation": "cutover",
        "phase": phase,
        "artifact_markdown": artifact,
        "current_v2_artifact_markdown": current,
    }
    completed = subprocess.run(
        [sys.executable, str(HELPER)],
        input=json.dumps(request, ensure_ascii=False),
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
        timeout=20,
    )
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout)


class TestTestConditionRuntimeV1Cutover(unittest.TestCase):
    def test_resume_waits_for_parent_before_dispatching_derived_model(self) -> None:
        artifact = _artifact(with_derived_model=True)
        root_request = _run(artifact, None)
        self.assertIs(root_request["valid"], True, root_request)
        condition_input = root_request["normalized_runtime_inputs"][0][
            "normalized_input"
        ]
        condition_pair = _current_pair(
            "artifact:condition_structure:all",
            "condition_structure",
            "condition-structure-v2",
            condition_input,
            {
                "tcn_id_map": [
                    {
                        "draft_key": "condition-login",
                        "tcn_id": "TCN-001",
                        "identity_action": "reuse",
                    }
                ],
                "model_key_map": [
                    {
                        "draft_key": "model-login-ep",
                        "model_key": "ep-001",
                        "model_type": "ep",
                        "technique_slug": "ep",
                        "parent_tcn_id": "TCN-001",
                        "derived_from_model_key": None,
                        "identity_action": "reuse",
                    },
                    {
                        "draft_key": "model-login-bva",
                        "model_key": "bva-001",
                        "model_type": "bva",
                        "technique_slug": "bva",
                        "parent_tcn_id": "TCN-001",
                        "derived_from_model_key": "ep-001",
                        "identity_action": "reuse",
                    },
                ],
                "tcn_id_state": [
                    {"tcn_id": "TCN-001", "status": "active", "scope_refs": []}
                ],
                "model_key_state": [
                    {
                        "model_key": "ep-001",
                        "model_type": "ep",
                        "technique_slug": "ep",
                        "parent_tcn_id": "TCN-001",
                        "selection_source": "condition_design",
                        "selection_key": None,
                        "derived_from_model_key": None,
                        "status": "active",
                        "scope_refs": [],
                    },
                    {
                        "model_key": "bva-001",
                        "model_type": "bva",
                        "technique_slug": "bva",
                        "parent_tcn_id": "TCN-001",
                        "selection_source": "condition_design",
                        "selection_key": None,
                        "derived_from_model_key": "ep-001",
                        "status": "active",
                        "scope_refs": [],
                    },
                ],
                "active_model_metadata": [
                    {
                        "model_key": "ep-001",
                        "model_type": "ep",
                        "technique_slug": "ep",
                        "parent_tcn_id": "TCN-001",
                        "scope_refs": [],
                        "content_fingerprint": "sha256:" + "a" * 64,
                    },
                    {
                        "model_key": "bva-001",
                        "model_type": "bva",
                        "technique_slug": "bva",
                        "parent_tcn_id": "TCN-001",
                        "scope_refs": [],
                        "content_fingerprint": "sha256:" + "b" * 64,
                    },
                ],
                "inactive_tcn_history": [],
                "inactive_model_history": [],
                "inactive_materialize_history": [],
            },
            scope_key="all",
        )
        model_request = _run(artifact, "".join(condition_pair))
        self.assertEqual(model_request["phase"], "models")
        self.assertEqual(
            [row["model_key"] for row in model_request["normalized_runtime_inputs"]],
            ["ep-001"],
        )
        parent_pair = _current_pair(
            "model:ep-001",
            "equivalence_partitions",
            "equivalence-partitions-v1",
            {},
            {
                "targets": [],
                "unsupported_items": [],
                "coverage_summary": {"complete": True},
                "derived_child_inputs": [
                    {
                        "child_model_key": "bva-001",
                        "parent_model_key": "ep-001",
                        "model_type": "bva",
                        "input": {"source": "parent-derived"},
                    }
                ],
            },
            model_key="ep-001",
            model_type="ep",
            technique_slug="ep",
            selection_source="condition_design",
        )
        partial_request = _run(artifact, "".join(condition_pair + parent_pair))
        self.assertEqual(partial_request["phase"], "models")
        self.assertEqual(
            [
                row["runtime_unit_key"]
                for row in partial_request["normalized_runtime_inputs"]
            ],
            ["model:bva-001"],
        )
        self.assertEqual(
            partial_request["normalized_runtime_inputs"][0]["normalized_input"],
            {"source": "parent-derived"},
        )

    def test_resume_selects_tdr_after_condition_and_skips_empty_materialize(
        self,
    ) -> None:
        artifact = _artifact(with_tdr=True)
        root_request = _run(artifact, None)
        self.assertIs(root_request["valid"], True, root_request)
        condition_input = root_request["normalized_runtime_inputs"][0][
            "normalized_input"
        ]
        condition_pair = _current_pair(
            "artifact:condition_structure:all",
            "condition_structure",
            "condition-structure-v2",
            condition_input,
            {
                "tcn_id_map": [],
                "model_key_map": [],
                "tcn_id_state": [],
                "model_key_state": [],
                "inactive_tcn_history": [],
                "inactive_model_history": [],
                "inactive_materialize_history": [],
                "active_model_metadata": [],
            },
            scope_key="all",
        )
        tdr_request = _run(artifact, "".join(condition_pair))
        self.assertEqual(tdr_request["phase"], "test-data-requirements")
        self.assertIs(tdr_request["phase_complete"], False)
        tdr_input = tdr_request["normalized_runtime_inputs"][0]["normalized_input"]
        tdr_pair = _current_pair(
            TDR_UNIT,
            "test_data_requirements",
            "test-data-requirements-v1",
            tdr_input,
            {"normalized_requirements": []},
            scope_key="all",
        )
        complete = _run(artifact, "".join(condition_pair + tdr_pair))
        self.assertEqual(complete["phase"], "materialize-coverage")
        self.assertIs(complete["phase_complete"], True)
        self.assertEqual(complete["normalized_runtime_inputs"], [])

    def test_resume_projects_condition_then_completes_empty_downstream(self) -> None:
        artifact = _artifact()
        first = _run(artifact, None)
        self.assertIs(first["valid"], True)
        self.assertEqual(first["phase"], "condition-structure")
        self.assertIs(first["phase_complete"], False)
        normalized = first["normalized_runtime_inputs"][0]["normalized_input"]
        self.assertEqual(normalized["inactive_tcn_ids"], [])
        self.assertEqual(normalized["inactive_model_keys"], [])
        self.assertEqual(normalized["inactive_materialize_history"], [])
        self.assertIs(normalized["zero_scope_terminal"], False)
        condition_pair = _current_pair(
            "artifact:condition_structure:all",
            "condition_structure",
            "condition-structure-v2",
            normalized,
            {
                "tcn_id_map": [],
                "model_key_map": [],
                "tcn_id_state": [],
                "model_key_state": [],
                "inactive_tcn_history": [],
                "inactive_model_history": [],
                "inactive_materialize_history": [],
                "active_model_metadata": [],
            },
            scope_key="all",
        )
        complete = _run(artifact, "".join(condition_pair))
        self.assertIs(complete["valid"], True)
        self.assertEqual(complete["phase"], "materialize-coverage")
        self.assertIs(complete["phase_complete"], True)
        self.assertEqual(complete["normalized_runtime_inputs"], [])

    def test_resume_dispatches_root_model_and_materialize_with_stable_identity(
        self,
    ) -> None:
        artifact = _artifact(with_model=True)
        root_request = _run(artifact, None)
        condition_input = root_request["normalized_runtime_inputs"][0][
            "normalized_input"
        ]
        active_metadata = [
            {
                "model_key": "ep-001",
                "model_type": "ep",
                "technique_slug": "ep",
                "parent_tcn_id": "TCN-001",
                "scope_refs": [],
                "content_fingerprint": "sha256:" + "a" * 64,
            }
        ]
        condition_pair = _current_pair(
            "artifact:condition_structure:all",
            "condition_structure",
            "condition-structure-v2",
            condition_input,
            {
                "tcn_id_map": [
                    {
                        "draft_key": "condition-login",
                        "tcn_id": "TCN-001",
                        "identity_action": "reuse",
                    }
                ],
                "model_key_map": [
                    {
                        "draft_key": "model-login-ep",
                        "model_key": "ep-001",
                        "model_type": "ep",
                        "technique_slug": "ep",
                        "parent_tcn_id": "TCN-001",
                        "derived_from_model_key": None,
                        "identity_action": "reuse",
                    }
                ],
                "tcn_id_state": [
                    {"tcn_id": "TCN-001", "status": "active", "scope_refs": []}
                ],
                "model_key_state": [
                    {
                        "model_key": "ep-001",
                        "model_type": "ep",
                        "technique_slug": "ep",
                        "parent_tcn_id": "TCN-001",
                        "selection_source": "condition_design",
                        "selection_key": None,
                        "derived_from_model_key": None,
                        "status": "active",
                        "scope_refs": [],
                    }
                ],
                "active_model_metadata": active_metadata,
                "inactive_tcn_history": [],
                "inactive_model_history": [],
                "inactive_materialize_history": [],
            },
            scope_key="all",
        )
        model_request = _run(artifact, "".join(condition_pair))
        self.assertEqual(model_request["phase"], "models")
        self.assertEqual(
            model_request["normalized_runtime_inputs"][0]["runtime_unit_key"],
            "model:ep-001",
        )
        model_pair = _current_pair(
            "model:ep-001",
            "equivalence_partitions",
            "equivalence-partitions-v1",
            {},
            {
                "targets": [],
                "unsupported_items": [],
                "coverage_summary": {"complete": True},
                "derived_child_inputs": [],
            },
            model_key="ep-001",
            model_type="ep",
            technique_slug="ep",
            selection_source="condition_design",
        )
        partial = "".join(condition_pair + model_pair)
        materialize_request = _run(artifact, partial)
        self.assertEqual(materialize_request["phase"], "materialize-coverage")
        self.assertIs(materialize_request["phase_complete"], False)
        materialize = materialize_request["normalized_runtime_inputs"][0]
        self.assertEqual(
            materialize["runtime_unit_key"],
            "artifact:materialize_coverage:TCN-001",
        )
        self.assertEqual(materialize["normalized_input"]["previous_ci_ids"], [])
        self.assertEqual(materialize["normalized_input"]["inactive_ci_ids"], [])
        materialize_pair = _current_pair(
            "artifact:materialize_coverage:TCN-001",
            "materialize_coverage",
            "materialize-coverage-v2",
            materialize["normalized_input"],
            {},
            scope_key="TCN-001",
        )
        complete = _run(artifact, partial + "".join(materialize_pair))
        self.assertIs(complete["valid"], True)
        self.assertEqual(complete["phase"], "materialize-coverage")
        self.assertIs(complete["phase_complete"], True)
        self.assertEqual(complete["normalized_runtime_inputs"], [])

    def test_cutover_rejects_v1_fingerprint_drift(self) -> None:
        response = _run(_artifact(tamper_root=True), None)
        self.assertIs(response["valid"], False)
        self.assertIs(response["issues"][0]["blocking"], True)

    def test_cutover_requires_v1_machine_entity_envelope(self) -> None:
        artifact = _artifact().replace(
            _block(
                "Entities",
                SKILL,
                {
                    "schema_version": "entity-state-v1",
                    "skill": SKILL,
                    "entities": [],
                },
            ),
            "",
        )
        response = _run(artifact, None)
        self.assertIs(response["valid"], False)
        self.assertEqual(response["issues"][0]["issue_type"], "invalid_input")

    def test_cutover_rejects_machine_entity_fingerprint_drift(self) -> None:
        artifact = _artifact().replace(
            '"entities":[]',
            '"entities":[{"content":{},"content_fingerprint":"sha256:'
            + "0" * 64
            + '","entity_ref":"TCN-001","entity_type":"tcn",'
            '"model_key":null,"runtime_dependencies":[],"schema_version":'
            '"entity-state-v1","skill":"test-condition-design",'
            '"upstream_entity_dependencies":[]}]',
        )
        response = _run(artifact, None)
        self.assertIs(response["valid"], False)
        self.assertEqual(response["issues"][0]["issue_type"], "invalid_input")

    def test_cutover_accepts_frozen_v1_disposition_entity_type(self) -> None:
        entity = {
            "schema_version": "entity-state-v1",
            "skill": SKILL,
            "entity_type": "disposition",
            "entity_ref": "tcn:TCN-001",
            "model_key": None,
            "content": {},
            "content_fingerprint": _digest({}),
            "upstream_entity_dependencies": [],
            "runtime_dependencies": [],
        }
        empty_entities = {
            "schema_version": "entity-state-v1",
            "skill": SKILL,
            "entities": [],
        }
        artifact = _artifact().replace(
            _block("Entities", SKILL, empty_entities),
            _block("Entities", SKILL, {**empty_entities, "entities": [entity]}),
        )
        response = _run(artifact, None)
        self.assertIs(response["valid"], True, response)

    def test_resume_rejects_future_only_unknown_and_duplicate_runtime_units(
        self,
    ) -> None:
        artifact = _artifact()
        future_only = _current_pair(
            "artifact:materialize_coverage:TCN-001",
            "materialize_coverage",
            "materialize-coverage-v2",
            {},
            {},
            scope_key="TCN-001",
        )
        response = _run(artifact, "".join(future_only))
        self.assertIs(response["valid"], False)
        self.assertTrue(response["issues"][0]["blocking"])

        root = _run(artifact, None)
        condition_input = root["normalized_runtime_inputs"][0]["normalized_input"]
        condition_pair = _current_pair(
            "artifact:condition_structure:all",
            "condition_structure",
            "condition-structure-v2",
            condition_input,
            {
                "tcn_id_map": [],
                "model_key_map": [],
                "tcn_id_state": [],
                "model_key_state": [],
                "inactive_tcn_history": [],
                "inactive_model_history": [],
                "inactive_materialize_history": [],
                "active_model_metadata": [],
            },
            scope_key="all",
        )
        unknown_model = _current_pair(
            "model:ep-999",
            "equivalence_partitions",
            "equivalence-partitions-v1",
            {},
            {
                "targets": [],
                "unsupported_items": [],
                "coverage_summary": {"complete": True},
                "derived_child_inputs": [],
            },
            model_key="ep-999",
            model_type="ep",
            technique_slug="ep",
            selection_source="user",
        )
        response = _run(artifact, "".join(condition_pair + unknown_model))
        self.assertIs(response["valid"], False)
        self.assertTrue(response["issues"][0]["blocking"])

        response = _run(artifact, "".join(condition_pair + condition_pair))
        self.assertIs(response["valid"], False)
        self.assertTrue(response["issues"][0]["blocking"])
