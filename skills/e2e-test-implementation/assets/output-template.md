# E2Eテスト実装 出力テンプレート

## 実装対象

| E2E対象 / 識別子 | TC ID（存在時のみ） | 明示対象 / 既存E2E参照 | 確認済み期待挙動 | 扱い |
| --- | --- | --- | --- | --- |
|  |  |  |  | 新規実装 / 既存E2E再利用 / 既存E2E拡張 / ブロック中 |

## 実装前の状態

| 項目 | 値 | 確認元 |
| --- | --- | --- |
| branch |  | repo |
| HEAD commit |  | repo |
| working tree |  | repo |
| 変更予定ファイルとの競合 |  | repo |
| inspectionからの差分 |  | repo / 実対象 |

## E2E実装参照

| E2E実装参照 | test file | Playwright title path | TC ID（存在時のみ） | 扱い |
| --- | --- | --- | --- | --- |
| tests/example.spec.ts > example | tests/example.spec.ts | example |  | 新規実装 / 再利用 / 拡張 |

## 変更・再利用したファイル

| ファイル | 変更内容 / 再利用理由 | inspection事実との対応 |
| --- | --- | --- |
|  |  |  |

## 静的・軽量検証

| 検証 | 実行command / 条件 | 結果 | 非破壊確認 / 未実施理由 |
| --- | --- | --- | --- |
| lint / typecheck / discovery / 既存validation |  | PASS / FAIL / 未実施 / ブロック中 |  |

## inspection差分・ブロック・要再検証

| 範囲 | 状態 | 理由 / 影響 | 次の担当 |
| --- | --- | --- | --- |
|  | なし / 要再検証 / ブロック中 |  |  |
