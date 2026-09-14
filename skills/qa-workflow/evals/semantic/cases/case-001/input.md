# Eval Input
## 依頼
TCのない明示E2E対象について、既存のQA成果物を使える範囲だけ使い、必要なE2E工程を進めてください。repoの`tests/orders/order.spec.ts > order history`を対象にしたいですが、E2E対象inspectionの確認結果はまだありません。

## 既存成果物
- spec-analysis v3: 注文履歴の期待挙動は現在有効。
- test-analysis v1: 注文履歴をE2E対象として選定した成果物はない。
- E2E inspection: 未作成。repo構造・fixture・実行入口・安全条件の確認も未実施。

## 制約
- TCがないため、TCまたはTC IDを新規作成して経路を補わない。
- E2E対象選定自体は今回の依頼では要求していない。
