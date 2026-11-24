"""Check that each stored artifact revision was pushed by an approved account.

The approval evidence is the repository activity API (Plan 02 section 2): the
push that produced the artifact's revision commit must come from an approved,
GitHub-authenticated account. The commit author is never used.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    cli = argparse.ArgumentParser()
    cli.add_argument("--activity", type=Path, required=True)
    cli.add_argument("--expected", type=Path, required=True)
    cli.add_argument("--approvers", required=True)
    args = cli.parse_args()
    approvers = {name.strip() for name in args.approvers.split(",") if name.strip()}
    rows = json.loads(args.activity.read_text(encoding="utf-8"))
    pushes = {
        row["after"]: row["actor"]["login"]
        for row in rows
        if row.get("activity_type") == "push"
    }
    expected = json.loads(args.expected.read_text(encoding="utf-8"))
    failures = []
    for artifact in expected["artifacts"]:
        commit = artifact["revision"].removeprefix("git:")
        actor = pushes.get(commit)
        if actor is None:
            failures.append(
                f"{artifact['artifact_ref']}: no push activity for {commit}"
            )
        elif actor not in approvers:
            failures.append(f"{artifact['artifact_ref']}: pushed by {actor}")
    if not approvers or failures:
        print("pusher check failed: " + "; ".join(failures or ["no approvers"]))
        return 1
    print(f"pusher check passed for {len(expected['artifacts'])} artifact(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
