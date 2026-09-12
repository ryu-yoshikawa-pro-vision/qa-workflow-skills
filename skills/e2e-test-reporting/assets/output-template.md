# E2Eテスト結果報告 出力テンプレート

## 対象・環境

| 項目 | 値 | 参照 / 確認元 |
| --- | --- | --- |
| 対象機能 / 範囲 |  |  |
| テスト環境URL / origin |  |  |
| テスト対象version / build ID |  |  |
| E2Eコードbranch / commit / working tree |  |  |
| 実行日時 / Playwright project |  |  |

## run全体結果

| 項目 | 値 | 確認元 | raw fact / 導出値 |
| --- | --- | --- | --- |
| Playwright run全体status |  |  | raw fact / 確認不能 |
| process exit code |  |  | raw fact |
| run-level / global error |  |  | raw fact |

## primary対象集計（単位を混同しない）

| 論理的な要求primary対象 | E2E実装参照 / TC ID（存在時のみ） | resolved primary TestCase数 | 実際に開始したresolved primary TestCase数 | 未実行logical理由 | 未実行resolved理由 |
| --- | --- | ---: | ---: | --- | --- |
| login-flow | tests/example.spec.ts > login | 1 | 1 |  |  |

## resolved primary結果 / attempt結果

| 論理的な要求primary対象 | resolved primary TestCase参照 | 実行開始 | 結果 | expectedStatus | outcome | retry attempt数（別集計） | 初回 / retry履歴 | 実行結果参照 |
| --- | --- | --- | --- | --- | --- | ---: | --- | --- |
| login-flow | session-test-1 | 開始 | passed | passed | expected | 1 | passed (retry 0) | result.jsonの対象参照 |

開始していないresolved primaryは、`結果`へPlaywright値や`未実行`を入れず、未実行理由を記録します。`expectedStatus` / `outcome`もPlaywrightが返していない限り空欄にします。

## TC・E2E・実行・分析追跡

| TC ID（存在時のみ） | E2E実装参照 | resolved primary TestCase / 実行結果参照 | 分析結果参照 | 報告上の扱い |
| --- | --- | --- | --- | --- |
|  | tests/example.spec.ts > login | session-test-1 |  |  |

## cleanup・証跡・残存リスク

| 項目 | 状態 / 内容 | 安全な参照 |
| --- | --- | --- |
| cleanup | 成功 / 失敗 / 未確認 / 対象なし / 意図的に残した状態 |  |
| 残存副作用 |  |  |
| 証跡 |  | secretを含まないローカル参照のみ |
| ブロック中 / 未解決事項 / 残存リスク |  |  |
