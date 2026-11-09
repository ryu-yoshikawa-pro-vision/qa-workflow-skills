"""Conditional Git publish for isolated testware changes.

Only a non-forced fast-forward push can update the shared branch. The candidate
must have the inspected base as its single parent. A failed push must not be
retried without reading the remote branch and re-reviewing changed content.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

HEX_SHA = re.compile(r"^[a-f0-9]{40}$")
REMOTE = re.compile(r"^[A-Za-z0-9_.-]+$")


class PublishError(ValueError):
    pass


def _git(repo: Path, *args: str) -> str:
    process = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        check=False,
        timeout=30,
    )
    if process.returncode:
        raise PublishError("git_" + args[0] + "_failed")
    return process.stdout.decode("utf-8", "strict").strip()


def _remote_head(repo: Path, remote: str, branch: str) -> str:
    lines = _git(repo, "ls-remote", "--heads", remote, "refs/heads/" + branch).splitlines()
    if len(lines) != 1:
        raise PublishError("remote_branch_unavailable")
    sha, ref = lines[0].split("\t", 1)
    if ref != "refs/heads/" + branch or not HEX_SHA.fullmatch(sha):
        raise PublishError("remote_head_invalid")
    return sha


def publish(
    *,
    repo_path: Path,
    remote: str,
    branch: str,
    expected_head: str,
    candidate: str,
    allowed_prefixes: list[str],
    prior_content_hashes: dict[str, str | None],
) -> dict[str, Any]:
    repo = repo_path.resolve(strict=True)
    if not repo.is_dir() or not REMOTE.fullmatch(remote):
        raise PublishError("invalid_repo_or_remote")
    if not HEX_SHA.fullmatch(expected_head) or not HEX_SHA.fullmatch(candidate):
        raise PublishError("invalid_commit")
    _git(repo, "check-ref-format", "--branch", branch)
    if not allowed_prefixes or not isinstance(prior_content_hashes, dict):
        raise PublishError("missing_write_scope")
    if _git(repo, "status", "--porcelain", "--untracked-files=all"):
        raise PublishError("dirty_candidate_workspace")
    parents = _git(repo, "rev-list", "--parents", "-n", "1", candidate).split()
    if parents != [candidate, expected_head]:
        raise PublishError("candidate_not_based_on_expected_head")
    paths_raw = _git(
        repo, "diff", "--name-only", "--no-renames", expected_head, candidate
    )
    paths = paths_raw.splitlines()
    if not paths or len(paths) != len(set(paths)):
        raise PublishError("empty_or_duplicate_diff")
    if set(paths) != set(prior_content_hashes):
        raise PublishError("incomplete_changed_paths")
    for path in paths:
        if "\\" in path or any(p in {"", ".", ".."} for p in path.split("/")):
            raise PublishError("unsafe_changed_path")
        if not any(
            path == prefix or path.startswith(prefix + "/")
            for prefix in allowed_prefixes
            if prefix and not prefix.startswith("/") and ".." not in prefix.split("/")
        ):
            raise PublishError("path_out_of_scope")
        mode = _git(repo, "ls-tree", candidate, "--", path).split("\t")
        if (
            len(mode) != 2
            or not (
                mode[0].startswith("100644 blob ")
                or mode[0].startswith("100755 blob ")
            )
        ):
            raise PublishError("non_regular_file_in_diff")
        process = subprocess.run(
            ["git", "-C", str(repo), "show", expected_head + ":" + path],
            capture_output=True, check=False, timeout=30,
        )
        old = (
            "sha256:" + hashlib.sha256(process.stdout).hexdigest()
            if process.returncode == 0 else None
        )
        if old != prior_content_hashes[path]:
            raise PublishError("changed_base_snapshot")
    if _remote_head(repo, remote, branch) != expected_head:
        raise PublishError("remote_branch_changed")
    # This is deliberately NOT --force or --force-with-lease. The remote's
    # native fast-forward check rejects another concurrent update.
    process = subprocess.run(
        ["git", "-C", str(repo), "push", remote, candidate + ":refs/heads/" + branch],
        capture_output=True, check=False, timeout=60,
    )
    if process.returncode:
        raise PublishError("push_rejected_or_response_unknown_verify_remote")
    if _remote_head(repo, remote, branch) != candidate:
        raise PublishError("push_readback_mismatch")
    _git(repo, "fetch", "--no-tags", remote, "refs/heads/" + branch)
    if _git(repo, "rev-parse", "FETCH_HEAD") != candidate:
        raise PublishError("fetched_readback_mismatch")
    for path in paths:
        local_blob = _git(repo, "rev-parse", candidate + ":" + path)
        remote_blob = _git(repo, "rev-parse", "FETCH_HEAD:" + path)
        if local_blob != remote_blob:
            raise PublishError("published_blob_mismatch")
    return {
        "state": "published_and_readback_verified",
        "remote": remote,
        "branch": branch,
        "commit_sha": candidate,
        "changed_paths": paths,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Conditional Git publish of reviewed testware")
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--publish", action="store_true")
    args = parser.parse_args()
    if not args.publish:
        parser.error("explicit --publish is required")
    try:
        data = json.loads(args.plan.read_text(encoding="utf-8"))
        result = publish(
            repo_path=Path(data["repo_path"]),
            remote=data["remote"],
            branch=data["branch"],
            expected_head=data["expected_head"],
            candidate=data["candidate"],
            allowed_prefixes=data["allowed_prefixes"],
            prior_content_hashes=data["prior_content_hashes"],
        )
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (PublishError, OSError, ValueError, KeyError, subprocess.TimeoutExpired) as err:
        print(json.dumps({
            "state": "not_attested",
            "reason": str(err) if isinstance(err, PublishError) else type(err).__name__,
        }, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
