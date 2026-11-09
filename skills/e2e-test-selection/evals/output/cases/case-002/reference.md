# E2E対象選定

## 判断範囲

- selection ref / revision: E2ESEL-002 / 1
- current change reason: source revisionと候補母集団を確認できず保留
- 自動化目的: 対象UI経路の価値判断
- 候補母集団と完全性: 未確認
- source refs / revisions / currentness: TI-009@unknown=unknown
- 対象外: なし
- blocker / 再開条件: ownerからcurrent TI一覧とrevisionを取得し、候補母集団を確定する
- 選定状態: blocked

## 候補と判断

| Candidate ID / key        | feature / item / condition refs | E2E候補範囲    | decision | 技術非依存の価値・根拠                       | source revision | 保留・重複・制約             |
| ------------------------- | ------------------------------- | -------------- | -------- | -------------------------------------------- | --------------- | ---------------------------- |
| E2E-CAND-003 / unknown-ui | TI-009                          | 未特定のUI経路 | blocked  | 対象範囲と価値を判断する情報が不足している。 | TI-009@unknown  | TI ownerのsource取得後に再開 |

## 履歴

| revision | previous revision | candidate IDs / keys | source refs / revisions / currentness | retired candidate IDs / reason | change reason |
| -------- | ----------------- | -------------------- | ------------------------------------- | ------------------------------ | ------------- |

- retired candidate IDs / 理由: なし

## 下流への受渡し

- 選定refを利用するconsumer: owner source確認後に再開
- 直接TC指定／E2E直接実行との区別: 既存E2E直接実行ではない
- `e2e-test-inspection`へ渡す選定対象: なし
- 未統合owner fixture / PR #22確認事項: TI-009の実owner artifact/revisionを横断確認
