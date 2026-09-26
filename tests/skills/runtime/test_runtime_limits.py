from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import unittest


REPO_ROOT = Path(__file__).resolve().parents[3]
RUNTIME_CONTRACT = REPO_ROOT / "skills" / "test-condition-design" / "scripts" / "runtime_contract.py"
AGGREGATE_LIMIT = 16 * 1024 * 1024


def _raw_request(
    artifact: str,
    normalized: dict | None = None,
    *,
    previous: str | None = None,
    partial: bool = False,
    skill: str = "test-condition-design",
) -> bytes:
    request = {
        "operation": "verify_runtime_evidence",
        "skill": skill,
        "normalized_skill_input": normalized or {},
        "artifact_markdown": artifact,
        "previous_artifact_markdown": previous,
        "partial_rerun": partial,
    }
    return json.dumps(request, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def _boundary_raw(extra: int) -> bytes:
    # Exercise the actual production transport: artifact_markdown itself is
    # the large top-level string, while the serialized request hits the limit.
    base = _raw_request("")
    remaining = AGGREGATE_LIMIT + extra - len(base)
    if remaining < 0:
        raise AssertionError("base request exceeds aggregate boundary")
    return _raw_request("x" * remaining)


class RuntimeAggregateLimitTests(unittest.TestCase):
    def _run(self, raw: bytes, script: Path = RUNTIME_CONTRACT) -> dict:
        result = subprocess.run(
            [sys.executable, str(script)],
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

    def test_large_candidate_artifact_is_not_subject_to_string_limit(self) -> None:
        raw = _raw_request("x" * (64 * 1024 + 1))
        self.assertLess(len(raw), AGGREGATE_LIMIT)
        result = self._run(raw)
        self.assertNotIn("limit_exceeded", {issue.get("issue_type") for issue in result["issues"]})

    def test_large_previous_artifact_is_not_subject_to_string_limit(self) -> None:
        raw = _raw_request("", previous="x" * (64 * 1024 + 1), partial=True)
        self.assertLess(len(raw), AGGREGATE_LIMIT)
        result = self._run(raw)
        self.assertNotIn("limit_exceeded", {issue.get("issue_type") for issue in result["issues"]})

    def test_normalized_input_string_limit_remains_in_force(self) -> None:
        raw = _raw_request("small", {"large": "x" * (64 * 1024 + 1)})
        result = self._run(raw)
        self.assertEqual(result["issues"][0]["issue_type"], "limit_exceeded")

    def test_nested_artifact_named_string_is_not_exempt(self) -> None:
        raw = _raw_request("small", {"nested": {"artifact_markdown": "x" * (64 * 1024 + 1)}})
        result = self._run(raw)
        self.assertEqual(result["issues"][0]["issue_type"], "limit_exceeded")

    def test_other_top_level_string_is_not_exempt(self) -> None:
        raw = _raw_request("small", skill="x" * (64 * 1024 + 1))
        result = self._run(raw)
        self.assertEqual(result["issues"][0]["issue_type"], "limit_exceeded")

    def test_artifact_named_field_is_not_exempt_for_other_operations(self) -> None:
        raw = json.dumps(
            {
                "operation": "not_verify_runtime_evidence",
                "artifact_markdown": "x" * (64 * 1024 + 1),
            },
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
        result = self._run(raw)
        self.assertEqual(result["issues"][0]["issue_type"], "limit_exceeded")

    def test_normal_generator_string_limit_remains_in_force(self) -> None:
        generator = REPO_ROOT / "skills" / "test-condition-design" / "scripts" / "equivalence_partitions.py"
        raw = json.dumps(
            {"metadata": {}, "input": {"large": "x" * (64 * 1024 + 1)}},
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
        result = self._run(raw, generator)
        self.assertEqual(result["runtime_status"], "limit_exceeded")


if __name__ == "__main__":
    unittest.main()
