from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
_RUNTIME_IMPL = (
    "sha256:c8fdccf927085d3a4cfaf76f18cb8b515349ff28988a4a4a8df4c2bf566fb691"
)
_GENERATORS = {
    "test-analysis": (
        "analysis_entities",
        "analysis-entities-v1",
        "sha256:4dda5ca7d9856947aeb2acb9cb0b64dcc4e6ebf58d9ee4d21e5fd11734483190",
        "artifact:analysis_entities:all",
    ),
    "usability-inspection": (
        "inspection_runtime",
        "usability-inspection-runtime-v2",
        "sha256:f0e85e6489986f75f20f922ccded81457721887e92e6927da6e626218a1a9fe1",
        "artifact:inspection_runtime:all",
    ),
    "wcag-conformance-evaluation": (
        "wcag_runtime",
        "wcag-em-runtime-v1",
        "sha256:7c1aa0346ab3c5afdc30ed33d3c2dca68016dbbc49cc668ef69ecb46f53ffe1",
        "artifact:wcag_runtime:all",
    ),
}


def _digest(value: Any) -> str:
    raw = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _artifact(skill: str, *, corrupt_result: bool = False) -> str:
    generator, contract, generator_fp, unit = _GENERATORS[skill]
    input_value: dict[str, Any] = {"saved_semantic_input": "kept"}
    if skill == "test-analysis":
        input_value = {
            "test_analysis_context": {},
            "product_risks": [],
            "technique_selections": [],
            "change_nodes": [],
            "change_edges": [],
            "environment_requirements": [],
            "risk_matrix_results": [],
            "technique_candidate_results": [],
            "current_runtime_units": [],
        }
    metadata = {
        "envelope_version": "1",
        "skill": skill,
        "runtime_contract_version": "runtime-v1",
        "generator_contract_version": contract,
        "runtime_unit_key": unit,
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
    input_fp_value: dict[str, Any] = {
        "skill": skill,
        "runtime_unit_key": unit,
        "input_mode": "artifact",
        "input": input_value,
        "authority_refs": [],
        "reference_refs": [],
    }
    input_fp = _digest(input_fp_value)
    generation_fp = _digest(
        {
            "generator": generator,
            "envelope_version": "1",
            "input_fingerprint": input_fp,
            "model_fingerprint": None,
            "runtime_contract_version": "runtime-v1",
            "generator_contract_version": contract,
            "runtime_implementation_fingerprint": _RUNTIME_IMPL,
            "generator_implementation_fingerprint": generator_fp,
            "upstream_entity_fingerprints": [],
            "static_data_versions": {},
        }
    )
    result = {
        "envelope_version": "1",
        "skill": skill,
        "runtime_contract_version": "runtime-v1",
        "generator_contract_version": contract,
        "generator": generator,
        "runtime_unit_key": unit,
        "model_key": None,
        "input_fingerprint": "sha256:" + "0" * 64 if corrupt_result else input_fp,
        "model_fingerprint": None,
        "generation_fingerprint": generation_fp,
        "runtime_implementation_fingerprint": _RUNTIME_IMPL,
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
        "payload": {},
        "issues": [],
    }

    def block(kind: str, body: Any) -> str:
        identity = f"{skill}::{unit}"
        return (
            f"### Machine Runtime {kind}: {identity}\n\n```json\n"
            + json.dumps(
                body, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            )
            + "\n```\n"
        )

    return block("Input", {"metadata": metadata, "input": input_value}) + block(
        "Result", result
    )


def _run_reader(skill: str, artifact: str) -> dict[str, Any]:
    script = ROOT / "skills" / skill / "scripts" / "runtime_v1_input_reader.py"
    completed = subprocess.run(
        [sys.executable, str(script)],
        input=json.dumps(
            {"operation": "extract-validated-inputs", "artifact_markdown": artifact}
        ),
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
        timeout=15,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    return json.loads(completed.stdout)


def test_each_reader_accepts_integral_v1_pair_and_returns_saved_input() -> None:
    for skill in _GENERATORS:
        result = _run_reader(skill, _artifact(skill))
        assert result["valid"] is True
        assert result["source_runtime_contract_version"] == "runtime-v1"
        assert len(result["normalized_runtime_inputs"]) == 1
        assert (
            result["normalized_runtime_inputs"][0]["runtime_unit_key"]
            == _GENERATORS[skill][3]
        )
        assert result["normalized_runtime_inputs"][0]["normalized_input"]


def test_readers_fail_closed_for_changed_fingerprint_or_missing_pair() -> None:
    for skill in _GENERATORS:
        tampered = _run_reader(skill, _artifact(skill, corrupt_result=True))
        assert tampered["valid"] is False
        assert tampered["issues"][0]["blocking"] is True
        missing_pair = _run_reader(skill, "")
        assert missing_pair["valid"] is False
        assert missing_pair["issues"][0]["issue_type"] == "invalid_input"
