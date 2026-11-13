# QAワークフロー状態: カート

- 要求: カート機能（`product/docs/spec/features/cart.md`）のQA。範囲はテスト分析からテスト観点（条件）設計まで
- 対象 / 実行範囲: `SCREEN-STOREFRONT-CART` / カート（BR-CART-001〜003、AC-CART-001〜003）
- 製品入力revision: commit `2a8bcf57`（ユーザー指定。本セッションではgit照合していない）。仕様改版 rev2（`product-change-spec.diff`）を反映済み。改版後のcommit IDは未提供
- 改版 rev2: `product/docs/spec/features/cart.md` BR-CART-001 見出しの上限値 99 → 50（差分はこの1行のみ）
- 進行モード: continuous（既定）
- 製品・仕様書: 本QAでは変更なし

## 1. Skill別の状態

| 順 | Skill                     | 対象 / 実行範囲                  | 状態                                  | 成果物                    | 備考                                                                                                    |
| -- | ------------------------- | -------------------------------- | ------------------------------------- | ------------------------- | ------------------------------------------------------------------------------------------------------- |
| 1  | `spec-analysis`           | カート仕様                       | 完了（草案、手作業）。rev2 反映済み   | `01-spec-authority.md`    | SPEC 14 / INF 10 / UNK 8 / ギャップ 10。runtime・helper未実行                                           |
| 2  | `question-analysis`       | 仕様の不明点                     | 分類済み・回答待ち（rev2 で追加）     | `02-pending-items.md`     | 保留 P-01〜P-10 を記録。P-09・P-10 は rev2 で追加、P-01 の範囲を拡張。解消は未実施                      |
| 3  | `test-analysis`           | テスト分析                       | 完了（草案、手作業）。rev2 反映済み   | `03-test-analysis.md`     | リスク10件（RISK-09・10 を rev2 で追加）、重点、技法、テストレベル                                      |
| 4  | `test-requirement-design` | テスト要求                       | 完了（部分・保留あり）。rev2 反映済み | `04-test-requirements.md` | 有効TR 15、保留TR 10（TR-P10 を rev2 で追加）                                                           |
| 5  | `test-condition-design`   | テスト観点・条件・カバレッジ項目 | 完了（部分・保留あり）。rev2 反映済み | `05-test-conditions.md`   | 有効TCN 14、保留TCN 10（TCN-P10 を rev2 で追加）、期待結果の一部保留                                    |
| –  | `test-case-design`        | 詳細TC                           | 範囲外（未実施）                      | –                         | 依頼範囲は観点・条件設計まで                                                                            |
| –  | `coverage-analysis`       | 閉鎖性・カバレッジ判定           | 範囲外（未実施）                      | –                         | 同上                                                                                                    |
| –  | `adversarial-review`      | 独立レビュー                     | 範囲外（未実施）                      | –                         | 同上                                                                                                    |
| –  | `project-context`         | 案件コンテキスト                 | 未作成                                | –                         | `product/docs/PROJECT_CONTEXT.md` は製品リポジトリの文書で、QA案件のProject Contextとしては扱っていない |

## 2. 再利用 / 再実行

- 初回作成（rev1）: 既存の qa-state・QA成果物は存在しなかったため、すべて新規作成。再利用はなし。
- 改版 rev2（上限値 99 → 50）:
  - 意味が変わった上流: SPEC-CART-001（上限値）。L = min(在庫数, 購入上限数, 50)。
  - 影響した下流を手作業で更新（再実行ではなく内容の書き換え）: `01`（SPEC-001、G-09・G-10、UNK-CART-008）、`02`（P-01 拡張、P-09・P-10 追加）、`03`（境界定義、RISK-09・10、重点、残存リスク）、`04`（TR-001・TR-004 の文言、TR-P10 追加）、`05`（L定義、TCN-001・TCN-004 の境界、TCN-P10 追加）。
  - 再利用（影響なし）: SPEC-CART-002〜014、統合の除外規則、再検証、ロール、画面状態、TCN-002・003・005〜014 の規則。
  - 機械的な再検証（runtime・owner verifier）は未実行。上記は手作業の書き換えであり、`verify_runtime_evidence` の対象ではない。
- 中断・再開: 本改版の作業は中断なしで完了。

## 3. 保留（承認・回答待ち）

詳細は `02-pending-items.md`。

- P-01（局所ブロッカー）: 仕様の権威範囲（補助文書のカート規則を仕様根拠として扱ってよいか）
- P-02〜P-07（要確認）: 二重実行の合否、無効SKU、拒否表示、除外理由表示、空ゲストカート統合、価格変更の承認
- P-08（要確認）: テストレベル割当（統合元 abandoned・単一activeをApplication Integrationで検証）
- P-09（要確認、rev2 追加）: AC-CART-001 本文の「99」と BR-CART-001 の「50」の不一致。仮定として上限50を採用
- P-10（要確認、rev2 追加）: 改版後に既存明細が新上限を超える場合の表示・再検証・チェックアウトの扱い（UNK-CART-008）
- 補助文書の上限値（99）の不一致は P-01 の範囲に含める（`01-spec-authority.md` G-10）

## 4. 機械検証（runtime / gate）の状態

- `verify_runtime_evidence` および各Skillのruntime・owner verifierは未実行。
- 理由: 各runtimeに渡す正規化入力（normalized input）をこのセッションで構築していない。また、シェル利用は `python3 <絶対path>` に限られるため、git照合も行っていない。
- 結果として、本ワークフローの成果物は「手作業草案」であり、qa-workflowの機械完了条件（`can_complete`相当）は満たしていない。

## 5. 再開手順

1. P-01 の承認を得る → `spec-analysis` で INF を SPEC へ昇格する、または対象外を明記する
2. P-02〜P-07、P-09、P-10 の回答を `question-analysis` で分類 → `spec-analysis` で UNK（UNK-CART-008 を含む）を更新
3. 保留TRを `test-requirement-design` で追加（TR-P01〜P09）→ `test-condition-design` で TCN-P を展開
4. 回答後、影響する TR・TCN だけを `要再検証` として再実行
5. 範囲を広げる場合: `test-case-design` → `coverage-analysis` → `adversarial-review`
