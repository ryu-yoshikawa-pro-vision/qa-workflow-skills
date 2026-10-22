from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

from scripts.skills.evals.agent.judge_validation import load_fixture_catalogue
from scripts.skills.evals.agent.qa_training_store import load_scenario

REPO_ROOT = Path(__file__).resolve().parents[4]
AGENT_ROOT = REPO_ROOT / "scripts" / "skills" / "evals" / "agent"


class AgentEvaluationRepositoryContracts(unittest.TestCase):
    def test_fixed_qts_scenario_has_pinned_target_and_split_judge_fixtures(self) -> None:
        scenario = load_scenario()
        self.assertEqual(
            scenario["target_revision"],
            "84ce165493649550832731a60cf436f8ae29c56b",
        )
        self.assertEqual(
            scenario["target_repository"],
            "ryu-yoshikawa-pro-vision/qa-training-store",
        )
        self.assertEqual(scenario["scenario_id"], "qa-training-store-checkout-payment-web-v1")
        self.assertEqual(len(scenario["required_artifacts"]), len(set(
            (row["skill"], row["kind"], row["scope"])
            for row in scenario["required_artifacts"]
        )))

        catalogue = load_fixture_catalogue()
        tune = set(catalogue["splits"]["tune"])
        independent = set(catalogue["splits"]["independent"])
        fixture_ids = {row["id"] for row in catalogue["cases"]}
        self.assertFalse(tune & independent)
        self.assertEqual(tune | independent, fixture_ids)
        self.assertTrue(all(row["approval_status"].startswith("pending_") for row in catalogue["cases"]))

    def test_live_agent_results_are_git_ignored(self) -> None:
        result = subprocess.run(
            ["git", "check-ignore", "--quiet", ".agent-eval-runs/contract-test/result.json"],
            cwd=REPO_ROOT,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            check=False,
            shell=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr.decode("utf-8", errors="replace"))

    def test_agent_runner_does_not_invoke_git_or_pr_mutations(self) -> None:
        forbidden = ("git commit", "git push", "git switch", "git branch", "gh pr create")
        source = "\n".join(
            path.read_text(encoding="utf-8").lower()
            for path in AGENT_ROOT.rglob("*.py")
            if "tests" not in path.parts
        )
        for operation in forbidden:
            self.assertNotIn(operation, source)

    def test_standard_ci_runs_fake_contracts_without_live_agent_commands(self) -> None:
        workflow = (REPO_ROOT / ".github" / "workflows" / "deterministic-output-evals.yml").read_text(encoding="utf-8")
        self.assertIn("scripts/skills/evals/agent/tests", workflow)
        self.assertIn("tests/skills/evals/agent", workflow)
        self.assertIn("PyYAML==6.0.3", workflow)
        for live_invocation in ("codex exec", "--agent-command", "--judge-command", "qa_training_store \\"):
            self.assertNotIn(live_invocation, workflow)


if __name__ == "__main__":
    unittest.main()
