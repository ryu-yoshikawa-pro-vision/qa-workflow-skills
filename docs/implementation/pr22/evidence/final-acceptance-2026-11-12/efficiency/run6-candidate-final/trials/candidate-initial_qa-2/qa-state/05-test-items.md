# テストアイテム候補: カート機能

ITEM IDは候補（安定ID未発行）。実装の関数名・ファイル名は参照情報として記載する。

| ITEM ID（候補） | テスト対象                                       | 種別                 | 参照（観測用）                                                  | 関連TR                        |
| --------------- | ------------------------------------------------ | -------------------- | --------------------------------------------------------------- | ----------------------------- |
| ITEM-CART-01    | 数量上限の算出（最小値・99）                     | ドメイン関数         | `domain/services/cart.ts` `maximumCartQuantity`                 | TR-01                         |
| ITEM-CART-02    | 数量の追加・上限判定                             | ドメイン関数         | `addCartQuantity`                                               | TR-01, 02, 24                 |
| ITEM-CART-03    | ログイン時統合の数量計算                         | ドメイン関数         | `mergeCartQuantity`                                             | TR-08, 09                     |
| ITEM-CART-10    | カートの取得（作成を含む）                       | ユースケース         | `cart-use-cases.ts` `getCart`                                   | TR-15, 16                     |
| ITEM-CART-11    | 商品の追加                                       | ユースケース         | `addItem`                                                       | TR-01, 02, 11, 12, 23         |
| ITEM-CART-12    | 数量の変更（0は削除）                            | ユースケース         | `updateQuantity`                                                | TR-01〜03, 11                 |
| ITEM-CART-13    | 明細の削除                                       | ユースケース         | `removeItem`                                                    | TR-03, 11                     |
| ITEM-CART-14    | 価格変更の承認                                   | ユースケース         | `acceptPriceChanges`                                            | TR-06                         |
| ITEM-CART-20    | 権限の解決（ゲスト・customer・その他）           | 権限                 | `resolveOwner`                                                  | TR-15, 16                     |
| ITEM-CART-30    | ログイン時のゲストカート統合                     | 横断（認証＋カート） | ログイン・統合処理（AC §2）                                     | TR-08, 09, 10, 11             |
| ITEM-CART-31    | 単価・割引・合計の算出                           | 横断（カート＋価格） | AC §4（`unitEffectivePriceAtAdd`）                              | TR-12, 14                     |
| ITEM-CART-40    | 注文作成時の価格再照合（チェックアウトへの入口） | 横断（カート＋注文） | AC §5                                                           | TR-13                         |
| ITEM-CART-50    | カート画面（明細・数量・問題点・合計・空状態）   | 画面                 | SCREEN-STOREFRONT-CART（`default` / `empty` / `invalid-items`） | TR-02, 04, 07, 19, 20, 21, 22 |
| ITEM-CART-51    | カート画面の問題点の修正・削除操作               | 画面操作             | SCREEN-STOREFRONT-CART `invalid-items`                          | TR-07                         |
| ITEM-CART-52    | カート画面の二重実行防止                         | 画面操作             | SPEC-CART-12                                                    | TR-17                         |
| ITEM-CART-60    | カートの永続化（Repository）                     | 永続化               | Dexieカート Repository                                          | TR-10, 11                     |

## 境界（この機能のテスト対象外）

- 注文作成・決済・在庫の確定（チェックアウト機能）
- 商品の公開・在庫の管理（商品管理機能）。カートは状態を読み取るのみ。
- 商品詳細画面の追加ボタンの表示（商品詳細機能）。カートからは結合で確認。

## 整理上の注意

- ITEM-CART-30 と ITEM-CART-31 は複数機能にまたがる。安定IDとして確定する前に、所有機能（カート / 認証 / 価格）を決める必要がある（feature-analysis・test-item-analysis の確認事項）。
