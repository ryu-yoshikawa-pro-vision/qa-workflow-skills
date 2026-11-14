"""PR #220 evidence collector (read-only against product repo).

- Runs feature-analysis git_source_inventory.py (trusted skill script) with
  authorized_root = product checkout and base/head full SHAs.
- Summarises package.json and pnpm-lock.yaml changes between base and head.
Writes JSON outputs under qa-state/pr-220/evidence/. Product files are not modified.
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path("<scratchpad>/realpr/workspace")
PRODUCT = ROOT / "product"
SKILL = ROOT / ".claude/skills/feature-analysis/scripts/git_source_inventory.py"
OUT = ROOT / "qa-state/pr-220/evidence"

HEAD = "2a8bcf57ff091e84a8b3bf7b123568e967000d88"
BASE = "d866f90961d73f738473b2c700780abe169ff79e"


def git(*args: str) -> str:
    res = subprocess.run(
        ["git", "-C", str(PRODUCT), *args],
        capture_output=True,
        check=True,
    )
    return res.stdout.decode("utf-8")


def run_inventory() -> dict:
    request = {
        "repository_root": str(PRODUCT),
        "authorized_root": str(PRODUCT),
        "base_sha": BASE,
        "head_sha": HEAD,
    }
    env = dict(os.environ)
    env["QA_FEATURE_AUTHORIZED_ROOT"] = str(PRODUCT)
    res = subprocess.run(
        [sys.executable, "-I", str(SKILL)],
        input=json.dumps(request).encode("utf-8"),
        capture_output=True,
        env=env,
        timeout=300,
    )
    out = res.stdout.decode("utf-8", "replace").strip()
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        data = {"status": "blocked", "reason": "non_json_output", "raw": out[:500]}
    # Keep only status-relevant fields plus file/change counts (full listing is large).
    summary = {k: v for k, v in data.items() if k not in {"files", "changes"}}
    if "files" in data:
        summary["files_count"] = len(data["files"])
    if "changes" in data:
        summary["changes_count"] = len(data["changes"])
        summary["changes"] = data["changes"]
    return summary


def package_json_delta() -> dict:
    old = json.loads(git("show", f"{BASE}:package.json"))
    new = json.loads(git("show", f"{HEAD}:package.json"))
    sections = ["dependencies", "devDependencies", "pnpm"]
    changed = []
    added = []
    removed = []
    for sec in sections:
        o = old.get(sec, {}) or {}
        n = new.get(sec, {}) or {}
        if sec == "pnpm":
            o = o.get("overrides", {}) | {
                f"packageExtensions:{k}": v
                for k, v in (
                    old.get("pnpm", {}).get("packageExtensions", {}) or {}
                ).items()
            }
            n = n.get("overrides", {}) | {
                f"packageExtensions:{k}": v
                for k, v in (
                    new.get("pnpm", {}).get("packageExtensions", {}) or {}
                ).items()
            }
            sec = "pnpm.overrides+packageExtensions"
        for k in sorted(set(o) | set(n)):
            if k not in o:
                added.append({"section": sec, "name": k, "to": n[k]})
            elif k not in n:
                removed.append({"section": sec, "name": k, "from": o[k]})
            elif o[k] != n[k]:
                changed.append({"section": sec, "name": k, "from": o[k], "to": n[k]})
    other_top = sorted(
        k
        for k in set(old) | set(new)
        if k not in {"dependencies", "devDependencies", "pnpm"}
        and old.get(k) != new.get(k)
    )
    return {
        "changed": changed,
        "added": added,
        "removed": removed,
        "other_top_level_keys_changed": other_top,
        "dependency_section_of_expo_dev_client": new.get("dependencies", {}).get(
            "expo-dev-client"
        ),
        "dev_dependencies_section_has_expo_dev_client": "expo-dev-client"
        in new.get("devDependencies", {}),
    }


PKG_KEY = re.compile(r"^  '?(.+?)'?:\s*$")


def lock_keys(text: str) -> set:
    keys = set()
    section = None
    for line in text.splitlines():
        if line in {"packages:", "snapshots:", "importers:"}:
            section = line[:-1]
            continue
        if line and not line.startswith(" "):
            section = (
                None
                if line not in {"packages:", "snapshots:", "importers:"}
                else section
            )
            continue
        if section in {"packages", "snapshots"}:
            m = PKG_KEY.match(line)
            if m and not line.startswith("   "):
                keys.add((section, m.group(1)))
    return keys


def lock_delta() -> dict:
    old = git("show", f"{BASE}:pnpm-lock.yaml")
    new = git("show", f"{HEAD}:pnpm-lock.yaml")
    ok = lock_keys(old)
    nk = lock_keys(new)
    added = sorted(nk - ok)
    removed = sorted(ok - nk)

    def name_of(key: str) -> str:
        # strip version / peer suffix: name@version(...) or @scope/name@version
        base = key.split("(")[0]
        idx = base.rfind("@")
        return base[:idx] if idx > 0 else base

    added_names = {name_of(k) for _, k in added}
    removed_names = {name_of(k) for _, k in removed}
    return {
        "added_key_count": len(added),
        "removed_key_count": len(removed),
        "added_keys_sample": [k for _, k in added][:80],
        "removed_keys_sample": [k for _, k in removed][:80],
        "names_only_added": sorted(added_names - removed_names),
        "names_only_removed": sorted(removed_names - added_names),
        "names_version_changed": sorted(added_names & removed_names),
    }


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    head_now = git("log", "-1", "--format=%H", HEAD).strip()
    result = {
        "pr": 220,
        "merge_commit": HEAD,
        "parent_commit": BASE,
        "commit_subject_check": head_now == HEAD,
        "stat": git("diff", "--stat", BASE, HEAD).strip(),
        "name_status": git("diff", "--name-status", BASE, HEAD).strip().splitlines(),
        "package_json": package_json_delta(),
        "pnpm_lock": lock_delta(),
        "git_source_inventory": run_inventory(),
    }
    (OUT / "pr220-evidence.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "written": str(OUT / "pr220-evidence.json"),
                "inventory_status": result["git_source_inventory"].get("status"),
                "inventory_reason": result["git_source_inventory"].get("reason"),
                "name_status": result["name_status"],
                "package_changed": len(result["package_json"]["changed"]),
                "package_added": len(result["package_json"]["added"]),
                "package_removed": len(result["package_json"]["removed"]),
                "lock_added": result["pnpm_lock"]["added_key_count"],
                "lock_removed": result["pnpm_lock"]["removed_key_count"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
