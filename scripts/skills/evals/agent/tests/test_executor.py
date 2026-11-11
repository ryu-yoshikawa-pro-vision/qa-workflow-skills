from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

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

    @unittest.skipUnless(
        os.name == "posix" and Path("/proc/self/fd").is_dir(),
        "requires a POSIX procfs file descriptor view",
    )
    def test_run_command_does_not_inherit_an_unlisted_open_descriptor(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            sentinel = root / "outside-sentinel.txt"
            sentinel.write_text("synthetic-outside-fd-v1\n", encoding="utf-8")
            descriptor = os.open(sentinel, os.O_RDONLY)
            os.set_inheritable(descriptor, True)
            descriptor_is_inheritable = os.get_inheritable(descriptor)
            child = """\
import json, os, sys
descriptor = int(sys.argv[1])
result = {"stdin": sys.stdin.read(), "stdio": {}, "proc": None, "dev": None}
for name, path in (("proc", f"/proc/self/fd/{descriptor}"), ("dev", f"/dev/fd/{descriptor}")):
    try:
        with open(path, "r", encoding="utf-8") as stream:
            value = stream.read()
        result[name] = {"readable": True, "marker": "synthetic-outside-fd-v1" in value}
    except OSError as exc:
        result[name] = {"readable": False, "error": type(exc).__name__}
for number in (0, 1, 2):
    result["stdio"][str(number)] = os.readlink(f"/proc/self/fd/{number}")
print(json.dumps(result, sort_keys=True))
"""
            clean_env = {
                "PATH": os.environ.get("PATH", ""),
                "HOME": temporary,
                "TMPDIR": temporary,
                "LC_ALL": "C",
            }
            try:
                with patch.dict(os.environ, clean_env, clear=True):
                    result = run_command(
                        [sys.executable, "-I", "-S", "-c", child, str(descriptor)],
                        input_text="synthetic-stdin-pipe-v1",
                        cwd=root,
                        timeout_seconds=5,
                    )
            finally:
                os.close(descriptor)

        child_result = json.loads(result.stdout)
        self.assertEqual(result.exit_code, 0)
        self.assertTrue(descriptor_is_inheritable)
        self.assertEqual(child_result["stdin"], "synthetic-stdin-pipe-v1")
        self.assertFalse(child_result["proc"]["readable"])
        self.assertFalse(child_result["dev"]["readable"])
        self.assertTrue(
            all("pipe:[" in child_result["stdio"][str(fd)] for fd in (0, 1, 2))
        )

    @unittest.skipUnless(os.name == "nt", "verifies Windows timeout temp cleanup")
    def test_timeout_termination_cleans_a_temporary_auth_home(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            ready_path = root / "temporary-home-path.txt"
            child = """\
import os, tempfile, time
from pathlib import Path
with tempfile.TemporaryDirectory(prefix="agent-eval-codex-home-timeout-") as home:
    path = Path(home)
    (path / "auth.json").write_text("SYNTHETIC_CREDENTIAL_MARKER", encoding="utf-8")
    Path(os.environ["PR17_TEMP_HOME_READY"]).write_text(str(path), encoding="utf-8")
    time.sleep(30)
"""
            child_env = {
                "PATH": os.environ.get("PATH", ""),
                "HOME": temporary,
                "TMPDIR": temporary,
                "TEMP": temporary,
                "TMP": temporary,
                "PR17_TEMP_HOME_READY": str(ready_path),
            }
            for name in ("SystemRoot", "WINDIR", "COMSPEC", "PATHEXT", "SystemDrive"):
                value = os.environ.get(name)
                if value:
                    child_env[name] = value
            with patch.dict(os.environ, child_env, clear=True):
                result = run_command(
                    [sys.executable, "-c", child],
                    input_text="synthetic-timeout-input",
                    cwd=root,
                    timeout_seconds=5,
                )

            self.assertTrue(result.timed_out)
            self.assertTrue(ready_path.is_file(), result.stderr or result.stdout)
            temporary_home = Path(ready_path.read_text(encoding="utf-8"))
            self.assertTrue(temporary_home.parent.name.startswith("qa-agent-eval-"))
            self.assertFalse(temporary_home.exists())

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
