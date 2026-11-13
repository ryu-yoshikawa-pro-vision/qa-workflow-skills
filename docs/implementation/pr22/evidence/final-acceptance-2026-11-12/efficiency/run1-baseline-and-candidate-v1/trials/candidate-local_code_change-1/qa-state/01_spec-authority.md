# 01 仕様根拠（spec-analysis）— カート

- 対象範囲: ゲスト / 会員のカート（商品追加、数量変更、削除、表示時・チェックアウト開始時の再検証、ログイン時のゲストカート統合）
- 対象外: 注文データへの変換（チェックアウト・注文機能側で定義）
- 対象製品: `product/`（commit 2a8bcf57 と指定）。製品コード・仕様書は変更していない。コード（`src/...`）は仕様Authorityとして読んでいない。
- 対象外の確認: 本成果物は`product/docs/spec/features/cart.md`を起点に、正本判定の優先順位（`product/docs/spec/README.md`「正本判定の優先順位」）に従って解決した。

## 1. 情報源の区分

`product/docs/spec/README.md` の「正式な製品動作」に含まれる正本（優先順位1）と、それ以外の補助文書を分ける。

| 区分           | ID    | 情報源                                                                                                                        | 扱い                                                                                                                                     |
| -------------- | ----- | ----------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| 正本（優先1）  | SRC-1 | `product/docs/spec/features/cart.md`（BR-CART-001〜003 / AC-CART-001〜003 / UI・振る舞い規約 / SCREEN-STOREFRONT-CART状態表） | 期待挙動の一次根拠（優先2のBR/ACを含む）                                                                                                 |
| 正本（優先1）  | SRC-2 | `product/docs/spec/features/checkout-and-payment.md`（BR-CHECKOUT-002 / AC-CHECKOUT-002）                                     | カート版数・価格のチェックアウト境界。カート側の参照のみ                                                                                 |
| 正本（優先1）  | SRC-3 | `product/docs/spec/state-and-scenarios.md`（Cart状態、境界での再検証、シナリオ名）                                            | 状態モデル・シナリオ名                                                                                                                   |
| 正本（優先1）  | SRC-4 | `product/docs/spec/roles-and-permissions.md`（カート列）、`product/docs/spec/product-scope.md`                                | ロール範囲。詳細行の読取は未了（下記 INF-CART-009 参照）                                                                                 |
| ADR（優先4）   | SRC-5 | `product/docs/13_decisions/decision_log.md` D-010                                                                             | カート版数とチェックアウト不一致検出の決定。SRC-1と矛盾しない                                                                            |
| 補助（正本外） | SUP-1 | `product/docs/03_domain/business_rules.md` L136〜147、L258〜259                                                               | 正本一覧に含まれない。カートの詳細規則（版数、表示順、ゲストID、絶対/相対数量）を含むが、正本化されていないため候補根拠（INF/UNK）に限定 |
| 補助（正本外） | SUP-2 | `product/docs/03_domain/state_transitions.md` L44、L92〜101                                                                   | カート状態遷移、版数の扱い（SRC-3と整合）                                                                                                |
| 補助（正本外） | SUP-3 | `product/docs/05_ui/validation_and_messages.md` L44、L61、L65〜77                                                             | 数量範囲（1〜99整数、購入上限・在庫以下）、エラーメッセージ                                                                              |
| 補助（正本外） | SUP-4 | `product/docs/05_ui/screen_list.md` L19、L75、L96〜97                                                                         | `/cart`のロール、版数不一致時の挙動                                                                                                      |
| 補助（正本外） | SUP-5 | `product/docs/05_ui/ui_specifications.md` L64〜67                                                                             | カート画面の表示・価格改定の旧新併記                                                                                                     |
| 補助（正本外） | SUP-6 | `product/docs/05_ui/ui_content_dictionary.md` L157                                                                            | 統合サマリー文言（追加 / 上限超過 / 除外件数）                                                                                           |
| 補助（正本外） | SUP-7 | `product/docs/12_quality/acceptance_criteria.md` §4 L58、L61〜67                                                              | 品質受入基準。L61は後述の矛盾（Q-CART-001）を含む                                                                                        |
| 補助（正本外） | SUP-8 | `product/docs/02_architecture/use_case_catalog.md` L46〜50                                                                    | ユースケース名と責務（版数更新・絶対数量）                                                                                               |
| 補助（正本外） | SUP-9 | `product/docs/03_domain/roles_and_permissions.md` L37                                                                         | カート追加の権限（ゲスト○、customer○、operator×、admin×）                                                                                |
| 参照のみ       | -     | `product/docs/spec/unresolved-specifications.md`                                                                              | カート関連の未確定項目なし（ピクセル一致の未確定はUI全般）                                                                               |
| 参照のみ       | -     | `product/docs/spec/known-deviations.md`                                                                                       | 有効な既知差異なし                                                                                                                       |

- 案件固有の情報源優先順位は、QA側のProject Contextとして定義されていない。このため`product/docs/spec/README.md`の正本判定順をそのまま使い、QA側での優先順位の新規決定はしていない。
- 製品コードの参照先（`src/application/use-cases/cart-use-cases.ts`等）は実装確認用であり、期待挙動の根拠にしていない。

## 2. 現在有効な仕様根拠（SPEC / DECISION）

| ID            | 種別     | 内容                                                                                                                                                                    | 根拠                                           | 状態                                                  |
| ------------- | -------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------- | ----------------------------------------------------- |
| SPEC-CART-001 | SPEC     | 同一SKUの数量は「在庫数」「購入上限数」「99」の最小値を超えない。上限超過の指定は数量を自動補正せず操作全体を拒否し、変更前数量を維持する                               | SRC-1 BR-CART-001、AC-CART-001                 | current                                               |
| SPEC-CART-002 | SPEC     | 数量0の指定で該当明細をカートから削除する                                                                                                                               | SRC-1 BR-CART-001                              | current                                               |
| SPEC-CART-003 | SPEC     | ログイン時、会員カートを基準にゲストカートをSKU単位で合算統合する。許容上限超過分、非公開商品、会員ランク不足、無効SKU、在庫0の明細は統合対象から除外し、理由を明示する | SRC-1 BR-CART-002、AC-CART-002                 | current                                               |
| SPEC-CART-004 | SPEC     | 統合元のゲストカートは破棄済み（abandoned）へ遷移する                                                                                                                   | SRC-1 BR-CART-002、AC-CART-002。SRC-3 Cart状態 | current                                               |
| SPEC-CART-005 | SPEC     | カート画面の表示時およびチェックアウト開始時に、商品の公開状態、購入権限、価格、在庫数を再検証する                                                                      | SRC-1 BR-CART-003、SRC-3 境界再検証            | current                                               |
| SPEC-CART-006 | SPEC     | 価格変更が発生している場合、会員の承認が得られるまでチェックアウト手続きへ進めない                                                                                      | SRC-1 BR-CART-003、AC-CART-003                 | current                                               |
| SPEC-CART-007 | SPEC     | 問題のある明細が含まれる場合、ユーザーによる承認または明細修正が行われない限りチェックアウトへ進めない                                                                  | SRC-1 AC-CART-003                              | current                                               |
| SPEC-CART-008 | SPEC     | カートはゲストまたは会員（customer）のみが利用できる。operatorとadminは利用不可（`/cart`は拒否）                                                                        | SRC-1 UI規約、SRC-4、SUP-4 L75                 | current（SUP-4は補助確認）                            |
| SPEC-CART-009 | SPEC     | カート明細に、商品情報、画像、現在価格、数量、上限数、問題点、合計金額、空状態を表示する                                                                                | SRC-1 UI規約                                   | current                                               |
| SPEC-CART-010 | SPEC     | 空状態は「カートが空である旨」と「商品を探すための導線」を表示する（web-desktop）                                                                                       | SRC-1 SCREEN状態表 `empty`                     | current                                               |
| SPEC-CART-011 | SPEC     | 問題ありの状態は「購入できない理由」と「修正用のアクション」を表示する（web-desktop）                                                                                   | SRC-1 SCREEN状態表 `invalid-items`             | current                                               |
| SPEC-CART-012 | SPEC     | 既定状態は web-desktop と android で表示する                                                                                                                            | SRC-1 SCREEN状態表 `default`                   | current                                               |
| SPEC-CART-013 | SPEC     | 更新処理の実行中は、同一カートに対する変更操作の二重実行を防止する（防止方法は未規定。観測結果は「1回だけ反映」）                                                       | SRC-1 UI規約                                   | current（方法はUNK-CART-007）                         |
| SPEC-CART-014 | SPEC     | チェックアウト開始・確認・注文作成の各境界で、カート版数と価格の不一致を検出し、注文・決済を作らずカート画面へ戻す                                                      | SRC-2 BR-CHECKOUT-002、AC-CHECKOUT-002、SRC-3  | current（チェックアウト側の責務。カートは版数を提供） |
| DEC-CART-001  | DECISION | カート変更時は親カートの版数のみを更新し、チェックアウトセッションは同一トランザクションで更新しない。不一致はルートガード・確認画面・注文確定で検出する                | SRC-5 D-010、SUP-2 L44                         | current（ADR。SRC-1と矛盾なし）                       |

## 3. 補助文書由来の候補根拠（INFERENCE / UNKNOWN）

正本外の補助文書だけに存在する規則は、`SPEC` へ昇格させず候補として保持する。期待結果の根拠に使う前に承認が必要（`06_pending-approvals.md`）。

| ID           | 種別      | 内容                                                                                                                                                                                                                        | 出典                                                                                                                                                | 状態                                   |
| ------------ | --------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------- |
| INF-CART-001 | INFERENCE | 「許容上限」は SPEC-CART-001 の最小値（在庫数・購入上限数・99）と同義                                                                                                                                                       | SRC-1 BR-CART-002 は「許容上限」と記載するが定義はない。SUP-1 L146「購入許容上限」                                                                  | 承認待ち（Q-CART-004）                 |
| INF-CART-002 | INFERENCE | 相対数量の追加（同一SKUへの加算）と絶対数量の変更（数量変更）を分ける契約                                                                                                                                                   | SUP-1 L138、SUP-8 L47                                                                                                                               | 承認待ち                               |
| INF-CART-003 | INFERENCE | 成功した追加・数量変更・削除で親カート版数を1回ずつ増やす。統合でも利用者カートの版数を増やす                                                                                                                               | SUP-1 L144、SUP-7 L61、SUP-1 L146                                                                                                                   | 承認待ち（Q-CART-001と併せて）         |
| INF-CART-004 | INFERENCE | 初回追加時はカート版数を要求しない。数量変更・削除は版数を要求する                                                                                                                                                          | SUP-1 L139、SUP-7 L62、SUP-8 L46〜48                                                                                                                | 承認待ち                               |
| INF-CART-005 | INFERENCE | 明細の表示順は作成日時の昇順、同時刻は明細IDの昇順                                                                                                                                                                          | SUP-1 L145                                                                                                                                          | 承認待ち                               |
| INF-CART-006 | INFERENCE | ゲストIDはローカルストレージに保存し、同一ブラウザからの再訪でゲストカートを再取得する                                                                                                                                      | SUP-1 L143                                                                                                                                          | 承認待ち                               |
| INF-CART-007 | INFERENCE | 価格改定の承認はカート単位（カート内の最新価格変動をまとめて承認）。承認で版数と更新日時を更新する                                                                                                                          | SUP-8 L50、SUP-1 L144                                                                                                                               | 承認待ち                               |
| INF-CART-008 | INFERENCE | カートの合計金額は、現在価格（会員ランク割引を適用後）の小計の合算。単価割引額は切り捨て                                                                                                                                    | SUP-7 L66、SUP-1 L119                                                                                                                               | 承認待ち（計算式の正本は未確認）       |
| INF-CART-009 | INFERENCE | ロール範囲の詳細（カート列の全行）は SRC-4 の読取で確認予定。現時点は SUP-9 とSPEC-CART-008で整合                                                                                                                           | SRC-4、SUP-9 L37                                                                                                                                    | 読取未了                               |
| UNK-CART-001 | UNKNOWN   | 拒否された操作（上限超過の追加・変更）で親カート版数が増えるか。SUP-7 L61は「購入上限数超過時の追加拒否」を版数増分の対象に含めるが、SUP-1 L137（操作全体拒否）とSUP-1 L144（変更時の版数更新）は拒否時の版数変化を示さない | SUP-7 L61 対 SUP-1 L137・L144                                                                                                                       | **矛盾**（Q-CART-001）                 |
| UNK-CART-002 | UNKNOWN   | 追加操作で相対数量0・負数・非整数を指定した場合の扱い。SUP-3 L44は「数量 1〜99の整数」とするが、0は「削除」（SPEC-CART-002）が更新操作に限られる                                                                            | SUP-3 L44、SPEC-CART-002                                                                                                                            | 未規定（Q-CART-002）                   |
| UNK-CART-003 | UNKNOWN   | 統合対象のゲストカートが空、または統合対象が全件除外となった場合のゲストカート状態                                                                                                                                          | SRC-1、SUP-1 いずれも未規定                                                                                                                         | 未規定（Q-CART-003）                   |
| UNK-CART-004 | UNKNOWN   | 複数の問題（価格変更・在庫不足等）や複数の除外理由が同時にある場合の表示順・優先順位                                                                                                                                        | SRC-1 は表示要素のみ規定。探索報告 `product/docs/reports/2026-08-01_ui-ux-user-journey-deep-exploration.md` L524 は「未確認」と記載（補助・非正本） | 未規定（Q-CART-006）                   |
| UNK-CART-005 | UNKNOWN   | ゲストIDが端末ストレージ削除で失われた場合の挙動                                                                                                                                                                            | SUP-1 L143 は再訪時の取得のみ規定                                                                                                                   | 未規定（Q-CART-007に含む）             |
| UNK-CART-007 | UNKNOWN   | 二重実行防止の方式（ボタン無効化・サーバ側冪等性等）。観測上の結果（1回だけ反映）のみ SPEC-CART-013 で規定                                                                                                                  | SRC-1                                                                                                                                               | 方式は未規定（テスト対象外の実装方式） |

## 4. 正本間の整合確認

- SRC-1 と SRC-5（D-010）: 整合。カート変更は版数のみ更新し、チェックアウト側で検出する。
- SRC-1 と SRC-2（BR-CHECKOUT-002）: 整合。カートは版数と価格を提供し、チェックアウトが不一致時に戻す。
- SRC-1 と SRC-3（Cart状態、境界再検証）: 整合。
- SRC-1 と SUP-1〜SUP-9: 上限・除外理由・ロール・UI表示は整合。**版数の扱いが SUP-7 L61 と他補助文書で矛盾**（UNK-CART-001）。
- 矛盾・衝突により解決した仕様根拠はない。UNK-CART-001 は局所ブロックとして扱う（`02_question-analysis.md`）。

## 5. 追跡性に関する指摘（仕様側の修正候補、本QAでは変更しない）

- `product/docs/spec/features/cart.md` の `empty` 状態の「関連オラクル」は `BR-CART-001` を指すが、空状態を規定するBRはない。仕様所有者による確認候補。
- 正本の cart.md には、表示順・ゲストID保持・版数増分・絶対/相対数量の区別が記載されていない（SUP-1のみ）。正本化する場合は `product/docs/spec/change-process.md` の手続きに従う必要がある（Q-CART-008）。

## 6. 基本停止条件の確認

- 対象範囲は特定済み。
- 現在有効な仕様根拠は SPEC-CART-001〜014 と DEC-CART-001 で解決済み。
- 重大な競合は UNK-CART-001 のみ。対象は「拒否時の版数変化」の期待結果に限られるため、全体停止にはしない（局所ブロック）。
