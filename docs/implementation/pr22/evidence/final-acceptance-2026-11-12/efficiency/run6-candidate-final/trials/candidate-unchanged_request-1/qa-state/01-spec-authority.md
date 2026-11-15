# 01 仕様権威分析（spec-analysis）— カート

- 対象: カート機能（ゲスト／会員のカート操作、数量上限、状態再検証、ログイン時のゲストカート統合）
- 製品: `product/`（ユーザー指定 commit `2a8bcf57`。本環境の`product/`にはgit情報がなく、commit一致は未照合）
- 分類: `SPEC`（現在有効な正式仕様）/ `DECISION` / `INFERENCE`（正式仕様ではない候補）/ `UNKNOWN`（未定義）
- 権威の優先順位: `product/docs/spec/README.md` の「正式な製品動作」に従い、`product-scope.md`・`roles-and-permissions.md`・`state-and-scenarios.md`・`ui-ux-contract.md`・`features/**/*.md` を正本とする。

## 1. 現在有効な仕様根拠（SPEC）

| ID                     | 出典                                                    | 内容（要約）                                                                                                                                                    | 区分                                                       |
| ---------------------- | ------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------- |
| SPEC-CART-SCOPE        | `spec/features/cart.md` 目的・対象範囲                  | ゲスト／会員のカートに対する追加・数量変更・削除・状態再検証・ログイン時統合。注文変換はチェックアウト・注文側（対象外）。                                      | SPEC                                                       |
| BR-CART-001            | `cart.md`                                               | 数量は「在庫数」「購入上限数」「99」の最小値以下。同一SKUは合算判定。上限超過は自動補正せず操作全体を拒否し変更前数量を維持。0指定は明細削除。                  | SPEC                                                       |
| BR-CART-002            | `cart.md`                                               | ログイン時は会員カートを基準にSKU単位で合算。上限超過分、非公開商品、会員ランク不足、無効SKU、在庫0は統合対象外とし理由を明示。統合元ゲストカートは abandoned。 | SPEC                                                       |
| BR-CART-003            | `cart.md`                                               | カート表示時・チェックアウト開始時に公開状態・購入権限・価格・在庫数を再検証。価格変更がある場合は会員の承認までチェックアウト不可。                            | SPEC                                                       |
| UI-CART-001            | `cart.md` UI・振る舞い規約                              | ゲスト／会員のみ利用可。明細に商品情報・画像・現在価格・数量・上限数・問題点・合計・空状態を表示。更新処理中の同一カート変更の二重実行を防止。                  | SPEC                                                       |
| SCR-CART-default       | `cart.md` 主要UI状態                                    | カート明細と数量変更操作。guest/customer。web-desktop・android 必須。                                                                                           | SPEC                                                       |
| SCR-CART-empty         | `cart.md`                                               | 空の旨と商品探索導線。guest/customer。**web-desktop のみ必須**。                                                                                                | SPEC                                                       |
| SCR-CART-invalid-items | `cart.md`                                               | 購入不可理由と修正アクション。guest/customer。**web-desktop のみ必須**。シナリオ `cart-with-invalid-items`。                                                    | SPEC                                                       |
| AC-CART-001            | `cart.md` 受入基準                                      | 在庫数・購入上限数・99の各境界で、上限超過指定時に数量が自動補正されず現在数量が維持されること。                                                                | SPEC                                                       |
| AC-CART-002            | `cart.md`                                               | 統合結果、除外理由、カートバージョン、ゲストカート状態が仕様どおり一致すること。                                                                                | SPEC（「カートバージョン」は下記 C-04 参照）               |
| AC-CART-003            | `cart.md`                                               | 価格変更・在庫切れ・公開停止・会員ランク不足が再検証され、承認または明細修正までチェックアウト不可。                                                            | SPEC                                                       |
| ROLE-CART              | `spec/roles-and-permissions.md`                         | カート: ゲスト〇、顧客（有効）〇、顧客（停止／退会）セッションなし、オペレーター×、管理者×。                                                                    | SPEC                                                       |
| STATE-CART             | `spec/state-and-scenarios.md`                           | Cart: active → consumed / abandoned。consumed・abandoned は終端。再検証の境界は「カート表示、チェックアウト開始、注文確認、注文作成」。                         | SPEC                                                       |
| SCR-LIST               | `spec/screen-catalog.md`                                | `SCREEN-STOREFRONT-CART`（`/cart`）、Guest / Customer。                                                                                                         | SPEC                                                       |
| CROSS-STOREFRONT-003   | `spec/features/storefront.md` BR-STOREFRONT-003         | 在庫切れのバリエーションはカートへ追加する操作を許可しない。AC-STOREFRONT-003 で活性／非活性と理由を確認。                                                      | SPEC（カート追加の入口側。カート機能の追加可否の一部根拠） |
| CROSS-CHECKOUT-002     | `spec/features/checkout-and-payment.md` BR-CHECKOUT-002 | カートバージョンの不一致または価格差異がある場合、注文・決済を作らずカート画面へ戻す。                                                                          | SPEC（カートバージョンの利用側。増分規則は未定義）         |

## 2. 補助・候補情報源（正式仕様ではない）

以下は `spec/README.md` の正式正本一覧に含まれない。現行有効性が未確認のため、**期待結果の根拠に使わず**、矛盾確認と質問生成の入力に限定する。

| 情報源                                                       | 該当                                                                       | 扱い                                      |
| ------------------------------------------------------------ | -------------------------------------------------------------------------- | ----------------------------------------- |
| `product/docs/01_requirements/functional_requirements.md` §3 | FR-CA-001〜018、FR-ST-002（在庫0は追加不可）、FR-AU-002/004、FR-CH-006/020 | INFERENCE候補。現行有効性は未確定（Q-01） |
| `product/docs/03_domain/business_rules.md`（カート節）       | 追加の相対数量、Cart version、表示順、統合の切り捨て、割引の再計算等       | INFERENCE候補（Q-01）                     |
| `product/docs/12_quality/acceptance_criteria.md` §4          | カート統合・バージョン・価格変更の受入観点                                 | INFERENCE候補（Q-01）                     |

## 3. cart.md 内・他正式仕様との矛盾・欠落（C-xx）

| ID   | 内容                                                                                                                                                                                                                                                  | 根拠                                                  | 影響                                         |
| ---- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------- | -------------------------------------------- |
| C-01 | 追加操作の可否ルール（在庫0、非公開、会員ランク不足）が cart.md に無い。在庫切れ追加の禁止は storefront 側（CROSS-STOREFRONT-003）にのみある。                                                                                                        | cart.md / storefront.md / FR-ST-002                   | 追加の受入条件を仕様から確定できない（Q-02） |
| C-02 | ログイン時の統合で、customer 以外（operator / admin）のゲストカートの扱いが cart.md に無い。FR-AU-004 は「変更しない」とする。                                                                                                                        | cart.md BR-002 / FR-AU-004 / roles                    | Q-06                                         |
| C-03 | 明細の表示順（createdAt昇順、itemId昇順）が cart.md に無い。                                                                                                                                                                                          | business_rules.md                                     | Q-13                                         |
| C-04 | AC-CART-002 が「カートバージョン」を検証項目にするが、cart.md はカートバージョンを定義していない。増分規則（追加・変更・削除・価格承認・統合で +1）は FR-CA-013 のみ。checkout は正式にバージョンを使う。                                             | cart.md AC-002 / checkout BR-CHECKOUT-002 / FR-CA-013 | Q-08                                         |
| C-05 | 再読込・ブラウザ再起動後のカート保持、guestId の永続化が cart.md に無い。                                                                                                                                                                             | FR-CA-008 / FR-CA-011                                 | Q-09                                         |
| C-06 | 数量の入力値規則（整数のみ、負数、非数値、空入力）が cart.md に無い。0 の扱いのみ定義。最小数量1は FR-CA-003 のみ。                                                                                                                                   | cart.md BR-001 / FR-CA-003                            | Q-10                                         |
| C-07 | 価格変更の表示（変更前後）、承認の記録方法、承認の状態・UI が cart.md に無い。UI状態表に価格変更の状態もない。                                                                                                                                        | BR-CART-003 / AC-CART-003 / FR-CA-006                 | Q-04                                         |
| C-08 | AC-CART-003 は「会員ランク不足」を再検証対象に含むが、BR-CART-003 の再検証項目（公開状態・購入権限・価格・在庫数）にランクは明記されていない。                                                                                                        | cart.md 内部                                          | Q-05                                         |
| C-09 | 既存明細の数量が再検証時点で新しい上限を超える場合（在庫減少など）の扱いが未定義。BR-CART-001 は操作時の自動補正禁止、BR-CART-003 は表示時の在庫再検証のみ。表示・チェックアウトのブロック表示は AC-CART-003 から読めるが、数量を保つか否かは未定義。 | cart.md BR-001 / BR-003                               | Q-03                                         |
| C-10 | 統合時の上限超過分の扱い（超過数量分の切り捨て）は cart.md と FR-CA-007 / business_rules が一致。ただし除外理由の表示形式・文言・粒度が未定義。                                                                                                       | cart.md BR-002                                        | Q-07（非ブロッカー）                         |
| C-11 | 空状態・invalid-items 状態が Android で必須でない（web-desktop のみ）。意図的か未確認。                                                                                                                                                               | cart.md 主要UI状態                                    | Q-11                                         |
| C-12 | 「二重実行を防止」の観測可能な振る舞い（ボタン無効化、キュー、無視等）が未定義。                                                                                                                                                                      | cart.md UI規約                                        | Q-12                                         |
| C-13 | カート明細に表示する価格が「現在価格」のみで、会員割引の表示の有無・計算単位が未定義。                                                                                                                                                                | cart.md UI規約 / FR-CA-015 / business_rules           | Q-14                                         |
| C-14 | 同一カートへの並行操作（複数タブ・競合）の期待挙動が cart.md に無い。                                                                                                                                                                                 | FR-CA-014                                             | Q-08 に併合                                  |

## 4. 仕様根拠の判定

- 対象範囲の主要な期待挙動（BR-CART-001〜003、AC-CART-001〜003、UI規約、画面状態、ロール、カート状態）は SPEC で解決できる。
- 追加可否、価格変更承認、カートバージョン、表示順、永続化、入力規則、再検証時の数量扱い、ランク再検証、operator/admin のログイン統合は SPEC で解決できない。当該論点に依存する期待結果は UNKNOWN とし、`question-analysis` のブロック中範囲として扱う（02参照）。
- 補助情報源を正式仕様へ昇格させる判断は本成果物では行わない（承認事項 P-01）。
- 実装（`src/application/use-cases/cart-use-cases.ts`、`src/domain/services/cart.ts` 等）は今回読んでいない。仕様根拠としては使用しない。

## 5. 未実施の確認

- 実対象（live UI）の現在の挙動は未観測（`test-target-inspection` 未実施）。期待結果の根拠は仕様のみ。
- `ui-target-analysis` / `ui-target-v1` package は作成していない（UI構造の深い分析は今回の範囲外）。
