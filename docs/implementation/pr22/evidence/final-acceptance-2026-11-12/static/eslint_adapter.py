"""Adapter: ESLint JSON -> normalized static-analysis report for testware-execution.

Runs ``eslint --format json`` on the expected paths inside the repository (cwd) and
prints the report the runner's static contract requires on stdout. A path that ESLint
did not return a result for is reported as skipped, never as clean. Exit code is the
number-independent ESLint exit code, so the runner's accepted exit codes apply.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path


def main(argv: list[str]) -> int:
    paths = argv
    repo = Path.cwd()
    eslint = repo / "node_modules" / ".bin" / "eslint"
    version = subprocess.run(
        [str(eslint), "--version"], capture_output=True, text=True, check=False
    ).stdout.strip()
    done = subprocess.run(
        [str(eslint), "--format", "json", *paths],
        capture_output=True,
        text=True,
        check=False,
    )
    try:
        results = json.loads(done.stdout)
    except ValueError:
        results = []
    analyzed = sorted(str(Path(r["filePath"]).relative_to(repo)) for r in results)
    skipped = sorted(set(paths) - set(analyzed))
    findings = sum(r["errorCount"] + r["warningCount"] for r in results)
    config = (repo / "eslint.config.js").read_bytes()
    report = {
        "tool_ref": "eslint",
        "tool_version": version,
        "rules_ref": "eslint.config.js@sha256:" + hashlib.sha256(config).hexdigest(),
        "config_ref": "eslint.config.js",
        "analyzed_paths": analyzed,
        "skipped_paths": skipped,
        "findings_count": findings,
        "per_file": {
            str(Path(r["filePath"]).relative_to(repo)): {
                "errors": r["errorCount"],
                "warnings": r["warningCount"],
            }
            for r in results
        },
    }
    print(json.dumps(report, ensure_ascii=False))
    return done.returncode


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
