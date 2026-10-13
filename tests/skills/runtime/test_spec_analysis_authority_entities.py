from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


class SpecAnalysisAuthorityEntityTests(unittest.TestCase):
    def test_empty_authority_snapshot_is_machine_readable(self) -> None:
        script = ROOT / "skills/spec-analysis/scripts/authority_entities.py"
        result = subprocess.run(
            [sys.executable, str(script)],
            input=b'{"authorities":[]}',
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=ROOT,
            check=False,
        )
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stderr, b"")
        self.assertEqual(json.loads(result.stdout)["expected_entity_identities"], [])

    def _v1_artifact(self, *, dependency: bool = False) -> str:
        content = {
            "authority_id": "SPEC-001",
            "authority_type": "SPEC",
            "active_content": {"text": "approved"},
            "scope": None,
            "source_refs": ["SRC-001"],
            "relations": [],
            "related_authority_refs": [],
        }
        canonical = json.dumps(
            content, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        entity = {
            "schema_version": "entity-state-v1",
            "skill": "spec-analysis",
            "entity_type": "authority",
            "entity_ref": "SPEC-001",
            "model_key": None,
            "content": content,
            "content_fingerprint": "sha256:" + hashlib.sha256(canonical).hexdigest(),
            "upstream_entity_dependencies": [],
            "runtime_dependencies": [],
        }
        if dependency:
            entity["upstream_entity_dependencies"] = [
                {
                    "skill": "spec-analysis",
                    "entity_type": "authority",
                    "entity_ref": "SPEC-002",
                    "content_fingerprint": "sha256:" + "0" * 64,
                }
            ]
        wrapper = {
            "schema_version": "entity-state-v1",
            "skill": "spec-analysis",
            "entities": [entity],
        }
        return (
            "### Machine Entities: spec-analysis\n\n```json\n"
            + json.dumps(
                wrapper, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            )
            + "\n```\n"
        )

    def test_v1_source_artifact_projects_canonical_content_to_v2(self) -> None:
        script = ROOT / "skills/spec-analysis/scripts/authority_entities.py"
        request = json.dumps({"source_artifact_markdown": self._v1_artifact()}).encode()
        result = subprocess.run(
            [sys.executable, str(script)],
            input=request,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=ROOT,
            check=False,
        )
        self.assertEqual(result.returncode, 0)
        response = json.loads(result.stdout)
        self.assertEqual(response["entities"][0]["schema_version"], "entity-state-v2")
        self.assertEqual(response["entities"][0]["entity_ref"], "SPEC-001")

    def test_v1_source_with_dependency_is_rejected_without_fallback(self) -> None:
        script = ROOT / "skills/spec-analysis/scripts/authority_entities.py"
        request = json.dumps(
            {"source_artifact_markdown": self._v1_artifact(dependency=True)}
        ).encode()
        result = subprocess.run(
            [sys.executable, str(script)],
            input=request,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=ROOT,
            check=False,
        )
        self.assertEqual(result.returncode, 0)
        response = json.loads(result.stdout)
        self.assertFalse(response["valid"])
        self.assertEqual(response["entities"], [])


if __name__ == "__main__":
    unittest.main()
