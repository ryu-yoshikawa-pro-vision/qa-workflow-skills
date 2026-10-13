#!/usr/bin/env python3
"""Check changed-line whitespace from the GitHub Actions event commits."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

SHA_PATTERN = re.compile(r"(?:[0-9a-fA-F]{40}|[0-9a-fA-F]{64})")


def require_sha(value: Any, name: str) -> str:
    if not isinstance(value, str) or not SHA_PATTERN.fullmatch(value):
        raise ValueError(f"GitHub event is missing a valid {name} commit SHA")
    return value


def empty_tree() -> str:
    result = subprocess.run(
        ["git", "hash-object", "-t", "tree", "--stdin"],
        input=b"",
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"could not determine the empty tree object: {detail}")
    return result.stdout.decode("ascii").strip()


def diff_arguments(
    event_name: str, event: dict[str, Any], github_sha: str
) -> list[str]:
    if event_name == "pull_request":
        pull_request = event.get("pull_request")
        if not isinstance(pull_request, dict):
            raise ValueError("pull_request event payload is missing pull_request")
        base = pull_request.get("base")
        head = pull_request.get("head")
        if not isinstance(base, dict) or not isinstance(head, dict):
            raise ValueError("pull_request event payload is missing base/head commits")
        base_sha = require_sha(base.get("sha"), "pull_request.base.sha")
        head_sha = require_sha(head.get("sha"), "pull_request.head.sha")
        if len(base_sha) != len(head_sha):
            raise ValueError("pull_request base/head commit SHA formats do not match")
        return [f"{base_sha}...{head_sha}"]

    if event_name == "push":
        head_sha = require_sha(github_sha, "GITHUB_SHA")
        before = event.get("before")
        if not isinstance(before, str) or not before:
            raise ValueError("push event payload is missing before SHA")
        if set(before) == {"0"}:
            if len(before) not in (40, 64) or len(before) != len(head_sha):
                raise ValueError("initial push before SHA has an invalid format")
            return [empty_tree(), head_sha]
        before_sha = require_sha(before, "push.before")
        if len(before_sha) != len(head_sha):
            raise ValueError("push before/HEAD commit SHA formats do not match")
        return [before_sha, head_sha]

    raise ValueError(f"unsupported GitHub event: {event_name!r}")


def main() -> int:
    try:
        event_name = os.environ.get("GITHUB_EVENT_NAME", "")
        event_path = os.environ.get("GITHUB_EVENT_PATH", "")
        github_sha = os.environ.get("GITHUB_SHA", "")
        if not event_name or not event_path:
            raise ValueError("GITHUB_EVENT_NAME and GITHUB_EVENT_PATH are required")
        event = json.loads(Path(event_path).read_text(encoding="utf-8"))
        if not isinstance(event, dict):
            raise ValueError("GitHub event payload must be a JSON object")
        revisions = diff_arguments(event_name, event, github_sha)
        command = [
            "git",
            "diff",
            "--no-ext-diff",
            "--no-textconv",
            "--check",
            *revisions,
        ]
        return subprocess.run(command, check=False).returncode
    except (OSError, json.JSONDecodeError, RuntimeError, ValueError) as error:
        print(f"patch whitespace check: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
