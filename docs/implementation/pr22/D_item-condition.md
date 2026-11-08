# PR #22 並行実装：D — テストアイテム・共通条件

## 位置付け

製品機能とは別のテストアイテム、正式TCNとは別の共通テスト条件候補を、それぞれ独立の正本として管理する。

- 作業branch：`feat/pr22-d-item-condition`
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

関連完了条件の主な担当：開発連動QA 12・13・14の候補識別部分。正式設計への採否・期待結果はEが担当する。

## このbranchで変更する対象

- 新設`skills/test-item-analysis/**` と `skills/test-condition-analysis/**`
- 各Skillのstable ID・source fingerprint・候補対応・履歴・validator・評価／fixture

**変更境界**：以下に記載のない共有ファイルを変更したくなった場合は、書込みownerへ変更内容・必要な入力出力・検証例を渡す。既存実装の回帰を避けるため、既存helperの再利用を優先し、他担当の正本を新設Skillに複製しない。新規テスト・fixture・評価データは可能な限り担当固有のファイルに分ける。

## 着手基準

- [ ] 既存feature・SCOPE・TR／TCN／CI・Disposition・ID管理・当該ownerのsource revision契約を確認した。
- [ ] B・Eと機能ref、item ID、condition ID、候補根拠、非採用判断の受渡しを固定した。

## 作業内容

1. テストアイテムの独立ID、親子・多対多機能参照、UI／API／バッチ等の種類、予定／未実装／実装済み／廃止／不明、改版・循環検出を実装する。
2. 共通条件候補に安定ID、意図・根拠・Authority参照・適用可能種別・source revision・変更履歴を付与し、アイテム確定前でも独立識別できるようにする。
3. item候補とcondition候補を独立収集して、不足・重複・未発見母集団・未確認状態を相互照合する。全組合せを正式採用しない。
4. 条件候補／アイテムの再利用と再採番の違い、分割／統合／廃止／同名異義・異名同義、partial input、変更影響を検証する。
5. 正式item×condition採否・TCN／CI／期待結果候補の確定はEへ渡し、DではAuthorityや正式カバレッジを更新しない。

## 依存と引継ぎ

- B→D：feature ID・source inventory・revision。
- D→E：アイテム／共通条件候補のref・履歴・根拠と未確認母集団。
- A：runtime登録・provider保存契約を依頼する。

**並行作業**：依存先のコード完成を待たずに固定fixtureで開発してよい。ただし、最終的には保存済みの実成果物ref・source revision・履歴・現在性を照合し、fixture成功を実統合成功と混同しない。必要な情報・権限・環境が欠けるときは、該当scopeを未確認／blockedと記録して別scopeの作業を継続する。

## 完了基準

- [ ] 2 Skillが独立に発火し、根拠付きのstable ID・履歴・階層／多対多・再利用を扱う。
- [ ] 相互不足検出と候補／適用判断／正式設計／実行の別指標が成立し、未確認・blocked・分母0を100%にしない。
- [ ] 同名別ID、ID誤統合、循環、分割・廃止、source欠落、旧revision、CAS競合の負例がPASSする。
- [ ] Eが正規のitem・condition refから、TR・正式TCN・期待結果・CIへ実成果物で接続できる。
- [ ] 新Skillの構造・isolated/trigger・決定論的・意味・局所回帰を実行した。

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
