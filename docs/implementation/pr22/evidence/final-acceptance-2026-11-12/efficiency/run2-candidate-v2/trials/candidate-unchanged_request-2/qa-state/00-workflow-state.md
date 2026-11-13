# QAワークフロー状態: カート

- 要求: カート機能（`product/docs/spec/features/cart.md`）のQA。範囲はテスト分析からテスト観点（条件）設計まで
- 対象 / 実行範囲: `SCREEN-STOREFRONT-CART` / カート（BR-CART-001〜003、AC-CART-001〜003）
- 製品入力revision: commit `2a8bcf57`（ユーザー指定。本セッションではgit照合していない）
- 進行モード: continuous（既定）
- 製品・仕様書: 変更なし

## 1. Skill別の状態

| 順 | Skill                     | 対象 / 実行範囲                  | 状態                   | 成果物                    | 備考                                                                                                    |
| -- | ------------------------- | -------------------------------- | ---------------------- | ------------------------- | ------------------------------------------------------------------------------------------------------- |
| 1  | `spec-analysis`           | カート仕様                       | 完了（草案、手作業）   | `01-spec-authority.md`    | SPEC 14 / INF 10 / UNK 7 / ギャップ 8。runtime・helper未実行                                            |
| 2  | `question-analysis`       | 仕様の不明点                     | 分類済み・回答待ち     | `02-pending-items.md`     | 保留 P-01〜P-08 を記録。解消は未実施                                                                    |
| 3  | `test-analysis`           | テスト分析                       | 完了（草案、手作業）   | `03-test-analysis.md`     | リスク8件、重点、技法、テストレベル                                                                     |
| 4  | `test-requirement-design` | テスト要求                       | 完了（部分・保留あり） | `04-test-requirements.md` | 有効TR 16、保留TR 10                                                                                    |
| 5  | `test-condition-design`   | テスト観点・条件・カバレッジ項目 | 完了（部分・保留あり） | `05-test-conditions.md`   | 有効TCN 15、保留TCN 10、期待結果の一部保留                                                              |
| –  | `test-case-design`        | 詳細TC                           | 範囲外（未実施）       | –                         | 依頼範囲は観点・条件設計まで                                                                            |
| –  | `coverage-analysis`       | 閉鎖性・カバレッジ判定           | 範囲外（未実施）       | –                         | 同上                                                                                                    |
| –  | `adversarial-review`      | 独立レビュー                     | 範囲外（未実施）       | –                         | 同上                                                                                                    |
| –  | `project-context`         | 案件コンテキスト                 | 未作成                 | –                         | `product/docs/PROJECT_CONTEXT.md` は製品リポジトリの文書で、QA案件のProject Contextとしては扱っていない |

## 2. 再利用 / 再実行

- 既存の qa-state は前回セッションの手作業草案。今回、`product/docs/spec/features/cart.md`・`state-and-scenarios.md`・`business_rules.md` §3・`functional_requirements.md` §3・`acceptance_criteria.md` §4・`test_strategy.md`・FR-TC-008 を再照合し、草案の引用先が現存することを確認した。
- 再照合で見つかった修正（今回セッション）: TCN-008 の期待結果を「変化」から「問題の有無」へ修正。終端状態の変更不可を TR-016 / TCN-015 として追加。表示時の会員割引再計算を TR-P10 / TCN-P10 として保留（P-01）へ追加。
- 製品の git 履歴は workspace 内に `product/.git` が存在せず、commit `2a8bcf57` は照合できていない（ユーザー指定のまま）。
- 上流（spec）に変更がなかったため、spec-analysis は再実行していない。
- 上流（spec）の変更時は、影響する下流（TR → TCN）だけを再検証する。

## 3. 保留（承認・回答待ち）

詳細は `02-pending-items.md`。

- P-01（局所ブロッカー）: 仕様の権威範囲（補助文書のカート規則を仕様根拠として扱ってよいか）。対象は TR-P01〜P07・P09・P10
- P-02〜P-07（要確認）: 二重実行の合否、無効SKU、拒否表示、除外理由表示、空ゲストカート統合、価格変更の承認
- P-08（要確認）: テストレベル割当（統合元 abandoned・単一activeをApplication Integrationで検証）

## 4. 機械検証（runtime / gate）の状態

- `verify_runtime_evidence` および各Skillのruntime・owner verifierは未実行。
- 理由: 各runtimeに渡す正規化入力（normalized input）をこのセッションで構築していない。また、シェル利用は `python3 <絶対path>` に限られるため、git照合も行っていない。
- 結果として、本ワークフローの成果物は「手作業草案」であり、qa-workflowの機械完了条件（`can_complete`相当）は満たしていない。

## 5. 再開手順

1. P-01 の承認を得る → `spec-analysis` で INF を SPEC へ昇格する、または対象外を明記する
2. P-02〜P-07 の回答を `question-analysis` で分類 → `spec-analysis` で UNK を更新
3. 保留TRを `test-requirement-design` で追加（TR-P01〜P10）→ `test-condition-design` で TCN-P を展開（TR-016 / TCN-015 は有効項目として既に追加済み）
4. 回答後、影響する TR・TCN だけを `要再検証` として再実行
5. 範囲を広げる場合: `test-case-design` → `coverage-analysis` → `adversarial-review`
