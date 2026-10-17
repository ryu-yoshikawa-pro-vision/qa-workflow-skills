from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
SKILL = "test-case-design"
SCRIPTS = ROOT / "skills" / SKILL / "scripts"
UNIT = "artifact:case_structure:all"
RUNTIME_IMPL = "sha256:c8fdccf927085d3a4cfaf76f18cb8b515349ff28988a4a4a8df4c2bf566fb691"
GENERATOR_IMPL = (
    "sha256:ed9b27273306a21f3f522a97e5d8bd4cc3065bacc322a1e64cd240da60e71d8c"
)
_SPEC = importlib.util.spec_from_file_location(
    "case_runtime_v1_cutover_contract", SCRIPTS / "runtime_contract.py"
)
assert _SPEC is not None and _SPEC.loader is not None
_RUNTIME = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _RUNTIME
_SPEC.loader.exec_module(_RUNTIME)


def _source_input() -> dict[str, Any]:
    return {
        "test_conditions": [
            {
                "tcn_id": "TCN-001",
                "tr_refs": [],
                "priority": "中",
                "scope_refs": [],
            }
        ],
        "coverage_items": [
            {
                "ci_id": "TCN-001-CI01",
                "tcn_id": "TCN-001",
                "model_key": "ep-001",
                "priority": "中",
                "authority_refs": [],
                "source_kind": "runtime_target",
                "execution": {"input": {"role": "admin"}},
                "semantic_item_key": None,
                "semantic_item_text": None,
                "semantic_source_targets": [],
                "test_data_requirement_refs": [],
                "scope_refs": [],
            }
        ],
        "environment_requirements": [],
        "test_data_requirements": [],
        "test_cases": [
            {
                "draft_key": "tc-admin",
                "identity_action": "new",
                "reuse_id": None,
                "title_or_purpose": "管理者ロールを確認する",
                "tr_refs": [],
                "tcn_refs": ["TCN-001"],
                "ci_refs": ["TCN-001-CI01"],
                "environment_requirement_refs": [],
                "test_data_requirement_refs": [],
                "priority": "中",
                "priority_override_reason": None,
                "preconditions": ["対象環境を準備する"],
                "test_data": ["role=admin"],
                "steps": [{"number": 1, "text": "管理者として操作する"}],
                "expected_results": [
                    {
                        "number": 1,
                        "text": "管理者向け結果が表示される",
                        "authority_refs": [],
                    }
                ],
                "postconditions_or_cleanup": ["作成データを削除する"],
            }
        ],
        "dispositions": [],
        "previous_tc_ids": [],
        "update_scope_tc_ids": [],
    }


def _source_metadata() -> dict[str, Any]:
    tcn_content = {
        "tcn_id": "TCN-001",
        "tr_refs": [],
        "priority": "中",
        "scope_refs": [],
    }
    ci_content = {
        "ci_id": "TCN-001-CI01",
        "tcn_id": "TCN-001",
        "model_key": "ep-001",
        "priority": "中",
        "authority_refs": [],
        "source_kind": "runtime_target",
        "execution": {"input": {"role": "admin"}},
        "semantic_item_key": None,
        "semantic_item_text": None,
        "semantic_source_targets": [],
        "test_data_requirement_refs": [],
        "scope_refs": [],
    }
    tcn = {
        "skill": "test-condition-design",
        "entity_type": "tcn",
        "entity_ref": "TCN-001",
        "content": tcn_content,
    }
    ci = {
        "skill": "test-condition-design",
        "entity_type": "ci",
        "entity_ref": "TCN-001-CI01",
        "content": ci_content,
    }
    return {
        "envelope_version": "1",
        "skill": SKILL,
        "runtime_contract_version": "runtime-v1",
        "generator_contract_version": "case-structure-v1",
        "runtime_unit_key": UNIT,
        "model_key": None,
        "model_type": None,
        "technique_slug": None,
        "selection_source": None,
        "selection_key": None,
        "scope_key": None,
        "input_mode": "artifact",
        "upstream_entities": [tcn, ci],
        "upstream_runtime_units": [],
        "static_data_versions": {},
        "authority_refs": [],
        "reference_refs": [],
    }


def _artifact(
    *,
    mapping: list[dict[str, Any]] | None = None,
    tamper_result: bool = False,
) -> str:
    metadata = _source_metadata()
    input_value = _source_input()
    v2_metadata = dict(metadata)
    v2_metadata["runtime_contract_version"] = "runtime-v2"
    input_fp = _RUNTIME.input_fingerprint(
        SKILL,
        UNIT,
        metadata["input_mode"],
        input_value,
        metadata["authority_refs"],
        metadata["reference_refs"],
        metadata["selection_source"],
    )
    model_fp = _RUNTIME.model_fingerprint(v2_metadata, input_fp)
    upstream = _RUNTIME.upstream_entity_fingerprints(
        _RUNTIME.validate_upstream_entities(v2_metadata)
    )
    generation_fp = _RUNTIME.generation_fingerprint(
        generator="case_structure",
        input_fp=input_fp,
        model_fp=model_fp,
        runtime_contract_version="runtime-v1",
        generator_contract_version="case-structure-v1",
        runtime_impl_fp=RUNTIME_IMPL,
        generator_impl_fp=GENERATOR_IMPL,
        upstream=upstream,
        static_data_versions=metadata["static_data_versions"],
    )
    result = {
        "envelope_version": "1",
        "skill": SKILL,
        "runtime_contract_version": "runtime-v1",
        "generator_contract_version": "case-structure-v1",
        "generator": "case_structure",
        "runtime_unit_key": UNIT,
        "model_key": None,
        "input_fingerprint": "sha256:" + "0" * 64 if tamper_result else input_fp,
        "model_fingerprint": model_fp,
        "generation_fingerprint": generation_fp,
        "runtime_implementation_fingerprint": RUNTIME_IMPL,
        "generator_implementation_fingerprint": GENERATOR_IMPL,
        "upstream_entity_fingerprints": upstream,
        "upstream_runtime_units": [],
        "support_status": "supported",
        "static_data_versions": {},
        "runtime_status": "ok",
        "result_status": "ready",
        "runtime_required": True,
        "deterministic_generated": True,
        "fallback_reason": None,
        "payload": {
            "tc_id_map": mapping
            if mapping is not None
            else [
                {
                    "draft_key": "tc-admin",
                    "tc_id": "TC-001",
                    "identity_action": "new",
                }
            ],
            "tc_id_state": [
                {"tc_id": "TC-001", "status": "active"},
                {"tc_id": "TC-002", "status": "deleted"},
            ],
        },
        "issues": [],
    }

    def block(kind: str, value: Any) -> str:
        body = _RUNTIME.canonical_json_text(value)
        return f"### Machine Runtime {kind}: {SKILL}::{UNIT}\n\n```json\n{body}\n```\n"

    return block("Input", {"metadata": metadata, "input": input_value}) + block(
        "Result", result
    )


def _run_cutover(artifact: str) -> tuple[int, dict[str, Any]]:
    request = {
        "operation": "cutover",
        "phase": "all",
        "artifact_markdown": artifact,
        "current_v2_artifact_markdown": None,
    }
    completed = subprocess.run(
        [sys.executable, str(SCRIPTS / "runtime_v1_cutover.py")],
        input=json.dumps(request),
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
        timeout=15,
    )
    return completed.returncode, json.loads(completed.stdout)


class TestCaseRuntimeV1Cutover(unittest.TestCase):
    def test_cutover_preserves_semantics_and_reuses_v1_active_ids_in_v2_runtime(self):
        code, response = _run_cutover(_artifact())
        self.assertEqual(code, 0)
        self.assertIs(response["valid"], True)
        value = response["normalized_runtime_inputs"][0]["normalized_input"]
        original = _source_input()
        for field in (
            "test_conditions",
            "coverage_items",
            "environment_requirements",
            "test_data_requirements",
            "dispositions",
        ):
            self.assertEqual(value[field], original[field])
        self.assertEqual(value["test_cases"][0]["identity_action"], "reuse")
        self.assertEqual(value["test_cases"][0]["reuse_id"], "TC-001")
        self.assertEqual(
            value["previous_tc_ids"],
            [
                {"tc_id": "TC-001", "status": "active", "scope_refs": []},
                {"tc_id": "TC-002", "status": "deleted", "scope_refs": []},
            ],
        )
        self.assertEqual(value["update_scope_tc_ids"], ["TC-001"])
        self.assertEqual(value["inactive_tc_ids"], [])
        self.assertEqual(value["inactive_tc_history"], [])

        metadata = _source_metadata()
        metadata.update(
            {
                "runtime_contract_version": "runtime-v2",
                "generator_contract_version": "case-structure-v2",
            }
        )
        completed = subprocess.run(
            [sys.executable, str(SCRIPTS / "case_structure.py")],
            input=json.dumps({"metadata": metadata, "input": value}),
            text=True,
            encoding="utf-8",
            capture_output=True,
            check=False,
            timeout=15,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        generated = json.loads(completed.stdout)
        self.assertEqual(generated["runtime_status"], "ok", generated)
        self.assertEqual(generated["payload"]["tc_id_map"][0]["tc_id"], "TC-001")
        self.assertEqual(
            generated["payload"]["tc_id_state"],
            [
                {"tc_id": "TC-001", "status": "active", "scope_refs": []},
                {"tc_id": "TC-002", "status": "deleted", "scope_refs": []},
            ],
        )

    def test_cutover_rejects_fingerprint_drift_and_non_exact_mapping(self):
        for artifact in (
            _artifact(tamper_result=True),
            _artifact(mapping=[]),
            _artifact(
                mapping=[
                    {
                        "draft_key": "tc-admin",
                        "tc_id": "TC-001",
                        "identity_action": "new",
                    },
                    {
                        "draft_key": "tc-admin",
                        "tc_id": "TC-003",
                        "identity_action": "new",
                    },
                ]
            ),
        ):
            code, response = _run_cutover(artifact)
            self.assertEqual(code, 0)
            self.assertIs(response["valid"], False)
            self.assertTrue(response["issues"][0]["blocking"])
