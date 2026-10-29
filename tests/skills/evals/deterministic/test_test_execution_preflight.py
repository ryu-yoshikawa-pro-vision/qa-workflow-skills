from __future__ import annotations

import unittest
from pathlib import Path

from scripts.skills.evals.deterministic.loader import load_validators

VALIDATORS = load_validators()


def blocked_report(*, count: int = 2) -> str:
    refs = [f"input-{index:03d}" for index in range(1, count + 1)]
    mappings = "\n".join(
        f"| {ref} | なし | {index} | なし |"
        for index, ref in enumerate(refs, 1)
    )
    conditions = "\n".join(
        f"| {ref} | 未提供 | 未提供 | 未提供 | 未提供 | 未提供 | 未提供 | 開始不可 |"
        for ref in refs
    )
    preconditions = "\n".join(
        f"| {ref} | 未提供 | なし | 必要なTC入力が不足 |" for ref in refs
    )
    results = "\n".join(
        f"| {ref} | 未開始 | 未実行 |  |  |  |  |" for ref in refs
    )
    unexecuted = "\n".join(
        f"| {ref} | 未実行 | TC本文が未提供 | 元TC本文と対象環境 | 必須入力を確認後 |"
        for ref in refs
    )
    post = "\n".join(f"| {ref} | なし | 未実施 | なし | TC未開始 |" for ref in refs)
    return f"""# テスト実行結果

## 実行情報
| 項目 | 値 | 確認元 |
| --- | --- | --- |
| 対象 | 未提供 | input.md |
| テストケース入力元 / 成果物参照 | 入力依頼 | input.md |
| TC revision / content identity | なし | input.md |
| snapshot固定方法 | 未生成（TC本文が入力にない） | input.md |
| 今回の実行対象 test_case_ref 集合 | {', '.join(refs)}（依頼slot。TC snapshot未生成） | input.md |
| 前回実行成果物参照 | なし | input.md |
| 実行日時 | 2026-10-29 | execution environment |
| 使用した実行手段 | 未実行 | execution preflight |
| テスト対象資料参照 | 未提供 | input.md |

## run固定条件
| 条件 | 値 | 確認元 |
| --- | --- | --- |
| 対象環境 | 未指定 | input.md |
| 許可origin | 未指定 | input.md |
| version / build | 未指定 | input.md |

## TC参照対応
| TC参照 | 元TC ID (source_test_case_id) | 入力順 | 前回TC参照 |
| --- | --- | ---: | --- |
{mappings}

## TC実行条件
| TC参照 | role / アカウント | viewport | locale | feature flag | テストデータ | 開始状態 | 確認結果 |
| --- | --- | --- | --- | --- | --- | --- | --- |
{conditions}

## Given / When / Then構造の実行前YAML

TC本文が入力にないためsnapshotとYAMLを生成していません。対象TCを推測せず未実行とします。

## 実行前条件
| TC参照 | 副作用scope | TC事後状態 / 後処理 | 確認結果 |
| --- | --- | --- | --- |
{preconditions}

## 副作用上限・実行時cleanup
| 副作用scope | 1回の定義 | 最大回数 | 準備回数 | TC操作回数 | TC事後処理回数 | 実行時cleanup回数 | 累計実施回数 | 実行時cleanup対象 / 方法 | cleanup結果 | 残存状態 | 残数 / 状態 | 根拠 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | --- | --- | --- |

## 手順・観測結果
| TC参照 | 手順 / 観測点 (step_ref) | 操作 | 観測方法 | 期待結果 | 実測結果 | 状態 / 備考 |
| --- | --- | --- | --- | --- | --- | --- |

## 視覚確認
| TC参照 | 手順 / 観測点 | 確認観点 | 画像で観測した事実 | 画像参照 | 判定への利用 |
| --- | --- | --- | --- | --- | --- |

## TC実行結果
| TC参照 | 実行開始 | 状態 | 期待結果 | 実測結果 | 判定根拠 | 証跡参照 |
| --- | --- | --- | --- | --- | --- | --- |
{results}

## 未実行・判定不能
| TC参照 | 状態 | 理由 | 必要な情報 / 対応 | 再開条件 |
| --- | --- | --- | --- | --- |
{unexecuted}

## TC事後状態・後処理
| TC参照 | 事後状態 / 後処理 | 実施結果 | 残存状態 | 根拠 |
| --- | --- | --- | --- | --- |
{post}

## 実行時cleanup・残存状態
| 対象 | 状態 | 内容 | 根拠 |
| --- | --- | --- | --- |

## 集計
| 状態 | 件数 |
| --- | ---: |
| PASS | 0 |
| FAIL | 0 |
| 未実行 | {count} |
| 判定不能 | 0 |

## 実行結果報告

必要なTC本文と対象情報が入力にないため、{count}件は未実行です。
"""


class TestExecutionPreflightTests(unittest.TestCase):
    def test_template_makes_yaml_example_conditional_on_restored_snapshot(self) -> None:
        template = (
            Path(__file__).resolve().parents[4]
            / "skills/test-execution/assets/output-template.md"
        ).read_text(encoding="utf-8")
        self.assertIn("snapshotを復元できる場合は", template)
        self.assertIn("YAMLブロックはsnapshotを復元できる場合の形の例", template)
        self.assertIn("このYAML例や空のYAML blockを出力しません", template)
        self.assertNotIn("このMarkdown内のYAMLを省略しません", template)

    def test_missing_tc_source_can_close_as_unexecuted_without_fake_yaml(self) -> None:
        result = VALIDATORS["test-execution"](
            blocked_report(),
            {
                "source_identity_present": False,
                "expected_snapshot_method": "未生成（TC本文が入力にない）",
                "expected_refs": ["input-001", "input-002"],
                "require_preflight_block": True,
                "expected_unexecuted_count": 2,
                "required_preflight_tokens": ["TC本文", "未実行"],
            },
            "TEX-PREFLIGHT",
        ).to_dict()
        self.assertEqual(result["status"], "pass", result)

    def test_preflight_block_rejects_empty_executable_yaml(self) -> None:
        text = blocked_report().replace(
            "TC本文が入力にないためsnapshotとYAMLを生成していません。対象TCを推測せず未実行とします。",
            """TC本文が入力にないためsnapshotとYAMLを生成していません。対象TCを推測せず未実行とします。

```yaml
test_case_ref: input-001
source_test_case_id: null
title: 未提供
scenario:
  given: []
  when: []
  then: []
unresolved: [TC本文未提供]
cleanup: []
```""",
        )
        result = VALIDATORS["test-execution"](
            text,
            {
                "source_identity_present": False,
                "expected_snapshot_method": "未生成（TC本文が入力にない）",
                "expected_refs": ["input-001", "input-002"],
                "require_preflight_block": True,
                "expected_unexecuted_count": 2,
                "required_preflight_tokens": ["TC本文", "未実行"],
            },
            "TEX-PREFLIGHT",
        ).to_dict()
        failed = {
            item["id"] for item in result["assertions"] if item["status"] == "fail"
        }
        self.assertIn("TEX-D003", failed, result)
        self.assertIn("TEX-D015", failed, result)

    def test_preflight_block_rejects_started_result(self) -> None:
        text = blocked_report().replace(
            "| input-001 | 未開始 | 未実行 |",
            "| input-001 | 開始済み | PASS |",
        )
        result = VALIDATORS["test-execution"](
            text,
            {
                "source_identity_present": False,
                "expected_snapshot_method": "未生成（TC本文が入力にない）",
                "expected_refs": ["input-001", "input-002"],
                "require_preflight_block": True,
                "expected_unexecuted_count": 2,
                "required_preflight_tokens": ["TC本文", "未実行"],
            },
            "TEX-PREFLIGHT",
        ).to_dict()
        failed = {
            item["id"] for item in result["assertions"] if item["status"] == "fail"
        }
        self.assertIn("TEX-D008", failed, result)
        self.assertIn("TEX-D015", failed, result)

    def test_preflight_block_rejects_procedure_rows_without_a_snapshot(self) -> None:
        text = blocked_report().replace(
            "## 手順・観測結果\n| TC参照 | 手順 / 観測点 (step_ref) | 操作 | 観測方法 | 期待結果 | 実測結果 | 状態 / 備考 |\n| --- | --- | --- | --- | --- | --- | --- |",
            "## 手順・観測結果\n| TC参照 | 手順 / 観測点 (step_ref) | 操作 | 観測方法 | 期待結果 | 実測結果 | 状態 / 備考 |\n| --- | --- | --- | --- | --- | --- | --- |\n| input-001 | 未提供 | 未実行 | 未提供 | 未提供 | なし | TC本文がない |",
        )
        result = VALIDATORS["test-execution"](
            text,
            {
                "source_identity_present": False,
                "expected_snapshot_method": "未生成（TC本文が入力にない）",
                "expected_refs": ["input-001", "input-002"],
                "require_preflight_block": True,
                "expected_unexecuted_count": 2,
                "required_preflight_tokens": ["TC本文", "未実行"],
            },
            "TEX-PREFLIGHT",
        ).to_dict()
        failed = {
            item["id"] for item in result["assertions"] if item["status"] == "fail"
        }
        self.assertIn("TEX-D010", failed, result)
        self.assertIn("TEX-D015", failed, result)

    def test_missing_previous_artifact_is_a_valid_preflight_block(self) -> None:
        text = blocked_report(count=1).replace(
            "| TC revision / content identity | なし | input.md |",
            "| TC revision / content identity | tcset-r10 | input.md |",
        ).replace(
            "| snapshot固定方法 | 未生成（TC本文が入力にない） | input.md |",
            "| snapshot固定方法 | 未生成（前回TC情報が入力にない） | input.md |",
        ).replace(
            "| 前回実行成果物参照 | なし | input.md |",
            "| 前回実行成果物参照 | 未提供 | input.md |",
        ).replace(
            "| input-001 | なし | 1 | なし |",
            "| input-001 | 未提供 | 1 | 未提供 |",
        )
        expected = {
            "source_identity_present": True,
            "expected_snapshot_method": "未生成（前回TC情報が入力にない）",
            "expected_refs": ["input-001"],
            "require_preflight_block": True,
            "expected_unexecuted_count": 1,
            "required_preflight_tokens": ["前回", "未実行"],
        }
        result = VALIDATORS["test-execution"](text, expected, "TEX-PREFLIGHT")
        assertion = next(item for item in result.assertions if item.id == "TEX-D006")
        self.assertEqual(assertion.status, "pass", result.to_dict())

        inconsistent = text.replace(
            "| input-001 | 未提供 | 1 | 未提供 |",
            "| input-001 | TC-OLD-001 | 1 | TC-OLD-001 |",
        )
        result = VALIDATORS["test-execution"](
            inconsistent, expected, "TEX-PREFLIGHT"
        )
        assertion = next(item for item in result.assertions if item.id == "TEX-D006")
        self.assertEqual(assertion.status, "fail", result.to_dict())


if __name__ == "__main__":
    unittest.main()
