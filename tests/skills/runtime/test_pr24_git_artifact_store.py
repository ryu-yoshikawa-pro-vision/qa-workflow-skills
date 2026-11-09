"""Isolated Git-native canonical Markdown and feature inventory CAS tests."""

from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[3] / "skills"
sys.path.insert(0, str(SKILL_ROOT / "project-context" / "scripts"))
sys.path.insert(0, str(SKILL_ROOT / "feature-analysis" / "scripts"))

from artifact_store import StoreError  # noqa: E402
from feature_registry import persist_snapshot  # noqa: E402
from git_artifact_store import GitArtifactStore  # noqa: E402
from project_context import handle as context_handle  # noqa: E402
from project_context import persist_prepared  # noqa: E402
from test_feature_registry import fixture  # noqa: E402


def git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


class GitArtifactStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        git(self.root, "init", "-q")
        git(self.root, "config", "user.email", "qa@example.invalid")
        git(self.root, "config", "user.name", "QA")
        (self.root / "README.md").write_text("original\n", encoding="utf-8")
        git(self.root, "add", ".")
        git(self.root, "commit", "-qm", "baseline")
        git(self.root, "branch", "qa-artifacts")
        self.allowed_projects = {"Sample"}
        self.allow_write = True

        def authorize(request: dict) -> bool:
            if request["project_ref"] not in self.allowed_projects:
                return False
            if request["operation"] == "read":
                return True
            return (
                self.allow_write
                and request["approval_ref"] == "approval/verified"
                and request["approval_revision"] == "policy-v1"
                and request["kind"] in {"project-context", "feature-inventory"}
            )

        self.authorize = authorize
        self.store = self.new_store()

    def new_store(self) -> GitArtifactStore:
        return GitArtifactStore(
            self.root,
            self.root,
            "qa-artifacts",
            self.authorize,
            author_name="QA",
            author_email="qa@example.invalid",
        )

    def write(
        self,
        *,
        ref: str = "docs/PROJECT_CONTEXT.md",
        content: str = "first",
        expected: str | None = None,
        operation: str = "op-1",
        kind: str = "project-context",
    ) -> dict:
        return self.store.write(
            kind=kind,
            project_ref="Sample",
            artifact_ref=ref,
            content=content,
            expected_revision=expected,
            operation_id=operation,
            source_ref="issue/1",
            source_revision="source-1",
            approval_ref="approval/verified",
            approval_revision="policy-v1",
            change_reason="approved change",
        )

    def test_new_markdown_is_in_git_tree_without_secondary_copy(self) -> None:
        first = self.write()
        self.assertEqual(first["status"], "stored", first)
        self.assertTrue(first["revision"].startswith("git:"))
        self.assertEqual(
            git(self.root, "show", "qa-artifacts:docs/PROJECT_CONTEXT.md"), "first"
        )
        self.assertFalse((self.root / "docs" / "PROJECT_CONTEXT.md").exists())
        self.assertEqual(
            self.store.read_current(
                "project-context", "Sample", "docs/PROJECT_CONTEXT.md"
            )["content"],
            "first",
        )

    def test_existing_markdown_updated_at_same_git_path(self) -> None:
        initial = context_handle(
            {
                "operation": "prepare-create",
                "project_name": "Sample",
                "enumeration_complete": True,
                "candidates": [{"ref": "docs/PROJECT_CONTEXT.md", "status": "absent"}],
            }
        )
        self.assertEqual(initial["status"], "draft")
        docs = self.root / "docs"
        docs.mkdir()
        path = docs / "PROJECT_CONTEXT.md"
        path.write_text(initial["artifact_markdown"], encoding="utf-8")
        git(self.root, "add", "docs/PROJECT_CONTEXT.md")
        git(self.root, "commit", "-qm", "existing canonical markdown")
        git(self.root, "branch", "-f", "qa-artifacts")
        before = self.store.read_current(
            "project-context", "Sample", "docs/PROJECT_CONTEXT.md"
        )
        self.assertIsNotNone(before)
        prep = {
            "operation": "prepare-sections",
            "markdown": before["content"],
            "artifact_ref": "docs/PROJECT_CONTEXT.md",
            "expected_revision": before["revision"],
            "source_ref": "source/2",
            "source_revision": "r2",
            "change_reason": "confirmed project facts",
            "section_updates": {"2": "- 製品: Sample App\n- 根拠: source/2"},
        }
        result = persist_prepared(
            self.store,
            prep,
            project_ref="Sample",
            operation_id="update-existing",
            approval_ref="approval/verified",
            approval_revision="policy-v1",
        )
        self.assertEqual(result["status"], "stored", result)
        self.assertIn(
            "- 製品: Sample App",
            git(self.root, "show", "qa-artifacts:docs/PROJECT_CONTEXT.md"),
        )
        self.assertEqual(
            self.store.read_revision(
                "project-context",
                "Sample",
                "docs/PROJECT_CONTEXT.md",
                before["revision"],
            )["content"],
            before["content"],
        )
        self.assertTrue(path.is_file())
        self.assertEqual(path.read_text(encoding="utf-8"), before["content"])
        self.assertFalse((self.root / ".qa-context-feature").exists())

    def test_retry_of_same_git_operation_is_idempotent(self) -> None:
        first = self.write()
        self.assertEqual(self.write()["status"], "idempotent")
        updated = self.write(
            content="second", expected=first["revision"], operation="op-2"
        )
        self.assertEqual(updated["status"], "stored")
        self.assertEqual(
            self.write(
                content="second",
                expected=first["revision"],
                operation="op-2",
            )["status"],
            "idempotent",
        )
        with self.assertRaisesRegex(StoreError, "revision_conflict"):
            self.write(content="changed", expected=first["revision"], operation="op-2")

    def test_native_ref_cas_detects_concurrent_edits(self) -> None:
        first = self.write()

        def update(index: int) -> str:
            store = self.new_store()
            try:
                return store.write(
                    kind="project-context",
                    project_ref="Sample",
                    artifact_ref="docs/PROJECT_CONTEXT.md",
                    content=f"change-{index}",
                    expected_revision=first["revision"],
                    operation_id=f"parallel-{index}",
                    source_ref="source/2",
                    source_revision="rev-2",
                    approval_ref="approval/verified",
                    approval_revision="policy-v1",
                    change_reason="parallel update",
                )["status"]
            except StoreError as exc:
                return str(exc)

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(update, (1, 2)))
        self.assertEqual(sorted(results), ["revision_conflict", "stored"])
        self.assertEqual(
            self.store.read_current(
                "project-context", "Sample", "docs/PROJECT_CONTEXT.md"
            )["revision"],
            "git:" + git(self.root, "rev-parse", "qa-artifacts"),
        )

    def test_untrusted_reference_transaction_hook_is_not_executed(self) -> None:
        hook = self.root / ".git" / "hooks" / "reference-transaction"
        marker = self.root / "unsafe-hook-executed"
        hook.write_text(
            "#!/bin/sh\nprintf executed > " + str(marker) + "\n",
            encoding="utf-8",
        )
        hook.chmod(0o700)
        self.assertEqual(self.write()["status"], "stored")
        self.assertFalse(marker.exists())

    def test_git_metadata_outside_authorized_root_is_rejected(self) -> None:
        worktree = self.root / "isolated-checkout"
        metadata = self.root / "external-gitdir"
        git(self.root, "init", "-q", "--separate-git-dir", str(metadata), str(worktree))
        with self.assertRaisesRegex(StoreError, "git_metadata_outside_authorized_root"):
            GitArtifactStore(
                worktree,
                worktree,
                "qa-artifacts",
                self.authorize,
                author_name="QA",
                author_email="qa@example.invalid",
            )

    def test_unknown_authorization_or_path_is_rejected(self) -> None:
        with self.assertRaisesRegex(StoreError, "artifact_ref_invalid"):
            self.write(ref="../escape.md")
        with self.assertRaisesRegex(StoreError, "artifact_ref_invalid"):
            self.write(ref=".git/config")
        with self.assertRaisesRegex(StoreError, "access_denied"):
            self.store.read_current(
                "project-context", "Other", "docs/PROJECT_CONTEXT.md"
            )
        self.allow_write = False
        with self.assertRaisesRegex(StoreError, "access_denied"):
            self.write()
        self.assertEqual(git(self.root, "rev-list", "--count", "qa-artifacts"), "1")

    def test_git_approval_revision_and_source_are_verified_before_write(self) -> None:
        authorized: list[dict] = []

        def inspect(request: dict) -> bool:
            authorized.append(request.copy())
            if request["operation"] == "read":
                return True
            return (
                request["approval_revision"] == "policy-v1"
                and request["source_revision"] == "source-1"
                and request["source_ref"] == "issue/1"
                and request["operation_id"] == "op-1"
                and request["change_reason"] == "approved change"
                and request["sha256"] == hashlib.sha256(b"first").hexdigest()
            )

        store = GitArtifactStore(
            self.root,
            self.root,
            "qa-artifacts",
            inspect,
            author_name="QA",
            author_email="qa@example.invalid",
        )

        def attempt(approval_revision: str) -> dict:
            return store.write(
                kind="project-context",
                project_ref="Sample",
                artifact_ref="docs/PROJECT_CONTEXT.md",
                content="first",
                expected_revision=None,
                operation_id="op-1",
                source_ref="issue/1",
                source_revision="source-1",
                approval_ref="approval/verified",
                approval_revision=approval_revision,
                change_reason="approved change",
            )

        with self.assertRaisesRegex(StoreError, "access_denied"):
            attempt("policy-invalid")
        self.assertEqual(git(self.root, "rev-list", "--count", "qa-artifacts"), "1")
        self.assertEqual(attempt("policy-v1")["status"], "stored")
        approved = next(
            request
            for request in authorized
            if request["operation"] == "write"
            and request["approval_revision"] == "policy-v1"
        )
        self.assertEqual(approved["source_revision"], "source-1")
        self.assertEqual(approved["operation_id"], "op-1")

    def test_source_ref_and_digest_are_preserved_in_git_history(self) -> None:
        result = self.write(content="verified")
        self.assertEqual(result["sha256"], hashlib.sha256(b"verified").hexdigest())
        message = git(self.root, "log", "-1", "--format=%B", "qa-artifacts")
        self.assertIn("QA-Operation-Id: op-1", message)
        self.assertIn("QA-Approval-Ref: approval/verified", message)
        self.assertIn("QA-Source-Revision: source-1", message)

    def _code_registry(self, *, additional_file: bool = False) -> tuple[dict, list]:
        baseline = git(self.root, "rev-parse", "qa-artifacts")
        source = self.root / "src"
        source.mkdir(exist_ok=True)
        (source / "auth.py").write_text("def access(): return True\n", encoding="utf-8")
        if additional_file:
            (source / "batch.py").write_text("def job(): pass\n", encoding="utf-8")
        git(self.root, "add", "src")
        git(self.root, "commit", "-qm", "source changes")
        head = git(self.root, "rev-parse", "HEAD")
        request = fixture()
        snap = request["snapshot"]
        snap["project_ref"] = "Sample"
        snap["artifact_ref"] = "qa/feature-inventory.json"
        snap["source_revision"] = head
        snap["sources"][0]["revision"] = head
        snap["changes"][0].update(
            before_revision=baseline,
            after_revision=head,
            locator="src/auth.py",
        )
        snap["history"][0]["revision"] = head
        request["observed_head_revision"] = head
        evidence = [
            {
                "source_id": "SRC-001",
                "repository_root": str(self.root),
                "authorized_root": str(self.root),
                "base_sha": baseline,
                "head_sha": head,
            }
        ]
        return request, evidence

    def test_initial_code_snapshot_requires_event_bound_primary_head(self) -> None:
        request, evidence = self._code_registry()
        request["snapshot"]["source_revision"] = "a" * 40
        request["observed_head_revision"] = "a" * 40
        result = persist_snapshot(
            self.store,
            request,
            expected_revision=None,
            approval_ref="approval/verified",
            approval_revision="policy-v1",
            change_reason="event primary not verified",
            git_inventory_requests=evidence,
        )
        self.assertEqual(result["status"], "blocked", result)
        self.assertIn("event_primary_code_source_missing", result["reasons"])

    def test_code_save_rechecks_actual_git_tree_and_rejects_unlisted_diff(
        self,
    ) -> None:
        request, evidence = self._code_registry(additional_file=True)
        result = persist_snapshot(
            self.store,
            request,
            expected_revision=None,
            approval_ref="approval/verified",
            approval_revision="policy-v1",
            change_reason="unlisted code diff",
            git_inventory_requests=evidence,
        )
        self.assertEqual(result["status"], "blocked", result)
        self.assertTrue(
            any("git_coverage_not_verified" in reason for reason in result["reasons"])
        )
        self.assertIsNone(
            self.store.read_current(
                "feature-inventory", "Sample", "qa/feature-inventory.json"
            )
        )

    def test_code_save_rejects_stale_head_even_if_commit_exists(self) -> None:
        request, evidence = self._code_registry()
        (self.root / "src" / "later.py").write_text(
            "def changed(): return True\n", encoding="utf-8"
        )
        git(self.root, "add", "src/later.py")
        git(self.root, "commit", "-qm", "advance source after inventory")
        result = persist_snapshot(
            self.store,
            request,
            expected_revision=None,
            approval_ref="approval/verified",
            approval_revision="policy-v1",
            change_reason="stale current git source",
            git_inventory_requests=evidence,
        )
        self.assertEqual(result["status"], "blocked", result)
        self.assertIn("git_head_changed", result["reasons"])
        self.assertIsNone(
            self.store.read_current(
                "feature-inventory", "Sample", "qa/feature-inventory.json"
            )
        )

    def test_code_save_rejects_wrong_git_diff_revision(self) -> None:
        request, evidence = self._code_registry()
        request["snapshot"]["changes"][0]["after_revision"] = "forged-head"
        result = persist_snapshot(
            self.store,
            request,
            expected_revision=None,
            approval_ref="approval/verified",
            approval_revision="policy-v1",
            change_reason="forged diff",
            git_inventory_requests=evidence,
        )
        self.assertEqual(result["status"], "blocked", result)
        self.assertIn("change_source_revision_mismatch:DIF-001", result["reasons"])

    def test_code_save_requires_complete_submodule_inventory(self) -> None:
        request, evidence = self._code_registry()
        git(
            self.root,
            "update-index",
            "--add",
            "--cacheinfo",
            "160000",
            evidence[0]["base_sha"],
            "vendor/module",
        )
        git(self.root, "commit", "-qm", "submodule added")
        head = git(self.root, "rev-parse", "HEAD")
        evidence[0]["head_sha"] = head
        request["observed_head_revision"] = head
        snapshot = request["snapshot"]
        snapshot["source_revision"] = head
        snapshot["sources"][0]["revision"] = head
        snapshot["changes"][0]["after_revision"] = head
        snapshot["history"][0]["revision"] = head
        result = persist_snapshot(
            self.store,
            request,
            expected_revision=None,
            approval_ref="approval/verified",
            approval_revision="policy-v1",
            change_reason="submodule not retrieved",
            git_inventory_requests=evidence,
        )
        self.assertEqual(result["status"], "blocked", result)
        self.assertTrue(
            any(
                reason.startswith("gitlink_source_evidence_missing:")
                for reason in result["reasons"]
            ),
            result,
        )

    def _assert_merge_or_release_requires_saved_git_base(self, event: str) -> None:
        request, evidence = self._code_registry()
        saved = persist_snapshot(
            self.store,
            request,
            expected_revision=None,
            approval_ref="approval/verified",
            approval_revision="policy-v1",
            change_reason="initial inventory",
            git_inventory_requests=evidence,
        )
        self.assertEqual(saved["status"], "stored", saved)
        previous = copy.deepcopy(request["snapshot"])
        old_head = evidence[0]["head_sha"]
        for filename in ("earlier.py", "latest.py"):
            (self.root / "src" / filename).write_text(
                f"def {filename[:-3]}(): return True\n", encoding="utf-8"
            )
            git(self.root, "add", f"src/{filename}")
            git(self.root, "commit", "-qm", f"source update {filename}")
            if filename == "earlier.py":
                middle = git(self.root, "rev-parse", "HEAD")
        head = git(self.root, "rev-parse", "HEAD")
        snapshot = request["snapshot"]
        request["previous_snapshot"] = previous
        request["observed_head_revision"] = head
        snapshot["event"] = event
        snapshot["event_basis"] = (
            {
                "merge_commit_sha": head,
                "target_ref": "refs/heads/main",
                "previous_head_sha": old_head,
            }
            if event == "merge"
            else {
                "commit_sha": head,
                "build_ref": "release/2",
                "target_ref": "refs/tags/v2",
            }
        )
        snapshot["source_revision"] = head
        snapshot["sources"][0]["revision"] = head
        snapshot["operation_id"] = f"op-{event}"
        snapshot["artifact_revision"] = "art-v2"
        snapshot["previous_artifact_revision"] = "art-v1"
        latest = copy.deepcopy(snapshot["changes"][0])
        latest.update(
            id="DIF-002",
            before_revision=middle,
            after_revision=head,
            locator="src/latest.py",
        )
        snapshot["changes"].append(latest)
        evidence[0].update(base_sha=middle, head_sha=head)
        # A middle-to-HEAD comparison has 100% coverage of the supplied DIFs,
        # but omits earlier.py added after the saved source revision.
        rejected = persist_snapshot(
            self.store,
            request,
            expected_revision=saved["revision"],
            approval_ref="approval/verified",
            approval_revision="policy-v1",
            change_reason=f"{event} with an incomplete Git baseline",
            git_inventory_requests=evidence,
        )
        self.assertEqual(rejected["status"], "blocked", rejected)
        self.assertTrue(
            any(
                "git_coverage_not_verified" in reason for reason in rejected["reasons"]
            ),
            rejected,
        )
        self.assertEqual(
            self.store.read_current(
                "feature-inventory", "Sample", "qa/feature-inventory.json"
            )["revision"],
            saved["revision"],
        )
        # The saved source is the only valid baseline; listing both paths
        # against it allows the complete update to be persisted.
        evidence[0]["base_sha"] = old_head
        latest["before_revision"] = old_head
        earlier = copy.deepcopy(latest)
        earlier.update(id="DIF-003", locator="src/earlier.py")
        snapshot["changes"].append(earlier)
        accepted = persist_snapshot(
            self.store,
            request,
            expected_revision=saved["revision"],
            approval_ref="approval/verified",
            approval_revision="policy-v1",
            change_reason=f"{event} with the saved Git baseline",
            git_inventory_requests=evidence,
        )
        self.assertEqual(accepted["status"], "stored", accepted)
        self.assertEqual(accepted["analysis_status"], "complete")

    def test_merge_requires_saved_git_base_for_full_source_diff(self) -> None:
        self._assert_merge_or_release_requires_saved_git_base("merge")

    def test_release_requires_saved_git_base_for_full_source_diff(self) -> None:
        self._assert_merge_or_release_requires_saved_git_base("release")

    def test_two_consecutive_pr_updates_preserve_earlier_dif_history(self) -> None:
        request, evidence = self._code_registry()
        saved = persist_snapshot(
            self.store,
            request,
            expected_revision=None,
            approval_ref="approval/verified",
            approval_revision="policy-v1",
            change_reason="initial inventory",
            git_inventory_requests=evidence,
        )
        self.assertEqual(saved["status"], "stored", saved)
        base_sha = evidence[0]["base_sha"]
        previous_head = evidence[0]["head_sha"]
        operation = saved["revision"]
        next_id = 2
        paths = ["src/auth.py"]
        for index, filename in enumerate(("batch.py", "reminders.py"), start=2):
            prior = copy.deepcopy(request["snapshot"])
            (self.root / "src" / filename).write_text(
                f"def run_{index}(): return {index}\n", encoding="utf-8"
            )
            git(self.root, "add", f"src/{filename}")
            git(self.root, "commit", "-qm", f"PR update {index}")
            head = git(self.root, "rev-parse", "HEAD")
            snapshot = request["snapshot"]
            request["previous_snapshot"] = prior
            snapshot["event"] = "pr_update"
            snapshot["event_basis"] = {
                "base_sha": base_sha,
                "head_sha": head,
                "previous_head_sha": previous_head,
            }
            snapshot["source_revision"] = head
            snapshot["sources"][0]["revision"] = head
            request["observed_head_revision"] = head
            snapshot["previous_artifact_revision"] = prior["artifact_revision"]
            snapshot["artifact_revision"] = f"art-v{index}"
            snapshot["operation_id"] = f"op-v{index}"
            paths.append(f"src/{filename}")
            for before, locator in [
                *((base_sha, path) for path in paths),
                (previous_head, f"src/{filename}"),
            ]:
                row = copy.deepcopy(snapshot["changes"][0])
                row.update(
                    id=f"DIF-{next_id:03d}",
                    before_revision=before,
                    after_revision=head,
                    locator=locator,
                )
                next_id += 1
                snapshot["changes"].append(row)
            evidence[0]["head_sha"] = head
            evidence[0]["previous_head_base_sha"] = previous_head
            result = persist_snapshot(
                self.store,
                request,
                expected_revision=operation,
                approval_ref="approval/verified",
                approval_revision="policy-v1",
                change_reason=f"PR update {index}",
                git_inventory_requests=evidence,
            )
            self.assertEqual(result["status"], "stored", result)
            self.assertEqual(result["analysis_status"], "complete")
            self.assertEqual(
                snapshot["changes"][0]["after_revision"],
                prior["changes"][0]["after_revision"],
            )
            operation = result["revision"]
            previous_head = head
        stored = self.store.read_current(
            "feature-inventory", "Sample", "qa/feature-inventory.json"
        )
        self.assertIsNotNone(stored)
        self.assertEqual(stored["revision"], operation)
        # A same-HEAD analysis update must repeat both Git comparisons.
        prior = copy.deepcopy(request["snapshot"])
        request["previous_snapshot"] = prior
        snapshot = request["snapshot"]
        snapshot["event"] = "analysis_update"
        snapshot["event_basis"] = {
            "source_revision": snapshot["source_revision"],
            "evidence_ref": "review/continued-analysis",
        }
        snapshot["operation_id"] = "op-analysis-review"
        snapshot["previous_artifact_revision"] = prior["artifact_revision"]
        snapshot["artifact_revision"] = "art-analysis-v3"
        saved_previous_head = evidence[0].pop("previous_head_base_sha")
        missing = persist_snapshot(
            self.store,
            request,
            expected_revision=operation,
            approval_ref="approval/verified",
            approval_revision="policy-v1",
            change_reason="missing original PR comparison",
            git_inventory_requests=evidence,
        )
        self.assertEqual(missing["status"], "blocked", missing)
        self.assertIn("analysis_git_baselines_mismatch", missing["reasons"])
        evidence[0]["previous_head_base_sha"] = saved_previous_head
        accepted = persist_snapshot(
            self.store,
            request,
            expected_revision=operation,
            approval_ref="approval/verified",
            approval_revision="policy-v1",
            change_reason="full analysis comparison",
            git_inventory_requests=evidence,
        )
        self.assertEqual(accepted["status"], "stored", accepted)
        self.assertEqual(accepted["analysis_status"], "complete")

    def test_shared_head_repositories_use_explicit_primary_source_and_own_base(
        self,
    ) -> None:
        request, evidence = self._code_registry()
        old_head = evidence[0]["head_sha"]
        base = evidence[0]["base_sha"]
        other_dir = tempfile.TemporaryDirectory()
        self.addCleanup(other_dir.cleanup)
        other = Path(other_dir.name) / "replica"
        subprocess.run(
            ["git", "clone", "-q", str(self.root), str(other)],
            capture_output=True,
            text=True,
            check=True,
        )
        snapshot = request["snapshot"]
        secondary_source = copy.deepcopy(snapshot["sources"][0])
        secondary_source.update(
            id="SRC-002",
            ref="product/replica",
        )
        snapshot["sources"].append(secondary_source)
        snapshot["expected_source_ids"].append("SRC-002")
        snapshot["features"][0]["source_ids"].append("SRC-002")
        secondary_change = copy.deepcopy(snapshot["changes"][0])
        secondary_change.update(id="DIF-002", source_id="SRC-002")
        snapshot["changes"].append(secondary_change)
        evidence.append(
            {
                "source_id": "SRC-002",
                "repository_root": str(other),
                "authorized_root": str(other),
                "base_sha": base,
                "head_sha": old_head,
            }
        )
        first = persist_snapshot(
            self.store,
            request,
            expected_revision=None,
            approval_ref="approval/verified",
            approval_revision="policy-v1",
            change_reason="same head initial",
            git_inventory_requests=evidence,
        )
        self.assertEqual(first["status"], "stored", first)
        previous = copy.deepcopy(snapshot)
        (self.root / "src" / "batch.py").write_text(
            "def batch(): return 1\n", encoding="utf-8"
        )
        git(self.root, "add", "src/batch.py")
        git(self.root, "commit", "-qm", "shared updated HEAD")
        new_head = git(self.root, "rev-parse", "HEAD")
        git(other, "fetch", "-q", str(self.root), new_head)
        git(other, "checkout", "-q", "--detach", new_head)
        self.assertEqual(git(other, "rev-parse", "HEAD"), new_head)
        request["previous_snapshot"] = previous
        snapshot["event"] = "pr_update"
        snapshot["event_basis"] = {
            "base_sha": base,
            "head_sha": new_head,
            "previous_head_sha": old_head,
        }
        snapshot["source_revision"] = new_head
        for source in snapshot["sources"]:
            source["revision"] = new_head
        snapshot["operation_id"] = "op-v2"
        snapshot["artifact_revision"] = "art-v2"
        snapshot["previous_artifact_revision"] = "art-v1"
        request["observed_head_revision"] = new_head
        for i, (sid, before, path) in enumerate(
            [
                ("SRC-001", base, "src/auth.py"),
                ("SRC-001", base, "src/batch.py"),
                ("SRC-001", old_head, "src/batch.py"),
                ("SRC-002", old_head, "src/batch.py"),
            ],
            start=3,
        ):
            changed = copy.deepcopy(snapshot["changes"][0])
            changed.update(
                id=f"DIF-{i:03d}",
                source_id=sid,
                before_revision=before,
                after_revision=new_head,
                locator=path,
            )
            snapshot["changes"].append(changed)
        evidence[0].update(
            head_sha=new_head,
            previous_head_base_sha=old_head,
        )
        evidence[1].update(
            base_sha=old_head,
            head_sha=new_head,
            previous_head_base_sha=old_head,
        )
        missing_primary = persist_snapshot(
            self.store,
            request,
            expected_revision=first["revision"],
            approval_ref="approval/verified",
            approval_revision="policy-v1",
            change_reason="ambiguous owner",
            git_inventory_requests=evidence,
        )
        self.assertEqual(missing_primary["status"], "blocked", missing_primary)
        self.assertIn("event_primary_source_ambiguous", missing_primary["reasons"])
        snapshot["event_basis"]["primary_source_id"] = "SRC-001"
        result = persist_snapshot(
            self.store,
            request,
            expected_revision=first["revision"],
            approval_ref="approval/verified",
            approval_revision="policy-v1",
            change_reason="shared SHA with independent source bases",
            git_inventory_requests=evidence,
        )
        self.assertEqual(result["status"], "stored", result)
        self.assertEqual(result["analysis_status"], "complete")

    def test_two_independent_git_repositories_save_and_update(self) -> None:
        second_dir = tempfile.TemporaryDirectory()
        self.addCleanup(second_dir.cleanup)
        other = Path(second_dir.name)
        git(other, "init", "-q")
        git(other, "config", "user.email", "qa@example.invalid")
        git(other, "config", "user.name", "QA")
        (other / "README.md").write_text("secondary\n", encoding="utf-8")
        git(other, "add", ".")
        git(other, "commit", "-qm", "secondary baseline")
        other_base = git(other, "rev-parse", "HEAD")
        (other / "src").mkdir()
        (other / "src" / "service.py").write_text(
            "def service(): pass\n", encoding="utf-8"
        )
        git(other, "add", "src")
        git(other, "commit", "-qm", "secondary code")
        other_head = git(other, "rev-parse", "HEAD")
        request, evidence = self._code_registry()
        snapshot = request["snapshot"]
        first_head = evidence[0]["head_sha"]
        first_base = evidence[0]["base_sha"]
        secondary = {
            **copy.deepcopy(snapshot["sources"][0]),
            "id": "SRC-002",
            "ref": "product/backend",
            "revision": other_head,
        }
        snapshot["sources"].append(secondary)
        snapshot["expected_source_ids"].append("SRC-002")
        snapshot["features"][0]["source_ids"].append("SRC-002")
        second_change = copy.deepcopy(snapshot["changes"][0])
        second_change.update(
            id="DIF-002",
            source_id="SRC-002",
            before_revision=other_base,
            after_revision=other_head,
            locator="src/service.py",
        )
        snapshot["changes"].append(second_change)
        evidence.append(
            {
                "source_id": "SRC-002",
                "repository_root": str(other),
                "authorized_root": str(other),
                "base_sha": other_base,
                "head_sha": other_head,
            }
        )
        saved = persist_snapshot(
            self.store,
            request,
            expected_revision=None,
            approval_ref="approval/verified",
            approval_revision="policy-v1",
            change_reason="two independent sources",
            git_inventory_requests=evidence,
        )
        self.assertEqual(saved["status"], "stored", saved)
        previous = copy.deepcopy(snapshot)
        (self.root / "src" / "batch.py").write_text(
            "def batch(): pass\n", encoding="utf-8"
        )
        git(self.root, "add", "src/batch.py")
        git(self.root, "commit", "-qm", "primary source update")
        new_first_head = git(self.root, "rev-parse", "HEAD")
        (other / "src" / "worker.py").write_text(
            "def worker(): pass\n", encoding="utf-8"
        )
        git(other, "add", "src/worker.py")
        git(other, "commit", "-qm", "secondary source update")
        new_other_head = git(other, "rev-parse", "HEAD")
        request["previous_snapshot"] = previous
        snapshot["event"] = "pr_update"
        snapshot["event_basis"] = {
            "base_sha": first_base,
            "head_sha": new_first_head,
            "previous_head_sha": first_head,
        }
        snapshot["source_revision"] = new_first_head
        snapshot["sources"][0]["revision"] = new_first_head
        snapshot["sources"][1]["revision"] = new_other_head
        request["observed_head_revision"] = new_first_head
        snapshot["previous_artifact_revision"] = "art-v1"
        snapshot["artifact_revision"] = "art-v2"
        snapshot["operation_id"] = "op-v2"
        pairs = [
            ("SRC-001", first_base, new_first_head, "src/auth.py"),
            ("SRC-001", first_base, new_first_head, "src/batch.py"),
            ("SRC-001", first_head, new_first_head, "src/batch.py"),
            ("SRC-002", other_base, new_other_head, "src/service.py"),
            ("SRC-002", other_base, new_other_head, "src/worker.py"),
            ("SRC-002", other_head, new_other_head, "src/worker.py"),
        ]
        for index, (sid, before, after, locator) in enumerate(pairs, start=3):
            row = copy.deepcopy(snapshot["changes"][0])
            row.update(
                id=f"DIF-{index:03d}",
                source_id=sid,
                before_revision=before,
                after_revision=after,
                locator=locator,
            )
            snapshot["changes"].append(row)
        evidence[0].update(head_sha=new_first_head, previous_head_base_sha=first_head)
        evidence[1].update(head_sha=new_other_head, previous_head_base_sha=other_head)
        result = persist_snapshot(
            self.store,
            request,
            expected_revision=saved["revision"],
            approval_ref="approval/verified",
            approval_revision="policy-v1",
            change_reason="two independent source revisions",
            git_inventory_requests=evidence,
        )
        self.assertEqual(result["status"], "stored", result)
        self.assertEqual(result["analysis_status"], "complete")
        self.assertEqual(
            self.store.read_current(
                "feature-inventory", "Sample", "qa/feature-inventory.json"
            )["revision"],
            result["revision"],
        )

    def test_new_secondary_repo_is_enumerated_in_pr_update(self) -> None:
        request, evidence = self._code_registry()
        first = persist_snapshot(
            self.store,
            request,
            expected_revision=None,
            approval_ref="approval/verified",
            approval_revision="policy-v1",
            change_reason="initial primary source",
            git_inventory_requests=evidence,
        )
        self.assertEqual(first["status"], "stored", first)
        previous = copy.deepcopy(request["snapshot"])
        (self.root / "src" / "batch.py").write_text(
            "def batch(): pass\n", encoding="utf-8"
        )
        git(self.root, "add", "src/batch.py")
        git(self.root, "commit", "-qm", "new PR changes")
        head = git(self.root, "rev-parse", "HEAD")
        secondary_dir = tempfile.TemporaryDirectory()
        self.addCleanup(secondary_dir.cleanup)
        other = Path(secondary_dir.name)
        git(other, "init", "-q")
        git(other, "config", "user.name", "QA")
        git(other, "config", "user.email", "qa@example.invalid")
        (other / "README.md").write_text("base\n", encoding="utf-8")
        git(other, "add", ".")
        git(other, "commit", "-qm", "new source baseline")
        base = git(other, "rev-parse", "HEAD")
        (other / "src").mkdir()
        (other / "src" / "service.py").write_text(
            "def service(): pass\n", encoding="utf-8"
        )
        git(other, "add", "src")
        git(other, "commit", "-qm", "new secondary changes")
        other_head = git(other, "rev-parse", "HEAD")
        snap = request["snapshot"]
        request["previous_snapshot"] = previous
        request["observed_head_revision"] = head
        snap["event"] = "pr_update"
        snap["event_basis"] = {
            "base_sha": evidence[0]["base_sha"],
            "head_sha": head,
            "previous_head_sha": evidence[0]["head_sha"],
        }
        snap["source_revision"] = head
        snap["sources"][0]["revision"] = head
        snap["sources"].append(
            {
                **copy.deepcopy(snap["sources"][0]),
                "id": "SRC-002",
                "ref": "product/new-service",
                "revision": other_head,
            }
        )
        snap["expected_source_ids"].append("SRC-002")
        snap["features"][0]["source_ids"].append("SRC-002")
        snap["history"].append(
            {
                "event_id": "event-2",
                "kind": "changed",
                "revision": head,
                "evidence_ref": "evidence/new-source",
                "from_ids": ["FEAT-001"],
                "to_ids": ["FEAT-001"],
            }
        )
        snap["operation_id"] = "op-secondary"
        snap["artifact_revision"] = "art-v2"
        snap["previous_artifact_revision"] = "art-v1"
        for i, (sid, before, after, path) in enumerate(
            (
                ("SRC-001", evidence[0]["base_sha"], head, "src/auth.py"),
                ("SRC-001", evidence[0]["base_sha"], head, "src/batch.py"),
                ("SRC-001", evidence[0]["head_sha"], head, "src/batch.py"),
                ("SRC-002", base, other_head, "src/service.py"),
            ),
            start=2,
        ):
            row = copy.deepcopy(snap["changes"][0])
            row.update(
                id=f"DIF-{i:03d}",
                source_id=sid,
                before_revision=before,
                after_revision=after,
                locator=path,
            )
            snap["changes"].append(row)
        evidence[0].update(
            head_sha=head,
            previous_head_base_sha=previous["source_revision"],
        )
        evidence.append(
            {
                "source_id": "SRC-002",
                "repository_root": str(other),
                "authorized_root": str(other),
                "base_sha": base,
                "head_sha": other_head,
            }
        )
        result = persist_snapshot(
            self.store,
            request,
            expected_revision=first["revision"],
            approval_ref="approval/verified",
            approval_revision="policy-v1",
            change_reason="register secondary checkout",
            git_inventory_requests=evidence,
        )
        self.assertEqual(result["status"], "stored", result)

    def test_verified_gitlink_source_can_complete_parent_git_inventory(self) -> None:
        request, evidence = self._code_registry()
        child = self.root / "vendor" / "module"
        child.mkdir(parents=True)
        git(child, "init", "-q")
        git(child, "config", "user.name", "QA")
        git(child, "config", "user.email", "qa@example.invalid")
        (child / "service.py").write_text("def service(): pass\n", encoding="utf-8")
        git(child, "add", ".")
        git(child, "commit", "-qm", "verified child")
        child_head = git(child, "rev-parse", "HEAD")
        git(
            self.root,
            "update-index",
            "--add",
            "--cacheinfo",
            "160000",
            child_head,
            "vendor/module",
        )
        git(self.root, "commit", "-qm", "link verified child source")
        parent_head = git(self.root, "rev-parse", "HEAD")
        snap = request["snapshot"]
        request["observed_head_revision"] = parent_head
        snap["source_revision"] = parent_head
        snap["sources"][0]["revision"] = parent_head
        snap["sources"].append(
            {
                **copy.deepcopy(snap["sources"][0]),
                "id": "SRC-002",
                "ref": "product/submodule",
                "revision": child_head,
            }
        )
        snap["expected_source_ids"].append("SRC-002")
        snap["features"][0]["source_ids"].append("SRC-002")
        snap["changes"][0]["after_revision"] = parent_head
        snap["changes"].append(
            {
                **copy.deepcopy(snap["changes"][0]),
                "id": "DIF-002",
                "locator": "vendor/module",
            }
        )
        snap["history"][0]["revision"] = parent_head
        evidence[0].update(
            head_sha=parent_head,
            gitlink_sources={f"gitlink:vendor/module@{child_head}": "SRC-002"},
        )
        evidence.append(
            {
                "source_id": "SRC-002",
                "repository_root": str(child),
                "authorized_root": str(child),
                "base_sha": None,
                "head_sha": child_head,
            }
        )
        stored = persist_snapshot(
            self.store,
            request,
            expected_revision=None,
            approval_ref="approval/verified",
            approval_revision="policy-v1",
            change_reason="verified submodule",
            git_inventory_requests=evidence,
        )
        self.assertEqual(stored["status"], "stored", stored)

    def test_saved_legacy_duplicate_merge_authorizes_each_parent(self) -> None:
        request, evidence = self._code_registry()
        previous = copy.deepcopy(request["snapshot"])
        second = copy.deepcopy(previous["changes"][0])
        second.update(
            id="DIF-002",
            classification="no_impact",
            feature_ids=[],
            reason="Old conflicting verdict",
            approval_ref="approval/verified",
        )
        previous["changes"].append(second)
        raw = json.dumps(previous, ensure_ascii=False, sort_keys=True)
        saved = self.store.write(
            kind="feature-inventory",
            project_ref="Sample",
            artifact_ref="qa/feature-inventory.json",
            content=raw,
            expected_revision=None,
            operation_id="legacy-raw-save",
            source_ref="Sample",
            source_revision=previous["source_revision"],
            approval_ref="approval/verified",
            approval_revision="policy-v1",
            change_reason="legacy artifact from old schema",
        )
        self.assertEqual(saved["status"], "stored", saved)
        snap = request["snapshot"]
        request["previous_snapshot"] = previous
        snap["changes"] = copy.deepcopy(previous["changes"])
        snap["event"] = "analysis_update"
        snap["event_basis"] = {
            "source_revision": snap["source_revision"],
            "evidence_ref": "review/legacy",
        }
        snap["previous_artifact_revision"] = "art-v1"
        snap["artifact_revision"] = "art-v2"
        snap["operation_id"] = "fix-legacy-duplicate"
        correction = copy.deepcopy(snap["changes"][0])
        correction.update(
            id="DIF-003",
            supersedes_ids=["DIF-001", "DIF-002"],
            evidence_ref="review/confirmed-scope",
            reason="Unify old conflicting classifications",
            approval_ref="approval/verified",
            approval_revision="policy-v1",
        )
        snap["changes"].append(correction)
        calls = []
        original = self.store.authorize

        def count_authorizations(data: dict) -> bool:
            if data["operation"] == "reclassify":
                calls.append(data["supersedes_id"])
            return original(data)

        self.store.authorize = count_authorizations
        result = persist_snapshot(
            self.store,
            request,
            expected_revision=saved["revision"],
            approval_ref="approval/verified",
            approval_revision="policy-v1",
            change_reason="reviewed old contradictory decisions",
            git_inventory_requests=evidence,
        )
        self.assertEqual(result["status"], "stored", result)
        self.assertEqual(sorted(calls), ["DIF-001", "DIF-002"])
        self.assertEqual(len(snap["changes"]), 3)

    def test_source_ref_lock_conflict_prevents_artifact_write(self) -> None:
        request, evidence = self._code_registry()
        branch = git(self.root, "symbolic-ref", "HEAD")
        ref_path = git(self.root, "rev-parse", "--git-path", branch)
        target = Path(ref_path)
        if not target.is_absolute():
            target = self.root / target
        lock = Path(str(target) + ".lock")
        lock.parent.mkdir(parents=True, exist_ok=True)
        lock.write_text("another writer", encoding="utf-8")
        self.addCleanup(lock.unlink, missing_ok=True)
        denied = persist_snapshot(
            self.store,
            request,
            expected_revision=None,
            approval_ref="approval/verified",
            approval_revision="policy-v1",
            change_reason="concurrent source mutation",
            git_inventory_requests=evidence,
        )
        self.assertEqual(denied["status"], "blocked", denied)
        self.assertIn("git_source_ref_lock_unavailable", denied["reasons"])
        self.assertIsNone(
            self.store.read_current(
                "feature-inventory", "Sample", "qa/feature-inventory.json"
            )
        )

    def test_feature_inventory_uses_same_git_cas_without_schema_copy(self) -> None:
        request, evidence = self._code_registry()
        saved = persist_snapshot(
            self.store,
            request,
            expected_revision=None,
            approval_ref="approval/verified",
            approval_revision="policy-v1",
            change_reason="first inventory",
            git_inventory_requests=evidence,
        )
        self.assertEqual(saved["status"], "stored", saved)
        before = copy.deepcopy(request["snapshot"])
        request["previous_snapshot"] = before
        request["snapshot"]["event"] = "analysis_update"
        request["snapshot"]["event_basis"] = {
            "source_revision": request["snapshot"]["source_revision"],
            "evidence_ref": "review/checked",
        }
        request["snapshot"]["operation_id"] = "op-v2"
        request["snapshot"]["artifact_revision"] = "art-v2"
        request["snapshot"]["previous_artifact_revision"] = "art-v1"
        saved2 = persist_snapshot(
            self.store,
            request,
            expected_revision=saved["revision"],
            approval_ref="approval/verified",
            approval_revision="policy-v1",
            change_reason="inventory review",
            git_inventory_requests=evidence,
        )
        self.assertEqual(saved2["status"], "stored", saved2)


if __name__ == "__main__":
    unittest.main()
