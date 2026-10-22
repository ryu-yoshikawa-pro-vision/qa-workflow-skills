from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.skills.evals.agent.common import AgentEvalError, visible_skill_names
from scripts.skills.evals.agent.improve import (
    _skill_use_for_attempt,
    _stable_failures,
    _validate_repair_diff,
)


class ImprovementGateTests(unittest.TestCase):
    def test_agent_workspace_exposes_only_skills_routed_by_selected_cases(self) -> None:
        self.assertEqual(
            visible_skill_names(
                [
                    {"skill": "qa-workflow"},
                    {"skill": "test-case-design"},
                    {"skill": "qa-workflow"},
                ]
            ),
            ["qa-workflow", "test-case-design"],
        )

    def test_skill_use_observation_is_read_from_the_specific_routed_skill(self) -> None:
        attempt = {
            "skill_use_observation": {
                "qa-workflow": "observed",
                "test-case-design": "unverified",
            }
        }
        self.assertEqual(_skill_use_for_attempt(attempt, "qa-workflow"), "observed")
        self.assertEqual(_skill_use_for_attempt(attempt, "test-case-design"), "unverified")
        self.assertEqual(_skill_use_for_attempt({}, "qa-workflow"), "unverified")

    def test_reproducible_approved_critical_failure_is_selected(self) -> None:
        attempts = [
            {"attempt": {"attempt_id": f"attempt-{index}"}, "criteria": {"QTS-SEM-006": {"rating": 1, "status": "fail"}}}
            for index in (1, 2)
        ]
        verified = {"QTS-SEM-006": {"status": "verified", "case_id": "major-violation-006"}}
        self.assertEqual(_stable_failures(attempts, verified)[0]["criterion"], "QTS-SEM-006")

    def test_judge_jitter_or_unverified_fixture_blocks_repair(self) -> None:
        attempts = [
            {"criteria": {"QTS-SEM-006": {"rating": rating, "status": status}}}
            for rating, status in ((1, "fail"), (2, "needs_review"))
        ]
        self.assertEqual(_stable_failures(attempts, {"QTS-SEM-006": {"status": "verified"}}), [])
        stable = [
            {"criteria": {"QTS-SEM-006": {"rating": 1, "status": "fail"}}},
            {"criteria": {"QTS-SEM-006": {"rating": 1, "status": "fail"}}},
        ]
        self.assertEqual(_stable_failures(stable, {}), [])

    def test_repair_diff_accepts_only_requested_skill_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            skills = Path(temporary) / ".agents" / "skills"
            skill = skills / "qa-workflow"
            skill.mkdir(parents=True)
            source = skill / "SKILL.md"
            source.write_text("before\n", encoding="utf-8")
            before = {"qa-workflow/SKILL.md": "old"}
            source.write_text("after\n", encoding="utf-8")
            changes, _ = _validate_repair_diff(before, skills, "qa-workflow", {"SKILL.md"})
        self.assertEqual(changes[0]["path"], "SKILL.md")

    def test_repair_diff_rejects_unrequested_path(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            skills = Path(temporary)
            skill = skills / "qa-workflow"
            skill.mkdir()
            (skill / "SKILL.md").write_text("changed", encoding="utf-8")
            with self.assertRaises(AgentEvalError):
                _validate_repair_diff({"qa-workflow/SKILL.md": "old"}, skills, "qa-workflow", {"references/guide.md"})


if __name__ == "__main__":
    unittest.main()
