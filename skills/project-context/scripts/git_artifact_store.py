"""Git-backed canonical Markdown provider with commit-SHA CAS and history.

The trusted host chooses an authorized local Git repository, branch, path and
authorizer. Writes update Git objects and the selected ref atomically; no
secondary SQLite/Markdown canonical copy is created. The working tree is not
changed and must not be mistaken for the current Git-branch artifact.
"""

from __future__ import annotations

import hashlib
import os
import re
import subprocess
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any

from artifact_store import Authorization, StoreError, _check_root, _name

COMMIT = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")
BRANCH = re.compile(r"[A-Za-z0-9._/-]+\Z")
MAX_BYTES = 16 * 1024 * 1024


def _path(ref: str) -> str:
    ref = _name(ref, "artifact_ref")
    path = PurePosixPath(ref)
    if (
        path.is_absolute()
        or ref.startswith("-")
        or "\\" in ref
        or ":" in ref
        or path.as_posix() != ref
        or any(part in {".", "..", ".git"} for part in ref.split("/"))
        or not ref.endswith((".md", ".json"))
    ):
        raise StoreError("git_artifact_ref_invalid")
    return ref


class GitArtifactStore:
    """Git ref is the canonical owner; commit SHA is its native CAS revision."""

    def __init__(
        self,
        repository_root: Path,
        authorized_root: Path,
        branch: str,
        authorize: Authorization,
        *,
        author_name: str,
        author_email: str,
    ) -> None:
        self.root = _check_root(repository_root, authorized_root)
        if not callable(authorize):
            raise StoreError("trusted_authorizer_required")
        self.authorize = authorize
        # Git ref transactions must not invoke hooks from a source repository.
        self._empty_hooks = tempfile.TemporaryDirectory(prefix="qa-git-no-hooks-")
        self.branch = _name(branch, "branch")
        if not BRANCH.fullmatch(self.branch):
            raise StoreError("branch_invalid")
        self.ref = "refs/heads/" + self.branch
        self.author_name = _name(author_name, "author_name")
        self.author_email = _name(author_email, "author_email")
        if "@" not in self.author_email:
            raise StoreError("author_email_invalid")
        top = self._git("rev-parse", "--show-toplevel")
        assert top is not None
        if Path(top.decode().strip()).resolve(strict=True) != self.root:
            raise StoreError("git_repository_root_mismatch")
        gitdir = self._git("rev-parse", "--absolute-git-dir")
        assert gitdir is not None
        metadata = Path(gitdir.decode().strip()).resolve(strict=True)
        if not metadata.is_relative_to(self.root):
            raise StoreError("git_metadata_outside_authorized_root")
        self._git("check-ref-format", "--branch", self.branch)
        self._head()

    def _git(
        self,
        *args: str,
        content: bytes | None = None,
        index: Path | None = None,
        allow_failure: bool = False,
    ) -> bytes | None:
        env = dict(os.environ)
        if index is not None:
            env["GIT_INDEX_FILE"] = str(index)
        env["GIT_AUTHOR_NAME"] = self.author_name
        env["GIT_AUTHOR_EMAIL"] = self.author_email
        env["GIT_COMMITTER_NAME"] = self.author_name
        env["GIT_COMMITTER_EMAIL"] = self.author_email
        try:
            completed = subprocess.run(
                [
                    "git",
                    "-c",
                    "core.hooksPath=" + self._empty_hooks.name,
                    "-c",
                    "core.fsmonitor=false",
                    "-C",
                    str(self.root),
                    *args,
                ],
                input=content,
                capture_output=True,
                check=False,
                timeout=30,
                env=env,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise StoreError("git_provider_unavailable") from exc
        if completed.returncode != 0:
            if allow_failure:
                return None
            raise StoreError("git_provider_command_failed")
        if len(completed.stdout) > MAX_BYTES + 1024:
            raise StoreError("git_provider_output_too_large")
        return completed.stdout

    def _head(self) -> str:
        raw = self._git("rev-parse", "--verify", self.ref + "^{commit}")
        assert raw is not None
        head = raw.decode("ascii").strip()
        if not COMMIT.fullmatch(head):
            raise StoreError("git_head_invalid")
        return head

    def _permission(
        self,
        action: str,
        kind: str,
        project_ref: str,
        artifact_ref: str,
        revision: str | None,
        *,
        approval_ref: str | None = None,
        digest: str | None = None,
    ) -> None:
        try:
            allowed = self.authorize(
                {
                    "operation": action,
                    "kind": kind,
                    "project_ref": project_ref,
                    "artifact_ref": artifact_ref,
                    "expected_revision": revision,
                    "approval_ref": approval_ref,
                    "sha256": digest,
                }
            )
        except Exception as exc:
            raise StoreError("approval_provider_unavailable") from exc
        if allowed is not True:
            raise StoreError("access_denied")

    def _identity(self, kind: str, project_ref: str, artifact_ref: str) -> str:
        if kind not in {"project-context", "feature-inventory"}:
            raise StoreError("artifact_kind_invalid")
        _name(project_ref, "project_ref")
        return _path(artifact_ref)

    def _read_at(
        self, kind: str, project_ref: str, path: str, sha: str
    ) -> dict[str, Any] | None:
        raw = self._git("show", f"{sha}:{path}", allow_failure=True)
        if raw is None:
            return None
        if len(raw) > MAX_BYTES:
            raise StoreError("artifact_content_too_large")
        try:
            content = raw.decode("utf-8")
        except UnicodeError as exc:
            raise StoreError("artifact_readback_encoding_invalid") from exc
        parents = self._git("rev-list", "--parents", "-n", "1", sha)
        assert parents is not None
        parts = parents.decode("ascii").split()
        return {
            "kind": kind,
            "project_ref": project_ref,
            "artifact_ref": path,
            "revision": "git:" + sha,
            "previous_revision": "git:" + parts[1] if len(parts) > 1 else None,
            "sha256": hashlib.sha256(raw).hexdigest(),
            "content": content,
        }

    def read_current(
        self, kind: str, project_ref: str, artifact_ref: str
    ) -> dict[str, Any] | None:
        path = self._identity(kind, project_ref, artifact_ref)
        head = self._head()
        self._permission("read", kind, project_ref, path, "git:" + head)
        return self._read_at(kind, project_ref, path, head)

    def read_revision(
        self, kind: str, project_ref: str, artifact_ref: str, revision: str
    ) -> dict[str, Any] | None:
        path = self._identity(kind, project_ref, artifact_ref)
        if not isinstance(revision, str) or not revision.startswith("git:"):
            raise StoreError("revision_invalid")
        sha = revision[4:]
        if not COMMIT.fullmatch(sha):
            raise StoreError("revision_invalid")
        self._permission("read", kind, project_ref, path, revision)
        head = self._head()
        reachable = self._git(
            "merge-base", "--is-ancestor", sha, head, allow_failure=True
        )
        if reachable is None:
            raise StoreError("revision_not_in_authorized_history")
        return self._read_at(kind, project_ref, path, sha)

    def write(
        self,
        *,
        kind: str,
        project_ref: str,
        artifact_ref: str,
        content: str,
        expected_revision: str | None,
        operation_id: str,
        source_ref: str,
        source_revision: str,
        approval_ref: str,
        approval_revision: str,
        change_reason: str,
    ) -> dict[str, Any]:
        path = self._identity(kind, project_ref, artifact_ref)
        operation_id = _name(operation_id, "operation_id")
        source_ref = _name(source_ref, "source_ref")
        source_revision = _name(source_revision, "source_revision")
        approval_ref = _name(approval_ref, "approval_ref")
        approval_revision = _name(approval_revision, "approval_revision")
        change_reason = _name(change_reason, "change_reason")
        if not isinstance(content, str):
            raise StoreError("artifact_content_invalid")
        raw = content.encode("utf-8")
        if len(raw) > MAX_BYTES:
            raise StoreError("artifact_content_too_large")
        digest = hashlib.sha256(raw).hexdigest()
        head = self._head()
        self._permission(
            "write",
            kind,
            project_ref,
            path,
            expected_revision,
            approval_ref=approval_ref,
            digest=digest,
        )
        current = self._read_at(kind, project_ref, path, head)
        same_operation = False
        if current is not None and current["content"] == content:
            last_message = self._git("log", "-1", "--format=%B", head)
            assert last_message is not None
            trailers = last_message.decode("utf-8").splitlines()
            same_operation = all(
                f"{key}: {value}" in trailers
                for key, value in (
                    ("QA-Operation-Id", operation_id),
                    ("QA-Project-Ref", project_ref),
                    ("QA-Source-Ref", source_ref),
                    ("QA-Source-Revision", source_revision),
                    ("QA-Approval-Ref", approval_ref),
                    ("QA-Approval-Revision", approval_revision),
                    ("QA-Change-Reason", change_reason),
                )
            )
        if expected_revision is None:
            if current is not None:
                parent = current["previous_revision"]
                existed_before = (
                    parent is not None
                    and self._read_at(kind, project_ref, path, parent[4:]) is not None
                )
                if same_operation and not existed_before:
                    return {
                        "status": "idempotent",
                        "artifact_ref": path,
                        "revision": current["revision"],
                        "previous_revision": parent,
                        "sha256": digest,
                        "source_revision": source_revision,
                        "approval_ref": approval_ref,
                    }
                raise StoreError("create_if_absent_conflict")
        elif expected_revision != "git:" + head:
            if (
                same_operation
                and current is not None
                and current["previous_revision"] == expected_revision
            ):
                return {
                    "status": "idempotent",
                    "artifact_ref": path,
                    "revision": current["revision"],
                    "previous_revision": expected_revision,
                    "sha256": digest,
                    "source_revision": source_revision,
                    "approval_ref": approval_ref,
                }
            raise StoreError("revision_conflict")
        if current is not None and current["content"] == content:
            raise StoreError("unchanged_artifact_write")
        blob = self._git("hash-object", "-w", "--stdin", content=raw)
        assert blob is not None
        blob_sha = blob.decode("ascii").strip()
        if not COMMIT.fullmatch(blob_sha):
            raise StoreError("git_blob_invalid")
        with tempfile.TemporaryDirectory(prefix="qa-git-index-") as folder:
            index = Path(folder) / "index"
            self._git("read-tree", head, index=index)
            self._git(
                "update-index",
                "--add",
                "--cacheinfo",
                "100644",
                blob_sha,
                path,
                index=index,
            )
            tree = self._git("write-tree", index=index)
        assert tree is not None
        tree_sha = tree.decode("ascii").strip()
        message = (
            f"qa artifact: {kind} {path}\n\n"
            f"QA-Operation-Id: {operation_id}\n"
            f"QA-Project-Ref: {project_ref}\n"
            f"QA-Source-Ref: {source_ref}\n"
            f"QA-Source-Revision: {source_revision}\n"
            f"QA-Approval-Ref: {approval_ref}\n"
            f"QA-Approval-Revision: {approval_revision}\n"
            f"QA-Change-Reason: {change_reason}\n"
        )
        commit_raw = self._git(
            "commit-tree", tree_sha, "-p", head, content=message.encode("utf-8")
        )
        assert commit_raw is not None
        new_sha = commit_raw.decode("ascii").strip()
        if not COMMIT.fullmatch(new_sha):
            raise StoreError("git_commit_invalid")
        updated = self._git("update-ref", self.ref, new_sha, head, allow_failure=True)
        if updated is None:
            raise StoreError("revision_conflict")
        history = self.read_revision(kind, project_ref, path, "git:" + new_sha)
        if (
            history is None
            or history["content"] != content
            or history["sha256"] != digest
        ):
            raise StoreError("independent_readback_mismatch")
        return {
            "status": "stored",
            "artifact_ref": path,
            "revision": history["revision"],
            "previous_revision": "git:" + head,
            "sha256": digest,
            "source_revision": source_revision,
            "approval_ref": approval_ref,
        }
