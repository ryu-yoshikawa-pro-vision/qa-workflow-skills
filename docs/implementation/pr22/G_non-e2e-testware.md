# PR #22 並行実装：G — 非E2E testware・実行

## 位置付け

API・バッチ・コンポーネント・非機能・静的検証のtestware実装／更新・実runnerによる実測・原因分析を担当する。

- 作業branch：`feat/pr22-g-non-e2e-testware`
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
- [詳細01：非E2E実装・実行](../../plans/2026-11-07_170134_qa-full-process-implementation_01_test-implementation-and-execution.md)
- [詳細05：実行と品質](../../plans/2026-11-07_170134_qa-full-process-implementation_05_testware-execution-and-quality.md)
- [詳細06：静的テスト](../../plans/2026-11-07_170134_qa-full-process-implementation_06_static-testing-and-improvement.md)

関連完了条件の主な担当：QA全工程 7・8・10の非E2E・静的／実行部分。

## このbranchで変更する対象

- 新設`skills/testware-implementation/**`、`skills/testware-execution/**`
- 既存`skills/adversarial-review/**`、`skills/test-execution/**`の必要な静的レビュー・直接実行の拡張
- 非E2Eのrunner adapter／preflight／cleanup／trace・assertion品質と独立fixture／実製品テスト

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

- [ ] 既存Playwright E2E／`test-execution`・`adversarial-review`、対象runner／fixture／cleanupとデータ権限を確認した。
- [ ] E/F/H/JとTC/ref・実行母集団・required route・run結果の単位を合意した。

## 作業内容

1. 対象TCまたは明示testwareから、API-only Playwright・Vitest・バッチ・イベント／非機能等の実装ownerを判定し、既存ブラウザE2Eと責務が重ならないようにする。
2. 安全なworktree／copyと競合時反映拒否の下でtestware・fixture・設定を実装／更新し、SUTの製品コードを改修しない。
3. TCに依存しない非ブラウザtestware直接実行、実runnerのpreflight・開始確認・attempt・raw結果・cleanup・副作用保護を行う。
4. Vitestのtest ID・TC ID・retryを区別し、実行結果を根拠なしのTC PASSへ変換しない。assertion・oracleを別経路でレビューする。
5. 非機能の測定条件／品質特性／閾値が未確定なら未確定として扱い、静的レビュー（`adversarial-review`）と静的解析ツール実行（`testware-execution`）を分離する。
6. 失敗時はSUT／testware／fixture／環境／runner／仕様不明等の観測・仮説・確度・証拠・再実行先を記録する。欠陥候補の外部Issue追跡はJへ渡す。

## 依存と引継ぎ

- E/F→G：TC・方式・準備・環境・終了条件。
- G→H/J：run・test ID・source/build revision・raw結果・cleanup・診断と取得完全性。
- A：実行ownerのruntime登録や保存／承認契約の共有変更を依頼する。
- J→G：修正通知を元testware・buildで再実行する依頼。

**並行作業**：依存先の完成前でも固定fixtureで担当範囲を実装・局所検証する。実際の他owner成果物を用いた横断照合はPR #22で行う。必要な外部情報・権限・環境が不足する箇所は未検証／blockedと記録し、独立して実装可能な箇所は継続する。

## 完了基準

- [ ] 対象方式のtestware実装／更新と実runnerでの実行・raw証拠・cleanupが結びつき、独立fixtureと固定qa-training-storeの対象を区別した。
- [ ] preflight不備・共有データ競合・応答消失・cleanup失敗・隔離worktreeの競合を安全に拒否／再開できる。
- [ ] 非E2E結果の原因仮説・確度・結果確定・未実行を元runへ保持し、FAILを製品欠陥やTC PASSへ自動変換しない。
- [ ] 静的レビュー／静的解析・非機能品質・手動非ブラウザTCの各経路が必要範囲で実行でき、非対応・未設定を明示した。
- [ ] PlaywrightブラウザE2E・既存test-executionを壊さず、H・Jが読めるrun契約・raw結果・fixtureを局所検証した。H・Jの実成果物との横断接続はPR #22へ引き継いだ。
- [ ] Plan詳細01・05の全完了条件と詳細06の静的テスト条件、関連unit／runner／isolated／意味評価を検証した。

- [ ] 変更したSkillの正式な`SKILL.md`・入力／出力・履歴／状態・運用文書と、必要なisolated packaging・決定論的テスト・意味評価・trigger評価を揃えた。
- [ ] 対象Planの正常系と負例を独立基準・証拠で判定し、旧artifact／legacy・既存呼び出し元・下流consumer・CIへの回帰を確認した。
- [ ] 関連unit／integration、repository既定のformat/lint/Skill validation、関連Actionsを個別に確認し、実行したコマンド・結果・未検証理由を担当Markdownまたは検証レポートへ記録し、PR本文は最新状態と参照先のみを示した。
- [ ] source ref・artifact ref・revision・必要承認・保存readback・失敗／再開条件をAと接続し、統合時に再取得できる証拠を残した。
- [ ] 担当branch内の実装・局所検証は完了し、PR #22のみで行う横断検証と15＋10条件の最終判定を**担当branchの完了条件から除外して**引継ぎ項目として記録した。

## PR #22へ取り込む前の確認

1. 自branchの差分が担当範囲に収まり、他担当の変更・main／PR #17の最新変更と衝突しないか再確認する。
2. 変更内容・受入証拠・未実施／blocked／SKIP・データ互換・移行・rollbackの影響を担当Markdownまたは検証レポートへ記録し、PR本文は目的と現在の状態だけに更新する。
3. PRのbaseが`feat/development-qa-traceability`であることを確認する。**PRのmain向け付け替え、merge、close、force push、branch削除は依頼なしに行わない**。
4. PR #22へ担当の変更・証拠・依存条件を引き渡す。PR #22の統合確認は**PR #22上で実施**し、A担当branchには移さない。

## 実装・局所検証記録（2026-11-09）

### 追加・更新した担当範囲

- 新規Skill: `skills/testware-implementation/`、`skills/testware-execution/`。各Skillに入口、責務境界、入力・出力・trigger、決定論的・意味評価データを用意。
- `skills/testware-implementation/scripts/snapshot_guard.py`: 隔離編集の対象path、dirty、HEAD、変更前hashの比較と競合拒否。これは**読取専用**であり、GitHubへの共有反映はnative条件付きHEAD更新と独立readbackが別途必要。
- `skills/testware-execution/scripts/contract.py`: Playwright API-onlyとブラウザE2Eのrouting、開始前の不足条件、Vitest JSONの個別結果・部分取得・重複名・skip/todo・期待母集団、非ブラウザTCの期待値比較、静的ツールの取得完全性、独立診断の保守的な照合。
- 既存`adversarial-review`: 非E2E testwareのassertion・fixture独立反証と、TC不要の製品要求／設計／コードの意味的静的レビューを追加。既存`test-execution`: ブラウザ直接TC実行異常の第一分析ownerと非ブラウザとの責務境界を明確化。
- `tests/skills/runtime/test_non_e2e_contract.py`: 担当固有の正常・負例テスト。

### 実施した検証と条件

| 実行環境                                                                                                            | コマンド／対象                                                                          | 結果                                                              | 証拠・制約                                                                                                                              |
| ------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------- | ----------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| ローカル隔離Python 3.13.5                                                                                           | `python -m unittest discover -s tests/skills/runtime -p 'test_*.py' -v`（担当固有10件） | 10件PASS                                                          | routing・preflight・Vitest重複／未収集／skip／todo・直接観測・静的tool・変更前hash拒否。独立fixtureによるunitであり実runner受入ではない |
| GitHub Actions（PR #29）                                                                                            | validate-skills／deterministic／semantic／format・lint等                                | Code Quality／deterministic／semantic PASS、Skill validation FAIL | commit `21641f7`: runtime 506件、決定論的290件PASS。Skill validationは共有READMEへの2 Skill未登録でFAIL。AへPR #23コメントで引継ぎ済み  |
| 固定qa-training-store commitでの実Vitest、API-only Playwright、batch／event／component／非機能の実runnerと生raw結果 | 実製品／実runner受入                                                                    | **未実施**                                                        | この実行環境では外部製品repo・runnerへ接続できない。対象commit、認証、テストデータ権限、runner入口・副作用・cleanupを固定してから再開   |
| 実source／artifact provider、承認、共有資源reservation・readback                                                    | native CAS・認証済み承認                                                                | **blocked**                                                       | PR #23/Aの公開契約および案件provider選定・権限が必要。local補助検査をatomic publish保証と読み替えない                                   |
| H/Jの実保存成果物との結合、S1〜S17・人間編集8ケース等                                                               | 横断受入                                                                                | **PR #22に引継ぎ**                                                | fixtureによる局所検証は他ownerの実成果物の証明ではない                                                                                  |

### 既知の未完了と再開条件

1. `contract.py`はraw JSONが与えられたときの**照合helper**であり、Vitest・Playwright・静的ツールを実際に起動するrunner adapter、timeout・attempt全取得や実cleanupの保証ではない。実runnerが導入された対象で入口chain・reporter・attempt・artifact鮮度・cleanupを実測し、対応方式のfixtureとテストを補う必要がある。
2. `snapshot_guard.py`は事前・反映直前の不一致を検出する補助で、local共有pathに対するatomic write/commitを実装しない。既存E2E実装にもPlan詳細05で要求された同じ競合保証が必要。対象ownerと協調し、shared編集のnative予約と実反映の条件付き確定の正当性を再検証する。
3. repo共有`README.md`／`EVALS.md`／`qa-workflow`のSkill登録・共通評価・CIはAの書込みowner範囲。PR #29からは勝手に変更せず、Aへ両新Skill名とvalidator／route契約を引き渡す。現行`validate-skills.yml`はREADMEに全current Skill名を要求するため、A側での同期が終わるまで該当CIは失敗し得る。
4. 非E2E testwareの独立assertionの実レビュー、公式TC／採用基準との対応、非機能の閾値、静的解析の誤検出・改版、H/Jとのrun・source revision参照は実成果物が揃った範囲で局所／横断再検証が必要。
5. 全対応方式の実runnerと保存先で必須受入を完了するまで、PR #29はDraftとし、**担当G完了**を宣言しない。PR #22の最終完了とは区別する。

### Planとの既存差分

- 詳細Plan 05は、共有workspaceでのreservationと変更反映時のnative競合検出を同時に要求する。現行`artifact_graph.reserve_shared_resource()`は実provider不在時にblockedを返すため、provider未選定環境で共有編集の開始はできない。今回のlocal fixture成功を例外扱いしない。
- 既存`test-execution`はUI手動相当のbrowser経路だけを担当する。非ブラウザ直接TCは新Skillへ分離したが、既存結果の移行・再採点は行わない。
