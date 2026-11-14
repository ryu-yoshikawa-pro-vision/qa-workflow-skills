# カート機能 仕様根拠（spec-analysis 草案）

- 対象: カート（`SCREEN-STOREFRONT-CART`、`/cart`）
- 製品対象: commit `2a8bcf57`（ユーザー指定。本セッションではgit照合していない）
- 作成方法: 手作業による草案。Skill付属のruntime / helper（`authority_entities.py` 等）は未実行
- 対象 / 実行範囲: 仕様分析（カート）

## 1. 使用した情報源と権威区分

| 区分                                          | 情報源                                                                                                       | 扱い                                                              |
| --------------------------------------------- | ------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------- |
| 正式な製品動作（正本）                        | `product/docs/spec/features/cart.md`（BR-CART-001〜003、AC-CART-001〜003、画面状態、UI規約）                 | 権威あり。`SPEC` の根拠                                           |
| 正式な製品動作（正本）                        | `product/docs/spec/state-and-scenarios.md`（Cart遷移 active→consumed/abandoned、終端状態、再検証の境界）     | 権威あり。`SPEC` の根拠                                           |
| 正式な製品動作（正本）                        | `product/docs/spec/roles-and-permissions.md` / `product-scope.md`                                            | 一部確認（カート対象ロール・ゲスト/会員の利用範囲）。全文は未確認 |
| 補助・運用文書（spec/README上は正本ではない） | `product/docs/01_requirements/functional_requirements.md` のFR-CA-001〜018、FR-AU-002/004/011、FR-ST-002/003 | 権威未承認。`INFERENCE` 相当。P-01で承認待ち                      |
| 補助・運用文書                                | `product/docs/03_domain/business_rules.md` のカート節（L136〜147）                                           | 同上                                                              |
| 補助・運用文書                                | `product/docs/12_quality/acceptance_criteria.md`（カート関連AC）                                             | 同上                                                              |
| 補助・運用文書                                | `product/docs/05_ui/ui_specifications.md` §6、`validation_and_messages.md`（CART_VERSION_CHANGED 等）        | 同上                                                              |
| テスト戦略（案件のテスト方針）                | `product/docs/08_testing/test_strategy.md`、`07_testability/testability_design.md`                           | テストレベル・観測制約の参考。仕様根拠ではない                    |
| 不使用                                        | 既存テスト、実装コード、Seed                                                                                 | 仕様根拠にしない（既存テストの期待値は仕様根拠にしない規則）      |

補足: `spec/README.md` の正式な製品動作は `features/**`・`state-and-scenarios.md`・`ui-ux-contract.md`・`roles-and-permissions.md`・`product-scope.md` である。`01_requirements` と `03_domain` のカート規則は、spec/README上の正本一覧に含まれていない。このため本書は両者を `SPEC` とせず、`INFERENCE` 扱いで保持する。

## 2. SPEC（権威ある情報源に明記）

| ID            | 内容                                                                                                                                           | 根拠                                                     |
| ------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------- |
| SPEC-CART-001 | 同一SKUは合算して上限判定する。上限は「在庫数」「購入上限数」「99」の最小値                                                                    | `cart.md` BR-CART-001                                    |
| SPEC-CART-002 | 上限を超える指定は数量を自動補正せず操作全体を拒否し、変更前の数量を維持する                                                                   | `cart.md` BR-CART-001、AC-CART-001                       |
| SPEC-CART-003 | 数量0の指定は該当明細をカートから削除する                                                                                                      | `cart.md` BR-CART-001                                    |
| SPEC-CART-004 | ログイン時は会員カートを基準に、ゲストカートをSKU単位で数量合算して統合する                                                                    | `cart.md` BR-CART-002                                    |
| SPEC-CART-005 | 統合時、許容上限を超える数量分、非公開商品、会員ランク不足、無効SKU、在庫0の商品は統合対象から除外し、理由を明示する                           | `cart.md` BR-CART-002                                    |
| SPEC-CART-006 | 統合元のゲストカートは abandoned へ遷移する                                                                                                    | `cart.md` BR-CART-002、`state-and-scenarios.md` 状態遷移 |
| SPEC-CART-007 | カート表示時およびチェックアウト開始時に、公開状態・購入権限・価格・在庫数を再検証する                                                         | `cart.md` BR-CART-003、`state-and-scenarios.md` 境界     |
| SPEC-CART-008 | 価格変更がある場合、会員の承認が得られるまでチェックアウトへ進めない                                                                           | `cart.md` BR-CART-003、AC-CART-003                       |
| SPEC-CART-009 | 問題のある明細が含まれる限り、修正または削除・承認が行われるまでチェックアウトへ進めない                                                       | `cart.md` AC-CART-003                                    |
| SPEC-CART-010 | カートはゲストまたは会員のみが利用できる。operator / admin は利用不可                                                                          | `cart.md` UI規約、`roles-and-permissions.md` 一部確認    |
| SPEC-CART-011 | 明細には商品情報、画像、現在価格、数量、上限数、問題点、合計金額、空状態を表示する                                                             | `cart.md` UI規約                                         |
| SPEC-CART-012 | 更新処理中は同一カートへの変更操作の二重実行を防止する                                                                                         | `cart.md` UI規約                                         |
| SPEC-CART-013 | 画面状態は `default`（web-desktop / android）、`empty`（web-desktop）、`invalid-items`（web-desktop、シナリオ `cart-with-invalid-items`）の3つ | `cart.md` 主要なUI状態                                   |
| SPEC-CART-014 | Cart遷移は active→consumed / abandoned のみ。consumed、abandoned は終端                                                                        | `state-and-scenarios.md`                                 |

## 3. INFERENCE（補助文書に基づく。未承認）

| ID           | 内容                                                                                                                                       | 根拠                                                       | 扱い                                              |
| ------------ | ------------------------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------- | ------------------------------------------------- |
| INF-CART-001 | 変更・加算・削除・統合の各操作は親カートの version / updatedAt を同一トランザクションで更新する。商品詳細からの追加は version を要求しない | `business_rules.md` L139、L144、`FR-CA-013`、`FR-CA-018`   | P-01 承認待ち。cart.md には記載なし               |
| INF-CART-002 | 旧版と異なるversionの操作はCART_VERSION_CHANGEDで拒否される                                                                                | `validation_and_messages.md`、`acceptance_criteria.md` L71 | P-01 承認待ち                                     |
| INF-CART-003 | 明細の表示順は createdAt 昇順、同時刻は itemId 昇順                                                                                        | `business_rules.md` L145、`FR-CA-*`には無し                | P-01 承認待ち                                     |
| INF-CART-004 | 商品詳細からの追加は相対数量、カート画面の変更は絶対数量                                                                                   | `business_rules.md` L138、`FR-CA-017`                      | P-01 承認待ち                                     |
| INF-CART-005 | カートには送料無料までの不足額または達成表示を出す                                                                                         | `FR-CA-010`、`acceptance_criteria.md` L67                  | P-01 承認待ち。送料ルールは別機能の仕様根拠も必要 |
| INF-CART-006 | ゲストIDはLocal Storageに保持し、再訪時にゲストカートを再取得する。再起動後もカート状態を保持する                                          | `FR-CA-008`、`FR-CA-011`、`business_rules.md` L143         | P-01 承認待ち                                     |
| INF-CART-007 | active Cartは User / Guest ごとに1件のみ。複数タブ競合でも1件                                                                              | `FR-CA-014`、`business_rules.md` L259                      | P-01 承認待ち                                     |
| INF-CART-008 | 価格変更時は旧価格と新価格を並べて表示し、確認ボタンを出す                                                                                 | `FR-CA-006`、`ui_specifications.md` §6                     | P-01 承認待ち                                     |
| INF-CART-009 | operator / admin のログインではゲストカートを変更しない                                                                                    | `FR-AU-004`、`FR-AU-011`                                   | P-01 承認待ち                                     |
| INF-CART-010 | 会員の承認（SPEC-CART-008）の承認主体は、チェックアウトを行う active customer と同義                                                       | `business_rules.md` L141（「顧客が承認」）との用語差       | 用語の解釈。P-01 と併せて確認                     |

## 4. UNKNOWN（根拠不足。一般論・類似製品で補完しない）

| ID           | 内容                                                                                                                              | 影響                     | 関連                |
| ------------ | --------------------------------------------------------------------------------------------------------------------------------- | ------------------------ | ------------------- |
| UNK-CART-001 | 「二重実行防止」の観測可能な合否基準（UI無効化か、サーバー側で重複を無視するか、期待する画面状態）                                | TCNの期待結果            | SPEC-CART-012       |
| UNK-CART-002 | `invalid-items` の「修正用のアクション」の具体（数量変更・削除・再確認のどれか、ボタン名、遷移先）                                | TCNの期待結果            | SPEC-CART-013       |
| UNK-CART-003 | 数量変更で上限超過した際の拒否表示（メッセージ・表示位置・live region通知の要否）                                                 | 拒否時の期待UI           | SPEC-CART-002       |
| UNK-CART-004 | 統合時の除外理由の表示形式（表示単位、複数理由が同時に該当した場合の表示順・優先度）                                              | 統合結果の期待結果       | SPEC-CART-005       |
| UNK-CART-005 | 統合対象のゲストカートが空の場合でも abandoned へ遷移するか（SPEC文言は「統合元」の遷移を規定するが、空の場合の扱いは明示なし）   | 統合条件の期待結果       | SPEC-CART-006       |
| UNK-CART-006 | `cart-with-invalid-items` シードの「無効なSKU」が、カート画面での表示・再検証の対象となる範囲（BR-CART-003の列挙に無効SKUが無い） | 再検証と表示             | SPEC-CART-007、G-04 |
| UNK-CART-007 | 「会員の承認」の承認操作（ボタン、確認後の状態、承認の取り消し可否）                                                              | 価格変更ゲートの期待結果 | SPEC-CART-008       |

## 5. 仕様の欠落・矛盾（ギャップ）

| ID                     | 内容                                                                                                                                                                                                                                                                                                           | 扱い                                                                                                                     |
| ---------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| G-01                   | `cart.md` にカートversionと競合（CART_VERSION_CHANGED）の規則がない。一方、AC-CART-002は「カートバージョン」の一致を要求している                                                                                                                                                                               | P-01                                                                                                                     |
| G-02                   | `cart.md` に明細の表示順・商品詳細からの追加契約・送料残額表示がない（補助文書にのみ存在）                                                                                                                                                                                                                     | P-01                                                                                                                     |
| G-03                   | 上限超過の統合処理について、`business_rules.md` L146 は「切り捨てて通知」、`cart.md` BR-CART-002 は「除外して理由を明示」。効果は同じ（超過分を取り込まない）ため矛盾とはしないが、通知方式は未確定                                                                                                            | UNK-CART-004 に統合                                                                                                      |
| G-04                   | BR-CART-003 の再検証対象は4項目（公開・購入権限・価格・在庫）で、シード `cart-with-invalid-items` は「無効なSKU」を含む。無効SKUが再検証の対象かが仕様上不明                                                                                                                                                   | UNK-CART-006                                                                                                             |
| G-05                   | AC-CART-001 は境界（在庫・上限・99）のみを扱い、数量0の削除（SPEC-CART-003）を受入基準に含めていない                                                                                                                                                                                                           | 受入基準の追加はTRで対応（仕様の創作はしない）                                                                           |
| G-06                   | 価格変更の承認者は、cart.md「会員」、business_rules「顧客」と表記が異なる。ゲストはチェックアウト不可のため実質同一と解釈（INF-CART-010）                                                                                                                                                                      | 用語確認                                                                                                                 |
| G-07                   | 会員ランクによる割引・送料の計算規則はカート仕様に含まれない（合計金額の計算規則）                                                                                                                                                                                                                             | 別機能（価格・送料）の仕様根拠で検証。カートでは表示のみ                                                                 |
| G-08                   | 状態遷移は `state-and-scenarios.md` で、チェックアウト側の abandoned / expired とカート側の abandoned が同じ語で書かれている                                                                                                                                                                                   | 別集約として扱う                                                                                                         |
| G-09（2026-11-13追加） | 実装の `INPUT_LIMITS.maxCartQuantity`（`src/application/contracts/common.ts`）が 100 だが、SPEC-CART-001 の上限（99）、`business_rules.md`・`validation_and_messages.md`・`application_contracts.md` の 99 と矛盾する。差分は局所変更で、仕様・正本は変更されていない。実装定数の参照先は `product/src` に無い | 仕様を実装に合わせて変えない（`change-process.md`）。SPEC-CART-001 の 99 を期待値として維持し、P-09 で製品側の意図を確認 |

## 5a. 2026-11-13 変更影響（局所差分）

- 仕様根拠（SPEC-CART-001 / 002、AC-CART-001）は変更なし。SPEC 14件・INFERENCE 10件・UNKNOWN 7件の内容と区分は変わらない。
- 追加: G-09。仕様と実装の不一致（実装側の逸脱の疑い）。不具合としては確定させない（`change-process.md`: 未解決事項は意思決定後に反映）。

## 6. 追跡の要約

- `SPEC` 14件、`INFERENCE` 10件、`UNKNOWN` 7件、ギャップ 8件。
- 現在有効な仕様根拠（SPEC）だけで設計可能な範囲: 数量上限・0削除・統合の除外ロジック・再検証の基本・チェックアウトゲート・ロール利用可否・画面状態の存在。
- 承認待ち（INFERENCE）に依存する範囲: version / 並び順 / 相対加算 / 送料残額 / ゲストID永続 / 単一active / 価格変更の表示。
- 根拠不足（UNKNOWN）により期待結果を確定できない範囲: 二重実行、無効SKU修正導線、拒否表示、除外理由表示、承認操作。
