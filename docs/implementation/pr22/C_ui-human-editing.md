# PR #22 並行実装：C — UI分析・人間編集

## 位置付け

UI構造と期待仕様を分離し、既存ui-target-v1を破壊せず人間の編集案を正式なwriterへ取り込む。

- 作業branch：`feat/pr22-c-ui-human-editing`
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
- [詳細08：人間編集・構成管理](../../plans/2026-11-07_170134_qa-full-process-implementation_08_human-artifact-editing.md)

関連完了条件の主な担当：開発連動QA 5・8・12・14、QA全工程 9。詳細08の全8受入はCが実証する。

## このbranchで変更する対象

- 新設`skills/ui-target-analysis/**` と `skills/spec-analysis/**` のUI mode／利用側接続
- `skills/spec-analysis/scripts/ui_target_package.py` とUI package関連の既存回帰テスト
- 人間の編集案の差分抽出・検証・正式materializeに必要なSkill局所helper／受入テスト

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

- [ ] `ui_target_package.py`、既存UI modeの利用側・migration・legacy・関連テストを読み、A/B/Eの変更境界を確認した。
- [ ] Q06の合意の位置・保存先・編集権限・元snapshot／revision参照の契約を確認した。

## 作業内容

1. `ui-target-v1`の00〜09、scope readiness、stable ID、MANIFEST／CHANGELOG、Machine Entities、既存writer／consumerを確認し、新Skillへの移行で互換性を維持する。
2. UI構造・操作・状態・画面遷移だけをUI ownerとし、期待挙動・Authorization・業務状態のAuthorityは`spec-analysis`のままにする。
3. BのProject Context配置合意に基づき、人間が機能IDから編集可能な正本ファイル／行／stable IDへ辿れる導出参照を用意する。
4. 人間のbranch／copy編集差分を有効な元snapshotと照合し、生成部・手動採番・行削除・承認不足・意味上の衝突を検出する。
5. 採用差分は`materialize`の既存table/prose/retire更新契約に変換する。編集案のMANIFEST・生成物をそのまま正本へ取り込まない。
6. canonical root直接改変、古いManifest、競合、保存応答消失、権限不足で編集案を保全し、検証済みsnapshotからの復旧以外をblockedにする。

## 依存と引継ぎ

- B：Project Context Q06合意・feature ID・source refを受け取る。
- E：currentなUI構造と、別正本であるAuthority参照を渡す。
- A：shared runtimeへのUI Skill登録／保存・承認境界を依頼する。

**並行作業**：依存先の完成前でも固定fixtureで担当範囲を実装・局所検証する。実際の他owner成果物を用いた横断照合はPR #22で行う。必要な外部情報・権限・環境が不足する箇所は未検証／blockedと記録し、独立して実装可能な箇所は継続する。

## 完了基準

- [ ] 独立`ui-target-analysis`と既存`spec-analysis`が責務・形式・履歴・migrationを維持し、既存UI packageと正式設計の読取が壊れない。
- [ ] 詳細08の8ケース（通常編集、新規／廃止、禁止領域、無承認変更、同時編集、直接改変、失敗再開、正本探索）を実際の編集差分・正式writer・readbackまで検証した。
- [ ] 必要な源Authority・関連ID・承認・scopeを意味検証し、採用分だけwriterで版を更新し無関係IDは維持した。
- [ ] Manifest不一致や元revision不明を誤修復・誤成功にせず、編集案を失わずblocked／安全な再開ができた。
- [ ] 機能別導出索引から正本と変更差分を確認でき、依存した下流だけstaleになる。
- [ ] UI Skillのisolated/trigger/semantic、UI package回帰・migration・既存TC/E2E利用経路を検証した。

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
