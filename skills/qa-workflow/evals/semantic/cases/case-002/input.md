# Eval Input
## 変更
Current Effective Authorityの「外部共有」条件が変更された。
- 変更前: 管理者のみ共有可能。
- 変更後: 管理者と編集者が共有可能。

## 既存状態
- spec-analysis: 変更を反映済み。
- question-analysis: 「閲覧者が共有可能か」は未確定で、その項目だけBlocker。
- test-analysis: 共有権限リスクを含む。
- test-requirement-design: 管理者のみを前提としたTRが1件ある。
- test-condition-design / test-case-design: そのTRから派生した権限ケースがある。
- 別機能の検索・ソートに関するTR/TCN/TCは今回のAuthority変更と無関係。

## 目的
必要な再検証・再実行範囲と現在の完了可否を判断する。
