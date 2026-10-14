from __future__ import annotations

import copy
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


def child_identity_unknown_request(root: Path, branch: str) -> dict:
    request = create_request(root)
    request["change_summary"] = f"Synthetic identity placement regression: {branch}"
    groups: dict[tuple[str, str], dict] = {}

    def add(file: str, section: str, draft_key: str, cells: dict) -> None:
        group = groups.setdefault(
            (file, section), {"file": file, "section": section, "rows": []}
        )
        group["rows"].append(
            {
                "draft_key": draft_key,
                "identity_action": "new",
                "reuse_id": None,
                "external_id": None,
                "cells": cells,
            }
        )

    unknown_ref = "@draft:identity-unknown"
    has_unknown = branch in {"uc", "behavior", "ac"}
    add(
        "00_scope_and_context.md",
        "分析対象機能scope一覧",
        "scope",
        {
            "対象機能 / 領域": "Synthetic sign-in",
            "UI操作判定": "あり",
            "関連UNKNOWN ID": [unknown_ref] if has_unknown else [],
            "関連仕様項目ID": ["@draft:spec"],
            "根拠 / 備考": "Synthetic identity placement input.",
        },
    )
    add(
        "01_ui_structure_and_navigation.md",
        "UI構造一覧",
        "page",
        {
            "種別": "PAGE",
            "名称": "Sign-in page",
            "状態軸": "",
            "Path / 識別子": "/sign-in",
            "親構造ID": [],
            "関連仕様項目ID": ["@draft:spec"],
            "関連構造ID": [],
            "備考": "Evaluation-only structure.",
        },
    )
    add(
        "02_behavior_and_business_rules.md",
        "UI操作一覧",
        "operation",
        {
            "Scope ID": ["@draft:scope"],
            "Actor / Role": "Member",
            "対象構造ID": ["@draft:page"],
            "操作": "Submit valid sign-in information.",
            "関連仕様項目ID": ["@draft:spec"],
            "対応UC ID": [] if branch == "uc" else ["@draft:use-case"],
            "関連UNKNOWN ID": [unknown_ref] if branch == "uc" else [],
        },
    )
    add(
        "02_behavior_and_business_rules.md",
        "User Story一覧",
        "story",
        {
            "Scope ID": ["@draft:scope"],
            "Actor / Role": "Member",
            "Goal": "Sign in to the account.",
            "関連仕様項目ID": ["@draft:spec"],
            "関連構造ID": ["@draft:page"],
            "関連UNKNOWN ID": [unknown_ref] if branch == "uc" else [],
        },
    )
    if branch != "uc":
        add(
            "02_behavior_and_business_rules.md",
            "Use Case一覧",
            "use-case",
            {
                "関連US ID": ["@draft:story"],
                "Use Case": "Member signs in.",
                "Trigger": "Member submits sign-in information.",
                "Preconditions": "Member account exists.",
                "Success Postcondition": "The account page is shown.",
                "関連仕様項目ID": ["@draft:spec"],
                "関連構造ID": ["@draft:page"],
                "関連UNKNOWN ID": [],
            },
        )
        add(
            "02_behavior_and_business_rules.md",
            "Behavior一覧",
            "success-behavior",
            {
                "UC ID": ["@draft:use-case"],
                "関連操作ID": ["@draft:operation"],
                "結果分類": "正常",
                "振る舞い": "Valid sign-in reaches the account page.",
                "Postcondition / Result": "The account page is shown.",
                "関連仕様項目ID": ["@draft:spec"],
                "関連構造ID": ["@draft:page"],
                "関連UNKNOWN ID": [unknown_ref] if branch == "ac" else [],
            },
        )
        if branch != "ac":
            add(
                "02_behavior_and_business_rules.md",
                "Acceptance Criteria一覧",
                "success-ac",
                {
                    "Behavior ID": ["@draft:success-behavior"],
                    "Acceptance Criteria": "After valid sign-in, the member reaches the account page.",
                    "関連仕様項目ID": ["@draft:spec"],
                    "関連構造ID": ["@draft:page"],
                    "関連UNKNOWN ID": [],
                },
            )

    source = {
        "情報源 / 正本一覧": "Synthetic approved sign-in requirement",
        "権威 / 優先順位": "承認済み正本",
        "鮮度 / バージョン": "test fixture",
        "対象範囲": "Synthetic sign-in",
        "参照 / 備考": "Evaluation-only input; not historical product data.",
    }
    add("09_authority_and_traceability.md", "情報源 / 正本参照一覧", "source", source)
    add(
        "09_authority_and_traceability.md",
        "分析項目",
        "spec",
        {
            "カテゴリ": "仕様",
            "内容": "Valid sign-in reaches the account page.",
            "分類": "SPEC",
            "情報源 / 正本参照": ["@draft:source"],
            "現在有効か": "Yes",
            "解消先ID": [],
            "補足 / 上書き / 置換関係": "",
            "備考": "Synthetic evaluation basis.",
        },
    )
    if has_unknown:
        add(
            "09_authority_and_traceability.md",
            "分析項目",
            "identity-unknown",
            {
                "カテゴリ": "仕様上の不明点",
                "内容": f"The {branch} child identity is unresolved.",
                "分類": "UNKNOWN",
                "情報源 / 正本参照": ["@draft:source"],
                "現在有効か": "Yes",
                "解消先ID": [],
                "補足 / 上書き / 置換関係": "",
                "備考": "No identity or product behavior is invented.",
            },
        )
    request["table_changes"] = list(groups.values())
    request["keyed_table_updates"] = [
        {
            "file": "00_scope_and_context.md",
            "section": "条件付き必須file applicability",
            "rows": [
                {
                    "ファイル": file,
                    "Scope ID": "@draft:scope",
                    "Trigger判定": "なし",
                    "関連仕様項目ID": ["@draft:spec"],
                    "根拠 / 備考": "Not part of this synthetic identity scenario.",
                    "関連UNKNOWN ID": [],
                }
                for file in (
                    "03_fields_and_validation.md",
                    "04_flows_and_data.md",
                    "05_notifications_and_external_interactions.md",
                    "08_repository_implementation_status.md",
                )
            ],
        },
        {
            "file": "07_current_unknowns.md",
            "section": "Current UNKNOWN一覧",
            "rows": (
                [
                    {
                        "UNKNOWN ID": unknown_ref,
                        "確認事項": f"What is the {branch} child identity?",
                        "根拠": "The synthetic source does not resolve the child identity.",
                        "影響範囲": "Only this child identity branch.",
                        "関連Scope ID": ["@draft:scope"],
                        "Blocking Scope ID": ["@draft:scope"],
                        "関連File": "02_behavior_and_business_rules.md",
                        "関連構造ID": ["@draft:page"],
                        "次の扱い": "Keep the affected scope blocked pending clarification.",
                    }
                ]
                if has_unknown
                else []
            ),
        },
        {
            "file": "02_behavior_and_business_rules.md",
            "section": "Use Case振る舞い完全性",
            "rows": (
                []
                if branch == "uc"
                else [
                    {
                        "UC ID": "@draft:use-case",
                        "結果分類": "正常",
                        "判定": "未定義" if branch == "ac" else "定義あり",
                        "関連Behavior ID": []
                        if branch == "ac"
                        else ["@draft:success-behavior"],
                        "関連仕様項目ID": ["@draft:spec"],
                        "関連UNKNOWN ID": [unknown_ref] if branch == "ac" else [],
                        "理由 / 根拠": "The Acceptance Criterion identity is unresolved."
                        if branch == "ac"
                        else "The synthetic source defines the successful sign-in result.",
                    },
                    {
                        "UC ID": "@draft:use-case",
                        "結果分類": "準正常",
                        "判定": "なし",
                        "関連Behavior ID": [],
                        "関連仕様項目ID": ["@draft:spec"],
                        "関連UNKNOWN ID": [],
                        "理由 / 根拠": "No abnormal path is in this synthetic input.",
                    },
                    {
                        "UC ID": "@draft:use-case",
                        "結果分類": "例外",
                        "判定": "未定義" if branch == "behavior" else "なし",
                        "関連Behavior ID": [],
                        "関連仕様項目ID": ["@draft:spec"],
                        "関連UNKNOWN ID": [unknown_ref] if branch == "behavior" else [],
                        "理由 / 根拠": "Exceptional Behavior identity is unresolved."
                        if branch == "behavior"
                        else "No exceptional path is in this synthetic input.",
                    },
                ]
            ),
        },
        {
            "file": "09_authority_and_traceability.md",
            "section": "現在有効な仕様根拠",
            "rows": [
                {
                    "仕様根拠ID": "@draft:spec",
                    "種別": "SPEC",
                    "現在有効な内容": "Valid sign-in reaches the account page.",
                    "適用範囲": "Synthetic sign-in",
                    "情報源 / 正本一覧": ["@draft:source"],
                    "関係": "独立",
                    "関連仕様根拠ID": [],
                }
            ],
        },
    ]
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

    def test_uncertain_file_trigger_accepts_same_request_unknown_draft(self) -> None:
        spec = package.TABLE_BY_KEY[
            ("00_scope_and_context.md", "条件付き必須file applicability")
        ]
        row = package._keyed_row_from_input(
            spec,
            {
                "ファイル": "03_fields_and_validation.md",
                "Scope ID": "@draft:scope-partial",
                "Trigger判定": "未確定",
                "関連仕様項目ID": ["@draft:spec-partial"],
                "根拠 / 備考": "Input-field applicability is unresolved.",
                "関連UNKNOWN ID": ["@draft:unk-partial"],
            },
        )

        self.assertEqual(row["状態"], "blocked")
        self.assertEqual(row["関連UNKNOWN ID"], "@draft:unk-partial")

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

    def test_post_commit_process_exit_replays_update_ids_extensions_and_retirements(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory(prefix="qa-pr16-update-replay-") as temporary:
            root = Path(temporary) / "package"
            initial = authority_scope_request(root)
            initial["extension_file_updates"] = [
                {
                    "draft_key": "retained-extension",
                    "identity_action": "new",
                    "path": None,
                    "slug": "retained",
                    "responsibility": "Record independent scope evidence.",
                    "split_reason": "Keep this case-specific note outside standard tables.",
                    "scope_refs": ["@draft:scope-a"],
                    "authority_refs": ["@draft:spec-a"],
                    "structure_refs": [],
                    "unknown_refs": [],
                    "body_markdown": "# Retained evidence\n\nEvidence for scope A.\n",
                }
            ]
            created = package._execute_operation(initial)
            self.assertTrue(created["valid"], created["issues"])
            snapshot = package._execute_operation(
                {"operation": "inspect", "package_root": str(root)}
            )["payload"]["update_snapshot"]

            request = create_request(root)
            request["artifact_mode"] = "update"
            request["previous_snapshot"] = snapshot
            request["keyed_table_updates"] = [
                {
                    "file": "09_authority_and_traceability.md",
                    "section": "現在有効な仕様根拠",
                    "rows": [
                        {
                            "仕様根拠ID": "SPEC-001",
                            "種別": "SPEC",
                            "現在有効な内容": "Aは独立している",
                            "適用範囲": "A機能",
                            "情報源 / 正本一覧": ["SRC-001"],
                            "関係": "独立",
                            "関連仕様根拠ID": [],
                        },
                        {
                            "仕様根拠ID": "SPEC-002",
                            "種別": "SPEC",
                            "現在有効な内容": "Bは独立している",
                            "適用範囲": "B機能",
                            "情報源 / 正本一覧": ["SRC-001"],
                            "関係": "独立",
                            "関連仕様根拠ID": [],
                        },
                        {
                            "仕様根拠ID": "@draft:spec-new",
                            "種別": "SPEC",
                            "現在有効な内容": "独立scope workflowの追加検証要件",
                            "適用範囲": "追加検証",
                            "情報源 / 正本一覧": ["SRC-001"],
                            "関係": "独立",
                            "関連仕様根拠ID": [],
                        },
                    ],
                }
            ]
            request["table_changes"] = [
                {
                    "file": "09_authority_and_traceability.md",
                    "section": "分析項目",
                    "rows": [
                        {
                            "draft_key": "spec-new",
                            "identity_action": "new",
                            "reuse_id": None,
                            "external_id": None,
                            "cells": {
                                "カテゴリ": "仕様",
                                "内容": "独立scope workflowの追加検証要件",
                                "分類": "SPEC",
                                "情報源 / 正本参照": ["SRC-001"],
                                "現在有効か": "Yes",
                                "解消先ID": [],
                                "補足 / 上書き / 置換関係": "",
                                "備考": "",
                            },
                        }
                    ],
                }
            ]
            request["change_summary"] = "extensionと仕様根拠を更新"
            request["extension_file_updates"] = [
                {
                    "draft_key": "replacement-extension",
                    "identity_action": "new",
                    "path": None,
                    "slug": "replacement",
                    "responsibility": "Record updated scope evidence.",
                    "split_reason": "Keep this case-specific note outside standard tables.",
                    "scope_refs": ["SCOPE-001"],
                    "authority_refs": ["SPEC-001"],
                    "structure_refs": [],
                    "unknown_refs": [],
                    "body_markdown": "# Replacement evidence\n\nUpdated evidence for scope A.\n",
                }
            ]
            request["extension_file_retirements"] = ["10_retained.md"]

            code = textwrap.dedent(
                """
                import json
                import os
                import sys

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

            committed = package._execute_operation(
                {"operation": "inspect", "package_root": str(root)}
            )
            self.assertTrue(committed["valid"], committed["issues"])
            self.assertEqual(committed["payload"]["package_version"], "v01")
            self.assertFalse((root / "10_retained.md").exists())
            self.assertTrue((root / "11_replacement.md").is_file())
            manifest_after_commit = (root / "MANIFEST.md").read_bytes()

            replay = package._execute_operation(request)
            self.assertTrue(replay["valid"], replay["issues"])
            self.assertTrue(replay["payload"]["replayed"])
            self.assertEqual(
                replay["payload"]["allocated_ids"],
                [{"draft_key": "spec-new", "stable_id": "SPEC-003"}],
            )
            self.assertEqual(
                replay["payload"]["allocated_extension_files"],
                [{"draft_key": "replacement-extension", "path": "11_replacement.md"}],
            )
            self.assertEqual(
                replay["payload"]["retired_extension_files"], ["10_retained.md"]
            )
            self.assertEqual(replay["payload"]["package_version"], "v01")
            self.assertEqual((root / "MANIFEST.md").read_bytes(), manifest_after_commit)
            self.assertTrue((root / "11_replacement.md").is_file())
            self.assertFalse((root / "10_retained.md").exists())

            changed_request = json.loads(json.dumps(request))
            changed_request["change_summary"] = "同じsnapshotからの別request"
            with self.assertRaises(package.PackageError) as caught:
                package._execute_operation(changed_request)
            self.assertEqual(caught.exception.issue_type, "stale_snapshot")

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

    def test_preflight_removes_orphan_staging_for_each_reader(self) -> None:
        for operation in ("inspect", "validate", "build-machine-evidence"):
            with self.subTest(operation=operation):
                with tempfile.TemporaryDirectory(
                    prefix=f"qa-pr16-orphan-staging-{operation}-"
                ) as temporary:
                    root = Path(temporary) / "package"
                    created = package._execute_operation(authority_scope_request(root))
                    self.assertTrue(created["valid"], created["issues"])
                    snapshot = package._execute_operation(
                        {"operation": "inspect", "package_root": str(root)}
                    )["payload"]["update_snapshot"]
                    manifest_before = (root / "MANIFEST.md").read_bytes()
                    staging = root.with_name(f".{root.name}.ui-target-staging")
                    staging.mkdir()
                    (staging / "partial.md").write_text("partial", encoding="utf-8")

                    request = {"operation": operation, "package_root": str(root)}
                    if operation == "validate":
                        request["previous_snapshot"] = snapshot
                    elif operation == "build-machine-evidence":
                        request["scope_ids"] = ["SCOPE-001", "SCOPE-002"]
                    result = package._execute_operation(request)

                    self.assertTrue(result["valid"], result["issues"])
                    self.assertFalse(staging.exists())
                    self.assertTrue(root.is_dir())
                    self.assertEqual(
                        (root / "MANIFEST.md").read_bytes(), manifest_before
                    )
                    if operation == "inspect":
                        self.assertEqual(result["payload"]["package_version"], "v00")
                    elif operation == "build-machine-evidence":
                        self.assertEqual(
                            [
                                entity["entity_ref"]
                                for entity in result["payload"]["batch_handoff"][
                                    "machine_entities"
                                ]
                            ],
                            ["SPEC-001", "SPEC-002"],
                        )

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

    def test_not_applicable_scope_rejects_lingering_domain_rows_across_sections(
        self,
    ) -> None:
        rows_by_route = {
            "optional-domain-files": [
                (
                    "04_flows_and_data.md",
                    "処理フロー一覧",
                    "flow-b",
                    {
                        "関連Scope ID": ["@draft:scope-b"],
                        "処理名": "Flow for not-applicable scope",
                        "トリガー / 操作": "Start flow",
                        "手順 / 状態遷移": "Step",
                        "結果": "Result",
                        "関連仕様項目ID": ["@draft:spec-b"],
                        "関連構造ID": [],
                        "関連UNKNOWN ID": [],
                        "備考": "",
                    },
                ),
                (
                    "05_notifications_and_external_interactions.md",
                    "通知・外部連携一覧",
                    "interaction-b",
                    {
                        "関連Scope ID": ["@draft:scope-b"],
                        "種別": "外部連携",
                        "名称": "Outbound request",
                        "発火条件": "Action",
                        "宛先 / 遷移先": "Service",
                        "内容 / 挙動": "Request",
                        "関連仕様項目ID": ["@draft:spec-b"],
                        "関連構造ID": [],
                        "関連UNKNOWN ID": [],
                        "備考": "",
                    },
                ),
                (
                    "08_repository_implementation_status.md",
                    "Repository実装状況",
                    "implementation-b",
                    {
                        "Repository": "frontend",
                        "関連Scope ID": ["@draft:scope-b"],
                        "対象": "Page",
                        "観測事実": "Observation",
                        "関連仕様項目ID": ["@draft:spec-b"],
                        "判定": "一致",
                        "証拠 / 参照": "case evidence",
                        "備考": "",
                    },
                ),
            ],
            "behavior-decomposition": [
                (
                    "02_behavior_and_business_rules.md",
                    "UI操作一覧",
                    "operation-b",
                    {
                        "Scope ID": ["@draft:scope-b"],
                        "Actor / Role": "User",
                        "対象構造ID": [],
                        "操作": "Complete a UI action.",
                        "関連仕様項目ID": ["@draft:spec-b"],
                        "対応UC ID": ["@draft:use-case-b"],
                        "関連UNKNOWN ID": [],
                    },
                ),
                (
                    "02_behavior_and_business_rules.md",
                    "User Story一覧",
                    "story-b",
                    {
                        "Scope ID": ["@draft:scope-b"],
                        "Actor / Role": "User",
                        "Goal": "Complete the represented workflow.",
                        "関連仕様項目ID": ["@draft:spec-b"],
                        "関連構造ID": [],
                        "関連UNKNOWN ID": [],
                    },
                ),
                (
                    "02_behavior_and_business_rules.md",
                    "Use Case一覧",
                    "use-case-b",
                    {
                        "関連US ID": ["@draft:story-b"],
                        "Use Case": "Complete workflow.",
                        "Trigger": "User begins workflow.",
                        "Preconditions": "Scope is available.",
                        "Success Postcondition": "Workflow completes.",
                        "関連仕様項目ID": ["@draft:spec-b"],
                        "関連構造ID": [],
                        "関連UNKNOWN ID": [],
                    },
                ),
                (
                    "02_behavior_and_business_rules.md",
                    "Behavior一覧",
                    "behavior-b",
                    {
                        "UC ID": ["@draft:use-case-b"],
                        "関連操作ID": ["@draft:operation-b"],
                        "結果分類": "正常",
                        "振る舞い": "Complete the workflow.",
                        "Postcondition / Result": "The workflow completes.",
                        "関連仕様項目ID": ["@draft:spec-b"],
                        "関連構造ID": [],
                        "関連UNKNOWN ID": [],
                    },
                ),
                (
                    "02_behavior_and_business_rules.md",
                    "Acceptance Criteria一覧",
                    "acceptance-b",
                    {
                        "Behavior ID": ["@draft:behavior-b"],
                        "Acceptance Criteria": "The workflow completes.",
                        "関連仕様項目ID": ["@draft:spec-b"],
                        "関連構造ID": [],
                        "関連UNKNOWN ID": [],
                    },
                ),
            ],
        }
        for route, rows in rows_by_route.items():
            with self.subTest(route=route):
                with tempfile.TemporaryDirectory(
                    prefix=f"qa-pr16-not-applicable-{route}-"
                ) as temporary:
                    root = Path(temporary) / "package"
                    request = authority_scope_request(root)
                    request["table_changes"].extend(
                        {
                            "file": file,
                            "section": section,
                            "rows": [
                                {
                                    "draft_key": draft_key,
                                    "identity_action": "new",
                                    "reuse_id": None,
                                    "external_id": None,
                                    "cells": cells,
                                }
                            ],
                        }
                        for file, section, draft_key, cells in rows
                    )

                    with self.assertRaises(package.PackageError) as caught:
                        package._execute_operation(request)
                    self.assertEqual(
                        caught.exception.issue_type, "state_transition_required"
                    )
                    self.assertFalse(root.exists())

    def test_reader_during_materialize_commit_fails_closed_then_reads_complete_version(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory(prefix="qa-pr16-reader-race-") as temporary:
            root = Path(temporary) / "package"
            first = package._execute_operation(authority_scope_request(root))
            self.assertTrue(first["valid"], first["issues"])
            snapshot = package._execute_operation(
                {"operation": "inspect", "package_root": str(root)}
            )["payload"]["update_snapshot"]
            update = create_request(root)
            update["artifact_mode"] = "update"
            update["previous_snapshot"] = snapshot
            update["change_summary"] = "atomic reader race"
            update["keyed_table_updates"] = []

            before = package._execute_operation(
                {"operation": "inspect", "package_root": str(root)}
            )
            self.assertTrue(before["valid"], before["issues"])
            self.assertEqual(before["payload"]["package_version"], "v00")
            before_evidence = package._execute_operation(
                {
                    "operation": "build-machine-evidence",
                    "package_root": str(root),
                    "scope_ids": ["SCOPE-001", "SCOPE-002"],
                }
            )
            self.assertTrue(before_evidence["valid"], before_evidence["issues"])
            self.assertEqual(
                [
                    entity["entity_ref"]
                    for entity in before_evidence["payload"]["batch_handoff"][
                        "machine_entities"
                    ]
                ],
                ["SPEC-001", "SPEC-002"],
            )

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
                writer.stdin = None
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

                for reader_request in (
                    {"operation": "inspect", "package_root": str(root)},
                    {
                        "operation": "build-machine-evidence",
                        "package_root": str(root),
                        "scope_ids": ["SCOPE-001", "SCOPE-002"],
                    },
                ):
                    read = subprocess.run(
                        [sys.executable, str(SCRIPT_DIR / "ui_target_package.py")],
                        input=json.dumps(reader_request),
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
                    self.assertEqual(
                        response["issues"][0]["issue_type"], "write_locked"
                    )
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
            after_evidence = package._execute_operation(
                {
                    "operation": "build-machine-evidence",
                    "package_root": str(root),
                    "scope_ids": ["SCOPE-001", "SCOPE-002"],
                }
            )
            self.assertTrue(after_evidence["valid"], after_evidence["issues"])
            self.assertEqual(
                [
                    entity["entity_ref"]
                    for entity in after_evidence["payload"]["batch_handoff"][
                        "machine_entities"
                    ]
                ],
                ["SPEC-001", "SPEC-002"],
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

    def test_unknown_child_identity_is_kept_at_the_blocking_parent(self) -> None:
        def rows_for(markdown: str, section: str) -> list[list[str]]:
            section_text = markdown.split(f"## {section}\n", 1)[1].split("\n## ", 1)[0]
            rows = []
            for line in section_text.splitlines():
                if not line.startswith("| ") or line.startswith("| ---"):
                    continue
                rows.append([cell.strip() for cell in line[1:-1].split("|")])
            return rows

        expected = {
            "uc": "User Story一覧",
            "behavior": "Use Case振る舞い完全性",
            "ac": "Behavior一覧",
        }
        for branch, _ in expected.items():
            with (
                self.subTest(branch=branch),
                tempfile.TemporaryDirectory(
                    prefix=f"qa-pr16-unknown-{branch}-"
                ) as temporary,
            ):
                root = Path(temporary) / "package"
                result = package._execute_operation(
                    child_identity_unknown_request(root, branch)
                )
                self.assertTrue(result["valid"], result["issues"])
                self.assertEqual(result["payload"]["blocked_scope_ids"], ["SCOPE-001"])
                self.assertEqual(
                    result["payload"]["scope_readiness"][0]["blocking_unknown_ids"],
                    ["UNK-001"],
                )
                markdown = (root / "02_behavior_and_business_rules.md").read_text(
                    encoding="utf-8"
                )

                if branch == "uc":
                    story_rows = rows_for(markdown, expected[branch])
                    self.assertEqual(len(story_rows), 2)
                    self.assertEqual(story_rows[1][0], "US-001")
                    self.assertEqual(story_rows[1][-2:], ["blocked", "UNK-001"])
                    self.assertEqual(rows_for(markdown, "Use Case一覧")[1:], [])
                elif branch == "behavior":
                    completeness = rows_for(markdown, expected[branch])
                    exceptional = next(
                        row for row in completeness[1:] if row[1] == "例外"
                    )
                    self.assertEqual(exceptional[2], "未定義")
                    self.assertEqual(exceptional[3], "")
                    self.assertEqual(exceptional[5], "UNK-001")
                    behavior_rows = rows_for(markdown, "Behavior一覧")
                    self.assertEqual(len(behavior_rows), 2)
                    self.assertEqual(behavior_rows[1][0], "BH-001")
                else:
                    behavior_rows = rows_for(markdown, expected[branch])
                    self.assertEqual(behavior_rows[1][0], "BH-001")
                    self.assertEqual(behavior_rows[1][-2:], ["blocked", "UNK-001"])
                    completeness = rows_for(markdown, "Use Case振る舞い完全性")
                    normal = next(row for row in completeness[1:] if row[1] == "正常")
                    self.assertEqual(normal[2], "未定義")
                    self.assertEqual(normal[3], "")
                    self.assertEqual(normal[5], "UNK-001")
                    self.assertEqual(
                        rows_for(markdown, "Acceptance Criteria一覧")[1:], []
                    )

    def test_blocked_known_uc_skips_behavior_completeness_closure(self) -> None:
        with tempfile.TemporaryDirectory(
            prefix="qa-pr16-blocked-known-uc-"
        ) as temporary:
            root = Path(temporary) / "package"
            created = package._execute_operation(
                child_identity_unknown_request(root, "ready")
            )
            self.assertTrue(created["valid"], created["issues"])
            model = package._read_package(root)

            for section, id_column, stable_id in (
                ("UI操作一覧", "操作ID", "UIOP-001"),
                ("Use Case一覧", "UC ID", "UC-001"),
                ("Behavior一覧", "Behavior ID", "BH-001"),
                ("Acceptance Criteria一覧", "AC ID", "AC-001"),
            ):
                row = next(
                    item
                    for item in model.tables[
                        ("02_behavior_and_business_rules.md", section)
                    ]
                    if item[id_column] == stable_id
                )
                row["状態"] = "blocked"
            model.tables[
                ("02_behavior_and_business_rules.md", "Use Case振る舞い完全性")
            ] = []

            package._validate_hierarchies(model)

    def test_ui_unknown_can_resolve_and_reopen_with_the_same_id(self) -> None:
        def group(request: dict, file: str, section: str) -> dict:
            return next(
                item
                for item in request["table_changes"]
                if item["file"] == file and item["section"] == section
            )

        def keyed_group(request: dict, file: str, section: str) -> dict:
            return next(
                item
                for item in request["keyed_table_updates"]
                if item["file"] == file and item["section"] == section
            )

        def replace_draft_refs(value: object, ids: dict[str, str]) -> object:
            if isinstance(value, str) and value.startswith("@draft:"):
                return ids[value.removeprefix("@draft:")]
            if isinstance(value, list):
                return [replace_draft_refs(item, ids) for item in value]
            if isinstance(value, dict):
                return {
                    key: replace_draft_refs(item, ids) for key, item in value.items()
                }
            return value

        with tempfile.TemporaryDirectory(
            prefix="qa-pr16-ui-unknown-life-"
        ) as temporary:
            root = Path(temporary) / "package"
            initial = child_identity_unknown_request(root, "ready")
            scope = group(initial, "00_scope_and_context.md", "分析対象機能scope一覧")[
                "rows"
            ][0]
            scope["cells"]["関連UNKNOWN ID"] = ["@draft:ui-type-unknown"]
            analysis = group(initial, "09_authority_and_traceability.md", "分析項目")
            analysis["rows"].append(
                {
                    "draft_key": "ui-type-unknown",
                    "identity_action": "new",
                    "reuse_id": None,
                    "external_id": None,
                    "cells": {
                        "カテゴリ": "仕様上の不明点",
                        "内容": "The saved-view ellipsis control type is unresolved.",
                        "分類": "UNKNOWN",
                        "情報源 / 正本参照": ["@draft:source"],
                        "現在有効か": "Yes",
                        "解消先ID": [],
                        "補足 / 上書き / 置換関係": "",
                        "備考": "Synthetic evaluation input.",
                    },
                }
            )
            keyed_group(initial, "07_current_unknowns.md", "Current UNKNOWN一覧")[
                "rows"
            ] = [
                {
                    "UNKNOWN ID": "@draft:ui-type-unknown",
                    "確認事項": "Is the saved-view ellipsis a popover?",
                    "根拠": "Synthetic owner evidence does not classify its UI type.",
                    "影響範囲": "Saved-view actions control only.",
                    "関連Scope ID": ["@draft:scope"],
                    "Blocking Scope ID": ["@draft:scope"],
                    "関連File": "01_ui_structure_and_navigation.md",
                    "関連構造ID": ["@draft:page"],
                    "次の扱い": "Keep scope blocked until clarified.",
                }
            ]

            created = package._execute_operation(initial)
            self.assertTrue(created["valid"], created["issues"])
            ids = {
                item["draft_key"]: item["stable_id"]
                for item in created["payload"]["allocated_ids"]
            }
            unknown_id = ids["ui-type-unknown"]
            self.assertEqual(created["payload"]["blocked_scope_ids"], [ids["scope"]])

            first_snapshot = package._execute_operation(
                {"operation": "inspect", "package_root": str(root)}
            )["payload"]["update_snapshot"]
            resolved = copy.deepcopy(initial)
            resolved["artifact_mode"] = "update"
            resolved["previous_snapshot"] = first_snapshot
            resolved["change_summary"] = "Synthetic evidence resolves the UI type."
            for table in resolved["table_changes"]:
                for row in table["rows"]:
                    draft_key = row.get("draft_key")
                    if row["identity_action"] == "new":
                        row["reuse_id"] = ids[draft_key]
                    row["identity_action"] = "reuse"
                    row["draft_key"] = None
                    row["cells"] = replace_draft_refs(row["cells"], ids)
            resolved["keyed_table_updates"] = replace_draft_refs(
                resolved["keyed_table_updates"], ids
            )
            group(resolved, "01_ui_structure_and_navigation.md", "UI構造一覧")[
                "rows"
            ].append(
                {
                    "draft_key": "resolved-popover",
                    "identity_action": "new",
                    "reuse_id": None,
                    "external_id": None,
                    "cells": {
                        "種別": "POPOVER",
                        "名称": "Saved-view actions",
                        "状態軸": "",
                        "Path / 識別子": "saved-view-actions",
                        "親構造ID": [ids["page"]],
                        "関連仕様項目ID": [ids["spec"]],
                        "関連構造ID": [],
                        "備考": "Synthetic owner clarification.",
                    },
                }
            )
            unknown_analysis = next(
                row
                for row in group(
                    resolved, "09_authority_and_traceability.md", "分析項目"
                )["rows"]
                if row["reuse_id"] == unknown_id
            )
            unknown_analysis["cells"]["現在有効か"] = "No"
            unknown_analysis["cells"]["解消先ID"] = [ids["spec"]]
            group(resolved, "00_scope_and_context.md", "分析対象機能scope一覧")["rows"][
                0
            ]["cells"]["関連UNKNOWN ID"] = []
            keyed_group(resolved, "07_current_unknowns.md", "Current UNKNOWN一覧")[
                "rows"
            ] = []

            resolved_result = package._execute_operation(resolved)
            self.assertTrue(resolved_result["valid"], resolved_result["issues"])
            self.assertEqual(resolved_result["payload"]["package_version"], "v01")
            self.assertEqual(
                resolved_result["payload"]["ready_scope_ids"], [ids["scope"]]
            )
            popover_id = next(
                item["stable_id"]
                for item in resolved_result["payload"]["allocated_ids"]
                if item["draft_key"] == "resolved-popover"
            )
            resolved_inspection = package._execute_operation(
                {"operation": "inspect", "package_root": str(root)}
            )
            self.assertTrue(resolved_inspection["valid"], resolved_inspection["issues"])
            self.assertEqual(resolved_inspection["payload"]["current_unknown_ids"], [])
            self.assertEqual(
                resolved_inspection["payload"]["resolved_unknown_ids"], [unknown_id]
            )
            self.assertIn(popover_id, resolved_inspection["payload"]["structural_ids"])

            reopened = copy.deepcopy(resolved)
            reopened["previous_snapshot"] = resolved_inspection["payload"][
                "update_snapshot"
            ]
            reopened["change_summary"] = (
                "Synthetic retraction reopens the same UNKNOWN."
            )
            ui_rows = group(
                reopened, "01_ui_structure_and_navigation.md", "UI構造一覧"
            )["rows"]
            ui_rows[:] = [row for row in ui_rows if row.get("reuse_id") != popover_id]
            reopened_unknown = next(
                row
                for row in group(
                    reopened, "09_authority_and_traceability.md", "分析項目"
                )["rows"]
                if row.get("reuse_id") == unknown_id
            )
            reopened_unknown["cells"]["現在有効か"] = "Yes"
            reopened_unknown["cells"]["解消先ID"] = []
            group(reopened, "00_scope_and_context.md", "分析対象機能scope一覧")["rows"][
                0
            ]["cells"]["関連UNKNOWN ID"] = [unknown_id]
            keyed_group(reopened, "07_current_unknowns.md", "Current UNKNOWN一覧")[
                "rows"
            ] = [
                {
                    "UNKNOWN ID": unknown_id,
                    "確認事項": "Is the saved-view ellipsis a popover?",
                    "根拠": "The owner withdrew the classification evidence.",
                    "影響範囲": "Saved-view actions control only.",
                    "関連Scope ID": [ids["scope"]],
                    "Blocking Scope ID": [ids["scope"]],
                    "関連File": "01_ui_structure_and_navigation.md",
                    "関連構造ID": [ids["page"]],
                    "次の扱い": "Keep scope blocked until new clarification.",
                }
            ]
            reopened["retire_ids"] = [popover_id]

            reopened_result = package._execute_operation(reopened)
            self.assertTrue(reopened_result["valid"], reopened_result["issues"])
            self.assertEqual(reopened_result["payload"]["package_version"], "v02")
            self.assertEqual(reopened_result["payload"]["retired_ids"], [popover_id])
            self.assertEqual(
                reopened_result["payload"]["blocked_scope_ids"], [ids["scope"]]
            )
            reopened_inspection = package._execute_operation(
                {"operation": "inspect", "package_root": str(root)}
            )
            self.assertTrue(reopened_inspection["valid"], reopened_inspection["issues"])
            self.assertEqual(
                reopened_inspection["payload"]["current_unknown_ids"], [unknown_id]
            )
            self.assertEqual(reopened_inspection["payload"]["resolved_unknown_ids"], [])
            self.assertNotIn(
                popover_id, reopened_inspection["payload"]["structural_ids"]
            )

    def test_large_ready_scope_batch_and_exact_io_size_boundary(self) -> None:
        with tempfile.TemporaryDirectory(prefix="qa-pr16-large-batch-") as temporary:
            root = Path(temporary) / "package"
            request = child_identity_unknown_request(root, "ready")
            acceptance_group = next(
                row_group
                for row_group in request["table_changes"]
                if row_group["section"] == "Acceptance Criteria一覧"
            )
            template = acceptance_group["rows"][0]
            acceptance_group["rows"] = []
            for index in range(40):
                row = copy.deepcopy(template)
                row["draft_key"] = f"large-ac-{index:02d}"
                row["cells"]["Acceptance Criteria"] = (
                    f"Synthetic criterion {index}: " + "x" * (60 * 1024)
                )
                acceptance_group["rows"].append(row)

            materialize_input = json.dumps(
                request, ensure_ascii=False, separators=(",", ":")
            ).encode("utf-8")
            self.assertGreater(len(materialize_input), 2 * 1024 * 1024)
            self.assertLess(len(materialize_input), 16 * 1024 * 1024)
            materialized = subprocess.run(
                [sys.executable, str(SCRIPT_DIR / "ui_target_package.py")],
                input=materialize_input,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=ROOT,
                check=False,
                timeout=60,
            )
            self.assertEqual(materialized.returncode, 0, materialized.stderr)
            materialize_result = json.loads(materialized.stdout)
            self.assertTrue(materialize_result["valid"], materialize_result["issues"])

            evidence_request = {
                "operation": "build-machine-evidence",
                "package_root": str(root),
                "scope_ids": ["SCOPE-001"],
            }
            evidence_input = json.dumps(
                evidence_request, ensure_ascii=False, separators=(",", ":")
            ).encode("utf-8")
            evidence_process = subprocess.run(
                [sys.executable, str(SCRIPT_DIR / "ui_target_package.py")],
                input=evidence_input,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=ROOT,
                check=False,
                timeout=60,
            )
            self.assertEqual(evidence_process.returncode, 0, evidence_process.stderr)
            evidence = json.loads(evidence_process.stdout)
            self.assertTrue(evidence["valid"], evidence["issues"])
            batch_bytes = len(
                package.canonical_json_bytes(evidence["payload"]["batch_handoff"])
            )
            self.assertGreater(batch_bytes, 2 * 1024 * 1024)
            self.assertLess(batch_bytes, 16 * 1024 * 1024)

            exact_limit_request = json.dumps(
                {"operation": "inspect", "package_root": str(root)},
                ensure_ascii=False,
                separators=(",", ":"),
            ).encode("utf-8")
            exact_limit_request += b" " * (16 * 1024 * 1024 - len(exact_limit_request))
            self.assertEqual(len(exact_limit_request), 16 * 1024 * 1024)
            exact_process = subprocess.run(
                [sys.executable, str(SCRIPT_DIR / "ui_target_package.py")],
                input=exact_limit_request,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=ROOT,
                check=False,
                timeout=60,
            )
            self.assertEqual(exact_process.returncode, 0, exact_process.stderr)
            self.assertTrue(json.loads(exact_process.stdout)["valid"])

            over_limit_process = subprocess.run(
                [sys.executable, str(SCRIPT_DIR / "ui_target_package.py")],
                input=exact_limit_request + b" ",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=ROOT,
                check=False,
                timeout=60,
            )
            self.assertEqual(
                over_limit_process.returncode, 0, over_limit_process.stderr
            )
            over_limit_result = json.loads(over_limit_process.stdout)
            self.assertFalse(over_limit_result["valid"])
            self.assertEqual(
                over_limit_result["issues"][0]["issue_type"], "limit_exceeded"
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
