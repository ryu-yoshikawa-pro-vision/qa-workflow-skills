# PR #22 並行実装：J — 欠陥・統合報告・活動評価

## 位置付け

raw結果の正本を保持したまま、欠陥候補・外部Issue追跡、source取得完全性付き統合報告、QA活動改善の実施・再測定を実装する。

- 作業branch：`feat/pr22-j-defects-reporting-evaluation`
- PRのbase／最終統合先：`feat/development-qa-traceability`（[PR #22](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/pull/22)）
- 分岐元commit：`718005961ade89a848788e8ad3a354d4c711b84a`
- このbranchのPRは**実装準備のDraft**から始め、以下の完了条件を満たしてレビューできる状態にする。**実装完了・merge済みを意味しない**。
- 2026-11-08の利用者指示で、最終統合先はPR #22に変更された。既存Plan索引の「PR #22は文書変更PR」という作成時点の記載より、この統合指示を優先する。
- このファイルは担当別の作業ガイド。要件・完了条件の正本は以下のPlan。**15＋10条件、詳細Plan 01〜08、S1〜S17、人間編集8ケースを削減しない**。全体の最終完了判定はPR #22で行う。

## 参照するPlan

- [PR #22：開発連動QA・QA全工程の実装Plan](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/pull/22)
- [Plan索引](../../plans/2026-11-07_170134_qa-full-process-implementation_00_index.md)
- [開発連動QA Plan（15完了条件）](../../plans/2026-11-07_122247_development-qa-traceability.md)
- [QA全工程Plan（10完了条件）](../../plans/2026-11-07_170134_qa-full-process-implementation.md)
- [詳細02：承認・取得完全性](../../plans/2026-11-07_170134_qa-full-process-implementation_02_storage-approval-reporting.md)
- [詳細06：改善の実施・再測定](../../plans/2026-11-07_170134_qa-full-process-implementation_06_static-testing-and-improvement.md)

関連完了条件の主な担当：QA全工程 4・5・6・8・10。開発評価の効率比較はA、QA案件の活動評価はJ。

## このbranchで変更する対象

- 新設`skills/defect-management/**`、`skills/test-reporting/**`、`skills/test-evaluation/**`
- 各Skillの外部Issue参照・raw結果集計・品質／効率評価・改善引継ぎの局所validator／評価

**変更境界**：以下に記載のない共有ファイルを変更したくなった場合は、書込みownerへ変更内容・必要な入力出力・検証例を渡す。既存実装の回帰を避けるため、既存helperの再利用を優先し、他担当の正本を新設Skillに複製しない。新規テスト・fixture・評価データは可能な限り担当固有のファイルに分ける。

## 担当branchで実施する作業とPR #22で実施する作業

### このbranchで実施・検証する

- 本書の担当対象のSkill・runtime・helper・データ契約・既存consumerとの局所接続を実装し、担当範囲の既存テスト・回帰・負例・権限／保存・履歴互換性を検証する。
- 担当機能の受入に必要な実runner・実保存先・実Agentの**単独経路**は、利用可能な環境で実施する。外部権限・実接続が不足する場合はその条件を未検証／blockedと明示し、独立に検証できる部分は完成させる。
- 他branchの未統合実装は合意した契約と独立fixtureで代替して局所検証する。fixtureは他ownerの実成果物を統合した証拠にはしない。
- 担当が所有する実装不具合、局所結合・回帰不具合は**このbranchで修正**し、対応したテスト・実施証拠を残す。

### PR #22だけで実施・判定する

- A〜Jの実装PRの取り込み、競合解消・全体再検証、**各ownerが実際に保存した成果物同士**のID／revision／currentness／承認・run参照による横断接続。
- 全current Skill同時利用時の発火／routing、工程をまたぐ実Agent・実runner・実provider・製品CIの一連の受入、S1〜S17の総合試験、人間編集8ケースの**全体経路としての再検証**。
- 開発連動QAの15条件、QA全工程の10条件と詳細Plan 01〜08の最終照合、Plan詳細07の5シナリオの**変更前後の横断実測・効率化判定**、統合後の全CI・回帰評価。
- 横断試験で見つかった問題はownerを特定し、分割可能な実装・修正は対象branchに戻す。統合固有の接続・設定・複数owner間の確認作業だけをPR #22で実施する。

### PR #22へ引き渡す証拠

- 担当の変更ファイル、公開入出力契約、参照するowner／source／artifact IDとrevision、schema／fixture、保存・承認・失敗／再開条件。
- 局所検証のコマンドと結果、実runner／実providerの担当経路の証拠、回帰・負例、未実行／SKIP／blockedと再開条件。
- 他担当の実成果物が必要な横断検証項目。**これらの未実施は担当branchの局所検証を失敗扱いする理由にはしないが、PR #22の最終受入完了には必ず必要**とする。

## 共通契約が未確定の場合の着手範囲

- A（[PR #23](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/pull/23)）のsource／artifact ID・revision・scope、runtime登録、保存・承認・CAS／readback、blocked／再開、評価・CI引継ぎ契約を**実コード・既存契約と照合し、PR #23で共有された内容**に従う。
- 上記に依存しない既存実装調査、担当Skill固有ロジック、独立fixture、局所テストは先行可能。Aによる確定・共有前に、未確定の共通schema・保存形式・承認・runtimeの接続方法を推測して確定しない。
- 契約未確定で停止する対象処理と理由・解決責任者・再開条件を記録し、独立して実施できる作業を止めない。Aが共有した契約を使う局所検証の後、他ownerの**実成果物を使う横断検証はPR #22**へ引き継ぐ。

## 着手基準

- [ ] 外部Issueの権限・source、現在のrun owner単位、計画inventory、source取得契約、既存Knowledge／評価の正本を確認した。
- [ ] F/G/H/I/E/Aとsource ref／raw result／run／retry／承認・source currentnessの受渡しを固定した。

## 作業内容

1. 実行ownerのFAIL／Observation／Findingと確度・証拠から欠陥候補を管理し、外部Issueを参照する。未確認原因で正式登録・closeせず、権限ある明示承認とscope/revisionがある操作だけ更新する。
2. 修正通知は元run ownerへ返し、旧build／不明な変更を誤修正確認扱いしない。外部Issueサービスの現在性・競合・操作済み不明を照合する。
3. Fの予定source inventoryに対し、E2E・一般TC・Regression・探索・API／バッチ・静的テスト／非機能・欠陥の実際の元source refを収集し、取得完全性を独立照合する。
4. 正式TC／retry／attempt／Activity／補助testwareの分母、build／revision／未実行／SKIPを区別し、見かけの100%や誤PASSを拒否する。
5. QA活動5軸の効果・効率・保守／再利用・引継ぎ・改善を評価する。測定不能・悪化・比較不能を成果へ算入しない。
6. 採用・認可された改善をF/E/実行ownerの正本改版へ返し、実施と次回測定まで検証する。Skill構成そのものの開発時効率比較はAのEVALS評価に残す。

## 依存と引継ぎ

- F→J：QA計画・予定source inventory・品質／終了条件・承認revision。
- G/H/I/E→J：元run／Activity／Finding／TR・coverage等の読み取りref。
- J→G/H：外部修正通知に基づく元runnerの再実行依頼。
- J→F/E/I：採用済み改善の正本改版・Knowledge利用候補。
- A：外部操作の認可・CAS／readbackの共通契約に沿って接続する。

**並行作業**：依存先の完成前でも固定fixtureで担当範囲を実装・局所検証する。実際の他owner成果物を用いた横断照合はPR #22で行う。必要な外部情報・権限・環境が不足する箇所は未検証／blockedと記録し、独立して実装可能な箇所は継続する。

## 完了基準

- [ ] 候補→外部Issue参照→修正通知→元実行owner確認が成立し、無許可書込み・重複・誤close・旧build確認を拒否する。
- [ ] 予定母集団と実取得を突合し、欠落・部分取得・旧revision・異なるbuild・retryの偽PASS／偽100%を独立validatorで拒否する。
- [ ] 複数技術のraw結果を元ownerから参照し、正式TC・補助・attempt・Activity・静的結果の計測単位を維持する。
- [ ] 5軸評価と採用／承認→正本改版→実施→次回測定が成立し、未承認・未実施・未測定を完了扱いしない。
- [ ] 新3 Skillの単独・複合発火、負例・権限・監査・deterministic／semantic・既存報告回帰がPASSする。
- [ ] QA全工程Plan 4・5・6と詳細02／06のJ担当範囲について、単独Skillの実Agent・利用可能な実providerの局所受入証拠を記録した。F/G/H/I/Eの実成果物との横断受入はPR #22へ引き継いだ。

- [ ] 変更したSkillの正式な`SKILL.md`・入力／出力・履歴／状態・運用文書と、必要なisolated packaging・決定論的テスト・意味評価・trigger評価を揃えた。
- [ ] 対象Planの正常系と負例を独立基準・証拠で判定し、旧artifact／legacy・既存呼び出し元・下流consumer・CIへの回帰を確認した。
- [ ] 関連unit／integration、repository既定のformat/lint/Skill validation、関連Actionsを個別に確認し、実行したコマンド・結果・未検証理由をPR本文へ記載した。
- [ ] source ref・artifact ref・revision・必要承認・保存readback・失敗／再開条件をAと接続し、統合時に再取得できる証拠を残した。
- [ ] 担当branch内の実装・局所検証は完了し、PR #22のみで行う横断検証と15＋10条件の最終判定を**担当branchの完了条件から除外して**引継ぎ項目として記録した。

## PR #22へ取り込む前の確認

1. 自branchの差分が担当範囲に収まり、他担当の変更・main／PR #17の最新変更と衝突しないか再確認する。
2. 変更内容・受入証拠・未実施／blocked／SKIP・データ互換・移行・rollbackの影響をPR本文に記載する。
3. PRのbaseが`feat/development-qa-traceability`であることを確認する。**PRのmain向け付け替え、merge、close、force push、branch削除は依頼なしに行わない**。
4. PR #22へ担当の変更・証拠・依存条件を引き渡す。PR #22の統合確認は**PR #22上で実施**し、A担当branchには移さない。
