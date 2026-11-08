# PR #22 並行実装：E — 正式テスト設計・E2E選定

## 位置付け

既存Product Risk→TR→TCN／CI→TCを保ち、機能・item・共通条件候補と技術非依存のE2E選定をつなぐ。

- 作業branch：`feat/pr22-e-formal-design-e2e-selection`
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
- [詳細03：E2E・直接開始](../../plans/2026-11-07_170134_qa-full-process-implementation_03_workflow-and-acceptance.md)

関連完了条件の主な担当：開発連動QA 5・8・12・13・14、QA全工程 2・9の正式設計部分。

## このbranchで変更する対象

- 新設`skills/e2e-test-selection/**`
- 既存`skills/test-analysis/**`、`skills/test-requirement-design/**`、`skills/test-condition-design/**`、`skills/test-case-design/**`、`skills/coverage-analysis/**`の必要な接続
- それらの既存runtime／validator／fixture／migrationテスト（共有runtimeの改変はAへ）

**変更境界**：以下に記載のない共有ファイルを変更したくなった場合は、書込みownerへ変更内容・必要な入力出力・検証例を渡す。既存実装の回帰を避けるため、既存helperの再利用を優先し、他担当の正本を新設Skillに複製しない。新規テスト・fixture・評価データは可能な限り担当固有のファイルに分ける。

## 着手基準

- [ ] Risk・TR・TCN・CI・TC・coverageの実装、schema、呼び出し元・先、CI・テストと既存IDを確認した。
- [ ] B／C／D／Fの受渡し契約と`test-analysis`のE単一編集ownerを確認した。

## 作業内容

1. B/D/C/Fから渡るsource、機能、item、共通条件候補、Authority、アーキテクチャ割当を既存Product Risk・TR・TCN・CI・TCに接続する。
2. 一次RiskをTRより前に扱い、新証拠や条件候補による局所再評価を行い、製品仕様・QA計画・Riskの正本を混ぜない。
3. item×conditionの採否／正当な不採用／未確認、アイテムごとの正式TCN ID、複数期待結果候補のAuthority・観測・副作用の根拠を保持する。
4. 既存CIのpartition／boundary／rule等の局所技法候補と共通condition IDを区別し、TCの個別期待結果が現在有効なAuthorityを持つか検証する。
5. テストレベルは明示指定＞承認済みarchitecture＞既存既定の優先で反映し、変更されたレベル・仕様・Riskに依存する範囲だけ再検証する。
6. 技術非依存のE2E候補・選定理由・履歴・source参照を新設し、既存Playwright E2E Skillによる検査／実装／実行を複製しない。
7. 既存ID・artifact graph・正規成果物・legacy・partial rerun・direct TC/E2Eでの利用を回帰する。

## 依存と引継ぎ

- B/C/D/F→E：機能・UI・item・condition・仕様Authority・QAレベル割当のref。
- E→G/H/J：正式TCとE2E選定ref・coverage評価。
- A：共有runtime登録依頼。Fが必要とする既存`test-analysis`変更はEが実施する。

**並行作業**：依存先のコード完成を待たずに固定fixtureで開発してよい。ただし、最終的には保存済みの実成果物ref・source revision・履歴・現在性を照合し、fixture成功を実統合成功と混同しない。必要な情報・権限・環境が欠けるときは、該当scopeを未確認／blockedと記録して別scopeの作業を継続する。

## 完了基準

- [ ] 各正本とauthorityを守り、feature/item/condition/architectureから既存設計まで実ID・revisionで追跡できる。
- [ ] 採否・不採用・blocked・複数expected result・別レベル・既存技法CIが互いに混同されない。
- [ ] 技術非依存のE2E選定がE2E実装・実行とは独立して発火し、既存E2E直接利用を妨げない。
- [ ] Risk・TR・TCN・CI・TC・coverageのlegacy／migration／partial rerun回帰と、authorityなし期待結果・誤100%等の負例がPASSする。
- [ ] 既存ID・証拠・既存設計／executionの直接入口が保たれ、Aによる統合検証へ渡せる。
- [ ] 新Skillと改訂既存Skillのisolated/trigger/semantic・決定論的評価を実行した。

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
