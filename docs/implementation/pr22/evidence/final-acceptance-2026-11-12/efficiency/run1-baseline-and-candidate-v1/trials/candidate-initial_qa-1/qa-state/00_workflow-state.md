# ワークフロー状態 — カート QA（テスト分析〜テスト観点・条件設計）

## 要求

- 対象: カート機能（`product/docs/spec/features/cart.md`）。対象製品は `product/`（commit 2a8bcf57）。
- 要求成果物: テスト分析 → テスト要求 → テスト観点・条件（カバレッジ基準・項目）
- 実施範囲外: テストケース設計、カバレッジ分析（coverage-analysis）、反証レビュー（adversarial-review）、テスト実行、E2E選定・実装
- 制約: 製品のコード・仕様書は変更しない。成果物と状態は `qa-state/` に保存。承認が必要な項目は保留として記録。
- 進行モード: `continuous`（既定。gatedの指定はない）

## 実施したSkillと状態

| 順 | Skill                     | 対象 / 実行範囲                         | 成果物                    | 状態                                                             |
| -- | ------------------------- | --------------------------------------- | ------------------------- | ---------------------------------------------------------------- |
| 1  | `spec-analysis`           | カートの仕様根拠（正本 / 補助の区別）   | `01_spec-authority.md`    | 完了（正本根拠は解決済み。補助由来は候補のまま）                 |
| 2  | `question-analysis`       | 矛盾・不明点・仮定                      | `02_question-analysis.md` | 完了（質問10件: ブロッカー（局所）1、要確認3、仮定可能3、提案3） |
| 3  | `test-analysis`           | テスト分析 / `テスト分析`               | `03_test-analysis.md`     | 完了（草案。変更差分なしのため全機能を対象）                     |
| 4  | `test-requirement-design` | テスト要求                              | `04_test-requirements.md` | 部分完了（TR-CART-011 ブロック中）                               |
| 5  | `test-condition-design`   | テスト設計 / 条件・カバレッジ基準・項目 | `05_test-conditions.md`   | 部分完了（保留項目あり、TCN-CART-011 ブロック中）                |
| -  | 承認待ち一覧              | -                                       | `06_pending-approvals.md` | 承認待ち13件、任意確認2件（承認依頼の要点あり）                  |

## ワークフロー全体状態

**部分完了（ブロック中あり）**

- ブロック中: TR-CART-011、TCN-CART-011（ゲストIDの保持。規定が正本外のみ）
- 局所ブロック: Q-CART-001（拒否時の版数）、Q-CART-002（追加の0）、Q-CART-003（空・全件除外のゲストカート）、Q-CART-006（表示順）
- 承認待ち: 13件（`06_pending-approvals.md`）。任意確認: 2件（P-CART-13、P-CART-14）

## 完了条件の確認

- テスト分析・テスト要求・テスト条件の各担当Skillの出力は作成した。ただし各Skillの出力前自己検証の実行経緯は記録しない（指示どおり）。
- 対象範囲内の現在有効な仕様根拠（SPEC-CART-001〜014、DEC-CART-001）は、TRへ接続するか、別テストレベル・対象外として扱いを明示した（`04_test-requirements.md` の閉鎖の確認）。
- 対象内のプロダクトリスク（RISK-CART-001〜008）は、TRへ接続するかブロック中として扱いを明示した。
- 追跡性: SPEC → TR → TCN の対応を `04` に記載。TCN の CI は `05` に記載。

## 未実施・制約（完了扱いにしない事項）

1. **Skill-local runtime（Python）と最終 runtime evidence gate は未実施**。理由: 各Skillの正規化JSON入力をこのセッションで組み立てておらず、本ワークフローの owner verifier も、今回の対象Skill（`test-analysis` / `test-requirement-design` / `test-condition-design`）には登録されていない。そのため、これらのscopeは `unverified_scopes` として完了扱いにできない。成果物は担当Skillのガイダンス・テンプレートに従う手作業の成果物である。
2. **ライブ対象（実アプリ）の観測は未実施**。期待結果の根拠は仕様文書のみ。UI上の表示・版数の観測手段は未確認（`03_test-analysis.md` の観測方法の注記）。
3. **Project Context は未作成**。QA側の案件コンテキスト（承認者、配置方針、情報源優先順位）が無いため、`project-context` は実行していない。承認者は未特定。配置は `qa-state/` のみ。
4. 正本 `roles-and-permissions.md` のカート列は全行の読取が未了（INF-CART-009）。
5. `coverage-analysis` / `test-case-design` / `adversarial-review` は本依頼の範囲外のため未実施。

## 次のアクション（承認後）

- 承認: `06_pending-approvals.md` の P-CART-07（最優先）→ P-CART-08/09 → P-CART-01/03/05/06/05b → P-CART-11/12 の順。
- 承認を得た後: `test-condition-design` の保留解除、必要に応じて `spec-analysis`（正本化）から再開。
- 次工程（依頼時）: `test-case-design` → `coverage-analysis` → `adversarial-review`。
