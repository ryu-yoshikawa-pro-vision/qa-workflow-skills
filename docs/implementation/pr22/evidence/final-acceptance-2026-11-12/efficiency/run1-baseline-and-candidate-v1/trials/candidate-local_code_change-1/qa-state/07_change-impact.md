# 07 変更影響（product-change-code.diff）— カート

記録日: 2026-11-13。対象製品: `product/`。製品コード・仕様書は変更していない。

## 1. 変更内容

`product-change-code.diff`（1ファイル・1行）:

- ファイル: `product/src/application/contracts/common.ts`（diff上の行97）
- 変更: `INPUT_LIMITS.maxCartQuantity` を `99` → `100`

## 2. 静的確認の結果

| 確認                     | 結果                                                                                                                  | 根拠                                                                                                                                                                                                                               |
| ------------------------ | --------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `maxCartQuantity` の参照 | src内では定義行（common.ts:97）のみ。キー名での参照はない                                                             | `src` 全体のキー名検索（静的、オブジェクト全体の展開による間接参照は未追跡）                                                                                                                                                       |
| カートの実効上限の判定   | 変更なし。`CART_QUANTITY_LIMIT = 99` を `maximumCartQuantity` が `min(在庫数, 購入上限数, 99)` として返す             | `src/domain/services/cart.ts:3, 11`                                                                                                                                                                                                |
| 上限判定の利用箇所       | Dexie / SQLite の cart・checkout repository が `maximumCartQuantity` / `addCartQuantity` / `mergeCartQuantity` を使用 | `src/infrastructure/database/dexie/cart-checkout-repositories.ts:19`、`src/infrastructure/database/sqlite/native-customer-application-repositories.ts:80`、`src/infrastructure/database/sqlite/native-customer-repositories.ts:25` |
| 正本の上限値             | 99（「在庫数」「購入上限数」「99」の最小値）                                                                          | `product/docs/spec/features/cart.md` BR-CART-001（L9, L11）、AC-CART-001（L74）                                                                                                                                                    |
| 補助文書の上限値         | 99                                                                                                                    | `product/docs/04_data/application_contracts.md:101`                                                                                                                                                                                |

判定: **変更による実効上限の変化は静的には確認されない（実効上限は99のまま）**。一方で、同じ上限を表す定数が `99`（ドメイン・仕様・補助文書）と `100`（契約定数）に分かれた。

## 3. 影響の判断

- **仕様（SPEC）の意味**: 変化なし。SPEC-CART-001 は99のまま。製品コードは仕様Authorityではないため、上流の仕様根拠を更新しない。
- **期待結果**: 変化なし。TCN-CART-001 CI03（上限99、合算数量98 / 99 / 100）の期待は「100は拒否、数量維持」のまま。
- **テスト要求・テスト条件の構造**: 変化なし。TR-CART-001 / 003、TCN-CART-001 / 003 は再設計不要。
- **観測の必要性（新規）**: 契約定数が100になったため、実アプリで数量100の追加・変更が拒否されることを確認対象に加える（TCN-CART-001 CI03）。現時点では未観測。
- **リスク**: RISK-CART-001（上限誤算）の信頼度に「定数の二重定義」を加えて記録する。レベル（高）は変えない。
- **将来の懸念**: `INPUT_LIMITS.maxCartQuantity` が入力制御やUIのバリデーションへ接続された場合、上限が100になり SPEC-CART-001 に反する。

## 4. 製品側の未解決事項

製品の購入上限が99か100かは、仕様と実装のどちらが正しいかの判断を要する。QAは判断しない。

- 正本（SPEC-CART-001）を変えないなら、製品側で `maxCartQuantity` を99へ戻す、または参照を `CART_QUANTITY_LIMIT` に一本化する。
- 正本を100へ変えるなら、`product/docs/spec/change-process.md` の手続きで変更し、`spec-analysis` から再開して影響下流（TCN-CART-001 CI03、TR-CART-001 / 003、補助文書）を要再検証にする。

## 5. QA側で行った更新

| 成果物                    | 更新                                                                        |
| ------------------------- | --------------------------------------------------------------------------- |
| `00_workflow-state.md`    | 変更差分の反映を記録。承認項目 P-CART-15 を追加                             |
| `02_question-analysis.md` | Q-CART-011（上限値の不一致、局所・要確認）を追加                            |
| `03_test-analysis.md`     | 変更/影響マップに変更差分の行を追加。RISK-CART-001 の信頼度に二重定義を注記 |
| `04_test-requirements.md` | TR-CART-001 / 003 に観測対象の注記。要求内容は不変                          |
| `05_test-conditions.md`   | TCN-CART-001 に変更差分による観測注記。CI03の期待は不変                     |
| `06_pending-approvals.md` | P-CART-15（製品の購入上限値の正本判断）を追加                               |

## 6. 未実施（完了扱いにしない事項）

- 実アプリでの数量100の追加・変更の観測（TCN-CART-001 CI03）。未実施。
- 実行（test-execution）による確認。未実施。実装が100を受理した場合は、欠陥候補として `defect-management` へ引き継ぐ。
- 製品側の回答（P-CART-15）。未受領。

## 7. 補足

- 本変更は仕様の意味を変えないため、上流成果物の再生成や下流の `要再検証` 化は行っていない（`qa-workflow` の上流変更の伝播に該当しない）。
- 製品のドキュメント `product/docs/04_data/application_contracts.md:101` の99は、契約定数（100）と食い違っている。製品側の修正対象。
