from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPT_DIR = ROOT / "skills" / "spec-analysis" / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))
import ui_target_package as package  # noqa: E402


def create_request(root: Path) -> dict:
    return {
        "operation": "materialize",
        "package_root": str(root),
        "artifact_mode": "create",
        "previous_snapshot": None,
        "change_mode": "normal",
        "legacy_source_version": None,
        "migration_retained_ids": [],
        "legacy_lifecycle_events": [],
        "change_summary": "初回作成",
        "retire_ids": [],
        "table_changes": [],
        "keyed_table_updates": [
            {
                "file": "00_scope_and_context.md",
                "section": "条件付き必須file applicability",
                "rows": [],
            },
            {
                "file": "07_current_unknowns.md",
                "section": "Current UNKNOWN一覧",
                "rows": [],
            },
        ],
        "prose_updates": [],
        "extension_file_updates": [],
        "extension_file_retirements": [],
    }


def authority_scope_request(root: Path) -> dict:
    request = create_request(root)
    request["change_summary"] = "独立scopeのAuthority projection"
    request["table_changes"] = [
        {
            "file": "00_scope_and_context.md",
            "section": "分析対象機能scope一覧",
            "rows": [
                {
                    "draft_key": "scope-a",
                    "identity_action": "new",
                    "reuse_id": None,
                    "external_id": None,
                    "cells": {
                        "対象機能 / 領域": "A機能",
                        "UI操作判定": "なし",
                        "関連UNKNOWN ID": [],
                        "関連仕様項目ID": ["@draft:spec-a"],
                        "根拠 / 備考": "Aのscope根拠",
                    },
                },
                {
                    "draft_key": "scope-b",
                    "identity_action": "new",
                    "reuse_id": None,
                    "external_id": None,
                    "cells": {
                        "対象機能 / 領域": "B機能",
                        "UI操作判定": "なし",
                        "関連UNKNOWN ID": [],
                        "関連仕様項目ID": ["@draft:spec-b"],
                        "根拠 / 備考": "Bのscope根拠",
                    },
                },
            ],
        },
        {
            "file": "09_authority_and_traceability.md",
            "section": "情報源 / 正本参照一覧",
            "rows": [
                {
                    "draft_key": "source-main",
                    "identity_action": "new",
                    "reuse_id": None,
                    "external_id": None,
                    "cells": {
                        "情報源 / 正本一覧": "Product specification",
                        "権威 / 優先順位": "一次資料",
                        "鮮度 / バージョン": "v1",
                        "対象範囲": "A機能とB機能",
                        "参照 / 備考": "fixture",
                    },
                }
            ],
        },
        {
            "file": "09_authority_and_traceability.md",
            "section": "分析項目",
            "rows": [
                {
                    "draft_key": "spec-a",
                    "identity_action": "new",
                    "reuse_id": None,
                    "external_id": None,
                    "cells": {
                        "カテゴリ": "仕様",
                        "内容": "Aは独立している",
                        "分類": "SPEC",
                        "情報源 / 正本参照": ["@draft:source-main"],
                        "現在有効か": "Yes",
                        "解消先ID": [],
                        "補足 / 上書き / 置換関係": "",
                        "備考": "",
                    },
                },
                {
                    "draft_key": "spec-b",
                    "identity_action": "new",
                    "reuse_id": None,
                    "external_id": None,
                    "cells": {
                        "カテゴリ": "仕様",
                        "内容": "Bは独立している",
                        "分類": "SPEC",
                        "情報源 / 正本参照": ["@draft:source-main"],
                        "現在有効か": "Yes",
                        "解消先ID": [],
                        "補足 / 上書き / 置換関係": "",
                        "備考": "",
                    },
                },
            ],
        },
    ]
    applicability = []
    for scope_key in ("scope-a", "scope-b"):
        for file in package.CONDITIONAL_FILES:
            applicability.append(
                {
                    "ファイル": file,
                    "Scope ID": f"@draft:{scope_key}",
                    "Trigger判定": "なし",
                    "関連仕様項目ID": [],
                    "根拠 / 備考": "対象外",
                    "関連UNKNOWN ID": [],
                }
            )
    request["keyed_table_updates"] = []
    request["keyed_table_updates"].extend(
        [
            {
                "file": "00_scope_and_context.md",
                "section": "条件付き必須file applicability",
                "rows": applicability,
            },
            {
                "file": "07_current_unknowns.md",
                "section": "Current UNKNOWN一覧",
                "rows": [],
            },
            {
                "file": "09_authority_and_traceability.md",
                "section": "現在有効な仕様根拠",
                "rows": [
                    {
                        "仕様根拠ID": "@draft:spec-a",
                        "種別": "SPEC",
                        "現在有効な内容": "Aは独立している",
                        "適用範囲": "A機能",
                        "情報源 / 正本一覧": ["@draft:source-main"],
                        "関係": "独立",
                        "関連仕様根拠ID": [],
                    },
                    {
                        "仕様根拠ID": "@draft:spec-b",
                        "種別": "SPEC",
                        "現在有効な内容": "Bは独立している",
                        "適用範囲": "B機能",
                        "情報源 / 正本一覧": ["@draft:source-main"],
                        "関係": "独立",
                        "関連仕様根拠ID": [],
                    },
                ],
            },
        ]
    )
    return request


class UiTargetPackageTests(unittest.TestCase):
    def test_assets_are_canonical_and_have_no_example_ids(self) -> None:
        asset_root = (
            ROOT / "skills" / "spec-analysis" / "assets" / "ui-test-target-analysis"
        )
        assets = sorted(asset_root.glob("*.md"))
        self.assertEqual(
            {path.name for path in assets},
            set(package.CORE_FILES)
            | set(package.CONDITIONAL_FILES)
            | {"CHANGELOG.md", "MANIFEST.md"},
        )
        for path in assets:
            raw = path.read_bytes()
            self.assertFalse(raw.startswith(b"\xef\xbb\xbf"), path.name)
            self.assertNotIn(b"\r", raw, path.name)
            self.assertTrue(raw.endswith(b"\n"), path.name)
            self.assertFalse(raw.endswith(b"\n\n"), path.name)
            if path.name not in {"README.md", "CHANGELOG.md", "MANIFEST.md"}:
                self.assertIsNone(
                    re.search(
                        rb"\b(?:SCOPE|PAGE|STATE|VIEW|STEP|MODAL|BDLG|PANEL|EXT|SHARED|FIELD|RULE|FLOW|NOTIFY|INTERACT|ISSUE|IMPL|UIOP|US|UC|BH|AC|SRC|SPEC|INF|UNK)-[0-9]{3,}\b",
                        raw,
                    ),
                    path.name,
                )

    def test_package_creation_inspection_and_receipt_replay(self) -> None:
        with tempfile.TemporaryDirectory(prefix="qa-pr16-package-") as temporary:
            root = Path(temporary) / "package"
            request = create_request(root)
            created = package._execute_operation(request)
            self.assertTrue(created["valid"], created["issues"])
            self.assertEqual(created["payload"]["package_version"], "v00")
            self.assertEqual(created["payload"]["completion_status"], "complete")
            self.assertEqual(created["payload"]["changed_files"][-1], "MANIFEST.md")

            inspected = package._execute_operation(
                {"operation": "inspect", "package_root": str(root)}
            )
            self.assertTrue(inspected["valid"], inspected["issues"])
            snapshot = inspected["payload"]["update_snapshot"]
            self.assertEqual(
                set(snapshot),
                {"package_version", "payload_file_sha256", "manifest_sha256"},
            )
            self.assertTrue(
                package._execute_operation(
                    {
                        "operation": "validate",
                        "package_root": str(root),
                        "previous_snapshot": snapshot,
                    }
                )["valid"]
            )

            replay = package._execute_operation(request)
            self.assertTrue(replay["valid"], replay["issues"])
            self.assertTrue(replay["payload"]["replayed"])
            self.assertEqual(
                replay["payload"]["request_fingerprint"],
                created["payload"]["request_fingerprint"],
            )

    def test_post_commit_process_exit_replays_create_receipt(self) -> None:
        with tempfile.TemporaryDirectory(prefix="qa-pr16-crash-replay-") as temporary:
            root = Path(temporary) / "package"
            request = authority_scope_request(root)
            code = textwrap.dedent(
                """
                import json
                import os
                import sys
                from pathlib import Path

                sys.path.insert(0, sys.argv[1])
                import ui_target_package as package

                original = package._commit_package

                def commit_then_exit(*args, **kwargs):
                    original(*args, **kwargs)
                    os._exit(73)

                package._commit_package = commit_then_exit
                package._execute_operation(json.load(sys.stdin))
                """
            )
            crashed = subprocess.run(
                [sys.executable, "-c", code, str(SCRIPT_DIR)],
                input=json.dumps(request, ensure_ascii=True),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                cwd=ROOT,
                check=False,
                timeout=15,
            )
            self.assertEqual(crashed.returncode, 73, crashed.stderr)

            before = package._execute_operation(
                {"operation": "inspect", "package_root": str(root)}
            )
            self.assertTrue(before["valid"], before["issues"])
            manifest_before = (root / "MANIFEST.md").read_bytes()

            replay = package._execute_operation(request)
            self.assertTrue(replay["valid"], replay["issues"])
            self.assertTrue(replay["payload"]["replayed"])
            self.assertEqual(replay["payload"]["package_version"], "v00")
            self.assertEqual((root / "MANIFEST.md").read_bytes(), manifest_before)

    def test_package_lock_is_exclusive_across_processes_and_released_after_kill(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory(prefix="qa-pr16-process-lock-") as temporary:
            root = Path(temporary) / "package"
            created = package._execute_operation(create_request(root))
            self.assertTrue(created["valid"], created["issues"])
            marker = Path(temporary) / "lock-held"
            code = textwrap.dedent(
                """
                import sys
                import time
                from pathlib import Path

                sys.path.insert(0, sys.argv[1])
                import ui_target_package as package

                with package._package_lock(Path(sys.argv[2])):
                    Path(sys.argv[3]).write_text("held", encoding="utf-8")
                    time.sleep(30)
                """
            )
            holder = subprocess.Popen(
                [sys.executable, "-c", code, str(SCRIPT_DIR), str(root), str(marker)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                cwd=ROOT,
            )
            try:
                deadline = time.monotonic() + 10
                while not marker.exists():
                    if holder.poll() is not None:
                        stdout, stderr = holder.communicate(timeout=1)
                        self.fail(f"lock holder exited early: {stdout} {stderr}")
                    if time.monotonic() >= deadline:
                        self.fail("lock holder did not acquire the package lock")
                    time.sleep(0.01)

                with self.assertRaises(package.PackageError) as caught:
                    package._execute_operation(
                        {"operation": "inspect", "package_root": str(root)}
                    )
                self.assertEqual(caught.exception.issue_type, "write_locked")
            finally:
                if holder.poll() is None:
                    holder.terminate()
                holder.communicate(timeout=5)

            inspected = package._execute_operation(
                {"operation": "inspect", "package_root": str(root)}
            )
            self.assertTrue(inspected["valid"], inspected["issues"])

    def test_preflight_recovers_backup_for_each_reader_and_fails_closed_when_ambiguous(
        self,
    ) -> None:
        for operation in ("inspect", "validate", "build-machine-evidence"):
            with self.subTest(operation=operation):
                with tempfile.TemporaryDirectory(
                    prefix=f"qa-pr16-backup-{operation}-"
                ) as temporary:
                    root = Path(temporary) / "package"
                    created = package._execute_operation(authority_scope_request(root))
                    self.assertTrue(created["valid"], created["issues"])
                    snapshot = package._execute_operation(
                        {"operation": "inspect", "package_root": str(root)}
                    )["payload"]["update_snapshot"]
                    backup = root.with_name(f".{root.name}.ui-target-backup")
                    staging = root.with_name(f".{root.name}.ui-target-staging")
                    root.rename(backup)
                    staging.mkdir()
                    (staging / "partial.md").write_text("partial", encoding="utf-8")

                    request = {"operation": operation, "package_root": str(root)}
                    if operation == "validate":
                        request["previous_snapshot"] = snapshot
                    elif operation == "build-machine-evidence":
                        request["scope_ids"] = ["SCOPE-001", "SCOPE-002"]
                    result = package._execute_operation(request)

                    self.assertTrue(result["valid"], result["issues"])
                    self.assertTrue(root.is_dir())
                    self.assertFalse(backup.exists())
                    self.assertFalse(staging.exists())
                    if operation == "build-machine-evidence":
                        self.assertEqual(
                            [
                                row["entity_ref"]
                                for row in result["payload"]["batch_handoff"][
                                    "machine_entities"
                                ]
                            ],
                            ["SPEC-001", "SPEC-002"],
                        )

        with tempfile.TemporaryDirectory(
            prefix="qa-pr16-ambiguous-recovery-"
        ) as temporary:
            root = Path(temporary) / "package"
            backup = root.with_name(f".{root.name}.ui-target-backup")
            staging = root.with_name(f".{root.name}.ui-target-staging")
            backup.mkdir()
            (backup / "invalid.md").write_text("invalid", encoding="utf-8")
            staging.mkdir()
            with self.assertRaises(package.PackageError) as caught:
                package._execute_operation(
                    {"operation": "inspect", "package_root": str(root)}
                )
            self.assertEqual(caught.exception.issue_type, "write_recovery_failed")

    def test_not_applicable_scope_rejects_lingering_domain_row(self) -> None:
        with tempfile.TemporaryDirectory(prefix="qa-pr16-not-applicable-") as temporary:
            root = Path(temporary) / "package"
            request = authority_scope_request(root)
            request["table_changes"].append(
                {
                    "file": "03_fields_and_validation.md",
                    "section": "項目・バリデーション一覧",
                    "rows": [
                        {
                            "draft_key": "field-in-na-scope",
                            "identity_action": "new",
                            "reuse_id": None,
                            "external_id": None,
                            "cells": {
                                "関連Scope ID": ["@draft:scope-b"],
                                "対象構造ID": [],
                                "ラベル / 名称": "email",
                                "要素タイプ": "text",
                                "入力 / 表示仕様": "email input",
                                "制約 / バリデーション": "valid email",
                                "関連仕様項目ID": ["@draft:spec-b"],
                                "関連UNKNOWN ID": [],
                                "備考": "",
                            },
                        }
                    ],
                }
            )
            with self.assertRaises(package.PackageError) as caught:
                package._execute_operation(request)
            self.assertEqual(caught.exception.issue_type, "state_transition_required")
            self.assertFalse(root.exists())

    def test_reader_during_materialize_commit_fails_closed_then_reads_complete_version(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory(prefix="qa-pr16-reader-race-") as temporary:
            root = Path(temporary) / "package"
            first = package._execute_operation(create_request(root))
            self.assertTrue(first["valid"], first["issues"])
            snapshot = package._execute_operation(
                {"operation": "inspect", "package_root": str(root)}
            )["payload"]["update_snapshot"]
            update = create_request(root)
            update["artifact_mode"] = "update"
            update["previous_snapshot"] = snapshot
            update["change_summary"] = "atomic reader race"

            marker = Path(temporary) / "old-root-moved"
            release = Path(temporary) / "release-commit"
            code = textwrap.dedent(
                """
                import json
                import sys
                import time
                from pathlib import Path

                sys.path.insert(0, sys.argv[1])
                import ui_target_package as package

                marker = Path(sys.argv[3])
                release = Path(sys.argv[4])

                def paused_commit(root, staging, backup, *, had_root):
                    if not had_root:
                        raise AssertionError("expected an update commit")
                    root.rename(backup)
                    marker.write_text("committing", encoding="utf-8")
                    deadline = time.monotonic() + 10
                    while not release.exists():
                        if time.monotonic() >= deadline:
                            raise TimeoutError("test did not release commit")
                        time.sleep(0.01)
                    staging.rename(root)
                    package._remove_owned(backup)

                package._commit_package = paused_commit
                response = package._execute_operation(json.load(sys.stdin))
                print(json.dumps(response, ensure_ascii=True))
                """
            )
            writer = subprocess.Popen(
                [
                    sys.executable,
                    "-c",
                    code,
                    str(SCRIPT_DIR),
                    str(root),
                    str(marker),
                    str(release),
                ],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                cwd=ROOT,
            )
            try:
                assert writer.stdin is not None
                writer.stdin.write(json.dumps(update, ensure_ascii=True))
                writer.stdin.close()
                deadline = time.monotonic() + 10
                while not marker.exists():
                    if writer.poll() is not None:
                        stdout, stderr = writer.communicate(timeout=1)
                        self.fail(
                            f"writer exited before commit pause: {stdout} {stderr}"
                        )
                    if time.monotonic() >= deadline:
                        self.fail(
                            "writer did not reach the root-to-backup commit point"
                        )
                    time.sleep(0.01)

                read = subprocess.run(
                    [sys.executable, str(SCRIPT_DIR / "ui_target_package.py")],
                    input=json.dumps(
                        {"operation": "inspect", "package_root": str(root)}
                    ),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    cwd=ROOT,
                    check=False,
                    timeout=10,
                )
                self.assertEqual(read.returncode, 0, read.stderr)
                response = json.loads(read.stdout)
                self.assertFalse(response["valid"])
                self.assertEqual(response["issues"][0]["issue_type"], "write_locked")
                self.assertFalse(root.exists())

                release.write_text("continue", encoding="utf-8")
                stdout, stderr = writer.communicate(timeout=10)
                self.assertEqual(writer.returncode, 0, stderr)
                write_response = json.loads(stdout)
                self.assertTrue(write_response["valid"], write_response["issues"])
            finally:
                if writer.poll() is None:
                    release.write_text("continue", encoding="utf-8")
                    writer.communicate(timeout=10)

            completed = package._execute_operation(
                {"operation": "inspect", "package_root": str(root)}
            )
            self.assertTrue(completed["valid"], completed["issues"])
            self.assertEqual(completed["payload"]["package_version"], "v01")

    def test_canonical_table_cell_round_trip_and_traversal_rejection(self) -> None:
        value = "first|second\\path\nthird"
        self.assertEqual(package._decode_cell(package._encode_cell(value)), value)
        with self.assertRaises(package.PackageError):
            package._encode_cell("literal <br> is ambiguous")
        with self.assertRaises(package.PackageError) as caught:
            package.canonical_path(Path("C:/package"), "../outside.md")
        self.assertEqual(caught.exception.issue_type, "path_outside_package")

    def test_ready_scope_batch_projects_authorities_from_each_scope(self) -> None:
        with tempfile.TemporaryDirectory(prefix="qa-pr16-scope-batch-") as temporary:
            root = Path(temporary) / "package"
            created = package._execute_operation(authority_scope_request(root))
            self.assertTrue(created["valid"], created["issues"])
            self.assertEqual(
                created["payload"]["ready_scope_ids"], ["SCOPE-001", "SCOPE-002"]
            )

            result = package._execute_operation(
                {
                    "operation": "build-machine-evidence",
                    "package_root": str(root),
                    "scope_ids": ["SCOPE-001", "SCOPE-002"],
                }
            )
            self.assertTrue(result["valid"], result["issues"])
            batch = result["payload"]["batch_handoff"]
            self.assertEqual(
                [
                    row["authority_id"]
                    for row in batch["normalized_skill_input"]["authorities"]
                ],
                ["SPEC-001", "SPEC-002"],
            )
            self.assertEqual(
                [row["entity_ref"] for row in batch["machine_entities"]],
                ["SPEC-001", "SPEC-002"],
            )

    def test_cli_emits_one_structured_json_line_for_invalid_input(self) -> None:
        result = subprocess.run(
            [sys.executable, str(SCRIPT_DIR / "ui_target_package.py")],
            input=b'{"operation":"unknown"}',
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=ROOT,
            check=False,
        )
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stderr, b"")
        self.assertEqual(result.stdout.count(b"\n"), 1)
        response = json.loads(result.stdout)
        self.assertFalse(response["valid"])
        self.assertEqual(response["operation"], "unknown")
        self.assertEqual(response["issues"][0]["issue_type"], "invalid_input")


if __name__ == "__main__":
    unittest.main()
