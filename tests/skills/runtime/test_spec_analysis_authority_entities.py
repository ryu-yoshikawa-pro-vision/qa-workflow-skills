from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[3]


class SpecAnalysisAuthorityEntityTests(unittest.TestCase):
    def test_empty_authority_snapshot_is_machine_readable(self) -> None:
        script = ROOT / "skills/spec-analysis/scripts/authority_entities.py"
        result = subprocess.run([sys.executable, str(script)], input=b'{"authorities":[]}', stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=ROOT, check=False)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stderr, b"")
        self.assertEqual(json.loads(result.stdout)["expected_entity_identities"], [])


if __name__ == "__main__":
    unittest.main()
