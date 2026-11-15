# ワークフロー状態: カート（SCREEN-STOREFRONT-CART）

- ワークフロー全体状態: **部分完了（ブロック中あり）**
- 開始Skill: spec-analysis（前回の実行、`01-spec-analysis.md`）
- 開始対象 / 実行範囲: カート（features/cart.md）/ テスト分析〜テスト観点（条件）設計
- 最終Skill: test-condition-design
- 最終対象 / 実行範囲: テスト観点・条件 / カバレッジ項目（TCN-001〜028、カバレッジ項目53）
- 入力revision: 製品commit `2a8bcf57` は **照合不可**（`product/` に `.git` がない。利用者申告のみ）。仕様書の版も未取得。
- 開始時の確認: 中断からの再開（前回 spec-analysis 完了後、question-analysis 以降が未保存のまま中断）。spec-analysis は保存済みのため再利用。`features/cart.md` は再読込して内容（BR-CART-001〜003、AC-CART-001〜003、画面状態3種）が `01` と一致することを確認。

## 中断・再開の記録

| 工程                                   | 状態                   | 成果物                        |
| -------------------------------------- | ---------------------- | ----------------------------- |
| spec-analysis                          | 完了（前回）           | `01-spec-analysis.md`         |
| question-analysis                      | 完了（今回）           | `02-question-analysis.md`     |
| test-analysis                          | 完了（今回）           | `03-test-analysis.md`         |
| test-requirement-design                | 完了（今回）           | `04-test-requirements.md`     |
| test-condition-design                  | 完了（今回）           | `05-test-condition-design.md` |
| test-case-design                       | 対象外（今回の範囲外） | —                             |
| coverage-analysis / adversarial-review | 対象外（今回の範囲外） | —                             |

前回の中断点: spec-analysis の後。`qa-state/` には question-analysis 以降の成果物がなかった。今回、`01` のUNK/Q参照を分類して再開した。

## 保留（承認・回答が必要）

回答を得るまで、該当する条件の期待結果は保留のままにする。承認や回答を求める事項はこの一覧で管理する。

| ID        | 内容                                                                                | 種別               | 止まる範囲            | 再開先             |
| --------- | ----------------------------------------------------------------------------------- | ------------------ | --------------------- | ------------------ |
| 承認 A-01 | 会員カート不在時は新規作成してから統合する（INF-001）                               | 仮定の承認         | TCN-010               | question-analysis  |
| 承認 A-02 | 在庫減少で数量超過の明細は自動補正せず問題点とし、修正・削除まで開始不可（INF-002） | 仮定の承認         | TCN-018, TCN-019      | question-analysis  |
| Q-001     | 「価格変更」の定義（ランク変更による割引率変化を含むか）                            | 回答（ブロッカー） | TCN-015               | spec-analysis      |
| Q-002     | カートバージョンの増分規則と競合時の振る舞い                                        | 回答（ブロッカー） | TCN-025, TR-014       | spec-analysis      |
| Q-003     | features以外の文書の詳細規則を正式採用するか（INF-003〜008の採否）                  | 回答               | INF系の条件           | spec-analysis      |
| Q-004     | モバイルWebを対象に含めるか                                                         | 回答               | TCN-026-CI02          | spec-analysis      |
| Q-005     | 合計金額の算出範囲と式                                                              | 回答（ブロッカー） | TCN-023-CI02          | spec-analysis      |
| Q-006     | 価格変更の承認操作と画面表現                                                        | 回答（ブロッカー） | TCN-015-CI02          | ui-target-analysis |
| Q-007     | 会員カート不在時の統合先                                                            | 回答（A-01と連動） | TCN-010               | question-analysis  |
| Q-008     | 在庫減少時の問題点表示（A-02と連動）                                                | 回答（A-02と連動） | TCN-018-CI02, TCN-019 | question-analysis  |
| Q-009     | 統合失敗時のゲストカート                                                            | 回答（ブロッカー） | TCN-009               | spec-analysis      |
| Q-010     | 運用者・管理者ログイン時のゲストカート                                              | 回答               | TCN-011               | question-analysis  |
| Q-011     | 購入権限の変化の一覧と反映時点                                                      | 回答               | TCN-027-CI02          | spec-analysis      |
| Q-012     | 空のゲストカートの統合（新規）                                                      | 回答               | TCN-005-CI05          | spec-analysis      |
| Q-013     | ランク不足商品の追加可否（新規）                                                    | 回答               | TCN-013-CI02          | spec-analysis      |

ブロッカーの優先順: Q-001、Q-002、Q-005、Q-006、Q-009。他は局所的。

## 作業の制約（実行環境）

- 製品コード・仕様書は変更していない（読取のみ）。
- Bash は `python3 <絶対path>` の形だけ許可されている。今回は `ls`・`find` 系の直接実行が拒否されたため、ファイル探索は Glob / Read で実施した。
- 決定論的runtime（`scripts/*.py`）は実行していない。scope 0（UI target package の対象scopeが無い）であり、`qa-workflow` の契約上 runtime dispatch は不要。ただし、各Skillの「最終 runtime evidence gate」は未実行のため、成果物は**判断ベースの記述**として扱う。機械検証済みではない。
- `workflow_ref`（UUID）は未発行。state root 未設定のため、永続 state provider は使っていない。

## 次の作業（承認・回答後）

1. A-01 / A-02 と Q-001〜Q-013 の回答を取得し、`02-question-analysis.md` を更新する。
2. 回答に応じて、保留の条件を `05-test-condition-design.md` で確定に変更する。
3. 次工程: `test-case-design`（詳細TC化。確定済みの条件から始める）、`coverage-analysis`（TR → 条件 → TC の追跡確認）。今回の範囲外のため未着手。
