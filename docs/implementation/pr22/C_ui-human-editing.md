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

- - [PR #22：開発連動QA・QA全工程の実装Plan](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/pull/22)
- - [Plan索引](../../plans/2026-11-07_170134_qa-full-process-implementation_00_index.md)
- - [開発連動QA Plan（15完了条件）](../../plans/2026-11-07_122247_development-qa-traceability.md)
- - [QA全工程Plan（10完了条件）](../../plans/2026-11-07_170134_qa-full-process-implementation.md)
- [詳細08：人間編集・構成管理](../../plans/2026-11-07_170134_qa-full-process-implementation_08_human-artifact-editing.md)

関連完了条件の主な担当：開発連動QA 5・8・12・14、QA全工程 9。詳細08の全8受入はCが実証する。

## このbranchで変更する対象

- 新設`skills/ui-target-analysis/**` と `skills/spec-analysis/**` のUI mode／利用側接続
- `skills/spec-analysis/scripts/ui_target_package.py` とUI package関連の既存回帰テスト
- 人間の編集案の差分抽出・検証・正式materializeに必要なSkill局所helper／受入テスト

**変更境界**：以下に記載のない共有ファイルを変更したくなった場合は、書込みownerへ変更内容・必要な入力出力・検証例を渡す。既存実装の回帰を避けるため、既存helperの再利用を優先し、他担当の正本を新設Skillに複製しない。新規テスト・fixture・評価データは可能な限り担当固有のファイルに分ける。

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

**並行作業**：依存先のコード完成を待たずに固定fixtureで開発してよい。ただし、最終的には保存済みの実成果物ref・source revision・履歴・現在性を照合し、fixture成功を実統合成功と混同しない。必要な情報・権限・環境が欠けるときは、該当scopeを未確認／blockedと記録して別scopeの作業を継続する。

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
- [ ] 他担当へ渡す入出力と、PR #22でのみ確認できる未完了の全体条件を区別して報告した。

## PR #22へ取り込む前の確認

1. 自branchの差分が担当範囲に収まり、他担当の変更・main／PR #17の最新変更と衝突しないか再確認する。
2. 変更内容・受入証拠・未実施／blocked／SKIP・データ互換・移行・rollbackの影響をPR本文に記載する。
3. PRのbaseが`feat/development-qa-traceability`であることを確認する。**PRのmain向け付け替え、merge、close、force push、branch削除は依頼なしに行わない**。
4. PR #22の統合担当Aに引継ぎ、統合先で関連Plan条件を再検証する。
