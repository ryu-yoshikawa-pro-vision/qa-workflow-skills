"""Format and check only formatter targets tracked by Git."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path, PurePosixPath
from typing import Sequence

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
RUFF_CONFIG = REPOSITORY_ROOT / "ruff.toml"
DPRINT_CONFIG = REPOSITORY_ROOT / "dprint.json"
DPRINT_VERSION = "dprint 0.55.2"
PYTHON_EXTENSIONS = {".py"}
DPRINT_EXTENSIONS = {
    ".md",
    ".json",
    ".yml",
    ".yaml",
    ".toml",
    ".js",
    ".cjs",
    ".mjs",
    ".jsx",
}
COMMANDS = ("ruff-check", "import-fix", "format", "check")


class FormatError(Exception):
    """An input or tool contract required by this script was not satisfied."""


def run_process(
    arguments: Sequence[str], input_text: str | None = None
) -> subprocess.CompletedProcess[str]:
    """Run a tool from the repository root without invoking a shell."""
    try:
        return subprocess.run(
            list(arguments),
            cwd=REPOSITORY_ROOT,
            input=input_text,
            capture_output=True,
            check=False,
            shell=False,
            text=True,
        )
    except OSError as error:
        raise FormatError(f"could not start {arguments[0]}: {error}") from error


def tracked_paths() -> list[str]:
    """Return the repository's tracked paths from Git's NUL-delimited output."""
    try:
        result = subprocess.run(
            ["git", "ls-files", "-z", "--"],
            cwd=REPOSITORY_ROOT,
            capture_output=True,
            check=False,
            shell=False,
        )
    except OSError as error:
        raise FormatError(f"could not start git: {error}") from error

    if result.returncode != 0:
        detail = os.fsdecode(result.stderr).strip()
        raise FormatError(f"git ls-files failed: {detail or result.returncode}")

    return sorted(os.fsdecode(path) for path in result.stdout.split(b"\0") if path)


def select_targets(paths: Sequence[str]) -> tuple[list[str], list[str]]:
    """Split tracked paths into Python and dprint target sets."""
    python_paths = []
    dprint_paths = []

    for path in paths:
        extension = PurePosixPath(path).suffix.lower()
        if extension in PYTHON_EXTENSIONS:
            python_paths.append(path)
        if extension in DPRINT_EXTENSIONS:
            if "\n" in path or "\r" in path:
                raise FormatError(
                    f"dprint --stdin-files cannot represent a path containing a newline: {path!r}"
                )
            dprint_paths.append(path)

    return python_paths, dprint_paths


def show_result(result: subprocess.CompletedProcess[str]) -> None:
    """Forward captured output while keeping successful checks quiet."""
    if result.stdout:
        sys.stdout.write(result.stdout)
    if result.stderr:
        sys.stderr.write(result.stderr)


def run_ruff(command: str, paths: Sequence[str]) -> int:
    """Run one Ruff operation on explicit tracked paths with the root config."""
    if not paths:
        return 0

    arguments = ["ruff"]
    if command == "ruff-check":
        arguments.extend(["check", "--config", str(RUFF_CONFIG)])
    elif command == "import-fix":
        arguments.extend(
            ["check", "--config", str(RUFF_CONFIG), "--select", "I", "--fix"]
        )
    elif command == "ruff-format":
        arguments.extend(["format", "--config", str(RUFF_CONFIG)])
    elif command == "ruff-format-check":
        arguments.extend(["format", "--check", "--config", str(RUFF_CONFIG)])
    else:
        raise FormatError(f"unsupported Ruff operation: {command}")

    result = run_process([*arguments, "--", *paths])
    show_result(result)
    return result.returncode


def normalized_dprint_path(path: str) -> str:
    """Normalize dprint's display paths for set comparison."""
    normalized = path.replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    repository_root = REPOSITORY_ROOT.resolve().as_posix().rstrip("/")
    root_prefix = repository_root + "/"
    candidate = normalized.casefold() if os.name == "nt" else normalized
    prefix = root_prefix.casefold() if os.name == "nt" else root_prefix
    if candidate.startswith(prefix):
        normalized = normalized[len(root_prefix) :]
    return normalized


def verify_dprint_version() -> None:
    """Require the pinned dprint CLI before any formatter target is changed."""
    result = run_process(["dprint", "--version"])
    if result.returncode != 0:
        show_result(result)
        raise FormatError(f"dprint --version failed with exit code {result.returncode}")

    version = result.stdout[:-1] if result.stdout.endswith("\n") else result.stdout
    if version != DPRINT_VERSION:
        raise FormatError(
            f"expected {DPRINT_VERSION!r} from dprint --version, received {version!r}"
        )


def stdin_paths(paths: Sequence[str]) -> str:
    """Encode a non-empty dprint path list using its newline-delimited input."""
    return "\n".join(paths) + "\n"


def verify_dprint_targets(paths: Sequence[str]) -> None:
    """Fail when dprint config does not resolve every expected tracked path."""
    arguments = [
        "dprint",
        "file-paths",
        "--config",
        str(DPRINT_CONFIG),
        "--config-discovery=false",
        "--no-gitignore",
        "--stdin-files",
    ]
    result = run_process(arguments, stdin_paths(paths))
    if result.returncode != 0:
        show_result(result)
        raise FormatError(
            f"dprint file-paths failed with exit code {result.returncode}"
        )

    expected = {normalized_dprint_path(path) for path in paths}
    resolved = {
        normalized_dprint_path(path)
        for path in result.stdout.splitlines()
        if path.strip()
    }
    if expected != resolved:
        missing = sorted(expected - resolved)
        unexpected = sorted(resolved - expected)
        raise FormatError(
            "dprint resolved paths differ from tracked targets; "
            f"missing={missing[:5]!r}, unexpected={unexpected[:5]!r}"
        )


def run_dprint(command: str, paths: Sequence[str]) -> int:
    """Run dprint on explicit tracked paths, bypassing all ignore discovery."""
    if not paths:
        return 0

    verify_dprint_version()
    verify_dprint_targets(paths)
    arguments = [
        "dprint",
        command,
        "--config",
        str(DPRINT_CONFIG),
        "--config-discovery=false",
        "--no-gitignore",
        "--stdin-files",
    ]
    result = run_process(arguments, stdin_paths(paths))
    show_result(result)
    return result.returncode


def execute(command: str, paths: Sequence[str] | None = None) -> int:
    """Execute a formatter entry point over the current tracked file set."""
    python_paths, dprint_paths = select_targets(
        paths if paths is not None else tracked_paths()
    )

    if command == "ruff-check":
        return run_ruff(command, python_paths)
    if command == "import-fix":
        return run_ruff(command, python_paths)
    if command == "format":
        if dprint_paths:
            verify_dprint_version()
            verify_dprint_targets(dprint_paths)
        ruff_result = run_ruff("ruff-format", python_paths)
        if ruff_result != 0:
            return ruff_result
        if not dprint_paths:
            return 0
        return run_dprint_after_preflight("fmt", dprint_paths)
    if command == "check":
        ruff_result = run_ruff("ruff-check", python_paths)
        if ruff_result != 0:
            return ruff_result
        ruff_result = run_ruff("ruff-format-check", python_paths)
        if ruff_result != 0:
            return ruff_result
        return run_dprint("check", dprint_paths)

    raise FormatError(f"unknown command: {command}")


def run_dprint_after_preflight(command: str, paths: Sequence[str]) -> int:
    """Format after dprint's version and target contracts have already passed."""
    arguments = [
        "dprint",
        command,
        "--config",
        str(DPRINT_CONFIG),
        "--config-discovery=false",
        "--no-gitignore",
        "--stdin-files",
    ]
    result = run_process(arguments, stdin_paths(paths))
    show_result(result)
    return result.returncode


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run format and lint tools on Git-tracked files only."
    )
    parser.add_argument("command", choices=COMMANDS)
    arguments = parser.parse_args(argv)

    try:
        return execute(arguments.command)
    except FormatError as error:
        print(f"format_tracked.py: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
