# PR #22 並行実装：A — 共通runtime・保存・CI・統合

## 位置付け

共通の検証・routing・保存／承認条件・製品CI受渡し・全Skill受入を担当する。個々の意味判断や成果物正本は各Skillに残す。

- 作業branch：`feat/pr22-a-runtime-integration`
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
- [詳細02：保存・承認・集計](../../plans/2026-11-07_170134_qa-full-process-implementation_02_storage-approval-reporting.md)
- [詳細03：workflow・受入](../../plans/2026-11-07_170134_qa-full-process-implementation_03_workflow-and-acceptance.md)
- [詳細04：runtime・Regression](../../plans/2026-11-07_170134_qa-full-process-implementation_04_workflow-runtime-and-regression.md)
- [詳細07：効率比較](../../plans/2026-11-07_170134_qa-full-process-implementation_07_process-efficiency-acceptance.md)

関連完了条件の主な担当：開発連動QA 2・3・7・11・15、QA全工程 8・9・10を中心に全体受入を所有する。

## このbranchで変更する対象

- `skills/qa-workflow/scripts/**` と必要な `skills/qa-workflow/` の契約
- `skills/qa-workflow/assets/project-context-template.md` の互換調整（Bの必要条件を受付）
- 共有評価基盤、`EVALS.md`、共通CI、全体README・受入記録
- 製品CI向けの成果物検証と案件別受渡し接続（接続先／認可の決定を含む）

**変更境界**：以下に記載のない共有ファイルを変更したくなった場合は、書込みownerへ変更内容・必要な入力出力・検証例を渡す。既存実装の回帰を避けるため、既存helperの再利用を優先し、他担当の正本を新設Skillに複製しない。新規テスト・fixture・評価データは可能な限り担当固有のファイルに分ける。

## 着手基準

- [ ] PR #22の固定HEAD、既存CIと対象Skill・テスト・PR #17／#10の変更範囲を読んだ。
- [ ] A〜Jの編集owner表、保存先・承認・ID／revision／状態／evidenceの最小引継ぎ契約を各担当と共有した。
- [ ] 実保存先、対象製品repoのCI権限、比較測定方法の可否を確認し、不足はblockedで記録した。

## 作業内容

1. PR #17・#10を含むbase/関連実装、既存23 Skill、runtime・評価runner・CIの差分／呼び出し元・先を確認し、A〜Jの正本owner・入力出力・依存revisionを固定する。
2. `_default_expected_runtime_units()`等の未登録Skill・未検証scope・空evidenceの完了判定を修正し、新設14 Skillの検証／routing／partial rerun／別セッション再開を維持する。
3. provider-native create-if-absent／update-if-revision(CAS)・履歴・readback・操作開始前記録・保存失敗／重複時の再照合を、ownerごとの既存保存経路へ接続する。単なるread-compare-writeをCAS扱いしない。
4. 対象scope・revisionに紐付く認証済み承認主体を検証し、未承認／期限切れ／権限不足／未信頼資料内指示を拒否する。外部Issueの意味処理はJに残す。
5. source inventory／差分分類／正規成果物を製品CIへ渡す方式を案件で選定し、接続可能な環境で旧HEAD・欠落・未分類・hash不一致をfailさせる。未設定なら実接続をblockedで保持する。
6. A〜Jの実成果物をつなぐS1〜S17、固定qa-training-store commitと独立fixture、全current Skill同時利用・実Agent発火、実providerの受入を計画し実行する。
7. Plan詳細07の5条件（初回・変更なし・局所コード変更・外部仕様改版・中断再開）で品質・安全を維持した実測比較を行い、未測定・比較不能と効率改善を区別する。

## 依存と引継ぎ

- B→A：source inventory・機能／変更差分と製品CIが検証すべき参照。
- C／D／E／F／G／H／I／J→A：正本ref・revision・validator・required route・独立fixture・negative case。
- A→全担当：runtime登録・save/approval/handoff契約。共通ファイル編集はAのみ。

**並行作業**：依存先のコード完成を待たずに固定fixtureで開発してよい。ただし、最終的には保存済みの実成果物ref・source revision・履歴・現在性を照合し、fixture成功を実統合成功と混同しない。必要な情報・権限・環境が欠けるときは、該当scopeを未確認／blockedと記録して別scopeの作業を継続する。

## 完了基準

- [ ] 未登録Skill・空evidence・旧revision・scopeの食違いを完了扱いしないruntime／routingと、既存経路の互換性が自動テストで確認された。
- [ ] native CAS・履歴・readback・承認・操作状態不明・二重受付・局所再開の正常／拒否／失敗テストが実providerを含めて成立した。
- [ ] 対象案件の実製品CIに成果物を渡して決定論的照合を行い、必須artifact欠落・旧版をfailさせた。方式未選定や未接続なら当該条件は未完了と記録した。
- [ ] 各担当の正規出力を用いてS1〜S17と別セッション再開を完走し、独立fixtureだけの成功で全体完了にしなかった。
- [ ] Plan詳細07の5比較についてraw測定・独立品質基準・未測定項目・改善／悪化時再測定を記録した。
- [ ] 新旧全current Skillの発火・構造・決定論的・意味・統合評価、各GitHub Actions、formatter、docsを個別検証し、未実施をPASS扱いしなかった。
- [ ] 開発連動QAの15条件、QA全工程の10条件および詳細01〜08の全条件について、担当別の証拠と未完了を照合した。

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
