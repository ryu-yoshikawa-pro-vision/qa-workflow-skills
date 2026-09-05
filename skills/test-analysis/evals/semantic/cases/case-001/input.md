# Eval Input
## 変更内容
会話の閲覧権限判定を、画面側の単純な所有者判定からAPIのrole-based判定へ変更する。
roles:
- owner: 閲覧可
- editor: 閲覧可
- viewer: 閲覧可
- external: 公開設定が許可する場合だけ閲覧可

## 影響
誤判定すると、権限のない外部ユーザーへ会話本文・参加者情報が露出する可能性がある。
複数roleと公開設定の組合せがある。
既存実装から判定経路が大きく変わる。

## 目的
Product Risk、Impact/Likelihood、テスト重点を設計する。
