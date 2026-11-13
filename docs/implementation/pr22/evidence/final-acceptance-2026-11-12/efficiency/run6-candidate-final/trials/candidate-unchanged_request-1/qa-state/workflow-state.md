# ワークフロー状態 — カート機能 QA（テスト分析〜テスト観点・条件設計）

## 基本情報

- 依頼: カート機能（`product/docs/spec/features/cart.md`）のQA。範囲は「テスト分析からテスト観点（条件）設計まで」。
- 対象製品: `product/`（ユーザー指定 commit `2a8bcf57`。本環境の`product/`にはgit情報がなく、commit一致は**未照合**）。
- 進行モード: `continuous`（既定）。
- 製品コード・仕様書: 変更していない。
- 保存先: 本ディレクトリ `qa-state/`。

## 工程と状態

| 順 | 工程（担当Skill）                                             | 対象 / 実行範囲                                    | 状態                                                       | 成果物                    |
| -- | ------------------------------------------------------------- | -------------------------------------------------- | ---------------------------------------------------------- | ------------------------- |
| 1  | `spec-analysis`                                               | 対象範囲の現在有効な仕様Authority                  | 完了（ブロック中事項あり）                                 | `01-spec-authority.md`    |
| 2  | `question-analysis`                                           | 不明点・矛盾の分類                                 | 完了（ブロッカー7件・要確認6件・提案1件）                  | `02-question-analysis.md` |
| 3  | 承認保留の記録                                                | 承認が必要な判断                                   | 記録済み（12件、全件未承認）                               | `03-pending-approvals.md` |
| 4  | `test-analysis`                                               | テスト分析（プロダクトリスク・重点・レベル・技法） | 完了                                                       | `04-test-analysis.md`     |
| 5  | `test-requirement-design`                                     | テスト要求（TR）                                   | 完了（TR 27件: 有効15・一部ブロック中1・ブロック中11）     | `05-test-requirements.md` |
| 6  | `test-condition-design`                                       | テスト観点・条件（CI）・カバレッジ項目             | 完了（項目53: 有効37・一部ブロック2・ブロック13・要確認1） | `06-test-conditions.md`   |
| —  | `test-case-design`                                            | 詳細TC                                             | **対象外（依頼範囲の外）**                                 | —                         |
| —  | `coverage-analysis` / `adversarial-review`                    | カバレッジ・独立レビュー                           | **未実施（依頼範囲の外）**                                 | —                         |
| —  | `e2e-test-*` / `test-architecture-design` / `test-management` | E2E・方式・計画                                    | **未実施（依頼範囲の外）**                                 | —                         |

## 入力revision

- 記録: `input-revisions.json`（`input-revision-v1`）。対象は cart.md、spec の README・roles・state・storefront・checkout・screen-catalog、および補助情報源（01_requirements、03_domain、12_quality）の計10件。
- 初回実行時は `no_record` として新規扱いし、完了後に `record` で記録した。
- 2026-11-13 の再開時: `input_revision.py compare`（現workspaceをroot指定）の結果は `status: same`（changed・added・removed なし）。記録の `root` は旧workspace（`candidate-initial_qa-1`）のままだが、内容ハッシュは現workspaceと一致している。`record` の再実行はしていない。
- `changed` のパスに依存する成果物だけを `要再検証` とする（対応表は下記）。

| 入力                                                     | 依存する成果物                                     |
| -------------------------------------------------------- | -------------------------------------------------- |
| `features/cart.md`                                       | 01〜06 すべて                                      |
| `features/storefront.md`（CROSS-STOREFRONT-003）         | 01, 05（TR-017）, 06（CI-009, 010）                |
| `features/checkout-and-payment.md`（CROSS-CHECKOUT-002） | 01, 05（TR-021）, 06（TR-021 関連）                |
| `roles-and-permissions.md`                               | 01, 05（TR-016）, 06（CI-037〜040）                |
| `state-and-scenarios.md`                                 | 01, 05（TR-007, 015, 019）, 06（CI-018, 033, 034） |
| `screen-catalog.md`                                      | 01                                                 |
| 補助情報源（01_requirements・03_domain・12_quality）     | 01（§2）, 02（Q-01 他）, 03（P-01）                |

## 再利用・再実行

- 2026-11-13 の再開（依頼と対象範囲は初回と同一）: 入力10件すべて `same` のため、工程1〜6（`01`〜`06`、`02`、`03`）を**再利用**した。再生成・再実行はしていない。
- 再利用の条件確認: 対象範囲は同一、上流入力は不変、`要再検証` なし、ブロック中は前回どおり期待結果を作っていない。`06` の件数集計（有効37・一部ブロック2・ブロック13・要確認1、計53）も本文と一致することを確認した。
- 再実行した工程: なし。`要再検証` に戻した成果物: なし。

## ブロック中・要再検証

- ブロック中（期待結果を作らない）: 02 の Q-01・Q-02・Q-03・Q-04・Q-08・Q-10・Q-12（ブロッカー）、および Q-05・Q-06・Q-09・Q-11・Q-13・Q-14（要確認）。詳細は `02` と `03`。
- 承認保留: `03-pending-approvals.md` の P-01〜P-12。すべて未承認。
- `要再検証`: なし（初回）。

## 機械的ランタイム検証（未実施）

- `workflow_runtime.py` の runtime dispatch、`verify_runtime_evidence`、owner verifier、workflow_ref の正規UUID、state CAS は**実行していない**。
- そのため、本ワークフローの成果物は機械検証（runtime evidence）で `valid=true` を確認したものではない。`unverified_scopes` は全件残る。
- 本成果物は**完了（workflow complete）とは扱わない**。状態は「部分完了（ブロック中あり）」かつ機械検証未実施。
- 2026-11-13 時点でも同じ判断。本workflowには `ui-target-v1` package がなく、登録済みowner verifier（test-item-analysis / test-condition-analysis / e2e-test-selection / test-reporting）の対象も含まないため、scope 0 としてruntime dispatchは行わない。
- 機械検証を行う場合は、正規の `workflow_ref` と `qa.workflow_state_root` の設定、各 scope の runtime 入力が必要。今回は依頼範囲と照らして、その設定を行っていない。
- 製品のcommit（依頼: `2a8bcf57`）との照合は未実施。`product/` に `.git` がなく、commit IDを確認できない。

## 中断・再開

- 初回実行: 中断なし（一括実行）。
- 2026-11-13 の再開: 前回の完了状態から再開。中断した工程はなし。承認者からの回答は未受領（`03` は全件未承認のまま）のため、新たな工程は進めていない。
- 再開先（回答後）: 承認が得られた P 項目の Q を `question-analysis` → `spec-analysis`（cart.md 反映・DECISION 化）→ 影響する下流（`test-requirement-design` 以降）を `要再検証` にして再実行。

## 次の一手（承認・依頼が必要なもの）

1. `03-pending-approvals.md` の P-01（補助情報源の現行有効性と優先順位）への回答。これが最も影響が大きい。
2. P-02〜P-07 の回答により、ブロック中の TR / CI の期待結果を確定できる。
3. 回答後に `test-case-design` へ進める（依頼があれば）。
