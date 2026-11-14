"""Acceptance run of the Git artifact provider against a real GitHub repository.

Authorized scope (user decision, 2026-11-13): push only to the dedicated branch
``qa/artifacts`` of ``qa-training-store``. Product code is never touched: the
branch is an orphan branch that only holds QA artifacts.

The run verifies, against GitHub itself:
  * create-if-absent and revision history through ``GitArtifactStore``,
  * remote compare-and-swap (a stale writer's push is rejected, the head is kept),
  * independent readback from a fresh clone,
  * the authenticated actor and before/after SHAs of each push, read from the
    repository activity API (the approval evidence defined in Plan 02 section 2),
  * refusal of an unapproved write.

Usage (the token is read from ``GH_TOKEN`` and never printed or stored):

    GH_TOKEN=... python run_git_provider_acceptance.py --repo OWNER/REPO \
        --approver LOGIN --out result.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[6]
sys.path.insert(0, str(REPO_ROOT / "skills" / "project-context" / "scripts"))

from artifact_store import StoreError  # noqa: E402
from git_artifact_store import GitArtifactStore  # noqa: E402
from project_context import persist_prepared  # noqa: E402

BRANCH = "qa/artifacts"
ARTIFACT_REF = "qa/project-context.md"
APPROVAL_REF = "approval/interactive-consent-2026-11-13"
APPROVAL_REVISION = "policy-git-push-actor-v1"
PINNED_SHA = "2a8bcf57ff091e84a8b3bf7b123568e967000d88"


def git(cwd: Path, *args: str, token: str | None = None, check: bool = True):
    command = ["git"]
    if token is not None:
        helper = '!f() { echo username=x-access-token; echo "password=$GH_TOKEN"; }; f'
        command += ["-c", "credential.helper=", "-c", f"credential.helper={helper}"]
    command += list(args)
    result = subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        text=True,
        env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
    )
    if check and result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args[:2])} failed: {result.stderr.strip()}")
    return result


def api(token: str, path: str) -> Any:
    request = urllib.request.Request(
        f"https://api.github.com{path}",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
        },
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read())


def authorizer(allowed_approval: str, allowed_revision: str):
    def authorize(request: dict[str, Any]) -> bool:
        if request["operation"] == "read":
            return True
        return (
            request.get("approval_ref") == allowed_approval
            and request.get("approval_revision") == allowed_revision
        )

    return authorize


def store_for(root: Path, authorize) -> GitArtifactStore:
    return GitArtifactStore(
        root,
        root,
        BRANCH,
        authorize,
        author_name="qa-workflow-skills",
        author_email="qa@example.invalid",
    )


def prepare_create() -> dict[str, Any]:
    return {
        "operation": "prepare-create",
        "project_name": "qa-training-store",
        "enumeration_complete": True,
        "candidates": [{"ref": ARTIFACT_REF, "status": "absent"}],
        "artifact_ref": ARTIFACT_REF,
        "source_ref": "qa-training-store",
        "source_revision": PINNED_SHA,
        "change_reason": "acceptance: initial Project Context",
    }


def prepare_update(markdown: str, expected_revision: str, value: str) -> dict[str, Any]:
    return {
        "operation": "prepare-update",
        "markdown": markdown,
        "artifact_ref": ARTIFACT_REF,
        "expected_revision": expected_revision,
        "source_ref": "qa-training-store",
        "source_revision": PINNED_SHA,
        "change_reason": "acceptance: record feature base ref",
        "updates": {"qa.feature_base_ref": value},
    }


def activity(
    token: str, repo: str, head: str, *, attempts: int = 24, delay: float = 5.0
) -> dict[str, Any] | None:
    """Read the push activity of ``head``. GitHub records it with a delay, so retry."""
    for attempt in range(attempts):
        rows = api(token, f"/repos/{repo}/activity?ref=refs/heads/{BRANCH}&per_page=50")
        for row in rows:
            if row["after"] == head:
                return {
                    "activity_type": row["activity_type"],
                    "actor": row["actor"]["login"],
                    "before": row["before"],
                    "after": row["after"],
                    "timestamp": row["timestamp"],
                    "polls": attempt + 1,
                }
        time.sleep(delay)
    return None


def verify_activity(token: str, repo: str, approver: str, path: Path) -> int:
    """Complete the approval evidence of an earlier run from the activity API.

    The first run read the activity before GitHub had recorded it. Each saved
    revision's commit must be a push by the approver whose ``before`` is the
    previous accepted head.
    """
    evidence = json.loads(path.read_text(encoding="utf-8"))
    steps = evidence["steps"]
    created = steps["branch_created"]["head"]
    sequence = [
        ("write_1_create", steps["write_1_create"]["result"]["revision"], created),
        (
            "write_2_update",
            steps["write_2_update"]["result"]["revision"],
            steps["write_1_create"]["result"]["revision"].removeprefix("git:"),
        ),
    ]
    actors = set()
    for key, revision, expected_before in sequence:
        head = revision.removeprefix("git:")
        found = activity(token, repo, head, attempts=3, delay=2)
        steps[key]["activity"] = found
        steps[key]["activity_matches_previous_head"] = bool(
            found and found["before"] == expected_before
        )
        if found:
            actors.add(found["actor"])
    steps["approver_check"] = {
        "expected_approver": approver,
        "observed_actors": sorted(actors),
        "matches": actors == {approver},
        "activity_read_after_the_run": True,
        "note": "GitHub records push activity with a delay; the run read it too early.",
    }
    evidence["passed"] = (
        steps["approver_check"]["matches"]
        and all(steps[k]["activity_matches_previous_head"] for k, _, _ in sequence)
        and steps["create_if_absent_again"]["status"] == "blocked"
        and steps["remote_cas_conflict"]["rejected"]
        and steps["remote_cas_conflict"]["remote_head_unchanged"]
        and steps["unapproved_write"]["status"] == "blocked"
        and steps["unapproved_write"]["ref_unchanged"]
        and all(
            v["sha256_matches_write"]
            for k, v in steps["independent_readback"].items()
            if k.startswith("rev")
        )
        and steps["independent_readback"]["current_is_latest_accepted"]
        and steps["independent_readback"]["stale_write_not_in_remote"]
    )
    path.write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0 if evidence["passed"] else 1


def main() -> int:
    cli = argparse.ArgumentParser()
    cli.add_argument("--repo", required=True)
    cli.add_argument("--approver", required=True)
    cli.add_argument("--out", type=Path, required=True)
    cli.add_argument("--url", help="remote URL override (local dry run)")
    cli.add_argument("--skip-api", action="store_true", help="do not call the API")
    cli.add_argument(
        "--verify-activity",
        action="store_true",
        help="complete the approval evidence of an earlier result file (--out)",
    )
    args = cli.parse_args()
    token = os.environ.get("GH_TOKEN", "")
    if not token:
        raise SystemExit("GH_TOKEN is required")
    if args.verify_activity:
        return verify_activity(token, args.repo, args.approver, args.out)
    url = args.url or f"https://github.com/{args.repo}.git"
    global activity
    if args.skip_api:
        activity = lambda *_: None  # noqa: E731
    evidence: dict[str, Any] = {"repo": args.repo, "branch": BRANCH, "steps": {}}
    steps = evidence["steps"]

    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        writer = base / "writer"
        writer.mkdir()
        git(writer, "init", "-q")
        git(writer, "config", "user.name", "qa-workflow-skills")
        git(writer, "config", "user.email", "qa@example.invalid")
        git(writer, "checkout", "-q", "--orphan", BRANCH)
        (writer / "README.md").write_text(
            "QA artifacts branch. Product code lives on other branches and is not touched.\n",
            encoding="utf-8",
        )
        git(writer, "add", "README.md")
        git(writer, "commit", "-qm", "chore: QA artifacts branch")
        git(writer, "remote", "add", "origin", url)
        remote = git(writer, "ls-remote", "origin", f"refs/heads/{BRANCH}", token=token)
        if remote.stdout.strip():
            raise SystemExit("branch already exists; refusing to continue")
        git(writer, "push", "origin", f"{BRANCH}:refs/heads/{BRANCH}", token=token)
        steps["branch_created"] = {
            "head": git(writer, "rev-parse", "HEAD").stdout.strip()
        }

        store = store_for(writer, authorizer(APPROVAL_REF, APPROVAL_REVISION))

        # 1. create-if-absent (project-context) and push.
        first = persist_prepared(
            store,
            prepare_create(),
            project_ref="qa-training-store",
            operation_id="acceptance-create-1",
            approval_ref=APPROVAL_REF,
            approval_revision=APPROVAL_REVISION,
        )
        assert first.get("status") == "stored", first
        git(writer, "push", "origin", BRANCH, token=token)
        head1 = git(writer, "rev-parse", "HEAD").stdout.strip()
        steps["write_1_create"] = {
            "result": {k: first[k] for k in ("status", "revision", "sha256")},
            "activity": activity(token, args.repo, head1),
        }

        # create-if-absent again must not overwrite.
        again = persist_prepared(
            store,
            prepare_create(),
            project_ref="qa-training-store",
            operation_id="acceptance-create-2",
            approval_ref=APPROVAL_REF,
            approval_revision=APPROVAL_REVISION,
        )
        steps["create_if_absent_again"] = {
            "status": again.get("status"),
            "reason": again.get("reason"),
        }

        # 2. update with the expected revision (history).
        current = store.read_current(
            "project-context", "qa-training-store", ARTIFACT_REF
        )
        second = persist_prepared(
            store,
            prepare_update(
                current["content"], current["revision"], f"refs/heads/main@{PINNED_SHA}"
            ),
            project_ref="qa-training-store",
            operation_id="acceptance-update-1",
            approval_ref=APPROVAL_REF,
            approval_revision=APPROVAL_REVISION,
        )
        assert second.get("status") == "stored", second
        git(writer, "push", "origin", BRANCH, token=token)
        head2 = git(writer, "rev-parse", "HEAD").stdout.strip()
        steps["write_2_update"] = {
            "result": {
                k: second[k]
                for k in ("status", "revision", "previous_revision", "sha256")
            },
            "activity": activity(token, args.repo, head2),
        }

        # 3. stale-writer conflict: a second clone at head2 is overtaken by the writer.
        stale = base / "stale"
        git(base, "clone", "-q", "--branch", BRANCH, url, str(stale), token=token)
        git(stale, "config", "user.name", "qa-workflow-skills")
        git(stale, "config", "user.email", "qa@example.invalid")
        current = store.read_current(
            "project-context", "qa-training-store", ARTIFACT_REF
        )
        third = persist_prepared(
            store,
            prepare_update(
                current["content"], current["revision"], "refs/heads/main@writer"
            ),
            project_ref="qa-training-store",
            operation_id="acceptance-update-2",
            approval_ref=APPROVAL_REF,
            approval_revision=APPROVAL_REVISION,
        )
        assert third.get("status") == "stored", third
        git(writer, "push", "origin", BRANCH, token=token)
        head3 = git(writer, "rev-parse", "HEAD").stdout.strip()
        stale_store = store_for(stale, authorizer(APPROVAL_REF, APPROVAL_REVISION))
        stale_current = stale_store.read_current(
            "project-context", "qa-training-store", ARTIFACT_REF
        )
        loser = persist_prepared(
            stale_store,
            prepare_update(
                stale_current["content"],
                stale_current["revision"],
                "refs/heads/main@stale",
            ),
            project_ref="qa-training-store",
            operation_id="acceptance-stale-update",
            approval_ref=APPROVAL_REF,
            approval_revision=APPROVAL_REVISION,
        )
        assert loser.get("status") == "stored", loser  # local write passes locally
        rejected = git(stale, "push", "origin", BRANCH, token=token, check=False)
        remote_head = git(
            writer, "ls-remote", "origin", f"refs/heads/{BRANCH}", token=token
        ).stdout.split()[0]
        steps["remote_cas_conflict"] = {
            "stale_push_returncode": rejected.returncode,
            "rejected": "rejected" in rejected.stderr
            or "non-fast-forward" in rejected.stderr,
            "remote_head_unchanged": remote_head == head3,
            "write_3_activity": activity(token, args.repo, head3),
        }

        # 4. unapproved write is refused and the ref is unchanged.
        denied_store = store_for(writer, authorizer("approval/other", "other"))
        before = git(writer, "rev-parse", "HEAD").stdout.strip()
        denied = persist_prepared(
            denied_store,
            prepare_update(
                store.read_current(
                    "project-context", "qa-training-store", ARTIFACT_REF
                )["content"],
                store.read_current(
                    "project-context", "qa-training-store", ARTIFACT_REF
                )["revision"],
                "refs/heads/main@denied",
            ),
            project_ref="qa-training-store",
            operation_id="acceptance-denied",
            approval_ref=APPROVAL_REF,
            approval_revision=APPROVAL_REVISION,
        )
        steps["unapproved_write"] = {
            "status": denied.get("status"),
            "reason": denied.get("reason"),
            "ref_unchanged": git(writer, "rev-parse", "HEAD").stdout.strip() == before,
        }

        # 5. independent readback from a fresh clone.
        fresh = base / "fresh"
        git(base, "clone", "-q", "--branch", BRANCH, url, str(fresh), token=token)
        reader = store_for(fresh, authorizer(APPROVAL_REF, APPROVAL_REVISION))
        readbacks = {}
        for name, written in (
            ("rev1", first),
            ("rev2", second),
            ("rev3", third),
        ):
            row = reader.read_revision(
                "project-context",
                "qa-training-store",
                ARTIFACT_REF,
                written["revision"],
            )
            readbacks[name] = {
                "revision": written["revision"],
                "sha256_matches_write": row is not None
                and row["sha256"] == written["sha256"]
                and hashlib.sha256(row["content"].encode("utf-8")).hexdigest()
                == written["sha256"],
            }
        current = reader.read_current(
            "project-context", "qa-training-store", ARTIFACT_REF
        )
        readbacks["current_is_latest_accepted"] = (
            current["revision"] == third["revision"]
        )
        readbacks["stale_write_not_in_remote"] = (
            "refs/heads/main@stale" not in current["content"]
        )
        steps["independent_readback"] = readbacks

    actors = {
        steps[key]["activity"]["actor"]
        for key in ("write_1_create", "write_2_update")
        if steps[key]["activity"]
    }
    steps["approver_check"] = {
        "expected_approver": args.approver,
        "observed_actors": sorted(actors),
        "matches": actors == {args.approver},
    }
    evidence["passed"] = all(
        [
            steps["write_1_create"]["activity"] is not None,
            steps["create_if_absent_again"]["status"] == "blocked",
            steps["remote_cas_conflict"]["rejected"],
            steps["remote_cas_conflict"]["remote_head_unchanged"],
            steps["unapproved_write"]["status"] == "blocked",
            steps["unapproved_write"]["ref_unchanged"],
            all(
                value["sha256_matches_write"]
                for key, value in steps["independent_readback"].items()
                if key.startswith("rev")
            ),
            steps["independent_readback"]["current_is_latest_accepted"],
            steps["independent_readback"]["stale_write_not_in_remote"],
            steps["approver_check"]["matches"],
        ]
    )
    args.out.write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0 if evidence["passed"] else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, StoreError, AssertionError) as exc:
        print(f"acceptance failed: {exc}", file=sys.stderr)
        raise SystemExit(2)
