"""PR #22/I: QA Knowledge identity / partial lookup and exploratory direct start."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import unittest.mock
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT))
from scripts.skills.evals.deterministic.run import grade  # noqa: E402


def _load(skill: str, relative: str, name: str):
    path = REPO_ROOT / "skills" / skill / relative
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


knowledge = _load("qa-knowledge", "scripts/knowledge_runtime.py", "pr22i_knowledge")
validator = _load(
    "qa-knowledge", "evals/deterministic/validator.py", "pr22i_knowledge_validator"
)
exploratory = _load(
    "exploratory-testing", "scripts/exploratory_runtime.py", "pr22i_exploratory"
)
exploratory_validator = _load(
    "exploratory-testing",
    "evals/deterministic/validator.py",
    "pr22i_exploratory_validator",
)

DEPENDENCIES = {"config:a": "r1", "config:b": "r1"}


def make_entry(scope="project:a", subject="delay", dependency="config:a", **overrides):
    identity = {
        "kind": "test_environment",
        "scope_refs": [scope],
        "subject": subject,
    }
    entry = {
        "schema_version": "1",
        "entry_ref": knowledge.canonical_entry_ref(identity),
        "identity": identity,
        "kind": "test_environment",
        "content": f"{subject} knowledge",
        "scope_refs": [scope],
        "applicability": {"environment": ["staging"], "version": "v1"},
        "provenance": [{"ref": "activity:ACT-1", "revision": "r1"}],
        "currentness_dependencies": [{"ref": dependency, "revision": "r1"}],
        "last_verified": {"at": "2026-11-09", "condition": "staging/v1"},
        "state": "有効",
        "replacement_ref": None,
        "related_qa_refs": [],
    }
    entry.update(overrides)
    return entry


def with_revision(entry, revision="sha256:stored"):
    return {**entry, "entry_revision": revision}


def search(entries, scope="project:a", dependencies=None, **overrides):
    params = {
        "scope_refs": {scope},
        "kind": "test_environment",
        "environment": "staging",
        "version": "v1",
        "current_dependencies": DEPENDENCIES if dependencies is None else dependencies,
        "listing_complete": True,
    }
    params.update(overrides)
    return knowledge.lookup(entries, **params)


def mismatched_entries():
    """Entries whose entry_ref hash matches identity but whose fields disagree."""
    base = make_entry()
    scope = make_entry()
    scope["scope_refs"] = ["project:b"]
    kind = make_entry()
    kind["kind"] = "test_focus"
    order_identity = {
        "kind": "test_environment",
        "scope_refs": ["project:a", "project:b"],
        "subject": "order",
    }
    order = make_entry()
    order["identity"] = order_identity
    order["entry_ref"] = knowledge.canonical_entry_ref(order_identity)
    order["scope_refs"] = ["project:b", "project:a"]
    no_kind = make_entry()
    no_kind["identity"] = {"scope_refs": ["project:a"], "subject": "delay"}
    no_kind["entry_ref"] = knowledge.canonical_entry_ref(no_kind["identity"])
    no_scope = make_entry()
    no_scope["identity"] = {"kind": "test_environment", "subject": "delay"}
    no_scope["entry_ref"] = knowledge.canonical_entry_ref(no_scope["identity"])
    return {
        "scope": scope,
        "kind": kind,
        "scope_order": order,
        "identity_without_kind": no_kind,
        "identity_without_scope": no_scope,
    }, base


class KnowledgeIdentityInvariantTests(unittest.TestCase):
    def test_valid_entry_has_no_identity_issues(self):
        self.assertEqual(knowledge.identity_issues(make_entry()), [])

    def test_mismatched_identity_is_rejected_on_every_path(self):
        cases, _ = mismatched_entries()
        for name, entry in cases.items():
            with self.subTest(case=name):
                # The hash is correct, so the old ref check alone would accept it.
                self.assertEqual(
                    entry["entry_ref"],
                    knowledge.canonical_entry_ref(entry["identity"]),
                )
                self.assertTrue(knowledge.identity_issues(entry))
                self.assertFalse(knowledge.validate_entry(entry)["valid"])

                with tempfile.TemporaryDirectory() as temp:
                    created = knowledge.create_entry(
                        Path(temp) / "knowledge",
                        entry,
                        complete_root_snapshot=True,
                        atomic_create_if_absent_available=True,
                        current_dependencies=DEPENDENCIES,
                    )
                    self.assertEqual(created["status"], "blocked")
                    self.assertEqual(created["reason"], "entry_identity_invalid")
                    self.assertEqual(list((Path(temp)).rglob("*.md")), [])

                    root = Path(temp)
                    (root / f"{entry['entry_ref']}.md").write_bytes(
                        knowledge.render_entry(entry)
                    )
                    read = knowledge.read_entry(root, entry["entry_ref"])
                    self.assertEqual(read["status"], "blocked")
                    self.assertEqual(read["reason"], "entry_identity_invalid")

                result = search([with_revision(entry)])
                self.assertEqual(result["status"], "incomplete")
                self.assertEqual(result["entries"], [])
                self.assertTrue(
                    any(entry["entry_ref"] in item for item in result["unresolved"])
                )

                plan = knowledge.plan_update(
                    expected_entry_revision="sha256:stored",
                    native_atomic_conditional_write=True,
                    current_entry=make_entry(),
                    updated_entry=entry,
                )
                self.assertEqual(plan["status"], "blocked")
                self.assertEqual(plan["reason"], "entry_identity_invalid")

    def test_identity_is_never_repaired_or_reordered(self):
        cases, _ = mismatched_entries()
        original = json.dumps(cases["scope_order"], sort_keys=True)
        search([with_revision(cases["scope_order"])])
        knowledge.identity_issues(cases["scope_order"])
        self.assertEqual(json.dumps(cases["scope_order"], sort_keys=True), original)

    def test_update_that_changes_identity_requires_replacement_not_reuse(self):
        current = make_entry()
        renamed = make_entry(subject="other")
        plan = knowledge.plan_update(
            expected_entry_revision="sha256:stored",
            native_atomic_conditional_write=True,
            current_entry=current,
            updated_entry=renamed,
        )
        self.assertEqual(plan["status"], "replacement_required")
        same = knowledge.plan_update(
            expected_entry_revision="sha256:stored",
            native_atomic_conditional_write=True,
            current_entry=current,
            updated_entry={**current, "content": "revised"},
        )
        self.assertEqual(same["status"], "conditional_write_required")
        no_cas = knowledge.plan_update(
            expected_entry_revision="sha256:stored",
            native_atomic_conditional_write=False,
            current_entry=current,
            updated_entry=current,
        )
        self.assertEqual(no_cas["reason"], "atomic_conditional_write_unavailable")

    def test_replacement_validates_the_new_entry_identity(self):
        cases, _ = mismatched_entries()
        base = make_entry(subject="old")
        bad = cases["kind"]
        blocked = knowledge.plan_replacement(
            old_entry_ref=base["entry_ref"],
            new_entry_ref=bad["entry_ref"],
            native_atomic_multi_entry_update=True,
            old_entry=base,
            new_entry=bad,
        )
        self.assertEqual(blocked["reason"], "entry_identity_invalid")
        new = make_entry(subject="split")
        ok = knowledge.plan_replacement(
            old_entry_ref=base["entry_ref"],
            new_entry_ref=new["entry_ref"],
            native_atomic_multi_entry_update=True,
            old_entry=base,
            new_entry=new,
        )
        self.assertEqual(ok["status"], "conditional_multi_entry_update_required")

    def test_conflicting_existing_target_is_not_accepted_as_same_identity(self):
        entry = make_entry()
        broken = {**entry, "kind": "test_focus"}
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / f"{entry['entry_ref']}.md").write_bytes(
                knowledge.render_entry(broken)
            )
            result = knowledge.create_entry(
                root,
                entry,
                complete_root_snapshot=True,
                atomic_create_if_absent_available=True,
                current_dependencies=DEPENDENCIES,
            )
            self.assertEqual(result["status"], "blocked")
            self.assertEqual(
                result["reason"], "existing_canonical_target_identity_invalid"
            )

    def test_legacy_entries_following_the_documented_schema_stay_readable(self):
        # An entry written by the previous helper: identity already carries the
        # matching kind and scope_refs, there is no entry_revision in the body.
        entry = make_entry()
        legacy_raw = knowledge.render_entry(entry)
        self.assertNotIn(b"entry_revision", legacy_raw)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / f"{entry['entry_ref']}.md").write_bytes(legacy_raw)
            read = knowledge.read_entry(root, entry["entry_ref"])
            self.assertEqual(read["status"], "current")
            self.assertEqual(read["entry"], entry)
            found = knowledge.lookup_root(
                root,
                scope_refs={"project:a"},
                kind="test_environment",
                environment="staging",
                version="v1",
                current_dependencies=DEPENDENCIES,
            )
            self.assertEqual(found["status"], "complete")
            self.assertEqual(
                [item["entry_ref"] for item in found["entries"]], [entry["entry_ref"]]
            )

    def test_entry_revision_is_metadata_never_stored_in_the_body(self):
        entry = make_entry()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            polluted = knowledge.create_entry(
                root,
                with_revision(entry, "sha256:invented"),
                complete_root_snapshot=True,
                atomic_create_if_absent_available=True,
                current_dependencies=DEPENDENCIES,
            )
            self.assertEqual(polluted["reason"], "entry_revision_must_not_be_in_body")
            created = knowledge.create_entry(
                root,
                entry,
                complete_root_snapshot=True,
                atomic_create_if_absent_available=True,
                current_dependencies=DEPENDENCIES,
            )
            self.assertEqual(created["status"], "created")
            raw = (root / f"{entry['entry_ref']}.md").read_bytes()
            self.assertNotIn(b"entry_revision", raw)
            read = knowledge.read_entry(root, entry["entry_ref"])
            self.assertNotIn("entry_revision", read["entry"])
            prepared = knowledge.lookup_input(read)
            self.assertEqual(prepared["entry_revision"], created["entry_revision"])
            with self.assertRaises(ValueError):
                knowledge.lookup_input({"status": "blocked", "entry": entry})
            with self.assertRaises(ValueError):
                knowledge.lookup_input({"status": "current", "entry": entry})


class KnowledgePartialLookupTests(unittest.TestCase):
    def test_unrelated_scope_dependency_unavailable_does_not_stop_search(self):
        a = with_revision(make_entry("project:a", "a", "config:a"))
        b = with_revision(make_entry("project:b", "b", "config:unreachable"))
        result = search([a, b])
        self.assertEqual(result["status"], "complete")
        self.assertTrue(result["complete"])
        self.assertEqual(
            [item["entry_ref"] for item in result["entries"]], [a["entry_ref"]]
        )
        self.assertEqual(
            result["out_of_scope_diagnostics"],
            [f"{b['entry_ref']}:currentness_unresolved_not_applicable"],
        )
        self.assertEqual(result["historical_excluded_refs"], [])

    def test_unrelated_entry_content_defects_do_not_stop_search(self):
        a = with_revision(make_entry("project:a", "a"))
        b = with_revision(make_entry("project:b", "b", content=""))
        self.assertEqual(search([a, b])["status"], "complete")

    def test_kind_environment_version_mismatch_is_certainly_unrelated(self):
        a = with_revision(make_entry("project:a", "a"))
        other_env = with_revision(
            make_entry(
                "project:a",
                "env",
                "config:unreachable",
                applicability={"environment": ["prod"], "version": "v1"},
            )
        )
        other_version = with_revision(
            make_entry(
                "project:a",
                "ver",
                "config:unreachable",
                applicability={"environment": ["staging"], "version": "v9"},
            )
        )
        result = search([a, other_env, other_version])
        self.assertEqual(result["status"], "complete")
        self.assertEqual(len(result["entries"]), 1)

    def test_applicable_entry_with_unresolved_dependency_is_not_returned(self):
        a = with_revision(make_entry("project:a", "a", "config:unreachable"))
        result = search([a])
        self.assertEqual(result["status"], "incomplete")
        self.assertEqual(result["entries"], [])
        self.assertIn(f"{a['entry_ref']}:currentness_unresolved", result["unresolved"])

    def test_applicable_stale_entry_is_excluded_as_history(self):
        a = with_revision(make_entry("project:a", "a", "config:a"))
        result = search([a], dependencies={"config:a": "r2"})
        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["entries"], [])
        self.assertEqual(result["historical_excluded_refs"], [a["entry_ref"]])

    def test_applicable_entry_without_storage_revision_is_not_returned(self):
        a = make_entry("project:a", "a")
        result = search([a])
        self.assertEqual(result["entries"], [])
        self.assertEqual(result["status"], "incomplete")

    def test_undecidable_entries_make_the_search_incomplete(self):
        a = with_revision(make_entry("project:a", "a"))
        broken_identity = with_revision(make_entry("project:b", "b"))
        broken_identity["identity"] = {"kind": "test_environment"}
        duplicate = with_revision(make_entry("project:b", "dup"))
        no_ref = with_revision(make_entry("project:b", "noref"))
        no_ref["entry_ref"] = ""
        for label, extra in {
            "broken_identity": [broken_identity],
            "duplicate_ref": [duplicate, dict(duplicate)],
            "missing_ref": [no_ref],
        }.items():
            with self.subTest(case=label):
                result = search([a, *extra])
                self.assertEqual(result["status"], "incomplete")
                self.assertEqual(result["entries"], [])
                self.assertFalse(result["complete"])

    def test_unreadable_scope_on_unrelated_looking_entry_is_not_assumed_unrelated(
        self,
    ):
        a = with_revision(make_entry("project:a", "a"))
        b = with_revision(make_entry("project:b", "b"))
        b["scope_refs"] = []
        self.assertEqual(search([a, b])["status"], "incomplete")
        c = with_revision(make_entry("project:b", "c"))
        c["scope_refs"] = None
        self.assertEqual(search([a, c])["status"], "incomplete")

    def test_incomplete_listing_and_invalid_inputs_stay_incomplete(self):
        a = with_revision(make_entry())
        self.assertFalse(search([a], listing_complete=False)["complete"])
        self.assertEqual(search("x")["status"], "incomplete")
        self.assertEqual(search(["x"])["status"], "incomplete")
        self.assertEqual(
            search([a], scope_refs={1})["reason"], "lookup_scope_refs_invalid"
        )

    def test_root_lookup_blocks_on_truncation_unreadable_and_noncanonical_files(
        self,
    ):
        a = make_entry("project:a", "a")
        b = make_entry("project:b", "b")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "knowledge"
            for entry in (a, b):
                created = knowledge.create_entry(
                    root,
                    entry,
                    complete_root_snapshot=True,
                    atomic_create_if_absent_available=True,
                    current_dependencies=DEPENDENCIES,
                )
                self.assertEqual(created["status"], "created")
            params = {
                "scope_refs": {"project:a"},
                "kind": None,
                "environment": None,
                "version": None,
                "current_dependencies": DEPENDENCIES,
            }
            full = knowledge.lookup_root(root, **params)
            self.assertEqual(full["status"], "complete")
            truncated = knowledge.lookup_root(root, max_entries=1, **params)
            self.assertEqual(truncated["status"], "incomplete")
            self.assertEqual(truncated["entries"], [])
            missing_root = knowledge.lookup_root(root / "absent", **params)
            self.assertEqual(missing_root["status"], "incomplete")

            (root / "notes.md").write_text("# stray", encoding="utf-8")
            stray = knowledge.lookup_root(root, **params)
            self.assertEqual(stray["status"], "incomplete")
            (root / "notes.md").unlink()

            (root / f"{b['entry_ref']}.md").write_text("garbage", encoding="utf-8")
            corrupted = knowledge.lookup_root(root, **params)
            self.assertEqual(corrupted["status"], "incomplete")
            self.assertEqual(corrupted["entries"], [])


class KnowledgeSessionResumeTests(unittest.TestCase):
    def test_create_read_lookup_revalidate_lookup_across_sessions(self):
        a = make_entry("project:a", "a", "config:a")
        b = make_entry("project:b", "b", "config:b")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "knowledge"
            # Session 1: create both entries.
            created = {}
            for entry in (a, b):
                created[entry["entry_ref"]] = knowledge.create_entry(
                    root,
                    entry,
                    complete_root_snapshot=True,
                    atomic_create_if_absent_available=True,
                    current_dependencies=DEPENDENCIES,
                )
            # Session 2: only the stored revision crosses the boundary.
            stored = knowledge.read_entry(
                root,
                a["entry_ref"],
                expected_revision=created[a["entry_ref"]]["entry_revision"],
            )
            self.assertEqual(stored["status"], "current")
            first = knowledge.lookup(
                [knowledge.lookup_input(stored)],
                scope_refs={"project:a"},
                kind=None,
                environment="staging",
                version="v1",
                current_dependencies=DEPENDENCIES,
                listing_complete=True,
            )
            self.assertEqual(
                first["entries"][0]["entry_revision"],
                created[a["entry_ref"]]["entry_revision"],
            )
            # Session 3: config:b changed. Only B is selected for revalidation and
            # A keeps being served; HEAD-like unrelated changes select nothing.
            changed = {"config:a": "r1", "config:b": "r2", "repo:HEAD": "new"}
            snapshot = knowledge.read_root_entries(root)
            self.assertTrue(snapshot["complete"])
            plan = knowledge.plan_revalidation(
                snapshot["entries"], current_dependencies=changed
            )
            self.assertEqual(plan["status"], "complete")
            self.assertEqual(
                [t["entry_ref"] for t in plan["targets"]], [b["entry_ref"]]
            )
            self.assertEqual(plan["unaffected_refs"], [a["entry_ref"]])
            self.assertEqual(
                plan["targets"][0]["expected_entry_revision"],
                created[b["entry_ref"]]["entry_revision"],
            )
            self.assertEqual(plan["targets"][0]["reason"], "dependency_changed")
            only_head = knowledge.plan_revalidation(
                snapshot["entries"],
                current_dependencies={**DEPENDENCIES, "repo:HEAD": "new"},
            )
            self.assertEqual(only_head["targets"], [])

            still_a = knowledge.lookup_root(
                root,
                scope_refs={"project:a"},
                kind=None,
                environment=None,
                version=None,
                current_dependencies=changed,
            )
            self.assertEqual(
                [e["entry_ref"] for e in still_a["entries"]], [a["entry_ref"]]
            )
            stale_b = knowledge.lookup_root(
                root,
                scope_refs={"project:b"},
                kind=None,
                environment=None,
                version=None,
                current_dependencies=changed,
            )
            self.assertEqual(stale_b["entries"], [])
            self.assertEqual(stale_b["historical_excluded_refs"], [b["entry_ref"]])

            # The update must be conditional on the revision read in this session.
            update = knowledge.plan_update(
                expected_entry_revision=plan["targets"][0]["expected_entry_revision"],
                native_atomic_conditional_write=True,
                current_entry=b,
                updated_entry={
                    **b,
                    "currentness_dependencies": [{"ref": "config:b", "revision": "r2"}],
                },
            )
            self.assertEqual(update["status"], "conditional_write_required")
            # A stale revision from an older session cannot be read back.
            replaced_raw = knowledge.render_entry({**b, "content": "revised elsewhere"})
            (root / f"{b['entry_ref']}.md").write_bytes(replaced_raw)
            old = knowledge.read_entry(
                root,
                b["entry_ref"],
                expected_revision=created[b["entry_ref"]]["entry_revision"],
            )
            self.assertEqual(old["reason"], "historical_revision_unavailable")
            self.assertEqual(
                knowledge.handle_update_conflict(
                    target_entry_revision_changed=True,
                    different_entry_only_changed=False,
                )["auto_merge"],
                False,
            )

    def test_revalidation_ignores_other_scopes_and_rejects_broken_entries(self):
        a = with_revision(make_entry("project:a", "a", "config:a"))
        b = with_revision(make_entry("project:b", "b", "config:b"))
        stale = {"config:a": "r2", "config:b": "r2"}
        scoped = knowledge.plan_revalidation(
            [a, b], current_dependencies=stale, scope_refs={"project:a"}
        )
        self.assertEqual([t["entry_ref"] for t in scoped["targets"]], [a["entry_ref"]])
        limited = knowledge.plan_revalidation(
            [a, b], current_dependencies=stale, changed_refs={"config:b"}
        )
        self.assertEqual([t["entry_ref"] for t in limited["targets"]], [b["entry_ref"]])
        unresolved = knowledge.plan_revalidation([a], current_dependencies={})
        self.assertEqual(unresolved["targets"][0]["reason"], "dependency_unresolved")
        cases, _ = mismatched_entries()
        rejected = knowledge.plan_revalidation(
            [with_revision(cases["scope"])], current_dependencies=stale
        )
        self.assertEqual(rejected["status"], "incomplete")
        self.assertEqual(rejected["targets"], [])


class KnowledgeImprovementHandoffTests(unittest.TestCase):
    def test_reference_hand_off_carries_refs_not_authority(self):
        entry = with_revision(make_entry(), "sha256:stored")
        result = knowledge.improvement_reference(
            entry, current_dependencies=DEPENDENCIES
        )
        self.assertEqual(result["status"], "ready")
        reference = result["reference"]
        self.assertEqual(reference["entry_revision"], "sha256:stored")
        self.assertEqual(reference["scope_refs"], ["project:a"])
        self.assertEqual(reference["source_refs"], entry["provenance"])
        self.assertEqual(reference["adoption_decision"], "owner_pending")
        self.assertEqual(reference["authority"], "reference_only")
        self.assertNotIn("content", reference)
        unverified = knowledge.improvement_reference(
            with_revision(make_entry(state="要再検証")),
            current_dependencies=DEPENDENCIES,
        )
        self.assertEqual(
            unverified["reference"]["unverified"], ["entry_state_not_valid"]
        )
        self.assertEqual(
            knowledge.improvement_reference(make_entry())["reason"],
            "entry_revision_unavailable",
        )
        cases, _ = mismatched_entries()
        self.assertEqual(
            knowledge.improvement_reference(with_revision(cases["kind"]))["status"],
            "blocked",
        )

    def test_update_request_requires_approved_improvement_and_is_not_completion(self):
        current = make_entry()
        updated = {**current, "content": "approved reuse"}
        request = {
            "improvement_ref": "IMP-1",
            "approval_ref": "APR-1",
            "source_refs": [{"ref": "evaluation:EV-1", "revision": "r4"}],
            "expected_entry_revision": "sha256:stored",
        }
        ok = knowledge.plan_approved_improvement_update(
            request,
            current_entry=current,
            updated_entry=updated,
            native_atomic_conditional_write=True,
        )
        self.assertEqual(ok["status"], "conditional_write_required")
        self.assertIs(ok["improvement_completed"], False)
        for broken, reason in (
            ({**request, "approval_ref": ""}, "approved_improvement_required"),
            ({**request, "source_refs": []}, "improvement_source_refs_required"),
            (
                {**request, "source_refs": [{"ref": "evaluation:EV-1"}]},
                "improvement_source_requires_revision",
            ),
        ):
            with self.subTest(reason=reason):
                result = knowledge.plan_approved_improvement_update(
                    broken,
                    current_entry=current,
                    updated_entry=updated,
                    native_atomic_conditional_write=True,
                )
                self.assertEqual(result["reason"], reason)


class LocalCasProvider:
    """Test fixture standing in for a storage-native conditional write.

    It is not evidence that a real provider offers CAS; it only lets the helper's
    update / readback / conflict handling be exercised.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self.calls = 0

    def __call__(self, path, content, expected_revision):
        with self._lock:
            self.calls += 1
            current = "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
            if current != expected_revision:
                return {"status": "conflict"}
            temporary = path.with_name(path.name + ".tmp")
            temporary.write_bytes(content)
            for attempt in range(50):
                try:
                    os.replace(temporary, path)
                    break
                except PermissionError:
                    # Windows refuses to replace a file another thread is reading.
                    if attempt == 49:
                        return {"status": "blocked", "reason": "replace_denied"}
                    time.sleep(0.01)
            return {"status": "written"}


class KnowledgeUpdateAndReadbackTests(unittest.TestCase):
    def created(self, root, entry):
        return knowledge.create_entry(
            root,
            entry,
            complete_root_snapshot=True,
            atomic_create_if_absent_available=True,
            current_dependencies=DEPENDENCIES,
        )

    def test_update_and_replacement_plans_cannot_skip_identity_checks(self):
        entry = make_entry()
        for kwargs in (
            {},
            {"current_entry": entry},
            {"updated_entry": entry},
        ):
            with self.subTest(kwargs=sorted(kwargs)):
                result = knowledge.plan_update(
                    expected_entry_revision="sha256:stored",
                    native_atomic_conditional_write=True,
                    **kwargs,
                )
                self.assertEqual(result["status"], "blocked")
                self.assertEqual(result["reason"], "entry_identity_unverified")
        other = make_entry(subject="other")
        for kwargs in ({}, {"old_entry": entry}, {"new_entry": other}):
            with self.subTest(replacement=sorted(kwargs)):
                result = knowledge.plan_replacement(
                    old_entry_ref=entry["entry_ref"],
                    new_entry_ref=other["entry_ref"],
                    native_atomic_multi_entry_update=True,
                    **kwargs,
                )
                self.assertEqual(result["reason"], "entry_identity_unverified")

    def test_ref_mismatch_is_rejected_even_when_identity_fields_agree(self):
        entry = make_entry()
        forged = {**entry, "entry_ref": knowledge.canonical_entry_ref({"kind": "x"})}
        plan = knowledge.plan_update(
            expected_entry_revision="sha256:stored",
            native_atomic_conditional_write=True,
            current_entry=entry,
            updated_entry=forged,
        )
        self.assertEqual(plan["reason"], "entry_ref_does_not_match_identity")
        replacement = knowledge.plan_replacement(
            old_entry_ref=entry["entry_ref"],
            new_entry_ref=forged["entry_ref"],
            native_atomic_multi_entry_update=True,
            old_entry=entry,
            new_entry=forged,
        )
        self.assertEqual(replacement["status"], "blocked")

    def test_create_returns_only_a_read_back_revision(self):
        entry = make_entry()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "knowledge"
            result = self.created(root, entry)
            self.assertEqual(result["status"], "created")
            self.assertIs(result["readback_verified"], True)
            stored = knowledge.read_entry(root, entry["entry_ref"])
            self.assertEqual(result["entry_revision"], stored["entry_revision"])

    def test_create_blocks_when_stored_bytes_do_not_read_back(self):
        entry = make_entry()
        original = knowledge.read_entry

        def altered(root, entry_ref, **kwargs):
            result = original(root, entry_ref, **kwargs)
            return {**result, "entry_revision": "sha256:other"}

        with tempfile.TemporaryDirectory() as temp:
            knowledge.read_entry = altered
            try:
                result = self.created(Path(temp) / "knowledge", entry)
            finally:
                knowledge.read_entry = original
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["reason"], "created_entry_readback_mismatch")

    def test_create_read_lookup_update_lookup_across_sessions(self):
        a = make_entry("project:a", "a", "config:a")
        b = make_entry("project:b", "b", "config:b")
        provider = LocalCasProvider()
        deps_r2 = {"config:a": "r2", "config:b": "r1"}
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "knowledge"
            created = {e["entry_ref"]: self.created(root, e) for e in (a, b)}
            # Session 2: read, hand the stored revision to lookup.
            read = knowledge.read_entry(root, a["entry_ref"])
            rev0 = read["entry_revision"]
            self.assertEqual(rev0, created[a["entry_ref"]]["entry_revision"])
            first = knowledge.lookup(
                [knowledge.lookup_input(read)],
                scope_refs={"project:a"},
                kind=None,
                environment=None,
                version=None,
                current_dependencies=DEPENDENCIES,
                listing_complete=True,
            )
            self.assertEqual(first["entries"][0]["entry_revision"], rev0)
            # Session 3: config:a changed; A is stale, B untouched.
            stale = knowledge.lookup_root(
                root,
                scope_refs={"project:a"},
                kind=None,
                environment=None,
                version=None,
                current_dependencies=deps_r2,
            )
            self.assertEqual(stale["entries"], [])
            self.assertEqual(stale["historical_excluded_refs"], [a["entry_ref"]])
            plan = knowledge.plan_revalidation(
                knowledge.read_root_entries(root)["entries"],
                current_dependencies=deps_r2,
            )
            self.assertEqual(
                [t["entry_ref"] for t in plan["targets"]], [a["entry_ref"]]
            )
            self.assertEqual(plan["targets"][0]["expected_entry_revision"], rev0)
            # Revalidate A with the revision read above; B is not rewritten.
            b_before = (root / f"{b['entry_ref']}.md").read_bytes()
            revalidated = {
                **read["entry"],
                "currentness_dependencies": [{"ref": "config:a", "revision": "r2"}],
                "last_verified": {"at": "2026-11-10", "condition": "staging/v1"},
            }
            updated = knowledge.update_entry(
                root,
                revalidated,
                expected_entry_revision=rev0,
                conditional_write=provider,
                current_dependencies=deps_r2,
            )
            self.assertEqual(updated["status"], "updated")
            self.assertIs(updated["readback_verified"], True)
            rev1 = updated["entry_revision"]
            self.assertNotEqual(rev0, rev1)
            self.assertEqual(b_before, (root / f"{b['entry_ref']}.md").read_bytes())
            # Session 4: lookup serves A again with the new revision.
            after = knowledge.lookup_root(
                root,
                scope_refs={"project:a"},
                kind=None,
                environment=None,
                version=None,
                current_dependencies=deps_r2,
            )
            self.assertEqual(
                [(e["entry_ref"], e["entry_revision"]) for e in after["entries"]],
                [(a["entry_ref"], rev1)],
            )
            self.assertNotIn(
                "entry_revision",
                (root / f"{a['entry_ref']}.md").read_text(encoding="utf-8"),
            )
            old = knowledge.read_entry(root, a["entry_ref"], expected_revision=rev0)
            self.assertEqual(old["reason"], "historical_revision_unavailable")
            # A writer still holding rev0 is a conflict, never an auto-merge.
            late = knowledge.update_entry(
                root,
                {**revalidated, "content": "late writer"},
                expected_entry_revision=rev0,
                conditional_write=provider,
                current_dependencies=deps_r2,
            )
            self.assertEqual(late["status"], "conflict")
            self.assertIs(late["auto_merge"], False)
            self.assertEqual(
                knowledge.read_entry(root, a["entry_ref"])["entry_revision"], rev1
            )

    def test_concurrent_updates_with_one_expected_revision_write_once(self):
        entry = make_entry()
        provider = LocalCasProvider()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "knowledge"
            created = self.created(root, entry)
            revision = created["entry_revision"]
            variants = [{**entry, "content": f"writer {n}"} for n in range(6)]
            with ThreadPoolExecutor(max_workers=6) as executor:
                results = list(
                    executor.map(
                        lambda e: knowledge.update_entry(
                            root,
                            e,
                            expected_entry_revision=revision,
                            conditional_write=provider,
                            current_dependencies=DEPENDENCIES,
                        ),
                        variants,
                    )
                )
            # Exactly one writer wins. Every other outcome is a conflict or a
            # fail-closed block (e.g. a transient Windows read/replace denial);
            # none may report success or merge.
            winners = [r for r in results if r["status"] == "updated"]
            self.assertEqual(len(winners), 1)
            for loser in results:
                if loser is not winners[0]:
                    self.assertIn(loser["status"], {"conflict", "blocked"})
                    self.assertIsNot(loser.get("auto_merge"), True)
            winner = winners[0]
            stored = knowledge.read_entry(root, entry["entry_ref"])
            self.assertEqual(stored["entry_revision"], winner["entry_revision"])

    def test_update_fails_closed_without_provider_or_with_bad_input(self):
        entry = make_entry()
        provider = LocalCasProvider()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "knowledge"
            revision = self.created(root, entry)["entry_revision"]
            common = {
                "expected_entry_revision": revision,
                "current_dependencies": DEPENDENCIES,
            }
            no_provider = knowledge.update_entry(
                root, entry, conditional_write=None, **common
            )
            self.assertEqual(
                no_provider["reason"], "atomic_conditional_write_unavailable"
            )
            cases = {
                "revision_in_body": (
                    {**entry, "entry_revision": revision},
                    "entry_revision_must_not_be_in_body",
                ),
                "identity_kind": (
                    {**entry, "kind": "test_focus"},
                    "entry_identity_invalid",
                ),
                "empty_content": ({**entry, "content": ""}, "entry_contract_invalid"),
                "stale_but_valid": (
                    {
                        **entry,
                        "currentness_dependencies": [
                            {"ref": "config:a", "revision": "r9"}
                        ],
                    },
                    "entry_dependencies_not_current",
                ),
            }
            for name, (updated, reason) in cases.items():
                with self.subTest(case=name):
                    result = knowledge.update_entry(
                        root, updated, conditional_write=provider, **common
                    )
                    self.assertEqual(result["status"], "blocked")
                    self.assertEqual(result["reason"], reason)
            self.assertEqual(provider.calls, 0)
            self.assertEqual(
                knowledge.read_entry(root, entry["entry_ref"])["entry_revision"],
                revision,
            )
            missing = knowledge.update_entry(
                root,
                make_entry(subject="absent"),
                conditional_write=provider,
                **common,
            )
            self.assertEqual(missing["reason"], "stored_entry_unreadable")

    def test_update_does_not_trust_a_provider_that_does_not_confirm_or_read_back(self):
        entry = make_entry()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "knowledge"
            revision = self.created(root, entry)["entry_revision"]
            common = {
                "expected_entry_revision": revision,
                "current_dependencies": DEPENDENCIES,
            }
            revised = {**entry, "content": "revised"}
            unconfirmed = knowledge.update_entry(
                root,
                revised,
                conditional_write=lambda *_: {"status": "blocked", "reason": "no_cas"},
                **common,
            )
            self.assertEqual(unconfirmed["reason"], "conditional_write_not_confirmed")
            self.assertEqual(unconfirmed["provider_reason"], "no_cas")
            lying = knowledge.update_entry(
                root,
                revised,
                conditional_write=lambda *_: {"status": "written"},
                **common,
            )
            self.assertEqual(lying["reason"], "updated_entry_readback_mismatch")
            self.assertEqual(
                knowledge.update_entry(
                    root, revised, conditional_write=lambda *_: None, **common
                )["reason"],
                "conditional_write_not_confirmed",
            )

    def test_identity_change_is_not_an_update(self):
        entry = make_entry()
        provider = LocalCasProvider()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "knowledge"
            revision = self.created(root, entry)["entry_revision"]
            renamed = make_entry(subject="renamed")
            result = knowledge.update_entry(
                root,
                renamed,
                expected_entry_revision=revision,
                conditional_write=provider,
                current_dependencies=DEPENDENCIES,
            )
            self.assertEqual(result["status"], "blocked")
            self.assertEqual(provider.calls, 0)


class KnowledgeHandoffStateTests(unittest.TestCase):
    def reference(self, entry, dependencies=DEPENDENCIES):
        return knowledge.improvement_reference(
            with_revision(entry), current_dependencies=dependencies
        )["reference"]

    def test_current_entry_carries_the_shared_handoff_fields(self):
        entry = make_entry()
        reference = self.reference(entry)
        self.assertEqual(reference["owner_skill"], "qa-knowledge")
        self.assertEqual(reference["artifact_ref"], entry["entry_ref"])
        self.assertEqual(reference["content_hash"], "sha256:stored")
        self.assertEqual(reference["state"], "current")
        self.assertIsNone(reference["resume"])
        self.assertEqual(reference["unresolved"], [])
        self.assertTrue(reference["validation"]["valid"])
        self.assertIsNone(reference["validation"]["result_ref"])
        self.assertEqual(
            reference["currentness_dependencies"], entry["currentness_dependencies"]
        )
        self.assertIs(reference["required_approval"]["required"], True)
        self.assertIsNone(reference["required_approval"]["approval_ref"])

    def test_stale_blocked_and_replaced_states_name_their_resume_point(self):
        stale = self.reference(make_entry(), {"config:a": "r2"})
        self.assertEqual(stale["state"], "stale")
        self.assertEqual(stale["resume"]["action"], "revalidation")
        self.assertEqual(stale["resume"]["expected_entry_revision"], "sha256:stored")
        self.assertEqual(stale["resume"]["changed_refs"], ["config:a"])

        unresolved = self.reference(make_entry(), {})
        self.assertEqual(unresolved["state"], "blocked")
        self.assertEqual(unresolved["unresolved"], ["config:a"])
        self.assertEqual(unresolved["resume"]["action"], "obtain_dependency_revisions")

        unchecked = knowledge.improvement_reference(with_revision(make_entry()))
        self.assertEqual(unchecked["reference"]["state"], "blocked")
        self.assertIn(
            "current_dependencies_not_checked", unchecked["reference"]["unverified"]
        )

        needs_revalidation = self.reference(make_entry(state="要再検証"))
        self.assertEqual(needs_revalidation["state"], "stale")

        replaced_entry = make_entry(state="置換済み", replacement_ref="KN-" + "a" * 64)
        replaced = self.reference(replaced_entry)
        self.assertEqual(replaced["state"], "stale")
        self.assertEqual(replaced["resume"]["action"], "use_replacement")
        self.assertEqual(replaced["resume"]["replacement_ref"], "KN-" + "a" * 64)

        invalid = self.reference(make_entry(content=""))
        self.assertEqual(invalid["state"], "blocked")
        self.assertFalse(invalid["validation"]["valid"])

    def test_approved_update_result_keeps_the_approval_and_source_refs(self):
        current = make_entry()
        request = {
            "improvement_ref": "IMP-1",
            "approval_ref": "APR-1",
            "source_refs": [{"ref": "evaluation:EV-1", "revision": "r4"}],
            "expected_entry_revision": "sha256:stored",
        }
        result = knowledge.plan_approved_improvement_update(
            request,
            current_entry=current,
            updated_entry={**current, "content": "approved"},
            native_atomic_conditional_write=True,
        )
        self.assertEqual(result["approval_ref"], "APR-1")
        self.assertEqual(result["improvement_ref"], "IMP-1")
        self.assertEqual(result["source_refs"], request["source_refs"])
        self.assertIs(result["improvement_completed"], False)
        # An approved request still cannot bypass the identity checks.
        broken = knowledge.plan_approved_improvement_update(
            request,
            current_entry=current,
            updated_entry={**current, "kind": "test_focus"},
            native_atomic_conditional_write=True,
        )
        self.assertEqual(broken["reason"], "entry_identity_invalid")


class IsolatedPackagingTests(unittest.TestCase):
    """The new helpers run from a copied Skill package without sibling Skills."""

    HEADER = """\
import importlib.util
import sys
import tempfile

spec = importlib.util.spec_from_file_location("module", sys.argv[1])
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
"""

    def run_copied(self, skill, filename, body):
        with tempfile.TemporaryDirectory() as temp:
            copied = Path(temp) / skill
            shutil.copytree(REPO_ROOT / "skills" / skill, copied)
            script = Path(temp) / "probe.py"
            script.write_text(self.HEADER + body, encoding="utf-8")
            env = dict(os.environ, PYTHONPATH="", PYTHONUTF8="1")
            result = subprocess.run(
                [sys.executable, "-I", str(script), str(copied / "scripts" / filename)],
                cwd=temp,
                env=env,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_knowledge_lookup_update_and_handoff_run_from_a_copy(self):
        body = """\
identity = {"kind": "test_environment", "scope_refs": ["p"], "subject": "s"}
entry = {
    "schema_version": "1",
    "entry_ref": module.canonical_entry_ref(identity),
    "identity": identity,
    "kind": "test_environment",
    "content": "c",
    "scope_refs": ["p"],
    "applicability": {"environment": ["e"], "version": "v"},
    "provenance": [{"ref": "a", "revision": "1"}],
    "currentness_dependencies": [{"ref": "d", "revision": "1"}],
    "last_verified": {"at": "t", "condition": "c"},
    "state": "有効",
    "replacement_ref": None,
    "related_qa_refs": [],
}
deps = {"d": "1"}
with tempfile.TemporaryDirectory() as root:
    created = module.create_entry(
        root,
        entry,
        complete_root_snapshot=True,
        atomic_create_if_absent_available=True,
        current_dependencies=deps,
    )
    assert created["status"] == "created" and created["readback_verified"]
    found = module.lookup_root(
        root,
        scope_refs={"p"},
        kind=None,
        environment=None,
        version=None,
        current_dependencies=deps,
    )
    assert found["status"] == "complete" and len(found["entries"]) == 1
    blocked = module.update_entry(
        root,
        entry,
        expected_entry_revision=created["entry_revision"],
        conditional_write=None,
        current_dependencies=deps,
    )
    assert blocked["status"] == "blocked"
"""
        self.run_copied("qa-knowledge", "knowledge_runtime.py", body)

    def test_exploratory_direct_start_runs_from_a_copy(self):
        body = """\
result = module.resolve_direct_start({"e2e_failure_ref": "run:1"})
assert result["status"] == "route" and "mode" not in result
assert module.resolve_direct_start({})["status"] == "blocked"
"""
        self.run_copied("exploratory-testing", "exploratory_runtime.py", body)


class KnowledgeValidatorTests(unittest.TestCase):
    def output(self, entry):
        return (
            "```json\n"
            + json.dumps(
                {
                    "action": "create",
                    "entry": entry,
                    "currentness_status": "current",
                    "storage": {
                        "atomic_create_if_absent": True,
                        "complete_root_snapshot": True,
                    },
                },
                ensure_ascii=False,
            )
            + "\n```"
        )

    def test_identity_mismatch_fails_the_deterministic_validator(self):
        ok = validator.validate(self.output(make_entry()), {}, "KN-X")
        self.assertTrue(
            next(a for a in ok.assertions if a.id == "KN-D012").status == "pass"
        )
        cases, _ = mismatched_entries()
        for name, entry in cases.items():
            with self.subTest(case=name):
                result = validator.validate(self.output(entry), {}, "KN-X")
                assertion = next(a for a in result.assertions if a.id == "KN-D012")
                self.assertEqual(assertion.status, "fail")

    def test_existing_candidate_outputs_still_pass(self):
        for eval_id in ("KN-OUT-001", "KN-OUT-002"):
            output = (
                REPO_ROOT
                / "skills/qa-knowledge/evals/output/cases"
                / eval_id.lower()
                / "output.md"
            )
            self.assertEqual(grade("qa-knowledge", eval_id, output)["status"], "pass")


def charter(**overrides):
    value = {
        "purpose": "explore checkout without prepared cases",
        "in_scope": ["checkout"],
        "out_of_scope": ["payment"],
        "source_refs": ["change:CHG-1"],
        "focus_refs": ["risk:R-1"],
        "timebox_or_exit_condition": "20 minutes",
        "allowed_origins": ["https://staging.example.test"],
        "allowed_operations": ["navigate", "submit_form"],
        "side_effect_operations": ["submit_form"],
        "side_effect_scope": "test account only",
        "side_effect_action_definition": "one form submission",
        "side_effect_maximum": 2,
        "cleanup_plan": "delete created test data",
        "evidence_policy": "refs only",
        "block_conditions": ["origin changes"],
    }
    value.update(overrides)
    return value


def session(**overrides):
    value = {
        "schema_version": "1",
        "session_ref": "SES-1",
        "mode": "exploration",
        "charter": charter(),
        "state": "実行中",
        "observations": [
            {
                "observation_ref": "OBS-1",
                "action_or_observation": "open order detail",
                "observed_fact": "cancelled order shown",
                "evidence_refs": ["ev:1"],
            }
        ],
        "findings": [
            {
                "finding_ref": "FND-1",
                "source_observation_refs": ["OBS-1"],
                "evidence_refs": ["ev:1"],
                "follow_up_reason": "spec for cancelled orders unclear",
                "recommended_routing": "question-analysis",
            }
        ],
        "unresolved": [],
        "cleanup": {"required": False, "status": "対象なし", "evidence_refs": []},
        "residual_side_effect": [],
        "charter_snapshot_identity": "snap-1",
        "source_revisions": {"change:CHG-1": "rev-chg-1"},
    }
    value.update(overrides)
    return value


class ExploratoryDirectStartTests(unittest.TestCase):
    def test_charter_starts_exploration_without_formal_test_artifacts(self):
        result = exploratory.resolve_direct_start({"charter": charter()})
        self.assertEqual(result["status"], "start")
        self.assertEqual(result["mode"], "exploration")
        self.assertEqual(result["required_prerequisite_skills"], [])
        self.assertIs(result["formal_tc_required"], False)

    def test_unowned_symptom_starts_investigation(self):
        result = exploratory.resolve_direct_start(
            {
                "symptom_ref": "symptom:S-1",
                "owner_unknown": True,
                "charter": charter(),
            }
        )
        self.assertEqual(result["status"], "start")
        self.assertEqual(result["mode"], "investigation")
        self.assertEqual(result["start_ref"], {"symptom_ref": "symptom:S-1"})
        for key in ("hypothesis_ref", "unresolved_finding_ref"):
            with self.subTest(start=key):
                started = exploratory.resolve_direct_start(
                    {key: "x:1", "owner_unknown": True, "charter": charter()}
                )
                self.assertEqual(started["status"], "start")
                self.assertEqual(started["mode"], "investigation")

    def test_known_owner_work_is_not_routed_to_investigation(self):
        cases = {
            "e2e": (
                {"e2e_failure_ref": "run:R-1", "owner_unknown": True},
                "e2e-test-result-analysis",
            ),
            "tc": ({"known_tc_ref": "TC-1"}, "test-execution"),
            "ui": ({"current_ui_collection": True}, "test-target-inspection"),
            "owner": (
                {"symptom_ref": "s:1", "known_owner": "question-analysis"},
                "question-analysis",
            ),
        }
        for name, (request, owner) in cases.items():
            with self.subTest(case=name):
                result = exploratory.resolve_direct_start(
                    {**request, "charter": charter()}
                )
                self.assertEqual(result["status"], "route")
                self.assertEqual(result["owner_skill"], owner)
                self.assertNotIn("mode", result)

    def test_start_is_blocked_without_charter_symptom_or_owner_confirmation(self):
        self.assertEqual(
            exploratory.resolve_direct_start({})["reason"],
            "charter_or_unowned_symptom_required",
        )
        self.assertEqual(
            exploratory.resolve_direct_start({"symptom_ref": "s:1"})["reason"],
            "owner_resolution_unconfirmed",
        )
        self.assertEqual(
            exploratory.resolve_direct_start(
                {"symptom_ref": "s:1", "owner_unknown": True}
            )["reason"],
            "charter_required",
        )
        incomplete = exploratory.resolve_direct_start(
            {"charter": charter(cleanup_plan="")}
        )
        self.assertEqual(incomplete["reason"], "charter_invalid")
        self.assertEqual(incomplete["missing_fields"], ["cleanup_plan"])

    def test_blocked_session_resumes_only_with_the_same_charter_and_environment(self):
        snapshot = {"url": "https://staging.example.test", "build": "1"}
        environment = {"browser": "chromium"}
        identity = exploratory.charter_identity(charter(), snapshot, environment)
        blocked = session(state="ブロック中", charter_snapshot_identity=identity)
        self.assertEqual(
            exploratory.can_resume(blocked, charter(), snapshot, environment)["status"],
            "resume_allowed",
        )
        self.assertEqual(
            exploratory.can_resume(
                blocked, charter(side_effect_maximum=9), snapshot, environment
            )["status"],
            "new_session_required",
        )
        self.assertEqual(
            exploratory.can_resume(
                blocked, charter(), {**snapshot, "build": "2"}, environment
            )["status"],
            "new_session_required",
        )
        done = {**blocked, "state": "完了"}
        self.assertEqual(
            exploratory.can_resume(done, charter(), snapshot, environment)["reason"],
            "completed_session_is_immutable",
        )

    def test_session_without_formal_test_case_is_valid(self):
        self.assertTrue(exploratory.validate_session(session())["valid"])


class ExploratoryFindingHandoffTests(unittest.TestCase):
    def test_finding_hand_off_is_reference_only(self):
        result = exploratory.build_follow_up_handoff(
            session(), "FND-1", session_revision="rev-7"
        )
        self.assertEqual(result["status"], "ready")
        handoff = result["handoff"]
        self.assertEqual(handoff["session_ref"], "SES-1")
        self.assertEqual(handoff["session_revision"], "rev-7")
        self.assertEqual(handoff["source_observation_refs"], ["OBS-1"])
        self.assertEqual(handoff["evidence_refs"], ["ev:1"])
        self.assertEqual(
            handoff["source_refs"], [{"ref": "change:CHG-1", "revision": "rev-chg-1"}]
        )
        self.assertEqual(handoff["follow_up_owner_skill"], "question-analysis")
        self.assertEqual(handoff["owner_skill"], "exploratory-testing")
        self.assertEqual(handoff["artifact_ref"], "SES-1")
        self.assertEqual(handoff["content_hash"], "rev-7")
        self.assertEqual(handoff["state"], "current")
        self.assertIsNone(handoff["resume"])
        self.assertTrue(handoff["validation"]["valid"])
        self.assertIsNone(handoff["validation"]["result_ref"])
        self.assertIs(handoff["required_approval"]["required"], False)
        self.assertEqual(handoff["promotion"], "not_promoted")
        self.assertIs(handoff["formal_defect"], False)
        self.assertIs(handoff["knowledge_entry_created"], False)
        serialized = json.dumps(handoff, ensure_ascii=False)
        self.assertNotIn("cancelled order shown", serialized)
        self.assertNotIn("open order detail", serialized)

    def test_defect_candidate_and_knowledge_routes_are_not_promotions(self):
        for owner, action in (
            ("defect-management", "defect_candidate_review"),
            ("qa-knowledge", "triage"),
        ):
            with self.subTest(owner=owner):
                data = session()
                data["findings"][0]["recommended_routing"] = owner
                result = exploratory.build_follow_up_handoff(
                    data, "FND-1", session_revision="rev-7"
                )
                self.assertEqual(result["handoff"]["target_action"], action)
                self.assertIs(result["handoff"]["formal_defect"], False)
                self.assertIs(result["handoff"]["knowledge_entry_created"], False)

    def test_unresolved_symptom_is_not_auto_promoted_to_defect_candidate(self):
        data = session(unresolved=["cause owner unknown"])
        data["findings"][0]["recommended_routing"] = "defect-management"
        result = exploratory.build_follow_up_handoff(
            data, "FND-1", session_revision="rev-7"
        )
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["reason"], "unresolved_finding_not_defect_candidate")
        data["findings"][0]["recommended_routing"] = "question-analysis"
        self.assertEqual(
            exploratory.build_follow_up_handoff(
                data, "FND-1", session_revision="rev-7"
            )["status"],
            "ready",
        )

    def test_hand_off_state_and_resume_point_follow_the_session(self):
        blocked = exploratory.build_follow_up_handoff(
            session(state="ブロック中"), "FND-1", session_revision="rev-7"
        )["handoff"]
        self.assertEqual(blocked["state"], "blocked")
        self.assertEqual(blocked["resume"]["action"], "resume_session")
        unresolved = exploratory.build_follow_up_handoff(
            session(unresolved=["cause owner unknown"]),
            "FND-1",
            session_revision="rev-7",
        )["handoff"]
        self.assertEqual(unresolved["state"], "current")
        self.assertEqual(
            unresolved["resume"]["action"], "owner_resolution_or_investigation"
        )
        self.assertEqual(unresolved["unresolved"], ["cause owner unknown"])
        data = session()
        data["findings"][0]["recommended_routing"] = "defect-management"
        defect = exploratory.build_follow_up_handoff(
            data, "FND-1", session_revision="rev-7"
        )["handoff"]
        self.assertIs(defect["required_approval"]["required"], True)
        self.assertIsNone(defect["required_approval"]["approval_ref"])

    def test_hand_off_fails_closed_without_revision_finding_owner_or_valid_session(
        self,
    ):
        self.assertEqual(
            exploratory.build_follow_up_handoff(
                session(), "FND-1", session_revision=""
            )["reason"],
            "session_revision_required",
        )
        self.assertEqual(
            exploratory.build_follow_up_handoff(
                session(), "FND-9", session_revision="rev-7"
            )["reason"],
            "finding_not_in_session",
        )
        data = session()
        data["findings"][0]["recommended_routing"] = "someone-else"
        self.assertEqual(
            exploratory.build_follow_up_handoff(
                data, "FND-1", session_revision="rev-7"
            )["reason"],
            "unknown_follow_up_owner",
        )
        broken = session()
        broken["findings"][0]["source_observation_refs"] = ["OBS-404"]
        result = exploratory.build_follow_up_handoff(
            broken, "FND-1", session_revision="rev-7"
        )
        self.assertEqual(result["reason"], "session_invalid")


class ExploratoryInvestigationOriginTests(unittest.TestCase):
    """An unresolved Finding alone must start a Session that stays valid."""

    ORIGINS = ("symptom_ref", "hypothesis_ref", "unresolved_finding_ref")

    def start(self, key, **extra):
        return exploratory.resolve_direct_start(
            {key: "origin:1", "owner_unknown": True, "charter": charter(), **extra}
        )

    def test_every_origin_starts_a_session_that_validates_resumes_and_grades(self):
        snapshot = {"url": "https://staging.example.test", "build": "1"}
        environment = {"browser": "chromium"}
        for key in self.ORIGINS:
            with self.subTest(origin=key):
                started = self.start(key)
                self.assertEqual(started["status"], "start")
                self.assertEqual(started["mode"], "investigation")
                self.assertEqual(started["start_ref"], {key: "origin:1"})
                # The origin is kept in the Charter that is saved with the Session.
                saved_charter = started["charter"]
                self.assertEqual(saved_charter[key], "origin:1")
                self.assertTrue(
                    exploratory.validate_charter("investigation", saved_charter)[
                        "valid"
                    ]
                )
                saved = session(mode="investigation", charter=saved_charter)
                self.assertEqual(exploratory.validate_session(saved)["issues"], [])
                identity = exploratory.charter_identity(
                    saved_charter, snapshot, environment
                )
                blocked = {
                    **saved,
                    "state": "ブロック中",
                    "charter_snapshot_identity": identity,
                }
                self.assertEqual(
                    exploratory.can_resume(
                        blocked, saved_charter, snapshot, environment
                    )["status"],
                    "resume_allowed",
                )
                # A different origin is a different investigation.
                self.assertEqual(
                    exploratory.can_resume(
                        blocked,
                        {**saved_charter, key: "origin:2"},
                        snapshot,
                        environment,
                    )["status"],
                    "new_session_required",
                )
                output = "```json\n" + json.dumps(saved, ensure_ascii=False) + "\n```"
                graded = exploratory_validator.validate(output, {}, "EXP-X")
                origin_check = next(a for a in graded.assertions if a.id == "EXP-D003")
                self.assertEqual(origin_check.status, "pass")

    def test_investigation_without_a_usable_origin_is_rejected(self):
        self.assertIn(
            "investigation_requires_symptom_or_hypothesis",
            exploratory.validate_charter("investigation", charter())["issues"],
        )
        for bad in ("", "  ", None, ["x"], {"a": 1}, 5):
            with self.subTest(origin=bad):
                self.assertFalse(
                    exploratory.validate_charter(
                        "investigation", charter(unresolved_finding_ref=bad)
                    )["valid"]
                )
        broken = session(mode="investigation")
        self.assertIn(
            "investigation_requires_symptom_or_hypothesis",
            exploratory.validate_session(broken)["issues"],
        )
        output = "```json\n" + json.dumps(broken, ensure_ascii=False) + "\n```"
        graded = exploratory_validator.validate(output, {}, "EXP-X")
        self.assertEqual(
            next(a for a in graded.assertions if a.id == "EXP-D003").status, "fail"
        )

    def test_non_string_start_ref_is_blocked_not_started(self):
        result = exploratory.resolve_direct_start(
            {
                "unresolved_finding_ref": ["FND-1"],
                "owner_unknown": True,
                "charter": charter(),
            }
        )
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["reason"], "charter_invalid")

    def test_known_owner_and_known_failures_still_route_without_a_mode(self):
        cases = {
            "known_owner": {"known_owner": "question-analysis"},
            "e2e_failure": {"e2e_failure_ref": "run:R-1"},
            "ui_collection": {"current_ui_collection": True},
        }
        for name, extra in cases.items():
            with self.subTest(case=name):
                result = exploratory.resolve_direct_start(
                    {
                        "unresolved_finding_ref": "FND-1",
                        "owner_unknown": True,
                        "charter": charter(),
                        **extra,
                    }
                )
                self.assertEqual(result["status"], "route")
                self.assertNotIn("mode", result)
                self.assertNotIn("charter", result)
        tc = exploratory.resolve_direct_start({"known_tc_ref": "TC-1"})
        self.assertEqual(tc["owner_skill"], "test-execution")

    def test_unresolved_finding_start_needs_owner_confirmation_and_a_valid_charter(
        self,
    ):
        unconfirmed = exploratory.resolve_direct_start(
            {"unresolved_finding_ref": "FND-1", "charter": charter()}
        )
        self.assertEqual(unconfirmed["reason"], "owner_resolution_unconfirmed")
        missing = exploratory.resolve_direct_start(
            {"unresolved_finding_ref": "FND-1", "owner_unknown": True}
        )
        self.assertEqual(missing["reason"], "charter_required")
        invalid = exploratory.resolve_direct_start(
            {
                "unresolved_finding_ref": "FND-1",
                "owner_unknown": True,
                "charter": charter(allowed_origins=[], cleanup_plan=""),
            }
        )
        self.assertEqual(invalid["reason"], "charter_invalid")
        self.assertIn("allowed_origins_required", invalid["issues"])
        self.assertEqual(invalid["missing_fields"], ["cleanup_plan"])

    def test_exploration_start_needs_no_origin_and_adds_no_formal_testware(self):
        result = exploratory.resolve_direct_start({"charter": charter()})
        self.assertEqual(result["status"], "start")
        self.assertEqual(result["mode"], "exploration")
        self.assertEqual(result["required_prerequisite_skills"], [])
        self.assertIs(result["formal_tc_required"], False)
        self.assertTrue(
            exploratory.validate_session(
                session(mode="exploration", charter=result["charter"])
            )["valid"]
        )


class ExploratorySourceRevisionHandoffTests(unittest.TestCase):
    def handoff(self, **overrides):
        return exploratory.build_follow_up_handoff(
            session(**overrides), "FND-1", session_revision="rev-session"
        )

    def test_each_source_keeps_its_own_revision_apart_from_the_session(self):
        data = session(
            charter=charter(
                source_refs=[
                    {"ref": "change:CHG-1", "revision": "rev-a"},
                    "spec:SPEC-2",
                ]
            ),
            source_revisions={"spec:SPEC-2": "rev-b"},
        )
        result = exploratory.build_follow_up_handoff(
            data, "FND-1", session_revision="rev-session"
        )
        self.assertEqual(result["status"], "ready")
        handoff = result["handoff"]
        self.assertEqual(
            handoff["source_refs"],
            [
                {"ref": "change:CHG-1", "revision": "rev-a"},
                {"ref": "spec:SPEC-2", "revision": "rev-b"},
            ],
        )
        self.assertEqual(handoff["session_revision"], "rev-session")
        self.assertEqual(handoff["content_hash"], "rev-session")
        self.assertNotIn(
            "rev-session", [item["revision"] for item in handoff["source_refs"]]
        )
        self.assertEqual(handoff["state"], "current")
        self.assertIsNone(handoff["resume"])
        self.assertEqual(handoff["unresolved"], [])

    def test_missing_source_revision_is_unresolved_and_never_current(self):
        for overrides in (
            {"source_revisions": {}},
            {"source_revisions": None},
            {"source_revisions": {"change:CHG-1": ""}},
            {"source_revisions": {"change:CHG-1": 7}},
        ):
            with self.subTest(overrides=overrides):
                result = self.handoff(**overrides)
                self.assertEqual(result["status"], "ready")
                handoff = result["handoff"]
                self.assertEqual(
                    handoff["source_refs"],
                    [{"ref": "change:CHG-1", "revision": None}],
                )
                self.assertEqual(handoff["state"], "blocked")
                self.assertEqual(
                    handoff["unresolved"],
                    ["source_revision_unresolved:change:CHG-1"],
                )
                self.assertEqual(handoff["resume"]["action"], "record_source_revisions")
                self.assertEqual(handoff["session_revision"], "rev-session")
        data = session()
        data.pop("source_revisions")
        self.assertEqual(
            exploratory.build_follow_up_handoff(
                data, "FND-1", session_revision="rev-session"
            )["handoff"]["state"],
            "blocked",
        )

    def test_a_blocked_session_keeps_its_own_resume_point(self):
        handoff = self.handoff(state="ブロック中", source_revisions={})["handoff"]
        self.assertEqual(handoff["state"], "blocked")
        self.assertEqual(handoff["resume"]["action"], "resume_session")
        self.assertEqual(
            handoff["unresolved"], ["source_revision_unresolved:change:CHG-1"]
        )

    def test_defect_candidate_is_not_built_from_an_unconfirmed_source(self):
        data = session(source_revisions={})
        data["findings"][0]["recommended_routing"] = "defect-management"
        result = exploratory.build_follow_up_handoff(
            data, "FND-1", session_revision="rev-session"
        )
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["reason"], "source_revision_unresolved")
        self.assertEqual(result["unresolved"], ["change:CHG-1"])
        data["unresolved"] = ["cause owner unknown"]
        self.assertEqual(
            exploratory.build_follow_up_handoff(
                data, "FND-1", session_revision="rev-session"
            )["reason"],
            "unresolved_finding_not_defect_candidate",
        )
        data["unresolved"] = []
        data["source_revisions"] = {"change:CHG-1": "rev-chg-1"}
        ready = exploratory.build_follow_up_handoff(
            data, "FND-1", session_revision="rev-session"
        )["handoff"]
        self.assertEqual(ready["state"], "current")
        self.assertIs(ready["required_approval"]["required"], True)
        self.assertIsNone(ready["required_approval"]["approval_ref"])
        self.assertIs(ready["formal_defect"], False)

    def test_malformed_sources_and_unresolved_do_not_raise_or_invent_revisions(self):
        data = session(
            charter=charter(source_refs=[["a"], {"ref": ""}, 5, "spec:ok"]),
            source_revisions=["not-a-map"],
        )
        result = exploratory.build_follow_up_handoff(
            data, "FND-1", session_revision="rev-session"
        )
        self.assertEqual(result["status"], "ready")
        sources = result["handoff"]["source_refs"]
        self.assertEqual(len(sources), 4)
        self.assertTrue(all(item["revision"] is None for item in sources))
        self.assertEqual(result["handoff"]["state"], "blocked")
        # A bare string is not a source list: it is an invalid source set, and its
        # revision is never looked up (see ExploratorySourceSetHandoffTests).
        text_sources = session(
            charter=charter(source_refs="change:CHG-1"),
            source_revisions={"change:CHG-1": "rev-chg-1"},
        )
        handoff = exploratory.build_follow_up_handoff(
            text_sources, "FND-1", session_revision="rev-session"
        )["handoff"]
        self.assertEqual(handoff["source_refs"], [])
        self.assertEqual(handoff["unresolved"], ["source_refs_invalid"])
        self.assertEqual(handoff["state"], "blocked")
        for broken in ({"unresolved": "text"}, {"unresolved": {"a": 1}}):
            with self.subTest(broken=broken):
                self.assertEqual(
                    self.handoff(**broken)["reason"], "unresolved_must_be_list"
                )

    def test_hand_off_still_copies_no_observed_text(self):
        serialized = json.dumps(self.handoff()["handoff"], ensure_ascii=False)
        self.assertNotIn("cancelled order shown", serialized)
        self.assertNotIn("open order detail", serialized)


def bad_values():
    return [[], {}, ["x"], {"a": 1}, 5, True, None, ""]


class KnowledgeMalformedEntryTests(unittest.TestCase):
    """JSON arrays / objects in scalar fields must become issues, not exceptions."""

    def variants(self):
        base = make_entry()
        cases = {}
        for index, bad in enumerate(bad_values()):
            kind_identity = {**base["identity"], "kind": bad}
            cases[f"identity.kind#{index}"] = {
                **base,
                "identity": kind_identity,
                "entry_ref": knowledge.canonical_entry_ref(kind_identity),
            }
            scope_identity = {**base["identity"], "scope_refs": bad}
            cases[f"identity.scope_refs#{index}"] = {
                **base,
                "identity": scope_identity,
                "entry_ref": knowledge.canonical_entry_ref(scope_identity),
            }
            cases[f"state#{index}"] = {**base, "state": bad}
            cases[f"kind#{index}"] = {**base, "kind": bad}
            cases[f"entry_ref#{index}"] = {**base, "entry_ref": bad}
            cases[f"scope_refs#{index}"] = {**base, "scope_refs": bad}
            cases[f"identity#{index}"] = {**base, "identity": bad}
            cases[f"dependencies#{index}"] = {**base, "currentness_dependencies": bad}
        cases["dependency.ref"] = {
            **base,
            "currentness_dependencies": [{"ref": ["x"], "revision": "r1"}],
        }
        cases["dependency.revision"] = {
            **base,
            "currentness_dependencies": [{"ref": "config:a", "revision": ["r"]}],
        }
        return cases

    def test_validation_never_raises_and_rejects_every_variant(self):
        for name, entry in self.variants().items():
            with self.subTest(case=name):
                self.assertFalse(knowledge.validate_entry(entry)["valid"])
                knowledge.identity_issues(entry)
                self.assertFalse(
                    knowledge.validate_entry(
                        entry,
                        current_dependencies=DEPENDENCIES,
                        entry_revision="sha256:stored",
                    )["valid"]
                )

    def test_non_object_entries_are_invalid_not_exceptions(self):
        for value in (None, [], "text", 5):
            with self.subTest(value=value):
                result = knowledge.validate_entry(value)
                self.assertEqual(result["issues"], ["entry_must_be_object"])
                with tempfile.TemporaryDirectory() as temp:
                    created = knowledge.create_entry(
                        Path(temp) / "knowledge",
                        value,
                        complete_root_snapshot=True,
                        atomic_create_if_absent_available=True,
                        current_dependencies=DEPENDENCIES,
                    )
                self.assertEqual(created["status"], "blocked")
                self.assertEqual(
                    knowledge.plan_revalidation(
                        [value], current_dependencies=DEPENDENCIES
                    )["status"],
                    "incomplete",
                )

    def test_applicable_malformed_entries_make_lookup_incomplete(self):
        for name, entry in self.variants().items():
            with self.subTest(case=name):
                result = search([with_revision(entry)])
                self.assertEqual(result["status"], "incomplete")
                self.assertEqual(result["entries"], [])
                self.assertIs(result["complete"], False)
        # Entries that certainly do not apply still do not stop the search.
        unrelated = make_entry("project:other", "other")
        unrelated["state"] = ["x"]
        valid = with_revision(make_entry())
        result = search([with_revision(unrelated), valid])
        self.assertEqual(result["status"], "complete")
        self.assertEqual(
            [e["entry_ref"] for e in result["entries"]], [valid["entry_ref"]]
        )

    def test_create_update_replacement_and_revalidation_block_instead_of_raising(
        self,
    ):
        stored = make_entry()
        provider = LocalCasProvider()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "knowledge"
            created = knowledge.create_entry(
                root,
                stored,
                complete_root_snapshot=True,
                atomic_create_if_absent_available=True,
                current_dependencies=DEPENDENCIES,
            )
            revision = created["entry_revision"]
            for name, entry in self.variants().items():
                with self.subTest(case=name):
                    snapshot = json.dumps(entry, sort_keys=True)
                    new = knowledge.create_entry(
                        Path(temp) / "other",
                        entry,
                        complete_root_snapshot=True,
                        atomic_create_if_absent_available=True,
                        current_dependencies=DEPENDENCIES,
                    )
                    self.assertEqual(new["status"], "blocked")
                    update = knowledge.update_entry(
                        root,
                        entry,
                        expected_entry_revision=revision,
                        conditional_write=provider,
                        current_dependencies=DEPENDENCIES,
                    )
                    self.assertEqual(update["status"], "blocked")
                    # plan_update only judges identity; it must not raise either.
                    knowledge.plan_update(
                        expected_entry_revision=revision,
                        native_atomic_conditional_write=True,
                        current_entry=stored,
                        updated_entry=entry,
                    )
                    replacement = knowledge.plan_replacement(
                        old_entry_ref=stored["entry_ref"],
                        new_entry_ref="KN-" + "0" * 64,
                        native_atomic_multi_entry_update=True,
                        old_entry=stored,
                        new_entry=entry,
                    )
                    self.assertEqual(replacement["status"], "blocked")
                    plan = knowledge.plan_revalidation(
                        [with_revision(entry)], current_dependencies=DEPENDENCIES
                    )
                    self.assertIn(plan["status"], {"complete", "incomplete"})
                    knowledge.improvement_reference(
                        with_revision(entry), current_dependencies=DEPENDENCIES
                    )
                    # The invalid entry is neither repaired nor stored.
                    self.assertEqual(snapshot, json.dumps(entry, sort_keys=True))
            self.assertEqual(
                knowledge.read_entry(root, stored["entry_ref"])["entry_revision"],
                revision,
            )
            self.assertEqual(provider.calls, 0)

    def test_stored_entry_with_malformed_identity_is_blocked_on_read(self):
        entry = make_entry()
        malformed = {**entry["identity"], "kind": ["test_environment"]}
        bad = {**entry, "identity": malformed}
        bad["entry_ref"] = knowledge.canonical_entry_ref(malformed)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / f"{bad['entry_ref']}.md").write_bytes(knowledge.render_entry(bad))
            result = knowledge.read_entry(root, bad["entry_ref"])
            self.assertEqual(result["status"], "blocked")
            self.assertEqual(result["reason"], "entry_identity_invalid")
            snapshot = knowledge.read_root_entries(root)
            self.assertIs(snapshot["complete"], False)
            self.assertEqual(
                knowledge.lookup_root(
                    root,
                    scope_refs={"project:a"},
                    kind=None,
                    environment=None,
                    version=None,
                    current_dependencies=DEPENDENCIES,
                )["status"],
                "incomplete",
            )

    def test_hand_off_inputs_do_not_raise_on_malformed_values(self):
        entry = with_revision(make_entry(provenance=5, currentness_dependencies="x"))
        reference = knowledge.improvement_reference(
            entry, current_dependencies=DEPENDENCIES
        )
        self.assertEqual(reference["reference"]["state"], "blocked")
        self.assertEqual(reference["reference"]["source_refs"], [])
        self.assertEqual(
            knowledge.plan_approved_improvement_update(
                None,
                current_entry=entry,
                updated_entry=entry,
                native_atomic_conditional_write=True,
            )["reason"],
            "approved_improvement_required",
        )


class KnowledgeRevalidationInputTests(unittest.TestCase):
    STALE = {"config:a": "r2", "config:b": "r2"}

    def test_invalid_inputs_are_rejected_not_silently_dropped(self):
        good = with_revision(make_entry("project:a", "a", "config:a"))
        for bad in (None, [], "text", 5, ["x"]):
            with self.subTest(entry=bad):
                plan = knowledge.plan_revalidation(
                    [bad, good], current_dependencies=self.STALE
                )
                self.assertEqual(plan["status"], "incomplete")
                self.assertEqual(
                    plan["rejected"],
                    [{"entry_ref": None, "issues": ["entry_must_be_object"]}],
                )
                # The decidable entry is still planned.
                self.assertEqual(
                    [t["entry_ref"] for t in plan["targets"]], [good["entry_ref"]]
                )
        for name, kwargs in (
            ("not-a-list", {"entries": "x"}),
            ("scope", {"entries": [good], "scope_refs": ["project:a"]}),
            ("scope-items", {"entries": [good], "scope_refs": {1}}),
            ("changed", {"entries": [good], "changed_refs": "config:a"}),
        ):
            with self.subTest(case=name):
                entries = kwargs.pop("entries")
                plan = knowledge.plan_revalidation(
                    entries, current_dependencies=self.STALE, **kwargs
                )
                self.assertEqual(plan["status"], "incomplete")
                self.assertEqual(plan["targets"], [])
        self.assertEqual(
            knowledge.plan_revalidation([good], current_dependencies=None)["status"],
            "incomplete",
        )

    def test_a_target_requires_the_stored_revision_that_was_read(self):
        stored = make_entry("project:a", "a", "config:a")
        for revision in (None, "", 7, ["sha256:x"]):
            with self.subTest(revision=revision):
                body = {**stored}
                if revision is not None:
                    body["entry_revision"] = revision
                plan = knowledge.plan_revalidation(
                    [body], current_dependencies=self.STALE
                )
                self.assertEqual(plan["status"], "incomplete")
                self.assertEqual(plan["targets"], [])
                self.assertEqual(
                    plan["rejected"],
                    [
                        {
                            "entry_ref": stored["entry_ref"],
                            "issues": ["entry_revision_unavailable"],
                        }
                    ],
                )
        # An entry that needs no revalidation, or lies outside the requested scope,
        # does not need a revision and is not rejected for lacking one.
        unchanged = knowledge.plan_revalidation(
            [stored], current_dependencies={"config:a": "r1"}
        )
        self.assertEqual(unchanged["status"], "complete")
        self.assertEqual(unchanged["unaffected_refs"], [stored["entry_ref"]])
        outside = knowledge.plan_revalidation(
            [stored], current_dependencies=self.STALE, scope_refs={"project:z"}
        )
        self.assertEqual(outside["status"], "complete")
        self.assertEqual(
            (outside["targets"], outside["unaffected_refs"], outside["rejected"]),
            ([], [], []),
        )

    def test_states_are_reported_separately(self):
        changed = with_revision(make_entry("project:a", "a", "config:a"))
        unresolved = with_revision(make_entry("project:b", "b", "config:b"))
        invalid = with_revision(make_entry("project:c", "c", "config:c"))
        invalid["scope_refs"] = ["project:other"]
        fine = with_revision(make_entry("project:d", "d", "config:d"))
        plan = knowledge.plan_revalidation(
            [changed, unresolved, invalid, fine],
            current_dependencies={"config:a": "r2", "config:d": "r1"},
        )
        reasons = {t["entry_ref"]: t["reason"] for t in plan["targets"]}
        self.assertEqual(reasons[changed["entry_ref"]], "dependency_changed")
        self.assertEqual(reasons[unresolved["entry_ref"]], "dependency_unresolved")
        self.assertEqual(
            [r["entry_ref"] for r in plan["rejected"]], [invalid["entry_ref"]]
        )
        self.assertIn("identity_scope_refs_mismatch", plan["rejected"][0]["issues"])
        self.assertEqual(plan["unaffected_refs"], [fine["entry_ref"]])
        self.assertEqual(plan["status"], "incomplete")

    def test_scoped_revalidation_ignores_unrelated_changes_and_head(self):
        a = with_revision(make_entry("project:a", "a", "config:a"), "sha256:ra")
        b = with_revision(make_entry("project:b", "b", "config:b"), "sha256:rb")
        head_only = knowledge.plan_revalidation(
            [a, b],
            current_dependencies={"config:a": "r1", "config:b": "r1", "repo:HEAD": "9"},
        )
        self.assertEqual((head_only["status"], head_only["targets"]), ("complete", []))
        scoped = knowledge.plan_revalidation(
            [a, b],
            current_dependencies=self.STALE,
            scope_refs={"project:a"},
            changed_refs={"config:a", "config:unrelated"},
        )
        self.assertEqual(
            [(t["entry_ref"], t["expected_entry_revision"]) for t in scoped["targets"]],
            [(a["entry_ref"], "sha256:ra")],
        )
        self.assertEqual(scoped["unaffected_refs"], [])
        unrelated = knowledge.plan_revalidation(
            [a, b],
            current_dependencies=self.STALE,
            changed_refs={"config:unrelated"},
        )
        self.assertEqual(unrelated["targets"], [])
        self.assertEqual(
            unrelated["unaffected_refs"], sorted([a["entry_ref"], b["entry_ref"]])
        )

    def test_update_plan_needs_a_string_revision(self):
        entry = make_entry()
        for revision in (None, "", 7, ["sha256:x"], {"a": 1}):
            with self.subTest(revision=revision):
                plan = knowledge.plan_update(
                    expected_entry_revision=revision,
                    native_atomic_conditional_write=True,
                    current_entry=entry,
                    updated_entry=entry,
                )
                self.assertEqual(plan["reason"], "entry_revision_unavailable")

    def test_planned_revision_is_the_conditional_update_condition(self):
        entry = make_entry("project:a", "a", "config:a")
        provider = LocalCasProvider()
        stale = {"config:a": "r2"}
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "knowledge"
            created = knowledge.create_entry(
                root,
                entry,
                complete_root_snapshot=True,
                atomic_create_if_absent_available=True,
                current_dependencies=DEPENDENCIES,
            )
            plan = knowledge.plan_revalidation(
                knowledge.read_root_entries(root)["entries"],
                current_dependencies=stale,
                scope_refs={"project:a"},
            )
            self.assertEqual(plan["status"], "complete")
            target = plan["targets"][0]
            self.assertEqual(
                target["expected_entry_revision"], created["entry_revision"]
            )
            revalidated = {
                **entry,
                "currentness_dependencies": [{"ref": "config:a", "revision": "r2"}],
            }
            updated = knowledge.update_entry(
                root,
                revalidated,
                expected_entry_revision=target["expected_entry_revision"],
                conditional_write=provider,
                current_dependencies=stale,
            )
            self.assertEqual(updated["status"], "updated")
            after = knowledge.plan_revalidation(
                knowledge.read_root_entries(root)["entries"],
                current_dependencies=stale,
            )
            self.assertEqual((after["targets"], after["status"]), ([], "complete"))
            late = knowledge.update_entry(
                root,
                {**revalidated, "content": "late"},
                expected_entry_revision=target["expected_entry_revision"],
                conditional_write=provider,
                current_dependencies=stale,
            )
            self.assertEqual(late["status"], "conflict")


class ExploratoryMalformedInputTests(unittest.TestCase):
    """Arrays / objects in scalar Session fields are issues, not exceptions."""

    def test_malformed_charter_and_session_values_are_issues(self):
        for bad in bad_values():
            cases = {
                "allowed_operations": session(charter=charter(allowed_operations=bad)),
                "side_effect_operations": session(
                    charter=charter(side_effect_operations=[bad])
                ),
                "mode": session(mode=bad),
                "state": session(state=bad),
                "cleanup": session(cleanup=bad),
                "observation_ref": session(
                    observations=[
                        {**session()["observations"][0], "observation_ref": bad}
                    ]
                ),
                "finding_ref": session(
                    findings=[{**session()["findings"][0], "finding_ref": bad}]
                ),
                "finding_sources": session(
                    findings=[
                        {**session()["findings"][0], "source_observation_refs": bad}
                    ]
                ),
                "finding_source_item": session(
                    findings=[
                        {**session()["findings"][0], "source_observation_refs": [bad]}
                    ]
                ),
            }
            for name, data in cases.items():
                with self.subTest(field=name, value=bad):
                    result = exploratory.validate_session(data)
                    self.assertFalse(result["valid"])
                    self.assertTrue(result["issues"])
                    for owner in ("question-analysis", "test-analysis"):
                        data["findings"][0]["recommended_routing"] = owner
                        handoff = exploratory.build_follow_up_handoff(
                            data, "FND-1", session_revision="rev-1"
                        )
                        self.assertEqual(handoff["status"], "blocked")
        for value in (None, [], "text", 5):
            with self.subTest(session=value):
                self.assertEqual(
                    exploratory.validate_session(value)["issues"],
                    ["session_must_be_object"],
                )
                self.assertFalse(
                    exploratory.validate_charter("exploration", value)["valid"]
                )


class ExploratorySourceSetHandoffTests(unittest.TestCase):
    """A hand-off needs a source set it can re-read; an empty one is never current."""

    def handoff(self, source_refs, owner="question-analysis", **overrides):
        data = session(charter=charter(source_refs=source_refs), **overrides)
        data["findings"][0]["recommended_routing"] = owner
        return exploratory.build_follow_up_handoff(
            data, "FND-1", session_revision="rev-session"
        )

    def test_empty_source_set_is_blocked_with_its_own_resume_point(self):
        result = self.handoff([])
        self.assertEqual(result["status"], "ready")
        handoff = result["handoff"]
        self.assertNotEqual(handoff["state"], "current")
        self.assertEqual(handoff["state"], "blocked")
        self.assertEqual(handoff["source_refs"], [])
        self.assertIn("source_refs_missing", handoff["unresolved"])
        self.assertEqual(handoff["resume"]["action"], "record_source_refs")
        # The Session revision is never used as a source revision.
        self.assertEqual(handoff["session_revision"], "rev-session")
        self.assertNotIn("rev-session", json.dumps(handoff["source_refs"]))

    def test_null_or_blank_source_refs_stop_at_session_validation(self):
        for value in (None, ""):
            with self.subTest(source_refs=value):
                result = self.handoff(value)
                self.assertEqual(result["status"], "blocked")
                self.assertEqual(result["reason"], "session_invalid")
                self.assertIn("missing_charter_field:source_refs", result["issues"])
                self.assertNotIn("handoff", result)

    def test_absent_source_refs_key_is_not_a_valid_source_set(self):
        data = session()
        del data["charter"]["source_refs"]
        result = exploratory.build_follow_up_handoff(
            data, "FND-1", session_revision="rev-session"
        )
        self.assertEqual(result["status"], "blocked")

    def test_invalid_source_set_is_distinguished_from_a_missing_one(self):
        for value in ("change:CHG-1", {"ref": "change:CHG-1"}, 5, True):
            with self.subTest(source_refs=value):
                handoff = self.handoff(value)["handoff"]
                self.assertEqual(handoff["state"], "blocked")
                self.assertEqual(handoff["source_refs"], [])
                self.assertIn("source_refs_invalid", handoff["unresolved"])
                self.assertNotIn("source_refs_missing", handoff["unresolved"])
                self.assertEqual(handoff["resume"]["action"], "record_source_refs")

    def test_missing_set_differs_from_a_source_without_revision(self):
        no_revision = self.handoff(["change:CHG-1"], source_revisions={})["handoff"]
        self.assertEqual(no_revision["resume"]["action"], "record_source_revisions")
        self.assertEqual(
            no_revision["unresolved"], ["source_revision_unresolved:change:CHG-1"]
        )
        self.assertEqual(
            no_revision["source_refs"], [{"ref": "change:CHG-1", "revision": None}]
        )
        none = self.handoff([])["handoff"]
        self.assertEqual(none["unresolved"], ["source_refs_missing"])

    def test_a_blocked_session_keeps_its_resume_point_but_reports_the_gap(self):
        handoff = self.handoff([], state="ブロック中")["handoff"]
        self.assertEqual(handoff["state"], "blocked")
        self.assertEqual(handoff["resume"]["action"], "resume_session")
        self.assertIn("source_refs_missing", handoff["unresolved"])

    def test_defect_candidate_stops_without_a_source_set(self):
        for value, reason in (
            ([], "source_refs_missing"),
            ("change:CHG-1", "source_refs_invalid"),
            (5, "source_refs_invalid"),
        ):
            with self.subTest(source_refs=value):
                result = self.handoff(value, owner="defect-management")
                self.assertEqual(result["status"], "blocked")
                self.assertEqual(result["reason"], reason)
                self.assertEqual(result["next"], "record_source_refs")
                self.assertNotIn("handoff", result)

    def test_valid_sources_and_revisions_keep_the_current_hand_off(self):
        for owner in ("question-analysis", "qa-knowledge", "defect-management"):
            with self.subTest(owner=owner):
                handoff = self.handoff(["change:CHG-1"], owner=owner)["handoff"]
                self.assertEqual(handoff["state"], "current")
                self.assertIsNone(handoff["resume"])
                self.assertEqual(handoff["unresolved"], [])
                self.assertEqual(
                    handoff["source_refs"],
                    [{"ref": "change:CHG-1", "revision": "rev-chg-1"}],
                )
                self.assertEqual(handoff["follow_up_owner_skill"], owner)

    def test_a_charter_without_sources_can_still_start_an_exploration(self):
        started = exploratory.resolve_direct_start({"charter": charter(source_refs=[])})
        self.assertEqual(started["status"], "start")
        self.assertFalse(started["formal_tc_required"])
        self.assertEqual(
            exploratory.validate_session(session(charter=charter(source_refs=[])))[
                "issues"
            ],
            [],
        )


class ExploratoryRoutingValidationTests(unittest.TestCase):
    """recommended_routing must be a registered owner name; never an exception."""

    BAD = [
        ["question-analysis"],
        {"owner": "question-analysis"},
        None,
        "",
        123,
        "unknown-owner",
    ]

    def with_routing(self, value):
        data = session()
        data["findings"][0]["recommended_routing"] = value
        return data

    def test_bad_routing_never_raises_and_is_rejected(self):
        for value in self.BAD:
            with self.subTest(routing=value):
                data = self.with_routing(value)
                result = exploratory.build_follow_up_handoff(
                    data, "FND-1", session_revision="rev-1"
                )
                self.assertEqual(result["status"], "blocked")
                self.assertNotIn("handoff", result)

    def test_non_string_routing_is_a_session_validation_issue(self):
        for value in self.BAD[:5]:
            with self.subTest(routing=value):
                result = exploratory.validate_session(self.with_routing(value))
                self.assertFalse(result["valid"])
                self.assertIn(
                    "finding_missing_evidence_or_reason:FND-1", result["issues"]
                )

    def test_unregistered_owner_is_blocked_and_never_rerouted(self):
        data = self.with_routing("unknown-owner")
        result = exploratory.build_follow_up_handoff(
            data, "FND-1", session_revision="rev-1"
        )
        self.assertEqual(result["reason"], "unknown_follow_up_owner")
        self.assertNotIn("follow_up_owner_skill", json.dumps(result))

    def test_hand_off_rejects_bad_routing_even_when_session_validation_passes(self):
        # build_follow_up_handoff() must not rely on validate_session() alone.
        for value in self.BAD:
            with self.subTest(routing=value):
                data = self.with_routing(value)
                with unittest.mock.patch.object(
                    exploratory,
                    "validate_session",
                    return_value={"valid": True, "issues": []},
                ):
                    result = exploratory.build_follow_up_handoff(
                        data, "FND-1", session_revision="rev-1"
                    )
                self.assertEqual(result["status"], "blocked")
                self.assertEqual(result["reason"], "unknown_follow_up_owner")

    def test_registered_owners_keep_their_actions_and_approval_requirement(self):
        expected = {
            "question-analysis": (None, False),
            "qa-knowledge": ("triage", False),
            "defect-management": ("defect_candidate_review", True),
        }
        for owner, (action, approval) in expected.items():
            with self.subTest(owner=owner):
                result = exploratory.build_follow_up_handoff(
                    self.with_routing(owner), "FND-1", session_revision="rev-1"
                )
                self.assertEqual(result["status"], "ready")
                handoff = result["handoff"]
                self.assertEqual(handoff["follow_up_owner_skill"], owner)
                self.assertEqual(handoff["target_action"], action)
                self.assertIs(handoff["required_approval"]["required"], approval)

    def test_evidence_refs_must_be_a_list_of_refs(self):
        for value in ("ev:1", {"a": "ev:1"}, [""], [["ev:1"]], [5], 5):
            with self.subTest(evidence_refs=value):
                data = session()
                data["findings"][0]["evidence_refs"] = value
                self.assertFalse(exploratory.validate_session(data)["valid"])
                self.assertEqual(
                    exploratory.build_follow_up_handoff(
                        data, "FND-1", session_revision="rev-1"
                    )["status"],
                    "blocked",
                )


def _document(data):
    return "```json\n" + json.dumps(data, ensure_ascii=False) + "\n```"


def _grade(data):
    graded = exploratory_validator.validate(_document(data), {}, "EXP-X")
    return {item.id: item.status for item in graded.assertions}


class ExploratoryValidatorRuntimeParityTests(unittest.TestCase):
    """The deterministic validator must not accept what the runtime rejects."""

    ORIGINS = ("symptom_ref", "hypothesis_ref", "unresolved_finding_ref")
    BAD_ORIGINS = ("", "  ", ["x"], {"a": 1}, 5, True)

    def investigation(self, **origin):
        return session(mode="investigation", charter=charter(**origin))

    def test_valid_origins_pass(self):
        for key in (*self.ORIGINS, "symptom", "hypothesis"):
            with self.subTest(origin=key):
                self.assertEqual(
                    _grade(self.investigation(**{key: "origin:1"}))["EXP-D003"],
                    "pass",
                )

    def test_unusable_origins_fail_in_the_validator_as_in_the_runtime(self):
        for key in (*self.ORIGINS, "symptom", "hypothesis"):
            for bad in self.BAD_ORIGINS:
                with self.subTest(origin=key, value=bad):
                    data = self.investigation(**{key: bad})
                    self.assertEqual(_grade(data)["EXP-D003"], "fail")
                    self.assertIn(
                        "investigation_requires_symptom_or_hypothesis",
                        exploratory.validate_charter("investigation", data["charter"])[
                            "issues"
                        ],
                    )

    def test_exploration_needs_no_origin(self):
        self.assertEqual(_grade(session())["EXP-D003"], "pass")

    def test_malformed_refs_fail_without_raising(self):
        bad_values = [[], {}, ["x"], {"a": 1}, 5, True, None, ""]
        for bad in bad_values:
            variants = {
                "observation_ref": session(
                    observations=[
                        {**session()["observations"][0], "observation_ref": bad}
                    ]
                ),
                "finding_ref": session(
                    findings=[{**session()["findings"][0], "finding_ref": bad}]
                ),
                "source_observation_refs": session(
                    findings=[
                        {**session()["findings"][0], "source_observation_refs": bad}
                    ]
                ),
                "source_observation_ref_item": session(
                    findings=[
                        {**session()["findings"][0], "source_observation_refs": [bad]}
                    ]
                ),
                "finding_evidence_refs": session(
                    findings=[{**session()["findings"][0], "evidence_refs": bad}]
                ),
                "recommended_routing": session(
                    findings=[{**session()["findings"][0], "recommended_routing": bad}]
                ),
            }
            if bad == ["x"]:  # a valid evidence ref list
                del variants["finding_evidence_refs"]
            for name, data in variants.items():
                with self.subTest(field=name, value=bad):
                    grades = _grade(data)
                    self.assertEqual(grades["EXP-D004"], "fail")
                    self.assertFalse(exploratory.validate_session(data)["valid"])

    def test_malformed_top_level_values_fail_without_raising(self):
        for bad in ([], {}, ["x"], {"a": 1}, 5, None):
            variants = {
                "mode": session(mode=bad),
                "state": session(state=bad),
                "charter": session(charter=bad),
                "cleanup": session(cleanup=bad),
                "observations": session(observations=bad),
                "findings": session(findings=bad),
            }
            for name, data in variants.items():
                with self.subTest(field=name, value=bad):
                    grades = _grade(data)
                    self.assertEqual(
                        sorted(grades),
                        [f"EXP-D00{n}" for n in range(1, 9)],
                    )

    def test_valid_observation_to_finding_links_still_pass(self):
        grades = _grade(session())
        self.assertEqual(grades["EXP-D004"], "pass")
        self.assertEqual(grades["EXP-D001"], "pass")

    def test_each_runtime_rejected_session_fails_the_matching_validator_check(self):
        data = session()
        data["findings"][0]["source_observation_refs"] = []
        self.assertFalse(exploratory.validate_session(data)["valid"])
        self.assertEqual(_grade(data)["EXP-D004"], "fail")
        data = session()
        data["findings"][0]["source_observation_refs"] = ["OBS-404"]
        self.assertEqual(_grade(data)["EXP-D004"], "fail")
        data = session()
        data["findings"].append(dict(data["findings"][0]))
        self.assertEqual(_grade(data)["EXP-D004"], "fail")


class KnowledgeRootSymlinkTests(unittest.TestCase):
    PARAMS = {
        "scope_refs": {"project:a"},
        "kind": None,
        "environment": None,
        "version": None,
        "current_dependencies": DEPENDENCIES,
    }

    def make_root(self, temp):
        root = Path(temp) / "knowledge"
        entry = make_entry("project:a", "a")
        created = knowledge.create_entry(
            root,
            entry,
            complete_root_snapshot=True,
            atomic_create_if_absent_available=True,
            current_dependencies=DEPENDENCIES,
        )
        self.assertEqual(created["status"], "created")
        return root, entry

    def link(self, link, target):
        try:
            os.symlink(target, link)
        except (OSError, NotImplementedError, AttributeError) as exc:
            self.skipTest(f"symlink is unavailable in this environment: {exc}")

    def test_regular_entries_are_a_complete_listing(self):
        with tempfile.TemporaryDirectory() as temp:
            root, entry = self.make_root(temp)
            scan = knowledge.scan_knowledge_root(root)
            self.assertTrue(scan["complete"])
            self.assertEqual(scan["unresolved"], [])
            self.assertEqual(len(scan["entry_paths"]), 1)
            self.assertTrue(knowledge.read_root_entries(root)["complete"])
            self.assertEqual(
                knowledge.lookup_root(root, **self.PARAMS)["status"], "complete"
            )

    def test_a_symlinked_entry_candidate_is_an_incomplete_listing(self):
        with tempfile.TemporaryDirectory() as temp:
            root, entry = self.make_root(temp)
            outside = Path(temp) / "outside.md"
            outside.write_text("# outside", encoding="utf-8")
            other = make_entry("project:b", "b")
            name = f"{other['entry_ref']}.md"
            self.link(root / name, outside)
            scan = knowledge.scan_knowledge_root(root)
            self.assertFalse(scan["complete"])
            self.assertEqual(scan["unresolved"], [f"{name}:entry_is_symlink"])
            # the link is never followed: it is not listed as an entry path
            self.assertNotIn(name, [Path(p).name for p in scan["entry_paths"]])
            self.assertEqual(outside.read_text(encoding="utf-8"), "# outside")

    def test_dangling_symlink_and_in_root_target_are_both_incomplete(self):
        with tempfile.TemporaryDirectory() as temp:
            root, entry = self.make_root(temp)
            dangling = f"{make_entry('project:b', 'b')['entry_ref']}.md"
            self.link(root / dangling, Path(temp) / "missing-target.md")
            scan = knowledge.scan_knowledge_root(root)
            self.assertFalse(scan["complete"])
            self.assertEqual(scan["unresolved"], [f"{dangling}:entry_is_symlink"])
            (root / dangling).unlink()
            alias = f"{make_entry('project:c', 'c')['entry_ref']}.md"
            self.link(root / alias, root / f"{entry['entry_ref']}.md")
            scan = knowledge.scan_knowledge_root(root)
            self.assertFalse(scan["complete"])
            self.assertEqual(scan["unresolved"], [f"{alias}:entry_is_symlink"])

    def test_mixed_regular_entry_and_symlink_makes_the_lookup_incomplete(self):
        with tempfile.TemporaryDirectory() as temp:
            root, entry = self.make_root(temp)
            outside = Path(temp) / "outside.md"
            outside.write_text("# outside", encoding="utf-8")
            name = f"{make_entry('project:b', 'b')['entry_ref']}.md"
            self.link(root / name, outside)
            snapshot = knowledge.read_root_entries(root)
            self.assertFalse(snapshot["complete"])
            self.assertEqual(snapshot["entries"], [])
            self.assertIn(f"{name}:entry_is_symlink", snapshot["unresolved"])
            found = knowledge.lookup_root(root, **self.PARAMS)
            self.assertEqual(found["status"], "incomplete")
            self.assertEqual(found["entries"], [])
            self.assertIn(f"{name}:entry_is_symlink", found["unresolved"])

    def test_non_entry_symlink_name_and_existing_negatives_are_unchanged(self):
        with tempfile.TemporaryDirectory() as temp:
            root, entry = self.make_root(temp)
            self.link(root / "latest", root / f"{entry['entry_ref']}.md")
            self.assertTrue(knowledge.scan_knowledge_root(root)["complete"])
            (root / "latest").unlink()
            (root / "notes.md").write_text("# stray", encoding="utf-8")
            self.assertEqual(
                knowledge.lookup_root(root, **self.PARAMS)["status"], "incomplete"
            )
            (root / "notes.md").unlink()
            self.assertTrue(knowledge.scan_knowledge_root(root)["complete"])
            self.assertFalse(
                knowledge.scan_knowledge_root(root, max_entries=0)["complete"]
            )

    def test_scan_does_not_write_through_or_outside_the_root(self):
        with tempfile.TemporaryDirectory() as temp:
            root, entry = self.make_root(temp)
            outside = Path(temp) / "outside.md"
            outside.write_text("# outside", encoding="utf-8")
            before = sorted(p.name for p in Path(temp).iterdir())
            name = f"{make_entry('project:b', 'b')['entry_ref']}.md"
            self.link(root / name, outside)
            knowledge.lookup_root(root, **self.PARAMS)
            self.assertEqual(outside.read_text(encoding="utf-8"), "# outside")
            self.assertEqual(sorted(p.name for p in Path(temp).iterdir()), before)


class KnowledgeCurrentDependencyRevisionTests(unittest.TestCase):
    STORED = [{"ref": "config:a", "revision": "r1"}]

    def test_only_a_valid_different_revision_is_stale(self):
        table = [
            ("r1", "current"),
            ("r2", "stale"),
            (None, "unresolved"),
            ("", "unresolved"),
            ([], "unresolved"),
            ({"revision": "r2"}, "unresolved"),
            (5, "unresolved"),
            (True, "unresolved"),
        ]
        for value, expected in table:
            with self.subTest(current=value):
                result = knowledge.compare_currentness(self.STORED, {"config:a": value})
                self.assertEqual(result["status"], expected)
                if expected == "unresolved":
                    self.assertEqual(result["changed_refs"], [])
                    self.assertEqual(result["unresolved"], ["config:a"])
                if expected == "stale":
                    self.assertEqual(result["changed_refs"], ["config:a"])
                    self.assertEqual(result["unresolved"], [])

    def test_a_ref_missing_from_the_snapshot_is_unresolved(self):
        result = knowledge.compare_currentness(self.STORED, {"config:other": "r1"})
        self.assertEqual(result["status"], "unresolved")
        self.assertEqual(result["unresolved"], ["config:a"])

    def test_one_unknown_dependency_keeps_the_unresolved_priority(self):
        stored = [
            {"ref": "config:a", "revision": "r1"},
            {"ref": "config:b", "revision": "r1"},
        ]
        for unknown in (None, "", [], {"revision": "r1"}):
            with self.subTest(unknown=unknown):
                result = knowledge.compare_currentness(
                    stored, {"config:a": "r2", "config:b": unknown}
                )
                self.assertEqual(result["status"], "unresolved")
                self.assertEqual(result["unresolved"], ["config:b"])
                self.assertEqual(result["changed_refs"], ["config:a"])

    def test_validate_entry_does_not_report_unknown_revision_as_stale(self):
        entry = with_revision(make_entry())
        for value in (None, "", [], {"revision": "r2"}):
            with self.subTest(current=value):
                currentness = knowledge.validate_entry(
                    entry,
                    current_dependencies={"config:a": value},
                    entry_revision="sha256:stored",
                )["currentness"]
                self.assertEqual(currentness["status"], "unresolved")
        stale = knowledge.validate_entry(
            entry,
            current_dependencies={"config:a": "r2"},
            entry_revision="sha256:stored",
        )["currentness"]
        self.assertEqual(stale["status"], "stale")

    def test_lookup_never_returns_an_entry_with_an_unknown_revision(self):
        entry = with_revision(make_entry())
        ok = search([entry])
        self.assertEqual(ok["status"], "complete")
        self.assertEqual(
            [item["entry_ref"] for item in ok["entries"]], [entry["entry_ref"]]
        )
        for value in (None, "", [], {"revision": "r2"}, 5):
            with self.subTest(current=value):
                result = search([entry], dependencies={"config:a": value})
                self.assertEqual(result["status"], "incomplete")
                self.assertEqual(result["entries"], [])
                self.assertIn(
                    f"{entry['entry_ref']}:currentness_unresolved",
                    result["unresolved"],
                )
        changed = search([entry], dependencies={"config:a": "r2"})
        self.assertEqual(changed["status"], "complete")
        self.assertEqual(changed["entries"], [])
        self.assertEqual(changed["historical_excluded_refs"], [entry["entry_ref"]])

    def test_lookup_of_an_unrelated_entry_ignores_its_unknown_revision(self):
        other = with_revision(make_entry("project:b", "b", dependency="config:b"))
        result = search([other], dependencies={"config:b": None})
        self.assertEqual(result["status"], "complete")
        self.assertEqual(
            result["out_of_scope_diagnostics"],
            [f"{other['entry_ref']}:currentness_unresolved_not_applicable"],
        )

    def test_revalidation_separates_unknown_from_changed(self):
        changed = with_revision(make_entry("project:a", "c", dependency="config:a"))
        unknown = with_revision(make_entry("project:a", "u", dependency="config:b"))
        same = with_revision(make_entry("project:a", "s", dependency="config:c"))
        snapshot = {"config:a": "r2", "config:b": None, "config:c": "r1"}
        plan = knowledge.plan_revalidation(
            [changed, unknown, same], current_dependencies=snapshot
        )
        self.assertEqual(plan["status"], "complete")
        reasons = {t["entry_ref"]: t for t in plan["targets"]}
        self.assertEqual(reasons[changed["entry_ref"]]["reason"], "dependency_changed")
        self.assertEqual(reasons[changed["entry_ref"]]["unresolved"], [])
        self.assertEqual(
            reasons[unknown["entry_ref"]]["reason"], "dependency_unresolved"
        )
        self.assertEqual(reasons[unknown["entry_ref"]]["changed_refs"], [])
        self.assertEqual(reasons[unknown["entry_ref"]]["unresolved"], ["config:b"])
        self.assertEqual(plan["unaffected_refs"], [same["entry_ref"]])

    def test_lookup_and_revalidation_agree_on_a_partly_unknown_entry(self):
        identity = {
            "kind": "test_environment",
            "scope_refs": ["project:a"],
            "subject": "multi",
        }
        entry = with_revision(
            make_entry(
                "project:a",
                "multi",
                identity=identity,
                entry_ref=knowledge.canonical_entry_ref(identity),
                currentness_dependencies=[
                    {"ref": "config:a", "revision": "r1"},
                    {"ref": "config:b", "revision": "r1"},
                ],
            )
        )
        snapshot = {"config:a": "r2", "config:b": None}
        lookup = search([entry], dependencies=snapshot)
        self.assertEqual(lookup["status"], "incomplete")
        plan = knowledge.plan_revalidation([entry], current_dependencies=snapshot)
        (target,) = plan["targets"]
        self.assertEqual(target["reason"], "dependency_unresolved")
        self.assertEqual(target["unresolved"], ["config:b"])
        self.assertEqual(target["changed_refs"], ["config:a"])

    def test_hand_off_state_blocks_an_unknown_revision_instead_of_stale(self):
        entry = with_revision(make_entry())
        for value in (None, "", [], {"revision": "r2"}):
            with self.subTest(current=value):
                reference = knowledge.improvement_reference(
                    entry, current_dependencies={"config:a": value}
                )["reference"]
                self.assertEqual(reference["state"], "blocked")
                self.assertEqual(
                    reference["resume"]["action"], "obtain_dependency_revisions"
                )
                self.assertEqual(reference["unresolved"], ["config:a"])
        stale = knowledge.improvement_reference(
            entry, current_dependencies={"config:a": "r2"}
        )["reference"]
        self.assertEqual(stale["state"], "stale")


if __name__ == "__main__":
    unittest.main()
