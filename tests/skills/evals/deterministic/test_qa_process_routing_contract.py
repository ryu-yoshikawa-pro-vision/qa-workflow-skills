from __future__ import annotations

import json
import unittest
from pathlib import Path

from scripts.skills.evals.deterministic.common import CANONICAL_SKILLS
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


if __name__ == "__main__":
    unittest.main()
