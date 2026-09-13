# Eval Input
## Authority
- 注文履歴を開くと、現在有効な注文の一覧が表示される。
- 注文詳細を開くと、対象注文の明細が表示される。

## TCなしE2E Review対象
### `tests/orders/order.spec.ts > order history`
注文履歴を開き、一覧が表示されることを確認する実装。

### `tests/orders/order.spec.ts > order detail`
注文詳細を開き、明細が表示されることを確認する実装。

## 目的
TCがないE2E testwareをCold Reviewし、E2Eコード自身を仕様根拠にして自己正当化せず、現在有効なAuthorityと確認済み期待挙動に照らしてレビューする。
