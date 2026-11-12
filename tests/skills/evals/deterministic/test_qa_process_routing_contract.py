from __future__ import annotations

import ast
import json
import unittest
from pathlib import Path

from scripts.skills.evals.deterministic.common import (
    CANONICAL_SKILLS,
    RUNTIME_UNIT_SKILLS,
    WORKFLOW_VERIFIED_SKILLS,
)
from scripts.skills.evals.deterministic.loader import load_validators

REPO_ROOT = Path(__file__).resolve().parents[4]
ROUTING_DIR = REPO_ROOT / "skills" / "qa-workflow" / "evals" / "deterministic"
VALIDATORS = load_validators()

# 開発連動QA Plan・QA全工程Planで新設したSkillの開始・停止境界。
# 期待値はPlanとqa-workflow guidanceから固定し、candidateから生成しない。
EXPECTED_PROCESS_ROUTES = {
    "WF-PROCESS-001": ("project-context", "project-context", ["project-context"]),
    "WF-PROCESS-002": ("feature-analysis", "feature-analysis", ["feature-analysis"]),
    "WF-PROCESS-003": (
        "test-item-analysis",
        "test-item-analysis",
        ["test-item-analysis"],
    ),
    "WF-PROCESS-004": (
        "test-condition-analysis",
        "test-condition-analysis",
        ["test-condition-analysis"],
    ),
    "WF-PROCESS-005": (
        "test-requirements-analysis",
        "test-requirements-analysis",
        ["test-requirements-analysis"],
    ),
    "WF-PROCESS-006": (
        "test-requirements-analysis",
        "test-management",
        ["test-requirements-analysis", "test-architecture-design", "test-management"],
    ),
    "WF-PROCESS-007": ("test-management", "test-management", ["test-management"]),
    "WF-PROCESS-008": (
        "e2e-test-selection",
        "e2e-test-selection",
        ["e2e-test-selection"],
    ),
    "WF-PROCESS-009": (
        "e2e-test-selection",
        "e2e-test-implementation",
        ["e2e-test-selection", "e2e-test-inspection", "e2e-test-implementation"],
    ),
    "WF-PROCESS-010": (
        "defect-management",
        "defect-management",
        ["defect-management"],
    ),
    "WF-PROCESS-011": ("test-reporting", "test-reporting", ["test-reporting"]),
    "WF-PROCESS-012": ("test-evaluation", "test-evaluation", ["test-evaluation"]),
    "WF-PROCESS-013": (
        "testware-implementation",
        "testware-implementation",
        ["testware-implementation"],
    ),
    "WF-PROCESS-014": (
        "testware-execution",
        "testware-execution",
        ["testware-execution"],
    ),
}


def render(candidate: dict) -> str:
    rows = [
        f"| {skill} |  | {candidate.get('states', {}).get(skill, '完了')} | {candidate['id']} | |"
        for skill in candidate["skills"]
    ]
    return f"""# Workflow
- ワークフロー全体状態: {candidate["overall"]}
- 開始Skill: {candidate["start"]}
- 開始対象 / 実行範囲:
- 最終Skill: {candidate["final"]}
- 最終対象 / 実行範囲:
| Skill | 対象 / 実行範囲 | 状態 | 成果物 / バージョン | ブロッカー / 備考 |
| --- | --- | --- | --- | --- |
{chr(10).join(rows)}
"""


def expected_for(case: dict) -> dict:
    return {
        "expected_start_skill": case["start"],
        "expected_final_skill": case["final"],
        "expected_skills": case["skills"],
        "expected_overall_state": case["overall"],
        "expected_skill_states": {
            skill: case.get("states", {}).get(skill, "完了") for skill in case["skills"]
        },
    }


class QaProcessRoutingContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.cases = {
            row["id"]: row
            for row in json.loads(
                (ROUTING_DIR / "routing_cases.json").read_text(encoding="utf-8")
            )
        }
        self.candidates = {
            row["id"]: row
            for row in json.loads(
                (ROUTING_DIR / "routing_candidate_outputs.json").read_text(
                    encoding="utf-8"
                )
            )
        }

    def validate(self, candidate: dict, case: dict) -> dict:
        return VALIDATORS["qa-workflow"](
            render(candidate), expected_for(case), "WF-PROCESS-UNIT"
        ).to_dict()

    def test_expected_routes_are_fixed_independently_of_candidates(self) -> None:
        actual = {
            case_id: (row["start"], row["final"], row["skills"])
            for case_id, row in self.cases.items()
            if case_id.startswith("WF-PROCESS-")
        }
        self.assertEqual(actual, EXPECTED_PROCESS_ROUTES)
        for case_id, row in self.cases.items():
            if case_id.startswith("WF-PROCESS-"):
                self.assertTrue(row["input_conditions"].strip(), case_id)

    def test_every_new_owner_skill_has_a_routing_case(self) -> None:
        routed = {
            skill for case_id, row in self.cases.items() for skill in row["skills"]
        }
        repository_skills = {
            path.parent.name for path in (REPO_ROOT / "skills").glob("*/SKILL.md")
        }
        # agent-answer-formはworkflow状態の担当Skillではない補助Skill。
        self.assertEqual(
            repository_skills - {"agent-answer-form"}, set(CANONICAL_SKILLS)
        )
        unrouted = sorted(
            CANONICAL_SKILLS
            - routed
            - {
                # 以下は既存fixture群の対象外で、各Skillのtrigger / output evalが担当。
                "test-requirement-design",
                "test-condition-design",
            }
        )
        self.assertEqual(unrouted, [])

    def test_candidates_pass_the_real_qa_workflow_validator(self) -> None:
        for case_id in EXPECTED_PROCESS_ROUTES:
            with self.subTest(case=case_id):
                result = self.validate(self.candidates[case_id], self.cases[case_id])
                self.assertEqual(result["status"], "pass", result)

    def test_legacy_test_analysis_selection_route_is_rejected(self) -> None:
        candidate = dict(self.candidates["WF-PROCESS-008"])
        candidate["start"] = candidate["final"] = "test-analysis"
        candidate["skills"] = ["test-analysis"]
        result = self.validate(candidate, self.cases["WF-PROCESS-008"])
        failed = {row["id"] for row in result["assertions"] if row["status"] == "fail"}
        self.assertTrue({"WF-D006", "WF-D007", "WF-D008"} <= failed, result)

    def test_planning_route_cannot_skip_architecture_or_stop_early(self) -> None:
        case = self.cases["WF-PROCESS-006"]
        skipped = dict(self.candidates["WF-PROCESS-006"])
        skipped["skills"] = ["test-requirements-analysis", "test-management"]
        stopped = dict(self.candidates["WF-PROCESS-006"])
        stopped["final"] = "test-architecture-design"
        for candidate, assertion in ((skipped, "WF-D008"), (stopped, "WF-D007")):
            with self.subTest(assertion=assertion):
                result = self.validate(candidate, case)
                failed = {
                    row["id"] for row in result["assertions"] if row["status"] == "fail"
                }
                self.assertIn(assertion, failed, result)

    def test_unknown_skill_name_is_rejected(self) -> None:
        candidate = dict(self.candidates["WF-PROCESS-010"])
        candidate["skills"] = ["defect-tracking"]
        result = self.validate(candidate, self.cases["WF-PROCESS-010"])
        failed = {row["id"] for row in result["assertions"] if row["status"] == "fail"}
        self.assertIn("WF-D002", failed, result)


def workflow_runtime_v2_roots() -> set[str]:
    source = (REPO_ROOT / "skills/qa-workflow/scripts/workflow_runtime.py").read_text(
        encoding="utf-8"
    )
    for node in ast.parse(source).body:
        if (
            isinstance(node, ast.Assign)
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id == "RUNTIME_V2_SKILL_ROOTS"
        ):
            return set(ast.literal_eval(node.value.args[0]))
    raise AssertionError("RUNTIME_V2_SKILL_ROOTS is not declared")


def workflow_runtime_doc(skill: str) -> str:
    return f"""# Workflow

- ワークフロー全体状態: 実行中
- 開始Skill: {skill}
- 開始対象 / 実行範囲:
- 最終Skill: {skill}
- 最終対象 / 実行範囲:

## ワークフロー状態

| Skill | 対象 / 実行範囲 | 状態 | 成果物 / バージョン | ブロッカー / 備考 |
| --- | --- | --- | --- | --- |
| {skill} | | 実行中 | WF-RUNTIME | |

## runtime状態

| Skill | Runtime Unit Key | Support Status | Result Status | Freshness | Runtime Status | Runtime Required | Deterministic Generated |
| --- | --- | --- | --- | --- | --- | --- | --- |
| {skill} | artifact:fake:all | supported | ready | current | ok | Yes | Yes |
"""


def question_doc(runtime_skill: str) -> str:
    return f"""# 不明点・矛盾分析

## 不明点 / 質問一覧

| ID | 問題 / 質問 | 根拠 | 分類 | 影響範囲 / 成果物 | 関連UNKNOWN ID | Runtime Skill | Runtime Unit Key | Model Key | Target Key | Generation Fingerprint | 回答なしの場合の扱い | 回答後の正規化先 | 再開Skill | 再開対象 / 実行範囲 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Q-001 | 計画の承認者が不明 | SPEC | 要確認 | plan | | {runtime_skill} | artifact:x:all | | | sha256:{"0" * 64} | 確認まで保留 | SPEC | spec-analysis | |

## 質問ID履歴

| ID |
| --- |
| Q-001 |

## 仮定候補

| 仮定候補 | 状態 | 根拠 / 理由 | 影響範囲 | 正式ASM ID |
| --- | --- | --- | --- | --- |

## ブロック中範囲

| ブロッカーID | ブロック中成果物 / 範囲 | 必要な決定 / 情報源 | Runtime Skill | Runtime Unit Key | Model Key | Target Key | Generation Fingerprint | 再開Skill | 再開対象 / 実行範囲 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
"""


class RuntimeSkillNameContractTests(unittest.TestCase):
    def test_runtime_unit_skills_match_skills_with_runtime_contract(self) -> None:
        actual = {
            path.parents[1].name
            for path in (REPO_ROOT / "skills").glob("*/scripts/runtime_contract.py")
        }
        self.assertEqual(set(RUNTIME_UNIT_SKILLS), actual)

    def test_workflow_verified_skills_match_runtime_v2_roots(self) -> None:
        self.assertEqual(set(WORKFLOW_VERIFIED_SKILLS), workflow_runtime_v2_roots())

    def test_workflow_runtime_row_rejects_unverified_skill(self) -> None:
        def d019(skill: str) -> str:
            result = VALIDATORS["qa-workflow"](
                workflow_runtime_doc(skill), {}, "WF-RUNTIME-UNIT"
            ).to_dict()
            return next(
                row["status"] for row in result["assertions"] if row["id"] == "WF-D019"
            )

        self.assertEqual(d019("test-case-design"), "pass")
        for skill in ("defect-management", "test-management", "spec-analysis"):
            with self.subTest(skill=skill):
                self.assertEqual(d019(skill), "fail")

    def test_question_runtime_skill_rejects_skill_without_runtime(self) -> None:
        def runtime_issue(skill: str) -> bool:
            result = VALIDATORS["question-analysis"](
                question_doc(skill), {}, "QUESTION-RUNTIME-UNIT"
            ).to_dict()
            return any(
                row["status"] == "fail"
                and "Runtime Skill"
                in json.dumps(row.get("evidence"), ensure_ascii=False)
                for row in result["assertions"]
            )

        self.assertFalse(runtime_issue("spec-analysis"))
        for skill in ("test-management", "defect-management", "feature-analysis"):
            with self.subTest(skill=skill):
                self.assertTrue(runtime_issue(skill))


if __name__ == "__main__":
    unittest.main()
