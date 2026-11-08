# PR #22 並行実装：G — 非E2E testware・実行

## 位置付け

API・バッチ・コンポーネント・非機能・静的検証のtestware実装／更新・実runnerによる実測・原因分析を担当する。

- 作業branch：`feat/pr22-g-non-e2e-testware`
- PRのbase／最終統合先：`feat/development-qa-traceability`（[PR #22](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/pull/22)）
- 分岐元commit：`718005961ade89a848788e8ad3a354d4c711b84a`
- このbranchのPRは**実装準備のDraft**から始め、以下の完了条件を満たしてレビューできる状態にする。**実装完了・merge済みを意味しない**。
- 2026-11-08の利用者指示で、最終統合先はPR #22に変更された。既存Plan索引の「PR #22は文書変更PR」という作成時点の記載より、この統合指示を優先する。
- このファイルは担当別の作業ガイド。要件・完了条件の正本は以下のPlan。**15＋10条件、詳細Plan 01〜08、S1〜S17、人間編集8ケースを削減しない**。全体の最終完了判定はPR #22で行う。

## 参照するPlan

- - [PR #22：開発連動QA・QA全工程の実装Plan](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/pull/22)
- - [Plan索引](../../plans/2026-11-07_170134_qa-full-process-implementation_00_index.md)
- - [開発連動QA Plan（15完了条件）](../../plans/2026-11-07_122247_development-qa-traceability.md)
- - [QA全工程Plan（10完了条件）](../../plans/2026-11-07_170134_qa-full-process-implementation.md)
- [詳細01：非E2E実装・実行](../../plans/2026-11-07_170134_qa-full-process-implementation_01_test-implementation-and-execution.md)
- [詳細05：実行と品質](../../plans/2026-11-07_170134_qa-full-process-implementation_05_testware-execution-and-quality.md)
- [詳細06：静的テスト](../../plans/2026-11-07_170134_qa-full-process-implementation_06_static-testing-and-improvement.md)

関連完了条件の主な担当：QA全工程 7・8・10の非E2E・静的／実行部分。

## このbranchで変更する対象

- 新設`skills/testware-implementation/**`、`skills/testware-execution/**`
- 既存`skills/adversarial-review/**`、`skills/test-execution/**`の必要な静的レビュー・直接実行の拡張
- 非E2Eのrunner adapter／preflight／cleanup／trace・assertion品質と独立fixture／実製品テスト

**変更境界**：以下に記載のない共有ファイルを変更したくなった場合は、書込みownerへ変更内容・必要な入力出力・検証例を渡す。既存実装の回帰を避けるため、既存helperの再利用を優先し、他担当の正本を新設Skillに複製しない。新規テスト・fixture・評価データは可能な限り担当固有のファイルに分ける。

## 着手基準

- [ ] 既存Playwright E2E／`test-execution`・`adversarial-review`、対象runner／fixture／cleanupとデータ権限を確認した。
- [ ] E/F/H/JとTC/ref・実行母集団・required route・run結果の単位を合意した。

## 作業内容

1. 対象TCまたは明示testwareから、API-only Playwright・Vitest・バッチ・イベント／非機能等の実装ownerを判定し、既存ブラウザE2Eと責務が重ならないようにする。
2. 安全なworktree／copyと競合時反映拒否の下でtestware・fixture・設定を実装／更新し、SUTの製品コードを改修しない。
3. TCに依存しない非ブラウザtestware直接実行、実runnerのpreflight・開始確認・attempt・raw結果・cleanup・副作用保護を行う。
4. Vitestのtest ID・TC ID・retryを区別し、実行結果を根拠なしのTC PASSへ変換しない。assertion・oracleを別経路でレビューする。
5. 非機能の測定条件／品質特性／閾値が未確定なら未確定として扱い、静的レビュー（`adversarial-review`）と静的解析ツール実行（`testware-execution`）を分離する。
6. 失敗時はSUT／testware／fixture／環境／runner／仕様不明等の観測・仮説・確度・証拠・再実行先を記録する。欠陥候補の外部Issue追跡はJへ渡す。

## 依存と引継ぎ

- E/F→G：TC・方式・準備・環境・終了条件。
- G→H/J：run・test ID・source/build revision・raw結果・cleanup・診断と取得完全性。
- A：実行ownerのruntime登録や保存／承認契約の共有変更を依頼する。
- J→G：修正通知を元testware・buildで再実行する依頼。

**並行作業**：依存先のコード完成を待たずに固定fixtureで開発してよい。ただし、最終的には保存済みの実成果物ref・source revision・履歴・現在性を照合し、fixture成功を実統合成功と混同しない。必要な情報・権限・環境が欠けるときは、該当scopeを未確認／blockedと記録して別scopeの作業を継続する。

## 完了基準

- [ ] 対象方式のtestware実装／更新と実runnerでの実行・raw証拠・cleanupが結びつき、独立fixtureと固定qa-training-storeの対象を区別した。
- [ ] preflight不備・共有データ競合・応答消失・cleanup失敗・隔離worktreeの競合を安全に拒否／再開できる。
- [ ] 非E2E結果の原因仮説・確度・結果確定・未実行を元runへ保持し、FAILを製品欠陥やTC PASSへ自動変換しない。
- [ ] 静的レビュー／静的解析・非機能品質・手動非ブラウザTCの各経路が必要範囲で実行でき、非対応・未設定を明示した。
- [ ] PlaywrightブラウザE2E・既存test-executionの呼び出しとテスト資産を壊さず、結果をH・Jが読み取れる。
- [ ] Plan詳細01・05の全完了条件と詳細06の静的テスト条件、関連unit／runner／isolated／意味評価を検証した。

- [ ] 変更したSkillの正式な`SKILL.md`・入力／出力・履歴／状態・運用文書と、必要なisolated packaging・決定論的テスト・意味評価・trigger評価を揃えた。
- [ ] 対象Planの正常系と負例を独立基準・証拠で判定し、旧artifact／legacy・既存呼び出し元・下流consumer・CIへの回帰を確認した。
- [ ] 関連unit／integration、repository既定のformat/lint/Skill validation、関連Actionsを個別に確認し、実行したコマンド・結果・未検証理由をPR本文へ記載した。
- [ ] source ref・artifact ref・revision・必要承認・保存readback・失敗／再開条件をAと接続し、統合時に再取得できる証拠を残した。
- [ ] 他担当へ渡す入出力と、PR #22でのみ確認できる未完了の全体条件を区別して報告した。

## PR #22へ取り込む前の確認

1. 自branchの差分が担当範囲に収まり、他担当の変更・main／PR #17の最新変更と衝突しないか再確認する。
2. 変更内容・受入証拠・未実施／blocked／SKIP・データ互換・移行・rollbackの影響をPR本文に記載する。
3. PRのbaseが`feat/development-qa-traceability`であることを確認する。**PRのmain向け付け替え、merge、close、force push、branch削除は依頼なしに行わない**。
4. PR #22の統合担当Aに引継ぎ、統合先で関連Plan条件を再検証する。
