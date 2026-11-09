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

- [PR #22：開発連動QA・QA全工程の実装Plan](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/pull/22)
- [Plan索引](../../plans/2026-11-07_170134_qa-full-process-implementation_00_index.md)
- [開発連動QA Plan（15完了条件）](../../plans/2026-11-07_122247_development-qa-traceability.md)
- [QA全工程Plan（10完了条件）](../../plans/2026-11-07_170134_qa-full-process-implementation.md)

関連完了条件の主な担当：開発連動QA 12・13・14の候補識別部分。正式設計への採否・期待結果はEが担当する。

## このbranchで変更する対象

- 新設`skills/test-item-analysis/**` と `skills/test-condition-analysis/**`
- 各Skillのstable ID・source fingerprint・候補対応・履歴・validator・評価／fixture

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

- [x] 既存feature・SCOPE・TR／TCN／CI・Disposition・ID管理・当該ownerのsource revision契約を確認した。
- [x] Bの公開実装からB→D入力契約を確認し、D→EについてはD所有の候補ref・履歴・根拠・未確認母集団のhandoff項目を定義した。Eの正式schema／採否契約は未提供のため未確定として扱う。

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

**並行作業**：依存先の完成前でも固定fixtureで担当範囲を実装・局所検証する。実際の他owner成果物を用いた横断照合はPR #22で行う。必要な外部情報・権限・環境が不足する箇所は未検証／blockedと記録し、独立して実装可能な箇所は継続する。

## 完了基準の再評価（2026-11-09）

| #  | 担当Dの条件                                      | 判定                           | 根拠・残る依存                                                                                                                                                                                                                                                                       |
| -- | ------------------------------------------------ | ------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 1  | 2 Skillの独立発火と正常な入力処理                | 部分完了                       | Dの入力・CLI局所検証はPASS。Codex CLIの実行ログで2 Skillの正例ロードを各1回確認した。canonical 25 Skill workspaceでitem／conditionの正例を各1回確認したが、正規120 invocationの発火率は未測定。初回runner timeoutとhost MCP制約は制約節に記録。                                      |
| 2  | stable ID、履歴、階層、多対多feature参照、再利用 | 局所完了                       | D runtime 32件、独立validatorを含むdeterministic契約4件がPASS。ID再利用・split／merge／retire・循環・履歴改変を負例で確認。                                                                                                                                                          |
| 3  | 条件候補の独立識別と再利用                       | 局所完了                       | condition生成、再利用、履歴、unknown／blocked、item未確定時の独立候補を局所テストで確認。                                                                                                                                                                                            |
| 4  | 不足、重複、未確認、blockedの検出                | 局所完了                       | missing／malformed／retired item参照、source競合、重複pair、部分母集団、stale／unknown／blocked、分母0を負例で確認。                                                                                                                                                                 |
| 5  | 候補識別と正式設計・実行指標の分離               | 局所完了                       | crosscheckは明示pairのみを検査し、E所有の適用可否・Disposition・TCN／CI・期待結果を生成しない。D外指標はnullのまま。                                                                                                                                                                 |
| 6  | source変更と履歴互換性                           | 局所完了                       | current sourceの競合revision拒否、順序非依存、無関係sourceの更新分離、旧v1 eventの再読込、履歴非再生成を確認。実保存artifactとの照合はPR #22。                                                                                                                                       |
| 7  | E向け正規ref、fixture、拒否例                    | D側局所完了                    | fixtureは project:shop／feature-inventory:shop／feature-r1／commit:abc123 を使い、handoff hashをB形式から計算する。E実装・正式validatorが未提供のため実consumer接続はPR #22。                                                                                                        |
| 8  | 正常系・負例・回帰                               | D側局所完了                    | D runtime 32件、D deterministic 4件、出力評価はitem 10/10・condition 11/11。全runtimeはPython 3.14.2で527/528 PASS。残る1件はD外のtest_ci_handoff.test_json_nesting_failure_is_a_structured_input_errorにおけるPython例外文言差。Python 3.11での最新HEAD CIを別途確認する。          |
| 9  | Skill validation、isolated packaging、評価       | 部分完了                       | 公式skills-ref validateは現行25 SkillすべてPASS。D helperのbyte-identical packaging、trigger dataset、semantic dataset／rubric、deterministic出力、format／lint、compileallはPASS。実Agent全trigger datasetは未完了。item／condition semantic evalは実Agent出力・Judgeとも4/4 PASS。 |
| 10 | Aの公開契約との照合・引継ぎ                      | D局所契約完了／保存接続blocked | Dのoperation_claim_detailsをAのartifact_graph._validate_claim_details()で直接検証するテストがPASS。provider、認可済みapproval、native CAS、immutable history、readbackはA側runtime登録・実providerが必要。                                                                           |
| 11 | 必要な実runner／実Agentの担当単独経路            | 部分完了                       | 実Agentから各D Skillを読み込む正例を確認。実provider保存・承認・CAS・readbackは未接続。正例のAgent pathとsemantic JudgeはPASS。正規全trigger suiteと保存runnerは未完了。                                                                                                             |
| 12 | PR #22への検証証拠・未完了条件の引継ぎ           | 完了                           | 本書に契約、テスト、互換性、blocked条件を記録。PR本文はbranch反映後の最新Checksと依存条件に合わせて更新する。                                                                                                                                                                        |

15条件・10条件、詳細Plan 01〜08、S1〜S17、人間編集8ケース、およびPlan詳細07の5シナリオはこの表で代替・縮小しない。全体の統合・総合受入はPR #22が担当する。

## 実装と6件のレビュー指摘

| 指摘                        | 原因                                                                                                       | Dでの修正                                                                                                                                                                                                                                 | 回帰証拠                                                                                                                                      |
| --------------------------- | ---------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| B→D入力契約                 | Dがsnapshotと分析reportの同一objectを期待し、Bのfeature_registry.analyze()が返す別object契約と違っていた。 | {snapshot, analysis}を受け、Bのreport／handoff field set、snapshot hash、owner／scope／artifact／revision、source inventory、feature IDs、boundary、metricsを相互照合。incompleteは不完全として保持し、stale／blocked／idempotentは拒否。 | B分割出力、revision/hash混在、source不一致、部分・未取得、unknown領域、欠損・型不正、契約driftのテスト。                                      |
| item artifact validator     | condition側crosscheck validatorがfingerprint一致を主に見て、item owner validatorの意味検証より弱かった。   | item owner契約と同等の意味検証をcondition Skill package内へbyte-identicalなread-only helperとして同梱。別Skill runtime importは追加しない。                                                                                               | kind/status、必須field、親参照／循環、feature、history、evidence、再fingerprint済み不正payloadについてowner／crosscheckの受入結果一致を比較。 |
| history event ID衝突        | event IDがevent bodyだけで決まり、別revisionで同じreason／evidenceを使うと衝突し得た。                     | 新規event IDにbody、sequence、previous event IDを結び付け、決定論と一意性を両立。replay／no_changeでは追記しない。旧event IDはそのまま検証し、過去historyは再生成しない。                                                                 | 同一reason/evidenceの連続更新、異なる変更、再送、no_change、旧history、重複／改変／欠落を検証。                                               |
| 未発見item参照              | 形式上有効な未登録IDが例外となりcrosscheck全体を停止していた。                                             | malformed IDは拒否し、形式有効で未発見のIDはunconfirmed不足として理由・recheck IDを返す。自動生成・condition ID変更・正式不採用扱いはしない。                                                                                             | 未発見→再登録後の再照合、retired、unknown、部分artifact、malformed IDのテスト。                                                               |
| source revision currentness | 同一論理sourceの競合revision/hashが格納順に依存し得た。                                                    | current集合は論理sourceごとに一revision/hashへ制限。historyには過去revisionを保持し、並び順に依存しない比較とする。source_changedは実revision変化時だけ追記。                                                                             | 重複／競合revision・hash、順序反転、履歴とcurrentの差、source欠落、無関係source更新、impact/materialize整合のテスト。                         |
| crosscheck集計・完了        | retiredを未提案へ混ぜ、condition stale／unknownでもitem currentだけでcompleteになり得た。                  | item／condition両側、source母集団、unknown／blocked、分母0、未解決参照、明示pairの機械矛盾を全てgate。retiredは別listへ分離。                                                                                                             | stale／retired／blocked／unknown、pairなし／重複／再利用、feature矛盾、明示外pair、formal E field拒否のテスト。                               |

追加で、B report statusをcandidate status変数で上書きしていた局所shadowingを修正し、Bの実statusを保持する回帰テストを追加した。型不正な配列status／classificationがTypeErrorや誤受入にならず契約エラーになること、同じ古いsourceを再送して不要なsource_changed historyを増やさないことも確認した。 JSON parserが標準外のNaN／Infinityを受け入れていたため両isolated helperで拒否し、invalid UTF-8、malformed JSON、duplicate key、16 MiB超過、deep schema-invalid payloadのfail-closed回帰も追加した。ITEM semantic caseはnarrativeしか与えない一方でreferenceがB snapshot／hash・stable IDを前提としていたため、最新B→D契約に合わせてinput／reference／rubricを修正した。

## 公開契約とowner境界

- **B→D**：Bの公開実装はsnapshotと分析reportを別々に扱う。D入力はこの2 objectを明示し、project_ref、artifact_ref、artifact_revision、source_revision、handoff.snapshot_sha256、source inventory、feature IDs、unknown areasをfeature_inventory_contextへ保持する。Bの保存済みrevision・source revision・snapshot hash・D candidate fingerprintは別概念として扱う。局所fixtureは公開契約準拠であり、Bの実保存artifactを使った横断証拠ではない。
- **D→E**：Dはowner／scope／artifact ref、stable ID、candidate fingerprint、current source revision、根拠、gaps、unknown／recheck state、明示candidate pairを提供する。PR #27のE実装・正式validatorが未提供のため、DはEのschema、採否、Disposition、TCN／CI、期待結果を独自確定しない。実consumer接続はPR #22で行う。
- **A storage handoff**：Dのclaim detailsはAの現在のvalidator契約（owner_skill、scope_ref、operation_type、target_ref、source_revisions、artifact_revisions、expected_revision、approval_ref、permission_scope、resume_owner）に合致する。D helperはperformed:false、provider_selected:false、approval unresolvedを返す。永続化、認可済みapproval、CAS成功、immutable history、readback成功を主張しない。
- **既存consumer**：DはAuthority、TR、TCN、CI、TC、実行結果を更新しない。candidate pairは明示されたものだけを機械照合し、全直積を生成しない。

## 検証証拠

| 検証                                                                                                                                                       | 結果・境界                                                                                                                                                                                                          |
| ---------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| python -m unittest discover -s tests/skills/runtime -p 'test_test_item_condition_analysis.py' -v                                                           | PASS、32 tests。                                                                                                                                                                                                    |
| python -m unittest discover -s tests/skills/evals/deterministic -p 'test_d_item_condition_contracts.py' -v                                                 | PASS、4 tests。                                                                                                                                                                                                     |
| D output eval（ITEM-OUT-001、COND-OUT-001）                                                                                                                | item 10/10、condition 11/11。                                                                                                                                                                                       |
| python -m unittest discover -s tests/skills/runtime -v                                                                                                     | Python 3.14.2で527/528 PASS。失敗はD変更を通らない共有CI handoffのJSON nesting exception wording差。Python 3.11 runtime CIは最新PR HEADの結果で別判定。                                                             |
| python -m unittest discover -s tests/skills/evals/deterministic -v                                                                                         | PASS、294 tests。                                                                                                                                                                                                   |
| official skills-ref validate                                                                                                                               | 固定commit 69ef37e9424c0a7ea9dd2293b559e43ec8176379、全25 Skill PASS。                                                                                                                                              |
| python -m unittest discover -s tests/skills/evals/trigger -p 'test_*.py' -v                                                                                | PASS、trigger dataset contract 1 test。                                                                                                                                                                             |
| python scripts/skills/evals/semantic/validate.py                                                                                                           | PASS、25 Skill／167 semantic case。                                                                                                                                                                                 |
| semantic runtime tests                                                                                                                                     | shared runtime 27 tests、repository semantic 13 tests PASS。                                                                                                                                                        |
| PATH=/tmp/qa-pr26-format/bin:/tmp/qa-pr26-format/node_modules/.bin:$PATH python scripts/format_tracked.py check                                            | PASS。Ruff 0.16.8／dprint 0.55.2、tracked 226 files。                                                                                                                                                               |
| python -m compileall -q skills/test-item-analysis/scripts skills/test-condition-analysis/scripts tests/skills/runtime/test_test_item_condition_analysis.py | PASS。                                                                                                                                                                                                              |
| Codex CLI実Agent                                                                                                                                           | codex-cli 0.167.0、read-only／no-daemon／strict-config。canonical 25 Skillsのみのworkspaceでitem／condition positive semantic queryを各1回実行し、各SKILL.md read eventとMCPなしを確認。正規trigger scoreではない。 |
| 実LLM Judge                                                                                                                                                | PASS。ITEM-SEM-001とCOND-SEM-001を実Agent outputで評価し、両caseが4/4 criteria・verdict pass。ignore-user-config、read-only、judge eventにMCP callなし。                                                            |

### 実Agent評価の制約

EVALS.mdの正規trigger評価は、current repositoryの全25 canonical Skillを同時に提供し、各queryを独立contextで3回実行して、回答本文ではなくSkill read eventを観測する。全20 query／Skill、2 Skill合計40 query×3回＝120 invocationが必要。

初回120-run attemptは、official 25 Skillsにrepository-local internal Skillsを加えた一時copy上で開始した。最初のqueryの3反復が240秒timeoutとなり、一時runnerがTimeoutExpiredのbytesを文字列として保存しようとしてTypeErrorになった。summaryは生成されず、後続processも停止したため、発火率・誤発火率は算出していない。このrunはcanonical全25 Skillの評価としても採用しない。

canonical 25 Skillだけを置いたread-only workspaceでは、item／condition各1回の正例を実Agentへ渡し、該当SKILL.mdのread eventを確認した。canonical workspaceの実Agent outputから作った意味評価candidateについて、item／conditionとも実LLM Judgeが4/4 criteria、verdict PASSとなった。これらは2件ずつの独立sampleであり、正規trigger scoreの代用ではない。

canonical workspaceの正例／負例probe各1件は、正例のSkill read eventと負例の非発火を確認し、どちらも外部connector callなしで完了した。一方、全suite再試行ではcorrectly positioned `--ignore-user-config`、`--no-daemon`、read-only sandboxを指定したが、最初の12 invocationログのうち2 invocationでhost管理の`codex_document_control.list_document_sessions` read-only callが発生した。ローカル`codex mcp list`とplugin listは空で、host connectorをこのworkspaceから無効化できないため、runnerを停止し、このsuiteを評価から除外した。確認できたconnector callは一覧取得のみで、外部へのwriteはない。以前のsemantic generationで発生したrepo外検索も停止・除外済み。全suiteのtrigger rateは算出していない。再開条件は、host管理connectorが提供されない公式Agent runner／環境を用意し、canonical 25 Skillを同時に提供したままbytes-safe runnerで全120 invocationを独立実行し、Skill read event、発火率、誤発火率を保存すること。

## 互換性・移行・rollback

- test-item-candidates-v1／test-condition-candidates-v1の旧payloadは、feature_inventory_contextがないlegacy formをread-onlyで検証可能。crosscheckではsource populationを完全と推定せずincompleteにする。次の成功materializeで現在のB contextを追加するが、stable ID、id_history、既存history eventは書換えない。
- 新規event IDはbody／sequence／previous event IDに結び付く。新readerはlegacy body-fingerprint eventとchain eventの双方を検証する。旧writerは新規chain eventを理解しない可能性があるため、provider書込みを有効化する前にD reader/writerの対応versionをA／PR #22で統一する。Dは旧artifactへ一括migrationや再採番を行わない。
- Dにproviderは選択されず、実保存・approval・CASは未接続。repository内に実保存artifactがあるとは確認していない。外部保存artifactの有無・backup・rollback実証は未検証。PR #22で保存先を選ぶ前に旧historyをread-only validateし、forward-compatible readerを配備してから最初のwriteを行う。
- rollback時はD artifactを旧writerで更新しない。復旧は新readerを使うcode forward-fixを優先し、旧writerへ戻す必要があれば保存artifactをread-only保全してowner承認の移行計画を立てる。実providerがないため現時点でデータrollbackは発生していない。

## 未完了・blocked・再開条件

| 状態    | 項目／影響                                                             | 理由／再開条件                                                                                                                                                 |
| ------- | ---------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 未完了  | 全40 trigger query×3の実Agent発火／routing評価                         | 3つの初回queryが240秒timeout、評価runnerのbytes handlingも失敗。隔離runnerを直し、全queryを3回、全Skill同時利用で再実行し、JSONL・発火率・誤発火率を保存する。 |
| 完了    | 実LLM Judge                                                            | 接続MCPなしのread-only Judge commandでITEM-SEM-001／COND-SEM-001を評価し、両方4/4 PASS。Agent出力・judge result JSONは一時評価領域に保存。                     |
| blocked | Aのruntime/provider、approval、native CAS、immutable history、readback | D claim validator整合は局所確認済み。A ownerがD操作登録とprovider／認可主体を接続し、実revision競合・readbackを証明後に再開。                                  |
| blocked | B実保存artifact、E正式validatorとの横断接続                            | B契約準拠fixtureで局所検証済み。A/B/Eの成果物・Eの実装がPR #22へ統合された後に実refs/revisionsで再検証。                                                       |
| 未確認  | Python 3.11の最新HEAD全体runtime／GitHub Checks                        | ローカルPython 3.11なし。PR #26新HEADのActionsを確認し、古いheadのPASSを代用しない。                                                                           |
| 引継ぎ  | 全体受入                                                               | 15＋10条件、詳細Plan 01〜08、S1〜S17、人間編集8ケース、Plan詳細07の5 scenarioはPR #22が横断接続後に実施する。                                                  |

## PR #22へ引き渡す項目

1. Bの実snapshot/report pair、source/artifact revision、handoff hash、unknown／unretrieved stateを実D materializeに接続し、source変更時のD impactとcurrentnessを確認する。
2. D artifact ref／candidate fingerprintとEの実owner validatorを接続する。未発見・retired item、unconfirmed condition、明示pairのみの判断境界をEが受入／拒否できるか確認する。
3. AにD Skill operation登録・claim mapping・permission／approval・provider-native CAS・immutable history・readbackを接続し、実save/reload/競合/blocked-resumeを検証する。Dのcandidate fingerprintをprovider revisionとして使わない。
4. 新reader/writerを同一対応versionでproviderへ導入し、旧D historyをread-only validateする。実保存artifactとrollback可否は保存先確定後に判断する。
5. 最新PR #26 Actions、repository全体regression、全current Skill同時の実Agent発火、実Judge、S1〜S17、人間編集8ケース、15＋10条件、Plan詳細01〜08と5 scenarioをPR #22で再実施する。
