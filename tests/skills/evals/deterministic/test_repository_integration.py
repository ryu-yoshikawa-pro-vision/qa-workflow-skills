from __future__ import annotations

import json
import unittest
from pathlib import Path

from scripts.skills.evals.deterministic.loader import (
    discover_output_eval_skills,
    load_validators,
)

REPO_ROOT = Path(__file__).resolve().parents[4]
SKILLS_ROOT = REPO_ROOT / "skills"
FINAL_RUNTIME_EVIDENCE_POLICIES = {
    "coverage-analysis": {
        "runtime_unit_key": "artifact:traceability:all",
        "partial_rerun": False,
    },
    "qa-workflow": {
        "runtime_unit_key": "artifact:workflow_runtime:all",
        "partial_rerun": False,
    },
    "test-analysis": {
        "runtime_unit_key": "artifact:analysis_entities:all",
        "partial_rerun": False,
        "accepted_blocked_assertion_id": "RISK-D018",
    },
    "test-case-design": {
        "runtime_unit_key": "artifact:case_structure:all",
        "partial_rerun": False,
    },
    "test-condition-design": {
        "runtime_unit_key": "artifact:condition_structure:all",
        "partial_rerun": False,
    },
    "test-requirement-design": {
        "runtime_unit_key": "artifact:requirement_structure:all",
        "partial_rerun": False,
    },
}


class RepositoryDeterministicIntegrationTests(unittest.TestCase):
    def test_output_eval_manifests_have_loadable_validators(self) -> None:
        expected = sorted(
            manifest.parents[2].name
            for manifest in SKILLS_ROOT.glob("*/evals/output/evals.json")
        )
        self.assertTrue(expected)
        self.assertEqual(discover_output_eval_skills(SKILLS_ROOT), expected)
        validators = load_validators(SKILLS_ROOT)
        self.assertEqual(sorted(validators), expected)
        self.assertTrue(all(callable(validate) for validate in validators.values()))

    def test_each_skill_final_runtime_gate_has_an_expected_independent_policy(
        self,
    ) -> None:
        gated_skills = {
            path.parent.name
            for path in SKILLS_ROOT.glob("*/SKILL.md")
            if "### 最終runtime evidence gate" in path.read_text(encoding="utf-8")
        }
        self.assertEqual(gated_skills, set(FINAL_RUNTIME_EVIDENCE_POLICIES))

        for skill, expected_policy in FINAL_RUNTIME_EVIDENCE_POLICIES.items():
            with self.subTest(skill=skill):
                skill_root = SKILLS_ROOT / skill
                manifest = json.loads(
                    (skill_root / "evals/output/evals.json").read_text(encoding="utf-8")
                )
                self.assertEqual(
                    manifest.get("skill_runtime_verification"),
                    expected_policy,
                )
                self.assertTrue((skill_root / "scripts/runtime_contract.py").is_file())


if __name__ == "__main__":
    unittest.main()
