# PR #22 並行実装：I — QA Knowledge・探索

## 位置付け

QA Knowledgeのidentity・scope・currentnessを正し、Charter／探索／症状調査の直接開始と安全な別セッション再利用を扱う。

- 作業branch：`feat/pr22-i-knowledge-exploration`
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
- [詳細06：探索／Knowledge／改善](../../plans/2026-11-07_170134_qa-full-process-implementation_06_static-testing-and-improvement.md)
- [詳細04：別セッション再開](../../plans/2026-11-07_170134_qa-full-process-implementation_04_workflow-runtime-and-regression.md)

関連完了条件の主な担当：QA全工程 8・9のKnowledge／探索・再開部分。

## このbranchで変更する対象

- 既存`skills/qa-knowledge/**`、`scripts/knowledge_runtime.py`を含むvalidator・lookup・lifecycle
- 既存`skills/exploratory-testing/**`の直接開始／Charter／Findingの必要な接続と局所テスト

**変更境界**：以下に記載のない共有ファイルを変更したくなった場合は、書込みownerへ変更内容・必要な入力出力・検証例を渡す。既存実装の回帰を避けるため、既存helperの再利用を優先し、他担当の正本を新設Skillに複製しない。新規テスト・fixture・評価データは可能な限り担当固有のファイルに分ける。

## 着手基準

- [ ] QA Knowledgeのentry schema・identity・hash・read_revision・reader／writer、探索Charter・session／Findingと既存テストを確認した。
- [ ] A/Jとhandoff・承認・欠陥候補と既存result ownerの境界を固定した。

## 作業内容

1. `identity.kind`／`scope_refs`とentry最上位のkind／scopeを照合し、ID hash一致だけで矛盾するentryを受け入れない。
2. scope別source currentness・read revisionを扱い、無関係なentryの依存不明だけで検索全体をblockedにしない。
3. 候補のpartial lookup、legacy entry／再検証・readback・同時更新と別セッション再開を扱う。
4. 探索Charter・Observation・Finding／調査依頼から必要Skillへ直接進み、未確定症状を正式欠陥へ自動昇格させない。
5. Knowledgeの再利用を強制経由・第二の仕様／結果正本にせず、改善候補の採否・適用範囲とsource refをJ／Fへ渡す。

## 依存と引継ぎ

- I→J：Finding・Knowledge改善候補・source revision・scopeと未確認。
- I→A：read_revision・currentness・再開条件。
- J/F→I：承認済み改善からの再利用知識の更新要求。

**並行作業**：依存先のコード完成を待たずに固定fixtureで開発してよい。ただし、最終的には保存済みの実成果物ref・source revision・履歴・現在性を照合し、fixture成功を実統合成功と混同しない。必要な情報・権限・環境が欠けるときは、該当scopeを未確認／blockedと記録して別scopeの作業を継続する。

## 完了基準

- [ ] identity.kind／scopeと適用対象の不一致を拒否し、旧entry／正当なscopeの読取互換を維持する。
- [ ] 部分検索・無関係scope stale・read_revision・再検証・保存失敗／競合と別セッション再開を検証した。
- [ ] Charter／Knowledgeから独立発火・停止／再開でき、無関係な設計・全工程Skillを強制しない。
- [ ] 探索FindingからJの欠陥候補／報告へ参照を渡せるが、run／仕様の正本を複製しない。
- [ ] 詳細06のKnowledge／探索条件と既存lifecycle・deterministic／trigger／semantic回帰がPASSする。

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
