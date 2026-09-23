# テスト分析 出力テンプレート

## テスト分析範囲

- 対象機能 / 変更:
- 案件固有のテスト目的 / 重点:
- テストレベル:
- 環境制約:
- 対象外:
- ブロッカー:
- 対象 / 実行範囲: テスト分析 / E2E対象選定

## 変更 / 影響マップ

| 領域 | 変更種別 | 根拠 / 依存関係 | 想定影響 |
| --- | --- | --- | --- |
|  | 新規 / 変更 / 削除 / 回帰影響 / 参考 |  |  |

## プロダクトリスク一覧

| リスクID | 製品上のリスク / 失敗 | 関連する現在有効な仕様根拠 / 変更 / 依存 | 影響度 | 発生可能性 | レベル | 根拠 | 判断信頼度 / 備考 |
| --- | --- | --- | ---: | ---: | --- | --- | --- |
| RISK-001 |  |  |  |  | 高 / 中 / 低 |  |  |

## テスト重点

| 優先度 | 重点領域 | 関連プロダクトリスク / 根拠 | 設計深度 / 備考 |
| --- | --- | --- | --- |
| 高 |  |  |  |

## 選択したテスト技法

| テスト技法 | 適用領域 | 選択理由 | 関連プロダクトリスク / 現在有効な仕様根拠 | `test-condition-design`への着眼点 |
| --- | --- | --- | --- | --- |
|  |  |  |  |  |

## テスト可能性 / テストレベル判断

| 要件 / 懸念 | 操作可能か | 観測可能か | 合否判定可能か | 選択テストレベル | 扱い / 備考 |
| --- | --- | --- | --- | --- | --- |
|  | 可 / 不可 / 一部 | 可 / 不可 / 一部 | 可 / 不可 / 一部 |  | 現在レベル / 別レベル / 残存リスク / 対象外 / ブロック中 |

## 残存リスク

| リスク / 要件 | 十分にカバーできない理由 | 推奨対応 |
| --- | --- | --- |
|  |  |  |

## E2E対象選定（E2E対象の選定自体を要求された場合だけ）

| 自動化目的 | 候補範囲 | 技術非依存の判断基準 / 根拠 | 対象外 / 保留 |
| --- | --- | --- | --- |
|  |  |  |  |

## Machine Runtime / Entity（機械証拠）

runtime dispatchを行った場合は、入力・結果・Entityを次の固定ブロックで保存します。expected unitやfingerprintを実行者が追記してはいけません。

`test_analysis_context`のMachine Entity contentには、実際に参照したAuthorityの`entity_ref`を`authority_refs[]`へ、同一invocation内のProduct Risk identityを`risk_refs[]`へ記録します。自然言語の残存リスクや重点から依存を推測せず、fingerprintはruntimeがcurrent Entityから決定します。

```text
<!-- Machine Runtime Input: test-analysis -->
{ "skill": "test-analysis", "runtime_contract_version": "runtime-contract-v1", "input": {} }
<!-- Machine Runtime Result: test-analysis / analysis_entities -->
{ "envelope_version": "runtime-envelope-v1", "runtime_unit_key": "analysis_entities", "input_fingerprint": "sha256:<64 hex>", "generation_fingerprint": "sha256:<64 hex>", "runtime_status": "ok", "result_status": "ready", "freshness_status": "current", "payload": {} }
<!-- Machine Entities: test-analysis -->
[{ "entity_schema_version": "entity-state-v1", "skill": "test-analysis", "entity_type": "risk", "entity_ref": "risk:<stable-ref>", "content": {}, "content_fingerprint": "sha256:<64 hex>", "dependencies": [] }]
```
