# Eval Input
## Authority
- TC-101: ログイン後に注文履歴を表示できる。
- TC-102: 注文履歴の詳細を開くと対象注文の明細が表示される。

## E2E実装
- `tests/orders/order.spec.ts > order history`はTC-101に対応する。
- `tests/orders/order.spec.ts > order detail`はTC-102に対応する。

## 実行結果
- `order history`は`result-1`として実行済み。
- `order detail`は未実行で、環境到達性の確認が必要。

## 目的
既存QA ID graphの閉鎖性と、E2E実装参照から実行結果への追跡を混ぜずに分析する。
