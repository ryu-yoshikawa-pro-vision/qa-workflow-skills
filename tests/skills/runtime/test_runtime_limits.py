from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import unittest


REPO_ROOT = Path(__file__).resolve().parents[3]
RUNTIME_CONTRACT = REPO_ROOT / "skills" / "test-condition-design" / "scripts" / "runtime_contract.py"
AGGREGATE_LIMIT = 16 * 1024 * 1024


def _raw_request(artifact: str, normalized: dict | None = None) -> bytes:
    request = {
        "operation": "verify_runtime_evidence",
        "skill": "test-condition-design",
        "normalized_skill_input": normalized or {},
        "artifact_markdown": artifact,
        "previous_artifact_markdown": None,
        "partial_rerun": False,
    }
    return json.dumps(request, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def _boundary_raw(extra: int) -> bytes:
    # A single JSON string is capped at 64 KiB.  Fill the aggregate request
    # with several bounded strings, then use two bounded strings to hit the
    # exact byte boundary without weakening the per-string contract.
    # The runtime scanner counts the closing quote as part of the bounded
    # token, so 64 KiB of payload is represented by 64 KiB - 1 characters.
    max_string_payload = (64 * 1024) - 1
    full = "x" * max_string_payload
    normalized = {"padding": [full] * 254 + [""]}
    base = _raw_request("", normalized)
    remaining = AGGREGATE_LIMIT + extra - len(base)
    tail = min(max_string_payload, max(0, remaining))
    artifact_length = remaining - tail
    if artifact_length > max_string_payload:
        raise AssertionError("boundary fixture exceeds per-string limit")
    normalized["padding"][-1] = "x" * tail
    return _raw_request("x" * artifact_length, normalized)


class RuntimeAggregateLimitTests(unittest.TestCase):
    def _run(self, raw: bytes) -> dict:
        result = subprocess.run(
            [sys.executable, str(RUNTIME_CONTRACT)],
            input=raw,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=REPO_ROOT,
            check=False,
        )
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stderr, b"")
        return json.loads(result.stdout)

    def test_exact_aggregate_boundary_is_decoded(self) -> None:
        raw = _boundary_raw(0)
        self.assertEqual(len(raw), AGGREGATE_LIMIT)
        result = self._run(raw)
        self.assertNotIn("limit_exceeded", {issue.get("issue_type") for issue in result["issues"]})

    def test_one_byte_over_aggregate_boundary_is_blocked(self) -> None:
        raw = _boundary_raw(1)
        self.assertEqual(len(raw), AGGREGATE_LIMIT + 1)
        result = self._run(raw)
        self.assertEqual(result["issues"][0]["issue_type"], "limit_exceeded")


if __name__ == "__main__":
    unittest.main()
