# E2E対象選定

## 判断範囲

- selection ref / revision: E2ESEL-003 / 3
- current revision digest: sha256:e4ef4b56d1d0074ca2693a7041e4bc727e90e87b679a80eff52a7f8469e2e6c7
- current change reason: current source更新とreceipt-view候補の評価
- 自動化目的: checkout完了経路の反復回帰確認
- 候補母集団と完全性: checkoutとreceipt-viewを確認。完全
- source refs / revisions / currentness: SPEC-001@r9=current、TI-001@r5=current
- retired candidate IDs / 理由: E2E-CAND-002: currentな既存E2Eと重複するためretire
- 対象外: なし
- blocker / 再開条件: なし
- 選定状態: ready

## 候補と判断

| Candidate ID / key              | feature / item / condition refs | E2E候補範囲              | decision     | 技術非依存の価値・根拠                                          | source revision        | 保留・重複・制約     |
| ------------------------------- | ------------------------------- | ------------------------ | ------------ | --------------------------------------------------------------- | ---------------------- | -------------------- |
| E2E-CAND-001 / checkout-primary | TI-001                          | checkoutから注文確定まで | selected     | 主要業務経路で変更ごとの反復確認価値がある。                    | TI-001@r5、SPEC-001@r9 | revision 1から継続   |
| E2E-CAND-003 / receipt-view     | TI-001                          | 注文完了後の領収表示     | not_selected | currentなシステム境界の確認は必要だが、独立した反復価値が低い。 | TI-001@r5、SPEC-001@r9 | TCでの直接確認を維持 |

## 履歴

| revision | previous revision | candidate IDs / keys                                        | decisions / rationale                                                                                                                      | source refs / revisions / currentness  | retired candidate IDs / reason                     | change reason                                 | revision digest                                                         |
| -------- | ----------------- | ----------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ | -------------------------------------- | -------------------------------------------------- | --------------------------------------------- | ----------------------------------------------------------------------- |
| 1        | なし              | E2E-CAND-001 / checkout-primary; E2E-CAND-002 / non-payment | E2E-CAND-001: selected — 主要業務経路で変更ごとの反復確認価値がある; E2E-CAND-002: not_selected — currentな既存E2Eが同じ経路を確認している | SPEC-001@r8=current、TI-001@r4=current | なし                                               | 初回のcheckout経路選定                        | sha256:302469d858209482edd5f93901e0f8b302e4519714510f60e25114eddbc9c25e |
| 2        | 1                 | E2E-CAND-001 / checkout-primary                             | E2E-CAND-001: not_selected — SPEC-001 r9では既存E2Eによる確認が優先されると判断した                                                        | SPEC-001@r9=current、TI-001@r4=current | E2E-CAND-002: currentな既存E2Eと重複するためretire | SPEC改版で価値を再評価し既存E2Eとの重複を確認 | sha256:2c4f32c1d43597555d54b344429a852fab93d87c497475b72a04599ada483c9c |

## 下流への受渡し

- 選定refを利用するconsumer: e2e-test-inspection
- 直接TC指定／E2E直接実行との区別: selectionはE2E自動化価値判断で、既存E2E直接実行は変更しない。
- `e2e-test-inspection`へ渡す選定対象: E2E-CAND-001
- 未統合owner fixture / PR #22確認事項: current revision 3のMachine Entity保存とreadbackを横断検証
