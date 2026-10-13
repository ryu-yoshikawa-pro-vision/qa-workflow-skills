"""Windows PowerShell transport tests for the configured PreToolUse command."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import tomllib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
NODE = shutil.which("node")
CONFIG = tomllib.loads((ROOT / ".codex" / "config.toml").read_text(encoding="utf-8"))
WINDOWS_COMMAND = CONFIG["hooks"]["PreToolUse"][0]["hooks"][0]["command_windows"]
LAUNCHER = ROOT / ".codex" / "hooks" / "pre_tool_use_policy_windows.ps1"
HOOK = ROOT / ".codex" / "hooks" / "pre_tool_use_policy.mjs"


@unittest.skipUnless(os.name == "nt", "Windows PowerShell transport is Windows-only")
class WindowsLauncherTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.powershells = {
            "Windows PowerShell 5.1": shutil.which("powershell.exe"),
            "PowerShell 7": shutil.which("pwsh.exe") or shutil.which("pwsh"),
        }

    def test_both_powershell_versions_are_available(self) -> None:
        self.assertTrue(all(self.powershells.values()), self.powershells)
        versions = {}
        for name, executable in self.powershells.items():
            result = subprocess.run(
                [
                    executable,
                    "-NoProfile",
                    "-NonInteractive",
                    "-Command",
                    "$PSVersionTable.PSVersion.ToString()",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            version = result.stdout.strip()
            versions[name] = version
            if name == "Windows PowerShell 5.1":
                self.assertTrue(version.startswith("5.1."), version)
            else:
                self.assertTrue(version.startswith("7."), version)
        self.versions = versions

    def test_configured_command_is_quote_free_and_decodes_to_root_guard(self) -> None:
        self.assertRegex(
            WINDOWS_COMMAND,
            r"^powershell\.exe -NoProfile -NonInteractive -EncodedCommand [A-Za-z0-9+/=]+$",
        )
        self.assertNotIn('"', WINDOWS_COMMAND)
        encoded = WINDOWS_COMMAND.rsplit(" ", 1)[1]
        import base64

        payload = base64.b64decode(encoded).decode("utf-16-le")
        self.assertIn("git rev-parse --show-toplevel", payload)
        self.assertIn("unable to resolve repository root", payload)
        self.assertIn("Set-Location -LiteralPath $root -ErrorAction Stop", payload)
        self.assertIn("pre_tool_use_policy_windows.ps1", payload)

    def create_repository(self, parent: Path) -> Path:
        repo = parent / "repository with spaces"
        repo.mkdir()
        hook_dir = repo / ".codex" / "hooks"
        hook_dir.mkdir(parents=True)
        shutil.copy2(HOOK, hook_dir / HOOK.name)
        shutil.copy2(LAUNCHER, hook_dir / LAUNCHER.name)
        subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True)
        subprocess.run(
            ["git", "config", "user.name", "Launcher Test"], cwd=repo, check=True
        )
        subprocess.run(
            ["git", "config", "user.email", "launcher@example.invalid"],
            cwd=repo,
            check=True,
        )
        (repo / "tracked.txt").write_text("fixture\n", encoding="utf-8")
        subprocess.run(["git", "add", "tracked.txt"], cwd=repo, check=True)
        subprocess.run(["git", "commit", "-qm", "fixture"], cwd=repo, check=True)
        return repo

    def run_command(
        self,
        command: str,
        shell: str,
        cwd: Path,
        input_bytes: bytes,
        env,
        powershell: str,
    ):
        if shell == "cmd.exe /C":
            invocation = ["cmd.exe", "/d", "/c", command]
        else:
            invocation = [powershell, *command.split(" ")[1:]]
        return subprocess.run(
            invocation,
            cwd=cwd,
            input=input_bytes,
            capture_output=True,
            check=False,
            env=env,
        )

    def test_direct_and_cmd_launchers_preserve_raw_streams_for_both_powershells(
        self,
    ) -> None:
        if not NODE:
            self.fail("Node.js 24 must be available on PATH")
        with tempfile.TemporaryDirectory(
            prefix="launcher fixture with spaces "
        ) as directory:
            repo = self.create_repository(Path(directory))
            payloads = (
                json.dumps(
                    {"tool_name": "Bash", "tool_input": {"command": "git status"}}
                ).encode(),
                b"{malformed input",
            )
            base_env = os.environ.copy()
            for name, powershell in self.powershells.items():
                if not powershell:
                    self.fail(f"{name} is required for the Windows launcher contract")
                env = base_env.copy()
                env["PATH"] = str(Path(NODE).parent) + os.pathsep + env["PATH"]
                for input_bytes in payloads:
                    direct = subprocess.run(
                        [NODE, str(HOOK)],
                        cwd=repo,
                        input=input_bytes,
                        capture_output=True,
                        check=False,
                        env=env,
                    )
                    shells = (
                        ("direct", "cmd.exe /C")
                        if name == "Windows PowerShell 5.1"
                        else ("direct",)
                    )
                    for shell in shells:
                        with self.subTest(
                            powershell=name, shell=shell, input=input_bytes
                        ):
                            actual = self.run_command(
                                WINDOWS_COMMAND,
                                shell,
                                repo,
                                input_bytes,
                                env,
                                powershell,
                            )
                            details = (
                                f"{name} {shell}: expected exit={direct.returncode}, "
                                f"stderr={direct.stderr!r}; actual exit={actual.returncode}, "
                                f"stdout={actual.stdout!r}, stderr={actual.stderr!r}"
                            )
                            self.assertEqual(
                                actual.returncode, direct.returncode, details
                            )
                            self.assertEqual(actual.stdout, direct.stdout, details)
                            self.assertEqual(actual.stderr, direct.stderr, details)

    def test_configured_command_preserves_safe_deny_and_malformed_contracts(
        self,
    ) -> None:
        if not NODE:
            self.fail("Node.js 24 must be available on PATH")
        with tempfile.TemporaryDirectory(
            prefix="configured launcher fixture with spaces "
        ) as directory:
            repo = self.create_repository(Path(directory))
            env = os.environ.copy()
            env["PATH"] = str(Path(NODE).parent) + os.pathsep + env["PATH"]
            cases = (
                (
                    "safe read-only command",
                    json.dumps(
                        {"tool_name": "Bash", "tool_input": {"command": "git status"}}
                    ).encode(),
                    0,
                    "",
                    "",
                ),
                (
                    "opaque cmd wrapper is denied",
                    json.dumps(
                        {
                            "tool_name": "Bash",
                            "tool_input": {
                                "command": 'cmd.exe /d /c "echo hook-negative-marker"'
                            },
                        }
                    ).encode(),
                    0,
                    None,
                    "",
                ),
                ("malformed JSON fails with a diagnostic", b"{", 2, "", "invalid JSON"),
            )
            for name, payload, expected_exit, expected_stdout, expected_stderr in cases:
                for powershell_name, powershell in self.powershells.items():
                    if not powershell:
                        self.fail(
                            f"{powershell_name} is required for the launcher contract"
                        )
                    with self.subTest(case=name, powershell=powershell_name):
                        result = self.run_command(
                            WINDOWS_COMMAND, "direct", repo, payload, env, powershell
                        )
                        details = (
                            f"exit={result.returncode}, stdout={result.stdout!r}, "
                            f"stderr={result.stderr!r}"
                        )
                        self.assertEqual(result.returncode, expected_exit, details)
                        if expected_stdout is not None:
                            self.assertEqual(
                                result.stdout.decode(), expected_stdout, details
                            )
                        if expected_stderr:
                            self.assertIn(
                                expected_stderr.encode(), result.stderr, details
                            )
                        else:
                            self.assertEqual(result.stderr, b"", details)
                        if name == "opaque cmd wrapper is denied":
                            response = json.loads(result.stdout)
                            output = response["hookSpecificOutput"]
                            self.assertEqual(
                                output["permissionDecision"], "deny", details
                            )
                            self.assertIn(
                                "Nested shell wrappers",
                                output["permissionDecisionReason"],
                            )
                            self.assertNotIn(
                                b"hook-negative-marker", result.stdout + result.stderr
                            )

    def test_configured_command_forwards_node_streams_and_exit_code(self) -> None:
        with tempfile.TemporaryDirectory(
            prefix="launcher stream fixture with spaces "
        ) as directory:
            repo = self.create_repository(Path(directory))
            fixture_hook = repo / ".codex" / "hooks" / HOOK.name
            fixture_hook.write_text(
                'process.stdout.write("stdout-marker\\r\\n");\n'
                'process.stderr.write("stderr-marker\\r\\n");\n'
                "process.exitCode = 17;\n",
                encoding="utf-8",
            )
            env = os.environ.copy()
            if NODE:
                env["PATH"] = str(Path(NODE).parent) + os.pathsep + env["PATH"]
            for powershell_name, powershell in self.powershells.items():
                if not powershell:
                    self.fail(
                        f"{powershell_name} is required for the launcher contract"
                    )
                with self.subTest(powershell=powershell_name):
                    result = self.run_command(
                        WINDOWS_COMMAND,
                        "direct",
                        repo,
                        b"launcher stream fixture",
                        env,
                        powershell,
                    )
                    self.assertEqual(result.returncode, 17, result.stderr)
                    self.assertEqual(result.stdout, b"stdout-marker\r\n")
                    self.assertEqual(result.stderr, b"stderr-marker\r\n")

    def test_configured_command_preserves_node_exception_diagnostic(self) -> None:
        with tempfile.TemporaryDirectory(
            prefix="launcher exception fixture with spaces "
        ) as directory:
            repo = self.create_repository(Path(directory))
            fixture_hook = repo / ".codex" / "hooks" / HOOK.name
            fixture_hook.write_text(
                'throw new Error("fixture hook exception");\n', encoding="utf-8"
            )
            env = os.environ.copy()
            if NODE:
                env["PATH"] = str(Path(NODE).parent) + os.pathsep + env["PATH"]
            for powershell_name, powershell in self.powershells.items():
                if not powershell:
                    self.fail(
                        f"{powershell_name} is required for the launcher contract"
                    )
                with self.subTest(powershell=powershell_name):
                    result = self.run_command(
                        WINDOWS_COMMAND, "direct", repo, b"{}", env, powershell
                    )
                    self.assertEqual(result.returncode, 1, result.stderr)
                    self.assertEqual(result.stdout, b"")
                    self.assertIn(b"fixture hook exception", result.stderr)

    def test_missing_node_fails_with_launcher_diagnostic(self) -> None:
        git = shutil.which("git")
        self.assertTrue(git, "Git for Windows must be available")
        system_root = Path(os.environ["SystemRoot"])
        env = os.environ.copy()
        env["PATH"] = os.pathsep.join(
            (str(Path(git).parent), str(system_root / "System32"))
        )
        with tempfile.TemporaryDirectory(
            prefix="launcher missing node fixture "
        ) as directory:
            repo = self.create_repository(Path(directory))
            for powershell_name, powershell in self.powershells.items():
                if not powershell:
                    self.fail(
                        f"{powershell_name} is required for the launcher contract"
                    )
                with self.subTest(powershell=powershell_name):
                    result = self.run_command(
                        WINDOWS_COMMAND, "direct", repo, b"{}", env, powershell
                    )
                    self.assertEqual(result.returncode, 2, result.stderr)
                    self.assertEqual(result.stdout, b"")
                    self.assertIn(
                        b"Node executable was not found on PATH", result.stderr
                    )

    def test_invalid_repository_root_stops_before_launcher_or_git(
        self,
    ) -> None:
        if not NODE:
            self.fail("Node.js 24 must be available on PATH")
        with tempfile.TemporaryDirectory(prefix="launcher location fail ") as directory:
            base = Path(directory)
            repo = self.create_repository(base)
            head_before = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=repo
            )
            status_before = subprocess.check_output(
                ["git", "status", "--porcelain=v1"], cwd=repo
            )
            shim = base / "git-shim"
            shim.mkdir()
            log = base / "git-shim.log"
            invalid_root = base / "missing repository root"
            fake_git = shim / "git.cmd"
            fake_git.write_text(
                '@echo off\r\necho invoked>>"%FAKE_GIT_LOG%"\necho %FAKE_GIT_ROOT%\r\n',
                encoding="ascii",
            )
            for name, powershell in self.powershells.items():
                if not powershell:
                    self.fail(f"{name} is required for the Windows launcher contract")
                env = os.environ.copy()
                env["PATH"] = str(shim) + os.pathsep + env["PATH"]
                env["FAKE_GIT_LOG"] = str(log)
                env["FAKE_GIT_ROOT"] = str(invalid_root)
                shells = (
                    ("direct", "cmd.exe /C")
                    if name == "Windows PowerShell 5.1"
                    else ("direct",)
                )
                for shell in shells:
                    log.unlink(missing_ok=True)
                    with self.subTest(powershell=name, shell=shell):
                        result = self.run_command(
                            WINDOWS_COMMAND, shell, repo, b"{}", env, powershell
                        )
                        self.assertEqual(result.returncode, 2, result.stderr)
                        self.assertIn(
                            b"resolved repository root does not exist",
                            result.stderr,
                        )
                        entries = log.read_text(encoding="ascii").splitlines()
                        self.assertEqual(entries, ["invoked"])
                        self.assertEqual(
                            subprocess.check_output(
                                ["git", "rev-parse", "HEAD"], cwd=repo
                            ),
                            head_before,
                        )
                        self.assertEqual(
                            subprocess.check_output(
                                ["git", "status", "--porcelain=v1"], cwd=repo
                            ),
                            status_before,
                        )


if __name__ == "__main__":
    unittest.main()
