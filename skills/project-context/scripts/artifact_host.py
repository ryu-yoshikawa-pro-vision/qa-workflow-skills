#!/usr/bin/env python3
"""Host CLI for the user-confirmed Git artifact store (Project Context / feature inventory).

Run directly: `python3 artifact_host.py <subcommand> ...`. Standard output is JSON,
one object per line. Errors are `{"status":"blocked","reason":...}` with a non-zero exit.

Ownership and limits:
- The canonical artifact is the Git commit on the selected branch of the given repository.
  The working tree, HEAD and index are never changed by save or init-branch.
- `export` writes a read-only projection copy. It is NOT the store: edits made by hand to
  the projection never reach the store. Use `verify-projection` to detect such drift.
- Saving goes only through `save-prepared`, which passes a prepared candidate from
  project_context.py to project_context.persist_prepared (16-section, project identity,
  previous-revision and approval checks). Arbitrary content is never written directly.
  `save-prepared` requires `--user-confirmed-ref`, a single-line reference to the user's
  explicit confirmation. The host registers that confirmation in this process and then
  writes. The confirmation is self-declared by the caller and is not authentication. The
  AI must not supply it before the user has confirmed the specific artifact.
- `read`, `export` and `verify-projection` also require `--user-confirmed-ref`. In the
  user-confirmed mode a read of a project is allowed only after a confirmation of that
  project is registered in the same process.
- Nothing here embeds a fixed repository path. Pass the repository path explicitly.

Branch operation guidance:
- One branch per (project, kind), for example `qa-artifacts/<project>/<kind>`. The
  revision of a Git branch is its commit SHA, so mixing kinds or projects on one branch
  makes the CAS revision cover unrelated artifacts.
- Create the branch with `init-branch` (plumbing only). The branch must not be checked
  out in the main worktree or in any linked worktree; the host refuses otherwise.
- Branch names match `[A-Za-z0-9._/-]+`.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import project_context
from artifact_store import USER_CONFIRMED, StoreError, _name
from git_artifact_store import (
    BRANCH,
    LINE_BREAKS,
    GitArtifactStore,
    branch_checked_out,
)

KINDS = ("project-context", "feature-inventory")
DEFAULT_AUTHOR_NAME = "qa-artifact-host"
DEFAULT_AUTHOR_EMAIL = "qa-artifact-host@example.invalid"
INIT_MESSAGE = "qa artifact: init"
# Git の「参照が存在しないこと」を表す空の旧値。update-ref は既存参照なら失敗する（create-if-absent）。
NO_PREVIOUS_REF = ""
MAX_REF = 1024


class HostError(Exception):
    """Reason code only; the message is printed as the blocked reason."""


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:  # type: ignore[override]
        raise HostError("arguments_invalid")


def _emit(payload: dict[str, Any], code: int = 0) -> int:
    sys.stdout.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
    return code


def _blocked(reason: str) -> int:
    return _emit({"status": "blocked", "reason": reason}, 1)


def _branch(value: Any) -> str:
    if (
        not isinstance(value, str)
        or not BRANCH.fullmatch(value)
        or value.startswith("-")
    ):
        raise HostError("branch_invalid")
    return value


def _single_line(value: Any, label: str) -> str:
    if value is None or not isinstance(value, str) or not value.strip():
        raise HostError(f"{label}_required")
    if (
        len(value) > MAX_REF
        or any(ord(ch) < 32 or ord(ch) == 127 for ch in value)
        or any(ch in LINE_BREAKS for ch in value)
    ):
        raise HostError(f"{label}_invalid")
    return value


def _kind(value: Any) -> str:
    if value not in KINDS:
        raise HostError("artifact_kind_invalid")
    return value


def _git(
    repo: Path,
    *args: str,
    stdin: bytes | None = None,
    env: dict[str, str] | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess[bytes]:
    run_env = dict(os.environ)
    if env:
        run_env.update(env)
    # 空のhooksPathを指定し、source repositoryのhook（reference-transaction等）を実行させない。
    # GitArtifactStore._git と同じ方式。
    with tempfile.TemporaryDirectory(prefix="qa-host-no-hooks-") as no_hooks:
        try:
            completed = subprocess.run(
                ["git", "-c", "core.hooksPath=" + no_hooks, "-C", str(repo), *args],
                input=stdin,
                capture_output=True,
                check=False,
                timeout=30,
                env=run_env,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise HostError("git_provider_unavailable") from exc
    if check and completed.returncode != 0:
        raise HostError("git_provider_command_failed")
    return completed


def _author_env(name: str, email: str) -> dict[str, str]:
    return {
        "GIT_AUTHOR_NAME": name,
        "GIT_AUTHOR_EMAIL": email,
        "GIT_COMMITTER_NAME": name,
        "GIT_COMMITTER_EMAIL": email,
    }


def _branch_exists(repo: Path, branch: str) -> bool:
    return (
        _git(
            repo, "show-ref", "--verify", "--quiet", "refs/heads/" + branch, check=False
        ).returncode
        == 0
    )


def _store(args: argparse.Namespace, approval_source: str | None) -> GitArtifactStore:
    return GitArtifactStore(
        Path(args.repo),
        Path(args.repo),
        _branch(args.branch),
        None,
        author_name=args.author_name,
        author_email=args.author_email,
        approval_source=approval_source,
    )


def _read_confirmation(args: argparse.Namespace, approval_ref: str) -> dict[str, Any]:
    # read記録は案件scopeだけを開く（書込みは許可しない）。
    return {
        "operation": "read",
        "kind": args.kind,
        "project_ref": args.project_ref,
        "artifact_ref": args.artifact_ref,
        "approval_ref": approval_ref,
    }


def _reader(args: argparse.Namespace) -> GitArtifactStore:
    approval_ref = _single_line(args.user_confirmed_ref, "user_confirmed_ref")
    store = _store(args, USER_CONFIRMED)
    store.record_user_confirmation(_read_confirmation(args, approval_ref))
    return store


def _author(name: Any, email: Any) -> tuple[str, str]:
    # GitArtifactStore.__init__ と同じ検査（制御文字・改行の拒否、email に @ を要求）。
    name = _name(name, "author_name")
    email = _name(email, "author_email")
    if "@" not in email:
        raise StoreError("author_email_invalid")
    return name, email


def cmd_init_branch(args: argparse.Namespace) -> int:
    repo = Path(args.repo)
    branch = _branch(args.branch)
    author_name, author_email = _author(args.author_name, args.author_email)
    ref = "refs/heads/" + branch
    if _git(repo, "check-ref-format", ref, check=False).returncode != 0:
        return _blocked("branch_invalid")
    if _branch_exists(repo, branch):
        return _emit({"status": "exists", "branch": branch})
    if branch_checked_out(repo, ref):
        return _blocked("branch_checked_out")
    # 空treeのroot commitを plumbing で作る。HEAD・index・作業ツリーには触れない。
    tree = _git(repo, "mktree", stdin=b"").stdout.decode("ascii").strip()
    author = _author_env(author_name, author_email)
    commit = (
        _git(
            repo,
            "commit-tree",
            tree,
            "-m",
            INIT_MESSAGE,
            env=author,
        )
        .stdout.decode("ascii")
        .strip()
    )
    created = _git(repo, "update-ref", ref, commit, NO_PREVIOUS_REF, check=False)
    if created.returncode != 0:
        if _branch_exists(repo, branch):
            return _emit({"status": "exists", "branch": branch})
        return _blocked("branch_init_failed")
    return _emit({"status": "created", "branch": branch, "commit": commit})


def _prepared_request(path: str) -> tuple[dict[str, Any], bytes]:
    """project_context.persist_prepared が受け取る preparation（prepare-* の要求JSON）を読む。"""
    try:
        raw = Path(path).read_bytes()
    except OSError:
        raise HostError("prepared_file_unavailable")
    if len(raw) > project_context.MAX_BYTES:
        raise HostError("prepared_file_too_large")
    try:
        request = json.loads(
            raw.decode("utf-8"), object_pairs_hook=project_context._pairs
        )
    except (UnicodeDecodeError, ValueError, RecursionError) as exc:
        raise HostError("prepared_file_invalid") from exc
    if not isinstance(request, dict):
        raise HostError("prepared_file_invalid")
    return request, raw


def _prepared_approval_revision(
    preparation: dict[str, Any], draft: dict[str, Any], digest: str
) -> str | None:
    # prepare-placement の草案は承認revisionを自身で持ち、persist_prepared がそれと一致を要求する。
    # それ以外は persist_prepared へ渡す値をホストが決める（既存の "sha256:<内容>" 形式）。
    if preparation.get("operation") == "prepare-placement":
        return draft.get("approval_revision")
    return "sha256:" + digest


def cmd_save_prepared(args: argparse.Namespace) -> int:
    approval_ref = _single_line(args.user_confirmed_ref, "user_confirmed_ref")
    if args.kind != "project-context":
        # feature-inventory は feature_registry.persist_snapshot（Git証跡・再分類の検証を含む）
        # を経由する必要がある。このターンでは安全に実装できないため明示的に拒否する。
        return _blocked("unsupported_kind_for_now")
    preparation, raw = _prepared_request(args.prepared_file)
    if preparation.get("artifact_ref") != args.artifact_ref:
        return _blocked("artifact_ref_mismatch")
    operation_id = args.operation_id or "prepared-" + hashlib.sha256(raw).hexdigest()
    # 草案は persist_prepared と同じ関数で作る（純粋な検証。書込みはしない）。
    draft = project_context.handle(preparation)
    if draft.get("status") != "draft":
        return _emit(
            {"status": "blocked", "reason": str(draft.get("reason") or "not_draft")}, 1
        )
    store = _store(args, USER_CONFIRMED)
    # 確認記録は persist_prepared が store.write へ渡す要求と同じキー・同じ値で登録する。
    # 値の導出は persist_prepared の実コードに従う（expected_revision は草案、source・change_reason は要求）。
    content = draft["artifact_markdown"]
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    approval_revision = _prepared_approval_revision(preparation, draft, digest)
    store.record_user_confirmation(_read_confirmation(args, approval_ref))
    store.record_user_confirmation(
        {
            "operation": "write",
            "kind": "project-context",
            "project_ref": args.project_ref,
            "artifact_ref": preparation.get("artifact_ref"),
            "expected_revision": draft.get("expected_revision"),
            "approval_ref": approval_ref,
            "sha256": digest,
            "approval_revision": approval_revision,
            "source_ref": preparation.get("source_ref"),
            "source_revision": preparation.get("source_revision"),
            "operation_id": operation_id,
            "change_reason": preparation.get("change_reason"),
        }
    )
    result = project_context.persist_prepared(
        store,
        preparation,
        project_ref=args.project_ref,
        operation_id=operation_id,
        approval_ref=approval_ref,
        approval_revision=approval_revision,
    )
    succeeded = result.get("status") in {"stored", "idempotent"}
    return _emit(result, 0 if succeeded else 1)


def _current(
    args: argparse.Namespace, store: GitArtifactStore
) -> dict[str, Any] | None:
    revision = getattr(args, "revision", None)
    if revision:
        return store.read_revision(
            args.kind, args.project_ref, args.artifact_ref, revision
        )
    return store.read_current(args.kind, args.project_ref, args.artifact_ref)


def cmd_read(args: argparse.Namespace) -> int:
    store = _reader(args)
    payload = _current(args, store)
    if payload is None:
        return _emit({"status": "absent", "artifact_ref": args.artifact_ref}, 1)
    return _emit({"status": "read", **payload})


def atomic_write(out: Path, data: bytes) -> None:
    """同じdirectoryの一時fileへ書き、fsyncの後にrenameする。失敗時は一時fileを残さない。"""
    if out.is_symlink() or out.is_dir():
        raise HostError("out_path_invalid")
    if not out.parent.is_dir():
        raise HostError("out_parent_missing")
    descriptor, temporary = tempfile.mkstemp(
        prefix="." + out.name + ".", suffix=".tmp", dir=str(out.parent)
    )
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        # 投影は読取専用の写しとして扱う（手編集の抑止の目安。正本は store）。
        os.chmod(temporary, 0o444)
        os.replace(temporary, out)
    except BaseException:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise
    try:
        directory = os.open(str(out.parent), os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(directory)
    except OSError:
        pass
    finally:
        os.close(directory)


def cmd_export(args: argparse.Namespace) -> int:
    store = _reader(args)
    payload = _current(args, store)
    if payload is None:
        return _emit({"status": "absent", "artifact_ref": args.artifact_ref}, 1)
    data = payload["content"].encode("utf-8")
    if hashlib.sha256(data).hexdigest() != payload["sha256"]:
        return _blocked("export_readback_mismatch")
    out = Path(args.out)
    if out.is_symlink() or out.is_dir():
        raise HostError("out_path_invalid")
    overwrote_drifted = False
    if out.is_file():
        # 既存の投影が store の現在内容と異なる（手編集などのずれ）場合は上書きしない。
        existing = hashlib.sha256(out.read_bytes()).hexdigest()
        if existing != payload["sha256"]:
            if not args.force:
                return _blocked("projection_drifted")
            overwrote_drifted = True
    atomic_write(out, data)
    written = out.read_bytes()
    if hashlib.sha256(written).hexdigest() != payload["sha256"]:
        return _blocked("export_readback_mismatch")
    result: dict[str, Any] = {
        "status": "exported",
        "out": str(out),
        "revision": payload["revision"],
        "sha256": payload["sha256"],
        "bytes": len(written),
    }
    if overwrote_drifted:
        result["overwrote_drifted"] = True
    return _emit(result)


def cmd_verify_projection(args: argparse.Namespace) -> int:
    store = _reader(args)
    payload = _current(args, store)
    if payload is None:
        return _emit({"status": "absent", "artifact_ref": args.artifact_ref}, 1)
    out = Path(args.out)
    if out.is_symlink() or not out.is_file():
        return _emit(
            {"status": "missing", "out": str(out), "revision": payload["revision"]}, 1
        )
    file_sha = hashlib.sha256(out.read_bytes()).hexdigest()
    status = "in_sync" if file_sha == payload["sha256"] else "drifted"
    return _emit(
        {
            "status": status,
            "out": str(out),
            "revision": payload["revision"],
            "store_sha256": payload["sha256"],
            "file_sha256": file_sha,
        }
    )


def _add_store_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--repo", required=True, help="absolute path of the Git repository"
    )
    parser.add_argument("--branch", required=True, help="branch name [A-Za-z0-9._/-]+")
    parser.add_argument("--project-ref", required=True, dest="project_ref")
    parser.add_argument("--kind", required=True, choices=KINDS)
    parser.add_argument(
        "--artifact-ref",
        required=True,
        dest="artifact_ref",
        help="e.g. docs/PROJECT_CONTEXT.md",
    )


def _add_author_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--author-name", default=DEFAULT_AUTHOR_NAME)
    parser.add_argument("--author-email", default=DEFAULT_AUTHOR_EMAIL)


def build_parser() -> argparse.ArgumentParser:
    parser = _Parser(
        prog="artifact_host.py",
        description=(
            "Host CLI for the user-confirmed Git artifact store. Output is JSON, one object per line. "
            "The store is the canonical artifact; `export` writes a read-only projection copy whose hand "
            "edits never reach the store (use verify-projection to detect drift). Save requires "
            "--user-confirmed-ref, which records a self-declared user confirmation (not authentication). "
            "Use one branch per (project, kind), for example qa-artifacts/<project>/<kind>, because the "
            "revision of a Git branch is its commit SHA."
        ),
    )
    sub = parser.add_subparsers(dest="command", required=True, parser_class=_Parser)

    init = sub.add_parser(
        "init-branch",
        help="create an empty root-commit branch with plumbing (no HEAD, index or worktree change)",
    )
    init.add_argument("--repo", required=True)
    init.add_argument("--branch", required=True)
    _add_author_arguments(init)
    init.set_defaults(handler=cmd_init_branch)

    save = sub.add_parser(
        "save-prepared",
        help="persist a prepared candidate via persist_prepared after registering the user confirmation",
        description=(
            "Persist one candidate prepared by project_context.py. --prepared-file is the prepare-* "
            "request JSON (operation prepare-create, prepare-sections, prepare-update, prepare-ids, "
            "prepare-placement) with artifact_ref, source_ref, source_revision, change_reason, and for "
            "updates markdown and expected_revision. Arbitrary content is not accepted. The 16-section "
            "structure, project identity, previous-revision match and DEC/ASM checks run in persist_prepared. "
            "Call only after the user has confirmed this exact candidate: --user-confirmed-ref is a "
            "self-declared confirmation, not authentication, and the AI must not pass it before that "
            "confirmation. feature-inventory is not supported yet (unsupported_kind_for_now)."
        ),
    )
    _add_store_arguments(save)
    save.add_argument(
        "--prepared-file",
        required=True,
        help="JSON file holding the prepare-* request that persist_prepared accepts",
    )
    save.add_argument(
        "--operation-id",
        help="idempotency key (default: prepared-<sha256 of the prepared file>)",
    )
    save.add_argument(
        "--user-confirmed-ref",
        required=True,
        help="single-line reference to the user's explicit confirmation of this exact candidate (self-declared; do not pass before the user confirms)",
    )
    _add_author_arguments(save)
    save.set_defaults(handler=cmd_save_prepared)

    read = sub.add_parser(
        "read", help="print the current (or given revision) content as JSON"
    )
    _add_store_arguments(read)
    read.add_argument("--revision", help="git:<sha> of a past revision")
    read.add_argument("--user-confirmed-ref", required=True)
    _add_author_arguments(read)
    read.set_defaults(handler=cmd_read)

    export = sub.add_parser(
        "export",
        help="write the current content byte-for-byte to --out (read-only projection; hand edits are not saved back; drifted files are not overwritten without --force)",
    )
    _add_store_arguments(export)
    export.add_argument(
        "--out",
        required=True,
        help=(
            "projection path; the parent directory must exist. Hand edits to this file never reach "
            "the store. An existing file whose content differs from the store is refused "
            "(projection_drifted) unless --force is given."
        ),
    )
    export.add_argument(
        "--force",
        action="store_true",
        help="overwrite an existing projection that has drifted from the store (output then has overwrote_drifted: true)",
    )
    export.add_argument("--user-confirmed-ref", required=True)
    _add_author_arguments(export)
    export.set_defaults(handler=cmd_export)

    verify = sub.add_parser(
        "verify-projection",
        help="compare the --out file with the store's current content (in_sync or drifted)",
    )
    _add_store_arguments(verify)
    verify.add_argument("--out", required=True)
    verify.add_argument("--user-confirmed-ref", required=True)
    _add_author_arguments(verify)
    verify.set_defaults(handler=cmd_verify_projection)
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        args = build_parser().parse_args(argv)
        return args.handler(args)
    except HostError as exc:
        return _blocked(str(exc))
    except StoreError as exc:
        return _blocked(str(exc))
    except OSError:
        return _blocked("host_io_failed")


if __name__ == "__main__":
    raise SystemExit(main())
