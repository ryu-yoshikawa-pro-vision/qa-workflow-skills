#!/usr/bin/env python3
"""Host CLI for the user-confirmed Git artifact store (Project Context / feature inventory).

Run directly: `python3 artifact_host.py <subcommand> ...`. Standard output is JSON,
one object per line. Errors are `{"status":"blocked","reason":...}` with a non-zero exit.

Ownership and limits:
- The canonical artifact is the Git commit on the selected branch of the given repository.
  The working tree, HEAD and index are never changed by save or init-branch.
- `export` writes a read-only projection copy. It is NOT the store: edits made by hand to
  the projection never reach the store. Use `verify-projection` to detect such drift.
- project-context is saved only through `save-prepared`, which passes a prepared candidate
  from project_context.py to project_context.persist_prepared (16-section, project identity,
  previous-revision and approval checks). feature-inventory is saved only through
  `save-snapshot`, which passes the snapshot to feature_registry.persist_snapshot (Git source
  evidence, reclassification approval, previous-snapshot checks). Arbitrary content is never
  written directly.
  `save-prepared` requires `--user-confirmed-ref`, a single-line reference to the user's
  explicit confirmation. The host registers that confirmation in this process and then
  writes. The confirmation is self-declared by the caller and is not authentication. The
  AI must not supply it before the user has confirmed the specific artifact.
- `read`, `export` and `verify-projection` also require `--user-confirmed-ref`. In the
  user-confirmed mode a read of a project is allowed only after a confirmation of that
  project is registered in the same process.
- spec-analysis and question-analysis documents are saved only through `save-document`
  (`--kind`, default spec-analysis). It validates the Markdown with the kind's validate
  first (spec_document or question_document), then calls the kind's persist_document.
  The same user-confirmed rules apply.
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
import importlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import project_context
from artifact_store import STORE_KINDS, USER_CONFIRMED, StoreError, _name
from git_artifact_store import (
    BRANCH,
    COMMIT,
    LINE_BREAKS,
    READ_ONLY_GIT_ENV,
    GitArtifactStore,
    _path,
    branch_checked_out,
)

KINDS = tuple(sorted(STORE_KINDS))
DEFAULT_AUTHOR_NAME = "qa-artifact-host"
DEFAULT_AUTHOR_EMAIL = "qa-artifact-host@example.invalid"
INIT_MESSAGE = "qa artifact: init"
# Git の「参照が存在しないこと」を表す空の旧値。update-ref は既存参照なら失敗する（create-if-absent）。
NO_PREVIOUS_REF = ""
MAX_REF = 1024
CONFIRMATION_KEYS = frozenset({"change_id", "approval_ref", "approval_revision"})
# 理由コードごとの原因の要約。reason は機械判定用、detail は利用者へ見せる説明。
REASON_DETAILS = {
    "snapshot_invalid:git_artifact_ref_invalid": (
        "artifact_ref は相対パスで、末尾が .md か .json である必要があります"
        "（絶対パス、.. や .git の区切り、バックスラッシュ、コロンを含めない）"
    ),
    "snapshot_invalid:field_missing": "snapshot の必須項目がないか、形式が契約と異なります",
    "snapshot_invalid:snapshot_nonfinite_number": "NaN と Infinity は保存できません",
    "snapshot_invalid:nonfinite_number": "NaN と Infinity は JSON の数値として受け付けません",
    "snapshot_invalid:text_not_utf8": (
        "文字列にUTF-8で表せない文字（孤立したサロゲート）が含まれます"
    ),
    "change_supersession_without_predecessor": (
        "supersedes_id を持つ変更行がありますが、前回snapshotに先行するDIFがありません"
        "（初回保存では supersedes_id を使えません）"
    ),
    "reclassification_invalid": (
        "再分類の決定を作れません（変更行または source の項目が不足しています）"
    ),
    "confirmed_reclassifications_invalid": (
        "--confirmed-reclassifications-file は"
        " [{change_id, approval_ref, approval_revision}] の配列である必要があります"
    ),
    "confirmed_reclassifications_duplicate": "change_id が確認表に重複しています",
}


class HostError(Exception):
    """Reason code only; the message is printed as the blocked reason."""


class _NonFiniteNumber(ValueError):
    """Raised by json.loads for NaN, Infinity and -Infinity."""


def _reject_nonfinite(_name: str) -> None:
    raise _NonFiniteNumber(_name)


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:  # type: ignore[override]
        raise HostError("arguments_invalid")


# 行区切りとして扱われる非ASCII文字（str.splitlines の対象）。JSON文字列の中でだけ現れるため、
# エスケープしても JSON の意味は変わらず、1オブジェクト1行の出力契約を守れる。
_LINE_BOUNDARY_ESCAPES = {"\x85": "\\u0085", "\u2028": "\\u2028", "\u2029": "\\u2029"}


def _emit(payload: dict[str, Any], code: int = 0) -> int:
    line = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    for raw, escaped in _LINE_BOUNDARY_ESCAPES.items():
        line = line.replace(raw, escaped)
    sys.stdout.write(line + "\n")
    return code


def _blocked(reason: str) -> int:
    payload: dict[str, Any] = {"status": "blocked", "reason": reason}
    detail = REASON_DETAILS.get(reason)
    if detail is None and reason.startswith("snapshot_invalid:"):
        detail = "snapshot の内容が契約に合いません（reason の理由コードを参照）"
    if detail is not None:
        payload["detail"] = detail
    return _emit(payload, 1)


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
    run_env = {**os.environ, **READ_ONLY_GIT_ENV}
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
        # feature-inventory は feature_registry.persist_snapshot（Git証跡・再分類の検証を含む）を
        # 経由する save-snapshot で保存する。ここ（persist_prepared 経由）では保存しない。
        return _emit(
            {
                "status": "blocked",
                "reason": "unsupported_kind_for_now",
                "hint": "feature-inventory is saved with save-snapshot",
            },
            1,
        )
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


def _feature_registry() -> Any:
    """feature_registry は feature-analysis の scripts にある。このコマンドでだけ読み込む。"""
    scripts = str(Path(__file__).resolve().parents[2] / "feature-analysis" / "scripts")
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    try:
        import feature_registry  # noqa: PLC0415
    except ImportError as exc:
        raise HostError("feature_analysis_unavailable") from exc
    return feature_registry


def _json_file(path: str, label: str) -> Any:
    feature_registry = _feature_registry()
    try:
        raw = Path(path).read_bytes()
    except OSError:
        raise HostError(f"{label}_unavailable")
    if len(raw) > feature_registry.MAX_INPUT:
        raise HostError(f"{label}_too_large")
    try:
        return json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=feature_registry._pairs,
            parse_constant=_reject_nonfinite,
        )
    except _NonFiniteNumber as exc:
        raise HostError(f"{label}_invalid:nonfinite_number") from exc
    except (UnicodeDecodeError, ValueError, RecursionError) as exc:
        raise HostError(f"{label}_invalid") from exc


def _confirmed_reclassifications(path: str | None) -> dict[str, tuple[str, str]]:
    """利用者が確認した再分類の表: change_id -> (approval_ref, approval_revision)。"""
    if path is None:
        return {}
    rows = _json_file(path, "confirmed_reclassifications")
    if not isinstance(rows, list):
        raise HostError("confirmed_reclassifications_invalid")
    table: dict[str, tuple[str, str]] = {}
    for row in rows:
        if not isinstance(row, dict) or set(row) != CONFIRMATION_KEYS:
            raise HostError("confirmed_reclassifications_invalid")
        change_id = _single_line(row["change_id"], "confirmed_change_id")
        approval = (
            _single_line(row["approval_ref"], "confirmed_approval_ref"),
            _single_line(row["approval_revision"], "confirmed_approval_revision"),
        )
        if change_id in table:
            raise HostError("confirmed_reclassifications_duplicate")
        table[change_id] = approval
    return table


def _unconfirmed_reclassifications(
    decisions: list[dict[str, Any]], confirmed: dict[str, tuple[str, str]]
) -> list[dict[str, str]]:
    """表と完全一致しない再分類を返す。表に無い、または承認参照／revisionが違うもの。"""
    unconfirmed: list[dict[str, str]] = []
    for decision in decisions:
        change_id = decision["change_id"]
        entry = confirmed.get(change_id)
        if entry is None:
            reason = "not_listed"
        elif entry[0] != decision["approval_ref"]:
            reason = "approval_ref_mismatch"
        elif entry[1] != decision["approval_revision"]:
            reason = "approval_revision_mismatch"
        else:
            continue
        unconfirmed.append({"change_id": change_id, "reason": reason})
    return unconfirmed


def _trusted_authorized_roots(requests: list[Any] | None) -> None:
    """save-snapshot の code source は、信頼済みの環境変数 QA_FEATURE_AUTHORIZED_ROOT で許可された
    root だけを読む（feature-analysis data-contract の Git CLI 入口と同じ規則）。入力JSONの
    authorized_root だけでは読取りを主張できないため、各 entry を環境変数の root と照合する。
    """
    if requests is None:
        return
    trusted = os.environ.get("QA_FEATURE_AUTHORIZED_ROOT")
    if not trusted:
        raise HostError("trusted_authorized_root_missing")
    try:
        trusted_root = Path(trusted).resolve(strict=True)
    except (OSError, ValueError) as exc:
        raise HostError("trusted_authorized_root_unavailable") from exc
    for entry in requests:
        if not isinstance(entry, dict) or not isinstance(
            entry.get("authorized_root"), str
        ):
            raise HostError("trusted_authorized_root_mismatch")
        try:
            allowed = Path(entry["authorized_root"]).resolve(strict=True)
        except (OSError, ValueError) as exc:
            raise HostError("trusted_authorized_root_unavailable") from exc
        if allowed != trusted_root:
            raise HostError("trusted_authorized_root_mismatch")


def _git_path_option(repo: Path, option: str) -> Path | None:
    """`git rev-parse <option>` の結果を、symlink解決後の絶対パスで返す（読取りのみ）。"""
    completed = _git(repo, "rev-parse", option, check=False)
    if completed.returncode != 0:
        return None
    try:
        raw = completed.stdout.decode("utf-8").strip()
    except UnicodeDecodeError:
        return None
    if not raw:
        return None
    path = Path(raw)
    if not path.is_absolute():
        path = repo / path
    try:
        return path.resolve(strict=True)
    except (OSError, ValueError):
        return None


def _repo_identity(repo: Path) -> tuple[Path, Path, Path] | None:
    """repo を含む作業ツリーの (toplevel, common git dir, absolute git dir) を返す。

    判定できなければ None。読取りだけを行う（READ_ONLY_GIT_ENV の GIT_OPTIONAL_LOCKS=0）。
    """
    top = _git_path_option(repo, "--show-toplevel")
    common = _git_path_option(repo, "--git-common-dir")
    gitdir = _git_path_option(repo, "--absolute-git-dir")
    if top is None or common is None or gitdir is None:
        return None
    return top, common, gitdir


def _refuse_store_inside_source(repo: Path, requests: list[Any] | None) -> None:
    """保存先（store）が読取り元（source）の .git に書き込みうる配置なら拒否する。

    拒否するのは次の場合だけ:
    (a) store と source が同一のGitリポジトリ（common git dir または absolute git dir が一致）。
    (b) store の toplevel が source の toplevel の配下（store が source の作業ツリー内にある）。
    source が store の配下にあっても、source が独自の .git を持つ独立したリポジトリなら許可する。
    判定に失敗した場合は拒否する（fail closed）。
    """
    if not requests:
        return
    try:
        store = _repo_identity(repo)
    except HostError as exc:
        raise HostError("store_source_relation_unverifiable") from exc
    if store is None:
        raise HostError("store_source_relation_unverifiable")
    store_top, store_common, store_gitdir = store
    for entry in requests:
        if not isinstance(entry, dict) or not isinstance(
            entry.get("repository_root"), str
        ):
            continue
        try:
            source_root = Path(entry["repository_root"]).resolve(strict=True)
            source = _repo_identity(source_root)
        except (OSError, ValueError, HostError) as exc:
            raise HostError("store_source_relation_unverifiable") from exc
        if source is None:
            raise HostError("store_source_relation_unverifiable")
        source_top, source_common, source_gitdir = source
        same_repository = store_common == source_common or store_gitdir == source_gitdir
        store_in_source_tree = store_top == source_top or store_top.is_relative_to(
            source_top
        )
        if same_repository or store_in_source_tree:
            raise HostError("store_repo_is_source_repo")


def _expected_snapshot_revision(value: str) -> str | None:
    if value == "none":
        return None
    if value.startswith("git:") and COMMIT.fullmatch(value[4:]):
        return value
    raise HostError("expected_revision_invalid")


def cmd_save_snapshot(args: argparse.Namespace) -> int:
    feature_registry = _feature_registry()
    approval_ref = _single_line(args.user_confirmed_ref, "user_confirmed_ref")
    change_reason = _single_line(args.change_reason, "change_reason")
    expected = _expected_snapshot_revision(args.expected_revision)
    snapshot = _json_file(args.snapshot_file, "snapshot")
    if not isinstance(snapshot, dict):
        raise HostError("snapshot_invalid")
    previous = None
    if args.previous_snapshot_file is not None:
        previous = _json_file(args.previous_snapshot_file, "previous_snapshot")
        if not isinstance(previous, dict):
            raise HostError("previous_snapshot_invalid")
    requests = _json_file(args.git_inventory_requests_file, "git_inventory_requests")
    if requests is not None and not isinstance(requests, list):
        raise HostError("git_inventory_requests_invalid")
    confirmed = _confirmed_reclassifications(args.confirmed_reclassifications_file)
    _trusted_authorized_roots(requests)
    _refuse_store_inside_source(Path(args.repo), requests)
    if snapshot.get("project_ref") != args.project_ref:
        return _blocked("project_ref_mismatch")
    if args.operation_id is not None and args.operation_id != snapshot.get(
        "operation_id"
    ):
        return _blocked("operation_id_mismatch")
    request = {
        "snapshot": snapshot,
        "previous_snapshot": previous,
        "observed_head_revision": args.observed_head_revision,
    }
    # 確認記録は persist_snapshot が store へ渡す認可要求と同じキー・同じ値で登録する。
    # 値は feature_registry（snapshot_content・reclassification_decisions）と
    # GitArtifactStore.write の実コードから導く。ホストが独自に値を組み立てない。
    try:
        content = feature_registry.snapshot_content(snapshot)
    except feature_registry.ContractError as exc:
        return _blocked(f"snapshot_invalid:{exc}")
    try:
        digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    except UnicodeEncodeError:
        return _blocked("snapshot_invalid:text_not_utf8")
    approval_revision = "sha256:" + digest
    try:
        artifact_ref = _path(snapshot["artifact_ref"])
        write_record = {
            "operation": "write",
            "kind": "feature-inventory",
            "project_ref": args.project_ref,
            "artifact_ref": artifact_ref,
            "expected_revision": expected,
            "sha256": digest,
            "source_ref": args.project_ref,
            "source_revision": snapshot["source_revision"],
            "approval_ref": approval_ref,
            "approval_revision": approval_revision,
            "operation_id": snapshot["operation_id"],
            "change_reason": change_reason,
        }
    except KeyError:
        return _blocked("snapshot_invalid:field_missing")
    except StoreError as exc:
        return _blocked(f"snapshot_invalid:{exc}")
    try:
        decisions = feature_registry.reclassification_decisions(request, expected)
    except feature_registry.ContractError as exc:
        return _blocked(str(exc))
    except (KeyError, TypeError, ValueError, StopIteration, AttributeError):
        return _blocked("reclassification_invalid")
    # 再分類は利用者が確認した表と change_id・承認参照・revision が完全一致するものだけ認める。
    # 1件でも一致しなければ保存しない（表は自己申告であり、認証ではない）。
    unconfirmed = _unconfirmed_reclassifications(decisions, confirmed)
    if unconfirmed:
        return _emit(
            {
                "status": "blocked",
                "reason": "reclassification_not_confirmed",
                "unconfirmed": unconfirmed,
                "reasons": [
                    f"reclassification_not_confirmed:{row['change_id']}:{row['reason']}"
                    for row in unconfirmed
                ],
            },
            1,
        )
    store = _store(args, USER_CONFIRMED)
    store.record_user_confirmation(write_record)
    for decision in decisions:
        store.record_user_confirmation(decision)
    result = feature_registry.persist_snapshot(
        store,
        request,
        expected_revision=expected,
        approval_ref=approval_ref,
        approval_revision=approval_revision,
        change_reason=change_reason,
        git_inventory_requests=requests,
        hold_source_refs=args.hold_source_refs,
    )
    succeeded = result.get("status") in {"stored", "idempotent"}
    return _emit(result, 0 if succeeded else 1)


# 文書 kind ごとの検証・保存 module。各 module は自分の skill の scripts にある。
DOCUMENT_MODULES = {
    "spec-analysis": "spec_document",
    "question-analysis": "question_document",
}


def _document_module(kind: str) -> Any:
    """文書 kind の module を、その skill の scripts から読み込む。このコマンドでだけ読み込む。"""
    name = DOCUMENT_MODULES[kind]
    scripts = str(Path(__file__).resolve().parents[2] / kind / "scripts")
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    try:
        return importlib.import_module(name)
    except ImportError as exc:
        raise HostError(f"{name}_unavailable") from exc


def _document_text(path: str, limit: int) -> str:
    try:
        raw = Path(path).read_bytes()
    except OSError:
        raise HostError("document_file_unavailable")
    if len(raw) > limit:
        raise HostError("document_file_too_large")
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        raise HostError("encoding_invalid")


def _expected_document_revision(value: str | None) -> str | None:
    if value is None:
        return None
    if value.startswith("git:") and COMMIT.fullmatch(value[4:]):
        return value
    raise HostError("expected_revision_invalid")


def cmd_save_document(args: argparse.Namespace) -> int:
    """spec-analysis / question-analysis の文書を検証してから保存する。確認記録は検証の通過後にだけ登録する。"""
    kind = args.kind
    doc = _document_module(kind)
    approval_ref = _single_line(args.user_confirmed_ref, "user_confirmed_ref")
    source_ref = _single_line(args.source_ref, "source_ref")
    source_revision = _single_line(args.source_revision, "source_revision")
    change_reason = _single_line(args.change_reason, "change_reason")
    expected = _expected_document_revision(args.expected_revision)
    markdown = _document_text(args.document_file, doc.MAX_BYTES)
    prefix, suffix = f"{kind}/", ".md"
    scope_id = None
    if args.artifact_ref.startswith(prefix) and args.artifact_ref.endswith(suffix):
        scope_id = args.artifact_ref[len(prefix) : -len(suffix)]
    report = doc.validate(markdown, scope_id, source_revision)
    if report["status"] != "valid":
        # 検証が通らなければ store に触れず、確認記録も登録しない。
        return _emit(
            {
                "status": "blocked",
                "reason": report["reasons"][0],
                "reasons": report["reasons"],
            },
            1,
        )
    if args.operation_id is not None:
        operation_id = _single_line(args.operation_id, "operation_id")
    else:
        digest = hashlib.sha256(
            markdown.encode("utf-8") + b"\n" + (expected or "none").encode("ascii")
        )
        operation_id = kind.split("-", 1)[0] + "-" + digest.hexdigest()[:32]
    # 確認記録は persist_document が store.write へ渡す要求と同じキー・同じ値で登録する。
    record = doc.write_confirmation_record(
        project_ref=args.project_ref,
        artifact_ref=args.artifact_ref,
        expected_revision=expected,
        approval_ref=approval_ref,
        markdown=markdown,
        source_ref=source_ref,
        source_revision=source_revision,
        operation_id=operation_id,
        change_reason=change_reason,
    )
    store = _store(args, USER_CONFIRMED)
    store.record_user_confirmation(record)
    result = doc.persist_document(
        store,
        {
            "project_ref": args.project_ref,
            "scope_id": scope_id,
            "markdown": markdown,
        },
        artifact_ref=args.artifact_ref,
        expected_revision=expected,
        operation_id=operation_id,
        approval_ref=approval_ref,
        approval_revision=record["approval_revision"],
        change_reason=change_reason,
        source_ref=source_ref,
        source_revision=source_revision,
    )
    succeeded = result.get("status") in {"stored", "idempotent"}
    if not succeeded and "reason" not in result:
        result["reason"] = result["reasons"][0]
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
            "confirmation. feature-inventory is saved with save-snapshot (unsupported_kind_for_now here)."
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

    snapshot = sub.add_parser(
        "save-snapshot",
        help="persist a feature-inventory snapshot via feature_registry.persist_snapshot",
        description=(
            "Persist one feature-inventory snapshot (kind feature-inventory) to the store branch. "
            "--snapshot-file is the snapshot object; --previous-snapshot-file is the previous saved "
            "snapshot (omit for the first save, which requires --expected-revision none). "
            "--git-inventory-requests-file is the JSON list of git_inventory_requests entries "
            "(source_id, repository_root, authorized_root, base_sha, head_sha, ...), or null when the "
            "snapshot has no code source. Each authorized_root must equal the trusted root in the "
            "QA_FEATURE_AUTHORIZED_ROOT environment variable. The store must not be the same Git repository "
            "as the source, nor inside the source's working tree (store_repo_is_source_repo); a source that "
            "is an independent repository nested inside the store is allowed. An undeterminable relation is "
            "refused (store_source_relation_unverifiable). The source Git "
            "trees are re-read by persist_snapshot. "
            "--observed-head-revision is the head the caller observed; it must equal the snapshot "
            "source_revision (otherwise stale). The host registers, in this process only, the write "
            "and each reclassification request that persist_snapshot will send to the store, then "
            "saves. Each reclassification must also appear in --confirmed-reclassifications-file with the "
            "same change_id, approval_ref and approval_revision, or the save is refused "
            "(reclassification_not_confirmed). --user-confirmed-ref is a self-declared confirmation of this "
            "exact snapshot (not authentication); the AI must not pass it before the user has confirmed. By default "
            "no ref lock is written into the source repository; --hold-source-refs restores the lock "
            "behaviour."
        ),
    )
    snapshot.add_argument(
        "--repo", required=True, help="absolute path of the store Git repository"
    )
    snapshot.add_argument(
        "--branch", required=True, help="branch name [A-Za-z0-9._/-]+"
    )
    snapshot.add_argument("--project-ref", required=True, dest="project_ref")
    snapshot.add_argument("--snapshot-file", required=True)
    snapshot.add_argument("--previous-snapshot-file")
    snapshot.add_argument("--git-inventory-requests-file", required=True)
    snapshot.add_argument(
        "--expected-revision",
        required=True,
        help="none (create-if-absent) or git:<sha> of the previous saved revision",
    )
    snapshot.add_argument(
        "--observed-head-revision",
        required=True,
        help=(
            "source head observed by the caller; must equal the snapshot source_revision (otherwise stale). "
            "This is only a self-consistency check against the snapshot. When there is no code source "
            "(--git-inventory-requests-file is null) there is no independent check of HEAD."
        ),
    )
    snapshot.add_argument("--change-reason", required=True)
    snapshot.add_argument(
        "--confirmed-reclassifications-file",
        help=(
            "JSON array of [{change_id, approval_ref, approval_revision}] that the user confirmed for "
            "the reclassifications of this snapshot. Each reclassification must match one entry exactly "
            "(change_id, approval_ref, approval_revision), or the save is refused with "
            "reclassification_not_confirmed. Not needed for an initial snapshot without reclassifications."
        ),
    )
    snapshot.add_argument(
        "--user-confirmed-ref",
        required=True,
        help="single-line reference to the user's explicit confirmation of this snapshot (self-declared; do not pass before the user confirms)",
    )
    snapshot.add_argument(
        "--operation-id",
        help="must equal the snapshot operation_id when given (default: the snapshot's)",
    )
    snapshot.add_argument(
        "--hold-source-refs",
        action="store_true",
        help="hold the source repository's HEAD and branch ref locks during verification and write (writes lock files into the source .git)",
    )
    _add_author_arguments(snapshot)
    snapshot.set_defaults(handler=cmd_save_snapshot)

    document = sub.add_parser(
        "save-document",
        help="validate and persist a spec-analysis or question-analysis document",
        description=(
            "Persist one Markdown document of --kind (spec-analysis or question-analysis; default "
            "spec-analysis) to the store branch. --artifact-ref must be <kind>/<scope-id>.md. "
            "--document-file is validated first (the kind's validate, read-only); a document that fails validation is not written and "
            "no confirmation is registered. --expected-revision is git:<sha> of the current revision; "
            "omit it to create. The store's CAS, idempotency and independent readback apply. "
            "--user-confirmed-ref is a self-declared confirmation of this exact document (not "
            "authentication); the AI must not pass it before the user has confirmed the document."
        ),
    )
    document.add_argument(
        "--repo", required=True, help="absolute path of the store Git repository"
    )
    document.add_argument(
        "--branch", required=True, help="branch name [A-Za-z0-9._/-]+"
    )
    document.add_argument(
        "--kind",
        default="spec-analysis",
        choices=sorted(DOCUMENT_MODULES),
        help="document kind (default spec-analysis)",
    )
    document.add_argument("--project-ref", required=True, dest="project_ref")
    document.add_argument(
        "--artifact-ref",
        required=True,
        dest="artifact_ref",
        help="<kind>/<scope-id>.md (for example spec-analysis/<scope-id>.md)",
    )
    document.add_argument(
        "--document-file", required=True, help="Markdown file of the document"
    )
    document.add_argument(
        "--expected-revision",
        help="git:<sha> of the current revision (omit to create the artifact)",
    )
    document.add_argument(
        "--operation-id",
        help="idempotency key (default: <spec|question>-<sha256 of the document and expected revision>)",
    )
    document.add_argument("--source-ref", required=True, dest="source_ref")
    document.add_argument("--source-revision", required=True, dest="source_revision")
    document.add_argument("--change-reason", required=True, dest="change_reason")
    document.add_argument(
        "--user-confirmed-ref",
        required=True,
        help="single-line reference to the user's explicit confirmation of this document (self-declared; do not pass before the user confirms)",
    )
    _add_author_arguments(document)
    document.set_defaults(handler=cmd_save_document)

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
