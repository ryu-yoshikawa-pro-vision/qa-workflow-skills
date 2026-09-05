# Eval Input
## Test Requirement
TR-010: roleと公開設定の組合せで会話閲覧可否が正しいことを保証する。

## Factors
- role: owner / editor / viewer / external
- visibility: private / company / public
- device: desktop / mobile

## 制約
- owner/editor/viewerは同一会社ユーザー。
- externalはprivateでは常に閲覧不可。
- publicでは全role閲覧可。
- deviceは認可判定ロジックへ影響しないが、UI表示差は別TRで確認済み。

## 目的
組合せ技法を使う範囲と、個別に確認すべき高リスク条件を設計する。
