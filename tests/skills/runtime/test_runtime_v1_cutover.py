from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
SKILL = "test-requirement-design"
UNIT = "artifact:requirement_structure:all"
RUNTIME_IMPL = "sha256:c8fdccf927085d3a4cfaf76f18cb8b515349ff28988a4a4a8df4c2bf566fb691"
GENERATOR_IMPL = (
    "sha256:1f58df5515e09c69b2670bcbc7375fe8d87e5ca10c6638d3898603c956702318"
)


def _digest(value: Any) -> str:
    data = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(data.encode("utf-8")).hexdigest()


def _artifact(*, tamper_result: bool = False) -> str:
    input_value = {
        "authorities": [{"authority_id": "AUTH-001"}],
        "risks": [{"risk_id": "RISK-001", "mapped_priority": "中"}],
        "test_requirements": [
            {
                "draft_key": "tr-login",
                "identity_action": "new",
                "reuse_id": None,
                "text": "ログインできる",
                "authority_refs": ["AUTH-001"],
                "risk_refs": ["RISK-001"],
                "priority": "高",
                "priority_override_reason": None,
                "test_level": "system",
                "observation_method": "画面表示",
            }
        ],
        "dispositions": [],
        "previous_tr_ids": [],
        "update_scope_tr_ids": [],
    }
    metadata = {
        "envelope_version": "1",
        "skill": SKILL,
        "runtime_contract_version": "runtime-v1",
        "generator_contract_version": "requirement-structure-v1",
        "runtime_unit_key": UNIT,
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
    input_fp = _digest(
        {
            "skill": SKILL,
            "runtime_unit_key": UNIT,
            "input_mode": "artifact",
            "input": input_value,
            "authority_refs": [],
            "reference_refs": [],
        }
    )
    generation_fp = _digest(
        {
            "generator": "requirement_structure",
            "envelope_version": "1",
            "input_fingerprint": input_fp,
            "model_fingerprint": None,
            "runtime_contract_version": "runtime-v1",
            "generator_contract_version": "requirement-structure-v1",
            "runtime_implementation_fingerprint": RUNTIME_IMPL,
            "generator_implementation_fingerprint": GENERATOR_IMPL,
            "upstream_entity_fingerprints": [],
            "static_data_versions": {},
        }
    )
    result = {
        "envelope_version": "1",
        "skill": SKILL,
        "runtime_contract_version": "runtime-v1",
        "generator_contract_version": "requirement-structure-v1",
        "generator": "requirement_structure",
        "runtime_unit_key": UNIT,
        "model_key": None,
        "input_fingerprint": "sha256:" + "0" * 64 if tamper_result else input_fp,
        "model_fingerprint": None,
        "generation_fingerprint": generation_fp,
        "runtime_implementation_fingerprint": RUNTIME_IMPL,
        "generator_implementation_fingerprint": GENERATOR_IMPL,
        "upstream_entity_fingerprints": [],
        "upstream_runtime_units": [],
        "support_status": "supported",
        "static_data_versions": {},
        "runtime_status": "ok",
        "result_status": "ready",
        "runtime_required": True,
        "deterministic_generated": True,
        "fallback_reason": None,
        "payload": {
            "tr_id_map": [
                {"draft_key": "tr-login", "tr_id": "TR-001", "identity_action": "new"}
            ],
            "tr_id_state": [{"tr_id": "TR-001", "status": "active"}],
        },
        "issues": [],
    }

    def block(kind: str, value: Any) -> str:
        body = json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
        return f"### Machine Runtime {kind}: {SKILL}::{UNIT}\n\n```json\n{body}\n```\n"

    return block("Input", {"metadata": metadata, "input": input_value}) + block(
        "Result", result
    )


def _run(artifact: str) -> tuple[int, dict[str, Any]]:
    script = ROOT / "skills" / SKILL / "scripts" / "runtime_v1_cutover.py"
    request = {
        "operation": "cutover",
        "phase": "all",
        "artifact_markdown": artifact,
        "current_v2_artifact_markdown": None,
    }
    completed = subprocess.run(
        [sys.executable, str(script)],
        input=json.dumps(request),
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
        timeout=15,
    )
    return completed.returncode, json.loads(completed.stdout)


def _test_trd_cutover_projects_exact_v1_map_into_complete_v2_input() -> None:
    code, response = _run(_artifact())
    assert code == 0
    assert response["valid"] is True
    normalized = response["normalized_runtime_inputs"][0]["normalized_input"]
    assert normalized["acceptance_criteria"] == []
    assert normalized["scope_ids"] == []
    assert normalized["previous_tr_ids"] == [
        {"tr_id": "TR-001", "status": "active", "scope_refs": []}
    ]
    assert normalized["update_scope_tr_ids"] == ["TR-001"]
    assert normalized["test_requirements"][0]["identity_action"] == "reuse"
    assert normalized["test_requirements"][0]["reuse_id"] == "TR-001"
    assert normalized["test_requirements"][0]["acceptance_refs"] == []
    assert normalized["zero_scope_terminal"] is False


def _test_trd_cutover_fails_closed_on_v1_fingerprint_drift() -> None:
    code, response = _run(_artifact(tamper_result=True))
    assert code == 0
    assert response["valid"] is False
    assert response["issues"][0]["blocking"] is True


class TestRuntimeV1Cutover(unittest.TestCase):
    def test_trd_cutover_projects_exact_v1_map_into_complete_v2_input(self) -> None:
        _test_trd_cutover_projects_exact_v1_map_into_complete_v2_input()

    def test_trd_cutover_fails_closed_on_v1_fingerprint_drift(self) -> None:
        _test_trd_cutover_fails_closed_on_v1_fingerprint_drift()
