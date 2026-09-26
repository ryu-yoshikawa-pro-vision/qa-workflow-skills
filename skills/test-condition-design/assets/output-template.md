# テスト観点・条件 / カバレッジ項目 出力テンプレート

## 観点範囲

- 対象テスト要求:
- テストレベル:
- 対象外:
- 仮定 / 未解決事項:

## テスト条件へ展開しないテスト要求

| テスト要求ID | 扱い | 理由 / 根拠 |
| --- | --- | --- |
|  | 別テストレベル / 残存リスク / 対象外 / ブロック中 |  |

## テスト観点・条件一覧

| 観点ID | テスト要求ID | テスト観点 / 条件 | カテゴリ | テスト技法 / 根拠 | カバレッジ基準 | 関連仕様根拠 / プロダクトリスク | 優先度 | 備考 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| TCN-001 | TR-001 |  |  |  |  |  | 高 / 中 / 低 |  |

## カバレッジ項目一覧

| カバレッジ項目ID | 観点ID | カバレッジ項目 | 導出元の技法 / 基準 | 期待挙動の根拠 | 優先度 | 備考 |
| --- | --- | --- | --- | --- | --- | --- |
| TCN-001-CI01 | TCN-001 |  |  |  | 高 / 中 / 低 |  |

## カバレッジ候補の扱い

| 候補 | 導出元 | 扱い | 理由 / 根拠 | カバー先 |
| --- | --- | --- | --- | --- |
|  |  | 対象外 / 別テストレベル / 残存リスク / 成立不能 / 重複 / ブロック中 |  |  |

## 任意: デシジョンテーブル

| ルール | 条件A | 条件B | 条件C | 期待結果 | 対応観点ID | 対応カバレッジ項目ID |
| --- | --- | --- | --- | --- | --- | --- |
| 1 |  |  |  |  |  |  |

## 任意: 状態遷移表

| 現在状態 | イベント / 操作 | 条件 | 期待する次状態 / 結果 | 観点ID | 対応カバレッジ項目ID |
| --- | --- | --- | --- | --- | --- |
|  |  |  |  |  |  |

## 任意: Pairwise / 組合せ

### 因子 / 値 / 制約

| 因子 | 値 | 制約 / 備考 |
| --- | --- | --- |
|  |  |  |

### 生成組合せ

| カバレッジ項目ID | 組合せ | 備考 |
| --- | --- | --- |
|  |  |  |

### 2-wiseカバレッジ確認

- 生成方法 / ツール:
- 制約:
- 成立可能なすべての値ペアをカバレッジ項目でカバー済みか:
- 確認根拠:

## 統合候補

| 候補 | 統合理由 | カバー先 |
| --- | --- | --- |
|  |  |  |

## Machine Runtime / Entity / Target mapping（機械証拠）

```text
<!-- Machine Runtime Input: test-condition-design -->
{ "skill": "test-condition-design", "runtime_contract_version": "runtime-contract-v1", "input": {} }
<!-- Machine Runtime Result: test-condition-design / <runtime_unit_key> -->
{ "envelope_version": "runtime-envelope-v1", "runtime_unit_key": "<runtime_unit_key>", "model_key": "<model-key>", "input_fingerprint": "sha256:<64 hex>", "generation_fingerprint": "sha256:<64 hex>", "runtime_status": "ok", "result_status": "ready", "freshness_status": "current", "payload": {} }
<!-- Machine Entities: test-condition-design -->
[{ "entity_schema_version": "entity-state-v1", "skill": "test-condition-design", "entity_type": "condition", "entity_ref": "condition:<stable-ref>", "content": {}, "content_fingerprint": "sha256:<64 hex>", "dependencies": [] }]
```

targetの`target_ref`、`target_content_fingerprint`、execution、CI ID、mapping status、test-data requirementは同じModel Keyとstable IDで追跡します。stale / legacy / unsupported / semantic coverage不足をcompleteへ置き換えません。
