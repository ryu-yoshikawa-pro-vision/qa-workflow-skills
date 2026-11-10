from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
WRITER_DIR = ROOT / "skills" / "spec-analysis" / "scripts"
WRITER_SCRIPT = WRITER_DIR / "ui_target_package.py"
HUMAN_EDIT_SCRIPT = (
    ROOT / "skills" / "ui-target-analysis" / "scripts" / "human_editing.py"
)
sys.path.insert(0, str(WRITER_DIR))
import ui_target_package as package  # noqa: E402

FIXTURE_TEST_PATH = ROOT / "tests" / "skills" / "runtime" / "test_ui_target_package.py"
FIXTURE_SPEC = importlib.util.spec_from_file_location(
    "ui_target_package_fixtures", FIXTURE_TEST_PATH
)
assert FIXTURE_SPEC is not None and FIXTURE_SPEC.loader is not None
fixture_module = importlib.util.module_from_spec(FIXTURE_SPEC)
FIXTURE_SPEC.loader.exec_module(fixture_module)


def cli(script: Path, request: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    result = subprocess.run(
        [sys.executable, str(script)],
        input=(json.dumps(request, ensure_ascii=False) + "\n").encode("utf-8"),
        capture_output=True,
        check=False,
        cwd=ROOT,
        timeout=30,
    )
    try:
        response = json.loads(result.stdout.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AssertionError(f"CLI returned invalid JSON: {result.stderr!r}") from exc
    return result.returncode, response


def raw_cli(script: Path, payload: str) -> tuple[int, dict[str, Any]]:
    result = subprocess.run(
        [sys.executable, str(script)],
        input=payload.encode("utf-8"),
        capture_output=True,
        check=False,
        cwd=ROOT,
        timeout=30,
    )
    return result.returncode, json.loads(result.stdout.decode("utf-8"))


def inspect(root: Path) -> dict[str, Any]:
    code, response = cli(
        WRITER_SCRIPT, {"operation": "inspect", "package_root": str(root)}
    )
    if code != 0 or response.get("valid") is not True:
        raise AssertionError(f"inspect failed: {response}")
    return response["payload"]


def create_workspace() -> tuple[
    tempfile.TemporaryDirectory[str], Path, Path, Path, dict[str, Any]
]:
    temp = tempfile.TemporaryDirectory()
    root = Path(temp.name)
    canonical = root / "canonical"
    canonical.mkdir()
    request = fixture_module.child_identity_unknown_request(canonical, "uc")
    structure_change = next(
        item
        for item in request["table_changes"]
        if item["file"] == "01_ui_structure_and_navigation.md"
        and item["section"] == "UI構造一覧"
    )
    structure_change["rows"].append(
        {
            "draft_key": "help-page",
            "identity_action": "new",
            "reuse_id": None,
            "external_id": None,
            "cells": {
                "種別": "PAGE",
                "名称": "Help page",
                "状態軸": "",
                "Path / 識別子": "/help",
                "親構造ID": [],
                "関連仕様項目ID": [],
                "関連構造ID": [],
                "備考": "Independent package fixture row.",
            },
        }
    )
    code, response = cli(WRITER_SCRIPT, request)
    if code != 0 or response.get("valid") is not True:
        temp.cleanup()
        raise AssertionError(f"fixture package materialize failed: {response}")
    base = root / "base"
    edit = root / "edit"
    shutil.copytree(canonical, base)
    shutil.copytree(canonical, edit)
    snapshot = inspect(base)["update_snapshot"]
    return temp, canonical, base, edit, snapshot


def edit_table(root: Path, file: str, section: str, update) -> None:
    path = root / file
    text = path.read_text(encoding="utf-8")
    rows = package.parse_table(
        text, section, package.TABLE_BY_KEY[(file, section)].headers
    )
    rows = update(rows)
    updated = package.replace_table(
        text, section, package.TABLE_BY_KEY[(file, section)].headers, rows
    )
    path.write_bytes(package.canonical_bytes(updated))


def review(
    change_keys: list[str],
    *,
    retirements: list[dict[str, str]] | None = None,
    current_snapshot: dict[str, Any] | None = None,
    decision: str = "approved",
    evidence_refs: dict[str, list[str]] | None = None,
) -> dict[str, Any]:
    retirement_rows = retirements or []
    result: dict[str, Any] = {
        "decision": decision,
        "review_ref": "fixture://review/001",
        "placement_agreement_ref": "fixture://project-context/q06/001",
        "change_summary": "UI owner reviewed human edit fixture",
        "approved_change_keys": change_keys,
        "evidence_refs": evidence_refs
        or {
            key: [f"fixture://source/{index}"]
            for index, key in enumerate(change_keys, 1)
        },
        "approved_retirements": retirement_rows,
        "retirement_evidence_refs": {
            row["id"]: [f"fixture://retirement/{row['id']}"] for row in retirement_rows
        },
    }
    if current_snapshot is not None:
        result["approved_current_snapshot"] = current_snapshot
    return result


def prepare(
    canonical: Path,
    base: Path,
    edit: Path,
    snapshot: dict[str, Any],
    decision: dict[str, Any],
):
    return cli(
        HUMAN_EDIT_SCRIPT,
        {
            "operation": "prepare",
            "package_root": str(canonical),
            "base_root": str(base),
            "edit_root": str(edit),
            "previous_snapshot": snapshot,
            "review": decision,
        },
    )


def apply(request: dict[str, Any]) -> dict[str, Any]:
    code, response = cli(WRITER_SCRIPT, request)
    if code != 0 or response.get("valid") is not True:
        raise AssertionError(f"materialize failed: {response}")
    return response["payload"]


def copy_page_row(row: dict[str, str], **changes: str) -> dict[str, str]:
    value = dict(row)
    value.update(changes)
    return value


def package_bytes(root: Path) -> dict[str, bytes]:
    return {path.name: path.read_bytes() for path in root.iterdir() if path.is_file()}


class UiHumanEditingAcceptanceTests(unittest.TestCase):
    def make_fixture(self):
        temp, canonical, base, edit, snapshot = create_workspace()
        self.addCleanup(temp.cleanup)
        return canonical, base, edit, snapshot

    def test_01_normal_edit_uses_writer_and_independent_readback(self) -> None:
        canonical, base, edit, snapshot = self.make_fixture()
        original = package._read_package(base)
        edit_table(
            edit,
            "01_ui_structure_and_navigation.md",
            "UI構造一覧",
            lambda rows: [
                copy_page_row(row, 名称="Updated sign-in page")
                if row["構造ID"] == "PAGE-001"
                else row
                for row in rows
            ],
        )
        nav = edit / "01_ui_structure_and_navigation.md"
        nav_text = nav.read_text(encoding="utf-8")
        nav.write_bytes(
            package.canonical_bytes(
                package._replace_user_prose_body(
                    nav_text, "Navigation / Entry / Exit", "Sign-in route is /sign-in."
                )
            )
        )
        keys = [
            "PAGE-001",
            "prose:01_ui_structure_and_navigation.md:Navigation / Entry / Exit",
        ]
        code, prepared = prepare(canonical, base, edit, snapshot, review(keys))
        self.assertEqual(code, 0, prepared)
        self.assertEqual(prepared["status"], "ready")
        applied = apply(prepared["materialize_request"])
        self.assertEqual(applied["previous_package_version"], "v00")
        self.assertEqual(applied["package_version"], "v01")
        readback = inspect(canonical)
        self.assertEqual(readback["package_schema_version"], "ui-target-v1")
        self.assertEqual(readback["package_version"], "v01")
        self.assertTrue(applied["changed"])
        final = package._read_package(canonical)
        before_ids = set(original.by_id)
        self.assertEqual(set(final.by_id), before_ids)
        self.assertEqual(final.by_id["PAGE-001"][1]["名称"], "Updated sign-in page")
        self.assertEqual(
            final.by_id["PAGE-002"][1]["名称"], original.by_id["PAGE-002"][1]["名称"]
        )
        self.assertIn(
            "Sign-in route is /sign-in.",
            final.files["01_ui_structure_and_navigation.md"],
        )
        valid_code, validated = cli(
            WRITER_SCRIPT,
            {
                "operation": "validate",
                "package_root": str(canonical),
                "previous_snapshot": readback["update_snapshot"],
            },
        )
        self.assertEqual(valid_code, 0, validated)
        self.assertTrue(validated["valid"])

    def test_02_new_row_and_explicit_retirement_preserve_identity_history(self) -> None:
        canonical, base, edit, snapshot = self.make_fixture()
        edit_table(
            edit,
            "01_ui_structure_and_navigation.md",
            "UI構造一覧",
            lambda rows: (
                [row for row in rows if row["構造ID"] != "PAGE-002"]
                + [
                    {
                        "構造ID": "@draft:settings-page",
                        "種別": "PAGE",
                        "名称": "Settings page",
                        "状態軸": "",
                        "Path / 識別子": "/settings",
                        "親構造ID": "",
                        "関連仕様項目ID": "",
                        "関連構造ID": "",
                        "備考": "New human-proposed UI structure.",
                    }
                ]
            ),
        )
        decisions = review(
            ["@draft:settings-page", "PAGE-002"],
            retirements=[
                {
                    "id": "PAGE-002",
                    "reason": "The UI page was formally removed.",
                    "approval_ref": "fixture://approval/retire-page-002",
                }
            ],
        )
        missing_retirement_approval = review(["@draft:settings-page", "PAGE-002"])
        canonical_before_block = package_bytes(canonical)
        blocked_code, blocked = prepare(
            canonical, base, edit, snapshot, missing_retirement_approval
        )
        self.assertNotEqual(blocked_code, 0)
        self.assertEqual(blocked["issues"][0]["code"], "retirement_review_required")
        self.assertEqual(package_bytes(canonical), canonical_before_block)
        code, prepared = prepare(canonical, base, edit, snapshot, decisions)
        self.assertEqual(code, 0, prepared)
        request = prepared["materialize_request"]
        self.assertEqual(request["retire_ids"], ["PAGE-002"])
        self.assertEqual(
            request["table_changes"][0]["rows"][0]["identity_action"], "new"
        )
        self.assertTrue(
            request["table_changes"][0]["rows"][0]["draft_key"] == "settings-page"
        )
        applied = apply(request)
        self.assertEqual(
            applied["allocated_ids"],
            [{"draft_key": "settings-page", "stable_id": "PAGE-003"}],
        )
        self.assertEqual(applied["retired_ids"], ["PAGE-002"])
        final = package._read_package(canonical)
        self.assertNotIn("PAGE-002", final.by_id)
        self.assertIn("PAGE-003", final.by_id)
        self.assertIn("| PAGE-002 | retired |", final.files["CHANGELOG.md"])

    def test_03_generated_and_control_file_edits_are_rejected_and_preserved(
        self,
    ) -> None:
        canonical, base, edit, snapshot = self.make_fixture()
        original_canonical = (canonical / "MANIFEST.md").read_bytes()
        manifest = edit / "MANIFEST.md"
        manifest.write_bytes(manifest.read_bytes() + b"\nHuman rewrite\n")
        code, response = prepare(canonical, base, edit, snapshot, review(["PAGE-001"]))
        self.assertNotEqual(code, 0)
        self.assertEqual(response["status"], "blocked")
        self.assertIn(
            response["issues"][0]["code"], {"owner_boundary", "noncanonical_text"}
        )
        self.assertEqual((canonical / "MANIFEST.md").read_bytes(), original_canonical)
        self.assertIn(b"Human rewrite", manifest.read_bytes())

    def test_04_authority_changes_and_missing_approval_or_evidence_are_blocked(
        self,
    ) -> None:
        canonical, base, edit, snapshot = self.make_fixture()
        canonical_before_block = package_bytes(canonical)
        authority = edit / "09_authority_and_traceability.md"
        authority.write_bytes(
            authority.read_bytes().replace(
                b"Valid sign-in reaches the account page.",
                b"Changed expected behavior.",
            )
        )
        code, response = prepare(canonical, base, edit, snapshot, review(["PAGE-001"]))
        self.assertNotEqual(code, 0)
        self.assertEqual(response["issues"][0]["code"], "owner_boundary")
        self.assertEqual(package_bytes(canonical), canonical_before_block)

        shutil.rmtree(edit)
        shutil.copytree(base, edit)
        edit_table(
            edit,
            "01_ui_structure_and_navigation.md",
            "UI構造一覧",
            lambda rows: [
                copy_page_row(row, 名称="Unapproved name")
                if row["構造ID"] == "PAGE-001"
                else row
                for row in rows
            ],
        )
        code, response = prepare(
            canonical, base, edit, snapshot, review(["PAGE-001"], decision="pending")
        )
        self.assertNotEqual(code, 0)
        self.assertEqual(response["issues"][0]["code"], "review_required")
        self.assertEqual(package_bytes(canonical), canonical_before_block)
        insufficient = review(["PAGE-001"], evidence_refs={"PAGE-001": []})
        code, response = prepare(canonical, base, edit, snapshot, insufficient)
        self.assertNotEqual(code, 0)
        self.assertEqual(response["issues"][0]["code"], "evidence_required")
        self.assertEqual(package_bytes(canonical), canonical_before_block)

    def test_05_same_id_conflict_blocks_and_independent_change_rebases_after_review(
        self,
    ) -> None:
        canonical, base, edit, snapshot = self.make_fixture()
        edit_table(
            edit,
            "01_ui_structure_and_navigation.md",
            "UI構造一覧",
            lambda rows: [
                copy_page_row(row, 名称="Human concurrent name")
                if row["構造ID"] == "PAGE-001"
                else row
                for row in rows
            ],
        )
        self._update_page(canonical, "PAGE-001", "Agent concurrent name")
        canonical_before_conflict = package_bytes(canonical)
        code, conflict = prepare(
            canonical,
            base,
            edit,
            snapshot,
            review(
                ["PAGE-001"], current_snapshot=inspect(canonical)["update_snapshot"]
            ),
        )
        self.assertNotEqual(code, 0)
        self.assertEqual(conflict["issues"][0]["code"], "concurrent_edit_blocked")
        self.assertEqual(package_bytes(canonical), canonical_before_conflict)

        canonical, base, edit, snapshot = self.make_fixture()
        edit_table(
            edit,
            "01_ui_structure_and_navigation.md",
            "UI構造一覧",
            lambda rows: (
                rows
                + [
                    {
                        "構造ID": "@draft:new-independent-page",
                        "種別": "PAGE",
                        "名称": "Independent page",
                        "状態軸": "",
                        "Path / 識別子": "/independent",
                        "親構造ID": "",
                        "関連仕様項目ID": "",
                        "関連構造ID": "",
                        "備考": "No shared structure or authority references.",
                    }
                ]
            ),
        )
        self._update_page(canonical, "PAGE-002", "Agent changed unrelated page")
        current_snapshot = inspect(canonical)["update_snapshot"]
        code, prepared = prepare(
            canonical,
            base,
            edit,
            snapshot,
            review(["@draft:new-independent-page"], current_snapshot=current_snapshot),
        )
        self.assertEqual(code, 0, prepared)
        self.assertTrue(prepared["rebased"])
        self.assertEqual(
            prepared["materialize_request"]["previous_snapshot"], current_snapshot
        )
        apply(prepared["materialize_request"])
        final = package._read_package(canonical)
        self.assertEqual(
            final.by_id["PAGE-002"][1]["名称"], "Agent changed unrelated page"
        )
        self.assertIn("PAGE-003", final.by_id)

        canonical, base, edit, snapshot = self.make_fixture()
        edit_table(
            edit,
            "01_ui_structure_and_navigation.md",
            "UI構造一覧",
            lambda rows: (
                rows
                + [
                    {
                        "構造ID": "@draft:cas-page",
                        "種別": "PAGE",
                        "名称": "CAS page",
                        "状態軸": "",
                        "Path / 識別子": "/cas",
                        "親構造ID": "",
                        "関連仕様項目ID": "",
                        "関連構造ID": "",
                        "備考": "The package changes after prepare.",
                    }
                ]
            ),
        )
        code, prepared = prepare(
            canonical, base, edit, snapshot, review(["@draft:cas-page"])
        )
        self.assertEqual(code, 0, prepared)
        self._update_page(canonical, "PAGE-002", "Changed after prepare")
        commit_code, commit = cli(WRITER_SCRIPT, prepared["materialize_request"])
        self.assertEqual(commit_code, 0, commit)
        self.assertFalse(commit["valid"])
        self.assertEqual(commit["status"], "blocked")
        self.assertEqual(commit["issues"][0]["issue_type"], "stale_snapshot")
        final = package._read_package(canonical)
        self.assertEqual(final.by_id["PAGE-002"][1]["名称"], "Changed after prepare")
        self.assertNotIn("PAGE-003", final.by_id)

    def test_06_direct_canonical_edit_blocks_then_validated_baseline_allows_safe_resume(
        self,
    ) -> None:
        canonical, base, edit, snapshot = self.make_fixture()
        edit_table(
            edit,
            "01_ui_structure_and_navigation.md",
            "UI構造一覧",
            lambda rows: [
                copy_page_row(row, 名称="Preserved human edit")
                if row["構造ID"] == "PAGE-001"
                else row
                for row in rows
            ],
        )
        current_file = canonical / "01_ui_structure_and_navigation.md"
        current_file.write_bytes(
            current_file.read_bytes().replace(
                b"Sign-in page", b"Direct canonical mutation"
            )
        )
        direct_bytes = current_file.read_bytes()
        code, blocked = prepare(canonical, base, edit, snapshot, review(["PAGE-001"]))
        self.assertNotEqual(code, 0)
        self.assertEqual(blocked["issues"][0]["code"], "package_not_current")
        self.assertEqual(current_file.read_bytes(), direct_bytes)
        self.assertIn(
            b"Preserved human edit",
            (edit / "01_ui_structure_and_navigation.md").read_bytes(),
        )

        shutil.rmtree(canonical)
        shutil.copytree(base, canonical)
        code, prepared = prepare(canonical, base, edit, snapshot, review(["PAGE-001"]))
        self.assertEqual(code, 0, prepared)
        apply(prepared["materialize_request"])
        self.assertEqual(
            package._read_package(canonical).by_id["PAGE-001"][1]["名称"],
            "Preserved human edit",
        )

    def test_07_lost_commit_response_replays_same_request_without_duplicate_ids(
        self,
    ) -> None:
        canonical, base, edit, snapshot = self.make_fixture()
        edit_table(
            edit,
            "01_ui_structure_and_navigation.md",
            "UI構造一覧",
            lambda rows: (
                rows
                + [
                    {
                        "構造ID": "@draft:response-loss-page",
                        "種別": "PAGE",
                        "名称": "Response loss page",
                        "状態軸": "",
                        "Path / 識別子": "/response-loss",
                        "親構造ID": "",
                        "関連仕様項目ID": "",
                        "関連構造ID": "",
                        "備考": "Retry uses the same writer request.",
                    }
                ]
            ),
        )
        code, prepared = prepare(
            canonical, base, edit, snapshot, review(["@draft:response-loss-page"])
        )
        self.assertEqual(code, 0, prepared)
        request = prepared["materialize_request"]
        first = apply(request)  # Treat this committed response as lost.
        replay = apply(request)
        self.assertFalse(first["replayed"])
        self.assertTrue(replay["replayed"])
        self.assertEqual(first["package_version"], replay["package_version"])
        self.assertEqual(first["allocated_ids"], replay["allocated_ids"])
        retry_code, retry = prepare(
            canonical,
            base,
            edit,
            snapshot,
            review(["@draft:response-loss-page"]),
        )
        self.assertEqual(retry_code, 0, retry)
        self.assertEqual(retry["status"], "unchanged")
        final = package._read_package(canonical)
        self.assertEqual(
            sum(1 for stable_id in final.by_id if stable_id == "PAGE-003"), 1
        )
        self.assertEqual(
            inspect(canonical)["package_version"], replay["package_version"]
        )

    def test_08_feature_index_reaches_current_ui_file_line_and_stable_id(self) -> None:
        canonical, _base, _edit, _snapshot = self.make_fixture()
        self._update_page(canonical, "PAGE-001", "Changed for feature index")
        code, response = cli(
            HUMAN_EDIT_SCRIPT,
            {
                "operation": "feature-index",
                "package_root": str(canonical),
                "feature_artifact_ref": "fixture://feature-analysis/features-v1",
                "feature_artifact_revision": "fixture-revision-01",
                "feature_scope_refs": [
                    {"feature_id": "FEATURE-001", "scope_id": "SCOPE-001"}
                ],
                "changed_ids": ["PAGE-001"],
            },
        )
        self.assertEqual(code, 0, response)
        entry = response["feature_scope_index"][0]
        self.assertEqual(entry["feature_id"], "FEATURE-001")
        self.assertEqual(entry["package_version"], "v01")
        by_id = {row["id"]: row for row in entry["ui_rows"]}
        self.assertIn("PAGE-001", by_id)
        self.assertIn("UIOP-001", by_id)
        self.assertIn("SCOPE-001", by_id)
        self.assertIn("PAGE-001", {row["id"] for row in entry["changed_ui_rows"]})
        self.assertEqual(
            package._read_package(canonical).by_id["PAGE-001"][1]["名称"],
            "Changed for feature index",
        )
        for location in entry["ui_rows"]:
            line = (
                (canonical / location["file"])
                .read_text(encoding="utf-8")
                .splitlines()[location["line"] - 1]
            )
            self.assertIn(location["id"], line)
        missing_code, missing = cli(
            HUMAN_EDIT_SCRIPT,
            {
                "operation": "feature-index",
                "package_root": str(canonical),
                "feature_artifact_ref": "",
                "feature_artifact_revision": "",
                "feature_scope_refs": [],
            },
        )
        self.assertNotEqual(missing_code, 0)
        self.assertEqual(missing["issues"][0]["code"], "source_ref_required")
        invalid_code, invalid = cli(
            HUMAN_EDIT_SCRIPT,
            {
                "operation": "feature-index",
                "package_root": str(canonical),
                "feature_artifact_ref": "fixture://feature-analysis/features-v1",
                "feature_artifact_revision": "fixture-revision-01",
                "feature_scope_refs": [{"feature_id": "FEATURE-001", "scope_id": []}],
            },
        )
        self.assertNotEqual(invalid_code, 0)
        self.assertEqual(invalid["issues"][0]["code"], "reference_not_found")

    def test_09_isolated_skill_copy_blocks_missing_shared_writer(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            isolated_root = Path(temp_dir) / "skills" / "ui-target-analysis"
            shutil.copytree(ROOT / "skills" / "ui-target-analysis", isolated_root)
            code, response = cli(
                isolated_root / "scripts" / "human_editing.py",
                {
                    "operation": "feature-index",
                    "package_root": str(Path(temp_dir) / "package"),
                    "feature_artifact_ref": "fixture://feature/001",
                    "feature_artifact_revision": "r1",
                    "feature_scope_refs": [],
                },
            )
            self.assertNotEqual(code, 0)
            self.assertEqual(response["status"], "blocked")
            self.assertEqual(response["issues"][0]["code"], "writer_unavailable")
            self.assertFalse(
                (Path(temp_dir) / "skills" / "spec-analysis" / "scripts").exists()
            )

    def test_10_symlink_root_and_duplicate_json_keys_are_rejected(self) -> None:
        duplicate_code, duplicate = raw_cli(
            HUMAN_EDIT_SCRIPT,
            '{"operation":"feature-index","operation":"prepare"}',
        )
        self.assertNotEqual(duplicate_code, 0)
        self.assertEqual(duplicate["issues"][0]["code"], "invalid_input")

        canonical, base, edit, snapshot = self.make_fixture()
        with tempfile.TemporaryDirectory() as temp_dir:
            base_link = Path(temp_dir) / "base-link"
            try:
                base_link.symlink_to(base, target_is_directory=True)
            except (OSError, NotImplementedError) as exc:
                self.skipTest(f"directory symlink is unavailable: {exc}")
            request = {
                "operation": "prepare",
                "package_root": str(canonical),
                "base_root": str(base_link),
                "edit_root": str(edit),
                "previous_snapshot": snapshot,
                "review": review(["PAGE-001"]),
            }
            code, response = cli(HUMAN_EDIT_SCRIPT, request)
            self.assertNotEqual(code, 0)
            self.assertEqual(response["issues"][0]["code"], "symlink_not_allowed")

    def _update_page(self, canonical: Path, stable_id: str, name: str) -> None:
        model = package._read_package(canonical)
        snapshot = package._read_update_snapshot(model)
        row = model.by_id[stable_id][1]
        spec = model.by_id[stable_id][0]
        derived = {spec.id_column, spec.status_column}
        cells = {
            field: package._split_refs(row[field]) if field in spec.refs else row[field]
            for field in spec.headers
            if field not in derived
        }
        cells["名称"] = name
        request = {
            "operation": "materialize",
            "package_root": str(canonical),
            "artifact_mode": "update",
            "previous_snapshot": snapshot,
            "change_mode": "normal",
            "legacy_source_version": None,
            "migration_retained_ids": [],
            "legacy_lifecycle_events": [],
            "change_summary": "Independent agent fixture update",
            "retire_ids": [],
            "table_changes": [
                {
                    "file": spec.file,
                    "section": spec.section,
                    "rows": [
                        {
                            "draft_key": None,
                            "identity_action": "reuse",
                            "reuse_id": stable_id,
                            "external_id": None,
                            "cells": cells,
                        }
                    ],
                }
            ],
            "keyed_table_updates": [],
            "prose_updates": [],
            "extension_file_updates": [],
            "extension_file_retirements": [],
        }
        apply(request)


if __name__ == "__main__":
    unittest.main()
