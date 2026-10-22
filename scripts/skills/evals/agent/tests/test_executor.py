from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

from scripts.skills.evals.agent.executor import run_command


class ExecutorTests(unittest.TestCase):
    def test_fake_agent_process_captures_stdout_and_sanitized_stderr(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            result = run_command(
                [
                    sys.executable,
                    "-c",
                    "import sys; print('candidate output'); print('Bearer abcdefghijklmnopqrstuv', file=sys.stderr)",
                ],
                input_text="prompt",
                cwd=Path(temporary),
                timeout_seconds=5,
            )
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(result.stdout.strip(), "candidate output")
        self.assertEqual(result.stderr_status, "sanitized")
        self.assertNotIn("abcdefghijklmnopqrstuv", result.stderr or "")

    def test_timeout_stops_a_fake_agent_process(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            result = run_command(
                [sys.executable, "-c", "import time; time.sleep(60)"],
                input_text="prompt",
                cwd=Path(temporary),
                timeout_seconds=1,
            )
        self.assertTrue(result.timed_out)
        self.assertNotEqual(result.exit_code, 0)


if __name__ == "__main__":
    unittest.main()
