"""Build the *trusted* expected handoff from the product CI's own checkouts.

Runs inside the product CI. Nothing is taken from the Agent's candidate manifest:
the source range comes from the product checkout, and each stored artifact's
ref, revision, content hash and source revision come from the artifact branch's
Git objects (the commit that last wrote the file and its QA trailers).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

ALLOWED_CLASSIFICATIONS = [
    "implementation",
    "specification",
    "test",
    "documentation",
    "dependency",
]
TRAILER = re.compile(r"^(QA-[A-Za-z-]+): (.*)$", re.MULTILINE)
SUBJECT = re.compile(r"^qa artifact: (\S+) (\S+)$")


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
    changed = sorted(
        line
        for line in git(args.product, "diff", "--name-only", base, head).splitlines()
        if line
    )
    artifact_commit = git(args.artifacts, "rev-parse", "HEAD")
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
        subject = SUBJECT.match(message.splitlines()[0])
        trailers = dict(TRAILER.findall(message))
        if not subject or "QA-Project-Ref" not in trailers:
            raise SystemExit(f"{path}: not written by the artifact provider")
        content = git(args.artifacts, "show", f"HEAD:{path}", binary=True)
        artifacts.append(
            {
                "owner": subject.group(1),
                "scope": trailers["QA-Project-Ref"],
                "artifact_ref": path,
                "revision": f"git:{last}",
                "sha256": "sha256:" + hashlib.sha256(content).hexdigest(),
                "source_refs": [
                    {
                        "ref": "repo-source",
                        "revision": trailers["QA-Source-Revision"],
                    }
                ],
            }
        )
    expected = {
        "schema_version": "qa-ci-handoff-v1",
        "source": {
            "repository": args.repository,
            "base_sha": base,
            "head_sha": head,
            "build_ref": f"git:{head}",
        },
        "source_inventory": [{"ref": "repo-source", "revision": head}],
        "changed_paths": changed,
        "allowed_classifications": ALLOWED_CLASSIFICATIONS,
        "artifacts": artifacts,
        "required_approvals": [],
    }
    args.out.write_text(
        json.dumps(expected, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        f"expected built: artifact_commit={artifact_commit} artifacts={len(artifacts)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
