from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest


REPO_ROOT = Path(__file__).resolve().parents[3]
SKILLS = (
    "spec-analysis",
    "test-analysis",
    "test-requirement-design",
    "test-condition-design",
    "test-case-design",
    "coverage-analysis",
    "qa-workflow",
)


class RuntimeDispatchTests(unittest.TestCase):
    def test_skill_local_runtime_contracts_are_identical_and_lf_normalized(self) -> None:
        paths = [REPO_ROOT / "skills" / skill / "scripts" / "runtime_contract.py" for skill in SKILLS]
        raw = [path.read_bytes() for path in paths]
        self.assertTrue(all(b"\r" not in content for content in raw))
        self.assertEqual(len({hashlib.sha256(content).hexdigest() for content in raw}), 1)

    def test_all_runtime_scripts_compile(self) -> None:
        scripts = [
            path
            for skill in SKILLS
            for path in (REPO_ROOT / "skills" / skill / "scripts").glob("*.py")
        ]
        self.assertTrue(scripts)
        completed = subprocess.run(
            [sys.executable, "-m", "py_compile", *(str(path) for path in scripts)],
            cwd=REPO_ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr.decode())

    def test_spec_authority_machine_entity_cli_is_standalone(self) -> None:
        script = REPO_ROOT / "skills" / "spec-analysis" / "scripts" / "authority_entities.py"
        request = {
            "authorities": [{
                "authority_id": "SPEC-001",
                "authority_type": "SPEC",
                "active_content": {"title": "保存"},
                "scope": "保存API",
                "source_refs": ["SRC-001"],
                "relations": [],
                "related_authority_refs": [],
            }],
        }
        completed = subprocess.run(
            [sys.executable, str(script)],
            input=json.dumps(request, ensure_ascii=False).encode("utf-8"),
            cwd=REPO_ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr.decode())
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["expected_entity_identities"], [{"skill": "spec-analysis", "entity_type": "authority", "entity_ref": "SPEC-001"}])
        self.assertEqual(payload["entities"][0]["content"]["active_content"], {"title": "保存"})


if __name__ == "__main__":
    unittest.main()
