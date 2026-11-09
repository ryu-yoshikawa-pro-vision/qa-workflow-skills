# E2E対象選定

## 判断範囲

- selection ref / revision: E2ESEL-001 / 1
- current change reason: 初回のcheckout E2E対象選定
- 自動化目的: checkout完了経路の反復回帰確認
- 候補母集団と完全性: TI-001、TI-002。完全
- source refs / revisions / currentness: SPEC-001@r8=current、TI-001@r4=current
- 対象外: 決済なしの既存E2Eで確認済みの共通画面
- blocker / 再開条件: なし
- 選定状態: ready

## 候補と判断

| Candidate ID / key              | feature / item / condition refs | E2E候補範囲              | decision     | 技術非依存の価値・根拠                                  | source revision        | 保留・重複・制約                   |
| ------------------------------- | ------------------------------- | ------------------------ | ------------ | ------------------------------------------------------- | ---------------------- | ---------------------------------- |
| E2E-CAND-001 / checkout-primary | TI-001                          | checkoutから注文確定まで | selected     | 主要業務経路で変更ごとの反復確認価値がある。            | TI-001@r4、SPEC-001@r8 | 既存TC-001は直接指定の確認に再利用 |
| E2E-CAND-002 / non-payment      | TI-002                          | 決済なし経路             | not_selected | 既存E2E E2E-01が同じ経路をcurrentな根拠で確認している。 | TI-001@r4、SPEC-001@r8 | 既存E2Eと重複                      |

## 履歴

| revision | previous revision | candidate IDs / keys | source refs / revisions / currentness | retired candidate IDs / reason | change reason |
| -------- | ----------------- | -------------------- | ------------------------------------- | ------------------------------ | ------------- |

- retired candidate IDs / 理由: なし

## 下流への受渡し

- 選定refを利用するconsumer: e2e-test-inspection
- 直接TC指定／E2E直接実行との区別: TC-001はTC直接指定。selectionはE2E自動化価値判断。
- `e2e-test-inspection`へ渡す選定対象: E2E-CAND-001
- 未統合owner fixture / PR #22確認事項: なし
