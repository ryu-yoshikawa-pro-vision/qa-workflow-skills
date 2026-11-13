# ワークフロー状態 — カート QA（テスト分析〜テスト観点・条件設計）

## 要求

- 対象: カート機能（`product/docs/spec/features/cart.md`）。対象製品は `product/`（commit 2a8bcf57）。
- 要求成果物: テスト分析 → テスト要求 → テスト観点・条件（カバレッジ基準・項目）。改版（`product-change-spec.diff`）に伴う変更影響の反映と、QAの最新化。
- 実施範囲外: テストケース設計、カバレッジ分析（coverage-analysis）、反証レビュー（adversarial-review）、テスト実行、E2E選定・実装
- 制約: 製品のコード・仕様書は変更しない。成果物と状態は `qa-state/` に保存。承認が必要な項目は保留として記録。
- 進行モード: `continuous`（既定。gatedの指定はない）

## 改版の反映（今回）

- 差分: `product-change-spec.diff`。`cart.md` BR-CART-001 の見出しの上限値「99」→「50」のみ（本文・AC・他の正本は差分に含まれない）。
- 最も早く変わった成果物: `01_spec-authority.md`（SPEC-CART-001、INF-CART-001）→ `02_question-analysis.md`（改版起因の矛盾を追加）→ `03`〜`05`（影響箇所のみ更新）→ `06`（承認項目を更新・追加）。
- 影響判断:
  - 変わったもの: SPEC-CART-001 の値、INF-CART-001 の値、TR-CART-001 の文言、TCN-CART-001（境界の具体値 K）、TCN-CART-003 CI03/CI05 の注記、TCN-CART-005 の上限参照、RISK-CART-001 の記述。
  - 変わらないもの: 上限超過時の規則（操作全体拒否・数量非補正・変更前数量維持）、リスクレベル（RISK-CART-001 は高のまま）、SPEC-CART-002〜014、DEC-CART-001、TR-CART-002〜011、TCN-CART-002/004/006〜011。
  - 改版起因の新規矛盾: AC-CART-001（本文L74）が「99の各境界値」のまま → Q-CART-011（ブロッカー・局所）。補助文書（SUP-1 L137「上限値99」、SUP-3 L44「1〜99」）が旧値のまま → Q-CART-012（要確認・局所）。
- 製品実装の観測（仕様Authorityではない・未検証）: `product/src/domain/services/cart.ts` L3 `CART_QUANTITY_LIMIT = 99`。改版後の50と一致しない可能性がある。製品は変更していない。`test-target-inspection` での実対象確認と、確認後の `defect-management` への引き継ぎが必要。

## 実施したSkillと状態

| 順 | Skill                     | 対象 / 実行範囲                                 | 成果物                    | 状態                                                                                              |
| -- | ------------------------- | ----------------------------------------------- | ------------------------- | ------------------------------------------------------------------------------------------------- |
| 1  | `spec-analysis`           | カートの仕様根拠（正本 / 補助の区別）・改版反映 | `01_spec-authority.md`    | 改版反映済み（上限値は改版の50。AC-CART-001 との矛盾は未解決 → Q-CART-011）                       |
| 2  | `question-analysis`       | 矛盾・不明点・仮定（改版起因の追加）            | `02_question-analysis.md` | 改版反映済み（質問12件: ブロッカー（局所）2、要確認4、仮定可能3、提案3）                          |
| 3  | `test-analysis`           | テスト分析 / `テスト分析`                       | `03_test-analysis.md`     | 改版反映済み（リスクレベルは不変。記述と変更影響マップを更新）                                    |
| 4  | `test-requirement-design` | テスト要求                                      | `04_test-requirements.md` | 改版反映済み（TR-CART-001 の文言のみ。TR-CART-011 ブロック中は継続）                              |
| 5  | `test-condition-design`   | テスト設計 / 条件・カバレッジ基準・項目         | `05_test-conditions.md`   | 改版反映済み（TCN-CART-001 の境界値を K で表記。K の具体値は保留）。TCN-CART-011 ブロック中は継続 |
| -  | 承認待ち一覧              | -                                               | `06_pending-approvals.md` | 承認待ち15件（新規: P-CART-15 最優先、P-CART-16 任意）、任意確認2件                               |

## ワークフロー全体状態

**部分完了（ブロック中あり）**

- ブロック中（改版前から継続）: TR-CART-011、TCN-CART-011（ゲストIDの保持。規定が正本外のみ）
- 局所ブロック（改版起因・新規）: Q-CART-011（上限値 K の具体値。BR-CART-001 の50 と AC-CART-001 の99 が矛盾）。影響は境界の具体値（TCN-CART-001、TCN-CART-003 CI03、TCN-CART-005の上限）のみで、上限超過時の規則は継続。Q-CART-012（補助文書の99。拒否時の文言のみ保留）
- 局所ブロック（既存）: Q-CART-001（拒否時の版数）、Q-CART-002（追加の0）、Q-CART-003（空・全件除外のゲストカート）、Q-CART-006（表示順）
- 承認待ち: 15件（`06_pending-approvals.md`）。任意確認: 2件（P-CART-13、P-CART-14）。任意（改版起因）: P-CART-16

## 完了条件の確認

- テスト分析・テスト要求・テスト条件の各担当Skillの出力は、改版の影響箇所を更新した。ただし各Skillの出力前自己検証の実行経緯は記録しない（指示どおり）。
- 対象範囲内の現在有効な仕様根拠（SPEC-CART-001〜014、DEC-CART-001）は、TRへ接続するか、別テストレベル・対象外として扱いを明示した（`04_test-requirements.md` の閉鎖の確認）。SPEC-CART-001 の上限値は改版値を反映し、具体値は Q-CART-011 で保留。
- 対象内のプロダクトリスク（RISK-CART-001〜008）は、TRへ接続するかブロック中として扱いを明示した。
- 追跡性: SPEC → TR → TCN の対応を `04` に記載。TCN の CI は `05` に記載。

## 未実施・制約（完了扱いにしない事項）

1. **Skill-local runtime（Python）と最終 runtime evidence gate は未実施**。理由: 各Skillの正規化JSON入力をこのセッションで組み立てておらず、本ワークフローの owner verifier も、今回の対象Skill（`test-analysis` / `test-requirement-design` / `test-condition-design`）には登録されていない。そのため、これらのscopeは `unverified_scopes` として完了扱いにできない。成果物は担当Skillのガイダンス・テンプレートに従う手作業の成果物である。
2. **ライブ対象（実アプリ）の観測は未実施**。期待結果の根拠は仕様文書のみ。改版後の上限値が実アプリに反映されているかは未確認（上記の実装定数の観測を参照）。
3. **Project Context は未作成**。QA側の案件コンテキスト（承認者、配置方針、情報源優先順位）が無いため、`project-context` は実行していない。承認者は未特定。配置は `qa-state/` のみ。
4. 正本 `roles-and-permissions.md` のカート列は全行の読取が未了（INF-CART-009）。
5. `coverage-analysis` / `test-case-design` / `adversarial-review` は本依頼の範囲外のため未実施。TCN-CART-001 等が改版で変わったため、これらを実行する場合は更新後の `05` を入力にする必要がある。

## 次のアクション（承認後）

- 承認: `06_pending-approvals.md` の P-CART-15（最優先。上限値 K の確定）→ P-CART-07 → P-CART-08/09 → P-CART-01/03/05/06/05b → P-CART-11/12 の順。
- P-CART-15 の回答後: `spec-analysis` で上限値を正本化し、`test-condition-design` で TCN-CART-001（CI01〜CI06 の具体値）、TCN-CART-003 CI03、TCN-CART-005 を確定する。
- 実装の上限値（`CART_QUANTITY_LIMIT = 99`）の実対象確認: `test-target-inspection`。不一致が確認されたら `defect-management`。
- 承認を得た後: `test-condition-design` の保留解除、必要に応じて `spec-analysis`（正本化）から再開。
- 次工程（依頼時）: `test-case-design` → `coverage-analysis` → `adversarial-review`。
