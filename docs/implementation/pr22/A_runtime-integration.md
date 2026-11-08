# PR #22 並行実装：A — 共通runtime・保存・CI基盤

## 位置付け

共通の検証・routing・保存／承認・製品CI受渡しの機構を実装・局所検証する。**全Skillの横断受入と統合作業はPR #22**に限定し、A担当branchでは実施しない。個々の意味判断や成果物正本は各Skillに残す。

- 作業branch：`feat/pr22-a-runtime-integration`
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
- [詳細03：workflow・受入](../../plans/2026-11-07_170134_qa-full-process-implementation_03_workflow-and-acceptance.md)
- [詳細04：runtime・Regression](../../plans/2026-11-07_170134_qa-full-process-implementation_04_workflow-runtime-and-regression.md)
- [詳細07：効率比較](../../plans/2026-11-07_170134_qa-full-process-implementation_07_process-efficiency-acceptance.md)

関連完了条件の主な担当：開発連動QA 2・3・7・11・15、QA全工程 8・9・10のうち、共通runtime・保存・CI・評価基盤を実装する。全体受入の実施・判定はPR #22。

## このbranchで変更する対象

- `skills/qa-workflow/scripts/**` と必要な `skills/qa-workflow/` の契約
- `skills/qa-workflow/assets/project-context-template.md` の互換調整（Bの必要条件を受付）
- 共有評価基盤、`EVALS.md`、共通CI・READMEのA担当実装部分（横断受入記録はPR #22）
- 製品CI向けの成果物検証と案件別受渡し接続（接続先／認可の決定を含む）

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

## 共通契約の確定と共有（後続実装の前提）

- [ ] 実装開始時点の既存runtime／正本schema・呼び出し元／下流・CI・PR #17／#10を確認し、既存契約の再利用と変更が必要な契約を区別した。
- [ ] B〜Jで共通利用するsource／artifact ID、revision／currentness、scope、owner、保存先のnative CAS・履歴／readback、承認主体・対象revision、blocked／resume、証拠・実行結果・cleanupの**公開引継ぎ条件**を、各正本ownerの責務を保って担当Markdownまたは検証レポートへ記録し、PR #23から参照できるようにした。
- [ ] 契約ごとのschema・固定fixture・正常例／拒否例、既存資産・legacyの互換性、共有ファイルの編集ownerをB〜Jへ伝達した。
- [ ] 保存provider・製品CI受渡し・承認者等の案件固有の未決定事項は仮の既定値にせず、未決定／blockedの範囲、決定元、再開条件を記録した。
- [ ] 共通契約を確認しただけでA〜Jの実成果物の横断接続を完了扱いしていない。実成果物による統合受入はPR #22へ引き継ぐ。

この文書のチェックリストは**共通契約の確定完了を宣言するものではない**。証拠と契約がPR #23に保存されるまで、B〜Jの依存実装へ確定済みと通知しない。

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
6. S1〜S17に必要な共通検証器・評価形式・fixture・CI契約を実装し、A担当経路を局所検証する。A〜Jの実成果物をつなぐ総合受入、全current Skill同時利用と実Agent発火・実provider横断検証はPR #22で実施する。
7. Plan詳細07の5条件（初回・変更なし・局所コード変更・外部仕様改版・中断再開）を測定する共通基盤と独立品質判定を実装・局所検証する。全体の同条件実Agent比較・改善判定・再測定はPR #22で実施する。

## 依存と引継ぎ

- B→A：source inventory・機能／変更差分と製品CIが検証すべき参照。
- C／D／E／F／G／H／I／J→A：正本ref・revision・validator・required route・独立fixture・negative case。
- A→全担当：runtime登録・save/approval/handoff契約。共通ファイル編集はAのみ。

**並行作業**：依存先の完成前でも固定fixtureで担当範囲を実装・局所検証する。実際の他owner成果物を用いた横断照合はPR #22で行う。必要な外部情報・権限・環境が不足する箇所は未検証／blockedと記録し、独立して実装可能な箇所は継続する。

## 完了基準

- [ ] 未登録Skill・空evidence・旧revision・scopeの食違いを完了扱いしないruntime／routingと、既存経路の互換性が自動テストで確認された。
- [ ] native CAS・履歴・readback・承認・操作状態不明・二重受付・局所再開の正常／拒否／失敗テストが実providerを含めて成立した。
- [ ] 製品CI受渡し機構・決定論的照合・artifact欠落／旧版のfail条件をA担当の独立経路とfixtureで検証した。担当の実接続が可能なら実証し、未接続は記録した。全owner成果物を通す実製品CI総合受入はPR #22へ引き継いだ。
- [ ] S1〜S17・別セッション再開に必要なA担当の共通契約と独立fixtureで局所検証した。各担当の実成果物を用いたS1〜S17総合受入はPR #22へ引き継いだ。
- [ ] Plan詳細07の5比較の計測・独立品質判定・未測定区分を実装し、局所試験を記録した。5条件の横断実測・比較・悪化時再測定はPR #22へ引き継いだ。
- [ ] A担当のruntime／共有評価基盤・Skill登録・局所routingと関連GitHub Actions／formatter／docsを検証した。全current Skill同時発火・全体CIの統合評価はPR #22へ引き継いだ。
- [ ] 15＋10条件および詳細01〜08の**A担当部分**の実装証拠と、PR #22へ渡す未完了の統合条件を整理した。全条件の最終照合はPR #22のみで行う。

- [ ] 変更したSkillの正式な`SKILL.md`・入力／出力・履歴／状態・運用文書と、必要なisolated packaging・決定論的テスト・意味評価・trigger評価を揃えた。
- [ ] 対象Planの正常系と負例を独立基準・証拠で判定し、旧artifact／legacy・既存呼び出し元・下流consumer・CIへの回帰を確認した。
- [ ] 関連unit／integration、repository既定のformat/lint/Skill validation、関連Actionsを個別に確認し、実行したコマンド・結果・未検証理由を担当Markdownまたは検証レポートへ記録し、PR本文は最新状態と参照先のみを示した。
- [ ] source ref・artifact ref・revision・必要承認・保存readback・失敗／再開条件をA担当の共通契約として実装・局所検証し、PR #22で再取得できる証拠を残した。
- [ ] 担当branch内の実装・局所検証は完了し、PR #22のみで行う横断検証と15＋10条件の最終判定を**担当branchの完了条件から除外して**引継ぎ項目として記録した。

## PR #22へ取り込む前の確認

1. 自branchの差分が担当範囲に収まり、他担当の変更・main／PR #17の最新変更と衝突しないか再確認する。
2. 変更内容・受入証拠・未実施／blocked／SKIP・データ互換・移行・rollbackの影響を担当Markdownまたは検証レポートへ記録し、PR本文は目的と現在の状態だけに更新する。
3. PRのbaseが`feat/development-qa-traceability`であることを確認する。**PRのmain向け付け替え、merge、close、force push、branch削除は依頼なしに行わない**。
4. PR #22へ担当の変更・証拠・依存条件を引き渡す。PR #22の統合確認は**PR #22上で実施**し、A担当branchには移さない。
