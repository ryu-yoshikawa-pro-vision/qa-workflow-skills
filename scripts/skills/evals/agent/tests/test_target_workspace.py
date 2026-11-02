from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.skills.evals.agent.common import AgentEvalError
from scripts.skills.evals.agent.target_workspace import (
    _scan_workspace,
    prepare_sanitized_target,
    verify_workspace_unchanged,
)


class TargetWorkspaceTests(unittest.TestCase):
    def _init_repo(self, root: Path, files: dict[str, str]) -> str:
        root.mkdir(parents=True, exist_ok=True)
        env = {
            **os.environ,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_AUTHOR_NAME": "Evaluator",
            "GIT_AUTHOR_EMAIL": "evaluator@invalid.local",
            "GIT_COMMITTER_NAME": "Evaluator",
            "GIT_COMMITTER_EMAIL": "evaluator@invalid.local",
        }
        subprocess.run(
            ["git", "init", "--quiet", str(root)],
            check=True,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
        )
        for relative, content in files.items():
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        subprocess.run(
            ["git", "-C", str(root), "add", "--all"],
            check=True,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
        )
        subprocess.run(
            ["git", "-C", str(root), "commit", "--quiet", "-m", "baseline"],
            check=True,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
        )
        result = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            check=True,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            env=env,
        )
        return result.stdout.strip()

    def test_target_integrity_requires_own_git_root_and_expected_baseline(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "target"
            expected_head = self._init_repo(root, {"spec.md": "fixed spec\n"})
            baseline = _scan_workspace(root)

            valid = verify_workspace_unchanged(
                root,
                baseline,
                expected_synthetic_baseline_revision=expected_head,
            )
            wrong_head = verify_workspace_unchanged(
                root,
                baseline,
                expected_synthetic_baseline_revision="0" * 40,
            )

        self.assertTrue(valid["unchanged"])
        self.assertTrue(valid["repository_root_matches_target"])
        self.assertTrue(valid["synthetic_baseline_matches"])
        self.assertFalse(wrong_head["unchanged"])
        self.assertFalse(wrong_head["synthetic_baseline_matches"])
        self.assertIn("synthetic_baseline_revision_mismatch", wrong_head["blockers"])

    def test_parent_git_discovery_is_not_accepted_as_target_integrity(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary) / "parent"
            self._init_repo(parent, {"nested-target/spec.md": "fixed spec\n"})
            target = parent / "nested-target"
            baseline = _scan_workspace(target)

            result = verify_workspace_unchanged(
                target,
                baseline,
                expected_synthetic_baseline_revision="1" * 40,
            )

        self.assertFalse(result["unchanged"])
        self.assertFalse(result["local_git_metadata_valid"])
        self.assertFalse(result["repository_root_matches_target"])
        self.assertEqual(result["repository_root"], str(parent.resolve()))
        self.assertIn("git_repository_root_does_not_match_target", result["blockers"])

    def test_workspace_scan_detects_tracked_untracked_and_ignored_changes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "target"
            expected_head = self._init_repo(
                root,
                {".gitignore": "*.pyc\n", "spec.md": "fixed spec\n"},
            )
            baseline = _scan_workspace(root)
            (root / "spec.md").write_text("changed spec\n", encoding="utf-8")
            (root / "untracked.md").write_text("new file\n", encoding="utf-8")
            ignored = root / "cache" / "generated.pyc"
            ignored.parent.mkdir()
            ignored.write_bytes(b"bytecode")

            result = verify_workspace_unchanged(
                root,
                baseline,
                expected_synthetic_baseline_revision=expected_head,
            )

        self.assertFalse(result["unchanged"])
        self.assertEqual(
            set(result["changed_paths"]),
            {"spec.md", "untracked.md", "cache/generated.pyc"},
        )

    def test_scan_rejects_symlink_roots_and_nonregular_entries(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "target"
            root.mkdir()
            link = Path(temporary) / "target-link"
            link.symlink_to(root, target_is_directory=True)
            with self.assertRaisesRegex(AgentEvalError, "real directory"):
                _scan_workspace(link)

            if hasattr(os, "mkfifo"):
                os.mkfifo(root / "named-pipe")
                with self.assertRaisesRegex(
                    AgentEvalError, "non-regular filesystem entry"
                ):
                    _scan_workspace(root)

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "target"
            root.mkdir()
            outside = Path(temporary) / "outside"
            outside.mkdir()
            (root / ".qa-eval-output").symlink_to(outside, target_is_directory=True)
            with self.assertRaisesRegex(AgentEvalError, "Agent output root"):
                _scan_workspace(root)

    def test_sanitized_target_destination_cannot_be_a_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            outside = root / "outside"
            outside.mkdir()
            destination = root / "target"
            destination.symlink_to(outside, target_is_directory=True)

            with self.assertRaisesRegex(AgentEvalError, "must not be a symlink"):
                prepare_sanitized_target(
                    source_root=root / "missing-source",
                    source_revision="1" * 40,
                    candidate_skills_root=root / "missing-skills",
                    verifier_capture_source=root / "missing-verifier.py",
                    destination=destination,
                )

            self.assertEqual(list(outside.iterdir()), [])

    def test_preparation_exposes_fixed_source_and_distinct_synthetic_baseline(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            source_revision = self._init_repo(
                source,
                {
                    "docs/spec/README.md": "Normative specification index.\n",
                    "docs/spec/features/checkout-and-payment.md": (
                        "Checkout specification.\n"
                    ),
                },
            )
            candidate_skills = root / "candidate-skills"
            (candidate_skills / "qa-workflow").mkdir(parents=True)
            (candidate_skills / "qa-workflow/SKILL.md").write_text(
                "# qa-workflow\n", encoding="utf-8"
            )
            verifier = root / "verifier_capture.py"
            verifier.write_text("# verifier helper\n", encoding="utf-8")
            target = root / "attempt" / "target"

            prepared = prepare_sanitized_target(
                source_root=source,
                source_revision=source_revision,
                candidate_skills_root=candidate_skills,
                verifier_capture_source=verifier,
                destination=target,
            )
            integrity = verify_workspace_unchanged(
                target,
                prepared["baseline_manifest"],
                expected_synthetic_baseline_revision=prepared[
                    "synthetic_baseline_revision"
                ],
            )
            instructions = (target / "AGENTS.md").read_text(encoding="utf-8")
            validator_exists = (
                target / ".qa-eval-tools" / "validate_artifact_index.py"
            ).is_file()
            public_contract = json.loads(
                (
                    target
                    / ".qa-eval-tools"
                    / "artifact-index-contract.json"
                ).read_text(encoding="utf-8")
            )

        self.assertEqual(prepared["source_revision"], source_revision)
        self.assertNotEqual(prepared["synthetic_baseline_revision"], source_revision)
        self.assertIn(source_revision, instructions)
        self.assertIn("合成1-commit baseline", instructions)
        self.assertIn("PYTHONDONTWRITEBYTECODE=1 python -B", instructions)
        self.assertIn("validate_artifact_index.py", instructions)
        self.assertIn("artifact-index-contract.json", instructions)
        self.assertTrue(validator_exists)
        self.assertEqual(public_contract["schema_version"], 1)
        self.assertEqual(
            len(public_contract["required_artifacts"]),
            8,
        )
        self.assertNotIn("rubric", public_contract)
        self.assertNotIn("expected", public_contract)
        self.assertTrue(integrity["unchanged"])
        self.assertTrue(integrity["synthetic_baseline_matches"])


if __name__ == "__main__":
    unittest.main()
