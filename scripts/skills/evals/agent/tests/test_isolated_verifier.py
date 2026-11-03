from __future__ import annotations

import ast
import errno
import hashlib
import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from scripts.skills.evals.agent import isolated_verifier
from scripts.skills.evals.agent.common import AgentEvalError


class IsolatedVerifierTests(unittest.TestCase):
    def _probe_or_skip(self) -> dict[str, object]:
        probe = isolated_verifier.probe_isolation()
        if probe.get("status") != "verified":
            if os.environ.get("PR17_REQUIRE_VERIFIER_ISOLATION") == "1":
                self.fail(f"Dockerless verifier isolation is required: {probe}")
            self.skipTest(f"isolation boundary unverified: {probe.get('reason')}")
        return probe

    def test_sealed_script_snapshot_cannot_be_written_after_creation(self) -> None:
        if not hasattr(os, "memfd_create"):
            self.skipTest("Linux sealed memfd is unavailable")
        descriptor = isolated_verifier._sealed_script_fd(b"fixed source")
        try:
            self.assertEqual(os.pread(descriptor, 64, 0), b"fixed source")
            with self.assertRaises(OSError):
                os.write(descriptor, b"changed")
        finally:
            os.close(descriptor)

    def test_verifier_source_hardlink_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "scripts"
            source.mkdir()
            source_file = source / "runtime_contract.py"
            source_file.write_text("print('{}')\n", encoding="utf-8")
            linked_file = root / "other-copy.py"
            os.link(source_file, linked_file)
            with self.assertRaisesRegex(
                AgentEvalError, "verifier source contains an unsafe file"
            ):
                isolated_verifier.source_tree_fingerprint(source)

    def test_verifier_source_directory_count_is_bounded(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "scripts"
            source.mkdir()
            for index in range(isolated_verifier.MAX_SOURCE_ENTRIES + 1):
                (source / f"empty-{index}").mkdir()

            with self.assertRaisesRegex(
                AgentEvalError, "verifier source tree exceeds the entry limit"
            ):
                isolated_verifier.source_tree_fingerprint(source)

    def test_probe_is_unverified_when_required_boundary_is_unavailable(self) -> None:
        with patch.object(isolated_verifier, "_host_tools", return_value=None):
            result = isolated_verifier.probe_isolation()
        self.assertEqual(result["status"], "evidence_unverified")
        self.assertFalse(result["candidate_executed"])

    def test_missing_bubblewrap_does_not_provide_host_tools(self) -> None:
        with patch.object(
            isolated_verifier.shutil,
            "which",
            return_value=None,
        ):
            self.assertIsNone(isolated_verifier._host_tools())

    def test_network_filter_covers_socket_io_uring_and_x32_syscalls(self) -> None:
        filter_bytes = isolated_verifier._network_seccomp_filter_bytes()
        self.assertEqual(len(filter_bytes) % 8, 0)
        self.assertIn(
            isolated_verifier._X32_SYSCALL_BIT.to_bytes(4, byteorder=sys.byteorder),
            filter_bytes,
        )
        for syscall_number in isolated_verifier._SECCOMP_BLOCKED_X86_64_SYSCALLS:
            self.assertIn(
                syscall_number.to_bytes(4, byteorder=sys.byteorder), filter_bytes
            )

    def test_network_filter_is_unavailable_outside_linux_x86_64(self) -> None:
        with (
            patch.object(isolated_verifier.sys, "platform", "darwin"),
            self.assertRaisesRegex(
                AgentEvalError, "network seccomp policy is unavailable"
            ),
        ):
            isolated_verifier._network_seccomp_filter_bytes()

    def test_nested_user_namespace_denial_requires_bwrap_assertion(self) -> None:
        self.assertTrue(
            isolated_verifier._nested_user_namespace_denied(-1, errno.EPERM, True)
        )
        self.assertTrue(
            isolated_verifier._nested_user_namespace_denied(-1, errno.ENOSPC, True)
        )
        self.assertFalse(
            isolated_verifier._nested_user_namespace_denied(-1, errno.ENOSPC, False)
        )
        self.assertFalse(
            isolated_verifier._nested_user_namespace_denied(0, 0, True)
        )
        self.assertFalse(
            isolated_verifier._nested_user_namespace_denied(-1, errno.EINVAL, True)
        )

    def test_synthetic_boundary_probe_script_is_valid_python(self) -> None:
        module = ast.parse(Path(isolated_verifier.__file__).read_text(encoding="utf-8"))
        probe_function = next(
            node
            for node in module.body
            if isinstance(node, ast.FunctionDef) and node.name == "probe_isolation"
        )
        script_assignment = next(
            node
            for node in ast.walk(probe_function)
            if isinstance(node, ast.Assign)
            and any(
                isinstance(target, ast.Name) and target.id == "script"
                for target in node.targets
            )
        )
        script = ast.literal_eval(script_assignment.value)
        compile(script, "<synthetic-boundary-probe>", "exec")

    def test_source_fingerprint_mismatch_stops_before_probe_or_execution(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "scripts"
            source.mkdir()
            (source / "runtime_contract.py").write_text(
                "raise RuntimeError('must not execute')\n", encoding="utf-8"
            )
            with patch.object(isolated_verifier, "probe_isolation") as probe:
                result = isolated_verifier.run_isolated_python(
                    source_dir=source,
                    script_name="runtime_contract.py",
                    request_bytes=b"{}\n",
                    expected_source_fingerprint="sha256:" + "0" * 64,
                )
            self.assertEqual(result["status"], "evidence_unverified")
            self.assertEqual(result["reason"], "candidate_source_fingerprint_mismatch")
            self.assertFalse(result["verifier_executed"])
            probe.assert_not_called()

    def test_request_size_limit_stops_before_probe(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "scripts"
            source.mkdir()
            (source / "runtime_contract.py").write_text(
                "raise RuntimeError('must not execute')\n", encoding="utf-8"
            )
            with patch.object(isolated_verifier, "probe_isolation") as probe:
                result = isolated_verifier.run_isolated_python(
                    source_dir=source,
                    script_name="runtime_contract.py",
                    request_bytes=b"x" * (isolated_verifier.MAX_REQUEST_BYTES + 1),
                )
            self.assertEqual(result["status"], "evidence_unverified")
            self.assertEqual(result["reason"], "request_exceeds_size_limit")
            self.assertFalse(result["verifier_executed"])
            probe.assert_not_called()

    def test_success_records_raw_output_hash_separately_from_parsed_json(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "scripts"
            source.mkdir()
            (source / "runtime_contract.py").write_text(
                "print('{}')\n", encoding="utf-8"
            )
            stdout = '{"valid":true}\n'
            raw_stdout_sha = (
                "sha256:" + hashlib.sha256(stdout.encode("utf-8")).hexdigest()
            )
            with (
                patch.object(
                    isolated_verifier,
                    "probe_isolation",
                    return_value={"status": "verified", "checks": {}},
                ),
                patch.object(
                    isolated_verifier,
                    "_host_tools",
                    return_value=(
                        Path("/usr/bin/bwrap"),
                        Path("/usr/bin/python3"),
                        {},
                    ),
                ),
                patch.object(
                    isolated_verifier,
                    "_run_bwrap",
                    return_value={
                        "status": "completed",
                        "stdout": stdout,
                        "stderr": "",
                        "stdout_sha256": raw_stdout_sha,
                        "stderr_sha256": "sha256:" + "0" * 64,
                        "source_fingerprint_before": isolated_verifier.source_tree_fingerprint(
                            source
                        ),
                        "source_fingerprint_after": isolated_verifier.source_tree_fingerprint(
                            source
                        ),
                        "verifier_executed": True,
                    },
                ),
            ):
                result = isolated_verifier.run_isolated_python(
                    source_dir=source,
                    script_name="runtime_contract.py",
                    request_bytes=b"{}\n",
                )
        self.assertEqual(result["status"], "verified")
        self.assertEqual(result["result_sha256"], raw_stdout_sha)
        self.assertEqual(
            result["parsed_result_sha256"],
            "sha256:" + hashlib.sha256(stdout.encode()).hexdigest(),
        )

    def test_duplicate_result_keys_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "scripts"
            source.mkdir()
            (source / "runtime_contract.py").write_text("pass\n", encoding="utf-8")
            stdout = '{"valid":true,"valid":false}\n'
            with (
                patch.object(
                    isolated_verifier,
                    "probe_isolation",
                    return_value={"status": "verified", "checks": {}},
                ),
                patch.object(
                    isolated_verifier,
                    "_host_tools",
                    return_value=(
                        Path("/usr/bin/bwrap"),
                        Path("/usr/bin/python3"),
                        {},
                    ),
                ),
                patch.object(
                    isolated_verifier,
                    "_run_bwrap",
                    return_value={
                        "status": "completed",
                        "stdout": stdout,
                        "stderr": "",
                        "stdout_sha256": "sha256:"
                        + hashlib.sha256(stdout.encode()).hexdigest(),
                        "stderr_sha256": "sha256:" + "0" * 64,
                        "source_fingerprint_before": isolated_verifier.source_tree_fingerprint(
                            source
                        ),
                        "source_fingerprint_after": isolated_verifier.source_tree_fingerprint(
                            source
                        ),
                        "verifier_executed": True,
                    },
                ),
            ):
                result = isolated_verifier.run_isolated_python(
                    source_dir=source,
                    script_name="runtime_contract.py",
                    request_bytes=b"{}\n",
                )

        self.assertEqual(result["status"], "execution_error")
        self.assertEqual(result["reason"], "invalid_verifier_json")
        self.assertNotIn("result", result)

    def test_nonzero_sandbox_exit_does_not_claim_verifier_execution(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "scripts"
            source.mkdir()
            (source / "runtime_contract.py").write_text(
                "print('{}')\n", encoding="utf-8"
            )
            with (
                patch.object(
                    isolated_verifier,
                    "probe_isolation",
                    return_value={"status": "verified", "checks": {}},
                ),
                patch.object(
                    isolated_verifier,
                    "_host_tools",
                    return_value=(
                        Path("/usr/bin/bwrap"),
                        Path("/usr/bin/python3"),
                        {},
                    ),
                ),
                patch.object(
                    isolated_verifier,
                    "_run_bwrap",
                    return_value={
                        "status": "execution_error",
                        "exit_code": 1,
                        "sandbox_process_started": True,
                        "verifier_executed": None,
                        "stdout": "",
                        "stderr": "bubblewrap setup failed",
                    },
                ),
            ):
                result = isolated_verifier.run_isolated_python(
                    source_dir=source,
                    script_name="runtime_contract.py",
                    request_bytes=b"{}\n",
                )

        self.assertEqual(result["status"], "execution_error")
        self.assertTrue(result["sandbox_process_started"])
        self.assertIsNone(result["verifier_executed"])

    def test_bwrap_exit_code_controls_verifier_execution_evidence(self) -> None:
        for exit_code, expected_execution in ((0, True), (1, None)):
            with (
                self.subTest(exit_code=exit_code),
                tempfile.TemporaryDirectory() as tmp,
            ):
                source = Path(tmp) / "scripts"
                source.mkdir()
                (source / "runtime_contract.py").write_text(
                    "print('{}')\n", encoding="utf-8"
                )
                process = Mock(returncode=exit_code, pid=12345)
                process.communicate.return_value = (b"", b"")
                observed_fds: dict[str, object] = {}

                def capture_spawn(*args: object, **kwargs: object) -> Mock:
                    self.assertTrue(args)
                    observed_fds["stdin"] = kwargs["stdin"]
                    observed_fds["stdout_is_regular"] = stat.S_ISREG(
                        os.fstat(kwargs["stdout"].fileno()).st_mode
                    )
                    observed_fds["stderr_is_regular"] = stat.S_ISREG(
                        os.fstat(kwargs["stderr"].fileno()).st_mode
                    )
                    observed_fds["passed_fds_are_regular"] = all(
                        stat.S_ISREG(os.fstat(descriptor).st_mode)
                        for descriptor in kwargs["pass_fds"]
                    )
                    return process

                with patch.object(
                    isolated_verifier.subprocess,
                    "Popen",
                    side_effect=capture_spawn,
                ) as popen:
                    result = isolated_verifier._run_bwrap(
                        bwrap=Path("/usr/bin/bwrap"),
                        python=Path("/usr/bin/python3"),
                        source_dir=source,
                        in_sandbox_source="/candidate",
                        script_name="runtime_contract.py",
                        inner_argv=[],
                        input_bytes=b"{}\n",
                        timeout_seconds=1,
                    )
                    command = popen.call_args.args[0]
                    self.assertEqual(command[0], "/usr/bin/bwrap")
                    self.assertIn("--seccomp", command)
                    self.assertIn("--disable-userns", command)
                    self.assertIn("--assert-userns-disabled", command)
                    self.assertNotIn("--unshare-net", command)
                    self.assertEqual(
                        command[
                            command.index("PWD") - 1 : command.index("PWD") + 2
                        ],
                        ["--setenv", "PWD", "/workspace"],
                    )
                    lib64_link_index = command.index("/lib64")
                    self.assertEqual(
                        command[lib64_link_index - 2 : lib64_link_index + 1],
                        ["--symlink", "usr/lib64", "/lib64"],
                    )
                    spawn_kwargs = popen.call_args.kwargs
                    self.assertTrue(spawn_kwargs["close_fds"])
                    self.assertEqual(
                        spawn_kwargs["env"], {"PATH": "/usr/bin:/bin", "LC_ALL": "C"}
                    )
                    self.assertEqual(observed_fds["stdin"], -1)
                    self.assertTrue(observed_fds["stdout_is_regular"])
                    self.assertTrue(observed_fds["stderr_is_regular"])
                    passed_descriptors = spawn_kwargs["pass_fds"]
                    self.assertEqual(len(passed_descriptors), 2)
                    self.assertTrue(observed_fds["passed_fds_are_regular"])

            self.assertTrue(result["sandbox_process_started"])
            self.assertEqual(result["verifier_executed"], expected_execution)
            self.assertEqual(
                result["bwrap_user_namespace_disable_assertion_passed"],
                expected_execution is True,
            )
            self.assertNotIn("candidate_executed", result)

    def test_missing_isolation_tool_never_executes_supplied_source(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "scripts"
            source.mkdir()
            marker = Path(temporary) / "candidate-executed"
            (source / "runtime_contract.py").write_text(
                f"from pathlib import Path\nPath({str(marker)!r}).write_text('ran')\n",
                encoding="utf-8",
            )
            with patch.object(isolated_verifier, "_host_tools", return_value=None):
                result = isolated_verifier.run_isolated_python(
                    source_dir=source,
                    script_name="runtime_contract.py",
                    request_bytes=b"{}\n",
                )
            self.assertEqual(result["status"], "evidence_unverified")
            self.assertFalse(result["verifier_executed"])
            self.assertFalse(marker.exists())

    def test_isolation_probe_checks_each_required_boundary(self) -> None:
        probe = self._probe_or_skip()
        self.assertEqual(probe["status"], "verified", probe)
        self.assertTrue(all(probe["checks"].values()), probe["checks"])

    def test_candidate_runs_only_after_the_isolation_probe_passes(self) -> None:
        self._probe_or_skip()
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "scripts"
            source.mkdir()
            (source / "runtime_contract.py").write_text(
                "import json, sys\n"
                "request = json.loads(sys.stdin.buffer.read())\n"
                "print(json.dumps({'valid': request['valid']}))\n",
                encoding="utf-8",
            )
            result = isolated_verifier.run_isolated_python(
                source_dir=source,
                script_name="runtime_contract.py",
                request_bytes=b'{"valid":true}\n',
                timeout_seconds=10,
            )
        self.assertEqual(result["status"], "verified", result)
        self.assertTrue(result["verifier_executed"])
        self.assertEqual(result["result"], {"valid": True})
        self.assertTrue(result["source_unchanged"])
        self.assertTrue(result["request_unchanged"])
        self.assertEqual(result["isolation_probe"]["status"], "verified")

    def test_timeout_is_not_a_pass_and_records_cleanup(self) -> None:
        self._probe_or_skip()
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "scripts"
            source.mkdir()
            (source / "runtime_contract.py").write_text(
                "import subprocess,sys,time\n"
                "subprocess.Popen([sys.executable, '-c', 'import time;time.sleep(30)'])\n"
                "time.sleep(30)\n",
                encoding="utf-8",
            )
            result = isolated_verifier.run_isolated_python(
                source_dir=source,
                script_name="runtime_contract.py",
                request_bytes=b"{}\n",
                timeout_seconds=1,
            )
        self.assertEqual(result["status"], "timeout", result)
        self.assertTrue(result["timeout_cleanup_verified"])
        self.assertNotIn("result", result)


if __name__ == "__main__":
    unittest.main()
