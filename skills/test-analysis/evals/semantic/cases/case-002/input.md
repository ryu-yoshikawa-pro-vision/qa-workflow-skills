# Eval Input
## 変更内容
ファイル処理を同期処理から状態を持つ非同期処理へ変更する。
状態:
queued → processing → completed
processing → failed
failed → retrying → processing

## 制約
- 1ファイル最大1GB。
- 外部ストレージ障害時はfailedとなり、ユーザーが再試行できる。
- completedだけが結果閲覧可能。
- UIから状態と再試行操作を観測できる。
- 内部queueの実装詳細はUIから直接観測できない。

## 目的
リスク、技法、testabilityとtest levelを判断する。
