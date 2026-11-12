# Eval Input

## Authority

- AUTH-ORDER-01: ログイン後に注文履歴を表示できる。
- AUTH-ORDER-02: 注文履歴の詳細を開くと対象注文の明細が表示される。

## テストケース

- TC-101: AUTH-ORDER-01を根拠に、ログイン後に注文履歴が表示されることを確認する。
- TC-102: AUTH-ORDER-02を根拠に、注文履歴の詳細で対象注文の明細が表示されることを確認する。
- 今回の監査入力には、TC-101／TC-102の上流のTR、TCN、CIは含まれない。

## E2E実装

- `tests/orders/order.spec.ts > order history`はTC-101に対応する。
- `tests/orders/order.spec.ts > order detail`はTC-102に対応する。

## 実行結果

- `order history`は`result-1`として実行済み。
- `order detail`は未実行で、環境到達性の確認が必要。

## 目的

既存QA ID graphの閉鎖性と、E2E実装参照から実行結果への追跡を混ぜずに分析する。
