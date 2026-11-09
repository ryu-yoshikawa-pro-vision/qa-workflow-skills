# PR #22 並行実装：G — 非E2E testware・実行

## 位置付け

API・バッチ・コンポーネント・非機能・静的検証のtestware実装・runner契約・独立fixtureでの局所検証をGが担当する。固定製品・実provider・他ownerとの受入判定はPR #22が担当する。

- 作業branch：`feat/pr22-g-non-e2e-testware`
- PRのbase／最終統合先：`feat/development-qa-traceability`（[PR #22](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/pull/22)）
- 分岐元commit：`718005961ade89a848788e8ad3a354d4c711b84a`
- このbranchのPRはDraftで進める。Gの実装・局所検証と、その実装に対するレビュー指摘の修正はGが担当する。下記の元Planに基づく受入基準はPR #22で判定し、未受入を実施済みとはしない。
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
- 非E2Eのrunner adapter／preflight／cleanup／trace・assertion品質と独立fixture、およびPR #22で実製品受入を行うための実行plan・検証手順

**変更境界**：以下に記載のない共有ファイルを変更したくなった場合は、書込みownerへ変更内容・必要な入力出力・検証例を渡す。既存実装の回帰を避けるため、既存helperの再利用を優先し、他担当の正本を新設Skillに複製しない。新規テスト・fixture・評価データは可能な限り担当固有のファイルに分ける。

## 担当branchで実施する作業とPR #22で実施する作業

### このbranchで実施・検証する

- 本書の担当対象のSkill・runtime・helper・データ契約・既存consumerとの局所接続を実装し、担当範囲の既存テスト・回帰・負例・権限／保存・履歴互換性を検証する。
- 実runner・実保存先・実Agentの局所的な契約と独立fixtureを実装・テストし、実行手順・必要権限・未検証条件をPR #22に渡す。固定製品や実providerの実行・実証による受入判定はこのbranchで行わない。
- 他branchの未統合実装は合意した契約と独立fixtureで代替して局所検証する。fixtureは他ownerの実成果物を統合した証拠にはしない。
- 担当が所有する実装不具合、局所結合・回帰不具合は**このbranchで修正**し、対応したテスト・実施証拠を残す。

### PR #22だけで実施・判定する

- Gの実runnerを固定`qa-training-store`や適切な実環境で起動し、Vitest／Playwright API-only／Web・Native component／batch・event／静的解析・非機能について、選択集合・実raw・attempt・cleanup・副作用・判定完全性を確認する。製品に存在しない方式の独立fixtureは製品実行の受入数に含めない。
- 認証済み仕様Authority・期待値oracle、provider-native承認・共有予約・CAS／readbackの証拠を取得・照合する。権限不足の場合はblockedと記録する。
- A〜Jの実装PRの取り込み、競合解消・全体再検証、**各ownerが実際に保存した成果物同士**のID／revision／currentness／承認・run参照による横断接続。
- 全current Skill同時利用時の発火／routing、工程をまたぐ実Agent・実runner・実provider・製品CIの一連の受入、S1〜S17の総合試験、人間編集8ケースの**全体経路としての再検証**。
- 開発連動QAの15条件、QA全工程の10条件と詳細Plan 01〜08の最終照合、Plan詳細07の5シナリオの**変更前後の横断実測・効率化判定**、統合後の全CI・回帰評価。
- 横断試験で見つかった問題はownerを特定し、分割可能な実装・修正は対象branchに戻す。統合固有の接続・設定・複数owner間の確認作業だけをPR #22で実施する。

### PR #22へ引き渡す証拠

- 担当の変更ファイル、公開入出力契約、参照するowner／source／artifact IDとrevision、schema／fixture、保存・承認・失敗／再開条件。
- 局所検証のコマンドと結果、独立fixture／回帰・負例、実runner・実providerの受入に必要なplan・参照情報、未実行／SKIP／blockedと再開条件。PR #22で取得した実runner／provider証拠はPR #22の受入結果として保存する。
- 他担当の実成果物が必要な横断検証項目。**これらの未実施は担当branchの局所検証を失敗扱いする理由にはしないが、PR #22の最終受入完了には必ず必要**とする。

## 共通契約が未確定の場合の着手範囲

- A（[PR #23](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/pull/23)）のsource／artifact ID・revision・scope、runtime登録、保存・承認・CAS／readback、blocked／再開、評価・CI引継ぎ契約を**実コード・既存契約と照合し、PR #23で共有された内容**に従う。
- 上記に依存しない既存実装調査、担当Skill固有ロジック、独立fixture、局所テストは先行可能。Aによる確定・共有前に、未確定の共通schema・保存形式・承認・runtimeの接続方法を推測して確定しない。
- 契約未確定で停止する対象処理と理由・解決責任者・再開条件を記録し、独立して実施できる作業を止めない。Aが共有した契約を使う局所検証の後、他ownerの**実成果物を使う横断検証はPR #22**へ引き継ぐ。

## 当初の着手基準（実データ・他ownerの合意はPR #22で確認）

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

## PR #29の実装・局所検証とPR #22の受入（2026-11-09）

利用者の指示により、**受入は単独経路も含めPR #22で実施・判定**する。ここでチェック済みなのはGの独立fixture・既存CIなど、実施した範囲の事実だけを示す。Gのコードレビュー指摘は実装上の対応事項としてPR #29に残し、元Planの受入条件を削除しない。

### Gで検証済みの実装・局所テスト

- [x] 担当Gの非E2E所有境界、既存E2E・直接TC・静的レビューとのroutingを実装・独立テストで検証した。
- [x] Git隔離編集、変更前hash／HEAD照合、非強制fast-forward確定・競合拒否とreadbackについてローカルGit fixtureで検証した。
- [x] 実subprocess・固定JSON reporter／直接観測・試行／タイムアウト・終了コード・cleanup・manifestの正常／負例を実装・局所検証した。実製品runnerを使用したとの主張はしない。
- [x] 未承認Authorityから正式TC判定を出さないこと、選択集合・suite・retry・集計・不正JSON・直接観測型比較・静的解析tool照合のfail-closedを回帰テストで確認した。
- [x] 非E2E testwareの反証レビューfixtureと、固定製品に対する限定的な静的レビューを記録し、未確認の仕様oracleを独立した品質合格へ昇格しなかった。
- [x] 担当GのSkill・guidance・評価fixture・検証記録を整備し、GitHub Actionsの5 workflowを最新の検証済みHEAD `92fe70e751ae2bc56c7f9f73ecd862f26287bb0f` で確認した。runtime unit/integration 637件、repository deterministic eval 292件がPASS。
- [x] PR #29本文とPR #22引継ぎコメントに、変更範囲、raw証拠の限界、受入の再開条件を残した。
- [ ] CodeRabbitの`CHANGES_REQUESTED`を確認し、G実装に関係する妥当な指摘を修正・回帰検証する（受入試験とは分ける）。

### PR #22に引き継ぐ受入（未実施）

- 固定`qa-training-store`でGの`runner.py`を実起動し、Vitest／Playwright API-only／Web・Native component／batch・event／静的解析・非機能の対象母集団とraw・cleanupを受け入れる作業。隔離された実行terminal、依存環境と実行許可がなく、単なる製品CIのPASSでは代替できない。固定Vitest 3件のfail-closed planと再開手順は本PR内に保存済み。
- 実providerに対する認証・仕様Authorityの承認、共有資源のnative予約、CAS、保存readback。必要なproviderと権限が接続されておらず、未認証のGit snapshotやローカル模擬結果を正式な承認証拠へ昇格しない。
- E/F/H/J各担当による契約の正式合意や他ownerの実成果物との接続。G側のschema・fixture・必要参照は記録済み。複数ownerの実データによる横断接続はPR #22で実施する。
- 固定製品testwareの期待値についての正式な仕様Authority決定と、製品testware ownerによる変更・採否。Gの確認候補と反証根拠は記録済み。製品本体・既存製品テストは本PRの書込み対象ではない。

**PR #29に残る実装上の対応**：CodeRabbitが最新の実装差分に対して`CHANGES_REQUESTED`を記録し、未解決のreview threadがある。runnerの中断・残存プロセス、Git更新時の競合、結果照合・評価の判定など、G所有コードの正しさに関する指摘はPR #22の受入へ移管しない。各指摘は既存実装・仕様・テストで確認し、妥当な修正をG branchで行う。レビュー指摘が残る時点でPR #29の実装レビューは完了していない。

上記受入の移管は未検証の隠蔽や仕様適合の証明を意味しない。PR #22で同一ID／revision／Authority／runner／raw／cleanupの実証を行い、結果を記録する。

## PR #22で判定する受入基準（元Planから保持）

以下のチェックリストはPR #29の実装済み範囲を含めた**受入の最終照合**としてPR #22へ引き継ぐ。Gの局所CI成功をもって完了にしない。

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

1. `runner.py`で隔離checkout上の実subprocess起動とattempt／timeout／raw／cleanupを実装した。ただし案件の実Vitest・API-only Playwright・静的解析toolと、実副作用・認証が必要な環境の受入は未実施。独立Python subprocessと固定JSON reporterの結果から製品runの完了を主張しない。
2. `snapshot_guard.py`の読取検査に加え`publish_git.py`で隔離commitをGit remoteに非強制fast-forward反映・readbackする経路を設けた。共有workspaceの直接編集、Git以外の保存先のnative reservation／CAS／承認、既存E2E側の競合対策は共通ownerと実providerの受入が必要。
3. 共有`README.md`／`EVALS.md`／`qa-workflow`のSkill登録・共通評価・CIはAの書込みowner範囲。PR #23はclosed・merge済み。共有正本と新Skillとの接続について、PR #22統合ownerに引き継ぐ。PR #29のtrigger正負件数不均衡はGで修正済み。README未登録による`Validate Agent Skills` failureは旧HEADの履歴で、PR #22側の共有README同期後、commit `481eada`ではsuccessを確認した。
4. 非E2E testwareの独立assertionの実レビュー、公式TC／採用基準との対応、非機能の閾値、静的解析の誤検出・改版、H/Jとのrun・source revision参照は実成果物が揃った範囲で局所／横断再検証が必要。
5. 全対応方式の実runnerと保存先で必須受入を完了するまで、PR #29はDraftとし、**担当G完了**を宣言しない。PR #22の最終完了とは区別する。

### Planとの既存差分

- 詳細Plan 05は、共有workspaceでのreservationと変更反映時のnative競合検出を同時に要求する。現行`artifact_graph.reserve_shared_resource()`は実provider不在時にblockedを返すため、provider未選定環境で共有編集の開始はできない。今回のlocal fixture成功を例外扱いしない。
- 既存`test-execution`はUI手動相当のbrowser経路だけを担当する。非ブラウザ直接TCは新Skillへ分離したが、既存結果の移行・再採点は行わない。

### qa-training-storeの固定参照と実runner再開条件

- 調査時の対象リポジトリ：`ryu-yoshikawa-pro-vision/qa-training-store`、`main` commit `2a8bcf57ff091e84a8b3bf7b123568e967000d88`（2026-11-09にGitHubから確認）。製品リポジトリには変更を加えていない。
- `package.json`で確認した実行入口は`pnpm run test:unit`（`vitest run tests/unit`）、`pnpm run test:integration`（`vitest run tests/integration --no-file-parallelism --maxWorkers=1`）、`pnpm run test:component:web`（`vitest run tests/component --exclude tests/component/native`）。`pnpm@10.34.5`、`vitest@4.1.11`、`vitest.config.ts`の`jsdom`／`tests/setup.ts`を確認した。
- これらは**既存package scriptの確認結果のみ**であり、実行許可ではない。実施前に当該固定commit、script chain・setup/fixtureの全副作用、データ・認証権限、隔離／予約・cleanup、記録するreporterの絶対pathとtest選択集合を調査する。安全な対象と許容副作用を固定してから実runner・retry・rawを取得し、H/Jへ渡す。
- ローカルcontainerではGitHubへの直接cloneが名前解決エラーとなり、当該製品repoの依存インストール／実runnerは実施できなかった。GitHub connectorによるソース閲覧は可能だったが、実行成功の証拠ではない。

## 追加実装・検証記録（2026-11-09）

前回レビューで指摘した未実装を次の範囲で対応した。

- `skills/testware-execution/scripts/runner.py`：既存Git checkoutのHEAD・clean状態、実行許可、事前検査したargv、timeoutを検証して実subprocessを起動する。個別attemptのPID・開始／終了時刻・終了コード・stdout／stderr・Vitest JSON reporter、run外cleanup、実行後の作業ツリー残存変更を保存・照合する。shared／外部副作用はnative providerの認証済み確認ができないため拒否する。
- 非ブラウザ直接TC：実行前に固定した期待値と、実バッチ等から得た終了コード・stdout JSONの観測値を比較する。終了コード0でも期待値不一致はFAIL、未観測は判定不能として元runner結果と分離した。非機能測定は品質特性、単位、閾値根拠、測定条件と実stdout数値を比較し、閾値違反と未測定を分ける。
- Vitest：固定repo rootからのreporter絶対path正規化、選択集合と個別結果の重複・missing、optionalな集計件数、suite単位の起動失敗、global `success` 不整合を検出する。runner内の一時IDをTCの永続IDに変えない。retry個別testの証拠がJSONにない場合は不明のままとする。
- `skills/testware-implementation/scripts/publish_git.py`：単一親candidateとexpected HEAD、全変更対象の変更前hash、許可path、通常ファイル性を確認後、Git remoteへの非強制fast-forward pushと、remote HEAD・fetch・blobのreadbackで変更確定を照合する。remoteが先に変更されたらpushしない。共有workspaceのnative reservationが必要な場合は別途取得し、Gitのref更新と混同しない。
- 評価器：新Skill両方の決定論的validatorが空欄の必須項目を通す問題を修正。反証レビューの修正先に新Skill二つを追加し、非E2Eのassertion漏れ／常真assertion／誤期待値およびTCなし静的レビューの独立意味評価ケースとtrigger正負例を追加。
- 独立fixture：実Git bare remoteと複数cloneを使う先行更新の競合拒否・readback・独立path再計画、実Python subprocessでの実開始・retry・timeout・run外cleanup・残存状態、Vitest形式JSONの不整合、直接TCの終了コード0＋内容不一致、非機能の閾値超過・未測定をテストする。これらは製品実runnerの受入証拠とは区別する。

### 現時点の残条件

1. 固定`qa-training-store`上の実Vitest、API-only Playwright、component、batch／event・非機能の実機能または独立runner実測は、環境・依存・認証・副作用／cleanup権限の確定を要し、**未検証**。今回のPython subprocess fixtureをVitest実行済みとしない。
2. 静的解析CLIは実行手順が追加されたが、案件で採用されたツールの実権限・raw取得・rule・version・改版後再確認は**未検証**。非機能測定条件・閾値の案件決定と本実測も未検証。
3. 共有workspaceの同一path予約、Git以外のsource／artifact providerのnative CAS・承認／readback、共通runtimeへの正式Skill登録と共有READMEの同期はAの書込み範囲および案件providerへの接続が必要。G独立fixtureはこれらの証明ではない。
4. H/J実成果物とのrun参照・診断・元結果、S1〜S17・人間編集8件・全15＋10条件の横断受入はPR #22へ引継ぎ。既存E2E implementationの共有編集競合保護もそのownerと照合する。
5. 最新HEADのCI結果はPR #29のChecksを正本とする。旧版`Validate Agent Skills`の共有README未登録FAILはAに引継ぎ済み。その他のCI・局所fixtureが成功しても、本節の未検証を完了として扱わない。

このPRは上記の未検証条件が残るためDraftのままとする。製品SUT・正式仕様・他ownerの共有正本は更新していない。

## 再レビュー修正と残る受入（2026-11-09）

### 今回の修正

- `adversarial-review`のtrigger学習／検証データを、それぞれ正例・負例同数へ修正した。共有READMEの2 Skill登録は別ownerが担当。
- `runner.py`の各attempt実行前・cleanup後にHEADを確認し、dirtyではない新しいcommitも安全完了から除外する負例を追加した。
- `preflight`は外部副作用・共有資源フラグの省略を拒否する。任意subprocessの副作用回数を検証できるproviderがないため、宣言された副作用を持つ実行を拒否する。フラグ自己申告を権限の実認証や副作用監視と同一視しない。
- `reconcile_vitest()`はsuite statusとassertion statusの矛盾も取得不完全として扱う。正常・異常fixtureのテストを追加した。
- 実run manifestへsource/build/testware/TC refとrevision、環境、選択条件・根拠、実argvのhashを追加した。選択根拠は呼出元宣言であり、provider認証済みと主張しない。
- 非機能閾値未設定を開始前に拒否し、静的解析では対象path、tool/version、rule/config、Finding数、未解析対象をraw summaryと比較する。tool固有adapter・本物の測定条件と採用基準の受入は残る。
- 独立Python runnerの既存試験に加え、ローカルHTTP実通信で200＋本文不一致をFAILとする負例を用意した。正式`qa-training-store`に対するネットワークや認証が必要なテストには代替できない。

### 未完了・外部依存

1. 固定`qa-training-store`の実Vitest（実JSON reporter・部分選択・skip/todo・retry）、API-only Playwright、component、batch/event、非機能runnerでのraw・cleanup実証は未実施。対象commit・setup、許可と実データ、runner環境の確定が必要。
2. 現在のCLIは任意subprocessの権限・副作用回数・ignored file／外部状態の復元・共有予約を認証付きで検証できない。このため宣言された副作用やshared実行は開始前に拒否する。安全に実行可能なprovider／sandboxが必要なケースはblockedのままにする。
3. 静的解析tool固有のraw収集・version照合・解析対象完全性の本接続、非機能採用閾値・測定条件の実証とtestware assertionの独立実製品レビューは未実施。独立fixtureのPASSで置換しない。
4. `README.md`、共有runtimeへのrouting／保存・承認・native CAS／readback、H/Jの実保存成果物との結合、PR #22の全条件・S1〜S17／人間編集8ケースは担当ownerの統合受入を要する。PR #23はclosed・merge済み（merge commit `d38b775e43f7`）。残る統合はPR #22で実施する。
5. 最新CI結果はPR #29のChecksを正本とする。README未登録による`Validate Agent Skills` FAILは旧HEADの履歴であり、現状と混同しない。未検証がある限りPR #29の完了・mergeは宣言しない。

## 実行安全性と非Vitest収集の追加修正（2026-11-09）

- `runner.py`で`diagnosis_hypotheses`を実行前に検証し、不正な診断による実行後のmanifest未保存を防ぐ。要素がdictではない、根拠または担当が空などの負例と、正常診断を残す試験を追加した。
- `artifacts_root`をcheckoutとの内外関係で判定してから`mkdir()`し、拒否対象のpathが作られない試験を追加した。
- Vitestに加え、Playwrightの公式JSON reporterとbatch/eventの個別結果JSONに対応した。Playwrightは公式`PLAYWRIGHT_JSON_OUTPUT_FILE`でattemptごとのrawを記録する。componentは対応するVitestまたはPlaywright reporterを利用する。
- reporterの選択集合、path／title／project、retry、global error、状態・母集団・exit codeとの矛盾を確認し、結果がない自動testwareではexit 0でも`runner_pass`としない。任意stdout期待値は正式なTC根拠がなければ個別結果の取得完了を代替しない。
- 独立Python subprocess・模擬JSONの正常／負例を実装した。採用済み実runnerと本物の製品・認証・権限・副作用／cleanup、静的解析・非機能の実測、H/Jやproviderの実成果物照合は未実施。fixtureのPASSと実製品受入を混同しない。
- PR #23はclosedだがmerge済みである。以前の「closed・未merge」という記載を訂正した。共有READMEとruntimeへの新Skill接続はPR #22の統合条件として引き継ぐ。

最新CIの正本はPR #29のChecksとする。担当Gの全完了条件を満たしたという判定には、実runner受入・共有接続・下流証拠が別途必要。

## 追加実装・検証（2026-11-09：Vitest・cleanup・TC Authority・Jest）

- Vitest 4公式JSONで`ancestorTitles`先頭に含まれる空root名を構造上の区切りとして扱い、実テスト名に含む途中の空文字列は引き続き不正とする。固定形式の回帰テストを追加した。
- Vitest／Playwright／batch-event各reporterの解釈で型不正などの例外が発生しても、元reporter・stdout・stderrを保存し、事前許可されたcleanup、実行後workspace確認、manifest保存へ進む。不正なreporter入力でcleanupが飛ぶ負例を追加した。
- `direct_tc=true`では、`direct_tc_authority_file`に指定された**固定Git HEAD上の追跡済み通常ファイル**からTC ref・revision・仕様Authority ref・期待結果全件を読み取る。実行planの期待値が1件でも欠ける・異なる、指定fileが未追跡・版違いなら開始前に拒否する。rawから仕様を推測しない。取得したGit blobとsource revisionをmanifestへ残す。ただしGit snapshotの存在は承認主体の認証ではなく、実providerの検証・approved状態の主張ではない。
- 固定`qa-training-store`のcomponent構成を再確認したところ、Web側はVitest、Native側はJestを利用するため、`component`にJestの公式`--json --outputFile`で出力するJest互換JSON形式を追加した。実runner本体ではなくJest形式JSONを生成する独立fixtureで局所検証する。
- 固定`qa-training-store`での実Vitest・Playwright API-only・Native Jest・batch/event・静的解析・非機能計測の実run、必要なデータ／権限・安全なcleanup、外部Authority providerの承認／CAS／readback、H/J実artifactとの横断受入は未検証として残す。GitHub connector経由では対象repoのsource・package scriptを確認できるが、この実行環境からGitHubへ直接cloneできず、製品実runの証拠にはならない。
- 上記の局所修正はPR #29の最新CIで判定する。PR #22の15＋10条件、S1〜S17、人間編集8件、詳細07の比較シナリオは削減しない。実runner・実provider受入が揃わないためG完了チェックボックスは未達のままとする。

## 局所レビュー追加修正（2026-11-09：Authority判定・静的解析の同一性）

- `runner.py` の直接TCは、固定Git HEADの期待結果snapshotから照合できても、そのsnapshotの仕様Authorityが実providerで認証・承認されたとは限らない。外部承認未接続のまま `tc_verdict=PASS` を出していたため、正式判定はnullに修正し、観測比較のみ `direct_observation_verdict` に維持した。固定snapshotの全件照合、元rawとrunner終了結果は従来どおり保持する。
- 静的解析のraw summary照合に `tool_ref` を追加した。予定toolと実raw上のtoolが異なる場合は取得不完全とする。version・rules・config・対象path・終了コードの検査は維持する。これは実ツールの認証・署名検査ではない。
- `tests/skills/runtime/test_non_e2e_runner.py` に、未認証Authorityでは正式TC PASSを出さない回帰確認と、静的解析tool不一致時の取得不完全の負例を追加した。
- 固定`qa-training-store`の実Vitest／Playwright API-only／Web Vitest・Native Jest／batch・event／静的解析・非機能の受入、実providerの認証・許可・cleanup・readbackとH/J実artifactの横断照合は、この変更では実施していない。実runnerの安全な実行前提を確定できない対象はblockedのまま保持する。
- 検証コマンド：`python -m unittest discover -s tests/skills/runtime -p 'test_non_e2e_*.py' -v`。実行結果と最新CIについてはPR #29のChecksを正本とし、ローカルで未実行の結果をPASSと記載しない。

### CI回帰・公式reporterの欠落検査（2026-11-09）

- commit `320c196` のDeterministic Output Evalsで、既存の直接TCテスト3件が旧`tc_verdict`値を期待してFAILした。新契約で未認証の正式`tc_verdict`はnull、観測比較は`direct_observation_verdict`へ分離するため、3件のassertionを修正した。元runの`observed_FAIL`／`observations_incomplete`は維持する。
- 公式Vitest／Jest JSONのroot `success`が欠落しても、終了コード0と個別resultだけで成功にしてしまう経路を修正。欠落rootの負例を追加した。
- 修正後の検証結果は更新後HEADのChecksを正本とする。旧commitのFAILと新HEADの結果を混同しない。

### Vitest／Jest JSON取得完全性の補強（2026-11-09）

- `contract.reconcile_vitest()`は、公式Vitest 4／Jest JSONの全test集計（total／passed／failed／pending／todo）とroot `success`が欠落していても、選択した個別結果が一致すれば取得完全とする余地があった。全カウンターの型・値とglobal statusを必須とし、欠落したreporterは取得不完全に変更した。
- `test_non_e2e_contract.py` の正常skip/todo fixtureに実reporterの集計・global statusを追加し、global status・total欠落の負例を追加した。skip/todo自体をTC PASSとみなさない従来の契約は維持する。

### 直接観測のJSON型比較（2026-11-09）

- `compare_direct()` の期待値比較では、辞書／配列の内側にあるJSON真偽値と数値が、Pythonの `True == 1`／`False == 0` により一致扱いになる可能性があった。ネストしたJSONにも型一致を適用し、終了コード0やHTTP 200と組み合わさっても誤PASSにならないようにした。
- `tests/skills/runtime/test_non_e2e_contract.py` に、期待`{"ok": true}`へ実測`{"ok": 1}`を渡す負例を追加した。外部Authority未認証では正式TC判定は未確定という契約は維持する。

## 最新CIの検証結果（2026-11-09）

- 修正済みコードHEAD `5b0602ae0c7c2b59849146de8936a63d574146eb` のGitHub Actionsは、[Code Quality](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/actions/runs/42584887894)、[Validate Agent Skills](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/actions/runs/42584887972)、[Validate Deterministic Output Evals](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/actions/runs/42584887817)、[Validate Semantic Output Evals](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/actions/runs/42584887926)、[Codex Harness](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/actions/runs/42584887799)が個別にsuccess。
- 決定論的workflowのログで、repository deterministic eval 292件・runtime unit/integration 633件がPASS。追加したGの回帰・負例は全runtime suiteの一部であり、これを固定製品runnerの受入結果とは扱わない。
- CodeRabbitの手動全体レビューは無料利用枠上限で実施されておらず、レビュー完了としない。
- 固定製品の実runner（Vitest／Playwright API-only／Web・Native component／batch・event・静的解析・非機能）、実provider承認／共有予約／CAS／readback、H/J実成果物との横断接続は依然未受入。固定製品の既存CIでVitestジョブが成功したことはG adapterの受入の代わりにならない。
- 本文書への追記後にHEADが進んだ場合は、最新の[PR #29 Checks](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/pull/29/checks)を最終検証の正本とする。未実行／blockedが残るためDraftを維持する。

## 直接TC期待値snapshotの型照合（2026-11-09）

- `runner._verified_tc_expectations()`は、Gitの追跡済み期待値と実行planの比較にPythonの`==`を使用しており、JSONの入れ子にある`true`と`1`を同一視できた。実行前の仕様期待値改変を拒否できないため、既存`contract._json_equal_strict()`を再利用して型まで照合する。
- 独立fixtureの固定Git blobに`{"ok":true}`を保存し、実行planだけを`{"ok":1}`へ変えた場合、起動前に`direct_tc_expectations_incomplete_or_mismatched`で拒否されることを回帰テストに追加した。
- この照合はGit snapshotの改変防止であり、仕様Authorityのprovider認証・承認ではない。正式`tc_verdict`は引き続き未判定とする。固定製品の実runner受入・実provider受入は未実施のまま。

## 固定製品の独立assertionレビューと実run再開条件（2026-11-09）

- 調査対象：`qa-training-store`の固定SHA `2a8bcf57ff091e84a8b3bf7b123568e967000d88`、`tests/unit/pricing.test.ts`（3件）、`src/domain/services/pricing.ts`、`vitest.config.ts`、`tests/setup.ts`、`docs/spec/features/storefront.md`（BR-STOREFRONT-003・AC-STOREFRONT-003）。
- 対象3件の実コードには、セール開始／終了の境界と価格、会員割引の数量計算、会員ランク別の送料・合計金額について、固定値を用いたassertionがある。対象テストに明白な常真assertionやassertion未実装は認められなかった。ただしこの確認は**コード静的読取による限定したレビュー**であり、runnerを実行した証拠・製品コードの正しさ・他のtestwareのレビュー完了を意味しない。
- 参照した正式仕様は、セール期間と会員割引の反映・境界を要求しているが、割引率、送料無料閾値、端数処理等の数値根拠は今回確認した節からは特定できなかった。テストに書かれた期待値が製品の計算コードと一致するだけでは独立した仕様Authorityの証明にならない。数値oracleの正式根拠が確認できるまで独立assertion品質の総合受入は**未完了**とする。
- 固定3件を実runnerで受入するためのfail-closed planひな形を`skills/testware-execution/assets/qa-training-store-pricing-vitest.plan.json`に追加。実行前に必須の`script_chain_reviewed`、権限、隔離、母集団の検証状態をfalseとしており、検証しないまま実行可能にしない。手順は`skills/testware-execution/references/guidance.md`に記載した。
- 本環境のGitHub接続はファイル・CI閲覧とbranchへの書込みに利用できるが、固定製品repoのclone／依存導入／任意のGitHub Actions実行を開始する権限付きterminalがない。コンテナのGitHub接続もDNS解決不能である。固定製品の実Vitest／Playwright API-only／Native Jest／バッチ・イベント・静的解析・非機能の実行、外部副作用／cleanup・provider承認の受入はこの実施では**未実行・blocked**であり、独立fixtureのCIを置き換えない。

## JSON入力の重複キー・非有限数拒否（2026-11-09）

- `runner.py`はplan、Git追跡のTC期待値snapshot、実reporter、直接観測stdout、静的解析／非機能stdoutを通常の`json.loads()`で読んでいた。同一objectに同名キーが複数あると後の値が採用され、実行許可フラグや期待値・raw結果の解釈を曖昧にできたため、共通の`_strict_json_loads()`で重複キーと`NaN`／`Infinity`を拒否する。
- 実行plan内の`script_chain_reviewed`が`false`と`true`で重複している場合は開始前に`duplicate_json_key`で拒否する。固定TC Authority blobの版情報が重複している場合は`invalid_direct_tc_authority`で拒否し、実コマンドを起動しない。元rawのreporter JSONが不正な場合は従来のresult collection・cleanup・manifestの処理で不完全として扱う。
- この入力検査は外部providerの本人性や承認状態を保証しない。実製品の実runner受入は未実行のまま。

## 固定製品testwareの反証レビュー（2026-11-09）

- 対象は固定SHA `2a8bcf57ff091e84a8b3bf7b123568e967000d88` の`tests/unit/pricing.test.ts`、`tests/component/cart-page.test.tsx`、対応する`src/domain/services/pricing.ts`および既存の仕様記述。**ソース静的レビューのみ**で、実runner・製品欠陥の確定ではない。
- `tests/unit/pricing.test.ts`の「uses the same subtotal shipping rule for every membership rank」は小計5,500円で全ランクの送料を確認する。実装の送料無料閾値5,000円以上なので、`platinum`の閾値未満でも送料無料となる独立分岐（`rank === "platinum"`）はこのケースでは検証されない。プラチナ特例が誤って削除されてもこのテストは通り得る。仕様Authorityと分岐根拠を確認したうえで別の閾値未満ケースが必要か、製品testwareのownerへ確認する。
- `tests/component/cart-page.test.tsx`の「keeps the cart visible while surfacing a mutation failure」は`updateQuantity`が呼ばれたこととエラー表示を確認する一方、要求した数量`2`、対象itemや期待versionが正しく渡されたことはassertionしていない。このテスト単独では引数の取り違えを検知できないため、対象TC・既存別テストでの検証有無を製品testwareのownerが確認する。
- 既存仕様`docs/spec/features/storefront.md`で価格・会員ランクの表示は確認できたが、数値の割引率・閾値を採用するAuthorityはこの参照範囲から確定できなかった。製品実装の定数だけを独立oracleとしない。
- いずれも「テスト観点／品質上の未検証候補」であり、SUTの製品欠陥や既存testwareの修正をこのPRで確定しない。Gでの確認結果をH/Jと製品testware ownerへ引き継ぎ、元runの判定を変更しない。

## Vitest reporter構造の追加負例（2026-11-09）

- `contract._test_key()`は先頭の空root名を`while`で無制限に除いていた。Vitest 4の既知の公式形式で許容する先頭空rootは1つだけなので、2つ以上の空rootを持つreporterは拒否する。
- `reconcile_vitest()`はfile suiteが`skipped`／`pending`／`todo`と報告する一方、個別assertionに`passed`／`failed`が含まれる矛盾を検出していなかった。取得完全と誤認しないよう、suite statusとの照合を追加した。
- `test_non_e2e_contract.py`に、重複した先頭空rootと、suite `skipped`＋assertion `passed`の負例を追加。これらは独立の構造テストであり、固定`qa-training-store`実runnerでの受入を済ませた証拠ではない。

## CodeRabbit指摘への実装対応（2026-11-09）

- 対象：PR #29のCodeRabbit `CHANGES_REQUESTED`（レビューコメント21件、2026-11-09の実装HEAD `92fe70e`に対するレビュー）。この項はGの実装・局所検証の記録であり、PR #22が担当する実runner・provider・他ownerの受入完了証拠ではない。
- reporterと選択集合：case-jsonは空タイトルを拒否、Vitestはreporterの先頭空rootのみ除外し、単一projectに一致する`--project`引数を1つだけ要求する。重複指定・glob・複数projectは開始前に拒否する。Playwrightは公式`config.rootDir`相対pathをrepo相対に照合する。実起動前に`selected`のtype・path・title・重複・projectの整合を検証する。
- 実行と原観測：相対`argv`／`cleanup_argv`はcheckout基準で解決し、`source_revision`と実repo HEADを照合。JSONの大きすぎる指数値は非有限として拒否。直接TCの結果収集は実観測の有無で判定し、期待値不一致と非ゼロ終了コードを`observed_FAIL`のまま記録する。
- process：Linuxの専用runnerはchild subreaper＋procfsで別sessionに移行した子孫も採用・検出し、実行scopeの停止・reap確認後にcleanupを開始する。cleanup自体の子孫も検査する。終了確認ができない場合はcleanup開始を拒否し、終了後に子孫が残った場合も安全成功としない。SIGINT時は元のprocess groupを停止してmanifestを残す。Linuxのsupervisionが使えない環境・Windows・その他POSIXは`process_supervision_unavailable`で開始前に拒否する。代替実行環境を含む受入はPR #22が担当する。
- Git公開：差分pathはNUL区切りで取得し、日本語file名、許可された削除・rename後の不在readbackに対応。候補commitは`expected_head`を単一親とし、leaseで競合する更新・巻き戻しを拒否する。実共有remoteには未公開で、独立bare Git fixtureで検証する。
- 評価と契約：実行結果の開始・cleanup・診断、testware実装の実testware／引継ぎを出力評価へ追加。反証レビューでは既存E2E用`REV-D015/D016`を維持し、非E2E・静的レビュー用`REV-D017〜D020`を追加。評価入力`review_mode`を基準に適用し、`source@revision`の両要素、fixture指定sourceとの一致を検証。`REV-OUT-003`の評価ケースと`ASSERTIONS.md`を更新した。製品文書への直接静的レビューを入力契約に明示した。
- 追加回帰：独立reporter、変更path許可、Gitの競合・削除・日本語path、direct TC、失敗したstatic tool終了コード、SIGINT時のcleanup開始順序、別sessionの子孫、cleanup由来の子孫、Vitestの複数`--project`指定、legacyレビューとの互換性。HEAD`7d1b1da`でDeterministic Output Evalsの292件、runtime unit/integrationの655件がPASS。CI結果はPR #29の最新Checksを正本とする。
- 共有ファイル`scripts/skills/evals/deterministic/common.py`の新Skill名許可はG branchでは変更せず、PR #22統合branch `e58e2a6`で修正し、`WF-D002`の回帰テストを追加。共有ownerの正本はPR #22とする。
- 上記実装がレビュー指摘に対応するかは最新の実装コード・個別回帰テストとCodeRabbit指摘threadごとに判定する。PR #29の全レビュー完了は未宣言で、実受入条件は引き続きPR #22へ引き継ぐ。
