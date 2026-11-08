# PR #22 並行実装：B — Project Context・機能分析

## 位置付け

初回案件のProject Context作成・更新、開発情報源の母集団、製品機能IDと差分の正本を作る。

- 作業branch：`feat/pr22-b-context-feature`
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
- [詳細02：保存・承認](../../plans/2026-11-07_170134_qa-full-process-implementation_02_storage-approval-reporting.md)
- [詳細08：人間編集](../../plans/2026-11-07_170134_qa-full-process-implementation_08_human-artifact-editing.md)

関連完了条件の主な担当：開発連動QA 1・2・4・6・9・10。全体の保存・CI・互換条件はA・Cと共同検証する。

## このbranchで変更する対象

- 新設`skills/project-context/**` と `skills/feature-analysis/**`
- 両Skill固有のhelper・fixture・unit／意味／発火テスト
- Project ContextのSection 12／14・既存16節への出力契約（共有template・parserの編集はAが実施）

**変更境界**：以下に記載のない共有ファイルを変更したくなった場合は、書込みownerへ変更内容・必要な入力出力・検証例を渡す。既存実装の回帰を避けるため、既存helperの再利用を優先し、他担当の正本を新設Skillに複製しない。新規テスト・fixture・評価データは可能な限り担当固有のファイルに分ける。

## 着手基準

- [ ] Project Contextの既存parser、`artifact_graph.py`、`project_context_ids.py`、template、呼び出し元と回帰テストを確認した。
- [ ] AとSection 12／14、source revision、機能ID、provider・承認refの契約と共有ファイルの編集ownerを確認した。
- [ ] 対象案件の探索範囲・認証・保存先を列挙し、未確認は明示的にblockedとした。

## 作業内容

1. 既存Project Contextの発見／候補重複／初期化／更新／readback、16節・stable key・DEC/ASM ID・parserの互換を実装する。
2. Q06の配置・編集可否・機能別参照の初回確認、承認記録と有効な合意の再利用を実装する。未承認の移動・保存を拒否し、読取分析は止めない。
3. 製品コード・Issue・仕様・設計・テストのsource inventory、権限不足・取得漏れの表示、PR／rebase／merge／releaseと資料改版の取得完全性を実装する。
4. UI以外を含む製品機能の階層・安定ID・根拠・追加／変更／分割／統合／削除／廃止履歴を管理する。ファイルpathを機能IDにしない。
5. 差分未分類・未知領域・partial discovery／分母0を区別し、分類率・機能網羅率・仕様対応率へ参照を渡す。仕様Authority／Product Risk／正式TCNは担当しない。
6. 同じsource再送・旧HEAD到着・権限不足・並行更新の負例と、保存先native CAS／readbackの受入を実施する。

## 依存と引継ぎ

- A：Project Context共通templateとruntime登録、保存・承認／source入力契約の共有変更を依頼する。
- C・D・E：feature ref・機能階層・source revisionを渡す。
- F：承認済み配置・案件QA用の基本情報を渡す。
- A：製品CIの差分分類／未分類／情報源完全性・artifact hashを渡す。

**並行作業**：依存先のコード完成を待たずに固定fixtureで開発してよい。ただし、最終的には保存済みの実成果物ref・source revision・履歴・現在性を照合し、fixture成功を実統合成功と混同しない。必要な情報・権限・環境が欠けるときは、該当scopeを未確認／blockedと記録して別scopeの作業を継続する。

## 完了基準

- [ ] `project-context`が初回作成・有効既存文書再利用・差分更新・競合拒否・読戻し・履歴を扱う。既存16節・DEC/ASM・過去成果物が維持される。
- [ ] 配置方針が必要時のみ合意され、未承認の正本移動・二重正本化がない。機能別の正本参照ができる。
- [ ] `feature-analysis`が非UIを含む機能全体・安定ID・階層・差分・source inventoryを保持し、PR／merge／release／外部資料変更の現在性を判定できる。
- [ ] 機能の分割／統合／削除・partial discovery・source取得不能・0分母・旧HEAD・競合・二重受付の負例を検証した。
- [ ] C・D・Eへ実際の機能参照とrevisionを渡し、AへCI照合用のinventory・hash・未分類を渡せる。
- [ ] 新SkillのSKILL／契約／template・局所unit・意味・発火テスト、既存Project Context回帰を実行して証拠を記録した。

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
