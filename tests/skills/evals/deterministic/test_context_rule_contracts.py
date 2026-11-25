"""Repository fixtures stay valid under the production context contract helper."""

from __future__ import annotations

import hashlib
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from scripts import context_artifacts  # noqa: E402
from scripts.skills.evals.deterministic.loader import load_validator  # noqa: E402


def load_example(skill: str, name: str) -> dict:
    path = ROOT / "skills" / skill / "assets" / name
    return json.loads(path.read_text(encoding="utf-8"))


class ContextRuleContractFixtureTests(unittest.TestCase):
    def test_skill_assets_validate_and_round_trip_canonically(self) -> None:
        examples = (
            ("context-signal-audit", "batch-example.json", "context-signal-batch"),
            (
                "context-rule-synthesis",
                "candidate-example.json",
                "context-rule-candidate",
            ),
            ("context-rule-synthesis", "run-example.json", "context-synthesis-run"),
        )
        for skill, filename, kind in examples:
            with self.subTest(skill=skill, filename=filename):
                artifact = load_example(skill, filename)
                self.assertEqual(
                    context_artifacts.validate_artifact(artifact, kind),
                    artifact,
                )
                encoded = context_artifacts.canonical_bytes(artifact)
                self.assertEqual(
                    context_artifacts.parse_canonical_json(encoded), artifact
                )

    def test_run_fixture_keeps_request_scope_single_source_of_identity(self) -> None:
        run = load_example("context-rule-synthesis", "run-example.json")
        operation_input = run["operation_input"]
        self.assertNotIn("requested_scope", operation_input)
        identity = context_artifacts.workflow_operation_id(
            run["workflow_ref"], operation_input, run["requested_scope"]
        )
        self.assertEqual(run["workflow_operation_id"], identity)
        self.assertEqual(run["run_identity"], context_artifacts.run_identity(identity))

    def test_zero_change_run_needs_exact_provider_readback(self) -> None:
        run = load_example("context-rule-synthesis", "run-example.json")
        source_content = "Example payment refund specification.\n"
        source_hash = hashlib.sha256(source_content.encode("utf-8")).hexdigest()
        source = run["operation_input"]["input_sources"][0]
        source["content_hash"] = source_hash
        snapshot_source = run["snapshot"]["referenced_sources"][0]
        snapshot_source["content_hash"] = source_hash
        run["snapshot"]["snapshot_hash"] = context_artifacts.snapshot_hash(
            run["snapshot"]
        )
        operation_id = context_artifacts.workflow_operation_id(
            run["workflow_ref"], run["operation_input"], run["requested_scope"]
        )
        run["workflow_operation_id"] = operation_id
        run["run_identity"] = context_artifacts.run_identity(operation_id)
        run["artifact_ref"] = context_artifacts.artifact_ref(
            "context-synthesis-run", run["run_identity"]
        )
        content = context_artifacts.canonical_bytes(run).decode("utf-8")
        digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
        source_readback = {
            "kind": "spec",
            "root_binding": "fixture-root:context-artifacts",
            "artifact_ref": source["artifact_ref"],
            "revision": source["source_revision"],
            "sha256": source_hash,
            "content": source_content,
        }
        readback = {
            "kind": "context-synthesis-run",
            "root_binding": "fixture-root:context-artifacts",
            "artifact_ref": run["artifact_ref"],
            "revision": "fixture:revision-1",
            "sha256": digest,
            "content": content,
        }
        verified = context_artifacts.completion_check(
            run,
            root_binding="fixture-root:context-artifacts",
            provider_readbacks=[source_readback, readback],
            run_readback_revision="fixture:revision-1",
        )
        self.assertTrue(verified["complete"], verified)
        altered = dict(readback, sha256="0" * 64)
        rejected = context_artifacts.completion_check(
            run,
            root_binding="fixture-root:context-artifacts",
            provider_readbacks=[source_readback, altered],
            run_readback_revision="fixture:revision-1",
        )
        self.assertFalse(rejected["complete"], rejected)

    def test_skill_local_output_validators_use_the_owner_contract(self) -> None:
        examples = (
            (
                "context-signal-audit",
                "batch-example.json",
                "context-signal-batch",
                "CSA-OUT-001",
            ),
            (
                "context-rule-synthesis",
                "run-example.json",
                "context-synthesis-run",
                "CRS-OUT-001",
            ),
        )
        for skill, filename, kind, eval_id in examples:
            with self.subTest(skill=skill):
                artifact = load_example(skill, filename)
                text = (
                    "```json\n"
                    + context_artifacts.canonical_bytes(artifact).decode("utf-8")
                    + "\n```"
                )
                expected = {"kind": kind}
                result = load_validator(skill)(text, expected, eval_id)
                self.assertEqual(result.to_dict()["status"], "pass")
                rejected = load_validator(skill)("```json\n{}\n```", expected, eval_id)
                self.assertEqual(rejected.to_dict()["status"], "fail")


if __name__ == "__main__":
    unittest.main()
