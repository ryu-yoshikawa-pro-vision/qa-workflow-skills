from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
RUNNER = REPO_ROOT / "scripts" / "skills" / "evals" / "deterministic" / "run.py"

VALID_RISK_OUTPUT = """# テスト分析
## プロダクトリスク一覧
| リスクID | 製品上のリスク / 失敗 | 関連する現在有効な仕様根拠 / 変更 / 依存 | 影響度 | 発生可能性 | レベル | 根拠 |
| --- | --- | --- | --- | --- | --- | --- |
| RISK-001 | 誤保存 | SPEC-001 / CHG-001 | 4 | 2 | 高 | 保存処理の全面変更 |
## 選択したテスト技法
| テスト技法 | 適用領域 | 選択理由 |
| --- | --- | --- |
| 状態遷移 | 保存 | 状態を持つ保存フローを確認するため |
## テスト可能性 / テストレベル判断
| 要件 / 懸念 | 操作可能か | 観測可能か | 合否判定可能か | 選択テストレベル |
| --- | --- | --- | --- | --- |
| 保存 | 可 | 可 | 可 | システム |
"""


def valid_risk_runtime_evidence() -> str:
    units = [
        (
            "risk_matrix",
            "artifact:risk_matrix:all",
            "risk-matrix-v1",
            "all",
            {
                "scheme": {
                    "kind": "repository-default",
                    "scheme_key": "risk-scheme-v1",
                },
                "risks": [
                    {"risk_id": "RISK-001", "impact": 4, "likelihood": 2}
                ],
            },
        ),
        (
            "technique_candidates",
            "artifact:technique_candidates:RISK-001",
            "technique-candidates-v1",
            "RISK-001",
            {
                "selection_key": "RISK-001",
                "signals": {
                    "ordered_domain": False,
                    "explicit_boundaries": False,
                    "equivalence_classes": False,
                    "multiple_discrete_conditions": False,
                    "stateful": True,
                    "multiple_factors": False,
                    "explicit_flow": False,
                    "multi_variable_domain": False,
                    "crud_model": False,
                    "operational_profile": False,
                    "metamorphic_relation": False,
                    "grammar_model": False,
                },
            },
        ),
        (
            "analysis_entities",
            "artifact:analysis_entities:all",
            "analysis-entities-v1",
            "all",
            {},
        ),
    ]
    blocks = []
    result_envelopes = {}
    for generator, runtime_unit_key, contract, scope_key, input_value in units:
        if generator == "analysis_entities":
            risk_envelope = result_envelopes["risk_matrix"]
            candidate_envelope = result_envelopes["technique_candidates"]
            candidate_result = candidate_envelope["payload"]
            signals = {
                "ordered_domain": False,
                "explicit_boundaries": False,
                "equivalence_classes": False,
                "multiple_discrete_conditions": False,
                "stateful": True,
                "multiple_factors": False,
                "explicit_flow": False,
                "multi_variable_domain": False,
                "crud_model": False,
                "operational_profile": False,
                "metamorphic_relation": False,
                "grammar_model": False,
            }
            input_value = {
                "test_analysis_context": {
                    "scope": "RISK-001: 誤保存 / CHG-001",
                    "objectives": ["保存処理のリスクを分析する"],
                    "test_levels": ["システムテスト"],
                    "environment_constraints": [],
                    "exclusions": ["E2E対象選定は今回の依頼範囲外"],
                    "blockers": ["current Authority Machine Entityがない"],
                    "test_focus_items": ["状態遷移を確認する"],
                    "testability_decisions": ["操作・観測・合否判定は可能"],
                    "residual_risks": ["現行Authorityの根拠がない"],
                    "authority_refs": ["SPEC-001"],
                    "risk_refs": ["RISK-001"],
                },
                "product_risks": [
                    {
                        "risk_id": "RISK-001",
                        "failure": "誤保存",
                        "source_refs": ["CHG-001"],
                        "authority_refs": ["SPEC-001"],
                        "impact": 4,
                        "likelihood": 2,
                        "assessment_reason": "全面変更によるリスク",
                        "confidence_note": "入力値を保持した評価",
                    }
                ],
                "technique_selections": [
                    {
                        "selection_key": "RISK-001",
                        "applicability_scope": "RISK-001",
                        "selection_source": "user",
                        "signals": signals,
                        "selected_techniques": ["state"],
                        "selection_reason": "入力で指定された技法",
                        "risk_refs": ["RISK-001"],
                        "authority_refs": ["SPEC-001"],
                        "condition_design_focus": ["状態と遷移を確認する"],
                        "undetermined_signal_closures": [
                            {
                                "signal_key": signal,
                                "handling": "selection_not_affected",
                                "reason": "選択済み技法はこの未確定signalに依存しない",
                                "question_id": None,
                            }
                            for signal in candidate_result["undetermined_signals"]
                        ],
                        "status": "active",
                    }
                ],
                "change_nodes": [],
                "change_edges": [],
                "environment_requirements": [],
                "risk_matrix_results": risk_envelope["payload"]["risks"],
                "technique_candidate_results": [candidate_result],
                "current_runtime_units": [
                    {
                        "skill": "test-analysis",
                        "runtime_unit_key": envelope["runtime_unit_key"],
                        "generation_fingerprint": envelope[
                            "generation_fingerprint"
                        ],
                    }
                    for envelope in (risk_envelope, candidate_envelope)
                ],
            }
        metadata = {
            "envelope_version": "1",
            "skill": "test-analysis",
            "runtime_contract_version": "runtime-v2",
            "generator_contract_version": contract,
            "runtime_unit_key": runtime_unit_key,
            "model_key": None,
            "model_type": None,
            "technique_slug": None,
            "selection_source": None,
            "selection_key": None,
            "scope_key": scope_key,
            "input_mode": "direct",
            "upstream_entities": [],
            "upstream_runtime_units": [],
            "static_data_versions": {},
            "authority_refs": [],
            "reference_refs": [],
        }
        request = {"metadata": metadata, "input": input_value}
        script = REPO_ROOT / "skills" / "test-analysis" / "scripts" / f"{generator}.py"
        completed = subprocess.run(
            [sys.executable, str(script)],
            input=json.dumps(request, ensure_ascii=False),
            text=True,
            capture_output=True,
            check=False,
            cwd=REPO_ROOT,
        )
        if completed.returncode != 0 or completed.stderr:
            raise AssertionError(
                f"{generator} runtime fixture failed: {completed.stderr}"
            )
        envelope = json.loads(completed.stdout)
        result_envelopes[generator] = envelope
        identity = f"test-analysis::{runtime_unit_key}"
        blocks.extend(
            [
                f"### Machine Runtime Input: {identity}\n\n```json\n"
                f"{json.dumps(request, ensure_ascii=False, indent=2)}\n```\n",
                f"### Machine Runtime Result: {identity}\n\n```json\n"
                f"{json.dumps(envelope, ensure_ascii=False, indent=2)}\n```\n",
            ]
        )
    return (
        "\n"
        + "\n".join(blocks)
        + '\n### Machine Entities: test-analysis\n\n'
        + '```json\n{"entities":[],"schema_version":"entity-state-v2",'
        + '"skill":"test-analysis"}\n```\n'
        + "\n## 最終runtime evidence gate\n\n"
        + "- verify_runtime_evidence valid: false\n"
        + "- 成果物状態: 未完成（ブロック中）\n"
    )


class CliIntegrationTests(unittest.TestCase):
    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(RUNNER), *args],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_single_valid_output_exit_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "valid.md"
            path.write_text(
                VALID_RISK_OUTPUT + valid_risk_runtime_evidence(), encoding="utf-8"
            )
            completed = self.run_cli(
                "--skill",
                "test-analysis",
                "--eval-id",
                "RISK-OUT-001",
                "--output",
                str(path),
            )
            self.assertEqual(
                completed.returncode, 0, completed.stdout + completed.stderr
            )
            self.assertEqual(json.loads(completed.stdout)["status"], "pass")

    def test_single_invalid_output_exit_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "invalid.md"
            path.write_text(
                VALID_RISK_OUTPUT.replace("| 4 | 2 | 高 |", "| 4 | 2 | 中 |")
                + valid_risk_runtime_evidence(),
                encoding="utf-8",
            )
            completed = self.run_cli(
                "--skill",
                "test-analysis",
                "--eval-id",
                "RISK-OUT-001",
                "--output",
                str(path),
            )
            self.assertEqual(
                completed.returncode, 1, completed.stdout + completed.stderr
            )
            self.assertEqual(json.loads(completed.stdout)["status"], "fail")

    def test_all_mode_missing_output_exit_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            completed = self.run_cli("--skill", "all", "--output-root", tmp)
            self.assertEqual(
                completed.returncode, 1, completed.stdout + completed.stderr
            )
            payload = json.loads(completed.stdout)
            self.assertEqual(payload["status"], "fail")
            self.assertTrue(payload["missing_outputs"])


if __name__ == "__main__":
    unittest.main()
