from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

from tests.skills.runtime.test_ep_runtime import metadata


ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "skills/test-condition-design/scripts/equivalence_partitions.py"
FIXTURE = ROOT / "tests/skills/runtime/fixtures/equivalence_partitions/valid_minimal.json"


class RuntimeDeterminismTests(unittest.TestCase):
    def test_hash_seed_does_not_change_cli_bytes(self) -> None:
        request = json.dumps({"metadata": metadata(), "input": json.loads(FIXTURE.read_text(encoding="utf-8"))}, ensure_ascii=False).encode("utf-8")
        outputs = []
        for seed in ("1", "999"):
            env = dict(os.environ)
            env["PYTHONHASHSEED"] = seed
            result = subprocess.run([sys.executable, str(SCRIPT)], input=request, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=ROOT, env=env, check=False)
            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stderr, b"")
            outputs.append(result.stdout)
        self.assertEqual(outputs[0], outputs[1])


if __name__ == "__main__":
    unittest.main()
