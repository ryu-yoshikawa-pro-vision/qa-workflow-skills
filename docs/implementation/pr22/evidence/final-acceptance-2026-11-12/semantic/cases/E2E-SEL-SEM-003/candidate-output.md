# E2E対象選定

## 判断範囲

- selection ref / revision: E2ESEL-004 / revision 2
- current revision digest: `sha256:b0d7049b9b2c97be29b08f844c563a6014478305b4a56ea6c198af177ca1cb92`（runtime `selection_contract.py` の出力値。record内容の整合性値であり、保存先の真正性・readbackは証明しない）
- current change reason: TI-002のsource revision更新とTI-003の候補追加
- 自動化目的: 利用者の主要checkout経路を反復確認する技術非依存の価値選定
- 候補母集団と完全性: TI-001、TI-002、TI-003の3 scopeで完全（`population_complete=true`、blockerなし）。候補は E2E-CAND-001〜003 の3件
- source refs / revisions / currentness:
  - `E2E-01@e2e-r3=current`
  - `REQ-CHECKOUT@req-r4=current`
  - `REQ-ORDER-TRACKING@req-track-r1=current`
  - `TI-001@ti1-r1=current`
  - `TI-002@ti2-r2=current`（revision 1では `ti2-r1`）
  - `TI-003@ti3-r1=current`
- retired candidate IDs / 理由: なし
- 対象外: locator、fixture、Playwright設定、実装可否、実装コスト、テスト実行（選定根拠に含めない）。TC、Product Risk、TR、CIの作成・複製も行わない
- blocker / 再開条件: blockerなし。ただし E2E-CAND-002 と E2E-CAND-003 が `deferred` のため、選定状態は ready にならない。再開条件は各候補の価値判断を確定すること
- 選定状態: unresolved

## 候補と判断

| Candidate ID / key                 | feature / item / condition refs | E2E候補範囲                                                          | decision | 技術非依存の価値・根拠                                                                               | source revision                                | 保留・重複・制約                                       |
| ---------------------------------- | ------------------------------- | -------------------------------------------------------------------- | -------- | ---------------------------------------------------------------------------------------------------- | ---------------------------------------------- | ------------------------------------------------------ |
| E2E-CAND-001 / `checkout-primary`  | REQ-CHECKOUT / TI-001           | 主要checkout完了経路                                                 | selected | 主要checkout完了経路をUIから反復確認する価値がある                                                   | REQ-CHECKOUT@req-r4, TI-001@ti1-r1             | なし                                                   |
| E2E-CAND-002 / `checkout-shipping` | REQ-CHECKOUT / TI-002           | 配送条件を含むcheckout経路（今回、配送再試行の業務経路が追加された） | deferred | TI-002がti2-r2へ更新され配送再試行の業務経路が追加されたが、その反復確認価値は未評価のため保留を維持 | REQ-CHECKOUT@req-r4, TI-002@ti2-r2             | 判断情報の不足による保留。完了選定に数えない           |
| E2E-CAND-003 / `order-tracking`    | REQ-ORDER-TRACKING / TI-003     | 注文追跡経路                                                         | deferred | 注文追跡経路の反復確認価値を判断する根拠が入力になく未評価                                           | REQ-ORDER-TRACKING@req-track-r1, TI-003@ti3-r1 | 新規候補。判断情報の不足による保留。完了選定に数えない |

## 履歴

| revision | previous revision | candidate IDs / keys                                                  | decisions / rationale                                                                                                                             | source refs / revisions / currentness                                                            | retired candidate IDs / reason | change reason           | revision digest                                                           |
| -------- | ----------------- | --------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------ | ------------------------------ | ----------------------- | ------------------------------------------------------------------------- |
| 1        | —                 | E2E-CAND-001 / `checkout-primary`; E2E-CAND-002 / `checkout-shipping` | E2E-CAND-001: selected、主要checkout完了経路をUIから反復確認する価値がある / E2E-CAND-002: deferred、現行source上は配送条件の反復確認価値が未評価 | E2E-01@e2e-r3=current; REQ-CHECKOUT@req-r4=current; TI-001@ti1-r1=current; TI-002@ti2-r1=current | なし                           | 初回のE2E自動化価値判断 | `sha256:4d5f0ed37a58d7e6d001dace61ed748d9fd18f0e382efe3a8d0d2b9b7794d464` |

revision 1 の snapshot は runtime で検証済みで、履歴は連続しています（`history_complete=true`）。revision 1 の digest は runtime が revision 1 の入力から再計算した値と一致しました。

## 下流への受渡し

- 選定refを利用するconsumer: なし（選定状態が unresolved のため、現時点で下流の実装対象として利用できる選定ではない）
- 直接TC指定／E2E直接実行との区別: 本選定は TC 直接指定ではなく、TCを伴わないE2E自動化候補の価値判断として扱う。既存E2Eの実行だけの経路は含まない
- `e2e-test-inspection`へ渡す選定対象: なし。ready ではないため、inspection に渡せる targets は空。`selected` は E2E-CAND-001 のみで、残り2件の判断が確定するまで inspection へ渡さない
- 未統合owner fixture / PR #22確認事項: 本入力はfixture由来の値で、共有保存先のreadbackによる確認は行っていない。source currentness は入力記録上の値として扱う
