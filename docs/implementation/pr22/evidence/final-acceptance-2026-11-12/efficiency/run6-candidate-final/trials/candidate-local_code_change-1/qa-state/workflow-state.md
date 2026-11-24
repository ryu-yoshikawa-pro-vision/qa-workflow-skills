# ワークフロー状態 — カート機能 QA（テスト分析〜テスト観点・条件設計）

## 基本情報

- 依頼: カート機能（`product/docs/spec/features/cart.md`）のQA。範囲は「テスト分析からテスト観点（条件）設計まで」。
- 対象製品: `product/`（ユーザー指定 commit `2a8bcf57`。本環境の`product/`にはgit情報がなく、commit一致は**未照合**）。
- 製品コードの局所変更（2026-11-13）: `product-change-code.diff`（sha256 `dd092337ba22c5bf8cfad73a1311ab499d704c04db98fdccda5091467a65b0bf`）。`src/application/contracts/common.ts` の `maxCartQuantity` を `99` → `100` に変更。`commit 2a8bcf57` にこの変更が加わった状態を、以後の製品として扱う。仕様書の入力revisionではないため `input-revisions.json` の対象外。
- 進行モード: `continuous`（既定）。
- 製品コード・仕様書: 変更していない。
- 保存先: 本ディレクトリ `qa-state/`。

## 工程と状態

| 順 | 工程（担当Skill）                                             | 対象 / 実行範囲                                        | 状態                                                           | 成果物                                        |
| -- | ------------------------------------------------------------- | ------------------------------------------------------ | -------------------------------------------------------------- | --------------------------------------------- |
| 1  | `spec-analysis`                                               | 対象範囲の現在有効な仕様Authority                      | 完了（ブロック中事項あり）                                     | `01-spec-authority.md`                        |
| 2  | `question-analysis`                                           | 不明点・矛盾の分類                                     | 完了（ブロッカー7件・要確認6件・提案1件）                      | `02-question-analysis.md`                     |
| 3  | 承認保留の記録                                                | 承認が必要な判断                                       | 記録済み（12件、全件未承認）                                   | `03-pending-approvals.md`                     |
| 4  | `test-analysis`                                               | テスト分析（プロダクトリスク・重点・レベル・技法）     | 完了                                                           | `04-test-analysis.md`                         |
| 5  | `test-requirement-design`                                     | テスト要求（TR）                                       | 完了（TR 27件: 有効15・一部ブロック中1・ブロック中11）         | `05-test-requirements.md`                     |
| 6  | `test-condition-design`                                       | テスト観点・条件（CI）・カバレッジ項目                 | 完了（項目53: 有効37・一部ブロック2・ブロック13・要確認1）     | `06-test-conditions.md`                       |
| 7  | 製品変更の影響判断（2026-11-13）                              | `product-change-code.diff`（`maxCartQuantity` 99→100） | 完了（影響判定・承認保留P-13追加。成果物の期待結果は変更なし） | `03-pending-approvals.md`（P-13）、本ファイル |
| —  | `test-case-design`                                            | 詳細TC                                                 | **対象外（依頼範囲の外）**                                     | —                                             |
| —  | `coverage-analysis` / `adversarial-review`                    | カバレッジ・独立レビュー                               | **未実施（依頼範囲の外）**                                     | —                                             |
| —  | `e2e-test-*` / `test-architecture-design` / `test-management` | E2E・方式・計画                                        | **未実施（依頼範囲の外）**                                     | —                                             |

## 入力revision

- 記録: `input-revisions.json`（`input-revision-v1`）。対象は cart.md、spec の README・roles・state・storefront・checkout・screen-catalog、および補助情報源（01_requirements、03_domain、12_quality）の計10件。
- 今回は初回のため `no_record` として新規扱いし、完了後に `record` で記録した。次回の再開時は `compare` で `same` / `changed` を判定する。
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

- 今回は全工程を初回実行。再利用した成果物はない。
- 今回の依頼内で、工程間の入力は順に渡した（再実行なし）。
- 2026-11-13 の再確認: `input-revisions.json` の10件を現在の `product/` と照合 → 全件 `same`。仕様入力は変化なし。01〜06 は再生成していない（再利用）。
- `input-revisions.json` の `root` は `candidate-initial_qa-1` を指しているが、ハッシュは現在のworkspaceの同名ファイルと一致した。root値は変更していない。

## 製品変更の影響判断（2026-11-13）

- 変更内容: `src/application/contracts/common.ts` の `maxCartQuantity` を `99` → `100`。
- 仕様との関係: `cart.md` BR-CART-001 と AC-CART-001 は、数量上限の第3の値を「99」と明記している。`business_rules.md` のカート節も「上限値99」。変更後の製品は100を受理しうる。
- 判断: 正式仕様は変更しない（`change-process.md`「既存仕様への違反」）。仕様違反の実装として扱い、期待結果は99のまま。
- 影響:
  - 01〜06 の期待結果・TR・CI は仕様（99）に基づくため**変更なし**。`要再検証` は発生しない。
  - 境界 CI-CART-003（最小が99、値 98・99・100・0）と CI-CART-001/002/005 の上限付き行は、変更後製品では100の行が **FAIL 候補** として観測される。これは期待結果の変更ではなく、実行時に観測される不一致。
  - 製品の不一致（100受理）は未確定の不具合として扱わず、`test-execution` の実行結果と `defect-management` の候補整理へ渡す。
  - 変更が意図的な仕様変更なら、P-13 の承認後に `spec-analysis` から改版し、影響下流（TR-001〜004、CI-CART-001〜005、関連AC）を `要再検証` にする。
- 承認保留: P-13 を追加（未承認）。

## ブロック中・要再検証

- ブロック中（期待結果を作らない）: 02 の Q-01・Q-02・Q-03・Q-04・Q-08・Q-10・Q-12（ブロッカー）、および Q-05・Q-06・Q-09・Q-11・Q-13・Q-14（要確認）。詳細は `02` と `03`。
- 承認保留: `03-pending-approvals.md` の P-01〜P-12。すべて未承認。
- `要再検証`: なし（初回）。

## 機械的ランタイム検証（未実施）

- `workflow_runtime.py` の runtime dispatch、`verify_runtime_evidence`、owner verifier、workflow_ref の正規UUID、state CAS は**実行していない**。
- そのため、本ワークフローの成果物は機械検証（runtime evidence）で `valid=true` を確認したものではない。`unverified_scopes` は全件残る。
- 2026-11-13 の製品変更対応でも再実行していない。`workflow_runtime.py` の検証は未実施のまま。
- 本成果物は**完了（workflow complete）とは扱わない**。状態は「部分完了（ブロック中あり）」かつ機械検証未実施。
- 機械検証を行う場合は、正規の `workflow_ref` と `qa.workflow_state_root` の設定、各 scope の runtime 入力が必要。今回は依頼範囲と照らして、その設定を行っていない。

## 中断・再開

- 中断なし（一括実行）。
- 再開先（回答後）: 承認が得られた P 項目の Q を `question-analysis` → `spec-analysis`（cart.md 反映・DECISION 化）→ 影響する下流（`test-requirement-design` 以降）を `要再検証` にして再実行。

## 次の一手（承認・依頼が必要なもの）

0. `03-pending-approvals.md` の P-13（数量上限 100 と仕様 99 の不一致。実装を99へ戻すか、仕様を変更するか）への回答。製品変更の確認に必要。
1. `03-pending-approvals.md` の P-01（補助情報源の現行有効性と優先順位）への回答。これが最も影響が大きい。
2. P-02〜P-07 の回答により、ブロック中の TR / CI の期待結果を確定できる。
3. 回答後に `test-case-design` へ進める（依頼があれば）。
