"""Contracts for the Git-tracked formatter entry point."""

from __future__ import annotations

import importlib.util
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "format_tracked.py"
SPEC = importlib.util.spec_from_file_location("format_tracked", SCRIPT_PATH)
assert SPEC and SPEC.loader
format_tracked = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(format_tracked)


def completed(arguments: list[str], stdout: str = "", returncode: int = 0):
    return subprocess.CompletedProcess(arguments, returncode, stdout, "")


class SelectTargetsTests(unittest.TestCase):
    def test_selects_only_plan_extensions_case_insensitively(self) -> None:
        python, dprint = format_tracked.select_targets(
            ["src/a.py", "a.MD", "b.json", "c.yaml", "d.toml", "e.jsx", "x.ts", "x.ps1"]
        )
        self.assertEqual(python, ["src/a.py"])
        self.assertEqual(dprint, ["a.MD", "b.json", "c.yaml", "d.toml", "e.jsx"])

    def test_rejects_newline_in_dprint_path(self) -> None:
        with self.assertRaisesRegex(format_tracked.FormatError, "newline"):
            format_tracked.select_targets(["directory/bad\nname.md"])


class FormatterInvocationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp(prefix="formatter fixture with spaces "))
        self.ruff_config = self.root / "ruff.toml"
        self.dprint_config = self.root / "dprint.json"

    def tearDown(self) -> None:
        import shutil

        shutil.rmtree(self.root)

    def run_with_paths(self, command: str, paths: list[str], side_effect):
        with (
            patch.object(format_tracked, "REPOSITORY_ROOT", self.root),
            patch.object(format_tracked, "RUFF_CONFIG", self.ruff_config),
            patch.object(format_tracked, "DPRINT_CONFIG", self.dprint_config),
            patch.object(format_tracked, "tracked_paths", return_value=paths),
            patch.object(
                format_tracked, "run_process", side_effect=side_effect
            ) as runner,
        ):
            result = format_tracked.execute(command)
        return result, runner

    def test_every_ruff_command_uses_absolute_root_config_and_explicit_paths(
        self,
    ) -> None:
        paths = ["src/module.py"]
        for command, expected_subcommand in (
            ("ruff-check", "check"),
            ("import-fix", "check"),
            ("check", "check"),
            ("format", "format"),
        ):
            with self.subTest(command=command):
                result, runner = self.run_with_paths(
                    command,
                    paths,
                    lambda args, input_text=None: completed(args),
                )
                self.assertEqual(result, 0)
                ruff_calls = [
                    call.args[0]
                    for call in runner.call_args_list
                    if call.args[0][0] == "ruff"
                ]
                self.assertTrue(ruff_calls)
                for args in ruff_calls:
                    self.assertEqual(args[0], "ruff")
                    if command == "format":
                        self.assertEqual(args[1], "format")
                    elif command == "check":
                        self.assertIn(args[1], {"check", "format"})
                        if args[1] == "format":
                            self.assertIn("--check", args)
                    else:
                        self.assertEqual(args[1], "check")
                    self.assertIn("--config", args)
                    self.assertEqual(
                        args[args.index("--config") + 1], str(self.ruff_config)
                    )
                    self.assertEqual(args[-2:], ["--", "src/module.py"])

    def test_format_and_check_pin_dprint_config_discovery_and_ignore_behavior(
        self,
    ) -> None:
        paths = ["nested/configured.md", "nested/configured.py"]
        expected_markdown = "nested/configured.md\n"

        def runner(args, input_text=None):
            if args[:2] == ["dprint", "--version"]:
                return completed(args, "dprint 0.55.2\n")
            if args[1] == "file-paths":
                self.assertEqual(input_text, expected_markdown)
                absolute_path = self.root / "nested" / "configured.md"
                return completed(args, f"{absolute_path}\n")
            return completed(args)

        for command in ("format", "check"):
            with (
                self.subTest(command=command),
                patch.dict(os.environ, {"DPRINT_GLOBAL_GITIGNORE": "1"}),
            ):
                result, calls = self.run_with_paths(command, paths, runner)
                self.assertEqual(result, 0)
                dprint_calls = [
                    call.args[0]
                    for call in calls.call_args_list
                    if call.args[0][0] == "dprint"
                ]
                self.assertGreaterEqual(len(dprint_calls), 3)
                for args in dprint_calls:
                    if args[1] == "--version":
                        continue
                    self.assertIn("--config", args)
                    self.assertEqual(
                        args[args.index("--config") + 1], str(self.dprint_config)
                    )
                    self.assertIn("--config-discovery=false", args)
                for args in dprint_calls:
                    if args[1] in {"file-paths", "fmt", "check"}:
                        self.assertIn("--no-gitignore", args)
                        self.assertIn("--stdin-files", args)

    def test_dprint_version_mismatch_stops_before_file_changes_or_file_paths(
        self,
    ) -> None:
        for output in (
            "dprint 0.55.2 extra\n",
            "dprint 0.55.20\n",
            "version dprint 0.55.2\n",
        ):
            with self.subTest(output=output):
                calls = []

                def runner(args, input_text=None):
                    calls.append(args)
                    return completed(args, output)

                with self.assertRaisesRegex(
                    format_tracked.FormatError, "expected 'dprint 0.55.2'"
                ):
                    self.run_with_paths("format", ["note.md"], runner)
                self.assertEqual(calls, [["dprint", "--version"]])

    def test_dprint_target_mismatch_stops_before_fmt(self) -> None:
        calls = []

        def runner(args, input_text=None):
            calls.append((args, input_text))
            if args[:2] == ["dprint", "--version"]:
                return completed(args, "dprint 0.55.2\n")
            return completed(args, "other.md\n")

        with self.assertRaisesRegex(
            format_tracked.FormatError, "resolved paths differ"
        ):
            self.run_with_paths("format", ["wanted.md"], runner)
        self.assertEqual([args[1] for args, _ in calls], ["--version", "file-paths"])

    def test_zero_dprint_targets_short_circuit_for_format_and_check(self) -> None:
        for command in ("format", "check"):
            with self.subTest(command=command):
                result, runner = self.run_with_paths(
                    command,
                    ["tracked.py"],
                    lambda args, input_text=None: completed(args),
                )
                self.assertEqual(result, 0)
                self.assertFalse(
                    any(call.args[0][0] == "dprint" for call in runner.call_args_list)
                )

    def test_zero_dprint_targets_ignore_untracked_files_without_touching_them(
        self,
    ) -> None:
        for command in ("format", "check"):
            with (
                self.subTest(command=command),
                tempfile.TemporaryDirectory() as directory,
            ):
                root = Path(directory)
                untracked = root / "untracked.md"
                untracked.write_text("leave this alone\n", encoding="utf-8")
                with (
                    patch.object(format_tracked, "REPOSITORY_ROOT", root),
                    patch.object(
                        format_tracked, "tracked_paths", return_value=["tracked.py"]
                    ),
                    patch.object(
                        format_tracked,
                        "run_process",
                        side_effect=lambda args, input_text=None: completed(args),
                    ) as runner,
                ):
                    self.assertEqual(format_tracked.execute(command), 0)
                self.assertFalse(
                    any(call.args[0][0] == "dprint" for call in runner.call_args_list)
                )
                self.assertEqual(
                    untracked.read_text(encoding="utf-8"), "leave this alone\n"
                )

    def test_nested_config_files_do_not_replace_explicit_root_configs(self) -> None:
        nested = self.root / "nested"
        nested.mkdir()
        (nested / "ruff.toml").write_text("select = ['ALL']\n", encoding="utf-8")
        (nested / "dprint.json").write_text('{"includes": []}\n', encoding="utf-8")
        paths = ["nested/a.py", "nested/a.md"]

        def runner(args, input_text=None):
            if args[:2] == ["dprint", "--version"]:
                return completed(args, "dprint 0.55.2\n")
            if args[1] == "file-paths":
                return completed(args, "nested/a.md\n")
            return completed(args)

        result, calls = self.run_with_paths("check", paths, runner)
        self.assertEqual(result, 0)
        for call in calls.call_args_list:
            args = call.args[0]
            if args[0] == "ruff":
                self.assertEqual(
                    args[args.index("--config") + 1], str(self.ruff_config)
                )
            if args[0] == "dprint":
                if args[1] == "--version":
                    continue
                self.assertEqual(
                    args[args.index("--config") + 1], str(self.dprint_config)
                )


class TrackedPathTests(unittest.TestCase):
    def test_git_ls_files_is_the_only_target_source_including_ignored_files(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory(
            prefix="tracked formatter space "
        ) as directory:
            root = Path(directory)
            global_ignore = root / "global-ignore"
            global_config = root / "isolated-gitconfig"
            global_ignore.write_text("global-ignored.yaml\n", encoding="utf-8")
            env = os.environ.copy()
            env["GIT_CONFIG_GLOBAL"] = str(global_config)
            subprocess.run(
                ["git", "config", "--global", "core.excludesfile", str(global_ignore)],
                cwd=root,
                env=env,
                check=True,
            )
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            subprocess.run(
                ["git", "config", "user.name", "Formatter Test"], cwd=root, check=True
            )
            subprocess.run(
                ["git", "config", "user.email", "formatter@example.invalid"],
                cwd=root,
                check=True,
            )
            (root / ".gitignore").write_text("repo-ignored.md\n", encoding="utf-8")
            info_exclude = root / ".git" / "info" / "exclude"
            info_exclude.write_text("info-ignored.json\n", encoding="utf-8")
            (root / "repo-ignored.md").write_text(
                "tracked despite ignore\n", encoding="utf-8"
            )
            (root / "info-ignored.json").write_text("{}\n", encoding="utf-8")
            (root / "global-ignored.yaml").write_text("value: true\n", encoding="utf-8")
            (root / "untracked.md").write_text(
                "not part of the set\n", encoding="utf-8"
            )
            subprocess.run(["git", "add", ".gitignore"], cwd=root, check=True)
            subprocess.run(
                [
                    "git",
                    "add",
                    "-f",
                    "repo-ignored.md",
                    "info-ignored.json",
                    "global-ignored.yaml",
                ],
                cwd=root,
                check=True,
                env=env,
            )

            with patch.object(format_tracked, "REPOSITORY_ROOT", root):
                paths = format_tracked.tracked_paths()

            for path in ("repo-ignored.md", "info-ignored.json", "global-ignored.yaml"):
                with self.subTest(path=path):
                    result = subprocess.run(
                        ["git", "check-ignore", "--no-index", "--", path],
                        cwd=root,
                        env=env,
                        capture_output=True,
                        check=False,
                    )
                    self.assertEqual(result.returncode, 0, path)
                    self.assertIn(path, paths)
            self.assertNotIn("untracked.md", paths)


if __name__ == "__main__":
    unittest.main()
