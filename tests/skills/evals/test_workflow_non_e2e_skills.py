"""New non-E2E Skill names remain valid in qa-workflow output evaluation."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

from scripts.skills.evals.deterministic.common import CANONICAL_SKILLS

ROOT = Path(__file__).resolve().parents[3]


class WorkflowNonE2ESkillsTests(unittest.TestCase):
    def test_both_skills_are_canonical_and_have_valid_status_rows(self):
        self.assertIn("testware-implementation", CANONICAL_SKILLS)
        self.assertIn("testware-execution", CANONICAL_SKILLS)
        filename = ROOT / "skills/qa-workflow/evals/deterministic/validator.py"
        spec = importlib.util.spec_from_file_location("qa_workflow_eval_test", filename)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        report = (
            "- ワークフロー全体状態: 未開始\n\n"
            "| Skill | 対象 / 実行範囲 | 状態 |\n"
            "| --- | --- | --- |\n"
            "| testware-implementation | | 未開始 |\n"
            "| testware-execution | | 未開始 |\n"
        )
        result = module.validate(report, {}, "new-non-e2e-skills")
        assertions = {item.id: item.status for item in result.assertions}
        self.assertEqual(assertions["WF-D002"], "pass")
        self.assertEqual(assertions["WF-D012"], "pass")
        self.assertEqual(assertions["WF-D016"], "pass")


if __name__ == "__main__":
    unittest.main()
