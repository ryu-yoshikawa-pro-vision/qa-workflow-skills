from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
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
