"""Regression tests for repository-level GitHub security configuration."""

import re
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


class GitHubActionsLoader(yaml.SafeLoader):
    """Keep YAML 1.1's `on` scalar as a string while parsing numbers normally."""

    yaml_implicit_resolvers = {
        initial: [
            (tag, pattern)
            for tag, pattern in resolvers
            if tag != "tag:yaml.org,2002:bool"
        ]
        for initial, resolvers in yaml.SafeLoader.yaml_implicit_resolvers.items()
    }


GitHubActionsLoader.add_implicit_resolver(
    "tag:yaml.org,2002:bool",
    re.compile(r"^(?:true|false)$", re.IGNORECASE),
    list("tTfF"),
)


def load_yaml(path: Path) -> object:
    """Parse GitHub YAML with `on` as a string and native scalar types."""
    return yaml.load(path.read_text(encoding="utf-8"), Loader=GitHubActionsLoader)


class CiSecurityContractTests(unittest.TestCase):
    def test_every_workflow_declares_read_only_contents_permissions(self) -> None:
        workflow_root = ROOT / ".github" / "workflows"
        workflow_paths = sorted(
            (*workflow_root.glob("*.yml"), *workflow_root.glob("*.yaml"))
        )
        self.assertTrue(workflow_paths, "no GitHub Actions workflows found")

        for workflow_path in workflow_paths:
            with self.subTest(workflow=workflow_path.name):
                workflow = load_yaml(workflow_path)
                self.assertIsInstance(workflow, dict)
                self.assertIn("on", workflow)
                self.assertEqual(workflow.get("permissions"), {"contents": "read"})

                jobs = workflow.get("jobs")
                self.assertIsInstance(jobs, dict)
                for job_id, job in jobs.items():
                    with self.subTest(workflow=workflow_path.name, job=job_id):
                        self.assertNotIn("permissions", job)

    def test_dependabot_updates_actions_and_pip_without_version_prs(self) -> None:
        config = load_yaml(ROOT / ".github" / "dependabot.yml")
        self.assertIsInstance(config, dict)
        self.assertEqual(config.get("version"), 2)

        updates = config.get("updates")
        self.assertIsInstance(updates, list)
        self.assertEqual(
            [update.get("package-ecosystem") for update in updates],
            ["github-actions", "pip"],
        )

        expected_keys = {
            "package-ecosystem",
            "directory",
            "schedule",
            "open-pull-requests-limit",
        }
        for update in updates:
            with self.subTest(ecosystem=update.get("package-ecosystem")):
                self.assertEqual(set(update), expected_keys)
                self.assertEqual(update.get("directory"), "/")
                self.assertEqual(update.get("schedule"), {"interval": "weekly"})
                self.assertIs(type(update.get("open-pull-requests-limit")), int)
                self.assertEqual(update.get("open-pull-requests-limit"), 0)


if __name__ == "__main__":
    unittest.main()
