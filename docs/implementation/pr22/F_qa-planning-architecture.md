# PR #22 並行実装：F — QA要求・アーキテクチャ・管理

## 位置付け

QA活動の要求・レベル／方式／環境の全体割当・計画と監視／是正を、既存製品仕様・設計・workflow状態から独立した正本として実装する。

- 作業branch：`feat/pr22-f-qa-planning-architecture`
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
- [詳細02：保存・承認・集計](../../plans/2026-11-07_170134_qa-full-process-implementation_02_storage-approval-reporting.md)

関連完了条件の主な担当：QA全工程 1・2・3・5・8。報告・評価本体はJ。

## このbranchで変更する対象

- 新設`skills/test-requirements-analysis/**`、`skills/test-architecture-design/**`、`skills/test-management/**`
- QA要求・レベル割当・計画改版・project risk・source inventoryのデータ契約・局所テスト

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

## 着手基準

- [ ] 既存Project Context・TR・Risk・test-analysis・qa-workflow・Regressionの正本、計画source ref、承認要件を確認した。
- [ ] Aと保存／承認、Eとレベル優先順、Jと計画母集団を合意した。

## 作業内容

1. QA活動の要求元・目標・対象／非対象・品質条件・承認根拠・未決定を記録する。製品要求・TRの第二の正本を作らない。
2. テストレベル・タイプ・方式・環境・データ・非機能品質特性の割当を管理し、明示指定＞承認済みarchitecture＞既定値の優先と改版影響を扱う。
3. suite・実行時点・対象build・担当・工数／資源・入口／終了基準・監視・project risk・是正を管理し、`qa-workflow`のrouting stateとRegression Runを二重管理しない。
4. 予定source inventoryと必要実行の母集団をJへ渡し、未取得結果・未実行・取消しの区別を維持する。
5. 承認済み計画の改版・失効、承認前の計画を現行扱いしない負例、environment／architecture変更の局所再評価を検証する。
6. 既存成果物からの管理／報告だけの直接開始と、新設B/D未実装時の単独受入を可能にする。

## 依存と引継ぎ

- B→F：配置・Project Context参照。
- F→E：承認済みレベル／方式・環境割当。`test-analysis`編集はEへ依頼する。
- F→G/H/J：実行計画・source inventory・終了条件・承認revision。
- A：承認／保存／workflow runtimeの共有変更依頼。

**並行作業**：依存先の完成前でも固定fixtureで担当範囲を実装・局所検証する。実際の他owner成果物を用いた横断照合はPR #22で行う。必要な外部情報・権限・環境が不足する箇所は未検証／blockedと記録し、独立して実装可能な箇所は継続する。

## 完了基準

- [ ] 3 Skillが単独・複合で正しく発火し、QA要求・architecture・計画を製品仕様や個別TRと区別できる。
- [ ] QA要求→レベル／方式割当→計画／進捗・是正・終了基準への正規refが成立した。
- [ ] 変更前後の承認・revision・currentness、環境・方式変更、未取得sourceを扱い、未承認計画を現行にしない。
- [ ] レベル変更が必要なRisk・正式設計・testware準備にだけ伝わり、無関係なcurrent成果物を保持した。
- [ ] Jが集計に利用できる正式な実行母集団・取得範囲の出力契約とfixtureを提供し、既存Regressionとの重複正本を作らない。Jの実成果物との照合はPR #22へ引き継いだ。
- [ ] isolated/trigger/semantic・決定論的・統合評価と保存／承認の負例を実行した。

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
