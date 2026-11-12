"""Agent side: write the candidate handoff manifest next to the stored artifacts.

The manifest is a candidate; the product CI never trusts it as expected and
compares it against values it derives independently.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

TRAILER = re.compile(r"^(QA-[A-Za-z-]+): (.*)$", re.MULTILINE)


def git(repo: Path, *args: str, binary: bool = False):
    result = subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, check=True
    )
    return result.stdout if binary else result.stdout.decode("utf-8").strip()


def main() -> int:
    cli = argparse.ArgumentParser()
    cli.add_argument("--product", type=Path, required=True)
    cli.add_argument("--artifacts", type=Path, required=True)
    cli.add_argument("--repository", required=True)
    cli.add_argument("--source-head", required=True)
    cli.add_argument("--out", type=Path, required=True)
    args = cli.parse_args()
    head = git(args.product, "rev-parse", args.source_head)
    base = git(args.product, "rev-parse", f"{head}^")
    changes = [
        {"path": path, "classification": "dependency"}
        for path in sorted(
            git(args.product, "diff", "--name-only", base, head).splitlines()
        )
        if path
    ]
    artifacts = []
    for path in sorted(
        git(
            args.artifacts, "ls-tree", "-r", "--name-only", "HEAD", "--", "qa/"
        ).splitlines()
    ):
        if not path.endswith(".md"):
            continue
        last = git(args.artifacts, "log", "-1", "--format=%H", "HEAD", "--", path)
        message = git(args.artifacts, "log", "-1", "--format=%B", last)
        trailers = dict(TRAILER.findall(message))
        subject = message.splitlines()[0].split()
        content = git(args.artifacts, "show", f"HEAD:{path}", binary=True)
        artifacts.append(
            {
                "owner": subject[2],
                "scope": trailers["QA-Project-Ref"],
                "artifact_ref": path,
                "revision": f"git:{last}",
                "sha256": "sha256:" + hashlib.sha256(content).hexdigest(),
                "path": path,
                "source_refs": [
                    {"ref": "repo-source", "revision": trailers["QA-Source-Revision"]}
                ],
            }
        )
    manifest = {
        "schema_version": "qa-ci-handoff-v1",
        "source": {
            "repository": args.repository,
            "base_sha": base,
            "head_sha": head,
            "build_ref": f"git:{head}",
        },
        "source_inventory": {
            "complete": True,
            "entries": [{"ref": "repo-source", "revision": head}],
        },
        "changes": changes,
        "artifacts": artifacts,
    }
    args.out.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
